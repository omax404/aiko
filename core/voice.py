"""
AIKO VOICE ENGINE — Pocket TTS (Local Inference)
Uses TTSModel.load_model() + .generate_audio(state, text) for local speech.
Pre-warms in a background thread to avoid blocking startup.
"""

import os
import asyncio
import time
import logging
import threading

logger = logging.getLogger("Voice")

# Thread-safe model state
_tts_lock = threading.Lock()
_tts_model = None
_voice_state = None
_tts_ready = threading.Event()  # Signals when model is loaded
_tts_failed = False


def _warmup_tts():
    """Load TTS model in background thread. Called once at startup."""
    global _tts_model, _voice_state, _tts_failed
    try:
        from pocket_tts import TTSModel
        logger.info("🔊 Loading Pocket-TTS model...")
        _tts_model = TTSModel.load_model()

        # Voice selection
        clone_path = os.path.join(os.getcwd(), "voice_preview_yuki.wav")
        if os.path.exists(clone_path):
            _voice_state = _tts_model.get_state_for_audio_prompt(clone_path)
            logger.info(f"✅ Pocket-TTS ready (clone: {os.path.basename(clone_path)})")
        else:
            _voice_state = _tts_model.get_state_for_audio_prompt("alba")
            logger.info("✅ Pocket-TTS ready (voice: alba)")

    except Exception as e:
        logger.warning(f"[Voice] Pocket-TTS init failed: {e}")
        _tts_failed = True
    finally:
        _tts_ready.set()  # Unblock any waiting speak() calls


class VoiceEngine:
    def __init__(self):
        self.is_speaking = False
        self.output_dir = os.path.join(os.getcwd(), "data", "voices")
        os.makedirs(self.output_dir, exist_ok=True)

    def start_warmup(self):
        """Start background model loading. Call this once at startup."""
        t = threading.Thread(target=_warmup_tts, daemon=True)
        t.start()

    def is_available(self) -> bool:
        return _tts_ready.is_set() and not _tts_failed

    def clean_text_for_tts(self, text: str) -> str:
        import re
        text = re.sub(r'http\S+', 'link', text)
        text = re.sub(r'```.*?```', 'code block', text, flags=re.DOTALL)
        text = re.sub(r'<.*?>', '', text)
        text = re.sub(r'[*_`]', '', text)
        text = " ".join(text.split()).strip()
        if len(text) > 300:
            text = text[:300]
        return text

    def clear_old_cache(self):
        """Remove audio files older than 1 hour."""
        try:
            now = time.time()
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".wav"):
                    path = os.path.join(self.output_dir, filename)
                    if os.path.isfile(path) and (now - os.path.getmtime(path)) > 3600:
                        os.remove(path)
        except Exception:
            pass

    async def speak(self, text: str, emotion: str = "neutral", on_audio=None, **kwargs):
        """Synthesize speech using local Pocket-TTS."""
        clean_text = self.clean_text_for_tts(text)
        if not clean_text:
            return

        loop = asyncio.get_running_loop()

        def _blocking_speak():
            """All blocking work runs in a thread."""
            # Wait for model to finish loading (blocks thread, NOT event loop)
            if not _tts_ready.wait(timeout=90):
                logger.warning("[Voice] TTS model still loading, skipping...")
                return None

            if _tts_failed or _tts_model is None:
                return None

            self.is_speaking = True
            try:
                self.clear_old_cache()
                filename = f"voice_{int(time.time() * 1000)}.wav"
                target_path = os.path.join(self.output_dir, filename)

                logger.info(f"🔊 Synthesizing: '{clean_text[:40]}...'")

                import scipy.io.wavfile
                audio_tensor = _tts_model.generate_audio(_voice_state, clean_text)
                audio_np = audio_tensor.cpu().numpy()
                scipy.io.wavfile.write(target_path, _tts_model.sample_rate, audio_np)

                logger.info(f"✅ Audio saved: {filename}")
                return filename
            except Exception as e:
                logger.error(f"❌ Pocket-TTS error: {e}")
                return None
            finally:
                self.is_speaking = False

        filename = await loop.run_in_executor(None, _blocking_speak)

        if filename and on_audio:
            if asyncio.iscoroutinefunction(on_audio):
                await on_audio(filename)
            else:
                on_audio(filename)


voice_engine = VoiceEngine()

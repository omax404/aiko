"""
AIKO VOICE ENGINE
Uses Pocket-TTS (Kokoro/StyleTTS2 based) for high-speed local inference.
"""

import os
import asyncio
import io
import time
import tempfile
import soundfile as sf
import sys

# Try to import pocket_tts
try:
    from pocket_tts import TTSModel
    HAS_POCKET_TTS = True
except ImportError:
    HAS_POCKET_TTS = False
    print("⚠️ [Voice] pocket_tts not found. Please install it or ensure it's in python path.")

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_AUDIO_DIR = os.path.join(BASE_DIR, "Reference Audios")

MOODS = {
    "neutral": "neutral.wav",
    "happy": "happy.wav",
    "sad": "sad.wav",
    "angry": "angry.wav",
    "whisper": "whisper.wav",
    "pout": "pout.wav",
    "shy": "shy.wav",
    "confused": "confused.wav",
    "nsfw": "nsfw.wav",
    "soft": "soft.wav",
    "sarcastic": "sarcastic.wav",
    "proud": "proud.wav",
    "cat": "cat.wav"
}


class VoiceEngine:
    """Aiko's local voice engine using Pocket TTS."""
    
    def __init__(self):
        self.model = None
        self.voice_states = {}
        self.is_ready = False
        self.is_speaking = False
        
        if HAS_POCKET_TTS:
            self._init_thread()
            
    def _init_thread(self):
        """Initialize in background."""
        print(" [Voice] Initializing Pocket TTS...")
        try:
            self.model = TTSModel.load_model()
            self.sample_rate = self.model.sample_rate
            
            # Load voices
            self._load_voices()
            self.is_ready = True
            print(f" [OK] [Voice] Ready with {len(self.voice_states)} moods.")
        except Exception as e:
            print(f" [X] [Voice] Init failed: {e}")
            
    def _load_voices(self):
        """Clone voices from reference files."""
        if not os.path.exists(REF_AUDIO_DIR):
            print(f" [!] [Voice] Ref dir not found: {REF_AUDIO_DIR}")
            return

        for mood, filename in MOODS.items():
            path = os.path.join(REF_AUDIO_DIR, filename)
            if os.path.exists(path):
                try:
                    self.voice_states[mood] = self.model.get_state_for_audio_prompt(path)
                except Exception:
                    pass
            else:
                pass
                
        # Fallback to first available if neutral missing
        if "neutral" not in self.voice_states and self.voice_states:
            self.voice_states["neutral"] = list(self.voice_states.values())[0]

    def is_available(self) -> bool:
        return self.is_ready

    def clean_text_for_tts(self, text: str) -> str:
        """Sanitize text for better speech synthesis."""
        import re
        
        # 1. Remove URLs
        text = re.sub(r'http\S+', 'link', text)
        
        # 2. Remove Code Blocks (```...```)
        text = re.sub(r'```.*?```', 'code block', text, flags=re.DOTALL)
        
        # 3. Remove Inline Code (`...`)
        text = re.sub(r'`.*?`', 'code', text)
        
        # 4. Remove Actions (*sneeze*)
        text = re.sub(r'\*[^*]+\*', '', text)
        
        # 5. Remove excessive punctuation/lists markers
        # Replace list bullets with pause
        text = re.sub(r'^\s*[-*]\s+', '. ', text, flags=re.MULTILINE)
        
        # 6. Normalize whitespace
        text = " ".join(text.split())
        
        return text.strip()

    def stop(self):
        """Stop current audio playback."""
        if self.is_speaking:
            self.is_speaking = False
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except:
                pass

    async def speak(self, text: str, emotion: str = "neutral"):
        """Generate and play speech using Flet's Audio or pygame."""
        if not self.is_ready:
            return

        # Smart Clean
        clean_text = self.clean_text_for_tts(text)
        if not clean_text or len(clean_text) < 2:
            return

        # Stop previous if requested (Smart Interruption)
        # For now, let's just queue or overlapping is weird.
        # Ideally we stop previous:
        self.stop() 

        try:
            # Run inference in thread
            loop = asyncio.get_event_loop()
            audio_path = await loop.run_in_executor(
                None, 
                lambda: self._generate_file(clean_text, emotion)
            )
            
            if audio_path:
                self._play_audio(audio_path)
                
        except Exception as e:
            print(f" [Voice] Gen Error: {e}")

    def _generate_file(self, text: str, emotion: str) -> str:
        """Generate audio file."""
        try:
            state = self.voice_states.get(emotion, self.voice_states.get("neutral"))
            if not state:
                if self.voice_states:
                    state = list(self.voice_states.values())[0]
                else:
                    return None
            
            # Generate tensor with slower speed
            try:
                # Try passing speed if supported
                audio_tensor = self.model.generate_audio(state, text, speed=0.85)
            except TypeError:
                # Fallback if speed arg not supported
                audio_tensor = self.model.generate_audio(state, text)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                sf.write(tmp.name, audio_tensor.numpy(), self.sample_rate)
                return tmp.name
                
        except Exception as e:
            print(f" [Voice] Synthesis error: {e}")
            return None
            
    def _play_audio(self, path: str):
        """Play using winsound and track status."""
        try:
            # Calculate duration
            f = sf.SoundFile(path)
            duration = len(f) / f.samplerate
            f.close()
            
            # Set Status
            self.is_speaking = True
            
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            
            # Reset after duration (fire and forget task)
            asyncio.create_task(self._reset_speaking(duration))
            
        except Exception as e:
             print(f" [Voice] Play error: {e}")
             self.is_speaking = False

    async def _reset_speaking(self, duration: float):
        await asyncio.sleep(duration)
        self.is_speaking = False

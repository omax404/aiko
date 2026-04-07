"""
AIKO VOICE ENGINE (POCKET-TTS)
Optimized for high-speed local inference using Torch-based PCM generation.
"""
import os
import asyncio
import time
import logging
import torch
import scipy.io.wavfile
from pocket_tts import TTSModel

# Set up logging
logger = logging.getLogger("Voice")

class VoiceEngine:
    def __init__(self):
        self.is_ready = False
        self.is_speaking = False
        self.output_dir = os.path.join(os.getcwd(), "data", "voices")
        os.makedirs(self.output_dir, exist_ok=True)
        
        try:
            logger.info("📡 Loading Pocket-TTS Model (this may take a moment)...")
            self.model = TTSModel.load_model()
            # Loading CUSTOM CLONED AUDIO
            clone_path = r"C:\Users\ousmo\.gemini\antigravity\scratch\Aiko-desktop\voice_preview_yuki.mp3"
            logger.info(f"📡 Generating Voice State from clone: {clone_path}")
            self.voice_state = self.model.get_state_for_audio_prompt(clone_path)
            self.is_ready = True
            logger.info("✅ Pocket-TTS Engine Loaded & Ready with Yuki's Voice Clone.")
        except Exception as e:
            logger.error(f"❌ Failed to load Pocket-TTS: {e}")

    def is_available(self) -> bool:
        return self.is_ready

    def clean_text_for_tts(self, text: str) -> str:
        import re
        text = re.sub(r'http\S+', 'link', text)
        text = re.sub(r'```.*?```', 'code block', text, flags=re.DOTALL)
        text = re.sub(r'<emotion>.*?</emotion>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'`.*?`', 'code', text)
        text = re.sub(r'\*[^*]+\*', '', text)
        # Pocket-TTS works best with clean, plain text
        return " ".join(text.split()).strip()

    async def speak(self, text: str, emotion: str = "neutral", on_amplitude=None, on_audio=None):
        if not self.is_ready or not text: 
            return
            
        clean_text = self.clean_text_for_tts(text)
        if not clean_text: 
            return

        self.is_speaking = True
        try:
            filename = f"voice_{int(time.time() * 1000)}.wav"
            target_path = os.path.join(self.output_dir, filename)
            
            # Generate PCM data in a background thread to keep the HUD responsive
            logger.info(f"🔊 Generating speech: '{clean_text[:30]}...'")
            audio_tensor = await asyncio.to_thread(self.model.generate_audio, self.voice_state, clean_text)
            
            # Save using scipy as suggested in the docs
            await asyncio.to_thread(
                scipy.io.wavfile.write, 
                target_path, 
                self.model.sample_rate, 
                audio_tensor.numpy()
            )

            if on_audio and os.path.exists(target_path):
                if asyncio.iscoroutinefunction(on_audio):
                    await on_audio(filename)
                else:
                    on_audio(filename)
                    
        except Exception as e:
            logger.error(f"❌ Voice generation error: {e}")
        finally:
            self.is_speaking = False

voice_engine = VoiceEngine()

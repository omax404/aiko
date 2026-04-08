import os
import asyncio
import time
import logging
import aiohttp

# Set up logging
logger = logging.getLogger("Voice")
POCKET_TTS_API = "http://localhost:8000/tts"

class VoiceEngine:
    def __init__(self):
        self.is_ready = True
        self.is_speaking = False
        self.output_dir = os.path.join(os.getcwd(), "data", "voices")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # We always keep the uncompressed wav mapping for Cloud API upload parameters
        self.clone_path = os.path.join(os.getcwd(), "voice_preview_yuki.wav")
        logger.info("✅ Voice Engine switched to HTTP Cloud Architecture (Kyutai REST)")

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

    def clear_old_cache(self):
        """Removes audio files older than 1 hour to prevent hard drive saturation."""
        try:
            now = time.time()
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".wav"):
                    path = os.path.join(self.output_dir, filename)
                    if os.path.isfile(path) and (now - os.path.getmtime(path)) > 3600:
                        os.remove(path)
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    async def speak(self, text: str, emotion: str = "neutral", on_amplitude=None, on_audio=None):
        if not self.is_ready or not text: 
            return
            
        clean_text = self.clean_text_for_tts(text)
        if not clean_text: 
            return

        self.is_speaking = True
        try:
            self.clear_old_cache()
            
            filename = f"voice_{int(time.time() * 1000)}.wav"
            target_path = os.path.join(self.output_dir, filename)
            
            logger.info(f"🔊 Requesting speech from hardware accelerator: '{clean_text[:30]}...'")
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('text', clean_text)
                
                # Attach the physical clone wav directly to the REST pipeline
                if os.path.exists(self.clone_path):
                    data.add_field('voice_wav', open(self.clone_path, 'rb'), filename='clone.wav', content_type='audio/wav')
                
                async with session.post(POCKET_TTS_API, data=data, timeout=60) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(target_path, "wb") as f:
                            f.write(content)
                            
                        if on_audio and os.path.exists(target_path):
                            if asyncio.iscoroutinefunction(on_audio):
                                await on_audio(filename)
                            else:
                                on_audio(filename)
                    else:
                        err_text = await resp.text()
                        logger.error(f"❌ Pocket-TTS server error: {resp.status} {err_text}")
                        
        except Exception as e:
            logger.error(f"❌ Voice REST error: {e}")
        finally:
            self.is_speaking = False

voice_engine = VoiceEngine()

"""
AIKO VISION ENGINE (CLOUD)
Analysis of screens and images using Moondream Cloud API.
"""

import os
import asyncio
import io
import logging
from PIL import Image
from core.utils import retry
from .config_manager import config

logger = logging.getLogger("Vision")

# Configuration
API_KEY = config.get("MOONDREAM_API_KEY", "")
API_URL = "https://api.moondream.ai/v1/query"

class VisionEngine:
    def __init__(self):
        self.ready = False
        self.error_msg = None
        self.processor = None
        self.model = None
        self.device = "cpu"
        
    async def load_model(self):
        """Prepare local vision fallback using Ollama (replacing HF BLIP)."""
        logger.info("Initializing Local Ollama Vision Fallback.")
        self.ready = True
        
    async def ingest_document(self, file_path: str) -> bool:
        """Analyze document/image using Ollama local vision."""
        if not os.path.exists(file_path): return False
        try:
            # We treat vision ingestion as a local-only or cloud-first task
            description = await self.analyze_file(file_path)
            return True if description else False
        except: return False
        
    async def scan_screen(self) -> tuple:
        """Capture screen and query Cloud API."""
        try:
            import pyautogui
            loop = asyncio.get_event_loop()
            img = await loop.run_in_executor(None, pyautogui.screenshot)
            
            # Engineer Mode: Save last scan for transparency
            os.makedirs("data", exist_ok=True)
            img.save("data/last_scan.png")
            
            # Analyze
            description = await self._analyze(img)
            return description, img
            
        except Exception as e:
            logger.error(f"Scan Error: {e}")
            # Fallback to CV2 capture if pyautogui is stuck
            try:
                img = await self._capture_screen_cv2()
                if img:
                    img.save("data/last_scan.png")
                    description = await self._analyze(img)
                    return description, img
            except: pass
            return f"My visual sensors are a bit blurry, Master... {e}", None

    async def _capture_screen_cv2(self):
        """Alternative screen capture using numpy/cv2 for robustness."""
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return img

    async def analyze_file(self, file_path: str) -> str:
        """Analyze a local image file (Cloud First, Ollama Fallback)."""
        try:
            loop = asyncio.get_event_loop()
            # Open image in thread
            img = await loop.run_in_executor(None, Image.open, file_path)
            # Analyze
            description = await self._analyze(img)
            return description
        except Exception as e:
            return f"Error analyzing file: {e}"

    async def analyze_base64(self, b64_str: str) -> str:
        """Analyze a base64 encoded image string."""
        import base64
        try:
            image_data = base64.b64decode(b64_str)
            img = Image.open(io.BytesIO(image_data))
            return await self._analyze(img)
        except Exception as e:
            logger.error(f"Base64 Analysis Error: {e}")
            return "I tried to look, but the image data is corrupted, Master."

    async def _analyze(self, image: Image.Image) -> str:
        """Send image to Moondream Cloud or local Ollama fallback."""
        if API_KEY:
            try:
                loop = asyncio.get_event_loop()
                description = await loop.run_in_executor(None, self._send_request, image)
                return description
            except Exception as e:
                logger.warning(f"Cloud Vision failed: {e}. Falling back to Local Ollama.")
                
        # 100% Offline / Non-HF Fallback using Ollama
        return await self._analyze_ollama(image)

    async def _analyze_ollama(self, image: Image.Image) -> str:
        """Native local vision using Ollama or LM Studio."""
        import requests
        import base64
        
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        provider = config.get("PROVIDER", "Ollama")
        # Ensure we don't accidentally send image bytes to a Text-Only LLM (like Gemma4 or Qwen).
        model = config.get("VISION_MODEL")
        if not model:
            # If no Vision Model is explicitly set, default strictly to moondream for vision.
            model = "moondream"

        
        try:
            loop = asyncio.get_event_loop()
            
            if provider == "OpenAI":
                # LM Studio Style (OpenAI compatible with Image Support)
                url = config.get("LLM_URL", "http://127.0.0.1:1234/v1/chat/completions")
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this image briefly. What am I looking at?"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                            ]
                        }
                    ],
                    "stream": False
                }
                def _req():
                    resp = requests.post(url, json=payload, timeout=30)
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
            else:
                # Ollama Style
                payload = {
                    "model": model,
                    "prompt": "Describe this image in detail. What objects, text, or actions are visible?",
                    "images": [img_str],
                    "stream": False
                }
                def _req():
                    try:
                        resp = requests.post(f"http://127.0.0.1:11434/api/generate", json=payload, timeout=30)
                        resp.raise_for_status()
                        return resp.json().get("response", "I see something, but I can't quite describe it, Master.")
                    except Exception as e:
                        logger.error(f"Ollama internal error: {e}")
                        return f"Ollama is having trouble seeing this: {e}"
            
            return await loop.run_in_executor(None, _req)
        except Exception as e:
            logger.error(f"Local Vision Error ({provider}): {e}")
            return "My local visual cortex is having trouble processing this frame, Master... 👁️‍🗨️"

    @retry(max_attempts=3)
    def _send_request(self, image: Image.Image) -> str:
        import requests
        import base64
        from PIL import ImageDraw
        from datetime import datetime

        stamped = image.copy()
        draw = ImageDraw.Draw(stamped)
        ts = f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        # Draw a black box for text readability
        draw.rectangle([10, 10, 350, 40], fill="black")
        draw.text((20, 15), ts, fill="white")
        
        buffered = io.BytesIO()
        stamped.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{img_str}"
        
        payload = {
            "image_url": data_uri,
            "question": "Identify CURRENT active windows and explain what is happening NOW. Check the burned-in timestamp at the top left and ignore any other dates in the background if they conflict. Be brief but accurate.",
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Moondream-Auth": API_KEY
        }
        
        response = requests.post(API_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        result = response.json()
        return result.get("answer", "No answer provided.")

    async def capture_camera(self) -> Image.Image:
        """Capture a frame from the default camera."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._capture_sync)

    def _capture_sync(self):
        import cv2
        import time
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise Exception("Could not open camera sensors, Master...")
        
        # Extended Warm up - some cameras need more time to adjust exposure
        # We read more frames and add a tiny delay
        frame = None
        for i in range(20): 
            ret, frame = cap.read()
            time.sleep(0.05)
            # If we have a frame, check if it's not just pure black
            if ret and frame is not None:
                if frame.mean() > 5: # Threshold for "not totally black"
                    break
        
        cap.release()
        
        if frame is None:
            raise Exception("Failed to grab a clear frame...")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)

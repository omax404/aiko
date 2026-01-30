"""
AIKO VISION ENGINE (CLOUD)
Analysis of screens and images using Moondream Cloud API.
"""

import os
import asyncio
import pyautogui
from PIL import Image
import io
import json
import logging
import requests
import base64
import cv2
import time
from core.utils import retry

logger = logging.getLogger("Vision")

# Optional BLIP support
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    import torch
    HAS_BLIP = True
except ImportError:
    HAS_BLIP = False

# Configuration
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlfaWQiOiIxNzg3ZjdiNC04NjhlLTQyZWItYmVjOS00OThiYzEzMWMxYzYiLCJvcmdfaWQiOiJmUEVaWTh1cG8xYUpzdHBOS0xQcmFqcGV4dHNJc2oydSIsImlhdCI6MTc2OTE4NjI4NiwidmVyIjoxfQ.rp9b5B0XPBq5biF01KiNancah5h3fETF6dXU2uqb1PY"
API_URL = "https://api.moondream.ai/v1/query"

class VisionEngine:
    def __init__(self):
        self.ready = False
        self.error_msg = None
        self.processor = None
        self.model = None
        self.device = "cuda" if HAS_BLIP and torch.cuda.is_available() else "cpu"
        
    async def load_model(self):
        """Load local BLIP model if available."""
        if HAS_BLIP:
            try:
                logger.info(f"Loading BLIP on {self.device}...")
                self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
                self.ready = True
                logger.info("BLIP Loaded Successfully.")
            except Exception as e:
                logger.error(f"Error loading BLIP: {e}")
                self.ready = True # Fallback to cloud-only
        else:
            logger.warning("Transformers/Torch not found. BLIP disabled.")
            self.ready = True
        
    async def scan_screen(self) -> tuple:
        """Capture screen and query Cloud API."""
        try:
            # Capture using pyautogui in executor
            loop = asyncio.get_event_loop()
            img = await loop.run_in_executor(None, pyautogui.screenshot)
            
            # Analyze
            description = await self._analyze(img)
            return description, img
            
        except Exception as e:
            logger.error(f"Scan Error: {e}")
            return f"Error analyzing screen: {e}", None

    async def analyze_file(self, file_path: str) -> str:
        """Analyze a local image file."""
        try:
            loop = asyncio.get_event_loop()
            # Open image in thread
            img = await loop.run_in_executor(None, Image.open, file_path)
            # Analyze
            description = await self._analyze(img)
            return description
        except Exception as e:
            return f"Error analyzing file: {e}"

    async def _analyze(self, image: Image.Image) -> str:
        """Send image to Moondream Cloud."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_request, image)

    @retry(max_attempts=3)
    def _send_request(self, image: Image.Image) -> str:
        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{img_str}"
        
        payload = {
            "image_url": data_uri,
            "question": "Describe this image in detail.",
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Moondream-Auth": API_KEY
        }
        
        try:
            response = requests.post(API_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result.get("answer", "No answer provided.")
        except Exception as e:
            logger.error(f"API Error: {e}")
            raise e

    async def capture_camera(self) -> Image.Image:
        """Capture a frame from the default camera."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._capture_sync)

    def _capture_sync(self):
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

    async def get_blip_caption(self, image: Image.Image) -> str:
        """Generate caption using local BLIP."""
        if not HAS_BLIP or not self.model:
            return "BLIP model not loaded."
            
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._blip_sync, image)

    def _blip_sync(self, image: Image.Image) -> str:
        inputs = self.processor(image, return_tensors="pt").to(self.device)
        out = self.model.generate(**inputs)
        return self.processor.decode(out[0], skip_special_tokens=True)

"""
AIKO IMAGE GENERATOR
Integrates Pollinations.ai with a "Nano Banana" style Prompt Enhancer.
"""

import urllib.request
import urllib.parse
import json
import random
import asyncio
from core.utils import retry

# User Provided Key for Prompt Enhancement (LLM)
# Assuming OpenAI or compatible endpoint given 'sk-' prefix
ENHANCER_API_KEY = "sk_4FNeszBbTIv3gms1NBCE0o9zgrSv3jUX"
ENHANCER_URL = "https://api.openai.com/v1/chat/completions" # Defaulting to OpenAI standard

# Styles extracted from the Awesome Prompts Repo
STYLES = [
    "High-end photo studio, 85mm lens, f/1.8 aperture, fashion magazine style",
    "Vintage Patent Document, late 1800s, aged ivory paper, technical drawing",
    "Japanese Edo-period Ukiyo-e woodblock print, traditional mineral pigments",
    "Cyberpunk, neon lights, highly detailed, cinematic lighting",
    "Hyper-realistic black and white studio portrait, dramatic contrast"
]

class ImageGenerator:
    def __init__(self):
        self.cached_images = []

    async def generate(self, prompt, enhance=True):
        """Generate image using Pollinations.ai, optionally enhancing prompt first."""
        final_prompt = prompt
        
        if enhance:
            print(f" [Gen] Enhancing prompt: {prompt}")
            enhanced = await self._enhance_prompt(prompt)
            if enhanced:
                final_prompt = enhanced
                print(f" [Gen] Enhanced to: {final_prompt[:50]}...")
        
        # Pollinations API (Direct URL generation)
        seed = random.randint(0, 999999)
        safe_prompt = urllib.parse.quote(final_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?seed={seed}&nologo=true"
        
        return image_url, final_prompt

    async def _enhance_prompt(self, base_prompt):
        """Use the LLM Key to rewrite the prompt in Nano Banana style."""
        if not ENHANCER_API_KEY: return None
        
        # Select a random style influence
        style_guide = random.choice(STYLES)
        
        system_prompt = f"""You are a Prompt Engineer expert in 'Nano Banana Pro' styles. 
Rewrite the user's request into a highly detailed image generation prompt.
Incorporating elements of: {style_guide}.
Keep it under 300 characters for best results with Pollinations."""

        payload = {
            "model": "gpt-3.5-turbo", # Fallback model, assuming key works for standard
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": base_prompt}
            ],
            "max_tokens": 150
        }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._post_llm(payload))
            if result:
                 return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f" [Gen] Enhancement Failed: {e}")
            return None
            
    @retry(max_attempts=3, backoff_factor=1.5)
    def _post_llm(self, payload):
        req = urllib.request.Request(
            ENHANCER_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ENHANCER_API_KEY}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())

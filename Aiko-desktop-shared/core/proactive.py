"""
AIKO PROACTIVE AGENT
Autonomous behavior loop for controlling PC based on visual context.
"""

import asyncio
import random
from datetime import datetime

class ProactiveAgent:
    def __init__(self, brain, vision, pc_manager, voice):
        self.brain = brain
        self.vision = vision
        self.pc = pc_manager
        self.voice = voice
        self.active = False
        self.interval = 60 # Check every 60s
        
    async def start_loop(self):
        print(" [Proactive] Agent Loop Started.")
        while True:
            if self.active:
                await self.tick()
                # Use a larger random interval if active to avoid spam
                wait = random.randint(self.interval, self.interval * 2)
            else:
                wait = 5 # Rapid check if toggled on
            await asyncio.sleep(wait)
            
    async def tick(self):
        """Single proactive cycle."""
        try:
            # 1. Observe
            print(" [Proactive] Scanning environment...")
            desc = await self.vision.scan_screen()
            
            if not desc or "Error" in desc:
                return

            # 2. Decide via Brain (Lightweight check)
            prompt = f"[AUTONOMOUS MODE: Observe Screen]\nI see: {desc}\n[INSTRUCTION]: If there is something interesting or I should mention something to omax, give a very short comment. Otherwise, respond with '...'."
            
            # Use Brain's raw call to avoid adding to chat history yet
            comment = await self.brain.ask_raw(prompt)
            
            if comment and "..." not in comment and len(comment) > 5:
                # 3. React
                print(f" [Proactive] Autonomous Thought: {comment}")
                
                # Add to chat as system notice or just speak?
                # Let's do both to make her feel alive
                if hasattr(self.brain, 'app_callback'):
                    self.brain.app_callback("assistant", comment, "neutral")
                
                if self.voice and self.voice.is_available():
                    await self.voice.speak(comment, "neutral")
                    
        except Exception as e:
            print(f" [Proactive] Error: {e}")

    def toggle(self, state: bool):
        self.active = state
        print(f" [Proactive] Set to: {self.active}")
        return self.active

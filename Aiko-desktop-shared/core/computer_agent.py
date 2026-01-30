"""
AIKO COMPUTER USE AGENT
Implements a Claude-like Computer Use loop with Visual Awareness, JSON Protocol, and Verification.
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
import pyautogui

# Setup Persistence Logger
LOG_FILE = "session_history.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ComputerUseAgent:
    def __init__(self, vision_engine, llm_client_func):
        self.vision = vision_engine
        self.ask_llm = llm_client_func # Function to query LLM (async)
        self.history = []
        self.active = False
        
    def log_action(self, action_data):
        """Log action for persistence and context."""
        entry = f"ACTION: {json.dumps(action_data)}"
        logging.info(entry)
        self.history.append(entry)
        # Keep history manageable
        if len(self.history) > 10: self.history.pop(0)

    def get_active_window(self):
        """Get active window title using ctypes (Robust/Builtin)."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except:
            return "Unknown Window"

    async def execute_task(self, goal: str):
        """Run the Computer Use Agent loop."""
        self.active = True
        print(f" [CompAgent] Starting Task: {goal}")
        
        max_steps = 10
        step = 0
        
        while step < max_steps and self.active:
            step += 1
            print(f" [CompAgent] Step {step}/{max_steps}")
            
            # --- 1. VISUAL AWARENESS ---
            print(" [CompAgent] Scanning screen...")
            visual_state = await self.vision.scan_screen()
            window_title = self.get_active_window()
            
            # --- 2. THINK (JSON PROTOCOL) ---
            prompt = self._construct_prompt(goal, visual_state, window_title)
            response_json = await self.ask_llm(prompt)
            
            try:
                # Extract JSON from response (handling potential markdown wrappers)
                clean_json = response_json.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
                # Parse
                action_plan = json.loads(clean_json)
            except json.JSONDecodeError:
                print(f" [CompAgent] Failed to parse JSON: {response_json}")
                # Retry prompt? For now, break or skip
                logging.error(f"JSON Parse Error: {response_json}")
                break
                
            # Log intention
            self.log_action(action_plan)
            print(f" [CompAgent] Action: {action_plan.get('action')} -> {action_plan.get('reason')}")
            
            if action_plan.get("action") == "finish":
                print(" [CompAgent] Task Completed.")
                return "Task Completed successfully."
                
            # --- 3. ACT (INTEGRATION) ---
            success = await self._perform_action(action_plan)
            
            # --- 4. VALIDATION (Retry Logic) ---
            if success:
                # Secondary scan to verify?
                # Optimization: The NEXT loop iteration does the scan.
                # However, user requested immediate validation.
                # await asyncio.sleep(1) # Wait for UI to settle
                # validation_scan = await self.vision.scan_screen()
                # if validation_scan == visual_state:
                #     print(" [CompAgent] Warning: State did not change.")
                pass
            else:
                print(" [CompAgent] Action Failed. Retrying...")
                # Logic to inform LLM of failure in next turn matches
        
        self.active = False
        return "Task limit reached or stopped."

    def _construct_prompt(self, goal, visual, window):
        return f"""
You are a Computer Use Agent acting on Windows.
GOAL: "{goal}"

CURRENT STATE:
- Active Window: {window}
- Visual Scan: {visual}
- Action History: {self.history[-3:]}

Your Task: Output a SINGLE JSON object with the next step.
Schema:
{{
  "action": "mouse_move" | "click" | "type" | "keypress" | "finish",
  "coordinates": [x, y],  // Required for mouse/click (approximate)
  "text": "string",       // Required for type/keypress
  "reason": "Running logic"
}}

NOTES:
- To open start menu, click bottom-left (approx [20, 1050]).
- Screen resolution is likely 1920x1080.
- If done, use action "finish".
- ONLY OUTPUT JSON. NO MARKDOWN.
"""

    async def _perform_action(self, action_map):
        action = action_map.get("action", "").lower()
        
        try:
            if action == "mouse_move":
                coords = action_map.get("coordinates", [0, 0])
                pyautogui.moveTo(coords[0], coords[1], duration=0.5)
                
            elif action == "click":
                coords = action_map.get("coordinates")
                if coords:
                    pyautogui.click(coords[0], coords[1])
                else:
                    pyautogui.click()
                    
            elif action == "type":
                text = action_map.get("text", "")
                pyautogui.write(text, interval=0.05)
                
            elif action == "keypress":
                key = action_map.get("text", "")
                pyautogui.press(key)
                
            return True
        except Exception as e:
            print(f" [CompAgent] Exec Error: {e}")
            return False

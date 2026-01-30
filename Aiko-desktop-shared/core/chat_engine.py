"""
AIKO CHAT ENGINE (Brain)
Handles LLM interactions with Local Ollama using a ReAct Agent Loop.
"""

import asyncio
import aiohttp
import re
import json
import logging
import os
from dotenv import load_dotenv
from .persona import get_system_prompt, detect_emotion

load_dotenv()
logger = logging.getLogger("Brain")

# DeepSeek Cloud Configuration
LLM_URL = "http://127.0.0.1:11434/api/chat" 
MODEL_NAME = "deepseek-v3.1:671b-cloud"
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")


class AikoBrain:
    """Aiko's AI brain using Ollama with Tool Feedback Loop."""
    
    def __init__(self, memory_manager, rag_memory, pc_manager=None, vision_engine=None, vts_connector=None, latex_engine=None, action_bridge=None, obsidian=None):
        self.memory = memory_manager
        self.rag = rag_memory
        self.pc = pc_manager
        self.vision = vision_engine
        self.vts = vts_connector
        self.latex = latex_engine
        self.bridge = action_bridge
        self.obsidian = obsidian
        self.comp_agent = None
        self.model = MODEL_NAME
        self.using_fallback = False
        self.on_thinking = None  # Callback for UI 
        self.app_callback = None # Callback to add messages to UI
        
    async def chat(self, message: str, user_id: str = "User", input_role: str = "user", save_input: bool = True) -> tuple:
        """
        Send message to LLM and get response.
        Supports multi-turn tool execution (ReAct).
        Returns (final_response_text, emotion, image_prompts, video_prompts).
        """
        # 1. Retrieve Context & History
        if save_input:
            self.memory.add_message(user_id, input_role, message)
        
        if self.on_thinking: self.on_thinking(True)
        
        # RAG Context
        rag_context = ""
        if self.rag and self.rag.is_available():
            try:
                # Offload blocking RAG search to thread
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(None, self.rag.search_memory, message, 1)
                
                if results:
                    rag_context = "\n[MEMORIES]:\n" + results[0]['text']
            except Exception as e:
                logger.warning(f"RAG Async Search Error: {e}")
                pass
                
        history = self.memory.get_history(user_id)
        
        # 2. Main Thinking Loop (Max 3 turns)
        observations = []
        image_prompts = []
        video_prompts = []
        final_response = "I'm a bit confused, Master..."
        
        for turn in range(3):
            # Construct Prompt
            system_prompt = get_system_prompt()
            
            if self.pc:
                system_prompt += "\n\n[TOOLS]:\nUse tags to control PC:\n[OPEN: app]\n[TYPE: text]\n[PRESS: key]\n[CLICK: x, y]\n[WAIT: seconds]\n[SCAN] (See screen)\n[WALLPAPER: image_name]\n[TASK: complex goal] (Hand off to Computer Agent)\n[WEATHER: city]\n[MUSIC: action]\n[LETTER: message]\n[VTS_BG: name] (Change Virtual Room/Background)"
                if self.latex:
                     system_prompt += "\n[LATEX: code] (Compile LaTeX to PDF and save in Downloads)"
            
            if rag_context:
                system_prompt += f"\n\n<relevant_memory_context>\n{rag_context[:1000]}\n</relevant_memory_context>\n[INSTRUCTION: The above is context. Do NOT output it directly. Answer the user as Aiko.]"

            messages = [{"role": "system", "content": system_prompt}]
            
            # Map history to messages (Increased context)
            for h in history[-20:]: 
                role = "user" if h["role"] == "system" else h["role"] # Treat system memory as user input context
                messages.append({"role": role, "content": h["content"]})
            
            # Inject Observations
            if observations:
                obs_text = "\n".join(observations)
                messages.append({"role": "system", "content": f"[OBSERVATIONS]:\n{obs_text}"})
            
            # Call LLM
            text = await self._call_llm(messages, self.model)
            
            # 3. Check for Tools
            if not any(tag in text.upper() for tag in ["[OPEN:", "[SCAN]", "[TYPE:", "[CLICK:", "[TASK:", "[LATEX:", "[NOTE:", "[READ:", "[WRITE:", "[DRAW:", "[VIDEO:"]):
                final_response = text
                break
            
            # Handle Tools
            final_response = text # Fallback
            try:
                if "[SCAN]" in text.upper() and self.vision:
                    desc = await self.vision.scan_screen()
                    observations.append(f"Screen Analysis: {desc}")
                    
                for match in re.finditer(r'\[LATEX\s*:\s*(.*?)\]', text, re.IGNORECASE | re.DOTALL):
                    code = match.group(1).strip()
                    if self.latex:
                        res = await self.latex.compile_to_pdf(code)
                        observations.append(res)

                for match in re.finditer(r'\[TASK\s*:\s*(.*?)\]', text, re.IGNORECASE | re.DOTALL):
                    task = match.group(1).strip()
                    if self.bridge:
                        res = await self.bridge.delegate_to_clawdbot(task)
                        observations.append(f"Clawdbot Sync: {res}")
                
                # Obsidian Tools
                if self.obsidian:
                    for match in re.finditer(r'\[NOTE\s*:\s*(.*?)\]', text, re.IGNORECASE):
                        query = match.group(1).strip()
                        results = self.obsidian.search_notes(query)
                        observations.append(f"Obsidian Search ({query}): {json.dumps(results)}")
                    
                    for match in re.finditer(r'\[READ\s*:\s*(.*?)\]', text, re.IGNORECASE):
                        path = match.group(1).strip()
                        content = self.obsidian.read_note(path)
                        observations.append(f"Obsidian Note ({path}): {content[:1000] if content else 'Not Found'}")

                    for match in re.finditer(r'\[WRITE\s*:\s*(.*?)\s*\|\s*(.*?)\]', text, re.IGNORECASE | re.DOTALL):
                        path = match.group(1).strip()
                        content = match.group(2).strip()
                        success = self.obsidian.create_note(path, content)
                        observations.append(f"Obsidian Write ({path}): {'Success' if success else 'Failed'}")

                for match in re.finditer(r'\[DRAW\s*:\s*(.*?)\]', text, re.IGNORECASE):
                    prompt = match.group(1).strip()
                    if prompt not in image_prompts:
                        image_prompts.append(prompt)
                    break # Strictly 1 per message
                
                for match in re.finditer(r'\[VIDEO\s*:\s*(.*?)\]', text, re.IGNORECASE):
                    prompt = match.group(1).strip()
                    if prompt not in video_prompts:
                        video_prompts.append(prompt)
                    break # Strictly 1 per message
                
                # ... Handle other basic PC tools or Computer Agent ...
                if self.pc:
                    # Generic tool execution loop
                    # For brevity, these would call pc_manager methods
                    pass
                    
            except Exception as e:
                observations.append(f"Tool Error: {e}")
                
        # Clean Final Response from internal tags for the UI
        cleaned_response = re.sub(r'\[TASK:.*?\]', '', final_response, flags=re.IGNORECASE | re.DOTALL)
        cleaned_response = re.sub(r'\[SCAN\]', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\[LATEX:.*?\]', '', cleaned_response, flags=re.IGNORECASE | re.DOTALL)
        cleaned_response = re.sub(r'\[NOTE:.*?\]', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\[READ:.*?\]', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\[WRITE:.*?\]', '', cleaned_response, flags=re.IGNORECASE | re.DOTALL)
        cleaned_response = re.sub(r'\[DRAW:.*?\]', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\[VIDEO:.*?\]', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = cleaned_response.strip()
        
        # Save Response
        self.memory.add_message(user_id, "assistant", cleaned_response)
        
        return cleaned_response, detect_emotion(cleaned_response), image_prompts, video_prompts

    async def ask_raw(self, prompt: str) -> str:
        """Lightweight direct call without history or ReAct loop."""
        messages = [{"role": "system", "content": "You are a JSON Computer Agent helper."}, 
                   {"role": "user", "content": prompt}]
        return await self._call_llm(messages, self.model)

    async def _call_llm(self, messages, model):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if DEEPSEEK_KEY:
                    headers["Authorization"] = f"Bearer {DEEPSEEK_KEY}"
                
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.7}
                }
                async with session.post(LLM_URL, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["message"]["content"]
                    else:
                        error_text = await resp.text()
                        logger.error(f"LLM Error {resp.status}: {error_text}")
                        return f"I'm having trouble thinking, Master... (Error {resp.status}). Are you sure the cloud proxy is running?"
        except Exception as e:
            logger.error(f"Ollama Connection Error: {e}")
            return "My local processors (Ollama) are 404... are you sure it's running?"

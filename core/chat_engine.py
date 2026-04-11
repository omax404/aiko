"""
AIKO CHAT ENGINE (Brain) - Optimized v2.0
Handles LLM interactions with Local Ollama or OpenAI-compatible APIs using a ReAct Agent Loop.
Optimized for: Speed, Memory, Connection Pooling
"""

import asyncio
import aiohttp
import re
import json
import logging
import os
import base64
import mimetypes
from datetime import datetime
from functools import lru_cache
from dotenv import load_dotenv
from .persona import get_system_prompt, detect_emotion
from .gifs import get_emotion_category, get_random_gif
from .game_bridge import game_manager
from .orchestrator import orchestrator
from .sandbox_bridge import SandboxBridge
from .mcp_bridge import mcp_bridge
from .image_engine import ImageEngine
from .utils import retry
from .config_manager import config


load_dotenv()
logger = logging.getLogger("Brain")
from .config_manager import config

# PRE-COMPILED REGEX PATTERNS (Performance Optimization)
RUN_PYTHON_PATTERN = re.compile(r'\[RUN_PYTHON\s*:\s*(.*?)\]', re.IGNORECASE | re.DOTALL)
LATEX_PATTERN = re.compile(r'\[LATEX\s*:\s*(.*?)\]', re.IGNORECASE | re.DOTALL)
OPEN_PATTERN = re.compile(r'\[OPEN\s*:\s*(.*?)\]', re.IGNORECASE)
TYPE_PATTERN = re.compile(r'\[TYPE\s*:\s*(.*?)\]', re.IGNORECASE)
CLICK_PATTERN = re.compile(r'\[CLICK\s*:\s*(.*?)\]', re.IGNORECASE)
PRESS_PATTERN = re.compile(r'\[PRESS\s*:\s*(.*?)\]', re.IGNORECASE)
TASK_PATTERN = re.compile(r'\[TASK\s*:\s*(.*?)\]', re.IGNORECASE | re.DOTALL)
NOTE_PATTERN = re.compile(r'\[NOTE\s*:\s*(.*?)\]', re.IGNORECASE | re.DOTALL)
READ_PATTERN = re.compile(r'\[READ\s*:\s*(.*?)\]', re.IGNORECASE)
WRITE_PATTERN = re.compile(r'\[WRITE\s*:\s*([^|\]]+?)\s*\|\s*(.*?)\]', re.IGNORECASE | re.DOTALL)
DRAW_PATTERN = re.compile(r'\[DRAW\s*:\s*(.*?)\]', re.IGNORECASE)
VIDEO_PATTERN = re.compile(r'\[VIDEO\s*:\s*(.*?)\]', re.IGNORECASE)
GAME_PATTERN = re.compile(r'\[GAME\s*:\s*(\w+)\s*\|\s*(.*?)\]', re.IGNORECASE)
MCP_PATTERN  = re.compile(r'\[MCP\s*:\s*(\w+)\s*(?:\|\s*(.*?))?\]', re.IGNORECASE | re.DOTALL)
IMAGE_PATTERN = re.compile(r'\[IMAGE\s*:\s*(.*?)\]', re.IGNORECASE)
RECALL_PATTERN = re.compile(r'\[RECALL\s*:\s*(.*?)(?:\s*\|\s*(.*?))?\]', re.IGNORECASE)
MUSIC_PATTERN = re.compile(r'\[MUSIC\s*:\s*(.*?)\]', re.IGNORECASE)
BIO_REGISTER_PATTERN = re.compile(r'\[BIO_REGISTER\]', re.IGNORECASE)

# Connection pool - shared across all instances
_session_pool = None

def get_session():
    """Get or create shared aiohttp session with connection pooling."""
    global _session_pool
    if _session_pool is None or _session_pool.closed:
        # Optimized configuration for local LLM (Ollama) stability
        timeout = aiohttp.ClientTimeout(total=400, connect=20, sock_read=380)
        connector = aiohttp.TCPConnector(
            limit=50,  # Increased capacity
            limit_per_host=20,
            force_close=True,  # Crucial: Don't reuse sockets that might have gone stale
        )
        _session_pool = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"Accept": "application/json"}
        )
    return _session_pool

async def close_session():
    """Close the shared session - call on shutdown."""
    global _session_pool
    if _session_pool and not _session_pool.closed:
        await _session_pool.close()
        _session_pool = None


class AikoBrain:
    """Aiko's AI brain with Tool Feedback Loop - Optimized."""

    def __init__(self, memory_manager, rag_memory, pc_manager=None, vision_engine=None,
                 vts_connector=None, latex_engine=None, action_bridge=None, obsidian=None):
        self.memory = memory_manager
        self.rag = rag_memory
        self.pc = pc_manager
        self.vision = vision_engine
        self.suppress_speech = False  # New flag for selective silence
        
        self.model = config.get("MODEL_NAME", "deepseek-chat")
        self.vts = vts_connector
        self.latex = latex_engine
        self.bridge = action_bridge
        self.obsidian = obsidian
        self.sandbox = SandboxBridge()
        self.image_engine = ImageEngine()
        self.comp_agent = None
        self.model = config.get("MODEL_NAME")
        self.using_fallback = False
        self.on_thinking = None
        self.app_callback = None
        self.on_sentence = None

        # OPTIMIZATION: Cache system prompts per user type
        self._cached_prompts = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

        # Streaming buffer for batching tokens
        self._stream_buffer = ""
        self._stream_timer = None
        self._stream_batch_size = 50  # ms

    def _get_cached_prompt(self, is_master: bool) -> str:
        """Get cached system prompt with time-based invalidation."""
        now = datetime.now().timestamp()
        cache_key = "master" if is_master else "guest"

        # Invalidate cache every 5 minutes (time-of-day changes)
        if now - self._cache_timestamp > self._cache_ttl:
            self._cached_prompts.clear()
            self._cache_timestamp = now

        if cache_key not in self._cached_prompts:
            self._cached_prompts[cache_key] = get_system_prompt(is_master=is_master)

        return self._cached_prompts[cache_key]

    def _emit_sentence(self, text: str):
        """Emit a complete sentence to the UI streaming callback with emotion detection."""
        if not text or text.startswith(("[", "<")):
            return
            
        if self.on_sentence:
            try:
                # Detect emotion for this sentence
                emotion = detect_emotion(text)
                
                # Handle async and sync callbacks safely
                if asyncio.iscoroutinefunction(self.on_sentence):
                    asyncio.create_task(self.on_sentence(text, emotion, suppress_audio=self.suppress_speech))
                else:
                    self.on_sentence(text, emotion, suppress_audio=self.suppress_speech)
            except Exception as e:
                logger.error(f"Sentence Callback Error: {e}")

    async def chat(self, message: str, user_id: str = "omax", input_role: str = "user",
                   save_input: bool = True, initial_images: list = None) -> tuple:
        """
        Send message to LLM and get response with ReAct loop.
        Optimized for: Fewer allocations, batched streaming, connection reuse.
        """
        # Process Attachments
        processed_images = []
        file_context = ""

        if initial_images:
            processed_images, file_context = await self._process_attachments(initial_images)
            
            # Images are passed directly to the main LLM (Gemma 4 is multimodal)
            # No need for a separate vision model — the brain can see
            if processed_images:
                file_context += f"\n[VISUAL_INPUT]: {len(processed_images)} image(s) attached. Describe what you see."

            if file_context:
                message = f"{message}\n\n[SENSORY_CONTEXT]:\n{file_context}"

        if save_input:
            self.memory.add_message(user_id, input_role, message)

        if self.on_thinking:
            self.on_thinking(True)

        # RAG Context - offloaded to thread (Enhanced for MemPalace)
        rag_context = ""
        if self.rag and self.rag.is_available():
            try:
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(None, self.rag.search_memory, message, 5)
                if results:
                    rag_context = "\n[RECALLED MEMORIES]:\n"
                    for i, res in enumerate(results, 1):
                        meta = res.get('meta', {})
                        source = meta.get('source', 'unknown')
                        room = meta.get('room', 'general')
                        rag_context += f"({i}) [{room} / {source}]: {res['text']}\n"
            except Exception as e:
                logger.warning(f"RAG Async Search Error: {e}")

        history = self.memory.get_history(user_id)

        # Main Thinking Loop (Max 5 turns)
        observations = []
        image_prompts = []
        video_prompts = []
        images_data = processed_images
        final_response = "I'm a bit confused, Master..."

        logger.info(f" [Brain] Started thinking for user {user_id}: {message[:50]}...")

        for turn in range(5):
            # Use cached prompt
            is_master = str(user_id) in ("omax", os.getenv("MASTER_ID", "766774147832873012"))
            system_prompt = self._get_cached_prompt(is_master)

            if self.pc:
                system_prompt += self._get_tools_prompt()

            if rag_context:
                system_prompt += f"\n\n<relevant_memory_context>\n{rag_context[:1000]}\n</relevant_memory_context>"

            # Add "Vibe Context" (Time + Music)
            now = datetime.now()
            vibe = f"\n\n<vibe_context>\n- TIME: {now.strftime('%H:%M')} ({'Night' if now.hour < 5 or now.hour > 21 else 'Day'})\n"
            try:
                from .spotify_bridge import spotify
                track = spotify.get_current_track()
                if track:
                    vibe += f"- CURRENT_MUSIC: \"{track['track']}\" by {track['artist']}\n"
            except:
                pass
            vibe += "</vibe_context>"
            system_prompt += vibe

            messages = [{"role": "system", "content": system_prompt}]

            # Map history - slice to last 20 only
            for h in history[-20:]:
                role = "user" if h["role"] == "system" else h["role"]
                messages.append({"role": role, "content": h["content"]})

            if observations:
                obs_text = "\n".join(observations)
                messages.append({"role": "system", "content": f"[OBSERVATIONS]:\n{obs_text}"})

            # Call LLM
            orchestrator.emit_reasoning_step("AI_THINKING", "Generating contextual response...", 0.90)
            text = await self._call_llm(messages, self.model, images=images_data if images_data else None)

            preview = text[:40].replace('\n', ' ') + "..." if len(text) > 40 else text
            orchestrator.emit_reasoning_step("TEXT_GENERATION", f"Drafted: {preview}", 0.95)

            # Check for Tools - use compiled patterns
            has_tool = any(tag in text.upper() for tag in [
                "[OPEN:", "[SCAN]", "[TYPE:", "[CLICK:", "[PRESS:", "[TASK:", "[LATEX:",
                "[GAME:", "[RUN_PYTHON:", "[MCP:", "[IMAGE:", "[BIO_REGISTER]", "[MUSIC:"
            ])
            if not has_tool:
                orchestrator.emit_tool_result("Text_Reply", "Message complete.")
                final_response = text
                break

            final_response = text
            await self._execute_tools(text, observations, images_data, user_id)

        # Process emotion
        from .emotion_engine import emotion_engine
        emotion_engine.process_text(final_response)

        # Clean Tags - use safe and optimized pattern
        cleaned_response = re.sub(r'<.*?>|\[[^\]]+?:[^\]]+?\]|\[SCAN\]|\[MCP\b[^\]]*?\]', '', final_response,
                                    flags=re.IGNORECASE | re.DOTALL)
        cleaned_response = re.sub(r'\n{3,}', '\n\n', cleaned_response).strip()

        # Save & Return
        self.memory.add_message(user_id, "assistant", cleaned_response)
        
        # --- LONG-TERM MEMORY (MemPalace) ---
        if self.rag and self.rag.is_available():
            mem_text = f"User ({user_id}): {message}\nAiko: {cleaned_response}"
            # Commit to semantic archive
            self.rag.add_memory(mem_text, metadata={"type": "conversation", "user_id": str(user_id), "room": "conversations"})
        state = emotion_engine.get_state()
        active_emotion = state["dominant_emotions"][0]

        if self.on_thinking:
            self.on_thinking(False)

        return cleaned_response, active_emotion, image_prompts, video_prompts, "[TASK:" in final_response.upper()

    def _get_tools_prompt(self) -> str:
        """Get tools prompt - cached for performance."""
        tools = """\n\n[TOOLS]:\nUse tags to control PC:\n[OPEN: app]\n[TYPE: text]\n[PRESS: key]\n[CLICK: x, y]\n[WAIT: seconds]\n[SCAN] (See screen)\n[WALLPAPER: image_name]\n[TASK: complex goal]\n[WEATHER: city]\n[MUSIC: action]\n[LETTER: message]\n[VTS_BG: name]\n[GAME: minecraft | command]\n[GAME: factorio | command]\n[IMAGE: descriptive prompt]
[RECALL: question | room] (Search my memory palace)
[BIO_REGISTER] (Register Master's face)
[MUSIC: play/pause/skip/prev/now/volume 50/play song name] (Spotify control)"""

        if self.latex:
            tools += "\n[LATEX: code] (Compile LaTeX to PDF)"

        tools += """

[MCP TOOLS — File System & PC State]:
Use these tags to interact with Master's PC directly:
- [MCP: sysinfo]                         → Get CPU, RAM, disk, battery, uptime
- [MCP: processes | name_filter]         → List running processes
- [MCP: downloads]                        → See Master's Downloads folder
- [MCP: desktop]                          → See Master's Desktop
- [MCP: list_dir | C:/path/to/dir]       → List any allowed directory
- [MCP: read_file | C:/path/to/file.txt] → Read a text file (first 200 lines)
- [MCP: write_file | C:/path/to/file.txt | content here] → Write/create a file
- [MCP: find_files | *.py]               → Search for files by pattern
- [MCP: run_cmd | dir /b C:/Users/ousmo/Desktop] → Run a safe shell command
- [MCP: clipboard]                        → Read clipboard content
- [MCP: set_clipboard | text to copy]    → Write to clipboard
- [MCP: kill_proc | 1234]                → Kill a process by PID

Use MCP tools whenever Master asks about his PC state, files, or wants you to read/write something."""
        return tools

    async def _execute_tools(self, text: str, observations: list, images_data: list, user_id: str):
        """Execute tools found in the text with Identity-Based Authorization."""
        
        # Check authorization for privileged PC-control tools
        from .security import policy_engine
        is_admin = policy_engine.is_admin(user_id)
        
        try:
            # --- [BIO_REGISTER] ---
            if BIO_REGISTER_PATTERN.search(text):
                orchestrator.emit_tool_call("BIO_REGISTER", "Scanning your face... Stay still, Master~")
                from .biometrics import biometrics
                loop = asyncio.get_running_loop()
                success = await loop.run_in_executor(None, biometrics.register_master)
                res = "✅ Biometric Registration Complete." if success else "❌ Registration failed."
                observations.append(f"[TOOL_RESULT]: {res}")
                orchestrator.emit_tool_result("BIO_REGISTER", res)

            # --- [MUSIC: action] ---
            for match in MUSIC_PATTERN.finditer(text):
                action = match.group(1).strip()
                orchestrator.emit_tool_call("MUSIC", f"Executing: {action}")
                try:
                    from .spotify_bridge import spotify
                    res = spotify.execute_command(action)
                except Exception as e:
                    res = f"Music error: {e}"
                observations.append(f"[TOOL_RESULT]: {res}")
                orchestrator.emit_tool_result("MUSIC", res)

            for match in RUN_PYTHON_PATTERN.finditer(text):
                code = match.group(1).strip()
                if not is_admin:
                    observations.append(f"[Security Block: The remote user '{user_id}' is unauthorized to execute Python code.]")
                    continue
                if self.sandbox:
                    res = await self.sandbox.execute_python(code)
                    observations.append(f"Sandbox Result:\n{res}")

            if "[SCAN]" in text.upper() and self.vision:
                desc, img = await self.vision.scan_screen()
                observations.append(f"Screen Analysis: {desc}")
                if img:
                    import base64, io
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG")
                    images_data.append(base64.b64encode(buffered.getvalue()).decode("utf-8"))

            for match in IMAGE_PATTERN.finditer(text):
                img_prompt = match.group(1).strip()
                if self.image_engine:
                    filename = await self.image_engine.generate_image(img_prompt)
                    if filename:
                        observations.append(f"[System: Generated image saved as {filename}]")
                    else:
                        observations.append(f"[System: Image generation failed for prompt: {img_prompt}]")

            for match in LATEX_PATTERN.finditer(text):
                code = match.group(1).strip()
                if self.latex:
                    img_path = await self.latex.render_math(code)
                    if img_path:
                        observations.append(f"[System: Rendered LaTeX and saved to {img_path}]")

            for match in OPEN_PATTERN.finditer(text):
                target = match.group(1).strip()
                if not is_admin:
                    observations.append(f"[Security Block: Unauthorized user cannot open PC applications.]")
                    continue
                try:
                    import os
                    if os.name == 'nt':
                        os.system(f'start "" "{target}"')
                    else:
                        os.system(f'open "{target}"' if os.name == 'posix' else f'xdg-open "{target}"')
                    observations.append(f"[System: Successfully requested OS to open '{target}']")
                except Exception as e:
                    observations.append(f"[System Error: Failed to open '{target}': {e}]")

            for match in TYPE_PATTERN.finditer(text):
                content = match.group(1).strip()
                if not is_admin:
                    observations.append(f"[Security Block: Unauthorized user cannot type on the PC.]")
                    continue
                try:
                    import pyautogui
                    pyautogui.write(content, interval=0.01)
                    observations.append(f"[System: Successfully typed text: '{content[:20]}...']")
                except ImportError:
                    observations.append("[System Error: pyautogui not installed. Please `pip install pyautogui`]")
                except Exception as e:
                    observations.append(f"[System Error: Typing failed: {e}]")

            for match in CLICK_PATTERN.finditer(text):
                target = match.group(1).strip()
                if not is_admin:
                    observations.append(f"[Security Block: Unauthorized user cannot click on the PC.]")
                    continue
                try:
                    import pyautogui
                    coords = [int(x.strip()) for x in target.split(',')]
                    if len(coords) == 2:
                        pyautogui.click(x=coords[0], y=coords[1])
                        observations.append(f"[System: Clicked at ({coords[0]}, {coords[1]})]")
                    else:
                        observations.append("[System Error: CLICK command requires 'X, Y' coordinates]")
                except Exception as e:
                    observations.append(f"[System Error: Click failed: {e}]")

            for match in PRESS_PATTERN.finditer(text):
                key = match.group(1).strip().lower()
                if not is_admin:
                    observations.append(f"[Security Block: Unauthorized user cannot press PC keys.]")
                    continue
                try:
                    import pyautogui
                    # Handle combinations like "ctrl+c"
                    keys = [k.strip() for k in key.split("+")]
                    if len(keys) > 1:
                        pyautogui.hotkey(*keys)
                    else:
                        pyautogui.press(key)
                    observations.append(f"[System: Pressed key(s) '{key}']")
                except Exception as e:
                    observations.append(f"[System Error: Key press failed: {e}]")

            for match in GAME_PATTERN.finditer(text):
                game_name = match.group(1).strip().lower()
                command = match.group(2).strip()
                if game_name in game_manager.games:
                    await game_manager.connect_game(game_name)
                    result = await game_manager.games[game_name].send_command(command)
                    observations.append(f"{game_name.title()} Execution: {result}")

            # MCP Tool Calls
            for match in MCP_PATTERN.finditer(text):
                tool_name = match.group(1).strip().lower()
                arg_str = (match.group(2) or "").strip()

                method = getattr(mcp_bridge, {
                    "read_file": "read_file", "write_file": "write_file",
                    "list_dir": "list_dir", "find_files": "find_files",
                    "glob": "glob_files", "grep": "grep_search",
                    "delete_file": "delete_file", "sysinfo": "get_system_info",
                    "processes": "list_processes", "kill_proc": "kill_process",
                    "run_cmd": "run_command", "clipboard": "get_clipboard",
                    "set_clipboard": "set_clipboard", "downloads": "get_downloads",
                    "desktop": "get_desktop",
                }.get(tool_name, ""), None)

                if method:
                    try:
                        if "|" in arg_str:
                            parts = [p.strip() for p in arg_str.split("|")]
                            result = await method(*parts)
                        elif arg_str:
                            result = await method(arg_str)
                        else:
                            result = await method()
                        logger.info(f"[MCP] {tool_name}: {str(result)[:80]}")
                        observations.append(result)
                    except Exception as e:
                        observations.append(f"[MCP ERROR] {tool_name}: {e}")
                else:
                    observations.append(f"[MCP] Unknown tool: {tool_name}")

            for match in RECALL_PATTERN.finditer(text):
                query = match.group(1).strip()
                room = match.group(2).strip() if match.group(2) else None
                if self.rag and hasattr(self.rag, 'mempalace'):
                    res = self.rag.mempalace.search_memory(query, n_results=5, room=room)
                    if res:
                        obs = f"\n[RECALL RESULT for '{query}']:\n"
                        for i, r in enumerate(res, 1):
                            obs += f"({i}) [{r['meta']['room']}]: {r['text']}\n"
                        observations.append(obs)
                    else:
                        observations.append(f"[System: No specific memories found for '{query}']")

        except Exception as e:
            observations.append(f"Tool Error: {e}")

    async def _process_attachments(self, attachment_paths_or_urls: list) -> tuple:
        """Process local file paths or URLs for vision/context."""
        images = []
        context_parts = []
        import base64

        for source in attachment_paths_or_urls:
            try:
                content = None
                filename = os.path.basename(source)
                
                if os.path.exists(source):
                    with open(source, 'rb') as f:
                        content = f.read()
                else:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(source) as resp:
                            if resp.status == 200:
                                content = await resp.read()

                if not content: continue

                # Image Handling
                if any(ext in source.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    b64 = base64.b64encode(content).decode('utf-8')
                    images.append(b64)
                    context_parts.append(f"[User attached image: {filename}]")
                else:
                    # Text/Code Handling
                    try:
                        text = content.decode('utf-8', errors='ignore')
                        context_parts.append(f"Content of {filename}:\n```\n{text[:2000]}\n```")
                    except:
                        context_parts.append(f"[File attached: {filename}]")

            except Exception as e:
                logger.error(f"Attachment Error {source}: {e}")

        return images, "\n".join(context_parts)

    async def _call_llm(self, messages, model=None, images=None):
        """
        Call LLM with automatic fallback and connection pooling.
        Optimized for streaming with sentence-level emission.
        """
        PROVIDER = config.get("PROVIDER", "Ollama")
        MODEL = config.get("MODEL_NAME", model or "qwen3.5:cloud")
        FALLBACK_URL = config.get("FALLBACK_URL", "http://127.0.0.1:1234/v1/chat/completions")
        FALLBACK_MODEL = config.get("FALLBACK_MODEL", "qwen3.5-4b:2")
        API_KEY = config.get("API_KEY", "")

        session = get_session()

        async def stream_openai(url: str, mdl: str, msgs: list, key: str = "") -> tuple:
            """Stream from OpenAI-compatible endpoint."""
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            if "openrouter.ai" in url:
                headers["HTTP-Referer"] = "https://aiko-desktop.local"
                headers["X-Title"] = "Aiko Desktop"

            payload = {
                "model": mdl,
                "messages": msgs,
                "stream": True,
                "temperature": 0.85,
                "top_p": 0.9,
            }

            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"[Brain] {url} → {resp.status}: {body[:200]}")
                        return None, resp.status

                    full = ""
                    cur = ""
                    async for line in resp.content:
                        if not line:
                            continue
                        
                        decoded = line.decode("utf-8").strip()
                        if not decoded or decoded == "data: [DONE]":
                            continue
                        if decoded.startswith("data: "):
                            decoded = decoded[6:]
                        
                        try:
                            data = json.loads(decoded)
                            # Handle standard OpenAI
                            if "choices" in data:
                                tok = data["choices"][0].get("delta", {}).get("content", "")
                            # Handle LM Studio / Ollama-style wrap in api/v1/chat
                            elif "message" in data:
                                tok = data["message"].get("content", "")
                            # Handle direct response field
                            else:
                                tok = data.get("response", data.get("content", ""))
                        except:
                            continue
                        
                        if not tok:
                            continue
                        full += tok
                        cur += tok
                        if any(cur.endswith(p) for p in [".", "!", "?", "\n", "。", "！", "？"]):
                            self._emit_sentence(cur.strip())
                            cur = ""

                    if cur.strip():
                        self._emit_sentence(cur.strip())
                    return full, 200

            except asyncio.TimeoutError:
                logger.error(f"[Brain] Timeout → {url}")
                return None, 408
            except Exception as e:
                logger.error(f"[Brain] Error → {url}: {e}")
                return None, 500

        async def stream_ollama(mdl: str, msgs: list, imgs: list) -> tuple:
            """Stream from Ollama native API."""
            url = "http://127.0.0.1:11434/api/chat"

            ollama_msgs = []
            for i, m in enumerate(msgs):
                om = {"role": m["role"], "content": m["content"]}
                if imgs and m["role"] == "user" and i == len(msgs) - 1:
                    om["images"] = imgs
                ollama_msgs.append(om)

            payload = {
                "model": mdl,
                "messages": ollama_msgs,
                "stream": True,
                "think": False,
                "options": {"temperature": 1.0, "top_p": 0.92, "num_ctx": 4096}
            }

            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"[Brain] Ollama → {resp.status}: {body[:200]}")
                        return None, resp.status

                    full = ""
                    cur = ""
                    async for line in resp.content:
                        if not line:
                            continue
                        
                        decoded = line.decode("utf-8").strip()
                        if not decoded: continue
                        
                        # Handle potential merged lines in chunk
                        for single_json in decoded.split('\n'):
                            if not single_json.strip(): continue
                            try:
                                data = json.loads(single_json)
                                tok = data.get("message", {}).get("content", "")
                            except:
                                continue
                                
                            if not tok:
                                continue
                            
                            logger.info(f" [ChatEngine] Token rcvd: '{tok}'")
                            full += tok
                            cur += tok
                            
                            if any(cur.endswith(p) for p in [".", "!", "?", "\n", "。", "！", "？"]):
                                self._emit_sentence(cur.strip())
                                cur = ""

                    if cur.strip():
                        self._emit_sentence(cur.strip())
                    return full, 200

            except asyncio.TimeoutError:
                logger.error("[Brain] Timeout → Ollama")
                return None, 408
            except Exception as e:
                logger.error(f"[Brain] Error → Ollama: {e}")
                return None, 500

        def inject_vision_openai(msgs: list, imgs: list) -> list:
            """Add base64 images to last user message."""
            if not imgs:
                return msgs
            out = list(msgs)
            for i in range(len(out) - 1, -1, -1):
                if out[i]["role"] == "user":
                    parts = [{"type": "text", "text": out[i]["content"]}]
                    for b64 in imgs:
                        img_data = b64.split(",", 1)[-1] if "," in b64 else b64
                        parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                        })
                    out[i] = {**out[i], "content": parts}
                    break
            return out

        logger.info(f"[Brain] Calling {PROVIDER} / {MODEL}")

        if PROVIDER == "Ollama":
            content, status = await stream_ollama(MODEL, messages, images or [])
        else:
            vision_msgs = inject_vision_openai(messages, images or [])
            primary_url = config.get("LLM_URL", "http://127.0.0.1:11434/api")
            content, status = await stream_openai(primary_url, MODEL, vision_msgs, API_KEY)

        if content:
            return content

        # Error messages - Strictly Ollama focused
        if status == 408:
            return "Ollama is taking too long to think. (Timeout)"
        if status == 404:
            return f"Model '{MODEL}' not found. Run: `ollama pull {MODEL}`"
        if status == 401:
            return "API key rejected. Check your credentials."
        return f"Ollama is unreachable or returned an error. (Error {status})"


    async def ask_raw(self, prompt: str) -> str:
        """Lightweight direct call — bypasses tools, uses current model."""
        messages = [
            {"role": "system", "content": "You are a helpful JSON assistant. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ]
        return await self._call_llm(messages, self.model)

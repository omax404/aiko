
"""
AIKO NEURAL HUB (Master Server) v2.0
─────────────────────────────────────
The single point of intelligence for the entire Aiko ecosystem.
Now with: Message Queue integration, Unified Memory, and Auto-restart
"""

import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import asyncio
import os
import sys
import time
import json
import logging
import mimetypes
import threading
import signal
from pathlib import Path
from aiohttp import web
import aiohttp
from datetime import datetime

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s"
)
logger = logging.getLogger("NeuralHub")

# Project Root
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

# Aiko Core Imports
from core.chat_engine import AikoBrain
from core.memory import MemoryManager
from core.rag_memory import RAGMemorySystem
from core.clawdbot_bridge import AikoActionBridge
from core.vision import VisionEngine
from core.persona import detect_emotion
from core.latex_engine import LatexEngine
from core.config_manager import config
from core.emotion_engine import emotion_engine
from core.voice import VoiceEngine
from core.hearing import HearingEngine
from core.autonomous_agent import autonomous_agent
from core.pc_manager import PCManager
from core.startup_manager import startup_manager
from core.message_queue import get_queue, send_response
from core.unified_memory import get_unified_memory
from core.proactive import ProactiveAgent
from core.bot_manager import start_all_satellites
from core.obsidian_connector import ObsidianConnector

# ═══════════════════════════════════════════════════════════════
# UI UPDATES & BROADCASTING
# ═══════════════════════════════════════════════════════════════

ws_clients = set()
start_time = time.time()

async def broadcast_event(e_type: str, data: dict):
    """Send live updates to all connected UI clients - Optimized with batch cleanup."""
    if not ws_clients:
        return

    msg = json.dumps({"type": e_type, "data": data})
    dead = set()

    # Use gather for concurrent sends to all connected clients
    tasks = []
    for ws in ws_clients:
        try:
            tasks.append(ws.send_str(msg))
        except:
            dead.add(ws)

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for ws, result in zip([w for w in ws_clients if w not in dead], results):
            if isinstance(result, Exception):
                dead.add(ws)

    # Batch cleanup of dead sockets
    if dead:
        ws_clients.difference_update(dead)

# ═══════════════════════════════════════════════════════════════
# SINGLE INSTANCE INITIALIZATION
# ═══════════════════════════════════════════════════════════════
logger.info("🧠 Initializing Neural Hub v2.0...")

# Initialize Message Queue for bot communication
msg_queue = get_queue()
logger.info("📬 Message Queue initialized")

# Initialize Unified Memory (thoughts + conversations + file links)
unified_memory = get_unified_memory()
unified_memory.think(
    "Neural Hub starting up. Systems coming online...",
    category="observation",
    importance=8
)
logger.info("🧠 Unified Memory initialized")

# Legacy memory for compatibility
memory = MemoryManager()

# RAG will be local here, as this IS the hub
os.environ["REMOTE_RAG_URL"] = ""
rag = RAGMemorySystem()
bridge = AikoActionBridge()
latex = LatexEngine()
vision = VisionEngine()
pc = PCManager()
voice_engine = VoiceEngine()
hearing_engine = HearingEngine()
obsidian = ObsidianConnector(vault_path=config.get("obsidian_path", ""))

# Initialize Proactive Agent
proactive_agent = ProactiveAgent(brain=None, vision=vision, pc_manager=pc, voice=voice_engine)

# OPTIMIZED: Create brain with cached prompts
brain = AikoBrain(
    memory_manager=memory,
    rag_memory=rag,
    pc_manager=pc,
    vision_engine=vision,
    vts_connector=None,
    action_bridge=bridge,
    latex_engine=latex,
    obsidian=obsidian
)

# Link components to proactive agent
proactive_agent.brain = brain
proactive_agent.obsidian = obsidian

# Late binding of brain to proactive agent and toggle state
proactive_agent.brain = brain
proactive_agent._broadcast = broadcast_event  # Wire broadcast so it can send to UI
if config.get("proactive_mode", True):
    proactive_agent.toggle(True)

# Register self in process registry
msg_queue.register_process("neural_hub", os.getpid())
logger.info(f"✅ Neural Hub registered (PID: {os.getpid()})")

STAR_OFFICE_URL = "http://127.0.0.1:19000"

async def sync_star_office(state: str, detail: str = ""):
    """Sync state with Star Office UI."""
    try:
        async with aiohttp.ClientSession() as sess:
            payload = {"state": state, "detail": detail}
            async with sess.post(f"{STAR_OFFICE_URL}/set_state", json=payload, timeout=2) as r:
                return r.status == 200
    except:
        return False

USER_ID = "omax"

# --- Callbacks ---
async def broadcast_amplitude(amp: float):
    """Sends tts_amplitude event to all UI clients for lip sync."""
    await broadcast_event("tts_amplitude", {"amplitude": amp})

async def _on_sentence(sentence: str, emotion: str = "neutral", suppress_audio: bool = False):
    """Vocalization callback — handles UI streaming and TTS triggering."""
    # 1. Stream token and emotion to UI immediately
    await broadcast_event("chat_token", {"token": sentence, "text": sentence, "emotion": emotion})
    await broadcast_event("emotion", {"emotion": emotion})
    await broadcast_event("tts_chunk", {"text": sentence})
    
    # 2. Trigger TTS if enabled
    if config.get("TTS_ENABLED", True):
        async def broadcast_audio(filename: str):
            await broadcast_event("tts_audio", {
                "url": f"/api/tts/audio/{filename}",
                "text": sentence
            })

        # We use create_task to avoid blocking the streaming response
        if not suppress_audio:
            asyncio.create_task(
                voice_engine.speak(sentence, emotion=emotion, on_amplitude=broadcast_amplitude, on_audio=broadcast_audio)
            )
        else:
            logger.info(f" [Hub] Speech suppressed for: {sentence[:30]}...")

def sync_on_sentence(sentence: str, emotion: str = "neutral", suppress_audio: bool = False):
    """Sync wrapper to fire the async callback without blocking"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_on_sentence(sentence, emotion, suppress_audio))
    except RuntimeError:
        pass

brain.on_sentence = sync_on_sentence


# ═══════════════════════════════════════════════════════════════
# MESSAGE QUEUE PROCESSING (Discord/Telegram Integration)
# ═══════════════════════════════════════════════════════════════

async def process_queue_messages():
    """Background task: Process messages from Discord/Telegram bots."""
    while True:
        try:
            # Process Discord messages
            discord_msg = msg_queue.dequeue_one('discord_in', processor_id='neural_hub')
            if discord_msg:
                payload = discord_msg['payload']
                user_id = payload.get('user_id', 'discord_user')
                message = payload.get('message', '')

                logger.info(f"[Queue] Processing Discord message from {user_id}: {message[:50]}...")

                # Process through Aiko brain
                reply, emotion, *_ = await brain.chat(message, user_id=user_id)

                # Send response back to Discord queue
                send_response('discord', user_id, reply, emotion)

                # Log thought
                unified_memory.think(
                    f"Responded to Discord user {user_id}: {reply[:100]}...",
                    category='observation',
                    related_memories=[user_id],
                    emotion=emotion,
                    importance=5
                )

                # Acknowledge message
                msg_queue.acknowledge(discord_msg['id'])

            # Process Telegram messages
            telegram_msg = msg_queue.dequeue_one('telegram_in', processor_id='neural_hub')
            if telegram_msg:
                payload = telegram_msg['payload']
                user_id = payload.get('user_id', 'telegram_user')
                message = payload.get('message', '')

                logger.info(f"[Queue] Processing Telegram message from {user_id}: {message[:50]}...")

                reply, emotion, *_ = await brain.chat(message, user_id=user_id)

                send_response('telegram', user_id, reply, emotion)

                unified_memory.think(
                    f"Responded to Telegram user {user_id}: {reply[:100]}...",
                    category='observation',
                    related_memories=[user_id],
                    emotion=emotion,
                    importance=5
                )

                msg_queue.acknowledge(telegram_msg['id'])

            # Heartbeat
            msg_queue.heartbeat('neural_hub')

            # Cleanup old messages every hour (only once per minute 0)
            now = datetime.now()
            if now.minute == 0 and not getattr(process_queue_messages, 'last_cleanup_minute', -1) == 0:
                msg_queue.cleanup_old_data(max_age_hours=24)
                process_queue_messages.last_cleanup_minute = 0
            elif now.minute != 0:
                process_queue_messages.last_cleanup_minute = now.minute

            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"[Queue] Processing error: {e}")
            await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET OPTIMIZATIONS
# ═══════════════════════════════════════════════════════════════

# --- Routes ---

async def handle_status(req):
    """Deep system health check."""
    from core.spotify_bridge import spotify
    status = {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "brain": "ready" if brain else "offline",
        "vision": "ready" if vision else "offline",
        "voice": "ready" if voice_engine.is_available() else "loading",
        "spotify": "connected" if spotify.is_ready else "offline",
        "active_clients": len(ws_clients),
        "uptime_snapshot": time.time() - start_time
    }
    return web.json_response(status)

async def handle_health(req):
    """Deep health check for bridges and LLM."""
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bridges": {
            "mcp": "online" if bridge else "offline",
            "vision": "online" if vision else "offline"
        },
        "llm_provider": config.get("PROVIDER", "Unknown")
    }
    return web.json_response(health)

async def handle_sessions(req):
    """List all available chat sessions with recency and pinning."""
    try:
        sessions = memory.get_recent_sessions()
        return web.json_response({"sessions": sessions})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_rename_session(req):
    try:
        data = await req.json()
        sid = data.get("id")
        name = data.get("name")
        if memory.rename_session(sid, name):
            return web.json_response({"status": "success"})
        return web.json_response({"error": "Session not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_pin_session(req):
    try:
        data = await req.json()
        sid = data.get("id")
        # memory.py doesn't have pin_session yet, I'll add it or simulate it
        if hasattr(memory, 'pin_session'):
            if memory.pin_session(sid):
                return web.json_response({"status": "success"})
        return web.json_response({"error": "Endpoint not implemented"}, status=501)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_delete_session(req):
    try:
        sid = req.query.get("id")
        if memory.delete_session(sid):
            return web.json_response({"status": "success"})
        return web.json_response({"error": "Session not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_history(req):
    """Get full history for a specific session."""
    try:
        # Support both ?id= and ?uid= (frontend uses uid)
        sid = req.query.get("uid") or req.query.get("id") or USER_ID
        mem, uid = memory.get_user_data(sid)
        return web.json_response({"history": mem[uid]["history"]})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_chat_api(req):
    """Synchronous API for Bots (Discord/Telegram)."""
    try:
        data = await req.json()
        msg = data.get("message", "").strip()
        uid = data.get("user_id", USER_ID)
        attachments = data.get("attachments", [])
        
        if not msg and not attachments: return web.json_response({"error": "Empty message"}, status=400)
        
        # Broadcast that Aiko is thinking
        await broadcast_event("state", {"thinking": True, "source": "api"})
        await sync_star_office("researching", f"Thinking about: {msg[:20]}...")
        
        reply, *_ = await brain.chat(msg, user_id=uid, initial_images=attachments)
        emotion = detect_emotion(reply)
        
        audio_filename = None
        if config.get("TTS_ENABLED", True):
            async def _on_audio(fname):
                nonlocal audio_filename
                audio_filename = fname
            await voice_engine.speak(reply, emotion=emotion, on_audio=_on_audio)
            
        await broadcast_event("state", {"thinking": False})
        await sync_star_office("idle", "Waiting for command...")
        
        return web.json_response({
            "response": reply,
            "emotion": emotion,
            "audio_url": f"http://127.0.0.1:8000/api/tts/audio/{audio_filename}" if audio_filename else None,
            "audio_path": os.path.join(os.getcwd(), "data", "voices", audio_filename) if audio_filename else None,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Brain Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_ws(req):
    """Real-time Streaming & UI Bridge."""
    ws = web.WebSocketResponse()
    await ws.prepare(req)
    ws_clients.add(ws)
    logger.info(f" [Hub] New WS Client connected. Total: {len(ws_clients)}")
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                m_type = data.get("type")
                
                if m_type == "chat":
                    text = data.get("text", "")
                    uid = data.get("session_id") or data.get("user_id", USER_ID)
                    attachments = data.get("attachments", [])

                    async def _process_chat(text, uid, attachments):
                        # Broadcast chat_start so UI shows thinking state
                        await broadcast_event("chat_start", {"role": "user", "text": text})
                        await sync_star_office("researching", "Processing user request...")

                        original_on_sentence = brain.on_sentence

                        def _bridge_sentence(s, emotion="neutral"):
                            try:
                                logger.info(f" [Hub] Generating token: '{s}'")
                                loop = asyncio.get_running_loop()
                                loop.create_task(_on_sentence(s, emotion))
                            except Exception as ex:
                                logger.error(f" [Hub] Bridge Error: {ex}")
                                
                        brain.on_sentence = _bridge_sentence

                        try:
                            reply, active_emotion, *_ = await brain.chat(text, user_id=uid, initial_images=attachments)
                        except Exception as e:
                            logger.error(f"Brain Chat Error: {e}")
                            reply = f"Neural Error: {e}"
                            active_emotion = "sad"
                        finally:
                            brain.on_sentence = original_on_sentence

                        await sync_star_office("idle", "Resting...")
                        await broadcast_event("chat_end", {
                            "role": "assistant",
                            "text": reply,
                            "content": reply,
                            "emotion": active_emotion
                        })
                    asyncio.create_task(_process_chat(text, uid, attachments))

                elif m_type == "speak":
                    text = data.get("text", "")
                    emotion = data.get("emotion") or detect_emotion(text)
                    logger.info(f" [Hub] UI requested manual speak: {text[:30]}...")
                    asyncio.create_task(voice_engine.speak(text, emotion=emotion, on_amplitude=broadcast_amplitude))

                elif m_type == "branch":
                    text = data.get("text", "")
                    msg_id = data.get("message_id")
                    uid = data.get("session_id") or data.get("user_id", USER_ID)
                    attachments = data.get("attachments", [])

                    async def _process_branch(text, msg_id, uid, attachments):
                        # 1. Truncate history
                        mem, user_key = memory.get_user_data(uid)
                        idx = -1
                        for i, m in enumerate(mem[user_key]["history"]):
                            if str(m.get("timestamp", "")) == str(msg_id) or str(m.get("id", "")) == str(msg_id):
                                idx = i
                                break
                        if idx != -1:
                            memory.truncate_history(uid, idx)

                        # 2. Proceed exactly like a chat message
                        await broadcast_event("chat_start", {"role": "user", "text": text})
                        await sync_star_office("researching", "Branching timeline...")

                        async def _conn_stream(s: str):
                            await ws.send_str(json.dumps({"type": "chat_token", "data": {"token": s, "text": s}}))

                        original_on_sentence = brain.on_sentence
                        brain.on_sentence = lambda s: asyncio.run_coroutine_threadsafe(
                            _conn_stream(s), asyncio.get_event_loop()
                        )

                        try:
                            reply, active_emotion, *_ = await brain.chat(text, user_id=uid, initial_images=attachments)
                        except Exception as e:
                            logger.error(f"Brain Chat Error: {e}")
                            reply = f"Neural Error: {e}"
                            active_emotion = "sad"
                        finally:
                            brain.on_sentence = original_on_sentence

                        await sync_star_office("idle", "Resting...")
                        await broadcast_event("chat_end", {
                            "role": "assistant",
                            "text": reply,
                            "content": reply,
                            "emotion": active_emotion
                        })
                    asyncio.create_task(_process_branch(text, msg_id, uid, attachments))
                

                elif m_type == "ping":
                    await ws.send_str(json.dumps({"type": "pong"}))
                
                elif m_type == "listen":
                    # STT Request
                    await broadcast_event("state", {"listening": True})
                    text = await hearing_engine.listen_async()
                    await broadcast_event("state", {"listening": False})
                    
                    if text:
                        # Send it back to the UI as recognized text so it can trigger chat
                        await ws.send_str(json.dumps({"type": "stt_result", "text": text}))
                    else:
                        await ws.send_str(json.dumps({"type": "stt_result", "text": ""}))

                elif m_type == "vts_sync":
                    pass

    finally:
        ws_clients.discard(ws)
        logger.info(f" [Hub] Client disconnected.")
    return ws

# --- Startup ---

async def on_startup(app):
    logger.info("✨ Neural Hub is warm and ready.")
    logger.info("🚀 Initiating Aiko Background Startup Sequence...")

    # Start message queue processing
    asyncio.create_task(process_queue_messages())
    logger.info("📬 Message Queue processor started")

    # Start unified memory auto-save
    asyncio.create_task(memory_autosave_loop())
    logger.info("💾 Memory auto-save started")

    # Start Consolidated Satellites (Discord/Telegram)
    asyncio.create_task(start_all_satellites())

    # MemPalace Wake-up & Indexing
    if hasattr(rag, 'mempalace') and rag.mempalace.is_available():
        _loop = asyncio.get_running_loop()
        logger.info("🌅 Palace Wake-up sequence initiated...")
        _loop.run_in_executor(None, rag.mempalace.wake_up)
        # Optional: Mine the project on startup to ensure latest files are indexed
        _loop.run_in_executor(None, rag.mempalace.mine_project, "./")
        
        # Obsidian Vault Mining
        if obsidian and obsidian.is_valid:
            logger.info(" [Obsidian] ⛏️ Vault Mining initiated...")
            _loop.run_in_executor(None, obsidian.mine_vault, rag.mempalace)

    # Start proactive agent loop
    asyncio.create_task(proactive_agent.start_loop())
    logger.info("👁️ Proactive Agent loop started")

    # Legacy startup
    startup_manager.launch_all()

    # Pre-warm TTS in background so first speak() is fast
    if config.get("TTS_ENABLED", True):
        logger.info("🔊 Pre-warming TTS model in background...")
        voice_engine.start_warmup()

    # Log startup thought
    unified_memory.think(
        "All systems online! Ready to serve Master.",
        category="observation",
        importance=9,
        emotion="excited"
    )


async def memory_autosave_loop():
    """Periodically save unified memory to disk."""
    while True:
        await asyncio.sleep(60)  # Every minute
        try:
            unified_memory.save()
        except Exception as e:
            logger.error(f"[Memory] Autosave error: {e}")
            
        # Periodic Project/Obsidian Mining (Every 30 mins)
        try:
            now = time.time()
            if not hasattr(memory_autosave_loop, "last_mine"):
                memory_autosave_loop.last_mine = now
            
            if now - memory_autosave_loop.last_mine > 1800:
                logger.info(" [Hub] ⛏️ Periodic Re-Mining Started...")
                _loop = asyncio.get_running_loop()
                _loop.run_in_executor(None, rag.mempalace.mine_project, "./")
                if obsidian and obsidian.is_valid:
                    _loop.run_in_executor(None, obsidian.mine_vault, rag.mempalace)
                memory_autosave_loop.last_mine = now
            
            # Periodic Cache Cleanup (Every 6 hours)
            if not hasattr(memory_autosave_loop, "last_cleanup"):
                memory_autosave_loop.last_cleanup = now
                
            if now - memory_autosave_loop.last_cleanup > 21600:
                logger.info(" [Hub] 🧹 Auto-Cache Cleanup Started...")
                from .utils import clear_cache
                _loop.run_in_executor(None, clear_cache)
                memory_autosave_loop.last_cleanup = now
        except Exception as e:
            logger.error(f"[Hub] Periodic Mine error: {e}")

async def handle_purge(req):
    """Clean system caches and session memory."""
    try:
        memory.clear_cache()
        await broadcast_event("state", {"info": "SYSTEM_PURGE_COMPLETE"})
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_update_settings(req):
    """Persist UI settings to config.json."""
    try:
        data = await req.json()
        config.update(data)
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
    
async def handle_upload(req):
    """Handle multipart file uploads."""
    try:
        reader = await req.multipart()
        field = await reader.next()
        if not field or field.name != 'file':
            return web.json_response({"error": "No file field found"}, status=400)
        
        filename = field.filename
        # Sanitize filename
        filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in ('.', '_', '-')]).strip()
        if not filename:
            filename = f"upload_{int(datetime.now().timestamp())}"
            
        upload_path = BASE / "uploads"
        upload_path.mkdir(exist_ok=True)
        
        filepath = upload_path / filename
        # Ensure unique name
        if filepath.exists():
            filename = f"{int(datetime.now().timestamp())}_{filename}"
            filepath = upload_path / filename
            
        size = 0
        with open(filepath, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                size += len(chunk)
                f.write(chunk)
                
        logger.info(f"File uploaded: {filename} ({size} bytes)")
        return web.json_response({
            "status": "success",
            "filename": filename,
            "url": f"http://127.0.0.1:8000/uploads/{filename}",
            "type": mimetypes.guess_type(filename)[0] or "application/octet-stream"
        })
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_project_structure(req):
    """Recursively list project files for 'Project Intelligence'."""
    try:
        import os
        root = os.getcwd()
        structure = []
        ignored = {'.git', '.venv', 'node_modules', '__pycache__', '.logs', '.next', '.tauri', '.agent'}
        
        for item in os.listdir(root):
            if item in ignored: continue
            path = os.path.join(root, item)
            structure.append({
                "name": item,
                "type": "folder" if os.path.isdir(path) else "file",
                "path": path,
                "size": os.path.getsize(path) if os.path.isfile(path) else 0
            })
        return web.json_response({"structure": structure})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_relationship(req):
    """Get relationship data and affection level."""
    try:
        uid = req.query.get("id", USER_ID)
        stats = memory.get_stats(uid)
        return web.json_response({
            "affection": stats.get("affection", 0),
            "level": "Neural Link Active",
            "trust": 85
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_bridge_status(req):
    """Proxy to check if OpenClaw bridge is alive on 8765."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:8765/status", timeout=2) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return web.json_response({"status": "connected", "data": data})
                return web.json_response({"status": "error", "code": resp.status})
    except Exception as e:
        return web.json_response({"status": "disconnected", "error": str(e)})

async def handle_latex_render(req):
    """Render a LaTeX snippet to a high-res image."""
    try:
        data = await req.json()
        snippet = data.get("snippet", "").strip()
        if not snippet:
             return web.json_response({"error": "No snippet provided"}, status=400)
        
        logger.info(f" [Latex] Rendering snippet: {snippet[:50]}...")
        path, err = await latex.render_snippet(snippet)
        if err:
             logger.error(f" [Latex] Render Error: {err}")
             return web.json_response({"error": err}, status=500)
        
        filename = os.path.basename(path)
        logger.info(f" [Latex] Successfully rendered: {filename}")
        return web.json_response({
            "url": f"/api/latex/image/{filename}",
            "path": path
        })
    except Exception as e:
        logger.error(f" [Latex] Fatal Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_latex_image(req):
    """Serve the rendered LaTeX image."""
    filename = req.match_info['filename']
    filepath = os.path.join(latex.output_dir, filename)
    if not os.path.exists(filepath):
        return web.HTTPNotFound()
    return web.FileResponse(filepath)

def build_hub_app():
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == "OPTIONS":
            resp = web.Response()
        else:
            try:
                resp = await handler(request)
            except Exception as e:
                resp = web.json_response({"error": str(e)}, status=500)
        origin = request.headers.get("Origin", "*")
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, PATCH, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        return resp

    app = web.Application(middlewares=[cors_middleware])
    app.on_startup.append(on_startup)
    app.router.add_get("/status", handle_status)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/api/sessions", handle_sessions)
    app.router.add_post("/api/sessions/rename", handle_rename_session)
    app.router.add_post("/api/sessions/pin", handle_pin_session)
    app.router.add_delete("/api/sessions/delete", handle_delete_session)
    app.router.add_get("/api/history", handle_history)
    app.router.add_get("/api/relationship", handle_relationship)
    app.router.add_get("/api/status", handle_status)
    app.router.add_post("/api/chat", handle_chat_api)
    app.router.add_post("/api/purge", handle_purge)
    app.router.add_post("/api/settings", handle_update_settings)
    app.router.add_get("/api/project/structure", handle_project_structure)
    app.router.add_get("/api/bridge/status", handle_bridge_status)
    app.router.add_post("/api/latex/render", handle_latex_render)
    app.router.add_get("/api/latex/image/{filename}", handle_latex_image)
    app.router.add_post("/api/upload", handle_upload)
    app.router.add_post("/api/store", lambda r: web.json_response({"ok": False, "msg": "Use RAG API"})) # Legacy
    app.router.add_get("/ws", handle_ws)
    
    # Serve stickers folder for image generation items
    stickers_path = BASE / "stickers"
    stickers_path.mkdir(exist_ok=True)
    app.router.add_static("/stickers", str(stickers_path), show_index=True)
    
    # Store temporary voice files for web playback
    temp_voice_path = BASE / "data" / "voices"
    temp_voice_path.mkdir(parents=True, exist_ok=True)
    app.router.add_static("/api/tts/audio", str(temp_voice_path), show_index=True)

    # Serve uploads folder
    uploads_path = BASE / "uploads"
    uploads_path.mkdir(exist_ok=True)
    app.router.add_static("/uploads", str(uploads_path), show_index=True)
    
    # --- Public Web UI Serving ---
    dist_path = BASE / "dist"
    if not dist_path.exists():
        dist_path = BASE / "aiko-app" / "dist"

    if dist_path.exists():
        logger.info(f"Serving Public UI from {dist_path}")
        
        # 1. Serve specific assets folder first
        if (dist_path / "assets").exists():
            app.router.add_static("/assets", str(dist_path / "assets"), show_index=False)
        
        # 2. Serve other static folders known by Aiko
        for folder in ["live2d", "icons", "stickers"]:
            if (dist_path / folder).exists():
                app.router.add_static(f"/{folder}", str(dist_path / folder), show_index=False)

        # 3. Main entry point (the face)
        async def handle_index(req):
            return web.FileResponse(dist_path / "index.html")
        app.router.add_get("/", handle_index)
        
        # 4. Fallback for SPA routing (only if it doesn't start with /api)
        @web.middleware
        async def spa_middleware(request, handler):
            try:
                return await handler(request)
            except web.HTTPNotFound:
                if not request.path.startswith("/api") and not request.path.startswith("/ws"):
                    return web.FileResponse(dist_path / "index.html")
                raise
        
        app.middlewares.append(spa_middleware)
    
    # --- Background Tasks ---
    async def knowledge_ingestion_loop():
        """Watches data/knowledge/ and auto-ingests new files."""
        knowledge_dir = BASE / "data" / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        ingested_files = set()
        logger.info("[RAG] 📚 Knowledge Ingestion Task Started.")
        
        while True:
            try:
                for file in knowledge_dir.iterdir():
                    if file.is_file() and file.name not in ingested_files:
                        logger.info(f"[RAG] 📖 Ingesting: {file.name}")
                        if rag.ingest_document(str(file)):
                            ingested_files.add(file.name)
                            logger.info(f"[RAG] ✅ Ingested {file.name}")
            except Exception as e:
                logger.error(f"[RAG] ❌ Ingestion error: {e}")
            
            await asyncio.sleep(60) # Check every minute

    async def start_background_tasks(app):
        app['knowledge_task'] = asyncio.create_task(knowledge_ingestion_loop())
    
    async def cleanup_background_tasks(app):
        app['knowledge_task'].cancel()
        await app['knowledge_task']
        
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    return app

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    # Ensure data directory
    (BASE / "data").mkdir(exist_ok=True)
    
    # PID Lock
    lock_file = BASE / "data" / "neural_hub.lock"
    if lock_file.exists():
        try: os.remove(lock_file)
        except: pass
    
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))
        
    # Graceful Shutdown Handler
    def signal_handler(sig, frame):
        logger.info("\n🛑 Shutdown signal received. Closing Aiko gracefully...")
        try:
            unified_memory.think("Master is closing me... Time to sleep. See you later! 💖", emotion="shy")
            unified_memory.save()
            logger.info("💾 Memories saved. Bye!")
        except:
            pass
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        web.run_app(build_hub_app(), host=args.host, port=args.port, print=lambda x: logger.info(x))
    except OSError as e:
        if e.errno in (10048, 98): # Windows and Linux "Address already in use"
            logger.warning(f" [!] Port {args.port} is already in use.")
            import http.client
            try:
                conn = http.client.HTTPConnection("127.0.0.1", args.port, timeout=5)
                conn.request("GET", "/status")
                if conn.getresponse().status == 200:
                    logger.info(f" [OK] Confirmed existing Neural Hub is healthy on port {args.port}. Exiting.")
                    sys.exit(0)
            except:
                logger.warning(f" [!] Port {args.port} occupied but status check failed. Exiting to prevent collision.")
                sys.exit(0)
        else:
            raise e
    finally:
        if lock_file.exists(): lock_file.unlink()

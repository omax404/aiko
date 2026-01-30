
import flet as ft
import asyncio
import os
import json
import logging
import datetime
import urllib.parse

# Core Modules
from core.chat_engine import AikoBrain
from core.memory import MemoryManager
from core.rag_memory import RAGMemorySystem
from core.vision import VisionEngine
from core.voice import VoiceEngine
from core.vts_connector import VTSConnector
from core.system_monitor import SystemMonitor
from core.config_manager import ConfigManager
from core.clawdbot_bridge import AikoActionBridge
from core.callback_server import AikoCallbackServer
from core.agency import AikoMultiPlatformBridge
from core.obsidian_connector import ObsidianConnector
from core.latex_engine import LatexEngine

# UI Components
from ui.components import FigmaSidebar, ChatBubble, ModernInputDock, SystemDashboard, COLORS, SettingsModal, ImageBubble

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AikoMain")

class AikoDesktop:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config = ConfigManager()
        self.setup_window()
        
        # State
        self.current_user_name = self.config.get("username", "omax")
        self.vts_port = self.config.get("vts_port", "8001")
        self.tts_enabled = self.config.get("tts_enabled", True)
        self.obsidian_path = self.config.get("obsidian_path", "")
        self.is_thinking = False
        self.proactive_mode = self.config.get("proactive_mode", False)
        self.current_chat_id = "default"
        
        # Engines
        self.init_engines()
        
        # UI
        self.setup_layout()
        
        # Initial Population
        self.populate_sidebar()
        self.load_active_chat()
        
        # Start background tasks
        asyncio.create_task(self.update_stats_loop())
        
        # Agency Platforms
        self.agency = AikoMultiPlatformBridge(self.brain, self.config)
        self.agency.start_all()
        
        # Start Callback Server for Clawdbot
        self.callback_server = AikoCallbackServer(
            port=8002, 
            callback_handler=self.handle_clawdbot_notification,
            loop=asyncio.get_event_loop()
        )
        self.callback_server.start()

    def setup_window(self):
        self.page.title = "Aiko Desktop | Virtual Assistant"
        self.page.bgcolor = COLORS["bg_layer_1"]
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_width = 1280
        self.page.window_height = 800
        self.page.window_resizable = True
        self.page.fonts = {
            "Pixelify Sans": "fonts/PixelifySans-Regular.ttf",
            "Pixelify Sans Bold": "fonts/PixelifySans-Bold.ttf",
        }

    def init_engines(self):
        self.memory = MemoryManager()
        self.rag = RAGMemorySystem()
        self.vision = VisionEngine()
        self.voice = VoiceEngine()
        self.vts = VTSConnector(port=self.vts_port)
        self.monitor = SystemMonitor()
        self.bridge = AikoActionBridge()
        self.obsidian = ObsidianConnector(vault_path=self.obsidian_path)
        self.latex_engine = LatexEngine()
        
        self.brain = AikoBrain(
            memory_manager=self.memory,
            rag_memory=self.rag,
            vision_engine=self.vision,
            vts_connector=self.vts,
            action_bridge=self.bridge,
            obsidian=self.obsidian,
            latex_engine=self.latex_engine
        )
        self.brain.on_thinking = self.set_thinking_state

    def setup_layout(self):
        # Sidebar
        self.sidebar = FigmaSidebar(
            on_new_chat=self.handle_new_chat,
            on_settings=self.handle_settings
        )
        
        # Chat History
        self.chat_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=20,
            auto_scroll=True
        )
        
        # Input Dock
        self.input_dock = ModernInputDock(
            on_send=self.handle_send,
            on_voice=self.handle_voice_input,
            on_screen_scan=self.handle_screen_scan,
            on_camera_scan=lambda: None,
            on_upload=lambda: None,
            on_tts_toggle=self.handle_tts_toggle
        )
        
        # Dashboard
        self.dashboard = SystemDashboard(
            monitor=self.monitor,
            on_reconnect_vts=self.handle_vts_reconnect,
            on_toggle_proactive=self.handle_proactive_toggle,
            on_toggle_ontop=self.handle_ontop_toggle
        )
        
        # Main Layout Structure
        self.page.add(
            ft.Row([
                self.sidebar,
                ft.Stack([
                    ft.Column([
                        ft.Container(self.chat_view, expand=True),
                        ft.Container(self.input_dock, padding=20)
                    ], expand=True),
                    ft.Container(self.dashboard, top=20, right=20)
                ], expand=True)
            ], expand=True, spacing=0)
        )

    # --- Handlers ---

    async def handle_send(self, text):
        if not text: return
        
        # Add User Message to UI
        self.add_message("user", text)
        
        # Generate Aiko Response
        response, emotion, image_prompts, video_prompts = await self.brain.chat(text, user_id=self.current_user_name)
        
        # Add Aiko Message to UI
        self.add_message("assistant", response, emotion, instant=False)
        
        import random
        # Handle Images (Limit passed from brain is 1, but we ensure it here too)
        for p in image_prompts[:1]:
            encoded = urllib.parse.quote(p)
            seed = random.randint(1, 1000000)
            url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&nologo=true"
            self.add_image("assistant", url, caption=f"I drew this for you: {p}")

        # Handle Videos
        for p in video_prompts[:1]:
            encoded = urllib.parse.quote(p)
            seed = random.randint(1, 1000000)
            url = f"https://pollinations.ai/p/{encoded}?model=video&seed={seed}"
            self.add_message("system", f"🎬 **Cinematic Video Ready**: [View Generation]({url})", "happy")

        # Handle TTS
        if self.tts_enabled:
            await self.voice.speak(response)

    def add_message(self, role, content, emotion="neutral", instant=True):
        idx = len(self.chat_view.controls)
        bubble = ChatBubble(
            role, 
            content, 
            emotion=emotion, 
            instant=instant,
            index=idx,
            on_copy=self.handle_copy,
            on_edit=self.handle_edit
        )
        self.chat_view.controls.append(bubble)
        self.page.update()

    def add_image(self, role, url, caption=""):
        idx = len(self.chat_view.controls)
        bubble = ImageBubble(role, url, caption=caption, index=idx)
        self.chat_view.controls.append(bubble)
        self.page.update()

    def handle_copy(self, text):
        self.page.set_clipboard(text)
        self.page.show_snack_bar(ft.SnackBar(ft.Text("Copied to clipboard!"), bgcolor=COLORS["primary"]))

    def handle_edit(self, text, index):
        # Set text back to input for editing
        self.input_dock.input_field.value = text
        self.input_dock.input_field.focus()
        self.page.update()
        # Note: In a full implementation, we might want to delete the message or 'replace' it.
        # For now, this lets the user 'redo' their message easily.

    async def handle_screen_scan(self):
        self.set_thinking_state(True)
        description, img = await self.vision.scan_screen()
        
        if img:
            # Save and show
            img_path = "assets/screen_snap.jpg"
            img.save(img_path)
            self.chat_view.controls.append(ImageBubble("assistant", img_path, f"Master, I'm looking at your screen: {description}"))
            self.page.update()
        
        # Let Aiko react
        await self.handle_send(f"[INTERNAL_OBSERVATION]: {description}")
        self.set_thinking_state(False)

    async def handle_clawdbot_notification(self, task, message, status):
        """Notification hook from Clawdbot Callback Server."""
        msg = f"🔔 **Clawdbot Update**: {message}"
        if status == "success":
            msg = f"✅ **Task Finished**: {message}"
        elif status == "error":
            msg = f"❌ **Task Failed**: {message}"
            
        self.add_message("system", msg, "joy" if status == "success" else "surprised")
        
        if self.tts_enabled:
            await self.voice.speak(f"Master, Clawdbot finished the task {task}. {message}")
            
        # Update sidebar if it involved file changes etc (proactive)
        self.populate_sidebar()

    def set_thinking_state(self, is_thinking):
        self.is_thinking = is_thinking
        self.dashboard.set_thinking(is_thinking)
        if is_thinking:
            # Subtle VTS animation
            asyncio.create_task(self.vts.set_expression("thinking"))
        else:
            asyncio.create_task(self.vts.set_expression("neutral"))

    def handle_new_chat(self, e):
        self.current_chat_id = f"chat_{datetime.datetime.now().timestamp()}"
        self.chat_view.controls.clear()
        self.add_message("assistant", "Hi Master! I'm ready for a new conversation. What's on your mind?")
        self.populate_sidebar()
        self.page.update()

    def handle_settings(self, e):
        current_settings = {
            "username": self.current_user_name,
            "vts_port": self.vts_port,
            "obsidian_path": self.obsidian_path,
            "tts_enabled": self.tts_enabled,
            "dark_mode": self.page.theme_mode == ft.ThemeMode.DARK,
            "discord_enabled": self.config.get("discord_enabled", False),
            "telegram_enabled": self.config.get("telegram_enabled", False)
        }
        self.settings_modal = SettingsModal(current_settings, on_save=self.save_settings, on_cancel=self.close_settings)
        self.page.overlay.append(self.settings_modal)
        self.page.update()

    def save_settings(self, new_data):
        self.current_user_name = new_data["username"]
        self.vts_port = new_data["vts_port"]
        self.obsidian_path = new_data["obsidian_path"]
        self.tts_enabled = new_data["tts_enabled"]
        self.page.theme_mode = ft.ThemeMode.DARK if new_data["dark_mode"] else ft.ThemeMode.LIGHT
        
        self.config.set("username", self.current_user_name)
        self.config.set("vts_port", self.vts_port)
        self.config.set("obsidian_path", self.obsidian_path)
        self.config.set("tts_enabled", self.tts_enabled)
        self.config.set("discord_enabled", new_data.get("discord_enabled", False))
        self.config.set("telegram_enabled", new_data.get("telegram_enabled", False))
        
        # Re-link Obsidian
        self.obsidian.vault_path = self.obsidian_path
        self.obsidian.validate_vault()
        
        self.agency.start_all()
        
        self.close_settings()
        self.add_message("system", "Settings saved and Obsidian linked!")

    def close_settings(self):
        if hasattr(self, "settings_modal"):
            self.page.overlay.remove(self.settings_modal)
            self.page.update()

    def handle_tts_toggle(self, state):
        self.tts_enabled = state
        self.config.set("tts_enabled", state)

    def handle_proactive_toggle(self, e):
        self.proactive_mode = e.control.value
        self.config.set("proactive_mode", self.proactive_mode)
        msg = "Proactive mode enabled! I'll keep my eyes open, Master~ ✨" if self.proactive_mode else "Proactive mode off."
        self.add_message("system", msg)

    async def handle_voice_input(self):
        self.add_message("system", "Listening...")
        text = await self.voice.listen()
        if text:
            await self.handle_send(text)

    async def handle_vts_reconnect(self, e):
        success = await self.vts.connect()
        if success:
            self.dashboard.vts_status_color = COLORS["success"]
            self.add_message("system", "VTube Studio connected!")
        else:
            self.dashboard.vts_status_color = COLORS["danger"]
            self.add_message("system", "Failed to connect to VTS.")

    def handle_ontop_toggle(self, e):
        self.page.window_always_on_top = e.control.value
        self.page.update()
        msg = "I'm pinned to the top now! 📌" if e.control.value else "Unpinned."
        self.add_message("system", msg)

    def populate_sidebar(self):
        self.sidebar.history_list.controls.clear()
        sessions = self.memory.get_recent_sessions()
        for s in sessions:
            # Closure for handlers
            sid = s["id"]
            self.sidebar.add_chat_item(
                s["name"], 
                s["preview"], 
                on_click=lambda e, sid=sid: self.switch_chat(sid),
                on_delete=lambda e, sid=sid: self.handle_delete_chat(sid),
                active=(sid == self.current_chat_id)
            )

    def switch_chat(self, chat_id):
        self.current_chat_id = chat_id
        self.load_active_chat()
        self.populate_sidebar()

    def load_active_chat(self):
        self.chat_view.controls.clear()
        history = self.memory.get_history(self.current_chat_id)
        for h in history:
            self.add_message(h["role"], h["content"], instant=True)
        self.page.update()

    def handle_delete_chat(self, chat_id):
        self.memory.delete_session(chat_id)
        if chat_id == self.current_chat_id:
            self.handle_new_chat(None)
        else:
            self.populate_sidebar()

    async def update_stats_loop(self):
        """Background loop for system stats and proactive observations."""
        counter = 0
        while True:
            # Update Dashboard stats
            self.dashboard.update_stats()
            
            # Proactive Vision (Only if enabled and NOT currently in a conversation)
            if self.proactive_mode and not self.is_thinking:
                counter += 1
                if counter >= 15: # 2s interval * 15 = 30s
                    counter = 0
                    asyncio.create_task(self._proactive_observation())

            await asyncio.sleep(2)

    async def _proactive_observation(self):
        """Aiko looks at the screen autonomously and reacts if needed."""
        description, img = await self.vision.scan_screen()
        if not description or "Error" in description or "No answer" in description:
            return
            
        # Internal system prompt for proactive reaction
        prompt = f"[PROACTIVE_OBSERVE] I see: {description}. If Master is busy or doing something cool, make a tiny cute comment. If nothing changed, say '[SILENT]'."
        
        # Call Brain without saving input to memory yet
        response, emotion, image_prompts, video_prompts = await self.brain.chat(prompt, user_id=self.current_user_name, save_input=False)
        
        if response and "[SILENT]" not in response.upper():
            self.add_message("assistant", response.strip(), emotion, instant=False)
            
            import random
            # Proactive drawings? Why not!
            for p in image_prompts[:1]:
                encoded = urllib.parse.quote(p)
                seed = random.randint(1, 1000000)
                url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&nologo=true"
                self.add_image("assistant", url, caption=p)

            # Proactive Videos
            for p in video_prompts[:1]:
                encoded = urllib.parse.quote(p)
                seed = random.randint(1, 1000000)
                url = f"https://pollinations.ai/p/{encoded}?model=video&seed={seed}"
                self.add_message("system", f"🎬 **Moment Captured**: [View Video]({url})")

            if self.tts_enabled:
                await self.voice.speak(response)

def main(page: ft.Page):
    try:
        # Create data directory if missing
        os.makedirs("data", exist_ok=True)
        AikoDesktop(page)
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure assets dir is specified for fonts/images
    ft.app(target=main, assets_dir="assets")

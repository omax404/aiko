import flet as ft
import asyncio
import re
import random

# --- REFINED FIGMA DESIGN SYSTEM (DARK MODE) ---
COLORS = {
    "bg_layer_1": "#0B0B0D",     # Deep Space
    "bg_layer_2": "#0F0F12",     # Sidebar Matte
    "primary": "#E11D48",        # Vivid Rose
    "primary_gradient": ["#E11D48", "#FB7185"],
    "secondary": "#3B82F6",      # Bright Azure
    "secondary_gradient": ["#3B82F6", "#60A5FA"],
    "accent": "#F59E0B",         # Amber Glow
    "card": "#1A1A22",           # Message Slate
    "card_border": "#2D2D35",    # Subtle Border
    "text_main": "#F8FAFC",      # Porcelain
    "text_dim": "#64748B",       # Slate
    "glass": "#ffffff08",        # Frosted
    "success": "#10B981", 
    "danger": "#EF4444",
    "warning": "#F59E0B", # Alias for accent
}

AIKO_STICKERS = [
    "✨", "🌸", "🎀", "🧸", "🐱", "💖", "🍭", "🍡", "🍓", "🍰", "🎈", "🎨", "🎵", "🌙", "⭐"
]

class ModernTypography:
    @staticmethod
    def heading(text, size=24, color=COLORS["text_main"]):
        return ft.Text(
            text, size=size, color=color,
            weight="bold",
            style=ft.TextStyle(
                font_family="Pixelify Sans Bold",
            )
        )
    
    @staticmethod
    def body(text, size=19, color=COLORS["text_main"]):
        return ft.Text(
            text, size=size, color=color,
            style=ft.TextStyle(
                font_family="Pixelify Sans",
            )
        )

    @staticmethod
    def caption(text, size=12, color=COLORS["text_dim"]):
        return ft.Text(
            text, size=size, color=color,
            style=ft.TextStyle(
                font_family="Pixelify Sans",
                font_variations=[ft.FontVariation("wght", 500)]
            )
        )

# --- COMPONENTS ---

class SidebarItem(ft.Container):
    def __init__(self, icon, text, on_click=None, active=False):
        super().__init__()
        self.on_click = on_click
        self.content = ft.Row([
            ft.Icon(icon, size=18, color=COLORS["primary"] if active else COLORS["text_dim"]),
            ft.Text(text, size=16, 
                    color=COLORS["text_main"] if active else COLORS["text_dim"], 
                    weight="bold" if active else "normal",
                    font_family="Pixelify Sans Bold" if active else "Pixelify Sans"),
        ], spacing=12)
        self.padding = ft.padding.symmetric(horizontal=15, vertical=10)
        self.border_radius = 8
        self.bgcolor = ft.Colors.with_opacity(0.1, COLORS["primary"]) if active else "transparent"
        self.on_hover = self._handle_hover

    def _handle_hover(self, e):
        self.bgcolor = ft.Colors.with_opacity(0.08, "white") if e.data == "true" else ("transparent" if not self.bgcolor else self.bgcolor)
        self.content.controls[1].color = COLORS["text_main"] if e.data == "true" else COLORS["text_dim"]
        self.update()

class FigmaSidebar(ft.Container):
    def __init__(self, on_new_chat, on_settings):
        super().__init__()
        self.width = 280
        self.padding = 20
        self.bgcolor = COLORS["bg_layer_2"]
        
        self.history_list = ft.Column(spacing=2, scroll=ft.ScrollMode.HIDDEN)
        
        self.content = ft.Column([
            ft.Row([
                ft.Text("AIKO", size=26, weight="bold", color=COLORS["text_main"], font_family="Pixelify Sans Bold"),
                ft.Text(".", size=26, weight="bold", color=COLORS["primary"], font_family="Pixelify Sans Bold"),
            ], spacing=0),
            
            ft.Divider(height=20, color="transparent"),
            
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ADD_ROUNDED, color="white", size=20),
                    ft.Text("NEW CHAT", size=13, weight="bold", color="white")
                ], alignment=ft.MainAxisAlignment.CENTER),
                gradient=ft.LinearGradient(colors=COLORS["secondary_gradient"], begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1)),
                height=48,
                border_radius=14,
                on_click=on_new_chat,
                on_hover=lambda e: self._btn_hover(e),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.Colors.with_opacity(0.2, COLORS["secondary"]))
            ),
            
            ft.Divider(height=25, color="transparent"),
            ft.Text("RECENT CHATS", size=12, weight="bold", color=COLORS["text_dim"], font_family="Pixelify Sans"),
            ft.Container(self.history_list, expand=True),
            
            ft.Divider(height=10, color="transparent"),
            
            ft.Text("QUICK ACCESS", size=12, weight="bold", color=COLORS["text_dim"], font_family="Pixelify Sans"),
            SidebarItem(ft.Icons.AUTO_AWESOME_OUTLINED, "Obsidian Link", on_click=lambda _: None), # Placeholder for logic if needed
            SidebarItem(ft.Icons.SETTINGS_OUTLINED, "Settings", on_click=on_settings),
            
            ft.Container(height=10),
            ft.Text("Aiko v1.2.0-Final", size=10, color=COLORS["text_dim"], text_align=ft.TextAlign.CENTER, expand=False)
        ], expand=True)

    def add_chat_item(self, name, preview, on_click, on_delete=None, active=False):
        
        # Delete Button (Subtle)
        delete_btn = ft.IconButton(
            ft.Icons.DELETE_OUTLINE, 
            icon_size=16, 
            icon_color=COLORS["text_dim"], 
            tooltip="Delete Chat",
            on_click=on_delete,
            visible=False # Shown on hover
        )

        text_content = ft.Column([
            ft.Text(name, size=13, weight="bold", color=COLORS["text_main"] if active else COLORS["text_dim"], overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(preview, size=11, color=COLORS["text_dim"], overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
        ], spacing=2, expand=True)

        content_row = ft.Row([
            text_content,
            delete_btn
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        item = ft.Container(
            content=content_row,
            padding=10,
            border_radius=8,
            bgcolor=COLORS["secondary"] if active else "transparent",
            on_click=on_click,
            on_hover=lambda e: self._on_item_hover(e, active, delete_btn)
        )
        self.history_list.controls.append(item)
        self.update()

    def _btn_hover(self, e):
        e.control.scale = 1.02 if e.data == "true" else 1.0
        e.control.update()

    def _on_item_hover(self, e, active, btn):
        # Toggle Delete Button
        btn.visible = True if e.data == "true" or active else False
        btn.update()
        
        if not active:
            e.control.bgcolor = ft.Colors.with_opacity(0.05, "white") if e.data == "true" else "transparent"
            e.control.shadow = ft.BoxShadow(blur_radius=5, color="#000000") if e.data == "true" else None
            e.control.update()

class TypewriterControl(ft.Markdown):
    def __init__(self, value, speed=0.04, **kwargs):
        ext = kwargs.pop("extension_set", ft.MarkdownExtensionSet.GITHUB_FLAVORED)
        super().__init__(
            value="", 
            extension_set=ext,
            selectable=True,
            code_theme="atom-one-dark",
            **kwargs
        )
        self.final_text = value
        self.speed = speed

    async def animate(self, instant=False):
        if instant:
            self.value = self.final_text
            self.update()
            return

        await asyncio.sleep(0.2)
        # 1. Typewriter for the raw markdown
        for i in range(len(self.final_text) + 1):
            cursor = "█" if (i // 3) % 2 == 0 else ""
            self.value = self.final_text[:i] + cursor
            try:
                self.update()
            except: 
                break
            await asyncio.sleep(self.speed)
        
        self.value = self.final_text
        try: self.update()
        except: pass

class ChatBubble(ft.Container):
    """Refined Figma-style Chat Bubble."""
    def __init__(self, role, content, on_copy=None, on_edit=None, emotion="neutral", index=None, sticker_path=None, instant=False):
        super().__init__()
        is_user = role == "user"
        self.index = index
        self.instant = instant
        
        # Message Theme
        bubble_bg = COLORS["secondary"] if is_user else COLORS["card"]
        text_color = "white" if is_user else COLORS["text_main"]
        
        if not is_user:
            # Enhanced Math Detection for KaTeX Rendering
            import urllib.parse
            
            # Detect blocks and inline math
            math_blocks = re.findall(r'\$\$(.*?)\$\$', content, re.DOTALL)
            inline_math = re.findall(r'\$([^\$]+?)\$', content)
            
            text_widget = TypewriterControl(content)
            self.text_ref = text_widget
            
            math_controls = []
            
            # 1. Block Math Rendering (Large)
            for formula in math_blocks:
                encoded = urllib.parse.quote(formula.strip())
                url = f"https://latex.codecogs.com/png.latex?\\bg_black\\white\\huge {encoded}"
                math_controls.append(
                    ft.Container(
                        content=ft.Image(src=url, height=80, fit="contain"),
                        alignment=ft.alignment.center,
                        padding=10,
                        bgcolor=ft.Colors.with_opacity(0.1, "white"),
                        border_radius=10
                    )
                )

            # 2. Inline Math Rendering (Small preview at bottom)
            if inline_math:
                inline_row = ft.Row(wrap=True, spacing=10)
                for formula in inline_math:
                    encoded = urllib.parse.quote(formula.strip())
                    url = f"https://latex.codecogs.com/png.latex?\\bg_black\\white\\small {encoded}"
                    inline_row.controls.append(ft.Image(src=url, height=20, fit="contain"))
                math_controls.append(ft.Column([
                    ft.Text("Inline Symbols Found:", size=10, color=COLORS["text_dim"]),
                    inline_row
                ]))
            
            bubble_content = ft.Column([
                text_widget,
                ft.Column(math_controls, spacing=10) if math_controls else ft.Container()
            ], spacing=10)
        else:
            bubble_content = ft.Markdown(content, selectable=True)
            self.text_ref = None
            
        bubble = ft.Container(
            content=bubble_content,
            bgcolor=bubble_bg if is_user else COLORS["card"],
            gradient=ft.LinearGradient(
                colors=COLORS["primary_gradient"],
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1)
            ) if is_user else None,
            padding=18,
            border_radius=ft.border_radius.only(
                top_left=20, top_right=20,
                bottom_left=20 if is_user else 5,
                bottom_right=5 if is_user else 20
            ),
            border=ft.border.all(1, COLORS["card_border"]) if not is_user else None,
            width=550,
            opacity=0,
            offset=ft.Offset(0, 0.2), # Start lower for better pop
            animate_opacity=300,
            animate_offset=ft.Animation(500, ft.AnimationCurve.EASE_OUT_BACK),
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.1, "black"))
        )

        sticker = ft.Text(
            re.sub(r'[^a-zA-Z0-9\s]', '', ""), # Placeholder
            size=24,
            opacity=0,
            animate_opacity=300,
            offset=ft.Offset(0, 0.5),
            animate_offset=ft.Animation(600, ft.AnimationCurve.BOUNCE_OUT)
        )
        
        self.sticker_ref = sticker
        
        # Select a random mood sticker for Assistant
        if not is_user:
            self.sticker_ref.value = random.choice(AIKO_STICKERS)

        controls = []
        if not is_user:
            controls.append(sticker)
            if sticker_path:
                controls.append(ft.Image(src=sticker_path, width=120, height=120, fit="contain"))

        controls.append(bubble)
        
        # User Actions
        if is_user:
            actions = ft.Row([
                ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=14, icon_color=COLORS["text_dim"], on_click=lambda _: on_edit(content, index) if on_edit else None),
                ft.IconButton(ft.Icons.COPY_OUTLINED, icon_size=14, icon_color=COLORS["text_dim"], on_click=lambda _: on_copy(content) if on_copy else None),
            ], spacing=0, alignment=ft.MainAxisAlignment.END)
            self.content = ft.Column([
                ft.Row(controls, alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.END, spacing=10),
                actions
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END)
        else:
            self.content = ft.Row(
                controls,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=10
            )

        self.padding = ft.padding.symmetric(vertical=8)
        self.bubble_ref = bubble
        asyncio.create_task(self._animate_entry())

    async def _animate_entry(self):
        await asyncio.sleep(0.05)
        self.bubble_ref.opacity = 1
        self.bubble_ref.offset = ft.Offset(0, 0)
        
        # Animate sticker if assistant
        if hasattr(self, "sticker_ref") and self.sticker_ref:
            self.sticker_ref.opacity = 1
            self.sticker_ref.offset = ft.Offset(0, 0)
            
        self.update()
        
        # Start Typewriter if it's an assistant message
        if hasattr(self, "text_ref") and self.text_ref:
            asyncio.create_task(self.text_ref.animate(instant=self.instant))

class ModernInputDock(ft.Container):
    """The 'Initial App' style Input Dock from Image 1."""
    def __init__(self, on_send, on_voice, on_screen_scan, on_camera_scan, on_upload, on_tts_toggle):
        super().__init__()
        self.callbacks = (on_send, on_voice, on_screen_scan, on_camera_scan, on_upload, on_tts_toggle)
        self.tts_active = True
        
        self.input_field = ft.TextField(
            hint_text="Ask Aiko something...",
            hint_style=ft.TextStyle(color="#555", size=15, font_family="Pixelify Sans"),
            text_style=ft.TextStyle(color="white", size=17, font_family="Pixelify Sans"),
            border=ft.InputBorder.NONE,
            bgcolor="transparent",
            expand=True,
            on_submit=self._submit,
            content_padding=15,
        )

        def btn(icon, func, color=COLORS["text_dim"], tooltip=None):
            return ft.IconButton(
                icon=icon, icon_size=20, icon_color=color,
                on_click=func, tooltip=tooltip,
                style=ft.ButtonStyle(overlay_color=ft.Colors.with_opacity(0.1, "white"))
            )

        self.tts_btn = btn(ft.Icons.VOLUME_UP_ROUNDED, self._toggle_tts_ui, COLORS["primary"])

        self.content = ft.Container(
            content=ft.Row([
                btn(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, self._upload_trigger, tooltip="Upload"),
                ft.Container(
                    self.input_field, 
                    expand=True, 
                    bgcolor="#0A0A0C", # Inner dark field
                    border_radius=20,
                    margin=ft.margin.symmetric(horizontal=10)
                ),
                self.tts_btn,
                btn(ft.Icons.MIC_NONE_ROUNDED, self._voice_trigger, tooltip="Voice"),
                btn(ft.Icons.CAMERA_ALT_OUTLINED, self._camera_trigger, tooltip="Camera"),
                btn(ft.Icons.MONITOR_HEART_OUTLINED, self._scan_trigger, tooltip="Scan"),
                ft.Container(
                    ft.IconButton(ft.Icons.ARROW_UPWARD_ROUNDED, icon_color="white", icon_size=18, on_click=self._submit),
                    bgcolor=COLORS["primary"], # Pink/Red send button
                    border_radius=ft.border_radius.all(20),
                    width=42, height=42,
                    margin=ft.margin.only(left=5)
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=15, vertical=5),
            border_radius=35,
            bgcolor="#15151A", # Dark pill background
            border=ft.border.all(1, "#22222A"),
            height=65,
            width=800,
        )
        self.alignment = ft.Alignment(0, 0)
        
    def _upload_trigger(self, e): 
        # pick_files is sync, don't wrap in create_task
        self.callbacks[4]() 
        
    def _voice_trigger(self, e): 
        # handle_voice_input is async
        asyncio.create_task(self.callbacks[1]())
        
    def _camera_trigger(self, e):
        # handle_camera_scan is async
        asyncio.create_task(self.callbacks[3]())

    def _scan_trigger(self, e): 
        # handle_screen_scan is async
        asyncio.create_task(self.callbacks[2]())
    
    def _toggle_tts_ui(self, e):
        self.tts_active = not self.tts_active
        self.tts_btn.icon = ft.Icons.VOLUME_UP_ROUNDED if self.tts_active else ft.Icons.VOLUME_OFF_ROUNDED
        self.tts_btn.update()
        self.callbacks[4](self.tts_active)

    async def _submit(self, e):
        text = self.input_field.value
        if text:
            self.input_field.value = ""
            self.input_field.update()
            await self.callbacks[0](text)

class SystemDashboard(ft.Container):
    """Clean Floating HUD from screenshot."""
    def __init__(self, monitor, on_reconnect_vts, on_toggle_proactive=None, on_toggle_ontop=None):
        super().__init__()
        self.monitor = monitor
        self.on_reconnect = on_reconnect_vts
        self.on_proactive = on_toggle_proactive
        self.on_ontop = on_toggle_ontop
        
        self.cpu_bar = ft.ProgressBar(value=0, height=4, color=COLORS["primary"], bgcolor="#22222A", border_radius=2)
        self.ram_bar = ft.ProgressBar(value=0, height=4, color=COLORS["secondary"], bgcolor="#22222A", border_radius=2)
        
        self.cpu_val = ft.Text("0%", size=10, font_family="Pixelify Sans Bold", color=COLORS["primary"])
        self.ram_val = ft.Text("0%", size=10, font_family="Pixelify Sans Bold", color=COLORS["secondary"])
        
        self.thinking_dot = ft.Container(
            width=10, height=10, bgcolor=COLORS["primary"], border_radius=5,
            opacity=0, scale=1,
            animate_opacity=300,
            animate_scale=ft.Animation(400, ft.AnimationCurve.BOUNCE_OUT),
            shadow=ft.BoxShadow(blur_radius=10, color=COLORS["primary"])
        )
        
        self.proactive_switch = ft.Switch(
            value=False, scale=0.6, 
            active_color=COLORS["primary"],
            on_change=lambda e: self.on_proactive(e) if self.on_proactive else None
        )

        self.ontap_switch = ft.Switch(
            value=False, scale=0.6, 
            active_color=COLORS["primary"],
            on_change=lambda e: self.on_ontop(e) if self.on_ontop else None
        )
        
        self.vts_icon = ft.Icon(ft.Icons.SYNC_ROUNDED, size=14, color=COLORS["primary"])
        self.vts_text = ft.Text("SYNC VTS", size=11, weight="bold", color=COLORS["text_dim"])
        
        self.content = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.MONITOR_HEART_OUTLINED, size=16, color=COLORS["primary"]),
                ft.Text("VITAL_SIGNS", size=11, font_family="Pixelify Sans Bold", weight="bold"),
                ft.Container(expand=True),
                self.thinking_dot
            ], spacing=8),
            
            ft.Divider(height=10, color="transparent"),
            
            ft.Column([
                ft.Row([ft.Text("CPU", size=10, color=COLORS["text_dim"]), ft.Container(expand=True), self.cpu_val]),
                self.cpu_bar,
            ], spacing=2),
            
            ft.Column([
                ft.Row([ft.Text("RAM", size=10, color=COLORS["text_dim"]), ft.Container(expand=True), self.ram_val]),
                self.ram_bar,
            ], spacing=2),
            
            ft.Divider(height=10, color="#2D2D35"),
            
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, size=14, color=COLORS["text_dim"]),
                ft.Text("PROACTIVE", size=10, font_family="Pixelify Sans"),
                ft.Container(expand=True),
                self.proactive_switch
            ], spacing=8),
            
            ft.Row([
                ft.Icon(ft.Icons.PUSH_PIN_OUTLINED, size=14, color=COLORS["text_dim"]),
                ft.Text("STAY ON TOP", size=10, font_family="Pixelify Sans"),
                ft.Container(expand=True),
                self.ontap_switch
            ], spacing=8),

            ft.Container(
                content=ft.Row([
                    self.vts_icon,
                    self.vts_text
                ], spacing=8),
                on_click=self.on_reconnect,
                padding=ft.padding.all(5),
                border_radius=8,
                on_hover=lambda e: self._hover_btn(e)
            )
        ], spacing=8, tight=True)
        
        self.padding = 12
        self.bgcolor = ft.Colors.with_opacity(0.9, "#0B0B0D")
        self.border_radius = 12
        self.border = ft.border.all(1, "#22222A")
        self.width = 180

    def _hover_btn(self, e):
        e.control.bgcolor = ft.Colors.with_opacity(0.1, "white") if e.data == "true" else None
        e.control.update()

    def set_thinking(self, state: bool):
        self.thinking_dot.opacity = 1 if state else 0
        self.thinking_dot.scale = 1.2 if state else 1.0
        self.thinking_dot.update()

    @property
    def vts_status_color(self): return self.vts_icon.color
    
    @vts_status_color.setter
    def vts_status_color(self, value):
        self.vts_icon.color = value
        self.vts_icon.update()
        
    @property
    def vts_status_icon(self): return self.vts_icon.name
    
    @vts_status_icon.setter
    def vts_status_icon(self, value):
        self.vts_icon.name = value
        self.vts_icon.update()

    def update_stats(self):
        stats = self.monitor.get_stats()
        cpu_p = stats['cpu'] / 100
        self.cpu_bar.value = cpu_p
        self.cpu_val.value = f"{int(stats['cpu'])}%"
        
        ram_perc = (stats['ram_used'] / stats['ram_total'])
        self.ram_bar.value = ram_perc
        self.ram_val.value = f"{int(ram_perc * 100)}%"
        self.update()

    def set_vision_status(self, is_ready):
        self.vision_icon.color = COLORS["success"] if is_ready else COLORS["danger"]
        self.vision_icon.update()

class ImageBubble(ft.Container):
    """Chat Bubble for Images."""
    def __init__(self, role, image_url, caption="", index=None):
        super().__init__()
        is_user = role == "user"
        self.index = index
        self.content = ft.Container(
            content=ft.Column([
                ft.Image(src=image_url, width=400, height=300, fit="contain", border_radius=12),
                ft.Text(caption, size=11, italic=True, color=COLORS["text_dim"]) if caption else ft.Container()
            ], spacing=5),
            bgcolor=COLORS["card"],
            padding=10,
            border_radius=12,
        )
        self.alignment = ft.Alignment(1, 0) if is_user else ft.Alignment(-1, 0)
        self.padding = ft.padding.only(bottom=10)

class StickerBubble(ft.Container):
    """Small transparent sticker for emotional flavor."""
    def __init__(self, image_path, size=120):
        super().__init__()
        self.content = ft.Image(src=image_path, width=size, height=size, fit="contain")
        self.animate_opacity = 300
        self.opacity = 0
        asyncio.create_task(self._entry())
    async def _entry(self):
        await asyncio.sleep(0.1); self.opacity = 1; self.update()

class SettingsModal(ft.Container):
    """
    Glassmorphism Settings Modal.
    """
    def __init__(self, current_settings, on_save, on_cancel):
        super().__init__()
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.settings = current_settings
        
        # Inputs
        self.username_field = ft.TextField(
            label="User Name", 
            value=self.settings.get("username", "User"),
            border_color=COLORS["primary"],
            text_size=14,
            height=40,
            content_padding=10
        )
        
        self.vts_port_field = ft.TextField(
            label="VTS Port", 
            value=self.settings.get("vts_port", "8001"),
            border_color=COLORS["primary"],
            text_size=14,
            height=40,
            content_padding=10
        )

        self.obsidian_path_field = ft.TextField(
            label="Obsidian Vault Path", 
            value=self.settings.get("obsidian_path", ""),
            border_color=COLORS["primary"],
            text_size=14,
            height=40,
            content_padding=10,
            hint_text="C:\\Users\\...\\Documents\\Vault"
        )
        
        self.tts_switch = ft.Switch(
            label="Enable TTS",
            value=self.settings.get("tts_enabled", True),
            active_color=COLORS["primary"]
        )

        self.dark_mode_switch = ft.Switch(
            label="Dark Mode",
            value=self.settings.get("dark_mode", True),
            active_color=COLORS["primary"]
        )

        self.discord_switch = ft.Switch(
            label="Discord Bridge",
            value=self.settings.get("discord_enabled", False),
            active_color=COLORS["primary"]
        )

        self.telegram_switch = ft.Switch(
            label="Telegram Bridge",
            value=self.settings.get("telegram_enabled", False),
            active_color=COLORS["primary"]
        )

        # Layout
        self.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("SYSTEM CONFIG", size=20, weight="bold", font_family="Pixelify Sans Bold"),
                    ft.IconButton(ft.Icons.CLOSE, on_click=self._handle_cancel)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Divider(color=COLORS["card_border"]),
                
                ft.Text("Identity", color=COLORS["accent"], size=12, weight="bold"),
                self.username_field,
                
                ft.Container(height=10),
                
                ft.Text("VTube Studio / Obsidian", color=COLORS["accent"], size=12, weight="bold"),
                self.vts_port_field,
                self.obsidian_path_field,
                
                ft.Container(height=10),
                
                ft.Text("Preferences", color=COLORS["accent"], size=12, weight="bold"),
                self.tts_switch,
                self.dark_mode_switch,
                
                ft.Container(height=10),
                
                ft.Text("Agency Platforms", color=COLORS["accent"], size=12, weight="bold"),
                self.discord_switch,
                self.telegram_switch,

                ft.Container(expand=True),
                
                ft.Row([
                    ft.ElevatedButton("Save Changes", 
                        on_click=self._handle_save,
                        bgcolor=COLORS["primary"],
                        color="white",
                        elevation=0
                    )
                ], alignment=ft.MainAxisAlignment.END)
                
            ], spacing=15),
            padding=30,
            bgcolor="#1A1A22",
            border_radius=16,
            width=400,
            height=500,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.5, "black")),
            border=ft.border.all(1, COLORS["card_border"])
        )
        
        self.alignment = ft.Alignment(0, 0)
        self.bgcolor = ft.Colors.with_opacity(0.6, "black") # Dim background
        self.expand = True
        self.opacity = 0
        self.animate_opacity = 300
        
    def did_mount(self):
        self.opacity = 1
        self.update()

    def _handle_save(self, e):
        new_data = {
            "username": self.username_field.value,
            "vts_port": self.vts_port_field.value,
            "obsidian_path": self.obsidian_path_field.value,
            "tts_enabled": self.tts_switch.value,
            "dark_mode": self.dark_mode_switch.value,
            "discord_enabled": self.discord_switch.value,
            "telegram_enabled": self.telegram_switch.value
        }
        self.on_save(new_data)
        
    def _handle_cancel(self, e):
        self.opacity = 0
        self.update()
        asyncio.create_task(self._delayed_close())

    async def _delayed_close(self):
        await asyncio.sleep(0.3)
        self.on_cancel()

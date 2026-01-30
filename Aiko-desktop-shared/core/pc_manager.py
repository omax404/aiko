"""
AIKO PC MANAGER
Allows Aiko to interact with the user's files and applications.
"""

import os
import shutil
import subprocess
from pathlib import Path
import getpass

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False
    print("⚠️ send2trash not installed. Delete-to-recycle-bin disabled.")


class PCManager:
    """Aiko's PC Management Module."""
    
    def __init__(self):
        self.username = getpass.getuser()
        self.user_paths = {
            "downloads": rf"C:\Users\{self.username}\Downloads",
            "desktop": rf"C:\Users\{self.username}\Desktop",
            "documents": rf"C:\Users\{self.username}\Documents",
            "pictures": rf"C:\Users\{self.username}\Pictures",
            "videos": rf"C:\Users\{self.username}\Videos",
        }
        
    def get_folder_path(self, folder_name: str) -> str:
        """Get the full path for a named folder."""
        return self.user_paths.get(folder_name.lower(), folder_name)
        
    def list_files(self, path: str) -> str:
        """List files in a directory."""
        try:
            p = Path(path)
            if not p.exists():
                return f"I couldn't find that place, Master... {path} doesn't seem to exist."
                
            files = os.listdir(path)
            if not files:
                return "It's empty there! Just like my heart when you're gone... 🥺"
                
            # Format nicely (limit to 20)
            file_list = "\n".join([f"- {f}" for f in files[:20]])
            if len(files) > 20:
                file_list += f"\n...and {len(files) - 20} more."
                
            return f"Here's what I found in {path}:\n{file_list}"
            
        except Exception as e:
            return f"Ehh? I got a headache trying to look there... {str(e)}"
            
    def open_file(self, path: str) -> str:
        """Open a file or folder using the default OS application."""
        try:
            if not os.path.exists(path):
                return "I can't open something that isn't there, Master! 😖"
                
            os.startfile(path)
            return f"I've opened {os.path.basename(path)} for you! ✨"
            
        except Exception as e:
            return f"I tried to open it, but computer-kun is being mean... {str(e)}"
            
    def open_folder(self, folder_name: str) -> str:
        """Open a user folder by name."""
        path = self.get_folder_path(folder_name)
        return self.open_file(path)
        
    def move_file(self, src: str, dest: str) -> str:
        """Move a file from source to destination."""
        try:
            if not os.path.exists(src):
                return "Where is the file? I can't find it to move it... 🥺"
                
            dest_path = Path(dest)
            if dest_path.is_dir():
                target = dest_path / os.path.basename(src)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                target = dest_path
                
            shutil.move(src, target)
            return f"Done! I moved {os.path.basename(src)} to {dest}. I'm a helpful waifu, right? 💕"
            
        except Exception as e:
            return f"I tried to move it, but it's too heavy! 😖 {str(e)}"
            
    def delete_to_recycle_bin(self, path: str) -> str:
        """Move a file or folder to the recycle bin."""
        if not HAS_SEND2TRASH:
            return "I can't delete things safely without send2trash installed! 😖"
            
        try:
            if not os.path.exists(path):
                return "It's already gone, Master! Or at least I can't find it. ✨"
                
            send2trash.send2trash(path)
            return f"I've thrown {os.path.basename(path)} into the trash! It's gone now~ 🗑️💞"
            
        except Exception as e:
            return f"I tried to throw it away, but it's stuck! {str(e)}"
            
    def organize_folder(self, folder_name: str) -> str:
        """Smart organize: move images, docs, etc. into subfolders."""
        path = self.get_folder_path(folder_name)
        
        try:
            p = Path(path)
            if not p.is_dir():
                return "That's not a folder, Master! 😖"
                
            extensions = {
                "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"],
                "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".md", ".doc"],
                "Videos": [".mp4", ".mkv", ".mov", ".avi", ".webm"],
                "Music": [".mp3", ".wav", ".flac", ".m4a", ".ogg"],
                "Archives": [".zip", ".rar", ".7z", ".gz", ".tar"],
                "Executables": [".exe", ".msi", ".bat", ".ps1"],
            }
            
            moved_count = 0
            for item in p.iterdir():
                if item.is_file():
                    ext = item.suffix.lower()
                    for folder_name_target, exts in extensions.items():
                        if ext in exts:
                            dest_dir = p / folder_name_target
                            dest_dir.mkdir(exist_ok=True)
                            shutil.move(str(item), str(dest_dir / item.name))
                            moved_count += 1
                            break
                            
            if moved_count == 0:
                return "Everything is already in its place! You're so organized, Master~ ✨"
                
            return f"I've organized {moved_count} files for you! Your {p.name} folder looks so clean now~ 💕"
            
        except Exception as e:
            return f"My hands got dirty trying to clean up... {str(e)}"
            
    def launch_app(self, app_name: str) -> str:
        """Launch an application by name."""
        # Common app mappings
        app_map = {
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "notepad": "notepad",
            "calculator": "calc",
            "explorer": "explorer",
            "cmd": "cmd",
            "powershell": "powershell",
            "code": "code",
            "vscode": "code",
            "discord": "discord",
            "spotify": "spotify",
        }
        
        try:
            cmd = app_map.get(app_name.lower(), app_name)
            
            # Windows specific 'start' command for better resolution
            if os.name == 'nt':
                # Use start "" "cmd" to handle quotes and titles safely
                full_cmd = f'start "" "{cmd}"' if " " in cmd else f'start {cmd}'
                # But for simple apps like 'chrome', 'start chrome' works better than Popen('chrome')
                subprocess.Popen(f"start {cmd}", shell=True)
            else:
                subprocess.Popen(cmd, shell=True)
                
            return f"I've launched {app_name} for you, Master! ✨"
        except Exception as e:
            print(f" [PC] Launch Error: {e}")
            return f"I couldn't find that app... {str(e)}"
            
    def get_folder_stats(self, folder_name: str) -> dict:
        """Get statistics for a folder."""
        path = self.get_folder_path(folder_name)
        
        try:
            p = Path(path)
            if not p.is_dir():
                return {"error": "Not a folder"}
                
            files = list(p.iterdir())
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            return {
                "name": p.name,
                "path": str(p),
                "file_count": len([f for f in files if f.is_file()]),
                "folder_count": len([f for f in files if f.is_dir()]),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
            
        except Exception as e:
            return {"error": str(e)}

    # --- COMPUTER USE (AUTOMATION) ---
    def mouse_move(self, x: int, y: int, duration=0.2) -> str:
        """Move mouse cursor."""
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=duration)
            return f"Moved cursor to ({x}, {y})"
        except Exception as e: return f"Mouse Error: {e}"

    def mouse_click(self, x: int = None, y: int = None, button="left") -> str:
        """Click mouse button."""
        try:
            import pyautogui
            pyautogui.click(x, y, button=button)
            return f"Clicked {button}"
        except Exception as e: return f"Click Error: {e}"

    def type_text(self, text: str, interval=0.01) -> str:
        """Type text."""
        try:
            import pyautogui
            pyautogui.write(text, interval=interval)
            return f"Typed {len(text)} chars"
        except Exception as e: return f"Type Error: {e}"

    def set_wallpaper(self, image_name_or_path: str) -> str:
        """Change desktop wallpaper (Windows only)."""
        try:
            import ctypes
            
            # Resolve Path
            target_path = image_name_or_path
            if not os.path.exists(target_path):
                # Check user folders
                candidates = [
                    os.path.join(self.user_paths["pictures"], image_name_or_path),
                    os.path.join(self.user_paths["downloads"], image_name_or_path),
                    os.path.join(self.user_paths["pictures"], "Wallpapers", image_name_or_path)
                ]
                for c in candidates:
                    if os.path.exists(c):
                        target_path = c
                        break
                    # Try with extensions
                    for ext in [".jpg", ".png", ".jpeg", ".bmp"]:
                        if os.path.exists(c + ext):
                            target_path = c + ext
                            break
                            
            if not os.path.exists(target_path):
                return f"I couldn't find the image '{image_name_or_path}'... 😖"
                
            # Set Wallpaper
            # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 0x01, SPIF_SENDWININICHANGE = 0x02
            ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(target_path), 3)
            return f"Wallpaper set to {os.path.basename(target_path)}! Does it look good? ✨"
            
        except Exception as e:
            return f"Start-up failed... I mean, wallpaper change failed: {e}"

    # --- ADDITIONAL CAPABILITIES ---
    def check_weather(self, city: str = "") -> str:
        """Check weather using wttr.in"""
        try:
            import requests
            # format=3: "Location: Condition Temp"
            url = f"http://wttr.in/{city}?format=3"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return f"Weather Report: {res.text.strip()}"
            return "Could not reach weather satellite..."
        except Exception as e:
            return f"Weather Error: {e}"

    def media_control(self, action: str) -> str:
        """Control media playback."""
        try:
            import pyautogui
            valid = {
                "play": "playpause",
                "pause": "playpause",
                "next": "nexttrack",
                "prev": "prevtrack",
                "vol_up": "volumeup",
                "vol_down": "volumedown",
                "mute": "volumemute"
            }
            key = valid.get(action.lower())
            if key:
                pyautogui.press(key)
                return f"Media Action: {action} (Pressed {key})"
            return "Unknown media command."
        except Exception as e:
            return f"Media Error: {e}"

    def leave_note(self, content: str) -> str:
        """Leave a secret note on the desktop."""
        try:
            import time
            ts = int(time.time())
            filename = f"Aiko_Note_{ts}.txt"
            path = os.path.join(self.user_paths["desktop"], filename)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
                
            return f"Hidden letter left at {path} 💌"
        except Exception as e:
            return f"Failed to hide letter: {e}"

"""
AIKO MEMORY MANAGER
Handles short-term conversation history and affection levels.
"""

import json
import os
import time
from typing import List, Dict

# Configuration
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "shared_memory.json")
MAX_HISTORY = 20
DEFAULT_AFFECTION = 30  # Start at 'Acquaintance' level


class MemoryManager:
    """Manages conversation history and user affection levels."""
    
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        self._cache = None
        
    def load_memory(self) -> Dict[str, Dict]:
        """Load the shared memory database."""
        if self._cache is not None:
            return self._cache
            
        if not os.path.exists(MEMORY_FILE):
            self._cache = {
                "global": {"history": [], "affection": 0},
                "omax404": {"history": [], "affection": 100}
            }
            return self._cache
            
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Migration: Convert old list format to new dict format
            migrated = False
            for uid, content in list(data.items()):
                if isinstance(content, list):
                    data[uid] = {
                        "history": content,
                        "affection": 100 if uid in ["omax404", "master"] else DEFAULT_AFFECTION
                    }
                    migrated = True
                    
            if migrated:
                print("[Memory] Migrated database to new Affection Schema.")
                self.save_memory(data)
                
            self._cache = data
            return data
            
        except Exception as e:
            print(f"[Memory] Load error: {e}")
            self._cache = {"global": {"history": [], "affection": 0}}
            return self._cache
            
    def save_memory(self, data: Dict[str, Dict] = None):
        """Save memory to disk."""
        if data is None:
            data = self._cache
        if data is None:
            return
            
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Memory] Save error: {e}")
            
    def get_user_data(self, user_id: str) -> tuple:
        """Helper to get user object, initializing if missing."""
        mem = self.load_memory()
        uid = str(user_id)
        
        if uid not in mem or not isinstance(mem[uid], dict) or "history" not in mem[uid]:
            # Reset or initialize structure
            mem[uid] = {
                "history": [],
                "affection": DEFAULT_AFFECTION
            }
            
        return mem, uid
        
    def add_message(self, user_id: str, role: str, content: str):
        """Add a message to the shared history."""
        mem, uid = self.get_user_data(user_id)
        
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        
        mem[uid]["history"].append(entry)
        
        # Prune old messages
        if len(mem[uid]["history"]) > MAX_HISTORY:
            mem[uid]["history"] = mem[uid]["history"][-MAX_HISTORY:]
            
        self.save_memory(mem)
        
    def get_history(self, user_id: str) -> List[Dict]:
        """Get conversation history formatted for LLM."""
        mem, uid = self.get_user_data(user_id)
        history = mem[uid]["history"]
        # Return only role/content for LLM
        return [{"role": m["role"], "content": m["content"]} for m in history]
        
    def get_stats(self, user_id: str) -> Dict:
        """Get user stats (affection, etc)."""
        mem, uid = self.get_user_data(user_id)
        return {"affection": mem[uid].get("affection", DEFAULT_AFFECTION)}
        
    def update_affection(self, user_id: str, delta: int) -> int:
        """Change affection level. Returns new level."""
        mem, uid = self.get_user_data(user_id)
        
        current = mem[uid].get("affection", DEFAULT_AFFECTION)
        new_val = max(0, min(100, current + delta))  # Clamp 0-100
        
        mem[uid]["affection"] = new_val
        self.save_memory(mem)
        return new_val
        
    def clear_memory(self, user_id: str = None) -> bool:
        """Clear memory for a specific user or all users."""
        if user_id:
            mem = self.load_memory()
            uid = str(user_id)
            if uid in mem:
                mem[uid]["history"] = []
                mem[uid]["affection"] = DEFAULT_AFFECTION
                self.save_memory(mem)
                return True
        else:
            self._cache = {"global": {"history": [], "affection": 0}}
            self.save_memory()
            return True
        return False
        
    def overwrite_history(self, user_id: str, new_history: List[Dict]) -> bool:
        """Overwrite history with new list (e.g. after editing)."""
        mem, uid = self.get_user_data(user_id)
        
        # Ensure format
        clean_hist = []
        for m in new_history:
            clean_hist.append({
                "role": m["role"],
                "content": m["content"],
                "timestamp": time.time()
            })
            
        mem[uid]["history"] = clean_hist[-MAX_HISTORY:]
        self.save_memory(mem)
        return True

    def truncate_history(self, user_id: str, index: int):
        """Remove history items starting from index."""
        mem, uid = self.get_user_data(user_id)
        if 0 <= index < len(mem[uid]["history"]):
            mem[uid]["history"] = mem[uid]["history"][:index]
            self.save_memory(mem)

    def get_recent_sessions(self) -> List[Dict]:
        """Get list of all chat sessions sorted by recency."""
        mem = self.load_memory()
        sessions = []
        for uid, data in mem.items():
            history = data.get("history", [])
            last_msg = history[-1] if history else None
            preview = last_msg["content"][:30] + "..." if last_msg else "Empty Chat"
            timestamp = last_msg["timestamp"] if last_msg else 0
            
            sessions.append({
                "id": uid,
                "name": data.get("name", f"Chat {uid[:6]}"),
                "preview": preview,
                "timestamp": timestamp
            })
            
        # Sort by timestamp, newest first
        sessions.sort(key=lambda x: x["timestamp"], reverse=True)
        return sessions

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename a chat session."""
        mem = self.load_memory()
        if session_id in mem:
            mem[session_id]["name"] = new_name
            self.save_memory(mem)
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session entirely."""
        mem = self.load_memory()
        if session_id in mem:
            del mem[session_id]
            self.save_memory(mem)
            return True
        return False

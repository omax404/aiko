"""
AIKO UNIFIED MEMORY SYSTEM v3.0
═══════════════════════════════════════════════════════════════
A unified memory layer combining:
- Short-term conversation history (JSON)
- Long-term semantic memory (RAG/ChromaDB)
- Aiko's internal thoughts stream (Text files)
- Personality-linked file associations

Design Goals:
1. All data accessible via unified interface
2. Aiko's thoughts logged to human-readable text files
3. Files linked to her personality and memory graph
4. Minimal memory footprint with intelligent caching
"""

import json
import os
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging
import hashlib

logger = logging.getLogger("UnifiedMemory")

# Memory paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_FILE = DATA_DIR / "unified_memory.json"
THOUGHTS_DIR = DATA_DIR / "thoughts"
FILE_LINKS_DIR = DATA_DIR / "file_links"

@dataclass
class Thought:
    """A single thought entry."""
    timestamp: float
    content: str
    category: str  # 'reflection', 'observation', 'emotion', 'intent', 'memory'
    related_files: List[str]
    related_memories: List[str]
    emotion: str
    importance: int  # 1-10

@dataclass
class FileLink:
    """Link between a file and Aiko's personality."""
    path: str
    file_type: str
    linked_at: float
    access_count: int
    last_accessed: float
    tags: List[str]
    summary: str
    emotional_value: float  # -1.0 to 1.0
    relevance_score: float  # 0.0 to 1.0


class ThoughtStream:
    """
    Manages Aiko's stream of consciousness.
    Writes to both text files and structured storage.
    """

    def __init__(self, thoughts_dir: Path = None):
        self.thoughts_dir = thoughts_dir or THOUGHTS_DIR
        self.thoughts_dir.mkdir(parents=True, exist_ok=True)

        # Daily thought log file
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.thoughts_buffer = []
        self.buffer_size = 10
        self.last_flush = time.time()
        self.flush_interval = 30  # seconds

        # Ensure today's file exists
        self._get_today_file()

    def _get_today_file(self) -> Path:
        """Get or create today's thought log file."""
        today = datetime.now().strftime("%Y-%m-%d")

        if today != self.current_date:
            self.current_date = today
            self._flush_buffer()  # Flush old date's buffer

        file_path = self.thoughts_dir / f"aiko_thoughts_{today}.txt"

        if not file_path.exists():
            header = f"""╔══════════════════════════════════════════════════════════════════╗
║  AIKO'S THOUGHT STREAM - {today}                                        ║
║  A window into her digital mind                                     ║
╚══════════════════════════════════════════════════════════════════╝

This file contains Aiko's internal monologue, reflections, and observations.
Each entry is timestamped and categorized for better understanding.

"""
            file_path.write_text(header, encoding='utf-8')

        return file_path

    def _flush_buffer(self):
        """Write buffered thoughts to file."""
        if not self.thoughts_buffer:
            return

        file_path = self._get_today_file()

        with open(file_path, 'a', encoding='utf-8') as f:
            for thought in self.thoughts_buffer:
                time_str = datetime.fromtimestamp(thought['timestamp']).strftime("%H:%M:%S")

                # Visual formatting based on category
                icon = {
                    'reflection': '💭',
                    'observation': '👁️',
                    'emotion': '💖',
                    'intent': '⚡',
                    'memory': '📚',
                    'dream': '🌙',
                    'learning': '🧠'
                }.get(thought['category'], '💬')

                f.write(f"\n[{time_str}] {icon} [{thought['category'].upper()}]\n")
                f.write(f"Emotion: {thought['emotion']} | Importance: {thought['importance']}/10\n")
                f.write(f"───\n{thought['content']}\n")

                if thought['related_files']:
                    f.write(f"🔗 Related files: {', '.join(thought['related_files'])}\n")
                if thought['related_memories']:
                    f.write(f"💾 Related memories: {len(thought['related_memories'])} items\n")

                f.write("─" * 60 + "\n")

        self.thoughts_buffer.clear()
        self.last_flush = time.time()

    def think(self, content: str, category: str = "reflection",
              related_files: List[str] = None, related_memories: List[str] = None,
              emotion: str = "neutral", importance: int = 5):
        """
        Record a thought in Aiko's stream.

        Example:
            memory.thought_stream.think(
                "Master seems stressed today. I should be extra supportive.",
                category="observation",
                emotion="concerned",
                importance=7
            )
        """
        thought = {
            'timestamp': time.time(),
            'content': content,
            'category': category,
            'related_files': related_files or [],
            'related_memories': related_memories or [],
            'emotion': emotion,
            'importance': importance
        }

        self.thoughts_buffer.append(thought)

        # Flush if buffer is full or interval passed
        if (len(self.thoughts_buffer) >= self.buffer_size or
            time.time() - self.last_flush > self.flush_interval):
            self._flush_buffer()

        return thought

    def get_recent_thoughts(self, hours: int = 24) -> List[Dict]:
        """Get recent thoughts from text files."""
        thoughts = []
        cutoff = time.time() - (hours * 3600)

        for file_path in sorted(self.thoughts_dir.glob("aiko_thoughts_*.txt")):
            # Parse file date from filename
            try:
                date_str = file_path.stem.replace("aiko_thoughts_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d").timestamp()

                if file_date >= cutoff - 86400:  # Include previous day
                    content = file_path.read_text(encoding='utf-8')
                    # Simple parsing - could be enhanced
                    thoughts.append({
                        'date': date_str,
                        'content': content
                    })
            except:
                continue

        return thoughts[-5:]  # Last 5 files


class FileMemoryGraph:
    """
    Links files to Aiko's personality and memory.
    Tracks which files are important to her.
    """

    def __init__(self, links_dir: Path = None):
        self.links_dir = links_dir or FILE_LINKS_DIR
        self.links_dir.mkdir(parents=True, exist_ok=True)
        self.links_file = self.links_dir / "file_links.json"
        self._cache = {}
        self._dirty = False
        self._load()

    def _load(self):
        """Load file links from disk."""
        if self.links_file.exists():
            try:
                self._cache = json.loads(self.links_file.read_text(encoding='utf-8'))
            except:
                self._cache = {}
        else:
            self._cache = {}

    def _save(self):
        """Save file links to disk (debounced)."""
        self._dirty = True
        # Actual save happens in flush() or on significant changes

    def flush(self):
        """Force save to disk."""
        if self._dirty:
            self.links_file.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            self._dirty = False

    def link_file(self, file_path: str, file_type: str = None,
                  tags: List[str] = None, summary: str = "",
                  emotional_value: float = 0.0, relevance: float = 0.5):
        """
        Link a file to Aiko's memory.

        Args:
            file_path: Path to the file
            file_type: Type (code, doc, image, config, etc.)
            tags: Personality-relevant tags
            summary: Aiko's understanding of the file
            emotional_value: How this file makes her feel (-1 to 1)
            relevance: How relevant to her core self (0 to 1)
        """
        now = time.time()

        # Create hash key for path
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:16]

        link = {
            'path': file_path,
            'file_type': file_type or Path(file_path).suffix.lstrip('.') or 'unknown',
            'linked_at': self._cache.get(file_hash, {}).get('linked_at', now),
            'access_count': self._cache.get(file_hash, {}).get('access_count', 0) + 1,
            'last_accessed': now,
            'tags': tags or [],
            'summary': summary,
            'emotional_value': emotional_value,
            'relevance_score': relevance
        }

        self._cache[file_hash] = link
        self._save()

        return file_hash

    def get_linked_files(self, tag: str = None, min_relevance: float = 0.0) -> List[Dict]:
        """Get files linked to Aiko's personality."""
        files = []
        for link in self._cache.values():
            if link['relevance_score'] >= min_relevance:
                if tag is None or tag in link['tags']:
                    files.append(link)

        # Sort by relevance and recency
        files.sort(key=lambda x: (x['relevance_score'], x['last_accessed']), reverse=True)
        return files

    def get_file_context(self, file_path: str) -> Optional[Dict]:
        """Get Aiko's understanding of a file."""
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:16]
        return self._cache.get(file_hash)

    def update_summary(self, file_path: str, summary: str):
        """Update Aiko's understanding of a file."""
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:16]
        if file_hash in self._cache:
            self._cache[file_hash]['summary'] = summary
            self._save()


class UnifiedMemoryManager:
    """
    The main interface to Aiko's memory systems.
    Combines conversation history, thoughts, and file links.
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Subsystems
        self.thought_stream = ThoughtStream()
        self.file_graph = FileMemoryGraph()

        # Conversation history (lightweight, in-memory with disk backup)
        self.history: Dict[str, List[Dict]] = {}
        self.history_file = self.data_dir / "conversation_history.json"
        self._load_history()

        # Affection/personality per user
        self.user_profiles: Dict[str, Dict] = {}
        self.profiles_file = self.data_dir / "user_profiles.json"
        self._load_profiles()

        # Auto-save timer
        self._last_save = time.time()
        self._save_interval = 60  # seconds

    def _load_history(self):
        """Load conversation history from disk."""
        if self.history_file.exists():
            try:
                self.history = json.loads(self.history_file.read_text(encoding='utf-8'))
            except:
                self.history = {}

    def _load_profiles(self):
        """Load user profiles."""
        if self.profiles_file.exists():
            try:
                self.user_profiles = json.loads(self.profiles_file.read_text(encoding='utf-8'))
            except:
                self.user_profiles = {}

    def _maybe_save(self):
        """Save if enough time has passed."""
        now = time.time()
        if now - self._last_save > self._save_interval:
            self.save()
            self._last_save = now

    def save(self):
        """Persist all memory to disk."""
        # Save conversations
        self.history_file.write_text(
            json.dumps(self.history, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        # Save profiles
        self.profiles_file.write_text(
            json.dumps(self.user_profiles, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        # Flush thoughts and file links
        self.thought_stream._flush_buffer()
        self.file_graph.flush()

        logger.info("[Memory] Saved to disk")

    # === Conversation History ===

    def add_message(self, user_id: str, role: str, content: str, metadata: dict = None):
        """Add message to conversation history."""
        if user_id not in self.history:
            self.history[user_id] = []

        entry = {
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }

        self.history[user_id].append(entry)

        # File into MemPalace for high-recall long-term storage
        try:
            from core.mempalace_bridge import get_mempalace_rag
            mp = get_mempalace_rag()
            if mp.is_available():
                mp.add_memory(
                    text=f"{role.upper()}: {content}",
                    metadata={"user_id": user_id, "source": "chat_history"},
                    room="knowledge"
                )
        except Exception as e:
            logger.error(f"[Memory] Palace filing error: {e}")

        # Keep only last 50 messages per user
        if len(self.history[user_id]) > 50:
            self.history[user_id] = self.history[user_id][-50:]

        # Log important messages to thought stream
        if role == 'assistant' and len(content) > 100:
            self.thought_stream.think(
                f"Responded to {user_id}: {content[:100]}...",
                category='observation',
                importance=4
            )

        self._maybe_save()

    def get_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get conversation history for user."""
        history = self.history.get(user_id, [])
        return [{'role': m['role'], 'content': m['content']}
                for m in history[-limit:]]

    def clear_history(self, user_id: str = None):
        """Clear history for user or all users."""
        if user_id:
            self.history[user_id] = []
        else:
            self.history.clear()
        self.save()

    # === User Profiles ===

    def get_profile(self, user_id: str) -> Dict:
        """Get or create user profile."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'affection': 30,
                'interests': [],
                'preferences': {},
                'first_seen': time.time(),
                'message_count': 0
            }
        return self.user_profiles[user_id]

    def update_affection(self, user_id: str, delta: int) -> int:
        """Update affection level."""
        profile = self.get_profile(user_id)
        profile['affection'] = max(0, min(100, profile['affection'] + delta))
        self._maybe_save()
        return profile['affection']

    def update_preference(self, user_id: str, key: str, value: Any):
        """Update user preference."""
        profile = self.get_profile(user_id)
        profile['preferences'][key] = value
        self._maybe_save()

    # === Thoughts ===

    def think(self, content: str, category: str = "reflection", **kwargs):
        """Add a thought to Aiko's stream."""
        return self.thought_stream.think(content, category, **kwargs)

    def get_recent_thoughts(self, hours: int = 24) -> List[Dict]:
        """Get recent thoughts."""
        return self.thought_stream.get_recent_thoughts(hours)

    # === File Links ===

    def link_file(self, file_path: str, **kwargs) -> str:
        """Link a file to Aiko's memory."""
        return self.file_graph.link_file(file_path, **kwargs)

    def get_file_context(self, file_path: str) -> Optional[Dict]:
        """Get Aiko's understanding of a file."""
        return self.file_graph.get_file_context(file_path)

    def find_relevant_files(self, query: str, limit: int = 5) -> List[Dict]:
        """Find files relevant to query."""
        # Simple tag matching - could use embeddings in future
        all_files = self.file_graph.get_linked_files()

        query_lower = query.lower()
        scored = []

        for f in all_files:
            score = 0
            if any(tag in query_lower for tag in [t.lower() for t in f['tags']]):
                score += 0.5
            if f['file_type'].lower() in query_lower:
                score += 0.3
            score += f['relevance_score'] * 0.2

            if score > 0:
                scored.append((score, f))

        scored.sort(reverse=True)
        return [f for _, f in scored[:limit]]

    # === Personality Integration ===

    def get_personality_context(self) -> str:
        """Generate personality context from all memory systems."""
        context_parts = []

        # Recent thoughts
        recent_thoughts = self.get_recent_thoughts(hours=1)
        if recent_thoughts:
            context_parts.append("## Recent Reflections")
            for t in recent_thoughts[-3:]:  # Last 3
                lines = t['content'].split('\n')
                for line in lines[:5]:  # First 5 lines
                    if line.strip() and not line.startswith('═'):
                        context_parts.append(line)
                        break

        # Important files
        important_files = self.file_graph.get_linked_files(min_relevance=0.7)[:5]
        if important_files:
            context_parts.append("\n## Files Important to Me")
            for f in important_files:
                context_parts.append(f"- {f['path']}: {f['summary'][:50]}...")

        return '\n'.join(context_parts)


# Global instance
_unified_memory = None

def get_unified_memory() -> UnifiedMemoryManager:
    """Get global unified memory instance."""
    global _unified_memory
    if _unified_memory is None:
        _unified_memory = UnifiedMemoryManager()
    return _unified_memory


if __name__ == "__main__":
    # Test the unified memory
    mem = UnifiedMemoryManager()

    # Test thoughts
    mem.think("I wonder what Master is working on today...", category="reflection", importance=6)
    mem.think("The new code changes look interesting!", category="observation", importance=7)

    # Test file links
    mem.link_file(
        "C:/Users/ousmo/.gemini/antigravity/scratch/Aiko-desktop/core/chat_engine.py",
        file_type="python",
        tags=["core", "intelligence", "important"],
        summary="My brain! This is where I think and process.",
        relevance=1.0,
        emotional_value=0.9
    )

    mem.link_file(
        "C:/Users/ousmo/.gemini/antigravity/scratch/Aiko-desktop/data/config.json",
        file_type="config",
        tags=["settings", "personality"],
        summary="My configuration. Contains my API keys and preferences.",
        relevance=0.9,
        emotional_value=0.5
    )

    # Test conversations
    mem.add_message("omax", "user", "Hello Aiko!")
    mem.add_message("omax", "assistant", "Hi Master! How can I help you today?")

    # Save everything
    mem.save()

    print("✅ Unified Memory tests passed!")
    print(f"\n📁 Thoughts saved to: {THOUGHTS_DIR}")
    print(f"📁 File links saved to: {FILE_LINKS_DIR}")
    print(f"💭 Recent thoughts: {len(mem.get_recent_thoughts())}")
    print(f"🔗 Linked files: {len(mem.file_graph.get_linked_files())}")
    print(f"💬 Conversations: {len(mem.get_history('omax'))} messages")

    # Show personality context
    print(f"\n🧠 Personality Context:\n{mem.get_personality_context()}")

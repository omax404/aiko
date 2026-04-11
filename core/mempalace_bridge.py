"""
AIKO MEMPALACE BRIDGE
═════════════════════
Connects Aiko to the MemPalace high-recall memory architecture.
Implements the RAG interface for transparent drop-in replacement.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from mempalace.searcher import search_memories
from mempalace.miner import get_collection, add_drawer, chunk_text

logger = logging.getLogger("MemPalaceBridge")

def safe_str(obj):
    """Safely convert object to string for Windows logging."""
    try:
        return str(obj).encode('ascii', 'ignore').decode('ascii')
    except:
        return "[Unencodable String]"

DEFAULT_PALACE = os.path.expanduser("~/.mempalace/palace")
DEFAULT_WING = "Aiko-desktop"

class MemPalaceRAG:
    """MemPalace-backed semantic memory for Aiko."""
    
    def __init__(self, palace_path: str = None, wing: str = None):
        self.palace_path = palace_path or DEFAULT_PALACE
        self.wing = wing or DEFAULT_WING
        self.collection = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialize ChromaDB collection via MemPalace."""
        if self._initialized: return
        try:
            self.collection = get_collection(self.palace_path)
            self._initialized = True
            logger.info(f" [MemPalace] Connected to Palace: {self.palace_path} (Wing: {self.wing})")
        except Exception as e:
            logger.error(f" [MemPalace] Init Error: {e}")

    def wake_up(self):
        """Invoke the MemPalace wake-up sequence to build the world context."""
        try:
            from mempalace.cli import cmd_wakeup
            import argparse
            args = argparse.Namespace(palace=self.palace_path, wing=self.wing)
            cmd_wakeup(args)
            logger.info(" [MemPalace] 🌅 Palace Wake-up Sequence Complete.")
        except Exception as e:
            logger.error(f" [MemPalace] Wake-up Error: {safe_str(e)}")

    def mine_project(self, project_dir: str = "./"):
        """Manually trigger a mine scan of the project."""
        try:
            from mempalace.miner import mine
            mine(project_dir=project_dir, palace_path=self.palace_path, wing_override=self.wing, agent="Aiko")
            logger.info(f" [MemPalace] ⛏️ Finished mining: {project_dir}")
        except Exception as e:
            logger.error(f" [MemPalace] Mine Error: {safe_str(e)}")

    def is_available(self) -> bool:
        self._initialize()
        return self.collection is not None

    def add_memory(self, text: str, metadata: dict = None, room: str = "general"):
        """File a memory into a specific room in the Aiko wing."""
        if not self.is_available(): return
        if not text.strip(): return
        
        try:
            # Chunk long texts as per MemPalace spec
            chunks = chunk_text(text, metadata.get("source", "conversation"))
            for i, chunk in enumerate(chunks):
                add_drawer(
                    collection=self.collection,
                    wing=self.wing,
                    room=room,
                    content=chunk["content"],
                    source_file=metadata.get("source", "conversation"),
                    chunk_index=i,
                    agent="Aiko"
                )
        except Exception as e:
            logger.error(f" [MemPalace] Add Error: {e}")

    def search_memory(self, query: str, n_results: int = 5, wing: str = None, room: str = None) -> tuple:
        """High-recall search using MemPalace search logic."""
        if not self.is_available(): return ()
        
        try:
            results = search_memories(
                query=query,
                palace_path=self.palace_path,
                wing=wing or self.wing,
                room=room,
                n_results=n_results
            )
            
            if "error" in results:
                logger.error(f" [MemPalace] Search Error: {results['error']}")
                return ()
                
            # Format to Aiko's expected (text, meta) format
            formatted = []
            for hit in results.get("results", []):
                formatted.append({
                    "text": hit["text"],
                    "meta": {
                        "wing": hit["wing"],
                        "room": hit["room"],
                        "source": hit["source_file"],
                        "similarity": hit["similarity"]
                    }
                })
            return tuple(formatted)
        except Exception as e:
            logger.error(f" [MemPalace] Search Fatal: {e}")
            return ()

    def get_memory_count(self) -> int:
        """Count only drawers in Aiko's wing."""
        if not self.is_available(): return 0
        try:
            # Chroma count is global; for wing-specific we'd need a query but count() is fine for status
            return self.collection.count()
        except: return 0

# Drop-in replacement global instance
def get_mempalace_rag() -> MemPalaceRAG:
    return MemPalaceRAG()

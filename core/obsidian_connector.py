
import os
import logging
from pathlib import Path

logger = logging.getLogger("Obsidian")

class ObsidianConnector:
    """Manages connection and interaction with an Obsidian vault."""
    
    def __init__(self, vault_path=None):
        self.vault_path = vault_path
        self.is_valid = False
        if vault_path:
            self.validate_vault()

    def validate_vault(self):
        """Check if the provided path is a valid Obsidian vault."""
        if not self.vault_path:
            self.is_valid = False
            return False
        
        path = Path(self.vault_path)
        if path.exists() and path.is_dir():
             self.is_valid = True
             logger.info(f"Obsidian Vault linked: {self.vault_path}")
             return True
        
        self.is_valid = False
        logger.warning(f"Invalid Obsidian Vault path: {self.vault_path}")
        return False

    def list_notes(self):
        """List all markdown notes in the vault."""
        if not self.is_valid: return []
        notes = []
        for p in Path(self.vault_path).rglob("*.md"):
            notes.append(str(p.relative_to(self.vault_path)))
        return notes

    def read_note(self, relative_path):
        """Read content of a specific note."""
        if not self.is_valid: return None
        full_path = Path(self.vault_path) / relative_path
        if not full_path.exists(): return None
        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading note {relative_path}: {e}")
            return None

    def create_note(self, relative_path, content):
        """Create or overwrite a note in the vault."""
        if not self.is_valid: return False
        if not relative_path.endswith(".md"): relative_path += ".md"
        full_path = Path(self.vault_path) / relative_path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Error creating note {relative_path}: {e}")
            return False

    def mine_vault(self, palace_bridge):
        """Index the entire vault into the MemPalace world context."""
        if not self.is_valid or not palace_bridge: return False
        logger.info(f" [Obsidian] ⛏️ Starting Mnemonic Mining of vault: {self.vault_path}")
        try:
            notes = self.list_notes()
            for note_path in notes:
                content = self.read_note(note_path)
                if content:
                    palace_bridge.add_memory(
                        text=content,
                        metadata={"source": note_path, "type": "obsidian_note"},
                        room="obsidian"
                    )
            return True
        except Exception as e:
            logger.error(f" [Obsidian] Mining Error: {e}")
            return False

    def get_daily_note_path(self):
        import datetime
        now = datetime.datetime.now()
        rel_path = f"05 - Dailies/{now.strftime('%Y-%m-%d')}.md"
        return rel_path

    def get_daily_note_content(self):
        """Read the content of today's daily note."""
        rel_path = self.get_daily_note_path()
        return self.read_note(rel_path)

    def append_to_daily(self, text):
        rel_path = self.get_daily_note_path()
        content = self.read_note(rel_path) or ""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M")
        new_content = f"{content}\n\n### Aiko Log [{timestamp}]\n{text}\n"
        return self.create_note(rel_path, new_content)


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
        # Check if directory exists and contains .obsidian
        if path.exists() and path.is_dir():
             # Technically a vault just needs to be a folder, 
             # but .obsidian usually exists.
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
        if not full_path.exists():
            return None
            
        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading note {relative_path}: {e}")
            return None

    def search_notes(self, query):
        """Simple keyword search across all notes."""
        if not self.is_valid: return []
        
        results = []
        query = query.lower()
        
        for p in Path(self.vault_path).rglob("*.md"):
            try:
                content = p.read_text(encoding="utf-8").lower()
                if query in content or query in p.name.lower():
                    results.append({
                        "path": str(p.relative_to(self.vault_path)),
                        "name": p.stem
                    })
            except:
                continue
        return results[:10] # Limit to 10 results

    def create_note(self, relative_path, content):
        """Create or overwrite a note in the vault."""
        if not self.is_valid: return False
        
        if not relative_path.endswith(".md"):
            relative_path += ".md"
            
        full_path = Path(self.vault_path) / relative_path
        
        try:
            # Create subdirectories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            logger.info(f"Created note: {relative_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating note {relative_path}: {e}")
            return False

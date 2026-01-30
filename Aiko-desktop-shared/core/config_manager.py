
"""
AIKO CONFIGURATION MANAGER
Handles persistent settings management (JSON).
"""
import json
import os
import logging

logger = logging.getLogger("Config")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")

DEFAULT_CONFIG = {
    "username": "User",
    "theme_mode": "dark",
    "vts_port": "8001",
    "tts_enabled": True,
    "last_model": "gpt-4o"
}

class ConfigManager:
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load configuration from disk."""
        if not os.path.exists(CONFIG_FILE):
            self.save() # Create default
            return

        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                # Merge with default to ensure all keys exist
                self._config = {**DEFAULT_CONFIG, **loaded}
                logger.info("Configuration loaded.")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = DEFAULT_CONFIG.copy()

    def save(self):
        """Save configuration to disk."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=4)
            logger.info("Configuration saved.")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value
        self.save() # Auto-save on change

    def get_all(self):
        return self._config.copy()

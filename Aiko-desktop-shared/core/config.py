"""
AIKO CONFIGURATION MANAGER
Centralized configuration management with environment variable support.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

class Config:
    """Centralized configuration manager."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file and environment variables."""
        # Default configuration
        self._config = {
            "ollama": {
                "url": "http://127.0.0.1:11434/api/chat",
                "model": "deepseek-v3.1:671b-cloud",
                "fallback_model": "deepseek-r1:1.5b",
                "timeout": 30
            },
            "vision": {
                "api_key": "",  # Load from environment
                "max_image_size": 1024
            },
            "vts": {
                "port": 8001,
                "plugin_name": "Aiko Controller",
                "developer": "AikoDev"
            },
            "ui": {
                "window_width": 1280,
                "window_height": 850,
                "theme": "dark"
            },
            "logging": {
                "level": "INFO",
                "file": "aiko.log"
            }
        }
        
        # Load from file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self._merge_config(self._config, file_config)
            except Exception as e:
                print(f" [!] Failed to load config file: {e}")
        
        # Override with environment variables
        self._load_env_vars()
    
    def _merge_config(self, base: Dict, update: Dict):
        """Recursively merge configuration dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _load_env_vars(self):
        """Load configuration from environment variables."""
        env_mappings = {
            "AIKO_OLLAMA_URL": ("ollama", "url"),
            "AIKO_OLLAMA_MODEL": ("ollama", "model"),
            "AIKO_OLLAMA_FALLBACK": ("ollama", "fallback_model"),
            "AIKO_VISION_API_KEY": ("vision", "api_key"),
            "AIKO_VTS_PORT": ("vts", "port"),
            "AIKO_LOG_LEVEL": ("logging", "level"),
            "AIKO_LOG_FILE": ("logging", "file")
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert port to integer
                if key == "port":
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                self._config[section][key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
    
    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f" [!] Failed to save config: {e}")
    
    def get_vision_api_key(self) -> str:
        """Get vision API key from config or environment."""
        api_key = self.get("vision", "api_key")
        if not api_key:
            api_key = os.getenv("AIKO_VISION_API_KEY", "")
        return api_key

# Global config instance
config = Config()
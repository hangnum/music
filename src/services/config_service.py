"""
Configuration Service Module

Manages application configuration read/write and hot updates.
"""

from typing import Any, Dict, Optional
from pathlib import Path
import os
import sys
import yaml
import threading
import logging

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Configuration Service - Singleton Pattern

    Manages application configuration, supporting reading and saving from YAML files.

    Usage Example:
        config = ConfigService("config/default_config.yaml")

        # Get configuration
        volume = config.get("playback.default_volume", 0.8)

        # Set configuration
        config.set("playback.default_volume", 0.9)
        config.save()
    """
    
    _instance: Optional['ConfigService'] = None
    _lock = threading.Lock()
    
    def __new__(cls, config_path: str = None) -> 'ConfigService':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = None):
        if self._initialized:
            return
        
        self._default_config_path = "config/default_config.yaml"
        default_path = Path(self._default_config_path)
        provided_path = Path(config_path) if config_path else None

        # Determine if using custom config path (for test/isolation scenarios)
        # Compatibility: When caller passes default template path, still use "default mode" (save to user directory) to avoid overwriting repository template files.
        self._use_custom_path = provided_path is not None and provided_path != default_path
        
        if self._use_custom_path:
            # Custom path: Used for both loading and saving (supports test isolation)
            self._user_config_path = provided_path
        else:
            # Default path: Load repository template, save to user directory
            self._user_config_path = self._get_user_config_path()
        
        self._config: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        self._load()
    
    @staticmethod
    def _get_user_config_path() -> Path:
        """Get user configuration file path (platform-specific)"""
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "python-music-player" / "config.yaml"
    
    def _load(self) -> None:
        """Load and merge from default and user configuration"""
        # 1. Load built-in default configuration
        self._config = self._get_default_config()
        
        if self._use_custom_path:
            # Custom path mode: Only load from this path (don't merge repository template)
            if self._user_config_path.exists():
                try:
                    with open(self._user_config_path, 'r', encoding='utf-8') as f:
                        custom_config = yaml.safe_load(f) or {}
                        self._deep_merge(self._config, custom_config)
                except Exception as e:
                    logger.warning("Failed to load custom configuration: %s", e)
        else:
            # Default mode: Load repository template + user configuration
            # 2. Load repository default configuration file (as template)
            default_path = Path(self._default_config_path)
            if default_path.exists():
                try:
                    with open(default_path, 'r', encoding='utf-8') as f:
                        default_config = yaml.safe_load(f) or {}
                        self._deep_merge(self._config, default_config)
                except Exception as e:
                    logger.warning("Failed to load default configuration: %s", e)
            
            # 3. Load user configuration file (override default configuration)
            if self._user_config_path.exists():
                try:
                    with open(self._user_config_path, 'r', encoding='utf-8') as f:
                        user_config = yaml.safe_load(f) or {}
                        self._deep_merge(self._config, user_config)
                except Exception as e:
                    logger.warning("Failed to load user configuration: %s", e)
    
    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge dictionaries, override overwrites base"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'app': {
                'name': 'Python Music Player',
                'version': '1.0.0',
                'language': 'zh_CN',
                'theme': 'dark',
            },
            'audio': {
                'backend': 'pygame',
                'buffer_size': 2048,
            },
            'playback': {
                'default_volume': 0.8,
                'fade_duration': 500,
                'remember_position': True,
                'persist_queue': True,
                'persist_queue_max_items': 500,
            },
            'library': {
                'directories': [],
                'watch_for_changes': True,
                'scan_on_startup': True,
                'supported_formats': ['mp3', 'flac', 'wav', 'ogg', 'm4a', 'aac'],
            },
            'ui': {
                'window_width': 1200,
                'window_height': 800,
                'sidebar_width': 240,
                'show_album_art': True,
            },
            'shortcuts': {
                'play_pause': 'Space',
                'next_track': 'Ctrl+Right',
                'previous_track': 'Ctrl+Left',
                'volume_up': 'Ctrl+Up',
                'volume_down': 'Ctrl+Down',
                'mute': 'M',
            },
            'llm': {
                'provider': 'siliconflow',
                'siliconflow': {
                    'base_url': 'https://api.siliconflow.cn/v1',
                    'model': 'Qwen/Qwen2.5-7B-Instruct',
                    'api_key_env': 'SILICONFLOW_API_KEY',
                    'api_key': '',
                    'timeout_seconds': 20.0,
                },
                'queue_manager': {
                    'max_items': 50,        # Maximum queue items to send to LLM
                    'max_tokens': 2048,     # Increased to prevent JSON truncation
                    'temperature': 0.2,
                    'json_mode': True,      # Try to use response_format=json_object
                    'cache': {
                        'enabled': True,
                        'ttl_days': 30,
                        'max_history': 80,
                        'max_items': 200,
                    },
                    'semantic_fallback': {
                        'max_catalog_items': 1500,   # Maximum tracks to traverse during semantic filtering (paginated by brief info)
                        'batch_size': 250,           # Number of candidate tracks sent to LLM each time
                        'per_batch_pick': 8,         # Maximum tracks picked per batch
                    },
                },
                'web_search': {
                    'enabled': True,      # Whether to enable enhanced web search
                    'timeout': 10.0,      # Search timeout (seconds)
                    'max_cache_size': 100, # Maximum cache entries
                    'region': 'cn-zh',    # Search region
                },
            },
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Supports dot-separated nested keys, e.g., "playback.default_volume".
        
        Args:
            key: Configuration key
            default: Default value
            
        Returns:
            Configuration value or the default value.
        """
        with self._lock:
            keys = key.split('.')
            value = self._config
            
            try:
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (dot-separated)
            value: Configuration value
        """
        with self._lock:
            keys = key.split('.')
            config = self._config
            
            # Navigate to the parent node
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configurations."""
        with self._lock:
            return self._config.copy()
    
    def save(self) -> bool:
        """
        Save configuration to the user configuration file.
        
        Note: Only saves to the user configuration file; does not modify the default configuration template.
        
        Returns:
            bool: True if saving was successful.
        """
        try:
            self._user_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                with open(self._user_config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
            logger.debug("Configuration saved to: %s", self._user_config_path)
            return True
        except Exception as e:
            logger.error("Failed to save configuration: %s", e)
            return False
    
    def reload(self) -> bool:
        """
        Reload configuration

        Returns:
            bool: Whether loading was successful
        """
        try:
            self._load()
            return True
        except Exception:
            return False
    
    def reset(self) -> None:
        """Reset to default configuration."""
        with self._lock:
            self._config = self._get_default_config()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing only)."""
        with cls._lock:
            cls._instance = None

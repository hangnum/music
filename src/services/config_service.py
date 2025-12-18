"""
配置服务模块

管理应用配置的读写和热更新。
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
    配置服务 - 单例模式
    
    管理应用配置，支持从YAML文件读取和保存配置。
    
    使用示例:
        config = ConfigService("config/default_config.yaml")
        
        # 获取配置
        volume = config.get("playback.default_volume", 0.8)
        
        # 设置配置
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
        
        # 判断是否使用自定义配置路径（用于测试/隔离场景）
        self._use_custom_path = config_path is not None
        self._default_config_path = "config/default_config.yaml"
        
        if self._use_custom_path:
            # 自定义路径：同时用于加载和保存（支持测试隔离）
            self._user_config_path = Path(config_path)
        else:
            # 默认路径：加载仓库模板，保存到用户目录
            self._user_config_path = self._get_user_config_path()
        
        self._config: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        self._load()
    
    @staticmethod
    def _get_user_config_path() -> Path:
        """获取用户配置文件路径（平台相关）"""
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "python-music-player" / "config.yaml"
    
    def _load(self) -> None:
        """从默认配置和用户配置加载并合并"""
        # 1. 加载内置默认配置
        self._config = self._get_default_config()
        
        if self._use_custom_path:
            # 自定义路径模式：只从该路径加载（不合并仓库模板）
            if self._user_config_path.exists():
                try:
                    with open(self._user_config_path, 'r', encoding='utf-8') as f:
                        custom_config = yaml.safe_load(f) or {}
                        self._deep_merge(self._config, custom_config)
                except Exception as e:
                    logger.warning("加载自定义配置失败: %s", e)
        else:
            # 默认模式：加载仓库模板 + 用户配置
            # 2. 加载仓库默认配置文件（作为模板）
            default_path = Path(self._default_config_path)
            if default_path.exists():
                try:
                    with open(default_path, 'r', encoding='utf-8') as f:
                        default_config = yaml.safe_load(f) or {}
                        self._deep_merge(self._config, default_config)
                except Exception as e:
                    logger.warning("加载默认配置失败: %s", e)
            
            # 3. 加载用户配置文件（覆盖默认配置）
            if self._user_config_path.exists():
                try:
                    with open(self._user_config_path, 'r', encoding='utf-8') as f:
                        user_config = yaml.safe_load(f) or {}
                        self._deep_merge(self._config, user_config)
                except Exception as e:
                    logger.warning("加载用户配置失败: %s", e)
    
    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """深度合并字典，override 覆盖 base"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
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
                    'max_items': 50,        # 发送给 LLM 的队列条目上限
                    'max_tokens': 512,
                    'temperature': 0.2,
                    'json_mode': True,      # 尝试使用 response_format=json_object
                    'cache': {
                        'enabled': True,
                        'ttl_days': 30,
                        'max_history': 80,
                        'max_items': 200,
                    },
                    'semantic_fallback': {
                        'max_catalog_items': 1500,   # 语义筛选时最多遍历的库曲目数量（按简要信息分页发送）
                        'batch_size': 250,           # 每次发送给 LLM 的候选曲目数量
                        'per_batch_pick': 8,         # 每批最多挑选的曲目数量
                    },
                },
            },
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        支持点号分隔的嵌套键，如 "playback.default_volume"
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值或默认值
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
        设置配置值
        
        Args:
            key: 配置键（支持点号分隔）
            value: 配置值
        """
        with self._lock:
            keys = key.split('.')
            config = self._config
            
            # 导航到父节点
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        with self._lock:
            return self._config.copy()
    
    def save(self) -> bool:
        """
        保存配置到用户配置文件
        
        注意：只保存到用户配置文件，不会修改默认配置模板。
        
        Returns:
            bool: 是否保存成功
        """
        try:
            self._user_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                with open(self._user_config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
            logger.debug("配置已保存到: %s", self._user_config_path)
            return True
        except Exception as e:
            logger.error("保存配置失败: %s", e)
            return False
    
    def reload(self) -> bool:
        """
        重新加载配置
        
        Returns:
            bool: 是否加载成功
        """
        try:
            self._load()
            return True
        except Exception:
            return False
    
    def reset(self) -> None:
        """重置为默认配置"""
        with self._lock:
            self._config = self._get_default_config()
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（仅用于测试）"""
        with cls._lock:
            cls._instance = None

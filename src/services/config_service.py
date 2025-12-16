"""
配置服务模块

管理应用配置的读写和热更新。
"""

from typing import Any, Dict, Optional
from pathlib import Path
import yaml
import threading


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
        
        self._config_path = config_path or "config/default_config.yaml"
        self._config: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        self._load()
    
    def _load(self) -> None:
        """从文件加载配置"""
        path = Path(self._config_path)
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[ConfigService] 加载配置失败: {e}")
                self._config = {}
        else:
            self._config = self._get_default_config()
    
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
        保存配置到文件
        
        Returns:
            bool: 是否保存成功
        """
        try:
            path = Path(self._config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            print(f"[ConfigService] 保存配置失败: {e}")
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

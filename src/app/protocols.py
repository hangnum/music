# -*- coding: utf-8 -*-
"""
协议定义模块

定义应用程序中所有服务的接口协议（Protocol）。
使用 Protocol 而非 ABC，以支持结构化子类型检查（structural subtyping）。

设计决策：
- 默认使用 Protocol + @runtime_checkable
- ABC 仅用于需要共享默认实现的基类（如 AudioEngineBase）
- 运行时检查只在容器装配或测试中做一次性断言
"""

from __future__ import annotations

from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)

if TYPE_CHECKING:
    from models.track import Track


# =============================================================================
# 事件总线协议
# =============================================================================

@runtime_checkable
class IEventBus(Protocol):
    """事件总线接口
    
    提供发布-订阅模式的事件系统。
    """
    
    def subscribe(
        self, 
        event_type: Enum, 
        callback: Callable[[Any], None]
    ) -> str:
        """订阅事件
        
        Args:
            event_type: 事件类型枚举
            callback: 回调函数
            
        Returns:
            订阅ID，用于取消订阅
        """
        ...
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅
        
        Args:
            subscription_id: 订阅时返回的ID
            
        Returns:
            是否成功取消
        """
        ...
    
    def publish(self, event_type: Enum, data: Any = None) -> None:
        """发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        ...
    
    def publish_sync(
        self, 
        event_type: Enum, 
        data: Any = None, 
        timeout: Optional[float] = None
    ) -> bool:
        """同步发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            timeout: 超时时间
            
        Returns:
            是否在超时前完成
        """
        ...


# =============================================================================
# 数据库协议
# =============================================================================

# 从 core.ports 重导出基础设施接口
from core.ports.database import IDatabase as _IDatabase, ITrackRepository
from core.ports.audio import IAudioEngine, IAudioEngineFactory
from core.ports.llm import ILLMProvider, ILLMProviderFactory, LLMSettings

# 保持向后兼容
IDatabase = _IDatabase


# =============================================================================
# 配置服务协议
# =============================================================================

@runtime_checkable
class IConfigService(Protocol):
    """配置服务接口"""
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值
        """
        ...
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        ...
    
    def save(self) -> None:
        """保存配置到文件"""
        ...


# =============================================================================
# 播放服务协议
# =============================================================================

@runtime_checkable
class IPlayerService(Protocol):
    """播放服务接口"""
    
    def play(self, track: Optional["Track"] = None) -> bool:
        """播放曲目"""
        ...
    
    def pause(self) -> None:
        """暂停播放"""
        ...
    
    def resume(self) -> None:
        """恢复播放"""
        ...
    
    def stop(self) -> None:
        """停止播放"""
        ...
    
    def next_track(self) -> Optional["Track"]:
        """下一曲"""
        ...
    
    def previous_track(self) -> Optional["Track"]:
        """上一曲"""
        ...
    
    def seek(self, position_ms: int) -> None:
        """跳转到指定位置"""
        ...
    
    def set_volume(self, volume: float) -> None:
        """设置音量 (0.0 - 1.0)"""
        ...
    
    def get_volume(self) -> float:
        """获取当前音量"""
        ...
    
    @property
    def is_playing(self) -> bool:
        """是否正在播放"""
        ...
    
    @property
    def current_track(self) -> Optional["Track"]:
        """当前播放的曲目"""
        ...
    
    @property
    def queue(self) -> List["Track"]:
        """播放队列"""
        ...
    
    def set_queue(self, tracks: List["Track"], start_index: int = 0) -> None:
        """设置播放队列"""
        ...
    
    def toggle_play(self) -> None:
        """切换播放/暂停"""
        ...


# =============================================================================
# 媒体库服务协议
# =============================================================================

@runtime_checkable
class ILibraryService(Protocol):
    """媒体库服务接口"""
    
    def scan_async(self, directories: List[str]) -> None:
        """异步扫描目录"""
        ...
    
    def get_all_tracks(self) -> List["Track"]:
        """获取所有曲目"""
        ...
    
    def get_track(self, track_id: str) -> Optional["Track"]:
        """获取单个曲目"""
        ...
    
    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """搜索媒体库"""
        ...
    
    def get_track_count(self) -> int:
        """获取曲目总数"""
        ...


# =============================================================================
# 歌单服务协议
# =============================================================================

@runtime_checkable
class IPlaylistService(Protocol):
    """歌单服务接口"""
    
    def create(self, name: str, description: str = "") -> Any:
        """创建歌单"""
        ...
    
    def get_all(self) -> List[Any]:
        """获取所有歌单"""
        ...
    
    def get(self, playlist_id: str) -> Optional[Any]:
        """获取单个歌单"""
        ...
    
    def add_track(self, playlist_id: str, track_id: str) -> bool:
        """添加曲目到歌单"""
        ...
    
    def remove_track(self, playlist_id: str, track_id: str) -> bool:
        """从歌单移除曲目"""
        ...

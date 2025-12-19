# -*- coding: utf-8 -*-
"""
事件总线模块 - 发布订阅模式实现

提供模块间松耦合的通信机制。

设计说明：
- 这是纯 Python 实现，不依赖任何 UI 框架
- Qt 主线程派发已移至 ui/qt_event_bus.py 的 QtEventBusAdapter
- 如需在 Qt 环境中使用，请使用 AppContainerFactory 创建的适配器
"""

from typing import Dict, Callable, Any, Optional
from enum import Enum
import threading
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    
    # 播放事件
    TRACK_LOADED = "track_loaded"
    TRACK_STARTED = "track_started"
    TRACK_ENDED = "track_ended"
    PLAYBACK_STOPPED = "playback_stopped"  # 手动停止（区分自然结束）
    TRACK_PAUSED = "track_paused"
    TRACK_RESUMED = "track_resumed"
    POSITION_CHANGED = "position_changed"
    VOLUME_CHANGED = "volume_changed"
    
    # 播放列表事件
    PLAYLIST_CREATED = "playlist_created"
    PLAYLIST_UPDATED = "playlist_updated"
    PLAYLIST_DELETED = "playlist_deleted"
    QUEUE_CHANGED = "queue_changed"
    
    # 媒体库事件
    LIBRARY_SCAN_STARTED = "library_scan_started"
    LIBRARY_SCAN_PROGRESS = "library_scan_progress"
    LIBRARY_SCAN_COMPLETED = "library_scan_completed"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"
    
    # 系统事件
    CONFIG_CHANGED = "config_changed"
    THEME_CHANGED = "theme_changed"
    ERROR_OCCURRED = "error_occurred"


class EventBus:
    """
    事件总线 - 单例模式
    
    提供发布-订阅模式的事件系统，支持异步事件处理。
    
    注意：这是纯 Python 实现。如需在 Qt UI 中使用（确保回调在主线程执行），
    请通过 AppContainerFactory 获取 QtEventBusAdapter 包装后的实例。
    
    使用示例:
        event_bus = EventBus()
        
        # 订阅事件
        def on_track_started(track):
            logger.info("播放: %s", track.title)
        
        sub_id = event_bus.subscribe(EventType.TRACK_STARTED, on_track_started)
        
        # 发布事件
        event_bus.publish(EventType.TRACK_STARTED, track)
        
        # 取消订阅
        event_bus.unsubscribe(sub_id)
    """
    
    _instance: Optional['EventBus'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._subscribers: Dict[EventType, Dict[str, Callable]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="EventBus")
        self._sub_lock = threading.Lock()
        self._initialized = True
    
    def subscribe(
        self, 
        event_type: EventType, 
        callback: Callable[[Any], None]
    ) -> str:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数，接收事件数据作为参数
            
        Returns:
            str: 订阅ID，用于取消订阅
        """
        subscription_id = str(uuid.uuid4())
        
        with self._sub_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = {}
            self._subscribers[event_type][subscription_id] = callback
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅时返回的ID
            
        Returns:
            bool: 是否成功取消
        """
        with self._sub_lock:
            for event_type in self._subscribers:
                if subscription_id in self._subscribers[event_type]:
                    del self._subscribers[event_type][subscription_id]
                    return True
        return False
    
    def publish(self, event_type: EventType, data: Any = None) -> None:
        """
        异步发布事件
        
        回调函数将在线程池中异步执行。
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        with self._sub_lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())

        for callback in callbacks:
            self._executor.submit(self._safe_call, callback, data)
    
    def publish_sync(
        self,
        event_type: EventType,
        data: Any = None,
        timeout: Optional[float] = 5.0,
    ) -> bool:
        """
        同步发布事件
        
        在当前线程中同步执行所有回调。
        
        Args:
            event_type: 事件类型
            data: 事件数据
            timeout: 此参数保留以兼容接口，在纯 Python 实现中不使用

        Returns:
            bool: 始终返回 True（同步执行无超时问题）
        """
        with self._sub_lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())

        for callback in callbacks:
            self._safe_call(callback, data)
    
        return True

    def _safe_call(self, callback: Callable, data: Any) -> None:
        """安全调用回调函数"""
        try:
            callback(data)
        except Exception as e:
            # 避免循环：不使用publish发布错误事件
            logger.error("事件回调执行错误: %s", e)
    
    def clear(self) -> None:
        """清除所有订阅"""
        with self._sub_lock:
            self._subscribers.clear()
    
    def shutdown(self) -> None:
        """关闭事件总线"""
        self._executor.shutdown(wait=True)
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（仅用于测试）
        
        警告：此方法将在未来版本中移除。
        请使用 AppContainerFactory.create_for_testing() 创建独立的测试实例。
        """
        import warnings
        warnings.warn(
            "EventBus.reset_instance() is deprecated and will be removed. "
            "Use AppContainerFactory.create_for_testing() for isolated test instances.",
            FutureWarning,
            stacklevel=2
        )
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
                cls._instance = None

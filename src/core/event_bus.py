"""
事件总线模块 - 发布订阅模式实现

提供模块间松耦合的通信机制。
"""

from typing import Dict, Callable, Any, Optional
from enum import Enum
import threading
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import QObject, pyqtSignal, Qt, QCoreApplication
except Exception:  # PyQt6 may be unavailable in non-UI environments
    QObject = None  # type: ignore[assignment]
    pyqtSignal = None  # type: ignore[assignment]
    Qt = None  # type: ignore[assignment]
    QCoreApplication = None  # type: ignore[assignment]


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
        self._lock = threading.Lock()

        # If a Qt application exists, dispatch callbacks onto the Qt main thread.
        # This prevents crashes/hangs caused by updating Qt widgets from worker threads.
        self._qt_dispatcher = None
        self._qt_thread = None
        self._ensure_qt_dispatcher()

        self._initialized = True

    def _ensure_qt_dispatcher(self) -> None:
        """Initialize Qt dispatcher if a Qt app is running."""
        if self._qt_dispatcher is not None:
            return
        if QCoreApplication is None or QObject is None or pyqtSignal is None:
            return
        app = QCoreApplication.instance()
        if app is None:
            return

        try:
            dispatcher = _QtDispatcher()
            qt_thread = app.thread()
            try:
                dispatcher.moveToThread(qt_thread)
            except Exception:
                pass
            self._qt_dispatcher = dispatcher
            self._qt_thread = qt_thread
        except Exception:
            self._qt_dispatcher = None
            self._qt_thread = None
    
    def subscribe(self, event_type: EventType, 
                  callback: Callable[[Any], None]) -> str:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数，接收事件数据作为参数
            
        Returns:
            str: 订阅ID，用于取消订阅
        """
        subscription_id = str(uuid.uuid4())
        
        with self._lock:
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
        with self._lock:
            for event_type in self._subscribers:
                if subscription_id in self._subscribers[event_type]:
                    del self._subscribers[event_type][subscription_id]
                    return True
        return False
    
    def publish(self, event_type: EventType, data: Any = None) -> None:
        """
        异步发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())

        self._ensure_qt_dispatcher()
        for callback in callbacks:
            if self._qt_dispatcher is not None:
                self._qt_dispatcher.dispatch.emit(callback, data)
            else:
                self._executor.submit(self._safe_call, callback, data)
    
    def publish_sync(
        self,
        event_type: EventType,
        data: Any = None,
        timeout: Optional[float] = 5.0,
    ) -> bool:
        """
        同步发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            timeout: Wait seconds for Qt-thread callbacks; None to wait indefinitely.

        Returns:
            bool: True if all callbacks finished before timeout.
        """
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())

        self._ensure_qt_dispatcher()
        all_completed = True
        for callback in callbacks:
            if self._qt_dispatcher is not None and self._qt_thread is not None:
                # If we're not on the Qt thread, queue and block until done.
                current_qt_thread = None
                if Qt is not None:
                    try:
                        from PyQt6.QtCore import QThread
                        current_qt_thread = QThread.currentThread()
                    except Exception:
                        current_qt_thread = None

                if current_qt_thread is not None and current_qt_thread != self._qt_thread:
                    done = threading.Event()
                    self._qt_dispatcher.dispatch_sync.emit(callback, data, done)
                    if timeout is None:
                        completed = done.wait()
                    else:
                        completed = done.wait(timeout=timeout)
                    if not completed:
                        logger.warning("EventBus.publish_sync timed out waiting for callback: %s", callback)
                        all_completed = False
                else:
                    self._safe_call(callback, data)
            else:
                self._safe_call(callback, data)
    
        return all_completed

    def _safe_call(self, callback: Callable, data: Any) -> None:
        """安全调用回调函数"""
        try:
            callback(data)
        except Exception as e:
            # 避免循环：不使用publish发布错误事件
            logger.error("回调执行错误: %s", e)
    
    def clear(self) -> None:
        """清除所有订阅"""
        with self._lock:
            self._subscribers.clear()
    
    def shutdown(self) -> None:
        """关闭事件总线"""
        self._executor.shutdown(wait=True)
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（仅用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
                cls._instance = None


if QObject is not None and pyqtSignal is not None:
    class _QtDispatcher(QObject):
        dispatch = pyqtSignal(object, object)           # callback, data
        dispatch_sync = pyqtSignal(object, object, object)  # callback, data, threading.Event

        def __init__(self):
            super().__init__()
            self.dispatch.connect(self._on_dispatch, Qt.ConnectionType.QueuedConnection)
            self.dispatch_sync.connect(self._on_dispatch_sync, Qt.ConnectionType.QueuedConnection)

        def _on_dispatch(self, callback: Callable, data: Any) -> None:
            try:
                callback(data)
            except Exception as e:
                logger.error("回调执行错误: %s", e)

        def _on_dispatch_sync(self, callback: Callable, data: Any, done: threading.Event) -> None:
            try:
                callback(data)
            except Exception as e:
                logger.error("回调执行错误: %s", e)
            finally:
                try:
                    done.set()
                except Exception:
                    pass

# -*- coding: utf-8 -*-
"""
Event Bus Module - Publish-Subscribe Pattern Implementation

Provides loose-coupled communication mechanism between modules.

Design Notes:
- This is a pure Python implementation, does not depend on any UI framework
- Qt main thread dispatch has been moved to QtEventBusAdapter in ui/qt_event_bus.py
- If using in Qt environment, please use the adapter created by AppContainerFactory
"""

from typing import Dict, Callable, Any, Optional
from enum import Enum
import threading
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event type enumeration"""
    
    # Playback events
    TRACK_LOADED = "track_loaded"
    TRACK_STARTED = "track_started"
    TRACK_ENDED = "track_ended"
    PLAYBACK_STOPPED = "playback_stopped"  # Manual stop (distinguished from natural end)
    TRACK_PAUSED = "track_paused"
    TRACK_RESUMED = "track_resumed"
    POSITION_CHANGED = "position_changed"
    VOLUME_CHANGED = "volume_changed"
    
    # Playlist events
    PLAYLIST_CREATED = "playlist_created"
    PLAYLIST_UPDATED = "playlist_updated"
    PLAYLIST_DELETED = "playlist_deleted"
    QUEUE_CHANGED = "queue_changed"
    
    # Library events
    LIBRARY_SCAN_STARTED = "library_scan_started"
    LIBRARY_SCAN_PROGRESS = "library_scan_progress"
    LIBRARY_SCAN_COMPLETED = "library_scan_completed"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"
    
    # System events
    CONFIG_CHANGED = "config_changed"
    THEME_CHANGED = "theme_changed"
    ERROR_OCCURRED = "error_occurred"


class EventBus:
    """
    Event Bus - Singleton Pattern
    
    Provides publish-subscribe pattern event system, supports asynchronous event handling.
    
    Note: This is a pure Python implementation. If using in Qt UI (to ensure callbacks execute in main thread),
    please get the QtEventBusAdapter wrapped instance through AppContainerFactory.
    
    Usage example:
        event_bus = EventBus()
        
        # Subscribe to event
        def on_track_started(track):
            logger.info("Playing: %s", track.title)
        
        sub_id = event_bus.subscribe(EventType.TRACK_STARTED, on_track_started)
        
        # Publish event
        event_bus.publish(EventType.TRACK_STARTED, track)
        
        # Unsubscribe
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
        Subscribe to event
        
        Args:
            event_type: Event type
            callback: Callback function, receiving event data as an argument
            
        Returns:
            str: Subscription ID, used for unsubscription
        """
        subscription_id = str(uuid.uuid4())
        
        with self._sub_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = {}
            self._subscribers[event_type][subscription_id] = callback
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe
        
        Args:
            subscription_id: The ID returned when subscribing
            
        Returns:
            bool: Whether the unsubscription was successful
        """
        with self._sub_lock:
            for event_type in self._subscribers:
                if subscription_id in self._subscribers[event_type]:
                    del self._subscribers[event_type][subscription_id]
                    return True
        return False
    
    def publish(self, event_type: EventType, data: Any = None) -> None:
        """
        Publish event asynchronously
        
        The callback function will be executed asynchronously in the thread pool.
        
        Args:
            event_type: Event type
            data: Event data
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
        Publish event synchronously
        
        All callbacks will be executed synchronously in the current thread.
        
        Args:
            event_type: Event type
            data: Event data
            timeout: This parameter is kept for interface compatibility; it is not used in the pure Python implementation.

        Returns:
            bool: Always returns True (synchronous execution has no timeout issues)
        """
        with self._sub_lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())

        for callback in callbacks:
            self._safe_call(callback, data)
    
        return True

    def _safe_call(self, callback: Callable, data: Any) -> None:
        """Safely call a callback function"""
        try:
            callback(data)
        except Exception as e:
            # Avoid loop: Do not use publish to report error events
            logger.error("Event callback execution error: %s", e)
    
    def clear(self) -> None:
        """Clear all subscriptions"""
        with self._sub_lock:
            self._subscribers.clear()
    
    def shutdown(self) -> None:
        """Shutdown the event bus"""
        self._executor.shutdown(wait=True)
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing only)
        
        Warning: This method will be removed in a future version.
        Please use AppContainerFactory.create_for_testing() to create independent test instances.
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

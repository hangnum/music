# -*- coding: utf-8 -*-
"""
Qt Event Bus Adapter

Dispatches callbacks from the pure Python EventBus to the Qt main thread, 
decoupling the core layer from Qt.

Design Principles:
- The core layer's EventBus remains pure Python and does not depend on Qt.
- Qt main thread dispatch logic is fully implemented in the UI layer.
- Bridges the two via the adapter pattern.
- publish_sync must wait for all Qt callbacks to complete.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal

if TYPE_CHECKING:
    from enum import Enum
    from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class QtEventBusAdapter(QObject):
    """Qt Event Bus Adapter
    
    Dispatches callbacks to the Qt main thread, ensuring UI updates are performed there.
    
    How it works:
    1. During subscribe, the original callback is registered in a local registry, and a wrapper is registered with the internal bus.
    2. During publish, the internal bus calls the wrapper, which emits a Qt signal to asynchronously dispatch to the main thread.
    3. During publish_sync, the local registry is traversed, using synchronous signals to wait for each callback to complete.
    
    Usage Example:
        from core.event_bus import EventBus
        
        pure_bus = EventBus()
        qt_bus = QtEventBusAdapter(pure_bus)
        
        # Now events can be published from any thread, and callbacks will execute in the main thread.
        qt_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
    """
    
    # Asynchronous dispatch signal
    _dispatch_signal = pyqtSignal(object, object)
    # Synchronous dispatch signal (with completion event)
    _dispatch_sync_signal = pyqtSignal(object, object, object)
    
    def __init__(self, inner_bus: "EventBus"):
        """Initialize the adapter.
        
        Args:
            inner_bus: The underlying pure Python EventBus.
            
        Raises:
            RuntimeError: If no Qt application instance is running.
        """
        super().__init__()
        
        # Ensure execution in the Qt main thread: move to application main thread
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            raise RuntimeError(
                "QtEventBusAdapter requires a running QApplication instance. "
                "Please create a QApplication before initializing the adapter."
            )
        
        main_thread = app.thread()
        if QThread.currentThread() != main_thread:
            # If not created in the main thread, move to it
            self.moveToThread(main_thread)
            logger.debug("QtEventBusAdapter moved to Qt main thread")
        
        self._bus = inner_bus
        self._lock = threading.Lock()
        
        # Local callback registry: {subscription_id: (event_type, original_callback)}
        # Used for direct dispatch to the Qt main thread during publish_sync.
        self._callbacks: Dict[str, tuple] = {}
        
        # Index by event type: {event_type: {subscription_id: original_callback}}
        self._callbacks_by_type: Dict[Any, Dict[str, Callable]] = {}
        
        # Connect signals to slots using QueuedConnection to ensure execution in the main thread.
        self._dispatch_signal.connect(
            self._on_dispatch,
            Qt.ConnectionType.QueuedConnection
        )
        self._dispatch_sync_signal.connect(
            self._on_dispatch_sync,
            Qt.ConnectionType.QueuedConnection
        )
    
    def subscribe(
        self,
        event_type: "Enum",
        callback: Callable[[Any], None]
    ) -> str:
        """Subscribe to an event.
        
        Callbacks will be executed in the Qt main thread.
        
        Args:
            event_type: Event type
            callback: Callback function
            
        Returns:
            Subscription ID
        """
        def qt_wrapper(data: Any) -> None:
            """Wrap the callback to emit as a Qt signal (asynchronous)."""
            self._dispatch_signal.emit(callback, data)
        
        # Register the wrapper with the internal bus
        subscription_id = self._bus.subscribe(event_type, qt_wrapper)
        
        # Save the original callback in the local registry (for publish_sync)
        with self._lock:
            self._callbacks[subscription_id] = (event_type, callback)
            if event_type not in self._callbacks_by_type:
                self._callbacks_by_type[event_type] = {}
            self._callbacks_by_type[event_type][subscription_id] = callback
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from an event.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            True if successfully unsubscribed.
        """
        result = self._bus.unsubscribe(subscription_id)
        
        # Remove from local registry
        with self._lock:
            if subscription_id in self._callbacks:
                event_type, _ = self._callbacks.pop(subscription_id)
                if event_type in self._callbacks_by_type:
                    self._callbacks_by_type[event_type].pop(subscription_id, None)
        
        return result
    
    def publish(self, event_type: "Enum", data: Any = None) -> None:
        """Publish an event (asynchronous).
        
        The callback will be dispatched via Qt signal to the main thread for execution.
        
        Args:
            event_type: Event type
            data: Event data
        """
        self._bus.publish(event_type, data)
    
    def publish_sync(
        self,
        event_type: "Enum",
        data: Any = None,
        timeout: Optional[float] = 5.0
    ) -> bool:
        """Publish an event synchronously.
        
        Waits for all callbacks to finish in the Qt main thread before returning.
        If currently in the Qt main thread, executes callbacks directly to avoid deadlock.
        
        Args:
            event_type: Event type
            data: Event data
            timeout: Timeout for each callback (seconds)
            
        Returns:
            True if all callbacks completed before the timeout.
        """
        # Get the list of callbacks to be called
        with self._lock:
            callbacks = list(self._callbacks_by_type.get(event_type, {}).values())
        
        if not callbacks:
            return True
        
        # Check if in the Qt main thread
        try:
            current_thread = QThread.currentThread()
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                main_thread = app.thread()
                is_main_thread = (current_thread == main_thread)
            else:
                is_main_thread = False
        except Exception:
            is_main_thread = False
        
        all_completed = True
        
        for callback in callbacks:
            if is_main_thread:
                # Already in main thread, execute directly
                try:
                    callback(data)
                except Exception as e:
                    logger.error("Qt event callback execution failed: %s", e)
            else:
                # In worker thread, dispatch via sync signal and wait
                done_event = threading.Event()
                self._dispatch_sync_signal.emit(callback, data, done_event)
                
                if timeout is None:
                    completed = done_event.wait()
                else:
                    completed = done_event.wait(timeout=timeout)
                
                if not completed:
                    logger.warning(
                        "QtEventBusAdapter.publish_sync timed out waiting for callback: %s", 
                        callback
                    )
                    all_completed = False
        
        return all_completed
    
    def clear(self) -> None:
        """Clear all subscriptions."""
        self._bus.clear()
        with self._lock:
            self._callbacks.clear()
            self._callbacks_by_type.clear()
    
    def shutdown(self) -> None:
        """Shutdown the event bus."""
        self._bus.shutdown()
    
    def _on_dispatch(self, callback: Callable, data: Any) -> None:
        """Asynchronous dispatch slot function.
        
        Executes callback in the Qt main thread.
        """
        try:
            callback(data)
        except Exception as e:
            logger.error("Qt event callback execution failed: %s", e)
    
    def _on_dispatch_sync(
        self,
        callback: Callable,
        data: Any,
        done_event: threading.Event
    ) -> None:
        """Synchronous dispatch slot function.
        
        Executes callback in the Qt main thread and sets the event upon completion.
        """
        try:
            callback(data)
        except Exception as e:
            logger.error("Qt event callback execution failed: %s", e)
        finally:
            done_event.set()

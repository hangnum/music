# -*- coding: utf-8 -*-
"""
Qt 事件总线适配器

将纯 Python EventBus 的回调派发到 Qt 主线程，实现 core 层与 Qt 的解耦。

设计原则：
- core 层的 EventBus 保持纯 Python，不依赖 Qt
- Qt 主线程派发逻辑完全在 UI 层实现
- 通过适配器模式桥接两者
- publish_sync 必须等待所有 Qt 回调执行完成
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
    """Qt 事件总线适配器
    
    将回调派发到 Qt 主线程，确保 UI 更新在主线程执行。
    
    工作原理：
    1. subscribe 时，将原始回调注册到本地注册表，并向内部 bus 注册包装器
    2. publish 时，内部 bus 调用包装器，包装器发射 Qt 信号异步派发到主线程
    3. publish_sync 时，直接遍历本地注册表，使用同步信号等待每个回调完成
    
    使用示例:
        from core.event_bus import EventBus
        
        pure_bus = EventBus()
        qt_bus = QtEventBusAdapter(pure_bus)
        
        # 现在可以在任意线程发布事件，回调会在主线程执行
        qt_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
    """
    
    # 异步派发信号
    _dispatch_signal = pyqtSignal(object, object)
    # 同步派发信号（带完成事件）
    _dispatch_sync_signal = pyqtSignal(object, object, object)
    
    def __init__(self, inner_bus: "EventBus"):
        """初始化适配器
        
        Args:
            inner_bus: 底层的纯 Python EventBus
            
        Raises:
            RuntimeError: 如果没有 Qt 应用实例运行
        """
        super().__init__()
        
        # 确保在 Qt 主线程执行：移动到应用主线程
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            raise RuntimeError(
                "QtEventBusAdapter 需要一个正在运行的 QApplication 实例。"
                "请先创建 QApplication 后再初始化适配器。"
            )
        
        main_thread = app.thread()
        if QThread.currentThread() != main_thread:
            # 如果不在主线程创建，移动到主线程
            self.moveToThread(main_thread)
            logger.debug("QtEventBusAdapter 已移动到 Qt 主线程")
        
        self._bus = inner_bus
        self._lock = threading.Lock()
        
        # 本地回调注册表：{subscription_id: (event_type, original_callback)}
        # 用于 publish_sync 时直接派发到 Qt 主线程
        self._callbacks: Dict[str, tuple] = {}
        
        # 按事件类型索引：{event_type: {subscription_id: original_callback}}
        self._callbacks_by_type: Dict[Any, Dict[str, Callable]] = {}
        
        # 连接信号到槽，使用 QueuedConnection 确保在主线程执行
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
        """订阅事件
        
        回调将在 Qt 主线程执行。
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            
        Returns:
            订阅ID
        """
        def qt_wrapper(data: Any) -> None:
            """将回调包装为 Qt 信号发射（异步）"""
            self._dispatch_signal.emit(callback, data)
        
        # 向内部 bus 注册包装器
        subscription_id = self._bus.subscribe(event_type, qt_wrapper)
        
        # 在本地注册表中保存原始回调（用于 publish_sync）
        with self._lock:
            self._callbacks[subscription_id] = (event_type, callback)
            if event_type not in self._callbacks_by_type:
                self._callbacks_by_type[event_type] = {}
            self._callbacks_by_type[event_type][subscription_id] = callback
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否成功取消
        """
        result = self._bus.unsubscribe(subscription_id)
        
        # 从本地注册表中移除
        with self._lock:
            if subscription_id in self._callbacks:
                event_type, _ = self._callbacks.pop(subscription_id)
                if event_type in self._callbacks_by_type:
                    self._callbacks_by_type[event_type].pop(subscription_id, None)
        
        return result
    
    def publish(self, event_type: "Enum", data: Any = None) -> None:
        """发布事件（异步）
        
        回调将通过 Qt 信号异步派发到主线程执行。
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        self._bus.publish(event_type, data)
    
    def publish_sync(
        self,
        event_type: "Enum",
        data: Any = None,
        timeout: Optional[float] = 5.0
    ) -> bool:
        """同步发布事件
        
        等待所有回调在 Qt 主线程执行完成后返回。
        如果当前已在 Qt 主线程，则直接执行回调（避免死锁）。
        
        Args:
            event_type: 事件类型
            data: 事件数据
            timeout: 每个回调的超时时间（秒）
            
        Returns:
            是否所有回调都在超时前完成
        """
        # 获取需要调用的回调列表
        with self._lock:
            callbacks = list(self._callbacks_by_type.get(event_type, {}).values())
        
        if not callbacks:
            return True
        
        # 检查是否在 Qt 主线程
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
                # 已在主线程，直接执行
                try:
                    callback(data)
                except Exception as e:
                    logger.error("Qt 事件回调执行失败: %s", e)
            else:
                # 在工作线程，使用同步信号派发并等待
                done_event = threading.Event()
                self._dispatch_sync_signal.emit(callback, data, done_event)
                
                if timeout is None:
                    completed = done_event.wait()
                else:
                    completed = done_event.wait(timeout=timeout)
                
                if not completed:
                    logger.warning(
                        "QtEventBusAdapter.publish_sync 超时等待回调: %s", 
                        callback
                    )
                    all_completed = False
        
        return all_completed
    
    def clear(self) -> None:
        """清除所有订阅"""
        self._bus.clear()
        with self._lock:
            self._callbacks.clear()
            self._callbacks_by_type.clear()
    
    def shutdown(self) -> None:
        """关闭事件总线"""
        self._bus.shutdown()
    
    def _on_dispatch(self, callback: Callable, data: Any) -> None:
        """异步派发槽函数
        
        在 Qt 主线程中执行回调。
        """
        try:
            callback(data)
        except Exception as e:
            logger.error("Qt 事件回调执行失败: %s", e)
    
    def _on_dispatch_sync(
        self,
        callback: Callable,
        data: Any,
        done_event: threading.Event
    ) -> None:
        """同步派发槽函数
        
        在 Qt 主线程中执行回调，完成后设置事件。
        """
        try:
            callback(data)
        except Exception as e:
            logger.error("Qt 事件回调执行失败: %s", e)
        finally:
            done_event.set()

# -*- coding: utf-8 -*-
"""
应用容器模块

定义应用程序的依赖容器，集中持有所有服务实例。

设计原则：
- 仅 MainWindow 持有完整的 AppContainer
- 子组件通过 facade 访问服务，不直接访问 container
- 禁止将 AppContainer 传递给子组件
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols import IConfigService, IDatabase, IEventBus
    from services.music_app_facade import MusicAppFacade


@dataclass
class AppContainer:
    """应用程序依赖容器
    
    集中持有所有服务实例，作为依赖注入的组合根。
    
    使用规则：
    - 仅 MainWindow 持有此容器
    - 子组件通过 facade 属性访问服务
    - 不要将此容器传递给子组件
    
    使用示例:
        # 在 main.py 中
        container = AppContainerFactory.create()
        window = MainWindow(container)
        
        # 在 MainWindow 中传递 facade 给子组件
        self.library_widget = LibraryWidget(container.facade)
    """
    
    # === 公开属性（MainWindow 可访问）===
    config: "IConfigService"
    event_bus: "IEventBus"
    db: "IDatabase"
    facade: "MusicAppFacade"
    
    # === 内部服务引用（不暴露给子组件）===
    # 使用 field(repr=False) 避免在调试输出中泄露
    _player: Any = field(default=None, repr=False)
    _library: Any = field(default=None, repr=False)
    _playlist_service: Any = field(default=None, repr=False)
    _queue_persistence: Any = field(default=None, repr=False)
    _tag_service: Any = field(default=None, repr=False)
    
    def cleanup(self) -> None:
        """清理所有资源
        
        应在应用退出时调用。
        """
        # 清理播放器
        if self._player and hasattr(self._player, 'cleanup'):
            self._player.cleanup()
        
        # 关闭事件总线
        if self.event_bus and hasattr(self.event_bus, 'shutdown'):
            self.event_bus.shutdown()
        
        # 关闭数据库
        if self.db and hasattr(self.db, 'close'):
            self.db.close()
        
        # 关闭队列持久化服务
        if self._queue_persistence and hasattr(self._queue_persistence, 'shutdown'):
            self._queue_persistence.shutdown()

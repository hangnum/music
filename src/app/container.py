# -*- coding: utf-8 -*-
"""
Application Container Module

Defines the dependency container for the application, holding all service instances centrally.

Design Principles:
- Only MainWindow holds the complete AppContainer
- Sub-components access services via facade, not directly accessing the container
- Prohibited to pass AppContainer to sub-components
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols import IConfigService, IDatabase, IEventBus
    from services.music_app_facade import MusicAppFacade


@dataclass
class AppContainer:
    """Application Dependency Container
    
    Holds all service instances centrally, serving as the composition root for dependency injection.
    
    Usage Rules:
    - Only MainWindow holds this container
    - Sub-components access services via the facade property
    - Do not pass this container to sub-components
    
    Usage Example:
        # In main.py
        container = AppContainerFactory.create()
        window = MainWindow(container)
        
        # In MainWindow, pass facade to sub-components
        self.library_widget = LibraryWidget(container.facade)
    """
    
    # === Public Attributes (Accessible by MainWindow) ===
    config: "IConfigService"
    event_bus: "IEventBus"
    db: "IDatabase"
    facade: "MusicAppFacade"
    
    # === Internal Service References (Not exposed to sub-components) ===
    # Use field(repr=False) to avoid leaking in debug output
    _player: Any = field(default=None, repr=False)
    _library: Any = field(default=None, repr=False)
    _playlist_service: Any = field(default=None, repr=False)
    _favorites_service: Any = field(default=None, repr=False)
    _queue_persistence: Any = field(default=None, repr=False)
    _tag_service: Any = field(default=None, repr=False)
    _llm_tagging_service: Any = field(default=None, repr=False)
    _web_search_service: Any = field(default=None, repr=False)
    
    def cleanup(self) -> None:
        """Clean up all resources
        
        Should be called when the application exits.
        """
        # Clean up player
        if self._player and hasattr(self._player, 'cleanup'):
            self._player.cleanup()
        
        # Shutdown event bus
        if self.event_bus and hasattr(self.event_bus, 'shutdown'):
            self.event_bus.shutdown()
        
        # Close database
        if self.db and hasattr(self.db, 'close'):
            self.db.close()
        
        # Shutdown queue persistence service
        if self._queue_persistence and hasattr(self._queue_persistence, 'shutdown'):
            self._queue_persistence.shutdown()

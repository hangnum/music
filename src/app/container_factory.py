# -*- coding: utf-8 -*-
"""
Container Factory Module

Responsible for creating and assembling all application dependencies.

This is the **only** instance creation point (Composition Root) for the application.
All service instance creation should be done here, not within individual services.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)


class AppContainerFactory:
    """Application Container Factory
    
    Creates and assembles all application dependencies.
    
    Usage Example:
        # In main.py
        container = AppContainerFactory.create(use_qt_dispatcher=True)
        window = MainWindow(container)
        
        # In tests (no Qt)
        container = AppContainerFactory.create(use_qt_dispatcher=False)
    """
    
    @staticmethod
    def create(
        config_path: str = "config/default_config.yaml",
        use_qt_dispatcher: bool = True,
    ) -> "AppContainer":
        """Create Application Container
        
        Creates all service instances in dependency order and assembles them into the container.
        
        Args:
            config_path: Configuration file path
            use_qt_dispatcher: Whether to use Qt main thread dispatching
                              - True: Use QtEventBusAdapter during UI runtime
                              - False: Use pure EventBus for unit tests/non-UI
                              
        Returns:
            A configured AppContainer instance
        """
        from app.container import AppContainer
        from core.database import DatabaseManager
        from core.engine_factory import AudioEngineFactory
        from core.event_bus import EventBus
        from services.config_service import ConfigService
        from services.library_service import LibraryService
        from services.music_app_facade import MusicAppFacade
        from services.player_service import PlayerService
        from services.playlist_service import PlaylistService
        from services.favorites_service import FavoritesService
        from services.queue_persistence_service import QueuePersistenceService
        from services.tag_service import TagService
        
        logger.info("Creating application container...")
        
        # === 1. Infrastructure Layer ===
        config = ConfigService(config_path)
        db = DatabaseManager()
        
        # === 2. Event Bus (Select adapter based on environment) ===
        pure_bus = EventBus()
        if use_qt_dispatcher:
            try:
                from ui.qt_event_bus import QtEventBusAdapter
                event_bus = QtEventBusAdapter(pure_bus)
                logger.debug("Using QtEventBusAdapter")
            except ImportError:
                logger.warning("Failed to import QtEventBusAdapter, using pure EventBus")
                event_bus = pure_bus
        else:
            event_bus = pure_bus
            logger.debug("Using pure EventBus (Non-Qt mode)")
        
        # === 3. Audio Engine ===
        backend = config.get("audio.backend", "miniaudio")
        try:
            audio_engine = AudioEngineFactory.create(backend)
            logger.info("Created audio engine: %s", backend)
        except RuntimeError as e:
            logger.error("Failed to create audio engine: %s", e)
            raise
        
        # === 4. Service Layer ===
        player = PlayerService(audio_engine=audio_engine)
        library = LibraryService(db=db)
        playlist_service = PlaylistService(db=db)
        favorites_service = FavoritesService(db=db, playlist_service=playlist_service)
        tag_service = TagService(db=db)
        
        # Queue Persistence Service
        queue_persistence = QueuePersistenceService(
            db=db,
            config=config,
            event_bus=event_bus,
        )
        queue_persistence.attach(player)
        
        # === 5. LLM Related Services ===
        # Web Search Service (for enhanced LLM tagging)
        from services.web_search_service import WebSearchService
        web_search_service = WebSearchService(config=config)
        
        # LLM Tagging Service
        llm_tagging_service = None
        try:
            from services.llm_tagging_service import LLMTaggingService
            from services.llm_providers import create_llm_provider
            
            llm_client = create_llm_provider(config)
            llm_tagging_service = LLMTaggingService(
                config=config,
                db=db,
                tag_service=tag_service,
                library_service=library,
                client=llm_client,
                web_search=web_search_service,
            )
            logger.info("LLM Tagging Service created successfully")
        except Exception as e:
            logger.warning("LLM Tagging Service creation failed (possibly missing API Key): %s", e)
        
        # === 6. Create Facade ===
        facade = MusicAppFacade(
            player=player,
            library=library,
            playlist_service=playlist_service,
            config=config,
            event_bus=event_bus,
            tag_service=tag_service,
            favorites_service=favorites_service,
        )
        
        # === 7. Assemble Container ===
        container = AppContainer(
            config=config,
            event_bus=event_bus,
            db=db,
            facade=facade,
            _player=player,
            _library=library,
            _playlist_service=playlist_service,
            _favorites_service=favorites_service,
            _queue_persistence=queue_persistence,
            _tag_service=tag_service,
            _llm_tagging_service=llm_tagging_service,
            _web_search_service=web_search_service,
        )
        
        logger.info("Application container creation complete")
        return container
    
    @staticmethod
    def create_for_testing(
        config_path: str = "config/default_config.yaml",
        db_path: str = ":memory:",
    ) -> "AppContainer":
        """Create a container for testing
        
        Uses an in-memory database and pure EventBus, independent of Qt.
        
        Args:
            config_path: Configuration file path
            db_path: Database path (defaults to in-memory database)
            
        Returns:
            A configured test AppContainer instance
        """
        from app.container import AppContainer
        from core.database import DatabaseManager
        from core.event_bus import EventBus
        from services.config_service import ConfigService
        from services.library_service import LibraryService
        from services.music_app_facade import MusicAppFacade
        from services.player_service import PlayerService
        from services.playlist_service import PlaylistService
        from services.favorites_service import FavoritesService
        from services.queue_persistence_service import QueuePersistenceService
        from services.tag_service import TagService
        
        logger.info("Creating test application container...")
        
        config = ConfigService(config_path)
        db = DatabaseManager(db_path)
        event_bus = EventBus()
        
        # Do not create a real audio engine during tests, use None
        player = PlayerService(audio_engine=None)
        library = LibraryService(db=db)
        playlist_service = PlaylistService(db=db)
        favorites_service = FavoritesService(db=db, playlist_service=playlist_service)
        tag_service = TagService(db=db)
        
        queue_persistence = QueuePersistenceService(
            db=db,
            config=config,
            event_bus=event_bus,
        )
        
        facade = MusicAppFacade(
            player=player,
            library=library,
            playlist_service=playlist_service,
            config=config,
            event_bus=event_bus,
            tag_service=tag_service,
            favorites_service=favorites_service,
        )
        
        container = AppContainer(
            config=config,
            event_bus=event_bus,
            db=db,
            facade=facade,
            _player=player,
            _library=library,
            _playlist_service=playlist_service,
            _favorites_service=favorites_service,
            _queue_persistence=queue_persistence,
            _tag_service=tag_service,
        )
        
        logger.info("Test application container creation complete")
        return container

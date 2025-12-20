# -*- coding: utf-8 -*-
"""
容器工厂模块

负责创建和装配所有应用程序依赖。

这是应用程序的**唯一**实例创建点（Composition Root）。
所有服务实例的创建都应在此处完成，而非在各个服务内部。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.container import AppContainer

logger = logging.getLogger(__name__)


class AppContainerFactory:
    """应用容器工厂
    
    创建并装配所有应用程序依赖。
    
    使用示例:
        # 在 main.py 中
        container = AppContainerFactory.create(use_qt_dispatcher=True)
        window = MainWindow(container)
        
        # 在测试中（不使用 Qt）
        container = AppContainerFactory.create(use_qt_dispatcher=False)
    """
    
    @staticmethod
    def create(
        config_path: str = "config/default_config.yaml",
        use_qt_dispatcher: bool = True,
    ) -> "AppContainer":
        """创建应用容器
        
        按依赖顺序创建所有服务实例并装配到容器中。
        
        Args:
            config_path: 配置文件路径
            use_qt_dispatcher: 是否使用 Qt 主线程派发
                              - True: UI 运行时使用 QtEventBusAdapter
                              - False: 单元测试/非 UI 使用纯 EventBus
                              
        Returns:
            配置完成的 AppContainer 实例
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
        
        logger.info("正在创建应用容器...")
        
        # === 1. 基础设施层 ===
        config = ConfigService(config_path)
        db = DatabaseManager()
        
        # === 2. 事件总线（根据环境选择适配器）===
        pure_bus = EventBus()
        if use_qt_dispatcher:
            try:
                from ui.qt_event_bus import QtEventBusAdapter
                event_bus = QtEventBusAdapter(pure_bus)
                logger.debug("使用 QtEventBusAdapter")
            except ImportError:
                logger.warning("无法导入 QtEventBusAdapter，使用纯 EventBus")
                event_bus = pure_bus
        else:
            event_bus = pure_bus
            logger.debug("使用纯 EventBus（非 Qt 模式）")
        
        # === 3. 音频引擎 ===
        backend = config.get("audio.backend", "miniaudio")
        try:
            audio_engine = AudioEngineFactory.create(backend)
            logger.info("创建音频引擎: %s", backend)
        except RuntimeError as e:
            logger.error("创建音频引擎失败: %s", e)
            raise
        
        # === 4. 服务层 ===
        player = PlayerService(audio_engine=audio_engine)
        library = LibraryService(db=db)
        playlist_service = PlaylistService(db=db)
        favorites_service = FavoritesService(db=db, playlist_service=playlist_service)
        tag_service = TagService(db=db)
        
        # 队列持久化服务
        queue_persistence = QueuePersistenceService(
            db=db,
            config=config,
            event_bus=event_bus,
        )
        queue_persistence.attach(player)
        
        # === 5. LLM 相关服务 ===
        # 网络搜索服务（用于增强 LLM 标注）
        from services.web_search_service import WebSearchService
        web_search_service = WebSearchService(config=config)
        
        # LLM 标注服务
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
            logger.info("LLM 标注服务创建成功")
        except Exception as e:
            logger.warning("LLM 标注服务创建失败（可能缺少 API Key）: %s", e)
        
        # === 6. 创建 Facade ===
        facade = MusicAppFacade(
            player=player,
            library=library,
            playlist_service=playlist_service,
            config=config,
            event_bus=event_bus,
        )
        
        # === 7. 装配容器 ===
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
        
        logger.info("应用容器创建完成")
        return container
    
    @staticmethod
    def create_for_testing(
        config_path: str = "config/default_config.yaml",
        db_path: str = ":memory:",
    ) -> "AppContainer":
        """创建用于测试的容器
        
        使用内存数据库和纯 EventBus，不依赖 Qt。
        
        Args:
            config_path: 配置文件路径
            db_path: 数据库路径（默认使用内存数据库）
            
        Returns:
            配置完成的测试用 AppContainer 实例
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
        
        logger.info("正在创建测试用应用容器...")
        
        config = ConfigService(config_path)
        db = DatabaseManager(db_path)
        event_bus = EventBus()
        
        # 测试时不创建真实音频引擎，使用 None
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
        
        logger.info("测试用应用容器创建完成")
        return container

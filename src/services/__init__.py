"""
服务层模块
"""

from .player_service import PlayerService, PlayMode, PlaybackState
from .playlist_service import PlaylistService
from .library_service import LibraryService
from .config_service import ConfigService
from .llm_queue_service import LLMQueueService, QueueReorderPlan, LLMQueueError
from .queue_persistence_service import QueuePersistenceService
from .llm_queue_cache_service import LLMQueueCacheService, LLMQueueHistoryEntry
from .tag_service import TagService
from .daily_playlist_service import DailyPlaylistService, DailyPlaylistResult

# LLM 提供商模块
from .llm_providers import (
    SiliconFlowProvider,
    SiliconFlowSettings,
    GeminiProvider,
    GeminiSettings,
    create_llm_provider,
    AVAILABLE_PROVIDERS,
)

# 向后兼容别名
SiliconFlowClient = SiliconFlowProvider

__all__ = [
    'PlayerService',
    'PlayMode',
    'PlaybackState',
    'PlaylistService',
    'LibraryService',
    'ConfigService',
    'LLMQueueService',
    'QueueReorderPlan',
    'LLMQueueError',
    'QueuePersistenceService',
    'LLMQueueCacheService',
    'LLMQueueHistoryEntry',
    'TagService',
    'DailyPlaylistService',
    'DailyPlaylistResult',
    # LLM 提供商
    'SiliconFlowProvider',
    'SiliconFlowSettings',
    'SiliconFlowClient',  # 向后兼容
    'GeminiProvider',
    'GeminiSettings',
    'create_llm_provider',
    'AVAILABLE_PROVIDERS',
]

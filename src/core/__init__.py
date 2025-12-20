"""
音乐播放器核心模块
"""

from .event_bus import EventBus, EventType
from .audio_engine import AudioEngineBase, PygameAudioEngine, PlayerState
from .metadata import MetadataParser, AudioMetadata
from .database import DatabaseManager
from .llm_provider import LLMProvider, LLMSettings, LLMProviderError
from .engine_factory import AudioEngineFactory
from .ffmpeg_transcoder import FFmpegTranscoder, MINIAUDIO_NATIVE_FORMATS

# 尝试导入 miniaudio 相关异常（可能不可用）
try:
    from .miniaudio_engine import UnsupportedFormatError
except ImportError:
    UnsupportedFormatError = None  # type: ignore

__all__ = [
    'EventBus',
    'EventType',
    'AudioEngineBase',
    'PygameAudioEngine',
    'PlayerState',
    'MetadataParser',
    'AudioMetadata',
    'DatabaseManager',
    'LLMProvider',
    'LLMSettings',
    'LLMProviderError',
    'AudioEngineFactory',
    'FFmpegTranscoder',
    'MINIAUDIO_NATIVE_FORMATS',
    'UnsupportedFormatError',
]


"""
UI 对话框
"""

from .llm_settings_dialog import LLMSettingsDialog
from .llm_queue_chat_dialog import LLMQueueChatDialog
from .tag_dialog import TagDialog
from .audio_settings_dialog import AudioSettingsDialog
from .daily_playlist_dialog import DailyPlaylistDialog

__all__ = [
    "LLMSettingsDialog", 
    "LLMQueueChatDialog", 
    "TagDialog",
    "AudioSettingsDialog",
    "DailyPlaylistDialog",
]




"""
LLM 队列管理相关数据模型
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


class LLMQueueError(RuntimeError):
    """LLM 队列操作错误"""
    pass


@dataclass(frozen=True)
class LibraryQueueRequest:
    """从音乐库请求曲目的参数"""
    mode: str = "replace"  # replace|append
    query: str = ""
    genre: str = ""
    artist: str = ""
    album: str = ""
    limit: int = 30
    shuffle: bool = True
    semantic_fallback: bool = True


@dataclass(frozen=True)
class QueueReorderPlan:
    """队列重排计划"""
    ordered_track_ids: List[str]
    reason: str = ""
    clear_queue: bool = False
    library_request: Optional[LibraryQueueRequest] = None
    instruction: str = ""

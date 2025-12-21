"""
Data models related to LLM queue management
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


class LLMQueueError(RuntimeError):
    """LLM queue operation error"""
    pass


@dataclass(frozen=True)
class LibraryQueueRequest:
    """Parameters for requesting tracks from the library"""
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
    """Queue reorder plan"""
    ordered_track_ids: List[str]
    reason: str = ""
    clear_queue: bool = False
    library_request: Optional[LibraryQueueRequest] = None
    instruction: str = ""

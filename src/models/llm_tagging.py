"""
Data models related to LLM tagging
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class LLMTaggingError(RuntimeError):
    """LLM tagging error"""
    pass


@dataclass
class TaggingJobStatus:
    """Tagging job status"""
    job_id: str
    status: str  # pending | running | completed | failed | stopped
    total_tracks: int
    processed_tracks: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    @property
    def progress(self) -> float:
        """Progress percentage (0.0 - 1.0)"""
        if self.total_tracks == 0:
            return 0.0
        return self.processed_tracks / self.total_tracks

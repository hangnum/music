"""
LLM 标签标注相关数据模型
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class LLMTaggingError(RuntimeError):
    """LLM 标注错误"""
    pass


@dataclass
class TaggingJobStatus:
    """标注任务状态"""
    job_id: str
    status: str  # pending | running | completed | failed | stopped
    total_tracks: int
    processed_tracks: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    @property
    def progress(self) -> float:
        """进度百分比 (0.0 - 1.0)"""
        if self.total_tracks == 0:
            return 0.0
        return self.processed_tracks / self.total_tracks

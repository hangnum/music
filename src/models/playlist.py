"""
播放列表数据模型
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid


@dataclass
class Playlist:
    """
    播放列表数据模型
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    cover_path: Optional[str] = None
    track_ids: List[str] = field(default_factory=list)
    track_count: int = 0
    total_duration_ms: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_str(self) -> str:
        """格式化总时长"""
        total_seconds = self.total_duration_ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        return f"{minutes}分钟"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cover_path': self.cover_path,
            'track_ids': self.track_ids,
            'track_count': self.track_count,
            'total_duration_ms': self.total_duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Playlist':
        """从字典创建Playlist对象"""
        created_at = datetime.now()
        updated_at = datetime.now()
        
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                pass
        
        if data.get('updated_at'):
            try:
                updated_at = datetime.fromisoformat(data['updated_at'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            cover_path=data.get('cover_path'),
            track_ids=data.get('track_ids', []),
            track_count=data.get('track_count', 0),
            total_duration_ms=data.get('total_duration_ms', 0),
            created_at=created_at,
            updated_at=updated_at,
        )

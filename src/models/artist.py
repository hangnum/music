"""
艺术家数据模型
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class Artist:
    """
    艺术家数据模型
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    image_path: Optional[str] = None
    album_count: int = 0
    track_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'image_path': self.image_path,
            'album_count': self.album_count,
            'track_count': self.track_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Artist':
        """从字典创建Artist对象"""
        created_at = datetime.now()
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            image_path=data.get('image_path'),
            album_count=data.get('album_count', 0),
            track_count=data.get('track_count', 0),
            created_at=created_at,
        )

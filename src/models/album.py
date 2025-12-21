"""
Album data model
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import uuid


@dataclass
class Album:
    """
    Album data model
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    artist_id: Optional[str] = None
    artist_name: str = ""
    year: Optional[int] = None
    cover_path: Optional[str] = None
    track_count: int = 0
    total_duration_ms: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_str(self) -> str:
        """Formatted total duration"""
        total_seconds = self.total_duration_ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'artist_id': self.artist_id,
            'artist_name': self.artist_name,
            'year': self.year,
            'cover_path': self.cover_path,
            'track_count': self.track_count,
            'total_duration_ms': self.total_duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Album':
        """Create Album object from dictionary"""
        created_at = datetime.now()
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            artist_id=data.get('artist_id'),
            artist_name=data.get('artist_name', ''),
            year=data.get('year'),
            cover_path=data.get('cover_path'),
            track_count=data.get('track_count', 0),
            total_duration_ms=data.get('total_duration_ms', 0),
            created_at=created_at,
        )

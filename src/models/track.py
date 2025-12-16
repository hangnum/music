"""
音轨数据模型
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class Track:
    """
    音轨数据模型
    
    代表一首音乐的完整信息。
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    file_path: str = ""
    duration_ms: int = 0
    bitrate: int = 0
    sample_rate: int = 0
    format: str = ""
    
    # 关联信息
    artist_id: Optional[str] = None
    artist_name: str = ""
    album_id: Optional[str] = None
    album_name: str = ""
    
    # 曲目信息
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    genre: str = ""
    year: Optional[int] = None
    
    # 用户数据
    play_count: int = 0
    last_played: Optional[datetime] = None
    rating: int = 0  # 0-5
    
    # 封面路径
    cover_path: Optional[str] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_str(self) -> str:
        """格式化时长字符串 (mm:ss)"""
        total_seconds = self.duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    @property
    def duration_long_str(self) -> str:
        """格式化时长字符串 (hh:mm:ss)"""
        total_seconds = self.duration_ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.artist_name:
            return f"{self.artist_name} - {self.title}"
        return self.title
    
    @property
    def bitrate_str(self) -> str:
        """格式化比特率"""
        if self.bitrate > 0:
            return f"{self.bitrate} kbps"
        return ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'file_path': self.file_path,
            'duration_ms': self.duration_ms,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'format': self.format,
            'artist_id': self.artist_id,
            'artist_name': self.artist_name,
            'album_id': self.album_id,
            'album_name': self.album_name,
            'track_number': self.track_number,
            'disc_number': self.disc_number,
            'genre': self.genre,
            'year': self.year,
            'play_count': self.play_count,
            'last_played': self.last_played.isoformat() if self.last_played else None,
            'rating': self.rating,
            'cover_path': self.cover_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Track':
        """从字典创建Track对象"""
        last_played = None
        if data.get('last_played'):
            try:
                last_played = datetime.fromisoformat(data['last_played'])
            except (ValueError, TypeError):
                pass
        
        created_at = datetime.now()
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            file_path=data.get('file_path', ''),
            duration_ms=data.get('duration_ms', 0),
            bitrate=data.get('bitrate', 0),
            sample_rate=data.get('sample_rate', 0),
            format=data.get('format', ''),
            artist_id=data.get('artist_id'),
            artist_name=data.get('artist_name', ''),
            album_id=data.get('album_id'),
            album_name=data.get('album_name', ''),
            track_number=data.get('track_number'),
            disc_number=data.get('disc_number'),
            genre=data.get('genre', ''),
            year=data.get('year'),
            play_count=data.get('play_count', 0),
            last_played=last_played,
            rating=data.get('rating', 0),
            cover_path=data.get('cover_path'),
            created_at=created_at,
        )
    
    @classmethod
    def from_metadata(cls, metadata) -> 'Track':
        """从AudioMetadata创建Track对象"""
        return cls(
            title=metadata.title,
            file_path=metadata.file_path,
            duration_ms=metadata.duration_ms,
            bitrate=metadata.bitrate,
            sample_rate=metadata.sample_rate,
            format=metadata.format,
            artist_name=metadata.artist,
            album_name=metadata.album,
            track_number=metadata.track_number,
            genre=metadata.genre,
            year=metadata.year,
        )

"""
Tag data model

User-defined tags for music tracks.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class Tag:
    """
    Tag data model
    
    Represents a tag, can be used for categorizing and filtering music.
    
    Attributes:
        id: Unique identifier
        name: Tag name (case-insensitive unique)
        color: Tag color (hex format, e.g., #FF5733)
        source: Tag source ("user" for manually created, "llm" for LLM auto-tagged)
        created_at: Creation time
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    color: str = "#808080"
    source: str = "user"  # "user" | "llm"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tag':
        """Create Tag object from dictionary"""
        created_at = datetime.now()
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            color=data.get('color', '#808080'),
            source=data.get('source', 'user'),
            created_at=created_at,
        )
    
    def __eq__(self, other: object) -> bool:
        """Compare if two tags are equal (based on ID)"""
        if not isinstance(other, Tag):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash function (based on ID)"""
        return hash(self.id)


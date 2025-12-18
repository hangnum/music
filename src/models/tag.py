"""
标签数据模型

用于音乐曲目的用户自定义标签。
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class Tag:
    """
    标签数据模型
    
    代表一个标签，可用于分类和筛选音乐。
    
    Attributes:
        id: 唯一标识符
        name: 标签名称（不区分大小写唯一）
        color: 标签颜色（十六进制格式，如 #FF5733）
        source: 标签来源 ("user" 表示用户手动创建, "llm" 表示 LLM 自动标注)
        created_at: 创建时间
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    color: str = "#808080"
    source: str = "user"  # "user" | "llm"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tag':
        """从字典创建Tag对象"""
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
        """比较两个标签是否相等（基于ID）"""
        if not isinstance(other, Tag):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """哈希函数（基于ID）"""
        return hash(self.id)


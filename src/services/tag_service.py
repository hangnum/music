"""
标签服务模块

提供标签的创建、管理、以及曲目与标签的关联操作。
"""

from typing import List, Optional
from datetime import datetime
import uuid

from core.database import DatabaseManager
from models.tag import Tag


class TagService:
    """
    标签服务
    
    提供标签的 CRUD 操作以及曲目-标签关联管理。
    
    使用示例:
        tag_service = TagService(db)
        
        # 创建标签
        tag = tag_service.create_tag("喜欢", "#FF5733")
        
        # 为曲目添加标签
        tag_service.add_tag_to_track(track_id, tag.id)
        
        # 获取曲目的所有标签
        tags = tag_service.get_track_tags(track_id)
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化标签服务
        
        Args:
            db: 数据库管理器实例，如果为 None 则使用默认实例
        """
        self._db = db or DatabaseManager()
    
    # ========== 标签 CRUD ==========
    
    def create_tag(self, name: str, color: str = "#808080") -> Optional[Tag]:
        """
        创建新标签
        
        Args:
            name: 标签名称
            color: 标签颜色（十六进制格式）
            
        Returns:
            创建的标签对象，如果标签名已存在则返回 None
        """
        # 检查是否存在同名标签（不区分大小写）
        existing = self.get_tag_by_name(name)
        if existing:
            return None
        
        tag = Tag(
            id=str(uuid.uuid4()),
            name=name.strip(),
            color=color,
            created_at=datetime.now()
        )
        
        self._db.insert("tags", {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "created_at": tag.created_at.isoformat()
        })
        
        return tag
    
    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """
        根据 ID 获取标签
        
        Args:
            tag_id: 标签 ID
            
        Returns:
            标签对象，如果不存在则返回 None
        """
        row = self._db.fetch_one(
            "SELECT * FROM tags WHERE id = ?",
            (tag_id,)
        )
        
        if not row:
            return None
        
        return Tag.from_dict(dict(row))
    
    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """
        根据名称获取标签（不区分大小写）
        
        Args:
            name: 标签名称
            
        Returns:
            标签对象，如果不存在则返回 None
        """
        row = self._db.fetch_one(
            "SELECT * FROM tags WHERE name = ? COLLATE NOCASE",
            (name.strip(),)
        )
        
        if not row:
            return None
        
        return Tag.from_dict(dict(row))
    
    def get_all_tags(self) -> List[Tag]:
        """
        获取所有标签
        
        Returns:
            标签列表，按名称排序
        """
        rows = self._db.fetch_all(
            "SELECT * FROM tags ORDER BY name COLLATE NOCASE"
        )
        
        return [Tag.from_dict(dict(row)) for row in rows]
    
    def update_tag(self, tag_id: str, name: Optional[str] = None, 
                   color: Optional[str] = None) -> bool:
        """
        更新标签
        
        Args:
            tag_id: 标签 ID
            name: 新名称（可选）
            color: 新颜色（可选）
            
        Returns:
            是否更新成功
        """
        data = {}
        if name is not None:
            # 检查新名称是否与其他标签冲突
            existing = self.get_tag_by_name(name)
            if existing and existing.id != tag_id:
                return False
            data["name"] = name.strip()
        
        if color is not None:
            data["color"] = color
        
        if not data:
            return False
        
        affected = self._db.update("tags", data, "id = ?", (tag_id,))
        return affected > 0
    
    def delete_tag(self, tag_id: str) -> bool:
        """
        删除标签
        
        会同时删除所有曲目与该标签的关联。
        
        Args:
            tag_id: 标签 ID
            
        Returns:
            是否删除成功
        """
        affected = self._db.delete("tags", "id = ?", (tag_id,))
        return affected > 0
    
    # ========== 曲目-标签关联 ==========
    
    def add_tag_to_track(self, track_id: str, tag_id: str) -> bool:
        """
        为曲目添加标签
        
        Args:
            track_id: 曲目 ID
            tag_id: 标签 ID
            
        Returns:
            是否添加成功
        """
        try:
            self._db.insert("track_tags", {
                "track_id": track_id,
                "tag_id": tag_id,
                "created_at": datetime.now().isoformat()
            })
            return True
        except Exception:
            # 可能是重复添加或外键约束失败
            return False
    
    def remove_tag_from_track(self, track_id: str, tag_id: str) -> bool:
        """
        从曲目移除标签
        
        Args:
            track_id: 曲目 ID
            tag_id: 标签 ID
            
        Returns:
            是否移除成功
        """
        affected = self._db.delete(
            "track_tags",
            "track_id = ? AND tag_id = ?",
            (track_id, tag_id)
        )
        return affected > 0
    
    def get_track_tags(self, track_id: str) -> List[Tag]:
        """
        获取曲目的所有标签
        
        Args:
            track_id: 曲目 ID
            
        Returns:
            标签列表
        """
        rows = self._db.fetch_all(
            """
            SELECT t.* FROM tags t
            INNER JOIN track_tags tt ON t.id = tt.tag_id
            WHERE tt.track_id = ?
            ORDER BY t.name COLLATE NOCASE
            """,
            (track_id,)
        )
        
        return [Tag.from_dict(dict(row)) for row in rows]
    
    def get_track_tag_names(self, track_id: str) -> List[str]:
        """
        获取曲目的所有标签名称（便于显示）
        
        Args:
            track_id: 曲目 ID
            
        Returns:
            标签名称列表
        """
        rows = self._db.fetch_all(
            """
            SELECT t.name FROM tags t
            INNER JOIN track_tags tt ON t.id = tt.tag_id
            WHERE tt.track_id = ?
            ORDER BY t.name COLLATE NOCASE
            """,
            (track_id,)
        )
        
        return [row['name'] for row in rows]
    
    def get_tracks_by_tag(self, tag_id: str) -> List[str]:
        """
        获取标签下的所有曲目 ID
        
        Args:
            tag_id: 标签 ID
            
        Returns:
            曲目 ID 列表
        """
        rows = self._db.fetch_all(
            "SELECT track_id FROM track_tags WHERE tag_id = ?",
            (tag_id,)
        )
        
        return [row['track_id'] for row in rows]
    
    def set_track_tags(self, track_id: str, tag_ids: List[str]) -> bool:
        """
        设置曲目的标签（替换所有现有标签）
        
        Args:
            track_id: 曲目 ID
            tag_ids: 新的标签 ID 列表
            
        Returns:
            是否设置成功
        """
        try:
            # 先删除现有关联
            self._db.delete("track_tags", "track_id = ?", (track_id,))
            
            # 添加新关联
            for tag_id in tag_ids:
                self._db.insert("track_tags", {
                    "track_id": track_id,
                    "tag_id": tag_id,
                    "created_at": datetime.now().isoformat()
                })
            
            return True
        except Exception:
            return False
    
    # ========== 搜索 ==========
    
    def search_tags(self, query: str, limit: int = 20) -> List[Tag]:
        """
        搜索标签
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            匹配的标签列表
        """
        rows = self._db.fetch_all(
            """
            SELECT * FROM tags
            WHERE name LIKE ? COLLATE NOCASE
            ORDER BY name COLLATE NOCASE
            LIMIT ?
            """,
            (f"%{query}%", limit)
        )
        
        return [Tag.from_dict(dict(row)) for row in rows]
    
    def get_tag_count(self) -> int:
        """
        获取标签总数
        
        Returns:
            标签数量
        """
        result = self._db.fetch_one("SELECT COUNT(*) as count FROM tags")
        return result['count'] if result else 0
    
    def get_track_count_by_tag(self, tag_id: str) -> int:
        """
        获取标签下的曲目数量
        
        Args:
            tag_id: 标签 ID
            
        Returns:
            曲目数量
        """
        result = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM track_tags WHERE tag_id = ?",
            (tag_id,)
        )
        return result['count'] if result else 0

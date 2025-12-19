"""
标签服务模块

提供标签的创建、管理、以及曲目与标签的关联操作。
"""

from typing import List, Optional
from datetime import datetime
import uuid
import logging

from core.database import DatabaseManager
from models.tag import Tag

logger = logging.getLogger(__name__)


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
    
    def create_tag(self, name: str, color: str = "#808080", 
                   source: str = "user") -> Optional[Tag]:
        """
        创建新标签
        
        Args:
            name: 标签名称
            color: 标签颜色（十六进制格式）
            source: 标签来源 ("user" 表示用户创建, "llm" 表示 LLM 标注)
            
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
            source=source,
            created_at=datetime.now()
        )
        
        self._db.insert("tags", {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "source": tag.source,
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
            logger.warning("添加标签失败: track_id=%s, tag_id=%s", track_id, tag_id, exc_info=True)
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
        
        使用事务确保原子性：如果中途失败，会回滚所有更改。
        
        Args:
            track_id: 曲目 ID
            tag_ids: 新的标签 ID 列表
            
        Returns:
            是否设置成功
        """
        try:
            with self._db.transaction():
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
            logger.warning("设置曲目标签失败: track_id=%s, tag_ids=%s", track_id, tag_ids, exc_info=True)
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
    
    # ========== LLM 批量标注支持 ==========
    
    def create_tag_if_not_exists(self, name: str, color: str = "#808080",
                                  source: str = "user") -> Tag:
        """
        创建标签（如已存在则返回现有标签）
        
        Args:
            name: 标签名称
            color: 标签颜色
            source: 标签来源
            
        Returns:
            标签对象（新创建或已存在的）
        """
        existing = self.get_tag_by_name(name)
        if existing:
            return existing
        
        tag = self.create_tag(name, color, source)
        if tag is None:
            # 并发情况下可能刚被创建，再次获取
            return self.get_tag_by_name(name)  # type: ignore
        return tag
    
    def batch_add_tags_to_track(self, track_id: str, tag_names: List[str],
                                 source: str = "llm") -> int:
        """
        批量为曲目添加标签（自动创建不存在的标签）
        
        Args:
            track_id: 曲目 ID
            tag_names: 标签名称列表
            source: 标签来源
            
        Returns:
            成功添加的标签数量
        """
        added = 0
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            
            tag = self.create_tag_if_not_exists(name, source=source)
            if self.add_tag_to_track(track_id, tag.id):
                added += 1
        
        return added
    
    def get_tracks_by_tags(self, tag_names: List[str], 
                           match_mode: str = "any",
                           limit: int = 200) -> List[str]:
        """
        按标签名称搜索曲目 ID
        
        Args:
            tag_names: 标签名称列表
            match_mode: 匹配模式
                - "any": 匹配任一标签（OR）
                - "all": 匹配所有标签（AND）
            limit: 结果数量限制
            
        Returns:
            曲目 ID 列表
        """
        if not tag_names:
            return []
        
        tag_names = [n.strip() for n in tag_names if n.strip()]
        if not tag_names:
            return []
        
        if match_mode == "all":
            # 必须匹配所有标签
            placeholders = ",".join(["?" for _ in tag_names])
            query = f"""
                SELECT tt.track_id
                FROM track_tags tt
                INNER JOIN tags t ON tt.tag_id = t.id
                WHERE t.name IN ({placeholders}) COLLATE NOCASE
                GROUP BY tt.track_id
                HAVING COUNT(DISTINCT t.id) = ?
                LIMIT ?
            """
            params = tuple(tag_names) + (len(tag_names), limit)
        else:
            # 匹配任一标签
            placeholders = ",".join(["?" for _ in tag_names])
            query = f"""
                SELECT DISTINCT tt.track_id
                FROM track_tags tt
                INNER JOIN tags t ON tt.tag_id = t.id
                WHERE t.name IN ({placeholders}) COLLATE NOCASE
                LIMIT ?
            """
            params = tuple(tag_names) + (limit,)
        
        rows = self._db.fetch_all(query, params)
        return [row['track_id'] for row in rows]
    
    def get_untagged_tracks(self, source: str = "llm", 
                            limit: int = 500) -> List[str]:
        """
        获取未被指定来源标注的曲目 ID
        
        Args:
            source: 标签来源（"llm" = 获取未被 LLM 标注的曲目）
            limit: 结果数量限制
            
        Returns:
            曲目 ID 列表
        """
        if source == "llm":
            # 查找不在 llm_tagged_tracks 表中的曲目
            query = """
                SELECT t.id
                FROM tracks t
                LEFT JOIN llm_tagged_tracks ltt ON t.id = ltt.track_id
                WHERE ltt.track_id IS NULL
                LIMIT ?
            """
        else:
            # 查找没有指定来源标签的曲目
            query = """
                SELECT t.id
                FROM tracks t
                WHERE t.id NOT IN (
                    SELECT DISTINCT tt.track_id
                    FROM track_tags tt
                    INNER JOIN tags tg ON tt.tag_id = tg.id
                    WHERE tg.source = ?
                )
                LIMIT ?
            """
            rows = self._db.fetch_all(query, (source, limit))
            return [row['id'] for row in rows]
        
        rows = self._db.fetch_all(query, (limit,))
        return [row['id'] for row in rows]
    
    def get_all_tag_names(self, source: Optional[str] = None) -> List[str]:
        """
        获取所有标签名称
        
        Args:
            source: 筛选特定来源的标签（None = 所有来源）
            
        Returns:
            标签名称列表
        """
        if source:
            rows = self._db.fetch_all(
                "SELECT name FROM tags WHERE source = ? ORDER BY name COLLATE NOCASE",
                (source,)
            )
        else:
            rows = self._db.fetch_all(
                "SELECT name FROM tags ORDER BY name COLLATE NOCASE"
            )
        
        return [row['name'] for row in rows]
    
    def mark_track_as_tagged(self, track_id: str, job_id: Optional[str] = None) -> bool:
        """
        标记曲目已被 LLM 标注
        
        Args:
            track_id: 曲目 ID
            job_id: 标注任务 ID（可选）
            
        Returns:
            是否标记成功
        """
        try:
            self._db.insert("llm_tagged_tracks", {
                "track_id": track_id,
                "job_id": job_id,
                "tagged_at": datetime.now().isoformat()
            })
            return True
        except Exception:
            logger.warning("标记曲目LLM标注状态失败: track_id=%s, job_id=%s", track_id, job_id, exc_info=True)
            return False


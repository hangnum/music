"""
播放列表服务模块

管理播放列表的CRUD操作。
"""

from typing import List, Optional
from datetime import datetime
import uuid
import logging

from core.database import DatabaseManager
from core.event_bus import EventBus, EventType
from models.playlist import Playlist
from models.track import Track

logger = logging.getLogger(__name__)


class PlaylistService:
    """
    播放列表服务
    
    提供播放列表的创建、读取、更新、删除功能。
    
    使用示例:
        service = PlaylistService()
        
        # 创建播放列表
        playlist = service.create("我的收藏", "喜欢的歌曲")
        
        # 添加曲目
        service.add_track(playlist.id, track)
        
        # 获取所有播放列表
        all_playlists = service.get_all()
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        self._db = db or DatabaseManager()
        self._event_bus = EventBus()
    
    def create(self, name: str, description: str = "") -> Playlist:
        """
        创建播放列表
        
        Args:
            name: 播放列表名称
            description: 描述
            
        Returns:
            Playlist: 创建的播放列表
        """
        playlist_id = str(uuid.uuid4())
        now = datetime.now()
        
        self._db.insert("playlists", {
            "id": playlist_id,
            "name": name,
            "description": description,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        })
        
        playlist = Playlist(
            id=playlist_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        
        self._event_bus.publish(EventType.PLAYLIST_CREATED, playlist)
        return playlist
    
    def get(self, playlist_id: str) -> Optional[Playlist]:
        """
        获取播放列表
        
        Args:
            playlist_id: 播放列表ID
            
        Returns:
            Playlist: 播放列表对象，不存在返回None
        """
        row = self._db.fetch_one(
            "SELECT * FROM playlists WHERE id = ?",
            (playlist_id,)
        )
        
        if not row:
            return None
        
        # 获取曲目ID列表
        tracks_rows = self._db.fetch_all(
            """SELECT track_id FROM playlist_tracks 
               WHERE playlist_id = ? ORDER BY position""",
            (playlist_id,)
        )
        track_ids = [r["track_id"] for r in tracks_rows]
        
        # 计算统计信息
        stats = self._db.fetch_one(
            """SELECT COUNT(*) as count, COALESCE(SUM(t.duration_ms), 0) as duration
               FROM playlist_tracks pt
               JOIN tracks t ON pt.track_id = t.id
               WHERE pt.playlist_id = ?""",
            (playlist_id,)
        )
        
        return Playlist(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            cover_path=row.get("cover_path"),
            track_ids=track_ids,
            track_count=stats["count"] if stats else 0,
            total_duration_ms=stats["duration"] if stats else 0,
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
        )
    
    def get_all(self) -> List[Playlist]:
        """
        获取所有播放列表
        
        Returns:
            List[Playlist]: 播放列表列表
        """
        rows = self._db.fetch_all(
            "SELECT id FROM playlists ORDER BY created_at DESC"
        )
        
        return [self.get(row["id"]) for row in rows if self.get(row["id"])]
    
    def update(self, playlist_id: str, name: str = None, 
               description: str = None) -> bool:
        """
        更新播放列表
        
        Args:
            playlist_id: 播放列表ID
            name: 新名称
            description: 新描述
            
        Returns:
            bool: 是否更新成功
        """
        updates = {"updated_at": datetime.now().isoformat()}
        
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        
        rows_affected = self._db.update(
            "playlists",
            updates,
            "id = ?",
            (playlist_id,)
        )
        
        if rows_affected > 0:
            playlist = self.get(playlist_id)
            if playlist:
                self._event_bus.publish(EventType.PLAYLIST_UPDATED, playlist)
            return True
        return False
    
    def delete(self, playlist_id: str) -> bool:
        """
        删除播放列表
        
        Args:
            playlist_id: 播放列表ID
            
        Returns:
            bool: 是否删除成功
        """
        rows_affected = self._db.delete("playlists", "id = ?", (playlist_id,))
        
        if rows_affected > 0:
            self._event_bus.publish(EventType.PLAYLIST_DELETED, playlist_id)
            return True
        return False
    
    def add_track(self, playlist_id: str, track: Track) -> bool:
        """
        添加曲目到播放列表
        
        Args:
            playlist_id: 播放列表ID
            track: 曲目对象
            
        Returns:
            bool: 是否添加成功
        """
        # 获取当前最大position
        result = self._db.fetch_one(
            "SELECT MAX(position) as max_pos FROM playlist_tracks WHERE playlist_id = ?",
            (playlist_id,)
        )
        next_pos = (result["max_pos"] or 0) + 1 if result else 1
        
        try:
            self._db.insert("playlist_tracks", {
                "playlist_id": playlist_id,
                "track_id": track.id,
                "position": next_pos,
                "added_at": datetime.now().isoformat(),
            })
            
            # 更新播放列表的更新时间
            self._db.update(
                "playlists",
                {"updated_at": datetime.now().isoformat()},
                "id = ?",
                (playlist_id,)
            )
            
            self._event_bus.publish(EventType.PLAYLIST_UPDATED, self.get(playlist_id))
            return True
        except Exception as e:
            logger.warning("添加曲目到播放列表失败: playlist_id=%s, track_id=%s, error=%s", playlist_id, track.id, e)
            return False
    
    def remove_track(self, playlist_id: str, track_id: str) -> bool:
        """
        从播放列表移除曲目
        
        Args:
            playlist_id: 播放列表ID
            track_id: 曲目ID
            
        Returns:
            bool: 是否移除成功
        """
        rows_affected = self._db.delete(
            "playlist_tracks",
            "playlist_id = ? AND track_id = ?",
            (playlist_id, track_id)
        )
        
        if rows_affected > 0:
            # 更新播放列表的更新时间
            self._db.update(
                "playlists",
                {"updated_at": datetime.now().isoformat()},
                "id = ?",
                (playlist_id,)
            )
            
            self._event_bus.publish(EventType.PLAYLIST_UPDATED, self.get(playlist_id))
            return True
        return False
    
    def reorder_track(self, playlist_id: str, track_id: str, 
                      new_position: int) -> bool:
        """
        调整曲目顺序
        
        Args:
            playlist_id: 播放列表ID
            track_id: 曲目ID
            new_position: 新位置
            
        Returns:
            bool: 是否成功
        """
        # 获取当前位置
        current = self._db.fetch_one(
            "SELECT position FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
            (playlist_id, track_id)
        )
        
        if not current:
            return False
        
        old_position = current["position"]
        
        if old_position == new_position:
            return True
        
        with self._db.transaction():
            if old_position < new_position:
                # 向后移动：中间的位置-1
                self._db.execute(
                    """UPDATE playlist_tracks SET position = position - 1
                       WHERE playlist_id = ? AND position > ? AND position <= ?""",
                    (playlist_id, old_position, new_position)
                )
            else:
                # 向前移动：中间的位置+1
                self._db.execute(
                    """UPDATE playlist_tracks SET position = position + 1
                       WHERE playlist_id = ? AND position >= ? AND position < ?""",
                    (playlist_id, new_position, old_position)
                )
            
            # 更新目标曲目位置
            self._db.execute(
                "UPDATE playlist_tracks SET position = ? WHERE playlist_id = ? AND track_id = ?",
                (new_position, playlist_id, track_id)
            )
        
        self._event_bus.publish(EventType.PLAYLIST_UPDATED, self.get(playlist_id))
        return True
    
    def get_tracks(self, playlist_id: str) -> List[Track]:
        """
        获取播放列表中的所有曲目
        
        Args:
            playlist_id: 播放列表ID
            
        Returns:
            List[Track]: 曲目列表
        """
        rows = self._db.fetch_all(
            """SELECT t.* FROM tracks t
               JOIN playlist_tracks pt ON t.id = pt.track_id
               WHERE pt.playlist_id = ?
               ORDER BY pt.position""",
            (playlist_id,)
        )
        
        return [Track.from_dict(row) for row in rows]

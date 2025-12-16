"""
媒体库服务模块

管理媒体库的扫描、索引和搜索功能。
"""

from typing import List, Optional, Callable
from pathlib import Path
from datetime import datetime
import uuid
import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.database import DatabaseManager
from core.event_bus import EventBus, EventType
from core.metadata import MetadataParser, AudioMetadata
from models.track import Track
from models.album import Album
from models.artist import Artist


class LibraryService:
    """
    媒体库服务
    
    提供媒体库的扫描、索引和搜索功能。
    
    使用示例:
        library = LibraryService()
        
        # 扫描目录
        library.scan(["D:/Music"])
        
        # 获取所有曲目
        tracks = library.get_all_tracks()
        
        # 搜索
        results = library.search("周杰伦")
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        self._db = db or DatabaseManager()
        self._event_bus = EventBus()
        self._scan_thread: Optional[threading.Thread] = None
        self._stop_scan = threading.Event()
    
    def scan(self, directories: List[str], 
             progress_callback: Optional[Callable[[int, int, str], None]] = None) -> int:
        """
        同步扫描目录
        
        Args:
            directories: 目录列表
            progress_callback: 进度回调 (current, total, file_path)
            
        Returns:
            int: 扫描到的曲目数量
        """
        self._stop_scan.clear()
        total_added = 0
        
        # 收集所有音频文件
        all_files = []
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            
            for ext in MetadataParser.get_supported_formats():
                all_files.extend(dir_path.rglob(f"*{ext}"))
        
        total_files = len(all_files)
        self._event_bus.publish(EventType.LIBRARY_SCAN_STARTED, {
            "total": total_files,
            "directories": directories
        })
        
        for i, file_path in enumerate(all_files):
            if self._stop_scan.is_set():
                break
            
            file_str = str(file_path)
            
            # 检查是否已存在
            existing = self._db.fetch_one(
                "SELECT id FROM tracks WHERE file_path = ?",
                (file_str,)
            )
            
            if not existing:
                track = self._add_track_from_file(file_str)
                if track:
                    total_added += 1
            
            # 进度回调
            if progress_callback:
                progress_callback(i + 1, total_files, file_str)
            
            self._event_bus.publish(EventType.LIBRARY_SCAN_PROGRESS, {
                "current": i + 1,
                "total": total_files,
                "file": file_str,
                "added": total_added
            })
        
        self._event_bus.publish(EventType.LIBRARY_SCAN_COMPLETED, {
            "total_scanned": total_files,
            "total_added": total_added
        })
        
        return total_added
    
    def scan_async(self, directories: List[str]) -> None:
        """
        异步扫描目录
        
        Args:
            directories: 目录列表
        """
        if self._scan_thread and self._scan_thread.is_alive():
            return
        
        self._scan_thread = threading.Thread(
            target=self.scan,
            args=(directories,),
            daemon=True
        )
        self._scan_thread.start()
    
    def stop_scan(self) -> None:
        """停止扫描"""
        self._stop_scan.set()
    
    def _add_track_from_file(self, file_path: str) -> Optional[Track]:
        """从文件添加曲目到数据库"""
        metadata = MetadataParser.parse(file_path)
        if not metadata:
            return None
        
        # 处理艺术家
        artist_id = None
        if metadata.artist:
            artist_id = self._get_or_create_artist(metadata.artist)
        
        # 处理专辑
        album_id = None
        if metadata.album:
            album_id = self._get_or_create_album(
                metadata.album,
                artist_id,
                metadata.year
            )
        
        # 创建曲目
        track_id = str(uuid.uuid4())
        track_data = {
            "id": track_id,
            "title": metadata.title,
            "file_path": file_path,
            "duration_ms": metadata.duration_ms,
            "bitrate": metadata.bitrate,
            "sample_rate": metadata.sample_rate,
            "format": metadata.format,
            "artist_id": artist_id,
            "artist_name": metadata.artist,
            "album_id": album_id,
            "album_name": metadata.album,
            "track_number": metadata.track_number,
            "genre": metadata.genre,
            "year": metadata.year,
            "created_at": datetime.now().isoformat(),
        }
        
        try:
            self._db.insert("tracks", track_data)
            track = Track.from_dict(track_data)
            self._event_bus.publish(EventType.TRACK_ADDED, track)
            return track
        except Exception as e:
            print(f"[LibraryService] 添加曲目失败: {e}")
            return None
    
    def _get_or_create_artist(self, name: str) -> str:
        """获取或创建艺术家"""
        existing = self._db.fetch_one(
            "SELECT id FROM artists WHERE name = ?",
            (name,)
        )
        
        if existing:
            return existing["id"]
        
        artist_id = str(uuid.uuid4())
        self._db.insert("artists", {
            "id": artist_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
        })
        
        return artist_id
    
    def _get_or_create_album(self, title: str, artist_id: Optional[str],
                             year: Optional[int]) -> str:
        """获取或创建专辑"""
        if artist_id:
            existing = self._db.fetch_one(
                "SELECT id FROM albums WHERE title = ? AND artist_id = ?",
                (title, artist_id)
            )
        else:
            existing = self._db.fetch_one(
                "SELECT id FROM albums WHERE title = ? AND artist_id IS NULL",
                (title,)
            )
        
        if existing:
            return existing["id"]
        
        album_id = str(uuid.uuid4())
        self._db.insert("albums", {
            "id": album_id,
            "title": title,
            "artist_id": artist_id,
            "year": year,
            "created_at": datetime.now().isoformat(),
        })
        
        return album_id
    
    def get_all_tracks(self) -> List[Track]:
        """获取所有曲目"""
        rows = self._db.fetch_all(
            "SELECT * FROM tracks ORDER BY artist_name, album_name, track_number"
        )
        return [Track.from_dict(row) for row in rows]
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """获取单个曲目"""
        row = self._db.fetch_one(
            "SELECT * FROM tracks WHERE id = ?",
            (track_id,)
        )
        return Track.from_dict(row) if row else None
    
    def get_track_by_path(self, file_path: str) -> Optional[Track]:
        """根据文件路径获取曲目"""
        row = self._db.fetch_one(
            "SELECT * FROM tracks WHERE file_path = ?",
            (file_path,)
        )
        return Track.from_dict(row) if row else None
    
    def get_albums(self) -> List[Album]:
        """获取所有专辑"""
        rows = self._db.fetch_all(
            """SELECT a.*, 
                      ar.name as artist_name,
                      COUNT(t.id) as track_count,
                      COALESCE(SUM(t.duration_ms), 0) as total_duration_ms
               FROM albums a
               LEFT JOIN artists ar ON a.artist_id = ar.id
               LEFT JOIN tracks t ON t.album_id = a.id
               GROUP BY a.id
               ORDER BY a.title"""
        )
        
        return [Album(
            id=row["id"],
            title=row["title"],
            artist_id=row.get("artist_id"),
            artist_name=row.get("artist_name", ""),
            year=row.get("year"),
            cover_path=row.get("cover_path"),
            track_count=row["track_count"],
            total_duration_ms=row["total_duration_ms"],
        ) for row in rows]
    
    def get_album_tracks(self, album_id: str) -> List[Track]:
        """获取专辑的所有曲目"""
        rows = self._db.fetch_all(
            "SELECT * FROM tracks WHERE album_id = ? ORDER BY track_number",
            (album_id,)
        )
        return [Track.from_dict(row) for row in rows]
    
    def get_artists(self) -> List[Artist]:
        """获取所有艺术家"""
        rows = self._db.fetch_all(
            """SELECT a.*,
                      COUNT(DISTINCT al.id) as album_count,
                      COUNT(DISTINCT t.id) as track_count
               FROM artists a
               LEFT JOIN albums al ON al.artist_id = a.id
               LEFT JOIN tracks t ON t.artist_id = a.id
               GROUP BY a.id
               ORDER BY a.name"""
        )
        
        return [Artist(
            id=row["id"],
            name=row["name"],
            image_path=row.get("image_path"),
            album_count=row["album_count"],
            track_count=row["track_count"],
        ) for row in rows]
    
    def get_artist_tracks(self, artist_id: str) -> List[Track]:
        """获取艺术家的所有曲目"""
        rows = self._db.fetch_all(
            "SELECT * FROM tracks WHERE artist_id = ? ORDER BY album_name, track_number",
            (artist_id,)
        )
        return [Track.from_dict(row) for row in rows]
    
    def search(self, query: str, limit: int = 50) -> dict:
        """
        搜索媒体库
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            dict: 包含tracks, albums, artists的搜索结果
        """
        search_term = f"%{query}%"
        
        # 搜索曲目
        track_rows = self._db.fetch_all(
            """SELECT * FROM tracks 
               WHERE title LIKE ? OR artist_name LIKE ? OR album_name LIKE ?
               LIMIT ?""",
            (search_term, search_term, search_term, limit)
        )
        
        # 搜索专辑
        album_rows = self._db.fetch_all(
            """SELECT a.*, ar.name as artist_name,
                      COUNT(t.id) as track_count,
                      COALESCE(SUM(t.duration_ms), 0) as total_duration_ms
               FROM albums a
               LEFT JOIN artists ar ON a.artist_id = ar.id
               LEFT JOIN tracks t ON t.album_id = a.id
               WHERE a.title LIKE ?
               GROUP BY a.id
               LIMIT ?""",
            (search_term, limit)
        )
        
        # 搜索艺术家
        artist_rows = self._db.fetch_all(
            """SELECT a.*,
                      COUNT(DISTINCT al.id) as album_count,
                      COUNT(DISTINCT t.id) as track_count
               FROM artists a
               LEFT JOIN albums al ON al.artist_id = a.id
               LEFT JOIN tracks t ON t.artist_id = a.id
               WHERE a.name LIKE ?
               GROUP BY a.id
               LIMIT ?""",
            (search_term, limit)
        )
        
        return {
            "tracks": [Track.from_dict(row) for row in track_rows],
            "albums": [Album(
                id=row["id"],
                title=row["title"],
                artist_id=row.get("artist_id"),
                artist_name=row.get("artist_name", ""),
                year=row.get("year"),
                track_count=row["track_count"],
                total_duration_ms=row["total_duration_ms"],
            ) for row in album_rows],
            "artists": [Artist(
                id=row["id"],
                name=row["name"],
                album_count=row["album_count"],
                track_count=row["track_count"],
            ) for row in artist_rows],
        }
    
    def get_recent_tracks(self, limit: int = 20) -> List[Track]:
        """获取最近播放的曲目"""
        rows = self._db.fetch_all(
            """SELECT * FROM tracks 
               WHERE last_played IS NOT NULL
               ORDER BY last_played DESC LIMIT ?""",
            (limit,)
        )
        return [Track.from_dict(row) for row in rows]
    
    def get_most_played_tracks(self, limit: int = 20) -> List[Track]:
        """获取播放次数最多的曲目"""
        rows = self._db.fetch_all(
            """SELECT * FROM tracks 
               WHERE play_count > 0
               ORDER BY play_count DESC LIMIT ?""",
            (limit,)
        )
        return [Track.from_dict(row) for row in rows]
    
    def update_play_stats(self, track_id: str) -> None:
        """更新播放统计"""
        self._db.execute(
            """UPDATE tracks SET 
               play_count = play_count + 1,
               last_played = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), track_id)
        )
        self._db._conn.commit()
    
    def remove_track(self, track_id: str) -> bool:
        """从库中移除曲目"""
        rows = self._db.delete("tracks", "id = ?", (track_id,))
        if rows > 0:
            self._event_bus.publish(EventType.TRACK_REMOVED, track_id)
            return True
        return False
    
    def get_track_count(self) -> int:
        """获取曲目总数"""
        result = self._db.fetch_one("SELECT COUNT(*) as count FROM tracks")
        return result["count"] if result else 0

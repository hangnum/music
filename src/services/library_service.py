"""
媒体库服务模块

管理媒体库的扫描、索引和搜索功能。
"""

from typing import Iterator, List, Optional, Callable, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import threading
import logging

from core.database import DatabaseManager
from core.event_bus import EventBus, EventType
from core.metadata import MetadataParser, AudioMetadata
from models.track import Track
from models.album import Album
from models.artist import Artist

logger = logging.getLogger(__name__)


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
        # 扫描时的缓存（减少重复查询）
        self._artist_cache: Dict[str, str] = {}
        self._album_cache: Dict[str, str] = {}
    
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
        
        # 收集所有音频文件（单次遍历，避免按扩展名重复扫描目录）
        supported_exts = set(MetadataParser.get_supported_formats())
        all_files: List[Path] = []
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue

            for file_path in dir_path.rglob("*"):
                if self._stop_scan.is_set():
                    break
                if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                    all_files.append(file_path)
        
        total_files = len(all_files)
        self._event_bus.publish(EventType.LIBRARY_SCAN_STARTED, {
            "total": total_files,
            "directories": directories
        })

        # 预加载已索引的文件路径，减少每个文件一次的SELECT查询
        existing_paths = set()
        try:
            rows = self._db.fetch_all("SELECT file_path FROM tracks")
            existing_paths = {row["file_path"] for row in rows if row.get("file_path")}
        except Exception:
            existing_paths = set()
        
        # 批量提交阈值
        batch_size = 50
        pending_count = 0
        
        for i, file_path in enumerate(all_files):
            if self._stop_scan.is_set():
                break
            
            file_str = str(file_path)
            
            # 检查是否已存在
            if file_str not in existing_paths:
                track = self._add_track_from_file(file_str, commit=False)
                if track:
                    total_added += 1
                    pending_count += 1
                    existing_paths.add(file_str)
                    
                    # 批量提交
                    if pending_count >= batch_size:
                        self._db.commit()
                        pending_count = 0
            
            # 进度回调
            if progress_callback:
                progress_callback(i + 1, total_files, file_str)
            
            self._event_bus.publish(EventType.LIBRARY_SCAN_PROGRESS, {
                "current": i + 1,
                "total": total_files,
                "file": file_str,
                "added": total_added
            })
        
        # 提交剩余记录
        if pending_count > 0:
            self._db.commit()
        
        # 清理扫描缓存
        self._artist_cache.clear()
        self._album_cache.clear()
        
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
    
    def _add_track_from_file(self, file_path: str, commit: bool = True) -> Optional[Track]:
        """从文件添加曲目到数据库
        
        Args:
            file_path: 音频文件路径
            commit: 是否立即提交（批量扫描时设为False）
        """
        try:
            metadata = MetadataParser.parse(file_path)
        except Exception as e:
            logger.warning("解析元数据失败: %s - %s", file_path, e)
            return None
            
        if not metadata:
            return None
        
        # 处理艺术家
        artist_id = None
        if metadata.artist:
            artist_id = self._get_or_create_artist(metadata.artist, commit=commit)
        
        # 处理专辑
        album_id = None
        if metadata.album:
            album_id = self._get_or_create_album(
                metadata.album,
                artist_id,
                metadata.year,
                commit=commit
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
            self._db.execute(
                "INSERT INTO tracks (id, title, file_path, duration_ms, bitrate, sample_rate, format, artist_id, artist_name, album_id, album_name, track_number, genre, year, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(track_data.values())
            )
            if commit:
                self._db.commit()
            track = Track.from_dict(track_data)
            self._event_bus.publish(EventType.TRACK_ADDED, track)
            return track
        except Exception as e:
            logger.warning("添加曲目失败: %s - %s", file_path, e)
            return None
    
    def _get_or_create_artist(self, name: str, commit: bool = True) -> str:
        """获取或创建艺术家（使用缓存）"""
        # 先检查缓存
        if name in self._artist_cache:
            return self._artist_cache[name]
        
        existing = self._db.fetch_one(
            "SELECT id FROM artists WHERE name = ?",
            (name,)
        )
        
        if existing:
            self._artist_cache[name] = existing["id"]
            return existing["id"]
        
        artist_id = str(uuid.uuid4())
        self._db.execute(
            "INSERT INTO artists (id, name, created_at) VALUES (?, ?, ?)",
            (artist_id, name, datetime.now().isoformat())
        )
        if commit:
            self._db.commit()
        
        self._artist_cache[name] = artist_id
        return artist_id
    
    def _get_or_create_album(self, title: str, artist_id: Optional[str],
                             year: Optional[int], commit: bool = True) -> str:
        """获取或创建专辑（使用缓存）"""
        # 缓存键: (title, artist_id)
        cache_key = (title, artist_id)
        if cache_key in self._album_cache:
            return self._album_cache[cache_key]
        
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
            self._album_cache[cache_key] = existing["id"]
            return existing["id"]
        
        album_id = str(uuid.uuid4())
        self._db.execute(
            "INSERT INTO albums (id, title, artist_id, year, created_at) VALUES (?, ?, ?, ?, ?)",
            (album_id, title, artist_id, year, datetime.now().isoformat())
        )
        if commit:
            self._db.commit()
        
        self._album_cache[cache_key] = album_id
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

    def get_top_genres(self, limit: int = 30) -> List[str]:
        """获取出现次数最多的流派列表（用于提示/LLM 上下文）"""
        try:
            limit = int(limit)
        except Exception:
            limit = 30
        limit = max(1, min(200, limit))

        rows = self._db.fetch_all(
            """SELECT genre, COUNT(*) as c
               FROM tracks
               WHERE genre IS NOT NULL AND TRIM(genre) <> ''
               GROUP BY genre
               ORDER BY c DESC
               LIMIT ?""",
            (limit,),
        )
        return [str(r.get("genre", "")).strip() for r in rows if str(r.get("genre", "")).strip()]

    def query_tracks(
        self,
        query: str = "",
        genre: str = "",
        artist: str = "",
        album: str = "",
        limit: int = 50,
        shuffle: bool = True,
    ) -> List[Track]:
        """
        按条件从音乐库选取曲目（支持按流派/歌手/专辑/关键词筛选）。

        query 会匹配：title/artist_name/album_name/genre
        """
        try:
            limit = int(limit)
        except Exception:
            limit = 50
        limit = max(1, min(200, limit))

        where_parts: List[str] = []
        params: List[object] = []

        q = (query or "").strip()
        if q:
            term = f"%{q}%"
            where_parts.append("(title LIKE ? OR artist_name LIKE ? OR album_name LIKE ? OR genre LIKE ?)")
            params.extend([term, term, term, term])

        g = (genre or "").strip()
        if g:
            where_parts.append("genre LIKE ?")
            params.append(f"%{g}%")

        a = (artist or "").strip()
        if a:
            where_parts.append("artist_name LIKE ?")
            params.append(f"%{a}%")

        al = (album or "").strip()
        if al:
            where_parts.append("album_name LIKE ?")
            params.append(f"%{al}%")

        sql = "SELECT * FROM tracks"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += " ORDER BY RANDOM()" if shuffle else " ORDER BY artist_name, album_name, track_number"
        sql += " LIMIT ?"
        params.append(limit)

        rows = self._db.fetch_all(sql, tuple(params))
        return [Track.from_dict(row) for row in rows]
    
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
        self._db.commit()
    
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

    def iter_tracks_brief(self, batch_size: int = 250, limit: Optional[int] = None) -> Iterator[List[Dict[str, Any]]]:
        """
        以分页方式遍历音乐库的简要曲目信息（用于 LLM 语义筛选，避免一次性加载过多数据）。

        返回的 dict 字段包含：id/title/artist_name/album_name
        """
        try:
            batch_size = int(batch_size)
        except Exception:
            batch_size = 250
        batch_size = max(50, min(800, batch_size))

        remaining = None
        if limit is not None:
            try:
                remaining = int(limit)
            except Exception:
                remaining = None
            if remaining is not None:
                remaining = max(1, remaining)

        offset = 0
        while True:
            if remaining is None:
                size = batch_size
            else:
                if remaining <= 0:
                    break
                size = min(batch_size, remaining)

            rows = self._db.fetch_all(
                """SELECT id, title, artist_name, album_name
                   FROM tracks
                   ORDER BY artist_name, album_name, title
                   LIMIT ? OFFSET ?""",
                (size, offset),
            )
            if not rows:
                break

            yield rows
            offset += len(rows)
            if remaining is not None:
                remaining -= len(rows)

    def get_tracks_by_ids(self, track_ids: List[str]) -> List[Track]:
        """按给定 id 列表批量获取曲目（返回顺序不保证，调用方可自行按 id 重新排序）。"""
        ids = [t for t in track_ids if isinstance(t, str) and t]
        if not ids:
            return []

        out: List[Track] = []
        # sqlite 参数上限可能较小，分块查询
        chunk_size = 400
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i : i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            rows = self._db.fetch_all(f"SELECT * FROM tracks WHERE id IN ({placeholders})", tuple(chunk))
            out.extend([Track.from_dict(r) for r in rows])
        return out

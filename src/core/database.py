"""
数据库管理模块

提供SQLite数据库操作封装，管理媒体库数据。
"""

import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
from contextlib import contextmanager


class DatabaseManager:
    """
    数据库管理器 - 单例模式
    
    提供线程安全的SQLite操作封装。
    
    使用示例:
        db = DatabaseManager("music.db")
        
        # 执行查询
        tracks = db.fetch_all("SELECT * FROM tracks WHERE artist_id = ?", (artist_id,))
        
        # 使用事务
        with db.transaction() as conn:
            db.execute("INSERT INTO tracks ...")
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None) -> 'DatabaseManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        
        self._db_path = db_path or "music_library.db"
        self._local = threading.local()
        self._initialized = True
        self._init_schema()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self._db_path)
            self._local.connection.row_factory = sqlite3.Row
            # 启用外键
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = self._conn
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行SQL语句"""
        return self._conn.execute(sql, params)
    
    def execute_many(self, sql: str, params_list: List[tuple]) -> None:
        """批量执行SQL语句"""
        self._conn.executemany(sql, params_list)
        self._conn.commit()
    
    def commit(self) -> None:
        """提交当前线程的事务（公开方法，供服务层调用）"""
        self._conn.commit()
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """获取单条记录"""
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """获取所有记录"""
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        插入记录
        
        Args:
            table: 表名
            data: 字段名-值字典
            
        Returns:
            int: 插入记录的ID
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor = self.execute(sql, tuple(data.values()))
        self._conn.commit()
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], 
               where: str, where_params: tuple) -> int:
        """
        更新记录
        
        Args:
            table: 表名
            data: 要更新的字段
            where: WHERE条件
            where_params: WHERE参数
            
        Returns:
            int: 受影响的行数
        """
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        cursor = self.execute(sql, tuple(data.values()) + where_params)
        self._conn.commit()
        return cursor.rowcount
    
    def delete(self, table: str, where: str, where_params: tuple) -> int:
        """
        删除记录
        
        Args:
            table: 表名
            where: WHERE条件
            where_params: WHERE参数
            
        Returns:
            int: 受影响的行数
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(sql, where_params)
        self._conn.commit()
        return cursor.rowcount
    
    def _init_schema(self) -> None:
        """初始化数据库Schema"""
        schema_statements = [
            # 艺术家表
            """
            CREATE TABLE IF NOT EXISTS artists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 专辑表
            """
            CREATE TABLE IF NOT EXISTS albums (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist_id TEXT,
                year INTEGER,
                cover_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE SET NULL
            )
            """,
            
            # 音轨表
            """
            CREATE TABLE IF NOT EXISTS tracks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                duration_ms INTEGER DEFAULT 0,
                bitrate INTEGER DEFAULT 0,
                sample_rate INTEGER DEFAULT 0,
                format TEXT,
                artist_id TEXT,
                artist_name TEXT,
                album_id TEXT,
                album_name TEXT,
                track_number INTEGER,
                genre TEXT,
                year INTEGER,
                play_count INTEGER DEFAULT 0,
                last_played TIMESTAMP,
                rating INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE SET NULL,
                FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE SET NULL
            )
            """,
            
            # 播放列表表
            """
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                cover_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 播放列表-音轨关联表
            """
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id TEXT NOT NULL,
                track_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (playlist_id, track_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
            )
            """,

            # 应用状态（键值存储）
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # LLM 队列生成历史（也可作为缓存命中来源）
            """
            CREATE TABLE IF NOT EXISTS llm_queue_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instruction TEXT NOT NULL,
                normalized_instruction TEXT NOT NULL,
                label TEXT NOT NULL,
                track_ids_json TEXT NOT NULL,
                start_index INTEGER NOT NULL DEFAULT 0,
                plan_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # 标签表
            """
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                color TEXT DEFAULT '#808080',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # 曲目-标签关联表
            """
            CREATE TABLE IF NOT EXISTS track_tags (
                track_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (track_id, tag_id),
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
            """,
             
            # 索引
            "CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id)",
            "CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album_id)",
            "CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title)",
            "CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist_id)",
            "CREATE INDEX IF NOT EXISTS idx_playlist_tracks_pos ON playlist_tracks(playlist_id, position)",
            "CREATE INDEX IF NOT EXISTS idx_llm_queue_history_norm_id ON llm_queue_history(normalized_instruction, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_track_tags_track ON track_tags(track_id)",
            "CREATE INDEX IF NOT EXISTS idx_track_tags_tag ON track_tags(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)",
            # 新增索引: 加速按流派、歌手名、文件路径的查询
            "CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks(genre)",
            "CREATE INDEX IF NOT EXISTS idx_tracks_artist_name ON tracks(artist_name)",
            "CREATE INDEX IF NOT EXISTS idx_tracks_file_path ON tracks(file_path)",
        ]
        
        for statement in schema_statements:
            try:
                self.execute(statement.strip())
            except Exception as e:
                # 忽略已存在的表/索引错误，用于增量迁移
                if "already exists" not in str(e).lower():
                    # 对于其他错误，继续尝试（可能是旧数据库缺少某些表）
                    pass
        self._conn.commit()
    
    def close(self) -> None:
        """关闭当前线程的连接"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def close_all(self) -> None:
        """关闭所有连接并重置实例"""
        self.close()
        DatabaseManager._instance = None
        self._initialized = False
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（仅用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

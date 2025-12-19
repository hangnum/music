"""
数据库管理模块

提供SQLite数据库操作封装，管理媒体库数据。
"""

import sqlite3
import re
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


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
    
    @staticmethod
    def _get_default_db_path() -> str:
        """获取用户数据目录下的默认数据库路径"""
        import sys
        import os
        from pathlib import Path
        
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        
        db_dir = base / "python-music-player"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "music_library.db")
    
    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        
        if db_path:
            self._db_path = db_path
        else:
            # 使用用户数据目录作为默认路径
            new_path = self._get_default_db_path()
            old_path = Path("music_library.db")
            
            # 自动迁移：如果新路径不存在但旧路径存在，则移动文件
            if not Path(new_path).exists() and old_path.exists():
                import shutil
                try:
                    Path(new_path).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_path), new_path)
                except Exception:
                    # 移动失败则继续使用旧路径
                    new_path = str(old_path)
            
            self._db_path = new_path
        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._initialized = True
        self._init_schema()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            # Set timeout to 30 seconds to handle concurrent access better
            self._local.connection = sqlite3.connect(self._db_path, timeout=30.0)
            self._local.connection.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency
            with self._write_lock:
                self._local.connection.execute("PRAGMA journal_mode=WAL")
                self._local.connection.execute("PRAGMA synchronous=NORMAL")
            
            # 启用外键
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            
            # Initialize transaction tracking flag
            self._local.in_transaction = False
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器
        
        在此上下文内的写操作不会自动提交，而是在上下文结束时统一提交或回滚。
        """
        with self._write_lock:
            conn = self._conn
            self._local.in_transaction = True
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                self._local.in_transaction = False
    
    @staticmethod
    def _strip_leading_sql_comments(sql: str) -> str:
        s = sql.lstrip()
        while True:
            if s.startswith("--"):
                newline_index = s.find("\n")
                if newline_index == -1:
                    return ""
                s = s[newline_index + 1 :].lstrip()
                continue
            if s.startswith("/*"):
                end_index = s.find("*/")
                if end_index == -1:
                    return ""
                s = s[end_index + 2 :].lstrip()
                continue
            return s

    @classmethod
    def _is_write_sql(cls, sql: str) -> bool:
        write_keywords = ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")

        stripped = cls._strip_leading_sql_comments(sql)
        sql_upper = stripped.lstrip().upper()
        if not sql_upper:
            return False

        match = re.match(r"[A-Z]+", sql_upper)
        first_keyword = match.group(0) if match else ""
        if first_keyword in write_keywords:
            return True

        if first_keyword == "WITH":
            return bool(
                re.search(r"\bINSERT\s+INTO\b", sql_upper)
                or re.search(r"\bREPLACE\s+INTO\b", sql_upper)
                or re.search(r"\bUPDATE\b", sql_upper)
                or re.search(r"\bDELETE\s+FROM\b", sql_upper)
            )

        return False

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行SQL语句
        
        对于写操作(INSERT/UPDATE/DELETE等)，当不在显式事务上下文中时，
        会自动提交以释放数据库锁，避免并发写入时的死锁问题。
        在 transaction() 上下文内的写操作不会自动提交。
        """
        max_retries = 5
        retry_delay = 0.1
        
        is_write = self._is_write_sql(sql)
        
        # Check if we're inside an explicit transaction
        in_transaction = getattr(self._local, 'in_transaction', False)
        
        for i in range(max_retries):
            try:
                if is_write:
                    with self._write_lock:
                        cursor = self._conn.execute(sql, params)
                        if not in_transaction:
                            self._conn.commit()
                else:
                    cursor = self._conn.execute(sql, params)
                return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and i < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (i + 1))  # Exponential-ish backoff
                    continue
                raise
        
        # 如果所有重试都失败，最后一次异常会被 raise
        # (正常情况下不会执行到这里，因为最后一次失败会 raise)
    
    def execute_many(self, sql: str, params_list: List[tuple]) -> None:
        """批量执行SQL语句"""
        is_write = self._is_write_sql(sql)
        in_transaction = getattr(self._local, "in_transaction", False)

        if is_write:
            with self._write_lock:
                self._conn.executemany(sql, params_list)
                if not in_transaction:
                    self._conn.commit()
        else:
            self._conn.executemany(sql, params_list)
    
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
                source TEXT DEFAULT 'user',
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

            # LLM 批量标注任务追踪表
            """
            CREATE TABLE IF NOT EXISTS llm_tagging_jobs (
                id TEXT PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                total_tracks INTEGER NOT NULL DEFAULT 0,
                processed_tracks INTEGER NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                error_message TEXT
            )
            """,

            # 已被 LLM 标注的曲目记录（防止重复标注）
            """
            CREATE TABLE IF NOT EXISTS llm_tagged_tracks (
                track_id TEXT PRIMARY KEY,
                tagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                job_id TEXT,
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES llm_tagging_jobs(id) ON DELETE SET NULL
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
            "CREATE INDEX IF NOT EXISTS idx_tags_source ON tags(source)",
            "CREATE INDEX IF NOT EXISTS idx_llm_tagged_tracks_job ON llm_tagged_tracks(job_id)",
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
        
        # 执行迁移（为已存在的表添加新列）
        self._run_migrations()
        
        self._conn.commit()
    
    def _run_migrations(self) -> None:
        """
        执行数据库迁移
        
        用于向已存在的表添加新列。使用 ALTER TABLE ADD COLUMN，
        该语句在 SQLite 中如果列已存在会报错，所以需要先检查。
        """
        migrations = [
            # Migration 1: 为 tags 表添加 source 列
            {
                "table": "tags",
                "column": "source",
                "sql": "ALTER TABLE tags ADD COLUMN source TEXT DEFAULT 'user'",
            },
        ]
        
        for migration in migrations:
            if not self._column_exists(migration["table"], migration["column"]):
                try:
                    self.execute(migration["sql"])
                except Exception as e:
                    # 忽略迁移错误（列可能已存在于某些边缘情况）
                    if "duplicate column" not in str(e).lower():
                        logger.exception("数据库迁移失败: %s", migration)
    
    def _column_exists(self, table: str, column: str) -> bool:
        """检查表中是否存在某列"""
        try:
            cursor = self.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            return column in columns
        except Exception:
            return False
    
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

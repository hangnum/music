"""
Database Management Module

Provides SQLite database operation encapsulation and manages media library data.
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
    Database Manager - Singleton Pattern
    
    Provides thread-safe SQLite operation encapsulation.
    
    Example:
        db = DatabaseManager("music.db")
        
        # Execute query
        tracks = db.fetch_all("SELECT * FROM tracks WHERE artist_id = ?", (artist_id,))
        
        # Use transaction
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
        """Get the default database path in the user data directory"""
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
            # Use user data directory as the default path
            new_path = self._get_default_db_path()
            old_path = Path("music_library.db")
            
            # Automatic migration: if new path doesn't exist but old path exists, move the file
            if not Path(new_path).exists() and old_path.exists():
                import shutil
                try:
                    Path(new_path).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_path), new_path)
                except Exception:
                    # Continue using old path if relocation fails
                    new_path = str(old_path)
            
            self._db_path = new_path
        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._initialized = True
        self._init_schema()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            # Set timeout to 30 seconds to handle concurrent access better
            self._local.connection = sqlite3.connect(self._db_path, timeout=30.0)
            self._local.connection.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency
            with self._write_lock:
                self._local.connection.execute("PRAGMA journal_mode=WAL")
                self._local.connection.execute("PRAGMA synchronous=NORMAL")
            
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            
            # Initialize transaction tracking flag
            self._local.in_transaction = False
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """Transaction context manager
        
        Write operations within this context are not automatically committed,
        but are committed or rolled back collectively when the context ends.
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
        """Execute SQL statement
        
        For write operations (INSERT/UPDATE/DELETE, etc.), automatically commits when
        not within an explicit transaction context to release database locks and
        avoid deadlocks during concurrent writes.
        Write operations within a transaction() context will not be automatically committed.
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
        
        # If all retries fail, the last exception will be raised
        # (Normally this won't be reached because the last failure will raise)
    
    def execute_many(self, sql: str, params_list: List[tuple]) -> None:
        """Bulk execute SQL statements"""
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
        """Commit current thread's transaction (Public method for service layer)"""
        self._conn.commit()
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single record"""
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all records"""
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert record
        
        Args:
            table: Table name
            data: Dictionary of column names and values
            
        Returns:
            int: ID of the inserted record
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor = self.execute(sql, tuple(data.values()))
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], 
               where: str, where_params: tuple) -> int:
        """
        Update record
        
        Args:
            table: Table name
            data: Fields to update
            where: WHERE condition
            where_params: WHERE parameters
            
        Returns:
            int: Number of affected rows
        """
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        cursor = self.execute(sql, tuple(data.values()) + where_params)
        return cursor.rowcount
    
    def delete(self, table: str, where: str, where_params: tuple) -> int:
        """
        Delete record
        
        Args:
            table: Table name
            where: WHERE condition
            where_params: WHERE parameters
            
        Returns:
            int: Number of affected rows
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(sql, where_params)
        return cursor.rowcount
    
    def _init_schema(self) -> None:
        """Initialize database Schema"""
        from core.schema import get_all_schema_statements
        from core.migrations import run_migrations
        
        for statement in get_all_schema_statements():
            try:
                self.execute(statement.strip())
            except Exception as e:
                # Ignore existing table/index errors for incremental migrations
                if "already exists" not in str(e).lower():
                    # For other errors, keep trying (maybe some tables are missing in old DB)
                    pass
        
        # Execute migrations (add new columns to existing tables)
        run_migrations(self)
        
        self._conn.commit()

    
    def close(self) -> None:
        """Close current thread's connection"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def close_all(self) -> None:
        """Close all connections and reset instance"""
        self.close()
        DatabaseManager._instance = None
        self._initialized = False
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (For testing only)
        
        Warning: This method will be removed in a future version.
        Use AppContainerFactory.create_for_testing() to create independent test instances.
        """
        import warnings
        warnings.warn(
            "DatabaseManager.reset_instance() is deprecated and will be removed. "
            "Use AppContainerFactory.create_for_testing() for isolated test instances.",
            FutureWarning,
            stacklevel=2
        )
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

"""
数据库 Schema 定义

包含所有表结构和索引定义。
"""

from __future__ import annotations

# 表结构 SQL 语句
TABLE_STATEMENTS = [
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
]

# 索引 SQL 语句
INDEX_STATEMENTS = [
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
    # 加速按流派、歌手名、文件路径的查询
    "CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks(genre)",
    "CREATE INDEX IF NOT EXISTS idx_tracks_artist_name ON tracks(artist_name)",
    "CREATE INDEX IF NOT EXISTS idx_tracks_file_path ON tracks(file_path)",
]


def get_all_schema_statements() -> list:
    """获取所有 Schema 语句（表 + 索引）"""
    return TABLE_STATEMENTS + INDEX_STATEMENTS

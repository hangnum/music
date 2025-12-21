"""
Database Schema Definitions

Contains all table structure and index definitions.
"""

from __future__ import annotations

# Table structure SQL statements
TABLE_STATEMENTS = [
    # Artists table
    """
    CREATE TABLE IF NOT EXISTS artists (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    
    # Albums table
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
    
    # Tracks table
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
    
    # Playlists table
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
    
    # Playlist-track relation table
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

    # App state (key-value storage)
    """
    CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # LLM queue generation history (also used as cache hit source)
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

    # Tags table
    """
    CREATE TABLE IF NOT EXISTS tags (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        color TEXT DEFAULT '#808080',
        source TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Track-tag relation table
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

    # LLM batch tagging job tracking table
    """
    CREATE TABLE IF NOT EXISTS llm_tagging_jobs (
        id TEXT PRIMARY KEY,
        name TEXT DEFAULT '',
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        total_tracks INTEGER NOT NULL DEFAULT 0,
        processed_tracks INTEGER NOT NULL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        error_message TEXT
    )
    """,

    # Record of tracks already tagged by LLM (to prevent duplicate tagging)
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

# Index SQL statements
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
    # Speed up queries by genre, artist name, and file path
    "CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks(genre)",
    "CREATE INDEX IF NOT EXISTS idx_tracks_artist_name ON tracks(artist_name)",
    "CREATE INDEX IF NOT EXISTS idx_tracks_file_path ON tracks(file_path)",
]


def get_all_schema_statements() -> list:
    """Get all schema statements (tables + indexes)"""
    return TABLE_STATEMENTS + INDEX_STATEMENTS

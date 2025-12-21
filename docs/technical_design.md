# High-Quality Music Player - Technical Design Document

## 1. Core Module Detailed Design

### 1.1 Audio Engine Module (AudioEngine)

#### 1.1.1 Design Goals

- Support decoding and playback of various audio formats
- Provide a unified playback control interface
- **Support advanced audio features**: Gapless playback, Crossfade, ReplayGain, 10-band Equalizer (EQ)
- **Multi-backend support**: Support Miniaudio (default/hi-fi), VLC (compatibility), and Pygame (basic) via Factory pattern

#### 1.1.2 Class Design

```python
# src/core/audio_engine.py

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from enum import Enum

class AudioEngineBase(ABC):
    """Audio engine base class"""
    
    # ... (Original basic playback control methods: play, pause, stop, seek, etc.)
    
    # ===== Advanced Features Interface =====
    
    @abstractmethod
    def supports_gapless(self) -> bool:
        """Whether gapless playback is supported"""
        return False

    @abstractmethod
    def supports_crossfade(self) -> bool:
        """Whether crossfade is supported"""
        return False

    @abstractmethod
    def supports_equalizer(self) -> bool:
        """Whether EQ is supported"""
        return False

    @abstractmethod
    def supports_replay_gain(self) -> bool:
        """Whether ReplayGain is supported"""
        return False

    @abstractmethod
    def set_next_track(self, file_path: str) -> bool:
        """Preload next track (for Gapless)"""
        return False

    @abstractmethod
    def set_crossfade_duration(self, duration_ms: int) -> None:
        """Set crossfade duration"""
        pass

    @abstractmethod
    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """Set ReplayGain"""
        pass

    @abstractmethod
    def set_equalizer(self, bands: List[float]) -> None:
        """Set 10-band EQ gain"""
        pass

# src/core/engine_factory.py

class AudioEngineFactory:
    """Audio engine factory"""
    
    PRIORITY_ORDER = ["miniaudio", "vlc", "pygame"]

    @classmethod
    def create(cls, backend: str = "miniaudio") -> AudioEngineBase:
        """Create engine instance with automatic fallback"""
        pass

# src/core/miniaudio_engine.py

class MiniaudioEngine(AudioEngineBase):
    """
    Miniaudio-based high-performance audio engine
    Supports: Gapless, Crossfade, ReplayGain, 10-Band EQ (Biquad Filter)
    Fallback: Uses FFmpegTranscoder for unsupported formats
    """
    pass

# src/core/ffmpeg_transcoder.py

class FFmpegTranscoder:
    """FFmpeg Transcoder"""
    
    @staticmethod
    def is_available() -> bool:
        """Check if FFmpeg is available"""
        pass

    @staticmethod
    def transcode_to_wav(input_path: str) -> Optional[str]:
        """Transcode audio to WAV format for compatibility"""
        pass
```

#### 1.1.3 Equalizer Model (EQPreset)

```python
# src/models/eq_preset.py

class EQPreset(Enum):
    FLAT = "flat"
    ROCK = "rock"
    POP = "pop"
    # ... other presets

@dataclass
class EQBands:
    bands: tuple  # dB values for 10 bands
```

---

### 1.2 Event Bus Module (EventBus)

#### 1.2.1 Design Goals

- Implement publish-subscribe pattern
- Support asynchronous event processing
- Thread-safe

#### 1.2.2 Class Design

```python
# src/core/event_bus.py

from typing import Dict, List, Callable, Any, Optional
from enum import Enum
import threading
import uuid
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

class EventType(Enum):
    # Playback events
    TRACK_LOADED = "track_loaded"
    TRACK_STARTED = "track_started"
    TRACK_ENDED = "track_ended"
    TRACK_PAUSED = "track_paused"
    TRACK_RESUMED = "track_resumed"
    POSITION_CHANGED = "position_changed"
    VOLUME_CHANGED = "volume_changed"
    
    # Playlist events
    PLAYLIST_CREATED = "playlist_created"
    PLAYLIST_UPDATED = "playlist_updated"
    PLAYLIST_DELETED = "playlist_deleted"
    QUEUE_CHANGED = "queue_changed"
    
    # Media library events
    LIBRARY_SCAN_STARTED = "library_scan_started"
    LIBRARY_SCAN_PROGRESS = "library_scan_progress"
    LIBRARY_SCAN_COMPLETED = "library_scan_completed"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"
    
    # System events
    CONFIG_CHANGED = "config_changed"
    THEME_CHANGED = "theme_changed"
    ERROR_OCCURRED = "error_occurred"

class EventBus:
    """Event Bus - Singleton Pattern"""
    
    _instance: Optional['EventBus'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._subscribers: Dict[EventType, Dict[str, Callable]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._event_queue: Queue = Queue()
        self._lock = threading.Lock()
        self._initialized = True
    
    def subscribe(self, event_type: EventType, 
                  callback: Callable[[Any], None]) -> str:
        """Subscribe to event, returns subscription ID"""
        subscription_id = str(uuid.uuid4())
        
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = {}
            self._subscribers[event_type][subscription_id] = callback
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe"""
        with self._lock:
            for event_type in self._subscribers:
                if subscription_id in self._subscribers[event_type]:
                    del self._subscribers[event_type][subscription_id]
                    return True
        return False
    
    def publish(self, event_type: EventType, data: Any = None) -> None:
        """Publish event"""
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())
        
        for callback in callbacks:
            self._executor.submit(self._safe_call, callback, data)
    
    def publish_sync(self, event_type: EventType, data: Any = None) -> None:
        """Publish event synchronously"""
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())
        
        for callback in callbacks:
            self._safe_call(callback, data)
    
    def _safe_call(self, callback: Callable, data: Any) -> None:
        """Safely call callback"""
        try:
            callback(data)
        except Exception as e:
            self.publish(EventType.ERROR_OCCURRED, {
                "source": "EventBus",
                "error": str(e)
            })
    
    def shutdown(self) -> None:
        """Shutdown event bus"""
        self._executor.shutdown(wait=True)
```

---

### 1.3 Metadata Parsing Module (Metadata)

#### 1.3.1 Design Goals

- Parse metadata for multiple audio formats
- Extract cover art
- Support metadata writing

#### 1.3.2 Class Design

```python
# src/core/metadata.py

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
import base64

@dataclass
class AudioMetadata:
    """Audio metadata"""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: Optional[int] = None
    track_number: Optional[int] = None
    total_tracks: Optional[int] = None
    disc_number: Optional[int] = None
    genre: str = ""
    duration_ms: int = 0
    bitrate: int = 0
    sample_rate: int = 0
    channels: int = 2
    format: str = ""
    file_path: str = ""
    cover_data: Optional[bytes] = None
    cover_mime: str = ""

class MetadataParser:
    """Metadata parser"""
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', 
                         '.aac', '.wma', '.ape', '.opus'}
    
    @classmethod
    def parse(cls, file_path: str) -> Optional[AudioMetadata]:
        """Parse audio file metadata"""
        path = Path(file_path)
        
        if not path.exists():
            return None
        
        suffix = path.suffix.lower()
        if suffix not in cls.SUPPORTED_FORMATS:
            return None
        
        try:
            from mutagen import File
            from mutagen.easyid3 import EasyID3
            from mutagen.mp3 import MP3
            from mutagen.flac import FLAC
            from mutagen.oggvorbis import OggVorbis
            from mutagen.mp4 import MP4
            
            audio = File(file_path)
            if audio is None:
                return None
            
            metadata = AudioMetadata(file_path=file_path)
            
            # Basic information
            if audio.info:
                metadata.duration_ms = int(audio.info.length * 1000)
                metadata.bitrate = getattr(audio.info, 'bitrate', 0)
                metadata.sample_rate = getattr(audio.info, 'sample_rate', 0)
                metadata.channels = getattr(audio.info, 'channels', 2)
            
            metadata.format = suffix[1:].upper()
            
            # Parse tags based on format
            if suffix == '.mp3':
                cls._parse_mp3(file_path, metadata)
            elif suffix == '.flac':
                cls._parse_flac(audio, metadata)
            elif suffix == '.ogg':
                cls._parse_ogg(audio, metadata)
            elif suffix in {'.m4a', '.aac'}:
                cls._parse_m4a(audio, metadata)
            else:
                cls._parse_generic(audio, metadata)
            
            # Use filename if no title
            if not metadata.title:
                metadata.title = path.stem
            
            return metadata
            
        except Exception as e:
            print(f"Failed to parse metadata: {file_path}, Error: {e}")
            return None
    
    @classmethod
    def _parse_mp3(cls, file_path: str, metadata: AudioMetadata) -> None:
        """Parse MP3 metadata"""
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3
        
        try:
            audio = MP3(file_path)
            tags = audio.tags
            
            if tags:
                metadata.title = str(tags.get('TIT2', metadata.title))
                metadata.artist = str(tags.get('TPE1', ''))
                metadata.album = str(tags.get('TALB', ''))
                metadata.album_artist = str(tags.get('TPE2', ''))
                
                if 'TDRC' in tags:
                    try:
                        metadata.year = int(str(tags['TDRC']))
                    except:
                        pass
                
                if 'TRCK' in tags:
                    track_str = str(tags['TRCK'])
                    if '/' in track_str:
                        parts = track_str.split('/')
                        metadata.track_number = int(parts[0])
                        metadata.total_tracks = int(parts[1])
                    else:
                        metadata.track_number = int(track_str)
                
                # Cover art
                for key in tags:
                    if key.startswith('APIC'):
                        apic = tags[key]
                        metadata.cover_data = apic.data
                        metadata.cover_mime = apic.mime
                        
        except Exception as e:
            print(f"Failed to parse MP3 tags: {e}")
    
    @classmethod
    def _parse_flac(cls, audio, metadata: AudioMetadata) -> None:
        """Parse FLAC metadata"""
        metadata.title = audio.get('title', [''])[0]
        metadata.artist = audio.get('artist', [''])[0]
        metadata.album = audio.get('album', [''])[0]
        metadata.album_artist = audio.get('albumartist', [''])[0]
        metadata.genre = audio.get('genre', [''])[0]
        
        if 'date' in audio:
            try:
                metadata.year = int(audio['date'][0][:4])
            except:
                pass
        
        if 'tracknumber' in audio:
            try:
                metadata.track_number = int(audio['tracknumber'][0])
            except:
                pass
        
        # FLAC cover
        if audio.pictures:
            metadata.cover_data = audio.pictures[0].data
            metadata.cover_mime = audio.pictures[0].mime
    
    @classmethod
    def _parse_ogg(cls, audio, metadata: AudioMetadata) -> None:
        """Parse OGG metadata"""
        metadata.title = audio.get('title', [''])[0]
        metadata.artist = audio.get('artist', [''])[0]
        metadata.album = audio.get('album', [''])[0]
    
    @classmethod
    def _parse_m4a(cls, audio, metadata: AudioMetadata) -> None:
        """Parse M4A/AAC metadata"""
        metadata.title = audio.get('\xa9nam', [''])[0]
        metadata.artist = audio.get('\xa9ART', [''])[0]
        metadata.album = audio.get('\xa9alb', [''])[0]
        
        if 'covr' in audio:
            metadata.cover_data = bytes(audio['covr'][0])
            metadata.cover_mime = 'image/jpeg'
    
    @classmethod
    def _parse_generic(cls, audio, metadata: AudioMetadata) -> None:
        """Generic metadata parsing"""
        if hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            metadata.title = tags.get('title', [''])[0] if 'title' in tags else ''
            metadata.artist = tags.get('artist', [''])[0] if 'artist' in tags else ''
            metadata.album = tags.get('album', [''])[0] if 'album' in tags else ''
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported formats"""
        return list(MetadataParser.SUPPORTED_FORMATS)
```

---

### 1.4 Database Management Module (Database)

#### 1.4.1 Database Schema

```sql
-- Artists table
CREATE TABLE IF NOT EXISTS artists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 专辑表
CREATE TABLE IF NOT EXISTS albums (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    artist_id TEXT,
    year INTEGER,
    cover_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artists(id)
);

-- 音轨表
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_path TEXT UNIQUE NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    bitrate INTEGER DEFAULT 0,
    sample_rate INTEGER DEFAULT 0,
    format TEXT,
    artist_id TEXT,
    album_id TEXT,
    track_number INTEGER,
    genre TEXT,
    year INTEGER,
    play_count INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    rating INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artists(id),
    FOREIGN KEY (album_id) REFERENCES albums(id)
);

-- 播放列表表
CREATE TABLE IF NOT EXISTS playlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    cover_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 播放列表-音轨关联表
CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id TEXT NOT NULL,
    track_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (playlist_id, track_id),
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT,
    source TEXT DEFAULT 'user', -- 'user' or 'llm'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 曲目-标签关联表
CREATE TABLE IF NOT EXISTS track_tags (
    track_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (track_id, tag_id),
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- LLM Tagging Jobs table
CREATE TABLE IF NOT EXISTS llm_tagging_jobs (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_tracks INTEGER NOT NULL DEFAULT 0,
    processed_tracks INTEGER NOT NULL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT
);

-- LLM Tagged Tracks records
CREATE TABLE IF NOT EXISTS llm_tagged_tracks (
    track_id TEXT PRIMARY KEY,
    tagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES llm_tagging_jobs(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
CREATE INDEX IF NOT EXISTS idx_tags_source ON tags(source);
CREATE INDEX IF NOT EXISTS idx_llm_tagged_tracks_job ON llm_tagged_tracks(job_id);
CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist_id);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_position ON playlist_tracks(playlist_id, position);
```

#### 1.4.2 Class Design

```python
# src/core/database.py

import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
from contextlib import contextmanager
import re # Added for _is_write_sql

class DatabaseManager:
    """Database Manager - Singleton Pattern"""
    
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
        # Added for transaction management
        self._write_lock = threading.Lock()
        self._in_transaction = False
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self._db_path)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        with self._write_lock:
            try:
                self._in_transaction = True
                yield self._conn
                self._conn.commit()
            except Exception as e:
                self._conn.rollback()
                raise e
            finally:
                self._in_transaction = False
    
    def execute(self, sql: str, params: tuple = (), max_retries: int = 5, retry_delay: float = 0.1) -> sqlite3.Cursor:
        """Execute SQL with auto-commit, write lock, and retry mechanism"""
        is_write = self._is_write_sql(sql)
        
        for i in range(max_retries):
            try:
                if is_write:
                    with self._write_lock:
                        cursor = self._conn.execute(sql, params)
                        if not self._in_transaction:
                            self._conn.commit()
                else:
                    cursor = self._conn.execute(sql, params)
                return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and i < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (i + 1))
                    continue
                raise
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch single record"""
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Fetch all records"""
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def _init_schema(self) -> None:
        """Initialize database Schema"""
        schema_sql = """
        -- Artists table
        CREATE TABLE IF NOT EXISTS artists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Albums table
        CREATE TABLE IF NOT EXISTS albums (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            artist_id TEXT,
            year INTEGER,
            cover_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id)
        );
        
        -- Tracks table
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            file_path TEXT UNIQUE NOT NULL,
            duration_ms INTEGER DEFAULT 0,
            bitrate INTEGER DEFAULT 0,
            sample_rate INTEGER DEFAULT 0,
            format TEXT,
            artist_id TEXT,
            album_id TEXT,
            track_number INTEGER,
            genre TEXT,
            year INTEGER,
            play_count INTEGER DEFAULT 0,
            last_played TIMESTAMP,
            rating INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id),
            FOREIGN KEY (album_id) REFERENCES albums(id)
        );
        
        -- Playlists table
        CREATE TABLE IF NOT EXISTS playlists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            cover_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Playlist tracks mapping table
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            playlist_id TEXT NOT NULL,
            track_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (playlist_id, track_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
        );
        
        -- Tags table
        CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            color TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Track tags mapping table
        CREATE TABLE IF NOT EXISTS track_tags (
            track_id TEXT NOT NULL,
            tag_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (track_id, tag_id),
            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );
        
        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id);
        CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album_id);
        CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
        """
        
        for statement in schema_sql.split(';'):
            if statement.strip():
                self.execute(statement)
        self._conn.commit()
    
    @classmethod
    def _strip_leading_sql_comments(cls, sql: str) -> str:
        """Strip leading SQL comments (single-line and multi-line)"""
        # Remove single-line comments like -- comment
        sql = re.sub(r'^\s*--.*$', '', sql, flags=re.MULTILINE)
        # Remove multi-line comments /* comment */
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        return sql.strip()

    @classmethod
    def _is_write_sql(cls, sql: str) -> bool:
        """Identify if the SQL statement is a write operation (supports CTE/WITH)"""
        write_keywords = ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")
        stripped = cls._strip_leading_sql_comments(sql).lstrip().upper()
        if not stripped: return False
        
        match = re.match(r"[A-Z]+", stripped)
        first_keyword = match.group(0) if match else ""
        if first_keyword in write_keywords: return True
        if first_keyword == "WITH":
            return bool(re.search(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", stripped))
        return False

    def close(self) -> None:
        """Close connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection
```

---

### 1.5 LLM Provider Framework (LLMProvider Framework)

#### 1.5.1 Design Goals

- Support multiple LLM models (e.g., GPT, Gemini, DeepSeek).
- Unified input and output interface.
- Easy to extend with new model providers.

#### 1.5.2 Class Design

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class LLMProvider(ABC):
    @abstractmethod
    def chat_completions(self, messages: List[Dict]) -> str:
        pass
```

---

### 1.6 Tag Service Architecture (TagService)

#### 1.6.1 Core Responsibilities

- Provide CRUD operations for tags.
- Manage many-to-many relationships between tags and tracks in the media library.

---

### 1.7 LLM Tagging Service Architecture (LLMTaggingService)

#### 1.7.1 Design Goals

- Automatically perform batch tagging for tracks in the media library.
- Support resume from breakpoint and progress management.
- Avoid duplicate tagging for the same track.

#### 1.7.2 Class Design

```python
class LLMTaggingService:
    def start_tagging_job(self, track_ids: List[str] = None) -> str:
        """Start tagging job"""
        pass

    def stop_tagging_job(self, job_id: str) -> bool:
        """Stop job"""
        pass
        
    def get_job_status(self, job_id: str) -> TaggingJobStatus:
        """Get job status"""
        pass
```

---

## 2. Service Layer Design

### 2.1 Player Service (PlayerService)

```python
# src/services/player_service.py

from typing import List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
import random

from core.audio_engine import AudioEngineBase, PygameAudioEngine, PlayerState
from core.event_bus import EventBus, EventType
from models.track import Track

class PlayMode(Enum):
    SEQUENTIAL = "sequential"
    REPEAT_ALL = "repeat_all"
    REPEAT_ONE = "repeat_one"
    SHUFFLE = "shuffle"

@dataclass
class PlaybackState:
    current_track: Optional[Track] = None
    position_ms: int = 0
    duration_ms: int = 0
    is_playing: bool = False
    volume: float = 1.0
    play_mode: PlayMode = PlayMode.SEQUENTIAL

class PlayerService:
    """Player Service"""
    
    def __init__(self, audio_engine: Optional[AudioEngineBase] = None):
        self._engine = audio_engine or PygameAudioEngine()
        self._event_bus = EventBus()
        
        self._queue: List[Track] = []
        self._current_index: int = -1
        self._play_mode: PlayMode = PlayMode.SEQUENTIAL
        self._shuffle_indices: List[int] = []
        
        # Bind engine callbacks
        self._engine.set_on_end(self._on_track_end)
        self._engine.set_on_error(self._on_error)
    
    @property
    def state(self) -> PlaybackState:
        """Get current playback state"""
        current_track = self._queue[self._current_index] if 0 <= self._current_index < len(self._queue) else None
        return PlaybackState(
            current_track=current_track,
            position_ms=self._engine.get_position(),
            duration_ms=self._engine.get_duration(),
            is_playing=self._engine.state == PlayerState.PLAYING,
            volume=self._engine.volume,
            play_mode=self._play_mode
        )
    
    def set_queue(self, tracks: List[Track], start_index: int = 0) -> None:
        """Set playback queue"""
        self._queue = tracks.copy()
        self._current_index = start_index
        self._shuffle_indices = list(range(len(tracks)))
        if self._play_mode == PlayMode.SHUFFLE:
            random.shuffle(self._shuffle_indices)
        self._event_bus.publish(EventType.QUEUE_CHANGED, self._queue)
    
    def play(self, track: Optional[Track] = None) -> bool:
        """Play specified track or current track"""
        if track:
            if track in self._queue:
                self._current_index = self._queue.index(track)
            else:
                self._queue.append(track)
                self._current_index = len(self._queue) - 1
        
        if self._current_index < 0 or self._current_index >= len(self._queue):
            return False
        
        current = self._queue[self._current_index]
        if self._engine.load(current.file_path):
            self._engine.play()
            self._event_bus.publish(EventType.TRACK_STARTED, current)
            return True
        return False
    
    def pause(self) -> None:
        """Pause playback"""
        if self._engine.state == PlayerState.PLAYING:
            self._engine.pause()
            self._event_bus.publish(EventType.TRACK_PAUSED)
    
    def resume(self) -> None:
        """Resume playback"""
        if self._engine.state == PlayerState.PAUSED:
            self._engine.resume()
            self._event_bus.publish(EventType.TRACK_RESUMED)
    
    def toggle_play(self) -> None:
        """Toggle play/pause"""
        if self._engine.state == PlayerState.PLAYING:
            self.pause()
        elif self._engine.state == PlayerState.PAUSED:
            self.resume()
        else:
            self.play()
    
    def stop(self) -> None:
        """Stop playback"""
        self._engine.stop()
        self._event_bus.publish(EventType.TRACK_ENDED)
    
    def next_track(self) -> Optional[Track]:
        """Next track"""
        if not self._queue:
            return None
        
        if self._play_mode == PlayMode.SHUFFLE:
            shuffle_pos = self._shuffle_indices.index(self._current_index)
            if shuffle_pos < len(self._shuffle_indices) - 1:
                self._current_index = self._shuffle_indices[shuffle_pos + 1]
            elif self._play_mode == PlayMode.REPEAT_ALL:
                random.shuffle(self._shuffle_indices)
                self._current_index = self._shuffle_indices[0]
            else:
                return None
        else:
            if self._current_index < len(self._queue) - 1:
                self._current_index += 1
            elif self._play_mode == PlayMode.REPEAT_ALL:
                self._current_index = 0
            else:
                return None
        
        self.play()
        return self._queue[self._current_index]
    
    def previous_track(self) -> Optional[Track]:
        """Previous track"""
        if not self._queue:
            return None
        
        # If played for more than 3 seconds, replay the current track
        if self._engine.get_position() > 3000:
            self.seek(0)
            return self._queue[self._current_index]
        
        if self._current_index > 0:
            self._current_index -= 1
        elif self._play_mode == PlayMode.REPEAT_ALL:
            self._current_index = len(self._queue) - 1
        
        self.play()
        return self._queue[self._current_index]
    
    def seek(self, position_ms: int) -> None:
        """Seek to specified position"""
        self._engine.seek(position_ms)
        self._event_bus.publish(EventType.POSITION_CHANGED, position_ms)
    
    def set_volume(self, volume: float) -> None:
        """Set volume"""
        self._engine.set_volume(volume)
        self._event_bus.publish(EventType.VOLUME_CHANGED, volume)
    
    def set_play_mode(self, mode: PlayMode) -> None:
        """Set playback mode"""
        self._play_mode = mode
        if mode == PlayMode.SHUFFLE:
            self._shuffle_indices = list(range(len(self._queue)))
            random.shuffle(self._shuffle_indices)
    
    def _on_track_end(self) -> None:
        """Track playback ended callback"""
        self._event_bus.publish(EventType.TRACK_ENDED)
        
        if self._play_mode == PlayMode.REPEAT_ONE:
            self.play()
        else:
            self.next_track()
    
    def _on_error(self, error: str) -> None:
        """Error callback"""
        self._event_bus.publish(EventType.ERROR_OCCURRED, {
            "source": "PlayerService",
            "error": error
        })
```

---

## 3. Data Model Design

### 3.1 Track Model

```python
# src/models/track.py

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid

# Assuming PyQt6 is used for GUI, pyqtSignal would be imported from it
# from PyQt6.QtCore import pyqtSignal 

@dataclass
class Track:
    """Track data model"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    file_path: str = ""
    duration_ms: int = 0
    bitrate: int = 0
    sample_rate: int = 0
    format: str = ""
    
    artist_id: Optional[str] = None
    artist_name: str = ""
    album_id: Optional[str] = None
    album_name: str = ""
    
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    genre: str = ""
    year: Optional[int] = None
    
    play_count: int = 0
    last_played: Optional[datetime] = None
    rating: int = 0
    is_favorite: bool = False
    
    cover_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_str(self) -> str:
        """Format duration string"""
        total_seconds = self.duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    @property
    def display_name(self) -> str:
        """Display name"""
        if self.artist_name:
            return f"{self.artist_name} - {self.title}"
        return self.title
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'file_path': self.file_path,
            'duration_ms': self.duration_ms,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'format': self.format,
            'artist_id': self.artist_id,
            'artist_name': self.artist_name,
            'album_id': self.album_id,
            'album_name': self.album_name,
            'track_number': self.track_number,
            'genre': self.genre,
            'year': self.year,
            'play_count': self.play_count,
            'rating': self.rating
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Track':
        """Create from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            file_path=data.get('file_path', ''),
            duration_ms=data.get('duration_ms', 0),
            bitrate=data.get('bitrate', 0),
            sample_rate=data.get('sample_rate', 0),
            format=data.get('format', ''),
            artist_id=data.get('artist_id'),
            artist_name=data.get('artist_name', ''),
            album_id=data.get('album_id'),
            album_name=data.get('album_name', ''),
            track_number=data.get('track_number'),
            genre=data.get('genre', ''),
            year=data.get('year'),
            play_count=data.get('play_count', 0),
            rating=data.get('rating', 0)
        )
```

---

## 4. UI Design Specification

### 4.1 Main Window Layout

```text
+----------------------------------------------------------+
|  [Logo]  Search Bar                    [Min][Max][Close] |
+----------+-----------------------------------------------+
|          |                                               |
| Sidebar  |                   Main Content Area           |
|          |                                               |
| - Browse |   Display content based on selection:         |
| - Recent |   - Music library browsing                    |
| - Playlist|   - Album details                             |
| - Settings|   - Search results                            |
|          |   - Settings page                             |
|          |                                               |
+----------+-----------------------------------------------+
|                                                          |
|  [Cover] Track Info [Prev][Play/Pause][Next] Progress Vol Mode |
|                                                          |
+----------------------------------------------------------+
```

### 4.2 Color Scheme

#### Dark Theme

| Element | Color |
|------|------|
| Primary Background | #121212 |
| Secondary Background | #1E1E1E |
| Surface Color | #282828 |
| Primary Accent | #1DB954 |
| Primary Text | #FFFFFF |
| Secondary Text | #B3B3B3 |
| Border Color | #333333 |

#### Light Theme

| Element | Color |
|------|------|
| Primary Background | #FFFFFF |
| Secondary Background | #F5F5F5 |
| Surface Color | #EEEEEE |
| Primary Accent | #1DB954 |
| Primary Text | #191414 |
| Secondary Text | #666666 |
| Border Color | #E0E0E0 |

---

## 5. Configuration Management

### 5.1 Default Configuration

```yaml
# config/default_config.yaml

app:
  name: "Python Music Player"
  version: "1.0.0"
  language: "zh_CN"
  theme: "dark"

audio:
  backend: "miniaudio"  # miniaudio, vlc, pygame
  output_device: "default"
  buffer_size: 2048
  gapless: true
  crossfade:
    enabled: true
    duration_ms: 500
  replay_gain:
    enabled: true
    mode: "track"
    preamp_db: 0.0
    prevent_clipping: true
  equalizer:
    enabled: false
    preset: "flat"
  
playback:
  default_volume: 0.8
  remember_position: true
  
library:
  directories: []
  watch_for_changes: true
  scan_on_startup: true
  supported_formats:
    - mp3
    - flac
    - wav
    - ogg
    - m4a
    - aac
    
ui:
  window_width: 1200
  window_height: 800
  sidebar_width: 240
  show_album_art: true
  
shortcuts:
  play_pause: "Space"
  next_track: "Ctrl+Right"
  previous_track: "Ctrl+Left"
  volume_up: "Ctrl+Up"
  volume_down: "Ctrl+Down"
  mute: "M"
```

---

## 6. Dependency List

```text
# requirements.txt

# requirements.txt

# GUI Framework
PyQt6>=6.4.0

# Audio Playback
pygame>=2.5.0
miniaudio>=1.59       # High-fidelity audio backend (Gapless/Crossfade/EQ)
python-vlc>=3.0.18122 # VLC backend

# Metadata Parsing
mutagen>=1.46.0

# Configuration Management
PyYAML>=6.0

# Database
# SQLite3 (Built-in)

# Utilities
Pillow>=10.0.0  # Image processing

# Development Dependencies
pytest>=7.0.0
pytest-qt>=4.2.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
```

---

## 7. Testing Strategy

### 7.1 Unit Testing Example

```python
# tests/test_audio_engine.py

import pytest
from unittest.mock import Mock, patch
from src.core.audio_engine import PygameAudioEngine, PlayerState

class TestPygameAudioEngine:
    
    @pytest.fixture
    def engine(self):
        with patch('pygame.mixer.init'):
            engine = PygameAudioEngine()
            return engine
    
    def test_initial_state(self, engine):
        assert engine.state == PlayerState.IDLE
        assert engine.volume == 1.0
    
    def test_load_success(self, engine):
        with patch('pygame.mixer.music.load'):
            result = engine.load("test.mp3")
            assert result == True
            assert engine.state == PlayerState.STOPPED
    
    def test_set_volume(self, engine):
        with patch('pygame.mixer.music.set_volume'):
            engine.set_volume(0.5)
            assert engine.volume == 0.5
    
    def test_volume_bounds(self, engine):
        with patch('pygame.mixer.music.set_volume'):
            engine.set_volume(-0.5)
            assert engine.volume == 0.0
            
            engine.set_volume(1.5)
            assert engine.volume == 1.0
```

### 7.2 Integration Testing

```python
# tests/test_player_service.py

import pytest
from unittest.mock import Mock, MagicMock
from src.services.player_service import PlayerService, PlayMode
from src.models.track import Track

class TestPlayerService:
    
    @pytest.fixture
    def mock_engine(self):
        engine = MagicMock()
        engine.state = Mock()
        return engine
    
    @pytest.fixture
    def player(self, mock_engine):
        return PlayerService(audio_engine=mock_engine)
    
    def test_set_queue(self, player):
        tracks = [Track(title=f"Track {i}") for i in range(5)]
        player.set_queue(tracks)
        assert len(player._queue) == 5
    
    def test_play_mode_shuffle(self, player):
        tracks = [Track(title=f"Track {i}") for i in range(10)]
        player.set_queue(tracks)
        player.set_play_mode(PlayMode.SHUFFLE)
        
        # Verify shuffle_indices are generated
        assert len(player._shuffle_indices) == 10
```

---

## 8. Performance Optimization Guide

### 8.1 Memory Optimization

- Use weak references for cover art cache management
- Lazy load metadata
- Paginated loading for large playlists

### 8.2 Responsiveness Optimization

- Offload time-consuming operations to background threads
- Use event queue to avoid UI blocking
- Incremental media library updates

### 8.3 Startup Optimization

- Lazy initialization for non-essential modules
- Cache historical states
- Use SQLite prepared statements

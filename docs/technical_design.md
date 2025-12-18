# 高质量音乐播放器 - 技术设计文档

## 1. 核心模块详细设计

### 1.1 音频引擎模块 (AudioEngine)

#### 1.1.1 设计目标

- 支持多种音频格式的解码与播放
- 提供统一的播放控制接口
- **支持高级音频特性**：无缝播放 (Gapless)、淡入淡出 (Crossfade)、ReplayGain、10段均衡器 (EQ)
- **多后端支持**：通过工厂模式支持 Miniaudio (默认/高保真)、VLC (兼容性)、Pygame (基础)

#### 1.1.2 类设计

```python
# src/core/audio_engine.py

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from enum import Enum

class AudioEngineBase(ABC):
    """音频引擎基类"""
    
    # ... (原有基础播放控制方法: play, pause, stop, seek, etc.)
    
    # ===== 高级特性接口 =====
    
    @abstractmethod
    def supports_gapless(self) -> bool:
        """是否支持无缝播放"""
        return False

    @abstractmethod
    def supports_crossfade(self) -> bool:
        """是否支持淡入淡出"""
        return False

    @abstractmethod
    def supports_equalizer(self) -> bool:
        """是否支持EQ"""
        return False

    @abstractmethod
    def supports_replay_gain(self) -> bool:
        """是否支持ReplayGain"""
        return False

    @abstractmethod
    def set_next_track(self, file_path: str) -> bool:
        """预加载下一曲 (用于Gapless)"""
        return False

    @abstractmethod
    def set_crossfade_duration(self, duration_ms: int) -> None:
        """设置淡入淡出时长"""
        pass

    @abstractmethod
    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """设置ReplayGain"""
        pass

    @abstractmethod
    def set_equalizer(self, bands: List[float]) -> None:
        """设置10段EQ增益"""
        pass

# src/core/engine_factory.py

class AudioEngineFactory:
    """音频引擎工厂"""
    
    PRIORITY_ORDER = ["miniaudio", "vlc", "pygame"]

    @classmethod
    def create(cls, backend: str = "miniaudio") -> AudioEngineBase:
        """创建引擎实例，支持自动降级"""
        pass

# src/core/miniaudio_engine.py

class MiniaudioEngine(AudioEngineBase):
    """
    基于 miniaudio 的高性能音频引擎
    支持: Gapless, Crossfade, ReplayGain, 10-Band EQ (Biquad Filter)
    """
    pass
```

#### 1.1.3 均衡器模型 (EQPreset)

```python
# src/models/eq_preset.py

class EQPreset(Enum):
    FLAT = "flat"
    ROCK = "rock"
    POP = "pop"
    # ... 其他预设

@dataclass
class EQBands:
    bands: tuple  # 10个频段的dB值
```

---

### 1.2 事件总线模块 (EventBus)

#### 1.2.1 设计目标

- 实现发布-订阅模式
- 支持异步事件处理
- 线程安全

#### 1.2.2 类设计

```python
# src/core/event_bus.py

from typing import Dict, List, Callable, Any, Optional
from enum import Enum
import threading
import uuid
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

class EventType(Enum):
    # 播放事件
    TRACK_LOADED = "track_loaded"
    TRACK_STARTED = "track_started"
    TRACK_ENDED = "track_ended"
    TRACK_PAUSED = "track_paused"
    TRACK_RESUMED = "track_resumed"
    POSITION_CHANGED = "position_changed"
    VOLUME_CHANGED = "volume_changed"
    
    # 播放列表事件
    PLAYLIST_CREATED = "playlist_created"
    PLAYLIST_UPDATED = "playlist_updated"
    PLAYLIST_DELETED = "playlist_deleted"
    QUEUE_CHANGED = "queue_changed"
    
    # 媒体库事件
    LIBRARY_SCAN_STARTED = "library_scan_started"
    LIBRARY_SCAN_PROGRESS = "library_scan_progress"
    LIBRARY_SCAN_COMPLETED = "library_scan_completed"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"
    
    # 系统事件
    CONFIG_CHANGED = "config_changed"
    THEME_CHANGED = "theme_changed"
    ERROR_OCCURRED = "error_occurred"

class EventBus:
    """事件总线 - 单例模式"""
    
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
        """订阅事件，返回订阅ID"""
        subscription_id = str(uuid.uuid4())
        
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = {}
            self._subscribers[event_type][subscription_id] = callback
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        with self._lock:
            for event_type in self._subscribers:
                if subscription_id in self._subscribers[event_type]:
                    del self._subscribers[event_type][subscription_id]
                    return True
        return False
    
    def publish(self, event_type: EventType, data: Any = None) -> None:
        """发布事件"""
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())
        
        for callback in callbacks:
            self._executor.submit(self._safe_call, callback, data)
    
    def publish_sync(self, event_type: EventType, data: Any = None) -> None:
        """同步发布事件"""
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, {}).values())
        
        for callback in callbacks:
            self._safe_call(callback, data)
    
    def _safe_call(self, callback: Callable, data: Any) -> None:
        """安全调用回调"""
        try:
            callback(data)
        except Exception as e:
            self.publish(EventType.ERROR_OCCURRED, {
                "source": "EventBus",
                "error": str(e)
            })
    
    def shutdown(self) -> None:
        """关闭事件总线"""
        self._executor.shutdown(wait=True)
```

---

### 1.3 元数据解析模块 (Metadata)

#### 1.3.1 设计目标

- 解析多种音频格式的元数据
- 提取封面图片
- 支持元数据写入

#### 1.3.2 类设计

```python
# src/core/metadata.py

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
import base64

@dataclass
class AudioMetadata:
    """音频元数据"""
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
    """元数据解析器"""
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', 
                         '.aac', '.wma', '.ape', '.opus'}
    
    @classmethod
    def parse(cls, file_path: str) -> Optional[AudioMetadata]:
        """解析音频文件元数据"""
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
            
            # 基本信息
            if audio.info:
                metadata.duration_ms = int(audio.info.length * 1000)
                metadata.bitrate = getattr(audio.info, 'bitrate', 0)
                metadata.sample_rate = getattr(audio.info, 'sample_rate', 0)
                metadata.channels = getattr(audio.info, 'channels', 2)
            
            metadata.format = suffix[1:].upper()
            
            # 根据格式解析标签
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
            
            # 如果没有标题，使用文件名
            if not metadata.title:
                metadata.title = path.stem
            
            return metadata
            
        except Exception as e:
            print(f"解析元数据失败: {file_path}, 错误: {e}")
            return None
    
    @classmethod
    def _parse_mp3(cls, file_path: str, metadata: AudioMetadata) -> None:
        """解析MP3元数据"""
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
                
                # 封面
                for key in tags:
                    if key.startswith('APIC'):
                        apic = tags[key]
                        metadata.cover_data = apic.data
                        metadata.cover_mime = apic.mime
                        
        except Exception as e:
            print(f"解析MP3标签失败: {e}")
    
    @classmethod
    def _parse_flac(cls, audio, metadata: AudioMetadata) -> None:
        """解析FLAC元数据"""
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
        
        # FLAC封面
        if audio.pictures:
            metadata.cover_data = audio.pictures[0].data
            metadata.cover_mime = audio.pictures[0].mime
    
    @classmethod
    def _parse_ogg(cls, audio, metadata: AudioMetadata) -> None:
        """解析OGG元数据"""
        metadata.title = audio.get('title', [''])[0]
        metadata.artist = audio.get('artist', [''])[0]
        metadata.album = audio.get('album', [''])[0]
    
    @classmethod
    def _parse_m4a(cls, audio, metadata: AudioMetadata) -> None:
        """解析M4A/AAC元数据"""
        metadata.title = audio.get('\xa9nam', [''])[0]
        metadata.artist = audio.get('\xa9ART', [''])[0]
        metadata.album = audio.get('\xa9alb', [''])[0]
        
        if 'covr' in audio:
            metadata.cover_data = bytes(audio['covr'][0])
            metadata.cover_mime = 'image/jpeg'
    
    @classmethod
    def _parse_generic(cls, audio, metadata: AudioMetadata) -> None:
        """通用元数据解析"""
        if hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            metadata.title = tags.get('title', [''])[0] if 'title' in tags else ''
            metadata.artist = tags.get('artist', [''])[0] if 'artist' in tags else ''
            metadata.album = tags.get('album', [''])[0] if 'album' in tags else ''
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """获取支持的格式列表"""
        return list(MetadataParser.SUPPORTED_FORMATS)
```

---

### 1.4 数据库管理模块 (Database)

#### 1.4.1 数据库Schema

```sql
-- 艺术家表
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

-- LLM 标签任务表
CREATE TABLE IF NOT EXISTS llm_tagging_jobs (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_tracks INTEGER NOT NULL DEFAULT 0,
    processed_tracks INTEGER NOT NULL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT
);

-- LLM 已打标曲目记录
CREATE TABLE IF NOT EXISTS llm_tagged_tracks (
    track_id TEXT PRIMARY KEY,
    tagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES llm_tagging_jobs(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
CREATE INDEX IF NOT EXISTS idx_tags_source ON tags(source);
CREATE INDEX IF NOT EXISTS idx_llm_tagged_tracks_job ON llm_tagged_tracks(job_id);
CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist_id);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_position ON playlist_tracks(playlist_id, position);
```

#### 1.4.2 类设计

```python
# src/core/database.py

import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
from contextlib import contextmanager
import re # Added for _is_write_sql

class DatabaseManager:
    """数据库管理器 - 单例模式"""
    
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
        """获取线程本地连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self._db_path)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
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
        """执行SQL，支持自动提交、写入锁和重试机制"""
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
        """获取单条记录"""
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        """获取所有记录"""
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def _init_schema(self) -> None:
        """初始化数据库Schema"""
        schema_sql = """
        -- 艺术家表
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
        
        -- 索引
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
        """识别是否为写入操作 (支持 CTE/WITH)"""
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
        """关闭连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection
```

---

### 1.5 LLM 提供商架构 (LLMProvider Framework)

#### 1.5.1 设计目标

- 支持多种 LLM 模型（如 GPT, Gemini, DeepSeek）。
- 统一的输入输出接口。
- 易于扩展新的模型提供商。

#### 1.5.2 类设计

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class LLMProvider(ABC):
    @abstractmethod
    def chat_completions(self, messages: List[Dict]) -> str:
        pass
```

---

### 1.6 标签服务架构 (TagService)

#### 1.6.1 核心职责

- 提供标签的增删改查。
- 管理标签与媒体库曲目的多对多关系。

---

### 1.7 LLM 打标服务架构 (LLMTaggingService)

#### 1.7.1 设计目标

- 自动对媒体库中的曲目进行批量打标。
- 支持断点续传和进度管理。
- 避免重复对同一首曲目进行打标。

#### 1.7.2 类设计

```python
class LLMTaggingService:
    def start_tagging_job(self, track_ids: List[str] = None) -> str:
        """启动打标任务"""
        pass

    def stop_tagging_job(self, job_id: str) -> bool:
        """停止任务"""
        pass
        
    def get_job_status(self, job_id: str) -> TaggingJobStatus:
        """获取任务状态"""
        pass
```

---

## 2. 服务层设计

### 2.1 播放服务 (PlayerService)

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
    """播放服务"""
    
    def __init__(self, audio_engine: Optional[AudioEngineBase] = None):
        self._engine = audio_engine or PygameAudioEngine()
        self._event_bus = EventBus()
        
        self._queue: List[Track] = []
        self._current_index: int = -1
        self._play_mode: PlayMode = PlayMode.SEQUENTIAL
        self._shuffle_indices: List[int] = []
        
        # 绑定引擎回调
        self._engine.set_on_end(self._on_track_end)
        self._engine.set_on_error(self._on_error)
    
    @property
    def state(self) -> PlaybackState:
        """获取当前播放状态"""
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
        """设置播放队列"""
        self._queue = tracks.copy()
        self._current_index = start_index
        self._shuffle_indices = list(range(len(tracks)))
        if self._play_mode == PlayMode.SHUFFLE:
            random.shuffle(self._shuffle_indices)
        self._event_bus.publish(EventType.QUEUE_CHANGED, self._queue)
    
    def play(self, track: Optional[Track] = None) -> bool:
        """播放指定曲目或当前曲目"""
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
        """暂停播放"""
        if self._engine.state == PlayerState.PLAYING:
            self._engine.pause()
            self._event_bus.publish(EventType.TRACK_PAUSED)
    
    def resume(self) -> None:
        """恢复播放"""
        if self._engine.state == PlayerState.PAUSED:
            self._engine.resume()
            self._event_bus.publish(EventType.TRACK_RESUMED)
    
    def toggle_play(self) -> None:
        """切换播放/暂停"""
        if self._engine.state == PlayerState.PLAYING:
            self.pause()
        elif self._engine.state == PlayerState.PAUSED:
            self.resume()
        else:
            self.play()
    
    def stop(self) -> None:
        """停止播放"""
        self._engine.stop()
        self._event_bus.publish(EventType.TRACK_ENDED)
    
    def next_track(self) -> Optional[Track]:
        """下一曲"""
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
        """上一曲"""
        if not self._queue:
            return None
        
        # 如果播放超过3秒，重新播放当前曲目
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
        """跳转到指定位置"""
        self._engine.seek(position_ms)
        self._event_bus.publish(EventType.POSITION_CHANGED, position_ms)
    
    def set_volume(self, volume: float) -> None:
        """设置音量"""
        self._engine.set_volume(volume)
        self._event_bus.publish(EventType.VOLUME_CHANGED, volume)
    
    def set_play_mode(self, mode: PlayMode) -> None:
        """设置播放模式"""
        self._play_mode = mode
        if mode == PlayMode.SHUFFLE:
            self._shuffle_indices = list(range(len(self._queue)))
            random.shuffle(self._shuffle_indices)
    
    def _on_track_end(self) -> None:
        """曲目播放结束回调"""
        self._event_bus.publish(EventType.TRACK_ENDED)
        
        if self._play_mode == PlayMode.REPEAT_ONE:
            self.play()
        else:
            self.next_track()
    
    def _on_error(self, error: str) -> None:
        """错误回调"""
        self._event_bus.publish(EventType.ERROR_OCCURRED, {
            "source": "PlayerService",
            "error": error
        })
```

---

## 3. 数据模型设计

### 3.1 Track模型

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
    """音轨数据模型"""
    
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
    
    cover_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_str(self) -> str:
        """格式化时长字符串"""
        total_seconds = self.duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.artist_name:
            return f"{self.artist_name} - {self.title}"
        return self.title
    
    def to_dict(self) -> dict:
        """转换为字典"""
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
        """从字典创建"""
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

## 4. UI设计规范

### 4.1 主窗口布局

```text
+----------------------------------------------------------+
|  [Logo]  搜索框                        [最小化][最大化][关闭] |
+----------+-----------------------------------------------+
|          |                                               |
| 侧边栏    |                   主内容区                    |
|          |                                               |
| - 发现    |   根据选择显示不同内容:                        |
| - 最近    |   - 音乐库浏览                                |
| - 播放列表 |   - 专辑详情                                  |
| - 设置    |   - 搜索结果                                  |
|          |   - 设置页面                                  |
|          |                                               |
+----------+-----------------------------------------------+
|                                                          |
|  [封面]  歌曲信息   [上一曲][播放][下一曲]  进度条  音量  模式 |
|                                                          |
+----------------------------------------------------------+
```

### 4.2 配色方案

#### 深色主题

| 元素 | 颜色 |
|------|------|
| 背景主色 | #121212 |
| 背景次色 | #1E1E1E |
| 表面色 | #282828 |
| 主强调色 | #1DB954 |
| 文字主色 | #FFFFFF |
| 文字次色 | #B3B3B3 |
| 边框色 | #333333 |

#### 浅色主题

| 元素 | 颜色 |
|------|------|
| 背景主色 | #FFFFFF |
| 背景次色 | #F5F5F5 |
| 表面色 | #EEEEEE |
| 主强调色 | #1DB954 |
| 文字主色 | #191414 |
| 文字次色 | #666666 |
| 边框色 | #E0E0E0 |

---

## 5. 配置管理

### 5.1 默认配置

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

## 6. 依赖列表

```text
# requirements.txt

# GUI框架
PyQt6>=6.4.0

# 音频播放
pygame>=2.5.0
miniaudio>=1.59       # 高保真音频后端 (Gapless/Crossfade/EQ)
python-vlc>=3.0.18122 # VLC后端

# 元数据解析
mutagen>=1.46.0

# 配置管理
PyYAML>=6.0

# 数据库
# SQLite3 (Python内置)

# 工具库
Pillow>=10.0.0  # 图像处理

# 开发依赖
pytest>=7.0.0
pytest-qt>=4.2.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
```

---

## 7. 测试策略

### 7.1 单元测试示例

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

### 7.2 集成测试

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
        
        # 验证shuffle_indices已生成
        assert len(player._shuffle_indices) == 10
```

---

## 8. 性能优化指南

### 8.1 内存优化

- 使用弱引用管理封面图片缓存
- 延迟加载元数据
- 分页加载大型播放列表

### 8.2 响应性优化

- 耗时操作放入后台线程
- 使用事件队列避免UI阻塞
- 增量更新媒体库

### 8.3 启动优化

- 延迟初始化非必要模块
- 缓存历史状态
- 使用SQLite预编译语句

# High-Quality Music Player - API Interface Document

## 1. Overview

This document defines the public interface specifications between various modules of the music player, ensuring low coupling and high cohesion.

---

## 2. Core Interfaces

### 2.1 IAudioEngine - Audio Engine Interface

Core abstract interface for audio playback, supporting multiple backend implementations.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `load(file_path)` | `str` | `bool` | Load audio file |
| `play()` | - | `bool` | Start playback |
| `pause()` | - | `None` | Pause playback |
| `resume()` | - | `None` | Resume playback |
| `stop()` | - | `None` | Stop playback |
| `seek(position_ms)` | `int` | `None` | Seek to specified position |
| `set_volume(volume)` | `float` | `None` | Set volume (0.0-1.0) |
| `get_position()` | - | `int` | Get current position (ms) |
| `get_duration()` | - | `int` | Get total duration (ms) |
| `supports_gapless()` | - | `bool` | Whether gapless playback is supported |
| `supports_crossfade()` | - | `bool` | Whether crossfade is supported |
| `supports_equalizer()` | - | `bool` | Whether EQ is supported |
| `supports_replay_gain()` | - | `bool` | Whether ReplayGain is supported |
| `set_next_track(path)` | `str` | `bool` | Preload next track |
| `set_crossfade_duration(ms)`| `int` | `None` | Set crossfade duration |
| `set_replay_gain(db, peak)`| `float, float`| `None` | Set ReplayGain |
| `set_equalizer(bands)` | `List[float]` | `None` | Set 10-band EQ gain |

**Properties:**

- `state: PlayerState` - Current playback state
- `volume: float` - Current volume

**Callbacks:**

- `set_on_end(callback)` - Set playback end callback
- `set_on_error(callback)` - Set error callback

### 2.1.1 AudioEngineFactory - Audio Engine Factory

Used to create and manage audio engine instances.

| Method (Static) | Parameters | Return Value | Description |
|------|------|--------|------|
| `create(backend)` | `str` | `AudioEngineBase` | Create engine for specified backend |
| `create_best_available()` | - | `AudioEngineBase` | Create best available engine |
| `get_available_backends()`| - | `List[str]` | Get list of available backends |
| `get_backend_info(backend)`| `str` | `dict` | Get backend feature support |

---

### 2.2 IEventBus - Event Bus Interface

Publish-subscribe pattern event system.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `subscribe(event_type, callback)` | `EventType, Callable` | `str` | Subscribe to event, returns subscription ID |
| `unsubscribe(subscription_id)` | `str` | `bool` | Unsubscribe |
| `publish(event_type, data)` | `EventType, Any` | `None` | Publish event asynchronously |
| `publish_sync(event_type, data)` | `EventType, Any` | `None` | Publish event synchronously |

**Event Types (EventType):**

| Event | Data Type | Trigger Timing |
|------|----------|----------|
| `TRACK_STARTED` | `Track` | Track starts playing |
| `TRACK_ENDED` | `None` | Track playback ends |
| `TRACK_PAUSED` | `None` | Playback paused |
| `TRACK_RESUMED` | `None` | Playback resumed |
| `POSITION_CHANGED` | `int` | Playback position changed |
| `VOLUME_CHANGED` | `float` | Volume changed |
| `QUEUE_CHANGED` | `List[Track]` | Playback queue changed |
| `LIBRARY_SCAN_PROGRESS` | `dict` | Scan progress updated |
| `ERROR_OCCURRED` | `dict` | Error occurred |

---

### 2.3 IPlayerService - Player Service Interface

High-level playback control, managing playback queue and playback modes.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `set_queue(tracks, start_index)` | `List[Track], int` | `None` | Set playback queue |
| `play(track)` | `Track?` | `bool` | Play specified or current track |
| `pause()` | - | `None` | Pause |
| `resume()` | - | `None` | Resume |
| `toggle_play()` | - | `None` | Toggle play/pause |
| `stop()` | - | `None` | Stop |
| `next_track()` | - | `Track?` | Next track |
| `previous_track()` | - | `Track?` | Previous track |
| `seek(position_ms)` | `int` | `None` | Seek position |
| `set_volume(volume)` | `float` | `None` | Set volume |
| `set_play_mode(mode)` | `PlayMode` | `None` | Set playback mode |

**Properties:**

- `state: PlaybackState` - Current playback state object

---

### 2.4 IPlaylistService - Playlist Service Interface

CRUD operations for playlists.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `create(name, description)` | `str, str` | `Playlist` | Create playlist |
| `get(playlist_id)` | `str` | `Playlist?` | Get playlist |
| `get_all()` | - | `List[Playlist]` | Get all playlists |
| `update(playlist)` | `Playlist` | `bool` | Update playlist |
| `delete(playlist_id)` | `str` | `bool` | Delete playlist |
| `add_track(playlist_id, track)` | `str, Track` | `bool` | Add track |
| `remove_track(playlist_id, track_id)` | `str, str` | `bool` | Remove track |
| `reorder(playlist_id, track_id, new_position)` | `str, str, int` | `bool` | Reorder tracks |

---

### 2.5 ILibraryService - Media Library Service Interface

Scanning, indexing, and searching for the media library.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `scan(directories)` | `List[str]` | `None` | Scan specified directories |
| `scan_async(directories)` | `List[str]` | `None` | Scan asynchronously |
| `get_all_tracks()` | - | `List[Track]` | Get all tracks |
| `get_track(track_id)` | `str` | `Track?` | Get track |
| `get_albums()` | - | `List[Album]` | Get all albums |
| `get_artists()` | - | `List[Artist]` | Get all artists |
| `search(query)` | `str` | `SearchResult` | Search |
| `get_recent(limit)` | `int` | `List[Track]` | Get recently played |

---

### 2.6 IConfigService - Configuration Service Interface

Configuration management and persistence.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `get(key, default)` | `str, Any` | `Any` | Get configuration value |
| `set(key, value)` | `str, Any` | `None` | Set configuration value |
| `save()` | - | `bool` | Save configuration |
| `reload()` | - | `bool` | Reload configuration |
| `reset()` | - | `None` | Reset to defaults |

---

### 2.7 ILLMQueueService - LLM Queue Management Interface

Intelligent queue management based on natural language instructions.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `suggest_reorder(instruction, queue)` | `str, List[Track]` | `dict` | Get reorder suggestions |
| `apply_reorder_plan(plan)` | `dict` | `bool` | Apply reorder plan |
| `get_reason()` | - | `str` | Get the reason for the last suggestion |

---

### 2.8 ITagService - Tag Service Interface

Manage music tags and their associations with tracks.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `create_tag(name, color, source)` | `str, str, str` | `Tag` | Create new tag |
| `get_all_tags()` | - | `List[Tag]` | Get all tags |
| `get_all_tag_names(source)` | `str?` | `List[str]` | Get list of tag names |
| `delete_tag(tag_id)` | `str` | `bool` | Delete tag |
| `add_tag_to_track(track_id, tag_id)` | `str, str` | `bool` | Add tag to track |
| `batch_add_tags_to_track(track_id, names)` | `str, List[str]` | `int` | Batch add tags |
| `remove_tag_from_track(track_id, tag_id)` | `str, str` | `bool` | Remove tag from track |
| `get_track_tags(track_id)` | `str` | `List[Tag]` | Get all tags for a track |
| `get_tracks_by_tags(names, mode)` | `List[str], str` | `List[str]` | Get track IDs by tags |
| `get_untagged_tracks(source, limit)` | `str, int` | `List[str]` | Get untagged tracks |

---

### 2.10 ILLMTaggingService - Intelligent Tagging Service Interface

Automatically generate tags for media library tracks in batches.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `start_tagging_job(track_ids)` | `List[str]?` | `str` | Start tagging job |
| `stop_tagging_job(job_id)` | `str` | `bool` | Stop job |
| `get_job_status(job_id)` | `str` | `TaggingJobStatus` | Get job status |

> [!IMPORTANT]
> **Cross-thread Safety Notes**
>
> The `start_tagging_job()` method accepts a `progress_callback` parameter, which is called from a background worker thread.
> If UI updates are needed within the callback, you **MUST** use the Qt signal mechanism to safely forward the call to the main thread.
>
> ```python
> # Define signal
> progress_updated = pyqtSignal(int, int)
>
> # Emit signal in callback (thread-safe)
> def progress_callback(current: int, total: int):
>     self.progress_updated.emit(current, total)
>
> # Handle signal in the main thread
> self.progress_updated.connect(self._on_progress_updated)
> ```
>
> Reference implementation: `LLMTaggingProgressDialog` uses this pattern to ensure thread safety.

---

### 2.11 TagQueryParser - Tag Query Parser

Parses natural language instructions into structured tag queries.

| Method | Parameters | Return Value | Description |
|------|------|--------|------|
| `parse(instruction, available_tags)` | `str, List[str]?` | `TagQuery` | Parse query |

---

### 2.12 ILLMProvider - LLM Provider Interface

Unified interface for underlying LLM clients.

| Method/Property | Type | Description |
|------|------|------|
| `name` | `property (str)` | Provider name (e.g., 'gemini') |
| `settings` | `property (LLMSettings)` | Get current configuration |
| `chat_completions(messages)` | `method` | Execute chat completion request |
| `validate_connection()` | `method` | Validate API connectivity |

---

## 📁 Project Structure

```text
src/
├── app/            # Application Bootstrap & DI Container
├── core/           # Low-level logic (AudioEngine, EventBus, Database, LLMProvider)
├── models/         # Data classes (Track, Album, Tag, etc.)
├── services/       # Business logic (PlayerService, LibraryService, TagService)
│   └── llm_providers/ # LLM implementations (Gemini, SiliconFlow)
├── ui/             # PyQt6 Widgets and Windows
└── main.py         # Application Entry Point
docs/               # Detailed documentation (Architecture, API)
tests/              # Unit and Integration tests
```

---

## 3. Data Models

### 3.1 Track - Track Model

```python
@dataclass
class Track:
    id: str              # Unique identifier
    title: str           # Title
    file_path: str       # File path
    duration_ms: int     # Duration (ms)
    bitrate: int         # Bitrate
    sample_rate: int     # Sample rate
    format: str          # Format
    artist_id: str       # Artist ID
    artist_name: str     # Artist name
    album_id: str        # Album ID
    album_name: str      # Album name
    track_number: int    # Track number
    genre: str           # Genre
    year: int            # Year
    play_count: int      # Play count
    rating: int          # Rating (0-5)
    is_favorite: bool    # Whether favorite
```

### 3.2 Album - Album Model

```python
@dataclass
class Album:
    id: str
    title: str
    artist_id: str
    artist_name: str
    year: int
    cover_path: str
    track_count: int
```

### 3.3 Artist - Artist Model

```python
@dataclass
class Artist:
    id: str
    name: str
    image_path: str
    album_count: int
    track_count: int
```

### 3.4 Playlist - Playlist Model

```python
@dataclass
class Playlist:
    id: str
    name: str
    description: str
    cover_path: str
    tracks: List[Track]
    created_at: datetime
    updated_at: datetime

### 3.5 Tag - Tag Model

```python
@dataclass
class Tag:
    id: str
    name: str
    color: str
    source: str          # 'user' | 'llm'
    created_at: datetime

### 3.6 TagQuery - Tag Query Model

```python
@dataclass
class TagQuery:
    tags: List[str]
    match_mode: str      # 'any' | 'all'
    confidence: float
    reason: str
```

### 3.7 PlaybackState - Playback State Model

```python
@dataclass
class PlaybackState:
    current_track: Track
    position_ms: int
    duration_ms: int
    is_playing: bool
    volume: float
    play_mode: PlayMode
```

---

## 4. Enumerations

### 4.1 PlayerState - Player State

| Value | Description |
|----|------|
| `IDLE` | Idle |
| `LOADING` | Loading |
| `PLAYING` | Playing |
| `PAUSED` | Paused |
| `STOPPED` | Stopped |
| `ERROR` | Error |

### 4.2 PlayMode - Play Mode

| Value | Description |
|----|------|
| `SEQUENTIAL` | Sequential |
| `REPEAT_ALL` | Repeat all |
| `REPEAT_ONE` | Repeat one |
| `SHUFFLE` | Shuffle |

---

## 5. Signals/Events Specification

Using PyQt6 signal mechanism for communication between UI components:

```python
# Playback control signals
play_clicked = pyqtSignal()
pause_clicked = pyqtSignal()
next_clicked = pyqtSignal()
previous_clicked = pyqtSignal()
seek_requested = pyqtSignal(int)  # position_ms
volume_changed = pyqtSignal(float)

# Playlist signals
track_selected = pyqtSignal(Track)
track_double_clicked = pyqtSignal(Track)

# Media library signals
album_selected = pyqtSignal(Album)
artist_selected = pyqtSignal(Artist)
search_submitted = pyqtSignal(str)
```

---

## 6. Error Codes

| Code | Name | Description |
|------|------|------|
| `E001` | FILE_NOT_FOUND | File does not exist |
| `E002` | FORMAT_NOT_SUPPORTED | Format not supported |
| `E003` | DECODE_ERROR | Decode error |
| `E004` | PLAYBACK_ERROR | Playback error |
| `E005` | DATABASE_ERROR | Database error |
| `E006` | CONFIG_ERROR | Configuration error |
| `E007` | NETWORK_ERROR | Network error |

---

## 7. Usage Examples

### 7.1 Playing Music

```python
from services.player_service import PlayerService
from services.library_service import LibraryService

# Get service instances
player = PlayerService()
library = LibraryService()

# Get all tracks
tracks = library.get_all_tracks()

# Set playback queue and play
player.set_queue(tracks, start_index=0)
player.play()
```

### 7.2 Subscribing to Events

```python
from core.event_bus import EventBus, EventType

event_bus = EventBus()

def on_track_started(track):
    print(f"Now playing: {track.title}")

# Subscribe to event
subscription_id = event_bus.subscribe(
    EventType.TRACK_STARTED, 
    on_track_started
)

# Unsubscribe
event_bus.unsubscribe(subscription_id)
```

### 7.3 Managing Playlists

```python
from services.playlist_service import PlaylistService

playlist_service = PlaylistService()

# Create playlist
playlist = playlist_service.create("My Favorites", "Songs I like")

# Add track
playlist_service.add_track(playlist.id, track)

# Get all playlists
all_playlists = playlist_service.get_all()
```

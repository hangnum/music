# 高质量音乐播放器 - API接口文档

## 1. 概述

本文档定义了音乐播放器各模块之间的公共接口规范，确保模块间低耦合、高内聚。

---

## 2. 核心接口

### 2.1 IAudioEngine - 音频引擎接口

音频播放的核心抽象接口，支持多后端实现。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `load(file_path)` | `str` | `bool` | 加载音频文件 |
| `play()` | - | `bool` | 开始播放 |
| `pause()` | - | `None` | 暂停播放 |
| `resume()` | - | `None` | 恢复播放 |
| `stop()` | - | `None` | 停止播放 |
| `seek(position_ms)` | `int` | `None` | 跳转到指定位置 |
| `set_volume(volume)` | `float` | `None` | 设置音量(0.0-1.0) |
| `get_position()` | - | `int` | 获取当前位置(毫秒) |
| `get_duration()` | - | `int` | 获取总时长(毫秒) |

**属性:**

- `state: PlayerState` - 当前播放状态
- `volume: float` - 当前音量

**回调:**

- `set_on_end(callback)` - 设置播放结束回调
- `set_on_error(callback)` - 设置错误回调

---

### 2.2 IEventBus - 事件总线接口

发布-订阅模式的事件系统。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `subscribe(event_type, callback)` | `EventType, Callable` | `str` | 订阅事件，返回订阅ID |
| `unsubscribe(subscription_id)` | `str` | `bool` | 取消订阅 |
| `publish(event_type, data)` | `EventType, Any` | `None` | 异步发布事件 |
| `publish_sync(event_type, data)` | `EventType, Any` | `None` | 同步发布事件 |

**事件类型 (EventType):**

| 事件 | 数据类型 | 触发时机 |
|------|----------|----------|
| `TRACK_STARTED` | `Track` | 曲目开始播放 |
| `TRACK_ENDED` | `None` | 曲目播放结束 |
| `TRACK_PAUSED` | `None` | 播放暂停 |
| `TRACK_RESUMED` | `None` | 播放恢复 |
| `POSITION_CHANGED` | `int` | 播放位置改变 |
| `VOLUME_CHANGED` | `float` | 音量改变 |
| `QUEUE_CHANGED` | `List[Track]` | 播放队列改变 |
| `LIBRARY_SCAN_PROGRESS` | `dict` | 扫描进度更新 |
| `ERROR_OCCURRED` | `dict` | 错误发生 |

---

### 2.3 IPlayerService - 播放服务接口

高级播放控制，管理播放队列和播放模式。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `set_queue(tracks, start_index)` | `List[Track], int` | `None` | 设置播放队列 |
| `play(track)` | `Track?` | `bool` | 播放指定或当前曲目 |
| `pause()` | - | `None` | 暂停 |
| `resume()` | - | `None` | 恢复 |
| `toggle_play()` | - | `None` | 切换播放/暂停 |
| `stop()` | - | `None` | 停止 |
| `next_track()` | - | `Track?` | 下一曲 |
| `previous_track()` | - | `Track?` | 上一曲 |
| `seek(position_ms)` | `int` | `None` | 跳转位置 |
| `set_volume(volume)` | `float` | `None` | 设置音量 |
| `set_play_mode(mode)` | `PlayMode` | `None` | 设置播放模式 |

**属性:**

- `state: PlaybackState` - 当前播放状态对象

---

### 2.4 IPlaylistService - 播放列表服务接口

播放列表的CRUD操作。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `create(name, description)` | `str, str` | `Playlist` | 创建播放列表 |
| `get(playlist_id)` | `str` | `Playlist?` | 获取播放列表 |
| `get_all()` | - | `List[Playlist]` | 获取所有播放列表 |
| `update(playlist)` | `Playlist` | `bool` | 更新播放列表 |
| `delete(playlist_id)` | `str` | `bool` | 删除播放列表 |
| `add_track(playlist_id, track)` | `str, Track` | `bool` | 添加曲目 |
| `remove_track(playlist_id, track_id)` | `str, str` | `bool` | 移除曲目 |
| `reorder(playlist_id, track_id, new_position)` | `str, str, int` | `bool` | 调整顺序 |

---

### 2.5 ILibraryService - 媒体库服务接口

媒体库的扫描、索引和搜索。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `scan(directories)` | `List[str]` | `None` | 扫描指定目录 |
| `scan_async(directories)` | `List[str]` | `None` | 异步扫描 |
| `get_all_tracks()` | - | `List[Track]` | 获取所有曲目 |
| `get_track(track_id)` | `str` | `Track?` | 获取曲目 |
| `get_albums()` | - | `List[Album]` | 获取所有专辑 |
| `get_artists()` | - | `List[Artist]` | 获取所有艺术家 |
| `search(query)` | `str` | `SearchResult` | 搜索 |
| `get_recent(limit)` | `int` | `List[Track]` | 获取最近播放 |

---

### 2.6 IConfigService - 配置服务接口

配置管理和持久化。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get(key, default)` | `str, Any` | `Any` | 获取配置值 |
| `set(key, value)` | `str, Any` | `None` | 设置配置值 |
| `save()` | - | `bool` | 保存配置 |
| `reload()` | - | `bool` | 重新加载 |
| `reset()` | - | `None` | 重置为默认 |

---

## 3. 数据模型

### 3.1 Track - 音轨模型

```python
@dataclass
class Track:
    id: str              # 唯一标识
    title: str           # 标题
    file_path: str       # 文件路径
    duration_ms: int     # 时长(毫秒)
    bitrate: int         # 比特率
    sample_rate: int     # 采样率
    format: str          # 格式
    artist_id: str       # 艺术家ID
    artist_name: str     # 艺术家名
    album_id: str        # 专辑ID
    album_name: str      # 专辑名
    track_number: int    # 曲目号
    genre: str           # 流派
    year: int            # 年份
    play_count: int      # 播放次数
    rating: int          # 评分(0-5)
```

### 3.2 Album - 专辑模型

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

### 3.3 Artist - 艺术家模型

```python
@dataclass
class Artist:
    id: str
    name: str
    image_path: str
    album_count: int
    track_count: int
```

### 3.4 Playlist - 播放列表模型

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
```

### 3.5 PlaybackState - 播放状态模型

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

## 4. 枚举类型

### 4.1 PlayerState - 播放器状态

| 值 | 说明 |
|----|------|
| `IDLE` | 空闲 |
| `LOADING` | 加载中 |
| `PLAYING` | 播放中 |
| `PAUSED` | 已暂停 |
| `STOPPED` | 已停止 |
| `ERROR` | 错误 |

### 4.2 PlayMode - 播放模式

| 值 | 说明 |
|----|------|
| `SEQUENTIAL` | 顺序播放 |
| `REPEAT_ALL` | 列表循环 |
| `REPEAT_ONE` | 单曲循环 |
| `SHUFFLE` | 随机播放 |

---

## 5. 信号/事件规范

### 5.1 UI信号

使用 PyQt6 信号机制在UI组件间通信：

```python
# 播放控制信号
play_clicked = pyqtSignal()
pause_clicked = pyqtSignal()
next_clicked = pyqtSignal()
previous_clicked = pyqtSignal()
seek_requested = pyqtSignal(int)  # position_ms
volume_changed = pyqtSignal(float)

# 播放列表信号
track_selected = pyqtSignal(Track)
track_double_clicked = pyqtSignal(Track)

# 媒体库信号
album_selected = pyqtSignal(Album)
artist_selected = pyqtSignal(Artist)
search_submitted = pyqtSignal(str)
```

---

## 6. 错误码

| 代码 | 名称 | 说明 |
|------|------|------|
| `E001` | FILE_NOT_FOUND | 文件不存在 |
| `E002` | FORMAT_NOT_SUPPORTED | 格式不支持 |
| `E003` | DECODE_ERROR | 解码错误 |
| `E004` | PLAYBACK_ERROR | 播放错误 |
| `E005` | DATABASE_ERROR | 数据库错误 |
| `E006` | CONFIG_ERROR | 配置错误 |
| `E007` | NETWORK_ERROR | 网络错误 |

---

## 7. 使用示例

### 7.1 播放音乐

```python
from services.player_service import PlayerService
from services.library_service import LibraryService

# 获取服务实例
player = PlayerService()
library = LibraryService()

# 获取所有曲目
tracks = library.get_all_tracks()

# 设置播放队列并播放
player.set_queue(tracks, start_index=0)
player.play()
```

### 7.2 订阅事件

```python
from core.event_bus import EventBus, EventType

event_bus = EventBus()

def on_track_started(track):
    print(f"正在播放: {track.title}")

# 订阅事件
subscription_id = event_bus.subscribe(
    EventType.TRACK_STARTED, 
    on_track_started
)

# 取消订阅
event_bus.unsubscribe(subscription_id)
```

### 7.3 管理播放列表

```python
from services.playlist_service import PlaylistService

playlist_service = PlaylistService()

# 创建播放列表
playlist = playlist_service.create("我的收藏", "喜欢的歌曲")

# 添加曲目
playlist_service.add_track(playlist.id, track)

# 获取播放列表
all_playlists = playlist_service.get_all()
```

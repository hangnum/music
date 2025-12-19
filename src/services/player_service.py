"""
播放服务模块

管理播放队列、播放状态和播放控制。
"""

from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import random
import logging
import threading

from core.audio_engine import AudioEngineBase, PlayerState, PlaybackEndInfo
from core.event_bus import EventBus, EventType
from models.track import Track

logger = logging.getLogger(__name__)


class PlayMode(Enum):
    """播放模式"""
    SEQUENTIAL = "sequential"      # 顺序播放
    REPEAT_ALL = "repeat_all"      # 列表循环
    REPEAT_ONE = "repeat_one"      # 单曲循环
    SHUFFLE = "shuffle"            # 随机播放


@dataclass
class PlaybackState:
    """播放状态"""
    current_track: Optional[Track] = None
    position_ms: int = 0
    duration_ms: int = 0
    is_playing: bool = False
    volume: float = 1.0
    play_mode: PlayMode = PlayMode.SEQUENTIAL


class PlayerService:
    """
    播放服务
    
    管理音乐播放的核心服务，包括播放队列、播放控制、播放模式等。
    
    使用示例:
        player = PlayerService()
        
        # 设置播放队列
        player.set_queue(tracks)
        
        # 播放
        player.play()
        
        # 下一曲
        player.next_track()
    """
    
    def __init__(self, audio_engine: Optional[AudioEngineBase] = None):
        import warnings
        
        if audio_engine:
            self._engine = audio_engine
        else:
            # 发出废弃警告：内部创建依赖的模式将被移除
            warnings.warn(
                "Creating AudioEngine internally in PlayerService is deprecated. "
                "Use AppContainerFactory.create() to get a properly configured PlayerService instance. "
                "This fallback will be removed in a future version.",
                FutureWarning,
                stacklevel=2
            )
            
            # 使用工厂模式创建引擎
            from core.engine_factory import AudioEngineFactory
            try:
                # 尝试从配置获取后端设置
                from services.config_service import ConfigService
                config = ConfigService()
                backend = config.get("audio.backend", "miniaudio")
            except Exception:
                backend = "miniaudio"
            
            self._engine = AudioEngineFactory.create(backend)
            logger.info("PlayerService 使用音频后端: %s", self._engine.get_engine_name())
        
        self._event_bus = EventBus()
        self._engine.set_on_end(self._on_engine_end)
        self._engine.set_on_error(self._on_error)
        
        # 线程安全锁（保护队列和索引访问）
        self._lock = threading.RLock()
        
        # 播放队列
        self._queue: List[Track] = []
        self._current_index: int = -1
        
        # 播放模式
        self._play_mode: PlayMode = PlayMode.SEQUENTIAL
        self._shuffle_indices: List[int] = []
        self._shuffle_position: int = 0
        
        # 历史记录（用于上一曲）
        self._history: List[int] = []
    
    def check_playback_ended(self) -> bool:
        """Check whether playback has ended."""
        return self._engine.check_if_ended()

    @property
    def state(self) -> PlaybackState:
        """获取当前播放状态"""
        with self._lock:
            current_track = None
            if 0 <= self._current_index < len(self._queue):
                current_track = self._queue[self._current_index]
            
            return PlaybackState(
                current_track=current_track,
                position_ms=self._engine.get_position(),
                duration_ms=self._engine.get_duration(),
                is_playing=self._engine.state == PlayerState.PLAYING,
                volume=self._engine.volume,
                play_mode=self._play_mode
            )
    
    @property
    def current_track(self) -> Optional[Track]:
        """获取当前曲目"""
        with self._lock:
            if 0 <= self._current_index < len(self._queue):
                return self._queue[self._current_index]
            return None
    
    @property
    def queue(self) -> List[Track]:
        """获取播放队列"""
        with self._lock:
            return self._queue.copy()
    
    @property
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._engine.state == PlayerState.PLAYING
    
    def set_queue(self, tracks: List[Track], start_index: int = 0) -> None:
        """
        设置播放队列
        
        Args:
            tracks: 曲目列表
            start_index: 起始索引
        """
        with self._lock:
            self._queue = tracks.copy()
            self._current_index = start_index if tracks else -1
            
            # 重置随机播放索引
            self._shuffle_indices = list(range(len(tracks)))
            if self._play_mode == PlayMode.SHUFFLE:
                random.shuffle(self._shuffle_indices)
                self._shuffle_position = 0
            
            self._history.clear()
        self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
        self._update_next_track_preload()

    def add_to_queue(self, track: Track) -> None:
        """添加曲目到队列末尾"""
        with self._lock:
            self._queue.append(track)
            self._shuffle_indices.append(len(self._queue) - 1)
        self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
        self._update_next_track_preload()

    def insert_next(self, track: Track) -> None:
        """插入曲目到当前曲目之后"""
        with self._lock:
            insert_pos = self._current_index + 1
            self._queue.insert(insert_pos, track)
            
            # 更新shuffle索引
            self._shuffle_indices = list(range(len(self._queue)))
            if self._play_mode == PlayMode.SHUFFLE:
                random.shuffle(self._shuffle_indices)
        
        self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
        
        self._update_next_track_preload()

    def remove_from_queue(self, index: int) -> bool:
        """
        从队列移除曲目
        
        Args:
            index: 队列索引
            
        Returns:
            bool: 是否成功移除
        """
        with self._lock:
            if 0 <= index < len(self._queue):
                self._queue.pop(index)
                
                # 调整当前索引
                if index < self._current_index:
                    self._current_index -= 1
                elif index == self._current_index:
                    if self._current_index >= len(self._queue):
                        self._current_index = len(self._queue) - 1
                
                # 更新shuffle索引
                self._shuffle_indices = list(range(len(self._queue)))
                if self._play_mode == PlayMode.SHUFFLE:
                    random.shuffle(self._shuffle_indices)
                
                self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
                
                self._update_next_track_preload()
                return True
            return False
    
    def clear_queue(self) -> None:
        """清空队列"""
        self.stop()
        with self._lock:
            self._queue.clear()
            self._current_index = -1
            self._shuffle_indices.clear()
            self._history.clear()
        self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
        self._update_next_track_preload()

    def play(self, track: Optional[Track] = None) -> bool:
        """
        播放曲目
        
        Args:
            track: 指定曲目，None则播放当前曲目
            
        Returns:
            bool: 是否成功播放
        """
        if track:
            # P1-4 修复：使用 file_path 作为稳定键判重，而非依赖 dataclass 默认相等性
            existing_index = next(
                (i for i, t in enumerate(self._queue) if t.file_path == track.file_path),
                None
            )
            if existing_index is not None:
                self._current_index = existing_index
            else:
                self._queue.append(track)
                self._current_index = len(self._queue) - 1
                self._shuffle_indices.append(self._current_index)
        
        if self._current_index < 0 or self._current_index >= len(self._queue):
            return False
        
        current = self._queue[self._current_index]
        
        if self._engine.load(current.file_path):
            if self._engine.play():
                # 添加到历史
                self._history.append(self._current_index)
                if len(self._history) > 100:  # 限制历史长度
                    self._history.pop(0)
                
                self._event_bus.publish_sync(EventType.TRACK_STARTED, current)
                self._update_next_track_preload()
                return True
        
        return False
    
    def pause(self) -> None:
        """暂停播放"""
        if self._engine.state == PlayerState.PLAYING:
            self._engine.pause()
            self._event_bus.publish_sync(EventType.TRACK_PAUSED)
    
    def resume(self) -> None:
        """恢复播放"""
        if self._engine.state == PlayerState.PAUSED:
            self._engine.resume()
            self._event_bus.publish_sync(EventType.TRACK_RESUMED)
    
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
        current = self.current_track
        self._engine.stop()
        self._engine.set_next_track(None)
        # P1-5 修复：使用 PLAYBACK_STOPPED 而非 TRACK_ENDED，避免误触发自动切歌逻辑
        self._event_bus.publish_sync(EventType.PLAYBACK_STOPPED, {
            "track": current,
            "reason": "stopped"
        })
    
    def next_track(self) -> Optional[Track]:
        """
        下一曲
        
        Returns:
            Track: 下一首曲目，无下一曲返回None
        """
        if not self._queue:
            return None
        
        next_index = self._get_next_index()
        
        if next_index is not None:
            self._current_index = next_index
            self.play()
            return self._queue[self._current_index]
        
        return None
    
    def previous_track(self) -> Optional[Track]:
        """
        上一曲
        
        Returns:
            Track: 上一首曲目
        """
        if not self._queue:
            return None
        
        # 如果播放超过3秒，重新播放当前曲目
        if self._engine.get_position() > 3000:
            self.seek(0)
            return self.current_track
        
        # 从历史中获取
        if len(self._history) > 1:
            self._history.pop()  # 移除当前
            self._current_index = self._history[-1]
        else:
            # 顺序上一曲
            if self._current_index > 0:
                self._current_index -= 1
            elif self._play_mode == PlayMode.REPEAT_ALL:
                self._current_index = len(self._queue) - 1
        
        self.play()
        return self.current_track
    
    def _get_next_index(self) -> Optional[int]:
        """获取下一曲索引"""
        if not self._queue:
            return None
        
        if self._play_mode == PlayMode.REPEAT_ONE:
            return self._current_index
        
        if self._play_mode == PlayMode.SHUFFLE:
            # 在shuffle列表中找到当前位置的下一个
            try:
                current_shuffle_pos = self._shuffle_indices.index(self._current_index)
                if current_shuffle_pos < len(self._shuffle_indices) - 1:
                    return self._shuffle_indices[current_shuffle_pos + 1]
                else:
                    # Shuffle 到末尾，重新 shuffle 并循环播放
                    random.shuffle(self._shuffle_indices)
                    return self._shuffle_indices[0]
            except ValueError:
                if self._shuffle_indices:
                    return self._shuffle_indices[0]
            return None
        
        # 顺序播放
        if self._current_index < len(self._queue) - 1:
            return self._current_index + 1
        elif self._play_mode == PlayMode.REPEAT_ALL:
            return 0
        
        return None
    
    def _find_track_index_by_file(self, file_path: str) -> Optional[int]:
        """Find queue index by file path."""
        with self._lock:
            for i, track in enumerate(self._queue):
                if track.file_path == file_path:
                    return i
        return None

    def _update_next_track_preload(self) -> None:
        """Preload next track for engines that support gapless/crossfade."""
        if not hasattr(self._engine, "set_next_track"):
            return

        if not self.is_playing:
            self._engine.set_next_track(None)
            return

        with self._lock:
            next_index = self._get_next_index()
            if next_index is None or not (0 <= next_index < len(self._queue)):
                next_path = None
            else:
                next_path = self._queue[next_index].file_path

        self._engine.set_next_track(next_path)

    def seek(self, position_ms: int) -> None:
        """
        跳转到指定位置
        
        Args:
            position_ms: 目标位置（毫秒）
        """
        self._engine.seek(position_ms)
        self._event_bus.publish_sync(EventType.POSITION_CHANGED, {
            "position": position_ms,
            "duration": self._engine.get_duration()
        })
    
    def set_volume(self, volume: float) -> None:
        """
        设置音量
        
        Args:
            volume: 音量值 (0.0 - 1.0)
        """
        self._engine.set_volume(volume)
        self._event_bus.publish_sync(EventType.VOLUME_CHANGED, volume)
    
    def get_volume(self) -> float:
        """获取音量"""
        return self._engine.volume
    
    def set_play_mode(self, mode: PlayMode) -> None:
        """
        设置播放模式
        
        Args:
            mode: 播放模式
        """
        self._play_mode = mode
        
        if mode == PlayMode.SHUFFLE:
            self._shuffle_indices = list(range(len(self._queue)))
            random.shuffle(self._shuffle_indices)
        self._update_next_track_preload()
    
    def get_play_mode(self) -> PlayMode:
        """获取播放模式"""
        return self._play_mode
    
    def cycle_play_mode(self) -> PlayMode:
        """循环切换播放模式"""
        modes = list(PlayMode)
        current_idx = modes.index(self._play_mode)
        next_idx = (current_idx + 1) % len(modes)
        self.set_play_mode(modes[next_idx])
        return self._play_mode
    
    def _on_engine_end(self, info: PlaybackEndInfo) -> None:
        """Handle playback end from the engine."""
        ended_track = self.current_track
        if ended_track:
            self._event_bus.publish_sync(EventType.TRACK_ENDED, {
                "track": ended_track,
                "reason": info.reason,
            })

        if info.next_file:
            next_index = self._find_track_index_by_file(info.next_file)
            if next_index is None:
                logger.warning("Auto-advanced track not found in queue: %s", info.next_file)
                return

            with self._lock:
                self._current_index = next_index
                self._history.append(next_index)
                if len(self._history) > 100:
                    self._history.pop(0)

            self._event_bus.publish_sync(EventType.TRACK_STARTED, self.current_track)
            self._update_next_track_preload()
            return

        # No auto-advance from engine; fall back to PlayerService queue logic.
        self.next_track()

    def _on_error(self, error: str) -> None:
        """错误回调"""
        self._event_bus.publish_sync(EventType.ERROR_OCCURRED, {
            "source": "PlayerService",
            "error": error
        })
    
    def cleanup(self) -> None:
        """清理资源"""
        self.stop()
        if hasattr(self._engine, 'cleanup'):
            self._engine.cleanup()

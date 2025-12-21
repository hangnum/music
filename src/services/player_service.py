"""
Playback Service Module

Manages playback queue, playback state, and playback control.
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
    """Playback mode"""
    SEQUENTIAL = "sequential"      # Sequential playback
    REPEAT_ALL = "repeat_all"      # Repeat list
    REPEAT_ONE = "repeat_one"      # Repeat one
    SHUFFLE = "shuffle"            # Shuffle playback


@dataclass
class PlaybackState:
    """Playback state"""
    current_track: Optional[Track] = None
    position_ms: int = 0
    duration_ms: int = 0
    is_playing: bool = False
    volume: float = 1.0
    play_mode: PlayMode = PlayMode.SEQUENTIAL


class PlayerService:
    """
    Playback Service
    
    The core service for managing music playback, including playback queue, playback control, playback modes, etc.
    
    Example:
        player = PlayerService()
        
        # Set playback queue
        player.set_queue(tracks)
        
        # Play
        player.play()
        
        # Next track
        player.next_track()
    """
    
    def __init__(self, audio_engine: Optional[AudioEngineBase] = None):
        import warnings
        
        if audio_engine:
            self._engine = audio_engine
        else:
            # Deprecation warning: the pattern of creating dependencies internally will be removed.
            warnings.warn(
                "Creating AudioEngine internally in PlayerService is deprecated. "
                "Use AppContainerFactory.create() to get a properly configured PlayerService instance. "
                "This fallback will be removed in a future version.",
                FutureWarning,
                stacklevel=2
            )
            
            # Use factory pattern to create engine
            from core.engine_factory import AudioEngineFactory
            try:
                # Try to get backend settings from configuration
                from services.config_service import ConfigService
                config = ConfigService()
                backend = config.get("audio.backend", "miniaudio")
            except Exception:
                backend = "miniaudio"
            
            self._engine = AudioEngineFactory.create(backend)
            logger.info("PlayerService using audio backend: %s", self._engine.get_engine_name())
        
        self._event_bus = EventBus()
        self._engine.set_on_end(self._on_engine_end)
        self._engine.set_on_error(self._on_error)
        
        # Thread safety lock (protects queue and index access)
        self._lock = threading.RLock()
        
        # Playback queue
        self._queue: List[Track] = []
        self._current_index: int = -1
        
        # Playback mode
        self._play_mode: PlayMode = PlayMode.SEQUENTIAL
        self._shuffle_indices: List[int] = []
        self._shuffle_position: int = 0
        
        # History record (used for previous track)
        self._history: List[int] = []
    
    def check_playback_ended(self) -> bool:
        """Check whether playback has ended."""
        return self._engine.check_if_ended()

    @property
    def state(self) -> PlaybackState:
        """Get current playback state"""
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
        """Get current track"""
        with self._lock:
            if 0 <= self._current_index < len(self._queue):
                return self._queue[self._current_index]
            return None
    
    @property
    def queue(self) -> List[Track]:
        """Get playback queue"""
        with self._lock:
            return self._queue.copy()
    
    @property
    def is_playing(self) -> bool:
        """Whether music is playing"""
        return self._engine.state == PlayerState.PLAYING
    
    def set_queue(self, tracks: List[Track], start_index: int = 0) -> None:
        """
        Set playback queue
        
        Args:
            tracks: List of tracks
            start_index: Starting index
        """
        with self._lock:
            self._queue = tracks.copy()
            self._current_index = start_index if tracks else -1
            
            # Reset shuffle indices
            self._shuffle_indices = list(range(len(tracks)))
            if self._play_mode == PlayMode.SHUFFLE:
                random.shuffle(self._shuffle_indices)
                self._shuffle_position = 0
            
            self._history.clear()
        self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
        self._update_next_track_preload()

    def add_to_queue(self, track: Track) -> None:
        """Add track to end of queue"""
        with self._lock:
            self._queue.append(track)
            self._shuffle_indices.append(len(self._queue) - 1)
        self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
        self._update_next_track_preload()

    def insert_next(self, track: Track) -> None:
        """Insert track after current track"""
        with self._lock:
            insert_pos = self._current_index + 1
            self._queue.insert(insert_pos, track)
            
            # Update shuffle indices
            self._shuffle_indices = list(range(len(self._queue)))
            if self._play_mode == PlayMode.SHUFFLE:
                random.shuffle(self._shuffle_indices)
        
        self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
        
        self._update_next_track_preload()

    def remove_from_queue(self, index: int) -> bool:
        """
        Remove track from queue
        
        Args:
            index: Queue index
            
        Returns:
            bool: Whether removal was successful
        """
        with self._lock:
            if 0 <= index < len(self._queue):
                self._queue.pop(index)
                
                # Adjust current index
                if index < self._current_index:
                    self._current_index -= 1
                elif index == self._current_index:
                    if self._current_index >= len(self._queue):
                        self._current_index = len(self._queue) - 1
                
                # Update shuffle indices
                self._shuffle_indices = list(range(len(self._queue)))
                if self._play_mode == PlayMode.SHUFFLE:
                    random.shuffle(self._shuffle_indices)
                
                self._event_bus.publish_sync(EventType.QUEUE_CHANGED, self._queue)
                
                self._update_next_track_preload()
                return True
            return False
    
    def clear_queue(self) -> None:
        """Clear queue"""
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
        Play track
        
        Args:
            track: Specified track, or None to play current track
            
        Returns:
            bool: Whether playback was successful
        """
        if track:
            # P1-4 fix: use file_path as a stable key for deduplication instead of default dataclass equality
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
        
        # Try loading file, supports VLC fallback
        if self._load_with_fallback(current.file_path):
            if self._engine.play():
                # Add to history
                self._history.append(self._current_index)
                if len(self._history) > 100:  # Limit history length
                    self._history.pop(0)
                
                self._event_bus.publish_sync(EventType.TRACK_STARTED, current)
                self._update_next_track_preload()
                return True
        
        return False

    def _load_with_fallback(self, file_path: str) -> bool:
        """
        Load file with VLC fallback support
        
        When the main engine fails to load (throws UnsupportedFormatError),
        attempt to switch to the VLC engine for playback.
        
        Args:
            file_path: Audio file path
            
        Returns:
            bool: Whether loading was successful
        """
        try:
            # Attempt to load using the current engine
            return self._engine.load(file_path)
        except Exception as e:
            # Check if it is an unsupported format error
            error_type = type(e).__name__
            if error_type == 'UnsupportedFormatError':
                logger.info("Main engine does not support this format, trying VLC fallback: %s", file_path)
                return self._try_vlc_fallback(file_path)
            else:
                logger.error("Failed to load file: %s", e)
                return False

    def _try_vlc_fallback(self, file_path: str) -> bool:
        """
        Attempt to use VLC engine as fallback
        
        Args:
            file_path: Audio file path
            
        Returns:
            bool: Whether successful
        """
        try:
            # Check if VLC is available
            if not AudioEngineFactory.is_available("vlc"):
                logger.warning("VLC engine unavailable, cannot play this format")
                self._event_bus.publish_sync(EventType.ERROR_OCCURRED, {
                    "source": "PlayerService",
                    "error": f"Unsupported audio format, please install FFmpeg or VLC: {file_path}"
                })
                return False
            
            # Save current engine state
            old_engine = self._engine
            old_volume = old_engine.volume
            
            # Create VLC engine
            vlc_engine = AudioEngineFactory.create("vlc")
            vlc_engine.set_volume(old_volume)
            vlc_engine.set_on_end(self._on_engine_end)
            vlc_engine.set_on_error(self._on_error)
            
            # Attempt to load
            if vlc_engine.load(file_path):
                # Switch to VLC engine
                if hasattr(old_engine, 'cleanup'):
                    old_engine.cleanup()
                self._engine = vlc_engine
                logger.info("Switched to VLC engine for playback: %s", file_path)
                return True
            else:
                # VLC also failed
                if hasattr(vlc_engine, 'cleanup'):
                    vlc_engine.cleanup()
                logger.warning("VLC engine also failed to play: %s", file_path)
                return False
                
        except Exception as e:
            logger.error("VLC fallback failed: %s", e)
            return False
    
    def pause(self) -> None:
        """Pause playback"""
        if self._engine.state == PlayerState.PLAYING:
            self._engine.pause()
            self._event_bus.publish_sync(EventType.TRACK_PAUSED)
    
    def resume(self) -> None:
        """Resume playback"""
        if self._engine.state == PlayerState.PAUSED:
            self._engine.resume()
            self._event_bus.publish_sync(EventType.TRACK_RESUMED)
    
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
        current = self.current_track
        self._engine.stop()
        self._engine.set_next_track(None)
        # P1-5 fix: use PLAYBACK_STOPPED instead of TRACK_ENDED to avoid mis-triggering auto-advance logic
        self._event_bus.publish_sync(EventType.PLAYBACK_STOPPED, {
            "track": current,
            "reason": "stopped"
        })
    
    def next_track(self) -> Optional[Track]:
        """
        Next track
        
        Returns:
            Track: The next track, or None if no next track
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
        Previous track
        
        Returns:
            Track: The previous track
        """
        if not self._queue:
            return None
        
        # If playback duration > 3 seconds, replay the current track
        if self._engine.get_position() > 3000:
            self.seek(0)
            return self.current_track
        
        # Get from history
        if len(self._history) > 1:
            self._history.pop()  # Remove current
            self._current_index = self._history[-1]
        else:
            # Sequential previous track
            if self._current_index > 0:
                self._current_index -= 1
            elif self._play_mode == PlayMode.REPEAT_ALL:
                self._current_index = len(self._queue) - 1
        
        self.play()
        return self.current_track
    
    def _get_next_index(self) -> Optional[int]:
        """Get next track index"""
        if not self._queue:
            return None
        
        if self._play_mode == PlayMode.REPEAT_ONE:
            return self._current_index
        
        if self._play_mode == PlayMode.SHUFFLE:
            # Find the next position after the current in the shuffle list
            try:
                current_shuffle_pos = self._shuffle_indices.index(self._current_index)
                if current_shuffle_pos < len(self._shuffle_indices) - 1:
                    return self._shuffle_indices[current_shuffle_pos + 1]
                else:
                    # After reaching end of shuffle, re-shuffle and repeat
                    random.shuffle(self._shuffle_indices)
                    return self._shuffle_indices[0]
            except ValueError:
                if self._shuffle_indices:
                    return self._shuffle_indices[0]
            return None
        
        # Sequential playback
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
        Seek to specified position
        
        Args:
            position_ms: Target position (ms)
        """
        self._engine.seek(position_ms)
        self._event_bus.publish_sync(EventType.POSITION_CHANGED, {
            "position": position_ms,
            "duration": self._engine.get_duration()
        })
    
    def set_volume(self, volume: float) -> None:
        """
        Set volume
        
        Args:
            volume: Volume value (0.0 - 1.0)
        """
        self._engine.set_volume(volume)
        self._event_bus.publish_sync(EventType.VOLUME_CHANGED, volume)
    
    def get_volume(self) -> float:
        """Get volume"""
        return self._engine.volume
    
    def set_play_mode(self, mode: PlayMode) -> None:
        """
        Set playback mode
        
        Args:
            mode: Playback mode
        """
        self._play_mode = mode
        
        if mode == PlayMode.SHUFFLE:
            self._shuffle_indices = list(range(len(self._queue)))
            random.shuffle(self._shuffle_indices)
        self._update_next_track_preload()
    
    def get_play_mode(self) -> PlayMode:
        """Get playback mode"""
        return self._play_mode
    
    def cycle_play_mode(self) -> PlayMode:
        """Cycle through playback modes"""
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
        """Error callback"""
        self._event_bus.publish_sync(EventType.ERROR_OCCURRED, {
            "source": "PlayerService",
            "error": error
        })
    
    def cleanup(self) -> None:
        """Clean up resources"""
        self.stop()
        if hasattr(self._engine, 'cleanup'):
            self._engine.cleanup()

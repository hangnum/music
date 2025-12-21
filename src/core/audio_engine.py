"""
Audio Engine Module - Core for Audio Playback

Provides functions for loading, playing, pausing, and stopping audio files.
Supports multiple backend implementations (defaults to pygame).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, List
from enum import Enum
import threading
import logging

logger = logging.getLogger(__name__)


class PlayerState(Enum):
    """Player Status"""
    IDLE = "idle"           # Idle
    LOADING = "loading"     # Loading
    PLAYING = "playing"     # Playing
    PAUSED = "paused"       # Paused
    STOPPED = "stopped"     # Stopped
    ERROR = "error"         # Error


@dataclass(frozen=True)
class PlaybackEndInfo:
    """Playback end info."""
    ended_file: Optional[str]
    next_file: Optional[str] = None
    reason: str = "ended"


class AudioEngineBase(ABC):
    """
    Abstract Base Class for Audio Engines
    
    Defines the standard interface for audio playback, with concrete implementations provided by subclasses.
    """
    
    def __init__(self):
        self._state: PlayerState = PlayerState.IDLE
        self._volume: float = 1.0
        self._current_file: Optional[str] = None
        self._on_end_callback: Optional[Callable[[PlaybackEndInfo], None]] = None
        self._on_error_callback: Optional[Callable[[str], None]] = None
    

    @staticmethod
    def probe() -> bool:
        """
        Check if engine dependencies are available (without touching playback state)
        
        Subclasses should override this method to only check if necessary dependencies can be imported,
        and should not initialize any global state or playback devices.
        
        Returns:
            bool: True if dependencies are available
        """
        return False

    @property
    def state(self) -> PlayerState:
        """Get the current playback state"""
        return self._state
    
    @property
    def volume(self) -> float:
        """Get the current volume"""
        return self._volume
    
    @property
    def current_file(self) -> Optional[str]:
        """Get the path of the currently loaded file"""
        return self._current_file
    
    @abstractmethod
    def load(self, file_path: str) -> bool:
        """
        Load an audio file
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            bool: True if loading was successful
        """
        pass
    
    @abstractmethod
    def play(self) -> bool:
        """
        Start playback
        
        Returns:
            bool: True if playback started successfully
        """
        pass
    
    @abstractmethod
    def pause(self) -> None:
        """Pause playback"""
        pass
    
    @abstractmethod
    def resume(self) -> None:
        """Resume playback"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop playback"""
        pass
    
    @abstractmethod
    def seek(self, position_ms: int) -> None:
        """
        Seek to a specified position
        
        Args:
            position_ms: Target position in milliseconds
        """
        pass
    
    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """
        Set the volume
        
        Args:
            volume: Volume value (0.0 - 1.0)
        """
        pass
    
    @abstractmethod
    def get_position(self) -> int:
        """
        Get the current playback position
        
        Returns:
            int: Current position in milliseconds
        """
        pass
    
    @abstractmethod
    def get_duration(self) -> int:
        """
        Get the total duration of the audio
        
        Returns:
            int: Total duration in milliseconds
        """
        pass
    
    @abstractmethod
    def check_if_ended(self) -> bool:
        """
        Check if playback has ended (called periodically by the main thread)
        
        Returns:
            bool: True if playback has ended
        """
        pass
    
    def set_on_end(self, callback: Callable[[PlaybackEndInfo], None]) -> None:
        """Set the playback end callback"""
        self._on_end_callback = callback
    
    def set_on_error(self, callback: Callable[[str], None]) -> None:
        """Set the error callback"""
        self._on_error_callback = callback

    # ===== Advanced Audio Features Interface =====

    def supports_gapless(self) -> bool:
        """
        Whether gapless playback is supported

        Returns:
            bool: True if Gapless Playback is supported
        """
        return False

    def supports_crossfade(self) -> bool:
        """
        Whether crossfade is supported

        Returns:
            bool: True if Crossfade is supported
        """
        return False

    def supports_equalizer(self) -> bool:
        """
        Whether an equalizer is supported

        Returns:
            bool: True if EQ is supported
        """
        return False

    def supports_replay_gain(self) -> bool:
        """
        Whether ReplayGain is supported

        Returns:
            bool: True if ReplayGain is supported
        """
        return False

    def set_next_track(self, file_path: Optional[str]) -> bool:
        """
        Preload the next track (for Gapless Playback)

        Subclasses can override this method to implement seamless transitions.

        Args:
            file_path: Path to the next track

        Returns:
            bool: True if preloading was successful
        """
        return False

    def set_crossfade_duration(self, duration_ms: int) -> None:
        """
        Set crossfade duration

        Args:
            duration_ms: Crossfade duration in milliseconds
        """
        pass

    def get_crossfade_duration(self) -> int:
        """
        Get current crossfade duration

        Returns:
            int: Crossfade duration in milliseconds, returns 0 if not supported
        """
        return 0

    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """
        Set ReplayGain gain

        Args:
            gain_db: Gain value (dB), positive to increase volume, negative to decrease
            peak: Peak information, used to prevent clipping
        """
        pass

    def set_equalizer(self, bands: List[float]) -> None:
        """
        Set equalizer band gains

        Args:
            bands: List of 10 band gains (dB), from low to high frequency:
                   [31Hz, 62Hz, 125Hz, 250Hz, 500Hz,
                    1kHz, 2kHz, 4kHz, 8kHz, 16kHz]
        """
        pass

    def set_equalizer_enabled(self, enabled: bool) -> None:
        """
        Enable/disable equalizer

        Args:
            enabled: True to enable, False to disable
        """
        pass

    def get_engine_name(self) -> str:
        """
        Get the engine name

        Returns:
            str: Engine identifier name
        """
        return "base"


class PygameAudioEngine(AudioEngineBase):
    """
    Audio engine implementation based on Pygame
    
    Uses pygame.mixer for audio playback, supporting most common audio formats.
    """
    
    _initialized = False
    _mixer_refcount = 0
    _lock = threading.Lock()
    
    @staticmethod
    def probe() -> bool:
        """Check if pygame dependency is available (without initializing mixer)"""
        try:
            import pygame
            return hasattr(pygame, 'mixer')
        except ImportError:
            return False
    
    def __init__(self):
        super().__init__()
        self._duration_ms: int = 0
        self._playback_started = False
        self._cleaned_up = False
        
        # Initialize pygame mixer
        self._acquire_mixer()
    
    def _acquire_mixer(self) -> None:
        """Initialize global pygame mixer and use reference counting to avoid accidental shutdown."""
        with PygameAudioEngine._lock:
            if not PygameAudioEngine._initialized:
                try:
                    import pygame
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                    PygameAudioEngine._initialized = True
                except Exception as e:
                    logger.error("Pygame initialization failed: %s", e)
                    self._state = PlayerState.ERROR
                    return

            PygameAudioEngine._mixer_refcount += 1
    
    def load(self, file_path: str) -> bool:
        """Load an audio file"""
        try:
            import pygame
            
            # Stop current playback
            if self._state == PlayerState.PLAYING:
                self.stop()
            
            # Load new file
            pygame.mixer.music.load(file_path)
            self._current_file = file_path
            self._state = PlayerState.STOPPED
            self._playback_started = False
            
            # Get duration
            self._duration_ms = self._get_duration_from_file(file_path)
            
            return True
            
        except Exception as e:
            self._state = PlayerState.ERROR
            if self._on_error_callback:
                self._on_error_callback(f"Failed to load file: {e}")
            return False
    
    def _get_duration_from_file(self, file_path: str) -> int:
        """Get duration from file"""
        try:
            from mutagen import File
            audio = File(file_path)
            if audio and audio.info:
                return int(audio.info.length * 1000)
        except Exception:
            pass
        return 0
    
    def play(self) -> bool:
        """Start playback"""
        try:
            import pygame
            
            if self._current_file is None:
                return False
            
            pygame.mixer.music.play()
            self._state = PlayerState.PLAYING
            self._playback_started = True
            return True
            
        except Exception as e:
            self._state = PlayerState.ERROR
            if self._on_error_callback:
                self._on_error_callback(f"Playback failed: {e}")
            return False
    
    def pause(self) -> None:
        """Pause playback"""
        import pygame
        
        if self._state == PlayerState.PLAYING:
            pygame.mixer.music.pause()
            self._state = PlayerState.PAUSED
    
    def resume(self) -> None:
        """Resume playback"""
        import pygame
        
        if self._state == PlayerState.PAUSED:
            pygame.mixer.music.unpause()
            self._state = PlayerState.PLAYING
    
    def stop(self) -> None:
        """Stop playback"""
        import pygame
        
        pygame.mixer.music.stop()
        self._state = PlayerState.STOPPED
        self._playback_started = False
    
    def seek(self, position_ms: int) -> None:
        """Seek to a specified position"""
        import pygame
        
        try:
            # pygame's set_pos accepts seconds
            pygame.mixer.music.set_pos(position_ms / 1000.0)
        except Exception as e:
            logger.warning("Seek failed: %s", e)
    
    def set_volume(self, volume: float) -> None:
        """Set the volume"""
        import pygame
        
        self._volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self._volume)
    
    def get_position(self) -> int:
        """Get the current playback position"""
        import pygame
        
        if self._state in (PlayerState.PLAYING, PlayerState.PAUSED):
            pos = pygame.mixer.music.get_pos()
            return max(0, pos)  # Return non-negative value
        return 0
    
    def get_duration(self) -> int:
        """Get total audio duration"""
        return self._duration_ms
    
    def check_if_ended(self) -> bool:
        """
        Check if playback has ended
        
        Called periodically by the main thread, ensuring thread safety.
        """
        import pygame
        
        if self._playback_started and self._state == PlayerState.PLAYING:
            try:
                busy = pygame.mixer.music.get_busy()
            except Exception as e:
                logger.warning("Pygame mixer not initialized, cannot check playback status: %s", e)
                self._state = PlayerState.ERROR
                self._playback_started = False
                return False

            if not busy:
                self._state = PlayerState.STOPPED
                self._playback_started = False
                if self._on_end_callback:
                    self._on_end_callback(
                        PlaybackEndInfo(
                            ended_file=self._current_file,
                            next_file=None,
                            reason="ended",
                        )
                    )
                return True
        return False
    
    def cleanup(self) -> None:
        """Clean up resources"""
        import pygame

        with PygameAudioEngine._lock:
            if self._cleaned_up:
                return
            self._cleaned_up = True

            if PygameAudioEngine._mixer_refcount > 0:
                PygameAudioEngine._mixer_refcount -= 1

            should_quit = PygameAudioEngine._initialized and PygameAudioEngine._mixer_refcount == 0

        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        if should_quit:
            try:
                pygame.mixer.quit()
            except Exception as e:
                logger.warning("Pygame cleanup failed: %s", e)
            finally:
                with PygameAudioEngine._lock:
                    PygameAudioEngine._initialized = False

    def get_engine_name(self) -> str:
        """Get the engine name"""
        return "pygame"


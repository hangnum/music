"""
VLC Audio Engine Implementation

Audio backend based on the python-vlc library, supporting:
- ReplayGain (Gain adjustment)
- EQ Equalizer (libvlc audio equalizer)
- Crossfade (Gradient mixing between two MediaPlayers)
- Extensive format support
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional, List, Any, TYPE_CHECKING

from core.audio_engine import AudioEngineBase, PlayerState, PlaybackEndInfo

logger = logging.getLogger(__name__)

# Try to import vlc
try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    vlc = None  # type: ignore
    VLC_AVAILABLE = False
    logger.warning("The python-vlc library is not installed; VLCEngine is unavailable.")


class VLCEngine(AudioEngineBase):
    """
    VLC-based Audio Engine

    Features:
    - Extensive format support
    - ReplayGain support (via volume adjustment)
    - EQ Equalizer (libvlc AudioEqualizer)
    - Crossfade (Volume gradient between two MediaPlayers)
    """

    @staticmethod
    def probe() -> bool:
        """Check if python-vlc dependencies are available."""
        return VLC_AVAILABLE

    def __init__(self):
        if not VLC_AVAILABLE:
            raise ImportError("The python-vlc library is not installed.")

        super().__init__()

        # VLC instance
        self._instance: Any = vlc.Instance(
            "--no-video",
            "--audio-filter=scaletempo",
        )
        
        # Main player
        self._player: Any = self._instance.media_player_new()
        self._media: Optional[Any] = None

        # Second player for Crossfade
        self._crossfade_player: Any = self._instance.media_player_new()
        self._crossfade_media: Optional[Any] = None
        self._crossfade_duration_ms: int = 0
        self._crossfade_active: bool = False
        self._crossfade_thread: Optional[threading.Thread] = None
        self._crossfade_stop_event = threading.Event()

        # EQ related
        self._eq_enabled: bool = False
        self._eq_bands: List[float] = [0.0] * 10
        self._equalizer: Optional[Any] = None
        self._crossfade_equalizer: Optional[Any] = None

        # ReplayGain
        self._replay_gain_db: float = 0.0

        # Playback status
        self._duration_ms: int = 0
        self._playback_started: bool = False

        # Next track preloading
        self._next_file: Optional[str] = None
        self._next_media: Optional[Any] = None

        # Event handlers
        self._event_handlers_bound = False
        self._end_event_handler = None
        self._error_event_handler = None


        # Thread lock
        self._lock = threading.Lock()

        # Setup event callbacks
        self._setup_event_callbacks()

    def _setup_event_callbacks(self) -> None:
        """Set VLC event callbacks."""
        if self._event_handlers_bound:
            return

        def on_end_reached(event):
            self._on_playback_finished()

        def on_error(event):
            self._state = PlayerState.ERROR
            if self._on_error_callback:
                self._on_error_callback("VLC playback error")

        self._end_event_handler = on_end_reached
        self._error_event_handler = on_error

        for player in (self._player, self._crossfade_player):
            events = player.event_manager()
            events.event_attach(vlc.EventType.MediaPlayerEndReached, on_end_reached)
            events.event_attach(vlc.EventType.MediaPlayerEncounteredError, on_error)

        self._event_handlers_bound = True

    def _on_playback_finished(self) -> None:
        """Handle playback completion."""
        # If crossfading, let the crossfade thread handle it.
        if self._crossfade_active:
            return
            
        with self._lock:
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

    def load(self, file_path: str) -> bool:
        """Load an audio file."""
        try:
            with self._lock:
                # Stop current playback and crossfade.
                self._stop_crossfade()
                if self._state == PlayerState.PLAYING:
                    self._player.stop()

                # Create media object.
                self._media = self._instance.media_new(file_path)
                self._player.set_media(self._media)

                # Parse media to get duration.
                self._media.parse_with_options(vlc.MediaParseFlag.local, 3000)
                
                # Wait for parsing to complete.
                for _ in range(30):
                    if self._media.get_parsed_status() == vlc.MediaParsedStatus.done:
                        break
                    time.sleep(0.1)

                self._current_file = file_path
                self._duration_ms = self._media.get_duration()
                if self._duration_ms < 0:
                    self._duration_ms = 0
                self._state = PlayerState.STOPPED
                self._playback_started = False

                return True

        except Exception as e:
            self._state = PlayerState.ERROR
            logger.error("Failed to load file: %s", e)
            if self._on_error_callback:
                self._on_error_callback(f"Failed to load file: {e}")
            return False

    def play(self) -> bool:
        """Start playback."""
        try:
            with self._lock:
                if self._media is None:
                    return False

                # Apply EQ
                if self._eq_enabled and self._equalizer:
                    self._player.set_equalizer(self._equalizer)
                else:
                    self._player.set_equalizer(None)

                # Apply volume (including ReplayGain)
                self._apply_volume(self._player)

                result = self._player.play()
                if result == 0:
                    self._state = PlayerState.PLAYING
                    self._playback_started = True
                    
                    # If there's a preloaded next track and crossfade is enabled, start monitoring.
                    if self._next_media and self._crossfade_duration_ms > 0:
                        self._start_crossfade_monitor()
                    
                    return True

            return False

        except Exception as e:
            self._state = PlayerState.ERROR
            logger.error("Playback failed: %s", e)
            if self._on_error_callback:
                self._on_error_callback(f"Playback failed: {e}")
            return False

    def _apply_volume(self, player: Any) -> None:
        """Apply volume settings (including ReplayGain adjustment)."""
        linear_gain = 10 ** (self._replay_gain_db / 20)
        final_volume = int(self._volume * linear_gain * 100)
        final_volume = max(0, min(200, final_volume))
        player.audio_set_volume(final_volume)

    def _start_crossfade_monitor(self) -> None:
        """Start the crossfade monitoring thread."""
        if self._crossfade_thread and self._crossfade_thread.is_alive():
            return
        
        self._crossfade_stop_event.clear()
        self._crossfade_thread = threading.Thread(
            target=self._crossfade_monitor_loop,
            daemon=True
        )
        self._crossfade_thread.start()

    def _crossfade_monitor_loop(self) -> None:
        """Monitor playback position and start crossfade at the appropriate time."""
        while not self._crossfade_stop_event.is_set():
            try:
                if self._state != PlayerState.PLAYING:
                    time.sleep(0.1)
                    continue
                
                current_pos = self._player.get_time()
                duration = self._duration_ms
                
                if current_pos < 0 or duration <= 0:
                    time.sleep(0.1)
                    continue
                
                remaining = duration - current_pos
                
                # When remaining time is less than or equal to crossfade duration, start crossfade.
                if remaining <= self._crossfade_duration_ms and self._next_media:
                    self._execute_crossfade()
                    return  # Exit monitoring after crossfade starts.
                
                time.sleep(0.05)  # 50ms check interval
                
            except Exception as e:
                logger.debug("Crossfade monitoring error: %s", e)
                time.sleep(0.1)

    def _execute_crossfade(self) -> None:
        """Perform the crossfade gradient."""
        if self._crossfade_active or not self._next_media:
            return
        
        self._crossfade_active = True
        logger.debug("Starting crossfade gradient")
        
        try:
            # Set crossfade player
            self._crossfade_player.set_media(self._next_media)
            
            # Apply EQ
            if self._eq_enabled and self._equalizer:
                # Create a new equalizer copy for the crossfade player.
                self._crossfade_equalizer = vlc.AudioEqualizer()
                for i in range(min(10, vlc.libvlc_audio_equalizer_get_band_count())):
                    vlc.libvlc_audio_equalizer_set_amp_at_index(
                        self._crossfade_equalizer, self._eq_bands[i], i
                    )
                self._crossfade_player.set_equalizer(self._crossfade_equalizer)
            
            # Initial volume: Main player 100%, crossfade player 0%
            main_volume = int(self._volume * 100)
            self._player.audio_set_volume(main_volume)
            self._crossfade_player.audio_set_volume(0)
            
            # Start crossfade player
            self._crossfade_player.play()
            
            # Gradient process
            steps = 50  # Number of steps
            step_duration = self._crossfade_duration_ms / steps / 1000.0
            
            for i in range(steps + 1):
                if self._crossfade_stop_event.is_set():
                    break
                
                t = i / steps  # 0.0 -> 1.0
                
                # Equal-power crossfade curve
                import math
                fade_out = math.cos(t * math.pi / 2)  # 1 -> 0
                fade_in = math.sin(t * math.pi / 2)   # 0 -> 1
                
                main_vol = int(main_volume * fade_out)
                cross_vol = int(main_volume * fade_in)
                
                self._player.audio_set_volume(max(0, main_vol))
                self._crossfade_player.audio_set_volume(max(0, cross_vol))
                
                time.sleep(step_duration)
            
            # Crossfade complete, switch players.
            self._finalize_crossfade()
            
        except Exception as e:
            logger.error("Crossfade execution failed: %s", e)
            self._crossfade_active = False

    def _finalize_crossfade(self) -> None:
        """Finalize crossfade and switch to the new track."""
        ended_file = None
        next_file = None

        with self._lock:
            ended_file = self._current_file
            next_file = self._next_file

            # Stop main player.
            self._player.stop()

            # Swap players/media.
            self._player, self._crossfade_player = self._crossfade_player, self._player
            self._media, self._crossfade_media = self._next_media, self._media

            # Update state.
            self._current_file = self._next_file
            self._duration_ms = self._media.get_duration() if self._media else 0

            # Cleanup.
            self._next_media = None
            self._next_file = None
            self._crossfade_active = False

            # Restore volume.
            self._apply_volume(self._player)

            logger.debug("Crossfade complete, switched to new track")

        if self._on_end_callback and next_file:
            self._on_end_callback(
                PlaybackEndInfo(
                    ended_file=ended_file,
                    next_file=next_file,
                    reason="auto_advance",
                )
            )

    def _stop_crossfade(self) -> None:
        """Stop the crossfade process."""
        self._crossfade_stop_event.set()
        self._crossfade_active = False
        if self._crossfade_thread and self._crossfade_thread.is_alive():
            self._crossfade_thread.join(timeout=1.0)
        try:
            self._crossfade_player.stop()
        except Exception:
            pass

    def pause(self) -> None:
        """Pause playback."""
        with self._lock:
            if self._state == PlayerState.PLAYING:
                self._player.pause()
                if self._crossfade_active:
                    self._crossfade_player.pause()
                self._state = PlayerState.PAUSED

    def resume(self) -> None:
        """Resume playback."""
        with self._lock:
            if self._state == PlayerState.PAUSED:
                self._player.pause()  # VLC's pause is a toggle.
                if self._crossfade_active:
                    self._crossfade_player.pause()
                self._state = PlayerState.PLAYING

    def stop(self) -> None:
        """Stop playback."""
        with self._lock:
            self._stop_crossfade()
            self._player.stop()
            self._state = PlayerState.STOPPED
            self._playback_started = False

    def seek(self, position_ms: int) -> None:
        """Seek to a specified position."""
        with self._lock:
            if self._duration_ms > 0:
                self._player.set_time(position_ms)

    def set_volume(self, volume: float) -> None:
        """Set volume."""
        self._volume = max(0.0, min(1.0, volume))
        self._apply_volume(self._player)
        if self._crossfade_active:
            self._apply_volume(self._crossfade_player)

    def get_position(self) -> int:
        """Get current playback position (milliseconds)."""
        pos = self._player.get_time()
        return max(0, pos) if pos >= 0 else 0

    def get_duration(self) -> int:
        """Get total audio duration (milliseconds)."""
        return self._duration_ms

    def check_if_ended(self) -> bool:
        """Check if playback has ended."""
        if self._playback_started:
            state = self._player.get_state()
            if state == vlc.State.Ended:
                return True
        return False

    # ===== Advanced Features Implementation =====

    def supports_gapless(self) -> bool:
        # VLC doesn't support true gapless, but crossfade can mask gaps.
        return False

    def supports_crossfade(self) -> bool:
        return True

    def supports_equalizer(self) -> bool:
        return True

    def supports_replay_gain(self) -> bool:
        return True

    def set_next_track(self, file_path: Optional[str]) -> bool:
        """Preload next track."""
        if not file_path:
            self._stop_crossfade()
            self._next_media = None
            self._next_file = None
            return True

        try:
            self._next_media = self._instance.media_new(file_path)
            self._next_file = file_path

            # If playing and crossfade is enabled, start monitoring.
            if self._state == PlayerState.PLAYING and self._crossfade_duration_ms > 0:
                self._start_crossfade_monitor()

            return True
        except Exception as e:
            logger.warning("Preload next track failed: %s", e)
            return False

    def set_crossfade_duration(self, duration_ms: int) -> None:
        """Set crossfade duration."""
        self._crossfade_duration_ms = max(0, duration_ms)

    def get_crossfade_duration(self) -> int:
        return self._crossfade_duration_ms

    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """Set ReplayGain gain."""
        self._replay_gain_db = gain_db
        if self._state in (PlayerState.PLAYING, PlayerState.PAUSED):
            self._apply_volume(self._player)

    def set_equalizer(self, bands: List[float]) -> None:
        """Set EQ band gains."""
        if len(bands) < 10:
            return

        self._eq_bands = list(bands[:10])

        # Create or update equalizer.
        if self._equalizer is None:
            self._equalizer = vlc.AudioEqualizer()

        # Get the number of bands supported by VLC.
        band_count = vlc.libvlc_audio_equalizer_get_band_count()

        # Set gain for each band.
        for i, gain in enumerate(self._eq_bands):
            if i < band_count:
                vlc.libvlc_audio_equalizer_set_amp_at_index(
                    self._equalizer, gain, i
                )

        # If enabled and playing, apply immediately.
        if self._eq_enabled:
            self._player.set_equalizer(self._equalizer)

    def set_equalizer_enabled(self, enabled: bool) -> None:
        """Enable/disable EQ."""
        self._eq_enabled = enabled

        if enabled and self._equalizer:
            self._player.set_equalizer(self._equalizer)
        else:
            self._player.set_equalizer(None)

    def get_engine_name(self) -> str:
        return "vlc"

    def cleanup(self) -> None:
        """Clean up resources."""
        with self._lock:
            self._stop_crossfade()
            try:
                self._player.stop()
                self._crossfade_player.stop()
                self._player.release()
                self._crossfade_player.release()
                if self._media:
                    self._media.release()
                if self._crossfade_media:
                    self._crossfade_media.release()
                if self._next_media:
                    self._next_media.release()
                self._instance.release()
            except Exception as e:
                logger.warning("VLC cleanup failed: %s", e)

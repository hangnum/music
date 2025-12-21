"""
miniaudio Audio Engine Implementation (Facade Pattern)

High-quality audio backend based on the miniaudio library, supporting:
- Gapless Playback (Data Source Chaining)
- Crossfade (Volume gradient mixing)
- 10-band EQ (Biquad Filter)
- ReplayGain (Gain adjustment)

Refactored to Facade Pattern, coordinating the following sub-modules:
- miniaudio.device_manager: Audio device management
- miniaudio.decoder: Audio file decoding
- miniaudio.stream_processor: Audio stream processing
- miniaudio.playback_controller: Playback control
"""

import logging
import os
import threading
import math
import array
from typing import Any, Optional, List

from core.audio_engine import AudioEngineBase, PlayerState, PlaybackEndInfo

from .miniaudio.device_manager import DeviceManager
from .miniaudio.decoder import AudioDecoder, UnsupportedFormatError
from .miniaudio.stream_processor import create_stream, apply_crossfade
from .miniaudio.playback_controller import (
    on_playback_finished,
    play as playback_play,
    pause as playback_pause,
    resume as playback_resume,
    stop as playback_stop,
    stop_internal,
    seek as playback_seek,
    set_volume as playback_set_volume,
    get_position as playback_get_position,
    get_duration as playback_get_duration,
    check_if_ended as playback_check_if_ended,
    set_next_track as playback_set_next_track,
    set_crossfade_duration as playback_set_crossfade_duration,
    get_crossfade_duration as playback_get_crossfade_duration,
    set_replay_gain as playback_set_replay_gain,
    set_equalizer as playback_set_equalizer,
    set_equalizer_enabled as playback_set_equalizer_enabled,
    cleanup as playback_cleanup,
)

logger = logging.getLogger(__name__)

# Try importing miniaudio (for probe method)
try:
    import miniaudio
    MINIAUDIO_AVAILABLE = True
except ImportError:
    MINIAUDIO_AVAILABLE = False
    logger.warning("miniaudio library not installed, MiniaudioEngine unavailable")

# Try importing FFmpeg transcoder (for probe method)
try:
    from core.ffmpeg_transcoder import FFmpegTranscoder, MINIAUDIO_NATIVE_FORMATS
    FFMPEG_TRANSCODER_AVAILABLE = True
except ImportError:
    FFMPEG_TRANSCODER_AVAILABLE = False
    MINIAUDIO_NATIVE_FORMATS = {'.mp3', '.flac', '.wav', '.ogg'}

# ===== DSP module imports =====
from core.dsp import EqualizerProcessor, EQ_FREQUENCIES


class MiniaudioEngine(AudioEngineBase):
    """
    High-quality audio engine based on miniaudio (Facade Pattern)

    Features:
    - Supports Gapless Playback
    - Supports Crossfade (Real implementation)
    - Supports 10-band EQ (Biquad filter)
    - Supports ReplayGain
    """

    @staticmethod
    def probe(self) -> bool:
        """Detect if miniaudio dependency is available"""

    def __init__(self):
        if not MINIAUDIO_AVAILABLE:
            raise ImportError("miniaudio library not installed")

        super().__init__()

        # Sub-module instances
        self._device_manager = DeviceManager()
        self._decoder = AudioDecoder()
        
        # Playback state
        self._decoded_audio: Optional[miniaudio.DecodedSoundFile] = None
        self._duration_ms: int = 0
        self._position_samples: int = 0
        self._sample_rate: int = 44100
        self._channels: int = 2
        self._playback_started: bool = False
        self._is_crossfading: bool = False

        # Crossfade related
        self._crossfade_duration_ms: int = 0
        self._crossfade_samples: int = 0
        self._crossfade_position: int = 0
        self._outgoing_audio: Optional[miniaudio.DecodedSoundFile] = None
        self._outgoing_position: int = 0

        # EQ processor
        self._eq_processor = EqualizerProcessor(self._sample_rate)

        # ReplayGain
        self._replay_gain_db: float = 0.0
        self._replay_gain_peak: float = 1.0

        # Next track preloading (gapless)
        self._next_file: Optional[str] = None
        self._next_decoded: Optional[miniaudio.DecodedSoundFile] = None
        self._next_crossfade_allowed: bool = True

        # Thread lock
        self._lock = threading.Lock()
        
        # Current file path
        self._current_file: Optional[str] = None

    # ===== Device Management Delegation =====
    
    @property
    def _device(self) -> Any:
        """Get audio device (compatibility)"""
        return self._device_manager.device
    
        """Initialize audio device (compatibility)"""
        # The device manager automatically initializes the device during initialization.
        pass
    
    def _reinit_device_if_needed(self, target_sample_rate: int) -> None:
        """Reconstruct playback device if sample rate changes"""
        self._device_manager.reinit_if_needed(target_sample_rate)
        self._sample_rate = self._device_manager.sample_rate
        self._channels = self._device_manager.channels
        self._eq_processor.set_sample_rate(self._sample_rate)

    # ===== Decoding Delegation =====
    
    def load(self, file_path: str) -> bool:
        """Load audio file"""
        try:
            with self._lock:
                # Stop current playback
                if self._state == PlayerState.PLAYING:
                    self._stop_internal()

                # Use decoder to decode file
                self._decoded_audio = self._decoder.decode_file(file_path)
                self._current_file = file_path
                # Get sample rate of decoded audio
                decoded_sample_rate = self._decoded_audio.sample_rate
                self._channels = self._decoded_audio.nchannels
                
                # Check if device reinitialization is needed
                if decoded_sample_rate != self._device_manager.sample_rate:
                    # Reinitialize device, which updates self._sample_rate and EQ processor
                    self._reinit_device_if_needed(decoded_sample_rate)
                else:
                    # Use decoded audio sample rate
                    self._sample_rate = decoded_sample_rate
                    self._eq_processor.set_sample_rate(self._sample_rate)
                
                # Calculate other states using the current sample rate (synced with device)
                self._duration_ms = int(
                    len(self._decoded_audio.samples)
                    / self._channels
                    / self._sample_rate
                    * 1000
                )
                self._position_samples = 0
                self._crossfade_samples = int(
                    self._crossfade_duration_ms / 1000.0 * self._sample_rate
                )
                
                self._state = PlayerState.STOPPED
                return True
                
        except UnsupportedFormatError:
            # Rethrow to let higher levels handle fallback
            raise
        except Exception as e:
            self._state = PlayerState.ERROR
            logger.error("Failed to load file: %s", e)
            if self._on_error_callback:
                self._on_error_callback(f"Failed to load file: {e}")
            return False
    
    def _decode_native(self, file_path: str) -> Any:
        """Use miniaudio native decoding (compatibility method)"""
        return self._decoder._decode_native(file_path)
    
    def _decode_via_ffmpeg(self, file_path: str) -> Any:
        """Decode via FFmpeg transcoding (compatibility method)"""
        return self._decoder._decode_via_ffmpeg(file_path)

    # ===== Stream Processing Delegation =====
    
    def _create_stream(self) -> Any:
        """Create audio stream generator"""
        return create_stream(self)
    
    def _apply_crossfade(self, *args, **kwargs) -> Any:
        """Apply Crossfade mixing"""
        return apply_crossfade(self, *args, **kwargs)

    # ===== Playback Control Delegation =====
    
    def _on_playback_finished(self) -> Any:
        """Playback finish handling"""
        return on_playback_finished(self)
    
    def play(self) -> bool:
        """Start playback"""
        return playback_play(self)
    
    def pause(self) -> None:
        """Pause playback"""
        playback_pause(self)
    
    def resume(self) -> None:
        """Resume playback"""
        playback_resume(self)
    
    def stop(self) -> None:
        """Stop playback"""
        playback_stop(self)
    
    def _stop_internal(self) -> None:
        """Internal stop method"""
        stop_internal(self)
    
    def seek(self, position_ms: int) -> None:
        """Seek to specified position"""
        playback_seek(self, position_ms)
    
    def set_volume(self, volume: float) -> None:
        """Set volume"""
        playback_set_volume(self, volume)
    
    def get_position(self) -> int:
        """Get current playback position (ms)"""
        return playback_get_position(self)
    
    def get_duration(self) -> int:
        """Get total audio duration (ms)"""
        return playback_get_duration(self)
    
    def check_if_ended(self) -> bool:
        """Check if playback has ended"""
        return playback_check_if_ended(self)
    
    def set_next_track(self, file_path: Optional[str]) -> bool:
        """Preload next track"""
        return playback_set_next_track(
            self, file_path, 
            self._decoder.get_native_formats(),
            self._decoder.is_ffmpeg_available(),
            None  # FFmpegTranscoder will be handled internally
        )
    
    def set_crossfade_duration(self, duration_ms: int) -> None:
        """Set crossfade duration"""
        playback_set_crossfade_duration(self, duration_ms)
    
    def get_crossfade_duration(self) -> int:
        """Get crossfade duration"""
        return playback_get_crossfade_duration(self)
    
    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """Set ReplayGain gain"""
        playback_set_replay_gain(self, gain_db, peak)
    
    def set_equalizer(self, bands: List[float]) -> None:
        """Set EQ band gains"""
        playback_set_equalizer(self, bands)
    
    def set_equalizer_enabled(self, enabled: bool) -> None:
        """Enable/Disable EQ"""
        playback_set_equalizer_enabled(self, enabled)
    
    def cleanup(self) -> None:
        """Clean up resources"""
        playback_cleanup(self)

    # ===== Advanced Features Implementation =====

    def supports_gapless(self) -> bool:
        return True

    def supports_crossfade(self) -> bool:
        return True

    def supports_equalizer(self) -> bool:
        return True

    def supports_replay_gain(self) -> bool:
        return True

    def get_engine_name(self) -> str:
        return "miniaudio"
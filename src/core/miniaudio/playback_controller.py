"""
miniaudio Playback Controller Module

Responsible for playback state control, seeking, volume adjustment, etc.
"""

import logging
import os
import threading
from typing import Any, Optional, Tuple

from core.audio_engine import PlayerState, PlaybackEndInfo
from core.dsp import EqualizerProcessor

logger = logging.getLogger(__name__)


def on_playback_finished(engine: Any) -> Tuple[Optional[str], Optional[str], bool, bool]:
    """
    Handle playback completion.
    
    Args:
        engine: MiniaudioEngine instance
        
    Returns:
        (ended_file, next_file, auto_advanced, stop_device)
    """
    ended_file = None
    next_file = None
    auto_advanced = False
    stop_device = False

    with engine._lock:
        ended_file = engine._current_file
        engine._is_crossfading = False

        can_auto_advance = (
            engine._next_decoded is not None
            and engine._next_crossfade_allowed
            and engine._next_decoded.sample_rate == engine._sample_rate
        )

        if can_auto_advance:
            next_decoded = engine._next_decoded
            next_file = engine._next_file
            had_crossfade = engine._crossfade_duration_ms > 0 and engine._next_crossfade_allowed

            # Clear preloaded state before switching.
            engine._next_decoded = None
            engine._next_file = None
            engine._next_crossfade_allowed = True

            engine._decoded_audio = next_decoded
            engine._current_file = next_file
            engine._sample_rate = engine._decoded_audio.sample_rate
            engine._channels = engine._decoded_audio.nchannels
            engine._duration_ms = int(
                len(engine._decoded_audio.samples)
                / engine._channels
                / engine._sample_rate
                * 1000
            )

            # Align position if crossfade already played part of the next track.
            engine._position_samples = engine._crossfade_samples if had_crossfade else 0

            # Refresh EQ and crossfade values for the new track.
            engine._eq_processor.set_sample_rate(engine._sample_rate)
            engine._eq_processor.reset()
            engine._crossfade_samples = int(
                engine._crossfade_duration_ms / 1000.0 * engine._sample_rate
            )

            engine._state = PlayerState.PLAYING
            engine._playback_started = True
            auto_advanced = True
        else:
            if engine._next_decoded is not None and not can_auto_advance:
                logger.info(
                    "Auto-advance disabled due to sample rate mismatch: %d -> %d",
                    engine._sample_rate,
                    engine._next_decoded.sample_rate,
                )

            # Clear preloaded state since we cannot auto-advance.
            engine._next_decoded = None
            engine._next_file = None
            engine._next_crossfade_allowed = True

            engine._state = PlayerState.STOPPED
            engine._playback_started = False
            stop_device = True

    return ended_file, (next_file if auto_advanced else None), auto_advanced, stop_device


def play(engine: Any) -> bool:
    """Start playback."""
    try:
        with engine._lock:
            if engine._decoded_audio is None:
                return False

            if engine._device is None:
                engine._init_device()
                if engine._device is None:
                    return False

            # Reset EQ filter state
            engine._eq_processor.reset()

            # Create stream generator
            from .stream_processor import create_stream
            stream = create_stream(engine)

            # Start playback
            engine._device.start(stream)
            engine._state = PlayerState.PLAYING
            engine._playback_started = True

            return True

    except Exception as e:
        engine._state = PlayerState.ERROR
        logger.error("Playback failed: %s", e)
        if engine._on_error_callback:
            engine._on_error_callback(f"Playback failed: {e}")
        return False


def pause(engine: Any) -> None:
    """Pause playback."""
    with engine._lock:
        if engine._state == PlayerState.PLAYING and engine._device:
            engine._device.stop()
            engine._state = PlayerState.PAUSED


def resume(engine: Any) -> None:
    """Resume playback."""
    with engine._lock:
        if engine._state == PlayerState.PAUSED:
            if engine._decoded_audio and engine._device:
                from .stream_processor import create_stream
                stream = create_stream(engine)
                engine._device.start(stream)
                engine._state = PlayerState.PLAYING


def stop(engine: Any) -> None:
    """Stop playback."""
    with engine._lock:
        stop_internal(engine)


def stop_internal(engine: Any) -> None:
    """Internal stop method (no lock)."""
    if engine._device:
        try:
            engine._device.stop()
        except Exception:
            pass
    engine._state = PlayerState.STOPPED
    engine._playback_started = False
    engine._position_samples = 0
    engine._is_crossfading = False


def seek(engine: Any, position_ms: int) -> None:
    """Seek to a specified position."""
    with engine._lock:
        if engine._decoded_audio:
            engine._position_samples = int(
                position_ms / 1000.0 * engine._sample_rate
            )
            engine._eq_processor.reset()
            
            if engine._state == PlayerState.PLAYING:
                engine._device.stop()
                from .stream_processor import create_stream
                stream = create_stream(engine)
                engine._device.start(stream)


def set_volume(engine: Any, volume: float) -> None:
    """Set volume."""
    engine._volume = max(0.0, min(1.0, volume))


def get_position(engine: Any) -> int:
    """Get current playback position (milliseconds)."""
    if engine._sample_rate > 0:
        return int(engine._position_samples / engine._sample_rate * 1000)
    return 0


def get_duration(engine: Any) -> int:
    """Get total audio duration (milliseconds)."""
    return engine._duration_ms


def check_if_ended(engine: Any) -> bool:
    """Check if playback has ended."""
    if engine._playback_started and engine._state == PlayerState.PLAYING:
        if engine._decoded_audio:
            total_samples = len(engine._decoded_audio.samples) // engine._channels
            if engine._position_samples >= total_samples:
                return True
    return False


def set_next_track(
    engine: Any,
    file_path: Optional[str],
    MINIAUDIO_NATIVE_FORMATS: set,
    FFMPEG_TRANSCODER_AVAILABLE: bool,
    FFmpegTranscoder: Any
) -> bool:
    """
    Preload next track for gapless/crossfade playback.
    
    Args:
        engine: MiniaudioEngine instance
        file_path: Path to the next track
        MINIAUDIO_NATIVE_FORMATS: Set of natively supported formats
        FFMPEG_TRANSCODER_AVAILABLE: Whether FFmpeg is available
        FFmpegTranscoder: FFmpegTranscoder class
        
    Returns:
        True if preloading was successful.
    """
    if not file_path:
        engine._next_decoded = None
        engine._next_file = None
        engine._next_crossfade_allowed = True
        return True

    try:
        ext = os.path.splitext(file_path)[1].lower()
        is_native = ext in MINIAUDIO_NATIVE_FORMATS
        decoded = None
        
        # Strategy 1: Native decoding
        if is_native:
            try:
                decoded = engine._decode_native(file_path)
            except Exception as e:
                logger.debug("Preload native decoding failed: %s", e)
        
        # Strategy 2: FFmpeg transcoding
        if decoded is None:
            if FFMPEG_TRANSCODER_AVAILABLE and FFmpegTranscoder.is_available():
                try:
                    decoded = engine._decode_via_ffmpeg(file_path)
                    logger.debug("Preload via FFmpeg transcoding: %s", file_path)
                except Exception as e:
                    logger.warning("Preload FFmpeg transcoding failed: %s", e)
        
        if decoded is None:
            logger.warning("Preload failed, format not supported: %s", file_path)
            return False
        engine._next_decoded = decoded
        engine._next_file = file_path

        # Avoid crossfade mixing when sample rates differ.
        engine._next_crossfade_allowed = (
            engine._sample_rate == decoded.sample_rate
        )
        if engine._crossfade_duration_ms > 0 and not engine._next_crossfade_allowed:
            logger.info(
                "Crossfade disabled due to sample rate mismatch: %d -> %d",
                engine._sample_rate,
                decoded.sample_rate,
            )

        logger.debug("Preloaded next track: %s", file_path)
        return True
    except Exception as e:
        logger.warning("Preload next track failed: %s", e)
        return False


def set_crossfade_duration(engine: Any, duration_ms: int) -> None:
    """Set crossfade duration."""
    engine._crossfade_duration_ms = max(0, duration_ms)
    engine._crossfade_samples = int(
        engine._crossfade_duration_ms / 1000.0 * engine._sample_rate
    )


def get_crossfade_duration(engine: Any) -> int:
    return engine._crossfade_duration_ms


def set_replay_gain(engine: Any, gain_db: float, peak: float = 1.0) -> None:
    """Set ReplayGain gain."""
    engine._replay_gain_db = gain_db
    engine._replay_gain_peak = max(0.001, peak)


def set_equalizer(engine: Any, bands: list) -> None:
    """Set EQ band gains."""
    if len(bands) >= 10:
        engine._eq_processor.set_bands(bands[:10])


def set_equalizer_enabled(engine: Any, enabled: bool) -> None:
    """Enable/disable EQ."""
    engine._eq_processor.enabled = enabled


def cleanup(engine: Any) -> None:
    """Clean up resources."""
    with engine._lock:
        stop_internal(engine)
        # Use DeviceManager to close the device.
        if engine._device_manager:
            try:
                engine._device_manager.close()
            except Exception as e:
                logger.warning("miniaudio cleanup failed: %s", e)
        engine._decoded_audio = None
        engine._next_decoded = None
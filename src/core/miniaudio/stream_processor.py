"""
miniaudio Audio Stream Processor Module

Responsible for audio stream generation and crossfade processing.
"""

import array
import math
import logging
from typing import Optional, Generator, Any

from core.audio_engine import PlayerState, PlaybackEndInfo
from core.dsp import EqualizerProcessor

logger = logging.getLogger(__name__)


def create_stream(engine: Any) -> Generator[array.array, int, None]:
    """
    Create an audio stream generator - contains the full audio processing chain.
    
    This is a modularized version of the original _create_stream method.
    
    Args:
        engine: MiniaudioEngine instance
        
    Returns:
        Audio stream generator
    """
    samples = engine._decoded_audio.samples
    channels = engine._channels
    
    # Current position in frames.
    position = engine._position_samples
    total_samples = len(samples)
    total_frames = total_samples // channels
    crossfade_frames = engine._crossfade_samples
    crossfade_start_frame = (
        total_frames - crossfade_frames if crossfade_frames > 0 else total_frames
    )
    
    # EQ processor reference.
    eq_processor = engine._eq_processor
    
    def stream_generator():
        nonlocal position, samples, channels, total_samples, total_frames, crossfade_frames, crossfade_start_frame
        
        framecount = yield
        
        while True:
            while position < total_frames:
                start = position * channels
                requested_frames = framecount or 1024
                end = min(start + requested_frames * channels, total_samples)

                if start >= total_samples:
                    break

                # Raw samples.
                chunk = array.array('f', samples[start:end])
                chunk_frames = len(chunk) // channels

                # Check crossfade window.
                in_crossfade = (crossfade_frames > 0 and 
                               position >= crossfade_start_frame and 
                               engine._next_decoded is not None and 
                               engine._next_crossfade_allowed)

                # 1. EQ (skip during crossfade).
                if eq_processor.enabled and not in_crossfade:
                    chunk = eq_processor.process(chunk)

                # 2. Gain (ReplayGain + volume).
                base_gain = engine._volume * (10 ** (engine._replay_gain_db / 20))
                max_gain = 1.0 / engine._replay_gain_peak if engine._replay_gain_peak > 0 else 1.0
                gain = min(base_gain, max_gain)
                
                if gain != 1.0:
                    for i in range(len(chunk)):
                        chunk[i] *= gain

                # 3. Crossfade mixing.
                if in_crossfade:
                    chunk = apply_crossfade(
                        engine, chunk, position, crossfade_start_frame, 
                        crossfade_frames, channels, gain
                    )

                # Update position.
                position += chunk_frames
                engine._position_samples = position

                framecount = yield chunk

            ended_file, next_file, auto_advanced, stop_device = engine._on_playback_finished()

            if not auto_advanced and stop_device and engine._device:
                try:
                    engine._device.stop()
                except Exception:
                    pass

            if engine._on_end_callback:
                reason = "auto_advance" if auto_advanced else "ended"
                engine._on_end_callback(
                    PlaybackEndInfo(
                        ended_file=ended_file,
                        next_file=next_file,
                        reason=reason,
                    )
                )

            if not auto_advanced:
                return

            samples = engine._decoded_audio.samples
            channels = engine._channels
            position = engine._position_samples
            total_samples = len(samples)
            total_frames = total_samples // channels
            crossfade_frames = engine._crossfade_samples
            crossfade_start_frame = (
                total_frames - crossfade_frames if crossfade_frames > 0 else total_frames
            )

    generator = stream_generator()
    next(generator)
    return generator


def apply_crossfade(
    engine: Any,
    outgoing_chunk: array.array,
    position: int,
    crossfade_start: int,
    crossfade_frames: int,
    channels: int,
    gain: float
) -> array.array:
    """
    Apply crossfade mixing.
    
    Note: EQ is applied globally after mixing to avoid filter state crosstalk between two streams.
    
    Args:
        engine: MiniaudioEngine instance
        outgoing_chunk: Current track's audio chunk (fading out, EQ already applied)
        position: Current playback position (frames)
        crossfade_start: Crossfade start position (frames)
        crossfade_frames: Total crossfade duration (frames)
        channels: Number of channels
        gain: Current gain
        
    Returns:
        Mixed audio chunk
    """
    next_samples = engine._next_decoded.samples
    next_total = len(next_samples)
    chunk_frames = len(outgoing_chunk) // channels
    
    # Calculate position within the crossfade region
    crossfade_pos = position - crossfade_start
    
    # Calculate start position for the next track (from the beginning)
    next_start = crossfade_pos * channels
    next_end = min(next_start + len(outgoing_chunk), next_total)
    
    if next_start >= next_total:
        return outgoing_chunk
    
    # Get samples for the next track (do not apply EQ individually to avoid filter state crosstalk)
    incoming_chunk = array.array('f', next_samples[next_start:next_end])
    
    # Apply gain only to the next track (EQ will be applied globally after mixing)
    if gain != 1.0:
        for i in range(len(incoming_chunk)):
            incoming_chunk[i] *= gain
    
    # Mix two audio chunks
    result = array.array('f', [0.0] * len(outgoing_chunk))
    
    for i in range(len(outgoing_chunk)):
        frame_in_crossfade = crossfade_pos + (i // channels)
        
        # Calculate fade coefficients (using equal-power crossfade)
        if crossfade_frames > 0:
            t = min(1.0, frame_in_crossfade / crossfade_frames)
        else:
            t = 1.0
        
        # Equal-power crossfade: use sin/cos curves
        fade_out = math.cos(t * math.pi / 2)  # 1 -> 0
        fade_in = math.sin(t * math.pi / 2)   # 0 -> 1
        
        outgoing_sample = outgoing_chunk[i]
        incoming_sample = incoming_chunk[i] if i < len(incoming_chunk) else 0.0
        
        result[i] = outgoing_sample * fade_out + incoming_sample * fade_in
    
    # Apply EQ globally after mixing (if enabled)
    # Note: outgoing_chunk was EQ'd in _create_stream, but we re-apply here to ensure consistency.
    # Since two streams are already mixed during crossfade, EQ only needs to be applied once to the result.
    if engine._eq_processor.enabled:
        result = engine._eq_processor.process(result)
    
    return result
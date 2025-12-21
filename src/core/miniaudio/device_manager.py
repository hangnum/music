"""
miniaudio Device Manager Module

Responsible for the life cycle management of audio devices.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import miniaudio
try:
    import miniaudio
    MINIAUDIO_AVAILABLE = True
except ImportError:
    MINIAUDIO_AVAILABLE = False
    logger.warning("miniaudio library not installed")


class DeviceManager:
    """
    miniaudio Device Manager
    
    Manages the initialization, reconstruction, and shutdown of audio devices.
    """
    
    def __init__(self):
        """Initialize the device manager"""
        if not MINIAUDIO_AVAILABLE:
            raise ImportError("miniaudio library not installed")
        
        self._device: Optional[miniaudio.PlaybackDevice] = None
        self._sample_rate: int = 44100
        self._channels: int = 2
        
        self._init_device()
    
    def _init_device(self) -> None:
        """Initialize the audio device"""
        try:
            self._device = miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=2,
                sample_rate=44100,
            )
            logger.info("miniaudio device initialized successfully")
        except Exception as e:
            logger.error("miniaudio device initialization failed: %s", e)
            raise
    
    def reinit_if_needed(self, target_sample_rate: int) -> None:
        """
        Reconstruct the playback device to match the source sample rate if it changes.
        
        Args:
            target_sample_rate: Target sample rate
        """
        if self._sample_rate == target_sample_rate:
            return
        
        if self._device:
            try:
                self._device.close()
            except Exception:
                pass
        
        try:
            self._device = miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=2,
                sample_rate=target_sample_rate,
            )
            self._sample_rate = target_sample_rate
            logger.info("miniaudio device reconstructed, sample rate: %d", target_sample_rate)
        except Exception as e:
            logger.error("miniaudio device reconstruction failed: %s", e)
            raise
    
    def close(self) -> None:
        """Close the audio device"""
        if self._device:
            try:
                self._device.close()
                self._device = None
            except Exception as e:
                logger.warning("Failed to close audio device: %s", e)
    
    @property
    def device(self) -> Optional[miniaudio.PlaybackDevice]:
        """Get the audio device instance"""
        return self._device
    
    @property
    def sample_rate(self) -> int:
        """Get the current sample rate"""
        return self._sample_rate
    
    @property
    def channels(self) -> int:
        """Get the current number of channels"""
        return self._channels
    
    def is_available(self) -> bool:
        """Check if the device is available"""
        return self._device is not None and MINIAUDIO_AVAILABLE
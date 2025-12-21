"""
10-Band EQ Processor

Implements equalizer processing using cascaded Biquad filters.
"""

from __future__ import annotations

import array
from typing import List

from core.dsp.biquad_filter import BiquadFilter


# EQ band center frequencies (Hz)
EQ_FREQUENCIES = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


class EqualizerProcessor:
    """
    10-Band EQ Processor
    
    Implemented using cascaded Biquad filters.
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.enabled = False
        self.filters: List[BiquadFilter] = []
        self._init_filters()
    
    def _init_filters(self) -> None:
        """Initialize filters for 10 bands."""
        self.filters = [
            BiquadFilter(self.sample_rate, freq, 0.0)
            for freq in EQ_FREQUENCIES
        ]
    
    def set_bands(self, bands: List[float]) -> None:
        """Set gains for each band."""
        for i, gain in enumerate(bands[:10]):
            if i < len(self.filters):
                self.filters[i].set_gain(gain)
    
    def set_sample_rate(self, sample_rate: int) -> None:
        """Update sample rate."""
        if self.sample_rate != sample_rate:
            self.sample_rate = sample_rate
            # Recreate filters
            bands = [f.gain_db for f in self.filters]
            self._init_filters()
            self.set_bands(bands)
    
    def process(self, samples: array.array) -> array.array:
        """
        Process audio data.
        
        Args:
            samples: Interleaved stereo samples.
            
        Returns:
            Samples after EQ processing.
        """
        if not self.enabled:
            return samples
        
        # Process each band in cascade.
        result = samples
        for filt in self.filters:
            if filt.gain_db != 0.0:
                result = filt.process_stereo(result)
        
        return result
    
    def reset(self) -> None:
        """Reset all filter states."""
        for filt in self.filters:
            filt.reset()

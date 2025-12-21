"""
DSP (Digital Signal Processing) Module

Provides audio processing related functions:
- BiquadFilter: Biquad filter
- EqualizerProcessor: 10-band EQ processor
"""

from core.dsp.biquad_filter import BiquadFilter
from core.dsp.equalizer import EqualizerProcessor, EQ_FREQUENCIES

__all__ = [
    "BiquadFilter",
    "EqualizerProcessor", 
    "EQ_FREQUENCIES",
]

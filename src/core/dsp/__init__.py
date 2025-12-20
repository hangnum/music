"""
DSP (Digital Signal Processing) 模块

提供音频处理相关功能：
- BiquadFilter: 双二阶滤波器
- EqualizerProcessor: 10 频段 EQ 处理器
"""

from core.dsp.biquad_filter import BiquadFilter
from core.dsp.equalizer import EqualizerProcessor, EQ_FREQUENCIES

__all__ = [
    "BiquadFilter",
    "EqualizerProcessor", 
    "EQ_FREQUENCIES",
]

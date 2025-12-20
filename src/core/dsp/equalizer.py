"""
10 频段 EQ 处理器

使用级联 Biquad 滤波器实现均衡器处理。
"""

from __future__ import annotations

import array
from typing import List

from core.dsp.biquad_filter import BiquadFilter


# EQ 频段中心频率 (Hz)
EQ_FREQUENCIES = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


class EqualizerProcessor:
    """
    10 频段 EQ 处理器
    
    使用级联 Biquad 滤波器实现
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.enabled = False
        self.filters: List[BiquadFilter] = []
        self._init_filters()
    
    def _init_filters(self) -> None:
        """初始化 10 个频段滤波器"""
        self.filters = [
            BiquadFilter(self.sample_rate, freq, 0.0)
            for freq in EQ_FREQUENCIES
        ]
    
    def set_bands(self, bands: List[float]) -> None:
        """设置各频段增益"""
        for i, gain in enumerate(bands[:10]):
            if i < len(self.filters):
                self.filters[i].set_gain(gain)
    
    def set_sample_rate(self, sample_rate: int) -> None:
        """更新采样率"""
        if self.sample_rate != sample_rate:
            self.sample_rate = sample_rate
            # 重新创建滤波器
            bands = [f.gain_db for f in self.filters]
            self._init_filters()
            self.set_bands(bands)
    
    def process(self, samples: array.array) -> array.array:
        """
        处理音频数据
        
        Args:
            samples: 立体声交错采样
            
        Returns:
            EQ 处理后的采样
        """
        if not self.enabled:
            return samples
        
        # 级联处理每个频段
        result = samples
        for filt in self.filters:
            if filt.gain_db != 0.0:
                result = filt.process_stereo(result)
        
        return result
    
    def reset(self) -> None:
        """重置所有滤波器状态"""
        for filt in self.filters:
            filt.reset()

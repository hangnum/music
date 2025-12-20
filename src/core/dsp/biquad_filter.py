"""
Biquad 滤波器实现

用于 EQ 频段处理的双二阶滤波器。
"""

from __future__ import annotations

import array
import math


class BiquadFilter:
    """
    Biquad 滤波器 - 用于 EQ 频段处理
    
    实现峰值/凹陷 EQ (peaking EQ) 滤波器
    """
    
    def __init__(self, sample_rate: int, frequency: float, gain_db: float, q: float = 1.4):
        """
        初始化 Biquad 滤波器
        
        Args:
            sample_rate: 采样率
            frequency: 中心频率 (Hz)
            gain_db: 增益 (dB)
            q: Q 因子，控制带宽
        """
        self.sample_rate = sample_rate
        self.frequency = frequency
        self.gain_db = gain_db
        self.q = q
        
        # 滤波器系数
        self.b0: float = 1.0
        self.b1: float = 0.0
        self.b2: float = 0.0
        self.a1: float = 0.0
        self.a2: float = 0.0
        
        # 滤波器状态 (每声道独立)
        self.x1_l = 0.0
        self.x2_l = 0.0
        self.y1_l = 0.0
        self.y2_l = 0.0
        self.x1_r = 0.0
        self.x2_r = 0.0
        self.y1_r = 0.0
        self.y2_r = 0.0
        
        # 计算滤波器系数
        self._calculate_coefficients()
    
    def _calculate_coefficients(self) -> None:
        """计算 Biquad 滤波器系数"""
        if self.gain_db == 0.0:
            # 无增益时使用直通
            self.b0 = 1.0
            self.b1 = 0.0
            self.b2 = 0.0
            self.a1 = 0.0
            self.a2 = 0.0
            return
        
        A = 10 ** (self.gain_db / 40)  # 使用 40 而非 20 用于 peaking EQ
        omega = 2 * math.pi * self.frequency / self.sample_rate
        sin_omega = math.sin(omega)
        cos_omega = math.cos(omega)
        alpha = sin_omega / (2 * self.q)
        
        # Peaking EQ 系数
        b0 = 1 + alpha * A
        b1 = -2 * cos_omega
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_omega
        a2 = 1 - alpha / A
        
        # 归一化
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0
    
    def set_gain(self, gain_db: float) -> None:
        """更新增益并重新计算系数"""
        if self.gain_db != gain_db:
            self.gain_db = gain_db
            self._calculate_coefficients()
    
    def process_stereo(self, samples: array.array) -> array.array:
        """
        处理立体声采样数据
        
        Args:
            samples: 交错的立体声采样 [L, R, L, R, ...]
            
        Returns:
            处理后的采样数据
        """
        if self.gain_db == 0.0:
            return samples
        
        result = array.array('f', [0.0] * len(samples))
        
        for i in range(0, len(samples), 2):
            # 左声道
            x0_l = samples[i]
            y0_l = (self.b0 * x0_l + self.b1 * self.x1_l + self.b2 * self.x2_l
                    - self.a1 * self.y1_l - self.a2 * self.y2_l)
            self.x2_l = self.x1_l
            self.x1_l = x0_l
            self.y2_l = self.y1_l
            self.y1_l = y0_l
            result[i] = y0_l
            
            # 右声道
            if i + 1 < len(samples):
                x0_r = samples[i + 1]
                y0_r = (self.b0 * x0_r + self.b1 * self.x1_r + self.b2 * self.x2_r
                        - self.a1 * self.y1_r - self.a2 * self.y2_r)
                self.x2_r = self.x1_r
                self.x1_r = x0_r
                self.y2_r = self.y1_r
                self.y1_r = y0_r
                result[i + 1] = y0_r
        
        return result
    
    def reset(self) -> None:
        """重置滤波器状态"""
        self.x1_l = self.x2_l = self.y1_l = self.y2_l = 0.0
        self.x1_r = self.x2_r = self.y1_r = self.y2_r = 0.0

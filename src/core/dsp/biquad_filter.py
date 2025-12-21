"""
Biquad Filter Implementation

A biquad filter for EQ band processing.
"""

from __future__ import annotations

import array
import math


class BiquadFilter:
    """
    Biquad Filter - Used for EQ band processing
    
    Implements a peaking/dipping EQ (peaking EQ) filter.
    """
    
    def __init__(self, sample_rate: int, frequency: float, gain_db: float, q: float = 1.4):
        """
        Initialize Biquad filter
        
        Args:
            sample_rate: Sample rate
            frequency: Center frequency (Hz)
            gain_db: Gain (dB)
            q: Q factor, controls bandwidth
        """
        self.sample_rate = sample_rate
        self.frequency = frequency
        self.gain_db = gain_db
        self.q = q
        
        # Filter coefficients
        self.b0: float = 1.0
        self.b1: float = 0.0
        self.b2: float = 0.0
        self.a1: float = 0.0
        self.a2: float = 0.0
        
        # Filter state (independent for each channel)
        self.x1_l = 0.0
        self.x2_l = 0.0
        self.y1_l = 0.0
        self.y2_l = 0.0
        self.x1_r = 0.0
        self.x2_r = 0.0
        self.y1_r = 0.0
        self.y2_r = 0.0
        
        # Calculate filter coefficients
        self._calculate_coefficients()
    
    def _calculate_coefficients(self) -> None:
        """Calculate Biquad filter coefficients"""
        if self.gain_db == 0.0:
            # Use pass-through when gain is 0
            self.b0 = 1.0
            self.b1 = 0.0
            self.b2 = 0.0
            self.a1 = 0.0
            self.a2 = 0.0
            return
        
        A = 10 ** (self.gain_db / 40)  # Use 40 instead of 20 for peaking EQ
        omega = 2 * math.pi * self.frequency / self.sample_rate
        sin_omega = math.sin(omega)
        cos_omega = math.cos(omega)
        alpha = sin_omega / (2 * self.q)
        
        # Peaking EQ coefficients
        b0 = 1 + alpha * A
        b1 = -2 * cos_omega
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_omega
        a2 = 1 - alpha / A
        
        # Normalization
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0
    
    def set_gain(self, gain_db: float) -> None:
        """Update gain and recalculate coefficients"""
        if self.gain_db != gain_db:
            self.gain_db = gain_db
            self._calculate_coefficients()
    
    def process_stereo(self, samples: array.array) -> array.array:
        """
        Process stereo sample data
        
        Args:
            samples: Interleaved stereo samples [L, R, L, R, ...]
            
        Returns:
            Processed sample data
        """
        if self.gain_db == 0.0:
            return samples
        
        result = array.array('f', [0.0] * len(samples))
        
        for i in range(0, len(samples), 2):
            # Left channel
            x0_l = samples[i]
            y0_l = (self.b0 * x0_l + self.b1 * self.x1_l + self.b2 * self.x2_l
                    - self.a1 * self.y1_l - self.a2 * self.y2_l)
            self.x2_l = self.x1_l
            self.x1_l = x0_l
            self.y2_l = self.y1_l
            self.y1_l = y0_l
            result[i] = y0_l
            
            # Right channel
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
        """Reset filter state"""
        self.x1_l = self.x2_l = self.y1_l = self.y2_l = 0.0
        self.x1_r = self.x2_r = self.y1_r = self.y2_r = 0.0

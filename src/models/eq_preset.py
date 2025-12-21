"""
EQ Preset Module

Provides configuration for 10-band equalizer presets.
"""

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum


class EQPreset(Enum):
    """EQ Preset Type"""
    FLAT = "flat"
    ROCK = "rock"
    POP = "pop"
    JAZZ = "jazz"
    CLASSICAL = "classical"
    ELECTRONIC = "electronic"
    HIP_HOP = "hip_hop"
    ACOUSTIC = "acoustic"
    VOCAL = "vocal"
    BASS_BOOST = "bass_boost"


@dataclass(frozen=True)
class EQBands:
    """
    10-Band EQ Configuration

    Band distribution:
    - 31Hz, 62Hz, 125Hz, 250Hz, 500Hz
    - 1kHz, 2kHz, 4kHz, 8kHz, 16kHz

    Attributes:
        bands: Gain values (dB) for 10 bands, range -12 to +12.
    """
    bands: tuple  # 10-element tuple of floats (dB)

    def to_list(self) -> List[float]:
        """Convert to a list."""
        return list(self.bands)


# 10-band EQ preset definitions
# Bands: [31Hz, 62Hz, 125Hz, 250Hz, 500Hz, 1kHz, 2kHz, 4kHz, 8kHz, 16kHz]
EQ_PRESETS: Dict[EQPreset, EQBands] = {
    # Flat - No adjustment
    EQPreset.FLAT: EQBands((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),

    # Rock - Enhance low and high frequencies
    EQPreset.ROCK: EQBands((5.0, 4.0, 3.0, 1.0, -1.0, 0.0, 2.0, 4.0, 5.0, 5.0)),

    # Pop - Enhance vocals and mid-high frequencies
    EQPreset.POP: EQBands((-2.0, -1.0, 0.0, 2.0, 4.0, 4.0, 3.0, 1.0, 0.0, -1.0)),

    # Jazz - Warm mid-low frequencies, soft highs
    EQPreset.JAZZ: EQBands((3.0, 2.0, 1.0, 2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0)),

    # Classical - Natural balance, slight enhancement of high-frequency details
    EQPreset.CLASSICAL: EQBands((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 2.0, 3.0, 4.0)),

    # Electronic - Strong bass and bright highs
    EQPreset.ELECTRONIC: EQBands((6.0, 5.0, 2.0, 0.0, -2.0, 0.0, 1.0, 3.0, 5.0, 6.0)),

    # Hip Hop - Ultra-strong bass
    EQPreset.HIP_HOP: EQBands((7.0, 6.0, 4.0, 2.0, 1.0, 0.0, 1.0, 2.0, 2.0, 3.0)),

    # Acoustic - Natural, warm
    EQPreset.ACOUSTIC: EQBands((3.0, 2.0, 1.0, 1.0, 2.0, 1.0, 2.0, 3.0, 2.0, 2.0)),

    # Vocal - Emphasize vocals
    EQPreset.VOCAL: EQBands((-3.0, -2.0, 0.0, 3.0, 5.0, 5.0, 4.0, 2.0, 0.0, -2.0)),

    # Bass Boost
    EQPreset.BASS_BOOST: EQBands((8.0, 7.0, 5.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
}


# Band center frequency labels
EQ_BAND_LABELS: tuple = (
    "31Hz", "62Hz", "125Hz", "250Hz", "500Hz",
    "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"
)


def get_preset_bands(preset: EQPreset) -> List[float]:
    """
    Get the band configuration for a preset.

    Args:
        preset: EQ preset type.

    Returns:
        List of gains (dB) for 10 bands.
    """
    return EQ_PRESETS.get(preset, EQ_PRESETS[EQPreset.FLAT]).to_list()


def get_preset_by_name(name: str) -> EQPreset:
    """
    Get preset type by name.

    Args:
        name: Preset name (e.g., "rock", "pop").

    Returns:
        EQPreset type, returns FLAT for invalid names.
    """
    try:
        return EQPreset(name.lower())
    except ValueError:
        return EQPreset.FLAT

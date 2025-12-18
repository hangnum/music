"""
EQ 预设模块

提供 10 频段均衡器预设配置。
"""

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum


class EQPreset(Enum):
    """EQ 预设类型"""
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
    10 频段 EQ 配置

    频段分布:
    - 31Hz, 62Hz, 125Hz, 250Hz, 500Hz
    - 1kHz, 2kHz, 4kHz, 8kHz, 16kHz

    Attributes:
        bands: 10 个频段的增益值 (dB)，范围 -12 到 +12
    """
    bands: tuple  # 10-element tuple of floats (dB)

    def to_list(self) -> List[float]:
        """转换为列表"""
        return list(self.bands)


# 10 频段 EQ 预设定义
# 频段: [31Hz, 62Hz, 125Hz, 250Hz, 500Hz, 1kHz, 2kHz, 4kHz, 8kHz, 16kHz]
EQ_PRESETS: Dict[EQPreset, EQBands] = {
    # 平坦 - 无调整
    EQPreset.FLAT: EQBands((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),

    # 摇滚 - 增强低频和高频
    EQPreset.ROCK: EQBands((5.0, 4.0, 3.0, 1.0, -1.0, 0.0, 2.0, 4.0, 5.0, 5.0)),

    # 流行 - 增强人声和中高频
    EQPreset.POP: EQBands((-2.0, -1.0, 0.0, 2.0, 4.0, 4.0, 3.0, 1.0, 0.0, -1.0)),

    # 爵士 - 温暖的中低频，柔和的高频
    EQPreset.JAZZ: EQBands((3.0, 2.0, 1.0, 2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0)),

    # 古典 - 自然平衡，轻微增强高频细节
    EQPreset.CLASSICAL: EQBands((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 2.0, 3.0, 4.0)),

    # 电子 - 强劲低音和明亮高频
    EQPreset.ELECTRONIC: EQBands((6.0, 5.0, 2.0, 0.0, -2.0, 0.0, 1.0, 3.0, 5.0, 6.0)),

    # 嘻哈 - 超强低音
    EQPreset.HIP_HOP: EQBands((7.0, 6.0, 4.0, 2.0, 1.0, 0.0, 1.0, 2.0, 2.0, 3.0)),

    # 原声 - 自然，温暖
    EQPreset.ACOUSTIC: EQBands((3.0, 2.0, 1.0, 1.0, 2.0, 1.0, 2.0, 3.0, 2.0, 2.0)),

    # 人声增强 - 突出人声
    EQPreset.VOCAL: EQBands((-3.0, -2.0, 0.0, 3.0, 5.0, 5.0, 4.0, 2.0, 0.0, -2.0)),

    # 低音增强
    EQPreset.BASS_BOOST: EQBands((8.0, 7.0, 5.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
}


# 频段中心频率标签
EQ_BAND_LABELS: tuple = (
    "31Hz", "62Hz", "125Hz", "250Hz", "500Hz",
    "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"
)


def get_preset_bands(preset: EQPreset) -> List[float]:
    """
    获取预设的频段配置

    Args:
        preset: EQ 预设类型

    Returns:
        10 个频段的增益列表 (dB)
    """
    return EQ_PRESETS.get(preset, EQ_PRESETS[EQPreset.FLAT]).to_list()


def get_preset_by_name(name: str) -> EQPreset:
    """
    根据名称获取预设类型

    Args:
        name: 预设名称（如 "rock", "pop"）

    Returns:
        EQPreset 类型，无效名称返回 FLAT
    """
    try:
        return EQPreset(name.lower())
    except ValueError:
        return EQPreset.FLAT

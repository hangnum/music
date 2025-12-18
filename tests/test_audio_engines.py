"""
音频引擎单元测试

测试 AudioEngineBase、PygameAudioEngine、工厂模式和 EQ 预设。
"""

import pytest
from unittest.mock import MagicMock, patch

from core.audio_engine import AudioEngineBase, PygameAudioEngine, PlayerState
from core.engine_factory import AudioEngineFactory
from models.eq_preset import (
    EQPreset, EQBands, EQ_PRESETS, EQ_BAND_LABELS,
    get_preset_bands, get_preset_by_name
)


class TestAudioEngineBase:
    """AudioEngineBase 抽象类测试"""
    
    def test_base_supports_default_false(self):
        """基类默认不支持高级特性"""
        # 使用 PygameAudioEngine 作为具体实现测试基类行为
        engine = PygameAudioEngine()
        
        # pygame 后端不支持高级特性
        assert engine.supports_gapless() is False
        assert engine.supports_crossfade() is False
        assert engine.supports_equalizer() is False
        assert engine.supports_replay_gain() is False
    
    def test_base_advanced_methods_no_op(self):
        """基类高级方法默认空实现"""
        engine = PygameAudioEngine()
        
        # 这些方法应该不抛出异常
        assert engine.set_next_track("test.mp3") is False
        engine.set_crossfade_duration(1000)
        assert engine.get_crossfade_duration() == 0
        engine.set_replay_gain(2.0, 0.9)
        engine.set_equalizer([0] * 10)
        engine.set_equalizer_enabled(True)
    
    def test_pygame_engine_name(self):
        """PygameAudioEngine 返回正确名称"""
        engine = PygameAudioEngine()
        assert engine.get_engine_name() == "pygame"


class TestAudioEngineFactory:
    """AudioEngineFactory 工厂测试"""
    
    def test_create_pygame_engine(self):
        """创建 pygame 引擎"""
        engine = AudioEngineFactory.create("pygame")
        assert engine is not None
        assert engine.get_engine_name() == "pygame"
    
    def test_fallback_to_pygame(self):
        """创建不存在的后端时降级到 pygame"""
        engine = AudioEngineFactory.create("nonexistent_backend")
        assert engine is not None
        # 应该降级到可用后端
        assert engine.get_engine_name() in ["pygame", "miniaudio", "vlc"]
    
    def test_get_available_backends(self):
        """获取可用后端列表"""
        backends = AudioEngineFactory.get_available_backends()
        assert isinstance(backends, list)
        # pygame 应该总是可用
        assert "pygame" in backends
    
    def test_is_available(self):
        """检查后端可用性"""
        assert AudioEngineFactory.is_available("pygame") is True
        assert AudioEngineFactory.is_available("nonexistent") is False
    
    def test_get_backend_info(self):
        """获取后端特性信息"""
        info = AudioEngineFactory.get_backend_info("pygame")
        assert isinstance(info, dict)
        assert "gapless" in info
        assert "crossfade" in info
        assert "equalizer" in info
        assert "replay_gain" in info


class TestEQPresets:
    """EQ 预设测试"""
    
    def test_eq_preset_values(self):
        """测试所有预设都有定义"""
        for preset in EQPreset:
            assert preset in EQ_PRESETS
            bands = EQ_PRESETS[preset]
            assert len(bands.bands) == 10
    
    def test_eq_bands_to_list(self):
        """测试 EQBands.to_list()"""
        bands = EQBands((1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0))
        result = bands.to_list()
        assert result == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    def test_flat_preset_is_zero(self):
        """flat 预设所有频段为 0"""
        flat_bands = get_preset_bands(EQPreset.FLAT)
        assert all(b == 0.0 for b in flat_bands)
    
    def test_rock_preset_has_v_shape(self):
        """rock 预设应该是 V 形曲线（低频和高频增强）"""
        rock_bands = get_preset_bands(EQPreset.ROCK)
        # 低频 (31Hz, 62Hz) 应该高于中频 (500Hz)
        assert rock_bands[0] > rock_bands[4]  # 31Hz > 500Hz
        # 高频 (8kHz, 16kHz) 应该高于中频
        assert rock_bands[8] > rock_bands[4]  # 8kHz > 500Hz
    
    def test_bass_boost_preset(self):
        """bass_boost 预设低频增强明显"""
        bass_bands = get_preset_bands(EQPreset.BASS_BOOST)
        # 低频应该是正值
        assert bass_bands[0] > 5.0  # 31Hz
        assert bass_bands[1] > 5.0  # 62Hz
        # 高频应该是 0
        assert bass_bands[9] == 0.0  # 16kHz
    
    def test_get_preset_by_name_valid(self):
        """根据名称获取预设 - 有效名称"""
        assert get_preset_by_name("rock") == EQPreset.ROCK
        assert get_preset_by_name("ROCK") == EQPreset.ROCK
        assert get_preset_by_name("Rock") == EQPreset.ROCK
    
    def test_get_preset_by_name_invalid(self):
        """根据名称获取预设 - 无效名称返回 FLAT"""
        assert get_preset_by_name("invalid") == EQPreset.FLAT
        assert get_preset_by_name("") == EQPreset.FLAT
    
    def test_eq_band_labels(self):
        """测试频段标签"""
        assert len(EQ_BAND_LABELS) == 10
        assert EQ_BAND_LABELS[0] == "31Hz"
        assert EQ_BAND_LABELS[5] == "1kHz"
        assert EQ_BAND_LABELS[9] == "16kHz"


class TestPlayerServiceWithFactory:
    """PlayerService 工厂模式集成测试"""
    
    def test_player_service_uses_factory(self):
        """PlayerService 使用工厂创建引擎"""
        from services.player_service import PlayerService
        
        # 不传入引擎时应使用工厂
        player = PlayerService()
        assert player._engine is not None
        
        # 引擎名称应该是已知后端之一
        assert player._engine.get_engine_name() in ["pygame", "miniaudio", "vlc"]
    
    def test_player_service_accepts_custom_engine(self):
        """PlayerService 接受自定义引擎"""
        from services.player_service import PlayerService
        
        custom_engine = PygameAudioEngine()
        player = PlayerService(audio_engine=custom_engine)
        
        assert player._engine is custom_engine

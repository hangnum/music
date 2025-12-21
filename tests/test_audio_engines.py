"""
Audio Engine Unit Tests

Test AudioEngineBase, PygameAudioEngine, factory pattern, and EQ presets.
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
    """Tests for the AudioEngineBase abstract class."""
    
    def test_base_supports_default_false(self):
        """The base class should not support advanced features by default."""
        # Use PygameAudioEngine as a concrete implementation to test base behavior
        engine = PygameAudioEngine()
        
        # The pygame backend does not support advanced features
        assert engine.supports_gapless() is False
        assert engine.supports_crossfade() is False
        assert engine.supports_equalizer() is False
        assert engine.supports_replay_gain() is False
    
    def test_base_advanced_methods_no_op(self):
        """Advanced methods in the base class should have empty default implementations."""
        engine = PygameAudioEngine()
        
        # These methods should not raise exceptions
        assert engine.set_next_track("test.mp3") is False
        engine.set_crossfade_duration(1000)
        assert engine.get_crossfade_duration() == 0
        engine.set_replay_gain(2.0, 0.9)
        engine.set_equalizer([0] * 10)
        engine.set_equalizer_enabled(True)
    
    def test_pygame_engine_name(self):
        """PygameAudioEngine should return the correct name."""
        engine = PygameAudioEngine()
        assert engine.get_engine_name() == "pygame"


class TestAudioEngineFactory:
    """Tests for the AudioEngineFactory."""
    
    def test_create_pygame_engine(self):
        """Test creating a pygame engine."""
        engine = AudioEngineFactory.create("pygame")
        assert engine is not None
        assert engine.get_engine_name() == "pygame"
    
    def test_fallback_to_pygame(self):
        """Test fallback to an available backend when creating a non-existent one."""
        engine = AudioEngineFactory.create("nonexistent_backend")
        assert engine is not None
        # Should fallback to an available backend
        assert engine.get_engine_name() in ["pygame", "miniaudio", "vlc"]
    
    def test_get_available_backends(self):
        """Test getting the list of available backends."""
        backends = AudioEngineFactory.get_available_backends()
        assert isinstance(backends, list)
        # pygame should always be available
        assert "pygame" in backends
    
    def test_is_available(self):
        """Test checking for backend availability."""
        assert AudioEngineFactory.is_available("pygame") is True
        assert AudioEngineFactory.is_available("nonexistent") is False
    
    def test_get_backend_info(self):
        """Test getting backend feature information."""
        info = AudioEngineFactory.get_backend_info("pygame")
        assert isinstance(info, dict)
        assert "gapless" in info
        assert "crossfade" in info
        assert "equalizer" in info
        assert "replay_gain" in info


class TestEQPresets:
    """Tests for EQ presets."""
    
    def test_eq_preset_values(self):
        """Test that all presets are defined."""
        for preset in EQPreset:
            assert preset in EQ_PRESETS
            bands = EQ_PRESETS[preset]
            assert len(bands.bands) == 10
    
    def test_eq_bands_to_list(self):
        """Test EQBands.to_list()."""
        bands = EQBands((1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0))
        result = bands.to_list()
        assert result == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    def test_flat_preset_is_zero(self):
        """Test that all bands in the 'flat' preset are 0."""
        flat_bands = get_preset_bands(EQPreset.FLAT)
        assert all(b == 0.0 for b in flat_bands)
    
    def test_rock_preset_has_v_shape(self):
        """Test that the 'rock' preset has a V-shaped curve (bass and treble boost)."""
        rock_bands = get_preset_bands(EQPreset.ROCK)
        # Bass (31Hz, 62Hz) should be higher than midrange (500Hz)
        assert rock_bands[0] > rock_bands[4]  # 31Hz > 500Hz
        # Treble (8kHz, 16kHz) should be higher than midrange
        assert rock_bands[8] > rock_bands[4]  # 8kHz > 500Hz
    
    def test_bass_boost_preset(self):
        """Test the 'bass_boost' preset for significant low-frequency boost."""
        bass_bands = get_preset_bands(EQPreset.BASS_BOOST)
        # Low frequencies should be positive
        assert bass_bands[0] > 5.0  # 31Hz
        assert bass_bands[1] > 5.0  # 62Hz
        # Treble should be 0
        assert bass_bands[9] == 0.0  # 16kHz
    
    def test_get_preset_by_name_valid(self):
        """Test getting a preset by a valid name."""
        assert get_preset_by_name("rock") == EQPreset.ROCK
        assert get_preset_by_name("ROCK") == EQPreset.ROCK
        assert get_preset_by_name("Rock") == EQPreset.ROCK
    
    def test_get_preset_by_name_invalid(self):
        """Test that getting a preset by an invalid name returns FLAT."""
        assert get_preset_by_name("invalid") == EQPreset.FLAT
        assert get_preset_by_name("") == EQPreset.FLAT
    
    def test_eq_band_labels(self):
        """Test band labels."""
        assert len(EQ_BAND_LABELS) == 10
        assert EQ_BAND_LABELS[0] == "31Hz"
        assert EQ_BAND_LABELS[5] == "1kHz"
        assert EQ_BAND_LABELS[9] == "16kHz"


class TestPlayerServiceWithFactory:
    """Integration tests for PlayerService with the factory pattern."""
    
    def test_player_service_uses_factory(self):
        """Test that PlayerService uses the factory to create an engine."""
        from services.player_service import PlayerService
        
        # Should use factory if no engine is provided
        player = PlayerService()
        assert player._engine is not None
        
        # Engine name should be one of the known backends
        assert player._engine.get_engine_name() in ["pygame", "miniaudio", "vlc"]
    
    def test_player_service_accepts_custom_engine(self):
        """Test that PlayerService accepts a custom engine."""
        from services.player_service import PlayerService
        
        custom_engine = PygameAudioEngine()
        player = PlayerService(audio_engine=custom_engine)
        
        assert player._engine is custom_engine

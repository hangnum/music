"""
Audio Settings Dialog

Provides audio engine configuration interface, including:
- Audio backend selection
- Crossfade settings
- ReplayGain settings
- 10-band EQ equalizer
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services.config_service import ConfigService
from core.engine_factory import AudioEngineFactory
from models.eq_preset import EQPreset, EQ_PRESETS, EQ_BAND_LABELS, get_preset_bands
from ui.resources.design_tokens import tokens


class EQBandSlider(QWidget):
    """Single EQ band slider component"""
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._value = 0.0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)
        
        # Value display
        self._value_label = QLabel("0")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setFixedWidth(32)
        self._value_label.setStyleSheet(f"font-size: {tokens.FONT_SIZE_XS}px;")
        
        # Slider (vertical)
        self._slider = QSlider(Qt.Orientation.Vertical)
        self._slider.setMinimum(-120)  # -12.0 dB
        self._slider.setMaximum(120)   # +12.0 dB
        self._slider.setValue(0)
        self._slider.setFixedHeight(120)
        self._slider.valueChanged.connect(self._on_slider_changed)
        
        # Frequency label
        self._freq_label = QLabel(label)
        self._freq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._freq_label.setStyleSheet(f"font-size: 10px; color: {tokens.NEUTRAL_500};")
        
        layout.addWidget(self._value_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._slider, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._freq_label, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def _on_slider_changed(self, value: int) -> None:
        self._value = value / 10.0
        self._value_label.setText(f"{self._value:+.1f}")
    
    def get_value(self) -> float:
        return self._value
    
    def set_value(self, value: float) -> None:
        self._value = value
        self._slider.setValue(int(value * 10))
        self._value_label.setText(f"{value:+.1f}")


class AudioSettingsDialog(QDialog):
    """
    Audio Settings Dialog

    Provides audio engine and advanced audio features configuration interface.
    """
    
    def __init__(self, config: ConfigService, parent=None):
        super().__init__(parent)
        self._config = config
        
        self.setWindowTitle("Audio Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        # Audio backend settings
        main_layout.addWidget(self._create_backend_group())
        
        # Crossfade settings
        main_layout.addWidget(self._create_crossfade_group())
        
        # ReplayGain settings
        main_layout.addWidget(self._create_replay_gain_group())
        
        # Equalizer (10-band EQ)
        main_layout.addWidget(self._create_eq_group())
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        
        # Load configuration
        self._load_from_config()
    
    def _create_backend_group(self) -> QGroupBox:
        """Create audio backend selection group"""
        group = QGroupBox("Audio backend")
        layout = QFormLayout(group)
        
        # Backend selection
        self._backend_combo = QComboBox()
        available = AudioEngineFactory.get_available_backends()
        all_backends = ["miniaudio", "vlc", "pygame"]
        
        for backend in all_backends:
            display_name = self._get_backend_display_name(backend)
            is_available = backend in available
            self._backend_combo.addItem(
                f"{display_name}" + ("" if is_available else " (Not installed)"),
                backend
            )
            if not is_available:
                idx = self._backend_combo.count() - 1
                self._backend_combo.model().item(idx).setEnabled(False)
        
        layout.addRow("Audio Engine", self._backend_combo)
        
        # Current backend info
        self._backend_info_label = QLabel()
        self._backend_info_label.setStyleSheet(f"color: {tokens.NEUTRAL_500}; font-size: {tokens.FONT_SIZE_XS}px;")
        layout.addRow("", self._backend_info_label)
        
        self._backend_combo.currentIndexChanged.connect(self._update_backend_info)
        
        return group
    
    def _get_backend_display_name(self, backend: str) -> str:
        names = {
            "miniaudio": "miniaudio (Recommended - Gapless/Crossfade/EQ)",
            "vlc": "VLC (Native ReplayGain support)",
            "pygame": "pygame (Compatibility fallback)",
        }
        return names.get(backend, backend)
    
    def _update_backend_info(self) -> None:
        backend = self._backend_combo.currentData()
        if not backend:
            return
        
        info = AudioEngineFactory.get_backend_info(backend)
        if info:
            features = []
            if info.get("gapless"):
                features.append("Gapless")
            if info.get("crossfade"):
                features.append("Crossfade")
            if info.get("equalizer"):
                features.append("EQ")
            if info.get("replay_gain"):
                features.append("ReplayGain")
            
            self._backend_info_label.setText(
                f"Supported features: {', '.join(features)}" if features else "Basic playback"
            )
        else:
            self._backend_info_label.setText("Backend not available")
    
    def _create_crossfade_group(self) -> QGroupBox:
        """Create Crossfade settings group"""
        group = QGroupBox("Crossfade")
        layout = QFormLayout(group)

        # Enable switch
        self._crossfade_enabled = QCheckBox("Enable track transition crossfade")
        layout.addRow(self._crossfade_enabled)
        
        # Duration setting
        duration_layout = QHBoxLayout()
        self._crossfade_duration = QSpinBox()
        self._crossfade_duration.setRange(0, 10000)
        self._crossfade_duration.setSingleStep(100)
        self._crossfade_duration.setSuffix(" ms")
        duration_layout.addWidget(self._crossfade_duration)
        duration_layout.addWidget(QLabel("(Recommended: 500-2000ms)"))
        duration_layout.addStretch()
        layout.addRow("Crossfade duration", duration_layout)
        
        return group
    
    def _create_replay_gain_group(self) -> QGroupBox:
        """Create ReplayGain settings group"""
        group = QGroupBox("ReplayGain (Loudness Normalization)")
        layout = QFormLayout(group)

        # Enable switch
        self._rg_enabled = QCheckBox("Enable loudness normalization")
        layout.addRow(self._rg_enabled)
        
        # Mode selection
        self._rg_mode_combo = QComboBox()
        self._rg_mode_combo.addItem("Track mode", "track")
        self._rg_mode_combo.addItem("Album mode", "album")
        layout.addRow("Normalization mode", self._rg_mode_combo)
        
        # Anti-clipping
        self._rg_prevent_clipping = QCheckBox("Prevent audio clipping")
        layout.addRow(self._rg_prevent_clipping)
        
        # Preamp
        preamp_layout = QHBoxLayout()
        self._rg_preamp = QSpinBox()
        self._rg_preamp.setRange(-12, 12)
        self._rg_preamp.setSuffix(" dB")
        preamp_layout.addWidget(self._rg_preamp)
        preamp_layout.addWidget(QLabel("(Preamp, usually set to 0)"))
        preamp_layout.addStretch()
        layout.addRow("Preamp", preamp_layout)
        
        return group
    
    def _create_eq_group(self) -> QGroupBox:
        """Create 10-band EQ settings group"""
        group = QGroupBox("Equalizer (10-band EQ)")
        main_layout = QVBoxLayout(group)
        
        # Enable switch and presets
        top_layout = QHBoxLayout()
        
        self._eq_enabled = QCheckBox("Enable equalizer")
        top_layout.addWidget(self._eq_enabled)
        
        top_layout.addStretch()
        
        top_layout.addWidget(QLabel("Preset:"))
        self._eq_preset_combo = QComboBox()
        for preset in EQPreset:
            display_name = self._get_preset_display_name(preset)
            self._eq_preset_combo.addItem(display_name, preset.value)
        self._eq_preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        top_layout.addWidget(self._eq_preset_combo)
        
        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.setFixedWidth(60)
        reset_btn.clicked.connect(self._reset_eq)
        top_layout.addWidget(reset_btn)
        
        main_layout.addLayout(top_layout)
        
        # EQ sliders area
        sliders_layout = QHBoxLayout()
        sliders_layout.setSpacing(8)
        
        self._eq_sliders: list[EQBandSlider] = []
        for label in EQ_BAND_LABELS:
            slider = EQBandSlider(label)
            self._eq_sliders.append(slider)
            sliders_layout.addWidget(slider)
        
        main_layout.addLayout(sliders_layout)
        
        return group
    
    def _get_preset_display_name(self, preset: EQPreset) -> str:
        names = {
            EQPreset.FLAT: "Flat",
            EQPreset.ROCK: "Rock",
            EQPreset.POP: "Pop",
            EQPreset.JAZZ: "Jazz",
            EQPreset.CLASSICAL: "Classical",
            EQPreset.ELECTRONIC: "Electronic",
            EQPreset.HIP_HOP: "Hip-Hop",
            EQPreset.ACOUSTIC: "Acoustic",
            EQPreset.VOCAL: "Vocal",
            EQPreset.BASS_BOOST: "Bass Boost",
        }
        return names.get(preset, preset.value)
    
    def _on_preset_changed(self) -> None:
        """Apply EQ preset"""
        preset_value = self._eq_preset_combo.currentData()
        try:
            preset = EQPreset(preset_value)
            bands = get_preset_bands(preset)
            for i, slider in enumerate(self._eq_sliders):
                if i < len(bands):
                    slider.set_value(bands[i])
        except ValueError:
            pass
    
    def _reset_eq(self) -> None:
        """Reset EQ to Flat"""
        self._eq_preset_combo.setCurrentIndex(0)  # Flat
        for slider in self._eq_sliders:
            slider.set_value(0.0)
    
    def _load_from_config(self) -> None:
        """Load settings from configuration"""
        # Audio backend
        backend = str(self._config.get("audio.backend", "miniaudio"))
        idx = self._backend_combo.findData(backend)
        if idx >= 0:
            self._backend_combo.setCurrentIndex(idx)
        self._update_backend_info()
        
        # Crossfade
        self._crossfade_enabled.setChecked(
            bool(self._config.get("audio.crossfade.enabled", True))
        )
        self._crossfade_duration.setValue(
            int(self._config.get("audio.crossfade.duration_ms", 500))
        )
        
        # ReplayGain
        self._rg_enabled.setChecked(
            bool(self._config.get("audio.replay_gain.enabled", True))
        )
        rg_mode = str(self._config.get("audio.replay_gain.mode", "track"))
        idx = self._rg_mode_combo.findData(rg_mode)
        if idx >= 0:
            self._rg_mode_combo.setCurrentIndex(idx)
        self._rg_prevent_clipping.setChecked(
            bool(self._config.get("audio.replay_gain.prevent_clipping", True))
        )
        self._rg_preamp.setValue(
            int(self._config.get("audio.replay_gain.preamp_db", 0))
        )
        
        # EQ
        self._eq_enabled.setChecked(
            bool(self._config.get("audio.equalizer.enabled", False))
        )
        preset = str(self._config.get("audio.equalizer.preset", "flat"))
        idx = self._eq_preset_combo.findData(preset)
        if idx >= 0:
            self._eq_preset_combo.setCurrentIndex(idx)
        
        # Load custom band values
        bands = self._config.get("audio.equalizer.bands", [0] * 10)
        if isinstance(bands, list) and len(bands) >= 10:
            for i, slider in enumerate(self._eq_sliders):
                if i < len(bands):
                    slider.set_value(float(bands[i]))
    
    def _on_save(self) -> None:
        """Save configuration"""
        # Audio backend
        backend = self._backend_combo.currentData()
        if backend:
            self._config.set("audio.backend", backend)
        
        # Crossfade
        self._config.set("audio.crossfade.enabled", self._crossfade_enabled.isChecked())
        self._config.set("audio.crossfade.duration_ms", self._crossfade_duration.value())
        
        # ReplayGain
        self._config.set("audio.replay_gain.enabled", self._rg_enabled.isChecked())
        self._config.set("audio.replay_gain.mode", self._rg_mode_combo.currentData())
        self._config.set("audio.replay_gain.prevent_clipping", self._rg_prevent_clipping.isChecked())
        self._config.set("audio.replay_gain.preamp_db", self._rg_preamp.value())
        
        # EQ
        self._config.set("audio.equalizer.enabled", self._eq_enabled.isChecked())
        self._config.set("audio.equalizer.preset", self._eq_preset_combo.currentData())
        
        # Save custom band values
        bands = [slider.get_value() for slider in self._eq_sliders]
        self._config.set("audio.equalizer.bands", bands)
        
        if not self._config.save():
            QMessageBox.critical(self, "Error", "Failed to save configuration")
            return
        
        QMessageBox.information(
            self, "Information", 
            "Settings saved.\nSome changes (like audio backend switching) require application restart to take effect."
        )
        self.accept()

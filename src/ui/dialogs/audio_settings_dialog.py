"""
音频设置对话框

提供音频引擎配置界面，包括:
- 音频后端选择
- Crossfade 设置
- ReplayGain 设置
- 10 频段 EQ 均衡器
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
    """单个 EQ 频段滑块组件"""
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._value = 0.0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)
        
        # 值显示
        self._value_label = QLabel("0")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setFixedWidth(32)
        self._value_label.setStyleSheet(f"font-size: {tokens.FONT_SIZE_XS}px;")
        
        # 滑块 (垂直)
        self._slider = QSlider(Qt.Orientation.Vertical)
        self._slider.setMinimum(-120)  # -12.0 dB
        self._slider.setMaximum(120)   # +12.0 dB
        self._slider.setValue(0)
        self._slider.setFixedHeight(120)
        self._slider.valueChanged.connect(self._on_slider_changed)
        
        # 频率标签
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
    音频设置对话框
    
    提供音频引擎和高级音频特性的配置界面。
    """
    
    def __init__(self, config: ConfigService, parent=None):
        super().__init__(parent)
        self._config = config
        
        self.setWindowTitle("音频设置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        # 音频后端设置
        main_layout.addWidget(self._create_backend_group())
        
        # Crossfade 设置
        main_layout.addWidget(self._create_crossfade_group())
        
        # ReplayGain 设置
        main_layout.addWidget(self._create_replay_gain_group())
        
        # EQ 均衡器
        main_layout.addWidget(self._create_eq_group())
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        
        # 加载配置
        self._load_from_config()
    
    def _create_backend_group(self) -> QGroupBox:
        """创建音频后端选择组"""
        group = QGroupBox("音频后端")
        layout = QFormLayout(group)
        
        # 后端选择
        self._backend_combo = QComboBox()
        available = AudioEngineFactory.get_available_backends()
        all_backends = ["miniaudio", "vlc", "pygame"]
        
        for backend in all_backends:
            display_name = self._get_backend_display_name(backend)
            is_available = backend in available
            self._backend_combo.addItem(
                f"{display_name}" + ("" if is_available else " (未安装)"),
                backend
            )
            if not is_available:
                idx = self._backend_combo.count() - 1
                self._backend_combo.model().item(idx).setEnabled(False)
        
        layout.addRow("音频引擎", self._backend_combo)
        
        # 当前后端信息
        self._backend_info_label = QLabel()
        self._backend_info_label.setStyleSheet(f"color: {tokens.NEUTRAL_500}; font-size: {tokens.FONT_SIZE_XS}px;")
        layout.addRow("", self._backend_info_label)
        
        self._backend_combo.currentIndexChanged.connect(self._update_backend_info)
        
        return group
    
    def _get_backend_display_name(self, backend: str) -> str:
        names = {
            "miniaudio": "miniaudio (推荐 - Gapless/Crossfade/EQ)",
            "vlc": "VLC (ReplayGain 原生支持)",
            "pygame": "pygame (兼容性后备)",
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
                f"支持特性: {', '.join(features)}" if features else "基础播放"
            )
        else:
            self._backend_info_label.setText("后端不可用")
    
    def _create_crossfade_group(self) -> QGroupBox:
        """创建 Crossfade 设置组"""
        group = QGroupBox("淡入淡出 (Crossfade)")
        layout = QFormLayout(group)
        
        # 启用开关
        self._crossfade_enabled = QCheckBox("启用曲目切换淡入淡出")
        layout.addRow(self._crossfade_enabled)
        
        # 时长设置
        duration_layout = QHBoxLayout()
        self._crossfade_duration = QSpinBox()
        self._crossfade_duration.setRange(0, 10000)
        self._crossfade_duration.setSingleStep(100)
        self._crossfade_duration.setSuffix(" ms")
        duration_layout.addWidget(self._crossfade_duration)
        duration_layout.addWidget(QLabel("(建议: 500-2000ms)"))
        duration_layout.addStretch()
        layout.addRow("淡入淡出时长", duration_layout)
        
        return group
    
    def _create_replay_gain_group(self) -> QGroupBox:
        """创建 ReplayGain 设置组"""
        group = QGroupBox("响度规范化 (ReplayGain)")
        layout = QFormLayout(group)
        
        # 启用开关
        self._rg_enabled = QCheckBox("启用响度规范化")
        layout.addRow(self._rg_enabled)
        
        # 模式选择
        self._rg_mode_combo = QComboBox()
        self._rg_mode_combo.addItem("单曲模式 (Track)", "track")
        self._rg_mode_combo.addItem("专辑模式 (Album)", "album")
        layout.addRow("规范化模式", self._rg_mode_combo)
        
        # 防削波
        self._rg_prevent_clipping = QCheckBox("防止音频削波")
        layout.addRow(self._rg_prevent_clipping)
        
        # Preamp
        preamp_layout = QHBoxLayout()
        self._rg_preamp = QSpinBox()
        self._rg_preamp.setRange(-12, 12)
        self._rg_preamp.setSuffix(" dB")
        preamp_layout.addWidget(self._rg_preamp)
        preamp_layout.addWidget(QLabel("(预增益，通常设为 0)"))
        preamp_layout.addStretch()
        layout.addRow("预增益", preamp_layout)
        
        return group
    
    def _create_eq_group(self) -> QGroupBox:
        """创建 10 频段 EQ 设置组"""
        group = QGroupBox("均衡器 (10 频段 EQ)")
        main_layout = QVBoxLayout(group)
        
        # 启用开关和预设
        top_layout = QHBoxLayout()
        
        self._eq_enabled = QCheckBox("启用均衡器")
        top_layout.addWidget(self._eq_enabled)
        
        top_layout.addStretch()
        
        top_layout.addWidget(QLabel("预设:"))
        self._eq_preset_combo = QComboBox()
        for preset in EQPreset:
            display_name = self._get_preset_display_name(preset)
            self._eq_preset_combo.addItem(display_name, preset.value)
        self._eq_preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        top_layout.addWidget(self._eq_preset_combo)
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.setFixedWidth(60)
        reset_btn.clicked.connect(self._reset_eq)
        top_layout.addWidget(reset_btn)
        
        main_layout.addLayout(top_layout)
        
        # EQ 滑块区域
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
            EQPreset.FLAT: "平坦",
            EQPreset.ROCK: "摇滚",
            EQPreset.POP: "流行",
            EQPreset.JAZZ: "爵士",
            EQPreset.CLASSICAL: "古典",
            EQPreset.ELECTRONIC: "电子",
            EQPreset.HIP_HOP: "嘻哈",
            EQPreset.ACOUSTIC: "原声",
            EQPreset.VOCAL: "人声",
            EQPreset.BASS_BOOST: "低音增强",
        }
        return names.get(preset, preset.value)
    
    def _on_preset_changed(self) -> None:
        """应用 EQ 预设"""
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
        """重置 EQ 为平坦"""
        self._eq_preset_combo.setCurrentIndex(0)  # Flat
        for slider in self._eq_sliders:
            slider.set_value(0.0)
    
    def _load_from_config(self) -> None:
        """从配置加载设置"""
        # 音频后端
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
        
        # 加载自定义频段值
        bands = self._config.get("audio.equalizer.bands", [0] * 10)
        if isinstance(bands, list) and len(bands) >= 10:
            for i, slider in enumerate(self._eq_sliders):
                if i < len(bands):
                    slider.set_value(float(bands[i]))
    
    def _on_save(self) -> None:
        """保存配置"""
        # 音频后端
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
        
        # 保存自定义频段值
        bands = [slider.get_value() for slider in self._eq_sliders]
        self._config.set("audio.equalizer.bands", bands)
        
        if not self._config.save():
            QMessageBox.critical(self, "错误", "保存配置失败")
            return
        
        QMessageBox.information(
            self, "提示", 
            "设置已保存。\n部分更改（如音频后端切换）需要重启应用才能生效。"
        )
        self.accept()

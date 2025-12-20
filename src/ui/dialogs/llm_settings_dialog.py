from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from services.config_service import ConfigService
from services.llm_providers import AVAILABLE_PROVIDERS


class LLMSettingsDialog(QDialog):
    """LLM 服务设置对话框
    
    支持多个提供商的配置切换。
    """
    
    def __init__(self, config: ConfigService, parent=None):
        super().__init__(parent)
        self._config = config

        self.setWindowTitle("LLM 设置")
        self.setMinimumWidth(520)

        # 提供商选择器
        self._provider_combo = QComboBox()
        self._provider_combo.addItems([p.title() for p in AVAILABLE_PROVIDERS])
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        # 通用设置
        provider_layout = QFormLayout()
        provider_layout.addRow("提供商", self._provider_combo)

        # 堆叠面板：各提供商配置
        self._stack = QStackedWidget()
        self._siliconflow_widget = self._create_siliconflow_widget()
        self._gemini_widget = self._create_gemini_widget()
        self._stack.addWidget(self._siliconflow_widget)
        self._stack.addWidget(self._gemini_widget)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        # 主布局
        layout = QVBoxLayout(self)
        layout.addLayout(provider_layout)
        layout.addWidget(self._stack)
        layout.addWidget(buttons)

        self._load_from_config()

    def _create_siliconflow_widget(self) -> QWidget:
        """创建 SiliconFlow 配置面板"""
        widget = QGroupBox("SiliconFlow 配置")
        
        self._sf_base_url_edit = QLineEdit()
        self._sf_model_edit = QLineEdit()
        self._sf_timeout_edit = QLineEdit()
        self._sf_api_key_env_edit = QLineEdit()
        self._sf_api_key_edit = QLineEdit()
        self._sf_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._sf_show_key = QCheckBox("显示 API Key")
        self._sf_show_key.toggled.connect(
            lambda checked: self._sf_api_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )

        form = QFormLayout(widget)
        form.addRow("Base URL", self._sf_base_url_edit)
        form.addRow("Model", self._sf_model_edit)
        form.addRow("Timeout (s)", self._sf_timeout_edit)
        form.addRow("API Key Env", self._sf_api_key_env_edit)
        form.addRow("API Key", self._sf_api_key_edit)
        form.addRow("", self._sf_show_key)

        return widget

    def _create_gemini_widget(self) -> QWidget:
        """创建 Gemini 配置面板"""
        widget = QGroupBox("Google Gemini 配置")
        
        self._gm_base_url_edit = QLineEdit()
        self._gm_model_edit = QLineEdit()
        self._gm_timeout_edit = QLineEdit()
        self._gm_api_key_env_edit = QLineEdit()
        self._gm_api_key_edit = QLineEdit()
        self._gm_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._gm_show_key = QCheckBox("显示 API Key")
        self._gm_show_key.toggled.connect(
            lambda checked: self._gm_api_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )

        form = QFormLayout(widget)
        form.addRow("Base URL", self._gm_base_url_edit)
        form.addRow("Model", self._gm_model_edit)
        form.addRow("Timeout (s)", self._gm_timeout_edit)
        form.addRow("API Key Env", self._gm_api_key_env_edit)
        form.addRow("API Key", self._gm_api_key_edit)
        form.addRow("", self._gm_show_key)
        
        # Gemini 特别提示
        note = QLabel("注意：需要能访问 Google API 的网络环境")
        note.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow("", note)

        return widget

    def _on_provider_changed(self, index: int) -> None:
        """切换提供商面板"""
        self._stack.setCurrentIndex(index)

    def _load_from_config(self) -> None:
        """从配置加载当前设置"""
        # 当前提供商
        provider = str(self._config.get("llm.provider", "siliconflow")).lower()
        try:
            idx = AVAILABLE_PROVIDERS.index(provider)
        except ValueError:
            idx = 0
        self._provider_combo.setCurrentIndex(idx)
        self._stack.setCurrentIndex(idx)

        # SiliconFlow 配置
        self._sf_base_url_edit.setText(
            str(self._config.get("llm.siliconflow.base_url", "https://api.siliconflow.cn/v1"))
        )
        self._sf_model_edit.setText(
            str(self._config.get("llm.siliconflow.model", "Qwen/Qwen2.5-7B-Instruct"))
        )
        self._sf_timeout_edit.setText(
            str(self._config.get("llm.siliconflow.timeout_seconds", 20.0))
        )
        self._sf_api_key_env_edit.setText(
            str(self._config.get("llm.siliconflow.api_key_env", "SILICONFLOW_API_KEY"))
        )
        self._sf_api_key_edit.setText(
            str(self._config.get("llm.siliconflow.api_key", ""))
        )

        # Gemini 配置
        self._gm_base_url_edit.setText(
            str(self._config.get("llm.gemini.base_url", "https://generativelanguage.googleapis.com/v1beta"))
        )
        self._gm_model_edit.setText(
            str(self._config.get("llm.gemini.model", "gemini-2.0-flash"))
        )
        self._gm_timeout_edit.setText(
            str(self._config.get("llm.gemini.timeout_seconds", 30.0))
        )
        self._gm_api_key_env_edit.setText(
            str(self._config.get("llm.gemini.api_key_env", "GOOGLE_GEMINI_API_KEY"))
        )
        self._gm_api_key_edit.setText(
            str(self._config.get("llm.gemini.api_key", ""))
        )

    def _on_save(self) -> None:
        """保存配置"""
        # 当前选择的提供商
        provider_idx = self._provider_combo.currentIndex()
        provider_name = AVAILABLE_PROVIDERS[provider_idx]
        
        # 验证并保存 SiliconFlow 配置
        sf_base_url = self._sf_base_url_edit.text().strip()
        sf_model = self._sf_model_edit.text().strip()
        sf_timeout_raw = self._sf_timeout_edit.text().strip()
        sf_api_key_env = self._sf_api_key_env_edit.text().strip()
        sf_api_key = self._sf_api_key_edit.text().strip()

        try:
            sf_timeout = float(sf_timeout_raw) if sf_timeout_raw else 20.0
            if sf_timeout <= 0:
                QMessageBox.warning(self, "提示", "SiliconFlow Timeout 必须是正数")
                return
        except ValueError:
            QMessageBox.warning(self, "提示", "SiliconFlow Timeout 必须是数字")
            return

        # 验证并保存 Gemini 配置
        gm_base_url = self._gm_base_url_edit.text().strip()
        gm_model = self._gm_model_edit.text().strip()
        gm_timeout_raw = self._gm_timeout_edit.text().strip()
        gm_api_key_env = self._gm_api_key_env_edit.text().strip()
        gm_api_key = self._gm_api_key_edit.text().strip()

        try:
            gm_timeout = float(gm_timeout_raw) if gm_timeout_raw else 30.0
            if gm_timeout <= 0:
                QMessageBox.warning(self, "提示", "Gemini Timeout 必须是正数")
                return
        except ValueError:
            QMessageBox.warning(self, "提示", "Gemini Timeout 必须是数字")
            return

        # 保存提供商选择
        self._config.set("llm.provider", provider_name)

        # 保存 SiliconFlow 配置
        self._config.set("llm.siliconflow.base_url", sf_base_url or "https://api.siliconflow.cn/v1")
        self._config.set("llm.siliconflow.model", sf_model or "Qwen/Qwen2.5-7B-Instruct")
        self._config.set("llm.siliconflow.timeout_seconds", sf_timeout)
        self._config.set("llm.siliconflow.api_key_env", sf_api_key_env or "SILICONFLOW_API_KEY")
        self._config.set("llm.siliconflow.api_key", sf_api_key)

        # 保存 Gemini 配置
        self._config.set("llm.gemini.base_url", gm_base_url or "https://generativelanguage.googleapis.com/v1beta")
        self._config.set("llm.gemini.model", gm_model or "gemini-2.0-flash")
        self._config.set("llm.gemini.timeout_seconds", gm_timeout)
        self._config.set("llm.gemini.api_key_env", gm_api_key_env or "GOOGLE_GEMINI_API_KEY")
        self._config.set("llm.gemini.api_key", gm_api_key)

        if not self._config.save():
            QMessageBox.critical(self, "错误", "保存配置失败")
            return

        self.accept()

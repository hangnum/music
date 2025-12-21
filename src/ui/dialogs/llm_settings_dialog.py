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
    """LLM Service Settings Dialog
    
    Supports configuration switching for multiple providers.
    """
    
    def __init__(self, config: ConfigService, parent=None):
        super().__init__(parent)
        self._config = config

        self.setWindowTitle("LLM Settings")
        self.setMinimumWidth(520)

        # Provider selector
        self._provider_combo = QComboBox()
        self._provider_combo.addItems([p.title() for p in AVAILABLE_PROVIDERS])
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        # Common settings
        provider_layout = QFormLayout()
        provider_layout.addRow("Provider", self._provider_combo)

        # Stacked panel for each provider's configuration
        self._stack = QStackedWidget()
        self._siliconflow_widget = self._create_siliconflow_widget()
        self._gemini_widget = self._create_gemini_widget()
        self._stack.addWidget(self._siliconflow_widget)
        self._stack.addWidget(self._gemini_widget)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addLayout(provider_layout)
        layout.addWidget(self._stack)
        layout.addWidget(buttons)

        self._load_from_config()

    def _create_siliconflow_widget(self) -> QWidget:
        """Create SiliconFlow configuration panel"""
        widget = QGroupBox("SiliconFlow Configuration")
        
        self._sf_base_url_edit = QLineEdit()
        self._sf_model_edit = QLineEdit()
        self._sf_timeout_edit = QLineEdit()
        self._sf_api_key_env_edit = QLineEdit()
        self._sf_api_key_edit = QLineEdit()
        self._sf_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._sf_show_key = QCheckBox("Show API Key")
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
        """Create Gemini configuration panel"""
        widget = QGroupBox("Google Gemini Configuration")
        
        self._gm_base_url_edit = QLineEdit()
        self._gm_model_edit = QLineEdit()
        self._gm_timeout_edit = QLineEdit()
        self._gm_api_key_env_edit = QLineEdit()
        self._gm_api_key_edit = QLineEdit()
        self._gm_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._gm_show_key = QCheckBox("Show API Key")
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
        
        # Gemini special note
        note = QLabel("Note: Network environment that can access Google API is required")
        from ui.resources.design_tokens import tokens
        note.setStyleSheet(f"color: {tokens.NEUTRAL_500}; font-size: {tokens.FONT_SIZE_XS}px;")
        form.addRow("", note)

        return widget

    def _on_provider_changed(self, index: int) -> None:
        """Switch provider panel."""
        self._stack.setCurrentIndex(index)

    def _load_from_config(self) -> None:
        """Load current settings from configuration"""
        # Current Provider
        provider = str(self._config.get("llm.provider", "siliconflow")).lower()
        try:
            idx = AVAILABLE_PROVIDERS.index(provider)
        except ValueError:
            idx = 0
        self._provider_combo.setCurrentIndex(idx)
        self._stack.setCurrentIndex(idx)

        # SiliconFlow Configuration
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

        # Gemini Configuration
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
        """Save configuration"""
        # Current provider selection
        provider_idx = self._provider_combo.currentIndex()
        provider_name = AVAILABLE_PROVIDERS[provider_idx]
        
        # Validate and save SiliconFlow configuration
        sf_base_url = self._sf_base_url_edit.text().strip()
        sf_model = self._sf_model_edit.text().strip()
        sf_timeout_raw = self._sf_timeout_edit.text().strip()
        sf_api_key_env = self._sf_api_key_env_edit.text().strip()
        sf_api_key = self._sf_api_key_edit.text().strip()

        try:
            sf_timeout = float(sf_timeout_raw) if sf_timeout_raw else 20.0
            if sf_timeout <= 0:
                QMessageBox.warning(self, "Warning", "SiliconFlow Timeout must be a positive number")
                return
        except ValueError:
            QMessageBox.warning(self, "Warning", "SiliconFlow Timeout must be a number")
            return

        # Validate and save Gemini configuration
        gm_base_url = self._gm_base_url_edit.text().strip()
        gm_model = self._gm_model_edit.text().strip()
        gm_timeout_raw = self._gm_timeout_edit.text().strip()
        gm_api_key_env = self._gm_api_key_env_edit.text().strip()
        gm_api_key = self._gm_api_key_edit.text().strip()

        try:
            gm_timeout = float(gm_timeout_raw) if gm_timeout_raw else 30.0
            if gm_timeout <= 0:
                QMessageBox.warning(self, "Warning", "Gemini Timeout must be a positive number")
                return
        except ValueError:
            QMessageBox.warning(self, "Warning", "Gemini Timeout must be a number")
            return

        # Save provider selection
        self._config.set("llm.provider", provider_name)

        # Save SiliconFlow configuration
        self._config.set("llm.siliconflow.base_url", sf_base_url or "https://api.siliconflow.cn/v1")
        self._config.set("llm.siliconflow.model", sf_model or "Qwen/Qwen2.5-7B-Instruct")
        self._config.set("llm.siliconflow.timeout_seconds", sf_timeout)
        self._config.set("llm.siliconflow.api_key_env", sf_api_key_env or "SILICONFLOW_API_KEY")
        self._config.set("llm.siliconflow.api_key", sf_api_key)

        # Save Gemini configuration
        self._config.set("llm.gemini.base_url", gm_base_url or "https://generativelanguage.googleapis.com/v1beta")
        self._config.set("llm.gemini.model", gm_model or "gemini-2.0-flash")
        self._config.set("llm.gemini.timeout_seconds", gm_timeout)
        self._config.set("llm.gemini.api_key_env", gm_api_key_env or "GOOGLE_GEMINI_API_KEY")
        self._config.set("llm.gemini.api_key", gm_api_key)

        if not self._config.save():
            QMessageBox.critical(self, "Error", "Failed to save configuration")
            return

        self.accept()

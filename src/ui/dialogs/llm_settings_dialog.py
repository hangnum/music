from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from services.config_service import ConfigService


class LLMSettingsDialog(QDialog):
    def __init__(self, config: ConfigService, parent=None):
        super().__init__(parent)
        self._config = config

        self.setWindowTitle("LLM 设置（SiliconFlow）")
        self.setMinimumWidth(520)

        self._base_url_edit = QLineEdit()
        self._model_edit = QLineEdit()
        self._timeout_edit = QLineEdit()

        self._api_key_env_edit = QLineEdit()
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._show_key = QCheckBox("显示 API Key")
        self._show_key.toggled.connect(self._on_toggle_show_key)

        form = QFormLayout()
        form.addRow("Base URL", self._base_url_edit)
        form.addRow("Model", self._model_edit)
        form.addRow("Timeout (s)", self._timeout_edit)
        form.addRow("API Key Env", self._api_key_env_edit)
        form.addRow("API Key", self._api_key_edit)
        form.addRow("", self._show_key)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._load_from_config()

    def _load_from_config(self) -> None:
        self._base_url_edit.setText(str(self._config.get("llm.siliconflow.base_url", "https://api.siliconflow.cn/v1")))
        self._model_edit.setText(str(self._config.get("llm.siliconflow.model", "Qwen/Qwen2.5-7B-Instruct")))
        self._timeout_edit.setText(str(self._config.get("llm.siliconflow.timeout_seconds", 20.0)))
        self._api_key_env_edit.setText(str(self._config.get("llm.siliconflow.api_key_env", "SILICONFLOW_API_KEY")))
        self._api_key_edit.setText(str(self._config.get("llm.siliconflow.api_key", "")))

    def _on_toggle_show_key(self, checked: bool) -> None:
        self._api_key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _on_save(self) -> None:
        base_url = self._base_url_edit.text().strip()
        model = self._model_edit.text().strip()
        timeout_raw = self._timeout_edit.text().strip()
        api_key_env = self._api_key_env_edit.text().strip()
        api_key = self._api_key_edit.text().strip()

        if not base_url:
            QMessageBox.warning(self, "提示", "Base URL 不能为空")
            return
        if not model:
            QMessageBox.warning(self, "提示", "Model 不能为空")
            return

        try:
            timeout_seconds = float(timeout_raw) if timeout_raw else 20.0
        except ValueError:
            QMessageBox.warning(self, "提示", "Timeout 必须是数字")
            return

        self._config.set("llm.siliconflow.base_url", base_url)
        self._config.set("llm.siliconflow.model", model)
        self._config.set("llm.siliconflow.timeout_seconds", timeout_seconds)
        self._config.set("llm.siliconflow.api_key_env", api_key_env or "SILICONFLOW_API_KEY")
        self._config.set("llm.siliconflow.api_key", api_key)

        if not self._config.save():
            QMessageBox.critical(self, "错误", "保存配置失败")
            return

        self.accept()


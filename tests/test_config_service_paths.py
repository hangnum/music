"""
Regression tests for ConfigService path handling and isolation.

Goal: Avoid overwriting repository template configuration files and ensure 
that the test environment does not pollute the real user directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture(autouse=True)
def _reset_config_service():
    from services.config_service import ConfigService

    ConfigService.reset_instance()
    yield
    ConfigService.reset_instance()


def _sandbox_user_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    base = tmp_path / "user-config"
    # Set for Windows/Mac/Linux to avoid platform differences leaking to real user directories
    monkeypatch.setenv("APPDATA", str(base))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(base))
    return base


def test_custom_config_path_save_and_reload_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from services.config_service import ConfigService

    _sandbox_user_config_dir(monkeypatch, tmp_path)

    custom_path = tmp_path / "isolated.yaml"
    config = ConfigService(str(custom_path))
    config.set("app.language", "en_US")

    assert config.save() is True
    assert custom_path.exists()

    # Custom mode should not write to the default user directory
    assert ConfigService._get_user_config_path().exists() is False

    ConfigService.reset_instance()
    config2 = ConfigService(str(custom_path))
    assert config2.get("app.language") == "en_US"


def test_passing_default_template_path_does_not_write_to_repo_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from services.config_service import ConfigService

    _sandbox_user_config_dir(monkeypatch, tmp_path)

    template_path = Path("config/default_config.yaml")
    before = template_path.read_text(encoding="utf-8")

    # When the default template path is passed, it should still save to the user directory
    # (avoiding writing back to the repository file).
    config = ConfigService("config/default_config.yaml")
    config.set("ui.window_width", 999)
    assert config.save() is True

    user_config_path = ConfigService._get_user_config_path()
    assert user_config_path.exists()

    after = template_path.read_text(encoding="utf-8")
    assert after == before


def test_default_mode_user_config_overrides_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from services.config_service import ConfigService

    _sandbox_user_config_dir(monkeypatch, tmp_path)

    user_config_path = ConfigService._get_user_config_path()
    user_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_config_path.write_text(yaml.safe_dump({"app": {"language": "en_US"}}, allow_unicode=True), encoding="utf-8")

    config = ConfigService()
    assert config.get("app.language") == "en_US"


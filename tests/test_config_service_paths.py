"""
ConfigService 路径/隔离相关的回归测试。

目标：避免误写仓库模板配置文件，且确保测试环境不会污染真实用户目录。
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
    # windows/mac/linux 都设置，避免平台差异导致落到真实用户目录
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

    # custom 模式不应写入用户目录
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

    # 传入默认模板路径时，仍应保存到用户目录（避免回写仓库文件）
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


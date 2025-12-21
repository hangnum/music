"""
Repository safety and consistency regression tests.

Used to detect early issues such as "accidental submission of keys or sensitive configurations".
"""

from __future__ import annotations

from pathlib import Path

import yaml


def test_default_config_does_not_contain_real_api_key():
    cfg_path = Path("config/default_config.yaml")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    api_key = (
        data.get("llm", {})
        .get("siliconflow", {})
        .get("api_key", "")
    )
    assert api_key in ("", None)


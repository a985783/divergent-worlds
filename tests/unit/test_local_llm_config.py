from __future__ import annotations

import os

from engine import local_llm_config


def test_saved_llm_config_applies_to_environment(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "llm_config.json"
    monkeypatch.setattr(local_llm_config, "CONFIG_PATH", config_path)
    for key in ["LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_LIVE_ENABLED"]:
        monkeypatch.delenv(key, raising=False)

    local_llm_config.save_llm_config(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key="sk-test",
        live_enabled=True,
    )
    local_llm_config.apply_saved_llm_config()

    assert os.environ["LLM_MODEL"] == "deepseek-v4-flash"
    assert os.environ["LLM_BASE_URL"] == "https://api.deepseek.com"
    assert os.environ["LLM_API_KEY"] == "sk-test"
    assert os.environ["LLM_LIVE_ENABLED"] == "true"


def test_delete_saved_llm_config(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "llm_config.json"
    monkeypatch.setattr(local_llm_config, "CONFIG_PATH", config_path)
    local_llm_config.save_llm_config(
        model="gpt-4o-mini",
        base_url="",
        api_key="sk-test",
        live_enabled=False,
    )

    local_llm_config.delete_saved_llm_config()

    assert not config_path.exists()

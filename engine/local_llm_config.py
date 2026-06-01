from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


CONFIG_PATH = Path.home() / ".parallel_worlds" / "llm_config.json"


def apply_saved_llm_config() -> None:
    config = load_saved_llm_config()
    if not config:
        return

    mapping = {
        "model": "LLM_MODEL",
        "base_url": "LLM_BASE_URL",
        "api_key": "LLM_API_KEY",
        "live_enabled": "LLM_LIVE_ENABLED",
        "output_language": "LLM_OUTPUT_LANGUAGE",
        "ui_language": "APP_LANGUAGE",
    }
    for config_key, env_key in mapping.items():
        value = config.get(config_key)
        if value is not None and str(value).strip():
            os.environ[env_key] = str(value).strip()


def load_saved_llm_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save_llm_config(
    *,
    model: str,
    base_url: str,
    api_key: str | None,
    live_enabled: bool,
    output_language: str | None = None,
    ui_language: str | None = None,
) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_saved_llm_config()
    config = {
        "model": model,
        "base_url": base_url,
        "live_enabled": "true" if live_enabled else "false",
    }
    if output_language:
        config["output_language"] = output_language
    elif existing.get("output_language"):
        config["output_language"] = existing["output_language"]
    if ui_language:
        config["ui_language"] = ui_language
    elif existing.get("ui_language"):
        config["ui_language"] = existing["ui_language"]
    if api_key:
        config["api_key"] = api_key
    elif existing.get("api_key"):
        config["api_key"] = existing["api_key"]

    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    CONFIG_PATH.chmod(0o600)


def save_language_config(*, ui_language: str, output_language: str) -> None:
    existing = load_saved_llm_config()
    save_llm_config(
        model=str(existing.get("model") or os.getenv("LLM_MODEL") or "gpt-4o-mini"),
        base_url=str(existing.get("base_url") or os.getenv("LLM_BASE_URL") or ""),
        api_key=existing.get("api_key") or os.getenv("LLM_API_KEY"),
        live_enabled=str(existing.get("live_enabled") or os.getenv("LLM_LIVE_ENABLED") or "false")
        .strip()
        .lower()
        == "true",
        output_language=output_language,
        ui_language=ui_language,
    )


def delete_saved_llm_config() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def saved_llm_config_path() -> Path:
    return CONFIG_PATH

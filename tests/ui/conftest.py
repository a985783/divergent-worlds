from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def preserve_llm_environment():
    keys = ["LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_LIVE_ENABLED"]
    original = {key: os.environ.get(key) for key in keys}
    yield
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

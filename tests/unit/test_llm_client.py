from __future__ import annotations

import pytest

from engine.llm_client import LLMCallError, LLMClient, normalize_base_url
from engine.schemas import MaterialSummary
from tests.conftest import make_material_summary


def test_missing_api_key_raises_clear_error_before_network_client_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    client = LLMClient(api_key="")

    with pytest.raises(LLMCallError, match="LLM_API_KEY is not configured"):
        client.generate(MaterialSummary, [{"role": "user", "content": "summarize"}])

    assert client.get_usage() == {"input_tokens": 0, "output_tokens": 0, "calls": 0}


def test_normalize_base_url_handles_common_pasted_endpoints() -> None:
    assert normalize_base_url("") is None
    assert normalize_base_url(" https://api.openai.com ") == "https://api.openai.com/v1"
    assert (
        normalize_base_url("https://example.com/v1/chat/completions")
        == "https://example.com/v1"
    )
    assert (
        normalize_base_url("https://example.com/chat/completions")
        == "https://example.com"
    )
    assert normalize_base_url("https://openrouter.ai/api/v1/") == "https://openrouter.ai/api/v1"
    assert normalize_base_url("https://api.deepseek.com/anthropic") == "https://api.deepseek.com"
    assert normalize_base_url("https://platform.deepseek.com") == "https://api.deepseek.com"


class _StructuredCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return make_material_summary()


class _TextCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs

        class Message:
            content = "mocked text"

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]

        return Response()


class _JsonCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs

        class Message:
            content = make_material_summary().model_dump_json()

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]

        return Response()


class _Chat:
    def __init__(self, completions) -> None:
        self.completions = completions


class _StructuredClient:
    def __init__(self, completions: _StructuredCompletions) -> None:
        self.chat = _Chat(completions)


class _TextClient:
    def __init__(self, completions: _TextCompletions) -> None:
        self.chat = _Chat(completions)


def test_generate_uses_injected_structured_client_without_live_api() -> None:
    completions = _StructuredCompletions()
    client = LLMClient(api_key="unused-test-key", model="mock-model")
    client._client = object()
    client._structured_client = _StructuredClient(completions)

    result = client.generate(
        MaterialSummary,
        [{"role": "user", "content": "local mocked request"}],
        max_retries=1,
        temperature=0.3,
    )

    assert result.facts
    assert completions.kwargs["model"] == "mock-model"
    assert completions.kwargs["response_model"] is MaterialSummary
    assert completions.kwargs["max_retries"] == 1
    assert client.get_usage()["calls"] == 1


def test_generate_uses_json_mode_for_deepseek_without_tool_choice() -> None:
    completions = _JsonCompletions()
    client = LLMClient(
        api_key="unused-test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
    )
    client._client = _TextClient(completions)
    client._structured_client = object()

    result = client.generate(
        MaterialSummary,
        [{"role": "user", "content": "return json"}],
        max_retries=1,
    )

    assert result.facts
    assert completions.kwargs["model"] == "deepseek-v4-flash"
    assert completions.kwargs["response_format"] == {"type": "json_object"}
    assert completions.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "tool_choice" not in completions.kwargs


def test_generate_text_uses_injected_text_client_without_live_api() -> None:
    completions = _TextCompletions()
    client = LLMClient(api_key="unused-test-key", model="mock-model")
    client._client = _TextClient(completions)
    client._structured_client = object()

    result = client.generate_text(
        [{"role": "user", "content": "write"}],
        max_tokens=123,
        temperature=0.4,
    )

    assert result == "mocked text"
    assert completions.kwargs["model"] == "mock-model"
    assert completions.kwargs["max_tokens"] == 123
    assert client.get_usage()["calls"] == 1

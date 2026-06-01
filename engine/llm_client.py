from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

from engine.utils import StructuredOutputValidationError, validate_structured_output


class LLMCallError(RuntimeError):
    """Raised when an LLM call fails or returns invalid structured output."""


@dataclass(frozen=True)
class LLMBudget:
    max_calls: int
    max_input_tokens: int
    max_output_tokens: int
    max_estimated_usd: float
    input_usd_per_1k_tokens: float
    output_usd_per_1k_tokens: float


class LLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        raw_base_url = base_url if base_url is not None else os.getenv("LLM_BASE_URL")
        self.base_url = normalize_base_url(raw_base_url)
        self.api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self._client: Any | None = None
        self._structured_client: Any | None = None
        self._usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        self._estimated_usd = 0.0
        self.live_enabled = _env_bool("LLM_LIVE_ENABLED", default=False)
        self.budget = LLMBudget(
            max_calls=_env_int("LLM_MAX_CALLS_PER_RUN", 25),
            max_input_tokens=_env_int("LLM_MAX_INPUT_TOKENS_PER_RUN", 500000),
            max_output_tokens=_env_int("LLM_MAX_OUTPUT_TOKENS_PER_RUN", 200000),
            max_estimated_usd=_env_float("LLM_MAX_ESTIMATED_USD_PER_RUN", 20.0),
            input_usd_per_1k_tokens=_env_float("LLM_INPUT_USD_PER_1K_TOKENS", 0.00015),
            output_usd_per_1k_tokens=_env_float("LLM_OUTPUT_USD_PER_1K_TOKENS", 0.0006),
        )

    def _ensure_clients(self) -> None:
        if self._client is not None and self._structured_client is not None:
            return
        if not self.api_key:
            raise LLMCallError(
                "LLM_API_KEY is not configured. Set it in .env or pass api_key to LLMClient."
            )
        if not self.live_enabled:
            raise LLMCallError(
                "LLM_LIVE_ENABLED is not true. Refusing to initialize a live LLM client."
            )
        try:
            import instructor
            from openai import OpenAI

            kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
            self._structured_client = instructor.from_openai(self._client)
        except Exception as exc:
            raise LLMCallError(f"Failed to initialize LLM client: {exc}") from exc

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens / 1000 * self.budget.input_usd_per_1k_tokens
            + output_tokens / 1000 * self.budget.output_usd_per_1k_tokens
        )

    def _check_budget(
        self,
        *,
        next_input_tokens: int = 0,
        next_output_tokens: int = 0,
        next_calls: int = 0,
    ) -> None:
        return

    def _message_tokens(self, messages: list[dict[str, str]]) -> int:
        return sum(self.count_tokens(msg.get("content", "")) for msg in messages)

    def _record_usage(self, input_tokens: int, output_tokens: int) -> None:
        self._usage["calls"] += 1
        self._usage["input_tokens"] += input_tokens
        self._usage["output_tokens"] += output_tokens
        self._estimated_usd += self._estimate_cost(input_tokens, output_tokens)

    def generate(
        self,
        response_model: Any,
        messages: list[dict[str, str]],
        max_retries: int = 3,
        temperature: float = 0.0,
    ) -> Any:
        self._ensure_clients()
        if self._uses_deepseek_json_mode():
            return self._generate_json_mode(
                response_model,
                messages,
                max_retries=max_retries,
                temperature=temperature,
            )

        input_tokens = self._message_tokens(messages)
        self._check_budget(next_input_tokens=input_tokens, next_calls=1)
        try:
            result = self._structured_client.chat.completions.create(
                model=self.model,
                response_model=response_model,
                messages=messages,
                max_retries=max_retries,
                temperature=temperature,
            )
            validated = validate_structured_output(
                result,
                response_model,
                "Structured LLM response",
            )
            output_tokens = self.count_tokens(str(validated))
            self._check_budget(
                next_input_tokens=input_tokens,
                next_output_tokens=output_tokens,
                next_calls=1,
            )
            self._record_usage(input_tokens, output_tokens)
            return validated
        except StructuredOutputValidationError as exc:
            raise LLMCallError(f"Structured LLM response failed validation: {exc}") from exc
        except LLMCallError:
            raise
        except Exception as exc:
            raise LLMCallError(
                "Structured LLM call failed: "
                + _friendly_provider_error(exc, self.base_url, self.model)
            ) from exc

    def _generate_json_mode(
        self,
        response_model: Any,
        messages: list[dict[str, str]],
        *,
        max_retries: int,
        temperature: float,
    ) -> Any:
        prepared_messages = self._json_mode_messages(response_model, messages)
        input_tokens = self._message_tokens(prepared_messages)
        self._check_budget(next_input_tokens=input_tokens, next_calls=1)
        last_exc: Exception | None = None

        for _ in range(max(1, max_retries)):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=prepared_messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise LLMCallError("DeepSeek JSON mode returned empty content.")
                raw = json.loads(content)
                validated = validate_structured_output(
                    raw,
                    response_model,
                    "DeepSeek JSON response",
                )
                output_tokens = self.count_tokens(content)
                self._check_budget(
                    next_input_tokens=input_tokens,
                    next_output_tokens=output_tokens,
                    next_calls=1,
                )
                self._record_usage(input_tokens, output_tokens)
                return validated
            except (json.JSONDecodeError, StructuredOutputValidationError, LLMCallError) as exc:
                last_exc = exc
            except Exception as exc:
                raise LLMCallError(
                    "DeepSeek JSON structured call failed: "
                    + _friendly_provider_error(exc, self.base_url, self.model)
                ) from exc

        raise LLMCallError(f"DeepSeek JSON structured call failed: {last_exc}") from last_exc

    def _json_mode_messages(
        self,
        response_model: Any,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        schema = _json_schema_for_model(response_model)
        instruction = (
            "Return JSON only. Do not wrap the answer in Markdown. "
            "All user-facing string values must be Simplified Chinese unless they are technical ids, URLs, model names, or variable keys. "
            "The JSON must match this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        return [{"role": "system", "content": instruction}, *messages]

    def generate_text(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.2,
    ) -> str:
        self._ensure_clients()
        input_tokens = self._message_tokens(messages)
        self._check_budget(
            next_input_tokens=input_tokens,
            next_output_tokens=max_tokens,
            next_calls=1,
        )
        try:
            request_kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if self._uses_deepseek_json_mode():
                request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
            response = self._client.chat.completions.create(
                **request_kwargs,
            )
            try:
                content = response.choices[0].message.content or ""
            except (AttributeError, IndexError, TypeError) as exc:
                raise LLMCallError(
                    "Text LLM response missing choices[0].message.content"
                ) from exc
            output_tokens = self.count_tokens(content)
            self._check_budget(
                next_input_tokens=input_tokens,
                next_output_tokens=output_tokens,
                next_calls=1,
            )
            self._record_usage(input_tokens, output_tokens)
            return content
        except LLMCallError:
            raise
        except Exception as exc:
            raise LLMCallError(
                "Text LLM call failed: "
                + _friendly_provider_error(exc, self.base_url, self.model)
            ) from exc

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def get_usage(self) -> dict[str, int]:
        return dict(self._usage)

    def _uses_deepseek_json_mode(self) -> bool:
        return bool(self.base_url and urlparse(self.base_url).netloc == "api.deepseek.com")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise LLMCallError(f"{name} must be an integer") from exc
    if value < 0:
        raise LLMCallError(f"{name} must be non-negative")
    return value


def normalize_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().rstrip("/")
    if not cleaned:
        return None

    parsed = urlparse(cleaned)
    path = parsed.path.rstrip("/")
    if parsed.netloc == "platform.deepseek.com":
        return "https://api.deepseek.com"
    if parsed.netloc == "api.deepseek.com" and path.endswith("/anthropic"):
        path = path[: -len("/anthropic")] or ""
        return urlunparse(parsed._replace(path=path, params="", query="", fragment="")).rstrip("/")
    for suffix in ("/v1/chat/completions", "/chat/completions"):
        if path.endswith(suffix):
            path = path[: -len("/chat/completions")] or ""
            cleaned = urlunparse(parsed._replace(path=path, params="", query="", fragment=""))
            return cleaned.rstrip("/") or None

    if parsed.netloc == "api.openai.com" and path in {"", "/"}:
        return urlunparse(parsed._replace(path="/v1", params="", query="", fragment=""))
    return cleaned


def _friendly_provider_error(exc: Exception, base_url: str | None, model: str) -> str:
    message = str(exc)
    error_name = type(exc).__name__
    if "404" in message or "NotFound" in error_name:
        endpoint = base_url or "OpenAI 默认地址"
        return (
            "服务返回 404。通常是 Base URL 或模型名不对。"
            f"当前 Base URL={endpoint}，模型={model}。"
            "Base URL 只填服务根地址，例如 https://api.openai.com/v1 "
            "或服务商给的 OpenAI-compatible base，"
            "不要填完整 /chat/completions。"
        )
    if "401" in message or "Unauthorized" in error_name:
        return "服务返回 401。API Key 无效、过期，或不属于当前 Base URL。"
    if "403" in message or "Permission" in error_name:
        return "服务返回 403。当前 API Key 没有这个模型或接口权限。"
    if "Thinking mode does not support this tool_choice" in message:
        return (
            "DeepSeek thinking mode 不支持 tool_choice。"
            "已为 DeepSeek 增加 JSON 模式兼容；"
            "请刷新页面后重新保存配置并重试。"
        )
    return message


def _json_schema_for_model(response_model: Any) -> dict[str, Any]:
    if hasattr(response_model, "model_json_schema"):
        return response_model.model_json_schema()
    try:
        from pydantic import TypeAdapter

        return TypeAdapter(response_model).json_schema()
    except Exception:
        return {"type": "object"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise LLMCallError(f"{name} must be a number") from exc
    if value < 0:
        raise LLMCallError(f"{name} must be non-negative")
    return value

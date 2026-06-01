from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, TypeAdapter, ValidationError

T = TypeVar("T")


class StructuredOutputValidationError(ValueError):
    """Raised when persisted or LLM-produced structured data fails validation."""


def data_root(data_dir: str | Path | None = None) -> Path:
    return Path(data_dir or os.getenv("DATA_DIR", "data"))


def generate_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}{stamp}_{uuid4().hex[:8]}"


def format_timestamp(dt: datetime | None = None) -> str:
    value = dt or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_case_dir(case_id: str, data_dir: str | Path | None = None) -> Path:
    case_dir = data_root(data_dir) / "cases" / case_id
    for subdir in ("uploads", "intermediate", "outputs"):
        (case_dir / subdir).mkdir(parents=True, exist_ok=True)
    return case_dir


def get_case_path(case_id: str, filename: str, data_dir: str | Path | None = None) -> Path:
    return ensure_case_dir(case_id, data_dir) / filename


def to_jsonable(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [to_jsonable(item) for item in data]
    if isinstance(data, tuple):
        return [to_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {str(key): to_jsonable(value) for key, value in data.items()}
    return data


def save_json(data: Any, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(to_jsonable(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(target)
    return target


def load_json(path: str | Path, model_class: type[T] | Any | None = None) -> T | Any:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if model_class is None:
        return raw
    return validate_structured_output(raw, model_class, f"JSON file {path}")


def save_text(text: str, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(target)
    return target


def validate_structured_output(
    data: Any,
    model_class: type[T] | Any,
    source: str = "Structured output",
) -> T:
    try:
        return TypeAdapter(model_class).validate_python(data)
    except ValidationError as exc:
        model_name = getattr(model_class, "__name__", repr(model_class))
        missing_fields = [
            ".".join(str(part) for part in error["loc"])
            for error in exc.errors()
            if error.get("type") == "missing"
        ]
        missing_note = (
            f"; missing required keys: {', '.join(missing_fields)}"
            if missing_fields
            else ""
        )
        raise StructuredOutputValidationError(
            f"{source} failed validation for {model_name}{missing_note}"
        ) from exc


def load_prompt(name: str) -> str:
    from engine.language import is_english

    prompt_root = Path(__file__).resolve().parents[1] / "prompts"
    localized_path = prompt_root / "en" / name
    prompt_path = localized_path if is_english() and localized_path.exists() else prompt_root / name
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def render_prompt(template: str, **values: Any) -> str:
    from engine.language import user_prompt_preamble

    rendered = template
    for key, value in values.items():
        if isinstance(value, BaseModel):
            replacement = json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2)
        elif isinstance(value, (dict, list)):
            replacement = json.dumps(to_jsonable(value), ensure_ascii=False, indent=2)
        else:
            replacement = str(value)
        rendered = rendered.replace("{" + key + "}", replacement)
    return user_prompt_preamble() + "\n\n" + rendered

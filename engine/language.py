from __future__ import annotations

import os


SUPPORTED_LANGUAGES = {"zh", "en"}
DEFAULT_LANGUAGE = "zh"


def normalize_language(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"en", "english", "en-us", "en_us"}:
        return "en"
    if normalized in {"zh", "cn", "chinese", "zh-cn", "zh_cn", "简体中文", "中文"}:
        return "zh"
    return DEFAULT_LANGUAGE


def get_output_language() -> str:
    return normalize_language(
        os.getenv("LLM_OUTPUT_LANGUAGE")
        or os.getenv("APP_LANGUAGE")
        or os.getenv("UI_LANGUAGE")
        or DEFAULT_LANGUAGE
    )


def set_output_language(language: str) -> str:
    normalized = normalize_language(language)
    os.environ["LLM_OUTPUT_LANGUAGE"] = normalized
    os.environ["APP_LANGUAGE"] = normalized
    return normalized


def language_name(language: str | None = None) -> str:
    return "English" if normalize_language(language or get_output_language()) == "en" else "简体中文"


def is_english(language: str | None = None) -> bool:
    return normalize_language(language or get_output_language()) == "en"


def json_output_instruction(schema_name: str, *, action: str | None = None) -> str:
    target = get_output_language()
    if target == "en":
        prefix = action or f"Return only a valid {schema_name} JSON object"
        return (
            f"{prefix}; all user-facing string fields must be written in natural English. "
            "Keep technical IDs, model names, URLs, branch_id, agent_id, and variable keys as ASCII when useful."
        )
    prefix = action or f"只返回一个合法 {schema_name} JSON 对象"
    return f"{prefix}；所有面向用户的字符串字段使用简体中文。"


def prompt_language_instruction(*, markdown: bool = False) -> str:
    if get_output_language() == "en":
        if markdown:
            return (
                "Write the full Markdown report in English. Keep technical IDs, model names, URLs, "
                "and Brier-style metric names unchanged when appropriate."
            )
        return (
            "All user-facing JSON string fields must be written in English. "
            "Keep technical IDs and variable keys as ASCII when useful."
        )
    if markdown:
        return "完整 Markdown 报告必须使用简体中文。只有技术 ID、模型名、URL 和 Brier 等指标名在必要时保留原文。"
    return "JSON 中所有面向用户的字符串必须使用简体中文。技术 ID 和变量 key 可保留 ASCII。"


def user_prompt_preamble() -> str:
    if get_output_language() == "en":
        return (
            "# Output language\n"
            "Use English for every user-facing title, explanation, summary, signal, action, "
            "report section, and natural-language value in this response. Preserve schema keys and IDs."
        )
    return "# 输出语言\n所有面向用户的标题、解释、摘要、信号、动作、报告章节和自然语言字段都使用简体中文。"

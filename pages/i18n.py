from __future__ import annotations

import os
from typing import Any

import streamlit as st

from engine.language import normalize_language, set_output_language
from engine.local_llm_config import load_saved_llm_config, save_language_config


LANGUAGE_OPTIONS = {
    "zh": "中文",
    "en": "English",
}

STAGE_EN = {
    "配置文件读取失败": "Config read failed",
    "配置损坏": "Config damaged",
    "预测卡片": "Forecast cards",
    "世界比较": "World comparison",
    "推演完成": "Simulation complete",
    "智能体已生成": "Agents generated",
    "分支已生成": "Branches generated",
    "初始世界": "Base world",
    "材料摘要": "Material summary",
    "项目已创建": "Project created",
    "空": "Empty",
}


def init_language() -> str:
    try:
        if "ui_language" not in st.session_state:
            saved = load_saved_llm_config()
            st.session_state.ui_language = normalize_language(
                os.getenv("APP_LANGUAGE")
                or os.getenv("LLM_OUTPUT_LANGUAGE")
                or saved.get("ui_language")
                or saved.get("output_language")
            )
        language = normalize_language(st.session_state.ui_language)
        st.session_state.ui_language = language
    except Exception:
        language = normalize_language(os.getenv("APP_LANGUAGE") or os.getenv("LLM_OUTPUT_LANGUAGE"))
    set_output_language(language)
    return language


def current_language() -> str:
    try:
        if "ui_language" not in st.session_state:
            return init_language()
        return normalize_language(st.session_state.ui_language)
    except Exception:
        return normalize_language(os.getenv("APP_LANGUAGE") or os.getenv("LLM_OUTPUT_LANGUAGE"))


def is_english() -> bool:
    return current_language() == "en"


def ui_text(zh: str, en: str | None = None) -> str:
    return en if is_english() and en is not None else zh


def format_text(zh: str, en: str | None = None, **values: Any) -> str:
    return ui_text(zh, en).format(**values)


def stage_text(value: str) -> str:
    return STAGE_EN.get(value, value) if is_english() else value


def render_language_selector(parent: Any = st.sidebar) -> None:
    language = current_language()
    selected = parent.selectbox(
        ui_text("界面语言", "Interface language"),
        options=list(LANGUAGE_OPTIONS),
        index=list(LANGUAGE_OPTIONS).index(language),
        format_func=lambda value: LANGUAGE_OPTIONS[value],
        key="ui_language_selectbox",
    )
    selected = normalize_language(selected)
    if selected != language:
        st.session_state.ui_language = selected
        set_output_language(selected)
        save_language_config(ui_language=selected, output_language=selected)
        st.rerun()

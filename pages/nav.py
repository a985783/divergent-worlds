from __future__ import annotations

from typing import Any

import streamlit as st


_PAGES: dict[str, Any] = {}


def register_pages(pages: dict[str, Any]) -> None:
    _PAGES.clear()
    _PAGES.update(pages)


def switch_to(page_key: str) -> None:
    # Fallback routing for legacy page keys
    legacy_keys = {"setup", "materials", "base_world", "forks", "simulation", "comparison", "report", "overview"}
    target_key = "workbench" if page_key in legacy_keys else page_key
    
    page = _PAGES.get(target_key)
    if page is None:
        st.error(f"页面未注册：{page_key} (已映射为 {target_key})")
        return
    st.switch_page(page)

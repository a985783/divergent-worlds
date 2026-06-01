import os
from importlib import reload
from typing import Any

import streamlit as st

from engine.case_store import list_case_records, load_case_state
from engine.llm_client import LLMCallError, LLMClient, normalize_base_url
from engine.local_llm_config import (
    apply_saved_llm_config,
    delete_saved_llm_config,
    load_saved_llm_config,
    save_llm_config,
)
from pages import (
    forecast_ledger,
    nav,
    project_records,
    simulation_workbench,
    ui_helpers,
)

def init_session() -> None:
    apply_saved_llm_config()
    defaults = {
        "case_config": None,
        "demo_case_loaded": False,
        "demo_material_paths": [],
        "material_summary": None,
        "material_preview": [],
        "base_world": None,
        "branches": [],
        "profiles": [],
        "actors_by_branch": {},
        "simulation_logs": {},
        "divergence": None,
        "forecast_cards": [],
        "report": "",
        "llm_client": None,
        "llm_client_init_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.llm_client is None:
        refresh_llm_client()

def refresh_llm_client() -> None:
    try:
        st.session_state.llm_client = LLMClient()
        st.session_state.llm_client_init_error = None
    except (LLMCallError, ValueError) as exc:
        st.session_state.llm_client = None
        st.session_state.llm_client_init_error = str(exc)

def render_llm_config_panel(parent: Any, *, expanded: bool, key_prefix: str) -> None:
    llm_client = st.session_state.llm_client
    ready, blockers = ui_helpers.llm_is_ready(llm_client)
    saved_config = load_saved_llm_config()
    with parent.expander("⚙️ 配置大模型 API", expanded=expanded):
        st.caption("保存后会记住到本机用户配置，下次启动自动读取。")
        current_model = getattr(llm_client, "model", os.getenv("LLM_MODEL", "gpt-4o-mini"))
        current_base_url = getattr(llm_client, "base_url", os.getenv("LLM_BASE_URL", ""))
        live_enabled = getattr(llm_client, "live_enabled", False)
        existing_key = bool(getattr(llm_client, "api_key", None) or os.getenv("LLM_API_KEY"))
        persisted_key = bool(saved_config.get("api_key"))

        if ready:
            st.success("已连接：真实模型调用可用。")
            if persisted_key:
                st.caption("API 密钥已保存在本机，下次启动会自动读取。")
        elif existing_key and not live_enabled:
            st.warning("API 密钥已有，但真实调用开关未启用。")
            if st.button(
                "一键启用真实模型调用",
                type="primary",
                width="stretch",
                key=f"{key_prefix}_enable_live",
            ):
                os.environ["LLM_LIVE_ENABLED"] = "true"
                save_llm_config(
                    model=current_model or "gpt-4o-mini",
                    base_url=current_base_url or "",
                    api_key=os.getenv("LLM_API_KEY"),
                    live_enabled=True,
                )
                refresh_llm_client()
                st.rerun()
        elif blockers:
            st.warning("当前阻止原因：" + " ".join(blockers))

        if st.button("套用 DeepSeek 兼容接口设置", width="stretch", key=f"{key_prefix}_deepseek"):
            os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
            os.environ["LLM_MODEL"] = "deepseek-v4-flash"
            os.environ["LLM_LIVE_ENABLED"] = "true" if existing_key else "false"
            save_llm_config(
                model="deepseek-v4-flash",
                base_url="https://api.deepseek.com",
                api_key=os.getenv("LLM_API_KEY"),
                live_enabled=existing_key,
            )
            refresh_llm_client()
            st.rerun()

        model = st.text_input(
            "模型",
            value=current_model or "gpt-4o-mini",
            key=f"{key_prefix}_model",
        )
        base_url = st.text_input(
            "接口地址（可选）",
            value=current_base_url or "",
            key=f"{key_prefix}_base_url",
        )
        st.caption(
            "本项目使用兼容 OpenAI 格式的接口。DeepSeek 填 "
            "https://api.deepseek.com，不要填 /anthropic。"
        )
        api_key = st.text_input(
            "API 密钥",
            type="password",
            placeholder="已保存/已配置" if existing_key else "sk-...",
            key=f"{key_prefix}_api_key",
        )
        enable_live = st.checkbox(
            "保存后启用真实模型调用",
            value=True,
            key=f"{key_prefix}_enable_live_checkbox",
        )
        remember_local = st.checkbox(
            "记住到本机，下次自动读取",
            value=True,
            key=f"{key_prefix}_remember_local",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "保存并启用",
                type="primary",
                width="stretch",
                key=f"{key_prefix}_save",
            ):
                normalized_model = model.strip() or "gpt-4o-mini"
                normalized_base_url = normalize_base_url(base_url) or ""
                os.environ["LLM_MODEL"] = normalized_model
                os.environ["LLM_BASE_URL"] = normalized_base_url
                if api_key.strip():
                    os.environ["LLM_API_KEY"] = api_key.strip()
                has_key = bool(api_key.strip() or os.getenv("LLM_API_KEY"))
                os.environ["LLM_LIVE_ENABLED"] = "true" if enable_live and has_key else "false"
                if remember_local:
                    save_llm_config(
                        model=normalized_model,
                        base_url=normalized_base_url,
                        api_key=api_key.strip() or os.getenv("LLM_API_KEY"),
                        live_enabled=enable_live and has_key,
                    )
                else:
                    delete_saved_llm_config()
                refresh_llm_client()
                st.rerun()
        with col2:
            if st.button("清除 Key", width="stretch", key=f"{key_prefix}_clear_key"):
                os.environ.pop("LLM_API_KEY", None)
                os.environ["LLM_LIVE_ENABLED"] = "false"
                delete_saved_llm_config()
                refresh_llm_client()
                st.rerun()
        if st.button("测试连接", width="stretch", key=f"{key_prefix}_test"):
            ready_now, blockers_now = ui_helpers.llm_is_ready(st.session_state.llm_client)
            if not ready_now:
                st.error("还不能测试：" + " ".join(blockers_now))
            else:
                try:
                    with st.spinner("正在测试模型连接..."):
                        st.session_state.llm_client.generate_text(
                            [{"role": "user", "content": "只回复：连接正常"}],
                            max_tokens=8,
                            temperature=0,
                        )
                    st.success("连接成功。")
                except LLMCallError as exc:
                    st.error(str(exc))


def render_sidebar_llm_config() -> None:
    ready, _ = ui_helpers.llm_is_ready(st.session_state.llm_client)
    render_llm_config_panel(st.sidebar, expanded=not ready, key_prefix="sidebar_llm")

def load_saved_case(case_id: str) -> None:
    for key, value in load_case_state(case_id).items():
        st.session_state[key] = value

def render_resume_panel(parent: Any = st.sidebar, *, key_prefix: str = "sidebar_resume") -> None:
    records = list_case_records()
    if not records:
        return
    with parent.expander("📂 恢复历史项目", expanded=False):
        labels = {
            record.case_id: f"{record.case_name} · {record.stage} · {record.case_id}"
            for record in records
        }
        selected = st.selectbox(
            "选择保存记录",
            [record.case_id for record in records],
            format_func=lambda case_id: labels[case_id],
            key=f"{key_prefix}_select",
        )
        if st.button("恢复到当前进度", type="primary", width="stretch", key=f"{key_prefix}_restore"):
            try:
                load_saved_case(selected)
                st.success("已恢复保存记录。")
                st.rerun()
            except Exception as exc:
                st.error(f"恢复失败：{exc}")


def main() -> None:
    st.set_page_config(
        page_title="平行世界推演台",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    if not hasattr(ui_helpers, "inject_app_css"):
        reload(ui_helpers)
    init_session()
    ui_helpers.inject_app_css()

    p_records = st.Page(
        project_records.render,
        title="首页",
        icon="🏠",
        url_path="home",
        default=True,
    )
    p_workbench = st.Page(
        simulation_workbench.render,
        title="推演工作台",
        icon="🌍",
        url_path="workbench",
    )
    p_ledger = st.Page(
        forecast_ledger.render,
        title="预测账本",
        icon="📒",
        url_path="ledger",
    )

    nav.register_pages({
        "home": p_records,
        "workbench": p_workbench,
        "ledger": p_ledger,
    })

    pg = st.navigation({
        "工作台": [p_records, p_workbench, p_ledger]
    })
    
    st.sidebar.markdown("### 控制面板")
    render_sidebar_llm_config()
    ui_helpers.render_sidebar_llm_status(st.session_state.llm_client)
    if st.sidebar.button("🔄 重新读取 LLM 配置", width="stretch"):
        refresh_llm_client()
        st.rerun()
    render_resume_panel()

    pg.run()

    ui_helpers.render_llm_warning_panel(
        st.session_state.llm_client,
        st.session_state.llm_client_init_error,
    )

if __name__ == "__main__":
    main()

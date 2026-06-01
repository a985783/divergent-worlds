from __future__ import annotations

from collections.abc import Callable
from html import escape
from typing import Any

import streamlit as st
from pages import i18n
from pages.state_manager import state

from engine.llm_client import LLMCallError


WORKFLOW_STEPS = [
    {
        "label": "创建项目",
        "state_key": "case_config",
        "summary": "确定问题、推演窗口、分支数和智能体数量。",
        "next_action": "创建后进入材料页，把现实背景、数据或笔记放进来。",
    },
    {
        "label": "材料解析",
        "state_key": "material_summary",
        "summary": "把上传文件或粘贴文本抽取成事实、变量、不确定性。",
        "next_action": "确认材料摘要后生成当前世界状态。",
    },
    {
        "label": "初始世界",
        "state_key": "base_world",
        "summary": "建立现实世界基线，锁定不可随意改写的事实。",
        "next_action": "确认基线后生成多个平行分支。",
    },
    {
        "label": "分支编辑",
        "state_key": "branches",
        "summary": "生成并校验互相有差异的世界分支。",
        "next_action": "确认分支后运行智能体推演。",
    },
    {
        "label": "运行推演",
        "state_key": "simulation_logs",
        "summary": "为每个分支生成行动者，并按时间窗口推进状态。",
        "next_action": "推演完成后比较世界分歧。",
    },
    {
        "label": "世界比较",
        "state_key": "divergence",
        "summary": "比较分支概率、关键变量和下一步观察信号。",
        "next_action": "确认比较后生成预测卡片和报告。",
    },
    {
        "label": "预测报告",
        "state_key": "report",
        "summary": "输出可下载报告、预测卡片和验证信号。",
        "next_action": "把预测写入账本并持续更新现实结果。",
    },
    {
        "label": "预测账本",
        "state_key": "forecast_cards",
        "summary": "跟踪预测是否被支持、失败或暂无信息，并计算 Brier。",
        "next_action": "定期补录现实反馈，让系统形成校准记录。",
    },
]


def inject_app_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=swap');
        
        /* Hide Streamlit chrome that belongs to hosting/dev, not this product UI. */
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        footer {
            visibility: hidden !important;
            height: 0 !important;
        }
        header {
            background: transparent !important;
        }
        [data-testid="stAppDeployButton"] {
            display: none !important;
        }

        /* Global Font & Reset. Keep this scoped; Streamlit icons use ligature fonts. */
        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"],
        .block-container {
            font-family: 'Outfit', sans-serif !important;
        }
        .material-symbols-rounded,
        .material-symbols-outlined,
        .material-symbols-sharp,
        .material-icons,
        .material-icons-round,
        .material-icons-outlined,
        [class*="material-symbols"],
        [class*="material-icons"] {
            font-family: 'Material Symbols Rounded', 'Material Icons' !important;
            font-weight: normal !important;
            font-style: normal !important;
            font-size: 20px !important;
            line-height: 1 !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            display: inline-block !important;
            white-space: nowrap !important;
            word-wrap: normal !important;
            direction: ltr !important;
            -webkit-font-feature-settings: 'liga' !important;
            -webkit-font-smoothing: antialiased !important;
            font-feature-settings: 'liga' !important;
        }
        span[data-testid="stIconMaterial"] {
            display: none !important;
        }
        
        /* Main Container */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 4rem;
            max-width: 1240px;
        }
        
        /* Sidebar Glassmorphism */
        [data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.7) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        
        /* Hero Section */
        .dw-hero {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .dw-kicker {
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .dw-title {
            color: #f8fafc;
            font-size: 1.45rem;
            line-height: 1.2;
            font-weight: 750;
            margin: 6px 0 8px 0;
        }
        .dw-subtitle {
            color: #cbd5e1;
            font-size: 0.95rem;
            line-height: 1.45;
            margin: 0;
            font-weight: 300;
        }
        
        /* Step Cards */
        .dw-step-card {
            background: rgba(30, 41, 59, 0.5);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-left: 4px solid #3b82f6;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 8px 0 12px 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .dw-location {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 8px;
            padding: 10px 14px;
            margin: 8px 0 10px 0;
            color: #cbd5e1;
            font-size: 0.9rem;
        }
        .dw-home-primary {
            border: 1px solid rgba(59, 130, 246, 0.42);
            background: rgba(59, 130, 246, 0.14);
            border-left: 4px solid #3b82f6;
            border-radius: 8px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }
        .project-center-hero {
            display: grid;
            grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.85fr);
            gap: 18px;
            align-items: stretch;
            border: 1px solid rgba(148, 163, 184, 0.2);
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.94), rgba(17, 24, 39, 0.86)),
                radial-gradient(circle at 80% 20%, rgba(45, 212, 191, 0.18), transparent 34%);
            border-radius: 8px;
            padding: 22px;
            margin-bottom: 16px;
        }
        .project-center-hero h1 {
            color: #f8fafc;
            font-size: 2rem;
            line-height: 1.15;
            letter-spacing: 0;
            margin: 8px 0;
        }
        .project-center-hero p {
            color: #cbd5e1;
            max-width: 760px;
            line-height: 1.5;
            margin: 0;
        }
        .project-center-stats {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
        }
        .project-center-stats div {
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.5);
            padding: 10px 12px;
        }
        .project-center-stats strong {
            display: block;
            color: #f8fafc;
            font-size: 1.15rem;
            line-height: 1.2;
        }
        .project-center-stats span {
            display: block;
            color: #94a3b8;
            font-size: 0.78rem;
            margin-top: 3px;
        }
        .dw-step-card strong {
            color: #f8fafc;
            font-weight: 600;
        }
        .dw-muted {
            color: #94a3b8;
        }

        }
        
        /* Chips */
        .dw-chip {
            display: inline-block;
            padding: 4px 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.03);
            color: #e2e8f0;
            font-size: 0.85rem;
            font-weight: 500;
            margin: 0 8px 8px 0;
            backdrop-filter: blur(4px);
            transition: all 0.2s ease;
        }
        .dw-chip:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-1px);
        }
        .dw-chip-good {
            border-color: rgba(52, 211, 153, 0.3);
            background: rgba(52, 211, 153, 0.1);
            color: #6ee7b7;
        }
        .dw-chip-warn {
            border-color: rgba(251, 191, 36, 0.3);
            background: rgba(251, 191, 36, 0.1);
            color: #fcd34d;
        }
        
        /* Data Cards */
        .dw-card {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }
        .dw-card:hover {
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        }
        .dw-card-title {
            color: #f8fafc;
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 8px;
        }
        .dw-card-body {
            color: #cbd5e1;
            line-height: 1.6;
        }
        
        /* Streamlit Element Overrides */
        
        /* Buttons */
        div.stButton > button:first-child {
            border-radius: 8px;
            font-weight: 600;
            letter-spacing: 0;
            transition: all 0.15s ease;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        div.stButton > button:first-child:hover {
            transform: translateY(-1px);
            border-color: #3b82f6;
        }
        [data-testid="stBaseButton-primary"] {
            background: #2563eb !important;
            border-color: #60a5fa !important;
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.28) !important;
        }
        [data-testid="stBaseButton-secondary"] {
            background: rgba(15, 23, 42, 0.82) !important;
            border-color: rgba(148, 163, 184, 0.35) !important;
            color: #e5e7eb !important;
        }
        
        /* Metric Styling */
        [data-testid="stMetricValue"] {
            font-weight: 800;
            background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        [data-testid="stMetricLabel"] {
            font-weight: 500;
            color: #94a3b8;
            letter-spacing: 0.03em;
        }
        
        /* Inputs */
        .stTextInput > div > div > input, 
        .stTextArea > div > div > textarea, 
        .stSelectbox > div > div > div {
            background: rgba(15, 23, 42, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            color: #f8fafc !important;
            transition: all 0.2s ease;
        }
        .stTextInput > div > div > input:focus, 
        .stTextArea > div > div > textarea:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            font-weight: 600 !important;
            color: #e2e8f0 !important;
            background: rgba(30, 41, 59, 0.3) !important;
            border-radius: 8px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def workflow_completion(session_state: Any) -> list[bool]:
    completion: list[bool] = []
    for step in WORKFLOW_STEPS:
        value = session_state.get(step["state_key"])
        completion.append(bool(value))
    return completion




def render_chip_row(items: list[str], *, tone: str = "neutral") -> None:
    if not items:
        st.caption(i18n.ui_text("暂无", "None yet"))
        return
    class_name = "dw-chip"
    if tone == "good":
        class_name = "dw-chip dw-chip-good"
    elif tone == "warn":
        class_name = "dw-chip dw-chip-warn"
    html = "".join(f'<span class="{class_name}">{escape(str(item))}</span>' for item in items)
    st.markdown(html, unsafe_allow_html=True)


def render_list_panel(title: str, items: list[str], *, empty: str = "暂无") -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if not items:
            st.caption(i18n.ui_text(empty, "None yet") if empty == "暂无" else empty)
            return
        for item in items:
            st.markdown(f"- {item}")


def _next_incomplete_label(completion: list[bool]) -> str | None:
    for done, step in zip(completion, WORKFLOW_STEPS):
        if not done:
            return step["label"]
    return None


def _next_work_page_index(session_state: Any) -> int | None:
    if not session_state.get("case_config"):
        return 2
    page_by_state_key = {
        "case_config": 2,
        "material_summary": 3,
        "base_world": 4,
        "branches": 5,
        "simulation_logs": 6,
        "divergence": 7,
        "report": 8,
        "forecast_cards": 9,
    }
    for step in WORKFLOW_STEPS:
        state_key = step["state_key"]
        if state_key == "report":
            done = bool(session_state.get("report") or session_state.get("forecast_cards"))
        else:
            done = bool(session_state.get(state_key))
        if not done:
            return page_by_state_key[state_key]
    return 1


def llm_is_ready(llm_client: Any | None) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if llm_client is None:
        return False, [
            i18n.ui_text(
                "模型客户端初始化失败，请检查环境变量格式。",
                "Model client initialization failed. Check environment variable format.",
            )
        ]

    if not getattr(llm_client, "live_enabled", False):
        blockers.append(i18n.ui_text("需要设置 LLM_LIVE_ENABLED=true。", "Set LLM_LIVE_ENABLED=true."))
    if not getattr(llm_client, "api_key", None):
        blockers.append(i18n.ui_text("需要设置 LLM_API_KEY。", "Set LLM_API_KEY."))

    return not blockers, blockers


def render_llm_warning_panel(llm_client: Any | None, init_error: str | None = None) -> None:
    _, blockers = llm_is_ready(llm_client)

    with st.expander(i18n.ui_text("隐私 / API 密钥 / 调用状态", "Privacy / API key / Call status"), expanded=False):
        st.warning(
            i18n.ui_text(
                "隐私提醒：点击模型调用步骤后，当前项目材料、问题、"
                "分支和推演上下文会发送到你配置的兼容 OpenAI 格式的模型服务；"
                "不要上传密钥、"
                "身份证件、客户隐私或其他敏感原文。",
                "Privacy reminder: when you run model-backed steps, project materials, questions, "
                "branches, and simulation context are sent to your configured OpenAI-compatible model service. "
                "Do not upload secrets, identity documents, customer privacy, or sensitive raw text.",
            )
        )

        if init_error:
            st.error(i18n.format_text("模型客户端初始化失败：{error}", "Model client initialization failed: {error}", error=init_error))

        if llm_client is None:
            return

        usage = llm_client.get_usage()
        estimated_usd = float(getattr(llm_client, "_estimated_usd", 0.0))

        col1, col2, col3 = st.columns(3)
        col1.metric(
            i18n.ui_text("真实模型", "Live model"),
            i18n.ui_text("已启用", "Enabled") if llm_client.live_enabled else i18n.ui_text("未启用", "Disabled"),
        )
        col2.metric(
            i18n.ui_text("API 密钥", "API key"),
            i18n.ui_text("已配置", "Configured") if llm_client.api_key else i18n.ui_text("缺失", "Missing"),
        )
        col3.metric(i18n.ui_text("模型", "Model"), llm_client.model)

        st.caption(
            i18n.format_text(
                "本次会话用量：调用 {calls} 次 · 输入 {input_tokens} · 输出 {output_tokens} · 预估 ${usd:.4f}",
                "Session usage: {calls} calls · input {input_tokens} · output {output_tokens} · estimated ${usd:.4f}",
                calls=usage["calls"],
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                usd=estimated_usd,
            )
        )

        if blockers:
            st.error(i18n.ui_text("LLM 步骤当前会被阻止：", "LLM steps are currently blocked: ") + " ".join(blockers))
        else:
            st.success(i18n.ui_text("LLM 配置可用。", "LLM configuration is ready."))


def render_sidebar_llm_status(llm_client: Any | None) -> None:
    ready, blockers = llm_is_ready(llm_client)
    status = i18n.ui_text("可用", "available") if ready else i18n.ui_text("受阻", "blocked")
    st.sidebar.caption(i18n.format_text("模型状态：{status}", "Model status: {status}", status=status))
    if blockers:
        st.sidebar.warning(blockers[0])

    if llm_client is None:
        return

    usage = llm_client.get_usage()
    st.sidebar.caption(
        i18n.format_text(
            "模型调用：{calls} 次 | 输入 {input_tokens} / 输出 {output_tokens}",
            "Model calls: {calls} | input {input_tokens} / output {output_tokens}",
            calls=usage["calls"],
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
    )


def run_llm_action(
    action_key: str,
    label: str,
    action: Callable[[], Any],
    *,
    spinner: str | None = None,
    button_type: str = "primary",
    disabled: bool = False,
    disabled_reason: str | None = None,
    use_container_width: bool = True,
    show_notice: bool = True,
) -> bool:
    """Run one LLM-backed UI action with preflight, retry, and visible errors."""

    retry_key = f"{action_key}_retry_requested"
    retry_requested = bool(state.get_dynamic(retry_key, False))
    if retry_requested:
        state.set_dynamic(retry_key, False)

    if show_notice:
        st.caption(
            i18n.ui_text(
                "该步骤会调用外部模型；请确认材料中没有敏感原文。",
                "This step calls an external model; make sure materials contain no sensitive raw text.",
            )
        )
    button_width = "stretch" if use_container_width else "content"
    clicked = st.button(label, type=button_type, disabled=disabled, width=button_width)
    should_run = clicked or retry_requested

    if not should_run:
        _render_retry_controls(action_key, label)
        return False

    if disabled:
        st.warning(disabled_reason or i18n.ui_text("当前状态下不能运行该步骤。", "This step cannot run in the current state."))
        _render_retry_controls(action_key, label)
        return False

    llm_client = state.llm_client
    ready, blockers = llm_is_ready(llm_client)
    if not ready:
        _store_action_error(
            action_key,
            i18n.ui_text("LLM 配置未就绪：", "LLM configuration is not ready: ") + " ".join(blockers),
            i18n.ui_text(
                "更新 .env 或环境变量后，在侧边栏点击“重新读取 LLM 配置”，再重试。",
                "After updating .env or environment variables, click Reload LLM settings in the sidebar and retry.",
            ),
        )
        _render_retry_controls(action_key, label)
        return False

    try:
        if spinner:
            with st.spinner(spinner):
                action()
        else:
            action()
        _clear_action_error(action_key)
        return True
    except LLMCallError as exc:
        _store_action_error(action_key, str(exc), _llm_recovery_hint(str(exc)))
        _render_retry_controls(action_key, label)
        return False
    except Exception as exc:
        _store_action_error(
            action_key,
            str(exc),
            i18n.ui_text("修正输入或配置后可以重试该步骤。", "Fix the input or configuration, then retry this step."),
        )
        _render_retry_controls(action_key, label)
        return False


def run_act_action(
    action_key: str,
    label: str,
    action: Callable[[], Any],
    **kwargs: Any,
) -> bool:
    """Run an LLM-backed act action and rerun on success so the wizard rail refreshes immediately."""
    ran = run_llm_action(action_key, label, action, **kwargs)
    if ran:
        st.rerun()
    return ran


def _llm_recovery_hint(message: str) -> str:
    if "LLM_API_KEY" in message:
        return (
            i18n.ui_text(
                "设置 LLM_API_KEY 后，在侧边栏点击“重新读取 LLM 配置”，再重试。",
                "Set LLM_API_KEY, click Reload LLM settings in the sidebar, then retry.",
            )
        )
    if "LLM_LIVE_ENABLED" in message:
        return (
            i18n.ui_text(
                "设置 LLM_LIVE_ENABLED=true 后，在侧边栏点击“重新读取 LLM 配置”，再重试。",
                "Set LLM_LIVE_ENABLED=true, click Reload LLM settings in the sidebar, then retry.",
            )
        )
    return (
        i18n.ui_text(
            "检查模型服务、网络、结构化输出或输入材料后，可以重试该步骤。",
            "Check the model service, network, structured output, or input materials, then retry.",
        )
    )


def _store_action_error(action_key: str, message: str, hint: str) -> None:
    state.set_dynamic(f"{action_key}_last_error", {"message": message, "hint": hint})


def _clear_action_error(action_key: str) -> None:
    state.set_dynamic(f"{action_key}_last_error", None)


def _render_retry_controls(action_key: str, label: str) -> None:
    error = state.get_dynamic(f"{action_key}_last_error")
    if not error:
        return

    st.error(i18n.format_text("{label} 失败：{message}", "{label} failed: {message}", label=label, message=error["message"]))
    st.caption(error["hint"])
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(i18n.ui_text("重试该步骤", "Retry this step"), key=f"{action_key}_retry", type="primary"):
            state.set_dynamic(f"{action_key}_retry_requested", True)
            st.rerun()
    with col2:
        if st.button(i18n.ui_text("清除错误", "Clear error"), key=f"{action_key}_clear"):
            _clear_action_error(action_key)
            st.rerun()

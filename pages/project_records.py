from __future__ import annotations

import streamlit as st
from pages.state_manager import state

from engine.case_store import CaseRecord, list_case_records, load_case_state
from pages import i18n, nav


def render() -> None:
    records = list_case_records()
    _render_project_center_header(records)

    if not records:
        _render_empty_home(has_active_case=bool(state.case_config))
        return

    _render_project_center(records)


def _render_record(record: CaseRecord) -> None:
    with st.container(border=True):
        left, middle, right = st.columns([2.2, 1.1, 0.8])
        with left:
            st.markdown(f"**{record.case_name}**")
            st.caption(record.question)
        with middle:
            st.metric(i18n.ui_text("当前进度", "Current progress"), i18n.stage_text(record.stage))
            st.caption(i18n.format_text("更新时间：{time}", "Updated: {time}", time=record.updated_at))
            st.caption(i18n.format_text("保存节点：{count}", "Saved artifacts: {count}", count=record.artifact_count))
        with right:
            if st.button(
                i18n.ui_text("进入项目", "Open project"),
                key=f"resume_{record.case_id}",
                width="stretch",
                type="primary",
            ):
                _load_record(record.case_id, "workbench")


def _render_project_center(records: list[CaseRecord]) -> None:
    latest = records[0]
    st.markdown(i18n.ui_text("### 项目中心", "### Project Center"))
    st.caption(
        i18n.ui_text(
            "从这里恢复已有模拟、创建新模拟，或者查看所有本机推演项目。",
            "Restore saved simulations, create a new one, or inspect all local projects.",
        )
    )

    action_cols = st.columns([1.15, 1, 1])
    with action_cols[0]:
        with st.container(border=True):
            st.markdown(i18n.ui_text("**继续最新模拟**", "**Continue Latest Simulation**"))
            st.caption(f"{latest.case_name} · {i18n.stage_text(latest.stage)}")
            if st.button(
                i18n.ui_text("继续推演", "Continue simulation"),
                type="primary",
                width="stretch",
                key="home_center_continue",
            ):
                _load_record(latest.case_id, "workbench")
    with action_cols[1]:
        with st.container(border=True):
            st.markdown(i18n.ui_text("**新建平行世界**", "**New Parallel World**"))
            st.caption(i18n.ui_text("从问题、材料和分支重新开启一条推演。", "Start from a question, materials, and branch design."))
            if st.button(i18n.ui_text("新建模拟", "New simulation"), width="stretch", key="home_center_new"):
                nav.switch_to("workbench")
    with action_cols[2]:
        with st.container(border=True):
            st.markdown(i18n.ui_text("**当前活动项目**", "**Active Project**"))
            if state.case_config:
                st.caption(state.case_config.case_name)
                label = i18n.ui_text("打开工作台", "Open workbench")
            else:
                st.caption(i18n.ui_text("当前没有临时项目。", "No temporary project is active."))
                label = i18n.ui_text("进入工作台", "Enter workbench")
            if st.button(label, width="stretch", key="home_center_open"):
                nav.switch_to("workbench")

    st.markdown(i18n.ui_text("#### 最近项目", "#### Recent Projects"))
    grid = st.columns(3)
    for index, record in enumerate(records[:6]):
        with grid[index % 3]:
            with st.container(border=True):
                st.markdown(f"**{record.case_name}**")
                st.caption(record.question)
                c1, c2 = st.columns(2)
                c1.metric(i18n.ui_text("阶段", "Stage"), i18n.stage_text(record.stage))
                c2.metric(i18n.ui_text("节点", "Artifacts"), record.artifact_count)
                st.caption(i18n.format_text("更新：{time}", "Updated: {time}", time=record.updated_at))
                if st.button(i18n.ui_text("进入", "Open"), key=f"center_resume_{record.case_id}", width="stretch"):
                    _load_record(record.case_id, "workbench")

    if len(records) > 6:
        with st.expander(i18n.ui_text("全部历史项目", "All saved projects"), expanded=False):
            for record in records[6:]:
                _render_record(record)


def _load_record(case_id: str, target_page: str | None = None) -> None:
    loaded = load_case_state(case_id)
    for key, value in loaded.items():
        state.set_dynamic(key, value)
    if target_page is not None:
        nav.switch_to(target_page)
    else:
        st.rerun()


def _render_empty_home(*, has_active_case: bool) -> None:
    if has_active_case:
        st.info(
            i18n.ui_text(
                "当前项目尚未形成保存记录。进入工作台继续后，首页会保留可恢复项目。",
                "The active project has not produced a saved record yet. Continue in the workbench to make it restorable from Home.",
            )
        )
        label = i18n.ui_text("打开当前项目", "Open active project")
    else:
        st.info(
            i18n.ui_text(
                "还没有保存过的项目。创建第一个项目后，首页会显示世界线、分支、智能体和事件流。",
                "No saved projects yet. After you create one, Home will show worldlines, branches, agents, and event flow.",
            )
        )
        label = i18n.ui_text("🚀 创建第一个项目", "🚀 Create first project")
    if st.button(label, type="primary", width="stretch"):
        nav.switch_to("workbench")


def _render_project_center_header(records: list[CaseRecord]) -> None:
    latest = records[0] if records else None
    active_case = state.case_config

    st.markdown(
        i18n.format_text(
            """
        <section class="project-center-hero">
            <div>
                <div class="dw-kicker">项目中心</div>
                <h1>平行世界推演台</h1>
                <p>管理模拟项目、恢复历史记录，并进入工作台运行多 Agent 世界线推演。</p>
            </div>
            <div class="project-center-stats">
                <div><strong>{record_count}</strong><span>本机项目</span></div>
                <div><strong>{latest_stage}</strong><span>最新阶段</span></div>
                <div><strong>{active_label}</strong><span>活动项目</span></div>
            </div>
        </section>
        """,
            """
        <section class="project-center-hero">
            <div>
                <div class="dw-kicker">Project Center</div>
                <h1>Divergent Worlds</h1>
                <p>Manage simulations, restore saved runs, and enter the workbench to run multi-agent worldline forecasts.</p>
            </div>
            <div class="project-center-stats">
                <div><strong>{record_count}</strong><span>Local projects</span></div>
                <div><strong>{latest_stage}</strong><span>Latest stage</span></div>
                <div><strong>{active_label}</strong><span>Active project</span></div>
            </div>
        </section>
        """,
            record_count=len(records),
            latest_stage=i18n.stage_text(latest.stage) if latest else i18n.ui_text("无", "None"),
            active_label=i18n.ui_text("有", "Yes") if active_case else i18n.ui_text("无", "No"),
        ),
        unsafe_allow_html=True,
    )

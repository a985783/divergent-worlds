from __future__ import annotations

import streamlit as st
from pages.state_manager import state

from engine.case_store import CaseRecord, list_case_records, load_case_state
from pages import nav


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
            st.metric("当前进度", record.stage)
            st.caption(f"更新时间：{record.updated_at}")
            st.caption(f"保存节点：{record.artifact_count}")
        with right:
            if st.button("进入项目", key=f"resume_{record.case_id}", width="stretch", type="primary"):
                _load_record(record.case_id, "workbench")


def _render_project_center(records: list[CaseRecord]) -> None:
    latest = records[0]
    st.markdown("### 项目中心")
    st.caption("从这里恢复已有模拟、创建新模拟，或者查看所有本机推演项目。")

    action_cols = st.columns([1.15, 1, 1])
    with action_cols[0]:
        with st.container(border=True):
            st.markdown("**继续最新模拟**")
            st.caption(f"{latest.case_name} · {latest.stage}")
            if st.button("继续推演", type="primary", width="stretch", key="home_center_continue"):
                _load_record(latest.case_id, "workbench")
    with action_cols[1]:
        with st.container(border=True):
            st.markdown("**新建平行世界**")
            st.caption("从问题、材料和分支重新开启一条推演。")
            if st.button("新建模拟", width="stretch", key="home_center_new"):
                nav.switch_to("workbench")
    with action_cols[2]:
        with st.container(border=True):
            st.markdown("**当前活动项目**")
            if state.case_config:
                st.caption(state.case_config.case_name)
                label = "打开工作台"
            else:
                st.caption("当前没有临时项目。")
                label = "进入工作台"
            if st.button(label, width="stretch", key="home_center_open"):
                nav.switch_to("workbench")

    st.markdown("#### 最近项目")
    grid = st.columns(3)
    for index, record in enumerate(records[:6]):
        with grid[index % 3]:
            with st.container(border=True):
                st.markdown(f"**{record.case_name}**")
                st.caption(record.question)
                c1, c2 = st.columns(2)
                c1.metric("阶段", record.stage)
                c2.metric("节点", record.artifact_count)
                st.caption(f"更新：{record.updated_at}")
                if st.button("进入", key=f"center_resume_{record.case_id}", width="stretch"):
                    _load_record(record.case_id, "workbench")

    if len(records) > 6:
        with st.expander("全部历史项目", expanded=False):
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
        st.info("当前项目尚未形成保存记录。进入工作台继续后，首页会保留可恢复项目。")
        label = "打开当前项目"
    else:
        st.info("还没有保存过的项目。创建第一个项目后，首页会显示世界线、分支、智能体和事件流。")
        label = "🚀 创建第一个项目"
    if st.button(label, type="primary", width="stretch"):
        nav.switch_to("workbench")


def _render_project_center_header(records: list[CaseRecord]) -> None:
    latest = records[0] if records else None
    active_case = state.case_config

    st.markdown(
        f"""
        <section class="project-center-hero">
            <div>
                <div class="dw-kicker">项目中心</div>
                <h1>平行世界推演台</h1>
                <p>管理模拟项目、恢复历史记录，并进入工作台运行多 Agent 世界线推演。</p>
            </div>
            <div class="project-center-stats">
                <div><strong>{len(records)}</strong><span>本机项目</span></div>
                <div><strong>{latest.stage if latest else "无"}</strong><span>最新阶段</span></div>
                <div><strong>{"有" if active_case else "无"}</strong><span>活动项目</span></div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

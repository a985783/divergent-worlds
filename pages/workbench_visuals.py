from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

from pages.workbench_state import (
    AgentView,
    BranchView,
    TimelineEvent,
    WorkbenchStage,
    WorkbenchViewModel,
    next_primary_action,
)


_STAGE_LABELS = {
    WorkbenchStage.NO_CASE: "等待创建",
    WorkbenchStage.DEMO_LOADED: "项目已创建",
    WorkbenchStage.MATERIALS_PARSED: "材料已解析",
    WorkbenchStage.BASE_WORLD_READY: "初始世界就绪",
    WorkbenchStage.BRANCHES_READY: "分支世界就绪",
    WorkbenchStage.PARTIAL_SIMULATION: "推演进行中",
    WorkbenchStage.COMPARISON_READY: "世界比较就绪",
    WorkbenchStage.REPORT_READY: "预测报告就绪",
}

_ACTION_LABELS = {
    "Create or load a case": "创建或恢复项目",
    "Parse materials": "解析材料",
    "Build base world": "构造初始世界",
    "Generate branch worlds": "生成分支世界",
    "Run branch simulation": "运行分支推演",
    "Resume branch simulation": "继续分支推演",
    "Compare branch outcomes": "比较分支结果",
    "Generate report": "生成预测报告",
    "Review report": "查看预测报告",
}

_STAGE_RAIL = (
    (WorkbenchStage.NO_CASE, "项目"),
    (WorkbenchStage.DEMO_LOADED, "材料"),
    (WorkbenchStage.MATERIALS_PARSED, "基线"),
    (WorkbenchStage.BASE_WORLD_READY, "分支"),
    (WorkbenchStage.BRANCHES_READY, "推演"),
    (WorkbenchStage.PARTIAL_SIMULATION, "比对"),
    (WorkbenchStage.COMPARISON_READY, "报告"),
    (WorkbenchStage.REPORT_READY, "归档"),
)


def render_cockpit_shell(
    vm: WorkbenchViewModel,
    *,
    saved_project_count: int = 0,
    latest_record_label: str | None = None,
    show_detail_panels: bool = True,
) -> None:
    """Render the homepage/workbench visual overview from a workbench view model."""

    title, question, horizon = _case_header(vm)
    stage_label = _stage_label(vm)
    primary_action = _action_label(next_primary_action(vm))
    saved_label = f"{saved_project_count} 个本机项目" if saved_project_count else "暂无保存项目"

    with st.container(border=True):
        col1, col2 = st.columns([2.5, 1])
        with col1:
            st.caption("世界线驾驶舱")
            st.subheader(title)
            st.write(question)
        with col2:
            st.button(stage_label, disabled=True, use_container_width=True, key="btn_stage")
            st.button(primary_action, disabled=True, use_container_width=True, key="btn_action")
            st.button(saved_label, disabled=True, use_container_width=True, key="btn_saved")
            if latest_record_label:
                st.button(latest_record_label, disabled=True, use_container_width=True, key="btn_latest")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("平行分支", len(vm.branches))
        m2.metric("智能体", len(vm.agents))
        m3.metric("时间事件", len(vm.timeline))
        m4.metric("预测窗口", horizon)

    if not show_detail_panels:
        return

    map_col, side_col = st.columns([1.75, 1])
    with map_col:
        render_world_map(vm)
        render_branch_lanes(vm.branches)
    with side_col:
        render_side_panel(vm)
        render_agent_cards(vm.agents)
        render_event_feed(vm.timeline)


def render_stage_rail(vm: WorkbenchViewModel) -> None:
    current_index = _stage_index(vm.stage)
    
    with st.container(border=True):
        col_title, col_action = st.columns([1, 1])
        with col_title:
            st.markdown("**推演阶段**")
        with col_action:
            st.markdown(f"*{_action_label(next_primary_action(vm))}*")

        cols = st.columns(8)
        for index, (stage, label) in enumerate(_STAGE_RAIL):
            if index < current_index:
                state = "✅"
            elif index == current_index:
                state = "▶️"
            else:
                state = "⏳"
            with cols[index]:
                st.markdown(f"{state} **{label}**")
                st.caption(_STAGE_LABELS.get(stage, stage.value))


def render_world_map(vm: WorkbenchViewModel) -> None:
    """Render a compact base-world to branch-world visual map using ECharts with pagination/truncation."""

    title, _, _ = _case_header(vm)
    branches = vm.branches
    limit = 5
    display_branches = branches[:limit]
    
    with st.container(border=True):
        st.markdown("**T0 现实基线 → 平行未来分支**")
        st.caption(_base_summary(vm))
        
        if not display_branches:
            st.info("分支等待生成：创建项目并构造初始世界后，这里会展开多条未来路径。")
            return
            
        try:
            from streamlit_echarts import st_echarts
            
            children = []
            for b in display_branches:
                prob = b.initial_probability
                children.append({
                    "name": f"{b.branch_name}\n({_percent(prob)})",
                    "value": prob,
                    "itemStyle": {"color": "#a78bfa"}
                })
            
            if len(branches) > limit:
                children.append({
                    "name": f"+{len(branches) - limit} 条分支",
                    "itemStyle": {"color": "#94a3b8"}
                })
            
            tree_data = {
                "name": title,
                "children": children,
                "itemStyle": {"color": "#10b981"}
            }
            
            options = {
                "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
                "series": [
                    {
                        "type": "tree",
                        "data": [tree_data],
                        "top": "10%",
                        "left": "15%",
                        "bottom": "10%",
                        "right": "20%",
                        "symbolSize": 12,
                        "itemStyle": {"borderColor": "#334155"},
                        "lineStyle": {"color": "#475569", "width": 2},
                        "label": {
                            "position": "left",
                            "verticalAlign": "middle",
                            "align": "right",
                            "fontSize": 12,
                            "color": "#f8fafc"
                        },
                        "leaves": {
                            "label": {
                                "position": "right",
                                "verticalAlign": "middle",
                                "align": "left",
                                "color": "#cbd5e1"
                            }
                        },
                        "expandAndCollapse": False,
                        "animationDuration": 500
                    }
                ]
            }
            st_echarts(options=options, height="260px")
        except Exception:
            for b in display_branches:
                st.markdown(f"- **{b.branch_name}** ({_percent(b.initial_probability)})")
            if len(branches) > limit:
                st.caption(f"+{len(branches) - limit} 条分支未显示")


def render_branch_lanes(branches: Sequence[BranchView], *, limit: int = 4) -> None:
    """Render branch lanes using native Streamlit components."""

    with st.container(border=True):
        st.markdown("**世界线轨道**")
        if not branches:
            st.info("暂无分支。先创建项目，再生成平行世界。")
        else:
            for branch in branches[:limit]:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{branch.branch_name}**")
                    with col2:
                        st.markdown(f"*{_percent(branch.initial_probability)}*")
                        
                    st.progress(max(0.0, min(1.0, branch.initial_probability)))
                    
                    summary = branch.latest_state_summary or branch.core_assumption or "等待推演更新"
                    st.write(_shorten(summary, 110))
                    
                    variables = _mapping_preview(branch.changed_variables, limit=2)
                    st.caption(f"{branch.simulation_step_count} 步推演 · {variables or '变量待定'}")
            
            if len(branches) > limit:
                st.caption(f"另有 {len(branches) - limit} 条分支，进入工作台查看完整分支集合。")


def render_agent_cards(agents: Sequence[AgentView], *, limit: int = 4) -> None:
    """Render active agent cards from view-model agent summaries."""

    with st.container(border=True):
        st.markdown("**智能体阵列**")
        if not agents:
            st.info("智能体待生成：运行分支推演前，行动者和立场会显示在这里。")
        else:
            for agent in agents[:limit]:
                with st.container(border=True):
                    st.markdown(f"**{agent.name}** · *{agent.branch_name}*")
                    goal = agent.goals[0] if agent.goals else "目标待生成"
                    st.write(agent.role or goal)
                    latest = agent.latest_action or agent.latest_belief or "等待下一步行动"
                    st.caption(_shorten(latest, 92))
            
            if len(agents) > limit:
                st.caption(f"+{len(agents) - limit} 更多智能体在工作台内展开。")


def render_event_feed(events: Sequence[TimelineEvent], *, limit: int = 5) -> None:
    """Render recent timeline events."""

    with st.container(border=True):
        st.markdown("**事件流**")
        recent = tuple(reversed(tuple(events)[-limit:]))
        if not recent:
            st.info("暂无事件流：分支完成至少一步推演后，这里会显示最新状态变化。")
        else:
            for event in recent:
                with st.container(border=True):
                    st.markdown(f"**{event.time_label or 'T+'}** · *{event.branch_name}*")
                    detail = event.state_summary or "; ".join(event.agent_actions) or "状态更新"
                    st.write(_shorten(detail, 110))
                    note = event.divergence_notes[0] if event.divergence_notes else event.branch_name
                    st.caption(_shorten(note, 88))


def render_event_timeline(events: Sequence[TimelineEvent], *, max_steps: int = 12) -> None:
    """中央舞台用：按 time_label 顺序正向揭示的逐步事件时间线，agent 动作逐条浮现。"""

    ordered = tuple(events)[-max_steps:]
    if not ordered:
        st.info("舞台待启幕：点击「一键运行所有分支」后，智能体会在这里按时间步逐条登场。")
        return

    for position, event in enumerate(ordered, start=1):
        with st.container(border=True):
            head_left, head_right = st.columns([3, 1])
            with head_left:
                st.markdown(f"**{position}. {event.time_label or 'T+'}** · *{event.branch_name}*")
            with head_right:
                st.caption(f"第 {position} 步")
            summary = event.state_summary or "状态更新"
            st.write(_shorten(summary, 160))

            actions = list(event.agent_actions)
            if actions:
                st.caption("智能体动作")
                for action in actions[:5]:
                    st.markdown(f"- {_shorten(_stringify(action), 120)}")
            signals = list(event.new_signals[:2]) + list(event.divergence_notes[:1])
            if signals:
                st.caption("信号 / 分歧：" + " · ".join(_shorten(_stringify(s), 60) for s in signals))


def render_side_panel(vm: WorkbenchViewModel) -> None:
    """Render cockpit context and next-action side panel."""

    stage_label = _stage_label(vm)
    primary_action = _action_label(next_primary_action(vm))
    signals = _top_signals(vm)

    with st.container(border=True):
        st.markdown("**任务状态**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.caption("当前阶段")
            st.markdown(f"**{stage_label}**")
            st.caption("证据密度")
            st.markdown(f"**{_evidence_density(vm)}**")
        with col2:
            st.caption("下一动作")
            st.markdown(f"**{primary_action}**")
            
        st.divider()
        if signals:
            for signal in signals:
                st.markdown(f"- {signal}")


def _case_header(vm: WorkbenchViewModel) -> tuple[str, str, str]:
    case_config = vm.case_config
    if not case_config:
        return (
            "平行世界推演台",
            "从一个真实问题出发，构造现实基线、平行分支、智能体行动和可校准预测。",
            "未设定",
        )
    return (
        str(_field(case_config, "case_name", "未命名项目")),
        str(_field(case_config, "question", "暂无核心问题")),
        str(_field(case_config, "horizon", "未设定")),
    )


def _base_summary(vm: WorkbenchViewModel) -> str:
    if vm.base_world:
        summary = _field(vm.base_world, "summary", None) or _field(vm.base_world, "situation", None)
        if summary:
            return _shorten(str(summary), 120)
        variables = _field(vm.base_world, "variables", {}) or {}
        preview = _mapping_preview(variables, limit=3)
        if preview:
            return preview
    if vm.material_summary:
        return "材料已解析，等待构造现实基线。"
    if vm.case_config:
        return "项目已创建，等待材料进入。"
    return "还没有活动项目。创建或恢复项目后，世界线会在这里展开。"


def _top_signals(vm: WorkbenchViewModel) -> list[str]:
    if vm.timeline:
        event = vm.timeline[-1]
        signals = list(event.new_signals[:2]) + list(event.divergence_notes[:1])
        if signals:
            return [_shorten(signal, 90) for signal in signals]
    if vm.branches:
        branch = vm.branches[0]
        signals = list(branch.support_signals[:2]) + list(branch.failure_signals[:1])
        if signals:
            return [_shorten(signal, 90) for signal in signals]
    return ["创建项目", "导入材料", "生成初始世界与平行分支"]


def _evidence_density(vm: WorkbenchViewModel) -> str:
    score = 0
    score += 1 if vm.material_summary else 0
    score += 1 if vm.base_world else 0
    score += 1 if vm.branches else 0
    score += 1 if vm.timeline else 0
    score += 1 if vm.divergence or vm.report or vm.forecast_cards else 0
    return f"{score}/5"


def _stage_label(vm: WorkbenchViewModel) -> str:
    return _STAGE_LABELS.get(vm.stage, str(vm.stage.value))


def _action_label(action: str) -> str:
    return _ACTION_LABELS.get(action, action)


def _stage_index(stage: WorkbenchStage) -> int:
    for index, (known_stage, _) in enumerate(_STAGE_RAIL):
        if known_stage is stage:
            return index
    return 0


def _percent(value: float) -> str:
    return f"{max(0.0, min(1.0, value)):.0%}"


def _mapping_preview(mapping: Mapping[str, Any], *, limit: int) -> str:
    parts = []
    for key, value in tuple(mapping.items())[:limit]:
        parts.append(f"{key}: {_shorten(_stringify(value), 30)}")
    return " · ".join(parts)


def _field(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _stringify(value: Any) -> str:
    if isinstance(value, Mapping):
        return ", ".join(f"{key}={_stringify(val)}" for key, val in tuple(value.items())[:3])
    if isinstance(value, list | tuple):
        return ", ".join(_stringify(item) for item in value[:3])
    return str(value)


def _shorten(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"

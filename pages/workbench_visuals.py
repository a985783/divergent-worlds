from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

from pages import i18n
from pages.workbench_state import (
    AgentView,
    BranchView,
    TimelineEvent,
    WorkbenchStage,
    WorkbenchViewModel,
    next_primary_action,
)


_STAGE_LABELS = {
    WorkbenchStage.NO_CASE: ("等待创建", "Waiting"),
    WorkbenchStage.DEMO_LOADED: ("项目已创建", "Project Created"),
    WorkbenchStage.MATERIALS_PARSED: ("材料已解析", "Materials Parsed"),
    WorkbenchStage.BASE_WORLD_READY: ("初始世界就绪", "Base World Ready"),
    WorkbenchStage.BRANCHES_READY: ("分支世界就绪", "Branches Ready"),
    WorkbenchStage.PARTIAL_SIMULATION: ("推演进行中", "Simulation Running"),
    WorkbenchStage.COMPARISON_READY: ("世界比较就绪", "Comparison Ready"),
    WorkbenchStage.REPORT_READY: ("预测报告就绪", "Forecast Ready"),
}

_ACTION_LABELS = {
    "Create or load a case": ("创建或恢复项目", "Create or load a case"),
    "Parse materials": ("解析材料", "Parse materials"),
    "Build base world": ("构造初始世界", "Build base world"),
    "Generate branch worlds": ("生成分支世界", "Generate branch worlds"),
    "Run branch simulation": ("运行分支推演", "Run branch simulation"),
    "Resume branch simulation": ("继续分支推演", "Resume branch simulation"),
    "Compare branch outcomes": ("比较分支结果", "Compare branch outcomes"),
    "Generate report": ("生成预测报告", "Generate report"),
    "Review report": ("查看预测报告", "Review report"),
}

_STAGE_RAIL = (
    (WorkbenchStage.NO_CASE, ("项目", "Project")),
    (WorkbenchStage.DEMO_LOADED, ("材料", "Materials")),
    (WorkbenchStage.MATERIALS_PARSED, ("基线", "Baseline")),
    (WorkbenchStage.BASE_WORLD_READY, ("分支", "Branches")),
    (WorkbenchStage.BRANCHES_READY, ("推演", "Run")),
    (WorkbenchStage.PARTIAL_SIMULATION, ("比对", "Compare")),
    (WorkbenchStage.COMPARISON_READY, ("报告", "Report")),
    (WorkbenchStage.REPORT_READY, ("归档", "Archive")),
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
    saved_label = (
        i18n.format_text("{count} 个本机项目", "{count} local projects", count=saved_project_count)
        if saved_project_count
        else i18n.ui_text("暂无保存项目", "No saved projects")
    )

    with st.container(border=True):
        col1, col2 = st.columns([2.5, 1])
        with col1:
            st.caption(i18n.ui_text("世界线驾驶舱", "Worldline Cockpit"))
            st.subheader(title)
            st.write(question)
        with col2:
            st.button(stage_label, disabled=True, use_container_width=True, key="btn_stage")
            st.button(primary_action, disabled=True, use_container_width=True, key="btn_action")
            st.button(saved_label, disabled=True, use_container_width=True, key="btn_saved")
            if latest_record_label:
                st.button(latest_record_label, disabled=True, use_container_width=True, key="btn_latest")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(i18n.ui_text("平行分支", "Branches"), len(vm.branches))
        m2.metric(i18n.ui_text("智能体", "Agents"), len(vm.agents))
        m3.metric(i18n.ui_text("时间事件", "Events"), len(vm.timeline))
        m4.metric(i18n.ui_text("预测窗口", "Horizon"), horizon)

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
            st.markdown(i18n.ui_text("**推演阶段**", "**Simulation Stages**"))
        with col_action:
            st.markdown(f"*{_action_label(next_primary_action(vm))}*")

        cols = st.columns(8)
        for index, (stage, label_pair) in enumerate(_STAGE_RAIL):
            if index < current_index:
                state = "✅"
            elif index == current_index:
                state = "▶️"
            else:
                state = "⏳"
            with cols[index]:
                label = i18n.ui_text(label_pair[0], label_pair[1])
                st.markdown(f"{state} **{label}**")
                st.caption(_stage_label_for(stage))


def render_world_map(vm: WorkbenchViewModel) -> None:
    """Render a compact base-world to branch-world visual map using ECharts with pagination/truncation."""

    title, _, _ = _case_header(vm)
    branches = vm.branches
    limit = 5
    display_branches = branches[:limit]
    
    with st.container(border=True):
        st.markdown(i18n.ui_text("**T0 现实基线 → 平行未来分支**", "**T0 Reality Baseline → Parallel Future Branches**"))
        st.caption(_base_summary(vm))
        
        if not display_branches:
            st.info(
                i18n.ui_text(
                    "分支等待生成：创建项目并构造初始世界后，这里会展开多条未来路径。",
                    "Branches are waiting: create a project and build the base world to unfold future paths here.",
                )
            )
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
                    "name": i18n.format_text(
                        "+{count} 条分支",
                        "+{count} branches",
                        count=len(branches) - limit,
                    ),
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
                st.caption(i18n.format_text("+{count} 条分支未显示", "+{count} branches hidden", count=len(branches) - limit))


def render_branch_lanes(branches: Sequence[BranchView], *, limit: int = 4) -> None:
    """Render branch lanes using native Streamlit components."""

    with st.container(border=True):
        st.markdown(i18n.ui_text("**世界线轨道**", "**Worldline Lanes**"))
        if not branches:
            st.info(i18n.ui_text("暂无分支。先创建项目，再生成平行世界。", "No branches yet. Create a project, then generate parallel worlds."))
        else:
            for branch in branches[:limit]:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{branch.branch_name}**")
                    with col2:
                        st.markdown(f"*{_percent(branch.initial_probability)}*")
                        
                    st.progress(max(0.0, min(1.0, branch.initial_probability)))
                    
                    summary = branch.latest_state_summary or branch.core_assumption or i18n.ui_text("等待推演更新", "Waiting for simulation updates")
                    st.write(_shorten(summary, 110))
                    
                    variables = _mapping_preview(branch.changed_variables, limit=2)
                    st.caption(
                        i18n.format_text(
                            "{count} 步推演 · {variables}",
                            "{count} simulation steps · {variables}",
                            count=branch.simulation_step_count,
                            variables=variables or i18n.ui_text("变量待定", "variables pending"),
                        )
                    )
            
            if len(branches) > limit:
                st.caption(
                    i18n.format_text(
                        "另有 {count} 条分支，进入工作台查看完整分支集合。",
                        "{count} more branches are available in the full workbench.",
                        count=len(branches) - limit,
                    )
                )


def render_agent_cards(agents: Sequence[AgentView], *, limit: int = 4) -> None:
    """Render active agent cards from view-model agent summaries."""

    with st.container(border=True):
        st.markdown(i18n.ui_text("**智能体阵列**", "**Agent Array**"))
        if not agents:
            st.info(i18n.ui_text("智能体待生成：运行分支推演前，行动者和立场会显示在这里。", "Agents are pending: actors and positions appear here before branch simulation runs."))
        else:
            for agent in agents[:limit]:
                with st.container(border=True):
                    st.markdown(f"**{agent.name}** · *{agent.branch_name}*")
                    goal = agent.goals[0] if agent.goals else i18n.ui_text("目标待生成", "Goal pending")
                    st.write(agent.role or goal)
                    latest = agent.latest_action or agent.latest_belief or i18n.ui_text("等待下一步行动", "Waiting for next action")
                    st.caption(_shorten(latest, 92))
            
            if len(agents) > limit:
                st.caption(i18n.format_text("+{count} 更多智能体在工作台内展开。", "+{count} more agents expand inside the workbench.", count=len(agents) - limit))


def render_event_feed(events: Sequence[TimelineEvent], *, limit: int = 5) -> None:
    """Render recent timeline events."""

    with st.container(border=True):
        st.markdown(i18n.ui_text("**事件流**", "**Event Feed**"))
        recent = tuple(reversed(tuple(events)[-limit:]))
        if not recent:
            st.info(i18n.ui_text("暂无事件流：分支完成至少一步推演后，这里会显示最新状态变化。", "No events yet: after at least one branch step, recent state changes appear here."))
        else:
            for event in recent:
                with st.container(border=True):
                    st.markdown(f"**{event.time_label or 'T+'}** · *{event.branch_name}*")
                    detail = event.state_summary or "; ".join(event.agent_actions) or i18n.ui_text("状态更新", "State update")
                    st.write(_shorten(detail, 110))
                    note = event.divergence_notes[0] if event.divergence_notes else event.branch_name
                    st.caption(_shorten(note, 88))


def render_event_timeline(events: Sequence[TimelineEvent], *, max_steps: int = 12) -> None:
    """中央舞台用：按 time_label 顺序正向揭示的逐步事件时间线，agent 动作逐条浮现。"""

    ordered = tuple(events)[-max_steps:]
    if not ordered:
        st.info(i18n.ui_text("舞台待启幕：点击「一键运行所有分支」后，智能体会在这里按时间步逐条登场。", "The stage is waiting: after running all branches, agents will appear here step by step."))
        return

    for position, event in enumerate(ordered, start=1):
        with st.container(border=True):
            head_left, head_right = st.columns([3, 1])
            with head_left:
                st.markdown(f"**{position}. {event.time_label or 'T+'}** · *{event.branch_name}*")
            with head_right:
                st.caption(i18n.format_text("第 {position} 步", "Step {position}", position=position))
            summary = event.state_summary or i18n.ui_text("状态更新", "State update")
            st.write(_shorten(summary, 160))

            actions = list(event.agent_actions)
            if actions:
                st.caption(i18n.ui_text("智能体动作", "Agent actions"))
                for action in actions[:5]:
                    st.markdown(f"- {_shorten(_stringify(action), 120)}")
            signals = list(event.new_signals[:2]) + list(event.divergence_notes[:1])
            if signals:
                st.caption(i18n.ui_text("信号 / 分歧：", "Signals / divergence: ") + " · ".join(_shorten(_stringify(s), 60) for s in signals))


def render_side_panel(vm: WorkbenchViewModel) -> None:
    """Render cockpit context and next-action side panel."""

    stage_label = _stage_label(vm)
    primary_action = _action_label(next_primary_action(vm))
    signals = _top_signals(vm)

    with st.container(border=True):
        st.markdown(i18n.ui_text("**任务状态**", "**Task Status**"))
        
        col1, col2 = st.columns(2)
        with col1:
            st.caption(i18n.ui_text("当前阶段", "Current stage"))
            st.markdown(f"**{stage_label}**")
            st.caption(i18n.ui_text("证据密度", "Evidence density"))
            st.markdown(f"**{_evidence_density(vm)}**")
        with col2:
            st.caption(i18n.ui_text("下一动作", "Next action"))
            st.markdown(f"**{primary_action}**")
            
        st.divider()
        if signals:
            for signal in signals:
                st.markdown(f"- {signal}")


def _case_header(vm: WorkbenchViewModel) -> tuple[str, str, str]:
    case_config = vm.case_config
    if not case_config:
        return (
            i18n.ui_text("平行世界推演台", "Divergent Worlds"),
            i18n.ui_text(
                "从一个真实问题出发，构造现实基线、平行分支、智能体行动和可校准预测。",
                "Start from a real question, build a reality baseline, parallel branches, agent actions, and calibratable forecasts.",
            ),
            i18n.ui_text("未设定", "Unset"),
        )
    return (
        str(_field(case_config, "case_name", i18n.ui_text("未命名项目", "Untitled project"))),
        str(_field(case_config, "question", i18n.ui_text("暂无核心问题", "No core question yet"))),
        str(_field(case_config, "horizon", i18n.ui_text("未设定", "Unset"))),
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
        return i18n.ui_text("材料已解析，等待构造现实基线。", "Materials parsed; waiting to build the reality baseline.")
    if vm.case_config:
        return i18n.ui_text("项目已创建，等待材料进入。", "Project created; waiting for materials.")
    return i18n.ui_text("还没有活动项目。创建或恢复项目后，世界线会在这里展开。", "No active project yet. Create or restore a project to unfold worldlines here.")


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
    return [
        i18n.ui_text("创建项目", "Create project"),
        i18n.ui_text("导入材料", "Import materials"),
        i18n.ui_text("生成初始世界与平行分支", "Generate base world and parallel branches"),
    ]


def _evidence_density(vm: WorkbenchViewModel) -> str:
    score = 0
    score += 1 if vm.material_summary else 0
    score += 1 if vm.base_world else 0
    score += 1 if vm.branches else 0
    score += 1 if vm.timeline else 0
    score += 1 if vm.divergence or vm.report or vm.forecast_cards else 0
    return f"{score}/5"


def _stage_label(vm: WorkbenchViewModel) -> str:
    return _stage_label_for(vm.stage)


def _action_label(action: str) -> str:
    label = _ACTION_LABELS.get(action)
    return i18n.ui_text(label[0], label[1]) if label else action


def _stage_label_for(stage: WorkbenchStage) -> str:
    label = _STAGE_LABELS.get(stage)
    return i18n.ui_text(label[0], label[1]) if label else str(stage.value)


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

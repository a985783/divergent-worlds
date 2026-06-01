from __future__ import annotations

from pathlib import Path

import streamlit as st

from pages.state_manager import state
from pages import i18n
from pages.ui_helpers import inject_app_css, llm_is_ready
from pages.workbench_state import WorkbenchStage, WorkbenchViewModel, build_workbench_vm

from pages.components.base_world import render_baseworld_section
from pages.components.branches import render_branches_section
from pages.components.material import render_material_ingestion_section
from pages.components.result import render_comparison_tab, render_report_tab
from pages.components.run import render_simulation_console_tab
from pages.components.setup import render_new_case_setup


WORKBENCH_STEPS = [
    "materials",
    "base_world",
    "branches",
    "simulation",
    "comparison",
    "report",
]

STAGE_TO_INDEX = {
    WorkbenchStage.NO_CASE: 0,
    WorkbenchStage.DEMO_LOADED: 0,
    WorkbenchStage.MATERIALS_PARSED: 1,
    WorkbenchStage.BASE_WORLD_READY: 2,
    WorkbenchStage.BRANCHES_READY: 3,
    WorkbenchStage.PARTIAL_SIMULATION: 3,
    WorkbenchStage.COMPARISON_READY: 4,
    WorkbenchStage.REPORT_READY: 5,
}

STAGE_RAIL = [
    (WorkbenchStage.NO_CASE, ("项目", "Project")),
    (WorkbenchStage.DEMO_LOADED, ("材料", "Materials")),
    (WorkbenchStage.MATERIALS_PARSED, ("基线", "Baseline")),
    (WorkbenchStage.BASE_WORLD_READY, ("分支", "Branches")),
    (WorkbenchStage.BRANCHES_READY, ("推演", "Run")),
    (WorkbenchStage.PARTIAL_SIMULATION, ("比对", "Compare")),
    (WorkbenchStage.COMPARISON_READY, ("报告", "Report")),
    (WorkbenchStage.REPORT_READY, ("完成", "Done")),
]


def _step_label(step: str) -> str:
    return {
        "materials": i18n.ui_text("1. 材料解析", "1. Material Parsing"),
        "base_world": i18n.ui_text("2. 初始世界", "2. Base World"),
        "branches": i18n.ui_text("3. 平行分支", "3. Parallel Branches"),
        "simulation": i18n.ui_text("4. 运行控制台", "4. Run Console"),
        "comparison": i18n.ui_text("5. 分支比对", "5. Branch Comparison"),
        "report": i18n.ui_text("6. 预测报告", "6. Forecast Report"),
    }[step]


def _stage_long_label(stage: WorkbenchStage) -> str:
    labels = {
        WorkbenchStage.NO_CASE: i18n.ui_text("等待创建项目", "Waiting for project creation"),
        WorkbenchStage.DEMO_LOADED: i18n.ui_text("项目已创建，等待材料解析", "Project created; waiting for material parsing"),
        WorkbenchStage.MATERIALS_PARSED: i18n.ui_text("材料已解析，等待构造基线", "Materials parsed; waiting for base world"),
        WorkbenchStage.BASE_WORLD_READY: i18n.ui_text("基线世界就绪，等待生成分支", "Base world ready; waiting for branches"),
        WorkbenchStage.BRANCHES_READY: i18n.ui_text("分支世界就绪，等待推演", "Branch worlds ready; waiting for simulation"),
        WorkbenchStage.PARTIAL_SIMULATION: i18n.ui_text("推演记录已产生，等待继续或比对", "Simulation logs exist; continue or compare"),
        WorkbenchStage.COMPARISON_READY: i18n.ui_text("分支比对就绪，等待生成报告", "Branch comparison ready; waiting for report"),
        WorkbenchStage.REPORT_READY: i18n.ui_text("报告结果就绪", "Report ready"),
    }
    return labels.get(stage, stage.value)


def render() -> None:
    inject_app_css()
    vm = build_workbench_vm(state)

    if not state.case_config:
        _render_empty_flow_intro(vm)
        render_new_case_setup()
        return

    _render_progress_rail(vm)

    active_step = _resolve_active_act(vm)

    st.divider()

    if active_step == "materials":
        render_material_ingestion_section(state.case_config)
    elif active_step == "base_world":
        if not state.material_summary:
            st.info(i18n.ui_text("请先完成材料解析。", "Complete material parsing first."))
        else:
            render_baseworld_section(state.case_config, state.material_summary, vm)
    elif active_step == "branches":
        if not state.base_world:
            st.info(i18n.ui_text("请先构造初始世界。", "Build the base world first."))
        else:
            render_branches_section(state.case_config, state.base_world, vm)
    elif active_step == "simulation":
        render_simulation_console_tab(vm)
    elif active_step == "comparison":
        render_comparison_tab(vm)
    elif active_step == "report":
        render_report_tab(vm)

    if state.is_auto_pilot and state.case_config:
        _run_auto_pilot(vm)


def _render_empty_flow_intro(vm: WorkbenchViewModel) -> None:
    with st.container(border=True):
        st.markdown(i18n.ui_text("### 流程推进器", "### Flow Driver"))
        st.caption(
            i18n.ui_text(
                "先创建或恢复项目。项目进入工作台后，顶部会出现固定的“下一步”按钮，"
                "把材料解析、基线、分支、推演、比对、报告串起来。",
                "Create or restore a project first. The workbench then connects materials, "
                "baseline, branches, simulation, comparison, and report into one flow.",
            )
        )
        _render_compact_stage_rail(vm)


def _render_progress_rail(vm: WorkbenchViewModel) -> None:
    """纯进度轨：只展示阶段进度与全局控制（自动推进/回到当前/重置）。

    阶段推进的唯一主操作放在各幕组件内（走 run_act_action），这里不再有重复的“下一步”按钮。
    """
    action_label = _next_step_label(vm)
    blocker = _structural_blocker(vm)
    ready, llm_blockers = llm_is_ready(state.llm_client)

    with st.container(border=True):
        top_left, top_right = st.columns([2.2, 1])
        with top_left:
            st.markdown(i18n.ui_text("### 流程推进器", "### Flow Driver"))
            st.caption(_stage_long_label(vm.stage))
            _render_compact_stage_rail(vm)
        with top_right:
            st.caption(i18n.ui_text("当前阶段", "Current stage"))
            st.markdown(f"**{_short_stage_label(vm.stage)}**")
            st.caption(i18n.ui_text("下一步", "Next step"))
            st.markdown(f"**{action_label}**")

        progress = _stage_progress(vm.stage)
        st.progress(
            progress,
            text=i18n.format_text(
                "流程进度 {value}%",
                "Flow progress {value}%",
                value=int(progress * 100),
            ),
        )

        if llm_blockers:
            st.warning(i18n.ui_text("模型调用受阻：", "Model call blocked: ") + " ".join(llm_blockers))
        elif ready:
            st.caption(i18n.ui_text("模型状态：可用。", "Model status: available."))

        if blocker:
            st.info(blocker)

        col_auto, col_focus, col_reset = st.columns([1.4, 1, 1])
        with col_auto:
            state.is_auto_pilot = st.toggle(
                i18n.ui_text("自动推进", "Autopilot"),
                value=state.is_auto_pilot,
                key="toggle_auto_pilot",
            )
        with col_focus:
            if st.button(
                i18n.ui_text("回到当前阶段", "Focus current stage"),
                use_container_width=True,
                key="workbench_focus_current",
            ):
                _goto_stage(vm.stage)
                st.rerun()
        with col_reset:
            if st.button(i18n.ui_text("重置项目", "Reset project"), use_container_width=True, key="workbench_reset_case"):
                _reset_current_case()
                st.rerun()


def _render_compact_stage_rail(vm: WorkbenchViewModel) -> None:
    current = _rail_index(vm.stage)
    cols = st.columns(len(STAGE_RAIL))
    for index, (_, label_pair) in enumerate(STAGE_RAIL):
        if index < current:
            status = i18n.ui_text("完成", "Done")
        elif index == current:
            status = i18n.ui_text("当前", "Current")
        else:
            status = i18n.ui_text("待处理", "Pending")
        with cols[index]:
            label = i18n.ui_text(label_pair[0], label_pair[1])
            st.markdown(f"**{label}**")
            st.caption(status)


def _resolve_active_act(vm: WorkbenchViewModel) -> str:
    """单幕路由：默认停在当前阶段对应的幕；只允许回看已完成的幕，不允许向前跳。

    阶段变化时自动跳到当前幕（通过 workbench_stage_seen 记录上次已见阶段）。
    """
    key = "workbench_active_step"
    seen_key = "workbench_stage_seen"
    current_index = STAGE_TO_INDEX.get(vm.stage, 0)
    target = WORKBENCH_STEPS[current_index]

    if st.session_state.get(seen_key) != vm.stage.value:
        st.session_state[key] = target
        st.session_state[seen_key] = vm.stage.value

    available = WORKBENCH_STEPS[: current_index + 1]
    selected = st.session_state.get(key)
    legacy_map = {
        "1. 材料解析": "materials",
        "2. 初始世界": "base_world",
        "3. 平行分支": "branches",
        "4. 运行控制台": "simulation",
        "5. 分支比对": "comparison",
        "6. 预测报告": "report",
    }
    selected = legacy_map.get(selected, selected)
    if selected not in available:
        selected = target
        st.session_state[key] = selected

    if len(available) > 1:
        # 当前值已写入 session_state[key]，控件不再传 default/index，避免 Streamlit 双重赋值警告。
        if hasattr(st, "pills"):
            picked = st.pills(
                i18n.ui_text("回看流程阶段", "Review completed stages"),
                options=available,
                key=key,
                format_func=_step_label,
            )
        elif hasattr(st, "segmented_control"):
            picked = st.segmented_control(
                i18n.ui_text("回看流程阶段", "Review completed stages"),
                options=available,
                key=key,
                format_func=_step_label,
            )
        else:
            picked = st.radio(
                i18n.ui_text("回看流程阶段", "Review completed stages"),
                options=available,
                horizontal=True,
                key=key,
                format_func=_step_label,
            )
        selected = picked or target
    return selected


def _reset_current_case() -> None:
    state.case_config = None
    state.material_summary = None
    state.material_preview = []
    state.base_world = None
    state.branches = []
    state.profiles = []
    state.actors_by_branch = {}
    state.simulation_logs = {}
    state.divergence = None
    state.forecast_cards = []
    state.report = ""
    state.report_json = {}
    state.is_auto_pilot = False
    st.session_state.pop("workbench_active_step", None)
    st.session_state.pop("workbench_stage_seen", None)


def _next_step_label(vm: WorkbenchViewModel) -> str:
    if vm.stage is WorkbenchStage.NO_CASE:
        return i18n.ui_text("创建或恢复项目", "Create or restore project")
    if vm.stage is WorkbenchStage.DEMO_LOADED:
        return i18n.ui_text("解析材料", "Parse materials")
    if vm.stage is WorkbenchStage.MATERIALS_PARSED:
        return i18n.ui_text("构造初始世界", "Build base world")
    if vm.stage is WorkbenchStage.BASE_WORLD_READY:
        return i18n.ui_text("生成平行分支", "Generate parallel branches")
    if vm.stage in (WorkbenchStage.BRANCHES_READY, WorkbenchStage.PARTIAL_SIMULATION):
        if not _simulation_complete():
            return i18n.ui_text("运行或继续全部世界线", "Run or resume all worldlines")
        return i18n.ui_text("生成分支比对与预测卡", "Generate comparison and forecast cards")
    if vm.stage is WorkbenchStage.COMPARISON_READY:
        if not state.forecast_cards:
            return i18n.ui_text("生成预测卡", "Generate forecast cards")
        return i18n.ui_text("生成最终报告", "Generate final report")
    if vm.stage is WorkbenchStage.REPORT_READY and not state.report:
        return i18n.ui_text("生成最终报告", "Generate final report")
    return i18n.ui_text("查看结果", "Review results")


def _structural_blocker(vm: WorkbenchViewModel) -> str | None:
    if vm.stage is WorkbenchStage.DEMO_LOADED and not state.material_summary:
        if not state.demo_material_paths and not state.material_preview:
            _goto_stage(WorkbenchStage.DEMO_LOADED)
            return i18n.ui_text(
                "需要先在“材料解析”区域上传文件、填写本地文件夹路径，或粘贴材料。",
                "Upload files, enter a local folder path, or paste materials in Material Parsing first.",
            )
    if vm.stage in (WorkbenchStage.BRANCHES_READY, WorkbenchStage.PARTIAL_SIMULATION):
        if not state.branches or not state.base_world:
            return i18n.ui_text("需要先生成并确认平行分支。", "Generate and confirm parallel branches first.")
    if vm.stage is WorkbenchStage.REPORT_READY and state.report:
        return i18n.ui_text("流程已经完成；可以查看报告或进入预测账本。", "The flow is complete; review the report or open the forecast ledger.")
    return None


def _advance_one_step(vm: WorkbenchViewModel) -> None:
    stage = vm.stage
    if stage is WorkbenchStage.NO_CASE:
        raise RuntimeError(i18n.ui_text("请先创建或恢复项目。", "Create or restore a project first."))
    if stage is WorkbenchStage.DEMO_LOADED:
        _parse_materials()
    elif stage is WorkbenchStage.MATERIALS_PARSED:
        _build_base_world()
    elif stage is WorkbenchStage.BASE_WORLD_READY:
        _generate_branches()
    elif stage in (WorkbenchStage.BRANCHES_READY, WorkbenchStage.PARTIAL_SIMULATION):
        if _simulation_complete():
            _generate_comparison_and_cards()
        else:
            _run_all_simulations()
    elif stage is WorkbenchStage.COMPARISON_READY:
        if not state.forecast_cards:
            _generate_comparison_and_cards()
        else:
            _generate_report()
    elif stage is WorkbenchStage.REPORT_READY:
        if not state.report and state.divergence and state.forecast_cards:
            _generate_report()
        else:
            return
    state.set_dynamic("_workbench_force_rerun", True)


def _parse_materials() -> None:
    if state.material_summary:
        return
    if not state.material_preview and state.demo_material_paths:
        from pages.components.shared import _load_material_preview

        paths = [Path(path) for path in state.demo_material_paths]
        state.material_preview = _load_material_preview(paths)

    preview = state.material_preview or []
    raw_texts = [item.get("text", "") for item in preview if item.get("text")]
    if not raw_texts:
        raise RuntimeError(
            i18n.ui_text(
                "没有可解析材料。请先上传文件、填写本地文件夹路径，或粘贴材料。",
                "No parseable materials. Upload files, enter a local folder path, or paste materials first.",
            )
        )

    from engine.ingest import summarize_materials

    state.material_summary = summarize_materials(raw_texts, state.llm_client, state.case_config)


def _build_base_world() -> None:
    if state.base_world:
        return
    from engine.world_builder import build_base_world

    state.base_world = build_base_world(state.material_summary, state.case_config, state.llm_client)


def _generate_branches() -> None:
    if state.branches:
        return
    from engine.fork_generator import assign_branch_type, generate_branches
    from engine.utils import get_case_path, save_json

    branches = generate_branches(state.base_world, state.case_config, state.llm_client)
    for branch in branches:
        branch.branch_type = assign_branch_type(branch)
    state.branches = branches
    save_json(branches, get_case_path(state.case_config.case_id, "03_branches.json"))


def _run_all_simulations() -> None:
    """调用推演函数；带实时 st.status 可视化，不在 spinner 内部阻塞。"""
    from pages.components.run import _run_all_branch_simulations

    _run_all_branch_simulations()


def _generate_comparison_and_cards() -> None:
    if not state.branches or not state.simulation_logs:
        raise RuntimeError(i18n.ui_text("还没有可比对的推演记录。请先运行世界线推演。", "No simulation logs to compare yet. Run the worldline simulation first."))
    from engine.divergence_analyzer import analyze_divergence
    from engine.forecast_card import generate_forecast_cards

    if not state.divergence:
        state.divergence = analyze_divergence(
            state.branches,
            state.simulation_logs,
            state.llm_client,
            state.case_config,
        )
    if not state.forecast_cards:
        state.forecast_cards = generate_forecast_cards(
            state.branches,
            state.simulation_logs,
            state.divergence,
            state.case_config,
            state.llm_client,
        )


def _generate_report() -> None:
    if not state.divergence:
        raise RuntimeError(i18n.ui_text("请先完成分支比对。", "Complete branch comparison first."))
    from engine.report_generator import generate_report, generate_report_json

    report_md = generate_report(
        state.case_config,
        state.material_summary,
        state.base_world,
        state.branches,
        state.profiles or [],
        state.simulation_logs,
        state.divergence,
        state.forecast_cards,
        state.llm_client,
    )
    state.report = report_md
    state.report_json = generate_report_json(
        state.case_config,
        state.material_summary,
        state.base_world,
        state.branches,
        state.profiles or [],
        state.simulation_logs,
        state.divergence,
        state.forecast_cards,
    )


def _simulation_complete() -> bool:
    case_config = state.case_config
    branches = state.branches or []
    if not case_config or not branches:
        return False
    from engine.simulation_runner import SimulationRunner

    expected_steps = len(SimulationRunner.get_time_steps(case_config.horizon))
    logs = state.simulation_logs or {}
    return all(len(logs.get(branch.branch_id, [])) >= expected_steps for branch in branches)


def _goto_stage(stage: WorkbenchStage) -> None:
    index = STAGE_TO_INDEX.get(stage, 0)
    st.session_state["workbench_active_step"] = WORKBENCH_STEPS[index]
    st.session_state["workbench_stage_seen"] = stage.value


def _state_progress_signature() -> tuple:
    logs = state.simulation_logs or {}
    return (
        bool(state.material_summary),
        bool(state.base_world),
        len(state.branches or []),
        sum(len(steps) for steps in logs.values()),
        bool(state.divergence),
        len(state.forecast_cards or []),
        bool(state.report),
    )


def _stage_progress(stage: WorkbenchStage) -> float:
    return _rail_index(stage) / max(1, len(STAGE_RAIL) - 1)


def _rail_index(stage: WorkbenchStage) -> int:
    if stage is WorkbenchStage.PARTIAL_SIMULATION:
        return 5
    for index, (candidate, _) in enumerate(STAGE_RAIL):
        if candidate is stage:
            return index
    return 0


def _short_stage_label(stage: WorkbenchStage) -> str:
    return {
        WorkbenchStage.NO_CASE: i18n.ui_text("未创建", "Not started"),
        WorkbenchStage.DEMO_LOADED: i18n.ui_text("材料", "Materials"),
        WorkbenchStage.MATERIALS_PARSED: i18n.ui_text("基线", "Baseline"),
        WorkbenchStage.BASE_WORLD_READY: i18n.ui_text("分支", "Branches"),
        WorkbenchStage.BRANCHES_READY: i18n.ui_text("推演", "Run"),
        WorkbenchStage.PARTIAL_SIMULATION: i18n.ui_text("比对", "Compare"),
        WorkbenchStage.COMPARISON_READY: i18n.ui_text("报告", "Report"),
        WorkbenchStage.REPORT_READY: i18n.ui_text("完成", "Done"),
    }.get(stage, stage.value)


def _run_auto_pilot(vm: WorkbenchViewModel) -> None:
    if st.session_state.get("_testing_skip_auto_pilot"):
        return

    blocker = _structural_blocker(vm)
    if blocker:
        st.warning(i18n.ui_text("自动推进已暂停：", "Autopilot paused: ") + blocker)
        state.is_auto_pilot = False
        return

    ready, blockers = llm_is_ready(state.llm_client)
    if not ready:
        st.warning(i18n.ui_text("自动推进已暂停：模型调用受阻。", "Autopilot paused: model call blocked. ") + " ".join(blockers))
        state.is_auto_pilot = False
        return

    if vm.stage is WorkbenchStage.REPORT_READY and state.report:
        state.is_auto_pilot = False
        return

    before = _state_progress_signature()

    # 推演阶段特殊处理：直接渲染可视化进度，不用 spinner 阻塞
    is_sim_stage = vm.stage in (WorkbenchStage.BRANCHES_READY, WorkbenchStage.PARTIAL_SIMULATION)
    if is_sim_stage and not _simulation_complete():
        st.markdown(i18n.ui_text("#### ⚙️ 自动推进：世界线推演", "#### ⚙️ Autopilot: Worldline Simulation"))
        try:
            _run_all_simulations()
        except Exception as exc:
            st.error(i18n.format_text("自动推进失败（推演）：{exc}", "Autopilot failed during simulation: {exc}", exc=exc))
            state.is_auto_pilot = False
            return
    else:
        # 其他阶段用 spinner 包裹（这些操作通常很快）
        try:
            with st.spinner(i18n.ui_text("自动推进：", "Autopilot: ") + _next_step_label(vm)):
                _advance_one_step(vm)
        except Exception as exc:
            st.error(i18n.format_text("自动推进失败：{exc}", "Autopilot failed: {exc}", exc=exc))
            state.is_auto_pilot = False
            return

    after = _state_progress_signature()
    if after == before:
        st.warning(
            i18n.ui_text(
                "自动推进没有产生新进度，已暂停。请检查当前阶段输入。",
                "Autopilot produced no new progress and has paused. Check the current stage input.",
            )
        )
        state.is_auto_pilot = False
        return

    state.set_dynamic("_workbench_force_rerun", False)
    next_vm = build_workbench_vm(state)
    _goto_stage(next_vm.stage)
    st.rerun()

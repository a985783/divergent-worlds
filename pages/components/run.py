"""推演控制台组件 – 同步顺序推演，实时 st.status 可视化。

核心修复：
1. 去掉 ThreadPoolExecutor + while/sleep 阻塞轮询（原双层并发会冻结 Streamlit 主线程）
2. 改为同步逐分支、逐步推演，每步完成后立即更新进度条和状态面板
3. 自动推进（autopilot）路径复用同一套可视化逻辑
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from engine.schemas import CaseConfig, BaseWorld, BranchWorld, WorldProfile
from engine.utils import get_case_path, save_json
from engine.simulation_runner import SimulationRunner
from engine.actor_generator import generate_actors_for_branches
from engine.world_profiler import profile_worlds
from pages.state_manager import state
from pages.workbench_visuals import render_agent_cards, render_event_timeline
from pages.workbench_state import WorkbenchViewModel


# ---------------------------------------------------------------------------
# Fragment 组件（仅用于控制台 tab 内的独立刷新区域）
# ---------------------------------------------------------------------------

@st.fragment
def fragment_event_timeline(vm: WorkbenchViewModel) -> None:
    render_event_timeline(vm.timeline)


@st.fragment
def fragment_agent_cards(vm: WorkbenchViewModel) -> None:
    render_agent_cards(vm.agents)


# ---------------------------------------------------------------------------
# 控制台主渲染
# ---------------------------------------------------------------------------

def render_simulation_console_tab(vm: WorkbenchViewModel) -> None:
    case_config = state.case_config
    base_world = state.base_world
    branches = state.branches or []

    if not case_config or not base_world or not branches:
        st.info('💡 请先完成"设定与分歧设计"并锁定平行分支。')
        return

    from pages.workbench_visuals import render_world_map, render_branch_lanes

    # 中央舞台抬头：智能体推演是 demo 的视觉主角
    st.markdown("### 🎭 智能体推演舞台")
    st.caption("多智能体在每条世界线上逐步行动；下方时间线会按时间步揭示它们的决策。")

    render_world_map(vm)

    st.markdown("#### 🚀 推演控制台")
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    with col_btn1:
        if st.button('⏩ 一键运行所有分支', type="primary", use_container_width=True):
            st.session_state.trigger_manual_run = True
    with col_btn2:
        if st.button('🎯 对比并生成预测卡', disabled=not bool(vm.timeline), use_container_width=True):
            st.info('请前往"分支比对"阶段')
    with col_btn3:
        if st.button('🧹 重置记录', disabled=not bool(vm.timeline), use_container_width=True):
            logs = state.simulation_logs or {}
            for b in branches:
                logs[b.branch_id] = []
            state.simulation_logs = logs
            if case_config:
                save_json(logs, get_case_path(case_config.case_id, "05_simulation_log.json"))
            st.success("推演进度已重置。")
            st.rerun()

    # 在控制台下方显示推演进度面板（运行时实时刷新）
    if st.session_state.get("trigger_manual_run"):
        st.session_state.trigger_manual_run = False
        st.divider()
        _run_all_branch_simulations()
        st.rerun()

    st.divider()

    # 中央主区：逐步事件时间线（戏份主角）占据宽列，智能体阵列在侧
    stage_col, agent_col = st.columns([1.7, 1])
    with stage_col:
        st.markdown("#### 🔄 逐步事件时间线")
        fragment_event_timeline(vm)
        render_branch_lanes(vm.branches)
    with agent_col:
        st.markdown("#### 🤖 参演智能体")
        fragment_agent_cards(vm)


# ---------------------------------------------------------------------------
# 核心推演执行 – 同步顺序，实时可视化
# ---------------------------------------------------------------------------

def _run_all_branch_simulations() -> None:
    """顺序推演所有分支，每步实时刷新 st.status 面板。

    不使用 ThreadPoolExecutor + while/sleep，避免阻塞 Streamlit 主线程。
    """
    case_config = state.case_config
    base_world = state.base_world
    branches = state.branches or []
    if not case_config or not base_world or not branches:
        st.warning("需要先完成项目、初始世界和分支世界。")
        return

    profiles, actors_by_branch = _ensure_profiles_and_actors(case_config, base_world, branches)
    logs: dict[str, Any] = dict(state.simulation_logs or {})
    runner = SimulationRunner(state.llm_client, case_config)
    time_steps = SimulationRunner.get_time_steps(case_config.horizon)
    total_steps = len(branches) * len(time_steps)
    done_steps = 0

    # 顶层进度容器
    overall_progress = st.progress(0, text="推演进度：0 / " + str(total_steps) + " 步")
    log_area = st.container()

    for branch in branches:
        branch_id = branch.branch_id
        existing = list(logs.get(branch_id, []))
        completed_labels = {s.time_label for s in existing}
        remaining = [t for t in time_steps if t not in completed_labels]

        # 已全部完成
        if not remaining:
            done_steps += len(time_steps)
            frac = min(done_steps / max(total_steps, 1), 1.0)
            overall_progress.progress(frac, text=f"推演进度：{done_steps} / {total_steps} 步")
            with log_area:
                st.success(f"✅ 【{branch.branch_name}】已推演完毕，跳过。")
            continue

        profile_by_branch = {p.branch_id: p for p in profiles}

        with st.status(
            f"🌐 推演分支：{branch.branch_name}",
            expanded=True,
        ) as status_box:
            step_log = list(existing)
            for time_label in remaining:
                status_box.update(
                    label=f"🌐 【{branch.branch_name}】 → {time_label} 智能体决策中…",
                    state="running",
                )
                try:
                    new_step = runner.run_step(
                        branch,
                        actors_by_branch.get(branch_id, []),
                        base_world,
                        step_log,
                        time_label,
                        profile_by_branch.get(branch_id),
                    )
                except Exception as exc:
                    status_box.update(
                        label=f"❌ 【{branch.branch_name}】{time_label} 推演失败",
                        state="error",
                    )
                    st.error(f"推演错误：{exc}")
                    break

                step_log.append(new_step)
                done_steps += 1
                frac = min(done_steps / max(total_steps, 1), 1.0)
                overall_progress.progress(
                    frac, text=f"推演进度：{done_steps} / {total_steps} 步"
                )

                # 实时写入 state，让其他面板也能感知到进度
                logs[branch_id] = step_log
                state.simulation_logs = logs

                status_box.write(
                    f"**{time_label}** ✔ {new_step.state_summary[:120]}"
                    + ("…" if len(new_step.state_summary) > 120 else "")
                )

            if len(step_log) >= len(time_steps):
                status_box.update(
                    label=f"✅ 【{branch.branch_name}】推演完成",
                    state="complete",
                )
            logs[branch_id] = step_log
            state.simulation_logs = logs

    # 全部完成后持久化
    save_json(logs, get_case_path(case_config.case_id, "05_simulation_log.json"))
    overall_progress.progress(1.0, text=f"✅ 全部推演完成，共 {total_steps} 步")
    st.success("🎉 全部世界线推演处理完成！")


# ---------------------------------------------------------------------------
# 辅助：确保 profiles 和 actors 就绪（带可视化提示）
# ---------------------------------------------------------------------------

def _ensure_profiles_and_actors(
    case_config: CaseConfig,
    base_world: BaseWorld,
    branches: list[BranchWorld],
) -> tuple[list[WorldProfile], dict[str, Any]]:
    profiles = state.profiles or []
    if not profiles:
        with st.status("🧠 分析世界画像…", expanded=False) as s:
            profiles = profile_worlds(branches, base_world, case_config, state.llm_client)
            state.profiles = profiles
            s.update(label="✅ 世界画像完成", state="complete")

    actors_by_branch = state.actors_by_branch or {}
    missing_actor_branch = any(not actors_by_branch.get(b.branch_id) for b in branches)
    if missing_actor_branch:
        with st.status("🤖 生成智能体阵列…", expanded=False) as s:
            actors_by_branch = generate_actors_for_branches(
                branches,
                base_world,
                case_config,
                state.llm_client,
            )
            state.actors_by_branch = actors_by_branch
            s.update(label="✅ 智能体就绪", state="complete")

    return profiles, actors_by_branch


# ---------------------------------------------------------------------------
# 以下保留，供非控制台路径使用
# ---------------------------------------------------------------------------

def _get_active_branch(branches: list[BranchWorld]) -> BranchWorld:
    if not branches:
        raise ValueError("没有可运行的世界线。")
    branch_names = [branch.branch_name for branch in branches]
    selected = state.sim_active_branch
    if selected not in branch_names:
        selected = branch_names[0]
        state.sim_active_branch = selected
    return next(branch for branch in branches if branch.branch_name == selected)


def _reset_active_branch() -> None:
    branches = state.branches or []
    if not branches:
        return
    case_config = state.case_config
    active_branch = _get_active_branch(branches)
    logs = state.simulation_logs or {}
    logs[active_branch.branch_id] = []
    state.simulation_logs = logs
    if case_config:
        save_json(logs, get_case_path(case_config.case_id, "05_simulation_log.json"))

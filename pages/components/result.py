import json
import streamlit as st
from engine.divergence_analyzer import analyze_divergence
from engine.forecast_card import generate_forecast_cards
from engine.forecast_ledger import ForecastLedger
from engine.report_generator import generate_report, generate_report_json
from engine.utils import get_case_path, save_json
from pages.state_manager import state
from pages.ui_helpers import run_act_action, render_chip_row
from pages.workbench_state import WorkbenchViewModel

def render_result_overview(vm: WorkbenchViewModel) -> None:
    has_result = bool(vm.timeline or vm.divergence or vm.forecast_cards or vm.report)
    if not has_result:
        return

    st.markdown("### 模拟世界结果")
    with st.container(border=True):
        m1, m2, m3, m4 = st.columns(4)
        finished_branches = sum(1 for branch in vm.branches if branch.simulation_step_count)
        m1.metric("已推演分支", f"{finished_branches}/{len(vm.branches)}")
        m2.metric("事件数", len(vm.timeline))
        m3.metric("预测卡片", len(vm.forecast_cards))
        m4.metric("报告", "已生成" if vm.report else "未生成")

        left, right = st.columns([1.25, 1])
        with left:
            st.markdown("**最新事件流**")
            recent_events = list(reversed(vm.timeline[-4:]))
            if not recent_events:
                st.caption("暂无事件。运行世界线后，这里会显示时间步、状态变化和智能体动作。")
            for event in recent_events:
                with st.container(border=True):
                    st.markdown(f"**{event.branch_name} · {event.time_label or '时间步'}**")
                    st.caption(event.state_summary or "状态更新")
                    if event.agent_actions:
                        render_chip_row(list(event.agent_actions[:3]))
        with right:
            st.markdown("**分支判断**")
            rankings = getattr(vm.divergence, "branch_ranking", None) if vm.divergence else None
            if rankings:
                branch_name_by_id = {branch.branch_id: branch.branch_name for branch in vm.branches}
                for row in rankings[:4]:
                    name = branch_name_by_id.get(row.branch_id, row.branch_id)
                    st.markdown(f"**{name}**")
                    st.progress(float(row.probability))
                    st.caption(row.reason)
            else:
                for branch in vm.branches[:4]:
                    st.markdown(f"**{branch.branch_name}**")
                    st.progress(float(branch.initial_probability))
                    st.caption(branch.latest_state_summary or branch.core_assumption)


def render_comparison_tab(vm: WorkbenchViewModel) -> None:
    render_result_overview(vm)
    
    case_config = state.case_config
    branches = state.branches or []
    logs = state.simulation_logs or {}

    st.markdown("#### 分支演化比对与预测卡片")
    if not branches or not logs:
        st.info("请先完成平行世界推演。")
        return

    def run_comparison():
        divergence = analyze_divergence(branches, logs, state.llm_client, case_config)
        state.divergence = divergence
        save_json(divergence, get_case_path(case_config.case_id, "06_divergence.json"))

        cards = generate_forecast_cards(branches, logs, divergence, case_config, state.llm_client)
        state.forecast_cards = cards
        save_json(cards, get_case_path(case_config.case_id, "07_forecast_cards.json"))
        st.success("收敛分析与预测卡片提取完成。")

    run_act_action(
        "workbench_divergence_analysis",
        "🚀 运行收敛分析与预测卡片生成",
        run_comparison,
        spinner="多世界线坍缩分析中..."
    )

    divergence = state.divergence
    cards = state.forecast_cards

    if divergence:
        st.markdown("##### 🏆 世界线概率坍缩")
        for row in getattr(divergence, "branch_ranking", []):
            st.progress(float(row.probability), text=f"{row.branch_id} - {row.probability:.0%}")
            st.caption(row.reason)

        col_vars, col_events = st.columns(2)
        with col_vars:
            st.markdown("**决定性分歧变量**")
            render_chip_row(getattr(divergence, "critical_divergence_variables", []))
        with col_events:
            st.markdown("**关键转折事件**")
            for evt in getattr(divergence, "key_turning_events", []):
                st.caption(f"- {evt}")

    if cards:
        st.markdown("##### 🃏 可证伪预测卡（预注册）")
        st.caption("每张卡是一次事前承诺：先写死预测、概率、看什么、什么算证伪、什么时候放弃——再交给现实打分。")
        cols = st.columns(len(cards))
        for col, card in zip(cols, cards):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{card.branch_id}**")
                    st.metric("预测概率", f"{card.probability:.0%}")
                    st.caption(f"验证窗口：{card.validation_window}")
                    st.markdown(f"*{card.prediction}*")
                    if card.support_signals:
                        st.markdown("**✅ 支持信号（兑现）**")
                        render_chip_row(card.support_signals)
                    if card.failure_signals:
                        st.markdown("**❌ 证伪信号（失败）**")
                        render_chip_row(card.failure_signals, tone="warn")
                    if card.watch_actions:
                        st.markdown("**🔍 该看什么（最小观察）**")
                        for action in card.watch_actions:
                            st.caption(f"- {action}")
                    if card.kill_condition:
                        st.markdown("**🛑 止损：此世界何时判死**")
                        st.caption(card.kill_condition)
                    if card.no_information_signals:
                        st.markdown("**⚪ 无信息信号（别过度解读）**")
                        render_chip_row(card.no_information_signals, tone="neutral")

        if st.button("📓 存入个人预测台账", type="primary"):
            ledger = ForecastLedger()
            ledger.save_cards(cards, case_config.case_id, case_config.scenario_type)
            st.success(f"已成功将 {len(cards)} 张预测卡片存入「预测账本」。可在侧边栏查看。")

def render_report_tab(vm: WorkbenchViewModel) -> None:
    render_result_overview(vm)
    
    case_config = state.case_config
    base_world = state.base_world
    branches = state.branches or []
    logs = state.simulation_logs or {}
    divergence = state.divergence
    cards = state.forecast_cards

    st.markdown("#### 最终决策报告")
    if not divergence:
        st.info("请先完成分支比对分析。")
        return

    def run_report_generation():
        report_md = generate_report(
            case_config,
            state.material_summary,
            base_world,
            branches,
            state.profiles or [],
            logs,
            divergence,
            cards,
            state.llm_client,
        )
        # generate_report 已把 Markdown 写入 08_final_report.md（case_store 读取的路径），
        # generate_report_json 已写入 08_final_report.json；此处不再重复写错误命名的副本。
        state.report = report_md

        report_json = generate_report_json(
            case_config,
            state.material_summary,
            base_world,
            branches,
            state.profiles or [],
            logs,
            divergence,
            cards,
        )
        state.report_json = report_json
        st.success("推演报告生成完成。")

    run_act_action(
        "workbench_report_gen",
        "🚀 生成最终推演决策报告",
        run_report_generation,
        spinner="汇总智能体推演结果，编写报告中..."
    )

    report = state.report
    if report:
        st.markdown("### 📑 最终推演决策报告")
        cols_dl = st.columns(2)
        with cols_dl[0]:
            st.download_button(
                "⬇️ 下载 Markdown 报告",
                data=report,
                file_name=f"{case_config.case_id}_report.md",
                mime="text/markdown",
                type="primary",
                use_container_width=True
            )
        with cols_dl[1]:
            json_str = json.dumps(state.report_json, ensure_ascii=False, indent=2)
            st.download_button(
                "⬇️ 下载 JSON 报告数据包",
                data=json_str,
                file_name=f"{case_config.case_id}_report.json",
                mime="application/json",
                type="secondary",
                use_container_width=True
            )

        with st.expander("👀 实时预览报告全文", expanded=True):
            st.markdown(report)

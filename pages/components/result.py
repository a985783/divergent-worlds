import json
import streamlit as st
from engine.divergence_analyzer import analyze_divergence
from engine.forecast_card import generate_forecast_cards
from engine.forecast_ledger import ForecastLedger
from engine.report_generator import generate_report, generate_report_json
from engine.utils import get_case_path, save_json
from pages import i18n
from pages.state_manager import state
from pages.ui_helpers import run_act_action, render_chip_row
from pages.workbench_state import WorkbenchViewModel

def render_result_overview(vm: WorkbenchViewModel) -> None:
    has_result = bool(vm.timeline or vm.divergence or vm.forecast_cards or vm.report)
    if not has_result:
        return

    st.markdown(i18n.ui_text("### 模拟世界结果", "### Simulated World Results"))
    with st.container(border=True):
        m1, m2, m3, m4 = st.columns(4)
        finished_branches = sum(1 for branch in vm.branches if branch.simulation_step_count)
        m1.metric(i18n.ui_text("已推演分支", "Simulated branches"), f"{finished_branches}/{len(vm.branches)}")
        m2.metric(i18n.ui_text("事件数", "Events"), len(vm.timeline))
        m3.metric(i18n.ui_text("预测卡片", "Forecast cards"), len(vm.forecast_cards))
        m4.metric(i18n.ui_text("报告", "Report"), i18n.ui_text("已生成", "Generated") if vm.report else i18n.ui_text("未生成", "Not generated"))

        left, right = st.columns([1.25, 1])
        with left:
            st.markdown(i18n.ui_text("**最新事件流**", "**Latest Event Flow**"))
            recent_events = list(reversed(vm.timeline[-4:]))
            if not recent_events:
                st.caption(i18n.ui_text("暂无事件。运行世界线后，这里会显示时间步、状态变化和智能体动作。", "No events yet. Run worldlines to see time steps, state changes, and agent actions."))
            for event in recent_events:
                with st.container(border=True):
                    st.markdown(f"**{event.branch_name} · {event.time_label or i18n.ui_text('时间步', 'time step')}**")
                    st.caption(event.state_summary or i18n.ui_text("状态更新", "State update"))
                    if event.agent_actions:
                        render_chip_row(list(event.agent_actions[:3]))
        with right:
            st.markdown(i18n.ui_text("**分支判断**", "**Branch Judgment**"))
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

    st.markdown(i18n.ui_text("#### 分支演化比对与预测卡片", "#### Branch Evolution Comparison and Forecast Cards"))
    if not branches or not logs:
        st.info(i18n.ui_text("请先完成平行世界推演。", "Complete the parallel-world simulation first."))
        return

    def run_comparison():
        divergence = analyze_divergence(branches, logs, state.llm_client, case_config)
        state.divergence = divergence
        save_json(divergence, get_case_path(case_config.case_id, "06_divergence.json"))

        cards = generate_forecast_cards(branches, logs, divergence, case_config, state.llm_client)
        state.forecast_cards = cards
        save_json(cards, get_case_path(case_config.case_id, "07_forecast_cards.json"))
        st.success(i18n.ui_text("收敛分析与预测卡片提取完成。", "Convergence analysis and forecast cards are complete."))

    run_act_action(
        "workbench_divergence_analysis",
        i18n.ui_text("🚀 运行收敛分析与预测卡片生成", "🚀 Run convergence analysis and forecast-card generation"),
        run_comparison,
        spinner=i18n.ui_text("多世界线坍缩分析中...", "Analyzing multi-worldline collapse...")
    )

    divergence = state.divergence
    cards = state.forecast_cards

    if divergence:
        st.markdown(i18n.ui_text("##### 🏆 世界线概率坍缩", "##### 🏆 Worldline Probability Collapse"))
        for row in getattr(divergence, "branch_ranking", []):
            st.progress(float(row.probability), text=f"{row.branch_id} - {row.probability:.0%}")
            st.caption(row.reason)

        col_vars, col_events = st.columns(2)
        with col_vars:
            st.markdown(i18n.ui_text("**决定性分歧变量**", "**Decisive Divergence Variables**"))
            render_chip_row(getattr(divergence, "critical_divergence_variables", []))
        with col_events:
            st.markdown(i18n.ui_text("**关键转折事件**", "**Key Turning Events**"))
            for evt in getattr(divergence, "key_turning_events", []):
                st.caption(f"- {evt}")

    if cards:
        st.markdown(i18n.ui_text("##### 🃏 可证伪预测卡（预注册）", "##### 🃏 Falsifiable Forecast Cards (Pre-registered)"))
        st.caption(i18n.ui_text("每张卡是一次事前承诺：先写死预测、概率、看什么、什么算证伪、什么时候放弃——再交给现实打分。", "Each card is an ex-ante commitment: prediction, probability, what to watch, what falsifies it, and when to abandon the branch before reality scores it."))
        cols = st.columns(len(cards))
        for col, card in zip(cols, cards):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{card.branch_id}**")
                    st.metric(i18n.ui_text("预测概率", "Forecast probability"), f"{card.probability:.0%}")
                    st.caption(i18n.format_text("验证窗口：{window}", "Validation window: {window}", window=card.validation_window))
                    st.markdown(f"*{card.prediction}*")
                    if card.support_signals:
                        st.markdown(i18n.ui_text("**✅ 支持信号（兑现）**", "**✅ Support Signals**"))
                        render_chip_row(card.support_signals)
                    if card.failure_signals:
                        st.markdown(i18n.ui_text("**❌ 证伪信号（失败）**", "**❌ Failure Signals**"))
                        render_chip_row(card.failure_signals, tone="warn")
                    if card.watch_actions:
                        st.markdown(i18n.ui_text("**🔍 该看什么（最小观察）**", "**🔍 Watch Actions**"))
                        for action in card.watch_actions:
                            st.caption(f"- {action}")
                    if card.kill_condition:
                        st.markdown(i18n.ui_text("**🛑 止损：此世界何时判死**", "**🛑 Kill Condition**"))
                        st.caption(card.kill_condition)
                    if card.no_information_signals:
                        st.markdown(i18n.ui_text("**⚪ 无信息信号（别过度解读）**", "**⚪ No-information Signals**"))
                        render_chip_row(card.no_information_signals, tone="neutral")

        if st.button(i18n.ui_text("📓 存入个人预测台账", "📓 Save to personal forecast ledger"), type="primary"):
            ledger = ForecastLedger()
            ledger.save_cards(cards, case_config.case_id, case_config.scenario_type)
            st.success(i18n.format_text("已成功将 {count} 张预测卡片存入「预测账本」。可在侧边栏查看。", "Saved {count} forecast cards to the Forecast Ledger.", count=len(cards)))

def render_report_tab(vm: WorkbenchViewModel) -> None:
    render_result_overview(vm)
    
    case_config = state.case_config
    base_world = state.base_world
    branches = state.branches or []
    logs = state.simulation_logs or {}
    divergence = state.divergence
    cards = state.forecast_cards

    st.markdown(i18n.ui_text("#### 最终决策报告", "#### Final Decision Report"))
    if not divergence:
        st.info(i18n.ui_text("请先完成分支比对分析。", "Complete branch comparison first."))
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
        st.success(i18n.ui_text("推演报告生成完成。", "Simulation report generated."))

    run_act_action(
        "workbench_report_gen",
        i18n.ui_text("🚀 生成最终推演决策报告", "🚀 Generate final simulation report"),
        run_report_generation,
        spinner=i18n.ui_text("汇总智能体推演结果，编写报告中...", "Summarizing agent simulation results and writing the report...")
    )

    report = state.report
    if report:
        st.markdown(i18n.ui_text("### 📑 最终推演决策报告", "### 📑 Final Simulation Report"))
        cols_dl = st.columns(2)
        with cols_dl[0]:
            st.download_button(
                i18n.ui_text("⬇️ 下载 Markdown 报告", "⬇️ Download Markdown report"),
                data=report,
                file_name=f"{case_config.case_id}_report.md",
                mime="text/markdown",
                type="primary",
                use_container_width=True
            )
        with cols_dl[1]:
            json_str = json.dumps(state.report_json, ensure_ascii=False, indent=2)
            st.download_button(
                i18n.ui_text("⬇️ 下载 JSON 报告数据包", "⬇️ Download JSON report bundle"),
                data=json_str,
                file_name=f"{case_config.case_id}_report.json",
                mime="application/json",
                type="secondary",
                use_container_width=True
            )

        with st.expander(i18n.ui_text("👀 实时预览报告全文", "👀 Live report preview"), expanded=True):
            st.markdown(report)

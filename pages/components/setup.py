import streamlit as st
from engine.schemas import CaseConfig
from pages import i18n
from pages.state_manager import state
from pages.components.shared import (
    _activate_case,
    horizon_label_for_value,
    horizon_options,
    scenario_label_for_value,
    scenario_options,
    scenario_template,
)

def render_new_case_setup() -> None:
    with st.container(border=True):
        st.markdown(i18n.ui_text("#### 新建自定义项目", "#### Create Custom Project"))
        
        # Initialize default config values if not present
        if not state.case_name_val:
            state.case_name_val = i18n.ui_text("闲鱼收入波动预测", "Xianyu Revenue Volatility Forecast")
            template = scenario_template("ecommerce")
            state.question_val = template["question"]
            state.branches_val = template["branches"]
            state.scenario_val = scenario_label_for_value("ecommerce")
            state.horizon_val = horizon_label_for_value("30d")
            state.branch_count_val = 5
            state.agent_count_val = 6
            state.auto_generate_val = True

        def on_scenario_change():
            val = scenario_options()[state.scenario_val]
            template = scenario_template(val)
            state.question_val = template["question"]
            state.branches_val = template["branches"]

        options = scenario_options()
        horizons = horizon_options()
        if state.scenario_val not in options:
            state.scenario_val = scenario_label_for_value("ecommerce")
        if state.horizon_val not in horizons:
            state.horizon_val = horizon_label_for_value("30d")

        case_name = st.text_input(i18n.ui_text("项目名称", "Project name"), key="case_name_val")
        question = st.text_area(i18n.ui_text("核心推演问题", "Core simulation question"), key="question_val", height=80)
        
        scenario_label = st.selectbox(i18n.ui_text("场景类型", "Scenario type"), list(options.keys()), key="scenario_val", on_change=on_scenario_change)
        horizon_label = st.selectbox(i18n.ui_text("预测窗口", "Forecast horizon"), list(horizons.keys()), key="horizon_val")
        
        col1, col2 = st.columns(2)
        with col1:
            branch_count = st.selectbox(i18n.ui_text("平行分支数量", "Number of branches"), [3, 5, 7], key="branch_count_val")
        with col2:
            agent_count = st.selectbox(i18n.ui_text("参演智能体数量", "Number of agents"), [5, 6, 8, 10], key="agent_count_val")
            
        auto_generate = st.checkbox(i18n.ui_text("让大模型自动发散剩余分支", "Let the model generate remaining branches"), key="auto_generate_val")
        branch_text = st.text_area(i18n.ui_text("指定关键分支路线（可选，每行一个）", "Specify key branch routes (optional, one per line)"), key="branches_val", height=70)
        
        submitted = st.button(i18n.ui_text("🚀 初始化项目", "🚀 Initialize project"), type="primary", use_container_width=True)
        if submitted:
            try:
                config = CaseConfig(
                    case_name=case_name.strip(),
                    question=question.strip(),
                    scenario_type=options[scenario_label],
                    horizon=horizons[horizon_label],
                    branch_count=branch_count,
                    agent_count=agent_count,
                    auto_generate_branches=auto_generate,
                    user_specified_branches=[
                        line.strip() for line in branch_text.splitlines() if line.strip()
                    ],
                )
                _activate_case(config, demo=False)
                st.rerun()
            except Exception as exc:
                st.error(i18n.format_text("创建失败：{exc}", "Create failed: {exc}", exc=exc))

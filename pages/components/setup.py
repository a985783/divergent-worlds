import streamlit as st
from engine.schemas import CaseConfig
from pages.state_manager import state
from pages.components.shared import SCENARIOS, HORIZONS, SCENARIO_TEMPLATES, _activate_case

def render_new_case_setup() -> None:
    with st.container(border=True):
        st.markdown("#### 新建自定义项目")
        
        # Initialize default config values if not present
        if not state.case_name_val:
            state.case_name_val = "闲鱼收入波动预测"
            state.question_val = SCENARIO_TEMPLATES["ecommerce"]["question"]
            state.branches_val = SCENARIO_TEMPLATES["ecommerce"]["branches"]
            state.scenario_val = "电商 / 平台经营"
            state.horizon_val = "30 天"
            state.branch_count_val = 5
            state.agent_count_val = 6
            state.auto_generate_val = True

        def on_scenario_change():
            val = SCENARIOS[state.scenario_val]
            template = SCENARIO_TEMPLATES.get(val, SCENARIO_TEMPLATES["custom"])
            state.question_val = template["question"]
            state.branches_val = template["branches"]

        case_name = st.text_input("项目名称", key="case_name_val")
        question = st.text_area("核心推演问题", key="question_val", height=80)
        
        scenario_label = st.selectbox("场景类型", list(SCENARIOS.keys()), key="scenario_val", on_change=on_scenario_change)
        horizon_label = st.selectbox("预测窗口", list(HORIZONS.keys()), key="horizon_val")
        
        col1, col2 = st.columns(2)
        with col1:
            branch_count = st.selectbox("平行分支数量", [3, 5, 7], key="branch_count_val")
        with col2:
            agent_count = st.selectbox("参演智能体数量", [5, 6, 8, 10], key="agent_count_val")
            
        auto_generate = st.checkbox("让大模型自动发散剩余分支", key="auto_generate_val")
        branch_text = st.text_area("指定关键分支路线（可选，每行一个）", key="branches_val", height=70)
        
        submitted = st.button("🚀 初始化项目", type="primary", use_container_width=True)
        if submitted:
            try:
                config = CaseConfig(
                    case_name=case_name.strip(),
                    question=question.strip(),
                    scenario_type=SCENARIOS[scenario_label],
                    horizon=HORIZONS[horizon_label],
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
                st.error(f"创建失败：{exc}")

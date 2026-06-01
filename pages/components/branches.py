import json
from typing import Any
import streamlit as st
from pydantic import TypeAdapter
from engine.schemas import CaseConfig, BaseWorld, BranchWorld
from engine.utils import get_case_path, save_json
from engine.fork_generator import generate_branches, validate_branch_diversity, assign_branch_type
from pages import i18n
from pages.state_manager import state
from pages.ui_helpers import run_act_action

from pages.workbench_visuals import render_world_map, render_branch_lanes

def render_branches_section(case_config: CaseConfig, base_world: BaseWorld, vm: Any = None) -> None:
    if vm and vm.branches:
        col1, col2 = st.columns([1, 1])
        with col1:
            render_world_map(vm)
        with col2:
            render_branch_lanes(vm.branches)
    branches = state.branches or []
    
    with st.container(border=True):
        if not branches:
            def sprout_branches():
                brs = generate_branches(base_world, case_config, state.llm_client)
                for b in brs:
                    b.branch_type = assign_branch_type(b)
                state.branches = brs
                score, warnings = validate_branch_diversity(brs)
                if warnings:
                    st.warning(i18n.format_text("平行分支已生成，分数值：{score:.2f}。存在多样性警告。", "Parallel branches generated; diversity score {score:.2f}. Diversity warnings exist.", score=score))
                else:
                    st.success(i18n.format_text("平行分支生成成功，多样性分数：{score:.2f}。", "Parallel branches generated. Diversity score: {score:.2f}.", score=score))

            run_act_action(
                "workbench_branches_sprout",
                i18n.ui_text("🚀 发散平行未来分支", "🚀 Generate parallel future branches"),
                sprout_branches,
                spinner=i18n.ui_text("发散平行未来路线中...", "Generating parallel future routes..."),
            )
        else:
            score, warnings = validate_branch_diversity(branches)
            st.markdown(i18n.format_text("**分支多样性评分：`{score:.2f}`**", "**Branch diversity score: `{score:.2f}`**", score=score))
            if warnings:
                for w in warnings:
                    st.warning(w)
            
            with st.expander(i18n.ui_text("🔗 同族分支软合并", "🔗 Soft-merge sibling branches"), expanded=False):
                st.caption(i18n.ui_text("把相似路线或演化重叠的分支标记为“同族分支”。", "Mark similar or overlapping branches as sibling branches."))
                branch_names = [b.branch_name for b in branches]
                m_cols = st.columns(2)
                with m_cols[0]:
                    b1 = st.selectbox(i18n.ui_text("分支 A", "Branch A"), branch_names, key="merg_b1")
                with m_cols[1]:
                    b2 = st.selectbox(i18n.ui_text("分支 B", "Branch B"), [n for n in branch_names if n != b1], key="merg_b2")
                
                if st.button(i18n.ui_text("合并关系绑定", "Bind merge relationship"), use_container_width=True):
                    b1_obj = next(b for b in branches if b.branch_name == b1)
                    b2_obj = next(b for b in branches if b.branch_name == b2)
                    if b2_obj.branch_name not in b1_obj.sibling_branches:
                        b1_obj.sibling_branches.append(b2_obj.branch_name)
                    if b1_obj.branch_name not in b2_obj.sibling_branches:
                        b2_obj.sibling_branches.append(b1_obj.branch_name)
                    st.success(i18n.format_text("已将【{b1}】与【{b2}】绑定为同族。", "Bound {b1} and {b2} as sibling branches.", b1=b1, b2=b2))
                    st.rerun()

            with st.expander(i18n.ui_text("🛠️ 编辑/确认平行分支", "🛠️ Edit/confirm parallel branches"), expanded=False):
                edited = st.text_area(
                    i18n.ui_text("分支世界列表 JSON", "Branch-world list JSON"),
                    value=json.dumps([b.model_dump(mode="json") for b in branches], ensure_ascii=False, indent=2),
                    height=200,
                )
                if st.button(i18n.ui_text("💾 锁定所有平行分支", "💾 Lock all parallel branches"), type="primary", use_container_width=True):
                    try:
                        confirmed = TypeAdapter(list[BranchWorld]).validate_json(edited)
                        state.branches = confirmed
                        save_json(confirmed, get_case_path(case_config.case_id, "03_branches.json"))
                        st.success(i18n.ui_text("分支设定已锁定，现在可以前往“智能体推演控制台”运行模拟！", "Branch settings locked. You can now run the simulation console."))
                        st.rerun()
                    except Exception as e:
                        st.error(i18n.format_text("校验失败：{error}", "Validation failed: {error}", error=e))

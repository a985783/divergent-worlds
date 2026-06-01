import json
from typing import Any
import streamlit as st
from engine.schemas import CaseConfig, BaseWorld
from engine.utils import get_case_path, save_json
from engine.world_builder import build_base_world
from engine.ingest import detect_all_forks
from pages.state_manager import state
from pages import i18n
from pages.ui_helpers import run_act_action

from pages.workbench_visuals import render_world_map

def render_baseworld_section(case_config: CaseConfig, material_summary: Any, vm: Any = None) -> None:
    if vm and vm.base_world:
        render_world_map(vm)
    if state.csv_data_rows is not None and state.csv_data_rows:
        with st.expander(i18n.ui_text("📊 自动分叉与变动检测 (FR-6)", "📊 Automatic Fork and Change Detection (FR-6)"), expanded=False):
            st.caption(i18n.ui_text("扫描上传 CSV 数值序列发现的数据突变点：", "Detected breakpoints in uploaded CSV numeric series:"))
            forks = detect_all_forks(state.csv_data_rows)
            if forks:
                st.dataframe(
                    [
                        {
                            i18n.ui_text("指标", "Metric"): fork["metric"],
                            i18n.ui_text("算法", "Method"): fork["method"],
                            i18n.ui_text("偏离", "Deviation"): fork.get("deviation") or fork.get("z_score"),
                            i18n.ui_text("因果发散解释", "Divergence interpretation"): " / ".join(fork["possible_interpretations"]),
                        }
                        for fork in forks[:5]
                    ],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success(i18n.ui_text("数值波动平稳，无剧变异常点。", "Numeric fluctuation is stable; no sharp anomaly found."))

    base_world = state.base_world
    
    with st.container(border=True):
        if not base_world:
            def generate_baseline():
                state.base_world = build_base_world(material_summary, case_config, state.llm_client)
                st.success(i18n.ui_text("T0 基线世界已生成。", "T0 base world generated."))
            run_act_action(
                "workbench_base_world_gen",
                i18n.ui_text("🚀 提取 T0 基线世界状态", "🚀 Extract T0 base-world state"),
                generate_baseline,
                spinner=i18n.ui_text("建模世界属性中...", "Modeling world attributes..."),
            )
        else:
            st.success(i18n.format_text("基线世界：{name} (锚点：{anchor})", "Base world: {name} (anchor: {anchor})", name=base_world.name, anchor=base_world.time_anchor))
            st.caption(base_world.summary)
            
            with st.expander(i18n.ui_text("🛠️ 编辑/确认基线世界数据 (Pydantic 校验)", "🛠️ Edit/confirm base-world data (Pydantic validation)"), expanded=False):
                edited = st.text_area(
                    i18n.ui_text("初始世界 JSON", "Base-world JSON"),
                    value=json.dumps(base_world.model_dump(mode="json"), ensure_ascii=False, indent=2),
                    height=200,
                )
                if st.button(i18n.ui_text("💾 确认并锁定初始世界状态", "💾 Confirm and lock base-world state"), type="primary", use_container_width=True):
                    try:
                        confirmed = BaseWorld.model_validate_json(edited)
                        state.base_world = confirmed
                        save_json(confirmed, get_case_path(case_config.case_id, "02_base_world.json"))
                        st.success(i18n.ui_text("基线世界已锁定。", "Base world locked."))
                        st.rerun()
                    except Exception as e:
                        st.error(i18n.format_text("校验失败：{error}", "Validation failed: {error}", error=e))

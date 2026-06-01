import json
from typing import Any
import streamlit as st
from engine.schemas import CaseConfig, BaseWorld
from engine.utils import get_case_path, save_json
from engine.world_builder import build_base_world
from engine.ingest import detect_all_forks
from pages.state_manager import state
from pages.ui_helpers import run_act_action

from pages.workbench_visuals import render_world_map

def render_baseworld_section(case_config: CaseConfig, material_summary: Any, vm: Any = None) -> None:
    if vm and vm.base_world:
        render_world_map(vm)
    if state.csv_data_rows is not None and state.csv_data_rows:
        with st.expander("📊 自动分叉与变动检测 (FR-6)", expanded=False):
            st.caption("扫描上传 CSV 数值序列发现的数据突变点：")
            forks = detect_all_forks(state.csv_data_rows)
            if forks:
                st.dataframe(
                    [
                        {
                            "指标": fork["metric"],
                            "算法": fork["method"],
                            "偏离": fork.get("deviation") or fork.get("z_score"),
                            "因果发散解释": " / ".join(fork["possible_interpretations"]),
                        }
                        for fork in forks[:5]
                    ],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("数值波动平稳，无剧变异常点。")

    base_world = state.base_world
    
    with st.container(border=True):
        if not base_world:
            def generate_baseline():
                state.base_world = build_base_world(material_summary, case_config, state.llm_client)
                st.success("T0 基线世界已生成。")
            run_act_action("workbench_base_world_gen", "🚀 提取 T0 基线世界状态", generate_baseline, spinner="建模世界属性中...")
        else:
            st.success(f"基线世界：{base_world.name} (锚点：{base_world.time_anchor})")
            st.caption(base_world.summary)
            
            with st.expander("🛠️ 编辑/确认基线世界数据 (Pydantic 校验)", expanded=False):
                edited = st.text_area(
                    "初始世界 JSON",
                    value=json.dumps(base_world.model_dump(mode="json"), ensure_ascii=False, indent=2),
                    height=200,
                )
                if st.button("💾 确认并锁定初始世界状态", type="primary", use_container_width=True):
                    try:
                        confirmed = BaseWorld.model_validate_json(edited)
                        state.base_world = confirmed
                        save_json(confirmed, get_case_path(case_config.case_id, "02_base_world.json"))
                        st.success("基线世界已锁定。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"校验失败：{e}")

import streamlit as st
from pathlib import Path
from engine.schemas import CaseConfig
from engine.ingest import summarize_materials
from pages.state_manager import state
from pages.ui_helpers import render_chip_row, run_llm_action
from pages.components.shared import _load_material_preview, _collect_materials, SUPPORTED_EXTENSIONS

def render_material_ingestion_section(case_config: CaseConfig) -> None:
    demo_paths = [Path(path) for path in state.demo_material_paths]
    if demo_paths:
        with st.container(border=True):
            st.markdown("**已加载示例案例的演示材料**")
            render_chip_row([path.name for path in demo_paths], tone="good")
            
            def summarize_demo() -> None:
                preview = _load_material_preview(demo_paths)
                state.material_preview = preview
                raw_texts = [item["text"] for item in preview]
                state.material_summary = summarize_materials(raw_texts, state.llm_client, case_config)
                st.success("示例材料解析成功。")
            
            ran = run_llm_action(
                "workbench_demo_parse",
                "🚀 解析并分析示例材料",
                summarize_demo,
                spinner="正在分析示例事实、变量和不确定性..."
            )
            if ran and state.material_summary:
                st.rerun()
    else:
        with st.container(border=True):
            tab_upload, tab_folder, tab_paste = st.tabs(["📁 文件/ZIP", "💻 本地文件夹", "📝 直接粘贴"])
            with tab_upload:
                uploads = st.file_uploader("选择材料文件或 ZIP 包", type=[*sorted(SUPPORTED_EXTENSIONS), "zip"], accept_multiple_files=True)
            with tab_folder:
                folder_path = st.text_input("本地绝对路径", placeholder="/Users/Desktop/reference")
            with tab_paste:
                pasted_text = st.text_area("粘贴背景资料", height=80)

            col_preview, col_parse = st.columns(2)
            with col_preview:
                if st.button("👀 仅预览材料", use_container_width=True):
                    try:
                        state.material_preview = _collect_materials(uploads, pasted_text, folder_path, case_config.case_id)
                        st.success("预览生成成功。")
                    except Exception as e:
                        st.error(str(e))
            with col_parse:
                def run_custom_parse():
                    materials = _collect_materials(uploads, pasted_text, folder_path, case_config.case_id)
                    state.material_preview = materials
                    raw_texts = [item["text"] for item in materials]
                    if not raw_texts:
                        st.warning("无任何有效材料。")
                        return
                    state.material_summary = summarize_materials(raw_texts, state.llm_client, case_config)
                    st.success("解析成功。")

                ran = run_llm_action("workbench_custom_parse", "🚀 解析并分析材料", run_custom_parse, spinner="提取事实、不确定性...")
                if ran and state.material_summary:
                    st.rerun()

    # Materials Preview / Summary metrics
    preview = state.material_preview
    summary = state.material_summary

    if preview:
        with st.expander("👀 查看材料原文预览", expanded=False):
            tbs = st.tabs([item["name"] for item in preview])
            for tb, item in zip(tbs, preview):
                with tb:
                    st.text_area("提取文本", value=item["text"][:3000], height=120, disabled=True, key=f"preview_{item['name']}")

    if summary:
        with st.container(border=True):
            st.markdown("**🔍 抽取事实概览**")
            col1, col2, col3 = st.columns(3)
            col1.metric("事实", len(summary.facts))
            col2.metric("变量", len(summary.variables))
            col3.metric("未确定项", len(summary.uncertainties))

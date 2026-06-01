import streamlit as st
from pathlib import Path
from engine.schemas import CaseConfig
from engine.ingest import summarize_materials
from pages import i18n
from pages.state_manager import state
from pages.ui_helpers import render_chip_row, run_llm_action
from pages.components.shared import _load_material_preview, _collect_materials, SUPPORTED_EXTENSIONS

def render_material_ingestion_section(case_config: CaseConfig) -> None:
    demo_paths = [Path(path) for path in state.demo_material_paths]
    if demo_paths:
        with st.container(border=True):
            st.markdown(i18n.ui_text("**已加载示例案例的演示材料**", "**Demo materials loaded**"))
            render_chip_row([path.name for path in demo_paths], tone="good")
            
            def summarize_demo() -> None:
                preview = _load_material_preview(demo_paths)
                state.material_preview = preview
                raw_texts = [item["text"] for item in preview]
                state.material_summary = summarize_materials(raw_texts, state.llm_client, case_config)
                st.success(i18n.ui_text("示例材料解析成功。", "Demo materials parsed."))
            
            ran = run_llm_action(
                "workbench_demo_parse",
                i18n.ui_text("🚀 解析并分析示例材料", "🚀 Parse and analyze demo materials"),
                summarize_demo,
                spinner=i18n.ui_text("正在分析示例事实、变量和不确定性...", "Analyzing demo facts, variables, and uncertainties...")
            )
            if ran and state.material_summary:
                st.rerun()
    else:
        with st.container(border=True):
            tab_upload, tab_folder, tab_paste = st.tabs(
                [
                    i18n.ui_text("📁 文件/ZIP", "📁 Files/ZIP"),
                    i18n.ui_text("💻 本地文件夹", "💻 Local folder"),
                    i18n.ui_text("📝 直接粘贴", "📝 Paste text"),
                ]
            )
            with tab_upload:
                uploads = st.file_uploader(
                    i18n.ui_text("选择材料文件或 ZIP 包", "Choose material files or a ZIP archive"),
                    type=[*sorted(SUPPORTED_EXTENSIONS), "zip"],
                    accept_multiple_files=True,
                )
            with tab_folder:
                folder_path = st.text_input(i18n.ui_text("本地绝对路径", "Local absolute path"), placeholder="/Users/Desktop/reference")
            with tab_paste:
                pasted_text = st.text_area(i18n.ui_text("粘贴背景资料", "Paste background material"), height=80)

            col_preview, col_parse = st.columns(2)
            with col_preview:
                if st.button(i18n.ui_text("👀 仅预览材料", "👀 Preview materials only"), use_container_width=True):
                    try:
                        state.material_preview = _collect_materials(uploads, pasted_text, folder_path, case_config.case_id)
                        st.success(i18n.ui_text("预览生成成功。", "Preview generated."))
                    except Exception as e:
                        st.error(str(e))
            with col_parse:
                def run_custom_parse():
                    materials = _collect_materials(uploads, pasted_text, folder_path, case_config.case_id)
                    state.material_preview = materials
                    raw_texts = [item["text"] for item in materials]
                    if not raw_texts:
                        st.warning(i18n.ui_text("无任何有效材料。", "No valid materials found."))
                        return
                    state.material_summary = summarize_materials(raw_texts, state.llm_client, case_config)
                    st.success(i18n.ui_text("解析成功。", "Parsed successfully."))

                ran = run_llm_action(
                    "workbench_custom_parse",
                    i18n.ui_text("🚀 解析并分析材料", "🚀 Parse and analyze materials"),
                    run_custom_parse,
                    spinner=i18n.ui_text("提取事实、不确定性...", "Extracting facts and uncertainties..."),
                )
                if ran and state.material_summary:
                    st.rerun()

    # Materials Preview / Summary metrics
    preview = state.material_preview
    summary = state.material_summary

    if preview:
        with st.expander(i18n.ui_text("👀 查看材料原文预览", "👀 View raw material preview"), expanded=False):
            tbs = st.tabs([item["name"] for item in preview])
            for tb, item in zip(tbs, preview):
                with tb:
                    st.text_area(i18n.ui_text("提取文本", "Extracted text"), value=item["text"][:3000], height=120, disabled=True, key=f"preview_{item['name']}")

    if summary:
        with st.container(border=True):
            st.markdown(i18n.ui_text("**🔍 抽取事实概览**", "**🔍 Extracted Fact Overview**"))
            col1, col2, col3 = st.columns(3)
            col1.metric(i18n.ui_text("事实", "Facts"), len(summary.facts))
            col2.metric(i18n.ui_text("变量", "Variables"), len(summary.variables))
            col3.metric(i18n.ui_text("未确定项", "Uncertainties"), len(summary.uncertainties))

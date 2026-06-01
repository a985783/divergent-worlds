from __future__ import annotations

import streamlit as st

from engine.forecast_ledger import ForecastLedger
from pages import i18n, nav


def render() -> None:
    st.title(i18n.ui_text("📒 预测校准账本", "📒 Forecast Calibration Ledger"))
    st.caption(i18n.ui_text("跨项目跟踪预测记录，并定期核对现实反馈。", "Track forecast records across projects and periodically score real-world feedback."))

    ledger = ForecastLedger()
    summary = ledger.get_summary()

    col1, col2, col3 = st.columns(3)
    col1.metric(i18n.ui_text("📌 预测总数", "📌 Total forecasts"), summary["total_forecasts"])
    col2.metric(i18n.ui_text("✅ 已评分", "✅ Scored"), summary["scored_forecasts"])
    col3.metric(
        i18n.ui_text("🎯 平均 Brier", "🎯 Average Brier"),
        i18n.ui_text("暂无", "None yet") if summary["average_brier"] is None else f"{summary['average_brier']:.3f}",
    )

    st.markdown(i18n.ui_text("### 📊 账本数据可视化", "### 📊 Ledger Visualizations"))
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        # 1. 状态分布饼图
        status_dist = ledger.get_status_distribution()
        if status_dist:
            try:
                from streamlit_echarts import st_echarts

                status_data = [
                    {"value": count, "name": status} for status, count in status_dist.items()
                ]
                pie_options = {
                    "title": {"text": i18n.ui_text("预测状态分布", "Forecast Status Distribution"), "left": "center", "textStyle": {"color": "#f8fafc"}},
                    "tooltip": {"trigger": "item"},
                    "legend": {"orient": "vertical", "left": "left", "textStyle": {"color": "#f8fafc"}},
                    "series": [
                        {
                            "name": i18n.ui_text("数量", "Count"),
                            "type": "pie",
                            "radius": "50%",
                            "data": status_data,
                            "emphasis": {
                                "itemStyle": {
                                    "shadowBlur": 10,
                                    "shadowOffsetX": 0,
                                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                                }
                            }
                        }
                    ]
                }
                st_echarts(options=pie_options, height="260px")
            except Exception:
                for status, count in status_dist.items():
                    st.markdown(f"- **{status}**：{count}")
        else:
            st.info(i18n.ui_text("暂无足够的状态分布数据。", "Not enough status distribution data yet."))

    with col_chart2:
        # 2. 场景统计
        st.markdown(i18n.ui_text("**场景精度对比**", "**Scenario Accuracy Comparison**"))
        scenario_stats = ledger.get_scenario_breakdown()
        if scenario_stats:
            st.dataframe(
                [
                    {
                        i18n.ui_text("场景类型", "Scenario type"): row["scenario_type"],
                        i18n.ui_text("预测数", "Forecasts"): row["total"],
                        i18n.ui_text("已评分", "Scored"): row["scored"],
                        i18n.ui_text("平均 Brier", "Average Brier"): f"{row['avg_brier']:.3f}" if row["avg_brier"] is not None else i18n.ui_text("暂无", "None yet")
                    }
                    for row in scenario_stats
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(i18n.ui_text("暂无场景统计数据。", "No scenario statistics yet."))

    # 3. Brier 分数趋势
    all_forecasts = ledger.list_forecasts()
    scored_forecasts = [f for f in all_forecasts if f.brier_score is not None]
    scored_forecasts.sort(key=lambda x: x.updated_at)
    
    if scored_forecasts:
        st.markdown("<br>", unsafe_allow_html=True)
        times = [f.updated_at.strftime("%Y-%m-%d %H:%M") for f in scored_forecasts]
        scores = [f.brier_score for f in scored_forecasts]
        try:
            from streamlit_echarts import st_echarts

            trend_options = {
                "title": {"text": i18n.ui_text("Brier 校准得分趋势 (越低越好)", "Brier Calibration Trend (lower is better)"), "left": "center", "textStyle": {"color": "#f8fafc"}},
                "tooltip": {"trigger": "axis"},
                "xAxis": {
                    "type": "category",
                    "data": times,
                    "axisLabel": {"color": "#f8fafc"},
                    "axisLine": {"lineStyle": {"color": "#475569"}}
                },
                "yAxis": {
                    "type": "value",
                    "axisLabel": {"color": "#f8fafc"},
                    "axisLine": {"lineStyle": {"color": "#475569"}},
                    "splitLine": {"lineStyle": {"color": "#334155"}}
                },
                "series": [{
                    "data": scores,
                    "type": "line",
                    "smooth": True,
                    "lineStyle": {"color": "#10b981"},
                    "itemStyle": {"color": "#10b981"}
                }]
            }
            st_echarts(options=trend_options, height="260px")
        except Exception:
            st.line_chart({"Brier": scores})

    st.markdown(i18n.ui_text("<br>### 📖 历史预测详情", "<br>### 📖 Historical Forecast Details"), unsafe_allow_html=True)
    status = st.selectbox(
        i18n.ui_text("🔍 状态筛选", "🔍 Status filter"),
        [i18n.ui_text("全部", "all"), "pending", "supported", "failed", "no_information", "expired"],
    )
    entries = ledger.list_forecasts(None if status in {"全部", "all"} else status)
    
    if entries:
        st.dataframe(
            [
                {
                    i18n.ui_text("预测", "Forecast"): entry.prediction,
                    i18n.ui_text("概率", "Probability"): entry.probability,
                    i18n.ui_text("状态", "Status"): entry.status,
                    i18n.ui_text("验证窗口", "Validation window"): entry.validation_window,
                    "Brier": entry.brier_score,
                    i18n.ui_text("项目 ID", "Project ID"): entry.case_id,
                    i18n.ui_text("预测 ID", "Forecast ID"): entry.forecast_id,
                }
                for entry in entries
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(i18n.ui_text("暂无该状态下的预测记录。", "No forecasts for this status."))

    st.divider()
    with st.container(border=True):
        st.markdown(i18n.ui_text("**✏️ 更新预测结果**", "**✏️ Update Forecast Outcome**"))
        st.caption(i18n.ui_text("当现实中发生事件后，回来给你的预测评分。", "When reality unfolds, come back here to score your forecast."))
        
        if entries:
            forecast_id = st.selectbox(i18n.ui_text("📝 选择要更新的预测", "📝 Choose forecast to update"), [entry.forecast_id for entry in entries])
            new_status = st.selectbox(
                i18n.ui_text("📉 结果状态", "📉 Outcome status"),
                ["supported", "failed", "no_information", "expired"],
            )
            outcome = st.text_area(i18n.ui_text("🗒️ 现实反馈 / 结果说明", "🗒️ Real-world feedback / outcome notes"), height=100)
            notes = st.text_area(i18n.ui_text("🔖 备注", "🔖 Notes"), height=80)
            
            if st.button(i18n.ui_text("💾 保存更新结果", "💾 Save outcome update"), type="primary"):
                try:
                    brier = ledger.update_outcome(forecast_id, new_status, outcome, notes)
                    if brier is None:
                        st.success(i18n.ui_text("结果已保存；该状态不计算 Brier。", "Outcome saved; this status does not calculate Brier."))
                    else:
                        st.success(i18n.format_text("结果已保存，Brier = {brier:.3f}", "Outcome saved. Brier = {brier:.3f}", brier=brier))
                    st.rerun()
                except Exception as exc:
                    st.error(i18n.format_text("保存失败：{exc}", "Save failed: {exc}", exc=exc))

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(i18n.ui_text("🏠 返回推演台首页", "🏠 Back to home"), width="stretch"):
        nav.switch_to("home")

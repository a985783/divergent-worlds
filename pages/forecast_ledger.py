from __future__ import annotations

import streamlit as st

from engine.forecast_ledger import ForecastLedger
from pages import nav


def render() -> None:
    st.title("📒 预测校准账本")
    st.caption("跨项目跟踪预测记录，并定期核对现实反馈。")

    ledger = ForecastLedger()
    summary = ledger.get_summary()

    col1, col2, col3 = st.columns(3)
    col1.metric("📌 预测总数", summary["total_forecasts"])
    col2.metric("✅ 已评分", summary["scored_forecasts"])
    col3.metric(
        "🎯 平均 Brier",
        "暂无" if summary["average_brier"] is None else f"{summary['average_brier']:.3f}",
    )

    st.markdown("### 📊 账本数据可视化")
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
                    "title": {"text": "预测状态分布", "left": "center", "textStyle": {"color": "#f8fafc"}},
                    "tooltip": {"trigger": "item"},
                    "legend": {"orient": "vertical", "left": "left", "textStyle": {"color": "#f8fafc"}},
                    "series": [
                        {
                            "name": "数量",
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
            st.info("暂无足够的状态分布数据。")

    with col_chart2:
        # 2. 场景统计
        st.markdown("**场景精度对比**")
        scenario_stats = ledger.get_scenario_breakdown()
        if scenario_stats:
            st.dataframe(
                [
                    {
                        "场景类型": row["scenario_type"],
                        "预测数": row["total"],
                        "已评分": row["scored"],
                        "平均 Brier": f"{row['avg_brier']:.3f}" if row["avg_brier"] is not None else "暂无"
                    }
                    for row in scenario_stats
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("暂无场景统计数据。")

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
                "title": {"text": "Brier 校准得分趋势 (越低越好)", "left": "center", "textStyle": {"color": "#f8fafc"}},
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

    st.markdown("<br>### 📖 历史预测详情", unsafe_allow_html=True)
    status = st.selectbox(
        "🔍 状态筛选",
        ["全部", "pending", "supported", "failed", "no_information", "expired"],
    )
    entries = ledger.list_forecasts(None if status == "全部" else status)
    
    if entries:
        st.dataframe(
            [
                {
                    "预测": entry.prediction,
                    "概率": entry.probability,
                    "状态": entry.status,
                    "验证窗口": entry.validation_window,
                    "Brier": entry.brier_score,
                    "项目 ID": entry.case_id,
                    "预测 ID": entry.forecast_id,
                }
                for entry in entries
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("暂无该状态下的预测记录。")

    st.divider()
    with st.container(border=True):
        st.markdown("**✏️ 更新预测结果**")
        st.caption("当现实中发生事件后，回来给你的预测评分。")
        
        if entries:
            forecast_id = st.selectbox("📝 选择要更新的预测", [entry.forecast_id for entry in entries])
            new_status = st.selectbox(
                "📉 结果状态",
                ["supported", "failed", "no_information", "expired"],
            )
            outcome = st.text_area("🗒️ 现实反馈 / 结果说明", height=100)
            notes = st.text_area("🔖 备注", height=80)
            
            if st.button("💾 保存更新结果", type="primary"):
                try:
                    brier = ledger.update_outcome(forecast_id, new_status, outcome, notes)
                    if brier is None:
                        st.success("结果已保存；该状态不计算 Brier。")
                    else:
                        st.success(f"结果已保存，Brier = {brier:.3f}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存失败：{exc}")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏠 返回推演台首页", width="stretch"):
        nav.switch_to("home")

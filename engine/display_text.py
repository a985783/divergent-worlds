from __future__ import annotations

from typing import Any


LABELS = {
    "xianyu_daily_sales": "闲鱼日销售额",
    "xianyu_profit_per_item": "闲鱼单件利润",
    "xianyu_sku_count": "闲鱼 SKU 数量",
    "xianyu_sku_expansion": "闲鱼 SKU 扩展",
    "xianyu_sku_expansion_rate": "闲鱼 SKU 扩展速度",
    "quant_capital": "量化本金",
    "quant_capital_change": "量化本金变化",
    "quant_position_rule": "量化仓位规则",
    "quant_automation": "量化自动化",
    "quant_automation_progress": "量化自动化进度",
    "ad_roi": "广告 ROI",
    "search_traffic_share": "搜索流量占比",
    "3min_response_rate": "3 分钟响应率",
    "repeat_purchase_rate": "复购率",
    "ppt_production_cost": "PPT 生产成本",
    "skills_order_count": "技能包订单数",
    "skills_package_orders": "技能包订单数",
    "openclaw_service_orders": "OpenClaw 服务订单数",
    "app_progress": "自有 App 进度",
    "case_library_update_frequency": "案例库更新频率",
    "weekly_action_completion": "每周行动完成度",
    "total_assets": "总资产",
    "total_monthly_income": "月总收入",
    "total_savings_12m": "12 个月储蓄",
    "monthly_savings": "月储蓄",
    "execution_bottleneck": "执行瓶颈",
    "execution_discipline": "执行纪律",
    "execution_rate": "执行率",
    "market_volatility": "市场波动",
    "market_trend": "市场趋势",
    "platform_policy_changes": "平台政策变化",
    "platform_risk": "平台风险",
    "service_quality": "服务质量",
    "package_quality": "资料包质量",
    "delivery_speed": "交付速度",
    "response_time": "响应时间",
    "response_rate": "响应率",
    "product_quality": "产品质量",
    "listing_quality": "商品页质量",
    "price_fairness": "价格合理性",
    "value_for_money": "性价比",
    "signal_accuracy": "信号准确率",
    "market_efficiency": "市场效率",
    "new_listings": "新上架商品",
    "offline_income": "线下收入",
    "offline_income_potential": "线下收入潜力",
    "backtest_annual_return": "回测年化收益",
    "max_positions": "最大仓位数",
    "points_system": "积分制",
    "membership_model": "会员制",
    "state": "状态",
    "direction": "方向",
}


VALUE_LABELS = {
    "stable": "稳定",
    "fixed": "固定",
    "unknown": "未知",
    "uncertain": "不确定",
    "negative": "负面",
    "positive": "正面",
    "increasing": "增长中",
    "declining": "下降中",
    "medium": "中",
    "high": "高",
    "low": "低",
}


def display_label(key: str) -> str:
    if key in LABELS:
        return LABELS[key]
    for prefix in ("sensitivity_to_", "sensitivity_"):
        if key.startswith(prefix):
            return "对" + display_label(key.removeprefix(prefix)) + "的敏感度"
    return key.replace("_", " ")


def display_value(value: Any) -> Any:
    if isinstance(value, dict):
        return "；".join(
            f"{display_label(str(key))}：{display_value(child)}"
            for key, child in value.items()
        )
    if isinstance(value, list):
        return "、".join(str(display_value(item)) for item in value)
    if isinstance(value, str):
        return VALUE_LABELS.get(value, value)
    return value

from __future__ import annotations

import re
from typing import Any

from engine.display_text import display_label, display_value
from engine.schemas import (
    BaseWorld,
    BranchWorld,
    CaseConfig,
    DivergenceReport,
    ForecastCard,
    MaterialSummary,
    SimulationStep,
    WorldProfile,
)
from engine.utils import get_case_path, save_text

REQUIRED_REPORT_SECTIONS = [
    "问题",
    "输入材料摘要",
    "当前世界状态",
    "世界树",
    "分支详情",
    "时间线推演",
    "智能体行为摘要",
    "世界分歧比较",
    "最可能路径",
    "未来观察信号",
    "预测卡片",
    "不确定性和限制",
]


def _bullet(items: list[str], prefix: str = "-") -> str:
    if not items:
        return f"{prefix} 暂无"
    return "\n".join(f"{prefix} {item}" for item in items)


def _branch_by_id(branches: list[BranchWorld]) -> dict[str, BranchWorld]:
    return {branch.branch_id: branch for branch in branches}


def validate_report_sections(markdown: str) -> None:
    headings = re.findall(r"^## (\d+)\. (.+)$", markdown, flags=re.MULTILINE)
    expected = [
        (str(index), title)
        for index, title in enumerate(REQUIRED_REPORT_SECTIONS, start=1)
    ]
    if headings != expected:
        raise ValueError(
            "Final report must include exactly the 12 required sections in order: "
            + ", ".join(f"{number}. {title}" for number, title in expected)
        )


def generate_report(
    case_config: CaseConfig,
    material_summary: MaterialSummary,
    base_world: BaseWorld,
    branches: list[BranchWorld],
    profiles: list[WorldProfile],
    simulation_logs: dict[str, list[SimulationStep]],
    divergence: DivergenceReport,
    forecast_cards: list[ForecastCard],
    llm_client: Any | None = None,
) -> str:
    del llm_client
    branch_lookup = _branch_by_id(branches)
    profile_lookup = {profile.branch_id: profile for profile in profiles}
    lines: list[str] = [
        "# 平行世界预测报告",
        "",
        "## 1. 问题",
        f"[事实] 项目：{case_config.case_name}",
        f"[事实] 核心问题：{case_config.question}",
        f"[事实] 场景：{case_config.scenario_type}；窗口：{case_config.horizon}",
        "",
        "## 2. 输入材料摘要",
        _bullet([f"[事实] {fact}" for fact in material_summary.facts]),
        "",
        "## 3. 当前世界状态",
        f"[推理] {base_world.summary}",
        "",
        "**关键变量**",
    ]

    for key, value in base_world.variables.items():
        lines.append(f"- [事实/推理] {display_label(key)}：{display_value(value)}")

    lines.extend(
        [
            "",
            "## 4. 世界树",
            "| 分支 | 初始概率 | 核心假设 |",
            "| --- | ---: | --- |",
        ]
    )
    for branch in branches:
        lines.append(
            f"| {branch.branch_name} | {branch.initial_probability:.2f} | "
            f"[假设] {branch.core_assumption} |"
        )

    lines.extend(["", "## 5. 分支详情"])
    for index, branch in enumerate(branches, start=1):
        profile = profile_lookup.get(branch.branch_id)
        lines.extend(
            [
                f"### 5.{index} {branch.branch_name}",
                f"[假设] {branch.core_assumption}",
                "",
                "**机制路径**",
                _bullet([f"[推理] {item}" for item in branch.mechanism_path]),
                "",
                "**世界画像**",
            ]
        )
        if profile:
            for key, value in profile.response_profile.items():
                lines.append(f"- [推理] {display_label(key)}：{display_value(value)}")
            if profile.explanation:
                lines.append(f"- [推理] {profile.explanation}")
        else:
            lines.append("- 暂无")

    lines.extend(["", "## 6. 时间线推演"])
    for branch_id, steps in simulation_logs.items():
        branch = branch_lookup.get(branch_id)
        lines.append(f"### {branch.branch_name if branch else branch_id}")
        for step in steps:
            lines.append(f"- [推演] {step.time_label}: {step.state_summary}")
            if step.variable_updates:
                for key, value in step.variable_updates.items():
                    lines.append(f"  - {display_label(key)}：{display_value(value)}")

    lines.extend(["", "## 7. 智能体行为摘要"])
    for branch_id, steps in simulation_logs.items():
        branch = branch_lookup.get(branch_id)
        lines.append(f"### {branch.branch_name if branch else branch_id}")
        for step in steps[:2]:
            for action in step.agent_actions[:3]:
                lines.append(f"- [推演] {step.time_label} / {action.agent_id}: {action.action}")

    lines.extend(
        [
            "",
            "## 8. 世界分歧比较",
            "**关键分歧变量**",
            _bullet([f"[推理] {item}" for item in divergence.top_divergence_variables]),
            "",
            "**分支排序**",
        ]
    )
    for ranking in divergence.branch_ranking:
        branch = branch_lookup.get(ranking.branch_id)
        name = branch.branch_name if branch else ranking.branch_id
        lines.append(f"- [推理] {name}: {ranking.probability:.2f}。{ranking.reason}")

    most_likely = divergence.branch_ranking[0] if divergence.branch_ranking else None
    most_likely_branch = branch_lookup.get(most_likely.branch_id) if most_likely else None
    lines.extend(
        [
            "",
            "## 9. 最可能路径",
            (
                f"[推理] 当前最可能路径是：{most_likely_branch.branch_name}。"
                if most_likely_branch
                else "[推理] 暂无足够排序信息。"
            ),
            "",
            "## 10. 未来观察信号",
            _bullet([f"[预测] {item}" for item in divergence.key_observation_signals]),
            "",
            "## 11. 预测卡片",
        ]
    )
    for card in forecast_cards:
        branch = branch_lookup.get(card.branch_id)
        lines.extend(
            [
                f"### {branch.branch_name if branch else card.branch_id}",
                f"- [预测] {card.prediction}",
                f"- 概率：{card.probability:.2f}",
                f"- 验证窗口：{card.validation_window}",
                "- 支持信号：",
                _bullet(card.support_signals),
                "- 证伪信号：",
                _bullet(card.failure_signals),
                "- 该看什么（最小观察）：",
                _bullet(card.watch_actions),
                f"- 止损（此世界何时判死）：{card.kill_condition or '未给出'}",
                "- 无信息信号：",
                _bullet(card.no_information_signals),
            ]
        )

    lines.extend(
        [
            "",
            "## 12. 不确定性和限制",
            _bullet([f"[假设] {item}" for item in base_world.uncertainties]),
            "- [事实] MVP 不自动联网，也不自动抓取现实结果。",
            "- [推理] 分支概率需要随着现实反馈更新。",
        ]
    )
    report = "\n".join(lines).strip() + "\n"
    validate_report_sections(report)
    save_text(report, get_case_path(case_config.case_id, "08_final_report.md"))
    return report


def generate_report_json(
    case_config: CaseConfig,
    material_summary: MaterialSummary,
    base_world: BaseWorld,
    branches: list[BranchWorld],
    profiles: list[WorldProfile],
    simulation_logs: dict[str, list[SimulationStep]],
    divergence: DivergenceReport,
    forecast_cards: list[ForecastCard],
) -> dict[str, Any]:
    """Export structured JSON report containing all case data."""
    import json as _json
    from datetime import datetime, timezone

    report_data: dict[str, Any] = {
        "report_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_config": case_config.model_dump(mode="json"),
        "material_summary": material_summary.model_dump(mode="json"),
        "base_world": base_world.model_dump(mode="json"),
        "branches": [b.model_dump(mode="json") for b in branches],
        "world_profiles": [p.model_dump(mode="json") for p in profiles],
        "simulation_logs": {
            branch_id: [step.model_dump(mode="json") for step in steps]
            for branch_id, steps in simulation_logs.items()
        },
        "divergence": divergence.model_dump(mode="json"),
        "forecast_cards": [c.model_dump(mode="json") for c in forecast_cards],
    }

    json_path = get_case_path(case_config.case_id, "08_final_report.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        _json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_data

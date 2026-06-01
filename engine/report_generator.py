from __future__ import annotations

import re
from typing import Any

from engine.display_text import display_label, display_value
from engine.language import is_english
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


REPORT_SECTIONS_ZH = [
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

REPORT_SECTIONS_EN = [
    "Problem",
    "Input Material Summary",
    "Current World State",
    "World Tree",
    "Branch Details",
    "Timeline Simulation",
    "Agent Behavior Summary",
    "World Divergence Comparison",
    "Most Likely Path",
    "Future Observation Signals",
    "Forecast Cards",
    "Uncertainty and Limits",
]

REQUIRED_REPORT_SECTIONS = REPORT_SECTIONS_ZH


def _sections() -> list[str]:
    return REPORT_SECTIONS_EN if is_english() else REPORT_SECTIONS_ZH


def _heading(index: int) -> str:
    return f"## {index}. {_sections()[index - 1]}"


def _label(zh: str, en: str) -> str:
    return en if is_english() else zh


def _mark(kind: str) -> str:
    zh = {
        "fact": "[事实]",
        "inference": "[推理]",
        "assumption": "[假设]",
        "simulation": "[推演]",
        "forecast": "[预测]",
    }
    en = {
        "fact": "[Fact]",
        "inference": "[Inference]",
        "assumption": "[Assumption]",
        "simulation": "[Simulation]",
        "forecast": "[Forecast]",
    }
    return (en if is_english() else zh)[kind]


def _bullet(items: list[str], prefix: str = "-") -> str:
    if not items:
        return f"{prefix} {_label('暂无', 'None yet')}"
    return "\n".join(f"{prefix} {item}" for item in items)


def _branch_by_id(branches: list[BranchWorld]) -> dict[str, BranchWorld]:
    return {branch.branch_id: branch for branch in branches}


def validate_report_sections(markdown: str) -> None:
    headings = re.findall(r"^## (\d+)\. (.+)$", markdown, flags=re.MULTILINE)
    expected = [(str(index), title) for index, title in enumerate(_sections(), start=1)]
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

    fact = _mark("fact")
    inference = _mark("inference")
    assumption = _mark("assumption")
    simulation = _mark("simulation")
    forecast = _mark("forecast")

    lines: list[str] = [
        _label("# 平行世界预测报告", "# Divergent Worlds Forecast Report"),
        "",
        _heading(1),
        f"{fact} {_label('项目', 'Project')}: {case_config.case_name}",
        f"{fact} {_label('核心问题', 'Core question')}: {case_config.question}",
        (
            f"{fact} {_label('场景', 'Scenario')}: {case_config.scenario_type}; "
            f"{_label('窗口', 'horizon')}: {case_config.horizon}"
        ),
        "",
        _heading(2),
        _bullet([f"{fact} {item}" for item in material_summary.facts]),
        "",
        _heading(3),
        f"{inference} {base_world.summary}",
        "",
        f"**{_label('关键变量', 'Key Variables')}**",
    ]

    for key, value in base_world.variables.items():
        lines.append(f"- {fact}/{inference} {display_label(key)}: {display_value(value)}")

    lines.extend(
        [
            "",
            _heading(4),
            (
                "| 分支 | 初始概率 | 核心假设 |"
                if not is_english()
                else "| Branch | Initial Probability | Core Assumption |"
            ),
            "| --- | ---: | --- |",
        ]
    )
    for branch in branches:
        lines.append(
            f"| {branch.branch_name} | {branch.initial_probability:.2f} | "
            f"{assumption} {branch.core_assumption} |"
        )

    lines.extend(["", _heading(5)])
    for index, branch in enumerate(branches, start=1):
        profile = profile_lookup.get(branch.branch_id)
        lines.extend(
            [
                f"### 5.{index} {branch.branch_name}",
                f"{assumption} {branch.core_assumption}",
                "",
                f"**{_label('机制路径', 'Mechanism Path')}**",
                _bullet([f"{inference} {item}" for item in branch.mechanism_path]),
                "",
                f"**{_label('世界画像', 'World Profile')}**",
            ]
        )
        if profile:
            for key, value in profile.response_profile.items():
                lines.append(f"- {inference} {display_label(key)}: {display_value(value)}")
            if profile.explanation:
                lines.append(f"- {inference} {profile.explanation}")
        else:
            lines.append(f"- {_label('暂无', 'None yet')}")

    lines.extend(["", _heading(6)])
    for branch_id, steps in simulation_logs.items():
        branch = branch_lookup.get(branch_id)
        lines.append(f"### {branch.branch_name if branch else branch_id}")
        for step in steps:
            lines.append(f"- {simulation} {step.time_label}: {step.state_summary}")
            if step.variable_updates:
                for key, value in step.variable_updates.items():
                    lines.append(f"  - {display_label(key)}: {display_value(value)}")

    lines.extend(["", _heading(7)])
    for branch_id, steps in simulation_logs.items():
        branch = branch_lookup.get(branch_id)
        lines.append(f"### {branch.branch_name if branch else branch_id}")
        for step in steps[:2]:
            for action in step.agent_actions[:3]:
                lines.append(f"- {simulation} {step.time_label} / {action.agent_id}: {action.action}")

    lines.extend(
        [
            "",
            _heading(8),
            f"**{_label('关键分歧变量', 'Critical Divergence Variables')}**",
            _bullet([f"{inference} {item}" for item in divergence.top_divergence_variables]),
            "",
            f"**{_label('分支排序', 'Branch Ranking')}**",
        ]
    )
    for ranking in divergence.branch_ranking:
        branch = branch_lookup.get(ranking.branch_id)
        name = branch.branch_name if branch else ranking.branch_id
        lines.append(f"- {inference} {name}: {ranking.probability:.2f}. {ranking.reason}")

    most_likely = divergence.branch_ranking[0] if divergence.branch_ranking else None
    most_likely_branch = branch_lookup.get(most_likely.branch_id) if most_likely else None
    likely_sentence = (
        f"{inference} 当前最可能路径是：{most_likely_branch.branch_name}。"
        if most_likely_branch
        else f"{inference} 暂无足够排序信息。"
    )
    if is_english():
        likely_sentence = (
            f"{inference} The current most likely path is: {most_likely_branch.branch_name}."
            if most_likely_branch
            else f"{inference} There is not enough ranking evidence yet."
        )
    lines.extend(
        [
            "",
            _heading(9),
            likely_sentence,
            "",
            _heading(10),
            _bullet([f"{forecast} {item}" for item in divergence.key_observation_signals]),
            "",
            _heading(11),
        ]
    )
    for card in forecast_cards:
        branch = branch_lookup.get(card.branch_id)
        lines.extend(
            [
                f"### {branch.branch_name if branch else card.branch_id}",
                f"- {forecast} {card.prediction}",
                f"- {_label('概率', 'Probability')}: {card.probability:.2f}",
                f"- {_label('验证窗口', 'Validation window')}: {card.validation_window}",
                f"- {_label('支持信号', 'Support signals')}:",
                _bullet(card.support_signals),
                f"- {_label('证伪信号', 'Failure signals')}:",
                _bullet(card.failure_signals),
                f"- {_label('该看什么（最小观察）', 'Watch actions')}:",
                _bullet(card.watch_actions),
                (
                    f"- {_label('止损（此世界何时判死）', 'Kill condition')}: "
                    f"{card.kill_condition or _label('未给出', 'Not provided')}"
                ),
                f"- {_label('无信息信号', 'No-information signals')}:",
                _bullet(card.no_information_signals),
            ]
        )

    lines.extend(
        [
            "",
            _heading(12),
            _bullet([f"{assumption} {item}" for item in base_world.uncertainties]),
            (
                f"- {fact} MVP 不自动联网，也不自动抓取现实结果。"
                if not is_english()
                else f"- {fact} The MVP does not browse the web or fetch real-world outcomes automatically."
            ),
            (
                f"- {inference} 分支概率需要随着现实反馈更新。"
                if not is_english()
                else f"- {inference} Branch probabilities should be updated as real-world feedback arrives."
            ),
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
        "language": "en" if is_english() else "zh",
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

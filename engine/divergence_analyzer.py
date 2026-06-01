from __future__ import annotations

from typing import Any

from engine.schemas import BranchWorld, CaseConfig, DivergenceReport, SimulationStep
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


def analyze_divergence(
    branches: list[BranchWorld],
    simulation_logs: dict[str, list[SimulationStep]],
    llm_client: Any,
    case_config: CaseConfig | None = None,
) -> DivergenceReport:
    template = load_prompt("divergence_analyzer.md")
    prompt = render_prompt(template, branches=branches, simulation_logs=simulation_logs)
    report = validate_structured_output(
        llm_client.generate(
            DivergenceReport,
            [
                {
                    "role": "system",
                    "content": "只返回合法 DivergenceReport JSON；所有面向用户的字符串字段使用简体中文。",
                },
                {"role": "user", "content": prompt},
            ],
        ),
        DivergenceReport,
        "DivergenceReport LLM output",
    )
    if case_config:
        save_json(report, get_case_path(case_config.case_id, "06_divergence.json"))
    return report

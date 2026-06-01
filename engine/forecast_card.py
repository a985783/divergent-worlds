from __future__ import annotations

from typing import Any

from engine.language import json_output_instruction
from engine.schemas import (
    BranchWorld,
    CaseConfig,
    DivergenceReport,
    ForecastCard,
    ForecastCardCollection,
    SimulationStep,
)
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


def _collection_items(result: Any) -> list[ForecastCard]:
    if isinstance(result, list):
        return validate_structured_output(
            result,
            list[ForecastCard],
            "ForecastCard list LLM output",
        )
    collection = validate_structured_output(
        result,
        ForecastCardCollection,
        "ForecastCardCollection LLM output",
    )
    return list(collection.cards)


def generate_forecast_cards(
    branches: list[BranchWorld],
    simulation_logs: dict[str, list[SimulationStep]],
    divergence: DivergenceReport,
    case_config: CaseConfig,
    llm_client: Any,
) -> list[ForecastCard]:
    template = load_prompt("forecast_card.md")
    prompt = render_prompt(
        template,
        case_config=case_config,
        branches=branches,
        simulation_logs=simulation_logs,
        divergence=divergence,
    )
    result = llm_client.generate(
        ForecastCardCollection,
        [
            {
                "role": "system",
                "content": json_output_instruction("ForecastCardCollection"),
            },
            {"role": "user", "content": prompt},
        ],
    )
    cards = _collection_items(result)
    save_json(cards, get_case_path(case_config.case_id, "07_forecast_cards.json"))
    return cards

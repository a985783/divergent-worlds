from __future__ import annotations

from typing import Any

from engine.schemas import BaseWorld, CaseConfig, MaterialSummary
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


def build_base_world(
    material_summary: MaterialSummary,
    case_config: CaseConfig,
    llm_client: Any,
) -> BaseWorld:
    template = load_prompt("world_builder.md")
    prompt = render_prompt(template, case_config=case_config, material_summary=material_summary)
    base_world = validate_structured_output(
        llm_client.generate(
            BaseWorld,
            [
                {
                    "role": "system",
                    "content": "只返回一个合法 BaseWorld JSON 对象；所有面向用户的字符串字段使用简体中文。",
                },
                {"role": "user", "content": prompt},
            ],
        ),
        BaseWorld,
        "BaseWorld LLM output",
    )
    save_json(base_world, get_case_path(case_config.case_id, "02_base_world.json"))
    return base_world

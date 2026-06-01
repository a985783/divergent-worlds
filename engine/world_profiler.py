from __future__ import annotations

from typing import Any

from engine.language import json_output_instruction
from engine.schemas import BaseWorld, BranchWorld, CaseConfig, WorldProfile
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


def profile_world(branch: BranchWorld, base_world: BaseWorld, llm_client: Any) -> WorldProfile:
    template = load_prompt("world_profiler.md")
    prompt = render_prompt(template, branch=branch, base_world=base_world)
    return validate_structured_output(
        llm_client.generate(
            WorldProfile,
            [
                {
                    "role": "system",
                    "content": json_output_instruction("WorldProfile"),
                },
                {"role": "user", "content": prompt},
            ],
        ),
        WorldProfile,
        "WorldProfile LLM output",
    )


def profile_worlds(
    branches: list[BranchWorld],
    base_world: BaseWorld,
    case_config: CaseConfig,
    llm_client: Any,
) -> list[WorldProfile]:
    profiles = [profile_world(branch, base_world, llm_client) for branch in branches]
    save_json(profiles, get_case_path(case_config.case_id, "03_world_profiles.json"))
    return profiles

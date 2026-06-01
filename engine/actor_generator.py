from __future__ import annotations

from typing import Any

from engine.schemas import Actor, ActorCollection, BaseWorld, BranchWorld, CaseConfig
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


def _collection_items(result: Any) -> list[Actor]:
    if isinstance(result, list):
        return validate_structured_output(result, list[Actor], "Actor list LLM output")
    collection = validate_structured_output(result, ActorCollection, "ActorCollection LLM output")
    return list(collection.actors)


def generate_actors(
    branch: BranchWorld,
    base_world: BaseWorld,
    case_config: CaseConfig,
    llm_client: Any,
) -> list[Actor]:
    template = load_prompt("actor_generator.md")
    prompt = render_prompt(
        template,
        case_config=case_config,
        base_world=base_world,
        branch=branch,
    )
    result = llm_client.generate(
        ActorCollection,
        [
            {
                "role": "system",
                "content": "只返回合法 ActorCollection JSON；所有面向用户的字符串字段使用简体中文。",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return _collection_items(result)


def generate_actors_for_branches(
    branches: list[BranchWorld],
    base_world: BaseWorld,
    case_config: CaseConfig,
    llm_client: Any,
) -> dict[str, list[Actor]]:
    actors_by_branch = {
        branch.branch_id: generate_actors(branch, base_world, case_config, llm_client)
        for branch in branches
    }
    save_json(actors_by_branch, get_case_path(case_config.case_id, "04_agents.json"))
    return actors_by_branch

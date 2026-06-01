from __future__ import annotations

from collections import Counter
from typing import Any

from engine.language import json_output_instruction
from engine.schemas import BaseWorld, BranchWorld, BranchWorldCollection, CaseConfig
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


def _collection_items(result: Any) -> list[BranchWorld]:
    if isinstance(result, list):
        return validate_structured_output(result, list[BranchWorld], "BranchWorld list LLM output")
    collection = validate_structured_output(
        result,
        BranchWorldCollection,
        "BranchWorldCollection LLM output",
    )
    return list(collection.branches)


def generate_branches(
    base_world: BaseWorld,
    case_config: CaseConfig,
    llm_client: Any,
) -> list[BranchWorld]:
    template = load_prompt("fork_generator.md")
    prompt = render_prompt(
        template,
        case_config=case_config,
        base_world=base_world,
        user_branches=case_config.user_specified_branches,
    )
    result = llm_client.generate(
        BranchWorldCollection,
        [
            {
                "role": "system",
                "content": json_output_instruction("BranchWorldCollection"),
            },
            {"role": "user", "content": prompt},
        ],
    )
    branches = _collection_items(result)
    save_json(branches, get_case_path(case_config.case_id, "03_branches.json"))
    return branches


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def validate_branch_diversity(branches: list[BranchWorld]) -> tuple[float, list[str]]:
    """Return (diversity_score 0-1, warnings). Higher score = more diverse."""
    warnings: list[str] = []
    if len(branches) < 2:
        return 1.0, warnings

    # 1. Duplicate name check
    names = [branch.branch_name.strip().lower() for branch in branches]
    for name, count in Counter(names).items():
        if count > 1:
            warnings.append(f"分支名称重复：{name}")

    # 2. Assumption text similarity (Jaccard)
    assumptions = [
        set(branch.core_assumption.lower().replace("/", " ").replace(",", " ").split())
        for branch in branches
    ]
    assumption_similarities: list[float] = []
    for i, left in enumerate(assumptions):
        for j, right in enumerate(assumptions[i + 1 :], start=i + 1):
            sim = _jaccard(left, right)
            assumption_similarities.append(sim)
            if sim > 0.75:
                warnings.append(
                    f"分支核心假设过于相似：{branches[i].branch_name} ↔ {branches[j].branch_name}"
                )

    # 3. Changed variable overlap
    var_sets = [set(branch.changed_variables.keys()) for branch in branches]
    variable_similarities: list[float] = []
    for i, left in enumerate(var_sets):
        for j, right in enumerate(var_sets[i + 1 :], start=i + 1):
            sim = _jaccard(left, right)
            variable_similarities.append(sim)
            if sim > 0.80:
                warnings.append(
                    f"分支变量变化高度重叠：{branches[i].branch_name} ↔ {branches[j].branch_name}"
                )

    # 4. Compute diversity score (1 - avg similarity)
    all_sims = assumption_similarities + variable_similarities
    avg_sim = sum(all_sims) / len(all_sims) if all_sims else 0.0
    diversity_score = round(1.0 - avg_sim, 3)

    if diversity_score < 0.5:
        warnings.append(f"整体分支多样性偏低（{diversity_score:.2f}），建议调整分支假设。")

    return diversity_score, warnings


# Branch type keywords for auto-assignment
_BRANCH_TYPE_KEYWORDS: dict[str, list[str]] = {
    "Reality Continuation": ["延续", "继续", "维持", "现状", "不变", "baseline", "continuation"],
    "Main Shock": ["冲击", "恶化", "崩溃", "暴跌", "危机", "shock", "crash", "decline"],
    "Hidden Variable": ["暗变量", "隐藏", "潜在", "意外", "hidden", "latent", "unexpected"],
    "Counterfactual Removal": ["如果没有", "去掉", "不存在", "取消", "without", "removal", "counterfactual"],
    "Timing Shift": ["提前", "延后", "延迟", "早期", "later", "earlier", "delay", "advance"],
    "Intensity Shift": ["强度", "加强", "减弱", "增加", "decrease", "increase", "intensity"],
    "Alternative Equilibrium": ["替代", "新均衡", "转型", "转变", "alternative", "equilibrium", "new"],
}


def assign_branch_type(branch: BranchWorld) -> str:
    """Infer branch_type from core_assumption text. Returns best match or default."""
    text = (branch.core_assumption + " " + branch.branch_name).lower()
    best_type = "Alternative Equilibrium"
    best_score = 0
    for branch_type, keywords in _BRANCH_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_type = branch_type
    return best_type


def merge_user_edits(branches: list[BranchWorld], user_edits: dict[str, dict[str, Any]]) -> list[BranchWorld]:
    merged: list[BranchWorld] = []
    for branch in branches:
        patch = user_edits.get(branch.branch_id)
        merged.append(branch.model_copy(update=patch) if patch else branch)
    return merged

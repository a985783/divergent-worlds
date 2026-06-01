from __future__ import annotations

from engine.actor_generator import generate_actors_for_branches
from engine.divergence_analyzer import analyze_divergence
from engine.forecast_card import generate_forecast_cards
from engine.fork_generator import generate_branches, merge_user_edits, validate_branch_diversity
from engine.schemas import (
    ActorCollection,
    BaseWorld,
    BranchWorldCollection,
    DivergenceReport,
    ForecastCardCollection,
    WorldProfile,
)
from engine.simulation_runner import SimulationRunner
from engine.world_builder import build_base_world
from engine.world_profiler import profile_worlds
from tests.conftest import (
    RecordingLLM,
    make_actor,
    make_base_world,
    make_branch,
    make_branches,
    make_case_config,
    make_divergence,
    make_forecast_card,
    make_material_summary,
    make_profile,
    make_step,
)


def test_world_builder_generates_base_world_and_saves_output(data_dir) -> None:
    case_config = make_case_config(case_id="case_world_builder")
    base_world = make_base_world()
    llm = RecordingLLM([(BaseWorld, base_world)])

    result = build_base_world(make_material_summary(), case_config, llm)

    assert result == base_world
    assert llm.calls[0]["response_model"] is BaseWorld
    assert (data_dir / "cases" / "case_world_builder" / "02_base_world.json").exists()


def test_fork_generator_accepts_collection_and_validates_diversity(data_dir) -> None:
    case_config = make_case_config(case_id="case_forks")
    branches = make_branches()
    llm = RecordingLLM([(BranchWorldCollection, BranchWorldCollection(branches=branches))])

    generated = generate_branches(make_base_world(), case_config, llm)

    assert generated == branches
    score, warnings = validate_branch_diversity(generated)
    assert isinstance(score, float)
    assert score > 0
    assert (data_dir / "cases" / "case_forks" / "03_branches.json").exists()


def test_validate_branch_diversity_flags_duplicate_names_and_similar_assumptions() -> None:
    branches = [
        make_branch(
            "branch_a",
            "Same Name",
            core_assumption="traffic ranking recovers buyer demand quickly",
        ),
        make_branch(
            "branch_b",
            "Same Name",
            core_assumption="traffic ranking recovers buyer demand quickly",
        ),
    ]

    score, warnings = validate_branch_diversity(branches)

    assert score == 0.0
    assert any("分支名称重复" in w for w in warnings)
    assert any("分支核心假设过于相似" in w for w in warnings)


def test_merge_user_edits_updates_only_targeted_branches() -> None:
    branches = make_branches()

    merged = merge_user_edits(
        branches,
        {"branch_recovery": {"branch_name": "Edited Recovery", "initial_probability": 0.5}},
    )

    assert merged[0].branch_name == "Edited Recovery"
    assert merged[0].initial_probability == 0.5
    assert merged[1] == branches[1]


def test_world_profiler_and_actor_generation_save_outputs(data_dir) -> None:
    case_config = make_case_config(case_id="case_profiles_actors")
    branches = make_branches()[:2]
    profiles = [make_profile(branch.branch_id) for branch in branches]
    actors_by_branch = {branch.branch_id: [make_actor()] for branch in branches}
    llm = RecordingLLM(
        [
            (WorldProfile, profiles[0]),
            (WorldProfile, profiles[1]),
            (ActorCollection, ActorCollection(actors=actors_by_branch[branches[0].branch_id])),
            (ActorCollection, ActorCollection(actors=actors_by_branch[branches[1].branch_id])),
        ]
    )

    generated_profiles = profile_worlds(branches, make_base_world(), case_config, llm)
    generated_actors = generate_actors_for_branches(branches, make_base_world(), case_config, llm)

    assert generated_profiles == profiles
    assert generated_actors == actors_by_branch
    assert (data_dir / "cases" / "case_profiles_actors" / "03_world_profiles.json").exists()
    assert (data_dir / "cases" / "case_profiles_actors" / "04_agents.json").exists()


def test_simulation_runner_uses_horizon_steps_profiles_and_persists_log(data_dir) -> None:
    case_config = make_case_config(case_id="case_simulation", horizon="7d")
    branch = make_branches()[0]
    steps = [make_step(branch.branch_id, label) for label in ["t+1d", "t+3d", "t+7d"]]
    llm = RecordingLLM(steps)
    runner = SimulationRunner(llm, case_config)

    logs = runner.run_all_branches(
        [branch],
        {branch.branch_id: [make_actor()]},
        make_base_world(),
        [make_profile(branch.branch_id)],
    )

    assert [step.time_label for step in logs[branch.branch_id]] == ["t+1d", "t+3d", "t+7d"]
    assert len(llm.calls) == 3
    assert all(call["response_model"].__name__ == "SimulationStep" for call in llm.calls)
    assert (data_dir / "cases" / "case_simulation" / "05_simulation_log.json").exists()


def test_divergence_and_forecast_card_modules_save_outputs(data_dir) -> None:
    case_config = make_case_config(case_id="case_divergence_forecast")
    branches = make_branches()[:2]
    logs = {branch.branch_id: [make_step(branch.branch_id)] for branch in branches}
    divergence = make_divergence(branches)
    cards = [make_forecast_card(branch.branch_id) for branch in branches]
    llm = RecordingLLM(
        [
            (DivergenceReport, divergence),
            (ForecastCardCollection, ForecastCardCollection(cards=cards)),
        ]
    )

    generated_divergence = analyze_divergence(branches, logs, llm, case_config)
    generated_cards = generate_forecast_cards(branches, logs, generated_divergence, case_config, llm)

    assert generated_divergence == divergence
    assert generated_cards == cards
    assert (data_dir / "cases" / "case_divergence_forecast" / "06_divergence.json").exists()
    assert (data_dir / "cases" / "case_divergence_forecast" / "07_forecast_cards.json").exists()

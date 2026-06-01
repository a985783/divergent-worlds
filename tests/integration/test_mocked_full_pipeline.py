from __future__ import annotations

from engine.actor_generator import generate_actors_for_branches
from engine.divergence_analyzer import analyze_divergence
from engine.forecast_card import generate_forecast_cards
from engine.forecast_ledger import ForecastLedger
from engine.fork_generator import generate_branches
from engine.ingest import summarize_materials
from engine.report_generator import generate_report
from engine.schemas import (
    ActorCollection,
    BaseWorld,
    BranchWorldCollection,
    DivergenceReport,
    ForecastCardCollection,
    MaterialSummary,
    WorldProfile,
)
from engine.simulation_runner import SimulationRunner
from engine.world_builder import build_base_world
from engine.world_profiler import profile_worlds
from tests.conftest import (
    RecordingLLM,
    make_actor,
    make_base_world,
    make_branches,
    make_case_config,
    make_divergence,
    make_forecast_card,
    make_material_summary,
    make_profile,
    make_step,
)


def test_mocked_full_pipeline_persists_intermediates_report_and_ledger(data_dir, tmp_path) -> None:
    case_config = make_case_config(case_id="case_full_pipeline", horizon="7d")
    material_summary = make_material_summary()
    base_world = make_base_world()
    branches = make_branches()
    profiles = [make_profile(branch.branch_id) for branch in branches]
    actors = [make_actor()]
    steps = [
        make_step(branch.branch_id, time_label)
        for branch in branches
        for time_label in ["t+1d", "t+3d", "t+7d"]
    ]
    divergence = make_divergence(branches)
    cards = [make_forecast_card(branch.branch_id) for branch in branches]
    llm = RecordingLLM(
        [
            (MaterialSummary, material_summary),
            (BaseWorld, base_world),
            (BranchWorldCollection, BranchWorldCollection(branches=branches)),
            *[(WorldProfile, profile) for profile in profiles],
            *[(ActorCollection, ActorCollection(actors=actors)) for _ in branches],
            *steps,
            (DivergenceReport, divergence),
            (ForecastCardCollection, ForecastCardCollection(cards=cards)),
        ]
    )

    summary = summarize_materials(["Fixture source material."], llm, case_config)
    built_world = build_base_world(summary, case_config, llm)
    generated_branches = generate_branches(built_world, case_config, llm)
    generated_profiles = profile_worlds(generated_branches, built_world, case_config, llm)
    actors_by_branch = generate_actors_for_branches(generated_branches, built_world, case_config, llm)
    simulation_logs = SimulationRunner(llm, case_config).run_all_branches(
        generated_branches,
        actors_by_branch,
        built_world,
        generated_profiles,
    )
    generated_divergence = analyze_divergence(generated_branches, simulation_logs, llm, case_config)
    generated_cards = generate_forecast_cards(
        generated_branches,
        simulation_logs,
        generated_divergence,
        case_config,
        llm,
    )
    ledger = ForecastLedger(tmp_path / "forecast_ledger.sqlite3")
    ledger.save_cards(generated_cards, case_config.case_id)
    report = generate_report(
        case_config,
        summary,
        built_world,
        generated_branches,
        generated_profiles,
        simulation_logs,
        generated_divergence,
        generated_cards,
    )

    assert llm.responses == []
    assert len(llm.calls) == 1 + 1 + 1 + 3 + 3 + 9 + 1 + 1
    assert len(simulation_logs) == 3
    assert all(len(steps_for_branch) == 3 for steps_for_branch in simulation_logs.values())
    assert {entry.forecast_id for entry in ledger.get_case_forecasts(case_config.case_id)} == {
        card.forecast_id for card in cards
    }
    assert "## 9. 最可能路径" in report
    assert "Traffic Recovery" in report

    case_dir = data_dir / "cases" / case_config.case_id
    expected_files = [
        "01_material_summary.json",
        "02_base_world.json",
        "03_branches.json",
        "03_world_profiles.json",
        "04_agents.json",
        "05_simulation_log.json",
        "06_divergence.json",
        "07_forecast_cards.json",
        "08_final_report.md",
    ]
    assert all((case_dir / filename).exists() for filename in expected_files)

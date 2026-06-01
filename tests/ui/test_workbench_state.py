from __future__ import annotations

import pytest

from pages.workbench_state import (
    WorkbenchStage,
    build_workbench_vm,
    merged_branch_variables,
    next_primary_action,
)
from tests.conftest import (
    make_actor,
    make_base_world,
    make_branch,
    make_branches,
    make_case_config,
    make_divergence,
    make_material_summary,
    make_step,
)


def _state(**overrides):
    state = {
        "case_config": None,
        "demo_case_loaded": False,
        "material_summary": None,
        "base_world": None,
        "branches": [],
        "actors_by_branch": {},
        "simulation_logs": {},
        "divergence": None,
        "forecast_cards": [],
        "report": "",
    }
    state.update(overrides)
    return state


@pytest.mark.parametrize(
    ("state", "stage", "action"),
    [
        (_state(), WorkbenchStage.NO_CASE, "Create or load a case"),
        (
            _state(case_config=make_case_config(), demo_case_loaded=True),
            WorkbenchStage.DEMO_LOADED,
            "Parse materials",
        ),
        (
            _state(case_config=make_case_config(), material_summary=make_material_summary()),
            WorkbenchStage.MATERIALS_PARSED,
            "Build base world",
        ),
        (
            _state(
                case_config=make_case_config(),
                material_summary=make_material_summary(),
                base_world=make_base_world(),
            ),
            WorkbenchStage.BASE_WORLD_READY,
            "Generate branch worlds",
        ),
        (
            _state(
                case_config=make_case_config(),
                material_summary=make_material_summary(),
                base_world=make_base_world(),
                branches=make_branches(),
            ),
            WorkbenchStage.BRANCHES_READY,
            "Run branch simulation",
        ),
        (
            _state(
                case_config=make_case_config(),
                material_summary=make_material_summary(),
                base_world=make_base_world(),
                branches=make_branches(),
                simulation_logs={"branch_recovery": [make_step("branch_recovery")]},
            ),
            WorkbenchStage.PARTIAL_SIMULATION,
            "Resume branch simulation",
        ),
        (
            _state(
                case_config=make_case_config(),
                material_summary=make_material_summary(),
                base_world=make_base_world(),
                branches=make_branches(),
                simulation_logs={
                    "branch_recovery": [make_step("branch_recovery")],
                    "branch_stagnation": [make_step("branch_stagnation")],
                    "branch_decline": [make_step("branch_decline")],
                },
            ),
            WorkbenchStage.PARTIAL_SIMULATION,
            "Compare branch outcomes",
        ),
        (
            _state(
                case_config=make_case_config(),
                material_summary=make_material_summary(),
                base_world=make_base_world(),
                branches=make_branches(),
                simulation_logs={"branch_recovery": [make_step("branch_recovery")]},
                divergence=make_divergence(),
            ),
            WorkbenchStage.COMPARISON_READY,
            "Generate report",
        ),
        (
            _state(
                case_config=make_case_config(),
                material_summary=make_material_summary(),
                base_world=make_base_world(),
                branches=make_branches(),
                simulation_logs={"branch_recovery": [make_step("branch_recovery")]},
                divergence=make_divergence(),
                report="final report",
            ),
            WorkbenchStage.REPORT_READY,
            "Review report",
        ),
    ],
)
def test_workbench_stage_derivation_and_next_action(state, stage, action) -> None:
    vm = build_workbench_vm(state)

    assert vm.stage is stage
    assert next_primary_action(vm) == action


def test_branch_agent_and_timeline_views_are_derived_from_session_state() -> None:
    base_world = make_base_world()
    branches = make_branches()
    step = make_step("branch_recovery", "t+7d")
    actor = make_actor("seller_1")
    state = _state(
        case_config=make_case_config(),
        material_summary=make_material_summary(),
        base_world=base_world,
        branches=branches,
        actors_by_branch={"branch_recovery": [actor]},
        simulation_logs={"branch_recovery": [step]},
    )

    vm = build_workbench_vm(state)

    recovery = vm.branches[0]
    assert recovery.branch_id == "branch_recovery"
    assert recovery.simulation_step_count == 1
    assert recovery.latest_state_summary == "branch_recovery evolves at t+7d."
    assert recovery.merged_branch_variables["traffic"] == "slightly up"
    assert recovery.merged_branch_variables["conversion_rate"] == 0.08

    assert vm.timeline[0].branch_id == "branch_recovery"
    assert vm.timeline[0].time_label == "t+7d"
    assert vm.timeline[0].agent_actions == ("refresh listing",)

    assert vm.agents[0].agent_id == "seller_1"
    assert vm.agents[0].latest_belief == "Traffic signal is informative but noisy."
    assert vm.agents[0].latest_action == "refresh listing"


def test_merged_branch_variables_copies_base_world_and_applies_branch_then_steps() -> None:
    base_world = make_base_world()
    base_world.variables["nested"] = {"source": ["base"]}
    branch = make_branch()
    branch.changed_variables = {"traffic": "branch", "buyer_intent": "stable", "branch_only": 1}
    step = make_step("branch_recovery")
    step.variable_updates = {"traffic": "step", "step_only": {"values": [1, 2]}}
    steps = [step]

    merged = merged_branch_variables(base_world, branch, steps)

    assert merged == {
        "traffic": "step",
        "conversion_rate": 0.08,
        "listing_quality": "stable",
        "nested": {"source": ["base"]},
        "buyer_intent": "stable",
        "branch_only": 1,
        "step_only": {"values": [1, 2]},
    }
    assert base_world.variables["traffic"] == "down 28%"

    merged["nested"]["source"].append("mutated return")
    assert base_world.variables["nested"] == {"source": ["base"]}


def test_branch_view_merged_variables_are_read_only() -> None:
    vm = build_workbench_vm(
        _state(
            case_config=make_case_config(),
            material_summary=make_material_summary(),
            base_world=make_base_world(),
            branches=[make_branch()],
        )
    )

    with pytest.raises(TypeError):
        vm.branches[0].merged_branch_variables["traffic"] = "mutated"

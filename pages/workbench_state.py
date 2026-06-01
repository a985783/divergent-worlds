from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


__all__ = [
    "WorkbenchStage",
    "BranchView",
    "AgentView",
    "TimelineEvent",
    "WorkbenchViewModel",
    "build_workbench_vm",
    "merged_branch_variables",
    "next_primary_action",
]


class WorkbenchStage(str, Enum):
    NO_CASE = "no_case"
    DEMO_LOADED = "demo_loaded"
    MATERIALS_PARSED = "materials_parsed"
    BASE_WORLD_READY = "base_world_ready"
    BRANCHES_READY = "branches_ready"
    PARTIAL_SIMULATION = "partial_simulation"
    COMPARISON_READY = "comparison_ready"
    REPORT_READY = "report_ready"


@dataclass(frozen=True)
class TimelineEvent:
    branch_id: str
    branch_name: str
    time_label: str
    state_summary: str
    variable_updates: Mapping[str, Any]
    agent_actions: tuple[str, ...]
    new_signals: tuple[str, ...]
    divergence_notes: tuple[str, ...]


@dataclass(frozen=True)
class AgentView:
    agent_id: str
    name: str
    role: str
    branch_id: str
    branch_name: str
    goals: tuple[str, ...]
    latest_belief: str | None = None
    latest_action: str | None = None


@dataclass(frozen=True)
class BranchView:
    branch_id: str
    branch_name: str
    branch_type: str
    core_assumption: str
    initial_probability: float
    changed_variables: Mapping[str, Any]
    merged_branch_variables: Mapping[str, Any]
    support_signals: tuple[str, ...]
    failure_signals: tuple[str, ...]
    sibling_branches: tuple[str, ...]
    simulation_step_count: int
    latest_state_summary: str | None = None


@dataclass(frozen=True)
class WorkbenchViewModel:
    stage: WorkbenchStage
    case_config: Any | None
    material_summary: Any | None
    base_world: Any | None
    branches: tuple[BranchView, ...]
    agents: tuple[AgentView, ...]
    timeline: tuple[TimelineEvent, ...]
    divergence: Any | None
    forecast_cards: tuple[Any, ...]
    report: str


def build_workbench_vm(session_state: Any) -> WorkbenchViewModel:
    case_config = _state_get(session_state, "case_config")
    material_summary = _state_get(session_state, "material_summary")
    base_world = _state_get(session_state, "base_world")
    raw_branches = tuple(_state_get(session_state, "branches") or ())
    simulation_logs = _state_get(session_state, "simulation_logs") or {}
    divergence = _state_get(session_state, "divergence")
    forecast_cards = tuple(_state_get(session_state, "forecast_cards") or ())
    report = _state_get(session_state, "report") or ""

    branch_name_by_id = {
        str(_field(branch, "branch_id", "")): str(_field(branch, "branch_name", ""))
        for branch in raw_branches
    }
    branch_views = tuple(
        _build_branch_view(branch, base_world, _steps_for_branch(simulation_logs, branch))
        for branch in raw_branches
    )
    timeline = _build_timeline(raw_branches, branch_name_by_id, simulation_logs)
    agents = _build_agents(
        _state_get(session_state, "actors_by_branch") or {},
        branch_name_by_id,
        simulation_logs,
    )

    return WorkbenchViewModel(
        stage=_derive_stage(
            session_state=session_state,
            case_config=case_config,
            material_summary=material_summary,
            base_world=base_world,
            branches=raw_branches,
            simulation_logs=simulation_logs,
            divergence=divergence,
            forecast_cards=forecast_cards,
            report=report,
        ),
        case_config=case_config,
        material_summary=material_summary,
        base_world=base_world,
        branches=branch_views,
        agents=agents,
        timeline=timeline,
        divergence=divergence,
        forecast_cards=forecast_cards,
        report=report,
    )


def merged_branch_variables(base_world: Any, branch: Any, steps: list[Any] | tuple[Any, ...]) -> dict:
    variables = deepcopy(_field(base_world, "variables", {}) or {})
    variables.update(deepcopy(_field(branch, "changed_variables", {}) or {}))
    for step in steps or ():
        variables.update(deepcopy(_field(step, "variable_updates", {}) or {}))
    return variables


def next_primary_action(vm: WorkbenchViewModel) -> str:
    actions = {
        WorkbenchStage.NO_CASE: "Create or load a case",
        WorkbenchStage.DEMO_LOADED: "Parse materials",
        WorkbenchStage.MATERIALS_PARSED: "Build base world",
        WorkbenchStage.BASE_WORLD_READY: "Generate branch worlds",
        WorkbenchStage.BRANCHES_READY: "Run branch simulation",
        WorkbenchStage.COMPARISON_READY: "Generate report",
        WorkbenchStage.REPORT_READY: "Review report",
    }
    if vm.stage is WorkbenchStage.PARTIAL_SIMULATION:
        return "Compare branch outcomes" if _all_branches_have_steps(vm) else "Resume branch simulation"
    return actions[vm.stage]


def _derive_stage(
    *,
    session_state: Any,
    case_config: Any,
    material_summary: Any,
    base_world: Any,
    branches: tuple[Any, ...],
    simulation_logs: Any,
    divergence: Any,
    forecast_cards: tuple[Any, ...],
    report: str,
) -> WorkbenchStage:
    if report:
        return WorkbenchStage.REPORT_READY
    if divergence or forecast_cards:
        return WorkbenchStage.COMPARISON_READY
    if _has_simulation_steps(simulation_logs):
        return WorkbenchStage.PARTIAL_SIMULATION
    if branches:
        return WorkbenchStage.BRANCHES_READY
    if base_world:
        return WorkbenchStage.BASE_WORLD_READY
    if material_summary:
        return WorkbenchStage.MATERIALS_PARSED
    if case_config and bool(_state_get(session_state, "demo_case_loaded")):
        return WorkbenchStage.DEMO_LOADED
    if case_config:
        return WorkbenchStage.DEMO_LOADED
    return WorkbenchStage.NO_CASE


def _build_branch_view(branch: Any, base_world: Any | None, steps: tuple[Any, ...]) -> BranchView:
    branch_id = str(_field(branch, "branch_id", ""))
    merged = merged_branch_variables(base_world, branch, steps) if base_world else deepcopy(
        _field(branch, "changed_variables", {}) or {}
    )
    latest = steps[-1] if steps else None

    return BranchView(
        branch_id=branch_id,
        branch_name=str(_field(branch, "branch_name", branch_id)),
        branch_type=str(_field(branch, "branch_type", "")),
        core_assumption=str(_field(branch, "core_assumption", "")),
        initial_probability=float(_field(branch, "initial_probability", 0.0) or 0.0),
        changed_variables=_freeze_mapping(_field(branch, "changed_variables", {}) or {}),
        merged_branch_variables=_freeze_mapping(merged),
        support_signals=_as_str_tuple(_field(branch, "support_signals", ())),
        failure_signals=_as_str_tuple(_field(branch, "failure_signals", ())),
        sibling_branches=_as_str_tuple(_field(branch, "sibling_branches", ())),
        simulation_step_count=len(steps),
        latest_state_summary=str(_field(latest, "state_summary", "")) if latest else None,
    )


def _build_timeline(
    branches: tuple[Any, ...],
    branch_name_by_id: dict[str, str],
    simulation_logs: Any,
) -> tuple[TimelineEvent, ...]:
    events: list[TimelineEvent] = []
    known_ids = [str(_field(branch, "branch_id", "")) for branch in branches]
    ordered_ids = known_ids + [
        str(branch_id) for branch_id in _log_branch_ids(simulation_logs) if str(branch_id) not in known_ids
    ]

    for branch_id in ordered_ids:
        branch_name = branch_name_by_id.get(branch_id, branch_id)
        for step in _log_get(simulation_logs, branch_id):
            actions = tuple(
                str(_field(action, "action", ""))
                for action in (_field(step, "agent_actions", ()) or ())
            )
            events.append(
                TimelineEvent(
                    branch_id=branch_id,
                    branch_name=branch_name,
                    time_label=str(_field(step, "time_label", "")),
                    state_summary=str(_field(step, "state_summary", "")),
                    variable_updates=_freeze_mapping(_field(step, "variable_updates", {}) or {}),
                    agent_actions=actions,
                    new_signals=_as_str_tuple(_field(step, "new_signals", ())),
                    divergence_notes=_as_str_tuple(_field(step, "divergence_notes", ())),
                )
            )
    return tuple(events)


def _build_agents(
    actors_by_branch: Any,
    branch_name_by_id: dict[str, str],
    simulation_logs: Any,
) -> tuple[AgentView, ...]:
    views: list[AgentView] = []
    for branch_id in _actor_branch_ids(actors_by_branch):
        branch_key = str(branch_id)
        for actor in _actors_get(actors_by_branch, branch_id):
            latest_belief, latest_action = _latest_agent_state(
                actor,
                _log_get(simulation_logs, branch_key),
            )
            actor_id = str(_field(actor, "agent_id", _field(actor, "name", "")))
            views.append(
                AgentView(
                    agent_id=actor_id,
                    name=str(_field(actor, "name", actor_id)),
                    role=str(_field(actor, "role", "")),
                    branch_id=branch_key,
                    branch_name=branch_name_by_id.get(branch_key, branch_key),
                    goals=_as_str_tuple(_field(actor, "goals", ())),
                    latest_belief=latest_belief,
                    latest_action=latest_action,
                )
            )
    return tuple(views)


def _latest_agent_state(actor: Any, steps: tuple[Any, ...]) -> tuple[str | None, str | None]:
    actor_id = str(_field(actor, "agent_id", ""))
    actor_name = str(_field(actor, "name", ""))
    for step in reversed(steps):
        for action in reversed(tuple(_field(step, "agent_actions", ()) or ())):
            action_agent_id = str(_field(action, "agent_id", ""))
            if action_agent_id in {actor_id, actor_name}:
                return (
                    str(_field(action, "belief_update", "")) or None,
                    str(_field(action, "action", "")) or None,
                )
    return None, None


def _all_branches_have_steps(vm: WorkbenchViewModel) -> bool:
    return bool(vm.branches) and all(branch.simulation_step_count > 0 for branch in vm.branches)


def _has_simulation_steps(simulation_logs: Any) -> bool:
    return any(bool(steps) for steps in _log_values(simulation_logs))


def _steps_for_branch(simulation_logs: Any, branch: Any) -> tuple[Any, ...]:
    branch_id = str(_field(branch, "branch_id", ""))
    return _log_get(simulation_logs, branch_id)


def _state_get(session_state: Any, key: str, default: Any = None) -> Any:
    if hasattr(session_state, "get"):
        return session_state.get(key, default)
    return getattr(session_state, key, default)


def _field(value: Any, key: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({str(key): _freeze_value(val) for key, val in deepcopy(dict(value)).items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _as_str_tuple(values: Any) -> tuple[str, ...]:
    return tuple(str(value) for value in (values or ()))


def _log_branch_ids(simulation_logs: Any) -> tuple[Any, ...]:
    return tuple(simulation_logs.keys()) if hasattr(simulation_logs, "keys") else ()


def _log_values(simulation_logs: Any) -> tuple[Any, ...]:
    return tuple(simulation_logs.values()) if hasattr(simulation_logs, "values") else ()


def _log_get(simulation_logs: Any, branch_id: str) -> tuple[Any, ...]:
    if not hasattr(simulation_logs, "get"):
        return ()
    return tuple(simulation_logs.get(branch_id, ()) or ())


def _actor_branch_ids(actors_by_branch: Any) -> tuple[Any, ...]:
    return tuple(actors_by_branch.keys()) if hasattr(actors_by_branch, "keys") else ()


def _actors_get(actors_by_branch: Any, branch_id: Any) -> tuple[Any, ...]:
    if not hasattr(actors_by_branch, "get"):
        return ()
    return tuple(actors_by_branch.get(branch_id, ()) or ())

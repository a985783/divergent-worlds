from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


ScenarioType = Literal["ecommerce", "policy", "open_source", "public_opinion", "creative", "custom"]
Horizon = Literal["7d", "30d", "3m", "1y"]
ForecastStatus = Literal["pending", "supported", "failed", "no_information", "expired"]
ConfidenceLevel = Literal["low", "medium", "high"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}{stamp}_{uuid4().hex[:8]}"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CaseConfig(StrictModel):
    case_id: str = Field(default_factory=lambda: _id("case_"), description="Unique case id.")
    case_name: str = Field(min_length=1, description="Human-readable case name.")
    question: str = Field(min_length=1, description="Core prediction question.")
    scenario_type: ScenarioType = Field(default="custom", description="Scenario category.")
    horizon: Horizon = Field(default="30d", description="Simulation horizon.")
    branch_count: int = Field(default=5, ge=3, le=7, description="Number of branch worlds.")
    agent_count: int = Field(default=6, ge=5, le=10, description="Agents generated per branch.")
    auto_generate_branches: bool = Field(default=True, description="Whether to generate branches.")
    user_specified_branches: list[str] = Field(
        default_factory=list,
        description="Optional user-provided branch concepts.",
    )
    created_at: datetime = Field(default_factory=_utcnow, description="Creation timestamp.")


class MaterialSummary(StrictModel):
    facts: list[str] = Field(default_factory=list, description="Facts extracted from input material.")
    timeline: list[str] = Field(default_factory=list, description="Time-ordered events or changes.")
    actors: list[str] = Field(default_factory=list, description="Relevant human or system actors.")
    variables: list[str] = Field(default_factory=list, description="Variables related to the question.")
    uncertainties: list[str] = Field(default_factory=list, description="Open uncertainties.")
    user_goals: list[str] = Field(default_factory=list, description="What the user wants to learn.")
    data_notes: list[str] = Field(default_factory=list, description="Notes about uploaded data quality.")


class BaseWorld(StrictModel):
    world_id: str = Field(default="base_world", description="Base world id.")
    name: str = Field(min_length=1, description="Base world name.")
    summary: str = Field(min_length=1, description="Compact current-world summary.")
    time_anchor: str = Field(min_length=1, description="Reference date or period.")
    actors: list[str] = Field(default_factory=list, max_length=10, description="Actors in the world.")
    variables: dict[str, Any] = Field(default_factory=dict, description="Current variables and states.")
    constraints: list[str] = Field(default_factory=list, description="Known limits or constraints.")
    known_facts: list[str] = Field(default_factory=list, description="Facts that should not be altered.")
    uncertainties: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Uncertainties that can drive branches.",
    )
    baseline_path: list[str] = Field(default_factory=list, description="Expected path without shocks.")

    @field_validator("variables")
    @classmethod
    def _limit_variables(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 15:
            raise ValueError("BaseWorld.variables cannot contain more than 15 variables")
        return value


class BranchWorld(StrictModel):
    branch_id: str = Field(default_factory=lambda: _id("branch_"), description="Branch world id.")
    branch_name: str = Field(min_length=1, description="Branch display name.")
    branch_type: str = Field(default="Alternative Equilibrium", description="Branch archetype.")
    core_assumption: str = Field(min_length=1, description="Core assumption that makes this branch true.")
    changed_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables changed from the base world.",
    )
    mechanism_path: list[str] = Field(default_factory=list, description="Causal mechanism path.")
    initial_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Initial probability assigned to this branch.",
    )
    support_signals: list[str] = Field(
        min_length=3,
        description="Signals that would support this branch.",
    )
    failure_signals: list[str] = Field(
        min_length=2,
        description="Signals that would weaken or fail this branch.",
    )
    uncertainty_notes: str = Field(default="", description="Notes about residual uncertainty.")
    confidence_reason: str = Field(default="", description="Reason for the probability estimate.")
    sibling_branches: list[str] = Field(
        default_factory=list,
        description="Branch IDs or names that are grouped/merged with this branch.",
    )


class WorldProfile(StrictModel):
    branch_id: str = Field(description="Branch id this profile belongs to.")
    response_profile: dict[str, str] = Field(
        description="Sensitivity parameters for this branch world.",
    )
    explanation: str = Field(default="", description="Why these response parameters matter.")

    @field_validator("response_profile")
    @classmethod
    def _at_least_three(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) < 3:
            raise ValueError("WorldProfile.response_profile must contain at least 3 parameters")
        return value


class Actor(StrictModel):
    agent_id: str = Field(default_factory=lambda: _id("agent_"), description="Actor id.")
    name: str = Field(min_length=1, description="Actor name.")
    role: str = Field(min_length=1, description="Actor role in the world.")
    goals: list[str] = Field(default_factory=list, description="Actor goals.")
    beliefs: dict[str, Any] = Field(default_factory=dict, description="Actor beliefs.")
    decision_rules: list[str] = Field(default_factory=list, description="Decision rules.")
    sensitive_variables: list[str] = Field(default_factory=list, description="Variables actor reacts to.")
    action_space: list[str] = Field(default_factory=list, description="Possible actions.")
    constraints: list[str] = Field(default_factory=list, description="Actor constraints.")


class ActorAction(StrictModel):
    agent_id: str = Field(description="Actor id.")
    belief_update: str = Field(description="Belief update in this step.")
    action: str = Field(description="Chosen action.")
    variable_pressure: dict[str, str | float | int] = Field(
        default_factory=dict,
        description="Directional pressure on variables.",
    )
    reason: str = Field(description="Reason for the action.")


class SimulationStep(StrictModel):
    step_id: str = Field(default_factory=lambda: _id("step_"), description="Simulation step id.")
    branch_id: str = Field(description="Branch id.")
    time_label: str = Field(description="Time point label, such as t+7d.")
    state_summary: str = Field(min_length=1, description="World state after this step.")
    agent_actions: list[ActorAction] = Field(default_factory=list, description="Actor actions.")
    variable_updates: dict[str, Any] = Field(
        default_factory=dict,
        description="Updated variable values or directions.",
    )
    new_signals: list[str] = Field(default_factory=list, description="New observation signals.")
    divergence_notes: list[str] = Field(default_factory=list, description="Cross-world differences.")


class BranchRanking(StrictModel):
    branch_id: str = Field(description="Branch id.")
    probability: float = Field(ge=0.0, le=1.0, description="Ranked probability.")
    reason: str = Field(default="", description="Reason for ranking.")


class DivergenceReport(StrictModel):
    top_divergence_variables: list[str] = Field(
        default_factory=list,
        description="Variables that best separate worlds.",
    )
    branch_ranking: list[BranchRanking] = Field(
        default_factory=list,
        description="Branch probability ranking.",
    )
    key_observation_signals: list[str] = Field(
        default_factory=list,
        description="Signals the user should observe next.",
    )
    comparison_notes: list[str] = Field(default_factory=list, description="Additional comparison notes.")


class ForecastCard(StrictModel):
    forecast_id: str = Field(default_factory=lambda: _id("forecast_"), description="Forecast id.")
    branch_id: str = Field(description="Branch id.")
    prediction: str = Field(min_length=1, description="Verifiable prediction.")
    probability: float = Field(ge=0.0, le=1.0, description="Prediction probability.")
    validation_window: str = Field(min_length=1, description="Window for checking the forecast.")
    support_signals: list[str] = Field(
        min_length=3,
        description="Signals that would support the prediction.",
    )
    failure_signals: list[str] = Field(
        min_length=2,
        description="Signals that would fail the prediction.",
    )
    no_information_signals: list[str] = Field(
        default_factory=list,
        description="Signals that should not be over-interpreted.",
    )
    watch_actions: list[str] = Field(
        default_factory=list,
        description="Cheapest concrete things to watch/check to resolve this forecast.",
    )
    kill_condition: str = Field(
        default="",
        description="What, if observed, means this branch is dead and should be abandoned.",
    )
    confidence_level: ConfidenceLevel = Field(default="medium", description="Confidence bucket.")
    evidence_basis: list[str] = Field(default_factory=list, description="Evidence and assumptions used.")
    status: ForecastStatus = Field(default="pending", description="Forecast tracking status.")
    outcome: str | None = Field(default=None, description="Observed outcome note.")
    brier_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Brier score.")


class ForecastLedgerEntry(StrictModel):
    forecast_id: str = Field(description="Forecast id.")
    case_id: str = Field(description="Case id.")
    scenario_type: str = Field(default="custom", description="Scenario category.")
    branch_id: str = Field(description="Branch id.")
    prediction: str = Field(description="Prediction text.")
    probability: float = Field(ge=0.0, le=1.0, description="Prediction probability.")
    validation_window: str = Field(description="Validation window.")
    status: ForecastStatus = Field(default="pending", description="Tracking status.")
    outcome: str | None = Field(default=None, description="Observed result.")
    brier_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Brier score.")
    notes: str = Field(default="", description="Ledger notes.")
    created_at: datetime = Field(default_factory=_utcnow, description="Creation timestamp.")
    updated_at: datetime = Field(default_factory=_utcnow, description="Last update timestamp.")


class WorldComparisonRow(StrictModel):
    branch_id: str = Field(description="Branch id.")
    branch_name: str = Field(description="Branch name.")
    probability: float = Field(ge=0.0, le=1.0, description="Branch probability.")
    key_variables: list[str] = Field(default_factory=list, description="Key variables.")
    future_path: str = Field(default="", description="Summarized future path.")
    support_signals: list[str] = Field(default_factory=list, description="Support signals.")
    failure_signals: list[str] = Field(default_factory=list, description="Failure signals.")


class FinalReport(StrictModel):
    case_id: str = Field(description="Case id.")
    title: str = Field(description="Report title.")
    markdown: str = Field(description="Markdown report content.")
    sections: dict[str, str] = Field(default_factory=dict, description="Named report sections.")
    created_at: datetime = Field(default_factory=_utcnow, description="Report creation timestamp.")


class BranchWorldCollection(StrictModel):
    branches: list[BranchWorld] = Field(description="Generated branch worlds.")


class WorldProfileCollection(StrictModel):
    profiles: list[WorldProfile] = Field(description="World profiles.")


class ActorCollection(StrictModel):
    actors: list[Actor] = Field(description="Generated actors.")


class SimulationLog(StrictModel):
    steps_by_branch: dict[str, list[SimulationStep]] = Field(description="Simulation steps per branch.")


class ForecastCardCollection(StrictModel):
    cards: list[ForecastCard] = Field(description="Forecast cards.")

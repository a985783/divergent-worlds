from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.schemas import (  # noqa: E402
    Actor,
    ActorAction,
    BaseWorld,
    BranchRanking,
    BranchWorld,
    CaseConfig,
    DivergenceReport,
    ForecastCard,
    MaterialSummary,
    SimulationStep,
    WorldProfile,
)


class RecordingLLM:
    """Deterministic LLM double that records structured generation calls."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        # UI readiness contract: pages.ui_helpers.llm_is_ready gates LLM actions on
        # these attributes, so the double must look like a configured live client.
        self.live_enabled = True
        self.api_key = "sk-test"
        self.model = "mock-model"
        self._estimated_usd = 0.0

    def get_usage(self) -> dict[str, int]:
        return {
            "calls": len(self.calls),
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def generate(
        self,
        response_model: Any,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        self.calls.append(
            {
                "response_model": response_model,
                "messages": messages,
                "kwargs": kwargs,
            }
        )
        if not self.responses:
            raise AssertionError(f"No mocked LLM response queued for {response_model}")

        response = self.responses.pop(0)
        if isinstance(response, tuple) and len(response) == 2:
            expected_model, value = response
            assert response_model is expected_model
            return value
        if callable(response):
            return response(response_model, messages)
        return response


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(root))
    return root


def make_case_config(
    case_id: str = "case_test",
    horizon: str = "7d",
    branch_count: int = 3,
    agent_count: int = 5,
) -> CaseConfig:
    return CaseConfig(
        case_id=case_id,
        case_name="Xianyu revenue recovery",
        question="Will Xianyu revenue recover after a platform traffic shock?",
        scenario_type="ecommerce",
        horizon=horizon,
        branch_count=branch_count,
        agent_count=agent_count,
        user_specified_branches=["traffic recovers", "traffic stagnates"],
    )


def make_material_summary() -> MaterialSummary:
    return MaterialSummary(
        facts=["Daily revenue fell after a search ranking change.", "Paid boosts were paused."],
        timeline=["Day 1: ranking changed", "Day 7: revenue stabilized at a lower level"],
        actors=["seller", "buyers", "platform algorithm"],
        variables=["traffic", "conversion_rate", "listing_quality"],
        uncertainties=["whether ranking recovers", "whether buyers substitute away"],
        user_goals=["estimate 30 day revenue path"],
        data_notes=["synthetic local fixture"],
    )


def make_base_world() -> BaseWorld:
    return BaseWorld(
        name="Current Xianyu shop state",
        summary="Traffic is depressed while conversion quality remains observable.",
        time_anchor="2026-05-31",
        actors=["seller", "buyers", "platform algorithm"],
        variables={
            "traffic": "down 28%",
            "conversion_rate": 0.08,
            "listing_quality": "stable",
        },
        constraints=["No live internet access in tests.", "Seller budget is capped."],
        known_facts=["Revenue fell after ranking change."],
        uncertainties=["ranking recovery timing", "buyer substitution"],
        baseline_path=["Traffic remains soft for one week.", "Seller refreshes listings."],
    )


def make_branch(
    branch_id: str = "branch_recovery",
    branch_name: str = "Traffic Recovery",
    probability: float = 0.45,
    core_assumption: str | None = None,
) -> BranchWorld:
    return BranchWorld(
        branch_id=branch_id,
        branch_name=branch_name,
        branch_type="Alternative Equilibrium",
        core_assumption=core_assumption
        or f"{branch_name} becomes true through a distinct demand and ranking mechanism.",
        changed_variables={"traffic": "improving", "buyer_intent": "stable"},
        mechanism_path=["ranking exposure changes", "buyer clicks respond", "revenue path shifts"],
        initial_probability=probability,
        support_signals=["impressions rise", "clicks rise", "order inquiries rise"],
        failure_signals=["impressions stay flat", "conversion drops"],
        uncertainty_notes="Mocked branch for deterministic tests.",
        confidence_reason="Probability is fixture-controlled.",
    )


def make_branches() -> list[BranchWorld]:
    return [
        make_branch(
            "branch_recovery",
            "Traffic Recovery",
            0.45,
            "Search exposure recovers and buyer intent stays stable.",
        ),
        make_branch(
            "branch_stagnation",
            "Low Traffic Plateau",
            0.35,
            "Exposure remains capped while loyal buyers continue to convert.",
        ),
        make_branch(
            "branch_decline",
            "Demand Decay",
            0.20,
            "Competing listings absorb buyers and conversion weakens further.",
        ),
    ]


def make_profile(branch_id: str = "branch_recovery") -> WorldProfile:
    return WorldProfile(
        branch_id=branch_id,
        response_profile={
            "traffic_elasticity": "high",
            "price_sensitivity": "medium",
            "platform_dependency": "high",
        },
        explanation="Traffic changes dominate near-term revenue outcomes.",
    )


def make_actor(agent_id: str = "seller_1") -> Actor:
    return Actor(
        agent_id=agent_id,
        name="Seller",
        role="Shop operator",
        goals=["restore revenue", "avoid excess ad spend"],
        beliefs={"ranking_recovery": "uncertain"},
        decision_rules=["refresh listings when impressions fall"],
        sensitive_variables=["traffic", "conversion_rate"],
        action_space=["refresh listing", "adjust price", "buy boost"],
        constraints=["limited budget"],
    )


def make_step(
    branch_id: str = "branch_recovery",
    time_label: str = "t+1d",
    state_summary: str | None = None,
) -> SimulationStep:
    return SimulationStep(
        branch_id=branch_id,
        time_label=time_label,
        state_summary=state_summary or f"{branch_id} evolves at {time_label}.",
        agent_actions=[
            ActorAction(
                agent_id="seller_1",
                belief_update="Traffic signal is informative but noisy.",
                action="refresh listing",
                variable_pressure={"traffic": "up", "conversion_rate": 0.01},
                reason="Refreshing can improve exposure without live API calls.",
            )
        ],
        variable_updates={"traffic": "slightly up", "revenue": "watch"},
        new_signals=["impressions moved"],
        divergence_notes=["traffic path separates branches"],
    )


def make_divergence(branches: list[BranchWorld] | None = None) -> DivergenceReport:
    selected = branches or make_branches()
    return DivergenceReport(
        top_divergence_variables=["traffic", "conversion_rate", "buyer_intent"],
        branch_ranking=[
            BranchRanking(
                branch_id=branch.branch_id,
                probability=branch.initial_probability,
                reason=f"{branch.branch_name} has fixture evidence.",
            )
            for branch in selected
        ],
        key_observation_signals=["impressions", "inquiries", "orders"],
        comparison_notes=["Mocked divergence report."],
    )


def make_forecast_card(branch_id: str = "branch_recovery") -> ForecastCard:
    return ForecastCard(
        forecast_id=f"forecast_{branch_id}",
        branch_id=branch_id,
        prediction="Revenue will recover at least 10% from the post-shock trough.",
        probability=0.62,
        validation_window="next 30 days",
        support_signals=["revenue rises", "inquiries rise", "impressions rise"],
        failure_signals=["revenue flat", "impressions flat"],
        no_information_signals=["one viral inquiry"],
        confidence_level="medium",
        evidence_basis=["mocked branch simulation", "local fixture facts"],
    )

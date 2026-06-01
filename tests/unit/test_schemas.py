from __future__ import annotations

import pytest
from pydantic import ValidationError

from engine.schemas import BaseWorld, BranchWorld, CaseConfig, ForecastCard, WorldProfile
from tests.conftest import make_base_world, make_branch, make_forecast_card


def test_strict_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CaseConfig(
            case_name="Case",
            question="Question?",
            unknown_field=True,
        )


def test_case_config_enforces_branch_and_agent_bounds() -> None:
    with pytest.raises(ValidationError):
        CaseConfig(case_name="Case", question="Question?", branch_count=2)

    with pytest.raises(ValidationError):
        CaseConfig(case_name="Case", question="Question?", agent_count=11)

    config = CaseConfig(case_name="Case", question="Question?", branch_count=3, agent_count=5)
    assert config.branch_count == 3
    assert config.agent_count == 5


def test_base_world_limits_variable_count() -> None:
    too_many_variables = {f"var_{index}": index for index in range(16)}
    with pytest.raises(ValidationError, match="cannot contain more than 15 variables"):
        BaseWorld(
            name="World",
            summary="A world with too many variables.",
            time_anchor="today",
            variables=too_many_variables,
        )

    assert make_base_world().variables["traffic"] == "down 28%"


def test_branch_world_signal_and_probability_validation() -> None:
    valid = make_branch(probability=0.7)
    assert valid.initial_probability == 0.7

    with pytest.raises(ValidationError):
        BranchWorld(
            branch_name="Weak branch",
            core_assumption="Missing enough support signals.",
            initial_probability=1.2,
            support_signals=["one", "two"],
            failure_signals=["one"],
        )


def test_forecast_card_signal_and_brier_bounds() -> None:
    valid = make_forecast_card()
    assert valid.status == "pending"

    with pytest.raises(ValidationError):
        ForecastCard(
            branch_id="branch",
            prediction="Prediction",
            probability=-0.1,
            validation_window="30d",
            support_signals=["one", "two"],
            failure_signals=["one"],
            brier_score=1.2,
        )


def test_world_profile_requires_at_least_three_parameters() -> None:
    with pytest.raises(ValidationError, match="at least 3 parameters"):
        WorldProfile(
            branch_id="branch",
            response_profile={"traffic": "high", "price": "medium"},
        )

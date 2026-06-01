from __future__ import annotations

from contextlib import closing
import sqlite3

import pytest

from engine.forecast_ledger import ForecastLedger
from tests.conftest import make_forecast_card


def test_forecast_ledger_save_list_update_brier_and_summary(tmp_path) -> None:
    db_path = tmp_path / "ledger.sqlite3"
    ledger = ForecastLedger(db_path)
    cards = [
        make_forecast_card("branch_recovery"),
        make_forecast_card("branch_stagnation").model_copy(
            update={"forecast_id": "forecast_branch_stagnation", "probability": 0.25}
        ),
    ]

    ledger.save_cards(cards, "case_ledger")
    entries = ledger.get_case_forecasts("case_ledger")
    all_entries = ledger.list_forecasts()

    assert {entry.forecast_id for entry in entries} == {
        "forecast_branch_recovery",
        "forecast_branch_stagnation",
    }
    assert len(all_entries) == 2

    brier = ledger.update_outcome(
        "forecast_branch_recovery",
        "supported",
        outcome="Revenue recovered.",
        notes="Observed in fixture.",
    )

    assert brier == pytest.approx((0.62 - 1.0) ** 2)
    supported = ledger.list_forecasts("supported")
    assert [entry.forecast_id for entry in supported] == ["forecast_branch_recovery"]
    assert supported[0].notes == "Observed in fixture."
    assert supported[0].brier_score == pytest.approx(brier)

    summary = ledger.get_summary(scenario_type="ecommerce")
    assert summary == {
        "total_forecasts": 2,
        "scored_forecasts": 1,
        "average_brier": pytest.approx(brier),
    }


def test_forecast_ledger_non_binary_status_has_no_brier_score(tmp_path) -> None:
    ledger = ForecastLedger(tmp_path / "ledger.sqlite3")
    card = make_forecast_card("branch_recovery")
    ledger.save_cards([card], "case_ledger")

    brier = ledger.update_outcome(
        card.forecast_id,
        "no_information",
        outcome="Evidence was ambiguous.",
    )

    assert brier is None
    assert ledger.get_summary()["scored_forecasts"] == 0


def test_forecast_ledger_raises_for_unknown_forecast(tmp_path) -> None:
    ledger = ForecastLedger(tmp_path / "ledger.sqlite3")

    with pytest.raises(KeyError, match="Forecast not found"):
        ledger.calculate_brier("missing")


def test_forecast_ledger_persists_signal_lists_as_json(tmp_path) -> None:
    db_path = tmp_path / "ledger.sqlite3"
    ledger = ForecastLedger(db_path)
    card = make_forecast_card("branch_recovery")

    ledger.save_cards([card], "case_ledger")

    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            "SELECT support_signals, failure_signals, no_information_signals, evidence_basis "
            "FROM forecasts WHERE forecast_id = ?",
            (card.forecast_id,),
        ).fetchone()

    assert '"revenue rises"' in row[0]
    assert '"revenue flat"' in row[1]
    assert '"one viral inquiry"' in row[2]
    assert '"mocked branch simulation"' in row[3]

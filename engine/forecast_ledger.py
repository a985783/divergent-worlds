from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.schemas import ForecastCard, ForecastLedgerEntry, ForecastStatus
from engine.utils import data_root


class ForecastLedger:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = (
            Path(db_path)
            if db_path is not None
            else data_root() / "forecast_ledger.sqlite3"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    scenario_type TEXT NOT NULL DEFAULT 'custom',
                    branch_id TEXT NOT NULL,
                    prediction TEXT NOT NULL,
                    probability REAL NOT NULL,
                    validation_window TEXT NOT NULL,
                    support_signals TEXT NOT NULL,
                    failure_signals TEXT NOT NULL,
                    no_information_signals TEXT NOT NULL,
                    evidence_basis TEXT NOT NULL,
                    status TEXT NOT NULL,
                    outcome TEXT,
                    brier_score REAL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(forecasts)").fetchall()
            }
            if "scenario_type" not in columns:
                conn.execute(
                    "ALTER TABLE forecasts "
                    "ADD COLUMN scenario_type TEXT NOT NULL DEFAULT 'custom'"
                )

    def save_cards(
        self,
        cards: list[ForecastCard],
        case_id: str,
        scenario_type: str = "custom",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        resolved_scenario_type = scenario_type or "custom"
        with self._connection() as conn:
            for card in cards:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO forecasts (
                        forecast_id, case_id, scenario_type, branch_id, prediction,
                        probability, validation_window, support_signals, failure_signals,
                        no_information_signals, evidence_basis, status, outcome,
                        brier_score, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                        (SELECT notes FROM forecasts WHERE forecast_id = ?), ''
                    ), COALESCE(
                        (SELECT created_at FROM forecasts WHERE forecast_id = ?), ?
                    ), ?)
                    """,
                    (
                        card.forecast_id,
                        case_id,
                        resolved_scenario_type,
                        card.branch_id,
                        card.prediction,
                        card.probability,
                        card.validation_window,
                        json.dumps(card.support_signals, ensure_ascii=False),
                        json.dumps(card.failure_signals, ensure_ascii=False),
                        json.dumps(card.no_information_signals, ensure_ascii=False),
                        json.dumps(card.evidence_basis, ensure_ascii=False),
                        card.status,
                        card.outcome,
                        card.brier_score,
                        card.forecast_id,
                        card.forecast_id,
                        now,
                        now,
                    ),
                )

    def update_outcome(
        self,
        forecast_id: str,
        status: ForecastStatus,
        outcome: str,
        notes: str = "",
    ) -> float | None:
        brier = self.calculate_brier(forecast_id, status)
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE forecasts
                SET status = ?, outcome = ?, notes = ?, brier_score = ?, updated_at = ?
                WHERE forecast_id = ?
                """,
                (status, outcome, notes, brier, now, forecast_id),
            )
        return brier

    def calculate_brier(
        self,
        forecast_id: str,
        status: ForecastStatus | None = None,
    ) -> float | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT probability, status FROM forecasts WHERE forecast_id = ?",
                (forecast_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Forecast not found: {forecast_id}")
        actual_status = status or row["status"]
        if actual_status == "supported":
            observed = 1.0
        elif actual_status == "failed":
            observed = 0.0
        else:
            return None
        return (float(row["probability"]) - observed) ** 2

    def get_case_forecasts(self, case_id: str) -> list[ForecastLedgerEntry]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM forecasts WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def list_forecasts(self, status: ForecastStatus | None = None) -> list[ForecastLedgerEntry]:
        with self._connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM forecasts WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM forecasts ORDER BY created_at DESC").fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_summary(self, scenario_type: str | None = None) -> dict[str, float | int | None]:
        with self._connection() as conn:
            where_clause = ""
            params: tuple[str, ...] = ()
            if scenario_type:
                matching = conn.execute(
                    "SELECT COUNT(*) AS count FROM forecasts WHERE scenario_type = ?",
                    (scenario_type,),
                ).fetchone()["count"]
                non_legacy = conn.execute(
                    "SELECT COUNT(*) AS count FROM forecasts WHERE scenario_type != 'custom'"
                ).fetchone()["count"]
                if matching > 0 or non_legacy > 0:
                    where_clause = " WHERE scenario_type = ?"
                    params = (scenario_type,)
            rows = conn.execute(
                "SELECT brier_score FROM forecasts"
                f"{where_clause}{' AND' if where_clause else ' WHERE'} brier_score IS NOT NULL",
                params,
            ).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) AS count FROM forecasts{where_clause}",
                params,
            ).fetchone()["count"]
        scores = [float(row["brier_score"]) for row in rows]
        return {
            "total_forecasts": int(total),
            "scored_forecasts": len(scores),
            "average_brier": sum(scores) / len(scores) if scores else None,
        }

    def get_scenario_breakdown(self) -> list[dict[str, Any]]:
        """Return per-scenario-type stats: count, scored, avg_brier."""
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT scenario_type,
                       COUNT(*) AS total,
                       SUM(CASE WHEN brier_score IS NOT NULL THEN 1 ELSE 0 END) AS scored,
                       AVG(CASE WHEN brier_score IS NOT NULL THEN brier_score END) AS avg_brier
                FROM forecasts
                GROUP BY scenario_type
                ORDER BY total DESC
                """
            ).fetchall()
        return [
            {
                "scenario_type": row["scenario_type"],
                "total": int(row["total"]),
                "scored": int(row["scored"]),
                "avg_brier": round(float(row["avg_brier"]), 4) if row["avg_brier"] is not None else None,
            }
            for row in rows
        ]

    def get_status_distribution(self) -> dict[str, int]:
        """Return count of forecasts per status."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM forecasts GROUP BY status"
            ).fetchall()
        return {row["status"]: int(row["count"]) for row in rows}

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> ForecastLedgerEntry:
        return ForecastLedgerEntry(
            forecast_id=row["forecast_id"],
            case_id=row["case_id"],
            scenario_type=row["scenario_type"],
            branch_id=row["branch_id"],
            prediction=row["prediction"],
            probability=row["probability"],
            validation_window=row["validation_window"],
            status=row["status"],
            outcome=row["outcome"],
            brier_score=row["brier_score"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

from __future__ import annotations

import json

from engine.ingest import (
    detect_forks_from_series,
    parse_csv_file,
    parse_material,
    summarize_materials,
)
from engine.schemas import MaterialSummary
from tests.conftest import RecordingLLM, make_case_config, make_material_summary


def test_parse_material_returns_raw_text_when_path_does_not_exist() -> None:
    assert parse_material("raw pasted context") == "raw pasted context"


def test_parse_material_supports_json_and_csv_files(tmp_path) -> None:
    json_path = tmp_path / "input.json"
    json_path.write_text(json.dumps({"fact": "local only"}), encoding="utf-8")

    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("day,revenue,note\n1,100,a\n2,150,b\n3,not-number,c\n", encoding="utf-8")

    assert '"fact": "local only"' in parse_material(json_path)
    csv_summary = parse_material(csv_path)
    assert "CSV rows: 3" in csv_summary
    assert "Columns: day, revenue, note" in csv_summary
    assert "- revenue: count=2, min=100.00, max=150.00, avg=125.00" in csv_summary


def test_parse_csv_file_handles_empty_numeric_columns(tmp_path) -> None:
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text("label,note\na,x\nb,y\n", encoding="utf-8")

    summary = parse_csv_file(csv_path)

    assert "Numeric column summary:" in summary
    assert "- none detected" in summary


def test_detect_forks_from_series_flags_large_baseline_deviation() -> None:
    rows = [{"revenue": value} for value in [100, 102, 98, 101, 99, 100, 100, 140, 142]]

    forks = detect_forks_from_series(rows, "revenue")

    assert forks
    assert forks[0]["metric"] == "revenue"
    assert forks[0]["possible_interpretations"] == ["structural_shift", "temporary_noise"]


def test_summarize_materials_calls_llm_and_persists_case_summary(data_dir) -> None:
    case_config = make_case_config(case_id="case_ingest")
    expected_summary = make_material_summary()
    llm = RecordingLLM([(MaterialSummary, expected_summary)])

    summary = summarize_materials(["local fixture text"], llm, case_config)

    assert summary == expected_summary
    assert llm.calls[0]["response_model"] is MaterialSummary
    assert (data_dir / "cases" / "case_ingest" / "01_material_summary.json").exists()

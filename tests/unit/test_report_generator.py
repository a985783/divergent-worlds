from __future__ import annotations

from engine.report_generator import generate_report
from tests.conftest import (
    make_base_world,
    make_branches,
    make_case_config,
    make_divergence,
    make_forecast_card,
    make_material_summary,
    make_profile,
    make_step,
)


def test_generate_report_contains_required_sections_labels_and_saved_markdown(data_dir) -> None:
    case_config = make_case_config(case_id="case_report")
    branches = make_branches()[:2]
    profiles = [make_profile(branch.branch_id) for branch in branches]
    logs = {branch.branch_id: [make_step(branch.branch_id, "t+1d")] for branch in branches}
    divergence = make_divergence(branches)
    cards = [make_forecast_card(branch.branch_id) for branch in branches]

    report = generate_report(
        case_config=case_config,
        material_summary=make_material_summary(),
        base_world=make_base_world(),
        branches=branches,
        profiles=profiles,
        simulation_logs=logs,
        divergence=divergence,
        forecast_cards=cards,
    )

    assert "# 平行世界预测报告" in report
    assert "## 1. 问题" in report
    assert "## 8. 世界分歧比较" in report
    assert "## 11. 预测卡片" in report
    assert "[事实]" in report
    assert "[推理]" in report
    assert "[假设]" in report
    assert "[推演]" in report
    assert "[预测]" in report
    assert "Traffic Recovery" in report
    assert "Low Traffic Plateau" in report
    assert report.endswith("\n")

    saved = data_dir / "cases" / "case_report" / "08_final_report.md"
    assert saved.read_text(encoding="utf-8") == report


def test_generate_report_json(data_dir) -> None:
    from engine.report_generator import generate_report_json
    case_config = make_case_config(case_id="case_report_json")
    branches = make_branches()[:2]
    profiles = [make_profile(branch.branch_id) for branch in branches]
    logs = {branch.branch_id: [make_step(branch.branch_id, "t+1d")] for branch in branches}
    divergence = make_divergence(branches)
    cards = [make_forecast_card(branch.branch_id) for branch in branches]

    report_data = generate_report_json(
        case_config=case_config,
        material_summary=make_material_summary(),
        base_world=make_base_world(),
        branches=branches,
        profiles=profiles,
        simulation_logs=logs,
        divergence=divergence,
        forecast_cards=cards,
    )

    assert report_data["report_version"] == "1.0"
    assert "case_config" in report_data
    assert "base_world" in report_data
    assert len(report_data["branches"]) == 2

    saved = data_dir / "cases" / "case_report_json" / "08_final_report.json"
    assert saved.exists()

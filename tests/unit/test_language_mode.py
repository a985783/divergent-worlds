from __future__ import annotations

from engine.report_generator import generate_report, generate_report_json
from engine.utils import load_prompt, render_prompt
from engine.world_builder import build_base_world
from tests.conftest import (
    RecordingLLM,
    make_base_world,
    make_branches,
    make_case_config,
    make_divergence,
    make_forecast_card,
    make_material_summary,
    make_profile,
    make_step,
)


def test_english_mode_loads_english_prompt_and_system_instruction(monkeypatch, data_dir) -> None:
    monkeypatch.setenv("LLM_OUTPUT_LANGUAGE", "en")
    template = load_prompt("world_builder.md")
    assert "You build the current reality baseline" in template
    rendered = render_prompt(template, case_config=make_case_config(), material_summary=make_material_summary())
    assert rendered.startswith("# Output language\nUse English")

    llm = RecordingLLM([make_base_world()])
    build_base_world(make_material_summary(), make_case_config(case_id="case_lang_prompt"), llm)

    messages = llm.calls[0]["messages"]
    assert "English" in messages[0]["content"]
    assert messages[1]["content"].startswith("# Output language\nUse English")


def test_english_mode_generates_english_report_sections(monkeypatch, data_dir) -> None:
    monkeypatch.setenv("LLM_OUTPUT_LANGUAGE", "en")
    case_config = make_case_config(case_id="case_lang_report")
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

    assert "# Divergent Worlds Forecast Report" in report
    assert "## 1. Problem" in report
    assert "## 8. World Divergence Comparison" in report
    assert "## 11. Forecast Cards" in report
    assert "[Fact]" in report
    assert "[Inference]" in report

    report_json = generate_report_json(
        case_config=case_config,
        material_summary=make_material_summary(),
        base_world=make_base_world(),
        branches=branches,
        profiles=profiles,
        simulation_logs=logs,
        divergence=divergence,
        forecast_cards=cards,
    )
    assert report_json["language"] == "en"

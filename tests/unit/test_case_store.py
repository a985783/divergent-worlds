from __future__ import annotations

from engine.case_store import list_case_records, load_case_state, resume_page_index
from engine.utils import save_json
from tests.conftest import (
    make_actor,
    make_base_world,
    make_branches,
    make_case_config,
    make_forecast_card,
    make_material_summary,
    make_profile,
)


def test_case_records_resume_to_simulation_when_agents_exist(tmp_path) -> None:
    root = tmp_path / "data"
    case = make_case_config(case_id="case_resume")
    case_dir = root / "cases" / case.case_id
    save_json(case, case_dir / "00_case_config.json")
    save_json(make_material_summary(), case_dir / "01_material_summary.json")
    save_json(make_base_world(), case_dir / "02_base_world.json")
    branches = make_branches()
    save_json(branches, case_dir / "03_branches.json")
    save_json(
        [make_profile(branch.branch_id) for branch in branches],
        case_dir / "03_world_profiles.json",
    )
    save_json(
        {branch.branch_id: [make_actor()] for branch in branches},
        case_dir / "04_agents.json",
    )

    records = list_case_records(root)
    state = load_case_state(case.case_id, root)

    assert records[0].stage == "智能体已生成"
    assert records[0].resume_page_index == 6
    assert resume_page_index(case_dir) == 6
    assert state["case_config"].case_id == "case_resume"
    assert state["branches"]
    assert state["actors_by_branch"]
    assert state["current_page_index"] == 6


def test_resume_roundtrip_restores_report_and_forecast_cards(tmp_path) -> None:
    """报告写在 08_final_report.md（case_store 读取的同名路径），恢复后不丢失。"""
    root = tmp_path / "data"
    case = make_case_config(case_id="case_report_roundtrip")
    case_dir = root / "cases" / case.case_id
    save_json(case, case_dir / "00_case_config.json")

    save_json([make_forecast_card()], case_dir / "07_forecast_cards.json")
    report_md = "# 推演报告\n\n核心结论：流量回升概率偏高。"
    (case_dir / "08_final_report.md").write_text(report_md, encoding="utf-8")

    state = load_case_state(case.case_id, root)

    assert state["report"] == report_md
    assert state["forecast_cards"]
    assert state["forecast_cards"][0].forecast_id == "forecast_branch_recovery"

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from engine.schemas import (
    Actor,
    BaseWorld,
    BranchWorld,
    CaseConfig,
    DivergenceReport,
    ForecastCard,
    MaterialSummary,
    SimulationStep,
    WorldProfile,
)
from engine.utils import data_root, load_json


CASE_ARTIFACTS: dict[str, tuple[str, Any, Any]] = {
    "case_config": ("00_case_config.json", CaseConfig, None),
    "material_summary": ("01_material_summary.json", MaterialSummary, None),
    "base_world": ("02_base_world.json", BaseWorld, None),
    "branches": ("03_branches.json", list[BranchWorld], []),
    "profiles": ("03_world_profiles.json", list[WorldProfile], []),
    "actors_by_branch": ("04_agents.json", dict[str, list[Actor]], {}),
    "simulation_logs": ("05_simulation_log.json", dict[str, list[SimulationStep]], {}),
    "divergence": ("06_divergence.json", DivergenceReport, None),
    "forecast_cards": ("07_forecast_cards.json", list[ForecastCard], []),
}


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    case_name: str
    question: str
    stage: str
    resume_page_index: int
    updated_at: str
    artifact_count: int
    case_dir: Path


def list_case_records(root: str | Path | None = None) -> list[CaseRecord]:
    cases_dir = data_root(root) / "cases"
    if not cases_dir.exists():
        return []

    records: list[CaseRecord] = []
    for case_dir in cases_dir.iterdir():
        if not case_dir.is_dir():
            continue
        config_path = case_dir / "00_case_config.json"
        if not config_path.exists():
            continue
        try:
            config = load_json(config_path, CaseConfig)
            records.append(
                CaseRecord(
                    case_id=case_dir.name,
                    case_name=config.case_name,
                    question=config.question,
                    stage=describe_case_stage(case_dir),
                    resume_page_index=resume_page_index(case_dir),
                    updated_at=_case_updated_at(case_dir),
                    artifact_count=_artifact_count(case_dir),
                    case_dir=case_dir,
                )
            )
        except Exception:
            records.append(
                CaseRecord(
                    case_id=case_dir.name,
                    case_name=case_dir.name,
                    question="配置文件读取失败",
                    stage="配置损坏",
                    resume_page_index=0,
                    updated_at=_case_updated_at(case_dir),
                    artifact_count=0,
                    case_dir=case_dir,
                )
            )
    return sorted(records, key=lambda record: record.updated_at, reverse=True)


def load_case_state(case_id: str, root: str | Path | None = None) -> dict[str, Any]:
    case_dir = data_root(root) / "cases" / case_id
    state: dict[str, Any] = {}
    for state_key, (filename, model, default) in CASE_ARTIFACTS.items():
        path = case_dir / filename
        if path.exists():
            raw = load_json(path)
            state[state_key] = TypeAdapter(model).validate_python(raw)
        else:
            state[state_key] = default

    report_path = case_dir / "08_final_report.md"
    state["report"] = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    state["demo_case_loaded"] = False
    state["demo_material_paths"] = []
    state["material_preview"] = []
    state["current_page_index"] = resume_page_index(case_dir)
    return state


def describe_case_stage(case_dir: Path) -> str:
    ordered = [
        ("07_forecast_cards.json", "预测卡片"),
        ("06_divergence.json", "世界比较"),
        ("05_simulation_log.json", "推演完成"),
        ("04_agents.json", "智能体已生成"),
        ("03_branches.json", "分支已生成"),
        ("02_base_world.json", "初始世界"),
        ("01_material_summary.json", "材料摘要"),
        ("00_case_config.json", "项目已创建"),
    ]
    for filename, label in ordered:
        if (case_dir / filename).exists():
            return label
    return "空"


def resume_page_index(case_dir: Path) -> int:
    if not (case_dir / "00_case_config.json").exists():
        return 0
    if not (case_dir / "01_material_summary.json").exists():
        return 3
    if not (case_dir / "02_base_world.json").exists():
        return 4
    if not (case_dir / "03_branches.json").exists():
        return 5
    if not (case_dir / "05_simulation_log.json").exists():
        return 6
    if not (case_dir / "06_divergence.json").exists():
        return 7
    if not (case_dir / "07_forecast_cards.json").exists() and not (
        case_dir / "08_final_report.md"
    ).exists():
        return 8
    return 1


def _case_updated_at(case_dir: Path) -> str:
    mtimes = [path.stat().st_mtime for path in case_dir.glob("*") if path.is_file()]
    if not mtimes:
        return ""
    from datetime import datetime

    return datetime.fromtimestamp(max(mtimes)).strftime("%Y-%m-%d %H:%M:%S")


def _artifact_count(case_dir: Path) -> int:
    return sum(
        1
        for filename, _, _ in CASE_ARTIFACTS.values()
        if (case_dir / filename).exists()
    )

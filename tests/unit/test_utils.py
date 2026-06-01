from __future__ import annotations

from datetime import datetime, timezone

from engine.schemas import CaseConfig
from engine.utils import (
    ensure_case_dir,
    format_timestamp,
    generate_id,
    get_case_path,
    load_json,
    render_prompt,
    save_json,
    save_text,
)
from tests.conftest import make_base_world, make_case_config


def test_case_paths_create_expected_directory_tree(tmp_path) -> None:
    case_dir = ensure_case_dir("case_123", tmp_path)

    assert case_dir == tmp_path / "cases" / "case_123"
    assert (case_dir / "uploads").is_dir()
    assert (case_dir / "intermediate").is_dir()
    assert (case_dir / "outputs").is_dir()
    assert get_case_path("case_123", "result.json", tmp_path) == case_dir / "result.json"


def test_save_and_load_json_round_trips_pydantic_models(tmp_path) -> None:
    config = make_case_config(case_id="case_json")
    path = save_json(config, tmp_path / "case.json")

    loaded = load_json(path, CaseConfig)
    raw = load_json(path)

    assert loaded == config
    assert raw["case_id"] == "case_json"
    assert "created_at" in raw


def test_save_text_writes_atomically_visible_file(tmp_path) -> None:
    target = save_text("hello", tmp_path / "nested" / "note.md")

    assert target.read_text(encoding="utf-8") == "hello"
    assert not target.with_suffix(".md.tmp").exists()


def test_render_prompt_serializes_models_and_nested_values() -> None:
    rendered = render_prompt(
        "World={world}\nItems={items}\nName={name}",
        world=make_base_world(),
        items=[{"value": 1}],
        name="demo",
    )

    assert '"summary": "Traffic is depressed while conversion quality remains observable."' in rendered
    assert '"value": 1' in rendered
    assert "Name=demo" in rendered


def test_timestamp_and_generated_id_format() -> None:
    stamp = format_timestamp(datetime(2026, 5, 31, 12, 30, tzinfo=timezone.utc))
    generated = generate_id("case_")

    assert stamp == "2026-05-31T12:30:00Z"
    assert generated.startswith("case_")
    assert len(generated.split("_")) >= 4

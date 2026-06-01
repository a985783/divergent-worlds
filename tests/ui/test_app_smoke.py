from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _markdown_text(app: AppTest) -> str:
    return "\n".join(str(getattr(item, "value", "")) for item in app.markdown)


def test_home_page_renders_visual_cockpit_before_footer_controls() -> None:
    app = AppTest.from_file("app.py")

    app.run(timeout=20)

    assert not app.exception
    body = _markdown_text(app)
    assert "项目中心" in body
    assert "平行世界推演台" in body
    assert "T0 现实基线" not in body
    assert "世界线轨道" not in body


def test_home_page_supports_english_ui_mode(monkeypatch) -> None:
    monkeypatch.setenv("APP_LANGUAGE", "en")
    monkeypatch.setenv("LLM_OUTPUT_LANGUAGE", "en")
    app = AppTest.from_file("app.py")

    app.run(timeout=20)

    assert not app.exception
    body = _markdown_text(app)
    assert "Project Center" in body
    assert "Divergent Worlds" in body
    assert "Control Panel" in body

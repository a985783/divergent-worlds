from __future__ import annotations

from streamlit.testing.v1 import AppTest


WORKBENCH_WITHOUT_LLM_APP = """
import streamlit as st

from app import init_session
from pages import simulation_workbench
from tests.conftest import make_base_world, make_case_config, make_material_summary

init_session()
st.session_state.case_config = make_case_config()
st.session_state.material_summary = make_material_summary()
st.session_state.base_world = make_base_world()
st.session_state.llm_client = None
simulation_workbench.render()
"""


def test_cockpit_run_action_is_blocked_cleanly_when_llm_is_missing() -> None:
    app = AppTest.from_string(WORKBENCH_WITHOUT_LLM_APP)
    app.run(timeout=20)

    assert not app.exception
    run_button = next(button for button in app.button if button.label == "🚀 发散平行未来分支")
    run_button.click()
    app.run(timeout=20)

    assert not app.exception
    errors = "\n".join(str(getattr(item, "value", "")) for item in app.error)
    assert "LLM 配置未就绪" in errors
    assert "模型客户端初始化失败" in errors

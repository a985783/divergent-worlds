from __future__ import annotations

from streamlit.testing.v1 import AppTest


WORKBENCH_EMPTY_APP = """
from app import init_session
from pages import simulation_workbench

init_session()
simulation_workbench.render()
"""


WORKBENCH_READY_APP = """
import streamlit as st

from app import init_session
from pages import simulation_workbench
from tests.conftest import (
    make_actor,
    make_base_world,
    make_branches,
    make_case_config,
    make_material_summary,
    make_step,
)

init_session()
st.session_state.case_config = make_case_config()
st.session_state.material_summary = make_material_summary()
st.session_state.base_world = make_base_world()
st.session_state.branches = make_branches()
st.session_state.actors_by_branch = {"branch_recovery": [make_actor()]}
st.session_state.simulation_logs = {"branch_recovery": [make_step("branch_recovery")]}
simulation_workbench.render()
"""


def _markdown_text(app: AppTest) -> str:
    return "\n".join(str(getattr(item, "value", "")) for item in app.markdown)


def test_workbench_empty_state_is_cockpit_first_not_form_first() -> None:
    app = AppTest.from_string(WORKBENCH_EMPTY_APP)

    app.run(timeout=20)

    assert not app.exception
    body = _markdown_text(app)
    assert "流程推进器" in body
    assert "🚀 初始化项目" in [button.label for button in app.button]

def test_workbench_ready_state_shows_graph_controls_agents_and_events() -> None:
    app = AppTest.from_string(WORKBENCH_READY_APP)

    app.run(timeout=20)

    assert not app.exception
    body = _markdown_text(app)
    assert "流程推进器" in body
    assert "Traffic Recovery" in body
    assert "推演控制台" in body
    # 顶部不再有与幕内重复的“下一步”动作按钮（单一真相源：唯一主操作在幕内）
    assert not any(b.label.startswith("下一步：") for b in app.button)
    assert "回到当前阶段" in [button.label for button in app.button]
    assert "⏩ 一键运行所有分支" in [button.label for button in app.button]
    assert "🎯 对比并生成预测卡" in [button.label for button in app.button]


WORKBENCH_AUTO_PILOT_APP = """
import streamlit as st

from app import init_session
from pages import simulation_workbench
from tests.conftest import (
    make_actor,
    make_base_world,
    make_branches,
    make_case_config,
    make_material_summary,
    make_step,
)

init_session()
st.session_state.case_config = make_case_config()
st.session_state.material_summary = make_material_summary()
st.session_state.base_world = make_base_world()
st.session_state.branches = make_branches()
st.session_state.actors_by_branch = {"branch_recovery": [make_actor()]}
st.session_state.simulation_logs = {"branch_recovery": [make_step("branch_recovery")]}
st.session_state.is_auto_pilot = True
st.session_state._testing_skip_auto_pilot = True

simulation_workbench.render()
"""

def test_workbench_auto_pilot_is_active_but_skipped_in_test() -> None:
    app = AppTest.from_string(WORKBENCH_AUTO_PILOT_APP)

    app.run(timeout=20)

    assert not app.exception
    assert app.session_state["is_auto_pilot"] is True

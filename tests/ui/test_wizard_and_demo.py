"""向导单幕路由、卡片/台账渲染与 resume-roundtrip 覆盖。

沿用 AppTest.from_string + session_state 注入 + RecordingLLM/llm_client=None 的既有模式。
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _markdown_text(app: AppTest) -> str:
    return "\n".join(str(getattr(item, "value", "")) for item in app.markdown)


# ---------------------------------------------------------------------------
# 向导：单主操作 + 进度轨即时刷新（无重复顶部动作按钮）
# ---------------------------------------------------------------------------

WIZARD_BASEWORLD_APP = """
import streamlit as st

from app import init_session
from pages import simulation_workbench
from tests.conftest import RecordingLLM, make_case_config, make_material_summary, make_base_world

init_session()
st.session_state.case_config = make_case_config()
st.session_state.material_summary = make_material_summary()
st.session_state.llm_client = RecordingLLM([(__import__("engine.schemas", fromlist=["BaseWorld"]).BaseWorld, make_base_world())])
simulation_workbench.render()
"""


def test_wizard_single_action_no_duplicate_top_button() -> None:
    app = AppTest.from_string(WIZARD_BASEWORLD_APP)
    app.run(timeout=20)

    assert not app.exception
    # 顶部进度轨存在
    assert "流程推进器" in _markdown_text(app)
    # 顶部没有与幕内重复的“下一步：”动作按钮
    assert not any(b.label.startswith("下一步：") for b in app.button)
    # 幕内有唯一主操作（构造基线世界）
    assert any("基线世界" in b.label for b in app.button)


def test_wizard_baseworld_action_advances_stage() -> None:
    app = AppTest.from_string(WIZARD_BASEWORLD_APP)
    app.run(timeout=20)
    assert not app.exception
    assert not app.session_state["base_world"]

    target = next(b for b in app.button if "基线世界" in b.label)
    target.click().run(timeout=20)

    assert not app.exception
    # run_act_action 成功后会 rerun，base_world 已写入 → 阶段前移
    assert app.session_state["base_world"]


# ---------------------------------------------------------------------------
# 预测卡渲染（八要素预注册）
# ---------------------------------------------------------------------------

CARD_RENDER_APP = """
import streamlit as st

from app import init_session
from pages.components.result import render_comparison_tab
from pages.workbench_state import build_workbench_vm
from pages.state_manager import state
from tests.conftest import (
    make_case_config, make_base_world, make_branches, make_divergence, make_forecast_card, make_step,
)

init_session()
st.session_state.llm_client = None
st.session_state.case_config = make_case_config()
st.session_state.base_world = make_base_world()
st.session_state.branches = make_branches()
st.session_state.simulation_logs = {"branch_recovery": [make_step("branch_recovery")]}
st.session_state.divergence = make_divergence()
_card = make_forecast_card()
_card.watch_actions = ["盯卖家是否继续上新", "盯平台是否恢复曝光"]
_card.kill_condition = "若 30 天内 impressions 持续走平则判定失败"
st.session_state.forecast_cards = [_card]
render_comparison_tab(build_workbench_vm(state))
"""


def test_forecast_card_preregistration_fields_render() -> None:
    app = AppTest.from_string(CARD_RENDER_APP)
    app.run(timeout=20)

    assert not app.exception
    body = _markdown_text(app)
    assert "可证伪预测卡" in body
    assert "该看什么" in body
    assert "止损" in body
    assert "无信息信号" in body


# ---------------------------------------------------------------------------
# 台账 UI
# ---------------------------------------------------------------------------

def test_forecast_ledger_page_renders_without_exception(data_dir) -> None:
    src = """
import streamlit as st
from app import init_session
from pages import forecast_ledger
init_session()
forecast_ledger.render()
"""
    app = AppTest.from_string(src)
    app.run(timeout=20)
    assert not app.exception

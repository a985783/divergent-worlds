import streamlit as st
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from engine.schemas import CaseConfig, BaseWorld, BranchWorld, WorldProfile

class AppState:
    """Type-safe wrapper around Streamlit's session_state."""

    # -------------------------------------------------------------------------
    # Core Engine Data
    # -------------------------------------------------------------------------
    @property
    def case_config(self) -> Optional[CaseConfig]:
        return st.session_state.get("case_config")

    @case_config.setter
    def case_config(self, value: Optional[CaseConfig]):
        st.session_state.case_config = value

    @property
    def base_world(self) -> Optional[BaseWorld]:
        return st.session_state.get("base_world")

    @base_world.setter
    def base_world(self, value: Optional[BaseWorld]):
        st.session_state.base_world = value

    @property
    def branches(self) -> List[BranchWorld]:
        return st.session_state.get("branches", [])

    @branches.setter
    def branches(self, value: List[BranchWorld]):
        st.session_state.branches = value

    @property
    def profiles(self) -> List[WorldProfile]:
        return st.session_state.get("profiles", [])

    @profiles.setter
    def profiles(self, value: List[WorldProfile]):
        st.session_state.profiles = value

    @property
    def actors_by_branch(self) -> Dict[str, Any]:
        return st.session_state.get("actors_by_branch", {})

    @actors_by_branch.setter
    def actors_by_branch(self, value: Dict[str, Any]):
        st.session_state.actors_by_branch = value

    @property
    def simulation_logs(self) -> Dict[str, Any]:
        return st.session_state.get("simulation_logs", {})

    @simulation_logs.setter
    def simulation_logs(self, value: Dict[str, Any]):
        st.session_state.simulation_logs = value

    @property
    def divergence(self) -> Optional[Any]:
        return st.session_state.get("divergence")

    @divergence.setter
    def divergence(self, value: Optional[Any]):
        st.session_state.divergence = value

    @property
    def forecast_cards(self) -> List[Any]:
        return st.session_state.get("forecast_cards", [])

    @forecast_cards.setter
    def forecast_cards(self, value: List[Any]):
        st.session_state.forecast_cards = value

    @property
    def report(self) -> Optional[Any]:
        return st.session_state.get("report")

    @report.setter
    def report(self, value: Optional[Any]):
        st.session_state.report = value

    @property
    def report_json(self) -> Optional[Dict[str, Any]]:
        return st.session_state.get("report_json")

    @report_json.setter
    def report_json(self, value: Optional[Dict[str, Any]]):
        st.session_state.report_json = value

    # -------------------------------------------------------------------------
    # Material Prep State
    # -------------------------------------------------------------------------
    @property
    def material_preview(self) -> Optional[Any]:
        return st.session_state.get("material_preview")

    @material_preview.setter
    def material_preview(self, value: Optional[Any]):
        st.session_state.material_preview = value

    @property
    def material_summary(self) -> Optional[Any]:
        return st.session_state.get("material_summary")

    @material_summary.setter
    def material_summary(self, value: Optional[Any]):
        st.session_state.material_summary = value

    @property
    def csv_data_rows(self) -> Optional[List[Dict[str, Any]]]:
        return st.session_state.get("csv_data_rows")

    @csv_data_rows.setter
    def csv_data_rows(self, value: Optional[List[Dict[str, Any]]]):
        st.session_state.csv_data_rows = value

    def clear_csv_data_rows(self):
        if "csv_data_rows" in st.session_state:
            del st.session_state["csv_data_rows"]

    # -------------------------------------------------------------------------
    # Demo and UI Config
    # -------------------------------------------------------------------------
    @property
    def demo_case_loaded(self) -> Union[bool, Dict[str, Any]]:
        return st.session_state.get("demo_case_loaded", False)

    @demo_case_loaded.setter
    def demo_case_loaded(self, value: Union[bool, Dict[str, Any]]):
        st.session_state.demo_case_loaded = value

    @property
    def demo_material_paths(self) -> List[Union[str, Path]]:
        return st.session_state.get("demo_material_paths", [])

    @demo_material_paths.setter
    def demo_material_paths(self, value: List[Union[str, Path]]):
        st.session_state.demo_material_paths = value

    @property
    def llm_client(self) -> Optional[Any]:
        return st.session_state.get("llm_client")

    @llm_client.setter
    def llm_client(self, value: Optional[Any]):
        st.session_state.llm_client = value

    @property
    def sim_active_branch(self) -> Optional[str]:
        return st.session_state.get("sim_active_branch")

    @sim_active_branch.setter
    def sim_active_branch(self, value: Optional[str]):
        st.session_state.sim_active_branch = value

    @property
    def workbench_setup_expanded(self) -> bool:
        return st.session_state.get("workbench_setup_expanded", True)

    @workbench_setup_expanded.setter
    def workbench_setup_expanded(self, value: bool):
        st.session_state.workbench_setup_expanded = value

    # -------------------------------------------------------------------------
    # Setup forms default state
    # -------------------------------------------------------------------------
    @property
    def case_name_val(self) -> str:
        return st.session_state.get("case_name_val", "")

    @case_name_val.setter
    def case_name_val(self, value: str):
        st.session_state.case_name_val = value

    @property
    def question_val(self) -> str:
        return st.session_state.get("question_val", "")

    @question_val.setter
    def question_val(self, value: str):
        st.session_state.question_val = value

    @property
    def scenario_val(self) -> str:
        return st.session_state.get("scenario_val", "")

    @scenario_val.setter
    def scenario_val(self, value: str):
        st.session_state.scenario_val = value

    @property
    def horizon_val(self) -> str:
        return st.session_state.get("horizon_val", "")

    @horizon_val.setter
    def horizon_val(self, value: str):
        st.session_state.horizon_val = value

    @property
    def auto_generate_val(self) -> bool:
        return st.session_state.get("auto_generate_val", False)

    @auto_generate_val.setter
    def auto_generate_val(self, value: bool):
        st.session_state.auto_generate_val = value

    @property
    def branch_count_val(self) -> int:
        return st.session_state.get("branch_count_val", 3)

    @branch_count_val.setter
    def branch_count_val(self, value: int):
        st.session_state.branch_count_val = value

    @property
    def agent_count_val(self) -> int:
        return st.session_state.get("agent_count_val", 2)

    @agent_count_val.setter
    def agent_count_val(self, value: int):
        st.session_state.agent_count_val = value

    @property
    def branches_val(self) -> List[Any]:
        return st.session_state.get("branches_val", [])

    @branches_val.setter
    def branches_val(self, value: List[Any]):
        st.session_state.branches_val = value

    # -------------------------------------------------------------------------
    # Auto-Pilot State
    # -------------------------------------------------------------------------
    @property
    def is_auto_pilot(self) -> bool:
        return st.session_state.get("is_auto_pilot", False)

    @is_auto_pilot.setter
    def is_auto_pilot(self, value: bool):
        st.session_state.is_auto_pilot = value

    @property
    def simulation_event_queue(self) -> list:
        if "simulation_event_queue" not in st.session_state:
            st.session_state.simulation_event_queue = []
        return st.session_state.simulation_event_queue

    @simulation_event_queue.setter
    def simulation_event_queue(self, value: list):
        st.session_state.simulation_event_queue = value

    # -------------------------------------------------------------------------
    # UI Action Helpers
    # -------------------------------------------------------------------------
    def get_error(self, action_key: str) -> Optional[Dict[str, str]]:
        return st.session_state.get(f"{action_key}_last_error")

    def set_error(self, action_key: str, message: str, hint: str = ""):
        st.session_state[f"{action_key}_last_error"] = {"message": message, "hint": hint}

    def clear_error(self, action_key: str):
        st.session_state.pop(f"{action_key}_last_error", None)

    def is_retry_requested(self, action_key: str) -> bool:
        return bool(st.session_state.get(f"{action_key}_retry_requested", False))

    def set_retry_requested(self, action_key: str, value: bool):
        st.session_state[f"{action_key}_retry_requested"] = value
        
    def get_dynamic(self, key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)
        
    def set_dynamic(self, key: str, value: Any):
        st.session_state[key] = value

state = AppState()

from __future__ import annotations

from unittest.mock import MagicMock
from engine.simulation_runner import SimulationRunner
from engine.schemas import (
    BranchWorld,
    CaseConfig,
    SimulationStep,
    BaseWorld,
    ActorAction
)

def test_resume_branch_runs_only_remaining_steps():
    # 1. 准备 mock LLM 和 CaseConfig (horizon 为 30d, 包含 t+1d, t+7d, t+14d, t+30d)
    mock_client = MagicMock()
    # 模拟生成的下一个 SimulationStep
    mock_step_result = SimulationStep(
        branch_id="branch_test",
        time_label="t+30d",
        state_summary="Final step completed",
        new_signals=[],
        divergence_notes=[],
        variable_updates={},
        agent_actions=[ActorAction(agent_id="Agent1", belief_update="belief", action="action1", reason="reason")]
    )
    mock_client.generate.return_value = mock_step_result
    
    config = CaseConfig(case_name="Test Resume", question="What happens?", horizon="30d")
    runner = SimulationRunner(mock_client, config)
    
    # 2. 模拟已经完成了前三个时间步 (t+1d, t+7d, t+14d)
    existing_steps = [
        SimulationStep(
            branch_id="branch_test",
            time_label="t+1d",
            state_summary="Step 1 summary",
            new_signals=[],
            divergence_notes=[],
            variable_updates={},
            agent_actions=[]
        ),
        SimulationStep(
            branch_id="branch_test",
            time_label="t+7d",
            state_summary="Step 2 summary",
            new_signals=[],
            divergence_notes=[],
            variable_updates={},
            agent_actions=[]
        ),
        SimulationStep(
            branch_id="branch_test",
            time_label="t+14d",
            state_summary="Step 3 summary",
            new_signals=[],
            divergence_notes=[],
            variable_updates={},
            agent_actions=[]
        ),
    ]
    
    branch = BranchWorld(
        branch_name="Test Branch",
        core_assumption="Assumption test",
        initial_probability=0.5,
        support_signals=["sign1", "sign2", "sign3"],
        failure_signals=["fail1", "fail2"]
    )
    
    # 3. 运行恢复
    all_steps = runner.resume_branch(
        branch=branch,
        actors=[],
        base_world=BaseWorld(name="Base", summary="Base summary", time_anchor="T0", variables={}),
        existing_steps=existing_steps,
        profile=None
    )
    
    # 4. 验证 mock LLM 仅被调用了一次 (只有 t+30d 是 remaining)
    assert mock_client.generate.call_count == 1
    assert len(all_steps) == 4
    assert all_steps[3].time_label == "t+30d"
    assert all_steps[0].time_label == "t+1d"

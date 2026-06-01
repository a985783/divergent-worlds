from __future__ import annotations

from typing import Any, Callable

from engine.schemas import Actor, BaseWorld, BranchWorld, CaseConfig, SimulationStep, WorldProfile
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


class SimulationRunner:
    def __init__(self, llm_client: Any, case_config: CaseConfig) -> None:
        self.llm_client = llm_client
        self.case_config = case_config

    @staticmethod
    def get_time_steps(horizon: str) -> list[str]:
        schedules = {
            "7d": ["t+1d", "t+3d", "t+7d"],
            "30d": ["t+1d", "t+7d", "t+14d", "t+30d"],
            "3m": ["t+1w", "t+1m", "t+2m", "t+3m"],
            "1y": ["t+1m", "t+3m", "t+6m", "t+12m"],
        }
        return schedules.get(horizon, schedules["30d"])

    def run_step(
        self,
        branch: BranchWorld,
        actors: list[Actor],
        base_world: BaseWorld,
        previous_steps: list[SimulationStep],
        time_label: str,
        profile: WorldProfile | None = None,
    ) -> SimulationStep:
        template = load_prompt("simulation_step.md")
        prompt = render_prompt(
            template,
            case_config=self.case_config,
            base_world=base_world,
            branch=branch,
            profile=profile.model_dump(mode="json") if profile else {},
            actors=actors,
            previous_steps=previous_steps,
            time_label=time_label,
        )
        return validate_structured_output(
            self.llm_client.generate(
                SimulationStep,
                [
                    {
                        "role": "system",
                        "content": "只推进一个分支的一个时间步；只返回合法 SimulationStep JSON；所有面向用户的字符串字段使用简体中文。",
                    },
                    {"role": "user", "content": prompt},
                ],
            ),
            SimulationStep,
            "SimulationStep LLM output",
        )

    def run_branch(
        self,
        branch: BranchWorld,
        actors: list[Actor],
        base_world: BaseWorld,
        profile: WorldProfile | None = None,
        progress_callback: Callable[[BranchWorld, str, SimulationStep | None], None] | None = None,
    ) -> list[SimulationStep]:
        steps: list[SimulationStep] = []
        for time_label in self.get_time_steps(self.case_config.horizon):
            if progress_callback:
                progress_callback(branch, time_label, None)
            step = self.run_step(branch, actors, base_world, steps, time_label, profile)
            steps.append(step)
            if progress_callback:
                progress_callback(branch, time_label, step)
        return steps

    def resume_branch(
        self,
        branch: BranchWorld,
        actors: list[Actor],
        base_world: BaseWorld,
        existing_steps: list[SimulationStep],
        profile: WorldProfile | None = None,
        progress_callback: Callable[[BranchWorld, str, SimulationStep | None], None] | None = None,
    ) -> list[SimulationStep]:
        """Resume simulation from existing steps, running only remaining time steps."""
        all_steps = list(existing_steps)
        completed_labels = {step.time_label for step in all_steps}
        remaining = [
            label for label in self.get_time_steps(self.case_config.horizon)
            if label not in completed_labels
        ]
        for time_label in remaining:
            if progress_callback:
                progress_callback(branch, time_label, None)
            step = self.run_step(branch, actors, base_world, all_steps, time_label, profile)
            all_steps.append(step)
            if progress_callback:
                progress_callback(branch, time_label, step)
        return all_steps

    def run_all_branches(
        self,
        branches: list[BranchWorld],
        actors_by_branch: dict[str, list[Actor]],
        base_world: BaseWorld,
        profiles: list[WorldProfile] | None = None,
        existing_logs: dict[str, list[SimulationStep]] | None = None,
        progress_callback: Callable[[BranchWorld, str, SimulationStep | None], None] | None = None,
    ) -> dict[str, list[SimulationStep]]:
        import concurrent.futures
        
        profile_by_branch = {profile.branch_id: profile for profile in profiles or []}
        logs = existing_logs.copy() if existing_logs else {}
        
        def run_single_branch(branch: BranchWorld) -> tuple[str, list[SimulationStep]]:
            branch_id = branch.branch_id
            existing = logs.get(branch_id, [])
            
            # Check if already completed
            expected_steps = self.get_time_steps(self.case_config.horizon)
            if len(existing) >= len(expected_steps):
                return branch_id, existing
                
            if existing:
                res = self.resume_branch(
                    branch,
                    actors_by_branch.get(branch_id, []),
                    base_world,
                    existing,
                    profile_by_branch.get(branch_id),
                    progress_callback,
                )
            else:
                res = self.run_branch(
                    branch,
                    actors_by_branch.get(branch_id, []),
                    base_world,
                    profile_by_branch.get(branch_id),
                    progress_callback,
                )
            return branch_id, res

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_single_branch, branch) for branch in branches]
            for future in concurrent.futures.as_completed(futures):
                branch_id, branch_logs = future.result()
                logs[branch_id] = branch_logs

        save_json(logs, get_case_path(self.case_config.case_id, "05_simulation_log.json"))
        return logs

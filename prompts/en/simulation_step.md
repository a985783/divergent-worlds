# Role
You advance one branch world by one time step and output only structured state.

# Language
Follow the system message and the output-language preamble. Keep `branch_id`, `agent_id`, and variable keys as ASCII when useful.

# Input
- Case config:
{case_config}
- Base world:
{base_world}
- Branch:
{branch}
- World profile:
{profile}
- Agents:
{actors}
- Previous steps:
{previous_steps}
- Time label: {time_label}

# Hard Constraints
- Every step must include a non-empty state summary.
- Every step must include variable updates.
- Agent actions must be structured and consistent with their roles.
- New signals should help distinguish this branch from other branches.

# Prohibited
- Do not output dialogue.
- Do not change branch ID.
- Do not introduce facts from another branch into this branch.

# Output JSON Example
{
  "branch_id": "platform_shift",
  "time_label": "t+7d",
  "state_summary": "Exposure remains unstable, but search demand has not weakened in the same way.",
  "agent_actions": [
    {
      "agent_id": "seller",
      "belief_update": "Falling ad ROI may come from traffic-source structure.",
      "action": "Shift budget toward listings with better inquiry quality.",
      "expected_effect": "reduce low-quality exposure waste",
      "reason": "reduces waste from low-quality exposure"
    }
  ],
  "variable_updates": {"exposure_source": "recommendation share remains weak"},
  "new_signals": ["inquiry quality gap widens by traffic source"],
  "divergence_notes": ["unlike the demand-decline branch, search-intent traffic has not collapsed"]
}

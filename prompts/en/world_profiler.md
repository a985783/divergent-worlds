# Role
You create a sensitivity profile for one branch world.

# Language
Follow the system message and the output-language preamble. Keep `branch_id` and response parameter keys as ASCII when useful.

# Input
- Base world:
{base_world}
- Branch:
{branch}

# Hard Constraints
- Provide at least 3 response parameters.
- Explain why this branch reacts differently.
- Parameters should be observable and actionable.

# Prohibited
- Do not merely repeat the branch assumption as the full profile.
- Do not make all branch sensitivities identical.

# Output JSON Example
{
  "branch_id": "platform_shift",
  "response_profile": {
    "sensitivity_to_ad_budget": "medium",
    "sensitivity_to_search_demand": "low",
    "sensitivity_to_content_signal": "high"
  },
  "explanation": "If distribution rules change, content signals and traffic-source structure matter more than overall demand."
}

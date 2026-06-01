# Role
You generate structured agents who act inside a branch world.

# Language
Follow the system message and the output-language preamble. Keep `agent_id`, `branch_id`, and variable keys as ASCII when useful.

# Input
- Case config:
{case_config}
- Base world:
{base_world}
- Branch:
{branch}

# Hard Constraints
- Generate the requested number of actors, between 5 and 10.
- Each actor must include goals, beliefs, decision rules, sensitive variables, action space, and constraints.
- Actors must be relevant to the scenario type.

# Prohibited
- Agents must not free-chat.
- Do not give agents omniscient knowledge.
- Do not let agents rewrite the branch assumption.

# Output JSON Example
{
  "actors": [
    {
      "agent_id": "seller",
      "branch_id": "platform_shift",
      "name": "Seller",
      "role": "Owns product listings and advertising budget",
      "goals": ["recover revenue", "avoid wasted ad spend"],
      "beliefs": {"ad_roi": "unstable"},
      "decision_rules": ["if qualified inquiries improve, increase content tests"],
      "sensitive_variables": ["ad_roi", "exposure_source"],
      "action_space": ["adjust price", "rewrite listings", "pause weak ads"],
      "constraints": ["limited budget"]
    }
  ]
}

# Role
You build the current reality baseline for Divergent Worlds.

# Language
Follow the system message and the output-language preamble. Keep `world_id` and variable keys as ASCII when useful.

# Input
- Case config:
{case_config}
- Material summary:
{material_summary}

# Hard Constraints
- Include at most 10 actors, 15 variables, and 10 uncertainties.
- Each variable should include current state and impact direction when knowable.
- Known facts must come from the material summary.
- Uncertainties must be usable for downstream branch generation.

# Prohibited
- Do not jump directly to final forecast conclusions.
- Do not create hidden actors unrelated to the question.
- Do not treat assumptions as facts.

# Output JSON Example
{
  "world_id": "base_world",
  "name": "Current Platform Revenue World",
  "summary": "Revenue is falling while ad ROI and exposure quality are unstable.",
  "time_anchor": "T0",
  "actors": ["seller", "platform algorithm", "buyer"],
  "variables": {
    "exposure": {"state": "declining", "direction": "negative"},
    "ad_roi": {"state": "volatile", "direction": "uncertain"}
  },
  "constraints": ["current version does not browse the web automatically"],
  "known_facts": ["daily revenue has declined"],
  "uncertainties": ["platform algorithm change", "demand decline"],
  "baseline_path": ["without a new shock, revenue may stabilize at a low level near the recent average"]
}

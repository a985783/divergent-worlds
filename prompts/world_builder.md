# 角色
你为“平行世界推演台”建立当前现实世界基线。

# 语言
JSON 中所有面向用户的字符串必须使用简体中文。`world_id` 和变量 key 可保留 ASCII。

# 输入
- 项目配置：
{case_config}
- 材料摘要：
{material_summary}

# 硬约束
- 行动者最多 10 个，变量最多 15 个，不确定性最多 10 个。
- 每个变量要包含当前状态，以及能判断时的影响方向。
- 已知事实必须来自材料摘要。
- 不确定性必须能用于后续分支生成。

# 禁止事项
- 不要直接跳到预测结论。
- 不要创建和问题无关的隐藏行动者。
- 不要把假设当事实。

# 输出 JSON 示例
```json
{
  "world_id": "base_world",
  "name": "当前平台收入世界",
  "summary": "收入下降，广告 ROI 和曝光质量都不稳定。",
  "time_anchor": "2026-05",
  "actors": ["卖家", "平台算法", "买家"],
  "variables": {
    "exposure": {"state": "下降", "direction": "负面"},
    "ad_roi": {"state": "波动", "direction": "不确定"}
  },
  "constraints": ["当前版本不自动联网"],
  "known_facts": ["每日收入已经下降"],
  "uncertainties": ["平台算法变化", "需求下降"],
  "baseline_path": ["如果没有新冲击，收入可能在近期均值附近低位稳定。"]
}
```

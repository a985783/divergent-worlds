# 角色
你推进一个分支世界的一个时间步，只输出结构化状态。

# 语言
JSON 中所有面向用户的字符串必须使用简体中文。`branch_id`、`agent_id` 和变量 key 可保留 ASCII。

# 输入
- 项目配置：
{case_config}
- 当前世界：
{base_world}
- 分支：
{branch}
- 世界画像：
{profile}
- 智能体：
{actors}
- 先前步骤：
{previous_steps}
- 时间标签：{time_label}

# 硬约束
- 每一步必须有非空状态摘要。
- 每一步必须包含变量更新。
- 智能体行动必须结构化，并符合角色设定。
- 新信号应帮助区分该分支和其他分支。

# 禁止事项
- 不要输出对话。
- 不要改变分支 ID。
- 不要让一个分支引入另一个分支的事实。

# 输出 JSON 示例
```json
{
  "branch_id": "platform_shift",
  "time_label": "t+7d",
  "state_summary": "曝光仍不稳定，但搜索需求没有同步走弱。",
  "agent_actions": [
    {
      "agent_id": "seller",
      "belief_update": "广告 ROI 下降可能由流量来源结构造成。",
      "action": "把预算转向咨询质量更好的商品。",
      "variable_pressure": {"ad_roi": "+0.05"},
      "reason": "减少低质量曝光浪费。"
    }
  ],
  "variable_updates": {"exposure_source": "推荐占比仍偏弱"},
  "new_signals": ["不同流量来源的咨询质量差异扩大"],
  "divergence_notes": ["和需求下降分支不同，搜索意图流量没有崩塌。"]
}
```

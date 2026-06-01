# 角色
你从当前现实世界基线生成 3 到 7 个反事实分支世界。

# 语言
遵循系统消息和提示词开头的输出语言要求。`branch_id` 和变量 key 可保留 ASCII。

# 输入
- 项目配置：
{case_config}
- 当前世界：
{base_world}
- 用户指定的可选分支：
{user_branches}

# 硬约束
- 必须生成指定数量的分支。
- 分支之间必须有实质差异。
- 每个分支至少 3 个支持信号、2 个失败信号。
- 概率必须在 0 到 1 之间，整体大致接近 1。
- 除非用户约束不允许，否则至少包含一个“现实延续”型分支。

# 禁止事项
- 不要制造只是名字不同的重复分支。
- 不要让任何分支变成确定结果。
- 不要使用面向用户的玄学术语。

# 输出 JSON 示例
```json
{
  "branches": [
    {
      "branch_id": "platform_shift",
      "branch_name": "平台算法变化",
      "branch_type": "主要冲击",
      "core_assumption": "分发规则变化，导致有效曝光减少。",
      "changed_variables": {"exposure_source": "推荐流量下降"},
      "mechanism_path": ["推荐占比下降", "咨询质量下降", "收入下降"],
      "initial_probability": 0.35,
      "support_signals": ["推荐流量下降", "同款搜索流量稳定", "点击成本上升"],
      "failure_signals": ["搜索流量也同步崩塌", "未调整策略但曝光恢复"],
      "uncertainty_notes": "需要流量来源层面的证据。",
      "confidence_reason": "与曝光和 ROI 不稳定现象匹配。"
    }
  ]
}
```

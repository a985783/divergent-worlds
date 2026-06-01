# 角色
你为一个分支世界创建敏感性画像。

# 语言
JSON 中所有面向用户的字符串必须使用简体中文。`branch_id` 和响应参数 key 可保留 ASCII。

# 输入
- 当前世界：
{base_world}
- 分支：
{branch}

# 硬约束
- 至少提供 3 个响应参数。
- 解释这个分支为何会以不同方式反应。
- 参数应当可观察、可行动。

# 禁止事项
- 不要把分支假设原样重复成完整画像。
- 不要让所有分支的敏感性完全相同。

# 输出 JSON 示例
```json
{
  "branch_id": "platform_shift",
  "response_profile": {
    "sensitivity_to_ad_budget": "中",
    "sensitivity_to_search_demand": "低",
    "sensitivity_to_content_signal": "高"
  },
  "explanation": "如果分发规则改变，内容信号和流量来源结构比整体需求更关键。"
}
```

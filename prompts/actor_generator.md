# 角色
你生成在分支世界中行动的结构化智能体。

# 语言
遵循系统消息和提示词开头的输出语言要求。`agent_id`、`branch_id` 和变量 key 可保留 ASCII。

# 输入
- 项目配置：
{case_config}
- 当前世界：
{base_world}
- 分支：
{branch}

# 硬约束
- 生成请求数量的行动者，数量在 5 到 10 之间。
- 每个行动者必须有目标、信念、决策规则、敏感变量、行动空间和约束。
- 行动者必须和场景类型相关。

# 禁止事项
- 智能体不能自由聊天。
- 不要给智能体全知视角。
- 不要让智能体改写分支假设。

# 输出 JSON 示例
```json
{
  "actors": [
    {
      "agent_id": "seller",
      "name": "卖家",
      "role": "负责商品和广告预算",
      "goals": ["恢复收入", "避免无效广告消耗"],
      "beliefs": {"ad_roi": "不稳定"},
      "decision_rules": ["如果有效咨询改善，就增加内容测试"],
      "sensitive_variables": ["ad_roi", "conversion_quality"],
      "action_space": ["调整价格", "修改商品文案", "暂停弱广告"],
      "constraints": ["预算有限"]
    }
  ]
}
```

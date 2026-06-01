# CHANGELOG

## [1.0.0] - 2026-06-01

首次公开版本，面向本地运行的平行世界多 Agent 推演工作台。

### Added

- 五幕工作台：项目创建、材料解析、初始世界、平行分支、推演控制台、分支比对与预测报告在同一 Streamlit 应用内串联。
- 智能体推演舞台：世界线图谱、逐步事件时间线、参演智能体阵列与分支轨道可视化展示。
- 结构化推演引擎：材料摘要、基线世界、分支世界、世界画像、智能体、时间步推演、分歧分析、预测卡与报告均使用 Pydantic 模型约束。
- 可证伪预测卡：输出概率、验证窗口、支持信号、失败信号、无信息信号、止损条件与观察动作。
- 预测校准账本：本地 SQLite 保存预测卡，可回填现实结果并计算 Brier 分数。
- 本地恢复机制：案例中间产物按阶段写入 `DATA_DIR/cases/`，中断后可从历史项目恢复。
- README 顶部加入真实 LLM 推演产生的工作台截图。

### Changed

- 公开仓库默认忽略 `data/`、`.env*`、`.streamlit/secrets.toml`、`docs/internal/` 与 `.sisyphus/`，避免本地数据、内部规划和私有语境进入仓库。
- 一次性本地翻译脚本已移入 `.sisyphus/internal-scripts/`，不随公开仓库发布。
- `pyproject.toml` 显式声明发布包，确保 CI 中 `pip install -e ".[dev]"` 不再因 flat layout 自动发现失败。

### Verified

- 本地 `ruff check .` 通过。
- 本地 `pytest tests/` 通过。

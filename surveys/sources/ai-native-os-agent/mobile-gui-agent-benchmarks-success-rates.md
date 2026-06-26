https://arxiv.org/abs/2512.19432

# 移动 GUI Agent 基准与成功率汇总（MobileWorld 及其它）

## MobileWorld（arXiv 2512.19432, 2026-01）
- 标题: MobileWorld: Benchmarking Autonomous Mobile Agents in Agent-User Interactive and MCP-Augmented Environments
- 针对 AndroidWorld 饱和（SOTA >90%）提出更难基准
- 硬数字：表现最好的 agentic framework 在 MobileWorld 上仅 **51.7%** 成功率

## AndroidWorld（arXiv 2405.14573, Google）
- 116 任务 / 20 app；原论文最佳 agent **30.6%**；2026 年 SOTA >90%

## AppAgent / AppAgentX（arXiv 2503.02268）
- AppAgent 无记忆基线成功率 **16.9%**
- 加链式记忆后提升到 **70.8%**
- AppAgentX 进一步把平均成功率提升到 **71.4%**

## 其它单点数字（二手综述，标注来源）
- MobileUse 在 AndroidWorld 上 **62.9%**（arXiv 2507.16853）
- DroidRun 在 65 个真实任务上 **43%**（aimultiple 报道）

## 与综述关联
不同基准成功率差异巨大（16.9% ~ 90%+），说明"agentic OS 自动化"高度依赖记忆/规划机制与基准难度；
端侧小模型（3B 级）与云端大模型在这些基准上的差距，是"端云协同 agentic OS"路线的核心动因。

# AgentOS 四组件调研 — 执行计划

**任务**：执行《AgentOS 组件调研 Prompt 集》（/mnt/agents/upload/user_pasted_clipboard_long_content_as_file_# AgentOS 组件调研 Promp.txt），对四个核心组件（推理框架 / 沙箱框架 / 记忆框架 / 内存管理）完成产业界+学术界深度调研，产出四份调研报告并整合。

**路线**：deep-research-swarm Route B（Focused Search — 问题清单明确、维度清晰）。

## Stage 1 — 并行深度调研（4 个 research subagent，并行）
加载 skill：deep-research-swarm。
每个 subagent 接收：通用调研要求（G 节）+ 对应组件 Prompt 全文（背景、核心问题、调研对象、组件特有输出）。
- Agent 1：推理框架与推理能力 → research_inference.md
- Agent 2：沙箱框架与执行能力 → research_sandbox.md
- Agent 3：记忆框架与记忆能力 → research_memory.md
- Agent 4：内存管理（传统+模型内存）→ research_memmgmt.md

统一输出要求：技术谱系表 / 关键数据（带出处与日期）/ 趋势判断 / 对我方架构立场的「支持/挑战/需要修订」逐条判断 + 组件特有输出。时间范围 2024-01 至 2026-11，来源以官方文档与顶会论文为准，区分事实与判断，宁缺毋滥。

## Stage 2 — 质检（reviewer subagent，对四份报告并行抽查）
验证：关键论断是否有来源、数据是否可核实、是否覆盖全部核心问题、是否有虚构。不合格则打回补充。

## Stage 3 — 整合（1 个整合 subagent 或主 agent）
加载 skill：report-writing。
- 合并谱系表 → 《AgentOS 外部参照全景》
- 汇总「公认空白点」× 负载建模/系统仿真 → 立项差异化论据
- 产出整合报告 agentos_research_final.md（含四份分报告 + 全景 + 差异化论据）

## Stage 4 — 交付格式化
加载 skill：docx。
将最终报告转为 .docx 交付（含 .md 源文件）。

输出目录：/mnt/agents/output/agentos_research/

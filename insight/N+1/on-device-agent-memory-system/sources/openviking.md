# OpenViking：面向 AI Agent 的上下文数据库 / 上下文文件系统

- 官网: https://openviking.ai/
- 代码: https://github.com/volcengine/OpenViking （volcengine / 火山引擎；License: AGPLv3 主体，Apache-2.0 CLI/examples）
- 文档: https://volcengine-openviking.mintlify.app/
- 组件拆解参考: https://deepwiki.com/volcengine/OpenViking
- 学术底座: 《VikingMem: A Memory Base Management System for Stateful LLM-based Applications》(VLDB 2026)
- 版本: 采集于 v0.3.x（基准数据标注 v0.3.22）
- Type: 开源系统 + 工程文档（非端侧专用；含嵌入式单机模式）

## 一句话主张
用「文件系统范式」取代扁平向量库 RAG——把 Agent 需要的记忆 / 资源 / 技能统一映射为
`viking://` 协议下的虚拟目录（每个对象一个 URI），配合 L0/L1/L2 分层加载、目录递归检索、
可视化检索轨迹与自演化会话管理，统一管理 Agent 的上下文。

## 针对的痛点（5）
1. **上下文碎片化** —— 记忆散落在代码 / 向量库 / 技能里，缺统一管理。
2. **上下文需求激增** —— 长程任务持续产出上下文，简单截断即丢信息。
3. **检索效果差** —— 传统 RAG 扁平存储、缺全局视野，召回质量不稳。
4. **上下文不可观测** —— 黑盒 RAG 难以调试「为什么召回这条」。
5. **记忆迭代有限** —— 多数系统只有用户交互记忆，缺 Agent 任务经验，且是静态的。

## 核心方案（五大概念）
- **文件系统管理**：`viking://` 虚拟目录 + 唯一 URI，`ls/find/grep/tree` 确定性操作。
- **分层加载 L0/L1/L2**：L0 摘要(~100 tok, `.abstract.md`) / L1 概览(~2k tok, `.overview.md`) / L2 原文(按需)。
- **目录递归检索**：意图分析 → 向量检索定位高分目录 → 目录内二次检索 → 递归下钻 → 聚合。
- **可视化检索轨迹**：全程记录 `viking://` 路径，检索可回放、可观测、可调试。
- **自演化会话管理**：会话结束抽取用户记忆 + Agent 经验（Profile/Preferences/Entities/Events/Cases/Patterns），写回 `user/` 与 `agent/`。

## 实现架构（分层，据 DeepWiki 拆解）
- **客户端层**：`ov` CLI(Rust) / `AsyncOpenViking`(Python SDK, 嵌入模式) / `AsyncHTTPClient`(服务模式)。
- **服务编排层**：`OpenVikingService` 中央编排 → `FSService`(路径/URI) + `ResourceService`(摄取/L0-L2 加工) + 会话/记忆服务；多租户 `RequestContext[account_id]`。
- **存储抽象层**：`VikingFS`(虚拟 FS·`viking://`) | `AGFS`(Go 分布式 FS·local/S3/memory，嵌入模式经 Rust FFI `RAGFSBindingClient`) | `VikingVectorIndexBackend`(向量索引)。
- **AI 服务集成层**：`VLMFactory`(Volcengine Doubao / OpenAI / LiteLLM) + `EmbedderBase`(dense/sparse/hybrid，13+ 供应商)。
- **部署模式**：嵌入模式（进程内、零网络）/ 服务模式（`openviking-server`，REST，默认 :1933，API-Key 多租户）。
- **技术栈**：Python 3.10+ / Rust(CLI+FFI) / Go 1.22+(AGFS) / C++17(向量扩展)。

## 关键基准（v0.3.22）
- **LoCoMo（长对话用户记忆）**：OpenClaw+OpenViking 82.08% / Hermes+OpenViking 82.86% / Claude Code+OpenViking 80.32%；对比自带方案延迟降 24–59%、token 降 34–91%。
- **tau2-bench（Agent 经验记忆）**：Retail 70.94% → 77.81%（+6.87pp）；Airline 54.38% → 66.25%（+11.87pp）。
- **HotpotQA（知识库 QA）**：Naive RAG 62.50% → OpenViking top-20 91.00%；5 数据集均值 66.87%、检索延迟 0.19s、建索引 8.7M tokens（LightRAG 为 62.7M）。
- MarkTechPost 报道 LoCoMo10（1,540 例）：OpenClaw memory-core 35.65%@24.6M tok → +OpenViking 52.08%@4.3M tok。

## 与本目录端侧语境的关系
OpenViking 主体是**服务端上下文数据库**（Go 分布式 FS、S3、K8s/Helm、HTTP 多租户），并非端侧专用。
但其**嵌入模式 + AGFS 本地/内存后端**是进程内、零网络的单机形态，可类比端侧部署；其
**文件系统范式、L0/L1/L2 分层加载、目录递归检索**等思想与 [[on-device-agent-memory-system]]
里 MemoryOS 三级明文记忆、以及「省 token / 省 RAM」的端侧诉求高度呼应，是横向对照的好样本。
引用其端侧结论时须注意区分「服务端设计」与「可迁移到端侧的部分」。

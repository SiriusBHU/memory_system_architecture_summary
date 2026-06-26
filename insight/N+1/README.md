# N+1：下一代终端内存系统设计优化研究

> 调研范围：2023-2026 学界顶会 + 业界实践
> 状态：✅ 全部主题调研撰写完成

## 主题总览

| # | 主题 | 关键研究 / 出处 | 状态 |
|---|------|----------------|------|
| 1 | [端侧 LLM KV Cache 与多 Agent 记忆管理](on-device-kv-cache-management-CN.md) | KVNAND, KVSwap, Q4 Persistent Cache, Agent.xpu | ✅ 已完成 |
| 2 | [eBPF 可编程内核内存策略](ebpf-programmable-memory-CN.md) | eBPF-mm, cachebpf, FetchBPF, PageFlex, CBMM, HawkEye | ✅ 已完成 |
| 3 | [异构 SoC 端侧 AI 推理调度与带宽管理](heterogeneous-soc-inference-CN.md) | Agent.xpu, HeteroInfer (SOSP'25), mllm-NPU, PowerInfer-2 | ✅ 已完成 |
| 4 | [分级内存管理与页面放置优化](tiered-memory-management-CN.md) | Colloid (SOSP'24), SoarAlto (OSDI'25), MGLRU, NeoMem, TPP | ✅ 已完成 |
| 5 | [LPDDR5X 带宽与能效优化](lpddr5x-bandwidth-efficiency-CN.md) | Samsung/SK Hynix/Micron 10.7Gbps LPDDR5X, JEDEC | ✅ 已完成 |
| 6 | [ARM 内存安全与机密计算 (CCA/MTE)](arm-memory-safety-cca-mte-CN.md) | ARM CCA (arxiv 2504.08508), MTE, RME, TikTag | ✅ 已完成 |
| 7 | [ML 驱动的智能内存分配](ml-driven-memory-allocation-CN.md) | LLAMA (ASPLOS'20), CACM'24, LeCaR, GL-Cache, Voyager, FarSight | ✅ 已完成 |
| 8 | [终端侧 Agent 记忆系统（外置分层记忆）](on-device-agent-memory-system-CN.md) | MemGPT, Mem0, MemOS, MemoryOS (EMNLP'25), A-MEM (NeurIPS'25) | ✅ 已完成 |
| 8b | [实际案例结构拆解：PagedAttention 与 MemoryOS](agent-memory-case-studies-CN.md) | vLLM PagedAttention (SOSP'23), MemoryOS, MemOS MemCube | ✅ 已完成 |

> 主题 8 是主题 1（KV Cache 存储层）的上层姊妹篇：聚焦 Agent「记忆系统」的设计——把记忆从上下文窗口外置为分层、可检索、自治理的记忆 OS。
> 主题 8b 给「KV Cache 管理」与「记忆系统」各挑一个真实系统逐层拆解、配架构图（[assets/pagedattention-arch.svg](assets/pagedattention-arch.svg)、[assets/memoryos-arch.svg](assets/memoryos-arch.svg)），并指出二者经 MemOS `MemCube` 同构于一条记忆层级。

## 关键源列表

### 学术论文
- **Tiered Memory Latency-Aware Placement** — ACM DL (ASPLOS 2025): https://dl.acm.org/doi/10.1145/3694715.3695968
- **KVNAND: DRAM-free In-Flash KV Cache** — arxiv 2512.03608
- **eBPF-mm: Programmable Huge Page Policy** — arxiv 2409.11220
- **Q4 Persistent KV Cache for Multi-Agent** — arxiv 2603.04428
- **KVSwap: Edge KV Cache Offloading** — arxiv 2511.11907
- **Agent.xpu: Heterogeneous SoC Scheduling** — arxiv 2506.24045
- **ARM CCA for On-Device ML Protection** — arxiv 2504.08508
- **ML-based Memory Allocation (CACM)** — https://cacm.acm.org/research-highlights/combining-machine-learning-and-lifetime-based-resource-management-for-memory-allocation-and-beyond/

### 业界资料
- **Samsung LPDDR5X 10.7Gbps** — Samsung Semiconductor Press
- **ARM MTE Whitepaper** — ARM Developer
- **Android Memory Management (Esper Blog)** — LSFMMBPF 2025 回顾
- **LWN LSFMMBPF 2025** — https://lwn.net/Articles/lsfmmbpf2025/

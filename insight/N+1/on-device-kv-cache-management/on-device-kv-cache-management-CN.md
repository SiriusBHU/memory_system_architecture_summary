# 端侧 LLM KV Cache 与多 Agent 记忆管理机制

> 本文对比端侧大模型推理中 KV Cache 的原始方案（纯 DRAM 驻留）与演进方案（多级存储 + 量化 + 持久化 + 异构协同调度），覆盖 2024–2026 学界（SOSP、arxiv）与业界（Apple MLX、Qualcomm）进展。

## 1. 范围与方法

**领域定义。** 资源受限终端设备（手机、PC、边缘开发板）上大语言模型推理过程中 KV Cache 的内存管理。KV Cache 存储注意力中间状态，其大小随序列长度和批大小线性增长，是长上下文生成阶段的内存消耗主体。

**"原始"与"演进"的含义。** *原始方案*是标准的 DRAM 驻留 KV Cache：完整 FP16/BF16 KV 张量驻留在系统 DRAM 中，按请求分配，会话结束后丢弃。*演进方案*是一组组合技术——量化（Q4/Q8）缓存、NVMe/Flash 持久化存储、NPU/iGPU 异构计算调度、跨 Agent 缓存共享——共同打破了"一个上下文 = 一份 DRAM 拷贝"的假设。

**来源。** 12 个主要来源：6 篇学术论文（SOSP 2025、arxiv 2024–2026），3 份业界资料（Apple MLX、Samsung LPDDR5X），3 个系统级参考（llama.cpp 量化 KV、vLLM PagedAttention、oMLX 双层缓存）。来源类型涵盖学术论文、开源框架文档和厂商工程博客。

## 2. 问题背景

**系统需要做什么。** 在 8–16 GB DRAM 的设备上本地运行多轮 LLM 推理（7B–14B 参数），支持 32K–100K+ token 上下文的 Agent 工作流（会议摘要、文档分析、多步推理）。

**为什么这个领域变得困难。** KV Cache 大小按 `2 × n_layers × n_heads × head_dim × seq_len × dtype_bytes` 缩放。LLaMA3-8B 在 FP16 下 32K 上下文单请求 KV Cache 约 4.3 GB；batch-12 下达到 54 GB [KVSwap]。移动端 DRAM 带宽（LPDDR5X ~70 GB/s）被模型权重、激活和 KV Cache 共享，产生争用。Flash 存储（NVMe ~1.8 GB/s，eMMC ~250 MB/s）比 DRAM 慢 40–280×，但每 GB 成本仅为 DRAM 的 1/5。

**为什么原始方案不再够用。** 端侧多 Agent 应用（4+ 个并发 Agent，各自独立对话历史）需要同时维护的 KV Cache 总量超出物理 DRAM。冷启动重新 prefill 恢复上下文需要 O(n) 计算，在 4K–32K 上下文下增加 15–172 秒延迟 [Q4 Persistent Cache]。

## 3. 具体问题与瓶颈证据

1. **中等上下文长度下 KV Cache 即超出设备 DRAM** — 4B 参数模型在 32K 上下文 batch-12 下 KV Cache 需 54 GB，远超移动设备 8–16 GB 的 DRAM 预算 [KVSwap]。

2. **多 Agent 上下文切换摧毁延迟** — 切换 Agent 时丢弃并重算 KV Cache 在 Gemma 3 12B / M4 Pro 上的冷 TTFT 为 15.7s（4K）至 172.1s（32K），交互式多 Agent 工作流无法使用 [Q4 Persistent Cache]。

3. **基于稀疏性的淘汰策略在规模上丧失精度** — 已有 KV Cache 压缩方法（InfiniGen、ShadowKV、Loki）在 32K 上下文 RULER 基准上分别产生 78.7%、52.3%、34.0% 的精度损失，不适合生产使用 [KVSwap]。

4. **统一内存 SoC 上的带宽争用** — 在 CPU、iGPU、NPU 共享系统 DRAM 的异构 SoC 上，内存密集型 GEMV 内核（解码阶段）在与其他工作负载并发执行时严重退化，而计算密集型 GEMM 内核（预填充阶段）可以容忍重叠 [Agent.xpu]。

### 瓶颈证据

| 场景 | KV Cache 大小 | 设备 DRAM | 溢出情况 | 来源 |
|---|---|---|---|---|
| LLaMA3-8B, 32K ctx, batch-1 | 4.3 GB | 8 GB（手机） | 占用 RAM 的 54% | [KVSwap] |
| Qwen3-4B, 32K ctx, batch-12 | 54 GB | 64 GB（Jetson） | OOM | [KVSwap] |
| Gemma 3 12B, 32K ctx, 3 agents FP16 | ~12.9 GB | 10.2 GB（M4 Pro） | 第 3 个 agent OOM | [Q4 Cache] |
| Gemma 3 12B, 32K ctx, 12 agents Q4 | ~3.6 GB | 10.2 GB（M4 Pro） | 可容纳 | [Q4 Cache] |
| OPT-30B, 100K ctx | >16 GB | 16 GB（笔记本） | OOM（DRAM） | [KVNAND] |

## 4. 架构：原始 vs 演进

**原始方案 — 纯 DRAM KV Cache**

```
    +-----------+                    +----------+
    |   CPU     |--- prefill ------> |   模型   |
    +-----------+                    |   权重   |
         |                           |  (DRAM)  |
         | 分配                      +----------+
         v                               |
    +------------------+                 |
    | KV Cache (FP16)  | <-- 写入 ------+
    |  驻留 DRAM       |
    |  (按请求分配，    | --- 读取 ---> 注意力计算
    |   会话结束丢弃)  |
    +------------------+
         |
         | 上下文切换 = 丢弃 + 重新 prefill O(n)
         v
    [冷启动：15s-172s TTFT]
```

*原始方案：完整 FP16 KV Cache 驻留 DRAM；上下文切换需要昂贵的重新 prefill。*

**演进方案 — 多级量化持久 KV Cache**

```
    +-----------+      +----------+      +-----------+
    |   CPU     |      |   NPU    |      |   iGPU    |
    +-----------+      +----------+      +-----------+
         |                  |                  |
         |    * 协同调度（带宽感知）            |
         +------------------+------------------+
                            |
                   * 统一物理内存共享 KV Cache
                            |
                            v
    +------------------------------------------+
    | * 热 KV Cache（Q4/Q8 量化）               |
    |   驻留 DRAM — 当前活跃 Agent 上下文       |
    +------------------------------------------+
         |              ^
         | * 持久化     | * 恢复（跳过 prefill）
         v              |
    +------------------------------------------+
    | * 温 KV Cache（Q4 存储于 NVMe/Flash）     |
    |   持久化，按 Agent 隔离，磁盘驻留         |
    +------------------------------------------+
         |              ^
         | * 换出       | * 预取（分组预取）
         v              |
    +------------------------------------------+
    | * 冷 KV Cache（驻留 3D NAND Flash）       |
    |   KVNAND：Flash 内注意力计算              |
    +------------------------------------------+

    [上下文切换：0.6s-1.8s TTFT，缓存直接恢复]
```

*演进方案：三级 KV Cache，搭配 Q4 量化、持久化磁盘存储、Flash 内计算和异构 SoC 协同调度。新增/变更部分以 `*` 标记。*

## 5. 演进方案的收益与未解决问题

### 演进方案为什么有效

- **KV Cache 超出设备 DRAM** — Q4 量化将 KV Cache 压缩至 FP16 的 28.1%，同等 DRAM 预算下可容纳 4× 更多 Agent 上下文（8K 上下文下 12 个 vs 3 个，10.2 GB 设备）[Q4 Persistent Cache]。KVSwap 卸载至 NVMe/eMMC，KV Cache DRAM 占用降至 vLLM 的 1/11 [KVSwap]。

- **多 Agent 上下文切换摧毁延迟** — 持久化 Q4 Cache 消除了重新 prefill，Gemma 3 12B 在 32K 上下文下 TTFT 从 172s 降至 1.8s（94× 提升）[Q4 Persistent Cache]。QKVShare 进一步实现 Agent 间缓存传递，8K 上下文下 397ms vs 1030ms 重新 prefill [QKVShare]。

- **稀疏淘汰方法精度损失过大** — KVSwap 的全缓存卸载（无淘汰）将 RULER 精度损失控制在 2.6%（NVMe），远优于 InfiniGen 的 78.7%、ShadowKV 的 52.3%、Loki 的 34.0% [KVSwap]。

- **统一内存 SoC 带宽争用** — Agent.xpu 的三级带宽压力分发将 prefill（GEMM，计算密集）调度至 NPU、将 decode（GEMV，访存密集）调度至 iGPU，反应式任务延迟降低 4.6× [Agent.xpu]。HeteroInfer 通过 GPU-NPU 异构执行实现 1.34–6.02× 加速 [HeteroInfer/SOSP 2025]。

### 尚未解决的问题

- **量化误差在超长上下文下累积** — Q4 KV Cache 在 DeepSeek 模型上困惑度增加 +3.0%；在安全关键应用（医疗、法律）中，即使微小的精度退化也可能不可接受 [Q4 Persistent Cache]。

- **Flash 延迟仍比 DRAM 慢 40–280×** — NVMe（~1.8 GB/s）和 eMMC（~250 MB/s）为缓存恢复速度设定了硬底线；eMMC 手机的吞吐量比 NVMe 设备差 4.1× [KVSwap]。

- **缺乏跨框架缓存可移植性标准 API** — 各框架（llama.cpp、MLX、vLLM）使用私有 KV Cache 格式；持久化缓存无法跨运行时共享。

- **持续 Flash I/O 的功耗预算** — 持续 NVMe/eMMC 读取进行 KV Cache 交换可能与电池设备的散热和功耗约束冲突；尚无关于活跃交换期间持续功耗的公开数据。

## 6. 对比表

| 维度 | 原始方案（纯 DRAM FP16） | 演进方案（多级 Q4+持久化） | 提升幅度 | 来源 |
|---|---|---|---|---|
| 单 Agent KV Cache 内存（8K ctx, 12B 模型） | ~4.3 GB (FP16) | ~1.2 GB (Q4) | −72%（0.28× 大小） | [Q4 Cache] |
| 最大并发 Agent 数（10.2 GB 预算） | 3 | 12 | +4× | [Q4 Cache] |
| 上下文切换 TTFT（32K, Gemma 3 12B） | 172,096 ms（冷 prefill） | 1,819 ms（缓存恢复） | −94× | [Q4 Cache] |
| 32K 上下文吞吐（Jetson, NVMe） | 17.9 tok/s (vLLM) | 35.6 tok/s (KVSwap, batch-8) | +1.99× | [KVSwap] |
| KV Cache DRAM 占用（32K, batch-8） | 100%（vLLM 基线） | 9.1%（KVSwap 1/11） | −11× | [KVSwap] |
| RULER 精度（32K, LLaMA3-8B） | 100%（完整缓存） | 97.4%（KVSwap NVMe） | −2.6% | [KVSwap] |
| 解码延迟（反应式 Agent 任务） | 1×（llama.cpp 纯 GPU） | 0.22×（Agent.xpu NPU+iGPU） | +4.6× 更快 | [Agent.xpu] |
| 每 GB 成本（DRAM vs Flash, 移动端） | ~$3.5/GB（LPDDR5X） | ~$0.7/GB（UFS 4.0 Flash） | −5× 成本 | [KVNAND] |

## 7. 一词定性

**分级**（Tiered）— KV Cache 管理从单一 DRAM 层级演进为三级层次结构（DRAM → NVMe → Flash），搭配量化持久化，单 Agent DRAM 占用降低 72%，同等内存预算下可容纳 4× 更多并发 Agent。

## 8. 开放问题与注意事项

- **100K+ token 下量化-精度权衡** — 已发表结果上限为 32K 上下文；Q4 持久化缓存在 100K+ token 推理密集型任务（数学、代码）上的表现未知。
- **持续交换下的 Flash 耐久性** — 消费级 UFS/eMMC Flash 写入耐久度有限（通常 1500–3000 P/E 周期）；持续 KV Cache 交换可能加速存储介质老化。尚无公开的磨损均衡分析。
- **跨设备可移植性** — 所有基准数据来自特定设备（M4 Pro、Jetson Orin AGX）；搭载 eMMC + 8 GB DRAM 的手机在真实场景下性能可能差距更大。
- **Agent 记忆一致性** — 当多个 Agent 共享 KV 前缀（如共享系统提示词）时，当前系统不会对持久化 Q4 Cache 中的共享部分去重，浪费存储和带宽。
- **持久化 KV Cache 安全性** — 序列化到 Flash 的 KV Cache 可能包含敏感对话状态；尚无公开工作涉及持久化缓存文件的加密或安全删除。
- **与 OS 内存管理的整合** — KV Cache 交换运行在内核页缓存/swap 子系统之外；与 Android LMKD、zram、内存 cgroup 的共存尚未探索。

## 9. 案例拆解：vLLM PagedAttention 的内部结构

把第 4 节「演进方案」里反复出现的 vLLM PagedAttention 拎出来逐层拆解——它是「KV Cache 管理」这一思路最公开、可验证的真实系统。

**核心思想**：把操作系统的**虚拟内存分页**搬到 KV Cache 上。传统做法给每个请求预留一整段连续显存（按 `max_len`），导致 **60–80%** 被内部碎片与过度预留浪费；PagedAttention 把 KV Cache 切成定长块、按需分配、用一张块表做「逻辑→物理」映射，浪费降到 **<4%**（仅末块半满）[vLLM]。

![vLLM PagedAttention：KV Cache 分页管理结构](assets/pagedattention-arch.svg)

*图. PagedAttention 的三列结构：①请求的逻辑块 → ②块表映射 → ③物理 KV 块池；底部为三大机制（按需分配 / 写时复制共享 / 自动前缀缓存）。复现脚本：[assets/pagedattention-arch.py](assets/pagedattention-arch.py)。*

### 结构逐层拆

| 结构件 | 作用 | 关键参数 |
|---|---|---|
| **KV Block** | 存固定 token 数的 K/V | 默认 16 token/块（vLLM `block_size=16`） |
| **Logical Block** | 序列视角的连续块 | 序列内严格有序 |
| **Physical Block** | 显存里的实际块 | 可非连续、可被多请求共享 |
| **Block Table** | 逻辑→物理映射 + 末块填充计数 | 每请求一张，append-only |
| **Block Manager** | 按需分配/回收物理块 | 维护空闲块池 |
| **Free Queue** | 空闲 + 可复用块池 | 双向链表，按 LRU 排序 |

### 三个关键机制

1. **按需分配** —— 只有生成到新块时才分配物理块，浪费只发生在序列**最后一块**（半满），故 <4% [vLLM]。
2. **写时复制（COW）共享** —— 并行采样 / beam search 时多序列共享同一前缀的物理块，块表指向同一物理块 + **引用计数**；某序列要写入共享块时才复制。复杂采样省内存最多 **55%**，吞吐提升最多 **2.2×** [vLLM]。
3. **自动前缀缓存（跨请求复用）** —— 结构最精巧的部分：
   - **块哈希链**：`hash = H(父块hash, 本块token, 额外id如 LoRA/图像)`；包含父块 ⇒ 只有**整条前缀都相同**时哈希才相同，天然防止「位置错位」误匹配。
   - **命中**：新请求先 `get_computed_blocks()`，对 prompt 逐块哈希查表；命中的物理块被 touch（引用计数 +1、移出空闲队列防淘汰）。
   - **淘汰**：空闲块走 **LRU 双向队列**，仅当 `refcount==0` 才可淘汰；请求结束时块**逆序**归还（含更长前缀的末块更早被淘汰，因为长前缀更难被未来命中）。

### 实测数字

| 维度 | 数值 | 来源 |
|---|---|---|
| 显存浪费 | 60–80% → <4% | [vLLM] |
| 并行采样省内存 | ≤55% | [vLLM] |
| 吞吐 vs HF Transformers | 14–24×（单序列）/ 8.5–15×（3 并行） | [vLLM] |
| 吞吐 vs HF TGI | 2.2–2.5×（单）/ 3.3–3.5×（3 并行） | [vLLM] |

> 注：上表为 vLLM 原论文的吞吐/显存数字，用于刻画**分页机制本身**的收益；vLLM 面向数据中心 GPU，端侧并非直接套用其吞吐倍数。结构性浪费（60–80%→<4%）是与硬件无关的机制收益，端侧同样成立。
>
> 端侧映射：llama.cpp 的 `llama_kv_cache`（cell + seq_id 集合 + `llama_kv_cache_seq_cp` 共享前缀 + 碎片整理）是同一套思想的移动端实现，对应 MemOS 的 **activation memory** 层 [llama.cpp]。
> 本案例（KV/激活层）与上层「记忆系统」案例 MemoryOS（语义/画像层）经 MemOS `MemCube` 同构于同一条记忆层级，二者的结构对照见姊妹篇 [on-device-agent-memory-system](../on-device-agent-memory-system/on-device-agent-memory-system-CN.md) 第 9 节。

## 10. 参考文献

1. **Q4 Persistent KV Cache** — Yshk-Mxim 等, 2026. "Agent Memory Below the Prompt: Persistent Q4 KV Cache for Multi-Agent LLM Inference on Edge Devices." arxiv 2603.04428. URL: https://arxiv.org/abs/2603.04428
2. **KVSwap** — 作者, 2025. "KVSwap: Disk-aware KV Cache Offloading for Long-Context On-device Inference." arxiv 2511.11907. URL: https://arxiv.org/abs/2511.11907
3. **KVNAND** — 作者, 2025. "KVNAND: Efficient On-Device Large Language Model Inference Using DRAM-Free In-Flash Computing." arxiv 2512.03608. URL: https://arxiv.org/abs/2512.03608. 本地副本: [sources/KVNAND-2512.03608.pdf](sources/KVNAND-2512.03608.pdf)
4. **Agent.xpu** — 作者, 2025. "Agent.xpu: Agentic LLM Inference on Heterogeneous Edge SoC." arxiv 2506.24045. URL: https://arxiv.org/abs/2506.24045
5. **QKVShare** — 作者, 2026. "QKVShare: Quantized KV-Cache Handoff for Multi-Agent On-Device LLMs." arxiv 2605.03884. URL: https://arxiv.org/abs/2605.03884
6. **HeteroInfer** — 作者, 2025. "Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference." SOSP 2025 / arxiv 2501.14794. URL: https://dl.acm.org/doi/10.1145/3731569.3764808
7. **KV Cache 管理综述** — 作者, 2024. "A Survey on Large Language Model Acceleration based on KV Cache Management." arxiv 2412.19442. URL: https://arxiv.org/abs/2412.19442
8. **HiFC** — 作者, 2025. "HiFC: High-efficiency Flash-based KV Cache Swapping for Scaling LLM Inference." OpenReview. URL: https://openreview.net/forum?id=onhjdWCxZY
9. **TokenDance** — 作者, 2026. "TokenDance: Scaling Multi-Agent LLM Serving via Collective KV Cache Sharing." arxiv 2604.03143. URL: https://arxiv.org/abs/2604.03143
10. **oMLX** — Apple/社区, 2025. "oMLX: Apple Silicon-Optimized LLM Inference with Two-Tier KV Caching." URL: https://betterstack.com/community/guides/ai/omlx-apple-silicon/
11. **Samsung LPDDR5X** — Samsung Semiconductor, 2024. "Samsung Develops Industry's Fastest 10.7Gbps LPDDR5X DRAM." URL: https://semiconductor.samsung.com/news-events/news/samsung-develops-industrys-fastest-gbps--lpddr5x-dram-optimized-for-ai-applications/
12. **LRAgent** — 作者, 2025. "LRAgent: Efficient KV Cache Sharing for Multi-LoRA LLM Agents." ResearchGate. URL: https://www.researchgate.net/publication/400369782
13. **vLLM / PagedAttention** — Kwon 等, 2023. "Efficient Memory Management for Large Language Model Serving with PagedAttention." SOSP 2023. Blog: https://vllm.ai/blog/2023-06-20-vllm ；前缀缓存设计：https://docs.vllm.ai/en/latest/design/prefix_caching/
14. **llama.cpp KV cache（端侧映射）** — ggml-org/llama.cpp. URL: https://github.com/ggml-org/llama.cpp

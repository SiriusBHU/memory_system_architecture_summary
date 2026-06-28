# 终端侧 Agent 记忆系统：从「上下文内记忆」到「外置分层记忆」

> 本文讨论终端设备上长程 Agent 的**记忆系统**设计，层次上比裸 KV Cache 存储高一层。对比的两端：原始方案——Agent 的记忆就是当前上下文窗口（及其 KV Cache）；演进方案——外置、分层、自管理的记忆系统（"记忆 OS"），把活跃工作集压小，同时把长期记忆持久化并按需检索。本文是 [on-device-kv-cache-management](../on-device-kv-cache-management/on-device-kv-cache-management-CN.md) 的姊妹篇，后者覆盖本文之下的 KV Cache 存储层。

## 1. 范围与方法

**领域定义。** 面向资源受限设备（手机、PC、边缘板卡）上跑多会话、长程任务的 LLM Agent 的记忆架构。这里的"记忆"指 Agent 跨轮、跨会话需要记住的一切：活跃对话上下文、情景事件历史、提炼出的事实、用户画像。核心问题是**记忆存在哪里**、**如何写入/检索/淘汰**——而不只是 KV 张量怎么存。

**这里的"原始"与"演进"指什么。** *原始*方案是**上下文内记忆（in-context memory）**：Agent 的记忆**就是**上下文窗口。历史每轮原样塞回 prompt，KV Cache 是唯一的持久状态，会话结束即丢弃。*演进*方案是**外置分层记忆系统**：一个有界的小工作上下文，外加多级外部记忆（短/中/长期，或情景/语义/画像），配合 LLM 驱动的抽取与整合、按需检索、以及基于热度/衰减的治理。代表系统有 MemGPT、Mem0、MemOS、MemoryOS，其最底层即 KV Cache 复用/持久化。

**来源。** 13 个主要来源：7 篇学术论文（NeurIPS 2025、EMNLP 2025、arXiv 2023–2026），2 个基准（LOCOMO、LongMemEval），2 份端侧现状报告（Edge AI Vision 2026、On-Device LLMs State of the Union 2026），2 个系统参考（CacheBlend/prompt-cache 复用、KV Cache 姊妹篇）。族系：Agent 记忆系统、KV Cache 复用、端侧约束报告、基准。

## 2. 问题背景

**系统要做什么。** 让端侧 Agent 在多会话（数天到数月）里维持连贯、个性化的对话与任务历史，不遗忘，同时跑在手机的内存与功耗预算之内。

**为什么难。** 上下文窗口有限，支撑它的 KV Cache 随留在上下文里的 token 数线性增长。移动端解码受内存带宽约束——移动 NPU 仅 50–90 GB/s，数据中心 GPU 达 2–3 TB/s，差 30–50 倍 [Edge AI Vision 2026]。扣掉 OS 开销后可用 RAM 常常不足 4 GB，而长上下文下 KV Cache 体积可超过模型权重本身 [Edge AI Vision 2026]。整段历史一直留在上下文里是不现实的。

**为什么原始方案不够。** Agent 化、多会话的用法打破了"一个 prompt、短上下文"的假设：原样重放完整历史会让 token 成本和延迟无界增长，截断历史又会让 Agent 遗忘——两条路都塞不进固定的 RAM 预算 [Mem0; MemGPT]。

## 3. 具体问题与瓶颈证据

### 具体问题

1. **有限上下文窗口限制长程记忆** —— Agent 只能"记住"塞得进窗口的内容；超出后，截断会遗忘、全留会撑爆 RAM，因为长上下文下 KV Cache 体积在可用 RAM 不足 4 GB 的手机上可超过模型权重 [Edge AI Vision 2026; MemGPT]。
2. **全上下文重放代价高** —— 每轮喂入完整历史，长会话下 token 数 >10 倍、p95 延迟约 11 倍于带记忆增强的 Agent [Mem0]。
3. **朴素 KV/前缀复用掉精度** —— CacheBlend 这类近似复用比完整 prefill 精度低 7–18%，精确匹配的前缀缓存遇到细微 token 变动就失效，无法低成本地把旧上下文"粘回去" [CacheBlend; 前缀复用研究]。
4. **缺乏跨会话整合** —— 没有外部存储时，Agent 在长对话的多跳、时序推理问题上失败；这恰恰是专用记忆系统在 LOCOMO 上收益最大的地方 [Mem0; MemoryOS]。
5. **记忆无界增长且无治理** —— 只增不减的记忆库，随规模增大检索质量下降；系统需要基于热度/新近度的提升与淘汰（如 MemoryOS 热度阈值 τ=5）才能保持有界 [MemoryOS; 综述]。

### 瓶颈证据

| 指标 | 原始（上下文内 / 全量重放） | 演进（外置记忆） | 来源 |
|---|---|---|---|
| 长会话 token 成本 | 100%（完整历史） | <10%（省 >90%） | [Mem0] |
| p95 延迟（相对全上下文） | 1.0× | 0.09×（−91%） | [Mem0] |
| LOCOMO token 消耗（MemOS） | 15.6 M | 4.4 M（−70%） | [MemOS] |
| LoCoMo 答案精度（LLM-Judge） | OpenAI-memory 基线 | +26%（Mem0） | [Mem0] |
| 移动 vs 数据中心内存带宽 | 50–90 GB/s（手机） | 2–3 TB/s（数据中心 GPU） | [Edge AI Vision] |

关键数据点：长会话下*原始*路径的 token 数 >10 倍、p95 延迟约 11 倍，KV Cache 在可用 RAM 不足 4 GB 的手机上可超过模型权重。解法不是更快的缓存——而是把大部分记忆移出活跃上下文。

## 4. 架构对比：原始 vs 演进

**原始 —— 上下文内记忆（历史活在窗口里）**

```
   +--------+   发送完整历史         +-------------------+
   |  用户  | --------------------> |   Agent (LLM)     |
   +--------+                       |    上下文窗口      |
       ^                            +-------------------+
       |  回复                           |   写入
       |                                 v
       |                        +-----------------------+
       +----------------------- |  KV Cache (DRAM)      |
            流式 token          |  随历史 O(n) 增长      |
                                +-----------------------+
                                         |
                                         | 溢出时：
                                         v
                                +-----------------------+
                                | 截断（遗忘）          |
                                | 或 OOM（超 RAM 预算） |
                                +-----------------------+
   （外部存储：缺失 —— 窗口本身就是记忆）
```

*原始：上下文窗口是唯一的记忆；KV Cache 随历史 O(n) 增长，直到被截断（遗忘）或溢出 RAM。*

**演进 —— 外置分层记忆（记忆 OS）**

```
   +--------+   查询 + 当前轮       +-------------------+
   |  用户  | --------------------> |   Agent (LLM)     |
   +--------+                       | * 有界工作上下文   |
       ^                            |   （很小）         |
       |  回复                       +-------------------+
       |                             |  写入      ^  读取
       |                             v            | * 检索 (top-k)
       |                    +-----------------+    |
       +------------------- | KV Cache (DRAM) |    |
            流式 token      | * 有界工作集 +  |    |
                            | * 复用/持久化   |    |
                            +-----------------+    |
                                 |                 |
                    * 抽取 /      |                 |
                      整合        v                 |
                    +------------------------------------------+
                    | * 外置记忆库（flash / 向量库）           |
                    |   STM(短) -> MTM(中) -> LTM/画像         |
                    |   * 提升(热度/新近), * 淘汰/衰减          |
                    +------------------------------------------+
```

*演进：一个有界的小工作上下文，背后是分层外部存储；Agent 通过抽取/整合写入、通过检索读取、通过热度/衰减的提升与淘汰来管理规模。新增/改动元素以 `*` 标记。*

## 5. 演进为何有效，又还没解决什么

### 演进方案为何有效

- **有限上下文窗口限制长程记忆** —— 记忆外置到多级（STM/MTM/LTM）后，总召回与窗口大小脱钩；MemoryOS 把活跃工作集限制在 7 个对话页，无论历史多长 KV Cache 都保持有界 [MemoryOS]。
- **全上下文重放代价高** —— 只检索相关记忆而非重放全部，省下 >90% token 成本、91% p95 延迟 [Mem0]，LOCOMO token 消耗降 70%（15.6 M → 4.4 M）[MemOS]。
- **朴素 KV/前缀复用掉精度** —— 记忆 OS 不走脆弱的"缓存粘贴"路线，而是通过受管路径把热点明文记忆提升为激活（KV）记忆（MemOS 的 Next-Scene Prediction / 基于 KV 的激活注入），避免近似融合 [MemOS]。
- **缺乏跨会话整合** —— LLM 驱动的抽取/更新（Mem0 的 ADD/UPDATE/DELETE/NOOP；MemoryOS 的 FIFO + 热度提升）维护一致的长期存储，LoCoMo 精度提升 +26%（Mem0）、F1 +49.11%（MemoryOS）[Mem0; MemoryOS]。
- **记忆无界增长且无治理** —— 热度/新近度阈值（MemoryOS τ=5，时间衰减 μ=1e7 秒）控制记忆的提升与淘汰，检索质量不随存储增大而下降 [MemoryOS]。

### 还没解决什么

- **检索未命中仍会"遗忘"** —— 检索器没把相关记忆捞出来，即便事实已存储，Agent 仍会遗忘；检索质量（MemOS 提升后精度也仅 31.68%）成了新瓶颈 [MemOS]。
- **写入侧开销是额外的端侧算力** —— 抽取/整合每轮要跑额外的 LLM 调用，在电池设备上是实打实的能耗与延迟——原始上下文内路径没有这个成本 [Mem0]。
- **嵌入库与向量索引占 RAM/flash** —— 外部记忆、其嵌入、以及 ANN 索引会消耗设备存储与内存带宽；目前没有公开的端侧占用数据 [综述; 端侧 2026]。
- **没有标准的端侧记忆 API** —— MemGPT/Mem0/MemOS/MemoryOS 的 schema 互不兼容；记忆无法跨运行时或跨设备移植，也没有一个是与移动 OS 内存管理（LMKD、zram）协同设计的 [综述]。

## 6. 对比表

| 维度 | 原始（上下文内 / 全量重放） | 演进（外置记忆 OS） | 改进 | 来源 |
|---|---|---|---|---|
| 长会话单查询 token 成本 | 100%（完整历史） | <10% 历史 token | −90%+ | [Mem0] |
| p95 响应延迟 | 1.0×（全上下文） | 0.09× | −91% | [Mem0] |
| LOCOMO token 消耗 | 15.6 M tokens | 4.4 M tokens | −70% | [MemOS] |
| LoCoMo 精度（LLM-as-Judge） | OpenAI-memory 基线 | +26% 相对 | +26% | [Mem0] |
| LoCoMo F1（GPT-4o-mini） | 基线 = 1.0× | +49.11% | +49.11% | [MemoryOS] |
| 活跃工作集大小 | 随历史 O(n) 增长 | 7 个对话页（固定） | 有界（n 不再增长） | [MemoryOS] |
| 记忆检索精度 | n/a（无存储） | 31.68%（在 −70% token 之后） | 相对 23.73% +7.95 pts | [MemOS] |
| 记忆写入成本 | 0 次额外 LLM 调用 | 每轮 +1 次抽取/更新调用 | −（新增推理开销） | [Mem0] |

## 7. 一词概括

**Externalized（外置化）** —— Agent 记忆从固定上下文窗口移出，进入可检索、自管理的外部存储，活跃工作集封顶（MemoryOS：7 页），长会话 token 成本降 70–90%，同时召回精度*提升*（LoCoMo 上 +26% 到 +49%）——这是让长程 Agent 塞进手机不足 4 GB 可用 RAM 的前提。

## 8. 开放问题与注意事项

- **端侧占用尚无实测** —— 所有头条数字（Mem0、MemOS、MemoryOS）都来自云端/服务器 LLM；没人公开过在手机上、与基座模型并存地跑抽取器 + 嵌入器 + 向量索引的 RAM/flash/能耗成本。
- **检索成为新瓶颈** —— 即便最好的系统，精度也就 31.68% 上下；检索未命中与遗忘无法区分，端到端任务精度未必跟随基准上的增益。
- **基准口径漂移** —— LOCOMO/LoCoMo 的轮数与 token 数各来源报告不一致（约 300 轮/约 9K token vs 约 600 轮/约 16K token）；引用前请核对具体切分。
- **激活与明文之间的提升机制尚不成熟** —— MemOS 基于 KV 的激活注入是连接 KV Cache 层的最直接桥梁，但端侧的提升/降级策略、一致性与安全性都未定义。
- **持久化记忆的隐私** —— flash 上外置的画像/情景记忆是长期存在的个人数据；加密、安全删除、用户可见的管理机制都尚未处理。
- **来年复查** —— JEDEC/OS 厂商是否会暴露标准记忆 API，以及是否会出现端侧原生（而非移植服务器）的记忆系统。

## 9. 案例拆解：MemoryOS 的内部结构，以及与 KV 层的同构

把前文反复引用的 MemoryOS（EMNLP 2025 Oral）逐层拆解——它是「外置分层记忆系统」这一思路中最公开、可验证的实际系统。

**核心思路**：把 OS 的**分层存储 + 换页**搬到 Agent 记忆上。最小单元不是 token，而是一次完整问答（Dialogue Page）；时间尺度是会话级。LoCoMo 上 F1 **+49.11%**、BLEU-1 **+46.18%**（GPT-4o-mini）[MemoryOS]。

![MemoryOS：分层记忆系统结构](assets/memoryos-arch.svg)

*图. MemoryOS 的三级存储主干（STM->MTM->LPM，向下沉淀晋升）+ 右侧四模块（Storage/Updating/Retrieval/Generation）+ 检索召回与 Heat 公式。复现脚本：[assets/memoryos-arch.py](assets/memoryos-arch.py)。*

### 结构逐层拆

| 层 | 结构 | 容量 / 规则 |
|---|---|---|
| **STM 短期** | Dialogue Page = `{Q, R, T, meta_chain}` 的 FIFO 队列 | **7 页**，满则挤出最旧页 |
| **MTM 中期** | 同话题页按相似度 **θ=0.6** 聚为 Segment | **≤200 段**，每段算 Heat |
| **LPM 长期画像** | User Persona + Agent Persona | User KB 100 条 FIFO；User Traits **90 维**（3 类）；Agent Traits 100 条 FIFO |

### 四个模块 = 三条数据流

| 模块 | 职责 | 关键规则 |
|---|---|---|
| **Storage** | 三级分层组织 | STM / MTM / LPM |
| **Updating** | 写入 + 晋升 | STM->MTM：FIFO + 话题链；MTM->LPM：Heat>τ=5 段换页 |
| **Retrieval** | 三级召回 | STM 全取；MTM 两阶段（top-m=5 段 -> top-k=5–10 页）；LPM 每类 top-10 |
| **Generation** | 拼装 prompt | 三级召回结果合并后喂给 LLM |

### Heat 晋升公式（决定哪些中期记忆「换页」进长期画像）

```
Heat(segment) = α·N_visit + β·L_interaction + γ·R_recency      (α = β = γ = 1)
              = 被检索次数 + 段内页数 + exp(-Δt / 1e7)
晋升条件: Heat > τ (= 5)
```

这就是 OS 里「访问频率 + 驻留量 + 新近度」决定页是否常驻的翻版——**热的记忆往上沉淀为画像，冷的随时间衰减**。

### 与底层 KV Cache 的结构同构（经 MemOS `MemCube` 接为一层）

把本文的记忆系统与底层 KV Cache 管理叠起来看，它们是**同一架构在不同层的实例**——后者的具体拆解见姊妹篇 [on-device-kv-cache-management](../on-device-kv-cache-management/on-device-kv-cache-management-CN.md) 第 9 节（vLLM PagedAttention）：

| 维度 | PagedAttention（KV / 激活层） | MemoryOS（语义 / 记忆层） |
|---|---|---|
| 管的对象 | 激活态 KV（注意力中间状态） | 语义记忆（事实 / 画像） |
| 最小单元 | KV Block（16 token） | Dialogue Page（一次问答） |
| 时间尺度 | 毫秒 / 每 token | 会话 / 每轮 |
| OS 类比 | 虚拟内存**分页** | 分层存储 + **换页** |
| 淘汰依据 | LRU + 引用计数 | Heat（频率+量+新近度）+ FIFO |
| 复用机制 | 前缀块哈希共享 | 话题段归并 + 画像沉淀 |

**结论**：MemOS 论文里的 `MemCube` 把这两层正式接到一起——它的 **activation memory 就是 KV Cache 层（PagedAttention 管的东西）**，**plaintext memory 就是语义记忆层（MemoryOS 管的东西）**，并定义二者间的「提升/降级」（热点明文记忆 -> 注入成 KV）。所以「KV 管理」和「记忆系统」在架构上不是两件事，而是同一条记忆层级的**底层（激活/KV）**与**上层（语义/画像）**。

## 10. 参考文献

1. **MemGPT** — Packer et al., 2023. "MemGPT: Towards LLMs as Operating Systems." arXiv 2310.08560. URL: https://arxiv.org/abs/2310.08560
2. **Mem0** — Chhikara et al., 2025. "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory." arXiv 2504.19413. URL: https://arxiv.org/abs/2504.19413. 本地副本：[sources/mem0-2504.19413.md](sources/mem0-2504.19413.md)
3. **MemOS** — Li et al., 2025. "MemOS: A Memory OS for AI System." arXiv 2507.03724（短版 2505.22101）。URL: https://arxiv.org/abs/2507.03724。代码：https://github.com/MemTensor/MemOS。本地副本：[sources/memos-2507.03724.md](sources/memos-2507.03724.md)
4. **MemoryOS** — Kang et al., 2025. "Memory OS of AI Agent." arXiv 2506.06326，EMNLP 2025 Oral。URL: https://arxiv.org/abs/2506.06326。代码：https://github.com/BAI-LAB/MemoryOS。本地副本：[sources/memoryos-2506.06326.md](sources/memoryos-2506.06326.md)
5. **A-MEM** — Xu et al., 2025. "A-MEM: Agentic Memory for LLM Agents." arXiv 2502.12110，NeurIPS 2025。URL: https://arxiv.org/abs/2502.12110
6. **Memory in the Age of AI Agents: A Survey** — Liu et al., 2025. 论文列表：https://github.com/Shichun-Liu/Agent-Memory-Paper-List
7. **Multi-Agent Memory from a Computer Architecture Perspective** — 2026. arXiv 2603.10062. URL: https://arxiv.org/pdf/2603.10062
8. **CacheBlend** — Yao et al., 2024/2025. "CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion." arXiv 2405.16444. URL: https://arxiv.org/abs/2405.16444
9. **Prompt Cache** — Gim et al., 2024. "Prompt Cache: Modular Attention Reuse for Low-Latency Inference." MLSys 2024. URL: https://arxiv.org/abs/2311.04934
10. **KVFlow** — 2025. "KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows." arXiv 2507.07400. URL: https://arxiv.org/html/2507.07400v1
11. **LOCOMO 基准** — Maharana et al., 2024. "Evaluating Very Long-Term Conversational Memory of LLM Agents." URL: https://arxiv.org/abs/2402.17753
12. **On-Device LLMs in 2026** — Edge AI and Vision Alliance, 2026. URL: https://www.edge-ai-vision.com/2026/01/on-device-llms-in-2026-what-changed-what-matters-whats-next/
13. **On-Device LLMs: State of the Union, 2026** — V. Chandra, 2026. URL: https://v-chandra.github.io/on-device-llms/
14. **vLLM / PagedAttention（KV 层对照）** — Kwon et al., 2023. "Efficient Memory Management for Large Language Model Serving with PagedAttention." SOSP 2023. URL: https://vllm.ai/blog/2023-06-20-vllm

# 异构 SoC 端侧 AI 推理调度与带宽管理

> 本文对比了端侧 LLM 推理的「原始方案」（单加速器推理）与「演进方案」（异构多 IP 协同调度），涵盖学术界（SOSP 2025、ASPLOS 2025、arxiv）与产业界（Intel、Qualcomm）2024–2026 年的进展。

## 1. 范围与方法

**领域界定。** 在统一内存 SoC（手机、笔记本、边缘设备）上，跨异构计算 IP（CPU、GPU、NPU）进行大语言模型推理时的调度与带宽管理。核心矛盾是：自回归解码阶段的瓶颈不在算力而在内存带宽，而单一加速器无法打满共享 DRAM 总线。

**「原始」与「演进」的含义。** *原始方案*指单加速器推理：LLM 完全运行在单一计算 IP 上（GPU-only 如 MNN/MLC，或 NPU-only 如 llm.npu），其余片上加速器闲置。*演进方案*指异构多 IP 协同调度：CPU、GPU、NPU 并行执行不同推理阶段或张量分区，通过带宽感知调度协调，并利用统一物理内存零拷贝共享 KV 缓存。

**资料来源。** 10 篇主要文献：4 篇学术论文（SOSP 2025、ASPLOS 2025、arxiv 2024–2026），3 个系统框架（llama.cpp、MNN、PowerInfer-2），3 份厂商资料（Qualcomm Snapdragon 8 Gen 3、Intel Core Ultra、Samsung LPDDR5X）。涵盖同行评审系统论文、开源运行时文档与 SoC 厂商数据手册。

## 2. 问题背景

**系统需要做什么。** 在 8–32 GB 共享 DRAM 的手机或边缘 SoC 上本地运行 1B–8B 参数 LLM，为用户的交互式查询（reactive）提供低延迟响应（< 100 ms/token），同时为后台主动任务（proactive，如摘要、RAG 索引、Agent 流水线）提供高吞吐。

**为什么这个领域变难了。** 现代手机 SoC（骁龙 8 Gen 3、Intel Core Ultra）集成 3 种以上计算 IP——CPU 核、移动 GPU（Adreno/Arc）和专用 NPU（Hexagon/AI Boost）——但现有推理引擎将它们视为互斥的独立目标。NPU 擅长固定形状 INT8 GEMM（预填充阶段），但在动态形状 GEMV（解码阶段）上严重退化；GPU 可处理动态形状，但单独无法打满 DRAM 带宽。LPDDR5X 峰值带宽约 68 GB/s，而单 GPU 解码仅能利用 40–45 GB/s（59–66%）[HeteroInfer]。与此同时，Agent 工作负载引入了并发的 reactive 与 proactive LLM 流，其延迟/吞吐目标相互冲突，单加速器引擎无法区分优先级。

## 3. 具体问题与瓶颈证据

1. **单加速器浪费带宽** — 骁龙 8 Gen 3 上，GPU-only 解码仅利用 68 GB/s DRAM 总线的 40–45 GB/s（59–66%），约 25 GB/s 闲置。NPU-only 利用率类似。GPU+NPU 并发执行可达 ~60 GB/s（88% 利用率），带宽提升 37% [HeteroInfer]。

2. **NPU 无法高效处理动态解码形状** — NPU 脉动阵列固定为 32×32；任何小于 32 的激活维度都会产生与维度 32 相同的延迟，浪费算力。自回归解码（batch-1 GEMV）触发此「阶梯性能」下限，使 NPU-only 解码慢于 GPU [HeteroInfer]。

3. **GEMV 核在并发执行下退化，GEMM 核可容忍** — 内存密集型 GEMV（解码）在与另一个高带宽核共享 DRAM 总线时延迟显著恶化。计算密集型 GEMM（预填充）因不受带宽限制，在并发执行下仍保持高效 [Agent.xpu]。

4. **无流级并发与优先级机制** — 现有引擎（llama.cpp、MNN、MLC）假设单次推理，无法区分 reactive 与 proactive 请求。后台摘要任务会阻塞交互式查询，因为没有抢占或优先级调度机制 [Agent.xpu]。

5. **NPU 图编译对动态输入过慢** — 骁龙 8 Gen 3 上，序列长度 135 时 NPU 在线图生成耗时 408.4 ms，使朴素动态形状 NPU 推理比 GPU-only 更慢 [HeteroInfer]。

### 瓶颈证据

| 场景 | 指标 | 单 IP | 异构 | 差距 | 来源 |
|---|---|---|---|---|---|
| 骁龙 8 Gen 3, 解码, Llama-8B | DRAM 带宽利用 | 40–45 GB/s (GPU) | ~60 GB/s (GPU+NPU) | +37% BW | [HeteroInfer] |
| 骁龙 8 Gen 3, 解码, Llama-8B | 吞吐量 | 9.3 tok/s (MNN GPU) | 14.0 tok/s (HeteroInfer) | 1.50x | [HeteroInfer] |
| Intel Core Ultra, 混合 Agent 负载 | Reactive 延迟 | 1x (llama.cpp CPU) | 0.22x (Agent.xpu) | 4.6x 更低 | [Agent.xpu] |
| 骁龙 8 Gen 3, 预填充 256tok, Llama-8B | 吞吐量 | 42.4 tok/s (MNN GPU) | 247.9 tok/s (HeteroInfer) | 5.85x | [HeteroInfer] |
| NPU 在线图生成, seq_len=135 | 编译延迟 | 408.4 ms | 0 ms（离线预编译） | 消除 | [HeteroInfer] |

## 4. 架构：原始方案 vs 演进方案

**原始方案 — 单加速器推理**

```
    用户请求
         |
         v
    +-----------+
    |  运行时    |--- 加载权重 ---> +----------+
    | (MNN /     |                 |  模型权重  |
    |  MLC /     |                 | (DRAM)    |
    |  llm.npu)  |                 +----------+
    +-----------+
         |
         | 所有层分发到同一 IP
         v
    +-------------------+
    |  单一加速器        |      +-----------+
    |  (GPU 或 NPU)     | ---> | KV Cache  |
    |                   |      | (DRAM)    |
    |  预填充: GEMM     |      +-----------+
    |  解码:   GEMV     |           |
    +-------------------+           |
         |                     注意力计算
         | 闲置: 其余 IP           |
         | 未使用 (NPU/CPU         v
         | 或 GPU/CPU)        输出 Token
         v
    [带宽利用率: 59-66%]
    [无抢占, 无优先级]
```

*原始方案：所有层运行在单一 IP 上；其余加速器闲置。带宽利用率上限约 60%。无流级调度。*

**演进方案 — 异构多 IP 协同调度**

```
    用户请求 ──────────────────── 后台任务
    (reactive, 低延迟)            (proactive, 高吞吐)
         |                                  |
         v                                  v
    +----------------------------------------------+
    | * 流感知调度器                                  |
    |   - * 优先级队列 (reactive > proactive)        |
    |   - * 核级抢占 (<100 ms)                       |
    |   - * 带宽压力监控 (Pmem)                       |
    +----------------------------------------------+
         |                    |                |
         v                    v                v
    +---------+        +----------+      +-----------+
    |  CPU    |        | * NPU    |      | * GPU     |
    | (离群值  |        | (预填充   |      | (解码     |
    |  计算)   |        |  GEMM,   |      |  GEMV,    |
    +---------+        |  静态)    |      |  动态)    |
                       +----------+      +-----------+
                            |                  |
                  * 张量分区           * 张量分区
                  * 亲和性引导         * 弹性绑定
                            |                  |
                            v                  v
                   +-------------------------------+
                   | * 统一物理内存                    |
                   |   (零拷贝 KV Cache 共享)         |
                   +-------------------------------+
                            |
               * 带宽感知调度:
               低 (<0.4):  激进并发调度
               中 (0.4-0.7): 选择性配对
               高 (>=0.7): 顺序执行, reactive 优先
                            |
                            v
                      输出 Token
    [带宽利用率: ~88%]
    [Reactive 延迟: 降低 4.6x]
```

*演进方案：预填充（GEMM）路由至 NPU，解码（GEMV）路由至 GPU，张量分区跨两者拆分；带宽压力调度防止 DRAM 争用；核级抢占保障 reactive 响应性。新增/变更部分以 `*` 标记。*

## 5. 演进方案为何有效，以及尚未解决什么

### 为何有效

- **单加速器浪费带宽** — GPU+NPU 并发执行将 DRAM 带宽利用率从 59–66% 提升至 ~88%（骁龙 8 Gen 3 上从 40–45 GB/s 升至 ~60 GB/s），直接转化为 Llama-8B 1.50x 解码加速 [HeteroInfer]。

- **NPU 无法处理动态解码形状** — 阶段感知调度将预填充（计算密集 GEMM，静态形状）路由至 NPU，解码（内存密集 GEMV，动态形状）路由至 GPU，发挥各 IP 优势。HeteroInfer 的激活中心分区进一步将动态序列拆分为 NPU 友好的固定长度块加 GPU 处理的余数 [HeteroInfer]。

- **GEMV 并发退化** — Agent.xpu 的三级带宽压力调度实时监控内存压力（Pmem），在 Pmem < 0.4 时激进并发，Pmem >= 0.7 时切换为顺序执行，在利用并行性的同时防止解码 GEMV 退化 [Agent.xpu]。

- **无流级并发** — Agent.xpu 引入 <100 ms 粒度的核级抢占（通过算子分块），加上松弛感知回填（在结构/计算/内存松弛窗口中插入 proactive 核），实现 reactive 延迟降低 4.6x，同时 proactive 吞吐提升 1.6–6.8x [Agent.xpu]。

- **NPU 图编译过慢** — HeteroInfer 的离线性能分析-求解器协作在 < 20 分钟内为所有预期张量形状预编译 NPU 图，完全消除 408.4 ms 的在线编译开销 [HeteroInfer]。

### 尚未解决的问题

- **持续双 IP 负载下的热节流** — GPU+NPU 并发运行增加功耗和芯片温度；尚无研究测量移动热包络（皮肤温度 < 42 °C、DVFS 降频）下的持续性能。实际表现可能低于基准测试。

- **跨 SoC 厂商的模型可移植性** — HeteroInfer 的离线分析器需为每款新 SoC 重新特征化（骁龙 vs. 天玑 vs. Exynos）；Agent.xpu 目前仅支持 Intel（OpenVINO）。不存在厂商中立的异构推理 API。

- **NPU INT8 量化的精度影响** — NPU 路径通常要求 INT8 或更低精度；相对 FP16 GPU 推理的精度差异取决于模型，且未在多样化任务（推理、代码、多语言）上系统性评测。

- **OS 级资源仲裁** — 异构调度器运行在用户态，无法感知其他竞争 GPU/NPU 的应用（游戏、相机 ISP、后台 ML 任务）。与 Android NNAPI 调度或 iOS CoreML 资源管理的集成尚未实现。

## 6. 对比表

| 维度 | 原始方案（单 IP） | 演进方案（异构协同调度） | 提升 | 来源 |
|---|---|---|---|---|
| DRAM 带宽利用率（解码） | 59–66%（GPU-only, 40–45 GB/s） | ~88%（GPU+NPU, ~60 GB/s） | +37% 绝对值 | [HeteroInfer] |
| 解码吞吐（Llama-8B, 骁龙 8 Gen 3） | 9.3 tok/s（MNN GPU） | 14.0 tok/s | 1.50x | [HeteroInfer] |
| 预填充吞吐（Llama-8B, 256 tok） | 42.4 tok/s（MNN GPU） | 247.9 tok/s | 5.85x | [HeteroInfer] |
| 端到端加速（LongBench, 预填充密集） | 1x（MNN-OpenCL） | 6.02x | 6.02x | [HeteroInfer] |
| Reactive 延迟（Agent 混合负载） | 1x（llama.cpp CPU） | 0.22x（Agent.xpu） | 4.6x 更低 | [Agent.xpu] |
| Proactive 吞吐（后台任务） | 1x（llama.cpp CPU） | 1.6–6.8x（Agent.xpu） | 1.6–6.8x | [Agent.xpu] |
| 同步开销（每层） | 不适用（单 IP） | ~可忽略（sleep-predict + polling） | 消除 vs. 朴素 400 us | [HeteroInfer] |
| NPU 图编译 | 408.4 ms 在线（seq=135） | 0 ms（离线预编译） | 消除 | [HeteroInfer] |

## 7. 一词概括

**Co-schedule**（协同调度）— 推理从单加速器独占转向带宽感知的多 IP 协作：NPU 处理计算密集的预填充，GPU 处理内存密集的解码，压力感知调度器仲裁共享 DRAM 带宽，将利用率从 ~60% 提升至 ~88%，reactive 延迟降低 4.6x。

## 8. 开放问题与注意事项

- **热可持续性** — 已发表基准测试度量的是突发性能；在移动热约束（皮肤温度 < 42 °C）下持续 GPU+NPU 并发执行可能触发 DVFS 降频，侵蚀 1.5–6x 加速。尚无热感知调度策略的提出。
- **多模型与多租户调度** — 现有工作假设单一 LLM；真实 Agent 设备可能并发运行 2+ 模型（视觉 + 语言 + 语音）。跨模型异构调度尚未探索。
- **LPDDR6 的影响** — LPDDR6（预计 2026 年中量产，~14 Gbps/pin，约为 LPDDR5X 带宽的两倍）可能使较小模型的瓶颈回归计算，从而减少双 IP 带宽聚合的收益。
- **操作系统集成** — 用户态调度器（Agent.xpu、HeteroInfer）无法与内核级 GPU/NPU 资源管理（Android NNAPI、厂商 HAL）协调，存在与相机、显示及其他 ML 工作负载的争用风险。
- **骁龙与 Intel 之外的泛化** — HeteroInfer 仅针对骁龙；Agent.xpu 仅针对 Intel Core Ultra。联发科天玑、三星 Exynos 与 Apple Silicon 各有不同的 NPU 架构（脉动阵列尺寸、量化支持、内存映射均不同）。可移植性尚未验证。
- **能效** — 更低延迟不等于更低能耗；双 IP 执行可能因同步开销和有源空闲态漏电流而增加总能耗。尚无已发表的 Joules/token 对比数据。

## 9. 参考文献

1. **HeteroInfer** — Chen et al., 2025. "Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference." ACM SOSP 2025. arxiv 2501.14794. URL: https://dl.acm.org/doi/10.1145/3731569.3764808
2. **Agent.xpu** — Authors, 2025. "Agent.xpu: Efficient Scheduling of Agentic LLM Workloads on Heterogeneous SoC." arxiv 2506.24045. URL: https://arxiv.org/abs/2506.24045
3. **mllm-NPU** — Xu et al., 2025. "Fast On-device LLM Inference with NPUs." ACM ASPLOS 2025. URL: https://dl.acm.org/doi/10.1145/3669940.3707239
4. **PowerInfer-2** — Authors, 2024. "PowerInfer-2: Fast Large Language Model Inference on a Smartphone." arxiv 2406.06282. URL: https://arxiv.org/abs/2406.06282
5. **Qualcomm Snapdragon 8 Gen 3** — Qualcomm, 2024. 产品简介. URL: https://www.qualcomm.com/smartphones/products/8-series/snapdragon-8-gen-3-mobile-platform
6. **Intel Core Ultra** — Intel, 2024. "Intel Core Ultra Processors." URL: https://www.intel.com/content/www/us/en/products/details/processors/core-ultra.html
7. **Samsung LPDDR5X** — Samsung Semiconductor, 2024. "Samsung Develops Industry's Fastest 10.7Gbps LPDDR5X DRAM." URL: https://semiconductor.samsung.com/news-events/news/samsung-develops-industrys-fastest-gbps--lpddr5x-dram-optimized-for-ai-applications/
8. **HeRo** — Authors, 2026. "HeRo: Adaptive Orchestration of Agentic RAG on Heterogeneous Mobile SoC." arxiv 2603.01661. URL: https://arxiv.org/abs/2603.01661
9. **ShadowNPU** — Authors, 2025. "ShadowNPU: System and Algorithm Co-design for NPU-Centric On-Device LLM Inference." arxiv 2508.16703. URL: https://arxiv.org/abs/2508.16703
10. **RooflineBench** — Authors, 2026. "RooflineBench: A Benchmarking Framework for On-Device LLMs via Roofline Analysis." arxiv 2602.11506. URL: https://arxiv.org/abs/2602.11506

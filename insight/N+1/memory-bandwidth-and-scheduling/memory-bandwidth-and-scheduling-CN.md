# 端侧 AI 推理的内存带宽：从窄管独占到宽管打满

> 本文围绕端侧 LLM 推理的**内存带宽瓶颈**，梳理两个互补方向：**带宽供给侧**——DRAM 标准从 LPDDR5（6.4 Gbps）演进到 LPDDR5X（10.7 Gbps、32 GB 封装、负载自适应功耗），把物理带宽做大；**带宽利用侧**——推理引擎从单加速器独占演进到 CPU/GPU/NPU 异构协同调度，把可用带宽用满。*原始方案* = LPDDR5 窄管 + 单 IP 独占（带宽不够，也用不满）；*演进方案* = LPDDR5X 宽管 + 带宽感知多 IP 协同（既加宽，又打满）。资料覆盖 JEDEC 标准、厂商数据（Samsung、SK Hynix、Micron、Qualcomm、Intel、MediaTek）与 2023–2026 学界工作（SOSP'25、ASPLOS'25、arxiv）。

## 1. 范围与方法

**领域界定。** 资源受限终端（手机、平板、笔记本、边缘板卡）上大语言模型推理的**内存带宽**问题，分两个面：

- **供给面**——低功耗移动 DRAM（LPDDR5/5X）作为主存能提供多少带宽、容量和能效；
- **利用面**——统一内存 SoC 上跨异构计算 IP（CPU、GPU、NPU）怎么调度，才能把共享 DRAM 总线的带宽真正用满。

两面共享同一个物理瓶颈：自回归解码阶段，每生成一个 token 都要把模型权重完整读一遍，tokens/s 与**有效**内存带宽近似线性相关——有效带宽既受限于 DRAM 能给多少（供给），也受限于计算侧能用多少（利用）。

**「原始」与「演进」的定义。** *原始方案*是窄管 + 独占：LPDDR5 在 6.4 Gbps 下四通道约 51 GB/s、单封装最大 16 GB、固定档位 DVFS；推理跑在单一计算 IP 上（GPU-only 如 MNN/MLC，或 NPU-only 如 llm.npu），其余加速器闲置，单 IP 只能利用约 60% DRAM 总线。*演进方案*是宽管 + 打满：LPDDR5X 在 10.7 Gbps 下四通道约 85.6 GB/s、单封装最高 32 GB、负载自适应功耗调节；推理由带宽感知调度器将预填充（GEMM）与解码（GEMV）分派到 NPU/GPU 并行执行，通过统一物理内存零拷贝共享 KV Cache，总线利用率推到约 88%。

**资料来源。** 约 20 个主要来源，分三类：(a) 异构调度与端侧推理系统——HeteroInfer（SOSP'25）、Agent.xpu、mllm-NPU（ASPLOS'25）、PowerInfer-2、HeRo、ShadowNPU、RooflineBench；(b) 内存标准与器件——JEDEC JESD209-5C，Samsung / Micron / SK Hynix 的 LPDDR5X / LPDDR6 公告，Synopsys / Semi Engineering 行业分析，CD-PIM；(c) 平台与现状报告——Qualcomm Snapdragon、Intel Core Ultra、MediaTek Dimensity、On-Device LLM State of the Union。涵盖同行评审系统论文、开源运行时文档与 SoC/DRAM 厂商数据手册。

## 2. 问题背景

**系统目标。** 在 8–32 GB 共享 DRAM 的手机或边缘 SoC 上本地跑 1B–8B（向 13B–30B 扩展）参数 LLM：交互式查询（reactive）要低延迟（流畅对话需 15–20 tok/s 以上），后台主动任务（proactive：摘要、RAG 索引、Agent 流水线）要高吞吐，同时把内存子系统功耗压在电池设备的热设计功耗内（整机典型 3–8 W）。

**瓶颈在哪——两个方面。**

- *供给不足。* 端侧解码是内存带宽受限型任务：每生成一个 token 要从 DRAM 完整读一次权重矩阵 [CD-PIM]。7B 模型 INT4 权重约 3.5 GB，LPDDR5 四通道约 51.2 GB/s，理论上限约 14 tok/s，实际 60–70% 效率后约 9 tok/s，达不到流畅交互的门槛。LPDDR5 的 16 GB 封装上限扣除 OS/应用（Android 约 4–6 GB）后只剩 10–12 GB，难以同时放下 13B INT4 权重 + KV Cache + 激活值。另外，LPDDR5 的 DVFS 针对突发负载设计，持续高带宽 AI 推理下会热降频。

- *利用不满。* 即便 DRAM 能提供更多带宽，单加速器也吃不下。现代 SoC（骁龙 8 Gen 3、Intel Core Ultra）集成 CPU、移动 GPU、专用 NPU 三类以上 IP，但现有引擎把它们当作互斥选项。LPDDR5X 峰值约 68 GB/s（实测），单 GPU 解码只能利用 40–45 GB/s（59–66%），约 25 GB/s 白白空着 [HeteroInfer]。NPU 擅长固定形状 INT8 GEMM（预填充），但遇到动态形状 GEMV（解码）性能严重下降；GPU 能处理动态形状，但单独也打不满总线。

**原始方案为什么不够了。** 两个问题叠在一起：模型越来越大、上下文越来越长、再加上并发的 reactive/proactive Agent 流，同时撞上「带宽不够」和「带宽用不满」两堵墙。只加宽管子（LPDDR5X）不改调度，单 IP 仍然只能用六成；只改调度不加宽管子，物理上限仍卡在约 51 GB/s。两边必须一起推。

## 3. 具体问题与瓶颈证据

### 供给侧问题（DRAM 能提供多少）

1. **带宽天花板限制 token 生成速率** — LPDDR5 四通道峰值 51.2 GB/s 下，7B INT4 模型理论上限约 14 tok/s、实测约 9 tok/s，低于 15–20 tok/s 的流畅交互门槛 [CD-PIM]。
2. **封装容量限制可部署模型规模** — LPDDR5 单封装最大 16 GB；扣除 OS/应用后仅余 10–12 GB，部署限制在 7B INT4，更强的 13B+ 模型放不下 [Samsung LPDDR5X]。
3. **持续 AI 负载下功耗/热效率差** — DVFS 针对突发型移动场景设计，持续推理使 DRAM 长期处于高带宽态无法降频；连续推理 30–60 秒后热降频使有效带宽再降 20–30% [Semi Engineering]。
4. **多模态带宽需求翻倍** — 视觉-语言模型（如 LLaVA-7B）处理多模态输入时带宽需求约为纯文本的 2 倍，超出 LPDDR5 有效吞吐 [Synopsys]。

### 利用侧问题（计算侧能用多少）

5. **单加速器浪费带宽** — 骁龙 8 Gen 3 上 GPU-only 解码仅利用 68 GB/s 总线的 40–45 GB/s（59–66%）；GPU+NPU 并发可达约 60 GB/s（88%），带宽提升 37% [HeteroInfer]。
6. **NPU 处理不了动态解码形状** — NPU 脉动阵列固定为 32x32，激活维度小于 32 也需要和 32 一样的延迟；batch-1 GEMV 解码正好踩到这个下限，导致 NPU-only 解码比 GPU 还慢 [HeteroInfer]。
7. **GEMV 核在并发下性能恶化，GEMM 核不受影响** — 内存密集的 GEMV（解码）和另一个高带宽核共享总线时延迟明显上升；计算密集的 GEMM（预填充）不受带宽瓶颈限制，并发下仍然高效 [Agent.xpu]。
8. **缺乏流级并发与优先级** — 现有引擎（llama.cpp、MNN、MLC）假设单次推理，没有 reactive 和 proactive 的区分；后台摘要会阻塞交互式查询 [Agent.xpu]。
9. **NPU 图编译太慢** — 骁龙 8 Gen 3 上 seq_len=135 时 NPU 在线图生成耗时 408.4 ms，导致动态形状的 NPU 推理比 GPU-only 更慢 [HeteroInfer]。

### 瓶颈证据

**供给侧（带宽/容量缺口，以 LPDDR5 为基线）**

| 场景 | 所需 | LPDDR5 可提供 | 缺口 | 来源 |
|---|---|---|---|---|
| 7B INT4，20 tok/s 目标 | 约 70 GB/s 有效 | 约 35 GB/s（70% 效率） | −50% | [CD-PIM] |
| 13B INT4 + KV Cache (8K ctx) | 约 8.5 GB 容量 | 10–12 GB 可用（16 GB 封装） | 余量极小 | [Samsung LPDDR5X] |
| 持续推理 60 秒 | 约 51 GB/s 持续 | 约 36 GB/s（热降频后） | −30% | [Semi Engineering] |
| 多模态流水线（视觉+LLM） | 约 80 GB/s 突发 | 约 51 GB/s 峰值 | −36% | [Synopsys] |
| 4 个并发 Agent，各 7B | 约 14 GB 容量 | 10–12 GB 可用 | 第 3 个 Agent OOM | [On-Device LLM Survey] |

**利用侧（单 IP vs 异构，骁龙 8 Gen 3 / Intel Core Ultra）**

| 场景 | 指标 | 单 IP | 异构 | 差距 | 来源 |
|---|---|---|---|---|---|
| 解码, Llama-8B | DRAM 带宽利用 | 40–45 GB/s (GPU) | 约 60 GB/s (GPU+NPU) | +37% BW | [HeteroInfer] |
| 解码, Llama-8B | 吞吐 | 9.3 tok/s (MNN GPU) | 14.0 tok/s (HeteroInfer) | 1.50x | [HeteroInfer] |
| 预填充 256tok, Llama-8B | 吞吐 | 42.4 tok/s (MNN GPU) | 247.9 tok/s (HeteroInfer) | 5.85x | [HeteroInfer] |
| 混合 Agent 负载 | Reactive 延迟 | 1x (llama.cpp CPU) | 0.22x (Agent.xpu) | 4.6x 更低 | [Agent.xpu] |
| NPU 在线图生成, seq=135 | 编译延迟 | 408.4 ms | 0 ms（离线预编译） | 消除 | [HeteroInfer] |

## 4. 架构：原始方案 vs 演进方案

![内存带宽：窄管+独占 vs 宽管+榨满 架构图](assets/memory-bandwidth-and-scheduling-arch.svg)

*图：原始方案与演进方案的架构对照（详细文本版见下方 ASCII 图）。*

**原始方案 — 窄管（LPDDR5）+ 单加速器独占**

```
    用户请求
         |
         v
    +-----------+        +------------------+
    |  运行时    |        | LPDDR5 内存子系统 |
    | (MNN/MLC/  |<------>| 4通道x16, 6.4Gbps |
    |  llm.npu)  | 权重/  | 峰值 51.2 GB/s    |
    +-----------+ KV     | 最大 16 GB        |
         |               | 固定档位 DVFS     |
         | 所有层 → 同一 IP +----------------+
         v
    +-------------------+
    |  单一加速器        |   其余 IP 闲置
    |  (GPU 或 NPU)     |   (NPU/CPU 或 GPU/CPU)
    |  预填充: GEMM     |
    |  解码:   GEMV     |
    +-------------------+
    [带宽供给: 51 GB/s 物理上限]
    [带宽利用: 59-66% (单 IP)]
    [无抢占, 无优先级; 持续负载热降频]
```

*原始方案：物理带宽上限约 51 GB/s，单 IP 又只用其中六成；持续 AI 负载下 DVFS/热降频还会进一步压缩。*

**演进方案 — 宽管（LPDDR5X）+ 异构多 IP 协同打满带宽**

```
    用户请求 ───────────────── 后台任务
    (reactive, 低延迟)        (proactive, 高吞吐)
         |                            |
         v                            v
    +----------------------------------------------+
    | * 流感知调度器                                  |
    |   - * 优先级队列 (reactive > proactive)        |
    |   - * 核级抢占 (<100 ms)                       |
    |   - * 带宽压力监控 (Pmem)                       |
    +----------------------------------------------+
         |              |                 |
         v              v                 v
    +---------+   +----------+      +-----------+
    |  CPU    |   | * NPU    |      | * GPU     |
    | (离群值) |   | (预填充   |      | (解码     |
    +---------+   |  GEMM)   |      |  GEMV)    |
                  +----------+      +-----------+
                       |  * 张量分区 / 弹性绑定  |
                       v                        v
    +--------------------------------------------------+
    | * LPDDR5X 内存子系统 (统一物理内存, 零拷贝 KV)    |
    |   4通道x16, 10.7 Gbps → 峰值 85.6 GB/s           |
    |   最大 32 GB; 12nm 级; DFE/预加重                 |
    |   * 负载自适应 DVFS / 扩展低功耗间隔 / PASR       |
    +--------------------------------------------------+
         * 带宽感知调度: 低(<0.4) 激进并发 /
           中(0.4-0.7) 选择性配对 / 高(>=0.7) 顺序, reactive 优先
    [带宽供给: 85.6 GB/s (+67%)]
    [带宽利用: ~88%; Reactive 延迟 -4.6x; 能效 +25%]
```

*演进方案：管子加宽（LPDDR5X +67% 带宽、2x 容量、负载自适应功耗），同时异构调度把带宽打满（预填充走 NPU、解码走 GPU、张量分区、压力感知仲裁、核级抢占）。新增/变更部分以 `*` 标记。*

## 5. 演进方案为什么有效，还剩什么没解决

### 为什么有效

**供给侧（把管子做宽）**

- **带宽天花板** — LPDDR5X 在 10.7 Gbps 下四通道达 85.6 GB/s，比 LPDDR5 高 67%；7B INT4 理论解码上限从约 14 升到约 24 tok/s，超过交互门槛。Snapdragon 8 Elite 的 LPDDR5X-9600 控制器实测 84.8 GB/s，片上 18 MB HPM 缓存把有效带宽再提升 38% [Qualcomm Snapdragon 8 Elite]。
- **封装容量** — Samsung 32 GB 单封装 LPDDR5X（8 层堆叠、12nm 级 die）给 13B INT4 权重 + OS + KV Cache + 激活值留出足够空间，无需多芯片就能在端侧部署更大模型 [Samsung LPDDR5X]。
- **能效** — Samsung 报告 12nm 工艺缩放 + 负载自适应功耗调节带来 25% 能效提升；Micron 1-gamma LPDDR5X 在 10.7 Gbps 下功耗降低 20%（最薄 0.61 mm）。单位比特能耗下降，持续高带宽下不容易触发热降频 [Micron 1-gamma LPDDR5X]。
- **高速率信号完整性** — DFE 与发送端预加重在不抬高 I/O 电压（VDDQ 维持 0.5 V）的前提下实现 10.7 Gbps 可靠运行，速度 +67% 而功耗包络不变 [Synopsys]。

**利用侧（把宽管打满）**

- **单加速器浪费带宽** — GPU+NPU 并发把 DRAM 利用率从 59–66% 推到约 88%，直接换来 Llama-8B 1.50x 解码加速 [HeteroInfer]。
- **NPU 处理不了动态解码形状** — 按阶段分工：预填充（GEMM, 静态）走 NPU、解码（GEMV, 动态）走 GPU；HeteroInfer 的激活中心分区把动态序列拆成 NPU 友好的定长块 + GPU 处理余数 [HeteroInfer]。
- **GEMV 并发退化** — Agent.xpu 用三级带宽压力调度实时监控 Pmem，<0.4 激进并发、>=0.7 切顺序，既利用并行又防止解码 GEMV 被拖慢 [Agent.xpu]。
- **缺乏流级并发** — Agent.xpu 引入 <100 ms 粒度核级抢占（算子分块）+ 松弛感知回填，reactive 延迟降 4.6x，proactive 吞吐升 1.6–6.8x [Agent.xpu]。
- **NPU 图编译太慢** — HeteroInfer 的离线分析-求解器在 <20 分钟内预编译所有预期张量形状的 NPU 图，消除 408.4 ms 在线编译开销 [HeteroInfer]。

### 尚未解决的问题

- **持续双 IP 负载下的热节流** — 管子宽了功耗也大了：GPU+NPU 并发拉高芯片温度，在移动热包络（皮肤温度 <42 °C、DVFS 降频）下的持续性能还没有实测数据，实际可能比基准低。LPDDR5X 的能效改善能不能抵消 10.7 Gbps 的更高绝对功耗，在轻薄/折叠机身上还没有验证。
- **物理带宽仍然偏低** — LPDDR5X 约 86 GB/s 比桌面/独显级高带宽内存低一个数量级左右；端侧以交互速度跑 70B 仍不可行。出路可能在近存计算——CD-PIM 提出基于 LPDDR5 的存内计算有望带来 10–100x 带宽提升 [CD-PIM]。
- **跨 SoC 厂商可移植性** — HeteroInfer 的离线分析器需要为每款 SoC 重新做性能特征化（骁龙 vs 天玑 vs Exynos），Agent.xpu 目前只支持 Intel；没有厂商中立的异构推理 API。LPDDR5X 沿用 LPDDR5 的读写命令集，存储端无法区分 AI 负载模式（顺序权重流式读 vs 随机 KV 访问）。
- **NPU INT8 量化的精度代价** — NPU 路径通常要求 INT8 或更低精度，相对 FP16 GPU 推理的精度差异因模型而异，在多种任务（推理、代码、多语言）上还没有系统评测。
- **OS 级资源仲裁** — 异构调度器跑在用户态，感知不到其他竞争 GPU/NPU 的应用（游戏、相机 ISP、后台 ML），和 Android NNAPI / iOS CoreML 的集成还没有做。
- **功耗节省不叠加** — KV Cache 卸载到 Flash（KVSwap、KVNAND）时，低功耗间隔省下的 DRAM 功耗被持续 Flash I/O 部分抵消；双 IP 执行也可能因同步开销和有源空闲漏电增加总能耗。目前没有公开的系统级 Joules/token 数据。
- **LPDDR6 临近** — LPDDR6（预计 2026 年中量产，约 14 Gbps/pin、约 2x LPDDR5X 带宽、再省 20% 功耗）可能使较小模型的瓶颈回到计算侧，削弱双 IP 带宽聚合的意义，同时给 2026–2027 产品线带来标准共存的采购风险 [SK Hynix LPDDR6; Synopsys]。

## 6. 对比表

| 维度 | 原始（LPDDR5 + 单 IP） | 演进（LPDDR5X + 异构协同） | 提升 | 来源 |
|---|---|---|---|---|
| 峰值数据速率（每引脚） | 6.4 Gbps | 10.7 Gbps | +67% | [JEDEC JESD209-5C] |
| 四通道峰值带宽 | 51.2 GB/s | 85.6 GB/s | +67% | [JEDEC JESD209-5C] |
| 最大单封装容量 | 16 GB | 32 GB | +100%（2x） | [Samsung LPDDR5X] |
| 功耗效率（对比前代） | 基准 | +25%（Samsung）/+20%（Micron） | 单位比特能耗 −20~25% | [Samsung; Micron 1-gamma] |
| 功耗管理 | 固定档位 DVFS、深度睡眠 | 负载自适应 DVFS、扩展低功耗间隔、PASR | AI 感知功耗门控 | [Samsung LPDDR5X] |
| DRAM 带宽利用率（解码） | 59–66%（GPU-only, 40–45 GB/s） | 约 88%（GPU+NPU, 约 60 GB/s） | +37% 绝对值 | [HeteroInfer] |
| 解码吞吐（Llama-8B, 骁龙 8 Gen 3） | 9.3 tok/s（MNN GPU） | 14.0 tok/s | 1.50x | [HeteroInfer] |
| 预填充吞吐（Llama-8B, 256 tok） | 42.4 tok/s（MNN GPU） | 247.9 tok/s | 5.85x | [HeteroInfer] |
| 端到端加速（LongBench, 预填充密集） | 1x（MNN-OpenCL） | 6.02x | 6.02x | [HeteroInfer] |
| Reactive 延迟（Agent 混合负载） | 1x（llama.cpp CPU） | 0.22x（Agent.xpu） | 4.6x 更低 | [Agent.xpu] |
| Proactive 吞吐（后台任务） | 1x（llama.cpp CPU） | 1.6–6.8x（Agent.xpu） | 1.6–6.8x | [Agent.xpu] |
| 7B INT4 解码吞吐（理论, 仅供给） | 约 14 tok/s | 约 24 tok/s | +71% | 据带宽计算 |
| NPU 图编译 | 408.4 ms 在线（seq=135） | 0 ms（离线预编译） | 消除 | [HeteroInfer] |

## 7. 一词概括

**打满**（Saturate）— 端侧推理从两端攻克内存带宽瓶颈：供给侧把管子做宽（LPDDR5X 带宽 +67%、容量 2x、能效 +25%），利用侧把宽管打满（异构协同把 DRAM 利用率从约 60% 推到约 88%，reactive 延迟降 4.6x）。两者缺一不可——只加宽不调度，单 IP 仍只用六成；只调度不加宽，物理上限仍卡在约 51 GB/s。

## 8. 开放问题与注意事项

- **真实 AI 推理的能耗与热可持续性** — 厂商公布的效率数字（20–25%）和论文基准（1.5–6x 加速）多为突发或营销口径；在量产手机的持续 LLM 推理与移动热约束（皮肤温度 <42 °C）下，每 token 能耗和持续吞吐还没有独立测量，DVFS 降频可能侵蚀加速效果。
- **争用下的有效带宽** — 旗舰 SoC 的 LPDDR5X 带宽由 CPU/GPU/NPU/ISP/显示共享；公布峰值假设独占，OS 与显示争用后实际 AI 推理带宽可能只有峰值的 50–70%，而且和用户态异构调度器的配合还没有系统测量。
- **多模型与多租户调度** — 现有工作多假设单一 LLM；真实 Agent 设备可能同时跑 2+ 模型（视觉+语言+语音），跨模型的异构调度还没有人做。
- **容量与成本** — 32 GB 封装虽已量产，2025 年多数旗舰仍配 12–16 GB；24–32 GB 能否成为标配取决于端侧 AI 能否证明每 8 GB 约 $15–25 的 BOM 增加是值得的。模型向 30B+ 扩展后，32 GB 在多 Agent 场景下仍可能不够。
- **骁龙/Intel 之外的泛化** — HeteroInfer 只针对骁龙、Agent.xpu 只针对 Intel Core Ultra；天玑、Exynos、Apple Silicon 的 NPU 架构（脉动阵列尺寸、量化支持、内存映射）各不相同，可移植性未验证。
- **架构级替代的时间窗口** — PIM（CD-PIM）和 LPDDR6 都可能在 LPDDR5X 生命周期结束前改变格局；本文的「宽管+打满」是为端侧 AI 争取 2–3 年窗口期的过渡方案，不是终局。

## 9. 参考文献

### 异构调度与端侧推理系统

1. **HeteroInfer** — Chen et al., 2025. "Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference." ACM SOSP 2025 / arxiv 2501.14794. URL: https://dl.acm.org/doi/10.1145/3731569.3764808
2. **Agent.xpu** — Authors, 2025. "Agent.xpu: Efficient Scheduling of Agentic LLM Workloads on Heterogeneous SoC." arxiv 2506.24045. URL: https://arxiv.org/abs/2506.24045
3. **mllm-NPU** — Xu et al., 2025. "Fast On-device LLM Inference with NPUs." ACM ASPLOS 2025. URL: https://dl.acm.org/doi/10.1145/3669940.3707239
4. **PowerInfer-2** — Authors, 2024. "PowerInfer-2: Fast Large Language Model Inference on a Smartphone." arxiv 2406.06282. URL: https://arxiv.org/abs/2406.06282
5. **HeRo** — Authors, 2026. "HeRo: Adaptive Orchestration of Agentic RAG on Heterogeneous Mobile SoC." arxiv 2603.01661. URL: https://arxiv.org/abs/2603.01661
6. **ShadowNPU** — Authors, 2025. "ShadowNPU: System and Algorithm Co-design for NPU-Centric On-Device LLM Inference." arxiv 2508.16703. URL: https://arxiv.org/abs/2508.16703
7. **RooflineBench** — Authors, 2026. "RooflineBench: A Benchmarking Framework for On-Device LLMs via Roofline Analysis." arxiv 2602.11506. URL: https://arxiv.org/abs/2602.11506

### 内存标准与器件

8. **JEDEC JESD209-5C** — JEDEC 固态技术协会, 2023. "Low Power Double Data Rate (LPDDR) 5/5X." URL: https://www.jedec.org/standards-documents/docs/jesd209-5c
9. **Samsung 10.7 Gbps LPDDR5X** — Samsung 半导体, 2024-04. "Samsung Develops Industry's Fastest 10.7Gbps LPDDR5X DRAM, Optimized for AI Applications." URL: https://semiconductor.samsung.com/news-events/news/samsung-develops-industrys-fastest-gbps--lpddr5x-dram-optimized-for-ai-applications/
10. **Samsung Thinnest LPDDR5X** — Samsung 半导体, 2024-08. "Samsung Begins Mass Production of Industry's Thinnest LPDDR5X DRAM Packages for On-Device AI." URL: https://semiconductor.samsung.com/news-events/news/samsung-begins-mass-production-of-industrys-thinnest-lpddr5x-dram-packages-for-on-device-ai/
11. **Samsung Automotive LPDDR5X** — Samsung 半导体, 2024. "Samsung's 12nm-Class Automotive LPDDR5X." URL: https://semiconductor.samsung.com/news-events/tech-blog/samsungs-12nm-class-automotive-lpddr5x-dram-for-safety-critical-centralized-automotive-systems/
12. **Samsung MediaTek Validation** — Samsung 半导体, 2024. "Samsung Completes Validation of Industry's Fastest LPDDR5X for Use with MediaTek's Flagship Mobile Platform." URL: https://semiconductor.samsung.com/news-events/news/samsung-completes-validation-of-industrys-fastest-lpddr5x-for-use-with-mediateks-flagship-mobile-platform/
13. **Micron 1-gamma LPDDR5X** — Micron 科技, 2025. "Micron Ships World's First 1-Gamma-Based LPDDR5X Enabling Rich On-Device AI." URL: https://www.stocktitan.net/news/MU/micron-ships-world-s-first-1-1-gamma-based-lpddr5x-enabling-rich-bdr3skeatdxp.html
14. **Micron LPDDR5X 产品页** — Micron 科技. "LPDDR5X: Memory performance that pushes the limits of what's possible." URL: https://www.micron.com/about/blog/memory/dram/lpddr5x-memory-performance-pushes-the-limits-of-whats-possible
15. **SK Hynix LPDDR6** — SK Hynix, 2025. "SK hynix Presents Leading AI Memory at COMPUTEX TAIPEI 2025." URL: https://news.skhynix.com/sk-hynix-showcases-hbm4-next-gen-ai-memory-at-computex-taipei-2025/
16. **CD-PIM** — 作者, 2025. "CD-PIM: A High-Bandwidth and Compute-Efficient LPDDR5-Based PIM for Low-Batch LLM Acceleration on Edge-Device." arxiv 2601.12298. URL: https://arxiv.org/pdf/2601.12298
17. **Synopsys LPDDR5X Specification** — Synopsys, 2024. "LPDDR5X Explained: Speed and Specification." URL: https://www.synopsys.com/blogs/chip-design/lpddr5x-specification-memory-design.html
18. **Synopsys LPDDR6 vs LPDDR5X** — Synopsys, 2025. "LPDDR6 vs LPDDR5X and LPDDR5: Key Differences and Benefits." URL: https://www.synopsys.com/blogs/chip-design/lpddr6-vs-lpddr5x-lpddr5-differences.html
19. **Semi Engineering LPDDR5X** — Semiconductor Engineering, 2024. "LPDDR5X: High Bandwidth, Power Efficient Performance For Mobile & Beyond." URL: https://semiengineering.com/lpddr5x-high-bandwidth-power-efficient-performance-for-mobile-beyond/

### 平台与现状报告

20. **Qualcomm Snapdragon 8 Gen 3** — Qualcomm, 2024. 产品简介. URL: https://www.qualcomm.com/smartphones/products/8-series/snapdragon-8-gen-3-mobile-platform
21. **Qualcomm Snapdragon 8 Elite** — Qualcomm, 2025. "Snapdragon 8 Elite Gen 5 Product Brief." URL: https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf
22. **Intel Core Ultra** — Intel, 2024. "Intel Core Ultra Processors." URL: https://www.intel.com/content/www/us/en/products/details/processors/core-ultra.html
23. **On-Device LLM Survey** — V. Chandra et al., 2026. "On-Device LLMs: State of the Union." URL: https://v-chandra.github.io/on-device-llms/

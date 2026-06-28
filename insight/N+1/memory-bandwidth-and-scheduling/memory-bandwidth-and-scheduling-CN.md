# 端侧 AI 推理的内存带宽：从「窄管+独占」到「宽管+榨满」

> 本文把端侧 LLM 推理的**内存带宽墙**作为一条主线，串起两个互补的攻关方向：**带宽供给侧**——DRAM 标准从 LPDDR5（6.4 Gbps）演进到 LPDDR5X（10.7 Gbps、32 GB 封装、负载自适应功耗）把「管子」做宽；**带宽利用侧**——推理引擎从单加速器独占演进到 CPU/GPU/NPU 异构协同调度把宽管「榨满」。*原始方案* = LPDDR5 的窄管 + 单 IP 独占（带宽既不够、又用不满）；*演进方案* = LPDDR5X 的宽管 + 带宽感知的多 IP 协同（既加宽、又打满）。覆盖 JEDEC 标准、厂商资料（Samsung、SK Hynix、Micron、Qualcomm、Intel、MediaTek）与 2023–2026 学界进展（SOSP'25、ASPLOS'25、arxiv）。

## 1. 范围与方法

**领域界定。** 资源受限终端（手机、平板、笔记本、边缘板卡）上大语言模型推理的**内存带宽**问题，包含两个不可分割的面：

- **供给面**——低功耗移动 DRAM（LPDDR5/5X）作为主存子系统提供多少带宽、容量与能效；
- **利用面**——统一内存 SoC 上跨异构计算 IP（CPU、GPU、NPU）如何调度，才能把共享 DRAM 总线的带宽真正用满。

两面共享同一个物理瓶颈：自回归解码阶段，每生成一个 token 都要把模型权重完整读一遍，因此 tokens/s 与**有效**内存带宽近似线性相关——而「有效带宽」既受限于 DRAM 能提供多少（供给），也受限于计算侧能榨出多少（利用）。

**「原始」与「演进」的含义。** *原始方案*是「窄管 + 独占」：LPDDR5 在 6.4 Gbps 下四通道约 51 GB/s、单封装最大 16 GB、固定档位 DVFS；推理完全跑在单一计算 IP 上（GPU-only 如 MNN/MLC，或 NPU-only 如 llm.npu），其余加速器闲置，单 IP 只能利用约 60% 的 DRAM 总线。*演进方案*是「宽管 + 榨满」：LPDDR5X 在 10.7 Gbps 下四通道约 85.6 GB/s、单封装最高 32 GB、负载自适应功耗调节；推理由带宽感知调度器把预填充（GEMM）与解码（GEMV）分派到 NPU/GPU 并行执行，经统一物理内存零拷贝共享 KV Cache，把总线利用率推到约 88%。

**资料来源。** 约 20 个主要来源，分三族：(a) 异构调度与端侧推理系统——HeteroInfer（SOSP'25）、Agent.xpu、mllm-NPU（ASPLOS'25）、PowerInfer-2、HeRo、ShadowNPU、RooflineBench；(b) 内存标准与器件——JEDEC JESD209-5C，Samsung / Micron / SK Hynix 的 LPDDR5X / LPDDR6 公告，Synopsys / Semi Engineering 行业分析，CD-PIM；(c) 平台与现状报告——Qualcomm Snapdragon、Intel Core Ultra、MediaTek Dimensity、On-Device LLM State of the Union。涵盖同行评审系统论文、开源运行时文档与 SoC/DRAM 厂商数据手册。

## 2. 问题背景

**系统需要做什么。** 在 8–32 GB 共享 DRAM 的手机或边缘 SoC 上本地运行 1B–8B（并向 13B–30B 扩展）参数 LLM：为交互式查询（reactive）提供低延迟响应（流畅对话需 15–20 tok/s 以上），为后台主动任务（proactive：摘要、RAG 索引、Agent 流水线）提供高吞吐，同时把内存子系统功耗压在电池设备的热设计功耗内（整机典型 3–8 W）。

**为什么这个领域变难了——瓶颈的两张面孔。**

- *供给不足。* 端侧解码是内存带宽受限型任务：生成每个 token 需从 DRAM 完整读一次权重矩阵 [CD-PIM]。7B 模型 INT4 权重约 3.5 GB，按 LPDDR5 四通道约 51.2 GB/s 计算，理论上限仅约 14 tok/s，实际 60–70% 效率后约 9 tok/s，低于流畅交互阈值。LPDDR5 的 16 GB 封装上限在扣除 OS/应用（Android 约 4–6 GB）后只剩 10–12 GB，难以同时容纳 13B INT4 权重 + KV Cache + 激活值。其针对突发负载设计的 DVFS 在持续高带宽 AI 推理下还会热降频。

- *利用不满。* 即便 DRAM 能提供更多，单加速器也吃不下。现代 SoC（骁龙 8 Gen 3、Intel Core Ultra）集成 CPU、移动 GPU、专用 NPU 三类以上 IP，但现有引擎把它们当作互斥目标。LPDDR5X 峰值约 68 GB/s（实测），而单 GPU 解码只能利用 40–45 GB/s（59–66%），约 25 GB/s 闲置 [HeteroInfer]。NPU 擅长固定形状 INT8 GEMM（预填充），但在动态形状 GEMV（解码）上严重退化；GPU 能处理动态形状却单独打不满总线。

**为什么原始方案不再够用。** 两张面孔叠加：把更大的模型塞进更长的上下文、再加上并发的 reactive/proactive Agent 流，会同时撞上「带宽不够」和「带宽用不满」两堵墙。只加宽管子（LPDDR5X）而不改调度，单 IP 仍只能用六成；只改调度而不加宽管子，物理上限仍卡在约 51 GB/s。两者必须合攻。

## 3. 具体问题与瓶颈证据

### 供给侧问题（DRAM 能提供多少）

1. **带宽天花板限制 token 生成速率** — LPDDR5 四通道峰值 51.2 GB/s 下，7B INT4 模型理论上限约 14 tok/s、实测约 9 tok/s，低于 15–20 tok/s 的流畅交互阈值 [CD-PIM]。
2. **封装容量限制可部署的模型规模** — LPDDR5 单封装最大 16 GB；扣除 OS/应用后仅余 10–12 GB，实际把部署限制在 7B INT4，排除推理能力更强的 13B+ 模型 [Samsung LPDDR5X]。
3. **持续 AI 负载下的功耗/热低效** — DVFS 针对突发型移动使用设计，持续推理使 DRAM 长时间处于高带宽态无法进入低功耗；连续推理 30–60 秒后热降频使有效带宽再降 20–30% [Semi Engineering]。
4. **多模态倍增带宽需求** — 视觉-语言模型（如 LLaVA-7B）多模态输入处理时带宽需求约为纯文本的 2 倍，超出 LPDDR5 有效吞吐 [Synopsys]。

### 利用侧问题（计算侧能榨出多少）

5. **单加速器浪费带宽** — 骁龙 8 Gen 3 上 GPU-only 解码仅利用 68 GB/s 总线的 40–45 GB/s（59–66%）；GPU+NPU 并发可达约 60 GB/s（88%），带宽提升 37% [HeteroInfer]。
6. **NPU 无法高效处理动态解码形状** — NPU 脉动阵列固定为 32×32，任何小于 32 的激活维度都产生与 32 同样的延迟；batch-1 GEMV 解码触发此「阶梯」下限，使 NPU-only 解码慢于 GPU [HeteroInfer]。
7. **GEMV 核在并发下退化，GEMM 核可容忍** — 内存密集的 GEMV（解码）与另一高带宽核共享总线时延迟显著恶化；计算密集的 GEMM（预填充）不受带宽限制，并发下仍高效 [Agent.xpu]。
8. **无流级并发与优先级** — 现有引擎（llama.cpp、MNN、MLC）假设单次推理，无法区分 reactive 与 proactive；后台摘要会阻塞交互式查询 [Agent.xpu]。
9. **NPU 图编译对动态输入过慢** — 骁龙 8 Gen 3 上 seq_len=135 时 NPU 在线图生成耗时 408.4 ms，使朴素动态形状 NPU 推理比 GPU-only 更慢 [HeteroInfer]。

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
| 解码, Llama-8B | 吞吐 | 9.3 tok/s (MNN GPU) | 14.0 tok/s (HeteroInfer) | 1.50× | [HeteroInfer] |
| 预填充 256tok, Llama-8B | 吞吐 | 42.4 tok/s (MNN GPU) | 247.9 tok/s (HeteroInfer) | 5.85× | [HeteroInfer] |
| 混合 Agent 负载 | Reactive 延迟 | 1× (llama.cpp CPU) | 0.22× (Agent.xpu) | 4.6× 更低 | [Agent.xpu] |
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

*原始方案：物理带宽卡在约 51 GB/s，单 IP 又只用其中六成；持续 AI 负载下还要被 DVFS/热降频进一步侵蚀。*

**演进方案 — 宽管（LPDDR5X）+ 异构多 IP 协同把带宽榨满**

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

*演进方案：管子加宽（LPDDR5X +67% 带宽、2× 容量、负载自适应功耗），同时被异构调度榨满（预填充→NPU、解码→GPU、张量分区、压力感知仲裁、核级抢占）。新增/变更部分以 `*` 标记。*

## 5. 演进方案为何有效，以及尚未解决什么

### 为何有效

**供给侧（把管子做宽）**

- **带宽天花板** — LPDDR5X 在 10.7 Gbps 下四通道达 85.6 GB/s，较 LPDDR5 提升 67%；7B INT4 理论解码上限从约 14 升到约 24 tok/s，舒适越过交互阈值。Snapdragon 8 Elite 的 LPDDR5X-9600 控制器实现 84.8 GB/s，片上 18 MB HPM 缓存再把有效带宽提升 38% [Qualcomm Snapdragon 8 Elite]。
- **封装容量** — Samsung 32 GB 单封装 LPDDR5X（8 层堆叠、12nm 级 die）为 13B INT4 权重 + OS + KV Cache + 激活值留足余量，无需多芯片即可端侧部署更高质量模型 [Samsung LPDDR5X]。
- **能效** — Samsung 报告通过 12nm 工艺缩放 + 负载自适应功耗调节实现 25% 能效提升；Micron 1-gamma LPDDR5X 在 10.7 Gbps 下实现 20% 功耗降低（最薄 0.61 mm）。更低单位比特能耗让持续高带宽不再触发热降频 [Micron 1-gamma LPDDR5X]。
- **更高速率下的信号完整性** — DFE 与发送端预加重在不抬高 I/O 电压（VDDQ 维持 0.5 V）的前提下实现 10.7 Gbps 可靠运行，速度 +67% 而功耗包络不变 [Synopsys]。

**利用侧（把宽管榨满）**

- **单加速器浪费带宽** — GPU+NPU 并发把 DRAM 利用率从 59–66% 推到约 88%，直接转化为 Llama-8B 1.50× 解码加速 [HeteroInfer]。
- **NPU 无法处理动态解码形状** — 阶段感知调度把预填充（GEMM, 静态）路由至 NPU、解码（GEMV, 动态）路由至 GPU；HeteroInfer 的激活中心分区进一步把动态序列拆成 NPU 友好的定长块 + GPU 处理的余数 [HeteroInfer]。
- **GEMV 并发退化** — Agent.xpu 三级带宽压力调度实时监控 Pmem，<0.4 激进并发、>=0.7 切顺序，在用并行的同时防止解码 GEMV 退化 [Agent.xpu]。
- **无流级并发** — Agent.xpu 引入 <100 ms 粒度核级抢占（算子分块）+ 松弛感知回填，reactive 延迟降 4.6×，proactive 吞吐升 1.6–6.8× [Agent.xpu]。
- **NPU 图编译过慢** — HeteroInfer 的离线分析-求解器协作在 <20 分钟内预编译所有预期张量形状的 NPU 图，消除 408.4 ms 在线编译开销 [HeteroInfer]。

### 尚未解决的问题

- **持续双 IP 负载下的热节流** — 加宽管子也加大了功耗：GPU+NPU 并发提升芯片温度，移动热包络（皮肤温度 <42 °C、DVFS 降频）下的持续性能尚无测量，实际可能低于基准。LPDDR5X 的能效改善能否抵消 10.7 Gbps 的更高绝对功耗，在轻薄/折叠机身尚未验证。
- **物理带宽仍偏低** — LPDDR5X 约 86 GB/s 仍比桌面/独显级高带宽内存低约一个数量级；端侧以交互速度跑 70B 仍不可行，出路在端侧友好的近存计算——CD-PIM 已提出基于 LPDDR5 的存内计算可能带来 10–100× 带宽提升 [CD-PIM]。
- **跨 SoC 厂商可移植性** — HeteroInfer 的离线分析器需为每款 SoC 重新特征化（骁龙 vs 天玑 vs Exynos），Agent.xpu 目前仅支持 Intel；不存在厂商中立的异构推理 API。LPDDR5X 也沿用与 LPDDR5 相同的读写命令集，存储端无法感知 AI 负载模式（顺序权重流式读 vs 随机 KV 访问）。
- **NPU INT8 量化的精度影响** — NPU 路径通常要求 INT8 或更低精度，相对 FP16 GPU 推理的精度差异取决于模型，未在多样任务（推理、代码、多语言）上系统评测。
- **OS 级资源仲裁** — 异构调度器跑在用户态，无法感知竞争 GPU/NPU 的其他应用（游戏、相机 ISP、后台 ML），与 Android NNAPI / iOS CoreML 的集成尚未实现。
- **功耗节省不叠加** — KV Cache 卸载到 Flash（KVSwap、KVNAND）时，低功耗间隔带来的 DRAM 节省被持续 Flash I/O 部分抵消；双 IP 执行也可能因同步开销与有源空闲漏电增加总能耗。尚无公开的系统级 Joules/token 数据。
- **LPDDR6 临近** — LPDDR6（预计 2026 年中量产，约 14 Gbps/pin、约 2× LPDDR5X 带宽、再省 20% 功耗）可能使较小模型瓶颈回归计算，从而削弱双 IP 带宽聚合的收益，同时给瞄准 2026–2027 的厂商带来标准共存的采购不确定性 [SK Hynix LPDDR6; Synopsys]。

## 6. 对比表

| 维度 | 原始（LPDDR5 + 单 IP） | 演进（LPDDR5X + 异构协同） | 提升 | 来源 |
|---|---|---|---|---|
| 峰值数据速率（每引脚） | 6.4 Gbps | 10.7 Gbps | +67% | [JEDEC JESD209-5C] |
| 四通道峰值带宽 | 51.2 GB/s | 85.6 GB/s | +67% | [JEDEC JESD209-5C] |
| 最大单封装容量 | 16 GB | 32 GB | +100%（2×） | [Samsung LPDDR5X] |
| 功耗效率（对比前代） | 基准 | +25%（Samsung）/+20%（Micron） | 单位比特能耗 −20~25% | [Samsung; Micron 1-gamma] |
| 功耗管理 | 固定档位 DVFS、深度睡眠 | 负载自适应 DVFS、扩展低功耗间隔、PASR | AI 感知功耗门控 | [Samsung LPDDR5X] |
| DRAM 带宽利用率（解码） | 59–66%（GPU-only, 40–45 GB/s） | 约 88%（GPU+NPU, 约 60 GB/s） | +37% 绝对值 | [HeteroInfer] |
| 解码吞吐（Llama-8B, 骁龙 8 Gen 3） | 9.3 tok/s（MNN GPU） | 14.0 tok/s | 1.50× | [HeteroInfer] |
| 预填充吞吐（Llama-8B, 256 tok） | 42.4 tok/s（MNN GPU） | 247.9 tok/s | 5.85× | [HeteroInfer] |
| 端到端加速（LongBench, 预填充密集） | 1×（MNN-OpenCL） | 6.02× | 6.02× | [HeteroInfer] |
| Reactive 延迟（Agent 混合负载） | 1×（llama.cpp CPU） | 0.22×（Agent.xpu） | 4.6× 更低 | [Agent.xpu] |
| Proactive 吞吐（后台任务） | 1×（llama.cpp CPU） | 1.6–6.8×（Agent.xpu） | 1.6–6.8× | [Agent.xpu] |
| 7B INT4 解码吞吐（理论, 仅供给） | 约 14 tok/s | 约 24 tok/s | +71% | 据带宽计算 |
| NPU 图编译 | 408.4 ms 在线（seq=135） | 0 ms（离线预编译） | 消除 | [HeteroInfer] |

## 7. 一词概括

**榨满**（Saturate）— 端侧推理同时从两端攻克内存带宽墙：供给侧把管子做宽（LPDDR5X 带宽 +67%、容量 2×、能效 +25%），利用侧把宽管榨满（异构协同把 DRAM 利用率从约 60% 推到约 88%，reactive 延迟降 4.6×）。两者缺一不可——只加宽不调度，单 IP 仍只用六成；只调度不加宽，物理上限仍卡在约 51 GB/s。

## 8. 开放问题与注意事项

- **真实 AI 推理的能耗与热可持续性** — 厂商公布的效率（20–25%）与论文基准（1.5–6× 加速）多为突发/营销口径；在量产手机的持续 LLM 推理与移动热约束（皮肤温度 <42 °C）下，每 token 能耗与持续吞吐尚无独立测量，DVFS 降频可能侵蚀加速。
- **争用下的有效带宽** — 旗舰 SoC 的 LPDDR5X 带宽由 CPU/GPU/NPU/ISP/显示共享；公布峰值假设独占，OS 与显示争用后实际 AI 推理带宽可能仅为峰值 50–70%，且与用户态异构调度器的协同尚未系统测量。
- **多模型与多租户调度** — 现有工作多假设单一 LLM；真实 Agent 设备可能并发跑 2+ 模型（视觉+语言+语音），跨模型异构调度尚未探索。
- **容量与成本** — 32 GB 封装虽已量产，2025 年多数旗舰仍配 12–16 GB；24–32 GB 能否成为标准取决于端侧 AI 场景能否证明每 8 GB 约 $15–25 的 BOM 增加合理。随着模型向 30B+ 扩展，32 GB 余量在多 Agent 下仍可能耗尽。
- **泛化到骁龙/Intel 之外** — HeteroInfer 仅针对骁龙、Agent.xpu 仅针对 Intel Core Ultra；天玑、Exynos、Apple Silicon 的 NPU 架构（脉动阵列尺寸、量化支持、内存映射）各异，可移植性未验证。
- **架构级替代的时间窗** — PIM（CD-PIM）与 LPDDR6 都可能在 LPDDR5X 自然生命周期结束前改变格局；本文「宽管+榨满」是为端侧 AI 争取 2–3 年余量的演化式精炼，而非终局。

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

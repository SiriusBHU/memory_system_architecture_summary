# A16g · DRAM、PIM 异构协同管理（会算的内存，和不会算的内存）

> **一句话定位**：[A15 §3.4](A15-前沿-先进内存.md) 起了个头——把计算下沉到内存侧（PIM / 近内存计算）。本篇接着问一个**系统/OS 的问题**：当内存里**一部分会算（PIM）、一部分只存（DRAM）**时，操作系统该怎么**协同管理**这两类异构介质——哪些数据放进会算的内存、计算在 CPU/NPU 还是在内存里做、两类内存访问如何调度、一致性怎么保。这是 A16「**异构**」轴的芯片侧第二题。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「第 4 层 · 存储层级」与「2B 物理与回收侧」的延伸——内存不再只是被动存储，它成了**异构的计算 + 存储介质**，分配（[A03](../foundations/A03-物理页分配.md)）与调度都要随之改。
> 🧭 **阅读前置**：先读 [A15 前沿·先进内存 §3.4](A15-前沿-先进内存.md)（PIM/近内存计算基础，本篇不重复器件原理）；统一内存/异构介质治理见 [A16e](A16e-IOMMU统一内存与异构PF-LRU.md)；PIM 的杀手负载（KV/GEMV）见 [A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md)；物理页分配见 [A03](../foundations/A03-物理页分配.md)。
> 🌡️ **演进分级**：**演进厚 ⚡（开放连载，偏研究）**——器件原型已有，但**OS 怎么协同管理 DRAM+PIM 多为研究方向、未定型**；行文重在**问题动因 → 现有原型 → 趋势与未解**，产品化判断按时间衰减看待。

---

## 1. 定位：内存从"只存"到"能算"，管理随之复杂

[A15 §3.4](A15-前沿-先进内存.md) 讲过 PIM（Processing-in-Memory）/ 近内存计算的动机：**把压缩/计算从 CPU 下沉到内存侧，省掉数据来回搬运的能耗与带宽**。本篇不重复器件原理，而是聚焦它给**系统管理**带来的新问题：

> 一旦内存分成"**会算的（PIM）**"和"**只存的（DRAM）**"两类，就多了一堆 OS 决策：**哪些数据该放进 PIM 可及的内存？某个算子在 CPU/NPU 上算还是丢给 PIM 算？两类内存访问怎么在同一条内存通道上调度？PIM 改了内存后 CPU 缓存怎么同步？** 这些"异构协同管理"的问题，就是本篇主题。

## 2. 负载动因：Agent 的 decode 正好落在 PIM 的甜区

本篇属于 A16「**异构**」轴。按 [A16 总论](A16-前沿-Agent时代内存负载.md) 的终端立场，PIM 之所以从"有趣的想法"变成"值得认真管理的介质"，是因为 **Agent 负载里有一大块计算天生适合 PIM**：

- **decode 是 memory-bound**：大模型自回归生成（decode 阶段）的主体是 **GEMV（矩阵×向量）与多头注意力**——**算术强度极低**（每读一字节只做一两次运算），GPU/NPU 的算力被内存带宽**饿死**。这正是 [A16f](A16f-端侧KV-Cache管理方案.md) KV 增长的另一面：KV/权重又大又要反复读。
- **PIM 就在数据旁边算**：把这些**低算术强度、读得多算得少**的算子放到内存里就地算，省掉搬到 CPU/NPU 的能耗与带宽——**PIM 的甜区（1–2 Ops/Byte）几乎就是为 LLM decode 量身定做**。
- **终端的异构又多一维**（A16 三特征里「异构」）：本就 CPU/NPU/GPU/DSP/ISP 多 IP 竞争，现在再加一个"**会算的内存**"作为新的计算位置——OS 的调度对象从"在哪个 IP 上算"扩成"**在哪个 IP、还是在内存里算**"。

> 一句话动因：**Agent 的 decode 是被带宽饿死的 memory-bound 计算，恰好是 PIM 的主场；于是"DRAM + PIM 怎么协同"从学术好奇变成终端必须面对的调度题。**

## 3. 机制本体：从 PIM 器件到"异构协同管理"

### 3.1 PIM 谱系（承 A15 §3.4，只补 LLM 与端侧落点）

| 类型 | 代表 | 能力（厂商声明，待核实量级） | 定位 |
|---|---|---|---|
| **HBM-PIM** | 三星 Aquabolt-XL | MAC 嵌 HBM bank，内部带宽约 2TB/s、约 1.2TFLOPS，适合 1–2 Ops/Byte 算子 | 数据中心 |
| **GDDR6-PIM** | SK 海力士 **AiM / AiMX** | 约 1TFLOPS/颗、1TB/s/颗；AiMX 原型 OPT-6.7B 约 330 tok/s（bs=1） | 数据中心/边缘 |
| **DIMM-PIM** | UPMEM、DIMM-PIM 研究 | DDR DIMM 内置计算，扩容量+带宽，适配 MHA decode | 数据中心 |
| **LPDDR-PIM** | **LP-Spec（研究）** | LPDDR5 增强 PIM + 近数据内存控制器，在 DRAM↔PIM bank 间重分配数据 | **端侧** |

> **端侧落点要清醒**：HBM-PIM/AiM 是**数据中心**介质（HBM/GDDR）；终端用的是 **LPDDR**，对应的是 **LPDDR-PIM**，目前以研究为主（[LP-Spec, arXiv 2508.07227](https://arxiv.org/abs/2508.07227)）。**移动端 PIM 是否量产、何时量产，高度不确定，待核实。**

### 3.2 为什么 LLM 把 PIM 从边缘推到台前

实测量级（厂商/论文声明，**按时间衰减看待**）：

- **HBM-PIM 加速 KV-Cache 处理**：GPU+HBM-PIM 较纯 GPU 约 **3.24×**；
- **GEMV（投影、FFN、全连接）放 HBM2-PIM**：GPT-1.3B 上较 A100 约 **1.6×**；
- decode 阶段的 **MHA** 的内存瓶颈，与 DIMM-PIM 的"容量+带宽可扩展"天然契合（[L3: DIMM-PIM for Long-Context LLM, arXiv 2504.17584](https://arxiv.org/pdf/2504.17584)）。

**LLM 是 PIM 等了多年的"杀手负载"**——此前 PIM 缺一个"读多算少、规模又大"的主流场景，decode 正好补上。

### 3.3 异构协同管理的硬骨头 ← 本篇核心

器件有了，难在 **OS/系统怎么把 DRAM 与 PIM 当一个整体来管**。四类决策，每类都有公认难点：

1. **数据放置（placement）**：哪些数据该落进 PIM 可及的 bank？LP-Spec 用**近数据内存控制器在 DRAM↔PIM bank 间重分配数据**——但"按什么策略放、动态迁移的代价"仍是研究题。这与 [A03 物理页分配](../foundations/A03-物理页分配.md) 直接相关：分配器要能区分"PIM 区 vs 普通区"。
2. **访问调度（scheduling）**：**PIM 请求与普通内存请求不能在同一条通道上同时执行**——因为 PIM 要用 bank 级并行，控制器得在"PIM 服务模式"与"普通访存模式"间**切换**。于是需要 **PIM-aware 的内存调度器**：全局调度 DRAM/PIM 访问、按请求类型动态切地址映射、并平衡两类请求的**公平性与能耗差异**。
3. **计算调度（offload 决策）**：一个算子放 CPU/NPU 算还是丢给 PIM 算，取决于算术强度、数据局部性、当前各 IP 的负载——这是把 [A16d](A16d-压缩IP边际建模.md) 的"边际取舍"搬到"算在哪"的版本。
4. **一致性（coherence）**：PIM 就地改了内存，CPU/NPU 的缓存得失效/同步；这与 [A16e](A16e-IOMMU统一内存与异构PF-LRU.md) 的统一内存一致性是同一类硬骨头。

> 这四点合起来就是"异构协同管理"。**目前缺的不是器件，而是统一的编程模型与系统支持**——学界明确把"工具、编程模型、系统支持"列为 PIM 落地的瓶颈（[New Tools, Programming Models, and System Support for PIM, arXiv 2508.19868](https://arxiv.org/pdf/2508.19868)）。

## 4. 历史：PIM 从"老概念"到"LLM 杀手应用"再到"要系统管"

```
存内/近内存计算（老概念，长期缺主流杀手负载）
   ▼ HBM-PIM(Aquabolt-XL) / AiM 原型（2021–23）：器件可行性验证
   ▼ LLM decode 成为杀手应用（2023–24）：memory-bound GEMV/MHA 正中 PIM 甜区
   ▼ 端侧 LPDDR-PIM（2025，LP-Spec 等研究）：把 PIM 带到手机内存
   ▼ 趋势：OS 协同管理 DRAM+PIM（放置/调度/一致性）—— 仍是研究
```

一句话：**PIM 一直在等一个"读多算少、规模大"的主流负载；LLM decode 把它等来了。器件随之成熟，但"系统怎么管这块会算的内存"才刚起步。**

## 5. 现状与平台差异

| 维度 | 数据中心 | 端侧（移动 SoC） |
|---|---|---|
| 器件 | HBM-PIM / AiM 原型，**未大规模商用** | LPDDR-PIM **研究阶段**（LP-Spec） |
| 系统支持 | PIM-aware 调度器、编程模型多为研究/厂商 SDK | **基本空白**，OS 无 PIM 介质概念 |
| 杀手负载 | LLM decode（KV/GEMV/MHA） | 同，但受能效/面积成本约束更紧 |

> **术语警示**：PIM（处理在内存）≠ 近内存计算（PNM，计算在内存模组旁）≠ 存内计算（CIM，用存储单元做模拟计算）——三者位置与精度不同（[A15 §3.4](A15-前沿-先进内存.md) 已分），**对比时勿混**。本篇"协同管理"主要针对数字 PIM/PNM。

## 6. 趋势与未解问题 ← 本篇重心

- **编程模型与系统支持是真瓶颈**（非器件）：要让 OS/运行时把 PIM 当一等公民调度，需要标准化的**数据放置接口、PIM-aware 分配器、调度策略**——目前各家原型各搞各的，无统一抽象（[arXiv 2508.19868](https://arxiv.org/pdf/2508.19868)）。
- **放置 + 调度 + 一致性三难同解**：放对了数据但调度切模式开销大、或一致性维护贵，收益就被吃掉。三者要联合优化，尚无成熟方案。
- **与统一内存 / KV 管理合流**：PIM 内存也要纳入 [A16e](A16e-IOMMU统一内存与异构PF-LRU.md) 的统一治理；而 PIM 最该加速的就是 [A16f](A16f-端侧KV-Cache管理方案.md) 的 KV/GEMV——"把 KV 放进会算的内存、就地做注意力"是诱人的终局，但端侧能效/面积账还没算清。
- **端侧能效 vs 面积成本**：移动端寸土寸金，给 LPDDR 加 PIM 单元的面积/功耗代价，能否被 decode 提速的能效收益覆盖，**待核实**。
- **压缩也是一种近内存计算**：[A16c](A16c-异构压缩CDSD.md)/[A16d](A16d-压缩IP边际建模.md) 提的"压缩下沉硬件 IP"，本质是 PIM 的一个特例（在内存侧做压缩而非 MAC）——两条线会合。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| PIM 器件基础 ← 近内存计算 | 本篇承其上讲"系统怎么管" | **[A15 §3.4](A15-前沿-先进内存.md)** |
| 数据放置 ↔ 物理页分配 | 分配器要区分 PIM 区/普通区 | [A03](../foundations/A03-物理页分配.md) |
| PIM 内存 → 统一治理 | PIM 也是异构介质，需纳入统一内存 | **[A16e](A16e-IOMMU统一内存与异构PF-LRU.md)** |
| PIM 甜区 ← KV/GEMV | decode 的 memory-bound 算子是 PIM 主场 | **[A16f](A16f-端侧KV-Cache管理方案.md)** |
| 算在哪 ↔ 边际取舍 | offload 决策是"算在哪"的边际优化 | [A16d](A16d-压缩IP边际建模.md) |
| 压缩下沉 ↔ 近内存计算 | 硬件压缩 IP 是 PIM 的一个特例 | [A16c](A16c-异构压缩CDSD.md)、[A16i](A16i-端侧UFS-HBF增强.md) |

## 8. 实测 / 观测点

- PIM 目前**多在硬件原型 / 厂商 SDK / 仿真器**层面，**无统一的 OS 用户态观测口径**；
- 数据中心：厂商 PIM SDK（Samsung/SK hynix）、学术仿真器（如 PIM 模拟框架）看带宽/能效；
- 端侧：LPDDR-PIM 属研究，**无量产可观测接口，待核实**；
- 相关系统侧信号：内存带宽利用率、decode 阶段的内存停顿（roofline 分析，[LLM Inference roofline, arXiv 2402.16363](https://arxiv.org/pdf/2402.16363)）。

## 9. 来源与延伸阅读

**PIM 器件与 LLM 加速**
- [A15 前沿·先进内存 §3.4](A15-前沿-先进内存.md)（HBM-PIM/CXL-PNM 基础与来源）
- [New Tools, Programming Models, and System Support for PIM (arXiv 2508.19868)](https://arxiv.org/pdf/2508.19868) —— 编程模型/系统支持是落地瓶颈
- [L3: DIMM-PIM Integrated Architecture for Scalable Long-Context LLM Inference (arXiv 2504.17584)](https://arxiv.org/pdf/2504.17584)
- [LLM Inference Unveiled: Survey and Roofline Model Insights (arXiv 2402.16363)](https://arxiv.org/pdf/2402.16363) —— decode memory-bound 的 roofline 论证
- [LLM Inference Acceleration: A Comprehensive Hardware Perspective (arXiv 2410.04466)](https://arxiv.org/pdf/2410.04466)

**端侧 LPDDR-PIM**
- [LP-Spec: Leveraging LPDDR PIM for Efficient LLM Mobile Speculative Inference (arXiv 2508.07227)](https://arxiv.org/abs/2508.07227) —— LPDDR5 PIM + 近数据控制器、DRAM↔PIM bank 数据重分配

**异构 DRAM/PIM 调度（系统侧）**
- PIM-aware 内存调度、PIM/非 PIM 请求服务模式切换、PIM 线程调度——见上述综述与相关专利（机制旁证，**具体方案随实现，待核实**）

**承接 / 相邻篇**
- [A16e IOMMU 统一内存 + 异构 PF/LRU](A16e-IOMMU统一内存与异构PF-LRU.md)、[A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md)、[A16h STT/SOT-MRAM 多级缓存](A16h-STT-SOT-MRAM多级缓存方案.md)、[A15 前沿·先进内存](A15-前沿-先进内存.md)、[A03 物理页分配](../foundations/A03-物理页分配.md)

> **待核实 / 待补**：移动端 LPDDR-PIM 的量产时间线与能效/面积账（高度不确定）；OS 协同管理 DRAM+PIM 的放置/调度/一致性是否有任何产品级落地（基本研究阶段）；HBM-PIM/AiM 的性能数字均为厂商/论文声明，需独立复核；PIM 与统一内存（[A16e](A16e-IOMMU统一内存与异构PF-LRU.md)）、KV 管理（[A16f](A16f-端侧KV-Cache管理方案.md)）结合的实际方案；HarmonyOS/iOS 是否有 PIM 相关系统支持（无公开信息）。

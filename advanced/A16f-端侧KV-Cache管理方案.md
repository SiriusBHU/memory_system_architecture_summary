# A16f · 端侧 KV Cache 管理方案（异构 + 增长的交汇点）

> **一句话定位**：KV cache 是端侧大模型推理里**增长最快、又最"异构"**的一块内存——它随上下文线性增长，常驻 NPU 可访问的设备内存、不走普通 LRU，还和传统 app 抢同一块 LPDDR。本篇是 A16 的**桥接篇**（异构 + 增长、跨系统 + 芯片），讲端侧怎么管这块内存：**分页、压缩/量化、offload 到闪存、纳入统一内存治理**四条路，以及它与数据中心 PagedAttention 的根本分野。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 横跨「2B 物理与回收侧」（KV 的回收/压缩）、「第 3 层 硬件」（KV 在设备内存、走统一内存）、「第 4 层 存储层级」（KV offload 到闪存）——这正是它"跨系统/芯片"的体现。
> 🧭 **阅读前置**：先读 [A16e IOMMU 统一内存 + 异构 PF/LRU](A16e-IOMMU统一内存与异构PF-LRU.md)（KV 落在设备内存、如何纳入治理）、[A16c 异构压缩 CDSD](A16c-异构压缩CDSD.md)（KV 的有损专用压缩）、[A09 设备内存全景](../foundations/A09-设备内存全景.md)（dma-buf/pinned）；分页思想的本源见 [A02 缺页与按需分页](../foundations/A02-缺页与按需分页.md)；offload 后端见 [A16i 端侧 UFS–HBF](A16i-端侧UFS-HBF增强.md)。
> 🌡️ **演进分级**：**演进厚 ⚡（开放连载）**——数据中心方案（PagedAttention）成熟，但端侧落地刚起步、且约束完全不同；**重点在 §3.4 端侧分野 与 §6 趋势**。

---

> **⚠️ 本篇立场（先读）**：本篇讨论的「在端侧把 KV cache 纳入系统级内存治理、与传统负载协调」是**基于学界研究与第一性原理的设计探讨与可行性分析**，**业界（Android / iOS / HarmonyOS）目前并未把 KV 纳入系统内存治理**——现有端侧 KV 管理都在推理框架层、与 OS 两张皮。全篇严格区分**① 已有机制与学术工作**（事实，如 PagedAttention/vLLM、KVSwap/HiFC 等论文）与**② 本篇设想**（非现状，标「设想 / 推测 / 待核实」）。核心问题：顺着第一性原理与学界，这样做**是否成立、可行性多大**。

## 1. 定位：把"KV cache"当成一类要管理的内存

自回归大模型每生成一个 token，都要用到前面所有 token 的 **Key/Value 张量**；为避免重算，这些 K/V 被缓存下来，就是 **KV cache**。它的体量大致 ∝ **上下文长度 × 层数 × 注意力头维度 × 精度**——**上下文越长、模型越大，KV 越大**，且**逐 token 增长**。

在端侧，这块内存有三个让它格外难管的特征，恰好对上 A16 的两个特征轴：

- **增长**：长上下文 / agentic 长循环让 KV 持续膨胀，常常**比模型权重还大**；
- **异构**：它常驻 **NPU 可访问的设备内存 / dma-buf**（[A09](../foundations/A09-设备内存全景.md)），pinned、不走普通 LRU；
- **跨层**：管理它既要推理框架（怎么分页/压缩），又要操作系统（怎么和 app 内存协调、怎么 offload）——**这是它"跨系统/芯片"的根因**。

本篇把 KV cache 当作"一类要管理的内存"，系统性地看端侧怎么管它。

## 2. 负载动因：KV cache 就是"异构 + 增长"本身

本篇是 A16 三特征里 **异构 × 增长** 的交汇。按 [A16 总论](A16-前沿-Agent时代内存负载.md) 的终端立场：

- **它是增长的主角**：传统 app 内存大体有界，KV cache 却随会话/任务**单调增长**——一个长程 agent 跑久了，KV 能吃掉数 GB。终端没有数据中心的 HBM 富余，这种增长**直接顶到 LPDDR 上限**。
- **它是异构的极端**：KV 由 NPU 消费、放在设备内存、pinned 不受治理（[A16e](A16e-IOMMU统一内存与异构PF-LRU.md) 要解的正是这个）——它是"**最该被治理、却最够不着治理**"的那类数据。
- **它和传统负载硬竞争**：KV 占的每一字节 LPDDR，都是前后台 app、page cache 少掉的一字节。**Agent 的 KV 与用户的微信/相机在同一块内存上零和博弈**——这是端侧与数据中心最不同的地方：数据中心可以整机伺候推理，终端必须让 KV 给传统体验让路。

> 一句话动因：**KV cache 把"异构"（设备内存、不受治理）和"增长"（随上下文线性膨胀）捏在一起，又被迫和传统 app 抢一块 LPDDR——它是整个 A16 立论最浓缩的实例。**

## 3. 机制本体：端侧管 KV 的四条路

### 3.1 数据中心的范本：PagedAttention 把 KV 当虚拟内存来分页

端侧方案大多脱胎于数据中心的 **PagedAttention**（vLLM，SOSP 2023）。它的洞见极具"操作系统味"：

> **朴素实现给每个序列预留一整段连续 KV 显存，导致严重的内部/外部碎片**——和 [A02/A03](../foundations/A02-缺页与按需分页.md) 里连续物理内存分配的老问题一模一样。PagedAttention **借用虚拟内存/分页思想**：把 KV 切成**固定大小的块**（默认 16 个 token 一块），用一张**块表（block table）把逻辑 KV 块映射到非连续的物理块**——于是碎片消失、并发请求数大增，吞吐提升 2–4×（[PagedAttention, arXiv 2309.06180](https://arxiv.org/pdf/2309.06180)、[vLLM Paged Attention docs](https://docs.vllm.ai/en/stable/design/paged_attention/)）。

> **一个有意思的回环**：LLM 推理框架为管 KV，**在用户态重新发明了一遍 [A01–A02](../foundations/A01-地址空间与虚实转换.md) 的分页**——块表就是页表，KV 块就是页。本系列前半讲的虚拟内存思想，在 KV 管理里又活了一次。

### 3.2 端侧管 KV 的四条路（工具箱）

| 路 | 做法 | 代价 / 约束 | 关联篇 |
|---|---|---|---|
| **① 分页 / 碎片管理** | PagedAttention 式块表，把 KV 分页、按需分配 | 框架层逻辑，省碎片但不省总量 | [A02](../foundations/A02-缺页与按需分页.md) |
| **② 压缩 / 量化 / 淘汰**（有损） | KIVI 2-bit 量化、H2O/StreamingLLM 淘汰、KV-Compress 按头变率压 | 降精度/丢 token，可能掉质量 | **[A16c](A16c-异构压缩CDSD.md)** |
| **③ offload 到闪存** | 把冷 KV 换到 UFS/SSD，按需取回 | **带宽墙**：移动内存约 100GB/s，闪存约 1GB/s（差 2–3 个量级） | **[A16i](A16i-端侧UFS-HBF增强.md)** |
| **④ 纳入统一内存治理** | 让 KV 在统一内存里被冷热迁移/回收，而非 pinned | 需 [A16e](A16e-IOMMU统一内存与异构PF-LRU.md) 的设备缺页/迁移底座 | **[A16e](A16e-IOMMU统一内存与异构PF-LRU.md)** |

四条路并非互斥：典型端侧方案是**分页（①）+ 量化（②）+ 关键项预取的 offload（③）**叠用，理想终局还要 **④** 把这套接进系统内存治理。

### 3.3 端侧 offload 的关键：带宽墙下靠"预测 + 预取"

offload 是端侧应对增长最直接的手段，但撞上**带宽墙**：移动内存带宽约 100GB/s，而闪存只有约 1GB/s——**比数据中心差 2–3 个数量级**。所以端侧 offload 不能"用时才取"，必须**预测哪些 KV 项关键、提前预取**：

- **KVSwap**（端侧长上下文）：把**完整 KV 存盘**，内存里只留一份**紧凑的 K 表示**用来**预测关键项**，再提前预取进缓冲——专为"CPU/NPU 共享统一内存、存储 I/O 受限"的端侧设计（[KVSwap, arXiv 2511.11907](https://arxiv.org/pdf/2511.11907)）。
- **HiFC**：DRAM-free 的 KV 换页，把 KV 页放进 NVMe 的 **pSLC** 区，顺序 I/O 下逼近 DRAM 吞吐、并把写寿命提升约 8×（[HiFC, OpenReview](https://openreview.net/forum?id=onhjdWCxZY)）——这与 [A16i](A16i-端侧UFS-HBF增强.md) 的"更快闪存后端"是一条线。
- NPU 侧还要优化 **prefill**（预填充常是端侧推理延迟的关键路径，[Fast On-device LLM Inference with NPUs, ASPLOS '25](https://xumengwei.github.io/files/ASPLOS25-NPU.pdf)）。

### 3.4 端侧 vs 数据中心：为什么 PagedAttention 不能照搬 ← 核心

| 维度 | 数据中心（vLLM/PagedAttention） | 端侧 |
|---|---|---|
| KV 放哪 | GPU HBM，独占、带宽极高 | **共享 LPDDR / dma-buf**，与传统 app 抢（[A09](../foundations/A09-设备内存全景.md)） |
| 谁管 | 推理框架软件分页器，整机伺候推理 | 框架 + **OS 必须协调**（KV 不能饿死前台 app） |
| offload 后端 | NVMe，带宽充裕 | UFS，**带宽差 2–3 个量级**，且要护闪存寿命 |
| 治理 | KV pinned 在 HBM 即可 | KV pinned 会**挤压可回收池、提前触发 lmkd**（[A16e](A16e-IOMMU统一内存与异构PF-LRU.md)） |
| 目标 | 最大化吞吐 | **在不毁传统体验的前提下**塞下 KV |

> **结论**：PagedAttention 的**分页思想**端侧可借，但它的**前提（独占显存、带宽充裕、整机伺候）端侧全不成立**。端侧 KV 管理的真问题是 **"KV 与传统负载在一块受限 LPDDR 上的公平共存 + 带宽墙下的 offload"**——这正是它必须既改框架、又改系统的原因。

## 4. 历史：KV 管理从"连续大块"到"分页、压缩、换页"

```
朴素 KV：每序列预留连续显存 —— 碎片严重、并发受限
   ▼ PagedAttention（SOSP 2023）：块表分页，碎片消失，吞吐 2–4×
   ▼ 压缩/量化/淘汰（2024）：KIVI/H2O/KV-Compress 降精度或丢 token（A16c）
   ▼ offload 到闪存（2024–25）：KVSwap/HiFC，带宽墙下靠预测+预取
   ▼ 趋势：端侧把 KV 纳入统一内存治理（A16e），与系统内存协调
```

主线：**KV 管理一路在"复刻操作系统的内存管理"**——先是分页（虚拟内存），再是压缩（zram），再是换页到慢存储（swap）。端侧的新意在于：**这些都得在"和传统负载共存、带宽受限"的约束下重做一遍**。

## 5. 现状与平台差异

| 维度 | 数据中心 | 端侧（Android/SoC） | iOS | HarmonyOS |
|---|---|---|---|---|
| KV 管理成熟度 | vLLM/PagedAttention 成熟 | **碎片化**：llama.cpp / MLC-LLM / 厂商 NPU 栈各搞各的，多在**框架层**、与 OS 内存治理两张皮 | 框架层（Core ML / MLX，细节不公开） | 待核实 |
| offload | NVMe，常规 | UFS，研究阶段（KVSwap/HiFC 类） | 不公开 | 待核实 |
| 与系统内存协调 | 框架独占即可 | **基本缺位**——KV 占用对系统 lmkd 不透明，易误杀或被挤 | 不公开 | 待核实 |

> **术语警示**：KV 的"分页/换页"是**推理框架层**的概念（块表、KV swap），**不是 [A02](../foundations/A02-缺页与按需分页.md)/[A06](../foundations/A06-压缩与换页.md) 的 OS 分页/zram**——同名异层，别混。KV 的"压缩"多为**有损**（量化/淘汰），≠ zram 无损压缩（[A16c](A16c-异构压缩CDSD.md) 已强调）。

## 6. 趋势与未解问题 ← 本篇重心

- **框架层与 OS 层的割裂**：今天 KV 管理几乎全在推理框架内，**系统看不见 KV 的冷热、也管不了它**；KV 占用对 [lmkd](../foundations/A08-压力与低内存终止.md) 不透明，可能导致"系统杀了前台 app 却动不了臃肿的 KV"。让框架把 KV 冷热/可让度透给系统、由系统统一在 KV 与 app 间做预算分配，是最大的开放工程（呼应 [A16c §6](A16c-异构压缩CDSD.md)、[A16d](A16d-压缩IP边际建模.md)）。
- **结构化冷热怎么喂给系统**：KV 的冷热由**注意力稀疏**决定（H2O 的"重击者"、StreamingLLM 的"注意力汇"），这是比 LRU 精细得多的语义冷热。能不能把它接进 [A16a](A16a-LRU主动扫描.md) 的主动扫描 / [A16b](A16b-eBPF可编程回收策略-Android.md) 的可编程策略，让系统据"注意力冷热"治理 KV？目前空白。
- **带宽墙难越**：offload 受限于闪存带宽（§3.3），预取预测一旦失准就是直接卡顿；[A16i 的 HBF](A16i-端侧UFS-HBF增强.md) 想从硬件侧抬高这堵墙。
- **安全与隔离**：KV 含用户对话上下文，offload 到闪存涉及加密/擦除；放在 secure heap 又不可迁移（[A16e §6](A16e-IOMMU统一内存与异构PF-LRU.md)）。
- **统一内存治理的落地**：让 KV 像普通内存一样被冷热迁移/回收（[A16e](A16e-IOMMU统一内存与异构PF-LRU.md) 的 ④），在端侧还基本是设想。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| KV 在设备内存 ↔ 统一治理 | KV 落 dma-buf，靠统一内存 + 异构 PF/LRU 纳入治理 | **[A16e](A16e-IOMMU统一内存与异构PF-LRU.md)、[A09](../foundations/A09-设备内存全景.md)** |
| KV 压缩 ← 异构压缩 | 量化/淘汰是 KV 的有损专用压缩 | **[A16c](A16c-异构压缩CDSD.md)** |
| KV offload → 闪存后端 | 冷 KV 换到 UFS/HBF | **[A16i](A16i-端侧UFS-HBF增强.md)** |
| 分页思想 ← 虚拟内存 | 块表 = 页表，KV 管理复刻 OS 分页 | [A02](../foundations/A02-缺页与按需分页.md) |
| KV 冷热 → 主动扫描/可编程 | 注意力稀疏的结构化冷热喂给系统 | [A16a](A16a-LRU主动扫描.md)、[A16b](A16b-eBPF可编程回收策略-Android.md) |
| 预算分配 ↔ 边际建模 | KV 与 app/压缩共享 CPU/内存预算 | [A16d](A16d-压缩IP边际建模.md) |

## 8. 实测 / 观测点

- **框架层**（KV 的真正主场）：推理框架的 KV 内存占用、块表利用率、量化位宽、保留 token 比、offload 命中/预取准确率——口径随框架（vLLM / llama.cpp / MLC / 厂商 NPU SDK）而异；
- **系统层**：KV 多落在 dma-buf / 设备堆，按 [A09](../foundations/A09-设备内存全景.md)/[A13](../foundations/A13-内存度量与排障.md) 的 dma-buf 计量观察其对系统内存的挤占；
- offload I/O：`iostat` / UFS 统计看 KV 换页的读写带宽与写放大（护闪存，[A16i](A16i-端侧UFS-HBF增强.md)）；
- **端侧各框架的统一观测口径缺失，待核实**。

## 9. 来源与延伸阅读

**KV 分页（数据中心范本）**
- [Efficient Memory Management for LLM Serving with PagedAttention (arXiv 2309.06180, SOSP 2023)](https://arxiv.org/pdf/2309.06180)、[vLLM Paged Attention (docs)](https://docs.vllm.ai/en/stable/design/paged_attention/)、[PagedAttention (Wikipedia)](https://en.wikipedia.org/wiki/PagedAttention)

**端侧 KV offload / 闪存换页**
- [KVSwap: Disk-aware KV Cache Offloading for Long-Context On-device Inference (arXiv 2511.11907)](https://arxiv.org/pdf/2511.11907) —— 端侧统一内存 + 受限存储下的预测预取
- [HiFC: High-efficiency Flash-based KV Cache Swapping (OpenReview)](https://openreview.net/forum?id=onhjdWCxZY) —— pSLC、写寿命 8×
- [Fast On-device LLM Inference with NPUs (ASPLOS '25)](https://xumengwei.github.io/files/ASPLOS25-NPU.pdf) —— NPU prefill 优化
- [KV-Compress: Paged KV-Cache Compression with Variable Rates per Head (arXiv 2410.00161)](https://arxiv.org/pdf/2410.00161)

**KV 压缩（有损，详见 A16c）**
- KIVI / H2O / StreamingLLM 等：见 [A16c 异构压缩 CDSD](A16c-异构压缩CDSD.md) 的来源

**承接 / 相邻篇**
- [A16e IOMMU 统一内存 + 异构 PF/LRU](A16e-IOMMU统一内存与异构PF-LRU.md)、[A16c 异构压缩 CDSD](A16c-异构压缩CDSD.md)、[A16i 端侧 UFS–HBF 增强](A16i-端侧UFS-HBF增强.md)、[A09 设备内存全景](../foundations/A09-设备内存全景.md)、[A02 缺页与按需分页](../foundations/A02-缺页与按需分页.md)、[A16 总论](A16-前沿-Agent时代内存负载.md)

> **待核实 / 待补**：端侧各推理框架（llama.cpp/MLC/厂商 NPU SDK）KV 管理的具体方案与 KV 是否走 dma-buf/统一内存；KV 占用对系统 lmkd 的可见性与协调机制（基本缺位）；端侧 KV offload 在量产机的实际启用；把"注意力稀疏冷热"接入系统主动扫描/可编程策略的任何尝试；iOS（Core ML/MLX）与 HarmonyOS 的端侧 KV 管理细节（不公开）；KVSwap/HiFC 等是研究原型，量产落地待核实。

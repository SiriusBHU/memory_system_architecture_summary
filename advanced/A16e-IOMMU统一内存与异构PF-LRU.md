# A16e · IOMMU 统一内存 + 异构 Page Fault / LRU（把 DMA 数据纳入冷热治理）

> **一句话定位**：[A10](../foundations/A10-IOMMU-SMMU与DMA.md) 讲清了设备怎么做地址转换与隔离，但留了一个大洞——**设备正在用的内存大多 pinned、不进 LRU、不受回收治理**（[A09 §3.5](../foundations/A09-设备内存全景.md)）。本篇讲怎么把这个洞补上：用**统一内存（CPU 与加速器共享地址空间）+ 异构 Page Fault（设备也能缺页）+ 异构 LRU/迁移（设备数据也能被回收/迁移）**，让 NPU/GPU 上的那块内存**像 CPU 内存一样被冷热治理**。这是 A16「**异构**」轴的芯片侧主篇。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「第 3 层 硬件 · IOMMU/SMMU」与「2B 物理与回收侧」的**打通**——让设备侧内存进入回收/迁移的版图。
> 🧭 **阅读前置**：先读 [A10 IOMMU/SMMU 与 DMA](../foundations/A10-IOMMU-SMMU与DMA.md)（SVA、设备缺页 stall/PRI，本篇不重复其机制细节）、[A09 设备内存全景](../foundations/A09-设备内存全景.md)（dma-buf/CMA/pinned，本篇要解的正是其 §3.5 的 pinned 痛点）；缺页基本功见 [A02 缺页与按需分页](../foundations/A02-缺页与按需分页.md)。
> 🌡️ **演进分级**：**演进厚 ⚡🔗**——机制本体（SVA/HMM）在数据中心成熟，但"把设备数据纳入统一冷热治理"在终端属前沿；**重点在 §3 机制本体 与 §6 趋势**。

---

## 1. 定位：补上"设备内存不受治理"那个洞

[A01–A05](../foundations/A05-冷热识别的演进.md) 的冷热治理（LRU、回收、压缩）默认治理对象是 **CPU 进程的页**。但终端里相当一部分内存是 [A09](../foundations/A09-设备内存全景.md) 的设备内存——GPU 纹理、相机/视频缓冲、**NPU 上的模型权重与 KV cache**。它们的共同特征是：

> **被 pinned（钉住）、不能移动、不能换出、不进普通 LRU**——因为设备正在 DMA，物理页一动就出错（[A09 §3.5](../foundations/A09-设备内存全景.md)）。

结果是：内存治理这套精巧的机器，**对设备内存基本失效**。设备内存只能"占着"，靠上层应用主动释放。本篇要回答的是：

> **能不能让设备也"缺页"、让设备数据也能被回收/迁移，从而把它纳入和 CPU 内存同一套冷热治理？** 这需要三块拼在一起：**统一内存 + 异构 Page Fault + 异构 LRU/迁移**。

## 2. 负载动因：Agent 把"不受治理的内存"撑大了

本篇属于 A16「**异构**」轴。按 [A16 总论](A16-前沿-Agent时代内存负载.md) 的终端立场，动因是**多任务 · 多 IP 竞争**：

- **设备侧内存被 Agent 撑大**：过去设备内存主要是图形/相机缓冲，体量有界；Agent 时代，**NPU 上的模型权重与 KV cache 成了内存大户**，且常驻 [A09](../foundations/A09-设备内存全景.md) 的 dma-buf / 设备堆里——**又大、又 pinned、又不进 LRU**。
- **它直接挤压传统负载**：这块 pinned 内存挤占可回收池（[00 §2 的 DEVMEM→压力级联](../foundations/00-内存系统总览.md)），让前后台 app 更早被 [lmkd 杀](../foundations/A08-压力与低内存终止.md)。**Agent 的内存和传统 app 的内存在同一块 LPDDR 上硬碰硬，而前者还不受治理**——这是终端最不公平的一处。
- **多 IP 并发**：CPU、NPU、GPU、ISP 同时按各自模式访问内存，谁也不肯让出带宽。要做整机最优的内存调度，**就不能有"治理盲区"**。

> 一句话动因：**Agent 把"最不受治理的那类内存（设备 pinned）"撑成了内存大户——要继续做整机内存治理，必须把设备数据从治理盲区拉回版图。**

## 3. 机制本体：统一内存 → 设备缺页 → 设备数据可迁移

### 3.1 "统一内存"的两层含义（务必区分）

"统一内存"是个容易混的词，终端语境下有**两个不同层次**：

| 层次 | 含义 | 终端现状 |
|---|---|---|
| **物理统一（UMA）** | CPU/NPU/GPU **共享同一块物理 DRAM**（LPDDR），无独立显存 | **移动 SoC 本就如此**；Apple Silicon 以 "Unified Memory" 为卖点 |
| **地址空间统一 + 一致（SVA/SVM）** | 设备与进程**共享同一虚拟地址空间**：任一 CPU 指针对设备也有效，且缓存一致 | 由 [A10 的 SVA](../foundations/A10-IOMMU-SMMU与DMA.md) 提供；终端落地程度待核实 |

> **别混**：移动端早有**物理统一**（省去了拷贝），但这不等于**地址空间统一 + 可治理**。本篇关心的是后者——它才是"把设备数据纳入冷热治理"的前提。Apple 的 "Unified Memory" 主要指前者（物理共享），其内部是否做 CPU↔设备的按需迁移治理**待核实**。

### 3.2 异构 Page Fault：让设备也能"缺页"，从而免 pin

设备数据之所以 pinned，根因是**设备过去不会缺页**——地址转换失败就是错误，所以必须提前把页钉死。[A10 §3.5](../foundations/A10-IOMMU-SMMU与DMA.md) 讲的两套机制改变了这点（此处只引结论，不重复）：

- **ATS（地址转换服务）**：设备缓存地址转换；IOMMU 用 `mmu_notifier` 让设备 TLB 与 CPU 页表同步；
- **PRI / IOPF（页请求 / IO 页错误）+ SMMU stall**：转换缺失时，设备**发起页请求、把事务挂起**，等内核把页调入再继续——**这就是"设备缺页（异构 Page Fault）"**。

**关键后果**：一旦设备能缺页，**就不必再 pin 所有页**——内核文档明说，SVA 的方向是"**device drivers should be able to use SVA without pinning all pages**"。免 pin，意味着这些页**重新变得可回收、可迁移**。（2025 年还在完善 SVA 缺页的错误通知路径，见 [IOMMU SVA page fault notifiers, patchew 2025](https://patchew.org/linux/20250710134215.97840-1-sergey.temerkhanov@intel.com/20250710134215.97840-2-sergey.temerkhanov@intel.com/)，**接口仍在演化、待核实**。）

### 3.3 异构 LRU / 迁移：HMM 把设备数据接进迁移版图

光能缺页还不够，得有机制**在 CPU 内存与设备内存之间搬数据、并保持地址有效**。这正是 **HMM（Heterogeneous Memory Management）** 做的（[HMM, kernel.org](https://docs.kernel.org/mm/hmm.html)）：

- **共享地址空间**：HMM 给 SVM 提供帮助函数，**让设备透明地、与 CPU 一致地访问进程地址**——任一有效 CPU 指针对设备也有效；
- **`ZONE_DEVICE` 内存**：给每页设备内存分配一个 `struct page`，使它**能被既有的页迁移机制搬运**（这些页特殊在 CPU 不能直接映射）；
- **双向迁移 + 不 pin**：可把主存页**迁到设备内存**；**CPU 一旦访问设备页，触发缺页并迁回主存**；全程用 `mmu_notifier` 把 CPU 页表更新同步到设备页表，**而非 pin 死内存**。迁移的"何时、迁哪些"策略留给驱动。

把三块拼起来：**统一地址空间（SVA/HMM）让 CPU 与加速器看同一份内存；设备缺页（PRI/IOPF）让设备数据免 pin；ZONE_DEVICE + 迁移让设备数据能被搬运/回收**——于是 [A09](../foundations/A09-设备内存全景.md)/[A15c §7](A15c-移动端分层内存与内存压缩前沿.md) 反复点名的那块"**设备内存够不着冷热治理**"的硬骨头，第一次有了技术底座。这就是"**异构 LRU**"的含义：让 LRU/迁移的治理对象从"CPU 页"扩到"设备可访问的页"。

## 4. 历史：从"pin 死内存"到"设备也能缺页、也能迁移"

```
32 位 legacy DMA：设备地址受限，靠 bounce buffer
   ▼ 经典 DMA：pin 死内存，物理页不可动（A09 §3.5）—— 简单但僵
   ▼ GPU/NPU 协处理兴起：要共享指针、要大块内存，pin 的代价越来越痛
   ▼ SVA（地址空间共享）+ ATS/PRI（设备缺页）—— A10 §3.4–3.5
        设备免 pin、按需分页成为可能
   ▼ HMM（ZONE_DEVICE + 双向迁移 + mmu_notifier）
        设备数据进入"可迁移"版图
   ▼ 趋势（本篇主张）：把设备数据纳入统一冷热治理（异构 LRU）
```

一句话：**"非均匀"从 CPU 渗到设备**——设备从"只能 pin 的特殊公民"逐步获得了 CPU 页早就有的能力（缺页、迁移、被回收），治理的版图随之扩张。

## 5. 现状与平台差异

| 维度 | 数据中心（Linux 服务器） | 移动端（Android/SoC） | iOS / Darwin | HarmonyOS |
|---|---|---|---|---|
| 物理统一内存 | 多为独立显存 + CXL | **SoC 物理 UMA（共享 LPDDR）** | Apple Silicon UMA | SoC UMA |
| 地址空间统一（SVA） | 成熟（DSA/GPU + IOMMU SVA） | SMMUv3 支持 stall/PRI，**NPU 实际是否走 SVA 免 pin、抑或仍 ION pin，待核实** | 不公开（Metal 统一内存抽象） | 待核实 |
| 设备数据可迁移（HMM） | GPU 驱动用 HMM 成熟 | **落地有限**：多数仍 dma-buf pin；HMM 在移动 GPU/NPU 的采用待核实 | 不公开 | 待核实 |
| 设备数据纳入 LRU/回收 | 仍是难点（一致性、所有权） | **基本空白**（[A15c §7](A15c-移动端分层内存与内存压缩前沿.md) 同列） | 不公开 | 待核实 |

> **术语警示**：移动端"统一内存"日常多指**物理 UMA**（省拷贝）；本篇的"统一内存 + 异构 PF/LRU"指**地址空间统一 + 可治理**，是更强的要求，**别用前者推断后者已实现**。

## 6. 趋势与未解问题 ← 本篇重心

- **设备缺页延迟 vs pin 的确定性**（承 [A10 §6](../foundations/A10-IOMMU-SMMU与DMA.md)）：免 pin 换来灵活，但页请求的往返延迟天然高于 pin 死内存的经典 DMA；对 NPU 推理这种**对延迟敏感**的负载，"按需分页一段 KV"可能直接拖慢出词速度。如何预取、如何对热 KV 仍 pin/对冷 KV 才迁，是核心权衡。
- **迁移/回收一致性的硬骨头**：要回收/迁移一块**正被 GPU/NPU 共享的缓冲**，得处理所有权、生命周期、缓存一致——"压缩或换出一块设备正在读的页"在一致性上极易出错（[A15c §7](A15c-移动端分层内存与内存压缩前沿.md) 已点名）。
- **secure / protected heap 迁不动**：DRM/安全堆（[A09 §3.4](../foundations/A09-设备内存全景.md)）出于隔离要求**不可迁移、不可换出**，注定留在治理之外。
- **统一的设备内存计量与配额**（承 [A09 §6](../foundations/A09-设备内存全景.md) 的 GPU cgroup 方向）：要把设备数据纳入治理，得先能**按 app/进程计量设备内存**并设配额——这是 per-app 公平回收的前提，社区的 DRM/GPU cgroup controller 正往这走。
- **与端侧 KV 管理的合流**：KV cache 是最该被"异构治理"的设备数据——把它在统一内存里按冷热迁移/换出，正是 [A16f](A16f-端侧KV-Cache管理方案.md) 的核心议题。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| 地址转换/设备缺页 ← IOMMU | SVA/ATS/PRI/stall 是统一内存与异构 PF 的底座 | **[A10](../foundations/A10-IOMMU-SMMU与DMA.md)** |
| pinned 痛点 ← 设备内存 | 本篇要解的正是 dma-buf/pinned 不受治理 | **[A09](../foundations/A09-设备内存全景.md)** |
| 缺页基本功 ← 按需分页 | 设备缺页与 CPU 缺页同源 | [A02](../foundations/A02-缺页与按需分页.md) |
| 设备数据冷热 → KV 管理 | KV 是最该纳入异构治理的设备数据 | **[A16f](A16f-端侧KV-Cache管理方案.md)** |
| 异构介质 → PIM/分层 | 统一内存也要面对 PIM 等异构介质 | [A16g](A16g-DRAM-PIM异构协同管理.md)、[A15](A15-前沿-先进内存.md) |
| 计量/配额 ↔ memcg/GPU cgroup | 设备内存计量是纳入治理的前提 | [A07](../foundations/A07-cgroup-memcg.md)、[A09 §6](../foundations/A09-设备内存全景.md) |

## 8. 实测 / 观测点

- IOMMU/SVA：`/sys/class/iommu/`、`/sys/kernel/iommu_groups/`；ARM SMMU 的 stall、PCIe 的 ATS/PRI 能力（`lspci -vvv` 看 ATS/PRI/PASID capability）；
- 设备内存与迁移：`/proc/meminfo` 的不可回收占用、dma-buf 计量（[A09](../foundations/A09-设备内存全景.md)/[A13](../foundations/A13-内存度量与排障.md)）；HMM/`ZONE_DEVICE` 多在驱动侧，无统一用户旋钮；
- 缺页观察：`/proc/vmstat` 的 `pgfault`/`pgmajfault`（设备缺页是否反映在统计中**因实现而异，待核实**）；
- **移动端 NPU 是否走 SVA 免 pin：无统一公开观测口径，待核实**。

## 9. 来源与延伸阅读

**统一地址空间与设备数据迁移**
- [Heterogeneous Memory Management (HMM) (kernel.org)](https://docs.kernel.org/mm/hmm.html) —— SVM 帮助、`ZONE_DEVICE`、CPU↔设备双向迁移、用 `mmu_notifier` 取代 pin
- [Shared Virtual Addressing (SVA) (kernel.org)](https://docs.kernel.org/arch/x86/sva.html) —— PASID/ATS/PRI、ENQCMD、"without pinning all pages" 的方向
- [Shared Virtual Addressing for the IOMMU (LWN)](https://lwn.net/Articles/747230/)
- [IOMMU SVA page fault processing error notifiers (patchew, 2025)](https://patchew.org/linux/20250710134215.97840-1-sergey.temerkhanov@intel.com/20250710134215.97840-2-sergey.temerkhanov@intel.com/) —— SVA 缺页路径仍在完善

**设备内存与本系列锚点**
- [A10 IOMMU/SMMU 与 DMA](../foundations/A10-IOMMU-SMMU与DMA.md)（SVA、stall vs PRI、设备缺页延迟）、[A09 设备内存全景](../foundations/A09-设备内存全景.md)（dma-buf/CMA/pinned、GPU cgroup 方向）、[A02 缺页与按需分页](../foundations/A02-缺页与按需分页.md)

**承接 / 相邻篇**
- [A16 总论](A16-前沿-Agent时代内存负载.md)、[A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md)、[A16g DRAM·PIM 异构协同](A16g-DRAM-PIM异构协同管理.md)、[A15c 移动端分层内存与内存压缩前沿](A15c-移动端分层内存与内存压缩前沿.md)

> **待核实 / 待补**：移动端 NPU/GPU 是否真走 SVA 免 pin（抑或仍 dma-buf/ION pin），HMM 在移动 GPU/NPU 的实际采用；Apple "Unified Memory" 是否做 CPU↔设备按需迁移治理（还是仅物理共享）；HarmonyOS 的设备内存与统一地址空间机制（[A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md) 无公开细节）；把设备数据纳入 LRU/回收的任何实际落地（[A15c §7](A15c-移动端分层内存与内存压缩前沿.md) 同列空白）；SVA 缺页延迟在 NPU 推理路径上的实测影响；设备内存按 app 计量/配额（GPU cgroup）的成熟度。

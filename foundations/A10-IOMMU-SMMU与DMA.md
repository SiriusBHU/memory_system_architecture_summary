# A10 · IOMMU/SMMU 与 DMA（设备地址转换与 SVA）

> **一句话定位**：给"设备发起的访存"也配一套 MMU——把设备 DMA 用的地址（IOVA）翻成物理地址、在设备之间做隔离与防护；并在 SVA 下让设备**直接共享 CPU 进程的页表**，这正是 A01 反复点到的那条 🔗 强耦合线的展开。
>
> 📍 **对应总览**：[00 总览](00-内存系统总览.md) 的「第 3 层 硬件 · IOMMU/SMMU」，与「2A 地址空间侧 · 页表」深度纠缠。
> 🧭 **阅读前置**：先读 [A01 地址空间与虚实转换](A01-地址空间与虚实转换.md)（页表 / MMU/TLB / ASID 是本篇的镜像对象），并搭配 [A09 设备内存全景](A09-设备内存全景.md)（dma-buf / CMA）一起看；物理页来源见 [A03 物理页分配](A03-物理页分配.md)。
> 🌡️ **演进分级**：**演进厚 ⚡🔗**。机制本体（地址转换）与 CPU 侧 MMU 同构，但 **SVA 把"页表"从 CPU 私有变成 CPU 与设备共享的资源**——§4 历史、§6 趋势、§7 配合（与 A01 页表的共享关系）都是主体。

---

## 1. 定位：它在地图上的哪一格

CPU 侧有 MMU 把虚拟地址翻成物理地址（[A01](A01-地址空间与虚实转换.md) §3.4）。但**设备**（GPU、NPU、网卡、各种 DMA 引擎）也要访存——它们发出的地址若直接落到物理总线上，就等于绕过了虚拟内存的一切保护。IOMMU（I/O Memory Management Unit）就是"设备侧的 MMU"：它坐在设备与内存控制器之间，对**每一笔 DMA 请求**做地址转换与权限检查。

平台术语在这里必须分清，**全篇不混用**：

- **ARM**：称 **SMMU**（System MMU），当前主力是 **SMMUv3**（旧的 SMMUv2 仍在部分 SoC）。本系列聚焦的移动端（Android / HarmonyOS）基本是 ARM 阵营，故下文以 SMMU 为主。
- **x86**：Intel 称 **VT-d**（DMA Remapping，DMAR），AMD 称 **AMD-Vi**（IOMMU）。
- **PCIe 通用扩展**：PASID / ATS / PRI 是 PCIe 规范定义的能力，被各家 IOMMU 复用。

## 2. 它解决什么问题（没有它会怎样）

没有 IOMMU 时，设备 DMA 用的是**物理地址**，由此带来三个问题，恰好与 [A01 §2](A01-地址空间与虚实转换.md) 那张"为什么要虚拟内存"的表一一对应，只是主语从"进程"换成"设备"：

| 问题 | 没有 IOMMU | 有了之后 |
|---|---|---|
| **隔离/防护** | 任一设备（或被攻陷的固件）可 DMA 读写任意物理内存，是经典的 DMA 攻击面 | 每设备只能访问被显式映射的页，越界 DMA 被拦截 |
| **地址抽象** | 驱动必须给设备喂**物理连续**的缓冲区，受碎片所限（依赖 [CMA](A09-设备内存全景.md)） | 物理离散的页可经 IOMMU 映射成设备眼中**连续**的 IOVA |
| **共享语义** | 设备看到的地址与进程的 VA 毫无关系，缓冲区需在两套地址间倒手 | 极致形态 SVA 下，设备与进程**共用同一套 VA** |

设备侧那个被翻译的地址叫 **IOVA**（I/O Virtual Address，也叫 DMA 地址 / bus address）。"IOVA → 物理地址"由 IOMMU 用一套**自己的页表**完成——这套页表与 CPU 页表是否同一份，正是 SVA 与传统 DMA 的分水岭（§3.4 / §7）。

## 3. 机制本体：当前是怎么做的

### 3.1 SMMU 怎么定位"这是哪个设备、用哪套页表"

每个能发起 DMA 的设备（更准确说是每条数据流）有一个 **StreamID（SID）**——在 PCIe 术语里就是 **Requester ID**。SMMU 用 StreamID 索引一张 **Stream Table**，取出对应的 **Stream Table Entry（STE）**；STE 里有该流的配置、stage-2 页表基址（S2TTB / VMID），以及指向 **Context Descriptor（CD）** 的指针。CD 里则装着 stage-1 的页表基址 **TTB0/TTB1 与 ASID**——可以看出它与 [A01 §3.1](A01-地址空间与虚实转换.md) 的 `TTBRx_EL1`/ASID 是同构的，CD 本质就是"设备侧的 TTBR 上下文"。（[ARM SMMU 架构与 STE/CD 结构梳理 · openEuler](https://www.openeuler.openatom.cn/en/blog/wxggg/2020-11-21-iommu-smmu-intro.html)）

一台设备可以承载**多个地址空间**：CD 是一张表，用 **SubstreamID（SSID）** 索引；**SSID 在 PCIe 术语里就是 PASID**，最大 20 位。于是"StreamID 选设备、SubstreamID/PASID 选该设备内的某个进程地址空间"——这正是 SVA 能让同一台 NPU 同时为多个进程做 DMA 的硬件基础。（[Add support for Substream IDs · patchwork](https://patchwork.kernel.org/patch/10394963/)）

### 3.2 两级转换：stage-1 与 stage-2

SMMUv3 像 CPU 的两阶段地址转换一样，支持两级（类似 x86 的 EPT / nested paging，但**勿与 VT-d 术语混用**）：

```
设备 IOVA ──stage1(CD: TTB0/TTB1)──► IPA ──stage2(STE: S2TTB)──► 物理地址
            (VA→IPA，进程/驱动视角)        (IPA→PA，虚拟化/Hypervisor 视角)
```

- **stage-1**（VA→IPA）：用 CD 里的页表，对应"进程/驱动给设备的那套地址"；
- **stage-2**（IPA→PA）：用 STE 里的页表，对应**虚拟化**场景下 Hypervisor 对客户机的再映射。

两级都可单独"bypass"。裸机非虚拟化时常只用 stage-1；passthrough 直通设备给虚机时 stage-2 兜底隔离。SMMUv2 早期只能给每设备一个地址空间，**多地址空间（多 SSID）是 SMMUv3 的能力**。

### 3.3 IOVA 与 DMA API：传统 DMA 的日常路径

绝大多数驱动并不直接碰 SMMU 寄存器，而是走内核的 **DMA API**。典型一笔：驱动把一段内核缓冲交给 `dma_map_single()`/`dma_map_sg()`，在开启 IOMMU 时，内核的 `dma-iommu` 层会**分配一段 IOVA**、在 IOMMU 页表里建立"IOVA→物理页"的映射，返回设备能用的 DMA 地址；用完 `dma_unmap_*` 拆映射。（[Dynamic DMA mapping · 内核文档](https://docs.kernel.org/core-api/dma-api.html)）

这里有个**性能与安全的取舍旋钮**，移动端调优常碰到：

- **strict（严格）模式**：每次 unmap 都立即失效 IOMMU TLB（IOTLB）——最安全，但失效开销高；
- **deferred / lazy（惰性，`IOMMU_DOMAIN_DMA_FQ` 刷新队列）**：把失效批量延后，吞吐更好，但被解映射的页在 IOTLB 真正失效前仍有**短暂可被设备访问**的窗口（弱化了隔离即时性）。（[`drivers/iommu/dma-iommu.c` · torvalds/linux](https://github.com/torvalds/linux/blob/master/drivers/iommu/dma-iommu.c)）

注意这套传统路径的前提是**缓冲区必须 pin 住**：DMA 进行中物理页不能被回收/迁移，否则设备会写到错的地方。pinned 内存挤占回收，是设备内存计量的老问题（见 [A09](A09-设备内存全景.md) 与 [A01](A01-地址空间与虚实转换.md) §7 "pinned 挤压"）。

### 3.4 SVA：设备与进程共享同一套页表

**SVA（Shared Virtual Addressing，共享虚拟寻址）** 是本篇的"演进厚"核心：让设备**直接使用 CPU 进程的页表**，于是设备和进程看到**完全相同的虚拟地址**——应用 `malloc` 出来的指针可以原样交给设备做 DMA，无需先 `dma_map` 翻成 IOVA。([Shared Virtual Addressing for the IOMMU · LWN](https://lwn.net/Articles/747230/))

它需要三块硬件能力同时到位（LWN 把这三点列为前提）：

1. **多地址空间标识 = PASID**：设备 DMA 里带上 20 位 PASID，IOMMU 据此知道"这笔访问属于哪个进程的地址空间"；内核 `iommu_sva_bind_device()` 分配 PASID，并把**进程的页表基址写进 PASID 上下文**（x86 上即把进程的 `%cr3` 填进 PASID context entry；ARM 上即把进程的 TTBR/ASID 填进对应 CD）。([SVA with ENQCMD · 内核文档](https://docs.kernel.org/arch/x86/sva.html))
2. **设备能像 CPU 一样缺页（I/O page fault）**：见 §3.5；
3. **MMU 与 IOMMU 的页表格式兼容**——这是能"共享同一份页表"的硬约束。只有当 SMMU 的 stage-1 页表格式与 CPU 的 ARM64 页表格式一致时，才可能让二者指向**同一棵页表树**而非各维护一份。([SVA · LWN](https://lwn.net/Articles/747230/))

共享之后，**CPU 改了页表，设备必须立刻看到一致结果**。内核为此挂上 **mmu_notifier**：当进程页表发生映射/权限变更或回收解映射时，通知 IOMMU 驱动同步失效设备侧缓存（ATC，见下）。([SVA with ENQCMD · 内核文档](https://docs.kernel.org/arch/x86/sva.html))这正是 [A01 §3.4](A01-地址空间与虚实转换.md) 那条"改 PTE → 广播失效 TLB"的**跨设备延伸**：失效不再只发给各 CPU 核，还要发给共享了这套页表的设备。

### 3.5 设备也会缺页：stall 模式 vs PRI

SVA 下设备直接用进程页表，而进程的页可能尚未分配或已被换出——于是设备 DMA 也会**缺页**，必须有机制让设备"等内核补好页再继续"，而不是直接报错。ARM 与 PCIe 走的是两条不同实现，**勿混用**：

- **PCIe 路径 = ATS + PRI**：设备先用 **ATS（Address Translation Services）** 把翻译结果缓存进自己的 **ATC（设备侧 TLB）**；当目标 VA 尚未在 CPU 页表中（ATS 查不到），设备发 **PRI（Page Request Interface）** 的页请求（PPR）给 IOMMU，内核当作一次缺页把页补进 CPU 页表，再回应设备重试。**前提是设备自带翻译缓存**。([SVA · LWN](https://lwn.net/Articles/747230/))
- **ARM 平台路径 = stall 模式**：很多 SoC 上的平台设备没有 ATC。SMMUv3 的 **stall 模型**改为：翻译缺页时 SMMU **把这笔事务"挂起/驻留"（stall）**，记录细节并产生事件中断；内核（经统一的 I/O page fault 处理 `io-pgfault.c`）补好页表后，向 SMMU 发 **Resume 命令**让事务重试。它与 PRI 解决同一问题，但**不要求设备有自己的翻译缓存**，更贴合 ARM 平台设备。([iommu: I/O page faults for SMMUv3 · LWN](https://lwn.net/Articles/837012/)、[Add stall support for platform devices · patchwork](https://patchwork.ozlabs.org/project/linux-pci/patch/20200224182401.353359-24-jean-philippe@linaro.org/))

> 一句话对照：**PRI = 设备先缓存、查不到再请求；stall = 设备先卡住、等内核放行**。两者都让 DMA 能打到"未 pin、按需分页"的内存上——也就把 [A02 缺页](A02-缺页与按需分页.md)那套按需分页的好处第一次带给了设备。

## 4. 历史：为什么演变成今天这样

IOMMU 最早的两个动机都很"工程"：一是**让 32 位老设备访问 4GB 以上内存**（地址重映射，替代 bounce buffer/swiotlb）；二是**虚拟化直通**——把物理设备直接交给虚机又不能让它 DMA 踩到别的虚机，于是用 stage-2 把客户机 IPA 限死在自己的物理范围内。这两阶段里，IOMMU 维护的是**与 CPU 完全独立的一套页表**，驱动通过 DMA API 显式 map/unmap，缓冲区全程 pin 住。

痛点随着 GPU/NPU 这类**与 CPU 紧密协作的加速器**而来：传统模型要在"进程 VA"和"设备 IOVA"两套地址间反复倒手，复杂且易错，还被迫 pin 大量内存。于是演进方向收敛到一句话——**让设备复用进程已有的那套页表**：PCIe 加上 PASID/ATS/PRI 三件套，ARM 用 SMMUv3 的 SSID + stall，内核侧把 SMMUv3 的 SVM/SVA、统一 I/O page fault 处理（`io-pgfault.c`）在 5.x 时间线陆续合入，AMD 的 IOMMU SVA 支持则到 **6.7** 前后才补齐其四个补丁系列的主干。([AMD Closing In On IOMMU SVA Support · Phoronix](https://www.phoronix.com/news/AMD-IOMMU-SVA-Nears))（具体 SVA-on-ARM 的首个稳定版本号 **（待核实）**。）

## 5. 现状与平台差异（简）

| 维度 | Android / HarmonyOS（ARM） | x86（Intel / AMD） |
|---|---|---|
| IOMMU 名称 | **SMMU**（v3 为主，部分 v2） | **VT-d**（Intel）/ **AMD-Vi**（AMD） |
| 进程地址空间标识 | **SubstreamID（SSID）** = PASID | **PASID** |
| 设备缺页机制 | SMMUv3 **stall**（平台设备）/ PRI（PCIe） | **ATS + PRI** |
| 典型受益方 | GPU / NPU 共享应用 VA、相机/编解码大缓冲 DMA | 加速器（DSA 等）、SR-IOV 直通 |

> iOS / XNU 的 DART（Apple 自研 IOMMU）有独立实现与术语，本系列暂 **（待核实 / 留待 A14 平台对照）**。

## 6. 趋势与未解问题

- **隔离 vs 性能的拉锯继续**：strict 与 deferred-flush 的取舍、IOTLB 失效广播开销，是高带宽设备的持续优化点；deferred 模式的"短暂可访问窗口"在安全敏感场景仍有争议。
- **SVA 的缺页代价**：SVA 用页请求换"免 pin、按需分页"的灵活性，但**页请求的往返延迟天然高于 pin 死内存的经典 DMA**（LWN 明确指出 SVA 通常更慢），如何降低设备缺页延迟、做预取，是开放问题。([SVA · LWN](https://lwn.net/Articles/747230/))
- **机密计算的新约束**：可信执行环境 / 机密虚机要求"连 Hypervisor 也不能随意经 IOMMU 读设备内存"，对 stage-2 与 IOMMU 信任模型提出了新要求 **（待核实）**。

## 7. 配合与依赖（本篇主体 · 与 A01 页表的共享关系）

本篇是 [A01 §7](A01-地址空间与虚实转换.md) 那条 🔗 "页表 ↔ IOMMU/SMMU"边的完整展开。把跨层耦合摊开：

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| **IOMMU 页表 ↔ CPU 页表（传统）** | 两套独立页表；DMA API map/unmap 维护 IOMMU 侧，缓冲区需 pin | 本篇 §3.3 |
| **IOMMU 页表 ↔ CPU 页表（SVA）🔗** | **共享同一棵进程页表**：设备用 PASID/SSID 选中进程地址空间，与 CPU 同 VA；前提是页表格式兼容 | 本篇 §3.4 / [A01](A01-地址空间与虚实转换.md) |
| **改 PTE → 失效设备缓存 🔗** | CPU 改/回收页表项时，经 mmu_notifier 同步失效设备 ATC（A01 的 TLB 失效向设备延伸） | 本篇 §3.4 / [A01 §3.4](A01-地址空间与虚实转换.md) |
| **设备缺页 → 核心缺页** | stall / PRI 把设备访问未映射页转成一次内核缺页 | 本篇 §3.5 / [A02](A02-缺页与按需分页.md) |
| **DMA 物理页来源** | map 的物理页来自伙伴系统；连续大缓冲走 CMA | [A03](A03-物理页分配.md) / [A09](A09-设备内存全景.md) |
| **与 dma-buf 协作** | dma-buf 描述跨设备共享缓冲，`map_dma_buf` 时由 IOMMU 建立各设备的 IOVA 映射 | [A09](A09-设备内存全景.md) |
| **pinned 挤压回收** | 传统 DMA pin 住的页不可回收/迁移，给压力侧添堵 | [A09](A09-设备内存全景.md) / [A08](A08-压力与低内存终止.md) |

> 这张表的两条 🔗 正是 [01 路线图](01-连载规划与文章结构.md#2-连载路线图阅读顺序--写作顺序)把本篇定为 **⚡🔗** 的原因：**SVA 让"页表"不再是 CPU 私有数据结构，而成了 CPU 与设备共享的资源**——A01 讲页表"被谁遍历、被谁缓存、改了要通知谁"，本篇给出的新答案是"也被设备遍历、被设备缓存（ATC）、改了要通知设备"。

## 8. 实测 / 观测点

- `dmesg | grep -i -E "smmu|iommu|dmar"`：看 SMMU/IOMMU 是否使能、StreamID 绑定与故障事件；
- `/sys/kernel/iommu_groups/`：看设备的 IOMMU 分组（隔离边界 = group 粒度）；
- `/sys/bus/pci/devices/*/iommu_group`、`iommu/intel-iommu` 等节点：查设备所属 group 与能力；
- 内核启动参数：`iommu.strict=0/1`、`iommu.passthrough=1`（直通绕过翻译）、`intel_iommu=on` / ARM 多由 DT/ACPI 自动使能；
- SVA 相关：设备是否上报 PASID/PRI/ATS 能力（`lspci -vvv` 的 `PASID`/`PRI`/`ATS` 字段），以及驱动是否走 `iommu_sva_bind_device()`；
- 源码锚点：`drivers/iommu/dma-iommu.c`、`drivers/iommu/io-pgfault.c`、`drivers/iommu/iommu-sva.c`、`drivers/iommu/arm/arm-smmu-v3/`。

## 9. 来源与延伸阅读

- SVA / PASID（机制基准）：[Shared Virtual Addressing for the IOMMU (LWN)](https://lwn.net/Articles/747230/)、[Shared Virtual Addressing (SVA) with ENQCMD (内核文档)](https://docs.kernel.org/arch/x86/sva.html)
- ARM SMMU 架构 / STE / CD / 两级转换：[Introduction to IOMMU and ARM SMMU (openEuler)](https://www.openeuler.openatom.cn/en/blog/wxggg/2020-11-21-iommu-smmu-intro.html)、[iommu/arm-smmu-v3: Add support for Substream IDs (patchwork)](https://patchwork.kernel.org/patch/10394963/)、Arm® System Memory Management Unit Architecture Specification（SMMUv3，IHI 0070 系列）
- 设备缺页（stall / PRI）：[iommu: I/O page faults for SMMUv3 (LWN)](https://lwn.net/Articles/837012/)、[iommu/arm-smmu-v3: Add stall support for platform devices (patchwork)](https://patchwork.ozlabs.org/project/linux-pci/patch/20200224182401.353359-24-jean-philippe@linaro.org/)
- DMA API / IOVA / strict-vs-deferred：[Dynamic DMA mapping using the generic device (内核文档)](https://docs.kernel.org/core-api/dma-api.html)、[drivers/iommu/dma-iommu.c (torvalds/linux)](https://github.com/torvalds/linux/blob/master/drivers/iommu/dma-iommu.c)
- AMD SVA 进展（版本旁证）：[AMD Closing In On IOMMU SVA Support For Linux (Phoronix)](https://www.phoronix.com/news/AMD-IOMMU-SVA-Nears)

> **待核实 / 待补**：SVA-on-ARM（SMMUv3）首个稳定合入的内核版本号；iOS/XNU 的 DART 实现与术语（留待 [A14 平台对照]）；机密计算对 IOMMU stage-2 信任模型的具体要求；deferred-flush 在 AOSP/厂商 BSP 的默认取值。

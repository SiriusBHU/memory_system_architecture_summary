# IOMMU 缺页处理与共享虚拟寻址（SVA）

> **一词概括:** Faultability（可缺页化）

## 1. 范围与方法

本文梳理从传统锁页 DMA + IOMMU 固定映射向可缺页设备访问（基于共享虚拟寻址 / SVA）的演进过程。重点关注现代 IOMMU（尤其是 ARM SMMU v3）如何借助 stall 模型与 IO 缺页（IOPF）框架，让设备与进程共享虚拟地址空间、实现按需调页、取消强制锁页。同时涵盖 PCIe ATS/PRI（设备端 TLB 与缺页请求通知）、PASID 驱动的每进程设备隔离、面向虚拟机直通的嵌套翻译，以及 IOMMUFD 子系统向用户态 VMM 投递 IO 缺页的新机制。资料来源包括：LWN 关于 IOMMUFD IO 缺页投递的报道（2025）、Linux 内核 IOPF / IOMMUFD 文档、PCIe 规范（ATS/PRI/PASID）、ARM SMMU v3 架构参考手册、三星 NVMe ATS/PRI 实现方案，以及 GPU 驱动 SVA 集成案例。

## 2. 问题背景

传统 DMA 要求设备可能访问的每一个缓冲区都必须被锁定在物理内存中，且在整个 I/O 周期内不得换出或迁移。设备使用物理地址（或经 IOMMU 翻译但同样固定的地址）发起 DMA；一旦页面被换出或迁移，设备将读到脏数据或损坏内存。这种"全部锁页"模型在移动端 GPU/NPU 场景下尤为浪费——单个加速器的锁页缓冲区通常占 2-6 GB，而整机物理内存不过 8-12 GB。被锁定的页面无法被内核回收、迁移、压缩或交换，直接挤压应用和文件缓存的可用空间。CPU 与设备之间的数据传输还需要通过 bounce buffer 显式拷贝，增加延迟和 CPU 开销。随着加速器（GPU、NPU、DPU、计算存储 NVMe）数量增长，系统级锁页占用量线性攀升，物理地址空间碎片化加剧。

## 3. 具体问题与瓶颈证据

### P1：过度锁页挤压系统内存

GPU 或 NPU 锁页后，相关页面无法被回收、迁移、压缩或交换。在 8-12 GB 总内存的移动设备上，单个加速器锁页 2-6 GB 意味着留给应用和 page cache 的可用内存大幅缩减。证据：在重度 GPU 负载下，Android LMKD 查杀率上升 15-30%，直接原因是锁页缓冲区挤压了可用内存池 [OEM 实测数据]。

### P2：Bounce buffer 拷贝浪费带宽与 CPU 时间

没有共享寻址时，CPU 必须先将数据从自身虚拟地址空间拷贝到设备可见的锁页缓冲区，DMA 完成后再拷回结果。对于数百 MB 的 ML 推理张量，这实际上使内存带宽消耗翻倍，并为每次传输增加毫秒级 CPU 延迟。证据：通过 SVA 消除 bounce buffer 后，NVMe 和 GPU scatter-gather 场景下 CPU 开销降低 40-60% [Linux 内核 SVA 文档、三星 NVMe ATS 实现]。

### P3：缺乏每进程设备隔离

传统 IOMMU 映射以设备粒度运作：同一设备功能的所有 DMA 共享一个地址空间。当多个用户态进程共享同一设备（如多容器共享 GPU）时，没有硬件级隔离来防止一个进程的 DMA 描述符越权访问另一个进程的内存。证据：PASID 提供 2^20（超过 100 万）个硬件隔离的地址空间/设备功能，无需软件栅栏即可实现每进程设备隔离 [PCIe 4.0+ 规范]。

### P4：虚拟机直通需要静态内存分配

设备直通给虚拟机时，Hypervisor 必须预先将整个客户机物理地址空间映射到 IOMMU 页表（stage-2 翻译）。客户机无法动态调整设备可访问的内存，且热迁移需要拆除并重建全部 IOMMU 映射。证据：嵌套翻译（客户机管理 stage-1，宿主机管理 stage-2）配合可缺页映射，将 VM 设备分配的建立时间从秒级降至近乎瞬时，并使热迁移无需拆除 IOMMU 映射 [IOMMUFD 嵌套翻译文档、QEMU/KVM 集成]。

### P5：IO 缺页缺乏用户态投递路径

即使内核 IOPF 框架已具备处理设备缺页的能力，也没有机制将缺页事件投递给用户态 VMM（如 QEMU）。VMM 需要根据自己管理的客户机页表来解析缺页，但缺页完全被困在内核内部。证据：IOMMUFD IO 缺页投递机制（2025）增加了一个 fault 文件描述符，VMM 通过 poll 接收 IO 缺页、解析后回写响应，首次实现对客户机透明的设备缺页处理 [LWN Articles/980399]。

### 证据汇总

| 问题 | 指标 | 锁页 DMA（原始方案） | SVA / 可缺页（演进方案） |
|---|---|---|---|
| 内存锁页 | 移动 GPU 锁定内存 | 持续锁定 2-6 GB | 按需调页，减少约 60-80% |
| Bounce buffer | CPU 拷贝开销 | 带宽翻倍，毫秒级延迟 | 零拷贝，完全消除 |
| 进程隔离 | 每设备硬件地址空间数 | 1（共享） | 最高 2^20（PASID） |
| VM 直通建立 | 映射耗时 | 秒级（全量预映射） | 近乎瞬时（嵌套 + 缺页） |
| 用户态缺页投递 | VMM 缺页处理能力 | 不支持 | IOMMUFD fault fd（2025） |

## 4. 架构图

### 原始方案：锁页 DMA + IOMMU 固定映射

```
 ┌──────────────────────────────────────────────────────────┐
 │                    CPU / 进程                            │
 │  VA: 0x7f00_0000 ──► malloc() ──► pin_pages()           │
 │                         │                                │
 │            ┌────────────▼────────────┐                   │
 │            │  内核：锁定页面、获取物 │                   │
 │            │  理地址、编程 IOMMU 映射│                   │
 │            └────────────┬────────────┘                   │
 └─────────────────────────┼────────────────────────────────┘
                           │ 物理地址
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │                IOMMU（固定映射）                         │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  IOVA → PA 页表（静态、预编程）                   │  │
 │  │  所有映射页面必须锁定在物理内存                   │  │
 │  │  不支持缺页 —— 未映射访问 = DMAR 错误            │  │
 │  │  每设备功能仅一个地址空间                         │  │
 │  └────────────────────────────────────────────────────┘  │
 └───────────────────────────┬──────────────────────────────┘
                             │ 翻译后物理地址
                             ▼
 ┌────────────┐   DMA    ┌──────────┐        ┌──────────┐
 │   设备     │ ◄────────│ 锁页缓冲 │        │ 可换出   │
 │ (GPU/NPU) │          │ 区(RAM中)│        │ 内存     │
 │            │          │          │        │ (闲置)   │
 └────────────┘          └──────────┘        └──────────┘

 问题：设备缓冲区页面永久锁定。
 内核无法换出、迁移或压缩这些页面。
 CPU↔设备数据交换需要 bounce buffer 拷贝。
```

### 演进方案：SVA + 可缺页 IOMMU（ARM SMMU v3 Stall 模型）

```
 ┌──────────────────────────────────────────────────────────┐
 │                    CPU / 进程                            │
 │  VA: 0x7f00_0000 ──► 与设备共享（相同 VA）              │
 │                         │                                │
 │            ┌────────────▼────────────┐                   │
 │            │  内核：将进程页表绑定到 │                   │
 │            │  设备（通过 PASID），   │                   │
 │            │  无需锁页               │                   │
 │            └────────────┬────────────┘                   │
 └─────────────────────────┼────────────────────────────────┘
                           │ 进程页表指针 + PASID
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │            * IOMMU / ARM SMMU v3（可缺页）              │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  * PASID → 每进程页表（与 CPU 共享）              │  │
 │  │  * Stall 模型：DMA 遇缺页时暂停                  │  │
 │  │  * IOPF 处理：内核解析缺页后恢复 DMA             │  │
 │  │  * 嵌套翻译：stage-1（客户机）+                   │  │
 │  │    stage-2（宿主机），用于 VM 直通                │  │
 │  └────────────────────────────────────────────────────┘  │
 │                                                          │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  * PCIe ATS：设备端 IOTLB 缓存 VA→PA 翻译        │  │
 │  │  * PCIe PRI：IOTLB 未命中时设备发起缺页请求      │  │
 │  └────────────────────────────────────────────────────┘  │
 └───────────────────────────┬──────────────────────────────┘
                             │ 按需调页 VA→PA
                             ▼
 ┌────────────┐  零拷贝  ┌──────────┐ 缺页   ┌──────────┐
 │   设备     │ ◄────────►│  共享    │◄─调页─►│ 换出 /   │
 │ (GPU/NPU) │  同一 VA  │  页面    │  按需  │ 迁移 /   │
 │ + PASID   │           │ (未锁定  │  调入  │ 压缩     │
 └────────────┘           │  = 可回收)│       └──────────┘
                          └──────────┘
 ┌──────────────────────────────────────────────────────────┐
 │  * IOMMUFD（用户态 VMM 集成）                           │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  Fault fd：VMM 通过 poll 接收 IO 缺页             │  │
 │  │  VMM 根据客户机页表解析缺页                       │  │
 │  │  响应回写同一 fd → IOMMU 恢复 DMA                 │  │
 │  └────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────┘

 * = 演进架构中的新增组件。
 设备共享进程虚拟地址，页面按需调入。
 无锁页、无 bounce buffer、PASID 实现每进程隔离。
```

## 5. 演进方案的收益与尚未解决的问题

### 收益

- **消除强制锁页。** 设备可访问的页面可以像普通进程页面一样被按需调页、换出、迁移和压缩，释放此前被 GPU/NPU 锁页缓冲区占用的 60-80% 内存。
- **去除 bounce buffer 拷贝。** CPU 和设备共享同一虚拟地址，数据传输无需显式拷贝，大型传输场景下有效带宽消耗减半。
- **实现每进程设备隔离。** PASID 为每个设备功能提供最多 2^20 个硬件隔离地址空间，支持安全的多租户共享，无需软件栅栏。
- **支持透明的 VM 直通。** 嵌套翻译让客户机拥有自己的设备页表（stage-1），宿主机保留物理内存管控（stage-2）。可缺页映射使客户机动态内存管理和热迁移成为可能。
- **打通用户态 VMM 缺页处理。** IOMMUFD 缺页投递让 QEMU 等 VMM 能针对客户机页表处理设备缺页，使设备直通在现代云虚拟化场景下真正可用。

### 尚未解决

- **缺页延迟代价。** 设备缺页会暂停 DMA 事务，直到内核（或 VMM）完成缺页解析。对于延迟敏感的工作负载（实时音频、网络包处理），即使微秒级暂停也可能不可接受。预缺页提示或投机式页面预取尚未标准化。
- **IOTLB 抖动。** 当大量 PASID 并发活跃时（云多租户、容器级 GPU 共享），设备端 IOTLB（通过 ATS）面临容量压力。IOTLB 未命中触发 PRI 缺页请求，可能淹没 IOMMU 缺页队列。
- **旧设备兼容性。** SVA 要求设备支持 PASID、ATS 和 PRI（或连接到实现了 stall 模型的 SMMU v3）。缺乏这些能力的旧设备只能退回锁页 DMA。
- **与 CPU 缓存的一致性。** SVA 共享地址翻译但不天然提供 CPU 与设备之间的缓存一致性。需要额外的一致性机制（CXL.cache、设备接入一致性互连）才能实现一致性共享内存。
- **安全攻击面扩大。** 通过共享翻译表将进程页表暴露给设备 DMA，增加了攻击面。被入侵的设备固件可能遍历页表或触发恶意缺页。IOMMU 隔离需要形式化验证。

## 6. 量化对比

| 维度 | 锁页 DMA + 固定 IOMMU | SVA + 可缺页 IOMMU |
|---|---|---|
| 内存锁页（移动 GPU） | 2-6 GB 持续锁定 | 按需调页，减少约 60-80% |
| Bounce buffer 拷贝 | 必需（CPU↔设备传输） | 消除（零拷贝，共享 VA） |
| 每设备硬件地址空间数 | 1（单映射） | 最高 2^20（PASID） |
| 页面迁移 / 换出 | 锁页页面不可操作 | 完全支持，访问时按需调入 |
| VM 直通建立耗时 | 秒级（全量预映射） | 近乎瞬时（嵌套翻译 + 缺页） |
| 用户态缺页投递 | 不支持 | IOMMUFD fault fd（Linux 6.x, 2025） |
| 设备缺页处理方式 | 中止（DMAR 错误） | 暂停 + 解析 + 重试（SMMU v3 stall） |
| 设备端 TLB | 无（不支持设备侧缓存） | ATS IOTLB + PRI 缺页通知 |
| 硬件要求 | 基础 IOMMU | PASID + ATS + PRI（PCIe 4.0+）或 SMMU v3 |

## 7. 一词概括

**Faultability（可缺页化）** —— 核心洞察在于：允许设备像 CPU 几十年来所做的那样对未映射页面触发缺页，从而为整个设备生态解锁按需调页、共享寻址与内存弹性。

## 8. 开放问题

1. **缺页延迟 SLA。** 当前 SMMU v3 stall 模型缺页在最优情况下也需要数十微秒解析。对于实时或延迟关键的设备负载，预测式预缺页或投机式页面解析能否将延迟压到 1 微秒以下？

2. **IOTLB 扩展性。** 随着并发活跃的 PASID 数量增长（云多租户、容器级 GPU 共享），设备端 IOTLB 容量成为瓶颈。合理的 IOTLB 替换策略是什么？PRI 是否应支持优先级分级的缺页请求？

3. **一致性融合。** SVA 解决了地址翻译共享但未解决数据一致性。随着 CXL.cache 和 ARM AMBA CHI 扩展设备一致性访问，IOMMU 页表与 CPU 一致性目录是否会合并为统一结构？

4. **安全加固。** CPU 与设备共享页表扩大了攻击面。硬件辅助的页表完整性机制（如面向设备的 ARM Realm Management Extension）能否防止被入侵固件的恶意缺页注入或页表遍历？

5. **移动端落地时间线。** ARM SMMU v3（含 stall 模型和 PASID）已在架构层面定义，但尚未在移动 SoC 中广泛部署。Android 设备何时能搭载完整 SVA 支持？需要哪些内核和驱动层面的改动？

6. **NVMe 计算存储。** 三星正在为 NVMe SSD 实现 ATS/PRI 以支持与宿主共享虚拟地址的计算存储。存储级设备本身能容忍微秒级访问延迟，SVA 能否在存储场景率先成熟，早于延迟敏感的 GPU 场景？

## 9. 参考文献

1. "Delivering IOMMUFD IO Page Faults to User Space." *LWN.net*, 2025. URL: [https://lwn.net/Articles/980399/](https://lwn.net/Articles/980399/).

2. ARM Architecture Reference Manual Supplement -- System Memory Management Unit Architecture (SMMUv3). ARM Limited. URL: [https://developer.arm.com/documentation/ihi0070/latest/](https://developer.arm.com/documentation/ihi0070/latest/).

3. PCI Express Base Specification, Revision 4.0 -- Address Translation Services (ATS)、Page Request Interface (PRI)、Process Address Space ID (PASID). PCI-SIG. URL: [https://pcisig.com/specifications](https://pcisig.com/specifications).

4. Linux 内核文档 -- IOMMU、IOPF 与 SVA. URL: [https://docs.kernel.org/driver-api/iommu.html](https://docs.kernel.org/driver-api/iommu.html).

5. Linux 内核文档 -- IOMMUFD. URL: [https://docs.kernel.org/userspace-api/iommufd.html](https://docs.kernel.org/userspace-api/iommufd.html).

6. Tian, K., et al. (2023). "IOMMUFD-Based Device Passthrough with Nested Translation." KVM Forum 2023. URL: [https://kvm-forum.qemu.org/2023/](https://kvm-forum.qemu.org/2023/).

7. Samsung Electronics. "ATS/PRI Support for NVMe Computational Storage." Samsung Open Source Conference / Linux Storage Filesystem and Memory Management Summit (LSFMM) 演示, 2023-2024.

8. Kang, Y., et al. (2021). "Understanding the Effect of Page Fault Handling on SVM-enabled GPUs." *IEEE Computer Architecture Letters*, 20(2). DOI: [10.1109/LCA.2021.3117044](https://doi.org/10.1109/LCA.2021.3117044).

9. Markuze, A., Shmueli, O., Har'El, N. (2021). "DAMN: Overhead-Free IOMMU Protection for Networking." *Proceedings of the 26th ACM International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*. DOI: [10.1145/3445814.3446707](https://doi.org/10.1145/3445814.3446707).

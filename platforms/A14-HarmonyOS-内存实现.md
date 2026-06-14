# A14 · 平台对照 — HarmonyOS / OpenHarmony 内存实现

> **一句话定位**：把 [00 总览](../foundations/00-内存系统总览.md) 的四层骨架，逐格填上 HarmonyOS / OpenHarmony 的实现——但 HarmonyOS 不是"一套内存系统"，而是**三套内核基座**各填各的，必须先分清再对照。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的四层（① 用户态 / ② 内核 2A 地址空间 + 2B 物理回收 / ③ 硬件 / ④ 存储层级）。
> 🧭 **阅读前置**：先读 [00 总览](../foundations/00-内存系统总览.md) 与机制篇 [A01](../foundations/A01-地址空间与虚实转换.md)–[A13](../foundations/A13-内存度量与排障.md)；本篇是**对照型**，凡标准系统复用 Linux 的机制都回链对应 A0X，不重复展开。
> 🌡️ **演进分级**：综合篇。**诚实优先**——公开程度差异极大：LiteOS-A/M **有完整开源码可逐行核**（本篇 LiteOS-A 部分已据源码坐实），标准系统就是 Linux，而 HarmonyOS NEXT 鸿蒙内核仅有论文/宣讲信息。**严格区分「已证实（带源码/来源）」与「待核实」，宁可留白不杜撰。**

---

## 0. 写在前面：三套基座，不可混为一谈

"HarmonyOS 的内存是怎么管的"没有单一答案，因为 **HarmonyOS / OpenHarmony 在不同设备档位上跑的是完全不同的内核**：

| 基座 | 归属 | 目标设备 / 参考内存 | MMU/MPU | 内存管理特征 | 公开程度 |
|---|---|---|---|---|---|
| **LiteOS-M** | OpenHarmony **轻量系统**（Mini） | MCU（Cortex-M / RISC-V 32 位），最小 **128 KiB** | 无 MMU，MPU 段保护（是否必选待核实） | 静态内存池 + 动态 **TLSF** 分配器；无虚拟内存 | **全开源** |
| **LiteOS-A** | OpenHarmony **小型系统**（Small） | MB 级内存设备（Cortex-A） | **有 MMU**（ARM 短描述符两级页表） | 虚拟内存 `LosVmSpace`、缺页/COW、**伙伴式物理页**、**文件页 LRU + 内核 OOM**、TLSF 堆 | **全开源**（本篇已据源码坐实） |
| **Linux** | OpenHarmony **标准系统**（Standard） | 应用处理器（Cortex-A），最小 **128 MiB** | 有 MMU | **就是 Linux 内核**（Linux-4.19 / 5.10），机制同 A0X | 开源（标准 Linux） |
| **鸿蒙内核 HMKernel / HongMeng** | **HarmonyOS NEXT**（HarmonyOS 5，闭源商用） | 手机 / 平板 / 路由器 / 车机等 | 有 MMU | 自研**微内核**：policy-free kernel paging、address-token 访问控制 | **仅论文 + 宣讲**，源码不公开 |

> - **OpenHarmony**（开源）小型系统可在 **LiteOS-A 或 Linux 之间二选一**；标准系统用 **Linux**。([华为开发者联盟 · OpenHarmony 系统类型与内核](https://developer.huawei.com/consumer/cn/forum/topic/0204729778972140718))
> - **HarmonyOS NEXT**（华为闭源商用版）用自研**鸿蒙微内核（HongMeng / HMKernel）**，已**去掉 Linux 内核与 AOSP 兼容层**——与 OpenHarmony 标准系统的 Linux 基座是两回事。([USENIX OSDI '24 · Microkernel Goes General](https://www.usenix.org/conference/osdi24/presentation/chen-haibo))

下面沿 00 四层填表，每层按"哪套基座"分别说明。**LiteOS-A 一列的事实均来自 [openharmony/kernel_liteos_a](https://github.com/openharmony/kernel_liteos_a) 主线源码**（文末列具体文件锚点）。

---

## 1. 第 1 层 · 用户态

| 子项 | LiteOS-M（轻量） | LiteOS-A（小型） | 标准系统（Linux） | HarmonyOS NEXT |
|---|---|---|---|---|
| 地址空间布局 | 单地址空间 + MPU 段保护（待核实必选性） | 每进程独立 `LosVmSpace`，代码/堆/栈/映射分区 | 标准 Linux VMA，见 [A01](../foundations/A01-地址空间与虚实转换.md) | 微内核 + 用户态服务，地址空间隔离（细节待核实） |
| 用户态分配器 | 内核动态内存接口（无独立 libc malloc 层） | musl libc 之上的 `malloc`（具体实现待核实） | musl libc（OpenHarmony 用 musl），`malloc` 实现待核实 | 待核实（是否复用 musl） |
| 内存系统调用 | 裸机式，无 `mmap`/`brk` 完整语义 | 类 POSIX 内存接口 + vmalloc（`los_vm_syscall.c`） | 标准 `mmap`/`brk`/`madvise`，见 [A01](../foundations/A01-地址空间与虚实转换.md) | 论文称兼容 Linux API/ABI（细节待核实） |

> OpenHarmony 用户态 C 库为 **musl libc**；但 `malloc` 走 musl 自带（mallocng）还是其他，本次未在 musl 源码层证实，标「待核实」——**不照搬 Android 的 Scudo 结论**。

---

## 2. 第 2 层 · 2A 地址空间侧（"该映射成什么"）

### 2.1 标准系统（Linux）

**就是 Linux 内核**（OpenHarmony 已适配 Linux-4.19、5.10）。因此 VMA、多级页表、缺页、COW **与 [A01](../foundations/A01-地址空间与虚实转换.md)、[A02](../foundations/A02-缺页与按需分页.md) 完全一致**。注意 4.19/5.10 较旧，**maple tree（6.1）、per-VMA lock（6.4）不在这两个内核里**——与最新 AOSP/GKI 的一个差异点。

### 2.2 小型系统（LiteOS-A）—— 已据源码坐实

LiteOS-A **带 MMU**，有真正的进程虚拟内存，结构与 Linux 高度同构但是**自有实现**（非 `mm/`）：

- **地址空间结构**：每进程一个 `LosVmSpace`，其中地址区间 `LosVmMapRegion`（VMA 等价物，带 `open/close/fault/remove` 操作钩子）组织在一棵**红黑树 `regionRbTree`** 上，并单列一个 `heap` 区。([`los_vm_map.h`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/include/los_vm_map.h)) — 注意这对应 **Linux 6.1 之前的 rbtree VMA**，而非 [A01](../foundations/A01-地址空间与虚实转换.md) 讲的 maple tree。
- **页表**：ARM **短描述符两级页表**——一级表项要么是 **1 MiB 段（section）**、要么指向二级表；二级表项是 **4 KiB 小页 / 64 KiB 大页**。([`los_mmu_descriptor_v6.h`](https://github.com/openharmony/kernel_liteos_a/blob/master/arch/arm/arm/include/los_mmu_descriptor_v6.h)、[`los_arch_mmu.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/arch/arm/arm/src/los_arch_mmu.c)) 页大小 **4 KiB**（`PAGE_SHIFT = 12`）。
- **缺页 / COW**：访问未建映射的地址触发 page fault，经 `region->fault` 钩子（`los_vm_fault.c`）申请物理页、填内容、回填页表——minor/major 模型同 [A02](../foundations/A02-缺页与按需分页.md)，COW 由 region 标志驱动。
- **地址空间分区**：`los_vm_zone.h` 划出内核 VMM（cached）、uncached、vmalloc、外设设备区与 **DMA 区**——内核/用户地址空间分离。**vmalloc** 按页申请**物理不连续**内存再建映射，用于大块。

### 2.3 轻量系统（LiteOS-M）

面向 MCU，**无 MMU**，靠 MPU 做段隔离。**没有虚拟地址空间/页表/缺页**——单一物理地址空间上的内存池管理，归到 2B 讲。

### 2.4 鸿蒙内核（HarmonyOS NEXT）

公开信息仅来自 OSDI '24 论文《Microkernel Goes General》：微内核架构、**兼容 Linux API/ABI**；与内存相关的设计点是 **policy-free kernel paging（机制在内核、策略可下放）** 与 **address-token-based access control**。([OSDI '24](https://www.usenix.org/conference/osdi24/presentation/chen-haibo))

> **待核实**：地址空间布局、页表层级、缺页路径的具体实现——论文外无公开源码，**不臆测**。

---

## 3. 第 2 层 · 2B 物理与回收侧（"先踢谁"）

### 3.1 标准系统（Linux）

伙伴系统/Zone/水线、slab、LRU/MGLRU、回收、zram、memcg、PSI —— **全是 Linux 实现**，分别对应 [A03](../foundations/A03-物理页分配.md)、[A04](../foundations/A04-回收总论.md)、[A05](../foundations/A05-冷热识别的演进.md)、[A06](../foundations/A06-压缩与换页.md)、[A07](../foundations/A07-cgroup-memcg.md)、[A08](../foundations/A08-压力与低内存终止.md)。**但具体启用了哪些（MGLRU 是否开、zram 默认参数、是否有自定义 lmkd）属厂商配置，本次未证实，标「待核实」。**

### 3.2 小型系统（LiteOS-A）—— 已据源码坐实

这是本篇最值得纠偏的一层：**RTOS 风格不等于"没有回收"。LiteOS-A 其实有一套精简版的 Linux 式物理页 + LRU + OOM。**

- **物理页管理 = 伙伴系统式**：物理内存切成多个段 `g_vmPhysSeg[]`，每段维护**按阶（order）分级的空闲链 `freeList[VM_LIST_ORDER_MAX]`**——这就是伙伴系统的"按 2 的幂分配/合并"形态，不是 MCU 那种平坦内存池。([`los_vm_phys.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/los_vm_phys.c)) 页帧结构 `LosVmPage`。
- **内核对象分配器 = TLSF**：内核堆（`kmalloc` 位置）用 **TLSF（Two-Level Segregated Fit）** 算法管理（`OsMemPoolHead`），对应 [A03](../foundations/A03-物理页分配.md) 里 slab/slub 的角色。([`tlsf/los_memory.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/mem/tlsf/los_memory.c))
- **页缓存 + 文件页 LRU**：文件页用 `LosFilePage` + 每文件一个 `page_mapping`（带命中/缺失计数），入 LRU 时调 `OsAddToPageacheLru`。LRU 是 **active/inactive 双链**（`VM_LRU_ACTIVE_FILE` / `VM_LRU_INACTIVE_FILE`），可在两链间升降温、判断 inactive 链是否过短——这是 [A05](../foundations/A05-冷热识别的演进.md) 双链 LRU 的极简版。([`los_vm_filemap.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/los_vm_filemap.c)、[`los_vm_scan.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/los_vm_scan.c))
- **回收只回收文件页，没有 swap**：`OsTryShrinkMemory` 沿 LRU 缩页缓存（先从 active 挪到 inactive，再从 inactive 回收）。源码树**无 swap 文件**、scan 只处理 file 链——**匿名页不换出**。这与移动端 Android「zram 换出匿名页」（[A06](../foundations/A06-压缩与换页.md)）形成鲜明对比：内存受限的 LiteOS-A 选择"页缓存丢得起、匿名页丢不起 → 内存不够就杀进程"。
- **低内存终止 = 内核态、阈值式 OOM**：内核常驻一个 `OomTask`（优先级 9，周期默认 **1 s**，可调 0.1–10 s）。`OomCheckProcess` 两级处置：① 空闲内存 < **reclaimMemThreshold（默认 5 MiB）** → `OomForceShrinkMemory` 强制回收页缓存；② 空闲 < **lowMemThreshold（默认 512 KiB，可调 0–1 MiB）** → `OomScoreProcess` 评分 + `OomKillProcess` 杀进程。([`oom.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/oom.c)、[`los_oom.h`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/include/los_oom.h)) — 这更像 Android **早年的内核态 LMK**（阈值 + 评分），而**非** [A08](../foundations/A08-压力与低内存终止.md) 讲的 PSI + 用户态 LMKD；LiteOS-A **没有 PSI、没有用户态守护进程**。

### 3.3 轻量系统（LiteOS-M）

MCU 上**没有伙伴系统、没有 LRU、没有 OOM**——内存管理退化为内存池：

- **静态内存**：预设固定块大小的池，按块分配/释放，无碎片；
- **动态内存**：动态池里按需分配，基于 **TLSF** 分级空闲链降碎片。([LiteOS-M 仓库](https://github.com/openharmony/kernel_liteos_m)、[SegmentFault · 鸿蒙轻内核动态内存](https://segmentfault.com/a/1190000040291540/en))

> MCU 上 TLSF 内存池就是它的"物理页管理 + 内核分配器"二合一。

### 3.4 鸿蒙内核（HarmonyOS NEXT）

- 论文层面：policy-free kernel paging 解耦分页机制与策略。([OSDI '24](https://www.usenix.org/conference/osdi24/presentation/chen-haibo))
- 应用运行时层面：HarmonyOS NEXT 应用用 **ArkTS / 方舟运行时**，堆由 **GC** 管理、宣称有"内存压缩"——但这是**语言运行时（应用层）**的内存管理，与"内核物理页回收"不是一回事，且仅见于二手博客，**未官方/论文证实，标「待核实」**。
- **待核实**：内核态物理回收、低内存杀进程优先级模型、是否用压缩内存/swap——无可靠公开来源，留白。

---

## 4. 第 3 层 · 内存管理硬件

| 基座 | MMU/TLB | IOMMU/SMMU · DMA |
|---|---|---|
| LiteOS-M | **无 MMU**，MPU 段保护 | 待核实 |
| LiteOS-A | **有 MMU**：ARM 短描述符两级页表（[`los_arch_mmu.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/arch/arm/arm/src/los_arch_mmu.c)） | 设备内存/DMA 机制公开少（待核实） |
| 标准系统（Linux） | 标准 ARM64 MMU/TLB，见 [A01 §3.4](../foundations/A01-地址空间与虚实转换.md)；IOMMU/SMMU 见 [A10](../foundations/A10-IOMMU-SMMU与DMA.md) | 同 Linux/A10 |
| HarmonyOS NEXT | 有 MMU（ARM64）；SMMU/SVA 细节待核实 | 待核实 |

硬件层由 **ARM 架构**定义，对带 MMU 的基座行为同 [A01](../foundations/A01-地址空间与虚实转换.md)/[A10](../foundations/A10-IOMMU-SMMU与DMA.md)；差异在**内核如何使用**，而非硬件本身。

---

## 5. 第 4 层 · 存储层级 / 存储 I/O 交界

- **标准系统（Linux）**：page cache、回写、readahead、direct I/O 同 [A11](../foundations/A11-page-cache与回写.md)；默认主力 FS 与回写参数属厂商配置（待核实，不照搬 Android 的 f2fs 结论）。
- **小型系统（LiteOS-A）**：**有 page cache**（`los_vm_filemap.c` 的 `LosFilePage`/`page_mapping`，见 §3.2）与 VFS/文件系统适配；主力 FS 待核实。
- **轻量系统（LiteOS-M）**：MCU，存储/文件系统极简（如 LittleFS 类，待核实），基本无 page cache。
- **HarmonyOS NEXT**：存储栈与 page cache 交界待核实。

---

## 6. 跨平台对照表（HarmonyOS 列回填，区分基座）

> 对照 [00 总览 §6 跨平台术语对照表](../foundations/00-内存系统总览.md)。HarmonyOS 一列必须按基座分写。

| 概念 | Android (Linux) | iOS / Darwin | **HarmonyOS（按基座）** |
|---|---|---|---|
| 内核基座 | Linux（GKI） | XNU | **LiteOS-M / LiteOS-A / Linux（标准）/ 鸿蒙微内核（NEXT）** |
| 页大小 | 4KB（部分 16KB 迁移） | 16KB | LiteOS-A：**4 KiB（已证实）**；标准：随 Linux；NEXT：待核实 |
| 物理内存分配 | 伙伴系统 + slub | XNU zone | LiteOS-A：**伙伴式段+按阶空闲链 + TLSF 堆（已证实）**；LiteOS-M：**TLSF 内存池**；标准：伙伴系统；NEXT：待核实 |
| 冷热 / 回收 | LRU / MGLRU | XNU page queues | LiteOS-A：**active/inactive 文件页 LRU（已证实）**；标准：随 Linux；LiteOS-M：无 |
| 匿名页换出后端 | zram | 压缩内存 | LiteOS-A：**无 swap，匿名页不换出（已证实）**；标准：随 Linux（待核实是否启用 zram）；NEXT：待核实 |
| 低内存杀进程 | LMK→LMKD（PSI） | Jetsam | LiteOS-A：**内核态阈值式 OOM（5MiB 回收 / 512KiB 杀，评分，已证实）**；标准/NEXT：待核实 |
| 用户态分配器 | Scudo | libmalloc | **musl libc（malloc 实现待核实）** |
| 主力文件系统 | f2fs / ext4 | APFS | **待核实** |

---

## 7. 来源与延伸阅读

**LiteOS-A 一手源码锚点**（本篇 §2.2 / §3.2 结论均据此，[openharmony/kernel_liteos_a](https://github.com/openharmony/kernel_liteos_a) 主线）：

- 地址空间 / VMA 等价物 / rbtree：[`kernel/base/include/los_vm_map.h`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/include/los_vm_map.h)
- 页表 / MMU（短描述符两级、1MiB 段 / 4KiB·64KiB 页）：[`arch/arm/arm/include/los_mmu_descriptor_v6.h`](https://github.com/openharmony/kernel_liteos_a/blob/master/arch/arm/arm/include/los_mmu_descriptor_v6.h)、[`arch/arm/arm/src/los_arch_mmu.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/arch/arm/arm/src/los_arch_mmu.c)
- 物理页（多段 + 按阶空闲链）：[`kernel/base/vm/los_vm_phys.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/los_vm_phys.c)
- 文件页 LRU / 回收：[`kernel/base/vm/los_vm_scan.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/los_vm_scan.c)、页缓存 [`kernel/base/vm/los_vm_filemap.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/los_vm_filemap.c)
- 内核 OOM（阈值 5MiB/512KiB、评分杀进程）：[`kernel/base/vm/oom.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/vm/oom.c)、[`kernel/base/include/los_oom.h`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/include/los_oom.h)
- TLSF 堆分配器：[`kernel/base/mem/tlsf/los_memory.c`](https://github.com/openharmony/kernel_liteos_a/blob/master/kernel/base/mem/tlsf/los_memory.c)

**其他来源：**

- OpenHarmony 系统类型与内核映射（轻量=LiteOS-M / 小型=LiteOS-A 或 Linux / 标准=Linux-4.19、5.10；最小内存 128KiB / 128MiB）：[华为开发者联盟](https://developer.huawei.com/consumer/cn/forum/topic/0204729778972140718)
- LiteOS-M 动态内存 TLSF：[github · openharmony/kernel_liteos_m](https://github.com/openharmony/kernel_liteos_m)、[SegmentFault · 鸿蒙轻内核动态内存](https://segmentfault.com/a/1190000040291540/en)
- 鸿蒙微内核（HongMeng / HMKernel）：[USENIX OSDI '24 · Microkernel Goes General](https://www.usenix.org/conference/osdi24/presentation/chen-haibo)

**仍存的「待核实」缺口：**

1. OpenHarmony 标准系统是否启用 MGLRU、zram 默认参数、是否有自定义 lmkd/低内存终止策略。
2. OpenHarmony 用户态 `malloc` 实现（musl mallocng vs 其他）。
3. 各基座主力文件系统及其与 page cache/回写的关系。
4. **HarmonyOS NEXT 鸿蒙内核**的物理回收、低内存杀进程优先级模型、是否用压缩内存/swap——论文外无公开来源。
5. HarmonyOS NEXT 应用层 ArkTS/方舟运行时 GC 与"内存压缩"的具体机制——仅二手博客，且属语言运行时而非内核。
6. LiteOS-M 的 MPU 是否在所有配置下强制启用。

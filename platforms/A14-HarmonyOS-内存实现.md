# A14 · 平台对照 — HarmonyOS / OpenHarmony 内存实现

> **一句话定位**：把 [00 总览](../foundations/00-内存系统总览.md) 的四层骨架，逐格填上 HarmonyOS / OpenHarmony 的实现——但 HarmonyOS 不是"一套内存系统"，而是**三套内核基座**各填各的，必须先分清再对照。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的四层（① 用户态 / ② 内核 2A 地址空间 + 2B 物理回收 / ③ 硬件 / ④ 存储层级）。
> 🧭 **阅读前置**：先读 [00 总览](../foundations/00-内存系统总览.md) 与机制篇 [A01](../foundations/A01-地址空间与虚实转换.md)–[A13](../foundations/A13-内存度量与排障.md)；本篇是**对照型**，凡标准系统复用 Linux 的机制都回链对应 A0X，不重复展开。
> 🌡️ **演进分级**：综合篇。**诚实优先**——HarmonyOS / OpenHarmony 的内存实现细节公开程度差异极大：LiteOS 有完整开源码可查，标准系统就是 Linux，而 HarmonyOS NEXT 的鸿蒙内核仅有论文与官方宣讲层面的信息。**本篇严格区分「已证实（带来源）」与「待核实」，宁可留白不杜撰。**

---

## 0. 写在前面：三套基座，不可混为一谈

"HarmonyOS 的内存是怎么管的"这个问题没有单一答案，因为 **HarmonyOS / OpenHarmony 在不同设备档位上跑的是完全不同的内核**。三套基座的内存子系统差异巨大：

| 基座 | 归属 | 目标设备 / 参考内存 | MMU/MPU | 内存管理特征 | 公开程度 |
|---|---|---|---|---|---|
| **LiteOS-M** | OpenHarmony **轻量系统**（Mini） | MCU（Cortex-M / RISC-V 32 位），最小 **128 KiB** | 无 MMU，**MPU** 隔离（待核实是否必选） | 静态/动态内存池、**TLSF** + bestfit 分配器 | **全开源**（gitee/github 可查码） |
| **LiteOS-A** | OpenHarmony **小型系统**（Small） | MB 级内存设备（Cortex-A） | **有 MMU**（`LOSCFG_KERNEL_MMU`） | 虚拟内存（`LosVmSpace`）、缺页、vmalloc、物理页管理 | **全开源** |
| **Linux** | OpenHarmony **标准系统**（Standard） | 应用处理器（Cortex-A），最小 **128 MiB** | 有 MMU | **就是 Linux 内核**（Linux-4.19 / 5.10），机制同 A0X | 开源（标准 Linux） |
| **鸿蒙内核 HMKernel / HongMeng** | **HarmonyOS NEXT**（HarmonyOS 5，闭源商用） | 手机 / 平板 / 智能路由器 / 车机等 | 有 MMU | 自研**微内核**，policy-free kernel paging、address-token 访问控制 | **仅论文 + 官方宣讲**，源码不公开 |

> 关键区分点：
> - **OpenHarmony**（开源）小型系统可在 **LiteOS-A 或 Linux 之间二选一**；标准系统用 **Linux**。([华为开发者联盟 · OpenHarmony 支持的系统类型与对应内核](https://developer.huawei.com/consumer/cn/forum/topic/0204729778972140718))
> - **HarmonyOS NEXT**（华为闭源商用版，对外称 HarmonyOS 5）用的是华为自研的**鸿蒙微内核（HongMeng / HMKernel）**，已**去掉 Linux 内核与 AOSP 兼容层**——这与 OpenHarmony 标准系统的 Linux 基座是两回事。([USENIX OSDI '24 · Microkernel Goes General](https://www.usenix.org/conference/osdi24/presentation/chen-haibo))

下面沿 00 四层填表，每层都按"哪套基座"分别说明。

---

## 1. 第 1 层 · 用户态

| 子项 | LiteOS-M（轻量） | LiteOS-A（小型） | 标准系统（Linux） | HarmonyOS NEXT（鸿蒙内核） |
|---|---|---|---|---|
| 地址空间布局 | 无独立进程地址空间（单地址空间 + MPU 段保护，**待核实**） | 有独立进程地址空间（`LosVmSpace`），代码/堆/栈/映射区分段 | 标准 Linux VMA 布局，见 [A01](../foundations/A01-地址空间与虚实转换.md) | 微内核 + 用户态服务，地址空间隔离（细节待核实） |
| 用户态分配器 | 内核自带动态内存接口（无独立 libc malloc 层，**待核实**） | musl libc / 标准 `malloc` 之上（**待核实**具体分配器） | musl libc（OpenHarmony 用 musl），`malloc` 实现**待核实** | **待核实**（是否复用 musl / 自研分配器） |
| 内存系统调用 | 无 `mmap`/`brk` 完整语义（裸机式） | 提供类 POSIX 内存接口 + vmalloc | 标准 `mmap`/`brk`/`madvise`，见 [A01](../foundations/A01-地址空间与虚实转换.md) | 论文称兼容 Linux API/ABI，应有等价接口（细节待核实） |

> 说明：OpenHarmony 用户态 C 库为 **musl libc**（标准系统）——这是 OpenHarmony 仓库公开信息；但**具体 `malloc` 走 musl 自带还是 Scudo/jemalloc 等，未在本次检索中证实，标「待核实」**，不照搬 Android 的 Scudo 结论。

---

## 2. 第 2 层 · 内核内存管理 — 2A 地址空间侧（"该映射成什么"）

### 2.1 标准系统（Linux）

**就是 Linux 内核**（OpenHarmony 已适配 Linux-4.19、Linux-5.10）。([华为开发者联盟 · 系统类型与对应内核](https://developer.huawei.com/consumer/cn/forum/topic/0204729778972140718)) 因此 2A 的全部机制——VMA（`vm_area_struct`）、多级页表、缺页、按需分页/COW——**与 [A01](../foundations/A01-地址空间与虚实转换.md)、[A02](../foundations/A02-缺页与按需分页.md) 完全一致**，本篇不重复。注意：4.19/5.10 较旧，**maple tree（6.1）、per-VMA lock（6.4）等新特性不在这两个内核里**——这是与最新 AOSP/GKI 的一个差异点。

### 2.2 小型系统（LiteOS-A）

LiteOS-A **带 MMU**，有真正的进程虚拟内存：

- **地址空间结构**：核心结构在 `kernel/base/include/los_vm_map.h`——进程地址空间 `LosVmSpace`、地址区间 `LosVmMapRegion`、地址范围 `LosVmMapRange`；区间用红黑树组织（类比 Linux 的 VMA）。([华为云社区 · 鸿蒙轻内核 A 核源码分析·虚拟内存](https://www.cnblogs.com/huaweiyun/p/15543256.html))
- **页表**：源码可见一级页表基址 `g_firstPageTable`（大小 `0x4000`）；按公开博客分析为**两级页表**、一级页表项描述 1 MiB 映射（**该"两级/1MiB"细节为二手博客所述，标「待核实」**，核验需查 `arch/arm/arm/mmu.c` 等源码）。MMU 由 `LOSCFG_KERNEL_MMU` 开关控制。([华为云社区](https://www.cnblogs.com/huaweiyun/p/15543256.html)、[OpenHarmony LiteOS-A 仓库 gitee](https://gitee.com/openharmony/kernel_liteos_a))
- **缺页**：访问无物理页映射的虚拟地址触发 page fault，内核申请物理页、填数据、回填页表项——与 [A02](../foundations/A02-缺页与按需分页.md) 的 minor/major 模型同构（但实现是 LiteOS 自有，**非** Linux `mm/memory.c`）。
- **vmalloc vs 普通分配**：普通分配要求**物理连续**、适合小块；**vmalloc** 按页（**4096 字节/页**）申请**物理不连续**内存并建虚实映射，适合大块。([CSDN · OpenHarmony 虚拟内存管理](https://blog.csdn.net/WEZC156465/article/details/143568728))

### 2.3 轻量系统（LiteOS-M）

LiteOS-M 面向 MCU，**无 MMU**，靠 **MPU** 做内存段隔离（MPU 是否在所有配置下启用，**待核实**）。没有"虚拟地址空间/页表/缺页"这套——它是单一物理地址空间上的内存池管理，归到下面 2B 讲。

### 2.4 鸿蒙内核（HarmonyOS NEXT）

公开信息来自 OSDI '24 论文《Microkernel Goes General》：

- 微内核架构，**兼容 Linux API/ABI** 以复用应用与驱动生态；
- 重新设计了传统微内核的若干点，与内存相关的有 **policy-free kernel paging（无策略的内核分页）** 与 **userspace paging 的重新取舍**，以及 **address-token-based access control（基于地址令牌的访问控制）**用于内核对象的协同管理。([USENIX OSDI '24 · Microkernel Goes General（论文页）](https://www.usenix.org/conference/osdi24/presentation/chen-haibo))

> **待核实**：地址空间布局细节、页表层级、缺页路径的具体实现——论文之外无公开源码，**不臆测版本号或数据结构**。

---

## 3. 第 2 层 · 内核内存管理 — 2B 物理与回收侧（"先踢谁"）

### 3.1 标准系统（Linux）

物理页管理（伙伴系统/Zone/水线）、slab/slub、LRU/MGLRU、回收（kswapd/直接/shrinker）、zram、memcg、PSI——**全部是 Linux 实现**，分别对应 [A03](../foundations/A03-物理页分配.md)、[A04](../foundations/A04-回收总论.md)、[A05](../foundations/A05-冷热识别的演进.md)、[A06](../foundations/A06-压缩与换页.md)、[A07](../foundations/A07-cgroup-memcg.md)、[A08](../foundations/A08-压力与低内存终止.md)。**但具体在 OpenHarmony 标准系统里启用了哪些（MGLRU 是否开、zram 默认参数、是否有自定义 LMK/lmkd）属厂商配置，本次未证实，标「待核实」。**

### 3.2 小型系统（LiteOS-A）

- **物理页管理**：有页帧（page）概念与物理页分配（vmalloc 即"申请若干物理页挂双向链表再映射"）。([华为云社区](https://www.cnblogs.com/huaweiyun/p/15543256.html))
- **堆/动态内存分配器**：LiteOS-A 与 LiteOS-M 同源，动态内存基于 **TLSF（Two-Level Segregate Fit）** 算法分区管理，配合 **bestfit（dlink）/ bestfit_little** 风格；目标是降碎片、提分配效率。源码位于 `kernel/base/mem/tlsf/los_memory.c`。([OpenHarmony LiteOS-A · los_memory.c（gitee）](https://gitee.com/openharmony/kernel_liteos_a/blob/master/kernel/base/mem/tlsf/los_memory.c))
- **回收/换页/LMK**：LiteOS 这类 RTOS 风格内核通常**没有** Linux 那套 LRU 冷热回收 + swap + LMKD 体系；是否有简化的低内存处理，**待核实**。

### 3.3 轻量系统（LiteOS-M）

这是 LiteOS 内存管理最"教科书"的一层：

- **静态内存**：初始化时预设固定大小内存块的内存池，按块分配/释放——**无碎片、效率高**，但只能分固定大小。
- **动态内存**：在动态内存池里按需分配任意大小，基于 **TLSF** 算法优化区间划分以降低碎片；空闲块按大小分级挂多条 free list（公开资料给出 [4,127] 等分 + 127 字节以上按 2 的幂递增的分级）。([SegmentFault · 鸿蒙轻内核动态内存详解](https://segmentfault.com/a/1190000040291540/en)、[LiteOS-M 仓库（github）](https://github.com/openharmony/kernel_liteos_m))

> 这与 00 总览的"伙伴系统 + slab"完全不同——MCU 上**没有伙伴系统**，TLSF 内存池就是它的"物理页管理 + 内核分配器"二合一。

### 3.4 鸿蒙内核（HarmonyOS NEXT）

- 论文层面：policy-free kernel paging 把分页策略与机制解耦（机制在内核、策略可下放）。([OSDI '24](https://www.usenix.org/conference/osdi24/presentation/chen-haibo))
- **应用运行时层面**：HarmonyOS NEXT 应用用 **ArkTS / 方舟（Ark）运行时**，堆内存由 **GC（垃圾回收）** 管理，并宣称有**内存压缩**等手段——但这些是**语言运行时的内存管理**（应用层），与"内核物理页回收"不是一回事，且本次仅见于**二手技术博客**，**未在官方/论文中逐条证实，标「待核实」**，不写入具体机制名。
- **待核实**：内核态的物理内存回收、低内存杀进程（是否有类 LMKD/Jetsam 的优先级模型）、是否用压缩内存/swap——**无可靠公开来源，留白**。

---

## 4. 第 3 层 · 内存管理硬件

| 基座 | MMU/TLB | IOMMU/SMMU · DMA |
|---|---|---|
| LiteOS-M | **无 MMU**，MPU 段保护 | 待核实 |
| LiteOS-A | **有 MMU**（ARM，`LOSCFG_KERNEL_MMU`），硬件页表遍历同 ARM 架构 | 待核实（设备内存/DMA 机制公开少） |
| 标准系统（Linux） | 标准 ARM64 MMU/TLB，见 [A01 §3.4](../foundations/A01-地址空间与虚实转换.md)；IOMMU/SMMU 见 [A10](../foundations/A10-IOMMU-SMMU与DMA.md) | 同 Linux/A10 |
| HarmonyOS NEXT | 有 MMU（ARM64）；SMMU/SVA 细节待核实 | 待核实 |

硬件层（MMU/TLB/SMMU/内存控制器）本质由 **ARM 架构**定义，对带 MMU 的基座而言行为与 [A01](../foundations/A01-地址空间与虚实转换.md)/[A10](../foundations/A10-IOMMU-SMMU与DMA.md) 所述一致；差异在**内核如何使用**，而非硬件本身。

---

## 5. 第 4 层 · 存储层级 / 存储 I/O 交界

- **标准系统（Linux）**：page cache、回写、readahead、direct I/O 等交界机制同 [A11](../foundations/A11-page-cache与回写.md)。文件系统层 OpenHarmony 公开资料提到对多种 FS 的支持，**默认主力 FS 与对 page cache/回写的影响本次未证实，标「待核实」**（不照搬 Android 的 f2fs 结论）。
- **小型系统（LiteOS-A）**：有 VFS 与文件系统适配，但是否有 Linux 式 page cache/回写体系，**待核实**。
- **轻量系统（LiteOS-M）**：MCU 场景，存储/文件系统极简（如 LittleFS 类，**待核实**），基本无 page cache 概念。
- **HarmonyOS NEXT**：存储栈与 page cache 交界细节**待核实**。

---

## 6. 跨平台对照表（HarmonyOS 列回填，区分基座）

> 对照 [00 总览 §6 跨平台术语对照表](../foundations/00-内存系统总览.md)。HarmonyOS 一列必须按基座分写，否则会误导。

| 概念 | Android (Linux) | iOS / Darwin | **HarmonyOS（按基座）** |
|---|---|---|---|
| 内核基座 | Linux（GKI） | XNU | **LiteOS-M（轻量）/ LiteOS-A（小型）/ Linux（标准）/ 鸿蒙微内核（NEXT）** |
| 页大小 | 4KB（部分 16KB 迁移） | 16KB | LiteOS-A：4096B（已证实）；标准系统：随 Linux；NEXT：待核实 |
| 物理内存分配 | 伙伴系统 + slub | XNU zone | LiteOS：**TLSF 内存池**（已证实）；标准系统：伙伴系统；NEXT：待核实 |
| 低内存杀进程 | LMK→LMKD（PSI） | Jetsam | **待核实**（各基座是否有等价机制均未证实） |
| 匿名页换出后端 | zram | 压缩内存 | 标准系统随 Linux（待核实是否启用 zram）；LiteOS：通常无；NEXT：待核实 |
| 用户态分配器 | Scudo | libmalloc | **待核实**（OpenHarmony 用 musl libc，malloc 实现未证实） |
| 主力文件系统 | f2fs / ext4 | APFS | **待核实** |

---

## 7. 来源与延伸阅读

**已检索/打开并据以下结论的来源：**

- OpenHarmony 系统类型与对应内核（轻量=LiteOS-M / 小型=LiteOS-A 或 Linux / 标准=Linux-4.19、5.10；最小内存 128KiB / 128MiB）：[华为开发者联盟 · OpenHarmony 支持的系统类型以及对应的内核](https://developer.huawei.com/consumer/cn/forum/topic/0204729778972140718)
- LiteOS-A 虚拟内存（`LosVmSpace`/`LosVmMapRegion`、MMU、缺页、vmalloc）：[华为云社区 · 鸿蒙轻内核 A 核源码分析·虚拟内存](https://www.cnblogs.com/huaweiyun/p/15543256.html)、[CSDN · OpenHarmony 虚拟内存管理（4096B 页、vmalloc 物理不连续）](https://blog.csdn.net/WEZC156465/article/details/143568728)
- LiteOS-A/M 动态内存 TLSF + bestfit：[OpenHarmony LiteOS-A · `kernel/base/mem/tlsf/los_memory.c`（gitee）](https://gitee.com/openharmony/kernel_liteos_a/blob/master/kernel/base/mem/tlsf/los_memory.c)、[SegmentFault · 鸿蒙轻内核动态内存详解](https://segmentfault.com/a/1190000040291540/en)
- LiteOS-M 仓库（MCU、资源极小设备）：[github · openharmony/kernel_liteos_m](https://github.com/openharmony/kernel_liteos_m)
- LiteOS-A 仓库：[gitee · openharmony/kernel_liteos_a](https://gitee.com/openharmony/kernel_liteos_a)
- 鸿蒙微内核（HongMeng / HMKernel，微内核、兼容 Linux API/ABI、policy-free kernel paging、address-token 访问控制、部署于智能路由器/车机/手机）：[USENIX OSDI '24 · Microkernel Goes General: Performance and Compatibility in the HongMeng Production Microkernel](https://www.usenix.org/conference/osdi24/presentation/chen-haibo)

**源码锚点（供进一步核验）：** `kernel/base/include/los_vm_map.h`（地址空间结构）、`kernel/base/mem/tlsf/los_memory.c`（TLSF 分配器）、`arch/arm/arm/mmu.c`（页表/MMU，待查证两级/1MiB 说法）。

**明确的「待核实」缺口（公开资料不足，未写入确定结论）：**

1. LiteOS-A 页表级数与"一级项 1MiB"——仅二手博客所述，需源码核验。
2. LiteOS-M 的 MPU 是否在所有配置下强制启用。
3. OpenHarmony 标准系统是否启用 MGLRU、zram 默认参数、是否有自定义 lmkd/低内存终止策略。
4. OpenHarmony 用户态 `malloc` 实现（musl 自带 vs 其他）。
5. 各基座主力文件系统及其与 page cache/回写的关系。
6. **HarmonyOS NEXT 鸿蒙内核**的物理内存回收、低内存杀进程优先级模型、是否用压缩内存/swap——论文外无公开来源。
7. HarmonyOS NEXT 应用层 ArkTS/方舟运行时的 GC 与"内存压缩"具体机制——仅见二手博客，未官方/论文证实，且属语言运行时而非内核。

# A14 · 平台对照 — Android 内存实现

> **一句话定位**：把 [00 总览](../foundations/00-内存系统总览.md) 的四层骨架（① 用户态 / ② 2A 地址空间侧 / ② 2B 物理与回收侧 / ③ 硬件 / ④ 存储 + 邻接 I/O 栈）逐格填上 **Android 的具体实现**——它本质是「**LTS Linux 内核 + GKI + 厂商模块**」之上叠 ART/Zygote/LMKD/dma-buf 这套 Android 特有的用户态与 HAL 机制。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的全部四层 + 2A/2B + 邻接 I/O 栈；本篇是「平台对照」篇的 Android 卷，每格回链到对应机制篇（A01–A13）。
> 🧭 **阅读前置**：先读 [00 总览](../foundations/00-内存系统总览.md) 建立骨架；机制细节去各 A 篇深潜，本篇只做「Android 用什么实现 + 来源 + 指向哪篇」。
> 🌡️ **演进分级**：**综合**——既覆盖稳定项（伙伴系统、缺页、page cache），也覆盖 Android 正在快速演进的热点（MGLRU、dma-buf heaps、16KB 页、cgroup v2 迁移、GKI 主线）。

---

## 1. 定位：Android 的内存栈 = Linux 内核 + Android 用户态

Android 不是「另起炉灶的内存系统」，而是**直接复用 Linux 内核的内存管理**（缺页、伙伴系统、回收、page cache 全是上游 `mm/` 的代码），再在两端做 Android 化改造：

- **下层（内核）**：通过 **GKI**（Generic Kernel Image，见 §7）把上游 LTS 内核标准化，并默认开启一批移动端关键特性（zram、MGLRU、PSI、dma-buf heaps）。
- **上层（用户态 / HAL）**：用 **ART/Zygote**（应用运行时与孵化器）、**LMKD**（用户态低内存终止）、**gralloc/dma-buf heaps**（图形与多媒体缓冲）等 Android 专有组件，接管「分配、共享、回收决策、设备内存」。

因此本篇的读法是：**内核机制照搬 Linux（回链 A01–A13），Android 的「差异点」集中在用户态策略和 GKI 默认开关上**。下面逐层填表。

## 2. 第 1 层 · 用户态

| 子项 | Android 实现 | 对应机制篇 |
|---|---|---|
| 用户态分配器 | **Scudo**：自 **Android 11** 起取代 jemalloc，成为所有原生代码的默认分配器（低内存设备仍用 jemalloc）。Scudo 是「强化型」分配器，按大小隔离分配、降低分配模式可预测性以抗堆破坏，并集成 GWP-ASan 做线上内存安全检测。 | [A01 地址空间与虚实转换](../foundations/A01-地址空间与虚实转换.md) §3.5 |
| 进程地址空间 / 孵化机制 | **Zygote**：所有 App 进程从 Zygote `fork` 而来，**COW 共享**预加载的框架类、资源与 ART 堆——已初始化的只读页跨进程共享，写时才复制，大幅降低每个 App 的常驻内存与启动开销。 | [A02 缺页与按需分页](../foundations/A02-缺页与按需分页.md) |
| 运行时堆（ART） | **ART**（Android Runtime）管理托管堆：分代 / 并发回收，并大量用 **`madvise`** 把意图直达内核回收侧——典型如对已编译/已映射但暂不用的区间下 `MADV_DONTNEED`（解映射、立即还页）、对冷区间下 `MADV_COLD`/`MADV_PAGEOUT`（推入回收）。 | [A04 回收总论](../foundations/A04-回收总论.md)、[A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md) |
| 内存系统调用 | 标准 Linux 接口：`mmap`/`munmap`/`mprotect`/`mlock`，以及 Android 路径里高频的 **`madvise`**（`DONTNEED`/`FREE`/`COLD`/`PAGEOUT`）。`ashmem`（匿名共享内存）历史上用于跨进程共享，新代码逐步转向 `memfd`/dma-buf。 | [A01](../foundations/A01-地址空间与虚实转换.md)、[A04](../foundations/A04-回收总论.md) |
| 内存度量 | `dumpsys meminfo`（PSS 视角的 App 占用）、`/proc/<pid>/smaps`、`procrank`、`/proc/meminfo`；PSS（按比例摊分共享页）是 Android 衡量「一个 App 到底占多少」的核心口径。 | [A13 内存度量与排障](../foundations/A13-内存度量与排障.md) |

> **Android 化要点**：Scudo（安全优先的默认分配器）与 Zygote 的 COW 共享（启动与内存双优化）是用户态最具 Android 特色的两点；二者都站在 Linux 的 `mmap`/`fork`/缺页机制之上。

## 3. 第 2 层 · 2A 地址空间侧（"该映射成什么"）

| 子项 | Android 实现 | 对应机制篇 |
|---|---|---|
| VMA 管理 | 沿用上游：Linux 6.1 起 VMA 存储改为 **maple tree**（区间友好、RCU 读友好）。Android 通过 **GKI**（`android14-6.1` 等分支）把这套带进设备内核。 | [A01](../foundations/A01-地址空间与虚实转换.md) §3.2 |
| 地址空间并发 | **per-VMA lock**（Linux 6.4 起）：把进程级 `mmap_lock` 细化到单个 VMA，缺页吞吐显著提升，**直接利好多线程 App 启动**——这是 Android 的典型受益场景。随 GKI 内核版本（如 `android14-6.1`）下放到设备。 | [A01](../foundations/A01-地址空间与虚实转换.md) §3.2、§6 |
| 页表 PGD~PTE | ARM64 多级页表（4KB 粒度常见为四级），用户 `TTBR0_EL1` / 内核 `TTBR1_EL1`。格式由硬件定义、内核 `arch/arm64/mm/` 管理。16KB 页配置见 §6 硬件层。 | [A01](../foundations/A01-地址空间与虚实转换.md) §3.3、[A12 大页与页粒度](../foundations/A12-大页与页粒度.md) |
| 缺页 / 按需分页 / COW | 标准 Linux 缺页（minor/major）；Android 的高频场景是 **Zygote `fork` 后的 COW**、以及 APK/dex/.so 文件页的 mmap 缺页（多 App 共享同一只读文件页）。 | [A02](../foundations/A02-缺页与按需分页.md) |

## 4. 第 2 层 · 2B 物理与回收侧（"先踢谁"）

这是 Android 差异最密集的一层——移动端对内存压力极敏感，Google 在回收、压缩、终止三条线上都做了强化，并通过 GKI 默认开启。

| 子项 | Android 实现 | 对应机制篇 |
|---|---|---|
| 物理页管理 | 上游**伙伴系统** + Zone + 水线（watermark），`mm/page_alloc.c`。为图形/多媒体的物理连续需求保留 **CMA**（连续内存分配器）。 | [A03 物理页分配](../foundations/A03-物理页分配.md)、[A09 设备内存全景](../foundations/A09-设备内存全景.md) |
| LRU / 冷热识别 | **MGLRU**（多代 LRU）：**Android 14 的 GKI 内核（`android14-5.15` 与 `android14-6.1`）默认启用**；**Pixel 8 系列是首批默认开启 MGLRU 的 Android 机型**（其内核基于 `android14-5.15` GKI）。Google 基准显示 MGLRU 降低 App 启动时间、减少后台进程被杀、大幅降低 kswapd CPU。 | [A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md) |
| 回收 | 上游 `kswapd` / 直接回收 / shrinker / 回写；触发源为水线 / 分配失败 / PSI / memcg 超限。移动端**几乎不向磁盘换匿名页**，而是走 zram（见下）。 | [A04 回收总论](../foundations/A04-回收总论.md) |
| 换页（匿名页后端） | **zram**：现代 Android 默认启用，把换出的匿名页**压缩后仍留在 RAM**（不落盘到闪存，避免磨损 + I/O 延迟）。是「移动端可见 swap」的实际形态。 | [A06 压缩与换页](../foundations/A06-压缩与换页.md) |
| 资源隔离 / 限额（memcg） | **cgroup memcg**：Android 用 cgroup 给前台/后台 App 分组做内存统计与限额，并有「cgroup 抽象层」统一描述挂载点。当前处于 **v1 → v2（unified hierarchy）迁移**中：AOSP 同时支持 cgroup v1 与 v2，配置层做了抽象以平滑过渡。 | [A07 cgroup / memcg](../foundations/A07-cgroup-memcg.md) |
| 压力与低内存终止 | **LMKD**（low memory killer daemon，**用户态**守护进程）：取代旧的内核态 LMK。**自 Android 10 起默认以 PSI 模式运行**（`ro.lmk.use_psi` 默认 `true`），用内核 **PSI**（pressure stall information）监视器感知停顿，按 App 优先级（oom_adj/进程状态）杀后台进程；内核 OOM Killer 兜底。 | [A08 压力与低内存终止](../foundations/A08-压力与低内存终止.md) |
| 设备 / 驱动内存（dma-buf / gralloc） | **dma-buf heaps**：自 **Android 12（GKI 2.0）** 取代 **ION**（`android12-5.10` 分支于 2021-03-01 关闭 `CONFIG_ION`）。改进点：每个 heap 是独立字符设备、可用 sepolicy 单独授权（安全）；IOCTL 接口由上游内核维护、**ABI 稳定**；UAPI 标准化。**gralloc**（HAL）则负责分配/描述图形缓冲（GraphicBuffer），底层经 dma-buf 共享给 GPU/显示/相机。 | [A09 设备内存全景](../foundations/A09-设备内存全景.md)、[A10 IOMMU/SMMU 与 DMA](../foundations/A10-IOMMU-SMMU与DMA.md) |
| 共享与去重 | `ashmem`（旧）/ `memfd` / **dma-buf**（跨进程、跨设备共享缓冲）；图形栈的 GraphicBuffer 跨进程即靠 dma-buf 句柄传递。 | [A09](../foundations/A09-设备内存全景.md)、[A13](../foundations/A13-内存度量与排障.md) |

> **2B 的 Android 三件套**：**zram**（不落盘的压缩换页）+ **MGLRU**（更准的冷热识别）+ **LMKD/PSI**（用户态、压力驱动的杀后台）——三者协同回答「内存紧张时，先压缩、再精准选页、最后按优先级杀谁」。

## 5. 第 3 层 · 内存管理硬件

| 子项 | Android 实现 | 对应机制篇 |
|---|---|---|
| MMU / TLB | ARM64 **MMU**：按 `TTBRx_EL1` 遍历多级页表，TLB 缓存翻译，ASID 标签化避免进程切换整表刷新，`TLBI` 广播失效。 | [A01](../foundations/A01-地址空间与虚实转换.md) §3.4 |
| 页粒度 / 16KB 页 | 传统 4KB；**Android 15 起系统「页大小无关」（page-size-agnostic），支持设备以 16KB 页运行**（许多 ARM CPU 支持 16KB，TLB 覆盖更大、性能更优）。Google Play 自 2025-11-01 起要求面向 Android 15+ 的新应用/更新支持 16KB（64 位设备）。 | [A12 大页与页粒度](../foundations/A12-大页与页粒度.md) |
| IOMMU / SMMU · DMA | ARM **SMMU**（System MMU）为 GPU/相机/编解码等外设做设备地址转换与隔离；与 dma-buf/CMA 配合给外设提供可寻址缓冲。 | [A10 IOMMU/SMMU 与 DMA](../foundations/A10-IOMMU-SMMU与DMA.md) |
| 内存控制器 · DRAM | LPDDR（移动端低功耗 DRAM），由 SoC 内存控制器调度——属硬件，AOSP 不直接管理。 | [00 总览](../foundations/00-内存系统总览.md) §第3层 |

## 6. 第 4 层 · 存储层级与邻接 I/O 栈

| 子项 | Android 实现 | 对应机制篇 |
|---|---|---|
| 主力文件系统 | **f2fs**（Flash-Friendly FS，多数现代 Android 数据分区）与 **ext4**；元数据加密、fsverity 等在其上。FS 内部实现属范围外，**交界（page cache 供页/回写）属内存话题**。 | [A11 page cache 与回写](../foundations/A11-page-cache与回写.md) |
| page cache / 回写 | 上游 `mm/filemap.c`：buffered 读写、readahead、脏页回写；已 **folio 化**（以 folio 而非单 page 为单位管理，利好大页与批量操作）。APK/dex/.so 的 mmap 缺页即从这里取文件页。 | [A11 page cache 与回写](../foundations/A11-page-cache与回写.md)、[A12](../foundations/A12-大页与页粒度.md) |
| 持久后端 | **UFS**（高端）/ eMMC（入门），经块层落盘。匿名页**不**走这里（走 zram 留在 RAM）；只有文件脏页回写、direct I/O 触达存储栈。 | [A11](../foundations/A11-page-cache与回写.md)、[00 总览](../foundations/00-内存系统总览.md) §第4层 |

## 7. 贯穿主线 · GKI（Generic Kernel Image）

GKI 是理解「为什么 Android 内核既是上游 Linux、又处处带 Android 默认开关」的钥匙：

- **是什么**：GKI 把核心内核统一成「**单一内核二进制 + 每架构每 LTS 一份**」，并把 SoC/板级代码从核心内核移到**可加载的厂商模块（vendor modules）**。核心内核来自 **ACK**（Android Common Kernel），ACK 又跟踪上游 **LTS Linux**。
- **解决什么**：GKI 之前，各 SoC 厂商/OEM 在 ACK 上大改，多达约 50% 是 out-of-tree 代码，碎片化严重、安全更新难下发。
- **KMI（稳定模块接口）**：GKI 对厂商模块暴露**稳定的 Kernel Module Interface**，使内核与驱动可分别更新——同一 LTS 内 KMI 保持稳定。
- **强制时点**：**自 Android 12 起，出厂内核版本 ≥ 5.10 的设备必须用 GKI 内核**。
- **与本篇的关系**：前文那些「Android 14 默认 MGLRU」「Android 12 改 dma-buf heaps」「maple tree/per-VMA lock 随 `android14-6.1` 下放」——**承载这些默认值与版本节点的正是 GKI 分支**（`android12-5.10`、`android14-5.15`、`android14-6.1` 等命名即 GKI 约定）。

一句话：**Android 内核 = LTS Linux（ACK 跟踪）+ GKI（统一核心 + 稳定 KMI + 移动端默认开关）+ 厂商模块（SoC/板级）**。

## 8. 跨平台术语提醒（避免与 iOS/HarmonyOS 混用）

本篇术语严格属 **Android/Linux 阵营**。对照时注意区分（详见 [00 总览](../foundations/00-内存系统总览.md) §6 术语表）：

| 概念 | Android（本篇） | 勿混为 |
|---|---|---|
| 低内存杀进程 | **LMKD**（用户态，PSI 驱动）+ 内核 OOM 兜底 | iOS 的 **Jetsam**（memorystatus） |
| 匿名页换出后端 | **zram**（压缩留 RAM，不落盘） | iOS 的 **compressed memory**（compressor） |
| 用户态分配器 | **Scudo**（11+） | iOS 的 **libmalloc**（nano/magazine） |
| 设备图形缓冲 | **gralloc + dma-buf heaps**（原 ION） | 各平台自有图形内存模型 |
| 页大小 | 4KB / 16KB（15+ 支持） | Apple 芯片**固定 16KB** |

## 9. 来源与延伸阅读

> 已检索/打开并据以撰写的来源（AOSP / Android Developers / android.googlesource.com 优先）：

- **Scudo（Android 11 默认）**：[Scudo (AOSP)](https://source.android.com/docs/security/test/scudo)、[System hardening in Android 11 (Android Developers Blog)](https://android-developers.googleblog.com/2020/06/system-hardening-in-android-11.html)、[Scudo Hardened Allocator (LLVM)](https://llvm.org/docs/ScudoHardenedAllocator.html)
- **MGLRU（Android 14 GKI 默认、Pixel 8 首批）**：[Multi-Gen LRU (kernel.org Documentation)](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)、[kernel/common GKI 提交（MGLRU 默认开启）](https://android.googlesource.com/kernel/common/+/e0f24fb5c654ae62356d3eb7d1fd265f9abb83f2)
- **LMKD / PSI（Android 10 默认 PSI）**：[Low memory killer daemon (AOSP)](https://source.android.com/docs/core/perf/lmkd)、[lmkd README (android.googlesource.com)](https://android.googlesource.com/platform/system/memory/lmkd/+/master/README.md)
- **ION → dma-buf heaps（Android 12 / GKI 2.0）**：[Transition from ION to DMA-BUF heaps (AOSP)](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)、[Implement DMABUF and GPU memory accounting in Android 12 (AOSP)](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem)
- **16KB 页（Android 15）**：[Support 16 KB page sizes (Android Developers)](https://developer.android.com/guide/practices/page-sizes)、[16 KB page size (AOSP)](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)、[Prepare apps for 16 KB page size (Android Developers Blog)](https://android-developers.googleblog.com/2025/05/prepare-play-apps-for-devices-with-16kb-page-size.html)
- **GKI 模型**：[Generic Kernel Image (GKI) project (AOSP)](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)、[Kernel modules overview (AOSP)](https://source.android.com/docs/core/architecture/kernel/modules)
- **cgroup / memcg（v1→v2）**：[Cgroup abstraction layer (AOSP)](https://source.android.com/docs/core/perf/cgroups)
- **VMA / per-VMA lock（随 GKI 下放）**：[Introducing the Maple Tree (LWN)](https://lwn.net/Articles/845507/)、[Per-VMA locks (LWN)](https://lwn.net/Articles/924572/)、[Linux 6.4 (kernelnewbies)](https://kernelnewbies.org/Linux_6.4)

> **待核实 / 待补**：
> - **zram 默认与「不落盘」**：现代 Android 默认启用 zram 在业界与 AOSP 多处可证，但本次未直接打开 source.android.com 上独立的 zram/swap 默认值条款，精确措辞**（待核实）**；RAM+/RAM 扩展类机型可能另配磁盘 swap，需逐机型确认。
> - **ART `madvise` 具体 `MADV_*` 调用点**：方向（DONTNEED/COLD/PAGEOUT）可证，但每个调用的精确源码锚点（ART/Zygote 哪个文件）**（待核实）**，应回到 `art/` 源码核对。
> - **per-VMA lock / maple tree 在各 GKI 分支与机型的启用版本**：随 `android14-6.1` 等内核进入，但「哪些出货机型实际跑 6.1 GKI」需按机型内核版本核对**（待核实）**。
> - **cgroup v2 迁移的完成度**：AOSP 同时支持 v1/v2，但「默认挂哪套、memcg 控制器迁移到何种程度」随版本变化，需对照具体 Android 版本**（待核实）**。

# A14 · 平台对照 — iOS / Darwin (XNU) 内存实现

> **一句话定位**：把 [00 总览](../foundations/00-内存系统总览.md) 的四层骨架，逐格填上 **iOS / Darwin（XNU 内核）** 的真实实现——并在每一格点明"它对应 Linux 的哪个机制、但实现与术语不同"，避免把 Mach VM 的概念误读成 Linux mm。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的四层 + 2A/2B 划分 + 存储交界，本篇按 iOS 实现逐层对照。
> 🧭 **阅读前置**：建议先读机制篇 [A01 地址空间](../foundations/A01-地址空间与虚实转换.md)、[A06 压缩与换页](../foundations/A06-压缩与换页.md)、[A08 压力与低内存终止](../foundations/A08-压力与低内存终止.md)、[A10 IOMMU/SMMU](../foundations/A10-IOMMU-SMMU与DMA.md)、[A11 page cache](../foundations/A11-page-cache与回写.md)、[A12 大页与页粒度](../foundations/A12-大页与页粒度.md)——本篇是这些篇在 iOS 平台上的"落地对照"。
> 🌡️ **演进分级**：综合对照篇（模板一·对照填表）。重点不在展开机制本体，而在**跨平台映射**与**术语区分**。

---

## 0. 怎么读这一篇（术语红线）

Darwin 的内存子系统出身 **Mach + BSD**，与 Linux 是**两套独立血统**：概念大体对得上（地址空间、缺页、回收、低内存杀进程都有），但**数据结构与名词几乎全不一样**。本篇所有对照都遵守一条红线——**不把 XNU 的东西叫成 Linux 的名字**：

| 概念层面 | Linux 术语 | iOS / Darwin (XNU) 术语 | 一句话差别 |
|---|---|---|---|
| 地址空间描述 | `vm_area_struct`（VMA）+ maple tree | **`vm_map` / `vm_map_entry`** | XNU 是有序链表 / 红黑树，不是 maple tree |
| 后备对象 | 文件 / 匿名 inode + page | **`vm_object` + pager（memory object）** | XNU 用 pager 抽象后备存储 |
| 冷热与回收 | LRU 链 + `kswapd` | **page queues + `vm_pageout` 线程** | 不叫 LRU、不叫 kswapd |
| 匿名页去处 | swap / **zram** | **VM compressor（压缩内存）** | iOS 基本不落盘 swap |
| 低内存杀进程 | LMK → **LMKD**（用户态） | **Jetsam / memorystatus**（内核态） | iOS 在内核内裁决 |
| 资源分组限额 | **cgroup / memcg** | 无 cgroup，用 **jetsam 优先级带** 代替 | 见 §7 |
| 文件页缓存 | page cache（file LRU） | **UBC（Unified Buffer Cache）** | 同一物理页池，但叫 UBC |
| 设备地址转换 | IOMMU / **SMMU** | **DART**（Apple 自研 IOMMU） | 自研，非 ARM SMMU |

> 写作底层依据：XNU 自身开源（[apple-oss-distributions/xnu](https://github.com/apple-oss-distributions/xnu)，含 `doc/vm/` 设计文档）、Apple 归档的内核编程指南、以及 newosxbook 等公开技术资料；拿不准处标「（待核实）」。

## 1. 第 1 层 · 用户态：libmalloc

iOS / macOS 的标准 C 分配器是 **libmalloc**（[apple-oss-distributions/libmalloc](https://github.com/apple-oss-distributions/libmalloc)），它是一套 **zone（分配区）** 架构：按申请尺寸路由到不同的专用分配器。对照 Linux 一侧（Android 默认 **Scudo**，见 [A01 §3.5](../foundations/A01-地址空间与虚实转换.md)）——**概念对应（都是"向内核要大块、用户态切小块复用"的 malloc），实现完全不同**：

- **Nano allocator**：处理 **≤256 字节**的极小分配（仅 64 位平台）。新的 **Nano V2** 用"region → arena → 16KB block → size-class slot"的层级结构切分。
- **Magazine allocators**（Tiny / Small / Medium）：尺寸分级、**借鉴 Hoard 分配器**的 magazine 设计，为多线程提供 per-CPU/per-magazine 的低争用快路径。
- **Scalable zone**：作为核心分配区按尺寸类别路由，提供可扩展的多线程性能。
- 大分配直接走 `vm_allocate` 向 Mach VM 要页（对应 Linux 的 `mmap` 大块路径）。

来源：[libmalloc · DeepWiki（Allocator Implementations）](https://deepwiki.com/apple-oss-distributions/libmalloc/3-allocator-implementations)、[Playing with Libmalloc in 2024（Blackwing）](https://blackwinghq.com/blog/posts/playing-with-libmalloc/)。

> **对照小结**：Linux 用 `brk`/`mmap` + Scudo/jemalloc；iOS 用 `vm_allocate`/`mmap` + libmalloc 的 nano/magazine/scalable 分层。术语别混：iOS 这边没有"scudo""arena（glibc 含义）"。

## 2. 第 2 层 · 2A 地址空间侧：Mach VM（vm_map / vm_object / vm_page）+ 16KB 页

这是与 Linux **差异最大**的一层。XNU 的地址空间不用 `vm_area_struct`，而是 **Mach VM 三件套**（[Apple 内核编程指南 · Memory and Virtual Memory](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/vm/vm.html)）：

| Mach VM 对象 | 职责 | 对应 Linux |
|---|---|---|
| **`vm_map`** | 每个 Mach task 一个地址空间，组织为**有序结构**（经典实现为双向链表，现代 XNU 为红黑树） | 对应 `mm_struct` + VMA 集合 |
| **`vm_map_entry`** | 描述一段连续映射：起止、当前/最大保护位（`protection`/`max_protection`）、继承方式、是否 submap、是否共享 pmap | 对应单个 `vm_area_struct`（VMA） |
| **`vm_object`** | 可缓存资源的机器无关表示，挂一组驻留页，并经 **memory object** 关联到 **pager** | 对应 VMA 的后备（file/anon inode） |
| **pager**（default / vnode / device） | 负责与后备存储交换数据；**vnode pager** 做文件 mmap，**default pager** 管匿名页后备 | 对应 Linux 的 address_space / 匿名 swap 后备 |
| **`pmap`** | 机器相关的页表层（ARM64 多级页表） | 对应 Linux 的 arch 页表层 |

几个**必须点明的术语对应、实现不同**：

- **COW**：XNU 用 **shadow object（影子对象）链**实现写时复制——`fork` 后子对象空、引用父对象，写时把页复制进影子对象；Mach 会自动 GC 中间影子对象。对照 Linux 的 COW（PTE 标只读、写触发缺页复制）——**概念对应、机制不同**（[Apple VM 指南](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/vm/vm.html)）。
- **缺页与预取**：XNU 缺页经 pager 取页，并用 **working set detection** 做按应用 profile 的预取（早年落到 `/var/vm/app_profile`），对照 Linux 的 readahead——目的相同、实现不同。
- **页操作的内核抽象**：XNU 用 **UPL（Universal Page List）** 在 VM 对象与 pager 之间批量搬页，对照 Linux 的 `struct page`/folio 批操作。

### 16KB 页（Apple 芯片默认）

**Apple 芯片（Apple silicon）的硬件页粒度默认为 16KB**，而非 Linux 移动端常见的 4KB（Intel Mac 仍是 4KB）。这条线索的机制展开见 [A12 §3.4](../foundations/A12-大页与页粒度.md)：更大的基页 = 页表更浅、单个 PTE 覆盖更大、**TLB 覆盖率成倍提升**、缺页次数下降。Apple 官方反复强调应用**绝不能硬编码页大小**，要用 `getpagesize()` / `vm_page_size` / `host_page_size` 运行期取值（[page_size · Apple Developer](https://developer.apple.com/documentation/kernel/page_size)、[host_page_size · Apple Developer](https://developer.apple.com/documentation/kernel/1502512-host_page_size)）。

> **对照小结**：Linux 的"VMA + 页表 + 4KB"在 iOS 对应"`vm_map_entry` + `pmap` + **16KB**"。同样是"该映射成什么 vs 当前实际映射"（[A01](../foundations/A01-地址空间与虚实转换.md) 的 2A 划分），但 XNU 多了一层 `vm_object`/pager 抽象。

## 3. 第 2 层 · 2B 物理与回收侧：page queues + pageout + VM compressor

XNU 的物理页回收**不叫 LRU、不叫 kswapd**。回收由内核线程 **`vm_pageout`**（pageout_scan）驱动，它在若干 **page queues** 上选 victim（[xnu/doc/vm/pageout_scan.md](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/pageout_scan.md)）：

| XNU page queue | 含义 | 对应 Linux LRU 概念 |
|---|---|---|
| **active** | 正在使用的页 | active LRU |
| **inactive** | 被降级的页（含 anonymous 子队列：降级的匿名页） | inactive LRU（anon/file） |
| **speculative** | 预读产生、**从未被激活过**的文件页 | readahead 后的 inactive file |
| **cleaned** | 已写回后备、可回收的文件页 | 干净 file 页 |
| **throttled** | 因 compressor 队列满而被限流的页 | 无直接对应（回收背压） |
| **secluded** | 预留页池（如相机），溢出时推到 active | 无直接对应 |

`pageout_scan` 的要点（对照 Linux `vmscan.c`）：分阶段循环、周期性让锁、按 flow control 状态判断是否偏向文件页；历史上偏好 **"2 个匿名页换 1 个文件页"** 的回收比例（反映 reaccess 代价的经验假设）；脏匿名页放到 **compressor pageout 队列**、脏文件页放到 **external 队列**清洗后再回收。

### VM compressor（压缩内存）—— 对应 Linux 的 zram，但无传统磁盘 swap

这是 iOS 回收侧的**标志性机制**，也是最容易被误称为"swap"的地方。XNU 把要换出的匿名页**就地压缩进内核内的压缩池**，而不是写盘：

- **压缩算法**：自适应混合方案——profitable 时用 **WKdm**（16 项小字典、约 2:1、极快），其余用 **LZ4 变体**。Apple 芯片甚至有定制 ARM 指令 `wkdmc`/`wkdmd` 直接加速压缩/解压；输入恒为 1 个 VM page、`wkdmd` 解压恒好为 1 个 VM page（[vm_compressor_algorithms.c](https://github.com/apple/darwin-xnu/blob/main/osfmk/vm/vm_compressor_algorithms.c)、[vm_compressor.c（newosxbook 镜像）](https://newosxbook.com/code/xnu-3247.1.106/osfmk/vm/vm_compressor.c.auto.html)、[Virtual memory compression（Wikipedia）](https://en.wikipedia.org/wiki/Virtual_memory_compression)）。
- **模式**：`vm_pageout.h` 定义 `VM_PAGER_COMPRESSOR_NO_SWAP`（**纯内核内压缩，无 swap 后端**）与 `VM_PAGER_COMPRESSOR_WITH_SWAP`（压缩 + swap 后端）。**iOS 实质走"压缩为主、基本不落盘 swap"**；macOS 默认带 swap 后端（在 Activity Monitor 里体现为 "Swap Used"），且仍**先压缩再考虑落盘**以减少 SSD 磨损（[macOS Activity Monitor 内存说明（Apple Support）](https://support.apple.com/guide/activity-monitor/view-memory-usage-actmntr1004/mac)）。

> **对照红线**：iOS 的"压缩内存"对应 Linux 的 **zram**（压缩进内存、不落盘），**不是** swap-to-disk。术语上请说 **VM compressor / 压缩内存**，不要说 "iOS 的 zram" 或 "iOS 的 swap"。机制脉络见 [A06 压缩与换页](../foundations/A06-压缩与换页.md)。

## 4. 第 2 层末端 · 终止：Jetsam / memorystatus（对应 LMKD/OOM）

iOS 的低内存终止逻辑**在 XNU 内核内**（与 Android 把决策放到用户态 LMKD 相反——见 [A08 §3.4/§4](../foundations/A08-压力与低内存终止.md)）。子系统名为 **memorystatus**，俗称 **Jetsam**：

- 维护一张全进程的 **jetsam 优先级带（priority band）** 列表；可回收页跌破阈值时，**按优先级升序**（最不重要的带最先）杀进程。**对应 Linux 的 `oom_score_adj` 排序**，但 iOS 是离散的优先级带、且由系统按前台/后台/扩展语义指派。
- 每个进程有 **per-process memory limit**：超**软上限**告警、超**硬上限**直接终止。对应 Linux 的 `memory.max`（memcg）触发 cgroup-OOM——**概念对应（每进程内存帽），实现不同**（iOS 没有 cgroup，这是进程级硬帽）。
- 另有 **压力等级通知 Normal / Warn / Critical**（对照 Android LMKD 三档），App 收到后应主动释放缓存。

来源：[memorystatus_notify.md（xnu）](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_notify.md)、[memorystatus_kills.md（xnu）](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_kills.md)、[No pressure, Mon!（newosxbook，Jetsam 剖析）](http://newosxbook.com/articles/MemoryPressure.html)。机制对照详见 [A08](../foundations/A08-压力与低内存终止.md)（该篇已并列分析 LMKD vs Jetsam vs OOM，本篇不重复展开）。

> **对照小结**：Linux 的 "PSI → LMKD（用户态）→ OOM（内核兜底）" 三段，在 iOS 压缩成 "memorystatus 压力等级 → Jetsam（内核内按优先级带 + per-proc limit 杀）"。少了"用户态守护进程"和"cgroup 分组"这两环。

## 5. 第 3 层 · 硬件：ARM MMU + DART（对应 SMMU）

- **CPU 侧 MMU**：Apple 芯片是 ARM64，走 ARM 多级页表 + TLB（[A01 §3.4](../foundations/A01-地址空间与虚实转换.md)），由 `pmap` 层管理；**16KB 基页**使页表更浅、TLB 覆盖更大。
- **设备侧 IOMMU = DART**：**DART（Device Address Resolution Table）是 Apple 自研的 IOMMU**，集成在内存控制器里，为外设提供独立的设备虚拟地址空间与页级读写保护；每个 DART 实例可服务多达 16 路 stream、各有独立页表。**对应 ARM 的 SMMU（[A10](../foundations/A10-IOMMU-SMMU与DMA.md)），但是 Apple 自研、术语与寄存器布局不同**。XNU 里 DART 由 `IOMapper` 的子类 `IODARTMapper`（`com.apple.driver.IODARTFamily`，闭源 KEXT）驱动；开源旁证可参考 Linux 侧的 [apple-dart 驱动](https://github.com/torvalds/linux/blob/master/drivers/iommu/apple-dart.c) 与 [Apple M1 DART IOMMU（LWN）](https://lwn.net/Articles/849969/)。

> **对照红线**：设备地址转换在 Android/Linux 叫 **SMMU**，在 iOS 叫 **DART**。两者都属 [A10](../foundations/A10-IOMMU-SMMU与DMA.md) 讲的"IOMMU"范畴，但**绝不要把 DART 称作 SMMU**。

## 6. 第 4 层与交界 · 存储：APFS + UBC（对应 page cache）

- **文件系统 APFS**（Apple File System）：iOS/macOS 主力文件系统，对应 Android 的 f2fs/ext4（[A11](../foundations/A11-page-cache与回写.md) 的存储交界）。其内部布局（写时复制元数据、快照、克隆）属本仓**范围外**，本篇只关注它与内存的交界。
- **UBC（Unified Buffer Cache，统一缓冲缓存）**：XNU 把**文件数据缓存与 mmap 后备**统一到 **VM 的物理页池里**——文件页就是普通 VM 页，挂在 page queues 上、由 `vm_pageout` 按同一套机制回收。**这正对应 Linux 的 page cache**（"文件页即 file LRU 成员"，[00 总览 §2](../foundations/00-内存系统总览.md)）——**概念完全对应、命名不同**：Linux 叫 page cache，XNU 叫 UBC。
  - 实现锚点：`ubc_info` 结构挂在 `V_REG`（普通文件）vnode 上；`UBC_PUSHDIRTY`/`UBC_PUSHALL`/`UBC_INVALIDATE` 等操作对应"回写脏页 / 全推 / 失效"。来源：[ubc.h（darwin-xnu）](https://github.com/apple/darwin-xnu/blob/main/bsd/sys/ubc.h)、[ubc_subr.c（darwin-xnu）](https://github.com/apple/darwin-xnu/blob/main/bsd/kern/ubc_subr.c)。UBC 谱系源自 NetBSD 的统一缓存设计（[Silvers, UBC for NetBSD](https://netbsd.stupin.su/en/ubc/)）。

> **对照小结**：Linux "page cache ↔ ext4/f2fs"，iOS "UBC ↔ APFS"。两边的关键性质一致——**文件页就是可回收的内存页**，干净页可丢、脏页要回写；`direct I/O` 的定义都是绕过它。

## 7. 没有 cgroup：用 jetsam band 代替"分组"

Linux 用 **cgroup/memcg**（[A07](../foundations/A07-cgroup-memcg.md)）把一组进程做**统计 + 限额 + per-memcg 回收**，Android 借它分前台/后台 App。**iOS 没有 cgroup**——它用两条更"扁平"的机制替代：

| Linux memcg 能力 | iOS 的替代 |
|---|---|
| 一组进程的内存**限额**（`memory.max`） | **per-process memory limit**（每进程硬帽，§4） |
| 按组排优先级、决定先回收/先杀谁 | **jetsam 优先级带**（按前台/后台/扩展指派，§4） |
| per-memcg LRU（限定回收作用域） | 无；回收是**全局** page queues，不分组 |

> **对照红线**：不要在 iOS 语境里说 "memcg""cgroup""per-memcg LRU"。iOS 的"分组"语义由 **jetsam band + per-process limit** 承担，且**回收本身是全局的**。

## 8. 一图对照（四层逐格）

| 层 / 格（[00 骨架](../foundations/00-内存系统总览.md)） | Linux / Android | **iOS / Darwin (XNU)** | 对照说明（回链机制篇） |
|---|---|---|---|
| ① 用户态分配器 | Scudo / jemalloc | **libmalloc**（nano/magazine/scalable） | 概念对应、实现不同（[A01](../foundations/A01-地址空间与虚实转换.md)） |
| 2A 地址空间描述 | VMA + maple tree | **vm_map / vm_map_entry** | 不是 maple tree（[A01](../foundations/A01-地址空间与虚实转换.md)） |
| 2A 后备对象 | file/anon inode | **vm_object + pager** | 多一层 pager 抽象 |
| 2A 页粒度 | 4KB（部分 16KB 迁移中） | **16KB**（Apple 芯片） | TLB 覆盖更大（[A12](../foundations/A12-大页与页粒度.md)） |
| 2A COW | PTE 只读 + 复制 | **shadow object 链** | 概念对应、机制不同 |
| 2B 冷热/回收 | LRU + kswapd + vmscan | **page queues + vm_pageout** | 不叫 LRU/kswapd（[A04](../foundations/A04-回收总论.md)/[A05](../foundations/A05-冷热识别的演进.md)） |
| 2B 匿名页后端 | **zram** / swap | **VM compressor**（WKdm/LZ4，基本不落盘） | 对应 zram，非 swap（[A06](../foundations/A06-压缩与换页.md)） |
| 2B 终止 | PSI → **LMKD**（用户态）→ OOM | **Jetsam / memorystatus**（内核态）+ per-proc limit | 决策在内核（[A08](../foundations/A08-压力与低内存终止.md)） |
| 2B 资源分组 | **cgroup / memcg** | 无 cgroup → **jetsam band + per-proc limit** | 回收全局、不分组（[A07](../foundations/A07-cgroup-memcg.md)） |
| ③ CPU MMU | ARM MMU + TLB | ARM MMU + TLB（`pmap`） | 同源（[A01](../foundations/A01-地址空间与虚实转换.md)） |
| ③ 设备 IOMMU | **SMMU** | **DART**（Apple 自研） | 对应 SMMU、术语不同（[A10](../foundations/A10-IOMMU-SMMU与DMA.md)） |
| ④ 文件系统 | f2fs / ext4 | **APFS** | 内部实现范围外（[A11](../foundations/A11-page-cache与回写.md)） |
| 交界 文件页缓存 | **page cache**（file LRU） | **UBC（Unified Buffer Cache）** | 概念对应、命名不同（[A11](../foundations/A11-page-cache与回写.md)） |

## 9. 来源与延伸阅读

**Apple 官方 / 归档文档**
- [Memory and Virtual Memory（Kernel Programming Guide, Apple 归档）](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/vm/vm.html) — vm_map / vm_object / pager / UPL / shadow object
- [page_size · Apple Developer](https://developer.apple.com/documentation/kernel/page_size)、[host_page_size · Apple Developer](https://developer.apple.com/documentation/kernel/1502512-host_page_size) — 运行期取页大小（16KB 不可硬编码）
- [Porting your macOS apps to Apple silicon · Apple Developer](https://developer.apple.com/documentation/apple-silicon/porting-your-macos-apps-to-apple-silicon)（页面正文未取到全文，**16KB 表述以归档 VM 指南与 page_size 文档为准 · 待核实细节**）
- [View memory usage in Activity Monitor（Apple Support）](https://support.apple.com/guide/activity-monitor/view-memory-usage-actmntr1004/mac) — 压缩内存 / Swap Used 的官方解释（macOS）

**XNU 开源（apple-oss-distributions / darwin-xnu）**
- [pageout_scan.md（xnu doc/vm）](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/pageout_scan.md) — page queues、flow control、2:1 比例
- [memorystatus_notify.md](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_notify.md)、[memorystatus_kills.md](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_kills.md) — Jetsam 优先级带、压力等级、per-proc limit
- [vm_compressor_algorithms.c（darwin-xnu）](https://github.com/apple/darwin-xnu/blob/main/osfmk/vm/vm_compressor_algorithms.c)、[vm_compressor.c（newosxbook 镜像）](https://newosxbook.com/code/xnu-3247.1.106/osfmk/vm/vm_compressor.c.auto.html) — WKdm / LZ4、压缩模式
- [ubc.h](https://github.com/apple/darwin-xnu/blob/main/bsd/sys/ubc.h)、[ubc_subr.c](https://github.com/apple/darwin-xnu/blob/main/bsd/kern/ubc_subr.c) — UBC / ubc_info / vnode

**libmalloc**
- [libmalloc · DeepWiki（Allocator Implementations）](https://deepwiki.com/apple-oss-distributions/libmalloc/3-allocator-implementations) — nano / magazine / scalable zone
- [Playing with Libmalloc in 2024（Blackwing HQ）](https://blackwinghq.com/blog/posts/playing-with-libmalloc/)

**DART / 压缩内存 旁证**
- [apple-dart.c（Linux 驱动）](https://github.com/torvalds/linux/blob/master/drivers/iommu/apple-dart.c)、[Apple M1 DART IOMMU（LWN）](https://lwn.net/Articles/849969/) — DART 流数、页表、16KB 最小页
- [Virtual memory compression（Wikipedia）](https://en.wikipedia.org/wiki/Virtual_memory_compression) — WKdm 字典与压缩比背景
- [No pressure, Mon!（newosxbook）](http://newosxbook.com/articles/MemoryPressure.html) — Jetsam / memorystatus 实测剖析

> **待核实 / 待补**：
> - `vm_map` 现代 XNU 的具体组织（链表 vs 红黑树）随版本演进，本篇取"有序结构"表述，**精确数据结构待核实**到具体 XNU 版本。
> - iOS（区别于 macOS）是否在任何场景启用磁盘 swap 后端：本篇取"iOS 基本不落盘、以 compressor 为主"，**iOS 端 swap 启用条件待核实**。
> - Apple 官方对 "16KB 页" 的最权威单句表述：Porting 文档正文未取到全文，当前以 Apple 归档 VM 指南"16 KB on Apple Silicon"与 `page_size`/`host_page_size` 文档为依据，**待补一条 developer.apple.com 正文直引**。
> - jetsam 各优先级带的具体取值与"前台/后台/扩展"映射（与 [A08](../foundations/A08-压力与低内存终止.md) 同一待核实项）。
> - DART 在 XNU 内的精确实现细节出自闭源 KEXT，本篇据 Linux 侧驱动与公开资料反推，**XNU 内 DART 行为待核实**。

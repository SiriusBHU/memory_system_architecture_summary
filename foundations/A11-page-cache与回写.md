# A11 · page cache 与回写

> **一句话定位**：文件数据在内存里的常驻形态——读过、写过的文件内容以"文件页"留在 page cache 中，供后续访问免去磁盘往返；它正是**内存 ↔ 存储的主交界**。
>
> 📍 **对应总览**：[00 总览](00-内存系统总览.md) 的「2B 物理与回收侧 · page cache」格，向右邻接「存储 I/O 栈（VFS/FS/块层）」。
> 🧭 **阅读前置**：先读 [00 总览](00-内存系统总览.md) 与 [A01 地址空间](A01-地址空间与虚实转换.md)；与 [A02 缺页](A02-缺页与按需分页.md)（文件缺页填充）、[A04 回收](A04-回收总论.md)（脏页回写）、[A05 冷热识别](A05-冷热识别的演进.md)（文件页即 file LRU）、[A12 大页与页粒度](A12-大页与页粒度.md)（folios）强耦合。
> 🌡️ **演进分级**：机制本体（buffered I/O、readahead、dirty 阈值）**相对稳定**；但 **page cache 的 folio 化** 是近年一次贯穿性大重构 ⚡——本篇 §4/§6 以它为重心，其余适度展开。

---

## 1. 定位：它在地图上的哪一格

page cache 坐在 [模块地图](01-连载规划与文章结构.md#1-模块层级与演进--篇幅地图) 的「2B 物理与回收侧」，但它的右边界直接顶到**存储 I/O 栈**（VFS → 文件系统 → 块层 → 驱动，[A09](A09-设备内存全景.md) 一侧）。一句话：**它是 DRAM 与持久化存储之间的那层缓存**。

- 向上：进程通过 `read`/`write`（buffered I/O）或 `mmap` 访问文件，命中的是 page cache 里的页；
- 向下：未命中时从文件系统读入，写脏后由回写路径刷回存储。

这些常驻的文件内容页就是 [A05](A05-冷热识别的演进.md) 里说的 **file-backed pages**，挂在 **file LRU**（与匿名页的 anon LRU 分开计冷热）。

## 2. 它解决什么问题

没有 page cache，每次 `read` 都要等一次磁盘/闪存 I/O，每次 `write` 都要同步落盘——延迟与吞吐都不可接受。page cache 用内存换两件事：

| 目标 | 机制 |
|---|---|
| **读不重复打磁盘** | 读过的文件页留在内存，再读直接命中；顺序访问还**预读**后续页 |
| **写不阻塞前台** | `write` 先把数据放进内存页并标脏，**异步**由后台线程批量回写 |

代价是：脏数据在内存中滞留有**丢失窗口**（掉电/崩溃），且内存吃紧时这些页要被回收——于是有了 dirty 阈值与回写策略来约束"能脏多少、何时必须刷"。

## 3. 机制本体：当前是怎么做的

### 3.1 索引结构与 buffered I/O 读写路径

每个文件对应一个 `address_space`，其中一棵 **XArray**（早年的 radix tree）以"文件内偏移（页索引）"为键，索引该文件已缓存的页。核心实现集中在内核 `mm/filemap.c`。

- **读路径**：`read()` → `filemap_read()` 按页索引查 XArray。命中则拷回用户缓冲区；未命中则分配页、发起文件系统读、填充后再返回——这与 [A02](A02-缺页与按需分页.md) 里 `mmap` 文件的**文件缺页**走的是同一套填充逻辑（前者主动查表、后者由缺页触发，殊途同归）。
- **写路径**：`write()` → `generic_perform_write()` 把用户数据拷进对应文件页，**置脏（dirty）**即返回，不等落盘。真正落盘交给回写路径（§3.3）。

### 3.2 readahead 预读

顺序读时只按需取页会让 I/O 与计算串行。内核据访问模式**预测并提前批量读入**后续页：维护一个预读窗口，命中预读页时放大窗口、随机访问时收缩。预读页先以"未引用"状态进入 file LRU，被真正命中才升温——这给了 [A05](A05-冷热识别的演进.md) 的冷热判定一个天然信号（预读了却没被读到的页应尽快回收）。

### 3.3 脏页与回写：dirty 阈值 + flusher 线程

写产生的脏页不能无限堆积，靠两道**水位**约束（[内核 vm sysctl 文档](https://docs.kernel.org/admin-guide/sysctl/vm.html)）：

- **`vm.dirty_background_ratio`**（默认约 10%）：脏页占"可用内存"达此比例时，**后台 flusher 线程**开始异步回写，进程**无感**继续运行；
- **`vm.dirty_ratio`**（默认约 20%）：脏页继续涨到此比例时，**产生写的进程自身被迫参与回写（节流，throttle）**——`write` 调用在此阻塞，直到脏页降下来。

> 两个比例都按"含空闲页与可回收页的可用内存"折算，而非物理总量。还有字节版 `dirty_bytes`/`dirty_background_bytes`（设了字节版则比例版失效），以及 `dirty_expire_centisecs`（脏页最长滞留时间）/`dirty_writeback_centisecs`（flusher 唤醒周期）控制"放久了也得刷"。

执行回写的是**每个后备设备（bdi）一组 flusher 内核线程**。回收侧（[A04](A04-回收总论.md)）在扫描 file LRU 遇到脏页时也会触发/等待回写——这是 page cache 与回收的直接接缝。

### 3.4 O_DIRECT：绕过 page cache

带 `O_DIRECT` 打开的文件，其 I/O **不经过 page cache**，数据在用户缓冲区与存储设备间直传（[open(2) man page](https://man7.org/linux/man-pages/man2/open.2.html)）。动机是**避免双重缓冲**：数据库等自带缓存的应用，再让内核缓存一份纯属浪费内存且打乱其换页策略。

代价与约束：

- 通常对缓冲区地址、长度、文件偏移有**对齐要求**（一般到逻辑块/扇区边界），且**对齐规则随文件系统与内核版本而异、无统一查询接口**（[open(2)](https://man7.org/linux/man-pages/man2/open.2.html)）；
- `O_DIRECT` 只绕缓存、**不保证持久化**——要落盘仍需 `O_DSYNC`/`fsync`；
- 与同文件的 buffered I/O 混用语义复杂，应避免。

### 3.5 文件 mmap：共享的文件页

`mmap` 一个文件（`MAP_SHARED`）时，建立的映射**直接指向 page cache 里的文件页**：

- 多个进程映射同一文件，**共享同一份物理页**（共享库 `.text` 的多进程复用即源于此）；
- 写 `MAP_SHARED` 映射会把页置脏，最终经同一回写路径落盘；
- 因此 mmap 写与 `write()` 写**看到一致的页内容**，不存在两份副本。

## 4. 历史：page cache 的 folio 化（演进重心）⚡

长期以来，page cache 以 `struct page`（一个基页，移动端通常 4KB）为单位管理。问题逐渐暴露：海量小页让 **LRU 链表过长**、管理元数据开销大、且无法表达"一段连续的大块文件内容"。

**folio** 是对此的回应——一个 folio 代表"一个或多个连续物理页构成的、不会再细分的内存块"，把 `struct page` 与"复合页/尾页"的语义混乱收拢成一个明确的对象（[Page folios, LWN](https://lwn.net/Articles/840593/)；[Folio-enabling the page cache, LWN](https://lwn.net/Articles/860537/)）。演进脉络：

- **page cache 全面转向 folio**：filemap 与读写、查找接口改以 folio 为单位操作（如 `readahead_folio()` 等），**page cache 本身已完成 folio 化**（[The state of the page in 2024, LWN](https://lwn.net/Articles/973565/)）。
- **多页 folio 的存储表示**：约 5.17 起，大 folio 在 page cache 中不再存为 2^N 个相同条目，而用 **XArray 的 multi-index 条目**表示一项即一大块（[Folios for 5.17, LWN](https://lwn.net/Articles/878016/)）。
- **改造重心其实在回写**："最大的一块工作是教会回写代码——folio 可能大于一页"（[Folio-enabling the page cache, LWN](https://lwn.net/Articles/860537/)）。readahead 侧也加入了**多页 folio 预读**：一次预读分配大 folio 而非逐个基页（[mm/readahead: Add multi-page folio readahead, LKML](https://lkml.iu.edu/hypermail/linux/kernel/2107.1/09712.html)）。

收益是结构性的：**用大 folio 装文件内容，能显著缩短 file LRU、降低管理开销，使回收更高效**，并减少内存碎片（[The state of the page in 2024, LWN](https://lwn.net/Articles/973565/)）。这条线与 [A12 大页与页粒度](A12-大页与页粒度.md) 是同一棵树的两根枝——folio 是"让一个内存对象覆盖多页"的统一抽象，大页/16KB 是它在硬件页表层的体现。

## 5. 现状与平台差异

- **Linux**：page cache 已 folio 化；但**"large folios for file"（文件页用多页大 folio）在各文件系统的落地并不齐**——XFS、bcachefs 等较完整，多数文件系统仍主要按基页或仅部分支持（[The state of the page in 2024, LWN](https://lwn.net/Articles/973565/)）。移动端常用的 **f2fs**、桌面常用的 **ext4** 的大 folio 支持程度需按内核版本逐一核对（待核实）。
- **iOS / Darwin**：用 **APFS** 作文件系统、XNU 的 **UBC（Unified Buffer Cache）** 统一文件缓存与 VM 页——概念对应 page cache，但实现与术语自成一套（与 Linux 的 folio/f2fs 不可混称）。
- **HarmonyOS**：内核基座与文件缓存实现待补（待核实）。

> 术语警示：Linux 的 **f2fs/ext4** 与 Apple 的 **APFS** 是不同文件系统，回写与缓存机制不可互相套用；folio 是 Linux 概念，勿用于描述 XNU/APFS。

## 6. 趋势与未解问题 ⚡

- **大 folio 向更多文件系统铺开**：给各文件系统加 large-folio 支持是当前主线，但"需要对具体文件系统的专门知识、并非易事"，进度不一（[The state of the page in 2024, LWN](https://lwn.net/Articles/973565/)）。
- **把 mapping/index 等字段移出 `struct page`**、`struct page` 持续瘦身，是 folio 化的后续清理工作（同上）。
- **回写与大 folio 的配合**仍在打磨：folio 越大，单次回写覆盖越广、但部分脏（sub-folio dirty）的精细回写与写放大需要权衡。

## 7. 配合与依赖（跨层）

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| page cache ↔ 文件系统/块层 | 未命中读入、脏页回写都经此栈——**内存↔存储主交界** | [A09](A09-设备内存全景.md) 存储 I/O 栈一侧 |
| 文件缺页 → page cache | `mmap` 文件访问缺页时，填充/复用同一份文件页 | [A02](A02-缺页与按需分页.md) |
| 回收 → 脏页回写 | file LRU 扫到脏页触发/等待回写后才能释放 | [A04](A04-回收总论.md) |
| 文件页 = file LRU | page cache 的页即冷热识别中的文件页 | [A05](A05-冷热识别的演进.md) |
| folio 化 ↔ 大页/页粒度 | 大 folio 是"覆盖多页"的统一抽象 | [A12](A12-大页与页粒度.md) |
| 共享文件页 ↔ 页表 | mmap 文件页被多进程页表共享映射 | [A01](A01-地址空间与虚实转换.md) |

## 8. 实测 / 观测点

- `cat /proc/meminfo`：看 `Cached`（page cache 总量）、`Buffers`、`Dirty`、`Writeback`（正在回写的脏页量）；
- `cat /proc/sys/vm/dirty_ratio`、`dirty_background_ratio`、`dirty_expire_centisecs`：回写水位旋钮；
- `/proc/<pid>/smaps` 中文件映射的 `Shared`/`Private` 项：看 mmap 文件页的共享情况（度量细节见 [A13](A13-内存度量与排障.md)）；
- `echo 1 > /proc/sys/vm/drop_caches`：丢弃干净 page cache（仅用于实验观测命中率变化，**生产慎用**）；
- `vmtouch`/`fincore`：查看某文件当前有多少页驻留在 page cache。

## 9. 来源与延伸阅读

- 脏页与回写 sysctl：[Documentation for /proc/sys/vm/ (docs.kernel.org)](https://docs.kernel.org/admin-guide/sysctl/vm.html)
- O_DIRECT 语义：[open(2) Linux manual page (man7.org)](https://man7.org/linux/man-pages/man2/open.2.html)
- folio 与 page cache：[Page folios (LWN)](https://lwn.net/Articles/840593/)、[Folio-enabling the page cache (LWN)](https://lwn.net/Articles/860537/)、[Memory folios (LWN)](https://lwn.net/Articles/862610/)、[Folios for 5.17 (LWN)](https://lwn.net/Articles/878016/)、[The state of the page in 2024 (LWN)](https://lwn.net/Articles/973565/)
- 多页 folio 预读：[mm/readahead: Add multi-page folio readahead (LKML)](https://lkml.iu.edu/hypermail/linux/kernel/2107.1/09712.html)
- 内核源码锚点：`mm/filemap.c`、`mm/readahead.c`、`mm/page-writeback.c`

> **待核实 / 待补**：f2fs / ext4 对 large folios for file 的支持版本与现状；`ondemand_readahead()` 是否已更名为 `page_cache_ra_order()`（二手来源所述，未在内核源码逐版核对）；HarmonyOS 文件缓存的内核实现（LiteOS-A 已见 [A14 · HarmonyOS 平台对照](../platforms/A14-HarmonyOS-内存实现.md)）；XNU UBC 与 APFS 回写策略的细节（见 [A14 · iOS/Darwin 平台对照](../platforms/A14-iOS-Darwin-内存实现.md)）。

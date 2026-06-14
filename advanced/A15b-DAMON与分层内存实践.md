# A15b · DAMON 与分层内存实践

> **一句话定位**：把 [A05](../foundations/A05-冷热识别的演进.md) 里点到为止的 DAMON 拆开看——它怎么用"基于区域的采样"做到**开销与内存大小无关**的访问监控，又怎么靠 DAMOS 的"条件→动作"把监控结果变成**主动回收**与**层间迁移**，最终成为 [A15](A15-前沿-先进内存.md) 那套分层内存的"驱动引擎"。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「2B 物理与回收侧 · LRU 冷热（A5 ⚡）」+「第 4 层 · 存储层级 · 分层内存（A15 ⚡）」——本篇是这两格的**交汇处**：DAMON 是冷热识别的可编程化身，分层迁移是它当下最重的应用。
> 🧭 **阅读前置**：先读 [A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md)（DAMON / MGLRU 的**基础**，本篇承接、不重复）与 [A15 前沿·先进内存](A15-前沿-先进内存.md)（分层内存 / CXL 总览，本篇是其 **DAMON 维度的深潜**）；回收路径见 [A04 回收总论](../foundations/A04-回收总论.md)，压缩换页见 [A06 压缩与换页](../foundations/A06-压缩与换页.md)。
> 🌡️ **演进分级**：**演进厚 ⚡（开放连载）**——DAMON 从 5.15 至今几乎每个版本都在加动作、加旋钮，分层迁移更是 2024–2025 才落地主线。行文按 **动机 → 现状 → 趋势/未解** 展开，版本号均带出处，拿不准处标「待核实」。

---

## 1. 定位：从"瞄准镜"到"可编程的访问中枢"

[A05](../foundations/A05-冷热识别的演进.md) 把冷热识别的演进讲到了一个分叉口：**MGLRU 把回收路径里的 LRU 重写得更聪明，而 DAMON 走的是另一条路——把"访问监控"从回收里抽出来，做成独立、低开销、可编程的子系统**。本篇就站在这个分叉口往下走，回答三个 A05 没展开的问题：

1. DAMON 凭什么敢宣称"开销与监控目标大小无关"？它的采样机制到底怎么转（§3）。
2. 光监控不够，**怎么把"这页很冷"变成"把它迁到慢层"**？这是 DAMOS 的"条件→动作"（§4）。
3. 这套东西在 [A15](A15-前沿-先进内存.md) 的 CXL / 分层内存里**真的跑出数据了吗**？有哪些公开实测（§5）。

一句话定位本篇在地图上的格子：它是 `REC -->|选页| LRU`（A05）与 `冷热识别 -->|层间迁移| TIER`（A15）**两条边的实现细节**。

## 2. 它解决什么问题（没有它会怎样）

要管好分层内存，前提是**知道每个页有多热**。但"测访问"这件事本身就有代价，而既有手段都卡在一个矛盾上：

| 手段 | 怎么测 | 痛点 |
|---|---|---|
| **PTE Accessed 位扫描**（second-chance / MGLRU，[A05 §3.2](../foundations/A05-冷热识别的演进.md)） | 回收时逐页清/查 access bit | 开销随物理页数线性增长；信息焊死在回收路径里，外部拿不到 |
| **空闲页跟踪 idle page tracking**（[内核文档](https://docs.kernel.org/admin-guide/mm/idle_page_tracking.html)） | 用户态写 `/sys/kernel/mm/page_idle/bitmap` 置位，再读回看哪些被清 | **逐页**置位/回读，几百 GB 内存下扫一遍开销巨大，难以常驻 |

共同病根：**开销正比于内存规模**。内存越大越该精细管理，可偏偏越大越测不起——这正是大内存服务器与受限移动端共同的困境。

DAMON 的破题思路是**牺牲单页精度换取可控总开销**：不追求"每个页都准"，而是保证"**整体画像够用、且开销可由旋钮固定住**"。这一步让访问监控第一次能够**常驻生产环境**，也才谈得上拿它去驱动迁移。

## 3. DAMON 架构再深入：开销为什么是常数

### 3.1 基于区域的采样（region-based sampling）

DAMON 不盯单页，而是把监控目标（一个进程的虚拟地址空间，或整段物理地址）切成若干 **region（区域）**，核心约定是：**同一 region 内的页被假定访问频率相同**。于是每个采样周期，DAMON 只需**在每个 region 里随机抽一个页**查它是否被访问（物理地址监控下用 `folio_check_references` 之类查引用；虚拟地址下查 PTE Accessed 位并清掉，供下次比对）——若被访问，就给该 region 的 **`nr_accesses` 计数器**加一。([DAMON 设计文档](https://docs.kernel.org/mm/damon/design.html))

关键推论：**一次采样的开销正比于 region 数量，而不是页数**。region 数有上下限旋钮（默认上限约一万），所以**把内存从 4GB 加到 4TB，监控开销几乎不变**——这就是"与目标大小无关"的来历，也是它和 §2 两种逐页方案的根本分野。

两个时间尺度要分清：

- **采样间隔 `sampling_interval`**：多久抽查一次（默认 5ms 量级）；
- **聚合间隔 `aggregation_interval`**：多久把 `nr_accesses` 汇总成一帧"访问快照"、并把计数清零重来（默认 100ms 量级）。

一帧聚合内 `nr_accesses` 的最大值 = 聚合间隔 / 采样间隔，它就是"这个 region 这一帧有多热"的离散刻度。

### 3.2 自适应区域调整（adaptive region adjustment）

固定切 region 会失真：一个 region 横跨冷热边界时，"同区域同频率"的假设就破了。DAMON 用一套**自适应合并/拆分**自我校正（[设计文档](https://docs.kernel.org/mm/damon/design.html)）：

- **合并**：相邻 region 若访问频率相近、且尺寸小于阈值，就并成一个——压低 region 总数、回收开销预算；
- **拆分**：把 region 随机切开，下一帧观察两半的 `nr_accesses` 是否分化；分化大说明内部冷热不均，保持拆分，否则下帧再并回去。

这套机制让 region 边界**自动贴合真实的冷热分界**：热区被切得细（精度高），大片均匀冷区被并成几个大 region（省开销）。**精度自动流向最需要的地方**，这是 DAMON 既省又够准的第二个支点。

### 3.3 接口与工具：`damon_sysfs` 与 `damo`

DAMON 早期用 debugfs，现以 **sysfs 接口 `/sys/kernel/mm/damon/admin/`** 为正式入口：`kdamonds/<N>` 是一个监控内核线程（kdamond），其下 `contexts/<N>/` 配监控目标、区间、`schemes/<N>/` 配 DAMOS 方案，写 `state` 文件 `commit`/`on`/`off` 生效。直接拼 sysfs 路径繁琐，实践中几乎都用用户态工具 **[`damo`](https://github.com/awslabs/damo)**（AWS Labs 维护）——它把上面那串路径包成 `damo start --damos_action ...` 这样的命令行，还能 `damo report` 出访问热力图。

> 与 [A05 §3](../foundations/A05-冷热识别的演进.md) 的对照：MGLRU 的"走页表清 access bit"仍是**逐页**、且只服务回收；DAMON 的采样是**逐 region**、且把结果**开放**给任意策略消费。二者不是替代关系——见 §6 分工。

## 4. DAMOS：把监控变成动作

监控只产出"哪些 region 多热"。**DAMOS（DAMON-based Operation Schemes）** 在其上加一层"**条件 → 动作**"规则，让访问感知的系统操作**无需写代码、只配规则**。

### 4.1 条件：访问模式 + 配额 + 目标

一条 DAMOS 方案先用**访问模式（access pattern）**圈定目标 region——给三个维度各设 min/max 闭区间：**区域大小 `sz`、访问频率 `nr_accesses`、年龄 `age`**（"已经多少帧维持当前冷热状态"）。例如"`nr_accesses=0` 且 `age≥` 若干秒"就圈出了**长期没碰过的冷区**。

光圈定还不够，DAMOS 再叠两层闸门，这是它能"常驻而不失控"的关键：

- **配额 quota**：给动作设**时间上限**（每段时间最多花 N 毫秒做这个动作）与**大小上限**（每段时间最多处理 N 字节），取两者更严的那个，把动作对系统的扰动钉在可控范围；
- **目标 goal / 反馈自调（feedback-driven auto-tuning）**：更进一步，让用户只声明**想达到的系统状态**（如"内存压力 0.5%""快层占用 29.7%"），DAMON 据当前实测值**自动加减配额的激进程度**——压力高了就放开回收/迁移，达标了就收手。([usage 文档](https://docs.kernel.org/admin-guide/mm/damon/usage.html))

此外可挂 **DAMOS filter** 做精筛，其中分层迁移最常用的是 **`young` 过滤器**——按页表 **Accessed 位**判定"上次检查后有没有被访问过"，把"真热/真冷"从 region 级粗判精确到页级（[设计文档](https://docs.kernel.org/mm/damon/design.html)）。

### 4.2 动作：从 pageout 到层间迁移

DAMOS 的动作清单逐版本生长，按用途归三类（动作名引自[设计文档](https://docs.kernel.org/mm/damon/design.html)）：

| 类别 | 动作 | 含义 | 合入 |
|---|---|---|---|
| **回收** | `pageout` / `cold` | 回收该 region / 对其 `madvise(MADV_COLD)` | 5.15 起 |
| **LRU 排序** | `lru_prio` / `lru_deprio` | 把页**挪到 active 链头**（最难被踢）/ **降级到 inactive 链** | **6.0** |
| **层间迁移** | `migrate_hot` / `migrate_cold` | 把页迁到 `target_nid` 指定的 NUMA 节点，分别**优先搬热页 / 冷页** | **6.11** |

后两类正是本篇与 [A15](A15-前沿-先进内存.md) 的接缝：

- **`lru_prio` / `lru_deprio`（Linux 6.0）**：不直接迁页，而是**重排 LRU**——`lru_prio` 把指定页移到 active 链头，使其成为最后才被回收的页；`lru_deprio` 反之，把页 deactivate 到 inactive 链。配套的 **DAMON_LRU_SORT** 静态模块用它做"基于访问模式的 LRU 再排序"，**让 LRU 这个数据访问来源更可信**——本质是给 [A05](../foundations/A05-冷热识别的演进.md) 的 LRU 喂一份外部冷热意见。([LRU-list manipulation with DAMON, LWN](https://lwn.net/Articles/905370/))
- **`DAMOS_MIGRATE_HOT` / `DAMOS_MIGRATE_COLD` + `target_nid`（Linux 6.11）**：这是分层迁移的主角。`migrate_cold` 像 `pageout`，但**不换出到 swap，而是把 folio 迁到 `target_nid` 指定的（更慢的）NUMA 节点**；`migrate_hot` 反向，把热页**提升回快层**。两者由 SK 海力士的 Honggyu Kim、Hyeongtak Ji 与维护者 SeongJae Park 合作，**RFC 基于 v6.10-rc3，正式合入 Linux 6.11**（经 Andrew Morton 的 mm 树）。([DAMON based tiered memory management for CXL, LWN](https://lwn.net/Articles/978313/)；[A 2026 DAMON update, LWN](https://lwn.net/Articles/1071256/))

> 这正是 [A15 §6.1](A15-前沿-先进内存.md) 那条"DAMON 接管分层迁移"伏笔的落地细节：**降级走 `migrate_cold`、提升走 `migrate_hot`，比 NUMA-balancing 式提升（靠缺页采样、反应慢）更主动、更可策略化。**

### 4.3 DAMON_RECLAIM：主动回收

在 DAMOS 之上，**DAMON_RECLAIM（Linux 5.16）** 是个开箱即用的静态模块：自动找**长期没访问的冷 region 并提前回收**，定位是"**轻度内存压力下的主动、轻量回收**"——重压力仍交给传统 LRU 扫描。它带 `quota_mem_pressure_us` 等旋钮，可声明一个**目标内存压力**，由 §4.1 的反馈自调机制自动增减回收力度。([DAMON-Based Memory Reclamation Merged For Linux 5.16, Phoronix](https://www.phoronix.com/news/DAMON-Reclamation-Linux-5.16)；[reclaim 文档](https://docs.kernel.org/admin-guide/mm/damon/reclaim.html)) 它的意义是把"什么时候回收"从被动等水线，变成**可主动、可策略化**——也为后来的 `migrate_*` 把"回收"扩成"迁移"铺了路。

## 5. 用于 CXL / 分层内存的真实案例与数据

把 §4 的动作组合起来，就是 [A15](A15-前沿-先进内存.md) 设想的 DAMON 驱动分层。**SK 海力士在合入 `migrate_*` 时给出的实测**（YCSB zipfian 负载、Redis 落在 DRAM+CXL 双层、高内存压力）是目前最具体的公开数据：

- **默认 NUMA 内存策略**：Redis 平均约 **28.7 GB** 数据落在 CXL 慢层，相对 DRAM-only 基线**性能下降约 11%**（部分配置达 17–18%）；
- **DAMON 分层（`migrate_hot`/`migrate_cold` + `young` 过滤）**：落在 CXL 的量压到约 **2.2 GB**（约 1/13），**性能下降收窄到约 4%**（4–5%）。

即"**用约十分之一的慢层占用，把性能损失砍掉一多半**"。([DAMON based tiered memory management for CXL, LWN](https://lwn.net/Articles/978313/)) 数据出处是合入帖与 LWN 报道，基于 v6.10-rc3 的补丁集；**具体数值随负载与硬件差异很大，引作量级而非定论**。

延伸的工程方向（2025 起，多为 Micron / AMD 等贡献，**新于本篇主参考时点、细节待核实**）：给 `migrate_hot/cold` 加 **`migrate_dests` 多目标 + 权重**，按比例把页**加权交织（weighted interleaving）**到多个慢层节点，呼应 [A15 §3.1](A15-前沿-先进内存.md) 的加权交织线；以及把 DAMOS 配额目标扩到**按 cgroup、按 NUMA 节点**的内存占用（`DAMOS_QUOTA_NODE_MEMCG_*`），做容器级的访问感知分层（[A 2026 DAMON update, LWN](https://lwn.net/Articles/1071256/)）。

> 移动端目前**没有 CXL 硬件**，但同一套 `pageout`/`cold`/物理地址监控可在 Android 内核做**访问感知的主动回收**——迁移目标是 [zram](../foundations/A06-压缩与换页.md) 而非 CXL 节点（启用与机型覆盖**待核实**，与 [A05](../foundations/A05-冷热识别的演进.md) 同一保留意见）。

## 6. DAMON 与 MGLRU 的分工

两者常被并列，但**职责正交、并非二选一**（承接 [A05 §6](../foundations/A05-冷热识别的演进.md)）：

| 维度 | MGLRU（[A05](../foundations/A05-冷热识别的演进.md)） | DAMON / DAMOS（本篇） |
|---|---|---|
| 在哪 | **焊在回收路径里**（`mm/vmscan.c`） | **独立子系统**（`mm/damon/`），常驻可编程 |
| 测什么 | 逐页清 access bit，分多代 | 逐 region 采样，开销与规模无关 |
| 产出给谁 | 只服务**回收选页** | 开放给**任意策略**：回收 / LRU 重排 / 层间迁移 |
| 典型动作 | 老化 + 逐出 | `pageout` / `lru_prio` / `migrate_hot/cold` |

**一句话分工：MGLRU 管"回收时怎么挑页挑得准"，DAMON 管"把可编程的访问监控与迁移开放成一等公民"。** 二者还能配合——DAMON 的 `lru_prio/deprio` 正是**反过来给 MGLRU/LRU 喂外部冷热意见**，让回收侧的链表更可信。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| DAMON → 回收 | DAMON_RECLAIM 主动回收冷 region | [A04](../foundations/A04-回收总论.md) |
| DAMON ↔ LRU/MGLRU | `lru_prio/deprio` 重排 LRU，喂外部冷热 | **[A05](../foundations/A05-冷热识别的演进.md)** |
| DAMON → 分层迁移 | `migrate_hot/cold` + `target_nid` 驱动 demote/promote | **[A15](A15-前沿-先进内存.md)** |
| `migrate_cold` ↔ 压缩换页 | 慢层满了仍可落 zram/swap，迁移是其上游 | [A06](../foundations/A06-压缩与换页.md) |
| DAMOS 配额 ↔ memcg | 按 cgroup/节点控制迁移与回收配额 | [A07](../foundations/A07-cgroup-memcg.md) |
| `young` 过滤 → 页表 | 按 PTE Accessed 位做页级访问判定 | [A01 §3.4](../foundations/A01-地址空间与虚实转换.md) |

## 8. 趋势与未解问题

- **策略的自适应化**：`migrate_*` 的"什么时候迁、迁多少"仍靠人调阈值；反馈自调（goal/feedback）与 per-cgroup-per-node 配额是把它**自动化**的方向，但**普适策略尚未成形**——迁移太慢则热页挨慢层之苦，太激进则层间抖动（thrashing 的层间版，[A15 §6.4](A15-前沿-先进内存.md)）。
- **接口稳定性**：DAMON sysfs 与 DAMOS 动作集**几乎每版都在加**（5.15 监控 → 5.16 RECLAIM → 6.0 LRU_SORT → 6.11 migrate → 6.1x 多目标/per-memcg），用户态需跟 `damo` 版本走，**接口尚未完全定型**。
- **移动端可用性**：DAMON 的**物理地址监控 + 低开销**理论上很适合移动端的主动回收，但 AOSP/GKI 的**实际启用、默认与机型覆盖待核实**；移动端缺 CXL，`migrate_*` 短期无用武之地，能落地的主要是 `pageout`/`cold` + 压缩（[A06](../foundations/A06-压缩与换页.md)）这条"软分层"。
- **与 MGLRU 的长期边界**：两套访问监控并存的维护成本、以及"DAMON 喂 LRU"是否会与 MGLRU 自身的 PID 反馈打架，仍是开放问题。

## 9. 实测 / 观测点

- `/sys/kernel/mm/damon/admin/kdamonds/<N>/`：sysfs 配置入口（`contexts/.../schemes/.../action`、`target_nid`、`quota/`、`access_pattern/`），写 `state` 文件 `commit`/`on`/`off`；
- 用户态 [`damo`](https://github.com/awslabs/damo)：`damo start --damos_action migrate_cold --damos_quota_goal ...` 配方案，`damo report access` 出访问热力；
- `cat /sys/module/damon_reclaim/parameters/enabled`：DAMON_RECLAIM 开关；同目录 `quota_*`、`min_age` 等旋钮；
- `cat /proc/vmstat | grep damon`：`damon_migrate_*` 等迁移计数（视版本，[A 2026 DAMON update](https://lwn.net/Articles/1071256/)）；
- 分层侧对照 [A15 §8](A15-前沿-先进内存.md)：`/sys/devices/system/node/`（CXL 呈 CPU-less 节点）、`numactl -H`、`cxl list`。

## 10. 来源与延伸阅读

**DAMON 架构与设计**
- [DAMON Design (kernel.org)](https://docs.kernel.org/mm/damon/design.html)
- [DAMON index / 概述 (kernel.org)](https://docs.kernel.org/mm/damon/index.html)
- [DAMON usage 文档 (kernel.org)](https://docs.kernel.org/admin-guide/mm/damon/usage.html)
- [Idle page tracking (kernel.org)](https://docs.kernel.org/admin-guide/mm/idle_page_tracking.html)
- [damo 用户态工具 (AWS Labs)](https://github.com/awslabs/damo)

**DAMOS 动作演进**
- [Using DAMON for proactive reclaim (LWN)](https://lwn.net/Articles/863753/)
- [DAMON-Based Memory Reclamation Merged For Linux 5.16 (Phoronix)](https://www.phoronix.com/news/DAMON-Reclamation-Linux-5.16)
- [DAMON-based Reclamation (kernel.org)](https://docs.kernel.org/admin-guide/mm/damon/reclaim.html)
- [LRU-list manipulation with DAMON (LWN)](https://lwn.net/Articles/905370/)（`lru_prio`/`lru_deprio`，6.0）

**DAMON 用于分层 / CXL**
- [DAMON based tiered memory management for CXL memory (LWN)](https://lwn.net/Articles/978313/)（`migrate_hot/cold` + `target_nid`，6.11；SK hynix Redis 实测）
- [A 2026 DAMON update (LWN)](https://lwn.net/Articles/1071256/)（多目标 `migrate_dests`、per-cgroup-per-node 配额等近况）
- [mm/damon/vaddr: Allow interleaving in migrate_{hot,cold} actions (LWN)](https://lwn.net/Articles/1028380/)

**内核源码锚点**：`mm/damon/core.c`（区域/采样/聚合）、`mm/damon/paddr.c`（物理地址监控、`migrate_*`/`lru_*` 动作）、`mm/damon/sysfs*.c`、`mm/damon/reclaim.c`、`mm/damon/lru_sort.c`

> **待核实 / 待补**：SK hynix Redis 数据的逐配置数值（不同负载/比例差异大，本篇引量级）；`migrate_dests` 多目标加权交织与 `DAMOS_QUOTA_NODE_MEMCG_*` 的确切合入版本（2025 后，新于主参考时点）；DAMON_LRU_SORT 模块的确切合入版本（`lru_prio/deprio` 动作为 6.0，模块化时点待逐版核对）；DAMON 物理地址监控在 Android/GKI 的实际启用、默认与机型覆盖；HarmonyOS 是否引入任何 DAMON 类访问监控。

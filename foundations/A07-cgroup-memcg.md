# A07 · cgroup / memcg（资源隔离与限额）

> **一句话定位**：memcg 是回收机制的"作用域容器"——按 cgroup 把一组进程的内存*统计*起来、给它们划定*配额边界*（min/low/high/max），并在边界内施加局部回收与压力反馈；它只管"这一组用了多少、能用多少"，不负责全局选哪个进程杀。
>
> 📍 **对应总览**：[00 总览](00-内存系统总览.md) 的「2B 物理与回收侧」——memcg 是横切在回收之上的一层"分组与计量"。
> 🧭 **阅读前置**：先读 [00 总览](00-内存系统总览.md) 与 [A4 回收总论](A04-回收总论.md)；本篇与 [A5 冷热识别](A05-冷热识别的演进.md)（per-memcg LRU）、[A8 压力与终止](A08-压力与低内存终止.md)（PSI / OOM / 杀进程）强耦合，建议连读。
> 🌡️ **演进分级**：**演进厚 ⚡**——接口从 cgroup v1 到 v2 经历了语义重写，且 `memory.reclaim`（5.19）、per-cgroup PSI（基于 4.20 的 PSI）等是近年新增的主动控制面。**重点在 §4 历史（v1→v2）与 §6 趋势**。

---

## 1. 定位：它在地图上的哪一格

在 [模块地图](01-连载规划与文章结构.md#1-模块层级与演进--篇幅地图) 里，memcg（MCG）不是一个独立的"机制层"，而是一条**横切边**：`MCG -->|限定作用域| REC`。也就是说，回收（[A4](A04-回收总论.md)）本身是全局的引擎，而 memcg 在它之上加了一层"按组划界"：

- **统计**：把"匿名页 / page cache / 内核对象（slab）/ swap"等占用，按 cgroup 归集计数；
- **限额**：给每组设上下界，越界时触发组内回收，或在硬上限处触发组内 OOM；
- **反馈**：把组内的内存延迟（stall）以 PSI 形式暴露给用户态决策器。

一句话区分本篇与邻篇：**memcg 决定"在谁身上、回收多少、压力多大"，[A8](A08-压力与低内存终止.md) 决定"系统真扛不住时杀谁"。** 两者常被混为一谈，但职责边界清晰——memcg 管配额，不做全局裁决。

## 2. 它解决什么问题

没有 memcg，内核的回收只有一个全局视角：所有进程的页混在同几条 LRU 上，水线一低就无差别地回收"全局看起来最冷"的页。这在终端场景有三个直接痛点：

| 问题 | 只有全局回收 | 有了 memcg |
|---|---|---|
| **隔离** | 一个失控 App 可把别人的工作集挤出内存 | 每组有独立配额，越界先回收自己 |
| **差异化策略** | 前台 / 后台一视同仁 | 可对后台组设更激进的回收 / swappiness |
| **可观测** | 只知道系统总量，不知"谁占了多少" | `memory.current` / `memory.stat` 按组精确计量 |

终端上这件事尤其要紧：前台 App 的页要尽量留住（卡顿即可感知），后台 App 的页要乐于换出/压缩。memcg 提供的正是"**按重要性分组、分别施策**"的抓手。

## 3. 机制本体：当前是怎么做的（cgroup v2）

以下接口均属 cgroup v2 的 `memory` 控制器，挂在 cgroupfs 各子目录下。

### 3.1 四道闸：min / low / high / max

这是 memcg 的核心配额模型，**两道保护下限 + 两道压力上限**：

| 文件 | 方向 | 语义（据 cgroup-v2 文档） | 越界行为 |
|---|---|---|---|
| `memory.min` | 下限·硬保护 | 在此额度内的内存**任何情况下都不回收** | 低于全局也保护，可能逼出全局 OOM |
| `memory.low` | 下限·软保护 | 仅当"无保护 cgroup 已无可回收内存"时才回收 | 尽力而为，可被突破 |
| `memory.high` | 上限·节流 | "使用超限时，进程被**节流（throttle）并置于重度回收压力**下" | **从不触发 OOM**，极端下限额可被突破 |
| `memory.max` | 上限·硬限 | "限制内存用量的**主机制**"，是硬墙 | 回收仍压不下去 → **触发组内 OOM killer** |

**`memory.high` 与 `memory.max` 的区别是本篇必须讲清的一点**：前者是"**节流**"——超了就让该组进程慢下来、边跑边被重度回收，给系统留出腾挪余地，但绝不杀进程；后者是"**硬墙**"——回收也压不回去就只能在组内动 OOM。换言之，`high` 是"软着陆的刹车"，`max` 是"撞墙的兜底"。容器/App 框架通常把 `high` 设在 `max` 之下，让大多数压力在节流阶段就被消化，避免直接走到 OOM。

`min/low` 则是对称的"地板"：`min` 是不可侵犯的硬保护（哪怕代价是全局 OOM），`low` 是尽力保护（实在没别的可回收才动它）。终端上常用来给前台/关键服务组兜底。

### 3.2 per-memcg LRU 与 `memory.stat`

memcg 不是简单地"数个总量"，而是**每个 cgroup 各自挂一套 LRU**（active/inactive、anon/file 各一条）。回收时按组遍历各自的 LRU，这样"回收谁"天然带上了"属于哪组"的维度——这条线索在 [A5 冷热识别](A05-冷热识别的演进.md) 展开（MGLRU 同样是 per-memcg 组织的）。

`memory.stat` 把这套计量摊开：anon / file / kernel(slab) / sock / shmem 等分类占用，以及 `pgscan` / `pgsteal` / `workingset_refault` 等回收统计。它是排障时回答"**这组的内存到底花在哪、回收效率如何**"的第一手数据。

### 3.3 `memory.reclaim`：主动回收

`memory.reclaim` 是一个**只写**接口，向它写入字节数即可**主动触发该 cgroup 的回收**：

```
echo "1G" > memory.reclaim
```

它把"回收"从纯被动（等水线低了内核才动手）变成**用户态可主动驱动**的动作：一个 proactive reclaimer 可以持续向 memcg 小步"探针式"回收，既能让 LRU 持续保持有序（工作集估计更准），也能更确定地腾出内存做 overcommit。文档同时提醒：内核可能**多收或少收**，若回收量不足会返回 `-EAGAIN`，可带 swappiness 参数微调。该接口在 **Linux 5.19**（2022-07-31）引入。

### 3.4 `memory.pressure`：per-cgroup PSI

`memory.pressure` 是只读文件，暴露该 cgroup 的 **PSI（Pressure Stall Information，压力滞留信息）**：`some`（至少一个任务因内存而停顿的时间占比）与 `full`（所有任务同时停顿的占比），各给 10s/60s/300s 滑动平均加累计值。`full` 非零意味着严重内存压力，往往是 OOM 临近的强信号。

PSI 本体在 **Linux 4.20** 引入；在挂载了 cgroup v2 的系统上，每个 cgroup 子目录都带 `cpu.pressure` / `memory.pressure` / `io.pressure`，格式与 `/proc/pressure/*` 相同。**这正是 [A8](A08-压力与低内存终止.md) 里 lmkd 用 PSI 监视器替代旧 vmpressure 的数据来源**——但 PSI 只负责"报告压力多大"，"压力大了杀谁"是 A8 的事。

## 4. 历史：为什么演变成今天这样（v1 → v2）

memcg 的演进主线是**从 v1 的"多层级、各控制器各自为政"走向 v2 的"统一层级（unified hierarchy）"**：

- **cgroup v1**：每种资源（memory / cpu / blkio…）各挂一棵独立层级树，一个进程在不同控制器里可处于不同分组。内存侧靠 `memory.limit_in_bytes`（硬限）+ `memory.soft_limit_in_bytes`（软限，回收时尽量压回）控制，软限的回收行为含糊、协同性差，且与 cpu/io 的回写、节流难以联动。
- **cgroup v2**：所有控制器**共用一棵统一层级**，一个 cgroup 同时受多控制器约束，使"内存压力 ↔ I/O 回写 ↔ CPU 节流"能在同一组上协同。内存接口被**重写为 min/low/high/max 四道闸**，语义远比 v1 的 limit/soft_limit 清晰：`high` 提供了 v1 没有的"节流而不杀"中间态，`min/low` 把"保护"分成硬/软两级。

此后的增量都是在 v2 这个统一框架上"补主动控制面"：**PSI（4.20）**让压力可被量化观测，**`memory.reclaim`（5.19）**让回收可被用户态主动驱动。一条清晰的"从被动限额 → 可观测、可主动调控"的脉络。

> **Android 的迁移**是这条线上的现实注脚：Android 长期基于 memcg **v1**（用 per-app 分组做差异化 swappiness 与计量），近年才在向 **v2 迁移**（相关 patch 约在 2023 年推进；据 T.J. Mercier 的 LPC 分享）。迁移的动因正是 v2 的统一层级与 `memory.reclaim` / `memory.swap` / PSI 这套更现代的控制面。

## 5. 现状与平台差异

| 维度 | Android (Linux) | iOS / Darwin | HarmonyOS |
|---|---|---|---|
| 分组机制 | memcg（v1 为主，迁 v2 中） | 无 cgroup；走 Jetsam 的 jetsam band 优先级 | 待核实（Linux 基座设备可用 memcg） |
| 用途 | per-app 分组：差异化 swappiness、计量、组内回收 | 按"内存压力 + 优先级带"管理，而非配额闸 | 待核实 |
| 压力信号 | PSI（lmkd 监视器） | `memorystatus` 压力等级 | 待核实 |

要点：**memcg 是 Linux 阵营特有的"配额 + 分组"抽象**；iOS 没有等价的 cgroup 层，它用 jetsam band（优先级带）+ `memorystatus` 压力来决定取舍——同是"按重要性分组"，但 iOS 不走"给每组划字节配额"的路子。跨平台对比时务必区分这两套术语（详见 [A8](A08-压力与低内存终止.md)）。

## 6. 趋势与未解问题

- **主动回收常态化**：`memory.reclaim` + 用户态 proactive reclaimer 正成为 overcommit 与分层内存（A15）的基础设施——持续小步回收以维持准确的工作集估计，是冷热识别（[A5](A05-冷热识别的演进.md)）与主动腾挪的交汇点。
- **PSI 驱动的精细调度**：per-cgroup `memory.pressure` 让"压力反馈环"下沉到每个 App 组，趋势是用 PSI 阈值驱动更早、更温和的干预（节流 / 主动回收），把"杀进程"尽量后推（[A8](A08-压力与低内存终止.md)）。
- **Android v1→v2 收尾**：迁移落地后，Android 才能完整吃到 v2 统一层级与现代接口；当前 v1/v2 并存期的兼容与行为差异仍是工程难点。
- **未解问题**：组内 LRU 与全局回收的公平性、`memory.high` 节流对前台延迟的副作用、`memory.reclaim` "多收/少收"的可控性，都还在持续调优中。

## 7. 配合与依赖（跨层耦合）

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| memcg → 回收 | memcg 是回收的**作用域**：越 high/max 即在组内触发回收 | [A4](A04-回收总论.md) |
| memcg → per-memcg LRU | 每组独立 LRU，回收按组遍历（MGLRU 亦 per-memcg） | [A5](A05-冷热识别的演进.md) |
| memcg → PSI → lmkd | `memory.pressure` 把组内停顿喂给用户态决策器 | [A8](A08-压力与低内存终止.md) |
| **memcg ↮ 全局杀进程** | memcg 只管配额边界与组内 OOM；"系统级杀谁"在 A8 | **[A8](A08-压力与低内存终止.md)** |
| memcg ↔ swap | `memory.swap.*` + 组级 swappiness 决定换出倾向 | [A6 压缩与换页](A06-压缩与换页.md) |

> **本篇与 A8 的边界再强调一次**：memcg 是"局部配额裁判"——越界先回收自己、撞硬墙才动**组内** OOM；而"全局内存告急、跨进程地选一个牺牲者"是 [A8](A08-压力与低内存终止.md) 的 LMKD / Jetsam / 全局 OOM 的职责。把 memcg 当成"全局杀进程的开关"是常见误解。

## 8. 实测 / 观测点

- `cat /sys/fs/cgroup/<组>/memory.current`：该组当前总占用；
- `cat .../memory.stat`：分类占用 + 回收统计（anon/file/slab/refault…）；
- `cat .../memory.max` / `memory.high` / `memory.min` / `memory.low`：当前四道闸的值；
- `echo 64M > .../memory.reclaim`：手动触发组内回收，观察 `memory.current` 回落（5.19+）；
- `cat .../memory.pressure`：该组的内存 PSI（some/full 的 10/60/300s 均值）；
- `cat .../memory.events`：low/high/max/oom/oom_kill 的累计次数（排查"是被节流还是被 OOM"）；
- Android 上：`/dev/memcg/` 下的 per-app 分组（v1）、`dumpsys meminfo` 的按 App 计量（度量细节见 [A13](A13-内存度量与排障.md)）。

## 9. 来源与延伸阅读

- cgroup v2 内存控制器接口（min/low/high/max、stat、reclaim、pressure、events 语义）：[Control Group v2 — Kernel docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- `memory.reclaim` 设计与动机：[memcg: introduce per-memcg proactive reclaim (LWN)](https://lwn.net/Articles/892328/)、[PATCH v4 1/4: memcg per-memcg reclaim interface (lore)](https://lore.kernel.org/linux-mm/20220421234426.3494842-2-yosryahmed@google.com/)
- `memory.reclaim` 引入版本（5.19，2022-07-31）：[Linux 5.19 (kernelnewbies)](https://kernelnewbies.org/Linux_5.19)
- PSI 与 per-cgroup `memory.pressure`（PSI 自 4.20）：[PSI — Pressure Stall Information (Kernel docs)](https://docs.kernel.org/accounting/psi.html)
- cgroup v1 内存控制器（历史对照：limit_in_bytes / soft_limit）：[Memory Resource Controller (Kernel docs, v1)](https://docs.kernel.org/admin-guide/cgroup-v1/memory.html)
- Android 使用 memcg 与 v1→v2 迁移：[Low memory killer daemon (AOSP)](https://source.android.com/docs/core/perf/lmkd)、[Android: memcg v1 → v2, T.J. Mercier (LPC 2023 slides)](https://lpc.events/event/17/contributions/1553/attachments/1355/2709/03_Android_%20memcg%20v1%20-_%20v2.pdf)
- 内核源码锚点：`mm/memcontrol.c`、`mm/vmscan.c`（memcg 回收路径）、`kernel/sched/psi.c`

> **待核实 / 待补**：HarmonyOS 的内核基座是否启用 memcg 及其分组策略；Android v1→v2 迁移在各厂商 GKI 上的实际落地版本与机型覆盖；`memory.high` 节流对前台 App 端到端延迟的量化影响。

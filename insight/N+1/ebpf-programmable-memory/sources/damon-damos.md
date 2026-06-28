# DAMON / DAMOS — 源笔记

DAMON = Data Access MONitor；DAMOS = DAMON-based Operation Schemes（访问感知的操作方案）。
作者：SeongJae Park（最初 Amazon，现 Meta/上游维护者）。mainline 自 Linux v5.15；DAMON_RECLAIM 自 v5.16。

## 来源 1：LWN「Using DAMON for proactive reclaim」
- 作者：Jonathan Corbet, LWN.net, 2021
- URL: https://lwn.net/Articles/863753/
- 关键数字：
  - **监控开销极低**：监控生产系统 **70 GB** 内存、每 **5 ms** 采样一次，消耗**不到 1%** 单核 CPU 时间。
  - 无约束（unconstrained）回收可释放接近一半可用内存，但 CPU 代价约为**单核的 12%**。
  - 当被回收内存被重新访问导致换页增加时，负载放缓**略高于 5%**。
- DAMOS 机制：新增 `pageout` 方案，作用于**物理页**（而非虚拟地址空间）；支持
  - 内存配额（字节/时间单位）、CPU 时间配额、
  - 空闲内存上/下**水位（watermark）**触发，
  - 按区域**大小、age（年龄）、访问频率**排序优先级。

## 来源 2：LWN「Introduce DAMON-based Proactive Reclamation」+ damonitor 文档
- URL: https://lwn.net/Articles/858682/ ；https://damonitor.github.io/
- 关键数字（RFC 实测，v5.12 + ZRAM swap，10 GB/s 限速）：
  - **内存节省 32%**，运行时开销仅 **1.91%**，
  - 仅消耗单核 CPU 的 **5.72%**，其中访问模式监控本身约 **1.448%** 单核 CPU。

## 来源 3：OSS NA 2025「Self-Driving DAMON/S: Controlled and Automated Access-aware Efficient Systems」
- 报告人：SeongJae Park
- URL: https://static.sched.com/hosted_files/ossna2025/16/damon_ossna25.pdf
- 要点：
  - DAMOS 可实现一系列访问感知方案：**proactive reclaim、access-aware THP（按访问热度提升大页）、memory tiering（分层放置）**。
  - DAMOS 动作集合含 `pageout`、`hugepage`、`nohugepage`、`lru_prio`、`lru_deprio`、`migrate_hot/cold` 等——这正是「可编程内存策略」在上游内核的现实落点。
  - 自调（self-tuned / auto-tuning）：上层只给目标（如「保持 X% 空闲」），DAMON 自动调采样与配额，**监控开销上界可由用户配置**，与被监控内存大小无关。

## 论文级判断
- DAMON/DAMOS 是端侧「访问感知、可编程回收/提升」最成熟、已在 mainline 的机制：
  采样开销 <1% 单核即可驱动 reclaim、THP 提升、分层等策略，
  是把固定 kswapd 水位 / 全有全无 THP 改造为**自适应**策略的关键支点。

# 主动回收：从「撞水位才救火」到「按节奏 + 反馈环驱动」

> 一份「演进前 vs 演进后」的对照调研，聚焦 Linux 回收路径的**触发方式**。锚点文章：[A16a — LRU 主动扫描](../../advanced/A16a-LRU主动扫描.md)。原方案 `kswapd` + 直接回收只在水线触发，本质是**救火**机制。演进方案在它之上叠了三层：（1）一个便宜的扫描器（MGLRU 页表 aging 或 DAMON 区域采样），（2）一个可定向 per-memcg 的入口（`memory.reclaim`），（3）一个反馈控制器（Meta 的 Senpai/TMO 用户态，或 DAMOS 的 aim-oriented 自调）用 PSI 决定该多激进。数据中心实测可在不可见慢化下省下**每台服务器 20–32% 内存**。手机上 MGLRU 扫描器已随 Android 14 GKI 落地，**控制器那半**还是厂商各自做，没有统一基线。

## 1. 范围与方法

**调研对象。** 这里说的「主动回收」专指**把回收的「触发」从「水位被撞」改成「节奏 + 反馈信号」**——回收算法本身没换，挑哪页冷还是 LRU/MGLRU/DAMON 那套；变的只是「什么时候去看一眼、按多狠的力度推」。

**原方案。** 被动回收。内存不断分配把空闲池压到 low 水线，`kswapd` 醒来扫 LRU 尾巴，扫到回到 high 水线为止；扫不动了就进**直接回收**，由分配路径**同步**地扫 LRU——分配的那个线程为这段延迟买单。Android 上再扛不住时由 `lmkd` 按 `oom_score_adj`（前台/可见/后台/缓存）开杀。

**演进方案。** 主动回收，三层叠起来：（1）**便宜的扫描器**——MGLRU 的 aging 走查进程页表批量判冷热；或 DAMON 把地址空间切区域、每个区域抽样几个页，扫描成本与区域数成正比，**与内存大小解耦**。（2）**可定向的入口**——cgroup v2 的 `memory.reclaim` 是一个**只写**接口，用户态写「从这个 memcg 回收 N 字节」即可，文档明确声明它**不代表有内存压力**，所以不会带动 socket-mem 等压力联动副作用。（3）**反馈控制器**——Meta 的 Senpai/TMO 用户态循环，以及内核的 DAMOS aim-oriented 自调节，都把 **PSI 当反馈信号**：PSI 低于阈值就调高激进度，超过阈值就退回。

**资料来源。** 14 条：内核文档（MGLRU、cgroup-v2 `memory.reclaim`、DAMON_RECLAIM、PSI），LWN 一系列跟踪上游补丁的长文，Meta TMO 工程博客（生产数字），Senpai GitHub README，以及 2024 年的一篇云上 VM 主动回收论文（arXiv 2409.13327）。下表里的所有数字在 §9 都能一一对到来源。

## 2. 问题背景

**系统要干的事是什么。** 让分配快、让重要工作驻留得住、压力来了别让整机翻车。在服务器上就是「高利用率而不出尾延迟」，在手机上就是「前台不掉帧、不被误杀」。

**为什么这件事变难。** 三个约束撞到一起：（1）经典回收**唯一**的触发信号是**水位**——它响起来时，工作负载其实早已经感到压力了，所以它最显眼的效果是「直接回收阻塞分配」；（2）**LRU 尾巴是个局部视野**——它没法告诉运维「过去几个小时你白白闲置了 20% 的内存」，那是一个**全局、统计**的问题；（3）回收的激进度应该由**工作负载真正在乎的指标**（延迟 / QoS）来钳，而不是由空闲页计数来钳。

**为什么原方案不够用了。** 数据中心里这笔账是可见的：TMO 在 Meta 数百万台服务器上量出**每台 20–32% 的内存**可以被卸载、且工作负载毫无可见慢化（[TMO 博客, 2022](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/)）。这么大的浪费意味着被动回收**根本就没问过**——直到水位敲它的门。在手机上情况更糟：`lmkd` 是水位之**后**才点火的，所以系统对压力的唯一反应就是杀掉一个 app。Agent 时代让这件事更难（长程后台推理把启发式当冷的那部分热住了），但底层批评——**"救火不是政策"**——其实 2018 年的手机和 2022 年的服务器同样适用。

## 3. 具体问题与瓶颈数据

### 具体问题

1. **直接回收阻塞分配。** `kswapd` 跟不上就转直接回收，分配线程同步去扫 LRU 被阻塞。PSI 的 `memory.full` 量的就是这件事（[PSI 文档](https://docs.kernel.org/accounting/psi.html)）。
2. **缺一个「巡看一遍」的通道。** 经典回收只往 LRU 尾巴扫到能填上当前缺口为止。没有主动扫描，就**没人会去问**「所有匿名页里，过去两分钟有 30% 都没碰过吗」。
3. **缺一个定向回收的原语。** Linux 5.19（2022）之前，用户态没办法对内核说「从这个 cgroup 回收 1 GB」而不顺带制造一个**假的内存压力**（那会触发 socket-mem 调整等副作用）。`memory.reclaim` 把这个口子补上（[cgroup-v2 文档](https://docs.kernel.org/admin-guide/cgroup-v2.html)）。
4. **调参打架。** DAMOS aim-oriented 自调之前，管理员要给 DAMON_RECLAIM 调 6 个相互耦合的旋钮（min_age、quota_sz、quota_ms、watermark_high/mid/low），跨负载调可靠性差。

### 瓶颈数据

下面这些是「为什么主动回收值得做」的实证。每个数字 §9 都有源。

| 信号 | 数值 | 含义 | 来源 |
|---|---|---|---|
| 每台服务器可卸载、且无可见慢化的内存比例（TMO 生产） | **20–32%** | 被动回收在 Meta 整队列上把每台 1/5 到 1/3 的 RAM **白闲着**。 | [TMO 博客 2022](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) |
| 压缩内存后端贡献的回收比例 | **7–12%** | Senpai 节奏推下来、由 zswap 一类压缩吃掉的"温冷"。 | 同上 |
| ML 负载下 SSD 后端贡献的回收比例 | **10–19%** | LRU 水线永远到不了的长尾冷页。 | 同上 |
| Senpai 控制环步长 | **6 s** | 节奏在秒级——慢到 PSI 可用作反馈，快到能在工作负载感到压力之前响应。 | TMO 博客 |
| MGLRU 在 Android 上线后 `kswapd` CPU 占用变化 | **−40%** | Google 整队列实测——页表 aging 比 rmap 反查便宜得多。 | MGLRU 补丁 cover letter / [LWN 1072866](https://lwn.net/Articles/1072866/) |
| 同上的 `lmkd` p75 杀进程率变化 | **−85%** | 同一组实测——冷热判得更准，少杀很多 app。 | 同上 |
| 同上的 app 启动 p50 耗时变化 | **−18%** | 启动热路径上少做回收。 | 同上 |
| DAMON_RECLAIM 节省内存（5.12 + zram 实验） | **32%** | 在节流限速下主动腾冷页。 | [LWN 858682 cover letter](https://lwn.net/Articles/858682/) |
| 同实验下的运行时开销 | **1.91%** | 扫描本身比它救回的小很多。 | 同上 |
| DAMOS 自调可见旋钮 | **6 → 1** | 一个目标（如「过去 10 s `some` memory PSI ≤ 0.5%」）替掉六个手调旋钮。 | [LWN 951195](https://lwn.net/Articles/951195/) |

**怎么看这张表。** TMO 的 20–32% 是瓶颈论证：被动回收在生产里**把一台服务器约 1/3 的 RAM 都荒着**。Google 那组数字是手机侧的并行论证——光是 MGLRU 这个更便宜的扫描器（**还没**叠 controller 反馈环），就把冷热误判减到 lmkd p75 杀少 85%、app 启动 p50 快 18%。

## 4. 架构图：原方案 vs 演进方案

两张图用同样的组件、同样的布局；演进图里和原图不一样的地方用 `*` 标。

**原方案——被动回收**

```
   +-----------+   alloc()    +-----------+
   |  Process  | -----------> |  Kernel   |
   +-----------+              |   (mm)    |
                              +-----+-----+
                                    |
                                    | 水位检查
                                    v
                              +-----------+
                              |  Free     |
                              |  pool     |
                              +-----+-----+
                                    | 跌破 low
                                    v
                              +-----------+
                              |  kswapd   |  扫 LRU 尾巴
                              | (kthread) |  扫到回到 high
                              +-----+-----+
                                    |
                                    | 还不够 ->
                                    v
                              +-----------+
                              |  直接回收 |  分配路径里
                              |  (direct  |  同步扫
                              |  reclaim) |  (阻塞)
                              +-----+-----+
                                    |
                                    v
                              +-----------+
                              |  LRU 尾巴 |
                              +-----------+
```

*原方案：**唯一**的触发是"已经快没内存了"。`kswapd` 救火；救不动就让分配线程自己扫，请求方付延迟。*

**演进方案——主动回收（扫描器 + 入口 + 控制器）**

```
   +-----------+              +-----------+
   |  Process  |              |  Kernel   |
   +-----------+              |   (mm)    |
                              +-----+-----+
                                    ^
                                    |
   +-----------+                    |
   |  工作负载 | -- PSI 采样 ---+   |
   |  metrics  |                |   |
   +-----------+                v   |
                              +---------------+
                              | * 控制器      |
                              |   (Senpai/TMO |
                              |    用户态，   |
                              |    或 DAMOS   |
                              |    内核态)    |
                              +-------+-------+
                                      |
                                      | * 按节奏
                                      |   写 memory.reclaim N
                                      v
                              +-------------+
                              | * 便宜扫描器|
                              |   - MGLRU   |
                              |     aging   |
                              |   - DAMON   |
                              |     区域采样|
                              +-----+-------+
                                    |
                                    v
                              +-------------+
                              | LRU 页      |
                              +-----+-------+
                                    | 水位还没敲门
                                    | 就已经腾完，
                                    | 留出 headroom
                                    v
                              +-------------+
                              |  Free pool  | <-- 持有 headroom
                              +-------------+   直接回收基本
                                                不再触发
```

*演进方案：控制器按节奏（生产里 Senpai ≈ 每 6 s）驱动便宜扫描器；PSI 反馈给"该多狠"；`memory.reclaim` 是定向的只写入口；回收在分配线程感到压力之**前**就完成了。*

## 5. 演进方案解决了什么 / 没解决什么

### 解决了什么

- **「直接回收阻塞分配」** —— 控制器在空闲池里留 headroom，分配进来时水位还没动；直接回收（被动回收最显眼的代价）只在 fallback 时才触发。TMO 生产里在工作负载不可见慢化下卸载 20–32% 内存（[TMO 博客](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/)）。
- **「缺一个巡看一遍的通道」** —— 两种扫描器（MGLRU aging、DAMON 区域采样）都维护一个**常驻**的全局冷热视图，不再只看 LRU 尾巴。MGLRU 的 debugfs `lru_gen` 还直接给出工作集直方图（[MGLRU 文档](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)）。
- **「缺一个定向回收的原语」** —— `memory.reclaim` 提供了一个，并且明确**不**抬升 cgroup 的压力计数器，与内核其它部分组合时不带副作用（[cgroup-v2 文档](https://docs.kernel.org/admin-guide/cgroup-v2.html)）。
- **「调参打架」** —— DAMOS aim-oriented 自调把 6 个旋钮收成 1 个**目标**（如「过去 10 s `some` memory PSI ≤ 0.5%」），内核反馈调节每秒配额（[LWN 951195](https://lwn.net/Articles/951195/)）；后续把目标细化到 per-memcg、per-NUMA 节点（[LWN 1026213](https://lwn.net/Articles/1026213/)）。

### 没解决什么

- **扫描本身不免费。** DAMON_RECLAIM 报告的 1.91% 运行时开销虽然小，但**是真实的**；在手机上的电池预算下，**常驻**这种 1.91% 可能也不可接受。务实的答案是「低压时低节奏、空闲时几乎不扫」。**目前没有把节奏挂在能耗预算上的上游旋钮**。
- **回收目标不总是 PSI。** 手机上更合适的目标可能涉及电流和闪存写入预算，而不只是 PSI。锚点文章 §6 把这件事称作「能耗感知反馈环」——**目前没有公开的手机基线把这件事串起来**。
- **手机端控制器那半没出货。** MGLRU 的**扫描器**已经随 Android 14 GKI 出货（Google 那组 40% / 85% / 18% 是真实生产数据）；**控制器**——谁、按什么节奏、对什么目标写 `memory.reclaim` 或 `lru_gen`——是 OEM 用户态、没有标准。所以"手机主动回收"现在更像扫描器升级、还不是反馈环。
- **per-node 主动回收 API 还在吵**（[per-node 接口讨论, LKML 2024](https://lkml.iu.edu/hypermail/linux/kernel/2409.0/05920.html)）—— "从 X 节点回收 N 字节" 的用户接口形态还没定。

## 6. 对比表

每个单元格都是数字、布尔，或 `n/a（原因）`；每一行都有来源。**至少有一行是诚实的折衷**——常驻后台 CPU 成本——以及一行**部署回归**——手机端 controller 半未出货。

| 维度 | 原方案：被动回收 | 演进方案：主动回收 | 改善 | 来源 |
|---|---|---|---|---|
| 触发 | 水位 / OOM | 节奏（约 6 s）+ PSI 反馈 | 新行为 | [TMO 博客](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) |
| 无慢化下每台服务器可卸载内存 | 0%（无机制） | 20–32%（生产） | **+20–32%** | TMO 博客 |
| Android app 启动 p50 耗时（MGLRU 上线对照） | 基线 | −18% | **−18%** | [LWN 1072866](https://lwn.net/Articles/1072866/) |
| Android `lmkd` p75 杀进程率（同上） | 基线 | −85% | **−85%** | 同上 |
| Android `kswapd` CPU 占用（同上） | 基线 | −40% | **−40%** | 同上 |
| DAMON_RECLAIM 节省内存（5.12 cover letter 实验） | n/a（无机制） | 32% | 新能力 | [LWN 858682](https://lwn.net/Articles/858682/) |
| DAMON_RECLAIM 运行时开销（同实验） | 0%（无后台扫描） | 1.91% | **−1.91%**（后台扫描的代价） | 同上 |
| DAMON 通路可见旋钮数 | 6（min_age、quota_sz、quota_ms、watermark_high/mid/low） | 1（目标，如 PSI ≤ 0.5%） | **6 → 1** | [LWN 951195](https://lwn.net/Articles/951195/) |
| per-memcg 定向回收原语 | 无（只有 `oom_score_adj` 与水位触发） | `memory.reclaim`（只写、无压力副作用） | 新能力 | [cgroup-v2 文档](https://docs.kernel.org/admin-guide/cgroup-v2.html) |
| 手机端 controller 半出货状态 | n/a（无控制器） | 未标准化、OEM 用户态各做各的 | **0**（controller 半未出货） | A16a §5 |

## 7. 一词概括

**Proactive**（主动） —— 演进方案的根本变化在于：回收按**节奏 + 反馈目标**跑、而不是被水位踢出来跑；一个便宜的扫描器（MGLRU aging 或 DAMON 采样）维护一个**常驻**的全局冷热视图，一个 PSI 驱动的控制器（Senpai/TMO 在生产里**约 6 s** 一拍，或 DAMOS 在内核态）通过 `memory.reclaim` 把工作负载的压力钳在目标之下。生产实测的收益：**20–32%** 每台服务器内存被卸载、且工作负载不可见慢化（[TMO 2022](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/)），Android 上 lmkd p75 杀少 **85%**、app 启动 p50 快 **18%**（Google MGLRU 整队列实测）——代价是一个小但**常驻**的后台扫描开销（DAMON_RECLAIM cover letter 报 **1.91%**）。

## 8. 开放问题与说明

- **MGLRU 生产数字是厂方报告。** 40% / 85% / 18% 这组 Google 数字来自 MGLRU 补丁 cover letter 与 LWN/Phoronix 报道，**没有同行评审论文复现**。视作「Google 队列实测」而非「独立复现」。
- **DAMON_RECLAIM 的 32% / 1.91% 来自最初的 cover letter**（[LWN 858682](https://lwn.net/Articles/858682/)），不是当前的上游 admin guide；当前 admin guide 在实现演进中**已经删掉了这组具体数字**。引用时锚点定到 cover letter，别定到当前文档。
- **Senpai 的 PSI 阈值是自校准的。** Meta 不公开绝对目标；TMO 博客与 Senpai README 都回避。视为自适应。
- **2024–26 年没出现手机/Android 上的主动回收学术评测**。arXiv 2409.13327 是最接近的（云上 VM，比 Linux baseline 多省 25%），但**不是手机**，也不是直接对 MGLRU/DAMON 做基准对比。手机评测的空白是真的。
- **能耗感知反馈环**（锚点文章 §6 提的）——把电池和闪存写入预算折进 DAMOS 目标——还没有公开基线。这正是"手机主动回收"还差的一段。
- **per-node 主动回收 API 还没定**（[LKML 2024](https://lkml.iu.edu/hypermail/linux/kernel/2409.0/05920.html)）；最终的用户接口未必长得像 `memory.reclaim`。

## 9. 参考资料

1. Linux 内核项目。(2022). *Multi-Gen LRU Framework — admin guide*. [docs.kernel.org/admin-guide/mm/multigen_lru.html](https://docs.kernel.org/admin-guide/mm/multigen_lru.html) —— `min_ttl_ms` 稳定旋钮；debugfs `lru_gen` 工作集估计与主动回收（实验）。
2. Linux 内核项目。(2022). *Control Group v2 — Memory controller (`memory.reclaim`)*. [docs.kernel.org/admin-guide/cgroup-v2.html](https://docs.kernel.org/admin-guide/cgroup-v2.html) —— 只写、per-memcg 主动回收，无压力副作用。
3. Butt, S. & Ahmed, Y.（Google）(2022). *memcg: introduce per-memcg proactive reclaim*（v4 系列）. LWN. [lwn.net/Articles/892328/](https://lwn.net/Articles/892328/) —— 设计动机。
4. Park, S. (2021). *DAMON-based Reclamation*. [docs.kernel.org/admin-guide/mm/damon/reclaim.html](https://docs.kernel.org/admin-guide/mm/damon/reclaim.html) —— `min_age=120 s`、`quota_sz=128 MiB`、`quota_ms=10 ms`、`quota_reset_interval_ms=1 s`。
5. Corbet, J. (2021). *Using DAMON for proactive reclaim*. LWN. [lwn.net/Articles/863753/](https://lwn.net/Articles/863753/) —— DAMON 区域采样。
6. Park, S. (2021). *DAMON_RECLAIM*（补丁系列 cover letter）. LWN. [lwn.net/Articles/858682/](https://lwn.net/Articles/858682/) —— **节省内存 32%、运行时开销 1.91%**（5.12 + zram）。
7. Park, S. (2023). *DAMOS: Introduce Aim-oriented Feedback-driven Aggressiveness Auto Tuning*. LWN. [lwn.net/Articles/951195/](https://lwn.net/Articles/951195/) —— **6 → 1** 旋钮；示例目标「过去 10 s `some` memory PSI 0.5%」。
8. Park, S. (2025). *mm/damon: allow DAMOS auto-tuned for per-memcg per-node memory usage*. LWN. [lwn.net/Articles/1026213/](https://lwn.net/Articles/1026213/) —— per-memcg / per-node 目标；示例 **200 MiB/s** 迁移上限。
9. Weiner, J., Agarwal, N., Schatzberg, D. 等。(2022). *TMO: Transparent Memory Offloading in Datacenters*. ASPLOS '22. DOI 10.1145/3503222.3507731. PDF: [cs.cmu.edu/~dskarlat/publications/tmo_asplos22.pdf](https://www.cs.cmu.edu/~dskarlat/publications/tmo_asplos22.pdf). —— PSI 驱动的卸载框架。
10. Agarwal, N. & Weiner, J. (2022). *Transparent memory offloading: more memory at a fraction of the cost and power*. Meta Engineering blog. [engineering.fb.com/.../transparent-memory-offloading-...](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) —— 每台服务器省 **20–32%**；压缩后端 **7–12%**、ML 负载 SSD 后端 **10–19%**；Senpai 步长 **6 s**。
11. Meta. (2022). *Senpai — automated memory sizing for containerized apps*（GitHub README）. [github.com/facebookincubator/senpai](https://github.com/facebookincubator/senpai) —— 用户态 PSI 反馈控制环，建立在 `memory.high` / `memory.reclaim` 之上。
12. Linux 内核项目。(2018). *PSI — Pressure Stall Information*. [docs.kernel.org/accounting/psi.html](https://docs.kernel.org/accounting/psi.html) —— 每资源 `some` / `full`，可 poll 阈值。
13. Corbet, J. (2022). *Meta: Transparent memory offloading*. LWN. [lwn.net/Articles/898454/](https://lwn.net/Articles/898454/) —— 独立总结。
14. Corbet, J. (2024). *What is to be done about MGLRU?*. LWN. [lwn.net/Articles/1072866/](https://lwn.net/Articles/1072866/) —— MGLRU 落地状态；Google 整队列数字的手机侧上下文。
15. Pandurov, R. 等（华为及合作者）。(2024). *Flexible Swapping for the Cloud*. arXiv:2409.13327. [arxiv.org/abs/2409.13327](https://arxiv.org/abs/2409.13327) —— 云上 VM 主动回收；同等节省下比 Linux baseline 多 **+25%**。
16. 本项目 A16a 锚点。[advanced/A16a-LRU主动扫描.md](../../advanced/A16a-LRU主动扫描.md).

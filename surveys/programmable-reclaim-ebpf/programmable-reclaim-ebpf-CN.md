# 用 eBPF 把内存回收变得可编程：从「写死的启发式」到「可下发的策略」

> 一份「演进前 vs 演进后」的对照调研，聚焦 Linux 内存回收与 OOM 的**策略到底由谁定**。锚点文章：[A16b — eBPF 可编程回收策略（Android）](../../advanced/A16b-eBPF可编程回收策略-Android.md)。原方案里——`active/inactive` 规则、MGLRU 代际、OOM 评分、Android `lmkd` 阈值——全部**编译进内核与系统镜像**。演进方案把这些判决点放到 eBPF `struct_ops` 钩子之后，让策略以**可加载程序**的形式分发。`sched_ext`（Linux 6.12）已经证明这条路在一个核心子系统（CPU 调度）上走得通。落到 mm 上的提案（eBPF-mm、cachebpf、BPF-OOM、2026 LSF/MM 的"reclaim_ext"式讨论）拿出来的数据很硬——cachebpf 在异构存储基准上报告 **吞吐 +70% / p99 −58% / CPU ≤1.7%**——但**没有一个进 mm 主线**；而且 Android 那套签名 + 开机 `bpfloader` 模型注定：就算将来落地，也只是 OEM/Google 的策略下发杠杆，与第三方 App 无关。

## 1. 范围与方法

**调研对象。** 这里说的「可编程回收」专指：内核的回收/淘汰/OOM **判决**写在哪里？原世界里写在 `mm/` 的编译产物里——想改就得打 patch、重编内核。演进世界里把这些判决点放到 eBPF 回调后面，想改就**加载一个 `struct_ops` 程序**。机制本身是通用的；把它套到 mm 是最近几年的活，且**没进主线**。

**原方案。** 写死在内核里的 LRU/MGLRU/OOM 启发式 + Android 用户态 `lmkd`（写死的 `oom_score_adj` 分级与 PSI 阈值）+ `process_madvise(MADV_COLD/MADV_PAGEOUT)`——这一个**应用感知**的杠杆已经在 Android 上出货（Linux 5.4 起）。

**演进方案。** 在回收/淘汰/OOM 判决点上挂 eBPF `struct_ops` 钩子。机制和 `sched_ext` 给 CPU 调度用的那套一样，只是搬到 mm。具体形态：cachebpf 的 5 个 page-cache 钩子（`init` / `admit` / `access` / `evict` / `remove`）；eBPF-mm 在缺页路径上挂一个返回页大小（4 KiB / 64 KiB / 2 MiB）的钩子；BPF-OOM 的 `bpf_oom_kill_process` / `bpf_get_root_mem_cgroup` 等 kfunc 和「一个系统级 + 每个 memcg 一个」的处理器树。

**资料来源。** 12 条：AOSP 文档（Android eBPF 加载模型），内核文档 + Phoronix（`sched_ext`），LWN 对 LSF/MM-BPF 2026 的报道（"Controlling memory management with BPF"），三篇一手论文（cachebpf arXiv 2502.02750、eBPF-mm arXiv 2409.11220、LearnedCache arXiv 2605.26168），Gushchin 的 BPF-OOM 两篇 RFC 报道，最初的 `MADV_COLD/PAGEOUT` LWN 长文，LPC 2019 报告**少杀 15–30%** 的 Android slides，以及 Android `process_madvise` 的 man page。下表里每一个关键数字 §9 都有对应来源。

## 2. 问题背景

**系统要干的事是什么。** 在一台手机上——一个内核镜像要服务一代设备好几年——决定该保护谁、回收谁、必要时杀谁；负载是异构混合（前台 UI app、后台同步、agent 推理、系统服务）。

**为什么这件事变难。** 三个约束撞到一起：（1）合理的回收策略**依赖应用**，可 `mm/` 的判决**对应用一无所知**——内核看见的是一页，不是 "Llama 3.2 KV cache" 或 "Chrome tab cache"；（2）Android **GKI** 模型要求一份内核镜像跑很多机型、很多年——想让回收策略**按机型变**的厂商，无法去 patch `mm/`；（3）反过来把决策全推到用户态，又会丢掉**频率**——回收钩子每秒会触发几百次，用户态 daemon 只能粗节奏地引导（这正是 [A16a](../proactive-reclaim/proactive-reclaim-CN.md) 那条线）。

**为什么原方案不够用了。** 有两组证据。（1）`process_madvise(MADV_COLD/PAGEOUT)`——Android 出货的**唯一**一个应用感知杠杆——相比水位驱动的 baseline 让 lmkd 少杀 15–30%（[LPC 2019, Baghdasaryan](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf)；MADV_COLD 本身比 zap+swap **快 10×**，[Kim/LWN 793462](https://lwn.net/Articles/793462/)）——说明只要策略**能看到**工作负载，就会显著优于内核的瞎扫 LRU。（2）服务器侧 cachebpf 在 page cache 层量到了同样的效应：用一个匹配负载的 eBPF 策略（MRU / LFU / S3-FIFO / LHD）替掉 Linux 默认 page cache 淘汰，在异构 GET-SCAN 上拿到 **+70% 吞吐**、**−58% p99**，开销只有 **内存 ≤1.2% / CPU ≤1.7%**（[Cache is King, arXiv 2502.02750](https://arxiv.org/html/2502.02750v1)）。两组数字说的是同一件事：**一份镜像要跑所有负载时，写死的启发式会把很大一块好处留在桌上**。

## 3. 具体问题与瓶颈数据

### 具体问题

1. **策略对应用无感知。** 内核分不清「Agent KV cache（长程、可能回来）」和「后台 app tab（凉透了、可以扔）」。[A16b §3.4](../../advanced/A16b-eBPF可编程回收策略-Android.md) 把这称作"语义 VRegion vs 页面级 LRU"的缺口。
2. **策略难改。** 在经典 Linux 上改回收策略意味着 patch `mm/` + 重编内核；在 Android GKI 下尤其贵——厂商不拥有内核镜像，每多一段策略 diff 都要在版本间维护。
3. **OOM 是二元的——杀或不杀。** lmkd 一开杀就是终止进程一条路。Gushchin 的 BPF-OOM 动机："可编程 handler 可以**改去删一个 tmpfs 文件**或换一种处理方式"（[LWN 1034293](https://lwn.net/Articles/1034293/)）。
4. **手机端没有"下发策略"的通路。** Android eBPF 是生产级的，但**只在**开机时由签名 `bpfloader` 从 `/system/etc/bpf/` 加载、AID 门控（[AOSP docs](https://source.android.com/docs/core/architecture/kernel/bpf)）。就算 eBPF-mm 进了上游，第三方 app 也加载不了回收策略——**只有 OEM/Google 能**。

### 瓶颈数据

| 信号 | 数值 | 含义 | 来源 |
|---|---|---|---|
| cachebpf 端到端吞吐 vs Linux 默认 page cache | **+70%** | 匹配负载的策略在异构 GET-SCAN 上把吞吐拉了 70% 以上。 | [arXiv 2502.02750](https://arxiv.org/html/2502.02750v1) |
| 同基准的 p99 尾延迟 vs 默认 | **−58%** | 尾延迟砍掉一多半。 | 同上 |
| 写一个自定义淘汰策略的代码量 | **56–366 LoC** BPF | MRU、LFU、S3-FIFO、LHD 每个都能装进这个范围。 | 同上 |
| 可编程性的内存开销 | **cgroup 内存的 ≤1.2%** | 程序本身不是瓶颈。 | 同上 |
| 可编程性的 CPU 开销 | **每 I/O ≤1.7%** | 同上；verifier 限制了执行时间。 | 同上 |
| 应用感知 deactivation（MADV_COLD）vs zap+swap 到 zram | **约 10×** 更快 | 应用感知的"deactivate"比二元 kill 路径强一个数量级。 | [LWN 793462](https://lwn.net/Articles/793462/), Minchan Kim 原话 |
| Android lmkd 杀进程减少（用户态 `process_madvise`） | **15–30%** | 应用感知、语义回收在 Android 上已经出货并赚到了——eBPF 把它推广到内核内常驻策略。 | [LPC 2019, Baghdasaryan](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf) |
| LearnedCache vs FIFO 基线（跨负载中位） | **插入率 +10%** | 一个简单的感知机淘汰策略，BPF 实现，跨 50 次配对实验显著优于 FIFO。 | [arXiv 2605.26168](https://arxiv.org/abs/2605.26168) |
| `sched_ext` 上游合入 | **Linux 6.12** | 目前主线唯一的 `struct_ops` 可编程策略子系统，是 mm 的先例。 | [kernel docs](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html); [Phoronix](https://www.phoronix.com/news/Linux-6.12-Lands-sched-ext) |
| BPF-OOM 上游状态 | **14 补丁 RFC v1（2025-08-18），未合入** | mm 侧最接近的提案；LWN 1072538 报告 BPF-mm 提案至今**无一进主线**。 | [LWN 1034293](https://lwn.net/Articles/1034293/); [LWN 1072538](https://lwn.net/Articles/1072538/) |

**怎么看这张表。** 两个数字最关键：cachebpf 的 **+70% / −58%** 说明匹配负载的策略相对写死的 baseline 价值不小；`process_madvise` 的 **15–30%** 减杀说明这件事**已经在 Android 上生产兑现**——只不过是用户态的**一次性 poke**，不是内核内的常驻 BPF 策略。可编程回收要弥合的，就是把这个一次性 poke 变成**不重编内核就能下发的常驻策略**。

## 4. 架构图：原方案 vs 演进方案

**原方案——写死的 LRU + lmkd，`process_madvise` 作为唯一应用级杠杆**

```
   +-----------+                        +-----------+
   |  Process  |                        |  lmkd     |
   +-----+-----+                        | userspace |
         | 被杀                         | * 写死的  |
         |                              |   oom_adj |
         |        PSI 信号              |   阈值    |
         |     +----------------------> |           |
         |     |                        +-----+-----+
         |     |                              |
         |     |        kill PID              |
         |     |  <---------------------------+
         v     |
   +-----------+
   |  Kernel   |   * 写死的 LRU /
   |   mm/     |     active/inactive
   |           |     /MGLRU 规则
   |           |     /OOM 评分
   +-----+-----+     （全部编译进去）
         |
         | (可选) MADV_COLD / MADV_PAGEOUT
         | 通过 process_madvise(2) 由用户态触发
         v
   +-----------+
   |    LRU    |
   +-----------+
```

*原方案：所有回收/淘汰/OOM 规则编译进 `mm/`；`lmkd` 在用户态用写死的 `oom_score_adj` 分级 + PSI 阈值；唯一的应用感知杠杆是用户态触发的 `process_madvise` 系统调用。*

**演进方案——在判决点挂 eBPF `struct_ops` 钩子（上游提案，未合入）**

```
   +-----------+                        +---------------+
   |  Process  |                        | * 用户态      |
   +-----+-----+                        |   bpfloader   |
         |                              |   (Android:   |
         |                              |   /system/etc/|
         |                              |   bpf/，AID   |
         |                              |   门控、仅开机|
         |                              |   加载)       |
         |                              +-------+-------+
         |                                      | * 加载
         |                                      |   struct_ops
         |                                      v
         |                              +---------------+
         |                              | * BPF 程序    |
         |                              |   - PROTECT / |
         |                              |     EVICT /   |
         |                              |     PASS      |
         |                              |     (eBPF-mm) |
         |                              |   - admit /   |
         |                              |     access /  |
         |                              |     evict     |
         |                              |     (cachebpf)|
         |                              |   - bpf_oom_  |
         |                              |     kill_proc |
         |                              |     (BPF-OOM) |
         |                              +-------+-------+
         |                                      ^
         v                                      | * verifier 限定
   +-----------+    * 钩子回调                  | 的回调按页/事件
   |  Kernel   | -----------------------------+ | 返回判决
   |   mm/     |                                |
   |           | <------------------------------+
   +-----+-----+
         |
         | 回收路径在每个判决点
         | 都调一下 BPF 程序
         v
   +-----------+
   |    LRU    |
   +-----------+
```

*演进方案：内核回收路径在每个判决点回调 BPF 程序；程序经 verifier 校验（无死循环、无越界访存），返回 PROTECT/EVICT/PASS、或一个页大小、或一个待杀进程指针。Android 上，程序被签名 + AID 门控，只在开机时由 `/system/etc/bpf/` 加载——所以未来真要落地，也只能是 OEM 的策略，不是用户代码。*

## 5. 演进方案解决了什么 / 没解决什么

### 解决了什么

- **「策略对应用无感知」** —— BPF 程序能读 VMA 元数据、cgroup ID、文件路径，按这些判决。eBPF-mm 的原型把 per-region 建议经 DAMON 画像送进 fault 路径的页大小选择（[arXiv 2409.11220](https://arxiv.org/abs/2409.11220)）；cachebpf 把 per-cgroup 淘汰策略接到钩子（[arXiv 2502.02750](https://arxiv.org/html/2502.02750v1)）。两者都补上「内核看见页、看不见负载」这道缺口。
- **「策略难改」** —— `sched_ext` 已经证明：不重编内核也能下发策略，加载一个 `struct_ops` 模块，内核就在每个调度判决点回调它。出问题有 fallback（SysRq-S 强制切回 CFS，默认 `sched_ext.slice_bypass_us=5000 µs`），坏程序能被弹出去而不 panic（[kernel docs](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html)）。同样的形态原则上能搬到 mm。
- **「OOM 是二元的」** —— BPF-OOM 的 `bpf_oom_ops` 让 per-memcg 的 handler 做点别的事：删 tmpfs 文件、触发 `memory.reclaim`、换一个 victim（[LWN 1034293](https://lwn.net/Articles/1034293/)）。
- **「手机端没有下发策略的通路」** —— Android 开机 bpfloader 其实**就是**一条下发通路，只是它只对 OEM/Google 开放、不向第三方。对 GKI 下的厂商差异化来说，这反而是恰好的形态。

### 没解决什么

- **mm 侧的提案没有一个进主线。** LWN 1072538（2026 LSF/MM 报道）的结论是 "BPF-mm 提案至今**无一进主线**"——mm 维护者担心 ABI 稳定性（Hildenbrand："这是一个永久的 mm 特性吗？五年后内存管理长什么样没人知道"），甚至 Alexei Starovoitov 自己都说 `sched_ext` 可能就是个错误。所以 §4 演进图里的一切，都是"提案"，不是"出货"。
- **每页成本必须便宜。** 一个回收/淘汰钩子在繁忙系统上每秒可能触发几百万次。verifier 限了执行时间但**没把它变快**——每次调用的工作必须在微秒级，否则收益被吃光。cachebpf 之所以 CPU ≤1.7% 是因为它的钩子很短；eBPF-mm 的逐页选择也类似。但「对每个回收候选都跑一遍 PROTECT/EVICT/PASS」要小心设计。
- **语义 VRegion 映射在 BPF 程序之上。** 就算 eBPF 接好了，**app 或框架还是得把每个模块的数据放进可寻址的区域里**（VMA 边界或 ART region），程序才能"读到语义"。没有分配器的纪律，BPF 程序还是只能看到没有应用语义的碎片页。
- **Android 签名加载的约束是永久的。** 即便上面所有事明天都进了主线，Android 上**只有系统镜像 / OEM 能下发**回收策略。第三方"让我的 app 走另一条策略"这个口子**大概率永远不会开**——安全模型是对的，但这就给"手机上的可编程"画了天花板。

## 6. 对比表

每个单元格都是数字、布尔，或 `n/a（原因）`；每行都有来源。**至少有一行是诚实的回归**：上游 mm 半没合入；手机端 eBPF 没用在回收上。

| 维度 | 原方案：写死启发式 + lmkd | 演进方案：eBPF struct_ops 钩子（上游提案） | 改善 | 来源 |
|---|---|---|---|---|
| 异构存储基准吞吐 | 基线（默认 LRU page cache） | **+70%**（cachebpf） | **+70%** | [arXiv 2502.02750](https://arxiv.org/html/2502.02750v1) |
| 同基准的 p99 尾延迟 | 基线 | **−58%**（cachebpf） | **−58%** | 同上 |
| 写一个自定义淘汰策略所需代码 | 数千行内核 patch | **56–366 LoC** BPF | **~10×** 更少 | 同上 |
| 可编程性的内存开销 | 0%（无钩子） | **cgroup 内存的 ≤1.2%**（cachebpf） | **−1.2%**（可编程的代价） | 同上 |
| 可编程性的 CPU 开销 | 0% | **每 I/O ≤1.7%**（cachebpf） | **−1.7%**（可编程的代价） | 同上 |
| 「刚切后台 app」的语义回收速度 | n/a（无语义路径） | 比 zap+swap **快 10×**（MADV_COLD 实测，已出货） | **快一个数量级** | [LWN 793462](https://lwn.net/Articles/793462/) |
| Android lmkd 杀进程减少（用户态 `process_madvise`） | 基线 | **15–30%** | **−15–30%** | [LPC 2019](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf) |
| 主线里的可编程内核策略 | **sched_ext**（CPU 调度，6.12 起） | **mm 半 0 / 14 补丁 RFC**（BPF-OOM，2025-08-18，未合入） | **0 → 0**（mm 半未落地） | [LWN 1034293](https://lwn.net/Articles/1034293/); [LWN 1072538](https://lwn.net/Articles/1072538/) |
| Android 上 eBPF 出货用途 | 是：流量统计（Android 9 起）、tracing、GPU 内存 | 否：回收**不在** AOSP 的 eBPF 清单里 | **0**（回归：手机端不能部署） | [AOSP docs](https://source.android.com/docs/core/architecture/kernel/bpf) |
| 第三方 app 能否下发策略 | 不能 | 不能——Android 签名 + 开机 bpfloader 把它锁在 OEM 手里 | 不变 | [AOSP docs](https://source.android.com/docs/core/architecture/kernel/bpf) |

## 7. 一词概括

**Programmable**（可编程） —— 演进方案的根本变化是：回收、淘汰、OOM 的**判决**从编译进内核的 C 代码，变成**可加载的 BPF 程序**。cachebpf 在 page cache 层量出了这件事的收益（吞吐 **+70%**、p99 **−58%**、CPU 开销 **≤1.7%**、单个策略 **56–366 LoC**，[arXiv 2502.02750](https://arxiv.org/html/2502.02750v1)）；`sched_ext`（Linux 6.12，[kernel docs](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html)）说明同样的形态在**核心**内核策略上也跑得通。诚实的回归：mm 半**没合入**主线（[LWN 1072538](https://lwn.net/Articles/1072538/)），手机端就算合入也只是 OEM/Google 的下发杠杆，与第三方 App 无关。

## 8. 开放问题与说明

- **BPF-mm / cachebpf / BPF-OOM 没一个进主线。** LWN 1072538（2026）是当下"事态报告"的权威长文，结论是 mm 侧 BPF 提案**至今无一进主线**。落地时间表的锚点定到「不是很快」。
- **15–30% lmkd 减杀是 2019 LPC 的 slide。** 来自 Google 内部的 dogfood + 压力测试；slide 公开，但**不是同行评审**。视作"Google 自报"。
- **cachebpf 的数字是论文在存储基准上的报告**（YCSB Zipfian、文件搜索、GET-SCAN），**不是**在 Android UI 回收上测的。定性方向能迁移，绝对数字不能。
- **"reclaim_ext" 这个名字。** 锚点文章用它作伞标签；LWN 1072538 **没有**把它当作上游项目名。视作作者综合命名，不是项目代号。
- **`sched_ext` 的生产开销没在一手源里量化。** Phoronix 和内核文档讲了正确性和 fallback 路径，但没量化运行时成本。"`sched_ext` 能跑，所以 BPF-mm 能跑"的类比是**架构方向**对，**不是 benchmark 背书**。
- **Android 的签名模型。** AOSP 文档讲了 AID 门控和开机 `bpfloader`，没明确提**每对象代码签名**——靠的是系统分区完整性（dm-verity）保签名镜像那张大牌。
- **手机端 per-app 策略注入在结构上被堵死。** 即便 eBPF-mm 全套进了上游，Android 加载模型还是把回收策略锁在 OEM。这可能是 feature 不是 bug，但它给「手机上的可编程回收」画了天花板。

## 9. 参考资料

1. Android 开源项目。(2024). *Extend the kernel with eBPF*. [source.android.com/docs/core/architecture/kernel/bpf](https://source.android.com/docs/core/architecture/kernel/bpf) —— `bpfloader`、`/system/etc/bpf/`、pin 到 `/sys/fs/bpf/`、AID 门控。
2. Android 开源项目。(2024). *eBPF traffic monitoring*. [source.android.com/docs/core/data/ebpf-traffic-monitor](https://source.android.com/docs/core/data/ebpf-traffic-monitor) —— 自 Android 9 / kernel ≥ 4.9 起强制；替代 `xt_qtaguid`。
3. Linux 内核项目。(2024). *Extensible Scheduler Class*. [kernel.org/doc/html/latest/scheduler/sched-ext.html](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html) —— `struct_ops` 回调；SysRq-S fallback；默认 `slice_bypass_us=5000`。
4. Larabel, M. (2024). *Sched_ext Merged For Linux 6.12*. Phoronix. [phoronix.com/news/Linux-6.12-Lands-sched-ext](https://www.phoronix.com/news/Linux-6.12-Lands-sched-ext) —— 主线合入确认。
5. Corbet, J. (2026). *Controlling memory management with BPF*. LWN. [lwn.net/Articles/1072538/](https://lwn.net/Articles/1072538/) —— 2026 LSF/MM/BPF 现状；"BPF-mm 提案至今无一进主线"。
6. Vainas, K., Karakostas, V. 等（NTUA）。(2024). *eBPF-mm: Userspace-guided memory management in Linux with eBPF*. arXiv:2409.11220. [arxiv.org/abs/2409.11220](https://arxiv.org/abs/2409.11220) —— 缺页路径钩子返回 4 KiB / 64 KiB / 2 MiB；由 DAMON 画像驱动。
7. *Cache is King: Smart Page Eviction with eBPF (cachebpf)*. (2025). arXiv:2502.02750. [arxiv.org/html/2502.02750v1](https://arxiv.org/html/2502.02750v1) —— 5 个 page cache 钩子；**吞吐 +70% / p99 −58%**；**内存 ≤1.2% / CPU ≤1.7%**；单策略 **56–366 LoC**。
8. *LearnedCache: eBPF-Integrated Perceptron-Based Eviction*. (2026). arXiv:2605.26168. [arxiv.org/abs/2605.26168](https://arxiv.org/abs/2605.26168) —— 中位 AUC ≈ 80%；插入率比 FIFO **+10%**。
9. Corbet, J. (2025). *mm: BPF OOM*. LWN. [lwn.net/Articles/1034293/](https://lwn.net/Articles/1034293/) —— Gushchin 14 补丁 RFC v1，2025-08-18；`bpf_oom_kill_process`、`bpf_get_root_mem_cgroup`、`bpf_out_of_memory`、`bpf_task_is_oom_victim` kfunc。
10. Corbet, J. (2025). *Custom out-of-memory killers in BPF*. LWN. [lwn.net/Articles/1019230/](https://lwn.net/Articles/1019230/) —— 更早的 RFC；`bpf_handle_psi_event` 与 `bpf_handle_out_of_memory`。
11. Kim, M. (2019). *Introduce MADV_COLD and MADV_PAGEOUT*. LWN. [lwn.net/Articles/793462/](https://lwn.net/Articles/793462/) —— 合入 Linux 5.4；"zapping 在 zram 上都比这慢 **10×**"。
12. Baghdasaryan, S. (2019). *Handling memory pressure on Android (application compaction)*. LPC 2019 slides. [lpc.events/.../Handling_memory_pressure_on_Android.pdf](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf) —— 用 `process_madvise(MADV_COLD/PAGEOUT)`，dogfood **少杀 15%**、压力测试 **最多少杀 30%**。
13. *process_madvise(2) — Linux manual page*. [man7.org/linux/man-pages/man2/process_madvise.2.html](https://man7.org/linux/man-pages/man2/process_madvise.2.html).
14. 本项目 A16b 锚点。[advanced/A16b-eBPF可编程回收策略-Android.md](../../advanced/A16b-eBPF可编程回收策略-Android.md).

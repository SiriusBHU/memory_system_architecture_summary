# A16a · LRU 主动扫描（被动回收 → 主动回收 / proactive reclaim）

> **一句话定位**：经典回收是**被动**的——等内存吃紧、水线告警、分配失败才动手挑冷页。本篇讲一条相反的思路：**在压力到来之前就主动去"扫描"内存、给页排冷热、提前把冷页腾走**。它是 A16 family「**冷热**」轴的系统侧第一题，回答"当 Agent 负载让冷热判断不再能靠场景拍脑袋时，内核凭什么、用什么节奏主动地看一遍内存"。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「2B 物理与回收侧」中 **LRU 冷热（A5）** 与 **回收（A4）** 两格的**主动化改造**——把 [A04 回收](../foundations/A04-回收总论.md) 的触发从"被动等水线"扩成"主动按节奏扫"。
> 🧭 **阅读前置**：先读 [A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md)（LRU→MGLRU→DAMON，本篇直接消费其"代际"与"可编程监控"）、[A04 回收总论](../foundations/A04-回收总论.md)（被动回收的整体路径与触发源）；冷页腾去哪见 [A06 压缩与换页](../foundations/A06-压缩与换页.md)；DAMON 细节见 [A15b DAMON 与分层内存实践](A15b-DAMON与分层内存实践.md)。
> 🌡️ **演进分级**：**演进厚 ⚡**——"主动回收"是一条仍在快速成形的线（接口几经反复、自调节策略刚成熟、终端落地未定型），**重点在 §2 负载动因、§4 历史 与 §6 趋势**。

---

## 1. 定位：它在地图上的哪一格

[A04 回收总论](../foundations/A04-回收总论.md) 讲的是回收的**被动主线**：分配走到低水线、`kswapd` 被唤醒、或直接回收（direct reclaim）在分配路径上同步挤页——**都由"内存不够了"这个事件触发**。[A05](../foundations/A05-冷热识别的演进.md) 讲的是回收的"瞄准镜"——LRU / MGLRU / DAMON 怎么判定哪页冷。

本篇把这两件事接起来问一个新问题：

> **能不能不等"内存不够"，就先主动扫一遍内存、把冷页提前腾走？** 这就是**主动扫描 / 主动回收（proactive reclaim）**。

它不是一个新子系统，而是**把"扫描—判冷热—回收"这条既有链路的触发权，从被动事件改成主动节奏**。"扫描"二字是关键：被动回收只在需要时扫描 LRU 的尾部；主动回收要**周期性地、低开销地把内存看一遍**，才能在压力之前就知道谁冷。

## 2. 负载动因：Agent 时代为什么"场景判冷热"会失效

这一篇属于 A16「冷热」轴。先按 [A16 总论](A16-前沿-Agent时代内存负载.md) 的终端立场把动因说清——**主动扫描不是数据中心的舶来品，而是被终端自己的负载逼出来的**。

终端过去能"偷懒"判冷热，靠的是一条朴素假设：

> **前台 app 热、后台 app 冷。** 用户在看的那个 app 的内存别动，切到后台的就可以压、可以杀。

[A08 压力与低内存终止](../foundations/A08-压力与低内存终止.md) 的 lmkd 正是这套思路的产物——按 `oom_score_adj`（前台/可见/后台/缓存的分级）决定先杀谁。这是一种**用"场景/前后台"近似冷热**的启发式，便宜且长期够用。

Agent 时代这条假设**三处同时塌**（对应 A16 三特征里的「冷热」）：

1. **后台不再冷**：一个端侧 agent 接了长程任务（持续推理、RAG 检索、工具调用、定时唤醒），**切到后台仍在跑、仍在频繁访问它的权重与 KV**。"后台=冷"直接失效。
2. **前后台同时热**：用户前台交互的同时，后台 agent 也活跃——内存里**同时存在多个热工作集**，不再是"一个前台热点 + 一片后台冷区"的干净图景。
3. **冷热更快、更结构化**：KV cache 的冷热由注意力稀疏决定、权重的冷热由"按层/按专家激活"决定（详见 [A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md)、[A16c 异构压缩](A16c-异构压缩CDSD.md)）——这种冷热**变化在毫秒级、且和"哪个 app 在前台"无关**，场景标签根本刻画不了。

三条合起来的结论：**当"它在前台吗"不再能回答"它热吗"，就只能回到内存本身去实测访问——主动、周期性地扫描，按真实访问给页排冷热。** 这正是被动回收给不了的：被动回收只在缺内存时看 LRU 尾巴，看不到"现在整机的冷热分布长什么样"，更没法在压力前就腾挪。主动扫描要补的就是这一块。

> 一句话动因：**前台/后台这个"场景代理变量"在 Agent 负载下与冷热解耦了，逼着系统从"按场景猜"退回"按访问扫"。**

## 3. 机制本体：什么叫"主动地扫描内存"

把"被动"与"主动"摆在一起看，差别在**触发**与**扫描范围**：

| 维度 | 被动回收（A04） | 主动扫描 / 主动回收 |
|---|---|---|
| 触发 | 水线告警 / 分配失败 / 直接回收 | **周期性节奏**，或外部策略按需下达 |
| 扫描什么 | LRU 非活跃链尾部，够用即止 | **周期性把（一部分）内存看一遍**，维护全局冷热视图 |
| 目的 | 救急——把 RSS 压回水线之上 | 预腾挪——压力到来前就把冷页换出，并**估准工作集** |
| 代价 | 抖动、direct reclaim 卡顿 | 扫描本身耗 CPU/电，节奏过激会无谓压解页 |

终端要让"主动扫描"可行，**扫描必须便宜**——否则为省内存烧的电得不偿失。这正是 [A05](../foundations/A05-冷热识别的演进.md) 那条演进线的价值，它给主动扫描准备了两种低开销的"扫描器"：

### 3.1 MGLRU 的 aging：用页表走查代替 rmap，把"扫描"做便宜

经典 LRU 的扫描贵在 **rmap 反向映射**：要判断一个物理页冷热，得反查所有映射它的 PTE。MGLRU 把这件事倒过来——**aging（老化）阶段直接正向走查进程页表**，批量清扫 Accessed 位、把仍被访问的页晋升到最新一代（generation）。内核文档把 MGLRU 的两个动作分得很清：

- **aging（产生新代际）**：扫描页表、给页重新排"代"——**这就是 MGLRU 内建的"主动扫描"**；
- **eviction（回收最老代）**：把最老一代里的页换出。

对外暴露的接口要分清稳定与实验：

- **稳定旋钮只有一个**——`/sys/kernel/mm/lru_gen/min_ttl_ms`：写入 `N`，保护"最近 N 毫秒的工作集"不被回收，是一个**抖动防护 / 压力泄洪阀**（文档建议 `N≈1000` 兼顾体验），超时仍护不住才触发 OOM。
- **主动回收的真正入口在 debugfs**——`/sys/kernel/debug/lru_gen`：可读出"各时间区间被访问页数的直方图"（= **工作集估计**），可写命令**主动产生新代际（提前 aging）或主动回收最老代**。文档明确这属于**实验特性、需由 userspace（"a job scheduler runs this command"）主动驱动**，不是开箱即用。

> 纠偏（沿用 [A15c §3.2](A15c-移动端分层内存与内存压缩前沿.md) 的提醒）：MGLRU 的"工作集估计 / 主动回收开箱即用"是误读——**那是实验性 debug 接口，要 userspace 写命令驱动**。

### 3.2 DAMON 的区域采样：让"扫描成本"与内存大小解耦

[A15b](A15b-DAMON与分层内存实践.md) 已详述：DAMON 不逐页统计，而是**把地址空间切成 region、对每个 region 抽样几个页**，一次采样的开销正比于 region 数而非页数——"把内存从 4GB 加到 4TB，监控开销几乎不变"。这使"周期性主动扫描整机内存"在能耗上变得可承受，是主动扫描在终端可行的另一块基石。DAMON 还能把监控直接接到动作（DAMOS），其中 `pageout`/`cold` 就是**访问感知的主动回收**。

### 3.3 谁来"按节奏"驱动：控制回路

有了便宜的扫描器，还缺一个**控制器**决定"多久扫一次、压多狠"。两种成熟形态：

- **内核内自调节**：DAMON_RECLAIM 把"主动回收"做成内核模块，并用 **aim-oriented 的配额自调节**——给一个目标（如某 PSI / 内存占用），DAMOS **欠目标就自动加大配额、超目标就自动收**，形成反馈回路（§4 详述）。
- **用户态控制回路**：Meta 的 **Senpai / TMO（Transparent Memory Offloading）**是范本——一个用户态 agent **持续施加"温和的"内存压力**：以 [A08](../foundations/A08-压力与低内存终止.md) 的 **PSI** 为反馈，压力低于阈值就调高回收速率、高于阈值就收手，通过 cgroup v2 的 `memory.reclaim` 把回收**定向**到目标 cgroup。

两者共性：**主动 ≠ 一味狠扫，而是"用一个可测的目标（PSI/占用）闭环调节扫描与回收的激进度"**。这正是终端最需要的——续航红线下，激进度必须能被自动钳住。

## 4. 历史：被动回收是怎么一步步"主动化"的

```
经典回收（kswapd/direct reclaim，按水线被动触发）
   │  痛点：只会救急，给不了"压力前预腾挪"，也估不准工作集
   ▼
① per-memcg 主动回收入口  memory.reclaim（cgroup v2，2022）
   │  只写接口：echo 1G > memory.reclaim，向某 cgroup 主动要回收
   │  文档强调：它触发的回收"不代表该 cgroup 有压力"
   ▼
② 便宜的扫描器就位  MGLRU（kernel 6.1，Android 14 GKI 默认）
   │  aging 走页表批量判冷热 + debugfs 工作集估计/主动回收（实验）
   ▼
③ 访问感知的主动回收  DAMON_RECLAIM（kernel 5.16）
   │  轻压力下用真实访问统计做主动回收，而非 LRU 近似
   ▼
④ 自调节激进度  DAMOS aim-oriented 配额自调节（2023–）
   │  给目标值，内核反馈回路自动增减回收配额
   ▼
⑤ 更细的作用域  DAMOS 配额按 per-memcg / per-node 自调（LWN 2024–25）
       + 讨论中的 per-node proactive reclaim 接口
```

几条线索值得点名：

- **入口先行**：`memory.reclaim`（2022）先把"主动要回收"这件事变成一个**只写接口**——它特别声明"**触发的回收不代表有内存压力**"，所以不会顺带拉高 socket 内存等压力联动；这是"主动"与"被动"在语义上被正式分开的标志（[per-memcg proactive reclaim, LWN](https://lwn.net/Articles/892328/)）。
- **从"近似"到"实测"**：DAMON_RECLAIM（5.16）让主动回收**基于真实访问统计**而非 LRU 的二级近似，这是"主动扫描"从"扫 LRU 链"升级到"扫访问"的关键一跳（[Using DAMON for proactive reclaim, LWN](https://lwn.net/Articles/863753/)）。
- **从"手调"到"自调"**：早期主动回收要管理员手动定回收量/冷阈值，极易调过头。DAMOS 的 **aim-oriented 配额自调节**把它变成反馈控制——"欠目标加配额、超目标减配额"，并进一步把配额目标细化到 **per-cgroup、per-NUMA 节点**（[DAMOS auto-tuned for per-memcg per-node memory usage, LWN](https://lwn.net/Articles/1026213/)）。
- **接口仍在反复**：连"按节点主动回收"这种基本能力都还在邮件列表讨论该不该新开 `memory.reclaim` 式的 per-node 接口（[per-node proactive reclaim interface, LKML 2024](https://lkml.iu.edu/hypermail/linux/kernel/2409.0/05920.html)）——**主动回收的用户接口尚未定型，待核实其最终形态与合入版本**。

## 5. 现状与平台差异

| 维度 | Android（Linux / GKI） | iOS / Darwin（XNU） | HarmonyOS |
|---|---|---|---|
| 主流回收形态 | **仍以被动为主**：lmkd 按 PSI 撞顶杀进程（[A08](../foundations/A08-压力与低内存终止.md)）；主动回收的**基础设施**（MGLRU 6.1、DAMON）已随 GKI 在位 | jetsam/memorystatus 被动响应低内存事件；compressed memory 吸收尖峰 | 待核实 |
| 主动扫描基础设施 | MGLRU `min_ttl_ms` 稳定可用；`lru_gen` debugfs 与 DAMON `pageout`/`cold` 可做主动回收 | 无 MGLRU/DAMON 对应物；XNU 自有 pageout 扫描器 | 待核实（[A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md) 无相关公开细节）；可编程主动感知方向见 [A16b XVM](A16b-XVM-eBPF的LRU主动感知优化.md) |
| 谁驱动、按什么节奏 | **厂商定制**：哪个 userspace 组件、以什么节奏调 `memory.reclaim`/`lru_gen` 属各家 GKI 黑魔法，**机型覆盖待核实** | 系统内建，外部不可编程 | 待核实 |

> **术语警示**：Android 的"主动回收"目前多指**用 MGLRU/DAMON 基础设施 + 厂商 userspace 策略**做的事；它与 iOS 的 `vm_pageout` 扫描线程**机制不同、别混**。lmkd 的"杀"是 [A15c](A15c-移动端分层内存与内存压缩前沿.md) 说的**硬手段**，主动扫描是**软手段**——前者保命、后者续航。

## 6. 趋势与未解问题 ← 本篇重心

- **激进度的自调节是主旋律，但目标函数在终端要改写**：Senpai/DAMOS 的反馈回路在数据中心以"PSI / 内存占用"为目标；终端要把**续航与闪存寿命**也并进目标（多压一页省了 RAM，却烧了 CPU、磨了闪存）。**"何时值得花一次扫描 + 一次压缩去腾一页"在能耗约束下仍无公开的可移植基线（待核实）**，与 [A16d 压缩 IP 边际建模](A16d-压缩IP边际建模.md) 是同一问题的两面。
- **扫描的能耗本身要被建模**：主动扫描越频繁，冷热视图越新，但 aging/采样自身耗电。终端理想是**按压力与能耗预算自适应调扫描频率**，而非固定节奏——目前是厂商各自调参。
- **谁来驱动尚无定论**：内核内（DAMON_RECLAIM 自调）还是用户态（Senpai 式 daemon）？终端上更可能是**一个感知前后台、感知 agent 生命周期的 userspace 策略** + 可编程内核钩子的组合——这正引向 [A16b 的 XVM/eBPF 可编程主动感知](A16b-XVM-eBPF的LRU主动感知优化.md)。
- **接口未定型**：per-node 主动回收、`lru_gen` 从 debugfs 转正、DAMOS 目标的标准化都还在动（[LKML 2024](https://lkml.iu.edu/hypermail/linux/kernel/2409.0/05920.html)）。
- **与"前后台"信号融合**：主动扫描不该抛弃前后台信息，而该把它**降级为众多特征之一**与真实访问统计融合——如何融合（agent 后台任务该给多大"保护期"）是开放问题。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| 回收触发 ← 主动节奏 | 把 [A04](../foundations/A04-回收总论.md) 的触发从被动水线扩成主动节奏 | [A04](../foundations/A04-回收总论.md) |
| 冷热刻度 ← MGLRU/DAMON | aging 代际 / 区域采样提供"扫描器" | **[A05](../foundations/A05-冷热识别的演进.md)、[A15b](A15b-DAMON与分层内存实践.md)** |
| 反馈信号 ← PSI | 主动回收的激进度以 PSI 为闭环反馈 | **[A08](../foundations/A08-压力与低内存终止.md)** |
| 作用域 ← memcg | `memory.reclaim`/配额按 cgroup 定向与自调 | [A07](../foundations/A07-cgroup-memcg.md) |
| 冷页去向 → 压缩/分层 | 主动腾出的冷页压进 zram 多级（软分层） | [A06](../foundations/A06-压缩与换页.md)、[A15c](A15c-移动端分层内存与内存压缩前沿.md) |
| 可编程化 → XVM/eBPF | 把"按什么策略主动扫"做成可下放的程序 | **[A16b](A16b-XVM-eBPF的LRU主动感知优化.md)** |

## 8. 实测 / 观测点

- `/sys/kernel/mm/lru_gen/min_ttl_ms`：MGLRU 抖动防护（**稳定**旋钮）；
- `/sys/kernel/debug/lru_gen`：读=工作集直方图，写=主动产代/主动回收（**实验性，需 userspace 驱动**）；
- `echo <bytes> > /<cgroup>/memory.reclaim`（可带 `swappiness=`）：对某 cgroup **主动**触发回收（cgroup v2，不代表有压力）；
- DAMON：`/sys/kernel/mm/damon/` 配置物理地址监控 + DAMOS `pageout`/`cold` 与配额目标自调；或用户态 [`damo`](https://github.com/awslabs/damo)；
- PSI：`/proc/pressure/memory`（some/full avg）——主动回收控制回路的反馈源（[A08](../foundations/A08-压力与低内存终止.md)）；
- 观察效果：`/proc/vmstat`（`pgscan_*`/`pgsteal_*` 看扫描/回收量）、`dumpsys meminfo` 看 SwapPss 变化（度量见 [A13](../foundations/A13-内存度量与排障.md)）。

## 9. 来源与延伸阅读

**MGLRU 的 aging 与主动回收接口**
- [Multi-Gen LRU (kernel.org)](https://docs.kernel.org/admin-guide/mm/multigen_lru.html) —— aging vs eviction；稳定旋钮 `min_ttl_ms`；`/sys/kernel/debug/lru_gen` 工作集估计/主动回收属实验、需 job scheduler 驱动
- [Merging the multi-generational LRU (LWN)](https://lwn.net/Articles/894859/)

**主动回收入口与控制回路**
- [memcg: introduce per-memcg proactive reclaim (LWN)](https://lwn.net/Articles/892328/) —— `memory.reclaim` 引入（2022）、"不代表有压力"
- [Control Group v2 · memory.reclaim (kernel.org)](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [Transparent memory offloading (Meta Engineering)](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) —— Senpai：以 PSI 为反馈、施加温和压力的用户态主动回收控制回路
- [per-node proactive reclaim interface (LKML, 2024)](https://lkml.iu.edu/hypermail/linux/kernel/2409.0/05920.html) —— 主动回收用户接口仍在讨论

**DAMON 主动回收与自调节**
- [DAMON-based Reclamation (kernel.org)](https://docs.kernel.org/admin-guide/mm/damon/reclaim.html) —— DAMON_RECLAIM 设计与 aim-oriented 配额自调节
- [Using DAMON for proactive reclaim (LWN)](https://lwn.net/Articles/863753/)
- [DAMON-Based Memory Reclamation Merged For Linux 5.16 (Phoronix)](https://www.phoronix.com/news/DAMON-Reclamation-Linux-5.16)
- [DAMOS auto-tuned for per-memcg per-node memory usage (LWN)](https://lwn.net/Articles/1026213/)

**承接 / 相邻篇**
- [A04 回收总论](../foundations/A04-回收总论.md)、[A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md)、[A08 压力与低内存终止](../foundations/A08-压力与低内存终止.md)、[A15b DAMON 与分层内存实践](A15b-DAMON与分层内存实践.md)、[A15c 移动端分层内存与内存压缩前沿](A15c-移动端分层内存与内存压缩前沿.md)、[A16b XVM·eBPF 的 LRU 主动感知](A16b-XVM-eBPF的LRU主动感知优化.md)、[A16d 压缩 IP 边际建模](A16d-压缩IP边际建模.md)

> **待核实 / 待补**：`memory.reclaim` 的 `swappiness` 参数与 per-node 主动回收接口的确切合入版本；`lru_gen` debugfs 接口是否/何时从实验转为稳定；DAMON_RECLAIM 与 DAMOS aim-oriented 自调节在 Android/GKI 的实际启用与机型覆盖（厂商定制）；各厂商 GKI 中"谁、按什么节奏驱动主动回收"的 userspace 策略基线（[A15c](A15c-移动端分层内存与内存压缩前沿.md) 同列待补）；HarmonyOS 是否有等价主动回收/主动扫描机制（[A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md) 留白）；iOS `vm_pageout` 扫描线程是否做"压力前预腾挪"式主动回收。

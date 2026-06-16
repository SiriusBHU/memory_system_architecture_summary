# A16d · 压缩 IP 边际建模（落盘量固定、算法固定下，压多少、压多狠）

> **一句话定位**：[A16c](A16c-异构压缩CDSD.md) 解决"用什么压"，本篇解决"**压多少、压多狠**"。设定很具体——**落盘量（writeback 预算）固定、压缩算法固定**——问题就收敛成一个控制题：**该把多大比例的内存保持在压缩态、以多快的速率去压，才能让压缩/解压的延迟落在目标内、不拖累整机吞吐？** 本篇把压缩路径当成一个有服务代价的"IP/服务"，给它建一套**边际成本–收益**的分析框架（**模型为推演/示意，非实测**），并指出它与 [A16a 主动回收自调](A16a-LRU主动扫描.md) 是同一类反馈控制。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「2B 物理与回收侧 · 换页」格——给"换出/压缩"这个动作配一个**代价感知的节流器**。
> 🧭 **阅读前置**：先读 [A06 压缩与换页](../foundations/A06-压缩与换页.md)（压缩=用 CPU 换内存的代价本质）、[A16c 异构压缩](A16c-异构压缩CDSD.md)（算法谱系，本篇假设算法已选定）、[A16a LRU 主动扫描](A16a-LRU主动扫描.md)（激进度自调的反馈控制范式，本篇复用）；吞吐/压力信号见 [A08 压力与低内存终止](../foundations/A08-压力与低内存终止.md)。
> 🌡️ **演进分级**：**演进厚 ⚡（含原创分析框架）**——现有内核只有粗旋钮（swappiness/writeback_limit），把"压多狠"做成代价模型尚无公开可移植基线；**重点在 §3 模型 与 §6 趋势**。**全篇凡公式均标"示意"，量级需实测标定。**

---

## 1. 定位：被忽略的那个旋钮——"压多狠"

[A06](../foundations/A06-压缩与换页.md) 讲清了压缩的代价本质：**压缩 = 用 CPU 周期换内存容量**。压一页省下内存，但花掉一次压缩的 CPU 时间；将来这页被再次访问（refault）时，还要在**关键路径上**付一次解压延迟。

现实里"压多狠"这个旋钮一直很粗：

- **`swappiness`**：一个 0–200 的全局/每 cgroup 倾向值，笼统地偏向"宁回收匿名页（压缩）还是文件页"；
- **`writeback_limit`**：给 zram 写回闪存设**字节预算上限**（[A15c §4](A15c-移动端分层内存与内存压缩前沿.md)），护闪存寿命；
- **`recompress` 的 `threshold`/`max_pages`**：限定一次重压缩的范围（[A16c](A16c-异构压缩CDSD.md)）。

这些都是**静态阈值或硬上限**，没有一个把"压缩激进度"直接挂到"**延迟/吞吐目标**"上。本篇要补的就是这块：**给定固定的落盘预算与固定算法，把"压缩量 + 压缩比例"作为决策变量，在延迟/吞吐约束下求一个边际最优。**

## 2. 负载动因：增长逼着多压，但终端的"压"有硬约束

本篇属于 A16「**增长**」轴。按 [A16 总论](A16-前沿-Agent时代内存负载.md) 的终端立场：增长（[A16c §2](A16c-异构压缩CDSD.md) 的双重增长）逼着系统把更多内存保持在压缩态——但终端的"压"被三条红线钳着，使"无脑多压"必然反噬：

1. **CPU/能耗预算**：压缩/解压自身耗电；多压一页省了 RAM，却烧了焦耳——续航是硬约束。
2. **关键路径延迟**：解压发生在 **refault 缺页路径**上，直接进用户可感知延迟。压得越多、越冷的页被压，refault 时的卡顿风险越大。
3. **多 IP 竞争**（A16 三特征里的「异构」在此现身）：压缩抢的 CPU 周期，正是前台交互与 NPU 推理要用的。终端不像数据中心有富余核去"顺手压一压"——**压缩的 CPU 预算本身是被争抢的**。

> 一句话动因：**增长要求多压，但终端的能耗、关键路径延迟、多 IP 竞争三条红线，要求"压多狠"必须被一个代价模型钳住——这就是压缩 IP 边际建模。**

## 3. 机制本体：把压缩路径建成"有代价的服务"

### 3.1 把压缩当成一个 IP / 服务队列

不论压缩跑在 CPU 软件路径还是专用硬件 IP 上，都可抽象成**一条有服务代价的队列**：

- **输入**：回收/主动扫描（[A16a](A16a-LRU主动扫描.md)）送来的候选页流；
- **服务代价**：单位页压缩延迟 `c_comp`、解压延迟 `c_decomp`（算法固定 ⇒ 近似常数，随数据类小幅波动，见 [A16c](A16c-异构压缩CDSD.md)）；
- **产出**：每页省下内存 `Δm ≈ page_size·(1 − 1/r)`，`r` 为压缩比（算法固定 ⇒ 由数据决定）；
- **延后代价**：解压不在压缩时付，而在该页 **refault** 时付，落在关键路径上。

zswap 的工程经验正是这条抽象的实证：它"**用 CPU 周期换更少的 swap I/O**，压缩/解压延迟显著贡献于换出/换入时间"，且"**解压在缺页时发生（decompress on fault）**"——代价的两段（压时 / refault 时）就此分离。

### 3.2 决策变量与约束（对应用户设定）

固定**落盘预算 `B`**（writeback_limit）与**算法**后，自由度只剩两个——正是要建模的对象：

- **压缩量 `R`**：单位时间压缩的页数（压缩队列的吞吐 / 激进度）；
- **压缩比例 `φ`**：把多大比例的工作集**保持在压缩态**（vs 留在未压快层）。

目标与约束（**示意**）：

```
max   有效容量增益  ≈  Σ_i Δm_i              （省下的内存越多越好）
s.t.  压缩占用 CPU  =  R · c_comp        ≤  CPU/能耗预算
      解压关键路径  p95( c_decomp on refault ) ≤  延迟目标 T
      写回闪存       Σ writeback           ≤  B（固定）
变量  R（压缩速率）, φ（压缩态比例）, 以及"压哪些页"的选择
```

### 3.3 边际判据：压到"边际收益 = 边际成本"为止 ← 核心

逐页看，**是否把第 i 页压（或保持压缩）**的边际判据（**示意**）：

```
  压它  ⇔  Δm_i · V(pressure)  ≥  c_comp  +  p_refault(i) · c_decomp
            └─ 边际收益 ─┘        └──────── 边际成本 ────────┘
```

- `V(pressure)`：**省一字节内存此刻值多少**——随当前内存压力（PSI，见 [A08](../foundations/A08-压力与低内存终止.md)）上升而上升。压力大时，省内存能避免一次 writeback（吃固定预算 `B`）甚至避免一次 lmkd 杀进程，故 `V` 高；压力小时 `V` 低，不值得为省内存付 CPU。
- `p_refault(i)`：**这页被再次访问的概率**——决定了"将来要不要付解压延迟"的期望。**这个量内核已经在测**：[A05](../foundations/A05-冷热识别的演进.md) 的 **refault / workingset** 机制（`mm/workingset.c`）正是用 refault 距离量化"刚回收的页多久又被要回来"。**边际模型不必凭空估 `p_refault`，可直接消费 workingset 的统计**——这是它落地的关键抓手。

**"边际"二字的含义**：随着 `R`、`φ` 增大，你会去压**可压性更差、或更可能 refault 的页**——于是**边际收益递减、边际成本递增**。两线相交处就是最优停止点；**越过它继续压 = 层间抖动的压缩版**（白烧 CPU/电换不到多少内存，还抬高 refault 延迟）。Alameldeen & Wood 的自适应 cache 压缩正是此思想的早期范本：**累积代价与收益，据此把压缩策略调得更激进或更保守**（[Adaptive Cache Compression, ISCA 2004](https://ieeexplore.ieee.org/document/1310776/)）。

### 3.4 它其实是一个带影子价格的准入控制

把上式重排：**压第 i 页 ⇔ 收益密度 `Δm_i / (c_comp + p_refault(i)·c_decomp)` ≥ 1/V(pressure)`**。

右边的 `1/V(pressure)` 是一个**影子价格（shadow price）λ**——按收益密度从高到低压页，压到预算耗尽时对应的那个密度就是 λ。这把"压多狠"变成一个**准入控制 / 背包问题**：

> **`swappiness` 其实就是今天那个粗糙的、静态的、全局的 λ。** 本篇主张把它换成**由 PSI / refault 率 / 吞吐反馈动态调出来的 λ**——这与 [A16a](A16a-LRU主动扫描.md) 里 DAMOS 的 **aim-oriented 配额自调**、Senpai 的 **PSI 闭环**是同一套控制范式，只是把被控量从"回收速率"换成"压缩激进度"。

### 3.5 落成控制器

实现上就是一个反馈回路：**测**（PSI、p95 refault 延迟、压缩 CPU 占用、writeback 余额）→ **比**（对目标 `T` 与预算）→ **调**（升/降 `R` 与 `φ`，即调 λ）。欠目标加压、超约束收手——和主动回收的自调节同构，可共用一套控制基础设施。

## 4. 历史：从静态阈值到预算化，再到反馈控制

```
swappiness（静态全局倾向，0–200）
   │  粗：只表达"偏好压匿名页 vs 丢文件页"，与延迟/吞吐目标无关
   ▼
writeback_limit（给闪存写回设字节预算上限）
   │  进步：第一次把"代价"显式预算化（护闪存寿命）——本篇 B 的来历
   ▼
recompress threshold / max_pages（限定一次重压范围）
   │  进步：把"压多少"局部参数化，但仍是手定阈值
   ▼
DAMOS aim-oriented 配额自调 / Senpai PSI 闭环（A16a）
   │  范式：把"激进度"变成反馈控制的被控量
   ▼
本篇主张：把"压缩激进度（R, φ）"也纳入同一类边际/反馈框架
   （消费 workingset 的 refault 统计估 p_refault）
```

学术脉络上，"自适应地决定压多少"早有先例：**Adaptive Main Memory Compression**（[Tuduce & Gross, USENIX ATC 2005](https://www.usenix.org/legacy/event/usenix05/tech/general/full_papers/tuduce/tuduce.pdf)）指出**静态固定压缩区大小对不同负载都不优**，须按运行时收益动态调整压缩区——这正是 `φ`（压缩态比例）该自适应的论据。本篇是把这条老思路放到**终端 + Agent 负载 + 固定落盘预算**的新约束下重述。

## 5. 现状与平台差异

| 维度 | Android（Linux / GKI） | iOS / Darwin（XNU） | HarmonyOS |
|---|---|---|---|
| "压多狠"如何定 | 厂商手调 `swappiness` + zram `disksize`/`writeback_limit` + recompress 阈值，**无公开边际模型，机型各异（黑魔法）** | XNU compressor 自有启发式（何时压、何时 swap），外部不可编程 | 待核实 |
| 代价反馈 | PSI 可用、workingset refault 可读，但**是否被用于闭环调压缩激进度未公开（待核实）** | 内建，不暴露 | 待核实 |
| 硬件卸载 | 移动端基本无（CPU 软件路径）；数据中心已有 Intel IAA 给 zswap 卸载压缩 | 无公开 | 待核实 |

> **术语警示**：这里的"边际建模"是**分析/控制框架**，不是某个已落地的内核模块；现状是**各厂商用静态参数近似**。把它说成"内核已有的功能"是误导。

## 6. 趋势与未解问题 ← 本篇重心

- **在线估 `p_refault` 与 `V(pressure)` 的精度**：模型好坏取决于这两个量估得准不准。workingset 给了 refault 数据，但把它**实时、低开销地折算成单页 refault 概率**仍是工程难题。
- **多目标、无统一目标函数**：终端要同时管内存、p95 延迟、能耗、闪存寿命——四者量纲不同、权重随场景漂移（前台游戏 vs 后台 agent 长任务），**没有放之四海的目标函数**；这与 [A16a §6](A16a-LRU主动扫描.md) 的"终端目标函数要改写"是同一道坎。
- **硬件压缩 IP 改写整个权衡**：一旦压缩下沉到专用 IP（近内存/存储侧），`c_comp` 趋近于零、且不再抢 CPU——边际判据右端塌掉，"几乎该把一切可压的都压上"。这把问题从"省 CPU"变成"省带宽/能耗"，载体见 [A16g PIM](A16g-DRAM-PIM异构协同管理.md) / [A16i UFS-HBF](A16i-端侧UFS-HBF增强.md)；数据中心的 [Intel IAA for zswap](https://cdrdv2-public.intel.com/846438/ZSWAPwithIAA_1.0.pdf) 是这条路的先声。
- **与 KV 有损压缩的联合预算**：KV 的量化/淘汰（[A16f](A16f-端侧KV-Cache管理方案.md)）也吃 CPU、也有"质量–容量"边际，与系统层无损压缩**共享同一块 CPU/能耗预算**却各自为政——如何做**联合的边际分配**（一焦耳电该花在多压一页匿名页，还是多量化一段 KV）是空白。
- **早停与不可压页**：对压不动的页应**早早放弃**（"early abort of compression"思路），把 CPU 让给值得压的页——这是边际判据在 `Δm_i≈0` 时的自然推论，但需要快速的可压性预判。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| 代价本质 ← 压缩 | "用 CPU 换内存"是边际成本的来源 | [A06](../foundations/A06-压缩与换页.md) |
| 算法谱系 ← 异构压缩 | 算法定了 `c_comp/c_decomp/r` 的量级 | **[A16c](A16c-异构压缩CDSD.md)** |
| 控制范式 ← 主动回收自调 | 共用 PSI/配额反馈，把被控量换成压缩激进度 | **[A16a](A16a-LRU主动扫描.md)** |
| refault 概率 ← workingset | `p_refault` 的现成数据源 | **[A05](../foundations/A05-冷热识别的演进.md)** |
| 压力信号 ← PSI | `V(pressure)` 与吞吐约束的反馈源 | **[A08](../foundations/A08-压力与低内存终止.md)** |
| 落盘预算 ← writeback_limit | 固定预算 `B` 的来历 | [A15c](A15c-移动端分层内存与内存压缩前沿.md) |
| 硬件卸载 → PIM/HBF | `c_comp→0` 改写权衡 | [A16g](A16g-DRAM-PIM异构协同管理.md)、[A16i](A16i-端侧UFS-HBF增强.md) |

## 8. 实测 / 观测点

- `/proc/pressure/memory`（PSI some/full）：`V(pressure)` 与吞吐退化的反馈源；
- `/proc/vmstat` 的 `workingset_refault*`、`pgmajfault`：估 `p_refault` 与解压关键路径压力；
- `cat /sys/block/zram0/mm_stat`：压缩比 `r`、`same_pages`，看实际省内存量 `Δm`；`bd_stat` 看 writeback 余额对 `B`；
- `cat /proc/sys/vm/swappiness`（或每 cgroup `memory.swappiness`）：今天那个"静态 λ"；
- 压缩 CPU 占用：`top`/`perf` 看 `zram`/压缩器线程的 CPU；
- 度量口径见 [A13](../foundations/A13-内存度量与排障.md)。

## 9. 来源与延伸阅读

**代价本质与"解压在缺页路径"**
- [zram (kernel.org)](https://docs.kernel.org/admin-guide/blockdev/zram.html) / [zswap (kernel.org)](https://www.kernel.org/doc/html/latest/admin-guide/mm/zswap.html) —— 压缩=用 CPU 换 I/O；`writeback_limit` 预算；decompress on fault
- [The zswap compressed swap cache (LWN)](https://lwn.net/Articles/537422/)

**自适应压缩 / 代价–收益模型（学术与体系结构先例）**
- [Adaptive Cache Compression for High-Performance Processors (ISCA 2004)](https://ieeexplore.ieee.org/document/1310776/) —— 累积代价与收益、据此调压缩激进度（边际预测器范本）
- [Adaptive Main Memory Compression (USENIX ATC 2005)](https://www.usenix.org/legacy/event/usenix05/tech/general/full_papers/tuduce/tuduce.pdf) —— 静态固定压缩区不优、须运行时自适应（`φ` 的论据）

**反馈控制范式与硬件卸载**
- [Transparent memory offloading (Meta)](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) —— Senpai 的 PSI 闭环（控制范式）
- [DAMON-based Reclamation (kernel.org)](https://docs.kernel.org/admin-guide/mm/damon/reclaim.html) —— aim-oriented 配额自调（同构控制器）
- [Enhancing Data Center Efficiency with zswap and Intel IAA (Intel)](https://cdrdv2-public.intel.com/846438/ZSWAPwithIAA_1.0.pdf) —— 压缩卸载到硬件 IP，`c_comp→0` 的先声
- refault/workingset 数据源：内核 `mm/workingset.c`（见 [A05](../foundations/A05-冷热识别的演进.md)）

**承接 / 相邻篇**
- [A06 压缩与换页](../foundations/A06-压缩与换页.md)、[A16a LRU 主动扫描](A16a-LRU主动扫描.md)、[A16c 异构压缩 CDSD](A16c-异构压缩CDSD.md)、[A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md)、[A08 压力与低内存终止](../foundations/A08-压力与低内存终止.md)

> **待核实 / 待补**：**本篇模型为分析推演，所有公式均"示意"**，`c_comp/c_decomp/r/p_refault` 的真实量级需在目标机型实测标定；各厂商 GKI 是否/如何用 PSI+workingset 闭环调压缩激进度（未公开）；移动端是否有压缩硬件卸载（现状基本无，待核实）；系统层无损压缩与 KV 有损压缩的联合 CPU/能耗预算分配机制（空白）；"early abort / 可压性预判"在 zram 路径的落地情况；HarmonyOS / iOS 的压缩激进度策略（不公开）。

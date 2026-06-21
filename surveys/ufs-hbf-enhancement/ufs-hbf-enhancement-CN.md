# 高带宽闪存在端侧：从「慢的 swap 后备」到「真正的内存层」

> 一份「演进前 vs 演进后」的对照调研，聚焦手机 UFS 闪存在内存层级里的角色。锚点文章：[A16i — 端侧 UFS-HBF 增强](../../advanced/A16i-端侧UFS-HBF增强.md)。原方案里 UFS 是「**非易失后备，离热路径远远的，闪存又慢、寿命又有限，碰它不划算**」。演进方案有两条路：（a）**UFS 5.0**（JEDEC 2025-10-06）把标准接口拉到 **约 10.8 GB/s**，M-PHY 6.0——已在路线图上；（b）**HBF（High Bandwidth Flash）**——SanDisk + SK 海力士 2025 提案，**256 GB/die、512 GB/stack、1.6 TB/s 读、按相同价位算容量是 HBM 的 8–16×**——这是数据中心的现实模板。HBF 的设计思路能不能下放到端侧 UFS，是开放探讨；**端侧产品不存在；数据中心版本样品 2H 2026 才出**。

## 1. 范围与方法

**调研对象。** 「端侧高带宽闪存」专指：把手机 UFS 当作 LLM 权重与 KV cache 的**内存后端**来用，以及能闭合"LPDDR-UFS 带宽差"的候选硬件演进。范围覆盖（a）**真实的近期路线图**（UFS 4.0 → 4.1 → 5.0）和（b）**思路下放的推测**（把 HBF 的堆叠模式搬到手机）。

**原方案。** 手机 UFS 4.0/4.1 是唯一的非易失层——顺序读 **约 4 GB/s**，4 KB 随机读 **0.45–1 GB/s**（PowerInfer-2 在 OnePlus 12 实测），队列深度 **32**。OS 把它当作"远的后备"；Android 默认不打开磁盘 swap 也是因为闪存寿命和带宽都说"少碰"。

**演进方案，两条赛道。** **(赛道 A——出货路线图)** UFS 5.0：M-PHY 6.0 HS-G6 单 lane **46.6 Gb/s**，2 lane 目标顺序读 **约 10.8 GB/s**，JEDEC 把 AI 负载明确列为驱动力。**(赛道 B——数据中心现实 / 端侧推测)** HBF：像 HBM 一样**堆叠 NAND**，TSV 走 interposer，**Gen-1 256 GB/die、16 高堆 512 GB/stack、读 1.6 TB/s**，Gen-2 >2 TB/s、Gen-3 3.2 TB/s；SanDisk + SK 海力士 MOU、OCP 标准化中；首批样品 **2H 2026**、首批推理设备 **2027 初**。端侧 UFS-HBF——把以上任何思路（更宽接口、更深队列、堆叠、pSLC 高耐久区、近存储计算）下放到手机量级——**没有产品**，仅为设计探讨。

**资料来源。** 13 条：KIOXIA UFS 4.0/4.1 产品页与 "Top 5 Reasons" 文档（带具体数字）、JEDEC 关于 UFS 4.1（2025-01）与 UFS 5.0（2025-10）的两份新闻、MNN-LLM（arXiv 2506.10443）和 PowerInfer-2（arXiv 2406.06282）的实测数字、KVSwap 论文（arXiv 2511.11907）、HiFC（NeurIPS 2025 poster）、SanDisk 自己的 HBF 公告、Tom's Hardware 两篇 HBF 专题、TrendForce 的 HBF 时间表、EE Times "NAND Reimagined"（Gen-1/2/3 路线图）、Samsung Semiconductor UFS 4.0 首发博客，以及 Wikipedia UFS 跨版本表。

## 2. 问题背景

**系统要干的事是什么。** 在一台 DRAM（约 12–24 GB LPDDR5X）比模型还小——长上下文下甚至比 KV cache 还小——的手机上跑端侧 LLM 推理。推理引擎按需从闪存流式读权重和 KV，同时还得让正常 app 栈活着。首 token 延迟、解码速率、电量代价都要顾。

**为什么这件事变难。** 三个约束撞到一起：（1）**DRAM-闪存带宽差巨大**——LPDDR5X ≈ 58 GB/s，UFS 4.0 ≈ 0.45–3 GB/s，差距 **19–130×**（[MNN-LLM, arXiv 2506.10443](https://arxiv.org/abs/2506.10443)）；（2）**闪存寿命预算钳住写频率**——KV offload 写到闪存要小心管理寿命，否则缩短整机寿命（[HiFC](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) 用 pSLC 区把写耐久提升 **约 8×**）；（3）**手机 UFS 队列浅**（约 32）——LLM 推理这种随机访问模式，IOPS 在带宽没打满时就已经卡住了。

**为什么原方案不够用了。** 装不进 DRAM 的端侧 LLM 没法以 LPDDR 量级的带宽从闪存流权重。PowerInfer-2 在 OnePlus 12（UFS 4.0）上跑 TurboSparse-Mixtral-47B 拿到 **11.68 tok/s**，闪存侧大约 **4 GB/s** 顺序读——这点速度来之不易，靠的是引擎用激活预测把闪存读藏在计算后面。下一步（更长上下文、更多 KV 走闪存、多模型常驻）要么靠带宽、要么换一种闪存拓扑。UFS 5.0 答前者，HBF 答后者。

## 3. 具体问题与瓶颈数据

### 具体问题

1. **DRAM-闪存带宽差。** 19–130×（按访问模式）——[MNN-LLM](https://arxiv.org/abs/2506.10443) 实测。
2. **UFS 内部的随机访问劣化。** OnePlus 12（UFS 4.0）顺序约 **4 GB/s**，4 KB 随机 **0.45–1 GB/s**——不利访问模式再丢 **4–10×**（[PowerInfer-2](https://arxiv.org/abs/2406.06282)）。
3. **队列深度限制并发。** UFS lane 的裸带宽不算窄，但队列浅（约 32）——多推理流并发随机读会相互卡。
4. **寿命预算。** 频繁 KV offload 写消耗的是承载整机的同一块闪存。HiFC 用 pSLC 区把写耐久乘上 **约 8×**，代价是有效容量下降。

### 瓶颈数据

| 信号 | 数值 | 含义 | 来源 |
|---|---|---|---|
| LPDDR5X 端侧带宽 | **约 58 GB/s** | 作为 DRAM 这一层的参考。 | [MNN-LLM](https://arxiv.org/abs/2506.10443) |
| UFS 4.0 顺序读（每 lane） | **约 2.9–4 GB/s** | 当前代能给的上限。 | [KIOXIA UFS 4.0/4.1](https://europe.kioxia.com/en-europe/business/memory/mlc-nand/ufs4.html); [Samsung UFS 4.0 公告](https://semiconductor.samsung.com/news-events/tech-blog/samsung-develops-first-ufs-4-0-storage-solution-compliant-with-new-industry-standard/) |
| UFS 4.0 4 KB 随机读 | **0.45–1 GB/s** | LLM 推理常打到的访问模式。 | [PowerInfer-2](https://arxiv.org/abs/2406.06282), OnePlus 12 实测 |
| DRAM vs UFS 带宽差 | **19–130×** | 跨访问模式；闪存还不能独立当内存后端的核心原因。 | [MNN-LLM](https://arxiv.org/abs/2506.10443) |
| UFS 队列深度 | **32** | 相对 PCIe NVMe 量级（64K+）很浅；钳住随机 IOPS 并发。 | A16i §3.1；通用引用 |
| PowerInfer-2 在 OnePlus 12 + UFS 4.0 上的解码速率（TurboSparse-Mixtral-47B） | **11.68 tok/s**；平均 cache miss **3.5%**，p99 **18.9%** | 当下纯软件的最佳现状，已经撞到带宽墙。 | [PowerInfer-2](https://arxiv.org/abs/2406.06282) |
| UFS 4.0 lane 接口 | **23.2 Gbps/lane**（46.4 Gbps/device） | 当前代的接口天花板。 | JEDEC；KIOXIA |
| UFS 5.0 目标（JEDEC 2025-10） | 顺序读最高 **10.8 GB/s**；M-PHY 6.0 HS-G6 单 lane **46.6 Gb/s**；明确把 AI 列为驱动 | 出货路线图的答卷——约 **2.7×** UFS 4.0 顺序天花板。 | [JEDEC UFS 5.0 新闻](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage) |
| HBF Gen-1（数据中心） | **256 GB/die、16 高堆 512 GB/stack、读 1.6 TB/s** | 数据中心对照：堆叠 NAND 比 UFS 4.0 顺序快 **>500×**。 | [EE Times "NAND Reimagined"](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/); [Tom's Hardware HBF](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers) |
| HBF 同价位下容量对 HBM | **8–16×** | 同价格下的容量倍数，不是降价。 | [Tom's Hardware HBF 容量](https://www.tomshardware.com/tech-industry/sandisk-and-sk-hynix-join-forces-to-standardize-high-bandwidth-flash-memory-a-nand-based-alternative-to-hbm-for-ai-gpus-move-could-enable-8-16x-higher-capacity-compared-to-dram) |
| HBF 首批样品 → 首批推理设备 | **2H 2026 → 2027 初** | 数据中心版的时间线。端侧没产品。 | [TrendForce](https://www.trendforce.com/news/2025/08/07/news-memory-giants-sandisk-sk-hynix-unite-for-hbf-standard-with-samples-expected-in-2h26/) |
| HiFC pSLC 写耐久倍数 | **约 8×** | 频繁 KV 写的寿命杠杆；容量代价。 | [HiFC NeurIPS 2025](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) |

**怎么看这张表。** 三个数字撑起论证。**58 GB/s vs 0.45–3 GB/s** 是瓶颈。**10.8 GB/s** 是 UFS 5.0 的答案——有意义，但还比 LPDDR 慢约 6×。**1.6 TB/s** 是 HBF 的答案——比 LPDDR 还快，但代价是手机现在装不下、供不起的数据中心包装。把 HBF 的**思路**（堆叠、更深队列、近存储计算、pSLC 高耐久区）做出端侧量级的版本能不能补上之间这段，是开放设计问题。

## 4. 架构图：原方案 vs 演进方案

两张图用同样的组件；不一样的地方用 `*` 标。

**原方案——UFS 4.x 作远后备**

```
   +---------+     约 58 GB/s        +-----------+
   |   SoC   | --------------------> |  LPDDR5X  |
   | (CPU/   |                       +-----------+
   |  NPU    |
   |  推理)  |
   +----+----+
        |
        | UFS 1-2 lane（顺序 4 GB/s、
        | 4K 随机 0.45-1 GB/s、
        | 队列深度 32）
        |
        v
   +-----------+
   | UFS 4.x   |   非易失、远，
   | NAND      |   有寿命预算
   +-----------+

   权重/KV 装不进 DRAM 时：
   读风暴从闪存拉，比 DRAM 慢
   19-130× → 卡住
```

*原方案：UFS 是唯一非易失层，被当作远后备。权重或 KV 装不进 DRAM 时，推理引擎被闪存读卡住；软件 workaround（激活预测）只能部分掩盖差距。*

**演进方案——UFS 5.0 已在路线图，HBF 思路下放属推测**

```
   +---------+     约 58 GB/s        +-----------+
   |   SoC   | --------------------> |  LPDDR5X  |
   +----+----+                       +-----------+
        |
        | * 赛道 A（路线图，JEDEC 2025-10）：
        |   UFS 5.0 -- M-PHY 6.0 HS-G6,
        |   每 lane 46.6 Gb/s x 2 = 最高 10.8 GB/s
        |   * 明确把 AI 列为驱动
        |   * 主机发起的 defrag
        v
   +-----------+
   | UFS 5.0   |   非易失、更近
   +-----------+
        |
        | * 赛道 B（数据中心现实 / 端侧推测）：
        |   HBF 式堆叠
        |   * 256 GB/die、512 GB/stack、1.6 TB/s（DC Gen-1）
        |   * 近存储计算
        |   * KV 写的 pSLC 区（耐久约 8×）
        |   * 端侧产品：无
        v
   +--------------+
   | UFS-HBF      |   * 堆叠 NAND
   | （提案，     |   * 近存储计算
   |  无产品）    |
   +--------------+
```

*演进方案：赛道 A（UFS 5.0）在 JEDEC 路线图上，把闪存拉到约 10.8 GB/s，与 LPDDR 的差距缩到约 6×。赛道 B（HBF）在 2026–2027 数据中心落地，展示堆叠 NAND 拓扑能做到什么；能不能往手机搬，是开放问题——没有产品存在。*

## 5. 演进方案解决了什么 / 没解决什么

### 解决了什么

- **DRAM-闪存带宽差** —— UFS 5.0 把差距从 19–130× 缩到顺序读约 6×。数据中心 HBF 直接反向（Gen-1 1.6 TB/s vs HBM4 量级）。对手机，就算只下放 HBF 一部分思路（更宽接口、更密堆叠），也足以让"从存储里跑模型"更现实。
- **随机访问劣化** —— UFS 5.0 的主机发起 defrag（[JEDEC UFS 4.1](https://www.jedec.org/news/pressreleases/jedec%C2%AE-announces-updates-universal-flash-storage-ufs-and-memory-interface)）和更深队列，会把更多随机访问转成顺序等价。软件侧 HiFC、KVSwap 已经在为 KV cache 做这件事；近存储计算（在闪存就地解压 / 筛选）让 SoC 发更大、更友好的请求。
- **队列深度** —— UFS 5.0 路线图明确把 AI 列为驱动，意味着更深的队列；数据中心 HBF 堆栈天生宽并行（TSV 连各 die、跨 bank 并发读）。
- **寿命预算** —— HiFC 的 pSLC 区把写耐久乘 **约 8×**（[HiFC NeurIPS 2025](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf)）。这是软件 / 固件杠杆，不在 UFS 规范里——但**对"KV offload 把闪存写坏"是目前最具体的写侧答案**。

### 没解决什么

- **HBF 今天不进手机。** HBM 量级的封装（TSV、interposer、HBM4 量级的堆高与封装尺寸）带来数据中心的功耗、成本与热密度。这些数字没有一个能干净地搬到手机上。锚点文章里的「端侧 UFS-HBF」是设计探讨，**没有任何厂商宣布过端侧产品**。
- **UFS 5.0 依然追不上 LPDDR。** 10.8 GB/s vs 约 58 GB/s 还差约 6×，而且这只是规范天花板，不是稳态随机读。
- **HBF 写慢。** Tom's Hardware 明确说 HBF 是**只做推理**的，因为写慢——这与 NAND 物理一致，也排除了 HBF 作为「内存频繁改写层」的可能。HBF 不让 KV 写消失；该用 pSLC 还是要用。
- **「同价位」不是「降价」。** HBF 同价位下容量是 HBM 的 8–16×——对容量瓶颈的数据中心推理有用，但每系统 $ 数和 HBM 一样。没有任何来源给出 $/GB 数字。
- **真实手机上 pinned-flash 占比尚无公开实测。** AOSP 文档讲了怎么测 UFS / dma-buf 计量，但没有公开数据集报告旗舰 Android 在真实端侧 LLM 负载下 UFS 带宽 / 闪存寿命被吃掉多少。
- **UFS 5.0 时间线。** JEDEC 2025-10-06 宣布标准；首批硅片与设备未点名。10.8 GB/s 视作路线图未来目标，不是今天可买到的。

## 6. 对比表

每个单元格都是数字、布尔，或 `n/a（原因）`；每行都有源。**多行诚实折衷**：HBF 写没改善；端侧 UFS-HBF 没产品。

| 维度 | 原方案：UFS 4.0/4.1 | 赛道 A：UFS 5.0 | 赛道 B：HBF（数据中心） | 改善 | 来源 |
|---|---|---|---|---|---|
| 顺序读带宽 | **约 4 GB/s** | **最高 10.8 GB/s** | **约 1.6 TB/s**（Gen-1） | A：**+2.7×**；B：**+400×** | [KIOXIA](https://europe.kioxia.com/en-europe/business/memory/mlc-nand/ufs4.html); [JEDEC UFS 5.0](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage); [Tom's Hardware](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers) |
| 单 lane 接口带宽 | **23.2 Gbps** | **46.6 Gbps**（HS-G6） | n/a（走 interposer / TSV，不靠 lane） | A：**+2×** | JEDEC UFS 4.1；JEDEC UFS 5.0 |
| 4 KB 随机读 | **0.45–1 GB/s** | 尚未公布；defrag + 更深队列利好 | n/a（单 die NAND 物理仍然适用） | A：方向性改善；B：n/a（顺序级） | [PowerInfer-2](https://arxiv.org/abs/2406.06282) |
| 单芯容量 | UFS 4.0 级约 512 GB QLC | 未公布 | **256 GB/die、16 高堆 512 GB/stack** | A：基本不变；B：每 die 约 **+1×**，每 package 约 **+16×** | [KIOXIA UFS 4.0/4.1 Top 5 Reasons]；[EE Times "NAND Reimagined"](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/) |
| 写耐久 | 基线（TLC/QLC NAND） | 基线 | 基线（HBF 明确写慢，只做推理） | 不变；HiFC pSLC 区 **约 8×**（容量代价） | [HiFC NeurIPS 2025](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) |
| LPDDR vs 闪存带宽差 | **19–130×**（UFS 4.0 vs LPDDR5X） | 顺序 **约 6×**（10.8 vs 58 GB/s） | **反向**（HBF >> HBM4 容量） | A：差距缩约 3–20×；B：仅数据中心 | [MNN-LLM](https://arxiv.org/abs/2506.10443); JEDEC UFS 5.0; [EE Times](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/) |
| 当前真机端侧 LLM 解码最佳值 | **11.68 tok/s**，TurboSparse-Mixtral-47B（OnePlus 12） | 尚未实测（无 UFS 5.0 手机） | n/a（数据中心） | A/B：待定 | [PowerInfer-2](https://arxiv.org/abs/2406.06282) |
| 标准发布 / 出货状态 | UFS 4.0（2022）、UFS 4.1（JESD220G, 2025-01） | UFS 5.0 宣布 **2025-10-06**；首批硅片待定 | HBF 样品 **2H 2026**；首批推理设备 **2027 初** | A：已宣布；B：数据中心时间线 | JEDEC 新闻；[TrendForce](https://www.trendforce.com/news/2025/08/07/news-memory-giants-sandisk-sk-hynix-unite-for-hbf-standard-with-samples-expected-in-2h26/) |
| 端侧 UFS-HBF 产品 | 是（经典 UFS） | 否（UFS 5.0 手机待定） | **端侧无产品** | **0**（端侧版本不存在） | A16i §5 |

## 7. 一词概括

**High-bandwidth**（高带宽） —— 演进方案的根本变化是：闪存带宽从 UFS 4.0 的 **约 2.9–4 GB/s** 天花板，沿着 UFS 5.0（JEDEC 2025-10-06）路线图朝着 **约 10.8 GB/s** 走，数据中心 HBF Gen-1 直接拉到 **约 1.6 TB/s**（[Tom's Hardware](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers)），让闪存有机会从「远后备」变成「真正的内存层」承载端侧 LLM 权重与 KV cache。手机上的 LPDDR-闪存差距随 UFS 5.0 从 **19–130×** 缩到约 **6×**；诚实的回归是 **HBF 写仍慢**（架构上就是只做推理）、**端侧 UFS-HBF 没产品**——数据中心 HBF 样品也要等到 **2H 2026**。

## 8. 开放问题与说明

- **端侧 UFS-HBF 是推测。** 没有任何厂商宣布过手机量级的 HBF 或 HBF 启发的 UFS。锚点文章 §3.4 「下放思路」是设计探讨、不是路线图。
- **HBF $/GB 没公布。** 所有来源都说 "comparable cost" / "similar price"，没人给 $/GB。8–16× 容量倍数是**同价位下的**，不是降价。
- **HBF 写速度与耐久没公布。** Tom's Hardware 说写慢（所以只面向推理）；Gen-1 没公布数值写带宽或 P/E 次数。
- **UFS 5.0 硅片与设备未点名。** JEDEC 2025-10-06 宣布标准；10.8 GB/s 是规范目标，不是今天可量产品。"UFS 5.0 能让我们拿到 X" 的锚点定到 JEDEC 新闻，不要定到出货产品。
- **UFS 队列深度 = 32 是广泛引用值，但本次手头可达的公开来源没直接核到规范文本上**。视为合理的标准实践上限，待 JEDEC 文本复核。
- **真实 Android 手机上的 pinned-flash 与带宽占比没实测。** AOSP 与 Perfetto 给了测量流程（`iostat`、`/sys/block/sd*/queue/`、UFS 健康描述符）；没有公开数据集报告在真实端侧 LLM 负载下的占比。在公司内部做一次实测是对这套瓶颈论证最有力的证据。
- **HBF 的堆叠优势在手机热包络下未必成立。** TSV interposer 和 HBM 量级堆叠适合数据中心包装；放进手机受板厚、散热、电池竞争限制。上面的所有带宽数字都不能机械迁移。

## 9. 参考资料

1. KIOXIA Europe. (2024–2025). *UFS 4.0/4.1 — Designed for Next Generation Mobile Storage*. [europe.kioxia.com/.../ufs4.html](https://europe.kioxia.com/en-europe/business/memory/mlc-nand/ufs4.html) —— **23.2 Gbps/lane**、**46.4 Gbps/device**。
2. KIOXIA Americas. (2024). *Top 5 Reasons to Move to UFS 4.0 / 4.1 Embedded Flash Memory from UFS 3.1* (PDF). [americas.kioxia.com/.../KIOXIA_Move_to_UFS4_4-1_Top_5_Reasons.pdf](https://americas.kioxia.com/content/dam/kioxia/en-us/business/memory/mlc-nand/asset/KIOXIA_Move_to_UFS4_4-1_Top_5_Reasons.pdf) —— 512 GB QLC UFS 4.0 顺序读 **约 4,200 MB/s**、写 **约 3,200 MB/s**。
3. JEDEC. (2025-01-08). *JEDEC Announces Updates to Universal Flash Storage (UFS) and Memory Interface Standards (UFS 4.1)*. [jedec.org/.../jedec-announces-updates-universal-flash-storage-...](https://www.jedec.org/news/pressreleases/jedec%C2%AE-announces-updates-universal-flash-storage-ufs-and-memory-interface) —— UFS 4.1 = JESD220G；M-PHY v5.0 + UniPro v2.0；主机发起 defrag。
4. JEDEC. (2025-10-06). *UFS 5.0 Is Coming: JEDEC Sets the Stage for the Next Leap in Flash Storage*. [jedec.org/.../ufs-50-coming-jedec-sets-stage-next-leap-flash-storage](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage) —— 目标 **最高 10.8 GB/s**；M-PHY 6.0 HS-G6 单 lane **46.6 Gb/s × 2 lane**；AI 列为驱动。
5. Wang 等（Alibaba）。(2025). *MNN-LLM: A Generic Inference Engine for Fast Large Language Model Deployment on Mobile Devices*. arXiv:2506.10443. [arxiv.org/abs/2506.10443](https://arxiv.org/abs/2506.10443) —— LPDDR5X **约 58 GB/s** vs UFS 4.0 **约 0.45–3 GB/s** → **19–130×** 差距。
6. Xue, Z.、Song, T. 等（SJTU IPADS）。(2024). *PowerInfer-2: Fast Large Language Model Inference on a Smartphone*. arXiv:2406.06282. [arxiv.org/abs/2406.06282](https://arxiv.org/abs/2406.06282) —— OnePlus 12 UFS 4.0 顺序 **约 4 GB/s**、4 KB 随机 **0.45–1 GB/s**；TurboSparse-Mixtral-47B 上 **11.68 tok/s**；平均 / p99 cache miss **3.5% / 18.9%**。
7. *KVSwap: Disk-aware KV Cache Offloading for Long-Context On-device Inference*. (2025). arXiv:2511.11907. [arxiv.org/pdf/2511.11907](https://arxiv.org/pdf/2511.11907) —— 面向受限端侧的 disk-based KV offload 框架。
8. *HiFC: High-efficiency Flash-based KV Cache Swapping for Scaling LLM Inference*. (NeurIPS 2025 poster). [openreview.net/pdf?id=onhjdWCxZY](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) —— DRAM-free 架构、pSLC + GPU Direct Storage；TPS 与 DRAM 可比；写耐久 **约 8×**；3 年 TCO 削 **4.5×**。
9. SanDisk newsroom. (2025-08-06). *Sandisk to Collaborate with SK hynix to Drive Standardization of High-Bandwidth Flash Memory*. [sandisk.com/.../2025-08-06-sandisk-to-collaborate-with-sk-hynix-...](https://www.sandisk.com/company/newsroom/press-releases/2025/2025-08-06-sandisk-to-collaborate-with-sk-hynix-to-drive-standardization-of-high-bandwidth-flash-memory-technology) —— MOU；HBF 拿 FMS 2025 "Best of Show, Most Innovative Technology"。
10. Shilov, A.（Tom's Hardware）。(2025). *SK hynix and SanDisk announce new High Bandwidth Flash — speedy HBF standard targeted at inference AI servers*. [tomshardware.com/.../sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-...](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers) —— 写慢，所以只做推理；匹配 HBM4 封装尺寸 / 功耗 / 堆高。
11. Tom's Hardware. (2025). *Sandisk and SK hynix join forces to standardize HBF — 8-16× higher capacity vs DRAM*. [tomshardware.com/.../sandisk-and-sk-hynix-join-forces-...-8-16x-higher-capacity-...](https://www.tomshardware.com/tech-industry/sandisk-and-sk-hynix-join-forces-to-standardize-high-bandwidth-flash-memory-a-nand-based-alternative-to-hbm-for-ai-gpus-move-could-enable-8-16x-higher-capacity-compared-to-dram) —— 同价位下容量是 HBM 的 **8–16×**。
12. TrendForce. (2025-08-07). *Memory Giants SanDisk, SK hynix Unite for HBF Standard, with Samples Expected in 2H26*. [trendforce.com/.../memory-giants-sandisk-sk-hynix-...-samples-expected-in-2h26/](https://www.trendforce.com/news/2025/08/07/news-memory-giants-sandisk-sk-hynix-unite-for-hbf-standard-with-samples-expected-in-2h26/) —— 首批样品 **2H 2026**；首批推理设备 **2027 初**。
13. EE Times. (2025). *NAND Reimagined in High-Bandwidth Flash to Complement HBM*. [eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/) —— Gen-1 **256 GB/die、16 高堆 512 GB/stack、读 1.6 TB/s**；Gen-2 **>2 TB/s**、Gen-3 **3.2 TB/s**；stack 容量 **1 TB / 1.5 TB**。
14. Samsung Semiconductor. (2022). *Samsung Develops First UFS 4.0 Storage Solution*. [semiconductor.samsung.com/.../samsung-develops-first-ufs-4-0-...](https://semiconductor.samsung.com/news-events/tech-blog/samsung-develops-first-ufs-4-0-storage-solution-compliant-with-new-industry-standard/) —— UFS 4.0 读 **约 4,200 MB/s**、写 **约 2,800 MB/s**；能效比 UFS 3.1 改善 **约 46%**。
15. 本项目 A16i 锚点。[advanced/A16i-端侧UFS-HBF增强.md](../../advanced/A16i-端侧UFS-HBF增强.md).

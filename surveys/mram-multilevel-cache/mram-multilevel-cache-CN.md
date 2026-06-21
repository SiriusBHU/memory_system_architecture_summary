# 用 STT/SOT-MRAM 做非易失多级缓存：从「全 SRAM 缓存」到「SRAM + MRAM 混合层级」

> 一份「演进前 vs 演进后」的对照调研，聚焦**非易失能不能进缓存层**这件事。锚点文章：[A16h — STT/SOT-MRAM 多级缓存方案](../../advanced/A16h-STT-SOT-MRAM多级缓存方案.md)。原层级里从 SRAM 一路到 DRAM 都是**易失**的——SRAM 漏电、DRAM 还得刷新。演进方案在 SRAM 缓存与 DRAM 之间插一层 MRAM：**非易失、无静态漏电、比 SRAM 更密**。STT-MRAM 已经出货——做 eFlash 替代（TSMC 22 nm、Samsung 14 nm、GlobalFoundries 22FDX）；SOT-MRAM 在 imec IEDM 2023 上拿到 **>10¹⁵ 耐久、<100 fJ/bit 切换能耗、300 ps 切换**。手机 SoC 用 MRAM 做 LLC / 端侧 AI 权重存——**没出货**，是设计探讨，挂在「混合层级把空闲能耗砍约 80%」这条**方向性**（未独立复现）的系统级论证上。

## 1. 范围与方法

**调研对象。** 这里说的「MRAM 多级缓存」专指：在易失的 SRAM 缓存与 DRAM 之间，**插一层非易失、低漏电的 MRAM**——比如做 LLC，或做端侧 AI 权重的常驻缓冲。**不是**用它替 L1/L2 的 SRAM（MRAM 太慢、cell 太大），**也不是**替闪存（MRAM 太小、太贵）。

**原方案。** 全 SRAM 缓存层级：L1/L2/L3 全 SRAM（易失、先进节点静态漏电越来越大、N3/N5 时 cell 就停止缩放）；DRAM 在下（易失、持续 refresh）。闪存以上的一切，掉电就丢。

**演进方案。** 混合层级：L1/L2 留 SRAM 求速度；MRAM（STT 或 SOT）插在 LLC，或做权重常驻缓冲。**非易失**（掉电不丢）、**无静态漏电**（闲时零功耗）、**比 SRAM 密**、延迟在 SRAM 与 DRAM 之间。**eFlash 替代已经出货**在 MCU/IoT/汽车上；手机 SoC 的 LLC / 权重存还是研究目标。

**资料来源。** 12 条：TSMC 研究页（22 nm 和 16 nm STT-MRAM）、ISSCC 2023 的 TSMC 16 nm 32 Mb eMRAM 论文、ITRI + TSMC IEDM 2023 SOT-MRAM、imec IEDM 2023 缩放 SOT-MRAM、GlobalFoundries 22FDX eMRAM 量产新闻、Samsung 14 nm eMRAM 规格、PMC 2024 行业综述、EDN 2024 SOT-MRAM 现状、Promwad 混合层级博客（空闲能耗数据，标注为方向性）、Memphis/Wevolver 端侧 AI 内存页、SOT 路线图论文（arXiv 2104.11459），以及 SemiWiki/IEDM 2022 关于"SRAM 停止缩放"的讨论。下表每个数字 §9 都有源。

## 2. 问题背景

**系统要干的事是什么。** 让 CPU/NPU 缓存够近、够快、够密——在手机上还要能装下数 MB 的 AI 权重切片——并且**别在闲着的时候白烧电**。

**为什么这件事变难。** 三个约束撞到一起：（1）**SRAM bit-cell 已经停止缩放**——TSMC N3B/N3E 的 SRAM bit-cell 相对 N5 几乎不缩（IEDM 2022），LLC 每 mm² 的容量被卡死；（2）**DRAM refresh 能耗不小**——32 Gb 量级 DRAM 的 refresh 占 DRAM 能耗 >20%，而内存层级整体占系统能耗约 40–50%，所以光 refresh 一项就占系统总能耗 **约 8–10%**；（3）**缓存内容掉电即失**——每次深度睡眠醒来，AI 权重与代码页都得从闪存重载，时间与能耗都不便宜。

**为什么原方案不够用了。** 两层压力：Agent 时代端侧 LLM 想让更大的工作集**常驻**（权重 + KV）；同一类负载又想让设备从冷启动唤醒**毫秒级**就绪。SRAM 缓存是今天唯一快的那层，但它**卡在缩放**、还 7×24 烧静态漏电。DRAM 更密，但 refresh 一直在烧。**它们之间没有一层既非易失又低漏电的**。MRAM 是今天唯一填得上这一格的候选。

## 3. 具体问题与瓶颈数据

### 具体问题

1. **先进节点上 SRAM 漏电不小。** 静态漏电在 SoC 闲时能耗里份额越来越大——cache 干没干活都得交。
2. **SRAM bit-cell 停止缩放。** N3B/N3E 上 SRAM bit-cell 相对 N5 几乎不缩（IEDM 2022）——LLC 多加一点容量都更贵。
3. **DRAM refresh 是常驻负担。** 系统闲着 DRAM 也得刷；高密度件上 refresh 占 DRAM 能耗 1/5 以上。
4. **缓存内容掉电即失。** 每次冷启动重新从闪存载入 AI 权重与代码——唤醒延迟和能耗都看得见。

### 瓶颈数据

| 信号 | 数值 | 含义 | 来源 |
|---|---|---|---|
| SRAM bit-cell N5 → N3B/N3E 缩放（TSMC） | **约 0%** | 用了几十年的"加容量"杠杆没了。 | IEDM 2022（"Did We Just Witness The Death Of SRAM?"）；SemiWiki |
| 5 nm 节点 STT-MRAM cell 对 6T SRAM 面积 | **43.3%** SRAM 宏面积 | 同节点 MRAM 在宏层密度是 SRAM 的 2× 以上，LLC 又能加容量了。 | PMC 2024 综述 |
| DRAM refresh 占 DRAM 能耗（32 Gb 量级） | **>20%** | refresh 自己就占 DRAM 能耗的 1/5 以上，其中相当一部分是闲时烧的。 | PMC 2024；行业来源印证 |
| DRAM refresh 占总系统能耗（估算） | **约 8–10%** | 一条可量化的杠杆；"非易失 + 不需 refresh"撬的就是这块。 | 同上推算 |
| 端侧 AI 用 MRAM 的尺寸点 | **4–16 MB**、**100–200 MHz**、**< 30 ns**、**> 10¹² 次**、**85 °C 下 20+ 年** | 与端侧 AI 权重缓冲的用例对得上。 | [Memphis / Wevolver](https://www.wevolver.com/article/three-edge-ai-architectures-that-demand-smarter-memoryand-why) |
| imec 缩放 SOT-MRAM（IEDM Dec 2023） | **<100 fJ/bit**、**>10¹⁵ 次**、切换 **300 ps**、能耗 **−63%** | 缓存级器件规格已经在 LLC 量级附近。 | [imec 文章](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| 混合 SRAM/MRAM/ReRAM 空闲能耗削减（厂方声明） | **约 80%** | 厂方博客的方向性声明，与 refresh + 漏电份额定性一致，但没独立复现。 | [Promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) —— 方向性 |

**怎么看这张表。** 前两行是瓶颈本身：SRAM 不缩放、MRAM 是除 DRAM 外密度最好的候选。中间两行说能耗杠杆是实的（DRAM refresh **约 8–10%** 系统总能耗可达）。最后两行说**器件**已经接近 LLC 量级，可以认真讨论了。

## 4. 架构图：原方案 vs 演进方案

两张图用同样的层级；不一样的地方用 `*` 标。

**原方案——全 SRAM 缓存 + DRAM refresh**

```
   +---------+
   |   CPU   |
   +----+----+
        |
        v
   +---------+   易失、漏电
   |  L1 SRAM|
   +----+----+
        |
        v
   +---------+   易失、漏电
   |  L2 SRAM|
   +----+----+
        |
        v
   +---------+   易失、漏电；
   | L3 SRAM |   N3 起停止缩放
   |  / LLC  |
   +----+----+
        |
        | 总线（refresh 耗电）
        v
   +---------+   易失、需 refresh
   |  DRAM   |
   +----+----+
        |
        v
   +---------+   非易失、慢
   | NAND    |
   +---------+
```

*原方案：每一层缓存都是 SRAM——易失、7×24 烧静态漏电、N3 起停止缩放。DRAM 烧 refresh。闪存以上一切掉电即失；每次醒来都冷启动。*

**演进方案——SRAM + MRAM 混合层级**

```
   +---------+
   |   CPU   |
   +----+----+
        |
        v
   +---------+   易失、漏电（留它求速度）
   |  L1 SRAM|
   +----+----+
        |
        v
   +---------+   易失、漏电（留它求速度）
   |  L2 SRAM|
   +----+----+
        |
        | * 切换层（换 cell 工艺）
        v
   +-------------+   * 非易失（instant-on）
   | LLC 或      |   * 零静态漏电
   | 权重常驻层: |   * STT-MRAM 读 6-7.5 ns /
   | MRAM        |     写 20 ns、10^6-10^12 次
   | (STT 或 SOT)|   * SOT-MRAM (imec) <100 fJ/bit、
   |             |     >10^15 次、300 ps 切换
   +------+------+   * 5 nm 节点 cell 约 SRAM 面积 43%
          |          * AI 权重跨电源周期常驻
          v
   +---------+   易失、需 refresh
   |  DRAM   |
   +----+----+
        |
        v
   +---------+   非易失、慢
   | NAND    |
   +---------+
```

*演进方案：L1/L2 SRAM 求速度不动；LLC（或权重常驻层）插一层 MRAM。数据和权重掉电不丢、闲时零静态漏电、同节点 cell 比 SRAM 密——LLC 又能"加容量"了。*

## 5. 演进方案解决了什么 / 没解决什么

### 解决了什么

- **「先进节点 SRAM 漏电」** —— MRAM 的静态漏电近似为零（闲时无电流路径）；混合层级把 SRAM 留在最需要速度的地方，其余替成 MRAM。Promwad 博客声明混合层级（叠加去掉 DRAM refresh）能把**空闲能耗削约 80%**（[Promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram)） —— 方向性，未实测。
- **「SRAM bit-cell 停止缩放」** —— 5 nm 节点 STT-MRAM cell 约 **SRAM 宏面积的 43.3%**（[PMC 2024 综述](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/)）。同样面积下 LLC 容量大约 2×，缓存层重新开始缩放。
- **「DRAM refresh 是常驻负担」** —— 非易失缓存层能把 AI 权重直接驻住，闲时不必由 DRAM 中介；该部分 refresh 能耗就省了。
- **「缓存内容掉电即失」** —— MRAM 天生非易失。AI 权重与持久缓冲跨深度睡眠仍在。这就是 instant-on 的本质，是用户最能直接感觉到的好处。

### 没解决什么

- **MRAM 写比 SRAM/DRAM 慢、也更费电。** TSMC 16 nm STT-MRAM 写 **20 ns**（[PMC 综述](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/)），SRAM 是 ns 量级；而且写电流大。**写密集型场景**（比如频繁更新模型激活）并不适合放进 MRAM。
- **STT 耐久有限。** TSMC 16 nm eFlash 级是 **10⁶ 次**（ISSCC 2023, 32 Mb）；缓存级目标到 **10¹²**（PMC 综述），仍然有限。SOT 实验室能上 **>10¹⁵**（imec），但还没量产。
- **SOT-MRAM 产品化没完成。** 路线图论文（[arXiv 2104.11459](https://arxiv.org/abs/2104.11459)）和 2024 EDN 现状都点名 **field-free SOT 切换的量产化**是器件物理上的卡点。imec 在实验室拿到 300 ps 切换，量产没到。
- **手机 SoC 上的 LLC / 权重存没出货。** **eMRAM 替 eFlash 已经出货**（Samsung 28 nm FD-SOI 自 2019、GF 22FDX 自 2020、TSMC 22 nm 与 16 nm）；MRAM 做手机消费 SoC 的 LLC 没出货。系统级"约 80%"是厂方博客的方向性声明，**没有独立复现**。
- **「持久」本身带来新责任。** 非易失缓存意味着**掉电后数据仍在**——安全擦除、写顺序语义（「持久缓存」需要持久内存那套 ordering）、侧信道暴露，都成了 SRAM 层级原来没有的新问题。

## 6. 对比表

每个单元格都是数字、布尔，或 `n/a（原因）`；每行都有源。**多行诚实折衷**：MRAM 写延迟、有限耐久、以及"在手机 LLC 量级上没出货"。

| 维度 | 原方案：SRAM 缓存 + DRAM | 演进方案：SRAM + MRAM 混合（STT/SOT） | 改善 | 来源 |
|---|---|---|---|---|
| 缓存级读延迟 | 约 1–3 ns（SRAM L1/L2/L3） | STT-MRAM **6–7.5 ns**；嵌入式端侧 AI 宏 **< 30 ns** | **约 3–10× 慢**（读侧回归） | TSMC 16 nm STT-MRAM, [PMC 综述](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/); [Wevolver](https://www.wevolver.com/article/three-edge-ai-architectures-that-demand-smarter-memoryand-why) |
| 缓存级写延迟 | 约 1–3 ns（SRAM） | STT-MRAM **20 ns**；SOT-MRAM 实验室 **300 ps**（imec） | 混合：STT 回归约 10×；SOT 长期占优 | PMC 综述；[imec](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| 耐久（写次数） | 无上限（SRAM） | STT-MRAM **10⁶–10¹²**（eFlash 级 vs 缓存级）；SOT-MRAM 实验室 **>10¹⁵** | 有限；相对 SRAM **−** | [PMC 综述](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/); [imec](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| 5 nm 节点 bit-cell 对 SRAM 面积 | 基线（6T SRAM，N3 起停止缩放） | **43.3%** SRAM 宏面积（STT-MRAM） | **−57%** 面积（更密 → 同 mm² 更大容量） | PMC 综述 |
| 待机静态漏电 | 非零，先进节点上升 | **0** | 定性：消除 | imec、TSMC 研究 |
| 掉电后保持 | **0**（易失） | TSMC 22 nm **>10 年 @150 °C**；TSMC 16 nm 缓存级 **1 分钟 @125 °C** | 定性：持久 | TSMC 22 nm；PMC 综述 |
| 缓存级切换能耗 | n/a（SRAM 翻一位 ~fJ 但常驻漏电） | SOT-MRAM **<100 fJ/bit**，比常规 MRAM **−63%** | 相对常规 MRAM **−63%**；对比 SRAM 翻位本身大致同数量级 | [imec](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| 与其它 NVM 的耐久对比 | SRAM 无限、DRAM 无限 | MRAM **~10¹⁵** vs ReRAM **10⁶–10⁹** vs NOR Flash **~10⁴** | MRAM 是唯一缓存级 NVM | [Promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) |
| 混合层级空闲能耗削减 | 基线 | 声明 **~80%**（去 DRAM refresh + SRAM 漏电） | **−80%** —— 方向性、未实测 | [Promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) |
| eMRAM 替 eFlash | n/a（不是同一市场） | **已出货**（TSMC 22/16 nm、Samsung 28 nm FD-SOI 自 2019、GF 22FDX 自 2020） | 新能力，**MCU/IoT/汽车 上出货** | TSMC、Samsung、GF 公告 |
| 手机消费 SoC LLC / 权重存用 MRAM | 出货（仅 SRAM） | **未出货**（仅研究） | **0**（部署回归） | A16h §5；EDN 2024 |

## 7. 一词概括

**Non-volatile**（非易失） —— 演进方案的根本变化是：在 SRAM 与 DRAM 之间插的 MRAM 层**断电不丢、闲时零漏电**，AI 权重等持久缓冲可跨深度睡眠常驻，缓存层因此重新开始缩放（5 nm 节点 MRAM cell **约 SRAM 面积 43.3%**），混合层级朝着 **约 80%** 空闲能耗削减的方向走（Promwad，方向性）——代价是 STT 形态下写比 SRAM **慢约 10×**、耐久有限（STT-MRAM **10⁶–10¹²**，imec 实验室 SOT-MRAM **>10¹⁵**）。**eFlash 替代已出货**（Samsung 28 nm FD-SOI 自 2019、GF 22FDX 自 2020、TSMC 22 nm 与 16 nm）；手机 SoC LLC / 端侧 AI 权重存**没出货**。

## 8. 开放问题与说明

- **80% 空闲能耗削减是厂方博客的方向性声明。** Promwad 没给测量链。底层杠杆（DRAM refresh ~8–10% 系统能耗 + SRAM 漏电在先进节点上升）是真的；80% 这个总数**没独立复现**。
- **TSMC 16 nm STT-MRAM 有两个不同的宏。** eFlash 替代版（ISSCC 2023，32 Mb）是 **10⁶ 次、20 年 @150 °C、读 6 ns**；缓存级目标是 **10¹² 次、1 分钟 @125 °C、读 7.5 ns / 写 20 ns**。锚点 A16h 引的是缓存级数字；两组都对，但**是不同器件**。引用要分清。
- **TSMC 研究页本次没拉下来。** 上面那些数字是通过 PMC 2024 综述、ResearchGate 上的 ISSCC 2023 论文、EDN 2024 SOT-MRAM 现状文章交叉印证的。下次能访问 TSMC 自己页面时建议复核。
- **field-free SOT 切换的产品化仍是开放问题。** 路线图论文（[arXiv 2104.11459](https://arxiv.org/abs/2104.11459)）和 2024 EDN 现状都点名这是器件物理上的卡点。imec 的 300 ps 是实验室。
- **没有任何手机消费 SoC LLC 用 MRAM。** "手机上 MRAM 做 LLC" 这套叙事都是**面向未来的设计探讨**，不是出货现实。
- **持久缓存带来新的系统级问题。** 掉电后残留数据（安全）、写顺序语义（持久内存那套 flush/fence）、侧信道暴露——SRAM 层级没有的问题，非易失层一进缓存就要面对。

## 9. 参考资料

1. *Progress of emerging non-volatile memory technologies in industry*. (2024). MRS Communications / PMC. [pmc.ncbi.nlm.nih.gov/articles/PMC11618178/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/) —— 各厂 STT-MRAM 规格表（TSMC 22 nm / 16 nm、Samsung 14 nm、GF 22 nm）。
2. TSMC. (2023). *33.1 A 16 nm 32 Mb Embedded STT-MRAM*（ISSCC 2023，eFlash 替代）. [researchgate.net/publication/369497100](https://www.researchgate.net/publication/369497100) —— **读 6 ns**、**10⁶ 次**、**20 年 @150 °C**。
3. TSMC Research. (2022). *22 nm STT-MRAM for Reflow and Automotive Uses*. [research.tsmc.com/page/mram/1.html](https://research.tsmc.com/page/mram/1.html) —— **6 次回流后 >10 年 @150 °C**、**>1100 Oe @25 °C 磁免疫**。
4. TSMC Research. (2023). *High RA Dual-MTJ SOT-MRAM devices for High Speed (10 ns) Compute-in-Memory Applications*. [research.tsmc.com/page/mram/5.html](https://research.tsmc.com/page/mram/5.html) —— SOT-MRAM 单元 **10 ns**，面向 CIM。
5. MRAM-Info. (2024). *ITRI and TSMC announce advances in SOT-MRAM development*. [mram-info.com/itri-and-tsmc-announce-advances-sot-mram-development](https://www.mram-info.com/itri-and-tsmc-announce-advances-sot-mram-development) —— SOT-MRAM **写 10 ns**、功耗 **STT 的 1%**，IEDM 2023。
6. Ahmad, M. (2024). *Memory lane: Where SOT-MRAM technology stands in 2024*. EDN. [edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/](https://www.edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/) —— imec **<100 fJ/bit**、**>10¹⁵** 耐久、能耗 **−63%**；SOT 比 STT 快约 4×；面向 LLC。
7. imec. (2024-12-16). *Bringing SOT-MRAM technology closer to last-level cache memory specifications*. [imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) —— 缩放 SOT-MRAM **<100 fJ/bit**、**>10¹⁵ 次**、切换 **300 ps**、写错率 **10⁻⁶**、400 °C 工艺兼容。
8. Shao, Q., Li, P., Lake, R. 等。(2021/2023). *Roadmap of spin-orbit torques*. arXiv:2104.11459. [arxiv.org/abs/2104.11459](https://arxiv.org/abs/2104.11459) —— SOT-MRAM 三端；能效优于 STT；field-free 切换为卡点。
9. GlobalFoundries / AnandTech. (2020-03). *GLOBALFOUNDRIES Delivers Industry's First Production-ready eMRAM on 22FDX*. [gf.com/.../industrys-first-production-ready-emram-22fdx-platform-iot/](https://gf.com/gf-press-release/globalfoundries-delivers-industrys-first-production-ready-emram-22fdx-platform-iot/) —— **4–48 Mb 宏**、**10⁵ 次**、**−40 至 125 °C 下保持 10 年**、磁免疫 **~600 Oe @105 °C**。
10. Promwad. (2025). *Adaptive Memory Hierarchies: Combining SRAM, MRAM, and ReRAM for Smarter Edge Systems*. [promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) —— **~80%** 空闲能耗削减（厂方声明，方向性）；MRAM **~10¹⁵** vs ReRAM **10⁶–10⁹** vs Flash **~10⁴** 耐久。
11. MEMPHIS Electronic / Wevolver. (2024). *Three Edge AI Architectures That Demand Smarter Memory—and Why?*. [wevolver.com/.../three-edge-ai-architectures-that-demand-smarter-memoryand-why](https://www.wevolver.com/article/three-edge-ai-architectures-that-demand-smarter-memoryand-why) —— 嵌入式 MRAM **4–16 MB**、**100–200 MHz**、**<30 ns**、**>10¹² 次**、**85 °C 下 20+ 年**。
12. Shilov, A. (2024). *TSMC tandem builds exotic new MRAM-based memory*. Tom's Hardware. [tomshardware.com/.../tsmc-tandem-builds-exotic-new-memory-...](https://www.tomshardware.com/pc-components/dram/tsmc-tandem-builds-exotic-new-memory-with-radically-lower-latency-and-power-consumption-mram-based-memory-can-also-conduct-its-own-compute-operations) —— TSMC + ITRI SOT-MRAM 面向 LLC 与近存计算。
13. SemiWiki forum. (2022/2023). *TSMC officially halts SRAM scaling*. [semiwiki.com/forum/threads/tsmc-officially-halts-sram-scaling.17223/](https://semiwiki.com/forum/threads/tsmc-officially-halts-sram-scaling.17223/) —— 引 IEDM 2022 *"Did We Just Witness The Death Of SRAM?"*，系统级动因。
14. 本项目 A16h 锚点。[advanced/A16h-STT-SOT-MRAM多级缓存方案.md](../../advanced/A16h-STT-SOT-MRAM多级缓存方案.md).

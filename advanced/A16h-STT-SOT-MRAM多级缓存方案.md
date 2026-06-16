# A16h · STT/SOT-MRAM 多级缓存方案（往金字塔里插一层非易失、低漏电的缓存）

> **一句话定位**：[A15](A15-前沿-先进内存.md) 在 DRAM 与闪存之间插新层；本篇往**更上面**插——在 **SRAM 缓存与 DRAM 之间**，插一层**非易失、低静态漏电、密度高于 SRAM** 的磁存储 **MRAM**（STT / SOT 两种写入机制）。它能做更大的末级缓存、能让权重**断电不丢（instant-on）**，正好缓解 Agent 时代的**增长 + 续航**双重压力。这是 A16「**增长**」轴的芯片侧一题。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「存储金字塔」——在 `寄存器/SRAM 缓存 → DRAM` 这一段**插入一层非易失缓存**，并改变"缓存断电即失、且持续漏电"的前提。
> 🧭 **阅读前置**：先读 [A15 前沿·先进内存](A15-前沿-先进内存.md)（介质谱系与分层思想，本篇是其往缓存层的延伸）；MRAM 做计算见 [A16g DRAM·PIM 协同](A16g-DRAM-PIM异构协同管理.md)；权重/KV 常驻见 [A16f](A16f-端侧KV-Cache管理方案.md)。
> 🌡️ **演进分级**：**演进厚 ⚡（开放连载，偏器件/前瞻）**——嵌入式 MRAM（eMRAM）已量产替 eFlash，但**作大容量缓存/LLC 仍属研究**；行文重在**器件取舍 → 在层级里的位置 → 趋势**，端侧产品化判断按时间衰减看待。

---

## 1. 定位：金字塔里缺一层"非易失的缓存"

[00 存储金字塔](../foundations/00-内存系统总览.md) 的经典分层有个长期空白：**缓存层（SRAM）快但有两个硬伤——断电即失、且随工艺缩小静态漏电越来越重；DRAM 密度高但要不断刷新（refresh）耗电**。两者之间没有"既非易失、又比 DRAM 快、又比 SRAM 省漏电"的层。

MRAM（磁阻随机存储）想补的就是这一格：

> **用磁隧道结（MTJ）的电阻高低存 0/1**——**非易失**（断电不丢、无需 refresh）、**无静态漏电**（不用时不耗电）、**密度高于 SRAM**，速度介于 SRAM 与 DRAM 之间。把它插进 `SRAM → DRAM` 之间做**末级缓存 / 持久缓存**，就是本篇的"多级缓存方案"。

## 2. 负载动因：增长 + 续航，逼着缓存层"非易失化"

本篇属于 A16「**增长**」轴。按 [A16 总论](A16-前沿-Agent时代内存负载.md) 的终端立场，MRAM 之所以值得认真考虑，是它同时回应了 Agent 时代两个压力：

- **增长**：模型权重大、要反复从闪存载入 DRAM 再进缓存；一个**非易失、够密的缓存层**能让**常用权重断电后仍驻留**，省掉反复 reload 的带宽与能耗——相当于给增长压力开一个"持久缓冲"。
- **续航**：随工艺节点缩小，**SRAM 静态漏电**成了电池设备的大头；**DRAM refresh** 也持续耗电。MRAM **非易失 → 无 refresh、不用时零静态功耗**，混合层级实测可把**空闲能耗降约 80%**（靠消除 DRAM refresh，[Adaptive Memory Hierarchies, promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram)）。
- **终端立场**：与 [A16e](A16e-IOMMU统一内存与异构PF-LRU.md)/[A16f](A16f-端侧KV-Cache管理方案.md) 一样，MRAM 的收益要在"**和传统负载共处一机**"下成立——instant-on（断电恢复快）对手机冷启动、低功耗待机尤其有价值。

> 一句话动因：**增长要"更大的缓存 + 权重持久驻留"，续航要"缓存别再漏电、DRAM 别再 refresh"——MRAM 的非易失 + 低漏电正好同时给这两个。**

## 3. 机制本体：STT vs SOT，以及它在层级里的位置

### 3.1 两种写入机制：STT 与 SOT

MRAM 都用 MTJ 存值，差别在**怎么写**：

| | **STT-MRAM**（自旋转移矩） | **SOT-MRAM**（自旋轨道矩） |
|---|---|---|
| 结构 | 2 端，**写电流穿过 MTJ** | **3 端，读写电流路径分离** |
| 耐久 | 受限（写电流反复冲击 MTJ）；TSMC 16nm 报约 **10¹²** 次 | **读写解耦 → 近乎无限耐久**、解决 MTJ 电阻限制 |
| 写能耗/速度 | 写电流大、写较慢/费电 | **能耗大降、速度快**（ITRI+TSMC IEDM'23：功耗约 STT 的 **1%**、约 **10ns**） |
| 成熟度 | **已商用**（替 eFlash、慢 SRAM）；TSMC 22/16nm 量产 | **较新、仍研究**；cell 比 SRAM 大、更难做 |

量级锚点（厂商/论文声明，**待独立复核**）：TSMC 16nm FinFET STT-MRAM 读/写约 **7.5 / 20 ns**、**10¹²** 写耐久、125℃ 下约 1 分钟保持（[TSMC MRAM research](https://research.tsmc.com/page/mram/1.html)）；SOT-MRAM 被寄望**在缓存层替代 SRAM**，但"cell 仍大于 SRAM、短期难全面替代 SRAM"（[Memory lane: SOT-MRAM in 2024, EDN](https://www.edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/)）。

### 3.2 它该插在层级的哪一格

MRAM **不是来替 SRAM 当 L1 的**（写慢、cell 大），而是**做更下面的缓存层**：

```
   L1/L2 SRAM            快、易失、高漏电          ← 仍是 SRAM
   ├─ LLC / 持久缓存：MRAM   非易失、低漏电、密度高、速度中  ← 本篇插入层
   ├─ DRAM / LPDDR        高密、需 refresh
   └─ UFS / 闪存          非易失、慢                ← A16i
```

典型 eMRAM 实现 **4–16 MB、100–200MHz、<30ns、>10¹² 写**，正好适合**存 AI 权重、持久缓存、instant-on 缓冲**（[edge AI memory, Memphis/Wevolver](https://www.memphis.de/en/techhub/memory-knowhow/edge-ai-memory)）。

### 3.3 "多级"的要义：混合，而非替换

关键不是"用 MRAM 替掉谁"，而是**混合层级**：**SRAM 做 L1/L2 求速度，MRAM 做 LLC/持久层求密度 + 非易失**，甚至再配 ReRAM——按 AI 活动在 active/idle 间切换用哪层（[Adaptive Memory Hierarchies, promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram)）。MRAM 还能**把代码与数据统一在一块、同时替掉 SRAM 与 eFlash**，简化嵌入式存储。

## 4. 历史：从替 eFlash 到"作缓存层 / 存权重"

```
SRAM + eFlash（嵌入式经典两件套）
   ▼ STT-MRAM 商用：替 eFlash、替慢 SRAM（TSMC 22nm 量产，2019–）
   ▼ STT-MRAM 进 FinFET：16nm，7.5/20ns、10^12 耐久（2024）
   ▼ SOT-MRAM 研究：读写解耦、近无限耐久、低功耗（ITRI+TSMC IEDM'23）
   ▼ 作缓存层 / AI 权重持久存储（2024–25，边缘 AI）
```

一句话：**MRAM 先从"替 eFlash"切入量产，再凭非易失 + 低漏电，往"缓存层 + AI 权重存储"爬——LLM 权重的"大且要反复载入"给了它新的用武之地。**

## 5. 现状与平台差异

| 维度 | 现状 |
|---|---|
| eMRAM 替 eFlash | **已量产**（TSMC/三星/GF 等，汽车/MCU/IoT） |
| MRAM 作大容量 LLC | **仍研究/早期**；SOT-MRAM 替 SRAM 缓存"短期不会发生"（[EDN 2024](https://www.edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/)） |
| 移动 SoC 用 MRAM 做缓存/权重 | **待核实**——消费级手机 SoC 是否、何时用 MRAM 做 LLC 或权重存储，无明确公开信息 |
| MRAM 做计算 | TSMC tandem 报"MRAM 基础上做计算"（与 [A16g PIM](A16g-DRAM-PIM异构协同管理.md) 合流，[Tom's Hardware](https://www.tomshardware.com/pc-components/dram/tsmc-tandem-builds-exotic-new-memory-with-radically-lower-latency-and-power-consumption-mram-based-memory-can-also-conduct-its-own-compute-operations)） |

> **术语警示**：MRAM（磁阻）≠ ReRAM（阻变）≠ FeRAM（铁电）≠ PCM（相变）——都是新型非易失存储但物理机制、特性各异（综述见 [Progress of emerging NVM, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/)）。本篇只讲 MRAM。

## 6. 趋势与未解问题 ← 本篇重心

- **写能耗/延迟是 STT 的命门**：STT 写电流大、写慢，做缓存时"写密集"场景吃亏；**SOT 用读写解耦解决了耐久与部分能耗，但 3 端结构面积更大、工艺更难**——容量、速度、面积的三角还没到甜点。
- **容量 vs 速度的定位**：MRAM 卡在"比 SRAM 密但比 SRAM 慢、比 DRAM 快但比 DRAM 贵/小"的中间带，**到底该做 LLC 还是做持久权重存储，取决于具体负载**，无统一答案。
- **与 PIM 合流**：MRAM 阵列也能就地做计算（[Tom's Hardware](https://www.tomshardware.com/pc-components/dram/tsmc-tandem-builds-exotic-new-memory-with-radically-lower-latency-and-power-consumption-mram-based-memory-can-also-conduct-its-own-compute-operations)、[Edge-Optimized MRAM Near-Memory Computing, ResearchGate](https://www.researchgate.net/publication/390075795_Edge-Optimized_AI_Architecture_MRAM-based_Near_Memory_Computing_macro_Balancing_between_Memory_Capacity_and_Computation)）——"非易失存权重 + 就地算"是与 [A16g](A16g-DRAM-PIM异构协同管理.md) 交汇的诱人方向。
- **非易失带来的新问题**：缓存非易失意味着**断电后数据仍在**——安全上要考虑残留数据擦除（含 [A16f](A16f-端侧KV-Cache管理方案.md) 的用户上下文）；一致性上要考虑"持久缓存"的写顺序语义（类似持久内存的 ordering）。
- **端侧产品化时间线高度不确定**：消费手机 SoC 用 MRAM 做 LLC/权重层，**何时落地待核实**，按时间衰减看待。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| 介质谱系 ← 先进内存 | 本篇是分层思想往缓存层的延伸 | **[A15](A15-前沿-先进内存.md)** |
| 金字塔插层 ← 存储层级 | 在 SRAM↔DRAM 间插非易失缓存 | [00 总览](../foundations/00-内存系统总览.md) |
| 权重持久驻留 → KV/权重 | instant-on、权重不重载，缓解增长 | [A16f](A16f-端侧KV-Cache管理方案.md) |
| MRAM 计算 ↔ PIM | 非易失存 + 就地算 | **[A16g](A16g-DRAM-PIM异构协同管理.md)** |
| 与闪存层的分工 | MRAM（快非易失缓存）vs UFS/HBF（慢非易失后端） | [A16i](A16i-端侧UFS-HBF增强.md) |

## 8. 实测 / 观测点

- MRAM 多在**器件/SoC 设计层**，**无 OS 用户态观测口径**；嵌入式场景由 SoC 厂商工具链/数据手册给参数；
- 系统侧可间接观察的是**功耗/待机能耗**（非易失缓存的收益主要体现在 idle 能耗与冷启动时间）；
- 器件参数（读写延迟、耐久、保持）以厂商数据手册与 IEDM/ISSCC 论文为准。

## 9. 来源与延伸阅读

**MRAM 器件与作缓存/SRAM 替代**
- [TSMC MRAM research (22/16nm STT-MRAM 参数)](https://research.tsmc.com/page/mram/1.html)
- [Memory lane: Where SOT-MRAM technology stands in 2024 (EDN)](https://www.edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/) —— SOT 替 SRAM 缓存的前景与短期局限
- [Progress of emerging non-volatile memory technologies in industry (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/) —— MRAM/ReRAM/FeRAM/PCM 横向综述
- [Roadmap of spin-orbit torques (arXiv 2104.11459)](https://arxiv.org/pdf/2104.11459) —— SOT 物理与器件路线

**边缘 AI 的 MRAM 缓存/权重存储**
- [Adaptive Memory Hierarchies: SRAM/MRAM/ReRAM for Edge (promwad)](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) —— 混合层级、idle 能耗降约 80%
- [Three Edge AI Architectures That Demand Smarter Memory (Wevolver/Memphis)](https://www.memphis.de/en/techhub/memory-knowhow/edge-ai-memory) —— MRAM 4–16MB、instant-on、权重存储
- [TSMC tandem MRAM-based memory that can compute (Tom's Hardware)](https://www.tomshardware.com/pc-components/dram/tsmc-tandem-builds-exotic-new-memory-with-radically-lower-latency-and-power-consumption-mram-based-memory-can-also-conduct-its-own-compute-operations) —— 与 PIM 合流

**承接 / 相邻篇**
- [A15 前沿·先进内存](A15-前沿-先进内存.md)、[A16g DRAM·PIM 异构协同](A16g-DRAM-PIM异构协同管理.md)、[A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md)、[A16i 端侧 UFS–HBF 增强](A16i-端侧UFS-HBF增强.md)、[00 总览](../foundations/00-内存系统总览.md)

> **待核实 / 待补**：MRAM 各项器件参数均为厂商/论文声明，需独立复核；消费级移动 SoC 用 MRAM 做 LLC / 权重存储的实际产品与时间线（无明确公开信息）；SOT-MRAM 量产节点与良率；MRAM 持久缓存的写顺序/一致性语义与安全擦除方案；与 [A16g PIM](A16g-DRAM-PIM异构协同管理.md) 的 MRAM 近内存计算落地情况；HarmonyOS/iOS/Android 是否有任何 OS 层对非易失缓存的感知（基本无）。

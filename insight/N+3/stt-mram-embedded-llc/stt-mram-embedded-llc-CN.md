# STT-MRAM 嵌入式商用化与末级缓存应用

> 本文对比"原始方案"（嵌入式 Flash + SRAM）与"演进方案"（STT-MRAM 统一嵌入式非易失存储与缓存替代），综述学术（Nature Reviews、VLSI/IEDM/ISSCC 会议）及产业（TSMC、三星、GlobalFoundries、IBM、NXP、瑞萨、Everspin、Avalanche Technology）2018–2026 年进展。

## 1. 范围与方法

**领域定义。** 面向 SoC（系统级芯片）设计的嵌入式非易失存储器（eNVM）——覆盖微控制器（MCU）、汽车电子 ECU、IoT 端侧芯片——以及处理器片上末级缓存（LLC）。范围包括：在 28 nm 及以下节点替代嵌入式 Flash（eFlash）作为主流 eNVM 技术，以及在大容量 LLC 阵列中替代 SRAM 以降低漏电功耗。

**"原始方案"与"演进方案"的含义。** *原始方案*是业界沿用数十年的 eFlash + SRAM 架构：分裂栅或浮栅 NOR Flash 在前道（FEOL）制造，用于代码/数据存储；6T-SRAM 用于工作存储器与缓存。*演进方案*是自旋转移矩磁性随机存取存储器（STT-MRAM），在后道（BEOL）制造，可同时替代 eFlash（作为 eNVM）和 SRAM（作为非易失工作存储器或 LLC），将两种原本分立的存储功能统一为单一技术。

**资料来源。** 16 篇主要来源：4 篇综述文章（Nature Reviews Electrical Engineering、MRS Communications、ACM TECS、ScienceDirect）、5 篇会议论文（VLSI 2024、IEDM 2024、ISSCC 2024、IEDM 2018、ISSCC 2019）、4 则产业公告（NXP/TSMC、瑞萨、Everspin/GlobalFoundries、三星）、3 份厂商技术文档（Avalanche Technology、Synopsys、GlobalFoundries）。来源类型涵盖同行评审综述、会议论文集、新闻稿及产品文档。

## 2. 问题背景

**系统需要完成什么。** 在先进工艺节点（28 nm、22 nm、16 nm FinFET 及更先进节点）上，将非易失存储器与高速工作存储器集成到同一颗芯片的逻辑工艺中。汽车 MCU 要求代码存储具备 150 °C 下 20 年数据保持、>10^6 次写入耐久、并通过 AEC-Q100 Grade 1 认证。IoT 及边缘设备要求超低待机功耗并具备即时唤醒能力。处理器 LLC 要求 <10 ns 读取延迟、>10^14 次写入耐久，且密度显著高于 6T-SRAM。

**为什么这个领域变得困难。** 嵌入式 Flash 是成熟且充分验证的技术，已服务行业数十年。然而，它在 28 nm 面临硬性缩放壁垒：浮栅或电荷捕获单元需要厚隧穿氧化层和高编程电压（10–20 V），与先进 FinFET 工艺规则不兼容。额外的 FEOL 工艺步骤（7–13 道额外光罩）使晶圆成本增加 20–30% [Synopsys, SemiEngineering]。与此同时，6T-SRAM 单元的相对面积随晶体管几何尺寸缩小而增大——在 7 nm 节点，SRAM 比特单元面积约 0.021 um^2，但每比特漏电功耗使大规模 SRAM 阵列在 LLC 级别的能量预算中变得过于昂贵。

**为什么原始方案不再足够。** 汽车与工业 MCU 路线图要求向 22 nm 和 16 nm 工艺迁移以获得性能、功耗和面积（PPA）改善，但 eFlash 无法跟随。多兆字节规模的 SRAM LLC 消耗过多的待机功耗——32 MB SRAM LLC 的漏电功耗可能超过其服务的计算核心的动态功耗。行业需要一种可扩展至先进节点、具备非易失性并降低漏电的统一存储技术。

## 3. 具体问题与瓶颈证据

1. **eFlash 无法缩放到 28 nm 以下** — 浮栅单元需要厚栅氧化层（8–10 nm）和高编程电压（10–20 V），与 FinFET 工艺规则在物理上不兼容。行业共识将 28/22 nm 视为 eFlash 的终点，原因并非基础物理限制，而是经济壁垒：额外的光罩数量（7–13 道）和工艺复杂度使 28 nm 以下的 eFlash 在成本上不可行 [SemiEngineering, Synopsys]。

2. **eFlash 光罩附加推高晶圆成本** — 嵌入 NOR Flash 需要在基础逻辑工艺之上增加 5–13 道光刻掩模，使晶圆成本增加 20–30%。一种宣称仅需 7 道额外光罩的 28 nm HKMG 分裂栅 eFlash 设计仍然代表了显著的成本开销 [IEDM 2018, Intel 22FFL]。

3. **SRAM 漏电在大规模 LLC 中主导功耗** — 7 nm 节点的 6T-SRAM 单元比特面积约 0.021 um^2，但六晶体管拓扑（140 F^2）导致显著的亚阈值漏电和栅极漏电。对于多兆字节的 LLC 阵列，待机漏电可能超过逻辑核心的动态开关功耗 [ACM TECS]。

4. **此前不存在统一的 eNVM + 工作存储器方案** — 在 STT-MRAM 之前，嵌入式非易失存储（eFlash）和工作存储器（SRAM）需要完全不同的制造工艺、单元结构和设计方法学，无法实现架构统一。

### 瓶颈证据

| 指标 | eFlash（28 nm） | SRAM（7 nm LLC） | 影响 |
|---|---|---|---|
| 额外光罩层数 | 7–13 | 0（基础工艺包含） | 晶圆成本增加 20–30% |
| 最小可缩放节点 | 28 nm（硬性壁垒） | 随逻辑工艺持续缩小 | 阻断 MCU 工艺迁移 |
| 单元拓扑 | 2T（分裂栅） | 6T | FEOL 与基础工艺不同 |
| 写入耐久 | 10^4–10^5 次 | 无限（易失） | eFlash 限制 OTA 更新频率 |
| 待机功耗（32 MB） | 近零（非易失） | ~数百 mW 漏电 | SRAM LLC 漏电主导 SoC 功耗 |
| 编程电压 | 10–20 V | ~0.7 V (V_DD) | eFlash 需要电荷泵、高压晶体管 |

## 4. 架构：原始方案 vs 演进方案

**原始方案 — eFlash + SRAM**

```
 SoC 芯片（28 nm 平面 CMOS）
 +---------------------------------------------------------+
 |                                                         |
 |  +----------------+   +----------------+                |
 |  |  逻辑核心      |   |  外设          |                |
 |  +----------------+   +----------------+                |
 |         |                     |                         |
 |         v                     v                         |
 |  +--------------+    +------------------+               |
 |  |  SRAM 缓存   |    |  eFlash (NOR)    |               |
 |  |  (6T, FEOL)  |    |  (分裂栅,        |               |
 |  |  易失性      |    |   FEOL, 7-13     |               |
 |  |  快速读写    |    |   额外光罩)      |               |
 |  |  高漏电      |    |  代码 + 配置     |               |
 |  +--------------+    +------------------+               |
 |                                                         |
 |  * 两种分立的存储技术                                    |
 |  * eFlash 将芯片锁定在 >=28nm 节点                      |
 |  * eFlash 光罩带来 20-30% 晶圆成本附加                  |
 +---------------------------------------------------------+
```

*原始方案：eFlash 通过 7–13 道额外 FEOL 光罩提供非易失代码/数据存储；SRAM 提供易失性缓存/工作存储器。两个分立的工艺模块，锁定在 28 nm 或更老节点。*

**演进方案 — STT-MRAM（eNVM + 工作存储器 + LLC）**

```
 SoC 芯片（22nm / 16nm FinFET / 更先进节点）
 +---------------------------------------------------------+
 |                                                         |
 |  +----------------+   +----------------+                |
 |  |  逻辑核心      |   |  外设          |                |
 |  +----------------+   +----------------+                |
 |         |                     |                         |
 |         v                     v                         |
 |  +----------------------------------------------------+ |
 |  |  * STT-MRAM (1T-1MTJ, BEOL, 2-3 道额外光罩)       | |
 |  |                                                    | |
 |  |  +-----------+  +-----------+  +----------------+  | |
 |  |  | eNVM      |  | 工作存储器|  | 末级缓存       |  | |
 |  |  | (替代     |  | (替代     |  | (LLC, 替代     |  | |
 |  |  |  eFlash)  |  |  SRAM)    |  |  SRAM LLC)     |  | |
 |  |  | 10年保持  |  | 10^9 耐久|  | 10^14+ 耐久    |  | |
 |  |  | 10^6 耐久 |  |           |  |                |  | |
 |  |  +-----------+  +-----------+  +----------------+  | |
 |  |                                                    | |
 |  |  * 单一 BEOL 技术，三种应用模式                     | |
 |  |  * 随逻辑工艺缩放至 16nm、12nm、5nm                 | |
 |  |  * 相比 eFlash 节省 15-40% 面积                     | |
 |  +----------------------------------------------------+ |
 |                                                         |
 +---------------------------------------------------------+
```

*演进方案：单一 STT-MRAM BEOL 模块（2–3 道额外光罩）通过三种应用模式——eNVM、工作存储器和 LLC——替代 eFlash 和 SRAM，每种模式通过调节保持力/耐久力权衡实现。标 `*` 为新增/变更要素。*

## 5. 演进方案为何有效，以及尚未解决什么

### 为何有效

- **eFlash 无法缩放到 28 nm 以下** — STT-MRAM 完全在 BEOL（金属互连层之间）制造，无需修改 FEOL 晶体管工艺，因此兼容 FinFET 节点：TSMC 在 22 nm（已量产）和 16 nm FinFET（已通过汽车认证）提供 eMRAM，12 nm 在研发中，5 nm 已宣布用于欧洲汽车 AI [TSMC, NXP]。GlobalFoundries 提供 22FDX eMRAM，12 nm FinFET 正在开发中 [Everspin/GF]。三星已展示 14 nm FinFET eMRAM [IEDM 2024]。Intel 在 IEDM 2018 展示了 22 nm FinFET eMRAM。

- **eFlash 光罩附加推高晶圆成本** — STT-MRAM 仅需 2–3 道额外 BEOL 光罩，相比 eFlash 的 7–13 道，并在同一节点上比同等容量的 eFlash 节省 15–40% 芯片面积 [ISSCC 2019, SemiEngineering]。这一经济优势在先进节点上随光罩成本攀升而进一步放大。

- **SRAM 漏电在大规模 LLC 中主导功耗** — STT-MRAM 的 1T-1MTJ 单元（36 F^2）比 6T-SRAM（140 F^2）密度高约 4 倍，且其非易失性意味着零待机漏电——单元在断电后仍保持数据。这使得多兆字节 LLC 在不引发 SRAM 功耗预算爆炸的情况下成为可能 [ACM TECS]。在密度超过 0.4 MB 时，STT-MRAM 在读操作上更节能；超过 5 MB 时，在写操作上也更优。

- **此前不存在统一的 eNVM + 工作存储器方案** — STT-MRAM 通过调节 MTJ 参数（保持势垒高度与开关电流之间的权衡）提供三种不同的工作模式：高保持 eNVM 模式（10 年保持、10^6 耐久）、中等保持工作存储器模式（数小时至数天保持、10^9 耐久，超低功耗边缘/IoT）、低保持 LLC 模式（数秒至数分钟保持、10^14+ 耐久，亚 10 ns 开关）。单一 BEOL 模块可服务全部三种角色 [Nature Reviews EE]。

### 尚未解决的问题

- **写入延迟差距 vs SRAM** — STT-MRAM 量产写入延迟为 10–30 ns，而 SRAM 为 1–3 ns。即使 IBM/三星在 VLSI 2024 演示的 2 ns 也使用了尚未量产的有序合金 MTJ [VLSI 2024]。对于写入延迟敏感的 L1/L2 缓存，STT-MRAM 仍然太慢。

- **写入能量高于 SRAM** — STT 开关每个 MTJ 需要约 100 uA 电流持续约 10 ns，单比特写入能量约 100 fJ——大约是相当节点 SRAM 写入能量的 10 倍。这对 LLC（写入不频繁）可以接受，但对写入密集型缓存层级构成问题。

- **LLC 的耐久性天花板** — 量产 eMRAM 耐久性通常为 10^6 次（eNVM 模式）。LLC 要求 >10^14 次。实现此目标需要降低保持势垒，从而牺牲数据保持时间。Avalanche Technology 声称其离散产品达到 10^16 耐久 [Avalanche]，但嵌入式代工厂工艺尚未在晶圆级大规模认证 LLC 级耐久性。

- **读取干扰** — STT-MRAM 的读和写使用同一电流路径（通过 MTJ），存在读取电流意外翻转自由层的风险。这限制了读取电流（因而限制读取速度）并要求仔细的设计裕度。SOT-MRAM 通过分离读写路径消除了此问题，但尚未商用。

- **保持力的温度敏感性** — MTJ 保持力随温度呈指数级退化。在 150 °C 下实现 10 年保持（汽车 Grade 1）需要更大的 MTJ 柱体，这会增大开关电流和单元面积，直接牺牲密度和速度。

## 6. 对比表

| 维度 | 原始方案（eFlash + SRAM） | 演进方案（STT-MRAM） | 变化 | 来源 |
|---|---|---|---|---|
| 额外光罩层数（eNVM） | 7–13（FEOL） | 2–3（BEOL） | 减少 5–10 道 | [SemiEngineering] |
| 晶圆成本附加 | 20–30% | ~5–8% | 降低 15–22 个百分点 | [Synopsys] |
| 最小可缩放节点 | 28 nm（eFlash 壁垒） | 5 nm（TSMC 路线图） | 跨越 5+ 代工艺节点 | [TSMC] |
| eNVM 芯片面积（同等容量） | 1×（eFlash 基准） | 0.60–0.85× | 减少 15–40% | [ISSCC 2019] |
| eNVM 数据保持 | 150 °C 下 10 年 | 150 °C 下 10–20 年 | 相当 | [TSMC 16nm, 三星 14nm] |
| eNVM 写入耐久 | 10^4–10^5 次 | 10^6 次（量产） | 提升 10–100× | [三星 IEDM 2024] |
| LLC 单元面积（vs 6T-SRAM） | 1×（140 F^2, 6T） | ~0.26×（36 F^2, 1T-1MTJ） | 密度提升约 4× | [ACM TECS] |
| LLC 待机漏电 | 高（亚阈值 + 栅极漏电） | 近零（非易失） | 降低约 100× | [ACM TECS] |
| LLC 读取延迟 | 1–3 ns（SRAM） | 3–10 ns（STT-MRAM） | 慢 3–10× | [Nature Reviews EE] |
| LLC 写入延迟 | 1–3 ns（SRAM） | 10–30 ns（量产）；2 ns（实验室） | 慢 3–15× | [VLSI 2024] |
| LLC 写入耐久 | 无限（易失） | 10^9–10^16（取决于模式） | 有限但实用 | [Avalanche, Nature Reviews EE] |
| 待机功耗（非易失） | eFlash: 零；SRAM: 高 | STT-MRAM: 零 | 统一 NV + 低漏电 | [Nature Reviews EE] |

## 7. 一词概括

**统一**（Unified）— STT-MRAM 将嵌入式非易失存储、工作存储器和末级缓存统一为单一 BEOL 技术，以一种 1T-1MTJ 单元替代两个分立的 FEOL/SRAM 模块，通过调节保持力-耐久力权衡来适配不同应用模式——将存储层次从两种异质技术坍缩为一种。

## 8. 未解问题与注意事项

- **LLC 耐久性认证差距** — 尚无代工厂公开认证耐久性 >10^14 的 eMRAM 工艺用于 LLC。10^16 的数据来自 Avalanche Technology 的离散产品，而非嵌入式代工 PDK。在晶圆级别从 10^6（eNVM 量产）跨越到 10^14（LLC 需求）仍是开放的工程挑战。

- **2 ns 开关速度仅限实验室** — IBM/三星在 VLSI 2024 展示的 2 ns STT 开关使用了基于 Mn 的有序合金 MTJ，而非量产中的标准 CoFeB/MgO 结构。将其转移至代工厂 BEOL 模块并达到 >99.9% 良率尚未得到验证。

- **SOT-MRAM 作为颠覆性后继者** — 自旋轨道矩 MRAM 分离了读写电流路径，消除了读取干扰，并实现亚纳秒开关与 >10^15 耐久（imec, VLSI/IEDM 2024）。如果 SOT-MRAM 在 STT-MRAM 攻克 LLC 领域之前成熟，STT-MRAM 可能被限制在其已经主导的 eNVM 角色。

- **RRAM/ReRAM 在 eNVM 领域的竞争** — 英飞凌为其 AURIX TC4x 汽车 MCU 系列选择了 RRAM（而非 MRAM），采用 TSMC 28 nm 工艺。RRAM 提供更简单的集成和更低的每比特成本，适用于写入不频繁的应用。eNVM 市场可能在 MRAM（高耐久、高速）和 RRAM（低成本、中等耐久）之间分化，而非收敛至单一赢家。

- **汽车 Grade 0（175 °C）热可靠性** — 多数 eMRAM 认证针对 AEC-Q100 Grade 1（150 °C）。Grade 0（175 °C，发动机舱环境）要求更大的 MTJ 柱体或新材料体系，其面积和功耗代价在公开文献中尚未充分表征。

- **存算一体扩展** — STT-MRAM 的电阻态可被用于片上布尔逻辑和模拟乘累加运算（Cadence AI 路线图, 2024）。如果存算一体成为主要用例，MTJ 设计权衡（TMR 比值、电阻均匀性）可能偏离为纯存储应用优化的方向。

- **成本平价时间表** — 虽然 STT-MRAM 的光罩附加数少于 eFlash，但 MTJ 沉积和刻蚀步骤使用专用设备（溅射工具、离子束刻蚀），吞吐量低于标准 CMOS 设备。在大规模量产中达到 eFlash 等效的每比特成本仍是工艺优化的活跃领域。

## 9. 参考文献

1. **Worledge & Hu, Nature Reviews Electrical Engineering (2024)** — "Spin-transfer torque magnetoresistive random access memory technology status and future directions." Vol. 1, No. 11, pp. 730–747. DOI: 10.1038/s44287-024-00111-z. URL: https://www.nature.com/articles/s44287-024-00111-z
2. **Hellenbrand et al., MRS Communications (2024)** — "Progress of emerging non-volatile memory technologies in industry." DOI: 10.1557/s43579-024-00660-2. URL: https://link.springer.com/article/10.1557/s43579-024-00660-2
3. **IBM Research, VLSI 2024** — "First demonstration of high retention energy barriers and 2 ns switching, using magnetic ordered-alloy-based STT MRAM devices." URL: https://research.ibm.com/publications/first-demonstration-of-high-retention-energy-barriers-and-2-ns-switching-using-magnetic-ordered-alloy-based-stt-mram-devices
4. **IBM Research, IEDM 2024** — "Ultra-Fast & Low Power STT-Switching of Ferrimagnetic Heusler Alloys for MRAM." URL: https://research.ibm.com/publications/ultra-fast-and-low-power-stt-switching-of-ferrimagnetic-heusler-alloys-for-mram
5. **三星半导体, IEDM 2024** — "Developing the Industry's Most Energy-Efficient Next-Generation MRAM." 14nm FinFET eMRAM，创纪录能效。URL: https://semiconductor.samsung.com/news-events/tech-blog/developing-the-industrys-most-energy-efficient-next-generation-mram-selected-as-iedm-highlight-paper/
6. **NXP / TSMC (2023)** — "NXP and TSMC to Deliver Industry's First Automotive 16 nm FinFET Embedded MRAM." URL: https://www.nxp.com/company/about-nxp/newsroom/NW-NXP-AND-TSMC-DELIVER-FIRST16NM-FINFET-MRAM
7. **NXP S32K5 (2025)** — "NXP Rolls Out Automotive MCU for Zonal SDVs, Leveraging MRAM." 首款 16nm FinFET 汽车 MCU 搭载 eMRAM。URL: https://www.allaboutcircuits.com/news/nxp-rolls-out-automotive-mcu-for-zonal-sdvs-leveraging-mram/
8. **瑞萨, ISSCC 2024** — 嵌入式 STT-MRAM MCU，TSMC 22nm ULL 工艺，>200 MHz 随机读取。URL: https://www.edgeir.com/renesas-develops-advanced-memory-technology-for-microcontrollers-20240228
9. **Everspin / GlobalFoundries (2024)** — "Everspin Technologies and GlobalFoundries Extend MRAM Joint Development Agreement to 12nm." URL: https://investor.everspin.com/news-releases/news-release-details/everspin-technologies-and-globalfoundries-extend-mram-joint
10. **Intel, IEDM 2018** — "MRAM as Embedded Non-Volatile Memory Solution for 22FFL FinFET Technology." URL: https://ieeexplore.ieee.org/document/8614620/
11. **Avalanche Technology** — "Data Endurance, Retention and Field Immunity in STT-MRAM." Application Note AN000002. 航天级产品 10^16 写入耐久。URL: https://www.avalanche-technology.com/wp-content/uploads/AN000002-Avalanche-STT-MRAM-Device-Characteristics-and-Capabilities.pdf
12. **Dey et al., ACM TECS (2022)** — "Microarchitectural Exploration of STT-MRAM Last-level Cache Parameters for Energy-efficient Devices." DOI: 10.1145/3490391. URL: https://dl.acm.org/doi/full/10.1145/3490391
13. **Salehi et al., ScienceDirect (2021)** — "Design of an area and energy-efficient last-level cache memory using STT-MRAM." URL: https://www.sciencedirect.com/science/article/abs/pii/S030488532100158X
14. **Synopsys IP** — "Future NVM Memories for Microcontrollers." URL: https://www.synopsys.com/designware-ip/technical-bulletin/future-nvm-memories.html
15. **SemiEngineering** — "MRAM Getting More Attention At Smallest Nodes." URL: https://semiengineering.com/mram-getting-more-attention-at-smallest-nodes/
16. **imec, VLSI/IEDM 2024** — SOT-MRAM 缩放演示：亚 100 fJ 开关能量、>10^15 耐久、复合自由层达到 10^-6 写入错误率。URL: https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications

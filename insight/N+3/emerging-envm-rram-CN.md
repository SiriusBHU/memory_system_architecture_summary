# 新型嵌入式 NVM 生态：ReRAM/RRAM 取代嵌入式闪存

> **范围**：追踪从嵌入式闪存（eFlash / NOR Flash）到电阻式随机存取存储器（ReRAM / RRAM）作为 MCU、IoT SoC、汽车控制器及边缘 AI 加速器的事实标准嵌入式非易失性存储器（eNVM）的技术演进。重点关注工艺可扩展性、制造成本、性能表现、代工厂生态，以及新兴的存内计算（CIM）应用。
>
> **方法**：交叉参考 Weebit Nano ICCAD 2024 演讲、MRS Communications 行业综述（2024年11月）、台积电代工平台数据、TechInsights 路线图（2024年5月）、Yole Emerging NVM 2025 报告、英飞凌 AURIX TC4x 公告及各厂商新闻稿。所有成本对比均采用相对于基线 CMOS 逻辑工艺的晶圆级成本增加百分比。

---

## 1. 问题背景

每一颗微控制器、IoT 传感器和汽车 ECU 都需要片上非易失性存储器来保存固件、校准数据和安全密钥。数十年来，**嵌入式 NOR 闪存（eFlash）** 一直承担这一角色：将浮栅或电荷陷阱存储单元与 CMOS 逻辑电路单片集成在同一颗芯片上。在 40 nm 及以上节点，eFlash 是成熟、可靠且经过充分验证的方案 —— NXP、意法半导体、瑞萨、英飞凌等厂商出货的数十亿颗 MCU 均采用此方案。

然而，半导体行业正将逻辑工艺推进至 22 nm、16 nm、12 nm 乃至更先进节点，以获取功耗、性能和成本优势。嵌入式闪存**无法跟随**。浮栅存储单元需要厚隧穿氧化层、高编程电压（>10 V）以及专用高压晶体管，这些与先进逻辑 CMOS 工艺不兼容。行业共识是 **28 nm 是 eFlash 的实际缩放极限** —— 许多人认为由于掩膜数量和工艺复杂度，经济极限甚至更早到来。

这造成了一个技术断层：先进节点的 SoC 需要片上 NVM，但行业使用了 30 年的唯一 NVM 方案无法在这些节点上制造。**电阻式 RAM（ReRAM / RRAM）** —— 一种双端金属氧化物器件，通过电阻状态而非陷阱电荷来存储数据 —— 已成为首选替代方案。它可扩展至 12 nm 及以下，仅需在 CMOS 工艺中增加 2 层掩膜，并开辟了全新的应用维度：面向边缘 AI 的存内计算。

---

## 2. 具体问题与瓶颈证据

### 2.1 eFlash 无法缩放至 28 nm 以下

| 证据 | 详情 |
|------|------|
| 缩放壁垒 | 行业尚未找到将 NOR 闪存工艺缩小至 28 nm 以下的方法（[Semiconductor Engineering](https://semiengineering.com/embedded-flash-scaling-limits/)） |
| 根因 — 电荷陷阱 | 28 nm 以下的微缩挑战了闪存的基本电荷陷阱机制；氧化层变薄导致保持力和耐久性退化 |
| 根因 — 高电压 | eFlash 编程/擦除需要 >10 V，需要与 sub-28 nm CMOS 不兼容的厚氧化层高压晶体管 |
| 经济壁垒 | "许多人认为 28nm/22nm 将是 eFlash 的终点，不是因为可缩放性限制，而是因为经济壁垒"（[Semiconductor Engineering](https://semiengineering.com/embedded-flash-scaling-limits/)） |

### 2.2 eFlash 制造成本不可持续

将闪存嵌入逻辑工艺需要 **7-10 层额外光罩**，用于浮栅叠层、隧穿氧化层、高压晶体管和隔离结构。这使**晶圆成本增加 >25%**，并将制造周期延长数周。随着逻辑节点的推进，基线 CMOS 与 eFlash 使能的 CMOS 之间的掩膜数量差距进一步扩大，使 eFlash 在成本敏感的 IoT 和消费级 MCU 上日益不可行。

### 2.3 eFlash 的性能局限

| 指标 | eFlash (NOR) | 局限性 |
|------|-------------|--------|
| 编程速度 | ~1-10 us/字 | 比逻辑时钟慢数个数量级 |
| 擦除 | 扇区擦除，~100 ms | 无法擦除单个比特或字节 |
| 耐久性 | ~10,000-100,000 次 P/E 循环 | 限制 OTA 更新频率 |
| 读取延迟 | ~20-50 ns | 可接受但不随工艺微缩改善 |
| 写入粒度 | 仅页/扇区级 | 无逐比特写入能力 |

### 2.4 新兴应用的需求超越了单纯存储

边缘 AI 加速器和神经形态芯片需要能够参与计算的存储器 —— 在存储阵列内直接执行乘累加（MAC）运算，以避免在存储器与计算单元之间搬运数据的能量开销。eFlash 纯粹为代码存储设计，不具备模拟计算能力，无法服务于这一新兴工作负载。

---

## 3. 架构对比：eFlash vs. ReRAM

### 嵌入式闪存（原始方案 — 28 nm+）

```
+-------------------------------------------------------------------+
|                     SoC 芯片 (40 nm / 28 nm)                        |
|                                                                    |
|   +--------------------+     +------------------------------+      |
|   |   逻辑域            |     |     eFlash 域                 |      |
|   |   (基线 CMOS)       |     |     (额外 7-10 层掩膜)         |      |
|   |                    |     |                               |      |
|   |   CPU 核心          |     |   +------------------------+  |      |
|   |   外设             |     |   | 浮栅 NOR 阵列            |  |      |
|   |   SRAM             |     |   | 隧穿氧化层 ~9-10 nm      |  |      |
|   |   I/O              |     |   | 控制栅叠层               |  |      |
|   |                    |     |   | 仅支持扇区擦除            |  |      |
|   +--------------------+     |   +------------------------+  |      |
|          |                   |              |                 |      |
|          |                   |   +------------------------+  |      |
|   +------+------+           |   |  高压晶体管 (>10 V)      |  |      |
|   | 低压晶体管    |           |   |  厚栅氧化层              |  |      |
|   | (1.0-1.8 V)  |           |   |  电荷泵                  |  |      |
|   +--------------+           |   |  电平转换器              |  |      |
|                              |   +------------------------+  |      |
|                              +------------------------------+      |
|                                                                    |
|   工艺：基线 CMOS + 7-10 层额外掩膜                                  |
|   成本增加：>25% 晶圆成本                                            |
|   缩放极限：28 nm（实际），40 nm（许多设计）                            |
|   耐久性：10K-100K 次 P/E 循环                                      |
+-------------------------------------------------------------------+
```

### ReRAM / RRAM（演进方案 — 可扩展至 12 nm+）

```
+-------------------------------------------------------------------+
|                  SoC 芯片 (22 nm / 16 nm / 12 nm)                   |
|                                                                    |
|   +--------------------+     +------------------------------+      |
|   |   逻辑域            |     |     ReRAM 域                  |      |
|   |   (基线 CMOS)       |     |     (仅 2 层额外掩膜)          |      |
|   |                    |     |                               |      |
|   |   CPU 核心          |     |   +------------------------+  |      |
|   |   外设             |     |   | ReRAM 阵列 (BEOL)        |  |      |
|   |   SRAM             |     |   | 金属-氧化物-金属叠层       |  |      |
|   |   I/O              |     |   | (如 TaOx/HfO2)           |  |      |
|   |   AI 加速器         |     |   | 在金属层间集成             |  |      |
|   |                    |     |   | 支持逐比特写入             |  |      |
|   +--------------------+     |   +------------------------+  |      |
|          |                   |              |                 |      |
|          |                   |   +------------------------+  |      |
|   +------+------+           |   |  访问晶体管 (1T)          |  |      |
|   | 标准 CMOS     |           |   |  标准 CMOS 电压           |  |      |
|   | 晶体管        |           |   |  无需高压器件             |  |      |
|   +--------------+           |   |  无需电荷泵               |  |      |
|                              |   +------------------------+  |      |
|                              +------------------------------+      |
|                                                                    |
|   工艺：基线 CMOS + 2 层额外掩膜（BEOL 集成）                         |
|   成本增加：<10% 晶圆成本                                            |
|   可扩展性：12 nm 已验证（台积电），7 nm / 6 nm 在研                   |
|   耐久性：100K-1M+ 循环（比 eFlash 好 10x-100x）                    |
|   额外能力：面向边缘 AI 的模拟存内计算                                 |
+-------------------------------------------------------------------+
```

### ReRAM 单元结构（1T1R）

```
         位线 (BL)
            |
    +-------+-------+
    |   顶电极       |   (TiN)
    |   +-----------+ |
    |   | 开关层     | |   金属氧化物 (HfO2, TaOx 或双层结构)
    |   |           | |   通过氧空位导电丝的形成/断裂调制电阻
    |   +-----------+ |
    |   底电极       |   (TiN / Ti / Ta)
    +-------+-------+
            |
    +-------+-------+
    |   访问晶体管    |
    |   (1T)         |   标准 CMOS NFET
    +-------+-------+
            |
        源线 (SL)

    SET:   形成导电丝    -> 低阻态 (LRS)
    RESET: 断裂导电丝    -> 高阻态 (HRS)
    READ:  感测电阻比    -> LRS / HRS = 比特值
```

### 关键架构差异

| 特征 | eFlash (NOR) | ReRAM (RRAM) |
|------|-------------|--------------|
| 存储机制 | 浮栅上的陷阱电荷 | 金属氧化物导电丝的电阻状态 |
| 单元结构 | 1T（浮栅）或 2T（分栅） | 1T1R（晶体管 + 电阻器） |
| 集成位置 | FEOL（前道工序，晶体管层） | BEOL（后道工序，金属层间） |
| 额外掩膜 | 7-10 层 | 2 层 |
| 晶圆成本增加 | >25% | <10% |
| 需要高压晶体管 | 是（编程/擦除需 >10 V） | 否（在 CMOS 电压下工作） |
| 缩放极限 | 28 nm（实际） | 12 nm 已验证，7/6 nm 在研 |
| 写入粒度 | 扇区擦除后页编程 | 无需擦除的逐比特写入 |
| 模拟存内计算潜力 | 无 | 原生支持（模拟电阻级别） |

---

## 4. ReRAM 能解决什么 — 不能解决什么

### 能解决

- **先进节点 eNVM**：ReRAM 在 22 nm、16 nm 和 12 nm 节点提供非易失性存储，而 eFlash 在这些节点根本无法存在，扫清了 MCU 和 IoT SoC 设计向先进节点迁移的障碍。
- **显著成本降低**：2 层掩膜的 BEOL 工艺仅增加 <10% 晶圆成本，相比 eFlash 的 >25%，对利润率紧张的高量产消费级和 IoT 芯片尤为关键。
- **更好的耐久性**：ReRAM 提供 100K-1M+ 次编程/擦除循环，是 eFlash 的 10x-100x，支持更频繁的 OTA 固件更新和数据日志记录。
- **逐比特写入**：与需要先擦除扇区才能编程的 eFlash 不同，ReRAM 支持逐比特写入操作 —— 提升写入性能并减少磨损。
- **边缘 AI 存内计算**：ReRAM 的模拟电阻状态可在存储阵列内直接执行乘累加运算，有望消除边缘推理中的数据搬运瓶颈。
- **汽车级就绪**：台积电与英飞凌的 AURIX TC4x 系列在 28 nm 节点展示了汽车级 ReRAM 并通过 AEC-Q100 认证；Weebit 也在推进同等认证。

### 不能解决

- **替代 SRAM/DRAM 的耐久性**：ReRAM 的 10^5-10^6 次循环耐久性虽远好于 eFlash，但远低于替代 SRAM 或 DRAM 所需的 >10^15 次循环。
- **与 SRAM 等速写入**：ReRAM 写入延迟（~50-200 ns）虽快于 eFlash，但仍比 SRAM（~0.5 ns）慢约 100 倍，限制了其作为通用高速缓存的使用。
- **可变性与良率**：基于导电丝的开关行为具有随机性；周期间和器件间的可变性仍是活跃的工程研究方向，对多级单元（MLC）操作尤为突出。
- **极端温度下的保持力**：虽然台积电已在 12 nm RRAM 上验证了 105°C 下 10 年保持力，但在最小节点上实现汽车 Grade-0（150°C）保持力仍在认证中。
- **存内计算成熟度**：ReRAM 存内计算已在学术原型和早期硅片（ISSCC 2024）上得到验证，但具备完整软件栈的量产 CIM 加速器尚未大规模出货。

---

## 5. 定量对比

| 指标 | eFlash (NOR, 28 nm+) | ReRAM/RRAM（演进方案） | 差异 |
|------|----------------------|----------------------|------|
| 最小工艺节点 | 28 nm（实际极限） | 12 nm（台积电已验证） | 可再缩放 2+ 个节点 |
| 额外光罩数 | 7-10 层 | 2 层 | 减少 5-8 层掩膜 |
| 晶圆成本增加 | >25% | <10% | 节省 >15 个百分点 |
| 编程/擦除耐久性 | 10K-100K 次循环 | 100K-1M+ 次循环 | 好 10x-100x |
| 数据保持力 | 10+ 年 @ 85°C | 10+ 年 @ 105°C | 更高温度容忍度 |
| 写入粒度 | 扇区擦除 + 页编程 | 逐比特写入 | 结构性优势 |
| 读取延迟 | 20-50 ns | 7-20 ns | 快 2x-3x |
| 写入延迟 | 1-10 us/字 | 50-200 ns | 快 10x-100x |
| 写入操作电压 | >10 V（需电荷泵） | 1.2-3.0 V（CMOS 电压） | 无需高压电路 |
| 集成位置 | FEOL（晶体管层） | BEOL（金属层） | 对逻辑无侵入 |
| 单元结构 | 1T 浮栅 / 2T 分栅 | 1T1R | 更简单 |
| 模拟存内计算能力 | 无 | 原生支持（多级电阻） | 全新能力 |
| 代工厂支持（2025） | 台积电、GF、联电、三星（28nm+） | 台积电 (40/28/22/12nm)、GF (22nm)、DB HiTek (130nm)、SkyWater (130nm) | 快速扩展中 |
| 量产客户（2025） | 数千家（成熟生态） | Nordic、英飞凌、新唐、onsemi、博通（量产爬坡中） | 早期但加速中 |

---

## 6. 生态系统与导入时间线

### 代工厂 ReRAM 平台（截至 2025 年中）

| 代工厂 | 节点 | 状态 | 主要客户 |
|--------|------|------|----------|
| 台积电 | 40 nm | 量产（自 ~2022 年） | 意法半导体、新唐 |
| 台积电 | 28 nm | 量产 | 英飞凌 (AURIX TC4x) |
| 台积电 | 22 nm ULL | 量产 / 风险生产 | Nordic Semiconductor (nRF54L15) |
| 台积电 | 12 nm | 消费级风险生产（2024） | NDA 保护 |
| 台积电 | 7 nm / 6 nm | 研发中 | — |
| GlobalFoundries | 22FDX | 认证中 | Weebit IP 被授权方 |
| DB HiTek | 130 nm BCD | 已认证（2025） | Weebit IP 被授权方 |
| SkyWater | 130 nm | 通过 Efabless chipIgnite 提供 | 原型 / 学术 |
| onsemi (Treo) | 待定 | 已授权 Weebit ReRAM IP（2025年1月） | 汽车 / 工业 |

### 关键产品里程碑

| 年份 | 里程碑 |
|------|--------|
| 2022 | 台积电 40/28/22 nm RRAM 量产；英飞凌宣布采用 28 nm RRAM 的 AURIX TC4x |
| 2023 | Nordic nRF54L15（22 nm，1.5 MB ReRAM）开始送样；新唐出货 ReRAM MCU |
| 2024 | 台积电在 12 nm 验证 RRAM（最小 CMOS 集成节点）；ISSCC 2024 展示 22 nm 16 Mb ReRAM CIM 宏单元达 31.2 TFLOPS/W；Weebit ICCAD 演讲；TechInsights 确认 Nordic nRF54L15 RRAM 工艺 |
| 2025 | onsemi 为 Treo 平台授权 Weebit ReRAM；DB HiTek 在 130 nm 认证 Weebit ReRAM；英飞凌 AURIX TC4x 28 nm RRAM 量产爬坡；eNVM 市场预测从 2024 年 $0.14B 增长至 2030 年 $3.3B（Yole） |
| 2025+ | 台积电路线图：7 nm / 6 nm RRAM 在研；NXP 16 nm FinFET MRAM 送样；MCU 从 eFlash 向 eNVM 的广泛迁移 |

---

## 7. 一词判决

**替代** —— ReRAM 是嵌入式闪存的直接且成本更优的替代方案，同时解锁了先进节点集成和存内计算能力，使其成为一次代际平台转变，而非渐进式升级。

---

## 8. 开放问题

1. **12 nm 及以下的良率**：台积电 12 nm RRAM 于 2024 年进入风险生产，但量产良率数据和该节点的汽车级认证尚未公开。导电丝可变性能否在 sub-20 nm 特征尺寸下得到控制？
2. **MRAM 与 ReRAM 的分工**：NXP 为汽车 MCU 推进 16 nm FinFET MRAM，而英飞凌选择了 28 nm RRAM。行业将趋同于一种 eNVM 技术，还是 MRAM 和 ReRAM 将根据应用场景共存（MRAM 面向高耐久性场景，ReRAM 面向成本/密度场景）？
3. **CIM 量产时间线**：ISSCC 2024 的 ReRAM CIM 宏单元（31.2 TFLOPS/W）是研究型演示。首颗搭载 ReRAM 存内计算的量产边缘 AI 芯片何时出货？配套软件栈将是什么？
4. **多级单元（MLC）可靠性**：MLC ReRAM（每单元存储 2+ 比特）将大幅提升密度，但需要更紧凑的电阻分布。MLC ReRAM 是否已准备好量产，还是单级单元（SLC）将在可预见的未来保持标准？
5. **eFlash 存量设计**：数十亿颗 40 nm 和 28 nm MCU 设计目前使用 eFlash。代工厂将继续支持 eFlash 工艺多久？现有设计的迁移成本是多少？
6. **意法半导体的 PCM 路径**：意法半导体在其 STM32 路线图中押注嵌入式 PCM（ePCM）而非 ReRAM（18 nm FDSOI，与三星代工合作）。ePCM 能否保持竞争力，还是 ReRAM 更广泛的代工厂生态将使其边缘化？

---

## 9. 参考资料

1. Weebit Nano, "Embedded NVM for a New Era," ICCAD 2024 演讲, 2024年12月. [PDF](https://www.weebit-nano.com/wp-content/uploads/2024/12/Weebit-ICCAD-2024-Embedded-NVM-RRAM-ReRAM-technology-IP-replace-flash-memory-semiconductor-companies.pdf)
2. Weebit Nano, "ReRAM: Emerging as the New Embedded NVM Standard," FMS 2025. [PDF](https://www.weebit-nano.com/wp-content/uploads/2025/09/FMS25_Weebit-ReRAM-in-commercial-fabs-for-various-AI-architectures-for-edge-applications-RRAM-IP-technology_W.pdf)
3. MRS Communications, "Progress of emerging non-volatile memory technologies in industry," 2024年11月. [Springer](https://link.springer.com/article/10.1557/s43579-024-00660-2)
4. TechInsights, "Embedded & Emerging Memory Technology Roadmap," 2024年5月. [Link](https://www.techinsights.com/blog/embedded-emerging-memory-technology-roadmap-may-2024)
5. TechInsights, "Advanced TSMC 22ULL Embedded RRAM Chip Unveiled"（Nordic nRF54L15 分析）. [Link](https://www.techinsights.com/blog/advanced-tsmc-22ull-embedded-rram-chip-unveiled)
6. 台积电, "Logic-Compatible RRAM Supports Firmware, Data Storage and Security Memory." [Link](https://www.tsmc.com/english/dedicatedFoundry/technology/platform_IoT_tech_NVM)
7. 台积电, "Comprehensive Ultra-low Power Technology Platform (22ULL / 12FFC+ ULL)." [Link](https://www.tsmc.com/english/dedicatedFoundry/technology/platform_IoT_tech_22ULL_12FFCplus_ULL)
8. 英飞凌 & 台积电, "Infineon and TSMC to Introduce RRAM Technology for Automotive AURIX TC4x Product Family," 2022年11月. [Link](https://www.infineon.com/market-news/2022/infatv202211-031)
9. NXP & 台积电, "NXP and TSMC to Deliver Industry's First Automotive 16 nm FinFET Embedded MRAM," 2024. [Link](https://www.nxp.com/company/about-nxp/newsroom/NW-NXP-AND-TSMC-DELIVER-FIRST16NM-FINFET-MRAM)
10. Yole Group, "With early adopters such as STMicroelectronics and NXP, emerging NVMs reaffirm their potential," 2024. [Link](https://www.yolegroup.com/strategy-insights/with-early-adopters-such-as-stmicroelectronics-and-nxp-emerging-nvms-reaffirm-their-potential/)
11. Yole Group, "Emerging Non-Volatile Memory 2025." [Link](https://www.yolegroup.com/product/report/emerging-non-volatile-memory-2025/)
12. Semiconductor Engineering, "Embedded Flash Scaling Limits." [Link](https://semiengineering.com/embedded-flash-scaling-limits/)
13. Semiconductor Engineering, "ReRAM Seeks To Replace NOR." [Link](https://semiengineering.com/reram-seeks-to-replace-nor/)
14. Embedded.com, "Understanding the emerging contenders for the Flash memory crown." [Link](https://www.embedded.com/understanding-the-emerging-contenders-for-the-flash-memory-crown/)
15. Weebit Nano, "ReRAM: The Automotive NVM Solution," FMS 2024. [PDF](https://files.futurememorystorage.com/proceedings/2024/20240807_OMEM-201-1_Regev.pdf)
16. Weebit Nano, "Weebit Nano licenses its ReRAM technology to onsemi," 2025年1月. [Link](https://www.storagenewsletter.com/2025/01/02/weebit-nano-licenses-its-reram-technology-to-onsemi-tier-1-semiconductor-supplier/)
17. Nature, "A compute-in-memory chip based on resistive random-access memory," 2022. [Link](https://www.nature.com/articles/s41586-022-04992-8)
18. Nature, "A mixed-precision memristor and SRAM compute-in-memory AI processor," 2025. [Link](https://www.nature.com/articles/s41586-025-08639-2)
19. SemiWiki, "Weebit Nano is at the Epicenter of the ReRAM Revolution." [Link](https://semiwiki.com/ip/weebit-nano/348406-weebit-nano-is-at-the-epicenter-of-the-reram-revolution/)
20. SemiWiki, "Weebit Nano Moves into the Mainstream with Customer Adoption." [Link](https://semiwiki.com/ip/weebit-nano/360158-weebit-nano-moves-into-the-mainstream-with-customer-adoption/)

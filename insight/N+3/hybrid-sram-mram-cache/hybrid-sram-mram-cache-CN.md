# 混合 SRAM-MRAM 缓存：从纯 SRAM 层级到非易失异构缓存

> 本文对比原始纯 SRAM 缓存层级（L1–L3 全部为 SRAM，先进节点下高漏电、大面积）与演进后的混合 SRAM-MRAM 缓存架构（L1 保留 SRAM，L2/L3/LLC 采用 MRAM，非易失优势，漏电大幅降低）。综述来源涵盖学术研究（AIP Advances、IEEE、imec）、产业研发（imec SOT-MRAM、三星 STT-MRAM）及架构探索，时间跨度 2022–2026。

## 1. 范围与方法

**领域定义。** 高性能处理器（服务器、HPC、移动 SoC）的片上缓存层级设计——聚焦从同构全 SRAM 缓存层级向异构架构的转变，即根据各缓存级的访问模式需求，将不同存储技术（SRAM、STT-MRAM、SOT-MRAM）分配至不同缓存层级。

**"原始"与"演进"的含义。** *原始*方案为纯 SRAM 缓存层级：L1（32–64 KB）、L2（256 KB–1 MB）、L3/LLC（4–64 MB）均采用 6T-SRAM 单元，特征为快速访问（L1 亚纳秒）、高漏电功耗（尤其在 sub-5nm 节点）、大单元面积（6T SRAM 每比特 6 个晶体管）、断电数据完全丢失。*演进*方案为混合 SRAM-MRAM 缓存：延迟敏感的 L1 保留 SRAM，L2/L3/LLC 级别替换为 STT-MRAM 或 SOT-MRAM，提供非易失数据保持、近零待机漏电、更高密度（更小单元面积），并使能全新系统能力（即时开机、无需检查点的崩溃恢复、常关计算）。

**资料来源。** 12 项主要来源：4 篇学术论文（AIP Advances、IEEE JESTPE、IEEE TNANO、ResearchGate），3 项研究机构出版物（imec SOT-MRAM），2 项架构研究（单片 3D 混合、增益单元基准测试），2 项产业路线图（Promwad 自适应存储器、PatSnap SOT-MRAM 路线图），1 项综述（非易失处理器设计）。来源类型涵盖同行评审期刊、会议论文、研究机构技术文章及产业分析。

## 2. 问题背景

**系统需要做什么。** 为运行多样化负载——服务器（云 AI 推理、数据库）、HPC（科学仿真、大模型训练）、移动（常在 AI、间歇计算）——的处理器提供多级片上缓存。缓存须提供亚纳秒 L1 访问、个位数纳秒 L2/L3 访问、千字节至数十兆字节容量，并在随每一制程节点递减的紧凑功耗与面积预算内运行。

**为何该领域变得困难。** 在 sub-5nm 制程节点，SRAM 面临"三重缩放墙"：（1）单元面积停止缩小——TSMC N3 SRAM 位单元（0.0199 um²）仅比 N5（0.021 um²）小约 5%，N3E 变体相比 N5 零缩放；（2）漏电功耗复合增长——亚阈值、栅极、GIDL 和结漏电机制在 3nm 以下同时成为主要贡献者，单一缓解手段（高阈值电压晶体管）已不充分；（3）缓存占据越来越大的裸片比例——随逻辑缩放但 SRAM 不缩放，缓存在现代服务器 CPU 和 AI 加速器上消耗 50–70% 的裸片面积，直接推高每 mm² 成本。

**为何原始方案不再满足需求。** 在 3nm 制程上，64 MB 的纯 SRAM LLC 即使空闲也消耗可观的漏电功耗——预计仅缓存部分即达 2–5 W。对于目标全天续航的移动 SoC，该待机漏电不可接受。在 HPC 节点中，50–70% 裸片面积为缓存，SRAM 大面积的机会成本巨大：用更高密度技术替换 LLC SRAM 可释放 20–30% 裸片面积用于额外计算或存储容量。此外，SRAM 的易失性意味着任何电力中断（崩溃、热节流、有意功率门控）都会销毁所有缓存状态，需从 DRAM/存储进行昂贵的重新预热。

## 3. 具体问题与瓶颈证据

1. **SRAM 面积缩放在 3nm 停滞** — TSMC N3 SRAM 位单元为 0.0199 um²，N5 为 0.021 um²，仅缩小约 5%。N3E 变体零缩放（0.021 um²）。同时逻辑标准单元面积每代缩放 1.3×。此分化意味着缓存在每一新节点占据越来越大的裸片比例 [TSMC N3 SRAM 分析；WikiChip IEDM 2022]。

2. **sub-3nm 多机制漏电** — 3nm 以下，亚阈值漏电、栅极漏电、GIDL 和结电流同时成为主要漏电源。高阈值电压晶体管仅解决亚阈值漏电，遗留 40–60% 的总漏电未缓解。3nm 下 64 MB SRAM LLC 预计在典型工作温度下漏电 2–5 W [PatSnap SRAM 漏电分析]。

3. **STT-MRAM 写延迟限制 L1/L2 使用** — STT-MRAM 写延迟通常为 5–10 ns，而 SRAM 低于 1 ns。这使 STT-MRAM 不适用于 L1 缓存（需亚纳秒读写），对 L2 也勉强（需 1–3 ns 写入）。仅 L3/LLC（写延迟容忍度 5–20 ns）能承受 STT-MRAM 的写入代价 [imec MRAM 技术综述]。

4. **STT-MRAM 写耐久性有限** — STT-MRAM 写电流通过薄 MgO 隧道势垒，造成累积应力，限制耐久性约 10^9–10^12 次。对于高写入率的 L2 缓存，此耐久性在 5–10 年产品寿命内可能不足 [IEEE MRAM 耐久性研究；nature npj Spintronics]。

5. **SOT-MRAM 密度不及 STT-MRAM** — SOT-MRAM 的三端单元结构（读写路径分离）面积比 STT-MRAM 的两端单元大约 50%。在面积敏感的 LLC 应用中，这部分抵消了 SOT-MRAM 在速度和耐久性方面的优势 [SOT vs STT MRAM 对比]。

### 瓶颈证据

| 场景 | SRAM（原始） | MRAM（目标） | 差距/收益 | 来源 |
|---|---|---|---|---|
| 5nm 位单元面积 | 0.021 um²（6T-SRAM） | ~0.009 um²（STT-MRAM，为 SRAM 的 43%） | 2.3× 更密 | [imec 5nm 研究] |
| 待机漏电（64 MB LLC） | 2–5 W | ~0 W（非易失） | 近零待机 | [PatSnap 漏电] |
| 写延迟（L3/LLC） | <1 ns | 5–10 ns（STT），<1 ns（SOT） | STT：5–10× 慢；SOT：相当 | [imec；EDN] |
| 写耐久性 | >10^16（无限） | 10^9–10^12（STT），>10^15（SOT） | STT：低数个数量级 | [imec；npj Spintronics] |
| 每比特写能耗 | ~1 fJ（SRAM） | ~100 fJ（STT），<100 fJ（SOT） | MRAM 单次写入更高；含漏电总系统更低 | [imec SOT-MRAM] |
| 3nm 面积缩放 | 停滞（N3E vs N5 为 0%） | 随 MTJ 直径缩放，BEOL 兼容 | MRAM 独立缩放 | [TSMC N3；imec] |
| SRAM 缓存裸片占比 | 50–70%（服务器 CPU） | 30–40%（MRAM LLC） | 释放 20–30% 面积 | [WikiChip IEDM 2022] |

## 4. 架构：原始 vs 演进

**原始 — 纯 SRAM 缓存层级**

```
    +--------------------------------------------------+
    |                  处理器核心                        |
    +--------------------------------------------------+
         |                    |                    |
    +----------+        +----------+         +-----------+
    |  L1 I$   |        |  L1 D$   |         |  L1 TLB   |
    |  SRAM    |        |  SRAM    |         |  SRAM     |
    |  32-64KB |        |  32-64KB |         |           |
    |  <1ns    |        |  <1ns    |         |           |
    +----------+        +----------+         +-----------+
         |                    |
         +--------------------+
                   |
              +----------+
              |   L2 $   |
              |   SRAM   |
              | 256KB-1MB|
              |   1-3ns  |
              +----------+
                   |
              +-----------+
              |  L3 / LLC |
              |   SRAM    |
              |  4-64 MB  |
              |  5-20ns   |
              +-----------+
                   |
              +-----------+
              |   DRAM    |
              |  (片外)    |
              |  50-100ns |
              +-----------+

    所有层级：6T-SRAM
    待机漏电：2-5 W（3nm 下 64 MB LLC）
    数据保持：易失（断电丢失）
    面积：占裸片 50-70%（服务器 CPU）
```

*原始方案：所有缓存层级使用 6T-SRAM 单元。先进节点下高漏电、大裸片面积、断电数据完全丢失。*

**演进 — 混合 SRAM-MRAM 缓存层级**

```
    +--------------------------------------------------+
    |                  处理器核心                        |
    +--------------------------------------------------+
         |                    |                    |
    +----------+        +----------+         +-----------+
    |  L1 I$   |        |  L1 D$   |         |  L1 TLB   |
    |  SRAM    |        |  SRAM    |         |  SRAM     |
    |  32-64KB |        |  32-64KB |         |           |
    |  <1ns    |        |  <1ns    |         |           |
    +----------+        +----------+         +-----------+
         |                    |
         +--------------------+
                   |
             *+----------+*
             *|   L2 $   |*
             *| STT-MRAM |*
             *| 256KB-2MB|*
             *|  2-5ns   |*
             *+----------+*
                   |
             *+-----------+*
             *| L3 / LLC  |*
             *| SOT-MRAM  |*
             *|  4-64 MB  |*
             *|  3-10ns   |*
             *+-----------+*
                   |
              +-----------+
              |   DRAM    |
              |  (片外)    |
              |  50-100ns |
              +-----------+

    * = 新增/变更的元素
    L1：SRAM（延迟敏感，保持不变）
    L2：STT-MRAM（非易失，2.3× 更密，近零漏电）
    L3/LLC：SOT-MRAM（非易失，亚纳秒写入，>10^15 耐久性）
    待机漏电：~0 W（非易失，可功率门控）
    新增能力：即时开机、无需检查点的崩溃恢复、
              常关计算、零漏电待机
    面积：占裸片 30-40%（较纯 SRAM 释放 20-30%）
```

*演进方案：L1 保留 SRAM 以获亚纳秒延迟；L2 迁移至 STT-MRAM 以获密度与非易失性；L3/LLC 采用 SOT-MRAM 以获速度、耐久性与密度。非易失缓存使能即时开机、崩溃恢复和无数据损失的功率门控。新增/变更元素以 `*` 标记。*

## 5. 演进方案的优势与尚未解决的问题

### 优势

- **SRAM 面积缩放停滞** — STT-MRAM 位单元在 5nm 下仅占 SRAM 宏面积的 43.3%，使 L2/L3/LLC 密度提升 2.3×。对于 64 MB LLC，这意味着约 30% 的裸片面积节省，释放硅面积用于额外计算核心或在相同裸片预算下扩大缓存容量 [imec 5nm 可行性研究]。

- **多机制漏电** — MRAM 本质上非易失：待机漏电趋近于零，因为磁态保持无需功耗。混合缓存可在待机期间完全功率门控 L2/L3，消除 2–5 W 的 LLC 漏电代价。对于 512 KB L2 缓存，SOT-MRAM 和 STT-MRAM 相比 SRAM 分别实现 73.7% 和 67.8% 的 EADP（能量-面积-延迟积）提升 [AIP Advances 层级缓存研究；imec]。

- **易失数据丢失** — 非易失 L2/L3 缓存可跨电源周期保持数据，使能：（a）**即时开机** — 处理器从精确的缓存状态恢复，无需从 DRAM 重新预热；（b）**无需检查点的崩溃恢复** — 不需显式检查点即可承受电力中断；（c）**常关计算** — 系统仅在需要处理时上电，缓存状态零唤醒开销 [SOT-MRAM 常关计算研究]。

- **SOT-MRAM 解决 STT-MRAM 的写入限制** — SOT-MRAM 实现亚 1 ns 写延迟（1V 下演示 210 ps），开关能耗低于 100 fJ/bit，耐久性超过 10^15 次。由于写电流从不穿过隧道势垒，消除了读干扰，且不发生限制 STT-MRAM 耐久性的势垒退化 [imec SOT-MRAM 缩放；npj Spintronics 综述]。

- **BEOL 兼容制造** — MRAM 器件在后端金属层（BEOL）中制造，位于晶体管层之上。这使得单片 3D 集成成为可能——MRAM 缓存层直接堆叠于逻辑之上，缩短布线长度，无需晶圆键合即可实现更紧密集成 [IEEE 单片 3D SRAM/MRAM 研究]。

### 尚未解决的问题

- **SOT-MRAM 相比 STT-MRAM 的面积代价** — SOT-MRAM 三端结构面积比两端 STT-MRAM 大约 50%。虽然两者均密于 SRAM，但 SOT-MRAM 的面积劣势在 LLC 规模下部分抵消了密度优势。imec 对 BEOL 读选择器的研究目标是缩小 10–40% 位单元面积以弥合此差距，但量产就绪方案尚不可用 [imec SOT-MRAM BEOL 选择器]。

- **STT-MRAM 写能耗高于 SRAM** — STT-MRAM 每比特写能耗（~100 fJ）约为 SRAM（~1 fJ）的 100×。对于写密集负载，MRAM L2 的动态写能耗可能超过 SRAM 的读+写+漏电总和。需要负载感知的缓存管理（写缓冲、迁移策略）以维持能效优势 [IEEE 写能耗分析]。

- **SOT-MRAM 的保持-延迟权衡** — Imec 面向 LLC 的保持时间目标为 0.1–100 秒（非存储所需的年级别）。同时实现低写能耗和充足保持需要精心调谐磁性自由层。写错误率目标（10^-6）已在研究中达到，但尚未在量产规模展示 [imec LLC 保持目标]。

- **制造成熟度** — STT-MRAM 已在 22nm 和 14nm 的嵌入式应用（eNVM）中商用，但面向 5nm 及以下的高密度缓存优化 STT-MRAM 尚未量产。SOT-MRAM 仍处于 imec 和学术实验室的研究阶段。面向处理器缓存的量产可用性预计 STT-MRAM 为 2027–2029 年，SOT-MRAM 为 2029 年以后 [imec 路线图；EDN SOT-MRAM 现状]。

- **无标准设计方法学** — 混合 SRAM-MRAM 缓存设计的 EDA 工具和 PDK 尚不成熟。缓存控制器须处理非对称读/写延迟、耐久性感知的磨损均衡和保持感知的刷新——这些在标准缓存控制器 IP 中均不存在。

## 6. 对比表

| 维度 | 原始（纯 SRAM，3nm） | 演进（混合 SRAM-MRAM） | 提升 | 来源 |
|---|---|---|---|---|
| LLC 位单元面积 | 0.0199 um²（6T-SRAM，N3） | ~0.009 um²（STT-MRAM，5nm 等效） | 2.3× 更密 | [imec 5nm] |
| LLC 待机漏电（64 MB） | 2–5 W | ~0 W（非易失） | 近零 | [PatSnap；imec] |
| L2 EADP（512 KB） | 基线（SRAM） | −73.7%（SOT-MRAM），−67.8%（STT-MRAM） | 最高 73.7% | [AIP Advances] |
| LLC 写延迟 | <1 ns | 5–10 ns（STT），<1 ns（SOT，210 ps 演示） | STT：5–10× 慢；SOT：相当 | [imec；EDN] |
| LLC 写耐久性 | >10^16 | 10^9–10^12（STT），>10^15（SOT） | SOT：近无限；STT：有限 | [imec；npj Spintronics] |
| LLC 每比特写能耗 | ~1 fJ | ~100 fJ（STT），<100 fJ（SOT，记录值） | 单次写入更高；系统总功耗更低 | [imec SOT-MRAM] |
| 断电数据保持 | 丢失（易失） | 保持（非易失） | 即时开机、崩溃恢复 | [NV 处理器研究] |
| SRAM 缓存未命中代价 | 基线 | −50%（eDRAM 混合），−80%（MRAM 混合） | 最高降低 80% | [IEEE 混合缓存] |
| 系统性能（IPC） | 基线 | +15%（eDRAM），+23%（MRAM L3） | 最高 +23% | [IEEE 混合缓存] |
| 缓存裸片面积占比（服务器 CPU） | 50–70% | 30–40%（MRAM LLC） | 释放 20–30% | [WikiChip IEDM] |

## 7. 一词概括

**非易失**（Non-volatile）— 混合 SRAM-MRAM 缓存以非易失磁性存储器（STT-MRAM 和 SOT-MRAM）替换 L2/L3/LLC 的易失 SRAM，消除待机漏电，实现 2.3× 更高密度，并解锁纯 SRAM 层级根本不可能的系统级能力——即时开机恢复、无需检查点的崩溃恢复和常关计算。

## 8. 开放性问题与注意事项

- **能效交叉点依赖于负载** — 漏电与写能耗的权衡高度依赖负载：读主导的 LLC 负载强烈有利于 MRAM；写密集负载（如流式写入、数据库日志）可能出现净能耗增加。需要逐应用表征，而非一刀切替换。

- **LLC 保持时间需求因应用而异** — Imec 的 SOT-MRAM LLC 0.1–100 秒保持目标假设短寿命缓存数据。需要断电数据持久化的应用（检查点/恢复、休眠）需更长保持时间，增加写能耗和延迟。没有单一保持目标适用于所有场景。

- **3nm 及以下的工艺集成挑战** — 在 3nm 制程 BEOL 中制造 MRAM MTJ（磁性隧道结）器件需与先进逻辑加工兼容的热预算（BEOL 通常 <400°C）。SOT-MRAM 复杂的自由层叠层能否承受 sub-3nm BEOL 热约束，是活跃的研究课题。

- **非对称访问模式使缓存一致性复杂化** — 在具有混合缓存的多核系统中，MRAM 缓存级的非对称读/写延迟与一致性协议（MESI、MOESI）交互。基于目录的一致性协议可能需修改，以避免 MRAM 写延迟制约失效响应时的性能病态。

- **耐久性磨损均衡开销** — STT-MRAM 有限的耐久性（10^9–10^12）需要类似闪存的磨损均衡逻辑。这增加面积、延迟和设计复杂度。在 LLC 规模下计入磨损均衡开销后，总系统收益（密度 + 漏电）是否仍证明 MRAM 的合理性，尚未完全表征。

- **竞争替代方案** — 混合 SRAM-MRAM 并非解决 SRAM 缩放限制的唯一途径。增益单元存储器（GC）、eDRAM 和 BEOL 兼容电容型存储器也瞄准 LLC 替换。3nm 下增益单元设计显示读延迟低 29%，面积约为 SRAM 的 0.5×，制造比 MRAM 更简单。赢家可能因应用而异，而非通用。

- **非易失缓存的安全隐患** — 非易失缓存在断电后保留敏感数据（加密密钥、认证令牌、PII）。若无显式擦除，物理攻击者可从断电设备中提取缓存内容。当前架构方案中未涉及 MRAM 缓存的安全擦除机制。

## 9. 参考文献

1. **AIP Advances 层级缓存** — 作者, 2023. "Hierarchical cache configuration based on hybrid SOT- and STT-MRAM." AIP Advances 13, 025111. URL: https://pubs.aip.org/aip/adv/article/13/2/025111/2877240/Hierarchical-cache-configuration-based-on-hybrid
2. **Imec SOT-MRAM 面向 LLC** — Imec, 2023. "Novel SOT-MRAM architecture opens doors to high-density last-level cache memory applications." URL: https://www.imec-int.com/en/articles/novel-sot-mram-architecture-opens-doors-high-density-last-level-cache-memory-applications
3. **Imec SOT-MRAM LLC 规格** — Imec, 2024. "Bringing SOT-MRAM technology closer to last-level cache memory specifications." URL: https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications
4. **Imec SOT-MRAM 缩放** — SemiEngineering, 2025. "Cross-Node Scaling Potential of SOT-MRAM for Last-Level Caches (imec)." URL: https://semiengineering.com/cross-node-scaling-potential-of-sot-mram-for-last-level-caches-imec/
5. **Imec SST-MRAM 5nm 可行性** — Imec, 2022. "Imec demonstrates the feasibility of introducing SST-MRAM as a last-level cache at the 5nm technology node." URL: https://www.imec-int.com/en/articles/imec-demonstrates-the-feasibility-of-introducing-sst-mram-as-a-last-level-cache
6. **Imec SOT-MRAM 创纪录能耗** — Semiconductor Digest, 2024. "Imec's Extremely Scaled SOT-MRAM Devices Show Record Low Switching Energy and Virtually Unlimited Endurance." URL: https://www.semiconductor-digest.com/imecs-extremely-scaled-sot-mram-devices-show-record-low-switching-energy-and-virtually-unlimited-endurance/
7. **SOT-MRAM 常关计算** — ResearchGate, 2018. "Ultra-Fast and High-Reliability SOT-MRAM: From Cache Replacement to Normally-Off Computing." URL: https://www.researchgate.net/publication/327384190_Ultra-Fast_and_High-Reliability_SOT-MRAM_From_Cache_Replacement_to_Normally-Off_Computing
8. **单片 3D SRAM/MRAM** — IEEE JESTPE, 2021. "Monolithic 3D-Based SRAM/MRAM Hybrid Memory for an Energy-Efficient Unified L2 TLB-Cache Architecture." URL: https://ieeexplore.ieee.org/document/9334969/
9. **TSMC N3 SRAM 缩放** — Tom's Hardware, 2022. "TSMC's 3nm Node: No SRAM Scaling Implies More Expensive CPUs and GPUs." URL: https://www.tomshardware.com/news/no-sram-scaling-implies-on-more-expensive-cpus-and-gpus
10. **WikiChip IEDM 2022 SRAM** — WikiChip Fuse, 2022. "IEDM 2022: Did We Just Witness The Death Of SRAM?" URL: https://fuse.wikichip.org/news/7343/iedm-2022-did-we-just-witness-the-death-of-sram/
11. **EDN SOT-MRAM 现状** — EDN, 2024. "Memory lane: Where SOT-MRAM technology stands in 2024." URL: https://www.edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/
12. **npj Spintronics SOT-MRAM 综述** — Nature npj Spintronics, 2024. "Recent progress in spin-orbit torque magnetic random-access memory." URL: https://www.nature.com/articles/s44306-024-00044-1

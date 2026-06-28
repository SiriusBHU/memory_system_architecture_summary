# HBM4 与先进封装：从标准基础芯粒到逻辑增强的 Chiplet 集成

> 本文对比原始 HBM3/3E 架构（单芯片标准基础裸片、微凸块互连、固定功能）与演进后的 HBM4/4E 架构（3nm 定制逻辑基础裸片、混合键合路径、UCIe 小芯片集成、共封装光学）。综述来源涵盖产业路线图（TSMC、SK 海力士、三星、GUC）、会议论文（IEDM 2024、ISSCC 2026）及标准组织（JEDEC、UCIe 联盟），时间跨度 2024–2027。

## 1. 范围与方法

**领域定义。** 面向 AI/HPC 加速器的高带宽存储器封装架构——聚焦基础裸片（base die）从被动信号再分配层向主动逻辑增强计算基板的演进，以及使该转变成为可能的先进封装生态系统（SoIC 3D 堆叠、混合键合、UCIe chiplet 互连、共封装光学）。

**"原始"与"演进"的含义。** *原始*方案为 HBM3/3E 标准基础裸片：采用 12nm–22nm 制程的单芯片逻辑裸片，DRAM 层间使用微凸块互连（25–40 um 间距），提供固定 PHY/控制逻辑，不支持客户定制。*演进*方案为 HBM4/4E 逻辑增强基础裸片：采用 3nm 级（N3P）逻辑裸片，支持定制存内计算加速器、ECC 引擎和电源管理；面向 16 层以上堆叠提供混合键合路径；通过 UCIe chiplet 集成实现存储器解聚合；通过共封装光学实现系统级带宽扩展。

**资料来源。** 14 项主要来源：4 项产业路线图（TSMC HotChips/IEDM、GUC、SK 海力士、三星），3 项会议论文（IEDM 2024、ISSCC 2026、Hot Chips），3 项标准/规范（JEDEC HBM4、UCIe 3.0、CXL 3.1），2 篇分析报告（SemiAnalysis、TrendForce），2 项厂商技术披露（Micron、Broadcom CPO）。来源类型涵盖会议论文、厂商技术简报、标准文档及半导体分析刊物。

## 2. 问题背景

**系统需要做什么。** 为运行万亿参数模型训练与推理的 AI 加速器提供多 TB/s 级存储带宽，同时将功耗控制在单 GPU 封装 700–1000 W 包络线内。存储子系统须支持每堆叠 64+ GB 容量、亚纳秒访问粒度（用于注意力核函数），以及足够的灵活性，让客户（超大规模云厂商、AI 芯片设计商）能针对特定负载特征协同优化存储控制器逻辑。

**为何该领域变得困难。** AI 模型规模扩展（GPT-5 级、LLaMA-4-400B+）所需带宽增速超过单纯引脚速率提升所能提供的。HBM3E 已在 1024 位接口上以 9.8 Gbps 引脚速率运行，实现每堆叠约 1.2 TB/s。要达到 2–3+ TB/s 需将接口宽度翻倍（1024→2048 位，更多 TSV，更大中介层面积）或大幅提升引脚速率——两者均对热管理、功耗和制造良率构成压力。同时，基础裸片——历来仅为被动再分配层——浪费了宝贵的硅面积，该面积本可执行存内计算操作（数据缩减、ECC、地址重映射）以降低数据搬运能耗。

**为何原始方案不再满足需求。** HBM3E 的 12nm 标准基础裸片不提供客户定制：所有加速器厂商获得相同的 PHY/控制器，无法针对负载优化。微凸块间距（25–40 um）限制了垂直互连数量，制约更宽接口所需的 TSV 密度。在 12 层以上堆叠时，微凸块良率和热阻成为关键瓶颈：顶层裸片结温可比底层高出 50%。此外，单片中介层（CoWoS-S/L）面临光刻视场限制，无法满足下一代需要 2–4 个 HBM 堆叠加大面积 SoC 裸片的 GPU 封装需求。

## 3. 具体问题与瓶颈证据

1. **1024 位接口的带宽墙** — HBM3E 以 1024 位接口、9.8 Gbps 引脚速率实现每堆叠 1.2–1.33 TB/s。NVIDIA B200 需 8 TB/s 聚合带宽（6 堆叠 × 1.33 TB/s），存储 I/O 独占 GPU 总功耗约 45%。面向 16+ TB/s 聚合带宽的下一代加速器无法通过 HBM3E 在合理堆叠数内实现 [TSMC/GUC HBM4 披露]。

2. **基础裸片是浪费的硅面积** — HBM3E 基础裸片为 12nm 单芯片，仅处理 PHY 和最小控制逻辑，占用约 80 mm²，不执行任何应用层有用计算。每一瓦花费在数据经中介层从 DRAM 搬运至 SoC 上的功耗中，I/O 驱动器本身即耗散 0.5–1.0 pJ/bit——存内计算可部分消除此开销 [SemiAnalysis HBM 路线图]。

3. **12 层以上微凸块良率下降** — 当前 HBM3E 使用约 25 um 间距微凸块，8 层堆叠时凸块高度 14.5 um。12 层堆叠时，微凸块缺陷导致的累积良率损失接近 15–20%，推高每一合格堆叠的有效成本。16 层堆叠（HBM4 64 GB 所需）面临严峻的经济性挑战 [Onto Innovation 互连分析]。

4. **热阻随堆叠高度线性增长** — 每层微凸块增加约 0.15 K·mm²/W 热阻。12 层堆叠中，顶层 DRAM 裸片比底层高 15–20°C，需降额刷新时序并降低有效带宽。混合键合可降低每层热阻 22–47% [TrendForce HBM 热分析]。

5. **中介层光刻视场限制约束多裸片集成** — CoWoS-S 中介层受限于约 2 倍光刻视场（~1700 mm²）。下一代配备 4 个 HBM4 堆叠加大面积 SoC 裸片的 GPU 封装需 2500+ mm² 中介层面积，超出单一中介层极限，需采用 CoWoS-L（chiplet 桥接）或 SoIC 3D 替代方案 [TSMC 先进封装路线图]。

### 瓶颈证据

| 场景 | HBM3E（原始） | HBM4（目标） | 差距 | 来源 |
|---|---|---|---|---|
| 每堆叠带宽 | 1.2–1.33 TB/s | 2.0–3.3 TB/s | 1.5–2.5× 不足 | [JEDEC/GUC] |
| 接口宽度 | 1024 位，16 通道 | 2048 位，32 通道 | 需 2× TSV 数 | [JEDEC HBM4] |
| 基础裸片制程 | 12nm（固定逻辑） | 3nm（定制逻辑） | 4× 逻辑密度机会 | [TSMC/GUC] |
| 微凸块间距 | 25–40 um | 10 um（目标），6 um（研发） | 4–6× 密度差距 | [Onto Innovation] |
| 堆叠高度（实际上限） | 8–12 层 | 12–16 层（HBM4/4E） | 良率与热限制 | [TrendForce] |
| 每层热阻 | ~0.15 K·mm²/W（微凸块） | ~0.08 K·mm²/W（混合键合） | 需降低 47% | [热分析综述] |

## 4. 架构：原始 vs 演进

**原始 — HBM3/3E 标准基础裸片**

```
    +------------------------------------------+
    |        GPU / 加速器 SoC                   |
    +------------------------------------------+
         |              |              |
         | CoWoS-S 硅中介层 (2.5D)
         |              |              |
    +----------+   +----------+   +----------+
    | HBM3E    |   | HBM3E    |   | HBM3E    |
    | 堆叠     |   | 堆叠     |   | 堆叠     |
    |          |   |          |   |          |
    | 8-12 层  |   | 8-12 层  |   | 8-12 层  |
    | DRAM 裸片|   | DRAM 裸片|   | DRAM 裸片|
    |  (微凸块)|   |  (微凸块)|   |  (微凸块)|
    |          |   |          |   |          |
    | +------+ |   | +------+ |   | +------+ |
    | | 基础 | |   | | 基础 | |   | | 基础 | |
    | | 裸片 | |   | | 裸片 | |   | | 裸片 | |
    | | 12nm | |   | | 12nm | |   | | 12nm | |
    | | 固定 | |   | | 固定 | |   | | 固定 | |
    | | PHY  | |   | | PHY  | |   | | PHY  | |
    | +------+ |   | +------+ |   | +------+ |
    +----------+   +----------+   +----------+

    基础裸片：12nm，固定 PHY + 控制器，无定制能力
    互连：微凸块（25-40 µm 间距）
    接口：1024 位，16 通道，最高 9.8 Gbps/pin
    容量：最高 36 GB（12 层，24Gb 层）
```

*原始方案：单片 12nm 基础裸片提供固定 PHY/控制器逻辑；微凸块连接 DRAM 各层；不支持客户定制基础裸片功能。*

**演进 — HBM4/4E 逻辑增强基础裸片与先进封装**

```
    +------------------------------------------+
    |        GPU / 加速器 SoC                   |
    +-------+----------------------------------+
            |         |              |
            | UCIe    | CoWoS-L / SoIC (3D)
            | chiplet |              |
            | 桥接    |              |
    +-------+--+  +----------+  +----------+
    | 光引擎   |  | HBM4/4E  |  | HBM4/4E  |
    | (CPO)    |  | 堆叠     |  | 堆叠     |
    |          |  |          |  |          |
    +----------+  | 12-16 层 |  | 12-16 层 |
                  | DRAM 裸片|  | DRAM 裸片|
                  |  (微凸块 |  |  (微凸块 |
                  |  → 混合  |  |  → 混合  |
                  |   键合)  |  |   键合)  |
                  |          |  |          |
                  |*+------+*|  |*+------+*|
                  |*| 基础 |*|  |*| 基础 |*|
                  |*| 裸片 |*|  |*| 裸片 |*|
                  |*| 3nm  |*|  |*| 3nm  |*|
                  |*| 定制 |*|  |*| 定制 |*|
                  |*| 逻辑 |*|  |*| 逻辑 |*|
                  |*| +ECC |*|  |*| +NDP |*|
                  |*| +PMU |*|  |*| +PMU |*|
                  |*+------+*|  |*+------+*|
                  +----------+  +----------+

    * = 新增/变更的元素
    基础裸片：3nm (N3P)，定制逻辑（ECC, NDP, PMU），按客户定制
    互连：微凸块 (10 µm) → 混合键合路径 (HBM4E/5)
    接口：2048 位，32 通道，6.4-12.8 Gbps/pin
    UCIe 3.0：chiplet 间互连 @ 48-64 GT/s
    CPO：光学 I/O 用于横向扩展带宽
    容量：最高 64 GB（16 层，32Gb 层）
```

*演进方案：3nm 定制基础裸片集成应用特定逻辑（ECC、近数据处理、电源管理）；从微凸块向混合键合过渡；UCIe chiplet 桥接实现解聚合存储；共封装光学实现系统级互连。新增/变更元素以 `*` 标记。*

## 5. 演进方案的优势与尚未解决的问题

### 优势

- **带宽墙** — HBM4 的 2048 位接口将数据通路翻倍，实现每堆叠 2.0–3.3 TB/s，相比 HBM3E 的 1.2–1.33 TB/s 提升 1.5–2.5×。在相近或更低引脚速率下，每比特 I/O 功耗降低约 40% [TSMC/GUC HBM4 披露；Micron HBM4 规格]。

- **基础裸片利用率** — 3nm 逻辑增强基础裸片将被动再分配层转变为主动计算层。客户特定加速器（稀疏注意力引擎、数据缩减单元、ECC 卸载）可消除存储受限 AI 负载中 30–50% 的往返数据搬运。TSMC 的 C-HBM4E 展示了 N3P 基础裸片将工作电压从 0.8V 降至 0.75V，能效较 12nm 基础裸片翻倍 [TSMC C-HBM4E N3P 披露]。

- **高堆叠微凸块良率** — 近期 HBM4 采用更细间距微凸块（~10 um，研发中推进至 6 um），改善良率。对于 16 层以上的 HBM4E/HBM5，混合键合完全消除凸块缺陷，热阻降低 22–47%，堆叠高度减少 >15%，使 20+ 层堆叠成为可能 [TrendForce 混合键合分析；Onto Innovation]。

- **中介层光刻视场限制** — TSMC SoIC 提供真正的 3D 芯片叠芯片方案，替代 2.5D 中介层。UCIe 3.0（48–64 GT/s）使基于 chiplet 的封装得以用多块较小中介层瓦片替代单片中介层，并将存储器解聚合延伸至封装边界以外 [UCIe 联盟 3.0 规范；TSMC IEDM 2024 SoIC]。

- **系统级带宽** — NVIDIA（COUPE）和 Broadcom（Tomahawk 6）的共封装光学在 GPU 封装上或其附近嵌入光引擎，实现每通道 200 Gbps 的横向扩展网络，消除电气 I/O 瓶颈。NVIDIA 在 ISSCC 2026 上展示了 32 Gbps/波长、8 波长 DWDM 方案 [ISSCC 2026 CPO 论文；SemiAnalysis CPO 分析]。

### 尚未解决的问题

- **定制基础裸片 NRE 成本** — 3nm 定制基础裸片每次流片需 1 亿美元以上的 NRE 费用。仅超大规模厂商（Google、Microsoft、Meta、Amazon）和顶级 GPU 厂商（NVIDIA、AMD）能分摊此成本；其余业界只能使用存储厂商提供的"标准增强版"基础裸片变体，定制空间有限 [SemiAnalysis HBM 路线图]。

- **HBM4 不向后兼容** — HBM4 的 2048 位接口与 HBM3/3E 控制器不兼容，需重新设计完整的存储子系统。这增加了采纳风险并延长新加速器的上市周期 [JEDEC HBM4 规范]。

- **混合键合尚未就绪** — HBM4（2025–2026）仍将使用微凸块；混合键合最早预计用于 HBM4E（2027–2028），更可能用于 HBM5。量产级良率、吞吐量和晶圆对准精度仍是挑战 [SemiEngineering HBM4 微凸块分析]。

- **UCIe chiplet 生态尚不成熟** — UCIe 3.0 于 2025 年 8 月发布，但基于 UCIe 实现存储器解聚合的商用 chiplet 产品预计 2027–2028 年才会出现。跨厂商互操作性测试仍处于早期阶段 [UCIe 联盟路线图]。

- **即便使用混合键合热限制仍在** — 16 层堆叠配合 3nm 基础裸片产生的可观热量，总堆叠热预算受封装级散热方案约束。需液冷或先进热界面材料，增加系统成本和复杂度。

## 6. 对比表

| 维度 | 原始（HBM3E，12nm 基础裸片） | 演进（HBM4/4E，3nm 基础裸片） | 提升 | 来源 |
|---|---|---|---|---|
| 每堆叠带宽 | 1.2–1.33 TB/s | 2.0–3.3 TB/s | +1.5–2.5× | [JEDEC/GUC] |
| 接口宽度 | 1024 位，16 通道 | 2048 位，32 通道 | 2× | [JEDEC HBM4] |
| 引脚速率 | 9.2–9.8 Gbps | 6.4–12.8 Gbps（三星演示达 13 Gbps） | 更宽范围，更高峰值 | [Samsung/GUC] |
| 基础裸片制程 | 12nm，固定逻辑 | 3nm (N3P)，定制逻辑 | ~4× 逻辑密度 | [TSMC/GUC] |
| 每比特功耗 | ~3.9 pJ/bit | ~2.3 pJ/bit | −40% | [Micron HBM4] |
| 核心电压 | 1.1 V | 1.05 V（基础裸片：N3P 下 0.75 V） | 核心 −5%，基础裸片 −6% | [TSMC C-HBM4E] |
| 每堆叠最大容量 | 36 GB（12 层，24Gb） | 64 GB（16 层，32Gb） | +1.8× | [JEDEC/SK 海力士] |
| 互连间距（DRAM 层间） | 25–40 um 微凸块 | 10 um 微凸块 → 混合键合路径 | 2.5–4× 更密 | [Onto Innovation] |
| 每层热阻 | ~0.15 K·mm²/W（微凸块） | ~0.08 K·mm²/W（混合键合目标） | −47% | [热分析综述] |
| Chiplet 互连 | 无（单片中介层） | UCIe 3.0 @ 48–64 GT/s | 新增能力 | [UCIe 3.0 规范] |
| 每瓦 IOPS | 基线 | 较 HBM3E +40% | +40% | [Micron] |

## 7. 一词概括

**可定制**（Customizable）— HBM4 将基础裸片从固定的 12nm 再分配层转变为 3nm 定制逻辑基板，加速器厂商可嵌入负载特定计算（ECC、NDP、PMU），带宽翻倍至 2+ TB/s，每比特功耗降低 40%，并通过 UCIe 开辟 chiplet 集成路径以实现系统级存储器解聚合。

## 8. 开放性问题与注意事项

- **定制基础裸片供应链** — TSMC、三星及第三方（GUC、创意电子）将竞争代工定制基础裸片。存储厂商（SK 海力士、三星存储、Micron）是否允许第三方基础裸片介入，还是维持垂直整合控制，是决定 HBM4 开放程度的关键产业结构问题。

- **混合键合时间表不确定** — 业界对混合键合何时进入 HBM 量产存在分歧：一些来源认为是 HBM4E（2027），另一些推迟至 HBM5（2028–2029）。新互连技术从研发展示到可接受良率量产之间历来有 2–3 年差距。

- **存内计算编程模型** — 具备运行定制逻辑能力的 3nm 基础裸片引发编程接口问题。目前不存在 HBM 基础裸片计算的标准 API 或 ISA 扩展；各厂商可能定义私有接口，导致软件生态碎片化。

- **成本结构变化** — 配备 3nm 基础裸片的 HBM4 成本将显著高于 12nm 基础裸片的 HBM3E。对于非超大规模客户（企业、汽车、边缘 AI），性能/瓦提升能否证明成本溢价的合理性尚不确定。

- **面向存储的 CPO 集成时间表** — 共封装光学初期面向网络交换机（横向扩展），而非存储互连（纵向扩展）。GPU 到 HBM 光学 I/O 通信（NVIDIA Rubin 代）预计十年末；近期 HBM4 仍为纯电气方案。

- **UCIe 3.0 存储器解聚合 vs CXL 3.1** — UCIe 和 CXL 均瞄准存储池化/解聚合，但分处不同层级：UCIe 在封装/chiplet 层面，CXL 在机架/系统层面。这两项标准如何在以存储为中心的架构中共存或融合，是开放的设计空间问题。

- **16 层堆叠的热-力学可靠性** — 16 层 HBM4 堆叠面临热循环带来的累积机械应力。微凸块和混合键合 16 层堆叠在工作温度下的长期可靠性数据（10 年以上）尚不存在。

## 9. 参考文献

1. **TSMC/GUC HBM4 披露** — Tom's Hardware, 2025. "HBM undergoes major architectural shakeup as TSMC and GUC detail HBM4, HBM4E and C-HBM4E." URL: https://www.tomshardware.com/pc-components/dram/hbm-undergoes-major-architectural-shakeup-as-tsmc-and-guc-detail-hbm4-hbm4e-and-c-hbm4e-3nm-base-dies-to-enable-2-5x-performance-boost-with-speeds-of-up-to-12-8gt-s-by-2027
2. **TSMC SoIC @ IEDM 2024** — TSMC/LatitudeDS, 2024. "IEDM 2024: TSMC's Next-Generation SoIC System-Level Chip Integration Platform." URL: https://www.latitudeds.com/post/iedm2024-tsmc-s-next-generation-soic-system-level-chip-integration-platform
3. **SemiAnalysis HBM 路线图** — SemiAnalysis, 2025. "Scaling the Memory Wall: The Rise and Roadmap of HBM." URL: https://newsletter.semianalysis.com/p/scaling-the-memory-wall-the-rise-and-roadmap-of-hbm
4. **TSMC C-HBM4E N3P** — TechPowerUp, 2026. "TSMC Showcases Custom C-HBM4E, N3P Logic Dies Target Double Efficiency." URL: https://www.techpowerup.com/343529/tsmc-showcases-custom-c-hbm4e-n3p-logic-dies-target-double-efficiency
5. **SK 海力士 HBM4E** — TrendForce, 2026. "SK hynix Reportedly Weighs TSMC 3nm for HBM4E Logic Dies." URL: https://www.trendforce.com/news/2026/03/20/news-sk-hynix-reportedly-weighs-tsmc-3nm-for-hbm4e-logic-dies-to-gain-edge-over-samsung/
6. **UCIe 3.0 规范** — SemiWiki/Alphawave, 2025. "UCIe 3.0: Doubling Bandwidth and Deepening Manageability for the Chiplet Era." URL: https://semiwiki.com/ip/alphawave/360532-ucie-3-0-doubling-bandwidth-and-deepening-manageability-for-the-chiplet-era/
7. **UCIe 存储器解聚合** — Ayar Labs, 2025. "AI Scale-Up and Memory Disaggregation: Two Use Cases Enabled by UCIe and Optical I/O." URL: https://ayarlabs.com/blog/ai-scale-up-and-memory-disaggregation-two-use-cases-enabled-by-ucie-and-optical-io/
8. **HBM 混合键合** — AllPCB, 2025. "Hybrid Bonding to Debut with HBM4E." URL: https://www.allpcb.com/allelectrohub/hybrid-bonding-to-debut-with-hbm4e
9. **微凸块 vs 混合键合** — SemiEngineering, 2026. "HBM4 Sticks With Microbumps, Postponing Hybrid Bonding." URL: https://semiengineering.com/hbm4-sticks-with-microbumps-postponing-hybrid-bonding/
10. **互连密度路线图** — Onto Innovation, 2025. "Bridging Performance and Yield: The Evolving Role of Interconnect Technologies in HBM." URL: https://ontoinnovation.com/resources/bridging-performance-and-yield-the-evolving-role-of-interconnect-technologies-in-hbm/
11. **ISSCC 2026 CPO** — SemiAnalysis, 2026. "ISSCC 2026: NVIDIA & Broadcom CPO, HBM4 & LPDDR6." URL: https://newsletter.semianalysis.com/p/isscc-2026-nvidia-and-broadcom-cpo
12. **Micron HBM4** — Micron Technology, 2026. "HBM4." URL: https://www.micron.com/products/memory/hbm/hbm4
13. **Siemens HBM 设计指南** — Siemens EDA, 2026. "HBM3e and HBM4: IC design guide for next-generation high bandwidth memory." URL: https://blogs.sw.siemens.com/semiconductor-packaging/2026/04/24/hbm3e-hbm4-ic-design-guide/
14. **HBM 热分析** — MDPI Electronics, 2025. "Thermal Issues Related to Hybrid Bonding of 3D-Stacked High Bandwidth Memory: A Comprehensive Review." URL: https://www.mdpi.com/2079-9292/14/13/2682

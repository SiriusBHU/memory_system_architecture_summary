# AMBA CHI C2C 与片上互联演进

> 本文对比了单片式 SoC 片上一致性互联方案（原方案）与 Chiplet 时代 CHI C2C 多芯粒一致性互联方案（演进方案）。调研来源涵盖 Arm 架构规范（CHI Issue B–G、CHI C2C IHI0098）、行业标准（UCIe 2.0）以及供应商工程文档，时间跨度 2017–2026 年。

## 1. 范围与方法

**领域界定。** 基于 Arm 的 SoC 及多芯粒系统中的一致性片上/芯片间互联。互联网络承载 CPU 集群、加速器、内存控制器与 I/O 子系统之间的一致性内存流量（snoop、request、response、data），是决定系统带宽、延迟和可扩展性的核心骨架。

**"原方案"与"演进方案"的含义。** *原方案* 指单片式 SoC 一致性互联：所有 IP 模块位于单颗裸片上，通过固定的一致性网格（如 CMN-600/700）使用 AMBA CHI 连接，整个一致性域限定在一个硅封装内。*演进方案* 通过 CHI C2C 包化将 CHI 一致性扩展到裸片边界之外，使用 UCIe 作为物理传输层，引入 NoC S3 作为异构非一致性背板，并增加跨裸片机密计算的 Realm 管理——从整体上打破了"一颗裸片 = 一个一致性域"的约束。

**资料来源。** 14 项主要来源：Arm 架构规范（CHI IHI0050、CHI C2C IHI0098、NoC S3 产品简报）、UCIe 联盟规范（UCIe 1.0/2.0）、行业博文（Arm Newsroom、Cadence、Synopsys）、学术会议报告（HPCA 2023 HipChips 研讨会）以及供应商产品文档（CMN S3、Neoverse CSS）。来源类型涵盖架构规范、行业标准、供应商工程博文和 EDA 验证文档。

## 2. 问题背景

**系统需要做什么。** 在异构计算单元——CPU 集群、GPU/NPU 加速器、内存控制器、I/O 桥——之间提供一致性、低延迟的数据搬运，同时支持面向 AI、HPC、网络和移动负载的数千亿晶体管级系统。

**为什么这个领域变得困难。** 单片 SoC 裸片已触及光刻掩模版极限（~858 mm2），超过此面积单次曝光无法完成图案化。制造良率随裸片面积呈超线性下降：在缺陷密度 0.1/cm2 条件下，600 mm2 裸片良率约 50%，而两颗 300 mm2 芯粒各自良率可达约 70%。与此同时，AI 和 HPC 负载对计算、内存带宽（HBM 堆叠）和 I/O 的需求超出了任何单颗裸片所能提供的范围。不同 IP 模块（CPU 用 3 nm、I/O 用 5 nm、模拟电路用 12 nm）的最优工艺节点各不相同，无法在同一衬底上共存。

**为什么原方案不再够用。** 单片一致性网格（CMN-600：每裸片最多 64 核；CMN-700：每裸片最多 256 核）无法容纳下一代 AI 加速器 + CPU 系统所需的晶体管预算、混合节点经济性或 I/O 岸线需求。将 SoC 拆分为芯粒需要一种能在裸片边界之间保持完整缓存一致性、安全 Realm 和低延迟 snoop 流量的协议——而片上 CHI 从未被设计用于此目的。

## 3. 具体问题与瓶颈证据

1. **掩模版极限封顶单片裸片面积** — 光刻掩模版对单次曝光面积施加了约 858 mm2 的硬上限。NVIDIA GB200 和 AMD MI300X 已填满掩模版，在单颗裸片上无法再增加额外 I/O 或计算单元。突破此极限必须采用多裸片分解。

2. **良率损失随裸片面积超线性增长** — 在缺陷密度 0.1/cm2 条件下，600 mm2 单片裸片良率约 50%；拆分为两颗 300 mm2 芯粒后，每颗良率提升至约 70%，同时可实现单颗裸片无法实现的系统配置 [Arteris Chiplet Guide]。

3. **裸片边缘的协议边界破坏一致性** — CHI C2C 出现之前，多芯片系统使用协议桥（CHI→CXL、CHI→私有协议），每跳增加 50–100 ns 延迟，且需要复杂的转换逻辑。这些桥接打断了统一的 snoop 域，无法将 Arm 安全 Realm 模型传播到裸片之外 [HPCA 2023 HipChips]。

4. **混合节点经济性迫使解耦** — 3 nm 计算裸片晶圆成本约 $16,000，5 nm I/O 裸片约 $10,000。在先进节点上放置模拟 SerDes、PCIe PHY 和 DDR 控制器，浪费了昂贵的晶体管密度在不受益于工艺缩放的电路上 [UCIe Consortium]。

5. **机密计算无法在无协议支持下跨多裸片** — Arm CCA Realm 管理扩展（RME）按安全 Realm 强制内存访问控制。缺少 CHI C2C 的 Realm 感知消息编码，加速器芯粒会被视为非安全世界外设，被拒绝访问 Realm 保护的内存，从而阻碍在解耦硬件上进行机密 AI 推理 [Arm RME-DA / CHI-G]。

### 瓶颈证据

| 约束 | 单片极限 | 芯粒方案 | 差距 | 来源 |
|---|---|---|---|---|
| 最大裸片面积 | 858 mm2（掩模版极限） | 不受限（多裸片堆叠） | 硬墙消除 | 光刻物理 |
| 核数（CMN-600） | 64 核/裸片 | 256+ 核/系统（CMN-700 多芯片） | 4x+ | Arm CMN-700 |
| 跨裸片一致性延迟 | +50–100 ns（桥接） | ~20 ns 开销（CHI C2C） | 延迟降低 2.5–5x | HPCA 2023 |
| 混合节点成本惩罚 | 全部使用先进节点（100%） | I/O 裸片成本降低 40% | 每晶圆节省约 $6K | UCIe Consortium |
| 安全 Realm 传播 | 无（桥接破坏 Realm） | 完整 RME-DA/CDA（CHI C2C 消息） | 已启用 | CHI-G 规范 |

## 4. 架构对比：原方案 vs 演进方案

**原方案 — 单片 SoC 片上 CHI 一致性**

```
    +========================================================+
    |                  单颗裸片 (SoC)                          |
    |                                                         |
    |  +-------+  +-------+  +-------+  +-------+            |
    |  | CPU-0 |  | CPU-1 |  | CPU-2 |  | CPU-3 |            |
    |  | (CHI) |  | (CHI) |  | (CHI) |  | (CHI) |            |
    |  +---+---+  +---+---+  +---+---+  +---+---+            |
    |      |          |          |          |                  |
    |  +---+----------+----------+----------+---+             |
    |  |       一致性网格网络 (CMN)               |             |
    |  |     (CHI Issue B–E, 单一域)             |             |
    |  +---+----------+----------+----------+---+             |
    |      |          |          |          |                  |
    |  +---+---+  +---+---+  +---+---+  +---+---+            |
    |  | SLC   |  | DDR MC |  | GPU   |  |  I/O  |           |
    |  |(缓存) |  | (DRAM) |  | (AXI) |  |(PCIe) |           |
    |  +-------+  +-------+  +-------+  +-------+            |
    |                                                         |
    +========================================================+
                         封装
```

*原方案：所有 IP 共享单颗裸片上的一个一致性网格。GPU 和 I/O 通过 AXI/ACE-Lite 桥接接入——它们作为 I/O 一致性代理参与一致性但不持有缓存行。裸片边界即系统边界。*

**演进方案 — Chiplet 时代 CHI C2C 多裸片一致性互联**

```
    +============================+    +============================+
    |      计算芯粒               |    |    加速器芯粒               |
    |     (Die 0, 3 nm)          |    |     (Die 1, 5 nm)          |
    |                            |    |                            |
    |  +------+ +------+        |    |        +------+ +------+   |
    |  |CPU-0 | |CPU-1 |        |    |        | NPU  | | HBM  |   |
    |  |(CHI) | |(CHI) |        |    |        |(CHI) | | Ctrl |   |
    |  +--+---+ +--+---+        |    |        +--+---+ +--+---+   |
    |     |        |             |    |           |        |       |
    |  +--+--------+------+     |    |     +-----+--------+--+   |
    |  | * CMN S3 (一致性  |     |    |     |  本地网格          |   |
    |  |   网格, CHI-G)    |     |    |     |  (CHI 一致性)     |   |
    |  +--------+----------+     |    |     +--------+----------+   |
    |           |                |    |              |              |
    |  +--------+----------+     |    |     +--------+----------+   |
    |  | * CHI C2C 协议层   |     |    |     | * CHI C2C 协议层   |   |
    |  |  (包化, Realm 管理)|     |    |     |  (包化, Realm 管理)|   |
    |  +--------+----------+     |    |     +--------+----------+   |
    |           |                |    |              |              |
    |  +--------+----------+     |    |     +--------+----------+   |
    |  | * UCIe PHY (D2D)  |     |    |     | * UCIe PHY (D2D)  |   |
    |  +--------+----------+     |    |     +--------+----------+   |
    +===========|================+    +==============|=============+
                |  +-----------+  芯粒链路    +-----------+  |
                +--| 基板       |================| 基板       |--+
                   | (硅中介层 / 有机基板)       |
                   +----------------------------+
    
    两颗裸片之下（非一致性背板）：
    +-----------------------------------------------------------+
    | * NoC S3 (非一致性, 最多 255 NI, AXI5/ACE5-Lite)          |
    |   连接: DDR MC, PCIe 根, USB, 显示, 传感器集线器          |
    +-----------------------------------------------------------+
```

*演进方案：计算芯粒与加速器芯粒位于不同裸片上，各自拥有本地一致性网格，通过 CHI C2C 包化经 UCIe PHY 连接。Realm 管理（RME-DA）将安全域传播到裸片边界之外。NoC S3 为外设连接提供非一致性背板。新增/变更元素以 `*` 标注。*

## 5. 演进方案的收益与未解决的问题

### 收益

- **突破掩模版极限** — CHI C2C 通过将一致性计算分布到多颗裸片上，使系统可以超越 858 mm2 的面积限制。每颗芯粒可独立选择最优良率和工艺节点。

- **降低协议边界延迟** — CHI C2C 包化避免了桥接方案中 CHI→CXL→CHI 的双重转换。协议层在片上 CHI 和 CHI C2C 之间的转换逻辑极为精简，容器格式（Format X 用于 UCIe，Format Y 用于 CXL）在设计上避免了复杂的打包/解包。

- **安全 Realm 跨裸片保持** — CHI C2C 在消息编码中携带 RME-DA 和 RME-CDA 属性，允许加速器芯粒访问 Realm 保护的内存，而不会被降级为非安全世界。这使得 GPU/NPU 位于独立裸片的解耦硬件上也能进行机密 AI 推理。

- **释放混合节点经济性** — 计算裸片采用 3 nm，I/O 裸片采用 5–7 nm，模拟裸片采用 12+ nm，各自使用成本最优工艺，同时通过 CHI C2C 保持完整的系统一致性。

- **异构非一致性背板** — NoC S3 支持最多 255 个网络接口并兼容 AXI5/ACE5-Lite，为大量不需要 snoop 流量的非一致性外设（显示、摄像头 ISP、连接、传感器）提供可扩展、低功耗的互联网络。

### 未解决的问题

- **UCIe 带宽 < 片上网格带宽** — UCIe 2.0 每通道最高 32 GT/s；即使在最大通道宽度下，芯片间聚合带宽仍低于片上 CMN 交叉开关。跨裸片 snoop 流量密集的负载（如细粒度生产者-消费者共享）延迟将高于单片设计。

- **缺乏统一的多供应商一致性生态** — CHI C2C 是 Arm 规范；使用 CXL.cache（Intel/AMD 生态）或私有协议（NVIDIA NVLink）的芯粒仍需协议桥接。混合 Arm CHI C2C 与 CXL 一致性芯粒的单一系统尚无标准化互操作层。

- **多裸片封装的散热与供电** — CHI C2C 解决了逻辑协议层问题，但未解决物理封装挑战：硅中介层上的散热、多裸片供电以及相邻芯粒间的热耦合仍是活跃的工程难题。

- **软件一致性模型复杂度** — OS 调度器、NUMA 感知分配器和运行时库需要更新以理解芯粒拓扑。跨裸片 snoop 延迟创造了一个新的 NUMA 层级，现有软件可能无法最优处理。

- **验证复杂度爆炸** — 多裸片一致性加 Realm 管理产生的组合状态空间远大于单裸片 CHI。EDA 供应商（Synopsys、Cadence）已发布专用 CHI C2C VIP，但全系统级验证仍是开放挑战。

## 6. 对比表

| 维度 | 原方案（单片 CHI SoC） | 演进方案（CHI C2C 多裸片） | 变化 | 来源 |
|---|---|---|---|---|
| 最大系统面积 | ~858 mm2（掩模版极限） | 不受限（多裸片堆叠） | 硬墙消除 | 光刻物理 |
| 一致性域 | 单裸片、单网格 | 多裸片、CHI C2C 统一一致性 | 跨裸片一致性启用 | CHI C2C IHI0098 |
| 跨裸片协议开销 | 无（无裸片边界）或 +50–100 ns（桥接） | ~20 ns 包化开销 | 延迟降低 2.5–5x | HPCA 2023 HipChips |
| 安全 Realm 传播 | 仅片上（RME 在网格内） | 跨裸片（CHI C2C 消息中的 RME-DA/CDA） | 芯粒间机密计算 | CHI-G / RME-DA 规范 |
| 非一致性外设网络 | NIC-400/NIC-450（NI 数量有限） | NoC S3（最多 255 NI，AXI5/ACE5-Lite） | NI 可扩展性 ~5x | Arm NoC S3 |
| 工艺节点灵活性 | 所有 IP 同一节点 | 每颗芯粒使用最优节点（3/5/7/12 nm） | I/O 裸片成本降低 30–40% | UCIe Consortium |
| 物理传输标准 | 片上布线（无需标准） | UCIe 2.0（32 GT/s, 2D/2.5D/3D） | 开放 D2D 标准 | UCIe 2.0 规范 |
| CHI 协议版本 | CHI Issue B–E（片上） | CHI Issue G + C2C 扩展 | Realm 管理 + DataSource + C2C | CHI-G 规范 |
| 验证复杂度 | 单裸片一致性 VIP | 多裸片 C2C VIP（Synopsys/Cadence） | 组合状态爆炸 | Synopsys CHI-G VIP |

## 7. 一词定性

**包化**（Packetized）— 核心创新在于将片上 CHI 一致性协议包化为固定大小的容器（Format X / Format Y），使其适合在标准化的芯片间链路上传输，将原本的裸片内布线问题转化为裸片间的分组交换协议，同时完整保留一致性语义和安全 Realm 属性。

## 8. 开放问题与注意事项

- **CHI C2C 规模化延迟** — 已公布的延迟开销数据来自 2 裸片配置。在 4–8 芯粒拓扑中多跳 CHI C2C 路由的行为尚未公开表征。
- **UCIe 3.0 及后续** — UCIe 2.0 目标速率为 32 GT/s，未来版本计划支持 48–64 GT/s。CHI C2C 容器格式是否需要针对更高带宽链路进行修订，是一个开放的规范问题。
- **CXL 4.0 的融合** — CXL 4.0（预计约 2026 年）可能引入 PCIe 接入设备间更紧密的缓存一致性。CHI C2C 与 CXL.cache 在协议层面是趋同、共存还是竞争，尚不明确。
- **芯粒间安全攻击面** — 将一致性扩展到物理链路上暴露了片上网格中不存在的新侧信道向量（时序、电磁）。CHI C2C 规范将物理层安全委托给 UCIe；这种分层信任模型在对抗性条件下的充分性尚未得到验证。
- **软件生态成熟度** — Linux 内核 NUMA 提示、Android 内存管理（LMKD、cgroups）和 hypervisor 内存分区尚未对芯粒粒度的一致性域建模。驱动和 OS 层面的变更是必需的但尚未标准化。
- **NoC S3 的落地时间线** — NoC S3 已发布但量产硅片数据（实测功耗/面积）尚未公开。与 NIC-400/NIC-450 的真实世界 PPA 对比仍不可得。

## 9. 参考文献

1. **AMBA CHI C2C 架构规范 (IHI0098)** — Arm Ltd., 2024. "AMBA CHI Chip-to-Chip (C2C) Architecture Specification." 文档号 IHI0098A. URL: https://developer.arm.com/documentation/ihi0098/latest/
2. **Arm 新闻: CHI C2C** — Arm Ltd., 2024. "Ecosystem Collaboration Drives New AMBA Specification for Chiplets." URL: https://newsroom.arm.com/blog/amba-chi-c2c-specification
3. **AMBA CHI 架构规范 (IHI0050)** — Arm Ltd., 2024. "AMBA 5 CHI Architecture Specification, Issue G." 文档号 IHI0050. URL: https://developer.arm.com/documentation/ihi0050/latest/
4. **CHI Issue G 演进** — Cadence, 2024. "Evolution of AMBA CHI Protocol: Introducing Issue G Update." URL: https://community.cadence.com/cadence_blogs_8/b/fv/posts/evolution-of-amba-chi-protocol-introducing-issue-g-update
5. **Synopsys CHI-G VIP** — Synopsys, 2024. "Industry's First Verification IP for Arm AMBA CHI-G." URL: https://www.synopsys.com/blogs/chip-design/amba-chi-g-verification-ip.html
6. **Synopsys CHI C2C 验证** — Synopsys, 2024. "AMBA CHI C2C System Verification Solutions." URL: https://www.synopsys.com/blogs/chip-design/amba-chi-c2c-system-verification-solutions.html
7. **Cadence CHI C2C 介绍** — Cadence, 2024. "An Introduction to AMBA CHI Chip-to-Chip (C2C) Protocol." URL: https://www.design-reuse.com/blog/56200-an-introduction-to-amba-chi-chip-to-chip-c2c-protocol/
8. **HPCA 2023 HipChips 研讨会** — Defilippi, J. (Arm), 2023. "AMBA for Chiplets." HPCA HipChips Workshop. URL: https://hipchips.github.io/hpca2023/
9. **Arm NoC S3** — Arm Ltd., 2024. "NoC S3: Next Generation Network-on-Chip Interconnect for Armv9-A SoCs." URL: https://www.arm.com/products/silicon-ip-system/interconnect/noc-s3
10. **Arm CMN S3** — Arm Ltd., 2024. "Neoverse CMN S3 Coherent Mesh Network." URL: https://www.arm.com/products/silicon-ip-system/neoverse-interconnect/cmn-s3
11. **UCIe 2.0 规范** — UCIe Consortium, 2024. "Universal Chiplet Interconnect Express Specification, Revision 2.0." URL: https://www.uciexpress.org/specifications
12. **Arteris 芯粒指南** — Arteris, 2024. "Chiplets 101: An Arteris Guide to Multi-Die Architecture." URL: https://www.arteris.com/blog/chiplets-101-an-arteris-guide-to-multi-die-architecture/
13. **CHI 规范演进** — Cadence / ChipEstimate, 2024. "How AMBA CHI Specification Has Evolved." URL: https://www.chipestimate.com/How-AMBA-CHI-Specification-Has-Evolved/Cadence/blogs/3583
14. **Arm 开发者: 多芯片 CHI C2C** — Arm Developer Blog, 2024. "Moving AMBA Forward with Multi-Chip and CHI C2C." URL: https://developer.arm.com/community/arm-community-blogs/b/servers-and-cloud-computing-blog/posts/multi-chip-and-chi-c2c

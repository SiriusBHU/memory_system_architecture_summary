# 细粒度异构一致性特化 (Fine-Grain Heterogeneous Coherence Specialization)

> **一词总结：** 特化

## 1. 范围与方法

本文梳理缓存一致性协议从"统一 MESI/MOESI 覆盖所有 IP"向"按单次访存粒度特化一致性策略"的演进路径。重点关注 Spandex 一致性接口及其 FCS（Fine-grain Coherence Specialization）扩展——根据数据共享模式（write-once、migratory、producer-consumer）为每一条访存请求独立选择最优一致性请求类型。同时回顾底层 DeNovo 协议，并与工业界 AMBA CHI/ACE 及 CXL 一致性方案做对照。资料来源包括 FCS 论文（ACM TACO 2022）、原始 Spandex 论文（ISCA 2018）、DeNovo 协议研究及 Cohmeleon 学习型编排工作。

## 2. 问题背景

现代 SoC 在单芯片或单封装内集成 CPU、GPU、DSP 及领域专用加速器，共享统一物理地址空间。在这些计算特性迥异的 IP 之间维护内存一致性对正确性至关重要，但代价日益高昂。

传统 MESI/MOESI 协议为同构 CPU 多处理器设计，通过写方发起的无效化（writer-initiated invalidation）来保证单写者-多读者（SWMR）不变量。当所有参与者具有相似的缓存层级、访问粒度和延迟/吞吐权衡时，这套机制运行良好。然而 GPU 偏重吞吐而非延迟，采用大规模并行和自失效协议来直接保证松弛一致性模型，而非 SWMR。许多加速器根本没有缓存，无法原生参与一致性协议。强制所有 IP 使用同一套 MESI/MOESI 协议导致"最低公分母"设计：CPU 为适配 GPU 访问模式承担额外开销，GPU 则受 CPU 中心化无效化风暴的拖累。结果是带宽浪费、延迟增加，且协议复杂度随设备多样性急剧膨胀。

## 3. 具体问题与证据

### P1：统一协议与异构访问模式不匹配

MESI 的写方发起无效化机制在每次写共享数据时产生 O(N) 条一致性消息。对于 GPU 工作负载中数千线程写不相交区域的场景，这些无效化完全多余。证据：FCS 论文表明，在 GPU 主导的基准测试中，统一 MESI 下高达 99% 的网络流量由冗余一致性消息构成 [1]。

### P2：粗粒度协议分配浪费优化机会

即使 Spandex（FCS 之前）等混合方案也只在设备粒度分配一致性策略——例如所有 GPU 访问使用 GPU 一致性，所有 CPU 访问使用 MESI。但在单个内核中，不同数据结构呈现不同的共享模式：有些只写一次再被多次读取，有些在生产者和消费者之间迁移。设备级分配无法利用这种多样性。证据：设备粒度的 Spandex 平均减少 16% 执行时间；叠加按访存粒度的 FCS 后额外再减少 13% [1][2]。

### P3：协议复杂度随异构性爆炸增长

传统 MESI 有 4 个稳态，但实际实现中存在数十个瞬态。为每种互连类型（AMBA CHI、CXL、NVLink）分别添加 GPU 一致性、加速器一致性和桥接逻辑，使复杂度成倍增长。验证负担呈组合爆炸。证据：HeteroGen（HPCA 2022）表明异构一致性协议的手工设计极易出错，需要自动化综合来管控状态空间爆炸 [4]。

### P4：LLC 处的带宽浪费

MESI 下，所有权转移需发送完整缓存行数据，即使只有少数字被修改。在生产者-消费者模式中，整行被取回、部分更新、再转发——浪费 LLC 带宽。证据：Spandex 的字粒度所有权避免全行传输，微基准测试中网络 flit 数减少高达 5.30 倍 [2]。

## 4. 架构示意

### 原始方案：统一 MESI/MOESI 一致性

```
 ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
 │  CPU-0   │  │  CPU-1   │  │  GPU CU0 │  │  加速器  │
 │  L1 (M)  │  │  L1 (M)  │  │  L1 (M)  │  │  L1 (M)  │
 └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
      │              │              │              │
      │  所有 IP 使用相同 MESI      │              │
      │  写方发起无效化             │              │
      ▼              ▼              ▼              ▼
 ┌─────────────────────────────────────────────────────┐
 │            共享 L2 / LLC（目录式 MESI）              │
 │  ┌─────────────────────────────────────────────┐    │
 │  │  每行状态：M | E | S | I                    │    │
 │  │  每行共享者位向量                            │    │
 │  │  写时触发无效化                              │    │
 │  │  以缓存行为粒度传输                          │    │
 │  └─────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────┘
                        │
                        ▼
                   ┌─────────┐
                   │  DRAM   │
                   └─────────┘

 问题：GPU CU 对不相交写产生无效化风暴。
 加速器被迫使用它们不需要的 MESI 状态。
 一刀切 = 每个设备都承担最差情况开销。
```

### 演进方案：Spandex + 细粒度一致性特化 (FCS)

```
 ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
 │  CPU-0   │  │  CPU-1   │  │  GPU CU0 │  │  加速器  │
 │  L1+FCS  │  │  L1+FCS  │  │  L1+FCS  │  │  L1+FCS  │
 │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │
 │ │请求  │ │  │ │请求  │ │  │ │请求  │ │  │ │请求  │ │
 │ │选择  │ │  │ │选择  │ │  │ │选择  │ │  │ │选择  │ │
 │ │逻辑  │ │  │ │逻辑  │ │  │ │逻辑  │ │  │ │逻辑  │ │
 │ └──┬───┘ │  │ └──┬───┘ │  │ └──┬───┘ │  │ └──┬───┘ │
 └────┼─────┘  └────┼─────┘  └────┼─────┘  └────┼─────┘
      │              │              │              │
      │   每个请求独立选择：                       │
      │   • ReqV  (读有效)   = DeNovo 风格        │
      │   • ReqO  (所有权写) = MESI 风格          │
      │   • ReqWT (写穿透)   = GPU 风格           │
      │   • ReqWB (写回)     = 迁移优化           │
      │   • ReqFwd(转发)     = 生产-消费优化      │
      ▼              ▼              ▼              ▼
 ┌─────────────────────────────────────────────────────┐
 │              Spandex LLC（统一）                     │
 │  ┌─────────────────────────────────────────────┐    │
 │  │  按字（WORD）粒度跟踪所有权（非按行）        │    │
 │  │  所有者 ID 存储在 LLC 数据行中               │    │
 │  │  无瞬态（DeNovo 基础）                       │    │
 │  │  按访问灵活处理请求                          │    │
 │  │  基于 trace 的自动特化引擎                   │    │
 │  └─────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────┘
                        │
                        ▼
                   ┌─────────┐
                   │  DRAM   │
                   └─────────┘

 关键：每条访存独立选择最优一致性请求类型。
 Write-once 数据跳过所有权获取；
 迁移数据使用 ReqWB；生产-消费使用 ReqFwd。
```

## 5. 解决了什么 / 未解决什么

### 解决的问题

- **消除冗余无效化。** GPU write-once 模式使用写穿透请求完全绕过所有权获取，一致性流量减少高达 99%。
- **降低异构工作负载执行时间。** 按访存粒度特化在设备级 Spandex 基础上进一步减少高达 61% 的执行时间。
- **简化协议复杂度。** Spandex 仅有 3 个稳态（来自 DeNovo），无瞬态，而生产级 MESI 有数十个瞬态。FCS 只增加请求选择逻辑，不引入新的协议状态。
- **支持自动优化。** 基于 trace 的特化引擎可在无需程序员标注的情况下确定最优请求类型，使得方案具有实用性。
- **兼容多种设备类型。** CPU、GPU 和加速器可各自发出最适合当前访问的请求类型，无需静态绑定到设备类型。

### 未解决的问题

- **软件无数据竞争要求。** DeNovo/Spandex 基础要求程序无数据竞争（DRF）。有竞争的代码将产生错误结果。这对程序员或语言运行时施加了约束。
- **非一致性加速器。** 仅通过非缓存 MMIO 或 DMA 通信的设备完全绕过 Spandex；该协议不能使非一致性 IP 变为一致性的。
- **跨芯片一致性。** FCS 针对单芯片或单封装一致性域。多插槽或 chiplet 间一致性（CXL.cache、NVLink-C2C）需要额外的桥接协议。
- **遗留软件兼容性。** 为 MESI 系统编译的现有二进制无法利用 FCS，除非重新编译或进行二进制翻译以发出特化请求类型。
- **动态模式变化。** 基于 trace 的特化是离线分析的。访问模式随运行阶段变化的工作负载可能无法被单一静态决策最优地服务。

## 6. 量化对比

| 维度 | 统一 MESI/MOESI | Spandex（设备级） | Spandex + FCS |
|---|---|---|---|
| 一致性粒度 | 按设备，所有 IP 一套协议 | 按设备类型（CPU=MESI, GPU=GPU 一致性） | 按单次访存请求 |
| 稳态数 | 4 (MESI) 或 5 (MOESI) + 数十瞬态 | 3（来自 DeNovo），无瞬态 | 3（与 Spandex 一致） |
| 所有权跟踪 | 按缓存行 | 按字 | 按字 |
| 执行时间减少（均值） | 基线 (0%) | ~16% 均值，最高 29% | 最高 61%（在 Spandex 基础上再减 13%） |
| 网络流量减少 | 基线 (0%) | ~27% 均值，最高 58% | 最高 99% |
| 网络 flit 减少（微基准） | 基线 | 最高 3.55 倍 | 最高 5.30 倍（flit-hop 计数） |
| 写模式优化 | 无——所有写使用 GetM | 仅设备默认 | Write-once: ReqWT; migratory: ReqWB; prod-cons: ReqFwd |
| 自动特化 | 不适用 | 不适用 | 基于 trace 的引擎为每次访存选择最优请求类型 |
| DRF 要求 | 否 | 是（DeNovo 基础） | 是（继承） |
| 硬件面积开销 | 基线 | 小（简化状态） | 极小（请求选择逻辑 + trace 表） |

## 7. 一词总结

**特化** —— 核心洞见是同一应用中不同的数据访问值得不同的一致性处理方式，而特化的粒度应当是单条访存请求，而非设备或协议。

## 8. 开放问题

1. **运行时自适应特化。** 当前基于 trace 的方法离线确定请求类型。硬件学习（如 Cohmeleon 式 ML 预测器）能否在运行时为阶段变化的工作负载自适应特化决策，同时不引入过高开销？

2. **CXL.cache 集成。** CXL 3.0 为 Type-2 设备引入反向无效化窥探，Spandex/FCS 如何映射到 CXL 的三个子协议（CXL.io、CXL.cache、CXL.mem）上？FCS 能否减少 CXL.cache 窥探流量？

3. **放松 DRF 要求。** DeNovo 和 Spandex 基本要求数据无竞争。FCS 方法能否适配 TSO 或其他更强的内存模型而不失去协议简洁性？

4. **Chiplet 级一致性。** 随着 UCIe 和 CXL 支持多芯粒集成，FCS 式的按请求特化能否跨延迟不对称的芯粒间链路工作？

5. **规模化验证。** 虽然 FCS 只增加极小的协议复杂度，但按访存特化选择的组合空间巨大。形式化验证如何跟上这种灵活性？

6. **与存内计算的交互。** PIM/PNM 设备在 DRAM 内部计算，不参与缓存一致性。FCS 应如何处理间歇性由 PIM 单元处理的数据区域的一致性？

## 9. 参考文献

1. Alsop, J., Sinclair, M. D., Adve, S. V. (2022). "A Case for Fine-grain Coherence Specialization in Heterogeneous Systems." *ACM Transactions on Architecture and Code Optimization*, 19(3), Article 39. DOI: [10.1145/3530819](https://dl.acm.org/doi/10.1145/3530819). arXiv: [2104.11678](https://arxiv.org/abs/2104.11678).

2. Alsop, J., Sinclair, M. D., Adve, S. V. (2018). "Spandex: A Flexible Interface for Efficient Heterogeneous Coherence." *Proceedings of the 45th International Symposium on Computer Architecture (ISCA)*. DOI: [10.1109/ISCA.2018.00031](https://dl.acm.org/doi/10.1109/ISCA.2018.00031).

3. Komuravelli, R., Adve, S. V., Sung, H. (2015). "Efficient GPU Synchronization without Scopes: Saying No to Complex Consistency Models." *Proceedings of the 48th International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/2830772.2830821](https://dl.acm.org/doi/10.1145/2830772.2830821).

4. Zhang, N., et al. (2022). "HeteroGen: Automatic Synthesis of Heterogeneous Cache Coherence Protocols." *Proceedings of the 28th IEEE International Symposium on High-Performance Computer Architecture (HPCA)*. 链接: [PDF](https://vasigavr1.github.io/files/heterogen-hpca-22.pdf).

5. Daya, B. K., et al. (2022). "Cohmeleon: Learning-Based Orchestration of Accelerator Coherence in Heterogeneous SoCs." arXiv: [2109.06382](https://arxiv.org/abs/2109.06382).

6. Lustig, D., et al. (2019). "A Formal Analysis of the NVIDIA PTX Memory Consistency Model." *Proceedings of the 24th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*. DOI: [10.1145/3297858.3304043](https://dl.acm.org/doi/10.1145/3297858.3304043).

7. Guo, F., et al. (2019). "Mozart: Taming Taxes and Composing Accelerators with Shared-Memory." *Proceedings of the 57th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/3656019.3676896](https://dl.acm.org/doi/10.1145/3656019.3676896).

8. Ausavarungnirun, R., et al. (2025). "Cohet: A CXL-Driven Coherent Heterogeneous Computing Framework." arXiv: [2511.23011](https://arxiv.org/abs/2511.23011).

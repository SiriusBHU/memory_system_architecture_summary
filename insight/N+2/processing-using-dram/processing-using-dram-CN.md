# Processing-using-DRAM 延迟优化

> **一词总结：** 自适应

## 1. 范围与方法

本文梳理 Processing-using-DRAM（PuD）从固定精度批量位运算到数据感知、动态精度执行并结合多阵列并发的演进路径。重点关注 Proteus 框架（ICS 2025），这是首个直接攻克 PuD 固有高延迟问题（而非仅通过数据级并行来隐藏延迟）的硬件设计。我们将 Proteus 与先前的 PuD 机制进行对照——Ambit（MICRO 2017）的三行激活批量位运算，以及 SIMDRAM（ASPLOS 2021）的端到端位串行 SIMD——并考察窄值利用和自适应算术如何将 PuD 从一种纯吞吐技术转变为同时具有延迟竞争力的方案。资料来源包括 Proteus 论文（arXiv 2501.17466，ICS 2025）、Ambit 和 SIMDRAM 论文，以及 CMU-SAFARI 的 Proteus 模拟器仓库。

## 2. 问题背景

Processing-using-DRAM（PuD）利用 DRAM 阵列的模拟操作特性——特别是位线间的电荷共享——直接在存储器内部执行批量逻辑运算，无需将数据搬移到 CPU 或 GPU。典型机制为三行激活（Ambit）：同时激活三条 DRAM 行通过电荷共享产生按位多数（MAJ）函数，配合 NOT 操作即可实现功能完备（AND、OR、NOT，进而构造任意布尔函数）。

PuD 的吸引力在于它以 DRAM 内部全带宽（每芯片数百 GB/s）运行，而非受限于窄片外总线带宽。Ambit 在批量位运算上实现了相对 Skylake CPU 44 倍的吞吐提升和 35 倍的能耗降低。SIMDRAM 通过 MAJ/NOT 分解将其扩展到任意操作，16 个 bank 下达到 CPU 88 倍的吞吐。

然而，现有所有 PuD 机制共享一个关键局限：它们处理每个操作数的每一位，而不考虑实际信息内容。两个操作数都只需 8 位表示的 32 位加法，仍然执行 32 个位串行周期。这种固定精度、纯吞吐的执行模型意味着 PuD 延迟与操作数位宽成线性关系，使其对延迟敏感的任务缺乏竞争力，也不适合实际应用中常见的窄值分布工作负载（如神经网络推理、图分析、数据库操作）。

## 3. 具体问题与证据

### P1：固定位精度在无用比特上浪费周期

标准 PuD 对 N 位操作数处理全部 N 位，需要 N 个串行周期，而不考虑实际值的大小。对于 32 位整数，值为 5（二进制：00000...101）仍然需要 32 个周期。证据：Proteus 作者证明在 12 个真实应用中，平均有效精度（非冗余位）显著小于标称精度，许多值是"窄"的——具有大量前导零或前导一 [1]。

### P2：纯吞吐执行模型限制适用范围

现有 PuD 通过大规模数据级并行来隐藏其高单操作延迟：同时对数千行操作。这对批量操作（memset、位图交集）有效，但对结果可用时序重要的延迟敏感操作无能为力（如图遍历中的依赖计算、神经网络推理中的条件分支）。证据：SIMDRAM 在 16 个 bank 下达到 CPU 88 倍吞吐，但未解决单操作延迟问题，延迟仍与位宽成正比 [2][3]。

### P3：单阵列执行未充分利用 DRAM 并行性

一个 DRAM 芯片包含多个 bank，每个 bank 有多个子阵列/阵列。标准 PuD 将每个操作限制在单个阵列中，其他阵列空闲。DRAM 的内部并行性——设计用于跨 bank 的行级并行——未被用来加速单个操作。证据：Proteus 表明在单 bank 内跨多个阵列的并发执行可以按阵列数量比例降低延迟 [1]。

### P4：僵化的数据表示导致次优算术

PuD 操作使用固定的数据表示（通常为无符号或二进制补码）和单一算术算法，而不考虑操作数特性。不同的表示（原码、反码）和算法（行波进位 vs 保存进位）根据操作数值有不同的延迟特性。证据：Proteus 证明根据运行时操作数特征动态选择数据表示和算术实现可带来显著的延迟降低 [1]。

## 4. 架构示意

### 原始方案：标准 PuD 固定精度批量位运算

```
 ┌─────────────────────────────────────────────────┐
 │                  DRAM 芯片                       │
 │  ┌──────────────────────────────────────────┐   │
 │  │              Bank 0                      │   │
 │  │  ┌────────────────────────────────────┐  │   │
 │  │  │         子阵列 / 阵列 0            │  │   │
 │  │  │  行 A: [0100 1100 0000 ... 0011]   │  │   │
 │  │  │  行 B: [1101 0010 0000 ... 1100]   │  │   │
 │  │  │  行 C: [0000 0000 0000 ... 0000]   │  │   │
 │  │  │                                    │  │   │
 │  │  │  三行激活 (TRA):                   │  │   │
 │  │  │  同时激活 A、B、C                  │  │   │
 │  │  │  → C = MAJ(A, B, C)               │  │   │
 │  │  │  无论值内容，全部 32 位都处理      │  │   │
 │  │  └────────────────────────────────────┘  │   │
 │  │                                          │   │
 │  │  阵列 1..N：操作期间空闲                 │   │
 │  └──────────────────────────────────────────┘   │
 │                                                  │
 │  Bank 1..7：空闲（无跨 bank PuD）               │
 └─────────────────────────────────────────────────┘
                        │
                  内存控制器
          （发出 TRA 命令，
           N 位操作数固定 N 周期延迟）

 问题：5+3 的 32 位加法耗费 32 周期。
 仅一个阵列活跃。第 3..31 位全是零
 但仍被处理。纯吞吐模型。
```

### 演进方案：Proteus 数据感知 PuD 动态精度

```
 ┌─────────────────────────────────────────────────┐
 │                  DRAM 芯片                       │
 │  ┌──────────────────────────────────────────┐   │
 │  │              Bank 0                      │   │
 │  │  ┌──────────────┐  ┌──────────────┐     │   │
 │  │  │  阵列 0      │  │  阵列 1      │     │   │
 │  │  │  位 0..7     │  │  位 8..15    │     │   │
 │  │  │  (活跃)      │  │  (活跃)      │     │   │
 │  │  │  并发执行    │  │  并发执行    │     │   │
 │  │  └──────┬───────┘  └──────┬───────┘     │   │
 │  │         │                  │              │   │
 │  │  ┌──────────────┐  ┌──────────────┐     │   │
 │  │  │  阵列 2      │  │  阵列 3      │     │   │
 │  │  │  位 16..23   │  │  位 24..31   │     │   │
 │  │  │  已跳过      │  │  已跳过      │     │   │
 │  │  │  (窄值优化)  │  │  (窄值优化)  │     │   │
 │  │  └──────────────┘  └──────────────┘     │   │
 │  └──────────────────────────────────────────┘   │
 └─────────────────────────────────────────────────┘
                        │
         ┌──────────────────────────────┐
         │   Proteus 运行时引擎         │
         │  ┌────────────────────────┐  │
         │  │ 窄值检测器             │  │
         │  │ 扫描前导 0/1           │  │
         │  │ → 有效精度             │  │
         │  └────────┬───────────────┘  │
         │  ┌────────▼───────────────┐  │
         │  │ 表示与算法选择器       │  │
         │  │ 原码 vs 补码           │  │
         │  │ 行波进位 vs 保存进位   │  │
         │  └────────┬───────────────┘  │
         │  ┌────────▼───────────────┐  │
         │  │ 多阵列调度器           │  │
         │  │ 将位切片分配到         │  │
         │  │ 各 DRAM 阵列           │  │
         │  └────────────────────────┘  │
         └──────────────────────────────┘

 结果：5+3 的 32 位加法耗费约 3 周期（3 位
 有效精度），跨阵列分布执行，而非 32 周期。
```

## 5. 解决了什么 / 未解决什么

### 解决的问题

- **降低 PuD 操作延迟。** 通过仅处理有效位（窄值优化），延迟从 O(N) 降至 O(k)，其中 k 为有效精度，通常远小于 N。
- **利用 DRAM 内部并行性。** 将位切片分配到 bank 内多个阵列实现并发执行，延迟随阵列数量近线性降低。
- **提升单位面积性能。** Proteus 在 12 个应用的平均值上，单 bank 性能密度分别是 CPU 的 17 倍、GPU 的 7.3 倍、SIMDRAM 的 10.2 倍。
- **大幅降低能耗。** 分别比 CPU、GPU、SIMDRAM 低 90.3 倍、21 倍、8.1 倍。
- **对程序员透明。** 运行时引擎动态选择数据表示和算术算法，无需程序员标注或代码修改。
- **使延迟敏感的 PuD 工作负载成为可能。** 通过降低单操作延迟，PuD 不再局限于批量吞吐操作，可扩展到图分析和神经网络推理等场景。

### 未解决的问题

- **DRAM 工艺约束。** PuD 仍需三行激活，这对 DRAM 时序裕量有压力，可能与部分 DRAM 厂商的单元设计不兼容。Proteus 未改变底层 DRAM 阵列。
- **数据布局要求。** PuD 要求位串行（纵向）数据布局，与传统行优先（横向）布局冲突。数据必须先转置才能进行 PuD 操作，产生额外开销。
- **有限的操作类型。** 虽然 SIMDRAM 证明任意布尔操作可行，但复杂操作（浮点乘法、除法）仍分解为大量位串行原语，即使经 Proteus 优化后延迟仍然较高。
- **依赖窄值分布。** 延迟收益与值的窄度成正比。值均匀宽度的工作负载（如加密、压缩）从动态精度中获益较少。
- **无跨 bank 协调。** Proteus 在单 bank 内优化。跨多 bank 的操作（如大矩阵乘法）仍需内存控制器协调和数据搬移。
- **可靠性问题。** 三行激活超出 DRAM 正常规范运行，噪声裕量可能较低，软错误率可能上升。

## 6. 量化对比

| 维度 | 标准 PuD（Ambit/SIMDRAM） | Proteus（数据感知 PuD） |
|---|---|---|
| 位精度 | 固定：N 位操作数处理全部 N 位 | 动态：仅处理有效位（跳过前导 0/1） |
| 阵列利用 | 每操作单阵列 | bank 内多阵列并发执行 |
| 数据表示 | 固定（通常为无符号/二进制补码） | 自适应：运行时为每个操作选择最优表示 |
| 算术算法 | 固定（单一实现） | 灵活：为每对操作数选择最优算法 |
| 性能密度 vs CPU | Ambit: 44x 吞吐; SIMDRAM: ~5.5x/bank | 17x（单 bank，12 应用均值） |
| 性能密度 vs GPU | SIMDRAM: ~0.36x/bank（需 16 bank） | 7.3x（单 bank） |
| 性能密度 vs SIMDRAM | 基线 (1x) | 10.2x |
| 能耗 vs CPU | Ambit: 35x; SIMDRAM: 257x（16 bank） | 90.3x |
| 能耗 vs GPU | SIMDRAM: 31x（16 bank） | 21x |
| 能耗 vs SIMDRAM | 基线 (1x) | 8.1x |
| 延迟模型 | O(N)/操作，N = 位宽 | O(k/A)，k = 有效位数，A = 使用的阵列数 |
| 程序员负担 | SIMDRAM: MAJ/NOT 分解 | 透明的运行时自适应 |
| 硬件开销 | Ambit: ~1% 面积; SIMDRAM: 0.2% 面积 | 内存控制器中的运行时引擎（适中） |

## 7. 一词总结

**自适应** —— 核心洞见是 PuD 操作应当根据实际被处理的数据来调整其精度、数据表示和并行策略，而非盲目地以固定位宽处理每个操作数的每一位。

## 8. 开放问题

1. **浮点 PuD。** Proteus 面向整数算术。窄值/自适应表示方法能否扩展到 IEEE 754 浮点数？指数和尾数具有不同的窄度特性。

2. **与 PIM 控制器的集成。** 随着 PIM 架构（HBM-PIM、GDDR-PIM）成熟，Proteus 式运行时引擎能否嵌入 PIM 逻辑芯粒而非内存控制器？

3. **编译器辅助的精度提示。** 当前运行时在执行时检测窄值。编译器能否提供值域的静态提示（如来自范围分析），以预配置 Proteus 引擎并减少检测开销？

4. **多 bank 协调。** Proteus 在单 bank 内优化。对于跨多 bank 的操作（如大规模矩阵乘法），内存控制器应如何编排带 Proteus 式自适应的跨 bank PuD？

5. **DRAM 厂商兼容性。** 三行激活不属于任何 DRAM 标准（DDR5、LPDDR5X）。标准化路径是什么？Proteus 的额外时序要求与厂商特定的 DRAM 单元设计如何交互？

6. **安全影响。** 共享 DRAM 行的 PuD 操作可能被利用于侧信道攻击（类似 RowHammer）。Proteus 的多阵列并发执行是否扩大了攻击面？

7. **与 CXL 内存的交互。** CXL 挂载的内存池可能服务多个主机。在多主机争用 DRAM 阵列的共享 CXL 内存架构中，PuD/Proteus 操作如何工作？

## 9. 参考文献

1. Bostanci, E., Oliveira, G. F., Cali, D. S., Ghiasi, N. M., Fernandez, R., Luna, I. E., Manglik, S., Novo, D., Gomez-Luna, J., Mutlu, O. (2025). "Proteus: Achieving High-Performance Processing-Using-DRAM with Dynamic Bit-Precision, Adaptive Data Representation, and Flexible Arithmetic." *Proceedings of the 39th ACM International Conference on Supercomputing (ICS 2025)*. arXiv: [2501.17466](https://arxiv.org/abs/2501.17466). GitHub: [CMU-SAFARI/Proteus](https://github.com/CMU-SAFARI/Proteus).

2. Seshadri, V., Lee, D., Mullins, T., Hassan, H., Boroumand, A., Kim, J., Kozuch, M. A., Mutlu, O., Gibbons, P. B., Mowry, T. C. (2017). "Ambit: In-Memory Accelerator for Bulk Bitwise Operations Using Commodity DRAM Technology." *Proceedings of the 50th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/3123939.3124544](https://dl.acm.org/doi/10.1145/3123939.3124544).

3. Hajinazar, N., Oliveira, G. F., Gregorio, S., Ferreira, J. D., Ghiasi, N. M., Patel, M., Alser, M., Cali, D. S., Novo, D., Mutlu, O. (2021). "SIMDRAM: An End-to-End Framework for Bit-Serial SIMD Computing in DRAM." *Proceedings of the 26th ACM International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*. DOI: [10.1145/3445814.3446749](https://dl.acm.org/doi/10.1145/3445814.3446749). arXiv: [2105.12839](https://arxiv.org/abs/2105.12839).

4. Ghose, S., Boroumand, A., Kim, J. S., Gomez-Luna, J., Mutlu, O. (2019). "Processing-in-Memory: A Workload-Driven Perspective." *IBM Journal of Research and Development*, 63(6). 链接: [PDF](https://arxiv.org/pdf/2012.03112).

5. Seshadri, V., Hsieh, K., Boroumand, A., Lee, D., Kozuch, M. A., Mutlu, O., Gibbons, P. B., Mowry, T. C. (2015). "Fast Bulk Bitwise AND and OR in DRAM." *IEEE Computer Architecture Letters*, 14(2).

6. Gao, F., Tziantzioulis, G., Wentzlaff, D. (2019). "ComputeDRAM: In-Memory Compute Using Off-the-Shelf DRAMs." *Proceedings of the 52nd Annual IEEE/ACM International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/3352460.3358260](https://dl.acm.org/doi/10.1145/3352460.3358260).

7. Ferreira, J. D., Oliveira, G. F., et al. (2022). "pLUTo: In-DRAM Lookup Tables to Enable Massively Parallel General-Purpose Computation." arXiv: [2104.07699](https://arxiv.org/abs/2104.07699).

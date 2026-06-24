# LPDDR 近存计算（PIM）架构：面向移动端 AI 的演进

> 本文对比了**原始方案**（传统 LPDDR：CPU/NPU 通过内存总线从 DRAM 取数据，受冯诺依曼瓶颈制约）与**演进方案**（LPDDR-PIM：在 DRAM bank 内/旁放置计算单元，减少数据搬运，支持 DRAM+PIM bank 混合分配）在端侧 AI 推理场景下的差异。调研覆盖 2023--2026 年学术会议（ISCA、DAC、Hot Chips、arxiv）与产业进展（三星、JEDEC）。

## 1. 调研范围与方法

**领域界定。** 基于 LPDDR5/LPDDR5X 移动 DRAM 的存内计算（Processing-in-Memory, PIM）架构，目标是加速资源受限终端设备（智能手机、边缘板卡、AR/VR 头显）上的 LLM 推理及其他 AI 负载。核心关注点为：在 DRAM bank 内部或附近嵌入计算单元，利用内部 bank 带宽与外部 I/O 带宽之间的 8 倍差距。

**"原始方案"与"演进方案"的含义。** *原始方案*是标准冯诺依曼存储层次：SoC 的 CPU、NPU 或 iGPU 通过 LPDDR5 接口发起内存请求，以最高 51.2 GB/s（单 x64 通道）的外部 I/O 带宽获取模型权重与激活值，所有计算均在 SoC 片上完成。*演进方案*在每个 DRAM bank（或 bank 组）内放置 SIMD/MAC 处理单元，使 GEMV 及轻量 GEMM 操作能以内部 bank 带宽（高达 409.6 GB/s）就地执行，并由近数据内存控制器（NMC）在标准 DRAM 访问与 PIM 计算之间动态分配 bank。

**来源。** 共 9 项一手来源：4 篇学术论文（arxiv/ISCA 2025--2026）、3 项产业参考（三星 Hot Chips 2023、JEDEC LPDDR6 PIM 路线图）、2 份系统级分析（PIM-AI 架构、Semi Engineering 移动内存报告）。来源类型涵盖学术论文、厂商演示与标准组织公告。

## 2. 问题背景

**系统需要完成的任务。** 在 8--16 GB 移动 DRAM 预算下，运行端侧 LLM 推理（1B--13B 参数），要求可接受的 token 吞吐（>10 tok/s）和能效（<5 J/query）。

**为什么这个领域变难了。** LLM 解码阶段由 memory-bound 的 GEMV 操作主导：每生成一个 token 需完整读取一次模型权重矩阵。7B INT8 模型每 token 需读取 ~7 GB 权重。按 LPDDR5 外部带宽 51.2 GB/s 计算，需 ~137 ms/token——远超交互式使用的 100 ms 目标。数据搬运能耗占主导：以 ~20 pJ/bit 计算，搬运 7B INT8 权重消耗 ~1.12 J/token，而算术运算本身不到 0.05 J。冯诺依曼瓶颈因此同时表现为延迟墙和能耗墙。

**为什么原始方案已不够用。** 移动端推测解码（speculative decoding）、长 KV cache 的多头注意力、混合专家（MoE）调度等场景不断提高并行内存访问需求，超出单 LPDDR5 通道的承载能力。推测解码将 GEMV 转化为 GEMM，产生类似 batch 的流量，既进一步饱和外部总线，又因 batch 太小而无法让 NPU 达到满利用率。

## 3. 具体问题与瓶颈证据

1. **外部带宽仅为内部 bank 带宽的 1/8** --- 单颗 x64 LPDDR5 芯片提供 51.2 GB/s 外部 I/O，但内部全 bank 带宽达 409.6 GB/s。这 8 倍差距意味着 PIM 对数据局部化操作可获得理论 8 倍的有效带宽 [LP-Spec]。

2. **数据搬运主导能耗** --- 片外数据传输消耗 ~20 pJ/bit，而 DRAM 内部搬运仅 ~3 pJ/bit（片外的 15%）。对 7B 模型而言，每 token 分别为 ~1.12 J（片外）和 ~0.17 J（片内）[LP-Spec, PIM-AI]。

3. **推测推理打破 GEMV 优化的 PIM 假设** --- 推测长度从 1 增加到 16 时，传统 PIM 的延迟和能效优势急剧下降，因为 GEMV 变为 GEMM，需要数据复用模式，而 per-bank 向量单元无法利用 [LP-Spec]。

4. **现有边缘 PIM 存在三项结构性缺陷** --- (a) 激活 bank 数量有限导致带宽提升不足；(b) 阻塞执行模式使处理器与 PIM 无法同时工作；(c) 固定数据映射导致计算单元利用率失衡 [CD-PIM]。

5. **实际带宽远低于峰值** --- LPDDR5X 最差情况下的实际带宽可比厂商标称峰值低 50%，进一步扩大了 PIM 需要弥补的有效带宽缺口 [Fraunhofer/SemiEngineering]。

### 瓶颈数据

| 场景 | 外部带宽 | 内部带宽 | 差距 | 来源 |
|---|---|---|---|---|
| LPDDR5 x64 单通道 | 51.2 GB/s | 409.6 GB/s | 8x | [LP-Spec] |
| LPDDR5X x64 双 die | 68 GB/s | ~512 GB/s | ~7.5x | [PIM-AI] |
| 7B INT8 单 token 权重搬运 | 137 ms（外部） | ~17 ms（内部） | 8x 延迟 | 推算 |
| 每 bit 能耗：片外 vs 片内 | ~20 pJ/bit | ~3 pJ/bit | 6.7x 能耗 | [LP-Spec] |

## 4. 架构对比：原始方案 vs 演进方案

**原始方案 --- 传统 LPDDR（冯诺依曼架构）**

```
    +-------------------+
    |  移动 SoC          |
    |  +------+ +-----+ |
    |  | CPU  | | NPU | |
    |  +------+ +-----+ |
    |       |      |     |
    |  +----+------+--+  |
    |  | 内存控制器     |  |
    |  +-------+------+  |
    +---------|-----------+
              | LPDDR5 I/O 总线 (51.2 GB/s)
              |
    +---------v-----------+
    |  LPDDR5 模块         |
    |  +--+ +--+ +--+ +--+|
    |  |Bk| |Bk| |Bk| |Bk||  Bank 0..15
    |  | 0| | 1| | 2| |..||  （仅数据存储）
    |  +--+ +--+ +--+ +--+|
    |                      |
    |  内部带宽: 409.6 GB/s（不可利用）
    |  外部带宽: 51.2 GB/s（瓶颈）
    +----------------------+

    数据流: 权重数据路径 Bank -> I/O 总线 ->
           SoC -> ALU -> 结果写回 DRAM
    所有计算在 SoC 侧完成。
```

*原始方案：所有数据必须经过窄外部 I/O 总线。内部 bank 带宽被浪费。*

**演进方案 --- 混合 LPDDR5-PIM（LP-Spec 架构）**

```
    +-------------------+
    |  移动 SoC          |
    |  +------+ +-----+ |
    |  | CPU  | | NPU | |
    |  +------+ +-----+ |
    |       |      |     |
    |  +----+------+--+  |
    |  | 内存控制器     |  |
    |  | * + NMC      |  |  * 近数据内存控制器
    |  +-------+------+  |
    +---------|-----------+
              | LPDDR5 I/O 总线 (51.2 GB/s)
              |
    +---------v-----------+
    |  * 混合 LPDDR5-PIM 模块                       |
    |                                              |
    |  DRAM Rank（标准访问）                         |
    |  +--+ +--+ +--+ +--+                        |
    |  |Bk| |Bk| |Bk| |Bk|  （权重供 NPU 使用）    |
    |  | 0| | 1| | 2| |..+                        |
    |  +--+ +--+ +--+ +--+                        |
    |                                              |
    |  * PIM Rank（可计算）                          |
    |  +--------+ +--------+ +--------+ +--------+|
    |  |Bk + MPU| |Bk + MPU| |Bk + MPU| |Bk+MPU ||
    |  | 0  SIMD| | 1  SIMD| | 2  SIMD| |.. SIMD||
    |  | INT8   | | INT8   | | INT8   | | INT8   ||
    |  +--------+ +--------+ +--------+ +--------+|
    |  * 8 个 MPU 服务 16 个 bank（每 MPU 2 bank）   |
    |  * 每个 MPU: 4x 32-wide SIMD ALU             |
    |  * 内部带宽: 409.6 GB/s（现已利用）            |
    |                                              |
    |  * DAU: DRAM <-> PIM 动态数据迁移             |
    |  * DTP: 草稿 token 剪枝（推测推理）           |
    +----------------------------------------------+

    数据流: PIM bank 以 409.6 GB/s 就地计算 GEMV；
    NPU 通过 DRAM Rank 处理 GEMM；
    * NMC 协调 NPU + PIM 并行执行。
```

*演进方案：嵌入 PIM bank 的处理单元（MPU）利用 8 倍内部带宽。近数据内存控制器（NMC）支持动态 bank 分配与 NPU-PIM 并行执行。`*` 标记新增/变化部分。*

## 5. 演进方案的改善与未解决问题

### 改善之处

- **带宽墙** --- PIM 以内部 bank 带宽（409.6 GB/s vs 51.2 GB/s 外部）计算 GEMV，对 memory-bound 解码操作可获得高达 8 倍有效带宽 [LP-Spec, CD-PIM]。

- **能耗墙** --- DRAM 内部数据搬运仅为片外传输成本的 15%（~3 vs ~20 pJ/bit），LP-Spec 实现 7.56 倍能效提升，PIM-AI 相比移动 SoC 基线实现 10--20 倍每 token 能耗下降 [LP-Spec, PIM-AI]。

- **推测推理的 GEMM 问题** --- LP-Spec 的混合 DRAM+PIM rank 设计配合动态负载调度，将 GEMM 卸载到 NPU、PIM 同时处理 GEMV，相比纯 NPU 基线性能提升 13.21 倍 [LP-Spec]。

- **Bank 利用率** --- CD-PIM 的跨分区伪 bank 设计在每个访问周期内激活 4 倍 bank，在边缘平台上实现 14.6 倍解码加速 [CD-PIM]。

- **边缘部署功耗** --- 三星 LPDDR-PIM 通过消除支持操作的往返数据搬运，相比传统 DRAM 访问模式节省 72% 功耗 [三星 Hot Chips 2023]。

### 未解决问题

- **预填充（encoding）阶段仍受计算约束** --- PIM 擅长 memory-bound 的 GEMV 但无法加速 compute-bound 的 GEMM 预填充；PIM-AI 报告编码延迟约为 GPU 的 3 倍 [PIM-AI]。

- **精度与算子支持有限** --- 当前 PIM 处理单元支持 INT8/FP16 MAC 操作；复杂运算（softmax、layer norm、非线性激活）仍需在 SoC 上执行，混合负载需要数据往返。

- **缺乏标准编程模型** --- 各 PIM 设计（LP-Spec、CD-PIM、PIM-AI、三星 PIM）各自使用专有指令集和数据布局约定；尚无统一 ISA 或编译器工具链。

- **容量折中** --- 分配给 PIM 计算的 bank 不能同时作为标准 DRAM 容量使用，在容量与算力之间产生张力，DAU 需持续再平衡。

- **持续 PIM 运算的散热约束** --- 在 DRAM die 上增加处理单元提高了功率密度；在移动热包络（3--5 W 封装）下持续 PIM 计算可能需要降频，侵蚀理论增益。

## 6. 对比表

| 维度 | 原始方案（传统 LPDDR） | 演进方案（LPDDR-PIM） | 提升幅度 | 来源 |
|---|---|---|---|---|
| GEMV 有效带宽 | 51.2 GB/s（外部 I/O） | 409.6 GB/s（内部 bank） | 8x | [LP-Spec] |
| 解码吞吐（LLM 推测推理） | 1x（NPU 基线） | 13.21x（LP-Spec NPU+PIM） | +13.21x | [LP-Spec] |
| 能效（tokens/J） | 0.13 tok/J (RTX 3090) / 4.3 tok/J（移动 NPU） | 32.6 tok/J（LP-Spec） | 7.56x vs NPU | [LP-Spec] |
| 每 bit 数据搬运能耗 | ~20 pJ/bit（片外） | ~3 pJ/bit（DRAM 内部） | 6.7x 下降 | [LP-Spec] |
| 边缘解码加速 | 1x（GPU-only, Jetson） | 14.6x（CD-PIM, LLaMA-13B） | +14.6x | [CD-PIM] |
| 功耗 vs 传统 DRAM 访问 | 100%（基线） | 28%（三星 LPDDR-PIM） | -72% | [三星 HC 2023] |
| PIM die 面积开销 | 0% | 32 Gb LPDDR5 die 的 0.8% | 极小 | [CD-PIM] |
| tokens/s 提升（移动端 7B） | 19 tok/s（LPDDR5X SoC） | 提升 25--49.6%（PIM-AI） | +25--49.6% | [PIM-AI] |

## 7. 一词概括

**近数据**（Near-data） --- LPDDR-PIM 将计算从 SoC 转移到存储 die，利用内部与外部带宽的 8 倍差距打破冯诺依曼数据搬运瓶颈，同时保持 LPDDR 封装形式与接口兼容性。

## 8. 开放问题与注意事项

- **JEDEC 标准化时间表** --- JEDEC 于 2026 年 4 月宣布即将完成 LPDDR6 PIM 正式标准，但目前尚无已批准规范；早期实现均为厂商专有且互不兼容。
- **编译器与软件生态** --- 尚无生产级编译器能自动将工作负载分配到 SoC 与 PIM 之间；现有方案需手动标注或定制调度（如 LP-Spec 的 DTP、CD-PIM 的模式切换）。
- **GEMM 扩展性** --- 随着端侧 batch 增大（多 agent、更长推测序列），GEMV 到 GEMM 的转折点随之移动；当前为 4--16 token 推测长度优化的 PIM 架构未来可能需要重新调优。
- **内存一致性** --- 独立于 SoC 缓存层次运行的 PIM bank 带来一致性挑战；LP-Spec 的 NMC 通过串行化访问解决但可能限制多通道扩展。
- **安全隐患** --- 计算期间驻留在 PIM bank 中的模型权重可能遭受物理侧信道攻击（类 rowhammer）；尚无针对 PIM 的威胁模型分析。
- **移动设备上的散热验证** --- 所有已发表结果基于仿真或 FPGA 原型；真实移动功耗包络下的硅验证散热与性能数据仍属空白。

## 9. 参考文献

1. **LP-Spec** --- Xu et al., 2025. "LP-Spec: Leveraging LPDDR PIM for Efficient LLM Mobile Speculative Inference with Architecture-Dataflow Co-Optimization." ISCA 2025 / arxiv 2508.07227. URL: https://arxiv.org/abs/2508.07227
2. **CD-PIM** --- Authors, 2025. "CD-PIM: A High-Bandwidth and Compute-Efficient LPDDR5-Based PIM for Low-Batch LLM Acceleration on Edge-Device." arxiv 2601.12298. URL: https://arxiv.org/abs/2601.12298
3. **PIM-AI** --- Authors, 2024. "PIM-AI: A Novel Architecture for High-Efficiency LLM Inference." arxiv 2411.17309. URL: https://arxiv.org/abs/2411.17309
4. **三星 PIM at Hot Chips 2023** --- Samsung, 2023. "PIM/PNM for Transformer based AI." Hot Chips 35 报告. URL: https://www.hc2023.hotchips.org/assets/program/conference/day1/PIM/23_HC35_PIM_PNM_Samsung_final.pdf
5. **三星 LPDDR-PIM 公告** --- Samsung Global Newsroom, 2023. "Samsung Brings In-Memory Processing Power to Wider Range of Applications." URL: https://news.samsung.com/global/samsung-brings-in-memory-processing-power-to-wider-range-of-applications
6. **JEDEC LPDDR6 PIM 路线图** --- JEDEC, 2026. "JEDEC Previews LPDDR6 Roadmap Expanding LPDDR into Data Centers and Processing-in-Memory." URL: https://www.jedec.org/news/pressreleases/jedec%C2%AE-previews-lpddr6-roadmap-expanding-lpddr-data-centers-and-processing-memory
7. **PIM-SHERPA** --- Authors, 2026. "PIM-SHERPA: Software Method for On-device LLM Inference by Resolving PIM Memory Attribute and Layout Inconsistencies." arxiv 2603.09216. URL: https://arxiv.org/abs/2603.09216
8. **三星 PIM IEEE Spectrum** --- IEEE Spectrum, 2023. "Samsung Speeds AI With Processing in Memory." URL: https://spectrum.ieee.org/samsung-ai-memory-chips
9. **LPDDR 与边缘 AI** --- Semi Engineering, 2025. "LPDDR Memory Is Key For On-Device AI Performance." URL: https://semiengineering.com/lpddr-memory-is-key-for-on-device-ai-performance/

# 分级内存管理与页面放置优化

> 本文对比了传统的静态硬件延迟页面放置方案与演进后的运行时延迟感知动态页面放置方案在分级内存系统中的应用。调研覆盖 2022–2025 年间的学术成果（SOSP、ASPLOS、OSDI、MICRO）及内核社区进展，重点关注 CXL 异构内存场景。

## 1. 范围与方法

**领域界定。** 面向多层级、不同延迟和带宽特性的内存系统的操作系统级内存管理——具体指本地 DDR DRAM（快速）与 CXL 挂载 DRAM（远端、高延迟、大容量）共存的场景。核心问题是：在真实负载条件下，如何决定每个页面驻留在哪一层，以最大化应用吞吐量。

**"原始方案"与"演进方案"的含义。** *原始方案*指基于静态硬件延迟的页面放置：操作系统将最热（访问最频繁）的页面塞入硬件标称延迟最低的层级（本地 DDR DRAM），使用固定热度阈值和 NUMA balancing 驱动的升降级。*演进方案*指运行时延迟感知的动态页面放置：操作系统监测各层实际访问延迟（含排队延迟、竞争、内存级并行度等因素），动态地在各层间重新分配页面以平衡负载延迟，并根据工作负载阶段变化自适应调整阈值。

**资料来源。** 14 篇主要文献：8 篇学术论文（SOSP 2024、ASPLOS 2023/2025、OSDI 2025、MICRO 2024、HotOS 2025），3 篇 Linux 内核资料（MGLRU 文档、LWN 分级内存峰会报告、TPP 补丁集），2 篇业界参考（Intel CXL 分级白皮书、Samsung CXL 原型性能特征报告），1 篇参数调优预印本。来源涵盖同行评审系统论文、内核文档和厂商工程报告。

## 2. 问题背景

**系统需要做什么。** 在本地 DDR DRAM（空载 80–100 ns）与 CXL 挂载 DRAM（空载 170–250 ns，容量大 2–8 倍）共存的服务器和工作站中，管理 2–3 层内存间的页面放置。目标是在充分利用聚合容量的同时，保持应用可见的内存访问延迟尽可能低。

**为什么这个领域变得困难。** CXL 内存在 DRAM 与存储之间引入了一个新层级：像 DRAM 一样字节寻址，但基础延迟高 2–3 倍，且经由 PCIe/CXL 链路连接独立的内存控制器。在负载下，内存控制器排队、互连竞争以及共驻工作负载的干扰，导致各层的*运行时*访问延迟偏离其*硬件标称*延迟。当默认层（本地 DDR）的控制器过载时，它反而成为瓶颈，而 CXL 层却利用不足。

**为什么原始方案不再够用。** 静态放置假设硬件标称延迟排序不变：本地 DDR 总是比 CXL 快。Colloid [SOSP 2024] 表明，在中等内存互连竞争下，默认层的实际访问延迟膨胀至 CXL 层的 2.5 倍。在此条件下，最先进的分级系统性能比最优方案差 2.3 倍 [Colloid]。

## 3. 具体问题与瓶颈证据

1. **静态延迟排序在竞争下失效** — 所有先前的分级系统（HeMem、TPP、MEMTIS）使用相同的页面放置算法：将最热页面塞入硬件标称延迟最低的层级。这忽略了运行时延迟取决于队列占用率和请求速率，而非仅仅是硬件传播延迟 [Colloid/SOSP 2024]。

2. **默认层在负载下成为瓶颈** — 当内存互连竞争从 1× 升至 2× 时，默认（DDR）层的访问延迟增加 2.5 倍，而 CXL 层延迟相对稳定。最优页面分布从"所有热页在 DDR"转变为跨层平衡分配，但静态策略无法检测或响应这一变化 [Colloid/SOSP 2024]。

3. **仅凭热度无法完整反映性能影响** — 访问频率（"热度"）未能捕捉内存级并行度（MLP）。一个访问计数高但负载完全重叠的页面性能影响小，而访问较少但串行化的页面反而关键。仅基于热度的策略对页面排序不当，导致性能比 MLP 感知放置差 12.4 倍 [SoarAlto/OSDI 2025]。

4. **升降级阈值对工作负载敏感** — Linux 分级管理（TPP、HMSDK）的默认阈值参数仅针对一类工作负载调优。对同一系统使用贝叶斯优化可获得比默认值 2 倍的性能提升，比最先进系统高 1.56 倍，说明固定阈值浪费了大量性能空间 [Karimzadeh et al., arXiv 2025]。

5. **迁移抖动浪费带宽** — 对瞬态热页的激进升级、随后立即降级，制造了迁移风暴，消耗内存带宽却无净性能增益。Jenga [arXiv 2025] 和 ARMS [arXiv 2025] 将抑制抖动作为一等设计目标。

### 瓶颈证据

| 场景 | 指标 | 数值 | 来源 |
|---|---|---|---|
| DDR 层在 2× 互连竞争下 | 运行时访问延迟 vs. 空载 | 膨胀 2.5 倍 | [Colloid/SOSP 2024] |
| TPP/HeMem/MEMTIS 在竞争下 | 吞吐量 vs. 最优放置 | 最差 2.3 倍 | [Colloid/SOSP 2024] |
| 默认 TPP vs. 调优后 TPP | 应用吞吐量 | 2.3 倍差距（ARMS 比默认 TPP 提升 2.3 倍） | [ARMS, arXiv 2025] |
| 基于热度 vs. MLP 感知放置 | 应用运行时间 | 最多慢 12.4 倍 | [SoarAlto/OSDI 2025] |
| HeMem/HMSDK 默认参数 vs. 贝叶斯优化 | 吞吐量 | 提升 2 倍 | [Karimzadeh et al., arXiv 2025] |
| NeoMem 硬件辅助 vs. 纯软件分析 | 几何平均加速比 | 1.32–1.67 倍 | [NeoMem/MICRO 2024] |

## 4. 架构：原始方案 vs 演进方案

**原始方案 — 基于静态硬件延迟的页面放置**

```
    +------------------+          +------------------+
    |  应用程序         |          |  应用程序         |
    +------------------+          +------------------+
           |                             |
           | 缺页 / 访问                  | 缺页 / 访问
           v                             v
    +----------------------------------------------+
    |           Linux 内存管理器                      |
    |  (NUMA balancing + MGLRU + 固定阈值)           |
    +----------------------------------------------+
           |                        |
           | 升级 (热页)             | 降级 (冷页)
           | 通过 NUMA hint fault    | 通过 LRU 扫描
           v                        v
    +-----------------+      +-----------------+
    | 第 0 层：DDR    |      | 第 1 层：CXL    |
    | （本地 DRAM）    |      | （CXL 挂载）     |
    | 硬件延迟：       |      | 硬件延迟：       |
    |  80-100 ns      |      |  170-250 ns     |
    +-----------------+      +-----------------+
           |                        |
           |   最热页面 -----> 第 0 层（始终）
           |   冷页面   -----> 第 1 层（始终）
           |
           +--- 假设：第 0 层延迟 < 第 1 层延迟（不变量）
```

*原始方案：页面按访问频率排序；最热页面始终放入硬件标称延迟最低的层级。升级通过 NUMA hint fault，降级通过 MGLRU/kswapd 扫描，使用固定代际阈值。*

**演进方案 — 运行时延迟感知的动态页面放置**

```
    +------------------+          +------------------+
    |  应用程序         |          |  应用程序         |
    +------------------+          +------------------+
           |                             |
           | 缺页 / 访问                  | 缺页 / 访问
           v                             v
    +----------------------------------------------+
    | * 运行时延迟监测器                               |
    |   (每层队列占用率, Little 定律,                  |
    |    PMU 计数器, * CXL 硬件分析器)                 |
    +----------------------------------------------+
           |
           | * 各层负载延迟
           v
    +----------------------------------------------+
    | * 延迟均衡页面放置引擎                            |
    |   (* 排队感知阈值自适应,                         |
    |    * MLP 感知关键性评分,                         |
    |    * 防抖动迁移预算控制)                          |
    +----------------------------------------------+
           |                        |
           | * 迁移（平衡             | * 迁移（平衡
           |   负载延迟）             |   负载延迟）
           v                        v
    +-----------------+      +-----------------+
    | 第 0 层：DDR    |      | 第 1 层：CXL    |
    | （本地 DRAM）    |      | （CXL 挂载）     |
    | * 运行时延迟：   |      | * 运行时延迟：   |
    |   随负载变化     |      |   随负载变化     |
    +-----------------+      +-----------------+
           |                        |
           | * 热页分布到多层以平衡负载延迟
           |
           +--- 原则：min(max(loaded_lat_tier0, loaded_lat_tier1))
```

*演进方案：页面放置以平衡各层运行时（负载）访问延迟为目标。新增/变更元素以 `*` 标记。运行时监测器将排队感知延迟馈入放置引擎，引擎综合考虑 MLP、竞争和迁移成本。*

## 5. 演进方案为何有效，以及尚未解决的问题

### 为何有效

- **静态延迟排序在竞争下失效** — Colloid 的延迟均衡原则直接解决了 DDR 层 2.5 倍延迟膨胀问题，通过在各层间重新分配负载。与 HeMem、TPP、MEMTIS 集成后，分别实现 1.2–2.35 倍吞吐量提升，将三个系统拉至最优方案的 3–13% 以内 [Colloid/SOSP 2024]。

- **仅凭热度无法完整反映性能影响** — SoarAlto 的摊销片外延迟（AOL）指标同时捕获访问延迟和内存级并行度，比仅基于热度的分级设计最多提升 12.4 倍，正确地将串行化（延迟关键）访问优先于可并行化访问 [SoarAlto/OSDI 2025]。

- **升降级阈值对工作负载敏感** — 自适应系统（ARMS、HybridTier）根据观测到的工作负载行为自调阈值，比默认参数基线提升 1.26–2.3 倍，无需手动调参 [ARMS, arXiv 2025]。

- **硬件辅助分析降低开销** — NeoMem 将访问分析下沉至 CXL 端硬件单元（NeoProf），消除软件页表扫描的 CPU 开销，比纯软件分级方案实现 1.32–1.67 倍几何平均加速 [NeoMem/MICRO 2024]。

- **MGLRU 提供更好的回收基础** — Multi-Gen LRU（Linux 6.1 合入）以 4 代际列表和 PTE accessed-bit 扫描取代两链表 active/inactive 模型，在 ChromeOS/Android 上降低 kswapd CPU 占用 40%、低内存杀进程次数降低 85%，为层级降级决策提供更灵敏的基座 [Google/MGLRU, 内核 6.1+]。

### 尚未解决的问题

- **多租户公平性** — 运行时延迟感知放置优化的是聚合吞吐量，当延迟敏感租户与带宽大户共驻时可能被饿死。Equilibria [arXiv 2025] 是面向公平多租户 CXL 分级的早期工作，但尚无生产级方案。

- **迁移成本非零** — 每次页面迁移消耗内存带宽和 TLB shootdown 开销。在工作负载阶段快速切换时，持续再平衡的成本可能抵消更优放置的收益，尤其对写密集负载（脏页迁移代价大）。

- **CXL 延迟因厂商而异** — CXL DRAM 延迟因控制器实现差异显著（Samsung ~170 ns，其他原型 ~250 ns）。针对一款 CXL 设备调优的放置策略，在另一款设备上未必适用。

- **内核缺乏统一的 CXL 分级接口** — 截至 Linux 6.12，分级内存支持依赖打补丁的 NUMA balancing 和 DAMON；没有统一的 CXL 感知分级内核子系统。2024 年 LSFMM 峰会的内存管理分会场已承认这一空白 [LWN]。

## 6. 对比表

| 维度 | 原始（静态硬件延迟） | 演进（运行时延迟感知） | 差异 | 来源 |
|---|---|---|---|---|
| 页面放置依据 | 硬件标称层级延迟（固定） | 运行时负载访问延迟（动态） | 从静态到动态的质变 | [Colloid/SOSP 2024] |
| 2× 竞争下吞吐量 | 比最优差 2.3 倍 | 在最优的 3–13% 以内 | 提升 1.2–2.35 倍 | [Colloid/SOSP 2024] |
| 页面排序指标 | 访问频率（热度） | 摊销片外延迟（AOL），含 MLP | 最多提升 12.4 倍 | [SoarAlto/OSDI 2025] |
| 阈值适配 | 固定，与工作负载无关 | 自调优或贝叶斯优化 | 比默认值提升 1.56–2 倍 | [ARMS; Karimzadeh et al. 2025] |
| 访问分析开销 | 软件页表扫描（CPU 开销大） | CXL 端硬件辅助分析（NeoProf） | 几何均值加速 32–67% | [NeoMem/MICRO 2024] |
| 降级基础 | 两链表 LRU（active/inactive） | MGLRU 4 代际 + PTE 扫描 | kswapd CPU 降低 40% | [MGLRU/内核 6.1] |
| 迁移控制 | 无显式抖动防护 | 预算限制、防抖策略 | 消除迁移风暴 | [Jenga; ARMS 2025] |
| CXL 消费级就绪度 | 不适用（仅服务器） | AMD 消费级 CXL 3–5 年内；Win11 仅基础枚举 | 桌面端尚未可用 | [Tom's Hardware; AMD 2024] |

## 7. 一词概括

**竞争感知（Contention-aware）。**

## 8. 开放问题

- **延迟均衡与 MLP 感知能否统一？** Colloid 平衡负载延迟；SoarAlto 使用含 MLP 的摊销片外延迟。目前没有系统同时融合两种信号——这样做可在单一放置决策中同时应对排队竞争和指令级并行度效应。

- **分级管理应如何与内存压缩（zswap/zram）交互？** 当前分级研究假设页面未压缩。在内存受限的系统（工作站、边缘设备）上，DDR 中的压缩页面可能优于 CXL 中的未压缩页面——解压缩与 CXL 访问之间的延迟权衡尚未被探索。

- **CXL 3.0/4.0 的 Fabric 级交换是否会改变分级模型？** CXL 3.0 引入跨主机共享的 Fabric 挂载内存池。单主机分级策略可能与 Fabric 级分配冲突，需要 OS 与 Fabric 管理器之间的协调。

- **异构内存分级的正确内核抽象是什么？** 2024 年 LSFMM 峰会确定了需要将热度检测与页面移动解耦，并暴露一个"热内存抽象层"，支持可插拔的检测后端（PTE 位、PMU、CXL 硬件计数器）。API 设计尚无共识。

- **学习型模型能否替代手调启发式实现页面放置？** 贝叶斯优化已展示比默认值 2 倍的收益。基于强化学习的放置策略可持续适应，但模型推理延迟须在亚微秒级，以免成为放置决策的主导开销。

- **分级管理在新兴工作负载（LLM 推理、图分析）上表现如何？** LLM 的 KV cache 和图遍历具有不规则、阶段性的访问模式，同时压力测试热度检测和迁移带宽。在这些工作负载下基准测试分级系统仍是开放领域。

## 9. 参考文献

1. **[Colloid/SOSP 2024]** M. Vuppalapati, R. Agarwal. "Tiered Memory Management: Access Latency is the Key!" *Proc. ACM SIGOPS 30th Symposium on Operating Systems Principles (SOSP '24)*, 2024 年 11 月. DOI: [10.1145/3694715.3695968](https://dl.acm.org/doi/10.1145/3694715.3695968)

2. **[TPP/ASPLOS 2023]** H. Al Maruf et al. "TPP: Transparent Page Placement for CXL-Enabled Tiered-Memory." *Proc. 28th ACM ASPLOS*, 2023. DOI: [10.1145/3582016.3582063](https://dl.acm.org/doi/10.1145/3582016.3582063)

3. **[M5/ASPLOS 2025]** "M5: Mastering Page Migration and Memory Management for CXL-based Tiered Memory Systems." *Proc. 30th ACM ASPLOS*, 2025. DOI: [10.1145/3676641.3711999](https://dl.acm.org/doi/abs/10.1145/3676641.3711999)

4. **[HybridTier/ASPLOS 2025]** K. Song et al. "HybridTier: An Adaptive and Lightweight CXL-Memory Tiering System." *Proc. 30th ACM ASPLOS*, 2025. [PDF](https://www.sihangliu.com/docs/hybridtier_asplos25.pdf)

5. **[SoarAlto/OSDI 2025]** J. Liu, H. Hadian, H. Xu, H. Li. "Tiered Memory Management Beyond Hotness." *Proc. 19th USENIX OSDI*, 2025 年 7 月. [USENIX](https://www.usenix.org/conference/osdi25/presentation/liu)

6. **[NeoMem/MICRO 2024]** Z. Zhou et al. "NeoMem: Hardware/Software Co-Design for CXL-Native Memory Tiering." *Proc. 57th IEEE/ACM MICRO*, 2024. DOI: [10.1109/MICRO61859.2024.00111](https://dl.acm.org/doi/10.1109/MICRO61859.2024.00111)

7. **[Jenga 2025]** R. Kadekodi et al. "Jenga: Responsive Tiered Memory Management without Thrashing." *arXiv:2510.22869*, 2025. [arXiv](https://arxiv.org/abs/2510.22869)

8. **[ARMS 2025]** "ARMS: Adaptive and Robust Memory Tiering System." *arXiv:2508.04417*, 2025. [arXiv](https://arxiv.org/abs/2508.04417)

9. **[Karimzadeh et al. 2025]** "From Good to Great: Improving Memory Tiering Performance Through Parameter Tuning." *arXiv:2504.18714*, 2025 年 4 月. [arXiv](https://arxiv.org/abs/2504.18714)

10. **[MGLRU/内核 6.1]** Y. Zhao (Google). "Multi-Gen LRU." *Linux 内核文档*，合入 v6.1，2022. [kernel.org](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)

11. **[LWN/LSFMM 2024]** J. Corbet. "Better support for locally-attached-memory tiering." *LWN.net*, 2024. [LWN](https://lwn.net/Articles/974126/)

12. **[Intel CXL Tiering]** Intel. "Advantages of Managing the CXL Memory Tier in Hardware." 技术白皮书, 2024. [PDF](https://cdrdv2-public.intel.com/886601/advantages-managing-cxl-memory-tier-in-hardware-technical-paper.pdf)

13. **[HotOS 2025]** "Tolerate It if You Cannot Reduce It: Handling Latency in Tiered Memory." *Proc. HotOS 2025*. [PDF](https://sigops.org/s/conferences/hotos/2025/papers/hotos25-72.pdf)

14. **[AMD CXL Consumer]** "AMD Working to Bring CXL Memory Tech to Future Consumer CPUs." *Tom's Hardware*, 2024. [链接](https://www.tomshardware.com/news/amd-working-to-bring-cxl-technology-to-consumer-cpus)

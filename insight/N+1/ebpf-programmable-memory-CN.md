# 基于 eBPF 的可编程内核内存策略

> 本文对比了 Linux 系统中**原始的静态内核内存管理方案**与**演进的 eBPF 可编程内存策略方案**。调研涵盖学术界（USENIX ATC、ASPLOS、SIGCOMM、LPC）及内核社区（LSFMMBPF、LWN）在 2019–2025 年间的相关进展。

## 1. 范围与方法

**领域定义。** Linux 内核空间内存管理策略的定制化 —— 具体涉及大页（huge page）分配、页缓存淘汰、预取以及页回收 —— 面向运行内存密集型负载（数据库、分析引擎、超大规模服务）的服务器与数据中心场景。

**"原始方案"与"演进方案"的含义。** *原始方案*指静态编译进内核的内存管理策略集：透明大页（THP）仅提供系统级 `always`/`madvise`/`never` 三挡开关，页缓存采用固定的 LRU/MGLRU 淘汰策略，预取使用硬编码的顺序读启发式，内存压缩由分配失败同步触发。*演进方案*在内核内存管理路径 —— 缺页处理、页缓存准入/淘汰、预取、回收 —— 中插入 eBPF 挂钩点，将策略决策委托给用户空间编写的、按应用粒度加载的 eBPF 程序，这些程序在内核上下文中以原生速度执行，无需编译内核模块或重启。

**来源。** 10 个主要来源：5 篇学术论文（USENIX ATC 2022/2024/2025、SIGCOMM eBPF 研讨会 2024、arxiv 2024–2025），2 个会议报告（LPC 2024、LSFMMBPF 2025），3 个内核/社区参考资料（LWN mTHP 报道、Linux 内核文档、HawkEye ASPLOS 2019）。来源类型涵盖同行评审系统论文、arxiv 预印本、会议幻灯片和内核文档。

## 2. 问题背景

**系统需要做什么。** Linux 内核内存管理器在每次缺页异常和每次内存压力事件中，都需要决定分配哪种页面大小（4 KB、64 KB、2 MB）、从页缓存中淘汰哪些页、何时触发内存压缩、以及预取什么内容 —— 而服务器上同时运行着数百个内存访问模式截然不同的进程。

**为什么这个领域很难。** 现代服务器配备 TB 级 DRAM 和异构内存层次（CXL 附连、NUMA、压缩内存）。TLB 覆盖范围受架构限制（x86 约 1500 条目），因此大页决策直接影响地址转换开销。然而大页代价不低：2 MB 页面因内部碎片浪费内存，分配时的压缩停顿长达 10–500 ms [THP-Stall]，且对需求差异巨大的应用施加统一策略（数据库需要大页；短生命周期微服务则不需要）。

**为什么原始方案不再够用。** Linux THP 是"成本无感知"的：它贪婪地将页面提升为 2 MB，不考虑各应用的 TLB 缺失率，导致小分配负载的内存膨胀高达 2.5 倍 [THP-Bloat]。系统级 `always`/`madvise` 开关无法区分同一主机上的 Redis 实例（受益于大页：吞吐量 +31%）和 Splunk 索引器（受损：性能 -30%）[Percona, Splunk-THP]。修改内核需经历数月的补丁审查周期，快速策略迭代无从实现。

## 3. 具体问题与瓶颈证据

1. **THP 压缩停顿导致延迟尖峰** —— 当内核找不到连续的 2 MB 区域时，同步压缩阻塞缺页线程 10–50 ms，碎片严重时最差可达 500 ms–1 s。数据库的 OSD 线程尤其受影响 [THP-Stall]。

2. **成本无感知的大页分配浪费内存** —— THP 的贪婪提升即使对仅访问少量数据的负载也分配 2 MB 页面，内部碎片率高达 75.6%，内存膨胀 2.5 倍 [THP-Bloat]。CBMM 表明，仅对 TLB 密集区域进行定向提升，即可以显著更少的大页达到相当性能 [CBMM]。

3. **一刀切的页缓存淘汰损失吞吐量** —— Linux 默认 LRU/MGLRU 淘汰策略不考虑应用特定的访问模式。cachebpf 证明通过 eBPF 实现按负载定制的淘汰策略，可获得高达 70% 的吞吐量提升和 58% 的 P99 尾延迟下降 [cachebpf]。

4. **静态预取启发式对多样化 I/O 预测失误** —— Linux 内置的读预取假定顺序访问模式。对于随机或跨步负载（键值存储、图遍历），这浪费 I/O 带宽并污染页缓存。FetchBPF 证明可定制的 eBPF 预取策略在零额外开销下匹配内核内策略性能，同时支持应用特定策略 [FetchBPF]。

5. **mTHP 缺乏按应用粒度的控制** —— 多尺寸 THP（Linux 6.8+）引入了 64 KB 中间尺寸，但控制仍然是系统级的（通过 sysfs）。在 Android 设备上，mTHP 分配成功率在运行 2 小时后从 50% 降至不足 10%，且"内核尚未达到可以自动使用 mTHP 的程度" [LWN-mTHP]。

### 瓶颈证据

| 场景 | 指标 | 数值 | 来源 |
|---|---|---|---|
| 碎片化环境下 THP 压缩 | 最差分配停顿 | 500 ms – 1 s | [THP-Stall] |
| THP always 模式 + 小分配负载 | 内部碎片 / 内存膨胀 | 75.6% 浪费，2.5× 膨胀 | [THP-Bloat] |
| 默认 LRU vs 按负载定制（YCSB） | 吞吐量差距 | 默认低至 70% | [cachebpf] |
| Android 运行 2 小时后 mTHP | 分配成功率 | < 10%（从 50% 下降） | [LWN-mTHP] |
| khugepaged 24 小时扫描开销 | 单次扫描最大延迟 | 6 ms | [THP-Stall] |

## 4. 架构对比：原始方案 vs 演进方案

**原始方案 —— 静态内核内存策略**

```
    +-------------------+
    |  应用程序          |
    |  （无按应用        |
    |   策略输入）       |
    +-------------------+
            |
            | 缺页异常
            v
    +-------------------+       +--------------------+
    |  缺页处理器        | ----> |  THP 决策          |
    |  （内核，固定逻辑） |       |  （系统级          |
    |                   |       |   always/madvise）  |
    +-------------------+       +--------------------+
            |                           |
            | 分配                      | 提升为 2 MB
            v                           v
    +-------------------+       +--------------------+
    |  伙伴分配器        |       |  khugepaged        |
    |  （默认 4 KB）     |       |  （后台扫描，      |
    |                   |       |   固定间隔）        |
    +-------------------+       +--------------------+
            |                           |
            v                           v
    +----------------------------------------------+
    |  页缓存                                      |
    |  LRU/MGLRU 淘汰（全局，固定策略）              |
    |  预读（固定顺序启发式）                        |
    +----------------------------------------------+
            |
            | 内存压力
            v
    +-------------------+
    |  kswapd/kcompactd |
    |  （固定触发阈值）  |
    +-------------------+
```

*原始方案：所有策略决策编译进内核。THP 为系统级，淘汰为全局 LRU，预取为固定预读。不修改内核则无法实现按应用定制。*

**演进方案 —— eBPF 可编程内存策略**

```
    +-------------------+       +------------------------+
    |  应用程序          |       | * 用户空间策略          |
    |  （通过 eBPF      |       |   管理器               |
    |   加载配置文件）    |       |   （DAMON 采样，       |
    +-------------------+       |    按应用配置文件）      |
            |                   +------------------------+
            | 缺页异常                  |
            v                           | * 加载 eBPF 程序
    +-------------------+               v
    | * eBPF 挂钩       |       +------------------------+
    |   缺页处理器      | <---- | * eBPF 页面大小        |
    |   （内核 +        |       |   选择器               |
    |    BPF 分发）     |       |   （按进程，           |
    +-------------------+       |    成本收益分析：       |
            |                   |    4KB/64KB/2MB/32MB） |
            | 分配              +------------------------+
            v
    +-------------------+       +------------------------+
    |  伙伴分配器        |       | * eBPF 压缩            |
    |  （多尺寸）        | <---- |   触发器               |
    |                   |       |   （自适应阈值）        |
    +-------------------+       +------------------------+
            |
            v
    +----------------------------------------------+
    | * 带 eBPF 挂钩的页缓存                         |
    |   cachebpf：按 cgroup 淘汰策略                 |
    |   （按应用 LFU/MRU/Hyperbolic）               |
    |   FetchBPF：自定义预取策略                     |
    |   （按负载 stride/ML）                        |
    +----------------------------------------------+
            |
            | 内存压力
            v
    +-------------------+       +------------------------+
    | * 可编程回收路径    | <---- | * eBPF 回收策略        |
    |   （kswapd + BPF） |       |   （PROTECT/EVICT/PASS |
    |                   |       |    逐页裁决）           |
    +-------------------+       +------------------------+
```

*演进方案：在缺页、页缓存和回收路径中插入 eBPF 挂钩，实现按应用策略，无需重新编译内核。新增/变更元素以 `*` 标记。用户空间管理器基于 DAMON 采样加载配置文件；eBPF 程序在内核中以原生速度执行。*

## 5. 演进方案的优势，以及尚未解决的问题

### 优势

- **THP 压缩停顿** —— eBPF-mm 仅对 TLB 密集区域（通过 DAMON 采样识别）选择性提升为 2 MB，其余使用 64 KB 或 4 KB，避免不必要的压缩，同时保持可比的 TLB 缺失率。CBMM 的成本收益模型表明，定向提升以显著更少的大页即可获得同等性能 [CBMM, eBPF-mm]。

- **成本无感知的大页分配** —— 按进程的 eBPF 程序根据实时碎片状态计算提升成本，并与各区域的 TLB 缺失收益进行比较，做出经济理性的决策而非贪婪决策 [eBPF-mm]。

- **一刀切的页缓存淘汰** —— cachebpf 的五个 eBPF 挂钩点（初始化、淘汰、准入、访问、移除）支持按 cgroup 策略：YCSB 使用 LFU（吞吐量 +37%），文件搜索使用 MRU（吞吐量 2 倍），且按应用隔离防止相互干扰。仅修改了 210 行核心页缓存代码 [cachebpf]。

- **静态预取启发式** —— FetchBPF 允许按负载部署 stride、Leap 或基于 ML 的预取策略，无需内核补丁，在零额外开销下匹配内核内策略性能 [FetchBPF]。

- **部署速度** —— eBPF 程序可在运行时加载和卸载，无需重启或编译内核模块，支持在生产环境中对内存策略进行 A/B 测试。PageFlex 的策略委托仅带来 < 1% 的应用减速 [PageFlex]。

### 尚未解决的问题

- **eBPF 验证器约束限制策略复杂度** —— BPF 验证器强制有界循环和有限栈深度，阻止在 eBPF 程序中进行复杂 ML 推理或深层数据结构遍历。策略必须保持计算简单。

- **eBPF-mm 挂钩尚未合入上游** —— 截至 Linux 6.12，用于大页选择的缺页 eBPF 挂钩尚未合入主线。eBPF-mm 和 PageFlex 仍为研究原型 [eBPF-mm, PageFlex]。

- **按 cgroup 隔离的开销** —— cachebpf 的按 cgroup 元数据增加 0.4%–1.2% 内存开销和最多 1.7% CPU 开销，在数百个 cgroup 规模下可能累积 [cachebpf]。

- **依赖采样的策略需要负载稳定性** —— eBPF-mm 依赖 DAMON 采样来识别热点区域；具有阶段变化或突发访问模式的负载可能需要持续重新采样，增加开销和延迟。

- **安全攻击面扩大** —— 将 eBPF 程序附加到缺页和回收路径扩大了内核攻击面。有缺陷的淘汰策略可能导致数据丢失；恶意策略可能窃取页面内容。

## 6. 对比表

| 维度 | 原始方案（静态内核策略） | 演进方案（eBPF 可编程策略） | 改进幅度 | 来源 |
|---|---|---|---|---|
| 页面大小选择粒度 | 系统级（always/madvise/never） | 按进程、按内存区域（4 KB/64 KB/2 MB/32 MB） | 区域级 vs 系统级 | [eBPF-mm] |
| 页缓存淘汰吞吐量（YCSB） | 基线（Linux LRU/MGLRU） | 吞吐量 +70%，P99 延迟 −58% | 最高 1.7× 吞吐量 | [cachebpf] |
| 策略部署延迟 | 内核补丁 → 审查 → 发布（数月） | 运行时 eBPF 加载（秒级），无需重启 | 数月 → 秒级 | [eBPF-mm, PageFlex] |
| 策略委托开销（应用减速） | 0%（编译进内核） | < 1%（PageFlex 实测） | 可忽略 | [PageFlex] |
| 核心内核代码修改量（页缓存） | 不适用（整体式） | 约 210 行（cachebpf） | 极小修改量 | [cachebpf] |
| 按 cgroup 策略隔离 | 不支持 | 按 cgroup 淘汰，按负载预取 | 完全隔离 | [cachebpf, FetchBPF] |
| 策略元数据内存开销 | 0% | 每 cgroup 0.4%–1.2% | 少量开销 | [cachebpf] |
| 预取可定制性 | 固定顺序预读 | 任意策略（stride、Leap、ML）按负载定制 | 按负载特化 | [FetchBPF] |

## 7. 一词概括

**Programmable**（可编程） —— 内核内存管理从硬编码的、编译时确定的策略，转变为运行时可加载的、按应用粒度的 eBPF 程序。这些程序在内核中以原生速度执行，实现成本感知的大页选择、按负载定制的淘汰策略和自定义预取，无需修改内核或重启。

## 8. 开放问题与注意事项

- **上游合入时间线不明** —— eBPF-mm 的缺页挂钩、cachebpf 的淘汰挂钩和 FetchBPF 的预取挂钩截至 2025 年中均为研究原型，尚未合入 Linux 主线。LSFMMBPF 2025 峰会讨论了可编程 MM，但未公布具体合入计划 [LSFMMBPF-2025]。
- **验证器限制 vs 策略表达力** —— eBPF 验证器的有界循环和栈深度约束可能阻止实现复杂策略（如基于 ML 的页面替换）。BPF-to-BPF 调用和 map 等绕行方案增加了复杂度。
- **采样驱动的策略需要负载稳定性** —— eBPF-mm 依赖 DAMON 采样热点区域；具有阶段变化或突发访问模式的负载可能需要持续重新采样，带来额外开销和延迟。
- **多个 eBPF 内存挂钩间的交互** —— 当缺页挂钩、淘汰挂钩和预取挂钩同时激活时，策略交互可能导致病态行为（如预取的页面被淘汰策略立即回收）。尚无发表的研究解决协调性多挂钩策略问题。
- **基准测试的代表性** —— eBPF-mm 仅评估了 astar（SPEC CPU 2006）；cachebpf 评估了 YCSB 和文件搜索。具有更复杂内存模式的生产负载（JVM 垃圾回收、容器编排）尚未得到测试。
- **CXL 与分层内存** —— LPC 2024 报告明确指出可编程 eBPF 挂钩应扩展到 CXL 内存分层的页面放置 [LPC-2024]，但尚无 eBPF 驱动分层放置的原型实现。

## 9. 参考文献

1. **eBPF-mm** — Mores K., Psomadakis S., Goumas G.（希腊国立雅典理工大学），2024. "eBPF-mm: Userspace-guided memory management in Linux with eBPF." arxiv 2409.11220. URL: https://arxiv.org/abs/2409.11220
2. **cachebpf** — Zussman T., Zarkadas I., Carin J., Cheng A., Franke H., Pfefferle J., Cidon A.（哥伦比亚大学、IBM），2025. "Cache is King: Smart Page Eviction with eBPF." arxiv 2502.02750. URL: https://arxiv.org/abs/2502.02750
3. **FetchBPF** — Cao X., Patel S., Lim S.-Y., Han X., Pasquier T., 2024. "FetchBPF: Customizable Prefetching Policies in Linux with eBPF." USENIX ATC 2024, pp. 369–378. URL: https://www.usenix.org/conference/atc24/presentation/cao
4. **PageFlex** — Yelam A., Wu K., Guo Z., Yang S., Shashidhara R., Xu W., Novakovic S., Snoeren A.C., Keeton K.（Google、UC San Diego、UW），2025. "PageFlex: Flexible and Efficient User-space Delegation of Linux Paging Policies with eBPF." USENIX ATC 2025. URL: https://www.usenix.org/conference/atc25/presentation/yelam
5. **CBMM** — Mansi A. 等，2022. "CBMM: Financial Advice for Kernel Memory Managers." USENIX ATC 2022. URL: https://www.usenix.org/system/files/atc22-mansi.pdf
6. **HawkEye** — Panwar A., Bansal S., Gopinath K., 2019. "HawkEye: Efficient Fine-grained OS Support for Huge Pages." ASPLOS 2019. URL: https://dl.acm.org/doi/10.1145/3297858.3304064
7. **LPC-2024** — Skarlatos D., Zhao K.（卡内基梅隆大学），2024. "Towards Programmable Memory Management with eBPF." Linux Plumbers Conference 2024, eBPF Track. URL: https://lpc.events/event/18/contributions/1932/
8. **LWN-mTHP** — Corbet J., 2024. "Two talks on multi-size transparent huge page performance." LWN.net. URL: https://lwn.net/Articles/974826/
9. **LSFMMBPF-2025** — Linux Foundation, 2025. "Linux Storage, Filesystem, MM & BPF Summit 2025." URL: https://events.linuxfoundation.org/archive/2025/lsfmmbpf/
10. **SIGCOMM-eBPF-2024** — Pandit S. 等，2024. "Custom Page Fault Handling With eBPF." ACM SIGCOMM 2024 Workshop on eBPF and Kernel Extensions. URL: https://dl.acm.org/doi/10.1145/3672197.3673432

---

**行文中简写说明：** [THP-Stall] = 生产 Ceph 集群的博客测量数据与 /proc/vmstat 数据；[THP-Bloat] = Percona THP 分析；[Percona] = Percona THP Refresher；[Splunk-THP] = Splunk THP 官方建议。补充参考如下：

- **[THP-Stall]** — Loke.dev, 2024. "The Compaction Stall: What Nobody Tells You About Linux Transparent Huge Pages." URL: https://loke.dev/blog/linux-thp-compaction-stall-performance
- **[THP-Bloat]** — Percona, 2024. "Transparent Huge Pages Refresher." URL: https://www.percona.com/blog/transparent-huge-pages-refresher/

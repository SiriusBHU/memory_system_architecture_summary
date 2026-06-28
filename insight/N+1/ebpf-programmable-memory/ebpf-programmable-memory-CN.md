# 端侧可编程 / 自适应内存管理

> 本文对比端侧（手机、平板、笔电、边缘开发板）OS 内存管理中的**原始方案**与**演进方案**。原始方案指内核中固定的、系统级的策略：全有全无的 THP、固定 LMKD/oom_adj 阈值、静态 kswapd 水位。演进方案指可编程、访问感知、随负载自适应的策略：多尺寸 THP（mTHP）、DAMON/DAMOS 驱动的回收与大页提升、可编程回收/压缩阈值，以及 eBPF 风格的策略挂钩。调研覆盖 2021–2026 年内核社区（LWN、LPC、LSFMMBPF）与学界（MobiCom、SOSP、USENIX ATC、arXiv）的进展，以 Android 上 mTHP 运行 2 小时后分配成功率从约 50% 跌至不足 10% 这一现象为锚点。

## 1. 范围与方法

**领域定义。** 资源受限终端设备上 OS 级内存管理策略的可编程化与自适应化——涉及大页（huge page / large folio）分配、页回收、低内存查杀（LMKD）、压缩交换（zRAM）阈值。关注点不是某个应用，而是 OS 如何从「固定策略」走向「按设备 / 按应用 / 按前后台状态可调」。

**"原始"与"演进"的含义。** *原始方案*是编译进内核、系统级生效的固定策略：THP 只有 `always`/`madvise`/`never` 三挡且贪婪提升 2 MB；LMKD 用固定 PSI/oom_adj 阈值杀进程；kswapd 用静态水位回收；zRAM 不区分冷热一律压缩。*演进方案*是让这些策略变得可编程、访问感知、自适应的一组技术——多尺寸 THP（mTHP，按区域选 16 KB–2 MB）、DAMON/DAMOS 低开销采样驱动回收与大页提升、热度感知的 zRAM 压缩、以及 eBPF 风格挂钩提供运行时策略定制能力。

**来源。** 14 个主要来源：内核社区报道与会议（LWN mTHP/DAMON 报道、LPC 2024 OPPO large folios、LPC 2024 可编程 MM、OSS NA 2025 Self-Driving DAMON）、端侧系统论文（MobiCom 2023 SWAM、MobiCom 2026 AppFlow、arXiv 2025 Ariadne）、机制类工作（eBPF-mm、cachebpf、FetchBPF、PageFlex），以及 Android 官方文档（LMKD/PSI）。机制类工作多源于服务器场景，本文仅作为「策略可编程」的实现手段引用，正文中标注其服务器出身后转向端侧映射。

## 2. 问题背景

**系统需要做什么。** 手机 / 边缘 OS 在每次缺页和每次内存压力事件上都要做决策：分配多大的页（4 KB / 16 KB / 64 KB / 2 MB）、回收哪些页、何时杀哪个后台进程、哪些数据压进 zRAM。设备只有 4–16 GB 物理内存，还要在前台交互（60/120 Hz，每帧 8.3–16.7 ms 预算）下保持流畅。

**为什么这个领域难。** 端侧没有 TB 级 DRAM 可用，内存常年高压。设备会连续运行数小时甚至数天，物理内存随之严重碎片化。大页能减少 TLB 缺失、提升能效，但 2 MB 页内部碎片浪费内存，碎片化后分配会触发同步压缩停顿。手机长时间运行恰恰会把连续物理内存耗尽。固定的 LMKD 阈值要么杀得太晚导致卡顿，要么杀得太早导致 App 冷启动慢。

**为什么原始方案不够用了。** Android 上的 mTHP 控制仍是系统级的（经 sysfs），无法根据实时碎片状态或应用前后台状态调整。运行 2 小时后分配成功率从约 50% 跌至不足 10%，且「内核尚未达到可以自动使用 mTHP 的程度」[LWN-mTHP]。固定 LMKD 在内存压力下把后台 App 按序杀掉，导致频繁冷启动。传统 swap+OOMK 组合的 OOM 查杀次数比自适应方案高 6.5 倍 [SWAM]。策略必须能在运行时、按设备和负载被改写，而不是编译时写死。

## 3. 具体问题与瓶颈证据

1. **系统级 THP 在长时间运行后失效** —— mTHP（Linux 6.8+）引入了 16 KB–512 KB 中间尺寸，但开关仍是系统级的。Android 设备运行 1 小时后 mTHP 分配成功率约 50%，运行 **2 小时后失败率超过 90%**，内存完全碎片化，大页不可得 [LWN-mTHP, OPPO-LPC]。

2. **碎片化引发分配停顿，回收缺乏访问感知** —— 固定 kswapd 水位与同步压缩在碎片化下放大延迟；没有访问热度信息时，回收会误伤热页。DAMON 用每 5 ms 采样 70 GB、**不到 1% 单核 CPU** 的开销提供访问热度，驱动的 proactive reclaim 在 ZRAM 上实测**节省 32% 内存、运行时开销仅 1.91%** [DAMON-Reclaim, DAMON-LWN]。固定策略拿不到这种信息。

3. **固定 LMKD/OOM 阈值导致错杀与频繁冷启动** —— LMKD 用固定 PSI 阈值（低端机部分停顿默认 200 ms、高端机 70 ms、完全停顿 700 ms）触发查杀 [Android-LMKD]。传统 swap+OOMK 组合在压力下查杀过激，SWAM 的自适应方案把 **OOM 查杀降低 6.5 倍**，App 启动快 36%、响应快 41% [SWAM]。

4. **zRAM 不区分冷热，压缩拖慢 App 重启** —— Android zRAM 对所有匿名页用同一压缩策略，是 App 重启慢、CPU 高的主因。热度感知、尺寸自适应的 Ariadne 把**相关重启延迟降低 50%**、压缩/解压 **CPU 降低 15%**（对比 SOTA zRAM）[Ariadne]。

5. **大 App 冷启动缺乏预取/回收协同** —— GB 级端侧 App（含本地 LLM/VLM）冷启动时，约 97.2% 的 I/O 是可预测的静态数据，却有 79% 的 DRAM I/O 带宽闲置。AppFlow 用内存调度把**冷启动延迟最多降低 66.5%**（2 s→690 ms）、内核直接回收减少 67.9%、LMK 事件减少 33.7% [AppFlow]。

### 瓶颈证据

| 场景 | 指标 | 数值 | 来源 |
|---|---|---|---|
| Android 运行 2 小时后 mTHP | 分配成功率 | < 10%（从约 50% 下降） | [LWN-mTHP] |
| DAMON 监控 70 GB / 每 5 ms | 监控 CPU 开销 | < 1% 单核 | [DAMON-LWN] |
| DAMON proactive reclaim（ZRAM, v5.12） | 内存节省 / 运行时开销 | 32% 节省 / 1.91% 开销 | [DAMON-Reclaim] |
| 传统 swap+OOMK vs SWAM（移动端） | OOM 查杀次数 | 高 6.5×（传统） | [SWAM] |
| Android zRAM vs Ariadne（Pixel 7） | 相关重启延迟 | 降低 50% | [Ariadne] |
| 固定预加载 vs AppFlow（GB 级 App） | 冷启动延迟 | 降低最多 66.5%（2 s→690 ms） | [AppFlow] |

## 4. 架构：原始 vs 演进

![端侧内存策略：固定内建 vs 可编程/访问感知 架构图](assets/ebpf-programmable-memory-arch.svg)

*图：原始方案与演进方案的架构对照（详细文本版见下方 ASCII 图）。*

**原始方案 —— 固定内建的端侧内存策略**

```
    +-------------------+
    |  App（前台/后台）  |
    |  （无策略输入，    |
    |   不分前后台）     |
    +-------------------+
            |
            | 缺页 / 内存压力
            v
    +-------------------+       +--------------------+
    |  缺页处理器        | ----> |  THP 决策          |
    |  （内核，固定逻辑） | 提升  |  （系统级          |
    |                   |       |   always/madvise） |
    +-------------------+       +--------------------+
            |                           |
            | 分配                      | 贪婪提升 2 MB
            v                           v
    +-------------------+       +--------------------+
    |  伙伴分配器        |       |  khugepaged        |
    |  （默认 4 KB）     |       |  （后台扫描，      |
    |                   |       |   固定间隔）        |
    +-------------------+       +--------------------+
            |                           |
            v                           v
    +----------------------------------------------+
    |  回收 / 交换 / 查杀（全局固定策略）            |
    |  kswapd 固定水位回收                          |
    |  zRAM 一刀切压缩（不分冷热）                  |
    |  LMKD 固定 PSI/oom_adj 阈值查杀               |
    +----------------------------------------------+
            |
            | 内存压力
            v
    +-------------------+
    |  杀后台 App        |
    |  （固定优先级序）   |
    +-------------------+
```

*原始方案：所有策略编译进内核、系统级生效。THP 贪婪提升 2 MB，回收/zRAM/查杀阈值固定，不区分应用前后台。长时间运行后碎片化使大页失效、查杀错位。*

**演进方案 —— 可编程 / 访问感知的端侧内存策略**

```
    +-------------------+       +------------------------+
    |  App（前台/后台）  |       | * 用户态策略管理器      |
    |  （前后台状态      | 状态  |   （DAMON 采样热度，    |
    |   反馈给策略）      | ----> |    按应用/设备配置）     |
    +-------------------+       +------------------------+
            |                           |
            | 缺页 / 内存压力           | * 下发策略 / 加载 eBPF
            v                           v
    +-------------------+       +------------------------+
    | * 可挂钩缺页处理   | <---- | * 选页大小器           |
    |   （内核 + 策略    | 选尺寸|   （按区域成本-收益：   |
    |    分发）          |       |    4KB/16KB/64KB/2MB） |
    +-------------------+       +------------------------+
            |                   （mTHP / eBPF-mm）
            | 分配
            v
    +-------------------+       +------------------------+
    |  伙伴分配器        |       | * 自适应压缩触发        |
    |  （多尺寸 +        | <---- |   （按碎片/水位阈值，   |
    |    双 LRU 链表）   | 触发  |    保留区给大页）       |
    +-------------------+       +------------------------+
            |                   （TAO：order-4 保留 15%）
            v
    +----------------------------------------------+
    | * 访问感知的回收 / 交换 / 查杀                 |
    |   DAMOS：pageout/hugepage/lru_prio 按热度裁决  |
    |   * 热冷分离 zRAM（Ariadne：热不压/冷外移）    |
    |   * 自适应 LMKD（SWAM：按热度延后查杀）        |
    +----------------------------------------------+
            |
            | 内存压力
            v
    +-------------------+       +------------------------+
    | * 可编程回收/调度  | <---- | * 回收策略             |
    |   （kswapd + 策略 | 裁决  |   （PROTECT/EVICT/PASS |
    |    / AppFlow 预取） |       |    + 冷启动预取协同）   |
    +-------------------+       +------------------------+
```

*演进方案：在缺页、分配、回收/zRAM/查杀路径上插入可编程、访问感知的策略点（`*` 标记为新增或变更）。用户态管理器通过 DAMON 低开销采样获取访问热度，并感知应用前后台状态，按设备/负载下发策略或加载 eBPF。mTHP 按区域选尺寸，TAO 用保留区与双 LRU 维持大页可得性，DAMOS/Ariadne/SWAM/AppFlow 让回收、压缩、查杀、预取随负载自适应。*

## 5. 演进方案的收益与未解决问题

### 演进方案为什么有效

- **系统级 THP 长时间运行后失效** —— mTHP 按区域选 16 KB–2 MB，不再是系统级一刀切。TAO 把尺寸设为 order-4（64 KB）并保留 15% 物理内存给 mTHP-only 分配后，成功率从「2 小时后 <10%」回到 **50% 以上**。双 LRU（base page 一条、large folio 一条）维持大页可得性 [LWN-mTHP, OPPO-LPC]。

- **碎片化停顿与无访问感知回收** —— DAMON 以 <1% 单核开销提供访问热度，DAMOS 据此只对冷区 `pageout`、只对热区 `hugepage` 提升，proactive reclaim 在 ZRAM 上**节省 32% 内存、开销仅 1.91%** [DAMON-Reclaim]。eBPF-mm 进一步用 DAMON 热区信息在缺页路径按区域选页大小（4 KB/64 KB/2 MB）[eBPF-mm]。

- **固定 LMKD/OOM 阈值错杀** —— SWAM 把 swap 与查杀整合，按数据热度延后/精确查杀，**OOM 查杀降低 6.5 倍**、App 启动快 36%、响应快 41% [SWAM]。

- **zRAM 一刀切压缩** —— Ariadne 区分热（不压、留 DRAM）/温（压入 zpool）/冷（外移 flash），对冷数据用大压缩块、热数据用小块，**相关重启延迟降低 50%、压缩/解压 CPU 降低 15%** [Ariadne]。

- **冷启动无预取/回收协同** —— AppFlow 利用「97.2% 冷启动 I/O 可预测、79% DRAM I/O 带宽闲置」这一特征，做内存调度与预取，**冷启动延迟最多降 66.5%、直接回收减 67.9%、LMK 事件减 33.7%、多保留 1.85x 后台 App** [AppFlow]。

### 尚未解决的问题

- **缺页/回收的 eBPF 挂钩尚未进 mainline** —— eBPF-mm、cachebpf、FetchBPF、PageFlex 截至 2025 年中多为研究原型，缺页与回收挂钩未合入主线。端侧目前可用的可编程接口主要是 mainline 的 DAMOS 与 userspace LMKD（PSI），还不是任意 eBPF 程序 [eBPF-mm, PageFlex, LSFMMBPF]。

- **采样驱动策略依赖负载稳定性** —— DAMON 采样在阶段切换或突发负载下需要持续重采样。手机的前后台频繁切换正是这种突发场景，可能削弱部分收益 [DAMON-Reclaim]。

- **eBPF 验证器约束限制策略复杂度** —— BPF 验证器强制有界循环与有限栈深。端侧若要在策略里跑复杂热度预测或 ML，难以直接实现，需要借助 map / BPF-to-BPF 等方式绕行。

- **多策略点可能相互干扰，且缺乏功耗数据** —— 缺页选尺寸、DAMOS 回收、zRAM 压缩、LMKD 查杀同时生效时可能出现病态交互（比如刚提升的大页被立即拆分回收）。端侧最关心的持续采样/压缩/预取功耗，目前没有公开的电池影响数据。

## 6. 对比表

| 维度 | 原始方案（固定内建策略） | 演进方案（可编程 / 自适应策略） | 提升幅度 | 来源 |
|---|---|---|---|---|
| 大页控制粒度 | 系统级（always/madvise/never，贪婪 2 MB） | 按区域选 16 KB–2 MB（mTHP / eBPF-mm 选尺寸） | 区域级 vs 系统级 | [LWN-mTHP, eBPF-mm] |
| 运行 2 小时后 mTHP 成功率 | < 10%（碎片化失效） | > 50%（TAO order-4 + 保留 15%） | 由 <10% 回到 >50% | [LWN-mTHP, OPPO-LPC] |
| 回收的访问感知 | 无（固定 kswapd 水位） | DAMOS 按热度回收，节省 32% 内存 | +32% 内存节省，开销仅 1.91% | [DAMON-Reclaim] |
| 监控/采样开销 | 不适用（无采样） | < 1% 单核（监控 70 GB/5 ms） | 近乎零开销 | [DAMON-LWN] |
| OOM 查杀频率（移动端） | 基线（固定 swap+OOMK） | 自适应整合，降低 6.5× | −6.5×，启动快 36%、响应快 41% | [SWAM] |
| zRAM 相关重启延迟 | 基线（一刀切压缩） | 热冷分离 + 尺寸自适应 | −50%，CPU −15% | [Ariadne] |
| GB 级 App 冷启动延迟 | 基线（固定预加载） | 预取/回收协同调度 | −66.5%（2 s→690 ms） | [AppFlow] |
| 策略部署方式（机制） | 改内核 + 重启（数月周期） | 运行时下发/加载（DAMOS sysfs / eBPF 秒级） | 数月 → 秒级，应用减速 <1%（权衡：挂钩未上游） | [PageFlex, LSFMMBPF] |

## 7. 一词概括

**Adaptive（自适应）** —— 端侧内存管理从编译时固定、系统级的策略，转向按访问热度、按设备碎片状态、按应用前后台状态在运行时自我调整。mTHP 让大页成功率在运行 2 小时后从 <10% 回到 >50%，DAMOS 以 <1% 单核采样开销节省 32% 内存，自适应查杀/压缩把 OOM 查杀降低 6.5x、相关重启延迟降低 50%。实现机制是「可编程（Programmable）」——把策略面开放给运行时可加载的程序，但端侧的核心价值在于自适应。

## 8. 开放问题与注意事项

- **可编程内存挂钩的端侧上游路径** —— DAMOS 已在 mainline，但缺页选尺寸、页缓存淘汰、回收的通用 eBPF 挂钩尚未合入。Android GKI 何时、以何种受限形式开放这些策略面仍不明确 [LSFMMBPF, eBPF-mm]。
- **自适应策略的功耗代价** —— 持续 DAMON 采样、热冷分离压缩、冷启动预取都消耗 CPU/IO。现有论文几乎都报告吞吐/延迟收益，但很少有在真实电池设备上的持续功耗与发热数据。
- **碎片化的长期治理** —— TAO 的保留区/双 LRU 在数小时尺度有效，但连续运行数天、跨多次前后台切换后的大页可得性仍缺长程实测 [OPPO-LPC]。
- **多策略点协调** —— 选尺寸、回收、压缩、查杀、预取各自自适应时缺乏统一协调。端侧尚无公开工作处理「多挂钩/多策略联合优化」的问题。
- **跨设备与跨厂商可移植性** —— 现有数据多来自特定机型（Pixel 7、OPPO 量产机），低端 eMMC + 小内存设备上的表现可能差距更大。mTHP/DAMOS 配置如何随设备档位自动适配尚无标准。
- **基准代表性** —— 端侧负载（相机、游戏、本地大模型、后台同步）访问模式差异大，多数评测只覆盖少数 App，生产环境的长尾负载仍待验证。

## 9. 参考文献

### 端侧锚点：mTHP / large folios（碎片化 50%→<10%）
1. **[LWN-mTHP]** — Corbet J., 2024. "Two talks on multi-size transparent huge page performance." LWN.net. URL: https://lwn.net/Articles/974826/ 。本地副本：[sources/android-mthp.md](sources/android-mthp.md)
2. **[OPPO-LPC]** — Song B., Han C., Liu H.（OPPO）, Singh K., Zhao Y.（Google）, 2024. "Product practices of large folios on millions of OPPO Android phones." Linux Plumbers Conference 2024, Android MC. URL: https://lpc.events/event/18/contributions/1705/
3. **mTHP for anonymous memory** — Roberts R. 等, 2024. LWN.net. URL: https://lwn.net/Articles/954094/
4. **mTHP swap-in for zRAM-like swapfile** — Song B. 等, 2024. LWN.net / LKML v5 series. URL: https://lwn.net/Articles/983531/

### DAMON / DAMOS（访问感知、自适应、mainline）
5. **[DAMON-LWN]** — Corbet J., 2021. "Using DAMON for proactive reclaim." LWN.net. URL: https://lwn.net/Articles/863753/ 。本地副本：[sources/damon-damos.md](sources/damon-damos.md)
6. **[DAMON-Reclaim]** — Park S.J., 2021. "Introduce DAMON-based Proactive Reclamation" + DAMON Project docs（32% 节省 / 1.91% 开销）. URL: https://lwn.net/Articles/858682/ ；https://damonitor.github.io/
7. **Self-Driving DAMON/S** — Park S.J., 2025. "Controlled and Automated Access-aware Efficient Systems." OSS NA 2025. URL: https://static.sched.com/hosted_files/ossna2025/16/damon_ossna25.pdf

### 端侧自适应查杀 / 交换 / 启动
8. **[SWAM]** — Lim G., Kang D., Ham M.J., Eom Y.I., 2023. "SWAM: Revisiting Swap and OOMK for Improving Application Responsiveness on Mobile Devices." MobiCom 2023. arXiv 2306.08345. URL: https://arxiv.org/abs/2306.08345
9. **[Ariadne]** — Liang Y., Shen A., Xue C.J. 等, 2025. "Ariadne: A Hotness-Aware and Size-Adaptive Compressed Swap Technique for Fast Application Relaunch on Mobile Devices." arXiv 2502.12826. URL: https://arxiv.org/abs/2502.12826
10. **[AppFlow]** — Li X., Liu S., Guo B. 等, 2026. "AppFlow: Memory Scheduling for Cold Launch of Large Apps on Mobile and Vehicle Systems." MobiCom 2026. arXiv 2603.17259. URL: https://arxiv.org/abs/2603.17259
11. **[Android-LMKD]** — Android Open Source Project. "Low memory killer daemon (lmkd)"（PSI 阈值：低端机 200 ms / 高端机 70 ms / 完全停顿 700 ms）. URL: https://source.android.com/docs/core/perf/lmkd

### 可编程机制（服务器出身，端侧映射）
12. **[eBPF-mm]** — Mores K., Psomadakis S., Goumas G.（NTUA）, 2024. "eBPF-mm: Userspace-guided memory management in Linux with eBPF." ACM SRC@MICRO'24. arXiv 2409.11220. URL: https://arxiv.org/abs/2409.11220 。本地副本：[sources/ebpf-mm.md](sources/ebpf-mm.md)
13. **cachebpf** — Zussman T., Zarkadas I. 等（Columbia, IBM）, 2025. "Cache is King: Smart Page Eviction with eBPF." arXiv 2502.02750. URL: https://arxiv.org/abs/2502.02750
14. **FetchBPF** — Cao X. 等, 2024. "FetchBPF: Customizable Prefetching Policies in Linux with eBPF." USENIX ATC 2024. URL: https://www.usenix.org/conference/atc24/presentation/cao
15. **PageFlex** — Yelam A. 等（Google, UCSD, UW）, 2025. "PageFlex: Flexible and Efficient User-space Delegation of Linux Paging Policies with eBPF." USENIX ATC 2025. URL: https://www.usenix.org/conference/atc25/presentation/yelam
16. **[LSFMMBPF]** — Skarlatos D., Zhao K.（CMU）, 2024. "Towards Programmable Memory Management with eBPF." LPC 2024. URL: https://lpc.events/event/18/contributions/1932/

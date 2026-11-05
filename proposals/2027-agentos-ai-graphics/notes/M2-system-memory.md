# M2 系统内存（KT1）调研笔记

> 检索日期：2026-11-03。范围：1.2 中的 KT1 部分、2.2 中的系统内存瓶颈、第四部分 KT1-a / KT1-b / KT1-c。
> 本文在仓库既有文章（A06、A11、A15b、A15c、A16a、A14、memory-capacity-crunch-CN）基础上补最新进展与缺口，不重复基础机制。

## 摘要

1. **SPE 路线的最大事实**：主线内核没有任何 SPE 热页识别/分层补丁。业界仅有（a）华为 openEuler OLK-6.6 的 19 patch 系列「SPE 驱动 NUMA balancing 与 DAMON」（v5，2025-05），无公开性能数据；（b）2026 年 5 月至 9 月 DAMON「硬件采样访问报告」RFC（v1 5 月，v2 9 月，PEBS/IBS，SPE 后端由另一开发者对接同一 ring，尚未合入）。
2. 「采样只能证明热、证明不了冷」已被 DAMON RFC 作者明确写出，补救办法是冷判定交还给页表 Accessed 位 / page-fault 原语（带 age）。KT1-b/c 必须是「SPE 做热证据 + 页表扫描做冷证据」的混合，不能纯 SPE。
3. 手机 SoC 是否开放 SPE：Cortex-A720/A725/X925 实现 SPE（来自 perf data source 编码补丁与 A720 勘误），但**量产手机是否放开：未找到公开资料**。2020 年 Arm 称当时无消费级 Android 设备带 SPE；EL3 固件可按核关闭 SPE。这是 KT1-b 的头号立项风险。
4. .so 冷启动：per-VMA lock 在 6.4 合入（仅匿名页），6.5 起覆盖「页缓存已命中」的文件缺页；需要 I/O 的文件缺页版本待核实。arm64 可执行段 contpte 大 folio 仍在演进（Ryan Roberts 2024-01 起 RFC，v5 2025-07；2026-03 Usama Arif 扩展到 16K/64K），合入版本待核实。
5. 公开量化数据：AppFlow（MobiCom 2026，arXiv 2026-03）显示 GB 级应用 86.6% 的冷启动超过 1 秒；Ariadne（HPCA 2025，Pixel 7）把 zram 换入后的重启时延降低 50%；ASAP（ATC 2021，Pixel 4）预取降低切换时延均值 22.2%。
6. 背景：移动 DRAM 合约价 2026Q1 +58–63%，Q2 近翻倍，3Q26 +8–13%，TrendForce 判断 4Q26 涨幅继续收敛、因 2027 供给紧张价格不会明显回落。
7. 最大资料空白：（1）量产手机 SPE 可用性与采样开销实测；（2）鸿蒙微内核（HarmonyOS NEXT）的页回收/换出机制，无公开资料；（3）「.so 页被逐出导致冷启动变慢」的专项公开数据，只有间接证据。

---

## 第一部分（1.2）KT1 业界最新进展

### 1.2.1 趋势与事实依据

**趋势一：内核主线对「硬件采样做冷热识别」的态度正从 x86 起步，Arm SPE 落后一步。**
- 事实：2025-03 Bharata B Rao 的 AMD IBS 热页推广 RFC，演进到 2026-07 的 pghot v8（IBS + NUMA balancing hint fault 两个来源）。2026-09-03 LWN 报道：Hildenbrand 称「8 版无 review tag，离可合入很远」，Wilcox 反对，Morton 问 DAMON 能否替代，SJ Park 称多来源整合正在 DAMON 里实现 [R1][R2]。
- 事实：DAMON 硬件采样访问报告 RFC v1 2026-05、v2（9 patch）2026-09-10，用 per-CPU 无锁 ring 接收 NMI 上下文的采样，已用 PEBS/IBS 验证，「SPE 后端由另一开发者对接同一 ring」 [R3][R4]。
- 对我们的影响：不要自建一套独立的采样内核框架；把 SPE 作为 DAMON 的一个硬件访问源去对接，可以复用上游路线，降低长期维护成本。

**趋势二：「采样能证明热、证明不了冷」已成共识，冷由页表/缺页原语补。**
- 事实：DAMON RFC v2 作者原话意思：采样器能证明区域热，不能证明冷，因为沉默既可能是没访问也可能是没采到；冷判定来自 page-fault 原语提供的 region age [R3]。LWN 同文指出「降级（找冷页）相对容易，找慢层里的热页更难」 [R2]。
- 事实：HeMem（SOSP 2021）用 PEBS 且用静态阈值（8 次读 / 4 次写判热，18 次冷却），Memtis（SOSP 2023）改为按全局访问分布动态分级并动态调采样间隔 [R5]。第三方评测指出 Memtis 写采样周期 100K，写密集负载表现差 [R6]（arXiv 2504.18714，结论属第三方，需对照原论文）。
- 对我们的影响：KT1-c（换出）的风险点是「误判冷」，所以换出的冷证据不能只靠 SPE，需要 Accessed 位/MGLRU 代龄交叉验证。

**趋势三：Android 侧内核回收仍在「谁是热应用」的语义缺口上挣扎。**
- 事实：2026-03-05 LWN 报道 LSFMM 议题：许多 Android 厂商没有启用 MGLRU；匿名页停在最年轻代很少被回收、文件页回收过猛，调 swappiness 解决不了；Android 的前/后台热冷应用模型 MGLRU 没有对应；readahead 页进最年轻代；荣耀用 memcg 强制回收后台应用匿名页绕开；Wilcox 称「rip it out」 [R7]。
- 对我们的影响：KT1-b/c 的价值落点正是这个缺口——用应用粒度（memcg）+ 硬件访问证据做匿名页热冷，而不是依赖 MGLRU 的页龄。同时这也意味着不能把方案绑死在 MGLRU 上。

**趋势四：移动端压缩换页研究转向「热感知 + 预取」。**
- 事实：Ariadne（HPCA 2025，arXiv 2502.12826，CMU SAFARI / ETH / 香港城大，Pixel 7）：热感知数据组织 + 自适应压缩粒度 + 主动解压，重启时延平均 -50%，压缩/解压 CPU 占用 -15% [R8]。ASAP（USENIX ATC 2021，Pixel 4，8 个真实应用）：自适应预取，切换时延均值 -22.2%、最大 -33.3% [R9]。Chou 等（ACM TECS 2023）：识别未用匿名页换入 zram 以多留文件页，Pixel 上切换时延最多 -43% [R10]。MemSaver（ICPE 2024）：后台应用页预先换出以代替杀进程 [R10]。
- 对我们的影响：KT1-b 的预取、KT1-c 的换出都有直接对标；差异点必须落在「硬件访问证据」，否则只是 ASAP/Ariadne 的重复。

**趋势五：冷启动的瓶颈正在从「CPU 初始化」转向「内存回收与文件 I/O」。**
- 事实：AppFlow（MobiCom 2026 录用，arXiv 2603.17259，2026-03-18）：GB 级应用冷启动 86.6% 超过 1 秒；Pixel 7/8、Android 15、DRAM 调到 6/8GB 实测；三组件（选择性文件预加载、自适应回收、感知上下文的杀进程）合用冷启动时延 -40.8%、后台存活应用数 1.85 倍；消融：仅自适应回收冷启动次数 -60% 但启动时延只 -14.7%，仅预加载时延 -26.1% 但冷启动次数 +30%（内存压力加大）[R11]。
- 对我们的影响：预加载（占内存）与回收（腾内存）互相打架，正是 KT1-a（.so 页保护/加速）与 KT1-b/c（匿名页换出腾空间）需要协同的依据。

**趋势六：系统层「容量虚拟化」已成厂商卖点。**
- 事实：三星 RAM Plus 把部分内部存储当虚拟内存，One UI 7 可选 2/4/6/8GB，One UI 8 报道新增 12GB 选项（2025-05 起多方报道，早期为泄露版本，最终稳定版细节待核实）[R12]。OpenHarmony 标准系统有 ESwap：常驻进程 zswapd 把 zram 压缩过的匿名页加密后换出到专用 ESwap 分区，无分区时仅用 zram [R13]（官方文档站页面本次未能抓取全文，来源为检索摘要，待核实）。
- 对我们的影响：闪存 swap 在业界已商用，KT1-c 的 zram writeback 方向不是孤例，但需讲清磨损预算与延迟。

**趋势七：内核 swap 子系统本身在重构。**
- 事实：swap table 首阶段合入 6.18（来自二手转述，非 LWN 原文，待核实）；Nhat Pham 的 virtual swap space 2026-02 已到 v3，仍是提案 [R14]。mTHP 大 folio 换入支持 zRAM 类同步设备的补丁（Barry Song、Chuanhua Han 等，commit 242d12c9）已进主线，具体版本待核实 [R15]。
- 对我们的影响：KT1-c 换出粒度应与大 folio 对齐，避免与内核方向冲突；基线内核版本要在立项时锁定。

### 1.2.2 KT1-a 相关锁与大 folio 的核实清单

| 项目 | 核实结果 | 来源 |
|---|---|---|
| per-VMA lock 合入 | Linux 6.4，初版仅覆盖匿名页（非 swap） | LWN 937943；LWN 906852 [R16] |
| per-VMA lock 覆盖文件缺页 | 6.5 起「页缓存已命中的文件缺页无需 mmap_lock」（kernelnewbies 6.5 条目）。需要同步 I/O 的 read fault、COW、共享写缺页的覆盖版本：Wilcox「Handle more faults under the VMA lock」系列，openEuler 2023-11 有 6.6 回移植，主线具体版本**待核实**（印象为 6.6） | kernelnewbies Linux_6.5 [R17]；openEuler 邮件列表 [R18] |
| arm64 可执行段大 folio（exec_folio_order） | Ryan Roberts：2024-01 RFC v1，2025-04 RFC v4，2025-07 v5（Graviton3、Ampere Altra 有 contpte 覆盖率提升数据，Will Deacon、Jan Kara ack）。2026-03-10 Usama Arif 4 patch 扩展到 16K/64K 页，2026-03-20 v2 把 `exec_folio_order()` 改为通用 `preferred_exec_order()`。**主线合入版本待核实**，Usama 的系列以已存在的 exec_folio_order 为前提，侧面说明基础补丁已合入 | LKML / patchew [R19] |
| Usama 系列数据（非手机） | Grace（Neoverse V2）、64K 页、512MB 可执行文件、ext4：冷缺页 83.4ms → 41.3ms（-50%），随机访问 76.0 → 58.3ms（-23%） | lkml.iu.edu 2603.1/12745 [R19] |
| contpte（arm64 连续 PTE）基础支持 | 印象为 6.9（Ryan Roberts），本次**未核实** | 待核实 |
| i_mmap_rwsem 与回收 | Minchan Kim 2022：rmap 锁（i_mmap_rwsem、anon_vma rwsem）在 Android 重负载下 kswapd 等锁 300ms 以上；改为 trylock 并旋转 LRU；后续测得某场景 i_mmap_rwsem 争用使回收效率 48% → 27%，又补了 skip 节流 | lore.kernel.org [R20] |
| 共享库映射对 i_mmap_rwsem | 2026 前后 Hygon 补丁（RWH_RMAP_EXCLUDE）：64 核以上 UnixBench execl 在 libc.so.6、ld-linux 上卡 i_mmap_rwsem，禁用 rmap 跟踪后 execl/shellscript 提升约 80%。这是服务器数据，**未合入，日期未知**，且代价是这些文件不可回收 | ci.syzbot.org [R21] |
| 16KB 页（相关背景） | Android 官方：16KB 页设备在内存压力下应用启动时间平均 -3.16%，部分应用最多 -30%；内存占用略增（9to5google 引用约 9%，官方页只说「略增」） | developer.android.com [R22] |
| folio lock / readahead / lru_lock | 未做专项文献检索；readahead 页进 MGLRU 最年轻代的问题见 [R7]；其余按 A11、A16a 既有内容 | — |
| 鸿蒙内核对应机制 | **未找到公开资料**。OpenHarmony 标准系统（Linux 内核）有 ESwap；HarmonyOS NEXT 微内核无公开信息 | — |

---

## 第二部分（2.2）系统内存瓶颈（仅系统内存）

### 2.2.1 平台术语对照（避免混用）

| 对象 | Android（Linux/GKI） | iOS（XNU） | HarmonyOS |
|---|---|---|---|
| 杀进程 | lmkd（PSI 驱动） | Jetsam | OpenHarmony 标准系统：Linux 内核，低内存终止机制待核实；HarmonyOS NEXT：未找到公开资料 |
| 匿名页换出 | zram（+ 可选 writeback 到块设备） | compressed memory（压缩器，不是 zram，不落盘，XNU 是否二次处理冷压缩页待核实，见 A15c） | OpenHarmony：ESwap（zswapd + zram + 专用分区）[R13]；LiteOS-A 无 swap（见 A14）；NEXT：未找到公开资料 |
| 冷热 | LRU / MGLRU（厂商是否开启待核实） | 页面老化机制（公开资料有限） | 未找到公开资料 |

### 2.2.2 瓶颈量化

1. **容量被冻结，回收成为唯一杠杆。** 移动 DRAM 合约价 2026Q1 环比 +58–63%、Q2 近翻倍至约 $20/GB（见仓库 memory-capacity-crunch-CN 引用的 TrendForce 数据）；3Q26 TrendForce 预测 +8–13% QoQ，4Q26 涨幅「进一步收敛」，因厂商产能向服务器与 HBM 倾斜、2027 供给偏紧，合约价不会明显回落 [R23]（TrendForce 3Q26 页，最后修改 2026-08-03）。旗舰/中端 RAM 维持 12GB / 8GB 的判断沿用仓库既有文章；渠道级「4GB 回潮」报道均为传闻级，不引用。
2. **冷启动已不是 CPU 问题。** GB 级应用 86.6% 冷启动超过 1 秒；Android Vitals 只把 ≥5 秒记为慢 [R11]。AppFlow 的内存表给出文件页占用：Photoshop 匿名 636MB / 文件 379MB，TikTok 616 / 434，Qwen2.5 307 / 1637，Gemma 710 / 1925（单位 MB）；16 个负载中可回收文件页常超过 1000MB [R11]。说明「Agent 叠加」时端侧模型文件页会和应用 .so/资源文件页争夺同一页缓存（模型 mmap 归 KT3，但竞争发生在系统内存层）。
3. **匿名页换入是重启时延主因之一。** zram 不区分冷热、不预取：Ariadne 在 Pixel 7 上改进后重启时延 -50% [R8]；ASAP 指出需求换页是应用切换慢的主要来源，Pixel 4 上预取均值 -22.2% [R9]。
4. **内核回收路径有锁与策略缺陷。** rmap 锁使 kswapd 等待 ≥300ms [R20]；MGLRU 在 Android 上的匿名页回收偏弱、与热冷应用模型脱节 [R7]。Google LPC 2022 的 Pixel 6 评估称一个无 swap 测试中 MGLRU 使整体应用启动时间 -47.10%（幻灯片，二手摘录，未核原稿）。
5. **叠加场景的估算（估算）。** 假设 Agent 常驻 + 前台应用 + 2–3 个后台应用，在 12GB 机型上，系统与驱动预留约 3–4GB（来自仓库既有文章的口径，待核实），端侧模型权重常驻若 2–4GB，则应用侧可用匿名 + 文件页约 4–6GB，而 AppFlow 单个 GB 级应用就占约 1–2GB（匿名 + 文件）。因此叠加时回收频率上升，冷启动与切换时延的代价会落在 .so/文件页被逐出与匿名页换入上。此为推算，非实测。

### 2.2.3 对立项的启示

- 证据支撑 KT1-a：冷启动慢来自文件页逐出 + 回收路径锁；AppFlow 已证明预加载与回收需要协调。
- 证据支撑 KT1-b：zram 换入无冷热、无预取，对标工作有 -22%～-50% 的空间。
- 证据支撑 KT1-c：容量冻结（价格 4 倍）使「不增加 DRAM 提升有效容量」成为刚需；但 MGLRU 在 Android 上不好用，需要自有冷热证据。

---

## 第四部分 关键技术

### KT1-a .so 文件页锁优化

#### 1. 要解决的问题

- 现状：Agent 与应用叠加时，多进程同时映射并缺页同一批共享库（libc、libart、libhwui、引擎库等）；内存压力下文件页被逐出，冷启动时反复发生缺页、等 I/O、等 rmap 与 LRU 锁。
- 代价（公开数据，均为间接证据）：
  - 冷启动：GB 级应用 86.6% 超 1 秒 [R11]。
  - 回收路径：Android 重负载 kswapd 等 rmap 锁 ≥300ms；i_mmap_rwsem 争用使回收效率 48% → 27% [R20]。
  - 文件缺页并行度：6.4 的 per-VMA lock 仅匿名页，6.5 起才有页缓存命中的文件缺页 [R16][R17]。
  - 大页收益：arm64 exec 大 folio 在服务器核上冷缺页 -50%（非手机）[R19]；Android 16KB 页让内存压力下启动均值 -3.16% [R22]。
- 缺口：「共享库页被逐出 → 冷启动变慢」没有手机侧专项公开数据，**未找到公开资料**；本节目标值依赖立项后自测。

#### 2. 业界做法扫描

| 方案 | 年份 | 来源 | 原理 | 局限 |
|---|---|---|---|---|
| per-VMA lock | 2023（6.4） | LWN 937943 [R16] | 缺页只锁本 VMA，不抢 mmap_lock | 初版仅匿名页；文件、swap 缺页后续补；曾有 fork 并发损坏回归 |
| 文件缺页走 VMA 锁 | 2023（6.5 起，I/O 型版本待核实） | kernelnewbies 6.5 [R17] | 页缓存命中缺页不拿 mmap_lock | 需要 I/O 的路径仍可能回退 mmap_lock，待核实 |
| rmap 锁 trylock | 2022 | Minchan Kim, lore [R20] | 回收时拿不到 i_mmap_rwsem 就旋转 LRU | 有活锁风险，需节流 |
| RWH_RMAP_EXCLUDE | 待核实 | ci.syzbot.org [R21] | 共享库文件标记后 VMA 不进 i_mmap 树 | 这些页不可回收、影响 compaction/KSM，未合入 |
| exec 大 folio（contpte 对齐） | 2024–2026 | Ryan Roberts；Usama Arif [R19] | readahead 按 arch 偏好阶数分配可执行页 | 合入版本待核实；手机实测缺失 |
| AppFlow 选择性文件预加载 | 2026 | arXiv 2603.17259 [R11] | 按启动画像预加载静态小文件，限额 100MB，保活扫描 10s 一次 | 预加载本身增加内存压力，冷启动次数 +30%（单独使用时） |
| Android 16KB 页 | 2024–2025 | developer.android.com [R22] | 减少缺页与 TLB 压力 | 内存占用上升；生态兼容 |
| MGLRU | 2022（6.1） | Google LPC [R7] | 多代 LRU | Android 厂商多未启用，readahead 页进最年轻代 |

#### 3. 技术难点

**难点一：文件缺页「全程无全局锁」做不到，关键路径上仍有 I/O 与 rmap 争用。**
- 难在哪：缺页要拿 folio lock、等 I/O、可能走 mmap_lock 回退；回收反向映射时又要拿 i_mmap_rwsem，共享库被几十个进程映射，一个读写信号量被多个路径争抢。约束是不能破坏回收对 .so 页的可回收性。
- 怎么破：对象是「共享库的文件页」，位置在内核 mm 的缺页与 rmap 路径。（1）确认并回移植 per-VMA lock 对 I/O 型文件缺页的覆盖；（2）回收侧对被多进程映射的热 .so 页走 trylock + 批量跳过，降低 kswapd 阻塞；（3）i_mmap_rwsem 的读写分离或对「只读共享库」采用 RCU 化遍历（需论证，非现成方案）。
- 关键突破：把共享库文件页的缺页和回收从全局锁路径中剥离。

**难点二：保护 .so 页与回收腾空间互相冲突。**
- 难在哪：AppFlow 证明预加载增加内存压力、回收又会撤销预加载。保护得太多，匿名页换出（KT1-c）腾不出空间。
- 怎么破：对象是「冷启动关键 .so 页集合」，位置在回收决策层。按应用启动画像生成关键页集合，用软保护（降低回收优先级、不 mlock），预算受 memcg 与全局上限双约束；与 KT1-c 共用一个内存预算账本。
- 关键突破：按启动画像对 .so 页做有预算的软保护。

**难点三：大 folio 与碎片、读放大的权衡。**
- 难在哪：exec 大 folio 减少缺页和 TLB 缺失，但需要连续物理内存；手机碎片严重，且读放大会增大 I/O 与内存（16KB 页已有约 9% 额外占用的报道）。
- 怎么破：对象是 .so 可执行段，位置在 readahead 与页分配。仅对启动关键 .so 的热段请求 contpte 对齐 folio，其余保持小页；失败时优雅降级。
- 关键突破：热段大 folio、冷段小页的分段映射。

#### 4. 机制架构

- 感知/建模：缺页 trace（tracepoint / Perfetto）、冷启动 .so 访问画像（按应用、按版本）、rmap 锁等待时间、PSI。
- 决策：关键 .so 页集合与预算；回收时的跳过/旋转策略；大 folio 请求开关。
- 执行：per-VMA lock 覆盖补全；rmap trylock 批处理；readahead 阶数设置；软保护标志（降低 LRU 优先级）。
- 反馈：冷启动时延、major fault 数、rmap 锁等待、关键页重新缺页率（refault）；异常时自动撤销保护。

#### 5. 目标与度量

| 指标 | 基线 | 目标（区间） | 依据与条件 |
|---|---|---|---|
| 叠加场景冷启动时延 | 立项后自测（待测） | -15%～-30% | 依据：AppFlow 回收+预加载 -40.8%、ASAP -22%、16KB 页内存压力下 -3%～-30%；本技术只占其中一部分，故取较保守区间。条件：Agent 常驻 + 应用冷启动，内存余量 <20% |
| 回收路径 rmap 锁最长等待 | 300ms 级 [R20] | <50ms（P99） | 目标由自测校准 |
| 关键 .so major fault 数 | 待测 | -40% 以上 | 估算，依据 exec 大 folio 冷缺页 -50%（服务器数据）折减 |

#### 6. 风险与待核实

- 全部区间目标缺手机侧基线，需先建测量基线（属 S1 风险评估中的「真机可观测性」）。
- 版本待核实：per-VMA lock 对 I/O 型文件缺页的版本；exec 大 folio 合入版本；contpte 6.9。
- 鸿蒙微内核对应机制：未找到公开资料。
- 软保护可能被应用滥用，需 memcg 预算。

#### 7. PPT 素材卡

**挑战**
1. 锁竞争拖慢缺页：叠加时共享库多进程缺页，rmap 锁使回收等待可达 300ms 以上。
2. 冷启动慢：GB 级应用 86.6% 冷启动超 1 秒。
3. 保护与回收冲突：预加载使冷启动次数反增 30%。

**目标**：降低叠加场景锁竞争与文件页逐出，提升应用冷启动性能。
**量化目标**：冷启动 -15%～-30%

**技术难题**
- 难题一：文件缺页与回收去全局锁
  - 缺页提速：补全 I/O 型文件缺页的 VMA 锁覆盖，避开 mmap_lock。
  - 回收降阻：对热 .so 页 trylock 批量跳过，不阻塞 kswapd。
  - 关键突破：共享库页脱离全局锁路径
- 难题二：.so 软保护与回收腾空间的平衡
  - 画像保护：按启动画像生成关键页集合，软保护不 mlock。
  - 统一预算：与匿名页换出共用内存账本。
  - 关键突破：有预算的关键页软保护
- 难题三：大 folio 的碎片权衡
  - 热段大页：仅对关键 .so 热段请求 contpte 对齐。
  - 优雅降级：分配失败退回小页。
  - 关键突破：热段大页冷段小页

**架构四段**：感知：缺页轨迹 / 启动画像 / 锁等待；决策：关键页集合 / 预算 / 跳过策略；执行：VMA 锁补全 / trylock / 大 folio；反馈：冷启动时延 / refault 率。

---

### KT1-b 基于 ARM SPE（含扩展）的匿名页冷热识别与预取

#### 1. 要解决的问题

- 现状：zram 换入是按需、无冷热区分、无预取 [R8][R9]；内核冷热信号来自 PTE Accessed 位扫描（MGLRU / DAMON），页级精度与扫描开销互相制约（见 A05、A15b）。Android 厂商大多没开 MGLRU，且 MGLRU 对匿名页回收偏弱 [R7]。
- 代价：应用切回前台时大批匿名页缺页换入，解压在关键路径上。Ariadne 的对标：热感知 + 主动解压让重启时延 -50%，Pixel 7 [R8]；ASAP 预取均值 -22.2%、最大 -33.3%，Pixel 4 [R9]。
- 缺口：这些方案的热信号来自软件（页表/访问位/应用生命周期），没有硬件访问证据；SPE 在手机上的实测，**未找到公开资料**。

#### 2. 业界做法扫描

| 方案 | 年份 | 来源 | 原理 | 局限 |
|---|---|---|---|---|
| ARM SPE 本身 | Armv8.2 起可选特性 | Arm 文档 / perf-arm-spe [R24] | 硬件按间隔从流水线操作中抽样，记录 PC、数据虚拟地址（部分实现含物理地址）、延迟、事件、data source 等 | 可选特性，异构核上不一定全核实现；需 `arm_spe_pmu` 驱动与固件中断描述；部分 CPU 需关闭 KPTI；出现 collision（上一次采样未结束又选中新操作）会丢样 |
| SPE 驱动 NUMA balancing + DAMON（openEuler） | 2025-05（v5，19 patch） | 邮件列表 [R25] | `mem_sampling` 抽象层；SPE 样本替代地址空间扫描与 hint fault；DAMON vaddr 接入；含 SPE boost（TLB 热页、远端访问） | 仅 vaddr；PMD 大页迁移未支持；邮件内无性能数据；仅 OLK-6.6 厂商分支，未上游 |
| DAMON 硬件采样访问报告 | 2026-05（v1）、2026-09-10（v2，9 patch） | LWN 1093677 [R3] | 通用 per-CPU 无锁 ring 接 NMI 采样；PEBS/IBS 已验证；SPE 后端由另一开发者对接 | RFC，未合入；冷判定仍靠 page-fault 原语 |
| pghot（IBS + hint fault） | 2025-03 RFC → 2026-07 v8 | LWN 1092001；lkml [R2] | 每 PFN 一字节记录频率与最近访问时间，kmigrated 批量迁移 | 针对 CXL/多层内存；评审意见不一；无 SPE |
| HeMem | SOSP 2021 | [R5] | PEBS 采样 + 静态阈值 | 阈值静态；PEBS 对部分流量（预取、回写）不敏感 |
| Memtis | SOSP 2023 | [R5][R6] | PEBS + 全局分布动态分级 + 动态采样间隔 | 写采样周期长；第三方评测显示写密集负载差 |
| DAMON（软件区域采样） | 2021 起（5.15 合入，见 A15b） | 仓库 A15b | 区域采样，开销与内存大小无关 | 区域粒度，页级精度靠 young 过滤 |
| ASAP | 2021 | USENIX ATC [R9] | 自适应预取：估计应用切换时所需页 | 软件信号；仅 Pixel 4 评估 |
| Ariadne | 2025 | HPCA [R8] | 热感知组织 + 自适应压缩粒度 + 主动解压 | 热信号为软件侧；Pixel 7 |
| SPE 过滤扩展（FEAT_SPEv1p4、SPE_FDS 等） | 2025 补丁（James Clark 系列 v4–v6，2025-07/08） | patchew [R26] | 增加按 L1D/TLB/LLC/远端事件与 data source 过滤，减少无关样本 | 合入版本：6.19 文档已有 SPEv1p4 过滤位，`inv_data_src_filter` 在 7.0-rc2 文档可见，确切版本**待核实**；需硬件支持 |

**SPE 相关事实补充**
- Linux 驱动 `arm_spe_pmu`；perf 用法见 perf-arm-spe 文档，须设置采样周期 `-c`，默认取最小间隔，文档提示周期过小会让 perf.data 过大 [R24]。
- 2024 年 Leo Yan 的补丁把 Cortex-A720、A725、X925 等加入 perf 的 Arm SPE common data source 编码列表（v3 于 2024-10）；A720 勘误 2926083 仅在 SPE 实现且启用时存在。据此判断这些核实现了 SPE；具体 TRM 条款本次未直接核对（A725 文档号 107652，X925 为 102807，来自 LLVM 提交，待核对）[R27]。
- 量产手机：Arm 2020 年 Streamline 博客称当时没有带 SPE 能力的消费级 Android 设备（六年前，可能已过时）；TF-A 里 SPE 受 EL3 控制，可按核在运行时关闭。**高通、联发科、华为麒麟、苹果等手机 SoC 是否向 Linux 开放 SPE：未找到公开资料**。泰山核主要见于服务器，手机端无公开资料。
- 采样开销：**未找到公开的手机侧开销数据**。openEuler 邮件无数字；DAMON RFC v2 未给 CPU 开销，只给带宽收敛结果 [R3]；pghot 给的是元数据开销（默认每 1TB 低层内存约 256MB，精确模式约 1GB），不是采样 CPU 开销 [R2]。

#### 3. 技术难点

**难点一：手机上采样能不能用、用得起——可用性与开销未知。**
- 难在哪：SPE 为可选特性，异构核（大中小核）不一定全实现；固件可能关闭；采样间隔太小则中断与缓冲区写入带来功耗，太大则热页漏判。无公开手机数据。
- 怎么破：对象是 SPE 采样流，位置在感知层的新增硬件采样模块。（1）立项前先做可用性摸底：各目标 SoC 的 `arm_spe_0` 节点、固件开关、哪些核可采样；（2）采样只开在大核或应用所在核，按 PSI/前台状态动态调间隔；（3）用 SPE 过滤（延迟阈值、data source、事件过滤）只留 DRAM 访问样本，丢弃缓存命中样本。
- 关键突破：按压力和场景自适应的稀疏 SPE 采样。

**难点二：采样只能证明热，证明不了冷。**
- 难在哪：样本是统计抽样，沉默不等于没访问。DAMON RFC 作者已明确此问题 [R3]；HeMem/Memtis 以阈值或分布来规避，也有对预取/回写流量不敏感的批评 [R5][R6]。直接把「没采到」当冷会换出热页，导致 refault 与颠簸。
- 怎么破：对象是匿名页的冷热状态机，位置在建模层。三态证据：（1）热证据：SPE 命中 → 立即标热并带时间戳；（2）冷证据：必须由页表 Accessed 位在窗口内为 0 + MGLRU/DAMON 年龄双确认；（3）未知态：只有「无 SPE 命中且无 Accessed 位」持续多个窗口，才进入冷候选。预取侧只用热证据，所以 KT1-b 本身不受该问题影响，该问题主要压在 KT1-c。
- 关键突破：SPE 管热、页表管冷的非对称证据融合。

**难点三：预取什么、何时预取、预取多少。**
- 难在哪：预取过多反而占内存，把别的页挤出去（AppFlow 的教训：预加载使冷启动次数 +30%）[R11]；预取过晚没用。需要「应用即将切回」的信号，而「按 Agent 语义调整前后台策略」在不做范围内，所以只能用通用信号（任务切换、应用唤起事件、历史重访问集）。
- 怎么破：对象是该应用被换出前的热页集合（SPE 记录）与 zram 中对应的压缩页，位置在决策与执行层。应用切到后台时，记录最近窗口的热页集合作为「恢复集」；切回前台的前几百毫秒批量解压并按块换入；预取量受内存余量预算限制，余量不足则只取最热的前 K 页。
- 关键突破：以换出前热集合为预取目标，按余量封顶。

#### 4. 机制架构

- 感知/建模：`arm_spe_pmu` 采样 → 地址/延迟/data source 过滤 → 物理页号映射 → 每应用（memcg）的热页集合与时间戳；PTE Accessed 位/DAMON 提供冷证据；PSI 与内存余量。
- 决策：预取触发（应用切换/唤起事件）；恢复集选择（热度排序，受余量上限）；采样间隔与开关策略。
- 执行：批量 zram 解压与换入（可使用大 folio 换入，对接 mTHP swap-in [R15]）；对恢复集页提升 LRU 位置，避免立刻被再回收。
- 反馈：预取命中率（预取页被访问比例）、预取浪费率、重启时延、SPE 采样 CPU 占比与功耗；命中率过低自动降低预取量。

#### 5. 目标与度量

| 指标 | 基线 | 目标（区间） | 依据与条件 |
|---|---|---|---|
| 后台应用切回前台时延（匿名页相关部分） | zram 按需换入（立项自测） | -20%～-40% | 依据 ASAP -22.2%（Pixel 4）、Ariadne -50%（Pixel 7，含压缩粒度优化）；SPE 的增量未知，取区间中低位。条件：叠加场景，内存余量 <15% |
| 预取命中率 | — | ≥70% | 工程目标，需实测校准，无公开依据 |
| SPE 采样 CPU 占用 | 未找到公开资料 | ≤1%，功耗增量≤1%（待测） | 目标值为设定，依据缺失，属风险项 |

#### 6. 风险与待核实

- **最大风险**：量产手机 SoC 是否开放 SPE（未找到公开资料）。若不可用，退路为软件信号（DAMON + Accessed 位 + 应用生命周期）驱动同一套预取，此时对 ASAP/Ariadne 的差异化下降。
- SPE data source 与物理地址字段在目标核上的具体语义，需对照对应 TRM（A725/X925 未核对）。
- openEuler 方案无性能数据，不能作为收益依据。
- 上游路线：DAMON 硬件采样 RFC 未合入；SPE 后端进展待跟踪。
- Android GKI 是否带 `CONFIG_ARM_SPE_PMU`、是否可被厂商启用：待核实。
- HarmonyOS NEXT 微内核无 Linux perf/SPE 子系统，需另行适配：未找到公开资料。

#### 7. PPT 素材卡

**挑战**
1. 换入无预取：zram 按需换入，切回前台大批缺页，解压在关键路径。
2. 热信号不准：软件扫描开销与精度互斥，MGLRU 在 Android 多未启用。
3. 采样可用性未知：手机 SPE 是否放开无公开资料。

**目标**：用硬件访问采样识别匿名热页，切回前台前预取，提升叠加场景流畅度。
**量化目标**：切回时延 -20%～-40%

**技术难题**
- 难题一：手机上稀疏采样可用且用得起
  - 可用性摸底：逐 SoC 核查 SPE 节点、固件开关与可采样核。
  - 自适应采样：按压力与场景调间隔，过滤只留 DRAM 访问。
  - 关键突破：自适应稀疏采样
- 难题二：采样证明不了冷
  - 非对称证据：SPE 只作热证据，冷须由访问位与代龄确认。
  - 三态管理：热、冷候选、未知，未知态不换出。
  - 关键突破：SPE 管热页表管冷
- 难题三：预取对象与预取量
  - 恢复集：记录换出前热页，切回前批量换入。
  - 余量封顶：按内存余量限预取量，命中率低则降量。
  - 关键突破：热集合预取加余量封顶

**架构四段**：感知：SPE 采样 / 访问位 / PSI；决策：热集合 / 预取触发 / 采样调度；执行：批量解压 / 大 folio 换入 / LRU 提升；反馈：命中率 / 浪费率 / 采样功耗。

---

### KT1-c 基于同一冷热识别的匿名页换出（zram）

#### 1. 要解决的问题

- 现状：容量冻结（价格 4 倍）使内存压力由回收独自承担 [R23]；Android 回收靠 MGLRU 或经典 LRU 的页龄，匿名页回收偏弱、文件页偏猛 [R7]；zram 之上可做 `recompress`（多算法）与 `writeback`（idle / incompressible 页到后备设备，带限额），见 A15c。厂商另有三星 RAM Plus 把存储当虚拟内存 [R12]。
- 代价：（1）误换出热页导致 refault 与 CPU 解压开销，Ariadne 报告普通 zram 的压缩/解压 CPU 占用比其方案高 15% [R8]；（2）压力顶满则 lmkd 杀进程，AppFlow 显示杀进程使冷启动 + 后台存活下降：三组件合用后台存活应用数为原来 1.85 倍 [R11]。
- 缺口：没有公开数据说明「换出准确率」对 refault 率的定量影响。

#### 2. 业界做法扫描

| 方案 | 年份 | 来源 | 原理 | 局限 |
|---|---|---|---|---|
| zram + recompress + writeback | 内核已有 | kernel.org zram 文档（A15c 引用） | 压缩内存；idle 页二次压缩；idle/不可压页写回后备设备并限额 | 触发依赖用户态策略；写回受闪存寿命约束 |
| MGLRU | 2022（6.1） | [R7] | 多代 LRU 提供更细页龄 | Android 厂商多未启用；匿名页回收偏弱；与热冷应用脱节 |
| DAMON_RECLAIM / DAMOS pageout | 5.16（见 A15b） | 仓库 A15b | 找长期未访问 region 提前回收 | region 粒度；移动端启用情况待核实 |
| memcg 强制回收匿名页 | 荣耀（LSFMM 报告） | LWN [R7] | 对后台应用 memcg 强制回收匿名页 | 厂商私有，细节无公开资料 |
| Ariadne | 2025 | HPCA [R8] | 热感知分区、按热度选压缩粒度 | 热信号为软件侧 |
| Chou 等 | 2023 | ACM TECS [R10] | 识别未用匿名页换入 zram | 切换时延最多 -43%，Pixel |
| mTHP 换入/换出对 zram 的支持 | 2024–2025 | Barry Song、Chuanhua Han 等 [R15] | 大 folio 整体换入，避免碎片 | 具体合入版本待核实 |
| swap table / virtual swap | 6.18 / 提案 | LWN 1059201 [R14] | 重构 swap 元数据 | swap table 合入版本来自二手转述，virtual swap 未合入 |
| 三星 RAM Plus | 2025–2026 | [R12] | 用存储做虚拟内存，可选 2–12GB | 内部机制未公开 |
| OpenHarmony ESwap | 2022 起文档 | [R13] | zswapd 把 zram 压缩页加密换出到 ESwap 分区 | 面向标准系统（Linux 内核）；HarmonyOS NEXT 无公开资料 |
| iOS compressed memory | 长期 | 见 A15c | 压缩器，不落盘 | 无设备内多级接口；是否二次处理待核实 |

#### 3. 技术难点

**难点一：换出准确率——误换出热页的代价极大。**
- 难在哪：见 KT1-b 难点二。换出一个热页要付压缩、再解压、可能的 lmkd 触发；硬件采样「没采到」不代表冷。
- 怎么破：对象是匿名页，位置在建模与决策层。换出候选必须同时满足：SPE 无热证据 + Accessed 位为 0 + 代龄超阈值；按应用 memcg 设预算，先换出已进入后台且冷的应用；每轮换出量由 PSI 反馈闭环控制。
- 关键突破：多证据一致才换出的闭环预算。

**难点二：zram 与闪存分层的预算——压缩收益、CPU、闪存磨损三者博弈。**
- 难在哪：不可压缩页占 DRAM 却压不下去；writeback 带来闪存写放大与寿命问题；解压延迟与能耗在大核上也有成本。
- 怎么破：对象是冷页的目的层选择，位置在执行层。按压缩率分流：可压缩冷页进 zram（可 recompress），不可压缩且长期 idle 的页才限额写回；写回预算按日写入量设上限；与 KT1-a 的软保护共享账本。
- 关键突破：按可压缩性与冷度分流到不同层。

**难点三：与内核既有回收（MGLRU/lmkd）协同而不是替代。**
- 难在哪：内核回收路径与厂商 hook 复杂；LWN 报道显示 MGLRU 的指标与 lmkd 依赖不同 [R7]；内核 swap 子系统也在重构 [R14]。
- 怎么破：对象是回收触发，位置在用户态策略层 + memcg 接口。用 `memory.reclaim` 或 DAMOS 作为执行入口，而不是改核心回收路径；策略参数通过 sysfs/cgroup 暴露。
- 关键突破：以 memcg 接口注入冷页清单，不改内核回收主路径。

#### 4. 机制架构

- 感知/建模：与 KT1-b 共用冷热模型（SPE 热证据 + 访问位冷证据 + 代龄）；PSI、内存余量、zram `mm_stat`、各 memcg 前后台状态。
- 决策：冷候选清单；按应用/按压力的换出配额；zram 与 writeback 的分流阈值。
- 执行：`memory.reclaim`/DAMOS pageout 入口换出到 zram；对 idle 不可压页限额 writeback；大 folio 对齐。
- 反馈：refault 率、换出后 N 秒内被重新访问的比例、lmkd 杀进程次数、压缩率与 CPU 占用、闪存写入量。

#### 5. 目标与度量

| 指标 | 基线 | 目标（区间） | 依据与条件 |
|---|---|---|---|
| 同等 DRAM 下后台存活应用数 | 立项自测 | +30%～+80% | 依据 AppFlow 三组件合用 1.85 倍（含预加载与杀进程策略），本技术只占其中；取中低位 |
| 误换出率（换出后 5 秒内 refault） | 待测 | ≤10% | 工程目标，无公开依据 |
| lmkd 杀进程次数（叠加场景） | 待测 | -30% 以上 | 估算，依据 AppFlow 杀进程组件 -30% 冷启动次数 |
| 闪存写入 | — | 日写入上限（如≤原 swap 方案的 50%） | 目标由寿命预算推出，待测 |

#### 6. 风险与待核实

- 误换出导致颠簸，需要保守阈值与熔断。
- 闪存写入与寿命：writeback 需要预算；厂商 RAM Plus 的磨损处理无公开资料。
- 压缩收益与 CPU/功耗：未做功耗实测。
- 内核版本与 swap 重构：swap table、mTHP swap-in 的具体版本待核实；基线内核需锁定。
- iOS 与 HarmonyOS NEXT：iOS 压缩器细节待核实；NEXT 无公开资料。
- 范围：本技术不做「按 Agent 语义调前后台资源」，只用通用的前后台与压力信号。

#### 7. PPT 素材卡

**挑战**
1. 容量被冻结：移动 DRAM 价格涨 4 倍，只能靠回收腾空间。
2. 换出不准：误换热页引发 refault，Android 匿名页回收偏弱。
3. 杀进程代价高：压力顶满杀后台，冷启动与存活双输。

**目标**：基于同一冷热识别换出冷匿名页到 zram，不加 DRAM 提升有效容量。
**量化目标**：后台存活 +30%～+80%

**技术难题**
- 难题一：换出准确率
  - 多证据一致：无 SPE 热证据、访问位为 0、代龄达标才换出。
  - 闭环预算：按应用设配额，PSI 反馈调节换出量。
  - 关键突破：多证据一致才换出
- 难题二：压缩、CPU、闪存的预算博弈
  - 分流：可压缩冷页入 zram，不可压且 idle 才写回。
  - 写入封顶：按日写入量限额，与 .so 保护共账本。
  - 关键突破：按可压缩性和冷度分流
- 难题三：与内核回收协同
  - memcg 注入：用 memory.reclaim 或 DAMOS 作入口。
  - 不改主路径：策略放用户态，参数可调。
  - 关键突破：冷页清单注入而非改核

**架构四段**：感知：冷热模型 / PSI / mm_stat；决策：冷候选 / 配额 / 分流阈值；执行：memory.reclaim / zram / 限额写回；反馈：refault 率 / 杀进程数 / 写入量。

---

## 对立项的启示（本模块）

1. KT1-b 的立项成败取决于「手机 SPE 可用性」这一个前置事实，建议立项时把「SoC 摸底 + 开销实测」作为第 0 阶段里程碑，并预设软件信号退路。
2. KT1-b/c 必须共用一个「热证据 SPE、冷证据页表」的非对称冷热模型，否则预取与换出各做各的，既重复又相互冲突。
3. KT1-a 与 KT1-c 共用同一份内存预算账本，AppFlow 的消融数据是直接论据。
4. 工程路线上优先对接 DAMON 硬件采样 RFC 的 ring 抽象，避免长期独立维护 openEuler 式分支。

---

## 参考资料

| 编号 | 标题 | URL | 日期 |
|---|---|---|---|
| R1 | [RFC PATCH 0/4] Kernel daemon for detecting and promoting hot pages（pghot 早期，AMD） | https://lkml.iu.edu/hypermail/linux/kernel/2503.0/08025.html | 2025-03 |
| R2 | pghot v8 "mm: Hot page tracking and promotion infrastructure"；LWN 对其讨论 | https://lkml.iu.edu/2607.3/07077.html ；https://lwn.net/Articles/1092001/ | 2026-07-28 前后；LWN 2026-09-03 |
| R3 | LWN：DAMON 硬件采样访问报告 RFC v2 | https://lwn.net/Articles/1093677/ ；https://patchew.org/linux/20260529165640.820-1-ravis.opensrc@gmail.com/ | v2 2026-09-10；v1 2026-05 |
| R4 | [RFC PATCH 0/7] mm/damon: hardware-sampled access reports + AMD IBS Op example | https://lkml.iu.edu/2605.2/00650.html | 2026-05 |
| R5 | HeMem（SOSP 2021）、Memtis（SOSP 2023）论文页 | https://cosmoss-jigu.github.io/pages/pubs/memtis-lee-sosp23.pdf | 2023 |
| R6 | From Good to Great: Improving Memory Tiering Performance Through Parameter Tuning | https://arxiv.org/pdf/2504.18714 | 2025-04 |
| R7 | LWN：MGLRU 在 Android 上的问题（LSFMM 议题） | https://lwn.net/Articles/1060967/ | 2026-03-05 |
| R8 | Ariadne（HPCA 2025） | https://arxiv.org/abs/2502.12826 | 2025-02 |
| R9 | ASAP: Fast Mobile Application Switch via Adaptive Prepaging（ATC 2021） | https://www.usenix.org/conference/atc21/presentation/son | 2021 |
| R10 | Chou 等 ACM TECS 2023（DOI 10.1145/3607937）；MemSaver ICPE 2024 | https://api.crossref.org/works/10.1145%2F3607937 ；https://research.spec.org/icpe_proceedings/2024/proceedings/p267.pdf | 2023；2024 |
| R11 | AppFlow: Memory Scheduling for Cold Launch of Large Apps（MobiCom 2026） | https://arxiv.org/abs/2603.17259 | 2026-03-18 |
| R12 | Samsung RAM Plus / One UI 8 虚拟内存选项报道 | https://9to5google.com/2025/05/02/one-ui-increases-ram-plus/ | 2025-05-02（传闻级，稳定版待核实） |
| R13 | OpenHarmony kernel-standard-mm-eswap 文档（仅检索摘要，页面抓取失败） | https://gitcode.com/openharmony/docs/blob/master/en/device-dev/kernel/kernel-standard-mm-eswap.md | 日期待核实 |
| R14 | LWN：Modernizing swapping: virtual swap spaces；swap table 概述 | https://lwn.net/Articles/1059201 | 2026-02 前后 |
| R15 | mm: support large folios swap-in for sync io devices（commit 242d12c9） | https://upd.dev/kernel/linux/commit/242d12c98174 | 合入版本待核实 |
| R16 | LWN：Stabilizing per-VMA locking；LWN 906852 | https://lwn.net/Articles/937943 | 2023-07 |
| R17 | kernelnewbies Linux 6.5 | https://kernelnewbies.org/Linux_6.5 | 2023-08 |
| R18 | openEuler：Handle more faults under the VMA lock 回移植（OLK-6.6 v2） | https://mailweb.openeuler.org/archives/list/kernel@openeuler.org/thread/BOA4N5D5I6AZIOQV5BKTK4F2JBETTTR2/ | 2023-11-29 |
| R19 | Ryan Roberts exec folio 系列 v5；Usama Arif contpte-sized exec folios for 16K/64K | https://lists.infradead.org/pipermail/linux-arm-kernel/2025-July/1044848.html ；https://lkml.iu.edu/2603.1/12745.html | 2025-07；2026-03-10/13 |
| R20 | Minchan Kim：mm: don't be stuck to rmap lock on reclaim path v4 | https://lore.kernel.org/lkml/Yn1mJEjP3LH8rl3t@google.com/T/ | 2022-05 |
| R21 | RWH_RMAP_EXCLUDE 补丁（Hygon，Yibin Liu） | https://ci.syzbot.org/patches/e4fdf2a4-77ea-45eb-b468-e8cb0f061bb4 | 日期未知 |
| R22 | Android：Support 16 KB page sizes | https://developer.android.com/guide/practices/page-sizes | 页面持续更新（访问 2026-11） |
| R23 | TrendForce Mobile DRAM Contract Price 3Q26 | https://www.trendforce.com/research/download/RP260803NC | 2026-08-03 |
| R24 | perf-arm-spe 文档（内核树镜像） | https://git.radix-linux.su/kernel/linux.git/tree/tools/perf/Documentation/perf-arm-spe.txt?h=v6.19.11 | 内核 v6.19.11 |
| R25 | openEuler：Memory access profiler(SPE) driven NUMA balancing and damon v5 | https://mailweb.openeuler.org/archives/list/kernel@openeuler.org/thread/2NBPOUJ3576U7TEIT3CLQZ5376LWSRGE/ | 2025-05-19 |
| R26 | perf: arm_spe: Armv8.8 SPE features v6（James Clark） | https://patchew.org/linux/20250808-james-perf-feat._5Fspe._5Feft-v6-0-6daf498578c8@linaro.org | 2025-08 |
| R27 | perf arm-spe: Add Cortex CPUs to common data source encoding list（Leo Yan v3）；Arm SPE 概述博客 | https://lists.infradead.org/pipermail/linux-arm-kernel/2024-October/965926.html ；https://developer.arm.com/community/arm-community-blogs/b/tools-software-ides-blog/posts/introduction-to-statistical-profiling-support-in-streamline | 2024-10；2020 |

## 待核实清单

1. per-VMA lock 对「需要 I/O 的文件缺页 / COW / 共享写缺页」的主线合入版本（印象 6.6，未核）。
2. exec_folio_order / preferred_exec_order 的主线合入版本；arm64 contpte 基础支持版本（印象 6.9）。
3. FEAT_SPEv1p4 过滤、SPE_FDS（`inv_data_src_filter`）合入的具体内核版本（6.19 文档可见 v1p4 位，7.0-rc2 文档可见 FDS）。
4. Cortex-A725 / X925 TRM 中 SPE 条款（文档号 107652 / 102807 来自 LLVM 提交，未直接核对）。
5. 量产手机 SoC（高通、联发科、麒麟、苹果等）是否向 Linux 开放 SPE，及 Android GKI 是否带 `CONFIG_ARM_SPE_PMU`：未找到公开资料。
6. 手机侧 SPE 采样的 CPU 与功耗开销：未找到公开资料。
7. Arm SPE 后端接入 DAMON 硬件采样 ring 的具体补丁与作者：LWN 仅提及「另一开发者」，未找到具体邮件。
8. swap table 合入 6.18（二手转述）；mTHP 大 folio swap-in 的合入版本。
9. OpenHarmony ESwap 文档全文细节（本次只有检索摘要）；HarmonyOS NEXT 微内核的页回收、换出、.so 页管理：未找到公开资料。
10. 国内厂商（华为以外的 vivo、OPPO、小米、荣耀）内存扩展与批量换入的实现细节：检索未找到具体资料；荣耀 memcg 强制回收仅见 LWN 一句转述。
11. iOS 压缩器是否对冷压缩页做二次处理（沿用 A15c 待核实项）。
12. Google LPC 2022 的 Pixel 6 MGLRU 评估原稿（-47.10% 为检索摘要）。
13. 2026 年旗舰与中端机型的 RAM 容量实际变化：渠道报道均为传闻，未采用；需用 Counterpoint / IDC 等原始数据补。
14. 「共享库页被逐出导致冷启动变慢」的手机侧专项公开数据：未找到公开资料。
15. Hygon RWH_RMAP_EXCLUDE 补丁的日期与评审状态。

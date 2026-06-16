# A16b · 基于 XVM(eBPF) 的 LRU 主动感知优化（让冷热"策略"可编程）

> **一句话定位**：[A16a](A16a-LRU主动扫描.md) 让内核**主动地扫**内存判冷热，但"按什么规则判冷热"仍是写死在内核里的一套启发式。本篇讲下一步——**把"判冷热、保护谁、回收谁"的策略本身做成可编程的**：用 eBPF 把自定义逻辑挂进内核的 LRU/回收路径，按机型、按场景、按整机多 app 的全局视角下发策略。**XVM 是 HarmonyOS 基于 eBPF 做这件事的框架**（据本系列口径，主要用于**整机文件页 LRU** 管理，或扩展到匿名页；**其公开技术细节稀薄，本篇据可证的通用机制立论，XVM 具体接口/版本一律标「待核实」**）。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「2B 物理与回收侧 · LRU 冷热」格的**可编程化改造**——把策略从内核硬编码挪成可下发的程序。
> 🧭 **阅读前置**：先读 [A16a LRU 主动扫描](A16a-LRU主动扫描.md)（主动获取冷热信号，本篇在其上"编排策略"）、[A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md)（LRU/MGLRU/DAMON，DAMON 已是"可编程监控"，本篇把可编程推进到"策略"）；平台落点见 [A14-HarmonyOS 内存实现](../platforms/A14-HarmonyOS-内存实现.md)（**当前无 XVM 内容，本篇首次填补该缺口**）。
> 🌡️ **演进分级**：**演进厚 ⚡（最高 sourcing 风险）**——eBPF-for-mm 在 Linux 也才研究/RFC 阶段，XVM 公开资料更少；**行文重在通用机制 + 趋势，事实性专名集中到「待核实」**。

---

## 1. 定位：从"主动扫描"到"可编程的冷热策略"

[A16a](A16a-LRU主动扫描.md) 解决了**触发与扫描**：内核能在压力前主动看一遍内存、给页排冷热。但它没碰一个更深的问题——

> **"什么算冷、谁该被保护、按什么次序回收"，这套策略是写死在内核里的。** MGLRU 的代际老化、LRU 的 active/inactive 晋升降级，规则都固定；想换一套（比如"给后台 agent 的长任务页一个保护期"），传统上只能改内核、重新编译、重启。

本篇要补的是**可编程**这一维：

> **把 LRU/回收路径上的"判决"开成一个可挂载自定义程序的钩子**——内核走到"这页要不要回收"时，回调一段外部下发的逻辑，由它说"保护 / 回收 / 用默认"。**XVM 就是 HarmonyOS 用 eBPF 实现这条思路的框架**。

这与 [A05](../foundations/A05-冷热识别的演进.md) 的 DAMON 是递进关系：**DAMON 让"监控（感知）"可编程，XVM/eBPF 把可编程推进到"策略（动作判决）"**。

## 2. 负载动因：一套写死的启发式，喂不饱异构叠加的负载

本篇与 [A16a](A16a-LRU主动扫描.md) 同属 A16「**冷热**」轴，但动因更进一层。[A16a §2](A16a-LRU主动扫描.md) 已说明：Agent 时代"前台热/后台冷"的场景启发式失效。这里要补的是——**即便主动扫描拿到了真实访问，"如何据此判决"也不该是一套写死的规则**：

- **整机、多 app 的全局视角**（终端立场，A16 三特征里「异构」的多任务侧）：终端是**几十个 app + 系统服务 + agent 后台任务**共处一机。"该保护谁"是一个**整机级**的权衡——前台 app 的工作集、后台 agent 的长任务页、共享库的文件页，孰先孰后，**随产品形态、机型内存档位、用户习惯而变**。一套内核默认值不可能对所有机型都最优。**XVM 主打"整机文件页 LRU"正是这个全局视角**：文件页（代码、共享库、资源）是多 app 共享、最值得整机统一调度的部分。
- **策略要能快速迭代、按机型下发**：厂商需要在不改内核基线（尤其 Android GKI / 鸿蒙统一内核）的前提下，**给不同机型/场景下发不同的回收策略**——这正是 eBPF"**不改内核、不重启、可热插拔**"的拿手好戏。
- **场景化保护**：给"正在跑长程任务的后台 agent"一个有时限的保护、对"刚切后台但马上回来的 app"延后回收——这类**带语义的策略**，硬编码 LRU 表达不了，可编程钩子才能。

> 一句话动因：**异构叠加的整机负载下，"按什么规则判冷热"本身需要随机型/场景可变——把策略从内核硬编码解放成可下发的程序，是冷热治理的必然一步。**

## 3. 机制本体：eBPF 怎么把内核 mm 路径变成可编程

### 3.1 eBPF 与 struct_ops：不改内核地"插"逻辑进去

**eBPF** 是一项内核技术：把经过校验器（verifier）安全检查的用户程序，挂到内核各类钩子点，在事件触发时**在内核态执行**——**无需内核模块、无需重启**即让内核可编程。其中 **BPF `struct_ops`** 机制尤为关键：它让一段 BPF 程序去**实现某个内核操作结构体的回调**，相当于把自定义逻辑"插"进某个内核子系统。近年 `struct_ops` 被做得更通用，能挂的子系统范围在扩大——**把它用到内存管理的回收/LRU 路径，正是 XVM 这类工作的技术底座**。

### 3.2 Linux 侧的可证同类：可编程回收的雏形

XVM 的具体实现公开很少，但**它要做的事，在 Linux 上已有清晰、可引用的同类研究**，用它们来锚定"可编程 LRU"长什么样：

- **eBPF-mm（用户态引导的内存管理）**：把 BPF 程序挂到**内核页回收路径**；当内核要回收内存时回调它，程序检视页的元数据后返回**判决：`PROTECT`（留下）/ `EVICT`（回收）/ `PASS`（走内核默认）**——这正是"让应用/策略参与回收判决"的最小骨架（[eBPF-mm, arXiv 2409.11220](https://arxiv.org/pdf/2409.11220)）。
- **"Cache is King：用 eBPF 做智能页淘汰"**：把页淘汰策略用 eBPF 表达，按负载定制，而非用内核一刀切的 LRU（[Cache is King, arXiv 2502.02750](https://arxiv.org/html/2502.02750v1)）。
- **DAMON/DAMOS + BPF**：[A15b](A15b-DAMON与分层内存实践.md) 的 DAMON 已是"用户态可控的回收策略工具箱"，与 BPF 结合可进一步把判决逻辑下放。
- 这些都在 **LSFMM+BPF 2024** 这类上游场合被讨论（[LSFMM+BPF 2024, LWN](https://lwn.net/Articles/lsfmmbpf2024/)），属**研究/RFC 热点而非稳定特性**。

> **术语警示**：上面这些是 **Linux 的研究同类**，用来说明"可编程 LRU"的形态；**它们不是 XVM**。XVM 是 HarmonyOS 自有的框架名，**别把 eBPF-mm 的 `PROTECT/EVICT/PASS` 接口当成 XVM 的接口**——XVM 的真实接口待核实。

### 3.3 XVM：HarmonyOS 用 eBPF 做整机文件页 LRU（细节待核实）

据本系列口径，**XVM 是 HarmonyOS 基于 eBPF 的内存管理框架，主要用于整机文件页 LRU 的主动感知与管理，并可能扩展到匿名页**。把它放进 HarmonyOS 的架构里看，有一条**自洽但需核实的线索**：

- [A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md) 记载 HarmonyOS NEXT 内核采用 **"policy-free kernel paging"（机制在内核、策略可下放）**，出自其 OSDI '24 微内核论文（[Microkernel Goes General, OSDI 2024](https://www.usenix.org/system/files/osdi24-chen-haibo.pdf)）。
- "机制在内核、策略可下放"恰恰需要一个**承接下放策略的载体**——eBPF/XVM 是这个载体的天然候选：内核保留 LRU/回收的**机制**，把"判冷热、保护谁"的**策略**交给 XVM 程序。

但必须诚实：**这条"XVM = policy-free paging 的策略载体"是合理推测，公开资料未坐实**；OSDI'24 论文是否点名 XVM、XVM 的挂载点/判决接口/是否真覆盖匿名页，**均待据一手（华为/OpenHarmony 资料、论文原文）核实**。本篇**不编造 XVM 的接口与版本**。

> **关键诚实声明**：[A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md) 当前**完全没有 XVM 相关内容**（其文件页 LRU 仅记到 LiteOS-A 的 active/inactive 双链）。本篇是本系列**第一次正面处理 XVM**，且大部分以「待核实」呈现——这是 sourcing 现状的如实反映，不是覆盖度的暗示。

## 4. 历史：冷热的"判决权"如何从内核走向可编程

```
硬编码 LRU 启发式（active/inactive 晋升降级，规则写死内核）
   ▼ MGLRU（kernel 6.1）：代际老化更准，但策略仍固定
   ▼ DAMON/DAMOS（监控可编程、用户态可控回收策略）—— A05/A15b
      "感知"先可编程化
   ▼ eBPF struct_ops + eBPF-mm / Cache-is-King（研究/RFC，2024–25）
      "判决（PROTECT/EVICT/PASS）"开始可编程化
   ▼ XVM（HarmonyOS）：用 eBPF 做整机文件页 LRU 的可编程主动感知
      （细节待核实）
```

主线：**冷热治理的"判决权"在逐步从内核硬编码，下放到可被外部策略编程的钩子**。DAMON 解放了"感知"，eBPF-for-mm 正在解放"动作判决"，XVM 是终端侧把这套思路落到"整机文件页"的一个实例。

## 5. 现状与平台差异

| 维度 | Android（Linux / GKI） | HarmonyOS | iOS / Darwin |
|---|---|---|---|
| 冷热策略形态 | MGLRU 固定策略 + DAMON 可编程监控；**eBPF 改回收策略仍属研究/RFC，未成稳定特性** | **XVM（eBPF）做整机文件页 LRU（待核实）**；内核侧 policy-free paging（OSDI'24） | 无 eBPF；XNU 自有 pageout/compressor 策略，外部不可编程 |
| 可编程程度 | 监控可编程；策略可编程在路上 | 据口径"策略可下放"，XVM 承接（**接口待核实**） | 不可编程 |
| 整机 vs 单 app | per-memcg 作用域（[A07](../foundations/A07-cgroup-memcg.md)）；整机文件页全局 LRU | **XVM 主打整机文件页全局视角** | 系统统管 |

> **术语警示（再强调）**：XVM 是 HarmonyOS 术语，**≠ 通用 "eBPF-for-mm"**；Linux 的 eBPF-mm/Cache-is-King 是另一套独立研究。三者思路同源、实现与命名各异，**对比时务必分清平台**。

## 6. 趋势与未解问题 ← 本篇重心

- **可编程的"安全边界"**：mm 是性能与稳定的核心路径，让外部程序参与回收判决，要受 eBPF **校验器**严格约束（不能死循环、不能越权访存、执行时间有界）。"既要足够表达力写出有用策略，又不危及内核稳定"如何平衡，是 eBPF-for-mm 的核心难题（上游 LSFMM 持续争论）。
- **谁来写策略、如何不打架**：厂商、系统、甚至 app 都可能想下发策略——**整机全局最优 vs 各自局部最优**的冲突如何仲裁？多段 XVM 程序并存时的优先级与公平性（呼应 [A16d](A16d-压缩IP边际建模.md) 的预算分配）尚无框架。
- **文件页之外**：XVM"可能扩展到匿名页"——但匿名页回收牵涉 swap/压缩（[A06](../foundations/A06-压缩与换页.md)）、refault 代价更直接，可编程策略的风险更高；这一步是否、如何走，**待核实**。
- **与主动扫描/边际建模的协同**：理想闭环是 [A16a](A16a-LRU主动扫描.md) 主动扫描供冷热信号 → XVM 据整机策略判决 → [A16d](A16d-压缩IP边际建模.md) 在预算内决定压多狠。三者怎么拼成一套**可下发、可观测、可回滚**的系统，是终端冷热治理的开放工程。
- **XVM 本身的公开化**：当前最大未解是**资料**——XVM 的挂载点、判决语义、覆盖范围、在量产机的启用，全部待一手核实。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| 冷热信号 ← 主动扫描 | XVM 在主动扫描拿到的访问之上"编排策略" | **[A16a](A16a-LRU主动扫描.md)** |
| 可编程监控 ← DAMON | "感知可编程"的前一步，XVM 推进到"策略可编程" | **[A05](../foundations/A05-冷热识别的演进.md)、[A15b](A15b-DAMON与分层内存实践.md)** |
| 作用域 ← memcg | 策略需在 per-app / 整机两个尺度协调 | [A07](../foundations/A07-cgroup-memcg.md) |
| 平台落点 ← HarmonyOS | policy-free paging 的策略载体（推测） | **[A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md)** |
| 判决后果 → 压缩/边际 | 判"回收"后压多狠由边际模型定 | [A16c](A16c-异构压缩CDSD.md)、[A16d](A16d-压缩IP边际建模.md) |

## 8. 实测 / 观测点

- Linux 通用 eBPF：`bpftool prog`/`bpftool struct_ops` 看已挂载的 BPF 程序与 struct_ops；
- DAMON：`/sys/kernel/mm/damon/`（可编程监控 + 用户态可控回收，[A15b](A15b-DAMON与分层内存实践.md)）；
- 整机文件页 LRU 现状：`/proc/meminfo` 的 `Active(file)`/`Inactive(file)`、`/proc/vmstat` 的 `pgscan_file`/`pgsteal_file`；
- **XVM 专属观测口径：待核实**（无公开 sysfs/工具文档）。

## 9. 来源与延伸阅读

**eBPF 与可编程内核子系统（机制底座）**
- [eBPF Tutorial: Extending Kernel Subsystems with BPF struct_ops (eunomia)](https://eunomia.dev/tutorials/features/struct_ops/) —— `struct_ops` 把自定义逻辑插进内核子系统
- [eBPF Ecosystem Progress in 2024–2025 (eunomia)](https://eunomia.dev/blog/2025/02/12/ebpf-ecosystem-progress-in-20242025-a-technical-deep-dive/)

**eBPF 用于内存回收 / 页淘汰（Linux 可证同类，非 XVM）**
- [eBPF-mm: Userspace-guided memory management in Linux with eBPF (arXiv 2409.11220)](https://arxiv.org/pdf/2409.11220) —— 回收路径 BPF 判决 `PROTECT/EVICT/PASS`
- [Cache is King: Smart Page Eviction with eBPF (arXiv 2502.02750)](https://arxiv.org/html/2502.02750v1)
- [The 2024 LSFMM+BPF Summit (LWN)](https://lwn.net/Articles/lsfmmbpf2024/) —— 可编程 mm 的上游讨论
- DAMON 可编程监控/回收：见 [A05](../foundations/A05-冷热识别的演进.md)、[A15b](A15b-DAMON与分层内存实践.md)

**HarmonyOS 内核（XVM 的可能落点，细节待核实）**
- [Microkernel Goes General: Performance and Compatibility (OSDI 2024)](https://www.usenix.org/system/files/osdi24-chen-haibo.pdf) —— HarmonyOS NEXT 微内核、policy-free kernel paging（机制/策略分离）
- [A14-HarmonyOS 内存实现](../platforms/A14-HarmonyOS-内存实现.md) —— 当前无 XVM 内容（本篇首次处理）

**承接 / 相邻篇**
- [A16a LRU 主动扫描](A16a-LRU主动扫描.md)、[A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md)、[A15b DAMON 与分层内存实践](A15b-DAMON与分层内存实践.md)、[A16d 压缩 IP 边际建模](A16d-压缩IP边际建模.md)、[A07 cgroup/memcg](../foundations/A07-cgroup-memcg.md)

> **待核实 / 待补**：**XVM 的确切定义、挂载点/判决接口、是否覆盖匿名页、在量产 HarmonyOS 的启用与机型覆盖**（公开资料稀薄，全部待一手）；XVM 与 OSDI'24 "policy-free kernel paging" 的确切关系（本篇为推测）；OpenHarmony 仓库中 XVM/eBPF-mm 相关代码是否存在及其形态；Linux eBPF-for-mm（eBPF-mm/Cache-is-King）是否/何时进入主线（现为研究/RFC）；Android GKI 是否引入等价的 eBPF 回收策略钩子；XVM 与 [A16a](A16a-LRU主动扫描.md) 主动扫描、[A16d](A16d-压缩IP边际建模.md) 边际建模如何在产品上拼成闭环。

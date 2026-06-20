# A16b · eBPF 可编程回收策略：Android 的学界研究与业界实践（让冷热"判决"可下放）

> **一句话定位**：[A16a](A16a-LRU主动扫描.md) 让内核**主动地扫**内存判冷热，但"按什么规则判冷热、回收谁"仍写死在内核里。本篇讲下一步——**把"判冷热、保护谁、回收谁"的策略本身做成可编程的**：用 **eBPF（尤其 `struct_ops`）** 把自定义逻辑挂进内核回收/LRU 路径。锚点放在 **Android 与 Linux 上游**：Android 上 eBPF 已是生产级基础设施（但用于网络/tracing/GPU，不是内存回收），可编程回收策略则是**学界与上游内核社区正在推进、尚未进主线**的前沿。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「2B 物理与回收侧 · LRU 冷热」格的**可编程化改造**——把策略从内核硬编码挪成可下放的程序。
> 🧭 **阅读前置**：先读 [A16a LRU 主动扫描](A16a-LRU主动扫描.md)（主动获取冷热信号，本篇在其上"编排策略"）、[A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md)（LRU/MGLRU/DAMON，DAMON 已是"可编程监控"，本篇把可编程推进到"策略"）。
> 🌡️ **演进分级**：**演进厚 ⚡**，但 sourcing 较前稿大幅改善——Android 加载模型、MGLRU 来源、上游 eBPF-mm/BPF-OOM/sched_ext 均有一手或权威源；**风险点不在"有没有这些机制"，而在"它们在 Android 上是否、何时用于内存回收"——本篇据此把"已实践 / 研究 / 准备"三层严格分开**。

---

> **⚠️ 本篇立场（先读）**：本篇讨论的「在 eBPF 之上做面向 Agent 负载的整机可编程回收」是**基于学界研究与上游内核动向的设计探讨与可行性分析**。需先厘清两个层次：**① eBPF 在 Android 已是生产级基础设施**——但官方用途是**网络流量统计、tracing、GPU 内存 profiling**，**不是内存回收**；**② 用 eBPF 编程内存回收/淘汰策略**（eBPF-mm、BPF-OOM、cachebpf 等）目前是**Linux 上游的研究 / RFC，无一进主线**，Android 更未启用。全篇区分**已落地的实践**、**学界与上游研究**、**业界准备与趋势**三层，不把后两层说成现状。鸿蒙的 XVM 路线公开资料稀薄，本系列不展开，仅在 §5 / §6 各一句点到（见 [A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md)）。

## 1. 定位：从"主动扫描"到"可编程的冷热策略"

[A16a](A16a-LRU主动扫描.md) 解决了**触发与扫描**：内核能在压力前主动看一遍内存、给页排冷热。但它没碰一个更深的问题——

> **"什么算冷、谁该被保护、按什么次序回收"，这套策略是写死在内核里的。** MGLRU 的代际老化、LRU 的 active/inactive 晋升降级，规则都固定；想换一套（比如"给后台 agent 的长任务页一个保护期"），传统上只能改内核、重新编译、重启。

本篇要补的是**可编程**这一维：

> **把 LRU/回收路径上的"判决"开成一个可挂载自定义程序的钩子**——内核走到"这页要不要回收 / 该 OOM-kill 谁"时，回调一段外部下发的逻辑，由它说"保护 / 回收 / 用默认"。这条思路在 Linux 上游已有多个具体提案（§3），在 Android 上则受其**特有的 eBPF 加载模型**约束（§3.2、§5）。

这与 [A05](../foundations/A05-冷热识别的演进.md) 的 DAMON 是递进关系：**DAMON 让"监控（感知）"可编程，eBPF-for-mm 把可编程推进到"策略（动作判决）"**。

## 2. 负载动因：一套写死的启发式，喂不饱异构叠加的负载

本篇与 [A16a](A16a-LRU主动扫描.md) 同属 A16「**冷热**」轴，但动因更进一层。[A16a §2](A16a-LRU主动扫描.md) 已说明：Agent 时代"前台热/后台冷"的场景启发式失效。这里要补的是——**即便主动扫描拿到了真实访问，"如何据此判决"也不该是一套写死的规则**：

- **整机、多 app 的全局视角**（终端立场，A16 三特征里「异构」的多任务侧）：终端是**几十个 app + 系统服务 + agent 后台任务**共处一机。"该保护谁"是一个**整机级**的权衡——前台 app 的工作集、后台 agent 的长任务页、共享库的文件页，孰先孰后，**随产品形态、机型内存档位、用户习惯而变**。一套内核默认值不可能对所有机型都最优。
- **策略要能快速迭代、按机型下发**：厂商需要在不改内核基线（尤其 Android **GKI** 统一内核）的前提下，**给不同机型/场景下发不同的回收策略**——这正是 eBPF"**不改内核、不重启、可挂载**"的拿手好戏。**但在 Android 上"谁能下发"被严格限制**（§3.2）。
- **场景化保护**：给"正在跑长程任务的后台 agent"一个有时限的保护、对"刚切后台但马上回来的 app"延后回收——这类**带语义的策略**，硬编码 LRU 表达不了，可编程钩子才能。

> 一句话动因：**异构叠加的整机负载下，"按什么规则判冷热"本身需要随机型/场景可变——把策略从内核硬编码解放成可下发的程序，是冷热治理的方向。问题只剩：在 Android 这套加载受限的体系里，这一步能走多远、由谁来走。**

## 3. 机制本体：eBPF 怎么把内核 mm 路径变成可编程

### 3.1 eBPF 与 struct_ops：不改内核地"插"逻辑进去

**eBPF** 是一项内核技术：把经过校验器（verifier）安全检查的用户程序，挂到内核各类钩子点，在事件触发时**在内核态执行**——**无需内核模块、无需重启**即让内核可编程。其中 **BPF `struct_ops`** 机制尤为关键：它让一段 BPF 程序去**实现某个内核操作结构体的回调**，相当于把自定义逻辑"插"进某个内核子系统（[eBPF struct_ops 教程, eunomia](https://eunomia.dev/tutorials/features/struct_ops/)）。

`struct_ops` 不是纸面设想——**它已经把一个核心内核策略整建制搬成了可编程**：**`sched_ext`（可扩展调度类）于 Linux 6.12 合入主线**，允许把**CPU 调度策略**写成 BPF 程序加载（[Sched_ext Merged For Linux 6.12, Phoronix](https://www.phoronix.com/news/Linux-6.12-Lands-sched-ext)；[Extensible Scheduler Class, kernel.org](https://docs.kernel.org/scheduler/sched-ext.html)）。**把同样的 `struct_ops` 思路用到内存管理的回收/LRU/OOM 路径，正是本篇讨论的方向**——只是它在 mm 子系统还没走完（§3.3、§6）。

### 3.2 Android 侧的现实：eBPF 是生产级的，但被"开机、签名、门控"框死

讨论"Android 上的可编程回收"，绕不开 Android **特有的 eBPF 加载模型**——它决定了"谁能下发策略"：

- **开机由 `bpfloader` 统一加载**：Android 把预编译的 eBPF 程序放在 **`/system/etc/bpf/`**，开机时由特权进程 **`bpfloader`** 载入内核，并 **pin 到 `/sys/fs/bpf/`** 供用户态按 fd 访问（[Extend the kernel with eBPF, AOSP](https://source.android.com/docs/core/architecture/kernel/bpf)）。
- **权限门控 + 签名预加载**：程序用 `DEFINE_BPF_PROG()` 声明所需 **AID（如 `AID_ROOT`/`AID_SYSTEM`）**，并经签名/认证预加载（上游有 "secure and authenticated preloading of eBPF programs" 的工作）。
- **App 不能运行时动态加载 eBPF**：截至目前，Android **没有为第三方 App 提供良好的动态加载链路**——CO-RE/BTF + libbpf 的那套编译分发依赖 Linux 环境，在 Android 上跑得并不顺（[eBPF on Android 教程, eunomia](https://eunomia.dev/tutorials/22-android/)）。BTF 支持在 Android T 周期才加进 `bpfloader`。
- **官方在用 eBPF 做什么**：**网络流量统计（netd / cgroup socket filter，自 Android 9）、tracing（如 `time_in_state` 统计 CPU 各频点驻留）、GPU 内存全局 profiling（Android 12+）**（[AOSP eBPF](https://source.android.com/docs/core/architecture/kernel/bpf)、[eBPF traffic monitoring, AOSP](https://source.android.com/docs/core/data/ebpf-traffic-monitor)）。**注意：这张清单里没有"内存回收/LRU"。**

> **关键推论（本篇原创洞察）**：Android 的 eBPF 是**开机、签名、AID 门控、仅随系统镜像下发**的。所以**即便上游把可编程回收做进内核，在 Android 上它也只会是 OEM / Google 随 GKI/系统下发的杠杆，而不是第三方 App 或运行时可注入的策略**。这与服务器 eBPF "运维随时挂载" 的玩法根本不同——终端的"可编程"，是**厂商侧的可配置**，不是开放生态的可编程。

### 3.3 上游的可编程回收：已有清晰、可引用的同类，但无一进主线

"让外部策略参与回收判决"在 Linux 上游已有一串具体提案，可用来锚定"可编程回收"长什么样——**但要诚实：它们目前都是研究 / RFC，没有一个进主线**（[Controlling memory management with BPF, LWN 2026](https://lwn.net/Articles/1072538/)）：

- **eBPF-mm（用户态引导的内存管理）**：把 BPF 程序挂到**内核页回收路径**；回收时回调它，程序检视页元数据后返回**判决：`PROTECT`（留下）/ `EVICT`（回收）/ `PASS`（走内核默认）**——"让策略参与回收判决"的最小骨架（[eBPF-mm, arXiv 2409.11220](https://arxiv.org/pdf/2409.11220)）。
- **Cache is King / cachebpf**：用 eBPF 表达**页缓存淘汰**策略，按负载定制而非内核一刀切的 LRU（[Cache is King, arXiv 2502.02750](https://arxiv.org/abs/2502.02750)）；后续还有 **LearnedCache**——用感知机（perceptron）做页缓存淘汰判决（[LearnedCache, arXiv 2605.26168](https://arxiv.org/html/2605.26168v1)）。
- **BPF OOM（`struct_ops` 实现自定义 OOM killer）**：Roman Gushchin（Meta）的系列，给 BPF 程序两个钩子接管 **OOM 处理**——可挂**一个系统级 + 每个 memcg 一个** `bpf_oom_ops`；memcg OOM 时自底向上遍历 cgroup 树依次调用，`bpf_handle_out_of_memory()` 返回是否已释放内存，否则回退内核默认 OOM killer。它甚至可以**不杀进程**，改为删 tmpfs 文件等方式腾内存（[mm: BPF OOM, LWN](https://lwn.net/Articles/1034293/)、[Custom OOM killers in BPF, LWN](https://lwn.net/Articles/1019230/)、[Gushchin patch v2, LKML](https://lkml.org/lkml/2025/10/27/1969)）。
- **reclaim_ext（统一可扩展回收）**：2026 年 LSF/MM/BPF 上的议题「Towards Unified and Extensible Memory Reclaim」，试图把上面这些零散提案收敛成一套统一框架（[reclaim_ext topic, LKML](https://lkml.iu.edu/hypermail/linux/kernel/2603.3/04703.html)）。
- **DAMON/DAMOS + BPF**：[A15b](A15b-DAMON与分层内存实践.md) 的 DAMON 已是"用户态可控的回收策略工具箱"，与 BPF 结合可进一步把判决逻辑下放。

> **术语警示**：上面是 **Linux 上游的研究/RFC**；**不要把 eBPF-mm 的 `PROTECT/EVICT/PASS`、BPF-OOM 的 `bpf_oom_ops` 当成 Android 已有接口**——Android 现在并不跑这些。它们说明的是"可编程回收"的形态与上游进度，不是终端现状。

### 3.4 两级冷热：语义 VRegion 粗排 → 页面级精排（让 eBPF 别在每页上算）

§3.3 的可编程判决若**逐页**回调，本身就贵——mm 热路径上每页跑一段程序，开销可能吃掉收益。一个更可落地的结构是**两级冷热**：

> **先用应用/框架的语义，在【进程 / 虚拟地址区域（VRegion）】这一**粗**粒度上判大块冷热、决定"先扫谁、先回收谁、保护谁"；再让内核页面级 LRU 在被选中的区域内做**细**排。** 粗排把页面级扫描/判决**剪枝**到少数候选区域，精排保证区域内不冤枉热页——**语义粗排正是让页面级可编程判决*可负担*的前提**。

关键在于：**这两级里，"粗"的那一半在终端已是现实，只是没和 LRU 焊成一套**——

- **进程/区域级语义回收已落地（syscall，非 eBPF）**：Android 用 `process_madvise(MADV_COLD / MADV_PAGEOUT)`，由平台（system_server / LMK 路径）**按语义**对"刚切后台的 app"**整片地址区域**提示冷 / 直接回收；其**明确动机就是"绕开内核 LRU 对'用户态已知为冷'的页判断不准"**，实测较 lmkd 撞顶**少杀 15–30%**（[MADV_COLD/PAGEOUT, LWN 790123](https://lwn.net/Articles/790123/)、[process_madvise(2)](https://man7.org/linux/man-pages/man2/process_madvise.2.html)、[Android application compaction, LPC](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf)）。但它是**一次性、命令式、用户态择时**的"poke"，不参与内核**持续**的回收判决。
- **粗→细的两级监控已存在（DAMON）**：DAMON 的 **region-based sampling + adaptive regions**——热区自适应**裂**得更细、冷区**并**成大块——正是"大块粗排、热处精排"（[DAMON 设计](https://docs.kernel.org/mm/damon/design.html)、[A15b](A15b-DAMON与分层内存实践.md)）。但 DAMON 的区域按**访问频率**裂并，**不带应用语义**。

> **本方向的真正增量（设想）**：用 **eBPF 把"应用/框架语义标注的 VRegion"做成对回收/扫描策略的*持续、声明式*输入**——让语义粗排 **riding along** 内核回收路径（而非用户态周期性 poke），并据此**给 [A16a](A16a-LRU主动扫描.md) 的主动扫描定向**（只走候选 VRegion，不扫全地址空间）。这把 `process_madvise` 的"命令式一次性"与 DAMON 的"频率裂并"**合**成一套：**语义定先验、页面级 recency/refault 定真值纠偏**。这一步公开未见，是本篇该收的方向。

两条必须诚实的**硬约束**（否则"无缝集成"是过度断言）：

- **语义→VMA→页 的映射不免费**：app 的"模块/框架"语义活在对象/分配器空间，内核回收活在物理页/VMA。一个"模块"很少恰好是一段连续 VMA——除非分配器配合（arena-per-module、区间打标）。没有分配纪律，语义区域就**碎**在页间，粗排失真。Android 上天然的语义 region 锚点是 **ART 的 region 化托管堆**（GC 已知各 region 存活性），但把托管堆 region 对接到内核页回收本身是未解问题（**待核实 / 设想**）。
- **粗标只能是先验，不能压过真值**：app 说"这块冷"，但一个回调刚摸过它——必须由页面级 recency/refault **纠偏**，否则就是 MGLRU 当年要消灭的 refault 颠簸。这也是 `MADV_COLD` 取"去激活、压力来了再收"而非"立即收"的道理：**给提示，但把真相留给内核**。

> **术语锚定**：本篇的 **VRegion ≈ 进程内的虚拟地址区域（Linux 的 VMA / DAMON region / `process_madvise` 区间）**，带应用/框架语义标签。若它系某平台私有专名（如鸿蒙侧用法），其确切定义**待核实**——本篇据 Linux 等价物立论，避免跨平台术语混用。

## 4. 历史：冷热的"判决权"如何从内核走向可编程

```
硬编码 LRU 启发式（active/inactive 晋升降级，规则写死内核）
   ▼ MGLRU（Linux 6.1, 2022）：代际老化更准——Google/Yu Zhao 主导，
      动因正是 Android/ChromeOS 的可执行页颠簸；随 ACK/GKI 下发到 Android。
      但它是"更好的固定策略"，仍不可编程。
   ▼ DAMON/DAMOS（监控可编程、用户态可控回收策略）—— A05/A15b
      "感知"先可编程化
   ▼ sched_ext（Linux 6.12, 2024）：用 BPF struct_ops 把【CPU 调度】策略
      整建制搬进主线——证明"核心内核策略可经 struct_ops 可编程化"路径可行
   ▼ eBPF-mm / cachebpf / BPF-OOM / reclaim_ext（研究/RFC，2024–26）
      "回收/淘汰/OOM 判决"开始可编程化——但【无一进 mm 主线】
   ？ Android 落地：受"开机+签名+门控"加载模型约束，
      若落地只会是 OEM/Google 侧的杠杆（推测，非现状）
```

主线：**冷热治理的"判决权"在逐步从内核硬编码，下放到可被外部策略编程的钩子**。DAMON 解放了"感知"，sched_ext 证明了"核心策略可经 BPF struct_ops 进主线"，eBPF-for-mm 正试图把同样的事做到"回收/淘汰/OOM 判决"——**但 mm 子系统比调度更保守，至今未落地**。

## 5. 现状与平台差异

| 维度 | Android（Linux / GKI） | HarmonyOS | iOS / Darwin |
|---|---|---|---|
| 冷热回收的**固定策略** | **MGLRU（Google 主导，随 ACK/GKI 下发，已落地）** + lmkd/PSI 驱动回收/杀进程 | LiteOS-A active/inactive 双链（[A14](../platforms/A14-HarmonyOS-内存实现.md)）；NEXT 内核 policy-free paging（OSDI'24） | XNU 自有 pageout/compressor 策略 |
| 回收策略**可编程**？ | **否**（上游 eBPF-mm/BPF-OOM/reclaim_ext 均研究/RFC，未进主线，Android 未启用） | 据口径"策略可下放"，载体公开资料稀薄（另走 XVM 路线，本系列不展开） | 不可编程 |
| eBPF **是否生产级** | **是，但用于网络/tracing/GPU 内存**，非回收；开机加载、签名、AID 门控、App 不能动态加载 | — | 无 eBPF |
| 整机 vs 单 app | per-memcg 作用域（[A07](../foundations/A07-cgroup-memcg.md)）；整机文件页全局 LRU；MGLRU 有 per-memcg LRU 演进 | 整机文件页全局 LRU | 系统统管 |

> **平台诚实点**：Android 在"冷热回收"上**已落地的进步是 MGLRU（更好的固定策略），不是可编程回收**。可编程回收在三个平台**都还不是现状**：Android 在等上游 + 受加载模型约束，鸿蒙路线（XVM）公开资料稀薄、本系列不展开，iOS 根本不开放。

## 6. 趋势与未解问题 ← 本篇重心

- **mm 比调度更保守，可编程为何卡住**：`sched_ext` 已进主线，但 mm maintainer 对"把回收判决开给 BPF"明显更谨慎。核心顾虑是 **ABI 稳定性**——这些钩子"是不是一个永久的 mm 特性？五年后内存管理长什么样没人知道"（David Hildenbrand 语，[LWN 1072538](https://lwn.net/Articles/1072538/)）。甚至有"`sched_ext` 本身是个错误、生产调度器仍 out-of-tree"的反方声音（Alexei Starovoitov）。**2026 LSF/MM 上 Gushchin 直言：BPF-mm 提案至今无一进主线**——这是本篇最重要的现状锚点。
- **可编程的"安全边界"**：mm 是性能与稳定的核心路径，让外部程序参与回收判决，要受 eBPF **校验器**严格约束（不能死循环、不能越权访存、执行时间有界）。"既要足够表达力写出有用策略，又不危及内核稳定"如何平衡，是 eBPF-for-mm 的核心难题。
- **Android 特有的"谁来下发"问题**：即便上游落地，Android 的**开机+签名+AID 门控**加载模型意味着可编程回收只能是 **OEM/Google 侧的配置杠杆**，不向第三方/App 开放（§3.2）。这反而可能是它在终端**更容易被接受**的形态——厂商在 GKI 之上下发机型差异化回收策略，不破坏统一内核基线。
- **多段策略如何不打架**：厂商、系统、甚至 app 都可能想影响策略——**整机全局最优 vs 各自局部最优**的冲突如何仲裁？多段 BPF 程序并存时的优先级与公平性（呼应 [A16d](A16d-压缩IP边际建模.md) 的预算分配）尚无框架；BPF-OOM 的"system + per-memcg 自底向上遍历"是一个早期答案。
- **与主动扫描/边际建模的协同**：理想闭环是 [A16a](A16a-LRU主动扫描.md) 主动扫描供冷热信号 → BPF 策略据整机视角判决 → [A16d](A16d-压缩IP边际建模.md) 在预算内决定压多狠。三者怎么拼成一套**可下发、可观测、可回滚**的系统，是终端冷热治理的开放工程。
- **两级冷热（§3.4）是最务实的一段，但卡在"语义→页"的映射**：「语义 VRegion 粗排 + 页面级精排」之所以最近可信，是因为它两半都已存在（`process_madvise` 语义回收已落地、DAMON 粗细两级已在上游）；难点不在内核钩子，而在**让 app/框架稳定地把模块语义映射到地址区域**（需分配器纪律），以及多方语义标注并存时的**冲突仲裁**（谁的"冷"说了算）。这也是 eBPF 把"命令式 poke"升级成"持续策略"后第一个要回答的问题。
- **鸿蒙的 XVM 路线**：据用户口径，HarmonyOS 另有名为 XVM 的 eBPF 内存管理框架（主打整机文件页 LRU），**但公开技术细节稀薄，本系列不展开**；其与 OSDI'24 "policy-free kernel paging" 的关系待一手核实（[A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md) 当前无 XVM 内容）。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| 冷热信号 ← 主动扫描 | 可编程策略在主动扫描拿到的访问之上"编排判决" | **[A16a](A16a-LRU主动扫描.md)** |
| 粗排 ← 进程/VRegion 语义 | 语义先判大块冷热、给扫描/回收定向，页面级 LRU 再精排（§3.4） | **[A16a](A16a-LRU主动扫描.md)**、`process_madvise`/DAMON |
| 可编程监控 ← DAMON | "感知可编程"的前一步，本篇推进到"策略可编程" | **[A05](../foundations/A05-冷热识别的演进.md)、[A15b](A15b-DAMON与分层内存实践.md)** |
| 作用域 ← memcg | 策略需在 per-app / 整机两个尺度协调；BPF-OOM 即按 memcg 树组织 | [A07](../foundations/A07-cgroup-memcg.md) |
| 固定策略基线 ← MGLRU | Android 已落地的"更好固定策略"，可编程是它之上的下一步 | [A05](../foundations/A05-冷热识别的演进.md) |
| 平台落点 → HarmonyOS | 鸿蒙另走 XVM 路线（资料稀薄，本系列不展开） | [A14-HarmonyOS](../platforms/A14-HarmonyOS-内存实现.md) |
| 判决后果 → 压缩/边际 | 判"回收"后压多狠由边际模型定 | [A16c](A16c-异构压缩CDSD.md)、[A16d](A16d-压缩IP边际建模.md) |

## 8. 实测 / 观测点

- Android eBPF 现状：`ls /sys/fs/bpf/`（看 `bpfloader` 开机 pin 的程序/map，多为网络/tracing 类）、`/system/etc/bpf/` 下的 `.o`；
- MGLRU（Android 已启用）：`/sys/kernel/mm/lru_gen/enabled`、`/sys/kernel/mm/lru_gen/min_ttl_ms`、debugfs `lru_gen`（见 [A16a](A16a-LRU主动扫描.md)）；
- 进程/区域级语义回收（已落地，非 eBPF，§3.4）：`process_madvise(MADV_COLD/MADV_PAGEOUT)`；按进程/区间观察用 `/proc/<pid>/smaps_rollup`，部分内核/厂商有 `/proc/<pid>/reclaim` 节点；
- Linux 通用 eBPF：`bpftool prog` / `bpftool struct_ops` 看已挂载的 BPF 程序与 struct_ops；`sched_ext` 用 `bpftool struct_ops list` 可见已加载调度器；
- DAMON：`/sys/kernel/mm/damon/`（可编程监控 + 用户态可控回收，[A15b](A15b-DAMON与分层内存实践.md)）；
- 整机文件页 LRU 现状：`/proc/meminfo` 的 `Active(file)`/`Inactive(file)`、`/proc/vmstat` 的 `pgscan_file`/`pgsteal_file`；
- **可编程回收专属观测口径：暂无**——上游 eBPF-mm/BPF-OOM 未进主线，Android 未启用。

## 9. 来源与延伸阅读

**Android 的 eBPF 加载模型与官方用途（已实践）**
- [Extend the kernel with eBPF (AOSP)](https://source.android.com/docs/core/architecture/kernel/bpf) —— `bpfloader` 开机加载、`/system/etc/bpf`、pin 到 `/sys/fs/bpf`、AID 门控、BTF
- [eBPF traffic monitoring (AOSP)](https://source.android.com/docs/core/data/ebpf-traffic-monitor) —— Android eBPF 的网络流量统计用途
- [eBPF on Android 教程 (eunomia)](https://eunomia.dev/tutorials/22-android/) —— Android eBPF 加载实操与"无良好动态加载"现状

**Android 的内存回收基线（已实践，非 eBPF）**
- [Multi-Gen LRU Framework (LWN 900288)](https://lwn.net/Articles/900288/) —— MGLRU 框架；动因为 Android/ChromeOS 可执行页颠簸（Google/Yu Zhao）
- [Android Low Memory Killer Daemon (lmkd, AOSP)](https://android.googlesource.com/platform/system/memory/lmkd/+/master/README.md) —— PSI + vmstat 驱动的用户态回收/杀进程
- [Introduce MADV_COLD and MADV_PAGEOUT (LWN 790123)](https://lwn.net/Articles/790123/)、[process_madvise(2) man page](https://man7.org/linux/man-pages/man2/process_madvise.2.html) —— 用户态按语义对指定进程/区域提示冷 / 回收（§3.4 两级粗排的"已落地半")
- [Handling memory pressure on Android application compaction (LPC)](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf) —— Android 用 `process_madvise` 做后台 app 整片回收，少杀 15–30%
- [Memory Management on Mobile Devices (Sareen et al., ISMM 2024)](https://www.steveblackburn.org/pubs/papers/android-ismm-2024.pdf) —— Android 内存管理的学术刻画（非 eBPF）
- [App-aware Swap Resource Allocation (ACM TECS 2025)](https://dl.acm.org/doi/10.1145/3760385) —— 面向 app 切换延迟的换页资源分配

**eBPF / struct_ops 把核心策略可编程化（机制底座 + 已进主线的先例）**
- [eBPF struct_ops 教程 (eunomia)](https://eunomia.dev/tutorials/features/struct_ops/) —— `struct_ops` 把自定义逻辑插进内核子系统
- [Sched_ext Merged For Linux 6.12 (Phoronix)](https://www.phoronix.com/news/Linux-6.12-Lands-sched-ext)、[Extensible Scheduler Class (kernel.org)](https://docs.kernel.org/scheduler/sched-ext.html) —— BPF 把【CPU 调度】策略搬进主线的已落地先例

**用 eBPF 编程内存回收 / 淘汰 / OOM（学界与上游研究，未进主线）**
- [Controlling memory management with BPF (LWN 1072538)](https://lwn.net/Articles/1072538/) —— 全景综述：OOM/NUMA/memcg/页缓存提案、ABI 稳定性顾虑、"无一进主线"
- [eBPF-mm: Userspace-guided memory management in Linux with eBPF (arXiv 2409.11220)](https://arxiv.org/pdf/2409.11220) —— 回收路径 BPF 判决 `PROTECT/EVICT/PASS`
- [Cache is King: Smart Page Eviction with eBPF (arXiv 2502.02750)](https://arxiv.org/abs/2502.02750)、[LearnedCache (arXiv 2605.26168)](https://arxiv.org/html/2605.26168v1) —— 可编程页缓存淘汰
- [mm: BPF OOM (LWN 1034293)](https://lwn.net/Articles/1034293/)、[Custom out-of-memory killers in BPF (LWN 1019230)](https://lwn.net/Articles/1019230/) —— Gushchin 的 BPF OOM `struct_ops`
- [Towards Unified and Extensible Memory Reclaim — reclaim_ext (LKML, LSF/MM 2026)](https://lkml.iu.edu/hypermail/linux/kernel/2603.3/04703.html)
- [The 2024 LSFMM+BPF Summit (LWN)](https://lwn.net/Articles/lsfmmbpf2024/) —— 可编程 mm 的上游讨论
- DAMON 可编程监控/回收：见 [A05](../foundations/A05-冷热识别的演进.md)、[A15b](A15b-DAMON与分层内存实践.md)

**承接 / 相邻篇**
- [A16a LRU 主动扫描](A16a-LRU主动扫描.md)、[A05 冷热识别的演进](../foundations/A05-冷热识别的演进.md)、[A15b DAMON 与分层内存实践](A15b-DAMON与分层内存实践.md)、[A16d 压缩 IP 边际建模](A16d-压缩IP边际建模.md)、[A07 cgroup/memcg](../foundations/A07-cgroup-memcg.md)、[A14 HarmonyOS 内存实现](../platforms/A14-HarmonyOS-内存实现.md)

> **待核实 / 待补**：Android `/vendor/etc/bpf` 等 vendor 加载路径与 GKI 下 vendor eBPF 的边界（AOSP 文档主述 `/system/etc/bpf`）；是否有 OEM（OPPO/小米/三星等）在量产机用 eBPF 介入内存回收的公开证据（本篇未找到，倾向"无"）；上游 eBPF-mm/BPF-OOM/reclaim_ext 是否/何时进主线（现为研究/RFC）；MGLRU 在各 Android 版本/机型的默认启用情况与 per-memcg LRU 演进的下发节奏；**"VRegion" 的确切定义与跨平台术语归属**（本篇锚到 Linux 的 VMA / DAMON region / `process_madvise` 区间）；把 app/框架"模块语义"稳定映射到地址区域（VMA）所需的**分配器配合**（arena / 区间打标）；**ART region 化托管堆与内核页回收的对接**（设想，未见公开实现）；是否有用 eBPF（而非 `process_madvise` 命令式）把语义 VRegion 做成**持续**回收策略的工作（本篇未找到）；鸿蒙 XVM 的确切定义与挂载点（公开资料稀薄，本系列不展开）。

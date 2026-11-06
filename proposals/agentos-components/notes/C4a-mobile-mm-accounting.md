# C4a 移动端传统内存与统一记账（AgentOS 组件调研）

> 子模块：C4a。负责内存 Q1、Q5、Q6、Q8，主责接缝 J2，立场评审 MM-1、MM-2、MM-3。
> 检索日期：2026-11-05。证据等级 A–D、成熟度 L1–L4 的含义见 research-prompt.md 第 3.2、3.3 节。
> 说明：本次联网检索额度在中途耗尽，iOS、HarmonyOS、Apple/MediaTek NPU、侧信道、mTHP 版本节点等方向只完成了部分核实，未核实处一律标「待核实」或「未找到公开资料」，不以背景记忆代替证据。
> 本库已有结论（MGLRU、PSI、LMKD、zram、memcg、IOMMU/SVA 的基础机制）不重复，只写 2025H2–2026 的新进展与对立场的评审。

---

## §0 摘要

1. **Android 17 已把「按进程 memcg 限额」做成平台默认机制**：Memory Limiter 用 cgroup v2 的 `memory.high` 与 `memory.swap.max` 对 UID≥10000 的应用进程限额，按「可见/不可见」两档、按整机 RAM 分档（4GB/6GB/8GB/12GB/16GB 有固定表），超限先被节流回收并压入 zRAM，极端情况才杀（R1、R2，A/B，L4 起步，首发 Pixel）。这直接回答了「Android 是否按应用建 memcg」：是，且用的是天花板（high/swap.max），不是 `memory.min/low` 保护契约。
2. **Android 的限额口径是「匿名 RSS + swap」**（ApplicationExitInfo 描述串为 `MemoryLimiter:AnonSwap`），官方文档未说 dma-buf 或 GPU 内存是否计入（R1、R2）。因此记账缺口表中 dma-buf、GPU、NPU 三行在 Android 17 上仍是限额盲区（判断）。
3. **dma-buf 记账上游路线在 2026 年出现分叉而非收敛**：sysfs 统计 2026-01 提出删除（Android 已迁到 BPF iterator）（R3）；memcg 路线是 2026-05 的 RFC（`MEMCG_DMABUF` + 分配时 `charge_pid_fd` + SELinux 跨 cgroup 计费授权）（R4）；dmem 路线已把设备内存区域纳入 cgroup（6.14 前后合入，R5），并有 2026-02 的 CMA 堆接入（R6）和 2026-05 的「dmem 双计费到 memcg」补丁（R7）。均无 Android 需求声明，均未见合入确认。
4. **MGLRU 在 Android 上仍是「有人大规模用、上游在争论去留」的状态**：荣耀称在约 7000 万台设备上使用 MGLRU，并靠 hook 与 memcg 强制回收绕开热冷应用语义缺口；LSFMM+BPF 2026 三场会议围绕 MGLRU，达成的是「拆文件、定评测负载、找共性」的四步计划，没有对 Android 诉求做出决定（R8、R9，C）。结论：我方方案不应绑定 MGLRU 页龄，应绑定 memcg 粒度的应用/会话语义。
5. **「用户注意力」信号在工业界停留在「可见/前台」**：Android 17 限额按可见性分档；荣耀 hook 让回收跳过前台应用；ChromeOS VMMMS 用 LMKD 与标签丢弃的优先级仲裁（R2、R8、R10）。亮屏、「用户正在等 Agent 结果」这类前台以外的信号：未找到公开的系统实现，属于差异化空白（判断）。
6. **移动端对「系统级模型服务内存」的归属，公开资料几乎空白**：AICore 的进程内存归属、Apple Foundation Models 守护进程的内存记账均未找到官方说明；学术侧 mzCache（MobiCom 2026）明确指出 OS 的低内存杀手倾向先杀大 LLM 进程（R11，C）。J2 的归属问题在三平台上都没有现成答案。
7. **NPU 内存抽象仍是「厂商私有 + 通用 dma-buf 底座」**：Linux accel 子系统在 2026 年继续增加驱动（NXP Neutron，用户态仍闭源）与记账能力（amdxdna 的单 BO 内存查询）；Qualcomm 走 FastRPC 内存映射 ioctl；MediaTek 未找到官方 dma-buf 导入文档（R12、R13）。跨厂商标准化仍无收敛迹象。
8. **NPU 共享内存隔离的学术工作少且偏体系结构**：sNPU（ISCA 2024）扩展 TEE 到 NPU；TZ-LLM（arXiv 2025-11）给出 Rockchip NPU 世界切换约 32ms 的实测（R14、R15）。针对手机 NPU 共享内存的侧信道专项论文：未找到。
9. **16KB 页进入强制期**：Play 要求针对 Android 15+ 的 64 位应用更新必须支持 16KB 页，截止 2027-02-01；Google 自测应用冷启动压力下平均 -3.16%、功耗 -4.56%，同时「平均略多占内存」，且对自带分配器的应用有 RSS 与 zRAM 压缩率副作用（R16，B）。
10. **总体判断**：MM-1 需修订（dma-buf 与 NPU 的计费上游未落地，需自带「归属语义」）；MM-2 得到上游分叉的间接支持；MM-3 方向被验证但「注意力」比工业界现状更细，需要把差异点钉在前台以外的新信号上。

---

## §1 技术谱系表

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 进程级 memcg 限额 | Android 17 Memory Limiter（`memory.high`+`memory.swap.max`） | Google | 2026（Android 17） | 按可见性与整机 RAM 分档限额，节流优先于杀进程 | L4（Pixel 起步，OEM 一年内跟进，R1） | 原生移动端 |
| 用户态低内存杀手 | LMKD（PSI 触发，Android 11 起） | Google | 2020–至今 | PSI 阈值+thrashing+swap 利用率三类信号决策杀进程（R17） | L4 | 原生 |
| 内核 PSI 回收闭环 | TMO/Senpai | Meta | ASPLOS 2022 | PSI 驱动用户态代理经 cgroup 接口持续下推冷页，省 20%–32% 内存（R18） | L4（Meta 机群） | 需改造：服务器负载、SSD/zswap 与手机 UFS 寿命约束不同 |
| 主动回收接口 | `memory.reclaim`（含 `swappiness=` 参数） | Linux 社区（Meta 等） | 内核 6.x 系列 | 用户态按 cgroup 写入回收量，参数可覆盖 swappiness（R19） | L4 | 可直接迁移（Honor 已在 Android 上用 memcg 强制回收，R8） |
| 桌面前台保护 | Fedora uresourced + systemd-oomd | Fedora/systemd | 2020–2023 起 | 为活跃图形会话设最小内存保护（文档提到 250MiB 量级，R20）；oomd 按 PSI 与 `memory.low` 语义选杀 | L3 | 需改造：保护量需随应用而非随会话 |
| 虚拟机气球 | ChromeOS ARCVM balloon + VMMMS | Google | 2024-07 博文 | 低压用 MGLRU 页缓存年龄求公平，高压用 LMKD 与标签丢弃优先级仲裁（R10） | L4（ChromeOS） | 需改造：手机无宿主-客户机双层 |
| 前台感知回收（学术） | Acclaim（ATC 2020）、PMR（ATC 2025） | CityU 等 | 2020、2025 | 前台感知驱逐把页让给前台；并行化页收缩与回写，响应时间最多 -43.6%（R21、R22） | L1–L2 | 原生移动端研究 |
| 设备内存 cgroup | dmem 控制器（`dmem.min/low/max/current/capacity`） | Linux/DRM 社区 | 6.14 周期（R5） | 按设备内存区域做配额，语义同 memcg | L3 | 需改造：UMA 手机无独立显存区域（见 Q1） |
| dma-buf 计费（memcg） | `MEMCG_DMABUF`+`charge_pid_fd` RFC | Red Hat/Google 先前工作 | 2026-05 | 分配时计到客户端 cgroup，经 LSM 钩子授权跨 cgroup 计费 | L1（RFC） | 直接面向 Android binder 场景 |
| dma-buf 统计导出 | dmabuf BPF iterator（取代 sysfs 统计） | Google | 2026-01 sysfs 删除提议 | 低开销枚举 dma-buf 及持有者 | L4（Android 已迁，R3） | 原生 |
| GPU 内存观测 | `gpu_mem_total` tracepoint+gpuservice BPF | Google | 2020 引入 | 厂商驱动上报全局与 per-pid GPU 总量 | L4 | 原生，但依赖厂商驱动上报 |
| NPU 内核栈 | Linux accel（amdxdna、ivpu、Neutron 等） | 社区/AMD/Intel/NXP | 2026 持续 | 通用 GEM+dma-buf 之上的 NPU 驱动框架 | L3（PC/嵌入式），手机 NPU 基本不走此路径 | 需改造：手机 NPU 驱动多为闭源 |
| 手机 NPU 内存 | Qualcomm FastRPC 内存映射 ioctl、MediaTek Neuron | 高通、联发科 | 持续 | dma-buf fd 映射到 DSP/APU 的 SMMU 上下文 | L4 | 厂商私有 |
| NPU TEE | sNPU（ISCA 2024）、TZ-LLM（2025-11） | 上交 IPADS 等 | 2024、2025 | NPU 访问控制+scratchpad/NoC 隔离；TrustZone 下 NPU 分时 | L1 | 需硬件改造 |

---

## §2 关键数据

| 指标 | 数值 | 条件（硬件 / 模型 / 负载） | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| Android 17 限额：16GB 整机 | 可见 10240MiB / 不可见 5120MiB / swap 5120MiB | 标准档；MemTotal≥18432MiB 或 <3200MiB 不设限 | R2 | 2026（Android 17 文档） | A（官方文档） |
| Android 17 限额：12GB / 8GB / 6GB / 4GB | 8192/4096/4096；5120/3072/3072；4096/2048/2048；2048/1024/1024（可见/不可见/swap，MiB） | 同上 | R2 | 2026 | A |
| Android 17 限额口径 | 匿名 RSS + swap（`MemoryLimiter:AnonSwap`） | 超限先压入 zRAM，再继续增长才终止 | R1 | 2026-08 | B |
| Android 17 保护范围 | 缓存进程先冻结再最大化回收；PERSISTENT 进程不设限 | UID≥10000 | R2 | 2026 | A |
| MGLRU 在荣耀的规模 | 约 7000 万台 | 荣耀 Zicheng Wang LSFMM 议题报道 | R9 | 2026（LSFMM+BPF） | C |
| 荣耀回收时间预算 | 8.3ms（120fps 一帧） | 回收需在此预算内避免渲染卡顿 | R9 | 2026 | C |
| TMO 内存节省 | 机群总内存 20%–32%，其中应用容器 7%–19% | Meta 机群，2021 起生产 | R18 | 2022 | A（同行评议） |
| PMR 响应时间改善 | 最多 -43.6% | 真实手机；机型与版本页面未写明 | R22 | 2025 | A（同行评议），条件不全 |
| mzCache TTFT | -2.1 至 -5.5 倍（相对存储支撑的部分卸载） | llama.cpp、Android 应用、统一内存 SoC | R11 | 2026-09（arXiv，MobiCom 2026 录用） | C（预印本，注明录用） |
| 16KB 页：冷压力下应用启动 | 平均 -3.16%，部分应用最高 -30% | Google 初步测试 | R16 | 2025–2026 | B |
| 16KB 页：启动功耗 / 相机冷启动 / 开机 | -4.56% / -6.60% / -8%（约 950ms） | 同上 | R16 | 同上 | B |
| TZ-LLM：NPU 世界切换 | 32ms（Rockchip NPU） | TrustZone，REE/TEE 分时使用 NPU | R15 | 2025-11 | C |
| ChromeOS ARC 气球策略成效 | 标签丢弃 -50%，且不触发 ARC 应用被杀 | ChromeOS，Google 口径 | R10 | 2024-07 | B |
| dma-buf RFC 规模 | 5 个补丁，18 个文件，633 增 / 10 删 | Albert Esteve RFC | R4 | 2026-05-12 | A（邮件列表） |
| 16KB 页 Play 截止 | 2027-02-01 | 目标 Android 15+ 的 64 位应用 | R16 | 2026 | B；另有页面提到过 2025-11-01 与 2026-05-31 延期，待核实以 Play 当前政策为准 |

---

## §3 逐问题分析

### Q1 移动端内存管理现状

#### 1.1 Android：从「杀」转向「限+压」

**现状。** LMKD 仍是用户态低内存终止的主体：Android 11 起 PSI 触发（`psi_partial_stall_ms` 默认 70ms，`complete_stall_ms` 700ms，另有 thrashing 与 swap 利用率阈值），文档同时说明 LMKD 依赖 memcg 按重要性给进程设限（R17，A）。2026 年的新事实是 Android 17 的 Memory Limiter 成为这一思路的正式落地：限额由 system_server 内的服务与 Activity Manager 联动，按进程可见性切换 `memory.high`，同时用 `memory.swap.max` 封顶 zRAM 占用；缓存进程冻结后被最大化回收（R2，A）。

**机制要点。**
- 超限的第一反应是节流与回收（内核换出匿名页、逐出干净文件页），不是杀；只有 swap 耗尽且继续增长、出现分配失败才终止（R2）。Google 博客的表述一致：先压入 zRAM，有压缩开销、可能掉帧，再超才杀（R1）。
- OEM 通过 XML 配置（`memory-limiter-config.xml`，按 MemTotal 区间选档）介入；文档称应用与系统服务可声明更紧的预算，但不得超平台限额；开发者运行时无 API 查询当前限额（R2）。
- 两处文档不一致需注意：AOSP 页面正文写配置在 `/system/etc/`，同页的另一个版本写 `/vendor/etc/`，以实机为准，待核实。
- 与第三方博客「静默杀死」的说法相比，官方口径是节流优先（R2 vs 第三方转述，D），采用官方口径。

**对我方的含义。** 这是 MM-1「会话级 memcg」最强的产业先例：**平台已愿意把 memcg 的 `high` 与 `swap.max` 当作每进程配额接口，且已有 AMS 生命周期联动与冻结联动**。但它的粒度是进程而非「会话」，口径是 anon+swap，不含 dma-buf/GPU。

**MGLRU。** 仍可见的事实是上游争论而非默认化：2026 年 LSFMM+BPF 有三场会议围绕 MGLRU（LWN 报道标题为「What is to be done about MGLRU?」），讨论四步统一计划，并没有对 Android 提出的诉求（生成数语义、热冷应用语义、回收上限 hook）形成决定（R8、R9，C）。同一时期 Wilcox 提议整体移除，被报道为「几乎没有支持」（R8，C）。Android 内核团队有专职工程师投入 MGLRU（来自邮件列表转述，待核实原文）。另有 MGLRU 回收循环系列 v7（2026-04）报告了 Android 上的收益（R23，A 为补丁系列，具体数字待核实）。MGLRU 与传统 LRU 的度量差异使 LMKD 的 refault/thrashing 判据在两种实现下不一致（R8，C）。Android 哪个 GKI 版本默认开启 MGLRU：本次未能核实，参考本库 A14 文档，待核实。

**mTHP / 16KB / freezer。**
- 16KB 页：自 Android 15 起 AOSP 支持；Play 要求 2027-02-01 起不支持 16KB 页的更新不可发布；Google 自述 16KB 设备「平均略多占内存」；Android 17 增加了让不兼容二进制立即 abort 的开关（R16，B）。文档还警告自带分配器在 16KB 下会放大 RSS、恶化 zRAM 压缩（R16）。对 Agent 场景：推理运行时、自带 mmap 权重布局、KV arena 的对齐假设都需要复查。
- mTHP/大 folio 换入对 zRAM 同步设备的支持已有补丁进入主线，具体版本未能核实（本库 M2 已有指向，待核实）。
- cached apps freezer：Android 17 文档确认缓存进程「冻结后最大化回收」（R2）；freezer 自身版本节点本次未核实。

**分歧。** 一类观点认为 Android 的天花板式限额（high+swap.max）已经足够；荣耀、LSFMM 议题则表明厂商仍需要「跳过前台」「活跃老化」「停止点 hook」等页级语义（R9）。**这说明什么：** 平台层限额已解决「漏洞型离群应用」，但没有解决「谁值得被保护」，保护语义仍缺位。

#### 1.2 iOS：Jetsam（memorystatus）

事实基础见本库 A14-iOS（xnu `memorystatus_kills.md`、`memorystatus_notify.md`，R24，A）：决策在内核内，按优先级带与 per-process limit 杀。2026 年新增证据只有开发者论坛的实测，证据等级 D–C：
- iPhone 17 Pro（12GB）在 iOS 26.3–26.4.1 上 WebContent 进程在 2048MB 的 ActiveHard 限额被 jetsam，且 `increased-memory-limit` 不适用于 WebKit WebContent（R25，D，开发者自述）。
- 另一位开发者测得 12GB iPhone 上单进程上限约 6144MB，叠加 `extended-virtual-addressing` 无变化，叠加调试用 entitlement 约 6656MB；8GB 机型也出现约 6GB 上限（R25，D）。
- Apple 官方文档说明 `increased-memory-limit` 仅部分机型可用，并建议用 `os_proc_available_memory` 查询（R26，A）。

**判断：** iOS 的模型是「每进程静态上限+优先级带」，与 Android 17 的「按整机 RAM 与可见性分档」同构。官方未公开 iOS 26 对 Jetsam 的变更说明，不能断言 iOS 26 有机制演进。footprint 记账口径（是否含压缩内存、IOSurface/Metal 缓冲）：未能核实，标待核实。

#### 1.3 HarmonyOS（鸿蒙内核 / OpenHarmony 与 HarmonyOS NEXT 区分）

已核实的只有应用侧与 NDK 侧接口：
- `onMemoryLevel` 三档回调（MODERATE/LOW/CRITICAL），后台已冻结的应用收不到回调（R27，C，开发者整理）。
- Purgeable Memory：内核文档称系统压力下优先回收，至少 4KiB 大块、重建成本低的数据适用，C API 自 API 10 起提供（R28，A 官方）。
- OpenHarmony 标准系统的 ESwap（zswapd 把 zram 压缩页加密后换出到专用分区）出自本库 M2 引用的 OpenHarmony 文档，本次未重新核实（待核实）。
- HarmonyOS NEXT 微内核下的页回收、换出、应用级 cgroup 类机制：未找到公开资料。

**这说明什么：** 鸿蒙的公开面是「应用自愿释放（回调+可丢弃内存）」，不是平台强制限额；与 Android 17 的强制限额路线相反，可作为 AgentOS 在鸿蒙上「合作式」与 Android 上「强制式」双形态的依据（判断）。

#### 1.4 dma-buf 与 GPU 记账的上游状态

| 方向 | 状态 | 要点 | 证据 |
|---|---|---|---|
| sysfs 统计（`CONFIG_DMABUF_SYSFS_STATS`） | 2022 弃用，2026-01 提出删除 | 性能问题；Android 可能是最后用户，已迁 BPF iterator；König 给 Reviewed-by，Semwal 称将推送。合入版本与是否已进主线：待核实 | R3，A |
| BPF iterator | Android 已用 | 以更低成本枚举 dma-buf；补丁系列含 selftests | R3，A（间接） |
| memcg 计费（Mercier 2023 → Esteve 2026 RFC） | RFC，未合入 | 2023 版在 export 时计到分配者 cgroup，并配 binder 转移所有权；2026 版移到 `dma_heap_ioctl_allocate()`，用 `charge_pid_fd` 指明被计费客户端，system heap 去掉 `__GFP_ACCOUNT` 避免重复；新增 LSM 钩子 `security_dma_heap_alloc` 与 SELinux `charge_to` 权限；评审：Barry Song 质疑 `mem_accounting` 开关与补丁拆分，König 指出按 PID 计费对「中心化分配器」不成立，作者回复后续可改传 cgroup fd | R4、R29，A |
| dmem 控制器 | 已合入（Phoronix 报道为 6.14 周期，具体首个版本以 git tag 为准，待核实） | `dmem.max/min/low/current/capacity`，语义同 memcg，bytes 为单位；仅 DRM（Xe 等）接入，TTM 驱动易接入 | R5、R30，A/C |
| dmem + CMA 堆 | v2（2026-02-18） | `dma_heap.mem_accounting` 默认关闭；dmem 用于 CMA 堆，是因为能按每个后备区域设限 | R6，A |
| dmem 双计费到 memcg | v2（2026-05-19） | 允许把 dmem 分配同时计入 memcg，并有控制文件 | R7，A（仅见摘要，细节待核实） |
| dmem 回收 / 软限 | 2026-05/06 提案 | v6「给 dmem 加回收」系列、`dmem.high` 软限提案；均为提案 | R31，A |
| GPU 内存 tracepoint | `gpu_mem_total` 已在 Android common 内核；`gpu_mem_imported` 2021 提案 | pid=0 为全局，正数为进程；gpuservice BPF 按 GPU ID+PID 聚合。DRM GEM 层按实例而非按进程计数的系列（Gurchetan Singh）是否合入：待核实 | R32，A |

**dmem 在 UMA 手机上的适用性（判断）。** dmem 的设计前提是「有一块可枚举、可独占的设备内存区域」（独显 VRAM、CMA 区域）。手机 GPU、ISP、NPU 多与 CPU 共享同一 LPDDR，设备缓冲来自 system heap 的普通页，没有独立区域可限额；因此对手机而言 dmem 只对 CMA 或预留区有意义，system heap 的计量仍须靠 memcg（这正是 Esteve RFC 去掉 `__GFP_ACCOUNT` 改走 `MEMCG_DMABUF` 的原因）。但 Chanudet 的「dmem 双计费到 memcg」说明社区在认真处理「区域配额 + memcg 账本」两层并存，这对 MM-2 有利。Android 对 dmem 的采纳：未找到公开资料。

**这说明什么：** 统一记账底座在上游并没有一条可直接依赖的路径；dma-buf 计费的「计到谁」（分配者、客户端、持有者）仍在争论，而这正是 J2 的核心。

#### 1.5 记账归属（J2）：共享模型服务

- **AICore（Android）。** 面向应用的 ML Kit GenAI 在前台限制（后台调用返回 `BACKGROUND_USE_BLOCKED`）与按应用的电量配额（`PER_APP_BATTERY_USE_QUOTA_EXCEEDED`）上有错误语义，但这两条来自开发者博客对官方文档的转述，我未核实官方原页（D→待核实）。模型内存由谁持有、是否计入调用应用：官方未说明，**未找到公开资料**。有第三方报道称某些机型为 AICore 预留内存，证据 D，不采信。
- **Apple Foundation Models 守护进程。** 未能核实，**未找到公开资料**（本次检索额度耗尽，不排除存在）。
- **可借用的原语。** Android 已有 binder 路径上 dma-buf 所有权转移的先例（Mercier 2023 的 binder 补丁，R29）；Esteve 的 `charge_pid_fd` 是更通用形式，但 König 指出的「中心化分配器按 PID 不成立」恰恰是共享模型服务的场景：服务代多个应用分配 KV、权重，客户端很多、请求并发。
- **推论（判断）。** 共享底座权重应记在「系统服务」名下（一次性，与客户端数量无关）；每会话的 KV/激活应记到会话 cgroup，并带「请求方」标签，使 LMKD 与限额在杀进程前能区分「杀哪个应用能真正释放内存」。mzCache 报告 OS 低内存杀手倾向先杀大 LLM 进程（R11，C），说明若不做归属，共享服务本身会成为头号被杀对象，而杀它又会让所有客户端失败。
- **侧信道。** 本子模块仅记录线索：前缀缓存的时序侧信道属 J2 的另一半，已发表攻击与防护本次未检索，待 C1b/C4b 或后续补，**待核实**。

### Q5 QoS 供给：`memory.min/low` 双契约先例

| 先例 | 契约形态 | 保护对象 | 回收动作 | 备注 | 证据 |
|---|---|---|---|---|---|
| Meta TMO/Senpai/oomd | 无硬保护；以 PSI 压力为目标，Senpai 持续下推冷页 | 全机群 | `memory.reclaim` 写入（含 `swappiness=` 参数，因 Senpai 此前改全局 swappiness 会竞争） | 省 20%–32% 内存；服务器 SSD/zswap（R18、R19） | A |
| Google 主动回收 | 未在本次检索到 Google 官方新文档 | — | — | 未找到公开资料（本次仅核实了 `memory.reclaim` 接口，不是 Google 论文） | — |
| systemd-oomd | 以 `memory.low` 语义选杀（看回收活动而非最大占用）；默认 `ManagedOOMMemoryPressureLimit=4%` 等 | 用户会话 | 杀 cgroup | 2020–2023 的 Fedora 资料；低内存机型上有误杀登录的缺陷报告（R20、R33） | C |
| Fedora uresourced | 为活跃图形会话设内存保护（250MiB 量级，配置文件可改） | 前台会话 | 保护 | 仅 Workstation 带；当前行为待核实 | C |
| ChromeOS ARCVM balloon | 气球在宿主与客户机之间搬运内存 | ARC 与 Chrome 的公平 | 低压：按页缓存年龄；高压：按 LMKD 与丢弃优先级 | 标签丢弃 -50% 且不触发 ARC 应用被杀（R10） | B |
| Android 17 Memory Limiter | 天花板（`high`、`swap.max`），无地板 | 可见进程 vs 不可见进程 | 节流→压 zRAM→杀 | 缓存进程冻结后最大化回收（R2） | A |

**Android 是否按应用建 memcg。** 现状可以拆成三层说：
1. LMKD 文档自 Android 11 起要求内核 `CONFIG_MEMCG`，并说 LMKD 用 memcg 按重要性给进程设限（R17，A，旧文档）。
2. Android 17 的 Memory Limiter 对每个 UID≥10000 的应用进程设 `memory.high`、`memory.swap.max`（R2，A）。
3. 荣耀用 memcg 强制回收非前台应用匿名页（R8，C）。
所以「按进程（应用进程）建 memcg 并设值」在 Android 17 起是平台默认；cgroup 目录是按 UID/PID 还是按应用组织：文档未写，**待核实**。**没有任何一家把 `memory.min/low` 作为「前台/后台双契约」的保护侧在手机上公开使用**（本次检索范围：AOSP 文档、LWN、Android 开发者博客）；保护侧的先例只有桌面（uresourced）与 VM 气球（ChromeOS）。

**用户注意力感知的研究与实践。**
- 学术：Acclaim（ATC 2020）把后台应用的空闲页让给前台（前台感知驱逐 FAE+预测式轻量回收 LWP），显著减少 re-fault 与 direct reclaim（R21，A）；PMR（ATC 2025）并行化页收缩与回写，响应时间最多 -43.6%（R22，A）。Fleet 与 Marvin：本次未检到原文，待核实。
- 工业：Android 17 可见/不可见分档；荣耀回收时跳过前台应用并在应用退到后台时做「活跃老化」（R8，C）；ChromeOS 用优先级仲裁（R10）。
- 学术近作：mzCache（MobiCom 2026）把 LLM 内存切成细粒度共享缓冲，利用统一内存让 GPU 继续运行而 CPU 恢复数据，重点在后台空闲阶段被杀的问题（R11，C）；LLMaaS（arXiv 2403.11805，2024）把 LLM 上下文内存与应用内存管理分离（R34，C）。
- 前台以外的信号：亮屏、用户正等待 Agent 结果、Agent 任务的用户意图级别——**未找到公开的系统实现或论文**，检索范围同上，另搜了「attention-aware memory scheduling」类关键词仅得上述 mzCache/LLMaaS。

**这说明什么：** 工业界已把 memcg 当作每进程配额接口，但只实现了「天花板+可见性」，没有「地板+注意力」。保护侧（`min/low`）是空白，也是最可能的差异化落点；同时必须承认，天花板式限额的简单性（按整机 RAM 查表）是 Google 有意的取舍，我方的保护契约需要证明它不会引入难以调试的非确定性。

### Q6 NPU 内存抽象

**Linux accel 与通用底座。** accel 子系统沿用 DRM GEM 与 dma-buf。2026 年的新进展：
- NXP Neutron 驱动系列（v2，2026-03-06，9 个补丁），第 1 个补丁扩展 GEM DMA 辅助以支持非一致 DMA 缓冲的双向映射；评审指出用户态部分闭源（R12，A）。
- v7.1 合并窗口摘要中的 amdxdna 变更包括「支持按 BO 查询内存用量」和「允许强制 DMA 经 IOMMU IOVA」，同批出现 shmem GEM 的页访问/脏位跟踪与 dma-buf 撤销（revoke）机制（R13，C，二手摘要，细节待核实）。
- ivpu 近期禁止重新导出被导入的 GEM 对象（R13，C）。

**判断：** accel 驱动已开始提供**单 BO 内存用量查询**，这是 NPU 记账可见性的第一个上游原语；但手机 NPU（高通 Hexagon、联发科 APU、Tensor TPU、麒麟/Ascend）仍几乎不走 accel 子系统。

**Qualcomm。** 内核侧 FastRPC UAPI 提供 `FASTRPC_IOCTL_ALLOC_DMA_BUFF`、`FREE_DMA_BUFF`、`MEM_MAP`，新版增加 `MEM_UNMAP`、`GET_DSP_INFO`；设备树绑定把计算上下文 bank 绑到应用处理器 SMMU 的 `iommus` 上（R35，A）。rpcmem 是用户态分配器、建立在 dma-buf 之上：本次未找到官方文档，**待核实**。

**MediaTek。** ExecuTorch 的 MediaTek 后端附带 `libneuron_buffer_allocator.so`，说明有自有缓冲分配器（R36，A 文档）。Neuron Adapter 是否接受 dma-buf fd 或 AHardwareBuffer：未找到官方文档，第三方博客称 Android 15 的 AHardwareBuffer 增加了 NPU 读写用法位，我未能对照 NDK 文档核实，标 D，待核实。

**Apple。** 统一内存与 ANE（经 Core ML）的内存归属：本次未检索到资料，**待核实**。

**标准化。** NNAPI 已在 Android 15 被弃用（背景知识，本次未取得链接，待核实）；跨厂商 NPU 内存抽象的收敛迹象：未找到。Windows MCDM 下 NPU 内存可见性：未检索，待核实。

**NPU 共享内存隔离研究。**
- sNPU（ISCA 2024，上交 IPADS）：NPU Guarder 加强访问控制，NPU Isolator 隔离 scratchpad 与 NoC 路由，NPU Monitor 缩小软件 TCB；论文称对 NPU 运行性能无影响（R14，A，作者口径）。
- TZ-LLM（arXiv 2511.13717，2025-11）：TrustZone 下 REE/TEE 对 NPU 分时，非安全模式阻断 NPU 访问安全内存，安全模式限定 MMIO 与中断，Rockchip NPU 世界切换约 32ms（R15，C）。
- 针对手机 NPU 的缓存或共享内存侧信道专项论文：未找到公开资料（检索范围：上述两条检索结果，覆盖不足）。

**这说明什么：** NPU 内存的三个最小需求——可见（谁占多少）、可归属（计到哪个 cgroup）、可回收（驱逐或杀持有者时能否撤销映射）——在 Linux 通用栈里只有「可见」的雏形（单 BO 查询），后两者没有。dma-buf revoke 的出现值得跟踪，它可能是「可回收」的上游原语（判断，细节待核实）。

### Q8 记账可见性缺口

标注：**可见** = 系统/开发者可观测其总量与持有者；**可归属** = 可稳定计到某应用或会话（cgroup/UID）；**可回收** = 内存压力下系统能在不杀持有者的情况下收回。控制方：G=Google，A=Apple，H=Huawei，V=芯片或驱动厂商，K=上游内核社区。✓=有公开依据，△=部分或条件成立，✗=没有，？=未找到公开资料或待核实。

| 内存类型 | Android 可见 | Android 可归属 | Android 可回收 | iOS 可见/归属/回收 | HarmonyOS 可见/归属/回收 | 控制方与说明 |
|---|---|---|---|---|---|---|
| 匿名页 | ✓（smaps、memcg、`AnonSwap` 口径，R1、R2） | ✓（进程 memcg，Android 17 限额） | ✓（zRAM 换出，限额触发） | 可见 ✓（footprint，待核实口径）/归属 ✓/回收：压缩内存与 Jetsam，细节待核实 | ？/？/Purgeable 仅应用自愿（R28） | G；K |
| 文件页 | ✓ | △（计到首次访问者 memcg；共享库页难拆分） | ✓（干净页可丢） | ？ | ？ | K；共享库页是归属难点 |
| dma-buf | ✓（BPF iterator，R3） | △（system heap 目前靠 `__GFP_ACCOUNT` 或未计；`MEMCG_DMABUF` 是 RFC，R4） | ✗（被持有的 dma-buf 无法回收，只能杀持有者或由导出者释放） | ？ | ？ | G+K；归属规则待上游裁决 |
| GPU 内存 | △（`gpu_mem_total` 依赖厂商驱动上报，R32） | △（per-pid，厂商相关） | ✗/△（驱动自管，公开资料缺） | ？ | ？ | V（GPU 厂商驱动）为主 |
| NPU 内存 | ✗/△（accel 驱动有单 BO 查询，R13；手机 NPU 多私有） | ✗ | ✗（revoke 机制待观察） | ？ | ？ | V；闭源驱动 |
| KV cache | ✗（对 OS 是匿名页/dma-buf/GPU 缓冲，无语义） | △（若放进会话进程 memcg 则随进程） | △（只能整体换出或杀进程，无「按 token 价值」回收） | ✗ | ✗ | 应用/推理运行时；OS 无语义 |
| 模型权重 | △（mmap 文件页可见，若加载进 GPU/NPU 则转入上述类别） | △（mmap 页计首次访问者；共享服务时归属混乱） | ✓（文件页）/✗（已转入设备缓冲） | ✗ | ✗ | 应用/运行时 |
| zram | ✓（全局统计；`memory.swap.current` 按 cgroup，R2） | ✓（按 cgroup swap 计费） | 本身不是回收对象，但 writeback 到闪存有磨损约束 | 压缩内存：概念对应但机制不同（不叫 zram） | ESwap/zram：待核实 | G；K |

**关键缺口（判断）：**
1. **dma-buf 与 GPU/NPU 内存在 Android 17 的限额之外**。限额口径是 anon+swap；把推理的权重和 KV 放到 dma-buf/GPU/NPU 缓冲，即可绕开限额，同时在记账上对 LMKD 不可见或不可归属。这是 Agent/模型内存最大的记账盲区。
2. **「可回收」缺口比「可见」缺口更深**：设备缓冲被持有时只能杀持有者。所以统一记账之外，还需要「可撤销/可迁移」原语，MM-7 的四种驱逐去向要依赖它，而上游尚未提供。
3. **KV 与权重对 OS 无语义**：除非运行时用特定 API 声明类型与价值，OS 只能按页龄回收。
4. iOS 与 HarmonyOS 的单元格大量为「？」是资料空白，不是已证无。

---

## §4 趋势判断

**正在收敛的方向**
- 把 memcg 当作每应用/每进程的统一配额接口，并让系统服务（AMS、冻结）联动（R2）。
- dma-buf 统计从 sysfs 迁到 BPF（R3）。
- 设备内存配额采用「区域配额（dmem）+ memcg 账本」双层（R6、R7，判断）。
- 回收由用户态按 cgroup 主动驱动（`memory.reclaim`，TMO/Senpai；Honor 的 memcg 强制回收）（R8、R19）。

**公认的空白点**
- dma-buf、GPU、NPU 内存的归属与限额：没有已合入的上游方案，也没有 Android 平台声明。
- 共享模型服务的内存归属：三平台均无公开说明。
- 前台以外的注意力信号。
- `memory.min/low` 在手机上的保护契约：只有桌面与 VM 先例。
- 手机 NPU 的跨厂商内存抽象与隔离研究。

**仍有分歧的问题**
- MGLRU 去留与是否与传统 LRU 统一（R8、R9）。
- dma-buf 该计给分配者、客户端还是持有者，以及 PID 还是 cgroup fd（R4 评审）。
- 限额应是天花板（Android 17）还是保护+天花板组合。
- 合作式（鸿蒙 `onMemoryLevel`+Purgeable）与强制式（Android 17）哪个更适合 Agent 负载。

---

## §5 立场评审表

| 立场 ID | 判断（支持 / 挑战 / 需修订） | 关键证据 | 最强反方证据 | 修订建议 | 置信度（高 / 中 / 低） |
|---|---|---|---|---|---|
| MM-1 统一记账底座：dma-buf 可见性 + 会话级 memcg + 扩展 PSI | **需修订** | Android 17 已用 memcg 做每进程限额（R2）；dma-buf 经 BPF iterator 可见（R3）；`MEMCG_DMABUF` RFC 给出计到客户端的语义（R4） | 平台口径是 anon+swap，未含 dma-buf/GPU（R1、R2）；dma-buf memcg 计费尚为 RFC，且 König 指出按 PID 对中心化分配器不成立（R4）；dmem 在 UMA 手机上区域化前提不成立；PSI 已按 cgroup 提供，「扩展 PSI」的具体含义未见需求证据 | (a) 把「会话」定义为 memcg 之上的归属标签，而非新 cgroup 层级，以兼容 Android 17 的按进程限额；(b) 明确 dma-buf 归属规则（分配者、请求方、持有者）并要求共享服务提供请求方标识；(c) 在设计文档中把 dma-buf/GPU/NPU 记账标成「依赖上游/厂商」的风险项；(d) 「扩展 PSI」需补出具体要扩展的信号 | 中 |
| MM-2 双策略域：传统与模型内存共享记账、策略分开 | **支持** | 上游正在做「dmem 区域配额+memcg 双计费」（R6、R7），本质是两域共享账本；Android 17 以 `swap.max` 单独封顶 zRAM（R2） | 记账尚无统一来源；若 dma-buf 不计入 memcg，两域账本无法对齐 | 在设计里把「账本」与「策略」两个接口显式分开；账本接口优先对接 memcg 与 dmem，不自建计数器 | 中 |
| MM-3 传统域冷热判别与精准供给；QoS 跟用户注意力而非进程身份 | **支持（方向），需修订（新颖性主张）** | Acclaim 前台感知驱逐（R21）；荣耀跳过前台回收（R8）；Android 17 可见/不可见分档（R2）；ChromeOS 优先级仲裁（R10） | 工业界已经是「可见性」而非「进程身份」，所以「不是跟进程身份」不是差异点；Android 17 刻意采用简单、可确定的整机 RAM 查表；MGLRU 上游不稳（R9）不适合作基础 | 差异化应落在前台以外的信号（亮屏、用户在等 Agent 结果、Agent 任务意图级别）与「保护侧 `memory.min/low`」，并避免绑定 MGLRU 页龄；需要以仿真或真机数据证明相对天花板式限额的收益 | 中 |

---

## §6 接缝发现

**J2 共享底座的记账归属与前缀共享的隔离（主责）**
- 事实：三平台均未找到官方说明系统级模型服务的内存如何计入应用（AICore、Apple Foundation Models 均无）。
- 事实：Android 上有 binder 层 dma-buf 所有权转移（Mercier 2023）与 `charge_pid_fd`（Esteve 2026）两个先例，前者面向单次转移，后者按客户端分配时计费，但都不覆盖「服务代多客户端持有且长期复用」的场景（R4、R29）。
- 判断：可行的归属方案是三层——底座权重记服务；会话 KV 记会话 cgroup 并带请求方标签；跨会话共享的前缀 KV 按「引用计数分摊」或记服务，二者需用数据比较。这三种方案的 LMKD/限额行为不同：计到服务→服务成杀进程目标；计到请求方→重复计费。
- 侧信道：仅记录线索。前缀缓存的时序侧信道已发表攻击与防护：本次未检索（检索额度耗尽），**待核实**；NPU/共享内存侧信道专项：未找到（见 Q6）。
- 需要其他子模块补的证据：C1b/C4b 的前缀共享隔离结论；C1a 的 AICore 进程模型。

---

## §7 组件特有输出：记账可见性缺口表

见 §3 Q8 的主表。此处补充一页「谁控制」摘要，供设计文档引用：

| 层 | 内容 | 控制方 | AgentOS 能否改 |
|---|---|---|---|
| 应用进程匿名/文件页、swap | memcg 配额与回收 | Google（AOSP）/OEM 内核 | OEM 可改；上游要走 AOSP/GKI |
| dma-buf 堆与导出者 | system heap、CMA heap、gralloc | Google + SoC 厂商 + 上游内核 | OEM 可在 vendor 内核补计费；上游路径长（RFC 阶段） |
| GPU 驱动内存 | 驱动私有分配 | GPU/SoC 厂商 | 受限，依赖 tracepoint 上报 |
| NPU 驱动内存 | FastRPC、Neuron、私有驱动 | 芯片厂商 | 基本不能，依赖厂商开放 |
| KV、权重语义 | 推理运行时 | 应用/运行时开发者，系统服务化后归 OS | 若 OS 提供服务则可改 |
| iOS 全栈 | Jetsam、footprint | Apple | 不可 |
| HarmonyOS | 微内核 + 应用框架 | 华为 | 仅限华为内部 |

---

## §8 参考资料与待核实清单

### 参考资料

| 编号 | 标题 | 机构或作者 | URL | 日期 |
|---|---|---|---|---|
| R1 | App broader memory limits | Android Developers Blog | https://android-developers.googleblog.com/2026/08/app-broader-memory-limits.html | 2026-08 |
| R2 | Memory Limiter | AOSP 文档 | https://source.android.com/docs/core/perf/memory-limiter | 2026 |
| R3 | [PATCH] dma-buf: Remove DMA-BUF sysfs stats（及回复） | T.J. Mercier | https://lkml.iu.edu/2601.2/09615.html 、 https://lkml.iu.edu/2601.2/05945.html | 2026-01-20 |
| R4 | [PATCH RFC 0/5] memcg: dma-buf per-cgroup accounting via pid_fd | Albert Esteve | https://lkml.iu.edu/2605.1/07247.html ；LWN：https://lwn.net/Articles/1072465/ | 2026-05-12 |
| R5 | Device Memory "DMEM" Cgroup Support Ready For Linux 6.14 | Phoronix | https://www.phoronix.com/news/DMEM-cgroup-vRAM-Control | 2025-01（以报道为准） |
| R6 | [PATCH v2 0/3] dma-buf: heaps: cma: enable dmem cgroup accounting | Eric Chanudet, Maxime Ripard | https://lkml.iu.edu/2602.2/03415.html | 2026-02-18 |
| R7 | cgroup/dmem: allow double-charging dmem allocations to memcg（v2） | Eric Chanudet | 见 R4 检索结果中的 lore.gitlab.freedesktop.org 邮件列表归档；单独 URL 待核实 | 2026-05-19 |
| R8 | Reconsidering the multi-generational LRU | LWN（Corbet） | https://lwn.net/Articles/1060967/ | 2026-03 |
| R9 | What is to be done about MGLRU? | LWN | https://lwn.net/Articles/1072866/ | 2026（LSFMM+BPF） |
| R10 | Improving performance with new ARC resource management features | chromeos.dev | https://chromeos.dev/en/posts/improving-performance-with-new-arc-resource-management-features | 2024-07-12 |
| R11 | mzCache: On-Device LLM Memory Management under Multitasking | Yu, Kim, Park, Lee | https://arxiv.org/abs/2609.01338 | 2026-09 |
| R12 | [PATCH v2 0/9] accel: New driver for NXP's Neutron NPU | NXP | https://lkml.iu.edu/hypermail/linux/kernel/2603.0/11337.html | 2026-03-06 |
| R13 | drivers/accel 的 v7.1 变更摘要 | 内核镜像 feed（二手） | https://git.radix-linux.su/kernel/linux.git/atom/drivers/accel?h=v7.1-rc5 | 2026-04 |
| R14 | sNPU: Trusted Execution Environments on Integrated NPUs（ISCA 2024） | 上交 IPADS | https://ipads.se.sjtu.edu.cn/_media/publications/feng-isca24.pdf | 2024 |
| R15 | TZ-LLM: Protecting On-Device Large Language Models with Arm TrustZone | 作者待核实 | https://arxiv.org/abs/2511.13717 | 2025-11 |
| R16 | Support 16 KB page sizes | Android Developers | https://developer.android.com/guide/practices/page-sizes | 2026 |
| R17 | Low Memory Killer Daemon | AOSP 文档 | https://source.android.com/docs/core/perf/lmkd | Android 11 起 |
| R18 | TMO: Transparent Memory Offloading in Datacenters（ASPLOS 2022）；Meta 工程博客 | Meta | https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/ | 2022-06-20 |
| R19 | [PATCH v6 2/2] mm: add swappiness= arg to memory.reclaim | Dan Schatzberg | https://lkml.iu.edu/hypermail/linux/kernel/2401.0/01941.html | 2024-01 |
| R20 | Changes/EnableSystemdOomd | Fedora | https://www.fedoraproject.org/wiki/Changes/EnableSystemdOomd | 2020–2021 |
| R21 | Acclaim: Adaptive Memory Reclaim to Improve User Experience in Android Systems | Liang 等（CityU） | https://www.usenix.org/conference/atc20/presentation/liang-yu | 2020 |
| R22 | PMR: Fast Application Response via Parallel Memory Reclaim on Mobile Devices | Li 等 | https://www.usenix.org/conference/atc25/presentation/li-wentong | 2025 |
| R23 | [PATCH v7 00/15] mm/mglru: improve reclaim loop and dirty folio handling | Kairui Song 等 | https://patchew.org/linux/20260428-mglru-reclaim-v7-0-02fabb92dc43@tencent.com/ | 2026-04 |
| R24 | memorystatus_kills.md、memorystatus_notify.md | Apple xnu | https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_kills.md | 持续更新 |
| R25 | iOS 26 增大内存限制相关开发者论坛帖 | Apple Developer Forums | https://developer.apple.com/forums/thread/834805 、 https://developer.apple.com/forums/thread/823061 | 2026 |
| R26 | com.apple.developer.kernel.increased-memory-limit | Apple | https://developer.apple.com/tutorials/data/documentation/bundleresources/entitlements/com.apple.developer.kernel.increased-memory-limit.md | — |
| R27 | HarmonyOS onMemoryLevel 等内存接口整理 | 社区博客 | https://bbs.huaweicloud.com/blogs/480019 | — |
| R28 | Purgeable Memory C API | 华为开发者 | https://developer.huawei.com/consumer/cn/doc/doccenter-references/api/capi-memory-purgmem | — |
| R29 | Track exported dma-buffers with memcg（v2） | T.J. Mercier | https://lore.kernel.org/20230123191728.2928839-2-tjmercier@google.com/ ；LWN：https://lwn.net/Articles/920886/ | 2023-01 |
| R30 | Linux cgroup v2 文档（含 DMEM 接口、`memory.min/low/reclaim`） | kernel.org | https://docs.kernel.org/admin-guide/cgroup-v2.html | 持续更新 |
| R31 | [PATCH v6 0/6] Add reclaim to the dmem cgroup controller；dmem.high 软限 v6 | Thomas Hellstrom 等 | https://patchew.org/linux/20260611173301.17473-1-thomas.hellstrom@linux.intel.com/ ；https://patchew.org/linux/20260531-feature-dmem-high-v6-1-20563ecd6dc7@gmail.com/ | 2026-05/06 |
| R32 | Add gpu memory tracepoints | Yiwei Zhang | https://lore.kernel.org/r/20200302234840.57188-1-zzyiwei@google.com/ ；gpuservice BPF：https://android.googlesource.com/platform/frameworks/native/+/445e98c792dfb991cd408de5699c6e3b813973d9/services/gpuservice/bpfprogs/gpu_mem.c | 2020 |
| R33 | Bug 1964153 / 2177722（systemd-oomd 误杀） | Red Hat Bugzilla | https://bugzilla.redhat.com/show_bug.cgi?id=1964153 | — |
| R34 | LLM as a System Service on Mobile Devices | 作者待核实 | https://arxiv.org/pdf/2403.11805 | 2024-03 |
| R35 | fastrpc.h UAPI；qcom,fastrpc 设备树绑定 | Linux/AOSP | https://git.zx2c4.com/linux-dev/tree/include/uapi/misc/fastrpc.h | — |
| R36 | ExecuTorch MediaTek 后端文档 | PyTorch | https://docs.pytorch.org/executorch/stable/_sources/backends-mediatek.md.txt | — |

### 待核实清单

1. dma-buf sysfs 统计删除补丁最终合入的树与内核版本（R3 仅见评审）。
2. dmem 控制器首个合入内核版本（R5 为媒体报道，需以 git tag/log 复核）；dmem 回收、`dmem.high` 是否合入。
3. `MEMCG_DMABUF` RFC 后续版本、评审结论、是否有 Android 侧声明。
4. Android 17 Memory Limiter：dma-buf/GPU 内存是否计入 `memory.high`；cgroup 层级是按 UID 还是 PID；配置文件在 `/system/etc` 还是 `/vendor/etc`。
5. Android 各 GKI 分支 MGLRU 默认开启版本；cached apps freezer 与 app hibernation 的版本节点；mTHP/大 folio zRAM 换入的主线版本。
6. LSFMM+BPF 2026 MGLRU 议题的最终结论，及 reclaim_ext 的进展。
7. iOS 26 对 Jetsam/footprint 记账是否有官方变更；Apple Foundation Models 守护进程的内存归属。
8. HarmonyOS NEXT 的页回收、换出机制，ESwap 在 HarmonyOS（非 OpenHarmony）中的存在性。
9. AICore 模型内存归属与配额的官方文档（`BACKGROUND_USE_BLOCKED`、`PER_APP_BATTERY_USE_QUOTA_EXCEEDED` 两个错误码仅见二手转述）。
10. MediaTek Neuron Adapter 对 dma-buf / AHardwareBuffer 的支持；AHardwareBuffer 的 NPU 用法位；Qualcomm rpcmem 官方文档；Apple ANE 内存归属。
11. NNAPI 在 Android 15 弃用的官方出处链接；Windows MCDM 的 NPU 内存可见性。
12. Fleet、Marvin 等移动端内存管理论文原文；Google 主动回收（far memory）论文是否有更新工作。
13. 前缀缓存时序侧信道的已发表攻击与防护（J2 后半），NPU/手机共享内存侧信道专项论文。
14. v7.1 accel 变更摘要（R13）为二手信息，amdxdna 单 BO 查询与 dma-buf revoke 需查 git 原提交。
15. 16KB 页 Play 截止日期（2027-02-01）与曾出现的 2025-11-01、2026-05-31 说法的关系，以 Play 当前政策页为准。

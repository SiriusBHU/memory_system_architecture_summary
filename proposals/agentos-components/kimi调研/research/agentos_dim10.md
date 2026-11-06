# AgentOS 内存管理组件调研 · 维度 A：移动端内存管理现状 + QoS 供给

- 调研日期：2026-11-06
- 时间范围：2024-01 ~ 2026-11 为主，奠基性工作标注年份
- 子代理：维度 A（传统内存域为主，含与模型内存域互通相关的记账底座证据）
- 说明：本文区分【事实】（来源可核）与【判断】（调研者推断）；媒体来源仅作线索并注明。

---

## 1. 技术谱系表

### 1.1 回收与查杀链路（Android / Linux）

| 技术 | 首次落地 | 现状（2024-2026） | 关键机制 | 来源 |
|---|---|---|---|---|
| in-kernel LMK driver | ~2011（Android） | 内核 4.12 起从上游移除，由 userspace lmkd 取代 | minfree 六档水位 + oom_adj | [^lmkd-doc^] |
| LMKD (userspace) | Android 9（2018） | 现役主线；Android 17 (API 37) 仍在演进 | AMS/OomAdjuster 下发 oom_score_adj，lmkd 决策并 pidfd kill | [^lmkd-arch^] |
| PSI monitor 模式 | Android 10（2019） | `ro.lmk.use_psi` 默认 true，优先 PSI、回落 vmpressure | 三级 PSI 阈值（SOME 70ms/1s、SOME 100ms/1s、FULL 70ms/1s），`ro.lmk.psi_complete_stall_ms` 默认 700 | [^lmkd-psi^][^lmkd-props^] |
| LMKD 新策略（use_new_strategy） | Android 10+ | low-RAM 或新设备默认启用；cgroup v2 下强制新策略 | 基于 zone 水位 + free swap + thrashing(refault) 的查杀 | [^lmkd-src^] |
| MGLRU | Linux 6.1（2022-12，合并） | Android 14 全系内核（android14-5.15/6.1）默认开启，Pixel 8 首发；Android 15 GKI 6.6、Android 17 内核 6.18 均默认开启；主要发行版默认开启 | 多代多链表页龄、页表扫描老化、refault/eviction PID 控制器、`min_ttl_ms` 防抖 | [^mglru-android14^][^mglru-lpc24^][^gki-tree^] |
| Android 17 MemoryLimiter | 2026（API 37） | 对所有应用生效（无需 targetSdk 37） | 按设备 RAM 设每应用 anon+swap 硬上限，超限终止（退出描述含 `MemoryLimiter:AnonSwap`）；`am memory-limiter` 调试接口 | [^a17-memlimit^][^a17-censuus^] |
| Android 17 内核基线 | 2026 | `android17-6.18-2026-06_r6`（Linux 6.18.21） | 开启 MGLRU、sched_ext、AutoFDO | [^a17-kernel^] |

### 1.2 交换与压缩链路

| 技术 | 首次落地 | 现状 | 关键机制 | 来源 |
|---|---|---|---|---|
| zRAM | Linux 3.14（2014） | Android 全量标配；社区模块显示多 zRAM、recompression、UFFD GC 在 OEM/玩机圈扩散 | 压缩匿名页驻留 RAM；`ro.lmk.swap_compression_ratio` 需按实测压缩比校准 | [^zram-tune^][^lmk-ctrl^] |
| zRAM writeback（回写存储） | 内核 4.20（2018）；Android 12 起有 `ZramWriteback` 服务 | Android 16 源码中仍现役（frameworks/base `ZramWriteback.java`）：JobScheduler 标记 idle 页并周期回写 | `MARK_IDLE_JOB`/`WRITEBACK_IDLE_JOB`；`ro.zram.mark_idle_delay_mins` | [^zram-wb^] |
| zswap 演进 | Linux 3.11（2013） | 6.8+ 支持 per-cgroup `memory.zswap.writeback=0`（禁回写防 LRU 反转）；6.18 起 zswap 改用 zsmalloc | cgroup 粒度回写控制 = 双契约工具之一 | [^zswap-chris^] |
| OpenHarmony ESWAP | OpenHarmony 3.1（2022-04） | 现役；zswapd 常驻线程把 zRAM 压缩匿名页加密换出到 ESwap 分区；per-memcg 参数（score/ub_mem2zram_ratio/ub_zram2ufs_ratio/refault_threshold）；按"账户状态"设回收优先级与目标可用内存 | memcg 回收优先级 + 目标 buffer 水线 + refault 阈值，三层 RAM/ZRAM/ESwap | [^eswap^][^eswap-doc^] |
| HarmonyOS Hyperhold | HDC 2021 | 宣称后台应用保持率领先 Android 50% | 应用生命周期（前台/短期活跃/持续任务/挂起）驱动的压缩、多线程压缩、聚合换出 | [^hyperhold^] |
| HarmonyOS 7 超空间内存 | 2026-10-22 官宣 | 60+ 存量机型 OTA；16GB 机型最多等效 +3GB；媒体称压缩率 65%+（传统 30-40%） | 方舟引擎 + AI 内存画像，对后台应用动态"瘦身"（高频保留/低频实时压缩随叫随解） | [^hos7^][^hos7-2^] |

### 1.3 记账与观测底座

| 技术 | 首次落地 | 现状 | 关键机制 | 来源 |
|---|---|---|---|---|
| PSI | Linux 4.20（2018） | Android lmkd/systemd-oomd/ChromeOS 全面依赖；cgroup v2 per-cgroup `memory.pressure` | some/full + avg10/60/300 + 可 poll 的 trigger（阈值+窗口） | [^psi-qualcomm^][^oomd-man^] |
| PSI_IRQ | Linux 6.1（2022-09 合入 tip） | 上游现役；openEuler 另有 PSI 细粒度扩展（pressure.stat、per-cgroup reclaim stall 细分，2023-11，OLK 下游） | IRQ/SOFTIRQ 压力计入 `irq.pressure` | [^psi-irq^][^psi-fine^] |
| dmabuf memcg 记账 | 2023-01 补丁系列（T.J. Mercier/Google）→ 上游 6.5 合入（2023-08）【事实；合入版本置信度中高】 | `memory.stat` 增加 `dmabuf` 键；charge 黏附分配者 cgroup，可经 binder 转移 | 解决 Android 图形 buffer 由中心化进程分配导致的记账失真 | [^dmabuf-v1^][^dmabuf-v2^] |
| dmabuf charge_pid_fd（跨 cgroup 显式记账） | 2026-05-18 RFC（Albert Esteve/Red Hat） | **未合入**（RFC 阶段），带 selftests | `dma_heap_allocation_data.charge_pid_fd`：分配时把账记到目标进程的 cgroup | [^dmabuf-rfc26^] |
| Honor memory.aging（MGLRU 主动老化接口） | 2026-07 RFC v2 | **未合入**；已作为 GKI 模块在 6.6/6.12/6.18（高通/MTK）出货，Android 与服务器负载均有收益 | 把 debugfs `lru_gen "+"` 原语暴露为 per-cgroup `memory.aging` | [^mem-aging^] |

### 1.4 iOS Jetsam（memorystatus）谱系

| 能力 | 年份 | 内容 | 来源 |
|---|---|---|---|
| Jetsam/memorystatus 基础 | 2006-2012（kern_memorystatus.c） | 按优先级桶从低到高查杀；`memorystatus_control()` syscall | [^moxii^] |
| 优先级带 revision 2 | ~iOS 11-13 代际 | 带扩展到 210：IDLE 0 → BACKGROUND 30 → FREEZER 75 → FOREGROUND 100 → ... → CRITICAL 190；AGING_BAND1/2；ELEVATED_INACTIVE | [^jetsam-hdr^] |
| 高水位/每进程上限 | 长期现役 | `memlimit_active/inactive`、fatal 属性；iOS 15+ 开放 `com.apple.developer.kernel.increased-memory-limit` entitlement 提高限额 | [^jetsam-hdr^][^ios-ent^] |
| 使用概率/重启行为驱动调度 | 现役（xnu 源码） | `memorystatus_properties_entry_v1.use_probability`；`P_MEMSTAT_RELAUNCH_*` 决定 daemon 在 aging band 的停留时间（高/中/低重启概率 = 10/5/2 秒缩放）；JLD（jetsam loop detection）激进来回收 elevated idle 进程 | [^jetsam-useprob^][^jetsam-relaunch^] |
| CONFIG_FREEZE / CONFIG_SECLUDED_MEMORY | 现役（xnu 源码） | 冻结进程进 freezer 带；`secluded_for_apps` 时优先级 ≥ FOREGROUND 的进程可用隔离内存池（前台专属内存供给的内核级先例） | [^jetsam-src^] |
| macOS 侧 | 2025 | jetsam 在 macOS 为按进程 opt-in，主要由 RunningBoard 管理后台 daemon；前台 macOS 应用不因内存压力被杀 | [^macos-jetsam^] |

---

## 2. 关键数据（带出处与日期）

**MGLRU（Google 官方/LPC 数据）**
- Pixel 6 开 MGLRU：App 总体启动时间 -6.60%；杀后台（进程终止）-8.04%；kswapd CPU -54.50%；直接回收次数 -81.10%。（2022 LPC 演示，2023-10 报道）[^mglru-android14^]
- Google 生产/产品汇总：服务器 kswapd CPU -40%；Android 手机低内存查杀 -85%；ChromeOS UI 渲染延迟 -18%；Android 应用冷启动 -16%；Google 生产用 MGLRU 模拟 kstaled，同等省内存下 CPU 开销 1/5；KVM 二级 MMU lockless 扫描降锁竞争 85%。（LPC 2024 slides）[^mglru-lpc24^]
- 已知问题（2024-2026 上游）：writeback 落后会触发 cgroup OOM（"wake up flushers conditionally" 修复在邮件列表）；缺 cgroup 级 writeback throttling（修复中，全局仍缺）；min_ttl_ms 防抖需 memcg 尊重（6.6.8 stable 修复 kswapd 100% CPU 问题）。2026-05 LWN/LSFMM：MGLRU"surprisingly good"，TTL 防抖有效，但仍有改进议程。[^mglru-lpc24^][^mglru-lwn26^][^mglru-ttl^]

**LMKD/PSI 参数级事实**
- 默认 PSI 阈值：`{PSI_SOME,70ms}/{PSI_SOME,100ms}/{PSI_FULL,70ms}`（1s 窗口）；`ro.lmk.psi_complete_stall_ms` 默认 700；`ro.lmk.thrashing_limit` 高性能机 100 / 低 RAM 机 30（%）。Pixel 实测属性例：`psi_complete_stall_ms=150`、`kill_timeout_ms=100`、`swap_util_max=90`、`thrashing_limit=30`。[^lmkd-psi^][^lmkd-props^][^pixel-props^]
- PSI 样例（Qualcomm LPC 2023 slides）：`memory some avg10=70.24 ... full avg10=57.59`；PSI monitor 例：`echo "some 150000 1000000" > /proc/pressure/memory`（150ms/1s）。[^psi-qualcomm^]

**zswap/zRAM**
- zswap per-cgroup 禁回写（6.8+）：被拒的不可压缩页回到 active list 而非落盘，防 LRU 反转：`echo 0 > .../memory.zswap.writeback`。（Chris Down，2026-03）[^zswap-chris^]
- zRAM 档位经验值：低 RAM Go 机 zRAM=50% RAM LZ4；旗舰 8-12GB 用 50% LZ4/ZSTD；16GB+ 用 25-50% ZSTD；lmkd 的 `swap_compression_ratio` 应按实测校准。（2026-08 技术书章节）[^zram-tune^]

**HarmonyOS**
- Hyperhold（HDC 2021）：Mate40 Pro 长测内存拆解；宣称后台应用保持率较 Android 领先 50%。[^hyperhold^]
- HarmonyOS 7 超空间内存（2026-10-22 官宣）：16GB 机型最多 +3GB 等效内存，60+ 机型 OTA；媒体报道"压缩率 65%+（行业常见 30-40%）、保活 App 数平均 +42%"（媒体口径，置信中）。[^hos7^][^hos7-2^]

**ChromeOS（双栈仲裁先例）**
- ARC++ VMMMS + on Demand（2024-07 官方博客）：Chrome tab discards -50%（且不触发 ARC++ 应用查杀）；不用 ARC++ 的用户省电 15-20%、省 ~750MB 内存。[^chromeos-vm^]

**Android 17 MemoryLimiter（2026）**
- 硬上限按设备总 RAM 定；超限终止且默认无日志（"fails silently"），`ApplicationExitInfo` 描述含 `MemoryLimiter:AnonSwap`；Play vitals"Excessive memory usage"坏行为阈值 4% 会话。[^a17-memlimit^][^a17-stora^]

**学术研究（QoS/注意力相关）**
- FALCON（MobiSys 2012）：上下文预测预启动，延迟 -50% vs LRU，能耗代价 ~2%；常驻 <2MB。[^falcon^]
- TPP（DATE 2023）：预测式两阶段预取，启动时间最高 -52.5%/平均 -37%，预取仅 1.31MB；指出 PBAL 类预测准确率 <70%、误预测浪费数百 MB。[^tpp^]
- DeepAPP（SenSys 2019）：DRL 预加载，加载时间 -68.14%，平均预载内存 190.6MB。[^deepapp^]
- AppFlow（arXiv 2026-03）：大 App（GB 级，含 LLM 权重）冷启动内存调度；97.2% 冷启动 I/O 等待涉及可预测静态数据；切换时 79% DRAM I/O 带宽空闲；MAPLE（LLM 预测下一 App）命中率仅 52%，误预测代价不可接受；预载上限 100MB（<5% DRAM on 4GB）且"压力下可被回收"。[^appflow^]

**服务端 QoS 先例（移植参考）**
- Facebook resctl-demo：workload.slice 用 `memory.low` 软保护主负载、hostcritical.slice 用 `memory.min` 硬保 768MB、sideload.slice 用 `memory.high` 限膨胀——三层契约即"交互-后台双契约"的服务器版。[^resctl^]
- systemd-oomd：PSI per-cgroup + `ManagedOOMMemoryPressure=kill`，压力超阈值持续 N 秒后杀整个 cgroup（`memory.oom.group=1`）；官方建议延迟敏感的 `user@UID.service` 用更低阈值（40% vs system.slice 60%）。[^oomd-man^]
- 会话级 memcg 先例：systemd `session-N.scope` 天然是"会话级 memcg"；2026 年已有真实工程（tmuxctl/PocketShell）给每个 agent 会话包一层 memory-capped scope（slice ~46G、每会话 ~10G），防 OOM 级联。[^pocketshell^]

---

## 3. 趋势判断

**收敛方向（事实+判断）：**
1. **压力信号收敛到 PSI 家族**：lmkd（2019 起）、systemd-oomd、ChromeOS 全部以 PSI some/full+持续时长为触发语义；上游还在扩维（PSI_IRQ 6.1；openEuler 下游的 pressure.stat 细粒度）。"扩展 PSI"方向与上游演进一致，但上游对新增 PSI 维度非常保守（判断）。
2. **回收器收敛到 MGLRU，但供给仍靠"杀"**：MGLRU 已在 Android 14-17 全量默认；然而供给保障的主手段仍是 oom_score_adj 查杀 + CachedAppFreezer +（2026 起）MemoryLimiter 硬上限。cgroup memory.min/low 在 Android 框架层**基本未被用作前台供给契约**（未见 AOSP 证据；其 memcg 用途主要是 lmkd 的 per-app 统计与 thrashing 计算）——这与服务端（Facebook resctl、K8s Guaranteed 用 memory.low）形成鲜明反差。【事实（检索范围内未见反例），置信中高】
3. **QoS 从"进程身份"向"使用行为"缓慢迁移**：Android 侧 App Standby Buckets（2018，active/working_set/frequent/rare/restricted，Android 13 把 restricted 触发从 45 天缩到 8 天）管 job/alarm/网络但**不管内存供给**；iOS 侧 Jetsam 的 use_probability / relaunch flags / aging band 已经是"使用概率感知"的查杀调度。两者都到了"行为分级"，但都停在查杀/限流，未到"供给保障"。[^standby^][^jetsam-useprob^]
4. **dmabuf 记账上游化完成、跨 cgroup 归账在路上**：`memory.stat dmabuf` 已上游（6.5）；2026-05 的 charge_pid_fd RFC（Red Hat）正在解决"分配者≠责任者"的显式归账，尚未合入。会话级 memcg 直接可读 dmabuf 账是可行底座，但"Agent 代应用分配"场景的归账转移仍需 binder 转移钩子或等新接口。【事实】
5. **OEM/中国生态在下游做"主动老化+分级回收"**：Honor memory.aging（2026-07 RFC，已在 GKI 模块出货）+ OpenHarmony ESWAP（per-memcg score/比例/refault 阈值，按账户状态调参）——说明"memcg 级 QoS 参数下发 + 主动回收"有真实出货先例，但均未上游。【事实】

**空白点（对我方最关键）：**
- **"会话级 memcg + 用户注意力 QoS"组合无直接先例**。最近邻：(a) systemd session scope 是会话级 memcg 但不感知注意力；(b) Jetsam use_probability 感知使用概率但是进程粒度且只用于查杀/aging；(c) AppFlow/MAPLE 用预测做预取而非供给契约，且 MAPLE 52% 命中率证明"预测驱动预载"成本风险高；(d) iOS secluded memory 是"前台专属内存池"的最接近工业先例——QoS 跟"是否前台"（注意力的粗粒度代理）而非进程身份，与方向一致但粒度粗、无 cgroup 契约语义。
- **交互场景内存供给保障研究稀缺**：服务端有 PARTIES 类交互 QoS 工作，移动端 2024-2026 检索未见"以 memory.min/low 做前台供给保障"的系统研究或工业实践；Android 17 MemoryLimiter 是"封顶"不是"保底"。【判断：检索 20+ 次未见，置信高】

---

## 4. 对我方的启发（逐条）

1. **统一记账底座（dmabuf 可见性）——支持**。上游 `memory.stat dmabuf`（6.5）+ 2026 charge_pid_fd RFC 证明方向正确且生态在演进；我方应直接复用上游键并跟踪 charge_pid_fd 进展，避免自造口径。风险：RFC 未合入，"代分配归账"短期只能靠 binder 转移钩子。[^dmabuf-v2^][^dmabuf-rfc26^]
2. **会话级 memcg——支持**。systemd session scope 是 15 年惯例，2026 年 agent 会话内存封顶已有真实工程落地（tmuxctl/PocketShell），粒度合理、心智成熟；Android 侧 per-app memcg 已被 lmkd 用于统计，说明移动端挂 memcg 的成本可接受。[^pocketshell^][^lmkd-src^]
3. **扩展 PSI——支持但需上游策略**。PSI trigger（阈值+窗口+poll）是事实标准；PSI_IRQ（6.1）证明上游接受新维度；建议我方扩展以"可复用 trigger 语义"为主，避免分叉 PSI 核心（openEuler 的 pressure.stat 细粒度停在下游是前车之鉴）。[^psi-irq^][^psi-fine^]
4. **冷热判别——支持，且不必自研底层**。MGLRU 的 min_ttl_ms 防抖、refault/eviction PID 控制器已提供高质量冷热信号；Honor memory.aging 证明"memcg 级主动老化"有收益。我方冷热判别应建在 MGLRU 统计 + refault 之上，把研发预算留给策略域。[^mglru-lwn26^][^mem-aging^]
5. **QoS 跟用户注意力而非进程身份——支持，属差异化空白**。证据链：iOS secluded memory（前台专属池）、Jetsam use_probability/aging、App Standby Buckets 都只走了一半；学术界预测式预载（FALCON/TPP/DeepAPP/MAPLE/AppFlow）证明"注意力预测"可行但误预测贵（MAPLE 52%）。建议我方：注意力信号以"确定性事件（前台/可见/交互中）"为主、"概率预测"为辅，供给契约用 memory.low（软保）而非 memory.min（硬保）以保留极端回收弹性——与 Facebook resctl 的 workload/hostcritical 分工一致。[^jetsam-src^][^resctl^][^appflow^]
6. **交互-后台双契约（memory.min/low）——支持，移动端为首创**。服务端与 K8s（Guaranteed 用 memory.low=request）已验证语义；移动端无 Android 先例，属我方差异化点；注意 memory.min 在"全局无内存可回"时会卡死分配路径（上游文档明示），前台契约应优先 memory.low。[^oci-case^][^resctl^]
7. **双策略域驱逐路径互通——支持，有相邻先例**。ChromeOS VMMMS 在 ChromeOS↔ARCVM 间用 balloon+压力信号做跨域仲裁（tab discards -50%），是"双域驱逐互通"的最接近工业证据；zswap 的 per-cgroup writeback 开关提供跨域"软驱逐"旋钮。[^chromeos-vm^][^zswap-chris^]
8. **需要修订**：不要把"驱逐"作为主要供给手段——Android 2026 趋势（MemoryLimiter）和 ESWAP/Hyperhold/超空间内存都表明行业正从"杀"转向"压缩+上限+主动回收"；我方宣传口径与默认策略应把 LMKD 式查杀降级为兜底。[^a17-memlimit^][^hos7^]
9. **挑战**：Android 17 MemoryLimiter 超限"静默终止无日志"已被开发者诟病；我方若做会话级硬上限，必须配套退出原因上报（参考其 `MemoryLimiter:AnonSwap` 描述与 Play vitals 4% 阈值机制），否则生态阻力大。[^a17-censuus^][^a17-stora^]
10. **挑战**：模型内存域接入记账底座时，dmabuf 是 GPU/NPU buffer 的天然口径，但"KV cache/权重驻留"多为 anon/shmem，不在 dmabuf 键内——记账底座需同时覆盖 anon+zRAM 压缩态（ESWAP 的 stat 扩展：Anon/File/zram/Eswap 分项是可借鉴格式）。[^eswap-doc^]

---

## 5. 证据清单

| # | Claim | Source | URL | Date | Excerpt（关键原文） | Confidence |
|---|---|---|---|---|---|---|
| 1 | LMKD 默认用 PSI monitor，三级阈值，ro.lmk.use_psi=true | AOSP 文档转载/源码解析 | https://www.leovp.com/2019/12/05/2019-12-05-Low-Memory-Killer-Daemon-lmkd/ | 2023-02（内容对应 Android 10+） | "ro.lmk.use_psi … Default true … PSI 设置为 lmkd 的默认内存压力检测机制" | 高 |
| 2 | lmkd PSI 默认阈值 SOME 70/100ms、FULL 70ms/1s；psi_complete_stall_ms 默认 700；thrashing_limit 100/30 | CSDN lmkd 源码+属性表 | https://blog.csdn.net/weixin_40214774/article/details/141687953 | 2025-07-17 | "static struct psi_threshold psi_thresholds[] = {{PSI_SOME,70},{PSI_SOME,100},{PSI_FULL,70}}" | 高 |
| 3 | lmkd 新策略（zone 水位+free swap+thrashing）在 cgroup v2/低 RAM 默认启用 | 掘金源码解析 | https://juejin.cn/post/7633644966019350580 | 2026-04-28 | "use_new_strategy = low_ram_device \|\| !use_minfree_levels … Old kill strategy can only be used with v1 cgroup" | 高 |
| 4 | Android 14 全系内核默认开 MGLRU；Pixel 8 首发；Pixel 6 数据：启动 -6.6%、杀后台 -8.04%、kswapd CPU -54.5%、直接回收 -81.1% | IT之家/同花顺转 Mishaal Rahman + 2022 LPC | https://xinsanban.10jqka.com.cn/20231018/c651361225.shtml | 2023-10-18 | "MGLRU 默认为所有 Android 14 内核启用 … App 总体启动时间减少约 6.60% … kswapd CPU 使用减少 54.50%" | 高 |
| 5 | MGLRU 部署汇总：Android 低内存查杀 -85%、ChromeOS 渲染延迟 -18%、冷启动 -16%、服务器 kswapd CPU -40%；Google 生产替代 kstaled CPU 1/5 | LPC 2024 slides | https://lpc.events/event/18/contributions/1781/attachments/1592/3304/mglru-updates-lpc2024.pdf | 2024-09 | "Low-memory kills 85% decrease (Android phones) … Enabled by default … Android, ChromeOS" | 高 |
| 6 | MGLRU 现存问题：cgroup OOM（writeback 落后）、缺全局 writeback throttling；TTL 防抖有效 | LWN（LSFMM 2026） | https://lwn.net/Articles/1072866/ | 2026-05-20 | "Its time-to-live (TTL) heuristic helps to prevent thrashing … writeback throttling for control groups … is being fixed now" | 高 |
| 7 | min_ttl_ms memcg 尊重修复（kswapd 100% CPU），stable 6.6.8 | openEuler 移植上游 commit | https://mailweb.openeuler.org/archives/list/kernel@openeuler.org/message/ALSM2ZRRUJ5VOIBDFEWWP5HVD4W7CNOM/ | 2024-01-02 | "memcg LRU can breach the thrashing protection imposed by min_ttl_ms" | 高 |
| 8 | Android 15=GKI 6.6 且 MGLRU 默认；Android 17 内核 android17-6.18（6.18.21）开 MGLRU/sched_ext | 内核构建说明/性能 wiki | https://wiki.androidperformance.com/part4-system/ch18-aosp/03-android17-kernel-arm64-security.html | 2026 | "android17-6.18-2026-06_r6, Linux 6.18.21 … GKI 配置开启 sched_ext、AutoFDO 与 MGLRU" | 中高 |
| 9 | dmabuf memcg 记账系列（memory.stat dmabuf + binder 转移），解决 Android 中心化分配记账问题 | Linaro mm-sig/LSM 列表（v1 2023-01-09, v2 2023-01-23） | https://lists-ec2.96boards.org/archives/list/linaro-mm-sig@lists.linaro.org/thread/JE2IB3273UCECPMEZUNGYJW33OITHA3U/ | 2023-01-09 | "adds a memory.stat counter for exported dmabufs … the charge to 'stick' to the allocating process/cgroup"（上游合入版本 6.5 为调研者知识，置信中高） | 高（系列）/中高（版本） |
| 10 | 2026-05 dmabuf charge_pid_fd RFC（Red Hat）：分配时显式归账到目标 cgroup，未合入 | dri-devel/kernsec 列表 | https://lists.freedesktop.org/archives/dri-devel/2026-May/566521.html | 2026-05 | "tests for the new charge_pid_fd field in struct dma_heap_allocation_data … asserts that memory.stat dmabuf in the child's cgroup reflects the allocation" | 高 |
| 11 | Honor memory.aging RFC v2：per-cgroup MGLRU 主动老化，GKI 模块在 6.6/6.12/6.18 出货，未上游 | patchew（LKML 镜像） | https://patchew.org/linux/0a218053083e41c8bc7aacc552c7f38c@honor.com/ | 2026-07 | "We ship it as a GKI module across kernels 6.6, 6.12 and 6.18 (Qcom and MTK), with stable gains on both Android and server workloads" | 高 |
| 12 | zswap 6.8+ per-cgroup memory.zswap.writeback=0 防 LRU 反转；6.18 zswap 改 zsmalloc | Chris Down 博客 | https://chrisdown.name/2026/03/24/zswap-vs-zram-when-to-use-what.html | 2026-03-24 | "kernel now supports a per-cgroup writeback disabled mode (kernel 6.8+) … cycles back to the active list rather than going to disk" | 高 |
| 13 | Android 12+ ZramWriteback（idle 标记+周期回写）在 Android 16 仍现役 | 源码级解析（Android 16） | https://www.wsisp.com/helps/100651.html | 2026-09-04 | "Android 16 源码 … ZramWriteback.java … MARK_IDLE_JOB_ID / WRITEBACK_IDLE_JOB_ID" | 中高 |
| 14 | zRAM 档位与 swap_compression_ratio 校准实践 | Android 性能书章节 | https://blog.csdn.net/dengfuma/article/details/163571166 | 2026-08-28 | "低内存 Go 版设备 1-2GB: zRAM 50% LZ4 … 16GB 以上 25-50% ZSTD" | 中 |
| 15 | OpenHarmony ESWAP：zswapd 加密换出、per-memcg score/压缩比/换出比/refault 阈值、按账户状态调参 | OpenHarmony 官方文档 | https://github.com/openharmony/docs/blob/master/zh-cn/device-dev/kernel/kernel-standard-mm-eswap.md | 文档持续更新（特性 2022-04 发布） | "memcg score: 300; ub_mem2zram_ratio: 60; ub_zram2ufs_ratio: 10; refault_threshold: 50" | 高 |
| 16 | HarmonyOS Hyperhold：生命周期分级回收，后台保持率领先 Android 50% | 华为 HDC 2021 PPT | https://www.harmonyos.com/resource/ppt/activity/sub-forum2/2021HDC-HarmonyOS-2-5.pdf | 2021 | "HarmonyOS 相比 AndroidOS 后台应用保持率领先 50%" | 中高（官方口径） |
| 17 | HarmonyOS 7 超空间内存：16GB +3GB 等效、60+ 机型；媒体称压缩率 65%+、保活 +42% | IT之家/搜狐 | https://www.ithome.com/1/016/755.htm ; https://m.sohu.com/a/1091365901_122066679 | 2026-10-22 | "16GB 运行内存最多增加 3GB，可以保活的应用更多"（65%/42% 为媒体口径） | 高（官方部分）/中（媒体部分） |
| 18 | Jetsam 优先级带 rev2（0..210，FOREGROUND=100、FREEZER=75、AGING_BAND、ELEVATED_INACTIVE）、use_probability 字段 | XNU 源码（Woboq/Apple） | https://fergofrog.com/code/codebrowser/xnu/bsd/sys/kern_memorystatus.h.html | xnu-12377（≈2024 代际） | "#define JETSAM_PRIORITY_FOREGROUND 100 … memorystatus_properties_entry_v1 { int use_probability; … }" | 高 |
| 19 | Jetsam relaunch flags 决定 aging band 停留（10/5/2s 缩放）；JLD 激进回收；CONFIG_SECLUDED_MEMORY 给 ≥FOREGROUND 进程隔离内存 | XNU 源码+中文解析 | https://blog.wyan.vip/2023/10/iOS_Jetsam.html ; https://fergofrog.com/code/codebrowser/xnu/bsd/kern/kern_memorystatus.c.html | 2023-10 / 2024-06 | "高重启概率的守护进程在 aging band 中获得 10 秒，中等 5 秒，低 2 秒"；"task_set_can_use_secluded_mem(priority >= JETSAM_PRIORITY_FOREGROUND)" | 高 |
| 20 | iOS 15+ Increased Memory Limit entitlement（提高 resident 上限、放宽 jetsam 阈值） | zenn.dev 整理 Apple 文档 | https://zenn.dev/mtfum/articles/ios_memory_entitlements | 2026-06-18 | "com.apple.developer.kernel.increased-memory-limit … Available on iOS 15.0 and later" | 高 |
| 21 | App Standby Buckets 按使用行为分 5 桶、限制 job/alarm/网络；Android 13 restricted 触发 45→8 天；**不管内存供给** | Android 官方文档 | https://developer.android.google.cn/topic/performance/appstandby | 2025-07-18（页面日期） | "each app is placed in one of five priority buckets. The system limits the device resources available to each app" | 高 |
| 22 | systemd-oomd：PSI per-cgroup + 持续时长杀整组；延迟敏感单元建议更低阈值（40% vs 60%） | systemd 官方 man | https://manpages.debian.org/testing/systemd-oomd/systemd-oomd.service.8.en.html | 2026-07-23 | "user@$UID.service may prefer a much lower value like 40%" | 高 |
| 23 | Facebook resctl 三层契约：workload memory.low / hostcritical memory.min 768MB / sideload memory.high | Meta resctl-demo 文档 | https://facebookmicrosites.github.io/resctl-demo-website/docs/demo_docs/res_protection/cgroup/ | 持续维护 | "workload.slice: memory.low … hostcritical.slice: memory.min … 768MB is always available" | 高 |
| 24 | cgroup v2 memory.min/low 语义与风险（min 卡死分配路径）；K8s Guaranteed 用 memory.low=request | OCI issue/cgroup2 文档 | https://github.com/opencontainers/runtime-spec/issues/1005 ; https://facebookmicrosites.github.io/cgroup2/docs/memory-controller.html | 2019 / 持续 | "memory.min … memory that can never be reclaimed … If the cgroup's memory usage reaches this low limit and can't be increased, the system OOM killer will be invoked" | 高 |
| 25 | 会话级 memcg 先例：systemd session-N.scope；2026 真实工程给每 agent 会话包 memory-capped scope | GitHub issue（PocketShell/tmuxctl） | https://github.com/alexeygrigorev/pocketshell/issues/726 | 2026-06-12 | "memory-capped tmux sessions … cgroup v2 systemd --user scopes under robust.slice … slice ≈46G, per-session ≈10G" | 高 |
| 26 | ChromeOS VMMMS：双 OS 内存仲裁，tab discards -50%、省电 15-20%、省 750MB | ChromeOS 官方博客 | https://chromeos.dev/en/posts/improving-performance-with-new-arc-resource-management-features | 2024-07-12 | "50% reduction in Chrome tab discards without triggering ARC++ app kills … save around 750 MB of memory" | 高 |
| 27 | PSI_IRQ 上游（6.1）；openEuler 下游 PSI 细粒度（pressure.stat、reclaim stall 细分） | tip 提交/openEuler 列表 | https://patchew.org/linux/166273201263.401.14957314590742548008.tip-bot2@tip-bot2/ ; https://mailweb.openeuler.org/hyperkitty/list/kernel@openeuler.org/message/T2VB62PUJXABLQ725WPN7U2TPE6FUXTD/ | 2022-09 / 2023-11 | "sched/psi: Add PSI_IRQ to track IRQ/SOFTIRQ pressure"；"PSI: Introduce fine grained stall time collect for cgroup reclaim" | 高 |
| 28 | Android 17 MemoryLimiter：按 RAM 设每应用硬上限，超限终止、默认静默、MemoryLimiter:AnonSwap、Play vitals 4% | 开发者博客（引官方文档） | https://censuus.com/blog/for-developers/android-17-behavior-changes-target-sdk-37 ; https://stora.sh/blog/2026-04-25-android-17-memory-limits-guide | 2026-10-01 / 2026-04-25 | "Per-app limits by device RAM; over the limit means zRAM, then termination"；"process terminates without logging … 'MemoryLimiter:AnonSwap'" | 中高（官方文档存在，二级转述） |
| 29 | 预测式预载研究链与代价：FALCON -50%/2% 能耗；TPP -52.5%/1.31MB；DeepAPP -68%/190MB；MAPLE 命中率 52%；AppFlow：97.2% 可预测、79% I/O 空闲、预载 100MB 可被回收 | MobiSys12/DATE23/SenSys19/arXiv 2603.17259 | https://people.cs.umass.edu/~dganesan/papers/MobiSys12-Falcon.pdf ; https://arxiv.org/html/2603.17259v1 | 2012 / 2023 / 2019 / 2026-03-18 | "MAPLE … its 52% hit rate means every miss wastes hundreds of megabytes"；"preloading is capped at 100 MB … these pages are reclaimed under pressure" | 高 |
| 30 | PSI 在移动端实测形态：avg10/60/300 + trigger（150ms/1s 例） | Qualcomm LPC 2023 slides | https://lpc.events/event/17/contributions/1433/attachments/1313/2638/Dynamic%20DDR%20Memory%20Offlining%20-%20LPC%202023.pdf | 2023-09 | "cat /proc/pressure/memory some avg10=70.24 … echo ~some 150000 1000000 > /proc/pressure/memory" | 高 |
| 31 | Pixel 实测 lmkd 属性：psi_complete_stall_ms=150、kill_timeout_ms=100、swap_util_max=90 等 | 期刊 PDF（含 adb 实测） | https://iaeme.com/MasterAdmin/Journal_uploads/IJITMIS/VOLUME_16_ISSUE_2/IJITMIS_16_02_014.pdf | 未标注（≈2025） | "[ro.lmk.psi_complete_stall_ms]: [150] … [ro.lmk.thrashing_limit]: [30]" | 中 |

[^lmkd-doc^]: Android lmkd/PSI 综述, https://www.leovp.com/2019/12/05/2019-12-05-Low-Memory-Killer-Daemon-lmkd/ (2023-02-02)
[^lmkd-arch^]: Android LMKD 服务深度解析, https://juejin.cn/post/7633644966019350580 (2026-04-28)
[^lmkd-psi^]: lmkd PSI 源码解析, https://blog.csdn.net/su749520/article/details/148544216 (2025-06-09)
[^lmkd-props^]: lmkd/psi/oomadj 属性总结, https://blog.csdn.net/weixin_40214774/article/details/141687953 (2025-07-17)
[^lmkd-src^]: Android 高版本 LMKD 源码解析, https://juejin.cn/post/7677254638325694474 (2026-08-24)
[^mglru-android14^]: Android 14 默认启用 MGLRU, https://xinsanban.10jqka.com.cn/20231018/c651361225.shtml (2023-10-18)
[^mglru-lpc24^]: MGLRU Updates, LPC 2024, https://lpc.events/event/18/contributions/1781/attachments/1592/3304/mglru-updates-lpc2024.pdf (2024-09)
[^mglru-lwn26^]: What is to be done about MGLRU?, LWN, https://lwn.net/Articles/1072866/ (2026-05-20)
[^mglru-ttl^]: mm/mglru: respect min_ttl_ms with memcgs, https://mailweb.openeuler.org/archives/list/kernel@openeuler.org/message/ALSM2ZRRUJ5VOIBDFEWWP5HVD4W7CNOM/ (2024-01-02)
[^gki-tree^]: Android 17 Kernel 6.18, https://wiki.androidperformance.com/part4-system/ch18-aosp/03-android17-kernel-arm64-security.html (2026)
[^a17-kernel^]: 同上 [^gki-tree^]
[^a17-memlimit^]: Android 17 适配指南（API 37 内存限制器）, https://blog.csdn.net/picture_share/article/details/162804559 (2026-07-12)
[^a17-censuus^]: Android 17 behavior changes checklist, https://censuus.com/blog/for-developers/android-17-behavior-changes-target-sdk-37 (2026-10-01)
[^a17-stora^]: Android 17 app memory limits explained, https://stora.sh/blog/2026-04-25-android-17-memory-limits-guide (2026-04-25)
[^zram-tune^]: Android 内存管理（zRAM 档位）, https://blog.csdn.net/dengfuma/article/details/163571166 (2026-08-28)
[^lmk-ctrl^]: LMK-Controller module, https://github.com/ferrdishx/LMK-Controller (2026-04-04)
[^zram-wb^]: ZRAM 回写机制源码级解析（Android 16）, https://www.wsisp.com/helps/100651.html (2026-09-04)
[^zswap-chris^]: Debunking zswap and zram myths, Chris Down, https://chrisdown.name/2026/03/24/zswap-vs-zram-when-to-use-what.html (2026-03-24)
[^eswap^]: OpenHarmony ESWAP 方案解析, https://juejin.cn/post/7395018314564157491 (2024-07-24)
[^eswap-doc^]: OpenHarmony Enhanced SWAP 特性介绍（官方文档）, https://github.com/openharmony/docs/blob/master/zh-cn/device-dev/kernel/kernel-standard-mm-eswap.md
[^hyperhold^]: HarmonyOS 内核核心技术解密（HDC 2021 PPT）, https://www.harmonyos.com/resource/ppt/activity/sub-forum2/2021HDC-HarmonyOS-2-5.pdf (2021)
[^hos7^]: 华为详解 HarmonyOS 7 超空间内存, https://www.ithome.com/1/016/755.htm (2026-10-22)
[^hos7-2^]: 方舟引擎新突破（媒体深度稿）, https://m.sohu.com/a/1091365901_122066679 (2026-10-22)
[^psi-qualcomm^]: Dynamic DDR Memory Offlining, LPC 2023 (PSI 章节), https://lpc.events/event/17/contributions/1433/attachments/1313/2638/Dynamic%20DDR%20Memory%20Offlining%20-%20LPC%202023.pdf (2023-09)
[^psi-irq^]: sched/psi: Add PSI_IRQ, https://patchew.org/linux/166273201263.401.14957314590742548008.tip-bot2@tip-bot2/ (2022-09-09)
[^psi-fine^]: openEuler PSI fine grained 系列, https://mailweb.openeuler.org/hyperkitty/list/kernel@openeuler.org/message/T2VB62PUJXABLQ725WPN7U2TPE6FUXTD/ (2023-11-27)
[^dmabuf-v1^]: [PATCH 0/4] Track exported dma-buffers with memcg, https://lists-ec2.96boards.org/archives/list/linaro-mm-sig@lists.linaro.org/thread/JE2IB3273UCECPMEZUNGYJW33OITHA3U/ (2023-01-09)
[^dmabuf-v2^]: [PATCH v2 0/4] Track exported dma-buffers with memcg, https://kernsec.org/pipermail/linux-security-module-archive/2023-January/036097.html (2023-01-23)
[^dmabuf-rfc26^]: [PATCH RFC 5/5] dmabuf-heaps memcg accounting tests (charge_pid_fd), https://lists.freedesktop.org/archives/dri-devel/2026-May/566521.html (2026-05)
[^mem-aging^]: [RFC v2 0/3] mm/mglru: proactive aging via memory.aging 讨论, https://patchew.org/linux/0a218053083e41c8bc7aacc552c7f38c@honor.com/ (2026-07)
[^moxii^]: Mac OS X and iOS Internals (MOXiI), https://www.newosxbook.com/MOXiI.pdf
[^jetsam-hdr^]: XNU kern_memorystatus.h, https://fergofrog.com/code/codebrowser/xnu/bsd/sys/kern_memorystatus.h.html
[^jetsam-src^]: XNU kern_memorystatus.c, https://fergofrog.com/code/codebrowser/xnu/bsd/kern/kern_memorystatus.c.html (2024-06-06 快照)
[^jetsam-useprob^]: 同 [^jetsam-hdr^]（use_probability 字段）
[^jetsam-relaunch^]: iOS Jetsam 机制解析, https://blog.wyan.vip/2023/10/iOS_Jetsam.html (2023-10)
[^macos-jetsam^]: macOS Memory Management notes, https://locara.dev/docs/notes/macos-memory-management (2025-07-15)
[^ios-ent^]: iOS memory entitlements, https://zenn.dev/mtfum/articles/ios_memory_entitlements (2026-06-18)
[^standby^]: App Standby Buckets（Android 官方）, https://developer.android.google.cn/topic/performance/appstandby (2025-07-18)
[^oomd-man^]: systemd-oomd.service(8), https://manpages.debian.org/testing/systemd-oomd/systemd-oomd.service.8.en.html (2026-07-23)
[^resctl^]: Facebook Resource Control Demo, https://facebookmicrosites.github.io/resctl-demo-website/docs/demo_docs/res_protection/cgroup/
[^oci-case^]: cgroupv2 memory controller case study, https://github.com/opencontainers/runtime-spec/issues/1005 (2019-03-08)
[^pocketshell^]: PocketShell issue #726（agent 会话内存封顶）, https://github.com/alexeygrigorev/pocketshell/issues/726 (2026-06-12)
[^chromeos-vm^]: Improving performance with new ARC++ resource management features, https://chromeos.dev/en/posts/improving-performance-with-new-arc-resource-management-features (2024-07-12)
[^falcon^]: FALCON (MobiSys 2012), https://people.cs.umass.edu/~dganesan/papers/MobiSys12-Falcon.pdf
[^tpp^]: Two-Phase Prefetching (DATE 2023), https://past.date-conference.com/proceedings-archive/2023/DATA/621.pdf
[^deepapp^]: DeepAPP (SenSys 2019), https://sites.ucmerced.edu/files/wdu/files/2019sensys-deepapp.pdf
[^appflow^]: AppFlow (arXiv 2603.17259), https://arxiv.org/html/2603.17259v1 (2026-03-18)
[^pixel-props^]: IJITMIS 论文中 Pixel lmkd 属性实测, https://iaeme.com/MasterAdmin/Journal_uploads/IJITMIS/VOLUME_16_ISSUE_2/IJITMIS_16_02_014.pdf

# Kimi 对照差异：C4 内存管理
> 对照日期 2026-11-05；核验方式：WebFetch 10 次 / WebSearch 0 次（额度用完即停）。总评：Kimi 在 C4 的强项是服务端 QoS 先例（resctl、systemd scope）、MoE 预测命中率链、预测信号分层（AppFlow/MAPLE）和 OEM 下游出货事实（Honor memory.aging、OpenHarmony ESWAP）；短板是 dim10 把 dma-buf memcg 误写成「6.5 已合入」、对 Android 17 Memory Limiter 的口径是二手博客转述，以及多处数字出自线索级列表或媒体。设计文档（《AgentOS 内存管理设计》）的 dmabuf 相关表述与已核实事实冲突，见 B1、B2。
> 核验标记：「已核」= 我方本轮抓到一手页面；「Kimi 已核」= 仅 Kimi 交叉验证文件（agentos_cross_verification.md）声称核过，我方未复核；「未核实（Kimi 单源）」= 额度内未抓到或页面不含该论断。

## A 可借鉴新增

| # | 条目 | 关键数据 / 事实 | 来源 | 核验 | 建议落点 |
|---|---|---|---|---|---|
| A1 | recharge-on-behalf：共享模型服务代持内存的归账转移，应作为记账底座的显式原语 | 系统服务代持内存在「按进程限额 + 单一属主记账」下要么饿死服务、要么冤杀某个 App；dmabuf 记账有「单一属主」「fd 传递不改账」两个缺陷 | Kimi insight I-09；dim12 脚注 24（Christian König 评论称「单驱动孤岛」）；2026-05 RFC：lists.linaro.org / lore（kernsec 2026-May/057331） | RFC 0/5（2026-05-12，「no transfer step is needed」，未合入）已核；「单一属主」「fd 不改账」「v2 共 8 补丁含 XFER_CHARGE ioctl」未核实（Kimi 单源，抓到的 Linaro 页面是 0/5 而非 v2）；I-09 本身是 Kimi 的推断 | §6 J2、§5 MM-1′ |
| A2 | 预测信号分层：确定性事件可进契约，行为概率只配驱动可回收的预载 | AppFlow：24 个 App 冷启动 I/O 等待中 97.2% 涉及可预测静态数据；切换时 79% DRAM I/O 带宽空闲；MAPLE（LLM 预测下一个 App）命中率 52%，每次未命中浪费数百 MB；预载上限 100MB 且压力下可回收 | Kimi insight I-04；dim10 脚注 29；arXiv 2603.17259（2026-03-18） | 已核（arXiv HTML §2.2.1、§7.2、§6.5.3 原文均含上述数字） | §5 MM-3′、Q5 |
| A3 | Honor memory.aging：把 MGLRU 主动老化暴露为 per-cgroup 接口，已作为 GKI 模块出货 | 2026-07 RFC v2；6.6/6.12/6.18（Qualcomm 与 MTK）出货，未上游 | dim10 证据 11；patchew 0a218053083e41c8bc7aacc552c7f38c@honor.com | 未核实（Kimi 单源，未抓取） | §3 Q1 MGLRU 段 |
| A4 | zswap per-cgroup writeback 开关 | `memory.zswap.writeback` 默认 1；写 0 则禁止向 swap 设备回写，但页仍可进 zswap 池；层级继承；与 `memory.swap.max=0` 语义不同 | dim10 证据 12（Chris Down 2026-03-24）；docs.kernel.org cgroup-v2 | 已核（内核文档）；「6.8 引入」未在抓取页面中见到，版本号待核实 | §3 Q5 表后、§5 MM-7（会话 KV 状态的换出许可旋钮） |
| A5 | 服务端三层契约与 memory.min 的风险 | Facebook resctl：workload.slice 用 `memory.low`，hostcritical.slice 用 `memory.min`（768MB），sideload.slice 用 `memory.high`；memory.min 在全局无可回收内存时会触发 OOM，前台契约应优先 memory.low | dim10 证据 23、24；resctl-demo 文档；OCI runtime-spec issue #1005 | 未核实（Kimi 单源，未抓取） | §3 Q5 先例表、§5 MM-3′ |
| A6 | 「会话 = memcg」的工程先例：systemd scope 给 agent 会话加内存上限 | PocketShell 为 tmux 会话建 `systemd --user` scope，挂在 `robust.slice` 下，记 slice 约 46G | dim10 脚注 25；github.com/alexeygrigorev/pocketshell/issues/726（2026-06-12） | 已核，但 Kimi 的「每会话约 10G」已过时，维护者后来定为 30GiB（见 B6）；属服务器 / 桌面先例，不是手机 | §3 Q5 先例表 |
| A7 | QNN 只接受 DMA-BUF 形式的共享内存，因此「dma-buf export / heap alloc」是跨 CPU/GPU/NPU 的唯一挂点 | Snapdragon 8 Elite 上 CPU/GPU/DSP 通过 DMA-BUF fd（AHardwareBuffer 或 Hexagon heap）共享内存 | dim12 证据 28；arXiv 2610.16244（2026-09）；docs.qualcomm.com | 已核 arXiv 2610.16244 原文（"QNN accepts memory only in this form"）；docs.qualcomm.com 页面抓取为空 | §3 Q6 |
| A8 | 重算与换出的硬件成本模型；vLLM V1 默认抢占策略为 RECOMPUTE | Stream2LLM 用「硬件特定成本模型」指导抢占策略；dim11 称其为分段线性模型，同一重算 H100 约 50ms、A40 约 200ms；V1 已移除 GPU↔CPU swap | dim11 脚注 32、50；arXiv 2604.16395 | 论文存在、摘要含 "hardware-specific cost models" 已核；分段线性与 50ms/200ms 未核实（Kimi 单源）；V1 默认 RECOMPUTE 未抓取 | §3 Q7 |
| A9 | 有损驱逐的失效数据（补强 SCBench） | NVIDIA 官方博客（2026-06）：2048-token 预算下 AIME 2024 全注意力 57.1%、SnapKV 34.6%、R-KV 25.4%；H2O 在 needle 类任务 20% 预算下降 30–40% | dim11 脚注 20、15 | 未核实（Kimi 单源；脚注 URL 未在抓取额度内取到） | §3 Q2 压缩与驱逐段 |
| A10 | KV 编码解压与推理在 GPU 上互相干扰 | arXiv 2509.16857：解压与推理并存时双向减速，无法同时压到 30% 以下 | dim11 脚注 47 | 未核实（Kimi 单源） | §7.3 上云行「端侧缺口」列 |
| A11 | MoE 预测命中率链：补全 §7.2 中多行「未核实」 | Fate 免训练跨层预取 78.79%（浅层全缓存后专家命中 99.08%）；ProMoE 学习式 84.7%，token-based 仅 58.3%；同层 pre-attention 93.03–97.62%；相邻层输入余弦相似度 91.7% | dim12 证据 7、9、10、11；arXiv 2502.12224、2410.22134、2511.10676 | Kimi 已核（交叉验证文件称 arXiv 原文一致）；我方未复核；均为 GPU / 服务器结果 | §7.2 |
| A12 | WiSP：专家与 KV 合并为一个显存预算下的分配问题 | 单流 decode 下瓶颈是 PCIe 带宽而非预测质量；相对静态 offload 最高约 2.0× decode 吞吐 | dim12 证据 18；arXiv 2606.21868 | 已核摘要；Kimi 的「1.95× vs vLLM」不在摘要中（见 B7） | §3 Q3、§5 MM-5′ |
| A13 | NPUMoE：Apple ANE 上 MoE prefill 卸载 | 延迟降 1.32–5.55×，能效升 1.81–7.37×；离线校准专家容量做静态分层 | dim12 证据 19；arXiv 2604.18788 | Kimi 已核；我方未抓取；只覆盖 prefill | §7.2 |
| A14 | OpenHarmony ESWAP：per-memcg 的换出参数 | zswapd 把 zRAM 压缩页加密换出到 ESwap 分区；per-memcg 参数含 score、ub_mem2zram_ratio、ub_zram2ufs_ratio、refault_threshold；按账户状态调参 | dim10 证据 15；github.com/openharmony/docs …/kernel-standard-mm-eswap.md | 未核实（Kimi 单源）；注意这是 OpenHarmony 官方文档，不等于商用 HarmonyOS | §3 Q1 HarmonyOS 段、§3 Q8 zram 行 |
| A15 | iOS 前台专属内存池：Jetsam 使用概率与 secluded memory | xnu 源码：优先级 ≥ FOREGROUND 的进程可用 secluded 池；`use_probability`、relaunch 标志决定 aging band 停留时间 | dim10 证据 18、19（fergofrog 的 xnu 源码浏览器；wyan.vip） | 未核实（Kimi 单源）；是源码级事实，但版本为 2024 快照 | §3 Q1 iOS 段、§5 MM-3 |

建议插入文字：

**A1**：Android 17 的 Memory Limiter 按进程设 `memory.high`，而共享模型服务代多个客户端持有基座权重与会话 KV，内存要么全记给服务，要么记给某个 App。2026-05 的 dma-buf 记账 RFC 采用分配时按 pidfd 向客户端记账，作者称无需转移步骤，仍未合入 [A4]。Kimi 称后续版本暴露出「单一属主」「fd 传递不改账」两个限制（Kimi dim12 脚注 24，我方未核实）。判断：MM-1′ 的「共享服务代记」应命名为一条独立原语（代分配归账转移），在 dma-buf export 与 heap alloc 处挂钩；该原语不依赖上游合入。

**A2**：AppFlow（arXiv 2603.17259，2026-03）在 24 个 App 上测得 97.2% 的冷启动 I/O 等待涉及可预测的静态数据，切换时 79% 的 DRAM I/O 带宽空闲；基于 LLM 的下一个 App 预测（MAPLE）命中率只有 52%，每次未命中浪费数百 MB。判断：MM-3′ 的注意力信号应以确定性事件（前台、可见、用户正在等待）进入保护契约，行为预测只驱动可回收的投机预载。

**A4**：`memory.zswap.writeback` 默认为 1，写 0 后该 cgroup 的页只进 zswap 池、不向 swap 设备回写（内核 cgroup-v2 文档）。判断：它是比 `memory.swap.max=0` 更细的旋钮，可用于给会话状态单元划定「允许压缩、禁止落闪存」的档位，与 MM-7′ 的「写寿命、热状态允许才换出」直接对应。

**A7**：QNN 只接受 DMA-BUF 形式的共享内存（arXiv 2610.16244，2026-09）。判断：骁龙平台上 CPU、GPU、NPU 的共享缓冲都经过 dma-buf export，记账挂点集中；但 VTCM 等片上内存与驱动私有池不经过 dma-buf，仍需厂商 HAL 上报。

**A8**：Stream2LLM（arXiv 2604.16395）用硬件特定的成本模型选择抢占策略；Kimi 引 vLLM V1 已移除 GPU↔CPU swap、抢占默认重算（Kimi dim11 脚注 32，我方未核实）。判断：服务器 GPU 上「重算优于换出」与我方手机估算（换出快 7–40 倍）方向相反，差别来自 PCIe/NVLink 与 UFS 带宽、以及复用概率 p；§3 Q7 应写明结论只对手机成立，并把 p 和平台标定作为一等输入。

## B 冲突与更正

| # | 事实 | 我方写法（报告位置） | Kimi 写法（文件位置） | 一手来源裁决 | 正确口径 | 我方需改动 |
|---|---|---|---|---|---|---|
| B1 | dma-buf 可见性的上游状态 | sysfs 统计 2026-01 提议删除，Android 已迁 BPF iterator；memcg 计费只有 RFC（§3 Q1 表、§0 第 3 条） | 设计文档 §6.1：「dmabuf 可见性近年才由上游补丁补齐」；§5 第 1 条称「上游内核已有 dmabuf 记账工作流」 | 内核 cgroup-v2 文档的 memory.stat 键列表中没有 dmabuf（已核）；RFC 0/5 为 2026-05-12，未见合入迹象（已核）；Kimi 交叉验证 C2 同裁决 | 可见性由 sysfs（拟删）与 BPF iterator 提供，且是 Android 侧而非上游补丁补齐；memcg 记账未合入 | 无需改我方；主 Agent 回复设计文档作者时应指出此条 |
| B2 | dma-buf memcg 记账的合入状态与作用 | 2026-05 RFC，König 有异议；记账 ≠ 可回收（§3 Q8 表「dma-buf 可回收 ✗」） | 设计文档 §6.2：「上游补丁使 DMA 内存首次可被纳入统一回收」 | 同 B1；另外记账只给出归属，不使 dma-buf 页可回收 | 未合入；即使合入，也只解决「可归属」，「可回收」仍需 revoke 或迁移原语 | 无需改；建议在 §3 Q8 末尾点名设计文档此句不成立 |
| B3 | dma-buf memcg「6.5 合入（2023-08）」 | §8 A29 把 Mercier 2023 作为 v2 补丁引用，未称合入 | Kimi dim10 §1.3 表与证据 9：合入 6.5，`memory.stat` 增加 `dmabuf` 键 | Kimi 自己的交叉验证 C2 已证伪；内核文档无该键（已核） | 未合入；Android GKI 下游可能携带（Kimi 称，未核实） | 无 |
| B4 | Android 17 Memory Limiter 的超限动作 | `memory.high` 节流、压 zRAM，最后才杀（§0 第 1 条） | Kimi dim10 §1.1 表：「硬上限，超限终止」，「默认静默」 | AOSP 文档（已核）：超限主要触发节流与回收，仅在 swap 耗尽后继续增长等极端情形才终止；按进程、UID≥10000；文档未说 dma-buf/GPU 是否计入 | 我方口径正确；「硬上限」措辞不准。Kimi 口径来自 csdn/censuus/stora 等二手博客 | 无 |
| B5 | `memory.pressure_level` | 未提 | Kimi dim10：lmkd 新增该控制点 | AOSP 文档未提及（已核）；Kimi 交叉验证标 UNVERIFIED | 不存在证据 | 无（见 E） |
| B6 | PocketShell 每会话内存上限 | 未提 | Kimi dim10 证据 25：每会话约 10G | issue #726：维护者后改为 30GiB（已核）；slice 约 46G 为最初估算，后续是否变更页面未说 | 引用时只写「会话 scope 加上限」的做法，不写具体数 | 采纳 A6 时勿带 10G |
| B7 | WiSP 的加速比 | 未提 | Kimi dim12：1.95×，对比 vLLM 静态 offload | 摘要：对静态 offload 最高 2.0× decode 吞吐，未提 vLLM；另有 1.19× 对固定离线切分（已核） | 写「相对静态 offload 最高约 2.0×」 | 采纳 A12 时按此写 |
| B8 | 4B 模型 8K 上下文 KV 体积 | 约 1.18GB（144KiB/token，36 层 × 8 KV 头 × head_dim 128，fp16；配置取自记忆，§8 第 12 条待核实） | Kimi dim02（经交叉验证文件转述）：Qwen3-4B @8K FP16 约 2GB；dim10 另有「INT4 4K 约 470MB」 | 未抓取 Qwen3-4B 配置；Kimi 交叉验证称「单一整理源」。2GB 对应约 250KiB/token，与 8 个 KV 头的 GQA 不符，更像按 MHA 或更多 KV 头算 | 仍以我方公式为准，配置核实前保持「估算」标注 | 不改正文；§8 第 12 条保持待核实 |

## C 可消解的待核实

| 我方待核实条目 | 新证据 | 结论 |
|---|---|---|
| 1. 设计文档对「扩展 PSI」「会话级 memcg」的定义 | 设计文档全文已读。§5 第 2 条：「PSI 扩展模型内存维度——NPU 侧分配压力驱动传统侧回收，反之亦然」；§7 M1 写作「PSI 扩展 DMA 压力维度」；§3.1：以会话为主体「建立 memcg 层级」 | 坐实定义，但与我方建议不一致，见 D-0 |
| 2. Memory Limiter：dma-buf/GPU 是否计入；按 UID 还是 PID | AOSP 文档（已核）：未说明 dma-buf/GPU 是否计入；按进程执行，对象为 UID≥10000 的应用进程，手动覆盖按 PID，`ignore` 命令按 UID 或全体 | 部分坐实：粒度是进程；dma-buf/GPU 口径仍待核实（官方文档沉默） |
| 3a. dmem 控制器首个合入版本 | kernelnewbies Linux 6.14（已核）：特性列表含 "dmem" memory accounting cgroup；6.14 于 2025-03-24 发布 | 坐实：6.14。「6.14 周期（待核实）」可去掉括号 |
| 3b. dma-buf sysfs 统计删除补丁合入版本 | 无新证据 | 仍待核实 |
| 3c. `MEMCG_DMABUF` RFC 后续版本 | Kimi dim12 称 2026-10 有 RFC v2（8 补丁，含 `DMA_BUF_IOCTL_XFER_CHARGE`、SELinux 限制）；我方抓到的 Linaro 页面是 2026-05 的 0/5，未见 v2 | 仍待核实（Kimi 单源）；可在 §8 记「Kimi 称有 v2」 |
| 4. MGLRU 在 GKI 分支默认开启的版本 | Kimi dim10 证据 4、8：Android 14 全系内核默认开；15 为 GKI 6.6；17 为 android17-6.18；来源是 IT之家转述和 androidperformance wiki | 部分坐实（二手）；LSFMM 议题结论无新证据 |
| 6. ESwap 是否存在于 HarmonyOS | OpenHarmony 官方文档有 ESWAP（见 A14）；Kimi 另给 HarmonyOS 7「超空间内存」（2026-10-22，媒体口径） | OpenHarmony 部分坐实（未抓取）；商用 HarmonyOS 仍待核实 |
| 7. Qualcomm rpcmem / dma-buf 要求 | arXiv 2610.16244（已核）：QNN 只接受 DMA-BUF；MediaTek、ANE 无新证据 | 高通一项坐实（二手论文，非 Qualcomm 官方页）；其余仍待核实 |
| 12. Qwen3-4B 的 KV 配置 | 无新证据，见 B8 | 仍待核实 |
| 16. vLLM Sleep Mode 出处与成熟度 | Kimi dim11 脚注 44、45：L1 睡眠权重卸 CPU、丢 KV，唤醒约 2–3s；L2 权重也丢弃，约 7–8s；小模型实测唤醒 0.39s；支持按 tags 细粒度唤醒 | 未核实（Kimi 单源，未抓取），可先标「Kimi 称」 |
| 5、8、9、10、11、13、14、15、17 | 无新证据 | 仍待核实 |

## D 立场层面的调整

**D-0 设计文档「扩展 PSI」与我方 MM-1 建议是否一致：不一致，需要继续追问。**
- 设计文档给出的是方向，没有给出停顿信号：§5 第 2 条说「NPU 侧分配压力驱动传统侧回收，反之亦然」，M1 说「DMA 压力维度」，两处措辞不同（模型内存维度 / DMA 压力维度），也没有说明新增的是 `memory.pressure` 之外的新文件、新 trigger 类型，还是在 dma-buf 分配路径上计入既有 memstall。我方 MM-1 的修订要求「写出具体扩展哪些停顿信号，否则删去」，设计文档未满足。
- 机制缺口：PSI 度量的是任务因内存不足而停顿的时间。设备缓冲被持有时「只能杀持有者」（§3 Q8），所以「NPU 侧压力驱动传统侧回收」在传统侧有机制（回收 / LMKD），而「传统侧压力驱动 NPU 侧释放」缺少回收原语，「反之亦然」目前没有落点。
- Kimi 的补充（dim10 启发 3）：PSI trigger 语义（阈值 + 窗口 + poll）是事实标准，PSI_IRQ 在 6.1 进入主线说明上游接受新维度，但上游对新增维度保守，openEuler 的 pressure.stat 细粒度扩展停在下游；建议复用 trigger 语义、避免分叉 PSI 核心。该建议与我方「写清具体停顿信号」不冲突，可并入 MM-1′。PSI_IRQ 的 6.1 合入未抓取核验（Kimi 单源）。
- 建议修改 MM-1′ 一句：「『扩展 PSI』须列出新增的停顿信号（如模型加载停顿、NPU 等待、dma-buf 分配停顿），复用既有 trigger 语义，并说明反向（传统侧压力 → 设备侧释放）依赖的回收原语；设计文档 v0.1 只给出方向。」

**MM-1（统一记账底座）**：设计文档 §3.1 要「建立 memcg 层级」，我方原判是「做归属标签、不做新层级」以兼容 Android 17 的按进程限额。Kimi 的 systemd scope / PocketShell 先例（A6）只证明 Linux 服务器与桌面上会话级 scope 可行，不改变 Android 17 已按进程限额这一约束，因此不改判。可加一句：会话 scope 可作为 Linux 参考实现。同时 A1 使「共享服务代记」从 §6 的判断升为 MM-1′ 里的显式原语。

**MM-3（QoS 跟注意力）**：Kimi 的 I-04 与 resctl 先例（A2、A5）支持我方 MM-3′ 的「前台以外的信号」，并给出一条我方没写的规则：确定性事件进契约，行为预测不进。设计文档 §3.2 把交互类映射到 `memory.min` 级别的硬保证，Kimi 与 resctl 文档认为 memory.min 在无可回收内存时会拖垮分配路径，应优先 `memory.low`（A5，未核实）。建议 MM-3′ 加一句：「保护侧契约首选 `memory.low`；`memory.min` 仅用于极小的关键集。」

**MM-4 / MM-7（驱逐去向）**：Kimi dim11 §4.4 主张把摘要入库单列为「物化」去向（「3+1」），与我方 MM-7′（摘要入库是形态转换，第六档交记忆框架）一致；设计文档 §4.2 把它列为 KV 的第四种去向，与我方不一致，保留我方判断。Kimi 对「换出比重算划算」的反证（A8：服务器上 V1 默认重算）不推翻我方手机估算，但要求 Q7 明写适用范围。

**MM-5（MoE）**：Kimi 的命中率链（A11）支持 router 预告在 GPU 服务器上可行，但跨层免训练预取 decode 阶段只有 78.79%，且 WiSP（A12）指出单流 decode 瓶颈是带宽而非预测质量；这与我方「512MiB 时 LRU 命中 0%、需最小工作集保证」同向。设计文档 §4.3「驱逐与预取第一次可基于预告」对 batch=1 的手机偏乐观。不改「降优先级并泛化」的判断，可在 MM-5′ 加一句：预测只作为界定最小驻留集的内存信号，不单独承担延迟收益。

**MM-2、MM-6**：无新证据，不调整。

## E 不采纳

| 条目 | 原因 |
|---|---|
| dim10「dmabuf memcg 上游 6.5 合入」及 `memory.stat dmabuf` 键 | Kimi 交叉验证已证伪；内核文档无此键（已核） |
| dim10「lmkd 新增 memory.pressure_level」 | 交叉验证标 UNVERIFIED；AOSP 文档未提及（已核） |
| dim09「KV 每 token 0.5MB（Llama-3-8B）」 | 交叉验证标 MISQUOTED：0.5MB 对应 MHA 7B，GQA 的 Llama-3-8B 约 0.125MB |
| dim10 对 Memory Limiter「硬上限、超限终止、默认静默」的措辞 | 二手博客转述，与 AOSP 文档不符（B4） |
| Sereno（OSDI'26）decode 带宽争用 | 仅见于 awesome 列表，dim02 自标「线索，未逐篇核对」；不是 C4 主题，且无一手摘要 |
| HarmonyOS 7 超空间内存（+3GB、压缩率 65%+、保活 +42%） | 官宣部分只有「最多 +3GB」，其余是媒体口径；无技术文档 |
| CVE-2026-1104 NPU 多租户侧信道 | 交叉验证标 Low：仅 techbytes 媒体分析，无学术原文 |
| vChunk <1% 干扰（MIG 最高 40%） | emergentmind 二手综述 |
| ANE IOSurface pin 上限 8–12 buffer | 单一博客（mvpfactory），交叉验证标 Low；ANE 32MB SRAM 为单源逆向 |
| CacheGen 3.5–4.3× 压缩 | 我方 §2 已含（B13），非新增；仅其「解压干扰」一项采纳为 A10 |
| MGLRU Pixel 6 启动 -6.6% 等数字 | 交叉验证标 PARTIAL，来源链存在但未复核；不进正文，必要时标「Google LPC slides 口径」 |
| Mixtral-offloading「LRU 命中 70–85%」 | dim12 自注为第三方复现叙述，非论文原文；且为 GPU 场景 |
| 设计文档 §4.2 把摘要入库列为 KV 去向 | 与我方 MM-7′ 及 Kimi dim11 的「3+1」判断都不一致，保留我方 |
| 设计文档 §6.2 PowerInfer-2「热神经元驻留 NPU、冷神经元走 CPU」 | 与 Kimi dim11 的描述（NPU 密计算、CPU 稀疏计算）不符；我方未核原文，不采纳也不更正，留给主 Agent 核对 PowerInfer-2 论文 |

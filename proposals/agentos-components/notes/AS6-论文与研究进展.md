# AS6 论文与研究进展：安卓 Agent 沙箱的性能诉求与技术创新

> 日期：2026-11-15；抓取版本：见参考文献表（均为 arXiv 当前最新 vN）；检索实际用量：WebFetch 0 / WebSearch 2 / 源码与论文文件 15（arXiv export API 检索 8 次，html 全文 7 篇）。
> 证据标记：「论文·全文」= 已抓 html 全文并 grep 到原文；「论文·摘要」= 只读到 arXiv 摘要，正文数字未核；「二手」= 搜索结果摘要。
> 所有 arXiv 编号都来自实际返回的 API / 页面结果。

## 结论（≤6 条）

1. **环境重置与模拟器交互是在线 RL 的主瓶颈，且已有实测。** Android Coach（2604.07277）在 8 路并行环境、80 步训练上测得：模拟器交互（初始化、恢复、响应）耗时是模型加载与推理的 **1.7 倍**（论文·全文）。MobileRL（2509.18119）自述每个 AVD 需 **>5 GB 内存、>30 GB 存储**，4 台各 1 TB 内存的 CPU 机器只能稳定撑 **≤256 路并行**，每步 **>10 分钟**，训练 100 步 **>25 小时**（论文·全文）。
2. **工业界规模已到万级并发，但安卓这一支靠容器化或真机，而不是 KVM 模拟器。** Qwen-UI-Agent（2607.28227）：基础设施支持最多 **10,000** 并发沙箱 / rollout；并明确把 MobileWorld 环境「重建在 redroid 上」，理由是 KVM 模拟器有扩展瓶颈（论文·全文）。同时另有 **100+ 台真机、150+ 应用**的真机运行时，并用虚拟屏让一部手机同时跑多个 App。
3. **「真机优先」的论文正在增多，动因是反模拟器检测与风控，而非性能。** Xiaomi-GUI-0（2606.31410）以物理设备为主、沙箱为辅，理由是主流商业 App 普遍有反模拟器检测，账号态、权限弹窗、支付认证、风控无法在沙箱复现（论文·全文）。BlueLM-GUI（2609.12394）在「数百台真机」上做 agentic RL（论文·摘要）。
4. **DSec（DeepSeek，2609.22978）给出了最完整的生产级密度与启动数字，但安卓只是一句话。** 单节点最多 **800 个 microVM 或 3,200 个容器**（过量分配）；生产峰值 **>380,000 并发沙箱、>5,000 次/秒创建**；按需加载镜像相对 eager pull 完成时间快 **1.71 倍**；DAMON + balloon free-page reporting 降内存 **21.2%**。安卓只作为 full-VM 后端（QEMU）出现，**没有安卓专项数字**（论文·全文）。
5. **异步、解耦是共识解法，且有量化收益。** DistRL（2410.14803）：任务时长跨度可达 **100 倍**（秒到 >10 分钟），同步多机方案出现快者空等；异步后训练效率 **3 倍**、数据采集 **2.4 倍**（论文·全文）。Worker 用 Environment Snapshots 重置模拟器。
6. **手机本机侧几乎没有「Agent 沙箱性能」论文。** 本轮检索到的手机侧工作要么是安全架构（Aster、IsolateGPT）、要么是攻击面分析（2505.12981），没有给出「在手机上给 Agent 开隔离环境的启动 / 内存 / 功耗」数字。AVF 性能论文只在搜索结果里见到标题（二手），未打开。

## 1. AS6-Q1 论文清单

先给总表，再按类别写要点。

| # | 论文（编号，日期） | 机构 | 类别 | 等级 |
|---|---|---|---|---|
| P1 | DSec: DeepSeek Elastic Compute（2609.22978，2026-09-19） | DeepSeek-AI | 云侧 Agent 沙箱系统 | 论文·全文 |
| P2 | UI-TARS-2 技术报告（2509.02544，2025-09-02） | 字节 Seed | GUI Agent 训练环境 | 论文·全文 |
| P3 | Qwen-UI-Agent 技术报告（2607.28227，2026-07-30） | 阿里 Qwen | 容器化 + 真机混合环境 | 论文·全文 |
| P4 | MobileRL（2509.18119，2025-09-10） | 清华 / 智谱（THUDM） | 手机 GUI 在线 RL | 论文·全文 |
| P5 | DistRL（2410.14803，2024-10-18） | 作者机构待核实 | 异步分布式 RL | 论文·全文 |
| P6 | Android Coach（2604.07277，2026-04-08） | 浙大 / Qualcomm AI Research（据文中脚注） | 降低模拟器交互次数 | 论文·全文 |
| P7 | Xiaomi-GUI-0（2606.31410，2026-06-30） | 小米 | 真机为主的混合设施 | 论文·全文 |
| P8 | BlueLM-GUI（2609.12394，2026-09-11） | vivo（据 BlueLM 系列推断，待核实） | 真机 flywheel | 论文·摘要 |
| P9 | HyMobileAgent（2607.14548，2026-07-16） | 腾讯混元 Hy Vision Team | 数据与环境协同扩展 | 论文·摘要 |
| P10 | Mobile-Agent-v3 / GUI-Owl（2508.15144，2025-08-21） | 阿里通义 | 云端多 OS 虚拟环境 + 异步 RL | 论文·摘要 |
| P11 | PhoneWorld（2605.29486，2026-05-28） | 作者机构待核实 | 由真实轨迹生成可重置 mock 环境 | 论文·摘要 |
| P12 | OpenMobile-2（2610.14157，2026-10-09） | OS-Copilot 团队 | 模拟 App + GUI/工具混合 | 论文·摘要 |
| P13 | WM-R1（2608.27508，2026-08-27） | 待核实 | 世界模型代替真机 / 模拟器 | 论文·摘要 |
| P14 | ClawGUI（2604.11784，2026-04-13） | 待核实 | 训练、评测、部署一体框架，含真机 | 论文·摘要 |
| P15 | AgentRL（2510.04206，2025-10-05） | THUDM | 全异步生成-训练流水线、容器化环境 | 论文·摘要 |
| P16 | AutoDroid-V2（2412.18116，2024-12-24） | MobileLLM 团队 | 代码生成式 GUI 执行（端侧小模型） | 论文·摘要 |
| P17 | From Assistants to Adversaries（2505.12981，2025-05-19） | Liangxuan Wu 等 | 手机 Agent 安全分析 | 论文·摘要 |
| P18 | Aster: Fixing the Android TEE Ecosystem with Arm CCA（2407.16694，2024-07-23） | ETH 等（作者含 Mark Kuhne、Supraja Sridhara、Andrin Bertschi；机构待核实） | pKVM / CCA 隔离 | 论文·摘要；MobiSys'26 版本见搜索结果（二手） |
| P19 | IsolateGPT（2403.04960，2024-03-08；NDSS 2025） | Wu、Roesner、Kohno 等 | Agent 应用执行隔离 | 论文·摘要 + 搜索结果（二手） |

### 1.1 云侧与训练系统（P1–P7）

**P1 DSec（2609.22978）**

- **问题**：agentic 训练的沙箱成批突发创建，种类异质，需要有状态、长寿命，镜像语料大且复用率低。
- **方法**：
  - 统一 SDK 暴露 FnCall、容器、Firecracker microVM、full VM 四类后端；
  - 环境由独立版本化的只读 EROFS 层组合；镜像经 3FS 按需加载；
  - microVM 用 virtio-pmem + DAX 共享只读层，用 DAMON + virtio-balloon free-page reporting 回收；
  - 与 RL 框架协同：把 agent loop 与 RL 框架分离，支持挂起沙箱以便抢占式训练。
- **关键数字**（论文·全文）：
  - 单个生产单元约 160 节点，日均约 300 万沙箱；峰值 >380,000 并发，>5,000 次/秒创建；
  - 单节点最多 800 microVM 或 3,200 容器（依赖过量分配）；
  - 沙箱寿命中位数：容器 17.4 分钟、microVM 15.5 分钟，P99 均 >3 小时；
  - 8,192 容器突发（10 节点）：按需 EROFS 约 35 分钟完成，eager Docker pull >60 分钟，即 1.71 倍；累计磁盘写入约 700 GB，对比 eager >1,600 GB（降约 57%）；
  - EROFS 层挂载对比 tar 解压：45 分钟对 79 分钟（1.76 倍），磁盘写入流量约 5.5 倍；
  - 内存：DAMON + balloon free-page reporting 降低内存消耗 21.2%，CPU 开销不显著。
- **创新点**：层组合降低 O(m·N) 的镜像成本；按需加载；microVM 内存共享与回收；与训练框架共设计。
- **启示**：
  - 手机侧不会有「万级并发」，但「只读底座层 + 可写上层」「空闲页回收」「按需加载」思路可迁移到手机上的 Agent 沙箱，因为手机内存预算更紧。
  - 注意：Android 在 DSec 里是 **QEMU full-VM 后端**，论文原文只有一句话，没有启动时间、内存、密度数字，也没有 redroid 方案。

**P2 UI-TARS-2（2509.02544）**

- **环境**：自建分布式 VM 平台，运行 Windows、Ubuntu 和 Android，集成 PyAutoGUI 与 ADB；统一 SDK 覆盖 VM 分配、初始化、交互、观测（截图和录屏）、评测。
- **数字**（论文·全文）：VM 集群**数千实例**；VM Manager 可承载**数千 QPS**；会话由 session ID 绑定任务与环境；VNC / RTC 实时可视化；租约（lease）机制回收完成、失败和超时的会话。
- **RL 基础设施**：服务器式异步 rollout、带有状态的环境、streaming 训练配合部分填充的 rollout 池，用以缓解长尾。
- **未披露**：安卓实例的具体形态（模拟器、容器还是云手机）、重置时间、单步时延。摘要与 grep 范围内没有找到，标「待核实」。
- **启示**：租约式生命周期、会话 ID 路由，是任何 Agent 沙箱管理层的最小集。

**P3 Qwen-UI-Agent（2607.28227）**

- **环境**（论文·全文）：
  - 沙箱支持最多 10,000 个隔离环境并行；在阿里云上支持最多 10,000 并发 rollout；
  - 移动沙箱基于 MobileWorld（20 个 App，可重置）；为解决 KVM 模拟器的扩展瓶颈，改建在 **redroid** 上，「Android 作为容器跑在宿主内核，没有 QEMU，也不需要嵌套 KVM」，设备与自托管 App 后端一并复制；
  - 真机运行时：**100+ 台物理设备、150+ 应用**；健康感知调度器、不健康设备黑名单；**虚拟屏**让一部手机并行多个 App；涉及支付等敏感操作时请用户确认，CAPTCHA 交还用户；
  - 统一环境接口：acquire / reset / step / evaluate / tear_down / release，租约式会话；
  - 在线 RL 支持超过 100 轮的轨迹；动作空间 GUI + CLI + API 混合，并在一轮模型输出中**批量动作**。
- **启示**：这是目前读到的最直接证据，说明「容器化安卓（redroid）+ 真机补充」是大厂在 2026 年的主流分工；批量动作和虚拟屏直接对应手机侧沙箱的诉求。

**P4 MobileRL（2509.18119）**

- 编排**数百个 Docker 化 AVD**，自述可并发交互**超过 1,000 个环境**（论文·全文）。
- 但「局限」一节自述：每个 AVD **>5 GB 内存、>30 GB 存储**；用 4 台各 1 TB 内存的 CPU 机器只做 rollout；**只能稳定撑 ≤256 路并行，每步 >10 分钟**；训练 100 步 >25 小时。两处数字口径不同（峰值能力与稳定并发），写作时应并列引用，不要只引前者。
- 方法侧：AdaGRPO（难度自适应正样本回放、失败课程过滤、最短路径奖励）；100 步预算 >40 小时的消融。

**P5 DistRL（2410.14803）**

- host learner（GPU）+ 异构 Workers（运行模拟器或接真机）；workers 用 Environment Snapshots 重置到指定状态；轨迹异步回传。
- 数字（论文·全文）：对同步多机方法训练效率提升 3 倍，数据采集快 2.4 倍；任务时长可相差 100 倍（秒到 >10 分钟）。
- 创新点：中心训练 + 去中心采集；off-policy 修正；分布式优先回放。

**P6 Android Coach（2604.07277）**

- 问题：模拟器延迟高、样本效率低；传统「单状态单动作」不能充分利用昂贵的模拟器状态。
- 方法：单状态多动作，用 critic 估计动作价值，在不增加模拟器开销下复用同一在线状态。
- 数字（论文·全文）：8 并行环境、80 步训练的 rollout 时间分布显示，模拟器交互耗时是模型加载与推理的 1.7 倍；相同成功率下训练效率为 PPO 和 GRPO 的 1.4 倍；AndroidLab / AndroidWorld 相对 UI-TARS-1.5-7B 提升 7.5% / 8.3%；N 个动作采样的训练时间 N=2、4、8 分别为 1.22、1.62、2.18 倍。训练在单节点 8×A100 80GB，基于改造的 verl。
- 启示：这是「环境成本高所以减少环境交互」的算法侧解法，与系统侧快照、池化互补。

**P7 Xiaomi-GUI-0（2606.31410）**

- 以物理设备为主、沙箱辅助，覆盖手机、平板，延伸到车机；动因是反模拟器检测、账号态、权限弹窗、支付认证、风控（论文·全文）。
- 成绩：RealMobile 72.0%，AndroidWorld 78.9%。
- 本轮没有抓到设备规模与并发数字，待核实。

### 1.2 其他训练与环境论文（P8–P16，仅摘要）

| 论文 | 要点（摘要原文可见） | 对沙箱的启示 |
|---|---|---|
| P8 BlueLM-GUI | 35B-A3B；在数百台真机上做 agentic RL，强调沙箱训练与生产环境分布不一致；AndroidWorld 84.9 | 与 P7 同样走真机路线 |
| P9 HyMobileAgent | 百万级动作数据管线部署在 2000+ 沙箱与真机实例上，带自动失败归因；PhoneWorld Mock App Factory：34 个 mock 应用、34,000+ 任务，可重置 | 规模数字取自摘要，细节待核实 |
| P10 Mobile-Agent-v3 / GUI-Owl | 云端覆盖 Android、Ubuntu、macOS、Windows 的虚拟环境；完全异步的可扩展 RL；GUI-Owl-7B 在 AndroidWorld 66.4，Mobile-Agent-v3 达 73.3 | 摘要未给实例规模 |
| P11 PhoneWorld | 把真实 App 轨迹转为可运行、可重置、可程序化验证的 Android 环境；34 个 App、16 个领域；mock 与真实 App rollout 组合优于只用真实 App 的 RL | 解决真实 App 难重置、难验证、难规模化 |
| P12 OpenMobile-2 | MobileGym++：35 个商业风格模拟 App，重置与验证完全可控；加上模拟器中配置的应用共 110+ App；300+ 个 App 原生工具、50+ App；AndroidWorld 79.9 | GUI 与工具混合，直接降低对截图轮次的依赖 |
| P13 WM-R1 | 用世界模型代替真实 Android 环境做所有 rollout，支持大规模并行和步级粒度的轨迹生成 | 用「模型」替代沙箱，彻底免去实例开销，但存在状态混淆风险（见 §4） |
| P14 ClawGUI | 开源 GUI Agent RL 基础设施，验证支持并行虚拟环境与真机；Agent 端覆盖 Android、HarmonyOS、iOS，混合 CLI-GUI 控制 | 云训练到端侧部署的闭环 |
| P15 AgentRL | 全异步生成-训练流水线；统一函数调用式 API；容器化环境开发；中心控制器；已用于 AutoGLM | 环境即服务接口范式 |
| P16 AutoDroid-V2 | 把 UI 自动化转成代码生成，由端侧小模型生成脚本，端侧解释器执行；成功率更高、延迟与 token 更低 | 手机侧「执行一段脚本」比「逐步截图」更省，且需要沙箱来跑这段脚本 |

### 1.3 手机侧隔离与 Agent 安全（P17–P19）

- **P17 2505.12981**：对三类手机 Agent（OEM 系统级如 YOYO、第三方通用如 AutoGLM、框架类如阿里 Mobile Agent）做安全分析，识别出 **11 个攻击面**，按推理、GUI 交互、系统级执行三个能力维度组织（论文·摘要）。启示：系统级执行与 GUI 交互是两个独立需要隔离的面。
- **P18 Aster**：用 Arm CCA 的 realm 提供「互相隔离」的沙箱服务抽象，使沙箱内执行既不能访问其他沙箱、Android、hypervisor 或安全世界的内存，又能与 Android 安全通信（论文·摘要）。搜索结果称 MobiSys'26 版在模拟器与 Arm 板上评估，运行期影响小、启动时一次性开销固定（二手，未核实原文数字）。arXiv 2407.16694 是 2024 年的版本。
- **P19 IsolateGPT**：把 OS 与浏览器的执行隔离思想用于 LLM 应用生态，NDSS 2025；搜索结果称对四分之三的测试查询开销 <30%（二手）。
- **仅见标题、未打开**：Wei 等「Measuring and Optimizing the Performance of the Android Virtualization Framework」（researchr 条目，二手）；AnBridge（DSN'26，把端侧 AI 负载移植进受保护 VM，Purdue DCSL 条目，二手）；LPC 2025「A Linux VM on Android via AVF」幻灯片（二手，称对比 PRoot 的 ptrace syscall 开销）。这三项与手机侧沙箱高度相关，建议后续专门抓取。
- **未找到**：MobileRisk-Live（提示词中提到，本轮检索未命中，不能确认其编号）；论文层面的「云手机 / 安卓容器密度与性能优化」——两次 arXiv 检索（abs 含 cloud phone、Android containers / virtualization 等）没有返回相关论文，只返回不相关或旧文章。这个空白本身值得记录。

**这说明什么（判断）**：训练侧的论文已经把「重置、并发、长尾」讲得很细；手机侧的论文集中在安全与隔离，缺性能画像。两边尚未接上。

## 2. AS6-Q2 性能诉求归纳

下表只收有论文原文出处的数字。「目标值」大多没有被论文明确写出，凡是只能从上下文推断的一律标「判断」。

| 指标 | 实测或自述值 | 条件 | 目标 / 诉求（判断） | 来源 |
|---|---|---|---|---|
| 实例启动 / 重置 | Android Coach：环境交互（含初始化、恢复、响应）是模型加载与推理的 1.7 倍 | 8 并行环境，80 步，模拟器 | 重置应降到不再是主瓶颈 | P6 |
| 重置 | DistRL 用 Environment Snapshots 把模拟器重置到指定状态；未给出时间 | 模拟器 | 快照重置是标配 | P5 |
| 快照恢复 | 本轮论文中没有直接给出安卓快照恢复时间 | 待核实 | 参见 Cube issue 自报约 50 ms（主线程已核实，厂商自报） | – |
| 单实例内存 | >5 GB 内存、>30 GB 存储 / AVD | MobileRL，Docker 化 AVD | 越低越能提高并发 | P4 |
| 单实例内存 | DSec 的 microVM：free-page reporting + DAMON 降 21.2% | 非安卓，生产 Firecracker | – | P1 |
| 单机密度 | MobileRL：4 台 1 TB 机器，稳定 ≤256 路 | 每步 >10 分钟 | 内存是首要限制 | P4 |
| 单机密度 | DSec：单节点最多 800 microVM / 3,200 容器 | 非安卓，依赖 CPU 稀疏与过量分配 | 安卓负载下是否成立未知 | P1 |
| 总并发 | UI-TARS-2：数千 VM 实例，管理层数千 QPS | 数据来自字节 | – | P2 |
| 总并发 | Qwen-UI-Agent：10,000 并发沙箱 / rollout | 阿里云；安卓部分基于 redroid | – | P3 |
| 总并发 | DSec 峰值 >380,000 沙箱，>5,000 创建/秒 | 非安卓为主 | – | P1 |
| rollout 步时延 | MobileRL：每步 >10 分钟（指一次训练步，含大批量 rollout） | 256 并行 | 不是单个动作的时延 | P4 |
| 单步（截图到动作）时延 | 本轮没有读到可用数字 | 待核实 | – | – |
| 长尾 | 任务时长跨度达 100 倍（秒到 >10 分钟） | DistRL，在线 RL | 异步以消除同步空等 | P5 |
| 长尾 | DSec 沙箱寿命 P99 >3 小时，中位数约 16–17 分钟 | 容器 / microVM | 说明常驻内存成本显著 | P1 |
| rollout 吞吐 | DistRL 数据采集 2.4 倍、训练效率 3 倍（相对同步多机） | – | – | P5 |
| rollout 吞吐 | DSec：>5,000 创建/秒 | – | – | P1 |
| 训练时间占比 | Android Coach 图：交互耗时是推理的 1.7 倍 | 即约六成以上耗在环境侧（判断：按 1.7:1 折算为约 63%，非论文原文数字） | – | P6 |

**这说明什么（判断）**：
- 单实例 5 GB 级内存是云侧安卓密度的上限，容器化（redroid）正是为绕开它；对比之下，手机本机的 Agent 沙箱预算只能是 MB 到几百 MB 量级，云侧做法不能直接搬过去。
- 现有论文里「启动、快照恢复、单步时延」三项关键数字缺位，需要在 AS1、AS3 的源码与实测中补。

## 3. AS6-Q3 技术创新点归类

| 类别 | 代表工作 | 做法 | 等级 |
|---|---|---|---|
| 快照与重置复用 | DistRL（Environment Snapshots）；PhoneWorld、OpenMobile-2（可重置 mock 环境）；Cube issue（microVM 快照拉起，主线程已核实） | 把环境状态当成可保存、可恢复的资产 | 论文·全文 / 摘要 |
| 减少环境交互 | Android Coach（单状态多动作）；WM-R1（世界模型代替环境） | 让每次昂贵的环境状态用得更多，或干脆不用环境 | 论文·全文 / 摘要 |
| 环境与训练解耦、异步 | DistRL；UI-TARS-2（异步 rollout + 部分填充池）；GUI-Owl（全异步）；AgentRL；DSec（agent loop 与 RL 框架分离、可挂起沙箱） | 采集与学习分开，快慢 Worker 不互相等待 | 论文 |
| 异构平台与分层调度 | Qwen-UI-Agent（redroid 容器 + 真机，健康感知调度，黑名单）；Xiaomi-GUI-0 与 BlueLM-GUI（真机为主）；DSec（FnCall / 容器 / microVM / VM 分级） | 按负载选后端，真机负责「真实性」，容器负责规模 | 论文 |
| 存储与内存层面的密度优化 | DSec（EROFS 层、按需加载、virtio-pmem + DAX、DAMON + balloon） | 共享只读层、回收空闲页 | 论文·全文 |
| GUI 与 API 或代码混合 | Qwen-UI-Agent（GUI + CLI + API，批量动作）；OpenMobile-2（300+ App 原生工具）；AutoDroid-V2（生成代码）；ClawGUI（混合 CLI-GUI）；UI-TARS-2（GUI + 文件系统 + 终端） | 减少截图与推理轮次 | 论文 |
| 隔离与信息流控制 | IsolateGPT（应用级执行隔离）；Aster（Arm CCA 互相隔离）；2505.12981（攻击面分类） | 把隔离边界划到 hypervisor 之外或应用之间 | 论文·摘要 + 二手 |
| 人机确认与回滚 | Qwen-UI-Agent（支付类操作请用户确认；CAPTCHA 交还用户；恢复后续跑） | 敏感操作的人在回路 | 论文·全文 |
| 端云协同 | ClawGUI（从训练到 Android、HarmonyOS、iOS 部署）；AutoDroid-V2（端侧小模型 + 端侧解释器） | 云端训练，端侧执行 | 论文·摘要 |

**这说明什么（判断）**：创新集中在「怎么少用环境、怎么让环境便宜」，而不是「怎么让单个安卓实例本身更快、更小」。后者（安卓客体的启动、内存占用优化）在论文里几乎空白，主要靠 Cube、redroid 等工程项目推进。

## 4. AS6-Q4 开放问题

**论文自己承认的局限**：
- MobileRL：AVD 资源占用大限制并发；训练 100 步 >25 小时；大规模图像推理与网络传输带来额外开销（论文·全文）。
- Android Coach：模拟器延迟高、样本效率低（论文·全文，作为动机）。
- Xiaomi-GUI-0 与 Qwen-UI-Agent：沙箱无法复现账号状态、权限、CAPTCHA、弹窗、网络不稳（论文·全文）。
- 世界模型路线：另有论文（2609.32679，摘要）指出 GUI 世界模型存在「状态混淆」问题，仅凭当前画面预测会出错；2609.00048（摘要）指出需要多步一致性评测。说明用模型替代环境还不成熟。
- 另一篇 2610.29609（摘要）指出 Agent 的「成功自报」不可信，需要独立验证轨迹，说明奖励与完成判定是环境侧的另一项工作量。

**尚无人做或本轮未找到的空白（判断）**：
1. **安卓客体的启动与快照恢复的系统论文**：没有看到针对「安卓整机」的 fork / 快照复用方案的学术评测。
2. **ARM 服务器云手机的密度与性能论文**：检索未命中。
3. **手机本机上的 Agent 沙箱**：
   - 没有论文给出 AVF / pKVM 上开隔离环境给 Agent 用的启动、内存、功耗与热的数据；
   - 没有看到「虚拟屏后台执行」的内存、GPU 代价与前台干扰的测量；
   - 没有看到面向手机的 GUI Agent 确认与回滚机制的系统评测（Qwen-UI-Agent 只有产品层描述）。
4. **单步时延分解**（截图编码、传输、推理、注入、界面稳定等待）：本轮读到的论文中没有分项数据。

## 待核实

- UI-TARS-2 安卓实例的具体形态、重置与单步时延；是否使用快照。
- Qwen-UI-Agent 的 redroid 实例规格与单机密度；虚拟屏的内存与 GPU 代价。
- Xiaomi-GUI-0 的设备规模与并发。
- BlueLM-GUI 的作者机构；DistRL、PhoneWorld、WM-R1、ClawGUI 的作者机构。
- Aster 的 MobiSys'26 版本编号和评测数字；Wei 等 AVF 性能论文及 AnBridge（DSN'26）的结果；LPC 2025 AVF 幻灯片中的实测值。
- MobileRisk-Live 是否存在及编号。
- 「DSec」没有找到字节方案；此处实际归属为 DeepSeek（arXiv 2609.22978 的标题与摘要已核实），与 AS3 的归属核实一致。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| P1 | DeepSeek Elastic Compute (DSec): A Sandbox Infrastructure for Effective Agentic Training at Scale | https://arxiv.org/abs/2609.22978 | v1，2026-09-19 | 已抓（html 全文） |
| P2 | UI-TARS-2 Technical Report | https://arxiv.org/abs/2509.02544 | v2，2025-09-02 | 已抓（html 全文，grep） |
| P3 | Qwen-UI-Agent Technical Report | https://arxiv.org/abs/2607.28227 | v1，2026-07-30 | 已抓（html 全文，grep） |
| P4 | MobileRL: Online Agentic Reinforcement Learning for Mobile GUI Agents | https://arxiv.org/abs/2509.18119 | v2，2025-09-10 | 已抓（html 全文，grep） |
| P5 | DistRL | https://arxiv.org/abs/2410.14803 | v5，2024-10-18 | 已抓（html 全文，grep） |
| P6 | Android Coach | https://arxiv.org/abs/2604.07277 | v2，2026-04-08 | 已抓（html 全文，grep） |
| P7 | Xiaomi-GUI-0 Technical Report | https://arxiv.org/abs/2606.31410 | v2，2026-06-30 | 已抓（html 全文，grep） |
| P8 | BlueLM-GUI Technical Report | https://arxiv.org/abs/2609.12394 | v3，2026-09-11 | 仅摘要（API） |
| P9 | HyMobileAgent | https://arxiv.org/abs/2607.14548 | v1，2026-07-16 | 仅摘要（API） |
| P10 | Mobile-Agent-v3: Fundamental Agents for GUI Automation | https://arxiv.org/abs/2508.15144 | v2，2025-08-21 | 仅摘要（API） |
| P11 | PhoneWorld | https://arxiv.org/abs/2605.29486 | v3，2026-05-28 | 仅摘要（API） |
| P12 | OpenMobile-2 | https://arxiv.org/abs/2610.14157 | v1，2026-10-09 | 仅摘要（API） |
| P13 | WM-R1 | https://arxiv.org/abs/2608.27508 | v1，2026-08-27 | 仅摘要（API） |
| P14 | ClawGUI | https://arxiv.org/abs/2604.11784 | v1，2026-04-13 | 仅摘要（API） |
| P15 | AgentRL | https://arxiv.org/abs/2510.04206 | v1，2025-10-05 | 仅摘要（API） |
| P16 | AutoDroid-V2 | https://arxiv.org/abs/2412.18116 | v3，2024-12-24 | 仅摘要（API） |
| P17 | From Assistants to Adversaries: Exploring the Security Risks of Mobile LLM Agents | https://arxiv.org/abs/2505.12981 | v2，2025-05-19 | 仅摘要（API） |
| P18 | Aster: Fixing the Android TEE Ecosystem with Arm CCA | https://arxiv.org/abs/2407.16694 | v1，2024-07-23 | 仅摘要（API）；MobiSys'26 PDF 见搜索结果，未打开 |
| P19 | IsolateGPT | https://arxiv.org/abs/2403.04960 | v2，2024-03-08 | 仅摘要（API）；NDSS 2025 为搜索结果信息（二手） |
| S1 | 2609.32679（GUI World Model 状态混淆）；2609.00048（GUI-CC）；2610.29609（成功自报泄漏） | https://arxiv.org/abs/<对应编号> | 2026-08 至 2026-10 | 仅摘要（API 返回） |
| S2 | Measuring and Optimizing the Performance of the Android Virtualization Framework（Wei 等） | https://researchr.org/publication/WeiLLL24 | 年份待核实 | 二手，未打开 |
| S3 | AnBridge（DSN'26） | https://engineering.purdue.edu/dcsl/publications/papers/2026/anbridge-dsn26.pdf | 2026 | 二手，未打开 |
| S4 | LPC 2025：A Linux VM on Android via AVF | https://lpc.events/event/19/contributions/2123/attachments/1730/3786/LPC%202025%20-%20A%20Linux%20VM%20on%20Android%20via%20AVF%20(Android%20MC).pdf | 2025 | 二手，未打开 |

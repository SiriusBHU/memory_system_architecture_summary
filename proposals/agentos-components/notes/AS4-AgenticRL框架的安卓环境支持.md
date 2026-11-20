# AS4：主流 Agentic RL 框架与 GUI Agent 训练对安卓沙箱的支持

> 日期：2026-11-15；抓取版本：arXiv HTML 最新版（MobileRL v2、MAI-UI v1、ClawGUI 2604.11784、Android Coach 2604.07277 等）、各 GitHub 仓库首页（2026-11-15 抓取，无版本号）。
> 检索实际用量：WebFetch 6 / WebSearch 4 / 源码与论文文件 14（arXiv HTML 13 + android_world README 1）/ api.github.com 0。
> 未覆盖：veRL 主仓库（AS3 负责）、AgentCPM-GUI、DigiRL、UI-Venus 的环境章节未发现并发数；Step-GUI 的环境章节未发现并发数。

## 结论

1. **通用 Agentic RL 框架（verl-agent、ROLL、AReaL、slime）核心仓库均未内置安卓环境**（官方 README 未列出，等级：厂商自报，读 README 首页所得，未翻源码目录）。它们提供的是异步 rollout 与「自定义环境 / 沙箱」接口；安卓环境由上层项目（MobileRL、MAI-UI、ClawGUI、Android Coach）自行外挂，其中 MobileRL、Android Coach 基于 verl（论文）。
2. **主流做法是「x86 服务器上 Docker 化 AVD（Android Emulator）」**。MobileRL、MAI-UI、"Generalization in Online RL for Mobile Agents"(2603.07432)、ClawGUI（经 MobileWorld）都是此形态；单实例资源约 5 GB+ 内存、30 GB+ 存储（MobileRL，论文）；AndroidWorld 官方标称轻量 2 GB 内存 / 8 GB 磁盘（官方 README），实际 RL 里配置 16 GB RAM / 6 vCPU（2603.07432，论文）。
3. **公开并发规模：256–512 台**。MobileRL 稳定上限 256 并行 rollout（4 台 1 TB 内存 CPU 机），每个 step 超过 10 分钟，100 step 训练超过 25 小时（论文）；MAI-UI 用 10 台阿里云 ECS（ecs.ebmg5s.24xlarge）支撑最多 512 并发实例，并行环境数 32 到 512 使成功率 65.5% 到 70.7%（论文）；UI-TARS-2 的 VM 集群为「数千实例」、VM Manager 数千 QPS，但未单列安卓并发（论文）。
4. **重置方式 = AVD snapshot + 容器复用**。MAI-UI：AVD snapshot 提供可复现任务初始化，容器完成 rollout 后重置并重新分配而非销毁，并有备用池故障替换（论文）；DistRL：Environment Snapshots 重置模拟器（论文）；ClawGUI：每 episode Task Reset + Spare Server Rotation（论文）。**所有被检索论文均未给出以秒计的重置时间**——这是缺口。
5. **环境 / 模拟器交互是 rollout 瓶颈**：Android Coach 测得模拟器的初始化、恢复、反应耗时是模型加载与推理的 1.7 倍（论文，8 并行环境）；2603.07432 中 16 并行环境相对单环境顺序采集加速 6.83 倍（论文）；DistRL 192 vCPU 下约 7.7 条轨迹/分钟，近线性扩展（论文）。
6. **云手机 / 真机路线刚起步**：Mobile-Agent-v3 / GUI-Owl 用阿里云「云手机 + 云电脑」做轨迹生产与 RL（论文，无并发数）；ClawGUI-RL 首次开源验证「Docker 模拟器 + 真机 / 云手机」统一接口，但真机无 root、只能靠 MLLM-as-judge 判奖励（论文）。
7. **云侧沙箱平台与安卓的关系**：DSec（DeepSeek）把 Android 放在 QEMU 全 VM 后端，开销最高、仅服务特定负载；其 microVM / 容器单节点上限 800 / 3,200（论文）。AENV（Kimi 与清华 KVCache）是 Firecracker 快照环境，快照恢复 <50 ms，未提安卓（README，厂商自报）。

## 1. 支持矩阵（AS4-Q1）

### 1.1 Agentic RL 训练框架（通用）

| 框架 | 内置安卓环境 | 内置环境（据 README） | 异步 rollout | 沙箱 / 环境对接 | 开源 | 等级 | 来源 |
|---|---|---|---|---|---|---|---|
| verl-agent（langfengQ，基于 veRL） | 否 | ALFWorld、WebShop、Search、Sokoban、Gym Cards、AppWorld（实验性）；README 把 UI-S1（GUI 模型）列入「基于 verl-agent 的工作」，但未说明环境 | README 只把异步 rollout 列为「可贡献想法」，当前未宣称 | 并行 Gym 式环境；AppWorld 作为独立 server | 是 | 厂商自报 | [R11] |
| ROLL（阿里） | 否（未提） | Sokoban、FrozenLake（示例配置），对齐 GEM 环境定义 | 有：环境级异步并行 rollout、线程式环境 | 未描述沙箱；另有独立项目 ROCK（未读） | 是 | 厂商自报 | [R9] |
| AReaL（蚂蚁 / 清华） | 否（未提） | Tau2、搜索、TIR、SWE Agent、OpenClaw、OpenAI Agents SDK、CAMEL；黑盒 Agent 通过替换 base_url 在线训练 | 有：全异步，宣称相对同步系统 2.77 倍（boba² v0.3）；2.0 为微服务架构（训练 / 推理 / Agent / 权重更新分离） | 有 agent service，无沙箱描述 | 是 | 厂商自报 | [R10] |
| slime（THUDM） | 否（未提） | multi_agent、search-r1、fully_async、coding_agent_rl（sunabako 沙箱） | 有：examples/fully_async 针对长尾 | 自定义 generate 函数可封装沙箱；生态项目 Dressage 支持 bwrap / E2B / K8s | 是 | 厂商自报 | [R12] |
| AgentRL（THUDM，2510.04206） | 论文引用 AndroidLab，但环境章节未发现安卓并发数；已核实的是容器化 + 集中控制器 | 多任务（含 WebShop 等） | 有：协程调度的全异步生成—训练 | 函数调用式统一 API、每任务容器、集中 controller 管理「数千」并行 episode | 待核实 | 论文 | [R6] |
| AENV / AgentENV（kvcache-ai） | 未提 | 非训练框架，是环境基础设施 | — | Firecracker microVM、E2B 兼容 API、快照 <50 ms 恢复、可 fork、内存超卖 9.6 倍 | 是 | 厂商自报 | [R13] |
| DSec（DeepSeek，2609.22978） | 有（QEMU 全 VM 里的 Android VM） | 函数调用、容器、microVM、全 VM 四类后端 | 论文称支撑异步 rollout、抢占后可恢复 | 与训练框架显式集成 | 未发现开源 | 论文 | [R5] |

### 1.2 GUI / 手机 Agent 训练项目

| 项目 | 环境形态 | 宿主架构 | 并发规模 | 重置方式 | 异步 rollout | 开源 | 等级 | 来源 |
|---|---|---|---|---|---|---|---|---|
| MobileRL / AutoGLM（智谱，2509.18119） | Docker 化 AVD | 未明写；纯 CPU 机，估计 x86（待核实） | 声称可协调 1,000+ 环境；实际稳定 256 并行 | 未详述 | 以 verl 为基础的框架；采样异步程度待核实 | 框架论文称开源，仓库待核实 | 论文 | [R1] |
| MAI-UI（阿里通义，2512.22047） | Docker：root 的 AVD + 自托管后端 + REST API | ECS 裸金属 ecs.ebmg5s.24xlarge（命名推测为 x86 Intel，估算） | 10 台 ECS 支撑最多 512 并发 | AVD snapshot；容器复用（重置后重新分配）；备用池故障切换 | 是（异步 rollout + Megatron 混合并行，最多 50 步） | 模型开源；环境框架未见开源 | 论文 | [R7] |
| UI-TARS-2（字节，2509.02544） | 云 VM（Windows / Ubuntu / Android）+ 浏览器沙箱 | 未披露 | VM 集群「数千实例」，VM Manager 数千 QPS | 未披露 | 是（服务端异步推理、动态 rollout 池、有状态环境） | 否（报告） | 论文 | [R3] |
| Mobile-Agent-v3 / GUI-Owl（阿里） | 阿里云云手机 + 云电脑（含 Android、Ubuntu、macOS、Windows） | 未披露 | 未披露 | 未披露 | 是（rollout 与更新完全解耦，同步 / 异步可选） | 模型与代码开源（X-PLUG/MobileAgent） | 论文 | [R2] |
| ClawGUI-RL（2604.11784） | Docker 模拟器（经 MobileWorld）+ 真机 / 云手机，统一接口 | 未披露 | 训练用 64 并行虚拟环境，8×A6000；称可启动「数十个」 | Task Reset 每 episode；Spare Server Rotation | 并行；异步程度待核实 | 是（称首个开源） | 论文 | [R14] |
| 2603.07432 Generalization in Online RL | Docker 容器内 Android 13（API 33）模拟器 + HTTP server | headless Linux 服务器；架构未明 | 16 并行环境，2×H100 | 容器隔离，同配额防掉队 | 是（环境独立推进，消除全局同步） | 称发布环境与基础设施 | 论文 | [R15] |
| Android Coach（2604.07277） | 并行 Android 13 模拟器，uiautomator2 | 未披露 | 并行环境数 = batch size，示例 8 | 未详述 | 否（批量 rollout）；用 critic 减少交互 | 待核实 | 论文 | [R16] |
| DistRL（2410.14803） | 工作机上的 Android Emulator 或真机，多线程 | 2 台工作机，各 8×T4、96 vCPU，运行于 AWS（x86 实例，估算） | 192 vCPU，32 模拟器对比实验 | Environment Snapshots | 是（主机 learner + worker，异步） | 待核实 | 论文 | [R4] |
| AndroidWorld（Google，2405.14573） | 单个 AVD（Pixel 6，API 33）；2025-06 起实验性 Docker | x86；Apple Silicon 上 Docker 内跑模拟器很慢 | 官方「通常不支持真并发」（MobileRL 的说法） | 官方示例用 `-no-snapshot`，任务自带 setup | 否 | 是 | 官方文档 | [R8] |
| AndroidLab（THUDM，2410.24024） | 预打包 AVD 镜像（固定屏幕、Android 版本、应用状态），ADB 连接，也支持真机 | 未披露 | 未披露 | AVD 镜像预置状态 | 否 | 是 | 论文 | [R17] |
| UI-Venus（蚂蚁，2508.10833） | 论文称有「含几十台手机的虚拟云环境」做轨迹生成 | 未披露 | 「dozens」 | 未披露 | 未披露 | 模型开源 | 论文 | [R18] |
| Step-GUI / GELab（阶跃，2512.15431） | 报告提到端到端基准存在 CAPTCHA、虚拟机崩溃等环境不稳定；训练环境形态未披露 | 未披露 | 未披露 | 未披露 | 未披露 | 模型开源 | 论文 | [R19] |

**这说明什么（判断）**：通用 RL 框架不负责安卓，环境层被抽象为「HTTP 服务 + reset/step/evaluate」，安卓只是其中一种后端。真正决定规模的是下层环境管理器（MAI-UI Environment Manager、DSec、AENV 这类）。

## 2. 规模与性能数字（AS4-Q2）

| 指标 | 数值 | 条件 | 等级 | 来源 |
|---|---|---|---|---|
| 并发实例（最大公开） | 512 | MAI-UI，10 台 ECS ecs.ebmg5s.24xlarge | 论文 | [R7] |
| 并发实例（稳定上限） | 256 | MobileRL，4 台 1 TB 内存 CPU 机 | 论文 | [R1] |
| 声称可编排 | 1,000+ 环境 | MobileRL，Docker AVD，跨机；与上一行的稳定上限 256 并存，口径有差 | 论文 | [R1] |
| 单实例内存 / 存储 | >5 GB / >30 GB | MobileRL 的 AVD | 论文 | [R1] |
| 单实例配置 | 16 GB RAM、6 GB 磁盘、6 vCPU、2400×1080 | 2603.07432，Android 13 | 论文 | [R15] |
| 单实例（官方标称） | 2 GB 内存 / 8 GB 磁盘 | AndroidWorld 官方「轻量」说法，Pixel 6 AVD | 官方文档 | [R8] |
| RL 单 step 耗时 | >10 分钟；100 step >25 小时 | MobileRL，256 并行 rollout | 论文 | [R1] |
| 采集吞吐 | ~7.7 条轨迹 / 分钟，近线性扩展 | DistRL，192 vCPU | 论文 | [R4] |
| 采集量对比 | 6,000 s 内 800 条 vs DigiRL 300 条 | DistRL 多机，32 模拟器 | 论文 | [R4] |
| 并行加速 | 6.83 倍 | 16 环境 vs 1 环境顺序，2×H100，每 step 16 条 rollout | 论文 | [R15] |
| 并行环境对效果的影响 | 32 到 512：65.5% 到 70.7%（正文另一处称提升 5.2 点） | MAI-UI 在线 RL | 论文 | [R7] |
| 步数预算 | 15 步到 50 步提升 4.3 点 | MAI-UI | 论文 | [R7]（经搜索摘要，未在正文逐字核对） |
| 环境交互 vs 推理 | 模拟器初始化 + 恢复 + 反应耗时是模型加载 + 推理的 1.7 倍 | Android Coach，8 并行环境，80 训练步 | 论文 | [R16] |
| 云 VM 集群 | 数千实例；VM Manager 数千 QPS | UI-TARS-2（含 Windows / Ubuntu / Android，未拆分） | 论文 | [R3] |
| 云侧沙箱峰值 | 380,000 并发、>5,000 创建 / 秒、~3M 沙箱 / 天；单节点最多 800 microVM 或 3,200 容器 | DSec 生产，160 节点一个 scale unit；Android 在 QEMU 全 VM，不在此数字中单列 | 论文 | [R5] |
| 沙箱存活时间 | 容器 / microVM 中位数 17.4 / 15.5 分钟，p99 >3 小时 | DSec，2026 年初一周 30K 容器 + 10K microVM 采样 | 论文 | [R5] |
| 快照恢复 | <50 ms；内存超卖 9.6 倍 | AENV，Firecracker，非安卓 | 厂商自报 | [R13] |
| 单步时延（截图 + 推理 + 动作） | **本轮未发现任何论文给出** | — | 待核实 | — |
| 重置时间（秒级） | **本轮未发现** | — | 待核实 | — |
| rollout 占训练时间比例 | 定性「rollout 主导」：2603.07432 图 7 显示 16 条 rollout 的采集时间远大于策略更新（具体比例图中，未转录） | — | 论文 | [R15] |

**这说明什么（判断）**：训练侧安卓环境的天花板在 200–500 实例量级，受制于单实例 5–16 GB 内存与 30 GB 存储。若换成 Cube 报告的 microVM 密度口径，需要同口径的安卓实例内存（redroid 在 guest 内 RSS）才能对比，这是本库后续要补的一环。

## 3. 报告自述的技术挑战与工程解法（AS4-Q3）

| 挑战 | 出处与证据 | 工程解法 | 等级 | 来源 |
|---|---|---|---|---|
| 模拟器资源重、实例少 | MobileRL：每台 >5 GB / >30 GB，稳定 256 并行，step >10 分钟，限制训练步数 | 4 台 1 TB 内存机专用 rollout；分布式多机采样 | 论文 | [R1] |
| 现有安卓模拟器实现不支持真并发 | MobileRL 对 AndroidEnv、AndroidWorld 的评价 | Docker 化 AVD + 多机编排 | 论文 | [R1] |
| 多模拟器争抢资源导致卡死、延迟、崩溃，一个失败拖垮其他 | 2603.07432 | 每环境一个容器，同 CPU / 内存配额防掉队；HTTP 解耦训练与环境 | 论文 | [R15] |
| 容器不健康 / 崩溃 | ClawGUI；MAI-UI | ClawGUI 备用 server 队列轮换；MAI-UI 自动检测并从备用池换实例 | 论文 | [R14][R7] |
| 重置慢、环境浪费 | MAI-UI | 容器复用：重置后重新分配；AVD snapshot 复现初始化 | 论文 | [R7] |
| 长尾时延拖累同步 RL | UI-TARS-2；AgentRL；DSec | 动态 rollout 池、完整 trace 够 batch 就更新、未完成留池；协程异步；DSec 持续补充并发、可中断恢复 | 论文 | [R3][R6][R5] |
| 奖励判定要读应用状态 | MAI-UI：root AVD 做规则校验，复杂任务 MLLM-as-judge，一致率 83% | 混合验证 | 论文 | [R7] |
| 真机无 root，无法自动验证 | ClawGUI | MLLM-as-judge 看最终屏幕；任务需人工编写 | 论文 | [R14] |
| 环境不稳定污染评测 | Step-GUI：CAPTCHA、虚拟机崩溃 | 用 pass@3 缓解 | 论文 | [R19] |
| 应用版本与 AVD 兼容、UI 改版 | DistRL | 用 ADB 与模拟器做重置，大改版需重新微调 | 论文 | [R4] |
| 截图编码与网络传输开销 | MobileRL：大规模图像推理与网络传输增加负担 | 未给出具体解法（自述局限） | 论文 | [R1] |
| 长轨迹超显存 | MAI-UI：单条轨迹可达百万 token | Megatron TP+PP+CP；图像缩至一半分辨率 | 论文 | [R7] |
| 账号风控、登录态、反作弊 | 本轮 GUI Agent 训练报告未发现正面论述；其中只有环境不稳定 | 待核实 | — | — |
| 难度分布长尾、训练崩溃 | MobileRL：约 30 步后崩溃，需 AdaPR 与 SPA | 自适应正样本重放、失败课程过滤 | 论文 | [R1] |

**这说明什么（判断）**：工程痛点集中在「实例太重」与「长尾」。登录态、风控这类问题在仿真环境里被回避了（用预装 App 的离线 AVD），一旦转向真机云手机（ClawGUI 路线）才会暴露。

## 4. 趋势（AS4-Q4）

| 趋势 | 证据 | 等级 | 来源 |
|---|---|---|---|
| 环境即服务（env-as-a-service） | MAI-UI 的 Environment Manager 暴露统一 REST API、跨 ECS 编排；AgentRL 函数调用式 API + 集中 controller；DSec 统一 SDK 覆盖四类后端；AENV 兼容 E2B API；ClawGUI 统一设备后端接口 | 论文 / 厂商自报 | [R7][R6][R5][R13][R14] |
| 异步 rollout 与环境解耦 | UI-TARS-2、Mobile-Agent-v3（rollout 与更新解耦）、AgentRL、AReaL 2.0 微服务、ROLL、slime fully_async、MAI-UI、2603.07432 | 论文 / 厂商自报 | [R3][R2][R6][R10][R9][R12][R7][R15] |
| 快照池化与容器复用 | MAI-UI（snapshot + 复用 + 备用池）、DistRL 快照、AENV 快照 <50 ms 且可 fork | 论文 / 厂商自报 | [R7][R4][R13] |
| 模拟器到真机 / 云手机迁移 | Mobile-Agent-v3 用阿里云云手机；ClawGUI-RL 支持真机但需 MLLM judge | 论文 | [R2][R14] |
| 少与环境交互（算法侧缓解） | Android Coach：用 critic 在同一状态多采样动作，不增加模拟器开销 | 论文 | [R16] |
| 云侧平台对安卓的支持是「全 VM」而非 microVM | DSec 的 Android 走 QEMU 全 VM（最高开销）；AENV 未提；Cube issue #1878 才在探索 redroid + microVM（见 AS1） | 论文 / 主线程已核实 | [R5][R13] |
| 合成环境 / 世界模型替代真实环境 | **本轮未检索到直接证据**（未做针对性搜索） | 待核实 | — |

**这说明什么（判断）**：训练侧已经把环境层抽象成服务，但安卓实例本身仍是 2020 年模拟器 + Docker 的重形态。云侧沙箱平台（DSec、AENV）的快照 / 超卖 / 按需加载机制尚未与安卓实例结合，这是 Cube 安卓路径（redroid 放进 guest 内核、恢复约 50 ms）可对比的空白。

## 待核实

- MobileRL 的并发上限 1,000+ 与稳定 256 的口径差；其宿主架构（x86 / ARM）；开源仓库状态。
- MAI-UI 的 ECS 规格 ecs.ebmg5s.24xlarge 的 CPU 架构与内存；Environment Manager 是否开源。
- Mobile-Agent-v3 / GUI-Owl 云手机的并发数、单步时延（论文正文本轮仅做关键词扫描，未发现）。
- UI-TARS-2 安卓实例形态与重置策略（报告未披露）。
- AENV 与 DSec 是否有安卓或 GUI 环境（AENV README 未提；DSec 只在 QEMU 全 VM 一句话）。
- 所有以秒计的「重置时间」「单步时延」，以及 rollout 占总训练时间的百分比。
- 通用框架仅查了 README 首页，未检索其 issue 与示例目录，可能存在未列出的 GUI 实验分支。
- 世界模型 / 合成环境证据；AgentCPM-GUI、DigiRL、DeepMind AndroidEnv 本轮未覆盖。
- verl 主仓库 AgentLoop 与安卓的关系（交 AS3）。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| R1 | MobileRL: Online Agentic RL for Mobile GUI Agents | https://arxiv.org/abs/2509.18119 | v2，2025-09 | 已抓 HTML |
| R2 | Mobile-Agent-v3: Fundamental Agents for GUI Automation | https://arxiv.org/abs/2508.15144 | 2025-08 | 已抓 HTML |
| R3 | UI-TARS-2 Technical Report | https://arxiv.org/abs/2509.02544 | 2025-09 | 已抓 HTML |
| R4 | DistRL | https://arxiv.org/abs/2410.14803 | 2024-10 | 已抓 HTML |
| R5 | DeepSeek Elastic Compute (DSec) | https://arxiv.org/abs/2609.22978 | 2026-09 | 已抓 HTML |
| R6 | AgentRL | https://arxiv.org/abs/2510.04206 | 2025-10 | 已抓 HTML |
| R7 | MAI-UI Technical Report | https://arxiv.org/abs/2512.22047 | v1，2025-12 | 已抓 HTML |
| R8 | AndroidWorld README | https://github.com/google-research/android_world | main，2026-11-15 抓取 | 已抓 |
| R9 | ROLL | https://github.com/alibaba/ROLL | 2026-11-15 抓取 | 已抓（WebFetch 摘要） |
| R10 | AReaL | https://github.com/inclusionAI/AReaL | 2026-11-15 抓取 | 已抓（WebFetch 摘要） |
| R11 | verl-agent | https://github.com/langfengQ/verl-agent | 2026-11-15 抓取 | 已抓（WebFetch 摘要） |
| R12 | slime | https://github.com/THUDM/slime | 2026-11-15 抓取 | 已抓（WebFetch 摘要） |
| R13 | AgentENV（AENV） | https://github.com/kvcache-ai/AgentENV | 2026-11-15 抓取（kvcache-ai/AENV 返回 404，AgentENV 可访问） | 已抓（WebFetch 摘要） |
| R14 | ClawGUI | https://arxiv.org/abs/2604.11784 | 2026-04 | 已抓 HTML |
| R15 | Generalization in Online RL for Mobile Agents | https://arxiv.org/abs/2603.07432 | 2026-03 | 已抓 HTML |
| R16 | Android Coach | https://arxiv.org/abs/2604.07277 | 2026-04 | 已抓 HTML |
| R17 | AndroidLab | https://arxiv.org/abs/2410.24024 | 2024-10 | 已抓 HTML |
| R18 | UI-Venus Technical Report | https://arxiv.org/abs/2508.10833 | 2025-08 | 已抓 HTML（仅关键词扫描） |
| R19 | Step-GUI Technical Report | https://arxiv.org/abs/2512.15431 | 2025-12 | 已抓 HTML（仅关键词扫描） |

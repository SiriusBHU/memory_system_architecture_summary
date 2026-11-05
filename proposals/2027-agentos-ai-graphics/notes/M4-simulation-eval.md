# M4 性能跟踪与仿真（S1 + S2）调研笔记

> 检索日期：2026-11-03。模块范围：1.2 中 S1、S2 的业界洞察；第四部分 S1、S2 两节。
> 边界：不做 GUI Agent、不做多 Agent 并发。AndroidWorld 等只作负载参考。

## 摘要

1. 公开的 LLM 仿真器（Vidur、LLMServingSim 2.0、GenZ、LLMCompass）全部面向数据中心 GPU/TPU，**没有找到面向手机 SoC（NPU/UFS/热）的公开 LLM 仿真器**。这是 S1/S2 最大的资料空白，也是我们自研「手机侧仿真平台」的立项理由。
2. 最接近的是解析式 roofline 路线：GenZ（报告最大 geomean 误差 5.82%）、LIFE（AMD 平台，arXiv 2025，误差待核实）、RooflineBench。手机上可用的校准素材来自 PowerInfer-2 的实测有效带宽（CPU 约 43.9 GB/s、NPU 约 56 GB/s）。
3. 端云能耗没有可直接比较的公开数据：Google 云侧中位 Gemini 文本 prompt 约 0.24 Wh（不含网络和终端）；端侧论文 2026 年报告「端侧每 token 能效平均比批处理服务器差约 3 倍」。两者口径不同，只能做量级判断。
4. 云成本口径：Google AI Studio 价格页（抓取日 2026-11-03）Gemini 3.1 Flash-Lite 为 $0.25 / $1.50 每百万 token（输入/输出），一个 10 步、约 2 万输入 token 的 Agent 任务云侧约 $0.007（估算），成本差距不是主要矛盾，**能耗、内存和体验风险才是**。
5. S2 有直接证据：LLMCompiler（ICML 2024）延迟最高 3.7 倍；PASTE（2026）任务完成时间降 43.5%；Speculative Actions 最高降 20%；手机 NPU 上 decode 受带宽限制，合批/投机能榨出 NPU 闲置算力（定量倍数待核实）。
6. 最大空白：真机 Agent 体验指标（如 time-to-first-action）没有公开标准定义；手机 SoC 功耗模型与仿真校准没有公开成熟方法，Perfetto 的 ODPM 仅部分机型可用。

---

## 第一部分（M4 范围）洞察：S1、S2 业界进展（对应 1.2）

### 1.2-S1 云转端：评估对象与业界数据

**趋势 S1-T1：端云协同从「整请求路由」走向「子任务 / token 级路由」。**
- 事实：Hybrid LLM（Ding 等，ICLR 2024，arXiv 2404.14618）用路由器按预测难度选小/大模型，大模型调用最多减少 40% 且质量不降；RouteLLM（Ong 等，ICLR 2025，arXiv 2406.18665）报告成本降低超过 2 倍。HybridFlow（arXiv 2512.22137，ICML 2026）按子任务路由到边缘小模型或云端大模型，摘要未给具体百分比。[R1][R2][R3]
- 事实：投机式端云解码——Venkatesha 等（TMLR 2025，arXiv 2505.21594）端侧小模型起草、云端验证，实验台（Jetson Nano + A100）相对云端自回归延迟最多降 35%；SPADE（arXiv 2608.13076，2026-08）称云端模型调用减少 76%（仅读摘要，待核实）。[R4][R5]
- 对我们的影响：S1 的评估对象不应只是「整个 Agent 搬到端」，而要按**步骤/子任务**粒度评估哪些留云、哪些下沉。仿真平台要能表达路由策略。

**趋势 S1-T2：端侧能效并不天然优于云。**
- 事实：Guégain & Coignion（arXiv 2609.11940，2026-07 提交）报告端侧推理平均比批处理服务器能效差约 3 倍，且端侧每 token 环境影响的 88–90% 来自设备制造隐含碳；两部手机、18 种模型配置，页面未给绝对 J/token。[R6]
- 事实：「Is Your NPU Ready for LLMs?」（arXiv 2607.05475，SIGMETRICS 2027 接收）指出 NPU 在 prefill 占优、CPU 在 decode 占优；框架间差异在 NPU 上最多放大 10 倍；CPU 调频单独可降能耗最多 39.7%，NPU 能耗配置最多降 53.2%（作者标注为估算）。[R7]
- 事实：Google 披露中位 Gemini Apps 文本 prompt 约 0.24 Wh、0.03 gCO2e、0.26 mL 水，覆盖加速器、主机 CPU/DRAM、空闲容量与机房开销，**不含外部网络与终端能耗**（arXiv 2508.15734，2025-08；未同行评审）。[R8]
- 对我们的影响：「云转端」的卖点不能写「更省电」，只能写在**隐私、离线、时延确定性、云成本**上，同时必须用 S1 量化「端侧多耗多少电」。结论方向和多数人直觉相反，要在立项材料里先讲清。

**趋势 S1-T3：云推理成本持续下降，两个量级的价差并存。**
- 事实：Google AI Studio 价格页（2026-11-03 抓取，无页面更新日期），文本、标准付费档、每百万 token 输入/输出美元：Gemini 2.5 Flash-Lite 0.10/0.40；3.1 Flash-Lite 0.25/1.50；3.5 Flash-Lite 0.30/2.50；3 Flash Preview 0.50/3.00；3.6 与 3.8 Flash 到 2026-12-31 为 0.75/3.75，2027-01-01 起 1.50/7.50；3.1 Pro Preview 2.00/12.00（≤200k 上下文）。页面称 2026-12-01 起 2.5 Flash/Pro 将自动路由到更新模型并按新价计费。[R9]
- 事实（二手来源，待核实）：DeepSeek V3.2 常见报价约 $0.28/$0.42，缓存命中输入约 $0.028；多个聚合站数字互相冲突，未核对官方页。[R10]
- 对我们的影响：云成本在 2027 年对厂商是**可计算的运营支出**，且 Flash 档 2027-01 起涨价一倍，端侧下沉的成本收益要按「调用量 × 单任务 token」算总账，不能只看单价。

**趋势 S1-T4：仿真器成熟于数据中心，手机侧是空白。**
见下表（均已核实名称、年份与出处）。

| 工具 | 年份 / 会议 | 对象 | 方法与精度 | 开源 | 局限（对手机） |
|---|---|---|---|---|---|
| Vidur | MLSys 2024，arXiv 2405.05465 | GPU 集群 LLM 服务 | 算子剖析 + 预测；请求级误差 <9% | github.com/microsoft/vidur（MIT，来自聚合页） | 无 NPU/UFS/热/DVFS；需 GPU 初始剖析 |
| LLMServingSim（初版） | IISWC 2024 | 异构加速器 HW/SW 协同仿真 | 与 ASTRA-Sim 耦合 | github.com/casys-kaist/LLMServingSim（MIT） | 同上 |
| LLMServingSim 2.0 | arXiv 2602.23036（2026-02，v2 2026-03）；仓库称 ISPASS 2026 与 CAL 2025 | 异构、解耦服务；含内存层级、MoE、投机解码、功耗 | 报告平均误差 0.95%，仿真约 10 分钟；profile 可接入新加速器 | 同上（仓库 README 称 RTX 4090 档在 1% 内） | 以 vLLM 调度为蓝本；无手机 SoC profile；论文 ISPASS 收录状态以仓库说明为准，待核实 |
| GenZ | arXiv 2406.01698（2024） | 分布式推理平台设计 | 解析式 roofline；最大 geomean 误差 5.82% | github.com/abhibambhaniya/GenZ-LLM-Analyzer（来自检索结果，未打开仓库） | 面向数据中心硬件 |
| LLMCompass | ISCA 2024，arXiv 2312.03134 | 硬件设计空间探索 | 算子误差约 10.4%，端到端约 4.1% | github.com/PrincetonUniversity/LLMCompass（许可待核实） | A100/MI210/TPUv3 |
| LIFE | arXiv 2508.00904（2025-07，仅预印本） | 与硬件无关的解析式推理预测 | 仅用 TOPS 与带宽预测 TTFT/TPOT；覆盖量化、KV 压缩、分块 prefill | 未找到 | AMD CPU/NPU/iGPU 与 V100 上验证，非手机；误差未在摘要给出 |
| RooflineBench | arXiv 2602.11506（2026） | 端侧 LLM roofline | 实测峰值算力与带宽后外推 | 待核实 | 需要真机，不是纯预测 |

- 对我们的影响：直接复用 Vidur/LLMServingSim 的**调度与批处理框架**，但手机 SoC 的算子延迟、带宽争抢、DVFS/热、UFS 换入换出必须自建 profile。LLMServingSim 2.0 的「profile 接入新加速器 + 内存层级（含 CXL/PIM）」是最合适的二次开发底座候选；这一判断为推断，需做一次实验验证。

**趋势 S1-T5：Agent 工作负载被系统性刻画，结论是「decode 主导、上下文高复用」。**
- 事实：「Agentic AI Workload Characteristics」（Yuan 等，arXiv 2605.26297，IISWC 2026）：ReAct 类 Agent 在有效上下文缓存下多数输入 token 被复用，执行以 decode 为主，依赖长生命周期 KV 状态；摘要未给数值。[R11]
- 事实（仅二手摘要，待核实原文）：同一论文的二手摘要称 LLM 推理占总执行时间 71–98%，SWE-bench Pro 累积上下文平均 69K–80K token；TraceLab（UW，2026-06）称编码 Agent 单次 LLM 生成平均约 13 s、单次工具调用约 18 s、输入 token 缓存命中 95.7%。[R11][R12]
- 对我们的影响：仿真负载需包含「多轮重入 + 大前缀复用 + 工具等待」三要素，这直接决定 KT2（KV 持久化）和 S2（工具并行）的收益上限。

**趋势 S1-T6：真机评测开始强调功耗/热，而非只看成功率。**
- 事实：BYTE（Li 等，NeurIPS 2026 研讨会 On-Device Intelligence，poster）连接真机并在设备端采集电量、功耗、温度，发现动态功耗包络、持续推理下的热累积、跨云/端的非线性能耗缩放；摘要无数值。[R13]
- 事实：MLPerf Mobile v6.0（MLCommons，2026-06）加入 Llama 3.2 1B/3B 与 Llama 3.1 8B 的 LLM 测试，应用通过 Google Play、App Store 与 GitHub（Apache 2.0）分发；未找到结果表。一篇 2026-05 论文称其只报聚合吞吐（二手，待核实）。[R14]
- 对我们的影响：标准负载集可「MLPerf Mobile 的 LLM 子集（模型与吞吐口径）+ 自建 Agent 多轮 trace 回放」组合；AndroidWorld 只借其任务步数与步间延迟分布作参考（我们不做 GUI Agent）。

### 1.2-S2 单 Agent 内部并行化：业界进展

**趋势 S2-T1：并行工具调用与规划已成熟，但主要在云。**
- 事实：LLMCompiler（Kim 等，ICML 2024，PMLR 235:24370–24391，arXiv 2312.04511）由规划器、任务取回单元、执行器组成，相对 ReAct 延迟最高 3.7 倍、成本最高 6.7 倍、精度最高提升约 9%，相对 OpenAI 并行函数调用最高 1.35 倍；官方仓库 github.com/SqueezeAILab/LLMCompiler（MIT）。[R15]
- 事实：Skeleton-of-Thought（Ning 等，ICLR 2024，arXiv 2307.15337）先生成骨架再并行/批量展开各点，12 个模型最高约 2.39 倍；论文自己的解释是增大 batch 不会明显增加每 token 延迟，仅适合可分解为独立要点的问题。[R16]

**趋势 S2-T2：投机式工具执行把「工具等待」藏进 LLM 生成里。**
- 事实：PASTE（Sui 等，arXiv 2603.18897，2026-03 提交、v3 于 2026-06）预测后续工具调用、在 LLM 生成期间投机执行并隔离结果，平均任务完成时间降 43.5%、工具延迟降 1.8 倍（深度研究、编码、科研类）。注意：检索摘要曾显示 48.5%，抓取 v3 页面为 43.5%，**以 v3 页面为准，不同版本数字不同**，待核实。[R17]
- 事实：Speculative Actions（Ye 等，arXiv 2510.04371，2025-10，v2 2026-04）用快速模型预测下一动作，最高 55% 预测准确率、最高 20% 延迟降低，场景含游戏、电商、搜索。[R18]
- 事实（二手摘要，待核实）：「Optimizing Agentic LM Inference via Speculative Tool Calls」称客户端投机每轮节省 6–21%，工具时延为模拟。局限：只适合无状态、廉价、可回滚的工具；有副作用的工具（发消息、转账）不能投机。[R19]
- 对我们的影响：手机上工具（通讯录、日历、文件、网络）多数**有副作用或有权限弹窗**，投机执行必须有「只读 / 可回滚」白名单；这是 S2 的核心约束。

**趋势 S2-T3：端侧 decode 带宽受限，合批/投机能利用 NPU 闲置算力。**
- 事实：「Scaling LLM Test-Time Compute with Mobile NPU on Smartphones」（Hao 等，arXiv 2509.23324，2025-09）指出手机 NPU 在常规 LLM 推理中矩阵单元大量闲置，提出在 NPU 上并行测试时扩展；摘要给出混合精度 GEMM 最高 19.0 倍、Softmax 2.2 倍（无单位与基线，待核实）；批大小越大吞吐越高但亚线性（来自检索摘要）。[R20]
- 事实：sd.npu（arXiv 2510.15312）称 decode 受带宽限制，验证阶段 NPU 算力闲置超过 70%，prefill/decode 图切换最多占 decode 延迟 29%（二手摘要，待核实）。[R21]
- 事实：PowerInfer-2（Xue 等，arXiv 2406.06282）在 OnePlus 12 上测得 7B 模型有效带宽约 43.9 GB/s（CPU）、56 GB/s（NPU）、两者并用 59.6 GB/s；TurboSparse-Mixtral-47B 为 11.68 token/s，且内存从 7 GB 增至 19 GB 时由 2.13 升至 11.68 token/s；llama.cpp 对比能耗 0.672 J/token，PowerInfer-2 为 0.257 J/token（设备与模型未在检索摘要中确认，待核实）。[R22]
- 对我们的影响：S2 的 CPU/GPU/NPU 流水不是「理论加速」，而是受**共享 LPDDR 带宽**约束（见上，约 44–60 GB/s 量级）；合批收益要在带宽被工具/UI/其他 IP 占用时重新评估，这正是需要仿真平台的原因。

**对立项的启示（M4 部分）**
- 支撑 S1：端云评估需要多维决策模型而非单一成本比较；云侧成本已很低，端侧能耗劣势已有论文佐证，必须量化；手机仿真器是公开空白。
- 支撑 S2：并行工具调用和投机执行有云上实证，但端侧的带宽、权限、副作用约束未被研究，是差异化点。

---

## 第四部分

### S1 Agent 云转端的性能 / 功耗代价与成本收益评估

#### 1. 要解决的问题

- 现状：立项要把一部分 Agent 步骤从云下沉到端，但「值不值」没有统一口径。云有 token 成本（Gemini 3.1 Flash-Lite $0.25/$1.50 每百万 token 输入/输出，2026-11-03），端有电量、内存、发热和体验风险，各自不可直接比较。
- 代价（量化，估算，计算过程见下）：
  - 假设一个 Agent 任务 10 轮，每轮输入约 2000 token（无缓存）、输出约 150 token，合计输入 2 万、输出 1500 token。
  - 云侧费用（估算）：3.1 Flash-Lite：20000×0.25/1e6 + 1500×1.50/1e6 = $0.0050 + $0.00225 ≈ $0.0073；3.5 Flash-Lite（0.30/2.50）≈ $0.0098；3.1 Pro Preview（2.00/12.00）≈ $0.058。DeepSeek V3.2（二手报价 0.28/0.42，待核实）≈ $0.0062。
  - 端侧 decode 能耗（估算）：取 PowerInfer-2 论文中 llama.cpp 基线 0.672 J/token 作量级，1500 token ≈ 1.0 kJ ≈ 0.28 Wh；若电池 5000 mAh × 3.85 V ≈ 19.3 Wh（电池容量为假设），约占电量 1.5%。prefill 2 万 token 能耗此处未计，真实值要用仿真平台算，**待核实**。
  - 云侧能耗参照：Google 中位 prompt 0.24 Wh（不含网络与终端，口径与上不同）。
  - 结论：单任务云成本在 1 美分以内，端侧每任务耗电约 1% 量级；**收益不在成本，而在隐私、离线可用、时延确定性，代价在耗电、占内存、发热**。该结论为估算，需 S1 平台验证。

#### 2. 业界做法扫描

| 方案 | 年份 / 来源 | 原理 | 局限 |
|---|---|---|---|
| Hybrid LLM | ICLR 2024，arXiv 2404.14618 | 预测查询难度，路由小/大模型 | 只考虑质量与云调用，不含端侧能耗 |
| RouteLLM | ICLR 2025，arXiv 2406.18665 | 偏好数据训练路由器 | 同上，面向强/弱云模型 |
| HybridFlow | ICML 2026，arXiv 2512.22137 | 子任务级路由，效用 = 收益 − 成本，预算自适应 | 端侧模型与度量待核实 |
| 端云投机解码 | TMLR 2025，arXiv 2505.21594；SPADE arXiv 2608.13076 | 端侧起草、云端验证 | 实验台为 Jetson Nano，不是手机；通信时延敏感 |
| 端侧能效研究 | arXiv 2609.11940；arXiv 2607.05475 | 实测 J/token、分后端 | 机型未命名，预印本 |
| 云侧能耗披露 | Google，arXiv 2508.15734（2025-08） | 全栈计量 0.24 Wh/prompt | 不含网络与终端 |
| 真机评测 | BYTE，NeurIPS 2026 研讨会 | 真机采集电量/功耗/热 | 面向 GUI Agent，我们仅借方法 |
| 仿真器 | Vidur、LLMServingSim 2.0、GenZ、LLMCompass、LIFE | 见 1.2 表 | 无手机 SoC |

#### 3. 技术难点

**难点一：能耗不可观测，端云无法同口径比较**
- 难在哪：Perfetto 电池计数器给整机电流，ODPM 分轨能耗仅在部分机型可用（Android 10 引入，需专用硬件，多数量产机缺失），轨名和分辨率由厂商决定；云侧能耗又是全栈摊销。
- 怎么破：对「Agent 步骤」建立统一能耗账：端侧用电池计数器 / ODPM（有则用）+ 分阶段（prefill/decode/空闲/网络）建模；云侧取公开口径（如 0.24 Wh 中位 prompt）做参照并标注不含网络；网络能耗按流量和射频状态单独建模。放在仿真平台的功耗层。
- 关键突破：把能耗记账单位从「整机」下沉到「Agent 步骤 × 阶段」。

**难点二：仿真结果不可信，缺少校准闭环**
- 难在哪：现有仿真器在 GPU 上误差 1%–10%（LLMServingSim 2.0 报告 0.95%、Vidur <9%、LLMCompass 端到端 4.1%、GenZ 最大 geomean 5.82%），但手机有 DVFS、热降频、共享带宽、UFS 抖动，没有公开校准方法。
- 怎么破：分层校准——算子级用微基准校准 roofline 参数（峰值算力、有效带宽；PowerInfer-2 给出 7B 下 CPU 约 43.9 GB/s、NPU 约 56 GB/s 作量级对照）；系统级用真机跑标准负载，回归 TTFT/TPOT/功耗；热和 DVFS 用长时序（≥10 分钟）轨迹校准；每次平台升级必须复跑并给出误差报告。放在仿真平台的「模型—真机对照」模块。
- 关键突破：用真机轨迹持续回归仿真参数，并公布误差带。

**难点三：体验风险无统一指标，下沉可能「省了钱、坏了体验」**
- 难在哪：Agent 体验指标没有公开标准；检索只发现通用 Agent 评测指标（端到端延迟、每任务 token、每成功任务成本、P95），未找到 time-to-first-action 的正式定义。端侧推理占用内存会挤占前台应用，造成冷启动、掉帧。
- 怎么破：自定义并公开定义体验指标集（见下节「风险评估」），把「端侧模型常驻内存」换算成前台应用冷启动退化和 lmkd/Jetsam 回收次数，与 KT1/KT2/KT3 联动；在决策模型里设体验红线作硬约束，不是加权项。
- 关键突破：体验红线作硬约束，超线直接否决下沉。

#### 4. 机制架构（感知 / 建模 → 决策 → 执行 → 反馈）

- 感知 / 建模：
  - 负载：Agent trace 回放器（轮数、每轮输入/输出 token、前缀复用率、工具类型与延迟分布）；公开参考为 2605.26297、TraceLab（数值待核实）。
  - 终端模型：SoC 算子延迟表、带宽争抢模型、功耗模型（阶段 × 频点）、热模型、UFS 模型、内存压力模型（接入 KT1/KT2/KT3 的状态）。
  - 云模型：价格表（含缓存折扣）、网络 RTT 与抖动、云侧时延分布。
- 决策：下沉评估引擎，输入步骤特征，输出「留云 / 下沉 / 混合（投机解码或路由）」及置信区间。
- 执行：平台批量运行方案对比；上线形态为在线路由器，沿用同一决策函数（仅参数不同）。
- 反馈：真机采集（Perfetto 电池/ODPM、应用启动时延、掉帧、lmkd 事件）回灌校准；偏差超阈值触发重新校准或回退到云。

**决策模型（核心产出）**

对每个任务类 *k*（如「日程查询」「长文摘要」「多工具编排」），比较两种部署 `cloud` 与 `device`（或混合）。定义净收益：

`NB_k = ΔCost_k + λP·ΔPrivacy_k − λE·ΔEnergy_k − λM·ΔMem_k − λT·ΔLatPenalty_k − λR·ΔRisk_k`

硬约束（任一不满足，直接不下沉）：体验红线（TTFT、P95 步延迟、前台掉帧率、冷启动退化、温度）、隐私等级要求、质量下限（任务成功率不低于云基线的某比例）。

| 因素 | 记号 | 量化方法 | 数据来源与口径 |
|---|---|---|---|
| 时延 | ΔLat | 端到端任务时延 P50/P95；端：TTFT + 输出 token×TPOT + 工具；云：RTT + 排队 + 云 TTFT/TPOT。只对超出「感知阈值」的部分罚分：max(0, Lat − slack) | 仿真输出，真机回归；slack 由用户研究定，**待核实** |
| 能耗 | ΔEnergy | 每任务 Wh 与「电量百分点」；端：Σ(阶段功率×时长) − 空闲基线；云不计入手机账，但网络射频能耗计入端 | 电池计数器 / ODPM；端侧 J/token 用 PowerInfer-2 等量级对照 |
| 云成本 | ΔCost | 每任务美元 = Σ(输入×价格_in + 输出×价格_out − 缓存折扣)，乘以日活与每日任务数，得年度总额 | 价格页注明模型与日期（见 S1-T3）；2027-01 Flash 档涨价需按分段计价 |
| 隐私 | ΔPrivacy | 分级而非货币化：数据敏感等级（L0 公开 / L1 个人 / L2 敏感）；L2 且云方案需出域则为硬约束；其余按「出域数据量×敏感等级」打分 | 内部合规分级；公开参照：Apple Private Cloud Compute 的服务端模式作为对照（见 Apple 技术报告 arXiv 2507.13575） |
| 端侧内存占用 | ΔMem | 常驻 GB（权重 + KV）×驻留时长；换算为「前台应用冷启动退化 ms」和「被回收进程数/小时」；也可折算为 DRAM 成本（$/GB，BOM），但 2025–2026 DRAM 价格本模块未检索，**待与 M2 对齐** | 与 KT1/KT2/KT3 的仿真联动 |
| 体验风险 | ΔRisk | 发热降频概率（持续推理 >N 分钟后 TPOT 下降比例）、掉帧增量、误判后回退代价、失败率差；以概率×代价计 | 真机长时序；BYTE 提示热累积与非线性能耗 |

权重 λ 的确定：按产品形态给三档预设（成本优先 / 体验优先 / 隐私优先），在平台上做灵敏度扫描，输出「决策翻转点」（例如云价格涨多少下沉才划算）。这一步比给定单个权重更可信。

**风险评估（题目要求的三项）**

1. **真机可观测性与体验指标**
   - 可观测性现状：Perfetto 电池计数器（Android 10 起，依赖 IHealth HAL，分辨率依厂商）和 ODPM（IPowerStats HAL，需专用硬件，多数量产机缺失）；配置项为 `android.power` 数据源的 `battery_counters` 与 `collect_power_rails`；USB 供电会使电流读数失真，需隔离供电的实验方案。鸿蒙和 iOS 的对应工具本模块**未找到公开资料**。
   - 建议指标集（我们的定义，非行业标准）：
     - 响应类：TTFT（用户发起到首 token）、time-to-first-action（用户发起到首个工具调用开始，**自定义**）、任务完成时延 P50/P95、步间停顿。
     - 质量类：任务成功率、工具调用正确率、与云基线的成功率比。
     - 资源类：每任务 Wh、电量百分点、峰值/稳态温度、TPOT 降幅。
     - 干扰类：叠加场景下前台应用冷启动时延增量、掉帧率增量、被回收进程数。
     - 经济类：每成功任务云成本（与通用评测口径一致）。
2. **标准负载集**
   - 建议三层：算子/模型层（MLPerf Mobile v6.0 的 Llama 3.2 1B/3B 与 3.1 8B，注意其口径只报聚合吞吐，待核实）；Agent 轨迹层（自建：把公开的 ReAct / 多轮工具 trace 的轮数、token、前缀复用、工具延迟分布参数化后回放，参考 2605.26297、TraceLab，数值待核实原文）；叠加场景层（与 KT1 联动：Agent 运行同时拉起 3–5 个典型应用）。
   - AndroidWorld（116 个任务、20 个应用，按检索摘要）和 BYTE 只借其「步数分布与评测框架思路」，我们不做 GUI Agent。
3. **仿真校准**
   - 校准分级见难点二；验收口径建议：算子级误差 ≤10%（对标 LLMCompass 10.4%）、端到端 TTFT/TPOT ≤10%（对标 Vidur <9%）、功耗 ≤15%（无公开手机侧先例，此阈值为我们的**目标假设**）。
   - 主要风险：热降频和后台争抢使真机方差大，需要每个场景多次重复并报告置信区间；仿真器若只在空载校准，叠加场景会系统性偏乐观。

#### 5. 目标与度量

| 指标 | 基线 | 目标 | 测试条件 / 依据 |
|---|---|---|---|
| 仿真 TTFT/TPOT 误差 | 无手机基线 | ≤10%（区间 8–15%） | 3 种机型 × 3 种模型规模；对标 Vidur <9%、LLMServingSim 2.0 0.95%（GPU） |
| 仿真功耗误差 | 无 | ≤15% | 电池计数器 / ODPM 对照；目标假设 |
| 决策覆盖 | 无 | 覆盖 ≥6 类典型任务，输出下沉建议与翻转点 | 与产品确认任务类 |
| 单次方案评估耗时 | 真机跑一轮数小时 | ≤10 分钟/配置 | 对标 LLMServingSim 2.0 约 10 分钟 |
| 估算收益 | 无 | 待仿真后给出（占位） | 不在本阶段承诺数值 |

#### 6. 风险与待核实

- 手机 SoC 仿真无公开先例，校准成本和误差可能高于 GPU 场景。
- 能耗数据多来自 2026 预印本，机型未命名，数值不可直接引用（待核实）。
- 云价格会变（Flash 档 2027-01 涨价；2.5 系列 2026-12 起被路由），成本结论要带日期。
- 厂商自有云推理成本（华为、荣耀、小米等）**未找到公开资料**。
- 鸿蒙 / iOS 的功耗观测工具**未找到公开资料**。
- LLMServingSim 2.0 的论文录用状态（ISPASS 2026 / CAL 2025）来自仓库自述，需核对会议官网。
- DRAM 价格（端侧内存折算）本模块未检索，需与 M2 对齐。

#### 7. PPT 素材卡

**挑战**
1. 无统一账本：端云能耗口径不同，Google 0.24 Wh/prompt 不含网络与终端。
2. 仿真无手机先例：现有仿真器误差 1–10% 但全在 GPU，手机无公开模型。
3. 体验风险难量化：单任务云成本约 $0.007，端侧耗电约 1%，坏体验才是代价（估算）。

**目标**：建立手机侧 Agent 云转端的仿真评估平台，用统一决策模型判断哪些步骤值得下沉（≤44 字）
**量化目标**：TTFT/TPOT 误差≤10%（≤24 字）

**技术难题**
1. 统一能耗记账
   - 观测缺口：ODPM 仅部分机型可用，整机电流难以拆分。
   - 口径对齐：云侧能耗不含网络和终端，需单独建模。
   - 关键突破：按步骤和阶段记账
2. 手机仿真校准
   - 算子校准：微基准标定有效带宽与峰值算力。
   - 热与降频：长时序轨迹回归 DVFS 与热模型。
   - 关键突破：真机回灌持续校准
3. 体验红线决策
   - 硬约束：TTFT、掉帧、冷启动退化超线则否决下沉。
   - 翻转点：扫描权重，输出价格与能耗的决策翻转点。
   - 关键突破：红线硬约束+翻转点

**架构四段**
- 感知 / 建模：Trace 回放、SoC 模型、云价格表、内存压力
- 决策：下沉评估、翻转点扫描、红线校验
- 执行：批量仿真、在线路由、混合解码
- 反馈：电池计数器、ODPM、误差报告

---

### S2 单个 Agent 内部并行化方案的导出与仿真验证

#### 1. 要解决的问题

- 现状：单 Agent 串行执行「LLM 生成 → 工具调用 → LLM 生成」。云上数据显示：编码 Agent 单次生成约 13 s、单次工具调用约 18 s（TraceLab，二手摘要，待核实）；LLM 推理占总时间 71–98%（2605.26297 二手摘要，待核实）。端侧 decode 受带宽限制，NPU 算力在 decode 阶段大量闲置（sd.npu 称验证阶段闲置超 70%，二手摘要，待核实）。
- 代价：串行使端侧任务完成时延等于所有步骤之和；同时 NPU/GPU/CPU 间的流水气泡造成能耗浪费（NPU 研究：CPU 调频单独可降能耗最多 39.7%，arXiv 2607.05475）。具体到我们场景的串行代价**需用 S1 平台测量**。

#### 2. 业界做法扫描

| 方案 | 年份 / 来源 | 原理 | 局限 |
|---|---|---|---|
| LLMCompiler | ICML 2024，arXiv 2312.04511 | 规划 DAG，并行执行无依赖函数调用；延迟最高 3.7 倍 | 云端；依赖规划器输出质量；无副作用控制 |
| 并行函数调用（OpenAI 等） | 2023 年起 | 模型一次输出多个调用 | 靠模型自行判断，无依赖分析 |
| Skeleton-of-Thought | ICLR 2024，arXiv 2307.15337 | 骨架 + 并行展开；最高约 2.39 倍 | 仅适合可分解问题，质量可能下降 |
| PASTE | arXiv 2603.18897（2026） | 预测后续工具并投机执行，结果隔离；完成时间降 43.5% | 需稳定工具模式；GPU 服务场景 |
| Speculative Actions | arXiv 2510.04371（2025-10） | 快模型预测下一动作；最高 20% 延迟降低 | 预测准确率最高 55% |
| 端侧并行测试时扩展 | arXiv 2509.23324（2025-09） | 在 NPU 空闲算力上并行多路采样 | 仅预印本；服务于质量提升而非时延 |
| 端侧投机解码 + NPU 协同 | arXiv 2510.15312（待核实版本） | 多草稿并行验证，decode 转向计算受限 | 图切换开销最高占 decode 延迟 29%（二手） |
| 端侧稀疏 / 异构调度 | PowerInfer-2，arXiv 2406.06282 | NPU/CPU 协同、神经元簇流水 | 目标是大模型装得下，非 Agent 并行 |

#### 3. 技术难点

**难点一：手机上哪些工具能安全并行 / 投机**
- 难在哪：手机工具多为有副作用的系统操作（发短信、设闹钟、调起应用）、需权限与用户确认，且依赖前台状态；云上方案默认工具无副作用。
- 怎么破：对工具声明增加「语义标签」（只读 / 幂等 / 可回滚 / 有副作用 / 需确认）；并行与投机只对前三类开放，其余在 LLM 确认后串行；PASTE 的「结果隔离到确认」机制对应落在工具运行时层。
- 关键突破：工具元数据驱动并行许可。

**难点二：共享带宽下，流水与合批的收益是否还在**
- 难在哪：decode 受带宽限制，合批/投机利用的是闲置算力，但 CPU/GPU/NPU 共享 LPDDR（PowerInfer-2 实测并用时约 59.6 GB/s，仅比 NPU 单用 56 GB/s 高约 6%）；工具执行、UI 渲染、其他应用也在争带宽，收益可能被吃掉；合批还增加 KV 占用。
- 怎么破：仿真平台里建带宽争抢模型，扫描「并行度 × 批大小 × 背景流量」，输出收益曲线和拐点；运行时按拐点给出并行度上限，并与 KT2 的 KV 配额联动。
- 关键突破：带宽争抢感知的并行度上限。

**难点三：并行方案「导出」——从 Agent 轨迹自动得到可验证的并行计划**
- 难在哪：Agent 的依赖关系隐含在对话里，LLMCompiler 靠 LLM 规划，错误会造成错序；不同任务并行潜力不同。
- 怎么破：用 S1 的 trace 回放器，从历史轨迹抽取工具调用依赖图（数据依赖、顺序依赖），枚举候选并行计划（并行调用、子任务拆分、投机、CPU/GPU/NPU 流水），在仿真平台里评估时延、能耗、内存，筛出帕累托前沿后固化为策略模板。
- 关键突破：轨迹→依赖图→仿真验证→策略模板的闭环。

#### 4. 机制架构（感知 / 建模 → 决策 → 执行 → 反馈）

- 感知 / 建模：Agent 轨迹采集与依赖图抽取；工具语义标签库；带宽/算力/功耗/热模型（复用 S1）；NPU 空闲算力画像。
- 决策：并行计划生成器（并行调用、子任务拆分、投机执行、流水映射）；仿真筛选（时延 / 能耗 / 内存帕累托）；并行度上限计算。
- 执行：工具运行时（并发调度、投机隔离、回滚）；推理侧合批 / 投机解码；CPU/GPU/NPU 流水编排。
- 反馈：投机命中率、回滚率、实际时延与仿真偏差、带宽争抢事件；回灌策略模板与仿真参数。

#### 5. 目标与度量

| 指标 | 基线 | 目标 | 测试条件 / 依据 |
|---|---|---|---|
| 多工具任务端到端时延 | 串行执行 | 降 20–40% | 区间依据：Speculative Actions 最高 20%、PASTE 43.5%（云上），端侧受带宽约束取区间；目标假设 |
| 投机命中率 | 无 | ≥50% | 依据：Speculative Actions 最高 55%（上限，作参照） |
| decode 合批吞吐 | batch=1 | 待仿真确定 | 公开资料只有定性结论（亚线性增长），无可引用倍数，**待核实** |
| 能耗增量 | 串行 | ≤+10%（时延降低时） | 目标假设，由 S1 功耗模型验证 |
| 仿真—真机偏差 | 无 | ≤10% | 同 S1 |

#### 6. 风险与待核实

- 云上收益（3.7 倍、43.5% 等）不能直接外推到端侧，端侧数据未找到公开资料。
- PASTE 不同版本数字不一致（43.5% 与 48.5%），引用前核对原文。
- 手机 NPU 批大小—吞吐的具体倍数未取得；2509.23324 与 2510.15312 数字为摘要/二手，待核实。
- 投机执行的副作用与隐私风险（预取读取敏感数据）需要策略层约束。
- 副作用工具占比、典型手机 Agent 工具延迟分布：**未找到公开资料**，需自建测量。

#### 7. PPT 素材卡

**挑战**
1. 串行等待：生成与工具串行，云上单次工具调用约 18 s（二手）。
2. 算力闲置：decode 受带宽限，NPU 验证阶段闲置超 70%（二手）。
3. 带宽共享：CPU+NPU 并用仅 59.6 GB/s，比 NPU 单用高约 6%。

**目标**：在单 Agent 内部导出并仿真验证并行方案，缩短端侧多工具任务时延（≤44 字）
**量化目标**：时延降 20–40%（≤24 字）

**技术难题**
1. 工具并行许可
   - 语义标签：声明只读、幂等、可回滚、有副作用、需确认。
   - 结果隔离：投机结果在 LLM 确认前不落地。
   - 关键突破：元数据驱动并行许可
2. 带宽争抢下的收益
   - 争抢建模：扫描并行度、批大小、背景流量。
   - 并行度上限：按收益拐点限制并行路数。
   - 关键突破：带宽感知并行上限
3. 并行方案自动导出
   - 依赖图：从轨迹抽取数据依赖与顺序依赖。
   - 仿真筛选：时延、能耗、内存帕累托筛选后固化模板。
   - 关键突破：轨迹到模板的闭环

**架构四段**
- 感知 / 建模：轨迹依赖图、工具标签、带宽模型
- 决策：计划生成、仿真筛选、并行度上限
- 执行：工具并发、投机隔离、合批、流水编排
- 反馈：命中率、回滚率、仿真偏差

---

## 参考资料

| 编号 | 标题 | URL | 日期 |
|---|---|---|---|
| R1 | Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing（ICLR 2024） | https://arxiv.org/abs/2404.14618 | 2024-04-22 |
| R2 | RouteLLM: Learning to Route LLMs from Preference Data（ICLR 2025） | https://arxiv.org/abs/2406.18665 | 2024（ICLR 2025） |
| R3 | HybridFlow: Resource-Adaptive Subtask Routing for Efficient Edge-Cloud LLM Inference（ICML 2026） | https://arxiv.org/abs/2512.22137 | 2025-12-11（v5 2026-08-10） |
| R4 | Fast and Cost-effective Speculative Edge-Cloud Decoding with Early Exits（TMLR 2025） | https://arxiv.org/abs/2505.21594 | 2025-05 |
| R5 | SPADE: Speculative Decoding for Precise and Low Cost Distributed Edge Cloud Inference | https://arxiv.org/pdf/2608.13076 | 2026-08（仅读摘要） |
| R6 | The Battery Price of edge AI（Guégain & Coignion） | https://arxiv.org/abs/2609.11940 | 2026-07-10 |
| R7 | Is Your NPU Ready for LLMs?（SIGMETRICS 2027） | https://arxiv.org/abs/2607.05475 | 2026-07-06（v2 2026-10-16） |
| R8 | Measuring the environmental impact of delivering AI at Google Scale | https://arxiv.org/abs/2508.15734（经检索结果 web3.arxiv.org 链接，未直接打开） | 2025-08 |
| R9 | Google AI Studio / Gemini API 价格页 | https://aistudio.google.com/docs/pricing（由 ai.google.dev/gemini-api/docs/pricing 重定向） | 抓取日 2026-11-03 |
| R10 | DeepSeek V3.2 价格（二手聚合） | https://pricepertoken.com/pricing-page/model/deepseek-deepseek-v3.2 | 2026（未核对官方页） |
| R11 | Agentic AI Workload Characteristics（IISWC 2026） | https://arxiv.org/abs/2605.26297 | 2026-05-25（v2 2026-09-21） |
| R12 | TraceLab: Characterizing Coding Agent Workloads for LLM Serving | https://syfi.cs.washington.edu/blog/2026-06-25-tracelab/ | 2026-06-25（仅读检索摘要） |
| R13 | Beyond the Emulator: Bridging the Sim-to-Real Gap in Mobile Agent Benchmarking（BYTE） | https://neurips.cc/virtual/2026/170091 | NeurIPS 2026 |
| R14 | MLPerf Mobile v6.0 | https://mlcommons.org/2026/06/mlperf-mobile-v6/ | 2026-06（仅读检索摘要） |
| R15 | An LLM Compiler for Parallel Function Calling（ICML 2024）；代码 https://github.com/SqueezeAILab/LLMCompiler | https://arxiv.org/abs/2312.04511 | 2023-12 / 2024 |
| R16 | Skeleton-of-Thought（ICLR 2024） | https://arxiv.org/abs/2307.15337 | 2023-07 / 2024 |
| R17 | PASTE: Parallelizing Tool Execution and LLM Generation for Low-Latency Agent Serving | https://arxiv.org/abs/2603.18897 | 2026-03-19（v3 2026-06-16） |
| R18 | Speculative Actions: A Lossless Framework for Faster Agentic Systems | https://arxiv.org/abs/2510.04371 | 2025-10-05（v2 2026-04-23） |
| R19 | Optimizing Agentic Language Model Inference via Speculative Tool Calls | 二手评述 https://www.themoonlight.io/review/optimizing-agentic-language-model-inference-via-speculative-tool-calls | 2025（原文 arXiv 号未取得） |
| R20 | Scaling LLM Test-Time Compute with Mobile NPU on Smartphones | https://arxiv.org/abs/2509.23324 | 2025-09-27 |
| R21 | Accelerating Mobile Language Model via Speculative Decoding and NPU-Coordinated Execution（sd.npu） | https://arxiv.org/abs/2510.15312 | 2025-10 |
| R22 | PowerInfer-2: Fast Large Language Model Inference on a Smartphone | https://arxiv.org/abs/2406.06282 | 2024-06 |
| R23 | Vidur（MLSys 2024）；代码 https://github.com/microsoft/vidur | https://arxiv.org/abs/2405.05465 | 2024-05 |
| R24 | LLMServingSim 2.0；代码 https://github.com/casys-kaist/LLMServingSim | https://arxiv.org/abs/2602.23036 | 2026-02-26（v2 2026-03-23） |
| R25 | GenZ（Demystifying AI Platform Design for Distributed Inference of Next-Generation LLM models） | https://arxiv.org/abs/2406.01698 | 2024-06 |
| R26 | LLMCompass（ISCA 2024）；代码 https://github.com/PrincetonUniversity/LLMCompass | https://arxiv.org/abs/2312.03134 | 2023-12 / 2024 |
| R27 | LIFE: Forecasting LLM Inference Performance via Hardware-Agnostic Analytical Modeling | https://arxiv.org/abs/2508.00904 | 2025-07-29 |
| R28 | RooflineBench | https://arxiv.org/pdf/2602.11506 | 2026（仅读检索摘要） |
| R29 | Perfetto: Power data sources（电池计数器与 ODPM） | https://perfetto.dev/docs/data-sources/battery-counters | 抓取日 2026-11-03 |
| R30 | Apple Intelligence Foundation Language Models Tech Report 2025 | https://arxiv.org/abs/2507.13575 | 2025-07 |

## 待核实清单

1. LLMServingSim 2.0 的会议录用状态（仓库称 ISPASS 2026 与 CAL 2025，arXiv 页未标会议）；GenZ、LLMCompass 的许可与仓库地址（来自检索结果，未打开仓库）。
2. LIFE（2508.00904）的误差、是否有开源实现。
3. PASTE 数字（43.5% vs 48.5%）、2605.26297 与 TraceLab 的具体数值，需读原文。
4. 2609.11940、2607.05475 的机型、模型与绝对 J/token；端云「约 3 倍」的口径。
5. PowerInfer-2 的 0.672 / 0.257 J/token 对应设备与模型。
6. Gemini 价格页无更新日期，Flash 档 2027-01 涨价与 2026-12 路由变化按页面描述；DeepSeek 价格未核对官方页。
7. 手机 NPU 合批倍数（2509.23324、2510.15312）；sd.npu 各数字为二手摘要。
8. time-to-first-action 等 Agent 体验指标无公开标准，需内部定义并说明为自定义。
9. 鸿蒙、iOS 的功耗观测工具与可用性，厂商自有云推理成本：未找到公开资料。
10. Speculative Tool Calls（R19）原论文 arXiv 号与数字。
11. DRAM 价格与内存折算：与 M2 对齐。
12. 端云能耗对比的口径统一（0.24 Wh 为云侧全栈、不含网络与终端，不可与端侧 J/token 直接相除）。

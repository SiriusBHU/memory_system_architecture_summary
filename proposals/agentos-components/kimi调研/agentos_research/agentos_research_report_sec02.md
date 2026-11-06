# 第 2 章 推理框架与推理能力

本章综合维度调研 dim01（系统级模型服务与 NPU 调度）、dim02（端侧推理框架与推理加速）、dim03（端云路由与 LoRA 生态）三份报告，并按交叉验证结论（High 28 项 / Medium 35 项 / Low 14 项 / Conflict Zone 10 项，全报告口径）对置信度分级处理：High 级直接陈述；Medium/Low 级加限定语；Conflict Zone 双边呈现。所有量化论断均标注数值、单位、来源与日期；已被标记为虚构或错引的条目（如 dim10 "dmabuf memcg 上游 6.5 合入"、dim09 "Llama-3-8B KV 0.5MB/token"、AMemBench）本章不予采用。

## 2.1 技术谱系：六条路线

围绕"端侧推理如何组织"，2021–2026 年的工作与产业实践可归为六条相互交叉的路线：系统级模型服务、NPU 抽象、端侧框架、推理加速、端云路由、LoRA 生态。表 2-1 给出各路线的代表工作。

**表 2-1 推理框架与推理能力技术谱系（路线 × 代表工作 × 机构 × 时间 × 一句话贡献）**

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|---|
| 系统级模型服务 | AICore + Gemini Nano + ML Kit GenAI APIs | Google | 2023-12 首落地（Pixel 8 Pro），2025-05 对第三方开放 beta[^2-1^] | 模型由系统服务统一下载/加载/推理，多应用共享单实例，APK 不含权重，以前台限制与每应用配额换取资源可控[^2-1^][^2-2^] |
| 系统级模型服务 | Foundation Models framework（~3B 端侧模型） | Apple | 2025-06 发布，iOS 26 起可用[^2-3^] | Swift 原生 API 直调系统 3B 模型，guided generation + tool calling，无按次计费[^2-3^] |
| 系统级模型服务（学术先导） | M4: Mobile Foundation Model as Firmware | 北京邮电大学等 | MobiCom 2024[^2-4^] | 底座模型由 OS 与硬件共同管理、对 App 不可修改，以系统服务形式暴露，App 仅经 adapter 调用[^2-4^] |
| 系统级模型服务 | 小艺 + Pangu 端侧（HarmonyOS 7 宣称"入内核"） | 华为 | 2024-06（NEXT）至 2026-06（HDC 2026）[^2-5^] | 模型深度集成进系统并以 Agent/Skill 架构开放；"Pangu 6.0 入内核"为媒体转述口径，无技术出处，置信度低[^2-5^] |
| NPU 抽象 | Android NNAPI（已弃用） | Google + 厂商 | 2018 引入，2024 Android 15 deprecated[^2-6^] | 首个跨厂商 NPU 抽象；因厂商实现不均、跟不上 transformer 演进被弃，NN HAL 保留给 AICore 等系统服务[^2-6^][^2-7^] |
| NPU 抽象 | LiteRT CompiledModel + Accelerator.NPU（Qualcomm/MediaTek 一等支持） | Google + Qualcomm + MediaTek | 2025-05 起，2026-01 生产可用[^2-8^] | 单一 API 选定 NPU 后端，AOT+JIT 编译，失败回退 GPU/CPU，配套 AI Pack 模型分发[^2-8^] |
| NPU 抽象 | Android 17 `NpuManager` + NPU scheduling AIDL | Google（AOSP） | 2026（API 37）[^2-9^] | 首个 OS 级 NPU 调度控制面：UID/优先级/直接访问资格/工作回调；best-effort、无 SLO、@SystemApi 不对第三方开放（源码阅读转述，置信度中高）[^2-9^] |
| NPU 抽象 | HarmonyOS NNRt | 华为 / OpenHarmony | 2022 起[^2-10^] | 跨芯片推理运行时，共享内存零拷贝、优先级可配；仅 56 个算子、仅同步推理，并发性取决于底层驱动[^2-10^] |
| 端侧框架 | llama.cpp / GGUF | 社区（ggml-org） | 2023 起[^2-11^] | 端侧推理事实标准：单文件格式 + 多档量化 + mmap 惰性加载，后端覆盖 CPU/CUDA/Metal/Vulkan/Hexagon 等[^2-11^] |
| 端侧框架 | ExecuTorch | Meta / PyTorch Foundation（Arm、Apple、Qualcomm 共建） | 1.0 GA 2025-10，MLSys 2026 论文[^2-12^] | PyTorch 原生端侧运行时，AOT 导出 + 12+ 硬件后端 delegate，50KB 级基础运行时[^2-12^] |
| 端侧框架 | LiteRT-LM；MNN/MNN-LLM；MLC-LLM | Google / 阿里巴巴 / MLC.AI | 2024–2026[^2-13^] | Google 官方"多特性共享单一底座 + 轻量 LoRA"栈；MNN-LLM 移动端 prefill 领先；MLC-LLM 内置端侧唯一类 vLLM 分页 KV[^2-13^] |
| 推理加速（量化） | GPTQ → AWQ → QuaRot/SpinQuant → QServe（W4A8KV4）；BitNet b1.58 2B4T | ISTA / MIT HAN Lab / Microsoft 等 | 2022–2025[^2-14^] | 权重 4-bit 成为端侧默认交付形态，主战场转向 KV cache 3–4 bit 低比特化；1.58-bit 从头训练模型 CPU 可跑[^2-14^][^2-15^] |
| 推理加速（投机解码） | Medusa → EAGLE-2/3；Apple AFM 48M draft + 3.18B base 双模型 | Princeton/SafeAILab/Apple | 2024–2025[^2-16^] | 自草稿投机解码无损加速；llama.cpp 2026 年已内置 6 类投机实现，成为运行时一等特性[^2-16^][^2-17^] |
| 推理加速（NPU 系统） | llm.npu；PowerInfer-2；LLM in a flash | 北大 / SJTU / Apple | ASPLOS 2025 / 2024[^2-18^] | NPU 中心端侧 LLM 系统：prefill 较 CPU 基线快 7.3–18.4×；flash-DRAM 分层加载使手机上可跑 47B 级模型[^2-18^] |
| 端云路由 | Apple Private Cloud Compute（PCC）+ System Orchestrator | Apple | 2024-06 发布，2026-06 扩展第三方机房[^2-19^] | 唯一大规模落地的"可验证隐私"云承接：无状态计算 + 签名镜像 + 透明日志 + 远程证明[^2-19^] |
| 端云路由 | Firebase AI Logic Hybrid Inference | Google | 2026-04 Android 上线，2026-05 扩展 iOS[^2-20^] | 四档规则式端云路由（PREFER/ONLY_ON_DEVICE/IN_CLOUD），官方自述为"initial solution"[^2-20^] |
| 端云路由 | NVIDIA OpenShell privacy router | NVIDIA | 2026-03 随 NemoClaw 首次亮相，2026-09-28 作为 Open Agent Safety Platform 正式发布[^2-21^] | 声明式 YAML 策略（隐私/成本）路由，deny-by-default，凭证剥离 + header 白名单，Apache 2.0 开源[^2-21^] |
| 端云路由（学术） | RouteLLM；MinionS；CITER/CE-CoLLM | LMSYS/Stanford 等 | 2024–2025[^2-22^] | 学习式请求级路由省 85% 成本；任务分解协作成本降 5.7× 且恢复 97.9% 质量；token 级置信度路由[^2-22^] |
| LoRA 生态 | LoRA；Punica（SGMV）；S-LoRA（Unified Paging） | Microsoft / 多机构 | ICLR 2022 / MLSys 2024[^2-23^] | 冻结基座 + 低秩适配；跨 adapter 混合批处理（吞吐 12×、+2ms/token）；adapter 权重与 KV cache 统一分页[^2-23^] |
| LoRA 生态（端侧） | Apple AFM 可换 adapter；EdgeLoRA；MobiLoRA | Apple / Univ. of Maryland / 东南大学·荣耀 | 2024–2025[^2-24^] | 系统级 LoRA 热插拔量产先例；端侧多租户 LoRA serving 吞吐 2–4× llama.cpp；跨 adapter KV 复用 TTFT 最高降 81.3%[^2-24^][^2-25^] |

表 2-1 显示三条结构性事实。其一，"模型即系统服务"已从学术设想（M4，MobiCom 2024）落地为两大平台的事实标准，华为以更激进但缺乏技术级出处的路径跟进；其二，NPU 抽象的主导权经历了"OS 内算子级抽象（NNAPI，失败）→ 框架级抽象（LiteRT/ONNX Runtime，当前主线）→ OS 级调度控制面（Android 17，刚起步）"的三次迁移，说明跨厂商抽象收敛在框架层而非内核层；其三，LoRA 从训练技术演变为系统对象——服务端（vLLM/SGLang）、OS（Apple adapter）、芯片（Qualcomm 白皮书、联发科 LoRA Fusion 2.0）三层均出现独立先例[^2-26^]，多方独立竞争者收敛到同一选择：adapter 是基座模型与硬件之间的定制层。

## 2.2 端侧推理栈分层图

综合 dim01 的分层素材，端侧推理栈可划分为五层，各层玩家与开放程度见表 2-2（开放度 ●=开放，○=封闭，按文档/源码可得性、第三方可编程性综合评定）。

**表 2-2 端侧推理栈分层：玩家与开放程度**

| 层 | 主要玩家 | 开放程度 | 关键约束 |
|---|---|---|---|
| 应用层 | Android：ML Kit GenAI APIs（beta）；iOS：Foundation Models framework；HarmonyOS：小艺 Skill/MCP 接入 | ●●○○ | 任务级 API 开放；模型选择、版本、调度均不可控；AICore 仅前台可用且有配额[^2-2^] |
| 系统服务层 | Android AICore（APEX 包、Play 分发、共享实例）；Android 17 NpuManager（@SystemApi、best-effort）；Apple Intelligence 系统进程（SystemLanguageModel）；华为小艺 + Pangu | ●○○○ | 三家均"开放调用、封闭调度"；Apple 不公开任何数值化配额[^2-27^] |
| 框架/运行时层 | LiteRT（+Qualcomm/MediaTek Accelerator）、ONNX Runtime（QNN EP / Neuron EP）、ExecuTorch、llama.cpp、MNN；已弃用：NNAPI（HAL 保留）；华为 NNRt + MindSpore Lite | ●●●○ | 开放度最高的一层，跨厂商抽象事实上的收敛点；但算子覆盖与性能 per-SoC 不均（LiteRT QNN 支持 90 算子，72 个基准模型中 64 个可全量卸载 NPU，Google 官方博客，2025-11-24）[^2-8^] |
| HAL/驱动层 | Android NN HAL（AIDL，保留）；Qualcomm FastRPC→HTP（8 级 context priority、性能档位、ION/SMMU 零拷贝）；MediaTek Neuron runtime（离线编译器 ncc-tflite 在伙伴注册墙后） | ●●○○ | 高通 QNN 对注册开发者开放；联发科编译器封闭；调度逻辑在固件内黑盒[^2-28^] |
| 芯片层 | Qualcomm Hexagon HTP（仅 INT8/INT16）；MediaTek MDLA+VPU；Apple ANE（固定功能、权重编译期烘焙）；华为麒麟 NPU | ●○○○ | 均无公开的虚拟化/多租户/抢占硬件接口；ANE 完全不开放直接编程；ANE 的 ~32MB SRAM 预算与"溢出性能降约 30%"系单源逆向数据（arXiv 2603.06728，2026-03），非 Apple 官方口径，置信度中[^2-29^] |

表 2-2 的核心读法是"开放度倒挂"：越靠近芯片越封闭，唯一高度开放的框架层因此成为所有跨厂商诉求的汇聚点——这解释了 NNAPI 失败后 Google 转而与 Qualcomm/MediaTek 共建 LiteRT Accelerator 的战略选择。同时注意两个层的制度性变化：系统服务层在 2026 年出现了首个 OS 级 NPU 调度控制面（Android 17 NpuManager），说明"NPU 需要调度"已成平台共识，但其 best-effort 语义与 @SystemApi 封闭性表明平台无意把调度能力交给第三方；芯片层则没有任何厂商提供多租户或抢占接口，学术工作 V10（ISCA 2023，硬件辅助算子级多租户，吞吐 1.57×、尾延迟降 1.74×、面积开销 <0.03%）[^2-30^]证明收益可观但需硬件配合，短期内不会出现在商用 SoC 上。

## 2.3 关键数据

本节汇集与本章论断直接相关且有出处的量化指标，分三组陈述（表 2-3 至表 2-5）。

**表 2-3 系统级模型服务：配额、限制与模型形态**

| 指标 | 数值 | 来源与日期 | 置信度 |
|---|---|---|---|
| AICore 前台限制 | 非 top foreground app（含 foreground service）调用 GenAI API 返回 `ErrorCode.BACKGROUND_USE_BLOCKED` | ML Kit 官方文档（经 Capawesome 逐字引用），2026-09-29[^2-2^] | High |
| AICore 配额错误码 | 短时超配额 → `ErrorCode.BUSY`；长周期超配额 → `ErrorCode.PER_APP_BATTERY_USE_QUOTA_EXCEEDED` | 同上[^2-2^] | High |
| ML Kit Prompt API 输入上限 | <4,000 token（约 3,000 英文单词）；>256 token 输出场景不建议 | 官方文档（经插件文档逐字引用），2026-07[^2-2^] | High |
| ML Kit GenAI APIs 成熟度 | beta，"is not subject to any SLA or deprecation policy" | WinBuzzer 引官方文档，2025-05-19[^2-1^] | High |
| Apple Foundation Models 配额 | Apple 未公开任何数值化配额/速率限制，仅存在可用性三态（not eligible / not enabled / model not ready） | Apple 文档与开发者实测综述，2025-06-28[^2-27^] | High（对"未公开"这一事实） |
| Foundation Models 上下文窗口 | 4,096 token（WWDC25/iOS 26）；WWDC26 示例达 8,192 token | 开发者实测 2025-06；slash-digital 查官方文档 2026-09-26[^2-27^] | High / Medium |
| Gemini Nano v3 内存门槛 | 需 ≥12GB RAM 旗舰机 | byteiota（二手），2026-05-19[^2-31^] | Medium |
| HarmonyOS AI 子系统调用量 | 20+ 项开放能力，日调用 36.8 亿次 | HDC 2026 报道（firecat 2026-06-14；Pandaily 2026-08-28 独立确认）[^2-5^] | High |
| AFM 端侧模型 | ~3B 参数；2024 报告：平均 <4 bit/权重；2025 报告：2-bit QAT + KV-reuse 双段架构 + 48M draft 投机解码 | Apple 技术报告 arXiv 2407.21075（2024-07-29）/ 2507.13575（2025-07）[^2-24^][^2-32^] | High |

表 2-3 呈现一个值得注意的非对称：Google 对平台约束完全透明（三个错误码逐字公开、输入上限明码标注），Apple 则完全不公开数值化配额——前者让开发者可做容量规划，后者把容量规划变成实验问题。但两者共享同一控制语义：前台独占 + 配额熔断 + 可用性降级。这说明"共享底座模型 + 硬降级面"不是某一家的取舍，而是平台把 LLM 纳入系统服务时的结构性代价；任何依赖平台托管模型的应用层设计都必须把 BUSY/不可用状态作为常规分支而非异常处理。

**表 2-4 AFM LoRA adapter 双口径（Conflict Zone C1 裁决结果：两者皆真、指代不同，须分开标注）**

| 口径 | rank | 体积 | 出处 | 置信度 |
|---|---|---|---|---|
| 2024 官方技术报告（accuracy-recovery/功能 adapter） | 16 | 数十 MB（16-bit 表示），可动态加载/缓存/换出，"保证 OS 响应性" | Apple 技术报告 arXiv 2407.21075，2024-07-29[^2-24^] | High（官方原文核实） |
| 2025 出货模型/开发者工具包（`.fmadapter`，Background Assets 分发） | 32 | ~160MB/个 | 第三方逆向（fguzman82 GitHub，2025-06）+ gamut.so（2025-09-08），两处一致但均非 Apple 官方文档[^2-33^] | Medium |

表 2-4 的两行不是误差，而是两套不同语义的并存：rank-16/数十 MB 是 Apple 2024 年官方技术报告中"精度恢复 + 功能特化"adapter 的口径；rank-32/~160MB 是 2025 年出货模型与开发者训练工具包（`.fmadapter`）的第三方逆向口径。交叉验证裁决（C1）要求二者分开标注，不得混写为单一数字。对系统设计的含义是：端侧 LoRA 的内存预算应按"单 adapter 数十至 160MB、多 adapter 常驻需分页池"规划，且 adapter 与基座模型版本绑定（基座升级须重训），版本治理是热插拔机制的前置条件。

**表 2-5 推理加速：量化、投机解码与 NPU 端侧指标**

| 指标 | 数值 | 来源与日期 | 置信度 |
|---|---|---|---|
| LiteRT Gemma-3n E2B @ Dimensity 9500 | prefill >1,600 tok/s、decode 28 tok/s @4K 上下文；LLM 吞吐 12× CPU / 10× GPU | Google developers blog（2025-12-08，经 MarkTechPost 2025-12-09 转述）[^2-34^] | High（注意系厂商基准） |
| LiteRT QNN Accelerator：FastVLM-0.5B @ Snapdragon 8 Elite Gen 5 | TTFT 0.12s、prefill >11,000 tok/s、decode >100 tok/s | Google 官方博客，2025-11-24（经 yomu.fyi 转述）[^2-8^] | Medium-High（厂商宣称值；芯片代际已按 C9 裁决更正为 8 Elite Gen 5） |
| NPU"prefill 强、decode 弱" | Qwen2.5-1.5B NPU(GENIE) prefill 1,213–1,464 tok/s，decode 仅 20.7–23.1 tok/s，低于 llama.cpp GPU decode（最高 64.4 tok/s） | 四款手机交叉实测，arXiv 2607.05475，2026-07[^2-35^] | Low（来源编号未能独立核实，结论以下两行 High 证据为准） |
| ExecuTorch MLSys 2026 基准（Galaxy S25 Ultra） | Llama-3.2-1B prefill：QNN 2,813–2,977 tok/s vs XNNPACK 525–529 tok/s（NPU prefill 优势 ~5.5×，decode 反而低于 CPU） | MLSys 2026 论文原文[^2-12^] | High |
| llm.npu（ASPLOS 2025） | prefill 较 CPU 基线快 7.3–18.4×，10 亿级模型 prefill 首破 1,000 tok/s | 论文原文[^2-18^] | High |
| NPU vs CPU 性能倍数 | 理论峰值"最高 100× CPU"（LiteRT 官方）/ 发布会口径 25×（I/O 2025 转述）/ 特定模型实测 12×（Gemma-3n @ D9500）并存 | C5 裁决：领域内口径混乱，引用必须带场景限定[^2-8^][^2-34^] | Conflict（已裁决为口径差异） |
| KV cache 量化（TurboQuant 落地 MNN） | Qwen3-4B @8K 上下文 KV 约 2GB（FP16）；压至 3–4 bit 省内存 30–60% | MNN GitHub Discussion #4351，2026-04-07[^2-15^] | Medium（源头单一，交叉换算一致） |
| 投机解码 | EAGLE-2 均值 2.5–3.5×（EMNLP 2024）；EAGLE-3 最高 6.5×（NeurIPS 2025）；Apple AFM 双模型整体 2–4×（第三方逆向口径，非官方数字） | 各论文/逆向分析[^2-16^][^2-33^] | Medium-High |
| BitNet b1.58 2B4T | 非嵌入权重 0.4GB；CPU 解码 29ms/token；能耗 0.028J/step | Microsoft 模型卡（Azure AI 目录），2026-04 页面[^2-14^] | High（官方卡） |
| PowerInfer-2 | 智能手机上 TurboSparse-Mixtral-47B 达 11.68 tok/s；加速比 v1 摘要 29.2×、v2 摘要 27.8×（C4 裁决为版本口径差异，建议引 v2） | arXiv 2406.06282 v2，2024-06[^2-18^] | High |
| LLM in a flash | 可运行 2× DRAM 容量模型；较朴素加载 CPU 4–5× / GPU 20–25× | Apple 论文 arXiv 2312.11514，2024-07-30[^2-18^] | High |
| 端侧 NPU KV 复用 | 较无复用 prefill 加速 1.5–5.4×，TTFT 降 40–60%；直接全量非前缀复用质量掉 ~30% | arXiv 2609.34727，2026-09-28[^2-36^] | High |
| S-LoRA / Punica（云端对照） | 单 A100-80GB 同时服务 2,000 adapter，吞吐 4× vLLM-packed / 30× HF PEFT；Punica SGMV 吞吐 12×、每 token +2ms | arXiv 2311.03285（2023-11）/ MLSys 2024[^2-23^] | High（多源核实） |
| EdgeLoRA | Jetson AGX Orin 上吞吐 2–4× llama.cpp；论文自述可服务千级 adapter（llama.cpp 约 50），数量差异达"several orders of magnitude" | arXiv 2507.01438（MobiSys 2025），2025-07-02[^2-25^] | High（吞吐倍数）；adapter 数量为论文自报口径，未独立复核（C7） |

三组数据合在一起勾勒出端侧推理的"能力包络"：系统服务层的能力上限被平台刻意压低（AICore 输入 4K token、前台独占、配额熔断；Apple 不公开配额但模型固定 3B/4K 上下文），而裸框架层在旗舰 NPU 上已能跑出 prefill 1,600–11,000 tok/s 的数字——两个层级的性能差可达一个数量级，但前者换来的是免携带权重与系统级资源共享。表 2-4 的双口径须特别注意：任何"AFM adapter 只有数十 MB"或"AFM adapter 有 160MB"的单一写法都是错的，二者分别对应 2024 官方报告与 2025 出货/工具包两套语义。表 2-5 中"prefill 强、decode 弱"的 NPU 分工特征被 ExecuTorch（MLSys 2026）与 llm.npu（ASPLOS 2025）两篇同行评议论文交叉证实（arXiv 2607.05475 提供同方向实测，但其编号未能独立核实，仅作旁证），已成为 2025–2026 端侧系统设计的基准事实，也直接引出 2.5 节的分阶段调度趋势。

## 2.4 端云路由方案对比

表 2-6 对比三套生产级端云路由方案，并以学术方案作参照。

**表 2-6 端云路由方案对比（方案 × 路由依据 × 隐私机制 × 延迟）**

| 方案 | 路由依据 | 决策粒度 | 隐私机制 | 延迟/成本数据 | 状态 |
|---|---|---|---|---|---|
| Apple 端侧 AFM ↔ PCC（2026-06 起扩展第三方机房） | 任务复杂度、隐私敏感度、延迟要求、设备热状态（WWDC26 System Orchestrator 口径，媒体转述，置信度中）；feature class / routing_hint | 请求级 | PCC：无状态计算、签名固件、Secure Enclave/Secure Boot、公开镜像 + 透明日志、远程证明、无特权访问（五大保证，Apple Security Research blog，2024-06-10）[^2-19^] | 端侧 TTFT <100ms；PCC 路径首 token 增加约 200–500ms（第三方开发者口径，2026，置信度中）[^2-37^]；PCC 32K 上下文、有日配额、需 entitlement（WWDC26）[^2-38^] | 生产（2024-06 起） |
| Firebase AI Logic Hybrid（Gemini Nano/AICore ↔ 云 Gemini） | 四档枚举 `InferenceMode`（PREFER_ON_DEVICE / PREFER_IN_CLOUD / ONLY_ON_DEVICE / ONLY_IN_CLOUD）+ 开发者自定义；官方自述"simple rule-based routing approach as an initial solution"[^2-20^] | 请求级（端侧限单轮、文本或单图输入） | 无 TEE；隐私 = 数据不出端（端侧路径）+ App Check 防配额盗用 | 无端云延迟对比官方数据；端侧上限 4,000 token/请求[^2-2^][^2-31^] | 生产（2026-04 Android / 2026-05 iOS，Firebase 官方博客）[^2-20^] |
| NVIDIA OpenShell privacy router | 用户声明式 YAML 策略（隐私/成本），deny-by-default，进程外执行，"路由遵循成本与隐私策略而非 agent 偏好"[^2-21^] | 请求级 | 凭证剥离、header 白名单、`inference.local` 本地端点承接敏感请求、本地 Nemotron 模型；无 TEE | 策略热更新 ~5s 生效；无推理延迟公开数据（NVIDIA 官方文档，2026）[^2-21^] | 生产（2026-03 随 NemoClaw 首次亮相，2026-09-28 作为 Open Agent Safety Platform 正式发布；Apache 2.0）[^2-21^] |
| RouteLLM（学术→Anyscale 生产组件） | 偏好数据训练的路由器预测强模型胜率，阈值校准 | 请求级 | 无（同一信任域内模型选择） | MT-Bench 省 85% 成本 @ 95% GPT-4 质量，仅 14–26% 查询进强模型（ICLR 2025）；Anyscale 生产 20 万查询省 85%（置信度中）[^2-22^] | 学术 + 生产组件 |
| MinionS（学术，Stanford 等） | 云端分解子任务 → 本地并行执行 → 云端汇总 | 任务分解级 | 原始长文档不出端，仅子任务/摘要上云 | 成本降 5.7×、恢复 97.9% 质量（朴素协议 30.4×/87%），arXiv 2502.15964，2025-02[^2-22^] | 学术 |
| GPU TEE 机密推理（H100/B200 CC + TDX/SEV-SNP，云端承接机制参照） | 用户选择隐私档 | 部署级 | GPU TEE + 远程证明 + PCIe AES-GCM-256 加密 + CPU TEE 联动 | TEE 开销约 5–15%、大模型额外 +50–100ms（第三方运营方口径，置信度中）；机制本身经 arXiv 2409.03992（2024-09）实测确认[^2-39^] | 云产品 |

表 2-6 揭示三点。第一，隐私保证已分化为两档：传输级（数据不出端即隐私，Google/Firebase 路径）与架构级（无状态 + 可验证，Apple PCC 阵营）；PCC 是后者唯一的大规模商用先例，且 2026 年把该信任模型扩展到 Google Cloud/NVIDIA 第三方机房，证明"可验证隐私云"可脱离自有数据中心存在[^2-19^]。第二，路由器的智能度差异悬殊：Apple 做逐 prompt 多维决策但完全黑盒（无用户开关可强制端侧[^2-40^]），Google 公开承认仅为规则式枚举，NVIDIA 用声明式静态策略——学习式路由（RouteLLM）与任务分解路由（MinionS）在学术上已证明数量级成本收益，但未被任何平台完整吸收。第三，也是对本章最重要的空白：三家生产方案均不把"数据敏感度分级"作为一等路由信号——Apple 按能力路由、Firebase 按可用性路由、OpenShell 按静态策略路由；同时路由决策的实测延迟/命中率数据全行业未公开（PCC 200–500ms 仅为第三方口径），路由决策审计日志仅见于企业合规侧的第三方架构建议[^2-40^]。

## 2.5 趋势判断与公认空白点

**正在收敛的方向（事实性观察）。** 其一，"端侧默认 + 云端升级"成为三大厂共识架构：Apple（AFM→PCC）、Google（Nano/AICore→Firebase 云 Gemini）、NVIDIA（本地 Nemotron→云前沿模型）在 2024–2026 年各自落地同一形态，差异仅在路由智能度与隐私承接强度。其二，"共享底座 + LoRA 特化"从云端向端侧迁移完成闭环：服务端 S-LoRA/Punica（2023）、OS 侧 Apple adapter 生态与 LiteRT-LM 官方"多特性共享单一底座"（2025）、端侧多租户学术系统 EdgeLoRA/MobiLoRA（2025）、芯片侧 Qualcomm/联发科/Taalas（2024–2026），四个层级独立收敛[^2-26^]。其三，adapter 内存与 KV cache 的管理正在统一：S-LoRA Unified Paging 开先河，SGLang 把 adapter 标识纳入前缀缓存键，MobiLoRA 按 adapter 复用 KV；权重（基座 + adapter）与 KV 进入同一分页/淘汰体系[^2-23^][^2-41^]。其四，热插拔延迟已压到亚百毫秒级：vLLM RL 场景热换 adapter <100ms（arXiv 2607.03441，2026-07）[^2-42^]，SGLang overlap loading 使对抗性负载下中位 TTFT 降约 35%（官方文档，2026-03）[^2-41^]，端侧 AFM adapter 为"数十 MB、内存暂存、即换即用"量级。其五，推理阶段分工与状态管理成为移动系统顶会热点：ASPLOS 2025（llm.npu）、MobiCom 2025（ElastiLM，单底座弹性化为多级子模型、切换开销 <1% TTFT）[^2-43^]、SenSys 2026（LLMaaS，KV chunk 级换入换出使上下文切换延迟降达 2 个数量级）[^2-44^]、MobiCom 2026（mzCache、NPUGen）密集出现，且多篇明确以"LLM-as-a-System-Service"为目标场景[^2-18^]。

**公认空白点（有据可依的 gap）。** 第一，无跨应用 QoS/SLO 保证：AICore 只有粗粒度配额 + 前台硬限制[^2-2^]，Apple 不公开配额，Android 17 NPU 调度 AIDL 明确 best-effort[^2-9^]；多租户公平性、SLO、抢占仅存在于学术原型（V10、Pantheon、ElastiLM）。第二，KV cache 与模型权重的 OS 级分页/换出未被任何平台服务暴露：AICore/Core ML 的 KV 对应用完全不可见，ANE 权重编译期烘焙不可变[^2-29^]；端侧框架普遍不支持跨请求持久 KV 复用（arXiv 2609.34727 引言明确指出 ExecuTorch/MLC-LLM/llama.cpp/MediaPipe "little or no support for persistent KV reuse across requests"）[^2-36^]。第三，NPU 无虚拟化/隔离标准：QNN 仅有 context priority 提示，联发科编译器在伙伴墙后，ANE 完全不开放；跨厂商 NPU 虚拟化、内存隔离、配额记账均无产业标准。第四，端云路由层缺标准接口与可观测数据（2.4 节）。第五，HarmonyOS 端侧推理栈硬核数据缺失：盘古/麒麟 NPU/MindSpore 侧只有软文口径，无论文或文档级来源，属真实覆盖缺口。第六，量化方案在 NPU 上的精度-性能横评无系统来源，"NPU 比 CPU 快 N 倍"类论断在领域内口径混乱（理论峰值 100× / 营销 25× / 实测 12× 并存），任何引用必须带场景限定。

## 2.6 对我方立场的逐条评审

**表 2-7 五条立场评审（立场 × 结论 × 依据）**

| # | 我方立场 | 评审结论 | 依据 |
|---|---|---|---|
| ① | 底座模型作为系统服务共享（类似编解码器） | **支持（已被产业验证）** | AICore（Android 14 起）与 Apple Foundation Models（iOS 26 起）均已量产落地该形态，多应用共享单实例、APK 不含权重[^2-1^][^2-3^]；M4（MobiCom 2024）提供学术背书[^2-4^]；SenSys 2026 "LLM as a System Service"直接命名并论证该范式[^2-44^]。**附带条件**：两大平台均以"前台限制 + 配额 + 可用性降级"换取资源可控，我方须预留同样的降级面；且系统服务代持内存（AICore 底座常驻 4GB+，逆向口径，置信度低-中[^2-45^]）在 per-app 限额体系下存在归账断裂，需与内存管理组件的 recharge-on-behalf 原语联动（见第 5 章）。 |
| ② | 多应用共享底座 + LoRA 热插拔 | **支持（强证据），但有一个必须正视的实现陷阱** | 支持证据跨四层：Apple AFM 内建可换 adapter（rank-16/数十 MB 官方口径，rank-32/~160MB 出货口径，见表 2-4）[^2-24^][^2-33^]；云端 S-LoRA/Punica/vLLM/SGLang 成熟工程体系[^2-23^][^2-41^]；端侧 EdgeLoRA 吞吐 2–4×[^2-25^]；芯片侧 Qualcomm/MTK 先例[^2-26^]。**陷阱**：LoRA 参与 K/V 投影计算，切换 adapter 会使既有 KV cache 失效（llama.cpp issue #10377："when we change the LoRA scale, we must clear the cache"，2024-11）[^2-46^]；且 llama.cpp 批量组织不支持同 batch 混合 adapter。**修订点**：多应用并发 + 各自 LoRA 必须采用 SGMV 类 per-request adapter kernel 或按 adapter 分组批处理；KV 缓存键必须含 (base_model_version, adapter_id, adapter_version, quant_tier) 等身份维度——SGLang 已在云端踩过此坑并把 adapter 标识写入前缀缓存键[^2-41^]（跨维度洞察 I-01"缓存键代数"）。另需修订：AICore 的 LoRA 能力未对第三方开放，"开放 LoRA"既是差异化空间也是审核/安全风险点，须同步设计签名/权限/版本治理（vLLM 官方警告运行时加载接口"不应暴露于生产环境"）[^2-42^]。 |
| ③ | 推理调度需多租户 QoS | **挑战（产业空白即机会），且需从"调度"扩展为"调度 + 弹性 + 状态管理"三层** | 现有平台全部停留在"配额 + 优先级提示"：AICore BUSY/battery 配额[^2-2^]、QNN 8 级 context priority[^2-28^]、Android 17 best-effort NPU AIDL[^2-9^]，无 SLO/公平性/抢占保证；主流端侧框架（llama.cpp/ExecuTorch/MNN）均无 QoS 概念。学术原型给出两条互补路线：ElastiLM 模型弹性化（SLO 驱动子模型升降级，切换 <1% TTFT）[^2-43^]、MobiLoRA 系统级上下文感知驱逐（按 App 前后台状态决定 KV 保留，TTFT 最高降 81.3%）[^2-25^]。**现实约束**：在厂商封闭 DSP 固件之上拿不到内核级抢占抓手，可行路径是系统服务层排队 + 抢占，而非 NPU 内核级抢占；QoS 契约的信号输入应遵循"预测信号分层定律"（I-04）——确定性事件（前台/可见）可签供给契约，结构性信号（router 预告）可做预取但不可占保底份额，行为概率（下一 App 预测命中率仅 52%）只配驱动可回收的投机预载[^2-47^]。 |
| ④ | 端云之间按隐私/成本/延迟的路由层 | **支持（方向正确，已被三大厂验证为必选项），需自研抽象并做两处修订** | 三大厂 2024–2026 全部落地混合推理路由（2.4 节）。**修订一**：路由输入须把"隐私分级"提升为一等信号——现有商用方案无人按数据敏感度路由，这既是空白点也是差异化空间；同时应预留路由决策日志接口（企业合规刚需）[^2-40^]。**修订二**：路由层输出必须与"云端承接机制"绑定——本地（明文信任）/ PCC 类（无状态 + 可验证）/ 普通云 API（明示降级）三档，否则隐私承诺降级为政策承诺；Apple 2026 年把可验证信任模型扩展到第三方机房证明该承接层可外挂于异构云[^2-19^]。工程注意：平台配额/前台限制使"端侧容量"高度动态，BUSY/quota/可用性三态必须作为路由决策的一等输入[^2-2^]。 |
| ⑤ | 模型权重与 KV cache 可分页 | **部分支持、部分需修订（平台路径不支持，自研路径可行）** | 权重可分页**强支持**：llama.cpp mmap 惰性加载、LLM in a flash（2× DRAM 模型可跑）、PowerInfer-2（手机 47B 11.68 tok/s）证明 flash-DRAM 分层已工程化[^2-11^][^2-18^]；ExecuTorch AOT memory planning 提供另一极（导出期定 arena，适合受控系统服务）[^2-12^]。KV 可分页**需修订**：vLLM 分页抽象在端侧仅 MLC-LLM（PagedKVCache，page=16）落地[^2-13^]；**NPU 静态图与 KV 分页存在根本张力**（动态复用语义 vs 静态编译形状），面向 NPU 后端须采用 chunk-and-pad + 图内重算方案而非照搬 vLLM[^2-36^]。**范围修订**：分页池应同时覆盖基座权重、adapter 权重、KV cache 三类对象（S-LoRA Unified Paging 先例）[^2-23^]；平台托管路径（AICore/AFM）的权重/KV 完全黑盒，短期只能在自研引擎内做分页，平台路径仅作回退。 |

表 2-7 的总体图景是：立场①②已被产业验证、属于"正确且拥挤"的方向，价值在执行质量与治理设计；立场④方向正确但所有人都在初级阶段，差异化空间在隐私分级与承接绑定两处修订；立场③⑤则落在产业空白区——学术证据（V10、ElastiLM、MobiLoRA、LLMaaS、S-LoRA）齐备而产业无人交付，是我方真正的机会窗口，但二者都有明确的物理约束（封闭 NPU 固件、NPU 静态图）要求把目标限定在系统服务层与自研引擎路径上。五条立场无一被证伪，但②③⑤各带一条必须写进设计文档的修订条款：缓存键规范（②）、QoS 三层扩展与预测信号分层（③）、分页对象扩容与路径限定（⑤）。

---

## 本章来源

[^2-1^]: WinBuzzer: Google opens Gemini Nano on-device AI to Android app developers（引 ML Kit 官方文档）, https://winbuzzer.com/2025/05/19/google-opens-gemini-nano-on-device-ai-to-android-app-developers-xcxwbn/, 2025-05-19
[^2-2^]: Capawesome: ML Kit GenAI Prompt 文档与博客（逐字引 Google 官方文档：4,000 token 上限、BUSY/PER_APP_BATTERY_USE_QUOTA_EXCEEDED/BACKGROUND_USE_BLOCKED 错误码）, https://capawesome.io/docs/sdks/capacitor/mlkit/genai-prompt/ 与 https://capawesome.io/blog/how-to-use-gemini-nano-in-a-capacitor-app/, 2026-07-10 / 2026-09-29
[^2-3^]: Apple Newsroom: Apple's Foundation Models framework unlocks new intelligent app experiences, https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/, 2025-09-29
[^2-4^]: M4: Mobile Foundation Model as Firmware（MobiCom 2024）, https://arxiv.org/html/2308.14363v3, 2024-03-12
[^2-5^]: firecat-web HDC 2026 报道, https://www.firecat-web.com/daily-news/10289, 2026-06-14；Pandaily: HarmonyOS Agent OS HDC 2026, https://pandaily.com/harmonyos-agent-os-hdc-2026-xiaoyi-celina-jun2026, 2026-08-28
[^2-6^]: meetonfriday 逐字引 Android 官方文档（NNAPI Android 15 deprecated）, https://meetonfriday.com/posts/666bbf67/, 2025-03-10
[^2-7^]: Google AI 官方论坛（Googler 答复：NN HAL 保留、AICore 内部使用 NNAPI）, https://discuss.ai.google.dev/t/how-to-deploy-aicore-gemini-nano-on-pixel-other-devices/93284, 2025-08-07
[^2-8^]: Google Developers Blog: Unlocking peak performance on Qualcomm NPU with LiteRT（经 yomu.fyi / daily.dev 镜像）, https://yomu.fyi/post/unlocking-peak-performance-on-qualcomm-npu-with-litert, 2025-11-24
[^2-9^]: androidperformance wiki（读 AOSP 源码：Android 17 NpuManager / NPU scheduling AIDL）, http://wiki.androidperformance.com/part1-fundamentals/ch05-cpu-power/05-ondevice-ai-runtime-npu.html, 2026
[^2-10^]: OpenHarmony 官方文档：Neural Network Runtime Kit（NNRt 56 算子/仅同步推理/零拷贝）, https://github.com/openharmony-rs/openharmony-docs/blob/master/zh-cn/application-dev/ai/nnrt/Neural-Network-Runtime-Kit-Introduction.md, 2024-04-12（持续更新）
[^2-11^]: llama.cpp 官方文档（后端清单、KV 重构、投机解码实现）, https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md 与 docs/speculative.md, 2025-08 ~ 2026 检索
[^2-12^]: ExecuTorch 论文（MLSys 2026，arXiv:2605.08195；Galaxy S25 Ultra 基准）, https://proceedings.mlsys.org/paper_files/paper/2026/file/236f915dd02af4f11927f67330b21d4b-Paper-Conference.pdf, 2026
[^2-13^]: theleftshift 引 Google 官方博客（LiteRT-LM 共享底座 + LoRA）, https://www.theleftshift.com/google-brings-on-device-genai-to-chrome-chromebook-plus-and-pixel-watch-via-litert-lm/, 2025-10-03；Apache TVM 官方教程（PagedKVCache page=16）, https://tvm.apache.org/docs/how_to/tutorials/optimize_llm.html, 2026-11 检索
[^2-14^]: GPTQ（ICLR 2023, arXiv:2210.17323）技术评述, https://research.rudrite.com/gptq, 2026-06-13；Microsoft BitNet b1.58 2B4T 模型卡（Azure AI 目录）, https://ai.azure.com/catalog/models/microsoft-bitnet-b1.58-2b-4t, 2026-04-20 页面
[^2-15^]: MNN GitHub Discussion #4351（TurboQuant 落地，Qwen3-4B@8K KV ~2GB、省 30–60%）, https://github.com/alibaba/MNN/discussions/4351, 2026-04-07
[^2-16^]: EAGLE-2（EMNLP 2024）解析, https://www.emergentmind.com/topics/eagle-2, 2025-12-29；EAGLE-3 NeurIPS 2025 官方 poster 摘要, https://neurips.cc/virtual/2025/poster/119930, 2025-12-02
[^2-17^]: Medusa（ICML 2024, arXiv:2401.10774）摘要, https://chatpaper.com/zh-CN/paper/37138, 2026-01-14
[^2-18^]: llm.npu（ASPLOS 2025）论文 PDF, https://xumengwei.github.io/files/ASPLOS25-NPU.pdf, 2025；PowerInfer-2（arXiv:2406.06282v2）, https://arxiv.org/abs/2406.06282v2/, 2024-06-10；LLM in a flash（Apple, arXiv:2312.11514, ACL 2024）, https://arxiv.org/pdf/2312.11514, 2024-07-30
[^2-19^]: Apple Security Research blog: Private Cloud Compute（五大保证）, https://security.apple.com/blog/private-cloud-compute/, 2024-06-10；Tobias Reithmeier（PCC 研究环境/$1M 悬赏/2026-06 扩展 Google Cloud+NVIDIA 官方来源清单）, https://www.tobiasreithmeier.de/en/blog/apple-private-cloud-compute, 2026-07-07
[^2-20^]: Firebase 官方博客：Google I/O 2026 announcements, https://firebase.blog/posts/2026/05/google-io-2026-announcements/, 2026-05-19；udfsoft 转 Android 开发者博客（"simple rule-based routing approach as an initial solution"）, https://news.udfsoft.com/?app=android, 2026-10-20；getsuperculture The Brief（包版本与单轮限制）, https://getsuperculture.com/thebrief/monday-april-20-2026, 2026-04-20
[^2-21^]: NVIDIA 官方文档：OpenShell inference/privacy router, https://docs.nvidia.com/openshell/inference/about, 2026；techjacksolutions（GTC 2026-03-16 NemoClaw+OpenShell）, https://techjacksolutions.com/ai-brief/nvidia-nemoclaw-open-source-security-stack-brings-privacy-co/, 2026-03-19；getsliq（"routing follows your cost and privacy policies"）, https://getsliq.com/blog/nvidia-openshell-explained, 2026-03-17；发布时间双口径按交叉验证 C3 裁决（2026-03 首次亮相 / 2026-09-28 平台正式发布）
[^2-22^]: RouteLLM（ICLR 2025）综述, https://www.digitalapplied.com/blog/llm-model-routing-2026-cost-quality-optimization-engineering-guide, 2026-06-14；Anyscale 生产部署转述, https://getnadir.com/blog/routellm-74-percent-gpt4-calls-dont-need-gpt4/, 2026-06-27；MinionS（arXiv:2502.15964）, https://arxiv.org/html/2502.15964v1, 2025-02-21；CE-CoLLM（arXiv:2411.02829）, https://arxiv.org/html/2411.02829v2, 2025-06-08
[^2-23^]: LoRA（ICLR 2022, arXiv:2106.09685）, 2021；S-LoRA（arXiv:2311.03285, MLSys 2024）, https://arxiv.org/abs/2311.03285, 2023-11-06；Punica（arXiv:2310.18547, MLSys 2024）, https://proceedings.mlsys.org/paper_files/paper/2024/file/054de805fcceb78a201f5e9d53c85908-Paper-Conference.pdf, 2023-10 / 2024
[^2-24^]: Apple 技术报告：Apple Intelligence Foundation Language Models（arXiv:2407.21075；rank-16 adapter 数十 MB、动态加载/暂存/换出）, https://arxiv.org/html/2407.21075v1, 2024-07-29
[^2-25^]: EdgeLoRA（MobiSys 2025, arXiv:2507.01438）, https://arxiv.org/html/2507.01438v1, 2025-07-02；MobiLoRA（ACL 2025）, https://aclanthology.org/2025.acl-long.1140/, 2025-07
[^2-26^]: Qualcomm 2024 白皮书（LoRA 并行/热切换，转载 PDF）, https://www.sgpjbg.com/baogao/607412.html, 2024-05-30；embedded.com（联发科 Dimensity 9300+ LoRA Fusion 2.0）, https://www.embedded.com/mediatek-new-flagship-dimensity-9300-targets-on-device-llms/, 2024-05-10；ertas.ai（芯片行业 LoRA 定制层收敛评论）, https://www.ertas.ai/blog/hardware-lora-support-ai-chips, 2026-02-22
[^2-27^]: natashatherobot（WWDC25 实测：4,096 token 上下文、可用性三态）, https://www.natashatherobot.com/p/apple-foundation-models, 2025-06-28；slash-digital（WWDC26 示例 8,192 token）, https://slash-digital.io/en/insights/small-models-on-device/, 2026-09-26
[^2-28^]: ONNX Runtime QNN EP 官方文档（8 级 context priority）, https://github.com/onnxruntime/onnxruntime-qnn/blob/main/docs/execution_providers/QNN-ExecutionProvider.md, 2026 在维护；SECO 开发者文档（QNN 后端库与 HTP 仅 INT8/INT16）, https://developer.seco.com/clea-os/scarthgap_2-05-00/npu/qcom-npu/, 2025 前后；GitHub mdla-cnn-engine（ncc-tflite 伙伴墙）, https://github.com/Peterc3-dev/mdla-cnn-engine, 2026-06-05
[^2-29^]: ANE 编程模型逆向分析（arXiv:2603.06728；~32MB SRAM、权重编译期烘焙——单源逆向，置信度中）, https://arxiv.org/html/2603.06728v1, 2026-03-06；Contra Collective（ANE 无通用计算 API）, https://contracollective.com/blog/gpu-vs-apple-neural-engine-local-llm-inference-m5-max-2026, 2026-07-10
[^2-30^]: V10: Hardware-Assisted NPU Multi-tenancy（ISCA 2023）, https://jianh.web.engr.illinois.edu/papers/v10-isca23.pdf, 2023；Pantheon（MobiSys 2024）, https://dl.acm.org/doi/10.1145/3643832.3661878, 2024-06
[^2-31^]: byteiota（Gemini Nano v3 需 ≥12GB RAM，二手口径）, https://byteiota.com/android-17-gemini-nano-api-on-device-ai/, 2026-05-19
[^2-32^]: Apple 技术报告 2025（arXiv:2507.13575；2-bit QAT、KV-reuse、draft 投机解码）, https://arxiv.org/pdf/2507.13575, 2025-07
[^2-33^]: fguzman82 GitHub 逆向分析（3.18B base、48.77M draft、LoRA rank 32、KV 共享 -37.5%）, https://github.com/fguzman82/apple-foundation-model-analysis, 2025-06；gamut.so（rank 32 ≈160MB/adapter、Background Assets）, https://www.gamut.so/blog/apple-foundations-models-framework-10-best-practices-for-developing-ai-apps, 2025-09-08
[^2-34^]: MarkTechPost 转 Google developers blog（LiteRT NeuroPilot：Gemma-3n E2B @ Dimensity 9500 prefill 1,600+ / decode 28 tok/s）, https://www.marktechpost.com/2025/12/09/google-litert-neuropilot-stack-turns-mediatek-dimensity-npus-into-first-class-targets-for-on-device-llms/, 2025-12-09
[^2-35^]: 端侧推理交叉实测（arXiv:2607.05475；NPU prefill 强 decode 弱）, https://arxiv.org/html/2607.05475v1, 2026-07-06（注：交叉验证中该 arXiv 编号检索零结果，未能独立核实，相关结论以 [^2-12^][^2-18^] 为准）
[^2-36^]: KV Cache Reuse for Efficient LLM Serving on Mobile NPUs（arXiv:2609.34727）, https://arxiv.org/html/2609.34727v1, 2026-09-28
[^2-37^]: kanopylabs（端侧 TTFT <100ms、PCC +200–500ms，第三方口径）, https://kanopylabs.com/blog/apple-intelligence-sdk-integration-for-apps, 2026
[^2-38^]: ai.singhsk.com（PCC 32K 上下文/entitlement/配额）, https://ai.singhsk.com/on-device-agentic-ai-for-mobile-apps-android-vs-ios-architecture-in-2026, 2026-08-03；theswift.dev（PCC 日配额）, https://www.theswift.dev/posts/choose-between-on-device-foundation-models-and-private-cloud-compute, 2026-06-23
[^2-39^]: GPU TEE 性能开销实测（arXiv:2409.03992）, https://arxiv.org/html/2409.03992v2, 2024-09-13；Phala（H100 CC 机制与 5–15% 开销口径）, https://phala.com/learn/How-Nvidia-Enable-Confidential-AI, 2025-11-14
[^2-40^]: softwareseni（无用户开关强制端侧）, https://www.softwareseni.com/which-apple-ai-workloads-leave-the-device-and-what-they-cost/, 2026-09-23；practicallogix（企业合规路由审计日志建议）, https://www.practicallogix.com/mobile-app-development-in-the-on-device-ai-era/, 2026-07-02；WWDC26 System Orchestrator 路由信号（ecorpit 媒体转述）, https://ecorpit.com/wwdc-2026-apple-intelligence-tim-cook-final-keynote/, 2026-06-08
[^2-41^]: SGLang 官方文档（LoRA 参数体系、pinned/eviction、overlap loading TTFT -35%）, https://sgl-project.github.io/advanced_features/lora.html, 2026-10-26；pinghaoyang SGLang 源码拆解（前缀缓存键含 adapter 标识）, https://pinghaoyang.com.cn/aigc/posts/sglang-lora-serving/, 2026-10-19
[^2-42^]: vLLM 运行时 LoRA 源码级核验（安全警告）, https://gpusmith.com/articles/en/pdfs/multi-lora-serving-many-adapters-one-gpu.pdf, 2026-10-30；RL 场景热换 adapter <100ms（arXiv:2607.03441）, https://arxiv.org/html/2607.03441v1, 2026-07-03
[^2-43^]: ElastiLM: Elastic On-Device LLM Service（MobiCom 2025）, https://dl.acm.org/doi/10.1145/3680207.3765259, 2025-09-01
[^2-44^]: LLM as a System Service（arXiv:2403.11805, SenSys 2026；上下文切换延迟降 2 个数量级）, https://arxiv.org/abs/2403.11805, 2024-03-18
[^2-45^]: xckevin.com（AICore 逆向：APEX/system_server、LoRA Adapter Registry、底座常驻 4GB+、卸载 40MB adapter ~200ms——第三方逆向，置信度低-中）, https://xckevin.com/en/blog/android-aicore-gemini-nano/, 2025-05-21
[^2-46^]: llama.cpp GitHub issue #10377（/lora-adapters 热插拔与 KV 失效）, https://github.com/ggml-org/llama.cpp/issues/10377, 2024-11-18
[^2-47^]: agentos_insight.md（跨维度洞察 I-01 缓存键代数、I-04 预测信号分层定律；I-04 内含 MAPLE 52% 命中率证据引自 dim10）, /mnt/agents/output/research/agentos_insight.md, 2026-11-06

# AgentOS 维度 A 调研报告：系统级端侧模型服务 + NPU 调度

- 调研日期：2026-11-06
- 范围：系统级端侧模型服务（Android AICore/Gemini Nano、Apple Foundation Models、HarmonyOS 小艺/Pangu）；NPU 编程/内存模型与多租户调度（Qualcomm QNN、MediaTek NeuroPilot、Apple ANE、跨厂商抽象层）
- 时间范围：2024-01 至 2026-11 为主，奠基性工作标注年份
- 所有事实性论断以 `[^n^]` 标注，证据清单见第 6 节

---

## 1. 技术谱系表

### 1.1 系统级端侧模型服务（模型即系统服务）

| 技术路线 | 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|---|
| OS 托管模型服务（Android） | **AICore + Gemini Nano + ML Kit GenAI APIs** | Google | 2023-12 首落地（Pixel 8 Pro），2025-05 对第三方开放 beta [^1^] | 模型由系统服务统一下载/加载/推理，多应用共享单实例，APK 不含模型；前台限制 + 每应用配额[^2^][^3^] |
| OS 托管模型服务（iOS/macOS） | **Foundation Models framework**（Apple Intelligence 3B 端侧模型） | Apple | 2025-06 发布（WWDC25），iOS 26 起可用[^4^] | Swift 原生 API 直接调用系统 3B 模型，guided generation + tool calling，免费无按次计费[^4^] |
| 底座模型 + LoRA 热插拔（产业实践） | **AFM 端侧模型 + 可换 LoRA adapter** | Apple | 2024（技术报告）[^5^] | rank-16 adapter 仅数十 MB，可动态加载/缓存/换出，底座冻结，"保证 OS 响应性"[^5^] |
| 底座模型 + LoRA 热插拔（产业实践） | **AICore LoRA Adapter Registry** | Google | 2024-2025（逆向分析，低置信）[^6^] | 系统服务内注册 LoRA adapter，内存压力时主动卸载（约 200ms 卸载 40MB adapter）[^6^] |
| 模型即固件（学术先导） | **M4: Mobile Foundation Model as Firmware** | 北京邮电大学等 | MobiCom 2024（arXiv 2023-08）[^7^] | 底座模型由 OS+硬件共同管理、对 App 不可修改，以系统服务形式暴露，App 仅通过小 adapter 调用[^7^] |
| 端侧多租户 LoRA serving（学术） | **EdgeLoRA** | Univ. of Maryland | MobiSys 2025[^8^] | 共享底座 + 上千 LoRA adapter 并发服务：自适应 adapter 选择、异构内存池、批量 LoRA 推理，吞吐较 llama.cpp 高 2–4×[^8^] |
| 云端大规模 LoRA serving（学术） | **S-LoRA** | Stanford 等 | MLSys 2024[^9^] | PagedAttention + Unified Paging 支持数千并发 LoRA（云端，非端侧，作对照） |
| 系统内嵌大模型 + Agent 化 | **HarmonyOS 小艺 + Pangu 端侧（PanGu-Σ / Pangu 5.0 Embedded / Pangu 6.0）** | 华为 | 2024-06（NEXT）至 2026-06（HDC 2026，HarmonyOS 7）[^10^][^11^][^12^] | Pangu 深度集成进系统；HarmonyOS 7 宣称 Pangu 6.0 "嵌入系统内核"；模型即插即用多模型路由（Pangu/DeepSeek）[^11^][^12^] |

### 1.2 NPU 编程模型、内存模型与调度

| 技术路线 | 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|---|
| 厂商底层 NPU SDK | **Qualcomm AI Engine Direct (QNN / QAIRT)** | Qualcomm | 2023 起持续演进[^13^] | 统一 API + 每加速器后端库（CPU/GPU/HTP），HTP 仅量化 INT8/INT16，context binary AOT/JIT，8 级 context priority + 性能/功耗档位[^13^][^14^][^15^] |
| 厂商底层 NPU SDK | **MediaTek NeuroPilot / Neuron SDK** | MediaTek | 2020 起；LiteRT 集成 2025-12[^16^][^17^] | MDLA（INT8 CNN 加速器）+ VPU 双引擎；离线编译器 ncc-tflite 在伙伴墙后；2025-12 与 Google 推 LiteRT NeuroPilot Accelerator 使 Dimensity NPU 成为一等 LLM 目标[^17^][^18^] |
| 固定功能加速器 + 编译调度 | **Apple Neural Engine + Core ML** | Apple | 2017 起（ANE）；编程模型分析 2026-03[^19^] | 编程面是 Core ML 图而非通用计算 API；compile-then-dispatch，权重编译期烘焙，IOSurface 零拷贝，~32MB SRAM 预算溢出性能降约 30%[^19^][^20^] |
| 跨厂商 OS 级抽象（已弃用） | **Android NNAPI** | Google + 厂商 | 2018（8.1）引入，2024 Android 15 弃用[^21^] | 首个跨厂商 NPU HAL/NDK 抽象；因厂商实现不均、跟不上 transformer/diffusion 演进被弃，HAL 保留给系统服务（如 AICore）[^21^][^22^] |
| 跨厂商框架级抽象（当前主线） | **LiteRT CompiledModel + 厂商 Accelerator（Qualcomm/MediaTek）+ AI Packs/PODAI** | Google + Qualcomm + MediaTek | 2025-05（I/O 2025）起，2026-01 生产可用[^23^][^17^][^24^] | 单一 API 选定 `Accelerator.NPU`，AOT+JIT，失败回退 GPU/CPU；宣称 NPU 最高 100× CPU / 10× GPU[^23^][^24^] |
| 端侧 LLM 引擎抽象 | **LiteRT-LM / ONNX Runtime EP（QNN EP、NeuronEP）** | Google / Microsoft + 厂商 | 2025 起[^25^][^26^] | QNN EP 直通 HTP；ONNX Runtime 在 MediaTek Genio 可经 NeuronExecutionProvider 直接跑 NPU[^26^][^25^] |
| OS 级 NPU 调度控制面（最新） | **Android 17 `NpuManager` + NPU scheduling AIDL** | Google（AOSP） | 2026（Android 17 / API 37）[^27^] | 新增 `FEATURE_NEURAL_PROCESSING_UNIT`；PriorityManager/SchedulingConfig/WorkInfo/ISchedulingCallback 描述 UID、优先级、直接访问资格；best-effort，无 SLO 保证；@SystemApi 不开放给第三方[^27^] |
| 跨芯片运行时（中国生态） | **HarmonyOS NNRt（Neural Network Runtime）** | 华为/OpenHarmony | 2022 起[^28^] | 跨芯片推理运行时，构图/编译/执行/共享内存零拷贝/模型缓存；支持推理优先级与性能模式配置；仅 56 个算子、仅同步推理，并发性取决于底层驱动[^28^] |

### 1.3 多租户推理调度（学术，与本维度直接相关）

| 代表工作 | 机构/ venue | 时间 | 一句话贡献 |
|---|---|---|---|
| **V10: Hardware-Assisted NPU Multi-tenancy** | UIUC 等, ISCA 2023[^29^] | 2023 | 硬件辅助的算子级 NPU 多租户：算子级调度 + 低开销抢占，吞吐 1.57×、尾延迟降 1.74×（云 TPU 场景） |
| **Pantheon: Preemptible Multi-DNN Inference on Mobile Edge GPUs** | CityU, MobiSys 2024[^30^] | 2024 | 移动 GPU 上可抢占多 DNN 推理：切片执行 + 提前退出，面向并发 DNN 工作负载 |
| **llm.npu / 11m.npu: Fast On-device LLM Inference with NPUs** | 北大徐梦炜团队, ASPLOS 2025[^31^] | 2025 | 端侧 LLM prefill 最大化卸载到 NPU（W8A8 + 定长 chunk 图 + CPU/GPU 离群值补偿）；论文明确以 "LLM-as-a-System-Service" 为目标场景[^31^] |
| **Agent.xpu: Efficient Scheduling of Agentic LLM Workloads on Heterogeneous SoC** | arXiv 2026-01[^32^] | 2026 | 面向单设备异构 SoC 的 agentic LLM 工作负载（响应式+主动式流）调度，区别于云端多租户假设 |
| **mzCache: On-Device LLM Memory Management under Multitasking** | MobiCom 2026[^33^] | 2026 | 多任务并存下的端侧 LLM 内存（KV cache 等）管理——KV 可分页/换出的学术化探索 |
| **NPUGen: NPU as KV Generator for Stable Long-Context Mobile LLM Inference** | MobiCom 2026[^33^] | 2026 | NPU 作为长上下文 KV 生成器，稳定长上下文端侧推理 |
| **Scaling LLM Test-Time Compute with Mobile NPU on Smartphones** | EuroSys 2026[^33^][^34^] | 2026 | 用移动 NPU（QNN HTP/FastRPC）扩展 LLM 推理时计算，实证手机 NPU 的 LLM serving 能力边界 |

---

## 2. 关键数据（有出处的量化指标）

| 指标 | 数值 | 来源与日期 | 置信度 |
|---|---|---|---|
| Gemini Nano 1.0 4-bit 量化体积 | ~1.8 GB | 逆向分析博客（xckevin，2025-05）[^6^] | medium |
| AICore 卸载 40MB LoRA adapter 耗时 | ~200 ms（Pixel 8 Pro，底座常驻 4GB+） | 同上，逆向/推测性描述[^6^] | low-medium |
| Gemini Nano 模型增量更新下载量 | 版本升级仅下载 ~200–400 MB（bsdiff 式差分） | 同上[^6^] | low-medium |
| ML Kit GenAI Prompt API 输入上限 | < 4,000 token（约 3,000 英文单词）；>256 token 输出场景不建议 | 官方文档（经插件文档逐字引用，2026-07）[^35^] | high |
| AICore 配额错误码 | 短时超配额 → `ErrorCode.BUSY`；长周期超配额 → `ErrorCode.PER_APP_BATTERY_USE_QUOTA_EXCEEDED` | 官方 ML Kit 文档（逐字引用）[^36^] | high |
| AICore 前台限制 | 非 top foreground app（含 foreground service）→ `ErrorCode.BACKGROUND_USE_BLOCKED` | 官方 ML Kit 文档（逐字引用）[^36^] | high |
| ML Kit GenAI APIs 成熟度 | beta（语音识别 alpha），"is not subject to any SLA or deprecation policy"，可能 break 兼容性 | 官方文档（经媒体引用，2025-05）[^1^] | high |
| Apple Foundation Models 端侧模型规模 | ~3B 参数；2024 报告：平均 <4 bit/权重；2025 报告：QAT 2 bit 权重 + KV-reuse 双段架构 + 48M draft 模型投机解码 | Apple 技术报告 2024-07 / 2025-07[^5^][^37^] | high |
| AFM LoRA adapter 体积 | rank-16 adapter 约 10s of MB（16-bit 表示）；可动态加载/缓存/换出 | Apple 技术报告 2024[^5^] | high |
| Foundation Models 上下文窗口 | 4,096 token（WWDC25/iOS 26）；WWDC26 示例达 8,192 token | 开发者实测/文档[^38^][^39^] | high / medium |
| Foundation Models 配额 | Apple **未公开任何数值化配额/速率限制**；仅存在可用性状态（not eligible / not enabled / model not ready）与 guardrail 拦截 | Apple 文档与开发者综述[^38^][^40^] | high（对"未公开"这一事实） |
| LiteRT NeuroPilot：Gemma-3n E2B @ Dimensity 9500 | prefill >1,600 tok/s、decode 28 tok/s @4K 上下文；LLM 吞吐 12× CPU / 10× GPU | Google developers blog（2025-12-08）[^17^] | high |
| LiteRT Qualcomm Accelerator | NPU 最高 100× CPU / 10× GPU；Snapdragon 8 Elite Gen 5 上 56+ 模型 NPU <5ms；FastVLM-0.5B：TTFT 0.12s、prefill >11,000 tok/s、decode >100 tok/s | Google 官方博客摘要（2026-01/2025-11）[^24^][^41^] | medium-high（厂商宣称值） |
| LiteRT NPU JIT 编译开销 | Gemma-3-270M 端上编译可 >1 分钟 → 官方强烈建议 AOT + AI Pack 分发 | Google/MediaTek 发布材料[^17^] | high |
| ANE 内存预算 | M4 Max 代：工作集超 ~32MB SRAM 预算时性能降约 30%（溢出到 DRAM） | arXiv 2603.06728（2026-03）[^19^] | medium-high |
| MediaTek NPU 支持精度 | MDLA：INT8/INT16/FP16（CNN 固定功能）；VPU：FP32/FP16/INT16/INT8 | SECO/MediaTek Genio 文档[^42^] | high |
| 华为端侧模型（传闻/媒体） | 原生 30B 参数模型常驻运存（2B 激活），量化剪枝+专家预测；Pangu 2.0 开放 512K 上下文 | 新浪科技横评（2026-07），非官方[^43^] | low-medium（媒体线索） |
| HarmonyOS AI 子系统调用量 | 20+ 项开放 AI 能力，日调用 36.8 亿次；2100+ 系统 Skill；500+ 伙伴 Skill | HDC 2026 报道（firecat/pandaily，2026-06）[^10^][^11^] | medium |
| NNRt 算子/并发限制 | 仅支持 56 个常用算子；仅同步推理；不支持多线程并发构图；并发编译/执行取决于底层驱动 | OpenHarmony 官方文档[^28^] | high |
| V10 NPU 多租户（学术） | 算子级多租户：聚合吞吐 1.57×、单任务延迟 1.56×、尾延迟 1.74× 改善；硬件改动 <0.03% 面积 | ISCA 2023[^29^] | high |
| EdgeLoRA（学术） | Jetson AGX Orin 上同时服务 1,000+ LoRA adapter（llama.cpp 仅 ~50）；吞吐 2–4× | MobiSys 2025[^8^] | high |

---

## 3. 趋势判断

**正在收敛的方向：**

1. **"模型即系统服务"已从学术设想（M4, MobiCom 2024[^7^]）落地为两大平台事实标准**。Google AICore（Android 14 起）与 Apple Foundation Models（iOS 26 起）均采用：模型由 OS 下载/加载/更新、多应用共享单实例、App 通过 IPC/框架 API 调用、APK 不含权重[^2^][^3^][^4^]。HarmonyOS 更激进，宣称 Pangu 6.0 直接嵌入系统内核并以 Agent 架构开放[^12^]。
2. **共享底座 + LoRA 特化成为端侧个性化的事实路径**。Apple AFM 原生内建可换 LoRA adapter（rank 16、数十 MB、动态换入换出）[^5^]；AICore 据逆向分析亦有 LoRA Adapter Registry[^6^]；学术界 EdgeLoRA（MobiSys 2025）证明端侧可同时服务 1,000+ adapter[^8^]。
3. **NNAPI 式"OS 内编译期算子级抽象"被放弃，转向"可独立升级的框架级抽象（LiteRT/ONNX Runtime）+ 厂商后端 + 系统服务直连 HAL"**。NNAPI 于 Android 15 弃用，但 NN HAL 保留供 AICore 等系统服务使用[^21^][^22^]；Google 联合 Qualcomm/MediaTek 把 NPU 做成 LiteRT 一等 Accelerator（AOT+JIT+AI Pack 分发）[^23^][^17^]。
4. **OS 级 NPU 调度控制面开始出现**：Android 17（API 37）AOSP 新增 `NpuManager` 与 NPU scheduling AIDL（UID/优先级/直接访问资格/工作状态回调），但为 best-effort、@SystemApi 封闭[^27^]——说明"NPU 需要调度"已成平台共识，但尚处于资格/优先级提示阶段，非 QoS 保证。
5. **端侧 LLM serving 系统成为移动系统顶会热点**：ASPLOS 2025（llm.npu[^31^]）、MobiSys 2025（EdgeLoRA[^8^]）、EuroSys/MobiCom 2026（NPUGen、mzCache、Test-Time Compute[^33^]）密集出现，且 llm.npu 明确以 "LLM-as-a-System-Service" 为目标[^31^]。

**公认空白点：**

1. **无跨应用 QoS/SLO 保证**：AICore 只有粗粒度配额（BUSY/battery quota）+ 前台硬限制[^36^]；Apple 不公开任何配额；Android 17 NPU 调度 AIDL 明确 best-effort、不保证完成时间[^27^]。多租户公平性、SLO、抢占仅存在于学术原型（V10[^29^]、Pantheon[^30^]）。
2. **KV cache 与模型权重的 OS 级分页/换出未被平台服务暴露**：AICore/Core ML 的 KV cache 对应用不可见、不可分页；相关工作仅在学术界（mzCache[^33^]、S-LoRA[^9^]）。
3. **NPU 无虚拟化/隔离标准**：高通 QNN 只有 context priority 提示与性能档位[^14^]；MediaTek 编译器在伙伴墙后[^16^]；ANE 完全不开放直接编程[^20^]。跨厂商 NPU 虚拟化、内存隔离、配额记账均无产业标准。
4. **端云路由层缺标准接口**：各平台各自为战（Firebase AI Logic Hybrid[^44^]、Apple PCC、华为 HPIC[^10^]），无可移植的"隐私/成本/延迟"路由抽象。

---

## 4. 对我方架构立场的启发（逐条对照）

| 我方立场 | 判断 | 依据 |
|---|---|---|
| 底座模型作为系统服务共享（类似编解码器） | **支持（已验证）** | AICore 与 Apple Foundation Models 均已量产落地该形态，证明可行且被用户接受；M4 论文提供学术背书[^2^][^4^][^7^]。注意代价：两家都以**前台限制 + 配额 + 可用性降级**换取资源可控，我方需预留同样的"降级面"。 |
| 多应用共享底座 + LoRA 热插拔 | **支持（强证据）** | Apple AFM 内建 rank-16 可换 adapter（数十 MB、动态换入换出且"保证 OS 响应性"）[^5^]；EdgeLoRA 证明 1,000+ adapter 端侧并发可行[^8^]。**需要修订点**：AICore 的 LoRA 能力未对第三方开放（仅系统特性），说明"开放 LoRA 给第三方"是差异化空间，也是安全/审核风险点。 |
| 推理调度需多租户 QoS | **挑战（产业空白即机会）** | 现有平台全部停留在"配额+优先级提示"（AICore BUSY 配额[^36^]、QNN 8 级 context priority[^14^]、Android 17 best-effort NPU AIDL[^27^]），无 SLO/公平性/抢占保证。学术（V10/Pantheon）证明收益可观但需硬件或深度运行时配合[^29^][^30^]。我方若实现真正的多租户 QoS，属于产业空白区，但需评估在厂商封闭 DSP 固件之上能拿到多少调度抓手——现实路径是**系统服务层排队+抢占**而非 NPU 内核级抢占。 |
| 端云按隐私/成本/延迟路由 | **支持（方向正确，需自研抽象）** | 各平台均有雏形（Firebase Hybrid 回退[^44^]、华为 HPIC 三重匿名[^10^]、Apple PCC），但无可移植标准。我方路由层可作为独立组件价值点；需注意平台配额/前台限制使"端侧容量"高度动态，路由决策必须把 BUSY/quota/可用性状态作为一等输入[^36^]。 |
| 模型权重与 KV cache 可分页 | **挑战（当前平台均不支持，属前沿空白）** | 平台服务把权重/KV 完全黑盒化（AICore 常驻 4GB+[^6^]；ANE 权重编译期烘焙不可变[^19^]）。学术已有针对工作（mzCache MobiCom 2026[^33^]、S-LoRA unified paging[^9^]）。**需要修订**：若我方想在商用 NPU 上落地分页，短期只能在自研推理引擎（CPU/GPU 或 LiteRT NPU 路径）内做，无法复用平台系统服务的黑盒模型；建议将"可分页"目标限定于自托管模型路径，平台托管路径仅作回退。 |

---

## 5. 组件特有输出素材：端侧推理栈分层图——本维度覆盖层的玩家与开放程度

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 应用层                                                                        │
│  Android: ML Kit GenAI APIs(beta,前台+配额) / LiteRT / ONNX RT / LiteRT-LM      │
│  iOS: Foundation Models framework(Swift,无公开配额) / Core ML                  │
│  HarmonyOS: 小艺 Agent/Skill/MCP 接入(不直接暴露LLM API) / MindSpore Lite Kit   │
│  开放度: ●●○○ (任务级API开放;模型选择/版本/调度均不可控)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 系统服务层  ←★ 本维度核心层                                                    │
│  Android: AICore(APEX,system_server,Play分发,共享实例,LoRA registry,配额+前台闸)│
│           Android 17: NpuManager + NPU scheduling AIDL(@SystemApi,best-effort)│
│  iOS: Apple Intelligence 系统进程(SystemLanguageModel), guardrails 内建        │
│  HarmonyOS: 小艺系统智能体 + Pangu 端侧(HarmonyOS 7 宣称入内核), HPIC 隐私架构  │
│  开放度: ●○○○ (Google/Apple 开放调用不开放内部;Android 17 调度面仅系统API)      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 框架/运行时层                                                                   │
│  跨厂商抽象: LiteRT CompiledModel+Accelerator.NPU(高通/联发科一等支持,AOT+JIT,   │
│   AI Pack/PODAI 分发) / ONNX Runtime(QNN EP, Neuron EP)                        │
│  已弃用: Android NNAPI(Android 15 deprecated, HAL 保留给系统服务)              │
│  华为: NNRt(跨芯片,56算子,仅同步,优先级/性能模式可配) + MindSpore Lite           │
│  开放度: ●●●○ (LiteRT/ONNX 开源且厂商共建;但算子覆盖与性能仍 per-SoC 不均)       │
├─────────────────────────────────────────────────────────────────────────────┤
│ HAL/驱动层                                                                      │
│  Android NN HAL(AIDL,保留) / 厂商专有: Qualcomm FastRPC→cDSP/HTP               │
│   (libQnnHtp.so, context binary, 8级priority, 性能档位, ION/SMMU 零拷贝)       │
│  MediaTek Neuron runtime(libneuron_adapter/runtime, ncc-tflite 伙伴墙)          │
│  HarmonyOS: NNRt 对接的 AI 硬件驱动(共享内存零拷贝)                              │
│  开放度: ●●○○ (高通QNN对注册开发者开放;联发科离线编译器封闭;调度在固件内黑盒)    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 芯片层                                                                          │
│  Qualcomm Hexagon HTP(仅INT8/INT16,VTCM) / MediaTek MDLA+VPU /                 │
│  Apple ANE(固定功能,编译期烘焙权重,~32MB SRAM,IOSurface零拷贝) / 华为麒麟 NPU     │
│  开放度: ●○○○ (均无公开的虚拟化/多租户/抢占硬件接口;学术 V10 提出硬件辅助方案)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**本维度（系统级模型服务 + NPU 调度）覆盖中间两层（系统服务层、框架/运行时层）并向 HAL/芯片层下探：**
- 系统服务层玩家：Google AICore、Apple Foundation Models/Apple Intelligence、华为小艺+Pangu——三家均"开放调用、封闭调度"。
- 框架层玩家：Google LiteRT（+Qualcomm/MediaTek 官方共建 Accelerator）、Microsoft ONNX Runtime（QNN EP/Neuron EP）、华为 NNRt/MindSpore Lite——开放度最高的一层，也是跨厂商抽象事实上的收敛点。
- 调度层现状：Android 17 NpuManager/AIDL 是首个 OS 级 NPU 调度控制面雏形（2026，best-effort、@SystemApi）[^27^]；QNN context priority 是厂商侧仅有的多会话提示机制[^14^]；ANE 无任何调度暴露[^19^][^20^]。

---

## 6. 证据清单

| # | Claim | Source | URL | Date | Excerpt（原文逐字） | Confidence |
|---|---|---|---|---|---|---|
| 1 | ML Kit GenAI APIs 2025-05 对第三方开放，beta 无 SLA | WinBuzzer 引官方文档 | https://winbuzzer.com/2025/05/19/google-opens-gemini-nano-on-device-ai-to-android-app-developers-xcxwbn/ | 2025-05-19 | "is not subject to any SLA or deprecation policy," and that "changes may be made to this API that break backward compatibility." | high |
| 2 | AICore 为系统级服务，模型单实例多应用共享，APK 不含模型 | WinBuzzer 引官方文档 | 同上 | 2025-05-19 | "The underlying AICore system service manages the distribution and execution of GenAI models like Gemini Nano, allowing multiple apps to share a single model instance." | high |
| 3 | AICore 包名 com.google.android.aicore，Play Store 分发，统管模型下载/加速/内存 | 掘金 JibarOS（引 Android 官方文档架构图） | https://juejin.cn/post/7650741599726780451 | 2026-06-14 | "AICore 是 Google 提供的系统级 AI 服务，以 com.google.android.aicore 为包名通过 Play Store 分发，负责 Gemini Nano 模型的下载、版本管理和推理执行…模型在系统进程中仅加载一次，多应用共享" | medium-high |
| 4 | Apple Foundation Models framework：3B 端侧模型、Swift 集成、guided generation、tool calling、iOS 26 起、Apple Intelligence 设备可用 | Apple Newsroom | https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/ | 2025-09-29 | "send requests to the 3 billion parameter on-device model right from their existing code. The framework provides guided generation… The Foundation Models framework is available with iOS 26, iPadOS 26, and macOS 26, and works on any Apple Intelligence-compatible device when Apple Intelligence is enabled." | high |
| 5 | AFM 端侧 ~3B，<4bit 量化，rank-16 LoRA 数十 MB，动态加载/换出 | Apple 技术报告 arXiv:2407.21075 | https://arxiv.org/html/2407.21075v1 | 2024-07-29 | "for the ∼3 billion parameter on-device model, the parameters for a rank 16 adapter typically require 10s of megabytes. The adapter models can be dynamically loaded, temporarily cached in memory, and swapped—giving our foundation model the ability to specialize itself on the fly for the task at hand while efficiently managing memory and guaranteeing the operating system's responsiveness." | high |
| 6 | AICore 内部架构：APEX/system_server、LoRA Adapter Registry、卸载 40MB adapter ~200ms、底座常驻 4GB+、SELinux 隔离 /data/misc/aicore | xckevin.com 逆向分析 | https://xckevin.com/en/blog/android-aicore-gemini-nano/ | 2025-05-21 | "AICore exists as an APEX package and runs inside the system_server process… AICore is aware of system memory pressure and actively unloads LoRA weights when memory is low. On a Pixel 8 Pro, unloading a 40 MB LoRA adapter takes about 200 ms, while the base model remains in 4 GB+ resident memory." | low-medium（第三方逆向，非官方） |
| 7 | M4：底座模型作为固件，由 OS+硬件管理，App 通过 adapter 调用 | arXiv:2308.14363（MobiCom 2024） | https://arxiv.org/html/2308.14363v3 | 2024-03-12 | "mobile OS and hardware jointly manage a foundation model that is capable of serving a wide array of mobile AI tasks. This foundation model functions akin to firmware, unmodifiable by apps or the OS, exposed as a system service to Apps." | high |
| 8 | EdgeLoRA：端侧多租户 LoRA serving，1,000+ adapter，吞吐 2–4× | arXiv:2507.01438（MobiSys 2025） | https://arxiv.org/abs/2507.01438 | 2025-07-02 | "EdgeLoRA can serve over 1,000 adapters simultaneously on Jetson Orin AGX… In contrast, llama.cpp is limited to serving only 50 adapters due to memory constraints. Overall, EdgeLoRA achieves 2-4x the throughput higher than llama.cpp" | high |
| 9 | S-LoRA：数千并发 LoRA（云端对照） | MLSys 2024（经论文清单） | https://github.com/byungsoo-oh/ml-systems-papers | — | "[MLSys'24] S-LoRA: Serving Thousands of Concurrent LoRA Adapters" | high |
| 10 | HDC 2026：小艺系统级智能体、2100+ Skill、多模型路由（Pangu/DeepSeek）、HPIC 隐私架构、20+ AI 能力日调用 36.8 亿次 | firecat-web（会议报道） | https://www.firecat-web.com/daily-news/10289 | 2026-06-14 | "系统应用全面Skill化，2100多项系统能力可被小艺调用…引入多个业界大模型（如Pangu、DeepSeek）…开放20多项AI子系统能力…日调用量36.8亿次…通过OHTTP协议和端云协同加密实现用户身份三重匿名盲化" | medium（会议报道，非官方原文） |
| 11 | HarmonyOS 向 Agent 架构演进，AI 子系统 3.68B 次/日调用，模型通用插座多模型路由 | Pandaily | https://pandaily.com/harmonyos-agent-os-hdc-2026-xiaoyi-celina-jun2026 | 2026-08-28 | "The AI subsystem handles an impressive 3.68 billion API calls daily across 20 opened capabilities… Xiaoyi underlying architecture has been rebuilt around a multi-model universal socket." | medium |
| 12 | HarmonyOS 7 宣称 Pangu 6.0 嵌入系统内核，Mate 90 首发 | chinatechdaily 转 ITHome | https://chinatechdaily.org/archive/china-daily/2026-06-12/ | 2026-06-12 | "calling it the first Chinese mobile operating system with the Pangu 6.0 large model embedded directly in the system kernel rather than called as a cloud service" | medium-low（媒体转述） |
| 13 | QNN 统一 API + 后端库，HTP 仅量化 | SECO 开发者文档 | https://developer.seco.com/clea-os/scarthgap_2-05-00/npu/qcom-npu/ | —（2025 前后） | "QNN exposes a single API with one backend library per accelerator: libQnnCpu.so / libQnnGpu.so / libQnnHtp.so (Hexagon NPU (HTP), quantized only (INT8/INT16))" | high |
| 14 | QNN 提供 8 级 context priority 与性能/功耗档位、vTCM 配置 | ONNX Runtime QNN EP 文档 | https://github.com/onnxruntime/onnxruntime-qnn/blob/main/docs/execution_providers/QNN-ExecutionProvider.md | —（2026 在维护） | "qnn_context_priority: 'low'|'normal_low'|'normal'|'normal_high'|'high'|'high_plus'|'critical'|'critical_plus'" | high |
| 15 | QNN HTP 性能模式 burst/high_performance/balanced/low_power | Edge Impulse 教程 | https://docs.edgeimpulse.com/tutorials/topics/android/qnn-acceleration | 2026-10-27 | "htp_performance_mode… burst: Maximum speed and higher power use (the default); high_performance… balanced… low_power" | medium-high |
| 16 | MediaTek NeuroPilot：MDLA+VPU 双引擎，ncc-tflite 编译器在伙伴注册墙后 | GitHub mdla-cnn-engine | https://github.com/Peterc3-dev/mdla-cnn-engine | 2026-06-05 | "the offline compiler ncc-tflite that turns a TFLite model into a .dla lives inside the Genio / NeuroPilot SDK, which is behind a partner registration wall." | high |
| 17 | LiteRT NeuroPilot Accelerator：Dimensity 7300–9500，Gemma-3n E2B 1600+ prefill / 28 decode tok/s @4K，12× CPU / 10× GPU，AOT 建议（270M 端上编译 >1min） | MarkTechPost 转 Google developers blog | https://www.marktechpost.com/2025/12/09/google-litert-neuropilot-stack-turns-mediatek-dimensity-npus-into-first-class-targets-for-on-device-llms/ | 2025-12-09 | "On a Dimensity 9500 class NPU, Gemma-3n-E2B can reach more than 1600 tokens per second in prefill and 28 tokens per second in decode at 4K context, with measured throughput up to 12 times CPU and 10 times GPU for LLM workloads." | high |
| 18 | 联发科 NNAPI 库使任何 NNAPI 应用可用其加速核（历史路径） | MediaTek 开发者中心 | https://developer.mediatek.com/ai/6423c8b6c612745b3a4baa2c.html | 2026-11-05 | "The main library which implements most of this capability is an optimized Android Neural Network API (NNAPI) library… any NNAPI application can use MediaTek acceleration cores without any special changes to the application code." | high |
| 19 | ANE 编程模型：compile-then-dispatch，MIL→E5 微码，权重编译期烘焙，IOSurface 零拷贝，~32MB SRAM 溢出性能降 30% | arXiv:2603.06728 | https://arxiv.org/html/2603.06728v1 | 2026-03-06 | "The ANE operates on a compile-then-dispatch model… the ANE bakes weights at compile time: weight tensors are embedded in the compiled program and cannot be mutated post-compilation… Performance drops ∼30% when working sets exceed the 32 MB SRAM budget" | medium-high |
| 20 | ANE 不提供通用计算 API，Core ML 运行时决定 ANE/GPU/CPU 放置 | Contra Collective | https://contracollective.com/blog/gpu-vs-apple-neural-engine-local-llm-inference-m5-max-2026 | 2026-07-10 | "You do not program it directly. You hand CoreML a model, CoreML compiles the graph, and the runtime decides which operations land on the ANE… The programming surface is the CoreML graph, not a general compute API." | medium-high |
| 21 | NNAPI 于 Android 15 弃用，官方迁移指南推荐 TF Lite GPU runtime | meetonfriday 逐字引官方文档 | https://meetonfriday.com/posts/666bbf67/ | 2025-03-10 | "Warning: With the release of Android 15, NNAPI will be deprecated. While you can continue to use NNAPI, we expect the majority of devices in the future to use the CPU backend, and therefore for performance critical workloads, we recommend migrating to alternative solutions, for example the TF Lite GPU runtime." | high |
| 22 | NNAPI 弃用后 NN HAL 保留，AICore 内部经 HAL 与驱动通信；AICore 内部用 NNAPI 加速 | Google AI 官方论坛（Googler 答复） | https://discuss.ai.google.dev/t/how-to-deploy-aicore-gemini-nano-on-pixel-other-devices/93284 | 2025-08-07 | "AICore uses NNAPI internally for hardware acceleration… the Neural Networks Hardware Abstraction Layer (HAL) interface continues to be supported. This is the layer that system services (like AICore) can use to communicate with hardware drivers" | high |
| 23 | LiteRT 与 Qualcomm/MediaTek 合作把 NPU 做成一等加速目标，自动下载 SDK 与模型分发 | SegmentFault 转 Google I/O 2025 博客 | https://segmentfault.com/p/1210000046575777 | 2025-05-23 | "通过与 Qualcomm 和 MediaTek 合作在 LiteRT 中添加对其 NPU 的支持，还简化 API 让开发者指定目标后端…NPUs 能比 CPU 快 25 倍且功耗低五分之一" | medium-high |
| 24 | 2026-01 LiteRT NPU 生产级集成可用，统一 AOT/JIT 工作流，宣称最高 100× CPU / 10× GPU | jobcher 转 LiteRT 官方更新 | https://www.jobcher.com/new/daily/github_trending_2026-01-30/ | 2026-01-30 | "面向 MediaTek 与 Qualcomm 的首批'生产级'NPU 集成已可用，并给出'最高可达 CPU 100×、GPU 10×'这类性能宣称" | medium-high（厂商宣称值） |
| 25 | ONNX Runtime 在 MediaTek Genio 经 NeuronExecutionProvider 直接跑 NPU | ProventusNova | https://proventusnova.com/blog/mediatek-genio-inference-offline-neuropilot | 2026-07-13 | "on Genio 520/720 ONNX Runtime also runs directly on the NPU via the NeuronExecutionProvider" | medium-high |
| 26 | QNN EP 直通 HTP，Hexagon NPU 为主要执行路径 | ibetter.kr ONNX RT 教程 | https://text.ibetter.kr/onnx-runtime/part-05-execution-provider-마스터/ch-07-qnn-ep-—-qualcomm-모바일-npu | 2026-06-11 | "QNN EP는 Qualcomm AI Engine Direct SDK(구 QNN SDK)를 기반으로 합니다… HTP (Hexagon Tensor Processor) ← 주요 실행 경로" | medium |
| 27 | Android 17/API 37：FEATURE_NEURAL_PROCESSING_UNIT、NpuManager、NPU scheduling AIDL（PriorityManager/SchedulingConfig/WorkInfo/ISchedulingCallback），best-effort、@SystemApi | androidperformance wiki（读 AOSP 源码） | http://wiki.androidperformance.com/part1-fundamentals/ch05-cpu-power/05-ondevice-ai-runtime-npu.html | 2026 | "Android 17 的 AOSP 新增 NpuManager 模块和 hardware/interfaces/npu/aidl/…数值更小的 priority 表示更高优先级，厂商实现以尽力而为（best-effort）的方式处理，不保证固定完成时间…NpuManager 的 Java 接口是受权限保护的系统 API（@SystemApi）" | medium-high（源码阅读转述，建议后续核对 AOSP） |
| 28 | HarmonyOS NNRt：跨芯片运行时、零拷贝共享内存、优先级/性能模式、仅 56 算子、仅同步推理、并发取决于驱动 | OpenHarmony 官方文档 | https://github.com/openharmony-rs/openharmony-docs/blob/master/zh-cn/application-dev/ai/nnrt/Neural-Network-Runtime-Kit-Introduction.md | 2024-04-12（持续更新） | "NNRt目前支持常用算子56个…NNRt目前仅支持同步推理…NNRt不支持多线程并发构图，是否支持并发编译和执行取决于底层硬件驱动是否支持…通过AI硬件驱动上的共享内存可以实现输入和输出数据的'零拷贝'" | high |
| 29 | V10：硬件辅助算子级 NPU 多租户，吞吐 1.57×、尾延迟 1.74×、面积开销 <0.03% | ISCA 2023 论文 | https://jianh.web.engr.illinois.edu/papers/v10-isca23.pdf | 2023 | "V10 improves NPU utilization by 1.64%, increases the aggregated throughput by 1.57x for collocated ML workloads, reduces the average latency of each workload by 1.56x, and decreases the tail latency by 1.74x" | high |
| 30 | Pantheon：移动 GPU 可抢占多 DNN 推理 | MobiSys 2024 | https://dl.acm.org/doi/10.1145/3643832.3661878 | 2024-06 | "Pantheon: Preemptible Multi-DNN Inference on Mobile Edge GPUs. In MOBISYS '24 (pp. 465-478)." | high |
| 31 | llm.npu：端侧 NPU 卸载 prefill，目标场景为 LLM-as-a-System-Service | ASPLOS 2025 论文 | https://xumengwei.github.io/files/ASPLOS25-NPU.pdf | 2025 | "It supports various mobile-sized LLMs on devices and can be integrated as part of LLM-as-a-System-Service in mobile OS or mobile application services" | high |
| 32 | Agent.xpu：单设备异构 SoC 上 agentic LLM 工作负载调度 | arXiv:2506.24045 | https://arxiv.org/html/2506.24045 | 2026-01-06 | "These systems target multi-tenant cloud settings with abundant resources, whereas our focus is on single-device agents operating under tight SoC constraints." | high |
| 33 | MobiCom 2026：mzCache（多任务下端侧 LLM 内存管理）、NPUGen（NPU 作 KV 生成器）；EuroSys 2026：移动 NPU 扩展推理时计算 | Awesome-LLM-IoT-Papers 清单 | https://github.com/KAIWEILIUCC/Awesome-LLM-IoT-Papers | 2025-09-19 | "NPUGen: NPU as KV Generator for Stable Long-Context Mobile LLM Inference. (MobiCom 2026, accepted)… mzCache: On-Device LLM Memory Management under Multitasking. (MobiCom 2026, accepted)… Scaling LLM Test-Time Compute with Mobile NPU on Smartphones. (EuroSys 2026)" | medium-high（会议录用清单） |
| 34 | EuroSys 2026 论文实证基于 QNN SDK/HTP/FastRPC 的手机 NPU LLM 推理 | arXiv:2509.23324 | https://arxiv.org/html/2509.23324v1 | 2025-05-16 | "Qualcomm® ai engine direct sdk… Unified API for AI development on Qualcomm accelerators (Hexagon DSP, Kryo CPU, Adreno GPU). Supports direct offloading for TensorFlow Lite/ONNX Runtime, with HTP… backend optimizations." | high |
| 35 | Prompt API 输入 <4,000 token，输出 >256 token 场景不建议；输出不做内容审核 | Capawesome 插件文档（逐字引官方） | https://capawesome.io/docs/sdks/capacitor/mlkit/genai-prompt/ | 2026-07-10 | "The prompt must be under 4,000 tokens (or about 3,000 English words). Use cases that require a long output (more than 256 tokens) should be avoided… the output is not moderated." | high |
| 36 | AICore 配额与前台限制错误码（官方 ML Kit 文档逐字） | Capawesome 博客引官方文档 | https://capawesome.io/blog/how-to-use-gemini-nano-in-a-capacitor-app/ | 2026-09-29 | "AICore enforces an inference quota per app. Making too many GenAI API requests in a short period will result in an ErrorCode.BUSY response… ErrorCode.PER_APP_BATTERY_USE_QUOTA_EXCEEDED… GenAI API inference is permitted only when the app is the top foreground application… ErrorCode.BACKGROUND_USE_BLOCKED" | high |
| 37 | Apple AFM 2025 技术报告：2-bit QAT 权重、LoRA 质量恢复 adapter、服务器模型 PT-MoE | arXiv:2507.13575 | https://arxiv.org/pdf/2507.13575 | 2025-07 | "To recover model quality lost during the compression stages, we apply Low-Rank Adaptation (LoRA) adapters to both models… Because the core model weights remain frozen, the LoRA parameters effectively compensate for the lossy compression without requiring full model retraining." | high |
| 38 | Foundation Models 上下文 4,096 token（输入+输出合计）；guardrail 误报存在 | natashatherobot（WWDC25 实测） | https://www.natashatherobot.com/p/apple-foundation-models | 2025-06-28 | "The FoundationModel is limited to only 4096 tokens - both input AND output!!" | high |
| 39 | WWDC26 示例上下文 8,192 token；AFM 3 Core 接受图像输入 | slash-digital（查官方文档） | https://slash-digital.io/en/insights/small-models-on-device/ | 2026-09-26 | "Foundation Models framework; 8,192-token context in Apple's WWDC26 sample" | medium |
| 40 | Foundation Models 可用性三态：device not eligible / Apple Intelligence 未启用 / model not ready | 同上（引 Apple 文档） | https://www.natashatherobot.com/p/apple-foundation-models | 2025-06-28 | "there are currently three reasons for the model being unavailable: The device is not eligible… Apple Intelligence is not enabled… Model not ready" | high |
| 41 | FastVLM-0.5B 于 Snapdragon 8 Elite Gen 5 NPU：TTFT 0.12s、prefill >11,000 tok/s、decode >100 tok/s | yomu.fyi 转 Google 博客 | https://yomu.fyi/post/unlocking-peak-performance-on-qualcomm-npu-with-litert | 2025-11-24 | "FastVLM-0.5B uses int8 weight and int16 activation quantization plus specialized attention kernels, achieving 0.12-second TTFT, over 11,000 prefill tokens per second, and over 100 decode tokens per second." | medium-high（厂商宣称值） |
| 42 | MediaTek Genio NPU 精度支持：MDLA FP16/INT16/INT8；VPU FP32/FP16/INT16/INT8 | SECO 开发者文档 | https://developer.seco.com/clea-os/scarthgap_2-04-00/npu/mtk-npu/ | — | "MDLA (MediaTek Deep Learning Accelerator): a CNN accelerator supporting FP16, INT16 and INT8. VPU (Vision Processing Unit, a Cadence Tensilica DSP): a general AI/vision DSP supporting FP32, FP16, INT16 and INT8." | high |
| 43 | 华为端侧 30B 模型常驻运存（2B 激活）、Pangu 2.0 开放 512K 上下文（媒体线索） | 新浪科技横评 | https://k.sina.com.cn/article_7879849013_1d5acf43506802pp26.html | 2026-07-25 | "华为将原生30B入端模型（包含2B激活参数）常驻手机运存，通过量化剪枝和专家预测算法…开放Pangu 2.0大模型支持512K长上下文" | low-medium |
| 44 | Gemini Nano 不可用时官方建议经 Firebase AI Logic Hybrid API 回退云端 | Omcircle AI Radar | https://omcircle.ai/radar/ai-models/gemini-nano | 2026-10-21 | "an app can use the Firebase AI Logic Hybrid API to fall back to Gemini models in the cloud when Nano is unavailable or unsupported on a device." | medium-high |
| 45 | LiteRT Qualcomm Accelerator 支持 90 个 LiteRT 算子，72 个基准模型中 64 个可全量卸载到 NPU | yomu.fyi 转 Google 博客 | https://yomu.fyi/post/unlocking-peak-performance-on-qualcomm-npu-with-litert | 2025-11-24 | "The accelerator supports 90 LiteRT ops and fully delegates 64 of 72 benchmarked vision, audio, and NLP models to the NPU." | medium-high |
| 46 | FastRPC 提供 ION 内存经 SMMU 与 DSP 零拷贝共享 | Qualcomm Dragonwing 官方文档 | https://dragonwingdocs.qualcomm.com/API_Documentation/public/docs/api/fastrpc/remote | 2026-10-13 | "Register a DMA handle with FastRPC to enable zero-copy sharing of ION memory with DSP via SMMU." | high |
| 47 | HarmonyOS NEXT 内建 PanGu-Σ + MindSpore + NNRt Kit；Harmony Intelligence 基于 Pangu 5.0（含 Embedded 变体） | Wikipedia（HarmonyOS NEXT） | https://en.m.wikipedia.org/wiki/HarmonyOS_NEXT | 2024-01-29（持续更新） | "Harmony Intelligence backend stack embedded across the OS, with PanGu 5.0 LLM with Embedded variant, MindSpore AI framework with Neural Network Runtime API kit with smarter Celia virtual assistant." | medium-high |
| 48 | Gemini Nano 版本随设备不同、同 prompt 输出可能不同；getBaseModelName() 可读版本 | Omcircle AI Radar | https://omcircle.ai/radar/ai-models/gemini-nano | 2026-10-21 | "Which version of Nano a phone has, an app can read with getBaseModelName(); Google warns that versions can give different answers to the same prompt." | medium-high |

---

### 调研方法与覆盖说明
- 独立搜索次数：5 轮 × 4 查询 = 20 次不重复关键词搜索（AICore 架构/ML Kit 配额/Apple FM/鸿蒙小艺/QNN/NeuroPilot/ANE/NNAPI/多租户调度/移动 NPU 学术/Apple 技术报告/I-O 2025/M4/EdgeLoRA/官方文档原文/HarmonyOS NNRt/QNN context/AI Hub AOT/Android 17 NpuManager/NNRt 文档/Apple 并发限制/QNN priority）。
- 一手来源覆盖：Apple Newsroom、Apple 技术报告（arXiv 2407.21075 / 2507.13575）、OpenHarmony 官方文档、Qualcomm Dragonwing 官方文档、ONNX Runtime QNN EP 官方文档、Google AI 官方论坛、ISCA/MobiSys/ASPLOS/MobiCom 论文原文。developers.google.com 与 developer.apple.com 直链在本环境被审计拦截，ML Kit 官方条款以两处独立第三方文档的逐字引用交叉验证（[^35^][^36^]）。
- 明确标注的低置信项：AICore 内部 LoRA 细节（[^6^]，逆向博客）、华为 30B 端侧模型（[^43^]，媒体）、Pangu 6.0 入内核（[^12^]，媒体转述）、Android 17 NpuManager（[^27^]，源码阅读 wiki，建议 lead 安排 AOSP 源码核对）。

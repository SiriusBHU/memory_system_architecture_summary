# C1a 系统模型服务与 NPU 栈（子模块调研）

**范围**：推理组件 Q1（系统级端侧模型服务）、Q2（NPU 编程与调度模型）、Q3（端侧推理框架格局）、Q7（模型生命周期）。
**立场评审**：INF-1、INF-3，以及 INF-2、INF-5 中与系统服务和框架支持相关的部分。
**日期**：2026-11-05。**检索说明**：WebSearch 额度在调研中途用尽，后半段仅靠 WebFetch 直接抓取官方页面；国内手机厂商、HarmonyOS 2026 年现状、自带模型的应用占比三块因此留有空白，已在 §8 列出。
**证据等级**：A 官方文档 / 同行评议 / 源码；B 厂商口径；C 权威媒体 / 第三方 / 预印本；D 传闻。**成熟度**：L1 论文；L2 原型；L3 生产可用；L4 平台默认或规模量产。
**术语**：AICore 与 Foundation Models framework 与 Windows AI APIs 是三套不同的系统服务，不混用；Core ML 与 Core AI 是 Apple 的两个不同框架。

---

## §0 摘要

1. 系统级共享底座已是三大平台的既成事实：Android 的 AICore 称 Gemini Nano 已装在超过 1.4 亿台设备上（B，E1），Apple 的 Foundation Models framework 在 iOS 26 起开放（A，E11），Windows 的 Phi Silica 在 Copilot+ PC 上预装于 NPU（A，E19）。INF-1 的方向得到支持。
2. 但「共享」是受限共享，不是编解码器式的共享。AICore 只允许前台应用推理，后台包括前台服务一律返回 `BACKGROUND_USE_BLOCKED`；每应用有短窗口和长窗口两级配额；Prompt API 输入窗口约 4000 token；官方页面未描述并发语义（A，E2、E3）。设计时要把「准入控制」当作现实起点，而不是「调度 QoS」。
3. 跨厂商 NPU 抽象层的成败已有定论：NNAPI 自 Android 15 弃用，Google 的理由是模型形态变化快、需要可频繁更新的栈，改走 Play services 里可更新的 LiteRT 与 AICore（A，E4）。接替者 LiteRT 的 NPU 路径是「Google 加芯片厂商 SDK」的形态：每个 SoC 一个预编译模型文件，经 Google Play for On-device AI 分发（A，E8、E9、E10）。判断：抽象层存活的条件是 OS 厂商控制分发与更新通道，而不是 HAL 接口本身。
4. 模型生命周期是平台的真实痛点，且正在发生：Windows 宣布 Phi Silica 在 2027-01 被 Aion Instruct 取代并从零售设备移除，开发者必须重训 LoRA（A，E21）；Apple 适配器每个约 160MB，只对一个系统模型版本有效，系统模型每次更新都要重训（A，E14）；AICore 文档要求开发者对每个 Gemini Nano 版本重新测试提示词（A，E2）。
5. NPU 并不总是更快：2026-05 的预印本在一款 CPU-NPU SoC 上测得，prefill 阶段 CPU 最多快 1.6 倍，decode 阶段 NPU 仅 1.05–1.2 倍，提高 NPU 卸载比例使能耗最多上升 51%（C，E25）；2026-07 的测量研究（已被 SIGMETRICS 2027 接收）则发现 NPU 最适合 prefill、CPU 反而最适合 decode，框架间差距在 NPU 上最大可达 10 倍（C，E26）。两篇结论在 prefill 上相反，说明结果强依赖具体 SoC 与框架。
6. 多租户 NPU 调度在生产系统中不存在公开的抢占机制：NNRt 文档仅说「并发编译和执行取决于底层驱动」（A，E22），AICore 用 BUSY 错误串行化（A，E2）。学术侧只有 Agent.xpu 这类 L1 工作，报告 reactive 延迟降低至少 91%（C，E26b）。
7. 多框架重复占用没有公开数据；按本文估算，12GB 手机上两个自带 2–3GB 级模型的应用同时驻留，可吃掉约一半内存（估算，见 §7.2）。系统服务化是唯一不依赖开发者自律的解法，但目前被第三方绕开的主因（能力、配额、版本不可控）缺少直接数据（待核实）。
8. Apple 的走向对 INF-1 是挑战：iOS 27 同时给出系统模型、可插拔的第三方模型协议（`LanguageModel`）、用 Core AI 自带模型、并让系统模型运行在 PCC 上（A，E11）。「底座共享」被扩展成「接口共享、模型可换」。
9. Linux accel 子系统是内核侧唯一的跨厂商收敛点，但它统一的是设备节点和提交框架，不是算子与编译器（A，E23）；手机上的 NPU 驱动与编译器仍由芯片厂商闭源控制（判断）。
10. 能耗与热：Android 有 `getThermalHeadroom` 可预测未来若干秒的热余量（A，E27），但该 API 面向游戏等通用负载，未发现 AICore 或 ML Kit 向应用暴露每 token 能耗或推理热状态（未找到公开资料）。

---

## §1 技术谱系表

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 系统服务式共享模型 | AICore + ML Kit GenAI（Prompt API 等） | Google | 2023 起；Prompt API 2025-10 Alpha，文档见 `genai-prompt:1.0.0-beta4` | 模型由系统服务持有，应用共享一份，配额与前台限制由服务执行 | L4（Gemini Nano 装机量）；Prompt API 本身 L3 beta | 本身即端侧方案 |
| 系统服务式共享模型 | Foundation Models framework（SystemLanguageModel、PCC 模型） | Apple | 2025 引入，2026 扩展 | guided generation、tool calling、适配器、`LanguageModel` 协议统一本地与服务器模型 | L4 | 本身即端侧方案 |
| 系统服务式共享模型 | Windows AI APIs（Phi Silica、OCR 等） | Microsoft | 2024 起 | NPU 预装模型，Limited Access Feature 解锁；2027-01 换为 Aion Instruct | L4（Copilot+ PC） | 需改造：PC 的内存与散热预算更宽 |
| 系统服务式共享模型 | Chrome Prompt API（浏览器内置 Gemini Nano） | Google | Chrome 148 上线网页版 | 浏览器托管模型，网页经 API 调用；需 22GB 空闲存储与 16GB 内存等 | L3 | 不可迁移到手机：官方明确不支持 Android、iOS |
| 系统服务式共享模型 | 华为盘古端侧模型与小艺、意图框架 | 华为 | 2024-06 起 | 系统级智能体，向第三方开放意图框架 | 待核实（2026 状态未查到） | 本身即端侧方案 |
| 跨厂商 NPU 抽象 | NNAPI | Google | 2017 引入，Android 15 弃用 | 统一接口但不统一行为，性能留给厂商驱动 | L4 → 已弃用 | 已失败 |
| 跨厂商 NPU 抽象 | LiteRT + NPU accelerator（Qualcomm、MediaTek、Google Tensor） | Google 与芯片厂商 | 2025-12 MediaTek，2026-01 总览 | 每 SoC 预编译，PODAI 分发，缺失时回退 GPU/CPU | L3 | 本身即端侧方案 |
| 跨厂商 NPU 抽象 | Windows ML + ONNX Runtime EP | Microsoft | 2025-09-23 GA | EP 以 MSIX 形式由 Windows Update 分发，应用不再打包 IHV SDK | L4 | 需改造：Windows 驱动模型与 Android HAL 不同 |
| 跨厂商 NPU 抽象 | NNRt（OpenHarmony / HarmonyOS） | OpenHarmony | 持续 | 北向 Native 接口加南向 HDI，支持离线模型与编译缓存；当前 56 个算子，仅同步推理 | L3 | 本身即端侧方案 |
| 跨厂商 NPU 抽象 | Linux accel 子系统 | Linux 内核社区 | 2022 起 | `/dev/accel/accel*`，通用设备节点，驱动含 amdxdna、qaic、rocket、ivpu、Ethos-U | L3 | 需改造：手机 NPU 驱动多为厂商树外实现 |
| 芯片厂商栈 | QAIRT / Qualcomm AI Engine Direct、GenieX | Qualcomm | GenieX 文档含 QAIRT 2.45 | 双运行时：llama.cpp（含 Hexagon HTP）与 QAIRT（仅 NPU，预编译 AI Hub 模型） | L3 | 本身即端侧方案 |
| 芯片厂商栈 | NeuroPilot | MediaTek | 2025-12 LiteRT 接入 | 编译器加运行时，LiteRT 作为统一外壳 | L3 | 本身即端侧方案 |
| 芯片厂商栈 | Core AI（`.aimodel`，设备与 OS 版本绑定的特化产物） | Apple | WWDC26（2026-06） | 推理框架，Apple Intelligence 底层，在设备上特化并缓存 | L4（系统内部）；对第三方 L2–L3 | 本身即端侧方案 |
| 开源推理框架 | ExecuTorch 1.0 | Meta | 2025-10-22 GA | 面向边缘的 PyTorch 运行时；Vulkan GPU 后端升为生产；新增 Samsung Exynos NPU、NXP、OpenVINO 等后端 | L3 | 本身即端侧方案 |
| 开源推理框架 | llama.cpp、LiteRT-LM、MNN、MLC-LLM、MLX、mllm、PowerInfer | 社区 / Google / 阿里 / 各高校 | 各异 | 未逐一核实，见 §8 | L2–L3（待核实） | 待核实 |
| 学术：NPU LLM 加速 | llm.npu | 北大、北邮等（作者 Daliang Xu 等） | 2024-07 预印本，v2 2024-12 | 报告 prefill 平均快 22.4 倍、节能 30.7 倍（论文自报） | L1 | 需改造：依赖具体 NPU |
| 学术：异构 SoC | HeteroInfer（arXiv 题为 Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference） | 上海交大（作者 Le Chen 等） | 2025-01，v2 2025-10 | GPU+NPU 并用，端到端比单后端快 1.34–6.02 倍（论文自报）；会议与年份待核实 | L1 | 需改造 |
| 学术：多负载调度 | Agent.xpu | 北大（作者 Xinming Wei 等） | 2025-06，v2 2026-01 | 异构执行图加 NPU-iGPU 协同加细粒度抢占，reactive 延迟降低至少 91% | L1 | 需改造 |
| 学术：测量 | When NPUs Are Not Always Faster；Is Your NPU Ready for LLMs | 作者见 §8 | 2026-05；2026-07（v2 2026-10） | 阶段级与跨层测量，纠正「NPU 必胜」的预设 | L1（后者已接收） | 不适用 |

---

## §2 关键数据

| 指标 | 数值 | 条件（硬件 / 模型 / 负载） | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| Gemini Nano 装机量 | 超过 1.4 亿台 | Google 口径，设备范围未细分 | E7 | 2026-04-02 | B |
| AICore 前台限制 | 非前台一律拒绝，含前台服务 | ML Kit GenAI API，错误码 `BACKGROUND_USE_BLOCKED` | E2 | 页面未标日期，2026-11 抓取 | A |
| AICore 配额层级 | 短窗口 `BUSY`；长窗口（如每日）`PER_APP_BATTERY_USE_QUOTA_EXCEEDED` | 每应用；具体数值未公开 | E2 | 同上 | A |
| Prompt API 上下文 | 输入不超过 4000 token，长输出（4K 以上）不建议 | Gemini Nano，ML Kit Prompt API | E3 | 同上 | A |
| 首次推理加载 | 约 1 分钟 | AICore 开发者预览，模型载入内存；出现 `BUSY` 提示可能另有大模型在用 | E5 | 同上 | A |
| 前缀缓存收益 | 1000 token 前缀加 100 token 后缀：2.11 s 降至 0.5 s；300 加 50：0.82 s 降至 0.45 s | Pixel 9，Google 文档标注为估算值 | E6 | 同上 | B |
| 前缀缓存存放 | 隐式缓存加密存放在应用私有存储，LRU 淘汰 | 仅文本，实验性 | E6 | 同上 | A |
| Gemini Nano 4 对比 | 比上代快至多 4 倍，省电至多 60% | Gemma 4 为其基础模型；基线与设备未说明 | E7 | 2026-04-02 | B |
| Gemma4-E2B 文件大小 | 2642 MB（4-bit 每通道，上下文 8192） | Google Tensor G6，LiteRT-LM | E9 | 页面抓取于 2026-11 | A |
| Gemma3-1B NPU 文件大小 | Qualcomm 657–658 MB；MediaTek 985–986 MB；Tensor 1704 MB（8-bit） | 同一模型在不同 SoC 上产物不同，上下文均为 1280 | E9 | 同上 | A |
| MediaTek NPU 吞吐 | Gemma 3n E2B：prefill 超过 1600 tok/s，decode 28 tok/s（4K 上下文） | Dimensity 9500，vivo X300 Pro，LiteRT NeuroPilot Accelerator | E10 | 2025-12-08 | B |
| MediaTek 端侧编译耗时 | Gemma 3 270M 端侧编译超过 1 分钟 | 因此官方建议生产环境 AOT | E10 | 2025-12-08 | B |
| NPU 对比 GPU | NPU 比 GPU 快至多 10 倍、比 CPU 快至多 100 倍；Gemma 3 1B 在 Galaxy S25 Ultra 上 NPU prefill 约为 GPU 的 3 倍 | Google 与芯片厂商口径 | E8 | 2026-01-28 | B |
| LiteRT NPU 覆盖 | Tensor G5/G6；Qualcomm SM8750/SM8650/SM8550；MediaTek MT6989/MT6991；Intel PantherLake/LunarLake | LiteRT-LM 文档支持表 | E9 | 同上 | A |
| NPU 阶段对比 | prefill CPU 最多快 1.6 倍；decode NPU 仅 1.05–1.2 倍；提高卸载使能耗最多上升 51% | CPU-NPU 异构 SoC，具体芯片页面未标 | E25 | 2026-05-22 | C |
| 框架间差距 | NPU 上框架间差异最大 10 倍；仅调 CPU 频率省电最多 39.7%；能耗导向配置使 NPU 后端能耗最多降 53.2% | 5 个框架（含 llama.cpp、GENIE）、3 个后端；SoC 页面未标 | E26 | 2026-07-06，v2 2026-10-16 | C |
| Agent.xpu | 主动负载吞吐 1.2–4.9 倍；reactive 延迟至少降低 91% | 对比 iGPU-only 工业引擎与静态 NPU-iGPU 划分；芯片未标 | E26b | 2026-01-06（v2） | C |
| llm.npu | prefill 平均快 22.4 倍，节能 30.7 倍，十亿级模型 prefill 超过 1000 tok/s | 论文自报 | E28 | 2024-12（v2） | C |
| Genie 解码速率 | Qwen3-4B w4a16 约 24（8 Elite）至 29（8 Elite Gen 5）tok/s；Llama 3.2 3B 约 10 tok/s | 第三方模型页与博客，列含义为推断，博客数字自相矛盾 | E24 | 2026-03 | D（线索，正文引用须标「待核实」） |
| Apple 适配器体积 | 每个约 160MB；每个适配器仅对应一个系统模型版本；训练工具箱 26.0.0 为最后一版，不兼容 27 及以后 | 需 32GB Apple silicon Mac 或 Linux GPU | E14 | 2026-11 抓取 | A |
| Apple 端侧上下文 | 示例读数 8192；PCC 模型 32000 | `SystemLanguageModel.contextSize` | E11 | 2026-06 | A |
| PCC 免费额度 | 首次下载量少于 200 万的开发者免云端费用 | 用户有每日额度，iCloud+ 更高 | E11、E12 | 2026-06 | A（E11）/ C（E12） |
| NNRt 限制 | 56 个算子；无 CPU 推理；仅同步推理；并发取决于驱动 | OpenHarmony 文档的 20250328 特性分支 | E22 | 2025-03 分支 | A |
| Windows ML 包装 | EP 为独立 MSIX，经 Windows Update 更新；NPU/GPU 优化 EP 需 Windows 11 24H2 | Qualcomm 驱动最低 30.0.140.0 | E15、E16 | 2026-10-05 更新 | A |
| Windows AI 模型替换 | 2026-11 起 Aion Instruct 进 Insider，2027-01 零售设备移除 Phi Silica | 开发者需重训 LoRA | E21 | 2026-10-16 更新 | A |
| Chrome 内置模型门槛 | 22GB 空闲存储、16GB 内存、4GB 以上显存、4 核 CPU；空闲低于 10GB 时模型被移除 | 桌面与 Chromebook Plus；不支持 Android、iOS | E19b | 2026-05 前后 | A |
| 热余量预测 | `getThermalHeadroom(n)` 预测 n 秒后余量；调用间隔不得少于 10 秒，否则返回 NaN | Android 11 起 | E27 | 页面未标日期 | A |

---

## §3 逐问题分析

### Q1 系统级端侧模型服务的现状

**现状。**三大平台形态趋同，开放程度不同。

- **Android AICore。**应用不直接碰模型，经 ML Kit GenAI API 进入 AICore（官方称其为「管理端侧基础模型的 Android 系统服务」），应用与各任务 API 共享同一个 Gemini Nano 基础模型（A，E2）。模型版本因设备而异：不同 Gemini Nano 版本对同一提示词输出不同，文档要求用 `getBaseModelName()` 检查并分别测试（A，E2）。2026 年设备分层为 nano-v2（Honor Magic 7/V5、OnePlus 13、Galaxy Z Fold7、小米 15 等）、nano-v3（Pixel 9/10、Galaxy S26、OPPO Find X9、vivo X300 等）、nano-v4（Pixel 11、Galaxy Z Flip8/Fold8，页面列出）（A，E2）。Prompt API 要求设备未解锁 bootloader，且依赖 `genai-prompt:1.0.0-beta4`，仍是 beta（A，E3）。2026-05 Google I/O 宣布 Nano 4 将于年内在旗舰机发布，并将加入 Structured Output 与 Prefix Caching（B，E7、E6）；2026-10 的 Android Dev Summit 又宣布 ML Kit 里 Agentic API 进入 alpha，内置函数自动执行、对话历史保存、编排循环与护栏（B，E7b）。判断：AICore 在往「系统托管会话与工具循环」走，这与 INF-1 同向，也触及 Q8（C1b 负责）。
- **Apple。**WWDC26 的 Foundation Models framework 增加图像输入、`LanguageModel` 协议（本地与服务器模型可互换）、`PrivateCloudComputeLanguageModel`、Dynamic Profiles、`usage` 里的 cached token 计数、Spotlight 本地 RAG 工具、整个核心框架开源（A，E11）。Anthropic 与 Google 以 Swift 包形式提供模型，`CoreAILanguageModel` 与 `MLXLanguageModel` 可在 Neural Engine 与 GPU 上运行开源本地模型（A，E11）。这意味着 Apple 的系统服务成了「调度外壳」，底座不再唯一。
- **Windows。**Windows AI APIs 在 Copilot+ PC 上总是跑在 NPU 上，模型预装；Phi Silica 是 Limited Access Feature，需要解锁令牌，在中国不可用（A，E19、E20）。非 Copilot+ 设备上的 GPU 路径在 2026-06 才作为实验通道出现，且不具备提示压缩与投机解码（A，E20）。
- **浏览器。**Chrome 的 Prompt API 在 Chrome 148 开放给网页，模型于各来源首次使用时下载，文档未说明跨来源是否共享（A，E19）；有第三方报道称 Mozilla、Apple、Microsoft、W3C 提出反对，仅属线索（C，待核实）。
- **HarmonyOS。**2025-06 HDC 发布 HarmonyOS 6 beta 与 HMAF 多智能体框架，称向第三方开放（C，E29）；盘古端侧参数规模未公开（本库已有资料标注未核实）。2026 年的现状没有查到，见 §8。
- **其他手机厂商。**ML Kit GenAI 官方设备列表已覆盖 Honor、OnePlus、OPPO、vivo、小米、Samsung、Motorola、Sony、Sharp 等（A，E2）。这说明 Google 的服务正在成为 Android 阵营事实上的共享底座；但三星 Galaxy AI、国内厂商自家端侧模型对第三方的开放 API 未能核实。

**分歧点。**关键分歧是「谁持有模型内存」。AICore 文档强调「不在 RAM 加载多份」，但官方预览页同时写明首次推理约一分钟用于载入内存，`BUSY` 提示可能有另一个大模型在用（A，E5）。可推断服务一次只常驻一个大模型，并以拒绝而不是排队处理竞争。内存记在谁头上没有文档说明（待核实，归 C4a）。

**反方：自带模型。**公开数据没有找到。能找到的是侧面证据：Google 自己在 I/O 2026 里为「高度定制或小众场景」推荐开发者用 LiteRT-LM 自带微调小模型（B，E7）；Apple 同时开放 Core AI 让开发者带自己的 70B 级模型（A，E13）；一篇第三方评论认为 NPU「从未被当作真正的平台暴露」，原因是碎片化与 SDK 被放弃（C，E30）。主流应用中自带运行时的比例、原因构成：未找到公开资料。

**这说明什么。**共享底座成立，但共享的是「通用任务能力」，定制模型这条路被平台自己保留了。INF-1 要覆盖的不只是共享，还有对自带模型的记账与准入。

### Q2 NPU 的编程与调度模型

**编译方式。**四家都落到「AOT 预编译为主、端侧编译为辅」：
- LiteRT：AOT 适合大模型且已知目标 SoC，减少初始化时间与启动内存；端侧 JIT 适合小模型广泛分发但首次运行慢，Gemma 3 270M 端侧编译超过一分钟（B，E8、E10）。
- Apple Core AI：随包分发的是源表示，在用户设备上做特化，产物与设备和 OS 版本绑定并缓存；官方建议避免在交互流程中特化，缓存缺失时应提示用户（A，E13）。AIModelCache 可在同一 app group 内多应用共享（A，E13）。
- NNRt：两条路——构图后编译（可跨硬件但首次加载慢）与直接加载硬件专用离线模型（快但不可移植）；支持编译缓存（A，E22）。
- QAIRT：GenieX 的 QAIRT 运行时只加载 Qualcomm AI Hub 预编译预量化的模型，llama.cpp 运行时可跑任意 GGUF 并可用 NPU、GPU、CPU（A，E24b）。上下文二进制（context binary）的细节本次未抓到官方页面，待核实。

**内存模型。**NNRt 明确支持在 AI 硬件驱动上申请共享内存做零拷贝（A，E22）；LiteRT 通过 `AHardwareBuffer` 与 OpenGL/OpenCL 缓冲实现零拷贝（B，E10）。Apple 的 Core AI 暴露内存布局匹配、预分配输出、有状态模型（如 KV cache）原地更新（A，E13）。dma-buf、VTCM、rpcmem、ION 的细节归 C4a/C4b，本次未深挖。

**多会话、优先级与抢占。**这是最薄的一块：
- NNRt 基础能力里列有优先级与性能模式，但并发是否可行取决于驱动，不支持多线程并发构图，目前仅同步推理（A，E22）。
- AICore 在应用侧只暴露 `BUSY` 与配额错误码；调度策略不公开（A，E2）。
- 没有找到任何一家厂商公开说明 NPU 上下文切换开销或抢占粒度。
- 学术：Agent.xpu 提出 NPU-iGPU 协同与细粒度抢占（L1，E26b）；TZ-LLM 在 TrustZone 下评估了 NPU 时分共享（预印本，仅从检索摘要得知，未读全文，待核实，E31）；多模型调度的综述性工作大多面向 GPU 服务器。判断：移动端多租户 NPU 抢占，学术与产业都处于空白，这正是 INF-3 的差异化空间。

**跨厂商抽象层的成败。**
- NNAPI：Android 8.1 引入，Android 15 弃用。Google 的官方说法是 Transformer 与扩散模型的出现使开发者需要频繁更新的工具链，所以推出 Play services 里的 TensorFlow Lite 与 AICore，并弃用 NNAPI 以澄清路径（A，E4）。一篇第三方评论补充：NNAPI 标准化了接口，没有标准化行为，性能全看厂商驱动（C，E30）；Samsung 撤回了自己的 Neural SDK（C，E30，待核实）。判断：失败原因是抽象放在了更新慢的 HAL 层，而模型栈需要按月更新。
- LiteRT：Google 现在的答案是把抽象放在用户态可更新的运行时，由 Play 分发模型与运行时，缺失 NPU 时回退 GPU/CPU（B，E8）。代价是仍需 per-SoC 产物：Gemma3-1B 在 Qualcomm、MediaTek、Tensor 上是三份不同的文件，大小从 657MB 到 1704MB 不等（A，E9）；LiteRT-LM 文档的 Qualcomm 路径还要求单独推送 QAIRT 运行库（A，E9）。
- Windows ML：EP 模型。IHV 的 EP 以独立 MSIX 经 Windows Update 分发，Windows 自动按硬件下载，应用不需打包（B，E16；A，E15）。官方声称性能与 AI Engine Direct、TensorRT 等专用 SDK 持平（B，E15）。判断：这是目前最干净的「OS 厂商控制分发」样板，而且 PC 上 Microsoft 掌握驱动模型（WDDM/MCDM），手机上 Google 没有同等控制力。
- Linux accel：统一设备节点（`/dev/accel/accel*`，主设备号 261）并放进 DRM 框架，与 GPU 区分开（A，E23）。已有 amdxdna、qaic、rocket、ivpu，Arm Ethos-U 在 2025 年底加入（C，E32）。它解决提交与内存框架（DRM GEM/GPU scheduler），不解决算子与编译器；手机 SoC 的 NPU 驱动是否上游，本次未查到。
- NNRt：与 NNAPI 的设计很像（北向 Native 接口，南向 HDI），文档限制显示其成熟度低于 LiteRT：56 个算子、同步推理、无 CPU 回退（A，E22）。是否为大模型准备了新路径，待核实。

**分歧点。**NPU 的真实收益存在分歧。厂商口径是 NPU 比 GPU 快至多 10 倍（B，E8）；独立预印本则发现某些阶段 CPU 更快、NPU 卸载增加能耗（C，E25、E26）。两篇预印本对 prefill 的结论方向相反（E25 说 CPU 最多快 1.6 倍，E26 说 NPU 在 prefill 最佳），但对「框架实现质量决定一切」是一致的。

**这说明什么。**NPU 栈的控制权在「分发通道」而不在「接口」。OS 厂商要影响 NPU，需要先握住模型与运行时的更新通道；并发与抢占在产业界仍是空白，需要 OS 层自己做准入控制。

### Q3 端侧推理框架格局

**格局。**
- **LiteRT / LiteRT-LM**（Google）：Android 默认路径；NPU 支持 Qualcomm、MediaTek、Tensor，Intel 在 Windows（A，E9）；LiteRT GPU 平均比旧 TFLite GPU delegate 快 1.4 倍（B，E8）。
- **ExecuTorch**（Meta）：2025-10-22 GA，Meta 称已支撑 Facebook、Instagram、Messenger、WhatsApp 等应用（B，E33）；后端含 XNNPACK、Vulkan（升为生产）、Samsung Exynos NPU、NXP、OpenVINO、Arm Ethos-U 等，Qualcomm 与 Core ML 后端的 1.0 状态未能核实（待核实）。
- **Core AI**（Apple）：见 Q2；对第三方的意义是 Core ML 之外增加面向大模型的一等路径，且 Apple 明确 Core ML 保留、主攻传统 ML（A，E13；另有会话记述，C）。
- **GenieX / QAIRT**（Qualcomm）：GenieX 声明支持 Snapdragon X（Windows ARM64）、8 Elite（Android）、Dragonwing QCS9075（Linux）（A，E24b）。
- **llama.cpp、MNN、MLC-LLM、MLX、mllm、PowerInfer**：内存管理方式（mmap、KV 布局、arena）、后端覆盖与模型格式本次没有逐项核实，不写数字（待核实）。

**多框架重复占用有没有解法。**
1. **系统服务化**：AICore、Foundation Models、Windows AI APIs 都是此解；代价是开放度（Q1）。
2. **共享运行时**：Windows ML 的 framework-dependent 部署让所有应用共享同一份运行时并经 Windows Update 演进（A，E15）；Android 的 LiteRT in Play services、PODAI 同理（A，E4；B，E8）。
3. **共享模型缓存**：Windows ML 提供给库和 SDK 作者的「跨应用共享模型」目录（A，E15）；Apple 的 AIModelCache 仅限同一 app group（A，E13）。Android 应用私有存储天然隔离，没有找到跨应用共享同一权重文件 page cache 的官方机制（未找到公开资料）。
4. **框架无关的记账**：没有找到平台在内存记账上区分「共享模型」与「应用私有模型」的公开设计（归 C4a）。

**这说明什么。**Windows 在「共享运行时加共享模型目录」上走得最远，Android 与 Apple 主要靠系统服务；第三方自带模型的重复占用在手机上没有平台级解法。

### Q7 模型生命周期

**下发。**
- AICore：按需下载，`checkStatus()` 有 AVAILABLE、DOWNLOADABLE、DOWNLOADING、UNAVAILABLE 四态与下载事件，需 Wi-Fi，更新机制页面未描述（A，E3、E5）。
- Windows：NPU 模型预装；GPU 路径与 Image Generation 首次调用 `EnsureReadyAsync` 时经 Windows Update 在后台下载数 GB，用户可在「设置 > 系统 > AI 组件」中删除，应用须先 `GetReadyState` 并征得用户同意（A，E19、E20）。
- Chrome：模型独立于浏览器下载，空闲存储低于 10GB 时被移除并在满足条件后重下（A，E19）。
- Apple：适配器约 160MB，不要放进主包，建议用 Background Assets 从服务器下发（A，E14）。
- 差分更新：本次未找到任何一家公开的模型差分更新机制（未找到公开资料）。

**版本升级的破坏与缓解。**
- Apple：适配器只对一个系统模型版本有效；每次系统模型更新都要重训；多个 OS 版本要多份适配器（A，E14）。缓解是工具箱按版本发布和 Evaluations 框架（A，E11），但没有向后兼容。
- Google：Nano 版本间输出不同，要求分别测试（A，E2）；缓解是开发者预览通道与 `getBaseModelName()`。
- Microsoft：Phi Silica 被 Aion Instruct 取代，已提供并行测试注册表键、独立可侧载包、用 Foundry Toolkit 重训 LoRA，并取消 LAF 令牌门槛（A，E21）。时间线明确：2026-11 进 Insider，2027-01 零售设备移除 Phi Silica。
- 判断：三家的缓解手段都是「给开发者时间与工具」，没有一家做到适配器跨底座版本自动迁移。INF-2 的「热插拔」必须同时设计适配器与底座的版本绑定与回退策略。

**能耗与热。**
- Android 有 `getThermalHeadroom` 与热状态回调，能预测未来若干秒余量，设备间不一致，部分机型返回 `THERMAL_STATUS_NONE` 或 NaN（A，E27）。这些 API 面向通用工作负载；是否被 AICore 用来做调度，未找到公开资料。
- Apple 与 Windows 是否向应用暴露推理期间的热状态或每 token 能耗：未找到公开资料。
- 学术：2026-07 测量研究提出 PowerBench 按后端归因能耗，并发现仅调 CPU 频率可省电至多 39.7%，能耗导向配置使 NPU 后端能耗至多降 53.2%（C，E26）；NPU 并不天然省电（E25）。
- AICore 对长窗口配额命名为 `PER_APP_BATTERY_USE_QUOTA_EXCEEDED`，表明 Google 以电量为配额单位（A，E2）；具体数值未公开。

**这说明什么。**生命周期问题已经成为平台和开发者之间的合同问题：谁为底座升级造成的适配器失效买单。目前答案是开发者。

---

## §4 趋势判断

**正在收敛的方向**
- 三大平台都提供系统级共享模型，并用任务级 API 加会话级 API 两层暴露（AICore 的 Summarization 等与 Prompt API；Apple 的 guided generation 与会话；Windows 的 Text Intelligence Skills 与 LanguageModel）。
- 系统托管提示前缀状态：AICore 的 Prefix Caching（E6）、Apple 的 cached token 计数（E11）。
- 预编译加设备特化加缓存成为 NPU 部署主路径（E8、E10、E13、E22）。
- 云端回退内置于系统服务：Firebase AI Logic hybrid（PREFER_ON_DEVICE 等，规则式路由）（E24c）、Apple PCC 作为框架内一等模型（E11）。路由本身归 C1b。
- 系统服务向「托管 Agent 循环」扩展：AICore Agentic API alpha（E7b）、Apple Dynamic Profiles 与 skill API（E11）。

**公认的空白点**
- NPU 的多租户抢占与优先级：产业无公开机制，学术仅 L1。
- 适配器跨底座版本的兼容与迁移。
- 每 token 能耗和热状态的遥测与向应用暴露。
- 模型差分更新。
- 跨应用共享同一份权重文件的平台级机制（Android、iOS 侧）。
- 第三方自带模型的采用率与原因的公开数据。

**仍有分歧的问题**
- NPU 是否值得：厂商口径与独立测量在 prefill 与能耗上不一致（E8 与 E25、E26）。
- 系统服务该不该开放第三方模型：Apple 选择可插拔；Google 保留 LiteRT-LM 作为旁路；Microsoft 把 Phi Silica 做成 LAF 受限。
- 跨厂商抽象放在哪一层：内核（accel）、HAL（NNAPI/NNRt）、用户态运行时（LiteRT、Windows ML EP）。目前用户态运行时加 OS 厂商分发胜出，但 PC 与手机的控制力不同。
- 设备覆盖：nano-v4 目前只覆盖少数旗舰（E2），共享底座在中低端机上是否成立未知。

---

## §5 立场评审表

| 立场 ID | 判断（支持 / 挑战 / 需修订） | 关键证据 | 最强反方证据 | 修订建议 | 置信度（高 / 中 / 低） |
|---|---|---|---|---|---|
| INF-1 底座模型作为系统服务共享 | 支持，需修订 | 三大平台均已量产：Gemini Nano 超 1.4 亿设备（E7）；AICore 应用共享一份基础模型（E2）；Phi Silica NPU 预装（E19）。 | Apple 在 iOS 27 把系统模型变成可插拔协议之一，并开放 Core AI 自带模型（E11、E13）；Google 推荐 LiteRT-LM 自带微调模型（E7）；Phi Silica 被替换说明「底座」本身会更换（E21）。「编解码器类比」的缺口：编解码器接口稳定，而 LLM 输出随版本变。 | 把 INF-1 改写为「共享底座 + 稳定的任务级接口 + 受控的自带模型旁路」。底座版本需要进入接口契约（类似 `getBaseModelName`），不能假设行为稳定。自带模型需要纳入同一套记账和准入，否则会绕过共享。 | 高 |
| INF-2（系统服务与框架支持部分）多应用共享底座，LoRA 热插拔 | 需修订 | Apple 有产品化适配器（约 160MB，版本绑定，需 entitlement）（E14）；Windows 有 LoRA 微调工作流并在换模型时要求重训（E21）。 | Google 的产品选择是 Prefix Caching 与 Structured Output（E6、E7），未发现 Gemini Nano 对第三方开放适配器；Apple 适配器不能热插拔到别的底座版本，使「共享底座」与「多适配器」存在版本耦合。 | 在 INF-2 中增加「适配器与底座版本绑定表、回退策略、体积配额」。评估用「前缀缓存加结构化输出」替代部分 LoRA 场景，成本更低、不受版本绑定。 | 中 |
| INF-3 推理调度需要多租户 QoS | 支持，需修订 | 产业缺口真实：并发语义未公开，NNRt 并发依赖驱动（E22）；学术 Agent.xpu 证明抢占对 reactive 延迟有大幅收益（E26b）。 | 产业用「前台限制加配额加 BUSY」的粗粒度准入控制已足够当前场景（E2）；E25 提示 NPU 调度开销与回退可能抵消卸载收益，细粒度调度的收益不确定。 | 把 INF-3 拆成两层：先做准入控制与前台优先（可落地），再做异构后端上的抢占（研究）。QoS 度量应跨 CPU/GPU/NPU，而不是只管 NPU。 | 中 |
| INF-5（框架与服务支持部分）模型权重与 KV cache 需要可分页 | 挑战 | 未发现任何系统服务支持分页：AICore 首次推理要把模型载入内存约一分钟（E5）；Apple Core AI 有状态模型原地更新 KV（E13）但未描述分页；Prefix Cache 落盘是唯一 KV 持久化先例，且在应用私有存储中（E6）。 | 没有反方证据反对「需要」，只有「现状没有」；分页的必要性证据在 C4b。 | 对 INF-5 标注「框架侧没有现成接口」，意味着需要自己定义服务级接口；可借 Prefix Caching 的显式缓存 API（create/list/get/delete）作为接口样板。 | 中 |

---

## §6 接缝发现

仅记录本组件协同的接缝；C1a 无主责接缝。

- **J2（协同）**：AICore 声称不在 RAM 多份加载，但文档没有说明内存记在哪个进程或应用头上（A，E2）。AICore 的隐式前缀缓存存放在应用私有存储，意味着缓存归属于应用而不是系统（A，E6）；这是「前缀共享」在 Android 上的现状：不跨应用共享，侧信道问题因此被回避，同时也放弃了跨应用共享系统提示词的收益。Windows ML 的「共享模型目录」则允许跨应用共享（A，E15），侧信道未讨论。
- **J3（协同）**：AICore 有 Structured Output 与 Agentic API 的路线（B，E7、E7b）；Apple 有 guided generation 与 tool calling（A，E11）。说明结构化输出和工具调用正在由推理服务提供，沙箱侧（C2b）需要接收这些调用的执行与权限。
- **J6（协同）**：适配器的版本绑定（E14、E21）直接限制热插拔：切换适配器不只是一次加载，还要匹配底座版本。
- **J8（协同）**：Firebase AI Logic hybrid 的路由当前是规则式，只有 `PREFER_ON_DEVICE` 一类模式，由应用选择（B，E24c）；没有看到使用数据敏感度标签。

---

## §7 组件特有输出

### 7.1 端侧推理栈分层图

开放度：开源 / 开放 API / 受限开放 / 封闭。控制方：OS 厂商、芯片厂商、Google 或 Apple、应用开发者、开源社区。

```
┌──────────────────────────────────────────────────────────────────────────┐
│ L7 应用 / Agent                                                           │
│    玩家：第三方应用、系统助手（Gemini、Siri、小艺）                        │
│    开放度：—；控制方：应用开发者（系统助手由 OS 厂商控制）                 │
├──────────────────────────────────────────────────────────────────────────┤
│ L6 应用 API                                                               │
│    Android：ML Kit GenAI（Prompt、Summarization 等，beta）、AppFunctions   │
│    Apple：Foundation Models framework（核心将开源）                        │
│    Windows：Windows AI APIs；HarmonyOS：意图框架 / HMAF                    │
│    开放度：开放 API（Phi Silica 为 LAF 受限；HarmonyOS 开放范围待核实）    │
│    控制方：Google / Apple / Microsoft / 华为                               │
├──────────────────────────────────────────────────────────────────────────┤
│ L5 系统服务                                                               │
│    AICore、Apple 系统模型守护进程（内部名未核实）、Windows AI Foundry、    │
│    小艺系统服务                                                            │
│    职责：持有模型、配额、前台限制、版本通道、隐私隔离                      │
│    开放度：封闭（行为仅通过 API 与错误码可见）；控制方：OS 厂商           │
├──────────────────────────────────────────────────────────────────────────┤
│ L4 运行时 / 框架（可被应用自带）                                          │
│    LiteRT / LiteRT-LM、Core AI（及保留的 Core ML）、Windows ML(ONNX RT)、  │
│    ExecuTorch、MindSpore Lite、llama.cpp、MNN、MLC-LLM、MLX                │
│    开放度：开源为主（Core AI 框架闭源，转换工具为开放 Python 包）          │
│    控制方：Google / Apple / Microsoft / 开源社区                           │
├──────────────────────────────────────────────────────────────────────────┤
│ L3 芯片厂商 SDK / 编译器 / 加速器插件                                     │
│    QAIRT / GenieX、MediaTek NeuroPilot、Google Tensor 运行库、             │
│    华为 CANN / HiAI Foundation、Windows ML 的各 IHV EP                     │
│    职责：图编译、context binary、算子实现                                  │
│    开放度：受限开放（SDK 可下载，编译器与内核实现闭源）                    │
│    控制方：芯片厂商                                                        │
├──────────────────────────────────────────────────────────────────────────┤
│ L2 驱动 / HAL / 抽象层                                                    │
│    NNAPI（已弃用）、NNRt 的 HDI、Linux accel（DRM_ACCEL）、               │
│    Windows MCDM / WDDM 驱动                                                │
│    开放度：接口开放，手机 NPU 驱动实现多为封闭；                           │
│    控制方：芯片厂商与 OS 厂商共管，Linux accel 为开源社区                  │
├──────────────────────────────────────────────────────────────────────────┤
│ L1 芯片                                                                   │
│    Hexagon（Qualcomm）、APU（MediaTek）、ANE（Apple）、TPU（Tensor）、     │
│    昇腾 / 达芬奇（华为）、Exynos NPU                                       │
│    开放度：封闭；控制方：芯片厂商                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**读图结论（判断）**：OS 厂商能直接改的只有 L5–L6 与部分 L2；L3 和 L1 由芯片厂商控制；L4 对 Google/Apple/Microsoft 是产品，对其他 OS 厂商是可选依赖。AgentOS 如果不是 Google/Apple，真正的杠杆点是 L5 的准入与记账，以及 L4 的分发通道。NNAPI 被弃用说明把杠杆放在 L2 不可持续。

### 7.2 多框架重复占用估算

**公开数据**：未找到。以下为估算，全部标「估算」，输入数字取自 E9、E14。

**方法**：重复占用 = 同时驻留的独立模型实例数 × 单实例权重常驻量 + 各实例的运行时库与 KV。
- 权重常驻量取量化后文件大小的下界（假设整份映射进内存，实际取决于是否 mmap、是否需要拷贝入 NPU 可见缓冲，后者未核实）。
- 单实例选三档：1B 级 4-bit，约 0.66–1.0GB（Gemma3-1B 在 Qualcomm、MediaTek 上的文件大小，E9）；2B 级 4-bit，约 2.6GB（Gemma4-E2B on Tensor G6，E9）；适配器约 0.16GB（E14）。
- 运行时库和 KV 本次没有可靠数据，不计入，故结果为下界。

| 场景（估算） | 计算 | 常驻量 | 占 12GB 手机比例 |
|---|---|---|---|
| 系统服务共享 1 份 2B 模型，3 个应用调用 | 1 × 2.6GB | 约 2.6GB | 约 22% |
| 3 个应用各自带一份 1B 模型（不同 SoC 产物，同时驻留） | 3 × 0.66–1.0GB | 约 2.0–3.0GB | 约 17–25% |
| 2 个应用各自带 2B 模型加系统服务同时有 2B 模型 | 3 × 2.6GB | 约 7.8GB | 约 65% |
| 系统服务 2B 加 3 个应用各 1 个适配器（Apple 模式） | 2.6GB + 3 × 0.16GB | 约 3.1GB | 约 26% |

**解读（判断）**：第三、四行之间的 4.7GB 差距就是「共享底座」的内存价值，即每多一个自带 2B 模型的应用，多占约 2.6GB。该估算有三个不确定项：(1) 驻留是否全量，取决于 mmap 与分页（C4b）；(2) NPU 路径是否要求额外的拷贝缓冲（待核实）；(3) 手机在后台能否真的同时保持多个模型（LMKD 通常会先杀掉，见 C4a）。因此实际表现更可能是「冷启动加载延迟与被杀」而不是「同时驻留」，重复成本换成了时间成本：AICore 首次推理加载约 1 分钟（E5）。

---

## §8 参考资料与待核实清单

### 参考资料

| 编号 | 标题 | 机构 / 作者 | URL | 日期 |
|---|---|---|---|---|
| E1 | 同 E7（Gemini Nano 装机量，见下） | Google | 同 E7 | 2026-04-02 |
| E2 | Overview of the ML Kit GenAI APIs | Google | https://developers.google.com/ml-kit/genai | 2026-11 抓取（页面无日期） |
| E3 | ML Kit GenAI Prompt API get started | Google | https://developers.google.com/ml-kit/genai/prompt/android/get-started | 2026-11 抓取 |
| E4 | NNAPI Migration Guide | Google | https://developer.android.com/ndk/guides/neuralnetworks/migration-guide | 2026-11 抓取 |
| E5 | AICore Developer Preview | Google | https://developers.google.com/ml-kit/genai/aicore-dev-preview | 2026-11 抓取 |
| E6 | Prompt API Prefix Caching | Google | https://developers.google.com/ml-kit/genai/prompt/android/prefix-caching | 2026-11 抓取 |
| E7 | Gemma 4: the new standard for local agentic intelligence（含 Nano 4 基础模型与 1.4 亿设备口径） | Android Developers Blog | https://android-developers.googleblog.com/2026/04/gemma-4-new-standard-for-local-agentic-intelligence.html | 2026-04-02 |
| E7a | Top AI on Android updates from Google I/O 26 | Android Developers Blog | https://developer.android.com/blog/posts/top-ai-on-android-updates-for-building-intelligent-experiences-from-google-i-o-26 | 2026-05-26 |
| E7b | Agentic and Flexible: A next era of Android development | Android Developers Blog | https://developer.android.com/blog/posts/build-it-your-way-a-next-era-of-android-development | 2026-10-28 |
| E8 | LiteRT: The Universal Framework for On-Device AI | Google Developers Blog | https://developers.googleblog.com/litert-the-universal-framework-for-on-device-ai/ | 2026-01-28 |
| E9 | Run LLMs using LiteRT-LM（NPU 支持表） | Google | https://developers.google.com/edge/litert/next/litert_lm_npu | 2026-11 抓取 |
| E10 | MediaTek NPU and LiteRT: Powering the next generation of on-device AI | Google Developers Blog | https://developers.googleblog.com/mediatek-npu-and-litert-powering-the-next-generation-of-on-device-ai/ | 2025-12-08 |
| E11 | What's new in the Foundation Models framework（WWDC26 session 241） | Apple | https://developer.apple.com/videos/play/wwdc2026/241 | 2026-06 |
| E12 | Apple Outlines Major AI and Developer Tool Updates at 2026 Platforms State of the Union | MacRumors | https://www.macrumors.com/2026/06/09/apple-outlines-major-ai-and-developer-tool-updates/ | 2026-06-09 |
| E13 | Meet Core AI（WWDC26 session 324） | Apple | https://developer.apple.com/videos/play/wwdc2026/324/ | 2026-06 |
| E14 | Foundation Models framework adapter toolkit | Apple | https://developer.apple.com/apple-intelligence/foundation-models-adapter/ | 2026-11 抓取 |
| E15 | What is Windows ML? | Microsoft Learn | https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/overview | 2026-09-08 更新 |
| E16 | Windows ML execution providers | Microsoft Learn | https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers | 2026-10-07 更新 |
| E17 | Windows ML is generally available | Windows Developer Blog | https://blogs.windows.com/windowsdeveloper/2025/09/23/windows-ml-is-generally-available | 2025-09-23 |
| E19 | What are Windows AI APIs? | Microsoft Learn | https://learn.microsoft.com/en-us/windows/ai/apis/ | 2026-10-08 |
| E19b | Chrome Prompt API 文档 | Google Chrome | https://developer.chrome.com/docs/ai/prompt-api | 2026-05 前后更新（页面无日期） |
| E20 | Get started with Phi Silica | Microsoft Learn | https://learn.microsoft.com/en-us/windows/ai/apis/phi-silica | 2026-10-19 更新 |
| E21 | 同 E20（Aion Instruct 过渡时间线） | Microsoft Learn | 同 E20 | 2026-10-19 更新 |
| E22 | Neural Network Runtime Kit 简介 | OpenHarmony 文档 | https://gitcode.com/openharmony/docs/blob/OpenHarmony_feature_20250328/zh-cn/application-dev/ai/nnrt/Neural-Network-Runtime-Kit-Introduction.md | 2025-03 分支 |
| E23 | Compute Accelerators introduction | Linux 内核文档 | https://docs.kernel.org/accel/introduction.html | 页面无日期 |
| E24 | Running LLMs on device with Qualcomm Snapdragon 8 Elite | Grape Up | https://grapeup.com/blog/running-llms-on-device-with-qualcomm-snapdragon-8-elite | 2026-03 |
| E24b | GenieX FAQ | Qualcomm AI Hub | https://geniex.aihub.qualcomm.com/en/resources/faq | 2026-11 抓取 |
| E24c | Hybrid inference and new AI models are coming to Android | Android Developers Blog | https://android-developers.googleblog.com/2026/04/Hybrid-inference-and-new-AI-models-are-coming-to-Android.html | 2026-04-17 |
| E25 | When NPUs Are Not Always Faster: A Stage-Level Analysis of Mobile LLM Inference（Pu Li 等） | arXiv 2605.27435 | https://arxiv.org/abs/2605.27435 | 2026-05-22 |
| E26 | Is Your NPU Ready for LLMs? Dissecting the Hidden Efficiency Bottlenecks in Mobile LLM Inference（Guanyu Cai 等，SIGMETRICS 2027） | arXiv 2607.05475 | https://arxiv.org/abs/2607.05475 | 2026-07-06；v2 2026-10-16 |
| E26b | Agent.xpu: Efficient Scheduling of Agentic LLM Workloads on Heterogeneous SoC（Xinming Wei 等） | arXiv 2506.24045 | https://arxiv.org/abs/2506.24045 | 2025-06-30；v2 2026-01-06 |
| E27 | ADPF Thermal API | Android Developers | https://developer.android.com/games/optimize/adpf/thermal | 页面无日期 |
| E28 | Fast On-device LLM Inference with NPUs（llm.npu，Daliang Xu 等） | arXiv 2407.05858 | https://arxiv.org/abs/2407.05858 | 2024-07；v2 2024-12 |
| E28b | Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference（Le Chen 等） | arXiv 2501.14794 | https://arxiv.org/abs/2501.14794 | 2025-01-11；v2 2025-10-04 |
| E29 | Huawei unveils HarmonyOS 6 beta at HDC 2025 | TechNode | https://technode.com/2025/06/23/huawei-unveils-harmonyos-6-beta-at-hdc-2025-mate-80-series-likely-to-feature-it-in-q4 | 2025-06-23 |
| E30 | It's been 8 years of phone AI chips and they're still wasting their potential（无署名） | ccstartup.com | https://ccstartup.com/blog/2026/01/18/its-been-8-years-of-phone-ai-chips-and-theyre-still-wasting-their-potential | 2026-01-18 |
| E31 | TZ-LLM: Protecting On-Device Large Language Models with Arm TrustZone | arXiv 2511.13717 | https://arxiv.org/pdf/2511.13717 | 2025-11（仅见检索摘要，未读全文） |
| E32 | More Kernel Graphics Driver & Accelerator/NPU Driver Updates Ready For Linux 6.19 | Phoronix | https://www.phoronix.com/news/Linux-6.19-DRM-Misc-Next-2 | 2025–2026（仅见检索摘要，未抓取正文） |
| E33 | Introducing ExecuTorch 1.0 | PyTorch 博客 | https://pytorch.org/blog/introducing-executorch-1-0/ | 2025-10（日期取自 Arm 公告，仅见检索摘要） |

编号说明：E1 与 E7 为同一来源；E18 未使用；E21 与 E20 同页。正文中引用 E7 的「1.4 亿设备」「快 4 倍、省电 60%」均出自 E7（Gemma 4 博客），而 Nano 4 将于年内上旗舰机、Structured Output 与 Prefix Caching 出自 E7a。

### 待核实清单

1. 国内手机厂商（荣耀、OPPO、vivo、小米）与三星 Galaxy AI 的端侧模型对第三方的开放 API 与配额：未查到。ML Kit 设备列表显示这些厂商的设备已被 Gemini Nano 覆盖（E2），但自家模型的开放度未知。
2. HarmonyOS 2026 年现状：HiAI Foundation、MindSpore Lite、盘古端侧模型对第三方的开放程度，仅有 2025-06 beta 阶段信息（E29）。NNRt 文档为 2025-03 分支，是否有大模型新路径未知。
3. 自带模型或运行时的应用占比、原因构成：未找到公开数据。
4. QAIRT context binary 的内存与多会话行为、Hexagon VTCM 的使用与并发：本次未抓到官方页面。
5. Genie 实测 tok/s 只有第三方来源（E24），不可作为正式数据。
6. Core AI 与 Core ML 的关系：官方会话称 Core ML 保留并主攻传统 ML（会话摘要来自检索与抓取，两处有出入），迁移细节待查 Apple 文档。
7. Foundation Models 的适配器在 iOS 27 是否有新机制：WWDC26 session 241 页面不涉及适配器；适配器页面称工具箱 26.0.0 是最后一版且与 27 不兼容（E14），27 的新路径待核实。
8. AICore 的内存记账归属、并发语义、模型更新机制：官方页面均未说明。
9. Chrome 内置模型跨来源是否共享：官方页面未说明（E19b）。
10. 各开源框架（llama.cpp、MNN、MLC-LLM、MLX、mllm、PowerInfer）的内存管理与后端覆盖：本次未核实，不写数字。
11. HeteroInfer、llm.npu、Agent.xpu 的正式发表会议与年份：arXiv 页面均未列出，需到会议论文集核对。
12. TZ-LLM 的 NPU 时分共享评估内容：仅见检索摘要，需读全文。
13. Samsung 撤回 Neural SDK 一说仅来自 E30，属第三方评论。
14. Chrome Prompt API 遭 Mozilla、Apple、Microsoft、W3C 反对的说法仅见第三方报道（C，未单独抓取）。
15. 能耗：未找到任何平台向应用暴露每 token 能耗的 API；J/token 手机实测数据归 C1b，本次未收集。

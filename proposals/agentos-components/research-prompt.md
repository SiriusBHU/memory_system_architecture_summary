# AgentOS 组件调研 Prompt 集（v2）

**用途**：调研 AgentOS 四个核心组件在产业界与学术界的最新进展，为设计文档《AgentOS 沙箱系统设计》《AgentOS 内存管理设计》提供外部参照与修订输入，并为立项差异化论据提供证据。
**版本**：v2，2026-11-05（在用户 v1 稿基础上修订，修订点见第 0 节）。
**使用方式**（三种模式，规则相同）：

- **单组件模式**：把「第 3 节 通用调研要求」全文拼接到某个组件 Prompt（第 4–7 节）之前，交给一个深度研究类工具或模型。
- **子模块模式**（给子 Agent 用）：在开头加一句「你负责子模块 Cxx，产出写入 <路径>」，只回答第 8 节分工表里该子模块对应的问题；第 3 节规则照样适用。
- **全量模式**：整份交给一个模型，按第 4–7 节逐个组件产出四份报告，再按第 9 节整合。

---

## 0. v2 修订说明：相对 v1 改了什么、为什么

| # | 修订点 | v1 的问题 | v2 的做法 |
|---|---|---|---|
| 1 | **立场编号** | 「对我们的启发」要求逐条判断，但背景里的立场是一段话，四份报告回收后无法逐条对齐、合并 | 每个组件的立场拆成编号条目（INF-、SBX-、MEM-、MM-），评审表按编号逐条给结论 |
| 2 | **跨组件接缝** | 四个组件分开调研，组件之间的接口（KV 有损驱逐入库、共享底座的记账归属、记忆投毒等）没人负责，而 OS 级设计的价值恰恰在接缝 | 新增第 2 节「跨组件接缝 J1–J8」，每条指定主责组件，报告里单列「接缝发现」 |
| 3 | **辅助子系统落点** | v1 说辅助子系统的进展「会自然落在」四个组件里，实际上没有问题去问它，就不会有人去查 | 新增第 1.2 节，把事件总线、命名与发现、记账可观测、身份、能耗、监督界面、版本兼容逐一挂到具体问题上 |
| 4 | **端侧可迁移性** | 沙箱厂商、vLLM/LMCache 等大多是云侧方案，直接拿来评审端侧设计会失真 | 每条云侧技术必须判断能否迁移到手机（内存、功耗、虚拟化支持、NPU 驱动封闭），并写出迁移代价 |
| 5 | **成熟度与证据等级** | 「代表工作」混在一起，看不出是论文、原型还是量产 | 每条技术标成熟度 L1–L4，每个数据标证据等级 A–D |
| 6 | **反方证据** | 只要求「支持 / 挑战 / 需修订」，调研者容易只找支持性证据 | 每个立场必须主动检索最强反方证据；找不到要写明检索范围 |
| 7 | **逐问题正文** | v1 的输出只有表格、数据、趋势、启发四块，没有逐问题的分析正文，深度不够 | 输出格式增加「逐问题分析」节，表格只做索引 |
| 8 | **补漏的调研对象** | 几个关键先例不在清单里 | 补入：Windows（Agent Workspace、Windows ML、Recall）、Android Private Compute Core 与 Pixel Magic Cue、三星 Personal Data Engine、NNAPI 弃用复盘、Linux accel 子系统与 dmem cgroup、信息流控制类 Agent 防护（FIDES、Progent 等）、Meta「Agents Rule of Two」、MCP 工具注解、KV 前缀共享的侧信道、KV 作为记忆（Cartridges 等）、混合注意力架构对 KV 优先级的冲击、GoEX 的 undo 设计等 |
| 9 | **用真实事件检验设计** | 事件复盘只要求「复盘」，没有和我方设计挂钩 | 每个公开事件都要回答：我方哪条立场或机制能挡住，挡不住的缺口是什么 |
| 10 | **新增问题** | 若干决定设计成败的问题缺失 | 推理：模型生命周期与版本兼容、推理服务对 Agent 的接口（结构化输出、工具调用）；沙箱：隔离的内存代价、监督界面；记忆：记忆投毒、索引常驻成本、记忆形态选型；内存：驱逐去向成本模型是否完备、记账可见性缺口 |
| 11 | **控制权视角** | 没有区分哪一层是 OS 厂商能改的、哪一层受芯片厂商或 Google/Apple 控制 | 推理栈分层图和记账缺口表都要标出「谁控制」，直接服务于「我们能改什么」的判断 |
| 12 | **统一输出模板** | 四份报告格式各异，第 7 节的合并难做 | 第 3.6 节给出统一模板，表头固定，便于合并成《AgentOS 外部参照全景》 |

---

## 1. AgentOS 四组件速览

### 1.1 四组件

| 组件 | 经典 OS 对应 | 职责一句话 | 立场前缀 |
|---|---|---|---|
| 推理框架与推理能力 | 计算抽象与调度器 | 系统级模型服务：NPU HAL、模型分发与调度、量化/LoRA、端云路由 | INF- |
| 沙箱框架与执行能力 | 进程模型与保护环 | Agent 对外动作的唯一通道：隔离边界 + 统一接口面 + 权限管理 | SBX- |
| 记忆框架与记忆能力 | 文件系统 | 语义记忆的存储、索引、授权与共享（记忆策略归 Agent） | MEM- |
| 内存管理 | 虚拟内存 | 统一记账底座 + 双策略域：传统内存冷热供给 / 模型内存（KV、MoE 专家、权重） | MM- |

**组件边界**（避免重复调研）：KV cache、权重、MoE 专家的**内存机制**归内存管理；推理框架只看「框架和服务是否支持、接口长什么样」。NPU 的**编程与调度模型**归推理；NPU 的**内存抽象与隔离**归内存管理。记忆投毒的**攻击面与写入授权**归记忆；prompt injection 的**通用攻防**归沙箱。

### 1.2 辅助子系统的落点（v1 未覆盖，v2 指定到具体问题）

| 辅助子系统 | 落在哪个组件的哪个问题 |
|---|---|
| 事件总线（触发、回调、异步通知） | 沙箱 Q4（接口面的异步与触发）、沙箱 Q3 七要素中的「异步」 |
| 命名与发现 | 沙箱 Q4（MCP registry、AppFunctions 发现、App Intents 元数据、鸿蒙意图框架） |
| 记账可观测 | 内存管理 Q1、Q8；推理 Q7（每 token 能耗与热的遥测） |
| 身份薄层 | 沙箱 Q3（Agent 身份与委托授权的业界走向） |
| 能耗 | 推理 Q4、Q7；内存管理 Q7（各驱逐去向的能耗） |
| 监督界面 | 沙箱 Q8；记忆 Q5（记忆可见、可删、可导出） |
| 版本兼容 | 推理 Q7（底座升级对适配器与提示词的破坏）；记忆 Q4（记忆格式迁移） |

---

## 2. 跨组件接缝（v2 新增）

OS 级设计的价值主要在组件之间。每条接缝指定一个主责组件，主责报告必须在「接缝发现」一节回答；协同组件发现相关证据时也要记录。

| ID | 接缝 | 主责 | 协同 | 要回答的问题 |
|---|---|---|---|---|
| J1 | KV / 上下文有损驱逐 → 摘要入库 | 内存管理 | 记忆 | 有没有系统研究把「驱逐」和「长期记忆写入」做成一条路径？摘要的质量损失与重算成本如何权衡？ |
| J2 | 共享底座的记账归属与前缀共享的隔离 | 内存管理 | 推理、沙箱 | 多应用共享一份底座权重和系统提示词 KV 时，内存记在谁头上？跨租户前缀缓存的时序侧信道有哪些已发表攻击和防护？ |
| J3 | 工具调用 / 结构化输出 ↔ 接口面 | 推理 | 沙箱 | 约束解码、工具调用格式是推理服务提供，还是沙箱提供？指令层级等注入防护放在模型层还是执行层？ |
| J4 | 记忆的写入授权与投毒 | 记忆 | 沙箱 | 记忆作为持久化注入载体的攻击有哪些？读写 ACL 应该从沙箱权限继承什么？ |
| J5 | 隔离的内存代价 | 沙箱 | 内存管理 | 每个会话级隔离单元（进程、Wasm、microVM、pKVM VM）占多少内存、启动多久？快照、分叉、休眠能共享多少页？ |
| J6 | LoRA / 适配器热插拔与权重分页 | 推理 | 内存管理 | 适配器切换的延迟和内存开销是多少？与底座权重分页如何共存？ |
| J7 | 语义索引的常驻成本 | 记忆 | 内存管理、推理 | 嵌入模型常驻、索引体积、后台建索引的能耗分别是多少？ |
| J8 | 端云路由与隐私标签 | 推理 | 沙箱、记忆 | 路由决策是否用到数据敏感度标签？标签从记忆 / 权限系统来，还是由模型临时判断？ |

---

## 3. 通用调研要求（G 节，使用时拼接到每个 Prompt 前）

### 3.1 时间与时效

- 今天是 **2026-11-05**。以 2024-01 至 2026-11 的进展为主；奠基性工作不受时间限制，但要标注年份。
- 你的训练知识可能停在更早。**2025 年下半年之后的进展必须联网检索核实**，凡写「最新」都要给出日期。

### 3.2 来源与证据等级

- 产业界以官方文档、技术博客、发布会、开源代码为准；学术界以 SOSP / OSDI / NSDI / USENIX ATC / EuroSys / ASPLOS / MLSys / MobiSys / MobiCom / USENIX Security / S&P / CCS / NDSS / NeurIPS / ICLR / ICML / ACL 等会议与 arXiv 为准；媒体报道只作线索。
- 每个关键数据标证据等级：
  - **A**：官方文档、同行评议论文、源码、内核邮件列表；
  - **B**：官方博客、发布会、厂商白皮书（即「厂商口径」）；
  - **C**：权威媒体、第三方实测、预印本；
  - **D**：传闻、社区帖子。D 级只能作线索，正文引用必须标「传闻，待核实」。

### 3.3 成熟度分级

每条技术路线或代表工作标成熟度：

- **L1** 论文 / 预印本；
- **L2** 开源原型或演示；
- **L3** 生产可用（开源项目稳定发布，或云服务 GA）；
- **L4** 平台默认或规模量产（系统内置、默认开启、亿级设备）。

### 3.4 端侧可迁移性

对每一条云侧或服务器侧技术，回答它能否迁移到手机，并写出理由。手机的约束包括：

- 内存 8–16GB，且与应用共享；
- 功耗与散热约束，持续负载会降频；
- 虚拟化支持有限（pKVM 只在部分机型可用）；
- NPU 驱动与编译器多为闭源；
- 存储是 UFS，有写入寿命约束。

结论写成「可直接迁移 / 需改造（说明改什么）/ 不可迁移（说明替代原语）」。

### 3.5 反方证据与控制权

- **反方证据**：对背景里的每一条立场，主动检索最强的反方证据，例如业界选择了相反路线的案例、失败复盘、性能反例。找不到就写「未找到反方证据」，并写明检索了哪些来源。
- **控制权**：涉及系统分层时，标出每层由谁控制——OS 厂商、芯片厂商、Google / Apple、应用开发者，或开源社区。

### 3.6 输出格式（统一模板，表头固定）

报告按以下顺序组织：

- **§0 摘要**：不超过 10 条，每条一句结论加一个证据编号。
- **§1 技术谱系表**：按技术路线分类。表头固定为：`路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性`。
- **§2 关键数据**：表头固定为：`指标 | 数值 | 条件（硬件 / 模型 / 负载） | 来源 | 日期 | 证据等级`。
- **§3 逐问题分析**：按本组件的核心问题 Q1、Q2……逐个写。每个问题写现状、机制、数据、分歧点，末尾用一句话说「这说明什么」。
- **§4 趋势判断**：分三块写——正在收敛的方向、公认的空白点、仍有分歧的问题。
- **§5 立场评审表**：表头固定为：`立场 ID | 判断（支持 / 挑战 / 需修订） | 关键证据 | 最强反方证据 | 修订建议 | 置信度（高 / 中 / 低）`。
- **§6 接缝发现**：只写本组件主责或协同的 J 编号。
- **§7 组件特有输出**：见各组件 Prompt。
- **§8 参考资料与待核实清单**：参考资料写编号、标题、机构或作者、URL、日期；待核实清单单列。

### 3.7 质量与写作规则

- 区分事实与判断：判断句以「判断：」开头。
- 无法证实的内容标「待核实」；查不到的写「未找到公开资料」。**绝不编造产品名、版本号、论文名、数字或链接。**
- 区分各平台术语，不混用：LMKD 与 Jetsam、zram 与 compressed memory、App Intents 与 AppFunctions 与意图框架、Linux 内核与鸿蒙内核。
- 中文撰写，专有名词保留英文原名；中文和数字之间不加空格。
- 宁缺毋滥：每个关键论断都要附来源。

### 3.8 本库已有资料（子 Agent 使用；外部模型可忽略）

本仓库 `D:\projects\memory_system_architecture_summary` 已积累相关调研。动笔前先浏览对应文件，避免重复劳动，把精力放在新进展、新数据和对我方立场的评审上。引用时请引用原始来源，不要引用本库文件。

| 子模块 | 先读 |
|---|---|
| C1a / C1b | `surveys/ai-native-os-agent-CN.md`；`surveys/sources/ai-native-os-agent/` 下的 AICore、ML Kit GenAI、Apple Foundation Models、HarmonyOS 相关文件；`insight/N+1/memory-bandwidth-and-scheduling/memory-bandwidth-and-scheduling-CN.md`；`proposals/2027-agentos-ai-graphics/notes/D2-foundation-evolution.md`、`M4-simulation-eval.md` |
| C2a / C2b | `surveys/ai-native-os-agent-CN.md`；`surveys/sources/ai-native-os-agent/` 下的 AppFunctions、App Intents、Intents Kit 文件；`insight/N+1/arm-memory-safety-cca-mte/arm-memory-safety-cca-mte-CN.md`；`proposals/2027-agentos-ai-graphics/notes/M1-agentos-commercial.md`、`D1-commercial-deep-dive.md` |
| C3a / C3b | `insight/N+1/on-device-agent-memory-system/` 下的 CN 文档与 `openviking-context-database-CN.md`、`prefix-cache-agent-notes.md`；`insight/N+1/edge-cloud-collaborative-memory/edge-cloud-collaborative-memory-CN.md` |
| C4a | `advanced/A16-前沿-Agent时代内存负载.md` 及 A16a–A16e；`platforms/A14-*` 三篇；`insight/N+1/tiered-memory-management/tiered-memory-management-CN.md`；`proposals/2027-agentos-ai-graphics/notes/M2-system-memory.md` |
| C4b | `insight/N+1/on-device-kv-cache-management/on-device-kv-cache-management-CN.md`；`insight/N+1/on-device-model-swapping/on-device-model-swapping-CN.md`；`surveys/on-device-llm-memory-CN.md`；`proposals/2027-agentos-ai-graphics/notes/M3-model-memory.md` |

---

## 4. Prompt 1：推理框架与推理能力

### 背景与立场

我们在设计面向端侧 Agent 的 OS 级推理子系统。架构立场：

- **INF-1** 底座模型作为系统服务共享（模型即系统服务，类似编解码器）。
- **INF-2** 多应用共享底座，LoRA 等适配器热插拔。
- **INF-3** 推理调度需要多租户 QoS。
- **INF-4** 端云之间存在一个按隐私、成本、延迟路由的路由层。
- **INF-5** 模型权重与 KV cache 需要可分页。本 Prompt 只看推理框架和系统服务是否支持，内存机制归 Prompt 4。

### 核心问题

**Q1 系统级端侧模型服务的现状**

- Android AICore / Gemini Nano（ML Kit GenAI API、Prompt API）：进程模型、模型内存由谁持有、配额（按应用、按电量、前台限制）、错误语义、设备覆盖、模型版本与更新通道。
- Apple Foundation Models framework：模型规格、上下文窗口、guided generation 与 tool calling、适配器训练与底座版本的绑定关系、后台限速、与 Private Cloud Compute 的衔接；2026 年新一代模型带来的变化。
- HarmonyOS：盘古端侧模型与小艺、HiAI Foundation、MindSpore Lite、NNRt、意图框架与智能体框架对第三方的开放程度。
- 非手机的平台先例：Windows AI Foundry / Windows ML / Phi Silica、Chrome Built-in AI（Prompt API）。
- 其他手机厂商：三星 Galaxy AI，荣耀、OPPO、vivo、小米的端侧模型开放 API。
- **反方**：主流应用中有多少仍自带模型或运行时（自带 llama.cpp、MNN、MediaPipe 等）？原因是能力不够、配额受限、版本不可控，还是设备覆盖率不足？

**Q2 NPU 的编程与调度模型**

- Qualcomm QNN / QAIRT（HTP）、MediaTek NeuroPilot、Apple ANE（经 Core ML）、华为 CANN / HiAI Foundation：
  - 图编译方式（AOT context binary 还是在线编译）；
  - 内存模型（共享 ION / dma-buf、VTCM 等片上存储）；
  - 多会话并发、优先级与抢占、上下文切换开销。
- 跨厂商 NPU 抽象层的尝试与成败：
  - NNAPI 在 Android 15 弃用的复盘；
  - LiteRT 的 NPU 加速路径（与芯片厂商合作）；
  - Windows ML 执行提供程序、ONNX Runtime EP；
  - Linux 内核 accel 子系统（DRM accel）；
  - OpenHarmony NNRt。
- 学术界的多租户 NPU 调度、虚拟化与抢占研究（服务器与移动端都要）。

**Q3 端侧推理框架格局**

- llama.cpp、ExecuTorch、LiteRT / LiteRT-LM、MediaPipe LLM Inference、MNN、MLC-LLM、MLX、Core ML、mllm / llm.npu、PowerInfer：内存管理方式（mmap、KV 布局、arena）、硬件后端覆盖（CPU / GPU / NPU）、模型格式。
- 多框架并存造成的重复占用（权重、运行时库、KV）有没有解法：系统服务化、经 Google Play services 分发的共享运行时、同一权重文件跨进程共享 page cache 等。

**Q4 推理加速在端侧的落地水平**

- 量化：W4A16、W4A8、2-bit QAT、三值量化。
- 投机解码：EAGLE 系列、MTP、draft model、LayerSkip 在 NPU 上是否可行。
- KV 复用：系统提示词跨请求复用、前缀缓存。
- prefill 放到 NPU 上执行。
- 给出手机实测的 tokens/s、TTFT、J/token。

**Q5 端云路由**

- 方案：Apple PCC、Google Private AI Compute（线索，待核实）、Meta Private Processing、Firebase AI Logic hybrid、Chrome、三星、NVIDIA OpenShell Privacy Router。
- 每个方案回答：
  - 路由依据（隐私标签、能力、成本、延迟、电量、网络）；
  - 谁做决策（OS、应用，还是模型自评）；
  - 隐私保证机制（TEE、可验证的透明日志、无状态、匿名中继）；
  - 延迟数据。
- 学术界：RouteLLM、Hybrid LLM、FrugalGPT、级联与投机式端云协同。

**Q6 LoRA 与适配器生态**

- 先例：Apple adapters（与底座版本绑定）、Gemini Nano 的特性适配器（线索，待核实）、Qualcomm 在 NPU 上预编译多适配器并切换、服务器侧 S-LoRA / Punica / dLoRA 的多适配器服务、端侧 EdgeLoRA。
- 指标：热插拔延迟、内存开销、底座升级后的兼容性。

**Q7 模型生命周期**（v2 新增，对应辅助子系统中的版本兼容、分发、能耗）

- 模型下发：按需下载、差分更新、存储占用。
- 版本升级对应用行为的破坏：提示词回归、适配器失效，以及平台如何缓解。
- 能耗与热：持续推理的降频曲线、J/token、平台是否向应用暴露能耗或热状态。

**Q8 推理服务对 Agent 的接口**（v2 新增，对应接缝 J3）

- 结构化输出与约束解码、工具调用格式。
- 会话与上下文管理 API：系统是否托管 KV 和会话状态。
- 指令层级、注入防护是否在服务层提供。

### 调研对象

- **产业界**：Google（AICore、Gemini Nano、LiteRT、Private AI Compute）、Apple（Foundation Models framework、Core ML、PCC）、Microsoft（Windows ML、Phi Silica）、Qualcomm、MediaTek、华为（HarmonyOS AI、CANN）、三星、国内手机厂商、Meta（ExecuTorch、Private Processing）、NVIDIA（OpenShell Privacy Router）、各端侧推理框架的开源社区。
- **学术界**：MLSys、ASPLOS、OSDI、SOSP、MobiSys、MobiCom 上 2024–2026 年的端侧推理系统论文（如 llm.npu、PowerInfer-2、HeteroInfer 等，核实会议与年份）；投机解码与量化的代表工作；offloading 谱系（FlexGen、ZeRO 系列）；端云协同推理的系统研究；多租户 NPU 调度研究。

### 组件特有输出

1. **端侧推理栈分层图**（芯片 → 驱动 / HAL → 运行时 / 框架 → 系统服务 → 应用 API → 应用 / Agent）：每层标出玩家、开放程度（开源 / 开放 API / 受限开放 / 封闭）和控制方。
2. **端云路由方案对比表**：路由依据、决策方、隐私机制、延迟数据、证据等级。
3. **多框架重复占用估算**：有公开数据就给数据；没有就写清估算方法并标「估算」。

---

## 5. Prompt 2：沙箱框架与执行能力

### 背景与立场

我们在设计 Agent 会话级沙箱，已有设计文档《AgentOS 沙箱系统设计》。架构立场：

- **SBX-1** 沙箱 = 借来的隔离边界：复用平台已有的隔离机制，不自建隔离技术。
- **SBX-2** 统一接口面：L0 raw 执行兜底，L1 结构化动作。
- **SBX-3** L1 的七要素：schema、效果描述、dry-run、undo、幂等、异步、结构化拒绝。评审时逐项给结论。
- **SBX-4** 参数化权限：权限绑定到参数取值，而不只是动作类型。
- **SBX-5** 三维风险模型定档。如果拿不到设计文档，请对照业界常见的风险维度（可逆性、影响范围、数据敏感度、外部可见性、资金）评审「三个维度是否够用」，并说明你采用的假设。
- **SBX-6** 策略在装配、调用、销毁三个时机执行。
- **SBX-7** 跨链不升级：在多步或多 Agent 的调用链上，权限只减不增。
- **SBX-8** 凭证经纪人：Agent 不持有明文凭证。
- **SBX-9** 身份管理归应用，系统只保留信任根与跨链规则。

### 核心问题

**Q1 Agent 执行沙箱格局（云侧）**

- 厂商：E2B、Daytona、Modal、Cloudflare（Sandbox SDK、Workers 隔离）、Blaxel、Morph、Vercel Sandbox、腾讯云 Cube、NVIDIA OpenShell、AWS Bedrock AgentCore（Runtime、Code Interpreter、Browser）、Azure Container Apps dynamic sessions、Google（GKE Agent Sandbox、kubernetes-sigs/agent-sandbox）、OpenAI（Codex 云端环境、ChatGPT agent）、Anthropic（code execution tool、Claude Code 沙箱）、Docker。
- 每家写清：隔离底座、冷启动时间、生命周期原语（快照、分叉、休眠）、单实例内存开销、计费模型、差异化。

**Q2 策略与授权**

- OPA / Rego 与 Cedar 的取舍；AWS AgentCore Policy 等新产品选了哪个（待核实）。
- 策略变更的形式化验证：Cedar 的验证工作、OpenShell policy prover 及后续工作。
- deny-by-default 出口治理的工程实践：Claude Code 沙箱的网络代理、Codex 默认断网、OpenShell 等。
- 信息流控制与能力系统用于 Agent（这是 SBX-7 的理论基础）：CaMeL、FIDES、Progent、IsolateGPT / SecGPT、Conseca 等。
- 参数化权限的先例：Android 运行时权限的范围化、iOS 有限访问、MCP 工具注解、Claude Code 带参数模式的权限规则。

**Q3 凭证经纪人与身份**

- 实现方式：出口代理注入、占位符替换、响应脱敏，各家怎么做。
- Agent 的委托授权：MCP authorization 规范（OAuth 2.1、resource indicators、禁止 token passthrough）、Microsoft Entra Agent ID、Okta Cross App Access、Windows 为 Agent 分配的本地账户。
- 端侧凭证原语：Android Keystore / StrongBox / Credential Manager、iOS Keychain / Secure Enclave、HarmonyOS 通用密钥库（HUKS）。
- 凭证泄漏事故复盘（经 prompt injection 窃取 token、Nx s1ngularity、MCP server 泄漏等）。
- **对 SBX-9 的检验**：业界是否在把 Agent 身份收进平台层？这对「身份归应用」是支持还是挑战？

**Q4 接口面**

- MCP 生态：工具注册与治理、registry、工具注解（readOnlyHint、destructiveHint、idempotentHint 等，与七要素对照）、2025–2026 年规范版本的新增能力（elicitation、结构化输出、异步任务等，核实版本号）。
- Android AppFunctions（Android 16 及 2026 年进展）、iOS App Intents（iOS 26 及之后）、HarmonyOS 意图框架与智能体框架、Windows 上的 MCP registry 与 App Actions：最新能力边界。
- computer use 类 UI 自动化 API：Anthropic computer use、OpenAI CUA、Gemini Computer Use，以及手机上的 UI 自动化接口。
- 命名与发现、事件触发与异步回调怎么做（辅助子系统落点）。
- 产出时把每个接口方案对照七要素逐项打分。

**Q5 Agent 安全**

- prompt injection 攻防：CaMeL、AgentDojo、InjecAgent、AgentPoison、ASB、WASP、《Design Patterns for Securing LLM Agents》、instruction hierarchy、spotlighting、Meta「Agents Rule of Two」。
- 逃逸基准：v1 提到的 SEB（核实全称与出处）、沙箱绕过类 CVE（Claude Code、Cursor、Codex CLI 等）。
- 2025–2026 公开逃逸 / 越权事件复盘：EchoLeak、Supabase MCP、GitHub MCP、Replit 删库、Amazon Q 扩展、Comet 浏览器、OpenClaw 等（逐一核实）。
- 风险框架：OWASP Agentic Top 10、NIST AI 600-1、Google SAIF。
- **每个事件都要回答**：我方哪条立场或机制能挡住？挡不住的缺口是什么？

**Q6 端侧会话级沙箱**

- Android：AVF / pKVM / Microdroid（内存与启动开销、可用机型）、isolated process、SDK Runtime 的现状、Private Space、UID 沙箱、seccomp / SELinux、MTE。
- iOS：App 沙箱、Extensions、BrowserEngineKit 的进程模型、Memory Integrity Enforcement。
- HarmonyOS：v1 提到的「动态沙箱」（核实名称与机制）、元服务、ArkTS 隔离。
- 桌面先例：Windows Agent Workspace（为 Agent 单独开会话）、macOS Seatbelt（Claude Code、Codex 在用）、Chrome 的 agentic browsing 安全架构。
- 回答：手机平台上做会话级沙箱的能力与空白分别是什么。

**Q7 隔离的代价**（v2 新增，对应接缝 J5）

- 进程沙箱、Wasm、V8 isolate、gVisor、Firecracker、pKVM VM 的单会话内存开销、启动延迟、功耗。
- 快照 / 分叉的写时复制能共享多少内存。
- 在 12–16GB 的手机上，能同时承载几个会话级沙箱（写出估算过程）。

**Q8 监督界面**（v2 新增，对应辅助子系统）

- 确认疲劳的数据（例如沙箱上线后权限确认减少的比例）。
- 自动批准模式、活动日志、接管与 watch mode、undo 的交互设计。

### 调研对象

- **产业界**：上述沙箱厂商；Anthropic、OpenAI、Google、AWS、Microsoft（Windows Agent Workspace、Entra Agent ID）、Kubernetes agent-sandbox 项目；三家移动 OS 厂商。
- **学术界**：能力安全谱系（object-capability、seL4、Capsicum、WASI）；信息流控制；LLM Agent 安全（CaMeL、FIDES、Progent、IsolateGPT 等）；undo / dry-run 先例（GoEX、TxOS、ToolEmu）；隔离技术（Firecracker、gVisor、Wasm 沙箱）；USENIX Security / S&P / CCS / NDSS 上 2024–2026 的 Agent 安全论文。

### 组件特有输出

1. **沙箱能力矩阵**：厂商 × 隔离底座 × 冷启动 × 快照 / 分叉 / 休眠 × 策略引擎 × 凭证方案 × 网络出口 × 计费模型 × 端侧可迁移性。
2. **七要素逐条评审表**：每个要素写业界先例、业界支持度、实现难点、修订建议。
3. **三维定档评审**：对照 Rule of Two、OWASP、MCP 工具注解，判断三个维度是否够用。
4. **事件复盘表**：事件、日期、攻击链、能挡住它的我方立场 ID、缺口。

---

## 6. Prompt 3：记忆框架与记忆能力

### 背景与立场

我们在设计 OS 级记忆框架。架构立场：

- **MEM-1** OS 提供记忆的存储、索引、ACL 与跨 Agent 共享机制，类比文件系统提供 inode。
- **MEM-2** 「记什么、忘什么、何时检索」的策略归 Agent。
- **MEM-3** 记忆框架与内存管理之间存在「有损驱逐」接口：KV 或上下文被驱逐时，摘要入库。
- **MEM-4** 端侧个人上下文（消息、相册、日历等）的统一语义索引 + 细粒度授权，是最大的生态空白。

### 核心问题

**Q1 Agent 记忆系统格局**

- 框架：MemGPT / Letta（memory blocks、sleep-time agent、文件系统）、Mem0（含图记忆）、Zep / Graphiti（时序知识图谱）、LangGraph / LangMem、A-MEM、MemOS、MemoryOS、MIRIX、Cognee、Memory-R1。
- 商业助手：ChatGPT memory、Claude memory 与 memory tool、Gemini personal context。
- 「文件系统即记忆」路线：CLAUDE.md 与 Agent Skills、Manus 的上下文工程、OpenViking。
- 每个系统写清：记忆模型（工作 / 情景 / 语义 / 程序记忆的划分）、存储引擎、检索策略。
- **检验 MEM-2**：写入决策由谁做——Agent 自己、框架里的抽取器，还是系统？

**Q2 记忆评测与失效模式**

- 基准：LongMemEval、LoCoMo、MemoryAgentBench 等的设计与各家得分；注意厂商之间的得分争议，以及「简单的文件式记忆也能拿到高分」一类的反例。
- 失效模式研究：遗忘错误、检索干扰、记忆污染、过时事实冲突、长上下文退化（context rot）。

**Q3 端侧个人数据索引**

- Windows Recall：架构（VBS enclave、Windows Hello、过滤机制）与隐私风波的时间线复盘。
- Apple：语义索引、App Intents 的实体与 Spotlight 集成、个人上下文。
- 三星 Personal Data Engine（含 Knox Vault）。
- Google：Pixel Magic Cue、Pixel Screenshots、Android Private Compute Core 与 Private Compute Services、Gemini 的个人上下文。
- HarmonyOS：ArkData 等数据管理能力、向量与知识库能力（核实名称）。
- 国内厂商的记忆功能：荣耀、OPPO、vivo、小米。
- 对比两条路线：**donation**（应用主动提供实体）与 **capture**（截屏、无障碍抓取）。
- 「Picker 式」细粒度授权的先例：Photo Picker、联系人选择器、iOS 有限联系人访问、Android 部分媒体访问、Share sheet。
- 语义级授权研究：基于情境完整性（contextual integrity）的工作，如 AirGapAgent、PrivacyLens、ConfAIde。

**Q4 记忆压缩与遗忘**

- 上下文摘要（递归式、分层式）、记忆巩固（反思、sleep-time compute）、遗忘策略（衰减、TTL、MemoryBank 一类的遗忘曲线）、编码 Agent 的上下文压缩（compact、context editing）。
- 给出压缩率与准确率损失的量化数据。
- 记忆格式的版本迁移（辅助子系统中的版本兼容）。

**Q5 隐私与合规**

- 端侧记忆索引的隐私保护技术落地情况：TEE（Knox Vault、Secure Enclave、PCC、Private AI Compute、Private Processing）、差分隐私、联邦学习。
- 合规要求：GDPR 删除权落到记忆上怎么做、EU AI Act、中国个人信息保护相关规定。
- 记忆的可见、可删、可导出（监督界面落点）。
- 多 Agent 共享记忆的权限模型先例：Letta 的共享 memory block、LangGraph 的命名空间、Mem0 的 user / agent / run 作用域、多用户共享记忆的学术工作。

**Q6 与推理的耦合**

- KV cache 与长期记忆的边界：
  - KV 作为记忆：Memory³、Cartridges、CacheBlend / LMCache 把 KV 当可复用的产物；
  - 检索式注意力：InfLLM、RetrievalAttention；
  - 参数化记忆：LoRA 作为记忆、Text-to-LoRA、Titans 等测试时记忆。
- 有损驱逐、摘要入库有没有系统研究（MemGPT 的递归摘要之后有哪些工作）。
- **检验 MEM-3**：记忆应该以什么形态存（文本、向量、图、KV、适配器），OS 托管其中哪些？

**Q7 记忆安全**（v2 新增，对应接缝 J4）

- 记忆投毒攻击：AgentPoison、MINJA、PoisonedRAG、ChatGPT 记忆持久化注入、Gemini 延迟工具调用攻击等。
- 防护：来源标注、写入授权、隔离区。
- 这对 ACL 设计意味着什么：只管读不够，还要管写。

**Q8 端侧索引的资源成本**（v2 新增，对应接缝 J7）

- 嵌入模型的体积与常驻内存、每万条记录的索引体积、后台建索引的时间与能耗、更新延迟。
- 端侧存储引擎：sqlite-vec、ObjectBox、Apple 与鸿蒙的向量能力。

### 调研对象

- **产业界**：Letta、Mem0、Zep、LangChain / LangGraph、向量数据库（Qdrant、Milvus、pgvector、sqlite-vec）、Microsoft（Recall）、Apple、Google（Gemini 记忆、Pixel、Private Compute Core）、三星、OpenAI、Anthropic、国内手机厂商。
- **学术界**：MemGPT 及后续工作；RAG 谱系；记忆基准（LongMemEval、LoCoMo、MemoryAgentBench）；认知架构启发的 Agent 记忆（Soar / ACT-R 传统、Generative Agents）；NeurIPS / ICLR / ACL 2024–2026 的 Agent memory 方向；情境完整性与隐私基准；记忆投毒。

### 组件特有输出

1. **记忆系统对比表**：系统 × 记忆类型划分 × 存储引擎 × 写入决策方（Agent / 框架 / 系统） × 遗忘机制 × 共享与 ACL × 隐私方案 × 基准得分。
2. **端侧个人语义索引的空白点清单**，以及与最接近实现（Apple 语义索引、三星 PDE、Recall、Magic Cue、鸿蒙）的差距分析。比较维度：数据覆盖、索引方式、授权粒度、第三方开放、跨应用、TEE。
3. **记忆形态选型表**：文本 / 向量 / 图 / KV / 适配器 × 写入成本 × 读取成本 × 可解释性 × 可删除性 × 是否适合 OS 托管。

---

## 7. Prompt 4：内存管理（传统内存 + 模型内存）

### 背景与立场

我们在设计 AgentOS 内存管理子系统，已有设计文档《AgentOS 内存管理设计》。架构立场：

- **MM-1** 统一记账底座：dma-buf 可见性 + 会话级 memcg + 扩展 PSI。
- **MM-2** 双策略域：传统内存域与模型内存域共享记账，策略分开。
- **MM-3** 传统内存域：在 Agent 与应用叠加的场景下做冷热判别与精准供给；QoS 跟着用户注意力走，而不是跟着进程身份走。
- **MM-4** 模型内存域的 KV：DMA 路径上的 KV cache 驱逐经济学。
- **MM-5** 模型内存域的 MoE 专家管理。
- **MM-6** 模型内存域的权重分页与 LoRA 热插拔。
- **MM-7** 两域之间驱逐路径互通，驱逐有四种去向：换出、重算、上云、摘要入库（KV 摘要可写入记忆框架）。

### 核心问题

**Q1 移动端内存管理现状**

- Android：LMKD（基于 PSI）、MGLRU 的落地情况（哪个 GKI 版本默认）、PSI 的应用、zram / zswap / writeback 策略、mTHP 与匿名大 folio、16KB 页、cached apps freezer、app hibernation。
- iOS：Jetsam 的最新演进（优先级带、内存上限、increased-memory-limit entitlement、footprint 记账、compressor）。
- HarmonyOS：对应机制，如 purgeable memory、内存扩展、应用内存级别回调（核实名称）。
- dma-buf 记账上游工作的状态：
  - dma-buf sysfs 统计的弃用；
  - BPF iterator；
  - memcg 计费补丁；
  - dmem cgroup，以及它在 UMA 手机上是否适用；
  - GPU 内存 tracepoint。
- **记账归属**（接缝 J2）：共享模型服务的内存记在谁头上？AICore 进程、Apple Foundation Models 的守护进程分别怎么做？

**Q2 KV cache 管理的系统化程度**

按五条路线调研，每条都给出端侧证据：

- **块化**：PagedAttention、vAttention（借用 OS 虚拟内存做按需分页）。
- **共享**：RadixAttention、前缀缓存、跨请求系统提示词复用；跨租户共享的侧信道（接缝 J2）。
- **压缩**：KIVI、KVQuant；架构级的 GQA、MLA、跨层 KV 共享（Apple 端侧模型、YOCO、CLA）。
- **驱逐**：H2O、SnapKV、StreamingLLM、PyramidKV、Quest 等。
- **卸载**：CachedAttention、InfiniGen、LMCache、Mooncake、SGLang HiCache、vLLM Sleep Mode；端侧的 KV 落闪存工作（KVSwap、KVNAND 等）。

**反方**：混合 / 线性注意力架构（Qwen3-Next / Qwen3.5、LFM2、Jamba、Mamba 系）正在压缩 KV 体积。这会不会降低 KV 管理的优先级？

**Q3 MoE 内存优化**

- 工作：EdgeMoE、MoE-Infinity、Mixtral-offloading、Pre-gated MoE、HOBBIT、AdapMoE、ProMoE、SwapMoE、fMoE、kTransformers、Fiddler、MoE-Lightning，以及 2026 年的手机侧专家换入工作。
- 指标：效果数据、工程成熟度、router 预测预取的命中率。
- 端侧 MoE 模型的出货状态，用来判断 MM-5 的优先级。

**Q4 权重分页与端侧推理**

- Apple《LLM in a flash》、PowerInfer-2 等「常驻集远小于模型尺寸」路线的后续工作。
- Gemma 3n 的 PLE 缓存（已量产的权重分层先例）。
- 激活稀疏性的现状：SwiGLU 降低了天然稀疏度，TEAL 等方法试图补救。
- 闪存直读权重的实际开销：UFS 4.x 随机读带宽与 IOPS、每 GB 读取能耗、mmap 与 direct IO 的差异。
- LoRA 热插拔的内存机制（接缝 J6，与 Prompt 1 Q6 协同）。

**Q5 QoS 供给**

- 用 cgroup memory.min / low 做「交互 – 后台」双契约的先例：Meta TMO / Senpai / oomd、Google 主动回收、systemd-oomd、Fedora uresourced（为活跃会话设内存保护，线索待核实）、ChromeOS ARCVM balloon。
- Android 是否按应用建 memcg（核实版本）。
- 「用户注意力感知」的内存调度：研究与工业实践——iOS QoS 类、Android top-app、鸿蒙前台感知，以及学术工作（Acclaim、Fleet 等）。
- 有没有人用过「前台」以外的注意力信号，例如亮屏、用户正在等待 Agent 结果？

**Q6 NPU 内存抽象**

- dma-buf heaps、accel 子系统的内存管理、NPU 的 IOMMU / SVA、Qualcomm 共享缓冲区（rpcmem）、MediaTek APU 内存、Apple 统一内存与 ANE。
- 跨厂商标准化的尝试：Windows MCDM 下 NPU 内存的可见性、Linux accel 的收敛。
- NPU 共享内存的隔离研究：NPU TEE（如 sNPU）、NPU 侧信道。

**Q7 四种驱逐去向的成本模型**（v2 新增，评审 MM-7）

- 对换出（zram / 闪存）、重算（重新 prefill）、上云（KV 或会话迁移到云侧）、摘要入库（有损）四种去向，分别写出：
  - 成本构成：DMA 带宽、能耗（J/GB）、恢复延迟、质量损失、隐私；
  - 已发表的数据：CachedAttention、HCache、「compute or load」类工作、CacheGen 的传输压缩、KVNAND / KVSwap 等。
- 四种去向是否完备？例如「降精度原地保留」和「直接丢弃」要不要单列？
- 给出一个决策规则草案。

**Q8 记账可见性缺口**（v2 新增，评审 MM-1）

- 逐类内存回答：在 Android、iOS、HarmonyOS 上，这类内存能否被看见、能否归属到应用或会话、能否回收。
- 内存类型至少包括：匿名页、文件页、dma-buf、GPU 内存、NPU 内存、KV cache、模型权重、zram。

### 调研对象

- **产业界**：Google（Android 内存团队、MGLRU、ChromeOS）、Apple（Jetsam、LLM in a flash 团队）、Meta（TMO、oomd）、vLLM / SGLang / LMCache 社区、Qualcomm、MediaTek、腾讯云 Cube（快照、休眠）、Linux 内核 mm / dma-buf / cgroup 社区。
- **学术界**：SOSP / OSDI / MLSys / ASPLOS / EuroSys / FAST 2024–2026 的 LLM 推理内存管理论文；KV 压缩与驱逐方向；MoE 系统方向；MemGPT（上下文虚存化）；FlexGen / ZeRO 卸载谱系；移动端内存管理（Acclaim、Fleet、Marvin 等）。

### 组件特有输出

1. **KV cache 管理技术谱系表**：块化、共享、压缩、驱逐、卸载五条路线，增加「端侧证据」列。
2. **MoE 专家管理对比表**：预取策略、命中率、内存节省、平台、成熟度。
3. **四种驱逐去向成本模型评审**：表格 + 公式 + 数据。
4. **记账可见性缺口表**：内存类型 × 三平台 × 可见 / 可归属 / 可回收。

---

## 8. 子模块分工（子 Agent 用）

| 子模块 | 负责的问题 | 主责接缝 | 产出路径 |
|---|---|---|---|
| **C1a** 系统模型服务与 NPU 栈 | 推理 Q1、Q2、Q3、Q7 | — | `notes/C1a-model-service-npu.md` |
| **C1b** 推理加速、端云路由与适配器 | 推理 Q4、Q5、Q6、Q8 | J3、J6、J8 | `notes/C1b-accel-routing-adapter.md` |
| **C2a** 执行沙箱与隔离底座 | 沙箱 Q1、Q6、Q7 | J5 | `notes/C2a-sandbox-isolation.md` |
| **C2b** 策略、凭证、接口面与 Agent 安全 | 沙箱 Q2、Q3、Q4、Q5、Q8 | J3（安全侧） | `notes/C2b-policy-interface-security.md` |
| **C3a** Agent 记忆系统与评测 | 记忆 Q1、Q2、Q4、Q6 | J1（记忆侧） | `notes/C3a-agent-memory-systems.md` |
| **C3b** 端侧个人上下文索引与隐私授权 | 记忆 Q3、Q5、Q7、Q8 | J4、J7 | `notes/C3b-personal-index-privacy.md` |
| **C4a** 移动端传统内存与统一记账 | 内存 Q1、Q5、Q6、Q8 | J2 | `notes/C4a-mobile-mm-accounting.md` |
| **C4b** 模型内存：KV、MoE、权重分页 | 内存 Q2、Q3、Q4、Q7 | J1（成本侧）、J6（内存侧） | `notes/C4b-model-memory.md` |

子模块报告按第 3.6 节模板写，但 §5 立场评审只评与本子模块相关的立场；§7 组件特有输出只做本子模块相关的部分。路径相对于 `proposals/agentos-components/`。

---

## 9. 回收与整合

四份调研回收后，按以下方式整合：

1. **立场评审 → 设计修订单**：把各报告 §5 的立场评审表合并，按两份设计文档（沙箱、内存管理）和两个未成文的组件（推理、记忆）分组，形成修订单：每条写立场 ID、修订动作、依据、优先级。
2. **谱系表 → 《AgentOS 外部参照全景》**：合并四份谱系表，按成熟度着色，标出每条路线与哪个立场相关。
3. **接缝 → 组件接口清单**：J1–J8 的发现汇成组件间接口的初稿，写清每个接口的提供方、调用方和数据格式要点。
4. **空白点 → 立项差异化论据**：调研发现的「公认空白点」与本部门的负载建模、系统仿真方向交叉，判断哪些空白可以用仿真先占位、哪些需要真机数据，产出立项差异化论据的最终版。

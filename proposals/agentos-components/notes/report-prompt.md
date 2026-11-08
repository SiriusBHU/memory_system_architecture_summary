# 汇报材料重写：负载量化与原型对比调研 Prompt（2026-11-07，可复用）

## 背景

我们在为一份 30 分钟的领导汇报重写主文档。主题是端侧 Agent OS 的四个系统组件：推理、沙箱、记忆、内存管理。结构见 `proposals/agentos-components/汇报材料重构规划.md`。

本 prompt 服务其中两节：

- **2.2 未来负载定义**：所有瓶颈都由负载引出，所以负载必须有理有据、数据翔实。
- **1.2 四组件技术趋势**：每个组件一张原型对比表。

根目录 `D:/projects/memory_system_architecture_summary/`。已有材料（先读，避免重复检索）：

| 材料 | 路径 | 用途 |
|---|---|---|
| 四组件调研 | `proposals/agentos-components/C1-推理框架与推理能力.md`、`C2-沙箱框架与执行能力.md`、`C3-记忆框架与记忆能力.md`、`C4-内存管理.md` | 已核实的事实、数据、参考文献（§1 谱系表、§2 关键数据、§8 参考资料） |
| 子模块笔记 | `proposals/agentos-components/notes/C1a…C4b-*.md`、`kimi-delta-C1…C4.md` | 更细的证据 |
| Kimi 调研 | `proposals/agentos-components/kimi调研/research/agentos_dim01–12.md` | 另一份独立调研；被其 `agentos_cross_verification.md` 标为不可靠的条目不得采用 |
| 设计文档 v0.1（Kimi 起草） | `proposals/agentos-components/kimi调研/AgentOS沙箱系统设计.md`、`AgentOS内存管理设计.md` | 只作设计参考，其中的事实陈述不能当来源 |
| 2027 立项笔记 | `proposals/2027-agentos-ai-graphics/notes/M1-agentos-commercial.md`（第二部分 2.1 场景与基线）、`D1-commercial-deep-dive.md`（Grok Bot、OpenAI dot 拆解）、`D2-foundation-evolution.md`（§1 端侧模型与 KV 对照表）、`M3-model-memory.md`、`M4-simulation-eval.md`（1.2-S1 Agent 负载刻画） | 负载基线与模型内存数据 |

## 通用约束

- **端侧设定**：2027 年旗舰手机，DRAM 12–16GB，UFS 4.x；端侧模型以 1–4B 激活参数为主（含 Apple AFM 3 这类稀疏模型），复杂任务可回落云端。
- **范围排除**：多 Agent 并发、GUI Agent（截屏 + 模拟点击）不在负载定义内（2026-11-03 立项决定）。Agent 通过 App Intents / MCP / 系统 API / 应用提供的工具执行。
- 中文写作，专有名词保留原名。区分平台术语：Android memcg / LMKD，iOS Jetsam，HarmonyOS 的 APL 与意图框架。
- **数字要求**：每个数字带来源、日期。厂商自报、媒体口径、二手转述，都要标注。
- **没有公开数据时**：写「估算」，并给出公式和输入，例如「KV = 2 × 层数 × KV 头数 × 头维度 × 字节 × token」。不得凭印象写数字。
- **引用限制**：摘录不超过 15 个英文词或 30 个汉字。
- **文件限制**：不得修改任何现有文件，只新建自己的输出文件。

## 参考负载：「贴身秘书」

一个常驻主 Agent 代表用户处理日常事务，同一时刻最多再跑 1–2 个子任务。四个组件的负载都从下面同一组任务原型推出。可以按证据调整原型参数，但要写明理由；不要另起一套原型。

| 原型 | 例子 | 交互性 | 特征 |
|---|---|---|---|
| **T1 即时指令** | 「把明天 9 点的会推迟半小时并通知参会人」 | 前台、用户等待 | 轮数少，有发消息类写操作 |
| **T2 跨应用事务** | 订票、订餐、打车、比价下单 | 前台、用户等待，关键步骤需确认 | 多步工具调用，含支付等不可逆操作，读入外部不可信内容 |
| **T3 长程任务** | 旅行规划、报销整理、周报汇总、长文档研究 | 可后台，跨数分钟到数小时，用户会切走再切回 | 上下文长，可能拆 1–2 个并行子任务，需要暂停与恢复 |
| **T4 后台感知与分拣** | 消息、邮件、通知分拣与摘要；日程冲突检测；待办提取；主动提醒 | 后台、事件触发、非交互 | 每天次数多，单次小，功耗敏感，大量读入不可信内容（注入入口） |
| **T5 个人记忆问答** | 「上次和张三谈的报价是多少」「护照什么时候过期」 | 前台 | 检索为主，生成短 |

另外要给出**一天的负载剖面**：

- 各原型每天的次数；
- 活跃时段；
- 峰值并发，典型峰值是「前台重应用 + 一个 T2 或 T3 + T4 后台」。

## 任务 A：负载量化（输出 `notes/L-C{n}-*.md`）

每个组件按下面的指标逐原型量化，再汇总成一天的剖面和峰值。

### C1 推理 → `notes/L-C1-推理负载.md`

1. 每个原型的轮数（LLM 调用次数）、每轮增量 prefill、每轮累计上下文、每轮 decode。依据可用：
   - Agent 基准的轨迹统计：τ-bench / τ²-bench、AppWorld、BFCL multi-turn、SWE-bench 类轨迹；
   - 系统刻画论文：「Agentic AI Workload Characteristics」arXiv 2605.26297；
   - 厂商披露：如 Manus 关于输入输出比与 KV 命中率的博客、Anthropic 多 Agent 研究系统的 token 倍数。
2. **核对 prefill : decode。** 用户的工作假设是 10 : 1。要分两个口径给出公开数据：
   - 不复用前缀时，每轮重算全部上下文的累计输入 : 输出；
   - 复用前缀 / KV 后的增量 prefill : decode。

   说明这两个口径各自对端侧意味着什么：算力、KV 驻留、能耗。
3. 并发会话数（峰值、典型值），以及系统提示、工具定义等可共享前缀的长度。
4. 时延要求：前台首 token、每秒 token 数；后台允许的时延。
5. 换算成端侧算力需求。参照 2026 旗舰的端侧实测：
   - Apple 2024 基础模型报告中 iPhone 15 Pro 的首 token 时延与生成速率；
   - 「Is Your NPU Ready for LLMs?」arXiv 2607.05475；
   - MLPerf Mobile 等。

   据此判断哪些原型能在端侧跑满足时延、哪些必须上云。

### C2 沙箱 → `notes/L-C2-沙箱负载.md`

1. 每个原型的工具调用数、其中写操作 / 不可逆操作 / 涉及支付或隐私的操作占比、读入不可信内容的比例。依据可用：
   - τ-bench 写操作、AppWorld 状态改变 API 占比；
   - ToolEmu、Agent-SafetyBench、AgentDojo 的风险动作统计；
   - MCP 生态使用统计。
2. **沙箱生命周期。** 每个原型要几个沙箱实例（按会话、按任务还是按工具调用）、每个实例的存活时长。存活期内的空闲比例，即等待模型或等待用户的时间占比；要核实设计文档里「71%–98%」的出处。
3. **暂停、快照、换出、换入。**
   - 什么事件触发（用户切走、等待确认、内存压力）、频率多高、恢复时延要求多少。
   - 云端参照：Firecracker 快照恢复、E2B pause / resume 的时长与每 GB 代价、CubeSandbox 的启动与内存开销。
   - 端侧参照：Android 进程 / isolated process / AVF Microdroid pVM 的启动时延与内存开销。
4. 峰值并发沙箱数，以及「并发数 × 单实例内存 + 快照存储」的内存与存储需求。

### C3 记忆 → `notes/L-C3-记忆负载.md`

1. **写入。**
   - 来源和每天的原始事件量：通知、消息、邮件、日程、照片、App 使用事件、Agent 自身的任务记录。尽量用手机使用研究的公开数据，例如每天通知数。
   - 抽取成记忆条目后的数量；参照 Mem0、MemGPT / Letta、A-Mem 等的抽取比例。
   - 单条大小：文本加向量，向量维度 × 字节。
   - 1 年、3 年的累积规模，以及索引占用的存储与内存。
2. **读取。**
   - 每个原型的检索次数、每次注入推理上下文的 token 数（这会回流到推理的 prefill）；
   - 检索时延要求；
   - 端侧向量检索的实测时延与内存，如 sqlite-vec、FAISS 移动端等。
3. **质量基线。** LongMemEval、LoCoMo 的历史规模与代表系统得分，说明「记得住、找得到」现在做到什么程度。
4. **更新与遗忘。** 冲突更新、过期删除、摘要压缩（驱逐入库）的频率。还要给出跨 App 读取记忆的授权请求频率。

### C4 内存管理 → `notes/L-C4-内存负载.md`

1. **常驻内存按类别拆分。** 每类给出大小、随什么增长、能否回收、回收后重建代价（重读 UFS 的时间，或重算 prefill 的时间）：
   - 模型权重：稠密 3B INT4、稀疏模型的 DRAM 驻留部分、PLE 卸载；
   - KV cache：每 token 字节 × 各原型上下文 × 并发会话；共享前缀只算一份；
   - LoRA 适配器：个数 × 大小；
   - 运行时缓冲：激活、NPU 上下文二进制、scratch；
   - 记忆的 embedding 模型与向量索引；
   - 沙箱实例。
2. **一天的内存剖面与峰值。** 峰值时刻的总需求，对比 12GB / 16GB 机型扣除系统与前台应用后的可用预算。基线取 M1 第二部分；Android 17 Memory Limiter 的口径取 C4。
3. **哪些内存必须钉住，哪些可以分层。** 给出 KV 换出到 UFS 与重算 prefill 的盈亏平衡点：按 UFS 4.1 约 4.3GB/s 读带宽和端侧 prefill 速度估算。

### 每份负载笔记的输出结构

```
# 负载量化：C{n} {组件}（贴身秘书参考负载）
> 日期；检索次数（WebFetch x / WebSearch y）；一句话结论

## 1 逐原型量化表
| 原型 | 指标1 | 指标2 | … | 依据 |
（每个数字在依据列写来源编号，或「估算：公式」）

## 2 一天的剖面与峰值
文字加小表。

## 3 关键推导
3–6 段，每段先写结论再写推导。例如「T3 恢复必须在 1s 内，因为…」。

## 4 对当前端侧机制意味着什么
3–6 条：哪个数字超出了现有机制的能力，为什么。供 2.4 瓶颈分析使用，只写事实与推导，不写方案。

## 5 参考资料
| 编号 | 标题 | 机构/作者 | URL | 日期 | 核验情况 |

## 6 待核实
```

## 任务 B：原型对比表（输出 `notes/P-C{n}-*.md`）

每个组件一张大表：

- **列**：技术原型，6–8 个，覆盖商业平台、云端或开源产品、学术 demo 三类。
- **第 1 行**：各原型的简介（是什么、谁做的、何时、形态），≤40 字。
- **其余各行**：下面列出的关键技术要素，每个要素一行。
- **格子**：用 ● 已具备 / ◐ 部分具备 / ○ 缺失 / — 不适用 标出达成情况，再加 ≤25 字说明和参考编号。

原型以下面的候选为准，可替换 1–2 个，并写明理由。证据优先取已有材料（C{n}.md 的 §1 谱系表、§3、§8，以及 notes），只对拿不准的格子做一手核验。

表后写「读表结论」4–6 条：

- 哪些要素已普遍做成；
- 哪些要素普遍缺失或只有云端做成；
- 端侧与云端的差距在哪；
- 学术 demo 领先产品的地方。

### C1 推理 → `notes/P-C1-推理原型对比.md`

- **候选列**：
  - Android AICore + NPU Manager（Android 17）
  - Apple Foundation Models 框架（含 AFM 3）
  - Windows ML / Copilot+ 端侧运行时
  - HarmonyOS 端侧大模型服务
  - vLLM / SGLang（云端参照）
  - 学术 demo：LLMS（LLM as a System Service on Mobile Devices），以及 1 个端侧多租户 / 异构调度相关工作
- **要素行**：
  1. 系统级共享模型服务（单底座、多客户端）
  2. 多会话调度与优先级
  3. 抢占粒度（请求 / 模型 / 会话 / token 级）
  4. 异构算力路由（CPU / GPU / NPU）
  5. 前缀与 KV 复用、持久化
  6. 多适配器驻留与热切换
  7. 端云路由与隐私控制
  8. 计量与配额

### C2 沙箱 → `notes/P-C2-沙箱原型对比.md`

- **候选列**：
  - Android（应用沙箱 + isolated process + AVF / Microdroid）
  - iOS（App Sandbox + App Intents）
  - HarmonyOS（应用沙箱 + 意图框架 / APL）
  - E2B 或腾讯 CubeSandbox（云端 microVM）
  - NVIDIA OpenShell
  - Claude Code / Codex 本地沙箱
  - 学术 demo：CaMeL（Google DeepMind），以及 IsolateGPT / SecGPT 或 FIDES 之一
- **要素行**：
  1. 隔离粒度（App / 进程 / 会话 / 工具调用）
  2. 隔离机制与强度
  3. 启动时延与单实例内存开销
  4. 快照、暂停恢复与回滚
  5. 可逆性分级 / dry-run / undo
  6. 策略表达与带外执法
  7. 数据标签与信息流控制
  8. 出口控制（含 DNS）
  9. 凭证托管与代为请求
  10. 审计与可验证性

### C3 记忆 → `notes/P-C3-记忆原型对比.md`

- **候选列**：
  - Apple Intelligence（语义索引 / 个人上下文）
  - Google Gemini 个人上下文（Android）
  - HarmonyOS 小艺记忆
  - ChatGPT Memory
  - Mem0
  - Letta / MemGPT
  - Zep / Graphiti 或 MemOS 之一
  - 学术 demo：A-Mem 或 OpenViking（本仓库 `insight/` 有调研）之一
- **要素行**：
  1. 记忆分层（工作 / 情景 / 语义 / 程序）
  2. 自动抽取、去重与冲突更新
  3. 检索方式与基准成绩
  4. 遗忘与生命周期
  5. 来源与完整性标签、写入治理
  6. 端侧运行（存储、索引、功耗）
  7. 系统级跨 App 索引
  8. 第三方授权与访问控制
  9. 用户可见、可编辑、可删除

### C4 内存管理 → `notes/P-C4-内存管理原型对比.md`

- **候选列**：
  - Android（LMKD + memcg + Android 17 Memory Limiter）
  - iOS（Jetsam + 内存压缩 + increased-memory-limit）
  - HarmonyOS / OpenHarmony（ESWAP 等）
  - Linux 主线（MGLRU、dmem cgroup、dma-buf memcg RFC）
  - Apple AFM 3 运行时（稀疏权重存 NAND）
  - vLLM PagedAttention（云端参照）
  - 学术 demo：LLMS 的分块 KV 换出，以及 PowerInfer-2 或 LLM in a Flash 之一
- **要素行**：
  1. 模型内存可见性与记账（含 dma-buf / GPU / NPU）
  2. 共享服务的代分配归账
  3. KV cache 管理（分页 / 压缩 / 换出 / 重算）
  4. 权重分层与按需换入
  5. 与应用内存的统一回收与 QoS
  6. 冷热识别（MGLRU / 硬件采样）
  7. 压缩交换（zram / zswap）
  8. 模型加载 IO 与零拷贝映射

### 每份原型笔记的输出结构

```
# 原型对比：C{n} {组件}
> 日期；检索次数；列的取舍理由（一句话）

## 1 对比表
## 2 读表结论
## 3 格子说明（只对 ◐ 和有争议的格子，每条 1–2 句，带参考编号）
## 4 参考资料
| 编号 | 标题 | 机构/作者 | URL | 日期 | 核验情况 |
## 5 待核实
```

## 检索预算

- **任务 A**：每人 WebFetch ≤12 次，WebSearch ≤5 次。
- **任务 B**：每人 WebFetch ≤8 次，WebSearch ≤3 次。
- 优先抓已知的一手 URL：官方文档、arXiv abs 页、AOSP、GitHub、厂商博客。额度用完就停。抓取失败或页面不含该论断的，标「未核实」。

## 回报

完成后用 5 行以内回报：

- 输出文件路径；
- 最重要的 3 个数字或结论；
- 最大的数据缺口。

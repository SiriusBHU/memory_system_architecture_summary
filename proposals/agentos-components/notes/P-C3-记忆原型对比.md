# 原型对比：C3 记忆

> 2026-11-07；检索次数 WebFetch 0 / WebSearch 0（全部证据取自 C3 主文档、C3a/C3b 笔记与本库 OpenViking 调研，未做一手复核）；列的取舍：Gemini 个人上下文并入「Google」一列（Magic Cue 与 Personal Intelligence 的授权与存储差异在格内注明）；「Zep / Graphiti 或 MemOS 之一」取 Zep（C3 对 MemOS 只有论文层设计，无 OS 强制，证据不足）；「A-Mem 或 OpenViking 之一」取 OpenViking（本库有专门调研，A-Mem 只有第三方测得的开销数据）。

**图例**：● 已具备；◐ 部分具备；○ 缺失，或未找到公开证据（凡属后者，说明里写「未公开」，不等于确认没有）；— 不适用（框架类产品不是 OS 层，无此要素）。格内编号见 §4，`E*` 来自 C3a，`R*` 来自 C3b，`K*` 来自 Kimi 核验条目，`I1` 为本库 `insight/` 对 OpenViking 的调研。厂商自报数字一律在格内注「自报」。

## 1 对比表

| 要素 | Apple Intelligence（语义索引 / 个人上下文） | Google（Magic Cue + Gemini 个人上下文） | HarmonyOS 小艺记忆 | ChatGPT Memory | Mem0 | Letta / MemGPT | Zep / Graphiti | OpenViking（学术 / 开源 demo） |
|---|---|---|---|---|---|---|---|---|
| **简介** | Apple；iOS；App Intents 实体经 Core Spotlight 语义检索；Siri AI 属 iOS 27 [R13][K6] | Google；Magic Cue 端侧 Nano 加云增强，Gemini PI 读云账户数据 [R9][R17] | 华为；记忆主页存卡证、地址、订单；应用侧有数据增强套件 [R18][R19] | OpenAI；云端；saved memories 加聊天历史引用 [E27] | Mem0；开源 / 云；LLM 抽取事实入向量库，2026-04 起只加不删 [E7] | Letta（源自 MemGPT）；开源；core 块加 archival，2026-02 改 git 文件 [E24] | Zep AI；开源 Graphiti；双时间轴知识图谱 [E4] | 火山引擎；开源；`viking://` 目录加 L0/L1/L2 分层，会话末抽取六类记忆 [I1] |
| **1 记忆分层** | ○ 实体索引，无分层公开 [R13] | ◐ 个人上下文加过往聊天；分层未公开 [E27] | ◐ 按卡证、地址、订单、事件分类 [R18] | ◐ 显式记忆加历史引用两层 [E27] | ◐ 按 user/agent/run 作用域，非时间层 [R32] | ◐ 工作加外存两层，无独立程序层 [E24] | ◐ 情景、语义实体、社区三层子图 [E4] | ● 六类含事件、案例、模式；L0/L1/L2 管加载 [I1] |
| **2 自动抽取、去重、冲突更新** | ○ 应用主动 donate，无抽取公开 [R13] | ◐ 系统自动记忆；冲突处理未公开 [E27] | ◐ 自动记兴趣、职业；去重未公开 [R18] | ◐ 模型判定加用户指令；冲突未公开 [E27] | ◐ 单次抽取只加不删，冲突留给检索 [E7] | ◐ Agent 自写；子 Agent 靠 git 合并 [E24] | ◐ 时间边失效旧事实；多跳冲突基准弱 [E4][E2] | ◐ 会话末自动抽取；去重待核实 [I1] |
| **3 检索方式与基准成绩** | ◐ 词法加语义；无基准 [R13] | ○ 机制与基准均未公开 [E27] | ◐ 向量加倒排加重排；无基准 [R19] | ○ 不公开；无基准 [E27] | ◐ 向量可选图；LoCoMo 92.5 自报 [E7] | ◐ grep 与文件工具；LoCoMo 74.0 自测 [E6] | ◐ 图加时间检索；LoCoMo 58–84 有争议 [E5] | ◐ L0 向量定位目录；LoCoMo 80–83 自评 [I1] |
| **4 遗忘与生命周期** | ○ 未公开 | ◐ 用户可管理；细节未公开 [E27] | ◐ 主页可管理；删除能力待核实 [R18] | ◐ 可删；关历史后 30 天内清除 [E27] | ○ 新算法只加不删 [E7] | ◐ 块可编辑删除；摘要压缩 [E24] | ◐ 时间边失效，非物理删除 [E4] | ○ 未找到遗忘或 TTL 说明 [I1] |
| **5 来源与完整性标签、写入治理** | ◐ 实体来源明确；无完整性标签 [R13] | ○ 未公开；延迟工具调用注入被演示 [R29] | ○ 未找到公开资料 | ○ 记忆注入已被演示 [R29] | ○ 无溯源字段 [R32] | ◐ git 提交留痕；无完整性标签 [E24] | ◐ 情景子图可回溯原文（推断）[E4] | ◐ 检索轨迹留痕；无完整性标签 [I1] |
| **6 端侧运行（存储、索引、功耗）** | ◐ 端侧索引；体积功耗未公开 [R13] | ◐ Nano 端侧加云增强；PI 在云 [R8][R17] | ◐ 端云协同；存储位置待核实 [R18] | ○ 纯云端 [E27] | ○ 抽取需 LLM；无端侧数据 [E7] | ◐ 文件加工具可迁移（判断）；无实测 [E24] | ○ 构图依赖 LLM；内存未知 [E4] | ○ 服务端数据库，需裁剪 [I1] |
| **7 系统级跨 App 索引** | ◐ 跨 App 实体；读取限系统 [R13][K6] | ◐ 限 Google 自家应用 [R9] | ◐ 系统记忆有；跨应用索引无 [R19] | — 应用内记忆 | — 框架，非 OS 层 | — 框架，非 OS 层 | — 框架，非 OS 层 | — 框架，非 OS 层 |
| **8 第三方授权与访问控制** | ◐ 应用声明实体；读取侧未公开 [R13] | ◐ 应用级连接，默认关闭 [R17] | ◐ Picker 与 UDMF，无语义层（转引）[K7] | ○ 账户级，无第三方细粒度 [E27] | ◐ 标识过滤，无角色读写 ACL [R32] | ◐ 共享块整块只读 [R32] | ○ 未找到公开资料 | ◐ 目录作用域加 API-Key 多租户 [I1] |
| **9 用户可见、可编辑、可删除** | ○ 未找到公开说明 | ◐ 可管理可导入；来源追溯弱 [E27] | ◐ 主页可见；编辑删除待核实 [R18] | ● 条目可见可删；删聊天不删记忆 [E27][R38] | ◐ 仅 API 层，界面由应用做（推断）[R32] | ● 块与 git 文件可读可改 [E24] | ◐ 图可检视；删除要清关联边 [E4] | ◐ 目录可检视；删除语义待核实 [I1] |

## 2 读表结论

1. **普遍做成的只有「用户可见可删」和「抽取式写入」。** 商业助手几乎都有条目级可见可删（第 9 行），写入全部由模型或框架内模型完成（第 2 行）。这与 C3 §3 Q1 的判断一致：写入策略已交给模型，OS 没有介入 [E6][E7][E11]。
2. **普遍缺失的是治理类要素：来源与完整性标签、遗忘、第三方授权。** 第 5 行没有一家做到 ●，商业产品要么未公开，要么已被攻破演示 [R29]；第 4 行没有 ●，Mem0 与 OpenViking 甚至不删；第 8 行最细只到「应用级连接」或「整块只读」。这些恰好是 C3 立场里 OS 能发力的位置（MEM-1′ 的元数据、ACL、级联删除）。
3. **检索与基准成绩口径混乱，不能用来选型。** 第 3 行全部为 ◐ 或 ○：能报分的都是厂商自报，且同一系统在 LoCoMo 上有 58–84 的多种说法 [E5]；Letta 的纯文件基线 74.0 高于 Mem0 当时的自报 68.5 [E6]。冲突更新是共同短板（MemoryAgentBench 多跳所有方法不超过约 7%）[E2]，第 2 行没有 ● 与此对应。
4. **端侧与云端的差距：端侧只有「索引」，没有「记忆管理」；管理能力都在云端或服务端。** 第 6 行没有 ●。云端 / 开源一侧（Mem0、Zep、Letta、OpenViking）有抽取、图、分层，但依赖 LLM 常驻与服务端存储，无端侧实测；端侧一侧（Apple、Google、华为）有系统级索引，但抽取、遗忘、标签机制均未公开。端侧资源成本只有 EmbeddingGemma 低于 200MB 一个数据点 [R34]（C3 J7）。
5. **系统级跨 App 索引只有三家系统厂商有，且都不对第三方 Agent 开放读取。** 第 7、8 行：Apple 的 IndexedEntity 是唯一文档化的第三方 donation 入口 [R13]，读取侧未公开；Google 与华为限自家应用或应用自建知识库 [R9][R19]。「开放、查询时授权、跨应用、来源可追溯」四者同时满足的格子为空（C3 MEM-4′）。
6. **学术与开源 demo 领先产品的地方在「可检视」与「可借鉴原语」，而非治理。** OpenViking 的目录范式、分层加载和检索轨迹回放 [I1]，Letta 的 git 版本化记忆 [E24]，都比商业产品更透明；学术上的 Collaborative Memory 已有读写双策略和不可变溯源 [R31]（未单列一列），防投毒的来源绑定也只在预印本里 [R30]。但这些都没有进入任何一个量产的端侧系统。

## 3 格子说明（只对 ◐ 和有争议的格子）

- **OpenViking 第 1 行记 ●**：依据是其抽取出的六类记忆（Profile、Preferences、Entities、Events、Cases、Patterns）已覆盖情景、语义与近似程序性内容 [I1]；L0/L1/L2 是加载粒度而非记忆类型。该数据为其自评口径，未独立核实。
- **Letta 第 1 行记 ◐**：core 块（常驻）加 archival（外存）已是经典的两层虚拟上下文，但没有独立的程序性记忆机制 [E24]。C3 §4 称程序性记忆缺独立机制和基准，仅 LangMem 有（单一博客来源，未核实）。
- **Mem0 第 2 行记 ◐**：2026-04 的新算法改为单次 ADD-only，不再做 UPDATE / DELETE，冲突推给检索阶段 [E7]；这是对冲突更新的主动放弃，不是尚未实现。学术上选择性删除平均有约 10% 绝对提升 [E25]，两者是真实分歧。
- **Zep 第 2 行记 ◐**：双时间轴让旧事实失效而不物理删除，机制是各列中最完整的；但 MemoryAgentBench 上 Zep 总分 24.0，并不领先 [E2]，所以只给 ◐。
- **Zep 第 5 行记 ◐（推断）**：Zep 有保留原始消息的情景子图，据此推断事实可回溯，但检索到的材料中没有明说来源标签字段 [E4]，待核实。
- **第 3 行全部 ◐ 或 ○**：Mem0 92.5 是厂商自测、无独立复现 [E7]；Letta 74.0 是 GPT-4o-mini 下自测 [E6]；OpenViking 80–83 是自评 [I1]；Zep 的四个数字为二手转述 [E5]。没有任何一家有第三方在端侧口径下的成绩。
- **小艺第 8 行记 ◐**：Picker 与 UDMF 的依据是华为安全白皮书经 Kimi 转引，本库未抓原文 [K7]；这是条目级与通路级授权，没有语义索引层。
- **Google 第 6、8 行记 ◐**：Magic Cue 端侧用 Gemini Nano 并在 2025-11 起叠加云增强，是否仍落在 Private Compute Core 内待核实 [R8][R9]；Gemini Personal Intelligence 读云账户数据，不是端侧索引 [R17]。
- **Apple 第 7 行记 ◐**：Siri AI 属 iOS 27，Apple 官方称曾为 EU 设计 Trusted System Agent 让第三方助手经系统中介访问，被欧委会拒绝 [K6]；对第三方的读取范围至今未公开，所以不给 ●。
- **ChatGPT 第 9 行记 ●**：条目级可见可删有官方依据 [E27]；「删来源聊天不删记忆」来自二手转述 [R38 一类，C 级]；可导出与来源追溯弱，这里只评「可见可编辑可删除」。

## 4 参考资料

| 编号 | 标题 | 机构 / 作者 | URL | 日期 | 核验情况 |
|---|---|---|---|---|---|
| E2 | Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions（MemoryAgentBench） | Hu、Wang、McAuley | https://arxiv.org/html/2507.05257v2 | 2025-07；ICLR 2026 | 沿用 C3a，A 级 |
| E4 | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | Zep AI | https://arxiv.org/abs/2501.13956 | 2025-01 | 沿用 C3a；论文宣称，厂商作者 |
| E5 | Lies, Damn Lies, & Statistics: Is Mem0 Really SOTA in Agent Memory? | Zep | https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/ | 2025 | 未打开全文，数字二手转述，C 级 |
| E6 | Benchmarking AI Agent Memory: Is a Filesystem All You Need? | Letta | https://www.letta.com/blog/benchmarking-ai-agent-memory | 2025-08-12 | 沿用 C3a；厂商自测，B 级 |
| E7 | Mem0 新算法博客与评测文档 | Mem0 | https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm ；https://docs.mem0.ai/core-concepts/memory-evaluation | 2026-04 / 05 | 沿用 C3a；厂商自测，无独立复现 |
| E11 | Managing context on the Claude Developer Platform | Anthropic | https://claude.com/blog/context-management | 2025-09-29 | 沿用 C3a |
| E24 | Introducing Context Repositories: Git-based Memory for Coding Agents | Letta | https://www.letta.com/blog/context-repositories | 2026-02 | 沿用 C3a |
| E25 | How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior | Xiong 等 | https://arxiv.org/abs/2505.16067 | 2025-05 | 沿用 C3a，预印本 |
| E27 | OpenAI Memory FAQ；Bringing memory to Claude；Gemini 记忆导入 | OpenAI；Anthropic；Google | https://help.openai.com/en/articles/11146739-how-does-reference-saved-memories-work ；https://claude.com/blog/memory ；https://blog.google/innovation-and-ai/products/gemini-app/switch-to-gemini-app/ | 2025–2026 | 沿用 C3a；ChatGPT 行为部分为二手 |
| R8 | Google Private AI Compute（Pixel） | 9to5Google | https://9to5google.com/2025/11/11/google-private-ai-compute-pixel/ | 2025-11-11 | 沿用 C3b；媒体，B/C 级 |
| R9 | Google upgrades Magic Cue with Gemini models | Digital Trends | https://www.digitaltrends.com/phones/google-just-upgraded-magic-cue-on-your-pixel-10-with-advanced-gemini-models-without-compromising-privacy/ | 2025-11 | 沿用 C3b；媒体 |
| R13 | Making app entities available in Spotlight | Apple Developer Documentation | https://developer.apple.com/documentation/appintents/making-app-entities-available-in-spotlight | 未标注 | 沿用 C3b；官方文档，A 级 |
| R17 | Gemini personalization overview | Google | https://gemini.google/overview/personalization/ | 未标注 | 沿用 C3b；厂商页面 |
| R18 | 小艺记忆能快速记忆重要的个人信息 | 华为消费者业务支持 | https://consumer.huawei.com/cn/support/content/zh-cn16010214/ | 基于 HarmonyOS 4.2 | 沿用 C3b；官方，B 级 |
| R19 | dataaugmentation capi module | 华为开发者联盟 | https://developer.huawei.com/consumer/cn/doc/doccenter-references/api/dataaugmentation-capi-module.md | 未标注 | 沿用 C3b；官方 API 页，检索链路细节来自开发者博客（C 级） |
| R29 | Gemini long-term memory attack | InfoQ | https://www.infoq.com/news/2025/02/gemini-long-term-memory-attack/ | 2025-02 | 沿用 C3b；媒体转述，C 级 |
| R30 | 2026 记忆投毒防御预印本（2601.05504、2606.24322、2605.08442） | arXiv | https://arxiv.org/abs/2601.05504v1 | 2026 | 沿用 C3b；预印本，未逐篇核对 |
| R31 | Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control | Rezazadeh 等（Accenture） | https://arxiv.org/html/2505.18279v1 | 2025-05-23 | 沿用 C3b |
| R32 | Mem0 entity-scoped memory；Letta shared memory blocks；LangGraph stores | 各项目文档 | https://docs.mem0.ai/platform/features/entity-scoped-memory ；https://docs.letta.com/guides/agents/shared-memory-blocks | 未标注 | 沿用 C3b，A 级 |
| R34 | EmbeddingGemma model overview | Google AI for Developers | https://ai.google.dev/gemma/docs/embeddinggemma | 2025-09 | 沿用 C3b；B 级 |
| R38 | How does Claude's memory work | Anthropic Help Center | https://support.anthropic.com/en/articles/11817273-how-does-claude-s-memory-work | 未标注 | 沿用 C3b；本表仅用于 ChatGPT 对照的间接旁证，ChatGPT 本身行为未取一手 |
| K6 | Due to the DMA, Siri AI delayed in the EU for iOS 27 and iPadOS 27 | Apple Newsroom | https://www.apple.com/newsroom/2026/06/due-to-dma-siri-ai-delayed-in-eu-for-ios-27-and-ipados-27/ | 2026-06-08 | C3 已抓官方页面 |
| K7 | HarmonyOS NEXT 安全技术白皮书（权限取消、System Picker、UDMF） | 华为 | 来自 Kimi dim08 脚注 21、22、45 | 2024-08 | 未抓原文，Kimi 转引 |
| I1 | OpenViking 上下文数据库调研（引 OpenViking 官方 README 与公开报道） | 本库 insight | `insight/N+1/on-device-agent-memory-system/openviking-context-database-CN.md`；原项目 https://github.com/volcengine/OpenViking | 2026 | 本库文档；所有指标为 OpenViking 自评，本轮未回查原仓库 |

## 5 待核实

1. Apple 个人上下文 Siri 在 iOS 27 中对第三方的读取范围、Core Spotlight 语义索引是否有 TEE 保护（均未公开）；Apple 在记忆抽取、遗忘、用户可见编辑上的公开说明，目前整列只有 donation 一条硬证据。
2. Google 第 3、4、5 行（检索机制、遗忘、来源标签）全是「未公开」，可补查 Pixel / Gemini 官方帮助页；Magic Cue 是否仍落在 Private Compute Core 内。
3. 小艺记忆的存储位置（端 / 云）、删除与编辑能力；K7 白皮书原文；数据增强套件在系统层的角色。
4. ChatGPT 记忆行为（删来源聊天是否影响记忆、检索机制）只有二手来源；本表未对 OpenAI 官方帮助页做一手复核（检索预算未用）。
5. Zep 的来源标签 / 溯源字段、共享与 ACL、隐私方案，C3 对比表已标「待核实」，本表第 5、8 行沿用。
6. OpenViking 的去重、冲突更新、遗忘 / TTL、删除语义：本库调研未涉及，需读原仓库；其 LoCoMo 80–83 为自评。
7. 本表未覆盖的学术先例：A-Mem（互链笔记，第三方测得建索引约 15 小时 [E9]）、MemOS 的 MemCube 治理属性（论文设计，无 OS 强制 [K4]）、Collaborative Memory 的读写双策略与不可变溯源 [R31]。若需要学术 demo 在第 5、8 行领先产品的论据，可把 Collaborative Memory 单列一列。
8. 所有格子均为公开资料口径；「○ 未公开」不能解读为「确实没有」，对外汇报时需保留该限定。

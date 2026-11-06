# AgentOS 维度 A：Agent 记忆系统格局 + 记忆评测

> 调研日期：2026-11-06。时间范围 2024-01 ～ 2026-11（MemGPT 等奠基工作标注年份）。
> 我方立场速记：OS 提供记忆的存储/索引/ACL/跨 Agent 共享（类比文件系统提供 inode），「记什么、忘什么、何时检索」策略归 Agent；记忆框架与内存管理之间有「有损驱逐」接口（KV/上下文被驱逐时摘要入库）。

---

## 1. 技术谱系表

### 1.1 认知架构源头（奠基，2023 及以前）

| 工作 | 年份 | 贡献 |
|---|---|---|
| Soar（Laird）/ ACT-R（Anderson） | 1980s–2012 | 经典认知架构：Soar 将陈述性知识拆为语义记忆与情景记忆（自动快照工作记忆 + 时间元数据），ACT-R 用统一陈述性记忆 + 激活方程（基频×新近度×联想强度）；两者均有程序性产生式规则与 RL 学习[^14^][^15^] |
| Tulving 1972 / Baddeley & Hitch 1974 / Squire 1987 | — | 情景/语义记忆区分、工作记忆模型、程序记忆——现代 Agent 记忆分类的心理学源头[^12^] |
| Generative Agents（Park et al., UIST） | 2023 | 记忆流 + recency/importance/relevance 三因子检索打分 + 周期性反思（reflection）把情景记录综合为高层语义知识[^17^] |
| CoALA（Sumers et al., Princeton, arXiv:2309.02427, TMLR 2024） | 2023 | 将 Soar/ACT-R 的记忆分类学翻译为语言 Agent 框架：工作记忆（当前上下文）+ 长期记忆（情景/语义/程序），学习=写长期记忆。被 IBM、MongoDB、LangChain、Letta、Mem0 文档普遍采用，是事实上的行业标准词汇[^12^][^13^][^15^] |

### 1.2 现代记忆系统谱系（2024–2026）

| 系统 | 年份/出处 | 记忆类型划分 | 核心机制 | 存储引擎 | 关键数字 |
|---|---|---|---|---|---|
| **MemGPT / Letta** | 2023-10（arXiv:2310.08560）；2024 起产品化 | 分层「虚拟上下文」：Main context（system + working context + FIFO 队列）/ External context（recall=全量对话可检索；archival=向量索引长期库） | Agent 通过工具调用（core_memory_append/replace、archival_memory_insert/search、conversation_search）**自编辑**记忆；memory pressure 中断通知驱逐决策 | Postgres + pgvector（记忆块、历史、embedding 一体化） | DMR：GPT-4 基线 32.1%→92.5%，GPT-4 Turbo 35.3%→93.4%[^1^][^5^][^6^] |
| **Letta sleep-time compute** | 2025-04（arXiv:2504.13171） | 主 Agent + 后台「sleeptime」Agent 共享记忆块 | 空闲期后台整合：改写 core memory、摘要、使矛盾记忆失效——整合移出关键路径 | 同上；2026-02 推出 git 化 Context Repositories（版本化记忆文件系统） | 厂商报告：同等精度下 test-time compute 降 ~5×；等算力下 GSM-Symbolic +13%、AIME +18%（自报）[^9^][^10^][^11^] |
| **Zep / Graphiti** | 2025-01（arXiv:2501.13956） | 三层：episodic 节点（原始消息）→ 语义实体与事实（双时态边）→ community 摘要 | Graphiti 时序知识图谱：每条边带 4 个时间戳（事务时 t_created'/t_expired' + 有效时 t_valid/t_invalid）；失效用 invalidation 而非删除；检索=cosine + BM25 + 图广度遍历，RRF/MMR/cross-encoder 重排 | 图数据库（Neo4j 等）+ 向量索引 | DMR 94.8% vs MemGPT 93.4%；LongMemEval 较全上下文基线 +15.2%（4o-mini）/ +18.5%（4o），延迟降 ~90%[^2^][^16^] |
| **Mem0** | 2025-04（arXiv:2504.19413，ECAI 2025） | 用户/会话/Agent 三级作用域；抽取式事实记忆（语义为主）；Mem0g 图变体 | 两阶段：extraction（新消息对 + 滚动摘要 + 最近 10 条消息抽取事实）→ update（与最相似 10 条旧记忆比对，LLM 决定 ADD/UPDATE/DELETE/NOOP）；Mem0g 把冲突关系标记 invalid 而非删除 | 向量库 +（Mem0g）Neo4j 图 + KV | LoCoMo LLM-judge 66.88%（全上下文 72.90%）；检索 p50 0.148s/p95 0.200s，总 p95 1.44s vs 全上下文 17.12s；~1.8K vs 26K tokens/会话[^3^][^18^][^19^] |
| **LangGraph / LangMem** | 2025（LangChain） | CoALA 三分法最完整实现：semantic（事实/画像）、episodic（历史交互作 few-shot 示例）、**procedural（Prompt Optimizer 让 Agent 改写自己的系统提示——独有）** | 双写路径：hot path（会话中 create_manage_memory_tool / create_search_memory_tool）+ background（create_memory_store_manager + ReflectionExecutor 异步整合） | 后端无关：LangGraph BaseStore（namespace 隔离 user/agent）、Postgres、向量库 | 第三方复测 LoCoMo ~58–78%，p95 搜索延迟高达 ~60s（Mem0 论文报 LangMem p50 17.99s/p95 59.82s）[^7^][^18^][^22^] |
| **Cognee** | 2024 创立，2025–26 成熟（topoteretes/cognee，30k+ stars） | 会话记忆（快路径）+ 永久知识图谱；remember/improve/recall/forget 四操作 | ECL 管线（Extract-Cognify-Load）：classify→permissions→chunk→graph-extract→summarise→embed；反馈环更新边权 | 本地嵌入式栈：SQLite + LanceDB + Kuzu（可选 Neo4j/Neptune） | HotPotQA 多跳：0.93 vs 基础 RAG 0.4（厂商自测）[^8^] |
| **MemOS（MemTensor，上海AI Lab 等）** | 2025-05/07（arXiv:2505.22101；arXiv:2507.03724） | 三种正交记忆形态：**明文（plaintext）/ 激活态（KV-cache、隐状态）/ 参数态（权重）**，统一封装为 MemCube | **最接近"OS 级记忆"的学术先例**：MemCube=元数据头（描述性/治理属性[访问权限、TTL、敏感度标签、水印、访问日志]/行为指标）+语义载荷；MemScheduler 策略感知调度、MemLifecycle 生命周期、MemGovernance 访问控制、MemVault 存储、MemStore 跨平台共享；支持 Plaintext⇄Activation⇄Parametric 跨形态转换 | 三层架构（Interface/Operation/Infrastructure） | LoCoMo 上 MemOS-0630 报告一致性优势（见原文）[^4^] |
| **AIOS** | 2024-03（arXiv:2403.16971，COLM 2025） | Memory Manager（RAM 级短期交互日志）+ Storage Manager（长期持久化）分离 | LLM 内核模块化：agent scheduler / context manager（快照恢复）/ memory manager / storage manager / tool manager / **access manager（Agent 间隐私与访问控制）** | 内核级 CRUD + 原子操作 + 线程安全 | —[^20^][^21^] |
| **MIRIX** | 2025-07（arXiv:2507.07957） | 六种记忆：Core/Episodic/Semantic/Procedural/Resource/Knowledge Vault（逐字敏感信息） | **多 Agent 记忆管理**：6 个 Memory Manager + Meta Memory Manager 负责任务路由；Active Retrieval（回答前先生成检索主题） | 分层结构化存储 | LoCoMo 上曾报 SOTA（第三方表：multi-hop 83.7%、temporal 88.4%）[^23^][^24^] |
| **A-MEM** | 2025-02（arXiv:2502.12110，NeurIPS 2025） | Zettelkasten 式互联知识网络 | 记忆笔记自动生成关键词/标签/链接，动态演化 | 向量+链接结构 | 检索开销较大（p50 0.668s，Mem0 论文复测）[^18^] |
| **MemoryBank** | 2023-05（arXiv:2305.10250，AAAI 2024） | 长期记忆 + 用户画像 | **Ebbinghaus 遗忘曲线**加权：新近记忆权重大 | 向量库 | 遗忘机制的最早现代实现之一[^25^] |

### 1.3 谱系判断

- 分类学收敛于 CoALA 四分法（working/episodic/semantic/procedural），但 2025-12 的 46 作者大综述 *Memory in the Age of AI Agents*（arXiv:2512.13564）明确指出长短记忆二分法已不够用，提出三维框架：forms（token 级/参数化/隐式）、functions（事实/经验/工作记忆）、dynamics（形成/演化/检索）[^12^][^13^]。
- 架构分化出两条主线：**分层上下文管理（MemGPT/Letta 的虚拟内存派）** 与 **外部记忆服务（Mem0/Zep/Cognee 的记忆层派）**；MemOS/AIOS 代表第三条「OS 内核派」。
- Letta 的 Sarah Wooders 2026 年公开反对「大脑类比」：LLM 是 tokens-in/tokens-out 函数，记忆应围绕「什么进出上下文窗口」设计——与 LangChain 的 Harrison Chase 的「记忆即 harness 留在上下文里的东西」呼应[^13^]。

---

## 2. 关键数据

### 2.1 基准设计

| 基准 | 出处 | 设计 | 规模 | 核心发现 |
|---|---|---|---|---|
| **DMR**（Deep Memory Retrieval） | MemGPT 论文，2023 | Multi-Session Chat 数据集 5 会话 + 第 6 会话提问；单轮事实检索 | 每会话仅 ~60 条消息 | Zep 论文批评其「规模太小、问题歧义、不代表企业场景，现代 LLM 全上下文即可高分」[^2^][^6^] |
| **LoCoMo** | ACL 2024（arXiv:2402.17753） | 10 段多会话对话（19–35 会话、~300 轮、~9K–26K tokens），基于 persona+时序事件图合成、人工校验；QA（single-hop/multi-hop/temporal/open-domain/adversarial）+ 事件摘要 + 多模态生成 | 1,986 QA 对 | 所有方法远低于人类；94% 的问题只需 ≤2 个会话的证据（Memora 论文批评其整合要求浅）[^26^][^27^] |
| **LongMemEval** | ICLR 2025（arXiv:2410.10813，UCLA+Tencent） | 500 题、五能力：信息抽取/多会话推理/时间推理/知识更新/拒答（abstention）；索引-检索-阅读三阶段统一框架；LongMemEval-S ~115K tokens，LongMemEval-M 500 会话 ~1.5M tokens | 500 题 | 商用助手与长上下文 LLM 掉 30–60%；提出 session decomposition、fact-augmented key expansion、time-aware query expansion 三项优化[^28^] |
| **LongMemEval-V2** | 2026-05（arXiv:2605.12493，UCLA） | 从「记住用户」转向「成为环境里的资深同事」：451 题覆盖静态状态回忆/动态状态跟踪/工作流知识/环境陷阱/前提意识；WebArena/WorkArena 轨迹干草堆最大 500 条、115M tokens；评测仅需 Insert(h)/Query(q) 两个 API（context gathering 设定，剥离 planning/tool-use 干扰） | 451 题 | **AgentRunbook-C（把轨迹存成文件、由 coding agent 在沙箱里查证）72.5% > 现成 coding agent 69.3% > 最佳 RAG 48.5%**；GPT-5.2 无历史仅 14.1%[^29^][^30^] |
| **MemBench** | ACL 2025 Findings（arXiv:2506.21605） | factual vs reflective 记忆 × 参与式 vs 观察式；三维指标 effectiveness/efficiency/capacity；噪声扩展至 100K tokens | 8,500 项 | —[^31^] |
| **MemoryAgentBench** | ICLR 2026（Hu et al., 2025） | 增量多轮交互重构长上下文数据集；四能力：accurate retrieval / test-time learning / long-range understanding / **selective forgetting** | — | **当前没有系统能同时掌握四项能力**[^31^][^32^] |
| **MemoryArena** | 2026（arXiv:2602.16313） | 多会话相互依赖的 agentic 任务（web 导航/偏好约束规划/渐进信息搜索/序列形式推理） | — | LoCoMo 上近饱和的模型在此降到 40–60%[^31^] |
| **Memora / FAMA** | ACL 2026 Findings（arXiv:2604.20006） | 数周至数月对话；remembering/reasoning/recommending 三任务；**FAMA 指标惩罚复用已失效记忆**（MPA − λ·(1−FAA)） | 4 LLM × 6 记忆 Agent | **频繁复用无效记忆、无法调和演化中的记忆；记忆 Agent 仅带来边际提升**[^33^] |
| **STALE** | 2026-05（arXiv:2605.06527） | 400 个专家校验冲突场景；隐性冲突（后续观察未显式否定旧记忆但使其失效）；State Resolution/Premise Resistance/Implicit Policy Adaptation | 400 场景 | LLM Agent 难以识别记忆何时失效[^34^] |
| **GroupMemBench** | 2026-05（arXiv:2605.14498） | 多方（multi-party）记忆 | — | **最佳系统平均仅 46.0%；知识更新 27.1%；BM25 即可打平多数记忆系统**——多方记忆本质是治理问题[^35^] |

### 2.2 系统得分（注意：厂商分数互掐严重，务必备注出处与日期）

| 系统 | 基准 | 分数 | 出处/日期 | 备注 |
|---|---|---|---|---|
| MemGPT | DMR | GPT-4: 32.1%→92.5%；GPT-4 Turbo: 35.3%→93.4% | arXiv:2310.08560（2023-10） | 基线收到有损递归摘要，对比的是「摘要 vs 检索」[^6^] |
| Zep | DMR | 94.8%（4-turbo）/ 98.2%（4o-mini） | arXiv:2501.13956（2025-01） | 自报；并自述 DMR 设计缺陷[^2^] |
| Zep | LongMemEval | 63.8%（4o-mini）/ 71.2%（4o），较基线 +18.5%、延迟 −90% | 同上 | 第三方（Vectorize 关联评测）报 Mem0 仅 49.0%——Mem0 对此有异议[^2^][^36^] |
| Mem0 | LoCoMo | 66.88%（论文，2025-04）；92.5（2026-04 新算法，厂商页面） | arXiv:2504.19413；mem0.ai | **同一厂商两个版本差 25 分**；独立复现（Maximem, 2026-05）测得 73.8%，认为 93.4/94.4 系 benchmark 特化 prompt 工程[^3^][^37^][^38^] |
| Mem0 | LongMemEval | 93.4–94.4（厂商，2026-04） vs 49.0%（独立论文 arXiv:2603.04814 用 GPT-5-mini reader） | 同上 | **同名基准相差 45 分**[^36^][^38^] |
| Zep | LoCoMo | Zep 自报 75.14%（修正实现）；Mem0 论文报 65.99%；Mem0 复算 Zep 58.44% | getzep.com blog 2025-05；GitHub getzep/zep-papers#5 | 双方互指对方 harness 有误，属公开争议[^39^][^40^] |
| Letta | LoCoMo | 74.0%（gpt-4o-mini，文件式存储） | Letta 自报，2025–2026 | 主张简单文件存储可与专用检索竞争[^37^] |
| LangMem | LoCoMo | ~58%–78.05%；p95 搜索延迟 ~60s | 第三方汇总 2026；arXiv:2603.19935 复测 78.05% | 延迟使其不适合交互场景[^7^][^18^] |
| Memori | LoCoMo | 81.95%（三轮平均） | arXiv:2603.19935（2026） | 同表：Zep 79.09 / LangMem 78.05 / Mem0 62.47 / 全上下文上限 87.52[^22^] |
| AgentRunbook-C | LongMemEval-V2 | 72.5%（RAG 48.5%、现成 coding agent 69.3%） | arXiv:2605.12493（2026-05） | 「coding-agent 检索 > 向量 RAG」的重要证据[^29^] |
| MINJA 攻击 | 注入成功率 98.2%，最终攻击成功率 76.8% | arXiv:2503.03704（2025-03，NeurIPS 2025） | 仅通过 query 交互即可污染记忆库[^41^] |
| MemoryGraft | 污染检索占比 PRP=47.9%（10 条毒种子 vs 100 条良性） | arXiv:2512.16962（2025-12） | 无触发器、跨会话持久；仅记忆层 tool-gating 能有效缓解[^42^] |

**评测生态总判断（事实）：** 2026 年各方公认「同一个基准在不同 harness 下分数完全不可比」，LoCoMo 的 Mem0↔Zep 之争是标志性案例；第三方评论建议「自己拿 30 条带答案的数据测，比任何公开榜单都可靠」[^38^][^39^][^40^]。

---

## 3. 趋势判断：收敛方向与空白点

### 3.1 收敛方向（有较强证据）

1. **记忆类型词汇收敛于 CoALA 四分法，但其边界在松动。** 所有主流框架文档都用 working/episodic/semantic/procedural；同时 2512.13564 大综述以 forms/functions/dynamics 三维取而代之，程序记忆与非陈述性记忆仍是公认最薄弱象限[^12^][^13^]。
2. **混合检索（向量+BM25+图遍历）+ 时态建模成为准确率前沿的标准配置。** Zep/Graphiti 的双时态边、Mem0g 的 invalid-instead-of-delete、Cognee 的 ECL 管线同向；时序推理与知识更新是纯向量方案的最大短板（第三方评测向量方案在 LongMemEval 时间/更新类目落后图方案约 15 分）[^16^][^36^]。
3. **写入时调和（write-time reconciliation）成为标配。** Mem0 的 ADD/UPDATE/DELETE/NOOP、Zep 的失效时间戳、Memora/STALE 基准的兴起都指向同一结论：遗忘与更新是写入路径的责任，不能只靠检索时过滤[^3^][^33^][^34^]。
4. **异步整合（sleep-time compute / dreams / background consolidation）从论文变成产品默认。** Letta（2025-04）、Anthropic Dreams、Claude Code Auto Dream、OpenClaw dreaming 均已落地；把整合移出用户关键路径、用更强模型做后台整合是共同设计[^9^][^10^][^11^]。
5. **「文件即记忆 + coding agent 检索」成为 2026 年准确率-延迟 Pareto 新前沿。** LongMemEval-V2 的 AgentRunbook-C（72.5% vs RAG 48.5%）与 Letta 的 git 化 Context Repositories、Claude Code 的 MEMORY.md 殊途同归——对复杂证据组装，给 Agent 一个文件系统比给一个向量 API 更强[^29^][^43^]。
6. **评测从「记住用户事实」转向「失效记忆处理」与「环境专长内化」。** FAMA、STALE、GroupMemBench、LME-V2 均诞生于 2026 上半年且结论一致：现有系统在记忆更新/失效/多方场景下接近崩溃，BM25 都能打平[^33^][^34^][^35^]。

### 3.2 空白点

1. **多方/跨 Agent 记忆的治理机制基本空白。** GroupMemBench 显示最好系统仅 46%：实体归属（entity attribution）必须在写入、检索、整合全链路成为一等公民，而现有系统皆不具备[^35^]。传染式越狱可在共享记忆的多 Agent 系统中级联扩散[^44^]。
2. **记忆安全防御远落后于攻击。** MINJA（98.2% 注入成功率）、MemoryGraft（无触发器持久污染）、MemPoison（绕过选择性记忆机制种后门）接连出现；对 6 种防御的评测中「只有记忆层 tool-gating 一致有效」；MemoryGraft 提出的密码学来源证明（CPA）尚无生产实现[^41^][^42^][^45^]。
3. **程序记忆近乎无人区。** 除 LangMem 的 Prompt Optimizer 外无成熟实现；Mem0 的程序路径「只是语义路径加 metadata 标签」，Graphiti 完全没有程序记忆概念[^11^]。
4. **KV/激活态记忆与明文记忆的联动只有 MemOS 一家提出统一抽象**（MemCube 的 Plaintext⇄Activation⇄Parametric 转换），且调度策略由系统内建，没有留给 Agent 的策略接口[^4^]。
5. **驱逐-入库接口无标准化先例。** KV cache 驱逐研究（SnapKV/TOVA/KVP 等）把驱逐视为纯丢弃问题；上下文压缩研究（Context Compaction Theory, arXiv:2608.01326）刚给出形式化，但 Codex/Claude Code 的压缩是「摘要替换历史」而非「摘要入库可检索」——**被驱逐内容变成可检索记忆条目这一接口，现有系统均未提供**[^46^][^47^][^48^]。

### 3.3 「机制/策略分离的 OS 级记忆框架」先例评估（重点）

**结论：有部分先例，但没有完全同构者；我方设计的差异化空间是真实存在的。**

| 先例 | 与我方的重合 | 关键差异 |
|---|---|---|
| **MemOS**（arXiv:2505.22101/2507.03724） | 最强先例：统一记忆单元抽象（MemCube≈inode）、治理属性（ACL/TTL/敏感度标签/访问日志）、生命周期管理、跨 Agent 共享（MemStore）、调度器——几乎逐条对应我方「OS 提供存储/索引/ACL/共享」 | **策略并未下放给 Agent**：MemScheduler 的跨形态转换（plaintext→activation→parametric）由系统的使用频率/成本模型自动驱动，是「OS 即策略」而非「OS 提供机制、Agent 定策略」；且不覆盖「记什么/忘什么」的语义决策[^4^] |
| **AIOS**（arXiv:2403.16971） | 内核模块化 + Access Manager 的 Agent 间访问控制 + Memory/Storage 分离 | 记忆管理器只做短期交互日志 CRUD，无索引/语义层；ACL 停留在论文模块图层面[^20^][^21^] |
| **MemGPT/Letta** | OS 类比的发明者（上下文=RAM、外部存储=disk、自分页） | **方向相反**：Letta 是「LLM 自己做 OS」（策略与机制都在 Agent 内），不是「OS 为 Agent 提供机制」。其 memory pressure 中断 ≈ 我方的驱逐通知，但驱逐决策完全归 Agent，且没有跨 Agent ACL（Letta 的记忆块可跨 Agent 共享，但权限模型弱）[^5^][^7^] |
| **LangGraph BaseStore** | namespace 隔离（user/agent 级）、原语化、策略留给开发者 | namespace 是隔离而非细粒度 ACL；无跨命名空间共享语义[^7^] |
| **Letta Context Repositories**（2026-02） | git 化记忆文件系统：版本、merge、多 Agent worktree——最像「记忆的文件系统」 | 冲突解决靠 git 文本合并，无语义级信念修订；无 ACL[^43^] |
| **GroupMemBench 等 2026 基准** | 反向证据：多方记忆场景下所有系统崩溃，说明「OS 级共享+治理」的需求被独立证实 | —[^35^] |

**判断：** 「机制/策略分离」作为显式设计原则在 Agent 记忆领域尚无同名先例；最接近的是 MemOS（有机制无策略分离）与 Letta（有策略无机制下沉）。我方方案可被定位为「MemOS 的机制面 + MemGPT 的策略面」的组合创新，且 GroupMemBench/记忆投毒文献为其 ACL 与治理组件提供了独立的需求证据。

---

## 4. 对我方架构的启发（逐条）

| # | 我方设计点 | 评估 | 依据 |
|---|---|---|---|
| 1 | OS 提供记忆存储/索引/ACL/跨 Agent 共享，类比 inode | **支持**。MemOS 的 MemCube（元数据头+语义载荷、治理属性、行为指标）证明该抽象可落地且被学界接受；AIOS 的 Access Manager、LangGraph namespace 提供次级先例。差异化在于 ACL 粒度与共享语义，GroupMemBench 的崩盘证明此需求真实且未被满足[^4^][^20^][^35^] | 高置信 |
| 2 | 「记什么、忘什么、何时检索」策略归 Agent | **支持，但需补充**。Letta 证明 Agent 自编辑可行但依赖模型能力（弱模型编辑决策差）；Memora/STALE 证明纯 Agent 策略在失效识别上不可靠。建议 OS 层提供**策略执行护栏**（如写入时矛盾检测 hook、失效时间戳机制——Zep 的 invalidation-instead-of-deletion 可直接借鉴为机制），Agent 保留决策权[^5^][^16^][^33^][^34^] | 高置信 |
| 3 | 有损驱逐接口：KV/上下文被驱逐时摘要入库 | **支持，属真实空白**。KV 驱逐文献只丢不存；生产压缩（Codex/Claude Code）摘要替换历史但不可检索；Context Compaction Theory 证明压缩丢弃的信息从此对 LLM 不可见且 agent 无法自我察觉丢失——「驱逐即入库」恰好补上这个语义断点。需要修订的点：摘要入库必须带来源指针（provenance）回指原始记录（recall/归档），否则派生摘要会成为「事实上的真相」而不可审计[^46^][^47^][^48^][^6^] | 高置信 |
| 4 | 跨 Agent 共享 | **挑战**。共享放大了攻击面：MemoryGraft 证明少量毒经验即可占检索量 47.9% 并跨会话、跨用户持久扩散；传染式越狱在共享记忆多 Agent 系统级联。共享机制必须内置来源证明（CPA 式签名）与记忆层 tool-gating，否则不宜上线[^42^][^44^][^45^] | 高置信 |
| 5 | 索引策略 | **需要修订/补强**。纯向量索引在时序与知识更新类目系统性落后（LongMemEval 上落后图方案约 15 分）；OS 层索引应原生支持：双时态（valid/transaction time）、失效而非删除、混合检索（向量+BM25+图）。这属于机制而非策略，正好归 OS[^16^][^36^] | 高置信 |
| 6 | 遗忘机制 | **需要修订**。不要只做 TTL/衰减（MemoryBank 式 Ebbinghaus 曲线已显单薄）：2026 基准共识是遗忘=写入时调和（ADD/UPDATE/DELETE/NOOP）+ 失效标记 + FAMA 式评测闭环。OS 应提供「失效标记/版本链」原语（MemOS Version Chain、Zep t_expired 均可借鉴），删除策略归 Agent[^3^][^4^][^33^] | 中高置信 |
| 7 | 性能预算 | **需要修订为约束**。交互场景的检索延迟预算约 p95 < 1s（Mem0 0.2s vs LangMem 60s 的差距直接决定可用性）；若 OS 记忆调用走多步 LLM 工具调用（Letta 式），每次查询耗数个顺序 LLM 步骤，token 与延迟显著高于「prompt 组装前一次性检索」的中间件式——接口设计应支持同步快路径 + 异步慢路径（sleep-time 整合）双通道[^18^][^9^] | 高置信 |
| 8 | 评测策略 | **支持并建议**：勿引用厂商 LoCoMo/LongMemEval 分数（Mem0 vs Zep 之争证明同名基准分差可达 45 分）；自建 30–100 条带答案的私有评测集；关注 FAMA/STALE/LME-V2 的失效与拒答维度，而非仅检索准确率[^38^][^39^][^33^][^29^] | 高置信 |

---

## 5. 组件特有输出素材：记忆系统对比表（本维度部分）

| 系统 | 记忆类型划分 | 存储引擎 | 遗忘/更新机制 | 隐私/权限方案 |
|---|---|---|---|---|
| **MemGPT / Letta**（2023/2024） | 分层：core（常驻上下文，persona/human 块）/ recall（全量对话）/ archival（长期事实文档）；2026 起 git 化 Context Repositories | Postgres + pgvector（块、历史、embedding 一体）；git 仓库 | Agent 自编辑（core_memory_append/replace）；memory pressure 通知驱逐；sleep-time 后台整合/失效化矛盾记忆 | 记忆块可跨 Agent 共享；无细粒度 ACL（GitHub 分析明确指出「No scoping/ACL story」）[^5^][^6^] |
| **Mem0**（2025） | 语义为主（抽取事实）；user/session/agent 三作用域；Mem0g 图变体 | 向量库 + Neo4j（Mem0g）+ KV | 写入时 ADD/UPDATE/DELETE/NOOP 调和；Mem0g 冲突边标 invalid 不删除；支持 TTL 与按作用域删除 | 作用域（user/agent/app/run）隔离；删除响应 right-to-be-forgotten[^3^][^7^] |
| **Zep / Graphiti**（2025） | episodic 节点（原始消息）→ 语义实体/事实（双时态边）→ community 摘要 | 时序知识图谱（Neo4j 等）+ 向量/BM25 | invalidation-instead-of-deletion：边带 t_valid/t_invalid/t_created'/t_expired' 四时间戳，时序版本链 | 单调用删除用户全部 threads/artifacts/graph；企业云服务模式（开源版已弃）[^16^][^7^] |
| **LangGraph / LangMem**（2025） | CoALA 全覆盖：semantic（事实/画像）/ episodic（few-shot 示例）/ procedural（Prompt Optimizer 自改系统提示，独有） | 后端无关：LangGraph BaseStore（JSON 文档，namespace+key）/ Postgres / 向量库 | 策略全归开发者（原语 SDK）；后台 store manager 异步整合 | namespace 隔离 user/agent；无内建 ACL/审计[^7^] |
| **Cognee**（2024–26） | 会话记忆（快路径）+ 永久知识图谱；remember/improve/recall/forget 四操作 | 自托管嵌入式栈 SQLite+LanceDB+Kuzu（可选 Neo4j/Neptune） | 反馈环更新边权、删除陈旧信息；forget API | 数据主权卖点：全本地部署；管线含 permissions 步骤；无多租户 ACL 文献[^8^] |
| **MemOS**（2025） | 按形态分：plaintext / activation（KV-cache、隐状态）/ parametric（权重），统一 MemCube 封装 | 三层架构 + MemVault 存储 + MemStore 共享 | MemLifecycle（TTL、频率衰减）；Version Chain 版本控制/回滚；跨形态自动转换（热明文→激活、稳态→参数、冷参数→明文） | **MemGovernance：访问权限、敏感度标签、水印、访问日志**——ACL 最完整的学术先例[^4^] |
| **AIOS**（2024） | Memory Manager（短期交互日志，会话结束清除）/ Storage Manager（长期持久化） | 内核级 CRUD（原子操作、线程安全） | 无显式遗忘机制 | **Access Manager：Agent 间隐私与访问控制策略**（模块级，实现浅）[^20^][^21^] |
| **MIRIX**（2025） | 六分：Core/Episodic/Semantic/Procedural/Resource/Knowledge Vault（逐字敏感信息） | 分层结构化存储；6 Memory Manager + Meta Manager 多 Agent 路由 | 分层 summary/details 组织；Active Retrieval | Knowledge Vault 隔离逐字敏感事实[^23^] |

---

## 6. 证据清单（Claim / Source / URL / Date / Excerpt / Confidence）

[^1^] **Claim:** MemGPT 提出 OS 式分层记忆（main context=RAM，external context=disk），Agent 用函数调用自分页。**Source:** Packer et al., MemGPT, arXiv:2310.08560。**URL:** https://arxiv.org/abs/2310.08560。**Date:** 2023-10。**Excerpt:** "MemGPT … introduced a tiered memory architecture … core memory … recall memory … archival memory … The agent manages its own memory through explicit tool calls"（经 arXiv:2604.12948 转述确认）。**Confidence:** 高。

[^2^] **Claim:** Zep 在 DMR 上 94.8% vs MemGPT 93.4%；LongMemEval 上准确率 +18.5%、延迟 −90%。**Source:** Rasmussen et al., arXiv:2501.13956。**URL:** https://arxiv.org/abs/2501.13956。**Date:** 2025-01-20。**Excerpt:** "In the DMR benchmark … Zep demonstrates superior performance (94.8% vs 93.4%)… accuracy improvements of up to 18.5% while simultaneously reducing response latency by 90%"。**Confidence:** 高（自报，厂商论文）。

[^3^] **Claim:** Mem0 在 LoCoMo 上 LLM-judge 66.88%（全上下文 72.90%），检索 p95 0.200s，总 p95 1.44s vs 全上下文 17.12s，~1.8K vs 26K tokens。**Source:** Chhikara et al., arXiv:2504.19413。**URL:** https://arxiv.org/abs/2504.19413。**Date:** 2025-04-28。**Excerpt:** "Mem0 attains a 91% lower p95 latency and saves more than 90% token cost… 26% relative improvements … over OpenAI"。**Confidence:** 高（数据本身）；分数的代表性中（自报）。

[^4^] **Claim:** MemOS 以 MemCube 统一明文/激活/参数三种记忆，带治理属性（访问权限、TTL、敏感度标签、水印、访问日志）、Version Chain、Policy-Aware Scheduling、MemStore 跨平台共享。**Source:** Li et al., arXiv:2505.22101 / arXiv:2507.03724。**URL:** https://arxiv.org/html/2505.22101v1。**Date:** 2025-05/07。**Excerpt:** "Governance Attributes … access permissions, lifespan policies (e.g., time-to-live or frequency-based decay), priority levels, and compliance mechanisms such as sensitivity tags, watermarking, and access logging"。**Confidence:** 高。

[^5^] **Claim:** Letta 生产化 MemGPT：记忆块存 Postgres/pgvector，Agent 工具调用自编辑，context 将满时收系统通知自行决定驱逐/摘要/归档。**Source:** openaitoolshub Letta teardown; callsphere.ai。**URL:** https://www.openaitoolshub.org/ai-product-research/letta。**Date:** 2026-05-15。**Excerpt:** "Memory tools … are tools the LLM chooses to call — not background processes… Letta uses Postgres (with pgvector) for everything"。**Confidence:** 中高（二手拆解，与论文一致）。

[^6^] **Claim:** MemGPT DMR 结果 GPT-4 32.1%→92.5%、GPT-4 Turbo 35.3%→93.4%；基线收到有损递归摘要，对比实质是「摘要 vs 检索」；Letta 缺 ACL 与更正语义。**Source:** lhl/agentic-memory 分析 + aimemoryworks。**URL:** https://github.com/lhl/agentic-memory/blob/main/ANALYSIS-arxiv-2310.08560-memgpt.md。**Date:** 2026-02-21。**Excerpt:** "No scoping/ACL story: for multi-user or multi-tenant systems, recall/archival stores must be scoped and access-controlled"。**Confidence:** 中高。

[^7^] **Claim:** LangMem 支持 semantic/episodic/procedural 三类，procedural 为独有（Prompt Optimizer 自改提示）；BaseStore namespace 隔离；LoCoMo ~58% 且 p95 搜索延迟 ~60s。**Source:** atlan.com / levelop.dev / past.dev。**URL:** https://atlan.com/know/long-term-memory-langchain-agents/。**Date:** 2026-09-18。**Excerpt:** "LangMem is the only option in this stack where the agent can rewrite its own system prompt based on accumulated experience (procedural memory)"。**Confidence:** 中高。

[^8^] **Claim:** Cognee 为自托管知识图谱记忆（SQLite+LanceDB+Kuzu 嵌入式栈），ECL 六步管线含 permissions 步骤，HotPotQA 0.93 vs RAG 0.4。**Source:** cognee.ai / promptquorum。**URL:** https://www.cognee.ai/cognee-review-2026-graphrag-knowledge-graphs-and-agent-memory。**Date:** 2026-09-28。**Excerpt:** "classify → permissions → chunk → graph-extract → summarise → embed… Cognee's benchmark on HotPotQA multi-hop questions shows a 0.93 correctness score compared to 0.4 for base RAG"。**Confidence:** 中（厂商自测）。

[^9^] **Claim:** Letta sleep-time compute（arXiv:2504.13171）后台 Agent 空闲期整合记忆，~5× test-time compute 降低 / +13–18% 准确率（自报）。**Source:** seekvana / letta.com blog。**URL:** https://seekvana.com/library/agentic-ai/memory-research-memgpt-letta-sleep-time。**Date:** 2026-08-23（报道 2025-04 论文）。**Excerpt:** "roughly a 5x reduction in test-time compute needed for equivalent accuracy … accuracy gains up to 13% on GSM-Symbolic and up to 18% on AIME"。**Confidence:** 中（厂商自报未独立复现）。

[^10^] **Claim:** 异步整合已成产品默认：Anthropic Dreams、Claude Code Auto Dream、OpenClaw dreaming 均受 sleep-time compute 启发。**Source:** brgsk.xyz agent memory anatomy。**URL:** https://brgsk.xyz/agent-memory-anatomy/。**Date:** 2026-05-26。**Excerpt:** "two production examples as of mid-2026: Letta's sleep-time compute … and Anthropic's Dreams — an offline pipeline that … writes a new store with duplicates merged and contradictions resolved"。**Confidence:** 中高。

[^11^] **Claim:** 程序记忆是公认空白：Mem0 的程序路径仅为 metadata 标签，Graphiti 无程序概念，仅 LangMem Prompt Optimizer 为独立机制。**Source:** brgsk.xyz（源头核验声明）。**URL:** https://brgsk.xyz/agent-memory-anatomy/。**Date:** 2026-05-26。**Excerpt:** "the procedural-memory claims are verified at source: LangMem's prompt optimizer is a separate mechanism with no vector-store writes; Mem0's procedural path differs from its semantic path only in a metadata label; Graphiti has no procedural concept at all"。**Confidence:** 中高。

[^12^] **Claim:** CoALA（Sumers et al., Princeton）确立 working/episodic/semantic/procedural 四分法，源自 Soar/ACT-R 与心理学（Tulving/Baddeley/Squire），被 IBM/MongoDB/LangChain/Letta/Mem0 文档采用。**Source:** arXiv:2309.02427；atlan.com。**URL:** https://atlan.com/know/types-of-ai-agent-memory/。**Date:** 2026-09-21（原文 2023）。**Excerpt:** "The CoALA paper (Princeton, 2023) formalised this taxonomy from cognitive science for language model agents… IBM, MongoDB, LangChain, Letta, and Mem0 all use a version of this model"。**Confidence:** 高。

[^13^] **Claim:** 2025-12 大综述（46 作者）宣告长短记忆二分法不足，提出 forms/functions/dynamics 三维；Letta Wooders 反对大脑类比，主张围绕上下文窗口进出设计。**Source:** arXiv:2512.13564；justin3go.com。**URL:** https://arxiv.org/abs/2512.13564。**Date:** 2025-12-15。**Excerpt:** "Traditional taxonomies such as long/short-term memory have proven insufficient… three dominant realizations … token-level, parametric, and latent memory … factual, experiential, and working memory"。**Confidence:** 高。

[^14^] **Claim:** Soar 提供三种长期记忆（语义/情景/程序）并与 LLM 协作的机器人系统已在 2025 年实现。**Source:** arXiv:2508.11759。**URL:** https://arxiv.org/pdf/2508.11759。**Date:** 2025-08。**Excerpt:** "The Soar architecture provides three forms of long-term memory: a semantic memory …, an episodic memory …, and a procedural memory…"。**Confidence:** 高。

[^15^] **Claim:** ACT-R 用激活方程（基频+联想强度）检索陈述性记忆；Soar 自动快照工作记忆到情景记忆；两架构均有「数据/元数据隔离墙」。**Source:** Laird, "An Analysis and Comparison of ACT-R and Soar", arXiv:2201.09305。**URL:** https://arxiv.org/abs/2201.09305。**Date:** 2022-01。**Excerpt:** "One of the most significant architectural principles … the strict separation between agent data and metadata"。**Confidence:** 高。

[^16^] **Claim:** Graphiti 三层组织（episodic 节点/双时态语义实体/community 摘要），边带 4 时间戳，检索=cosine+BM25+图遍历+RRF/MMR 重排。**Source:** arXiv:2603.25097 转述 Zep。**URL:** https://arxiv.org/pdf/2603.25097。**Date:** 2026。**Excerpt:** "Zep tracks four timestamps per edge (t′created, t′expired on the transactional timeline and tvalid, tinvalid on the real-world timeline)"。**Confidence:** 高。

[^17^] **Claim:** Generative Agents 的记忆流按 recency/importance/relevance 检索并周期性反思。**Source:** Park et al., UIST 2023（经 arXiv:2604.12948 转述）。**URL:** https://arxiv.org/pdf/2604.12948。**Date:** 2023。**Excerpt:** "Their retrieval mechanism scores memories by recency, importance, and relevance"。**Confidence:** 高。

[^18^] **Claim:** Mem0 论文延迟分析：Mem0 检索 p50 0.148s/p95 0.200s；LangMem p50 17.99s/p95 59.82s；A-Mem p50 0.668s；Zep 总 p50 1.292s；全上下文总 p95 17.117s。**Source:** arXiv:2504.19413 §4.4。**URL:** https://arxiv.org/pdf/2504.19413v1。**Date:** 2025-04。**Excerpt:** "LangMem exhibits even higher search latencies (p50: 17.99s, p95: 59.82s), rendering it impractical for interactive applications"。**Confidence:** 高（注意为 Mem0 论文复测他人系统）。

[^19^] **Claim:** Mem0 更新阶段将候选事实与 10 条最相似旧记忆比对，LLM 决定 ADD/UPDATE/DELETE/NOOP；Mem0g 冲突标 invalid。**Source:** llms.blog 综述引论文。**URL:** https://www.llms.blog/posts/agent-memory-frameworks-in-production-…。**Date:** 2026-10-19。**Excerpt:** "an update phase compares each candidate fact with the 10 most similar stored memories and has the LLM choose ADD, UPDATE, DELETE or NOOP"。**Confidence:** 高。

[^20^] **Claim:** AIOS 内核含 memory manager（短期交互日志）、storage manager（长期持久化）、access manager（Agent 间隐私与访问控制）。**Source:** Mei et al., arXiv:2403.16971。**URL:** https://arxiv.org/abs/2403.16971。**Date:** 2024-03（COLM 2025）。**Excerpt:** "Access Manager: Enforces privacy and access control policies between agents"。**Confidence:** 高。

[^21^] **Claim:** AIOS memory manager 提供原子 CRUD、元数据同步、线程安全，类比底层指针管理。**Source:** arXiv:2403.16971 v5 附录 A.5。**URL:** https://arxiv.org/html/2403.16971v5。**Date:** 2025-08-12。**Excerpt:** "comprehensive memory access through atomic operations, automatic metadata synchronization, and thread-safe access patterns… functioning similarly to pointer management in low-level programming"。**Confidence:** 高。

[^22^] **Claim:** 独立复测 LoCoMo：Memori 81.95 > Zep 79.09 > LangMem 78.05 > Mem0 62.47；全上下文上限 87.52。**Source:** arXiv:2603.19935（2026）。**URL:** https://arxiv.org/pdf/2603.19935。**Date:** 2026。**Excerpt:** 表格数值如上，"Results for Mem0, Zep, LangMem and Full-context were retrieved from Du et al. [2025]"。**Confidence:** 中高（一方复测）。

[^23^] **Claim:** MIRIX 六种记忆组件（Core/Episodic/Semantic/Procedural/Resource/Knowledge Vault）+ 多 Agent Memory Manager 路由 + Active Retrieval。**Source:** arXiv:2507.07957。**URL:** https://arxiv.org/pdf/2507.07957。**Date:** 2025-07。**Excerpt:** "six memory components: Core Memory, Episodic Memory, Semantic Memory, Procedural Memory, Resource Memory, and the Knowledge Vault… a multi-agent architecture: six Memory Managers… and a Meta Memory Manager"。**Confidence:** 高。

[^24^] **Claim:** 第三方 LoCoMo 分层：MemU/MIRIX/Hindsight 第一梯队（MIRIX multi-hop 83.7%、temporal 88.4%）；Mem0 66.9%、Zep 58–75%、OpenAI Memory 52.9% 第三梯队。**Source:** clude.io/benchmark。**URL:** https://clude.io/benchmark。**Date:** 2026。**Confidence:** 中低（聚合方有自身利益，仅作光谱参考）。

[^25^] **Claim:** MemoryBank 用 Ebbinghaus 遗忘曲线加权新近记忆。**Source:** Zhong et al., arXiv:2305.10250（AAAI 2024）（经 arXiv:2605.14833 转述）。**URL:** https://arxiv.org/abs/2305.10250。**Date:** 2023-05。**Excerpt:** "applying an Ebbinghaus forgetting curve model to weight recent memories more heavily"。**Confidence:** 高。

[^26^] **Claim:** LoCoMo：10 段对话、19–35 会话、~300 轮、~9K tokens，1,986 QA 对，五类目，F1 评分；所有方法远低于人类。**Source:** Maharana et al., ACL 2024, arXiv:2402.17753。**URL:** https://arxiv.org/abs/2402.17753。**Date:** 2024-02。**Excerpt:** "10 conversations with 19-32 sessions each … 1,986 QA pairs across five categories"。**Confidence:** 高。

[^27^] **Claim:** Memora 论文批评 LoCoMo 94% 问题只需 ≤2 会话证据（整合要求浅）。**Source:** alphaxiv 对 arXiv:2604.20006 的综述。**URL:** https://www.alphaxiv.org/abs/2604.20006。**Date:** 2026-04-24。**Excerpt:** "94% of its questions require evidence from two or fewer sessions"。**Confidence:** 中高。

[^28^] **Claim:** LongMemEval：500 题、五能力（抽取/多会话/时间/知识更新/拒答）、115K–1.5M tokens、indexing-retrieval-reading 三阶段框架；商用系统与长上下文 LLM 掉 30–60%。**Source:** Wu et al., ICLR 2025, arXiv:2410.10813。**URL:** https://arxiv.org/abs/2410.10813。**Date:** 2024-10-14。**Excerpt:** "long-context LLMs show a 30%~60% performance drop on LONGMEMEVAL_M, and … state-of-the-art commercial systems only achieved 30%~70% accuracy"。**Confidence:** 高。

[^29^] **Claim:** LongMemEval-V2：451 题、五能力（静态/动态状态、工作流、环境陷阱、前提意识）、最大 500 轨迹/115M tokens；AgentRunbook-C 72.5% > 现成 coding agent 69.3% > 最佳 RAG 48.5%；GPT-5.2 无历史仅 14.1%；评测仅需 Insert/Query 两 API。**Source:** Wu et al., arXiv:2605.12493。**URL:** https://arxiv.org/abs/2605.12493。**Date:** 2026-05-12。**Excerpt:** "AgentRunbook-C reaches 72.5% average accuracy; best RAG baseline 48.5%; off-the-shelf coding agent 69.3%"。**Confidence:** 高。

[^30^] **Claim:** LME-V2 官方 repo 提供公开评测 harness 与 leaderboard（LAFS 指标衡量准确率-延迟前沿提升）。**Source:** github.com/xiaowu0162/LongMemEval-V2。**URL:** https://github.com/xiaowu0162/LongMemEval-V2。**Date:** 2026-05-11。**Confidence:** 高。

[^31^] **Claim:** MemBench（factual/reflective × 参与/观察 × effectiveness/efficiency/capacity）；MemoryAgentBench 四能力含 selective forgetting 且无系统全掌握；MemoryArena 上 LoCoMo 饱和模型降至 40–60%。**Source:** agent-harness-registry/GUIDE.md；博客综述引原论文（arXiv:2506.21605；Hu et al. 2025；arXiv:2602.16313）。**URL:** https://github.com/workain/agent-harness-registry/blob/main/GUIDE.md。**Date:** 2026-07-01。**Confidence:** 中高。

[^32^] **Claim:** MemoryAgentBench（ICLR 2026）"current memory agents fall short of mastering all four"。**Source:** llms.blog 引 Hu et al. 2025。**URL:** https://www.llms.blog/posts/agent-memory-frameworks-in-production-…。**Date:** 2026-10-19。**Confidence:** 中高。

[^33^] **Claim:** Memora/FAMA 惩罚复用失效记忆；6 个记忆 Agent 频繁复用无效记忆、仅有边际提升。**Source:** Uddin et al., ACL 2026 Findings, arXiv:2604.20006。**URL:** https://aclanthology.org/2026.findings-acl.1337/。**Date:** 2026-07（v1 2026-04-21）。**Excerpt:** "Evaluations of four LLMs and six memory agents reveal frequent reuse of invalid memories and failures to reconcile evolving memories. Memory agents offer marginal improvements"。**Confidence:** 高。

[^34^] **Claim:** STALE：400 专家校验冲突场景，考察隐性冲突下记忆失效识别；LLM Agent 难以察觉记忆过期。**Source:** Chao et al., arXiv:2605.06527。**URL:** https://arxiv.org/abs/2605.06527。**Date:** 2026-05-07。**Excerpt:** "STALE, a benchmark of 400 expert-validated conflict scenarios"。**Confidence:** 高。

[^35^] **Claim:** GroupMemBench：多方记忆场景最佳系统仅 46.0% 平均准确率，知识更新 27.1%，BM25 打平多数记忆系统。**Source:** arXiv:2605.14498（经 nemooperans.com 引述）。**URL:** https://nemooperans.com/memory-is-governance。**Date:** 2026-05-27。**Excerpt:** "Best system in the evaluation: 46.0% average accuracy. Knowledge update: 27.1%… BM25 … matches or beats most agent-memory systems"。**Confidence:** 中高（二手引述，建议复核原文）。

[^36^] **Claim:** 独立论文（arXiv:2603.04814）测 Mem0 在 LongMemEval 仅 49.0%（GPT-5-mini reader），与厂商 93.4–94.4 相差 45 分；Zep 论文自报 63.8%/71.2%。**Source:** mnemoverse 汇总。**URL:** https://mnemoverse.com/docs/library/ai-memory-solutions-2026-q3。**Date:** 2026-09-28。**Excerpt:** "An independent paper measured 49.0% on LongMemEval for a Mem0 pipeline with a GPT-5-mini reader (arXiv:2603.04814); Zep's own paper reports 63.8% with gpt-4o-mini and 71.2% with gpt-4o"。**Confidence:** 中高。

[^37^] **Claim:** Mem0 2026-04 新算法自报 LoCoMo 92.5 / LongMemEval 94.4 / BEAM(1M) 64.1，~6.9K tokens/query；Letta 自报 LoCoMo 74.0（gpt-4o-mini 文件式）。**Source:** mem0.ai blog "State of AI Agent Memory 2026"。**URL:** https://mem0.ai/blog/state-of-ai-agent-memory-2026。**Date:** 2026-04-01。**Confidence:** 中（厂商自报）。

[^38^] **Claim:** Maximem 2026-05-27 独立复现：Mem0 在 LongMemEval 实测 73.8%（4-14 后），认为厂商 93.4% 差距来自 benchmark 特化 prompt 工程。**Source:** mnemoverse 引 Maximem reproduction。**URL:** https://mnemoverse.com/docs/library/ai-memory-solutions-2026-q3。**Date:** 2026-09-28。**Excerpt:** "it measured 73.8% for Mem0 on LongMemEval… it attributes the gap to benchmark-specific prompt engineering and dataset-specific equivalence rules"。**Confidence:** 中高。

[^39^] **Claim:** Zep 反驳 Mem0 论文：正确实现下 Zep LoCoMo 75.14%±0.17 vs Mem0g 68.44%；Zep p95 搜索 0.632s。**Source:** getzep.com blog。**URL:** https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/。**Date:** 2025-05-06。**Confidence:** 高（争议一方自述，事实即「存在此争议」）。

[^40^] **Claim:** Mem0 反算 Zep 仅 58.44%（GitHub getzep/zep-papers issue #5）；评论界结论「同一基准不同 harness 分数不可比，别引用厂商分数」。**Source:** Agent-DNA-Transfer EVALUATION.md；developersdigest。**URL:** https://github.com/abhay-codes07/Agent-DNA-Transfer/blob/main/docs/EVALUATION.md。**Date:** 2026-06-17。**Excerpt:** "the same benchmark produces wildly different numbers depending on who runs the scoring… we do not cite vendor LoCoMo scores as evidence of anything"。**Confidence:** 高。

[^41^] **Claim:** MINJA：仅 query 交互即可向记忆库注入恶意记录，注入成功率 98.2%、攻击成功率 76.8%。**Source:** Dong et al., arXiv:2503.03704（NeurIPS 2025）。**URL:** https://arxiv.org/abs/2503.03704。**Date:** 2025-03-05。**Excerpt:** "MINJA achieves a high average success rate of 98.2% for injecting malicious records into the memory, and a high average attack success rate of 76.8%"。**Confidence:** 高。

[^42^] **Claim:** MemoryGraft：无触发器、经良性摄入通道（README）植入毒经验，10 毒种/100 良性下 PRP=47.9%，跨会话持久；提出密码学来源证明（CPA）防御。**Source:** Srivastava & He, arXiv:2512.16962。**URL:** https://arxiv.org/abs/2512.16962。**Date:** 2025-12-18。**Excerpt:** "PRP = 23/48 = 0.479 … nearly half of all retrieved records originated from S_poison, despite poisoned items forming only a small minority"。**Confidence:** 高。

[^43^] **Claim:** Letta Context Repositories（2026-02）为 git 化记忆文件系统，自动版本化、多 Agent worktree 合并；但 git 文本合并无法语义解决信念冲突。**Source:** arXiv:2603.17244 相关工作。**URL:** https://arxiv.org/html/2603.17244v1。**Date:** 2026-02-04。**Excerpt:** "Letta Context Repositories (2026) provide git-backed memory filesystems with automatic versioning and merge-based conflict resolution via multi-agent worktrees"。**Confidence:** 高。

[^44^] **Claim:** 传染式越狱可经共享记忆在多 Agent 系统级联扩散。**Source:** arXiv:2601.05504 相关工作引 Men et al. 2025。**URL:** https://arxiv.org/html/2601.05504v2。**Date:** 2026-01-12。**Excerpt:** "Men et al. (2025) demonstrate contagious jailbreak attacks where malicious instructions spread through shared memory structures… cascading failures across multi-agent systems"。**Confidence:** 中高。

[^45^] **Claim:** 六种防御中仅记忆层 tool-gating 一致阻断持久化记忆攻击。**Source:** arXiv:2605.08442。**URL:** https://arxiv.org/pdf/2605.08442。**Date:** 2026。**Excerpt:** "Of six defenses evaluated, only tool-gating at the memory layer consistently disrupted the attack… Defenses should treat memory recall as a privileged operation"。**Confidence:** 中高。

[^46^] **Claim:** Context Compaction Theory：压缩后被丢弃的信息从此对 LLM 不可见，agent 无法自我察觉丢失；Claude Code 用分层驱逐（先内联压缩再大摘要）。**Source:** arXiv:2608.01326。**URL:** https://arxiv.org/html/2608.01326v1。**Date:** 2026-08-02。**Excerpt:** "information a context compaction discards no longer reaches the LLM in future steps… context compaction has received essentially no formal analysis"。**Confidence:** 高。

[^47^] **Claim:** KV cache 驱逐研究（KVP 等）把驱逐建模为纯选择/丢弃问题，被逐内容不可再被注意。**Source:** arXiv:2602.10238。**URL:** https://arxiv.org/html/2602.10238v1。**Date:** 2026-02-10。**Excerpt:** "Existing eviction or compression methods reduce cost but rely on heuristics… KV eviction / compression … saves memory but is lossy—evicted observations can no longer be attended to"。**Confidence:** 高。

[^48^] **Claim:** Claude Code 在 ~80% 上下文（160K/200K）自动压缩，仅保留最近 10–15 轮全文，早期细节仅存摘要；工程对策是把约束外置为命名 artifact。**Source:** jsmanifest / ileventech（二手，2026-09）。**URL:** https://jsmanifest.com/claude-code-session-compaction-2026。**Date:** 2026-09-16。**Confidence:** 中。

---

### 附：调研方法与局限

- 共执行 34 次独立搜索（web_search），覆盖系统论文、官方文档、GitHub、第三方复测与博客评论；优先采用 arXiv/ACL/ICLR/NeurIPS 一手来源，博客仅作线索与争议记录。
- **主要局限**：(1) 厂商基准分数互相矛盾且多为自报，本文所有分数均标注出处性质；(2) GroupMemBench、MemOS 部分实验数字经二手引述，建议复核原文；(3) Letta 2026 年新产品（Conversations API、Context Repositories）细节主要来自第三方拆解。

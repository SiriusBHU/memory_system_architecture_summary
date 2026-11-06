# 第 4 章 记忆框架与记忆能力

> 本章调研基准日：2026-11-06；覆盖时间范围 2024-01 ～ 2026-11（奠基工作追溯至 2023 年及更早）。
> 引用约定：行内引用 `[^4-N^]` 为本章编号，章末附来源清单。凡厂商自报分数均显式标注，不作为结论性证据。

记忆（Memory）是 AgentOS 四个组件中与「机制/策略分离」命题耦合最深的一个：记忆的存储、索引、访问控制天然类似操作系统资源，而「记什么、忘什么、何时检索」则是典型的 Agent 策略。本章先梳理 2023–2026 年记忆系统的技术谱系（4.1），再以五维矩阵对比六个代表性系统（4.2），继而分析记忆评测基准的设计与三类失效模式（4.3），随后盘点端侧个人语义索引的生态空白（4.4），最后对我方三项立场逐条评审（4.5）。

## 4.1 技术谱系

### 4.1.1 三条架构主线

现代 Agent 记忆的分类学词汇已由 CoALA（Cognitive Architectures for Language Agents，Princeton，2023）统一为工作记忆（working）/情景记忆（episodic）/语义记忆（semantic）/程序记忆（procedural）四分法，并被 IBM、MongoDB、LangChain、Letta、Mem0 等文档普遍采用[^4-1^]。2025-12 发表的 46 作者大综述进一步指出长/短期记忆二分法已不够用，提出 forms（token 级/参数化/隐式）× functions（事实/经验/工作）× dynamics（形成/演化/检索）的三维框架[^4-2^]。在此分类学之上，系统实现分化为表 4-1 所示的三条主线。

表 4-1：Agent 记忆系统的三条架构主线（2023–2026）

| 派别 | 代表系统（年份） | 核心命题 | 关键机制 | 关键量化证据（口径） |
|---|---|---|---|---|
| 虚拟内存自编辑派 | MemGPT（2023-10）[^4-3^]；Letta 产品化（2024 起）[^4-4^] | 上下文窗口=RAM，外部存储=disk，LLM 自主分页 | Agent 经工具调用（core_memory_append/replace、archival_memory_insert/search）自编辑记忆；上下文将满时收到 memory pressure 系统通知后自行决定驱逐/摘要/归档 | DMR 基准：GPT-4 32.1%→92.5%、GPT-4 Turbo 35.3%→93.4%（论文自报；基线为有损递归摘要）[^4-3^] |
| 虚拟内存自编辑派（延展） | Letta sleep-time compute（2025-04）[^4-5^]；Context Repositories（2026-02）[^4-6^] | 记忆整合移出用户关键路径；记忆即文件系统 | 空闲期后台 Agent 改写 core memory、摘要、失效化矛盾记忆；git 化版本化记忆文件、多 Agent worktree 合并 | 厂商自报：同等精度 test-time compute 降约 5×；GSM-Symbolic +13%、AIME +18%（无独立复现）[^4-5^] |
| 外部记忆层派 | Mem0（2025-04）[^4-7^]；Zep/Graphiti（2025-01）[^4-8^]；Cognee（2024–26）[^4-9^]；LangMem（2025）[^4-10^] | 记忆是与模型解耦的外部服务/中间件，读写由管线而非 Agent 自主完成 | Mem0 两阶段 extraction→update（ADD/UPDATE/DELETE/NOOP）；Zep 时序知识图谱双时态边、失效（invalidation）而非删除；Cognee ECL 管线（classify→permissions→chunk→graph-extract→summarise→embed）；LangMem 覆盖 CoALA 三类且程序记忆（Prompt Optimizer 自改系统提示）为独有 | Mem0 论文：检索 p50 0.148s/p95 0.200s，总 p95 1.44s vs 全上下文 17.12s，约 1.8K vs 26K tokens/会话[^4-7^]；Zep 论文：LongMemEval 较全上下文基线 +18.5pt、延迟 −90%（自报）[^4-8^] |
| 内核派（OS 化） | AIOS（2024-03）[^4-11^]；MemOS（2025-05/07）[^4-12^] | 记忆是内核管理的可调度资源，类比文件系统 inode | AIOS：Memory Manager（短期日志）/Storage Manager（长期）分离 + Access Manager（Agent 间访问控制）；MemOS：明文/激活态（KV-cache）/参数态三形态统一封装为 MemCube，元数据头含治理属性（ACL、TTL、敏感度标签、水印、访问日志），MemScheduler 策略感知调度，MemStore 跨平台共享 | MemOS 为 ACL 最完整的学术先例；AIOS 记忆管理器仅短期日志 CRUD，无索引/语义层[^4-11^][^4-12^] |

表 4-1 显示三条主线的分化本质是「记忆控制权归属」的分化：虚拟内存派把策略与机制都放在 Agent 内（Letta 是「LLM 自己做 OS」）；外部记忆层派把机制做成独立服务，但读写策略由管线固化；内核派把机制下沉到系统层，其中 MemOS 与我方立场重合度最高（统一记忆单元抽象、治理属性、生命周期、跨 Agent 共享），但其跨形态调度由系统的频率/成本模型自动驱动，属「OS 即策略」而非「OS 提供机制、Agent 定策略」——这一差异是 4.5 节立场评审的关键依据。需补充两点边界事实：其一，Letta 的记忆块可跨 Agent 共享，但第三方拆解明确指出其「无作用域/ACL 设计」（No scoping/ACL story）[^4-4^]；其二，LangMem 虽实现 CoALA 全覆盖，但 Mem0 论文复测其检索延迟 p50 17.99s/p95 59.82s（复测口径，非 LangChain 自报），交互场景可用性存疑[^4-13^]。

### 4.1.2 记忆压缩与遗忘的五条技术线

「压缩与遗忘」横跨记忆框架与推理引擎两个互不连通的文献群，可梳理为五条线（表 4-2）。

表 4-2：记忆压缩与遗忘的五条技术线

| 技术线 | 代表工作（年份） | 机制 | 关键量化证据 | 驱逐语义 |
|---|---|---|---|---|
| ① 摘要/巩固/遗忘（文本空间，记忆侧） | Generative Agents（2023-04）[^4-14^]；MemoryBank（2023-05）[^4-15^]；递归摘要 Rsum（2023-08）[^4-16^]；Google「Language Models Need Sleep」（2026-06）[^4-17^] | recency/importance/relevance 三因子检索打分 + 周期性反思；Ebbinghaus 遗忘曲线加权；M_i=LLM(S_i, M_{i−1}) 递归摘要；参数级睡眠巩固（低秩专家蒸馏+Dreaming 排练） | Rsum 在 MSC 上记忆 F1 较 MemoryBank +25%[^4-16^]；Google Sleep：SQuAD 48.9 vs 无 Dreaming 35.7（自报）[^4-17^] | 有损归档：被替换内容以摘要形式留存 |
| ② RAG/上下文压缩（文本→潜空间） | RECOMP（2023-10）[^4-18^]；LLMLingua 系列（2023–24）[^4-19^]；ICAE（2023-07）[^4-20^]；MemoRAG（2024-09）[^4-21^]；Cartridges（2025-06）[^4-22^] | 检索后抽取/生成式压缩；困惑度 token 剪枝；LoRA 编码器压成 memory slots；KV 压缩作全局记忆；离线训练小型 KV cache | RECOMP：NQ 上 5% token 仅掉 2 EM[^4-18^]；LongLLMLingua 最高 20× 压缩[^4-19^]；Cartridges：显存 ↓38.6×、吞吐 ↑26.4× 且匹配 ICL[^4-22^] | 压缩为手段，不涉及驱逐生命周期 |
| ③ KV 驱逐（推理侧算法） | H2O/StreamingLLM（2023）；SnapKV（2024-04）[^4-23^]；推理模型 KV 压缩基准（2025-12）[^4-24^] | attention sink+滑窗；累计注意力 heavy-hitter；观察窗投票 | SnapKV：16K 输入生成速度 ↑3.6×、显存效率 ↑8.2×，单卡 380K token[^4-23^]；推理（长 CoT）模型上除 SnapKV-D 外各驱逐策略均显著落后 full cache[^4-24^] | 纯丢弃：被逐内容不可再被注意，miss 代价=重算 |
| ④ KV 分层复用（推理侧系统） | vLLM PagedAttention（2023-09）[^4-25^]；AttentionStore（2024-03）[^4-26^]；Mooncake（2024-06）[^4-27^]；SGLang HiCache（2025-02 起）[^4-28^] | KV 分页；多轮会话 KV 分层落盘复用；KVCache 中心 PD 分离 + CPU/DRAM/SSD/RDMA 分离池；L1 GPU/L2 主机/L3 分布式三层缓存 | AttentionStore：TTFT ↓87%、prefill 吞吐 ↑7.8×、成本 ↓70%[^4-26^]；Mooncake：模拟吞吐最高 +525%、真实负载多承载 75% 请求[^4-27^] | 缓存失效：KV 沿 HBM→DRAM→SSD→远端逐层流动，可字节级精确重建 |
| ⑤ Compaction 系统化（2025–26 新兴） | Anthropic 上下文工程博客（2025-09-29）[^4-29^]；Slipstream（2026-05）[^4-30^]；Parallel Context Compaction（2026-05）[^4-31^]；Governance Decay/ConstraintRot（2026-06）[^4-32^]；Context Compaction Theory（2026-08）[^4-33^] | compaction（摘要并重启）列为四大上下文工程技术之一；异步 compaction + 轨迹 judge 校验；并行分块压缩；约束钉住（Constraint Pinning）；压缩的形式化分析 | Slipstream：SWE-bench Verified/BrowseComp 准确率最高 +8.8pt、端到端延迟 ↓39.7%，88–100% 压缩错误在 3 步内显现[^4-30^]；Governance Decay：compaction 后安全约束违规率 0%→30%（个别模型 59%）[^4-32^] | 有损摘要替换历史，但摘要不可检索、原文不留存 |

表 4-2 揭示一个对本章至关重要的结构性事实：技术线 ③④ 与技术线 ①⑤ 互不连通。推理侧系统（Mooncake/HiCache/AttentionStore）把 KV 驱逐到更慢的同构介质，驱逐语义是「可重算的缓存失效」；记忆侧（MemGPT、Slipstream、Anthropic 工程实践）做的是「上下文满→LLM 摘要→外部存储」，发生在应用层/中间件层，与推理引擎的 KV 驱逐事件完全脱钩。截至 2026-11，没有任何主流 serving 系统把被驱逐 KV 转成文本摘要写入记忆框架，也没有记忆系统把引擎驱逐事件作为入库触发器——「跨越推理引擎与记忆框架的统一驱逐策略」没有顶会/系统论文直接研究（判断，置信度中高；详见 4.5-②）。同时，2026 年 compaction 风险研究集中爆发（验证缺口、约束静默丢失、退化遗忘），社区共识正在形成：摘要入库必须配验证与可恢复机制，不能裸奔[^4-30^][^4-32^][^4-33^]。

## 4.2 记忆系统对比

表 4-3 按「记忆类型划分 × 存储引擎 × 检索策略 × 遗忘机制 × 隐私方案」五维对比六个代表系统（另附 AIOS、MIRIX 两行作为内核派与多 Agent 派的参照）。

表 4-3：主流记忆系统五维对比（截至 2026-11）

| 系统（年份） | 记忆类型划分 | 存储引擎 | 检索策略 | 遗忘/更新机制 | 隐私/权限方案 |
|---|---|---|---|---|---|
| MemGPT / Letta（2023/2024） | 分层虚拟上下文：core（常驻 persona/human 块）/ recall（全量对话）/ archival（长期文档）；2026 起 git 化 Context Repositories | Postgres + pgvector（块、历史、embedding 一体）；git 仓库 | Agent 工具调用自检索（向量+会话搜索）；sleep-time 后台整合 | Agent 自编辑 + memory pressure 驱逐通知 + 后台失效化矛盾记忆 | 记忆块可跨 Agent 共享；无细粒度 ACL[^4-4^][^4-6^] |
| Mem0（2025-04） | 抽取式事实记忆（语义为主）；user/session/agent 三级作用域；Mem0g 图变体 | 向量库 +（Mem0g）Neo4j 图 + KV | 向量相似度取 top-10 候选，LLM 比对决策 | 写入时 ADD/UPDATE/DELETE/NOOP 调和；Mem0g 冲突边标 invalid 不删除；支持 TTL 与按作用域删除 | 作用域（user/agent/app/run）隔离；删除响应被遗忘权[^4-7^] |
| Zep / Graphiti（2025-01） | 三层：episodic 节点（原始消息）→ 语义实体/事实（双时态边）→ community 摘要 | 时序知识图谱（Neo4j 等）+ 向量/BM25 索引 | 混合检索：cosine + BM25 + 图广度遍历，RRF/MMR/cross-encoder 重排 | invalidation-instead-of-deletion：每边四时间戳（事务时 t_created′/t_expired′ + 有效时 t_valid/t_invalid），时序版本链 | 单调用删除用户全部数据；企业云服务模式[^4-8^] |
| LangGraph / LangMem（2025） | CoALA 三分法最完整实现：semantic（事实/画像）/ episodic（few-shot 示例）/ procedural（Prompt Optimizer 自改系统提示，独有） | 后端无关：LangGraph BaseStore（namespace+key JSON 文档）/ Postgres / 向量库 | namespace 限定 + 向量搜索；后台 store manager 异步整合 | 策略全归开发者（原语 SDK）；后台 ReflectionExecutor 异步整合 | namespace 隔离 user/agent；无内建 ACL/审计[^4-10^] |
| Cognee（2024–26） | 会话记忆（快路径）+ 永久知识图谱；remember/improve/recall/forget 四操作 | 自托管嵌入式栈 SQLite + LanceDB + Kuzu（可选 Neo4j/Neptune） | 图+向量混合（ECL 管线产出）；反馈环更新边权 | forget API + 边权衰减 + 删除陈旧信息 | 数据主权卖点（全本地部署）；管线含 permissions 步骤；无多租户 ACL 文献[^4-9^] |
| MemOS（2025-05/07） | 按形态分：明文 / 激活态（KV-cache、隐状态）/ 参数态（权重），统一 MemCube 封装 | 三层架构（Interface/Operation/Infrastructure）+ MemVault + MemStore | MemScheduler 策略感知调度 + 跨形态转换（热明文→激活、稳态→参数、冷参数→明文） | MemLifecycle（TTL、频率衰减）；Version Chain 版本控制/回滚 | MemGovernance：访问权限、TTL、敏感度标签、水印、访问日志——ACL 最完整的学术先例[^4-12^] |
| AIOS（2024-03） | Memory Manager（短期交互日志）/ Storage Manager（长期持久化） | 内核级 CRUD（原子操作、线程安全） | 无索引/语义检索层 | 无显式遗忘机制 | Access Manager：Agent 间隐私与访问控制（模块级，实现浅）[^4-11^] |
| MIRIX（2025-07） | 六分：Core/Episodic/Semantic/Procedural/Resource/Knowledge Vault（逐字敏感信息） | 分层结构化存储；6 Memory Manager + Meta Manager 路由 | Active Retrieval（回答前先生成检索主题） | 分层 summary/details 组织 | Knowledge Vault 隔离逐字敏感事实[^4-34^] |

表 4-3 呈现三点结构性收敛与两点结构性空白。收敛之一：混合检索（向量+BM25+图遍历）与时态建模成为准确率前沿的标准配置——Zep 的双时态边、Mem0g 的 invalid-instead-of-delete、Cognee 的 ECL 管线同向，第三方评测显示纯向量方案在 LongMemEval 的时间推理/知识更新类目落后图方案约 15 分（中等置信，来源为汇总评测）[^4-35^]。收敛之二：写入时调和（write-time reconciliation）成为标配，遗忘与更新被视为写入路径的责任而非检索时过滤。收敛之三：异步整合（sleep-time/background consolidation）从论文变成产品默认。空白之一：隐私/权限一列从「无」（Letta、LangMem）到「学术先例」（MemOS）呈断崖式分布，生产级系统无一具备数据层强制的记忆 ACL。空白之二：KV/激活态记忆与明文记忆的联动只有 MemOS 一家提出统一抽象，且调度策略内建于系统，没有留给 Agent 的策略接口。此外，延迟是可用性的硬约束：Mem0 论文口径下其检索 p95 0.200s，而 LangMem 同口径 p95 达 59.82s，二者相差约 300 倍，直接决定交互场景的选型[^4-7^][^4-13^]。

## 4.3 记忆评测与失效模式

### 4.3.1 基准设计谱系

表 4-4：主要记忆基准的设计与核心发现

| 基准（出处，年份） | 设计 | 规模 | 核心发现 |
|---|---|---|---|
| DMR（MemGPT 论文，2023） | Multi-Session Chat 5 会话 + 第 6 会话提问，单轮事实检索 | 每会话约 60 条消息 | Zep 论文批评其规模太小、问题歧义、现代 LLM 全上下文即可高分[^4-3^][^4-8^] |
| LoCoMo（ACL 2024）[^4-36^] | 10 段多会话对话（19–35 会话、约 300 轮、9K–26K tokens），persona+时序事件图合成、人工校验；QA 五类目 + 事件摘要 | 1,986 QA 对 | 所有方法远低于人类；Memora 论文批评其 94% 问题只需 ≤2 个会话证据，整合要求浅[^4-36^][^4-37^] |
| LongMemEval（ICLR 2025）[^4-38^] | 500 题五能力：信息抽取/多会话推理/时间推理/知识更新/拒答；索引-检索-阅读三阶段统一框架 | 115K tokens（S）～1.5M tokens/500 会话（M） | 商用助手与长上下文 LLM 掉 30–60%[^4-38^] |
| LongMemEval-V2（2026-05）[^4-39^] | 从「记住用户」转向「成为环境里的资深同事」：静态/动态状态、工作流知识、环境陷阱、前提意识；仅需 Insert(h)/Query(q) 两 API | 451 题；轨迹干草堆最大 500 条/115M tokens | AgentRunbook-C（轨迹存文件 + coding agent 沙箱查证）72.5% > 现成 coding agent 69.3% > 最佳 RAG 48.5%；GPT-5.2 无历史仅 14.1%[^4-39^] |
| Memora / FAMA（ACL 2026 Findings）[^4-37^] | 数周至数月对话；remembering/reasoning/recommending 三任务；FAMA 指标惩罚复用已失效记忆（MPA − λ·(1−FAA)） | 4 LLM × 6 记忆 Agent | 频繁复用无效记忆、无法调和演化中的记忆；记忆 Agent 仅带来边际提升[^4-37^] |
| STALE（2026-05）[^4-40^] | 400 个专家校验冲突场景；隐性冲突（后续观察未显式否定旧记忆但使其失效） | 400 场景 | LLM Agent 难以识别记忆何时失效[^4-40^] |
| GroupMemBench（2026-05）[^4-41^] | 多方（multi-party）记忆 | — | 最佳系统平均仅 46.0%；知识更新 27.1%；BM25 即可打平多数记忆系统——多方记忆本质是治理问题[^4-41^] |
| MemoryAgentBench（ICLR 2026）[^4-42^] | 增量多轮交互重构长上下文数据集；四能力含选择性遗忘（selective forgetting） | — | 当前没有系统能同时掌握四项能力（转引口径，中等置信）[^4-42^] |

表 4-4 的演进方向清晰：2024–2025 年的基准（DMR/LoCoMo/LongMemEval）考「记住用户事实」，2026 年上半年的新一代基准（FAMA/STALE/GroupMemBench/LME-V2）一致转向「失效记忆处理」与「环境专长内化」，且结论一致地悲观——现有系统在记忆更新、失效识别、多方场景下接近崩溃。对系统设计者的直接含义有二：其一，「文件即记忆 + coding agent 检索」成为 2026 年准确率-延迟 Pareto 新前沿（AgentRunbook-C 72.5% vs RAG 48.5%），对复杂证据组装，给 Agent 一个文件系统比给一个向量 API 更强[^4-39^]；其二，评测的失效维度（FAMA 的失效记忆惩罚、STALE 的隐性冲突）比检索准确率更能区分系统优劣，应作为自建评测集的设计参照。

### 4.3.2 Conflict Zone：Mem0 vs Zep 评测之争（双边呈现）

记忆评测领域存在 2026 年仍未解决的方法论争议，属「领域真实分歧」，本节双边呈现、不作结论：

- **Mem0 侧**：论文（2025-04）报 LoCoMo LLM-judge 66.88%（全上下文基线 72.90%）[^4-7^]；2026-04 厂商页面报新算法 LoCoMo 92.5、LongMemEval 93.4–94.4[^4-43^]。
- **Zep 侧**：博客（2025-05）称正确实现下 Zep LoCoMo 75.14%±0.17 vs Mem0g 68.44%，并指 Mem0 论文的 Zep 复现（65.99%）有误[^4-44^]；Mem0 方面在 GitHub issue 中反算 Zep 仅 58.44%[^4-45^]。
- **独立复现**：独立论文（arXiv:2603.04814，用 GPT-5-mini reader）测 Mem0 在 LongMemEval 仅 49.0%，与厂商 93.4–94.4 相差 45 分；Maximem（2026-05）复现 Mem0 为 73.8%，将差距归因于 benchmark 特化 prompt 工程（均为转引汇总口径，中高置信）[^4-35^]。
- **评论界共识**：同一基准在不同 harness 下分数完全不可比；「不引用厂商 LoCoMo 分数作为任何事物的证据」「自建 30 条带答案的数据测，比任何公开榜单都可靠」[^4-45^]。

据此，本章不引用任何厂商基准分数作为系统优劣结论；上引数字仅用于说明「同名基准分差可达 45 分」这一评测生态事实。注：交叉验证已标记 AMemBench（arXiv:2609.13767）为疑似虚构来源，本章不予使用。

### 4.3.3 三类失效模式

**（a）遗忘与失效错误。** FAMA 显示 6 个记忆 Agent 频繁复用已失效记忆、无法调和演化中的记忆[^4-37^]；STALE 进一步显示失效识别在隐性冲突（旧记忆未被显式否定但被后续观察架空）下尤为困难[^4-40^]。此类失效的根因是遗忘被错误地放在检索路径：2026 年基准共识是遗忘=写入时调和（ADD/UPDATE/DELETE/NOOP）+ 失效标记 + 评测闭环[^4-7^][^4-37^]。

**（b）检索干扰。** Lost in the Middle（TACL 2024）证明相关信息位于长上下文中段时性能 U 形塌陷[^4-46^]；Chroma 的 Context Rot 报告（2025-07，工业报告非同行评审，中等置信）显示 18 个前沿模型随输入变长性能非均匀劣化、单个干扰项即降性能，LongMemEval 上约 300 token 聚焦输入优于约 113K token 全历史[^4-47^]；GroupMemBench 则给出更尖锐的对照——BM25 即可打平多数记忆系统[^4-41^]。三者共同说明：更多检索结果不等于更好记忆，检索的精确性与干扰控制是独立的质量维度。

**（c）记忆污染（安全失效）。** MINJA（NeurIPS 2025）证明攻击者仅通过 query 交互即可向记忆库注入恶意记录，注入成功率 98.2%、最终攻击成功率 76.8%[^4-48^]；MemoryGraft（2025-12）进一步证明经良性摄入通道（如 README）植入的 10 条毒种子对 100 条良性记录即可占检索量 47.9%（PRP），无触发器、跨会话持久[^4-49^]。防御侧，对 6 种防御的评测显示「只有记忆层 tool-gating 一致有效」——记忆召回应被视为特权操作（中等置信，单篇评测）[^4-50^]。记忆安全防御整体远落后于攻击，且 MemoryGraft 提出的密码学来源证明（CPA）尚无生产实现[^4-49^]。

## 4.4 端侧个人语义索引：空白点清单与差距分析

### 4.4.1 Windows Recall 复盘：全量横向索引的信任成本

Windows Recall 是唯一量产的全量横向个人语义索引（每数秒全屏快照 + OCR + 本地向量库，自然语言检索「见过的一切」），其两年风波是该路线的完整压力测试。时间线（事实层）：2024-05-20 随 Copilot+ PC 发布[^4-51^]；2024-05-22 英国信息专员办公室（ICO）启动问询[^4-52^]；2024-06-04 安全研究者发布 TotalRecall，证明首发版数据库未加密、「全部明文」，现成 infostealer 可秒级拖库[^4-53^]；2024-06 微软三连退（改 opt-in、要求 Windows Hello、延期转入 Insider 测试）；2024-09-27 公布重做架构：VBS Enclave 隔离、密钥 TPM 托管并绑定 Hello ESS、默认过滤密码/信用卡、可卸载、经渗透测试与第三方评审[^4-54^]；2025-04-25 向全部 Copilot+ PC 推送（仍标 preview），距首发近一年[^4-55^]；2025-06-16 EEA 专属更新引入快照导出工具（一次性 32 位导出码）并将新设备默认保留期从无限改为 90 天[^4-56^]；2026-03 研究者发布 TotalRecall Reloaded，称可经 AIXHost.exe 注入再次提取（研究者自述，微软未正式确认细节，中等置信）[^4-57^]。

四点教训：①首发版属「无威胁建模上线」；②重做核心 = opt-in + 生物识别每次验证 + TEE + 内容过滤 + 企业默认关闭，此范式后被全行业沿用；③即便如此 2025–2026 年仍被持续攻破演示，说明全量屏幕索引的攻击面是结构性的；④监管（ICO 问询、GDPR 数据可携带）直接塑造了产品形态（opt-in、EEA 导出、90 天默认保留）。对我方含义：若做统一索引，「采集面宽度」须让位于「可证明的最小化」——敏感过滤、保留期、TEE 证明应作为首发而非补丁。

### 4.4.2 Apple / Google / HarmonyOS 能力边界

**Apple**：个人上下文（personal context）基于邮件/信息/文件/联系人构建端侧语义索引；iOS 18 起第三方 App 可通过 IndexedEntity 协议向 Spotlight 语义索引捐献实体[^4-58^]；WWDC26/iOS 27（2026-09-14）Siri AI 由 System Orchestrator 路由 Spotlight 语义索引 + App Intents + onscreen awareness[^4-59^]。**关键边界：第三方只能「写入/被查询」，不能直接查询全局语义索引，查询入口独占于 Siri/系统**；高频变动数据走 IntentValueQuery 动态查询而非入库[^4-59^]。2026-06-08 Apple 宣布 Siri AI 不在 EU 上线，理由为 DMA 要求向任何 AI 助手开放深层设备访问；Apple 提出的「Trusted System Agent」中介方案被欧委会拒绝——监管正在把「语义索引+深访问」从平台独占资产推向互操作义务对象[^4-60^]。

**Google**：Pixel Screenshots（2024-08）为单模态纵向索引；Magic Cue（2025-08-20，Pixel 10）跨 Gmail/Calendar/Messages/Screenshots 主动联想，端侧 Tensor G5 + Gemini Nano，支持**逐 App 粒度授权**（「可授权日历但不授权信息」）[^4-61^]；Private AI Compute（2025-11-11）以硬件密封云环境 + 远程证明兜底，2026 年起加入设备密钥加密的持久化服务器端记忆[^4-62^]；AppFunctions（Android 16，2026）把 App 变成「端侧 MCP server」向 Gemini 暴露函数——**动作面已开放给 Agent，但记忆/语料面仍未开放**[^4-63^]。

**HarmonyOS**：授权哲学最激进——「从管权限到管数据」，取消 9 类不合理权限、图库/通讯录强制 System Picker、「单次授予、单次访问」[^4-64^]；UDMF 提供跨应用标准化数据通路（含权限与生命周期管理）[^4-65^]；小艺在用户授权下感知 200+ 项系统级数据，本地处理优先、仅结构化结果上云；HPIC（2026-06）端云协同加密获泰尔实验室增强级认证（行业首家，厂商口径）[^4-66^]。**关键边界：UDMF 是数据流转通道而非语义索引，无向量/语义检索层；小艺的记忆与感知服务第一方 Agent**。

### 4.4.3 Picker 式授权先例评估

Picker 范式（独立进程、免权限、逐条授权、单次授予）已在三大移动 OS 普及：iOS PHPicker（iOS 14，2020）[^4-67^]、Android Photo Picker（API 33+，回迁至 Android 4.4）[^4-68^]、HarmonyOS 强制 System Picker[^4-64^]、Google Photos Picker API 取代全库 scope（2025-03 后）[^4-69^]。评估结论：**所有先例均为「用户手动点选条目」的一次性授权，粒度最细的语义授权雏形仅到 Magic Cue 的「逐 App」级；「按语义谓词授权」（如「只授权与出差相关的邮件检索结果」）无任何先例**。但 Picker 的用户心智与监管语言已被教育成熟，把 Picker 从「选照片」升级为「选语义范围」是自然外推，无需从零教育市场。

### 4.4.4 空白确认、差距分析与窗口判断

表 4-5：端侧个人语义索引空白点清单与最接近实现

| # | 空白点 | 现状证据 | 最接近实现与差距 |
|---|---|---|---|
| G1 | 跨应用统一语义索引对第三方 Agent 开放查询 | 四大平台索引全部第一方锁定：Recall 无第三方 API（EEA 手动导出为唯一例外）[^4-56^]；Apple 第三方只捐献不查询[^4-59^]；Magic Cue 只连 Google 自家 App[^4-61^]；小艺 200+ 项数据感知服务自身[^4-66^] | **Apple** 距离最近（统一索引+schema 化贡献+TEE 兜底），但封闭是有意的商业+合规定位；DMA 压力正迫其向「OS 中介层」演进[^4-60^] |
| G2 | 语义级（谓词级）授权：按类别/时间/敏感度/关系授权检索结果 | Picker 只到条目级[^4-67^]；Magic Cue 只到 App 级[^4-61^] | 无实现；HarmonyOS 授权哲学最接近 |
| G3 | 记忆/索引的数据层强制 ACL + provenance + 审计（OS 侧不可绕过） | 仅学术原型：Collaborative Memory 动态二分图（2025-05）[^4-70^]、MemOS MemGovernance[^4-12^]；行业共识「prompt 级控制不算访问控制」（行业博客口径，中等置信）[^4-71^] | MemOS 形式化最完整但无 OS 强制力、无硬件信任根 |
| G4 | 跨 Agent 共享记忆的标准权限模型 | MCP/A2A 只管传输不管记忆治理（中等置信）[^4-72^]；框架级只有命名空间隔离[^4-10^]；GroupMemBench 最佳系统仅 46.0%[^4-41^] | 无实现 |
| G5 | 索引的可验证最小化（TEE 证明+敏感过滤+保留期组合对外可审计） | Recall/PCC/PAC/HPIC 各自部分具备，无一家对第三方出具可编程证明[^4-54^][^4-62^][^4-66^] | Recall 防护清单最完整但无生态接口，且 2026 年仍被攻破演示[^4-57^] |
| G6 | 索引的可携带与退出（导出/迁移/删除标准化） | 仅 Recall EEA 导出码一种雏形，且为合规而非生态[^4-56^] | 无实现 |
| G7 | 旁观者/第三方数据主体保护（always-on 索引拍到他人信息） | EDPB 智能眼镜声明指出该义务（二手整理，中等置信），OS 级索引无一处理[^4-73^] | 无实现 |

表 4-5 支持两个结论。**空白确认（高置信）**：「统一个人语义索引 + 面向任意第三方 Agent 的细粒度语义授权 + 数据层强制的记忆 ACL」三者交集不存在任何实现；每条腿分别有先例（Apple 的索引、HarmonyOS 的授权哲学、MemOS 的 ACL 形式化、Recall 的 TEE 防护清单），但没有任何一方覆盖其中两项以上。组合这四者即是我方组件的完整定义。**窗口判断（中等置信，含推断成分）**：空白期可能只有 12–24 个月——Apple 的语义索引 + App Intents 已把「OS 级索引 + schema 化贡献」产品化，Google AppFunctions 已把动作面开放给 Agent，若 Apple 按 DMA 要求在 EU 落地 Trusted System Agent 式中介，则「第三方助手经 OS 中介访问个人上下文」将在 2027 年前后成为现实。Apple/DMA 路线是最快的填坑者；该空白属「将被填的区」而非无人区，入场时间本身就是战略变量。

## 4.5 趋势判断与对我方立场评审

基于 4.1–4.4 的证据，对我方三项立场逐条评审（表 4-6）。

表 4-6：我方记忆立场评审汇总

| # | 立场 | 评估 | 核心依据 | 修订意见 |
|---|---|---|---|---|
| ① | OS 管机制（存储/索引/ACL/共享），Agent 管策略（记什么/忘什么/何时检索） | **支持，分离空位真实存在**（高置信） | MemOS 有机制无策略分离[^4-12^]；Letta 有策略无机制下沉[^4-3^][^4-4^]；GroupMemBench 崩盘反向证实治理需求[^4-41^] | OS 层须提供策略执行护栏（写入时矛盾检测 hook、失效时间戳机制），数据层 ACL/审计/出处不可绕过 |
| ② | 有损驱逐接口：KV/上下文被驱逐时摘要入库 | **支持，无先例；但必须修订**（空白判断高置信；修订意见基于 2026 失效证据） | KV 驱逐文献只丢不存[^4-23^][^4-26^]；生产压缩摘要替换历史但不可检索[^4-29^]；Context Compaction Theory 证明被丢弃信息对 LLM 永久不可见[^4-33^] | 钉住关键项（Constraint Pinning 类）+ 摘要质量异步校验（judge/轨迹对照）+ 强制治理元数据（provenance/污点标签/ACL/TTL）+ 原文冷存储可恢复窗口 |
| ③ | 跨 Agent 共享 + ACL | **方向被独立证实，但攻击面显著，须内置防御**（高置信） | GroupMemBench 最佳 46.0%、BM25 打平[^4-41^]；MemoryGraft PRP 47.9% 跨会话持久[^4-49^]；仅记忆层 tool-gating 一致有效[^4-50^] | 共享机制必须内置来源证明（CPA 式签名）与记忆层 tool-gating，否则不宜上线 |

**① 机制/策略分离的空位。** 「机制/策略分离」作为显式设计原则在 Agent 记忆领域尚无同名先例。最接近的两端分别是 MemOS（有机制无策略分离：MemScheduler 的跨形态转换由系统频率/成本模型自动驱动，且不覆盖「记什么/忘什么」的语义决策）[^4-12^] 与 MemGPT/Letta（有策略无机制下沉：驱逐决策完全归 Agent，但无跨 Agent ACL）[^4-3^][^4-4^]。我方可定位为「MemOS 的机制面 + MemGPT 的策略面」的组合创新。需加限定：Memora/STALE 证明纯 Agent 策略在失效识别上不可靠[^4-37^][^4-40^]，故 OS 层应把「失效标记/版本链」做成机制原语（Zep 的 invalidation-instead-of-deletion 可直接借鉴），Agent 在授权包络内保留决策权。索引策略同理归机制侧：双时态、失效而非删除、混合检索应原生内建[^4-8^]。

**② 有损驱逐摘要入库：无先例确认与三点修订。** 先例检索结论：KV 驱逐研究（SnapKV/H2O 谱系）把驱逐建模为纯选择/丢弃问题[^4-23^][^4-24^]；KV 分层系统把驱逐视为可重算的缓存失效[^4-26^][^4-27^]；生产压缩（Codex/Claude Code 式 compaction）是「摘要替换历史」而非「摘要入库可检索」[^4-29^]；最接近的系统级工作（Slipstream、Parallel Compaction、Context Recycling）全部停留在文本摘要层且位于引擎之外[^4-30^][^4-31^]。**「被驱逐内容变成可检索记忆条目」这一接口，截至 2026-11 现有系统均未提供（高置信）**；但 2026 年该方向论文密度快速上升，空白窗口预计 1–2 年内被填（中等置信）。三点修订均有直接证据支撑：(a) **钉住关键项**——Governance Decay 证明 compaction 会静默抹除安全约束（违规率 0%→30%，个别模型 59%），Constraint Pinning 可维持 0%[^4-32^]；(b) **异步校验**——Slipstream 证明同步摘要存在结构性验证缺口（压缩器不知道未来需要什么），异步 compaction + 轨迹 judge 校验准确率最高 +8.8pt、88–100% 的压缩错误在 3 步内显现，校验成本可控[^4-30^]；(c) **治理元数据**——跨维度证据（信息丢失、约束丢失、污点持久化在同一条边上汇合）表明驱逐入库记录的本质是治理检查点而非缓存机制，最小 schema 应为 {摘要载荷, provenance 回指原始记录, 污点标签, 被钉住的安全约束, ACL+TTL+敏感度}，不可裁剪；派生摘要若无 provenance 回指，将成为「事实上的真相」而不可审计[^4-32^][^4-49^][^4-12^]。另有两个补强机会：KV 驱逐文献的注意力 heavy-hitter 信号是几乎免费的入库重要性加权来源[^4-23^]；入库后的巩固/去重/矛盾消解应放在睡眠相位（sleep-time compute 范式）避免阻塞关键路径[^4-5^]。

**③ 跨 Agent 共享 ACL：需求与风险同源。** 需求侧证据独立且强：多方记忆场景下所有系统崩溃（最佳 46.0%，知识更新 27.1%），说明「OS 级共享+治理」的需求被基准独立证实[^4-41^]；而生产 OS 的记忆全部为第一方助手私有，学术形式化（Collaborative Memory 动态权限图、MemOS MemGovernance）无 OS 强制力[^4-70^][^4-12^]。风险侧同样明确：共享放大攻击面——MemoryGraft 证明少量毒经验即可占检索量 47.9% 并跨会话、跨用户持久扩散，传染式越狱可在共享记忆的多 Agent 系统中级联（中等置信）[^4-49^][^4-74^]；行业共识「prompt 级控制不算访问控制」，权限必须在数据层强制[^4-71^]。结论：跨 Agent 共享机制必须内置来源证明与记忆层 tool-gating 作为上线前提；实体归属（entity attribution）须在写入、检索、整合全链路成为一等公民。

**本章小结。** 记忆领域 2024–2026 年的收敛（CoALA 词汇、混合检索、写入时调和、异步整合）验证了我方机制面的技术选型；2026 年基准与攻击文献的集中爆发（FAMA/STALE/GroupMemBench/MINJA/MemoryGraft）则把我方三项立场从「设计偏好」升级为「被独立证实的需求」。两个时间窗需要显式管理：端侧语义索引授权（12–24 个月）与驱逐-入库接缝（1–2 年）均为快关闭窗，先发者定义问题。

---

## 本章来源

[^4-1^]: Sumers et al., CoALA: Cognitive Architectures for Language Agents, arXiv:2309.02427（TMLR 2024）, https://arxiv.org/abs/2309.02427, 2023-09
[^4-2^]: Memory in the Age of AI Agents（46 作者大综述）, arXiv:2512.13564, https://arxiv.org/abs/2512.13564, 2025-12-15
[^4-3^]: Packer et al., MemGPT: Towards LLMs as Operating Systems, arXiv:2310.08560, https://arxiv.org/abs/2310.08560, 2023-10-12
[^4-4^]: lhl/agentic-memory 分析（MemGPT/Letta 拆解，含 "No scoping/ACL story"）, https://github.com/lhl/agentic-memory/blob/main/ANALYSIS-arxiv-2310.08560-memgpt.md, 2026-02-21
[^4-5^]: Lin et al. (Letta/UC Berkeley), Sleep-time Compute, arXiv:2504.13171, https://arxiv.org/abs/2504.13171, 2025-04-17
[^4-6^]: Letta Context Repositories 相关工作（git 化记忆文件系统）, arXiv:2603.17244, https://arxiv.org/html/2603.17244v1, 2026-02-04
[^4-7^]: Chhikara et al., Mem0, arXiv:2504.19413（ECAI 2025）, https://arxiv.org/abs/2504.19413, 2025-04-28
[^4-8^]: Rasmussen et al., Zep/Graphiti, arXiv:2501.13956, https://arxiv.org/abs/2501.13956, 2025-01-20
[^4-9^]: Cognee Review 2026（ECL 管线、HotPotQA 0.93 厂商自测）, https://www.cognee.ai/cognee-review-2026-graphrag-knowledge-graphs-and-agent-memory, 2026-09-28
[^4-10^]: Atlan, Long-term Memory for LangChain Agents（LangMem 三类记忆与 BaseStore）, https://atlan.com/know/long-term-memory-langchain-agents/, 2026-09-18
[^4-11^]: Mei et al., AIOS: LLM Agent Operating System, arXiv:2403.16971（COLM 2025）, https://arxiv.org/abs/2403.16971, 2024-03
[^4-12^]: Li et al., MemOS, arXiv:2505.22101 / arXiv:2507.03724, https://arxiv.org/html/2505.22101v1, 2025-05/2025-07
[^4-13^]: Mem0 论文 §4.4 延迟复测（LangMem p50 17.99s/p95 59.82s）, arXiv:2504.19413, https://arxiv.org/pdf/2504.19413v1, 2025-04
[^4-14^]: Park et al., Generative Agents, UIST 2023, arXiv:2304.03442, https://arxiv.org/pdf/2304.03442, 2023-04
[^4-15^]: Zhong et al., MemoryBank, AAAI 2024, arXiv:2305.10250, https://arxiv.org/abs/2305.10250, 2023-05-21
[^4-16^]: Wang et al., Recursively Summarizing Enables Long-Term Dialogue Memory, arXiv:2308.15022, https://arxiv.org/html/2308.15022v3, 2023-08（v3 2025-05）
[^4-17^]: Behrouz, Hashemi, Mirrokni (Google), Language Models Need Sleep, arXiv:2606.03979, https://arxiv.org/abs/2606.03979, 2026-06-02
[^4-18^]: Xu, Shi, Choi, RECOMP, arXiv:2310.04408, https://arxiv.org/abs/2310.04408, 2023-10-06
[^4-19^]: Prompt Compression for LLMs: A Survey（LLMLingua 系列 20×）, arXiv:2410.12388, https://arxiv.org/html/2410.12388v2, 2024-10-17
[^4-20^]: Ge et al., ICAE, ICLR 2024, arXiv:2307.06945, https://arxiv.org/abs/2307.06945, 2023-07
[^4-21^]: Qian et al., MemoRAG, arXiv:2409.05591, https://arxiv.org/abs/2409.05591, 2024-09-09
[^4-22^]: Eyuboglu et al., Cartridges, arXiv:2506.06266, https://arxiv.org/abs/2506.06266, 2025-06-06
[^4-23^]: Li et al., SnapKV, NeurIPS 2024, arXiv:2404.14469, https://arxiv.org/html/2404.14469v2, 2024-04
[^4-24^]: Assessing KV Cache Compression On Reasoning, arXiv:2512.12008, https://arxiv.org/html/2512.12008v1, 2025-12-12
[^4-25^]: Kwon et al., vLLM PagedAttention, SOSP 2023, arXiv:2309.06180, https://arxiv.org/abs/2309.06180, 2023-09
[^4-26^]: Gao et al., AttentionStore, arXiv:2403.19708, https://arxiv.org/html/2403.19708v2, 2024-03
[^4-27^]: Qin et al., Mooncake（Kimi）, FAST 2025, arXiv:2407.00079, https://arxiv.org/abs/2407.00079, 2024-06-24
[^4-28^]: SGLang 官方文档：HiCache 设计, https://docs.sglang.ai/advanced_features/hicache_design.html, 访问于 2026-11-05
[^4-29^]: Anthropic Engineering Blog, Effective Context Engineering for AI Agents, https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents, 2025-09-29
[^4-30^]: Chen et al. (Princeton), Slipstream, arXiv:2605.08580, https://arxiv.org/abs/2605.08580, 2026-05-09
[^4-31^]: Cim et al., Parallel Context Compaction, arXiv:2605.23296, https://arxiv.org/abs/2605.23296, 2026-05-22
[^4-32^]: Chen et al., Governance Decay / ConstraintRot, arXiv:2606.22528, https://arxiv.org/abs/2606.22528, 2026-06-21
[^4-33^]: Context Compaction Theory, arXiv:2608.01326, https://arxiv.org/html/2608.01326v1, 2026-08-02
[^4-34^]: MIRIX, arXiv:2507.07957, https://arxiv.org/pdf/2507.07957, 2025-07
[^4-35^]: mnemoverse 汇总（独立评测：Mem0 LongMemEval 49.0%；Maximem 复现 73.8%；向量方案时序类目落后图方案约 15 分）, https://mnemoverse.com/docs/library/ai-memory-solutions-2026-q3, 2026-09-28
[^4-36^]: Maharana et al., LoCoMo, ACL 2024, arXiv:2402.17753, https://arxiv.org/abs/2402.17753, 2024-02
[^4-37^]: Uddin et al., Memora/FAMA, ACL 2026 Findings, arXiv:2604.20006, https://aclanthology.org/2026.findings-acl.1337/, 2026-07（v1 2026-04-21）
[^4-38^]: Wu et al., LongMemEval, ICLR 2025, arXiv:2410.10813, https://arxiv.org/abs/2410.10813, 2024-10-14
[^4-39^]: Wu et al., LongMemEval-V2, arXiv:2605.12493, https://arxiv.org/abs/2605.12493, 2026-05-12
[^4-40^]: Chao et al., STALE, arXiv:2605.06527, https://arxiv.org/abs/2605.06527, 2026-05-07
[^4-41^]: GroupMemBench, arXiv:2605.14498, https://arxiv.org/abs/2605.14498, 2026-05
[^4-42^]: llms.blog 转引 MemoryAgentBench（Hu et al., ICLR 2026）, https://www.llms.blog/posts/agent-memory-frameworks-in-production-, 2026-10-19
[^4-43^]: Mem0 官方博客, State of AI Agent Memory 2026, https://mem0.ai/blog/state-of-ai-agent-memory-2026, 2026-04-01
[^4-44^]: Zep 官方博客, Lies, Damn Lies, Statistics: Is Mem0 really SOTA in Agent Memory?, https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/, 2025-05-06
[^4-45^]: Agent-DNA-Transfer EVALUATION.md（含 Mem0/Zep 复算争议与"不引用厂商分数"共识）, https://github.com/abhay-codes07/Agent-DNA-Transfer/blob/main/docs/EVALUATION.md, 2026-06-17
[^4-46^]: Liu et al., Lost in the Middle, TACL 2024, arXiv:2307.03172, https://aclanthology.org/2024.tacl-1.9/, 2023-07
[^4-47^]: Hong, Troynikov, Huber, Context Rot（Chroma 技术报告）, https://www.trychroma.com/research/context-rot, 2025-07-14
[^4-48^]: Dong et al., MINJA, NeurIPS 2025, arXiv:2503.03704, https://arxiv.org/abs/2503.03704, 2025-03-05
[^4-49^]: Srivastava & He, MemoryGraft, arXiv:2512.16962, https://arxiv.org/abs/2512.16962, 2025-12-18
[^4-50^]: 记忆攻击防御评测（仅记忆层 tool-gating 一致有效）, arXiv:2605.08442, https://arxiv.org/pdf/2605.08442, 2026
[^4-51^]: Wikipedia: Windows Recall（发布与延期全过程汇编）, https://en.wikipedia.org/wiki/Windows_Recall, 持续更新（2024-05 起）
[^4-52^]: ICO 声明（就 Recall 启动问询）, https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2024/05/statement-in-response-to-microsoft-recall-feature/, 2024-05-22
[^4-53^]: WIRED, TotalRecall 拖库披露, https://www.wired.com/story/total-recall-windows-recall-ai/, 2024-06-04
[^4-54^]: Microsoft Windows Experience Blog, Update on Recall Security and Privacy Architecture, https://blogs.windows.com/windowsexperience/2024/09/27/update-on-recall-security-and-privacy-architecture/, 2024-09-27
[^4-55^]: GeekWire, Microsoft Rolls Out Recall to All Copilot+ PCs, https://www.geekwire.com/2025/microsoft-rolls-out-recall-and-other-ai-features-to-all-copilot-pcs-nearly-a-year-after-unveiling/, 2025-04-25
[^4-56^]: WinBuzzer, Recall EEA 导出工具与 90 天默认保留期, https://winbuzzer.com/2025/06/16/microsofts-windows-recall-feature-gets-export-tool-in-the-eu-amid-ongoing-privacy-concerns-xcxwbn/, 2025-06-16
[^4-57^]: GovInfoSecurity, TotalRecall Reloaded, https://www.govinfosecurity.com/microsoft-recall-again-spills-secrets-a-31083, 2026-03
[^4-58^]: Apple Developer 文档, Making App Entities Available in Spotlight, https://docs.developer.apple.com/tutorials/data/documentation/appintents/making-app-entities-available-in-spotlight.md, 2024 起
[^4-59^]: WWDC26 Session 343 纪要（IndexedEntityQuery/IntentValueQuery）, https://wwdc.ai/2026/343, 2026-06
[^4-60^]: Apple Newsroom, Due to DMA, Siri AI Delayed in EU for iOS 27 and iPadOS 27, https://www.apple.com/newsroom/2026/06/due-to-dma-siri-ai-delayed-in-eu-for-ios-27-and-ipados-27/, 2026-06-08
[^4-61^]: Google 官方博客, Pixel 10 AI Features（Magic Cue）, https://blog.google/products-and-platforms/devices/pixel/google-pixel-10-ai-features-updates/, 2025-08-20
[^4-62^]: 9to5Google, Google Private AI Compute, https://9to5google.com/2025/11/11/google-private-ai-compute-pixel/, 2025-11-11
[^4-63^]: LetsDataScience, Android AppFunctions for Gemini, https://letsdatascience.com/news/google-enables-android-apps-with-appfunctions-for-gemini-8e56077a, 2026-06-08
[^4-64^]: 华为《HarmonyOS NEXT 安全技术白皮书》（星盾、强制 System Picker、取消 9 类权限）, https://consumer.huawei.com/content/dam/huawei-cbg-site/cn/mkt/privacy/privary-new/250610/down/HarmonyOS%20NEXT%E5%AE%89%E5%85%A8%E6%8A%80%E6%9C%AF%E7%99%BD%E7%9A%AE%E4%B9%A6.pdf, 2024-08
[^4-65^]: HarmonyOS 开发者文档镜像, UDMF/DataShare 权限与生命周期管理, https://github.com/liasica/harmonyos-skills/blob/master/harmonyos/references/harmonyos-guides/data-share-overview.md, 2026-09（文档快照）
[^4-66^]: 中国日报（HDC2026）, HPIC 三原则与泰尔增强级认证；小艺 200+ 项数据感知, http://ex.chinadaily.com.cn/exchange/partners/82/rss/channel/cn/columns/sz8srm/stories/WS6a2f7405a310d709c2fb8019.html, 2026-06-15
[^4-67^]: ohmyswift, PHPickerViewController（独立进程、免权限、逐条授权）, https://ohmyswift.com/blog/2020/08/29/replacing-uiimagepickercontroller-with-phpickerviewcontroller/, 2020-08
[^4-68^]: ProAndroidDev, Permissionless Photo Picker on Android, https://proandroiddev.com/permissionless-photo-picker-android-18f2ffce1b62, 2023-05-04
[^4-69^]: MemoryKPR, Google Photos API Deprecation（强制 Picker API）, https://memorykpr.com/blog/google-photos-api-deprecation-what-it-means-for-third-party-apps-and-how-to-prepare/, 2025-10-24
[^4-70^]: Collaborative Memory（动态二分图 ACL 形式化）, arXiv:2505.18279, https://arxiv.org/html/2505.18279v1, 2025-05-23
[^4-71^]: MindStudio, Shared vs Private AI Agent Memory（"Prompt-level access control isn't access control"）, https://www.mindstudio.ai/blog/shared-vs-private-ai-agent-memory-team-access-control, 2026-06-03
[^4-72^]: mnemoverse, Shared Memory for Multi-Agent Systems（A2A 不涉记忆治理）, https://mnemoverse.com/docs/library/shared-memory-for-multi-agent-systems, 2026-06-18
[^4-73^]: Kaamel 整理 EDPB 智能眼镜声明（旁观者告知义务）, https://www.kaamel.com/blog/en-edpb-smart-glasses-responsibility/, 2026-10-14
[^4-74^]: 传染式越狱经共享记忆级联扩散（相关工作引述）, arXiv:2601.05504, https://arxiv.org/html/2601.05504v2, 2026-01-12

# C3a Agent 记忆系统与评测

> 子模块：C3a（记忆 Q1、Q2、Q4、Q6；主责接缝 J1 记忆侧；立场评审 MEM-1、MEM-2、MEM-3）
> 调研日期：2026-11-05。检索基于公开网页，凡未打开原文、仅见摘要或二手转述的数字，已在证据等级和待核实清单中降级标注。
> 术语约定：「记忆」指 Agent 的跨会话语义记忆；KV cache 的内存机制归 C4b，本文只看其作为记忆形态的角色。

---

## §0 摘要

1. 写入决策的主流已从「框架抽取器 + 向量库」转向「Agent 自己读写文件」：Letta 把 LoCoMo 对话放进文件、给 grep 与检索工具，74.0% 超过 Mem0 当时自报的 68.5%（厂商自测，且 Mem0 此后已大改）[E6][E7]；Anthropic 的 memory tool 是客户端文件目录 [E11]；Letta 2026-02 又把记忆块改成 git 管理的文件系统 [E24]。这对 MEM-2（策略归 Agent）是强支持。
2. 基准得分不可横向比较。同一系统在 LoCoMo 上有 58%/75%/84% 三种说法 [E5]；Mem0 自报 2026 新算法 LoCoMo 92.5、LongMemEval 94.4，而 MemoryAgentBench 上旧版 Mem0 总分仅 21.1，低于长上下文 GPT-4o 的 48.8 [E2][E7]。LoCoMo 审计称答案键约 6.4% 有误、评委对故意答错的回答放行率高达约 63%（审计方自身是记忆厂商，证据等级 C）[E10]。
3. 冲突消解（选择性遗忘）是所有范式的公共短板：MemoryAgentBench 的 FactConsolidation 多跳场景所有被测方法不超过约 7%（o4-mini 在 6K 上下文为 80.0%、32K 降到 14.0%）[E2]。「新事实覆盖旧事实」没有任何记忆框架解决，而 OS 层 ACL 与存储抽象对此无能为力。
4. 压缩的量化证据很薄且多为厂商自评：Factory 评测里三种压缩都去掉约 98.6%–99.3% 的 token，但整体质量只有 3.35–3.70（满分 5），文件轨迹维度仅 2.19–2.45 [E12]；JetBrains 发现简单的观察遮蔽（observation masking）成本减半且解决率与 LLM 摘要相当 [E14]。摘要不是免费午餐，且最容易丢的是「碰过哪些文件」这类结构化状态。
5. KV 作为记忆已有强信号但仍是 L1–L2：Cartridges 在其测试上以 38.6 倍更小内存达到上下文内学习（ICL）质量，但需离线自学习训练 [E17]；CacheBlend 将 RAG 的 TTFT 降 2.2–3.3 倍 [E19]；它们都是服务器侧，且绑定模型版本。
6. 「驱逐」与「摘要入库」在文献里仍是两条分离的路径：本次检索未找到把 KV 有损驱逐直接接到长期记忆写入的系统研究；最近的 IndexMem 把被驱逐 KV 压成潜在记忆回灌注意力，不是文本入库 [E26]。J1 在学术上仍是空白，对 MEM-3 是「空白而非反例」。
7. 参数化记忆（Doc-to-LoRA、Text-to-LoRA、Titans）是 L1 论文级，且 D2L 类方法与预训练知识冲突时系统性失败（报告案例准确率 46.4%）[E21]，不适合 OS 托管。
8. 商业助手收敛到「显式保存的记忆 + 聊天历史引用」双层，并开放用户可见可删：ChatGPT 区分 saved memories 与 reference chat history [E27]；Claude 记忆按项目隔离，2025-10 起对 Pro/Max 开放 [E27]；Gemini 2026-03 推出跨助手记忆/聊天导入 [E27]。「记忆格式迁移」第一次出现了产品级需求，但格式是自然语言文本，无标准 schema。
9. 简单文本方案在基准上很强：Mastra 的 Observational Memory 无向量库、无图，GPT-5 mini 上 LongMemEval 94.87%（自测，无独立复现）[E8]。判断：OS 不应绑定任何一种检索结构。
10. 对立场：MEM-1 需修订（OS 提供的是「带来源与版本的文本/文件对象存储 + ACL」，不要预设索引形态）；MEM-2 支持但需补「写入授权」；MEM-3 部分支持（摘要入库用文本最稳，KV 级入库缺证据）。

---

## §1 技术谱系表

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 上下文虚存化 / 自管理记忆 | MemGPT → Letta（memory blocks、sleep-time、Context Repositories） | UC Berkeley → Letta | 2023；Letta 持续更新至 2026-02 [E24] | 让 LLM 通过工具自己换页；2026 年改为 git 管理的文件式记忆块 | L3 | 可直接迁移（本质是文件+工具），注意后台 sleep-time agent 的功耗 |
| 抽取式记忆层 | Mem0（含图记忆；2026-04 新算法 ADD-only 单次抽取）| Mem0 | 论文 2025-04；新算法 2026-04 [E3][E7] | LLM 抽取事实入向量库，检索注入 | L3 | 需改造：抽取需要 LLM 调用，端侧需常驻小模型 |
| 时序知识图谱 | Zep / Graphiti | Zep AI | 2025-01 [E4] | 双时间轴图谱，保留事实有效期，支持时间推理 | L3 | 需改造：图构建依赖 LLM、图库内存占用大（端侧数据待核实）|
| 认知/OS 隐喻框架 | MemOS（MemCube）、MemoryOS（STM/MTM/LPM 三级）、MIRIX（六类记忆）| MemTensor；BAI-LAB；MIRIX | 2025-07 [E28][E22] | 把 OS 的分层/调度隐喻搬到记忆；MIRIX 按 Core/Episodic/Semantic/Procedural/Resource/Knowledge Vault 分管理 Agent | L2–L3 | 需改造：多 Agent 管理器的 LLM 调用开销大（MemoryOS 在一项第三方测量中单轮约 32.4 秒）[E9] |
| 自组织笔记 | A-MEM（Zettelkasten 式互链笔记）| 学术 | 2025-02 [E28] | 记忆自行建立链接和演化 | L1–L2 | 可迁移（文本+嵌入） |
| RL 学习的记忆管理 | Memory-R1（ADD/UPDATE/DELETE/NOOP 策略由 PPO/GRPO 训练）| 学术（ACL 2026 收录，待核实卷号）| 2025-08，v5 2026-01 [E22] | 用 152 对 QA 训练记忆管理器 | L1 | 需改造：训练依赖基准分布，泛化未知 |
| 文件即记忆 | Anthropic memory tool、CLAUDE.md、Manus 文件系统上下文、OpenViking（L0/L1/L2 分层、目录递归检索）、Mastra Observational Memory | Anthropic、Manus、字节火山引擎、Mastra | 2025-07 至 2026 [E11][E15][E30][E8] | 用文件/目录承载记忆，Agent 以读写文件操作管理 | L3（Anthropic/Manus）；L2（OpenViking 自评）| 可直接迁移：本地文件系统即可，OS 可托管 |
| 商业助手记忆 | ChatGPT saved memories + chat history；Claude 项目级记忆；Gemini 记忆与导入 | OpenAI；Anthropic；Google | 2024–2026 [E27] | 用户可见可删的两层记忆 | L4（亿级用户）| 云侧产品，端侧机制不公开 |
| KV 作为记忆 | Cartridges；Memory³；CacheBlend/LMCache | Stanford；上海算法创新院等（Memory³ 机构待核实）；UChicago/LMCache | 2024–2025 [E17][E18][E19] | 把长上下文/知识离线编码为可加载的 KV | L1（Cartridges、Memory³）；L2–L3（LMCache）| 需改造：KV 体积大、绑定模型与量化版本，端侧闪存带宽受限 |
| 检索式注意力 | InfLLM；RetrievalAttention | 清华等；Microsoft | 2024；NeurIPS 2025 [E20] | 对 KV 建索引，仅访问 1–3% 的 KV 达近似全注意力 | L1–L2 | 需改造：论文在 RTX4090 上让 8B 模型处理 128K，手机 DRAM/带宽不足 |
| 参数化记忆 | Text-to-LoRA；Doc-to-LoRA；Titans | Sakana AI；Google Research | 2025–2026 [E21] | 超网络一次前向把文本/文档写成 LoRA；Titans 测试时更新神经记忆 | L1 | 不可迁移（目前）：替代原语为文本记忆 + 提示缓存 |
| 压缩 / 上下文工程 | Anthropic context editing、Factory 锚定摘要、ACON、LLMLingua-2、观察遮蔽 | Anthropic、Factory、Microsoft 等 | 2025-09 至 2026 [E11][E12][E13][E14][E29] | 清除工具结果、结构化摘要、学习压缩准则 | L3（产品）/ L1（ACON，ICML 2026）| 可直接迁移（主要是文本处理）|
| 睡眠时计算 | Sleep-time Compute | Letta + UC Berkeley | 2025-04 [E23] | 空闲时预推理，把结果写回记忆 | L2 | 需改造：端侧要与功耗/热预算绑定，适合充电空闲窗口 |

---

## §2 关键数据

| 指标 | 数值 | 条件（硬件 / 模型 / 负载） | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| LongMemEval 设计 | 500 题，覆盖信息抽取、多会话推理、时间推理、知识更新、拒答五项能力；商业助手与长上下文模型记忆准确率下降约 30% | 论文摘要口径 | [E1] | ICLR 2025 | A |
| MemoryAgentBench 总分（旧版 Mem0）| Mem0 21.1，Cognee 20.6，Zep 24.0，MemGPT 28.3，MIRIX 26.2，对比长上下文 GPT-4o 48.8、Claude-3.7-Sonnet 49.6 | 增量喂入、RAG/商业记忆默认 GPT-4o-mini | [E2] | ICLR 2026（arXiv 2025-07）| A |
| 冲突消解（FC-MH）| 所有方法不超过约 7%；o4-mini 6K 上下文 80.0、32K 上下文 14.0 | FactConsolidation 多跳 | [E2] | 同上 | A |
| Mem0 论文宣称 | p95 延迟降 91%、token 降 90% 以上；LLM 评委指标相对 OpenAI 记忆高 26%；全上下文基线在该指标上最高（约 72.9），90% 节省不含抽取开销 | LoCoMo，GPT-4o-mini | [E3] 及二手分析 | 2025-04 | A（论文宣称）/ C（二手解读）|
| Mem0 新算法自报 | LoCoMo 91.6→92.5（旧 71.4）；LongMemEval 93.4→94.4（旧 67.8）；约 6.8–7.0K token/查询 | 厂商自测，ADD-only 单次抽取 | [E7] | 2026-04，页面更新 2026-05-20 | B |
| Zep 论文 | DMR 94.8%（MemGPT 93.4%）；LongMemEval 最高提升 18.5%；延迟降 90% | 论文摘要 | [E4] | 2025-01 | A（论文宣称，厂商作者）|
| Zep vs Mem0 在 LoCoMo 上的争议 | Zep 自测 75.14%，Mem0 论文中 Zep 为 65.99%，Zep 称正确配置 84%，Mem0 共同创始人复测 58.44% | 二手转述，未核对原帖全部数字 | [E5] 及二手 | 2025 | C |
| Letta 文件系统基线 | LoCoMo 74.0%（GPT-4o-mini，grep/search_files 等文件工具）vs Mem0 图变体自报 68.5% | 厂商自测，Mem0 对比数字存疑 | [E6] | 2025-08-12 | B |
| Mastra OM | LongMemEval 94.87%（GPT-5 mini）；GPT-4o 上 84.23%；平均上下文约 30K token | 厂商自测，无独立复现 | [E8] | 2026 | B |
| LoCoMo 审计 | 1,540 道非对抗题中 99 题答案键有误（约 6.4%），完美系统上限约 93.6%；评委放行故意错误答案约 63% | 审计者为记忆厂商 | [E10] | 2026 | C |
| 基准饱和 | LoCoMo 约 20K token，LongMemEval-S 约 103K token，均被评为易被全上下文覆盖；LongMemEval-M 超 1M token | 启发式估计 | [E9] | 2026-02 | C（预印本）|
| 评委敏感性 | LoCoMo 上 F1 排第一的 Nemori，在三种评委提示下有一种仍第一、另两种被 MAGMA 超过 | 评委 gpt-4o-mini | [E9] | 2026-02 | C |
| 记忆系统开销 | Nemori 构建索引约 7.04M token，SimpleMem 约 1.3M；A-MEM 构建约 15 小时 | LoCoMo，gpt-4o-mini | [E9] | 2026-02 | C |
| Anthropic context editing + memory tool | 相对基线提升 39%（两者合用）、29%（仅 editing）；100 轮网页搜索任务 token 降 84% | 内部评测，基线与指标未定义 | [E11] | 2025-09-29 | B |
| Factory 压缩评测 | 整体 3.70（Factory）/ 3.44（Anthropic）/ 3.35（OpenAI），满分 5；压缩率 98.6%/98.7%/99.3%；文件轨迹维度 2.45/2.33/2.19 | 36,000+ 条生产消息，评委 GPT-5.2 | [E12] | 2025-12 | B（厂商自评）|
| 观察遮蔽 | 成本约减半，Qwen3-Coder 480B 解决率 53.8%→54.8%；观察占 SWE-agent 单轮约 84% token | SWE-agent，SWE-bench Verified | [E14] | 2025-08（NeurIPS DL4C 研讨会）| A（研讨会论文）|
| ACON | 峰值 token 降 26–54%，精度基本保持；压缩器蒸馏后保留 95% 以上精度 | AppWorld、OfficeBench、多目标 QA | [E13] | arXiv 2025-10；ICML 2026 | A |
| LLMLingua-2 | 2–5 倍压缩；MeetingBank QA F1 原文 87.8、压缩后 86.9（二手汇总页）| 提取式压缩 | [E29] | 2024 | A（压缩倍率）/ C（具体 F1）|
| Cartridges | 内存降 38.6 倍、吞吐升 26.4 倍，匹配 ICL；MTOB 有效上下文 128K→484K | 需离线 self-study 训练 | [E17] | 2025-06 | A（arXiv v3；ICML 2025 研讨会）|
| CacheBlend | TTFT 降 2.2–3.3 倍，吞吐升 2.8–5 倍，质量损失可忽略 | RAG，选择性重算少量 token | [E19] | EuroSys 2025 | A |
| RetrievalAttention | 访问 1–3% 数据近似全注意力；RTX4090 上 8B 模型 128K；单 token 解码 0.107 或 0.188 秒（两个版本不一致）| NeurIPS 2025 | [E20] | 2025 | A（数值待核实）|
| Doc-to-LoRA | 单次前向把文档写入 LoRA，needle 测试在超过原生上下文 4 倍的长度近乎满分 | Gemma-2-2b-it | [E21] | 2026-02；ICML 2026 | A |
| Sleep-time compute | 达到同等精度的测试时计算降约 5 倍；多查询摊销后单查询成本降 2.5 倍；可预测性高时收益大 | Stateful GSM-Symbolic / AIME | [E23] | 2025-04 | A |
| 经验遵循缺陷 | 劣质记录会被检索并放大；严格添加+选择性删除平均约 10% 绝对提升 | AgentDriver、EHRAgent、CIC-IoT | [E25] | 2025-05 | A（预印本，C 视作）|

---

## §3 逐问题分析

### Q1 Agent 记忆系统格局与「写入决策由谁做」

**现状。** 2025H2 到 2026 年的格局可以按「谁决定写什么」分成四类：

- **Agent 自己写**：MemGPT/Letta 的 memory blocks 由 LLM 调用工具编辑；2026-02 的 Context Repositories 把块存成 git 仓库里的文件，每个子 Agent 一个隔离 worktree，通过 git 合并解决并发写入 [E24]。Anthropic memory tool 是客户端文件目录，由 Claude 以创建/读取/更新/删除文件操作管理，存储后端由开发者控制 [E11]。Manus 把文件系统当作「无限、持久、可直接操作」的外部记忆，并强调压缩应可逆（丢网页内容、保留 URL）[E15]。
- **框架抽取器写**：Mem0 的 2026-04 新算法把两趟（抽取+ADD/UPDATE/DELETE 协调）改成单趟只 ADD，旧事实保留不删除；最大的 LongMemEval 增益来自把 Agent 侧生成的事实当作一等公民（单会话助手类 +53.6）[E7]。Zep/Graphiti 由框架在摄入时构建双时间轴图谱 [E4]。
- **系统/产品写**：ChatGPT 的 saved memories 由模型判定+用户显式指令触发，另有 reference chat history（二手逆向称是摘要画像，非官方）[E27]；Claude 记忆按项目隔离，需用户开启「从聊天历史生成记忆」[E27]；Gemini 把「过往聊天」改名为「记忆」，2026-03-26 上线记忆/聊天历史导入 [E27]。
- **学习出来的写入策略**：Memory-R1 用 PPO/GRPO 训练记忆管理器选择 ADD/UPDATE/DELETE/NOOP，152 对 QA 即可训练，但绝大多数结果在 LoCoMo 单一分布上 [E22]。

**记忆模型。** 工作/情景/语义/程序的划分各家不一：MemoryOS 为 STM/MTM/LPM 三级（依时间尺度）；MIRIX 为 Core、Episodic、Semantic、Procedural、Resource、Knowledge Vault 六类并各配管理器 [E22][E28]；Letta 是 core memory（常驻）+ archival（检索）+ 文件。程序记忆在产品里的落点是 CLAUDE.md 与 Agent Skills 这类「指令文件」（本库已有 OpenViking 调研，不重复）。

**数据与分歧。**
(1) Letta 的文件系统实验是最有影响力的反例：74.0% 对 68.5%，Letta 自己的解释是「是否记住取决于 Agent 是否知道何时、如何调用检索工具，而非检索机制本身」[E6]。但 Mem0 当时的 68.5% 存在争议（Letta 称无法复现，Mem0 未说明计算过程），且 Mem0 此后重写算法并自报 92.5%，Letta 未重跑 [E6][E7]。
(2) 反过来，MemoryAgentBench 中以 GPT-4o-mini 为主干的商业记忆（Mem0 21.1、Zep 24.0、Cognee 20.6）全面低于长上下文 Agent，MIRIX 换成 GPT-4.1-mini 后从 26.2 升到 37.7 [E2]。两组数据放在一起，唯一稳妥的结论是：**主干模型与评测配置对得分的影响大于记忆架构本身**。
(3) 无向量库的文本方案（Mastra OM，LongMemEval 94.87%，GPT-4o 上则只有 84.23% [E8]）再次说明模型依赖性。

**这说明什么。** 判断：写入决策在实践中几乎全部由「模型 + 记忆工具」完成，要么是 Agent 自己，要么是框架里的另一个模型；没有任何一家把写入决策交给 OS/系统层。MEM-2 与业界方向一致，但这也意味着写入的授权与审计（谁能写什么、来源是什么）才是 OS 层真正有话语权的地方，而不是写入策略本身。

### Q2 记忆评测与失效模式

**基准设计。**
- **LongMemEval**（ICLR 2025）：500 题，五类能力（信息抽取、多会话推理、时间推理、知识更新、拒答），历史长度可扩展 [E1]。S 版约 103K token，M 版超 1M token [E9]。
- **LoCoMo**：约 20K token、35 个会话的长对话问答 [E9]；已知问题是对话较短，全上下文即可覆盖；类别 5（对抗）缺失标准答案，被不同团队以不同方式处理 [E5][E10]。
- **MemoryAgentBench**（ICLR 2026）：把长文本切块增量喂入，四项能力——准确检索（AR）、测试时学习（TTL）、长程理解（LRU）、冲突消解（SF，FactConsolidation 基于 MQuAKE 反事实编辑对）[E2]。设计上最贴近「Agent 边做边记」。
- **其他**：Mem0 自报引用了 BEAM-1M（64.1%）[E7]；DMR（Deep Memory Retrieval，来自 MemGPT）已被 Zep 指出过于简单 [E4]（该评价为二手印象，待核实）。

**得分争议。**
1. 同一系统同一基准多种数字：Zep 在 LoCoMo 上被报告为 58.44%、65.99%、75.14%、84%（评测者不同、时间戳处理不同、类别 5 是否计入不同）[E5]。大部分细节来自二手转述，本文未逐条核对 Zep 与 Mem0 原帖，证据等级仅 C。
2. 评测配置：Mem0 自己的文档承认，LoCoMo、LongMemEval 这类较小基准可被更激进的检索、更大的上下文窗口或前沿模型明显抬高 [E7]。Mem0 研究页声明「若线上发现多个数值，以本页为准」，这是厂商把自己当作数值的最终解释者。
3. 答案键与评委质量：独立审计称 LoCoMo 约 6.4% 答案键错误、评委放行约 63% 的故意错答 [E10]（审计方是竞争厂商，证据等级 C，LoCoMo 作者未见回应）。
4. 基准饱和：Anatomy 论文定义「上下文饱和差」Δ = Score_记忆 − Score_全上下文，指出 LoCoMo、LongMemEval-S 的体量使全上下文基线足以覆盖，记忆系统的真实收益被掩盖；同一论文测得 F1 与评委排名不一致、同一方法换到 3B 主干后分数大幅下降且格式错误率升到 30% [E9]。
5. 成本被忽略：Anatomy 的测量中 MemoryOS 单轮约 32.4 秒，A-MEM 索引构建约 15 小时，Nemori 构建消耗约 7.04M token，而全上下文单轮 1.7 秒 [E9]。

**简单方案的反例。** Letta 文件基线 [E6]；Mastra OM 无向量库得 94.87% [E8]；Manus、Claude Code 的文件式上下文管理。这类证据大多是厂商自评，但方向一致：**检索结构不是瓶颈，写入时的组织方式和 Agent 的检索行为才是。**

**失效模式研究。**
- 冲突/过时事实：MemoryAgentBench 的 FactConsolidation 显示单跳尚可（GPT-4o 60.0），多跳全面崩溃（≤约 7%）[E2]；Mem0 新算法选择「只加不删」，把冲突消解推给检索与读取阶段 [E7]，意味着过时事实在存储中保留。
- 错误传播与误导性回放：Xiong 等发现 Agent 有「经验遵循」倾向，劣质记录会被检索并放大，高输入相似但低输出相似的记录会误导；严格添加加选择性删除平均约 10% 绝对提升 [E25]。
- 长上下文退化：Chroma 的 Context Rot 报告（2025-07）称输入变长后模型可靠性下降，语义相似的干扰项加剧退化，任务难度与长度相互混淆使归因困难（该报告以技术报告形式发布，证据等级 C）[E16]。
- 参数化记忆的冲突失败：D2L 类超网络在文档与预训练知识矛盾时系统性失败，报告案例准确率 46.4% [E21]。
- 记忆投毒归 C3b，不在此展开。

**这说明什么。** 判断：现有基准分不清「记忆架构的收益」和「模型/配置的收益」，选型不能依赖榜单。对 OS 设计而言，应该评测的是 OS 层可以控制的变量（写入来源标注、版本、删除语义、读取延迟与能耗），而不是复刻 LoCoMo 得分。

### Q4 压缩与遗忘

**机制分类。** 摘要（递归/分层）、遮蔽（清除旧观察）、结构化压缩准则（ACON）、提取式 token 压缩（LLMLingua-2）、巩固（睡眠时计算、反思）、遗忘（时间衰减、Heat、TTL、删除）。

**量化数据。**
- Anthropic context editing：自动清除过期的工具调用与结果，100 轮搜索任务中 token 降 84% 并让原本因上下文耗尽失败的流程跑完；合用 memory tool 相对基线 +39%，仅 editing +29%，但基线与指标未定义（B）[E11]。
- JetBrains Research：观察遮蔽成本减半，解决率与 LLM 摘要持平甚至略优（Qwen3-Coder 480B 53.8%→54.8%）；混合策略再降 7%（对遮蔽）和 11%（对摘要）；限于 SWE-agent，OpenHands 仅为初步结果 [E14]。
- ACON：峰值 token 降 26–54%，AppWorld 精度保持，蒸馏压缩器保留 95% 以上精度，且小模型因减少干扰最高提升 46% [E13]。
- Factory：36,000+ 条生产消息，三种方案压缩率都在 98.6%–99.3%，整体分数差 0.26–0.35 分且无显著性检验；文件轨迹最弱（2.19–2.45）[E12]。Factory 称其锚定式（增量合并）摘要优于 Anthropic 的每次全量重生成；评委为 GPT-5.2，且 Factory 自己的方法参赛，故质量排序只能当线索。
- 旁证：Sourcegraph 在 Amp 中放弃「compaction」改用交接机制，理由是反复压缩使跨阶段连续性变差（来自 Morph 等二手汇总，未找到 Sourcegraph 原文，待核实）。
- LLMLingua-2：2–5 倍压缩，MeetingBank QA F1 从 87.8 降到 86.9（二手汇总），说明任务无关的提取式压缩在 2–5 倍内损失可控，但高压缩比（约 15 倍）下无可靠精度数字 [E29]。
- 理论视角：2026-07 的一篇预印本把 KV 驱逐、量化、提示剪枝、Agent 记忆巩固统一为速率-失真问题，指出现有方法多用注意力幅度或新近度判断保留项，会丢掉后续查询需要的信息，并且「重复压缩」几乎无人度量；该文未给出压缩率与精度数据 [E26]。

**遗忘。** 业界实践偏向「不删，靠检索排序淘汰」：Mem0 新算法 ADD-only [E7]；MemoryOS 靠 Heat 与衰减晋升/淘汰（本库已有调研）；Memory-R1 把 DELETE 作为学习动作 [E22]。学术上 [E25] 证明选择性删除有收益，但 [E7] 的工业选择相反，这是真实分歧。

**格式迁移（版本兼容）。** 公开资料显示：Gemini 2026-03 提供「记忆导入」（让用户把其他助手的记忆摘要以文本粘贴）与「聊天历史 ZIP 导入」，不是实时同步 [E27]；没有找到任何跨厂商的记忆 schema 标准（检索范围：厂商博客与论文标题搜索，未覆盖标准组织）。嵌入模型换代会令向量索引整体失效，这一条是推断，未找到公开量化研究，待核实。

**这说明什么。** 判断：编码 Agent 里「清除旧观察」是性价比最高的压缩，LLM 摘要的边际收益不稳定且丢结构化状态；因此 MEM-3 的「摘要入库」应保留指针（文件路径、URL、原始记录引用），做成可逆压缩，与 Manus 的原则一致 [E15]。

### Q6 与推理的耦合

**KV 作为记忆。**
- Memory³ 提出「显式记忆」作为第三种记忆形态（相对隐式参数与工作记忆），2.4B 参数原型声称优于更大模型与 RAG 并保持更快解码，尚无独立复现 [E18]。
- Cartridges：对每个语料离线训练一个小 KV（self-study），匹配 ICL 质量时内存降 38.6 倍、吞吐升 26.4 倍；训练成本需摊销，随语料变化需重训 [E17]。这是目前最强的「KV 即长期记忆」论据，但对话式、频繁更新的个人记忆并不适合离线训练。
- CacheBlend/LMCache：不要求前缀一致的 KV 复用，TTFT 降 2.2–3.3 倍；LMCache 做多层存储（GPU/CPU/磁盘/远程），MLSys 2026 口头报告 [E19]。它们解决的是「已有文本的 KV 复用」，不是「新写入的记忆」。
- 本库已有 prefix cache 笔记：精确前缀匹配、动态内容必须排在静态前缀之后（RoPE 位置烤入 K）。Manus 同样把 KV 命中率视为最重要指标，Claude Sonnet 缓存输入 0.30 美元/百万 token，对比未缓存 3 美元，相差 10 倍 [E15]。
**检索式注意力。** InfLLM（块级记忆单元，CPU 卸载，可扩展至 1,024K）与 RetrievalAttention（ANNS 索引 KV，访问 1–3% 数据）把「记忆」放进注意力内部 [E20]；代价是需要在内存中保留完整 KV 或其索引，手机上不成立。
**参数化记忆。** Text-to-LoRA（单次前向由任务描述生成 LoRA，ICML 2025）、Doc-to-LoRA（把文档内化，ICML 2026，更新延迟低）、Titans（测试时更新神经长期记忆，NeurIPS 2025 收录）[E21]。成熟度 L1，且知识冲突时 D2L 失败 [E21]；删除一条事实无法精确做到（可删除性差）。
**有损驱逐 → 摘要入库的系统研究。** 本次检索没有找到把「KV 有损驱逐」与「长期记忆写入」做成同一条路径的论文：2026 年的相关工作分在两层——KV 层（IndexMem 把驱逐的 KV 压成固定大小潜在记忆并回灌注意力 [E26]；MemDecay 的区域感知驱逐用于 Agent 推理，评测的是事实保留而非入库 [E26]；KV 卸载 [E26]）与 Agent 层（MemGPT 递归摘要之后的 Letta、Mem0 等）。检索范围：一次标准搜索加 arXiv 标题关键词，不能排除遗漏。
**这说明什么。** 判断：KV 适合做「由 OS 管理的缓存」（可丢、可重建），不适合做「系统的记录」（需可解释、可删除、可迁移）。

---

## §4 趋势判断

**正在收敛的方向**
- 文件/文本为基础的记忆：Anthropic、Letta、Manus、OpenViking、Mastra 殊途同归，Agent 用文件工具管理记忆，必要时叠加索引 [E6][E8][E11][E15][E24][E30]。
- 记忆可见、可编辑、按项目/用户作用域隔离：ChatGPT、Claude 均提供查看与删除 [E27]。
- 编码 Agent 的上下文管理优先清除旧观察，其次才是摘要 [E11][E14]。
- 睡眠时/后台整合：Letta 起步，2026-03 起从服务端 agent 转向客户端子 Agent（二手来源，待核实）[E23][E24]。

**公认的空白点**
- 冲突消解与知识更新：MemoryAgentBench 多跳 ≤约 7% [E2]；Mem0 选择只加不删 [E7]。
- 重复压缩的累积损失无人度量 [E26]；压缩评测几乎都是厂商自评 [E12]。
- 记忆格式与跨厂商迁移：只有用户手动导入，无 schema 标准。
- 端侧能耗与延迟：基准几乎不报告端侧数据；Anatomy 的延迟/构建成本数据是 GPU/云侧口径 [E9]。
- KV 驱逐与长期记忆写入的联合研究（J1）。

**仍有分歧的问题**
- 要不要删除：学术上选择性删除有收益 [E25]，Mem0 工业实践选择只加不删 [E7]。
- 图记忆是否值得：Zep 靠图谱获得时间推理优势 [E4]，但 Mastra 文本方案成绩更高 [E8]，且 MemoryAgentBench 上 Zep 并不领先 [E2]。
- 摘要 vs 遮蔽：Factory 主张结构化摘要 [E12]，JetBrains 主张遮蔽 [E14]。
- 参数化/KV 记忆能否走出论文：Cartridges 与 D2L 数据好但训练/适配成本高 [E17][E21]。

---

## §5 立场评审表

| 立场 ID | 判断（支持 / 挑战 / 需修订） | 关键证据 | 最强反方证据 | 修订建议 | 置信度 |
|---|---|---|---|---|---|
| MEM-1：OS 提供记忆的存储、索引、ACL 与跨 Agent 共享，类比 inode | 需修订 | 业界收敛于文件式记忆（Anthropic memory tool 为文件目录 [E11]，Letta 用 git 管理文件 [E24]，Manus [E15]，OpenViking 目录范式 [E30]）；文件系统抽象天然带路径、版本、权限 | Letta 的 git 版本与并发合并、Mem0 的 user/agent/run 作用域都在应用层完成；没有任何一家把记忆 ACL 做进 OS（检索范围：本文所列框架与商业助手；OS 级 ACL 先例归 C3b）；MemoryAgentBench 显示检索结构（RAG、图）并不稳定优于简单方案 [E2] | 把 MEM-1 改为「OS 提供带来源、版本、作用域的记忆对象存储 + 读写 ACL + 审计，索引形态由 Agent/框架决定；OS 可选提供通用嵌入索引服务」；不要把图谱或向量索引写死进 OS 接口 | 中 |
| MEM-2：「记什么、忘什么、何时检索」的策略归 Agent | 支持（补充写入授权）| 写入决策几乎都由 Agent 或框架内模型做（Letta、Anthropic、Mem0、Memory-R1）[E6][E7][E11][E22]；Letta 称「是否记住取决于 Agent 是否知道何时调用检索」[E6] | Mem0/Zep/ChatGPT 由框架或产品抽取，Agent 并不决定；ChatGPT 的历史引用为产品自动完成 [E27]；Memory-R1 指出手写启发式策略不如学习策略（仅 LoCoMo 分布）[E22]；经验遵循研究表明 Agent 自管写入会传播错误，需要质量把关 [E25] | 保留「策略归 Agent」，但 OS 要承担两件策略无关的事：写入来源标注（谁、何时、基于什么输入写入）和写入配额/授权（J4）；遗忘语义分两层——Agent 决定「标记过期」，OS 保证「物理删除可达」 | 中高 |
| MEM-3：KV/上下文被驱逐时摘要入库（有损驱逐接口）| 需修订（部分支持）| Manus 的可逆压缩、Anthropic context editing 把旧工具结果清出上下文 [E11][E15]；速率-失真视角主张统一处理但无数据 [E26]；ACON 在压缩时保留关键状态，峰值 token 降 26–54% [E13] | 未找到把 KV 驱逐接入长期记忆写入的系统研究（J1 空白）；摘要质量不稳定——Factory 文件轨迹仅 2.19–2.45，JetBrains 发现遮蔽与摘要持平 [E12][E14]；Sourcegraph 放弃 compaction（二手）；IndexMem 说明驱逐的「入库形态」可以是潜在向量而非文本 [E26] | 区分两个接口：(a) 上下文层（文本）驱逐 → 文本摘要入库，保留指针与原始引用；(b) KV 层驱逐 → 只允许「丢弃/降精度/换出/重算」，不要把 KV 摘要成文本记忆（KV 无语义边界，无已发表方案）。摘要入库作为可选去向，并且必须可逆（保留原始记录引用）| 中 |

---

## §6 接缝发现

**J1（记忆侧）：KV / 上下文有损驱逐 → 摘要入库。**
- 学术现状：没有找到把两者做成同一条路径的论文；KV 层与 Agent 层各自演进，最接近的是 IndexMem 的潜在记忆回灌和 2026-07 速率-失真综述的统一框架（无数据）[E26]。
- 质量/重算权衡的可用数据：Factory 的压缩率约 98.6%–99.3% 对应 3.35–3.70/5 的质量，文件轨迹最弱 [E12]；观察遮蔽在 SWE-bench 上不输摘要且成本更低 [E14]；ACON 在 26–54% 峰值 token 降幅下精度基本持平 [E13]。CacheBlend 说明「重算少量 token」可以让 KV 复用的质量损失可忽略 [E19]。
- 判断：摘要入库适合「已完成的子任务/工具长输出」，不适合「活跃推理轨迹」；重算（重新 prefill）在命中前缀缓存时便宜，摘要入库的收益主要来自保留跨会话的信息，而非节省内存。具体的 J/GB 与延迟成本模型归 C4b。
- 决策规则草案：驱逐对象为「已决议的子任务输出」→ 写文本摘要+原文指针；为「活跃上下文」→ 优先降精度或换出；为「系统提示/技能前缀」→ 永不摘要（影响前缀缓存命中 [E15]）。

**J4（协同，主责 C3b）。** 本组件相关证据：写入错误会经「经验遵循」传播 [E25]；Mem0 的只加不删使毒记忆不被覆盖 [E7]；因此 ACL 需覆盖写入和删除。

**J7（协同）。** 本组件相关证据：Anatomy 的构建成本测量（Nemori 约 7.04M token、A-MEM 约 15 小时）说明建索引成本可能远高于查询成本，端侧需按充电/空闲窗口调度 [E9]。端侧嵌入模型常驻成本归 C3b。

---

## §7 组件特有输出

### 7.1 记忆系统对比表

「基准得分」均为厂商自报或第三方测量，口径不同，不可直接比较。「共享与 ACL」「隐私方案」中标「待核实」的条目为未在本次检索中找到一手来源。

| 系统 | 记忆类型划分 | 存储引擎 | 写入决策方 | 遗忘机制 | 共享与 ACL | 隐私方案 | 基准得分 |
|---|---|---|---|---|---|---|---|
| MemGPT / Letta | core（常驻块）+ archival + 文件；sleep-time 整合 | 记忆块；2026-02 起 git 文件系统 [E24] | Agent 自己（工具调用）| 压缩摘要；块可编辑/删除 | 共享 memory block（先例，细节待核实）；子 Agent 独立 worktree，git 合并 [E24] | 自托管；无专门隐私方案（待核实）| LoCoMo 74.0%（文件基线，GPT-4o-mini，自测）[E6]；MemoryAgentBench 总分 28.3 [E2] |
| Mem0 | user / agent / run 作用域的事实记忆 + 可选图记忆 | 向量库 + 可选图 | 框架抽取器（2026-04 起单次 ADD-only）[E7] | 新算法不删旧事实；旧版有 UPDATE/DELETE | user/agent/run 作用域（来自本任务背景，官方文档细节待核实）| 云服务/自托管（待核实）| LoCoMo 92.5、LongMemEval 94.4（自报，2026-05）[E7]；旧版 MemoryAgentBench 总分 21.1 [E2] |
| Zep / Graphiti | 情景子图、语义实体子图、社区子图（三层）| 双时间轴知识图谱 [E4] | 框架（摄入时构建）| 事实有效期失效（时间边），非物理删除 | 待核实 | 待核实 | DMR 94.8%、LongMemEval 最高 +18.5%（论文自报）[E4]；LoCoMo 数字存在 58–84% 争议 [E5]；MemoryAgentBench 总分 24.0 [E2] |
| LangGraph / LangMem | 语义/情景/程序（LangMem 文档分类，待核实）| Store（命名空间化键值+向量）| Agent 或后台抽取（待核实）| 待核实 | 命名空间（来自任务背景，待核实）| 待核实 | 未找到公开资料 |
| A-MEM | 互链原子笔记（Zettelkasten）| 嵌入+链接 | Agent 自管（笔记生成与链接演化）[E28] | 链接演化；细节待核实 | 单 Agent，无 | 无 | LoCoMo（论文自报，数值未核对）；第三方测得 F1 0.116、评委约 0.48–0.51 [E9] |
| MemOS | MemCube：明文 / 激活（KV）/ 参数三类记忆 | 抽象存储层，多后端 | 框架调度 [E28] | MemCube 生命周期管理（细节待核实）| 多用户/多 Agent 共享（待核实）| 待核实 | LoCoMo 论文自报：相对 OpenAI 全局记忆总体 +38.97%、时间推理 +159%、token 开销 −60.95%；README 2.0 报 88.83（口径不同）[E28] |
| MemoryOS | STM / MTM / LPM 三级 | 三级分层存储 | 框架（Heat 晋升）| Heat 衰减淘汰 | 单用户 | 本地部署 | LoCoMo 论文自报 F1 +49.11%、BLEU-1 +46.18%（相对基线）；第三方测得评委约 0.55、单轮约 32.4 秒 [E9][E28] |
| MIRIX | 六类记忆 + 元记忆管理器 | 多管理器 | 多 Agent 框架 [E22] | 待核实 | 待核实 | 待核实 | MemoryAgentBench 总分 26.2（GPT-4.1-mini 为 37.7）[E2] |
| Cognee | 图 + 向量混合（官方定位，待核实）| 图库 + 向量库 | 框架 | 待核实 | 待核实 | 待核实 | MemoryAgentBench 总分 20.6 [E2] |
| Memory-R1 | 事实库（Mem0 式）+ RL 学习的管理器与回答 Agent | 沿用外部记忆库 | 学习得到的策略（PPO/GRPO）[E22] | DELETE 为动作之一 | 无 | 无 | LoCoMo 相对增益：v5 称 F1 +28%，早期版本称 30.41→45.02；对 Mem0 的 68.9% 为二手，待核实 [E22] |
| OpenViking | 文件系统范式：L0/L1/L2 分层加载、目录递归检索、自演化会话 | 虚拟文件系统+向量检索 | Agent / 框架会话提交时抽取 | 待核实 | 目录作用域（本库调研）| 自托管 | LoCoMo 80.32%–82.86%（接入不同宿主，自评，本库引述）[E30] |
| Anthropic memory tool | 文件目录（自由结构）| 开发者客户端存储 [E11] | Agent 自己 | Agent 自行删改文件 | 由开发者的存储权限决定 | 数据留在开发者基础设施 | 与 context editing 合用相对基线 +39%（内部评测）[E11] |
| ChatGPT 记忆 | saved memories + reference chat history | 不公开 | 模型+用户指令（saved）；系统（chat history）[E27] | 用户可删；关闭 chat history 后 30 天内删除所学内容；Temporary Chat 不读写 [E27] | 项目/账户级（待核实）| 云端；临时聊天 | 无公开基准 |
| Claude 记忆 | 按项目隔离的用户记忆摘要 | 不公开 | 用户开启后自动从聊天历史生成 [E27] | 用户可查看与编辑；企业管理员可禁用 | 项目隔离 | 云端 | 无公开基准 |
| Gemini 记忆 | 个人上下文 + 过往聊天（现称「记忆」）；2026-03 起可导入 | 不公开 | 系统/用户 [E27] | 用户管理（细节待核实）| 个人账户；EEA/英国/瑞士首发未覆盖 | 云端 | 无公开基准 |
| Mastra Observational Memory | 压缩的「观察」文本（带优先级标记）| 纯文本，无向量/图 | 后台 observer/reflector 模型 [E8] | 反射阶段合并压缩 | 线程/资源级（待核实）| 自托管 | LongMemEval 94.87%（GPT-5 mini），GPT-4o 84.23%（自测）[E8] |

### 7.2 记忆形态选型表

「写入/读取成本」为定性判断（高/中/低），带 [E] 的为有数据支撑，其余为作者推断，标「推断」。

| 形态 | 写入成本 | 读取成本 | 可解释性 | 可删除性 | 是否适合 OS 托管 | 依据 |
|---|---|---|---|---|---|---|
| 文本 / 文件 | 低（直接写；摘要需一次 LLM 调用）| 低到中（grep 或扫描；长文本占用上下文）| 高（人可读，可 diff，git 管理 [E24]）| 高（删文件即可，物理删除可审计）| 适合：对象存储+ACL+版本+审计 | 业界收敛 [E6][E8][E11][E24]；推断：可删除性是 GDPR 类合规的最低成本路径 |
| 向量（嵌入索引）| 中（每条需嵌入；嵌入模型换代需全量重建，推断）| 低（ANN 检索）| 中低（相似度分数不可解释）| 中（需同步删除向量与原文；近似索引的物理删除实现细节依库而异，待核实）| 适合作为 OS 可选通用服务，不宜绑定索引结构 | MemoryAgentBench 中嵌入 RAG 并不优于 BM25（Contriever 29.8、BM25 41.5）[E2] |
| 图（知识图谱）| 高（实体抽取+关系+去重，依赖 LLM；Nemori/A-MEM 的构建成本参考 [E9]）| 中（图遍历+检索）| 高（实体/关系可检视；Zep 保留时间有效期 [E4]）| 中（时序边使「失效」容易，但物理删除要清理关联）| 不宜托管：模式与抽取逻辑与应用强耦合，由框架提供 | Zep 时间推理优势 [E4]；Mastra 文本方案成绩更高 [E8]，图的收益未被稳定证明 |
| KV cache | 高（预填充或离线训练，Cartridges 需 self-study [E17]）| 低（命中时跳过 prefill）；加载受闪存带宽限制 | 低（张量不可读）| 低（无法删除某一事实，只能整块丢弃；绑定模型版本与量化）| 适合作为 OS 管理的缓存（C4b 记账），不适合作为记录系统 | CacheBlend [E19]、Cartridges [E17]、本库前缀缓存笔记；Manus 命中率经济学 [E15] |
| 适配器 / 参数化（LoRA、D2L、Titans）| 中到高（超网络一次前向或训练）| 低（常驻后无检索）；热插拔有延迟（归 C1b/C4b）| 极低 | 极低（无法精确遗忘单条事实）；知识冲突时失败 [E21] | 不适合作为 OS 托管的记忆记录；可作为未来个性化能力，由推理服务管理 | Doc-to-LoRA、Text-to-LoRA、Titans 均为 L1 [E21] |

---

## §8 参考资料与待核实清单

### 参考资料

| 编号 | 标题 | 机构 / 作者 | URL | 日期 |
|---|---|---|---|---|
| E1 | LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory | Di Wu 等（UCLA、Tencent AI Lab）| https://arxiv.org/abs/2410.10813 | 2024-10；ICLR 2025 |
| E2 | Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions（MemoryAgentBench）| Hu, Wang, McAuley（UCSD）| https://arxiv.org/html/2507.05257v2 | 2025-07；ICLR 2026 |
| E3 | Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory | Mem0 | https://arxiv.org/abs/2504.19413 | 2025-04 |
| E4 | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | Rasmussen 等（Zep AI）| https://arxiv.org/abs/2501.13956 | 2025-01 |
| E5 | Lies, Damn Lies, & Statistics: Is Mem0 Really SOTA in Agent Memory?（仅确认存在，本文未打开全文；其中数字经二手转述）| Zep | https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/ | 2025 |
| E6 | Benchmarking AI Agent Memory: Is a Filesystem All You Need? | Letta | https://www.letta.com/blog/benchmarking-ai-agent-memory | 2025-08-12 |
| E7 | Mem0: the token-efficient memory algorithm；Memory Evaluation 文档；研究页 | Mem0 | https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm ；https://docs.mem0.ai/core-concepts/memory-evaluation ；https://mem0.ai/research | 2026-04；页面更新 2026-05-20 |
| E8 | Observational Memory: 95% on LongMemEval | Mastra | https://mastra.ai/research/observational-memory | 2026 |
| E9 | Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of Evaluation and System Limitations | Dongming Jiang 等 | https://arxiv.org/abs/2602.19320 | 2026-02-22 |
| E10 | locomo-audit（LoCoMo 答案键与评委审计）| dial481（Penfield Labs 相关）| https://github.com/dial481/locomo-audit | 2026 |
| E11 | Managing context on the Claude Developer Platform（context editing 与 memory tool）| Anthropic | https://claude.com/blog/context-management | 2025-09-29 |
| E12 | Evaluating Context Compression for AI Agents | Factory | https://factory.com/news/evaluating-compression | 2025-12 |
| E13 | ACON: Optimizing Context Compression for Long-horizon LLM Agents | Minki Kang 等（含 Microsoft）| https://arxiv.org/abs/2510.00615 | 2025-10；ICML 2026 |
| E14 | The Complexity Trap: Simple Observation Masking Is as Efficient as LLM Summarization for Agent Context Management | Lindenbauer 等（JetBrains Research）| https://arxiv.org/abs/2508.21433 | 2025-08 |
| E15 | Context Engineering for AI Agents: Lessons from Building Manus | Yichao Ji / Manus | https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus | 2025-07 |
| E16 | Context Rot: How Increasing Input Tokens Impacts LLM Performance | Hong, Troynikov, Huber（Chroma）| https://research.trychroma.com/context-rot | 2025-07 |
| E17 | Cartridges: Lightweight and general-purpose long context representations via self-study | Stanford（Hazy Research）| https://arxiv.org/abs/2506.06266 | 2025-06 |
| E18 | Memory³: Language Modeling with Explicit Memory | 作者与机构待核实 | https://arxiv.org/abs/2407.01178 | 2024-07 |
| E19 | CacheBlend: Fast LLM Serving for RAG with Cached Knowledge Fusion；LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference | LMCache 团队 | https://arxiv.org/abs/2405.16444 ；https://arxiv.org/abs/2510.09665 | 2024-05（EuroSys 2025）；2025-10（MLSys 2026）|
| E20 | RetrievalAttention；InfLLM | Microsoft 等；清华等 | https://arxiv.org/abs/2409.10516 ；https://arxiv.org/abs/2402.04617 | 2024；NeurIPS 2025 |
| E21 | Text-to-LoRA；Doc-to-LoRA；Titans；后续研究：文档与预训练知识冲突时 D2L 失败 | Sakana AI；Google Research | https://arxiv.org/abs/2506.06105 ；https://arxiv.org/abs/2602.15902 ；https://arxiv.org/abs/2501.00663 ；https://arxiv.org/html/2604.23750v1 | 2025–2026 |
| E22 | Memory-R1；MIRIX: Multi-Agent Memory System for LLM-Based Agents | Sikuan Yan 等；Yu Wang、Xi Chen | https://arxiv.org/abs/2508.19828 ；https://arxiv.org/abs/2507.07957 | 2025-08（v5 2026-01）；2025-07 |
| E23 | Sleep-time Compute: Beyond Inference Scaling at Test-time | Kevin Lin、Charlie Snell 等（Letta、UC Berkeley）| https://arxiv.org/abs/2504.13171 | 2025-04 |
| E24 | Introducing Context Repositories: Git-based Memory for Coding Agents | Letta | https://www.letta.com/blog/context-repositories | 2026-02 |
| E25 | How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior | Xiong 等 | https://arxiv.org/abs/2505.16067 | 2025-05 |
| E26 | What to Keep, What to Forget: A Rate-Distortion View of Memory Compaction；IndexMem；MemDecay；KV Cache Offloading for Context-Intensive Tasks | Colaco、Lahjouji；其他待核实 | https://arxiv.org/abs/2607.08032 ；https://arxiv.org/abs/2605.25475 ；https://arxiv.org/abs/2607.10582 ；https://arxiv.org/abs/2604.08426 | 2026-04 至 2026-07（后三篇仅见检索摘要）|
| E27 | OpenAI Memory FAQ / How does reference saved memories work；Bringing memory to Claude；Gemini 记忆与聊天历史导入 | OpenAI；Anthropic；Google | https://help.openai.com/en/articles/11146739-how-does-reference-saved-memories-work ；https://claude.com/blog/memory ；https://blog.google/innovation-and-ai/products/gemini-app/switch-to-gemini-app/ | 2025-04 至 2026-03 |
| E28 | A-MEM: Agentic Memory for LLM Agents；MemOS: A Memory OS for AI System；MemoryOS 代码库 | 学术；MemTensor；BAI-LAB | https://arxiv.org/abs/2502.12110 ；https://arxiv.org/abs/2507.03724 ；https://github.com/BAI-LAB/MemoryOS | 2025-02；2025-07 |
| E29 | LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression | Microsoft | https://arxiv.org/abs/2403.12968 | 2024-03 |
| E30 | OpenViking 代码仓库与文档 | 火山引擎 | https://github.com/volcengine/OpenViking | 2026（本库已有调研，指标为其自评）|

### 待核实清单

1. Zep 与 Mem0 在 LoCoMo 上 58.44%/65.99%/75.14%/84% 的来源与口径（未打开 Zep 原帖全文，数字经二手转述）。
2. Mem0 对 Letta 文件基线是否有正式回应，以及 Letta 是否用新版 Mem0 重跑。
3. LoCoMo 审计结论（约 6.4% 答案键错误、约 63% 放行率）：审计方为竞争厂商，LoCoMo 原作者无回应；需第三方复核。
4. Mem0 新算法的数字（91.6/93.4 与 92.5/94.4 两组）：同一页面不同时间，且厂商自测；无独立复现。
5. Mastra OM 94.87% 的独立复现；与「Mem0 约 90%、Letta 约 92%」的第三方列表（来源较弱）不要混用。
6. Memory-R1 对 Mem0 的相对增益（68.9% 为二手，v5 称 F1 +28%）、ACL 2026 收录卷号。
7. Memory³ 的机构与作者；RetrievalAttention 单 token 解码 0.107 与 0.188 秒两个版本的差异。
8. Sourcegraph 放弃 compaction 的原始出处（目前仅 Morph 等二手汇总）。
9. Letta sleep-time 在 2026-03 转向客户端子 Agent：仅见 Latent Space 等二手摘要。
10. LangMem、Cognee 的记忆类型、共享/ACL、隐私方案：本次未检索一手文档，对比表中均标待核实。
11. Mem0 的 user/agent/run 作用域、Letta 共享 memory block、LangGraph 命名空间的官方文档细节（任务背景给出，本次未逐条核对；多 Agent 共享权限归 C3b）。
12. MemOS 的 MemCube 遗忘/共享细节；MemoryOS 是否确为 EMNLP 2025（本次未在 ACL Anthology 确认）。
13. 嵌入模型换代导致索引失效的量化研究：未找到。
14. Anatomy 论文剩余约 2 万字符未读（含可能的 LongMemEval 结果）。
15. IndexMem、MemDecay、KV Offloading 三篇仅见检索摘要，未打开全文；速率-失真综述未给出压缩率-精度数据。
16. 端侧（手机）上的记忆系统功耗与延迟：本次检索未找到公开实测，所有延迟数据均为服务器/云侧口径。
17. 国内手机厂商、Apple、HarmonyOS 的 Agent 记忆形态：不在 C3a 范围，由 C3b 负责。

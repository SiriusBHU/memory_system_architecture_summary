# AgentOS 调研 · 记忆框架维度 C：记忆压缩与遗忘 + 与推理（KV/上下文）的耦合

- 调研日期：2026-11-06；覆盖 2024-01 ~ 2026-11 为主，奠基工作标注年份。
- 聚焦问题：(1) 上下文摘要 / 记忆巩固 / 遗忘策略的研究进展及 RAG 上下文压缩谱系；(2) KV cache 与长期记忆的边界，"有损驱逐、摘要入库"是否有系统研究；MemGPT 谱系后续；LLM 记忆 × KV 复用/前缀缓存的系统论文。
- 方法：32+ 次独立检索 + 多篇原文摘要/正文核验（arXiv HTML/abs、官方文档）。事实与判断分开标注。

---

## 1. 技术谱系表

### 1.A 文本空间：摘要、巩固、遗忘（记忆框架侧）

| 工作 | 时间/出处 | 类别 | 核心机制 | 关键数字 |
|---|---|---|---|---|
| Generative Agents | 2023-04, UIST'23 奠基 | 检索+遗忘+巩固 | 记忆流；检索分数 = Recency(0.995/小时指数衰减)+Importance(LLM 打 1–10)+Relevance(余弦)；重要性阈值触发 Reflection 写回高层洞察 [^3^] | 25 个 agent 沙盘 |
| MemoryBank | 2023-05, AAAI'24 奠基 | 遗忘曲线+摘要 | Ebbinghaus 遗忘曲线 R=e^(−t/S)，召回强化 S；对话→日摘要→全局摘要的分层摘要 [^4^] | — |
| MemoChat / Think-in-Memory | 2023 | 会话摘要 | 静态 memo 摘要；"先回忆后反思"两段式 [^7^] | — |
| MemGPT | 2023-10, arXiv 奠基 | 虚拟内存 | 上下文=物理内存，外部存储=磁盘；LLM 收到 token 水位警报后自主分页/驱逐到外部 [^1^] | — |
| Recursively Summarizing (Rsum) | 2023-08（v4 至 2025） | 递归摘要 | M_i = LLM(S_i, M_{i−1})，旧摘要+新会话递归更新；与长窗口/检索互补 [^35^] | MSC 上记忆 F1 较 MemoryBank +25% |
| LongMemEval / LoCoMo | 2024-02, ACL'24 | 评测 | 超长对话记忆基准，成为后续记忆论文标配 [^40^] | — |
| Mem0 | 2025-04 | 提取-巩固 | 两阶段：提取显著事实→ADD/UPDATE/DELETE/NOOP 决策 [^41^] | LoCOMO 上较 OpenAI 内置记忆 +26%，p95 延迟 −91%，token 成本 −90%+（厂商自报） |
| RMM (Reflective Memory Mgmt) | 2025-03 | 前瞻/回溯反思 | Prospective Reflection 跨 utterance/turn/session 粒度摘要入库；Retrospective Reflection 用 RL 在线优化检索 [^34^] | LongMemEval 较无记忆基线 +10% acc |
| MemoryOS | 2025-05, EMNLP'25 | OS 式三层记忆 | STM→MTM（FIFO 对话链）→LPM（分段分页）；热度驱动驱逐 [^33^] | LoCoMo F1 +49.11%，BLEU-1 +46.18%（GPT-4o-mini） |
| MemOS / A-MEM / Zep | 2025 | 记忆 OS / 笔记网络 / 时序图 | MemOS 把记忆做成可调度资源（MemCube）；A-MEM Zettelkasten 链接演化；Zep 时序知识图谱 [^44^] | — |
| Letta Sleep-time Compute | 2025-04 | 睡眠式巩固（离线预计算） | 空闲期对上下文"预先思考"、预生成推理轨迹，分摊到未来查询 [^23^] | 同精度下测试时算力 ↓~5×；GSM-Symbolic +13%、AIME +18%；多查询分摊成本 ↓2.5× |
| Language Models Need Sleep (Google) | 2026-06 | 参数级睡眠巩固 | Sleep 范式：Knowledge Seeding（快记忆→慢记忆的低秩专家蒸馏）+ Dreaming（自生成课程排练）+ 剪枝 [^24^] | SQuAD 48.9 vs 无 Dreaming 35.7 vs 基座 31.9；BABILong 在 10M token 仍稳定 |
| FSFM | 2026-04 | 选择性遗忘框架 | 海马体索引 + Ebbinghaus 衰变的分类法：被动衰减/主动删除/安全触发/自适应强化 [^26^] | 低价值记忆 λ=0.85 快速衰减 vs 高价值缓慢衰减 |
| Oblivion | 2026-04 | 衰减驱动遗忘 | 分层记忆痕迹上的衰减激活；不确定性门控检索；反馈驱动更新 [^27^] | — |
| Epistemics of Agent Memory / ConsolidationBench | 2026-09 | 巩固"决策质量"度量 | 把度量从"记住多少"转向"巩固决策好不好/可不可信"；可学习的提升时机与抽象层级选择 [^25^] | Phase-2：任务成功率 +22.7%，~7× 压缩；暴露 degenerate-forgetting 失效模式 |
| DreamBench-SWE | 2026-07 | 记忆卫生基准 | 多会话软件 agent 的记忆写入/维护/检索/使用分阶段诊断 [^28^] | — |

### 1.B RAG / 上下文压缩谱系（文本空间→潜空间）

| 工作 | 时间/出处 | 类别 | 核心机制 | 关键数字 |
|---|---|---|---|---|
| Lost in the Middle | 2023-07, TACL'24 | 动机证据 | 相关信息在上下文中段时性能 U 形塌陷；32k+ 模型亦然 [^5^] | — |
| RECOMP | 2023-10 | 检索后文本压缩 | 抽取式/生成式压缩器，以端到端任务信号训练；可返回空串（选择性增强） [^6^] | NQ 上 5% token 仅掉 2 EM；oracle 6% 压缩率 |
| LLMLingua / LongLLMLingua / LLMLingua-2 | 2023-10 ~ 2024 | token 级剪枝 | 小模型算困惑度删冗余 token；LongLLMLingua 面向 RAG 长上下文、问题感知 [^7^] | 最高 20× 压缩 |
| ICAE | 2023-07, ICLR'24 | 潜空间压缩 | 冻结 LLM 为解码器，LoRA 编码器把长上下文压成 memory slots [^8^] | 4× 压缩、+1% 参数 |
| AutoCompressors / Nugget / 500xCompressor | 2023–2024 | 摘要向量/信息块 | 递归压缩成 summary vectors；注意力熵选 nugget [^8^] | — |
| MemoRAG | 2024-09 | KV 压缩作全局记忆 | 把整个语料压成 KV 形式的全局记忆 θmem，生成"线索"引导检索；RLGF 强化 [^21^] | β∈[4,64]，128K 模型可处理 8M token |
| Cartridges (Stanford/Hazy) | 2025-06 | 训练式 KV 压缩 | Self-Study：为语料离线训练小型 KV cache（context distillation），推理时直接加载 [^22^] | 匹配 ICL 性能，显存 ↓38.6×，吞吐 ↑26.4×；128k→484k 有效窗口 |
| Recursive Language Models (MIT) | 2025-12 | 上下文=外部环境 | 长 prompt 作为 REPL 变量，LLM 写代码分解并递归调用自身 [^32^] | 超窗口 2 个数量级；GPT-5 上较 compaction 中位 +26% |

### 1.C KV cache 压缩/驱逐（推理侧算法）

| 工作 | 时间/出处 | 机制 | 关键数字 |
|---|---|---|---|
| StreamingLLM / H2O | 2023, NeurIPS'23 奠基 | attention sink+滑窗 / 累计注意力 heavy-hitter 驱逐 [^10^] | — |
| SnapKV | 2024-04, NeurIPS'24 | 观察窗投票选重要 KV 位置，prefill 期压缩 [^9^] | 16K 输入：生成速度 ↑3.6×、显存效率 ↑8.2×；压缩率 2–32×；380K token 单卡可跑 |
| PyramidKV / Quest / KIVI / TOVA / DuoAttention / KVzip / R-KV | 2024–2025 | 分层预算 / 页级检索式稀疏 / 量化 / 检索头-流式头分工 [^10^] | — |
| "Assessing KV Cache Compression On Reasoning" | 2025-12 | 推理模型上 KV 压缩基准 | attention-based heavy-hitter（H2O、SnapKV-D）在推理模型上整体最优，偶超 full-cache；但推理模型上除 SnapKV-D 外均显著落后 full cache；注意力损失与性能强相关 [^10^] |

### 1.D KV 复用 / 前缀缓存 / 分层存储（推理侧系统）

| 工作 | 时间/出处 | 机制 | 关键数字 |
|---|---|---|---|
| vLLM PagedAttention | 2023-09, SOSP'23 奠基 | KV 分页管理 [^2^] | — |
| Prompt Cache | 2023-11, MLSys'24 | Prompt Module 显式 schema，跨 prompt 复用注意力状态 [^12^] | TTFT ↓8×(GPU)~70×(CPU) |
| SGLang RadixAttention | 2024, NeurIPS'24 | radix tree 前缀共享 LRU [^17^] | — |
| AttentionStore | 2024-03 | 多轮会话 KV 分层落盘复用；位置编码解耦使截断后 KV 仍有效 [^11^] | TTFT ↓最高 87%，prefill 吞吐 ↑7.8×，成本 ↓70%；历史 token 占新轮次 prefill 的 99% |
| RAGCache | 2024-04, ASPLOS'25 | 检索文档 KV 组成知识树，GPU/主机多级缓存，PGDSF 替换策略 [^14^] | TTFT ↓最高 4×，吞吐 ↑2.1× |
| MemServe | 2024-06 | MemPool 统一管分布式内存+KV，首个把 context caching 与 PD 分离结合 [^16^] | JCT 改善最高 42%+29% |
| Mooncake (Kimi) | 2024-06（生产） | KVCache-centric PD 分离；CPU/DRAM/SSD/RDMA 组成分离式 KV 池，前缀缓存近 GPU 化 [^15^] | 模拟吞吐最高 +525%；真实负载多承载 75% 请求 |
| CacheBlend | 2024-05, EuroSys'25 | 非前缀 RAG chunk 的 KV 复用 + 选择性重算融合 [^13^] | — |
| EPIC | 2024-10, ICML'25 | 位置无关缓存（LegoLink 只重算每 chunk 前 ≤32 个 token 修复 attention sink） [^18^] | TTFT 较 CacheBlend-15 ↓8× |
| InferCept | 2024, ICML'24 | agent 工具调用中断时 discard/preserve/swap 的 min-waste 决策 [^19^] | 重算浪费最高 40% 算力 |
| SGLang HiCache | 2025-02 起 | L1=GPU/L2=主机/L3=分布式（Mooncake/3FS/NIXL）三层 KV 缓存 [^17^] | 输入吞吐最高 15.5×（官方 benchmark） |
| LMCache | 2025-10, MLSys'26 | 企业级独立 KV cache 层 [^39^] | — |
| Marconi / ContextPilot / Multi-Segment Attention | 2025–2026 | 混合模型前缀缓存 / 上下文复用 / KV 分段管理 [^17^] | — |
| galahad-kv（KV 长期记忆实验） | 2026-10 | 每 16K token 块 KV 加密落 NVMe，字节级精确回放，不重算 [^38^] | 50M token 流上 100/100 命中；加载较重算快 2.8–4.3×、GPU 能耗 ↓8.8–12.3×；百万 token 前埋点问答 82–98/100 |

### 1.E "驱逐→摘要入库"（compaction）作为系统问题的直接研究（2025–2026，新兴）

| 工作 | 时间/出处 | 核心发现 | 关键数字 |
|---|---|---|---|
| Anthropic《Effective context engineering for AI agents》 | 2025-09-29 官方博客 | 把 compaction（摘要并重启）、结构化笔记、子代理、JIT 检索列为四大上下文工程技术；"注意力预算"随 token 数摊薄 [^37^] | 建议部分负载在 5–20k token 即触发 compaction（转引自 [^28^]） |
| Context Rot（Chroma 技术报告） | 2025-07-14 | 18 个前沿模型随输入变长性能非均匀劣化，即使任务简单；单个干扰项即降性能 [^36^] | LongMemEval 上 ~300 token 聚焦输入优于 ~113k token 全历史 |
| Parallel Context Compaction | 2026-05 | 同步摘要阻塞数十秒且摘要体量不可控；并行分块压缩给出细粒度、可预期的摘要体量 [^29^] | 8B–120B 四骨干、HotpotQA+LoCoMo |
| Slipstream（Princeton） | 2026-05 | 同步 compaction 存在"结构性验证缺口"（压缩器不知道未来需要什么）；异步 compaction + 轨迹 judge 校验（plan 级+statement 级） [^28^] | SWE-bench Verified/BrowseComp 准确率最高 +8.8pt，端到端延迟 ↓39.7%；88–100% 的压缩错误在 3 步内显现；judge 拒绝率 1.0–8.5% |
| Governance Decay / ConstraintRot | 2026-06 | compaction 会静默抹除安全约束：约束在摘要中丢失 → 违规率 0%→38%；并提出 Compaction-Eviction Attack 与 Constraint Pinning 缓解 [^30^] | 1323 episodes：全上下文 0% 违规 → compaction 后 30%（个别模型 59%） |
| Context Recycling | 2026-05 | 上下文窗口生命周期管理：分层记忆架构 + 显式"上下文回收/主动加载"（应用中间件层，与 PagedAttention 互补） [^31^] | — |
| ContextBudget / HiMem / HiAgent | 2025–2026 | 把"压缩什么/保留什么"建模为预算约束下的序贯决策/分层工作记忆 [^31^] | HiAgent 成功率 +20% |

---

## 2. 关键数据（压缩率 / 保真度 / 命中率，带出处日期）

**文本摘要/压缩侧**
- 递归摘要 vs MemoryBank：MSC 上记忆 F1 均有 +25% 量级，Rsum 更优（arXiv:2308.15022，2023-08/v4 2025-05）[^35^]
- RECOMP：NQ/TQA 上以 5% token 压缩率仅损失 2–3.7 EM；oracle 达 6%（2023-10）[^6^]
- LongLLMLingua：长上下文 RAG 最高 20× 压缩（综述 2410.12388，2024-10）[^7^]
- ICAE：4× 压缩、约 1% 附加参数（2023-07）[^8^]
- RMM：LongMemEval 准确率较无记忆 +10%+（2025-03）[^34^]
- MemoryOS：LoCoMo F1 +49.11%（2025-05，EMNLP'25）[^33^]
- Letta Sleep-time Compute：同精度测试时算力 ~5× 节省；多查询摊销成本 ↓2.5×（2025-04，厂商自测）[^23^]
- ConsolidationBench Phase-2：可学习的巩固决策 +22.7% 成功率 @ ~7× 压缩，但出现"近乎完全不作为换取高精度"的退化遗忘（2026-09）[^25^]

**KV/系统侧**
- SnapKV：3.6× 生成加速、8.2× 显存效率 @16K；380K 单卡（2024-04）[^9^]
- AttentionStore：TTFT ↓87%（长序列 ↓95%）、prefill 吞吐 ↑7.8×、成本 ↓70%（2024-03）[^11^]
- RAGCache：TTFT ↓4×、吞吐 ↑2.1×（2024-04）[^14^]
- Mooncake：吞吐最高 +525%，真实负载多 75% 请求（2024-06）[^15^]
- Prompt Cache：TTFT ↓8–70×（MLSys'24）[^12^]
- Cartridges：显存 ↓38.6×、吞吐 ↑26.4×，128k→484k 有效窗口（2025-06）[^22^]
- galahad-kv：50M token KV 落盘字节级回放 100/100，加载快 2.8–4.3×（2026-10，单一来源需谨慎）[^38^]
- Slipstream：准确率 +8.8pt、延迟 ↓39.7%（2026-05）[^28^]
- Governance Decay：compaction 后违规率 0%→30–59%（2026-06）[^30^]

**KV 压缩在推理模型上的保真度警示（2025-12 基准）[^10^]**：注意力损失越小的方法性能越好；非推理模型上多种方法可偶超 full-cache，但推理（长 CoT）模型上只有 SnapKV-D 能稳定打平 full cache——KV 驱逐对推理链并非免费。

---

## 3. 趋势判断（收敛方向 + 空白点）

**收敛方向（事实层）**
1. **"上下文=虚拟内存"已从隐喻落地为工程事实，但分成两条互不连通的实现线**：
   - *推理侧*：KV 沿 HBM→DRAM→SSD→远端逐层流动，驱逐=删除（必要时重算），复用=字节级精确（PagedAttention→AttentionStore→Mooncake→HiCache→LMCache）。KV 被明确当作"纯缓存"——miss 的代价是重算，不是遗忘 [^11^][^15^][^17^][^38^]。
   - *记忆侧*：上下文溢出时走 compaction/摘要入库（Anthropic 工程实践已标准化 [^37^]，Slipstream/Parallel Compaction 开始系统化 [^28^][^29^]）。驱逐=有损摘要，miss 的代价是信息永久丢失。
2. **compaction 的风险研究在 2026 年集中爆发**：同步阻塞、摘要体量不可控 [^29^]、验证缺口 [^28^]、安全约束静默丢失 [^30^]、degenerate forgetting [^25^]。社区共识正在形成："摘要入库"必须配验证/可恢复机制，不能裸奔。
3. **潜空间（KV 参数化）记忆是压缩保真度的上升路线**：MemoRAG（KV 全局记忆 β=4–64）[^21^]、Cartridges（训练式 KV，显存 ↓38.6× 且匹配 ICL）[^22^]、Google Sleep（蒸馏进慢参数）[^24^] 均指向"文本摘要高度有损、潜空间压缩保留模型原生记忆格式"（Attic-KV 的 related work 明确表述 token-space summarization is "highly lossy" [^45^]）。
4. **遗忘从手工曲线走向可学习/可度量**：Ebbinghaus 谱系（MemoryBank→SAGE→FSFM）仍是默认基线 [^4^][^26^]，但 2026 年出现以"巩固决策质量"为对象的度量与基准（ConsolidationBench [^25^]、DreamBench-SWE [^28^]），以及把"忘什么"建模为预算约束决策问题（ContextBudget [^31^]）。
5. **离线/睡眠式整理成为独立时间相位**：Sleep-time Compute（Letta）[^23^]、Google Sleep/Dreaming [^24^]、MemGPT→Letta 的 sleep-time agents 产品化，说明"唤醒期服务、睡眠期巩固"已是工程共识。

**空白点评估："KV 驱逐 → 摘要入库"是否确为空白？（判断层）**

- **部分空白，但边界正在被从两侧逼近，2026 年已不再是无人区**：
  - 推理侧系统（Mooncake/HiCache/AttentionStore）把 KV 驱逐到更慢的*同构*介质，**没有任何主流 serving 系统把被驱逐 KV 转成文本摘要写进记忆框架**；驱逐语义是"可重算的缓存失效"而非"有损归档"。此为我方立场的正向证据：尚无系统论文研究"驱逐去向=有损摘要"这条边。
  - 记忆侧（MemGPT/Letta、Slipstream、Context Recycling）做的是"上下文满→LLM 摘要→外部存储"，但它发生在**应用层/中间件层**，与推理引擎的 KV 驱逐事件完全脱钩——摘要由 LLM 主动生成，不是 KV 驱逐的副作用。
  - 两侧最接近的桥：MemoRAG/Cartridges 证明 KV 可以*训练*成长期可用的潜记忆 [^21^][^22^]；galahad-kv 证明 KV 可以*落盘*成字节级长期记忆 [^38^]；但都未解决"驱逐时刻在线生成摘要/潜记忆并入库、载入时双层恢复（KV 或摘要）"的统一生命周期。
- **结论（判断，置信度中高）**："有损驱逐→摘要入库"作为一个**跨越推理引擎与记忆框架的统一驱逐策略**，截至 2026-11 没有顶会/系统论文直接研究；最接近的系统级工作（Slipstream、Parallel Compaction、Context Recycling、Governance Decay）全部停留在文本摘要层且位于引擎之外。我方接口设计具备原创空间，但需注意：2026 年该方向论文密度快速上升，"空白窗口"预计在 1–2 年内被填。
- **次要空白**：(a) KV 驱逐重要性信号（attention score 等）与记忆重要性打分（LLM 自评）从未被打通——attention 的 heavy-hitter 信号几乎是免费的"重要性加权"来源，尚无工作用它驱动记忆入库决策；(b) 摘要的"可恢复性/可审计性"（provenance）只在 Oblivion [^27^]、mimir_dream 等零散工作出现；(c) 安全面（Governance Decay 的 Compaction-Eviction Attack）说明驱逐接口本身是攻击面，尚无防御体系。

---

## 4. 对我方架构立场的启发

立场回顾：记忆框架与内存管理间存在"有损驱逐"接口；KV/上下文被驱逐时可摘要入库；KV 是纯缓存，驱逐去向含"有损摘要到记忆框架"。

1. **【支持】KV=纯缓存、驱逐可重算的语义与主流 serving 系统完全一致。** AttentionStore/Mooncake/HiCache/LMCache 全部把 KV 当可重建缓存分层流动 [^11^][^15^][^17^][^39^]。我方"KV 是纯缓存"的定位是行业收敛方向，无争议。
2. **【支持】驱逐时摘要入库在记忆侧已是标准实践，我方接口有成熟范式可借。** Anthropic 官方建议 5–20k token 即触发 compaction [^37^]；MemoryOS 的 STM→MTM FIFO、MemGPT 的水位警报分页都是"满则摘要换出" [^33^][^1^]。
3. **【支持，且是差异化机会】"把驱逐事件本身变成入库触发器"（引擎层驱逐 → 记忆层写入）确为半空白**（见 §3 空白评估）。现有工作要么引擎内驱逐不摘要（KV 分层），要么引擎外摘要不接驱逐事件（compaction 系统）。我方接口若把两者缝合成一个统一驱逐策略，属于领先半步的设计。
4. **【挑战/必须修订】裸摘要入库已被 2026 年研究证伪为不可靠。** Slipstream 证明同步摘要存在结构性验证缺口且错误静默传播 [^28^]；Governance Decay 证明摘要会丢安全约束（0%→30–59% 违规）[^30^]；ConsolidationBench 发现退化遗忘失效模式 [^25^]。→ 我方"有损驱逐"接口**必须内置**：(a) 摘要前的关键项钉住（constraint pinning 类）；(b) 摘要质量的异步校验（judge/轨迹对照）；(c) 驱逐决策的可撤销/可恢复通道（原文在冷存储保留一段时间）。
5. **【挑战】KV 驱逐对推理链不是免费的。** 2025-12 基准显示推理模型上除 SnapKV-D 外各驱逐策略均显著落后 full cache [^10^]；"context rot"显示长输入本身即降智 [^36^]。→ 驱逐时机不能只按显存水位，应结合内容位置（lost-in-the-middle [^5^]）与推理阶段。
6. **【需要修订】"摘要"不应默认=文本摘要。** Cartridges/MemoRAG/Google Sleep 表明潜空间（训练式 KV / 参数蒸馏）保真度远高，token-space 摘要被明确批评为 highly lossy [^22^][^45^]。→ 我方接口应预留**双去向**：热驱逐→KV 落盘（字节级，galahad-kv 已验证 50M token 可行 [^38^]）；冷驱逐→文本/结构化摘要入库；长期可探索 ICAE/Cartridge 式潜记忆作为第三层。
7. **【支持+机会】免费的重要性信号未利用。** KV 驱逐文献积累了大量 token 重要性度量（累计注意力、key L2 norm、观察窗投票 [^9^][^10^]）；记忆文献用昂贵的 LLM 自评打分 [^3^][^25^]。我方可在驱逐接口处复用 attention 信号做入库优先级/遗忘权重，成本近零——这是两侧文献都没想到的交叉点。
8. **【支持】睡眠期是入库后整理的正确相位。** Sleep-time Compute（算力 ↓5×）[^23^] 与 Google Sleep（巩固+Dreaming）[^24^] 证明离线整理收益显著；我方摘要入库后的巩固/去重/矛盾消解应放在空闲相位，避免阻塞关键路径（Parallel Compaction/Slipstream 的异步化亦同向 [^28^][^29^]）。

---

## 5. 证据清单

[^1^]: **Claim**: MemGPT 把上下文视为受限内存资源，类比 OS 虚拟内存，LLM 自主分页/驱逐到外部存储。 **Source**: MemGPT: Towards LLMs as Operating Systems. **URL**: https://arxiv.org/abs/2310.08560. **Date**: 2023-10-12. **Excerpt**: "we treat context windows as a constrained memory resource, and design a memory hierarchy for LLMs analogous to memory tiers used in traditional OSes ... MemGPT enables the LLM to retrieve relevant historical data missing from what is placed in-context, and also evict less relevant data from context and into external storage systems." **Confidence**: 高.
[^2^]: **Claim**: vLLM PagedAttention 对 KV cache 做 OS 式分页管理（SOSP'23）。**Source**: Kwon et al., Efficient Memory Management for LLM Serving with PagedAttention, arXiv:2309.06180. **URL**: https://arxiv.org/abs/2309.06180. **Date**: 2023-09. **Confidence**: 高（多方引用一致）.
[^3^]: **Claim**: Generative Agents 记忆流检索=Recency(0.995/小时指数衰减)+Importance(LLM 1–10 分)+Relevance(余弦)，等权相加；Reflection 周期性合成高层洞察。**Source**: Park et al., UIST 2023, arXiv:2304.03442. **URL**: https://arxiv.org/pdf/2304.03442. **Date**: 2023-04. **Excerpt**: "Recency assigns a higher score... decay factor is 0.995. Importance distinguishes mundane from core memories..." **Confidence**: 高.
[^4^]: **Claim**: MemoryBank 引入 Ebbinghaus 遗忘曲线做记忆更新/遗忘，并对对话做日→全局分层摘要。**Source**: Zhong et al., AAAI 2024, arXiv:2305.10250. **URL**: https://arxiv.org/html/2305.10250v3. **Date**: 2023-05-21. **Excerpt**: "inspired by the Ebbinghaus Forgetting Curve theory ... empowers the AI to remember, selectively forget, and strengthen memories based on time elapsed". **Confidence**: 高.
[^5^]: **Claim**: 相关信息位于长上下文中段时性能显著下降（U 形），长上下文模型亦然。**Source**: Liu et al., Lost in the Middle, TACL 2024, arXiv:2307.03172. **URL**: https://aclanthology.org/2024.tacl-1.9/. **Date**: 2023-07（TACL 2024 正式）. **Confidence**: 高.
[^6^]: **Claim**: RECOMP 用任务信号训练检索后压缩器，NQ 上 5% token 仅掉 2 EM，oracle 压缩率 6%。**Source**: Xu, Shi, Choi, arXiv:2310.04408. **URL**: https://arxiv.org/abs/2310.04408. **Date**: 2023-10-06. **Excerpt**: "We achieve a compression rate of as low as 6% with minimal loss in performance... On NQ, it achieves a compression ratio of 5% tokens while losing 2 EM points". **Confidence**: 高.
[^7^]: **Claim**: LLMLingua 系列用小模型困惑度删冗余 token，LongLLMLingua 面向 RAG 最高 20× 压缩。**Source**: Prompt Compression for LLMs: A Survey, arXiv:2410.12388；LLMLingua arXiv:2310.05736. **URL**: https://arxiv.org/html/2410.12388v2. **Date**: 2024-10-17. **Excerpt**: "Achieving compression ratios up to 20x". **Confidence**: 高.
[^8^]: **Claim**: ICAE 用 LoRA 编码器把长上下文压成 memory slots，4× 压缩、+~1% 参数；AutoCompressors/Nugget 为同谱系。**Source**: Ge et al., ICLR 2024, arXiv:2307.06945. **URL**: https://arxiv.org/abs/2307.06945. **Date**: 2023-07. **Excerpt**: "effectively achieves 4x context compression based on Llama, offering advantages in both improved latency and GPU memory cost". **Confidence**: 高.
[^9^]: **Claim**: SnapKV 观察窗投票压缩 prompt KV，16K 输入生成速度 3.6×、显存效率 8.2×，单卡 380K token。**Source**: Li et al., NeurIPS 2024, arXiv:2404.14469. **URL**: https://arxiv.org/html/2404.14469v2. **Date**: 2024-04. **Excerpt**: "a 3.6x increase in generation speed and an 8.2x enhancement in memory efficiency ... when processing inputs of 16K tokens". **Confidence**: 高.
[^10^]: **Claim**: 推理模型上 KV 驱逐压缩整体落后 full cache（SnapKV-D 除外），注意力损失与性能强相关。**Source**: Assessing KV Cache Compression On Reasoning, arXiv:2512.12008. **URL**: https://arxiv.org/html/2512.12008v1. **Date**: 2025-12-12. **Excerpt**: "classical attention-based 'heavy-hitter' strategies ... significantly outperform other methods... Eviction lags full cache performance for reasoning models". **Confidence**: 中高（单篇基准）.
[^11^]: **Claim**: AttentionStore 跨会话分层保存 KV 并复用，TTFT↓87%、prefill↑7.8×、成本↓70%；位置编码解耦使截断后 KV 仍有效。**Source**: Gao et al., arXiv:2403.19708. **URL**: https://arxiv.org/html/2403.19708v2. **Date**: 2024-03/04. **Excerpt**: "decreases the time to the first token (TTFT) by up to 87% and improves the prompt prefilling throughput by 7.8× ... reduces the end-to-end inference cost by up to 70%". **Confidence**: 高.
[^12^]: **Claim**: Prompt Cache 以 schema 显式声明可复用文本段并预计算注意力状态，TTFT↓8×(GPU)–70×(CPU)。**Source**: Gim et al., MLSys 2024, arXiv:2311.04934. **URL**: https://arxiv.org/pdf/2311.04934. **Date**: 2023-11（MLSys 2024）. **Confidence**: 高.
[^13^]: **Claim**: CacheBlend 实现非前缀位置 RAG chunk 的 KV 复用+选择性重算（EuroSys 2025）。**Source**: Yao et al., arXiv:2405.16444. **URL**: https://arxiv.org/abs/2405.16444. **Date**: 2024-05. **Confidence**: 高（venue 经多方引用确认）.
[^14^]: **Claim**: RAGCache 把检索文档 KV 组织为知识树做 GPU/主机多级缓存，TTFT↓4×、吞吐↑2.1×。**Source**: Jin et al., ASPLOS 2025, arXiv:2404.12457. **URL**: https://arxiv.org/abs/2404.12457. **Date**: 2024-04-18. **Excerpt**: "reduces the time to first token (TTFT) by up to 4× and improves the throughput by up to 2.1×". **Confidence**: 高.
[^15^]: **Claim**: Mooncake（Kimi 生产系统）以 KVCache 为中心做 PD 分离与 CPU/DRAM/SSD 分离式缓存，吞吐最高 +525%，真实负载多承载 75% 请求。**Source**: Qin et al., arXiv:2407.00079. **URL**: https://arxiv.org/abs/2407.00079. **Date**: 2024-06-24. **Excerpt**: "Mooncake can achieve up to a 525% increase in throughput ... enables Kimi to handle 75% more requests". **Confidence**: 高.
[^16^]: **Claim**: MemServe 用 MemPool 统一分布式内存与 KV 管理，首次结合 context caching 与 PD 分离，JCT 改善 42%+29%。**Source**: Hu et al., arXiv:2406.17565. **URL**: https://arxiv.org/abs/2406.17565. **Date**: 2024-06-25. **Confidence**: 高.
[^17^]: **Claim**: SGLang HiCache 组织 L1 GPU/L2 主机/L3 分布式三层 KV 缓存（2025-02 起，集成 Mooncake/3FS/NIXL）。**Source**: SGLang 官方文档. **URL**: https://docs.sglang.ai/advanced_features/hicache_design.html. **Date**: 访问于 2026-11-05. **Excerpt**: "HiCache organizes GPU memory as L1, host memory as L2, and distributed storage as L3". **Confidence**: 高（官方文档）.
[^18^]: **Claim**: EPIC 位置无关缓存 LegoLink 每 chunk 仅重算 ≤32 个初始 token，TTFT 较 CacheBlend-15 低 8×（ICML 2025）。**Source**: Hu et al., arXiv:2410.15332. **URL**: https://arxiv.org/abs/2410.15332. **Date**: 2024-10（ICML 2025）. **Confidence**: 中高（数字经二手 explainer 与引用确认）.
[^19^]: **Claim**: InferCept 处理 agent 工具调用中断时的 KV discard/preserve/swap 选择，避免最高 40% 的重算浪费（ICML 2024）。**Source**: Abhyankar et al., ICML 2024. **URL**: https://arxiv.org/abs/2406.10658. **Date**: 2024. **Confidence**: 中高.
[^20^]: **Claim**: InfLLM 把历史 KV 组织为块级外部记忆、全部卸载到 CPU、LRU 缓存常用块，100K token 仅需 26G VRAM。**Source**: Xiao et al., arXiv:2402.04617. **URL**: https://arxiv.org/html/2402.04617. **Date**: 2024-02. **Excerpt**: "InfLLM offloads all units on CPU memory and dynamically retains the frequently used units on GPU memory". **Confidence**: 高.
[^21^]: **Claim**: MemoRAG 以 KV 压缩（β∈[4,64]）实现全局记忆，生成检索线索，128K 模型可处理 8M token。**Source**: Qian et al., arXiv:2409.05591. **URL**: https://arxiv.org/abs/2409.05591. **Date**: 2024-09-09. **Excerpt**: "we realize the memory module in the form of a KV-compressible LLM with configurable compression rates ... a 128K context LLM can process up to an 8M token context when β=64". **Confidence**: 高.
[^22^]: **Claim**: Cartridges 离线为语料训练小型 KV cache（Self-Study+context distillation），匹配 ICL 且显存↓38.6×、吞吐↑26.4×。**Source**: Eyuboglu et al., arXiv:2506.06266. **URL**: https://arxiv.org/abs/2506.06266. **Date**: 2025-06-06. **Excerpt**: "match ICL performance while using 38.6x less memory and enabling 26.4x higher throughput". **Confidence**: 高.
[^23^]: **Claim**: Sleep-time compute 离线预计算上下文，同精度测试时算力↓~5×，GSM-Symbolic +13%/AIME +18%，多查询摊销成本↓2.5×。**Source**: Lin et al. (Letta/UC Berkeley), arXiv:2504.13171. **URL**: https://arxiv.org/abs/2504.13171. **Date**: 2025-04-17. **Excerpt**: "sleep-time compute can reduce the amount of test-time compute needed to achieve the same accuracy by ~5×". **Confidence**: 高（注意：厂商自测基准，无独立复现）.
[^24^]: **Claim**: Google"Language Models Need Sleep"提出巩固（Knowledge Seeding 蒸馏到慢参数）+Dreaming（自生成课程）睡眠范式，缓解灾难性遗忘；SQuAD 48.9 vs 无 Dreaming 35.7。**Source**: Behrouz, Hashemi, Mirrokni, arXiv:2606.03979. **URL**: https://arxiv.org/abs/2606.03979. **Date**: 2026-06-02. **Confidence**: 中高.
[^25^]: **Claim**: ConsolidationBench 把度量转向"巩固决策质量"；Phase-2 可学习提升策略 +22.7% 成功率 @ ~7× 压缩，但暴露 degenerate-forgetting 失效模式。**Source**: The Epistemics of Agent Memory, arXiv:2609.33013. **URL**: https://arxiv.org/html/2609.33013v1. **Date**: 2026-09-26. **Excerpt**: "achieving a verified +22.7% task-success improvement with ~7× compression, but exposing a degenerate-forgetting failure". **Confidence**: 中高（预印本，未同行评审）.
[^26^]: **Claim**: FSFM 给出选择性遗忘分类法（被动衰减/主动删除/安全触发/自适应强化），低价值记忆快速衰减（λ=0.85）释放资源。**Source**: FSFM, arXiv:2604.20300. **URL**: https://arxiv.org/html/2604.20300v2. **Date**: 2026-04-23. **Confidence**: 中.
[^27^]: **Claim**: Oblivion 以衰减驱动激活+不确定性门控检索+反馈驱动更新实现动态遗忘。**Source**: arXiv:2604.00131. **URL**: https://arxiv.org/pdf/2604.00131. **Date**: 2026-04. **Confidence**: 中.
[^28^]: **Claim**: Slipstream 指出同步 compaction 存在结构性验证缺口；异步 compaction+轨迹 judge 使准确率最高 +8.8pt、延迟↓39.7%；88–100% 压缩错误在 3 步内显现。**Source**: Chen et al. (Princeton), arXiv:2605.08580. **URL**: https://arxiv.org/abs/2605.08580. **Date**: 2026-05-09. **Excerpt**: "improves task accuracy by up to 8.8 percentage points while reducing end-to-end latency by up to 39.7%". **Confidence**: 高.
[^29^]: **Claim**: Parallel Context Compaction 指出同步 LLM 摘要阻塞数十秒且摘要体量不可预期，并行分块压缩给出可控体量。**Source**: Cim et al., arXiv:2605.23296. **URL**: https://arxiv.org/abs/2605.23296. **Date**: 2026-05-22. **Excerpt**: "summarization is inherently lossy and the blocking call stalls agent inference for tens of seconds". **Confidence**: 高.
[^30^]: **Claim**: Governance Decay：compaction 静默抹除安全约束，违规率 0%→30%（个别 59%）；约束保留则维持 0%；提出 Compaction-Eviction Attack 与 Constraint Pinning。**Source**: Chen et al., arXiv:2606.22528. **URL**: https://arxiv.org/abs/2606.22528. **Date**: 2026-06-21. **Excerpt**: "violation rises from 0% with the policy in full context to 30% after compaction, reaching 59% for some models". **Confidence**: 高.
[^31^]: **Claim**: Context Recycling 做上下文窗口生命周期管理（回收+主动加载），与 PagedAttention 互补；相关工作含 ContextBudget（预算约束序贯决策）、HiMem、HiAgent。**Source**: arXiv:2606.26105. **URL**: https://arxiv.org/html/2606.26105. **Date**: 2026-05-01. **Confidence**: 中高.
[^32^]: **Claim**: RLM 把长 prompt 当作 REPL 环境中的外部数据，LLM 程序化分解并递归调用，超窗口 2 个数量级，GPT-5 上较 compaction 中位 +26%。**Source**: Zhang, Kraska, Khattab, arXiv:2512.24601. **URL**: https://arxiv.org/abs/2512.24601. **Date**: 2025-12-31. **Confidence**: 高.
[^33^]: **Claim**: MemoryOS 三层记忆（STM/MTM/LPM）+OS 式 FIFO/分段分页+热度驱逐，LoCoMo F1 +49.11%（EMNLP 2025）。**Source**: Kang et al., arXiv:2506.06326. **URL**: https://arxiv.org/abs/2506.06326. **Date**: 2025-05-30. **Confidence**: 高.
[^34^]: **Claim**: RMM 前瞻反思跨粒度摘要入库+回溯反思 RL 优化检索，LongMemEval 较无记忆基线 +10%+。**Source**: Tan et al., arXiv:2503.08026. **URL**: https://arxiv.org/pdf/2503.08026. **Date**: 2025-03. **Confidence**: 高.
[^35^]: **Claim**: 递归摘要 M_i=LLM(S_i, M_{i−1}) 维持长对话记忆，MSC 上记忆 F1 +25% 量级且优于 MemoryBank。**Source**: Wang et al., arXiv:2308.15022. **URL**: https://arxiv.org/html/2308.15022v3. **Date**: 2023-08（v3 2025-05）. **Confidence**: 高.
[^36^]: **Claim**: Context Rot：18 个前沿模型随输入变长性能非均匀劣化，单干扰项即降性能；~300 token 聚焦输入优于 ~113k 全历史。**Source**: Hong, Troynikov, Huber, Chroma Technical Report. **URL**: https://www.trychroma.com/research/context-rot. **Date**: 2025-07-14. **Confidence**: 中高（工业报告，非同行评审）.
[^37^]: **Claim**: Anthropic 将 compaction/结构化笔记/子代理/JIT 检索列为四大上下文工程技术，建议部分负载 5–20k token 即触发 compaction。**Source**: Anthropic Engineering Blog, "Effective context engineering for AI agents". **URL**: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents. **Date**: 2025-09-29. **Confidence**: 高（官方博客；触发阈值数字经 Slipstream 转引）.
[^38^]: **Claim**: KV 状态可落盘为字节级精确长期记忆：50M token 流 100/100 回放命中，加载较重算快 2.8–4.3×、能耗低 8.8–12.3×。**Source**: "Real Long-Term Memory for AI: A 50-Million-Token Window", arXiv:2610.10845. **URL**: https://arxiv.org/abs/2610.10845. **Date**: 2026-10-07. **Excerpt**: "Loading a block was 2.8x to 4.3x faster than recomputing it and used 8.8x to 12.3x less GPU energy". **Confidence**: 中（单一作者+商业包，需独立验证）.
[^39^]: **Claim**: LMCache 为企业级独立 KV cache 层（MLSys 2026）。**Source**: Liu et al., arXiv:2510.09665. **URL**: https://arxiv.org/abs/2510.09665. **Date**: 2025-10. **Confidence**: 高（venue 经引用确认）.
[^40^]: **Claim**: LongMemEval/LoCoMo 为超长对话记忆标准评测（ACL 2024）。**Source**: Maharana et al., arXiv:2402.17753. **URL**: https://arxiv.org/abs/2402.17753. **Date**: 2024-02. **Confidence**: 高.
[^41^]: **Claim**: Mem0 两阶段提取+ADD/UPDATE/DELETE/NOOP 巩固；厂商自报 LoCOMO +26%、p95 −91%。**Source**: Chhikara et al., arXiv:2504.19413. **URL**: https://arxiv.org/abs/2504.19413. **Date**: 2025-04. **Confidence**: 中高（厂商自报）.
[^42^]: **Claim**: SAGE 用 Ebbinghaus 曲线优化 agent 记忆存储，AgentBench 上 GPT-4 提升最高 2.26×。**Source**: arXiv:2409.00872. **URL**: https://arxiv.org/html/2409.00872v1. **Date**: 2024-09. **Confidence**: 中.
[^43^]: **Claim**: KV 驱逐方法综述将其分为硬驱逐/合并/量化/预算分配等类别。**Source**: "To Evict or to Merge? A Survey of LLM KV Cache Compression"（期刊预印）. **URL**: https://ijcseonline.org/index.php/j/article/download/7546/7379/15062. **Date**: 2026-09. **Confidence**: 中.
[^44^]: **Claim**: MemOS 提出记忆操作系统与 MemCube（arXiv:2505.22101 / 2507.03724）；A-MEM 为 Zettelkasten 式动态链接（arXiv:2502.12110）；Zep 为时序知识图谱记忆（arXiv:2501.13956）。**Source**: 各论文. **URL**: https://arxiv.org/abs/2505.22101. **Date**: 2025. **Confidence**: 高.
[^45^]: **Claim**: 后续 KV 融合文献明确指出 token-space 摘要"highly lossy"，潜空间压缩保留模型原生记忆格式。**Source**: Attic-KV (arXiv:2610.12133) 及 CacheRepair (arXiv:2609.35139) 的 related work. **URL**: https://arxiv.org/html/2610.12133v2. **Date**: 2026-10-09. **Confidence**: 中高.

---

*报告完。事实均以引用支撑；§3 空白点评估与 §4 启发中的"判断"均已显式标注置信度。*

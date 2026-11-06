# Kimi 对照差异：C3 记忆框架与记忆能力

> 对照日期 2026-11-05；核验方式：WebFetch 10 次（arXiv abs/html 8 次、Apple Newsroom 1 次、MemOS 全文 1 次）/ WebSearch 1 次（FragFuse）。总评：Kimi 在 2026 年上半年的 compaction 风险、记忆评测新基准、Apple/DMA 时间线上比我方新，且主论文基本核实；短板是端侧资源成本（J7）几乎没有硬数据，多处依赖聚合博客和媒体，两条被点名条目（MemexRL、VectorTune）在其维度报告里根本没有出处。
>
> 引用约定：「Kimi dimNN 脚注 n」；CV 指 `kimi调研/research/agentos_cross_verification.md`。

## A 可借鉴新增

| # | 条目 | 关键数据 / 事实 | 来源（Kimi 文件+脚注；一手 URL；日期） | 核验 | 建议落点 |
|---|---|---|---|---|---|
| A1 | Governance Decay / ConstraintRot / Compaction-Eviction Attack | 1,323 个 episode、7 个模型族；策略在全上下文中违规 0%，compaction 后 30%，部分模型 59%；约束若在摘要里丢失则违规 38%，若保留则 0%；注入内容可诱使摘要器漏掉合法策略，优化后的注入击败所有被测模型；Constraint Pinning 把违规压回 0% | Kimi dim09 脚注 30；insight I-06；arXiv 2606.22528；2026-06-21（v2 06-27） | **已核实（arXiv abs，WebFetch）**；单作者 Shiyang Chen，预印本，基准为作者自建 | §3 Q4、§5 MEM-3′、§6 J1 |
| A2 | Slipstream：同步 compaction 的验证缺口 | 异步 compaction 加轨迹 judge，SWE-bench Verified / BrowseComp 准确率最高 +8.8 个百分点，端到端延迟最高降 39.7% | Kimi dim09 脚注 28；arXiv 2605.08580；2026-05-09 | **部分核实**：+8.8、-39.7% 与作者（Chen、Pan、Dai、Netravali）已核；「88–100% 的压缩错误 3 步内显现」「judge 拒绝率」摘要未见，未核实（Kimi 单源） | §3 Q4、J1 |
| A3 | FragFuse：记忆分片绕过访问控制 | 把被禁内容拆成能通过访问控制的片段存入长期记忆，检索时由 Agent 重组；4 种 Agent 设置、3 种访问控制机制下平均绕过成功率 86.3%，端到端有害任务成功率 41.1%；提示注入与困惑度检测器均未拦住；建议缓解为记忆准入控制、检索时策略检查、记忆增强后再做访问控制 | Kimi dim06 脚注 25（C2 组件，但与 J4 直接相关）；arXiv 2606.15609；2026-06-14 | **部分核实（WebSearch 摘要，未抓全文）**：论文存在、数字来自 papers.cool 摘要；USENIX Security 2026 收录未能证实。Kimi 给的 arXiv 号有误，见 B2 | §3 Q7、§6 J4 |
| A4 | MemOS MemCube 治理属性 | MemCube 元数据含访问权限、生命周期策略（TTL 或频率衰减）、优先级、敏感度标签、水印、访问日志 | Kimi dim07 脚注 4、dim08 脚注 34；arXiv 2505.22101 §4.2；2025-05-28 | **已核实（全文 §4.2，WebFetch）**；摘要页不含这些属性，只在正文。这是论文设计，不等于实现或 OS 强制 | §7.1 表 MemOS 行；§5 MEM-1′ |
| A5 | LongMemEval-V2 与 GroupMemBench | LME-V2：451 题；AgentRunbook-C（轨迹存成文件，coding agent 在沙箱里查证）72.5%，现成 coding agent 69.3%，最佳 RAG 48.5%。GroupMemBench：最强系统平均 46.0%，知识更新 27.1%，术语歧义 37.7%，简单 BM25 持平或超过多数记忆系统 | Kimi dim07 脚注 29、35；arXiv 2605.12493（2026-05-12）、2605.14498（2026-05-14） | **已核实（abs 页，WebFetch）**，与 CV 一致 | §0 第 1 条、§3 Q1/Q2、MEM-1 反方证据 |
| A6 | Apple Trusted System Agent 被欧委会拒绝 | Apple 2026-06-08 称设计了让第三方助手经中介访问与 Siri AI 同等能力的 Trusted System Agent，欧委会「说不」；Apple 称 iOS/iPadOS 27 上 EU 暂无 Siri AI 时间表，macOS 27 与 visionOS 27 在 EU 可用 | Kimi dim08 脚注 15（官方）、16（AP）；apple.com/newsroom/2026/06/due-to-dma-siri-ai-delayed-in-eu-for-ios-27-and-ipados-27；2026-06-08 | **已核实（Apple Newsroom，WebFetch）**；AP 一条未抓。「12–24 个月窗口」是 Kimi 推断，不是来源事实 | §3 Q3、MEM-4′ 最强反方证据 |
| A7 | HarmonyOS 授权机制 | 取消 9 类不合理权限，图库与通讯录强制 System Picker，「单次授予、单次访问」；UDMF 带权限与生命周期的跨应用数据通路；数据分类 S1–S4。均为条目级或通路级，没有语义索引层 | Kimi dim08 脚注 21、22、45；华为《HarmonyOS NEXT 安全技术白皮书》2024-08 | 未核实（Kimi 引官方白皮书与文档镜像，我方未抓） | §7.2 矩阵 HarmonyOS 列「授权粒度」 |
| A8 | 失效记忆基准：Memora/FAMA、STALE | Memora（ACL 2026 Findings）：4 个 LLM、6 个记忆 Agent，频繁复用已失效记忆，记忆 Agent 仅带来边际提升；STALE：400 个专家校验的冲突场景，考察隐性冲突 | Kimi dim07 脚注 33、34；arXiv 2604.20006（2026-04）、2605.06527（2026-05-07） | Memora 存在性经 CV 核实；STALE 与 Memora 具体数字我方未抓 | §3 Q2「冲突消解」 |
| A9 | 程序性记忆近乎空白 | Mem0 的程序路径与语义路径只差一个 metadata 标签，Graphiti 无程序记忆概念；仅 LangMem 的 Prompt Optimizer 是独立机制 | Kimi dim07 脚注 11；brgsk.xyz，2026-05-26 | 未核实（Kimi 单源，博客自称「源头核验」） | §4 空白点、§7.3 形态选型（补「程序性」行） |
| A10 | AIOS Access Manager | 内核含 memory / storage / access manager，access manager 负责 Agent 间隐私与访问控制 | Kimi dim07 脚注 20；arXiv 2403.16971；2024-03 | 未核实（我方未抓；CV 列为多源一致） | §5 MEM-1 反方证据（补先例） |
| A11 | 被采集旁观者的数据主体保护 | EDPB 智能眼镜声明：always-on 采集须告知旁观者、指示器不可规避；OS 级索引无一处理 | Kimi dim08 脚注 57；Kaamel 整理，2026-10-14 | 未核实（二手整理，Kimi 自己也建议核原文） | §6 空白点 5（被采集方排除权） |

**A1 建议插入文字（§3 Q4 末尾，并在 §6 J1 引用）**

2026-06 的 Governance Decay 在 1,323 个 episode、7 个模型族上测得：策略放在完整上下文里时违规率为 0%，经 compaction 后升到 30%，部分模型达 59%；约束一旦在摘要中丢失，违规率为 38%，保留则为 0%（arXiv 2606.22528，单作者预印本，基准自建）。作者还展示了 Compaction-Eviction Attack：注入内容能诱使摘要器漏掉合法策略，优化后的注入击败了所有被测模型。判断：摘要入库不只是「质量会掉」，摘要器本身是攻击面；权限类、禁令类约束不能依赖摘要器保留，要由 OS 在驱逐前钉住。

**A2 建议插入文字（§6 J1 驱逐对象分类规则下）**

Slipstream 指出同步摘要有结构性验证缺口：压缩时不知道后续需要什么。它用异步 compaction 加轨迹 judge 校验，在 SWE-bench Verified 与 BrowseComp 上准确率最高 +8.8 个百分点，延迟最高降 39.7%（arXiv 2605.08580，2026-05）。判断：摘要入库路径应预留异步校验位，校验成本要计入 C4 的驱逐去向成本模型。

**A3 建议插入文字（§3 Q7 攻击表新增一行，§6 J4）**

FragFuse 把被访问控制拦截的内容拆成合规片段存进长期记忆，检索时由 Agent 重组；在 4 种 Agent 设置、3 种访问控制下平均绕过成功率 86.3%，端到端有害任务成功率 41.1%（arXiv 2606.15609，2026-06；数字来自摘要转载）。判断：只在写入时或单次读取时检查不够，ACL 需要覆盖「记忆增强之后」的组合结果，这与 MEM-4′ 的结果返回路径约束同向。

**A4 建议插入文字（§7.1 MemOS 行「共享与 ACL」「隐私方案」两栏，把「待核实」换掉）**

MemCube 元数据含访问权限、TTL 或频率衰减、优先级、敏感度标签、水印、访问日志（MemOS 论文 §4.2，arXiv 2505.22101）。这是论文设计，没有看到 OS 级强制或硬件信任根。判断：它是 MEM-1′ 元数据集合的最近先例，但调度策略由系统内置，与「策略归 Agent」相反。

**A5 建议插入文字（§3 Q2 失效模式或 §0 第 1 条）**

LongMemEval-V2（451 题，arXiv 2605.12493，2026-05）上，把轨迹存成文件、由 coding agent 在沙箱里查证的 AgentRunbook-C 得 72.5%，现成 coding agent 69.3%，最佳 RAG 仅 48.5%。GroupMemBench（arXiv 2605.14498）上最强系统平均 46.0%，知识更新 27.1%，简单 BM25 持平或超过多数系统。判断：这与「记忆文件化」和「检索结构不稳定优于简单方案」同向；多方场景下实体归属需要从写入起就是一等元数据。

**A6 建议插入文字（§3 Q3 Apple 段，并改 MEM-4′ 反方证据）**

2026-06-08 Apple 称为 EU 设计了 Trusted System Agent，让第三方助手经中介访问与 Siri AI 同等的能力，欧委会拒绝；Apple 表示 iOS/iPadOS 27 上 EU 暂无 Siri AI 时间表（Apple Newsroom）。事实是监管正在把深度访问推向互操作义务，但开放接口并未落地。判断：「Apple/Google 在 2027 年前开放」的反方证据目前只有监管压力，没有产品；窗口长短属推断，不应写成数字。

**A7 建议插入文字（§7.2 矩阵 HarmonyOS 列授权粒度）**

HarmonyOS 授权哲学是「管数据不管权限」：取消 9 类权限，图库与通讯录强制 System Picker，单次授予、单次访问（华为白皮书，2024-08）；UDMF 提供带权限与生命周期的跨应用数据通路。均为条目级或通路级，未见语义索引与查询时授权。

**A8 建议插入文字（§3 Q2 冲突消解）**

2026 年出现专门度量「复用已失效记忆」的基准：Memora 的 FAMA 指标惩罚复用失效记忆，6 个记忆 Agent 仅带来边际提升（ACL 2026 Findings）；STALE 用 400 个专家校验的隐性冲突场景检验 Agent 能否察觉记忆过期（arXiv 2605.06527）。判断：失效识别不能全靠 Agent，印证 MEM-2′ 里 OS 保留失效标记与物理删除的分工。

## B 冲突与更正

| # | 事实 | 我方写法 | Kimi 写法 | 一手来源裁决 | 正确口径 | 我方需改动 |
|---|---|---|---|---|---|---|
| B1 | Governance Decay 的违规率 | 未写 | dim09 §1.E 表写「0%→38%」，同表脚注与 §2 写「0%→30%，个别 59%」 | arXiv 2606.22528 摘要：全上下文 0%，compaction 后 30%，部分模型 59%；38% 是「约束在摘要中丢失」条件下的违规率 | 30% / 59% 是 compaction 后总体；38% 是约束被丢条件下；作者为单人 Shiyang Chen，非「Chen et al.」 | 采用 A1 的写法；不要引 Kimi 表里的「0%→38%」 |
| B2 | FragFuse 的出处 | 未写 | dim06 脚注 25 与成稿 sec03 脚注 3-52 把 FragFuse 与 AgentPoison 的 arXiv 2407.12784 并列，易被读成同一篇 | 搜索得 FragFuse 为 arXiv 2606.15609（2026-06-14）；2407.12784 是 AgentPoison；USENIX Security 2026 收录未能证实 | FragFuse 用 2606.15609；venue 写「USENIX Security 2026（Kimi 称，未核实）」 | 引用 FragFuse 时用上述编号 |
| B3 | Apple Siri 个人上下文的状态 | R14/R15：2026-02 报道推迟到 iOS 26.5 或 27，实际范围无法确认（§3 Q3、待核实 1） | dim08：Siri AI 2026-09-14 随 iOS 27 发布；EU、中国缺席 | Apple Newsroom 2026-06-08 证实「Siri AI」随 iOS 27 的存在与 EU 缺席；9-14 具体发布日只见 progressivewebapps 单一媒体 | 官方确认：Siri AI 属 iOS 27 一线功能，EU iOS 无时间表。9-14 发布日未核实 | 删「无法确认」，改为官方口径加媒体日期；个人上下文读取侧是否开放第三方仍按 Apple 开发者文档 |
| B4 | 「同一基准不同 harness 分差 45 分」 | §0 第 8 条写 Zep 在 LoCoMo 上 58%–84% | dim07 §2.2 与成稿 sec04：Mem0 在 LongMemEval 厂商 93.4–94.4 对独立论文 49.0%，称差 45 分 | arXiv 2603.04814 摘要不含 49.0%；摘要只说长上下文 GPT-5-mini 在 LongMemEval 与 LoCoMo 上事实召回更高。且两边 reader 模型不同，不是「同一 harness」 | 不可写「同一基准不同 harness 差 45 分」。可写：Mem0 厂商自报 LongMemEval 94.4，另有一次第三方复现 73.8%（Maximem，2026-05，经聚合博客转引，未核实） | 暂不引 45 分；若引 73.8% 须标二手 |
| B5 | 「Kimi 说 12–24 个月窗口」的性质 | §5 MEM-4 反方写「2027 年前可能开放」 | dim08 §4-4 当结论写 | 来源只证明 TSA 被拒，不证明窗口长度 | 窗口长度是 Kimi 判断 | 不引 12–24 个月为事实 |

## C 可消解的待核实

| 我方待核实条目 | 新证据 | 结论 |
|---|---|---|
| 1 Siri 个人上下文上线版本与范围 | Apple Newsroom 2026-06-08（已抓）；上线日期来自媒体 | 部分坐实：属 iOS 27，EU iOS 缺席；个人上下文对第三方的读取范围仍待核实 |
| 2 Mem0 新算法有无独立复现 | Maximem 73.8%（经 mnemoverse 聚合，未核实）；arXiv 2603.04814 摘要不支持 49.0% | 仍待核实，倾向「有第三方复现但数字二手」 |
| 4 Recall GA 时间线 | Kimi dim08 脚注 6、7：2025-04-25 推送（GeekWire）、EEA 2025-07-30 | 未抓一手；倾向坐实，仍待核实 |
| 5 Magic Cue 数据源开关粒度 | Kimi dim08 脚注 19、54：Google 官方博客 2025-08-20 与 Yahoo Tech 引文「可授权日历而不授权消息」 | 部分坐实为逐应用开关（我方未抓，Kimi 单源）；与 Private Compute Core 关系仍待核实 |
| 6 小艺记忆存储位置与删除 | Kimi dim08 脚注 48：小艺帮记本地处理优先，仅向云传结构化结果（搜狐，媒体） | 仍待核实（媒体口径，删除能力无来源） |
| 9 MemoryGraft 二手数字 | Kimi dim07 脚注 42 称 PRP=47.9%（10 毒种/100 良性）；我方抓 arXiv abs，摘要仅说「少量毒记录占大量检索」，无数字 | 方向坐实，数字仍待核实（须读正文）；MINJA 的 NeurIPS 2025 归属 Kimi 单源，仍待核实 |
| 10 PIPL 第 47 条等 | Kimi dim08 脚注 58–60 给了合规审计办法（2025-02-14，网信办）、GB/T 45654-2025、个保法第六条 | 第 47 条本身仍待核实；可补充办法与国标 |
| 13 LangMem、Cognee | Kimi dim07 脚注 7、8：LangMem 为 namespace 隔离加 Prompt Optimizer；Cognee 管线含 permissions 步骤、本地嵌入式栈（均为厂商或聚合博客） | 部分消解（二手），ACL 细节仍待核实 |
| §7.1 MemOS 共享与 ACL「待核实」 | 见 A4，MemOS 论文 §4.2 已核 | 坐实（论文层面） |

## D 立场层面的调整

- **MEM-3 → MEM-3′（结论不变，置信度由「中」升到「中高」）。** Kimi 证据：A1、A2。建议在 MEM-3′ 第二句后加：「权限与禁令类约束不进入摘要，由 OS 在驱逐前钉住保存；摘要生成若处理了低完整性内容，入库记录标注该事实。」§6 J1 驱逐分类规则增一类「治理约束 → 钉住，不摘要」，与已有的「系统提示词、技能前缀不摘要」并列。依据的边界要写明：Governance Decay 测的是文本层 compaction，没有覆盖 KV 层，因此只加强了「文本层可逆、KV 层不做摘要入库」的后半句，没有新证据改 KV 部分。
- **MEM-1′（补元数据，不改方向）。** Kimi 证据：A4、A5。四类元数据（来源、完整性、数据域、版本）可补两项可选字段：生命周期（TTL 或衰减）与归属主体（多方场景下的实体归属）；审计日志已有。同时 MEM-1 的「最强反方证据」第一句「没有一家把记忆 ACL 做进 OS」要加限定：MemOS 在论文层面有完整治理属性（A4），但无 OS 强制，现有表述仍成立。
- **MEM-2′（微调）。** Kimi 证据：A8。第二句「何时检索归 Agent」后，在 OS 职责里补「提供失效标记与版本链原语（invalidate 而非 delete），物理删除可达仍归 OS」。理由：Memora 与 STALE 显示 Agent 自己识别失效不可靠。置信度保持「中高」。
- **MEM-4′（反方证据更新，立场不变）。** Kimi 证据：A6、A7。「最强反方证据」栏把「Apple / Google 可能在 2027 年前开放」改为「欧委会 2026-06 拒绝 Apple 的 Trusted System Agent 中介方案，监管压力真实，但 EU 内开放接口尚未出现」。此外 J4 补一条：FragFuse（A3）说明 ACL 检查点要放在记忆增强之后，与「结果返回路径受约束」合并表述。
- **MEM-3′ 之外的 J1 论据。** insight I-06 把「驱逐是治理检查点」当结论，其中的 provenance、污点标签与我方「原文指针 + 完整性等级」基本重合，可直接借用措辞，但 I-06 里的 FragFuse 和 MemoryGraft 47.9% 分别见 B2 与 C 表，引用前先按此处校正。

## E 不采纳

| 条目 | 原因 |
|---|---|
| AMemBench（arXiv 2609.13767）、OSDN（2607.05475） | CV 标 HALLUCINATED-SUSPECT / UNVERIFIED，按任务说明不采纳 |
| MemexRL MCP 泄漏 34% | 只出现在 CV「Medium」列表；Kimi 的 dim07–09、insight、sec04 里全文搜索无此条，无来源无 URL，无法核验 |
| 端侧 ANN VectorTune 1.4–1.5×（VLDB 2026） | 同上，仅 CV 提及，维度报告无出处；J7 仍缺端侧向量库数据，建议另行检索原论文，不借 Kimi |
| Android ObjectBox、iOS ObjectivePGP | 仅 CV 提及，无来源；ObjectPGP 与向量检索无关，疑似误植 |
| 「45 分」口径 | 见 B4，摘要不支持，且不是同一 harness |
| Context Compaction Theory「agent 无法自我察觉丢失」（dim07 脚注 46） | arXiv 2608.01326 存在（2026-08-02，形式化选择与生成两类 compaction），但摘要不含该论断，需读全文 |
| galahad-kv（50M token KV 落盘，arXiv 2610.10845） | 单一作者加商业包，Kimi 自己标「中、需独立验证」；且属 KV 层，与 MEM-3′ 不合 |
| Claude Code 约 80% 上下文自动压缩（dim07 脚注 48） | 仅 jsmanifest 博客二手 |
| Google PAC 持久化服务器端记忆（dim08 脚注 55） | 仅 Unite.ai 等媒体；若成立会影响 §3 Q3 的「端侧 vs 云」分歧，先留作待核实 |
| Gemini Personal context 默认开启等（dim08 脚注 49–53） | 云账户数据，偏离端侧索引主线；我方 R16/R17 已覆盖授权单位 |
| Letta Sleep-time、Mem0 +26%、DMR 等 | 我方 E23、E3 已覆盖，无新增 |
| 「端侧记忆 × KV 复用统一框架为空白」 | CV 缺口清单里是 Kimi 自认的空白，不是证据 |

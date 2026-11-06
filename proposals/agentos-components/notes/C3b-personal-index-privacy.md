# C3b 端侧个人上下文索引与隐私授权

**子模块**：C3b（记忆 Q3、Q5、Q7、Q8；主责接缝 J4、J7；立场评审 MEM-4 与 MEM-1 的 ACL/共享/授权部分）
**日期**：2026-11-05
**方法说明**：本稿基于联网检索。检索工具返回的多为二手报道与摘要，凡未打开原文核对的数字一律降级为 C 级或标「待核实」。厂商未公开细节处写「未找到公开资料」。引用编号见 §8。

---

## §0 摘要

1. Recall 重发后的架构（VBS enclave、逐快照密钥、Windows Hello 门控、默认关闭、敏感信息过滤）是目前公开资料中最完整的 capture 路线样本，但 2026 年 3—4 月 TotalRecall Reloaded 表明，信任边界终止在「解密后交给的 UI 进程」，enclave 本身未被攻破。微软称其不构成漏洞 [R1, R5, R7]（A/C）。
2. donation 路线（Apple App Intents 实体经 IndexedEntity 进入 Core Spotlight）是文档化的、可授权的第三方入口；capture 路线（Recall、Pixel Screenshots 类）覆盖广但把授权粒度降为「全屏」。判断：两条路线在 OS 层应并存，授权对象不同（R13）。
3. Samsung Personal Data Engine 把知识图谱放在 Knox Vault 并明确只服务三星原生应用、不对第三方开放 [R11, R12]（B/C）。这印证 MEM-4「第三方开放」是空白。
4. Apple 的「个人上下文 Siri」在检索窗口内的公开资料不一致：2026 年 2 月的报道称其被推迟到 iOS 26.5 或 iOS 27，且 26.4 首个 beta 不含相关功能 [R14, R15]（C）。上线现状「待核实」，不能据此断言 Apple 已有成熟的跨应用个人语义索引。
5. Google 路线是「Private Compute Core 隔离 + Private AI Compute 云侧 enclave 兜底」，Magic Cue 的云侧增强和 Gemini Personal Intelligence 的「按应用连接」授权，是目前最贴近 MEM-4 授权粒度的商业先例，但授权单位是「应用级连接」，不是「实体/记录级」[R8, R9, R16, R17]（B/C）。
6. 记忆投毒已有成体系的攻击与防御文献：AgentPoison、MINJA（报告注入成功率 98.2%、最终攻击成功率 76.8%，后续工作称那是理想化条件）、PoisonedRAG、MemoryGraft，加上 ChatGPT/Gemini 的真实记忆注入演示 [R24–R29]（A/C）。2026 年的防御工作结论一致：内容过滤与信任分数对重洗（laundering）和多轮攻击不够，来源绑定（provenance）与架构级隔离更有希望 [R30]（C，预印本）。
7. 因此 MEM-1 里「ACL」必须覆盖写，而不止读；且写入必须携带不可伪造的来源标签。Collaborative Memory 论文的读写双策略加不可变溯源，是最接近的学术设计（R31, C）。
8. 现有框架的共享/隔离模型都很粗：Letta 共享 block 按整块只读/可写、并发为 last-write-wins；Mem0 以 user/agent/app/run 标识划分；LangGraph 以命名空间元组划分 [R32]（A）。没有任何一个提供「按来源数据域」的授权。
9. 合规：EDPB Opinion 28/2024 要求按个案判断模型是否匿名、鼓励便于行使数据主体权利 [R33]；端侧索引的删除是外置存储，技术上比删模型参数容易，但「向量索引、缓存、摘要」多副本要一并清理（判断）。中国侧 PIPL 第 47 条（删除权）依据为法条原文，本稿未打开官方文本，URL 待补。
10. 资源成本公开数据极少。最硬的数据点：EmbeddingGemma 308M 参数，量化后可在 200MB 以内 RAM 运行，输出维度可由 768 截到 128 [R34]（B）；Recall 默认磁盘配额随盘大小 25GB/75GB/150GB [R3, R4]（B/C）。每万条索引体积、建索引能耗在手机上未找到权威公开数据（J7 的最大空白）。

---

## §1 技术谱系表

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| capture：屏幕快照语义索引 | Windows Recall | Microsoft | 2024-05 发布，2024-09 重设计，之后随 Copilot+ PC 推送（具体 GA 时间待核实） | 周期性截屏 + OCR/语义索引，VBS enclave 存储，Hello 门控 | L4（Copilot+ PC 量产）| 需改造：手机无 VBS，对应物为 TEE（TrustZone/pKVM），且电量与存储约束更严 |
| capture：截图/屏幕理解 | Pixel Screenshots、Magic Cue 读取 Screenshots 等 | Google | 2025 | 用户主动截图后做本地检索；Magic Cue 汇集 Gmail、日历、截图、消息 | L4（Pixel）| 已是手机方案；仅 Pixel/Tensor 设备 |
| donation：应用声明实体入索引 | App Intents `IndexedEntity` + Core Spotlight | Apple | iOS 18/26 文档 | 应用主动贡献实体，Core Spotlight 提供词法与语义检索 | L4（API 已发布）| 可借鉴原语：实体声明式贡献 |
| 厂商自建知识图谱（封闭）| Personal Data Engine | Samsung | 2025-01（S25）| 融合多个三星应用数据为知识图谱，存 Knox Vault，仅三星原生应用 | L4 | 只可借鉴；不对第三方开放 |
| 平台隔离域 | Private Compute Core + Private Compute Services | Google | 2021 起 | 无直接网络访问的隔离环境，对外经少量开源 API，联邦分析 | L4 | 已是手机方案 |
| 云侧 enclave 兜底 | Private AI Compute | Google | 2025-11 | 远程证明 + 硬件密封云环境，为 Magic Cue 提供更强模型 | L4（Pixel 10 上线）| 不可迁移到无云依赖场景；路由逻辑可借鉴 |
| 应用级连接授权 | Gemini Personal Intelligence | Google | 2026-01，3 月起扩展到美国免费用户 | 默认关闭、按应用选择连接 | L4（云账户数据，非端侧）| 授权 UX 可借鉴 |
| 系统记忆 + 知识库 | 小艺记忆、Data Augmentation Kit（知识加工、向量库+倒排库、多路召回+重排）| 华为 HarmonyOS | 2024–2026 | 记忆主页保存重要日、卡证、地址、订单等；开发者可构建应用侧知识库 | L3–L4（具体范围待核实）| 同属 HarmonyOS 生态内 |
| 端侧向量存储 | ObjectBox 4.0（HNSW）、HarmonyOS 关系型数据库的向量能力、sqlite-vec | 各厂商/社区 | 2024–2025 | 本地向量检索 | L3 | 直接可用；基准数据缺 |
| 语义授权研究 | AirGapAgent、PrivacyLens、ConfAIde、AgentDAM | 学术 | 2023–2025 | 情境完整性用于约束 Agent 能看到什么 | L1 | 需改造：模型层判断不能替代系统层 ACL |
| 记忆投毒攻击 | AgentPoison、MINJA、PoisonedRAG、MemoryGraft | 学术 | 2024–2025 | 在知识库或记忆里植入触发式或模仿式恶意记录 | L1 | 与平台无关，攻击面迁移到端侧 |
| 记忆投毒防御 | 信任分数与清洗、来源绑定、Memory Sandbox 等 | 学术（2026 预印本）| 2026 | 写时校验、来源标签、工具层移除召回 | L1 | 来源绑定可直接迁移为 OS 机制 |
| 多用户/多 Agent 记忆 ACL | Collaborative Memory；Letta shared blocks；Mem0 作用域；LangGraph namespace | Accenture 等/开源 | 2025 | 读写策略、私有/共享分层、不可变溯源 | L1–L3 | 可迁移（逻辑层）|

---

## §2 关键数据

| 指标 | 数值 | 条件 | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| Recall 硬件基线 | 40 TOPS NPU、16GB RAM、256GB 存储 | Copilot+ PC | Microsoft Support [R2 页面所链] | 2025 | B（搜索摘要转述，待核实） |
| Recall 最低可用空间 | 启用需至少 50GB 空闲；低于 25GB 暂停保存 | Windows 11 | Microsoft Learn [R2] | 2025 | A（经摘要转述）|
| Recall 默认存储配额 | 256GB 盘 25GB（可降 10GB）；512GB 盘 75GB；1TB 盘 150GB | 默认设置 | Pureinfotech [R4] | 2025 | C |
| Recall 25GB 约容纳时长 | 约三个月 | 微软口径 | PCWorld [R3] | 2024 | C |
| Recall 保留期选项 | 30/60/90/180 天或不限 | 企业版和教育版可用策略配置 | ElevenForum / ADMX 镜像（经检索摘要）| 2025 | C |
| Recall 快照加密 | 每快照独立密钥，密钥在 enclave 内，由 TPM 保护并绑定 Windows Hello ESS | VBS enclave | Microsoft 博客 [R1] | 2024-09-27 | B |
| TotalRecall Reloaded | 研究者 Hagenah 于 2026-03-06 向 MSRC 披露；工具向 AIXHost 进程注入 DLL，在 Hello 认证后提取数据；微软称属于「设计内行为」 | Windows 11 Recall | Verge 镜像 [R5]、Neowin [R7] | 2026-03/04 | C |
| MINJA | 注入成功率 98.2%，攻击成功率 76.8% | 查询级交互、无直接写记忆权限；后续工作称为理想条件 | arXiv 2503.03704 [R25]（经检索摘要）| 2025-03 | A/C（数字待对原文核对）|
| PoisonedRAG | 每个目标问题注入 5 条恶意文本，百万级文本库上攻击成功率约 90%；NQ 黑盒 97% | RAG 知识库 | USENIX Security 2025 [R27] | 2025-08 | A |
| 个人数据泄露率 | PrivacyLens 上 GPT-4o 泄露率 33.06%，加 PrivacyChecker 降至 8.32%；AgentDAM 上 36–46%，CoT 隐私提示降至 6–8% | 各基准 | arXiv 2509.17488 及 AgentDAM 页面 [R24] | 2025 | C |
| AirGapAgent 效果 | 上下文劫持下，基线 94% 降到 45%，AirGapAgent 保持 97% | 其自建基准（未公开，后由 AirGapAgent-R 重建）| arXiv 2405.05175 [R22] | 2024 | A（自评）|
| EmbeddingGemma | 308M 参数；量化后 RAM 低于 200MB；输出维度 768 可截至 128；上下文 2K | Gemma 3 系 | Google AI for Developers [R34] | 2025-09 | B |
| ObjectBox 向量检索 | HNSW，不要求全部向量常驻内存；开源基准「coming soon」 | 厂商口径 | ObjectBox [R35] | 2024 | B（无独立实测）|
| 每万条记录索引体积、后台建索引能耗、更新延迟 | 未找到公开权威数据 | — | — | — | — |

估算（标「估算」，非来源数据）：768 维 float32 每向量 3072 字节，一万条约 30.7MB；截到 256 维并 int8 量化约 2.6MB 每万条；仅向量部分，不含 HNSW 图和元数据。一部手机若有 50 万条消息、照片、通知级实体，768 维 float32 约 1.5GB，说明维度截断和量化在端侧不是可选项。

---

## §3 逐问题分析

### Q3 端侧个人数据索引

**3.1 Windows Recall：架构与风波复盘**

时间线（来源不均，已标注）：

- 2024-05 发布，计划随 Copilot+ PC 推出。早期版本被安全研究者指出快照库明文存放（TotalRecall 首版，2024-06 报道，R7 一类二手来源，C）。
- 2024-06 微软推迟发布，改为预览。
- 2024-09-27 微软发布重设计说明（B，R1）：默认关闭、需要主动开启；Windows Hello ESS 生物识别门控；快照与向量库放入 VBS enclave；每个快照单独加密，密钥由 TPM 保护并绑定 Hello 身份；敏感信息过滤（密码、证件号、银行卡）和私密浏览默认过滤；可卸载；经过内部红队和第三方渗透测试。
- 之后分阶段向 Copilot+ PC 推送，具体 GA 日期本次未核实。
- 2026-03-06 研究者 Hagenah 向 MSRC 披露 TotalRecall Reloaded，2026 年 4 月前后被多家媒体报道（C）。他的论点是 enclave 本身牢固，但信任边界终止过早：认证后，数据交给 enclave 之外的 UI 进程（AIXHost），而那个进程可被注入。微软的回应是这属于文档化的安全设计，不是边界绕过 [R5]。
- Brave、Signal、AdGuard 等加入阻止 Recall 截取的功能：仅有一个二手来源，细节未核实。

分析：这件事里，「存储安全」做对了，「使用安全」没做完。快照被取出展示给 UI 的那一刻，数据从 enclave 的保护域进入普通用户态进程，同一用户权限下的恶意程序可以走同一条路。同时，Recall 的授权单位是「整个功能开或关」加「过滤规则」，没有「某应用/某类内容不进索引」的第三方可声明机制，所以才出现 Signal、Brave 自己去阻止被截图。这是 capture 路线的结构性代价：被采集的应用没有话语权。

挂钩我方（SBX/MEM 立场）：事件复盘需回答「我方哪条立场能挡住，缺口是什么」。

| 事件 | 能挡住的我方立场 | 缺口 |
|---|---|---|
| Recall 明文库（2024）| MEM-1（OS 托管存储与 ACL，库不由应用自管）| 未覆盖加密与密钥归属，需补「索引静态加密、密钥不出 TEE」|
| TotalRecall Reloaded（2026）| MEM-1 的 ACL 若把「读结果的渲染进程」也纳入主体 | 立场未规定「解密后数据的接收方也必须是受约束主体」；需补「返回路径同样受 ACL，且结果带水印/审计」|
| 第三方应用被动被截 | MEM-4 的细粒度授权 | 立场只讲 Agent 读索引，未讲「应用可对自己的内容声明不入索引」（排除权）|

**3.2 Apple：语义索引与 App Intents 实体**

事实（A）：App Intents 文档说明，实体类型只需遵循 `IndexedEntity` 即可进入 Spotlight；已使用 Core Spotlight 的应用可直接加入实体；Core Spotlight 支持词法与语义检索 [R13]。这是 donation 路线的官方机制：应用决定贡献什么、以什么 schema。

状态（C，需谨慎）：Siri「个人上下文」本应能在备忘录、短信、邮件中定位信息 [R14]。2026 年 2 月的报道称首个 iOS 26.4 beta 不含相关功能，并有消息称推迟到 iOS 26.5 或 iOS 27 [R15]。另一来源称最终上线的范围小于最初承诺，且多数 App Intents 初期只对 Apple 自家应用生效。本次检索没有找到 Apple 官方发布说明确认实际上线内容。判断：不能把 Apple 视为已完成跨应用个人语义索引的对象。

Apple 的隐私保障（Private Cloud Compute 等）归 C1b 的端云路由，不在本稿展开。

**3.3 三星 Personal Data Engine**

PDE 用知识图谱融合多个三星应用的数据，存放于 Knox Vault，数据留在设备上，关闭「个人数据智能」菜单后分析数据删除；明确仅限三星原生应用，不适用于第三方；Now Brief 需要三星账号登录；后续 Knox Enhanced Encrypted Protection（KEEP）扩展保护范围 [R11, R12]。证据等级：B（厂商）+C（媒体）。知识图谱技术来自 Oxford Semantic Technologies（媒体转述，C）。PDE 的实体 schema 与授权粒度未找到公开资料。

**3.4 Google：Magic Cue、Pixel Screenshots、Private Compute Core、Gemini 个人上下文**

- Private Compute Core（2021 年起）：与系统其余部分隔离、无直接网络访问，对外经 Private Compute Services 的少量开源 API，使用联邦分析、联邦学习等 [R10]（C，来源是 2021 年报道，非 source.android.com 文档）。
- Magic Cue（Pixel 10）：跨 Gmail、日历、Screenshots、Messages 等给出上下文建议；2025-11 起使用 Private AI Compute 做云侧增强，同时仍有 Gemini Nano 在端侧 [R8, R9]（B/C）。Private AI Compute 用远程证明和加密连接到硬件密封的云环境。检索没能确认 Magic Cue 的数据是否仍落在 Private Compute Core 内，两者关系「待核实」。
- Gemini Personal Intelligence（2026-01 推出，3 月起面向美国免费用户）：默认关闭，用户逐个选择连接 Gmail、Photos、YouTube 等；Google 称不直接用收件箱/相册训练，但提示和回复可用于训练 [R16, R17]（B/C）。注意这是云账户数据，不是端侧索引。

**3.5 HarmonyOS**

- 小艺记忆（HarmonyOS 4.2 页面，称 HarmonyOS 5 已升级）：记录重要日、卡证、地址、订单、事件，自动从对话记录兴趣、职业，以摘要形式存于记忆主页 [R18]（B）。底层是否为端侧向量库、数据是否仅在端侧：未找到公开资料。
- 数据增强套件（Data Augmentation Kit）：官方文档列出 AIP 与 Retrieval 两个模块 [R19]；开发者博客描述的链路为知识加工生成向量库和倒排库，多路召回加重排，再交给大模型（C，博客）。这是面向应用的知识库构建能力，不是系统级统一个人索引。
- 关系型数据库的向量能力：有开发者文章介绍 ArkTS 与 C++ 两种接口 [R20]（C）。官方文档名称与版本需对照 developer.huawei.com 核实。
- 2026 年 7 月有宣传性新闻称复杂任务才按需调用云端，并通过个人智能计算系统把隐私保护延伸到云端（C，未独立验证）。

**3.6 国内其他厂商**

- OPPO 与 Google Cloud 在 2026 年 1 月提出以「记忆共生」和「隐私保护」为核心的 AIOS 构想 [R21]（B，是构想而非产品规格）。
- 荣耀、vivo、小米的「个人记忆」功能实现方式、是否端侧存储、用户能否查看或删除：本次检索未找到公开资料。有报道称 2026 年 7 月首批 7 款手机端侧 AI 服务完成备案，且部分手机隐私政策中对无障碍权限说明不够清晰（C，来源不明确）。
- 判断：国内厂商在「抓取」路线上依赖无障碍等系统权限的可能性高，但本稿没有证据，列为资料空白。

**3.7 donation 与 capture 对比**

| 维度 | donation（App Intents/IndexedEntity）| capture（Recall、截图、无障碍）|
|---|---|---|
| 数据覆盖 | 仅限接入的应用，覆盖随生态增长 | 屏幕可见的一切，包括未接入应用 |
| 结构化程度 | 高（实体 schema）| 低（OCR 文本、像素）|
| 授权粒度 | 可到实体类型，应用端可控 | 一般为功能开关加过滤规则 |
| 被采集方话语权 | 有（应用自己决定贡献）| 无，需靠应用自己去阻止（FLAG_SECURE、被动过滤）|
| 敏感内容风险 | 取决于应用 | 高：密码、验证码、聊天都会被看到 |
| 冷启动 | 慢，需应用适配 | 快，装上就有 |
| 防投毒 | 来源明确（谁贡献的）| 来源是屏幕内容，任何网页文字都可进入 |

判断：capture 的覆盖优势是真实的，但授权和防投毒上先天弱；donation 覆盖受制于生态。OS 层方案应以 donation 为主路径，capture 作为受限兜底（需用户逐应用/逐场景开启，且被采集应用有排除权）。

**3.8 Picker 式授权先例**

- Android 14 的部分媒体访问：把图片、视频读取合并为 `READ_MEDIA_VISUAL_USER_SELECTED`，弹窗出现「选择照片」，应用只能访问用户选的条目；Google 建议大多数应用使用无需权限的 Photo Picker [R36]（A/B）。
- iOS 有限照片访问、iOS 18 的有限联系人访问与 Contact Access Button、Share sheet：本次检索未取回原文，作为已知先例列入但标「待核实原文」。
- 这类授权的共同特点：授权单位是「条目集合」，由 OS 渲染的选择器完成，应用拿不到未选条目。判断：这正是 MEM-4「细粒度授权」可以直接继承的 UX 与权限模型，但它们解决的是「应用读一批具体对象」，不是「Agent 对整个索引做开放式语义查询」。后者需要查询时授权（query-time grant）而不是对象枚举时授权，现有 Picker 先例不覆盖。

**3.9 情境完整性类研究**

- AirGapAgent（arXiv 2405.05175）：为每个任务把 Agent 可见的数据限制到所需字段，在上下文劫持攻击下保持约 97%（自评，原基准未公开）[R22]。
- PrivacyLens（arXiv 2409.00138）、ConfAIde：评测语言模型在行动中的隐私规范意识；泄露率在 GPT-4o 上约三分之一，需要额外检查器才降到约 8% [R23, R24]。
- AgentDAM：网页 Agent 泄露率 36–46%，提示级缓解降到 6–8%。
- 局限与分歧：这些方法把判断放在模型里或模型前的过滤器里，输出是概率性的；OS 层需要的是确定性的 ACL。两者的合理关系是：ACL 做硬边界（谁能读哪个数据域），情境完整性做软边界（同一数据域内，某次披露是否适合当前任务）。J8 的「隐私标签由谁产生」是它们的接口。

**这说明什么**：个人索引的三个商业先例（Recall、PDE、Magic Cue）都停在「自家应用/自家模型可用」，没有一个提供「第三方 Agent 带着授权查询个人语义索引」的开放接口；donation 是唯一有文档化第三方入口的路线，但其最关键的 Siri 个人上下文在检索窗口内未能确认上线。MEM-4 的「最大生态空白」判断成立，但需要加限定：空白在「开放 + 细粒度 + 跨应用」三者同时满足，而不是「没人做个人索引」。

### Q5 隐私与合规

**5.1 TEE、差分隐私、联邦学习的落地**

| 技术 | 落地实例 | 保护对象 | 局限 |
|---|---|---|---|
| 设备侧硬件隔离存储 | Knox Vault（PDE）[R12]；Recall 的 VBS enclave + TPM [R1] | 静态数据与密钥 | 解密后的使用路径是新边界（Recall 复盘）|
| 隔离计算域 | Private Compute Core [R10] | 处理中的数据与网络出口 | 文档为 2021 年二手资料，近年细节待核实 |
| 云侧机密计算 | Google Private AI Compute（远程证明、TPU 与 Titanium Intelligence Enclaves）[R8]；Apple PCC、Meta Private Processing（归 C1b）| 上云时的数据 | 信任根仍是厂商 |
| 联邦分析/学习 | Private Compute Services 使用联邦分析、联邦学习、私有信息检索 [R10] | 改进模型时不上传原始数据 | 与个人索引的检索无关，主要是模型/统计侧 |
| 差分隐私 | 本次检索未找到个人索引场景的落地资料 | — | 未找到公开资料 |

判断：个人索引的主力隐私技术是「设备侧 TEE + 不出端」，不是差分隐私或联邦学习；后两者服务于模型改进与统计，不是索引检索本身。

**5.2 合规**

- GDPR：EDPB Opinion 28/2024（2024-12-17 通过）认为训练过个人数据的模型不能一概视为匿名，需个案评估，并鼓励开发者便于数据主体行使权利（如无条件退出、对记忆化做反学习）[R33]（B）。这针对模型参数；端侧记忆索引是外置存储，删除逻辑更接近数据库。判断：记忆框架应当把「删除」设计成一等原语，覆盖原文、向量、图、摘要、缓存、导出副本五类副本；任何摘要或派生物必须能追溯到来源记录，否则无法兑现删除权。
- EU AI Act：本次未检索，未找到可引用资料，列入待核实。
- 中国：PIPL 第 47 条规定删除权，学术文章讨论了大模型中的定位难、效果难验证等问题，并主张用「等效性」标准认定删除结果 [检索所得学术摘要，法律原文 URL 待补]。《生成式人工智能服务管理暂行办法》与 2025 年的相关标准实践指南本次未检索到条文，待核实。
- 一个实务点（C，非官方）：先屏蔽访问，再逐存储删除，仅在监管或风险要求时才对模型做反学习。

**5.3 可见、可删、可导出**

- 商业助手现状（均为二手，C）：ChatGPT 的记忆可在设置中查看管理，删除来源聊天不会删除记忆；Claude 的记忆可查看、编辑、删除单条，Anthropic 帮助中心称其导入/导出功能为实验性 [R38]；有批评指出缺少变更历史和「来源对话」链接（单一来源，待核实）。
- 端侧：三星 PDE 关闭菜单即删除分析数据 [R11]；Recall 可卸载、可设保留期；小艺记忆有记忆主页展示 [R18]。
- 判断：「可见」目前普遍做到条目级，「可删」做到条目级，「可导出」和「来源可追溯」最弱。而来源可追溯恰好同时服务合规（删除要追溯派生物）和防投毒（回溯污染源）。这是 OS 记忆层应作为基础字段提供的元数据。

**5.4 多 Agent 共享记忆的权限模型先例**

| 系统 | 作用域/共享单位 | 读写区分 | 并发/冲突 | 来源与审计 |
|---|---|---|---|---|
| Letta shared memory blocks [R32] | 一个 block 挂到多个 agent | 只读按整块设置，不能对部分 agent 只读 | 并发写 last-write-wins，官方列为反模式 | 未找到公开资料 |
| Mem0 [R32] | user_id、agent_id、app_id、run_id，保存和检索需至少一个标识 | 作用域由过滤条件表达，未见按角色的读写 ACL | 记录有单一主实体；组合 AND 返回空 | 未找到公开资料 |
| LangGraph store [R32] | 命名空间元组，前缀匹配 | 命名空间即隔离，无细粒度 ACL | 取决于后端存储 | 未找到公开资料 |
| Collaborative Memory（ICML 2025 列出，arXiv 2505.18279）[R31] | 私有碎片 + 选择性共享碎片；用户-Agent-资源二部图编码动态权限 | 读策略返回过滤视图；写策略可决定保留、共享或变换 | 不可变溯源（贡献 Agent、访问资源、时间戳）| 有 |

判断：工业框架的隔离是「命名空间 = 租户」，没有「数据域继承」；学术先例引入了读写策略和溯源，但没有与 OS 权限系统（应用权限、沙箱策略）对接。MEM-1 的 ACL 若要继承沙箱权限，需要定义「记忆条目的标签从哪里来」：一个合理做法是写入时继承写入者的会话权限与数据来源域，读取时按读者当前权限与条目标签做交集（判断，非业界现成做法）。

**这说明什么**：合规与监督界面的共同需求是「来源可追溯 + 派生物可级联删除」，业界商业产品只做到了条目级；多 Agent 共享的学术先例有但没落地到 OS 权限，MEM-1 在这里有设计空间也有风险。

### Q7 记忆安全（J4）

**7.1 攻击谱系**

| 攻击 | 注入方式 | 持久化位置 | 要点 | 证据 |
|---|---|---|---|---|
| AgentPoison（arXiv 2407.12784；会议为 NeurIPS 2024 的说法来自二手来源，待核实）| 向 RAG/记忆库植入触发式后门文档 | 向量库 | 声称无需微调模型 | 二手摘要，C |
| MINJA（arXiv 2503.03704；NeurIPS 2025 与 ICLR 2026 页面均有列出，会议归属待核实）| 仅通过查询交互注入，无需直接写记忆 | Agent 记忆库 | 注入成功率 98.2%，攻击成功率 76.8%（理想条件）| A/C |
| PoisonedRAG（USENIX Security 2025）| 向知识库注入少量文本 | 知识库 | 5 条恶意文本即可达约 90% 成功率；所测防御不够 | A |
| MemoryGraft（arXiv 2512.16962，2025-12）| 在 README 等表面文件植入「成功经验」，Agent 模仿 | 经验检索池 | 持久化直到人工清除；摘要称不到 10% 的投毒记忆占后续检索约 48%（二手，待核实）| C |
| ChatGPT 记忆注入与 spAIware（Rehberger，2024-05/09）| 不可信文档、图像、网页触发记忆工具写入 | 产品记忆 | 跨会话持久；macOS 应用 1.2024.247 缓解外泄向量 | C（媒体转述）|
| Gemini 延迟工具调用（Rehberger，2025-02）| 文档里埋「当用户说 X 时调用工具」| Gemini 长期记忆 | 绕过「解析文档时不执行」；Google 评估概率与影响低 | C [R29] |

共同机理：记忆把一次性的间接注入变成持久化注入；写入通道往往没有权限检查，因为「记住」被视为 Agent 的内部行为；检索时恶意记录与可信记录混在一起，没有来源区分。

**7.2 防护**

2026 年预印本（C，均为预印本，未经评审）：

- 信任分数 + 记忆清洗（衰减、模式过滤）：阈值难校准，要么全拦要么漏掉隐蔽攻击（arXiv 2601.05504）[R30]。
- 写入时来源绑定 + 佐证后提升（arXiv 2606.24322）：作者称现有防御的「重洗」攻击成功率最高 68%，该构造为 0%（作者自评）。
- Memory Sandbox（arXiv 2605.08442）：工具层移除召回能力，九个模型中八个攻击成功率降到 0%，一个推理模型反而升到 100%。
- 写时一致性检查能压制直接攻击但压制不了多轮攻击；另有 MPBench 等基准指出现有提示注入防御覆盖不到记忆投毒（以上来自检索摘要，原文未逐一核对）。

判断：内容检测类防御（分类器、一致性）在对抗场景下不可靠；稳健的方向是来源与能力两类结构性控制：
1. 每条记忆带不可伪造的来源标签（写入者身份、会话、数据域、是否含不可信内容）；
2. 写入授权：来自不可信内容（网页、邮件、第三方工具返回）的会话，写记忆需用户确认或进入隔离区，隔离区的记忆不参与高权限动作的上下文；
3. 读取时按来源分层，并把「危险动作的参数」与记忆来源解耦（与 CaMeL/FIDES 等信息流控制同思路，归 C2b）。

**对 MEM-1 ACL 的含义**：只管读不够。读 ACL 保护机密性，写 ACL 保护完整性，而持久化注入是完整性问题。这要求 OS 记忆层提供：写入主体鉴别、来源标签、隔离区、回滚/快照（对应 undo）。这与沙箱 SBX-7「跨链不升级」自然对接：低完整性主体写入的记忆，在读取时降为低完整性数据（判断）。

**事件复盘（J4）**

| 事件 | 日期 | 攻击链 | 能挡住的我方立场 | 缺口 |
|---|---|---|---|---|
| ChatGPT 记忆注入/spAIware | 2024-05/09 | 不可信内容 → 记忆工具写入 → 跨会话外泄 | MEM-2 把「记什么」归 Agent，本身挡不住；需 SBX-7、SBX-8（写入需权限、外泄需出口代理）| MEM-2 与 MEM-1 之间缺「写入授权」条款 |
| Gemini 延迟工具调用 | 2025-02 | 文档埋触发条件 → 用户说话触发 → 写长期记忆 | SBX-4 参数化权限、SBX-6 调用时检查 | 触发式延迟执行需要「调用时重验来源」，立场未写 |
| MemoryGraft 类模仿式 | 2025-12 | 表面文件植入「成功经验」 | 来源标签 + 隔离区（MEM-1 需新增）| 当前立场无对应机制 |

**这说明什么**：记忆投毒是 J4 的核心，防护的主战场不在检测，而在把来源与写入权限做进 OS 记忆层的数据模型。

### Q8 端侧索引资源成本（J7）

**8.1 嵌入模型常驻**

- EmbeddingGemma：308M 参数，量化后 RAM 低于 200MB，支持 Matryoshka 截断到 128 维，上下文 2K [R34]。证据 B。这是目前能查到的最明确的端侧嵌入常驻数据点。注意 200MB 是模型运行内存，不含索引和运行时开销（判断）。
- 其他端侧嵌入模型（MiniLM 类、BGE-small 类）的手机实测内存/延迟：本次未检索，列待核实。
- 系统化问题：嵌入模型是否常驻，决定了查询延迟与内存。16GB 手机上 200MB 常驻代价尚可，8GB 机型与大模型 KV 竞争时需要可回收（对应 C4b 的模型内存域）。选项：事件驱动加载 + 空闲驱逐，换取首次查询延迟。

**8.2 索引体积**

估算见 §2。关键点：向量占比取决于维度与量化；原文、OCR 文本、元数据、图像缩略图往往远大于向量本身。Recall 的配额（25GB 约三个月，B/C）说明 capture 路线的存储主要由原始快照主导，不是向量 [R3, R4]。判断：手机 UFS 有写入寿命约束，capture 路线应只保留文本与向量，不保留原图，或设很短保留期。

**8.3 后台建索引能耗**

未找到手机上建索引的公开能耗数据。Recall 要求 40 TOPS NPU 的 Copilot+ PC（A/B）说明微软认为需要专用 NPU 才能让后台建索引的功耗可接受（判断）。端侧替代做法：仅在充电且空闲时批量建索引，增量更新按事件触发；对 capture 路线则是屏幕变化检测触发，避免固定频率截屏。

**8.4 端侧向量存储引擎**

- ObjectBox 4.0 自称首个端侧向量数据库，HNSW，称不要求全部向量常驻内存、可借助多层缓存落盘；开源基准未发布 [R35]（B，厂商口径）。
- HarmonyOS 关系型数据库提供向量能力（ArkTS/C++ 接口）[R20]（C）。
- sqlite-vec：本次检索无结果，不作结论。
- Apple 侧：Core Spotlight 提供语义检索 [R13]；底层向量实现未找到公开资料。
- 一般判断：HNSW 的随机访问对 UFS 不友好，量级大时倒排 + 量化向量（IVF/PQ 类）更省内存，但没有手机实测支撑，待做仿真或真机测试。

**这说明什么**：J7 在公开资料里几乎是盲区，只有嵌入模型体积一个硬数据点。这既是立项差异化机会（用负载建模与仿真先占位），也是风险：MEM-4 的「统一语义索引」若没有成本模型，无法证明 OS 常驻是合理的。

---

## §4 趋势判断

**正在收敛的方向**
- 个人数据索引必须本地加密存储、默认关闭、可删除（Recall、PDE、Gemini PI 均如此）。
- 授权趋向「按应用/按数据源选择连接」，而不是一次性全权限。
- 重推理上云时用远程证明的机密计算兜底（Private AI Compute、PCC）。
- 防投毒研究收敛到「来源绑定 + 写入控制」，而非内容检测。

**公认的空白点**
1. 面向第三方 Agent 的、查询时授权的统一个人语义索引接口：未找到任何厂商的公开产品。
2. 被采集方的排除权（应用声明自己的内容不入索引）：Recall 事件中由应用自行阻止，OS 无标准机制。
3. 记忆条目级的来源标签与跨副本级联删除。
4. 索引资源成本的公开基准（体积、能耗、延迟）。
5. 解密后返回路径的受约束渲染（Recall 的信任边界教训）。

**仍有分歧的问题**
- capture 与 donation 谁是主路径：覆盖优势对生态依赖。
- 判断放在模型层（情境完整性）还是系统层（ACL）：本稿判断两者分层并存。
- Recall 是否算「被攻破」：微软称否，研究者称边界太早结束；本稿判断为使用路径设计缺陷，不是存储缺陷。
- 个人上下文放端侧还是云：Gemini PI 以云账户数据实现，Pixel/Apple/三星强调端侧，华为强调端云协同。

---

## §5 立场评审表

| 立场 ID | 判断（支持 / 挑战 / 需修订） | 关键证据 | 最强反方证据 | 修订建议 | 置信度 |
|---|---|---|---|---|---|
| MEM-4 | 支持，但需限定与细化 | 三星 PDE 明确仅限原生应用 [R11]；Recall 无第三方授权 [R1]；Apple 个人上下文推迟且早期 App Intents 多限自家应用 [R14, R15]；Gemini PI 授权单位是应用级 [R17] | (a) Apple IndexedEntity + Core Spotlight 已是文档化的第三方 donation 入口 [R13]，空白没有表述得那么大；(b) 厂商封闭索引可能是刻意的商业与安全选择，开放接口的需求方（第三方 Agent）规模未知；(c) Apple/Google 若在 2027 年前开放，空白可能被占 | 把「最大生态空白」改写为「开放 + 查询时授权 + 跨应用 + 来源可追溯」四者同时满足的空白；增加被采集方排除权；评估 donation 优先、capture 受限兜底 | 中 |
| MEM-1（ACL） | 需修订 | 投毒文献与 Gemini/ChatGPT 实例说明写入是攻击面 [R25–R30]；Collaborative Memory 设计读写双策略与溯源 [R31] | Letta、Mem0 等已在应用层做隔离，不需要 OS 介入；OS 级 ACL 的价值需证明 | ACL 明确含写权限、来源标签、隔离区、回滚；ACL 主体包含「结果接收进程」；条目标签从沙箱会话权限与数据来源域继承 | 中 |
| MEM-1（共享） | 需修订 | Letta 共享 block 无细粒度只读、并发 last-write-wins；Mem0/LangGraph 以命名空间隔离 [R32] | 简单命名空间已被大量应用使用，复杂 ACL 可能过度设计 | 共享应采用「标签交集」模型而非「命名空间 = 租户」，并提供冲突策略（版本化，而不是 last-write-wins）| 中 |
| MEM-1（OS 托管存储与索引） | 部分挑战 | 本次未找到手机上 OS 托管统一记忆存储的出货先例，仅 Spotlight、PDE 等厂商自用 | 厂商自建封闭（PDE）是产业现实 | 把「OS 提供机制」限定为索引/ACL/审计原语，不承诺统一 schema | 低 |

反方证据检索范围：Apple/Google/三星/微软官方与媒体报道、Rehberger 系列、arXiv 2026 防御预印本。未找到「OS 级统一个人语义索引已成功量产且向第三方开放」的反例，也未找到「该方向被明确否定」的资料。

---

## §6 接缝发现

**J4（记忆的写入授权与投毒，本组件主责）**
- 记忆作为持久化注入载体的攻击已有完整谱系 [R25–R30]。
- 读写 ACL 从沙箱继承的内容：写入主体身份与会话、会话是否接触不可信内容（完整性等级）、数据来源域。记忆条目携带这些标签，读取时降级使用（判断）。
- 对 C2b：SBX-7 的「权限只减不增」应扩展到记忆路径（低完整性写入不得在后续会话里变成高完整性输入）。
- 对 C3a：MEM-2 把写入策略归 Agent 与 MEM-1 的写入授权需划清：Agent 决定「想记什么」，OS 决定「允不允许写、标什么来源」。

**J7（语义索引的常驻成本，本组件主责）**
- 仅有 EmbeddingGemma 的 200MB 级数据点 [R34] 和 Recall 的存储配额 [R3, R4]。
- 建索引能耗、手机端向量引擎基准：未找到公开资料。
- 对 C4a/C4b：嵌入模型应纳入模型内存域管理（可驱逐、可按事件加载）；索引文件属于文件页，需要记账归属到「记忆服务」而不是各应用。
- 对 C1：嵌入模型是否由推理系统服务统一提供，避免每个应用自带一份。

**J8（协同）**：情境完整性研究提供的是软判断；数据敏感度标签的来源应是记忆条目的数据域标签（确定性），模型只补充（判断）。

**J1（协同）**：摘要入库产生的派生记忆必须保留来源指针，否则无法级联删除，也无法回溯投毒；与 C3a 对齐。

---

## §7 组件特有输出：端侧个人语义索引的空白点清单与差距分析

### 7.1 差距矩阵

比较对象：Apple（Core Spotlight + App Intents，个人上下文状态待核实）、三星 PDE、Windows Recall、Pixel Magic Cue、HarmonyOS（小艺记忆 + 数据增强套件）。MEM-4 目标列为我方设想。

| 维度 | Apple | 三星 PDE | Windows Recall | Pixel Magic Cue | HarmonyOS | MEM-4 目标 |
|---|---|---|---|---|---|---|
| 数据覆盖 | 接入 App Intents 的应用实体 + 系统应用；Siri 个人上下文范围待核实 | 三星原生应用（含 Now Brief 等）[R11] | 屏幕所见 [R1] | Gmail、日历、Screenshots、Messages 等 Google 应用 [R9] | 对话与系统信息（卡证、订单、地址等）[R18]；应用侧知识库 | 系统应用 + 第三方实体 + 受限屏幕兜底 |
| 索引方式 | Core Spotlight 词法 + 语义 [R13] | 知识图谱 [R11] | OCR/语义索引 + 向量库，在 enclave [R1] | 端侧 Gemini Nano + 云增强 [R8, R9]；索引形态未找到公开资料 | 向量库 + 倒排库 + 重排（应用侧）[R19] | 多形态（文本/向量/图），统一元数据 |
| 授权粒度 | 实体类型由应用声明；对 Siri 的读授权细节未找到公开资料 | 功能级开关（关闭即删除）[R11] | 功能开关 + 过滤 + 保留期；Hello 门控 [R1] | 应用级（Magic Cue 的数据源开关细节待核实）| 未找到公开资料 | 查询时授权，实体/数据域/任务三级 |
| 第三方开放 | 部分（IndexedEntity 供应用贡献；读取侧限 Siri/系统）| 否 [R11] | 否（无第三方读取接口，已知公开资料）| 否 | 部分（数据增强套件面向应用自建知识库，不是读取系统级索引）| 开放 |
| 跨应用 | 受限（实体 donation 后系统检索）| 限三星应用之间 | 是（跨一切屏幕内容）| 限 Google 应用 | 系统级部分 | 是 |
| TEE | Secure Enclave、PCC（索引本身是否 TEE 保护：未找到公开资料）| Knox Vault [R12] | VBS enclave + TPM [R1] | Private Compute Core [R10]；云侧 Titanium Intelligence Enclaves [R8] | 个人智能计算系统（宣传口径，待核实）| TEE 内索引与查询，结果受约束渲染 |

### 7.2 空白点清单（按优先级，带证据状态）

1. **面向第三方 Agent 的开放读取接口**：所有对比对象均无。证据：R11、R1，Apple 状态待核实。
2. **查询时授权**（按任务与数据域授权，而非枚举对象或开关功能）：Picker 先例不覆盖开放式查询 [R36]；Gemini PI 为应用级 [R17]。
3. **被采集方排除权**：Recall 事件中由 Signal、Brave 等自行阻止（单一来源，待核实）。
4. **来源标签与级联删除**：商业产品只到条目级；学术有 Collaborative Memory 的不可变溯源 [R31]。
5. **写入完整性与隔离区**：投毒文献 [R24–R30]；无商业产品公开机制。
6. **结果返回路径受约束**：TotalRecall Reloaded 教训 [R5]。
7. **资源成本基准**：J7，几乎无数据。
8. **国内厂商个人记忆的公开机制**：荣耀、vivo、小米、OPPO 的实现、存储位置、删除能力均未找到公开资料。

### 7.3 与最接近实现的差距

- 与 Apple：最接近的机制层（IndexedEntity）。差距在于读取侧开放（第三方 Agent 无法读系统索引）与查询时授权。Apple 个人上下文的实际上线情况必须在定稿前核实。
- 与三星 PDE：TEE 与端侧留存做得最扎实（Knox Vault），差距在封闭。
- 与 Recall：覆盖最广，安全工程最透明，差距在授权粒度（功能级）、被采集方无话语权、结果路径。
- 与 Magic Cue：产品化最成熟的端云混合，差距在授权粒度未知、第三方数据不可见。
- 与 HarmonyOS：已有系统记忆与应用侧向量/知识库，差距在没有统一的系统级跨应用索引，且公开资料对授权和 TEE 缺乏说明。

---

## §8 参考资料与待核实清单

### 参考资料

| 编号 | 标题 | 机构/作者 | URL | 日期 |
|---|---|---|---|---|
| R1 | Update on Recall security and privacy architecture | Microsoft Windows Experience Blog | https://blogs.windows.com/windowsexperience/2024/09/27/update-on-recall-security-and-privacy-architecture/ | 2024-09-27 |
| R2 | Manage Recall | Microsoft Learn | https://learn.microsoft.com/windows/client-management/manage-recall | 未标注 |
| R3 | Windows Recall has one big gotcha | PCWorld | https://www.pcworld.com/article/2339032/windows-recall-has-one-big-gotcha-and-its-not-privacy.html | 2024 |
| R4 | How to change Recall space allocation | Pureinfotech | https://pureinfotech.com/change-space-allocation-recall-windows-11/ | 未标注 |
| R5 | Microsoft faces fresh Windows Recall security concerns（访问的是镜像）| The Verge（镜像：hn.jakechampion.name）| https://hn.jakechampion.name/reader/https://www.theverge.com/report/912101/microsoft-windows-recall-new-security-concerns-response | 2026-04 前后 |
| R6 | One year after its rocky launch, Windows Recall still raises security red flags（未能打开，403，仅引标题）| GeekWire | https://www.geekwire.com/2026/one-year-after-its-rocky-launch-microsofts-windows-recall-still-raises-security-red-flags/ | 2026 |
| R7 | Windows 11's controversial Recall is under fire again | Neowin | https://www.neowin.net/news/windows-11s-controversial-recall-is-under-fire-again-while-microsoft-denies-flaws/ | 2026 |
| R8 | Google Private AI Compute（Pixel）| 9to5Google | https://9to5google.com/2025/11/11/google-private-ai-compute-pixel/ | 2025-11-11 |
| R9 | Google upgrades Magic Cue with Gemini models | Digital Trends | https://www.digitaltrends.com/phones/google-just-upgraded-magic-cue-on-your-pixel-10-with-advanced-gemini-models-without-compromising-privacy/ | 2025-11 |
| R10 | Android Private Compute Services | 9to5Google | https://9to5google.com/2021/09/09/android-private-compute-services/ | 2021-09-09 |
| R11 | Samsung's Personal Data Engine | Tom's Guide | https://www.tomsguide.com/phones/samsung-phones/samsungs-personal-data-engine-is-a-big-addition-to-the-galaxy-s25-heres-why | 2025-01 |
| R12 | Your Privacy, Secured: Inside the Tech Powering More Secure, Personalised Galaxy AI Experiences | Samsung Newsroom UK | https://news.samsung.com/uk/your-privacy-secured-inside-the-tech-powering-more-secure-personalised-galaxy-ai-experiences | 2025 |
| R13 | Making app entities available in Spotlight | Apple Developer Documentation | https://developer.apple.com/documentation/appintents/making-app-entities-available-in-spotlight | 未标注 |
| R14 | Why Apple's iOS 26.4 Siri upgrade will be bigger than originally promised | MacRumors | https://www.macrumors.com/2026/02/06/siri-ios-26-4-rumors/ | 2026-02-06 |
| R15 | iOS 26.4 beta launches without Apple Intelligence Siri features | MacRumors Forums | https://forums.macrumors.com/threads/ios-26-4-beta-launches-without-apple-intelligence-siri-features.2477859/ | 2026-02 |
| R16 | Personal Intelligence now rolling out to free Gemini users in the U.S. | MacRumors | https://www.macrumors.com/2026/03/17/gemini-personal-intelligence/ | 2026-03-17 |
| R17 | Gemini personalization overview | Google | https://gemini.google/overview/personalization/ | 未标注 |
| R18 | 小艺记忆能快速记忆重要的个人信息 | 华为消费者业务支持 | https://consumer.huawei.com/cn/support/content/zh-cn16010214/ | 基于 HarmonyOS 4.2，后更新 |
| R19 | dataaugmentation capi module | 华为开发者联盟 | https://developer.huawei.com/consumer/cn/doc/doccenter-references/api/dataaugmentation-capi-module.md | 未标注 |
| R20 | Introduction to HarmonyOS NEXT database: vector database | DEV Community（第三方）| https://dev.to/qingkouwei/ntroduction-to-harmonyos-next-data-base-vector-database-5b51 | 未标注 |
| R21 | OPPO 与 Google Cloud 深化战略协同 | OPPO 新闻中心 | https://www.oppo.com/cn/newsroom/press/544/ | 2026-01 |
| R22 | Air Gap: Protecting Privacy-Conscious Conversational Agents | arXiv 2405.05175 | https://ar5iv.labs.arxiv.org/html/2405.05175 | 2024-05 |
| R23 | PrivacyLens: Evaluating Privacy Norm Awareness of Language Models in Action | arXiv 2409.00138 | https://arxiv.org/pdf/2409.00138 | 2024-08 |
| R24 | Privacy in Action: Towards Realistic Privacy Mitigation and Evaluation for LLM-Powered Agents | arXiv 2509.17488 | https://arxiv.org/pdf/2509.17488 | 2025-09 |
| R25 | Memory Injection Attacks on LLM Agents via Query-Only Interaction（MINJA）| Dong 等，arXiv 2503.03704 | https://arxiv.org/pdf/2503.03704 | 2025-03 |
| R26 | AgentPoison（arXiv 2407.12784；URL 由编号推得，未在检索结果中直接取得）| 学术 | https://arxiv.org/abs/2407.12784 | 2024-07 |
| R27 | PoisonedRAG | Zou, Geng, Wang, Jia；USENIX Security 2025 | https://www.usenix.org/conference/usenixsecurity25/presentation/zou | 2025-08 |
| R28 | MemoryGraft: Persistent Compromise of LLM Agents via Poisoned Experience Retrieval | Srivastava, He；arXiv 2512.16962 | https://arxiv.org/html/2512.16962 | 2025-12-18 |
| R29 | Gemini long-term memory attack | InfoQ；另见 Techzine | https://www.infoq.com/news/2025/02/gemini-long-term-memory-attack/ ；https://www.techzine.eu/news/security/128653/a-new-hack-corrupts-geminis-long-term-memory/ | 2025-02 |
| R30 | 2026 防御预印本：2601.05504、2606.24322、2605.08442 | arXiv | https://arxiv.org/abs/2601.05504v1 ；https://www.emergentmind.com/papers/2606.24322 ；https://arxiv.org/html/2605.08442v1 | 2026 |
| R31 | Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control | Rezazadeh 等，Accenture；arXiv 2505.18279 | https://arxiv.org/html/2505.18279v1 | 2025-05-23 |
| R32 | Mem0 entity-scoped memory；Letta shared memory blocks；LangGraph stores | 各项目文档 | https://docs.mem0.ai/platform/features/entity-scoped-memory ；https://docs.letta.com/guides/agents/shared-memory-blocks ；https://docs.langchain.com/oss/python/langgraph/stores | 未标注 |
| R33 | EDPB weighs in on key questions on personal data in AI models | IAPP | https://iapp.org/news/a/edpb-weighs-in-on-key-questions-on-personal-data-in-ai-models | 2024-12 |
| R34 | EmbeddingGemma model overview | Google AI for Developers | https://ai.google.dev/gemma/docs/embeddinggemma | 2025-09 |
| R35 | The first on-device vector database: ObjectBox 4.0 | ObjectBox | https://objectbox.io/the-first-on-device-vector-database-objectbox-4-0 | 2024 |
| R36 | Choosing the right storage experience | Android Developers Blog | https://android-developers.googleblog.com/2023/08/choosing-right-storage-experience.html | 2023-08 |
| R37 | Right to be forgotten in AI systems（实务博客，C/D）| tianpan.co | https://tianpan.co/blog/2026/07/05/the-user-you-cannot-delete-right-to-be-forgotten-in-ai | 2026-07 |
| R38 | How does Claude's memory work | Anthropic Help Center | https://support.anthropic.com/en/articles/11817273-how-does-claude-s-memory-work | 未标注 |

### 待核实清单

1. Apple「个人上下文」Siri 实际上线版本与范围（iOS 26.4/26.5/27）；找 Apple 官方发布说明或实测。
2. Recall 的 GA 时间线与 2025–2026 的设计变更；GeekWire 一周年报道原文（本次 403）。
3. Brave、Signal、AdGuard 阻止 Recall 的具体实现（单一来源）。
4. Magic Cue 与 Private Compute Core 的关系；Magic Cue 数据源开关粒度。
5. Private Compute Core 官方文档（source.android.com）与 2024 年后的演进。
6. 华为：小艺记忆的存储位置与删除能力；关系型数据库向量能力的官方文档名称与版本；个人智能计算系统技术细节。
7. 荣耀、vivo、小米、OPPO 个人记忆功能的实现与隐私政策。
8. iOS 有限照片/联系人访问（Contact Access Button）的官方文档原文；Share sheet 作为授权先例的论证。
9. MINJA 与 AgentPoison 的会议归属与数字，需对照原文。
10. MemoryGraft 的二手数字（约 10% 与约 48%）。
11. EU AI Act、PIPL 第 47 条原文、《生成式人工智能服务管理暂行办法》相关条款的官方 URL。
12. 手机端嵌入模型的实测内存、延迟、能耗；sqlite-vec 与 ObjectBox 的移动端基准；建索引的 J/记录。
13. 差分隐私在个人索引场景的落地：未找到公开资料。
14. ChatGPT/Claude 记忆导出与删除行为，需对照官方帮助页（本次多为二手）。

# AgentOS 组件深研 · 维度 B：端侧个人数据索引 + 隐私与合规

- 调研日期：2026-11-06；时间范围以 2024-01 ~ 2026-11 为主（少量基础技术追溯至更早）
- 我方待验证立场：**端侧个人上下文的统一语义索引 + 细粒度授权是最大的生态空白；OS 提供记忆存储/索引/ACL/跨 Agent 共享，策略归 Agent**
- 方法：官方文档/技术博客/发布会/监管原文优先，媒体仅作线索；关键论断附 URL+日期+摘录；共执行约 28 次独立搜索

---

## 1. 技术谱系表

### 1.1 端侧个人数据索引（OS 级）

| 厂商/系统 | 能力 | 形态与范围 | 索引技术 | 第三方/Agent 可及性 | 状态（截至 2026-11） |
|---|---|---|---|---|---|
| Microsoft Windows Recall (Copilot+ PC) | 全屏每数秒快照 + OCR + 向量库，自然语言检索"见过的一切" | **横向全量**（跨所有应用/网页的屏幕内容），但仅桌面屏幕语义 | 本地向量数据库 + OCR，VBS Enclave 内处理 | **无 API**；仅 EEA 有手动快照导出（32 位一次性导出码，用户显式操作）[^8^][^9^] | 2025-04-25 起 GA 推送（仍标 preview）；EEA 2025-07-30 起 Release Preview[^6^][^7^] |
| Apple Spotlight 语义索引 + App Intents | personal context（邮件/信息/文件/联系人语义索引）；第三方 App 通过 `IndexedEntity` 向 Spotlight 语义索引贡献实体 | **纵向结构化**（App 主动捐献实体 schema），不是全屏抓取 | Core Spotlight 词法+语义索引；WWDC26 起 `IndexedEntityQuery`/`IntentValueQuery`[^12^][^13^] | 第三方只能"写入/被查询"，**不能直接查询全局语义索引**；消费方只有 Siri/Apple Intelligence 系统组件 | Siri AI 2026-09-14 随 iOS 27 发布（beta）；EU 因 DMA 缺席 iOS/iPadOS[^14^][^15^] |
| Google Pixel Screenshots / Magic Cue | Screenshots：Gemini Nano 端侧为截图生成标题/摘要/OCR 并建可搜索索引；Magic Cue：跨 Gmail/Calendar/Messages/Screenshots 的主动上下文联想 | Screenshots = 单模态纵向；Magic Cue = **Google 第一方 App 集合**的横向联动 | 端侧 Gemini Nano（Tensor G5）；2025-11 起部分走云端 Private AI Compute[^19^][^20^] | 无第三方写入/查询接口；Magic Cue 仅 Google 自有 App | Pixel Screenshots 2024-08（Pixel 9）；Magic Cue 2025-08-20（Pixel 10）[^18^][^19^] |
| HarmonyOS（华为） | 小艺感知 200+ 项系统级用户数据（日程、健康、兴趣等，需用户授权）；UDMF 跨应用标准化数据通路；System Picker 细粒度授权 | 数据**流转与授权**框架完整（UDMF/DataShare/Picker），但语义索引能力集中在小艺第一方 | 本地大模型闭环检索（文档/备忘录）；HPIC 端云协同 | UDMF 供 App 间共享标准化数据（权限+生命周期管理）；小艺生态经 HMAF/A2A 接入 2000+ 智能体[^21^][^24^] | 星盾架构 2024-06 随 HarmonyOS NEXT；HDC2026 发布《鸿蒙智能安全白皮书》[^22^][^23^] |

### 1.2 隐私保护技术落地

| 技术 | 落地实例 | 关键点 |
|---|---|---|
| TEE / 机密计算 | Microsoft VBS Enclave（Recall 快照+密钥，TPM 绑定 Hello ESS，JIT 解密）[^2^]；Apple Secure Enclave→PCC（无 SSH/无持久存储/镜像公开可验证）[^10^][^11^]；Google Titanium Intelligence Enclaves（Cloud TPU，远程证明+加密，外部审计）[^20^]；华为 HPIC（OHTTP+端云协同加密，三重匿名盲化，泰尔实验室增强级认证，行业首家）[^23^][^24^] | 2024-2025 四年内"硬件隔离+可验证"成为头部厂商标配；均用于**自家第一方** AI，无一对第三方 Agent 开放 |
| 差分隐私（DP） | Apple：iOS 10 起本地 DP（emoji/Safari 等），2025-04 扩展至 Apple Intelligence（Genmoji/邮件合成数据，设备端比对合成 embedding，只上传噪声信号）[^25^][^26^]；Google：Gboard DP-FTRL 2022-02 首个生产级用户级 DP，2024-02 全部 NWP 模型 DP 化（ε 0.994–13.69）[^27^] | DP/FL 用于**遥测与模型训练信号**，**未用于保护个人语义索引本身**——索引靠加密+TEE+不离开设备来保护 |
| 联邦学习（FL） | Gboard（2017 起，数亿用户；+安全聚合 SecAgg）[^28^]；学术证实裸 FL 可被重构攻击，需 DP/SecAgg 配套[^29^] | 与个人数据索引无直接耦合 |
| Picker 式细粒度授权 | iOS PHPicker（iOS 14，独立进程、免权限、逐条授权）[^30^]；Android Photo Picker（API 33+，回迁至 4.4）[^31^]；HarmonyOS 强制 System Picker（图库/通讯录）+ 取消 9 类权限[^22^]；Google Photos Picker API 取代全库 scope（2025-03 后）[^32^] | **均为"用户手动点选条目"的一次性授权；尚无"按语义范围/类别授权检索结果"的先例** |

### 1.3 多 Agent 共享记忆的权限模型

| 来源 | 模型 | 粒度 |
|---|---|---|
| Collaborative Memory（arXiv 2505.18279，2025-05） | 动态二分图（用户↔Agent、Agent↔资源）+ 私有/共享双层记忆 + 可配置读写策略（系统/Agent/用户三级）[^33^] | 学术原型，最接近"记忆 ACL"形式化 |
| MemOS（arXiv 2505.22101 / MemTensor，2025-05/07） | MemGovernance：每条记忆带 ACL、TTL、敏感标签、水印、审计日志；MemStore 跨机构共享[^34^] | 学术/开源 OS 化框架，消费级 OS 未采用 |
| Letta / CrewAI / Mem0 等框架 | 共享 memory block / scope tree / user-agent 命名空间隔离[^35^][^36^] | 多为命名空间级，业内共识"prompt 级控制不算访问控制"[^36^] |
| 生产 OS | 无。Apple/Google/Microsoft 的记忆均为第一方助手私有 | **空白** |

---

## 2. 关键数据（带出处日期）

### 2.1 Windows Recall 风波复盘（时间线）

- **2024-05-20** Microsoft 发布 Copilot+ PC 与 Recall：每数秒截屏、本地存储+OCR+向量索引、自然语言检索[^1^]。
- **2024-05-22** 英国 ICO 发声明启动问询："We are making enquiries with Microsoft to understand the safeguards in place to protect user privacy… process personal data only to the extent that it is necessary"[^3^]。
- **2024-06-04** 安全研究者 Alex Hagenah 发布 TotalRecall：数据库未加密、"all plain text"；Kevin Beaumont 验证用现成 infostealer 可在秒级自动化拖库[^4^][^5^]。
- **2024-06-07/13/14** Microsoft 三连退：Recall 改 opt-in、要求 Windows Hello；延期，不在 6-18 随 Copilot+ PC 首发，转入 Insider 测试[^1^]。
- **2024-09-27** 官方博客《Update on Recall security and privacy architecture》：VBS Enclave 隔离、密钥 TPM 托管并绑定 Hello ESS、默认过滤密码/信用卡（复用 Purview 库）、可卸载、MORSE 渗透测试+第三方独立评审[^2^]。
- **2024-11** Insider 预览上线[^37^]。
- **2025-04-25** 随 4 月非安全预览更新向全部 Copilot+ PC 推送（GA 性质，仍标 preview），距首次发布近一年[^6^]。
- **2025-06-16** EEA 专属更新：快照导出工具（一次性 32 位十六进制导出码，Microsoft 不保存）+ 新设备默认保留期从无限改为 90 天[^9^]。
- **2025-07-30** EEA 上线（build 26100.4770 Release Preview）[^7^][^8^]。
- **2026-03** 研究者发布 TotalRecall Reloaded，称可经 AIXHost.exe 注入再次提取（新防御仍可被绕过；Microsoft 未正式回应细节）[^38^]。

**教训要点（事实）**：①首发版本 SQLite 明文+无访问门禁，属于"无威胁建模上线"[^5^]；②重做核心 = opt-in + 生物识别每次验证 + TEE(VBS) + 内容过滤 + 企业默认关闭；③即便如此，2025-2026 仍被持续攻破演示，说明"全量屏幕索引"的攻击面是结构性的；④监管（ICO/GDPR/DMA 数据可携带）直接塑造了产品形态（opt-in、EEA 导出、90 天默认保留）。

### 2.2 Apple：语义索引与 personal context

- **2024-06-10 WWDC**：Apple Intelligence 三层架构（端侧 ~3B 模型 + PCC + 第三方模型可选接入）；"personal context"基于邮件/信息/文件/联系人等构建**端侧语义索引**；"If you can look it up on your device, Siri will be able to look it up on your device"（Apple 表述，经 Gruber 转引）[^39^][^40^]。
- **PCC**（2024-06 发布）：Apple Silicon 服务器、Secure Enclave、无持久存储/无日志/无 SSH 管理通道、镜像公开供独立研究者验证[^10^][^11^]。
- **2025-03-07** Apple 宣布个性化 Siri（personal context/onscreen awareness/in-app actions）延期，被批"vaporware"[^39^]。
- **iOS 18（2024）**：`IndexedEntity` 协议，App 实体可入 Spotlight 语义索引，支持自然语言匹配[^12^][^41^]。
- **WWDC26（2026-06-08）/ iOS 27（2026-09-14）**：Siri AI 发布，System Orchestrator 路由 Spotlight 语义索引 + App Intents + onscreen awareness；实体 schema"contribute your app's content to the Spotlight semantic index"；加密本地向量库[^14^][^42^][^43^]。**关键边界：第三方 App 只能捐献与被检索，查询入口独占于 Siri/系统**；服务端或高频变动数据走 `IntentValueQuery` 动态查询而非入库[^13^]。
- **DMA 合规冲突**：2025-09-24 Apple Newsroom 列举 DMA 导致的功能延迟；**2026-06-08 Newsroom：Siri AI 不在 EU 的 iOS 27/iPadOS 27 上线**，理由是 DMA 要求向任何 AI 助手开放近乎无限制的设备访问，Apple 提出"Trusted System Agent"中介方案+18 个月渐进 rollout 被欧委会拒绝[^15^][^16^]。

### 2.3 HarmonyOS：数据管理与授权

- **2024-06** 星盾（StarShield）安全架构随 HarmonyOS NEXT 发布：全栈无特权、权限最小化、"一文一密/用时解密"；获智能终端 OS 领域首个 EAL5+[^22^]。
- **"从管权限到管数据"**：禁止 9 类不合理权限（读取应用列表、短信、通话记录、存储文件等）；图库/通讯录强制 System Picker；"最小化精准授权，单次授予，单次访问"[^22^][^44^]。
- **数据分类分级**：敏感个人数据 S4（凭据/生物特征/健康等）~基本个人信息 S1，对应差异化管控（《HarmonyOS NEXT 安全技术白皮书》，2024-08）[^45^]。
- **UDMF**（OpenHarmony 4.0，2023-06 起）：统一数据管理框架，标准化数据通路 `udmf://intention/bundleName/groupId`，写入数据按应用定义权限+通路权限+框架逻辑管理，含生命周期管理；DataShare 三层权限（声明/规则/运行时校验）[^21^][^46^]。
- **小艺（2025-2026）**：Agentic 自演进架构，用户授权下感知 200+ 项系统级数据；"小艺帮记"本地处理优先、仅向云端传结构化结果；"小艺帮帮忙"资产操作强制人工确认；2026-04 小艺 Claw 获信通院首个终端厂商智能体安全认证[^47^][^48^]。
- **HPIC**（HDC2026，2026-06）：本地优先/数据最小化/用户可控三原则；OHTTP+端云协同加密，三重匿名盲化，"隔离计算、算完即删"；泰尔实验室《面向端云协同的人工智能隐私安全能力测试》增强级，行业首家[^23^][^24^]。

### 2.4 Google：记忆与端侧索引

- **Pixel Screenshots**（2024-08-13，Pixel 9）：Gemini Nano 端侧为每张截图生成标题/摘要，全文 OCR+元数据索引、语义搜索、可生成提醒/日历动作；仅限截图[^18^]。
- **Gemini 记忆**：2025-03-13 "Personalization (experimental)"（连接 Search 历史，opt-in）；**2025-08-13 "Personal context" 默认开启**（从过往聊天学习偏好）+ Temporary Chat（不记忆、72 小时删除）[^49^][^50^]；**2026-01-14 "Personal Intelligence"**（连接 Gmail/Photos/Search/YouTube，**opt-in、默认关**）[^51^]；2026-02-26 past chats 推广至免费用户（欧洲除外）[^52^]。默认开启引发隐私批评（有用户报告旧设置被自动重开）[^53^]。
- **Magic Cue**（2025-08-20，Pixel 10）：跨 Gmail/Calendar/Messages/Screenshots 主动联想；端侧 Tensor G5+Gemini Nano；"you can turn it on or off, or grant permission to see your calendar but not your messages"——**逐 App 粒度授权**[^19^][^54^]。
- **Private AI Compute**（2025-11-11）：Titanium Intelligence Enclaves + 远程证明 + ALTS/Noise 加密，外部审计验证初始设计；首用于 Magic Cue 与 Recorder；2026 年进一步加入**持久化服务器端记忆**（设备密钥加密的跨设备记忆层）[^20^][^55^]。
- **AppFunctions**（Android 16，2026）：App 作为"端侧 MCP server"向 Gemini 等 Agent 暴露函数；调用方须持 `EXECUTE_APP_FUNCTIONS` 权限；Gemini 集成 2026-05 起 private preview[^56^]。——**动作面**已开放给 Agent，但**记忆/语料面**仍未开放。

### 2.5 隐私技术落地现状（小结数据点）

- Apple DP 2025-04-14：Genmoji 等场景中，设备只回传"与合成 embedding 最近邻"的噪声信号，邮件内容不出设备[^26^]。
- Gboard：2024-02 Google 称全部 NWP 神经语言模型以 FL+DP 训练，含首个 ε<1 的用户级 DP 生产部署[^27^]。
- 学术验证：裸 FL 更新可高保真重构用户输入，DP 噪声到有效防护水平会显著损效用[^29^]——**DP/FL 是"训练侧"技术，不是"索引/记忆访问控制"技术**。

### 2.6 监管动态

- **GDPR/英国**：ICO 2024-05-22 就 Recall 启动问询，强调透明与数据最小化[^3^]；EEA 版 Recall 的导出机制被普遍解读为回应 GDPR 数据可携带与 DMA Art.6(9)（厂商未声明法律依据）[^7^]；EDPB 就智能眼镜发布声明：always-on 采集须兼顾**旁观者**告知与指示器不可规避——对"持续采集"类设备的直接约束信号[^57^]。
- **DMA**：Apple 以"被迫向对手 AI 开放深层数据访问"为由拒绝在 EU 上线 Siri AI（2026-06-08），欧委会公开反驳"DMA 并不禁止上线"——**监管正在把"语义索引+深访问"从平台独占资产推向互操作义务对象**[^15^][^16^]。
- **中国**：《个人信息保护合规审计管理办法》2025-02-14 公布、2025-05-01 施行，处理超 1000 万人个人信息者每两年至少一次合规审计[^58^]；GB/T 45654-2025《网络安全技术 生成式人工智能服务安全基本要求》2025-11-01 实施：用户输入用于训练须明确告知并提供"≤4 次点击"的便捷关闭方式[^59^][^60^]；个保法第六条"最小必要"为 always-on 索引设定目的限定与最小范围硬约束[^60^]。

---

## 3. 趋势判断

**收敛方向（事实支撑）：**

1. **"端侧语义索引"已从概念变为头部 OS 标配，但均为第一方助手私有资源**。Recall（全屏横向）、Spotlight semantic index（捐献式纵向）、Magic Cue（第一方 App 横向）、小艺（系统数据纵向）四条路线并存；没有任何一家把索引作为"可被第三方 Agent 经授权查询的 OS 服务"开放。
2. **隐私架构收敛于同一范式**：默认 opt-in → 生物识别/身份门禁 → TEE 隔离处理（VBS/Secure Enclave/TIE/HPIC）→ 敏感内容自动过滤 → 可删除/可审计/可携带。Recall 风波是该范式形成的直接催化剂。
3. **云端兜底方案同质化**：Apple PCC（2024-06）→ Google PAC（2025-11）→ 华为 HPIC（2026-06），均为"硬件密封+远程证明+算完即删+可外部验证"，16 个月内三家对齐。
4. **细粒度授权收敛于 Picker 范式但停留在"条目级手动选择"**：iOS/Android/HarmonyOS/Google Photos API 全部是"用户点哪条给哪条"；Magic Cue 的"逐 App 授权"是粒度最粗的语义授权雏形；**"按语义谓词授权"（如"只授权与出差相关的邮件检索结果"）无任何先例**。
5. **记忆 ACL 只在学术与 Agent 框架层出现**（Collaborative Memory、MemOS、Letta/Mem0 的命名空间），生产 OS 为零；且业内明确"prompt 级控制不算 ACL"，需要数据层强制[^36^]。
6. **监管成为架构的硬约束变量**：GDPR/DMA 既逼出了 opt-in/导出/默认保留期，也以互操作名义要求平台向对手开放同等深访问（Apple-EU Siri AI 僵局）；中国侧以审计办法+GB/T 45654 把"告知-同意-便捷关闭"量化到点击数。

**空白点（判断）：**

- 不存在"统一个人语义索引 + 面向任意第三方 Agent 的细粒度语义授权 + 数据层强制的记忆 ACL"三者的交集实现；每条腿分别有先例，但没人把三者焊在一起。
- DP/FL 没有也不会成为索引访问控制手段——记忆 ACL 的正确技术栈是 TEE+加密+属性/谓词级授权+审计，这块没有任何厂商做完。
- 多 Agent 共享记忆的权限模型连"事实标准"都未形成（MCP/A2A 只管传输不管记忆治理[^61^]）。

---

## 4. 对我方立场的逐条验证

**立场："端侧个人上下文统一语义索引 + 细粒度授权是最大生态空白；OS 提供存储/索引/ACL/跨 Agent 共享，策略归 Agent。"**

1. **支持（核心判断成立，且证据强于预期）**。四大平台的个人索引全部第一方锁定：Recall 无第三方 API（EEA 导出是唯一例外且为手动）[^8^]；Apple 第三方只能"捐献"不能"查询"[^13^]；Magic Cue 只连 Google 自家 App[^54^]；小艺 200+ 项数据感知服务小艺自身[^47^]。"统一索引存在、但不可被生态经授权使用"——空白判断**成立**。置信度：高。
2. **支持（细粒度授权范式已被教育成熟，可直接嫁接）**。Picker 范式（逐条、免权限、单次授予）在三大移动 OS 已普及，用户心智与监管语言都已接受[^30^][^31^][^44^]；把 Picker 从"选照片"升级为"选语义范围"是自然外推，无需从零教育市场。
3. **支持（"OS 管基础设施、策略归 Agent"的分工与监管走向同构）**。DMA 要求平台向第三方助手开放同等访问，Apple 的应对思路（Trusted System Agent 中介层）本质就是"OS 提供受控中介、助手自带策略"[^15^]——我方架构与该方向一致，且可抢占"合规叙事"。
4. **挑战（窗口正在收窄，不是无人区而是"将被填的区"）**。Apple 的语义索引+App Intents 已让"OS 级索引+schema 化贡献"产品化；Google AppFunctions 已把动作面开放给 Agent；若 Apple 按 DMA 要求在 EU 落地 Trusted System Agent，则"第三方助手经 OS 中介访问个人上下文"将在 2027 年前后成为现实——空白期可能只有 12-24 个月。
5. **挑战（Recall 证明"全量横向索引"的信任成本极高）**。always-on 全屏索引引发 ICO 问询、舆论抵制、两次公开攻破；即便重做后，2026 年仍被演示绕过[^38^]。我方若做统一索引，"采集面宽度"须让位于"可证明的最小化"（敏感过滤、保留期、TEE 证明应作为首发而非补丁）。
6. **需要修订（"策略归 Agent"需加限定词）**。MemOS/Collaborative Memory 与行业实践表明：写策略、敏感分级、跨 Agent 传递的最小上下文裁剪，不能完全下放给 Agent——**数据层的强制 ACL、provenance、审计必须在 OS 侧不可绕过**（"prompt 级控制不算访问控制"[^36^]）。建议修订为："OS 强制数据层 ACL/审计/出处，Agent 在授权包络内自定使用策略"。
7. **需要修订（隐私技术选型）**。不要指望 DP/FL 保护索引（它们是训练侧技术，且裸 FL 已被攻破[^29^]）；索引保护的正解是 TEE+加密+授权谓词+审计，DP 只用于遥测/改进环节。

---

## 5. 组件特有素材：空白点清单与最接近实现的差距分析

### 5.1 端侧个人语义索引的空白点清单

| # | 空白点 | 现状证据 |
|---|---|---|
| G1 | **跨应用统一语义索引对第三方 Agent 开放查询** | 四大平台索引全部第一方锁定[^8^][^13^][^54^][^47^] |
| G2 | **语义级（谓词级）授权**：按"类别/时间/敏感度/关系"授权检索结果而非按条目/按 App | Picker 只到条目级；Magic Cue 只到 App 级[^30^][^54^] |
| G3 | **记忆/索引的数据层强制 ACL + provenance + 审计**（OS 侧不可绕过） | 仅学术（Collaborative Memory 动态二分图、MemOS MemGovernance）[^33^][^34^] |
| G4 | **跨 Agent 共享记忆的标准权限模型** | MCP/A2A 不涉记忆治理[^61^]；框架级只有命名空间隔离[^35^] |
| G5 | **索引的可验证最小化**：TEE 证明+敏感过滤+保留期的组合对外可审计 | Recall/PCC/PAC/HPIC 各自部分具备，无一家对第三方出具可编程证明[^2^][^10^][^20^][^23^] |
| G6 | **索引的可携带与退出**（导出/迁移/删除的标准化） | 仅 Recall EEA 导出码一种雏形，且是为合规而非生态[^9^] |
| G7 | **旁观者/第三方数据主体保护**（always-on 索引拍到他人信息） | EDPB 智能眼镜声明指出该义务，OS 级索引无一处理[^57^] |

### 5.2 最接近实现的差距分析

**最接近者 A：Apple（Spotlight 语义索引 + App Intents + PCC）**
- 已有：统一的系统级语义索引、schema 化实体贡献、端侧模型编排、TEE 云端兜底、IndexedEntityQuery/IntentValueQuery 双模检索[^13^][^14^]。
- 差距：①查询入口被 Siri 独占，第三方 Agent 拿不到索引句柄（G1）；②授权是"是否捐献"的二元开关，无语义谓词（G2）；③无记忆级 ACL/审计对开发者暴露（G3）。
- 评估：**距离完整形态最近，但封闭是有意的商业+合规定位**；DMA 压力（Trusted System Agent 方案）显示其被迫向"OS 中介层"演进——恰好验证我方架构方向[^15^]。

**最接近者 B：HarmonyOS（星盾 + Picker + UDMF + 小艺 + HPIC）**
- 已有：最激进的细粒度授权哲学（管数据不管权限、单次授予）、跨应用标准化数据通路（UDMF 带权限+生命周期）、200+ 项系统数据的授权感知、端云机密计算认证[^22^][^21^][^47^][^23^]。
- 差距：①UDMF 是"数据流转通道"不是语义索引，无向量/语义检索层（G1 的一半）；②Picker 授权到条目级，无语义谓词（G2）；③小艺的记忆与感知仍服务第一方 Agent，HMAF/A2A 解决 Agent 间协作而非"任意 Agent 查询个人索引"（G4）。
- 评估：**授权哲学与数据通路最接近我方立场，但缺"语义索引+Agent 可查询"那一层**。

**参照系 C：Windows Recall**
- 已有：唯一的全量横向个人索引、TEE 重做后的完整防护清单。
- 差距：全量截屏路线信任成本最高、无生态接口、且 2026 年仍被攻破演示[^38^]——**作为反面教材价值大于参考价值**。

**参照系 D：学术/框架（Collaborative Memory、MemOS、Letta）**
- 已有：记忆 ACL 形式化（动态权限图、TTL/水印/审计）、共享块机制[^33^][^34^][^35^]。
- 差距：无 OS 强制力、无硬件信任根、无消费级合规工程。

**结论**：把 B 的授权哲学 + A 的索引/编排 + D 的记忆 ACL 形式化 + Recall 的 TEE 防护清单组合，即是我方组件的完整定义；当前没有任一实现覆盖超过其中两项——**空白判断在 2026-11 时点仍然成立，但 Apple/DMA 路线是最快的填坑者**。

---

## 6. 证据清单

| # | Claim | Source | URL | Date | Excerpt | Confidence |
|---|---|---|---|---|---|---|
| [^1^] | Recall 发布与延期/重做全过程 | Wikipedia: Windows Recall | https://en.wikipedia.org/wiki/Windows_Recall | 2024-10（持续更新） | "Microsoft pledged to rework Windows Recall… on June 14 to delay release… changed the feature to opt-in" | 高（二手汇编，与官方博文互证） |
| [^2^] | Recall 重做架构：VBS Enclave、TPM+Hello ESS、敏感过滤 | Microsoft Windows Experience Blog（经 CRN/Computerworld 转述） | https://blogs.windows.com/windowsexperience/2024/09/27/update-on-recall-security-and-privacy-architecture/ ; https://www.crn.com/news/security/2024/microsoft-ai-pc-recall-feature-gets-security-architecture-update | 2024-09-27 | "Recall services operating on screenshots… are within a secure VBS Enclave… rate-limiting and anti-hammering" | 高 |
| [^3^] | ICO 就 Recall 启动问询 | ICO 官网声明 | https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2024/05/statement-in-response-to-microsoft-recall-feature/ | 2024-05-22 | "We are making enquiries with Microsoft to understand the safeguards in place to protect user privacy." | 高（监管原文） |
| [^4^] | TotalRecall 拖库：数据库明文 | WIRED | https://www.wired.com/story/total-recall-windows-recall-ai/ | 2024-06-04 | "The database is unencrypted. It's all plain text" | 高 |
| [^5^] | Recall 首发版 SQLite 明文、用户态即可读全量历史 | ironhackers 技术复盘（引 Beaumont/Hagenah/Forshaw 原始披露） | https://ironhackers.es/en/microsoft-copilot-recall-analisis/ | 2024-05-30 | "ukg.db is a standard SQLite. No DPAPI, no SQLCipher… a process running as the current user reads the full visual history in less than a second" | 中高（技术媒体汇编一手披露） |
| [^6^] | Recall 2025-04-25 起向全部 Copilot+ PC 推送 | GeekWire / Microsoft 博客 | https://www.geekwire.com/2025/microsoft-rolls-out-recall-and-other-ai-features-to-all-copilot-pcs-nearly-a-year-after-unveiling/ | 2025-04-25 | "broadly releasing its flagship AI-powered features for Copilot+ PCs… Recall (in preview)" | 高 |
| [^7^] | EEA 延迟上线与导出机制合规模糊性 | L00P.ai 追踪报告 | https://www.l00p.ai/en/resources/ai-in-the-eu/ | 2026-09-24 | "reached general availability on 25 April 2025, with the EEA excluded… started in the EEA on 30 July 2025… documentation as of February 2026 still labels Recall a preview" | 中（编辑解读，日期与官方 build 一致） |
| [^8^] | EEA 快照导出：一次性导出码、第三方须凭码+路径访问 | ElevenForum（引 Microsoft 文档） | https://www.elevenforum.com/t/use-recall-with-snapshots-in-windows-11.31003/ | 2025-07 起 | "Third-party apps can access exported snapshots only when both the export code and folder path are provided" | 高（逐条引官方文档） |
| [^9^] | 导出功能与新机默认 90 天保留期 | WinBuzzer | https://winbuzzer.com/2025/06/16/microsofts-windows-recall-feature-gets-export-tool-in-the-eu-amid-ongoing-privacy-concerns-xcxwbn/ | 2025-06-16 | "changes the default storage limit on new PCs from unlimited to 90 days" | 中高 |
| [^10^] | PCC：无持久存储、无日志、无 SSH | SimpleMDM | https://simplemdm.com/blog/apple-intelligence-how-secure-is-private-cloud-compute-for-enterprise/ | 2025-07-17 | "no persistent storage, profiling, or logging… removed SSH, remote shells, and debug tools from PCC nodes" | 中高（与 Apple 官方一致） |
| [^11^] | PCC 端到端可验证 | Jamf | https://www.jamf.com/blog/apple-intelligence-private-cloud-compute-explained/ | 2024-10-30 | "the entire stack is both verifiable… from silicon to the cloud services" | 中高 |
| [^12^] | iOS 18 IndexedEntity 入 Spotlight 语义索引 | Matthew Cassinelli（WWDC24 整理） | https://matthewcassinelli.com/?p=34069 | 2024-06-24 | "IndexedEntity protocol… index of all the items… matched when queried using natural language" | 中高 |
| [^13^] | WWDC26：IndexedEntityQuery/IntentValueQuery；索引须保鲜；动态查询替代入库 | WWDC26 session 343 纪要 | https://wwdc.ai/2026/343 | 2026-06 | "Use IntentValueQuery when search must be resolved dynamically" | 中高（第三方纪要，与 Apple 文档一致） |
| [^14^] | iOS 27 Siri AI 架构：Orchestrator 路由 Spotlight 语义索引；第三方只贡献不查询 | progressivewebapps / ideaequity | https://progressivewebapps.com/ai/future/ ; https://ideaequity.ai/blog/ios-27-app-intents-siri-app-discovery | 2026-09-25 / 2026-08-27 | "entity schemas 'contribute your app's content to the Spotlight semantic index'"（引 Apple Newsroom） | 中高 |
| [^15^] | Siri AI 因 DMA 不上 EU iOS/iPadOS；Trusted System Agent 方案被拒 | Apple Newsroom | https://www.apple.com/newsroom/2026/06/due-to-dma-siri-ai-delayed-in-eu-for-ios-27-and-ipados-27/ | 2026-06-08 | "Apple designed a solution called Trusted System Agent—an intermediary that would allow virtual assistants to safely access the same features and capabilities as Siri AI… The European Commission said no." | 高（官方） |
| [^16^] | 欧委会反驳：DMA 不禁止 Siri AI 上线 | AP News | https://apnews.com/article/siri-ai-europe-apple-5d18df90b03e4e98ac528c8802e2b531 | 2026-06-09 | "absolutely nothing in the DMA prohibits Apple from introducing new products in the EU" | 高 |
| [^17^] | Apple Intelligence 端侧语义索引演示与架构 | xmartlabs / hangyan（信达证券图） | https://blog.xmartlabs.com/blog/apple-intelligence-ai-data-privacy/ | 2024-09-16 | "sophisticated on-device semantic index that organizes and surfaces information from across your apps" | 中 |
| [^18^] | Pixel Screenshots：Gemini Nano 端侧索引截图 | Mashable | https://mashable.com/article/pixel-screenshots-google-event-2024 | 2024-08-13 | "Using on-device AI that Google calls 'Gemini Nano,' the app generates a title and summary for each screenshot" | 高 |
| [^19^] | Magic Cue 发布与端侧架构 | Google 官方博客 | https://blog.google/products-and-platforms/devices/pixel/google-pixel-10-ai-features-updates/ | 2025-08-20 | "Magic Cue connects the dots across your apps, like Gmail, Calendar, Screenshots, Messages… runs securely and privately through a combination of the Tensor G5 chip and Gemini Nano" | 高（官方） |
| [^20^] | Private AI Compute：TIE+远程证明+外部审计 | Google 博客/9to5Google/evrimagaci（引技术简报） | https://9to5google.com/2025/11/11/google-private-ai-compute-pixel/ | 2025-11-11 | "hardware-secured sealed cloud environment… an external auditor validated the initial system design" | 高 |
| [^21^] | UDMF：标准化数据通路、权限与生命周期管理 | HarmonyOS 开发者文档镜像（GitHub） | https://github.com/liasica/harmonyos-skills/blob/master/harmonyos/references/harmonyos-guides/data-share-overview.md | 2026-09（文档快照） | "写入UDMF中的数据依据应用定义的权限、数据通路定义的权限以及整个UDMF框架定义的权限管理逻辑进行管理" | 高（官方文档镜像） |
| [^22^] | 星盾架构、取消 9 类权限、强制 System Picker | 华为《HarmonyOS NEXT 安全技术白皮书》/中国日报 | https://consumer.huawei.com/content/dam/huawei-cbg-site/cn/mkt/privacy/privary-new/250610/down/HarmonyOS%20NEXT%E5%AE%89%E5%85%A8%E6%8A%80%E6%9C%AF%E7%99%BD%E7%9A%AE%E4%B9%A6.pdf ; http://ex.chinadaily.com.cn/exchange/partners/82/rss/channel/cn/columns/snl9a7/stories/WS667d22b5a3107cd55d268dc9.html | 2024-08 / 2024-06-27 | "对图库、通讯录等强制使用System Picker方式防止权限滥用行为"；"取消…9类不合理权限" | 高（官方） |
| [^23^] | HPIC 三原则+三重匿名盲化+泰尔增强级认证 | 中国日报（HDC2026）/华为认证页 | http://ex.chinadaily.com.cn/exchange/partners/82/rss/channel/cn/columns/sz8srm/stories/WS6a2f7405a310d709c2fb8019.html ; https://consumer.huawei.com/cn/privacy/certification/ | 2026-06-15 | "本地优先、数据最小化、用户可控三大原则…用户身份三重匿名盲化，即便是系统管理员也无法查看用户明文数据" | 高 |
| [^24^] | HPIC 算完即删、隔离计算 | 新浪财经（HarmonyOS 7 发布） | https://k.sina.com.cn/article_7879995958_1d5af323601901vmf2.html | 2026-07-14 | "上云的数据实现隔离计算、用完即删、不存储" | 中高 |
| [^25^] | Apple DP 生产部署（iOS 10 起，本地 DP） | Apple ML Research《Learning with Privacy at Scale》 | https://machinelearning.apple.com/research/learning-with-privacy-at-scale | 2017-12-06 | "Data is privatized on the user's device using event-level differential privacy in the local model" | 高（官方） |
| [^26^] | DP 扩展至 Apple Intelligence（Genmoji/邮件合成数据） | Apple ML Research | https://machinelearning.apple.com/research/differential-privacy-aggregate-trends | 2025-04-14 | "The contents of the sampled emails never leave the device… Apple learns which selected synthetic emails are most often selected across all devices" | 高（官方） |
| [^27^] | Gboard 全部 NWP 模型 FL+DP 化，首个 ε<1 生产部署 | Google Research（经 techmeridian 转引）/arXiv 2306.14793 | https://arxiv.org/html/2306.14793v1 | 2024-02-21 / 2023-06 | "In Feb 2022 we deployed the DP-FTRL… for the first time offered a formal DP guarantee in production (zCDP ρ=0.81)" | 高（官方论文） |
| [^28^] | Gboard FL 2017 年起生产部署 | InfoWorld | https://www.infoworld.com/article/2259200/android-gboard-smartens-up-with-federated-machine-learning.html | 2017-04-10 | "Only this update to the model is sent to the cloud… immediately averaged with other user updates" | 高 |
| [^29^] | 裸 FL 可被重构攻击，DP 噪声有效水平损效用 | arXiv 2210.16947 | https://arxiv.org/html/2210.16947v2 | 2022-10-24 | "an attack that reconstructs the original training data… DP is not an effective countermeasure unless noise levels substantially degrade utility" | 高（同行评议级预印本） |
| [^30^] | PHPicker：独立进程、免权限、逐条授权 | Apple 开发者文档（经 Flutter issue 转引）/ohmyswift | https://github.com/flutter/flutter/issues/106799 ; https://ohmyswift.com/blog/2020/08/29/replacing-uiimagepickercontroller-with-phpickerviewcontroller/ | 2020-08 / 2022-06 | "The user doesn't need to explicitly authorize your app to select photos" | 高（官方文档摘录） |
| [^31^] | Android Photo Picker 免权限、回迁 | ProAndroidDev | https://proandroiddev.com/permissionless-photo-picker-android-18f2ffce1b62 | 2023-05-04 | "back-ported version provided by Google Play services on devices running Android KitKat (4.4) and later" | 中高 |
| [^32^] | Google Photos 全库 scope 弃用，强制 Picker API | MemoryKPR | https://memorykpr.com/blog/google-photos-api-deprecation-what-it-means-for-third-party-apps-and-how-to-prepare/ | 2025-10-24 | "After March 2025, those permissions will be permanently disabled… Photos Picker API… requires users to manually select" | 中 |
| [^33^] | 多用户/多 Agent 记忆动态 ACL 形式化 | arXiv 2505.18279《Collaborative Memory》 | https://arxiv.org/html/2505.18279v1 | 2025-05-23 | "Dynamic bipartite access graphs… two-tier memory system… fine-grained read and write policies" | 高（学术） |
| [^34^] | MemOS：记忆 OS 化 + MemGovernance（ACL/TTL/水印/审计/出处 API） | arXiv 2505.22101 / MemTensor 白皮书 | https://arxiv.org/html/2505.22101v1 ; https://statics.memtensor.com.cn/files/MemOS_0707.pdf | 2025-05-27 / 2025-07 | "Governance Attributes… access permissions, lifespan policies, sensitivity tags, watermarking, and access logging" | 高（学术+开源） |
| [^35^] | Letta 共享 memory block 机制 | Letta 官方文档 | https://docs.letta.com/concepts/shared-memory/ | 2025-2026 | "Shared memory gives multiple agents access… one in-context memory block attached to multiple agents" | 高（官方文档） |
| [^36^] | 行业共识：prompt 级控制不算 ACL；需数据层强制；逐跳独立认证 | MindStudio / zylos 框架对比 | https://www.mindstudio.ai/blog/shared-vs-private-ai-agent-memory-team-access-control ; https://zylos.ai/research/2026-03-09-multi-agent-memory-architectures-shared-isolated-hierarchical/ | 2026-06-03 / 2026-03-09 | "Prompt-level access control isn't access control. Enforce permissions at the data layer" | 中（行业博客，论断与学术一致） |
| [^37^] | Recall Insider 预览 2024-11 上线 | Computerworld | https://www.computerworld.com/article/2128281/microsoft-windows-recall-privacy.html | 2024-11-27 | "In late November 2024, Recall became available in a preview form for Windows Insiders" | 高 |
| [^38^] | TotalRecall Reloaded 2026 再次提取成功 | GovInfoSecurity | https://www.govinfosecurity.com/microsoft-recall-again-spills-secrets-a-31083 | 2026-03 | "Microsoft redesigned the entire architecture with VBS enclaves after the original TotalRecall… he was still able to pop the new defenses" | 中（研究者自述，Microsoft 未确认） |
| [^39^] | 个性化 Siri 延期（2025-03）；personal context=语义索引 | Daring Fireball | https://daringfireball.net/2025/03/something_is_rotten_in_the_state_of_cupertino | 2025-03-07 | "'Personal context'—Knowing details and information about you from a 'semantic index', built from the contents of your email, messages, files, contacts" | 高（引 Apple 官方表述） |
| [^40^] | Apple Intelligence 三层架构发布 | Digital Trends（WWDC24） | https://www.digitaltrends.com/phones/everything-apple-announced-at-wwdc-2024/ | 2024-06-11 | "Private Cloud Compute allows Apple Intelligence to utilize external information when necessary without storing user data" | 中高 |
| [^41^] | Apple 官方：App 实体入 Spotlight 索引供 Siri/语义搜索 | Apple Developer 文档 | https://docs.developer.apple.com/tutorials/data/documentation/appintents/making-app-entities-available-in-spotlight.md | 2024 起 | "you gain the ability to perform fast lexical and semantic searches… Apple Intelligence can also apply your app's indexed content to other system experiences like Siri" | 高（官方） |
| [^42^] | Siri AI 加密本地向量库（邮件/信息/备忘录/照片） | AICC 技术实测 | https://www.ai.cc/blogs/apple-intelligence-guide-siri-ai-iphone-automation/ | 2026-06-26 | "continuously builds an encrypted local vector database of your emails, messages, notes, and photos" | 中（第三方技术博客） |
| [^43^] | Siri AI 2026-09-14 随 iOS 27 发布、EU/中国缺席 | progressivewebapps | https://progressivewebapps.com/ai/future/ | 2026-09-25 | "Apple released Siri AI with iOS 27 on September 14, 2026… isn't initially available in the EU… or in China" | 中高 |
| [^44^] | "从管权限到管数据"、单次授予单次访问 | 钛媒体 | https://www.tmtpost.com/7145819.html | 2024-06-27 | "最小化精准授权，单次授予，单次访问，杜绝了'过度申请'" | 中高 |
| [^45^] | HarmonyOS 数据分类分级 S1-S4 | 华为白皮书 | 同 [^22^] PDF | 2024-08 | "敏感个人数据…严重(S4)…生物特征…健康信息" | 高（官方） |
| [^46^] | UDMF/DataShare 权限模型与公共通路 | 腾讯云开发者（引鸿蒙官方） | https://cloud.tencent.com/developer/article/2464744 | 2024-11-10 | "全局唯一URI标识 udmf://intention/bundleName/groupId…按照一定的策略对暂存数据的访问权限和生命周期进行管理" | 中高 |
| [^47^] | 小艺感知 200+ 项系统级数据（授权下）；分层权限策略 | 百度百科"鸿蒙智能体"/搜狐 HDC2026 | https://baike.baidu.com/item/%E9%B8%BF%E8%92%99%E6%99%BA%E8%83%BD%E4%BD%93/68747927 ; https://m.sohu.com/a/1036277671_121850782 | 2026-09 / 2026-06-14 | "在用户授权下可感知200余项系统级用户数据…小艺通过多智能体协作框架与分层权限策略" | 中 |
| [^48^] | 小艺帮记本地优先、仅结构化结果上云；Claw 信通院首认证 | 搜狐（HDC2026 白皮书报道） | https://m.sohu.com/a/1036277671_121850782 | 2026-06-14 | "敏感资料在设备端完成处理后，仅向云端传输结构化结果…首个获得国家级认证的终端厂商智能体" | 中高 |
| [^49^] | Gemini Personal context 默认开启 + Temporary Chat | Google 官方博客 | https://blog.google/products-and-platforms/products/gemini/temporary-chats-privacy-controls/ | 2025-08-13 | "a new setting that allows Gemini to learn from your past conversations over time" | 高（官方） |
| [^50^] | Personal context 默认开启的设置路径 | Search Engine Journal | https://www.searchenginejournal.com/google-gemini-adds-personalization-from-past-chats/553639/ | 2025-08-13 | "The setting is on by default and can be turned off in Settings → Personal context" | 高 |
| [^51^] | Personal Intelligence 连接 Gmail/Photos/Search/YouTube，opt-in | memx.app 汇编（引 Google 帮助文档） | https://memx.app/glossary/gemini-personalization/ | 2026-06-12 | "On January 14, 2026, Google launched 'Personal Intelligence'… off by default and opt-in" | 中 |
| [^52^] | past chats 推向免费用户（欧洲除外） | 9to5Google | https://9to5google.com/2026/02/26/gemini-past-chats-free/ | 2026-02-26 | "rolling out for all free users around the world, except Europe" | 中高 |
| [^53^] | 默认开启引发隐私批评、旧设置被重开 | PPC Land | https://ppc.land/google-gemini-now-learns-from-your-chats-unless-you-turn-it-off/ | 2025-08-17 | "users who previously disabled 'Gemini Apps Activity'… may find their settings automatically reactivated" | 中 |
| [^54^] | Magic Cue 逐 App 粒度授权 | Yahoo Tech | https://tech.yahoo.com/ai/articles/pixel-10-magic-cue-connects-181310237.html | 2025-08-22 | "grant permission to see your calendar but not your messages" | 中高 |
| [^55^] | PAC 引入持久化服务器端记忆（设备密钥） | Unite.ai / Zeniteq（引 Google DeepMind） | https://www.unite.ai/google-brings-persistent-server-side-memory-to-private-ai-compute/ | 2026-09-23 | "the earlier system could process a request in an isolated cloud environment, then discard its context… retain per-user context in encrypted server-side storage" | 中 |
| [^56^] | AppFunctions：App 即端侧 MCP server；EXECUTE_APP_FUNCTIONS 权限 | LetsDataScience（引 developer.android.com） | https://letsdatascience.com/news/google-enables-android-apps-with-appfunctions-for-gemini-8e56077a | 2026-06-08 | "callers… must hold the EXECUTE_APP_FUNCTIONS permission… Gemini is in a private preview with trusted testers as of May 2026" | 中高（引官方文档） |
| [^57^] | EDPB 智能眼镜声明：旁观者告知义务、指示器不可规避 | Kaamel（整理 EDPB 声明） | https://www.kaamel.com/blog/en-edpb-smart-glasses-responsibility/ | 2026-10-14 | "Indicators should make people aware that the glasses are recording or performing AI processing" | 中（二手整理监管原文） |
| [^58^] | 个人信息保护合规审计管理办法（2025-05-01 施行） | 网信办官网 | https://www.cac.gov.cn/2025-02/14/c_1741233507681519.htm | 2025-02-14 | "处理超过1000万人个人信息的个人信息处理者，应当每两年至少开展一次个人信息保护合规审计" | 高（监管原文） |
| [^59^] | GB/T 45654-2025（2025-11-01 实施） | 中国日报 | http://ex.chinadaily.com.cn/exchange/partners/82/rss/channel/cn/columns/sz8srm/stories/WS68637bf8a3106af2b3c71d9a.html | 2025-07-01 | "GB/T 45654-2025《网络安全技术 生成式人工智能服务安全基本要求》…将于2025年11月1日正式实施" | 高 |
| [^60^] | 用户输入用于训练须告知+≤4 次点击可关闭；最小必要 | 金杜律师事务所 | https://www.kingandwood.com/cn/zh/insights/latest-thinking/compliance-guide-for-large-model-service-providers-on-model-debugging-for-commercial-use.html | 2025-11-13 | "使用者从服务主界面开始到达该选项所需操作不超过4次点击…仅收集与所提供的服务直接相关的最小范围数据" | 高（律所引标准原文） |
| [^61^] | MCP/A2A 不管记忆治理；记忆需独立策略层 | mnemoverse（引 A2A 规范与 arXiv 2603.10062） | https://mnemoverse.com/docs/library/shared-memory-for-multi-agent-systems | 2026-06-18 | "A2A specification says agents collaborate without requiring access to each other's internal state, memory, or tools" | 中 |
| [^62^] | Recall 管理面：不同用户/IT 管理员/Microsoft 均不可见快照 | Microsoft Learn | https://learn.microsoft.com/en-us/windows/client-management/manage-recall | 2025-12 | "Snapshots and any associated information in the vector database are always encrypted. Encryption keys are protected via TPM… VBS Enclave" | 高（官方文档） |

---

### 附：事实 vs 判断速览

- **事实**：四大 OS 的个人索引均第一方锁定（§1.1）；Picker 均为条目级手动授权（§1.2）；记忆 ACL 仅存在于学术/框架层（§1.3）；ICO/DMA/个保法审计办法/GB/T 45654 的监管动作（§2.6）。
- **判断**："三者交集空白成立但窗口 12-24 个月"（§4-4）；谓词级语义授权无先例（§3-空白点）；"策略归 Agent"需修订为"OS 强制数据层 ACL"（§4-6）。
- **未能完全证实的点**：①2026-03 TotalRecall Reloaded 的技术细节仅有研究者自述[^38^]；②PAC 持久记忆层的产品化范围（Google 未明示哪些功能启用）[^55^]；③EDPB 智能眼镜声明为二手整理，建议引用前核对原文。

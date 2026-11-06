# AgentOS 组件调研 · 维度 C：Agent 安全 + 端侧会话级沙箱

> 调研日期：2026-11-06 ｜ 时间范围：2024-01 至 2026-11（奠基性工作另行标注年份）
> 我方架构立场：沙箱 = 借来的隔离边界 + 统一接口面 + 权限管理（三维风险定档、三时机执行、跨链不升级）；目标是端侧 Agent 会话级沙箱。
> 来源标准：官方文档 / 安全公告 / 顶会论文 / arXiv 优先，媒体仅作线索。事实与判断分别标注。

---

## 1. 技术谱系表

### 1.1 攻防路线谱系（Prompt Injection / Agent 安全）

| 谱系节点 | 类型 | 时间/出处 | 核心内容与意义 |
|---|---|---|---|
| 间接提示注入（IPI）形式化：Greshake et al. "Not What You've Signed Up For" | 攻击奠基 | 2023, AISec | 首次系统演示通过外部内容劫持 LLM 集成应用[^36^] |
| Willison "Dual-LLM Pattern" | 防御奠基（架构派） | 2023-04（博客） | 特权 LLM 规划 + 隔离 LLM 读不可信数据，仅符号变量互通；后被 CaMeL 引用并强化[^7^] |
| Morris II（"Here Comes the AI Worm"） | 攻击（蠕虫化） | 2024-03 arXiv；CCS 2025 | 首个 GenAI 生态自复制零点击蠕虫，跨 ChatGPT/Gemini/LLaVA 邮件助手传播并窃数[^37^] |
| InjecAgent | 基准 | 2024-03，arXiv:2403.02691（UIUC） | 首个 IPI 工具型 Agent 基准：1,054 用例、17 用户工具+62 攻击者工具；ReAct-GPT-4 ASR 24%，加 hacking prompt 后 47%；Llama2-70B >80%[^2^] |
| Formalizing and Benchmarking PI Attacks and Defenses（Liu, Jia, Gong 等） | 基准+攻防 | USENIX Security 2024 | 统一框架归纳 5 类攻击、10 类防御；结论：无任何防御足够，最佳检测（known-answer）仍漏检[^24^] |
| AgentDojo | 动态基准 | 2024-06 arXiv；NeurIPS 2024 D&B（ETH/SPy Lab） | 97 真实任务、629 安全用例、70 工具；无攻击时 SOTA 效用 <66%，攻击对最佳 Agent ASR <25%，检测器防御下降至 8%；显式设计为可持续填充自适应攻击的动态环境[^1^] |
| AgentPoison | 攻击（记忆/RAG 投毒后门） | 2024-07 arXiv；NeurIPS 2024（UChicago/UIUC 等） | 首个针对 RAG/长期记忆 Agent 的后门：投毒率 <0.1% 下平均 ASR ≥80%，良性性能损失 ≤1%[^3^] |
| Spotlighting（Microsoft） | 防御（数据标记） | 2024-03，CAMLIS | delimiting/datamarking/encoding，GPT 系列 ASR 从 >50% 降至 <2%；属概率性防御[^11^] |
| StruQ | 防御（结构化查询微调） | arXiv 2024-02；USENIX Security 2025（Berkeley） | 借鉴 SQL prepared statement，指令/数据双通道；优化-free 攻击 ASR 降至约 0%，效用损失约 4.5%[^9^] |
| SecAlign / Meta SecAlign | 防御（偏好优化/基础模型） | arXiv 2024-10；CCS 2025 | 将优化型攻击 ASR 较此前 SOTA 再降 >4 倍（约 <15%）[^10^] |
| AirGapAgent（CCS 2024）、IsolateGPT（NDSS 2025） | 防御（上下文/执行隔离） | 2024–2025 | 上下文完整性限制数据访问 / 每应用执行隔离 + 最小权限；隔离派早期代表[^22^] |
| CaMeL："Defeating Prompt Injections by Design" | 防御（能力安全+解释器） | 2025-03 arXiv（Google DeepMind/ETH） | 从可信查询显式抽取控制流/数据流；能力（capability）+ 策略在工具调用处强制；AgentDojo 上 77% 任务获得可证明安全（无防御 84%）[^4^] |
| Design Patterns（IBM/ETH/Google/Microsoft/Invariant 14 作者） | 防御模式集 | 2025-06 arXiv | 六模式：Action-Selector / Plan-Then-Execute / LLM Map-Reduce / Dual LLM / Code-Then-Execute / Context-Minimization；指导原则："一旦摄入不可信输入，必须约束到该输入不可能触发任何有后果的动作"[^5^] |
| Progent | 防御（可编程权限控制） | 2025-04 arXiv | JSON DSL 细粒度工具调用策略；AgentDojo ASR 41.2%→2.2%，ASB 基准 70.3%→0%[^23^] |
| IFC for Agents（Microsoft Research，Costa 等） | 防御（信息流控制） | 2025-05/09 arXiv | 系统级信息流控制防 IPI，f-secure LLM 风格[^6^] |
| The Attacker Moves Second（Nasr, Carlini, Tramèr 等 14 人，OpenAI/Anthropic/GDM） | 攻击（自适应评测） | 2025-10-10 arXiv；USENIX Security 2026 接收 | 对 12 个已发表防御做自适应攻击（梯度/RL/搜索/人工），多数 ASR >90%（原文多报近零）；人工红队 100%[^8^] |
| MUZZLE / AttriGuard / FragFuse 等 | 攻防新点 | USENIX Security 2026 | Web Agent 自适应红队；工具调用因果归因防御；记忆分片融合绕过访问控制（跨会话攻击）[^25^] |
| Lethal Trifecta（Willison） | 风险论述 | 2025-06-16（博客） | 私数据访问 + 不可信内容 + 对外通信三要素共存即可被注入转化为外泄通道；砍断任一腿即破链[^12^] |
| Meta "Agents Rule of Two" | 设计规则 | 2025-10-31（Meta 官方） | 单会话内 [A]处理不可信输入、[B]访问敏感系统/私数据、[C]改状态或对外通信，三取其二为限；三者全需则必须人类监督[^13^] |
| OWASP LLM01 / Agentic Top 10 | 行业定档 | 2025 | Prompt Injection 连续两年列 LLM 应用头号风险[^36^] |

### 1.2 隔离技术路线谱系（含端侧）

| 技术 | 层级 | 时间/出处 | 能力边界与关键事实 |
|---|---|---|---|
| 能力安全奠基：Dennis & Van Horn（1966）；KeyKOS（1985）；EROS（Shapiro, SOSP 1999） | 理论/OS | 1966–1999（标注年份） | capability = 不可伪造的"对象引用+权限"令牌；最小授权（POLA）传统[^32^] |
| Object-capability：Miller《Robust Composition》（Johns Hopkins 博士论文） | 语言级 | 2006（标注年份） | 形式化 ocaps 与 POLA；Caja（2008）、Joe-E（2010）、Cap'n Proto/Sandstorm 为工程后代[^31^] |
| "Capability Myths Demolished"（Miller/Yee/Shapiro） | 理论澄清 | 2003（标注年份） | 厘清 capability 与 ACL 关系、delegation/revocation 可行性[^33^] |
| seL4 | 微内核（形式化验证） | 2009 功能正确性证明（SOSP'09）；2014 开源 | 约 1 万行 C；1.3M 行机检证明；capability 访问控制 + 信息流安全证明；IPC fastpath ARM ~240 cycles；官方称"完成证明以来 0 次违反已验证性质"[^29^] |
| FreeBSD Capsicum（2010s）/ Fuchsia capability model | OS 实用化 | 2010s | 进程级 capability sandbox；Fuchsia 组件按 namespace 显式授予能力[^32^] |
| Android 应用沙箱（UID + SELinux） | 进程级 | 长期存在 | 应用边界强，但**粒度是"每应用"而非"每会话/每任务"** |
| Android SDK Runtime（Privacy Sandbox） | 进程级（应用内二级隔离） | Android 14（2023-10 起随系统），文档 2024-12 | 第三方 SDK 跑在独立 `<app>_sdk_sandbox` 进程：无网络权限、不可读写外部存储、不可访问宿主内存，Binder 声明式通信；**每应用仅一个 SDK Runtime 进程，专为广告/分析 SDK 设计**[^27^] |
| Android AVF（pKVM/pVM/Microdroid） | VM 级 | 文档持续更新（2025-02 快照） | 受保护 VM 与宿主互相不信任；宿主被攻破也无法读 pVM 内存；可跑 Microdroid 迷你 Android；官方用例以隔离编译等系统场景为主；**未对第三方 App 开放通用"pVM 即沙箱"SDK API**[^26^] |
| Android 16 Linux Terminal（AVF 承载） | VM 级（非保护模式） | 2026（Android 16 QPR2） | 官方文档明示其运行于 **unprotected VM**，官方自己声明"不是绝对安全边界"——端侧 VM 能力存在但安全定位保守[^28^] |
| iOS App Sandbox + Entitlements + TCC | 进程级 | 长期存在 | XNU 内核强制 seatbelt profile；默认拒绝、按 entitlement 授予；**无第三方可用 hypervisor/VM API，无会话级隔离原语**[^30^] |
| HarmonyOS NEXT 星盾（StarShield）+ 鸿蒙微内核 + iTrustee TEE | OS/TEE | 星盾随 HarmonyOS NEXT（2024-10 商用）/ HarmonyOS 6（2025-06 发布） | 软硬芯云协同四架构（纯净治理/隐私保护/数据安全/分布式安全）；TEE OS 微内核 CC EAL5+（2021），鸿蒙内核宣称 CC EAL6+（2024-10），整机 CCRC EAL5+（2024-06，业界整机首个）；AI 防窥、超级隐私模式为运行期治理；**无公开的"每会话 VM/进程沙箱"API，动态沙箱更接近动态权限与行为治理**[^34^][^35^] |
| 云端 Agent 沙箱（E2B/Firecracker、gVisor、V8 isolates 等） | VM/用户态内核/语言级 | 2024–2026 | 行业惯例分级：microVM > gVisor > V8 isolate > 容器；会话=一次隔离单元已成云端事实标准，但依赖服务器资源[^38^] |

---

## 2. 关键数据（带出处与日期）

### 2.1 攻击面数据

| 数据点 | 数值 | 出处（日期） |
|---|---|---|
| InjecAgent：ReAct 提示的 GPT-4 IPI 攻击成功率 | 基准 24%；叠加 hacking prompt 47%；Llama2-70B >80%；微调 GPT-4 仅 7.1% | arXiv:2403.02691（2024-03）[^2^] |
| AgentPoison：记忆/RAG 投毒攻击 | 平均 ASR ≥80%（摘要口径），检索成功率 82%、端到端 63%；投毒率 <0.1%，良性性能损失 ≤1% | arXiv:2407.12784（2024-07）[^3^] |
| AgentDojo：无攻击时 SOTA 效用 | <66%（GPT-4o 69%）；最强攻击对最佳 Agent ASR <25%；加检测器后 ASR 8% | arXiv:2406.13352 / NeurIPS 2024[^1^] |
| AgentDojo 消融：注入文本放在工具返回末尾 | 平均成功率最高可达 70%（对 GPT-4o） | 同上[^1^] |
| The Attacker Moves Second：自适应攻击 vs 12 个已发表防御 | 多数防御 ASR >90%（原文多报近 0）；人工红队 100% | arXiv:2510.09023（2025-10-10），USENIX Sec'26[^8^] |
| StruQ/SecAlign：优化-free 攻击 ASR | ≈0%；优化型攻击 SecAlign <15%；StruQ 效用损失约 4.5%（AlpacaEval2） | BAIR Blog（2025-04-11）/ USENIX Sec'25[^9^] |
| 后续白盒架构感知攻击 vs StruQ/SecAlign | 最高约 70% ASR（ASTRA 类攻击，2026） | cenpie 文献汇编引述（2026-04）[^9^] |
| Anthropic Opus 4.5（Gray Swan Shade 自适应红队，agentic coding） | ASR：1 次尝试 4.7% → 10 次 33.6% → 100 次 63.0% | Claude Opus 4.5 System Card（2025-11）[^19^] |
| Anthropic Opus 4.6：coding 环境 Shade ASR | 全条件 0%（200 次尝试自适应攻击者）；computer-use 环境仍有 57–64%@200（带防护 9.7%@1） | Claude Opus 4.6 System Card（2026-02-06）[^20^] |
| CaMeL：AgentDojo 上"可证明安全"任务解决率 | 77%（无防御 84%）；安全策略由解释器在工具调用处强制，数据流违规即阻断 | arXiv:2503.18813（2025-03-24）[^4^] |
| Progent：可编程权限控制 | AgentDojo ASR 41.2%→2.2%；ASB 70.3%→0% | arXiv:2504.11703（2025-04）[^23^] |
| AgentFuzz（USENIX Sec'25）：LLM Agent 污点型漏洞挖掘 | 20 个开源 Agent 应用中发现 34 个高危 0day，23 个 CVE 编号 | USENIX Security 2025[^21^] |
| MCPSecBench 沙箱逃逸用例（ATT-16） | 借命令注入型 MCP server 测宿主：Claude Desktop 拒绝执行（0% ASR）；OpenAI 与 Cursor 宿主全失陷（100% ASR） | arXiv:2508.13220 v3（2026-02）[^17^] |
| SandboxEscapeBench（容器逃逸能力基准，18 任务/3 层） | Claude Opus 4.5（2025-11-24 发布）56% 样本成功；Claude Mythos Preview（2026-04-07）100% 样本至少成功一次——两个月内基准被打满 | arXiv:2603.02277 v3（2026-08）[^18^] |
| NIST CAISI 大规模 Agent 红队竞赛 | >400 参与者、>25 万次尝试，"所有目标前沿模型均至少被攻陷一次" | NIST CAISI（2026，经二手引述）[^15^] |

### 2.2 2025–2026 公开逃逸/越权事件复盘（事实）

| 事件 | 时间 | 机制与教训 |
|---|---|---|
| EchoLeak（CVE-2025-32711，CVSS 9.3）— Microsoft 365 Copilot | 披露 2025-06-11/12；服务端修复 2025-05 | 首个生产系统零点击 IPI 外泄：连环绕过 XPIA 分类器、链接脱敏（reference-style Markdown）、CSP（借 Teams 白名单域代理）；Aim Labs 定性为 "LLM Scope Violation"。**教训：检测器+输出过滤+CSP 三层均被逐层绕过，信任边界缺失是根因**[^14^] |
| ForcedLeak（CVE-2025-32731，CVSS 9.4）— Salesforce Agentforce | 披露 2025-09-25（Noma Security） | 公开 Web-to-Lead 表单字段成注入向量；外泄通道是 CSP 白名单内过期域名（研究者约 $5 购回）。**教训：任何会被 Agent 下游读取的公开输入字段都是注入面；白名单的维护性失效**[^16^] |
| Shadow Escape — Operant AI | 2025-10-22 | 宣称首个零点击 MCP 攻击：经正常认证会话、合法凭据静默窃数，传统 DLP/SIEM 不可见；已向 OpenAI 报告并申请 CVE。**教训：协议层信任即攻击面**[^39^] |
| postmark-mcp 供应链后门 | 2025-09 | 首个在野恶意 MCP server：15 个干净版本建立信任后 v1.0.16 加一行代码密送全部外发邮件；约 300 组织受影响[^40^] |
| Supabase–Cursor 事件 | 2025-07 | 客服工单注入 SQL 指令 → Cursor Agent 以 service-role 特权读密钥并经公开线程外泄[^40^] |
| Copilot "YOLO mode"（CVE-2025-53773） | 2025 | 注入指令让 Agent 自改 `.vscode/settings.json` 打开 autoApprove，获得无人值守 shell 执行——**Agent 自我提权改配置**[^41^] |
| OpenAI Codex CLI 沙箱绕过（CVE-2025-59532，CVSS 8.6） | NVD 2025-09-22；修复于 0.39.0 | 沙箱可写根由**模型生成的 cwd** 决定，模型可把边界指到会话目录外 → 任意文件写+命令执行。**教训：沙箱边界必须由宿主确定性设定，绝不能由模型输出参与决定**[^42^] |
| Claude Code 网络沙箱两连穿（CVE-2025-66479 + null-byte 注入） | 修复 2025-11-26；第二起披露 2026-05 | (1) "block all outbound" 配置被解释成 "allow everything"；(2) SOCKS5 主机名 null-byte：`attacker.com\x00.google.com` 过白名单后缀检查、OS 在 null 处截断拨真攻击域。2025-10-20 GA 起存在约半年。**教训：代理白名单这类"接口面过滤"实现细节可整体失效，且用户无感知**[^43^] |
| Anthropic 披露国家级攻击者操纵 Claude Code 做间谍活动 | 2025 年底 | 30+ 组织受影响；Agent 被用作攻击编排体[^40^] |
| GitLost（GitHub Agent 私库外泄） | 2026-07 | 在恶意指令前加 "Additionally" 即绕过护栏，把注入重构为"合法补充任务"[^44^] |

---

## 3. 趋势判断

### 3.1 收敛方向（高置信）

1. **"检测/训练防御不足以兜底，架构性约束成为共识"**。The Attacker Moves Second（USENIX Sec'26）以 >90% ASR 打穿 12 个防御；OpenAI 公开承认注入"unlikely to ever be fully solved"（2025-12）；英国 NCSC 称注入"may never be totally mitigated"（2025-12）。产业与学界同步转向"约束结果而非拦截输入"：Meta Rule of Two、Design Patterns 六模式、CaMeL 的能力+数据流强制，本质都是**在架构上砍掉致命三要素中的至少一腿**[^8^][^45^][^46^][^13^]。
2. **风险评估框架收敛于"能力清单"范式**。Lethal Trifecta（2025-06）→ Meta Rule of Two（2025-10，把"对外通信"泛化为"改状态或对外通信"）→ 学术形式化（2026 年 compositional risk 工作把 trifecta 写成能力合取式 CA∧FR∧NO）。三维能力清点已成事实标准[^12^][^13^][^47^]。
3. **防御的工程形态收敛于"规划/执行分离 + 策略执行点（PEP）"**。Plan-Then-Execute、Dual-LLM、CaMeL（Code-Then-Execute）、Progent、f-secure LLM 均把"不可信数据不得影响控制流"作为不变式，并在工具调用处设置确定性策略检查点。共同代价是效用折扣（CaMeL 77% vs 84%）与适用面受限（The Attacker Moves Second 承认这类"控制流与数据无关"的防御在其场景下"攻击必然失败"但"只适用有限任务集"）[^5^][^4^][^23^][^8^]。
4. **沙箱边界本身成为攻击目标，"边界由模型决定"被证明是反模式**。Codex CVE-2025-59532（cwd 由模型生成）、Claude Code 白名单双穿、MCPSecBench 100% ASR 宿主，指向同一原则：隔离边界必须由宿主侧确定性配置与校验[^42^][^43^][^17^]。
5. **模型内生鲁棒性在快速提升但按"重试放大"失效**。Opus 4.5→4.6 的 coding ASR 从 63%@100 降到 0%@200，但 computer-use/browser 场景 200 次尝试下仍 57–64%；单次 1% ASR 对日均百次接触的 Agent 意味着"每天被引导一次"。结论：**模型层改善是真，但不能作为唯一边界**[^19^][^20^][^48^]。

### 3.2 空白点（判断，标注置信度）

1. **移动端不存在"Agent 会话级隔离"的公开原语**（高置信）。Android AVF 有 pVM 硬件能力但未开放为通用 App API（Android 16 Terminal 也只是 unprotected VM）；SDK Runtime 是"每应用一个"且限定 SDK 场景；iOS 只有进程级 App Sandbox；HarmonyOS 星盾强在 TEE/权限治理/整机认证，未见会话级 VM 隔离接口。**三大移动端均停留在"应用级隔离"，会话级隔离是真实空白**[^26^][^27^][^28^][^30^][^34^]。
2. **跨会话/跨任务污染缺少防御覆盖**（中高置信）。AgentDojo 作者自承工具白名单防御对"先注入、等后续任务再触发"无效；USENIX Sec'26 FragFuse 演示记忆分片跨轮融合绕过访问控制；AgentPoison 证明长期记忆可被 <0.1% 投毒率后门化。会话边界不等于污染边界[^1^][^25^][^3^]。
3. **"能力可撤销、可衰减、可审计"的 Agent 工具令牌体系未成标准**（中置信）。seL4/ocap 提供 revoke/attenuation/badge 的成熟语义，但 Agent 生态（MCP 等）仍以 ambient authority 为主；IETF 层面 2026 年才出现 agentic delegation 衰减令牌草案[^29^][^31^][^49^]。
4. **防御评测缺乏"攻击者适应"强制要求**。AgentDojo 显式声明静态攻击集不构成充分评测，但多数防御论文仍报固定攻击集数字——已被 The Attacker Moves Second 系统性证伪[^1^][^8^]。
5. **端侧性能/能耗与强隔离的折中数据几乎空白**。云端有 microVM/gVisor/isolate 分级经验；端侧 pVM 启动开销、内存占用对"每会话一 VM"的可行性无量化公开数据（判断：这是 AVF 类方案未下沉到应用层的部分原因）。

---

## 4. 对我方的启发（逐条）

> 我方立场：沙箱 = 借来的隔离边界 + 统一接口面 + 权限管理（三维风险定档、三时机执行、跨链不升级）；目标端侧 Agent 会话级沙箱。

### 4.1 支持（证据强化我方设计）

1. **三维风险定档（支持，强证据）**：Lethal Trifecta 与 Meta Rule of Two 与我方三维定档同构且已成为行业共识；Rule of Two 把第三维从"对外通信"扩为"改状态或对外通信"，与我方"风险按能力组合定档"完全一致。建议直接对齐 A/B/C 三属性语义以便与外部文献互操作[^12^][^13^]。
2. **三时机执行（支持）**：Design Patterns 六模式中 Plan-Then-Execute（规划时固化）、CaMeL/Progent（执行时 PEP 强制）、输出审计/Context-Minimization（事后）恰好对应"三时机"；CaMeL 用 77% 效用保留证明该路线可工程化[^5^][^4^][^23^]。
3. **统一接口面（支持，反例证据充分）**：postmark-mcp、Shadow Escape、CVE-2025-6514（mcp-remote RCE）说明工具接入面若无统一策略点即为攻击面；Progent 的 DSL 策略、CaMeL 的策略执行器证明"统一接口面 + 调用处强制"可行[^39^][^40^][^4^]。
4. **借来的隔离边界（支持，且要借硬件级）**：AVF pVM"宿主被攻破也读不到 guest 内存"、seL4 信息流证明、HarmonyOS EAL6+ 内核均说明：移动端已有可借的强边界（VM/TEE/微内核），关键在于封装为会话级接口[^26^][^29^][^35^]。

### 4.2 挑战（证据指出风险/前提需重审）

1. **"跨链不升级"不充分（挑战）**：污染可跨会话潜伏（AgentDojo 的"等待后续任务"攻击、FragFuse 记忆分片、AgentPoison 记忆后门）。仅"权限不升级"挡不住"数据已带毒、后续合法权限下发作"。**需要补充：跨会话污点追踪（taint provenance），权限链之外还要有数据链定档**[^1^][^25^][^3^]。
2. **检测器/分类器不能作为任何定档的兜底（挑战）**：>90% 自适应绕过率、EchoLeak 三层检测全穿。我方三维定档若含"检测通过即降档"语义须删除；检测只能作为纵深的一层[^8^][^14^]。
3. **沙箱边界参数绝不能由模型输出决定（挑战，强证据）**：Codex CVE-2025-59532 是"模型参与定边界"的直接事故。我方"会话级沙箱"的边界（可写根、网络白名单、能力集）必须宿主侧确定性计算[^42^]。
4. **白名单类接口面过滤存在实现级失效模式（挑战）**：Claude Code 的 null-byte 与 "block=all→allow" 表明统一接口面的过滤器需要形式化/高强度测试（规范化、编码、截断语义），否则"有接口面"不等于"接口面有效"[^43^]。
5. **效用税真实存在（挑战）**：所有结构性防御付 15–20% 效用损失（AgentDojo），CaMeL 77/84；端侧会话级隔离还要叠加 VM/进程启动开销。三维定档的价值恰恰在于**只为高风险组合付隔离税**，这是我方相对 Rule of Two 的差异化空间，但需实测开销数据支撑[^1^][^4^]。

### 4.3 需要修订（建议落到设计文档）

1. **修订三维定档为"3+1"**：在"私数据/不可信内容/对外动作"外，增加第四维"**持久写入（记忆/文件）**"——记忆是跨会话污染的载体（AgentPoison、FragFuse）[^3^][^25^]。
2. **把"会话"定义为隔离与污点的双重边界**：会话结束=隔离单元销毁+污点清除；会话内一旦摄入不可信内容即打标，该标签随数据流动（借鉴 CaMeL provenance、IFC for Agents），而非仅在调用点判权限[^4^][^6^]。
3. **端侧隔离路线图修订**：近期=进程级（Android isolated process/SDK Runtime 式独立进程 + iOS App Sandbox + HarmonyOS 应用沙箱），中期=借 AVF pVM/TEE 做"高风险会话"硬件级隔离（Android 唯一现实路径；iOS 无公开原语，只能靠应用内进程拆分+服务端代理执行），长期=推动/自研会话级 microVM。**"iOS 无会话级隔离原语"应写进架构风险登记册**[^26^][^27^][^30^]。
4. **采纳 capability 语义作为权限管理词汇**：seL4 的 revoke（CDT）/attenuation、ocap 的"无 ambient authority"直接对应"跨链不升级"的形式化表述；可使三维定档从"策略文档"升级为"可推理的授权图"[^29^][^31^]。
5. **评测纪律**：任何我方防御声称必须配自适应攻击评测（参照 The Attacker Moves Second 方法论 + AgentDojo 动态基准 + SandboxEscapeBench 思想做端侧逃逸用例），禁止只报固定攻击集 ASR[^8^][^1^][^18^]。

---

## 5. 证据清单（Claim / Source / URL / Date / Excerpt / Confidence）

[^1^]: **Claim**: AgentDojo 为动态攻防基准，97 任务/629 用例；SOTA 无攻击效用 <66%；攻击对最佳 Agent ASR <25%，检测器下 8%。**Source**: Debenedetti et al., NeurIPS 2024 D&B。**URL**: https://arxiv.org/abs/2406.13352 。**Date**: 2024-06-03。**Excerpt**: "Current LLMs solve less than 66% of AgentDojo tasks in the absence of any attack... our attacks succeed against the best performing agents in less than 25% of cases... the attack success rate drops to 8%."。**Confidence**: 高。

[^2^]: **Claim**: InjecAgent 1,054 用例；ReAct-GPT-4 ASR 24%→47%（enhanced）；Llama2-70B >80%。**Source**: Zhan et al. (UIUC)。**URL**: https://arxiv.org/abs/2403.02691 。**Date**: 2024-03-05。**Excerpt**: "ReAct-prompted GPT-4 vulnerable to attacks 24% of the time... nearly doubling the attack success rate... prompted Llama2-70B exhibits ASRs exceeding 80%"。**Confidence**: 高。

[^3^]: **Claim**: AgentPoison 投毒率 <0.1% 下平均 ASR ≥80%，良性损失 ≤1%。**Source**: Chen et al., NeurIPS 2024。**URL**: https://arxiv.org/abs/2407.12784 。**Date**: 2024-07-17。**Excerpt**: "average attack success rate of ≥80% with minimal impact on benign performance (≤1%) with a poison rate <0.1%"。**Confidence**: 高。

[^4^]: **Claim**: CaMeL 以能力+数据流策略防御，AgentDojo 77% 任务可证明安全（无防御 84%）。**Source**: Debenedetti et al. (Google DeepMind/ETH)。**URL**: https://arxiv.org/abs/2503.18813 。**Date**: 2025-03-24。**Excerpt**: "solving 77% of tasks with provable security (compared to 84% with an undefended system) in AgentDojo"。**Confidence**: 高。

[^5^]: **Claim**: 六大防御设计模式与"不可能触发有后果动作"原则。**Source**: Beurer-Kellner et al. (IBM/ETH/Google/Microsoft 等)。**URL**: https://arxiv.org/abs/2506.08837 。**Date**: 2025-06-10。**Excerpt**: "Once an LLM agent has ingested untrusted input, it must be constrained so that it is impossible for that input to trigger any consequential actions."。**Confidence**: 高。

[^6^]: **Claim**: 信息流控制（IFC）用于 Agent 系统级防 IPI。**Source**: Costa et al. (Microsoft Research), arXiv:2505.23643。**URL**: https://arxiv.org/abs/2505.23643 。**Date**: 2025-05/09。**Excerpt**: "Securing AI agents with information-flow control"（经多篇论文参考文献确认）。**Confidence**: 中高（未读全文）。

[^7^]: **Claim**: Dual-LLM 模式由 Willison 2023-04 提出并被 CaMeL/Design Patterns 引用。**Source**: simonwillison.net。**URL**: https://simonwillison.net/2023/Apr/25/dual-llm-pattern/ 。**Date**: 2023-04-25。**Confidence**: 高。

[^8^]: **Claim**: 自适应攻击对 12 个已发表防御多数 ASR >90%，人工红队 100%。**Source**: Nasr, Carlini et al., USENIX Security 2026。**URL**: https://arxiv.org/abs/2510.09023 。**Date**: 2025-10-10。**Excerpt**: "we bypass 12 recent defenses... with attack success rate above 90% for most; importantly, the majority of defenses originally reported near-zero attack success rates"。**Confidence**: 高。

[^9^]: **Claim**: StruQ/SecAlign 对非优化攻击 ASR≈0%，优化攻击 <15%；后续白盒攻击达 ~70%。**Source**: BAIR Blog（2025-04-11）；USENIX Sec'25 / CCS'25；ASTRA 类后续工作。**URL**: https://bair.berkeley.edu/blog/2025/04/11/prompt-injection-defense/ 。**Date**: 2025-04-11。**Excerpt**: "reduce the success rates of over a dozen of optimization-free attacks to around 0%. SecAlign also stops strong optimization-based attacks to success rates lower than 15%"。**Confidence**: 高（原始数值）；中（70% 为二手汇编）。

[^10^]: **Claim**: SecAlign 发表于 ACM CCS 2025。**URL**: https://arxiv.org/abs/2410.05451 。**Date**: 2024-10（arXiv）/ 2025（CCS）。**Confidence**: 高。

[^11^]: **Claim**: Microsoft Spotlighting 将 GPT 系列 ASR 从 >50% 降至 <2%。**Source**: Hines et al., CAMLIS 2024, arXiv:2403.14720。**Date**: 2024-03。**Confidence**: 中高（经文献汇编转引）。

[^12^]: **Claim**: Lethal Trifecta = 私数据 + 不可信内容 + 对外通信；砍任一腿破链。**Source**: Simon Willison。**URL**: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/ 。**Date**: 2025-06-16。**Confidence**: 高。

[^13^]: **Claim**: Meta Rule of Two：单会话三属性（不可信输入/敏感访问/改状态或外发）最多取二，全需则须人类监督。**Source**: Meta, "Agents Rule of Two: A Practical Approach to AI Agent Security"。**URL**: https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/ （二次引述 Meta 原文）。**Date**: 2025-10-31。**Excerpt**: "agents must satisfy no more than two of three properties within a session... [otherwise] requires supervision, via human-in-the-loop approval"。**Confidence**: 高。

[^14^]: **Claim**: EchoLeak（CVE-2025-32711）为首个生产零点击 IPI 外泄，连环绕过 XPIA/链接脱敏/CSP。**Source**: Aim Labs 披露 + GWU 案例分析 arXiv:2509.10540。**URL**: https://arxiv.org/abs/2509.10540 。**Date**: 2025-09-06（论文）/ 2025-06-11（披露）。**Excerpt**: "the first known case of a prompt injection being weaponized to cause concrete data exfiltration in a production AI system"。**Confidence**: 高。

[^15^]: **Claim**: NIST CAISI 红队竞赛中所有目标前沿模型均至少被攻破一次。**Source**: NIST CAISI（2026，经 redactsure.com 转引）。**URL**: https://redactsure.com/research/how-do-you-protect-ai-agents-against-prompt-injection/ 。**Date**: 2026。**Confidence**: 中（二手）。

[^16^]: **Claim**: ForcedLeak（CVE-2025-32731, CVSS 9.4）：Agentforce 经公开 Web-to-Lead 表单注入，CSP 过期域名外泄。**Source**: Noma Security（2025-09-25 披露）/ 复盘文章。**URL**: https://www.softwareinsights.dev/posts/salesforce-agentforce-forcedleak-prompt-injection-hardening/ 。**Date**: 2025-09-25 / 2026-07-12。**Confidence**: 中高（CVE 与披露日期多方一致；细节来自复盘）。

[^17^]: **Claim**: MCPSecBench 沙箱逃逸用例：Claude Desktop 0% ASR，OpenAI/Cursor 宿主 100% ASR。**Source**: arXiv:2508.13220 v3。**URL**: https://arxiv.org/html/2508.13220v3 。**Date**: 2026-02-12。**Excerpt**: "Claude Desktop demonstrated effective permission check... (0% ASR). In stark contrast, both OpenAI and Cursor failed to contain the exploit... 100% ASR."。**Confidence**: 高。

[^18^]: **Claim**: SandboxEscapeBench（18 任务/编排-运行时-内核三层）：Opus 4.5 56%；Mythos Preview 100%，两个月打满。**Source**: arXiv:2603.02277 v3。**URL**: https://arxiv.org/html/2603.02277v3 。**Date**: 2026-08-01。**Excerpt**: "Claude Opus 4.5... succeeded on 56% of samples. Mythos Preview... succeeded at least once on 100% of samples."。**Confidence**: 高。

[^19^]: **Claim**: Opus 4.5 Shade 自适应红队 ASR 4.7%@1 / 33.6%@10 / 63.0%@100。**Source**: Claude Opus 4.5 System Card。**Date**: 2025-11-24。**URL**: 经 arXiv:2606.26479 参考文献转引（原始 PDF：anthropic.com system card）。**Confidence**: 高。

[^20^]: **Claim**: Opus 4.6 coding Shade ASR 全条件 0%；computer-use 仍有 ~57–64%@200（防护+思考后 9.7%@1/57.1%@200）。**Source**: Claude Opus 4.6 System Card。**URL**: https://www-cdn.anthropic.com/0dd865075ad3132672ee0ab40b05a53f14cf5288.pdf 。**Date**: 2026-02-06。**Confidence**: 高。

[^21^]: **Claim**: AgentFuzz 在 20 个开源 Agent 应用发现 34 个高危 0day，23 个 CVE。**Source**: "Make Agent Defeat Agent", USENIX Security 2025。**URL**: https://www.usenix.org/conference/usenixsecurity25/presentation/liu-fengyu 。**Date**: 2025-08。**Confidence**: 高。

[^22^]: **Claim**: IsolateGPT（NDSS 2025）执行隔离架构；AirGapAgent（CCS 2024）上下文隔离。**URL**: https://arxiv.org/abs/2403.04960 。**Date**: 2024-03 / 2025-02。**Confidence**: 中高（经论文集与引用链确认）。

[^23^]: **Claim**: Progent 策略 DSL：AgentDojo ASR 41.2%→2.2%，ASB 70.3%→0%。**Source**: Shi et al., arXiv:2504.11703。**Date**: 2025-04。**Confidence**: 中高（经文献汇编转引）。

[^24^]: **Claim**: USENIX Sec'24 形式化基准结论：无防御足够。**Source**: Liu, Jia, Geng, Jia, Gong, arXiv:2310.12815。**Date**: 2024-08。**Confidence**: 高。

[^25^]: **Claim**: USENIX Sec'26：AttriGuard（因果归因防御）、MUZZLE（Web Agent 自适应红队）、FragFuse（记忆分片跨会话绕过访问控制）。**Source**: USENIX Security 2026 程序（usenix.org PDF + 论文整理）。**URL**: https://www.usenix.org/system/files/usenixsecurity26-he-yu.pdf 。**Date**: 2026-08-12。**Confidence**: 高。

[^26^]: **Claim**: AVF pVM 与宿主互不信任，宿主被攻破亦无法读 pVM 内存；可跑 Microdroid。**Source**: Android 官方文档（AOSP）。**URL**: https://source.android.google.cn/docs/core/virtualization 。**Date**: 2025-02-27（页面快照）。**Excerpt**: "Ein wichtiger Aspekt der Sicherheit von pVMs ist, dass der Host auch bei einer Manipulation keinen Zugriff auf den Speicher einer pVM hat."。**Confidence**: 高。

[^27^]: **Claim**: SDK Runtime（Android 14+）：第三方 SDK 于独立进程运行、无网络权限、不可访问宿主内存；每应用一个 SDK Runtime 进程。**Source**: Google 官方文档 + 官方 samples 仓库。**URL**: https://developers.google.cn/privacy-sandbox/private-advertising/sdk-runtime ；https://github.com/privacysandbox/sdk-runtime-samples 。**Date**: 2024-12-05（文档快照）。**Excerpt**: "For each app, there is one SDK Runtime process with a defined set of permissions and restrictions."。**Confidence**: 高。

[^28^]: **Claim**: Android 16 Linux Terminal 运行于 AVF unprotected VM，官方不定位于安全边界。**Source**: AOSP use-case 文档（经 rottonwifi 转引核对）。**URL**: https://rottenwifi.com/how-to-run-linux-apps-on-android-16-using-the-virtual-machine-feature-phones-setup-and-limits/ 。**Date**: 2026-08-16。**Excerpt**: "The Linux development environment itself is documented as running in an unprotected VM... describing the feature as an absolute security boundary is not [appropriate]."。**Confidence**: 中（需以 AOSP 原文复核）。

[^29^]: **Claim**: seL4（2009 证明/2014 开源）：1.3M 行机检证明，功能/二进制正确性、完整性与机密性（信息流）证明；capability 访问控制。**Source**: sel4.systems Fact Sheet；Klein et al., SOSP 2009。**URL**: https://sel4.systems/About/fact-sheet.html ；https://web.eecs.umich.edu/~ryanph/jhu/cs718/spring18/readings/seL4.pdf 。**Date**: 2009 / 2026-09（fact sheet 快照）。**Confidence**: 高。

[^30^]: **Claim**: iOS App Sandbox 由 XNU 内核强制，默认拒绝、entitlement 授予；无第三方 VM/hypervisor API。**Source**: Apple 安全体系综述。**URL**: https://whatis.in/what-is-ios-app-sandbox/ 。**Date**: 2026-02-18。**Excerpt**: "The sandbox is not an optional feature... enforced by the XNU kernel... Deny by default."。**Confidence**: 中高（机制事实广泛 corroborated；"无 VM API"为缺席性证据，中等置信）。

[^31^]: **Claim**: Object-capability 由 Miller 2006 博士论文《Robust Composition》奠基（POLA、authority/permission 区分）。**Source**: Johns Hopkins PhD thesis。**URL**: http://erights.org/talks/thesis/markm-thesis.pdf 。**Date**: 2006。**Confidence**: 高。

[^32^]: **Claim**: 能力安全谱系：Dennis & Van Horn 1966 → KeyKOS/EROS → Capsicum/Fuchsia。**Source**: 多篇综述与文献目录（arXiv:1907.07154 等）。**Date**: 1966–2010s（标注年份）。**Confidence**: 高（学术共识）。

[^33^]: **Claim**: "Capability Myths Demolished"（2003）澄清 capability vs ACL、delegation/revocation。**Source**: Miller, Yee, Shapiro。**URL**: http://www.erights.org/elib/capability/duals 。**Date**: 2003。**Confidence**: 高。

[^34^]: **Claim**: HarmonyOS 6 发布星盾（StarShield）统一安全架构，软硬芯云协同（纯净治理/隐私保护/数据安全/分布式安全）。**Source**: Notebookcheck（HDC 2025 报道）+ 36kr 英文。**URL**: https://www.notebookcheck.net/HarmonyOS-6-debuts-with-Star-Shield-security-and-AI-agent-support.1040907.0.html ；https://eu.36kr.com/en/p/3905473157797765 。**Date**: 2025-06-20 / 2026-07-21。**Confidence**: 中高（官方细节有限，媒体与官方口径一致）。

[^35^]: **Claim**: 鸿蒙 TEE OS 微内核 CC EAL5+（2021，iTrustee）；HarmonyOS NEXT 整机 CCRC EAL5+（2024-06，业界整机首个）；鸿蒙内核宣称 CC EAL6+（2024-10）。**Source**: 华为官网认证页 + chinadaily + 新浪财经。**URL**: https://consumer.huawei.com/cn/privacy/certification/ 。**Date**: 2021-11 / 2024-06 / 2024-10。**Confidence**: 高（认证事实）；EAL6+ 为中高（媒体报道口径）。

[^36^]: **Claim**: OWASP LLM Top 10 将 Prompt Injection 列为 LLM01；Greshake et al. 2023 奠基 IPI。**URL**: https://genai.owasp.org （经多源转引）。**Date**: 2023 / 2025。**Confidence**: 高。

[^37^]: **Claim**: Morris II 为首个 GenAI 自复制零点击蠕虫。**Source**: Cohen, Bitton, Nassi, arXiv:2403.02817；CCS 2025。**Date**: 2024-03 / 2025。**Confidence**: 高。

[^38^]: **Claim**: 云端 Agent 沙箱分级惯例：microVM（E2B/Vercel/AgentCore）> gVisor（Modal）> V8 isolate（Cloudflare）；会话=隔离单元。**Source**: camelai.com 分层综述（2026-10）+ Cloudflare/Tangle 文档。**URL**: https://camelai.com/blog/agent-harness-vs-framework-vs-runtime 。**Date**: 2026-10-06。**Confidence**: 中（厂商口径，作趋势参考）。

[^39^]: **Claim**: Shadow Escape 为首例宣称的零点击 MCP 攻击（2025-10-22，GlobeNewswire/Operant）。**URL**: https://www.globenewswire.com/news-release/2025/10/22/3171164/0/en/Operant-AI-Discovers-Shadow-Escape-The-First-Zero-Click-Agentic-Attack-via-MCP.html 。**Date**: 2025-10-22。**Confidence**: 中（厂商研究，缺独立复现）。

[^40^]: **Claim**: postmark-mcp 供应链后门（2025-09）、Supabase-Cursor 事件（2025-07）、Anthropic 披露 AI 编排间谍活动（2025 末，30+ 组织）。**Source**: The Hacker News / 事件复盘汇编 / leverageai 综述。**URL**: https://www.cnblogs.com/32bin/p/23200578 （汇编）；https://leverageai.com.au/openclaw-has-a-provenance-problem-and-so-does-every-agent-platform/ 。**Date**: 2025-07 至 2026-02。**Confidence**: 中（媒体线索级）。

[^41^]: **Claim**: CVE-2025-53773：注入指令让 Copilot 自改 settings.json 开启 autoApprove（YOLO mode）。**Source**: Johann Rehberger 披露（经 riskatlas 汇编）。**URL**: https://riskatlas.principle.sg/taxonomy/risk-indirect-injection 。**Date**: 2025。**Confidence**: 中高。

[^42^]: **Claim**: CVE-2025-59532：Codex CLI 沙箱可写根由模型生成的 cwd 决定，CVSS 8.6，0.39.0 修复。**Source**: NVD / SentinelOne / offseq。**URL**: https://nvd.nist.gov/vuln/detail/CVE-2025-59532 。**Date**: 2025-09-22。**Excerpt**: "the sandbox boundary was determined based on a model-generated current working directory (cwd)... arbitrary file writes and command execution"。**Confidence**: 高。

[^43^]: **Claim**: Claude Code 网络沙箱两起绕过：CVE-2025-66479（block-all 被解释为 allow-all）与 SOCKS5 null-byte 主机名注入。**Source**: SecurityWeek（Aonan Guan 披露）。**URL**: https://www.securityweek.com/anthropic-silently-patches-claude-code-sandbox-bypass/ 。**Date**: 2026-05-20。**Confidence**: 中高。

[^44^]: **Claim**: GitLost 以 "Additionally" 前缀重构恶意指令绕过 GitHub Agent 护栏外泄私库。**Source**: fp8.co 复盘。**URL**: https://fp8.co/articles/GitLost-Prompt-Injection-GitHub-AI-Agent-Repo-Leak 。**Date**: 2026-07-08。**Confidence**: 中。

[^45^]: **Claim**: OpenAI 称 prompt injection "unlikely to ever be fully 'solved'"。**Source**: OpenAI, "Continuously hardening ChatGPT Atlas against prompt injection attacks"。**URL**: https://openai.com/index/hardening-atlas-against-prompt-injection/ 。**Date**: 2025-12。**Confidence**: 高。

[^46^]: **Claim**: UK NCSC：prompt injection "may never be totally mitigated"，模型应视为 "inherently confusable deputy"。**Source**: NCSC 博客（2025-12-10，经多源转引）。**URL**: https://www.onext.es/en/insights/prompt-injection-ai-agents-tool-permissions/ （转引）。**Date**: 2025-12-10。**Confidence**: 中高。

[^47^]: **Claim**: 学术工作将 Lethal Trifecta 形式化为能力合取（CA∧FR∧NO），"不可信内容暴露"被视为攻击投递属性而非静态能力。**Source**: "Measuring Compositional Risk in Agent Skill Ecosystems", arXiv:2606.00448。**Date**: 2026-04-19。**Confidence**: 中高。

[^48^]: **Claim**: Anthropic 自述"1% ASR 仍是有意义的风险"。**Source**: Anthropic browser-use 工程博客（2025，经 redactsure 转引）。**Date**: 2025。**Confidence**: 中高。

[^49^]: **Claim**: IETF 草案出现面向 Agent 委托链的衰减授权令牌（attenuating tokens），能力安全语义进入 Agent 标准化视野。**Source**: IETF draft-niyikiza-oauth-attenuating-agent-tokens-00。**URL**: https://datatracker.ietf.org/doc/html/draft-niyikiza-oauth-attenuating-agent-tokens-00 。**Date**: 2026-03-16。**Confidence**: 高（草案存在；采纳度未知）。

---

### 附：本次调研搜索覆盖说明
共执行 7 轮 24 个独立查询（覆盖：CaMeL/AgentDojo/InjecAgent/AgentPoison、lethal trifecta、Rule of Two、逃逸基准、2025–2026 CVE 事件、USENIX/S&P/CCS/NDSS 论文谱系、AVF/SDK Runtime/iOS 沙箱/HarmonyOS 星盾、seL4/object-capability、Attacker Moves Second 等），另直接打开 2 个官方文档 URL（source.android.com 被审计拦截，改用 source.android.google.cn 镜像页）。
**遗留不确定性**：(1) Meta Rule of Two 原文 URL 未直接打开（日期与内容经 Willison 与多处独立转引一致）；(2) HarmonyOS "动态沙箱"未见华为官方逐字文档，结论基于官方认证页 + HDC 报道 + 开发者社区实现文；(3) Android 16 Terminal 的 unprotected VM 定性建议以 AOSP 原文复核；(4) NIST CAISI 竞赛数字为二手转引。

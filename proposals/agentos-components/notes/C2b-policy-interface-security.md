# C2b 策略、凭证、接口面与 Agent 安全

**子模块**：C2b（沙箱 Q2、Q3、Q4、Q5、Q8；接缝 J3 安全侧）
**调研日期**：2026-11-05
**检索说明**：本轮联网检索额度在中途用尽，之后只能对已知一手 URL 做抓取。因此以下几块没有做到一手核实，文中已逐处标「待核实」：Okta Cross App Access、Android Keystore/StrongBox/Credential Manager、iOS Keychain/Secure Enclave、HarmonyOS HUKS、iOS 26/27 App Intents 的官方文档、Anthropic computer use / OpenAI CUA / Gemini Computer Use 的官方细节、OPA/Rego 侧的 2025–2026 进展、NIST AI 600-1、Google SAIF、CurXecute/MCPoison 等 Cursor 类 CVE。
**立场输入**：SBX-2 至 SBX-9。未取得《AgentOS 沙箱系统设计》原文，SBX-5 的三个维度按第 5 节所述「业界常见维度」做假设（见 §7.2）。
**本库已有资料**：只浏览了 `surveys/ai-native-os-agent-CN.md` 中与 AppFunctions、App Intents 相关的部分，以掌握已有结论为限，未精读。引用均回到原始来源。

---

## §0 摘要

1. MCP 规范在 2026-07-28 发布了新一版，已经与「2025-11-25」大不相同：去掉会话与初始化握手、改为无状态；Tasks 从核心移出成为扩展；引入 Multi Round-Trip Requests；弃用 Roots、Sampling、Logging 与动态客户端注册（DCR）。接口面的「异步」与「需要输入」要素已有标准形态，但仍处于扩展或变动期 [R1][R2]（A，L3）。
2. MCP 工具注解（readOnlyHint、destructiveHint、idempotentHint、openWorldHint）至今只是「提示」，规范明确要求客户端把注解视为不可信，除非来自可信服务器；dry-run 与 undo 在 MCP 与 AppFunctions 中都没有标准化位置 [R2][R3][R4]（A，L3）。这是七要素里支持度最低的两项。
3. 目前最强的 Agent 防护都落在「确定性执行层」而非「模型层」：CaMeL 在 AgentDojo 上以可证明安全解出 77% 任务（无防护 84%）[R5]；FIDES 在启用策略检查时挡住 AgentDojo 全部注入 [R6]；Progent 把成功率从 39.9% 降到 1.0%（v2 口径）[R7]（均 A，L1）。这支持 SBX-4、SBX-6、SBX-7 的执行层思路，但三者都只在基准上验证，产品化的只有 Chrome 的 User Alignment Critic 与 Origin Sets（L3，B）[R8]。
4. 基于模型或分类器的防护在自适应攻击下不可靠：12 个已发表防护被自适应攻击绕过，多数攻击成功率超过 90%，人工红队对全部防护成功 [R9]（A，L1）。Anthropic 自家的 auto mode 分类器在真实越界样本上漏报率为 17%（完整流水线）[R10]（B）。结论：分类器只能当辅助层。
5. 凭证经纪人（SBX-8）已成为云沙箱的产品默认模式：Vercel Sandbox（2026-02-23）、Deno Sandbox、Daytona、Docker sandboxes、Fly Tokenizer、Claude Code on the web 的 git 代理都是「沙箱内无明文、出口注入」[R11][R12]（B，L3）。反面是 Nx s1ngularity 之类事件说明，只要明文在环境变量或文件里，Agent 的 CLI 本身就成了扫描器 [R13]（C）。
6. Agent 身份正在被收进平台层，对 SBX-9 构成挑战：Microsoft Entra Agent ID 把 Agent 做成一等身份（blueprint、agent identity、条件访问可作用于 OBO 交换）[R14]；Windows Agent Workspace 为 Agent 分配独立身份 [R15]；Android AppFunctions 用 `EXECUTE_APP_FUNCTIONS` 在平台层给调用方放行 [R4]；鸿蒙 Skill 上架与华为账号认证绑定 [R16]。判断：「身份归应用」需要修订为「会话级 Agent 主体由系统签发，用户对服务的身份仍归应用」。
7. 确认疲劳有一手数据：Claude Code 用户手动确认的批准率为 93% [R10]；沙箱化把权限提示减少 84%（内部使用口径，无方法学）[R17]。Register 引用的 97% 与之冲突，未核实到一手出处（C）。监督界面的出路是「减少提示 + 事后可审」，而不是「更多弹窗」。
8. 2025–2026 事件复盘表明，没有一个事件是靠「更严格的权限弹窗」能避免的：EchoLeak、GitHub MCP、Supabase MCP 的攻击链全程使用 Agent 合法持有的权限；真正能阻断的是信息流标签、出口治理与「不同时具备三要素」（Meta Rule of Two，2025-10-31）[R18]。
9. SBX-5 的三维模型需要补一个「输入污染状态」维度：Rule of Two 的三个属性之一是「处理不可信输入」，它是会话的动态状态，而不是动作的静态属性；若三维都是动作属性，就无法表达 Rule of Two（判断，见 §7.2）。
10. 端侧最大的空白是「谁在 OS 层强制执行信息流与出口策略」：云侧有 AgentCore Policy（Cedar，2026-03-03 GA）[R19]、Vercel/OpenShell 的网络策略；手机侧 AppFunctions 仍是 Android 16 起的私有预览（截至 2026-05）[R4]，HarmonyOS 的安全框架只有白皮书口径 [R16]，未找到公开可审计的端侧策略引擎。

---

## §1 技术谱系表

成熟度 L1–L4，端侧可迁移性按第 3.4 节。

### 1.1 策略与授权（Q2）

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 策略语言（可分析） | Cedar | AWS | 2024（OOPSLA 论文 arXiv 2403.04651） | 用 Lean 建模、支持可判定的策略分析，如证明重构前后授权集合不变 | L3 | 需改造：Rust 实现，可嵌入 native 服务；手机侧无现成宿主 |
| 策略语言（通用） | OPA/Rego | CNCF | 先于 2024 | 通用策略引擎，云原生事实标准 | L3 | 待核实：本轮未检索 |
| 托管策略产品 | AgentCore Policy | AWS | 2026-03-03 GA | 自然语言生成 Cedar，挂在 AgentCore Gateway 上逐请求评估 | L3 | 不可迁移（云网关）；其「工具调用前置评估」模式可迁移 |
| 声明式沙箱策略 | OpenShell | NVIDIA | 2026-03（alpha，第三方口径） | YAML 策略，文件系统与进程静态锁定，网络与推理动态热更新，默认拒绝 | L2 | 需改造：Linux 容器宿主，手机需映射到 SELinux/seccomp/网络代理 |
| 能力/权限控制层 | Progent | UC Berkeley、UCSB | 2025-04（arXiv 2504.11703） | 可编程的最小权限策略，含参数约束，由 LLM 或人生成 | L1 | 可直接迁移（策略层与模型无关） |
| 任务级策略生成 | Conseca | Google | 2025-01（HotOS 2025） | 仅用可信上下文由模型生成任务策略，确定性评估器执行 | L1 | 可直接迁移 |
| 信息流控制 | FIDES | Microsoft Research | 2025-05（v2 2025-09） | 规划器跟踪机密性与完整性标签，确定性执行，变量化隐藏工具结果 | L1 | 需改造：需要运行时跟踪每个工具结果的标签 |
| 控制流与数据流分离 | CaMeL | Google DeepMind、ETH | 2025-03（v2 2025-06） | 特权/隔离双 LLM + 自定义解释器 + 能力标签，可证明安全 | L1 | 需改造：解释器可跑在端，但需两个模型调用，成本高 |
| 执行隔离 | IsolateGPT | 华盛顿大学等 | NDSS 2025 | 为 LLM 应用做执行隔离，四分之三查询开销低于 30% | L1 | 需改造：隔离单元要映射到端侧进程/沙箱 |
| 设计模式 | 《Design Patterns for Securing LLM Agents against Prompt Injections》 | Beurer-Kellner 等 14 位作者 | 2025-06 | 系统化一组抗注入设计模式 | L1 | 可直接迁移（设计方法） |
| 会话级属性约束 | Agents Rule of Two | Meta | 2025-10-31 | 一个会话最多同时具备三属性中的两个 | L2（实践规则） | 可直接迁移 |

### 1.2 凭证与身份（Q3）

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 出口头部注入 | Vercel Sandbox credential injection | Vercel | 2026-02-23 | 在网络策略里声明头部转换，沙箱代码不见密钥，规则可对运行中沙箱热更新 | L3 | 需改造：手机没有出口 HTTPS 代理层，需系统网络服务充当 |
| 占位符替换 | Deno Sandbox secrets、Daytona secrets | Deno、Daytona | 2026 | 沙箱内只有占位符，访问允许主机时才替换成真值 | L3（Deno 为 beta） | 同上 |
| 加密令牌代理 | Fly Tokenizer | Fly.io | 2025（开源项目） | 无状态代理持有私钥，客户端发送加密的密钥头，由代理解密并注入 | L2 | 需改造 |
| 代理持凭证 | Claude Code on the web 的 git 代理 | Anthropic | 2025-10-20 | 沙箱内 git 客户端只持作用域凭证，代理校验操作后附加真实令牌 | L3 | 需改造 |
| 授权规范 | MCP authorization（OAuth 2.1、RFC 8707、RFC 9728、禁止令牌透传、Client ID Metadata Documents） | MCP 社区 | 2025-06 至 2026-07 | 把 MCP 服务器定位为 OAuth 资源服务器，令牌必须绑定受众 | L3 | 可直接迁移到网络型 MCP；对 AppFunctions 这类本地调用不适用 |
| Agent 一等身份 | Microsoft Entra Agent ID | Microsoft | 预览 2025，GA 日期待核实（第三方称 2026-05） | blueprint 模板、agent identity、条件访问作用于 OBO | L3 | 不可迁移（企业 IdP）；模型可参考 |
| 跨应用授权 | Okta Cross App Access | Okta | 待核实 | 待核实 | 待核实 | 待核实 |
| 端侧凭证原语 | Android Keystore/StrongBox/Credential Manager、iOS Keychain/Secure Enclave、HarmonyOS HUKS | Google、Apple、华为 | 长期 | 密钥不可导出、使用需授权 | L4 | 可直接迁移（本轮未联网核实具体版本，属背景知识） |

### 1.3 接口面（Q4）

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 开放协议 | MCP 规范 2025-11-25、2026-07-28 | MCP 社区（最初 Anthropic） | 2025-11、2026-07 | 工具 schema、注解、授权、Tasks 扩展、MRTR | L3 | 需改造：stdio/HTTP 在手机上需系统代理 |
| 注册与发现 | MCP Registry（预览） | MCP 社区 | 2025-09-08 | 公共目录，可建公共/私有子注册表；预览期无持久性保证 | L2 | 可直接迁移（元数据） |
| 平台内 MCP | Windows On-device Agent Registry | Microsoft | 公共预览（Ignite 2025） | 本地 MCP 服务器注册、MCP 代理网关、默认容器化、MSIX/MCPB 打包 | L2 | 概念可迁移 |
| 手机原生函数 | Android AppFunctions | Google | Android 16；Gemini 集成私有预览（截至 2026-05） | 应用暴露函数给 Agent，`EXECUTE_APP_FUNCTIONS` 放行，XML schema 索引 | L2 | 原生 |
| 手机原生意图 | iOS App Intents | Apple | iOS 16 起；iOS 26/27 变化待核实 | 实体与意图元数据，Siri/Spotlight 集成 | L4 | 原生（官方文档本轮未核实） |
| 鸿蒙智能体框架 | HMAF 2.0、意图框架、Skill | 华为 | HDC 2026（2026-06） | 意图即服务，A2A、A2UI，兼容 MCP | L3（厂商口径） | 原生 |
| UI 自动化 | Android UI automation 框架、Gemini 自动化 | Google | 2026-02-25 公布，Galaxy S26 与 Pixel 10 | 无集成的应用也可被 Agent 操作 | L2 | 原生 |
| computer use API | Anthropic、OpenAI、Google | — | 2024–2025 | 截图加点击的通用 UI 控制 | 待核实 | 待核实 |

### 1.4 Agent 安全（Q5）

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 攻防基准 | AgentDojo | ETH 等 | 2024（arXiv 2406.13352） | 97 个任务、629 个安全测试用例 | L2 | 不涉及 |
| 自适应攻击 | The Attacker Moves Second | Nasr、Carlini 等 14 人 | 2025-10-10 | 绕过 12 个已发表防护 | L1 | 不涉及 |
| 逃逸基准 | SandboxEscapeBench | Marchand 等（ICML 2026） | 2026-03-01 | 评估 LLM 能否逃出 Docker/OCI 容器 | L1 | 不涉及 |
| 浏览器内 Agent 安全架构 | User Alignment Critic、Origin Sets | Google Chrome | 2025-12-08 | 独立批评模型只看动作元数据，源集合限制可读写范围 | L3 | 可直接迁移（设计模式） |
| 分类器自动审批 | Claude Code auto mode | Anthropic | 2026-03 预览，2026-07-10 GA（第三方口径） | 两阶段分类器，剥离工具结果 | L3 | 需改造 |
| 风险框架 | OWASP Top 10 for Agentic Applications 2026 | OWASP GenAI Security Project | 2025-12-09 | 十类 ASI 风险 | — | 不涉及 |

---

## §2 关键数据

| 指标 | 数值 | 条件 | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| CaMeL 可证明安全解出任务比例 | 77%（无防护 84%） | AgentDojo，v2 | [R5] | 2025-06-24（v2） | A |
| FIDES 注入拦截 | 启用策略检查时挡住 AgentDojo 全部注入；推理模型平均多完成约 16% 任务（相对基础规划器） | AgentDojo | [R6] | 2025-09-03（v2） | A（"约 16%" 来自检索摘要，待回读原文） |
| Progent 攻击成功率 | v1：41.2% 降到 2.2%；v2：39.9% 降到 1.0%，效用 76.3% 对 79.4% | AgentDojo，LLM 生成策略 | [R7] | 2025-04（v1），后续（v2） | A（数字来自检索摘要，待回读原文） |
| 自适应攻击对 12 个防护 | 多数攻击成功率高于 90%；人工红队对全部防护成功；约 500 名参与者、2 万美元奖池 | 各防护各自的基准 | [R9][R19] | 2025-10-10 | A |
| IsolateGPT 开销 | 四分之三测试查询的开销低于 30% | NDSS 2025 | [R20] | 2025-01-30（v2） | A |
| AgentDojo 规模 | 97 任务、629 个安全测试用例 | — | [R21] | 2024 | A |
| Claude Code 手动提示批准率 | 93% | 内部/公开写作口径 | [R10] | 2026-03-25 | B |
| auto mode 分类器误报/漏报 | 全流水线：真实流量误报 0.4%（n=10000），真实越界漏报 17%（n=52），合成外泄漏报 5.7%（n=1000）；仅阶段一：8.5%、6.6%、1.8% | 内部评测 | [R10] | 2026-03-25 | B |
| auto mode 升级人工的阈值 | 连续 3 次拒绝或总计 20 次拒绝 | 默认配置 | [R10] | 2026-03-25 | B |
| 沙箱化减少权限提示 | 84% | 内部使用，无方法学 | [R17] | 2025-10-20 | B |
| 第三方对 auto mode 的压力测试 | 128 个模糊 DevOps 场景，漏报 81% | 单一来源，方法学未核实 | 检索摘要（besthub.dev） | 2026 | D（线索） |
| Register 称批准率 | 97% | 引自 Anthropic 后续发现，一手未核实 | 检索摘要 | 2026-08 | C（与 93% 冲突） |
| EchoLeak 严重度 | CVSS 9.3，CVE-2025-32711；2025-01 报告微软，2025-06 披露 | 零点击 | [R22][R23] | 2025-06 | A/C |
| Asana MCP 影响面 | 约 1000 客户；2025-05-01 上线，2025-06-04 发现 | 跨租户数据暴露 | [R24] | 2025-06 | C |
| postmark-mcp | 1.0.16 版把邮件密送到外部地址；累计 1643 次下载；2025-09-17 发布恶意版 | npm | [R25] | 2025-09 | C |
| Nx s1ngularity | 2025-08-26 恶意版本；2349 个被盗密钥；调用 Claude、Gemini、Amazon Q CLI | npm、GitHub | [R13] | 2025-08 | C |
| GTG-1002 | 约 30 个目标组织；AI 承担 80–90%；人只在约 4–6 个关键点介入 | Claude Code 加 MCP | [R26] | 2025-11-13 | B |
| OpenClaw/ClawHavoc | Koi 审计 2857 个 skill 中 341 个恶意；后续口径 824、1184 不一致；暴露实例数 21639 至 42665 互相冲突 | ClawHub | 检索摘要（多个二手来源） | 2026-01 至 2026-02 | C/D |
| Claude Code 沙箱绕过 | CVE-2025-66479（出站全封被当成全放行，2025-11-26 修）；CVE-2026-25725（bubblewrap 下可写 `.claude/settings.json` 植入钩子，2026-02-06，CVSS 4.0 为 7.7） | sandbox-runtime、Claude Code <2.1.2 | 检索摘要（securityweek、GitLab advisory） | 2025-11、2026-02 | C |
| HarmonyOS 开放规模 | 2100 多项系统能力可被小艺调用；500 多个伙伴 Skill；2000 多个智能体；20 多项 AI 能力、每日 36.8 亿次调用 | HDC 2026 | [R16] | 2026-06 | B（媒体转述） |
| AppFunctions 状态 | Android 16 及以上；与 Gemini 集成截至 2026-05 为私有预览 | — | [R4] | 2026-05 | A |

---

## §3 逐问题分析

### Q2 策略与授权

**现状**

云侧策略层在 2026 年上半年收敛到「工具调用前置评估」这一形态。AWS 的 Policy in Bedrock AgentCore 于 2026-03-03 GA：策略由自然语言生成为 Cedar，存放在策略引擎中并挂到 AgentCore Gateway，网关拦截 Agent 与工具之间的流量并逐请求评估，13 个区域可用 [R19]（B，L3）。其后 2026-06-17 增加了对 Bedrock Guardrails 的支持（第三方转述，C）。NVIDIA OpenShell 走另一路：YAML 策略，文件系统与进程段在创建时锁死，网络与推理段可以对运行中的沙箱热加载，未命中任何策略块的连接被阻断并记录 [R27]（C，L2；alpha 状态，GTC 2026 发布的版本号 v0.0.8 仅有第三方口径）。

**OPA/Rego 与 Cedar 的取舍**

本轮只核实到 Cedar 一侧：Cedar 论文说明它用 Lean 建模并证明设计性质，且其逻辑编码「可靠且完备」，能精确回答「重构后授权集合是否变化」这类问题 [R28]（A）。这正是策略变更需要的能力。AgentCore 选 Cedar 而非 OPA，符合「策略由 LLM 生成、需要自动分析生成结果」的场景。OPA/Rego 的 2025–2026 进展本轮未检索，待核实。判断：选型的关键变量不是语言表达力，而是「能否对机器生成的策略做静态分析」；Cedar 在这点上有论文级证据，Rego 侧未找到对应证据。

**形式化验证**

- Cedar 的验证对象是语言与分析器本身，不是 Agent 行为 [R28]。
- OpenShell 的「policy prover」在公开文档中未找到：搜索只找到沙箱、策略引擎与 privacy router，没有 prover [R27]。v1 提到的这一项暂记「待核实」，不应写进设计依据。
- 学术侧的确定性执行器（CaMeL 的解释器、FIDES 的策略检查、Conseca 的评估器）提供的是「执行不可被注入绕过」的论证，不是形式化证明整个系统安全。CaMeL 的「可证明安全」是相对其威胁模型和任务集合而言 [R5]。

**deny-by-default 出口治理的工程实践**

- Claude Code 沙箱：文件系统限定在工作目录（Linux 用 bubblewrap，macOS 用 seatbelt），网络只能经 Unix 域套接字连到沙箱外代理，由代理按域名放行，新域名需用户确认；文章强调两种隔离缺一不可：没有网络隔离，被攻陷的 Agent 能外泄 SSH 密钥；没有文件隔离，它能逃逸沙箱再联网 [R17]（B）。
- 但这个代理本身成了攻击面：CVE-2025-66479 中「封锁全部出站」的设置被当成「全部放行」，另有 SOCKS5 主机名空字节注入绕过白名单（无 CVE，日期在不同来源中不一致）[R29]（C）。CVE-2026-25725 则是沙箱内代码可创建 `.claude/settings.json` 并植入钩子，重启后以宿主权限运行 [R29]。教训：策略文件本身必须在沙箱的写保护范围内。
- Vercel Sandbox 提供 `deny-all` 与域名白名单两种网络策略，且可对运行中的沙箱更新 [R11]（B）。
- Chrome 的 Origin Sets 把同一思路应用到浏览器：只读源集与可读写源集，由可信的门控函数判断哪些源与任务相关，导航到新源还要过批评模型变体的检查 [R8]（B）。

**信息流控制与能力系统**

这一组是 SBX-7 的理论基础。机制差异如下。

| 方法 | 核心机制 | 强制点 | 代价 | 证据 |
|---|---|---|---|---|
| CaMeL | 特权 LLM 只看用户请求并产出受限 Python 计划，隔离 LLM 处理不可信数据且无工具权限；解释器跟踪数据来源与能力 | 解释器 | 77% 对 84% 的任务效用；需要用户或系统写安全策略 | [R5] A |
| FIDES | 工具结果存入规划器内存的变量，不进上下文；变量带机密性与完整性标签；有选择地对模型隐藏 | 规划器的策略检查 | 需要为每个工具定义标签传播 | [R6] A |
| Progent | 在工具调用上施加最小权限策略，可按参数约束，LLM 可协助生成/更新 | 工具调用代理层 | 策略质量依赖生成器；v1 与 v2 数字不同 | [R7] A |
| Conseca | 仅用可信上下文生成任务级策略，独立确定性评估器执行 | 评估器 | 策略生成的正确性靠人类可审的理由字段 | [R30] A |
| IsolateGPT | 应用级执行隔离，中枢调度 | 隔离边界与中枢 | 四分之三查询开销低于 30% | [R20] A |

分歧点：CaMeL 与 FIDES 依赖「控制流可以与不可信数据分离」；对需要读取数据后动态决定下一步的任务（Travel 套件因 API 文档缺失表现差，检索摘要）效用下降。Progent 与 Conseca 走「策略生成」路线，但这引入新的信任问题：策略是模型生成的，谁来审核。AgentCore Policy 的自然语言到 Cedar 也属于此类，AWS 称会标出无法强制的规则 [R19]。

Chrome 团队明确说 User Alignment Critic「部分受双 LLM 模式与 CaMeL 启发」，同时把它定位成启发而非实现 [R8]。判断：产品落地选择的是「独立批评模型加源隔离」这条弱化版，而不是完整的 CaMeL 解释器，原因大概率是通用网页任务无法预先写出计划。这一点是推断，Google 文章没有说明原因。

**参数化权限的先例**

- Progent 的策略可限制参数取值 [R7]；Cedar 策略可以引用请求上下文，原则上可表达参数条件（Cedar 论文未直接讨论 Agent 参数，推断）。
- MCP 授权规范允许服务器根据请求参数动态决定要求的 scope，并要求在一次质询中一并给出（"required scopes may be determined dynamically based on the specific request arguments and context"）[R31]（A）。这是标准层面最接近「参数化权限」的表述，但粒度仍是 scope，而非参数取值本身。
- MCP 2026-07-28 增加 `x-mcp-header`，把指定参数镜像到 HTTP 头 `Mcp-Param-*`，使 WAF、负载均衡等中间设施能基于参数取值路由 [R3]（A）。注意规范同时警告不要把敏感参数标出来。这给「在网关按参数做策略」提供了传输层钩子。
- Android 运行时权限的范围化、iOS 有限访问、Photo Picker 属于「由用户选择范围而非授予类别」的先例，本轮未做一手核实，仅作背景知识（待核实）。
- Claude Code 的带参数模式权限规则：auto mode 进入时会丢弃授予任意代码执行的规则（宽泛 shell、带通配符的脚本解释器、包管理器 run 命令）[R10]。这反过来说明静态的「命令前缀白名单」容易被滥用成任意执行。

**这说明什么**：执行层的确定性策略（能力、标签、参数约束）已有较扎实的 L1 证据和 Chrome 的 L3 落地，但「策略由谁写、谁审」是未解问题；SBX-4 的方向对，但必须配套策略来源的信任模型。

### Q3 凭证经纪人与 Agent 身份

**经纪人实现方式对比**

| 实现 | 注入位置 | 沙箱看到什么 | 响应脱敏 | 弱点 | 证据 |
|---|---|---|---|---|---|
| Vercel Sandbox | 防火墙转换块，对匹配域名的 HTTPS 请求添加或覆盖头部 | 无凭证；沙箱自设的同名头会被覆盖 | 未见说明 | 只覆盖头部；规则可热更新，所以可「先注入再拆除」 | [R11] B |
| Deno Sandbox | 创建时按主机声明密钥；占位符在访问批准主机时换成真值 | 占位符 | 未见说明 | HN 评论质疑头部以外（如数据库 TCP）无法替换（D）；beta | [R12] C |
| Daytona | 不透明占位符加出站代理 | 占位符 | 未见说明 | 同上 | [R12] C |
| Docker sandboxes | 文档含「credentials」章节，细节未回读 | 待核实 | 待核实 | 待核实 | [R12] C |
| Fly Tokenizer | 无状态代理持 Curve25519 私钥，客户端发加密密钥头 | 只有密文 | 无 | 客户端仍要持有「可用密文」，可被重放到代理允许的域 | [R12] C |
| Claude Code on the web | git 代理校验作用域凭证与操作（如只允许推送到配置分支）后附加真实令牌 | 作用域凭证 | 未见说明 | 作用域凭证本身仍可在代理允许范围内滥用 | [R17] B |

观察：「响应脱敏」一项没有任何厂商的公开文档给出细节（本轮未找到），即「服务回显了凭证或把凭证写进错误信息」这条路径缺少公开方案。出口代理还有两个共同弱点：一是代理允许的动作，Agent 仍可滥用（经纪人解决的是「明文泄漏」，不是「合法凭证被误用」）；二是非 HTTP 协议覆盖不全。

**泄漏事故**

- Nx s1ngularity（2025-08-26）：恶意 npm 版本扫描开发者环境，并调用本机的 Claude、Gemini、Amazon Q CLI，利用 `--yolo`、`--trust-all-tools` 之类不安全参数让 AI 工具递归寻找敏感文件，约 2349 个密钥被盗，大部分是 GitHub OAuth 密钥与个人令牌 [R13]（C）。启示：明文存在于文件系统或环境变量，本机上的 Agent CLI 就是现成的探测器；SBX-8 的「Agent 不持有明文」必须覆盖「Agent 所在环境不存在明文」。
- Amazon Q 扩展（CVE-2025-8217）：根因是 CodeBuild 配置里的 GitHub 令牌权限过大，攻击者借此把恶意提示合入开源仓库并随 1.84.0 发布；AWS 称代码因语法错误未执行 [R32]（A）。凭证过权，而非提示注入技术本身，是入口。
- postmark-mcp、mcp-remote（CVE-2025-6514，CVSS 9.6，影响 0.0.5 至 0.1.15，0.1.16 修复）、Asana MCP 跨租户暴露分别是恶意服务器、客户端 OAuth 处理缺陷、服务端逻辑缺陷 [R25][R24][R33]（C）。

**Agent 的委托授权**

- MCP authorization（2026-07-28 修订）：HTTP 传输上 OAuth 2.1，必须用 RFC 9728 做保护资源元数据，必须使用 RFC 8707 resource 参数、令牌必须绑定受众，客户端不得把非本授权服务器签发的令牌发给 MCP 服务器，服务器不得接受或转发其他令牌（即禁止令牌透传）；推荐 Client ID Metadata Documents，动态客户端注册被弃用；授权响应需校验 `iss`（RFC 9207）；scope 支持逐步升级 [R31]（A）。stdio 传输明确「不应」使用该规范，凭证从环境读取。判断：这对手机上本地调用的 AppFunctions 没有直接约束力，端侧仍缺等价物。
- Microsoft Entra Agent ID：blueprint 是创建 agent identity 的模板对象，只能执行「创建/删除 agent identity」这一种操作；agent identity 不持有自己的密钥，靠 blueprint 取令牌；可对 blueprint 施加条件访问；停用 blueprint 即阻止其全部 agent identity 认证；可继承权限需管理员同意 [R14]（A，文档更新于 2026-05-01）。GA 日期：第三方称 2026-05-01，微软一手公告未核实，待核实。
- Windows：Agent Workspace 中的所有动作归属于独立于用户的 agent identity（私有预览，Ignite 2025）；Windows On-device Registry 的所有 Agent 与连接器通信经 MCP 代理，用于同意、治理、审计与围堵 [R15][R34]（B）。
- Okta Cross App Access：本轮未能检索，待核实。
- 鸿蒙：Skill 上架与华为账号认证绑定；转账、支付等环节系统阻断自动化流程，需用户手动完成；用户可看到调用了哪个工具、在哪一步 [R16]（B，媒体转述，未见沙箱或逐 Agent 权限模型的说明）。

**端侧凭证原语**

Android Keystore/StrongBox/Credential Manager、iOS Keychain/Secure Enclave、HarmonyOS HUKS 的共同点是「密钥可用而不可导出」。本轮未联网核实具体能力与版本，属背景知识。判断：在手机上，经纪人的最自然形态是「系统服务持有密钥并代为签名/请求」，而不是 HTTP 代理注入；但对存量 HTTPS 流量，仍需要某种出口代理（需要用户信任的根证书或应用配合），这是云侧方案迁移到手机的主要障碍（推断）。

**对 SBX-9 的检验**：见 §5。

**这说明什么**：SBX-8 是业界最一致的方向；SBX-9 受到明确挑战，Entra、Windows、AppFunctions、鸿蒙四家都在平台层建立 Agent 主体。

### Q4 接口面

**MCP 规范演进（核实至 2026-07-28 修订）**

以 2025-11-25 为基线，2026-07-28 的主要变化 [R1]（A）：

1. 去掉协议级会话与 `Mcp-Session-Id`，`tools/list` 等列表端点不再随连接而变；有状态的服务器用显式句柄作为普通工具参数传递（规范专门写了「Stateful Tools」指南，要求每次调用都校验授权，句柄是名字而不是能力）[R3]。
2. 无状态化：取消 `initialize` 握手，每个请求在 `_meta` 携带协议版本与客户端能力；新增 `server/discover`。
3. `subscriptions/listen` 取代 HTTP GET 与 `resources/subscribe`；去掉 SSE 的断点续传，断流后请求丢失，客户端须以新 ID 重发。
4. Tasks 从核心移出，成为官方扩展 `io.modelcontextprotocol/tasks`：用 `tasks/get` 轮询、新增 `tasks/update` 以回送输入、删除 `tasks/list`。
5. Multi Round-Trip Requests：服务器返回 `resultType: "input_required"`，客户端带着 `inputResponses` 重试原请求，取代服务器主动发起的 `elicitation/create` 等请求。URL 模式 elicitation 的完成通知和 `elicitationId` 一并移除。
6. 弃用 Roots、Sampling、Logging；弃用 DCR；新增 12 个月最短弃用窗口的特性生命周期政策。
7. 次要：`ttlMs` 与 `cacheScope` 缓存提示，工具列表应确定性排序以利于 LLM 提示缓存，OpenTelemetry 追踪上下文约定，`inputSchema`/`outputSchema` 放宽到 JSON Schema 2020-12 任意关键字。

判断：协议在一年内两次结构性修订，说明接口面仍在快速变动；SBX-3 的「异步」「结构化拒绝」不应直接绑定某个 MCP 版本的字段，应保留适配层。

**MCP 工具注解与七要素对照**

注解字段（来自 2025-06-18 schema）[R35]（A）：`readOnlyHint`（默认 false）、`destructiveHint`（默认 true，仅在非只读时有意义）、`idempotentHint`（默认 false）、`openWorldHint`（默认 true）、`title`。规范在 2026-07-28 的工具页再次强调：为了信任与安全，客户端必须把注解视为不可信，除非来自可信服务器 [R3]。同页规定应始终有人在环能够拒绝工具调用，建议显示工具输入以避免恶意或意外的外泄 [R3]。

**接口方案七要素打分**

图例：● 标准内明确支持；◐ 部分或仅为提示/约定；○ 未找到；「—」未核实。

| 要素 | MCP 2025-11-25 | MCP 2026-07-28 | AppFunctions | App Intents | 鸿蒙意图框架/HMAF | Windows ODR | computer use |
|---|---|---|---|---|---|---|---|
| schema | ● inputSchema/outputSchema | ● 放宽到 2020-12 | ● 由注解生成 XML schema | ● （背景知识，待核实） | — | ● 沿用 MCP | ○ 无，靠截图 |
| 效果描述 | ◐ 四个提示且不可信 | ◐ 同上，并要求不可信 | ◐ 用 KDoc 描述，另有应用级元数据 | — | — | ◐ 声明最小能力 | ○ |
| dry-run | ○ | ○ | ○ | — | — | ○ | ○ |
| undo | ○ | ○ | ○ | — | — | ○ | ○ |
| 幂等 | ◐ idempotentHint | ◐ 同上 | ○ | — | — | ◐ | ○ |
| 异步 | ◐ Tasks（实验性） | ◐ Tasks 扩展 + MRTR | ◐ `suspend` 函数，未见任务句柄 | — | — | ◐ 沿用 MCP | ○ |
| 结构化拒绝 | ◐ `isError` 与 JSON-RPC 错误 | ● 加 403 `insufficient_scope` 质询 | ◐ 预定义异常（如 `AppFunctionInvalidArgumentException`、`AppFunctionElementNotFoundException`） | — | — | ◐ 同意与围堵由代理执行 | ○ |

依据：[R1][R3][R4][R35]。dry-run 与 undo 两列「○」的结论基于对 MCP 工具页、schema 与 AppFunctions 官方页的阅读，没有找到相应字段；不排除某些厂商私有扩展，但未发现。判断：七要素中 dry-run 和 undo 是我方相对业界的真空，即潜在差异化点，也是最难落地之处。

**Android AppFunctions**

官方页面显示：它是 Android 平台 API 加 Jetpack 库，使应用像设备端 MCP 服务器那样贡献函数；调用方需要 `EXECUTE_APP_FUNCTIONS` 权限才能发现与执行；Android 16 及以上可用；库生成 XML schema 供系统索引；截至 2026-05 与 Gemini 的集成为私有预览，仅限受信任测试者；整体标注为实验性；官方 FAQ 明确对比 MCP：AppFunctions 是 Android 专有、本地执行，MCP 依赖云执行与网络往返 [R4]（A）。Google 2026-02-25 的公告称 Gemini 已用 AppFunctions 支撑 Calendar、Notes、Tasks 集成，同时在开发 UI 自动化框架，用于没有专用集成的应用，Android 17 将扩大这些能力 [R36]（B/C）。这个「结构化函数 + UI 自动化兜底」的二层结构，与 SBX-2 的 L1/L0 结构高度同构。

**iOS App Intents**

检索到的 WWDC 2026 报道均为二手：称 SiriKit 被弃用、App Intents 成为新 Siri 唯一入口、增加流式响应与多轮追问、Xcode 支持 MCP [R37]（C/D）。没有取得 Apple 一手文档，全部标「待核实」，不用作设计依据。

**鸿蒙**

HDC 2026（2026-06）发布 HMAF 2.0：开发者可通过 Agent、Skill、MCP、意图框架四种方式接入；「意图即服务」由系统匹配 Agent 或 Skill；A2A 支持端侧直连；A2UI 让 Agent 动态生成界面；兼容 MCP；披露 2100 多项系统能力可被小艺调用、500 多个伙伴 Skill、2000 多个智能体；「天工计划」投入 10 亿元 [R16]（B，媒体转述，未见华为官方开发者文档）。授权口径是白皮书式的「本地优先、数据最小化、用户可控」，细节缺。

**Windows**

On-device Agent Registry（公共预览）：MCP 服务器默认放在独立环境中，只能访问被批准的资源；用户与 IT 管理员可经设置与 Intune 控制每个 Agent 对 MCP 服务器的访问；支持记录与审计；连接器须打包签名（MSIX 或 MCPB）并声明最小能力；所有 Agent 与连接器通信经 MCP 代理，由其执行同意、治理、审计与围堵 [R15][R34]（B）。第三方文章提到存在「降低保护以启用更多连接器」的选项，细节受构建号限制，待核实。

**computer use**

本轮未能检索 Anthropic computer use、OpenAI CUA、Gemini Computer Use 的官方细节，待核实。能确认的是 Chrome 的做法：对敏感站点访问、通过密码管理器登录、购买/支付/发消息等后果性动作要求用户确认，提供工作日志与接管，并在页面上并行运行注入分类器，Google 自己说它抓不全；悬赏最高 2 万美元 [R8]。判断：computer use 没有 schema、dry-run、undo，因此不适合充当 L1，只能作为 L0 兜底并配合外层门控。

**命名、发现与异步**

- 命名：MCP 规范只保证工具名在单个服务器内唯一，聚合多服务器时可能冲突，建议加服务器前缀；服务器名不保证唯一，不应用于消歧 [R3]。
- 发现：MCP Registry 于 2025-09-08 进入预览，无数据持久性保证，允许公共/私有子注册表 [R38]；`server/discover` 提供服务器自述；AppFunctions 经 XML schema 由系统索引，并有应用级元数据 [R4]；Windows 由 ODR 管理 [R15]。
- 事件触发：MCP 2026-07-28 以 `subscriptions/listen` 做列表变更等订阅；AppFunctions 与鸿蒙在事件触发/回调侧本轮没有找到公开接口描述，待核实。

**这说明什么**：接口面已收敛到「函数式工具 + schema + 提示性注解 + 轮询式异步」，七要素中的 schema、异步、结构化拒绝有标准件，效果描述只有不可信提示，dry-run 与 undo 在标准层缺失。

### Q5 Agent 安全

**攻防基准与防护**

- AgentDojo：97 个任务、629 个安全测试用例，发现当前模型即使无攻击也完不成不少任务，现有注入攻击能破坏部分而非全部安全性质 [R21]（A）。
- 自适应攻击：Nasr、Carlini 等 14 人的论文用多种攻击（梯度、强化学习、搜索、人工红队）绕过 12 个已发表防护，多数攻击成功率超过 90%，人工红队对全部成功 [R9]（A）。论文的方法学论点是：用静态攻击集评估防护几乎无意义。Willison 据此认为 Rule of Two 是目前最实用的指导 [R19]。
- 提示层防护（spotlighting、指令层级等）：本轮未做一手检索，见 §8 待核实。上述自适应攻击论文中提示类防护的成功率为 95% 至 99%（检索摘要，待回读）。
- 设计模式：《Design Patterns for Securing LLM Agents against Prompt Injections》（arXiv 2506.08837，2025-06）提出一组原则化模式；具体六种模式的名称本轮未取得，待核实 [R39]。

**Meta Agents Rule of Two**（2025-10-31）[R18]（B）：三个属性为 [A] 能处理不可信输入、[B] 能访问敏感系统或私有数据、[C] 能改变状态或对外通信；在能可靠检测并拒绝提示注入之前，一个会话最多同时具备其中两个；三者都需要时，应开启新会话并清空上下文，或由人批准或其他可靠验证手段监督。批评：Willison 指出原图把「不可信输入加状态变更」标成「安全」是不对的，Meta 随后把标签改为「lower risk」，并解释「敏感系统」不止私有数据，被严格沙箱隔离的 Agent 可以自由写状态 [R19]（B）。另有观点认为该规则不覆盖多 Agent 级联失效（二手评论，D）。

**逃逸基准**

v1 里的「SEB」应为 SandboxEscapeBench：论文《Quantifying Frontier LLM Capabilities for Container Sandbox Escape》（Marchand 等，arXiv 2603.02277，2026-03-01，收录于 ICML 2026，v3 修订于 2026-08-01）。它是 Inspect AI 的 CTF 评估，采用嵌套沙箱，外层承载旗标；摘要称加入漏洞后 LLM 「能识别并利用」；覆盖错误配置、权限分配错误、内核缺陷与运行时/编排弱点 [R40]（A）。英国 AISI 的说明（检索摘要）称有 18 个逃逸场景、分编排/运行时/内核三层，且基准每个容器外再套加固虚拟机；该条与摘要里「各模型成功率」均未在论文摘要中见到，具体成功率待回读。Edera 称约一半逃逸尝试成功，属厂商博客，D。论文范围明确不含持久化、隐蔽性、外泄量与特权巩固，也排除虚拟机逃逸 [R40]。判断：这是 SBX-1「借来的隔离边界」应当选更强边界（VM/pKVM 一类）的反方之外的支持证据——容器级边界对前沿模型不可靠；而 Claude Code 自己的沙箱 CVE 说明绕过更常发生在代理与配置层，而非内核逃逸。

**事件复盘**：见 §7.3。

**风险框架**

- OWASP Top 10 for Agentic Applications 2026：2025-12-09 发布，ASI01 为 Agent 目标劫持，ASI02 为工具滥用，ASI03 为身份与权限滥用，ASI10 为流氓 Agent；完整十项在 OWASP 官方页没有列出，需下载文档，本轮只取到二手转述，故不展开列举（待核实）[R41]（官方页确认发布日期，条目 C）。
- NIST AI 600-1、Google SAIF：本轮未检索，待核实。

**这说明什么**：模型层防护无法为安全论证提供基础；可论证的只有「限制能力组合」（Rule of Two）和「确定性执行」（CaMeL、FIDES、Progent），后者仍未在通用任务上证明效用。

### Q8 监督界面

**确认疲劳数据**

- Anthropic（2026-03-25）：「用户手动确认中的 93% 都批准了」，所以人工检查点常常是肌肉记忆 [R10]（B）。同文给出 auto mode 的分类器：阶段一是单 token 的是/否过滤器，被告知「宁可误拦」；阶段二仅对阶段一标记的动作做链式推理；分类器看不到助手自己的文字和工具结果，只看到用户消息与工具调用；真实越界样本漏报 17%，真实流量误报 0.4% [R10]。
- 沙箱：Anthropic 内部使用口径下，沙箱使权限提示减少 84% [R17]（B，无方法学）。
- 冲突/线索：Register 报道的 97% 与 93% 不一致，一手出处未核实（C）；一项第三方压力测试称 128 个模糊场景漏报 81%（D，方法学未核实）。

**交互设计要素的业界现状**

| 要素 | 实例 | 证据 |
|---|---|---|
| 自动批准 | Claude Code auto mode，连续 3 次或累计 20 次拒绝后回退人工 | [R10] B |
| 活动日志 | Chrome 工作日志；MCP 规范要求客户端记录工具使用以便审计；Windows ODR 日志审计 | [R8][R3][R15] |
| 接管/watch mode | Chrome 用户可观看、接管或停止任务 | [R8] B |
| 敏感动作强制确认 | Chrome：购买、支付、发消息、访问银行/医疗站点、使用密码管理器登录；鸿蒙：转账支付由系统阻断自动流程，用户手动完成 | [R8][R16] |
| 工具调用可见 | 鸿蒙：用户可看到调用的工具与步骤；MCP：显示工具输入 | [R16][R3] |
| undo | 业界未找到标准化的回滚界面；学术先例 GoEX 在本轮未检索，待核实 | — |

**这说明什么**：确认弹窗在高批准率下接近无效；有效的是「默认在边界内无提示，越界才升级」加「事后可审、可接管」。undo 是业界空白。

---

## §4 趋势判断

**正在收敛的方向**

- 工具调用前置评估：AgentCore Policy、Progent、Conseca、MCP 的 scope 质询都在工具调用点做确定性判定。
- 出口默认拒绝加凭证出口注入：Vercel、Deno、Daytona、Docker、Claude Code 都是此形态。
- 把「会话属性组合」作为风险语言：Rule of Two 已被 Databricks 等引用（检索摘要）。
- 结构化接口加 UI 自动化兜底：AppFunctions 与 Gemini UI 自动化、MCP 与 computer use 并存。
- Agent 主体上收平台：Entra Agent ID、Windows Agent Workspace、AppFunctions 的调用方权限。

**公认的空白点**

- dry-run 与 undo 的标准化（MCP、AppFunctions 均未提供）。
- 端侧 OS 层的信息流标签与出口策略强制，目前未找到公开实现。
- 响应脱敏与「合法凭证被误用」的防护。
- 注解可信度：注解不可信，但没有签名或认证机制（规范只说可信服务器可信）。
- 监督界面的 undo 与跨 Agent 链的可见性。

**仍有分歧的问题**

- 策略由谁生成：人写、LLM 生成还是任务级动态生成（Progent、Conseca、AgentCore 的 NL→Cedar 三种）。
- 用确定性解释器（CaMeL）还是批评模型（Chrome 的 Critic）。
- 分类器自动批准是否可接受：Anthropic 已上线，但漏报 17%；第三方压力测试给出更差的数字。
- Agent 身份归平台、IdP 还是应用。
- MCP 与平台原生接口（AppFunctions、App Intents、HMAF）长期是融合还是并存。

---

## §5 立场评审表

| 立场 ID | 判断 | 关键证据 | 最强反方证据 | 修订建议 | 置信度 |
|---|---|---|---|---|---|
| SBX-2 统一接口面（L0 兜底，L1 结构化） | 支持 | Android：AppFunctions 加 UI 自动化兜底 [R4][R36]；MCP 与 computer use 并存；Windows ODR | AppFunctions 仍为私有预览，L1 覆盖面极窄；鸿蒙 Skill 数量虽多但为厂商口径 [R16] | 保持 L0/L1；明确 L0 不是「未受约束」，而是「受 Rule of Two 与出口策略约束」 | 高 |
| SBX-3 七要素（逐项见 §7.1） | 部分支持 | schema、异步、结构化拒绝有标准件 [R1][R3] | dry-run、undo 无任何标准；效果描述只有不可信提示 | 把七要素分级：schema、结构化拒绝、异步为必选；效果描述为必选但由系统校验；dry-run、undo 为可声明能力，缺省按不可逆定档 | 中 |
| SBX-4 参数化权限 | 支持，需补策略来源 | Progent 参数约束 [R7]；MCP scope 可依请求参数动态决定 [R31]；`x-mcp-header` 暴露参数供网关策略 [R3] | 策略多由 LLM 生成，质量与可审计性未证；Claude Code 自家分类器漏报 17% [R10] | 把策略的「来源」纳入权限模型（人签署/可信上下文生成/模型生成）并区分审核级别 | 中 |
| SBX-5 三维风险定档 | 需修订 | Rule of Two 以会话属性定档 [R18]；OWASP 把目标劫持列在首位 [R41] | 若三维仅为动作静态属性，无法表达「会话已接触不可信输入」 | 增加会话动态状态（污染/来源标签），见 §7.2 | 中 |
| SBX-6 装配、调用、销毁三时机 | 支持 | Vercel 凭证可「先注入后拆除」且热更新 [R11]；OpenShell 静态与动态段分离 [R27]；auto mode 进入时丢弃任意执行规则 [R10] | 绕过多发生在装配期：CVE-2026-25725 因 `.claude/settings.json` 在沙箱启动时不存在而被植入 [R29] | 装配期要把策略与配置文件置于沙箱不可写范围；销毁期要明确凭证、句柄、代理规则的撤销 | 高 |
| SBX-7 跨链不升级（权限只减不增） | 支持，需补信息流 | CaMeL、FIDES、Progent 的理论基础 [R5][R6][R7]；MCP 禁止令牌透传与受众绑定 [R31]；Asana 是跨租户混淆 [R24] | EchoLeak 与 GitHub MCP 攻击链没有任何权限提升，全程使用 Agent 合法权限 [R22][R42]；仅权限衰减挡不住 | 加一条「污染传递」规则：链上数据标签单调不降；权限衰减与标签传播并列 | 中高 |
| SBX-8 凭证经纪人 | 支持 | Vercel、Deno、Daytona、Docker、Claude Code on the web 都采用 [R11][R12][R17] | 经纪人不防止合法凭证被误用；非 HTTP 协议覆盖不全（D）；Nx 事件说明环境中不能有明文 [R13] | 经纪人之外要求「使用审计与限额」；端侧用「系统服务持钥并代为请求」的形态 | 高 |
| SBX-9 身份归应用，系统只留信任根与跨链规则 | 需修订 | 反面证据：Entra Agent ID [R14]、Windows Agent Workspace [R15]、AppFunctions 平台级调用方权限 [R4]、鸿蒙 Skill 与华为账号绑定 [R16] | 支持证据：MCP 授权把授权服务器与用户身份留给资源方与 IdP [R31]；Entra 的 agent identity 面向企业 IdP，不等于 OS | 拆成两层：会话级 Agent 主体（包名+签名+会话号）由系统签发、可审计、可撤销；用户对第三方服务的身份仍归应用 | 中 |

---

## §6 接缝发现

### J3 工具调用/结构化输出 ↔ 接口面（安全侧，协同）

- 指令层级与注入防护应放在哪一层：本轮证据倾向「执行层」。自适应攻击表明模型层防护被系统性绕过 [R9]；CaMeL、FIDES、Progent 都把强制点放在解释器、规划器或工具调用代理 [R5][R6][R7]；Chrome 的批评模型被设计成只看动作元数据，从结构上拒绝接触不可信内容 [R8]。
- 结构化输出与接口面的分工：MCP 规范特别注明 `structuredContent` 是服务器产出的结果数据，与 LLM「结构化输出」（模式约束生成）无关 [R3]，即接口面只管工具侧的 schema，不管模型怎么生成参数。由此，约束解码（推理侧）保证参数合乎 schema，沙箱侧用 schema 做入口校验与策略评估，二者不可互相替代。
- 推论：参数化权限（SBX-4）依赖参数 schema 的稳定与类型化；MCP 2026-07-28 放宽 `inputSchema` 到任意 JSON Schema 关键字、并为复合关键字设资源上限 [R1]，意味着策略引擎需要自己的参数规范化层（推断）。
- MCP 的「工具列表应确定性排序，以利于 LLM 提示缓存命中」说明接口面的稳定性与推理侧前缀缓存相关，与 C1b 相关（线索）[R1][R3]。

---

## §7 组件特有输出

### 7.1 七要素逐条评审表

| 要素 | 业界先例 | 业界支持度 | 实现难点 | 修订建议 |
|---|---|---|---|---|
| schema | MCP `inputSchema`/`outputSchema`；AppFunctions 注解生成 XML schema [R3][R4] | 高（所有主流方案都有） | 2026-07-28 放宽到任意 JSON Schema 关键字，策略引擎需规范化；`$ref` 解析有资源边界 | 保持必选；要求参数类型可被策略引擎引用，并在注册时静态校验 |
| 效果描述 | MCP 四个注解（`readOnlyHint`、`destructiveHint`、`idempotentHint`、`openWorldHint`）；AppFunctions 用 KDoc [R35][R4] | 中（有，但不可信） | 注解是「提示」，规范要求客户端视其为不可信；恶意或粗心的声明会误导定档 | 把效果描述分成「声明」与「观测」两层：声明用于初筛，沙箱按实际调用结果（写了什么、连了哪里）校正；声明与观测不符的调用方降级 |
| dry-run | 未在 MCP、AppFunctions 标准中发现；学术先例（ToolEmu、GoEX）本轮未检索，待核实 | 低 | 多数后端没有「试算」接口；让每个工具实现 dry-run 的生态成本高 | 作为可声明能力：有则优先走；无则按不可逆定档并要求确认或额外的 Rule of Two 约束 |
| undo | 未在标准中发现；Replit 事件后其官方承诺的是开发/生产库分离（回滚能力的具体承诺未见） [R43] | 低 | 外部副作用无法回滚（发消息、转账）；只有部分数据变更可补偿 | 将 undo 设为「补偿动作声明」：由应用声明补偿工具，系统记录调用链用于回放；不可补偿的动作一律定高档 |
| 幂等 | `idempotentHint`；MCP 的有状态工具句柄指南 [R3] | 中（仅提示） | 提示不等于幂等键；断流后请求丢失，客户端须以新 ID 重发（2026-07-28 去掉续传）→ 重试可能导致重复副作用 [R1] | 要求副作用动作携带幂等键；由系统在会话层去重，而不是依赖应用 |
| 异步 | MCP Tasks（先实验，后改为扩展，轮询加 `tasks/update`）；MRTR [R1] | 中（有标准件，但在变） | 规范一年内改动两次；AppFunctions 异步用 `suspend` 而非任务句柄，跨平台不一致 | 内部用统一任务句柄抽象，外部适配 MCP Tasks 与平台原生异步 |
| 结构化拒绝 | MCP：`isError`、JSON-RPC 错误、403 `insufficient_scope` 与 `WWW-Authenticate`（含所需 scope）；AppFunctions 预定义异常 [R3][R31][R4] | 中高 | 拒绝原因需要对模型可读但又不泄漏策略细节（泄漏策略会帮助攻击者探测）；业界未见统一的拒绝码表 | 定义拒绝码：缺权限（附可申请 scope）、需确认、被策略禁止（不带细节）、参数无效；参数无效可回送模型，策略禁止不回送细节 |

补充两点判断：一是「幂等」在断流后的语义变化是 MCP 2026-07-28 引入的新风险，直接影响 SBX-3；二是七要素与 MCP 注解重合的只有三项（效果、幂等，加 schema），dry-run 与 undo 是我方独有，也是最需要证明价值的两项。

### 7.2 三维定档评审

**假设**：未获得设计文档。假设我方三维为可逆性、影响范围、数据敏感度（来自第 5 节列举的业界常见维度之三）；外部可见性与资金视为被这三维吸收或另列。以下评审据此做出，需用设计文档核对。

| 对照对象 | 其维度 | 与三维的关系 | 缺口 |
|---|---|---|---|
| Meta Rule of Two [R18] | [A] 处理不可信输入、[B] 访问敏感系统/私有数据、[C] 改变状态或对外通信 | 数据敏感度≈[B]；可逆性与影响范围≈[C] 的强度 | 没有对应 [A]：会话是否已接触不可信输入是动态状态 |
| MCP 工具注解 [R35] | 只读、破坏性、幂等、开放世界 | 只读/破坏性≈可逆性；开放世界≈外部可见性 | 注解不可信；缺数据敏感度 |
| OWASP ASI [R41] | 目标劫持、工具滥用、身份与权限滥用等 | 偏威胁分类而非定档维度 | 「身份与权限滥用」说明调用方身份应进入定档 |
| Chrome 敏感动作清单 [R8] | 敏感站点、登录、购买、支付、发消息 | 清单式，对应资金与外部可见性 | 说明资金/外部可见性在实践中单列 |

结论（判断）：三维作为「动作静态属性」基本够用，但缺两个量：（1）会话污染状态（Rule of Two 的 [A]），决定同一动作在不同会话上下文里是否升档；（2）调用方可信度/身份（OWASP ASI03，及 MCP 注解不可信的前提）。建议将定档函数改为「动作静态三维 × 会话污染状态」，其中污染状态取自信息流标签（FIDES 式）或简化为「是否读取过外部不可信内容」二值，并把「会话中同时出现污染、敏感数据访问和外部副作用」设为硬性升级条件。资金与外部可见性是否独立，由设计文档决定；Chrome 实践支持资金单列。

### 7.3 事件复盘表

「我方立场 ID」指评估该立场若按设计落地能否阻断，「缺口」为挡不住的部分。日期为披露/发布日期，括号内为核实来源。

| 事件 | 日期 | 攻击链 | 能挡住它的我方立场 ID | 缺口 | 证据 |
|---|---|---|---|---|---|
| EchoLeak（M365 Copilot，CVE-2025-32711，CVSS 9.3） | 2025-01 报告，2025-06 披露 | 一封恶意邮件→Copilot 检索时读到→绕过 XPIA 分类器、引用式 Markdown 绕过链接脱敏、自动抓取图片、利用 Teams 代理被 CSP 允许→把数据外传 [R22][R23] | SBX-7（若含信息流标签，污染邮件内容不得流向外发通道）；SBX-6（出口默认拒绝：自动抓取图片即出口） | 全程使用 Copilot 合法的读邮件权限，纯权限衰减无效；分类器被绕过 | A/C |
| GitHub MCP「toxic agent flow」 | 2025-05-26 | 恶意公共 issue→持有跨公私仓库令牌的 Agent 被劫持→读取私有仓库→写入公共仓库 PR 外泄 [R42] | SBX-4（参数化：限制可访问仓库）；SBX-7；Rule of Two 拆会话 | Invariant 称这是「Agent 系统层面」而非服务器缺陷；令牌作用域过宽是前提 | B/C |
| Supabase MCP | 2025-07-06（Willison 文章） | 客户支持工单中的恶意文本→Cursor 通过 `service_role`（绕过行级安全）执行 SQL→读集成令牌表→回写工单 [R44] | SBX-4（参数化权限，按表限定）；SBX-8（不使用高权限角色）；SBX-7 | 同一服务器内已具备三属性，需拆会话；Supabase 称无客户数据泄漏报告（二手） | B/C |
| Asana MCP 跨租户 | 2025-06 发现并披露（上线于 2025-05-01，2025-06-04 识别） | 服务端逻辑缺陷→用户看到其他组织数据 [R24] | SBX-7（受众绑定、禁止令牌透传的精神）；系统侧无法修复服务端逻辑缺陷 | 属于服务端缺陷，我方立场只能限制爆炸半径 | C |
| mcp-remote CVE-2025-6514 | 2025-07 | 恶意服务器返回构造的授权端点→客户端交给 PowerShell→命令注入，CVSS 9.6 [R33] | SBX-1（借来的隔离边界）限制被攻陷后的影响；SBX-9 的跨链规则不直接相关 | 客户端处理授权 URL 的缺陷在宿主侧，沙箱若不含客户端则无法保护 | C |
| Replit 删库 | 2025-07（Fortune 2025-07-23） | 代码冻结期间 Agent 删除生产库并掩饰；Replit 承诺开发/生产自动分离 [R43] | SBX-3（dry-run、undo）；SBX-4；SBX-5（不可逆定高档）；SBX-6 | 属于 Agent 越权加缺少隔离，非外部攻击；回滚能力是否存在不同来源说法不一（日期、受影响公司数口径不一，C） | C |
| Amazon Q 扩展（CVE-2025-8217，1.84.0） | AWS 公告 2025-07-23，更新 2025-07-25 | CodeBuild 里过权的 GitHub 令牌→攻击者向开源仓库合入恶意提示并随 1.84.0 发布；代码因语法错误未执行 [R32] | SBX-8（令牌不可过权、不放进构建环境）；SBX-6（装配期校验） | 供应链层面，非运行时沙箱问题；若无语法错误，Agent 将以用户权限执行 | A |
| Comet 浏览器 | 2025-08-20（Brave 披露；2025-07-25 报告，8 月 13 日确认补丁） | 网页中隐藏指令→总结页面时被执行→取邮箱、登录伪造域名、读 Gmail 验证码 [R45] | SBX-7（污染标签）；SBX-6；Chrome 式 Origin Sets 的源隔离 | Brave 称修复不完整；Perplexity 在 2025-10-22 承认注入「仍未解决」[R45] | B |
| Nx s1ngularity | 2025-08-26 | 恶意 npm 版本→调用本机 AI CLI（带 `--yolo` 等）找敏感文件→密钥外泄到受害者 GitHub 账号下的仓库 [R13] | SBX-8（环境无明文）；SBX-1（Agent 在沙箱内，看不到宿主密钥） | 恶意代码本身不是 Agent；Agent CLI 被当工具使用；开发机上明文凭证普遍存在 | C |
| postmark-mcp | 2025-09-17（恶意版本发布） | 仿冒 npm 包，1.0.16 版把每封邮件密送外部地址，1643 次下载 [R25] | SBX-4（参数化：收件人限定）；SBX-6（出口白名单）；注册表签名 | 来源冒充，非运行时问题；MCP Registry 在预览期无保证 [R38] | C |
| GTG-1002 | 2025-11-13 发布（检测于 2025-09 中旬） | 把攻击拆成小任务绕过拒绝，假扮防御性测试→Claude Code 经 MCP 调用扫描器与破解器，AI 承担 80–90% [R26] | 不属于我方沙箱可防范范围：这是模型被恶意使用，而非 Agent 被劫持 | 沙箱不能阻止用户本人是攻击者 | B |
| Claude Code 沙箱绕过 | CVE-2025-66479 修于 2025-11-26；CVE-2026-25725 公布于 2026-02-06 | 配置语义错误导致网络封锁失效；沙箱内可写 `.claude/settings.json` 植入钩子，重启后宿主权限执行 [R29] | SBX-6（装配期保护配置）；SBX-1（更强隔离边界） | 说明策略引擎和代理本身是攻击面，需要独立审计 | C |
| OpenClaw/ClawHavoc | 2026-01 起 | 恶意 skill 通过 ClawHub 分发；大量实例暴露公网；CVE-2026-25253（二手称 CVSS 9.8） | SBX-8、SBX-6（技能装配需来源校验）；SBX-9 的签发式主体 | 数字在来源间严重不一致（恶意 skill 数 341、824、1184；暴露实例数 21639 至 42665），均为二手；一手来源（Koi 报告）未回读 | C/D |

阅读结论：在 13 个事件中，约一半（EchoLeak、GitHub MCP、Supabase MCP、Comet、Replit）的攻击链完全使用 Agent 合法持有的权限，只有信息流/污染标签、会话属性约束（Rule of Two）和出口治理能阻断；另一半（Amazon Q、Nx、postmark-mcp、mcp-remote、ClawHavoc、Claude Code CVE）是供应链或实现缺陷，需要装配期校验与更强隔离。GTG-1002 超出沙箱范围。

---

## §8 参考资料与待核实清单

### 8.1 参考资料

| 编号 | 标题 | 机构或作者 | URL | 日期 |
|---|---|---|---|---|
| R1 | MCP 规范 2026-07-28 变更日志 | MCP 社区 | https://modelcontextprotocol.io/specification/2026-07-28/changelog | 2026-07-28 |
| R2 | MCP 规范 2025-11-25 变更日志 | MCP 社区 | https://modelcontextprotocol.io/specification/2025-11-25/changelog | 2025-11-25 |
| R3 | MCP 规范 2026-07-28：Tools | MCP 社区 | https://modelcontextprotocol.io/specification/2026-07-28/server/tools | 2026-07-28 |
| R4 | AppFunctions 概览 | Google（Android 开发者） | https://developer.android.com/ai/appfunctions | 页面标注截至 2026-05 |
| R5 | Defeating Prompt Injections by Design | Debenedetti、Shumailov、Tramèr 等 | https://arxiv.org/abs/2503.18813 | 2025-03-24（v1），2025-06-24（v2） |
| R6 | Securing AI Agents with Information-Flow Control | Costa、Köpf、Russinovich、Paverd 等（Microsoft） | https://arxiv.org/abs/2505.23643 | 2025-05（v2 2025-09-03） |
| R7 | Progent: Programmable Privilege Control for LLM Agents | Shi 等（UC Berkeley、UCSB） | https://arxiv.org/abs/2504.11703 | 2025-04 |
| R8 | Architecting Security for Agentic Capabilities in Chrome | Chrome Security（Nathan Parker） | https://blog.google/security/architecting-security-for-agentic/ | 2025-12-08 |
| R9 | The Attacker Moves Second | Nasr、Carlini 等 | https://arxiv.org/abs/2510.09023 | 2025-10-10 |
| R10 | Claude Code auto mode | Anthropic Engineering | https://anthropic.com/engineering/claude-code-auto-mode | 2026-03-25 |
| R11 | Safely inject credentials in HTTP headers with Vercel Sandbox | Vercel | https://vercel.com/changelog/safely-inject-credentials-in-http-headers-with-vercel-sandbox | 2026-02-23 |
| R12 | Introducing Deno Sandbox；Daytona secrets；Docker sandboxes credentials；Fly Tokenizer | Deno、Daytona、Docker、Fly.io | https://deno.com/blog/introducing-deno-sandbox ；https://www.daytona.io/docs/en/secrets/ ；https://docs.docker.com/ai/sandboxes/security/credentials/ ；https://github.com/superfly/tokenizer | 2026（Deno 具体日期待核实） |
| R13 | Nx supply chain breach: how s1ngularity weaponized AI | OX Security 等（二手） | https://www.ox.security/blog/nx-supply-chain-breach-how-s1ngularity-weaponized-ai/ | 2025-08 |
| R14 | Agent identity blueprints in Microsoft Entra Agent ID | Microsoft Learn | https://learn.microsoft.com/en-us/entra/agent-id/agent-blueprint | 页面日期 2026-04-28，更新 2026-05-01 |
| R15 | Windows 11 agent 安全模型（Ignite 2025 报道） | VentureBeat、Petri 等（二手） | https://venturebeat.com/ai/microsoft-remakes-windows-for-an-era-of-autonomous-ai-agents | 2025-11 |
| R16 | HDC 2026 深度解构：鸿蒙全面向 Agent 架构演进 | 爱范儿（媒体转述） | https://www.ifanr.com/1668931 | 2026-06 |
| R17 | Beyond permission prompts: making Claude Code more secure and autonomous | Anthropic Engineering | https://anthropic.com/engineering/claude-code-sandboxing | 2025-10-20 |
| R18 | Practical AI Agent Security（Agents Rule of Two） | Meta AI | https://ai.meta.com/blog/practical-ai-agent-security/ | 2025-10-31 |
| R19 | Policy in Amazon Bedrock AgentCore is now generally available | AWS | https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available | 2026-03-03 |
| R19b | New prompt injection papers: Agents Rule of Two and The Attacker Moves Second | Simon Willison | https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/ | 2025-11-02 |
| R20 | IsolateGPT: An Execution Isolation Architecture for LLM-Based Agentic Systems | Wu、Roesner、Kohno、Zhang、Iqbal | https://arxiv.org/abs/2403.04960 | 2024-03（NDSS 2025） |
| R21 | AgentDojo | Debenedetti 等 | https://arxiv.org/abs/2406.13352 | 2024-06 |
| R22 | EchoLeak（arXiv 版） | Reddy、Gujral | https://arxiv.org/abs/2509.10540 | 2025-09-06 |
| R23 | Zero-click AI vulnerability exposes Microsoft 365 Copilot data | The Hacker News | https://thehackernews.com/2025/06/zero-click-ai-vulnerability-exposes.html | 2025-06 |
| R24 | Asana warns MCP AI feature exposed customer data to other orgs | BleepingComputer | https://bleepingcomputer.com/news/security/asana-warns-mcp-ai-feature-exposed-customer-data-to-other-orgs/ | 2025-06 |
| R25 | First malicious MCP server found | The Hacker News | https://thehackernews.com/2025/09/first-malicious-mcp-server-found.html | 2025-09 |
| R26 | Disrupting the first reported AI-orchestrated cyber espionage campaign | Anthropic | https://www.anthropic.com/news/disrupting-AI-espionage | 2025-11-13 |
| R27 | NVIDIA OpenShell | NVIDIA | https://github.com/NVIDIA/OpenShell ；https://docs.nvidia.com/openshell/about/architecture.md | 2026-03 |
| R28 | Cedar: A New Language for Expressive, Fast, Safe, and Analyzable Authorization | Cutler、Disselkoen、Hicks 等 | https://arxiv.org/abs/2403.04651 | 2024-03 |
| R29 | Anthropic silently patches Claude Code sandbox bypass；CVE-2026-25725 | SecurityWeek；GitLab advisory | https://www.securityweek.com/anthropic-silently-patches-claude-code-sandbox-bypass/amp/ ；https://advisories.gitlab.com/npm/@anthropic-ai/claude-code/CVE-2026-25725/ | 2025-11 至 2026-02 |
| R30 | Contextual Agent Security: A Policy for Every Purpose（Conseca） | Tsai、Bagdasarian（Google） | https://arxiv.org/abs/2501.17070 | 2025-01（HotOS 2025） |
| R31 | MCP 规范 2026-07-28：Authorization | MCP 社区 | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization | 2026-07-28 |
| R32 | Amazon Q Developer for VS Code 安全公告（CVE-2025-8217） | AWS | https://aws.amazon.com/security/security-bulletins/AWS-2025-015/ | 2025-07-23，更新 2025-07-25 |
| R33 | mcp-remote CVE-2025-6514 | JFrog；OSV | https://api.osv.dev/v1/vulns/CVE-2025-6514 | 2025-07 |
| R34 | Model Context Protocol on Windows overview | Microsoft Learn | https://learn.microsoft.com/en-us/windows/ai/mcp/overview | 页面日期 2025-12-06，更新 2026-06-04 |
| R35 | MCP 规范 2025-06-18 Schema（ToolAnnotations） | MCP 社区 | https://modelcontextprotocol.io/specification/2025-06-18/schema | 2025-06-18 |
| R36 | Android AppFunctions 与 Gemini 自动化 | 9to5Google | https://9to5google.com/2026/02/25/android-appfunctions-gemini/ | 2026-02-25 |
| R37 | WWDC 2026 与 App Intents 报道 | Fonearena 等（二手） | https://www.fonearena.com/blog/?p=484623 | 2026-06 |
| R38 | MCP Registry 预览公告 | MCP 社区 | https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/ | 2025-09-08 |
| R39 | Design Patterns for Securing LLM Agents against Prompt Injections | Beurer-Kellner、Tramèr 等 14 人 | https://arxiv.org/abs/2506.08837 | 2025-06-10 |
| R40 | Quantifying Frontier LLM Capabilities for Container Sandbox Escape（SandboxEscapeBench） | Marchand 等 | https://arxiv.org/abs/2603.02277 | 2026-03-01（v3 2026-08-01） |
| R41 | OWASP Top 10 for Agentic Applications for 2026 | OWASP GenAI Security Project | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | 2025-12-09 |
| R42 | GitHub MCP exploited: accessing private repositories via MCP | Invariant Labs | https://invariantlabs.ai/blog/mcp-github-vulnerability | 2025-05-26 |
| R43 | AI coding tool Replit wiped database, called it a catastrophic failure | Fortune | https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure | 2025-07-23 |
| R44 | Supabase MCP: the lethal trifecta strikes again | Simon Willison | https://simonwillison.net/2025/Jul/06/supabase-mcp-lethal-trifecta/ | 2025-07-06 |
| R45 | Agentic Browser Security: Indirect Prompt Injection in Perplexity Comet | Brave | https://brave.com/blog/comet-prompt-injection/ | 2025-08-20 |

说明：R19b 编号用于区别 R19 的 AWS 条目；表中 §3、§5 引用的「[R19]」在涉及 Willison 观点时指 R19b。

### 8.2 待核实清单

| # | 项目 | 原因 |
|---|---|---|
| 1 | Okta Cross App Access 的机制、规范状态 | 检索额度用尽 |
| 2 | Android Keystore/StrongBox/Credential Manager、iOS Keychain/Secure Enclave、HarmonyOS HUKS 的具体能力与版本 | 同上，目前只有背景知识 |
| 3 | iOS 26/27 App Intents 的官方文档（实体、流式响应、Siri 路径），及 Apple 是否支持 MCP | 仅有二手报道 |
| 4 | Anthropic computer use、OpenAI CUA、Gemini Computer Use 的官方安全与确认机制 | 未检索 |
| 5 | OPA/Rego 在 Agent 场景的 2025–2026 进展，及与 Cedar 的对比 | 未检索 |
| 6 | OpenShell「policy prover」是否存在 | 公开文档未提及 |
| 7 | NIST AI 600-1、Google SAIF 的内容 | 未检索 |
| 8 | OWASP Agentic Top 10 的完整十项条目与定义 | 官方页仅给出发布日期，条目需下载文档 |
| 9 | Entra Agent ID 的 GA 时间与 OBO 流程的 GA | 第三方称 2026-05-01，微软一手公告未取得 |
| 10 | Progent v1 与 v2 的精确数字、FIDES「多完成约 16% 任务」 | 数字来自检索摘要，需回读论文 |
| 11 | SandboxEscapeBench 的场景数与各模型成功率 | 论文摘要未给出，AISI 与 Edera 为二手 |
| 12 | Anthropic 93% 与 Register 97% 的差异出处 | 一手未取得 |
| 13 | Claude Code 带参数模式权限规则的具体语法与引入版本 | 本轮未核实官方文档 |
| 14 | OpenClaw/ClawHavoc 的一手披露（Koi Security 报告）与 CVE-2026-25253 的详细信息 | 仅有二手来源，数字冲突 |
| 15 | CurXecute、MCPoison 等 Cursor 类 CVE、Codex CLI 相关 CVE | 检索未返回 |
| 16 | 鸿蒙智能体安全框架的官方开发者文档，及意图框架/HMAF 的权限模型 | 仅有媒体转述 |
| 17 | Docker sandboxes 的凭证方案细节 | 只取到页面入口 |
| 18 | GoEX、ToolEmu、TxOS 等 undo/dry-run 先例的论文信息 | 未检索 |
| 19 | AirGapAgent 等语义级授权工作（归 C3b，仅提示） | 不在本子模块范围 |
| 20 | 响应脱敏（凭证回显过滤）有无公开方案 | 本轮未找到公开资料 |

# AgentOS 组件调研 · 维度 B：策略与授权 + 凭证经纪人 + 接口面

> 调研日期：2026-11-06。时间范围 2024-01 至 2026-11（奠基性工作标注年份）。
> 来源标准：官方文档/技术博客/GitHub/发布会、学界（arXiv/顶会），媒体仅作线索并已标注。
> 事实与判断已区分；置信度见第 5 节证据清单。

---

## 1. 技术谱系表

### 1.1 策略与授权（Policy & Authorization）

| 代际 | 代表 | 年份 | 机制 | 在 agent 场景的落点 |
|---|---|---|---|---|
| 通用 Policy-as-Code | OPA/Rego（CNCF，2016 起） | 2016–2026 | 通用 JSON 策略求值；deny 语义由策略结构决定 | NVIDIA Sentry/DOCA Tower 用 OPA+Rego 做 L7 请求级授权，单请求 <1ms[^5^]；Permit.io 等用它做 MCP 网关授权[^17^][^18^] |
| 类型化授权语言 | Cedar（AWS，OSS 2023） | 2023–2026 | principal/action/resource/context 四元组；默认拒绝 + forbid 覆盖 permit；SMT 可分析 | **Amazon Bedrock AgentCore Policy**（2026-03-03 GA，13 区域）：Gateway 拦截每次 tool call，Cedar 决策在 agent 之外；支持 NL2Cedar 与自动化推理校验（拒绝 Overly Permissive 策略）[^9^][^10^][^8^] |
| 时序授权语言 | Dogwood（AWS，OSS 2026-08-06，Apache-2.0） | 2026 | Cedar 超集，`when temporal {}` 基于 MFOTL（Metric First-Order Temporal Logic），支持 `formerly/once/count_within/sum_within` | 解决「单次请求合规、序列越界」（如三笔 2000 美元绕过 5000 限额）；托管于 AgentCore Policy，24h 回溯窗口[^11^][^14^][^17^] |
| 策略变更形式化验证 | NVIDIA OpenShell Policy Prover | 2026-09（v0.1.0）/2026-10-21（参考架构，GTC Berlin） | Z3 SMT 求解器；boundary check（候选策略 ≤ 边界策略）+ proposal risk check（新凭证目的地/云元数据/新方法） | 「propose → prove → approve → reload」生命周期；父 agent 给子 agent 写策略时验证不越界[^1^][^2^][^3^] |
| 工程取舍轴 | — | — | OPA=通用异构策略平台（K8s admission、API、agent 工具约束一机多管）；Cedar=类型化应用授权、schema 校验前置、编译后更快 | 选型取决于「一个策略服务评多种输入」（OPA）vs「类型化应用授权 + 形式化可分析」（Cedar）[^16^][^17^] |

### 1.2 凭证经纪人（Credential Broker）

| 模式 | 代表实现（日期） | 要点 |
|---|---|---|
| 出口代理注入（真凭证只在代理侧） | Anthropic Claude Managed Agents（2026-04-08 发布）：vault + credential proxy，「The harness is never made aware of any credentials」[^22^][^23^][^24^]；Vercel Sandbox credential brokering（环境 key 不进 VM）[^13^]；Infisical Agent Vault（OSS，2026-04-21）[^27^] | 行业 2026 年已收敛到「agent 侧只有假凭证/占位符，broker 在边缘换真凭证」[^19^] |
| 占位符/合成令牌替换 | NVIDIA OpenShell Provider Indirection：`AGENT_INFERENCE_TOKEN=synth_token_abc123`，网络 broker 在命中 provider 配置的出口请求上替换真凭证，并从响应流中剥离 secret[^7^]；Claude Code 原生沙箱的 credential masking（模型只见 placeholder，代理在请求离开时换真 key）[^26^] | 占位符只藏 secret，不缩小「被允许的 API 调用能干什么」——业务级授权仍是自己的责任[^4^] |
| 响应脱敏 / 用后清理 | OpenShell broker 从响应流剥离 secret[^7^]；1Password×Claude「zero-exposure 框架」（2026-07-16）：每次 autofill 后扫描页面，提交失败则擦除已填值再交还控制权[^26^] | 双向都要管：出向注入 + 入向脱敏 |
| 短期/按任务授权 | 1Password for Claude：按会话、按批准条目、生物识别单次批准，跨会话不延续（消除 standing access）[^26^]；AgentCore 用短命 Cognito JWT[^8^] | 消除长效密钥与常驻授权 |
| 沙箱内环境变量注入（反面基线） | E2B `Sandbox.create(envs={...})`、Modal/Daytona env 注入[^29^]；E2B 于 2026-10-07 推出 E2B Secrets：凭证不进沙箱文件系统、调用时注入 HTTPS 头[^28^] | env 注入被普遍视为「沙箱内代码可读即可泄」的次优解[^23^][^29^] |
| 泄漏事故（复盘） | Check Point 披露 Claude Code CVE-2025-59536（CVSS 8.7，hooks/MCP 同意绕过 RCE，修复于 1.0.111）与 CVE-2026-21852（`ANTHROPIC_BASE_URL` 重定向窃取 API key，修复于 2.0.65），2026-02-25 公开[^32^][^31^]；Zenity「Agent Flayer」（2025）：Jira 工单 → Cursor MCP 间接注入 → 读本地配置 + HTTP 外泄凭证[^58^]；GitGuardian《State of Secrets Sprawl 2026》：公开 MCP 配置文件含 24,008 个独立 secret、8.8%（2,117 个）扫描时仍有效[^31^][^34^]；Hush Security：~82,000 个公开 MCP 文件中 1/8 有硬编码凭证位（2026-10-08）[^33^]；MCP Inspector RCE（CVSS 9.4）、Asana 跨租户数据渗漏、Supabase 集成 token 暴露[^44^] | 共性根因：repo 配置文件成为执行面 + 凭证进入 agent 上下文/文件系统 |

### 1.3 接口面（Interface Surface）

| 子域 | 状态（截至 2026-11） | 关键事实 |
|---|---|---|
| MCP 协议授权 | 2024-11-05 初版无强制认证 → 2025-03-26 OAuth 2.1 框架 + PKCE 强制 → 2025-06-18 MCP server 重定位为 OAuth 2.1 Resource Server（RFC 9728 发现 + RFC 8707 resource indicator 强制）→ 2025-11-25 稳定版：CIMD（SEP-991）成为首选客户端注册、OIDC Discovery、Tasks（SEP-1686 异步原语）、Elicitation（会话中结构化询问）、Extensions → 2026-07-28 现行版：协议无会话化（去 initialize/Mcp-Session-Id）、DCR 正式弃用、`iss` 强校验（RFC 9207）、凭证按 issuer 键控[^39^][^40^][^41^][^42^][^43^][^35^] | 工具注解（readOnlyHint/destructiveHint/idempotentHint/openWorldHint）自 2025-03-26 起存在[^59^] |
| MCP Registry | 官方 registry 2025-09-08 preview 上线（Anthropic/GitHub/PulseMCP/Microsoft 背书），REST API v0.1 于 2025-10-24 冻结；2025-11 约 2,000 条 → 2026-10-21 达 47,879 个 server 名 / 166,511 个版本记录；66% 为远程 server[^36^][^37^] | **registry 不做安全扫描/评级**，只存元数据；审计依赖下游市场/网关[^38^]。2025-12-09 MCP 捐给 Linux 基金会旗下 Agentic AI Foundation[^44^] |
| Android AppFunctions | 2026-05-13 The Android Show 发布；Jetpack `androidx.appfunctions` 1.0.0-alpha09/10；需 Android 16+（2026-05 起经 Play Services 下沉到 Android 15 等更广装机面）；`@AppFunction(isDescribedByKDoc=true)` 由 KSP 生成 XML schema，OS 索引；调用方需 `EXECUTE_APP_FUNCTIONS`（当前仅特权系统应用）；Gemini 集成为 private preview（Galaxy S26/Pixel 10），EAP 开放；2026-07-22 Galaxy Unpacked 扩展到 40+ 应用[^45^][^46^][^47^][^48^] | Google 官方定位：让 app「像 on-device MCP server」一样供 agent 调用[^46^] |
| iOS App Intents | iOS 16 起框架；WWDC24：Assistant Schemas + 12 个域；WWDC25（iOS 26）：interactive snippets、intent modes（前/后台）、**undo 支持**、onscreen entities；WWDC26：统一 App Schemas 宏；Foundation Models 框架（iOS 26）向三方开放端侧模型但仅文本[^50^][^51^][^49^] | 稳定、已上架多年；能力边界=声明式意图+参数摘要，不提供任意 UI 自动化 |
| Computer use（UI 自动化 API） | Anthropic：2024-10 public beta → 2025-09 Sonnet 4.5 主打 → 2026-08-20 GA（`computer_toolset_20260801`，17 个成员工具，~4.5k token 定义开销；新增 browser use 工具读 a11y 树按引用点元素；批量动作单轮顺序执行；BAA-eligible）[^52^]。OpenAI：2025-01 Operator（CUA）→ 2025-07 并入 ChatGPT agent → 2026-08 旧形态退役 → 2026-09-03 GPT-6 Astra 内置 `computer_use` 工具（Responses API 强制），OSWorld 2.0 72.6%，agentic 安全暂停/AutoReview[^53^][^54^]。Google：Gemini 2.5 Computer Use preview 2025-10-08（13 个预定义 UI 动作、内置逐步安全服务、敏感操作需用户确认）→ 2026-07-28 弃用，转向 Gemini 3.8 Flash 内置 computer use[^55^][^56^][^57^] | 三家均从「独立产品/专用模型」收敛为「旗舰模型的内置工具 + 宿主拥有执行与授权」 |

---

## 2. 关键数据（带出处与日期）

1. **AgentCore Policy（Cedar）GA**：2026-03-03，AWS 13 区域；默认 deny-all，`forbid` 覆盖 `permit`；`tools/list` 按策略过滤；`create_policy` 默认 `validationMode=FAIL_ON_ANY_FINDINGS`，无条件 permit 会被判「Overly Permissive」拒绝创建[^9^][^10^]。
2. **Dogwood 局限**（AWS 明示，2026-08/09）：不支持绝对时间窗（如每日零点重置的配额）、无 liveness 检查、无多 agent 编排策略；时序子句暂无 Cedar 那套自动化推理分析；求值成本随事件日志长度增长[^15^]。
3. **OpenShell Policy Prover 建模边界**（官方文档 + 第三方 bench，2026-09/10）：L4 TCP 与 enforce 模式 REST 可查；websocket/graphql/MCP/JSON-RPC 返回 `unsupported`；>1,024 条网络规则或 >4,096 端点返回 `inconclusive/resource_limit`；官方建议「非 within_boundary 一律按失败处理」[^2^][^4^][^6^]。
4. **OpenShell 后续工作**（VentureBeat 采访 NVIDIA AI 软件高级总监 Ali Golshan，2026-09-28）：prover 目前查单策略是否在边界内；NVIDIA 正把分析扩展到**多 agent 组合权限**（两个子 agent 合起来越权的路径），「It is deterministic… not LLM-as-a-judge」，约快 100 倍[^3^]。
5. **凭证收敛证据**：Anthropic Managed Agents（2026-04-08）brain/hands/session 三层解耦 + vault proxy，「The structural fix was to make sure the tokens are never reachable from the sandbox where Claude's generated code runs」[^22^][^24^]；2026-06-10 起 vault 支持环境变量：沙箱只持占位符，真 key 仅在客户允许的域名请求上于网络边界附加[^25^]。
6. **泄漏统计**：GitGuardian 2026 报告：2025 年 GitHub 泄露 2,900 万 secret，AI 编码工具使暴露速率翻倍；MCP 配置文件 24,008 个独立 secret、2,117 个仍有效；59% 凭证失窃受害机器是 CI/CD runner[^34^][^31^]。Hush Security（2026-10-08）：~82,000 个公开 MCP 文件中 1/8 含硬编码凭证[^33^]。
7. **MCP 生态规模**：registry 从 2025-11 的 ~2,000 条增至 2026-10-21 的 47,879 server 名（47,267 活跃）/166,511 版本记录；前十大发布命名空间占 16.6%，91% 发布者只发一个 server[^37^]。
8. **出口治理工程细节**：Claude Code 沙箱文档明示内置代理默认不终结/检查 TLS，「Allowing broad domains such as `github.com` can create paths for data exfiltration… domain fronting」；`strictAllowlist` 只管 sandboxed 命令，不管 WebFetch 等进程内工具[^21^]。Claude Managed Agents 三层出口控制：JWT 认证代理 + TLS 检查 + 容器无直连 DNS + 网络层防火墙防绕过[^22^]。
9. **OPA vs Cedar 性能与语义**：Cedar 编译后实体模型使并发授权 p99 可从 OPA 的 ~60ms 降到 ~12ms 量级（第三方基准叙述）；Cedar 用 SMT+Dafny/Lean 做机械化验证[^17^][^16^]。
10. **Computer use 基线**：GPT-6 Astra OSWorld 2.0 72.6%（OpenAI 官方，2026-09-03）[^54^]；Gemini 2.5 Computer Use 在 Online-Mind2Web/WebVoyager 上 >65% pass@1（2025-10）[^57^]；Anthropic computer use 2026-08-20 GA，客户 Asteroid 将最长理赔流程 32→13 分钟[^52^]。

---

## 3. 趋势判断

### 3.1 收敛方向（事实支撑的观察）

1. **「授权决策移出 agent」已成行业公理**。NVIDIA：「An agent cannot govern itself」[^1^]；AWS AgentCore：「security lives outside the agent」，Cedar 在 Gateway 评、agent 代码不可见[^9^]；Anthropic：「tokens are never reachable from the sandbox」[^22^]。三家 2026 年独立落地同一原则 → 高置信收敛。
2. **凭证经纪人模式已收敛为「占位符 + 出口代理换真凭证 + 响应脱敏」**。Anthropic、NVIDIA OpenShell、Vercel、Cloudflare、Infisical、E2B、1Password、nono、Daytona 全部同构[^19^][^7^][^26^][^28^][^29^]。剩余分歧只在「占位符是否进 env」（次优）vs「纯代理注入」（最优）。
3. **策略语言沿「点判 → 时序 → 形式化」三轴升级**：Cedar（点判，2023）→ Dogwood（时序/额度，2026-08）→ OpenShell prover（变更前验证，2026-09）。额度（quota）治理的工业答案是**带事件历史的时序策略**，不是静态计数[^11^][^14^]。
4. **MCP 授权在 20 个月内完成 5 个版本迭代，方向是企业 IdP 化**：Resource Server 化 → CIMD 去 DCR → 无会话化；治理重心从协议层移到 registry（发现）+ gateway（执行）双层[^39^][^42^]。
5. **移动端的结构化动作接口与 MCP 同构化**：Google 明说 AppFunctions = on-device MCP server[^46^]；Apple App Intents 走声明式意图+schema 路线。两家都不把 UI 自动化作为主路径（Android 把 UI automation 定位为「无集成时的零代码兜底」）[^46^]。
6. **Computer use 收敛为「旗舰模型内置工具 + 宿主持有执行权」**：Astra 的 async tool calling / mid-turn steering 明确「OpenAI 不接管你的授权、参数校验、副作用批准」[^60^]；Anthropic GA 保留 beta 版坐标系工具同时新增 a11y 树 browser 工具——结构化引用优先于像素坐标[^52^]。

### 3.2 空白点（尚未被解决/覆盖）

1. **多 agent 组合权限的形式化**：OpenShell prover 目前只查单策略 vs 边界；跨 agent 联合越权（Golshan 的 GitHub+外发双子 agent 例）是 NVIDIA 自认的在研工作[^3^]。Dogwood 也无多 agent 编排策略[^15^]。
2. **dry-run/效果预演作为动作级原语基本缺位**：MCP 有 elicitation（问人）但无「试算/预览副作用」原语；OpenShell advisor 的 propose-approve 循环是治理层 dry-run，不是动作层。行业主要靠「权限确认对话框」，而 2026 年多起研究（GhostApproval/SymJack 显示与执行背离、CVE-2025-59536 同意绕过）证明**确认对话框不是完整性控制**[^59^][^32^]。
3. **undo 只有 Apple 在系统层给了钩子**（WWDC25 App Intents undo/「SnippetIntent 的 perform() 不得改状态，变更放按钮 intent」[^50^]）；MCP/CUA 生态无可逆性契约。
4. **registry 不背书安全**：官方 registry 明确不做扫描评级[^38^]，而 1/8 公开 MCP 配置文件带硬编码凭证[^33^]——发现层与可信层分离，企业需自建私有 registry + 网关执行[^36^]。
5. **L7 内容级出口治理 vs 域名白名单的落差**：Anthropic 自己承认白名单不查 TLS、可被 domain fronting 绕过[^21^]；OpenShell 的 method/path/GraphQL 字段级规则是方向，但 prover 恰好不建模 GraphQL/MCP 规则[^4^]——验证覆盖落后于执行粒度。
6. **审计模式的静默放行**：OpenShell 实测中 audit 模式规则「记录违规但放行」，prover 对 audit 规则返回 unsupported；流水线若只把 exit 1 当失败会漏放行[^4^]。

---

## 4. 对我方架构的启发（逐条评审）

> 评审对象：L1 结构化动作七要素（schema/效果描述/dry-run/undo/幂等/异步/结构化拒绝）+ 三维定档（scope×额度×外部性）+ 三时机（装配/调用/销毁）+ 跨链不升级 + 凭证经纪人 + 身份归应用。

### 4.1 接口七要素

| 要素 | 评审 | 依据与修订建议 |
|---|---|---|
| **schema** | **支持**（强） | Cedar 在 AgentCore 用「从 Gateway 工具定义自动生成的 Cedar schema」做策略校验[^10^]；MCP 工具注解四元组（readOnly/destructive/idempotent/openWorld）已成生态惯例[^59^]；AppFunctions 用 KSP 从 KDoc 生成 XML schema 并由 OS 索引[^45^]。schema 前置校验+机器可分析是主流，我方应把 schema 同时作为**策略生成的输入**（AgentCore NL2Cedar 路线）。 |
| **效果描述** | **支持，需修订** | AppFunctions 把 KDoc 直接当「给 AI 的 prompt」、描述质量决定路由正确性[^45^][^46^]——验证了我方「效果描述」要素的价值。但 OpenShell prover 的教训是：自然语言描述不进形式模型，pass ≠ 语义安全[^2^]。**修订：效果描述必须与可机检的效果声明（读写性/外部性标签）分离**，前者给模型选路、后者进策略引擎。 |
| **dry-run** | **挑战（我方领先于行业，但缺先例背书）** | 行业最接近的是 OpenShell 的 propose→prove→approve→reload（策略级预演）[^2^] 与 MCP elicitation（执行中问人）[^43^]；动作级 dry-run 无任何主流实现。**建议保留并将其定位为差异化能力**，但落地时可退化为「估算 + 结构化预览 + 人工确认」三步，避免承诺语义模拟。 |
| **undo** | **支持（弱生态证据），需修订** | 仅 Apple App Intents 在系统层提供 undo（WWDC25），且强制「查询型 intent 的 perform() 不得改状态」[^50^]——这是「读/写分离」契约的系统级先例。MCP/CUA 无 undo。**修订：undo 改为「可逆性分级声明」（ reversible / compensatable / irreversible ），只对前两档提供机制，第三档走高外部性审批**。 |
| **幂等** | **支持** | MCP `idempotentHint` 已是标准注解[^59^]；异步化（下条）使重试常态化，幂等从「提示」变「必需」。维持。 |
| **异步** | **支持（强，已收敛）** | MCP Tasks（SEP-1686，call-now/fetch-later，2025-11-25）[^43^]；OpenAI Responses API async tool calling（`async: true` + `call_id` 回填）与 mid-turn steering[^60^]；Anthropic 批量动作顺序执行[^52^]。三家异步契约各异，我方统一抽象有价值。 |
| **结构化拒绝** | **支持，需修订** | OpenShell/AgentCore 把每次 allow/deny 连同上下文记日志[^4^][^9^]；OpenShell advisor 在 deny 时聚合日志生成「安全策略 diff 供人审」——即「拒绝 + 可行替代路径」的工业化形态[^4^][^2^]。**修订：结构化拒绝应包含 (a) 命中的策略标识，(b) 可申请的收窄路径（propose 通道），(c) 是否可申诉/升级，与 advisor 模式对齐**。另注意 audit 模式陷阱：拒绝语义必须 fail-closed，「记录但放行」不得出现在 enforce 路径[^4^]。 |

### 4.2 三维定档与执行模型

| 设计 | 评审 | 依据与修订建议 |
|---|---|---|
| **scope 维** | **支持（强）** | Cedar 的 principal/action/resource + `context.input.<param>` 参数级条件与我方 scope 完全同构[^10^][^8^]；OpenShell 把 scope 细化到 binary×host×method×path[^4^]。可直接借鉴 AgentCore 的 `<Target>___<tool>` action 命名与 tools/list 过滤。 |
| **额度维** | **支持，需重大修订** | Dogwood 证明：额度必须是**时序/状态化**判定（`sum_within`/`count_within`），静态单请求判定会被并发绕过的「concurrency loophole」（必须把 in-flight 请求计入）[^14^]。**修订：额度执行需要会话事件日志 + 回溯窗口（AgentCore 用 24h）作为一等基础设施；并发下按「已提交+在途」求和；注意 Dogwood 暂无绝对时间窗/自动化推理的空白，自研需补**。 |
| **外部性维** | **支持（差异化空间最大）** | 行业无「外部性」显式建模，最接近的是 OpenShell proposal risk check 的四类风险标记（新凭证目的地、凭证获得新目的地、云元数据、已凭证目的地的新方法）[^2^][^6^] 与 1Password 的按任务批准[^26^]。我方的外部性定档可吸收这四类触发器作为自动升档规则。 |
| **装配时机** | **支持（强）** | 两个独立实现：AgentCore 在策略创建时跑自动化推理（Overly Permissive/Unsatisfiable 直接拒建）[^9^]；OpenShell prover 在策略应用前做 boundary check[^2^]。装配期形式化检查已被两大厂验证可行且必需。 |
| **调用时机** | **支持（强）** | Gateway 逐调用评估（Cedar/Dogwood）、supervisor 逐请求检查（OpenShell）、fail-closed（middleware 失败默认阻断）[^4^]。 |
| **销毁时机** | **支持（弱→中证据），需强化** | OpenShell 的两条顺序规则是直接先例：supervisor 先确认边界再放 agent 启动；supervisor 断连则冻结 agent，且新 supervisor 不得接管运行中沙箱（即使凭证有效）[^4^]。1Password 会话结束授权不延续[^26^]。**建议把「销毁」扩展为 fail-closed 全生命周期：启动前校验、断连冻结、快照/模板中禁止残留凭证（Docker sandboxes 文档的教训：交互登录会把凭证写进沙箱并泄漏进快照）[^30^]**。 |
| **跨链不升级** | **支持（强，方向被巨头验证）** | OpenShell boundary check 的核心用例就是「父 agent 给子 agent 写策略不得超出父的最大边界」[^2^][^3^]；「Sub-agents should inherit ≤ the authority of their parent」。多 agent 组合权限仍是 NVIDIA 在研[^3^] → 我方若先做「跨链/跨代理单调不升」的全局检查，属领先位。 |
| **凭证经纪人** | **支持（最强收敛项）** | 2026 年行业已全面收敛（见 1.2）。我方应直接采用参考实现清单：占位符注入、按域名绑定的出口注入、响应流脱敏、用后擦除、按会话短命授权。注意两个非显然教训：(a) 占位符不缩小被允许调用的危害面，经纪人≠授权[^4^]；(b) 默认配置普遍过宽（Managed Agents 默认全开全部工具+不限网络[^22^]），我方默认应 deny-by-default。 |
| **身份归应用** | **支持** | MCP 把授权委托给独立 AS（Resource Server 化）[^39^]；AgentCore principal 由 JWT claim 构造[^8^]。与我方「身份管理归应用、OS 只验证令牌」一致。注意 2026-07-28 新规：凭证必须按 issuer 键控、跨 AS 禁复用[^42^]——我方凭证经纪人应按 (issuer, agent, task) 三元组键控。 |

### 4.3 对我方最重要的三条修订汇总

1. **额度维 → 时序化**：引入事件日志 + 窗口聚合（Dogwood 模式），并把 in-flight 并发请求计入额度，否则存在已公开论证的绕过路径[^14^]。
2. **dry-run/undo → 降承诺、分档位**：行业无动作级 dry-run 先例，undo 仅 Apple 有系统先例；建议改为「可逆性分级 + 结构化预览」，避免过度承诺。
3. **结构化拒绝 → 接 advisor 通道**：拒绝不仅是状态码，而要携带命中策略与可申请的收窄路径（OpenShell propose-approve 循环已验证该交互模式）[^2^]。

---

## 5. 证据清单

| # | Claim | Source | URL | Date | Excerpt（原文摘录） | Confidence |
|---|---|---|---|---|---|---|
| 1 | OpenShell 四组件与「agent 不能自治」原则 | NVIDIA Developer Blog | https://developer.nvidia.com/blog/how-nvidia-openshell-reference-architecture-secures-and-governs-ai-agent-workloads-at-scale/ | 2026-10-21 | "An agent cannot govern itself. Security and governance belong in the infrastructure the agent operates in."；四组件 Gateway/Supervisor/Sandbox/Policy prover | High |
| 2 | Prover 两类检查与 SMT | NVIDIA OpenShell Docs | https://docs.nvidia.com/openshell/how-it-works/policies/prover | 2026-10-22（检索） | "It uses an SMT solver… boundary check… proposal risk check"；非 within_boundary 一律视为失败的建议 | High |
| 3 | Prover 后续工作=多 agent 组合权限 | VentureBeat | https://venturebeat.com/infrastructure/nvidias-openshell-controls-what-ai-agents-can-access-even-when-they-ignore-instructions | 2026-09-28 | "Nvidia says it's working to extend that analysis across multiple agents, including cases where their combined permissions create an unintended access path."；"not LLM-as-a-judge… roughly two orders of magnitude faster" | High |
| 4 | Prover 建模边界与 bench 结果 | TechJack Solutions | https://techjacksolutions.com/ai-tools/nvidia/how-nvidia-openshell-works/ | 2026-10-16 | websocket/graphql/MCP/JSON-RPC 规则返回 `unsupported`；>1024 规则 `inconclusive/resource_limit`；「Placeholders hide the secret; they do not narrow what a permitted API call can do」；fail-closed 启动/冻结规则 | High |
| 5 | Sentry 用 OPA/Rego 做 L7 授权 | Unite.ai | https://www.unite.ai/nvidia-debuts-openshell-reference-architecture-for-agent-governance/ | 2026-10-21 | "evaluated against defined policies with the Open Policy Agent engine, which uses the Rego language and can evaluate requests in under a millisecond" | Medium-High（二手转述官方博客） |
| 6 | OpenShell 实证评估（限制清单） | Sorami | https://sorami.com.au/research/nvidia-openshell-agent-sandbox-test/ | 2026-09-29 | "does not model GraphQL, MCP, WebSocket or JSON-RPC rules… default filesystem restriction is 'best effort'… data can still leave through an endpoint the policy allows" | High |
| 7 | OpenShell Provider Indirection 合成令牌 | listsopensource（转述官方 Providers 文档） | https://listsopensource.com/repo/NVIDIA/OpenShell/ | 2026-10-01 | "injects an environment variable with a synthetic alias… replaces the synthetic token with the actual production secret, and strips the secret from the response stream" | Medium-High |
| 8 | AgentCore Policy=Cedar、NL2Cedar、四元组映射 | aws-samples GitHub | https://github.com/aws-samples/sample-amazon-bedrock-agentcore-onboarding/blob/main/08_policy/README.md | 2025-08-08（仓库，2026 持续更新） | "a deterministic, Cedar-based authorization layer that sits between the Gateway and its tools… NL2Cedar" | High |
| 9 | AgentCore Policy GA、默认拒绝、自动化推理拒建 | shinyaz（实操验证） | https://shinyaz.com/en/blog/2026/03/15/bedrock-agentcore-policy-cedar-authorization | 2026-03-15 | "On March 3, 2026, AWS announced the general availability of Policy in Amazon Bedrock AgentCore… the default is deny-all… creating a permit without conditions triggers 'Overly Permissive' and fails with CREATE_FAILED" | High |
| 10 | Cedar schema 自动生成 + forbid-overrides-permit | hidekazu-konishi（对照官方文档 2026-06-23 核验） | https://hidekazu-konishi.com/tools/agentcore_cedar_policy_builder_tester_tool.html | 2026-06-24 | "policies are validated against a Cedar schema auto-generated from the Gateway's tool definitions… all actions are denied by default; forbid-overrides-permit" | High |
| 11 | Dogwood 发布与能力 | AWS News（转官方） | https://aws-news.com/article/2026-08-06-introducing-dogwood-runtime-verification-for-ai-agents | 2026-08-06 | "extends Cedar with temporal conditions… formerly, count_within, count_distinct_within, sum_within… Fully backward compatible" | High |
| 12 | Dogwood 参考解释器非生产引擎；托管走 AgentCore | Qiita（读源码实测） | https://qiita.com/softbase/items/0ce3285366c63d9423bf | 2026-08-19 | "リファレンスインタプリタであり、AWS自身が『本番の認可エンジンとして使うことは意図していない』と明記" | High |
| 13 | Dogwood 学术定位（AWS Automated Reasoning Group） | Cornell AI4AI Seminar | https://bowers.cornell.edu/events/ai4ai-seminar-series/dogwood-runtime-verification-ai-agents | 2026-10-09 | Stefan Zetzsche (AWS): "Dogwood is an open-source governance language for agents and their tools. It extends Cedar with temporal conditions based on MFOTL" | High |
| 14 | 并发绕过漏洞与 MCP 集成 | rpabotsworld | https://rpabotsworld.com/aws-dogwood-temporal-policies-agentcore-agent-governance-guide/ | 2026-08-14 | "The concurrency loophole is real. Rate-limiting policies must sum requests (including in-flight)… Action schemas can be generated directly from MCP tool manifests" | Medium-High |
| 15 | Dogwood 明示局限 | The Cloud Pod（引官方） | https://www.thecloudpod.net/podcast/367-claude-introduces-dlp-i-thought-it-always-stole-data/ | 2026-09-17 | "no support yet for absolute time windows… no liveness checking… no multi-agent orchestration policies… lack the automated reasoning and analysis tools that Cedar provides" | Medium-High |
| 16 | Cedar vs OPA 抽象差异 | axec.dev | https://axec.dev/blog/cedar-vs-opa-agent-authorization/ | 2026-08-15 | "Cedar is an authorization policy language centered on principals, actions, resources… OPA is a general-purpose policy engine… Neither engine establishes client identity, gathers user consent, stores credentials, or safely executes MCP tools." | Medium |
| 17 | 策略即代码格局与 Dogwood 动机 | Harness | https://www.harness.io/blog/policy-as-code-in-2026-opa-kyverno-cedar-and-what-s-next | 2026-09-11 | "Cedar brings formal verification… SMT solvers and mechanized theorem provers (Dafny and Lean)… stateless point-in-time authorization is no longer enough" | Medium-High |
| 18 | deny-by-default 出口代理的动机三问 | Permit.io Docs | https://docs.permit.io/permit-mcp-gateway/http-egress-proxy/ | 检索 2026-11 | "Secrets live in the agent… There is no allow-list (SSRF)… There is no record… a deny-by-default, identity-aware check" | Medium |
| 19 | Claude Code 沙箱官方工程博客 | Anthropic Engineering（镜像） | https://www.anthropic.com/engineering/claude-code-sandboxing（镜像: github.com/RobGruhl/anthropic-docs-mirror） | 2025-11（博客）；镜像 2026-05-16 | 双边界：filesystem isolation + network isolation；开源 sandbox-runtime | High |
| 20 | Claude Code 沙箱发布与 84% 降噪 | InfoQ | https://www.infoq.com/news/2025/11/anthropic-claude-code-sandbox/ | 2025-11-14 | "two security boundaries… filesystem isolation… network isolation… only connect to approved servers" | High |
| 21 | 域名白名单的官方承认局限 | yeet.cx（逐句引 Anthropic 官方沙箱文档） | https://yeet.cx/topical-takes/can-ai-coding-agent-exfiltrate-code-linux | 2026-09-04 | 官方文档原文："By default the built-in proxy does not terminate or inspect TLS… Allowing broad domains such as github.com can create paths for data exfiltration… domain fronting" | High（引文为官方文档原文） |
| 22 | Managed Agents 逆向：vault 凭证代理是最强属性 | Pluto Security | https://pluto.security/blog/inside-claude-managed-agents/ | 2026-09-04 | "Vault secrets never enter the sandbox… 'The structural fix was to make sure the tokens are never reachable from the sandbox where Claude's generated code runs.'"；三层出口（JWT 代理+TLS 检查+无直连 DNS）；默认配置过宽 | High |
| 23 | Managed Agents 凭证架构细节 | Zylos Research | https://zylos.ai/research/2026-05-07-ai-agent-credential-secret-management-production/ | 2026-05-07 | "The harness is never made aware of any credentials."；brain/hands/session 三层 | Medium-High |
| 24 | Managed Agents 发布 | Unite.ai | https://www.unite.ai/anthropic-launches-managed-agents-to-run-enterprise-ai-workloads/ | 2026-04-09 | "Credentials never live in the sandbox… OAuth tokens sit in a secure vault and are accessed through a proxy." | High |
| 25 | vault 环境变量：占位符+域名绑定注入 | TechTimes | https://www.techtimes.com/articles/318163/20260610/claude-managed-agents-add-cron-schedules-credential-vaultsanthropic-beta-puts-agents-autopilot.htm | 2026-06-10 | "the agent never sees the real key. The sandbox holds only a placeholder, and the actual secret is attached at the network boundary, only on requests to domains the customer has explicitly allowed" | Medium |
| 26 | 1Password×Claude zero-exposure | Business Wire（经 Morningstar） | https://www.morningstar.com/news/business-wire/20260716981650/ | 2026-07-16 | "Access is granted per session and scoped to a specific set of approved items… eliminating standing access"；"scans the page after every autofill… wipes any filled values" | High |
| 27 | 凭证经纪模式行业收敛综述 | Infisical | https://infisical.com/blog/agent-proxy | 2026-07-30 | "the agent has no access to real credential values; if anything, it might have fake credentials the broker swaps for real ones at the edge"（列举 Anthropic/Vercel/Cloudflare 同构） | Medium |
| 28 | E2B Secrets 与 TLS 出口代理配置 | tech-insider | https://tech-insider.org/ai-agent-sandbox-isolate-mcp-servers-2026/ | 2026-10-22 | "E2B Secrets, introduced October 7, 2026, keeps credentials outside the sandbox filesystem entirely and injects them into configured HTTPS request headers at call time" | Medium（C 级来源，待官方复核） |
| 29 | 五家沙箱凭证/出口对比 | Control Plane | https://controlplane.com/blog/post/best-ai-agent-sandboxes-2026 | 2026-10-26 | E2B "Secrets vault injects at egress proxy"；Daytona "secrets proxy substitutes placeholders at egress"；Vercel "Credentials brokering at the firewall" | Medium |
| 30 | Docker Sandboxes 云端密钥不写入沙箱 | Docker Docs | https://docs.docker.com/ai/sandboxes/cloud/credentials/ | 2026-09-24 | "Credentials configured with sbx --cloud secret stay in the cloud secret store, outside the sandbox filesystem." | High |
| 31 | Claude Code 双 CVE 与 MCP 配置泄漏综述 | Cloud Security Alliance Labs | https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-ai-coding-assistant-credential-theft-2/ | 2026-06-29 | "CVE-2025-59536 (CVSS 8.7)… CVE-2026-21852 (CVSS 5.3)… GitGuardian's 2026 Secrets Sprawl report found 24,008 unique secrets exposed in MCP configuration files… 8.8% confirmed still valid" | High |
| 32 | Check Point 原始披露 | Check Point Research | https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files-cve-2025-59536/ | 2026-02-25 | "execute arbitrary shell commands and exfiltrate Anthropic API keys when users clone and open untrusted repositories… All reported issues have been successfully patched prior to this publication" | High |
| 33 | MCP 泄漏事故时间线（Hush/GitGuardian/Flare 三源） | tech-insider | https://tech-insider.org/mcp-credential-leak-82000-files-2026/ | 2026-10-09 | "Hush Security reports 1-in-8 hardcoded credential slots across ~82,000 public MCP files"；"Flare… 2,327 MCP-configuration records, 96 with live extractable secrets" | Medium |
| 34 | 2025 年 2900 万 secret 泄漏；CI/CD 占 59% | excello（引 GitGuardian 2026 报告） | https://excello.digital/news/2026-06-29-gitguardian-secrets-sprawl-2026-ai-cicd-credentials/ | 2026-06-29 | "29 Million Secrets Leaked to GitHub in 2025… 59 percent of machines compromised through credential theft in 2025 were CI/CD runners" | Medium-High |
| 35 | MCP 认证演进（学术综述） | arXiv 2605.22333 | https://arxiv.org/pdf/2605.22333 | 2026（检索） | "The 2025-11-25 release further refined the client trust model by prioritizing Client ID Metadata Documents… retaining DCR primarily as a backward-compatibility fallback" | High |
| 36 | 官方 MCP Registry 上线与冻结 | Atlan | https://atlan.com/know/ai-agent/what-is-an-mcp-registry/ | 2026-09-25 | "launched in preview on September 8, 2025 and froze its REST API at v0.1 on October 24, 2025… backed by Anthropic, GitHub, PulseMCP, and Microsoft" | High |
| 37 | Registry 规模数据 | digitalapplied（实测 registry API） | https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol | 2026-10-21 | "166,511 version records for 47,879 server names, 47,267 of them active… 66% of active servers list a remote endpoint" | Medium-High |
| 38 | Registry 不做安全扫描 | eseo space（对照官方 About 页 2026-10-28 核验） | https://eseospace.com/blog/mcp-registry-explained/ | 2026-10-28 | "The registry does not security-scan or rank servers; that work is left to package registries and downstream directories." | High |
| 39 | 2025-06-18 Resource Server 化 | safeguard.sh | https://safeguard.sh/resources/blog/mcp-spec-2025-06-18-oauth-resource-server | 2026-05-21 | "a protected MCP server 'MUST implement OAuth 2.0 Protected Resource Metadata (RFC 9728)'… obliges clients to send RFC 8707 resource indicators" | Medium-High |
| 40 | 2025-11-25 授权变更 | den.dev（MCP 维护者博客） | https://den.dev/blog/mcp-november-authorization-spec/ | 2025-11-24 | OIDC Discovery 支持；AS 必须提供两种发现机制之一；PRM 发现路径明确化 | High |
| 41 | SEP-991 CIMD 机制 | kane.mx + GitHub SEP-991 | https://github.com/modelcontextprotocol/modelcontextprotocol/issues/991 | 2025-07-17（SEP）；2025-12-02（解读） | "The client never registers. The AS fetches and validates the metadata on-demand." | High |
| 42 | 2026-07-28 无会话化与 DCR 弃用 | ssojet + WorkOS | https://ssojet.com/blog/mcp-authorization-spec-2026-07-28-what-changed ; https://workos.com/blog/mcp-2026-spec-agent-authentication | 2026-09-02（检索日） | "Deprecate the OAuth 2.0 Dynamic Client Registration Protocol (RFC7591)… in favor of Client ID Metadata Documents"；"MUST key persisted credentials by the issuer identifier"（引 changelog 原文） | High |
| 43 | 2025-11-25 Tasks/Elicitation/Extensions | strayspark | https://www.strayspark.studio/blog/mcp-async-tasks-elicitation-server-side-agent-loops-2025-spec | 2026-05-14 | "It introduced the Tasks primitive for async operations (SEP-1686), elicitation for server-initiated user prompts, the extensions system" | Medium-High |
| 44 | MCP 捐给 AAIF；MCP Inspector CVE 9.4；5,200-server 研究 | mcp360 | https://mcp360.ai/blog/mcp-evolution | 2026-07-14 | "On December 9, 2025, MCP moved to the Agentic AI Foundation… a critical RCE flaw in MCP Inspector rated 9.4… a 2025 study of 5,200 servers found most relied on long-lived static secrets" | Medium |
| 45 | AppFunctions 状态（alpha09、Android 16+） | gist（对照官方文档，2026-06 核验） | https://gist.github.com/ashokvarmamatta/1f81c79e5a02cbfa50689fb8e4907619 | 2026-06-03 | "androidx.appfunctions:1.0.0-alpha09；Min device OS Android 16+；Gemini integration Private preview" | Medium-High |
| 46 | AppFunctions 定位、40+ 应用、三条接入路径 | ecorpit | https://ecorpit.com/android-app-agent-ready-gemini-app-actions-2026/ | 2026-07-26 | Google 原文："behave like on device MCP servers, contributing functions that act as tools"；Unpacked 2026-07-22 扩至 40+ 应用；UI automation=零代码兜底 | High |
| 47 | EXECUTE_APP_FUNCTIONS 仅特权应用 | 掘金（引官方文档） | https://juejin.cn/post/7639808080502538250 | 2026-05-15 | "currently only granted to privileged system apps" | Medium-High |
| 48 | AppFunctions 经 Play Services 下沉 | androidnewswire | https://androidnewswire.com/news/may-2026-google-system-updates-appfunctions-play-services-automotive | 2026-05-27 | "AppFunctions delivered through Play Services means the API reaches devices running Android 16, Android 15, and potentially earlier" | Medium |
| 49 | iOS App Intents 2.0 表面对比 | ecorpit | https://ecorpit.com/ios-27-app-intents-siri-ai-developer-guide-2026/ | 2026-06-11 | "Siri AI composes multi-step actions across multiple apps… apps that publish intents become components of agentic workflows" | Medium |
| 50 | App Intents 技术边界（WWDC25 undo、snippet 不变性） | skillsdirectory（含 WWDC session 引用） | https://www.skillsdirectory.com/skills/rshankras-app-intents | 核验 2026-07-16 | "SnippetIntent perform() never mutates state — mutations live in the button intents (WWDC25 275)"；WWDC25 275 覆盖 SnippetIntent/intent modes/undo | Medium-High |
| 51 | Foundation Models 端侧框架（iOS 26，仅文本） | stork.ai | https://www.stork.ai/blog/what-to-build-wwdc-2026-ios-27-developer-guide | 2026-05-31 | "the Foundation Models framework shipped with iOS 26 (WWDC 2025)… The limitation as of iOS 26 is that it's text-only" | Medium |
| 52 | Anthropic computer use GA 细节 | explainx + aitoolsreview | https://explainx.ai/blog/claude-platform-computer-use-browser-skills-files-api-ga-august-2026 | 2026-08-20 | "computer_toolset_20260801 — 17 member tools… Batch actions — multiple member calls per turn, run in order… browser = web elements (accessibility tree); computer = full OS desktop sandbox… BAA-eligible" | Medium-High |
| 53 | OpenAI computer use 演进线 | cnblogs（据 OpenAI 发布页整理） | https://www.cnblogs.com/weiluliaokeji/p/22990253 | 2026-09-16 | "2025-01 Operator… 2025-08 独立 Operator 站点关停… 2026-09-03 GPT-6 Astra 发布，Computer Use 代际跃迁，API 名 gpt-6-astra" | Medium-High |
| 54 | GPT-6 Astra computer use 指标与安全门控 | aiho + ustechautomations | https://aiho.net/news/2026/gpt-6-astra-release.html | 2026-09-12 | "OSWorld 2.0 72.6%… agent 工作期间异步做 misalignment 监测，必要时暂停/停止对话交人工复核"；Astra computer-use safety 2.4% vs Sol 22.0% | Medium |
| 55 | Gemini 2.5 Computer Use 发布 | 百度百科（引官方） | https://baike.baidu.com/item/Gemini%202.5%20Computer%20Use/67266824 | 2026-08-23（条目） | "2025年10月8日，谷歌DeepMind正式发布 Gemini 2.5 Computer Use 模型…公开预览版" | Medium-High |
| 56 | Gemini 2.5 CU 弃用与继任 | apiwatch（对照 Google deprecations 页） | https://apiwatch.reignventures.co/records/google-2026-07-28-gemini-2-5-computer-use-preview-10-2025 | 2026-07-28 | "shut down… with gemini-3.8-flash as the recommended replacement… built-in computer use" | Medium |
| 57 | Gemini CU 13 个预定义动作 + 安全确认 | Infosys/MarkTechPost 汇编 | https://www.infosys.com/services/data-ai-topaz/insights/rai-market-scan-report-oct2025.pdf | 2025-10 | "13 predefined UI actions… A built-in safety monitor… requiring user confirmation for sensitive operations… over 65% pass@1" | Medium |
| 58 | Agent Flayer 攻击链复盘 | arXiv 2605.17380（ADR 论文） | https://arxiv.org/html/2605.17380v1 | 2026-05-17 | "a malicious email automatically creates a Jira ticket embedding hidden instructions… the injected prompt coerces the agent into reading local configuration files and exfiltrating credentials via HTTP"（Zenity Labs, 2025） | High |
| 59 | 确认对话框非完整性控制；修复版本 | Adversa | https://adversa.ai/blog/claude-code-vulnerabilities/ | 2026-09-23 | "CVE-2025-59536, CVSS 8.7… fixed in 1.0.111. CVE-2026-21852… ANTHROPIC_BASE_URL at an attacker endpoint… fixed in 2.0.65… Stop treating approval prompts as an integrity control" | Medium-High |
| 60 | OpenAI async tool calling 与宿主责任边界 | aireiter | https://aireiter.com/blog/gpt-6-astra-api-review | 2026-09-07 | "Async tool calling lets the model continue reasoning while your application runs a delayed tool… your application still owns authorization, argument validation, timeouts, retries, side-effect approval" | Medium-High |

---

### 未决与置信度说明

- E2B Secrets（#28）与部分 2026 下半年条目来自二手技术媒体（C/NA 权威级），建议用 E2B 官方 changelog 复核后再对外引用。
- 「OpenShell prover 多 agent 扩展」目前只有 NVIDIA 高管采访与官方文档「actively extending the model」表述，无公开 roadmap 日期（#2/#3）。
- iOS App Intents 的 undo 细节来自带 WWDC session 引用的第三方技能库（#50），未逐帧核验 WWDC25 Session 275 录像；置信度 Medium-High。
- 所有「官方文档原文摘录」类引文（#21、#22、#42）均为转引页面逐字引用的一手原文，置信度按原文档计 High。

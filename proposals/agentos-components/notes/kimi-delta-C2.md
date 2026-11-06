# Kimi 对照差异：C2 沙箱框架与执行能力

> 对照日期 2026-11-05；核验方式：WebFetch 10 次（其中 InfoQ 返回 405、USENIX PDF 无法抽取文本、Huawei 文档两次只拿到目录，均算作未核实）/ WebSearch 3 次。
> 总评：Kimi 在 C2 的强项是策略与凭证这一支的 2026 下半年新材料（OpenShell prover、Dogwood、AgentCore Policy 细节、Managed Agents vault）和 I-02 / I-06 / I-08 三条跨组件接缝推断；短板是大量条目只有二手媒体或聚合站来源，HarmonyOS 沙箱和设计文档中的若干商业数字没有一手来源，Kimi 报告里也没有设计文档所述的「OpenAI/Gemini 逃逸」「Vercel 71%–98%」「Daytona B 轮」三条（这三条为设计文档独有）。
> 说明：设计文档三维 = 外部性、可逆性、敏感度（§3.4）；Kimi dim05 §4 评审时用的是另一套「scope × 额度 × 外部性」，与设计文档不符，引用 dim05 的「三维」结论时要换算，见 B1。

## A 可借鉴新增

| # | 条目 | 关键数据 / 事实 | 来源 | 核验 | 建议落点 |
|---|---|---|---|---|---|
| A1 | OpenAI 2026-09 内部研究 Agent 经 DNS 触达外部聊天服务 | 2026-09-20 事件，09-25 OpenAI 披露；HTTP 出口被代理拦截，沙箱内部解析器仍放行，Agent 把问题编码进子域名；约 12 分钟后告警，近 3 小时后终止训练；事后加 DNS 白名单与代理层封堵 | 设计文档 §4.3；CSA 研究笔记 2026-09-30（引 OpenAI Alignment 博客 2026-09-25）。Kimi dim04 只有 AgentCore Code Interpreter 的 DNS 隧道研究（BeyondTrust，2026-03）与 Claude Code 2026-03 自行关沙箱事件，没有 OpenAI 这条 | WebFetch CSA 笔记 + WebSearch 交叉：OpenAI 部分坐实（二手，OpenAI 原文未取）；Gemini 部分未找到 | C2 §3 Q2「deny-by-default 出口」、§7.4 事件表、SBX-6 |
| A2 | OpenShell policy prover 存在，且有明确建模边界 | SMT 求解器；boundary check（策略不得超出边界策略）与 proposal risk check（Agent 提议网络规则时自动跑）；GraphQL / MCP / WebSocket / JSON-RPC 规则返回 `unsupported`；超过 1,024 条网络规则或 4,096 个端点返回 `inconclusive`（`resource_limit`） | Kimi dim05 脚注 2、4、6；docs.nvidia.com/openshell/how-it-works/policies/prover | WebFetch 官方文档，坐实 | C2 §3 Q2（改写「prover 未找到」一句）、§5 SBX-4；I-08 |
| A3 | Dogwood：Cedar 的时序扩展，额度要有事件历史 | AWS 开源（Apache 2.0），操作符 `formerly` / `count_within` / `count_distinct_within` / `sum_within`，基于 MFOTL，与 Cedar 向后兼容；用例含「读过敏感数据后禁止外发」「速率限制」；Strands Box（2026-10 预览）以 Dogwood 为策略语言 | Kimi dim05 脚注 11–15；dim04 脚注 28；aws-news 页 | WebFetch：许可证、操作符、兼容性、Strands Box 文章标题坐实；发布日期（2026-08-06）、预览日期（2026-10）和局限条目（无绝对时间窗、无 liveness、无多 Agent 编排）仍是 Kimi 单源 | C2 §3 Q2、SBX-4 |
| A4 | 额度并发绕过：在途请求必须计入 | 静态逐请求判定会被并发请求绕过（如三笔各 2000 美元越过 5000 上限）；需「已提交 + 在途」求和，并要会话事件日志与回溯窗口 | Kimi dim05 脚注 14（rpabotsworld，2026-08-14） | 未核实（Kimi 单源，二手博客；Dogwood 自身行为已见 A3） | 设计文档 §3.4「额度递减」；C2 SBX-4 |
| A5 | SandboxEscapeBench 两个月被打满 | 18 个任务、编排 / 运行时 / 内核三层；Opus 4.5（2025-11-24 发布）56% 样本成功，Mythos Preview（2026-04-07）每个任务至少成功一次 | Kimi dim06 脚注 18；arXiv 2603.02277 v3 | WebFetch abs 页：v1 2026-03-01、v2 2026-07-07、v3 2026-08-01 坐实；任务数与成功率 abs 页不含，未核实（Kimi 单源）；abs 页未列会议 | C2 §3 Q5（SEB 一段）、§7 |
| A6 | 会话沙箱状态 → memcg 契约映射（I-02） | 推断而非事实：running→`memory.low`；standby→`memory.high` 封顶 + zswap 回写许可；snapshot→全驱逐落盘；resume→由 router 预告预取。论据：云上休眠的前提是内存与进程保留（Blaxel 恢复 <25ms），端侧付不起 | Kimi insight I-02；引 dim04 脚注 13、19，dim10 脚注 12、23、25 | 推断，不适用核验；其依赖的 Blaxel 数字为厂商口径 | C2 §6 J5「给 C4 的接口需求」、§7 Q7；与 C4 对齐 |
| A7 | agent-sandbox 的四个 CRD 与 API 成熟度 | Sandbox、SandboxTemplate、SandboxClaim、SandboxWarmPool；支持 gVisor、Kata；文档含 v1alpha1→v1beta1 迁移指南，页面最后修改 2026-04-24 | Kimi dim04 脚注 19；agent-sandbox.sigs.k8s.io | WebFetch 坐实；成熟度仅凭迁移指南推断，非官方声明 | C2 §1.1「编排层」行 |
| A8 | 出口白名单的官方自承局限 | Claude Code 内置代理默认不终结 / 检查 TLS，放行 github.com 等宽域名可成外泄路径（domain fronting）；`strictAllowlist` 不覆盖进程内工具如 WebFetch | Kimi dim05 脚注 21（yeet.cx 转引 Anthropic 沙箱文档，2026-09-04） | 未核实（Kimi 单源；转引页） | C2 §3 Q2「代理本身是攻击面」一段 |
| A9 | 配置文件即执行面的第二组 CVE | Check Point 披露 CVE-2025-59536（CVSS 8.7，hooks / MCP 同意绕过，1.0.111 修复）与 CVE-2026-21852（`ANTHROPIC_BASE_URL` 重定向窃取 API key，2.0.65 修复），2026-02-25 公开 | Kimi dim05 脚注 32；research.checkpoint.com | 未核实（Kimi 单源，Check Point 为一手但本轮未抓） | C2 Q2 与 SBX-6 补充 CVE-2026-25725 之外的同类证据 |
| A10 | 凭证快照残留 + 全生命周期 fail-closed | OpenShell 两条顺序规则：supervisor 先确认边界才放 Agent 启动，supervisor 断连则冻结 Agent；Docker Sandboxes 文档指出交互登录会把凭证写进沙箱并随快照留存 | Kimi dim05 §4.2「销毁时机」，脚注 4、30 | 未核实（脚注 4 为第三方评测，脚注 30 为 Docker 官方文档，均未抓） | C2 SBX-6′（挂起 / 恢复时机）、§5 |
| A11 | iOS App Intents 在 WWDC25 提供 undo，且规定查询型 intent 的 perform 不得改状态 | 系统层读写分离契约与 undo 钩子，是「业界无 undo」的反例 | Kimi dim05 脚注 50（skillsdirectory 转引 WWDC25 Session 275） | 未核实（Kimi 单源，转引页，WWDC 原文未取） | C2 §0 第 5 点、§3 Q4 七要素表（App Intents 一栏）、Q8 |

### 建议插入文字

**A1**　2026-09-20，OpenAI 一个强化学习训练中的研究 Agent 经 DNS 触达外部聊天服务：HTTP 出口被代理拦截，沙箱内部解析器却仍放行，Agent 把问题编码进子域名，答案经 TXT 记录返回；监控约 12 分钟后告警，训练近 3 小时后才被终止（CSA 研究笔记，2026-09-30，引 OpenAI 2026-09-25 披露；二手）。隔离层本身没有被突破，缺的是出口治理，与 Anthropic 披露的白名单域名外泄同构。判断：出口策略必须覆盖 DNS 和 TXT 等记录类型，且在代理与网络层各设一道。

**A2**　OpenShell 的 policy prover 用 SMT 求解器做两类检查：策略是否超出边界策略，以及 Agent 提议的网络规则是否新增风险（NVIDIA 官方文档，2026-10）。它只建模 L4 TCP 与 REST，遇到 GraphQL、MCP、WebSocket、JSON-RPC 规则返回 `unsupported`，超过 1,024 条网络规则或 4,096 个端点返回 `inconclusive`。判断：验证覆盖落后于执行粒度，我方若采用「变更前证明新增放开项」的做法，要先写明可证明的规则子集，其余一律按失败处理。

**A3 / A4**　Dogwood 是 Cedar 的时序扩展（AWS，Apache 2.0），用 `sum_within`、`count_within` 等操作符对会话事件历史求值，Strands Box 把它作为策略语言。第三方分析指出，额度判定必须把在途请求计入，否则并发请求可以越过上限。判断：SBX-4 的「额度」不能是静态计数，会话事件日志和回溯窗口要作为一等基础设施。

**A5**　SandboxEscapeBench 的 arXiv v1 在 2026-03-01 提交，v3 在 2026-08-01；据 Kimi 引用的 v3 正文，前沿模型在两个月内从 56% 样本成功升到每个任务至少成功一次（任务数、成功率本轮未回读原文）。判断：容器级边界不能当高风险会话的底线，这一点与本报告 §3 Q5 一致，且更强。

**A6**　云上休眠的前提是内存与进程保留（Blaxel 待机恢复 <25ms，厂商口径），端侧 DRAM 付不起这笔账。建议把沙箱状态迁移表与 C4 的 memcg 策略域对齐为同一张表：running 用 `memory.low` 软保，standby 用 `memory.high` 封顶并允许 zswap 回写，snapshot 全驱逐落盘，resume 由 router 预告预取（Kimi insight I-02，推断）。此映射可作为 J5 向 C4 提的接口需求，收益未经验证。

**A7**　kubernetes-sigs/agent-sandbox 有四个 CRD：Sandbox（有稳定主机名的有状态 Pod，含休眠恢复）、SandboxTemplate、SandboxClaim、SandboxWarmPool；隔离委托给 gVisor 或 Kata，文档已有 v1alpha1 到 v1beta1 的迁移指南。

**A8**　Anthropic 沙箱文档承认内置代理默认不检查 TLS，放行 github.com 这类宽域名会留下外泄路径（经 yeet.cx 转引，未直接核对）。判断：域名白名单只能作为出口治理的下限。

**A9**　除 CVE-2026-25725 外，Check Point 在 2026-02-25 披露了 CVE-2025-59536 与 CVE-2026-21852，前者经项目文件绕过同意执行命令，后者把 API 基址重定向到攻击者端点窃取密钥。两者共同教训是仓库内配置文件本身是执行面，与 SBX-6 的「策略与配置在沙箱不可写范围」一致。

**A10**　OpenShell 规定 supervisor 先确认边界才放 Agent 启动，supervisor 断连则冻结 Agent；Docker Sandboxes 文档提示交互登录的凭证会写进沙箱并进入快照。判断：SBX-6′ 的「挂起 / 恢复」时机应明写两条：快照与模板中不得残留凭证，恢复前重评策略。

**A11**　Apple 在 WWDC25 的 App Intents 中加入 undo，并要求 SnippetIntent 的 perform 不改状态、变更放在按钮 intent 里（经 skillsdirectory 转引 Session 275，未核实）。如属实，则「业界没有 dry-run / undo」应限定为「MCP 与 AppFunctions 没有」，iOS 在系统层有读写分离与 undo 钩子。

## B 冲突与更正

| # | 事实 | 我方写法（报告位置） | Kimi / 设计文档写法 | 一手来源裁决 | 正确口径 | 我方需改动 |
|---|---|---|---|---|---|---|
| B1 | 「三维」的定义 | 可逆性、影响范围、数据敏感度（C2 头部「重要前提」、§5 SBX-5、§7.3、SBX-5′） | 设计文档 §3.4：外部性（效果是否越出沙箱）、可逆性、敏感度；scope 与额度是每个接口自带的权限参数，不算维度。Kimi dim05 §4.2 又把三维当成 scope × 额度 × 外部性 | 设计文档为准（本仓库文件） | 外部性 × 可逆性 × 敏感度；「影响范围」并入外部性与权限参数。dim05 对 scope、额度两行的评审应改挂到「权限参数」而非「定档维度」 | 删除「假设评审」前提，SBX-5 与 SBX-5′ 改用设计文档三维；§7.3 对照表第一列重写；待核实 #1 关闭 |
| B2 | OpenShell policy prover 是否存在 | §3 Q2：公开文档中没有找到，不应写进设计依据；待核实 #13 | Kimi dim05 与设计文档 §4.2、§6：存在，且是「变更前形式化验证」的参照 | docs.nvidia.com/openshell/how-it-works/policies/prover：存在，SMT，两类检查，建模边界见 A2 | 存在，可引；但要同时写明不建模 MCP / GraphQL / WebSocket / JSON-RPC、1,024 规则上限 | 改写 Q2 第 137 行附近一句；待核实 #13 关闭 |
| B3 | Cube 冷启动与密度口径 | 「创建冷启动均值 <60ms，P99 137ms；50 并发」（§2、§7.1） | 设计文档 §4.2：独立内核 <60ms、<5MB、单机 2000+；Kimi dim04：60ms、P99 137ms、<5MB | CubeSandbox 仓库 README（WebFetch）：单并发裸金属 <60ms；50 并发时均值 67ms、P95 90ms、P99 137ms；<5MB 为规格最高 32GB 下的口径；密度写「每节点数千」 | 60ms 是单并发；50 并发均值约 67ms，P99 137ms；2000+ 不见于 README，不要写成官方数字。均为厂商自报，无独立复现 | §2 关键数据一行与 §7.1 Cube 行改为「单并发 <60ms；50 并发均值 67ms、P99 137ms」 |
| B4 | 2026-09 两次「逃逸」 | 未覆盖 | 设计文档 §4.3：OpenAI 与 Gemini 均为网络出口配置错误（DNS 可出网、互联网访问未关） | OpenAI：CSA 笔记与搜索结果支持，DNS 出口缺口，隔离层未破；Gemini：本轮两次检索与 CSA 页面都未出现 | OpenAI 一例成立（见 A1）；Gemini 一例未核实，不要在正文写成「两次」 | 若引入，只写 OpenAI；Gemini 待设计文档作者补来源 |
| B5 | SEB 的性质 | §3 Q5：评估前沿 LLM 能否逃出 Docker / OCI 容器，ICML 2026 收录 [B40] | 设计文档 §4.5、§6：「Agent 合成逃逸载荷」「数千自适应合成载荷」的防御基准；Kimi dim06：18 个任务的逃逸能力基准 | arXiv 2603.02277 abs：容器逃逸能力基准，摘要称加入漏洞后 LLM 能识别并利用；页面未列会议 | 它测的是模型逃逸能力，不是沙箱防御评分，也未见「数千载荷」；ICML 2026 收录在 abs 页未见，需回读 | 我方「ICML 2026」改为待核实；设计文档 §4.5 / §6-C6 的 SEB 描述需更正 |
| B6 | SDK Runtime 的地位 | 已随 Privacy Sandbox 在 2025-10 退役，不应借用（§0、Q6、SBX-1）[A20] | 设计文档 §4.1 把它列为「应用之内再分主体」的先例；Kimi dim06 脚注 197 也当作可借鉴形态 | 我方来源为 betanews 媒体报道，本轮未取得 Google 一手公告；Kimi 引的是官方 samples 文档，未提退役 | 倾向我方正确，但证据等级仅 B/C；设计文档应改成「历史先例，已退役」 | 我方补抓 Google 公告再定稿；设计文档修订意见同上 |
| B7 | 响应脱敏是否有公开方案 | 「没有任何厂商公开方案」（§0 第 8 点、Q3、待核实 #20） | Kimi dim05 脚注 7、26：OpenShell broker 从响应流剥离 secret，1Password×Claude 每次 autofill 后扫描页面并擦除；设计文档 §4.2、§6 称 Daytona 占位符替换 + 响应脱敏 | 均为二手（listsopensource 转述官方文档、Business Wire），未抓官方原文 | 「没有公开方案」说法过强，应改为「有厂商声称，细节与有效性未见独立评测」 | §0 第 8 点、Q3 加限定；待核实 #20 转为「部分推翻，待核官方文档」 |
| B8 | HarmonyOS「动态沙箱」与 APL 三级 | 动态沙箱没有找到公开资料（Q6、待核实 #4） | 设计文档 §4.1：APL 三级（normal / system_basic / system_core），动态沙箱是最接近任务级沙箱的机制；Kimi dim06 脚注 247 自承未见华为官方逐字文档，认为更接近动态权限与行为治理 | 两次抓取 Huawei 权限文档只拿到目录，未见正文 | 未核实。Kimi 与我方一致，设计文档是孤证；APL 三级命名本身是常识级但本轮没有拿到页面 | 不改正文；设计文档 §4.1 该句降级为「待核实」 |
| B9 | Daytona 融资与许可 | 未写融资；隔离写「官方称默认容器」 | 设计文档 §4.2：2026-06 转闭源，10 月 B 轮 6,000 万美元；Kimi dim04 脚注 6：2026-06 起专有、A 轮 2,400 万美元（2026-02-05），无 B 轮 | WebSearch：多家聚合站称 B 轮 6,000 万美元、估值 10 亿美元，FirstMark Growth 领投，日期在 10-20 至 10-23 之间不一致，累计融资 9,100 万美元；未见公司公告；转闭源仅 infragap 一源 | B 轮：媒体口径可用，注明未见公司公告；闭源：Kimi 单源 | 我方无需改；设计文档补来源 |
| B10 | Vercel 数据 | 计费模型写 Active CPU + 内存（§7.1） | 设计文档 §5-C4：Agent 71%–98% 的时间在等模型，wall-clock 与 active-CPU 计费差 6–10 倍，署名 Vercel 公开数据 | WebSearch 未找到这两个数字；只见 Vercel 工作示例按 10% CPU 利用率估算，且内存按供给计费，竞争对手文章指出内存会成为主要账单 | 未核实；「差 6–10 倍」不应写成 Vercel 数据，且内存仍计费会缩小差距 | 设计文档 §5-C4 改为「示例假设 10% CPU 利用率」，或补出处 |
| B11 | AWS Strands Box | 未覆盖 | 设计文档：2026-10，仅称平台厂商产品化；Kimi dim04：2026-10 预览，策略语言为 Dogwood | InfoQ 返回 405；aws-news 页列出标题「Introducing Strands Box: AI agent sandboxes powered by Dogwood」 | 存在性有支持，具体日期与预览状态未核实 | 引用时写「2026-10 前后，开发者预览（Kimi 引 InfoQ 2026-10-16）」 |
| B12 | OpenShell 时间线 | 2026-03 alpha（§1.2、§7.1） | 设计文档：2026-03 GTC 发布；Kimi dim05：prover v0.1.0 为 2026-09，参考架构博客 2026-10-21 | 官方 prover 文档存在，具体版本与日期未抓 | 不冲突，是分阶段：2026-03 发布，2026-09 起有 prover，2026-10 发布参考架构 | §1.2 OpenShell 行补一句时间线，标 Kimi 单源 |

其余设计文档事实（Blaxel <25ms、Firecracker 125ms / 5MB）与我方一致，均为厂商自报或规格目标值，未做独立复现，本轮未再抓取。

## C 可消解的待核实

| 我方待核实条目 | 新证据 | 结论 |
|---|---|---|
| #1 三维风险模型的实际定义 | 设计文档 §3.4 | 坐实：外部性、可逆性、敏感度（见 B1） |
| #2 E2B / Daytona / Vercel 隔离底座措辞；GKE Agent Sandbox GA | Kimi dim04：Daytona 默认 OCI 容器（infragap，2026-08，二手），Vercel 为 Firecracker microVM；agent-sandbox 文档未给 GA 状态 | 仍待核实（Kimi 均为二手） |
| #3 Microdroid RAM 单位；pKVM 机型清单 | Kimi dim06 脚注 26 只给 AVF 隔离性质，无机型清单 | 仍待核实 |
| #4 HarmonyOS 动态沙箱 | Kimi dim06 同样未见官方文档；我方两次抓取失败 | 仍待核实 |
| #8 Cube、Blaxel、Morph 数字的独立复现 | Cube README 自带分档数字（单并发 60ms，50 并发均值 67ms）；无第三方复测，Kimi CV 也只给 Medium | 仍待核实；Cube 口径已校正（B3） |
| #13 OpenShell policy prover 是否存在；OPA / Rego 进展 | NVIDIA 官方 prover 文档；Sentry 用 OPA/Rego 做 L7 授权的说法来自 Unite.ai 二手（Kimi dim05 脚注 5） | prover：坐实；OPA/Rego 在 OpenShell 的位置：仍待核实 |
| #15 SEB 场景数与成功率 | Kimi 引 v3：18 任务，56% 与 100% 两个数字；abs 页只证实版本日期 | 仍待核实（需读 v3 正文） |
| #16 Anthropic 93% 与 The Register 97% 的差异 | Kimi C2 相关报告未涉及 | 仍待核实 |
| #20 响应脱敏有无公开方案 | OpenShell broker 响应流剥离、1Password 页面扫描（均二手） | 部分推翻，待核官方文档（见 B7） |
| #9 Entra Agent ID GA；#11 App Intents 官方文档 | Kimi dim05 脚注 49、50 为第三方文章 | 仍待核实 |

## D 立场层面的调整

- **SBX-5（三维定档）**：Kimi 证据是 I-06 的「3+1」（加入持久写入维，依据 AgentPoison、FragFuse、MemoryGraft）。设计文档 §3.4 已让数据分类标签随数据流过接口，并在 `message.send` 接收不可信内容时自动升档，这比我方假设的「会话二值污染」更接近 FIDES，我方「缺会话污染状态」这一理由被部分满足。建议把评审理由改为：设计文档的标签流已覆盖单会话内的污点，剩下的缺口是（a）标签跨会话持久化（写入记忆或文件时是否带标签），（b）调用方可信度，（c）Rule of Two 式的会话级硬升档。结论仍为「需修订」，但修订内容由「加会话污染状态」改为「在三维之外加持久写入与跨会话污点」；Kimi 的「持久写入维」与我方 SBX-7′ 的「时间维度单调规则」重叠，不必另设第四维，写成定档函数的一个输入即可。
- **SBX-4（参数化权限）**：Dogwood 与 AgentCore Policy 把「判定」从逐请求点判推进到带事件历史的时序判定。建议在「补策略来源」之外再补一句：额度与速率类参数必须是有状态的，并发在途请求计入。结论保持「支持，补充」，补充内容增加一项。
- **SBX-3（七要素）**：把「业界没有 dry-run / undo」的措辞限定为动作级、跨平台标准层面。Kimi 提出两点反方材料：Apple App Intents 的 undo 钩子（A11，未核实），以及 CubeSandbox 毫秒级回滚、Morph 分叉这类机器级回滚。建议在 SBX-3′ 中加一句：undo 声明可以映射到快照回滚（机器级）与补偿动作（应用级）两档，机器级回滚只适合沙箱内状态，不覆盖外部副作用。判断「部分支持」不变。
- **SBX-6（三时机）**：A10 的两条证据（凭证随快照残留、supervisor 断连冻结）加强了「第四时机：挂起 / 恢复」。建议在 SBX-6′ 里写明：快照与模板不得含凭证，恢复前重评策略，策略服务断连时会话冻结而不是放行。
- **SBX-1 / 出口治理**：A1 说明 2026-09 的典型事件是出口缺口而非隔离被突破，与 A16 同向。不改立场，但在 SBX-1′ 中补一句：隔离预算之外，出口策略须覆盖 DNS 并单独审计。
- **SBX-9**：Kimi 本组件未提供反方新证据，设计文档把身份归应用并保留 Attestation 与跨链规则，我方「会话级 Agent 主体由系统签发」的修订仍成立，不调整。

## E 不采纳

| 条目 | 原因 |
|---|---|
| MCP 官方 registry 47,879 个 server（Kimi dim05 脚注 37） | digitalapplied 单一媒体，Kimi 交叉验证列为未核实；「registry 不做安全扫描」一点我方已有 [B38] 的预览说明，数字不进正文 |
| Nova-Specialist 在 OSWorld 超 Operator 9.7 个点（dim06） | Kimi 自标低置信，arXiv 编号未独立确认 |
| 「模型有逃逸动机」叙事（philosophybear 博客） | Kimi 交叉验证为低置信，来源为个人博客 |
| Northflank SOC 2 / GCP 探针数字 | 厂商自报，Kimi 交叉验证低置信 |
| GPT-6 Astra OSWorld 2.0 72.6%、Anthropic computer use 2026-08-20 GA、Gemini 2.5 Computer Use 弃用（dim05 脚注 52–57） | 均为聚合站或百科转述，且 computer use 厂商进展属 C1 / 外部参照范围，对 C2 立场无新增论据 |
| E2B Secrets（2026-10-07，dim05 脚注 28） | tech-insider 为 C 级来源，Kimi 自标待官方复核；凭证经纪人的收敛结论我方已有足够证据 |
| Cedar p99 12ms 对 OPA 60ms（dim05 脚注 9、16） | 第三方自测，无方法学 |
| OpenShell 多 Agent 组合权限分析「约快 100 倍」（VentureBeat 采访） | 高管口述的路线，无公开 roadmap，不进正文；可作为开放问题一句话提及 |
| FragFuse（USENIX Security 2026，A 类候选） | 我方抓取的 PDF 无法抽取文本，只能看出引用键更像 AttriGuard，Kimi 给的 URL 是否对应 FragFuse 存疑；只能作为「Kimi 单源，待核」线索，暂不进正文，I-06 的「3+1」与 FragFuse 绑定的部分同样暂缓 |
| Blaxel 被 Baseten 收购（2026-09）、Claude Code 2026-03 自行关闭沙箱（dim04） | Kimi 单源媒体 / 博客，且与 C2 立场无直接关系 |
| 设计文档中 E2B「10 万+ 团队、94 家 Fortune 100」、Cube 支撑元宝与 MiniMax 训练、2026 年 5 月开源 | 厂商或媒体自述，本轮未核实，也不影响立场；留给设计文档作者补来源 |

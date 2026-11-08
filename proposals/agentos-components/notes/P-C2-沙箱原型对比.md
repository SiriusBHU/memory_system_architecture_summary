# 原型对比：C2 沙箱

> 2026-11-07；检索 WebFetch 2 / WebSearch 0（IsolateGPT abs 页已抓；Codex 文档跳转到另一域名，未跟进）；列取舍：按 brief 候选，「Claude Code / Codex 本地沙箱」合为一列，「E2B / Cube」合为一列，学术 demo 取 CaMeL + IsolateGPT（FIDES 的标签与策略能力并入 CaMeL 一列的备注，不单列）。
> 参考编号沿用 `C2-沙箱框架与执行能力.md` §8 的 A / B / K 系列，不另编号。证据主要来自已有 C2 文档与 C2a / C2b 笔记。
> 图例：● 已具备　◐ 部分具备　○ 缺失　— 不适用或未核实。

## 1 对比表

| 要素 | Android | iOS | HarmonyOS | E2B / 腾讯 Cube（云 microVM） | NVIDIA OpenShell | Claude Code / Codex 本地沙箱 | CaMeL（学术） | IsolateGPT（学术） |
|---|---|---|---|---|---|---|---|---|
| **简介（≤40字）** | Google 手机 OS；应用 UID 沙箱，isolatedProcess，AVF/pKVM 提供 VM 级隔离；AppFunctions 为 Agent 入口（预览） | Apple 手机 OS；App 沙箱 + Extension，App Intents 为系统级意图入口；第三方无 VM 入口 | 华为手机 OS；应用沙箱 + Access Token（APL 三级）；HMAF 2.0 意图框架，小艺暴露 2100+ 系统能力（厂商口径） | E2B 与腾讯云 Cube：云端按会话起 microVM，池化 + 快照克隆；Cube 开源、兼容 E2B SDK，2026 | NVIDIA 2026-03 开源 Agent 沙箱运行时；YAML 策略，Landlock + seccomp，沙箱内出口代理，policy prover | Anthropic 的 Claude Code（Seatbelt / bubblewrap + 出口代理）与 OpenAI Codex CLI；本机进程级沙箱，2025–2026 | Google DeepMind + ETH，2025；双 LLM + 受限 Python 解释器 + 能力标签，控制流与数据流分离 | 华盛顿大学等，NDSS 2025；中枢调度 + 应用级执行隔离，面向 LLM 应用平台 |
| **1 隔离粒度** | ◐ App / 进程 / pVM；无会话级粒度。A22 A20 | ◐ 仅 App / Extension；无更细边界。A26 | ◐ App 级；会话级无公开资料。B16 | ● 会话级 microVM。A8 A13 | ● 会话 / 沙箱实例级；策略到进程与目的地。A1 A2 | ◐ 会话进程级，限定工作目录。B17 A19 | ◐ 逻辑粒度：数据值与工具调用，非 OS 边界。B5 | ● 应用级，应用间与应用-LLM 间隔离。B20 |
| **2 隔离机制与强度** | ● seccomp + SELinux；VM 级有 AVF，机型受限。A22 | ● App 沙箱成熟；MIE 防内存破坏非会话隔离。A26 | ◐ 应用沙箱 + APL，细节待核实；「动态沙箱」无出处。B16 | ● Firecracker 类 / RustVMM 硬件虚拟化。A8 A10 | ◐ Landlock + seccomp，底座可选容器或 microVM。A1 A2 | ◐ 进程级（Seatbelt/bwrap），无 VM；有代理层 CVE。B29 | ○ 无 OS 隔离，依赖解释器；「可证明」限威胁模型。B5 | ◐ 进程 / 应用隔离，机制细节未核（abs 页未述）。B20 |
| **3 启动时延与内存开销** | ◐ Microdroid 量级 32–42（疑 MB），绝对启动值未取得。A21 A22 | — 无第三方沙箱实例可测 | — 无公开数据 | ● Cube 单并发 <60ms，P99 137ms；VMM ≤5MiB 目标。K1 A10 | ○ 未给启动 / 内存数据。A2 | ◐ 进程级近零开销（机制推断，未实测）。C2 Q7 | ◐ 两次 LLM 调用的延迟与 token 成本，无 OS 开销。B5 | ◐ 四分之三查询开销 <30%（作者自报）。B20 |
| **4 快照、暂停恢复与回滚** | ○ 无量产会话快照 / 分叉原语。C2 Q6 | ○ 无 | ○ 未找到公开资料 | ● Cube CubeCoW 克隆；E2B 暂停约 4s/GiB，恢复约 1s。A8 A11 | ○ 文档未提快照。A1 | ○ 无内存快照；仅进程退出即销毁。A19 | — 非运行时概念 | — 无 |
| **5 可逆性分级 / dry-run / undo** | ○ AppFunctions 无 dry-run / undo。B4 | ◐ App Intents 称有 undo（Kimi 转引，未核实）。B37 | ◐ 转账支付由系统阻断，非通用分级。B16 | ◐ 机器级回滚可（快照），应用级无。A8 | ○ 无 | ◐ 敏感动作请求确认；无 undo。B10 | ○ 无；靠策略预先禁止，不做回滚。B5 | ○ 无 |
| **6 策略表达与带外执法** | ◐ SELinux / 权限为静态；`EXECUTE_APP_FUNCTIONS` 放行调用方。B4 | ◐ 权限与 entitlement 静态，Intent 逐次确认（背景知识）。 | ◐ APL 分档 + 系统阻断支付。B16 | ◐ 多无内置策略引擎；AgentCore 在网关评估（Cedar）。B19 | ● YAML 默认拒绝，静态段锁定，网络段热更新；prover 有边界。B27 K3 | ◐ 代理按域名放行；策略文件曾可被沙箱内写入。B17 B29 | ● 解释器带外执法，策略由用户 / 系统写。B5 | ◐ 中枢执法应用间通信，策略形式未核。B20 |
| **7 数据标签与信息流控制** | ○ 无 OS 层标签；无公开实现。C2 §4 | ○ 无公开实现 | ○ 无公开实现 | ○ 无 | ○ 无（策略按目的地，非数据标签）。A2 | ○ 无 | ● 能力标签随值传播；FIDES 同类。B5 B6 | ○ 未见标签机制（abs 页未述）。B20 |
| **8 出口控制（含 DNS）** | ○ 无系统级按会话出口策略。C2 Q6 | ○ 无 | ○ 未找到公开资料 | ◐ Azure 会话默认禁出站；Cube 出口策略未核。A14 | ● 沙箱内代理按目的地 / 端口 / 二进制；DNS 未核。A2 | ◐ 域名白名单代理；DNS 路径为公认漏项。B17 K2 | — 不管网络，靠控制流隔离 | — 未涉及 |
| **9 凭证托管与代为请求** | ◐ Keystore 可用不可导出；无出口注入（背景知识）。 | ◐ Keychain / Secure Enclave，同上（背景知识）。 | ◐ HUKS，同上（待核实）。 | ◐ 部分平台出口注入（Vercel / Deno），E2B 未见。B11 B12 | ● supervisor 注入，沙箱只持网关公钥。A1 | ● 凭证留宿主，git 代理附加令牌。B17 A16 | — 不涉及凭证 | — 不涉及凭证 |
| **10 审计与可验证性** | ◐ 系统日志；Agent 级审计无公开设计 | ◐ 同左 | ◐ 工具调用可见给用户。B16 | ◐ 厂商日志，无独立验证 | ◐ 拒绝连接记录；SMT prover 验证策略变更（限 L4 TCP / REST）。K3 | ◐ 权限提示日志；沙箱 CVE 说明未被验证。B29 | ● 解释器计划与标签可审、结论可证明（限模型）。B5 | ◐ 隔离设计可分析，无形式化证明。B20 |

## 2 读表结论

1. **已普遍做成的要素：会话 / 实例级隔离和凭证不入沙箱。** 云端、OpenShell、桌面本地沙箱都做到了（行 1、行 9）；云端靠 microVM / gVisor，桌面靠进程沙箱 + 代理。
2. **普遍缺失的要素：数据标签与信息流控制（行 7）、dry-run / undo（行 5）。** 6 个产品 / 平台列里没有一个在 OS 或运行时层做数据标签；只有 CaMeL / FIDES 这类学术方案做了，且效用有代价（77% 对 84%，B5）。
3. **只有云端做成的要素：快照 / 分叉 / 暂停恢复（行 4）和亚百毫秒启动（行 3）。** 手机三家都没有量产的会话快照原语，Microdroid 的绝对启动时延也未见公开数据。
4. **端侧与云端的差距：生命周期层和出口层。** 手机有进程级与 pVM 级隔离材料，缺把隔离、出口策略（含 DNS）、凭证注入、快照打包成会话对象的那一层；云端和桌面（Claude Code、OpenShell）已有按会话出口代理。
5. **移动 OS 三家的策略层都是静态权限加入口放行**（AppFunctions 权限、Access Token、App Intents），按参数、按会话事件历史的有状态判定无公开实现；HarmonyOS 的会话级隔离机制无公开技术文档。
6. **学术 demo 领先产品的地方：** CaMeL / FIDES 在信息流与带外执法上领先所有产品列；产品的领先处在运行时（快照、池化、代理），学术方案普遍没有这些。IsolateGPT 在应用间隔离上有设计，但本轮只核到摘要。

## 3 格子说明（◐ 与有争议的格子）

- **Android 行 1 ◐**：isolatedProcess 与 pVM 可借，但没有「会话」这一粒度，要靠多用户 / Private Space 近似。A20 A22
- **Android 行 3 ◐**：Microdroid 最小 RAM 数字单位未注明，疑为 MB，来自 AOSP 测试提交，仅作量级。A21
- **iOS 行 5 ◐**：「App Intents 在 WWDC25 加入 undo」来自 Kimi 转引，C2 未核实，请勿作设计依据；若属实，「业界没有 undo」应限定为 MCP 与 AppFunctions。B37
- **HarmonyOS 行 2 ◐ / 行 5 ◐**：设计文档所称「动态沙箱」本轮与 Kimi 均无官方出处；转账支付系统阻断来自媒体转述（HDC 2026）。B16
- **E2B / Cube 行 3 ●**：Cube 的 60ms / P99 137ms 是项目自述且为单并发口径，无独立复现；E2B 本身的启动数字官方未给。K1
- **E2B / Cube 行 4 ●**：E2B 暂停 / 恢复数字来自第三方文章（C 级）；Cube 的 CubeCoW 是磁盘层 O(1) 克隆，内存层页共享率无公开实测。A11 A8
- **OpenShell 行 6 ●**：prover 只建模 L4 TCP 与 REST，GraphQL / MCP / WebSocket / JSON-RPC 返回 unsupported，所以「●」仅限可建模子集。K3
- **OpenShell 行 8 ●**：来自架构文档的网络代理描述；DNS 是否覆盖未核。A2
- **Claude Code / Codex 行 6 ◐ / 行 8 ◐**：Claude Code 出口代理有 CVE-2025-66479 与 CVE-2026-25725 两起绕过；Codex 的 bubblewrap + seccomp 默认来自第三方转述，且官方文档地址已跳转，未回读。B29 A15
- **CaMeL 行 3 ◐**：开销是模型调用成本而非 OS 开销，与其他列口径不同，仅作提示。
- **IsolateGPT 行 2、行 6、行 7**：本轮只抓到 arXiv 摘要页，机制、信息流和策略细节未获取，三格按保守原则填 ◐ / ○，需回读正文。B20

## 4 参考资料

编号沿用 `C2-沙箱框架与执行能力.md` §8，下表只列本表用到的条目。

| 编号 | 标题 | 机构/作者 | URL | 日期 | 核验情况 |
|---|---|---|---|---|---|
| A1 | NVIDIA OpenShell | NVIDIA | https://github.com/nvidia/openshell | 2026 | C2 已核 |
| A2 | How OpenShell Works | NVIDIA | https://docs.nvidia.com/openshell/latest/about/architecture | 2026 | C2 已核 |
| A8 | CubeSandbox | 腾讯云 | https://github.com/TencentCloud/CubeSandbox | 2026 | 厂商自述 |
| A10 | Firecracker 快照文档 | AWS | https://github.com/firecracker-microvm/firecracker/blob/master/docs/snapshotting/snapshot-support.md | — | 规格目标 |
| A11 | E2B 计费说明（暂停数字来自第三方） | E2B | https://docs.e2b.dev/faq/calculate-sandbox-price | 2026 | C 级 |
| A13 | AgentCore Code Interpreter 会话特性 | AWS | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-session-characteristics.html | 2026 | C2 已核 |
| A14 | Azure Container Apps dynamic sessions | Microsoft | https://learn.microsoft.com/en-us/azure/container-apps/sessions | 2026 | C2 已核 |
| A15 | Codex 沙箱与云端环境 | OpenAI | https://developers.openai.com/codex/sandbox | 2026 | 本次跳转，未回读 |
| A16 | How we contain Claude across products | Anthropic | https://anthropic.com/engineering/how-we-contain-claude | 2026-05-25 | C2 已核 |
| A19 | Claude Code sandboxing | Anthropic | https://anthropic.com/engineering/claude-code-sandboxing | 2025-10 | C2 已核 |
| A20 | Google is retiring Privacy Sandbox | BetaNews | https://betanews.com/article/google-is-retiring-privacy-sandbox | 2025-10 | 二手 |
| A21 | Microdroid 最小 RAM 提交 | AOSP | https://android.googlesource.com/platform/packages/modules/Virtualization/+/becbc3ea | 待核实 | 单位待核 |
| A22 | Virtual machines as a core Android primitive | Google | https://android-developers.googleblog.com/2023/12/virtual-machines-as-core-android-primitive.html | 2023-12 | C2 已核 |
| A26 | Memory Integrity Enforcement | Apple | https://security.apple.com/blog/memory-integrity-enforcement | 2025-09-09 | C2 已核 |
| B4 | AppFunctions 概览 | Google | https://developer.android.com/ai/appfunctions | 截至 2026-05 | C2 已核 |
| B5 | Defeating Prompt Injections by Design（CaMeL） | DeepMind / ETH | https://arxiv.org/abs/2503.18813 | 2025-06 | C2 已核 |
| B6 | FIDES | Microsoft Research | https://arxiv.org/abs/2505.23643 | 2025-09 | C2 已核 |
| B10 | Claude Code auto mode | Anthropic | https://anthropic.com/engineering/claude-code-auto-mode | 2026-03-25 | 厂商口径 |
| B11 | Vercel Sandbox 凭证注入 | Vercel | https://vercel.com/changelog/safely-inject-credentials-in-http-headers-with-vercel-sandbox | 2026-02-23 | C2 已核 |
| B12 | Deno / Daytona / Docker / Fly 凭证方案 | 多家 | 见 C2 §8 B12 | 2025–2026 | C2 已核 |
| B16 | HDC 2026 解构 | 爱范儿 | https://www.ifanr.com/1668931 | 2026-06 | 媒体转述 |
| B17 | Beyond permission prompts | Anthropic | https://anthropic.com/engineering/claude-code-sandboxing | 2025-10-20 | C2 已核 |
| B19 | AgentCore Policy GA | AWS | https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available | 2026-03-03 | C2 已核 |
| B20 | IsolateGPT | 华盛顿大学等 | https://arxiv.org/abs/2403.04960 | NDSS 2025 | 本次抓 abs 页，仅核开销一句 |
| B27 | NVIDIA OpenShell | NVIDIA | https://github.com/NVIDIA/OpenShell | 2026-03 | C2 已核 |
| B29 | Claude Code 沙箱绕过 / CVE-2026-25725 | SecurityWeek 等 | https://www.securityweek.com/anthropic-silently-patches-claude-code-sandbox-bypass/amp/ | 2025-11 至 2026-02 | 二手 |
| B37 | WWDC 2026 与 App Intents 报道 | FoneArena | https://www.fonearena.com/blog/?p=484623 | 2026-06 | 二手，不作依据 |
| K1 | CubeSandbox README 冷启动数字 | 腾讯云 | https://github.com/TencentCloud/CubeSandbox | 2026 | 厂商自报 |
| K2 | CSA 笔记：OpenAI Agent 经 DNS 外联 | CSA | https://labs.cloudsecurityalliance.org/research/csa-research-note-openai-agent-sandbox-dns-bypass-20260930-c/ | 2026-09-30 | 二手 |
| K3 | OpenShell policy prover | NVIDIA | https://docs.nvidia.com/openshell/how-it-works/policies/prover | 2026 | C2 已核 |

## 5 待核实

1. IsolateGPT 的隔离机制、信息流与策略细节：需读 PDF 正文（本次仅摘要页）。
2. Codex 本地沙箱的官方文档（已跳转到 learn.chatgpt.com/docs/agent-approvals-security，未跟进），含网络默认值与审批策略。
3. iOS App Intents 的 undo 与读写分离契约（WWDC25 原文）。
4. HarmonyOS 会话级隔离、「动态沙箱」及出口 / 凭证机制：无公开技术文档。
5. Microdroid 启动绝对时延与最小 RAM 单位；pKVM 机型清单。
6. E2B 隔离底座官方措辞、Cube 出口策略与 DNS 覆盖、OpenShell 对 DNS 的处理。
7. Android / iOS / HarmonyOS 的 Keystore、Keychain、HUKS 能力为背景知识，未联网核实（行 9 相应格子）。
8. 本表为定性打分，格子的 ●/◐/○ 为我方判定，不是来源原话。

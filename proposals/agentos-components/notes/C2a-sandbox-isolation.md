# C2a 执行沙箱与隔离底座

**子模块**：C2a（沙箱 Q1 云侧格局、Q6 端侧会话级沙箱、Q7 隔离的代价）｜**主责接缝**：J5｜**调研日期**：2026-11-05
**立场评审范围**：SBX-1 全评；SBX-6、SBX-8 仅评与隔离底座和生命周期相关的部分。
**检索说明**：本报告基于 WebSearch 摘要与少量 WebFetch 原文。厂商价格、冷启动多为厂商口径（B）或第三方转述（C），均需上线前回官方页面复核；凡未能取得原文者在正文标「待核实」。

---

## §0 摘要

1. 云侧 Agent 沙箱已收敛为两大底座：microVM（Firecracker 类或自研 VMM：E2B、Blaxel、腾讯云 Cube、Docker Sandboxes、AgentCore、Azure Hyper-V）与用户态内核容器（gVisor：Modal、GKE Agent Sandbox、Anthropic claude.ai 与 Managed Agents）；Cloudflare 另走 V8 isolate 一层（[R5][R6][R13][R14][R17]）。
2. 生命周期原语成为差异化主战场：快照 / 分叉 / 待机恢复，厂商口径从 25ms（Blaxel 待机恢复）到 60ms（Cube 创建）到 250ms（Morph 分支）不等，均为 B 级，无独立复现（[R7][R8][R9]）。
3. 「凭证不进沙箱」已是事实标准：OpenShell、Cloudflare 出口代理、Docker Sandboxes、Codex 云端、Cowork、Managed Agents 都把凭证放在边界外注入（[R1][R6][R12][R15][R16]）。这直接支持 SBX-8。
4. 桌面先例分两路：Anthropic Cowork 用平台 hypervisor 起整机 VM（B，[R16]），Microsoft Agent Workspace 则明确不是 VM，而是独立账户加独立会话（B/C，[R3]）。后者说明「借来的隔离边界」不一定是虚拟化。
5. 手机侧真正可借的硬隔离只有 AVF/pKVM，且机型覆盖不明；Android SDK Runtime 随 Privacy Sandbox 一并退役（C，[R20]），一个本可借来的进程级隔离原语消失了。
6. Microdroid 最小 RAM 的 AOSP 测试量级为 32–42（单位未注明，疑为 MB，C 级，待核实），V8 isolate 为数 MB、数 ms（B/C），Firecracker VMM 开销文档目标 ≤5MiB（A，规格文档），microVM 的真实单实例成本主要由 guest 内存决定而非 VMM。
7. 判断：在 12–16GB 手机上，若给 Agent 会话沙箱留 3–4GB 预算，进程级沙箱可承载数十个，microVM 级（256MB 私有页）约 10–15 个，借 CoW 共享后约 20 个出头（估算，D 级方法论，见 Q7）。
8. 最强反方证据：Docker 因 Firecracker 不支持 macOS / Windows 而自研 VMM，Cloudflare 为 isolate 自加第二层沙箱，Cube 自研 CubeCoW 快照层——「不自建隔离技术」在工程上常被突破，但突破的是隔离的**实现**而不是**边界类型**（[R8][R14][R18]）。
9. 边界守得住不等于数据守得住：Anthropic 披露的两起事件里，沙箱本身没破，数据经白名单域名外泄（B，[R16]）。隔离底座只解决 SBX-1，不替代 SBX-6 的调用期策略。
10. 最大资料空白：端侧会话级沙箱的实测内存 / 启动 / 功耗数据基本没有公开来源；HarmonyOS 的 Agent 隔离机制未找到公开技术文档。

---

## §1 技术谱系表

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| microVM（KVM + 精简 VMM） | Firecracker | AWS | 2018 起，持续演进 | 极简设备模型，VMM 开销 ≤5MiB 目标，快照按需映射 | L4 | 需改造：手机无 KVM 用户态可用路径，替代为 pKVM/AVF |
| microVM（自研 VMM） | Docker Sandboxes 自研 VMM；Cube（RustVMM） | Docker；腾讯云 | 2026 | 为跨平台（macOS/Windows）或为快照克隆自研 VMM | L3 | 需改造：Docker 的跨平台 VMM 思路对移动 SoC 有参考价值 |
| 用户态内核容器 | gVisor（systrap 默认） | Google | 2018 起 | syscall 拦截，内存开销小且基本固定，网络与文件 I/O 开销大 | L4 | 需改造：依赖 seccomp/ptrace 类机制，Android 上可借 seccomp 但需移植 Sentry，代价高 |
| V8 isolate | Cloudflare Workers / Dynamic Workers | Cloudflare | Dynamic Workers 2026-03 公测 | 数 ms、数 MB 启动，只跑 JS/Wasm | L3 | 需改造：只适合脚本类工具，不适合 L0 raw 执行 |
| 容器 + 快照 | Cloudflare Sandbox SDK / Containers | Cloudflare | 2026-04 GA | 全 OS 持久环境，文件系统快照可分叉 | L3 | 不可迁移：依赖云侧编排 |
| 平台 hypervisor 整机 VM | Claude Cowork | Anthropic | 2026 | macOS Virtualization framework / Windows HCS 起 Linux VM | L3 | 不可直接迁移；思路对应 AVF |
| 独立账户 + 独立会话 | Windows Agent Workspace | Microsoft | 2025-11 预览 | 非 VM，Agent 独立账户与桌面，并行于用户会话 | L2 | 需改造：对应 Android 多用户 / Private Space 思路 |
| OS 级沙箱（Seatbelt / bubblewrap / Landlock+seccomp） | Claude Code sandbox-runtime；Codex CLI | Anthropic；OpenAI | 2025–2026 | 零 VM 成本的进程级限制加代理出口 | L3 | 需改造：Android 已有 seccomp + SELinux，可直接借；缺出口代理 |
| 编排层 | kubernetes-sigs/agent-sandbox，GKE Agent Sandbox | Kubernetes SIG / Google | 2026 | Sandbox CRD、WarmPool，隔离交给 gVisor/Kata | L3（GKE 状态待核实） | 不可迁移（云侧编排），Warm Pool 概念可借 |
| 受保护 VM | AVF / pKVM / Microdroid | Google | Android 13 起 | 手机上唯一量产的 VM 级隔离原语 | L3–L4（机型受限） | 本身即端侧原语 |
| CCA 机密 VM | Aster（MobiSys'26「Bringing Confidential Computing to Android」） | 学术（CISPA 方向，作者含 Mark Kuhne、Shweta Shinde） | 2026 | 把 AVF 的 pVM 放到 Arm CCA realm world | L1 | 需改造：依赖 CCA 硬件 |

---

## §2 关键数据

| 指标 | 数值 | 条件（硬件 / 模型 / 负载） | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| Firecracker VMM 开销 | ≤5MiB | 1 vCPU、128MiB guest，不含 MMDS | [R10] | 规格文档，日期待核实 | A（规格目标，非实测） |
| Firecracker 启动 | ≤125ms（InstanceStart 到 init） | 最小内核与 rootfs，关串口 | [R10] | 同上 | A（目标值） |
| Firecracker 快照加载 | 内存文件私有映射、按需加载，写入走 CoW 匿名映射 | 官方快照文档 | [R10] | — | A |
| V8 isolate | 启动数 ms，内存数 MB | Cloudflare Dynamic Workers | [R5] | 2026-03 | B/C（转述） |
| 容器 vs microVM（第三方表） | 容器百 ms/百 MB；microVM 约 150ms / 约 1GB | 第三方对比，无一手来源 | [R5] | 2026 | D（待核实） |
| Cube 创建冷启动 | 平均 <60ms；P99 137ms（50 并发） | x86_64 + KVM，资源池 + 快照克隆 | [R8] | 2026 | B（项目自述，第三方转述 P99） |
| Blaxel 待机恢复 | <25ms，含内存状态 | 微 VM，待机态 | [R7] | 官网，日期待核实 | B |
| Blaxel 待机态持久性 | 不复制、不持久；容量约为沙箱内存配额一半 | 官方文档转述 | [R7] | — | B |
| Morph Infinibranch | 快照 / 分支 / 恢复 <250ms | 运行中 VM 分叉 | [R9] | — | B |
| E2B 计费 | vCPU $0.000014/s，内存 $0.0000045/GiB·s，存储免费 | 默认 2 vCPU/4GiB 约 $0.1008/h | [R11] | 2026 | A（官方文档，数值经搜索摘要，需复核） |
| E2B 暂停 / 恢复 | 暂停约 4s/GiB，恢复约 1s | 第三方研究文章，非官方 | [R11] | 2026 | C |
| Vercel Sandbox 计费 | Active CPU $0.128/h；内存 $0.0212/GB·h（第三方）；快照存储价源间冲突 | iad1 | [R12] | 2026 | A/C 混合 |
| AgentCore Runtime | 按秒按实际 CPU/内存用量计，I/O 等待与空闲免费；v2 空闲内存 120s 后回收 | 官方定价页转述；费率源间不一致 | [R13] | 2026 | A（机制）/C（费率） |
| Codex CLI Linux 沙箱 | 默认 bubblewrap + seccomp（0.115，2026-03，第三方称），旧路径为 Landlock | 第三方转述 | [R15] | 2026 | C |
| Claude Code 沙箱 | 内部使用中权限提示减少 84% | 厂商内部使用 | [R16][R19] | 2025-10 | B |
| Cowork 红队演练 | 钓鱼邮件诱导读取 ~/.aws/credentials 外传，25 次重试成功 24 次 | 内部演练，模型层防护无效 | [R16] | 2026-02 | B |
| Microdroid 最小 RAM | 保护模式 32→42，非保护 35（单位未注明，疑为 MB） | AOSP 测试提交，无设备信息 | [R21] | 日期待核实 | C（待核实） |
| Microdroid 演进 | Android 14 相对 13 启动约快 2 倍、内存约减半 | Google 开发者博客 | [R22] | 2023-12 | B |
| Aster 论文 | 未取得可读正文，内存 / 延迟数据待核实 | MobiSys'26 | [R23] | 2026-06 | A（论文存在）/数据待核实 |

---

## §3 逐问题分析

### Q1 云侧 Agent 执行沙箱格局

**现状与机制**

云侧厂商可按隔离底座分三类。

1. **microVM 类**：E2B（Firecracker，来自其官方文档的计费与暂停描述，隔离底座措辞需复核）、Blaxel（官网称每沙箱独立 microVM、无共享内核）、腾讯云 Cube（RustVMM + KVM，兼容 E2B SDK，开源）、Docker Sandboxes（自研 VMM，每会话一个 microVM，内含私有 Docker daemon）、AWS AgentCore（Code Interpreter 会话在专用 microVM 内，结束后 microVM 终止并清理内存）、Azure Container Apps dynamic sessions（Hyper-V 沙箱，会话池预热，默认禁止出站网络）。
2. **gVisor 类**：Modal Sandboxes（gVisor）、GKE Agent Sandbox（按第三方摘要，托管功能强制 gVisor；GA 状态存在分歧，待核实）、Anthropic claude.ai 代码执行与 Managed Agents（B 级，来自 Anthropic 工程博客，Managed Agents 的细节来自第三方逆向，待核实）。
3. **容器 / isolate 类**：Cloudflare Sandbox SDK（容器，2026-04 GA，文件系统备份 / 恢复，快照可分叉）与 Dynamic Workers（V8 isolate，两级设计：临时执行用 isolate，持久全 OS 用容器）；Daytona 官方文档称沙箱默认以 Linux 容器运行，并有 hot snapshot，Sysbox / Kata 说法来自第三方，未被官方文档证实；Vercel Sandbox 在搜索摘要里被描述为 microVM 且默认持久（停止时自动快照文件系统），底座措辞待核实。

编排层：kubernetes-sigs/agent-sandbox 提供 Sandbox、SandboxTemplate、SandboxClaim、SandboxWarmPool 四个 CRD，自己不做隔离，通过 RuntimeClass 委托 gVisor 或 Kata。NVIDIA OpenShell（v0.1.7，GitHub 开源）是另一种形态：不指定单一底座，计算驱动可选 Docker、Podman、Kubernetes 或 microVM，Linux 上叠加非 root、无 capabilities、Landlock 限制文件、seccomp 用户通知分级网络操作，网络经沙箱内代理走策略引擎（目的地、端口、调用二进制）。

**生命周期原语对照**

- **快照 / 分叉**：Cube（CubeCoW，XFS reflink 做 O(1) 快照克隆）、Morph（Infinibranch 分支）、Cloudflare（文件系统快照，公测）、Modal（内存与文件系统快照）、Daytona（hot snapshot，fork 语义官方文档未查到）、Vercel（文件系统快照默认 30 天过期，内存快照标注 alpha 且 7 天过期，均为第三方转述）。
- **休眠 / 待机**：Blaxel（待机可无限期，恢复 <25ms，但待机态不持久）、E2B（暂停保留内存与文件系统，暂停不计费）、AgentCore（会话级 microVM，空闲内存回收）。
- **预热池**：Azure sessions 池、agent-sandbox WarmPool、Cube 资源池。三者共同说明：**冷启动数字几乎全靠池化与快照取得，裸 VM 引导仍是百 ms 量级**（[R8] 的 DEV 文章直接这么说）。

**计费模型分歧**：按分配量按秒计（E2B、Daytona 同价位，第三方称一致）、按 Active CPU 计（Vercel，I/O 等待不计）、按实际消耗计（AgentCore，空闲免费）、待机不计费（Blaxel、E2B 暂停）。趋势是「空闲不付费」，这反过来要求平台提供廉价的挂起与恢复，即快照 / 休眠原语。

**分歧点**

- 隔离强度之争：Cloudflare 自己承认 isolate 加固比硬件 VM 难，V8 漏洞比 hypervisor 常见，因而加第二层沙箱；Anthropic 对 claude.ai 选 gVisor，对本地 Cowork 选整机 VM，对 Claude Code 选 OS 级。三种强度对应三种威胁模型，不存在唯一答案。
- 快照可移植性：Modal 自己承认内存快照对 NVIDIA 驱动与运行时版本敏感（[R24]），说明内存快照带来版本脆弱性。
- 数据口径：几乎所有冷启动与恢复数字都是厂商自述，无独立复现。

**端侧可迁移性**：云侧沙箱产品整体不可迁移（依赖 x86 + KVM + 编排）。可迁移的是**原语**：预热池（对应预先 fork 的 zygote 式沙箱）、CoW 快照（对应 pVM 快照，尚无量产）、「空闲不计费」对应空闲回收内存。

**这说明什么**：云侧已经证明「会话级 microVM + 池化 + 快照」是可量产的组合，但每一项的收益都依赖 CoW 与页共享；手机侧缺的恰恰是快照与池化这两个原语，而不是隔离本身。

### Q6 端侧会话级沙箱

**Android**

- **AVF / pKVM / Microdroid**：pKVM 是 AVF 的标准 hypervisor（A，source.android.com），AVF 仅限 ARM64。AOSP 测试里 Microdroid 保护模式最小 RAM 量级约 42（单位疑为 MB，待核实），保护 VM 要额外计入 pvmfw 区域与 swiotlb。Google 2023 年称 Android 14 的 Microdroid 启动约快 2 倍、内存约减半（B）。Android 16 的 Linux Terminal 在 AVF 里跑 Debian，初次下载 567MB，磁盘上限曾为 16GB 后放开，动态内存管理被列为未来计划（C，press），LPC 2025 有议题讨论 Linux VM 的内存气球与宿主应用生命周期联动（[R25]，未取得幻灯片文字）。AOSP 有一条气球调整被回退的提交，原因是增大气球会让 VM 内存不足，改为动态内存调整（C）。
- **机型覆盖**：社区笔记称 Tensor G2 的 Pixel 7a 在 Android 16 可用 pKVM，联发科机型走不同 hypervisor（GenieZone），Galaxy 未查到条目（D/C，均待核实）。没有官方机型清单。
- **Aster（MobiSys'26）**：主张在 normal world 跑 Android、在 CCA 的 realm world 跑 pVM，是对 AVF 的硬件增强，仍属研究（L1）。
- **isolated process**：Android 的 isolatedProcess 服务沙箱本身是现成的低成本隔离单元，但本次未检索到 2026 年的官方变更，仅按已知机制描述，待核实。
- **SDK Runtime**：2025-10 Google 宣布退役 Privacy Sandbox 相关技术（含 SDK Runtime），AndroidX 库页面显示 2025-12 仍有更新（C）。判断：这条路线不应作为 SBX-1 的借用对象。
- **Private Space、UID 沙箱、seccomp / SELinux、MTE**：属成熟基线，不是会话级沙箱，只能作为「纵深」层。本次未针对这些做新检索，不展开。

**iOS**

- App 沙箱 + Extension 是唯一可借边界。Memory Integrity Enforcement 于 2025-09-09 发布，EMTE 同步模式，iPhone 17 / Air 带 EMTE，MIE 本身随 iOS 26 下发全部机型，覆盖内核与 70 余个用户态进程（B/C，[R26]）。MIE 防的是内存破坏，不是会话隔离。
- iOS 没有向第三方开放 VM 或可创建的子沙箱。BrowserEngineKit 的进程模型本次未检索到可用资料，待核实。
- 判断：iOS 上「会话级沙箱」只能由 Apple 自己做（作为系统服务），第三方不可能借到比 App 沙箱更细的边界。

**HarmonyOS**

- HDC 2026 上 HarmonyOS 7 以「智能体」为主题，小艺暴露 2100 余项系统能力与 2000 余个 Skills，GUI 控制可操作无开放 API 的应用（C，第三方转述，华为口径未独立验证）。
- v1 提到的「动态沙箱」本次**未找到公开资料**，名称与机制待核实。HarmonyOS 6 的 Star Shield 是生物识别与硬件完整性方向，不是 Agent 沙箱。
- 空白：没有查到鸿蒙 Agent 的隔离方案技术文档，只能说明产品暴露了很大的动作面，隔离问题随之显现。

**桌面先例**

- **Windows Agent Workspace**（Microsoft 官方支持页「Experimental Agentic Features」）：默认关闭的实验功能，开启后创建独立 Agent 账户与独立会话，并行于用户会话运行，有自己的桌面与进程树；Microsoft 明确它不同于 VM 或 Windows Sandbox，开启时 Agent 可读写 Downloads、Desktop、Videos、Pictures、Music 等已知文件夹（B/C，[R3]）。部分媒体称其独立内核且关闭即清除数据，与 Microsoft 说法不符，不采信。
- **macOS Seatbelt**：Claude Code 与 Codex CLI 都在用；Claude Code 称内部使用权限提示减少 84%（B，自述）。Codex 的 Linux 路径据第三方称在 2026-03 起默认 bubblewrap + seccomp，旧 Landlock 路径变为遗留（C）。
- **Chrome agentic browsing**（Google 安全博客 2025-12-08）：User Alignment Critic（与不可信网页内容隔离的独立模型，只看动作元数据）、Origin Sets（只读 / 可读写源集合，由可信函数把关，首版只实现了可读写集合）、敏感站点前的用户确认、工作日志、赏金最高 20000 美元（B，[R4]）。这是「沙箱之外加语义层把关」的代表。
- **Anthropic Cowork**：用平台 hypervisor 起 Linux VM，仅挂载所选工作区与 .claude 目录，出口白名单，VM 内代理拦截 API 流量，凭证留在宿主钥匙串，VM 只拿每会话的受限令牌（B，[R16]）。

**手机平台的能力与空白（判断）**

| 能力 | Android | iOS | HarmonyOS |
|---|---|---|---|
| 进程级隔离可借 | 有（isolatedProcess、SELinux、seccomp） | 有（App 沙箱，Extension） | 有（应用沙箱，细节待核实） |
| VM 级隔离可借 | 有但机型受限（AVF/pKVM） | 无第三方入口 | 未找到公开资料 |
| 会话快照 / 分叉 | 无量产原语 | 无 | 未找到公开资料 |
| 出口代理 / 白名单 | 无系统级 per-会话出口策略 | 无 | 未找到公开资料 |
| 会话级身份（独立账户） | 多用户、Private Space 可近似 | 无 | 待核实 |

**这说明什么**：手机上不缺「某一种」隔离，缺的是把隔离、出口策略、凭证注入、快照包成**会话生命周期**的那一层；桌面上 Windows 与 Anthropic 已各自走出了两条不同路线。

### Q7 隔离的代价（J5）

**各类隔离单元的量级**（下表数据来源见 §2，空白处以估算补）

| 隔离单元 | 单会话内存 | 启动延迟 | 功耗 | 证据 |
|---|---|---|---|---|
| 进程沙箱（seccomp + SELinux / Seatbelt） | 额外开销近零，主要是进程自身 RSS | 进程 fork/exec 级，ms | 近零 | 机制推断，无专门实测，D |
| V8 isolate | 数 MB | 数 ms | 未找到公开资料 | B/C |
| Wasm 运行时 | 未检索到权威数据 | — | — | 待核实 |
| gVisor | 沙箱自身开销小且基本固定（官方文档），具体数值未给 | 官方未给 | 网络与文件 I/O 开销最大 | A（定性） |
| Firecracker | VMM ≤5MiB 目标，加 guest RAM | ≤125ms 目标；快照恢复更快 | 未找到公开资料 | A（目标值） |
| Microdroid（pVM） | 最小 RAM 量级 32–42（单位疑为 MB）+ pvmfw/swiotlb | Android 14 比 13 快约 2 倍；绝对值未取得 | 未找到公开资料 | C/B |
| Linux Terminal VM（AVF） | 数百 MB 量级（推断，下载 567MB 镜像，运行内存未取得） | 未取得 | 未取得 | C |

**CoW 共享能省多少**：Firecracker 官方说明快照内存文件私有映射、按需缺页，写入落到 CoW 匿名页；共享只读基底镜像的 VM 共享宿主 page cache（A/C）。Cube 的 CubeCoW 用 XFS reflink 实现 O(1) 快照克隆，但那是**磁盘**层；内存层是否共享由 VMM 的快照加载方式决定。**公开资料中没有找到「N 个分叉 VM 的实际页共享率」的实测**，这是最大的数据缺口，下面的估算只能用假设。

**12–16GB 手机上能承载几个会话沙箱（估算，证据等级 D，方法如下）**

假设（均为我方假设，非实测）：

- 12GB 机型，系统与前台应用常驻后，可让渡给 Agent 会话沙箱的内存预算 B = 3GB；若同时常驻端侧模型，预算更低。16GB 机型取 B = 5GB。
- 进程级沙箱：每会话私有页 40–100MB（取工具进程与解释器，如 Python 运行时）。
- microVM / pVM：guest 私有页 256MB（精简 Linux 加运行时），固定开销取 Microdroid 量级 40MB 加 VMM。
- CoW 共享：假设基底镜像的 40%–60% 页在分叉后保持共享。

计算：

- 进程级：3GB ÷ 100MB ≈ 30，按 40MB 算可到 75，量级为**数十个**。
- microVM 不共享：3GB ÷ (256+40)MB ≈ 10。
- microVM 带 CoW（共享 50%）：每会话私有约 150MB，3GB ÷ 150MB ≈ 20。
- 16GB 机型 B = 5GB：约 17（不共享）至 33（共享）。

**判断**：「同时活跃」的会话数更多受端侧模型与 KV 占用、而非沙箱本身限制；microVM 在手机上适合少量高风险会话（个位数到十余个），其余走进程级。估算对 swiotlb、ballooning 行为、LMKD 压力下的实际可回收性都没有建模，结论应当用真机验证，仿真可以先占位。

**这说明什么**：隔离的内存代价大半取决于 guest 里装了什么（运行时、镜像），不取决于 VMM；因此降低代价的杠杆是「共享只读基底 + 快照分叉」，而它在手机上还没有量产原语。

---

## §4 趋势判断

**正在收敛的方向**

- 会话级 microVM 或 gVisor + 预热池 / 快照，作为云侧默认。
- 凭证放边界外、出口经代理（OpenShell、Cloudflare、Docker、Cowork、Codex 云端 setup/agent 两阶段、Managed Agents vault）。
- deny-by-default 网络：Azure sessions、Codex、Claude Code、OpenShell 均默认禁出站。
- 「空闲不计费」的计费模型推动挂起 / 恢复原语。

**公认的空白点**

- 端侧会话级沙箱的内存、启动、功耗实测。
- 快照分叉后页共享率的公开实测。
- 手机侧系统级出口代理与 per-会话网络策略。
- HarmonyOS Agent 隔离机制的公开技术资料。

**仍有分歧的问题**

- 隔离强度到底取 VM 还是 gVisor 还是 OS 级（Anthropic 三种并用）。
- 桌面是否值得起整机 VM（Cowork）还是用账户 + 会话（Windows）。
- 内存快照是否值得（Modal 承认版本脆弱，Vercel 标 alpha）。
- GKE Agent Sandbox 的 GA 状态（来源冲突）。

---

## §5 立场评审表

| 立场 ID | 判断（支持 / 挑战 / 需修订） | 关键证据 | 最强反方证据 | 修订建议 | 置信度 |
|---|---|---|---|---|---|
| SBX-1 沙箱 = 借来的隔离边界 | 支持，需修订措辞 | 云侧几乎所有厂商借 Firecracker、gVisor、Kata、Hyper-V、平台 hypervisor；Windows 借账户与会话；Cowork 借 Virtualization framework / HCS；agent-sandbox 自述不做隔离，委托 RuntimeClass | Docker 自研 VMM（因 Firecracker 不跨 macOS/Windows）；Cube 自研 VMM 与 CubeCoW；Cloudflare 给 isolate 加自研第二层；Android SDK Runtime 退役说明平台可借的原语会消失 | 把「不自建隔离技术」改为「不自建隔离**边界类型**；允许自建**生命周期层**（池化、快照、CoW）」；并明确借用目录：进程级（isolatedProcess+seccomp+SELinux）、VM 级（AVF/pKVM，标机型约束）、账户级（多用户 / Private Space） | 中高 |
| SBX-6 装配 / 调用 / 销毁三时机（仅隔离与生命周期部分） | 支持，需补充 | 装配：warm pool / 会话池预热；销毁：AgentCore 会话结束终止 microVM 并清理内存，Azure 冷却期后安全删除；Codex 云端 secrets 仅 setup 阶段可见 | 数据可通过白名单域名外泄（Anthropic 披露事件），说明边界存在时调用期检查仍不可缺；Blaxel 待机态不持久、Daytona 停止即清内存，说明「销毁」与「休眠」语义要分开 | 增加第四个时机「挂起 / 恢复」：休眠时内存态是否保留、凭证是否失效、恢复后策略是否重评；销毁时明确内存清零与凭证撤销 | 中 |
| SBX-8 凭证经纪人（仅隔离底座相关部分） | 支持 | OpenShell（agent 不见真实凭证，supervisor 注入，sandbox 仅持网关公钥）、Cloudflare 出口代理注入、Docker 运行时注入于 microVM 边界外、Cowork 凭证留宿主钥匙串、Managed Agents vault 凭证不进沙箱（后者为第三方逆向） | 同域名外泄事件：凭证没泄但数据通过合法凭证上传到攻击者账户；经纪人只管「Agent 不持有凭证」，不管「合法凭证被滥用」 | 经纪人需带**目的地与会话绑定**（Cowork 的每会话受限令牌、请求须携带 VM 自己的会话令牌即为实例） | 中高 |

---

## §6 接缝发现

**J5 隔离的内存代价（主责）**

- 隔离单元的内存由两部分组成：固定开销（VMM、pvmfw、swiotlb，量级几十 MB）与 guest 私有页（取决于运行时与镜像）。降低代价的杠杆是共享只读基底与快照分叉。
- 手机缺少量产的快照 / 分叉原语；AVF 的气球机制曾因内存不足回退（C），说明 pVM 内存与 LMKD、应用生命周期的耦合还没有解。
- 交给内存管理（C4a）的接口需求：pVM 与会话沙箱的内存记入会话级 memcg；气球回收需和 LMKD / PSI 联动；swiotlb 与 dma-buf 的归属要可见。
- 与 J2 的交集：会话共享底座模型时，隔离单元不能持有 KV 页的直接映射，需要走 dma-buf 受控共享，这对 pVM 是额外限制，本次未检索到现成方案，待核实。

**J3（安全侧，仅记录）**：Chrome 的 User Alignment Critic 和 Origin Sets 是在执行层之上加语义层把关，与「注入防护放模型层还是执行层」的争论相关，详见 C2b。

---

## §7 组件特有输出：沙箱能力矩阵

列：隔离底座｜冷启动｜快照 / 分叉 / 休眠｜策略引擎｜凭证方案｜网络出口｜计费｜端侧可迁移性。「—」表示未找到公开资料，「待核实」表示来源冲突或仅第三方。

| 厂商 / 项目 | 隔离底座 | 冷启动 | 快照 / 分叉 / 休眠 | 策略引擎 | 凭证方案 | 网络出口 | 计费 | 端侧可迁移性 |
|---|---|---|---|---|---|---|---|---|
| E2B | 微 VM（Firecracker，待复核） | 官方未给 | 暂停 / 恢复，暂停约 4s/GiB（C） | — | — | — | 按秒 vCPU + 内存，暂停不计费 | 不可迁移，原语可借 |
| Daytona | 官方称默认 Linux 容器（Sysbox/Kata 说法待核实） | 27–90ms（第三方） | hot snapshot；fork 待核实 | — | — | — | 按秒 vCPU/内存（第三方称与 E2B 同价） | 不可迁移 |
| Modal | gVisor | — | 内存与文件系统快照；对驱动与运行时版本敏感 | — | — | — | — | 不可迁移 |
| Cloudflare | 容器（Sandbox）；V8 isolate（Dynamic Workers） | isolate 数 ms；容器据称快约 6 倍 | 文件系统快照（公测），可分叉 | — | 出口代理注入 | 代理 | — | isolate 需改造，容器不可迁移 |
| Blaxel | 微 VM（官网自述） | 待机恢复 <25ms | 待机可无限期，不持久 | — | — | — | — | 不可迁移，待机思路可借 |
| Morph | VM（Infinibranch） | 分支 <250ms | 快照 / 分支 / 恢复 | — | — | — | 公开价目未找到 | 不可迁移 |
| Vercel Sandbox | 底座措辞待核实 | — | 默认持久，停止即快照；内存快照 alpha | — | — | — | Active CPU + 内存 | 不可迁移 |
| 腾讯云 Cube | RustVMM + KVM | 均值 <60ms，P99 137ms | CubeCoW 快照克隆，回滚 | — | — | — | 开源自部署 | 不可迁移，CoW 思路可借 |
| NVIDIA OpenShell | 可选 Docker / Podman / K8s / microVM；Landlock + seccomp | — | 文档未提快照 | 声明式 YAML，静态与动态段，policy prover（形式化验证）阻止自动批准 | supervisor 注入，沙箱不见真实凭证 | 沙箱内代理，按目的地 / 端口 / 二进制 | 开源（v0.1.7） | 需改造：Landlock/seccomp 在 Android 可用，policy 模型可借 |
| AWS AgentCore | 会话级 microVM | — | 会话生命周期，结束清内存 | Gateway 处 Policy，Cedar 相关（Dogwood 关系待核实） | — | — | 按实际 CPU/内存，空闲免费 | 不可迁移 |
| Azure dynamic sessions | Hyper-V 沙箱 | 会话池预热 | 冷却期后删除 | Entra 角色鉴权 | — | 默认禁出站 | 预览状态待核实 | 不可迁移 |
| GKE Agent Sandbox / agent-sandbox | gVisor / Kata（RuntimeClass） | WarmPool 毫秒级分配（项目自述） | Sandbox 带稳定身份与持久存储 | — | — | NetworkPolicy | 随集群 | 不可迁移，WarmPool 概念可借 |
| OpenAI Codex | 云端隔离容器；CLI 为 Seatbelt / Landlock / bubblewrap | — | 容器缓存 | requirements.toml 等 | secrets 仅 setup 阶段 | 代理，agent 阶段默认关 | — | CLI 路线需改造后可借 |
| Anthropic | claude.ai：gVisor；Claude Code：Seatbelt / bubblewrap；Cowork：本地整机 VM | — | — | 代理执行网络与文件策略 | 凭证留宿主，受限令牌 | 白名单加 MITM 代理 | — | Cowork 对应 AVF，需改造 |
| Docker Sandboxes | 自研 VMM microVM | — | — | 网络允许 / 拒绝列表 | 运行时注入于边界外 | 列表控制 | — | 跨平台 VMM 思路有参考 |

**端侧参照行**

| 平台 | 隔离底座 | 启动 / 内存 | 快照 | 出口 | 凭证 |
|---|---|---|---|---|---|
| Android AVF / Microdroid | pKVM pVM | 量级 32–42（疑 MB，待核实） | 无量产 | 无系统级 per-会话 | Keystore / StrongBox（本次未检索，属已知机制） |
| Windows Agent Workspace | 账户 + 会话 | 未取得 | 无 | 未取得 | 本地 Agent 账户 |

---

## §8 参考资料与待核实清单

**参考资料**

| 编号 | 标题 | 机构 / 作者 | URL | 日期 |
|---|---|---|---|---|
| R1 | NVIDIA OpenShell（项目） | NVIDIA | https://github.com/nvidia/openshell | 2026 |
| R2 | How OpenShell Works | NVIDIA | https://docs.nvidia.com/openshell/latest/about/architecture | 2026（v0.1.7） |
| R3 | Experimental Agentic Features | Microsoft | https://support.microsoft.com/en-us/windows/ai/ai-features/experimental-agentic-features | 2025-11 起 |
| R4 | Architecting Security for Agentic Capabilities in Chrome | Google | https://blog.google/security/architecting-security-for-agentic/ | 2025-12-08 |
| R5 | Cloudflare Dynamic Workers（VentureBeat 报道） | VentureBeat | https://venturebeat.com/infrastructure/cloudflares-new-dynamic-workers-ditch-containers-to-run-ai-agent-code-100x | 2026-03 |
| R6 | Containers and Sandboxes are now generally available | Cloudflare | https://developers.cloudflare.com/changelog/2026-04-13-containers-sandbox-ga | 2026-04-13 |
| R6b | Cloudflare Containers, rebuilt to scale agent sandboxes | Cloudflare | https://blog.cloudflare.com/faster-agent-sandboxes/ | 2026 |
| R7 | Blaxel Sandboxes（官网与文档） | Blaxel | https://blaxel.ai/platform/sandboxes ；https://docs.blaxel.ai/ | 2026 |
| R8 | CubeSandbox | 腾讯云 | https://github.com/TencentCloud/CubeSandbox | 2026 |
| R8b | Cube Sandbox 开源介绍 | DEV Community | https://dev.to/jerrylin_0101/cube-sandbox-is-now-open-source-why-we-built-a-fast-and-secure-sandbox-for-ai-agents-d4k | 2026 |
| R9 | Morph Cloud 文档 | Morph | https://cloud.morph.so/docs/developers | 2026 |
| R10 | Firecracker 快照支持文档 | AWS / Firecracker | https://github.com/firecracker-microvm/firecracker/blob/master/docs/snapshotting/snapshot-support.md | — |
| R11 | E2B 计费说明 | E2B | https://docs.e2b.dev/faq/calculate-sandbox-price | 2026 |
| R12 | Vercel Sandbox pricing | Vercel | https://vercel.com/docs/sandbox/pricing | 2026 |
| R13 | AgentCore 会话管理；定价 | AWS | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-session-characteristics.html ；https://aws.amazon.com/bedrock/agentcore/pricing/ | 2026 |
| R14 | Azure Container Apps dynamic sessions overview | Microsoft | https://learn.microsoft.com/en-us/azure/container-apps/sessions | 2026 |
| R15 | Codex 沙箱与云端环境 | OpenAI | https://developers.openai.com/codex/sandbox ；https://developers.openai.com/codex/cloud/environments | 2026 |
| R16 | How we contain Claude across products | Anthropic | https://anthropic.com/engineering/how-we-contain-claude | 2026-05-25 |
| R17 | Agent Sandbox 文档 | Kubernetes SIG Apps | https://agent-sandbox.sigs.k8s.io/docs/ | 2026 |
| R18 | Why MicroVMs: The Architecture Behind Docker Sandboxes | Docker | https://www.docker.com/blog/why-microvms-the-architecture-behind-docker-sandboxes/ | 2026-04 |
| R19 | Claude Code sandboxing | Anthropic | https://anthropic.com/engineering/claude-code-sandboxing | 2025-10 |
| R20 | Google is retiring Privacy Sandbox（含 SDK Runtime） | BetaNews 等报道 | https://betanews.com/article/google-is-retiring-privacy-sandbox | 2025-10 |
| R21 | microdroid 最小 RAM 测量提交 | AOSP | https://android.googlesource.com/platform/packages/modules/Virtualization/+/becbc3ea | 日期待核实 |
| R22 | Virtual machines as a core Android primitive | Android Developers Blog | https://android-developers.googleblog.com/2023/12/virtual-machines-as-core-android-primitive.html | 2023-12 |
| R23 | Aster（MobiSys 2026，Bringing Confidential Computing to Android）；预印本 Aster: Fixing the Android TEE Ecosystem with Arm CCA | Shinde 课题组等 | https://www.shwetashinde.org/publications/aster_mobisys26.pdf ；https://arxiv.org/html/2407.16694v1 | 2026 / 2024 |
| R24 | Memory snapshots | Modal | https://modal.com/blog/mem-snapshots | 2025-01 |
| R25 | A Linux VM on Android via AVF（LPC 2025） | Google Android | https://lpc.events/event/19/contributions/2123/attachments/1730/3786/LPC%202025%20-%20A%20Linux%20VM%20on%20Android%20via%20AVF%20(Android%20MC).pdf | 2025 |
| R26 | Memory Integrity Enforcement | Apple | https://security.apple.com/blog/memory-integrity-enforcement | 2025-09-09 |
| R27 | gVisor Performance Guide | Google | https://gvisor.dev/docs/architecture_guide/performance/ | — |
| R28 | Daytona Isolation | Daytona | https://www.daytona.io/docs/en/isolation.md | 2026 |
| R29 | HarmonyOS 7 相关报道（HDC 2026） | 第三方 | https://news.lavx.hu/article/harmonyos-7-beta-puts-agents-at-the-os-layer-but-the-hard-evidence-is-still-missing | 2026 |

**待核实清单**

1. E2B 隔离底座是否为 Firecracker（官方文档措辞）；Daytona 默认边界与 fork 语义；Vercel Sandbox 底座。
2. GKE Agent Sandbox 是否 GA、最低版本；是否强制 gVisor。
3. AgentCore Policy 与 Cedar / Dogwood 的关系（归 C2b）。
4. Microdroid 最小 RAM 数字的单位与设备；绝对启动时间；pKVM 官方机型清单；Galaxy 支持情况。
5. Android isolatedProcess 在 2026 年的变化；SDK Runtime 官方退役时间表。
6. HarmonyOS「动态沙箱」是否存在及机制；鸿蒙 Agent 隔离方案。
7. Aster 论文的内存、延迟、并发数据（PDF 无法抽取文字）。
8. Firecracker 规格文档的日期；分叉 VM 的实测页共享率；Wasm 运行时单会话开销；各隔离单元的功耗。
9. Windows Agent Workspace 的凭证 / 网络出口机制。
10. Cube、Blaxel、Morph 的冷启动与恢复数字的独立复现。
11. BrowserEngineKit 的进程模型。

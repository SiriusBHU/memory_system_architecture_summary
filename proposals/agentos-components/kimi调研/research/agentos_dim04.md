# AgentOS 组件调研 · 维度 A：Agent 执行沙箱厂商格局（沙箱框架与执行能力）

- 调研日期：2026-11-06；时间范围以 2024-01 ~ 2026-11 为主，奠基性工作单独标注年份。
- 来源标准：官方文档 / GitHub / 技术博客优先；媒体与第三方对比站仅作佐证，均标注日期与置信度。
- 本维度覆盖：E2B、Daytona、Modal、Cloudflare（Sandboxes/Workers）、Blaxel、Morph、腾讯云 CubeSandbox、NVIDIA OpenShell；并覆盖 Anthropic Claude Code 沙箱、OpenAI Agent 执行环境、AWS（AgentCore/Strands）、Google（GKE Agent Sandbox / Agent Substrate）、Kubernetes agent-sandbox 项目。

---

## 1. 技术谱系表：隔离底座路线分类

隔离底座已在 2025–2026 收敛为五条清晰路线，各路线对应不同的"启动延迟—隔离强度—生态兼容性"三角取舍[^9^][^20^]：

| 路线 | 隔离原理 | 是否共享宿主机内核 | 典型启动 | 代表实现（年份） | 采用厂商/项目 |
|---|---|---|---|---|---|
| **microVM（硬件虚拟化）** | KVM 之上跑极简 VMM，每个沙箱独立 guest kernel | 否 | 60–250ms（快照/预热可 <100ms） | Firecracker（AWS，2018 开源，NSDI'20 论文）[^1^]；Cloud Hypervisor；libkrun | E2B、Morph、Vercel Sandbox、Fly.io Sprites、Blaxel、CubeSandbox（RustVMM+KVM 自研）、microsandbox（libkrun）、Runloop、Northflank、AWS AgentCore Code Interpreter[^1^][^2^][^13^][^14^][^22^] |
| **gVisor（用户态内核）** | Sentry 拦截并重实现 syscall，缩小对宿主内核的攻击面 | 部分（经收窄的 syscall 面） | 容器级；Pod 快照恢复秒级 | gVisor（Google，2018 开源） | Modal（默认运行时）、GKE Agent Sandbox、K8s agent-sandbox 默认后端、Agent Substrate[^8^][^20^][^21^] |
| **普通容器（runc/OCI）** | namespace + cgroup，共享内核 | 是 | 90ms–2s（预热池可达 <90ms） | Docker/containerd | Daytona（默认容器类，可选 VM 类/Kata/Sysbox）、OpenSandbox（可选 gVisor/Kata/Firecracker）[^5^][^7^][^26^] |
| **轻量 VM 包装容器（Kata）** | 容器接口 + 每 Pod 一个轻量 VM | 否 | ~200ms+ | Kata Containers（OpenInfra，2017 起） | K8s agent-sandbox 可选后端、CoreWeave、Northflank[^19^][^20^] |
| **语言级 / 进程级沙箱** | OS 原语（Seatbelt/bubblewrap/Landlock/seccomp/WFP）或 V8 isolate | 是 | 毫秒级（V8 isolate 亚毫秒） | sandbox-exec/Seatbelt、bubblewrap、Landlock、V8 isolates | Claude Code sandbox-runtime（srt）、OpenAI Codex CLI、NVIDIA OpenShell（Landlock+seccomp+容器/MicroVM 后端）、Cloudflare Dynamic Worker Loader（V8 isolate）、Docker Sandboxes[^7^][^16^][^17^][^24^] |

**关键结构性事实**：
- **"编排层 ≠ 隔离层"已成行业共识**。K8s agent-sandbox 官方文档明确自述："Agent Sandbox is a sandbox orchestrator. It delegates low-level container isolation to secure 'Sandbox Runtimes' (like gVisor or Kata Containers)"[^19^]；NVIDIA OpenShell 同样是策略/生命周期控制面，隔离委托给 Docker/Podman/MicroVM/K8s 后端[^15^]。这直接印证我方"第零层（借来的隔离边界）+ 统一接口面"的分层立场。
- **E2B SDK 正在成为事实接口标准**：CubeSandbox "兼容 E2B SDK，替换一个环境变量即可平替"[^14^]；Run Cloud 提供 `runcloud.compat.e2b` 适配层[^2^]；Runtime 提供 E2B SDK 兼容[^27^]。
- **OpenAI Agents SDK 于 2026-04-15 原生支持沙箱**，官宣托管供应商七家：Blaxel、Cloudflare、Daytona、E2B、Modal、Runloop、Vercel，外加 Docker 与 Unix-local 本地客户端[^17^][^18^]——这是"沙箱供应商接口收敛"的最强信号。

---

## 2. 关键数据（带出处日期）

### 2.1 启动延迟与密度

| 厂商 | 冷启动 | 恢复/分叉 | 密度/开销 | 出处（日期） |
|---|---|---|---|---|
| Firecracker（奠基） | ≤125ms；单主机 150 次启动/秒 | 快照/恢复为核心原语 | ≤5MiB VMM 开销/VM | NSDI 2020 论文 / AWS 官方规格[^1^]（2018 开源） |
| E2B | ~150ms（快照/模板启动）；<200ms | 暂停 ~4s/GiB，恢复 ~1s；单次最多 fork 20 份（含内存） | 1–8 vCPU / 1–8 GiB，仅 CPU | E2B 文档口径（2026-10 核验）[^2^][^3^][^7^] |
| Daytona | sub-90ms（预热容器池） | VM 类支持含内存 fork；暂停/恢复 <1s | 容器共享内核，密度高 | 官方口径 + 第三方核验（2026-07/10）[^5^][^7^] |
| Modal | 亚秒（实测中位 ~929ms） | 文件系统快照 GA；内存快照 alpha（7 天过期、终止原沙箱、限同机型、不支持 GPU） | gVisor | Beam/第三方对比（2026-11-01）[^8^][^10^] |
| Cloudflare Containers/Sandbox SDK | ~2s（完整容器） | 自动 sleep，scale-to-zero；R2 持久化 | 按实例规格 | 官方文档（2026-10-05）[^11^][^12^] |
| Cloudflare Dynamic Worker Loader | 毫秒级（V8 isolate） | — | 单进程内多 isolate，密度极高 | Cloudflare 官方博客（2026-03-24）[^7^] |
| Blaxel | <1s 新建 | standby 恢复 **<25ms**（内存与进程保留），待机 $0 计算费 | microVM（Hypervisor 未公开，一说 Firecracker） | Ry Walker / 官方（2026-06/10）[^23^][^13^] |
| Morph Cloud | <250ms | Infinibranch：**快照/分叉/恢复均 <250ms**，可分叉数百并行副本 | Firecracker microVM | Morph API 文档（2026-06）/ sandboxreview（2026-10-02）[^4^][^27^] |
| 腾讯云 CubeSandbox | **60ms**（50 并发 P99 137ms） | CubeCoW 事件级快照、毫秒级回滚、分叉克隆 | **<5MB 内存开销/沙箱，单机数千实例** | 腾讯云开发者社区（2026-09-01）/ 官网[^14^] |
| microsandbox | <100ms（自报，Apple Silicon）；实测裸机 320ms | fork/全状态快照 | 嵌入式、无 daemon | README/第三方（2026-04/08）[^24^] |
| K8s agent-sandbox / GKE | 预热池后亚秒（GKE 称 <800ms） | scale-to-zero + 恢复；Pod Snapshot 存 GCS | WarmPool 预热；GKE 称 300 沙箱/秒分配 | K8s 官方博客（2026-03-20）/ solo.io（2026-10-19）[^19^][^20^][^21^] |
| Agent Substrate（Google 系开源） | — | **<500ms 恢复，>500 次激活/秒**；"10x 于标准容器的密度" | actor 映射到 worker 池，空闲者快照出内存 | GitHub README（2026-11-05）[^21^] |

### 2.2 计费模型（2026-10 核验的公开牌价）

| 厂商 | 计费 | 关键价格 | 闲置成本 | 出处 |
|---|---|---|---|---|
| E2B | 按秒 | $0.000014/vCPU·s（≈$0.0504/vCPU·h）+ $0.0000045/GiB·s；Pro $150/月起，Enterprise $3k/月起（BYOC） | 暂停后停止计算计费，快照占存储费 | 官方 pricing（2026-10）[^2^][^3^] |
| Daytona | 按秒 | $0.0504/vCPU·h + $0.0162/GiB·h（与 E2B 同价）；GPU $0.57/h（RTX4090 抢占）~ $6.25/h（B300）；Windows +$0.0858/vCPU·h | 停止/暂停仍收磁盘保留费；归档释放 | 官方/第三方核验（2026-10-04/17）[^5^][^6^] |
| Modal | 按秒（沙箱价为函数价 3x） | $0.00003942/物理核·s + $0.00000667/GiB·s（≈$0.19/h 一核+2GiB）；按 max（请求， 实耗）计费 | 默认 5 分钟 TTL，上限 24h | Beam 对比（2026-11-01）[^8^] |
| Cloudflare Containers | 按 10ms | $0.000020/vCPU·s（仅活跃 CPU）+ $0.0000025/GiB·s（按规格预置）；含 Workers Paid $5/月额度 | sleep 即停费（scale-to-zero） | 官方文档（2026-10-05）[^11^] |
| Vercel Sandbox | 活跃 CPU 计费 | $0.128/活跃 vCPU·h + $0.0212/GB·h（I/O 等待不计费，官方称对突发负载省至 95%） | 停止后从快照恢复 | Vercel GA 公告（2026-01-30）/ 第三方[^25^][^7^] |
| Blaxel | 按秒 + 待机 $0 | $0.0000115/GB·s（活跃，≈$0.041/GB·h）；快照存储 $0.20/GB·月 | 待机仅存储费，无限期休眠 | 官方/第三方（2026-10-13）[^13^][^23^] |
| Morph | MCU 积分 | $0.05/MCU；Team $40/月含 1,000 MCU | 暂停仅按快照计费 | temps.sh（2026-10-20）[^27^] |
| AWS AgentCore Code Interpreter | 按秒（1s 起步） | $0.0895/vCPU·h + $0.00945/GB·h；空闲与 I/O 等待免费 | 会话默认 15 分钟，可延至 8h | 官方/研究综述（2026-06）[^22^] |
| CubeSandbox / K8s agent-sandbox / OpenShell / microsandbox | 开源（Apache-2.0），自付基础设施 | — | 自动挂起/唤醒 | 各自 GitHub[^14^][^19^][^15^][^24^] |

### 2.3 生命周期原语对比（快照/分叉/休眠/恢复）

- **E2B**：pause（文件系统+内存，约 4s/GiB）→ resume（~1s，无限期保留）；fork 运行中沙箱最多 20 份（含内存）；模板=Docker 镜像派生[^2^][^7^]。
- **Morph**：Infinibranch 把"分叉"做成核心产品——运行中 VM 全状态（内存/文件系统/网络连接）快照并分叉为 N 个并行分支，<250ms，分支可再分支；暂停期间只付快照费[^4^][^27^]。
- **CubeSandbox**：CubeCoW（写时复制快照引擎）支持事件级快照、毫秒级回滚、一快照分叉多沙箱（RL 场景一训十分叉）[^14^]。
- **Blaxel**：差异化在"perpetual"——空闲数秒自动 standby，内存+进程保留，恢复 <25ms，无限期[^13^][^23^]。
- **Modal**：GA 路径只有文件系统快照（恢复到新沙箱）；内存快照 alpha 且会终止原沙箱[^8^][^7^]。
- **K8s agent-sandbox**：pause/resume、scale-to-zero、SandboxWarmPool 预热；GKE 侧 Pod Snapshot（内存+文件落 GCS，恢复成新沙箱）[^19^][^20^]。
- **Cloudflare**：快照只恢复文件，不含内存/进程；Dynamic Worker 为纯无状态 isolate[^7^][^12^]。
- **Vercel Sandbox**：从最近保存的快照恢复，不含活内存[^7^]。

---

## 3. 趋势判断（收敛方向 + 空白点）

### 3.1 收敛方向（事实+判断）

1. **隔离底座向 microVM 收敛为"高端默认"，gVisor 守住 K8s 生态**。2025–2026 市场固化在三个隔离原语上：Firecracker microVM（E2B、Morph、Blaxel、Vercel、CubeSandbox 等）、gVisor（Modal、GKE）、V8 isolate（Cloudflare Dynamic Workers）[^9^]。判断：对新入局者，"具名 hypervisor"已成信任门槛——"说得出 Firecracker 才是架构，'secure sandbox' 只是营销"（infragap 评 E2B vs Daytona）[^6^]。
2. **生命周期原语从"短暂一次性"转向"可休眠、可分叉、可恢复"**。fork/分叉从 Morph 的独门绝技变成 2026 年头部厂商标配（E2B fork×20、CubeSandbox 分叉克隆、Daytona VM 类 fork）[^7^][^14^]；休眠经济学（Blaxel 25ms 恢复、待机 $0）成为直接竞争轴[^13^]。
3. **凭证经纪人（credential broker）成为 2026 年最一致的差异化收敛点**：E2B Secrets（2026-10，egress 代理注入凭证，对 agent 不可见）[^3^]；CubeSandbox CubeEgress "凭证注入，密钥对沙箱内代码物理不可见"[^14^]；OpenShell "真实 secret 留在沙箱外，仅注入被 policy 授权的请求"[^15^]；Agent Substrate "Zero credentials in the sandbox"[^21^]；microsandbox "secrets that never enter the VM"[^24^]。判断：**凭证不出边界已从加分项变为入场券**。
4. **策略层外移 + 声明式策略语言兴起**。OpenShell 把 YAML policy 编译为 OPA/Rego、附带 policy prover（形式化校验权限不越界，Z3/Zelkova 式）[^15^]；AWS Strands Box（2026-10 开发者预览）用开源策略语言 **Dogwood**，支持"有状态策略"（如"测试通过才允许 git push"、"读过客户数据后禁止外发 HTTP"）[^28^]。判断：策略引擎正从"静态 allowlist"走向"跨动作关联的有状态策略"——这与我方"三维风险模型定档 + 三时机执行"同向。
5. **计费模型分化为两派**：按分配资源按秒计费（E2B/Daytona/Modal）vs 按活跃 CPU 计费（Cloudflare/Vercel，I/O 等待免费）[^7^][^11^]。对"大部分时间在等模型"的 agent 负载，活跃 CPU 计费 + 休眠至零是明确趋势。
6. **编排层标准化**：K8s SIG Apps agent-sandbox（2025-11 KubeCon NA 立项，Sandbox/SandboxTemplate/SandboxClaim/SandboxWarmPool 四 CRD）成为云中立标准，GKE 已托管化，EKS 有官方参考架构[^19^][^20^]。OpenAI Agents SDK 沙箱供应商抽象（2026-04）是应用层的对应收敛[^17^]。
7. **安全事故推动"边界在 agent 之外"叙事**。Claude Code 沙箱绕过事件（2026-03：agent 在 bubblewrap 拦截后自行关闭沙箱执行）[^29^]；AWS AgentCore Code Interpreter 的 DNS 隧道逃逸研究与两个 RCE CVE（2026 年）[^22^]；NVIDIA 以"agent circumvented security controls at the application layer"为 OpenShell 的核心论据[^15^]。

### 3.2 空白点

1. **端侧/本地会话级沙箱基本空白但有先行者**：microsandbox（本地优先、嵌入式、无 daemon、<100ms、密钥不进 VM）与 Docker Sandboxes（单机开发者向）、SmolVM（本地 computer-use）是最早占位者[^24^][^30^]；但**没有任何主流托管厂商提供"端侧会话级沙箱"产品**——E2B/Daytona/Modal/Blaxel 全部是云端 per-second 计费模型，端侧只有开源库（beta 状态）与 OS 原语级方案（srt、Codex 沙箱）。判断：**"端侧 + 会话级 + 统一接口面"确为空白带**，但需注意 Claude Code srt 与 Codex 已把"OS 原语沙箱"做成编码 agent 的本地默认配置[^16^][^18^]——空白的不是"端侧隔离"，而是"端侧隔离之上的统一动作接口与权限装配层"。
2. **undo/幂等/dry-run 等动作级语义无人覆盖**。所有厂商的生命周期原语停留在"机器级"（快照/分叉/恢复），**没有厂商把 dry-run、undo、幂等键、结构化拒绝作为沙箱接口面的一等公民**——快照回滚（CubeSandbox 毫秒级回滚）是最接近的能力，但它是运维原语而非动作契约。这是我方 L1 七要素的明确空位。
3. **GPU 沙箱碎片化**：Modal GPU 只能 gVisor 不能 Docker/内存快照[^8^]；E2B/Vercel/Blaxel 无 GPU[^2^]；Daytona/Northflank 有 GPU[^5^]。GPU×强隔离×快照三者不可兼得仍是常态。
4. **跨链权限规则无标准**：principal 传播仍无共识标准（Zylos 研究指出 RFC 8693 token exchange 为最先进水平，SPIFFE 不覆盖 per-agent 粒度）[^9^]；"跨链不升级"类规则未见任何厂商实现——OpenShell 的 policy prover 是最近似者（校验权限变更不越界）[^15^]。
5. **Windows/移动端沙箱稀缺**：仅 Daytona 提供 Windows 沙箱（加价）；iOS/Android 侧只有个别厂商（Run Cloud 的 iOS simulator）[^2^][^5^]。

---

## 4. 对我方的启发（逐条「支持/挑战/需要修订」）

**对我方"借来的隔离边界（第零层）"立场 —— 总体强烈支持：**
- 【支持】编排层/接口层与隔离层分离已是行业标准做法：K8s agent-sandbox 明言自己是 orchestrator 不是边界[^19^]；OpenShell 支持 Docker/Podman/MicroVM/K8s 多后端[^15^]；Agent Substrate 同时支持 gVisor 与 microVM[^21^]。"不自建隔离底座、向后端借隔离"有大量先例背书。
- 【支持】E2B SDK 兼容层的扩散（CubeSandbox、Run Cloud、Runtime）证明"统一接口面 + 可替换底座"的商业可行性[^14^][^2^]。
- 【需要修订】"借来"不等于"无选择标准"。市场已把"具名隔离机制"作为信任门槛[^6^]；我方应规定第零层的**准入清单**（如仅接受 microVM/gVisor/Kata/具名 OS 原语，普通 runc 容器仅限低危档），并与三维风险模型定档联动——高危档强制 microVM 级。
- 【挑战】端侧场景下"借"的对象不同：端侧没有 Firecracker 云，只有 OS 原语（Seatbelt/bubblewrap/Landlock/WFP）或嵌入式 microVM（libkrun/Hypervisor.framework）[^16^][^24^]。第零层在端侧的抽象需容忍"共享内核 + 进程级限制"这一较弱底座，此时 L1 接口面与权限层承担更多补偿责任（参考 OpenShell：容器/进程隔离 + 强策略 + 凭证外置的组合拳）[^15^]。

**对 L0/L1 接口面与七要素：**
- 【支持】L0 raw 执行兜底符合所有厂商现状（exec/run_code 是共同基线）。
- 【支持】七要素中"异步、schema"已有行业对应物（SSE 流式输出、MCP 工具 schema）；但 **dry-run/undo/幂等/结构化拒绝无厂商覆盖（见 3.2-2）**，是我方差异化空位，建议坚持。
- 【需要修订】"undo"在机器级已有廉价实现路径：CubeSandbox 毫秒级回滚、Morph 分叉即"平行试错"。我方 L1 的 undo 语义可考虑**底层复用快照/分叉原语**，而非逐动作补偿——但需定义动作级 undo 与机器级回滚的映射与降级规则[^14^][^4^]。

**对权限管理：**
- 【支持】凭证经纪人设计被多方独立验证为正确方向（E2B Secrets、CubeEgress、OpenShell provider、Substrate egress gateway 全部"凭证不进沙箱"）[^3^][^14^][^15^][^21^]。
- 【支持】"装配/调用/销毁三时机执行"对应 OpenShell 的"policy 运行前校验（prover）+ 运行中强制（supervisor）+ 动态变更审批"[^15^]。
- 【挑战】"跨链不升级"无先例，需自研校验逻辑；OpenShell policy prover（形式化校验 policy 变更不越界）是唯一可参考实现[^15^]。
- 【需要修订】注意 Claude Code 事件的教训：**agent 能请求"关闭沙箱/绕过拦截"本身必须被列为高危动作并默认拒绝**（外部演示中 agent 被 bubblewrap 拦截后自行禁用沙箱）[^29^]。我方结构化拒绝应把"削弱隔离/策略的动作"定为最高风险档。
- 【挑战】有状态策略正在兴起（Strands Box/Dogwood："读过敏感数据后禁止外发"）[^28^]——若我方权限模型是纯静态三维定档，需评估是否引入"会话历史感知"的动态降档。

**对身份管理归应用：**
- 【支持】Agent Substrate 的 per-actor SPIFFE 短期证书 + egress gateway 代铸 JWT[^21^]、AgentCore 的 IAM 执行角色[^22^]，都把"工作负载身份"留在基础设施层、把用户身份留给应用——与我方"系统只留信任根与跨链规则"一致。
- 【挑战】Zylos 研究指出 principal 传播无标准、SPIFFE 不覆盖 per-agent-instance 粒度[^9^]——我方信任根设计需自行定义会话/动作级身份的断言格式，短期无标准可借力。

---

## 5. 组件特有输出素材：沙箱能力矩阵（维度 A 部分）

| 厂商 | 隔离底座 | 快照能力 | 策略引擎 | 凭证方案 | 计费模型 | 差异化定位 |
|---|---|---|---|---|---|---|
| **E2B** | Firecracker microVM（独立内核） | 模板快照启动 ~150ms；pause 含内存（~4s/GiB）；resume ~1s；fork ≤20（含内存） | egress 按 CIDR/hostname 策略 | Secrets vault：egress 代理注入，对 agent 不可见（2026-10） | 按秒 $0.0504/vCPU·h + $0.0162/GiB·h；Pro $150/月 | 品类定义者；开源 Apache-2.0 + BYOC；Embed 单机自托管（2026-09）[^2^][^3^] |
| **Daytona** | 默认 OCI 容器（共享内核）；可选 VM 类（独立内核，fork 含内存）/Kata/Sysbox | sub-90ms 预热池；快照/fork/恢复；归档至对象存储无限期 | egress 按账户 Tier 门控（Tier1-2 受限） | scoped API keys；秘密代理 | 按秒 $0.0504/vCPU·h + $0.0162/GiB·h；GPU $0.57–6.25/h | 速度+GPU+Windows 桌面+computer use；$24M A 轮（2026-02）[^5^][^6^][^7^] |
| **Modal** | gVisor（默认）；VM 运行时（可选，独立内核）；GPU 仅 gVisor | 文件系统快照 GA；内存快照 alpha（7 天过期、终止原沙箱） | 域名 allowlist（仅 443） | env 注入 | 按秒，沙箱=3x 函数价（≈$0.19/h/核+2GiB）；上限 24h | GPU+Python ML 原生；LLM 运行时自定义环境[^8^][^10^] |
| **Cloudflare（Sandboxes/Containers/Workers）** | Workers 上容器（VM 隔离由平台保证，非 per-sandbox 具名 hypervisor）；Dynamic Workers = V8 isolate | 文件快照（R2）；不含内存/进程；自动 sleep→0 | 出口代理 + 域名策略 | 出口代理注入凭证 | 按 10ms；活跃 CPU $0.072/vCPU·h + 内存按规格；含 $5/月额度 | 边缘分布 300+ 节点；Agents SDK 原生集成[^11^][^12^][^7^] |
| **Blaxel** | microVM（hypervisor 未公开，一说 Firecracker） | standby 保内存+进程，恢复 <25ms；无限期休眠；待机 $0 | 网络网关一等公民 | 秘密代理 | 按秒 $0.0000115/GB·s（活跃）；快照存储 $0.20/GB·月 | "Perpetual sandbox" 休眠经济学；同址托管 agent/MCP；2026-09 被 Baseten 收购[^13^][^23^] |
| **Morph** | Firecracker microVM（Infinibranch） | 快照/分叉/恢复均 <250ms；分叉数百并行副本，分支可再分支 | 未公开 | 未公开（无 secret store） | MCU 积分 $0.05/MCU；Team $40/月 | 分叉为核心产品：树状探索/RL rollout/SWE-bench 评估[^4^][^27^] |
| **腾讯云 CubeSandbox** | 自研 RustVMM+KVM microVM（独立内核 + eBPF） | CubeCoW：事件级快照、毫秒级回滚、分叉克隆；60ms 冷启动；<5MB/实例，单机数千实例 | eBPF 内核态 L4 隔离 + CubeEgress L7（域名/路径/方法，HTTPS MITM 动态证书） | CubeEgress 凭证注入，密钥对沙箱物理不可见 | 开源 Apache-2.0，自建 | E2B SDK 平替；私有化部署；CNCF Landscape[^14^] |
| **NVIDIA OpenShell** | 委托后端：Docker/Podman/MicroVM（KVM/Hypervisor.framework）/K8s；沙箱内 Landlock+seccomp+无能力子进程 | SDK 支持 create/pause/resume/snapshot/destroy | **YAML→OPA/Rego；policy prover 形式化校验；supervisor 逐请求检查 HTTP/GraphQL/MCP；默认全拒绝** | Provider 机制：真实密钥留 gateway，占位符进沙箱 | 开源 Apache-2.0 | 策略层产品化+Sentry DPU 带外看门狗；100+ 组织协作；SAP/Salesforce/ServiceNow 集成[^15^] |
| **Anthropic Claude Code（srt）** | OS 原语：macOS Seatbelt / Linux bubblewrap / Windows WFP+NTFS ACL（alpha） | 无机器级快照（进程级） | 域名 allowlist/denylist + Unix socket 代理；v2.1.219 strictAllowlist 直接拒绝 | credential masking；无内置凭证 denylist | 开源 Apache-2.0（2026-10 发布 @anthropic-ai/sandbox-runtime） | 端侧/CLI 编码 agent 默认沙箱；减少 84% 权限询问[^16^][^29^] |
| **OpenAI（Codex + Agents SDK）** | Codex 本地：Seatbelt/bubblewrap/MXC；Codex Cloud：云端隔离沙箱禁网；Agents SDK：抽象七家托管商 | Codex Cloud 每任务一次性环境；Agents SDK 支持快照与会话 rehydration | workspace-write/read-only/full-access 三模式 + 域名级网络控制 | harness 与执行平面凭证分离（控制面持 key，沙箱零凭证） | API 订阅内 | 2026-04-15 Agents SDK 沙箱化=harness/执行分离架构的行业标杆[^17^][^18^] |
| **AWS（AgentCore CI / Strands Box）** | AgentCore Code Interpreter：每会话独立 microVM（MMDS 元数据服务） | 会话 15min–8h；S3 文件互通；无分叉 | 网络三模式（sandbox/public/VPC）；Strands Box（2026-10 预览）：**Dogwood 策略语言，有状态策略** | IAM 执行角色（最小权限是用户责任；2026 研究揭示 MMDS 凭证提取路径） | 按秒 $0.0895/vCPU·h + $0.00945/GB·h | 企业信封（CloudTrail/VPC/PrivateLink）；Strands Box 把策略做成开源语言[^22^][^28^] |
| **Google（GKE Agent Sandbox / Agent Substrate）** | gVisor（runsc）；Substrate 另支持 Cloud Hypervisor microVM | WarmPool <800ms 分配；Pod Snapshot（内存+文件落 GCS）；Substrate <500ms 恢复、500 激活/秒、10x 密度 | Substrate：默认全拒绝网络 + egress 网关 | Substrate：SPIFFE per-actor 短期证书 + egress 代铸 JWT；沙箱零凭证 | GKE 常规计费（Autopilot 按 Pod 请求按秒） | K8s 原生标准实现；密度/休眠调度是核心创新[^19^][^20^][^21^] |
| **Kubernetes agent-sandbox（SIG Apps）** | 可插拔 RuntimeClass（gVisor/Kata；未来 Firecracker） | pause/resume、scale-to-zero、SandboxWarmPool | 委托 K8s NetworkPolicy/RBAC | env 注入（委托生态） | 开源 Apache-2.0 | 编排标准（四 CRD），2025-11 KubeCon NA 立项[^19^] |

---

## 6. 证据清单

[^1^] **Claim**: Firecracker 冷启动 ≤125ms、每 VM ≤5MiB VMM 开销、单主机 150 次启动/秒；AWS 2018 开源，NSDI 2020 论文背书。 **Source**: bex.co 技术博客。 **URL**: https://bex.co/blog/2026/07/29/dagger-firecracker-microvm-build-isolation **Date**: 2026-07-29 **Excerpt**: "Firecracker's own specification puts a cold boot at 125ms or less, with 5MiB or less of VMM memory overhead per microVM... up to 150 microVM boots per second on a single host... backed by the team's NSDI 2020 paper." **Confidence**: 高（论文级数据）。

[^2^] **Claim**: E2B = Firecracker microVM/沙箱；快照启动 ~150ms；pause 保内存约 4s/GiB、resume ~1s；fork ≤20；$0.000014/vCPU·s + $0.0000045/GiB·s；Hobby 免费（$100 credit、1h 会话、20 并发）；Pro $150/月（24h、100 并发）；Enterprise $3k/月起 BYOC；无 GPU。 **Source**: controlplane 对比文 + aitrendtool + balazscsorba（均引官方 pricing/docs）。 **URL**: https://controlplane.com/blog/post/best-ai-agent-sandboxes-2026 ; https://balazscsorba.com/blog/e2b **Date**: 2026-10-26 / 2026-10-02 **Excerpt**: "each session runs in a hardware-isolated Firecracker microVM... about 150 ms startup from a snapshot... about 1 second to resume a paused sandbox... $0.000014 per vCPU-second and $0.0000045 per GiB-second." **Confidence**: 高。

[^3^] **Claim**: E2B Secrets（2026-10）在 egress 代理注入凭证、对 agent 不暴露；egress 可按 CIDR/hostname 控制；Embed（2026-09）Apache-2.0 单机自托管包；2025-07 完成 $21M A 轮。 **Source**: simular.ai 对比文（引官方文档）。 **URL**: https://www.simular.ai/alternatives/e2b-alternatives-for-ai-agents **Date**: 2026-10-13 **Excerpt**: "in October, Secrets, for injecting credentials into requests without exposing them to the agent... In September 2026 E2B shipped Embed, an Apache-2.0 single-machine package." **Confidence**: 高。

[^4^] **Claim**: Morph Cloud = Infinibranch microVM（Firecracker），快照/分叉/恢复 sub-250ms，命令执行含 SSE，HTTP 服务暴露，morphcloud Python/TS SDK + CLI。 **Source**: GitHub api-evangelist/morph-labs（引官方 API 文档）。 **URL**: https://github.com/api-evangelist/morph-labs **Date**: 2026-06-20 **Excerpt**: "Infinibranch microVM (Firecracker) sandbox infrastructure for agents — sub-250ms branch, snapshot, and restore." **Confidence**: 高。

[^5^] **Claim**: Daytona 默认 Docker/OCI 容器（可选 Kata/Sysbox），冷启动 ~90ms（预热池），快照/fork/暂停恢复，GPU（RTX4090 $0.57/h 起至 B300 $6.25/h）、Windows（+$0.0858/vCPU·h）；$0.0504/vCPU·h + $0.0162/GiB·h 按秒；$200 免费额度。 **Source**: ghuntley 参考文档 + hokai 测评（引官方 pricing）。 **URL**: https://github.com/ghuntley/how-to-ralph-wiggum/blob/main/references/sandbox-environments.md ; https://hokai.io/kr/hub/services/daytona **Date**: 2026-10-04（hokai 核验） **Excerpt**: "Fastest cold start: ~90ms (container-based)... Isolation: Docker/OCI, Kata/Sysbox optional... Compute is $0.0504 per vCPU-hour and memory is $0.0162 per GiB-hour." **Confidence**: 高。

[^6^] **Claim**: Daytona 仓库自 2026-06 归档转专有；$24M A 轮（FirstMark，2026-02-05）；egress 受账户 Tier 门控；fork 含内存仅限 VM 类。 **Source**: infragap 对比文 + temps.sh + developersdigest。 **URL**: https://infragap.com/compare/e2b-vs-daytona/ **Date**: 2026-08-26 **Excerpt**: "Proprietary since June 2026... $24M Series A led by FirstMark Capital announced 02-05-2026." **Confidence**: 高。

[^7^] **Claim**: 各厂 fork/快照能力对比：E2B fork 含内存 ≤20；Daytona 仅 VM 类含内存 fork；Vercel 从最近快照恢复（无活内存）；Modal 内存快照实验性且终止原沙箱；Cloudflare 快照仅文件。另：Cloudflare Dynamic Worker Loader（V8 isolate）2026-03 开放 beta，可运行时注入代码、禁网、RPC 能力授予。 **Source**: developersdigest 对比 FAQ + Cloudflare 官方博客。 **URL**: https://www.developersdigest.tech/blog/ai-agent-code-sandbox-comparison-2026 ; https://blog.cloudflare.com/dynamic-workers **Date**: 2026-07-01 / 2026-03-24 **Excerpt**: "E2B forks a running sandbox with filesystem and memory, up to 20 forks per call... Cloudflare snapshots restore files but not memory or running processes." / "Dynamic Worker Loader is now in open beta." **Confidence**: 高。

[^8^] **Claim**: Modal 沙箱 24h 上限；GPU 仅 gVisor、Docker 仅 VM 运行时；内存快照 alpha（7 天过期、须同机型、终止原沙箱）；沙箱计费为 3x 牌价（$0.00003942/核·s + $0.00000667/GiB·s）。 **Source**: Beam 官方博客对比。 **URL**: https://www.beam.cloud/blog/modal-sandbox-alternatives **Date**: 2026-11-01 **Excerpt**: "GPU sandboxes run only on gVisor... Memory snapshots are in alpha. They expire after 7 days... snapshotting a sandbox terminates it... Sandboxes bill at Modal's non-preemptible rate, three times list price." **Confidence**: 中高（竞争对手视角，但与官方文档多处一致）。

[^9^] **Claim**: 2025–2026 市场收敛于三隔离原语（Firecracker/gVisor/V8 isolate）；策略执行收敛为三层模型（客户端预检/网关强制/沙箱内资源限）；principal 传播无共识标准（RFC 8693 为最先进水平）。 **Source**: Zylos Research。 **URL**: https://zylos.ai/research/2026-06-13-remote-tool-execution-cloud-sandbox-platforms/ **Date**: 2026-06-13 **Excerpt**: "The market solidified in 2025-2026 around three isolation primitives... Principal propagation has no consensus standard yet." **Confidence**: 中高（研究综述，判断成分标注）。

[^10^] **Claim**: Modal 冷启动实测中位 929ms；gVisor 默认、VM 运行时可选。 **Source**: agent37 对比（引公开 benchmark）。 **URL**: https://www.agent37.com/compare **Date**: 2026-10-22 **Confidence**: 中。

[^11^] **Claim**: Cloudflare Containers 按 10ms 计费，CPU 仅按活跃使用、内存/磁盘按预置规格；sleep 后停费（scale-to-zero）；Workers Paid $5/月含 25 GiB·h 内存 + 375 vCPU·min。 **Source**: Cloudflare 官方文档。 **URL**: https://developers.cloudflare.com/containers/platform/pricing/ **Date**: 2026-10-05 **Excerpt**: "Containers are billed for every 10ms that they are actively running... CPU usage is based on active usage only... Charges stop after the container instance goes to sleep." **Confidence**: 高（官方）。

[^12^] **Claim**: Cloudflare Sandbox SDK（@cloudflare/sandbox）2026-02 大版本：流式输出、持久 Python/JS code interpreter、文件系统、Git、后台进程控制、公开 URL 暴露；容器化执行于 Workers 之上。 **Source**: Cloudflare 社区官方 changelog。 **URL**: https://community.cloudflare.com/t/agents-workers-cloudflare-sandbox-sdk-adds-streaming-code-interpreter-git-support-process-control-and-more/897032 **Date**: 2026-02-24 **Confidence**: 高（官方）。

[^13^] **Claim**: Blaxel "perpetual sandbox"：standby $0 计算费、恢复 <25ms（内存+进程保留）、无限期休眠；$0.0000115/GB·s（活跃）、快照存储 $0.20/GB·月；SOC2/HIPAA/ISO27001；2026-09 被 Baseten 收购；$7.3M 种子轮（2025-07）。 **Source**: Ry Walker Research + simular。 **URL**: https://rywalker.com/research/blaxel ; https://www.simular.ai/alternatives/e2b-alternatives-for-ai-agents **Date**: 2026-06-11 / 2026-10-13 **Excerpt**: "sandboxes hibernate to $0 compute on standby and resume in under 25ms with memory and running processes preserved." **Confidence**: 高。

[^14^] **Claim**: CubeSandbox（腾讯云开源，Apache-2.0）：RustVMM+KVM MicroVM，60ms 创建（50 并发 P99 137ms）、<5MB 内存开销、单机数千实例；CubeCoW 事件级快照/毫秒回滚/分叉克隆；eBPF（CubeVS）内核态网络隔离 + CubeEgress（OpenResty）L7 域名/路径过滤、HTTPS MITM 动态证书、凭证注入（密钥对沙箱不可见）、JSONL 审计；兼容 E2B SDK。 **Source**: 腾讯云开发者社区 + GitHub README + 官方博客。 **URL**: https://cloud.tencent.com/developer/article/2735539 ; https://github.com/TencentCloud/CubeSandbox/blob/master/README_zh.md ; https://cubesandbox.com/zh/blog/posts/2026-06-23-cubesandbox-network-deep-dive **Date**: 2026-09-01 / 2026-06-22 **Excerpt**: "60 毫秒创建沙箱、5MB 内存开销、硬件级隔离... 内置L7 安全代理支持按域名/路径/方法的精细策略及自动凭证注入，密钥对沙箱内代码不可见。" **Confidence**: 高（官方）。

[^15^] **Claim**: NVIDIA OpenShell（2026-09-28 发布，Apache-2.0，随 Open Agent Safety Platform）：Gateway/Supervisor/Sandbox 三件套；YAML policy 编译 OPA/Rego；Landlock 文件系统 + seccomp 进程 + 无能力子进程；默认全拒绝网络；supervisor 可检查 HTTP/GraphQL/MCP 流量到方法级；凭证留沙箱外按需注入；policy prover（Z3/Zelkova 式）形式化校验权限不越界；agent 可提议权限变更但不能自批；支持 Docker/Podman/MicroVM/K8s 后端；OCSF 审计；Sentry 在 BlueField-4 DPU 带外监控可毫秒级隔离 agent。 **Source**: Wikipedia + NVIDIA 技术博客转述 + 多家测评。 **URL**: https://en.wikipedia.org/wiki/Nvidia_OpenShell ; https://www.promptea.me/en/blog/nvidia-open-agent-safety-platform-openshell-sentry **Date**: 2026-09-28/29 **Excerpt**: "Policies are defined declaratively... keep credentials outside the agent workload... policy prover uses formal methods to analyze whether proposed permissions exceed defined security boundaries." **Confidence**: 高。

[^16^] **Claim**: Anthropic 开源 Claude Code 沙箱 runtime（srt，@anthropic-ai/sandbox-runtime，Apache-2.0）：macOS sandbox-exec/Seatbelt、Linux bubblewrap、Windows WFP+NTFS ACL（alpha）；allow-only 网络策略经沙箱外 Unix socket 代理执行域名白名单；credential masking、AWS SigV4；Claude Code v2.1+ 原生内置，内部数据称减少 84% 权限询问。 **Source**: aiweekly + 社区指南（引官方 README/文档）。 **URL**: https://aiweekly.co/alerts/anthropic-open-sources-claude-code-sandbox-under-apache-20 ; https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/guide/security/sandbox-native.md **Date**: 2026-10-24 / 2026-10-17 **Excerpt**: "a lightweight sandboxing tool for enforcing filesystem and network restrictions on arbitrary processes at the OS level, without requiring a container." **Confidence**: 高。

[^17^] **Claim**: OpenAI 于 2026-04-15 发布 Agents SDK 重大更新：原生沙箱执行，托管供应商含 Blaxel/Cloudflare/Daytona/E2B/Modal/Runloop/Vercel + Docker/Unix-local；harness（控制面，持凭证）与沙箱化计算（执行面，窄凭证）分离；支持小时/天/周级长运行 agent（快照+会话 rehydration）。 **Source**: OpenAI 官方 + byteiota + agenticbrew。 **URL**: https://openai.com/index/the-next-evolution-of-the-agents-sdk/ ; https://www.agenticbrew.ai/news/341c7677-8a5f-4dc9-8d66-20838c8484ab/openai-agents-sdk-adds-sandbox-execution-and-long-running-agent-support **Date**: 2026-04-15/16 **Excerpt**: "sandbox-aware orchestration... The architecture cleanly separates the agent harness (control plane...) from sandboxed compute (execution plane running tool calls in unprivileged environments with narrow credentials)." **Confidence**: 高。

[^18^] **Claim**: OpenAI Codex 本地沙箱：macOS Seatbelt、Linux bubblewrap+seccomp、Windows MXC；默认 workspace-write 且禁网；Codex Cloud 每任务云端隔离沙箱、预载仓库快照、默认禁网（2025-06 起可选联网+域名级控制）；已知 CVE-2025-59532（沙箱 cwd 配置绕过，0.2.0–0.38.0）。 **Source**: agent37 指南 + arXiv 论文 + CVE 记录。 **URL**: https://www.agent37.com/blog/codex-sandbox ; https://arxiv.org/html/2603.18377v2 ; https://cve.imfht.com/detail/CVE-2025-59532?lang=en **Date**: 2026-10-14 / 2025-09-24 **Excerpt**: "OpenAI Codex executes tasks in a cloud sandbox with internet disabled, confining execution to a preloaded repository snapshot." **Confidence**: 高。

[^19^] **Claim**: Kubernetes agent-sandbox（SIG Apps，2025-11 KubeCon NA 立项）：Sandbox/SandboxTemplate/SandboxClaim/SandboxWarmPool 四 CRD；稳定主机名与网络身份；pause/resume/scale-to-zero；明确声明"sandbox orchestrator"，隔离委托 gVisor/Kata（RuntimeClass）；Python/Go SDK；alpha 阶段。 **Source**: Kubernetes 官方博客 + pkg.go.dev + 官方文档站。 **URL**: https://kubernetes.io/blog/2026/03/20/running-agents-on-kubernetes-with-agent-sandbox/ ; https://pkg.go.dev/sigs.k8s.io/agent-sandbox@v1.0.0 **Date**: 2026-03-20 **Excerpt**: "Agent Sandbox is a sandbox orchestrator. It delegates low-level container isolation to secure 'Sandbox Runtimes' (like gVisor or Kata Containers)." **Confidence**: 高（官方）。

[^20^] **Claim**: GKE Agent Sandbox（GKE 1.35.2+/1.36 预览-GA 演进）：托管 gVisor（Autopilot 默认启用）；SandboxWarmPool 亚秒分配（称 300 沙箱/秒、<200ms）；Pod Snapshot 存内存+文件至 GCS 恢复；无额外计费（按 GKE 常规）。 **Source**: solo.io 分析 + boat.dev 对比 + shahvatsal 报道。 **URL**: https://www.solo.io/topics/ai-infrastructure/how-google-agent-substrate-works ; https://boat.dev/compare/boat-vs-gke-agent-sandbox **Date**: 2026-10-19 / 2026-10-14 **Excerpt**: "Agent Sandbox also ships a warm pool that can provision 300 sandboxes per second at sub-200ms latency, and Pod Snapshots to suspend idle agents and resume them in seconds." **Confidence**: 中高。

[^21^] **Claim**: Agent Substrate（开源，Google 系，K8s 之上）：每 actor 强制 gVisor 或 Cloud Hypervisor microVM（不支持普通容器）；空闲 actor 快照出内存，<500ms 恢复、>500 激活/秒、10x 容器密度（"Instant Session Teleport"）；per-actor SPIFFE X.509 短期证书 + egress 网关代铸 JWT；"Zero credentials in the sandbox"；默认全拒绝网络。 **Source**: GitHub agent-substrate/substrate README。 **URL**: https://github.com/agent-substrate/substrate **Date**: 2026-11-05 **Excerpt**: "fast resume operations in less than 500ms, with more than 500 activations per second... Sensitive credentials are kept out of reach from untrusted code." **Confidence**: 高（官方 README）。

[^22^] **Claim**: AWS Bedrock AgentCore Code Interpreter（2025-10-13 GA）：每会话独立 microVM（"compute-based session isolation"，暴露 MMDS 169.254.169.254）；Python/JS/TS；会话默认 15min 可延 8h；$0.0895/vCPU·h + $0.00945/GB·h 按秒、空闲/I-O 免费；CloudTrail/VPC/PrivateLink；2026 年 BeyondTrust/Sonrai 研究：sandbox 网络模式下 DNS 隧道可逃逸、MMDS 凭证可提取；两个 install_packages() RCE CVE（CVE-2026-16796/12530，修复于 1.18.1）。 **Source**: Ry Walker Research + BeyondTrust。 **URL**: https://rywalker.com/research/agentcore-code-interpreter ; https://www.beyondtrust.com/blog/entry/pwning-aws-agentcore-code-interpreter **Date**: 2026-06-11 / 2026-03-16 **Excerpt**: "a Firecracker microVM is real isolation and it held. What made code execution inside it valuable was the execution role... least privilege from the start." **Confidence**: 高。

[^23^] **Claim**: Blaxel hypervisor 未公开披露（一说 Firecracker）；7.5M+ agent 请求/日、16 区域（2025-07 融资时）；8GB 沙箱活跃约 $0.33/h。 **Source**: Ry Walker Research。 **URL**: https://rywalker.com/research/blaxel **Date**: 2026-06-11 **Confidence**: 中高。

[^24^] **Claim**: microsandbox（superradcompany，Apache-2.0，YC 支持）：libkrun/KVM microVM，README 宣称 <100ms 启动（Apple Silicon；第三方实测裸机 320ms）；嵌入式无 daemon、rootless；OCI 镜像兼容；"secrets that never enter the VM"；分叉/全状态快照；Rust/Python/TS/Go/Ruby SDK；beta 状态。 **Source**: glama MCP 目录 + beam 对比 + seminal.ai。 **URL**: https://glama.ai/mcp/servers/superradcompany/microsandbox ; https://www.beam.cloud/blog/how-to-self-host-code-sandbox **Date**: 2026-04/06 **Excerpt**: "Hardware Isolation... Average boot times under 100 milliseconds... Unexploitable secret keys that never enter the VM." **Confidence**: 中高（启动数字为自报，已标注）。

[^25^] **Claim**: Vercel Sandbox 2026-01-30 GA：Firecracker microVM 独立内核；默认镜像预装 Node 24/Python 3.14 及 Claude Code/Codex 等 agent；活跃 CPU 计费 $0.128/vCPU·h（I/O 等待免费，官方称突发负载省至 95%）；19 区域；24h 会话上限（Pro/Ent）。 **Source**: o-mega + boat.dev。 **URL**: https://o-mega.ai/articles/where-ai-agents-run-code-e2b-vs-modal-2026 ; https://boat.dev/compare/e2b-vs-vercel-sandbox **Date**: 2026-08-12 / 2026-10-14 **Confidence**: 高。

[^26^] **Claim**: OpenSandbox（阿里巴巴，Apache-2.0，~15.8k stars）：Docker/K8s/Firecracker 多后端、pause/resume、浏览器与桌面环境、Python/Java/TS/C#/Go SDK、MCP；为自建路线代表。 **Source**: simular.ai。 **URL**: https://www.simular.ai/alternatives/e2b-alternatives-for-ai-agents **Date**: 2026-10-13 **Confidence**: 中高。

[^27^] **Claim**: 分叉/快照已成为独立产品品类：Morph 分叉为核心（RL rollout/SWE-bench/树状探索）；PandaStack CoW fork 同机 400–750ms；Nebius Contree 文件系统级分支（每命令生成不可变快照）；Runtime（withruntime）Firecracker、243ms 中位启动、egress 代理+E2B 兼容。 **Source**: sandboxreview + forkast + awesome-ai-sandboxes。 **URL**: https://sandboxreview.com/posts/snapshot-and-fork-support-across-ai-agent-sandbox-providers ; https://github.com/tizkovatereza/awesome-ai-sandboxes **Date**: 2026-10-02 / 2026-05-27 **Confidence**: 中高。

[^28^] **Claim**: AWS Strands Box（2026-10 开发者预览）：OS 级隔离 + 开源策略语言 Dogwood；策略可基于动作内容与执行历史（有状态），如"测试通过才允许 push""限制 API 调用频率"；控制位于模型之外。另有社区 strands-bubblewrap（bwrap 后端，strands.sandbox.Sandbox 抽象自 1.43.0 起内置 DockerSandbox/SshSandbox）。 **Source**: InfoQ + GitHub strands-bubblewrap。 **URL**: https://www.infoq.com/news/2026/10/aws-strands-agents/ ; https://github.com/agent-of-mkmeral/strands-bubblewrap **Date**: 2026-10-16 **Excerpt**: "combines operating-system-level isolation with Dogwood, an open-source policy language that defines which actions an agent can perform... Developers can allow or deny actions based on their content and execution history." **Confidence**: 高。

[^29^] **Claim**: 2026-03 外部演示：Claude Code 可用路径技巧绕过自身 denylist；当 bubblewrap 拦截后，agent 自行禁用沙箱在沙箱外执行命令——证明应用层防护不足、需纵深防御。 **Source**: CCE 研究仓库（引外部公司演示）。 **URL**: https://github.com/Playful-Sincerity/CCE-Claude-Code-Entities/blob/main/research/2026-04-15-stream3-permission-first-safety.md **Date**: 2026-04-15 **Excerpt**: "When bubblewrap caught that, the agent disabled the sandbox itself and ran the command outside it." **Confidence**: 中（二手转述，但与 NVIDIA"agent 绕过应用层控制"的官方叙事互相印证）。

[^30^] **Claim**: 端侧/本地隔离带已有先行者但无成熟产品：Docker Sandboxes（每沙箱 microVM 独立内核 + 网络策略 + 凭证代理 + 文件夹级文件访问，面向单机开发者）；SmolVM（本地 computer use）；Anthropic srt 与 Codex 沙箱为 OS 原语级。 **Source**: helix.ml 对比 + shipengtao 综述。 **URL**: https://helix.ml/blog/self-hosted-agent-sandboxes ; https://shipengtao.com/en/agent-sandbox/ **Date**: 2026-08-31 / 2026-09-08 **Confidence**: 中高。

---

### 附：事实 vs 判断声明
- 第 1、2、5、6 节为事实性整理（数据均标注来源日期；凡"厂商自报"数字已注明）。
- 第 3 节趋势判断与第 4 节启发为基于上述事实的分析判断，已逐条标注【支持/挑战/需要修订】。
- 未解决的不确定性：Blaxel 的 hypervisor 未公开；Daytona 默认容器类的多租户安全模型缺乏具名隔离机制（infragap 已指出"应书面确认"）[^6^]；microsandbox 的 <100ms 为自报数据；Morph 的策略与凭证能力基本未公开。

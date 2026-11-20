# 安卓 Agent 沙箱洞察：形态、部署、框架支持、性能诉求与技术挑战

> **日期**：2026-11-15
> **性质**：独立的沙箱洞察文档，与汇报材料（[report/](report/README.md)、[ppt/](ppt/大纲.md)）并行，不替换其中任何章节。配套 PPT：[ppt/沙箱洞察/安卓Agent沙箱洞察.pptx](ppt/沙箱洞察/安卓Agent沙箱洞察.pptx)。
> **调研依据**：
> - 提示词：[notes/research-prompt-安卓Agent沙箱.md](notes/research-prompt-安卓Agent沙箱.md)。它既可以交给子 Agent，也可以直接交给其他模型使用。
> - 六份分项笔记：
>   - [AS1 云侧安卓沙箱形态与性能](notes/AS1-云侧安卓沙箱形态与性能.md)
>   - [AS2 x86 与 ARM 部署差异](notes/AS2-x86与ARM部署差异.md)
>   - [AS3 字节系方案与名称核实](notes/AS3-字节系方案与名称核实.md)
>   - [AS4 Agentic RL 框架的安卓环境支持](notes/AS4-AgenticRL框架的安卓环境支持.md)
>   - [AS5 手机侧 Agent 沙箱](notes/AS5-手机侧Agent沙箱.md)
>   - [AS6 论文与研究进展](notes/AS6-论文与研究进展.md)
> - 本库已有材料：
>   - [C2 沙箱框架与执行能力](C2-沙箱框架与执行能力.md)
>   - [沙箱实例开销汇总](notes/S-沙箱实例开销-汇总.md)
>   - [沙箱负载](notes/L-C2-沙箱负载.md)
>   - [沙箱商业价值讨论稿](discussion/沙箱-商业价值代价与定位.md)
> **主线程复核**：以下关键事实由主线程直接对过原文，没有只依赖子 Agent 的转述。
> - CubeSandbox 的 issue #1878，以及 PR #1879、#1880、#1881、#1882、#2031 的正文与状态（GitHub API，2026-11-15）。
> - Qwen-UI-Agent 把 MobileWorld 改建在 redroid 上的原文（arXiv 2607.28227 HTML 版）。
> - Google 在 LPC 2025 上讲 AVF Linux VM 的幻灯片原文。
> - AnBridge（DSN'26）的评测原文。
> - Napaxi 的 `docs/architecture.md`，以及 OpenMinis 的 `PRootKernel.kt`。
>
> **标注约定**：
> - 每个数字都标出口径，分为官方文档、官方基准、论文、源码、厂商自报、二手、估算。
> - 以「判断：」开头的句子是本文的分析结论。
> - 查不到的事实写「待核实」，不补写。
> - 引用编号 [Rn] 见文末参考资料。

---

## 0 摘要

1. **本文讨论的「安卓 Agent 沙箱」有三种用途，诉求差别很大。**
   - **云侧执行与云手机**：云端推理，云端安卓实例执行，产品形态是云手机、Mobile Use Agent。
   - **Agentic RL 训练环境**：成百上千个可快速重置的安卓实例，供 GUI Agent 做 rollout。
   - **手机本机执行**：在用户自己的手机上，给 Agent 一个与用户数据、其他应用隔离的执行环境。
   - 前两种的核心指标是密度、重置和吞吐，第三种的核心指标是隔离强度、常驻内存、存活与功耗。
   - 判断：云侧方案能直接迁移到手机的只有机制，例如快照、共享只读层、内存回收，产品形态不能直接搬过来。
2. **云侧安卓沙箱的形态正在从「KVM 模拟器」转向「容器化安卓（redroid）+ microVM + 真机补充」。**
   - 训练侧此前的主流是 x86 服务器上 Docker 化的 AVD。单实例超过 5 GB 内存、30 GB 存储；MobileRL 用 4 台 1 TB 内存的机器，只能稳定支撑 256 路并行 [R39]。
   - 2026 年阿里 Qwen-UI-Agent 把 MobileWorld 环境改建在 redroid 上。原文说明理由是 KVM 模拟器存在扩展瓶颈；整套基础设施支持超过 1 万个并发环境 [R42]。
   - 小米、vivo 的 GUI 模型则以真机为主。原因是商业应用普遍检测模拟器，账号态、支付认证和风控无法在模拟环境中复现 [R50][R51]。
3. **腾讯 CubeSandbox 正在把 redroid 接入 microVM，PR #1879 是第一块。**
   - #1879 于 2026-10-08 合入，只改两行：arm64 guest 内核开启 IPv6 与 PSI，安卓网络与 lmkd 依赖这两项 [R2]。
   - 母 issue #1878 列了 4 个阻塞点，后来又发现第 5 个（#2031）。截至 2026-11-15：
     - 2 个已合入：#1879、#1882；
     - 3 个仍开放：#1880 TCP 探针、#1881 镜像导入加固、#2031 关闭继承的 fd [R1]–[R6]。
   - 提出者自报的数字（arm64，4 vCPU / 8 GiB）：模板约 40 s 就绪，沙箱从快照恢复约 50 ms，adbd 可连。
   - 判断：这 5 个阻塞点都不是安卓特有的难题。它们说明通用沙箱平台默认面向「Linux 服务」，要承载「完整操作系统」需要放宽平台抽象。Cube 的安卓能力目前应表述为「社区贡献者推进中」，不能表述为「已支持」。
4. **用户点名的「字节方案」中，AgentEnv 与 DSec 都不是字节的。**
   - DSec 是 DeepSeek Elastic Compute（arXiv 2609.22978）。安卓在其中只是 QEMU 全虚拟机后端里的一句话，没有安卓专项数字 [R34]。
   - AgentENV 是月之暗面 Kimi 与 kvcache-ai 的 Firecracker microVM 环境平台，README 未提安卓 [R35]。
   - 字节自己对应的是：
     - UI-TARS-2 的「all-in-one GUI sandbox」，含 Android，规模为数千 VM 实例 [R30]；
     - 火山引擎云手机加 Mobile Use Agent [R19]；
     - 豆包手机。豆包手机的公开证据只有一条：它使用 `INJECT_EVENTS` 系统权限做跨应用模拟点击 [R37]。虚拟屏、推理位置均无官方说明。
5. **主流 Agentic RL 框架都不内置安卓环境，安卓由上层项目自行外挂。**
   - verl / verl-agent、slime、AReaL、ROLL 提供的是异步 rollout 和自定义环境接口 [R68]。
   - MobileRL、Android Coach 基于 verl，MAI-UI、ClawGUI 自建环境管理器 [R39][R44][R40][R46]。
   - 环境层已经普遍抽象为「reset / step / evaluate」形式的 HTTP 服务。
   - 判断：在训练规模上起决定作用的是下层的环境管理器和实例形态，不是 RL 框架本身。
6. **x86 与 ARM 的差别主要在「隔离形态能否部署」，而不在性能。**
   - x86 宿主：KVM 与嵌套虚拟化成熟，AWS 自 2026-02 起在 Intel 实例上提供嵌套虚拟化 [R27]。但运行 ARM 应用要靠 libndk_translation 或 Houdini。Google 的 ARM 翻译许可写明「不应用于商业托管服务」[R21]。
   - ARM 宿主：应用原生运行。但云上的 VM 级沙箱基本需要裸金属：Graviton 不支持嵌套虚拟化，KVM arm64 的 FEAT_NV2 从 Linux 6.11 起才进入内核 [R28][R29]。
   - redroid 要求宿主为 4 KB 页，而安卓生态正向 16 KB 页迁移 [R9][R25]。共享宿主内核的容器形态因此会被页大小限制，microVM 的 guest 可以自带内核。
7. **手机侧的现状：无特权的第三方方案隔离强度不足，系统级的强隔离尚未向第三方开放。**
   - **OpenMinis**：在安卓上用 PRoot 运行 Alpine Linux。PRoot 与宿主应用同 uid、同 SELinux 域，只改写路径视图，不构成安全边界 [R60]。
   - **Napaxi**（蚂蚁）：文档称其为「Trusted sandbox」，实际在安卓上同样是 PRoot，在 iOS 上是 QEMU 用户态模拟 [R61]。它的约束主要来自上层的工具准入闸门。
   - **AVF / pKVM**：是手机上唯一量产的 VM 级隔离，但有三个限制：
     - 第三方创建 VM 的权限没有官方说明；
     - Linux Terminal 依赖非保护 VM，芯片支持不全；
     - 屏幕关闭时 VM 被系统结束 [R63][R66][R67]。
   - **Google Computer Control**：只授予 OEM 预装的助手，在后台虚拟屏中操作应用。虚拟屏隔离的是显示与输入焦点，不隔离数据与权限 [R62]。
8. **性能数据在云侧集中于训练吞吐，在手机侧几乎空白。**
   - 云侧有可引用的数字：
     - Android Coach 测得模拟器交互耗时是模型推理的 1.7 倍 [R44]；
     - DistRL 的任务时长相差可达 100 倍，异步化后训练效率提升 3 倍 [R43]；
     - DSec 单节点最多 800 个 microVM 或 3,200 个容器 [R34]；
     - Anbox Cloud 用 Ampere Altra 加 2 块 T4，可跑 55 个 720p 容器 [R15]。
   - 手机侧找不到公开测量的项目：PRoot 的系统调用开销、Linux Terminal 的启动时间、后台虚拟屏的内存与 GPU 代价、手机上 Agent 沙箱的功耗。可引用的只有两项：
     - Google LPC 2025 的定性结论，即 PRoot 的 ptrace 开销显著 [R64]；
     - AnBridge 在 Pixel 7 Pro 上的实测：pVM 分配 250 MB 内存，跨 pVM 调用开销 2%–14% [R65]。
9. **技术创新集中在「少用环境、让环境便宜」，而不是「让单个安卓实例更小更快」。**
   - 「少用环境」包括：快照重置、环境与训练解耦的异步 rollout、单状态多动作（Android Coach）、用世界模型或模拟应用替代真实环境（WM-R1、PhoneWorld、OpenMobile-2）。
   - 「让环境便宜」包括：共享只读层、按需加载、DAMON 加 balloon 回收（DSec）、GUI 与 API / CLI 混合执行、批量动作。
   - 手机侧值得关注的工程创新是 Google 的 AVF Linux VM [R64]：
     - 内存气球与安卓应用生命周期联动，宿主应用退到后台时主动回收 guest 内存，避免被 LMK 结束；
     - gfxstream 经 AHB 实现零拷贝显示。
10. **对手机侧 Agent 沙箱的判断。**
    - 端侧可行的形态是「分档的会话沙箱」：
      - 低风险会话用进程级隔离（独立 uid、seccomp、出口代理）；
      - 需要完整 Linux 工具链时挂载用户态环境；
      - 高风险会话用 pVM；
      - GUI 任务由系统在后台虚拟屏中执行，并逐应用授权。
    - 这四档在手机上都有现成部件，但没有人把它们组织成统一的会话生命周期（创建、挂起、快照、恢复、销毁）。这与本库 [C2](C2-沙箱框架与执行能力.md) 的结论一致。
    - 本轮新增两点：
      - 云侧已经证明 redroid 加 microVM 快照可以做到约 50 ms 恢复（自报）；
      - Google 已经证明 VM 内存可以随应用生命周期回收。
    - 这两点都可以借到手机上，但需要在真机上重新测出口径。

---

## 1 范围与问题定义

### 1.1 三种用途

| 用途 | 安卓实例在哪运行 | 隔离要保护谁 | 代表方案 | 核心指标 |
|---|---|---|---|---|
| 云侧执行与云手机 | 云端服务器（x86 或 ARM） | 租户之间、宿主与实例之间 | 火山引擎云手机 + MUA、华为云 CPH、Anbox Cloud、CubeSandbox + redroid | 单机密度、启动与恢复、画面串流时延、单路成本 |
| Agentic RL 训练环境 | 云端集群 | 训练集群与环境之间；环境之间互不干扰 | UI-TARS-2 GUI 沙箱、MobileRL、MAI-UI、Qwen-UI-Agent、DSec | 并发数、重置时间、单步时延、长尾、环境稳定性 |
| 手机本机执行 | 用户自己的手机 | 用户数据、其他应用、系统，不受 Agent 的不可信执行影响 | OpenMinis、Napaxi、AVF Linux Terminal、Google Computer Control、豆包手机 | 隔离强度、常驻内存、启动与恢复、后台存活、功耗与发热 |

判断：前两种用途在云端运行，规模决定成本，所以关注密度与吞吐。第三种用途在手机上运行，手机内存已被前台应用和端侧模型占满，所以关注的是单个会话的增量代价，以及能否在后台活下来。

### 1.2 与本库已有沙箱调研的关系

- [C2](C2-沙箱框架与执行能力.md) 关注两件事：云侧代码执行沙箱（microVM、gVisor、容器），以及端侧的会话级执行管控（策略、凭证、出口、快照）。
- 本文关注「安卓环境本身作为沙箱」，补上 C2 没有展开的三块：
  - 安卓实例在云端怎么部署；
  - 训练框架怎么用安卓实例；
  - 手机本机上有哪些可用的隔离执行环境。
- 两份文档的结论在第 10 节汇合：端侧需要的是会话生命周期层，隔离单元可以分档选择。

### 1.3 名称与归属核实

用户把豆包手机、AgentEnv、DSec 都归为字节的方案。核实结果如下 [R34][R35][R36][AS3]：

| 名称 | 实际归属 | 形态 | 是否支持安卓 |
|---|---|---|---|
| 豆包手机 | 字节跳动与中兴努比亚 | 手机整机。系统级权限加 GUI 操作 | 本身运行在安卓上，但没有公开的隔离执行环境 |
| DSec | **DeepSeek**（DeepSeek Elastic Compute，arXiv 2609.22978，2026-09-19） | 统一 SDK，四类后端：FnCall、容器、Firecracker microVM、QEMU 全 VM | 支持，安卓放在 QEMU 全 VM 后端；论文没有安卓专项性能数字 |
| AgentENV（AENV） | **月之暗面 Kimi 与 kvcache-ai**（仓库 kvcache-ai/AgentENV，2026-07-23 创建，MIT） | Firecracker microVM，兼容 E2B API；快照恢复 <50 ms，内存超分 9.6 倍（厂商自报） | README 未提安卓或 GUI |
| LlamaTouch/AgentEnv | 学术项目，2024 年后无更新 | 把 AITW 格式的动作映射到安卓设备或模拟器 | 是。只是一个桥接层，不是沙箱 |

判断：没有找到字节名为 AgentEnv 或 DSec 的项目。混淆的原因可能是，DeepSeek、Kimi、字节在 2026 年都披露了 Agentic RL 的沙箱基础设施。三者的关系见第 3.3 节。

---

## 2 现状全景：形态谱系与部署方式

### 2.1 形态谱系

| 形态 | 代表 | 隔离边界 | 关键依赖 | 快照能力 | 典型用途 | 来源 |
|---|---|---|---|---|---|---|
| 容器（共享宿主内核） | redroid、Anbox Cloud 容器实例、Waydroid | 共享宿主内核，通常以 `--privileged` 启动；redroid 官方建议关闭宿主 SELinux | 宿主内核需有 binderfs、ashmem 或 memfd、IPv6、ION 或 DMA-BUF heap，且必须是 4 KB 页 | 弱。没有内存快照，只能做文件系统层复用 | 高密度云手机、云游戏、RL 环境（Qwen-UI-Agent） | [R8][R9][R15][R42] |
| 全虚拟机 | Cuttlefish（crosvm / QEMU）、Android Emulator（QEMU goldfish / ranchu）、Anbox Cloud VM 实例、DSec 的 QEMU 后端 | 独立 guest 内核 | 需要 KVM；云上需要嵌套虚拟化或裸金属 | Emulator 有 Quick Boot 快照；Cuttlefish 快照只支持 x86_64 加 SwiftShader 软渲染 | AOSP 测试、CTS、开发者调试、训练（AVD） | [R10][R11][R13][R34] |
| microVM 包容器 | CubeSandbox + redroid | Cloud Hypervisor 分叉加 KVM；redroid 作为 guest 内的容器，binder 由 guest 内核提供 | 宿主只需要 KVM；guest 内核需要自己维护 | 强。内存快照约 50 ms 恢复（自报） | 可快照复用的 Agent 安卓环境 | [R1]–[R6] |
| ARM 服务器或板卡阵列 | 华为云 CPH（鲲鹏）、火山引擎云手机、国内其他云手机 | 厂商未披露是容器还是 VM | 厂商自建 | 未披露（火山 OpenAPI 有实例重置接口） | 面向终端用户的云手机、挂机、游戏 | [R18][R19] |
| 真机农场 | Xiaomi-GUI-0、BlueLM-GUI、Qwen-UI-Agent 的 100 多台真机 | 物理设备 | 设备管理、健康调度 | 无，靠任务重置与重装应用 | 需要真实账号态、风控、支付的训练与评测 | [R50][R51][R42] |
| 用户态（路径虚拟化或指令集模拟） | OpenMinis（安卓 PRoot、iOS iSH）、Napaxi（安卓 PRoot、iOS QEMU 用户态）、Termux proot-distro | 与宿主应用同 uid、同 SELinux 域 | 无需特权 | 无 | 手机上给 Agent 一台能装软件的 Linux | [R60][R61] |
| 进程级 | `isolatedProcess`、seccomp、独立 SELinux 域 | 独立 uid 与 SELinux 域 | 系统或应用自行配置 | 无 | 受控计算：解析、脚本、插件 | [R70] C2 §3 Q6 |
| VM 级（手机） | AVF / pKVM：Microdroid、Linux Terminal | 保护 VM 的内存对宿主不可见；非保护 VM 为 KVM 级隔离 | ARM64、IOMMU、pvmfw；芯片厂商需开放对应 VM 类型 | 无量产的会话快照 | 敏感计算（生物识别、DRM）、Linux 终端 | [R63][R64] |
| 虚拟屏级（手机） | Google Computer Control、豆包手机（据第三方分析） | 只隔离显示与输入焦点 | 特权权限 | 无 | 系统助手在后台操作应用 | [R62][R37] |

判断：按隔离强度排序，全 VM ≈ microVM 包容器 > 容器 > 进程级 > 用户态。按「能否快照」这条轴，排序几乎相反：容器和用户态没有内存快照，全 VM 的快照受 GPU 限制，只有 microVM 路线把隔离与快照同时拿到了。

### 2.2 部署方式

| 部署方式 | 推理在哪 | 执行在哪 | 代表 | 状态 |
|---|---|---|---|---|
| 云端集中式 | 云 | 云端安卓实例 | 火山引擎 Mobile Use Agent、UI-TARS-2 训练、Qwen-UI-Agent 训练 | 量产（训练侧、云手机侧） |
| 端云协同 | 云（多数）或端 | 用户手机，由系统级权限操作真实应用 | 豆包手机、Google Computer Control、荣耀 YOYO、鸿蒙小艺 GUI 操作 | 量产或预览；除 Google 外，执行环境的隔离均无官方技术说明 |
| 端侧本机 | 自带模型（BYO model）或端侧模型 | 手机上的隔离环境 | OpenMinis、Napaxi、AVF Linux Terminal | 开源或预览，均为开发者向 |
| 云训练、端部署 | 端侧小模型 | 手机 | ClawGUI（覆盖 Android、HarmonyOS、iOS）、AutoDroid-V2（端侧解释器执行生成的脚本） | 学术与开源 |

来源：[R19][R30][R42][R37][R62][R60][R61][R64][R46][R56]。

判断：今天面向用户的手机 Agent 产品，几乎都走「端云协同、在真实系统上执行」。真正把 Agent 放进隔离环境的，只有面向开发者的开源项目和 Google 的 Linux Terminal。也就是说，「手机侧 Agent 沙箱」作为面向消费者的系统能力，还没有量产。

---

## 3 主要方案拆解

### 3.1 腾讯 CubeSandbox 的安卓路径（PR #1879 与 issue #1878 系列）

**背景。** CubeSandbox 是腾讯云开源的 microVM 沙箱，底座是 Cloud Hypervisor 的分叉加 KVM。

- 通用数据（官方基准）[R7]：
  - VMM 自身 PSS 约 5 MiB；
  - 纯净 Linux guest 的 RSS 为 156–193 MiB；
  - 多实例共享模板页后，每多一台，宿主净增 19–25 MiB；
  - 从快照拉起 50–65 ms，条件是服务器 NVMe、页缓存已热。
- 2026-09-30，贡献者 DualPhaseDev 提出 issue #1878，目标是让 redroid 镜像成为 Cube 模板。沙箱在 :5555 端口提供 adbd，用于设备农场、仪器化测试和云设备 [R1]。

**PR #1879 做了什么** [R2]：

- 只改 `configs/kernel-oc9.aarch64.config` 两行：
  - `CONFIG_IPV6` 从 `m` 改为 `y`；
  - 新增 `CONFIG_PSI=y`。
- 原因：Cube 的 guest 内核是不带模块的单一镜像，`=m` 等于没有 IPv6。安卓 guest 的网络需要 IPv6，lmkd 依赖 PSI。
- x86_64 的配置早已开启这两项，arm64 的配置已有 `CONFIG_ANDROID_BINDER_IPC=y`。
- 状态：2026-10-08 合入。提出者自述，用该内核构建的 redroid 模板可以进入就绪状态，沙箱恢复约 50 ms，adbd 可用。

**五个阻塞点与 PR 状态**（GitHub API，2026-11-15，主线程复核）：

| 阻塞点 | 现象 | 修复 | PR | 状态 |
|---|---|---|---|---|
| guest 内核缺 IPv6、PSI | 无 IPv6 时端口绑定间歇失败；lmkd 无法工作 | arm64 内核配置对齐 x86_64 | #1879 | 已合入（2026-10-08） |
| 强制 cgroup v2 | shim 无条件注入 `agent.unified_cgroup_hierarchy=true`，而 Android init 的 task_profiles 直接挂载 cgroup v1 控制器，模板构建陷入 apexd `reboot_on_failure` 循环 | `--cgroup-mode legacy`。修复链路是：CLI → CubeMaster 请求字段 → 沙箱 annotation → Cubelet 透传到 OCI spec → CubeShim 不再注入该参数。首版只在 CLI 提供 | #1882 | 已合入（GitHub 记录为 2026-11-16 UTC） |
| 就绪探针只支持 HTTP | adbd 是裸 TCP，HTTP GET 永远不成功 | `--probe-type tcp`、`--probe-timeout`、`--probe-initial-delay` | #1880 | 开放 |
| 镜像导入失败 | 在开启 SELinux 的主机上构建的镜像带 `security.selinux` xattr，导入时 setxattr 返回 EINVAL；Android 的 `/etc` 是指向 `/system/etc` 的符号链接，写 CA 证书时 MkdirAll 返回 EEXIST | 剥离 selinux xattr；把 CA 证书写入 Android 的 `system/etc/security/cacerts`，文件名用 subject-hash | #1881 | 开放 |
| zygote 遇到继承的 FIFO fd 中止 | agent 把日志转发管道继承给 guest init，zygote fork system_server 时报 `Unsupported st_mode ... FIFO` 并中止 | exec 前执行 `close_range(3, ~0U, 0)` | #2031 | 开放（2026-10-22 提出，不在 issue 原列的 4 项内） |

**示例模板规格**：

- 4 vCPU / 8 GiB 内存 / 10 GiB 可写层；
- 探针超时 600 s，因为完整操作系统启动慢。

**已知数字**：

- 模板约 40 s 就绪；
- 恢复约 50 ms；
- `getprop` 返回 Android 14。

以上均为贡献者自报，硬件未披露，也没有多实例密度、恢复后内存、截图通道的数据 [R1][R6]。

**其他事实**：

- 维护者在 issue 中回复「内部也在看安卓沙箱支持」，并建议增加 `examples/redroid/`，该目录截至本文仍不存在 [R1]。
- 所有端到端验证都在 arm64 上完成，x86_64 没有验证记录。

**判断：**

- **这 5 个阻塞点没有一个是安卓特有的难题。** cgroup 版本、探针类型、xattr、符号链接、继承的 fd，都源于通用沙箱平台默认承载「Linux 服务」，而不是「完整操作系统」。
  - 安卓沙箱要求平台把抽象从「运行一个服务进程」放宽到「启动一个操作系统」。
  - 体现在接口上，就是 TCP 探针、长启动窗口、按模板选择的 cgroup 模式。
- **50 ms 恢复的含义要说准。** 它指的是恢复到「adbd 可连接」，不等于应用已就绪、界面已稳定。
  - Cube 的 50–65 ms 是 Linux 轻量 guest 在热页缓存下测得的口径。
  - 8 GiB 配置的安卓实例，恢复后的实际工作集需要单独测。
- **Cube 路径的价值**：把宿主内核依赖（binder、ashmem、页大小）转移到 guest 内核，同时获得 microVM 的隔离和内存快照。代价是要自己维护一份面向安卓的 guest 内核配置。

### 3.2 字节跳动

**豆包手机（端侧执行）** [R37][R38][AS3]：

- **操作其他应用的方式**：官方回应称依赖安卓系统级权限 `INJECT_EVENTS` 跨应用模拟点击，该权限需用户授权并在权限清单中披露（经 IT之家转述，原页未能打开）。
- **未经官方确认的说法**：
  - 第三方分析称它还使用 `VirtualDisplay` 把目标应用放到虚拟屏，声明了 `CAPTURE_SECURE_VIDEO_OUTPUT`；
  - 推理在云端还是端侧、截图是否上传，没有可靠来源。
- **商业侧**（本库 D1 笔记）：
  - 一代发布后 48 小时内，即遭微信、淘宝、支付宝、银行等应用限制；
  - 二代 2026-09 开售，仍有 150 余款应用拒绝 GUI 自动化；
  - 关于新版是否转向应用方提供 MCP，2026-07 与 2026-09 的报道互相冲突。
- 判断：豆包一代的「沙箱」是权限边界，不是执行隔离。Agent 以系统权限，在用户的真实系统上操作真实应用，没有看到独立的 VM 或独立用户空间。

**UI-TARS-2 的训练沙箱** [R30]：

- **形态**：自建分布式 VM 平台，运行 Windows、Ubuntu 和 Android，集成 PyAutoGUI 与 ADB。统一 SDK 覆盖 VM 分配、初始化、交互、观测（截图、录屏）和任务评估。
- **规模**：VM 集群为「数千实例」，VM Manager 承载「数千 QPS」。
- **生命周期**：基于租约（lease）回收，超时的会话被回收；可通过 VNC / RTC 实时观看。
- **训练侧**：全异步的服务式推理，加上有状态环境和部分填充的 rollout 池，用来缓解长尾。
- **未披露**：安卓实例是模拟器、容器还是云手机；重置方式；单步时延。UI-TARS-2 只说明了平台能力的量级，不能当作安卓沙箱性能的来源。

**通用沙箱与 RL 框架** [R31][R32][R33]：

- AIO Sandbox（agent-infra/sandbox，v1.11.0）：单个 Docker 容器，集成浏览器、终端、VSCode、Jupyter、MCP。
- SandboxFusion：代码执行与评测。
- veRL：提供多轮工具调用和 Sandbox Fusion 集成。
- 三者都没有安卓。

**火山引擎云手机加 Mobile Use Agent** [R19]：

- 是字节实际的安卓环境产品，属于商业云服务。
- OpenAPI 包括截图（单张或批量）、录屏、文件推拉、ADB 隧道、实例重置。
- API 示例中，规格 g2.8c12g 可切分为 1 到 6 开，这是示例值，不一定对应真实售卖规格。
- 容器还是 VM、ARM 还是 x86，文档目录中未展开，待核实。

判断：字节的 Agent 沙箱分两条线。代码与浏览器类走容器（AIO Sandbox、SandboxFusion），安卓类走云手机产品。两条线之间没有统一的 microVM 层。

### 3.3 DeepSeek DSec 与 Kimi AgentENV

**DSec** [R34]：

- **规模**：
  - 生产单元约 160 个节点，日均约 300 万个沙箱；
  - 峰值并发超过 38 万，创建速率超过 5,000 次每秒；
  - 单节点最多 800 个 microVM 或 3,200 个容器，依赖过量分配。
- **存储**：
  - 环境由版本化的只读 EROFS 层组合而成，镜像经 3FS 按需加载；
  - 8,192 个容器突发创建时，按需加载约 35 分钟完成，传统 eager pull 超过 60 分钟，快 1.71 倍；磁盘写入减少约 57%。
- **内存**：microVM 用 virtio-pmem 加 DAX 共享只读层；DAMON 加 virtio-balloon free-page reporting 使内存消耗降低 21.2%。
- **寿命**：沙箱寿命中位数，容器 17.4 分钟，microVM 15.5 分钟；P99 都超过 3 小时。
- **安卓**：只出现在「QEMU 全 VM 后端支持 Android VM」一句话里，GPU 走 virtio-gpu 半虚拟化。论文的性能测量不含安卓。

**AgentENV** [R35]：

- Firecracker microVM，兼容 E2B API，要求 Linux 6.8 以上与 `/dev/kvm`；
- 快照恢复小于 50 ms，暂停小于 100 ms，内存超分 9.6 倍，支持 fork（均为厂商自报，条件未给）；
- 镜像规模 150 万（引自 Kimi K3 报告）；
- 没有安卓。

判断：DSec 是公开资料中少有的、在统一平台里把安卓放进全 VM 后端的 RL 沙箱。但它把安卓当作开销最高的长尾类别，量产主力是容器与 microVM。两者的快照、超分、按需加载机制都还没有与安卓实例结合。Cube 的 redroid 加 microVM 正好落在这个空白上。

### 3.4 其他大厂的训练环境

| 厂商与项目 | 安卓环境形态 | 规模 | 重置与容错 | 来源 |
|---|---|---|---|---|
| 阿里 Qwen-UI-Agent（2607.28227，2026-07） | 原文：「为解决基于 KVM 的模拟器的扩展瓶颈，把 MobileWorld 环境改建在 redroid 上；Android 作为容器运行在宿主内核上，不需要 QEMU 或嵌套 KVM」；另有 100 多台真机、150 多个应用，用虚拟屏让一部手机并行多个 App | 超过 1 万个并发环境 | 统一接口 acquire / reset / step / evaluate / tear_down / release，租约式会话；健康感知调度、不健康设备黑名单 | [R42]（主线程复核原文） |
| 阿里通义 MAI-UI（2512.22047） | Docker 化的 root AVD，加自托管后端和 REST API | 10 台 ECS 裸金属，最多 512 并发；并行环境从 32 增到 512，成功率从 65.5% 升到 70.7% | AVD snapshot 初始化；容器重置后复用，不销毁；备用池故障替换 | [R40] |
| 阿里 Mobile-Agent-v3 / GUI-Owl（2508.15144） | 阿里云云手机加云电脑 | 未披露 | rollout 与更新完全解耦 | [R41] |
| 智谱 MobileRL（2509.18119） | Docker 化 AVD | 声称可编排 1,000 个以上；实际稳定上限 256 路，用 4 台 1 TB 内存的 CPU 机器 | 未详述；训练每步超过 10 分钟，100 步超过 25 小时 | [R39] |
| 智谱 AndroidLab、AgentRL | 预打包 AVD 镜像；容器化环境加集中控制器 | AgentRL 称管理「数千」个并行 episode | AVD 镜像预置状态；协程异步 | [R49][R47] |
| 小米 Xiaomi-GUI-0（2606.31410） | 以真机为主、沙箱为辅，覆盖手机、平板、车机 | 未披露 | 动因是反模拟器检测、账号态、权限弹窗、支付认证、风控 | [R50] |
| vivo BlueLM-GUI（2609.12394） | 数百台真机上做 agentic RL | 数百台 | 强调沙箱训练与生产环境的分布不一致 | [R51]（只读了摘要；机构归属为推断） |
| 腾讯混元 HyMobileAgent（2607.14548） | 2000 多个沙箱与真机实例；34 个 mock 应用 | 2000 多个 | 自动失败归因 | [R52]（只读了摘要） |
| 蚂蚁 UI-Venus（2508.10833） | 「几十台手机的虚拟云环境」 | 数十台 | 未披露 | [R69] |

判断：2026 年大厂的分工已经比较清楚。**规模由容器化安卓（redroid）承担，真实性由真机承担，模拟器只用于中小规模研究。** 训练侧的安卓环境从「每实例 5 GB 以上的 AVD」走向「容器化」，正是为了绕开模拟器的内存与 KVM 限制。

### 3.5 OpenMinis

OpenMinis 是 GPLv3 开源的端侧 Agent 应用，模型由用户自带（BYO model）[R60]。

| 项 | 内容 | 等级 |
|---|---|---|
| 沙箱实现 | 安卓：PRoot（自有分叉）。命令为 `proot -0 --link2symlink -r <Alpine rootfs> -b /dev -b /proc -b /sys ... --fake-netlink`，每条命令起一个新的 proot 进程。iOS：iSH 的 ARM64 分叉 | 源码（主线程复核 `PRootKernel.kt`） |
| rootfs | Alpine 3.21.3 aarch64 minirootfs，打进 APK，首次启动时解压；构建脚本只用 curl 下载，没有校验和 | 源码 |
| 隔离边界 | 与宿主应用同 uid、同 SELinux 域（untrusted_app）。PRoot 用 ptrace 拦截系统调用、改写路径，没有 namespace、cgroup，也没有独立的 SELinux 域 | 源码 + 判断 |
| 设备能力 | 无障碍、Shizuku、日历、联系人、相册、浏览器等，经 `--native-offload` 由抽象 unix socket 交给宿主进程执行，不在沙箱内 | 源码 |
| 权限面 | Manifest 申请 29 项权限，含 `MANAGE_EXTERNAL_STORAGE`、`SYSTEM_ALERT_WINDOW`、`REQUEST_INSTALL_PACKAGES`、Shizuku API，并声明了无障碍服务 | 源码 |
| 体积 | arm64 APK 47.58 MB（build 44，2026-11-15） | 厂商自报 |
| 兼容性补丁 | `--link2symlink` 应对 /data 拒绝跨目录硬链接；`--fake-netlink` 应对 untrusted_app 不能建 NETLINK_ROUTE；`PROOT_NO_SECCOMP=1` 重试应对某些 ARM64 机型在 ptrace 加 seccomp 下 SIGBUS / SIGSEGV（GH#186） | 源码 |
| 安全重试策略 | 只有同时满足四个条件才重试一次：致命信号、1.5 s 内退出、无输出、未重试过。SIGKILL 和 SIGTERM 不重试，因为它们可能来自超时、取消或 LMK | 源码 |
| 性能 | PRoot 的系统调用开销没有公开测量 | 待核实 |

判断：OpenMinis 的取舍是「给模型一台能装软件的 Linux」，隔离靠应用沙箱，危险的设备能力在宿主侧用权限管理。它的价值在于说明「手机上的 Agent 能做到什么」，而不是提供隔离样本。

### 3.6 Napaxi（蚂蚁集团）

Napaxi 是嵌入宿主 App 的端侧 Agent SDK，用 Rust 编写，GPL-3.0；SDK 1.0 于 2026-07-02 发布 [R61]。

| 项 | 内容 | 等级 |
|---|---|---|
| 分层 | 宿主 App → SDK 适配层（Flutter / Android / iOS）→ FFI 桥 → `napaxi_core` Rust 运行时 → 特性 crate → Android PRoot 或 iOS QEMU 平台环境 | 官方文档（主线程复核 `docs/architecture.md`） |
| 「Trusted sandbox」的实现 | 安卓：PRoot 加 Alpine aarch64 rootfs。iOS：QEMU `aarch64-linux-user` 静态库（仓库内 41.8 MB），用户态模拟。不是 WASM、QuickJS 或 seccomp | 源码 |
| 隔离内容 | `env_clear()` 清空宿主环境变量；只绑定 `/workspace`、`/skills` 和 `/proc /dev /sys`；超时钳位在 1–600 s；先 SIGTERM，宽限 2 s 后 SIGKILL | 源码 |
| 强约束来源 | 上层四处闸门：工具描述符准入、工具调用准入、provider 准入、模型切换。外部权限由宿主 App 决定是否暴露 | 官方文档 |
| 预装 | Python、Node、git、OpenJDK 17、Codex CLI、Android APK 构建工具，以及经 qemu-x86_64 运行的 x86_64 工具（aapt2 等） | 源码 |
| 典型负载 | 在 PRoot 里用 PTY 启动 `codex app-server`，演示「在手机上生成、构建、安装 APK」 | 官方文档 |
| 已承认的缺口 | 路线图写明当前没有「secret egress proxy」，相关检查要等该能力落地后再做 | 官方文档 |
| 性能与体积 | 无公开数值；rootfs 资产在仓库中是 Git LFS 指针 | 待核实 |

判断：Napaxi 与 OpenMinis 用的是同一类沙箱。这说明在无特权的第三方应用里，「给 Agent 一台 Linux」目前只有 PRoot 或 QEMU 用户态这一条现实路径，隔离强度等同于应用沙箱。Napaxi 多做的一步，是把「是否把权限交给 Agent」留给宿主应用，并在 SDK 内设置准入闸门。

### 3.7 Google：AVF Linux Terminal 与 Computer Control

**AVF Linux Terminal**（LPC 2025，Google，主线程复核幻灯片原文）[R64]：

- **定位**：AVF 主要为保护 VM 设计，用于生物识别、KeyMint、DRM 等敏感负载，资源用量小且严格受控。这次是第一次评估 AVF 能否承载通用计算。
- **为什么不用用户态方案**：原文列了三点：
  - 安卓的 Bionic libc 不能直接运行 glibc 程序；
  - PRoot 依赖 ptrace 做系统调用转换，开销显著；
  - 共享内核有局限。
  - 结论是需要完整的 VM。
- **架构**：
  - 非保护 VM 跑 Debian；终端界面是 WebView 里的 xterm.js 加 guest 内的 ttyd，用双向 TLS 认证；
  - 设备有 virtio-blk、virtio-input、virtio-gpu、virtio-net、virtio-fs，其中 virtio-fs 映射 `/sdcard`。
- **生命周期与资源**：
  - 内存气球与安卓应用生命周期联动。宿主应用退到后台时主动回收 guest 内存，避免被 LMK 结束；
  - 磁盘气球按宿主可用存储调整；
  - guest 内的 eBPF 探测 `bind()`，自动建立 vsock 端口转发。
- **图形**：
  - 最初用 lavapipe 加 Zink 软渲染，CPU 占用高、帧率低；
  - 现改为 gfxstream 硬件加速，为此新写了基于 AHB（Android Hardware Buffer）的安卓宿主后端；
  - 解决了 ARM 上宿主与 guest 之间缓存一致性导致的画面损坏；
  - 用 SurfaceControl Transaction 实现从 guest 渲染到显示的零拷贝。
- **机型与使用限制**（二手与个人实测）[R66][R67]：
  - Linux Terminal 需要非保护 VM。报道称 Snapdragon 8 Elite 只支持保护 VM，Galaxy Z Flip 7（Exynos 2500）是首个非 Pixel 支持机型；
  - 个人实测，Android 17 上 VM 默认内存 1024 MiB，屏幕关闭时 VM 被结束，除非打开 Keep awake；
  - 第三方应用能否持有 `MANAGE_VIRTUAL_MACHINE`，官方文档没有写 [R63]。

**AnBridge**（DSN'26，那不勒斯大学、巴黎电信、普渡大学）[R65]：

- 目标：把端侧 AI 的原生代码迁进 pVM（Microdroid）保护，并通过 Binder 加 vsock 的中间件回调宿主 Java。
- 设备与配置：Pixel 7 Pro（11 GB 内存，Android 14，内核 5.10）；pVM 分配 250 MB 内存。
- 结果：
  - pVM 内原生代码调用宿主 Java 函数，开销 2%–14%；
  - Binder 单次最多传约 40 KB，超过后走 vsock，vsock 的固定开销约 800 µs；
  - pVM 通过 virtio 读文件的吞吐为 74 MB/s，经 AnBridge 访问宿主存储可达 167 MB/s。
- 判断：这是本轮唯一找到的、在量产手机上测 pVM 跨边界开销的论文。开销不大，但前提是负载能适应 pVM 的编程模型。

**Computer Control**（官方文档，预览）[R62]：

- **授予对象**：OEM 预装的助手，持特权权限 `ACCESS_COMPUTER_CONTROL`。
- **执行方式**：目标应用在「安全的后台虚拟屏」上启动，助手截屏并模拟点击、滑动、文本输入。
- **约束**：
  - 首次操作某个应用时，系统弹窗请求授权；
  - 交易确认等步骤，把控制权交还用户；
  - 一个会话最多 6 个目标应用，同一时间只有 1 个会话。
- 判断：虚拟屏隔离的是显示与输入焦点，不隔离数据与权限，目标应用仍以用户身份在用户数据上运行。这是「不打扰前台」，不是「防止 Agent 越权」。Google 的防护来自另外三件事：特权权限只给预装助手、逐应用授权、敏感步骤交还用户。

### 3.8 云手机产品与 Anbox Cloud

- **Anbox Cloud**（Canonical）官方基准 [R15]：
  - Ampere Altra 加 2 块 T4，硬件渲染与编码：720p 下 55 个容器、29 FPS；1080p 下 50 个、26 FPS；
  - AWS g5g.metal：720p 下 55 个、28 FPS；
  - 纯软件渲染与编码：m6g.2xlarge（ARM，8 vCPU）只能稳定 3 个、20 FPS；m5a.2xlarge（x86）3 个、13 FPS。
  - 文档说明：VM 实例不支持 GPU；同一 LXD 集群的所有节点必须同一架构 [R16][R17]。
- **华为云 CPH**：基于鲲鹏 ARM 服务器，原生应用无需指令转换。官方称相对 x86 模拟器方案「最高提升 80%」，并称 x86 模拟器方案有「至少 50% 性能损失」。两个数字都没有给基线 [R18]。

判断：容器形态的密度由 GPU 与编码能力决定，不由 CPU 决定。但 GUI Agent 只需要按需截图，不需要 30 fps 视频流。所以 Agent 沙箱可以接受软渲染，用较低帧率换取快照能力和密度。Cuttlefish 只在软渲染下支持快照，这一约束因此对 Agent 场景影响不大。

---

## 4 Agentic RL 框架对安卓沙箱的支持

### 4.1 通用框架

| 框架 | 机构 | 内置安卓环境 | 异步 rollout | 与环境的对接方式 | 来源 |
|---|---|---|---|---|---|
| veRL | 字节（火山引擎） | 否 | 有（AgentLoop、多轮工具调用） | 客户端对接，有 Sandbox Fusion 集成示例 | [R33] |
| verl-agent | 社区（基于 veRL） | 否。内置 ALFWorld、WebShop、Sokoban、AppWorld 等 | README 列为可贡献的想法 | 并行 Gym 式环境 | [R68] |
| slime | 智谱 THUDM | 否 | 有（fully_async 示例，针对长尾） | 自定义 generate 函数可封装沙箱 | [R68] |
| AReaL | 蚂蚁与清华 | 否 | 有，全异步；2.0 为微服务架构 | agent service | [R68] |
| ROLL | 阿里 | 否 | 有，环境级异步并行 | 对齐 GEM 环境定义 | [R68] |
| AgentRL | 智谱 THUDM | 论文引用 AndroidLab | 有，协程式全异步 | 函数调用式统一 API、每任务一个容器、集中控制器 | [R47] |
| DSec | DeepSeek | 有（QEMU 全 VM） | 支持，抢占后可恢复 | 统一 SDK，与训练框架显式集成 | [R34] |
| AgentENV | Kimi 与 kvcache-ai | 未提 | — | 兼容 E2B API | [R35] |

注：以上「否」来自各仓库 README 首页，未逐一翻查示例目录。OpenRLHF 本轮未覆盖。

### 4.2 GUI 与手机 Agent 训练项目

| 项目 | 环境形态 | 并发 | 单实例资源 | 重置 | 来源 |
|---|---|---|---|---|---|
| MobileRL | Docker 化 AVD，基于 verl | 稳定 256（声称 1,000 以上） | 超过 5 GB 内存、超过 30 GB 存储 | 未详述 | [R39] |
| MAI-UI | Docker 化 root AVD | 最多 512 | — | AVD snapshot + 容器复用 + 备用池 | [R40] |
| Qwen-UI-Agent | redroid 容器 + 100 多台真机 | 超过 1 万（含非安卓环境） | — | 租约式会话 | [R42] |
| ClawGUI-RL | Docker 模拟器 + 真机 / 云手机，统一接口 | 训练时 64 个并行虚拟环境 | — | 每个 episode 重置任务；备用 server 轮换 | [R46] |
| Generalization in Online RL（2603.07432） | 容器内 Android 13 模拟器 + HTTP server | 16 | 16 GB 内存、6 vCPU | 每环境一个容器，配额相同，防止掉队 | [R45] |
| Android Coach | 并行 Android 13 模拟器，基于 verl | 8 | — | 未详述 | [R44] |
| DistRL | 工作机上的模拟器或真机 | 32 个模拟器（192 vCPU） | — | Environment Snapshots | [R43] |
| AndroidWorld | 单个 AVD（Pixel 6，API 33） | 官方不支持真正的并发 | 官方标称 2 GB 内存、8 GB 磁盘 | 任务自带 setup | [R48] |

### 4.3 读表结论

- **框架不管安卓。** 通用 RL 框架把环境抽象成「HTTP 服务 + reset / step / evaluate」，安卓只是其中一种后端。决定规模的是下层的环境管理器，例如 MAI-UI 的 Environment Manager、DSec、Qwen-UI-Agent 的统一接口。
- **规模跨了两个数量级。**
  - AVD 路线停留在 256–512 路，原因是单实例 5–16 GB 内存；
  - redroid 路线达到万级；
  - 真机路线是几十到几百台。
- **重置没有秒级数字。** 所有被检索的论文都没给出以秒计的重置时间，也没给出「截图 + 推理 + 动作」的单步时延分解。这是公开资料中最大的缺口。
- 判断：「环境即服务」的接口已经收敛，各家的差别在实例形态与重置机制。microVM 内存快照（Cube 约 50 ms 恢复、AgentENV 小于 50 ms）和安卓实例的结合，是训练侧下一步最可能出现的优化。

---

## 5 虚拟化支持与手机支持

### 5.1 云侧

| 能力 | x86 | ARM | 来源 |
|---|---|---|---|
| KVM | 成熟 | 成熟 | — |
| 公有云嵌套虚拟化 | AWS 自 2026-02 起提供，限 Intel 实例（C8i / M8i / R8i，2026-06 扩展到 C7i、M7i、X8i 等）；L1 只支持 KVM 与 Hyper-V；对性能敏感的负载，AWS 建议用裸金属 | AWS Graviton 不支持（二手）；KVM arm64 的 FEAT_NV2 嵌套支持在 Linux 6.11 合入（二手）；Arm 官方路径要求 6.13 以上、裸金属、`kvm-arm.mode=nested` | [R27][R28][R29] |
| 容器形态（redroid） | 普通云 VM 即可 | Graviton4 c8g.large（2 vCPU / 4 GB）普通 VM 即可 | [R24] |
| 全 VM（Cuttlefish） | `aosp_cf_x86_64_phone` | `aosp_cf_arm64_only_phone`；真正的 16 KB 页测试只能在 ARM64 宿主上做 | [R11][R12] |
| Android Emulator | 不能在另一个 VM 里运行带 VM 加速的模拟器 | arm64-v8a 镜像可在 ARM64 宿主上加速 | [R14] |

### 5.2 手机侧

| 能力 | 现状 | 来源 |
|---|---|---|
| pKVM / AVF | 手机上唯一量产的 VM 级隔离，限 ARM64。保护 VM 的 guest 内存从宿主取消映射；需要 IOMMU、pvmfw、DICE | [R63] |
| 机型覆盖 | 没有官方机型清单。Linux Terminal 需要非保护 VM，Snapdragon 8 Elite 只支持保护 VM（二手）；联发科机型走 GenieZone（社区资料） | [R66]；C2 §3 Q6 |
| 第三方能否创建 VM | `MANAGE_VIRTUAL_MACHINE`、`USE_CUSTOM_VIRTUAL_MACHINE` 的持有规则，官方架构页没有写 | [R63] |
| 资源 | Microdroid 最小内存量级 32–42（疑为 MB，C 级）；AnBridge 给 pVM 分配 250 MB；Terminal 默认 1024 MiB | C2 §2；[R65][R67] |
| 生命周期 | Terminal：屏幕关闭时 VM 被结束（个人实测）；内存气球随应用前后台回收（Google 官方幻灯片） | [R67][R64] |
| 跨边界开销 | AnBridge：pVM 原生代码调用宿主 Java，开销 2%–14% | [R65] |
| 图形 | gfxstream 加 AHB 后端，零拷贝显示（Google 官方幻灯片）；是否已在 Android 17 稳定版落地，待核实 | [R64] |
| 系统级 GUI 执行 | Computer Control：特权权限、后台虚拟屏、每会话 6 个应用、同时 1 个会话 | [R62] |
| iOS | 第三方拿不到比 App 沙箱更细的边界；OpenMinis、Napaxi 只能用 iSH 或 QEMU 用户态模拟 | C2 §3 Q6；[R60][R61] |

### 5.3 判断

1. **云侧的问题是「能不能部署」，手机侧的问题是「谁能用」。** 云侧在 x86 上，各种形态都能部署；在 ARM 上，VM 形态要裸金属。手机侧 VM 能力已经存在，但只对系统和 OEM 开放，而且受芯片支持的 VM 类型限制。
2. **手机上 VM 的生命周期与 Agent 的诉求冲突。** Agent 的价值在于用户不看屏幕时继续执行，而 Terminal 的 VM 在屏幕关闭时被结束。Google 的内存气球联动是正确方向：后台时缩小，而不是被结束。但它还没有延伸到「挂起到闪存、恢复时按需换入」的会话快照。
3. **pVM 的跨边界开销可以接受，编程模型才是门槛。** AnBridge 的 2%–14% 说明，性能不是阻止 Agent 工具进 pVM 的主因；工具代码要按 pVM 的接口改写，才是主因。

---

## 6 x86 与 ARM 部署差异与技术挑战

### 6.1 对照表

| 维度 | x86 宿主 | ARM 宿主 | 来源 |
|---|---|---|---|
| ARM 应用 | 依赖翻译层：AOSP x86 镜像与 ChromeOS 用的 libndk_translation，或 Intel Houdini；redroid 官方镜像已内置 libndk_translation。Google 官方 ARM 翻译只用于开发调试，「不应用于商业托管服务」。注：AOSP Berberis 是 riscv64→x86_64，不做 ARM 翻译 | 原生运行，无需翻译 | [R21][R22][R8] |
| 翻译层性能 | 官方没有基准。华为称 x86 模拟器方案「至少 50% 性能损失」（厂商自报，无基线） | — | [R18] |
| 虚拟化 | KVM 与嵌套虚拟化成熟，普通云 VM 上可起 microVM | 容器可在普通 VM 上运行；microVM 与全 VM 基本要裸金属 | [R27][R29] |
| 页大小 | 4 KB 为主 | 服务器发行版可能默认 64 KB（背景知识，待核实）；redroid 要求 4 KB；Android 15 起支持 16 KB 页，Play 要求目标 API 35 以上的应用自 2027-02-01 起支持 16 KB 页 | [R9][R25] |
| GPU | NVIDIA、AMD、Intel，文档覆盖完整 | 多数 ARM 服务器没有 GPU，只能软渲染；AWS G5g（Graviton2 + T4G）称每路游戏流成本最多低 30%（厂商自报） | [R17][R23] |
| 应用完整性 | Play Integrity 依据硬件级证明，与 CPU 架构无关；模拟器不通过检查时返回空结果 | 同左，ARM 服务器并不因为是 ARM 就能通过 | [R26] |
| 成本与密度 | 没有找到同口径的公开对比 | 同左 | [AS2] |

### 6.2 技术挑战

1. **翻译层同时受授权与覆盖率约束。** x86 云手机厂商要用自有或第三方翻译层，覆盖率和性能损失都没有公开数据。判断：这是 x86 路线最大的非技术约束。
2. **ARM 上 VM 形态的部署弹性差。** 没有嵌套虚拟化，microVM 沙箱只能在裸金属上运行，扩缩容要以整机为单位。CubeSandbox 的安卓验证全在 arm64 上，部署时要以裸金属为前提（判断）。
3. **页大小冲突将在 2027 年前后显现。** 容器形态的 redroid 共享宿主内核，被固定在 4 KB 页。要测试 16 KB 页设备上的应用，需要 guest 自带内核的 microVM 或全 VM。判断：这是「容器还是 microVM」选型中一个实质性的变量。
4. **GPU 与快照不能兼得。** Cuttlefish 只在 SwiftShader 软渲染下支持快照，Anbox Cloud 的 VM 实例不支持 GPU。要同时得到 VM 级隔离、GPU 和快照，目前没有官方路线。
5. **强风控应用在两种架构上都可能失败。** 银行、支付类应用依赖硬件证明与反模拟器检测，x86 翻译与 ARM 服务器都难以通过（推断，没有实测）。这类任务只能交给真机或真机云手机。

### 6.3 选型判断

| 负载 | 倾向 | 理由 |
|---|---|---|
| RL rollout（快照、秒级重置、大规模并发） | x86 上的容器或 microVM；需要 ARM 原生时用 ARM 裸金属 | KVM 与嵌套成熟；训练自用不涉及「商业托管」 |
| 面向终端用户的云手机 | ARM 容器或板卡 | 原生兼容；避开翻译层授权限制 |
| 兼容性测试 | 以 ARM 原生为主，x86 翻译为辅 | Google 自己也不建议用翻译替代真机 |
| 手机本机 | 天然是 ARM，没有翻译问题；虚拟化入口只有 pKVM / AVF | 见第 5.2 节 |

判断：「x86 还是 ARM」本质上是隔离形态的选型，不是性能的选型。要 VM 级隔离加快照，选 x86 或 ARM 裸金属；要原生应用兼容加低成本，选 ARM 容器。

---

## 7 性能诉求

### 7.1 指标体系

| 指标 | 含义 | 云侧训练关心 | 云手机关心 | 手机本机关心 |
|---|---|---|---|---|
| 创建 / 启动 | 从无到可执行第一条命令 | 是 | 是 | 是 |
| 重置 | 回到任务初始状态 | **核心** | 是 | 否 |
| 快照恢复 | 从挂起状态恢复到可执行 | 是 | 是 | **核心**（用户切回、内存压力后） |
| 单实例常驻内存 | 空闲时占用的物理内存 | 决定密度 | 决定成本 | **核心**（与前台应用、模型争用） |
| 单机密度 | 同一台机器同时承载的实例数 | **核心** | **核心** | 只需 1–3 个 |
| 单步时延 | 截图、编码传输、推理、动作注入、界面稳定 | 决定吞吐 | 决定体验 | 决定体验 |
| 长尾 | 慢任务对整体的拖累 | **核心** | 否 | 否 |
| 后台存活 | 屏幕关闭、内存压力下不被结束 | 否 | 否 | **核心** |
| 功耗与发热 | 持续执行时的电量与温度 | 否 | 否 | **核心** |

### 7.2 已知量级

| 指标 | 数值 | 条件 | 等级 | 来源 |
|---|---|---|---|---|
| AVD 单实例 | 超过 5 GB 内存、超过 30 GB 存储 | MobileRL，Docker 化 AVD | 论文 | [R39] |
| AVD 单实例配置 | 16 GB 内存、6 vCPU | 2603.07432，Android 13 | 论文 | [R45] |
| redroid 单实例配置 | 4 vCPU / 8 GiB / 10 GiB 可写层 | Cube 示例模板 | 贡献者自报 | [R1] |
| Linux microVM 单实例 | guest RSS 156–193 MiB；每多一台净增 19–25 MiB | Cube，纯净 Linux guest | 官方基准 | [R7] |
| 手机 pVM | 250 MB | AnBridge，Pixel 7 Pro | 论文 | [R65] |
| 手机 Terminal VM | 默认 1024 MiB | Android 17，Pixel | 二手（个人实测） | [R67] |
| redroid 模板就绪 | 约 40 s | Cube，arm64 | 贡献者自报 | [R1] |
| redroid 快照恢复 | 约 50 ms | Cube，恢复到 adbd 可连 | 贡献者自报 | [R1][R2] |
| Linux microVM 快照恢复 | 50–65 ms；暂停加恢复约 220 ms | Cube v0.7.3，服务器 NVMe、热页缓存 | 官方基准 | [R7] |
| Firecracker 快照恢复 | 小于 50 ms | AgentENV，非安卓 | 厂商自报 | [R35] |
| 模拟器快速启动 | 比冷启动最多快 10 倍 | Android Emulator Quick Boot，无绝对值 | 官方文档 | [R13] |
| 训练并发 | 256（AVD）、512（AVD）、超过 1 万（redroid 与其他环境合计） | MobileRL、MAI-UI、Qwen-UI-Agent | 论文 | [R39][R40][R42] |
| 云侧沙箱密度 | 单节点 800 个 microVM 或 3,200 个容器 | DSec，非安卓 | 论文 | [R34] |
| 云手机密度 | 55 个 720p 容器（29 FPS）；无 GPU 时 3 个 | Anbox Cloud，Ampere Altra + 2×T4；m6g.2xlarge | 官方基准 | [R15] |
| 环境交互占比 | 模拟器交互耗时是模型推理的 1.7 倍，折算约 63% 的时间在环境侧（折算为本文计算） | Android Coach，8 并行 | 论文 | [R44] |
| 训练步耗时 | 每步超过 10 分钟；100 步超过 25 小时 | MobileRL，256 并行 | 论文 | [R39] |
| 长尾 | 任务时长相差可达 100 倍；异步后训练效率 3 倍、采集 2.4 倍 | DistRL | 论文 | [R43] |
| 沙箱寿命 | 中位数 15.5–17.4 分钟，P99 超过 3 小时 | DSec | 论文 | [R34] |
| GUI 单步时延 | 每步 7.0–14.7 s（含云端推理） | AndroidDaily，真机 350 个任务 | 论文 | 本库讨论稿 [A1] |
| 串流时延 | 35–70 ms | scrcpy 自述 | 厂商自报 | [R20] |
| pVM 跨边界开销 | 2%–14% | AnBridge | 论文 | [R65] |

### 7.3 手机侧的性能诉求（判断）

下表是基于本库已有负载分析（[L-C2](notes/L-C2-沙箱负载.md)、[C2](C2-沙箱框架与执行能力.md) §3 Q7、[讨论稿](discussion/沙箱-商业价值代价与定位.md) §3）与本轮数据推出的目标量级。**均为估算或建议值，需要真机验证。**

| 指标 | 建议目标 | 依据 |
|---|---|---|
| 进程级会话沙箱创建 | 不超过 50 ms | 进程级为毫秒级（机制推断）；工具调用不应增加可感知时延 |
| VM 级会话沙箱创建 | 预热或快照下不超过 0.5 s | 云侧快照恢复为 50–65 ms，手机 UFS 随机缺页按 0.1–0.4 s 估算（L-C2 §3.3） |
| 挂起后恢复（用户切回） | 不超过 1 s | L-C2 §3.3 的 T3 目标 |
| 单会话常驻增量 | 进程级 40–100 MB；VM 级 150–300 MB | C2 §3 Q7 的假设；AnBridge pVM 250 MB；Cube guest 156–193 MiB |
| 后台虚拟屏 | 每个 0.2–0.5 GB（未实测） | 讨论稿 §3 的估算：被操作的应用需在后台再运行一份 |
| 同时存活的会话 | 1–3 个 | 手机内存预算；并发上限更多受端侧模型与 KV 限制 |
| 后台存活 | 屏幕关闭、中等内存压力下不被结束；压力大时挂起到闪存，而不是丢弃 | Terminal 屏幕关闭即被结束的反例 |
| 功耗 | 待建立口径 | 公开资料为空白 |

判断：手机侧诉求与云侧的根本区别是，**云侧追求的是「一台机器多少个」，手机侧追求的是「一个会话多花多少」以及「后台能否活下来」**。云侧用来提高密度的做法（模板页共享、超分）在手机上摊不开，因为手机上同时只有 1–3 个会话。手机侧更需要的是快照挂起、按需换入，以及与 LMKD 协同回收。

---

## 8 技术挑战

| 层次 | 挑战 | 证据 | 已有解法或方向 |
|---|---|---|---|
| 平台抽象 | 通用沙箱平台默认承载「Linux 服务」，承载「完整操作系统」时会在 cgroup、探针、xattr、符号链接、继承的 fd 上逐一失败 | Cube 的 5 个阻塞点 [R1]–[R6] | 按模板选择 cgroup 模式、TCP 探针、长启动窗口、exec 前关闭 fd |
| 实例重量 | 安卓实例每个 5–16 GB 内存、30 GB 存储，限制并发 | MobileRL、2603.07432 [R39][R45] | redroid 容器化；共享只读层（DSec EROFS、redroid overlayfs）；microVM 内存快照 |
| 重置与长尾 | 重置慢；任务时长相差 100 倍，同步训练空等 | DistRL、Android Coach [R43][R44] | 快照重置、容器复用、备用池；异步 rollout、部分填充池；单状态多动作 |
| 图形与快照 | GPU 加速与快照互斥；ARM 服务器多数没有 GPU | Cuttlefish 快照文档、Anbox Cloud [R10][R17] | Agent 场景用软渲染、按需截图 |
| 页大小 | redroid 被固定在 4 KB；生态向 16 KB 迁移 | [R9][R25] | 由 guest 自带内核的 microVM 承担 16 KB 测试 |
| 真实性 | 反模拟器、Play Integrity、账号态、支付认证、风控 | Xiaomi-GUI-0、Qwen-UI-Agent [R50][R42][R26] | 真机农场；敏感步骤交还用户 |
| 奖励判定 | 需要读应用状态；真机无 root 时只能用模型评判 | MAI-UI（规则与模型评判的一致率 83%）、ClawGUI [R40][R46] | root 的 AVD 做规则校验加 MLLM 评判；可编程验证的 mock 应用（PhoneWorld） |
| 手机：隔离与开放 | 无特权方案（PRoot）隔离强度等于应用沙箱；pKVM 不向第三方开放 | OpenMinis、Napaxi、AVF [R60][R61][R63] | 由系统提供分档会话沙箱（第 10 节） |
| 手机：生命周期 | 屏幕关闭 VM 被结束；LMK 查杀；Android 12 起的 phantom process killer 会结束过多子进程 | [R67][AS5] | 内存气球随应用生命周期回收（Google）；需要挂起到闪存、恢复时按需换入 |
| 手机：资源 | 后台虚拟屏要在后台再运行一份应用；Agent 沙箱与前台应用、端侧模型共享内存 | 讨论稿 §3（估算） | 统一记账；与本库「内存与资源」服务协同 |
| 手机：兼容性 | PRoot 在部分 ARM64 机型上 ptrace 加 seccomp 崩溃；Bionic 与 glibc 不兼容 | OpenMinis GH#186；LPC 2025 [R60][R64] | 完整 VM（Terminal 路线）；安全的有限次重试 |
| 安全 | PRoot 不是安全边界；rootfs 没有完整性校验；虚拟屏不隔离数据；Napaxi 还没有出口凭证代理 | [R60][R61][R62] | 出口代理、凭证托管、信息流标签（见 C2） |

---

## 9 最新研究进展与技术创新点

### 9.1 论文清单（按与本文的相关度选取）

| 论文 | 机构 | 时间 | 解决的问题 | 关键数字 | 创新点 | 对手机侧的启示 |
|---|---|---|---|---|---|---|
| DSec（2609.22978） | DeepSeek | 2026-09 | 训练沙箱成批突发、种类异质、长寿命 | 单节点 800 microVM / 3,200 容器；峰值超过 38 万；按需加载快 1.71 倍；内存降 21.2% | 四类后端统一 SDK；EROFS 层组合；virtio-pmem 加 DAX；DAMON 加 balloon | 只读底座层、空闲页回收、按需加载，可迁移到手机 |
| Qwen-UI-Agent（2607.28227） | 阿里 Qwen | 2026-07 | KVM 模拟器扩展瓶颈；沙箱无法复现真实应用 | 超过 1 万个并发环境；100 多台真机、150 多个应用 | redroid 容器化；真机虚拟屏多应用并行；GUI、CLI、API 混合与批量动作 | 批量动作、虚拟屏并行，直接对应手机侧的时延诉求 |
| UI-TARS-2（2509.02544） | 字节 Seed | 2025-09 | 多 OS 交互环境与长尾 | 数千 VM 实例；VM Manager 数千 QPS | 租约式生命周期；会话 ID 路由；部分填充的 rollout 池 | 租约与会话 ID 是任何沙箱管理层的最小集 |
| MobileRL（2509.18119） | 智谱 | 2025-09 | 手机 GUI 在线 RL | 每 AVD 超过 5 GB / 30 GB；稳定 256 路；每步超过 10 分钟 | 难度自适应的正样本回放 | 安卓实例过重是共性问题 |
| MAI-UI（2512.22047） | 阿里通义 | 2025-12 | 大规模在线 RL 的环境管理 | 最多 512 并发；并行数从 32 增到 512，成功率提升 5.2 个百分点 | AVD snapshot + 容器复用 + 备用池 | 环境并行度直接影响模型效果 |
| DistRL（2410.14803） | — | 2024-10 | 同步多机的空等 | 任务时长相差 100 倍；训练效率 3 倍、采集 2.4 倍 | 中心训练、分布式采集、Environment Snapshots | 快照重置是标配 |
| Android Coach（2604.07277） | 浙大与 Qualcomm AI Research | 2026-04 | 模拟器交互昂贵 | 交互耗时是推理的 1.7 倍；训练效率是 PPO / GRPO 的 1.4 倍 | 单状态多动作，用 critic 复用状态 | 减少环境交互是与快照互补的算法侧路线 |
| Xiaomi-GUI-0（2606.31410） | 小米 | 2026-06 | 商业应用检测模拟器、风控 | AndroidWorld 78.9%；RealMobile 72.0% | 真机为主、沙箱为辅 | 手机厂商的天然优势是真机与系统权限 |
| BlueLM-GUI（2609.12394） | vivo（推断） | 2026-09 | 沙箱与生产环境分布不一致 | 数百台真机；AndroidWorld 84.9 | 真机上的 agentic RL | 同上 |
| PhoneWorld（2605.29486）、OpenMobile-2（2610.14157） | — | 2026 | 真实应用难重置、难验证 | 34 个 mock 应用；35 个模拟应用加 300 多个原生工具 | 从真实轨迹生成可重置、可编程验证的环境；GUI 与工具混合 | 降低对截图轮次的依赖 |
| WM-R1（2608.27508） | — | 2026-08 | 环境实例开销 | — | 用世界模型代替真实环境做 rollout | 另有工作指出 GUI 世界模型存在「状态混淆」，尚不成熟 |
| AutoDroid-V2（2412.18116） | — | 2024-12 | 逐步截图慢、token 多 | — | 端侧小模型生成脚本，端侧解释器执行 | 手机上「执行一段脚本」需要沙箱来跑这段脚本 |
| AnBridge（DSN'26） | 那不勒斯大学、巴黎电信、普渡大学 | 2026 | 端侧 AI 迁入 pVM 的编程模型门槛 | Pixel 7 Pro；pVM 250 MB；开销 2%–14% | Binder 加 vsock 的跨边界中间件 | 手机 pVM 的开销可接受 |
| Google LPC 2025：A Linux VM on Android via AVF | Google | 2025 | 在手机上运行完整 Linux | 定性：PRoot 的 ptrace 开销显著 | 内存气球随应用生命周期回收；gfxstream AHB 零拷贝；eBPF 自动端口转发 | 手机 VM 生命周期管理的第一份官方工程实践 |
| Aster（2407.16694；MobiSys'26 版为二手） | ETH 等 | 2024 / 2026 | 把 pVM 放进 Arm CCA realm | 运行期影响小（二手） | 互相隔离的沙箱服务抽象 | 未来手机上更强的隔离底座 |
| IsolateGPT（2403.04960，NDSS 2025） | 华盛顿大学等 | 2024 | LLM 应用生态的执行隔离 | 四分之三的测试查询开销小于 30%（二手） | 中枢调度加应用级隔离 | 应用之间隔离的系统设计 |
| From Assistants to Adversaries（2505.12981） | — | 2025 | 手机 Agent 的攻击面 | 11 个攻击面 | 按推理、GUI 交互、系统级执行三个维度分类 | 系统级执行与 GUI 交互需要分别隔离 |

来源：[R34][R42][R30][R39][R40][R43][R44][R50][R51][R53][R54][R55][R56][R65][R64][R58][R59][R57]。

### 9.2 技术创新点归类

| 类别 | 代表工作 | 做法 |
|---|---|---|
| 快照与重置复用 | Cube + redroid、AgentENV、DistRL、MAI-UI | 把环境状态当作可保存、可恢复的资产 |
| 减少环境交互 | Android Coach、WM-R1、PhoneWorld | 让每个昂贵的状态多用几次，或用模型与 mock 代替真实环境 |
| 环境与训练解耦 | UI-TARS-2、GUI-Owl、AgentRL、DSec、AReaL | 采集与学习分离，快慢 worker 不互相等待；沙箱可挂起，配合抢占式训练 |
| 异构分层调度 | Qwen-UI-Agent、DSec、Xiaomi-GUI-0 | 按负载选后端：容器负责规模，真机负责真实性 |
| 密度优化 | DSec、redroid overlayfs | 共享只读层、按需加载、空闲页回收 |
| 执行方式优化 | Qwen-UI-Agent、OpenMobile-2、AutoDroid-V2、ClawGUI | GUI、API、CLI、代码混合；批量动作 |
| 隔离与信息流 | IsolateGPT、Aster、Computer Control | 应用之间隔离；hypervisor 之外的隔离；逐应用授权 |
| 手机 VM 生命周期 | Google AVF Linux Terminal | 内存与磁盘气球联动应用生命周期；零拷贝图形 |
| 人在回路 | Qwen-UI-Agent、Computer Control | 支付、验证码等敏感步骤交还用户 |

判断：创新集中在「怎么少用环境、怎么让环境便宜」，而「单个安卓实例本身的启动、内存优化」在学术上几乎空白，主要靠 Cube、redroid 等工程项目推进。手机侧的空白更大：本轮没有找到任何论文测量手机上 Agent 沙箱的启动、内存、功耗与发热。

### 9.3 研究空白

1. 安卓客体的快照、fork 与恢复的系统评测，包括恢复后的工作集，以及「adbd 可连」到「界面稳定」的差距。
2. ARM 服务器云手机的密度与性能论文。
3. 手机本机：
   - AVF 上为 Agent 开隔离环境的启动、内存、功耗；
   - 后台虚拟屏的内存与 GPU 代价、对前台的干扰；
   - GUI Agent 确认与回滚机制的系统评测。
4. 单步时延的分项数据：截图编码、传输、推理、注入、界面稳定等待。

---

## 10 总结与判断：手机侧 Agent 沙箱的走向

### 10.1 现状

| 维度 | 现状 |
|---|---|
| 部署方式 | 面向用户的手机 Agent 产品都在真实系统上执行（豆包、Computer Control、荣耀、小艺）；把 Agent 放进隔离环境的只有面向开发者的开源项目（OpenMinis、Napaxi）和 Google Linux Terminal |
| 沙箱形态 | 第三方：PRoot 或 QEMU 用户态。系统：pKVM / AVF、后台虚拟屏。云侧：redroid 容器、AVD、microVM 包 redroid、真机 |
| 框架支持 | RL 框架不内置安卓；环境层已抽象为服务；Cube 正在补 microVM 加 redroid |
| 虚拟机支持 | 云侧 x86 成熟，ARM 要裸金属；手机侧 pKVM 量产，但第三方权限未明、芯片支持不全、屏幕关闭即被结束 |
| 性能数据 | 云侧训练吞吐有数字，安卓快照、重置、单步时延缺数字；手机侧几乎空白 |

### 10.2 三个判断

1. **云侧会收敛到「容器化安卓 + microVM 快照 + 真机补充」。**
   - 训练侧已经从 AVD 转向 redroid（Qwen-UI-Agent）。
   - 下一步是 microVM 快照与 redroid 结合（Cube 正在推进），解决重置与隔离。
   - 真机承担风控与真实性。
   - 预计 2027 年会出现以秒计的安卓环境重置数据，以及 microVM 加 redroid 的密度数据（判断）。
2. **手机侧会走「系统提供分档会话沙箱」，而不是「第三方自带沙箱」。**
   - 第三方能拿到的只有 PRoot 或 QEMU 用户态，隔离强度不够；强隔离（pKVM、虚拟屏授权）只在系统手里。
   - Google 已经把 GUI 执行（Computer Control）和完整 Linux（Terminal）收进系统，并只开放给 OEM 预装应用。这正是手机厂商的位置。
3. **手机侧的关键技术不在隔离本身，而在会话生命周期与资源协同。** 隔离部件已经存在，缺的是三件事：
   - 把它们组织成会话：创建、挂起、快照、恢复、销毁；
   - 与 LMKD、内存记账协同：后台缩小、压力下挂起到闪存、恢复时按需换入；
   - 在屏幕关闭时继续存活。
   - 这与本库汇报材料中「执行与沙箱」服务的「会话级隔离与状态底座」一致。本轮新增的参照有三个：
     - Cube 的 redroid 快照恢复约 50 ms（云侧，自报）；
     - Google 的内存气球联动应用生命周期；
     - AnBridge 的 pVM 跨边界开销 2%–14%。

### 10.3 建议的后续验证（按优先级）

1. **真机测量手机侧四档沙箱的代价**：PRoot、isolatedProcess 加 seccomp、pVM（Microdroid）、后台虚拟屏。在同一台设备上测：
   - 创建与恢复时延；
   - 常驻内存（PSS 与私有页）；
   - 单步时延的分解；
   - 持续执行 30 分钟的功耗与温升。
   这是公开资料中最大的空白，也是本库仿真与评估工作的差异化所在。
2. **在 ARM 服务器上复现 Cube 加 redroid**：在 #1880、#1881、#2031 合入后，测多实例密度、恢复后的工作集、「adbd 可连」到「界面稳定」的时间，并与 Docker 化 AVD 对比。
3. **评估后台虚拟屏的内存与 GPU 代价**：对应讨论稿中 0.2–0.5 GB 的估算。
4. **补核**：
   - 豆包手机的执行机制，需要拆包或官方技术说明；
   - 火山引擎云手机的形态；
   - `MANAGE_VIRTUAL_MACHINE` 的开放条件。

---

## 11 待核实

1. **Cube**：
   - #1880、#1881、#2031 的合入情况；
   - x86_64 加 redroid 的验证；
   - 多实例密度与恢复后的内存；
   - 截图与 GPU 通道。
2. **豆包手机**：推理在云还是端、截图是否上传、虚拟屏是否真实使用。目前只有 `INJECT_EVENTS` 一条官方说法，且经媒体转述。
3. **火山引擎云手机**：实例规格、ARM 还是 x86、容器还是 VM、单机密度；g2.8c12g 是否为真实售卖规格。
4. **训练侧**：
   - UI-TARS-2、GUI-Owl 安卓实例的形态、重置与单步时延；
   - Qwen-UI-Agent 的 redroid 实例规格与单机密度。
5. **x86 与 ARM 的成本、密度、功耗**：没有同口径公开数据；ARM 独占应用的占比；翻译层的覆盖率与性能损失。
6. **GCP、Azure 的嵌套虚拟化政策**，包括 ARM 实例。
7. **手机侧**：
   - PRoot 的系统调用开销；
   - Linux Terminal 的启动时间与官方机型清单；
   - gfxstream 是否已在 Android 17 稳定版落地；
   - `MANAGE_VIRTUAL_MACHINE` 对第三方的开放条件。
8. **荣耀 YOYO、鸿蒙小艺**：后台执行与隔离机制的官方说明。
9. **论文机构归属**：BlueLM-GUI 的机构（推断为 vivo），以及 DistRL、PhoneWorld、WM-R1、ClawGUI 的机构；Aster MobiSys'26 版本的编号与数字。
10. **OpenRLHF** 对安卓环境的支持（本轮未覆盖）。

---

## 参考资料

| 编号 | 标题 | URL | 日期 / 版本 | 状态 |
|---|---|---|---|---|
| R1 | CubeSandbox issue #1878：Support Android container images (e.g. redroid) as sandbox templates | https://github.com/TencentCloud/CubeSandbox/issues/1878 | 2026-09-30，open | 主线程已核 |
| R2 | CubeSandbox PR #1879：enable IPv6 and PSI in the arm64 guest kernel config | https://github.com/TencentCloud/CubeSandbox/pull/1879 | 2026-10-08 合入 | 主线程已核 |
| R3 | CubeSandbox PR #1880：`--probe-type tcp` 与 `--probe-timeout` | https://github.com/TencentCloud/CubeSandbox/pull/1880 | open | 主线程已核状态 |
| R4 | CubeSandbox PR #1881：harden image import for Android-based images | https://github.com/TencentCloud/CubeSandbox/pull/1881 | open | 主线程已核状态 |
| R5 | CubeSandbox PR #1882：annotation-driven cgroup mode | https://github.com/TencentCloud/CubeSandbox/pull/1882 | 2026-11-16（UTC）合入 | 主线程已核状态 |
| R6 | CubeSandbox PR #2031：close inherited fds before container init exec (Android zygote) | https://github.com/TencentCloud/CubeSandbox/pull/2031 | 2026-10-22，open | 主线程已核状态 |
| R7 | 本库：OpenShell 与 CubeSandbox 单实例内存与快照汇总（引 Cube README 与 CubeBench v0.7.3） | [notes/S-沙箱实例开销-汇总.md](notes/S-沙箱实例开销-汇总.md) | 2026-11-12 | 本地 |
| R8 | redroid-doc README | https://github.com/remote-android/redroid-doc | master | 已抓 |
| R9 | redroid deploy README（内核要求） | https://github.com/remote-android/redroid-doc/tree/master/deploy | master | 已抓 |
| R10 | Cuttlefish：Snapshot and restore | https://source.android.com/docs/devices/cuttlefish/snapshot-restore | 2026-11 | 已抓 |
| R11 | Cuttlefish：Get started | https://source.android.com/docs/devices/cuttlefish/get-started | 2026-11 | 已抓 |
| R12 | Cuttlefish 16 KB 页（ARM64 pgagnostic） | https://source.android.com/docs/core/architecture/16kb-page-size/getting-started-cf-arm64-pgagnostic | 2026-11 | 已抓 |
| R13 | Android Emulator Snapshots（Quick Boot） | https://developer.android.com/studio/run/emulator-snapshots | 2026-11 | 已抓 |
| R14 | Configure hardware acceleration for the Android Emulator | https://developer.android.com/studio/run/emulator-acceleration | 2026-11 | 已抓 |
| R15 | Anbox Cloud Performance benchmarks | https://canonical.com/anbox-cloud/docs/reference/perf-benchmarks | 1.11.2 / 1.12.1 | 已抓 |
| R16 | Anbox Cloud requirements | https://canonical.com/anbox-cloud/docs/reference/requirements/ | 2026-11 | 已抓 |
| R17 | Anbox Cloud supported rendering resources | https://canonical.com/anbox-cloud/docs/reference/supported-rendering-resources/ | 2026-11 | 已抓 |
| R18 | 华为云 CPH 产品优势 | https://support.huaweicloud.com/intl/en-us/productdesc-cph/cph_prod_0006.html | 2026-01-27 更新 | 已抓 |
| R19 | 火山引擎云手机文档（目录与 ListInstanceConfigurationSpec） | https://docs.volcengine.com/docs/6394/1404692 | 2026-11 | 已抓 |
| R20 | scrcpy README | https://github.com/Genymobile/scrcpy | master | 已抓 |
| R21 | Run ARM apps on the Android Emulator（Android Developers Blog） | https://android-developers.googleblog.com/2020/03/run-arm-apps-on-android-emulator.html | 2020-03-26 | 已抓 |
| R22 | AOSP Berberis（binary_translation）README | https://android.googlesource.com/platform/frameworks/libs/binary_translation/+/refs/heads/main/README.md | main | 已抓 |
| R23 | Streaming Android games with AWS Graviton-based G5g（AWS Compute Blog） | https://aws.amazon.com/blogs/compute/streaming-android-games-from-cloud-to-mobile-with-aws-graviton-based-amazon-ec2-g5g-instances | 日期待核实 | 已抓 |
| R24 | 基于 Graviton4 实例和 Redroid 搭建云手机（AWS 中国博客） | https://aws.amazon.com/cn/blogs/china/building-a-cloud-phone-based-on-graviton4-instance-and-redroid/ | 日期待核实 | 已抓 |
| R25 | Support 16 KB page sizes | https://developer.android.com/guide/practices/page-sizes | 2026-11 | 已抓 |
| R26 | Play Integrity API verdicts | https://developer.android.com/google/play/integrity/verdicts | 2026-11 | 已抓 |
| R27 | Amazon EC2 nested virtualization（User Guide）；InfoQ 报道 | https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.html ；https://www.infoq.com/news/2026/03/aws-ec2-nested-virtualization/ | 2026-02 / 2026-06 | 文档已抓；报道为二手 |
| R28 | Linux 6.11（KernelNewbies） | https://kernelnewbies.org/Linux_6.11 | 6.11 | 已抓（二手） |
| R29 | Configure and run nested virtualization on an Arm server（Arm Learning Path） | https://learn.arm.com/learning-paths/servers-and-cloud-computing/nested-virtualization/1-preparation/ | 2026-11 | 已抓 |
| R30 | UI-TARS-2 Technical Report | https://arxiv.org/abs/2509.02544 | 2025-09 | 已抓全文 |
| R31 | agent-infra/sandbox（AIO Sandbox） | https://github.com/agent-infra/sandbox | v1.11.0 | 已抓 |
| R32 | bytedance/SandboxFusion | https://github.com/bytedance/SandboxFusion | main | 已抓 |
| R33 | volcengine/verl | https://github.com/volcengine/verl | main | 已抓 |
| R34 | DSec: DeepSeek Elastic Compute | https://arxiv.org/abs/2609.22978 | 2026-09-19 | 已抓全文 |
| R35 | kvcache-ai/AgentENV | https://github.com/kvcache-ai/AgentENV | main，2026-11 | 已抓 |
| R36 | LlamaTouch/AgentEnv | https://github.com/LlamaTouch/AgentEnv | 2024-07 | 仅元数据 |
| R37 | 豆包手机助手 INJECT_EVENTS 公告（IT之家）及第三方技术分析 | https://www.ithome.com/0/902/287.htm ；https://www.woshipm.com/ai/6302896.html | 2025-12 | 二手（原页 403，依据检索摘要） |
| R38 | 本库：D1 商业形态深度补充 §5 | [../2027-agentos-ai-graphics/notes/D1-commercial-deep-dive.md](../2027-agentos-ai-graphics/notes/D1-commercial-deep-dive.md) | 2026-11 | 本地 |
| R39 | MobileRL | https://arxiv.org/abs/2509.18119 | v2，2025-09 | 已抓全文 |
| R40 | MAI-UI Technical Report | https://arxiv.org/abs/2512.22047 | 2025-12 | 已抓全文 |
| R41 | Mobile-Agent-v3 / GUI-Owl | https://arxiv.org/abs/2508.15144 | 2025-08 | 已抓（关键词扫描） |
| R42 | Qwen-UI-Agent Technical Report | https://arxiv.org/abs/2607.28227 | 2026-07-30 | 主线程已核原文 |
| R43 | DistRL | https://arxiv.org/abs/2410.14803 | 2024-10 | 已抓全文 |
| R44 | Android Coach | https://arxiv.org/abs/2604.07277 | 2026-04 | 已抓全文 |
| R45 | Generalization in Online RL for Mobile Agents | https://arxiv.org/abs/2603.07432 | 2026-03 | 已抓全文 |
| R46 | ClawGUI | https://arxiv.org/abs/2604.11784 | 2026-04 | 已抓全文 |
| R47 | AgentRL | https://arxiv.org/abs/2510.04206 | 2025-10 | 已抓全文 |
| R48 | AndroidWorld README | https://github.com/google-research/android_world | main | 已抓 |
| R49 | AndroidLab | https://arxiv.org/abs/2410.24024 | 2024-10 | 已抓 |
| R50 | Xiaomi-GUI-0 Technical Report | https://arxiv.org/abs/2606.31410 | 2026-06 | 已抓全文 |
| R51 | BlueLM-GUI Technical Report | https://arxiv.org/abs/2609.12394 | 2026-09 | 仅摘要 |
| R52 | HyMobileAgent | https://arxiv.org/abs/2607.14548 | 2026-07 | 仅摘要 |
| R53 | PhoneWorld | https://arxiv.org/abs/2605.29486 | 2026-05 | 仅摘要 |
| R54 | OpenMobile-2 | https://arxiv.org/abs/2610.14157 | 2026-10 | 仅摘要 |
| R55 | WM-R1 | https://arxiv.org/abs/2608.27508 | 2026-08 | 仅摘要 |
| R56 | AutoDroid-V2 | https://arxiv.org/abs/2412.18116 | 2024-12 | 仅摘要 |
| R57 | From Assistants to Adversaries: Exploring the Security Risks of Mobile LLM Agents | https://arxiv.org/abs/2505.12981 | 2025-05 | 仅摘要 |
| R58 | Aster: Fixing the Android TEE Ecosystem with Arm CCA | https://arxiv.org/abs/2407.16694 | 2024-07（MobiSys'26 版为二手） | 仅摘要 |
| R59 | IsolateGPT | https://arxiv.org/abs/2403.04960 | NDSS 2025 | 仅摘要 |
| R60 | OpenMinis（README、`PRootKernel.kt`、`SeccompFallbackPolicy.kt`、`AndroidManifest.xml`） | https://github.com/OpenMinis/OpenMinis | build 44，2026-11-15 | 已抓源码；主线程复核 |
| R61 | Napaxi（README、`docs/architecture.md`、`android_linux_env.rs`、`bake_android_rootfs.sh`） | https://github.com/antgroup/napaxi | sdk-v1.0.0，主干 | 已抓源码；主线程复核 |
| R62 | Android Computer Control（预览） | https://developer.android.com/ai/computer-control | 2026-11 | 已抓 |
| R63 | AOSP：AVF 架构 | https://source.android.com/docs/core/virtualization/architecture | 2026-11 | 已抓 |
| R64 | LPC 2025：A Linux VM on Android via AVF（Google，Jeongik Cha） | https://lpc.events/event/19/contributions/2123/ | 2025 | 主线程已读幻灯片原文 |
| R65 | AnBridge: Protecting On-Device AI with Android Virtualization Framework（DSN'26） | https://engineering.purdue.edu/dcsl/publications/papers/2026/anbridge-dsn26.pdf | 2026 | 主线程已读原文 |
| R66 | Android Authority：Linux Terminal 性能与画质；Galaxy Z Flip 7 支持 | https://www.androidauthority.com/androids-linux-terminal-performance-vs-quality-3660716/ | 2026-04 | 二手 |
| R67 | 个人指南：Android Virtualization Framework (AVF) Path C | https://cdn.jsdelivr.net/gh/ferrumclaudepilgrim/claude-code-android@main/docs/avf-guide.md | 2026 | 二手（个人实测） |
| R68 | verl-agent、ROLL、AReaL、slime 的 README | https://github.com/langfengQ/verl-agent ；https://github.com/alibaba/ROLL ；https://github.com/inclusionAI/AReaL ；https://github.com/THUDM/slime | 2026-11-15 抓取 | 已抓 |
| R69 | UI-Venus Technical Report；Step-GUI Technical Report | https://arxiv.org/abs/2508.10833 ；https://arxiv.org/abs/2512.15431 | 2025 | 关键词扫描 |
| R70 | 本库：C2 沙箱框架与执行能力；L-C2 沙箱负载；沙箱商业价值讨论稿 | [C2-沙箱框架与执行能力.md](C2-沙箱框架与执行能力.md)；[notes/L-C2-沙箱负载.md](notes/L-C2-沙箱负载.md)；[discussion/沙箱-商业价值代价与定位.md](discussion/沙箱-商业价值代价与定位.md) | 2026-11 | 本地 |
| A1 | AndroidDaily（ACM MM 2026） | https://arxiv.org/html/2605.27761v1 | 2026 | 经讨论稿引用，Table 2 已核 |

# AS1 云侧安卓沙箱的形态、部署与性能（含 CubeSandbox 安卓支持）

> 日期：2026-11-15。抓取版本：redroid-doc master（支持到 Android 16）；Cuttlefish snapshot 文档（android-latest-release）；Anbox Cloud 文档 + benchmark 页（数据基于 Anbox Cloud 1.11.2 / 1.12.1）；CubeSandbox PR 状态取自 GitHub API 2026-11-15。
> 实际用量：WebFetch 10 / WebSearch 4 / 源码与文档 curl 6（redroid README、deploy README、deploy/kubernetes.md、Anbox 源码页（404 失败）、scrcpy README、Android Emulator snapshot 页）/ api.github.com 7（超出预算 5 次，见「待核实」）。
> 本轮**未覆盖**：Android Emulator 的 ARM/x86 加速页、阿里云无影云手机、腾讯云云手机、Cuttlefish 的 GPU 模式页与 crosvm/QEMU 页（只在搜索摘要里见到片段）。这些在对应小节标「待核实」。

## 结论（≤6 条）

1. **Cube 的安卓路径已经「大部分打通、尚未全部合入」。** 5 个关联 PR 里 2 个已合入（#1879 arm64 内核 IPv6+PSI，2026-10-08；#1882 cgroup legacy，GitHub 记录合入时间 2026-11-16T03:02Z），3 个仍开放（#1880 TCP 探针、#1881 镜像导入加固、#2031 关闭继承 fd）。[源码/PR，GitHub API]
2. **阻塞点不止 issue 列的 4 个，还有第 5 个：zygote 遇到继承的 FIFO fd 会中止。** #2031（2026-10-22 提出，81 行新增、1 个文件）：agent 的 `do_exec` 把 passfd 日志转发管道继承给 guest init，Android zygote 在 fork system_server 时因 `Unsupported st_mode ... FIFO` 中止。作者自报修复后模板经 adbd TCP 探针到 READY，恢复的沙箱响应 ADB 握手，`getprop` 返回 Android 14。[PR 自述，厂商/贡献者自报；未见独立复现]
3. **Cube 路径的核心卖点是「快照恢复」：约 50 ms 恢复一台 redroid，对比 Cuttlefish 官方只写「x86_64 + SwiftShader 才能做快照」。** Cube 数字：模板约 40 s READY、恢复约 50 ms（#1878/#1879 提出者自报，规格 4 vCPU / 8 GiB，硬件未披露）。Cuttlefish：快照只在 x86_64 且 `guest_swiftshader` 下受支持，官方页无任何耗时数字。[Cube：贡献者自报；Cuttlefish：官方文档]
4. **容器形态的密度由 GPU/编码决定，不由 CPU 决定。** Anbox Cloud 官方 benchmark：Ampere Altra + 2×T4，720p、硬件渲染/编码，最多 55 个容器、平均 29 FPS；同一机器 1080p 为 50 个、26 FPS。AWS m6g.2xlarge（8 vCPU）纯软件渲染/编码只能稳定 3 个容器、20 FPS。[官方基准]
5. **国内云手机的官方口径几乎不披露单机密度。** 华为云 CPH 官方页只说「Arm 服务器、原生应用无需指令转换、相对 x86 模拟器方案最高提升 80%（无基线）」，并称 x86 模拟器方案「至少 50% 性能损失」；火山引擎 API 示例给出「开数」1–6（云机规格 g2.8c12g，8 核 12 GB 宿主切分，示例值非目录价）。[厂商官方文档；开数为 API 示例，需核实]
6. **redroid 对宿主的硬要求是「4 KB 页 + binderfs + ashmem/memfd + IPv6 + ION/DMA-BUF heap」。** 这解释了 Cube 路径为什么先要给 arm64 guest 内核补 IPv6 与 PSI，也预示 64 KB 页的 ARM 服务器（AS2 主题）不能直接跑 redroid 容器，但 microVM 的 guest 内核可以自选 4 KB 页（判断）。[官方文档 + 推断]

## 1. AS1-Q1 形态谱系

| 形态 | 代表 | 隔离边界 | 宿主内核要求 | KVM / 嵌套 | GPU 方案 | 典型用途 | 等级 | 来源 |
|---|---|---|---|---|---|---|---|---|
| 容器 | redroid（Docker/podman/k8s/LXC） | 共享宿主内核，`--privileged` 启动；README 警告 adb 端口暴露会危及容器甚至宿主 | binderfs、ashmem 或 memfd、IPv6、ION/DMA-BUF heap、**4 KB 页**；缺内核特性可用 redroid-modules 补；官方让关 SELinux（`setenforce 0`） | 不需要 | `androidboot.redroid_gpu_mode`：`guest`（软渲染，默认）/ `host`（宿主 GPU）/ `auto`；默认帧率 GPU 开 30、关 15 | 云游戏、云手机、自动化测试 | 官方文档 | [1][2] |
| 容器（LXD 系统容器） | Anbox Cloud 容器实例 | 共享宿主内核（LXD） | 官方文档未列出，待核实 | 不需要 | 硬件渲染/编码（T4 等）或 CPU 软件渲染/编码 | 高密度云手机、云游戏、流式应用 | 官方文档 | [3][4] |
| 全虚拟机 | Cuttlefish（crosvm 或 QEMU，待核实） | 独立 guest 内核，VM 边界 | 宿主 x86 与 ARM64 均可（官方首页）；Google Cloud 原生支持 | 需要 KVM；云上需嵌套或裸金属（AS2） | gfxstream 与 `guest_swiftshader`；快照仅限 swiftshader（官方快照页） | AOSP 平台测试、CTS、多设备并行 | 官方文档 | [5][6] |
| 全虚拟机（Anbox Cloud 的 VM 实例） | 以 Cuttlefish 虚拟机形式提供「更强隔离、标准未修改 Android」 | VM 边界 | 官方说明很简略，待核实 | 需要 | 待核实 | 对隔离或兼容性要求高的场景 | 官方文档 | [3] |
| 全虚拟机（模拟器） | Android Emulator（QEMU goldfish/ranchu） | VM 边界 | 需宿主硬件虚拟化加速（本轮未抓加速页） | 需要 | 待核实 | 开发者与测试 | 待核实 | [7] |
| microVM 包容器 | CubeSandbox + redroid | Cloud Hypervisor 分叉 + KVM 的 microVM；redroid 作为 guest 内 OCI 容器，guest 内核自带 binder | 宿主只需 KVM；guest 内核是不带模块的单镜像（arm64 配置 `CONFIG_ANDROID_BINDER_IPC=y`） | 需要 KVM | 当前未见 GPU 方案，截图/渲染路径未披露（待核实） | Agent 沙箱、可快照复用的安卓环境 | 贡献者自报 + 源码 PR | [8][9] |
| ARM 服务器/板卡阵列 | 华为云 CPH（鲲鹏/自研 Arm 芯片）、火山引擎云手机 | 厂商未披露是容器还是 VM（官方页未提） | 厂商自建 | 不适用 | 华为称有「专业 GPU 加速」，无细节 | 云手机、游戏、应用挂机 | 厂商官方文档（页面更新日期 2026-01-27） | [10][11] |

补充：
- Waydroid 只在搜索条目里被列入任务，本轮未抓，不展开。待核实。
- redroid 的 ARM 应用在 x86 实例上通过 `libhoudini` / `libndk_translation` / QEMU translator 运行；官方发布镜像已自带 `libndk_translation`。[官方文档][1]
- redroid 的 WebRTC 推流「计划」从 Cuttlefish 移植，说明截至该 README 它还没有内置推流。[官方文档][1]
- redroid 支持 Android 8.1–16 的镜像，且有 `64only` 变体，供只支持 aarch64 的 Arm 平台使用。[官方文档][1][2]

**这说明什么（判断）：**
- 隔离强度从强到弱的顺序是 全 VM ≈ microVM 包容器 > 容器；
- 但「能不能做快照」是另一条轴，Cuttlefish 限制得严，容器几乎没有；
- Cube 路径把容器的 guest 内核依赖问题转移到 guest 内核配置上（宿主不用装 binder），同时拿到 microVM 的快照与隔离。代价是要自己维护 guest 内核。

## 2. AS1-Q2 CubeSandbox 的安卓路径

### 2.1 PR 状态（GitHub API 2026-11-15 抓取）

| 编号 | 标题 | 状态 | 日期 | 内容与改动量 | 等级 |
|---|---|---|---|---|---|
| #1878 | Support Android container images (e.g. redroid) as sandbox templates | open（issue） | 2026-09-30 | 总 issue，主线程已核实 | 官方仓库 |
| #1879 | enable IPv6 and PSI in the arm64 guest kernel config | **已合入** | 2026-09-30 提出，2026-10-08 合入 | `kernel-oc9.aarch64.config` 两行 | 官方仓库 |
| #1880 | feat(cli): add `--probe-type tcp` and configurable `--probe-timeout` | **open** | 2026-09-30 提出，2026-11-04 最近更新 | 4 个文件；新增 `--probe-type tcp`、`--probe-timeout`（默认 30000 ms，FailureThreshold 由窗口推导，原固定 60）、`--probe-initial-delay`（默认 0）。复用平台已有的 `TCPSocketAction`；构建期的初始延迟不写入存储的探针 | 官方仓库 |
| #1881 | fix(image): harden image import for Android-based images | **open** | 2026-09-30 提出，2026-11-04 最近更新 | 5 个文件；导入层时剥离 `SCHILY.xattr.security.selinux`；CA 证书写入支持 Android 的 `system/etc/security/cacerts`（用 OpenSSL subject-hash 文件名，否则 conscrypt 忽略）；`/etc -> /system/etc` 绝对符号链接解析到 rootfs 外时报错而不是写到构建宿主 | 官方仓库 |
| #1882 | annotation-driven cgroup mode for guests that require cgroup v1 | **已合入** | 2026-09-30 提出，GitHub 记录合入 2026-11-16T03:02:21Z（晚于本调研日，疑为时区/时钟差异，原样记录） | 10 个文件、+220/-1。仅 `tpl create-from-image` 的 CLI 暴露 | 官方仓库 |
| #2031 | fix(agent): close inherited fds before container init exec (Android zygote) | **open** | 2026-10-22 | 1 个文件、+81。`close_range(3, ~0U, 0)`，旧内核回退 `/proc/self/fd` 扫描 | 官方仓库 |

`#1878` 时间线里只出现这 5 个交叉引用（#1879、#1880、#1881、#1882、#2031）。其中 #2031 不在 issue 原文的 4 个 PR 里，是后来新增的第 5 个阻塞点（作者 PR 自述）。

### 2.2 `--cgroup-mode legacy` 的实现链路（源码级，来自 #1882 自述）

CLI `--cgroup-mode legacy` → CubeMaster 的 `CreateTemplateFromImageReq.CgroupMode` → 沙箱 annotation `cube.master.cgroup_mode`（空值归一为默认；其他非法值在归一化时直接报错）→ Cubelet 把该 annotation 透传到沙箱 OCI spec（原来 CreateSandbox 只携带平台内部 key，请求级 annotation 会被丢掉）→ CubeShim 看到 `cgroup_mode=legacy` 时不再向 guest 内核 cmdline 注入 `agent.unified_cgroup_hierarchy=true`（agent / guest-init 在没有该参数时默认走 legacy）。
默认行为不变。验证：cmdline 不再含 `unified_cgroup_hierarchy=true`，`bootstrap-apexd-failed` 计数降为 0，模板进入就绪探针阶段。[PR 自述，贡献者自报]
PR 作者提醒：Cubelet 透传放在 cbri CreateSandbox 的 annotation 接缝上，如果新的 containerd 内部架构偏好别的机制可以改。同期 #2228 在升级内嵌 containerd 到 v2.3.7（open），这条链路有被重构的可能（判断）。

### 2.3 其余问题

| 问题 | 结论 | 等级 |
|---|---|---|
| 官方文档或 `examples/redroid/` | 抓取 `master/examples/redroid/README.md` 返回 404；未发现已合入的官方示例。维护者此前建议加 `examples/redroid/`，本轮未见合入 | 源码（curl 404）+ issue 评论 |
| 只支持 arm64 还是 x86_64 也行 | 所有端到端验证描述都在 arm64（#1879 改的是 aarch64 内核配置；#2031「release build of rustjail on arm64」）。x86_64 内核配置早就有 IPv6 与 PSI，理论上应能行，但没有任何 x86_64 验证记录。**待核实** | PR 自述 + 推断 |
| Android 版本 | #2031 里 `getprop` 返回 Android 14 | 贡献者自报 |
| 密度与内存数据 | 只有单点数据：4 vCPU / 8192 MiB / 10 GiB 可写层，约 40 s 到 READY，恢复约 50 ms。**没有任何多实例密度、恢复后 RSS、截图时延数据** | 贡献者自报；缺口 |
| 4 个 PR 共同的维护者态度 | 评论中维护者说内部也在看安卓沙箱支持；#1880/#1881/#2031 在 2026-11-04 之后无合入记录 | issue 评论，PR 状态 |

Cube 通用数据（来自 `S-沙箱实例开销-汇总.md`，不再重抓）：VMM PSS 约 5 MiB；纯净 guest RSS 156–193 MiB；每台宿主净增 19–25 MiB；从快照拉起 50–65 ms（NVMe + 页缓存热）。**这些是 Linux 轻量 guest 的数字，不能套到 8 GiB 配置的安卓上**：安卓冷启动后常驻内存远高于它，但快照恢复靠按需页加载，恢复后的实际工作集需要实测（判断；待核实）。

**这说明什么（判断）：**
- 这 5 个阻塞点没有一个是「安卓特有的难题」：cgroup v1/v2、HTTP 探针只适配 HTTP、SELinux xattr、`/etc` 符号链接、继承 fd。全是通用沙箱平台默认做了「Linux 服务」假设；
- 要把完整 OS 当成沙箱，平台抽象要从「服务」放宽到「OS」。其中 #1880 的 `--probe-initial-delay` 就是这种放宽的体现；
- 只有 2/5 合入，加上无官方示例，Cube 的安卓能力现在仍是「社区贡献者在推」，对外口径宜写「正在进行」而非「已支持」。

## 3. AS1-Q3 单实例资源与性能

| 形态 | 指标 | 数值 | 条件 | 口径 | 等级 | 来源 |
|---|---|---|---|---|---|---|
| Cube + redroid | 模板到 READY | 约 40 s | 4 vCPU / 8192 MiB / 10 GiB 可写层；arm64；硬件未披露 | 单次自报，未说明 P50 | 厂商/贡献者自报 | [8][9] |
| Cube + redroid | 沙箱恢复 | 约 50 ms | 同上；从模板快照恢复；adbd 在 :5555 可达 | 单次自报 | 贡献者自报 | [8][9] |
| Android Emulator | Quick Boot 对比冷启动 | 「最多快 10 倍」 | 官方文档；无硬件与绝对秒数 | 官方口径，无条件 | 官方文档 | [7] |
| Android Emulator | 快照限制 | 不支持 Android 4.0.4 及以下；不支持 Android 8.0（API 26）的 ARM system image；任何模拟器/镜像/AVD 设置更新都使快照失效 | 官方文档 | — | 官方文档 | [7] |
| Cuttlefish | 快照 | 仅 x86_64；仅 `guest_swiftshader`；VirtioFS 必须关闭；恢复前原实例必须停止；无耗时数字 | `cvd create --enable_virtiofs=false --gpu_mode=guest_swiftshader` 后 `cvd snapshot_take --force --auto_suspend --snapshot_path=PATH` | 官方文档 | [6] |
| Cuttlefish | 额外的社区信号 | crosvm-dev 2026-02 有一条 ARM64 快照恢复后网络失败的求助帖，无回复；crosvm 有一条「恢复时钟偏移」修复 | 搜索摘要，未打开原帖 | 二手 | [5]（搜索摘要） |
| Anbox Cloud 容器 | 单机密度 | Ampere Altra + 1×T4：720p/30 个、29 FPS；1080p/20 个、28 FPS。Ampere Altra + 2×T4：720p/55 个、29 FPS；1080p/50 个、26 FPS | Anbox Cloud 1.11.2；硬件渲染/编码；BombSquad demo（带自动玩法）；`amc benchmark -f -s 0.1 --measure-time 5m`，1280×720 / 30 fps / WebRTC | 「能保持稳定帧率的最大并行数」 | 官方基准 | [4] |
| Anbox Cloud 容器 | AWS g5g.metal | 720p：55 个/28 FPS 或 40 个/55 FPS；1080p：40 个/27 FPS 或 20 个/57 FPS | 1.12.1；硬件渲染/编码；BombSquad | 同上 | 官方基准 | [4] |
| Anbox Cloud 容器 | 无 GPU 对照 | m6g.2xlarge（Arm，8 vCPU）3 个、20 FPS；m5a.2xlarge（x86）3 个、13 FPS | 软件渲染/编码，720p，Android 10 Launcher（与 BombSquad 行不可直接比较） | 同上 | 官方基准 | [4] |
| Anbox Cloud 容器 | 官方宣称上限 | 单机最多 100 个实例；密度至少是其他 Android 模拟方案的 2 倍 | 搜索摘要引用文档；无条件 | 厂商自报 | [3]（搜索摘要） |
| Anbox Cloud | 启动时间 | `amc benchmark` 会测实例启动时间和平均 FPS，并有 Prometheus 直方图 `ams_cluster_instance_boot_time_seconds_bucket`；**没有公开数值** | — | — | 官方文档 | [3][4] |
| 华为云 CPH | 相对 x86 模拟器 | 「最多提升 80%」；x86 模拟器方案「至少 50% 性能损失」 | 无基线、无工作负载 | 厂商自报，不可复现 | 厂商官方文档 | [10] |
| 火山引擎云手机 | 规格/开数 | 云机规格 g2.8c12g（8 核）；开数：1 开 8C/8192、2 开 4C/4096、3 开 3C/3072、4 开 2C/2048、5 开 1.6C/2048、6 开 1.3C/1706 | `ListInstanceConfigurationSpec` API 的示例响应，文档声明为示例，内存单位疑为 MB | API 示例 | 厂商官方文档（需核实是否对应真实售卖规格） | [11] |
| redroid | 资源 | 官方未给出内存/启动时间数字；默认分辨率 720×1280、320 dpi、帧率 30（GPU）或 15（软渲染） | — | — | 官方文档 | [1] |

存储方面：Cube 示例模板可写层 10 GiB；redroid 支持 `androidboot.use_redroid_overlayfs=1`，把 `/data-base` 共享、`/data-diff` 私有，可以减少多实例的存储占用（官方没给节省比例，待核实）。[官方文档][1]

**这说明什么（判断）：**
- 「实测」和「厂商」基本无法对比：Cube 的是单次自报，Anbox 的是限定应用的压力测试，华为的是无基线的相对值；目前**没有任何一份同一硬件、同一应用、含快照的横向实测**。AS 汇总不要把这几组数字放在同一张柱状图里；
- Anbox 的 benchmark 有可借鉴的口径：以「能保持稳定帧率的最大并行数」作为密度；Agent 沙箱可改为「保持目标步时延的最大并行数」；
- Cube 的 50 ms 恢复本身对 RL rollout 很有吸引力，但它给的是恢复到「可连接 adbd」的时点，不等于「应用已就绪、屏幕已稳定」（判断）。

## 4. AS1-Q4 画面与交互链路

本轮证据较薄，只有以下可靠项：

| 环节 | 事实 | 等级 | 来源 |
|---|---|---|---|
| scrcpy 串流时延 | README 称 low latency 为 35~70 ms（链接指向 PR #646） | 厂商自报（项目自述），无硬件条件 | [12] |
| scrcpy 编码 | README 示例使用 H.265、16 Mbps | 项目文档示例（非实测带宽） | [12] |
| redroid 串流 | 官方 README 只写「计划」把 Cuttlefish 的 WebRTC 方案移植过来；当前用 adb + scrcpy 查看画面 | 官方文档 | [1] |
| redroid 帧率默认值 | GPU 开 30 fps，软渲染 15 fps；GPU 模式默认 `guest`（软渲染） | 官方文档 | [1] |
| Anbox Cloud | 渲染与编码是同一个瓶颈：有 GPU 时硬件渲染+硬件编码，无 GPU 时 CPU 软件渲染+软件编码；WebRTC 流式；文档没有端到端时延数字 | 官方基准/文档 | [4] |
| Cuttlefish GPU | 快照只支持 SwiftShader，说明「要快照就要软渲染」，gfxstream 与快照互斥（官方文档） | 官方文档 | [6] |
| Cuttlefish 的 `gpu_mode=gfxstream` | 仅在 AOSP commit 里看到该路径，无时延、无带宽数据 | 搜索摘要 | [5] |
| adb 动作注入时延、gRPC 截屏时延、Android Emulator gRPC 截图 | **本轮未找到公开数据，待核实** | — | — |

**这说明什么（判断）：**
- 对 GUI Agent 来说，吞吐瓶颈不在 adb 注入，而在「截图→模型推理→动作」中的截图编码与模型推理，这条判断还没有公开数据支持，需要 AS4/AS6 的 GUI Agent 论文数据来补；
- 快照与 GPU 加速互斥（Cuttlefish），而软渲染在无 GPU 的 ARM 服务器上 FPS 只有 13–20（Anbox m5a/m6g），所以 Agent 沙箱需要在「每秒几帧就够」的前提下用软渲染，才能同时获得快照与高密度。RL 沙箱不需要 30 fps 视频流，只需要按需截图（判断）；
- Cube 路径当前没有 GPU 与截图通道的公开方案，后续需要考察 guest 内的 SwiftShader 或 virtio-gpu 如何接入 Cloud Hypervisor（待核实）。

## 待核实

1. Cube 的 x86_64 + redroid 是否有人验证；多实例密度与恢复后内存占用；截图/GPU 路径。
2. Cube #1880、#1881、#2031 是否会合入；#1882 合入日期显示 2026-11-16（晚于本调研日），是否为 UTC 时区造成的显示差异，需要在后续引用前再确认。
3. Cuttlefish 的 crosvm/QEMU 选择、GPU 模式全表、单实例资源与启动秒数；Android Emulator 的加速（KVM/HAXM/WHPX）页；Waydroid。
4. Anbox Cloud 的 VM 实例（Cuttlefish）的资源与密度；容器实例的宿主内核要求；「单机最多 100 个」「至少 2 倍」的原文位置（目前来自搜索摘要）。
5. 阿里云无影云手机、腾讯云云手机、火山引擎云手机的单机密度与容器/VM 形态；火山引擎 g2.8c12g 是否对应真实售卖规格。
6. adb 注入、gRPC 截屏、WebRTC 的实测时延与带宽；本轮没有找到可引用的公开测量。
7. api.github.com 实际调用 7 次（5 次用于 Cube 的 PR 搜索、时间线与 PR 正文；1 次 redroid-doc 的 deploy 目录列表；1 次 #1881/#1880 的重复调用），超出每模块 5 次的预算；原因是需要补全 3 个 PR 的编号、状态与正文，但应在汇总时说明。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| [1] | redroid-doc README | https://github.com/remote-android/redroid-doc | master，支持到 Android 16（2026-11-15 抓取） | 已抓（curl） |
| [2] | redroid deploy README（内核要求、k8s、LXC 及各发行版列表） | https://github.com/remote-android/redroid-doc/tree/master/deploy | master | 已抓（README 与 kubernetes.md；各发行版页未打开） |
| [3] | Anbox Cloud 文档首页与搜索摘要 | https://canonical.com/anbox-cloud/docs/ | 2026-11-15 | 已抓（首页）；「100 个实例」等来自搜索摘要，二手 |
| [4] | Anbox Cloud Performance benchmarks | https://canonical.com/anbox-cloud/docs/reference/perf-benchmarks | Anbox Cloud 1.11.2 / 1.12.1 数据 | 已抓 |
| [5] | Cuttlefish 首页（Linux x86 与 ARM64、云上、多实例）；crosvm 快照与 Cuttlefish commit | https://source.android.com/docs/devices/cuttlefish | 2026-11-15 | 首页已抓；crosvm/commit 仅见搜索摘要，未打开 |
| [6] | Cuttlefish: Snapshot and restore | https://source.android.com/docs/devices/cuttlefish/snapshot-restore | android-latest-release | 已抓 |
| [7] | Android Emulator Snapshots（Quick Boot） | https://developer.android.com/studio/run/emulator-snapshots | 2026-11-15 | 已抓（curl） |
| [8] | CubeSandbox issue #1878 | https://github.com/TencentCloud/CubeSandbox/issues/1878 | 2026-09-30 提出，open | 主线程已核实；本轮仅读时间线 |
| [9] | CubeSandbox PR #1879 / #1880 / #1881 / #1882 / #2031 | https://github.com/TencentCloud/CubeSandbox/pull/<编号> | 见 2.1 | #1879 主线程已核实；其余经 GitHub API 抓正文 |
| [10] | 华为云 CPH 产品优势 | https://support.huaweicloud.com/intl/en-us/productdesc-cph/cph_prod_0006.html | 页面更新 2026-01-27 | 已抓 |
| [11] | 火山引擎云手机 ListInstanceConfigurationSpec | https://docs.volcengine.com/docs/6394/1404692 | 2026-11-15 | 已抓 |
| [12] | scrcpy README | https://github.com/Genymobile/scrcpy | master | 已抓（curl） |

# NVIDIA OpenShell：单实例内存开销与快照恢复时间

> 日期：2026-11-12；抓取版本：release v0.1.8（2026-11-10 发布）与 main 分支源码；检索实际用量：WebFetch 0 / WebSearch 0 / GitHub 原始文件与 API 约 25 次（README、docs 4 页、RFC 0004、VM 驱动 README 与 `driver.rs`/`runtime.rs`、Helm `values.yaml`、release assets、issues/PR 7 个）。
> 说明：未使用 WebFetch，docs.nvidia.com 页面以仓库内 `docs/*.mdx` 源文件代替（内容同源）。全文无任何实测，OpenShell 官方没有给出单实例内存或快照时延数字。

## 结论

1. **官方没有任何单实例内存数字（M1/M2 均无），也没有创建时延数字。** README、docs、RFC、issues 均查无（官方文档，查无）。唯一的容量数字是配置默认值：microVM 驱动 `vcpus=2`、`mem_mib=2048`、`overlay_disk_mib=4096`（M3，官方文档 + 源码 `DEFAULT_MEM_MIB=2048`）。
2. **microVM 驱动用 libkrun（GPU 场景用 QEMU），不是 Firecracker / Kata / Cloud Hypervisor。** 每个 microVM 沙箱在宿主上新增两个进程：一个 VM launcher（把 `openshell-driver-vm` 自己以 `--internal-run-vm` 重新执行，libkrun 在进程内）+ 一个宿主 `openshell-supervisor` 进程（源码确认，等级：源码推断）。M1 的数字无官方值，估算见 §2。
3. **默认不限内存的驱动：Docker/Podman/Kubernetes 不设默认 requests/limits**（`--memory` 才下发；K8s Helm `resources: {}`；源码推断，等级：源码）；microVM 驱动当前**忽略** `--cpu/--memory`，容量只能用 `mem_mib`（官方文档），且驱动自述 `memory.limit_supported=false`。
4. **快照类原语：通用 suspend/resume 契约已于 2026-10-27 合入（PR #4765），但所有自带驱动都不实现。** VM 驱动 `suspend_sandbox` 直接返回 `unimplemented`（源码）；只有一个 V8 isolate 示例（PR #4858，未合入）演示。没有 snapshot / fork / rollback 原语；`stop/start` 是冷启动，丢弃运行态。因此 T1–T4 均「无该原语、无数字」。
5. **一个旁证数字：VM 沙箱首次进程启动 / 首次文件读 / 首次内存触达比普通 cloud-hypervisor microVM 慢 2–3 倍**（用户 issue #4363，v0.1.2，2 vCPU/约 1GiB，样本极小，等级：二手、小样本；`python -c pass` 112–116 ms vs 28–51 ms；读 7784 个小文件首遍 90.8 µs/文件 vs 28.7 µs）。该 issue 已于 2026-11-08 关闭，`state_reason=not_planned`（主线程用 API 核实），即不修。

## 1 架构与每实例组成

| 组件 | 每实例 / 共享 | 作用 | 来源 |
|---|---|---|---|
| openshell-gateway（Rust） | 共享 | 控制面：沙箱生命周期、策略、凭证、SQLite/Postgres。release 压缩包 x86_64 约 46.1MB（tar.gz） | architecture.mdx；release v0.1.8 assets |
| openshell-driver-vm（Rust，内嵌 libkrun、libkrunfw、guest 内核、guest 沙箱） | 驱动进程共享一个；另被**每个沙箱重新执行一次**作为 launcher | gateway 以子进程拉起，UDS gRPC；`Command::new(launcher_bin)` 加 `--internal-run-vm --vm-vcpus --vm-mem-mib` 为每个沙箱起一个 launcher 进程，libkrun 在该进程内 `krun_start_enter` | VM 驱动 README；`driver.rs` L1213、L2141；`runtime.rs` L295–381 |
| openshell-supervisor（Rust，glibc 动态） | **每个沙箱一个宿主进程**（VM 驱动）；Docker/Podman 为每沙箱一个 supervisor 容器；K8s 默认每沙箱独立 pod，也有「共享 supervisor」拓扑（Helm `supervisor_topology=gateway`，HPA 目标 512Mi/pod） | 策略检查、凭证注入、DNS、网络代理、gateway 会话；release x86_64 压缩包 19.9MB（tar.gz，解压后更大，待核实） | VM 驱动 README；architecture.mdx 表；`driver.rs` L1368–1425；Helm values |
| openshell-sandbox（Rust，musl 静态） | 每实例，guest 内 PID 1，无 capabilities | guest 本地隔离（Landlock、seccomp、进程管理）、vsock 通道；压缩包 x86_64 约 4.7MB | VM 驱动 README；release assets |
| libkrun microVM（含 libkrunfw 定制内核） | 每实例 | VMM 以库形式在 launcher 进程内；KVM（Linux）/ Hypervisor.framework（macOS）；虚拟设备：virtio-blk（bootstrap ext4 根盘 + 每沙箱 overlay + 可选 image 盘）、vsock、可选 virtiofs；guest 无网卡 | VM 驱动 README；`runtime.rs` |
| 沙箱内代理 | 无独立进程 | 网络代理在**宿主** supervisor 内，guest 无 NIC，经 vsock 转发 | architecture.mdx L116 |
| QEMU 后端 | 仅 GPU（VFIO）沙箱 | `needs_qemu = is_gpu`；virtiofs 挂载不可用于 GPU 沙箱 | `driver.rs` L1939；runtimes.mdx |
| 容器 shim（Docker/Podman） | 每容器一个（runc/containerd-shim 或 conmon） | OpenShell 未自带；Docker/Podman 容器均 `network=none`，supervisor 独立成容器 | architecture.mdx 表；docs（shim 数据为通用知识，非 OpenShell 文档） |
| Kubernetes | 每沙箱 pod（工作负载 + supervisor pod），tmpfs（`emptyDir medium: Memory`）用于 runtime、state、proxy-CA 卷 | 这些 tmpfs 计入 pod 内存 | `kubernetes driver.rs` L7533–7547（源码） |

各驱动差异小结：Docker / Podman（容器 + 独立 supervisor 容器）、Kubernetes（pod + 独立 supervisor pod 或共享 supervisor）、MicroVM（libkrun/QEMU + 宿主 supervisor）。VM 驱动自述 Experimental（README）；issue #2332 里维护者认为主要面向 VM 隔离实验与 Docker/Podman 不可用的本地环境。

## 2 内存开销

| 指标 | 层 | 数值 | 测试条件 | 等级 | 来源 |
|---|---|---|---|---|---|
| microVM 默认内存 | M3 | 2048 MiB（`mem_mib`），vcpus 2，overlay 磁盘 4096 MiB（稀疏） | 驱动默认 | 官方文档 + 源码 | VM 驱动 README；`driver.rs` L117 |
| microVM 内存 limit 机制 | M3 | 沙箱级 `--memory` 被忽略；驱动 `memory.limit_supported=false` | — | 官方文档 + 源码 | runtimes.mdx「Size Sandboxes」；`driver.rs` L1563 |
| Docker / Podman / K8s 默认 limit | M3 | 无默认值，`--memory` 才下发 limits（K8s 同时把 limit 设为 request）；Helm 网关 `resources: {}` | — | 源码推断 | K8s `driver.rs` L8272–8300；values.yaml L383 |
| 每实例宿主进程 | M1 | 官方无数值 | — | 无（官方未给） | — |
| 每实例 launcher + supervisor 常驻 RSS | M1 | 估算约 40–100MB | 推断链见下 | 估算 | 见下 |
| 纯净 guest 实际占用 | M2 | 官方无数值；估算 80–200MB | 推断链见下 | 估算 | 见下 |
| 基础镜像 | — | `nvcr.io/nvidia/base/ubuntu:24.04`（体积未取到，待核实） | — | 官方文档 | runtimes.mdx |
| 最低主机要求 | — | 需 Docker/Podman 或宿主虚拟化（KVM / Apple HV）；未发现 RAM 最低值 | — | 官方文档（README） | README；support-matrix.mdx（未逐行读） |

**M1 估算推断链（估算，需实测）**：
- launcher 进程 = `openshell-driver-vm` 同一二进制（压缩包约 37.4MB，含 libkrun、libkrunfw 内核、guest 沙箱），启动后用 libkrun 把 guest 内存以匿名映射挂入本进程，RSS 随 guest 触达页增长。此进程的自身 Rust 运行时部分估计数 MB 到十余 MB；libkrunfw 内核镜像在 libkrun 中被映射进 guest 内存，计入 guest 而非 VMM。
- supervisor 为 Rust（tokio + 策略引擎 + TLS 代理 + gRPC），glibc 动态，压缩包约 19.9MB；常驻 RSS 合理区间 20–60MB（估算，依据：同类 Rust 异步代理的常见量级；含 OPA/策略与代理缓冲时偏高）。HPA 目标 512Mi/pod 是「共享 supervisor」的 pod 级目标值，不能反推单沙箱。
- 两者合计 40–100MB 为估算，**不能与 Firecracker「VMM ≤5MiB」或 Cube「<5MB」对标**：OpenShell 的每实例 supervisor 带整套策略与代理，比纯 VMM 重一个数量级。

**M2 估算推断链（估算）**：libkrun guest 用定制 6.12 内核（issue #4363 环境注明 libkrunfw guest kernel 6.12.76），根盘 ext4 加 overlay，init 为 shell 脚本 + 静态 guest-init + `openshell-sandbox`（musl，压缩包 4.7MB）。空闲 guest 内核 + 用户态 + page cache 估计 80–200MB；与 2048MiB 配置上限的差额不会被触达（匿名映射按需分配）。没有 balloon、KSM、DAX 共享的任何代码或文档证据（本次读取范围内），所以**没有证据表明多沙箱会共享模板页**（共享的只有宿主 page cache 里的只读 bootstrap/image ext4 盘）。

口径辨析：已有材料「文档未给启动 / 内存数据」是对的，本次追加确认；「计算驱动可选 Docker / Podman / Kubernetes / microVM」需补一句：microVM 驱动当前 Experimental，且 VM 沙箱内存只能靠驱动级 `mem_mib` 设定（所有沙箱同一值），不是沙箱级可调。

## 3 快照与恢复

| 指标 | 层 | 数值 | 测试条件 | 等级 | 来源 |
|---|---|---|---|---|---|
| 创建快照（暂停 + 写出） | T1 | 无该原语，无数字 | — | 官方（实现缺失） | VM 驱动 `suspend_sandbox` 返回 `unimplemented` |
| 从快照恢复 | T2 | 无 | — | 同上 | 同上 |
| 暂停 / 恢复 | T3 | 契约已合入，自带驱动不实现；无数字 | 仅 V8 isolate 示例（PR #4858 未合入）演示 | 官方（PR）| PR #4765（2026-10-27 合入）、issue #4763、`compute_driver.proto` |
| 回滚 | T4 | 无该原语 | — | 官方（查无） | — |
| 停止（含 flush） | — | guest 刷盘最多等 3 s，宿主等 supervisor 关闭最多 22 s，再等 5 s 停 VM；**丢弃运行态** | microVM `sandbox stop` | 官方文档 | runtimes.mdx「MicroVM Stop Durability」 |
| 创建时延（O4） | — | 首个 VM 沙箱 **10–30 s**（拉取与准备镜像缓存、libkrun 启动、guest init）；之后复用已准备的镜像缓存，只新建稀疏的 `overlay.ext4`，耗时无数字；升级后缓存要重建 | microVM 驱动 | 官方文档（主线程核对补入：VM 驱动 README 第 201 行） | VM 驱动 README；runtimes.mdx |

没有 snapshot / checkpoint / fork / rollback 原语的证据链：
- issue #1823「Design checkpoint, pause, and resume support」（2026-06-08 创建，2026-09-21 关闭，仅有设计要求，无实现）。
- PR #4765（合入）新增 `SuspendSandbox` / `ResumeSandbox` RPC、`Suspending/Suspended` 阶段、CLI `openshell sandbox suspend|resume`、驱动能力位 `openshell.compute.suspend-resume`；PR 正文明确「不启用现有示例或自带生产驱动的 suspend」。resume 语义是「在新的 runtime generation 下恢复 retained state」，由驱动与 isolation backend 负责。
- `compute_driver.proto` 注释：suspend「retaining its memory state」，即语义上是保留内存态，具体机制交给后端。
- issue #4351（开放）：外部提出 Firecracker 计算驱动；维护者的 RFC 0012 Firecracker 原型（#2934）已在 2026-09-30 关闭，无近期合入计划。Firecracker 快照若引入，将来才可能成为 microVM 的 suspend 实现。

底层可借原语的量级参照（均非 OpenShell 数据）：libkrun 无公开快照 API（待核实）；Firecracker 快照 / 恢复与 E2B 暂停约 4 s/GiB、恢复约 1 s 见 `L-C2-沙箱负载.md` §3.3（二手）；Docker checkpoint 走 CRIU，K8s ContainerCheckpoint 为 kubelet 特性，本次均未检索，无数字，待核实。

## 4 对端侧的含义（判断）

- 判断：OpenShell 的「每实例一个宿主 supervisor 进程」模型对内存最敏感；端侧参考其**策略与凭证注入语义**，但宿主侧不应每沙箱复制一个这样重的代理，应改成多沙箱共享的 supervisor（OpenShell 的 K8s「共享 supervisor」拓扑已是这个方向）。
- 判断：OpenShell 不能作为 T3「快照 / 恢复约 1 s」的时间参照，它没有任何实现；但它的 suspend/resume 契约（Suspending / Suspended 阶段、resume 换新 generation 与新凭证、strict restore 失败可重试）可直接借作**状态机与凭证重签**的设计参照。
- 判断：不要拿 OpenShell 的内存数字去对标 Firecracker / Cube 的「VMM 开销」，口径不同（含策略代理）。

## 待核实

1. 单沙箱 launcher 与 supervisor 的实测 RSS/PSS、纯净 guest 的 `memory.current`，需要本地装 VM 驱动实测，本次未做（也未按要求执行任何代码）。
2. docs 的 `support-matrix.mdx` 是否给出最低 RAM / 磁盘要求（已下载未逐行读）。
3. supervisor 解压后二进制体积、基础镜像体积。
4. issue #4363 关闭原因（是否有针对 first-touch 慢的修复，涉及内存预取或 virtio 配置）。
5. libkrun 是否有快照路径、是否会被 OpenShell 采用（roadmap 项目板 https://github.com/orgs/NVIDIA/projects/233 本次未打开）。
6. 创建时延（O4）无任何数字，需实测。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| O1 | OpenShell README | https://github.com/NVIDIA/OpenShell | main，2026-11-12 | 已抓（raw） |
| O2 | docs/about/architecture.mdx | https://docs.nvidia.com/openshell/latest/about/architecture | main | 已抓（仓库源文件） |
| O3 | docs/how-it-works/sandboxes/runtimes.mdx | https://docs.nvidia.com/openshell/latest/how-it-works/sandboxes/runtimes | main | 已抓（仓库源文件） |
| O4 | crates/openshell-driver-vm/README.md、src/driver.rs、src/runtime.rs | https://github.com/NVIDIA/OpenShell/tree/main/crates/openshell-driver-vm | main | 已抓 |
| O5 | rfc/0004-sandbox-resource-requirements | https://github.com/NVIDIA/OpenShell/tree/main/rfc/0004-sandbox-resource-requirements | main | 已抓 |
| O6 | deploy/helm/openshell/values.yaml | https://github.com/NVIDIA/OpenShell/blob/main/deploy/helm/openshell/values.yaml | main | 已抓 |
| O7 | Release v0.1.8 assets | https://github.com/NVIDIA/OpenShell/releases/tag/v0.1.8 | 2026-11-10 | 已抓（API） |
| O8 | issue #1823 / #4763、PR #4765、issue #4857 | https://github.com/NVIDIA/OpenShell/issues/1823 等 | 2026-06 至 2026-11 | 已抓（API） |
| O9 | issue #4363（VM first-touch 慢） | https://github.com/NVIDIA/OpenShell/issues/4363 | 2026-10-09 创建，2026-11-08 关闭 | 已抓（API） |
| O10 | issue #4351（Firecracker 驱动提案）、#2332（VM 驱动定位文档） | https://github.com/NVIDIA/OpenShell/issues/4351 | — | 已抓（API） |
| O11 | L-C2-沙箱负载.md §3.3 | 本仓库 notes/ | 2026-11-12 | 已读 |

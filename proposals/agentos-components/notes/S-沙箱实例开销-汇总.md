# OpenShell 与 CubeSandbox：单实例内存开销与快照恢复时间（汇总）

> 日期：2026-11-12
> 分项笔记：`S-Cube-实例内存与快照.md`、`S-OpenShell-实例内存与快照.md`；提示词：`research-prompt-沙箱实例开销.md`
> 版本：CubeSandbox master（release v0.7.3）；OpenShell release v0.1.8（2026-11-10）与 main 分支
> 核对：本文所有数字都由主线程逐条对过原文，包括 Cube 的三份基准报告和 README 的两张内存图，以及 OpenShell 四个驱动的 suspend 实现、VM 驱动 README、PR #4765 与 issue #4363。分项笔记里已更正的一处见 §1.2。
> 「纯净实例」指刚创建完成、处于空闲状态，没有启动用户进程，也没有装依赖或加载数据。

## 结论

1. **Cube 一个纯净实例的内存要分三层读，三个数字并不矛盾：**
   - VMM 自身约 **5 MiB**（PSS），即 README 宣传的「<5MB」；
   - guest RSS 约 **156 MiB**（1c2g）到 **193 MiB**（16c32g）；
   - 多个实例共享模板页之后，每多一台，宿主净增约 **19–25 MiB**（服务器，100–1000 台），只起 1 台时约 **34 MB**（云主机）。
   等级：官方基准，README 图为厂商自报。
2. **Cube 快照 + 恢复一轮约 90 ms**：空闲快照 35.6 ms，从快照拉起 53.1 ms。暂停 + 恢复一轮约 220 ms（85.9 + 132.1 ms）。快照耗时随脏页线性增长，约 0.26 ms/MiB；恢复耗时与快照大小无关，因为恢复走 `mmap(MAP_PRIVATE)` 按需缺页。前提：服务器 NVMe、页缓存已热、单并发。等级：官方基准，无第三方复现。
3. **OpenShell 官方没有任何单实例内存数字。** 已知的只有：
   - 配置默认值：microVM 2 vCPU / 2048 MiB；Docker / Podman / K8s 默认不设内存上限。
   - 每个沙箱在宿主上的组成：microVM 驱动下多一个 libkrun launcher 和一个 supervisor 进程；Docker / Podman 下多一个 supervisor 容器。
   - 运行时自身开销估算约 40–100 MB。这是估算，需要实测，比 Cube 的 VMM 重一个数量级，因为策略引擎和网络代理都在每实例的 supervisor 里。
4. **OpenShell 目前没有快照与恢复能力。** 2026-10-27 合入了 suspend / resume 的接口契约，但自带的 VM、Docker、Podman、Kubernetes 四个驱动都直接返回 `unimplemented`（源码已核）。只有 stop / start 两个操作，stop 会丢弃运行态。唯一的时间数字是首个 VM 沙箱启动 10–30 s（官方文档）。
5. **对端侧估算（判断）：**
   - 原来按「<5MB」估算单实例开销的地方都要改。手机上同时只有 1–3 个沙箱，模板页摊不开：第一台要常驻约 160 MiB 的工作集，其中不可回收的私有页约 20–34 MiB；第二台起每台再加约 20–25 MiB。
   - 恢复时延 50–65 ms 是服务器热缓存的口径，不能直接搬到手机。

## 1 内存开销

### 1.1 对比表

| 层 | CubeSandbox | OpenShell |
|---|---|---|
| **M1 运行时自身**（每实例的 VMM、shim、supervisor，不含 guest） | **VMM PSS 约 4–5 MiB**，1c2g 到 16c32g 几乎不随规格变化（README 图读数）；中文图对比「传统 QEMU 虚拟机 30 MB」，图注「仅为 Hypervisor 自身开销，不含 Guest OS 及用户负载内存」[C1]。containerd shim 与 guest 内 agent 的 RSS 无数据 | **官方无数字。** microVM 驱动下，每沙箱多两个 Rust 宿主进程：内嵌 libkrun 的 launcher（驱动二进制以 `--internal-run-vm` 重新执行）和 `openshell-supervisor`（策略、凭证注入、DNS、网络代理）[O1][O2]。Docker / Podman 下，supervisor 单独起一个容器 [O3]。**估算 40–100 MB**（推断链见分项笔记 §2） |
| **M2 纯净 guest 实际占用** | **Guest RSS 约 156 / 170 / 171 / 184 / 193 MiB**（1c2g / 2c4g / 4c8g / 8c16g / 16c32g，读图，误差约 ±2 MiB）[C1]。其中 guest 私有脏页只有约 **6.5 MiB**（空闲快照的脏页量）[C2]，其余是模板内存镜像在页缓存里的共享页 | **官方无数字。** guest 为 libkrunfw 定制内核 + ext4 根盘 + overlay，估算 80–200 MB（估算）。没有找到模板内存共享（KSM、DAX、内存快照模板）的代码或文档 |
| **每台宿主净增**（`free` 的 used 增量 ÷ 台数） | v0.7.3：100 台 18.71 → 500 台 24.58 MiB [C2]；6 月版：1000 台约 25.7 MB [C3]；PVM 云主机：1 台约 34 MB，5–20 台 27–32 MB [C4] | 无 |
| **M3 配置规格** | 测试规格 2 vCPU / 2000 MiB；按需分配，2 GiB 沙箱空闲时不会占满 [C3] | microVM 默认 `vcpus=2`、`mem_mib=2048`、overlay 4096 MiB；沙箱级 `--memory` 被忽略，只能在驱动级统一设置 [O1][O4]。Docker / Podman / K8s 默认不设上限，只有传了 `--memory` 才下发 [O4] |
| 底座 | Cloud Hypervisor 分叉（`cube-hypervisor`）+ KVM | libkrun（GPU 沙箱用 QEMU）；VM 驱动标注为 Experimental [O1] |

### 1.2 Cube 三个数字怎么读

- **5 MiB** 只算 VMM 进程自身的 PSS。
- **约 156 MiB 的 guest RSS** 包含从模板内存镜像以 `mmap(MAP_PRIVATE)` 映射进来的页。这些页只读时留在宿主页缓存里，所有同模板的实例共用；guest 写过之后才变成私有的匿名页 [C5]。
- **约 19–25 MiB 的每台净增** 用 `free` 的 used 计算，不含页缓存，所以只反映私有部分：guest 写过的匿名页（空闲时约 6.5 MiB），加上 VMM、shim、页表、TAP 等。这个值随台数从 18.7 缓慢升到 24.6 MiB [C2]。
- 1 台时的 34 MB（PVM 云主机）[C4] 说明：哪怕只起一台，私有部分也在 30 MB 量级；但它不包括模板页进入页缓存那一份。
- **已有材料的口径问题**：`L-C2-沙箱负载.md` §3.3、`report/2-场景与负载瓶颈.md` 的 W9 行、`P-C2-沙箱原型对比.md` 第 3 行写的「每实例额外内存 <5MB」，数字本身没错，但只是 VMM 自身，不能当成单实例的总开销。
- **分项笔记里的一处更正**：子 Agent 原判断「<5MB 口径不明，应不采纳」。README 的两张图写明了口径，已在 `S-Cube-实例内存与快照.md` 文首更正。
- **「纯净」的程度**：密度测试用的镜像是 `sandbox-code:latest`，探活端口 49999。按 E2B 的惯例，guest 里已经跑着代码解释器服务（这一点是推断）；内存图没有注明用的哪个镜像。所以约 156 MiB 是「带基础服务的空闲实例」，不是空 init。

### 1.3 OpenShell 为什么没有数字，以及怎么补

- README、文档、RFC、issue 里都没有内存测量。RFC 0004 只讨论资源请求的语义 [O5]。
- 每实例的进程构成已从源码确认（VM 驱动 `driver.rs` 为每个沙箱 `Command::new(launcher)` 加 `--internal-run-vm`）。但进程的 RSS 只能靠实测。
- 补法（需要 Linux + KVM）：起一个 VM 沙箱，记录 launcher 与 supervisor 两个进程的 `smaps_rollup`（Rss / Pss / Private），以及宿主 `free` 的增量；再连续起 5 台、10 台，看边际值。Docker 驱动同样测 workload 与 supervisor 两个容器的 `memory.current`。

## 2 快照与恢复时间

### 2.1 CubeSandbox

测试条件：腾讯云 BMI5 裸金属，Xeon 8255C 96 逻辑核，375 GiB 内存，NVMe + XFS；沙箱 2 vCPU / 2000 MiB；单并发，每档 3–5 轮；页缓存已热，不含冷读 IO（官方原注）[C2][C3]。

| 操作 | v0.7.3（2026-10） | 6 月版（2026-06） | 说明 |
|---|---|---|---|
| **创建快照**（空闲，脏页 6.5 MiB） | **35.6 ms** | 约 50 ms | 增量模式，只写匿名脏页 |
| 创建快照，随脏页增长 | 39.8 MiB 51.9 ms；194 MiB 91.7 ms；398 MiB 142.1 ms；909 MiB 277.4 ms；1137 MiB 332.4 ms | 1136 MiB 486.9 ms | 斜率约 0.26 ms/MiB，按首尾两点计算 |
| **从快照拉起** | **53.1 ms**；按脏页分档测 50–65 ms，与快照大小无关 | 63.9 ms | `mmap(MAP_PRIVATE)` 按需缺页；预取全部页的开关默认关闭 [C5] |
| 从模板创建（即 README 的「<60 ms 冷启动」） | 41.0 ms（p95 52.3 ms） | 47.8 ms | 模板本身就是内存快照，首次创建也是快照恢复 [C5] |
| 回滚 | 68.4 ms | 81.6 ms（流程含先建快照） | 只能回滚到本沙箱自己的快照 |
| 克隆（运行中的源沙箱，含完整内存） | 184.3 ms | 约 220 ms | — |
| **暂停 / 恢复** | **85.9 / 132.1 ms** | 558.4 / 41.8 ms | 6 月版暂停是全量写出 2 GiB 匿名内存；之后改为 soft-dirty 增量，暂停快了约 85% [C3] |
| 共享存储暂停 / 本地恢复 | 613.8 / 390.6 ms | — | 3 台云主机（PVM），JuiceFS + MinIO；数据真正落盘要 674 ms [C6] |
| 跨节点恢复 | 1044.4 ms | — | 同上；跨节点从快照拉起：冷 766.8 ms，热 199.5 ms [C6] |
| AutoPause / AutoResume | 只有定性描述「sub-second to a few seconds」 | — | 官方文档 [C7] |
| 快照文件大小 | 无数字 | — | 增量快照的目标文件是上一份的 reflink 克隆，实际落盘约等于脏页量（推断） |

**一轮合计**（v0.7.3，空闲实例）：快照 + 从快照拉起约 **89 ms**；暂停 + 恢复约 **218 ms**。

### 2.2 OpenShell

| 原语 | 状态 | 来源 |
|---|---|---|
| snapshot / checkpoint / fork / rollback | **没有**。issue #1823（checkpoint、pause、resume 的设计需求）已关闭，没有实现 | [O6] |
| suspend / resume | 2026-10-27 合入 PR #4765，加了 RPC、`Suspending` / `Suspended` 两个状态和 CLI 子命令 `openshell sandbox suspend\|resume`。PR 明确说不为自带驱动启用；VM、Docker、Podman、Kubernetes 四个驱动的 `suspend_sandbox` 都返回 `unimplemented`（逐个看过源码） | [O6][O7] |
| stop / start | 冷启动语义，stop 丢弃运行态。stop 时 guest 冲刷根文件系统最多等 3 s，宿主等 supervisor 退出最多 22 s | [O4] |
| 创建时延 | 首个 VM 沙箱 10–30 s（拉取并准备镜像缓存、libkrun 启动、guest init）；之后复用缓存，没有数字 | [O1] |
| 旁证 | issue #4363：VM 沙箱里首次启动进程、首次读文件、首次触达内存，比普通 microVM 慢 2–3 倍（用户报告，v0.1.2，样本很小）。2026-11-08 以 `not_planned` 关闭 | [O8] |
| Firecracker 驱动 | issue #4351 外部提案仍开放；维护者的 Firecracker 原型（RFC 0012）已在 2026-09-30 关闭 | [O6] |

**结论**：OpenShell 不能作为快照恢复时间的参照。可以借鉴的是它的挂起状态机：恢复时换新的 runtime generation、重签凭证，严格恢复失败可以重试。

## 3 对端侧估算的影响（判断）

1. **VM 级沙箱的常驻内存**：以 Cube 为参照，第一台约 160 MiB 工作集，其中不可回收的私有页约 20–34 MiB，其余约 130 MiB 是模板页缓存；第二台起每台约 +20–25 MiB。模板页可以回收，但回收后缺页要从闪存冷读，恢复和首次执行都会变慢。手机上的沙箱数量少，这部分基本摊不开。
2. **恢复时延**：Cube 的 50–65 ms 是「页缓存热 + 服务器 NVMe」的口径。手机上模板页常被 LMKD 压力回收，应沿用 `L-C2-沙箱负载.md` §3.3 的估算 0.1–0.4 s（UFS 随机缺页），再加上会话和网络重建。
3. **快照写出**：按 Cube 的模式，快照只写脏页，空闲时只有几 MiB，代价接近恒定。但 Agent 跑过任务后脏页会到数百 MiB，按服务器上 0.26 ms/MiB 计算，1 GiB 约 0.33 s；手机要按 UFS 写带宽重新折算，而且要避开 LMKD 回收与前台 IO 的高峰。
4. **OpenShell 的每实例 supervisor 模型**：内存最重，搬到端侧要改成多沙箱共享 supervisor。它的 K8s「共享 supervisor」拓扑已经朝这个方向走。

## 4 待核实

1. Cube 内存图的精确数值（读图误差约 ±2 MiB）、所用镜像，以及 guest RSS 是否包含 guest 内部的文件缓存。
2. Cube 快照文件的实际大小，以及模板页冷读时的恢复时延。官方只测了热缓存。
3. OpenShell 实测：launcher、supervisor 的 RSS / PSS，纯净 guest 的占用，后续创建时延。需要 Linux + KVM 环境，按 §1.3 的方法测。
4. 两者都没有第三方复现。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| C1 | CubeSandbox README / README_zh 及内存图 `docs/assets/cube-sandbox-mem-overhead.png`、`readme_overhead_zh_1.png` | https://github.com/TencentCloud/CubeSandbox | master，2026-11-12 | 主线程已抓，已看图 |
| C2 | CubeBench v0.7.3 报告 | https://github.com/TencentCloud/CubeSandbox/blob/master/docs/blog/posts/2026-10-28-cubebench-073.md | 2026-10-28 | 主线程已抓 |
| C3 | 性能基准（裸金属） | https://github.com/TencentCloud/CubeSandbox/blob/master/docs/blog/posts/2026-06-01-cubesandbox-perf-benchmark.md | 2026-06-01 | 主线程已抓 |
| C4 | PVM 云主机基准 | https://github.com/TencentCloud/CubeSandbox/blob/master/docs/blog/posts/2026-06-03-cubesandbox-perf-benchmark-pvm.md | 2026-06-03 | 主线程已抓 |
| C5 | 快照 / 克隆 / 回滚深度文章 | https://github.com/TencentCloud/CubeSandbox/blob/master/docs/blog/posts/2026-06-25-cubesandbox-snapshot-clone-rollback-deep-dive.md | 2026-06-25 | 主线程已抓 |
| C6 | JuiceFS 多节点基准 | https://github.com/TencentCloud/CubeSandbox/blob/master/docs/blog/posts/2026-11-04-cubesandbox-juicefs-perf-benchmark.md | 2026-11-04 | 主线程已抓 |
| C7 | Lifecycle 指南 | https://github.com/TencentCloud/CubeSandbox/tree/master/docs/guide | master | 子 Agent 已抓 |
| O1 | OpenShell VM 驱动 README 与 `src/driver.rs` | https://github.com/NVIDIA/OpenShell/tree/main/crates/openshell-driver-vm | main，2026-11-12 | 主线程已抓 |
| O2 | How OpenShell Works（`docs/about/architecture.mdx`） | https://docs.nvidia.com/openshell/latest/about/architecture | main | 主线程已抓 |
| O3 | 同上，各运行时的 supervisor 位置表 | 同上 | main | 主线程已抓 |
| O4 | Compute runtimes（`docs/how-it-works/sandboxes/runtimes.mdx`） | https://docs.nvidia.com/openshell/latest/how-it-works/sandboxes/runtimes | main | 主线程已抓 |
| O5 | RFC 0004 sandbox resource requirements | https://github.com/NVIDIA/OpenShell/tree/main/rfc/0004-sandbox-resource-requirements | main | 子 Agent 已抓 |
| O6 | issue #1823、#4351、#4763，PR #4765 | https://github.com/NVIDIA/OpenShell/pull/4765 | 2026-06 至 2026-11 | 主线程核对了 PR #4765 的状态 |
| O7 | Docker / Podman / Kubernetes 驱动的 `suspend_sandbox` 实现 | https://github.com/NVIDIA/OpenShell/tree/main/crates | main | 主线程已抓 |
| O8 | issue #4363（VM 首次访问慢） | https://github.com/NVIDIA/OpenShell/issues/4363 | 2026-11-08 关闭（not_planned） | 主线程已核状态 |

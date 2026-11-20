# CubeSandbox：单实例内存开销与快照恢复时间

> 日期：2026-11-12；抓取版本：仓库 master（pushed 2026-11-12），最新 release v0.7.3（2026-10-12），docs/changelog 已列到 v0.8.0；检索实际用量：WebFetch 1 / WebSearch 1 / 源码与仓库文档 13 个文件（raw.githubusercontent.com，`gh` 未认证故改用 curl）。

> **主线程核对更正（2026-11-12）**：下面第 1 条原写「<5MB 口径不明，应不采纳」，这一判断有误。README 引用的两张图写明了口径：
> - `docs/assets/cube-sandbox-mem-overhead.png`：按规格 1c2g–16c32g 分两段堆叠，图例是「Guest RSS (MiB)」和「VMM Overhead PSS (MiB)」。橙色的 VMM 段约 4–5 MiB，蓝色的 Guest RSS 段约 156–193 MiB（读图得出，误差约 ±2 MiB）。
> - `docs/assets/readme_overhead_zh_1.png`：CubeSandbox 5 MB 对传统 QEMU 虚拟机 30 MB，图注为「仅为 Hypervisor 自身开销，不含 Guest OS 及用户负载内存」。
>
> 所以 <5MB 属于 **M1**（VMM 进程 PSS），应当采纳，只是不能拿它当单实例的总开销。三个数字的关系见汇总文档 `S-沙箱实例开销-汇总.md` §1。§2 的「口径辨析」同样按这一点理解。

## 结论（≤5 条）

1. **README「<5MB」是 VMM 自身的 PSS（M1），不是单实例总开销**（已按上方更正改写）。纯净 guest RSS 约 156 MiB（1c2g）到 193 MiB（16c32g），其中大部分是模板内存镜像的共享页缓存；宿主净增（`free` 的 used 增量 ÷ 台数）每台约 18.7–24.6 MiB（v0.7.3，2 vCPU / 2000 MiB，100–500 台）、约 21.5–25.7 MB（6 月版，至 1000 台）、云主机 PVM 上约 27–34 MB（1 台时约 34 MB）。等级：官方基准，README 图为厂商自报。
2. **「32GB」是沙箱规格上限，不是主机内存。** 原文：「≤ 32GB 规格沙箱实测，更大规格下开销会略有上升」。含义是 VMM 开销与 guest 配置内存几乎无关（按需分配），不是说在 32GB 主机上测（厂商自报，README 原文）。
3. **从快照恢复到可用约 50–65 ms，单并发；这就是 README 的 <60 ms「冷启动」。** 架构文档：「Pre-snapshotted templates plus a RustVMM restore path」；深度文章：几乎所有 VM 都从内存快照恢复，包括首次创建。v0.7.3 单并发 avg 41.0 ms，从快照创建 53.1 ms；6 月版 47.8 / 63.9 ms。前提是资源池预热、磁盘文件已在 page cache（官方基准）。
4. **快照创建与脏页成正比，恢复与脏页无关。** 空闲 2 GiB 沙箱快照（脏页 ~6.5 MB）avg 35.6 ms；脏页 1137 MB 为 332 ms；恢复始终 50–65 ms，因为恢复用 `mmap(MAP_PRIVATE)` 按需缺页。回滚单并发 68.4 ms，克隆 184 ms（官方基准，v0.7.3，BMI5 裸金属）。
5. **Pause/Resume 是另一套数字，且随版本和存储后端变化大。** v0.7.3 裸金属：pause 85.9 ms、resume 132 ms（单并发）；6 月版是 pause 558 ms（全量拷贝，2 GiB）、resume 42 ms；JuiceFS 三节点云主机上 pause 614 ms、本地 resume 391 ms、跨节点 resume 1044 ms。「百毫秒」对快照创建、回滚成立，对暂停到共享存储不成立（官方基准）。

## 1 架构与每实例组成

| 组件 | 每实例 / 共享 | 作用 | 来源 |
|---|---|---|---|
| CubeHypervisor（`cube-hypervisor` 进程） | 每实例 | VMM；仓库 `hypervisor/` 的 Cargo.toml 写的是 `cube-hypervisor` v28.0.0、作者 The Cloud Hypervisor Authors、README 是 Cloud Hypervisor 的——即 **Cloud Hypervisor 的分叉**，不是 Firecracker 分叉（源码推断） | 仓库 hypervisor/ |
| containerd-shim-cube-rs（CubeShim） | 每实例（containerd Shim v2 每沙箱一个 shim） | Rust，管 rootfs、memory file、内核准备，boot/restore，vsock，原地快照 | 架构概览、CubeShim/README |
| cube-agent | 每实例，在 guest 内 | guest 内 agent，ttrpc/vsock 转发 Create/Exec/Kill | CubeShim/README |
| guest 内核 + guest-init | 每实例（内核页按快照共享） | 每沙箱独立 Linux 内核 | 架构概览 |
| Cubelet（Go） | 每节点共享 | 节点内全生命周期，调 CubeCoW | 架构概览 |
| CubeAPI（Rust）、CubeMaster（Go）、Redis、CubeProxy（OpenResty）、cube-lifecycle-manager（Go）、CubeEgress | 共享（控制面 / 每节点代理） | 网关、调度、状态、路由、自动暂停恢复、出口代理 | 架构概览 |
| CubeVS（eBPF） | 每节点共享；每沙箱一个 TAP | 网络数据面 | 架构概览 |
| CubeCoW | 库，在 Cubelet 内 | XFS reflink，`FICLONE`；rootfs 与内存卷的创建、克隆、快照 | 架构概览 |

README 致谢 Cloud Hypervisor 和 Kata。shim 进程本身的 RSS 无数据（待核实）。

## 2 内存开销

| 指标 | 层 | 数值 | 测试条件 | 等级 | 来源 |
|---|---|---|---|---|---|
| README 单沙箱额外开销 | 未明示（见辨析） | <5MB | 「≤32GB 规格沙箱」，无其他条件 | 厂商自报 | README 脚注 |
| dev.to：Memory per Instance | 未明示 | <5MB，「6x lower」，无基线 | 作者 JerryLin，2026-04-30 | 厂商自报 | dev.to |
| 整机增量法 每 VM 摊销 | M1+M2 的非共享部分（宿主 used 增量 ÷ 台数，含 VMM、shim、guest 私有页，不含共享的 page cache 内核页） | 100 台 18.71；200 台 21.34；300 台 22.63；400 台 23.68；500 台 24.58 MiB | v0.7.3，2 vCPU / 2000 MiB，BMI5 裸金属，375 GiB，Xeon 8255C，create-only | 官方基准 | cubebench-073 |
| 同上（6 月版） | 同上 | 100 台 ~21.5；300 台 ~23.8；500 台 ~25.0；1000 台 ~25.7 MB | 2 vCPU / 2 GiB，同硬件 | 官方基准 | 6 月 benchmark 文 §3.3 |
| 同上（PVM 云主机） | 同上 | 1 台 ~34，5 台 ~27，10 台 ~32，20 台 ~29 MB | 32GB 内存的云主机，嵌套 PVM | 官方基准 | PVM benchmark 文 |
| 空闲快照脏页（匿名页） | M2 的私有下限 | ~6.5–8.3 MB | 刚创建、未写入的 2 GiB 沙箱，`PagemapAnon snapshot saved` 日志确认 | 官方基准 | 三份 benchmark 文 §4.1 |
| 沙箱规格 | M3 | 2 vCPU / 2 GiB（v0.7.3 为 2000 MiB） | 测试规格 | 官方基准 | 同上 |
| 单机密度 | — | 1000 台稳定，占 ~25 GiB；满载写满按 375 GiB ÷ (2 GiB + 25 MB) ≈ 185 台 | BMI5 | 官方基准 + 官方估算 | 6 月 benchmark 文 |
| 共享手段 | — | 内存镜像 `mmap(MAP_PRIVATE)`：只读页留在页缓存，多 VM 共享；写过才变匿名私有页。未提 KSM、DAX、virtio-pmem | — | 官方文档（源码级描述） | 快照深度文章 §3.3 |
| 进程自身 RSS（VMM / shim / agent） | M1 | 无数据 | — | 待核实 | — |

**口径辨析。**

- 官方 benchmark 的 18.7–25.7 MiB 是「宿主机 used 增量 ÷ 台数」，覆盖 M1 加 M2 的私有页（含 guest 启动后写过的页）。快照基线匿名页 6.5–8.3 MB 是 M2 私有部分的下限。其余约 12–17 MB 应来自 VMM、shim、页表、virtio 队列、每沙箱 TAP 等（推断，无拆分数据）。
- README 的 <5MB 与这套数据差 4–5 倍，原因是口径不同：README 图注明 <5MB 是 VMM Overhead PSS（M1），不含 guest（主线程核对更正，见文首）。
- 摊销值随密度上升（18.7 到 24.6 MiB），说明每实例开销含随台数增长的部分（页表、TAP、日志、slab 等，推断）。
- 共享内核页不计入单实例：每 VM 仍有自己的 guest 内核，但只读页来自同一镜像的 page cache。所以「单实例 M2」与「每台增量」不等价，后者更小。
- 空闲 guest 的 RSS / PSS：**官方未给**。用基线脏页 ~7 MB（私有）加摊销残差给出区间 **~20–25 MB（每台整机增量，估算，依据上文）**，不得写成 PSS。

## 3 快照与恢复

主机均为 Tencent Cloud BMI5 裸金属，Xeon 8255C 96 逻辑核，375 GiB，NVMe + XFS，沙箱 2 vCPU / 2 GiB，页缓存已热（clone 测试原文说明「已在 Page Cache」），非 userfaultfd 懒加载，而是 `mmap(MAP_PRIVATE)` 按需缺页。「v0.7.3」指 2026-10-28 报告，「6 月」指 2026-06-01 报告。

| 指标 | 原语 | 数值（avg） | 测试条件 | 等级 | 来源 |
|---|---|---|---|---|---|
| 从模板创建（README「冷启动」） | T2 | 单并发 41.0 ms（v0.7.3）/ 47.8 ms（6 月）；10 并发 47.9 / 88.7 ms；50 并发 92.4 / 276.1 ms | create-only，p95 52.3 ms（v0.7.3）；README 另写 60 ms 与 50 并发 avg 67 ms、P95 90 ms、P99 137 ms | 官方基准 + 厂商自报 | cubebench-073；6 月文；README |
| 从快照创建沙箱 | T2 | 单并发 53.1 ms（v0.7.3）/ 63.9 ms（6 月）；50 并发 191.7 ms 批耗时，摊销 3.8 ms | 与脏页大小无关 | 官方基准 | 同上 §4.3 |
| 创建快照（空闲） | T1 | 单并发 35.6 ms（v0.7.3）/ ~50 ms（6 月）；10 并发批 66.4 ms | 脏页 ~6.5–7 MB，soft-dirty 增量 | 官方基准 | §4.1 |
| 创建快照，随脏页 | T1 | 39.8 MB 脏页 51.9 ms；194 MB 91.7；397.7 MB 142.1；908.5 MB 277.4；1137 MB 332.4 ms（6 月版 1136 MB 为 486.9 ms） | 串行，每点 3 次平均 | 官方基准 | §4.2 |
| 回滚 | T4 | 单并发 68.4 ms（v0.7.3）/ 81.6 ms（6 月）；10 并发 210.4 / 266.1 ms 批耗时 | 流程是先 create_snapshot 再 rollback，且仅能回滚到自己创建的快照 | 官方基准 | §4.4 |
| 克隆（含完整内存） | — | 单个 184 ms（v0.7.3）/ 220 ms（6 月）；100 台 50 并发摊销 4.6 ms | 源沙箱运行中，页缓存已热 | 官方基准 | §4.5 |
| Pause（裸金属，v0.7.3） | T3 | 单并发 85.9 ms；10 并发批 116.9 ms | 2 GiB，空闲 | 官方基准 | cubebench-073 §4.6 |
| Resume（裸金属，v0.7.3） | T3 | 单并发 132.1 ms；10 并发批 899 ms（摊销 89.9 ms） | 同上 | 官方基准 | 同上 |
| Pause（6 月，旧实现） | T3 | 558.4 ms（全量拷贝匿名页，随内存线性）；官方预期改增量后降 80–90% 到 ~60 ms | 2 GiB | 官方基准 | 6 月文 §4.6 |
| Resume（6 月） | T3 | 41.8 ms | 同上 | 官方基准 | 同上 |
| JuiceFS 共享存储：pause / 本地 resume | T3 | 613.8 / 390.6 ms（并发 1）；1484.7 / 1496.7 ms（并发 10）；数据真正就绪再加 674 ms（并发 1）到 4315 ms（并发 10） | 3 台 16 vCPU 云主机 PVM，AMD EPYC 9754，32 GiB，JuiceFS + MinIO writeback | 官方基准 | JuiceFS benchmark |
| 跨节点 resume（c2 到 c3） | T3 | 1044.4 ms（并发 1）、1666.8（5）、2611.1（10）；跨节点快照启动：冷 766.8 / 热 199.5 ms | 同上；含 c3 上建对象、起 VMM、等 guest 健康检查 | 官方基准 | 同上 |
| AutoPause / AutoResume | T3 | 文档仅写「typical resume latency is sub-second to a few seconds」 | 无测试条件 | 官方文档（定性） | docs/guide/lifecycle |
| 快照文件大小 | — | 无直接数字。增量快照只写匿名脏页：空闲约 7 MB，加上 reflink 基线，实际落盘随脏页增长；fs-only 快照每个都是独立镜像 | — | 官方文档（定性）+ 估算 | 快照深度文章；snapshot-rollback-clone.md |

**内存快照的机制**（官方文档）：三种模式 Full、Incremental（只写匿名页）、SoftDirty（只写上次快照后被写的页）；用 `/proc/self/pagemap` 判断匿名页与 soft-dirty，不读页内容；目标文件是上一份快照的 reflink 克隆，因此是增量写但得到完整镜像。恢复 `mmap(MAP_PRIVATE)` 内存镜像、按需缺页；`RestoreConfig` 有可选「预取全部页」开关，默认 false。因此 CubeCoW 既管磁盘（reflink），也用同一机制间接支撑内存镜像，但内存页的增量判定在 VMM 内。

**关于 README「百毫秒」**：中文原文「百毫秒级快照、克隆与回滚能力」和「整体保持在百毫秒级」。第二处指 50 并发创建 avg 67 ms / P99 137 ms，口径是创建而非快照。对快照的数字见上表：快照 35–50 ms 起，回滚 68–82 ms，克隆 184–220 ms，在「百毫秒量级」内，但随脏页增长到 1 GiB 可到 330–490 ms。

## 4 对端侧的含义（判断）

- 判断：端侧「纯净沙箱 M2」不宜引用 <5MB；参照云侧实测，取 ~20–25 MB（每台增量，含 VMM / shim / 页表），并明确这是「共享内核页之后」的口径。
- 判断：从快照恢复靠 `mmap(MAP_PRIVATE)` + 按需缺页，恢复时间与快照大小无关。恢复到可执行约 50–65 ms，但是在页缓存热、NVMe、x86 服务器上；端侧闪存冷读会更慢，且还要重建网络与会话。
- 判断：暂停（持久化）一次的代价是空闲 85 ms 起，随脏页线性（约每 100 MB 多 40 ms，2026-06 数据）；用户切走再切回的场景可参考这个量级，但在共享存储上是秒级。
- 判断：Cube 的 CPU 与内存都是服务器级，端侧手机需自行折算。

## 待核实

- <5MB 的原始测量方法：README 与 dev.to 均无基线，无拆分。需向团队或在 issue 中确认是否仅 VMM。
- 单实例 RSS / PSS 的拆分（VMM、shim、cube-agent、guest 内核）：官方未给；本文最大的缺口。
- v0.7.3 与 6 月版的 pause 数字差异（558 到 86 ms）对应的是增量模式上线，未在仓库 changelog 中逐一核对。
- 快照实际文件大小（空闲、1 GiB 脏页）：无数字。
- 中文渠道（ithome、CSDN、ai-bot 等）仅检索到摘要，未逐篇打开，无更细数字。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| R1 | CubeSandbox README / README_zh | https://github.com/TencentCloud/CubeSandbox | master，2026-11-12 | 已抓 |
| R2 | Architecture Overview | https://github.com/TencentCloud/CubeSandbox/blob/master/docs/architecture/overview.md | master | 已抓 |
| R3 | 性能基准（裸金属方法与复现） | .../docs/blog/posts/2026-06-01-cubesandbox-perf-benchmark.md | 2026-06-01 | 已抓 |
| R4 | CubeBench v0.7.3 报告 | .../docs/blog/posts/2026-10-28-cubebench-073.md | 2026-10-28 | 已抓 |
| R5 | PVM 云主机基准 | .../docs/blog/posts/2026-06-03-cubesandbox-perf-benchmark-pvm.md | 2026-06-03 | 已抓（部分） |
| R6 | JuiceFS 多节点基准 | .../docs/blog/posts/2026-11-04-cubesandbox-juicefs-perf-benchmark.md | 2026-11-04 | 已抓（部分） |
| R7 | 快照 / 克隆 / 回滚深度文章 | .../docs/blog/posts/2026-06-25-cubesandbox-snapshot-clone-rollback-deep-dive.md | 2026-06-25 | 已抓（部分） |
| R8 | Lifecycle 与 Snapshot-Rollback-Clone 指南、CubeShim README、rollback-snapshot shimapi、hypervisor/Cargo.toml | .../docs/guide/、CubeShim/、hypervisor/ | master | 已抓（部分） |
| R9 | Cube Sandbox is Now Open Source | https://dev.to/jerrylin_0101/cube-sandbox-is-now-open-source-why-we-built-a-fast-and-secure-sandbox-for-ai-agents-d4k | 2026-04-30 | 已抓 |
| R10 | 中文媒体检索结果（ithome、CSDN、ai-bot.cn） | https://www.ithome.com/0/973/640.htm 等 | — | 二手，未打开 |

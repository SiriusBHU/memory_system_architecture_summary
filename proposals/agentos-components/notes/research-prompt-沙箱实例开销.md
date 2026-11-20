# 调研提示词：OpenShell 与 CubeSandbox 的单实例内存开销和快照恢复时间

> 日期：2026-11-12
> 用途：同一份提示词既给子 Agent 用，也可以直接提交给其他模型。完整模式做 O、C 两个模块；单模块模式只做指定模块。

## 背景

我们在写 Agent OS「执行与沙箱」系统服务的汇报。端侧需要估算：一个沙箱实例常驻要占多少内存、挂起后多快能恢复。云侧两个开源参照是 NVIDIA OpenShell 和腾讯云 CubeSandbox。本轮只回答两个问题：

1. **单个纯净沙箱实例的内存开销。**「纯净」指刚创建完成、空闲，里面还没有启动用户进程、没有安装依赖、没有加载模型或数据。
2. **快照与恢复的时间。** 包括：创建快照（暂停 + 写出）耗时、从快照恢复到可执行命令的耗时、快照文件大小；有暂停 / 恢复（pause / resume）或回滚（rollback）原语的也算。

## 已有材料（先读，只补缺口）

- `notes/L-C2-沙箱负载.md` §3.3（第 123–140 行附近）：Cube README 自报「每实例内存开销 <5MB（最大配置 32GB）」「快照与回滚百毫秒粒度」，AutoPause / AutoResume 无时延数字；E2B 暂停约 4 s/GiB、恢复约 1 s；Firecracker 官方不给快照时延。
- `notes/C2a-sandbox-isolation.md`：Cube = RustVMM + KVM，CubeCoW 用 XFS reflink 做 O(1) 克隆（磁盘层）；OpenShell 计算驱动可选 Docker / Podman / Kubernetes / microVM，「文档未提快照」，「未给启动 / 内存数据」。
- `notes/P-C2-沙箱原型对比.md` 第 14–15 行：同上口径。

上面这些是第一轮的粗口径。本轮要把它们拆开、坐实或推翻。

## 必须区分的口径

内存开销至少拆成三层，每个数字都要说明属于哪一层：

| 层 | 含义 | 例子 |
|---|---|---|
| M1 运行时自身开销 | 每实例在宿主上额外多出的进程：VMM、shim、supervisor、代理等，不含 guest 内存 | Firecracker 官方「VMM 开销 <5 MiB」 |
| M2 纯净 guest 实际占用 | 空闲 guest 内核 + init + 基础服务实际触达的物理页（RSS / PSS / cgroup memory.current） | 一个空闲 microVM 实际占 30–60MB |
| M3 配置上限 | 给实例分配的内存规格（`--memory`、vCPU/内存模板） | 512MiB、2GiB |

另外要标出**共享部分**：多实例共享的只读页（模板快照、page cache、DAX、KSM 去重）不应重复计入单实例。gateway、控制面等多实例共用的进程单列，不计入单实例。

快照时间至少拆成：T1 创建快照（暂停 + 写内存 + 写磁盘）；T2 从快照恢复到可执行第一条命令；T3 暂停 / 恢复（如果与快照是两套原语）；T4 回滚。每个数字写明实例内存规格、是否懒加载（按需缺页 / userfaultfd）、并发数、硬件。

## 通用要求

1. **预算**：WebFetch 不超过 12 次，WebSearch 不超过 4 次。优先抓下面列出的已知链接。读源码时可以用 `gh api` 或 `curl https://raw.githubusercontent.com/...`（Bash）抓单个文件，这部分不计入 WebFetch 预算，但只读文本、不执行下载的代码，下载内容放进你的临时目录。
2. **等级**：每个数字标注 官方文档 / 官方基准 / 源码推断 / 厂商自报（README、博客）/ 二手 / 估算。查不到的写「待核实」，不要编造版本号、链接或数字。
3. **源码推断可以做，但要写出推断链**：例如「每实例 supervisor 是 Rust 静态二进制，大小 X MB，常驻 RSS 估计 Y MB（估算，依据……）」。
4. **今天是 2026-11-12**，优先最新版本；写明你查到的版本号和日期。
5. **用中文写**，术语保留英文原名。
6. **只写自己的输出文件**，不要修改仓库里的其他文件。

## 模块 O：NVIDIA OpenShell

已知链接：

- https://github.com/NVIDIA/OpenShell （README、`docs/`、releases、issues、discussions）
- https://docs.nvidia.com/openshell/latest/about/architecture
- https://docs.nvidia.com/openshell/ （文档首页，找 sandbox lifecycle、compute drivers、system requirements、resource limits 等页面）

问题：

- **O1 架构与每实例组成**：一个纯净沙箱由哪些进程 / 容器 / VM 组成？哪些是每实例的（supervisor、沙箱内代理、容器 shim、microVM 的 VMM），哪些是共享的（gateway、控制面）？各计算驱动（Docker、Podman、Kubernetes、microVM）下的差异；microVM 驱动用的是哪个 VMM（libkrun、Firecracker、Kata、Cloud Hypervisor？）。
- **O2 内存开销**：官方文档、README、issue、discussion、benchmark 里有没有单实例内存数字（M1 / M2 / M3）？默认内存 limit、最低主机要求、Helm chart 或 K8s manifest 的 requests / limits、基础镜像大小。没有官方数字时，从源码推断 M1（每实例常驻进程的语言、二进制大小、是否常驻）。
- **O3 快照与恢复**：是否支持 snapshot / checkpoint / pause / resume / fork / rollback？查 docs、CLI 子命令、API、issues、roadmap。没有就明确写「无该原语」，并说明它的底层驱动能借什么（Docker checkpoint 走 CRIU、K8s ContainerCheckpoint、microVM 快照），能找到量级参照就附上并标等级。
- **O4（附带）创建时延**：创建一个沙箱到可用的时间，有就记。

输出文件：`notes/S-OpenShell-实例内存与快照.md`

## 模块 C：腾讯云 CubeSandbox

已知链接：

- https://github.com/TencentCloud/CubeSandbox （README，以及 README 里链接的 benchmark 报告、架构文档、`docs/` 目录）
- https://dev.to/jerrylin_0101/cube-sandbox-is-now-open-source-why-we-built-a-fast-and-secure-sandbox-for-ai-agents-d4k
- 腾讯云官方文档与中文技术文章（腾讯云开发者社区、InfoQ、知乎等）：用 WebSearch 找「CubeSandbox 内存开销」「Cube 沙箱 快照 恢复 毫秒」「CubeSandbox benchmark」

问题：

- **C1 架构与每实例组成**：每实例由哪些组件组成（VMM 进程、shim、agent / guest 内进程），哪些共享（Cubelet、CubeAPI、CubeProxy 等控制面）？VMM 基于什么（RustVMM 组件、Cloud Hypervisor、Firecracker 的分叉？）。
- **C2 内存开销**：README「每实例 <5MB」的确切口径：是 M1（VMM 自身）还是含 guest？在什么规格下测？「最大配置 32GB」是什么意思？benchmark 报告里有没有单实例 RSS / PSS、单节点密度、模板内存共享（多实例共享模板快照页、KSM、DAX、virtio-pmem）的数字？纯净 guest 的 M2 有没有数据？
- **C3 快照与恢复**：快照创建时间、从快照恢复（拉起）时间、回滚时间、AutoPause / AutoResume 时间、跨节点暂停恢复时间；「百毫秒」的原文与口径；CubeCoW 只管磁盘层，还是也管内存层？内存快照是全量还是增量、是否懒加载。
- **C4 冷启动与快照的关系**：README 的「单并发 <60 ms 创建」是否就是「从模板快照恢复」？如果是，T2 就可以用这个数，但要写明前提（资源池预热、模板已在内存或 page cache 里）。

输出文件：`notes/S-Cube-实例内存与快照.md`

## 输出格式（每个模块一个文件）

```markdown
# <对象>：单实例内存开销与快照恢复时间

> 日期；抓取版本；检索实际用量（WebFetch n / WebSearch n / 源码文件 n）

## 结论（≤5 条，每条带数字和等级）

## 1 架构与每实例组成
（组件表：组件 | 每实例 / 共享 | 作用 | 来源）

## 2 内存开销
（数字表：指标 | 层 M1/M2/M3 | 数值 | 测试条件 | 等级 | 来源）
（口径辨析：已有材料里的数字该怎么读）

## 3 快照与恢复
（数字表：指标 | T1/T2/T3/T4 | 数值 | 测试条件 | 等级 | 来源）
（没有原语时：写明，并给底层可借原语的量级参照）

## 4 对端侧的含义（≤5 行，标「判断」）

## 待核实

## 参考文献
| 编号 | 标题 | URL | 版本 / 日期 | 状态（已抓 / 二手 / 未打开） |
```

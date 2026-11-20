# AS2：x86 与 ARM 上部署安卓沙箱的区别和技术挑战

> 日期：2026-11-15。抓取版本：Android 官方文档为 2026-11 在线版（16 KB 页文档含 Android 17 内容）；redroid-doc master（README 列到 Android 16）；AWS EC2 嵌套虚拟化文档为 2026-11 在线版。
> 检索实际用量：WebFetch 10 / WebSearch 4 / 源码与文档文件（curl）11 / api.github.com 1。
> 未覆盖：国内云手机（华为 CPH、火山 ACEP、阿里无影、腾讯）的产品文档，预算用完，已在「待核实」列出。

## 结论（≤6 条）

1. **本模块提示词里的「Berberis = ARM→x86 翻译」不对**。AOSP 的 Berberis 页面写的是 **riscv64 → x86_64** 动态二进制翻译，且仍是 work in progress（官方源码，已抓 README）。ARM→x86 用的是 `libndk_translation`（Google，AOSP x86 镜像与 Chrome OS ARC 用）或 Intel Houdini；redroid 官方镜像已内置 `libndk_translation`（官方 README）。
2. **Google 官方的 ARM 翻译不能用于商业托管**。Android Emulator 的 ARM-on-x86 翻译只在 Google APIs / Play Store 镜像上提供，授权范围是「x86 桌面、笔记本、本地服务器和客户自购云环境上的应用开发与调试」，明确写「不应用于提供商业托管服务」（官方博客，2020-03，只针对 Android 11 镜像）。云手机厂商在 x86 上跑 ARM 应用，要么自带翻译层（Houdini 等），要么换 ARM 宿主。这是 x86 路线最大的非技术约束（判断，依据官方博客原文）。
3. **ARM 宿主上做 microVM / 全 VM 沙箱，今天基本要裸金属**。AWS 嵌套虚拟化 2026-02 上线，只覆盖 Intel 的 C8i/M8i/R8i，2026-06 扩到 C7i、R7i、M7i、X8i 等 Intel 系列；**Graviton 不在列**（AWS 官方公告与 InfoQ，二手转述 Graviton 不支持）。Linux 内核里 KVM arm64 的 FEAT_NV2 嵌套虚拟化在 6.11 合入（KernelNewbies，二手）；Arm 官方学习路径要求 6.13+、建议更新的内核，并且必须在裸金属 Arm64 服务器上做，宿主启动参数 `kvm-arm.mode=nested`（Arm 官方学习路径）。容器形态（redroid）不受影响：Graviton4 c8g.large（2 vCPU / 4 GB 的普通虚拟机）上就能跑（AWS 官方中文博客）。
4. **页大小是 ARM 宿主的硬约束**。redroid 官方部署文档的「强制内核特性」清单里写了 **4 KB page size**；而 Android 15 起 AOSP 支持 16 KB 页，Google Play 要求目标 API 35+ 的应用在 **2027-02-01** 前支持 16 KB 页，否则无法发布更新（官方文档）。ARM 服务器发行版若默认 64 KB 页（如 RHEL 系 arm64，背景知识，本轮未核实）则 redroid 容器跑不起来，需换 4 KB 内核。Cuttlefish 则提供官方 `aosp_cf_arm64_phone_pgagnostic` 目标，要求 ARM64 Linux 宿主才能真 16 KB 页测试；x86 只能「simulate」（官方文档页标题）。
5. **GPU 路线两边都靠 NVIDIA，ARM 上多一个 G5g 特例**。Anbox Cloud 官方文档写支持的 GPU 厂商只有 NVIDIA、Intel、AMD，**虚拟机实例不支持 GPU**，没有 GPU 时用 LLVMpipe 软渲染，不能混用不同厂商 GPU，LXD 集群内所有节点必须同一架构。AWS 官方博客：Graviton2 + NVIDIA T4G 的 G5g，相比 x86 GPU 实例「每路游戏流每小时成本最多低 30%」，原因之一是 ARM 宿主不需要翻译或模拟（厂商自报，仅一个游戏流场景，未给出路数）。
6. **没有找到同口径的 x86 vs ARM 云手机密度 / 功耗 / 成本对比**。唯一的数字是 AWS 厂商口径的 G5g 最多 −30%，以及 WebSearch 摘要里另一个「Anbox Cloud G5g 最多 55 路 720p30、成本低 20%」的转述（二手，未在原文核到）。其余密度与功耗数据缺失，不能编造，见「待核实」。

---

## AS2-Q1 指令集与应用兼容

| 项 | 内容 | 数字 / 条件 | 等级 | 来源 |
|---|---|---|---|---|
| Android 自带翻译层机制 | Android 11 起的 x86 Google APIs / Play 镜像，用户态进程内把 ARM 二进制翻译成 x86；ART、libGLES、libvulkan 等性能关键库保持原生；底层硬件相关库不翻译，避免昂贵的内存访问插桩 | 只披露了 Android 11；没有 benchmark；全 ARM 模拟比翻译慢很多（WebSearch 摘要转述「over 10x slower」，原文页面未见数字） | 官方博客（机制）；10x 为二手 | [1] [2] |
| 授权限制 | 仅 Google APIs / Play Store 镜像；仅用于应用开发与调试；「不应用于商业托管服务」 | — | 官方博客 | [1] |
| 调试限制 | ARM 原生库在翻译下不支持断点 | — | 二手（WebSearch 摘要转述 Google 博客） | [2] |
| redroid 的翻译 | x86 redroid 可通过 `libhoudini`、`libndk_translation` 或 QEMU translator 跑 ARM 应用；官方镜像已内置 `libndk_translation` | 预编译包来自第三方仓库 zhouziyang/libndk_translation | 官方 README（项目方） | [3] |
| Berberis | AOSP `frameworks/libs/binary_translation`，**riscv64 → x86_64**，支持 Zb* 与大部分 Zv，部分 Zv 指令未实现，WIP，无性能数字 | — | 官方源码 README | [4] |
| ARM 宿主原生跑 | arm64-v8a APK 直接运行，不需要翻译；G5g 博客的演示选用 arm64-v8a 的《原神》APK | — | 官方博客 | [5] |
| 32 位 ARM | redroid 同时发布 `*_64only` 与含 32 位的镜像；AWS 中文博客选用 `13.0.0_64only-latest`。个人博客称「标准镜像带 32 位 ARM 库，在 Graviton 上可能 kernel panic」，未能在官方文档核实 | — | 官方（镜像清单）；panic 说法为二手，待核实 | [3] [6] |
| 「ARM 独占应用占比」 | **没有找到公开统计**。官方 16 KB 文档只说「用到 NDK 的应用要重编译」，没给占比 | — | 待核实 | [7] |
| Play Integrity | 官方 verdict 文档：`MEETS_DEVICE_INTEGRITY` 要求「真实认证设备」，Android 13+ 有硬件级的 bootloader 锁定证明；不通过 Google 检查的模拟器返回**空 verdict**；`MEETS_VIRTUAL_INTEGRITY` 仅对 Google Play Games for PC 这类通过检查、带 Play 服务的模拟器开放 | 没有任何文档说 x86 翻译或 ARM 服务器能通过 | 官方文档 | [8] |
| 银行 / 支付 / 反模拟器 | **本轮没有查到可引用的来源** | — | 待核实 | — |

**这说明什么（判断）**：
- 指令集差异在 ARM 宿主上直接消失，在 x86 宿主上变成「翻译层覆盖率 + 授权」两个问题。官方没有公布翻译层的覆盖率和性能损失，不能给数字。
- Play Integrity 看的是硬件级证明，不是 CPU 架构。所以 ARM 服务器上的 redroid / Cuttlefish 并不会因为「是 ARM」就通过检查；对强校验应用，x86 翻译与 ARM 服务器大概率同样失败（推断，来自官方 verdict 定义，没有实测）。
- 这条对 Agent 沙箱意义：纯用内置 / 自研 / 无强风控的 App 做 RL 环境时，两个架构差别不大；要跑银行、支付、强风控 App，只有真机或真机云手机（ARM 板卡）可信。

---

## AS2-Q2 虚拟化与内核

### 宿主形态对照

| 沙箱形态 | x86 宿主 | ARM 宿主 | 关键约束 | 等级 | 来源 |
|---|---|---|---|---|---|
| 容器（redroid） | 普通云 VM 即可 | Graviton4 c8g.large（2 vCPU / 4 GB）普通虚拟机即可 | 必须内核有 `binderfs`、`ashmem` 或 memfd、IPv6、ION 或 DMA-BUF Heaps、**4 KB 页**；`--privileged`；Amazon Linux 文档写支持 5.4 / 4.14 内核（5.10 当时在做），并提供 redroid-modules 补内核模块 | 官方 README 与部署文档；AWS 官方博客 | [3] [6] [9] |
| 全 VM（Cuttlefish） | `aosp_cf_x86_64_phone` / `aosp_cf_x86_64_only_phone` | `aosp_cf_arm64_only_phone-userdebug` | 宿主需要 `/dev/kvm`；文档对 GCE 指向嵌套虚拟化说明；ARM64 上用 `find /dev -name kvm` 检查 | 官方文档 | [10] |
| Cuttlefish 16 KB 页 | 只能「模拟」16 KB | `aosp_cf_arm64_phone_pgagnostic`，必须 ARM64 Linux 宿主；内核可用 `kernel_aarch64_16k_dist` 自编 | — | 官方文档 | [11] |
| Android Emulator | KVM / WHPX / Hypervisor.Framework；**不能在另一个 VM 里跑带 VM 加速的模拟器** | arm64-v8a 镜像可加速（文档要求 ARM64 镜像对应 ARM64 CPU，Apple silicon 列为支持） | ARM / MIPS 镜像在 Intel/AMD 上没有 VM 加速；Windows AEHD 驱动 2026-12-31 停止 | 官方文档 | [12] |
| Anbox Cloud 容器 | x86 或 Arm，≥4 核、8 GB、30 GB 磁盘 | 同左 | 同一 LXD 集群所有节点必须同架构 | 官方文档 | [13] |
| Anbox Cloud VM 实例 | 需要 `/dev/kvm` | 同左 | 每实例至少 4 CPU、5 GB 内存、15 GB 磁盘；**无 GPU 支持**；文档未提嵌套虚拟化 | 官方文档 | [13] [14] |
| microVM 包 redroid（CubeSandbox） | Cloud Hypervisor + KVM；x86_64 内核配置早已开 IPv6 与 PSI | arm64 guest 内核配置 PR #1879（2026-10-08 合入）才补开 `IPV6=y` 与 `PSI=y`；已有 `ANDROID_BINDER_IPC=y` | 需要宿主有 KVM；ARM 云上要裸金属（推断） | 主线程已核实（issue / PR）；裸金属为判断 | 主线程 |

### 嵌套虚拟化现状

| 平台 | 现状 | 等级 | 来源 |
|---|---|---|---|
| AWS x86 虚拟实例 | 2026-02 上线，C8i / M8i / R8i；2026-06-18 扩到 C7i、R7i、M7i、C8id、R8id、M8id、C7i-flex、M7i-flex、I7i、C8i-flex、R8i-flex、M8i-flex、X8i；L1 仅支持 KVM 与 Hyper-V；Nitro 把 VT-x 等处理器扩展透传给实例 | 官方 AWS 公告（经 WebSearch 摘要）+ 官方 EC2 文档 | [15] [16] |
| AWS Graviton | **不支持**（InfoQ 转述 AWS 工程师；2026-06 扩展清单里也都是 Intel） | 二手 | [15] |
| AWS 对性能的态度 | 对性能或延迟敏感、需要硬件虚拟化扩展的负载，建议用裸金属 | 官方文档 | [16] |
| KVM arm64 嵌套 | Linux 6.11 合入「Nested Virtualization support (FEAT_NV2 only)」；Marc Zyngier 的补丁系列从 2021-11 v5 迭代到 2023 年 v10 | 二手（KernelNewbies、LWN 目录） | [17] |
| Arm 嵌套实操 | 需要 Linux 6.13+（建议更新），裸金属 Arm64 服务器，`kvm-arm.mode=nested`，日志出现「VHE+NV2 mode initialized successfully」才算开启；硬件必须有 FEAT_NV2 | Arm 官方学习路径 | [18] |
| GCP / Azure | **本轮没有检索到，待核实**。Cuttlefish 文档只提到 GCE 有嵌套虚拟化说明页 | — | [10] |

### 页大小

| 项 | 内容 | 等级 | 来源 |
|---|---|---|---|
| Android 15 起 | AOSP 支持 16 KB 页设备；用 NDK 的应用必须重编译才能在 16 KB 设备运行；16 KB 设备内存略增，但应用启动低 3.16%（最高 30%），启动功耗降 4.56%，相机冷启动快 6.60%，系统启动快 8%（约 950 ms） | 官方文档（Google 初步测试） | [7] |
| Play 要求 | 目标 API 35+ 的应用须支持 16 KB 页，**2027-02-01** 起不满足则不能发布更新 | 官方文档 | [7] |
| 兼容模式 | 16 KB 内核下，包管理器可对含 4 KB 对齐 `.so` 的应用启用 backcompat 模式；Android 17 可用 `bionic.linker.16kb.app_compat.enabled fatal` 强制让不兼容二进制直接 abort | 官方文档 | [7] |
| redroid 要求 | 强制 4 KB 页 | 官方部署文档 | [9] |

**这说明什么（判断）**：
- x86 宿主上，KVM 和嵌套虚拟化都成熟，microVM / 全 VM 沙箱在普通云 VM 上就能起（AWS 从 2026-02 起也补上了）。ARM 宿主上，容器形态没问题，VM 形态要裸金属，这直接限制了 CubeSandbox 这类 microVM 路线在 ARM 公有云上的部署弹性。
- 页大小有两个方向的冲突：redroid 要 4 KB 宿主页，而 Android 生态在往 16 KB 走。两边会在 2027 年前后相遇：宿主 4 KB、guest 16 KB 的组合要用 microVM / 全 VM（guest 自带内核）才能解决，容器形态的 redroid 由于共享宿主内核，就被钉在 4 KB。这个组合对「容器 vs microVM」选型是实质性变量。

---

## AS2-Q3 GPU 与图形

| 方案 | 架构 | 数据 | 条件 | 等级 | 来源 |
|---|---|---|---|---|---|
| redroid GPU 模式 | `androidboot.redroid_gpu_mode`：`guest`（软渲染，默认）、`host`、`auto`；默认帧率 GPU 开启 30 fps，未开启 **15 fps** | fps 默认值 | 配置默认值，不是实测 | 官方 README | [3] |
| Android Emulator 软渲染 | `-gpu` 可选 `host`、`software`、`lavapipe`、`swiftshader`、`swangle`；`guest` 与 `swiftshader_indirect` 等已在 36.4.9 弃用 | — | — | 官方文档 | [12] |
| Anbox Cloud 容器 | 官方只列 NVIDIA、Intel、AMD；NVIDIA 用 ERD 驱动，AMD 用 Mesa radv，Intel 用 Mesa anv；无 GPU 时 `webrtc` 平台回落到 LLVMpipe 软渲染；`null` 平台用 ANGLE 做无头渲染（CPU 开销低，不出画面）；GPU 以「slot」方式分配，slot 不限制使用量 | 无数字 | — | 官方文档 | [14] |
| Anbox Cloud VM 实例 | **不支持 GPU** | — | — | 官方文档 | [14] [13] |
| ARM + NVIDIA（G5g） | Graviton2 + NVIDIA T4G；Anbox Cloud 的 ARM 版 appliance；演示《原神》串流 | 每路游戏流每小时成本最多低 30%（对比 x86 GPU 实例）；原因：不需要交叉编译或模拟；另有二手转述最多 55 路 720p30、低 20% | 厂商自报；场景是游戏串流，非 GUI Agent RL | 官方博客；55 路为二手 | [5] |
| ARM 服务器无 GPU | 只能软渲染（llvmpipe 等），受 CPU 限制 | **没有找到公开的软渲染密度数字** | 待核实 | — | — |
| 国产 ARM 云手机板卡的移动 GPU | **本轮没有检索** | — | 待核实 | — | — |

**这说明什么（判断）**：
- 对「Agent 点按 UI + 截图」的负载，画面刷新率要求远低于游戏；redroid 默认没有 GPU 时是 15 fps，足够截图，这类负载在 x86 与 ARM 软渲染下都能跑，GPU 不是第一约束。
- 真正拉开差距的是游戏类或 3D 密集的 App 与大规模串流。这时 x86 + NVIDIA 是文档覆盖最完整的路线；ARM + NVIDIA（G5g）有官方背书，但厂商自己只给了成本差，没给路数 / 帧率。**没有找到 ARM 板卡内置移动 GPU 的公开云侧密度数据，不能做对比。**
- 注意 Anbox Cloud 的 VM 实例无 GPU：要 microVM 级隔离又要 GPU，目前官方路线给不出来。

---

## AS2-Q4 成本、密度与选型

| 项 | 内容 | 等级 | 来源 |
|---|---|---|---|
| 成本 | G5g（ARM + T4G）相对 x86 GPU 实例，每路游戏流每小时最多低 30% | 厂商自报（AWS 博客） | [5] |
| Graviton4 对 Graviton3 | 性能最高 +30%，能耗 −60%（与 Graviton3 对比，不是对 x86） | 厂商自报（AWS 博客） | [6] |
| 密度 | **没有找到 redroid 在 x86 与 ARM 上的同口径密度数据**。唯一的密度线索是 Canonical 一篇 2018 年 A1 实例文章里「同一 EC2 实例上 10 个 Android LXD 容器」，年代久远，不可比 | 二手，不可比 | [19] |
| 功耗 | 无同口径数据 | 待核实 | — |
| Anbox Cloud 最低规格 | 容器：4 核 / 8 GB 宿主；VM 实例每个至少 4 CPU / 5 GB / 15 GB | 官方文档 | [13] |

### 选型建议（判断，非来源结论）

| 负载 | 倾向 | 理由 |
|---|---|---|
| RL rollout（要快照、秒级重置、成千上万并发） | x86 优先（microVM / 全 VM，普通云 VM 上有嵌套虚拟化） | KVM 与嵌套成熟；Google 的翻译层授权限制在训练自用场景（自购云）下可接受；ARM 要裸金属才能用 microVM |
| 云手机（面向最终用户，要 ARM 应用原生兼容和成本） | ARM 优先（容器 + 板卡 / Graviton 类） | 不需要翻译，也避开 Google 翻译层的「不得商业托管」限制；容器形态在 ARM 虚拟机上就能跑 |
| 测试农场（兼容性回归） | 两边都要；用 ARM 原生测试 ARM 应用，x86 翻译测试只当补充 | Google 自己建议同时发布 x86 与 ARM 版本、不替代真机 |
| 手机本机（端侧） | 天然 ARM，没有翻译问题；虚拟化入口只有 AVF / pKVM（见 AS5） | 手机上没有 KVM 嵌套可用，也没有 binder 内核改动空间 |

**这说明什么（判断）**：
- 「x86 还是 ARM」不是性能选型，而是**隔离形态选型**：要 VM 级隔离 + 快照 → 倾向 x86 或 ARM 裸金属；要原生 ARM 应用 + 低成本密度 → 倾向 ARM 容器。
- 用户关心的「同等实例数下成本 / 功耗」没有可引用的公开同口径数据，最诚实的结论是：目前只有厂商口径的 −30%（单一场景），其余需要自测。

---

## 待核实

1. 国内云手机（华为云 CPH 鲲鹏、火山引擎 ACEP、阿里无影、腾讯云）的架构、单服务器密度、容器还是虚拟机、是否用裸金属 ARM。预算用完，未查。
2. ARM-only 应用在 Play 或国内应用市场的占比，ARM→x86 翻译层的覆盖率和性能损失（官方无 benchmark）。
3. 银行、支付、强风控应用在 x86 翻译 / ARM 服务器容器 / 真机云手机上的可用性。
4. GCP、Azure 的嵌套虚拟化政策（含 Arm 实例：Axion、Cobalt）。
5. ARM 服务器发行版默认页大小（64 KB 的说法是背景知识，未核实），以及 Amazon Linux 2023 / Ubuntu on Graviton 的默认页大小。
6. G5g「最多 55 路 720p30、成本低 20%」是 WebSearch 摘要转述，未在原文核到。
7. 个人博客称 redroid 标准镜像含 32 位 ARM 库会在 Graviton 上 kernel panic，未在官方来源核实。
8. Google「ARM 翻译比全 ARM 模拟快 10 倍以上」只出现在搜索摘要，抓取的博客页面没有该数字。
9. Cuttlefish 在 x86 与 ARM 宿主上的 GPU 模式（gfxstream 等）：抓取的页面未提，待查 `gpu` 文档页。
10. libndk_translation 是否随 Android 16 / 17 的 AOSP x86 镜像继续提供，授权是否变化。
11. AWS 嵌套虚拟化的性能开销数字（文档只说建议敏感负载用裸金属）。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| [1] | Run ARM apps on the Android Emulator（Android Developers Blog） | https://android-developers.googleblog.com/2020/03/run-arm-apps-on-android-emulator.html | 2020-03-26 | 已抓 |
| [2] | 搜索摘要：ARM translation / libndk_translation / Houdini 的二手资料（含 Chrome OS ARC 的说明） | 见 WebSearch 结果，未逐个打开 | — | 二手 |
| [3] | remote-android/redroid-doc README | https://raw.githubusercontent.com/remote-android/redroid-doc/master/README.md | master，列到 Android 16 | 已抓 |
| [4] | AOSP binary_translation（Berberis）README | https://android.googlesource.com/platform/frameworks/libs/binary_translation/+/refs/heads/main/README.md | main，WIP | 已抓（WebFetch 摘要） |
| [5] | Streaming Android games from cloud to mobile with AWS Graviton-based G5g instances（AWS Compute Blog） | https://aws.amazon.com/blogs/compute/streaming-android-games-from-cloud-to-mobile-with-aws-graviton-based-amazon-ec2-g5g-instances | 日期待核实 | 已抓 |
| [6] | 基于 Graviton4 实例和 Redroid 搭建云手机（AWS 中国博客） | https://aws.amazon.com/cn/blogs/china/building-a-cloud-phone-based-on-graviton4-instance-and-redroid/ | 日期待核实 | 已抓（curl 提取文本） |
| [7] | Support 16 KB page sizes（Android Developers） | https://developer.android.com/guide/practices/page-sizes | 2026-11 在线版 | 已抓 |
| [8] | Play Integrity API verdicts | https://developer.android.com/google/play/integrity/verdicts | 2026-11 在线版 | 已抓 |
| [9] | redroid-doc deploy/README.md 与 deploy/amazon-linux.md | https://raw.githubusercontent.com/remote-android/redroid-doc/master/deploy/README.md | master | 已抓 |
| [10] | Use Cuttlefish（AOSP） | https://source.android.com/docs/devices/cuttlefish/get-started | 2026-11 在线版 | 已抓 |
| [11] | Use Cuttlefish with 16 KB page size on ARM64 | https://source.android.com/docs/core/architecture/16kb-page-size/getting-started-cf-arm64-pgagnostic | 2026-11 在线版 | 已抓 |
| [12] | Configure hardware acceleration for the Android Emulator | https://developer.android.com/studio/run/emulator-acceleration | 2026-11 在线版 | 已抓 |
| [13] | Anbox Cloud requirements | https://canonical.com/anbox-cloud/docs/reference/requirements/ | 2026-11 在线版 | 已抓 |
| [14] | Anbox Cloud supported rendering resources 与 capacity planning | https://canonical.com/anbox-cloud/docs/reference/supported-rendering-resources/ | 2026-11 在线版 | 已抓 |
| [15] | AWS adds nested virtualization option for EC2（The Register、InfoQ）与 AWS What's New 2026-02、2026-06 | https://www.infoq.com/news/2026/03/aws-ec2-nested-virtualization/ | 2026-02 / 2026-03 / 2026-06 | 二手（WebSearch 摘要，未打开原文） |
| [16] | Amazon EC2 nested virtualization（User Guide） | https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.md | 2026-11 在线版 | 已抓 |
| [17] | Linux 6.11（KernelNewbies）；LWN 877175 / 928426（NV 补丁系列） | https://kernelnewbies.org/Linux_6.11 | 6.11 | 已抓（KernelNewbies）；LWN 为搜索摘要 |
| [18] | Configure and run nested virtualization on an Arm server（Arm Learning Path） | https://learn.arm.com/learning-paths/servers-and-cloud-computing/nested-virtualization/1-preparation/ | 2026-11 在线版 | 已抓 |
| [19] | Running Android in the cloud with Amazon EC2 A1 instances（Canonical） | https://canonical.com/blog/running-android-in-the-cloud-with-amazon-ec2-a1-instances | 约 2018 | 二手（搜索摘要） |
| 主线程 | CubeSandbox issue #1878、PR #1879 等 | 见提示词「主线程已核实的事实」 | 2026-09 / 2026-10 | 引用主线程结论，未重抓 |

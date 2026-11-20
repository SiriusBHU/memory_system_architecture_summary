# 手机侧 Agent 沙箱（OpenMinis、Napaxi 与系统原生方案）

> 日期：2026-11-15。抓取版本：OpenMinis 主干（HEAD）及 Android 1.16-beta.6 build 44（2026-11-15 发布）；Napaxi 主干（HEAD，pushed 2026-11-16）及 sdk-v1.0.0（2026-07-02）。
> 检索实际用量：WebFetch 7 / WebSearch 4 / 源码与文档文件 15（curl）/ api.github.com 5。
> 证据等级：官方文档 / 源码 / 厂商自报 / 二手 / 估算 / 判断。源码指仓库主干的代码与代码注释，是「实现了什么」的强证据，但不等于「在所有机型上表现如何」。

## 结论

1. **OpenMinis 的 Android 沙箱是 PRoot 用户态 chroot，不是安全边界。** 命令行为 `proot -0 --link2symlink -r <alpine rootfs> -b /dev -b /proc -b /sys -w /root ...`，每条命令起一个新的 proot 进程（process-per-command），没有常驻内核 [源码 S1]。proot 与 App 同 uid、同 SELinux 域（untrusted_app），隔离强度等于 App 沙箱本身，只提供路径视图隔离 [判断]。
2. **Napaxi 的「Trusted sandbox」在 Android 上也是 PRoot，iOS 上是 QEMU user-mode（aarch64-linux-user）静态库，不是 WASM、QuickJS 或 seccomp。** 文档的架构图原文是「Android PRoot / iOS QEMU platform environments where enabled」[源码 S6][S7]。隔离的实际内容：`env_clear()` 清空宿主环境变量，只绑定 `/workspace`、`/skills` 与 `/proc /dev /sys`，另有超时（1–600 s 钳位）和取消 [源码 S8]。强隔离靠的是上层的策略闸门（工具描述符准入、调用准入），不是沙箱本身 [官方文档 S6][S7]。
3. **两个项目的 rootfs 都是 Alpine aarch64 minirootfs（OpenMinis 3.21.3），打进 APK 随包分发。** OpenMinis 的 Android arm64 APK 为 47.58 MB（build 44）[厂商自报 S3，GitHub Release 元数据]；其 rootfs 准备脚本只用 curl 下载，没有校验和 [源码 S4]。Napaxi 的 `bake_android_rootfs.sh` 对下载的归档做 sha256 校验 [源码 S9]，是对比中更严谨的一方，但对最终 rootfs 资产本身的完整性校验未见 [判断]。
4. **PRoot 的真实代价不在性能，在兼容性。** OpenMinis 源码里累积了大量补丁：`--link2symlink`（Android 的 /data 拒绝跨目录 hardlink，apk 装 busybox applet 会 EPERM）、`--fake-netlink`（untrusted_app 不能建 NETLINK_ROUTE 套接字）、`PROOT_NO_SECCOMP=1` 重试（某 ARM64 机型上 `apk` 在 ptrace+seccomp 交互下以 SIGBUS/SIGSEGV 立刻死亡，GH#186；仅当「致命信号 + 死于 1.5 s 内 + 无输出」才重试一次）[源码 S1][S2]。PRoot 的 syscall 拦截开销**没有找到任何公开实测**，只能写「待核实」。
5. **OpenMinis 把「真正危险或平台特有」的能力移出沙箱，用 native offload 走抽象 unix socket 交给宿主进程**：`--native-offload=<socket>:<handler,...>` 是它自己 fork 的 proot 的扩展参数；handler 覆盖无障碍、Shizuku、日历、联系人、相册、通知、闹钟、定位、浏览器等 [源码 S1，文件清单 S11]。所以沙箱内的 Linux 能力（包管理、Python、git）与设备能力（跨应用 UI、特权操作）走两条通道，权限边界落在宿主 App 的 Manifest 上，而 Manifest 申请了 29 项权限，含 `MANAGE_EXTERNAL_STORAGE`、`SYSTEM_ALERT_WINDOW`、`REQUEST_INSTALL_PACKAGES`、`moe.shizuku.manager.permission.API_V23`，并声明了无障碍服务 [源码 S5]。
6. **系统原生 VM 级隔离在 2026 年仍然不可被第三方量产使用。** Linux Terminal（AVF 上的 Debian）要求**非保护（non-protected）VM**；报道称 Snapdragon 8 Elite 只支持保护 VM，所以 Galaxy Z Flip 7（Exynos 2500）成了首个非 Pixel 支持机型 [二手 S13]。Android 17 QPR1 beta 1 给 Terminal 增加显示分辨率选项（Full/Half/Quarter）和内存上限选项，未给数值 [二手 S12]。`MANAGE_VIRTUAL_MACHINE` 对第三方 App 开放与否，官方文档中未找到，待核实。Google 的 Computer Control 则只开放给 OEM 预装助手（特权权限 `ACCESS_COMPUTER_CONTROL`，一个会话最多 6 个目标应用，同一时间 1 个会话）[官方文档 S10]。

## 1. AS5-Q1 OpenMinis

### 1.1 沙箱怎么实现

| 项 | 内容 | 等级 | 来源 |
|---|---|---|---|
| 仓库与许可 | github.com/OpenMinis/OpenMinis，GPLv3；是私有开发树的镜像，不收 PR | 厂商自报（README） | S3 |
| 平台实现 | Android：PRoot（自己的 fork，talloc 静态链接）；iOS：iSH 的 ARM64 fork | 厂商自报 | S3 |
| 命令行 | `proot -0 --link2symlink -r <rootfs> -b /dev -b /proc -b /sys -w /root [-b host:linux ...] [--native-offload=...] --fake-netlink /bin/sh -c "<cmd>"` | 源码 | S1 |
| 运行模型 | 每条命令一个 proot 进程，`PRootKernel` 只持有配置并拼命令行（注释写明 "process-per-command, not a persistent kernel"） | 源码 | S1 |
| rootfs | Alpine 3.21.3 aarch64 minirootfs（`alpine-minirootfs-3.21.3-aarch64.tar.gz`），作为 `assets/alpine-minirootfs.tar.gz` 打进 APK，首启用手写 POSIX tar 解析器解压到私有目录 | 源码 | S4, S1b |
| proot 二进制 | `deps/build_proot.sh` 从源码构建，作为 `jniLibs` 里的 `.so` 由包管理器解压到 nativeLibDir 后执行（`extractNativeLibs="true"`）；loader 内嵌于 proot 并经 `/proc/self/fd` 取出 | 源码 | S1, S5 |
| rootfs 来源与校验 | 构建时 `curl -fSL` 从 dl-cdn.alpinelinux.org 下载，**脚本里无 sha256 / 签名校验** | 源码 | S4 |
| 体积 | 整个 arm64 APK 47.58 MB（build 44）、46.87 MB（build 43）；rootfs 解压后大小由 UI 统计，未给数值 | 厂商自报（Release 元数据） | S3 |
| 版本与发布节奏 | Android 1.16-beta.5 于 2026-11-10，beta.6 于 2026-11-15 | 厂商自报 | S3 |

### 1.2 隔离边界在哪

- **边界层级**：PRoot 通过 ptrace 拦截 syscall，在用户态重写路径（chroot、bind）、模拟 `-0` 的假 root uid；内核看到的仍是 App 进程。它没有 namespace、cgroup、capability 的收缩，也没有独立 SELinux 域 [机制判断，依据 PRoot 的通用实现与 OpenMinis 命令行]。
- **直接证据**：`--fake-netlink` 的注释写明「Android 的 untrusted_app SELinux 域不能创建 AF_NETLINK/NETLINK_ROUTE 套接字，拒绝来自真内核」，说明沙箱内进程受宿主 SELinux 域约束，PRoot 并不改变这一点 [源码 S1]。
- **绑定挂载面**：`/dev`、`/proc`、`/sys` 直接绑定宿主，加上 `memory`、`skills`、`shared`、`mcp-servers`、`mounts/<name>`（用户选的外部目录）以及每会话私有的 `workspace`、`attachments`、`offloads`、`browser`；每会话目录通过各 shell 自己的 argv 绑定，避免全局映射被后写者覆盖（T-android-session-private-mounts）[源码 S1]。
- **假象风险**：作者自己在注释里承认 `--fake-netlink` 是「对 guest 程序说谎」，且当前对用户无开关，标注「仅限内部测试」[源码 S1]。
- **判断**：这是**路径与环境隔离，不是信任隔离**。让模型在其中执行任意命令，风险由 App 的权限面决定（见 1.4）。

### 1.3 Agent 能做什么与性能

| 能力 | 实现 | 等级 | 来源 |
|---|---|---|---|
| 包管理 | Alpine `apk`；有镜像测速与自动切换 UI（MirrorSpeedTest） | 源码 | S1 |
| Python / Node / Go / git | 在 rootfs 内安装；默认环境注入 `PYTHONDONTWRITEBYTECODE=1`、`GOMAXPROCS=2`、`UV_LINK_MODE=symlink`、git `core.createObject=rename`（绕开 link2symlink 的 `.l2s.*` 哨兵文件问题） | 源码 | S1 |
| 浏览器自动化 | `BrowserUseOffloadHandler`，在宿主进程执行 | 源码（文件清单） | S11 |
| 跨应用 UI | `AccessibilityOffloadHandler`（约 66 KB）+ `MinisAccessibilityService`；`ShizukuOffloadHandler` 做特权操作 | 源码 | S11, S5 |
| 设备能力 | 日历、联系人、相册、通知、闹钟、定位、剪贴板、语音等 offload handler | 源码 | S11 |
| 执行调度 | `ExecutionCoordinator`、`GlobalShellThrottle`、`ShellTimeoutPolicy`、`PersistentShell`、`FreshProcessShell` | 源码（文件名） | S11 |
| 性能开销 | PRoot ptrace 的启动与 syscall 开销**未找到公开测量**；仅有 `EARLY_DEATH_MS=1500` 的注释称冷启动动态链接 apk「远小于 1 秒」 | 待核实 / 源码注释 | S2 |

**自愈策略值得记录**：`SeccompFallbackPolicy` 把「重试」的触发限定为 `exit ∈ {132,135,139,159}`（SIGILL/SIGBUS/SIGSEGV/SIGSYS）且 `< 1500 ms` 且**无输出**且未重试过，原因是避免对有副作用的命令重放；SIGKILL(137)/SIGTERM(143) 被明确排除，因为它们是自己的超时、取消或 Android 低内存查杀 [源码 S2]。这是「沙箱不可靠时如何安全重试」的一个具体样本。

### 1.4 安全问题

| 问题 | 事实 | 等级 | 来源 |
|---|---|---|---|
| PRoot 不是安全边界 | 与宿主 App 同 uid / 同 SELinux 域；沙箱内进程能通过绑定的 `/proc`、`/sys`、`/dev` 与宿主交互 | 判断（依据命令行与注释） | S1 |
| rootfs 校验 | 构建脚本无校验和；运行时 `RootfsManager` 只做 tar 解压与进度，未见完整性校验 | 源码 | S4, S1b |
| 权限面 | Manifest 29 项：`INTERNET`、`REQUEST_INSTALL_PACKAGES`、`MANAGE_EXTERNAL_STORAGE`、`SYSTEM_ALERT_WINDOW`、`READ/WRITE_CONTACTS`、`READ/WRITE_CALENDAR`、`ACCESS_FINE_LOCATION`、`CAMERA`、`RECORD_AUDIO`、`RECEIVE_BOOT_COMPLETED`、`SCHEDULE_EXACT_ALARM`、`moe.shizuku.manager.permission.API_V23` 等；另有无障碍服务 | 源码 | S5 |
| 沙箱到宿主的回调通道 | offload 走抽象 unix socket；注释称仅在自己的 server 正在监听时才加参数，避免连接到被别的进程占用的同名 socket 而挂起 | 源码 | S1 |
| 网络出口 | 有 `ShellTransparentNet`（对忽略代理变量的 ssh、nc 的 TCP 透明转发，按设置页路由文件控制），是出口控制的雏形，不是策略引擎 | 源码 | S1 |

**这说明什么。**（判断）OpenMinis 的设计取舍是：沙箱负责「给模型一台能装软件的 Linux」，隔离靠 App 沙箱，真正危险的设备能力在宿主侧用权限弹窗和 offload 管理。它不是为「防住恶意代码」设计的，而是为「功能完整、兼容 Linux 工具链」设计的。要把它当作 Agent 沙箱的参照，应当把它的价值定位为「手机上能跑什么」的上限样本，而非隔离样本。

## 2. AS5-Q2 Napaxi

### 2.1 架构与平台

| 项 | 内容 | 等级 | 来源 |
|---|---|---|---|
| 归属与状态 | github.com/antgroup/napaxi；GPL-3.0-or-later；SDK 1.0（sdk-v1.0.0，2026-07-02）；仓库创建 2026-07-01；34 星 | 厂商自报 / API | S6, S3b |
| 定位 | 嵌入宿主 App 的移动 Agent SDK，不带产品 UI；宿主保有 UI、账号、模型配置、权限和产品策略 | 官方文档 | S6 |
| 层次 | 宿主 App → SDK 适配层（Flutter / Android / iOS）→ `packages/api_bridge`（FFI/FRB）→ `napaxi_core::api` → Rust 运行时 → 特性 crate（skills、evolution）→ Android PRoot / iOS QEMU | 官方文档 | S6, S7 |
| 平台 | Flutter（首个完整适配）、Android Kotlin、iOS Swift Package | 官方文档 | S6 |
| 工具体系 | 14+ 内置移动工具、model-as-tool、MCP、宿主自定义工具；Agent Provider 协议（Agent App actions） | 官方文档 | S6 |
| 联网 | 除宿主批准的模型调用外，运行时不依赖 Napaxi 云服务 | 厂商自报 | S6 |

### 2.2 沙箱实现与隔离边界

| 项 | Android | iOS | 来源 |
|---|---|---|---|
| 机制 | PRoot + Alpine aarch64 rootfs；二进制是 `libproot.so`，另有 `libldmusl.so` 绑到 `/lib/ld-musl-aarch64.so.1`、`libloader.so` 作 `PROOT_LOADER` | `napaxi.platform.ios_qemu`：QEMU `aarch64-linux-user`（仓库自带 41.8 MB 的 `libqemu-aarch64-linux-user.a` 等静态库）+ 自备 rootfs；用户态模拟，无 JIT 虚拟化 | 源码 S8, S7, S11b |
| 命令构造 | `-r rootfs -b workspace:/workspace -b skills:/skills -w <cwd>` + 绑 `/proc /dev /sys` | 同层 API，后端不同 | 源码 S8 |
| 环境 | `env_clear()`；仅注入 HOME、PATH、TERM=xterm-256color、LANG、TERMINFO、`LD_LIBRARY_PATH`、`PROOT_TMP_DIR` | 待核实 | 源码 S8 |
| 超时与取消 | 超时钳位 1–600 s；SIGTERM 后宽限 2 s 再 SIGKILL；支持用户取消；按进程组 kill | — | 源码 S8 |
| 版本管理 | `ROOTFS_VERSION=3`；rootfs 目录有 `.version`，版本不符或缺 `bin/sh`、`sbin/apk` 则删掉重解压 | — | 源码 S8 |
| 预装 | `python3 py3-pip nodejs npm curl bash zip unzip git qemu-x86_64 gcompat` 及 OpenJDK 17、Codex CLI、Android APK 构建工具、x86_64 运行库闭包（给 aapt2、zipalign 用） | iOS 用更小的 profile：无 Codex、OpenJDK、Android SDK、qemu-x86_64 | 源码 S9 |
| 与 PRoot 的差异 | 没有 `-0` 假 root，没有 `--link2symlink`、`--fake-netlink`、`--native-offload`（至少在该文件里未见） | — | 源码 S8 对比 S1 |
| 没有的东西 | 在 `docs/architecture.md`、`mobile-capabilities.md`、`android_linux_env.rs` 中**未见** WASM、QuickJS、seccomp 或 isolatedProcess | — | S7, S8，按全文检索 |

- **隔离边界**：与 OpenMinis 相同，是 App 内的用户态路径隔离。文档把「Trusted sandbox」描述为「移动沙箱 + 策略闸门 + 宿主控制的授权」三者的组合 [厂商自报 S6]；真正起约束作用的是后两者：核心在**工具描述符准入、工具调用准入、provider 准入、模型切换**四处设闸 [官方文档 S6]。
- **与宿主应用的权限关系**：沙箱不自己申请权限。外部权限、平台工具、文件、渠道、后台能力都由宿主 App 决定是否暴露；平台工具与后台执行属于适配层，必须显式通过 SDK API 暴露 [官方文档 S6]。Android 适配层 Manifest 约 3.2 KB（Flutter 包 5.7 KB）[源码，文件清单 S11b]，具体权限未逐条读，待核实。
- **安全流程**：SECURITY.md 要求私下披露，3 个工作日内确认、10 个工作日内初评；对集成方的加固建议中有「capability profile：只声明宿主能安全执行的能力」[官方文档 S6b]。注意 `process-hosting-roadmap.md` 写明当前**没有**「secret egress proxy」，相应检查项要等该能力落地后才执行 [官方文档 S10b]。
- **典型工作负载**：在 PRoot 中以 PTY 启动 `codex app-server`，Android 走 PRoot 后端、iOS 走 QEMU 后端，二者共享烘焙好的 rootfs；Codex 发出的 `item/tool/call` 由 core 执行并回到工具桥 [官方文档 S7b]。演示场景是「在手机上生成、构建、安装 Android APK」。
- **性能或体积数据**：未找到启动时间、内存、rootfs 体积的公开数值（rootfs 资产在仓库中是 134 字节的 Git LFS 指针）[源码 S11b]，待核实。

**这说明什么。**（判断）Napaxi 与 OpenMinis 用了同一类沙箱（PRoot + Alpine），说明「手机上给 Agent 一台 Linux」在无特权的第三方 App 里目前只有这条现实路径。差别在于：OpenMinis 是产品，沙箱与设备能力打包在同一个 App；Napaxi 是 SDK，把「是否给 Agent 这些权限」留给宿主，并用策略闸门补强。两者都没有把 Agent 与宿主 App 之间做成不同的信任域。

## 3. AS5-Q3 系统原生沙箱能力

### 3.1 AVF / Linux Terminal / Microdroid（只补 2026 新进展；基础见 C2 §3 Q6、Q7）

| 项 | 事实 | 等级 | 来源 |
|---|---|---|---|
| AVF 架构 | pKVM 扩展 KVM；保护型 VM 的 guest 内存在移交时从宿主取消映射，宿主不能访问，除非 guest 显式共享（如 virtio）；VM 停止后内存由 hypervisor 擦除并还给宿主内核；AVF 面向 ARM64，x86_64 仅「测试用途，非保护 VM」 | 官方文档 | S14 |
| 硬件前置 | 每个 DMA 设备需 IOMMU（推荐 Arm SMMU）；PSCI；有 S-EL2 时需要 Hafnium 之类的安全分区管理器；ABL 需加载校验 pvmfw 并提供 DICE 秘密 | 官方文档 | S14 |
| 第三方权限 | 官方架构页与 custom_vm 页都**没有**写 `MANAGE_VIRTUAL_MACHINE` / `USE_CUSTOM_VIRTUAL_MACHINE` 的持有者规则；custom_vm 的流程需要 root 的 AVF 设备（`adb root`、`vm run <config>`） | 官方文档（空白） | S14, S15 |
| Linux Terminal 机型 | 2025-03 起在 Pixel 上预览；Terminal 需要**非保护 VM**。报道称 Snapdragon 8 Elite 只支持保护 VM，Exynos 2500 支持非保护 VM，Galaxy Z Flip 7 为首个非 Pixel 支持机型 | 二手 | S13 |
| Android 17 变化 | Android 17 QPR1 beta 1（报道日期 2026-04-24）：Terminal 增加「显示分辨率」设置 Full / Half / Quarter；Android 17 beta 中已有内存上限选项（数值未给），确认进入稳定版 | 二手 | S12 |
| 图形 | 报道称 Terminal 曾用 Lavapipe（CPU 渲染），gfxstream 为方向；**没有找到 gfxstream 在 Android 17 稳定版落地的证据** | 二手 / 待核实 | S12 |
| 实测样本（个人指南，非官方） | Pixel 6、Pixel 10 Pro（Tensor G5）在 Android 17 上，2026-05-26 复测：VM 内存默认 1024 MiB，滑块最大约宿主 RAM 的三分之二；根盘 103 GB，Debian 镜像下载数百 MB、实际占用约 2 GB；8 核可见；内核 6.12.x；屏幕关闭时 VM 被杀，除非开启 Keep awake（1 分钟到 1 天），官方对话框称会「显著影响电池」；移动数据需「无限制」设置；非正常关机会把 VM 标成损坏，需重装；无 USB 直通；nftables 不可用；SysV IPC 在内核中禁用。启动时间未给 | 二手（个人指南，日期自相矛盾） | S16 |
| Microdroid | 本轮没有取得新的 2026 数据；沿用 C2 的 C 级结论（量级 32–42，疑为 MB，绝对值未取得） | — | C2 §3 Q7 |

判断：
- **Terminal 的可用性取决于芯片厂商是否开放非保护 VM**，不是 Android 版本。Snapdragon 8 Elite 的例子说明同一代旗舰芯片也可能不满足。
- **屏幕关闭时 VM 被杀**这一点对 Agent 沙箱是硬伤：Agent 的价值恰恰在于用户不看屏幕时继续执行。Keep awake 是一个用电池换存活的手动开关，不是 Agent 沙箱可以依赖的生命周期。
- 第三方 App 能否合法创建 VM 仍没有官方答案；在这一点落地前，VM 级隔离只能由 OEM 或系统应用提供。

### 3.2 后台虚拟屏与系统级 GUI 执行

| 方案 | 机制 | 隔离与限制 | 等级 | 来源 |
|---|---|---|---|---|
| Google Computer Control（预览） | OEM 预装的助手持特权权限 `ACCESS_COMPUTER_CONTROL`，把目标应用启动在「安全的后台虚拟屏」上，类似投屏；助手截屏并模拟点击、滑动、文本输入；首次操作某应用时系统弹出授权对话框；可把控制权交还用户（交易确认等） | 一个会话最多 6 个目标应用，顺序执行；同一时间 1 个活动会话；目标应用无需改造；助手可自行限定目标应用集合；文档标注为预览，仅支持有限的目标应用集 | 官方文档 | S10 |
| 豆包手机助手 | 外部分析称：声明 `INJECT_EVENTS`，通过反射调用 `InputManager.injectInputEvent()` 注入事件；使用 `VirtualDisplay` 把目标应用放到虚拟屏；另有开发者称其声明了 `CAPTURE_SECURE_VIDEO_OUTPUT`。官方回应称 `INJECT_EVENTS` 是系统级权限、需用户授权并在权限清单披露 | 机制细节均为第三方推测，**非官方确认**；官方只确认了权限声明 | 二手 | S17 |
| 荣耀 YOYO、鸿蒙小艺 | 本轮检索只找到功能描述（点咖啡、比价、领券；小艺 GUI 操作），**没有找到后台执行或虚拟屏隔离的官方技术说明** | 待核实 | 二手 / 待核实 | S17, C2 Q6 |
| Termux / proot-distro 里跑 CLI Agent | Claude Code 无 Termux 原生 android-arm64 构建（上游 issue「not planned」），可用路径为 glibc-runner、proot-distro Ubuntu、固定旧版本；Android 12+ 的 phantom process killer 会把超过 32 个子进程或 CPU 过高的进程用 SIGKILL 杀掉，proot-distro 不能绕开 | 厂商软文为主，细节需核实 | 二手（含竞品厂商宣传） | S18 |

- **内存与 GPU 代价、对前台的干扰**：Computer Control 文档没有给出虚拟屏的内存、GPU 或对前台的干扰数据；一个虚拟屏上的应用与主屏应用一样占用应用进程内存，受 LMKD 约束 [机制判断，无实测]。**没有找到公开实测**，待核实。
- **「沙箱」的含义**：虚拟屏隔离的是**显示与输入焦点**，不隔离数据与权限，目标应用仍以用户身份在用户数据上运行。这是「不打扰前台」，不是「防止 Agent 越权」[判断]。Google 的防护靠三件事：特权权限只给 OEM 预装助手、首次逐应用授权、敏感步骤交还用户 [官方文档 S10]。
- **各家手机厂商是否有隔离执行环境**：在公开资料里，豆包、荣耀、小艺都没有看到「隔离的执行环境」的官方描述；已有官方文字的只有 Google 的虚拟屏 + 授权对话框 [综合判断，证据来自 S10、S17、C2 Q6]。

## 4. AS5-Q4 端侧沙箱形态对比与性能诉求

### 4.1 四类端侧沙箱对比

「内存」「启动」两列：有公开数据的写数据，没有的写「无公开测量」。本表中的估算项明确标「估算」。

| 形态 | 代表 | 隔离强度 | 内存 | 启动 | 能力范围 | 可用性 | 来源 |
|---|---|---|---|---|---|---|---|
| 用户态（路径虚拟化） | OpenMinis、Napaxi（Android PRoot） | 弱：同 uid、同 SELinux 域，ptrace 拦截只改路径视图 | 每条命令一个 proot 进程加 guest 进程自身 RSS；无公开测量 | 无公开测量；冷启动 apk 动态链接 < 1 s（仅代码注释） | 最宽：完整 Alpine 用户态、包管理、Python / Node / git；仅限 aarch64 用户态程序（x86_64 要靠 qemu-x86_64 用户态模拟，Napaxi 的 aapt2 就走这条） | 任何 Android 机型、无需特权；受 phantom process killer 与 ptrace 兼容性（GH#186）影响 | S1, S2, S8, S9 |
| 用户态（指令集模拟） | Napaxi（iOS QEMU user-mode）、OpenMinis（iOS iSH 的 ARM64 fork） | 弱到中：模拟器内核态 syscall 由宿主实现；iOS 无 JIT 虚拟化，所以走解释 / 翻译 | 无公开测量；仅有 QEMU 静态库 41.8 MB 的体积样本 | 无公开测量 | 宽，但速度慢于原生 | iOS 无其他选择 | S3, S7, S11b |
| 进程级 | `isolatedProcess`、seccomp、SELinux 域 | 中：独立 uid、独立 SELinux 域，无文件与网络权限；seccomp 可收紧 syscall | 近零额外开销，主要是进程 RSS（机制推断） | 毫秒级（机制推断） | 窄：无 Linux 用户态，无包管理；适合受控计算（解析、脚本引擎、插件） | 所有 Android 机型；两个 PRoot 项目都**没有**用它 | C2 Q6、Q7（判断） |
| VM 级 | AVF / pKVM（Linux Terminal、Microdroid） | 强：保护型 VM 内存对宿主不可见；Terminal 使用的非保护 VM 则只有 KVM 级隔离 | Terminal 默认 1024 MiB，上限约宿主 RAM 的三分之二；Microdroid 量级 32–42（疑为 MB，C 级）；手机承载量 10–33 个为 D 级估算（C2） | 无公开测量 | 完整 Linux 内核与用户态；GPU 为软件渲染（Lavapipe）为主；无 USB 直通；nftables、SysV IPC 受限 | 窄：芯片是否支持非保护 VM 决定；第三方权限未开放；屏幕关闭时 VM 被杀 | S12–S16, C2 |
| 虚拟屏级 | Computer Control、豆包手机助手 | 只隔离显示与输入焦点，不隔离数据与权限 | 目标应用进程内存 + 虚拟屏缓冲；无公开测量 | 应用冷启动时间（无公开测量） | 只能操作 GUI；每步依赖截屏与推理 | OEM 预装助手专用；特权权限 | S10, S17 |

### 4.2 手机侧的性能诉求与约束

下列每条都是约束，而不是实测：

| 约束 | 事实或机制 | 等级 | 来源 |
|---|---|---|---|
| 内存预算与 LMKD | PRoot 沙箱的 guest 进程是 App 的子进程，被 LMKD 杀时报 137，OpenMinis 因此特意把 137/143 排除在重试条件外 | 源码 | S2 |
| 进程数与后台查杀 | Android 12+ 的 phantom process killer 以子进程数（报道称 32）与 CPU 为条件杀进程；proot-distro 不能绕开 | 二手 | S18 |
| 功耗与保活 | Terminal 的 VM 在屏幕关闭时被杀，Keep awake 以电池换存活；OpenMinis 申请 `WAKE_LOCK`、`REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`、前台服务（mediaPlayback、dataSync）以持续运行 | 二手 / 源码 | S16, S5 |
| 存储与 UFS 写入 | Alpine rootfs 经 apk 持续写入；link2symlink 产生 `.l2s.*` 哨兵文件，git/uv 等需要环境变量规避；Terminal 的 Debian 实际占用约 2 GB | 源码 / 二手 | S1, S16 |
| 热与持续负载 | 未找到手机沙箱持续负载下的热或降频测量 | 待核实 | — |
| 安全与能力权衡 | PRoot 系的价值在能力宽、无需特权；缺的是隔离强度；AVF 反之 | 判断 | — |

**这说明什么。**（判断）
1. 在无特权的第三方 App 里，沙箱只有「PRoot / QEMU 用户态」一条现实路径，并且它的隔离强度等于 App 沙箱；强隔离只能由系统（pKVM、虚拟屏授权）提供，而系统能力又不对第三方开放。**能力强的不隔离，隔离强的不开放**，这是手机侧最核心的矛盾。
2. 本轮能拿到的性能数据极少：PRoot 开销、Terminal 启动时间、虚拟屏内存、Napaxi 沙箱资源，都是「无公开测量」。这本身就是结论：手机侧 Agent 沙箱的性能口径还没有人建立，而云侧已有 Firecracker 一类的数字。
3. 对 AgentOS 的含义：可行的组合是「系统层给 Agent 一个**会话级**的进程级沙箱（独立 uid + seccomp + 出口代理）+ 少数高风险会话走 pVM」，PRoot 式的完整 Linux 只在需要工具链时挂载。该组合在手机上**没有现成实现**。

## 待核实

- PRoot 的 ptrace 与 seccomp 加速的 syscall 开销（任何公开测量）；Android 机型差异（GH#186 只有单个报告机型）。
- OpenMinis 解压后 rootfs 大小、首启时间、单命令启动时延；Napaxi 同上；Napaxi rootfs 资产（Git LFS）大小。
- Napaxi Android 适配层 Manifest 的具体权限；iOS QEMU 后端的运行时开销。
- `MANAGE_VIRTUAL_MACHINE`、`USE_CUSTOM_VIRTUAL_MACHINE` 对第三方 App 的开放条件（官方 AVF 文档页未写）；Android 17 稳定版对 AVF 的正式变化；Linux Terminal 的官方机型清单与启动时间；gfxstream 是否在 Android 17 稳定版落地。
- 荣耀 YOYO、鸿蒙小艺的后台执行与隔离机制的官方说明；豆包手机助手的虚拟屏与权限的官方技术说明（本轮只有第三方推测与官方的权限回应）。
- 后台虚拟屏的内存、GPU 与对前台干扰的实测。
- Termux 路线中 phantom process killer 的阈值（32 个子进程）与 Android 14+ 的关闭开关，来源多为竞品厂商文章，需官方文档核实。
- 本轮未打开：Android 官方 `VirtualDeviceManager` / `createVirtualDisplay` API 文档、Android 16 KB 页、Android 官方 Microdroid 文档。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| S1 | OpenMinis `PRootKernel.kt` | https://raw.githubusercontent.com/OpenMinis/OpenMinis/HEAD/src/android/app/src/main/java/com/openminis/app/sandbox/PRootKernel.kt | 主干，2026-11-15 抓取 | 已抓（读命令构造、注释，未读全文） |
| S1b | OpenMinis `RootfsManager.kt` | 同仓库 `.../sandbox/RootfsManager.kt` | 同上 | 已抓（grep 校验与解压逻辑） |
| S2 | OpenMinis `SeccompFallbackPolicy.kt` | 同仓库 `.../sandbox/SeccompFallbackPolicy.kt` | 同上 | 已抓 |
| S3 | OpenMinis README 与 Release 元数据 | https://github.com/OpenMinis/OpenMinis | build 44，2026-11-15 | 已抓（README）；Release 经 api.github.com |
| S3b | Napaxi 仓库与 Release 元数据 | https://github.com/antgroup/napaxi | sdk-v1.0.0，2026-07-02 | 经 api.github.com |
| S4 | OpenMinis `scripts/prepare_android_sandbox.sh`；`deps/prepare_alpine_rootfs.sh`（iOS） | 同仓库 | 同上 | 已抓 |
| S5 | OpenMinis `AndroidManifest.xml` | 同仓库 `src/android/app/src/main/AndroidManifest.xml` | 同上 | 已抓（grep 权限、服务） |
| S6 | Napaxi README | https://raw.githubusercontent.com/antgroup/napaxi/HEAD/README.md | 主干 | 已抓 |
| S6b | Napaxi SECURITY.md | 同仓库 `SECURITY.md` | 主干 | 已抓 |
| S7 | Napaxi `docs/architecture.md` | 同仓库 | 主干 | 已抓（grep 沙箱相关） |
| S7b | Napaxi `docs/mobile-capabilities.md` | 同仓库 | 主干 | 已抓（grep） |
| S8 | Napaxi `crates/core/src/platform/android_linux_env.rs` | 同仓库 | 主干 | 已抓（读命令构造、超时、版本管理） |
| S9 | Napaxi `tools/scripts/bake_android_rootfs.sh` | 同仓库 | 主干 | 已抓（读头部与校验逻辑） |
| S10 | Android Computer Control（预览） | https://developer.android.com/ai/computer-control | 2026-11-15 抓取 | 已抓（官方） |
| S10b | Napaxi `docs/process-hosting-roadmap.md`；`CHANGELOG.md` | 同仓库 | 主干 | 已抓 |
| S11 | OpenMinis 仓库文件清单（sandbox/offload 目录） | api.github.com git/trees | 主干 | 已抓 |
| S11b | Napaxi 仓库文件清单（platform、Vendor/IosQemu、LFS 指针） | api.github.com git/trees | 主干 | 已抓 |
| S12 | Android Authority：Android 的 Linux Terminal 性能与画质 | https://www.androidauthority.com/androids-linux-terminal-performance-vs-quality-3660716/ | 2026-04-24 | 已抓（二手） |
| S13 | Android Authority：Galaxy Z Flip 7 Linux Terminal | https://www.androidauthority.com/galaxy-z-flip-7-linux-terminal-3578675 | — | 抓取失败（403），内容来自检索摘要（二手） |
| S14 | AOSP：AVF 架构 | https://source.android.com/docs/core/virtualization/architecture | 2026-11-15 抓取 | 已抓（官方） |
| S15 | AOSP Virtualization：custom_vm.md | https://android.googlesource.com/platform/packages/modules/Virtualization/+/12f923ea7/docs/custom_vm.md | 12f923ea7 | 已抓（官方，未涉及权限） |
| S16 | 个人指南：Android Virtualization Framework (AVF): Path C | https://cdn.jsdelivr.net/gh/ferrumclaudepilgrim/claude-code-android@main/docs/avf-guide.md | 页内日期自相矛盾（2026-05-26 / 08-31 / 10-25） | 已抓（二手，个人实测） |
| S17 | 豆包手机助手权限与机制的技术报道（检索结果） | https://www.woshipm.com/ai/6302896.html 等；检索结果列表 | 2025-12 前后 | 检索摘要（二手，未打开原文） |
| S18 | Termux 上运行 Claude Code / Codex CLI / Gemini CLI 的检索结果 | https://cosyra.com/guides/claude-code-on-android.html 等 | 2026 | 检索摘要（二手，含竞品厂商宣传） |
| S19 | PRoot 仓库首页 | https://github.com/proot-me/proot | — | 已抓，信息量不足（无开销数据） |
| C2 | 本库：沙箱框架与执行能力 §3 Q6、Q7 | `../C2-沙箱框架与执行能力.md` | 2026-11 | 本地 |

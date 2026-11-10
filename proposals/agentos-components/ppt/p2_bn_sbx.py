"""第二部分 · 瓶颈分析：执行沙箱（报告 2.5.2）。版式：solution.problem-arch-callouts。
中央架构图在本模块自绘（当前手机上的 Agent 执行架构，以 Android 为主、注明 iOS 对应机制）；
两侧问题卡、扫描卡、连线、底部通栏与编号用 pages.bn_* 部件。"""

import lib
from lib import box, text
from pages import bn_badges, bn_bottom, bn_layer, bn_sep, bn_side
from registry import page


@page
def bottleneck_sandbox(prs):
    s = lib.new_slide(prs, "执行沙箱瓶颈分析：", "边界停留在 App 级，缺少会话快照、参数级策略、数据标签与出口托管",
                      crumb="二、场景与负载瓶颈 › 瓶颈分析 › 执行沙箱")

    # ---------------- 中央：当前手机上的 Agent 执行架构
    # 输入
    y = 90
    x1, wfull = bn_layer(s, y, 40, "输入")
    user = (x1, y + 3, 200, 34)
    ext_in = (x1 + 208, y + 3, wfull - 208, 34)
    box(s, user, "**用户指令**：T1、T2 前台等待", fill="peach_m")
    box(s, ext_in, "**第三方内容**：网页、消息、邮件", fill="pink_l", line="grey_d")
    bn_sep(s, y + 43)

    # 执行：Agent App
    y = 136
    bn_layer(s, y, 212, "执行")
    app = (x1, y + 2, wfull, 208)
    lib.outline(s, app, line="grey_d", width=1.0, kind="rounded", radius=8)
    lib.arrow(s, (user[0] + 100, user[1] + user[3]), (user[0] + 100, app[1]), color="dark")
    lib.arrow(s, (ext_in[0] + ext_in[2] / 2, ext_in[1] + ext_in[3]), (ext_in[0] + ext_in[2] / 2, app[1]), color="dark")
    text(s, (x1 + 6, y + 6, wfull - 12, 18), "**Agent App**：以自身 App 身份运行，边界为 UID 沙箱",
         style="detail", align="center", check=False)
    bw = (wfull - 16 - 2 * 8) / 3
    for i, (t, f) in enumerate([("**Agent 进程**\n模型规划与工具编排", "blue_l"),
                                ("**解释器与工具子进程**\n代码执行、文档解析", "blue_l"),
                                ("**子任务实例**\nT3 子任务、T4 批次", "green_l")]):
        box(s, (x1 + 8 + i * (bw + 8), y + 28, bw, 56), t, fill=f)
    hw = (wfull - 16 - 8) / 2
    box(s, (x1 + 8, y + 90, hw, 64), "**任务状态**\n解释器状态与中间产物\n只保存在进程内存中", fill="beige")
    box(s, (x1 + 16 + hw, y + 90, hw, 64), "**凭证**\n存于应用进程或 Keystore\n由应用取出使用，Agent 可见", fill="purple_l")
    text(s, (x1 + 8, y + 160, wfull - 16, 44),
         "!!系统中没有「Agent 会话」对象：一个会话分布在多个进程中，!!\n!!无法整体冻结、快照与记账!!",
         style="detail", align="center", valign="middle", check=False)
    bn_sep(s, y + 216)

    # 调用与出口
    y = 356
    bn_layer(s, y, 68, "出口")
    call = (x1, y + 2, 250, 64)
    net = (x1 + 258, y + 2, wfull - 258, 64)
    lib.arrow(s, (call[0] + 125, app[1] + app[3]), (call[0] + 125, call[1]), color="dark")
    lib.arrow(s, (net[0] + net[2] / 2, app[1] + app[3]), (net[0] + net[2] / 2, net[1]), color="dark")
    box(s, call, "**调用入口**：App Intents、AppFunctions、MCP\n**权限**：布尔值，按调用方静态放行", fill="blue_m")
    box(s, net, "**网络出口**：按 UID 管控\nAgent 进程直接出网，含 DNS", fill="pink_l", line="red", dash=True,
        line_width=1.5)
    bn_sep(s, y + 72)

    # 目标
    y = 432
    bn_layer(s, y, 48, "目标")
    apps = (x1, y + 3, 250, 42)
    ext = (x1 + 258, y + 3, wfull - 258, 42)
    lib.arrow(s, (call[0] + 125, call[1] + call[3]), (call[0] + 125, apps[1]), color="dark")
    lib.arrow(s, (net[0] + net[2] / 2, net[1] + net[3]), (net[0] + net[2] / 2, ext[1]), color="dark")
    box(s, apps, "**目标应用**：支付、消息、日历\n各自运行在 UID 沙箱中", fill="green_l")
    box(s, ext, "**外部网络与服务**", fill="grey_m")
    bn_sep(s, y + 52)

    # OS 隔离与回收机制
    y = 488
    bn_layer(s, y, 72, "OS")
    lw = 226
    box(s, (x1, y + 2, lw, 32), "**UID 沙箱**、SELinux、seccomp", fill="blue_l")
    box(s, (x1 + lw + 8, y + 2, wfull - lw - 8, 32), "**isolatedProcess**：单段代码", fill="blue_l")
    box(s, (x1, y + 38, lw, 32), "**AVF / pKVM**：机型受限", fill="beige")
    lmkd = (x1 + lw + 8, y + 38, wfull - lw - 8, 32)
    box(s, lmkd, "**LMKD**：内存紧张时终止进程", fill="pink_l", line="red", dash=True, line_width=1.5)

    targets = {
        "app": (app[0] + 4, app[1] + 4), "call": (call[0] + 4, call[1] + 4),
        "ext_in": (ext_in[0] + ext_in[2] - 4, ext_in[1] + 4), "net": (net[0] + net[2] - 4, net[1] + 4),
        "lmkd": (lmkd[0] + lmkd[2] - 4, lmkd[1] + 2),
    }

    # ---------------- 两侧问题卡与业界技术扫描卡
    bn_side(s, "left", [
        ("callout", "①", "边界粒度不匹配：隔离以 App 为单位而非以会话为单位，一个会话的风险跨越多个进程", 86, "app"),
        ("card", "E2B / 腾讯 CubeSandbox", "2024–2026 · 云端",
         "每个会话一个 microVM，池化与快照克隆；Cube 单并发创建 <60 毫秒（厂商自报）", "暂停约 4 秒/GiB，手机上无对应原语", 124),
        ("callout", "③", "静态权限无法判定单次调用：权限为布尔值，缺少金额、收件人等参数级约束；确认弹窗批准率约 93%", 86, "call"),
        ("card", "NVIDIA OpenShell", "2026-03 · NVIDIA 开源",
         "默认拒绝的 YAML 策略在 Agent 之外执行，打包出口代理与凭证注入，策略变更经证明器检查",
         "无数据标签；证明器只覆盖部分协议", 140),
        ("card", "AVF / Microdroid", "2023 起 · Google",
         "提供虚拟机级隔离；Android 14 的 Microdroid 比 13 启动快约 2 倍", "机型受限，无绝对时延与内存数据", 124),
    ], targets)
    bn_side(s, "right", [
        ("callout", "④", "不可信内容缺少来源标签：T2–T4 有 70%–100% 的读取来自第三方，OS 层没有数据标签", 86, "ext_in"),
        ("card", "CaMeL / FIDES", "2025 · DeepMind、微软研究院",
         "能力标签随数据值传播，控制流与数据流分离，由解释器在 Agent 之外执行策略", "任务完成率 77%，不设防基线为 84%", 124),
        ("callout", "⑤", "出口与凭证未托管：网络按 UID 管控，没有按会话的出口策略，凭证对 Agent 进程可见", 86, "net"),
        ("card", "Claude Code 本地沙箱", "2025–2026 · Anthropic",
         "Seatbelt / bubblewrap 进程级沙箱，出口经域名白名单代理，凭证留在宿主", "代理有两起绕过 CVE；DNS 为公认漏项", 140),
        ("card", "IsolateGPT", "NDSS 2025 · 华盛顿大学等",
         "中枢调度加应用级执行隔离，约束应用之间及应用与 LLM 的交互",
         "未涉及出口与数据标签，机制细节待核实", 124),
    ], targets)
    bn_bottom(s, "②", "缺少暂停、快照与恢复：内存紧张时 LMKD 直接终止进程，解释器状态与中间产物全部丢失", targets["lmkd"],
              "@@会话级隔离与状态底座@@（对应 ①②）、@@策略引擎与数据标签@@（对应 ③④）、@@出口代理与凭证托管@@（对应 ⑤）")
    bn_badges(s, targets, [("1", "app"), ("2", "lmkd"), ("3", "call"), ("4", "ext_in"), ("5", "net")])

    lib.footnote(s, "来源：报告 2.2.3 负载估算、2.5.2 瓶颈分析；P-C2 原型对比笔记；iOS 对应机制为 App Intents、App 沙箱与 Keychain。"
                    "确认批准率与 Cube 数据为厂商口径。", y=694)

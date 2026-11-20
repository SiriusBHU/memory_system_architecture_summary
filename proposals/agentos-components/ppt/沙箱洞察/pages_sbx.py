"""安卓 Agent 沙箱洞察 deck 的页面（2026-11-15）。

内容来自 ../../安卓Agent沙箱洞察.md 与 notes/AS1–AS6；页面库与风格沿用 ../lib.py。
文字标记：!!…!! 深红加粗（关键数字），@@…@@ 蓝色加粗（关键结论），**…** 加粗，~~…~~ 灰色（口径）。
"""

import math

import lib
from lib import (arrow, badge, box, measure, new_slide, outline, panel, rect, round_card, table, table_height,
                 text, footnote)

PAGES = []
CRUMB = "安卓 Agent 沙箱洞察"


def page(fn):
    PAGES.append(fn)
    return fn


# ---------------------------------------------------------------- 本模块的辅助函数

def conclusion_band(s, y, items, label="读表\n结论", bottom=686):
    """表下方的「读表结论」横带：左侧红色标签，右侧 n 栏结论（@@名称@@：说明）。"""
    h = bottom - y
    outline(s, (32, y, 1216, h), line="grey_line")
    text(s, (36, y, 64, h), label, style="label_big", align="center", valign="middle", check=False)
    n = len(items)
    x0, gap = 108, 14
    cw = (1240 - x0 - gap * (n - 1)) / n
    mds = [f"@@{name}@@：{body}" if name else body for name, body in items]
    style = "body" if max(measure(m, cw, "body") for m in mds) <= h - 10 else "detail"
    for i, md in enumerate(mds):
        x = x0 + i * (cw + gap)
        if i:
            rect(s, (x - gap / 2, y + 8, 0.75, h - 16), "grey_m")
        text(s, (x, y + 4, cw, h - 8), md, style=style, valign="middle")


def card(s, b, title, md, style="detail", title_color="primary_text", fill="grey_l", gap_pt=2):
    """浅灰圆角卡：蓝色加粗标题 + 要点正文。"""
    x, y, w, h = b
    round_card(s, b, fill=fill, radius=10)
    text(s, (x + 10, y + 5, w - 20, 22), f"**{title}**", style="body", color=title_color, check=False)
    text(s, (x + 10, y + 28, w - 20, h - 32), md, style=style, gap_pt=gap_pt)


def table_at(s, x, y, w, cols, rows, ratios, style="detail", pad=(4, 1), align=None, fills=None, hot_col=None):
    th = table_height(w, cols, rows, ratios, style=style, pad=pad)
    table(s, (x, y, w, th), cols, rows, widths=ratios, style=style, pad=pad, align=align, fills=fills,
          hot_col=hot_col, fit=False)
    return th * 1.04


def fit_style(md, w, h, styles=("body", "detail", "caption"), gap_pt=2, head_style=None):
    """返回能放进 (w, h) 的最大字号样式。"""
    for st in styles:
        if measure(md, w, st, gap_pt, head_style=head_style) <= h:
            return st
    return styles[-1]


def auto_table(s, x, y, w, cols, rows, ratios, max_h, align=None, fills=None, stretch=False,
               styles=(("body", (5, 4)), ("body", (5, 2)), ("detail", (5, 4)), ("detail", (4, 2)), ("caption", (3, 2)))):
    """在 max_h 内选最大的字号与内边距画表，返回占用高度。"""
    for st, pad in styles:
        th = table_height(w, cols, rows, ratios, style=st, pad=pad)
        if th * 1.04 <= max_h:
            break
    if stretch:
        table(s, (x, y, w, max_h / 1.04), cols, rows, widths=ratios, style=st, pad=pad, align=align, fills=fills, fit=True)
        return max_h
    table(s, (x, y, w, th), cols, rows, widths=ratios, style=st, pad=pad, align=align, fills=fills, fit=False)
    return th * 1.04


def _tick(v):
    return {1: "1", 10: "10", 100: "100", 1000: "1千", 10 ** 4: "1万", 10 ** 5: "10万", 10 ** 6: "100万"}.get(v, f"{v:,}")


def log_bars(s, x, y, w, items, lo, hi, label_w=170, row_h=34, unit="", ticks=None, value_w=170, tick_fmt=_tick):
    """对数刻度横向条形图：items = [(标签, 数值, 显示文字, 填充色)]；lo/hi 为 10 的幂次。返回结束的 y。"""
    bx = x + label_w
    bw = w - label_w - value_w
    span = hi - lo

    def px(v):
        return bx + bw * (math.log10(v) - lo) / span

    top = y
    for i, (lab, v, disp, fill) in enumerate(items):
        cy = y + i * row_h
        text(s, (x, cy + 2, label_w - 8, row_h - 4), lab, style="detail", align="right", valign="middle",
             check=False)
        rect(s, (bx, cy + 7, max(3, px(v) - bx), row_h - 14), fill)
        text(s, (px(v) + 5, cy + 2, value_w, row_h - 4), disp, style="detail", valign="middle", check=False)
    end = y + len(items) * row_h
    rect(s, (bx, top, 0.75, end - top), "grey_d")
    rect(s, (bx, end, bw, 0.75), "grey_d")
    for t in ticks or range(lo, hi + 1):
        tx = bx + bw * (t - lo) / span
        rect(s, (tx, end, 0.75, 4), "grey_d")
        text(s, (tx - 40, end + 4, 80, 14), tick_fmt(10 ** t) + unit, style="caption", color="grey_d", align="center",
             check=False)
    return end + 18


def legend_row(s, x, y, items, sw=14):
    """横排图例：items = [(fill, 文字)]。"""
    for fill, t in items:
        rect(s, (x, y + 2, sw, 10), fill)
        tw = lib.text_em(t) * 9 * lib.PX_PER_PT + 8
        text(s, (x + sw + 4, y - 1, tw, 16), t, style="caption", check=False)
        x += sw + 4 + tw + 10


def fcard(s, b, title, md, fill="grey_l", line="grey_line", title_color="primary_text", styles=("lead", "body", "detail", "caption"),
          gap_pt=3):
    """自动选字号的圆角卡：标题 + 正文，正文取能放下的最大字号。"""
    x, y, w, h = b
    round_card(s, b, fill=fill, line=line, radius=10)
    text(s, (x + 12, y + 6, w - 24, 22), f"**{title}**", style="body", color=title_color, check=False)
    st = fit_style(md, w - 24, h - 40, styles, gap_pt)
    text(s, (x + 12, y + 32, w - 24, h - 38), md, style=st, gap_pt=gap_pt)


def stack_cards(s, x, y0, w, total_h, items, gap=12, styles=("lead", "body", "detail"), gap_pt=3, fills=None):
    """自上而下排一列卡片，字号统一取能放下的最大值，富余高度平均分给各卡。items = [(标题, md)]。"""
    n = len(items)
    for st in styles:
        needs = [measure(md, w - 24, st, gap_pt) + 40 for _, md in items]
        if sum(needs) + gap * (n - 1) <= total_h:
            break
    extra = max(0.0, total_h - gap * (n - 1) - sum(needs)) / n
    y = y0
    for i, ((t, md), h) in enumerate(zip(items, needs)):
        h += extra
        fill, line = (fills[i] if fills else ("grey_l", "grey_line"))
        round_card(s, (x, y, w, h), fill=fill, line=line, radius=10)
        text(s, (x + 12, y + 6, w - 24, 22), f"**{t}**", style="body", color="accent" if line == "red" else "primary_text",
             check=False)
        text(s, (x + 12, y + 32, w - 24, h - 36), md, style=st, gap_pt=gap_pt)
        y += h + gap


def judge_box(s, b, md):
    """红框判断卡：正文取能放下的最大字号，纵向居中。"""
    x, y, w, h = b
    round_card(s, b, fill="bg", line="red", radius=8)
    st = fit_style(md, w - 24, h - 12, ("lead", "body", "detail", "caption"))
    text(s, (x + 12, y + 6, w - 24, h - 12), md, style=st, valign="middle")


# ---------------------------------------------------------------- 封面与摘要

@page
def cover(prs):
    lib.cover_slide(prs, "安卓 Agent 沙箱洞察",
                    "形态、部署、框架支持、x86 与 ARM、性能诉求、技术挑战与研究进展",
                    "2026 年 11 月　讨论稿")


@page
def summary(prs):
    s = new_slide(prs, "洞察摘要：", "云侧转向容器化安卓与 microVM 快照，手机侧需要系统提供分档的会话沙箱",
                  crumb=CRUMB + " › 摘要")
    rect(s, (32, 88, 1216, 52), "grey_l")
    text(s, (44, 92, 1192, 44),
         "「安卓 Agent 沙箱」有三种用途：云侧执行与云手机、Agentic RL 训练环境、手机本机执行。"
         "@@前两种看密度、重置与吞吐，第三种看隔离强度、单个会话的增量内存与后台存活@@；"
         "云侧方案能迁移到手机的是机制（快照、共享只读层、内存回收），不是产品形态。",
         style="body", valign="middle")
    cols = ["维度", "现状", "关键证据", "判断"]
    rows = [
        ["沙箱形态", "云侧从 Docker 化 AVD 转向 redroid 容器，microVM 包 redroid 正在出现，真机补真实性",
         "MobileRL 每 AVD 超过 !!5 GB!!，稳定 256 路；Qwen-UI-Agent 改建在 redroid 上，超过 !!1 万!!并发环境",
         "规模由容器承担，真实性由真机承担"],
        ["腾讯 Cube", "PR #1879 补齐 arm64 guest 内核的 IPv6 与 PSI；5 个阻塞点合入 2 个",
         "模板约 40 s 就绪，恢复约 !!50 ms!!（贡献者自报，arm64，4 vCPU / 8 GiB）",
         "应表述为「推进中」；阻塞点都源于平台默认承载 Linux 服务"],
        ["字节与归属", "字节的安卓沙箱在火山云手机与 UI-TARS-2 训练平台；豆包手机靠 INJECT_EVENTS 操作真实应用",
         "DSec 属 DeepSeek（arXiv 2609.22978）；AgentENV 属 Kimi 与 kvcache-ai", "AgentEnv、DSec 不是字节的方案"],
        ["框架支持", "veRL、slime、AReaL、ROLL 都不内置安卓；上层项目自行外挂，环境层抽象为服务",
         "MobileRL、Android Coach 基于 verl；MAI-UI 自建环境管理器，最多 512 并发",
         "规模取决于下层实例形态，不取决于 RL 框架"],
        ["x86 与 ARM", "x86 嵌套虚拟化成熟但要翻译 ARM 应用；ARM 原生兼容但 VM 形态要裸金属",
         "Google ARM 翻译「不应用于商业托管」；Graviton 不支持嵌套；redroid 要求 4 KB 页",
         "本质是隔离形态的选型，不是性能的选型"],
        ["手机侧", "第三方只有 PRoot 或 QEMU 用户态（OpenMinis、Napaxi）；pKVM 与后台虚拟屏只在系统手中",
         "Terminal VM 屏幕关闭即被结束；Computer Control 只授予 OEM 预装助手；pVM 跨边界开销 !!2%–14%!!",
         "需要系统提供分档会话沙箱与生命周期管理"],
        ["性能与研究", "云侧数据集中于训练吞吐；安卓快照、重置、单步时延缺数；手机侧几乎空白",
         "模拟器交互耗时是推理的 !!1.7 倍!!；任务时长相差 100 倍，异步后训练效率 3 倍",
         "创新集中在少用环境、让环境便宜"],
    ]
    th = auto_table(s, 32, 150, 1216, cols, rows, [0.62, 2.0, 2.2, 1.35], 430, align=["center", "left", "left", "left"])
    conclusion_band(s, 150 + th + 10, [
        ("云侧", "规模由 redroid 容器承担，真实性由真机承担；microVM 快照与 redroid 结合是下一步"),
        ("手机侧", "由系统提供分档会话沙箱：进程级、按需挂载的用户态工具链、高风险会话走 pVM、GUI 走后台虚拟屏"),
        ("关键技术", "会话生命周期与资源协同：挂起到闪存、按需换入、与 LMKD 协同；先建立真机测量基线"),
    ], label="三个\n判断")
    footnote(s, "来源：安卓Agent沙箱洞察.md 第 0 节；分项笔记 notes/AS1–AS6。自报、二手数字在正文逐条标注口径。", y=694, w=1100)


# ---------------------------------------------------------------- 一、范围、用途与形态

@page
def usages(prs):
    s = new_slide(prs, "安卓 Agent 沙箱的三种用途：", "云侧看密度与重置，手机本机看隔离、增量内存与后台存活",
                  crumb=CRUMB + " › 用途与部署")
    uses = [
        ("云侧执行与云手机", "blue_l",
         "- **运行位置**：云端 x86 或 ARM 服务器\n- **隔离对象**：租户之间、宿主与实例之间\n"
         "- **代表**：火山引擎云手机 + Mobile Use Agent、华为云 CPH、Anbox Cloud、CubeSandbox + redroid\n"
         "- **核心指标**：单机密度、启动与恢复、串流时延、单路成本\n"
         "- **现状**：量产；Anbox Cloud 用 Ampere Altra + 2×T4 跑 !!55!! 个 720p 容器"),
        ("Agentic RL 训练环境", "purple_l",
         "- **运行位置**：云端集群\n- **隔离对象**：训练集群与环境之间、环境之间\n"
         "- **代表**：UI-TARS-2 GUI 沙箱、MobileRL、MAI-UI、Qwen-UI-Agent、DSec\n"
         "- **核心指标**：并发数、重置时间、单步时延、长尾、环境稳定性\n"
         "- **现状**：量产；AVD 路线 256–512 路，redroid 路线超过 !!1 万!!"),
        ("手机本机执行", "green_l",
         "- **运行位置**：用户自己的手机\n- **隔离对象**：用户数据、其他应用与系统\n"
         "- **代表**：OpenMinis、Napaxi、AVF Linux Terminal、Google Computer Control、豆包手机\n"
         "- **核心指标**：隔离强度、单会话增量内存、恢复时延、后台存活、功耗与发热\n"
         "- **现状**：只有开发者向开源项目与系统预览，面向消费者的沙箱能力未量产"),
    ]
    gw, gap, y0, h = 394, 17, 104, 262
    st = "body" if all(fit_style(md, gw - 36, h - 34, ("body", "detail"), 3) == "body" for _, _, md in uses) else "detail"
    for i, (name, fill, md) in enumerate(uses):
        x = 32 + i * (gw + gap)
        ix, iy, iw, ih = panel(s, (x, y0, gw, h), name, title_style="heading")
        rect(s, (ix - 2, iy - 2, iw + 4, ih + 4), fill, kind="rounded", radius=8)
        text(s, (ix + 6, iy + 2, iw - 12, ih - 4), md, style=st, gap_pt=3)
    y = y0 + h + 22
    text(s, (32, y, 1216, 22), "**四种部署方式**", style="body", color="accent", check=False)
    cols = ["部署方式", "推理在哪", "执行在哪", "代表", "状态"]
    rows = [
        ["云端集中式", "云", "云端安卓实例", "火山引擎 Mobile Use Agent；UI-TARS-2、Qwen-UI-Agent 的训练环境", "量产（训练侧、云手机侧）"],
        ["端云协同", "云（多数）或端", "用户手机，以系统级权限操作真实应用",
         "豆包手机（INJECT_EVENTS）；Google Computer Control（后台虚拟屏）；荣耀 YOYO；鸿蒙小艺 GUI 操作",
         "量产或预览；除 Google 外，执行环境的隔离均无官方技术说明"],
        ["端侧本机", "自带模型或端侧模型", "手机上的隔离环境", "OpenMinis（PRoot）；Napaxi（PRoot / QEMU 用户态）；AVF Linux Terminal",
         "开源或预览，均为开发者向"],
        ["云训练、端部署", "端侧小模型", "手机", "ClawGUI（Android、HarmonyOS、iOS）；AutoDroid-V2（端侧解释器执行生成的脚本）", "学术与开源"],
    ]
    th = auto_table(s, 32, y + 24, 1216, cols, rows, [0.8, 0.8, 1.35, 3.0, 1.9], 686 - 60 - (y + 24),
                    align=["center", "center", "left", "left", "left"])
    cy = y + 24 + th + 8
    conclusion_band(s, cy, [("", "@@面向用户的手机 Agent 产品都在真实系统上执行@@；真正把 Agent 放进隔离环境的，只有开发者向开源项目和 "
                                "Google Linux Terminal。手机侧 Agent 沙箱作为消费级系统能力，尚未量产。")], label="判断")


@page
def spectrum(prs):
    s = new_slide(prs, "安卓沙箱的形态谱系：", "隔离强度与快照能力是两条轴，microVM 包容器是目前唯一兼得的路线",
                  crumb=CRUMB + " › 形态谱系")
    X0, X1, Y0, Y1 = 92, 556, 642, 112
    round_card(s, (32, 92, 536, 594), fill="grey_l", radius=10)
    arrow(s, (X0, Y0), (X1, Y0), color="dark", width=1.25)
    arrow(s, (X0, Y0), (X0, Y1), color="dark", width=1.25)
    text(s, (X0, Y0 + 8, X1 - X0, 18), "快照与快速恢复能力：弱 → 强", style="caption", align="center", check=False)
    text(s, (40, Y1 + 4, 46, 18), "强", style="caption", align="center", check=False)
    text(s, (40, 300, 46, 160), "隔\n离\n强\n度", style="caption", align="center", valign="middle", check=False)
    text(s, (40, Y0 - 22, 46, 18), "弱", style="caption", align="center", check=False)
    pts = [
        ("真机农场", "物理隔离；靠重装应用重置", 192, 150, "blue_l", None),
        ("手机 pVM（AVF）", "VM 级隔离；无会话快照", 200, 236, "green_l", None),
        ("全虚拟机", "Cuttlefish、AVD；快照受 GPU 限制", 372, 300, "blue_l", None),
        ("microVM 包 redroid", "Cube；恢复约 50 ms（自报）", 462, 192, "peach_l", "red"),
        ("容器", "redroid；只有文件层复用", 380, 400, "blue_l", None),
        ("进程级", "isolatedProcess、seccomp", 196, 448, "green_l", None),
        ("虚拟屏", "只隔离显示与输入焦点", 196, 540, "green_l", None),
        ("用户态", "PRoot；同 uid、同 SELinux 域", 384, 592, "green_l", None),
    ]
    for name, sub, cx, cy, fill, line in pts:
        w, h = 176, 56
        md = f"**{name}**\n{sub}"
        if line:
            box(s, (cx - w / 2, cy - h / 2, w, h), md, fill=fill, line=line, line_width=1.5, style="caption",
                color="accent", inset=2)
        else:
            box(s, (cx - w / 2, cy - h / 2, w, h), md, fill=fill, line="grey_d", style="caption", inset=2)
    legend_row(s, 250, 100, [("blue_l", "云侧形态"), ("green_l", "手机侧形态"), ("peach_l", "兼得两轴")])

    cols = ["形态", "代表", "隔离边界与关键依赖", "快照", "典型用途"]
    rows = [
        ["容器", "redroid、Anbox 容器", "共享宿主内核；宿主需 binderfs、ashmem / memfd、IPv6、DMA-BUF heap、**4 KB 页**", "弱", "云手机、云游戏、RL（Qwen）"],
        ["全虚拟机", "Cuttlefish、AVD、DSec QEMU", "独立 guest 内核；需 KVM，云上需嵌套或裸金属", "有，受限", "AOSP 测试、训练（AVD）"],
        ["microVM 包容器", "CubeSandbox + redroid", "Cloud Hypervisor 分叉 + KVM；binder 由 guest 内核提供", "强", "可快照复用的 Agent 环境"],
        ["ARM 阵列", "华为云 CPH、火山云手机", "厂商未披露容器还是 VM", "未披露", "面向用户的云手机"],
        ["真机农场", "Xiaomi-GUI-0、BlueLM-GUI", "物理设备；健康调度", "无", "风控、账号态、支付"],
        ["用户态", "OpenMinis、Napaxi", "与宿主应用同 uid、同 SELinux 域；无需特权", "无", "手机上的 Linux 工具链"],
        ["进程级", "isolatedProcess、seccomp", "独立 uid 与 SELinux 域", "无", "受控计算、插件"],
        ["VM 级（手机）", "Microdroid、Linux Terminal", "pKVM；需 IOMMU、pvmfw；芯片需开放对应 VM 类型", "无", "敏感计算、Linux 终端"],
        ["虚拟屏级", "Computer Control、豆包", "特权权限；不隔离数据与权限", "无", "系统助手后台操作应用"],
    ]
    th = auto_table(s, 584, 92, 664, cols, rows, [0.78, 1.15, 2.1, 0.5, 1.15], 480,
                    align=["center", "left", "left", "center", "left"])
    cy = 92 + th + 10
    judge_box(s, (584, cy, 664, 686 - cy),
              "!!判断：!!按隔离强度排序，全 VM ≈ microVM 包容器 > 容器 > 进程级 > 用户态；按快照能力排序几乎相反。"
              "@@只有 microVM 路线同时拿到了隔离与内存快照@@，代价是自己维护面向安卓的 guest 内核。")
    footnote(s, "来源：redroid-doc、Cuttlefish 快照文档、Anbox Cloud 文档、CubeSandbox #1878 系列、OpenMinis 与 Napaxi 源码、AVF 架构文档、"
                "Android Computer Control 文档。示意图位置为定性判断。", y=694, w=1130)


# ---------------------------------------------------------------- 二、方案拆解

@page
def cube(prs):
    s = new_slide(prs, "腾讯 CubeSandbox 的安卓路径：", "PR #1879 补齐 guest 内核，5 个阻塞点已合入 2 个",
                  crumb=CRUMB + " › CubeSandbox")
    L, W = 32, 540
    round_card(s, (L, 92, W, 594), fill="grey_l", radius=10)
    text(s, (L + 12, 98, W - 24, 20), "**redroid 模板在 Cube 中的路径与阻塞点位置**", style="body", color="primary_text",
         check=False)
    box(s, (L + 20, 126, W - 40, 30), "**上层**：Agent 或测试框架，经 adb 连接 :5555", fill="bg", line="grey_d", style="detail")
    arrow(s, (L + W / 2, 157), (L + W / 2, 172), color="dark")
    cw = (W - 40 - 16) / 3
    ctrl = [("CubeMaster", "新增 cgroup_mode 字段"), ("Cubelet", "透传 annotation"), ("CubeShim", "是否注入 cgroup v2")]
    for i, (n, d) in enumerate(ctrl):
        box(s, (L + 20 + i * (cw + 8), 173, cw, 44), f"**{n}**\n{d}", fill="blue_l", line="grey_d", style="caption")
    box(s, (L + 20, 225, W - 40, 30), "**CubeTemplateCenter 镜像导入**：解包镜像层、写入根证书", fill="blue_l", line="grey_d",
        style="detail")
    arrow(s, (L + W / 2, 256), (L + W / 2, 270), color="dark")
    mx, my, mw, mh = L + 20, 271, W - 40, 300
    outline(s, (mx, my, mw, mh), line="red", width=1.5, dash=True)
    text(s, (mx + 8, my + 4, mw - 16, 18), "!!microVM!!（cube-hypervisor；4 vCPU / 8 GiB / 10 GiB 可写层）", style="caption",
         check=False)
    box(s, (mx + 12, my + 26, mw - 24, 32), "**guest 内核**：BINDER_IPC=y；IPv6、PSI 由 #1879 补齐", fill="bg", line="grey_d",
        style="caption")
    box(s, (mx + 12, my + 66, mw - 24, 30), "**guest agent**：exec 容器 init 前关闭继承的 fd（#2031）", fill="bg", line="grey_d",
        style="caption")
    rx, ry, rw, rh = mx + 12, my + 104, mw - 24, 186
    rect(s, (rx, ry, rw, rh), "green_l", kind="rounded", radius=8)
    text(s, (rx + 8, ry + 4, rw - 16, 18), "**redroid 容器（Android 14）**", style="detail", check=False)
    seq = [("init", "挂 cgroup v1\napexd 引导"), ("zygote", "fork\nsystem_server"), ("system_server", "框架服务"),
           ("adbd", ":5555 裸 TCP")]
    sw = (rw - 16 - 3 * 14) / 4
    for i, (n, d) in enumerate(seq):
        bx = rx + 8 + i * (sw + 14)
        box(s, (bx, ry + 30, sw, 58), f"**{n}**\n{d}", fill="bg", line="grey_d", style="caption", inset=2)
        if i < 3:
            arrow(s, (bx + sw + 1, ry + 59), (bx + sw + 13, ry + 59), color="dark")
    adbd_x = rx + 8 + 3 * (sw + 14)
    text(s, (rx + 8, ry + 96, rw - 16, 86),
         "- /etc 是指向 /system/etc 的符号链接；CA 证书要写入 system/etc/security/cacerts\n"
         "- 镜像层带构建主机的 security.selinux xattr\n- lmkd 依赖 PSI；网络依赖 IPv6",
         style="caption", gap_pt=1)
    box(s, (L + 20, 580, W - 40, 26), "宿主：arm64 + KVM（验证均在 arm64；ARM 云上需裸金属）", fill="beige", line="grey_d",
        style="detail")
    for n, cx, cy in [(1, mx + mw - 14, my + 30), (2, L + 20 + 3 * cw + 16 - 6, 177), (3, adbd_x + sw - 4, ry + 34),
                      (4, L + W - 26, 229), (5, mx + mw - 14, my + 70)]:
        badge(s, cx, cy, n, d=20)
    text(s, (L + 12, 614, W - 24, 66),
         "~~编号对应右表的阻塞点。数字均为贡献者 DualPhaseDev 自报：模板约 40 s 进入 READY，从快照恢复约 50 ms，adbd 可连，"
         "getprop 返回 Android 14；硬件未披露，无多实例密度、恢复后内存与截图通道的数据。~~", style="caption")

    R, RW = 588, 660
    cols = ["#", "阻塞点", "修复", "PR 与状态"]
    rows = [
        ["1", "guest 内核 IPV6=m（无模块等于没有）、未开 PSI：端口绑定间歇失败，lmkd 无法工作", "arm64 配置对齐 x86_64，两行改动",
         "**#1879**\n@@已合入@@\n2026-10-08"],
        ["2", "shim 强制注入 cgroup v2，Android init 直接挂 cgroup v1，模板构建陷入 apexd 重启循环",
         "--cgroup-mode legacy：CLI → CubeMaster → annotation → Cubelet → CubeShim", "**#1882**\n@@已合入@@\n2026-11-16（UTC）"],
        ["3", "就绪探针只支持 HTTP，adbd 是裸 TCP", "--probe-type tcp、--probe-timeout、--probe-initial-delay", "**#1880**\n!!开放!!"],
        ["4", "SELinux 主机构建的镜像带 xattr，导入报 EINVAL；/etc 符号链接使 MkdirAll 报 EEXIST",
         "剥离 selinux xattr；按 Android 规则写 CA 证书", "**#1881**\n!!开放!!"],
        ["5", "zygote 遇到继承的 FIFO fd 中止（不在 issue 原列的 4 项内）", "exec 前 close_range(3, ~0U, 0)", "**#2031**\n!!开放!!"],
    ]
    th = auto_table(s, R, 92, RW, cols, rows, [0.2, 2.1, 1.75, 1.15], 330, align=["center", "left", "left", "center"])
    y = 92 + th + 10
    md = ("- 规格：4 vCPU / 8192 MiB / 10 GiB 可写层；探针超时 600 s，因为完整操作系统启动慢\n"
          "- 维护者：「内部也在看安卓沙箱支持」，建议增加 examples/redroid/（截至 2026-11-15 不存在）\n"
          "- #1882 首版只在 CLI 提供，CubeAPI 与 SDK 暴露留作后续")
    ch = measure(md, RW - 24, "body", 3) + 44
    fcard(s, (R, y, RW, ch), "示例模板与维护者态度", md)
    y += ch + 10
    judge_box(s, (R, y, RW, 686 - y),
              "!!判断：!!5 个阻塞点没有一个是安卓特有的难题，@@都源于通用沙箱平台默认承载「Linux 服务」而非「完整操作系统」@@。"
              "50 ms 指恢复到 adbd 可连，不等于界面稳定；Cube 的安卓能力宜表述为「社区贡献者推进中」。"
              "价值在于把 binder、页大小等宿主内核依赖转移到 guest 内核，同时获得 microVM 的隔离与内存快照。")
    footnote(s, "来源：TencentCloud/CubeSandbox issue #1878，PR #1879、#1880、#1881、#1882、#2031（GitHub API，2026-11-15，主线程复核）。", y=694, w=1100)


@page
def bytedance(prs):
    s = new_slide(prs, "字节相关方案与名称核实：", "AgentEnv 属 Kimi、DSec 属 DeepSeek，均非字节方案",
                  crumb=CRUMB + " › 字节与归属")
    L, W = 32, 640
    items = [
        ("豆包手机：端云协同，在真实系统上执行",
         "- 官方回应：依赖系统级权限 **INJECT_EVENTS** 跨应用模拟点击（经 IT之家转述）\n"
         "- 第三方分析称还用 VirtualDisplay；推理位置、截图是否上传均无可靠来源\n"
         "- 一代上市即被微信、淘宝、银行等限制；二代仍有 150 余款应用拒绝 GUI 自动化\n"
         "- !!判断：!!它的「沙箱」是权限边界，不是执行隔离"),
        ("UI-TARS-2 的 all-in-one GUI sandbox：训练平台",
         "- 分布式 VM 平台跑 Windows、Ubuntu、Android，集成 PyAutoGUI 与 ADB\n"
         "- 规模：VM 集群 !!数千实例!!、数千 QPS；租约式回收；异步 rollout\n"
         "- 未披露：安卓实例形态、重置方式、单步时延"),
        ("通用沙箱与 RL 框架：都没有安卓",
         "- AIO Sandbox（v1.11.0）：单容器集成浏览器、终端、VSCode、Jupyter、MCP\n"
         "- SandboxFusion：代码执行与评测；veRL：多轮工具调用、Sandbox Fusion 集成"),
        ("火山引擎云手机 + Mobile Use Agent：商业云服务",
         "- OpenAPI：截图（单张、批量）、录屏、文件推拉、ADB 隧道、实例重置\n"
         "- API 示例中 g2.8c12g 可切 1–6 开（示例值）；容器还是 VM、ARM 还是 x86 待核实"),
    ]
    stack_cards(s, L, 92, W, 594, items, gap=10)

    R, RW = 692, 556
    text(s, (R, 92, RW, 22), "**名称与归属核实**", style="body", color="accent", check=False)
    cols = ["名称", "实际归属", "形态", "安卓"]
    rows = [
        ["DSec", "**DeepSeek**\nDeepSeek Elastic Compute\narXiv 2609.22978", "统一 SDK：FnCall、容器、Firecracker microVM、QEMU 全 VM",
         "有，在 QEMU 全 VM；无安卓数字"],
        ["AgentENV", "**月之暗面 Kimi 与 kvcache-ai**\n2026-07 开源，MIT", "Firecracker microVM，兼容 E2B API", "README 未提"],
        ["LlamaTouch/ AgentEnv", "学术项目\n2024 年后无更新", "AITW 动作到安卓设备的桥接层", "是，但不是沙箱"],
    ]
    th = auto_table(s, R, 116, RW, cols, rows, [0.85, 1.5, 1.6, 1.05], 240, align=["center", "left", "left", "left"])
    y = 116 + th + 10
    md = ("- DSec：单节点最多 !!800!! 个 microVM 或 !!3,200!! 个容器；峰值并发超过 38 万，创建超过 5,000 次每秒\n"
          "- DSec：EROFS 层按需加载快 1.71 倍；DAMON + balloon 降内存 21.2%；沙箱寿命中位数约 16 分钟，P99 超过 3 小时\n"
          "- AgentENV：快照恢复小于 50 ms、暂停小于 100 ms、内存超分 9.6 倍（厂商自报）")
    ch = measure(md, RW - 24, "body", 3) + 44
    fcard(s, (R, y, RW, ch), "DSec 与 AgentENV 的关键数字", md)
    y += ch + 10
    judge_box(s, (R, y, RW, 686 - y),
              "!!判断：!!没有找到字节名为 AgentEnv 或 DSec 的项目。字节的 Agent 沙箱分两条线：代码与浏览器走容器，安卓走云手机产品，"
              "@@中间没有统一的 microVM 层@@；DSec、AgentENV 的快照与超分也尚未与安卓实例结合。")
    footnote(s, "来源：arXiv 2509.02544、2609.22978；agent-infra/sandbox、bytedance/SandboxFusion、volcengine/verl、kvcache-ai/AgentENV；"
                "火山引擎云手机文档；豆包权限说明为媒体转述（二手）。", y=694, w=1130)


@page
def training(prs):
    s = new_slide(prs, "大厂 GUI Agent 训练环境：", "规模由容器化安卓承担、真实性由真机承担，AVD 路线停留在数百路",
                  crumb=CRUMB + " › 训练环境")
    L, W = 32, 560
    round_card(s, (L, 92, W, 400), fill="grey_l", radius=10)
    text(s, (L + 12, 98, W - 24, 20), "**公开的并发规模（对数刻度，单位：实例或环境）**", style="body", color="primary_text",
         check=False)
    items = [
        ("ClawGUI-RL", 64, "64（Docker 模拟器）", "blue_m"),
        ("Qwen-UI-Agent 真机", 100, "100+ 台真机", "green_m"),
        ("MobileRL", 256, "!!256!!（AVD，稳定上限）", "blue_m"),
        ("MAI-UI", 512, "!!512!!（Docker AVD）", "blue_m"),
        ("HyMobileAgent", 2000, "2000+（沙箱与真机）", "purple_m"),
        ("Qwen-UI-Agent", 10000, "!!1 万+!!（redroid 等）", "peach_m"),
        ("DSec 峰值（参照）", 380000, "38 万（非安卓为主）", "grey_m"),
    ]
    end = log_bars(s, L + 8, 128, W - 16, items, 1, 6, label_w=146, row_h=42, value_w=168)
    legend_row(s, L + 30, end + 4, [("blue_m", "AVD 模拟器"), ("peach_m", "redroid 容器"), ("green_m", "真机"),
                                    ("purple_m", "混合"), ("grey_m", "非安卓参照")])
    y = 504
    text(s, (L, y, W, 20), "**安卓环境的演进**", style="body", color="accent", check=False)
    stages = [("Docker 化 AVD", "单实例 5–16 GB 内存、30 GB 存储；需 KVM"),
              ("redroid 容器", "无需 QEMU 与嵌套 KVM；可在普通容器主机复制"),
              ("microVM + redroid", "内存快照恢复约 50 ms（Cube，自报）")]
    sw = (W - 2 * 22) / 3
    for i, (n, d) in enumerate(stages):
        x = L + i * (sw + 22)
        box(s, (x, y + 26, sw, 76), f"**{n}**\n{d}", fill="peach_l" if i == 2 else "blue_l",
            line="red" if i == 2 else "grey_d", style="detail", color="accent" if i == 2 else None)
        if i < 2:
            lib.block_arrow(s, (x + sw + 3, y + 54, 16, 20), fill="grey_m")
    box(s, (L, y + 112, W, 46), "**真机并行补充**：反模拟器检测、账号态、权限弹窗、支付认证与风控只能在真机复现（小米、vivo、阿里）",
        fill="green_l", line="grey_d", style="detail")
    text(s, (L, y + 162, W, 20), "~~2026 年阶段为本文判断；microVM + redroid 尚无训练侧公开用例。~~", style="caption")

    R, RW = 612, 636
    cols = ["厂商与项目", "安卓环境形态", "规模", "重置与容错"]
    rows = [
        ["阿里 Qwen-UI-Agent\n2026-07", "为解决 KVM 模拟器的扩展瓶颈，**改建在 redroid 上**；另有 100 多台真机，用虚拟屏让一台手机并行多个 App",
         "超过 1 万个并发环境", "统一接口 acquire / reset / step / evaluate / release；健康调度、设备黑名单"],
        ["阿里通义 MAI-UI\n2025-12", "Docker 化 root AVD + 自托管后端", "10 台 ECS，最多 512；并行 32→512，成功率 65.5%→70.7%",
         "AVD snapshot；容器复用；备用池"],
        ["智谱 MobileRL\n2025-09", "Docker 化 AVD，基于 verl", "稳定 256（4 台 1 TB 机器）", "每步超过 10 分钟，100 步超过 25 小时"],
        ["阿里 GUI-Owl\n2025-08", "阿里云云手机 + 云电脑", "未披露", "rollout 与更新解耦"],
        ["小米 Xiaomi-GUI-0\n2026-06", "真机为主、沙箱为辅", "未披露", "动因：反模拟器检测、风控"],
        ["vivo BlueLM-GUI\n2026-09", "数百台真机上的 agentic RL", "数百台", "强调沙箱与生产环境分布不一致"],
        ["腾讯混元 HyMobileAgent\n2026-07", "沙箱与真机，34 个 mock 应用", "2000 多个实例", "自动失败归因"],
    ]
    th = auto_table(s, R, 92, RW, cols, rows, [1.05, 2.0, 1.25, 1.45], 500, align=["left", "left", "left", "left"])
    y = 92 + th + 8
    judge_box(s, (R, y, RW, 686 - y),
              "!!判断：!!@@规模由容器化安卓承担，真实性由真机承担，模拟器只用于中小规模研究@@。"
              "训练侧从 AVD 转向 redroid，是为了绕开模拟器的内存与 KVM 限制；所有论文都没给出以秒计的重置时间与单步时延分解。")
    footnote(s, "来源：arXiv 2607.28227（主线程核对 redroid 原文）、2512.22047、2509.18119、2508.15144、2606.31410、2609.12394（摘要）、"
                "2607.14548（摘要）、2604.11784、2609.22978。", y=694, w=1130)


@page
def frameworks(prs):
    s = new_slide(prs, "Agentic RL 框架的安卓支持：", "框架都不内置安卓，环境层已抽象为服务，规模取决于下层实例形态",
                  crumb=CRUMB + " › 框架支持")
    cols = ["框架", "机构", "内置安卓", "异步 rollout", "与环境的对接", "基于它的安卓项目"]
    rows = [
        ["veRL", "字节（火山引擎）", "!!否!!", "有（AgentLoop）", "客户端对接；Sandbox Fusion 集成示例", "MobileRL、Android Coach"],
        ["verl-agent", "社区（基于 veRL）", "!!否!!", "列为可贡献想法", "并行 Gym 式环境（ALFWorld、WebShop、AppWorld）", "UI-S1（README 列出）"],
        ["slime", "智谱 THUDM", "!!否!!", "有（fully_async）", "自定义 generate 封装沙箱", "—"],
        ["AReaL", "蚂蚁与清华", "!!否!!", "有，全异步（2.0 微服务）", "agent service", "—"],
        ["ROLL", "阿里", "!!否!!", "有，环境级异步", "对齐 GEM 环境定义", "—"],
        ["AgentRL", "智谱 THUDM", "引用 AndroidLab", "有，协程式", "函数调用式 API；每任务一个容器；集中控制器", "AutoGLM"],
        ["DSec", "DeepSeek", "@@有@@（QEMU 全 VM）", "支持，可抢占恢复", "统一 SDK，四类后端", "—"],
        ["AgentENV", "Kimi 与 kvcache-ai", "未提", "—", "兼容 E2B API", "—"],
    ]
    W = 720
    th = auto_table(s, 32, 92, W, cols, rows, [0.8, 0.95, 0.8, 1.0, 1.7, 0.95], 470,
                    align=["center", "left", "center", "left", "left", "left"])
    text(s, (32, 92 + th + 2, W, 16), "~~「否」依据各仓库 README 首页，未逐一翻查示例目录；OpenRLHF 本轮未覆盖。~~", style="caption",
         check=False)
    bottom = 92 + th + 22
    R, RW = 772, 476
    round_card(s, (R, 92, RW, bottom - 92), fill="grey_l", radius=10)
    text(s, (R + 12, 98, RW - 24, 20), "**训练侧的分层：框架只到接口这一层**", style="body", color="primary_text", check=False)
    layers = [
        ("RL 框架", "veRL、slime、AReaL、ROLL", "bg", "grey_d"),
        ("环境服务接口", "acquire / reset / step / evaluate / release；HTTP 解耦", "blue_l", "grey_d"),
        ("环境管理器", "MAI-UI Environment Manager、Qwen 统一接口、DSec、AgentENV", "blue_l", "grey_d"),
        ("实例形态", "Docker AVD｜redroid 容器｜microVM + redroid｜QEMU 全 VM｜真机", "peach_l", "red"),
    ]
    top, foot = 128, 30
    gap = 18
    lh = (bottom - top - foot - 8 - gap * 3) / 4
    y = top
    for i, (n, d, fill, line) in enumerate(layers):
        box(s, (R + 20, y, RW - 40, lh), f"**{n}**\n{d}", fill=fill, line=line, style="detail",
            color="accent" if line == "red" else None, line_width=1.25 if line == "red" else 0.75)
        if i < 3:
            arrow(s, (R + RW / 2, y + lh + 1), (R + RW / 2, y + lh + gap - 1), color="dark", width=1.25)
        y += lh + gap
    text(s, (R + 20, bottom - foot - 4, RW - 40, foot), "!!决定规模、重置速度与真实性的是最下面一层!!", style="detail",
         align="center", valign="middle", check=False)
    conclusion_band(s, bottom + 10, [
        ("框架不管安卓", "通用 RL 框架把环境抽象为 HTTP 服务，安卓只是其中一种后端；安卓环境由 MobileRL、MAI-UI、ClawGUI 等上层项目外挂"),
        ("接口已收敛", "各家都提供 reset、step、evaluate 与租约式会话；差别在实例形态与重置机制"),
        ("下一步", "microVM 内存快照（Cube 约 50 ms、AgentENV 小于 50 ms，均自报）与安卓实例结合，是训练侧最可能出现的优化"),
    ])
    footnote(s, "来源：各框架 GitHub README（2026-11-15 抓取）；arXiv 2510.04206、2609.22978、2512.22047、2607.28227。", y=694, w=1100)


@page
def phone_third_party(prs):
    s = new_slide(prs, "手机侧第三方沙箱：", "OpenMinis 与 Napaxi 都是 PRoot 用户态，隔离强度等同应用沙箱",
                  crumb=CRUMB + " › 手机侧第三方")
    W, gap = 600, 16
    L = 32
    ix, iy, iw, ih = panel(s, (L, 104, W, 470), "OpenMinis（开源端侧 Agent 应用）", title_style="heading")
    dy = iy + 4
    outline(s, (ix, dy, iw, 200), line="grey_d", width=1.0)
    text(s, (ix + 8, dy + 4, iw - 16, 18), "**OpenMinis App 进程**（untrusted_app；Manifest 申请 29 项权限 + 无障碍服务）",
         style="caption", check=False)
    box(s, (ix + 12, dy + 28, 300, 46), "**PRoot**（自有分叉）：ptrace 拦截系统调用、改写路径；每条命令一个进程",
        fill="peach_l", line="red", style="caption", color="accent", inset=3)
    box(s, (ix + 12, dy + 84, 300, 56), "**Alpine 3.21.3 aarch64 rootfs**\napk、Python、Node、git；/dev /proc /sys 直接绑定宿主",
        fill="bg", line="grey_d", style="caption", inset=3)
    arrow(s, (ix + 162, dy + 75), (ix + 162, dy + 83), color="dark")
    box(s, (ix + 362, dy + 28, iw - 374, 112), "**宿主侧能力**\n无障碍、Shizuku、日历、联系人、相册、通知、浏览器",
        fill="blue_l", line="grey_d", style="caption", inset=3)
    arrow(s, (ix + 313, dy + 52), (ix + 361, dy + 52), color="dark", width=1.25)
    text(s, (ix + 312, dy + 56, 50, 30), "native\noffload", style="caption", align="center", check=False)
    text(s, (ix + 12, dy + 146, iw - 24, 52),
         "~~与宿主同 uid、同 SELinux 域；没有 namespace、cgroup，也没有独立 SELinux 域。rootfs 打进 APK（arm64 APK 47.58 MB），"
         "构建脚本只用 curl 下载，无校验和。~~", style="caption")
    md1 = ("- **兼容补丁多于隔离设计**：--link2symlink 应对 /data 拒绝跨目录硬链接；--fake-netlink 应对 untrusted_app 不能建 NETLINK_ROUTE；"
           "部分 ARM64 机型 ptrace + seccomp 下 apk 崩溃（GH#186），改用 PROOT_NO_SECCOMP=1 重试\n"
           "- **安全重试**：致命信号、1.5 s 内退出、无输出、未重试过四条同时满足才重试一次；SIGKILL 可能来自 LMK，不重试\n"
           "- **性能**：PRoot 的系统调用开销没有公开测量；Google 在 LPC 2025 上定性为「显著」")
    bh = ih - 212
    text(s, (ix, dy + 210, iw, bh), md1, style=fit_style(md1, iw, bh, ("body", "detail"), 7), gap_pt=7)

    L2 = L + W + gap
    ix, iy, iw, ih = panel(s, (L2, 104, W, 470), "Napaxi（蚂蚁开源端侧 Agent SDK）", title_style="heading")
    dy = iy + 4
    chain = [("宿主 App", "保有 UI、账号、模型配置、权限与产品策略", "bg", "grey_d"),
             ("SDK 适配层", "Flutter、Android Kotlin、iOS Swift Package", "bg", "grey_d"),
             ("napaxi_core（Rust）+ 准入闸门", "工具描述符、工具调用、provider 准入与模型切换", "blue_l", "grey_d")]
    y = dy
    for n, d, f, ln in chain:
        box(s, (ix + 12, y, iw - 24, 34), f"**{n}**：{d}", fill=f, line=ln, style="caption", inset=3)
        arrow(s, (ix + iw / 2, y + 35), (ix + iw / 2, y + 43), color="dark")
        y += 44
    hw = (iw - 24 - 12) / 2
    box(s, (ix + 12, y, hw, 48), "**Android：PRoot + Alpine**\nenv_clear()；只绑 /workspace、/skills", fill="peach_l", line="red",
        style="caption", color="accent", inset=3)
    box(s, (ix + 24 + hw, y, hw, 48), "**iOS：QEMU aarch64-linux-user**\n用户态模拟（静态库 41.8 MB）", fill="peach_l", line="red",
        style="caption", color="accent", inset=3)
    text(s, (ix + 12, y + 54, iw - 24, 18), "~~典型负载：PTY 中运行 codex app-server，在手机上生成、构建、安装 APK~~", style="caption",
         check=False)
    md2 = ("- **「Trusted sandbox」的实际构成**：移动沙箱 + 策略闸门 + 宿主授权，起约束作用的主要是后两者；"
           "没有 WASM、QuickJS、seccomp 或 isolatedProcess\n"
           "- **资源控制**：超时钳位 1–600 s，先 SIGTERM，宽限 2 s 后 SIGKILL；rootfs 版本不符即重新解压\n"
           "- **已承认的缺口**：路线图写明当前没有出口凭证代理（secret egress proxy）；无启动、内存与体积的公开数据")
    text(s, (ix, dy + 210, iw, bh), md2, style=fit_style(md2, iw, bh, ("body", "detail"), 7), gap_pt=7)
    conclusion_band(s, 588, [("", "@@在无特权的第三方应用里，「给 Agent 一台 Linux」目前只有 PRoot 或 QEMU 用户态这一条路径，隔离强度等同应用沙箱@@。"
                                  "OpenMinis 的价值是说明手机上的 Agent 能做到什么；Napaxi 多做的一步是把权限交给宿主决定，并在 SDK 内设闸。")],
                    label="判断")
    footnote(s, "来源：OpenMinis 仓库（PRootKernel.kt、SeccompFallbackPolicy.kt、AndroidManifest.xml，build 44）；antgroup/napaxi（docs/architecture.md、"
                "android_linux_env.rs，主线程复核）；LPC 2025 Google 幻灯片。", y=694, w=1130)


@page
def phone_native(prs):
    s = new_slide(prs, "手机侧系统原生方案：", "VM 级隔离与后台 GUI 执行都已存在，但只对系统与 OEM 开放",
                  crumb=CRUMB + " › 手机侧系统方案")
    W = 640
    ix, iy, iw, ih = panel(s, (32, 104, W, 470), "AVF Linux Terminal（Google LPC 2025）", title_style="heading")
    dy = iy + 2
    box(s, (ix, dy, 150, 126), "**Terminal App**\nWebView：xterm.js\nSurfaceView：显示\n\n输入事件转换\n（触控、键盘、鼠标）",
        fill="blue_l", line="grey_d", style="caption", inset=3)
    vx, vw = ix + 170, iw - 170
    outline(s, (vx, dy, vw, 126), line="red", width=1.5, dash=True)
    text(s, (vx + 6, dy + 2, vw - 12, 16), "!!非保护 VM!!（crosvm + pKVM）：Debian", style="caption", check=False)
    box(s, (vx + 8, dy + 22, 120, 40), "**ttyd + shell**\n双向 TLS 认证", fill="bg", line="grey_d", style="caption", inset=2)
    box(s, (vx + 136, dy + 22, vw - 144, 40), "**guest agent**：内存与磁盘气球；eBPF 监测 bind() 建 vsock 转发",
        fill="peach_l", line="red", style="caption", color="accent", inset=2)
    devs = ["blk", "input", "gpu", "net", "fs"]
    dw = (vw - 16 - 4 * 4) / 5
    for i, d in enumerate(devs):
        box(s, (vx + 8 + i * (dw + 4), dy + 70, dw, 22), f"virtio-{d}", fill="bg", line="grey_d", style="caption", inset=0)
    box(s, (vx + 8, dy + 98, vw - 16, 22), "gfxstream（AHB 宿主后端，零拷贝）｜/sdcard 经 virtio-fs", fill="beige",
        line="grey_d", style="caption", inset=1)
    arrow(s, (ix + 151, dy + 63), (vx - 1, dy + 63), color="dark", both=True)
    md1 = ("- **为什么不用用户态**：Bionic 不能直接运行 glibc 程序；PRoot 的 ptrace 开销显著；共享内核受限（官方幻灯片原文）\n"
           "- **生命周期**：@@内存气球与应用生命周期联动@@，宿主应用退到后台时主动回收 guest 内存，避免被 LMK 结束\n"
           "- **图形**：从 lavapipe 软渲染（CPU 高、帧率低）改为 gfxstream；修复 ARM 宿主与 guest 缓存一致性导致的画面损坏\n"
           "- **限制**：需非保护 VM，Snapdragon 8 Elite 只支持保护 VM（二手）；Android 17 默认 1024 MiB；!!屏幕关闭时 VM 被结束!!（个人实测）；"
           "第三方能否持有 MANAGE_VIRTUAL_MACHINE，官方文档未写\n"
           "- **AnBridge（DSN'26）**：Pixel 7 Pro 上 pVM 分配 250 MB，原生代码跨 pVM 调用宿主 Java 开销 !!2%–14%!!")
    bh = ih - 140
    text(s, (ix, dy + 136, iw, bh), md1, style=fit_style(md1, iw, bh, ("body", "detail"), 6), gap_pt=6)

    R, RW = 32 + W + 16, 1248 - 32 - W - 16
    ix, iy, iw, ih = panel(s, (R, 104, RW, 470), "后台虚拟屏与系统级 GUI 执行", title_style="heading")
    dy = iy + 2
    box(s, (ix, dy, iw, 40), "**OEM 预装助手**：持特权权限 ACCESS_COMPUTER_CONTROL；截屏、模拟点击、滑动、输入文本",
        fill="blue_l", line="grey_d", style="caption", inset=3)
    hw = (iw - 12) / 2
    box(s, (ix, dy + 48, hw, 66), "**主屏**\n用户前台应用\n不受打扰", fill="bg", line="grey_d", style="caption")
    box(s, (ix + hw + 12, dy + 48, hw, 66), "**安全的后台虚拟屏**\n目标应用（每会话最多 6 个）\n同一时间 1 个会话", fill="peach_l",
        line="red", style="caption", color="accent")
    box(s, (ix, dy + 122, iw, 30), "首次操作某应用：系统授权弹窗｜交易确认等步骤：控制权交还用户", fill="beige", line="grey_d",
        style="caption", inset=3)
    md2 = ("- **隔离的是什么**：显示与输入焦点；@@不隔离数据与权限@@，目标应用仍以用户身份在用户数据上运行\n"
           "- **防护来自三件事**：特权权限只给预装助手、逐应用授权、敏感步骤交还用户\n"
           "- **豆包手机**：官方只确认 INJECT_EVENTS；VirtualDisplay 为第三方推测\n"
           "- **荣耀 YOYO、鸿蒙小艺**：只有功能描述，没有隔离机制的官方说明\n"
           "- **代价**：虚拟屏上的应用要在后台再运行一份；内存、GPU 与前台干扰没有公开测量（讨论稿估算每个 0.2–0.5 GB）")
    bh2 = ih - 164
    text(s, (ix, dy + 160, iw, bh2), md2, style=fit_style(md2, iw, bh2, ("body", "detail"), 8), gap_pt=8)
    conclusion_band(s, 588, [("", "@@VM 级隔离与后台 GUI 执行的部件都已存在，但只对系统与 OEM 开放@@，这正是手机厂商的位置。"
                                  "Google 已证明 VM 内存可以随应用生命周期回收；尚未有人做到「挂起到闪存、恢复时按需换入」的会话快照。")],
                    label="判断")
    footnote(s, "来源：LPC 2025「A Linux VM on Android via AVF」（主线程读原文）；AnBridge DSN'26（主线程读原文）；AOSP AVF 架构文档；"
                "Android Computer Control 文档；Android Authority 与个人实测指南（二手）。", y=694, w=1130)


@page
def phone_forms(prs):
    s = new_slide(prs, "手机侧五类沙箱形态对比：", "无特权方案隔离不足，强隔离只在系统手中，性能数据普遍缺失",
                  crumb=CRUMB + " › 手机侧形态对比")
    cols = ["形态", "代表", "隔离强度", "常驻内存", "启动与恢复", "能力范围", "可用性"]
    rows = [
        ["用户态\n（路径虚拟化）", "OpenMinis、Napaxi（Android PRoot）、Termux proot-distro", "!!弱!!：同 uid、同 SELinux 域，只改路径视图",
         "proot 进程 + guest 进程 RSS；~~无公开测量~~", "~~无公开测量~~；冷启动 apk 小于 1 s（代码注释）",
         "最宽：完整 Alpine 用户态、包管理、Python、git", "任何机型、无需特权；受 phantom process killer 与 ptrace 兼容性影响"],
        ["用户态\n（指令集模拟）", "Napaxi（iOS QEMU user）、OpenMinis（iOS iSH）", "弱到中", "~~无公开测量~~；QEMU 静态库 41.8 MB",
         "~~无公开测量~~", "宽，但慢于原生", "iOS 上唯一选择"],
        ["进程级", "isolatedProcess、seccomp、独立 SELinux 域", "中：独立 uid 与 SELinux 域", "近零额外开销（机制推断）", "毫秒级（机制推断）",
         "窄：无 Linux 用户态；适合解析、脚本引擎、插件", "所有机型；两个 PRoot 项目都没有采用"],
        ["VM 级", "Microdroid、Linux Terminal（pKVM / AVF）", "@@强@@：保护 VM 内存对宿主不可见；非保护 VM 为 KVM 级",
         "pVM 250 MB（AnBridge）；Terminal 默认 1024 MiB；Microdroid 量级 32–42（疑为 MB）", "~~无公开测量~~",
         "完整 Linux 内核与用户态；跨边界开销 2%–14%", "!!窄!!：芯片决定 VM 类型；第三方权限未明；屏幕关闭被结束"],
        ["虚拟屏级", "Google Computer Control、豆包手机", "只隔离显示与输入焦点", "目标应用进程 + 虚拟屏缓冲；~~无公开测量~~",
         "应用冷启动", "只能操作 GUI；每步依赖截屏与推理（每步 7–15 s，含云端推理）", "OEM 预装助手专用；特权权限"],
    ]
    th = auto_table(s, 32, 92, 1216, cols, rows, [0.75, 1.35, 1.35, 1.45, 1.05, 1.45, 1.5], 480,
                    align=["center", "left", "left", "left", "left", "left", "left"])
    cy = 92 + th + 10
    conclusion_band(s, cy, [
        ("矛盾", "无特权的第三方方案（PRoot）能力宽但隔离弱；强隔离（pKVM、虚拟屏授权）只由系统提供，且不对第三方开放"),
        ("空白", "PRoot 开销、Terminal 启动时间、虚拟屏内存、手机沙箱功耗都没有公开测量；手机侧性能口径尚未建立"),
        ("可行组合", "系统提供会话级进程沙箱（独立 uid + seccomp + 出口代理），需要工具链时挂载用户态环境，高风险会话走 pVM，GUI 走后台虚拟屏"),
    ])
    footnote(s, "来源：OpenMinis、Napaxi 源码；AnBridge DSN'26；LPC 2025；本库 C2 §3 Q6–Q7；AndroidDaily（arXiv 2605.27761）；"
                "Android Computer Control 文档。灰字为口径说明。", y=694, w=1130)


# ---------------------------------------------------------------- 三、虚拟化、x86 与 ARM

@page
def virtualization(prs):
    s = new_slide(prs, "虚拟化支持与手机支持：", "云侧的问题是能否部署，手机侧的问题是谁能使用",
                  crumb=CRUMB + " › 虚拟化支持")
    cols = ["能力", "x86 云", "ARM 云", "手机（pKVM / AVF）"]
    rows = [
        ["KVM", "成熟", "成熟", "pKVM 是手机上唯一量产的 VM 级隔离，限 ARM64；需 IOMMU、pvmfw、DICE"],
        ["嵌套虚拟化", "AWS 自 2026-02 起提供，限 Intel 实例（C8i、M8i、R8i 等）；敏感负载建议裸金属",
         "Graviton 不支持（二手）；KVM arm64 的 FEAT_NV2 自 Linux 6.11 合入；Arm 官方路径要求 6.13 以上、裸金属", "不适用"],
        ["容器形态（redroid）", "普通云 VM 即可", "Graviton4 c8g.large 普通 VM 即可；宿主须为 4 KB 页", "不适用"],
        ["全 VM / microVM", "普通云 VM 上可起（有嵌套时）", "!!基本要裸金属!!", "非保护 VM 依赖芯片支持：Snapdragon 8 Elite 只支持保护 VM（二手）"],
        ["GPU 与快照", "Cuttlefish 快照只在 x86_64 + SwiftShader 下支持", "多数 ARM 服务器无 GPU；Anbox VM 实例不支持 GPU",
         "gfxstream + AHB 零拷贝（Google 官方）；稳定版是否落地待核实"],
        ["第三方可用性", "公有云按实例开放", "公有云按实例开放", "!!MANAGE_VIRTUAL_MACHINE 的持有规则官方未写!!；Computer Control 只授予 OEM 预装助手"],
        ["生命周期", "云端常驻；按需暂停计费", "同左", "Terminal 屏幕关闭即被结束；内存气球随应用前后台回收；无会话快照"],
        ["跨边界开销", "—", "—", "AnBridge：pVM 调用宿主 Java 开销 2%–14%；Binder 单次约 40 KB，超出走 vsock"],
    ]
    th = auto_table(s, 32, 92, 1216, cols, rows, [0.8, 1.7, 1.9, 2.4], 490, align=["center", "left", "left", "left"])
    cy = 92 + th + 10
    conclusion_band(s, cy, [
        ("云侧", "x86 上各种形态都能部署；ARM 上容器没问题，VM 形态要裸金属，扩缩容以整机为单位"),
        ("手机侧", "VM 能力已存在，但只对系统和 OEM 开放，且受芯片支持的 VM 类型限制"),
        ("生命周期冲突", "Agent 的价值在用户不看屏幕时继续执行，而 VM 在屏幕关闭时被结束；应当缩小与挂起，而不是被结束"),
    ])
    footnote(s, "来源：AWS EC2 嵌套虚拟化文档、InfoQ（二手）、KernelNewbies 6.11、Arm Learning Path、AOSP AVF 架构文档、Cuttlefish 文档、"
                "Anbox Cloud 文档、LPC 2025、AnBridge DSN'26。", y=694, w=1130)


@page
def x86_arm(prs):
    s = new_slide(prs, "x86 与 ARM 部署差异：", "本质是隔离形态的选型，而不是性能的选型",
                  crumb=CRUMB + " › x86 与 ARM")
    cols = ["维度", "x86 宿主", "ARM 宿主"]
    rows = [
        ["ARM 应用", "依赖 libndk_translation 或 Houdini（redroid 镜像已内置前者）；Google 的 ARM 翻译「!!不应用于商业托管服务!!」", "原生运行"],
        ["翻译损失", "官方无基准；华为称 x86 模拟器方案至少 50% 性能损失（厂商自报）", "—"],
        ["虚拟化", "KVM 与嵌套成熟，普通云 VM 上可起 microVM", "容器可在普通 VM 上运行；VM 形态基本要裸金属"],
        ["页大小", "4 KB 为主", "服务器发行版可能默认 64 KB（待核实）；redroid 要求 4 KB"],
        ["GPU", "NVIDIA、AMD、Intel，文档覆盖完整", "多数无 GPU，只能软渲染；G5g（Graviton2 + T4G）称每路游戏流成本最多低 30%（自报）"],
        ["应用完整性", "Play Integrity 依据硬件证明，与架构无关", "同左：ARM 服务器不因是 ARM 就能通过"],
        ["成本与密度", "无同口径公开对比", "Anbox：Ampere Altra + 2×T4 跑 55 个 720p 容器；无 GPU 的 m6g.2xlarge 只能 3 个"],
    ]
    W = 700
    th = auto_table(s, 32, 92, W, cols, rows, [0.62, 1.9, 1.7], 480, align=["center", "left", "left"])
    text(s, (32, 92 + th + 2, W, 16), "~~注：AOSP Berberis 做的是 riscv64→x86_64 翻译，不做 ARM 翻译。~~", style="caption", check=False)
    jy = 92 + th + 24
    if 686 - jy >= 60:
        judge_box(s, (32, jy, W, 686 - jy),
                  "!!判断：!!x86 路线受翻译授权与覆盖率约束，ARM 路线受「VM 形态要裸金属」与页大小约束。"
                  "@@在手机本机上两类约束都不存在@@：手机天然是 ARM，问题变成 pKVM 是否开放、VM 能否在后台存活。")

    R, RW = 752, 496
    text(s, (R, 92, RW, 22), "**选型判断**", style="body", color="accent", check=False)
    cols2 = ["负载", "倾向", "理由"]
    rows2 = [
        ["RL rollout", "x86 上的容器或 microVM；要 ARM 原生时用 ARM 裸金属", "KVM 与嵌套成熟；训练自用不涉及商业托管"],
        ["面向用户的云手机", "ARM 容器或板卡", "原生兼容；避开翻译层授权限制"],
        ["兼容性测试", "ARM 原生为主，x86 翻译为辅", "Google 也不建议用翻译替代真机"],
        ["手机本机", "天然 ARM；虚拟化入口只有 pKVM / AVF", "无翻译问题，问题在开放与生命周期"],
    ]
    th2 = auto_table(s, R, 116, RW, cols2, rows2, [0.8, 1.35, 1.35], 260, align=["center", "left", "left"])
    y = 116 + th2 + 10
    fcard(s, (R, y, RW, 686 - y), "技术挑战",
          "- **翻译层**：授权与覆盖率双重约束，覆盖率与性能损失无公开数据\n"
          "- **ARM 上 VM 的部署弹性**：没有嵌套虚拟化，microVM 只能跑在裸金属；Cube 安卓验证全在 arm64\n"
          "- **页大小冲突**：Play 要求目标 API 35 以上的应用自 !!2027-02-01!! 起支持 16 KB 页；容器形态的 redroid 被固定在 4 KB，"
          "16 KB 测试要靠 guest 自带内核的 microVM 或全 VM\n"
          "- **GPU 与快照不能兼得**：目前没有同时提供 VM 级隔离、GPU 与快照的官方路线\n"
          "- **强风控应用**：两种架构都可能无法通过，只能交给真机")
    footnote(s, "来源：Android Developers Blog（2020-03）、Berberis README、redroid-doc、Android 16 KB 页文档、Play Integrity 文档、AWS 博客、"
                "Anbox Cloud 基准、华为云 CPH 文档。", y=694, w=1130)


# ---------------------------------------------------------------- 四、性能诉求

@page
def perf_known(prs):
    s = new_slide(prs, "性能诉求与已知量级：", "云侧数据集中于训练吞吐，安卓快照、重置与单步时延普遍缺数",
                  crumb=CRUMB + " › 性能（已知量级）")
    L, W = 32, 560
    round_card(s, (L, 92, W, 594), fill="grey_l", radius=10)
    text(s, (L + 12, 98, W - 24, 20), "**单实例内存的量级（对数刻度，MiB）**", style="body", color="primary_text", check=False)
    items = [
        ("Cube 每多一台净增", 22, "19–25（Linux guest，实测）", "blue_m"),
        ("Cube 纯净 Linux guest", 175, "156–193（实测）", "blue_m"),
        ("手机 pVM（AnBridge）", 250, "250（配置）", "green_l"),
        ("手机 Terminal VM", 1024, "1024（默认配置）", "green_l"),
        ("AndroidWorld AVD", 2048, "2 GB（官方标称）", "peach_l"),
        ("MobileRL AVD", 5120, "!!超过 5 GB!!（论文自述）", "peach_m"),
        ("Cube redroid 模板", 8192, "8 GiB（配置）", "peach_l"),
        ("2603.07432 AVD", 16384, "16 GB（配置）", "peach_l"),
    ]
    end = log_bars(s, L + 8, 132, W - 16, items, 1, 5, label_w=150, row_h=54, value_w=176,
                   tick_fmt=lambda v: f"{v:,}")
    legend_row(s, L + 24, end + 6, [("blue_m", "Linux microVM"), ("green_l", "手机 VM"), ("peach_m", "安卓实测"),
                                    ("peach_l", "安卓配置或标称")])
    text(s, (L + 14, end + 30, W - 28, 686 - end - 36),
         "~~配置值是分配上限，不等于实际占用；只有 MobileRL 的「超过 5 GB」与 Cube 的 Linux guest 是实测口径。"
         "安卓实例恢复后的实际工作集尚无公开数据。~~", style="detail", valign="middle")

    R, RW = 612, 636
    cols = ["指标", "数值", "条件", "口径"]
    rows = [
        ["redroid 快照恢复", "约 !!50 ms!!", "Cube，恢复到 adbd 可连", "贡献者自报"],
        ["redroid 模板就绪", "约 40 s", "Cube，arm64，4 vCPU / 8 GiB", "贡献者自报"],
        ["Linux microVM 恢复", "50–65 ms；暂停加恢复约 220 ms", "Cube v0.7.3，NVMe、热页缓存", "官方基准"],
        ["模拟器 Quick Boot", "比冷启动最多快 10 倍", "无绝对值", "官方文档"],
        ["训练并发", "256、512、超过 1 万", "MobileRL、MAI-UI、Qwen-UI-Agent", "论文"],
        ["云侧沙箱密度", "单节点 800 microVM / 3,200 容器", "DSec，非安卓", "论文"],
        ["云手机密度", "55 个 720p 容器（29 FPS）；无 GPU 时 3 个", "Anbox Cloud", "官方基准"],
        ["环境交互占比", "模拟器交互是推理的 !!1.7 倍!!（约 63%）", "Android Coach，8 并行", "论文（占比为折算）"],
        ["训练步耗时", "每步超过 10 分钟", "MobileRL，256 并行", "论文"],
        ["长尾", "任务时长相差 100 倍；异步后效率 3 倍", "DistRL", "论文"],
        ["沙箱寿命", "中位数约 16 分钟，P99 超过 3 小时", "DSec", "论文"],
        ["GUI 单步时延", "7.0–14.7 s（含云端推理）", "AndroidDaily，真机 350 个任务", "论文"],
        ["pVM 跨边界开销", "2%–14%", "AnBridge，Pixel 7 Pro", "论文"],
        ["重置时间、单步分解", "!!缺数!!", "所有被检索论文均未给出", "—"],
    ]
    auto_table(s, R, 92, RW, cols, rows, [1.05, 1.6, 1.55, 0.85], 594, align=["left", "left", "left", "center"])
    footnote(s, "来源：CubeSandbox #1878、CubeBench v0.7.3；arXiv 2509.18119、2603.07432、2604.07277、2410.14803、2609.22978、2605.27761；"
                "Anbox Cloud；AnBridge DSN'26。", y=694, w=1130)


@page
def perf_phone(prs):
    s = new_slide(prs, "手机侧的性能诉求：", "关注单个会话多花多少、后台能否存活，而不是一台机器承载多少",
                  crumb=CRUMB + " › 性能（手机侧诉求）")
    cols = ["指标", "云侧训练", "云手机", "手机本机"]
    M = {"核": "@@● 核心@@", "关": "◐ 关注", "否": "~~○ 次要~~"}
    rows = [
        ["创建 / 启动", M["关"], M["关"], M["关"]],
        ["重置", M["核"], M["关"], M["否"]],
        ["快照恢复", M["关"], M["关"], M["核"]],
        ["单实例常驻内存", M["关"], M["关"], M["核"]],
        ["单机密度", M["核"], M["核"], M["否"]],
        ["单步时延", M["关"], M["关"], M["关"]],
        ["长尾", M["核"], M["否"], M["否"]],
        ["后台存活", M["否"], M["否"], M["核"]],
        ["功耗与发热", M["否"], M["否"], M["核"]],
    ]
    W = 470
    fills = {(i + 1, 3): "peach_l" for i in range(len(rows))}
    band_y = 556
    th = table_height(W, cols, rows, [1.2, 0.9, 0.9, 0.95], style="body", pad=(4, 4))
    pad_v = max(4, int((band_y - 10 - 92 - th) / (2 * (len(rows) + 1))) + 4)
    table_at(s, 32, 92, W, cols, rows, [1.2, 0.9, 0.9, 0.95], style="body", pad=(4, pad_v),
             align=["left", "center", "center", "center"], fills=fills)

    R, RW = 522, 726
    text(s, (R, 92, RW, 22), "手机侧的目标量级（估算与建议值，需真机验证）", style="body", color="accent", check=False)
    cols2 = ["指标", "建议目标", "依据"]
    rows2 = [
        ["进程级会话沙箱创建", "不超过 50 ms", "进程级为毫秒级；工具调用不应增加可感知时延"],
        ["VM 级会话沙箱创建", "预热或快照下不超过 0.5 s", "云侧快照恢复 50–65 ms；手机 UFS 随机缺页按 0.1–0.4 s 估算"],
        ["挂起后恢复（用户切回）", "不超过 1 s", "本库沙箱负载分析的 T3 目标"],
        ["单会话常驻增量", "进程级 40–100 MB；VM 级 150–300 MB", "AnBridge pVM 250 MB；Cube Linux guest 156–193 MiB"],
        ["后台虚拟屏", "每个 0.2–0.5 GB（未实测）", "被操作的应用要在后台再运行一份"],
        ["同时存活的会话", "1–3 个", "并发上限更多受端侧模型与 KV 限制"],
        ["后台存活", "屏幕关闭、中等压力下不被结束；压力大时挂起到闪存而不是丢弃", "Terminal 屏幕关闭即被结束是反例"],
        ["功耗与发热", "待建立口径", "公开资料为空白"],
    ]
    auto_table(s, R, 118, RW, cols2, rows2, [1.25, 1.75, 2.0], band_y - 10 - 118, align=["left", "left", "left"], stretch=True)
    conclusion_band(s, band_y, [
        ("根本区别", "云侧追求「一台机器多少个」，手机侧追求「一个会话多花多少」和「后台能否活下来」"),
        ("云侧做法摊不开", "模板页共享、超分依赖大量同构实例；手机上同时只有 1–3 个会话，共享收益很小"),
        ("手机侧更需要", "快照挂起、按需换入，以及与 LMKD 协同回收：后台缩小、压力下挂起，而不是被结束"),
    ])
    footnote(s, "来源：本库 notes/L-C2-沙箱负载.md §3.3、C2 §3 Q7、discussion/沙箱-商业价值代价与定位.md §3；AnBridge DSN'26；CubeBench v0.7.3。", y=694, w=1100)


# ---------------------------------------------------------------- 五、挑战、研究与创新

@page
def challenges(prs):
    s = new_slide(prs, "技术挑战全景：", "云侧难在平台抽象、实例重量与真实性，手机侧难在隔离开放、生命周期与资源协同",
                  crumb=CRUMB + " › 技术挑战")
    W, gap = 600, 16
    cloud = [
        ("平台抽象", "通用沙箱平台默认承载 Linux 服务，承载完整操作系统时在 cgroup、探针、xattr、符号链接、继承的 fd 上逐一失败（Cube 的 5 个阻塞点）",
         "按模板选 cgroup 模式、TCP 探针、长启动窗口"),
        ("实例重量", "AVD 每个 5–16 GB 内存、30 GB 存储，限制并发", "redroid 容器化；共享只读层；microVM 内存快照"),
        ("重置与长尾", "任务时长相差 100 倍；模拟器交互耗时是推理的 1.7 倍", "快照重置、容器复用、备用池；异步 rollout；单状态多动作"),
        ("图形与快照", "GPU 加速与快照互斥；ARM 服务器多数没有 GPU", "Agent 场景用软渲染、按需截图"),
        ("页大小", "redroid 固定在 4 KB；生态向 16 KB 迁移", "由 guest 自带内核的 microVM 承担"),
        ("真实性与奖励", "反模拟器、Play Integrity、账号态、支付认证、风控；奖励判定要读应用状态", "真机农场；规则校验加模型评判（一致率 83%）；可编程验证的 mock 应用"),
    ]
    phone = [
        ("隔离与开放", "无特权方案（PRoot）隔离强度等于应用沙箱；pKVM 不向第三方开放", "由系统提供分档会话沙箱"),
        ("生命周期", "屏幕关闭 VM 被结束；LMK 查杀；phantom process killer 结束过多子进程",
         "内存气球随应用生命周期回收；需要挂起到闪存、恢复时按需换入"),
        ("资源协同", "后台虚拟屏要在后台再运行一份应用；沙箱与前台应用、端侧模型共享内存", "统一记账；与「内存与资源」服务协同"),
        ("兼容性", "部分 ARM64 机型 ptrace + seccomp 崩溃；Bionic 与 glibc 不兼容", "完整 VM（Terminal 路线）；有限次安全重试"),
        ("安全", "PRoot 不是安全边界；rootfs 无完整性校验；虚拟屏不隔离数据；Napaxi 尚无出口凭证代理", "出口代理、凭证托管、信息流标签（见 C2）"),
        ("测量口径", "启动、内存、功耗、发热都没有公开测量", "建立真机测量基线，作为仿真与评估的输入"),
    ]
    for k, (title, items) in enumerate([("云侧（云手机与训练环境）", cloud), ("手机本机", phone)]):
        x = 32 + k * (W + gap)
        ix, iy, iw, ih = panel(s, (x, 104, W, 582), title, title_style="heading")
        mds = [f"# {n}\n- **难点**：{d}\n- **方向**：{a}" for n, d, a in items]
        for st in ("body", "detail"):
            hs = [measure(m, iw - 16, st, 1, head_style="body_strong") + 10 for m in mds]
            if sum(hs) + 6 * (len(hs) - 1) <= ih + 4:
                break
        extra = (ih + 4 - sum(hs) - 6 * (len(hs) - 1)) / len(hs)
        y = iy - 2
        for m, h in zip(mds, hs):
            h += extra
            rect(s, (ix, y, iw, h), "grey_l", kind="rounded", radius=6)
            text(s, (ix + 8, y + 4, iw - 16, h - 6), m, style=st, gap_pt=1, head_style="body_strong",
                 head_color="accent", valign="middle")
            y += h + 6
    footnote(s, "来源：安卓Agent沙箱洞察.md 第 8 节；CubeSandbox #1878 系列；arXiv 2509.18119、2410.14803、2604.07277、2512.22047、2606.31410；"
                "OpenMinis、Napaxi 源码；LPC 2025。", y=694, w=1130)


@page
def research(prs):
    s = new_slide(prs, "最新研究进展：", "训练侧论文讲清了重置、并发与长尾，手机侧论文集中在安全，缺性能画像",
                  crumb=CRUMB + " › 研究进展")
    cols = ["论文", "机构与时间", "方法要点", "关键数字", "对手机侧的启示"]
    rows = [
        ["DSec（2609.22978）", "DeepSeek，2026-09", "四类后端统一 SDK；EROFS 层组合、按需加载；virtio-pmem + DAX；DAMON + balloon",
         "单节点 800 microVM / 3,200 容器；按需加载快 1.71 倍；内存降 21.2%", "只读底座层、空闲页回收、按需加载可迁移"],
        ["Qwen-UI-Agent（2607.28227）", "阿里 Qwen，2026-07", "redroid 容器化；真机虚拟屏多应用并行；GUI、CLI、API 混合与批量动作",
         "超过 1 万并发环境；100 多台真机", "批量动作、虚拟屏并行对应手机侧时延诉求"],
        ["UI-TARS-2（2509.02544）", "字节 Seed，2025-09", "多 OS VM 平台；租约式生命周期；部分填充的 rollout 池", "数千实例；数千 QPS",
         "租约与会话 ID 是沙箱管理层的最小集"],
        ["MobileRL（2509.18119）", "智谱，2025-09", "Docker AVD；难度自适应正样本回放", "每 AVD 超过 5 GB；稳定 256 路", "安卓实例过重是共性问题"],
        ["DistRL（2410.14803）", "2024-10", "中心训练、分布式采集、Environment Snapshots", "时长差 100 倍；训练效率 3 倍", "快照重置是标配"],
        ["Android Coach（2604.07277）", "浙大、Qualcomm，2026-04", "单状态多动作，critic 复用状态", "交互耗时是推理的 1.7 倍；效率 1.4 倍",
         "减少环境交互与快照互补"],
        ["Xiaomi-GUI-0 / BlueLM-GUI", "小米、vivo，2026", "真机为主的 agentic RL", "AndroidWorld 78.9 / 84.9", "手机厂商的优势是真机与系统权限"],
        ["PhoneWorld、OpenMobile-2、WM-R1", "2026", "可重置的 mock 应用；GUI 与工具混合；世界模型代替环境", "34 个 mock 应用；35 个模拟应用 + 300 多个工具",
         "降低截图轮次；世界模型尚有状态混淆"],
        ["AnBridge（DSN'26）", "那不勒斯、巴黎电信、普渡", "Binder + vsock 跨 pVM 中间件", "Pixel 7 Pro；pVM 250 MB；开销 2%–14%", "手机 pVM 开销可接受"],
        ["Google LPC 2025", "Google，2025", "AVF 上运行 Debian；内存气球联动生命周期；gfxstream AHB 零拷贝", "定性：PRoot ptrace 开销显著",
         "手机 VM 生命周期管理的首份官方实践"],
        ["Aster / IsolateGPT / 2505.12981", "ETH 等；华盛顿大学等", "Arm CCA realm 隔离；应用级执行隔离；攻击面分类", "11 个攻击面；开销小于 30%（二手）",
         "系统级执行与 GUI 交互需分别隔离"],
    ]
    th = auto_table(s, 32, 92, 1216, cols, rows, [1.3, 1.05, 2.2, 1.8, 1.7], 500,
                    align=["left", "left", "left", "left", "left"], stretch=True)
    cy = 92 + th + 8
    conclusion_band(s, cy, [("", "@@训练侧与手机侧尚未接上@@：训练侧讲清了重置、并发与长尾；手机侧集中在安全与隔离架构。"
                                 "本轮没有找到任何论文测量手机上 Agent 沙箱的启动、内存、功耗与发热。")], label="判断")
    footnote(s, "来源：各论文 arXiv 页面与全文（DSec、Qwen-UI-Agent、UI-TARS-2、MobileRL、DistRL、Android Coach、Xiaomi-GUI-0 读全文，其余读摘要）；"
                "AnBridge 与 LPC 2025 主线程读原文。", y=694, w=1130)


@page
def innovations(prs):
    s = new_slide(prs, "技术创新点归类：", "创新集中在少用环境、让环境便宜，单个安卓实例的优化与手机侧测量仍是空白",
                  crumb=CRUMB + " › 技术创新")
    cats = [
        ("快照与重置复用", "Cube + redroid、AgentENV、DistRL、MAI-UI", "把环境状态当作可保存、可恢复的资产"),
        ("减少环境交互", "Android Coach、WM-R1、PhoneWorld", "一个昂贵状态多用几次，或用模型与 mock 代替真实环境"),
        ("环境与训练解耦", "UI-TARS-2、GUI-Owl、AgentRL、DSec、AReaL", "采集与学习分离；沙箱可挂起，配合抢占式训练"),
        ("异构分层调度", "Qwen-UI-Agent、DSec、Xiaomi-GUI-0", "按负载选后端：容器负责规模，真机负责真实性"),
        ("密度优化", "DSec、redroid overlayfs", "共享只读层、按需加载、空闲页回收"),
        ("执行方式优化", "Qwen-UI-Agent、OpenMobile-2、AutoDroid-V2、ClawGUI", "GUI、API、CLI、代码混合；批量动作"),
        ("隔离与授权", "IsolateGPT、Aster、Computer Control", "应用之间隔离；hypervisor 之外的隔离；逐应用授权"),
        ("手机 VM 生命周期", "Google AVF Linux Terminal", "内存与磁盘气球联动应用生命周期；零拷贝图形"),
        ("人在回路", "Qwen-UI-Agent、Computer Control", "支付、验证码等敏感步骤交还用户"),
    ]
    L, W = 32, 820
    g = 12
    cw, ch = (W - 2 * g) / 3, (594 - 2 * g) / 3
    mds = [f"**代表**：{rep}\n**做法**：{how}" for _, rep, how in cats]
    st = next((x for x in ("lead", "body", "detail") if all(measure(m, cw - 20, x, 4) <= ch - 48 for m in mds)), "detail")
    for i, (n, rep, how) in enumerate(cats):
        r, c = divmod(i, 3)
        x, y = L + c * (cw + g), 92 + r * (ch + g)
        hot = n in ("快照与重置复用", "手机 VM 生命周期")
        round_card(s, (x, y, cw, ch), fill="peach_l" if hot else "grey_l", line="red" if hot else "grey_line", radius=10)
        text(s, (x + 10, y + 8, cw - 20, 22), f"**{n}**", style="lead", color="accent" if hot else "primary_text",
             check=False)
        text(s, (x + 10, y + 40, cw - 20, ch - 46), mds[i], style=st, gap_pt=4)
    R, RW = 872, 376
    ix, iy, iw, ih = panel(s, (R, 104, RW, 582), "研究与工程空白", title_style="heading")
    md = ("# 1 安卓客体的快照与恢复\n- fork、快照、恢复的系统评测；恢复后的工作集；「adbd 可连」到「界面稳定」的差距\n"
          "# 2 ARM 云手机\n- 密度与性能的论文，检索未命中\n"
          "# 3 手机本机\n- AVF 上为 Agent 开隔离环境的启动、内存、功耗\n- 后台虚拟屏的内存、GPU 代价与对前台的干扰\n"
          "- GUI Agent 确认与回滚的系统评测\n"
          "# 4 单步时延分解\n- 截图编码、传输、推理、注入、界面稳定等待，没有分项数据\n"
          "!!判断：!!@@「让单个安卓实例更小更快」在学术上几乎空白@@，靠 Cube、redroid 等工程项目推进；"
          "手机侧的测量空白，正是本部门仿真与评估工作的差异化所在。")
    st2 = fit_style(md, iw, ih, ("body", "detail"), 4, head_style="body_strong")
    text(s, (ix, iy, iw, ih), md, style=st2, gap_pt=4, head_style="body_strong", head_color="accent")
    footnote(s, "来源：安卓Agent沙箱洞察.md 第 9 节；notes/AS6-论文与研究进展.md。浅橙卡为与手机侧最相关的两类。", y=694, w=1100)


# ---------------------------------------------------------------- 六、总结

@page
def conclusion(prs):
    s = new_slide(prs, "总结与判断：", "手机侧的关键不在隔离本身，而在会话生命周期与资源协同",
                  crumb=CRUMB + " › 总结")
    cols = ["维度", "现状"]
    rows = [
        ["部署方式", "面向用户的手机 Agent 都在真实系统上执行；隔离执行只见于开发者向开源项目与 Google Linux Terminal"],
        ["沙箱形态", "第三方：PRoot 或 QEMU 用户态；系统：pKVM / AVF、后台虚拟屏；云侧：redroid 容器、AVD、microVM 包 redroid、真机"],
        ["框架支持", "RL 框架不内置安卓；环境层已抽象为服务；Cube 正在补 microVM + redroid"],
        ["虚拟机支持", "云侧 x86 成熟，ARM 要裸金属；手机 pKVM 量产，但第三方权限未明、芯片支持不全、屏幕关闭即被结束"],
        ["性能数据", "云侧训练吞吐有数字；安卓快照、重置、单步时延缺数；手机侧几乎空白"],
    ]
    W = 560
    th = auto_table(s, 32, 92, W, cols, rows, [0.55, 2.6], 330, align=["center", "left"])
    y = 92 + th + 12
    fcard(s, (32, y, W, 686 - y), "建议的后续验证（按优先级）",
          "1. **真机测量手机侧四档沙箱**：PRoot、isolatedProcess + seccomp、pVM、后台虚拟屏；测创建与恢复、PSS 与私有页、单步时延分解、30 分钟功耗与温升\n"
          "2. **在 ARM 服务器上复现 Cube + redroid**：#1880、#1881、#2031 合入后，测多实例密度、恢复后工作集、到界面稳定的时间\n"
          "3. **评估后台虚拟屏的内存与 GPU 代价**：校准每个 0.2–0.5 GB 的估算\n"
          "4. **补核**：豆包手机执行机制、火山云手机形态、MANAGE_VIRTUAL_MACHINE 开放条件", gap_pt=4)
    R, RW = 612, 636
    judg = [
        ("判断一：云侧收敛到「容器化安卓 + microVM 快照 + 真机补充」",
         "训练侧已从 AVD 转向 redroid（Qwen-UI-Agent，超过 1 万并发）；下一步是 microVM 快照与 redroid 结合（Cube 推进中），解决重置与隔离；"
         "真机承担风控与真实性。预计 2027 年出现以秒计的安卓重置数据与 microVM + redroid 的密度数据。"),
        ("判断二：手机侧走「系统提供分档会话沙箱」，而不是「第三方自带沙箱」",
         "第三方只能拿到 PRoot 或 QEMU 用户态；强隔离只在系统手中。Google 已把 GUI 执行（Computer Control）与完整 Linux（Terminal）"
         "收进系统，只开放给 OEM 预装应用，这正是手机厂商的位置。"),
        ("判断三：关键技术在会话生命周期与资源协同",
         "隔离部件已存在，缺的是：组织成会话（创建、挂起、快照、恢复、销毁）；与 LMKD 和内存记账协同（后台缩小、压力下挂起到闪存、恢复时按需换入）；"
         "屏幕关闭时继续存活。新参照：Cube 恢复约 50 ms、Google 内存气球联动、AnBridge 开销 2%–14%。"),
    ]
    stack_cards(s, R, 92, RW, 594, judg, gap=14,
                fills=[("grey_l", "grey_line"), ("grey_l", "grey_line"), ("peach_l", "red")])
    footnote(s, "来源：安卓Agent沙箱洞察.md 第 10 节；与本库汇报材料「执行与沙箱」服务的会话级隔离与状态底座一致。", y=694, w=1100)

"""核心十一页：把《核心十页》的技术总览页（P3）拆成两页能力建设页，输出《核心十一页.pptx》（2026-11-24）。

领导意见：总页的形式可以，但一页装两个领域、结构不好；从能力建设的角度拆成两页，
  P3  Agent OS 领域建模仿真能力建设
  P4  AI+图形领域建模仿真能力建设
两边的竞争力目标和关键技术各自展开。其余九页与十页相同，页码顺延。

两页版式相同：
  左  架构图，自上而下三层：寻优（一行小框）→ 负载建模 → 性能仿真。
      基座是负载建模与性能仿真，业务内容写成这两块和寻优里的条目；
      每层由若干行专项卡片组成，每个专项下面是若干小框，每框一个短词组，文字全部居中。
      图里不写业务目标，也不体现校准。右侧一条回路：性能仿真的评估结果回到寻优。
  右上  竞争力目标：三句话，每句一行、带一个数。
  右下  关键技术：三项放在一个框里，每项一行标题，下面一句话说明、占两行（在逗号处换行）；
        红色编号与架构图里的编号对应。

2026-11-24 第二轮（汇报人与专家看过 P3 之后）：
  - P3 架构图：负载建模压成一行（四个专项各两个小框）；性能仿真扩成五行
    （负载回放 / 三列专项仿真 / 多 IP 性能快仿 / 硬件 IP 模型 / 性能指标输出）。
  - P3 关键技术不再按层罗列，改成三项具体技术，编号标在图里对应的专项上：
    ① 异构多 IP 性能快仿 ② 沙箱端到端性能建模 ③ 会话级内存回收代价建模。
  - 两页右栏统一成「目标每句一行；关键技术一行标题 + 每点一行」。P4 的架构图没有动。

2026-11-24 第三轮：关键技术标题下面不再分点、不要小标题，每项改成一句话，占两行。
  这句话写成上下两个半句，在逗号处软换行：两行各自放得下，PowerPoint 与预览里的断行位置就一致，不会把词拆开。
  措辞用书面的技术表述（基于…模型解析…、构建…、量化…），不写「找出」「快速给出」这类口语。

做法：复用十页的生成脚本（../核心十页/build.py）——同样从《核心九页.pptx》打补丁，只是不再插入原来的总览页，
改插这两页。九页与十页都不会被改写。

运行（在 ppt_templates 的 uv 环境里）：
  cd ~/Projects/ppt_template && uv run python <本目录>/build.py [--preview]
"""

import argparse
import importlib.util
import sys
from pathlib import Path

from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
PPT = HERE.parent
sys.path.insert(0, str(PPT))

import lib  # noqa: E402
from lib import badge, box, poly, rect, text  # noqa: E402
from ppt_templates.geometry import px_to_emu  # noqa: E402
from ppt_templates.preview import render_pngs  # noqa: E402

_spec = importlib.util.spec_from_file_location("ten_pages_build", PPT / "核心十页" / "build.py")
ten = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ten)

OUT = PPT / "核心十一页.pptx"

# ---------------------------------------------------------------- 两页的内容
#
# 架构图里每一层 = 若干行；每一行 =（[专项…]，每行排几个小框）；每个专项 =（标题，[小框词组…]）。词组尽量不超过六个字。
# layer_marks / group_marks：关键技术的红色编号标在哪一层的层名上、或哪个专项的标题旁。
# ret_row：右侧「评估结果」回路从性能仿真的第几行引出（不写则从这一层的中部引出）。
#
# Agent OS 页的条目出处：
#   性能仿真取自推理页、沙箱页与两页内存页的关键技术；「硬件 IP 模型」取自推理页架构图底部的四组硬件；
#   负载建模取自早先的负载量化页（p2_load_inf / p2_load_sbx / p2_load_mm：贴身秘书参考负载、五类任务原型、驻留剖面）。
#   「专家路由」「系统调用」「参数化缩放」三条现有页面里没有明说，是为快仿与拦截开销建模补的输入，汇报人已确认保留。
#   「负载回放」一行是第二轮新归拢的：负载采集、Trace 回放、参数化缩放、逐轮增量原在负载建模里，
#   会话切换来自推理内存页的场景（会话频繁切走切回），多前台叠加来自内存页的交付件「多前台内存协同回放验证」。
#   沙箱的「双路径对照」放在沙箱性能仿真里，与关键技术 ② 的分点对应。
# AI+图形页的条目全部取自同事的三页技术页（图形算法寻优、异构计算仿真平台、3DGS/4DGS）。

AGENT = {
    "title": "Agent OS 领域建模仿真能力建设",
    "suffix": "：以负载建模与性能仿真为基座，支撑推理、沙箱与内存寻优",
    "optimize": [
        ("推理寻优", ["模型结构", "长序列", "异构调度"]),
        ("沙箱寻优", ["原生执行", "调用加速", "启动恢复"]),
        ("内存寻优", ["水线回收", "冷热预取", "缓存分层"]),
    ],
    "down_1": "候选策略与架构",
    "load": [
        ([("场景原型", ["贴身秘书", "五类任务"]),
          ("推理负载", ["长上下文", "专家路由"]),
          ("执行负载", ["工具调用", "系统调用"]),
          ("内存负载", ["驻留剖面", "页面冷热"])], 2),
    ],
    "down_2": "负载：token 序列 · 工具调用 · 内存访问",
    "sim": [
        ([("负载回放", ["负载采集", "Trace 回放", "参数化缩放", "逐轮增量", "会话切换", "多前台叠加"])], 6),
        ([("推理性能仿真", ["长序列量化", "KV 稀疏压缩", "前缀命中", "专家缓存命中", "算子分派", "结构权衡"]),
          ("沙箱性能仿真", ["胶水层转换", "调用拦截", "内核路径", "双路径对照", "启动时延", "热页恢复"]),
          ("内存性能仿真", ["会话级记账", "回收代价", "PSI 压力", "场景关联", "冷热识别", "换出与重算"])], 2),
        ([("多 IP 性能快仿", ["Roofline 建模", "性能上界", "云转端评估", "任务依赖拆解", "空闲 IP 识别",
                         "并行加速空间"])], 6),
        ([("硬件 IP 模型", ["NPU", "CPU/GPU", "LPDDR", "2D-PIM", "UFS", "UFS-PIM"])], 6),
        ([("性能指标输出", ["TTFT/TPS", "执行开销", "恢复时延", "内存均值", "丢帧", "功耗"])], 6),
    ],
    "layer_marks": {},
    "group_marks": {"多 IP 性能快仿": 1, "沙箱性能仿真": 2, "内存性能仿真": 3},
    "ret_row": -1,
    "goals": [
        "**长序列推理**：端侧长序列 Decode @@≥30 TPS@@",
        "**执行沙箱**：执行开销@@低于 Android 基准的一半@@",
        "**X+Agent 内存**：叠加场景内存均值@@优化 ≥150M@@",
    ],
    "techs": [
        ("异构多 IP 性能快仿，支撑云转端性能评估",
         ("基于多 IP Roofline 模型解析算力与带宽性能上界，",
          "结合任务依赖分析，量化多 IP 并行化的加速空间。")),
        ("沙箱端到端性能建模，定位虚拟化开销来源",
         ("构建可回放沙箱负载，在基准与原生双路径对照评测，",
          "分层计量胶水层转换、系统调用拦截与内核路径开销。")),
        ("会话级内存回收代价建模，支撑主动回收与预取",
         ("建立匿名页/DMA/KV/模型内存的会话级统一账本，",
          "构建冷热感知的回收代价模型，量化换出与重算开销。")),
    ],
}

GFX = {
    "title": "AI+图形领域建模仿真能力建设",
    "suffix": "：以负载建模与性能仿真为基座，支撑算法、异构计算与 3DGS 寻优",
    "optimize": [
        ("图形算法寻优", ["候选生成", "进化筛选", "前沿输出"]),
        ("异构计算寻优", ["算子分图", "算子硬化", "数据通路"]),
        ("3DGS/4DGS 寻优", ["性能优化", "内存优化", "效果优化"]),
    ],
    "down_1": "候选算法、分图与硬件形态",
    "load": [
        ([("目标负载", ["超分/插帧", "神经着色/材质", "3DGS/4DGS", "生成式绘制"])], 4),
        ([("负载仿真器", ["指令级抽象", "XPU 分别建模", "算子映射", "可信度标记"]),
          ("指令生成", ["Shader 输入", "生成规则", "结构化 IR", "ISA 指令流"]),
          ("3DGS 负载", ["管线拆解", "光栅化混合", "梯度优化器", "寻址统计"])], 2),
        ([("场景工程化", ["数据采集管理", "混合管线构建", "数据集", "基线算法"])], 4),
    ],
    "down_2": "负载：指令流与算子图",
    "sim": [
        ([("硬件单元建模", ["GPU 单元", "NPU 单元", "TensorCore", "Cache 与存储"]),
          ("性能仿真器", ["执行流程", "数据形态", "耗时建模", "瓶颈归因"]),
          ("数据传输建模", ["统一时间线", "资源占用", "容量临界", "带宽饱和"])], 2),
        ([("评估准则", ["效果评估", "能效评估", "落地成本评估"])], 3),
        ([("分层评估器", ["简化评估", "详细评估", "硬件评估"])], 3),
    ],
    "layer_marks": {"opt": 3, "load": 1, "sim": 2},
    "group_marks": {},
    "goals": [
        "**仿真可信**：指令生成精度 @@90%@@，能耗评估精度 @@75%@@",
        "**异构寻优**：神经材质类负载性能@@提升 5%@@",
        "**3DGS/4DGS**：重建与渲染性能@@提升 5%@@",
    ],
    "techs": [
        ("指令级负载仿真器，还原真实指令流",
         ("面向 GPU/NPU 分别构建指令级负载模型与算子映射，",
          "按生成规则将 Shader 转换为 IR 与 ISA 指令流。")),
        ("XPU 性能仿真器，瓶颈可仿真、可归因",
         ("建模指令在 XPU 内的执行流程、数据形态与耗时，",
          "以统一时间线与资源占用状态刻画多 IP 间数据传输。")),
        ("仿真驱动寻优，量化算法、分图与硬化决策",
         ("以 LLM 进化搜索与分层评估实现图形算法自动寻优，",
          "量化算子分图、硬化与 3DGS/4DGS 优化的性能收益。")),
    ],
}


# ---------------------------------------------------------------- 架构图
#
# 横向：层名列 32–70；通栏底板 78–750；右侧回路 x=764。
# 纵向：三层的高度由各自的行数决定，两个层间空当画向下的箭头。

LX, LW = 32, 38
BX, BR = 78, 750
RET_X = 764
PAD, GAP = 8, 8
TITLE_H, CHIP_H, CHIP_GAP = 22, 26, 5
SIDE = 7                                            # 专项卡片的左右内边距
C_OPT, C_LOAD, C_SIM = "peach_l", "blue_l", "purple_l"      # 小框底色按层区分：寻优、负载建模、性能仿真


def _card_h(rows):
    return 4 + TITLE_H + rows * CHIP_H + (rows - 1) * CHIP_GAP + 7


def _row_h(groups, per_row):
    return _card_h(max(-(-len(chips) // per_row) for _, chips in groups))


def _rows_h(rows):
    return sum(_row_h(groups, per_row) for groups, per_row in rows) + (len(rows) - 1) * GAP


def _fit_pt(txt, width):
    """小框里的词组用 10 号，放不下退到 9 号；仍放不下就报警。"""
    for pt in (10, 9):
        if ten.yahei_px(txt, pt) * 1.05 <= width:
            return pt
    lib._warn(f"小框放不下：{txt}（宽 {width:.0f}px）")
    return 9


def _mark(s, cx, cy, n, d=16):
    """专项标题旁的关键技术编号（比层名上的略小）。"""
    shp = badge(s, cx, cy, n, d=d)
    for r in shp.text_frame.paragraphs[0].runs:
        r.font.size = Pt(10)


def _group(s, b, title, chips, fill, per_row, mark=None):
    """一个专项：白底圆角卡片，标题居中加粗，下面排若干小框（每框一个短词组，居中）。"""
    x, y, w, h = b
    rect(s, b, "bg", line="grey_line", kind="rounded", radius=6, line_width=0.75)
    text(s, (x + 4, y + 3, w - 8, TITLE_H), f"**{title}**", style="detail", align="center", valign="middle",
         check=False)
    for r in ten.last_shape(s).text_frame.paragraphs[0].runs:
        r.font.size = Pt(11)
    if mark:                                        # 编号紧贴在居中标题的左侧
        _mark(s, x + w / 2 - lib.text_em(title) * 11 * lib.PX_PER_PT / 2 - 13, y + 3 + TITLE_H / 2, mark)
    cw = (w - 2 * SIDE - (per_row - 1) * CHIP_GAP) / per_row
    cy = y + 4 + TITLE_H
    for i, chip in enumerate(chips):
        row, col = divmod(i, per_row)
        cb = (x + SIDE + col * (cw + CHIP_GAP), cy + row * (CHIP_H + CHIP_GAP), cw, CHIP_H)
        shp = box(s, cb, chip, fill=fill, line="grey_line", line_width=0.5, kind="rounded", radius=4,
                  style="detail", inset=1, gap_pt=0, check=False)
        pt = _fit_pt(chip, cw - 4)
        for r in shp.text_frame.paragraphs[0].runs:
            r.font.size = Pt(pt)


def _row(s, y, groups, fill, per_row, marks):
    """一行并排的专项卡片，等宽，占满通栏。返回这一行的高度。"""
    h = _row_h(groups, per_row)
    w = (BR - BX - 2 * PAD - (len(groups) - 1) * GAP) / len(groups)
    for i, (title, chips) in enumerate(groups):
        _group(s, (BX + PAD + i * (w + GAP), y, w, h), title, chips, fill, per_row, marks.get(title))
    return h


def _stack(s, y, rows, fill, marks):
    """一层里自上而下的若干行。返回每一行的（y，高）。"""
    spans = []
    for groups, per_row in rows:
        h = _row(s, y, groups, fill, per_row, marks)
        spans.append((y, h))
        y += h + GAP
    return spans


def _layer(s, y, h, name, n=None):
    """一层：左边灰色层名（整层对应一项关键技术时，顶上标编号），右边浅灰通栏底板。"""
    ten._layer_label(s, (LX, y, LW, h), name)
    ten._band(s, (BX, y, BR - BX, h))
    if n:
        badge(s, LX + LW / 2, y + 14, n, d=18)


def _down(s, y1, y2, label):
    """层间向下的箭头，右边写往下传的是什么。"""
    cx = (BX + BR) / 2
    lib.arrow(s, (cx, y1 + 3), (cx, y2 - 3), color="grey_d", width=1.25)
    text(s, (cx + 8, (y1 + y2) / 2 - 8, 300, 16), label, style="caption", color="dark", valign="middle",
         check=False)


def _diagram(s, page):
    top, bottom = 88, 696
    opt_rows = [(page["optimize"], 3)]
    opt_h = 2 * PAD + _rows_h(opt_rows)
    load_h = 2 * PAD + _rows_h(page["load"])
    sim_h = 2 * PAD + _rows_h(page["sim"])
    gap = (bottom - top - opt_h - load_h - sim_h) / 2
    if gap < 18:
        lib._warn(f"架构图排不下，层间只剩 {gap:.0f}px")
    opt_y = top
    load_y = opt_y + opt_h + gap
    sim_y = load_y + load_h + gap
    lm, gm = page.get("layer_marks", {}), page.get("group_marks", {})

    # ---- 寻优：一行小框
    _layer(s, opt_y, opt_h, "寻优", lm.get("opt"))
    _stack(s, opt_y + PAD, opt_rows, C_OPT, gm)
    _down(s, opt_y + opt_h, load_y, page["down_1"])

    # ---- 负载建模
    _layer(s, load_y, load_h, "负载\n建模", lm.get("load"))
    _stack(s, load_y + PAD, page["load"], C_LOAD, gm)
    _down(s, load_y + load_h, sim_y, page["down_2"])

    # ---- 性能仿真
    _layer(s, sim_y, sim_h, "性能\n仿真", lm.get("sim"))
    spans = _stack(s, sim_y + PAD, page["sim"], C_SIM, gm)

    # ---- 右侧回路：性能仿真的评估结果回到寻优
    if page.get("ret_row") is None:
        y_from = sim_y + sim_h / 2
    else:
        ry, rh = spans[page["ret_row"]]
        y_from = ry + rh / 2
    y_to = opt_y + opt_h / 2
    poly(s, [(BR + 1, y_from), (RET_X, y_from), (RET_X, y_to), (BR + 2, y_to)], head=True, color="grey_d",
         width=1.25)
    ym = (y_from + y_to) / 2
    box(s, (RET_X - 8, ym - 34, 16, 68), "评\n估\n结\n果", fill="bg", style="caption", color="dark", inset=0,
        gap_pt=0, check=False)


# ---------------------------------------------------------------- 右栏：竞争力目标与关键技术

GOAL_PT, TECH_PT, DESC_PT = 12, 13, 12             # 目标句、关键技术标题、标题下那句说明的字号


def _one_line(md, pt, room, what):
    """一句话必须落在一行里。宽度按 lib 的保守估算（含中西文间距），给预览里偏宽的中西文混排留余量。"""
    w = lib.text_em(lib.plain(md)) * pt * lib.PX_PER_PT
    if w > room:
        lib._warn(f"{what}一行放不下（{w:.0f} > {room:.0f}px）：{lib.plain(md)}")


def _soft_break(tf):
    """把文本框里的各段并成一段，段与段之间改成软换行：读起来、改起来都是一句话，只是排成两行。"""
    first = tf.paragraphs[0]._p
    for para in tf.paragraphs[1:]:
        tail = first.find(qn("a:endParaRPr"))
        nodes = [parse_xml(f'<a:br {nsdecls("a")}/>')] + para._p.findall(qn("a:r"))
        for node in nodes:
            if tail is None:
                first.append(node)
            else:
                tail.addprevious(node)
        para._p.getparent().remove(para._p)


def _goals_and_techs(s, goals, techs):
    rx, rw, gap, bottom = 792, 456, 12, 696
    px = lib.PX_PER_PT
    # ---- 竞争力目标：三句话，每句一行、只带一个数
    spacing = 1.7
    y = 88
    h = round(42 + len(goals) * GOAL_PT * px * 1.32 * spacing + 12)
    ten._card(s, (rx, y, rw, h))
    ten._heading(s, (rx + 13, y + 8, rw - 26, 26), "竞争力目标")
    text(s, (rx + 13, y + 40, rw - 26, h - 48), "\n".join(goals), style="body", gap_pt=0, check=False)
    for p in ten.last_shape(s).text_frame.paragraphs:
        ten.par_style(p._p, bullet="arrow", line=spacing, algn="l")
    for g in goals:
        _one_line(g, GOAL_PT, rw - 26 - 24 - 4, "目标")                     # 去掉项目符号的悬挂缩进
    # ---- 关键技术：三项放在一个框里，每项一行标题（红色编号与架构图里的编号对应），下面一句话说明、占两行
    y += h + gap
    h = bottom - y
    ten._card(s, (rx, y, rw, h))
    ten._heading(s, (rx + 13, y + 8, rw - 26, 26), "关键技术")
    title_h, spacing = 28, 1.35
    desc_h = 2 * DESC_PT * px * 1.32 * spacing                           # 两行说明在 PowerPoint 里的高度
    body = len(techs) * (title_h + desc_h)
    free = h - 44 - 14 - body
    between = min(free / (len(techs) - 1), 56)                           # 余量分到各项之间，封顶后上下均分
    if between < 8:
        lib._warn(f"关键技术框排不下，各项之间只剩 {between:.0f}px")
    gy = y + 44 + (free - between * (len(techs) - 1)) / 2
    tx = rx + 13 + 26                                                    # 标题与说明都缩进到编号右侧
    tw = rx + rw - 13 - tx
    for i, (title, desc) in enumerate(techs):
        if i:                                                            # 各项之间一条细分隔线
            ly = gy - between / 2
            lib.arrow(s, (rx + 16, ly), (rx + rw - 16, ly), color="grey_line", width=0.75, head=False)
        badge(s, rx + 13 + 9, gy + title_h / 2, i + 1, d=18)
        text(s, (tx, gy, tw, title_h), f"**{title}**", style="body", valign="middle", check=False)
        for r in ten.last_shape(s).text_frame.paragraphs[0].runs:
            r.font.size = Pt(TECH_PT)
        _one_line(title, TECH_PT, tw - 4, "关键技术标题")
        if len(desc) != 2:
            lib._warn(f"关键技术说明要写成上下两个半句：{title}")
        text(s, (tx, gy + title_h, tw, desc_h + 2), "\n".join(desc), style="body", gap_pt=0, check=False)
        tf = ten.last_shape(s).text_frame
        _soft_break(tf)
        ten.par_style(tf.paragraphs[0]._p, line=spacing, algn="l")
        for half in desc:
            _one_line(half, DESC_PT, tw - 4, "关键技术说明的半句")
        gy += title_h + desc_h + between


def add_capability_page(prs, page):
    s = lib.new_slide(prs, page["title"], page["suffix"])
    for sh in list(s.shapes):                      # 去掉标题里框架自动加的全角空格；页码最后统一加
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text
        if t.startswith(page["title"]):
            for r in sh.text_frame.paragraphs[0].runs:
                if r.text.startswith("　"):
                    r.text = r.text[1:]
            sh.width = Emu(px_to_emu(1240))
        elif t.strip().isdigit():
            sh._element.getparent().remove(sh._element)
    _diagram(s, page)
    _goals_and_techs(s, page["goals"], page["techs"])
    return s


# ---------------------------------------------------------------- 入口

def build():
    prs = Presentation(ten.SRC)
    lib.LAYOUTS["blank"] = prs.slides[0].slide_layout       # 与原有各页相同的空白版式
    ten.fix_insight(prs.slides[0])
    ten.rework_inference(prs.slides[5])                     # 九页里的第 6 页：推理服务
    ten.rework_sandbox(prs.slides[6])                       # 九页里的第 7 页：执行沙箱
    for pos, page in ((2, AGENT), (3, GFX)):                # 两页能力建设页放在两页洞察之后、七页技术之前
        add_capability_page(prs, page)
        ten.move_slide(prs, len(prs.slides) - 1, pos)
    ten.unify(prs)
    return prs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--preview-dir")
    args = ap.parse_args()
    prs = build()
    out = Path(args.out) if args.out else OUT
    prs.save(out)
    print(f"saved {out} ({len(prs.slides)} slides)")
    for w in lib.WARNINGS:
        print("WARN", w)
    if args.preview:
        pdir = Path(args.preview_dir) if args.preview_dir else HERE / "preview"
        pdir.mkdir(parents=True, exist_ok=True)
        for old in pdir.glob("slide-*.png"):
            old.unlink()
        render_pngs(prs, pdir, width=1920)
        print(f"preview -> {pdir}")

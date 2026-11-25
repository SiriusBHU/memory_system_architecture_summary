"""核心十页：在汇报人手工合并的《核心九页.pptx》上做三件事，输出《核心十页.pptx》（2026-11-20）。

  1. 洞察页（P1）修正：时间轴补上豆包二代手机；执行沙箱化的示意图改画快照与恢复，痛点里权限放到最后、不加粗不换色；
     X+Agent 内存协同管理的痛点点明内存占用引起 X 应用丢帧卡顿、冷启动慢。
  2. 在两页洞察之后插入技术总览页（新 P3）：左为从场景到硬件 IP 的端到端架构（六层 + 设计态立柱），
     右上为三句竞争力目标，右下为聚合后的三项关键技术。
  3. 全套格式统一：标题位置与字号、深红与蓝两种强调色、字体、页码、同事三页技术页的卡片与交付线。

  4. 2026-11-22 领导反馈：推理页新增「异构多 IP 计算快仿」并重排合并关键技术；沙箱页改为以执行开销为主线
     （目标、三项关键技术、架构图、交付线），总览页同步。

输入是手工改过的 pptx，所以这里是「打补丁」而不是从零生成：只动上面列出的形状，其余原样保留。
《核心九页.pptx》不会被改写。

运行（在 ppt_templates 的 uv 环境里）：
  cd ~/Projects/ppt_template && uv run python <本目录>/build.py [--preview]
"""

import argparse
import copy
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.dml.color import RGBColor
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
PPT = HERE.parent
sys.path.insert(0, str(PPT))

import lib  # noqa: E402
from lib import arrow, badge, box, outline, rect, round_card, text  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from ppt_templates.draw import SHAPES  # noqa: E402
from ppt_templates.geometry import px_to_emu  # noqa: E402
from ppt_templates.preview import render_pngs  # noqa: E402

SHAPES.setdefault("triangle", MSO_SHAPE.ISOSCELES_TRIANGLE)     # 交付线的三角节点；有的 ppt_templates 版本没登记

SRC = PPT / "核心九页.pptx"
OUT = PPT / "核心十页.pptx"

RED, BLUE, BLACK = "A00000", "0000FF", "000000"
FONT = "微软雅黑"
PX = 9525


# ---------------------------------------------------------------- 通用：按 id 找形状、删形状、改文字

def walk(shapes):
    for sh in shapes:
        yield sh
        if sh.shape_type == 6:      # 组合
            yield from walk(sh.shapes)


def by_id(slide, sid):
    for sh in walk(slide.shapes):
        if sh.shape_id == sid:
            return sh
    raise KeyError(f"找不到形状 id={sid}")


def drop(slide, ids):
    for sid in ids:
        el = by_id(slide, sid)._element
        el.getparent().remove(el)


def set_runs(shape, runs, para=0, algn=None):
    """用 [(文字, 是否加粗, 颜色)] 重写一段文字，字号、字体等其余属性沿用该段原来的第一个 run。"""
    p = shape.text_frame.paragraphs[para]._p
    old = p.findall(qn("a:r"))
    tpl = copy.deepcopy(old[0].find(qn("a:rPr")))
    for r in old:
        p.remove(r)
    end = p.find(qn("a:endParaRPr"))
    for txt, bold, color in runs:
        rpr = copy.deepcopy(tpl)
        rpr.set("b", "1" if bold else "0")
        fill = rpr.find(qn("a:solidFill"))
        for child in list(fill):
            fill.remove(child)
        fill.append(parse_xml(f'<a:srgbClr {nsdecls("a")} val="{color}"/>'))
        r = parse_xml(f'<a:r {nsdecls("a")}><a:t/></a:r>')
        r.insert(0, rpr)
        r.find(qn("a:t")).text = txt
        if end is not None:
            end.addprevious(r)
        else:
            p.append(r)
    if algn:
        p.find(qn("a:pPr")).set("algn", algn)


def par_style(p, bullet=None, line=None, algn=None, hang=230505, bullet_color=None):
    """按手工页的写法重排一段的 a:pPr：行距、对齐、项目符号。
    bullet：'square' 空心方框（卡片标题）、'arrow' 箭头（要点）、'num' 圈码自动编号、None 不动项目符号。"""
    ppr = p.get_or_add_pPr()
    if algn:
        ppr.set("algn", algn)
    keep = {}
    for child in list(ppr):
        keep[child.tag] = child
        ppr.remove(child)
    a = nsdecls("a")
    order = []
    if line:
        order.append(parse_xml(f'<a:lnSpc {a}><a:spcPct val="{int(line * 100000)}"/></a:lnSpc>'))
    elif qn("a:lnSpc") in keep:
        order.append(keep[qn("a:lnSpc")])
    for tag in ("a:spcBef", "a:spcAft"):
        if qn(tag) in keep:
            order.append(keep[qn(tag)])
    if bullet:
        ppr.set("marL", str(hang))
        ppr.set("indent", str(-hang))
        if bullet_color:
            order.append(parse_xml(f'<a:buClr {a}><a:srgbClr val="{bullet_color}"/></a:buClr>'))
        if bullet == "num":
            order.append(parse_xml(f'<a:buFont {a} typeface="{FONT}"/>'))
            order.append(parse_xml(f'<a:buAutoNum {a} type="circleNumDbPlain"/>'))
        else:
            order.append(parse_xml(f'<a:buFont {a} typeface="Wingdings" panose="05000000000000000000" '
                                   'pitchFamily="2" charset="2"/>'))
            order.append(parse_xml(f'<a:buChar {a} char="{"p" if bullet == "square" else "Ø"}"/>'))
    else:
        for tag in ("a:buClrTx", "a:buClr", "a:buSzTx", "a:buFontTx", "a:buFont", "a:buNone", "a:buChar",
                    "a:buAutoNum"):
            if qn(tag) in keep:
                order.append(keep[qn(tag)])
    for el in order:
        ppr.append(el)


def yahei_px(s, pt):
    """一行文字在 PowerPoint 里的宽度估算（px）：按 lib 的微软雅黑字宽表，不加 lib 为保守起见附加的中西文间距。"""
    return sum(lib._char_em(c) for c in s) * pt * lib.PX_PER_PT


def last_shape(slide):
    return slide.shapes[len(slide.shapes) - 1]


# ---------------------------------------------------------------- 1. 洞察页（P1）

def fix_insight(s):
    # ---- 1.1 时间轴：三款产品改成四款，按时间补上豆包二代手机（2026-09-16 开售，早于 9-29 的 OpenAI dot）
    #      数据出处：../2027-agentos-ai-graphics/notes/D1-commercial-deep-dive.md §5（界面新闻、第一财经）
    drop(s, range(79, 94))          # 原来的三组：圆点、日期、卡片、产品名、说明
    tl = 166                        # 时间轴线的 y（Connector 7，保留）
    prods = [
        ("2026-08", "xAI Grok Bot",
         "账号级常驻云端电脑，200 美元/月\nGrok 月活 3 个月由 !!3500 万增至 1.17 亿!!"),
        ("2026-09", "豆包二代手机开售",
         # 只写「系统级 Agent」：二代是否仍以 GUI 自动化为主，D1 笔记里有两种说法，列为待核实
         "努比亚 NaviX Ultra，系统级 Agent\n预约 !!36 万台以上!!；任务成功率 !!>80%!!"),
        ("2026-09", "OpenAI dot",
         "每个 Agent 一台云端电脑；ChatGPT 周活 !!10 亿!!\nCodex 周用户 2 个月由 !!500 万增至 800 万!!"),
        ("2026-10", "阶跃手机开售",
         "7 月发布系统级 Agent OS（Step AOS）\n10 月整机开售；端侧小模型加云端大模型"),
    ]
    # 卡宽按各自最长一行的宽度分配，余量平均分给四张卡；四张卡连同间距占满背景框内侧（44–1236）
    # 卡片高 84：正常是两行说明；万一某行在别的字体下折成三行，也还在卡片里（原来高 72，只容两行）
    grow = 10
    panel, fan = by_id(s, 75), by_id(s, 94)
    panel.height = panel.height + px_to_emu(grow)                 # 背景框 100–256 → 100–266
    fan.top, fan.height = fan.top + px_to_emu(grow), fan.height - px_to_emu(grow)   # 扇面随之收短，下沿不动
    gap, pad, cy, ch = 8, 4, tl + 10, 84
    need = [max(yahei_px(lib.plain(ln), 10) for ln in md.split("\n")) + 2 * pad for _, _, md in prods]
    slack = (1192 - gap * (len(prods) - 1) - sum(need)) / len(prods)
    if slack < 12:
        lib._warn(f"时间轴卡片余量只有 {slack:.0f}px，文字可能折行")
    px = 44
    for (date, name, md), n in zip(prods, need):
        cw = n + slack
        cx = px + cw / 2
        rect(s, (cx - 6, tl - 6, 12, 12), "red", kind="oval")
        text(s, (cx - 50, tl - 24, 100, 16), f"@@{date}@@", style="detail", align="center", check=False)
        round_card(s, (px, cy, cw, ch), radius=10)
        text(s, (px + pad, cy + 3, cw - 2 * pad, 22), f"**{name}**", style="body", color="primary_text",
             align="center", check=False)
        text(s, (px + pad, cy + 24, cw - 2 * pad, ch - 26), md, style="detail", align="center", valign="middle",
             gap_pt=0, check=False)
        px += cw + gap

    # ---- 1.2 执行沙箱化：示意图从「调用在沙箱边界上判定」改成「会话的快照与恢复」
    #      性能团队汇报，重点放在快照和恢复；权限仍然要做，但只在痛点末尾提一句
    #      数据出处：../notes/S-沙箱实例开销-汇总.md（Cube 快照 35.6 ms + 拉起 53.1 ms，官方基准）、
    #      ../安卓Agent沙箱洞察.md（AgentENV 快照恢复 <50 ms，厂商自报；手机侧 AVF / pKVM 无量产的会话快照）
    drop(s, range(114, 124))        # 原图：外部 Agent、应用工具、会话沙箱红框、A2A / MCP 箭头与标签
    set_runs(by_id(s, 112), [("从应用内执行，转为", False, BLACK),
                             ("会话沙箱执行，可快照、可恢复", True, BLUE)])
    _diagram_snapshot(s)
    set_runs(by_id(s, 124), [
        ("产品化进展", True, BLACK), ("：", False, BLACK),
        ("云侧 ", False, BLACK), ("腾讯 CubeSandbox", True, BLUE), (" 快照加恢复约 90 ms、", False, BLACK),
        ("Kimi AgentENV", True, BLUE), (" 恢复 <50 ms；手机侧尚未量产", False, BLACK)])
    set_runs(by_id(s, 143), [
        ("瓶颈与痛点：", True, BLACK),
        ("会话缺乏快照，任务中断直接丢失", True, RED),           # 原句照用，只是提到前面
        ("；端侧缺乏沙箱权限管理，头部应用厂商接入困难", False, BLACK)], algn="l")   # 权限放后面，不加粗不换色

    # ---- 1.3 X+Agent 内存协同管理：痛点点明后果，不只写占用
    pain = by_id(s, 141)
    pain.left, pain.width = Emu(px_to_emu(855)), Emu(px_to_emu(389))     # 与另两框的痛点同宽
    set_runs(pain, [
        ("瓶颈与痛点：", True, BLACK),
        ("权重与 KV 超 2.5G", True, RED), ("，引起 ", False, BLACK),
        ("X 应用丢帧卡顿、冷启动慢", True, RED),
        ("；KV 丢弃后重算需 6–14 秒", False, BLACK)], algn="l")
    set_runs(by_id(s, 142), [                                           # 推理框的痛点：只把对齐改成与另两框一致
        ("瓶颈与痛点", True, BLACK), ("：", False, BLACK), ("端侧算力受限、", False, BLACK),
        ("Agent长上下文推理慢", True, RED), ("，异构算力", False, BLACK),
        ("缺乏统一调度与针对性架构设计", True, RED)], algn="l")


def _diagram_snapshot(s):
    """执行沙箱化的示意图（底板 455..826 × 409..583）：上面是会话沙箱里一个会话的三个状态，下面是闪存里的快照；
    红色只留给两条主路径：回收前先快照、切回时热页优先恢复。"""
    fx, fy, fw, fh = 467, 415, 347, 82
    outline(s, (fx, fy, fw, fh), line="grey_d", width=1.25, dash=True)
    text(s, (fx, fy + 3, fw, 16), "**会话沙箱（每会话一个）**", style="detail", align="center", check=False)
    cy, ch = fy + 24, 46
    chips = [(479, 92, "**运行**\nAgent 执行", "green_l", False),
             (592, 97, "**停放**\n内存已释放", "bg", True),
             (710, 92, "**恢复**\n任务接续", "green_l", False)]
    for x, w, md, fill, dash in chips:
        box(s, (x, cy, w, ch), md, fill=fill, line="grey_d", dash=dash, inset=2, gap_pt=0,
            color="grey_d" if dash else None)
    arrow(s, (572, cy + ch / 2), (591, cy + ch / 2), color="dark", width=1.25)
    arrow(s, (690, cy + ch / 2), (709, cy + ch / 2), color="dark", width=1.25)
    # 下：闪存里的快照（与另两框底部的浅蓝条同位置）
    by, bh = 547, 32
    box(s, (480, by, 320, bh), "UFS：沙箱快照（工作集热页 + 冷页）", fill="blue_l")
    x1, x2 = 512, 768
    arrow(s, (x1, cy + ch + 1), (x1, by - 1), color="red", width=1.5)
    arrow(s, (x2, by - 1), (x2, cy + ch + 1), color="red", width=1.5)
    text(s, (x1 + 6, 501, 124, 38), "① 回收压力下\n!!先快照、后释放!!", style="detail", gap_pt=0, check=False)
    text(s, (x2 - 130, 501, 124, 38), "② 用户切回时\n!!热页优先恢复!!", style="detail", align="right", gap_pt=0,
         check=False)


# ---------------------------------------------------------------- 1b. 推理页与沙箱页（2026-11-22 领导反馈）
#
# 推理页（九页的第 6 页，成品 P7）：
#   新增关键技术一「异构多 IP 计算快仿，支撑 Agent 云转端性能评估」（多 IP-Roofline 性能快仿、并行化机会寻找）；
#   原关键技术一（超长序列推理）顺延为二；原二（NPU/PIM 异构融合）与原三（模型架构寻优）合并为三。
# 沙箱页（九页的第 7 页，成品 P8）：
#   专家意见：Agent 沙箱当前最大的问题是开销。现有方案在 Android 上跑非原生的 Linux，胶水层转换命令带来成倍开销，
#   其中 ptrace 与 seccomp 拦截最高带来 30 倍以上开销；快照与快速恢复排在其次。据此：
#   目标改为「以 Android 为 benchmark，原生沙箱执行开销低于参照物的一半」；
#   关键技术一 端到端性能建模（开销分层拆解、沙箱负载建模）；二 原生执行（系统调用加速、原生 Linux 执行环境）；
#   三 快速启动与快照恢复。左下架构图随之重画，交付线改成与三项关键技术对应。

def set_title(slide, main, suffix):
    """在原标题框里重写标题：冒号前 24 号、冒号后 18 号，其余格式沿用原来的 run。"""
    p = title_shape(slide).text_frame.paragraphs[0]._p
    runs = p.findall(qn("a:r"))
    big = copy.deepcopy(next(r for r in runs if r.find(qn("a:rPr")).get("sz") == "2400"))
    small = copy.deepcopy(next(r for r in runs if r.find(qn("a:rPr")).get("sz") == "1800"))
    for r in runs:
        p.remove(r)
    end = p.find(qn("a:endParaRPr"))
    for tpl, txt in ((big, main), (small, suffix)):
        tpl.find(qn("a:t")).text = txt
        if end is not None:
            end.addprevious(tpl)
        else:
            p.append(tpl)


def set_kt(shape, heading, bullets):
    """重写一张关键技术卡：标题一行（深红加粗），下面每条是「子技术名（加粗）：说明，指标（蓝色加粗）」。"""
    set_runs(shape, [(heading, True, RED)], para=0)
    for i, (name, desc, metric) in enumerate(bullets, 1):
        runs = [(name, True, BLACK), ("：" + desc, False, BLACK)]
        if metric:
            runs.append((metric, True, BLUE))
        set_runs(shape, runs, para=i)


def put_par(shape, idx, new_p):
    """把文本框的第 idx 段整段换成 new_p（另一段的深拷贝），用于在卡片之间搬运原文。"""
    old = shape.text_frame.paragraphs[idx]._p
    old.addprevious(new_p)
    old.getparent().remove(old)


def set_plain(shape, lines):
    """把一个框里的文字换成若干行，格式沿用原来第一段的第一个 run（交付线上的框用）。"""
    ps = [p._p for p in shape.text_frame.paragraphs]
    tpl = copy.deepcopy(ps[0])
    for p in ps[1:]:
        p.getparent().remove(p)
    for i, line in enumerate(lines):
        p = ps[0] if i == 0 else copy.deepcopy(tpl)
        if i:
            ps[0].getparent().append(p)
        runs = p.findall(qn("a:r"))
        for r in runs[1:]:
            p.remove(r)
        runs[0].find(qn("a:t")).text = line


def rework_inference(s):
    set_title(s, "端侧Agent OS推理服务能力提升", "：多 IP 快仿/异构融合推理加速，支撑超长序列 30+TPS 推理")
    # ---- 挑战：第 ② 条末尾的「模型选型需要进行针对性设计」换成「云转端性能缺乏快速评估」，长度基本不变；
    #      目标保持原文（原文已有「硬件-模型架构协同仿真寻优能力」，再加字会多折一行、排不下）
    set_runs(by_id(s, 5), [
        ("挑战：", True, BLACK), ("① 端侧 Agent 对 ", False, BLACK), ("32k~128k 超长上下文 ", True, RED),
        ("推理需求激增，KV Cache占用与MoE专家路由对端侧 NPU 算力 / 内存容量提出挑战；"
         "② 端侧异构计算 IP（UFS-PIM / DDR-PIM / NPU / HBF）迭出且", False, BLACK),
        ("缺乏统一调度", True, RED), ("，", False, BLACK), ("云转端性能缺乏快速评估", True, RED)], para=0)

    # ---- 右侧三张卡：新增一，原一顺延为二，原二、三合并为三
    k1, k2, k3 = by_id(s, 47), by_id(s, 50), by_id(s, 53)
    old1 = [copy.deepcopy(p._p) for p in k1.text_frame.paragraphs[:3]]
    for i, p in enumerate(old1):                     # 原关键技术一整卡搬到第二张卡，只改标题里的序号
        put_par(k2, i, p)
    head = k2.text_frame.paragraphs[0].runs
    head[0].text = head[0].text.replace("关键技术一", "关键技术二")
    set_kt(k1, "关键技术一：异构多 IP 计算快仿，支撑 Agent 云转端性能评估", [
        ("多 IP-Roofline 性能快仿", "对 Agent 执行与推理建立各 IP 的 Roofline 模型，快速给出性能上界，",
         "支撑云转端性能精准评估"),
        ("并行化机会寻找", "拆解 Agent 任务的执行与推理依赖，识别可并发的阶段与空闲 IP，",
         "给出多 IP 并行化的加速空间")])
    set_kt(k3, "关键技术三：NPU/PIM 异构融合与硬件亲和的架构寻优", [
        ("异构融合调度", "按算术强度分派算子，带宽统一仲裁，权重 / KV 按 PIM 计算形态亲和排布，", "推理性能提升 10%"),
        ("模型结构寻优", "建模注意力结构与层数/维度配比的资源-性能权衡，后训练寻优专家路由，",
         "UFS 多 Channel 带宽利用率 > 80%")])

    # ---- 左下架构图（在一个被缩放过的组合里，坐标按组合内的坐标系）：编号顺延，「端侧约束」改成新的关键技术一
    by_id(s, 19).text_frame.paragraphs[0].runs[0].text = "2"        # 超长序列推理引擎
    by_id(s, 21).text_frame.paragraphs[0].runs[0].text = "3"        # 异构融合调度（模型结构寻优原本就是 3）
    sim = by_id(s, 42)                                              # 原「端侧约束：算力 · 带宽 · 存储」
    sim.top, sim.height = Emu(px_to_emu(610)), Emu(px_to_emu(62))
    sim.fill.solid()
    sim.fill.fore_color.rgb = RGBColor(0xFD, 0xEA, 0xDA)
    sim.line.color.rgb = RGBColor(0xA0, 0x00, 0x00)
    sim.line.width = Pt(1.5)
    set_runs(sim, [("多 IP 性能快仿", True, RED)], para=0)
    sim.text_frame.paragraphs[0].runs[0].font.size = Pt(10)
    set_runs(sim, [("Roofline 建模", False, BLACK)], para=1)
    extra = copy.deepcopy(sim.text_frame.paragraphs[1]._p)
    sim.text_frame.paragraphs[1]._p.addnext(extra)
    extra.find(qn("a:r")).find(qn("a:t")).text = "云转端评估 · 并行化机会"
    link = by_id(s, 44)                                             # 模型结构寻优到它的竖线，随框上沿缩短
    link.height = Emu(px_to_emu(610) - link.top - px_to_emu(2))
    dot = copy.deepcopy(by_id(s, 35)._element)                      # 借「3」那个红色编号的样子做一个「1」
    sim._element.addnext(dot)
    dot.find(".//" + qn("p:cNvPr")).set("id", str(max(sh.shape_id for sh in walk(s.shapes)) + 1))
    off = dot.find(".//" + qn("a:off"))
    off.set("x", str(px_to_emu(514 + 158 - 12)))
    off.set("y", str(px_to_emu(610 - 8)))
    dot.find(".//" + qn("a:t")).text = "1"

    # ---- 交付线：三个日期与原交付件不动，第一个节点补上快仿评估
    set_plain(by_id(s, 55), ["多 IP 快仿评估", "超长序列推理原型验证"])


def rework_sandbox(s):
    set_title(s, "端侧Agent OS执行沙箱", "：原生执行降低拦截开销，沙箱开销低于 Android 基准的一半")
    top = by_id(s, 5)
    set_runs(top, [
        ("挑战：", True, BLACK),
        ("① Agent 沙箱虚拟化开销大：现有方案在 Android 上运行非原生的 Linux 环境，胶水层转换命令带来成倍开销，",
         False, BLACK),
        ("ptrace 与 seccomp 拦截最高带来 30 倍以上开销", True, RED),
        ("；② 沙箱启动、快照与恢复慢，仍影响会话切换与前台体验", False, BLACK)], para=0)
    set_runs(top, [
        ("目标：", True, BLACK),
        ("提供原生执行的低开销 Agent 沙箱；以 Android 为 benchmark，", False, BLACK),
        ("原生沙箱执行开销低于参照物的一半，后台执行时功耗开销 <3%", True, BLUE),
        ("，前台应用帧率影响 <1%；RL 训练沙箱执行效率优化 20%，", False, BLACK),
        ("内存超分比超过 3 倍", True, BLUE)], para=1)

    # ---- 右侧三张卡
    k1, k2, k3 = by_id(s, 45), by_id(s, 48), by_id(s, 51)
    snap, tmpl = (copy.deepcopy(p._p) for p in k1.text_frame.paragraphs[1:3])   # 原文：快照恢复、模板写时复制
    set_kt(k1, "关键技术一：Agent 沙箱端到端性能建模", [
        ("性能开销分层拆解", "按胶水层命令转换、ptrace / seccomp 拦截、内核路径逐层计量工具调用的耗时，",
         "定位拦截开销的来源"),
        ("Agent 沙箱负载建模", "采集工具调用的命令、文件与进程操作，构建可回放的沙箱负载，",
         "以 Android 为 benchmark 对比评测")])
    set_kt(k2, "关键技术二：Agent 沙箱原生执行", [
        ("系统调用加速", "规避或减少 ptrace / seccomp 拦截，执行过程中仅对敏感调用做拦截判定，",
         "沙箱执行开销低于参照物的一半"),
        ("原生 Linux 执行环境", "不再用用户态模拟 Linux，改由内核原生隔离能力承载，工具命令原生运行，",
         "免去胶水层的命令转换开销")])
    set_runs(k3, [("关键技术三：沙箱快速启动与快照恢复", True, RED)], para=0)
    put_par(k3, 1, tmpl)                             # 启动在前：模板实例与写时复制（原文与指标不动）
    put_par(k3, 2, snap)                             # 快照与恢复在后（原文与指标不动），只把「会话」改成「沙箱」
    first = k3.text_frame.paragraphs[2].runs[0]
    first.text = first.text.replace("会话快照", "沙箱快照")

    # ---- 交付线：与三项关键技术一一对应，三个日期不动
    set_plain(by_id(s, 53), ["沙箱性能建模与 Android 基准"])
    set_plain(by_id(s, 56), ["原生执行原型验证"])
    set_plain(by_id(s, 59), ["启动与快照恢复原型验证"])

    # ---- 左下架构图重画：原图讲的是调用判定与出口代理，现在讲两条执行路径的开销对比
    drop(s, range(7, 43))
    _diagram_sandbox_overhead(s)


def _kbox(s, b, n, title, lines):
    """架构图里本页要做的模块（与其余技术页同一画法）：浅橙底深红框、右上角红色编号。"""
    box(s, b, "\n".join([f"!!{title}!!", *lines]), style="detail", inset=4, fill="peach_l", line="red",
        line_width=1.5, gap_pt=1, check=False)
    badge(s, b[0] + b[2] - 2, b[1] + 2, n, d=20)


def _diagram_sandbox_overhead(s):
    """沙箱页左下的架构图（32..672 × 352..700）：同一份 Agent 沙箱负载走两条路径，左为参照物，右为原生沙箱。"""
    def plain(b, md, fill="bg", line="grey_d", **kw):
        return box(s, b, md, fill=fill, line=line, style="detail", inset=3, gap_pt=1, check=False, **kw)

    lx, lw, rx, rw = 32, 294, 338, 334
    lc, rc = lx + lw / 2, rx + rw / 2
    # 调用方
    plain((32, 352, 314, 24), "System Agent")
    plain((358, 352, 314, 24), "三方 Agent")
    for x in (189, 515):
        arrow(s, (x, 377), (x, 391), color="grey_d")
    text(s, (196, 377, 300, 14), "工具调用：命令 · 文件 · 进程 · 网络", style="caption", color="dark", valign="middle",
         check=False)
    # ① 端到端性能建模：同一份负载、两条路径、逐层计量
    _kbox(s, (32, 392, 640, 46), 1, "端到端性能建模",
          ["同一份 Agent 沙箱负载在两条路径上回放 · 按胶水层 / 拦截 / 内核路径分层计量开销"])
    for x in (lc, rc):
        arrow(s, (x, 439), (x, 449), color="grey_d")
    # 左：参照物（目标句里「开销低于参照物的一半」指的就是它，用词保持一致）
    y0, h0 = 450, 186
    rect(s, (lx, y0, lw, h0), "grey_l", kind="rounded", radius=8)
    text(s, (lx + 8, y0 + 4, lw - 16, 14), "**参照物：Android 上的现有沙箱**", style="caption", color="grey_d",
         check=False)
    plain((lx + 8, y0 + 24, lw - 16, 30), "胶水层：命令与路径转换")
    arrow(s, (lc, y0 + 55), (lc, y0 + 61), color="grey_d", head=False)
    plain((lx + 8, y0 + 62, lw - 16, 30), "用户态模拟的 Linux 环境（非原生）")
    arrow(s, (lc, y0 + 93), (lc, y0 + 99), color="grey_d", head=False)
    plain((lx + 8, y0 + 100, lw - 16, 44), "**ptrace / seccomp 逐调用拦截**\n!!最高带来 30 倍以上开销!!", fill="pink_l")
    text(s, (lx + 8, y0 + 150, lw - 16, 30), "虚拟化开销成倍叠加，是当前的性能瓶颈", style="caption", color="dark",
         align="center", valign="middle", check=False)
    # 右：原生沙箱
    rect(s, (rx, y0, rw, h0), "grey_l", kind="rounded", radius=8)
    text(s, (rx + 8, y0 + 4, rw - 16, 14), "**原生沙箱（本项目）**　@@目标：执行开销低于参照物的一半@@", style="caption",
         color="grey_d", check=False)
    _kbox(s, (rx + 8, y0 + 24, rw - 16, 62), 2, "原生执行",
          ["原生 Linux 执行环境，免胶水层转换", "系统调用加速，规避或减少拦截"])
    _kbox(s, (rx + 8, y0 + 94, rw - 16, 44), 3, "启动 · 快照 · 恢复", ["模板写时复制拉起 · 热页优先恢复"])
    weak = plain((rx + 8, y0 + 146, rw - 16, 24), "调用判定 · 出口代理 · 凭证托管（安全体系复用）", line="grey_line")
    for r in weak.text_frame.paragraphs[0].runs:     # 权限这一行弱化：小一号、深灰
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    for x in (lc, rc):
        arrow(s, (x, y0 + h0 + 1), (x, 645), color="grey_d")
    # 内核与复用的安全体系
    box(s, (32, 646, 640, 24), "**Android 内核**　namespace · seccomp-BPF · SELinux · AVF / pKVM", fill="bg",
        line="grey_d", style="caption", inset=2, check=False)
    box(s, (32, 678, 640, 22), "**安全体系（复用）**　签名与身份 · 权限框架 · Keystore / StrongBox · TEE 与证明",
        fill="grey_l", line="grey_line", style="caption", inset=2, check=False)


# ---------------------------------------------------------------- 2. 技术总览页
#
# 2026-11-20 第二版，按汇报人意见重做：
#   左：端到端的领域架构，自上而下六层通栏（场景负载 → 应用接入 → 系统服务 → 资源底座 → 内核 → 硬件 IP），
#       层与层之间标出往下传的是什么；资源底座分「存」与「算」，正对下面的存储 IP 与算力 IP，
#       推理服务骑在「存｜算」分界线上（KV 与权重落在存，算子落在算）；
#       右侧竖条是设计态的建模仿真与寻优，图形与 Agent OS 推理的建模仿真能力都放在上面，四段与运行态各层对齐。
#       模块按属性配色（AI+图形、推理与算力、内存与存储、沙箱执行），同色自上而下连成一列就是那条纵向链路；
#       不再用红框标「本期工作」，只用暗红色圆形编号标出四项关键技术在架构里的位置。
#   右上：竞争力目标只写三句话，每句一个数。
#   右下：关键技术聚合成四项、放在一个框里，每项一行标题、下面分点：AI+图形的仿真与寻优一项，
#       Agent OS 的推理、内存、沙箱各一项；不是每一页都算关键技术（3DGS 只出现在架构图里）。
#   左右不对半：架构图约占六成。

OVERVIEW_TITLE = "总体架构与关键技术"
OVERVIEW_SUFFIX = "：从场景到硬件 IP 端到端打通，构建仿真寻优、推理、内存与沙箱四项基座能力"

GOALS = [   # 「⏎」处固定换行；沙箱的目标按 2026-11-22 的反馈改成「开销低于 Android 基准的一半」
    "**端侧 Agent 可用**：长序列 @@Decode ≥30 TPS@@，⏎@@原生沙箱开销低于 Android 基准的一半@@",
    "**X+Agent 共存**：减少前台应用丢帧与冷启动变慢⏎@@叠加场景内存均值优化 ≥150M@@",
    "**AI+图形可寻优**：算法与硬件由实机试错转向仿真⏎@@端侧能耗评估精度 75%@@",
]
KEY_TECHS = [   # 四项：AI+图形一项，Agent OS 的推理、内存、沙箱各一项；编号与架构图里的红色圆形编号一致
    ("AI+图形：仿真与自动寻优", [
        "**异构计算仿真**：XPU/存储/传输统一建模，量化分图与硬化",
        "**图形算法自动寻优**：LLM 进化搜索，仿真评估替代实机试错"]),
    ("Agent OS 推理：多 IP 快仿与异构融合推理", [      # 与推理页的三项关键技术一一对应
        "**多 IP 性能快仿**：Roofline 建模，支撑云转端性能评估",
        "**超长序列推理**：KV 稀疏与上下文压缩，专家路由多级复用",
        "**异构融合与架构寻优**：算子分派、亲和排布与模型结构寻优"]),
    ("Agent OS 内存：X+Agent 协同与主动管理", [
        "**X+Agent 内存协同**：会话级记账，主动回收，冷热预取",
        "**模型内存主动管理**：KV 冷热分层，专家缓存，零拷贝加载"]),
    ("Agent OS 沙箱：原生执行与低开销", [               # 与沙箱页的三项关键技术一一对应
        "**端到端性能建模**：开销分层拆解，Agent 沙箱负载建模",
        "**原生执行**：系统调用加速，减少 ptrace/seccomp 拦截",
        "**启动与快照恢复**：模板写时复制拉起，热页优先恢复"]),
]


def _band(s, b):
    """一层的浅灰底板（无边框、小圆角）。"""
    return rect(s, b, "grey_l", kind="rounded", radius=8)


def _layer_label(s, b, md):
    box(s, b, "\n".join(f"**{ln}**" for ln in md.split("\n")), fill="grey_m", style="detail", inset=1, gap_pt=0,
        check=False)


def _hdr(s, x, y, w, md):
    text(s, (x, y, w, 14), f"**{md}**", style="caption", color="grey_d", check=False)


def _tag_hdr(s, x, y, w, tag, md):
    """带深灰小标签的层内标题，如「存｜内存与资源服务」。"""
    box(s, (x, y, 16, 15), f"**{tag}**", fill="grey_d", style="caption", color="on_primary", inset=0, check=False)
    text(s, (x + 22, y, w - 22, 15), f"**{md}**", style="caption", color="grey_d", valign="middle", check=False)


# 架构图里模块的底色表示属性；同一种颜色自上而下连成一列，就是那条纵向链路
C_GFX = "purple_l"          # AI+图形：运行时的渲染管线，以及设计态的仿真与寻优
C_COMPUTE = "blue_l"        # 推理与算力：推理服务、异构计算调度、算力 IP
C_MEMORY = "green_m"        # 内存与存储：内存与资源服务、存储 IP
C_SANDBOX = "peach_l"       # 沙箱执行
LEGEND = ((C_GFX, "AI+图形"), (C_COMPUTE, "推理与算力"), (C_MEMORY, "内存与存储"), (C_SANDBOX, "沙箱执行"))
SIZE_CAPTION_PX = 9 * 4 / 3                         # 9 号字的字宽（px）


def _chip(s, b, md, fill="bg"):
    """小模块：细灰边、9 号字；默认白底（不属于四类属性的中性模块）。"""
    return box(s, b, md, fill=fill, line="grey_d" if fill != "bg" else "grey_line", style="caption", inset=2,
               gap_pt=0, check=False)


def _block(s, b, title, lines, fill, n=None, title_pt=10, corner=False):
    """架构图里的一个模块：底色表示属性，细灰边；标题黑色加粗 10 号，说明 9 号。
    n 是它对应的关键技术编号，用暗红色圆形数字标在右上角；不是关键技术的模块不标。"""
    shp = box(s, b, "\n".join([f"**{title}**", *lines]), fill=fill, line="grey_d", line_width=0.75,
              style="caption", inset=3, gap_pt=1, check=False)
    for r in shp.text_frame.paragraphs[0].runs:
        r.font.size = Pt(title_pt)
    if n and corner:        # 窄卡片（竖条、内存两张卡）：编号骑在右上角，不压标题，也让开上方的层内标题
        badge(s, b[0] + b[2] - 1, b[1] + 1, n, d=18)
    elif n:                 # 其余模块：编号压在上边线上、离右边 26px，不会被看成右邻模块的编号
        badge(s, b[0] + b[2] - 26, b[1] + 2, n, d=18)
    return shp


def _flow(s, x, y1, y2, label=None, both=False, side="right", w=176):
    """层间的竖向箭头，旁边 9 号深灰字写往下传的是什么。"""
    arrow(s, (x, y1), (x, y2), color="grey_d", both=both)
    if label:
        ym = (y1 + y2) / 2 - 7
        if side == "right":
            text(s, (x + 5, ym, w, 14), label, style="caption", color="dark", valign="middle", check=False)
        else:
            text(s, (x - 5 - w, ym, w, 14), label, style="caption", color="dark", align="right", valign="middle",
                 check=False)


def add_overview(prs):
    s = lib.new_slide(prs, OVERVIEW_TITLE, OVERVIEW_SUFFIX)
    for sh in list(s.shapes):                      # 去掉标题里框架自动加的全角空格；页码最后统一加
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text
        if t.startswith(OVERVIEW_TITLE):
            for r in sh.text_frame.paragraphs[0].runs:
                if r.text.startswith("　"):
                    r.text = r.text[1:]
            sh.width = Emu(px_to_emu(1240))        # 标题约占 1216 的 95%，放宽一点防折行（汇报人自己的长标题页也是这么做的）
        elif t.strip().isdigit():
            sh._element.getparent().remove(sh._element)
    _architecture(s)
    _goals_and_techs(s)
    return s


def _architecture(s):
    # ---- 横向：层名列 32–70；运行态的栈 78–616（每层一条通栏底板）；设计态竖条 632–776
    sx, sr = 78, 616
    div = 372                   # 资源底座与硬件 IP 两层里「存｜算」的分界；上一层的推理服务正好骑在这条线上
    sbx_b = (86, 186)           # 系统服务层三张卡的 x 与宽：执行沙箱、推理服务、混合渲染
    inf_b = (div - 88, 176)
    gfx_b = (472, 136)
    agent_x, agent_w = 86, inf_b[0] + inf_b[1] - 86      # 上三层左半：端侧 Agent
    # ---- 纵向：六层
    y1, h1 = 88, 58
    y2, h2 = 158, 42
    y3, h3 = 226, 138
    y4, h4 = 390, 154
    y5, h5 = 570, 30
    y6, h6 = 612, 62
    rows = ((y1, h1), (y2, h2), (y3, h3), (y4, h4), (y5, h5), (y6, h6))
    for (y, h), name in zip(rows, ("场景\n负载", "应用\n接入", "系统\n服务", "资源\n底座", "内核", "硬件\nIP")):
        _layer_label(s, (32, y, 38, h), name)
        _band(s, (sx, y, sr - sx, h))
    sbx_x, inf_x, gfx_x = (b[0] + b[1] / 2 for b in (sbx_b, inf_b, gfx_b))
    agent_c = agent_x + agent_w / 2

    # ---- 一、场景与负载
    for x, w, name, lines in (
            (agent_x, agent_w, "端侧 Agent 场景", "贴身秘书长程任务 · 跨应用事务 · X+Agent 多前台\n"
                                              "32K–128K 上下文 · 约 200 次工具调用/天 · 12GB 机型"),
            (gfx_b[0], gfx_b[1], "AI+图形负载", "超分插帧 · 神经着色\n3DGS · 生成式渲染")):
        _hdr(s, x, y1 + 4, w, name)
        text(s, (x, y1 + 20, w, h1 - 24), lines, style="caption", gap_pt=0, check=False)
    _flow(s, agent_c, y1 + h1 + 1, y2 - 1)
    _flow(s, gfx_x, y1 + h1 + 1, y2 - 1)

    # ---- 二、应用与接入
    cwid = (agent_w - 2 * 8) / 3
    for i, nm in enumerate(("System Agent", "三方 Agent", "应用 AI 功能")):
        _chip(s, (agent_x + i * (cwid + 8), y2 + 9, cwid, 24), nm)
    gwid = (gfx_b[1] - 8) / 2
    for i, nm in enumerate(("游戏引擎", "空间影像")):
        _chip(s, (gfx_b[0] + i * (gwid + 8), y2 + 9, gwid, 24), nm)

    # ---- 三、系统服务：执行沙箱｜推理服务｜混合渲染管线
    ky, kh = y3 + 22, h3 - 30
    _hdr(s, agent_x, y3 + 5, agent_w, "Agent OS 系统服务")
    sbx = _block(s, (sbx_b[0], ky, sbx_b[1], kh), "执行沙箱",
                 ["原生执行 · 系统调用加速", "启动 · 快照 · 恢复", "~~调用判定 · 出口代理~~"], C_SANDBOX, 4)
    for r in sbx.text_frame.paragraphs[-1].runs:          # 权限一行弱化，但要看得清：用 595959，不用浅灰
        r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    _block(s, (inf_b[0], ky, inf_b[1], kh), "推理服务",
           ["超长序列推理引擎", "KV 稀疏与上下文压缩", "专家路由多级缓存复用"], C_COMPUTE, 2)
    _hdr(s, gfx_b[0], y3 + 5, gfx_b[1], "AI+图形 运行时")
    _block(s, (gfx_b[0], ky, gfx_b[1], kh - 34), "混合渲染管线", ["传统渲染 + 神经网络", "超分插帧 · 神经着色"], C_GFX)
    _block(s, (gfx_b[0], ky + kh - 28, gfx_b[1], 28), "3DGS/4DGS 优化", [], C_GFX, title_pt=9)
    _flow(s, sbx_x, y2 + h2 + 1, y3 - 1, "工具调用（MCP / A2A）")
    _flow(s, inf_x, y2 + h2 + 1, y3 - 1, "推理请求")
    _flow(s, gfx_x, y2 + h2 + 1, y3 - 1, "渲染请求")

    # ---- 四、资源底座：存｜算（虚线分界一直贯到硬件 IP 层）
    ry, rh = y4 + 22, h4 - 30
    mwid = (div - 6 - 86 - 10) / 2
    _tag_hdr(s, 86, y4 + 5, 200, "存", "内存与资源服务")
    _block(s, (86, ry, mwid, rh), "X+Agent 内存协同",
           ["会话级统一记账", "MemCG 水线自适应", "主动回收 · 冷热预取"], C_MEMORY, 3, corner=True)   # 编号放右上角，让开上方的层内标题
    _block(s, (86 + mwid + 10, ry, mwid, rh), "模型内存主动管理",
           ["KV 前缀与冷热分层", "MoE 专家缓存", "模型加载零拷贝"], C_MEMORY, 3, corner=True)
    cx0 = div + 20
    _tag_hdr(s, cx0, y4 + 5, 200, "算", "异构计算调度")
    _block(s, (cx0, ry, sr - 8 - cx0, rh), "异构融合调度",
           ["算子按算术强度分派 · 分图决策", "带宽统一仲裁", "权重 / KV 亲和排布"], C_COMPUTE, 2)
    for y, h in ((y4, h4), (y6, h6)):
        arrow(s, (div + 6, y + 8), (div + 6, y + h - 8), color="grey_line", head=False, dash=True)
    _flow(s, sbx_x, y3 + h3 + 1, y4 - 1, "会话状态")
    _flow(s, div + 6 - 42, y3 + h3 + 1, y4 - 1, "KV · 权重", side="left")      # 推理服务一手落在「存」
    _flow(s, div + 6 + 42, y3 + h3 + 1, y4 - 1, "LLM 算子")                    # 一手落在「算」
    _flow(s, gfx_x, y3 + h3 + 1, y4 - 1, "图形算子")

    # ---- 五、内核与驱动
    text(s, (sx + 8, y5, sr - sx - 16, h5),
         "**内核与驱动**　memcg · PSI · LMKD · zRAM · dma-buf　AVF / pKVM　GPU / NPU 驱动",
         style="caption", align="center", valign="middle", check=False)
    mem_x, cmp_x = (86 + div) / 2, (cx0 + sr - 8) / 2
    _flow(s, mem_x, y4 + h4 + 1, y5 - 1, "换出 · 快照 · 按需换入", both=True)
    _flow(s, cmp_x, y4 + h4 + 1, y5 - 1, "算子与数据下发")

    # ---- 六、硬件 IP：存储 IP 在「存」正下方，算力 IP 在「算」正下方
    _chip(s, (86, y6 + 8, mwid, h6 - 16), "**LPDDR + 2D-PIM**\n热专家 · KV · 工作集", C_MEMORY)
    _chip(s, (86 + mwid + 10, y6 + 8, mwid, h6 - 16), "**UFS + UFS-PIM**\n冷专家 · 快照 · 换出", C_MEMORY)
    hx = cx0
    for nm, sub, w in (("NPU", "推理", 44), ("GPU", "+ TensorCore", 94), ("CPU", "其余算子", 66)):   # 合计 204
        _chip(s, (hx, y6 + 8, w, h6 - 16), f"**{nm}**\n{sub}", C_COMPUTE)
        hx += w + 6
    _flow(s, mem_x, y5 + h5 + 1, y6 - 1)
    _flow(s, cmp_x, y5 + h5 + 1, y6 - 1)

    # ---- 竖条：设计态的建模仿真与寻优，图形（紫）、Agent OS 推理（蓝）与沙箱（橙）的建模仿真能力都放在这里；
    #      四段与运行态各层对齐：负载建模 → 算法与模型寻优 → 算子与通路仿真 → 硬件评估
    px, pw = 632, 144
    pb = y6 + h6
    _band(s, (px, y1, pw, pb - y1))
    text(s, (px + 4, y1 + 3, pw - 8, 16), "**建模仿真与寻优**", style="caption", align="center", valign="middle",
         check=False)
    text(s, (px + 4, pb - 17, pw - 8, 14), "设计态 · 离线", style="caption", color="dark", align="center",
         valign="middle", check=False)
    zones = [   # （起始 y，高，连到运行态的 y，本段的卡片）；卡 =（底色，标题，说明行，关键技术编号）
        (y1 + 22, y2 + h2 - y1 - 22, y1 + h1 - 16, [
            (C_GFX, "负载仿真器", ["指令级 · 3DGS 负载"], None),
            (C_COMPUTE, "长序列推理建模", ["时延/带宽/内存量化"], None)]),
        (y3 + 2, h3 - 4, y3 + h3 / 2, [
            (C_GFX, "图形算法自动寻优", ["LLM 进化搜索"], 1),
            (C_COMPUTE, "模型结构寻优", ["Attn 与专家架构"], 2),
            (C_SANDBOX, "沙箱性能建模", ["分层拆解与负载建模"], 4)]),
        (y4 + 2, h4 - 4, y4 + h4 / 2, [
            (C_GFX, "异构计算仿真", ["算子调优与分图决策", "存算协同数据通路"], 1),
            (C_COMPUTE, "推理异构融合仿真", ["算子路由与带宽仲裁", "权重 / KV 亲和排布"], None)]),
        (y5, pb - 20 - y5, y6 + h6 / 2 - 8, [
            (C_GFX, "性能仿真器", ["算子硬化收益评估"], None),
            (C_COMPUTE, "多 IP 性能快仿", ["云转端性能评估"], 2)]),
    ]
    for zy, zh, _, zone_cards in zones:
        ch = (zh - 6 * (len(zone_cards) - 1)) / len(zone_cards)
        for k, (fill, title, lines, n) in enumerate(zone_cards):
            _block(s, (px + 8, zy + k * (ch + 6), pw - 16, ch), title, lines, fill, n, corner=True)
    for (zy0, zh0, *_), (zy1, *_) in zip(zones, zones[1:]):
        arrow(s, (px + pw / 2, zy0 + zh0 + 1), (px + pw / 2, zy1 - 1), color="grey_d")
    for _, _, cy, *_ in zones:                     # 与运行态整层往来（接在通栏底板上，不特指哪一列）
        arrow(s, (sr + 2, cy), (px + 7, cy), color="grey_d", dash=True, both=True)

    # ---- 图例
    ly, lx = y6 + h6 + 6, sx
    for fill, name in LEGEND:
        rect(s, (lx, ly + 3, 14, 10), fill, line="grey_d")
        w = lib.text_em(name) * SIZE_CAPTION_PX + 6
        text(s, (lx + 19, ly, w, 16), name, style="caption", color="dark", check=False)
        lx += 19 + w + 10
    rect(s, (lx + 2, ly + 2, 12, 12), "red", kind="oval")
    text(s, (lx + 19, ly, 240, 16), "暗红编号：关键技术所在位置", style="caption", color="dark", check=False)


def _soft_breaks(p):
    """把一段里的「⏎」换成段内换行（a:br），用来把一句话固定断成两行，不靠各家软件自己折行。"""
    for r in list(p.findall(qn("a:r"))):
        t = r.find(qn("a:t"))
        if "⏎" not in (t.text or ""):
            continue
        parts = t.text.split("⏎")
        t.text = parts[0]
        anchor = r
        for part in parts[1:]:
            br = parse_xml(f'<a:br {nsdecls("a")}/>')
            anchor.addnext(br)
            anchor = br
            if part:
                nr = copy.deepcopy(r)
                nr.find(qn("a:t")).text = part
                anchor.addnext(nr)
                anchor = nr
        if not parts[0]:
            p.remove(r)


def _goals_and_techs(s):
    rx, rw, gap, bottom = 792, 456, 12, 696
    # ---- 竞争力目标：三句话，每句固定两行、只带一个数
    y, h = 88, 216
    _card(s, (rx, y, rw, h))
    _heading(s, (rx + 13, y + 8, rw - 26, 26), "竞争力目标")
    text(s, (rx + 13, y + 40, rw - 26, h - 50), "\n".join(GOALS), style="body", gap_pt=2, check=False)
    for p in last_shape(s).text_frame.paragraphs:
        par_style(p._p, bullet="arrow", line=1.3, algn="l")
        _soft_breaks(p._p)
    # ---- 关键技术：四项放在一个框里，每项一行标题（红色编号与架构图里的编号对应），下面分点
    y += h + gap
    h = bottom - y
    _card(s, (rx, y, rw, h))
    _heading(s, (rx + 13, y + 8, rw - 26, 26), "关键技术")
    title_h, spacing = 22, 1.25
    line_h = lib.SIZES["detail"] * lib.PX_PER_PT * 1.32 * spacing        # 分点一行在 PowerPoint 里的高度
    body = sum(title_h + len(points) * line_h for _, points in KEY_TECHS)
    between = (h - 40 - 10 - body) / (len(KEY_TECHS) - 1)                # 余量平均分到各项之间
    if between < 4:
        lib._warn(f"关键技术框排不下，各项之间只剩 {between:.0f}px")
    gy = y + 40
    tx = rx + 13 + 26                                                    # 标题与分点都缩进到编号右侧
    for i, (title, points) in enumerate(KEY_TECHS):
        badge(s, rx + 13 + 9, gy + title_h / 2, i + 1, d=18)
        text(s, (tx, gy, rx + rw - 13 - tx, title_h), f"**{title}**", style="body", valign="middle", check=False)
        ph = len(points) * line_h
        text(s, (tx, gy + title_h, rx + rw - 13 - tx, ph + 2), "\n".join(points), style="detail", gap_pt=0,
             check=False)
        for p in last_shape(s).text_frame.paragraphs:
            par_style(p._p, bullet="arrow", line=spacing, algn="l", hang=171450)
        gy += title_h + ph + min(between, 14)


def _card(s, b):
    """右侧卡片：与各技术页相同的浅灰圆角卡（细黑边）。"""
    shp = rect(s, b, "grey_l", line="text", kind="rounded", radius=14, line_width=0.5)
    return shp


def _heading(s, b, title, note=None):
    """卡片标题：空心方框项目符号 + 深红加粗（与各技术页的「关键技术一：…」同一写法）。"""
    md = f"!!{title}!!" + (f"~~{note}~~" if note else "")
    text(s, b, md, style="body", valign="middle", check=False)
    tb = last_shape(s)
    par_style(tb.text_frame.paragraphs[0]._p, bullet="square", algn="l")
    if note:                                       # 括注用 10 号灰字
        tb.text_frame.paragraphs[0].runs[-1].font.size = Pt(10)


def move_slide(prs, old, new):
    lst = prs.slides._sldIdLst
    ids = list(lst)
    el = ids[old]
    lst.remove(el)
    lst.insert(new, el)


# ---------------------------------------------------------------- 3. 全套格式统一
#
# 以汇报人自己的五页（洞察页与四页 Agent OS 技术页）为准，把同事的四页对齐过来：
#   标题：左上角同一位置，冒号前 24 号、冒号后 18 号，深红加粗
#   颜色：红色统一为 A00000，蓝色统一为 0000FF；「挑战」里的强调用红，「目标」与句末指标用蓝
#   字体：全部微软雅黑；9.35、18.65 这类缩放出来的字号取整
#   版面：正文从 y=88 起；交付线改成同一种画法（浅灰框、粗红线、三角节点、蓝色日期）
#   页码：十页统一重编

RED_ALIAS = {"990000", "C00000", "E9002F", "A00203"}
BLUE_ALIAS = {"0303FE"}
BLACK_ALIAS = {"1D1D1A"}
SIZE_MAP = {"935": "900", "1865": "1800", "1335": "1400"}
SYMBOL_FONTS = {"Wingdings", "Wingdings 2", "Wingdings 3", "Symbol", "Webdings"}
_RPR_HEAD = {qn(f"a:{t}") for t in ("ln", "noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill",
                                    "effectLst", "effectDag", "highlight", "uLnTx", "uLn", "uFillTx", "uFill")}
METRIC = re.compile(r"\d+(?:\.\d+)?\s*(?:%|dB)")
DELIMS = "，；。：,;"
DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")


def unify_colors(slide):
    for el in slide._element.iter(qn("a:srgbClr")):
        v = el.get("val").upper()
        if v in RED_ALIAS:
            el.set("val", RED)
        elif v in BLUE_ALIAS:
            el.set("val", BLUE)
        elif v in BLACK_ALIAS:
            el.set("val", BLACK)


def unify_fonts(slide):
    """每个 run 显式写微软雅黑（含表格单元格）；符号字体的 run 不动；缩放出来的小数字号取整。"""
    a = nsdecls("a")
    for tag in ("a:rPr", "a:endParaRPr"):
        for rp in slide._element.iter(qn(tag)):
            if rp.get("sz") in SIZE_MAP:
                rp.set("sz", SIZE_MAP[rp.get("sz")])
            lat = rp.find(qn("a:latin"))
            if rp.find(qn("a:sym")) is not None or (lat is not None and lat.get("typeface") in SYMBOL_FONTS):
                continue
            for t in ("a:latin", "a:ea", "a:cs"):
                for e in rp.findall(qn(t)):
                    rp.remove(e)
            idx = 0
            for i, ch in enumerate(rp):
                if ch.tag in _RPR_HEAD:
                    idx = i + 1
            for k, t in enumerate(("latin", "ea", "cs")):
                rp.insert(idx + k, parse_xml(f'<a:{t} {a} typeface="{FONT}"/>'))


def title_shape(slide):
    for sh in slide.shapes:
        if sh.has_text_frame and sh.top is not None and sh.top < px_to_emu(80):
            runs = sh.text_frame.paragraphs[0].runs
            if runs and runs[0].font.size == Pt(24):
                return sh
    raise KeyError("找不到标题")


def unify_title(slide, template):
    """把标题换成与汇报人各页相同的文本框：同位置、不自动调整大小、冒号归后半句。"""
    old = title_shape(slide)
    full = "".join(r.text for p in old.text_frame.paragraphs for r in p.runs).strip()
    main, sep, rest = full.partition("：")
    new = copy.deepcopy(template._element)
    old._element.addprevious(new)
    c_old, c_new = old._element.find(".//" + qn("p:cNvPr")), new.find(".//" + qn("p:cNvPr"))
    c_new.set("id", c_old.get("id"))
    c_new.set("name", c_old.get("name"))
    old._element.getparent().remove(old._element)
    p = new.find(".//" + qn("a:p"))
    runs = p.findall(qn("a:r"))
    big = copy.deepcopy(next(r for r in runs if r.find(qn("a:rPr")).get("sz") == "2400"))
    small = copy.deepcopy(next(r for r in runs if r.find(qn("a:rPr")).get("sz") == "1800"))
    for r in runs:
        p.remove(r)
    end = p.find(qn("a:endParaRPr"))
    for tpl, txt in ((big, main), (small, sep + rest)):
        if not txt:
            continue
        tpl.find(qn("a:t")).text = txt
        if end is not None:
            end.addprevious(tpl)
        else:
            p.append(tpl)
    off, ext = new.find(".//" + qn("a:off")), new.find(".//" + qn("a:ext"))
    off.set("x", str(px_to_emu(32)))
    off.set("y", str(px_to_emu(32)))
    ext.set("cx", str(px_to_emu(1216)))
    ext.set("cy", str(px_to_emu(40)))


def page_numbers(prs):
    for i, s in enumerate(prs.slides, 1):
        for sh in list(s.shapes):
            if (sh.has_text_frame and sh.text_frame.text.strip().isdigit() and sh.top > px_to_emu(680)
                    and sh.width < px_to_emu(100)):
                sh._element.getparent().remove(sh._element)
        text(s, (1180, 700, 68, 14), str(i), style="footnote", color="grey_d", align="right", check=False)


# ---- 强调色：按字符区间给一段文字上色

def _set_color(rpr, color, bold=None):
    fill = rpr.find(qn("a:solidFill"))
    if fill is None:
        fill = parse_xml(f'<a:solidFill {nsdecls("a")}/>')
        ln = rpr.find(qn("a:ln"))
        if ln is not None:
            ln.addnext(fill)
        else:
            rpr.insert(0, fill)
    for ch in list(fill):
        fill.remove(ch)
    fill.append(parse_xml(f'<a:srgbClr {nsdecls("a")} val="{color}"/>'))
    if bold is not None:
        rpr.set("b", "1" if bold else "0")


def style_range(p, start, end, color, bold=True):
    """把一段里第 start 到 end 个字符（按各 run 拼起来的文字计）设成指定颜色并加粗，必要时拆分 run。"""
    pos = 0
    for r in list(p.findall(qn("a:r"))):
        t = r.find(qn("a:t"))
        s = t.text or ""
        a0, b0 = pos, pos + len(s)
        pos = b0
        lo, hi = max(a0, start), min(b0, end)
        if lo >= hi:
            continue
        clean = copy.deepcopy(r)
        anchor, first = r, True
        for txt, hit in ((s[:lo - a0], False), (s[lo - a0:hi - a0], True), (s[hi - a0:], False)):
            if not txt:
                continue
            if first:
                node, first = r, False
            else:
                node = copy.deepcopy(clean)
                anchor.addnext(node)
            node.find(qn("a:t")).text = txt
            if hit:
                if node.find(qn("a:rPr")) is None:
                    node.insert(0, parse_xml(f'<a:rPr {nsdecls("a")}/>'))
                _set_color(node.find(qn("a:rPr")), color, bold)
            anchor = node


def _highlight_paragraph(p):
    """同事技术页的一段文字，按汇报人各页的用色重新标强调：
    「挑战」段里原有的加粗词（不含「性能上：」这类小标签）改深红；「目标」段里原有的加粗词改蓝；
    其余各段中含指标的分句（如「指令生成精度达到90%」）蓝色加粗。"""
    runs = p.findall(qn("a:r"))
    texts = [r.find(qn("a:t")).text or "" for r in runs]
    full = "".join(texts)
    if not full.strip() or full.startswith("难题") or full.startswith("交付件"):
        return
    kind = "challenge" if full.startswith("挑战") else "goal" if full.startswith("目标") else "bullet"
    spans = []
    if kind in ("challenge", "goal"):
        pos, bolds = 0, []
        for r, t in zip(runs, texts):
            rp = r.find(qn("a:rPr"))
            bolds.append((pos, pos + len(t), rp is not None and rp.get("b") == "1"))
            pos += len(t)
        i = 0
        while i < len(bolds):
            if not bolds[i][2]:
                i += 1
                continue
            j = i
            while j + 1 < len(bolds) and bolds[j + 1][2]:
                j += 1
            a0, b0 = bolds[i][0], bolds[j][1]
            is_label = full[b0:b0 + 1] == "：" or full[a0:b0].endswith("：") or a0 == 0
            if not is_label:
                spans.append((a0, b0, RED if kind == "challenge" else BLUE))
            i = j + 1
    if kind != "challenge":
        for m in METRIC.finditer(full):
            a0 = max(full.rfind(d, 0, m.start()) for d in DELIMS) + 1
            while a0 < m.start() and full[a0] == " ":
                a0 += 1
            spans.append((a0, m.end(), BLUE))
    for a0, b0, color in spans:
        style_range(p, a0, b0, color)


def unify_tech_page(s):
    """同事的一页技术页：正文下移到 y=88，交付线按统一画法重画，卡片圆角与强调色对齐。"""
    tops = [sh for sh in s.shapes if sh is not None]
    title = title_shape(s)
    # ---- 交付线：收集交付件与日期，删掉原来的线、三角、日期、交付件框
    delivs, dates, junk = [], [], []
    for sh in tops:
        if sh.shape_id == title.shape_id:
            continue
        t = sh.text_frame.text.strip() if sh.has_text_frame else ""
        low = sh.top > px_to_emu(590)
        if DATE.match(t):
            dates.append((sh.left, t))
            junk.append(sh)
        elif t.startswith("交付件"):
            delivs.append((sh.left, t))
            junk.append(sh)
        elif low and sh.shape_type == 9 and sh.width > px_to_emu(400):          # 时间轴线
            junk.append(sh)
        elif low and sh.shape_type == 1 and "triangle" in sh._element.xml.split("prstGeom")[1][:40]:
            junk.append(sh)
    for sh in junk:
        sh._element.getparent().remove(sh._element)
    items = []
    for (_, d), (_, t) in zip(sorted(delivs), sorted(dates)):
        y, m, dd = DATE.match(t).groups()
        items.append((re.sub(r"^交付件[：:]\s*", "", d), f"{y}.{int(m):02d}.{int(dd):02d}"))

    # ---- 左右两栏各自下移，使正文顶部落在 y=88
    card = next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith("挑战"))
    split = card.left + card.width + px_to_emu(8)
    body = [sh for sh in s.shapes if sh.shape_id != title.shape_id]
    left = [sh for sh in body if sh.left + sh.width / 2 < split]
    right = [sh for sh in body if sh.left + sh.width / 2 >= split]
    for col in (left, right):
        dy = px_to_emu(88) - min(sh.top for sh in col)
        for sh in col:
            sh.top = sh.top + dy
    # ---- 卡片圆角与汇报人各页一致（约 14px）
    for sh in body:
        t = sh.text_frame.text if sh.has_text_frame else ""
        if t.startswith(("挑战", "难题")):
            gd = sh._element.find(".//" + qn("a:gd"))
            if gd is not None:
                gd.set("fmla", f"val {int(px_to_emu(14) / min(sh.width, sh.height) * 100000)}")
    # ---- 右栏最后一张卡到交付线之间有空当：平均分给各张卡（卡内浮动的文字、小图随所属卡片下移）
    cards = sorted((sh for sh in right if sh.has_text_frame and sh.text_frame.text.startswith("难题")),
                   key=lambda sh: sh.top)
    free = px_to_emu(622) - (cards[-1].top + cards[-1].height)
    if free > px_to_emu(6):
        grow = int(min(free / len(cards), px_to_emu(28)))
        owned = [[sh for sh in right if sh is not c and sh not in cards
                  and c.top <= sh.top + sh.height / 2 <= c.top + c.height] for c in cards]
        for i, (c, members) in enumerate(zip(cards, owned)):
            for sh in members:
                sh.top = sh.top + i * grow
            c.top, c.height = c.top + i * grow, c.height + grow
    # ---- 交付线：与汇报人各页同一位置、同一画法
    rx = min(sh.left for sh in right) / PX
    rw = max(sh.left + sh.width for sh in right) / PX - rx
    lib.milestones(s, (rx, 618, rw, 104), items, box_w=176 if len(items) <= 3 else 128, box_h=44, style="detail")
    # ---- 强调色；行距由 1.5 收到 1.35（这三页的卡片按 1.5 倍行距排不下，末行会压到卡片下沿之外）
    for sh in body:
        if sh.has_text_frame and sh.width > px_to_emu(300):
            for p in sh.text_frame.paragraphs:
                _highlight_paragraph(p._p)
                spc = p._p.find(qn("a:pPr") + "/" + qn("a:lnSpc") + "/" + qn("a:spcPct"))
                if spc is not None and spc.get("val") == "150000":
                    spc.set("val", "135000")
    # ---- 架构图里压在分区标题上的编号，挪到所属分区的左上角（与另两个编号的摆法一致）
    for grp in (sh for sh in body if sh.shape_type == 6):
        kids = list(grp.shapes)
        for owner_text, num in (("存算协同数据通路优化", "3"),):
            owner = next((k for k in kids if k.has_text_frame and k.text_frame.text.startswith(owner_text)), None)
            dot = next((k for k in kids if k.has_text_frame and k.text_frame.text.strip() == num
                        and "ellipse" in k._element.xml), None)
            if owner is not None and dot is not None:
                dot.left, dot.top = owner.left - px_to_emu(6), owner.top - px_to_emu(6)


def unify_gfx_insight(s):
    """同事的洞察页：标题换位后，把标题下的导语框下移并收窄行距，留出与其他页相同的标题间距。"""
    lead = next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith("端侧图形后处理"))
    bottom = lead.top + lead.height
    lead.top = px_to_emu(82)
    lead.height = bottom - lead.top
    for p in lead.text_frame.paragraphs:
        par_style(p._p, line=1.3)
    for sh in s.shapes:
        if sh.has_table and sh.table.cell(0, 0).text_frame.text.strip() == "游戏":
            cols = sh.table.columns
            move = px_to_emu(14)                       # 第一列 146 → 160，第二列 211 → 197（表头仍放得下）
            cols[0].width, cols[1].width = cols[0].width + move, cols[1].width - move


def ppt_text_height(shape, width=None):
    """文本在 PowerPoint 里大约占多高（px）：按 lib 的微软雅黑字宽表折行，行高取 1.32 倍字号乘行距。"""
    bp = shape._element.find(".//" + qn("a:bodyPr"))
    ins = [int(bp.get(k, d)) / PX for k, d in (("lIns", 91440), ("rIns", 91440), ("tIns", 45720), ("bIns", 45720))]
    w = (width if width is not None else shape.width / PX) - ins[0] - ins[1]
    total = ins[2] + ins[3]
    for para in shape.text_frame.paragraphs:
        ppr = para._p.find(qn("a:pPr"))
        spc = para._p.find(qn("a:pPr") + "/" + qn("a:lnSpc") + "/" + qn("a:spcPct"))
        pct = int(spc.get("val")) / 100000 if spc is not None else 1.0
        mar = int(ppr.get("marL", 0)) / PX if ppr is not None else 0
        wpx, size = 0.0, 0.0
        for r in para.runs:
            pt = r.font.size.pt if r.font.size else 12
            size = max(size, pt)
            wpx += yahei_px(r.text, pt)
        if wpx:
            total += max(1, -(-wpx // max(w - mar, 10))) * size * lib.PX_PER_PT * 1.32 * pct
    return total


def fit_card_text(slide):
    """汇报人技术页右侧的三张关键技术卡：卡内文本框统一放宽到卡片内侧（左右各留 10px）。不改字、不改行距。
    右栏整组被纵向压缩过（约 0.95 倍），卡片实际高约 161px，正好容下 5 行，多折一行就会压到卡片边框。
    原来各文本框宽 513–526 不等，有几条要点占到两行的 95% 以上；内存管理页第一张卡的第一条在原宽度下
    会折成 3 行。放宽到 532 后每条都回到两行以内，并多出一点余量。"""
    grp = next((sh for sh in slide.shapes if sh.shape_type == 6 and sh.left > px_to_emu(600)), None)
    if grp is None:
        return
    x = grp._element.find(qn("p:grpSpPr") + "/" + qn("a:xfrm"))
    sy = int(x.find(qn("a:ext")).get("cy")) / int(x.find(qn("a:chExt")).get("cy"))     # 组合的纵向缩放
    kids = list(grp.shapes)
    for c in (k for k in kids if k.name.startswith("Rounded Rectangle")):
        body = next((k for k in kids if k is not c and k.has_text_frame and k.text_frame.text.strip()
                     and c.top <= k.top + k.height / 2 <= c.top + c.height), None)
        if body is None:
            continue
        body.left, body.width = c.left + px_to_emu(10), c.width - px_to_emu(20)
        if ppt_text_height(body) > c.height / PX * sy + 2:
            lib._warn(f"关键技术卡放宽后仍排不下：{body.text_frame.text[:16]}")


def unify(prs):
    template = title_shape(prs.slides[0])          # 汇报人洞察页的标题框，作为各页标题的样板
    colleague = [s for s in prs.slides if title_shape(s).name.startswith("文本框")]
    for s in colleague:
        unify_title(s, template)
        if any(sh.has_text_frame and sh.text_frame.text.startswith("挑战") for sh in s.shapes):
            unify_tech_page(s)
        else:
            unify_gfx_insight(s)
    for s in prs.slides:
        if s not in colleague:
            fit_card_text(s)
        unify_colors(s)
        unify_fonts(s)
    page_numbers(prs)


# ---------------------------------------------------------------- 入口

def build():
    prs = Presentation(SRC)
    lib.LAYOUTS["blank"] = prs.slides[0].slide_layout       # 与原有各页相同的空白版式
    fix_insight(prs.slides[0])
    rework_inference(prs.slides[5])                         # 九页里的第 6 页：推理服务
    rework_sandbox(prs.slides[6])                           # 九页里的第 7 页：执行沙箱
    add_overview(prs)
    move_slide(prs, len(prs.slides) - 1, 2)                 # 放到两页洞察之后、七页技术之前
    unify(prs)
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

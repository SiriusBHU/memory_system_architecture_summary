"""Agent OS 四组件汇报 deck 的自绘页面库。

底版是空白演示文稿（不使用任何外部母版、标识或页脚）。页面排版沿用 ppt_templates 的 solutions 模板
（result-sim-tables-read、problem-arch-callouts、solution-arch-overview、solution-kickoff-difficulties、
roadmap-matrix），视觉风格参照外部样例的浅色系：红色结论标题、浅色底板（不用深蓝色块）、蓝色强调、
只画横线的表格、红框问题卡与红色编号。坐标一律是 1280×720 画布逻辑像素。

富文本标记（text / box / 表格单元格）：
  **加粗**      加粗，颜色不变
  !!关键数字!!  深红加粗
  @@关键结论@@  蓝色加粗
  ~~弱化~~      灰色（注释、口径）
段落：换行分段；行首 "- " 一级要点，"  - " 二级要点；行首 "# " 段落小标题（加粗）。
"""

import copy
import math
import re
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Pt

from ppt_templates.draw import ALIGN, _setup_frame, add_run, add_shape, emu_box, rgb
from ppt_templates.geometry import px_to_emu
from ppt_templates.loader import find_repo_root, load_style
from ppt_templates.render import _render_frame

ROOT = find_repo_root(Path(r"D:\projects\ppt_templates"))
S = copy.deepcopy(load_style(ROOT, "default"))

# ---------------------------------------------------------------- 浅色调色板（不用深蓝色块）
S["colors"].update({
    "primary": "#7F7F7F",          # 不再用深蓝色块
    "blue_l": "#DBEEF4", "blue_m": "#B7DEE8",
    "peach_l": "#FDEADA", "peach_m": "#FCD5B5",
    "purple_l": "#E6E0EC", "purple_m": "#B3A2C7",
    "pink_l": "#F2DCDB", "pink_m": "#E6B9B8",
    "green_l": "#EBF1DE", "green_m": "#D7E4BD",
    "beige": "#EEECE1", "beige_m": "#DDD9C4",
    "grey_l": "#F2F2F2", "grey_m": "#D9D9D9", "grey_d": "#7F7F7F", "grey_line": "#BFBFBF",
    "dark": "#404040", "red": "#C00000", "blue": "#0000FF",
})
S["text_styles"].update({
    "panel_title": {"size": 18, "bold": True, "color": "primary_text"},
    "card_head": {"size": 18, "bold": True, "color": "accent"},
    "label_big": {"size": 18, "bold": True, "color": "accent"},
    "lead_strong": {"size": 14, "bold": True, "color": "text"},
    "cover_title": {"size": 36, "bold": True, "color": "accent"},
    "cover_sub": {"size": 20, "color": "text"},
})

WARNINGS: list[str] = []
_CURRENT = {"title": ""}
LAYOUTS: dict = {}

PX_PER_PT = 4 / 3
LINE = 1.36
SIZES = {k: v["size"] for k, v in S["text_styles"].items()}

BODY_TOP = 88
BODY_BOTTOM = 688
LEFT, RIGHT, WIDTH = 32, 1248, 1216

# ---------------------------------------------------------------- 底版：空白演示文稿


def base_presentation():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(px_to_emu(1280)), Emu(px_to_emu(720))
    LAYOUTS.clear()
    LAYOUTS["blank"] = prs.slide_layouts[6]
    return prs


def _blank(prs):
    s = prs.slides.add_slide(LAYOUTS["blank"])
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    return s


def _page_number(prs, slide):
    n = len(prs.slides)
    text(slide, (1180, 696, 68, 14), str(n), style="footnote", color="grey_d", align="right", check=False)


def cover_slide(prs, title, subtitle, note):
    """封面：白底、左侧红色竖条、红色主标题、黑色副标题、灰色日期。"""
    s = _blank(prs)
    add_shape(s, S, (96, 206, 10, 236), "red")
    text(s, (132, 200, 1050, 136), title, style="cover_title", valign="middle", check=False)
    text(s, (132, 348, 1050, 36), subtitle, style="cover_sub", check=False)
    text(s, (132, 392, 1050, 24), note, style="lead", color="grey_d", check=False)
    add_shape(s, S, (96, 640, 1088, 1), "grey_line")
    return s


def section_slide(prs, num, title, desc=""):
    s = _blank(prs)
    add_shape(s, S, (96, 270, 10, 110), "red")
    text(s, (132, 262, 1050, 60), f"{num}　{title}", style="cover_title", valign="middle", check=False)
    if desc:
        text(s, (132, 330, 1050, 60), desc, style="lead", check=False)
    _page_number(prs, s)
    return s


# ---------------------------------------------------------------- 富文本

_TOKEN = re.compile(r"(\*\*.+?\*\*|!!.+?!!|@@.+?@@|~~.+?~~)")


def runs_of(md: str, color=None):
    out = []
    for part in _TOKEN.split(md):
        if not part:
            continue
        if part.startswith("**"):
            out.append((part[2:-2], color, True))
        elif part.startswith("!!"):
            out.append((part[2:-2], "accent", True))
        elif part.startswith("@@"):
            out.append((part[2:-2], "primary_text", True))
        elif part.startswith("~~"):
            out.append((part[2:-2], "grey_d", None))
        else:
            out.append((part, color, None))
    return out


def plain(md: str) -> str:
    return re.sub(r"\*\*|!!|@@|~~", "", md)


# ---------------------------------------------------------------- 文字宽高估算

def _is_cjk(ch: str) -> bool:
    return ord(ch) >= 0x2E80 or ch in "，。：；、！？（）《》“”‘’【】—…·「」"


def _char_em(ch: str) -> float:
    if _is_cjk(ch):
        return 1.0
    if ch == " ":
        return 0.32
    if ch.isdigit():
        return 0.58
    if ch.isupper():
        return 0.68
    if ch.islower():
        return 0.56
    return 0.45


def text_em(s: str) -> float:
    total, prev = 0.0, None
    for c in s:
        total += _char_em(c)
        cur = _is_cjk(c) if c != " " else None
        if prev is not None and cur is not None and cur != prev:
            total += 0.25
        if cur is not None:
            prev = cur
    return total


def lines_of(s: str, width_px: float, size_pt: float, indent_em: float = 0) -> int:
    size_px = size_pt * PX_PER_PT
    avail = max(width_px - indent_em * size_px, size_px)
    return max(1, math.ceil(text_em(s) * size_px * 1.02 / avail))


def para_height(s: str, width_px: float, size_pt: float, indent_em: float = 0) -> float:
    return lines_of(s, width_px, size_pt, indent_em) * size_pt * PX_PER_PT * LINE


def _warn(msg):
    WARNINGS.append(f"[{_CURRENT['title'][:18]}] {msg}")


# ---------------------------------------------------------------- 页面

def new_slide(prs, title, suffix=None, crumb=None, takeaway=None):
    """crumb：右上角灰色小字的位置导航，如「三、架构与关键技术 › 内存管理 › 关键技术二」；
    takeaway：标题下一行 18 号的一句话结论（有它时正文从 y=128 起）。"""
    slide = _blank(prs)
    data = {"title": title}
    if suffix:
        data["title_suffix"] = suffix
    if takeaway:
        data["takeaway"] = takeaway
    _render_frame(slide, S, data)
    _page_number(prs, slide)
    if takeaway and text_em(takeaway) * 18 * PX_PER_PT > WIDTH:
        _warn("takeaway 过长")
    if crumb:
        text(slide, (648, 10, 600, 16), crumb, style="caption", color="grey_d", align="right", check=False)
    _CURRENT["title"] = title
    width = text_em(title) * 24 * PX_PER_PT + (text_em("　" + suffix) * 18 * PX_PER_PT if suffix else 0)
    if width > WIDTH + 8:
        _warn(f"标题过长（约 {width:.0f}px）")
    return slide


def _paragraphs(md: str):
    out = []
    for raw in md.split("\n"):
        if not raw.strip():
            continue
        if raw.startswith("  - "):
            out.append(("bullet", 1, raw[4:]))
        elif raw.startswith("- "):
            out.append(("bullet", 0, raw[2:]))
        elif raw.startswith("# "):
            out.append(("head", 0, raw[2:]))
        else:
            out.append(("p", 0, raw))
    return out


def _fill_tf(tf, md, style, color, align, gap_pt, head_style=None, head_color=None):
    paras = _paragraphs(md)
    size = SIZES[style]
    em = px_to_emu(size * PX_PER_PT)
    for i, (kind, level, txt) in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = ALIGN[align]
        p_pr = p._p.get_or_add_pPr()
        if i and gap_pt:
            p_pr.append(parse_xml(f'<a:spcBef {nsdecls("a")}><a:spcPts val="{int(gap_pt * 100)}"/></a:spcBef>'))
        if kind == "bullet":
            p_pr.set("marL", str(int(em * (level + 1) * 0.95)))
            p_pr.set("indent", str(int(-em * 0.95)))
            p_pr.append(parse_xml(f'<a:buFont {nsdecls("a")} typeface="{S["fonts"]["latin"]}"/>'))
            p_pr.append(parse_xml(f'<a:buChar {nsdecls("a")} char="{"•" if level == 0 else "–"}"/>'))
        if kind == "head":
            for t, c, b in runs_of(txt, head_color or color):
                add_run(p, S, t, head_style or style, c, True)
        else:
            for t, c, b in runs_of(txt, color):
                add_run(p, S, t, style, c, b)
    return paras


def measure(md, width, style="body", gap_pt=3, head_style=None):
    size = SIZES[style]
    h = 0
    for i, (kind, level, txt) in enumerate(_paragraphs(md)):
        s = SIZES[head_style] if (kind == "head" and head_style) else size
        indent = (level + 1) * 0.95 if kind == "bullet" else 0
        h += para_height(plain(txt), width, s, indent)
        if i:
            h += gap_pt * PX_PER_PT
    return h


def text(slide, box, md, style="body", color=None, align="left", valign="top", gap_pt=3, inset=0,
         head_style=None, head_color=None, check=True, fill=None):
    x, y, w, h = box
    tb = slide.shapes.add_textbox(*emu_box(box))
    if fill:
        tb.fill.solid()
        tb.fill.fore_color.rgb = rgb(S, fill)
    _setup_frame(tb.text_frame, valign, inset)
    _fill_tf(tb.text_frame, md, style, color, align, gap_pt, head_style, head_color)
    need = measure(md, w - 2 * inset, style, gap_pt, head_style) + 2 * inset
    if check and need > h + max(6, 0.12 * h):
        _warn(f"文字可能溢出 {need:.0f}>{h:.0f}px：{plain(md)[:24]}…")
    return need


def box(slide, b, md, fill="blue_l", line=None, style="detail", color=None, align="center", valign="middle",
        kind="rect", radius=None, dash=False, shadow=False, inset=4, gap_pt=2, line_width=0.75, check=True):
    """带文字的形状（架构图里的模块框、标签）。"""
    shape = add_shape(slide, S, b, fill, line=line, kind=kind, radius=radius, dash=dash, shadow=shadow,
                      line_width=line_width)
    tf = shape.text_frame
    _setup_frame(tf, valign, inset)
    _fill_tf(tf, md, style, color, align, gap_pt)
    need = measure(md, b[2] - 2 * inset, style, gap_pt) + 2 * inset
    if check and need > b[3] + max(6, 0.12 * b[3]):
        _warn(f"框内文字可能溢出 {need:.0f}>{b[3]:.0f}px：{plain(md)[:20]}…")
    return shape


def outline(slide, b, line="grey_line", width=1.0, dash=False, kind="rect", radius=None):
    """只有描边、没有填充的框。"""
    shape = add_shape(slide, S, b, "bg", line=line, kind=kind, radius=radius, dash=dash, line_width=width)
    shape.fill.background()
    return shape


def rect(slide, b, fill, line=None, kind="rect", radius=None, line_width=0.75, dash=False):
    return add_shape(slide, S, b, fill, line=line, kind=kind, radius=radius, line_width=line_width, dash=dash)


def arrow(slide, p1, p2, color="dark", width=1.0, head=True, dash=False, both=False):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, *(Emu(px_to_emu(v)) for v in (*p1, *p2)))
    conn._element.find(qn("p:style")).find(qn("a:effectRef")).set("idx", "0")
    conn.line.color.rgb = rgb(S, color)
    conn.line.width = Pt(width)
    ln = conn.line._get_or_add_ln()
    if dash:
        ln.append(parse_xml(f'<a:prstDash {nsdecls("a")} val="dash"/>'))
    if both:
        ln.append(parse_xml(f'<a:headEnd {nsdecls("a")} type="triangle" w="med" len="med"/>'))
    if head:
        ln.append(parse_xml(f'<a:tailEnd {nsdecls("a")} type="triangle" w="med" len="med"/>'))
    return conn


def poly(slide, pts, head=False, **kw):
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        arrow(slide, a, b, head=head and i == len(pts) - 2, **kw)


def block_arrow(slide, b, fill="grey_m", direction="right"):
    shp = {"right": MSO_SHAPE.RIGHT_ARROW, "down": MSO_SHAPE.DOWN_ARROW, "left": MSO_SHAPE.LEFT_ARROW,
           "up": MSO_SHAPE.UP_ARROW}[direction]
    s = slide.shapes.add_shape(shp, *emu_box(b))
    s._element.find(qn("p:style")).find(qn("a:effectRef")).set("idx", "0")
    s.shadow.inherit = False
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(S, fill)
    s.line.fill.background()
    return s


def badge(slide, cx, cy, n, d=22, fill="red"):
    """红色实心圆编号（架构图上标问题 / 关键技术的位置）。"""
    return box(slide, (cx - d / 2, cy - d / 2, d, d), f"**{n}**", fill=fill, kind="oval", style="body",
               color="on_primary", inset=0, check=False)


# ---------------------------------------------------------------- 模板4 组件

def problem_band(slide, items, y=BODY_TOP, h=144, label="核心\n问题", x=LEFT, w=WIDTH, body_style="body"):
    """「核心问题」虚线框：items = [(红色问题名, 黑色加粗小标题, 正文)]；正文可用 !!红色!! 标关键数字。"""
    outline(slide, (x, y, w, h), line="grey_d", width=2.0, dash=True)
    text(slide, (x + 12, y, 76, h), label, style="label_big", align="center", valign="middle", check=False)
    n = len(items)
    gx0, gap = x + 100, 22
    cw = (x + w - 14 - gx0 - gap * (n - 1)) / n
    for i, (head, sub, body) in enumerate(items):
        cx = gx0 + i * (cw + gap)
        text(slide, (cx, y + 6, cw, 30), head, style="card_head", align="center", check=False)
        outline(slide, (cx, y + 38, cw, h - 46), line="grey_line", width=1.0)
        inner = cw - 20
        sub_h = 22 if sub else 0
        if sub:
            text(slide, (cx + 10, y + 42, inner, 22), f"**{sub}**", style="lead_strong", align="center")
        text(slide, (cx + 10, y + 44 + sub_h, inner, h - 56 - sub_h), body, style=body_style, align="center",
             valign="middle" if not sub else "top")


def kpi_band(slide, items, y=592, h=82, label="立项\n目标", x=LEFT, w=WIDTH):
    """底部「立项目标」指标带：items = [(大数字, 指标名, 依据)]，与顶部「核心问题」首尾呼应。"""
    outline(slide, (x, y, w, h), line="grey_d", width=2.0, dash=True)
    text(slide, (x + 12, y, 76, h), label, style="label_big", align="center", valign="middle", check=False)
    n = len(items)
    gx0, gap = x + 100, 10
    cw = (x + w - 10 - gx0 - gap * (n - 1)) / n
    for i, (val, name, basis) in enumerate(items):
        cx = gx0 + i * (cw + gap)
        rect(slide, (cx, y + 6, cw, h - 12), "grey_l")
        text(slide, (cx + 4, y + 6, cw - 8, 34), val, style="kpi", color="accent", align="center", valign="middle",
             check=False)
        text(slide, (cx + 4, y + 41, cw - 8, 17), f"**{name}**", style="detail", align="center")
        text(slide, (cx + 4, y + 58, cw - 8, 16), basis, style="caption", color="grey_d", align="center")


def panel(slide, b, title, title_style="panel_title", line="grey_line"):
    """细灰框面板，蓝色标题压在上边框中间。返回内部可用区域 (x, y, w, h)。"""
    x, y, w, h = b
    outline(slide, b, line=line, width=1.0)
    tw = text_em(plain(title)) * SIZES[title_style] * PX_PER_PT + 36
    text(slide, (x + (w - tw) / 2, y - 17, tw, 32), title, style=title_style, align="center", valign="middle",
         fill="bg", check=False)
    return (x + 12, y + 22, w - 24, h - 30)


def callout(slide, b, num, md, style="emphasis"):
    """红框问题卡：圈码 + 红色加粗问题。"""
    outline(slide, b, line="red", width=2.0)
    shape = slide.shapes.add_textbox(*emu_box((b[0] + 8, b[1] + 4, b[2] - 16, b[3] - 8)))
    _setup_frame(shape.text_frame, "middle", 0)
    _fill_tf(shape.text_frame, f"{num} {md}" if num else md, style, "accent", "left", 0)
    need = measure(f"{num} {md}", b[2] - 16, style) + 8
    if need > b[3] + 6:
        _warn(f"问题卡溢出 {need:.0f}>{b[3]:.0f}：{plain(md)[:16]}")


def scan_card(slide, b, name, src, body, legacy=None, body_style="body"):
    """业界技术扫描卡（浅灰圆角）：名称、（年份 来源）、原理与效果、红色遗留问题。"""
    x, y, w, h = b
    rect(slide, b, "grey_l", kind="rounded", radius=12)
    text(slide, (x + 10, y + 6, w - 20, 22), f"**{name}**", style="emphasis", align="center")
    text(slide, (x + 10, y + 28, w - 20, 18), f"@@（{src}）@@", style="body", align="center")
    lmd = f"!!遗留问题：{legacy}!!" if legacy else ""
    lh = measure(lmd, w - 24, "detail") if legacy else 0
    bh = h - 56 - (lh + 2 if legacy else 0)
    text(slide, (x + 12, y + 50, w - 24, bh), body, style=body_style)
    if legacy:
        text(slide, (x + 12, y + h - 6 - lh, w - 24, lh), lmd, style="detail")


def header_bar(slide, b, title):
    """浅蓝渐变感的栏目标题条（模板4「业务场景与挑战」一类）。"""
    rect(slide, b, "blue_l")
    text(slide, b, f"**{title}**", style="heading", align="center", valign="middle", check=False)


# ---------------------------------------------------------------- 表格（模板4：白底、只画横线）

NO_STYLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"


def _border(cell, side, width_pt, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tag = {"L": "a:lnL", "R": "a:lnR", "T": "a:lnT", "B": "a:lnB"}[side]
    old = tcPr.find(qn(tag))
    if old is not None:
        tcPr.remove(old)
    if width_pt:
        xml = (f'<{tag} {nsdecls("a")} w="{int(width_pt * 12700)}" cap="flat" cmpd="sng" algn="ctr">'
               f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill><a:prstDash val="solid"/></{tag}>')
    else:
        xml = f'<{tag} {nsdecls("a")} w="0"><a:noFill/></{tag}>'
    el = parse_xml(xml)
    order = ["a:lnL", "a:lnR", "a:lnT", "a:lnB"]
    idx = order.index(tag)
    # 插在 fill 之前，按 lnL, lnR, lnT, lnB 的顺序
    pos = 0
    for child in tcPr:
        if child.tag in [qn(t) for t in order[:idx]]:
            pos += 1
    tcPr.insert(pos, el)


def _cell(cell, md, style, fill, color=None, align="center", bold_all=False, pad=(5, 2)):
    if fill:
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(S, fill)
    else:
        cell.fill.background()
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_left = cell.margin_right = Emu(px_to_emu(pad[0]))
    cell.margin_top = cell.margin_bottom = Emu(px_to_emu(pad[1]))
    tf = cell.text_frame
    tf.word_wrap = True
    paras = _paragraphs(md) or [("p", 0, "")]
    size = SIZES[style]
    em = px_to_emu(size * PX_PER_PT)
    for i, (kind, level, txt) in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = ALIGN[align]
        if kind == "bullet":
            p_pr = p._p.get_or_add_pPr()
            p_pr.set("marL", str(int(em * 0.9)))
            p_pr.set("indent", str(int(-em * 0.9)))
            p_pr.append(parse_xml(f'<a:buFont {nsdecls("a")} typeface="{S["fonts"]["latin"]}"/>'))
            p_pr.append(parse_xml(f'<a:buChar {nsdecls("a")} char="•"/>'))
        for t, c, b in runs_of(txt, color):
            add_run(p, S, t, style, c, True if bold_all else b)


def table_height(w, columns, rows, widths=None, style="detail", header_style=None, pad=(5, 2)):
    """与 table() 相同口径的自然高度估算（不画），用于排版前预留空间。"""
    n = len(columns)
    ratios = widths or [1] * n
    cw = [w * r / sum(ratios) for r in ratios]
    hs = header_style or ("body_strong" if style == "body" else style)

    def cell_h(md, wpx, s):
        tot = 0
        for kind, level, txt in _paragraphs(md) or [("p", 0, "")]:
            tot += para_height(plain(txt), wpx - 2 * pad[0], s, 0.9 if kind == "bullet" else 0)
        return tot + 2 * pad[1] + 2

    total = max(cell_h(c, cw[j], SIZES[hs]) for j, c in enumerate(columns))
    for r in rows:
        total += max(cell_h(c, cw[j], SIZES[style]) for j, c in enumerate(r))
    return total


def table(slide, b, columns, rows, widths=None, style="detail", header_style=None, align=None, first_bold=True,
          pad=(5, 2), hot_col=None, fills=None, check=True, fit=True):
    """模板4 风格表格：白底；表头上粗线、下细线；行间细灰线；末行下粗线。
    align：整表或逐列（"left" / "center"）；hot_col：这一列的正文用浅橙底（本方案 / 目标列）；
    fills：{(行, 列): 颜色 token} 单格底色（行号从 1 起，0 为表头）。返回估算总高度。"""
    x, y, w, h = b
    n = len(columns)
    for i, r in enumerate(rows):
        assert len(r) == n, f"{_CURRENT['title']} 表格第 {i + 1} 行列数 {len(r)}≠{n}"
    ratios = widths or [1] * n
    cw = [w * r / sum(ratios) for r in ratios]
    shape = slide.shapes.add_table(len(rows) + 1, n, *emu_box(b))
    t = shape.table
    t.first_row = t.horz_banding = False
    t._tbl.tblPr.find(qn("a:tableStyleId")).text = NO_STYLE
    for col, wpx in zip(t.columns, cw):
        col.width = Emu(px_to_emu(wpx))
    hs = header_style or ("body_strong" if style == "body" else style)
    size, hsize = SIZES[style], SIZES[hs]

    def cell_h(md, wpx, s):
        tot = 0
        for kind, level, txt in _paragraphs(md) or [("p", 0, "")]:
            tot += para_height(plain(txt), wpx - 2 * pad[0], s, 0.9 if kind == "bullet" else 0)
        return tot + 2 * pad[1] + 2

    heights = [max(cell_h(c, cw[j], hsize) for j, c in enumerate(columns))]
    for r in rows:
        heights.append(max(cell_h(c, cw[j], size) for j, c in enumerate(r)))
    total = sum(heights)
    scale = max(1.0, h / total) if fit else 1.0
    for i, row in enumerate(t.rows):
        row.height = Emu(px_to_emu(heights[i] * scale))

    def a_of(j):
        if isinstance(align, (list, tuple)):
            return align[j]
        return align or ("left" if j == 0 and n > 2 else "center")

    fills = fills or {}
    last = len(rows)
    for j, name in enumerate(columns):
        c = t.cell(0, j)
        _cell(c, name, hs, fills.get((0, j)), align="center", bold_all=True, pad=pad)
        _border(c, "L", 0, None)
        _border(c, "R", 0, None)
        _border(c, "T", 1.5, "000000")
        _border(c, "B", 1.0, "000000")
    for i, r in enumerate(rows, 1):
        for j, md in enumerate(r):
            c = t.cell(i, j)
            f = fills.get((i, j)) or ("peach_l" if j == hot_col else None)
            _cell(c, md, style, f, align=a_of(j), bold_all=(first_bold and j == 0), pad=pad)
            _border(c, "L", 0, None)
            _border(c, "R", 0, None)
            _border(c, "T", 1.0 if i == 1 else 0.5, "000000" if i == 1 else "A6A6A6")
            _border(c, "B", 1.5 if i == last else 0.5, "000000" if i == last else "A6A6A6")
    if check and total > h + 4:
        _warn(f"表格可能溢出 {total:.0f}>{h:.0f}px（{plain(columns[0])}…）")
    return total


def footnote(slide, md, y=678, x=LEFT, w=900, h=14):
    text(slide, (x, y, w, h), md, style="footnote", color="grey_d", check=False)


def difficulties(slide, b, items, style="body", gap_pt=2, item_gap=8, head_style="lead_strong"):
    """技术难点：items = [(编号, 难点名, 难在哪, 怎么做)]，自上而下排；返回结束的 y。"""
    x, y, w, h = b
    for num, name, hard, how in items:
        md = f"# {num} {name}\n- **难在哪**：{hard}\n- **怎么做**：{how}"
        need = measure(md, w, style, gap_pt, head_style=head_style)
        text(slide, (x, y, w, need + 2), md, style=style, gap_pt=gap_pt, head_style=head_style,
             head_color="accent")
        y += need + item_gap
    if y > b[1] + h + 6:
        _warn(f"技术难点溢出 {y - b[1]:.0f}>{h:.0f}px")
    return y


# ---------------------------------------------------------------- solutions 模板版式的组件（只换风格，不改排版）

ZH = "一二三四五六"


def round_card(slide, b, fill="grey_l", line="grey_line", radius=14):
    return rect(slide, b, fill, line=line, kind="rounded", radius=radius, line_width=0.75)


def head_card(slide, b, label, md, label_w=56):
    """arch-overview 顶部说明卡：左侧红色两字标签（如「核心\\n挑战」）+ 右侧逐行要点。"""
    x, y, w, h = b
    lib_card = outline(slide, b, line="grey_line", width=1.0)
    text(slide, (x + 10, y, label_w, h), label, style="label_big", align="center", valign="middle", check=False)
    text(slide, (x + label_w + 18, y + 6, w - label_w - 28, h - 12), md, style="body", valign="middle", gap_pt=3)
    return lib_card


def layer_row(slide, x, y, w, h, name, modules, name_w=64, gap=6, style="detail"):
    """分区架构的一层：左侧层名块（浅蓝底黑字）+ 等宽模块；modules = [(文字, 是否新增)]。
    新增 / 改动模块：浅橙底、红色描边、红色文字。"""
    box(slide, (x, y, name_w, h), "\n".join(f"**{ln}**" for ln in name.split("\n")), fill="blue_m", style="detail")
    n = len(modules)
    mw = (w - name_w - gap * n) / n
    out = []
    for i, (t, new) in enumerate(modules):
        b = (x + name_w + gap + i * (mw + gap), y, mw, h)
        if new:
            box(slide, b, t, fill="peach_l", line="red", line_width=1.25, color="accent", style=style)
        else:
            box(slide, b, t, fill="bg", line="grey_d", line_width=0.75, style=style)
        out.append(b)
    return out


def canvas_panel(slide, b, num, title):
    """立项页架构画布的分区：浅灰圆角底 + 红色圆形编号 + 蓝色加粗分区名。返回内部区域。"""
    x, y, w, h = b
    rect(slide, b, "grey_l", kind="rounded", radius=10)
    badge(slide, x + 18, y + 17, num, d=22)
    text(slide, (x + 34, y + 5, w - 40, 24), f"**{title}**", style="lead", color="primary_text", valign="middle",
         check=False)
    return (x + 8, y + 36, w - 16, h - 44)


def difficulty_cards(slide, b, items, gap=14, style="body"):
    """立项页「技术难题」卡（浅灰圆角细描边）：items = [(名称, 要点 md)]，卡高按内容分配。"""
    x, y, w, h = b
    needs = [measure(md, w - 26, style, 2) + 42 for _, md in items]
    extra = h - gap * (len(items) - 1) - sum(needs)
    if extra < 0:
        _warn(f"难题卡溢出 {-extra:.0f}px")
    add = max(0.0, extra) / len(items)
    for i, (name, md) in enumerate(items):
        ch = needs[i] + add
        round_card(slide, (x, y, w, ch))
        text(slide, (x + 13, y + 9, w - 26, 22), f"难题{ZH[i]}：{name}", style="body_strong", color="accent")
        text(slide, (x + 13, y + 35, w - 26, ch - 40), md, style=style, gap_pt=2)
        y += ch + gap


def milestones(slide, b, items):
    """立项页「交付节奏」：红色时间轴 + 三角节点，上方交付件、下方日期。items = [(交付件, 日期)]。"""
    x, y, w, h = b
    n = len(items)
    gap = 8
    cw = (w - gap * (n - 1)) / n
    add_shape(slide, S, (x + 2, y + 70, w - 4, 4), "red")
    for i, (deliv, date) in enumerate(items):
        cx = x + i * (cw + gap) + cw / 2
        box(slide, (cx - 82, y + 6, 164, 54), f"**{deliv}**", fill="grey_l", line="text", style="body")
        add_shape(slide, S, (cx - 12, y + 60, 24, 19), "red", kind="triangle")
        text(slide, (cx - 70, y + 82, 140, 22), f"@@{date}@@", style="body", align="center", check=False)


def bullets(slide, b, items, style="body", gap_pt=4):
    """items = [(名称, 说明)] → 「• **名称**：说明」。"""
    md = "\n".join(f"- **{k}**：{v}" if k else f"- {v}" for k, v in items)
    return text(slide, b, md, style=style, gap_pt=gap_pt)

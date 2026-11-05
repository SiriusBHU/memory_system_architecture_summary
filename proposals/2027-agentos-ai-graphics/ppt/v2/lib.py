"""v2 立项 deck 的自绘页面库：沿用 ppt_templates 的风格 token 与绘图原语（微软雅黑、颜色 token、白底阴影卡片），
在模板之外画高信息密度的页面。坐标一律是 1280×720 画布逻辑像素。

富文本标记（用于 text / table 单元格 / box）：
  **加粗**            加粗，颜色不变
  !!关键数字!!        深红加粗（accent）
  @@关键短语@@        蓝色加粗（primary_text）
段落：用换行分段；行首 "- " 为一级要点，"  - " 为二级要点；行首 "# " 为段落小标题（加粗）。
"""

import math
import re
from pathlib import Path

from pptx.enum.shapes import MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Pt

from ppt_templates.draw import ALIGN, _setup_frame, add_run, add_shape, emu_box, rgb
from ppt_templates.geometry import px_to_emu
from ppt_templates.loader import find_repo_root, load_style
from ppt_templates.render import BLANK_LAYOUT, _render_frame

ROOT = find_repo_root(Path(r"D:\projects\ppt_templates"))
S = load_style(ROOT, "default")
WARNINGS: list[str] = []
_CURRENT = {"title": ""}

PX_PER_PT = 4 / 3
LINE = 1.36          # 微软雅黑行高约为字号的 1.32–1.36 倍
SIZES = {k: v["size"] for k, v in S["text_styles"].items()}

# ---------------------------------------------------------------- 富文本解析

_TOKEN = re.compile(r"(\*\*.+?\*\*|!!.+?!!|@@.+?@@)")


def runs_of(md: str, color=None):
    """一段文字 → [(text, color, bold)]。"""
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
        else:
            out.append((part, color, None))
    return out


def plain(md: str) -> str:
    return re.sub(r"\*\*|!!|@@", "", md)


# ---------------------------------------------------------------- 估算文字高度（防溢出）

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
    """估算宽度（em）。渲染时中文与西文之间会自动加间距，按每个边界 0.25em 计。"""
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
    WARNINGS.append(f"[{_CURRENT['title']}] {msg}")


# ---------------------------------------------------------------- 页面与基本元素

def new_slide(prs, title, suffix=None, takeaway=None):
    slide = prs.slides.add_slide(prs.slide_layouts[BLANK_LAYOUT])
    data = {"title": title}
    if suffix:
        data["title_suffix"] = suffix
    if takeaway:
        data["takeaway"] = takeaway
    _render_frame(slide, S, data)
    _CURRENT["title"] = title
    full = title + ("　" + suffix if suffix else "")
    if text_em(full) * 24 * PX_PER_PT > 1216:
        _warn("标题过长")
    if takeaway and text_em(takeaway) * 18 * PX_PER_PT > 1216:
        _warn("takeaway 过长")
    return slide


BODY_TOP = 128      # 有 takeaway 时正文区顶边
BODY_TOP_COMPACT = 88
BODY_BOTTOM = 688   # 正文区下边缘
LEFT, RIGHT = 32, 1248


def card(slide, box, fill="bg", shadow=True, line=None, dash=False, kind="rect", radius=None, line_width=0.75):
    return add_shape(slide, S, box, fill, line=line, dash=dash, kind=kind, radius=radius, shadow=shadow,
                     line_width=line_width)


def _paragraphs(md: str):
    """→ [(kind, level, text)]，kind: p / bullet / head。"""
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
         head_style=None, head_color=None, check=True):
    x, y, w, h = box
    tb = slide.shapes.add_textbox(*emu_box(box))
    _setup_frame(tb.text_frame, valign, inset)
    _fill_tf(tb.text_frame, md, style, color, align, gap_pt, head_style, head_color)
    need = measure(md, w - 2 * inset, style, gap_pt, head_style) + 2 * inset
    if check and need > h + max(6, 0.12 * h):
        _warn(f"文字可能溢出 {need:.0f}>{h:.0f}px：{plain(md)[:24]}…")
    return need


def box(slide, b, md, fill="surface", line=None, style="detail", color=None, align="center", valign="middle",
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


def arrow(slide, p1, p2, color="muted", width=1.25, head=True, dash=False, both=False):
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


def poly_arrow(slide, pts, **kw):
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        arrow(slide, a, b, head=kw.get("head", True) and i == len(pts) - 2,
              **{k: v for k, v in kw.items() if k != "head"})


# ---------------------------------------------------------------- 卡片：标题 + 正文

def titled_card(slide, b, title, md, title_style="emphasis", title_color="primary_text", style="body",
                pad=12, gap_pt=3, fill="bg", shadow=True, head_style=None, title_h=None):
    x, y, w, h = b
    card(slide, b, fill=fill, shadow=shadow)
    th = title_h or para_height(plain(title), w - 2 * pad, SIZES[title_style])
    text(slide, (x + pad, y + pad - 2, w - 2 * pad, th), title, style=title_style, color=title_color)
    text(slide, (x + pad, y + pad + th + 4, w - 2 * pad, h - th - 2 * pad - 4), md, style=style, gap_pt=gap_pt,
         head_style=head_style)


def num_badge(slide, x, y, n, d=20, fill="accent"):
    box(slide, (x, y, d, d), str(n), fill=fill, kind="oval", style="caption", color="on_primary", inset=0)


# ---------------------------------------------------------------- 表格

NO_STYLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"


def _cell(cell, md, style, fill, color=None, align="left", bold_all=False, pad=(6, 3)):
    cell.fill.solid()
    cell.fill.fore_color.rgb = rgb(S, fill)
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


def table(slide, b, columns, rows, widths=None, style="detail", header_style=None, header_fill="primary",
          zebra=True, first_bold=True, align=None, pad=(6, 3), row_h=None, hot_col=None, check=True):
    """原生表格。rows 里每格是富文本字符串。返回估算的总高度。"""
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
        for i, (kind, level, txt) in enumerate(_paragraphs(md) or [("p", 0, "")]):
            tot += para_height(plain(txt), wpx - 2 * pad[0], s, 0.9 if kind == "bullet" else 0)
        return tot + 2 * pad[1] + 2

    heights = [max(cell_h(c, cw[j], hsize) for j, c in enumerate(columns))]
    for r in rows:
        heights.append(max(cell_h(c, cw[j], size) for j, c in enumerate(r)))
    total = sum(heights)
    # 余量按比例分给各行，让表格填满 box
    scale = max(1.0, h / total) if not row_h else 1.0
    for i, row in enumerate(t.rows):
        row.height = Emu(px_to_emu(row_h if row_h else heights[i] * scale))
    for j, name in enumerate(columns):
        _cell(t.cell(0, j), name, hs, "highlight_strong" if j == hot_col else header_fill, color="on_primary",
              align="center" if (align == "center" or j) else "left", bold_all=True, pad=pad)
    for i, r in enumerate(rows, 1):
        fill = "surface_light" if (zebra and i % 2 == 0) else "bg"
        for j, md in enumerate(r):
            a = (align[j] if isinstance(align, (list, tuple)) else align) or "left"
            if j == hot_col:
                _cell(t.cell(i, j), md, style, "highlight", align=a, pad=pad)
            else:
                _cell(t.cell(i, j), md, style, fill, align=a, bold_all=(first_bold and j == 0), pad=pad)
    if check and total > h + 4:
        _warn(f"表格可能溢出 {total:.0f}>{h:.0f}px（{plain(columns[0])}…）")
    return total


def kpi(slide, b, value, label, note=None):
    """指标卡：大数字（kpi 样式）+ 标签 + 一行说明。"""
    x, y, w, h = b
    card(slide, b)
    text(slide, (x + 10, y + 8, w - 20, 34), value, style="kpi", color="accent", align="center")
    text(slide, (x + 10, y + 44, w - 20, 20), f"**{label}**", style="body", align="center")
    if note:
        text(slide, (x + 10, y + 66, w - 20, h - 72), note, style="caption", align="center")


def timeline(slide, x, y, w, events, label_w=None, text_h=64, style="caption"):
    """水平时间轴：events = [(时间, 说明)]，节点等距分布，说明写在轴下方。"""
    n = len(events)
    step = w / n
    arrow(slide, (x, y), (x + w, y), color="muted", width=1.5)
    for i, (when, md) in enumerate(events):
        cx = x + step * i + step / 2
        box(slide, (cx - 6, y - 6, 12, 12), "", fill="accent", kind="oval", check=False)
        text(slide, (cx - step / 2 + 4, y - 26, step - 8, 18), f"**{when}**", style="detail", align="center",
             color="accent")
        text(slide, (cx - step / 2 + 4, y + 10, step - 8, text_h), md, style=style, align="center")


def footnote(slide, md, y=672, x=LEFT, w=1216, h=16):
    """正文区底部的注释（来源、口径说明），8 号字；调用方的正文要在 y 之上结束。"""
    text(slide, (x, y, w, h), md, style="footnote")


def points(slide, x, y, w, h, items, style="body", badge=True, gap=None):
    """等分高度排列的编号要点：items = [(名称, 说明)]，每项占 h/len 的高度。"""
    n = len(items)
    slot = h / n
    for i, (t, d) in enumerate(items, 1):
        yy = y + (i - 1) * slot
        if badge:
            num_badge(slide, x, yy + 1, i)
            text(slide, (x + 28, yy, w - 28, slot - 4), f"**{t}**：{d}" if t else d, style=style)
        else:
            text(slide, (x, yy, w, slot - 4), f"**{t}**：{d}" if t else d, style=style)

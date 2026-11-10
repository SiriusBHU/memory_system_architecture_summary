# -*- coding: utf-8 -*-
"""v3.3 评审 PPT 版式工具。全部原生可编辑元素，16:9。

富文本约定：段落 = str | run | list[run]；run = str 或 dict(t, s, c, b, i, f, sub, sup)。
"""
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.oxml.ns import qn

DARK = RGBColor(0x0F, 0x1E, 0x2E); INK = RGBColor(0x1E, 0x29, 0x3B)
MUTE = RGBColor(0x64, 0x74, 0x8B); SLATE = RGBColor(0x94, 0xA3, 0xB8)
SLATEF = RGBColor(0xF1, 0xF5, 0xF9); WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x0D, 0x94, 0x88); TEALDK = RGBColor(0x0B, 0x6E, 0x66)
TEALLT = RGBColor(0x99, 0xE6, 0xDA); BAND = RGBColor(0xE6, 0xFB, 0xF8)
RED = RGBColor(0xD8, 0x4B, 0x3C); REDLT = RGBColor(0xFD, 0xEC, 0xEA)
AMBER = RGBColor(0xD9, 0x77, 0x06); BLUE = RGBColor(0x25, 0x63, 0xEB)
YAHEI = "Microsoft YaHei"; MONO = "Consolas"

HALF_LIFE = {"不变量": TEALDK, "慢变量": BLUE, "快变量": AMBER, "未验证": RED}
TAGS = {"v3.3 修订": TEAL, "v3.3 新增": BLUE, "v3.3 翻转": RED}
SHOW_TAGS = False          # v3.4：正文页不显示版本角标（修订对照集中在附录 D）

SW, SH = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.45)
CONTENT_TOP = Inches(1.05)


def new_deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = SW, SH
    return prs


def _apply_font(run, t, s=12, c=INK, b=False, i=False, f=YAHEI, sub=False, sup=False):
    run.text = t
    font = run.font
    font.size = Pt(s); font.bold = b; font.italic = i; font.name = f
    font.color.rgb = c
    rPr = run._r.get_or_add_rPr()
    for tag, face in (("a:latin", f), ("a:ea", YAHEI), ("a:cs", f)):
        e = rPr.find(qn(tag))
        if e is None:
            e = rPr.makeelement(qn(tag), {}); rPr.append(e)
        e.set("typeface", face)
    if sub:
        rPr.set("baseline", "-25000")
    if sup:
        rPr.set("baseline", "30000")


def rich(tf, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, s=12, c=INK,
         space_after=3, line_spacing=None):
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    for idx, para in enumerate(paras):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after); p.space_before = Pt(0)
        if line_spacing:
            p.line_spacing = line_spacing
        if isinstance(para, (str, dict)):
            para = [para]
        for r in para:
            spec = {"t": r} if isinstance(r, str) else dict(r)
            spec.setdefault("s", s); spec.setdefault("c", c)
            _apply_font(p.add_run(), **spec)


def text(slide, x, y, w, h, paras, **kw):
    tb = slide.shapes.add_textbox(x, y, w, h)
    rich(tb.text_frame, paras, **kw)
    return tb


_SCRIPT = re.compile(r"_\{([^}]*)\}|_([A-Za-z0-9]+)|\^\{([^}]*)\}|\^([A-Za-z0-9*]+)")


def fx(src, s=11, c=INK, f=MONO, b=False):
    """'B_{ufs}/F_{eff} ≥ 1/(4·L_c)' → 带上下标的 run 列表。"""
    runs, pos = [], 0
    base = {"s": s, "c": c, "f": f, "b": b}
    for m in _SCRIPT.finditer(src):
        if m.start() > pos:
            runs.append({**base, "t": src[pos:m.start()]})
        sub = m.group(1) if m.group(1) is not None else m.group(2)
        sup = m.group(3) if m.group(3) is not None else m.group(4)
        if sub is not None:
            runs.append({**base, "t": sub, "sub": True})
        else:
            runs.append({**base, "t": sup, "sup": True})
        pos = m.end()
    if pos < len(src):
        runs.append({**base, "t": src[pos:]})
    return runs


def hl(label, s=10):
    """行内半衰期标记。"""
    return {"t": f"〔{label}〕", "s": s, "c": HALF_LIFE[label], "b": True}


def rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, line_w=0.75):
    sp = slide.shapes.add_shape(shape, x, y, w, h)
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid(); sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line; sp.line.width = Pt(line_w)
    sp.shadow.inherit = False
    style = sp._element.find(qn("p:style"))       # 去掉主题样式（阴影、默认字色）
    if style is not None:
        sp._element.remove(style)
    return sp


def box(slide, x, y, w, h, paras, fill=SLATEF, line=SLATE, shape=MSO_SHAPE.RECTANGLE,
        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, s=11, c=INK):
    sp = rect(slide, x, y, w, h, fill, line, shape)
    rich(sp.text_frame, paras, align=align, anchor=anchor, s=s, c=c)
    return sp


def arrow(slide, x1, y1, x2, y2, color=MUTE, w=1.25, head=True):
    cn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    cn.line.color.rgb = color; cn.line.width = Pt(w)
    if head:
        ln = cn.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return cn


def _label_w(label, s=9):
    inch = sum(0.0139 * s if ord(ch) > 0x2E80 else 0.0075 * s for ch in label) + 0.22
    return Inches(inch)


def badge(slide, x, y, label, color, w=None, s=9):
    w = w or _label_w(label, s)
    sp = rect(slide, x, y, w, Inches(0.26), fill=color, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rich(sp.text_frame, [[{"t": label, "s": s, "c": WHITE, "b": True}]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    return sp


def add_slide(prs, section, title, half_life=(), tag=None, source=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill; bg.solid(); bg.fore_color.rgb = WHITE
    text(slide, MARGIN, Inches(0.25), Inches(9.8), Inches(0.6),
         [[{"t": section + "  ", "s": 20, "c": TEAL, "b": True},
           {"t": title, "s": 20, "c": INK, "b": True}]], anchor=MSO_ANCHOR.MIDDLE)
    rect(slide, MARGIN, Inches(0.88), SW - 2 * MARGIN, Inches(0.03), fill=TEAL)
    labels = ([(tag, TAGS[tag])] if tag and SHOW_TAGS else []) + [(h, HALF_LIFE[h]) for h in half_life]
    xr = SW - MARGIN
    for label, color in labels:
        w = _label_w(label); xr -= w
        badge(slide, xr, Inches(0.42), label, color, w)
        xr -= Inches(0.08)
    if source:
        text(slide, MARGIN, Inches(7.08), Inches(11.4), Inches(0.3),
             [[{"t": "出处：" + source, "s": 8.5, "c": MUTE}]])
    text(slide, SW - MARGIN - Inches(0.8), Inches(7.08), Inches(0.8), Inches(0.3),
         [[{"t": str(len(prs.slides)), "s": 9, "c": MUTE}]], align=PP_ALIGN.RIGHT)
    return slide


def table(slide, x, y, w, h, header, rows, col_w=None, s=10, head_s=None,
          hl_rows=(), hl_color=REDLT, first_col_bold=False, right_cols=(), center_cols=()):
    nr, nc = len(rows) + 1, len(header)
    gf = slide.shapes.add_table(nr, nc, x, y, w, h)
    tbl = gf.table
    if col_w:
        tot = sum(col_w)
        for j, cw in enumerate(col_w):
            tbl.columns[j].width = int(w * cw / tot)
    for r in range(nr):
        tbl.rows[r].height = int(h / nr)

    def put(cell, content, bold, color, fill, size, align):
        cell.fill.solid(); cell.fill.fore_color.rgb = fill
        cell.margin_left = cell.margin_right = Inches(0.05)
        cell.margin_top = cell.margin_bottom = Inches(0.025)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        paras = content if isinstance(content, list) else [[{"t": str(content), "b": bold}]]
        rich(cell.text_frame, paras, align=align, anchor=MSO_ANCHOR.MIDDLE, s=size, c=color,
             space_after=0)

    for j, hd in enumerate(header):
        put(tbl.cell(0, j), hd, True, WHITE, DARK, head_s or s, PP_ALIGN.CENTER)
    for i, row in enumerate(rows, start=1):
        fill = hl_color if (i - 1) in hl_rows else (SLATEF if i % 2 == 0 else WHITE)
        for j, val in enumerate(row):
            al = PP_ALIGN.RIGHT if j in right_cols else PP_ALIGN.CENTER if j in center_cols else PP_ALIGN.LEFT
            put(tbl.cell(i, j), val, first_col_bold and j == 0, INK, fill, s, al)
    return gf


def formula_box(slide, x, y, w, h, title, lines, s=11):
    rect(slide, x, y, w, h, fill=BAND)
    rect(slide, x, y, Inches(0.06), h, fill=TEAL)
    paras = [[{"t": title, "s": s, "c": TEALDK, "b": True}]]
    for ln in lines:
        paras.append(ln if isinstance(ln, list) else [{"t": ln, "f": MONO, "s": s}])
    return text(slide, x + Inches(0.15), y + Inches(0.06), w - Inches(0.22), h - Inches(0.1),
                paras, s=s)


def _style_chart(ch, n_series, s, legend):
    ch.has_title = False
    ch.font.size = Pt(s); ch.font.name = YAHEI
    ch.has_legend = legend and n_series > 1
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(s)


def _axis_title(axis, title, s):
    axis.has_title = True
    axis.axis_title.text_frame.text = title
    axis.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(s)


def chart(slide, x, y, w, h, kind, categories, series, colors=None, x_title=None,
          y_title=None, legend=True, s=10, number_format=None, labels=None, gap=None):
    """kind：line / bar / barh / colstack / barstack。labels：数据标签的数字格式（如 '0.0'），None 不显示。"""
    cd = CategoryChartData(); cd.categories = categories
    for name, vals in series.items():
        cd.add_series(name, vals)
    ct = {"line": XL_CHART_TYPE.LINE_MARKERS, "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
          "barh": XL_CHART_TYPE.BAR_CLUSTERED, "colstack": XL_CHART_TYPE.COLUMN_STACKED,
          "barstack": XL_CHART_TYPE.BAR_STACKED}[kind]
    gf = slide.shapes.add_chart(ct, x, y, w, h, cd); ch = gf.chart
    _style_chart(ch, len(series), s, legend)
    colors = colors or [TEAL, RED, BLUE, AMBER, MUTE]
    for i, ser in enumerate(ch.series):
        col = colors[i % len(colors)]
        if kind == "line":
            ser.format.line.color.rgb = col; ser.format.line.width = Pt(2); ser.smooth = False
        else:
            ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
    if x_title:
        _axis_title(ch.category_axis, x_title, s)
    if y_title:
        _axis_title(ch.value_axis, y_title, s)
    if number_format:
        ch.value_axis.tick_labels.number_format = number_format
        ch.value_axis.tick_labels.number_format_is_linked = False
    if labels:
        plot = ch.plots[0]
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.number_format, dl.number_format_is_linked = labels, False
        dl.font.size = Pt(s)
    if gap is not None:
        ch.plots[0].gap_width = gap
    if kind in ("colstack", "barstack"):
        ch.plots[0].overlap = 100
    return gf


def _log_axis(axis):
    scaling = axis._element.find(qn("c:scaling"))
    scaling.insert(0, scaling.makeelement(qn("c:logBase"), {"val": "10"}))


def xy_chart(slide, x, y, w, h, series, colors=None, x_title=None, y_title=None,
             log=False, s=10, legend=True, log_x=None, log_y=None, x_range=None, y_range=None):
    cd = XyChartData()
    for name, pts in series.items():
        se = cd.add_series(name)
        for px, py in pts:
            se.add_data_point(px, py)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, x, y, w, h, cd)
    ch = gf.chart
    _style_chart(ch, len(series), s, legend)
    colors = colors or [TEAL, RED, BLUE, AMBER, MUTE]
    for i, ser in enumerate(ch.series):
        ser.format.line.color.rgb = colors[i % len(colors)]; ser.format.line.width = Pt(2)
        ser.smooth = False
    if log_x if log_x is not None else log:
        _log_axis(ch.category_axis)
    if log_y if log_y is not None else log:
        _log_axis(ch.value_axis)
    if x_range:
        ch.category_axis.minimum_scale, ch.category_axis.maximum_scale = x_range
    if y_range:
        ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = y_range
    if x_title:
        _axis_title(ch.category_axis, x_title, s)
    if y_title:
        _axis_title(ch.value_axis, y_title, s)
    return gf


def vline(slide, x, y1, y2, color=MUTE, w=1.5, dash=False):
    cn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, y1, x, y2)
    cn.line.color.rgb = color; cn.line.width = Pt(w)
    if dash:
        cn.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    return cn


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s

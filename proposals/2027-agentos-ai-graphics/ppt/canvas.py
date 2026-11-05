"""arch-canvas 画布构建助手：节点、分区、连线、编号、小表，外加文字放不放得下的粗估。"""

import math

W, H = 616, 390
PT = {"caption": 9, "detail": 10, "body": 12, "body_strong": 12, "emphasis": 14}


def text_width(text, size_pt):
    px = size_pt * 96 / 72
    w = 0.0
    for ch in text:
        if ord(ch) < 128:
            w += 0.62 if ch.isupper() or ch.isdigit() else 0.52
        elif ch in "·–—":
            w += 0.5
        else:
            w += 1.0
    return w * px


class Canvas:
    def __init__(self, name, size=(W, H)):
        self.name = name
        self.W, self.H = size
        self.panels, self.shapes, self.texts, self.arrows, self.badges = [], [], [], [], []
        self.warnings = []

    # ---- 检查 ----
    def _fit(self, box, text, style, inset):
        x, y, w, h = box
        if x < 0 or y < 0 or x + w > self.W + 0.01 or y + h > self.H + 0.01:
            self.warnings.append(f"{self.name}: 越界 {box} {text!r}")
        if not text:
            return
        size = PT[style]
        lh = size * 96 / 72 * 1.2
        lines = 0
        for line in text.split("\n"):
            lines += max(1, math.ceil(text_width(line, size) / max(1, w - 2 * inset - 2)))
        if lines * lh > h + 1:
            self.warnings.append(f"{self.name}: 放不下（{lines} 行，需 {lines * lh:.0f}px / 框 {h}px，宽 {w}） {text!r}")

    # ---- 元素 ----
    def panel(self, x, y, w, h, fill="surface_light", line=None, dash=False, radius=6, kind="rounded"):
        item = {"box": [x, y, w, h], "fill": fill, "kind": kind}
        if kind == "rounded":
            item["radius"] = radius
        if line:
            item["line"] = line
        if dash:
            item["dash"] = True
        self._fit(item["box"], "", "caption", 0)
        self.panels.append(item)

    def node(self, x, y, w, h, text, fill="bg", line="line", style="detail", color=None, bold=None,
             kind="rounded", radius=3, align=None, dash=False):
        item = {"box": [x, y, w, h], "fill": fill, "kind": kind, "text": text, "text_style": style}
        if kind == "rounded":
            item["radius"] = radius
        if line:
            item["line"] = line
        if dash:
            item["dash"] = True
        if color:
            item["color"] = color
        if bold is not None:
            item["bold"] = bold
        if align:
            item["align"] = align
        self._fit(item["box"], text, style, 2)
        self.shapes.append(item)

    def key(self, x, y, w, h, text, style="detail"):
        """创新点 / 判定节点：浅橙底、深红描边、深红加粗字。"""
        self.node(x, y, w, h, text, fill="highlight", line="accent", style=style, color="accent", bold=True)

    def core(self, x, y, w, h, text, style="detail"):
        """核心模块：靛蓝实心、白字。"""
        self.node(x, y, w, h, text, fill="primary", line="primary", style=style, color="on_primary", bold=True)

    def out(self, x, y, w, h, text, style="detail"):
        """输出 / 收益节点：浅蓝底、靛蓝描边。"""
        self.node(x, y, w, h, text, fill="highlight_blue", line="primary", style=style)

    def text(self, x, y, w, h, text, style="caption", color=None, bold=None, align="center", valign="middle"):
        item = {"box": [x, y, w, h], "text": text, "style": style, "align": align, "valign": valign}
        if color:
            item["color"] = color
        if bold is not None:
            item["bold"] = bold
        self._fit(item["box"], text, style, 0)
        self.texts.append(item)

    def mask(self, x, y, w, h, text, color="primary_text"):
        """压在连线上的白底标注。"""
        self.node(x, y, w, h, text, fill="bg", line=None, style="caption", color=color, kind="rect")

    def arrow(self, *points, color="primary", head=True, width=1.25):
        item = {"points": [list(p) for p in points]}
        if color != "primary":
            item["color"] = color
        if not head:
            item["head"] = False
        if width != 1.25:
            item["width"] = width
        for p in points:
            if not (0 <= p[0] <= self.W and 0 <= p[1] <= self.H):
                self.warnings.append(f"{self.name}: 连线越界 {p}")
        self.arrows.append(item)

    def badge(self, x, y, n, d=16):
        self.badges.append({"box": [x, y, d, d], "fill": "highlight_strong", "kind": "oval", "text": str(n),
                            "text_style": "caption", "color": "on_primary", "bold": True})

    def lane(self, x, y, w, h, n, title, fill="surface_light"):
        self.panel(x, y, w, h, fill=fill, radius=8)
        tx = x + 8
        if n:
            self.badge(x + 8, y + 5, n)
            tx = x + 30
        self.text(tx, y + 3, w - (tx - x) - 6, 20, title, style="body_strong", color="primary_text", align="left")

    def table(self, x, y, widths, rows, row_h=22, header_fill="primary", header_color="on_primary", emph=None,
              style="caption", align=None):
        """rows[0] 是表头；单元格写 "^" 表示与上一行合并；emph(r, c, text) 返回 (fill, color, bold) 或 None。"""
        cy = y
        for r, row in enumerate(rows):
            cx = x
            for c, (cw, cell) in enumerate(zip(widths, row)):
                if cell == "^":
                    cx += cw
                    continue
                span = 1
                while r + span < len(rows) and rows[r + span][c] == "^":
                    span += 1
                if r == 0:
                    self.node(cx, cy, cw, row_h, cell, fill=header_fill, line="bg", style=style,
                              color=header_color, bold=True, kind="rect")
                else:
                    fill, color, bold = "bg", None, None
                    if emph:
                        got = emph(r, c, cell)
                        if got:
                            fill, color, bold = got
                    self.node(cx, cy, cw, row_h * span, cell, fill=fill, line="line", style=style, color=color,
                              bold=bold, kind="rect", align=(align[c] if align else None))
                cx += cw
            cy += row_h
        return cy

    def data(self):
        out = {"canvas": [self.W, self.H]}
        if self.panels:
            out["panels"] = self.panels
        shapes = self.shapes + self.badges
        if shapes:
            out["shapes"] = shapes
        if self.texts:
            out["texts"] = self.texts
        if self.arrows:
            out["arrows"] = self.arrows
        return out

"""关键技术页的两种版式：
- problem_page：问题机理（编号步骤图）+ 量化证据 + 业界方案扫描表 + 差异化与风险
- solution_page：机制架构（感知/建模 → 决策 → 执行 → 反馈）+ 三个技术难题 + 目标与度量 + 交付节奏
内容用 dict 传入，版式统一，便于 12 项技术保持一致。"""

from lib import (arrow, box, card, new_slide, num_badge, poly_arrow, table, text, titled_card)


def problem_page(prs, d):
    s = new_slide(prs, d["code"] + " " + d["name"], "问题与业界进展", d["takeaway"])
    # 左上：问题机理
    x0, w = 32, 600
    card(s, (x0, 128, w, 316))
    text(s, (x0 + 14, 136, w - 28, 20), f"@@问题机理@@：{d['mech_title']}", style="body")
    steps = d["mech"]
    n = len(steps)
    top, bottom, gap = 162, 436, 8
    h = (bottom - top - gap * (n - 1)) / n
    y = top
    for i, (t, desc, badge) in enumerate(steps):
        fill = "surface" if badge else "highlight_blue"
        box(s, (x0 + 14, y, w - 66, h), f"**{t}**：{desc}", fill=fill, style="detail", align="left", inset=8)
        if badge:
            num_badge(s, x0 + w - 44, y + h / 2 - 10, badge)
        if i < n - 1:
            arrow(s, (x0 + 14 + (w - 66) / 2, y + h), (x0 + 14 + (w - 66) / 2, y + h + gap), color="muted", width=1.25)
        y += h + gap
    # 左下：量化证据
    titled_card(s, (x0, 456, w, 232), "量化证据", d["evidence"], style="detail", gap_pt=3)
    # 右上：业界方案扫描
    rx, rw = 648, 600
    table(s, (rx, 128, rw, 400), ["方案", "时间 / 来源", "原理", "效果与局限"], d["scan"],
          widths=[1.3, 1.1, 2.0, 2.4], style="caption", header_style="detail")
    # 右下：差异化与风险
    card(s, (rx, 540, rw, 148))
    text(s, (rx + 14, 548, rw - 28, 20), "我们的差异化与风险", style="emphasis", color="primary_text")
    text(s, (rx + 14, 572, rw - 28, 112), d["diff"], style="detail", gap_pt=2)
    return s


def solution_page(prs, d):
    s = new_slide(prs, d["code"] + " " + d["name"], "方案与技术难点", d["goal"])
    # 左：机制架构四层
    x0, w = 32, 568
    card(s, (x0, 128, w, 560))
    text(s, (x0 + 14, 136, w - 28, 20), f"@@机制架构@@：{d['arch_title']}", style="body")
    lanes = d["arch"]
    names = ["感知 / 建模", "决策", "执行", "反馈"]
    top, bottom, agap = 164, 676, 16
    lh = (bottom - top - agap * 3) / 4
    LW = 70
    y = top
    for i, (name, comps) in enumerate(zip(names, lanes)):
        box(s, (x0 + 14, y, LW, lh), name, fill="primary", color="on_primary", style="body_strong")
        n = len(comps)
        cols = 2 if n > 2 else n
        rows = (n + cols - 1) // cols
        cx0 = x0 + 14 + LW + 8
        cwid = (w - 28 - LW - 8 - 34 - 6 * (cols - 1)) / cols
        chh = (lh - 6 * (rows - 1)) / rows
        for j, c in enumerate(comps):
            r, cc = divmod(j, cols)
            new = c.startswith("+")
            label = c[1:] if new else c
            box(s, (cx0 + cc * (cwid + 6), y + r * (chh + 6), cwid, chh), label,
                fill="highlight" if new else "surface", line="highlight_strong" if new else None, style="detail", inset=4)
        if i < 3:
            mx = x0 + 14 + LW / 2
            arrow(s, (mx, y + lh), (mx, y + lh + agap), color="accent", width=1.5)
        y += lh + agap
    # 反馈回环：从反馈层右侧回到感知层
    rxl = x0 + w - 22
    fy = top + 3 * (lh + agap) + lh / 2
    poly_arrow(s, [(rxl - 10, fy), (rxl, fy), (rxl, top + lh / 2), (rxl - 10, top + lh / 2)], color="accent", width=1.25)

    # 右上：三个技术难题
    rx, rw = 616, 632
    dy = 128
    for i, (title, key, hard, how) in enumerate(d["diffs"], 1):
        card(s, (rx, dy, rw, 112))
        text(s, (rx + 12, dy + 6, rw - 260, 20), f"!!难题{'一二三'[i - 1]}!!　**{title}**", style="body")
        box(s, (rx + rw - 246, dy + 6, 234, 22), f"突破：{key}", fill="highlight_blue", style="caption", inset=3)
        text(s, (rx + 12, dy + 32, rw - 24, 76), f"**难在哪**：{hard}\n**怎么破**：{how}", style="detail", gap_pt=2)
        dy += 118
    # 右下：目标与度量
    table(s, (rx, 484, rw, 118), ["指标", "基线", "目标（建议区间）", "依据与条件"], d["targets"],
          widths=[1.4, 1.0, 1.3, 2.6], style="caption", header_style="caption")
    # 交付节奏
    qs = d["plan"]
    qw = (rw - 3 * 6) / 4
    for i, (q, t) in enumerate(qs):
        qx = rx + i * (qw + 6)
        box(s, (qx, 610, qw, 20), q, fill="primary", color="on_primary", style="caption", inset=2)
        box(s, (qx, 632, qw, 56), t, fill="bg", style="caption", align="left", valign="top", inset=5, shadow=True)
    return s

"""页面生成函数：solutions 模板版式 + 浅色风格。

各组件的页面模块只写内容 spec，统一调用这里的函数，保证全套风格一致：
  kt_page      关键技术单页（solution-kickoff-difficulties：挑战与目标 / 三分区方案架构 / 三个技术难题 / 交付节奏）
  arch_page    组件目标架构（solution-arch-overview：核心挑战与架构理念 / 双分区 + 共享层 / 关键技术）
  load_page    负载量化（result-sim-tables-read：本页回答的问题 / 分析方法 / 分栏指标表与关键结论）
  bn_*         瓶颈分析（problem-arch-callouts）的部件：中央架构图由页面模块自绘，两侧卡片与连线用 bn_side 等
文字规则：正式的汇报语言；!!…!! 深红加粗（关键数字），@@…@@ 蓝色加粗（关键结论），**…** 加粗。
"""

from lib import (arrow, badge, box, bullets, callout, canvas_panel, difficulty_cards, footnote, layer_row, measure,
                 milestones, new_slide, outline, poly, rect, round_card, scan_card, table, table_height, text, _warn,
                 head_card)

KIND = {
    "in": dict(fill="blue_l", line="grey_d"),        # 输入 / 感知
    "plain": dict(fill="bg", line="grey_d"),          # 普通节点
    "core": dict(fill="blue_m", line=None),           # 决策核心 / 下发（原模板深蓝块，改浅蓝）
    "judge": dict(fill="peach_l", line="red", line_width=1.25),   # 判定条件
    "effect": dict(fill="blue_l", line="grey_d"),     # 作用 / 收益
    "alt": dict(fill="purple_l", line="grey_d"),      # 辅助路径
    "warn": dict(fill="pink_l", line="grey_d"),       # 压力 / 风险来源
    "new": dict(fill="peach_l", line="red", line_width=1.25, color="accent"),   # 新增动作
}


def kbox(slide, b, md, kind="plain", style="detail"):
    opts = dict(KIND[kind])
    color = opts.pop("color", None)
    return box(slide, b, md, style=style, color=color, **opts)


# ---------------------------------------------------------------- 立项方案页（solution-kickoff-difficulties）

def _flow_natural(row, w):
    t = row[0]
    if t == "box":
        return max(30, measure(row[1], w - 8, "detail") + 12)
    if t == "pair":
        hw = (w - 8) / 2
        return max(36, max(measure(m, hw - 8, "detail") + 12 for m, _ in row[1]))
    if t == "acts":
        return len(row[1]) * 42 + 4
    if t == "table":
        return 18 + table_height(w, row[2], row[3], row[4] if len(row) > 4 else None, style="caption", pad=(3, 1))
    if t == "note":
        return measure(row[1], w, "detail") + 2
    raise ValueError(t)


def flow_panel(slide, inner, rows, gap=10):
    """架构画布分区内自上而下的节点流。rows 元素：
      ("box", md, kind)                                  单个节点（kind 见 KIND）
      ("pair", [(md, kind), (md, kind)], ("是", "否"))     并排两个节点；第三项可选，为两条分支的标签
      ("acts", [(动作, 作用对象), ...])                    虚线框内的「动作 → 作用对象」行（建议 2–3 行）
      ("table", 表题, 表头, 行, 列宽)                      小表格（9 号字）
      ("note", md)                                       一行说明文字（其后不画箭头）
    节点高度按内容自动分配并拉伸填满分区；相邻行之间自动画向下的箭头。"""
    x, y, w, h = inner
    nat = [_flow_natural(r, w) for r in rows]
    gaps = [18 if (r[0] == "pair" and len(r) > 2) else gap for r in rows[1:]]
    extra = h - sum(nat) - sum(gaps)
    if extra < -4:
        _warn(f"架构分区溢出 {-extra:.0f}px")
    stretch = [i for i, r in enumerate(rows) if r[0] in ("box", "pair")]
    add = max(0.0, extra) / max(1, len(stretch))
    spare = 0.0
    if add > 28:
        spare = (add - 28) * len(stretch)
        add = 28
    if gaps and spare:
        gaps = [g + spare / len(gaps) for g in gaps]
    yy = y
    prev = None
    for i, r in enumerate(rows):
        if i:
            yy += gaps[i - 1]
        hh = nat[i] + (add if i in stretch else 0)
        t = r[0]
        if t == "box":
            kbox(slide, (x, yy, w, hh), r[1], r[2])
            tops = [x + w / 2]
            cur = ("single", tops, yy + hh)
        elif t == "pair":
            hw = (w - 8) / 2
            xs_ = [x, x + hw + 8]
            for (md, kind), bx in zip(r[1], xs_):
                kbox(slide, (bx, yy, hw, hh), md, kind)
            tops = [bx + hw / 2 for bx in xs_]
            if len(r) > 2:
                for lab, cx in zip(r[2], tops):
                    text(slide, (cx + 5, yy - 17, 40, 16), f"!!{lab}!!", style="caption", check=False)
            cur = ("pair", tops, yy + hh)
        elif t == "acts":
            outline(slide, (x - 2, yy - 2, w + 4, hh + 2), line="grey_d", width=1.0, dash=True)
            aw = min(96, w * 0.48)
            ow = w - aw - 16
            for k, (act, obj) in enumerate(r[1]):
                ay = yy + 3 + k * 42
                kbox(slide, (x + 2, ay, aw, 36), f"**{act}**", "new")
                arrow(slide, (x + 2 + aw, ay + 18), (x + aw + 13, ay + 18), color="dark")
                kbox(slide, (x + aw + 14, ay, ow, 36), obj, "plain", style="caption")
            tops = [x + w / 2]
            cur = ("single", tops, yy + hh)
        elif t == "table":
            text(slide, (x, yy, w, 16), f"@@{r[1]}@@", style="detail", align="center", check=False)
            table(slide, (x, yy + 18, w, 10), r[2], r[3], widths=r[4] if len(r) > 4 else None, style="caption",
                  fit=False, check=False, pad=(3, 1))
            tops = [x + w / 2]
            cur = ("single", tops, yy + hh)
        else:  # note
            text(slide, (x, yy, w, hh), r[1], style="detail", align="center", check=False)
            tops = [x + w / 2]
            cur = ("note", tops, yy + hh)
        if prev is not None and prev[0] != "note":
            if prev[0] == "pair" and cur[0] == "pair":
                for a_, b_ in zip(prev[1], tops):
                    arrow(slide, (a_, prev[2]), (b_, yy), color="dark")
            elif prev[0] == "pair":
                for cx in prev[1]:
                    arrow(slide, (cx, prev[2]), (cx, yy), color="dark")
            else:
                for cx in tops:
                    arrow(slide, (cx, prev[2]), (cx, yy), color="dark")
        prev = cur
        yy += hh


def kt_page(prs, spec):
    """关键技术单页（立项方案版式）。spec 字段：
      crumb, title, suffix：位置导航、标题主体（以「：」结尾）与后半句（技术路线 + 核心量化目标）
      challenge：以「!!挑战：…!!」开头的一段；goal：以「!!目标：!!」开头，量化目标用 @@…@@
      panels：三个分区 [(分区名, rows)]，通常为「感知与建模」「决策」「执行与作用」，rows 见 flow_panel
      loop：闭环说明（「评估结果回流，校准……」）
      difficulties：三个难题 [(难题名, "- **难点**：…\\n- **方法名**：…@@关键突破@@")]，编号与分区编号对应
      milestones：三个里程碑 [(交付件, "2027.06")]
      source：页脚来源"""
    s = new_slide(prs, spec["title"], spec["suffix"], crumb=spec["crumb"])
    round_card(s, (32, 88, 640, 178))
    ch = measure(spec["challenge"], 616, "body")
    g = measure(spec["goal"], 616, "body")
    if ch + g + 10 > 166:
        _warn(f"挑战与目标溢出 {ch + g + 10:.0f}>166px")
    text(s, (44, 96, 616, ch + 2), spec["challenge"], style="body", check=False)
    text(s, (44, 96 + ch + 10, 616, g + 2), spec["goal"], style="body", check=False)

    pw, gp, top, ph = 196, 26, 280, 372
    xs = [32, 32 + pw + gp, 32 + 2 * (pw + gp)]
    for i, (ptitle, rows) in enumerate(spec["panels"]):
        inner = canvas_panel(s, (xs[i], top, pw, ph), str(i + 1), ptitle)
        flow_panel(s, inner, rows)
    for i in range(2):
        arrow(s, (xs[i] + pw + 2, top + 150), (xs[i + 1] - 2, top + 150), color="dark", width=1.25)
    fy = top + ph + 14
    poly(s, [(xs[2] + pw / 2, top + ph), (xs[2] + pw / 2, fy), (xs[0] + pw / 2, fy), (xs[0] + pw / 2, top + ph)],
         head=True, color="red", width=1.25)
    text(s, (xs[0] + pw / 2 + 40, fy - 8, 270, 16), spec["loop"], style="caption", color="accent", align="center",
         fill="bg", check=False)

    difficulty_cards(s, (696, 88, 552, 478), spec["difficulties"])
    milestones(s, (696, 574, 552, 108), spec["milestones"])
    footnote(s, spec["source"], y=694, w=1100)
    return s


# ---------------------------------------------------------------- 组件架构页（solution-arch-overview）

def arch_page(prs, spec):
    """组件目标架构页。spec 字段：
      crumb, title, suffix, takeaway（一句话目标，18 号，约 50 字以内）
      challenges / principles：各三条 [(名称, 说明)]，每条一行（挑战含名称约 30 字、理念含名称约 24 字以内）
      （techs 的名称约 18 字以内，保证一行）
      partitions：两个分区 [(分区标题, [(层名, [(模块文字, 是否新增), ...]), ...])]，每分区 2–3 层，每层 1–3 个模块
      shared：共享层 1–2 行 [(层名，可含 \\n, [(模块文字, 是否新增), ...])]
      techs：关键技术 3–4 项 [(名称, 怎么做, 效果)]，怎么做与效果各约 30 字以内
      badges：[(位置, 层序号, 模块序号, 技术编号)]，位置为 "p1" / "p2" / "s"（共享层），序号从 0 起
      source：页脚来源"""
    s = new_slide(prs, spec["title"], spec["suffix"], crumb=spec["crumb"], takeaway=spec["takeaway"])
    head_card(s, (32, 128, 664, 92), "核心\n挑战", "\n".join(f"**{n}**：{d}" for n, d in spec["challenges"]))
    head_card(s, (712, 128, 536, 92), "架构\n理念", "\n".join(f"**{n}**：{d}" for n, d in spec["principles"]))

    pw = (664 - 12) / 2
    px = (32, 32 + pw + 12)
    cells = {}
    body_h = 252
    for k, (x, (ptitle, layers)) in enumerate(zip(px, spec["partitions"])):
        outline(s, (x, 236, pw, 26), line="primary_text", width=1.25)
        text(s, (x, 236, pw, 26), f"**{ptitle}**", style="body", color="primary_text", align="center",
             valign="middle", check=False)
        rect(s, (x, 266, pw, body_h), "grey_l")
        n = len(layers)
        lh = (body_h - 12 - 8 * (n - 1)) / n
        for i, (lname, mods) in enumerate(layers):
            cells[(f"p{k + 1}", i)] = layer_row(s, x + 6, 272 + i * (lh + 8), pw - 12, lh, lname, mods)
    shared = spec.get("shared", [])
    sy = 526
    rect(s, (32, sy, 664, 146), "grey_l")
    hs = [70, 56] if len(shared) == 2 else [134]
    yy = sy + 6
    for i, (lname, mods) in enumerate(shared):
        cells[("s", i)] = layer_row(s, 38, yy, 652, hs[i], lname, mods)
        yy += hs[i] + 8
    rect(s, (566, 678, 12, 10), "peach_l", line="red", line_width=1.0)
    text(s, (582, 674, 114, 16), "本次新增 / 改动", style="caption", check=False)
    for where, i, j, n in spec.get("badges", []):
        b = cells[(where, i)][j]
        badge(s, b[0] + b[2] - 6, b[1] + 6, n, d=18)

    outline(s, (712, 236, 536, 436), line="grey_line")
    text(s, (728, 246, 504, 26), "**关键技术**", style="emphasis", color="accent", valign="middle", check=False)
    items = spec["techs"]
    slot = 392 / len(items)
    for i, (name, how, goal) in enumerate(items):
        y = 278 + i * slot
        badge(s, 742, y + 14, i + 1, d=26)
        text(s, (764, y + 1, 472, 26), f"**{name}**", style="emphasis", color="accent", valign="middle")
        text(s, (764, y + 30, 472, slot - 32), f"- **怎么做**：{how}\n- **效果**：@@{goal}@@", style="body", gap_pt=2)
    footnote(s, spec["source"], y=694, w=1100)
    return s


# ---------------------------------------------------------------- 负载量化页（result-sim-tables-read）

TONE = {"warm": "peach_l", "gray": "grey_m", "cool": "blue_l"}


def load_page(prs, spec):
    """负载量化页。spec 字段：
      crumb, title, suffix
      questions：本页回答的问题，3 张卡 [(tone: warm / gray / cool, 名称（以「：」结尾）, 说明，约 40 字)]
      methods：分析方法 3 条 [(名称, 说明，约 26 字)]
      banner：横幅一句话（「基于统一的「贴身秘书」参考负载，以下分 N 栏给出……的量化结论」）
      columns：2–3 栏 [(栏标题, [(表题, 表头, 行, 列宽), ...], [(结论名, 结论)])]；表格为 9 号字
      source：页脚来源"""
    s = new_slide(prs, spec["title"], spec["suffix"], crumb=spec["crumb"])
    text(s, (32, 88, 604, 22), "**本页回答的问题**", style="emphasis", align="center", valign="middle", check=False)
    text(s, (644, 88, 604, 22), "**分析方法**", style="emphasis", align="center", valign="middle", check=False)
    outline(s, (32, 112, 604, 128), line="grey_line")
    cards = spec["questions"]
    n = len(cards)
    cw = (592 - 8 * (n - 1)) / n
    for i, (tone, name, desc) in enumerate(cards):
        x = 38 + i * (cw + 8)
        rect(s, (x, 116, cw, 120), TONE[tone])
        text(s, (x + 6, 120, cw - 12, 112), f"@@{name}@@{desc}", style="detail")
    outline(s, (644, 112, 604, 128), line="grey_line")
    bullets(s, (656, 120, 584, 114), spec["methods"], style="body", gap_pt=5)

    rect(s, (280, 248, 720, 22), "blue_l")
    text(s, (280, 248, 720, 22), f"**{spec['banner']}**", style="emphasis", align="center", valign="middle",
         check=False)
    rect(s, (336, 272, 608, 22), "blue_l")
    text(s, (336, 272, 608, 22), "**关键结果**", style="emphasis", align="center", valign="middle", check=False)

    cols = spec["columns"]
    m = len(cols)
    cw = (1216 - 8 * (m - 1)) / m
    top, hh = 300, 388
    for k, (ctitle, blocks, points) in enumerate(cols):
        x = 32 + k * (cw + 8)
        outline(s, (x, top, cw, hh), line="grey_line")
        text(s, (x + 4, top + 5, cw - 8, 20), f"**{ctitle}**", style="body", color="accent", align="center",
             check=False)
        yy = top + 28
        ix, iw = x + 8, cw - 16
        for caption, heads, rows, widths in blocks:
            text(s, (ix, yy, iw, 16), caption, style="detail", align="center", check=False)
            yy += 17
            yy += table(s, (ix, yy, iw, 10), heads, rows, widths=widths, style="caption", fit=False, check=False,
                        pad=(3, 1)) + 6
        text(s, (ix, yy, iw, 18), "**关键结论**", style="body", color="accent", check=False)
        yy += 20
        md = "\n".join(f"- **{a}**：{b}" for a, b in points)
        text(s, (ix, yy, iw, top + hh - 6 - yy), md, style="detail", gap_pt=3)
    footnote(s, spec["source"], y=694, w=1100)
    return s


# ---------------------------------------------------------------- 瓶颈分析页（problem-arch-callouts）的部件
# 中央架构图各组件差异大，由页面模块用 box / text / outline 自绘（范围 x 388–892、y 90–560）；
# 两侧问题卡、技术扫描卡、连线与编号用下列函数。

BN_LX, BN_LW = 32, 340
BN_CX, BN_CW = 388, 504
BN_RX, BN_RW = 908, 340
BN_Y0 = 90


def bn_layer(slide, y, h, label):
    """中央架构图的一层：左侧竖排层名；返回该层内容区的 (x1, 宽度)。"""
    md = label if label.isascii() else "\n".join(label)
    text(slide, (BN_CX + 2, y, 38, h), md, style="body_strong", align="center", valign="middle", check=False)
    return BN_CX + 46, BN_CW - 50


def bn_sep(slide, y):
    arrow(slide, (BN_CX + 4, y), (BN_CX + BN_CW, y), color="grey_d", width=0.75, head=False, dash=True)


def bn_side(slide, side, items, targets):
    """一侧的问题卡与扫描卡，自上而下排（卡间距 8px）。items 元素：
      ("callout", 圈码, 文字, 高度, 目标键)   红框问题卡（14 号加粗，每行约 17 字；三行取高度 86），
                                            连线指向 targets[目标键]，即中央图上编号圆点的位置 (x, y)
      ("card", 名称, 年份与来源, 原理说明, 遗留问题, 高度)   浅灰技术扫描卡（说明两行约 104–124，三行约 140）
    返回结束的 y（应 ≤ 686）。"""
    x, w = (BN_LX, BN_LW) if side == "left" else (BN_RX, BN_RW)
    y = BN_Y0
    for it in items:
        if it[0] == "callout":
            _, num, md, h, key = it
            callout(slide, (x, y, w, h), num, md)
            if side == "left":
                poly(slide, [(x + w, y + h / 2), (x + w + 8, y + h / 2), targets[key]], color="red", width=1.5)
            else:
                poly(slide, [(x, y + h / 2), (x - 8, y + h / 2), targets[key]], color="red", width=1.5)
        else:
            _, name, src, body, legacy, h = it
            scan_card(slide, (x, y, w, h), name, src, body, legacy=legacy)
        y += h + 8
    if y > 694:
        _warn(f"{side} 栏溢出至 {y:.0f}px")
    return y


def bn_bottom(slide, num, md, target, direction):
    """底部通栏问题卡（y 568–630）+ 改进方向（y 636–684）。target 为中央图上的编号位置。"""
    callout(slide, (BN_CX, 568, BN_CW, 62), num, md)
    poly(slide, [(target[0], 568), target], color="red", width=1.5)
    text(slide, (BN_CX, 636, BN_CW, 48), f"**改进方向**：{direction}", style="body", valign="middle")


def bn_badges(slide, targets, order):
    """最后画编号圆点，压在连线之上。order = [(编号, 目标键)]。"""
    for n, key in order:
        badge(slide, targets[key][0], targets[key][1], n)

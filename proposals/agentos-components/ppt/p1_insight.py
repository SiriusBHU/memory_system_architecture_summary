"""第一部分 · 洞察（报告 1-洞察）：
  章节页；业界三条路线（1.1.1）；端侧 Agent OS 能力蓝图与覆盖度（1.1.2–1.1.3）；
  四组件技术趋势（1.2.1–1.2.4）：三阶段演进 + 原型对比表 + 读表结论。
"""

import re
from pathlib import Path

from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Pt

import lib
from lib import arrow, badge, block_arrow, box, footnote, measure, new_slide, outline, plain, rect, round_card, table, \
    table_height, text
from registry import page

CRUMB = "一、洞察"
ZH = "一二三四"

# ---------------------------------------------------------------- 本模块的辅助函数

_MARK = {"●": "@@●@@", "◐": "**◐**", "○": "!!○!!", "—": "~~—~~"}
_FILL = {"●": "green_l", "○": "pink_l"}
_NOTE = re.compile(r"（(?:未核|待核|未核实|待核实|自报|自测|自评|推断|转引|判断|有争议|二手|估算|厂商口径|媒体)[^）]*）")
LEGEND = "图例：● 已具备　◐ 部分具备　○ 缺失或未见公开资料　— 不适用；灰字为口径标注（「未核」指仅凭单一来源或常识）。"


def cell(md: str) -> str:
    """原型表格子：● 蓝色加粗、○ 红色加粗、— 灰色；括号里的口径标注（未核、自报……）改灰色。"""
    md = md.strip()
    if md and md[0] in _MARK:
        md = _MARK[md[0]] + md[1:]
    return _NOTE.sub(lambda m: f"~~{m.group(0)}~~", md)


def col_edges(x, w, ratios):
    tot = sum(ratios)
    xs = [x]
    for r in ratios:
        xs.append(xs[-1] + w * r / tot)
    return xs


def _symbol_sizes(slide):
    """● ○ 在微软雅黑里偏小，调到 10 号；◐ 由后备字体绘制、偏大，调到 8 号，使三种符号观感接近。"""
    tbl = slide.shapes[-1].table
    for row in list(tbl.rows)[1:]:
        for c in row.cells:
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    if r.text in ("●", "○"):
                        r.font.size = Pt(10)
                    elif r.text == "◐":
                        r.font.size = Pt(8)


def _check_cells(edges, rows, max_lines, pad=4):
    for r in rows:
        for j, c in enumerate(r[1:], 1):
            n = lib.lines_of(plain(c), edges[j + 1] - edges[j] - 2 * pad, 9)
            if n > max_lines:
                lib._warn(f"格子 {n} 行：{plain(c)[:16]}")


def stages_row(s, y, h, stages):
    """三阶段演进：横向三个阶段框，第三阶段（当前前沿）用浅橙底加红框。"""
    gap = 28
    sw = (1216 - 2 * gap) / 3
    for i, (when, form, reps) in enumerate(stages):
        x = 32 + i * (sw + gap)
        hot = i == 2
        rect(s, (x, y, sw, h), "peach_l" if hot else "grey_l", line="red" if hot else None, line_width=1.25)
        head = f"**阶段{ZH[i]}**　~~{when}~~　" + (f"!!{form}!!" if hot else f"@@{form}@@")
        text(s, (x + 8, y + 3, sw - 16, 18), head, style="body", check=False)
        text(s, (x + 8, y + 22, sw - 16, h - 24), reps, style="detail", gap_pt=1)
        if i < 2:
            block_arrow(s, (x + sw + 6, y + h / 2 - 8, 16, 16), fill="grey_m")


def group_labels(s, y, edges, groups):
    """表头上方的原型分组标签：groups = [(标签, 起始列, 结束列)]，列号从 1 起（0 为要素列）。"""
    for label, a, b in groups:
        x0, x1 = edges[a] + 4, edges[b + 1] - 4
        text(s, (x0, y, x1 - x0, 15), f"**{label}**", style="caption", color="grey_d", align="center",
             check=False)
        rect(s, (x0, y + 15, x1 - x0, 1.2), "grey_d")


def conclusion_band(s, y, items, label="读表\n结论"):
    """表下方的「读表结论」横带：左侧红色标签，右侧 n 栏结论（@@名称@@：说明）。"""
    h = 686 - y
    outline(s, (32, y, 1216, h), line="grey_line")
    text(s, (36, y, 64, h), label, style="label_big", align="center", valign="middle", check=False)
    n = len(items)
    x0, gap = 108, 14
    cw = (1240 - x0 - gap * (n - 1)) / n
    mds = [f"@@{name}@@：{body}" for name, body in items]
    style = "body" if max(measure(m, cw, "body") for m in mds) <= h - 10 else "detail"
    for i, md in enumerate(mds):
        x = x0 + i * (cw + gap)
        if i:
            rect(s, (x - gap / 2, y + 8, 0.75, h - 16), "grey_m")
        text(s, (x, y + 4, cw, h - 8), md, style=style, valign="middle")


def trend_page(prs, spec):
    """技术趋势页：上方三阶段演进，中部原型对比表（9 号字），下方读表结论。"""
    s = new_slide(prs, spec["title"], spec["suffix"], crumb=spec["crumb"])
    sh = 60
    stages_row(s, 88, sh, spec["stages"])

    cols = spec["columns"]
    ratios = [spec.get("first_ratio", 0.7)] + [1] * (len(cols) - 1)
    edges = col_edges(32, 1216, ratios)
    gy = 88 + sh + 5
    group_labels(s, gy, edges, spec["groups"])
    ty = gy + 19
    raw = spec["rows"]
    rows = [["简介"] + spec["intro"]] + [[r[0]] + [cell(c) for c in r[1:]] for r in raw]
    _check_cells(edges, rows[:1], 3)
    _check_cells(edges, rows[1:], 2)
    fills = {(1, j): "grey_l" for j in range(len(cols))}
    for i, r in enumerate(raw, 2):
        for j, c in enumerate(r[1:], 1):
            if c.strip()[:1] in _FILL:
                fills[(i, j)] = _FILL[c.strip()[0]]
    th = table_height(1216, cols, rows, ratios, style="caption", pad=(4, 1))
    table(s, (32, ty, 1216, th), cols, rows, widths=ratios, style="caption", pad=(4, 1), fills=fills,
          align=["left"] * len(cols), fit=False)
    _symbol_sizes(s)
    cy = ty + th * 1.05 + 8   # 西文长词换行比估算早，留 5% 余量
    if 686 - cy < 56:
        lib._warn(f"读表结论区过矮 {686 - cy:.0f}px")
    conclusion_band(s, cy, spec["conclusions"])
    footnote(s, LEGEND + spec["source"], y=694, w=1130)
    return s


# ---------------------------------------------------------------- 章节页

@page
def insight_section(prs):
    lib.section_slide(prs, "一、", "洞察",
                      "Agent 的商业化趋势与端侧运行需求；业界 Agent OS 的三条路线；端侧 Agent OS 的能力蓝图与三项系统服务；"
                      "业界进展与技术趋势")


# ---------------------------------------------------------------- 概括：趋势洞察（背景 + 三个演进趋势）

IMG = Path(__file__).parent / "img"


def _picture(s, name, x, y, h):
    """按高度插图、保持原比例，返回图片宽度（逻辑像素）。"""
    pic = s.shapes.add_picture(str(IMG / name), Emu(lib.px_to_emu(x)), Emu(lib.px_to_emu(y)),
                               height=Emu(lib.px_to_emu(h)))
    return pic.width / lib.px_to_emu(1)


def _glow(s, b):
    """标题上方的浅灰光晕：自顶部中点向外渐隐为白色，衔接「背景」与「演进趋势」。"""
    shp = rect(s, b, "bg", kind="oval")
    sp_pr = shp._element.spPr
    for tag in ("a:solidFill", "a:noFill", "a:gradFill"):
        for el in sp_pr.findall(qn(tag)):
            sp_pr.remove(el)
    grad = parse_xml(
        f'<a:gradFill {nsdecls("a")} rotWithShape="1"><a:gsLst>'
        '<a:gs pos="0"><a:srgbClr val="D9D9D9"/></a:gs>'
        '<a:gs pos="100000"><a:srgbClr val="FFFFFF"/></a:gs></a:gsLst>'
        '<a:path path="circle"><a:fillToRect l="50000" t="0" r="50000" b="100000"/></a:path></a:gradFill>')
    sp_pr.find(qn("a:prstGeom")).addnext(grad)
    shp.line.fill.background()


def _diagram_inference(s, dx, dy, W=320):
    """推理服务化：多个应用与 Agent 共用系统托管的一个底座模型。"""
    g = 12
    bw = (W - 2 * g) / 3
    for i, nm in enumerate(["应用 A", "应用 B", "Agent"]):
        bx = dx + i * (bw + g)
        box(s, (bx, dy + 4, bw, 26), nm, fill="green_l" if nm == "Agent" else "bg", line="grey_d")
        arrow(s, (bx + bw / 2, dy + 31), (bx + bw / 2, dy + 47), color="dark")
    box(s, (dx, dy + 48, W, 42), "**系统推理服务**\n一个底座模型，按会话分配算力", fill="peach_l", line="red",
        line_width=1.25, color="accent")
    arrow(s, (dx + W / 2, dy + 91), (dx + W / 2, dy + 101), color="dark", head=False)
    box(s, (dx, dy + 101, W, 24), "NPU · GPU · PIM", fill="blue_l")


def _diagram_sandbox(s, dx, dy, W=320):
    """执行沙箱化：外部 Agent 经 A2A 入站、Agent 经 MCP 出站，每次调用在会话沙箱边界上判定。"""
    ew, sw = 58, 124
    cx = dx + W / 2
    box(s, (dx, dy + 36, ew, 50), "外部\nAgent", fill="bg", line="grey_d", inset=1)
    box(s, (dx + W - ew, dy + 36, ew, 50), "应用\n工具", fill="bg", line="grey_d", inset=1)
    outline(s, (cx - sw / 2, dy + 4, sw, 121), line="red", width=1.5, dash=True)
    text(s, (cx - sw / 2, dy + 8, sw, 16), "!!会话沙箱!!", style="detail", align="center", check=False)
    box(s, (cx - 40, dy + 40, 80, 42), "Agent", fill="green_l", line="grey_d")
    text(s, (cx - sw / 2, dy + 88, sw, 34), "隔离\n按调用判定", style="detail", align="center", check=False)
    arrow(s, (dx + ew + 1, dy + 61), (cx - 41, dy + 61), color="dark", width=1.25)
    arrow(s, (cx + 41, dy + 61), (dx + W - ew - 1, dy + 61), color="dark", width=1.25)
    gap = W / 2 - sw / 2 - ew
    text(s, (dx + ew, dy + 42, gap, 15), "@@A2A@@", style="caption", align="center", check=False)
    text(s, (cx + sw / 2, dy + 42, gap, 15), "@@MCP@@", style="caption", align="center", check=False)


def _diagram_memory(s, dx, dy, W=320):
    """X + Agent 内存协同管理：前台应用与 Agent 的权重、KV 共用一块 DRAM，统一记账、协同回收。"""
    text(s, (dx, dy, W, 15), "DRAM（12GB 机型）", style="caption", color="grey_d", check=False)
    segs = [("前台应用 X", 0.38, "blue_l"), ("Agent 权重", 0.27, "peach_l"), ("KV", 0.15, "peach_m"),
            ("其余", 0.20, "grey_m")]
    bx = dx
    for nm, frac, fill in segs:
        box(s, (bx, dy + 18, W * frac, 34), nm, fill=fill, line="grey_d", inset=1)
        bx += W * frac
    lib.poly(s, [(dx + 2, dy + 56), (dx + 2, dy + 62), (dx + W - 2, dy + 62), (dx + W - 2, dy + 56)], color="red",
             width=1.25)
    text(s, (dx, dy + 64, W, 16), "!!统一记账 · 协同回收!!", style="detail", align="center", check=False)
    wx = dx + W * 0.38 + W * 0.27 / 2
    arrow(s, (wx, dy + 101), (wx, dy + 84), color="dark")
    box(s, (dx, dy + 101, W, 24), "闪存（UFS）：权重按需换入", fill="blue_l")


@page
def overview(prs):
    s = new_slide(prs, "Agent OS 趋势洞察：",
                  "Agent 需求暴增，端侧需推理服务化、执行沙箱化、X+Agent 内存协同管理",
                  crumb=CRUMB + " › 概括")

    # ---- 上：背景　Agent 应用爆发式增长
    ix, iy, iw, ih = lib.panel(s, (32, 104, 1216, 214), "背景：Agent 应用爆发式增长")
    text(s, (ix, iy - 2, iw, 20),
         "@@Agent 处于爆发期，市场广阔@@：用户基盘已达十亿级，token 用量一年增长 7–10 倍，Agent 开始替用户付款；"
         "用户数增速放缓，用量成倍增长", style="body", check=False)
    tl = iy + 46
    arrow(s, (ix, tl), (ix + iw, tl), color="red", width=2.0)
    ch, cw = 126, 204
    prods = [
        ("2026-08", "xAI Grok Bot", "账号级常驻云端电脑；\n200 美元/月", "Grok 月活：3 个月由 !!3500 万增至 1.17 亿!!",
         "grok_bot.png"),
        ("2026-09", "OpenAI dot", "每个 Agent 一台云端电脑；\n随 Pro 档提供",
         "ChatGPT 周活 !!10 亿!!；Codex 周用户 2 个月由 !!500 万增至 800 万!!", "openai_dots.png"),
        ("2026-10", "阶跃手机开售", "整机 Agent 手机；\n3999 元起，10-16 首销",
         "Step AOS 于 7 月发布：\n系统级 Agent，端侧小模型加云端大模型", "stepx_neo.png"),
    ]
    # 图片按卡片高度等比缩放；先算总宽，再把余量均分到组间
    aspect = {"grok_bot.png": 104 / 118, "openai_dots.png": 89 / 115, "stepx_neo.png": 248 / 109}
    total = sum(cw + 10 + ch * aspect[p[4]] for p in prods)
    m = 8
    gap = (iw - 2 * m - total) / 2
    px = ix + m
    for date, name, form, metric, img in prods:
        cy = tl + 10
        lib.rect(s, (px + cw / 2 - 6, tl - 6, 12, 12), "red", kind="oval")
        text(s, (px + cw / 2 - 50, tl - 24, 100, 16), f"@@{date}@@", style="detail", align="center", check=False)
        round_card(s, (px, cy, cw, ch), radius=10)
        text(s, (px + 8, cy + 4, cw - 16, 20), f"**{name}**", style="body", color="primary_text", check=False)
        text(s, (px + 8, cy + 25, cw - 16, 40), form, style="detail")
        rect(s, (px + 8, cy + 67, cw - 16, 1), "grey_line")
        text(s, (px + 8, cy + 70, cw - 16, 54), metric, style="detail", gap_pt=0)
        iw_ = _picture(s, img, px + cw + 10, cy, ch)
        px += cw + 10 + iw_ + gap

    # ---- 中：Agent OS 系统服务演进趋势
    _glow(s, (160, 317, 960, 60))
    text(s, (340, 332, 600, 28), "Agent OS 系统服务演进趋势", style="panel_title", align="center", valign="middle",
         check=False)

    # ---- 下：三个趋势，各配一张示意图，并对应一项系统服务
    trends = [
        ("趋势一：推理服务化", _diagram_inference, "从每个应用自带模型，转为@@系统托管底座模型、按会话分配算力@@",
         "业界：Apple Foundation Models、Android AICore 均由系统托管端侧模型", "推理服务"),
        ("趋势二：执行沙箱化", _diagram_sandbox, "从应用级权限，转为@@系统按会话隔离、按每次调用判定权限@@",
         "业界：dot、Grok Bot 每个 Agent 一台云端电脑；Windows 为 Agent 设独立账户与会话", "执行与沙箱"),
        ("趋势三：X+Agent 内存协同管理", _diagram_memory,
         "从应用与模型各管各的，转为@@前台应用（X）与 Agent 统一记账、协同回收@@",
         "业界：Apple、Google 以 12GB 内存为准入门槛；AFM 3 权重放闪存、按请求换入", "内存与资源"),
    ]
    g = 16
    pw = (lib.WIDTH - 2 * g) / 3
    for i, (head, draw, shift, evid, svc) in enumerate(trends):
        tx, ty, tw, th = lib.panel(s, (lib.LEFT + i * (pw + g), 382, pw, 300), head)
        rect(s, (tx, ty, tw, 142), "grey_l", kind="rounded", radius=8)
        draw(s, tx + (tw - 320) / 2, ty + 8)
        text(s, (tx, ty + 150, tw, 44), shift, style="body")
        text(s, (tx, ty + 198, tw, 36), evid, style="detail", color="grey_d")
        box(s, (tx, ty + th - 30, tw, 28), f"对应系统服务：**{svc}**", fill="peach_l", line="red", line_width=1.25,
            color="accent", style="body")

    footnote(s, "来源：报告「概括」（GT1–GT7、AN1）。token 增长为 Google、豆包的厂商自报数据（经媒体转述）；"
                "「替用户付款」指支付宝 AI 付累计 3 亿笔（2026-05）；Grok 月活为二手转述；三款产品均未公开日活。",
             y=690, w=1140)


# ---------------------------------------------------------------- 1.1.1 业界三条路线

@page
def three_routes(prs):
    s = new_slide(prs, "业界三条路线的共同指向：", "端侧要在手机上为 Agent 提供推理与执行，并与应用共享芯片和内存",
                  crumb=CRUMB + " › 业界路线")
    cols = ["", "路线一　云端常驻 Agent", "路线二　OS 内建的系统级 Agent", "路线三　整机重构的 Agent 手机"]
    rows = [
        ["代表",
         "OpenAI dot（2026-09 上线）；xAI Grok Bot（2026-08 公测）；Meta Muse（2026-09）",
         "iOS 27 + 新 Siri；Android 17 + Gemini Intelligence；HarmonyOS 7 + 小艺 / HMAF 2.0；荣耀 MagicOS 11",
         "阶跃 STEPX Neo（2026-07 亮相，16GB，3999 元）；豆包手机（二代 2026-09 开售）"],
        ["架构要点",
         "每个 dot 配一台独立的云端 Linux 电脑与浏览器；Grok Bot 为账号级持久云 VM，多个 bot 共用；"
         "安全上采用环境外的独立审核，密码与付款交回用户确认",
         "Agent 在手机内，靠近用户数据、直接调用本机应用、可离线；Apple AFM 3 为 20B 稀疏模型，权重放在 NAND，"
         "每个请求换入 1–4B 激活参数；应用接入走 App Intents、AppFunctions（私有预览）、Skill（2100 多项，厂商口径）、MCP + A2A",
         "Step AOS 用 MCP 把系统能力做成功能块；豆包手机依靠系统特权做 GUI 自动化（读屏、模拟点击）"],
        ["商业模式与单位成本",
         "每用户每月 !!70–300 美元!!（估算：GPU 推理 + 云 VM）；dot 只随 100–500 美元档的 ChatGPT Pro 附赠，"
         "Grok Bot 单独订阅 200 美元/月（二手）",
         "随操作系统提供，云成本由厂商承担；Apple 与 Google 均以 !!12GB!! 内存作为准入门槛，iPhone 17 标准版的 8GB 被排除",
         "整机销售；概念上吸引力强，但出货规模小"],
        ["局限",
         "Agent 远离手机、本地数据和正在使用的 App；dot 越权率 5 步任务链 !!8.6%!!、10 步 !!19.7%!!"
         "（OpenAI 内部数据，二手转述）",
         "约束全部落在端侧资源上；没有一家公布模型的常驻内存，以及与应用共存时的回收机制",
         "!!150 余款!!应用（含微信、支付宝、淘宝、美团）拒绝被 GUI 自动化操作；绕开应用接口模拟点击，会受到应用生态的限制"],
    ]
    fills = {(0, 1): "blue_l", (0, 2): "green_l", (0, 3): "purple_l"}
    ratios = [0.42, 1, 1.12, 0.9]
    th = table_height(1216, cols, rows, ratios, style="detail", header_style="body_strong")
    table(s, (32, 88, 1216, th), cols, rows, widths=ratios, style="detail", header_style="body_strong",
          fills=fills, align=["left", "left", "left", "left"], fit=False)

    # 五个收敛事实
    y = 88 + th + 10
    text(s, (32, y, 1216, 22), "**三条路线收敛出的五个事实**", style="emphasis", color="accent", check=False)
    facts = [
        ("应用能力函数化已成共识", "App Intents、AppFunctions、Skill、MCP / A2A；GUI 模拟退为兜底。执行的安全边界须由系统划定"),
        ("内存成为端侧 Agent 的准入门槛", "两大平台以内存而非 NPU 算力作为准入门槛；无一家公布模型常驻内存与共存回收机制"),
        ("端侧模型走向稀疏大模型 + 闪存分层", "AFM 3 已量产；模型内存不再是固定常驻区，而是按请求换入换出的工作集"),
        ("Agent 需要完整的计算环境", "推理算力、隔离的执行环境、持久的状态与记忆、专属内存；云端以每人一台 VM 解决"),
        ("长任务的可靠性与可控性仍是瓶颈", "越权率随任务链变长而上升；Agent 的 token 消耗约为对话的 !!4!! 倍，多 Agent 约 !!15!! 倍（Anthropic 一手数据）"),
    ]
    fy = y + 26
    fh = 128
    gap = 10
    fw = (1216 - gap * 4) / 5
    for i, (name, body) in enumerate(facts):
        x = 32 + i * (fw + gap)
        round_card(s, (x, fy, fw, fh), radius=10)
        badge(s, x + 18, fy + 18, i + 1, d=22)
        text(s, (x + 34, fy + 6, fw - 40, 40), f"**{name}**", style="body", valign="middle")
        text(s, (x + 10, fy + 48, fw - 20, fh - 52), body, style="detail")

    # 对我们的启示
    iy = fy + fh + 10
    ih = 686 - iy
    outline(s, (32, iy, 1216, ih), line="grey_d", width=1.5, dash=True)
    text(s, (40, iy, 76, ih), "对我们\n的启示", style="label_big", align="center", valign="middle", check=False)
    text(s, (124, iy + 8, 396, ih - 16),
         "云端 Agent 以每用户一台云端虚拟机提供这四项能力，代价是每月数十至数百美元。"
         "端侧的记忆由各 Agent 自己持有；@@推理与执行要由系统提供@@，"
         "而且要与用户正在使用的 App 共享同一块芯片和同一块内存，这是 Agent OS 的系统层问题。",
         style="body", valign="middle")
    # 能力 → 经典 OS 部件 → 本次投入的组件
    gx, lw = 532, 100
    bw = (1240 - gx - lw - 3 * 8) / 4
    rows3 = [
        ("所需能力", ["推理算力的分配", "隔离的执行环境", "持久的状态与记忆", "专属内存"], "plain"),
        ("经典 OS 部件", ["处理器", "进程隔离", "文件系统", "虚拟内存"], "grey"),
        ("端侧的归属", ["推理服务", "执行与沙箱", "~Agent 层自有", "内存与资源"], "new"),
    ]
    rh, rg = 26, 14
    top = iy + (ih - 3 * rh - 2 * rg) / 2
    for k, (lab, items, kind) in enumerate(rows3):
        yy = top + k * (rh + rg)
        text(s, (gx, yy, lw - 8, rh), f"**{lab}**", style="detail", align="right", valign="middle", check=False)
        for j, it in enumerate(items):
            bx = gx + lw + j * (bw + 8)
            if kind == "new" and it.startswith("~"):
                box(s, (bx, yy, bw, rh), it[1:], fill="green_l", line="grey_d", style="body")
            elif kind == "new":
                box(s, (bx, yy, bw, rh), f"**{it}**", fill="peach_l", line="red", line_width=1.25, color="accent",
                    style="body")
            elif kind == "grey":
                box(s, (bx, yy, bw, rh), it, fill="blue_l", style="body")
            else:
                box(s, (bx, yy, bw, rh), it, fill="bg", line="grey_d", style="body")
            if k < 2:
                arrow(s, (bx + bw / 2, yy + rh + 1), (bx + bw / 2, yy + rh + rg - 1), color="dark")
    footnote(s, "来源：报告 1.1.1。单位成本为估算（D1-1）；dot、Grok Bot 的档位与越权率为二手转述（D1-2～D1-4）；"
                "2100 多项为厂商口径（H1）；AFM 3（A1）与 token 倍数（AN1）为一手资料。", y=694, w=1120)


# ---------------------------------------------------------------- 1.1.2 能力蓝图：为什么是三项系统服务

@page
def blueprint(prs):
    s = new_slide(prs, "端侧 Agent OS 能力蓝图：", "Agent 只需推理与执行，加上与应用共存，系统服务收为三项",
                  crumb=CRUMB + " › 能力蓝图")
    # 左：能力蓝图
    LX, LW = 32, 628
    ix, iy, iw, ih = lib.panel(s, (LX, 104, LW, 582), "能力蓝图")
    text(s, (ix, iy - 4, iw, 44),
         "@@目标形态@@：常驻的个人 Agent，在用户授权范围内代为办事。**想得快**：前台秒级响应，长任务上下文不丢；"
         "**做得稳**：异常影响限定在授权范围内，能定责、能撤销；**不打扰**：不影响正在使用的 App", style="detail")
    name_w, prov_w, g = 84, 100, 6
    mod_x = ix + name_w + g
    mod_w = iw - name_w - prov_w - 2 * g
    layers = [
        ("交互与感知", [("**交互**：语音、文本、多模态入口；生成式 UI", "plain"),
                    ("**感知**：屏幕内容、通知与消息事件", "plain")], "应用框架", 56),
        ("智能\n（Agent 层）", [("**System Agent**\n意图与编排 · @@记忆@@\n以 MCP / A2A 对外提供记忆读取", "agent"),
                           ("**应用 Agent**（微信、抖音等）\n意图与编排 · @@各自的记忆@@", "agent")],
         "Agent 框架\n（模型 + 运行时）", 100),
        ("能力接口", [("App Intents、AppFunctions、**MCP**、**A2A**、Skill", "plain")], "应用生态 + 系统", 44),
        ("系统服务", [("**推理服务**\n想", "new"), ("**执行与沙箱**\n做", "new"), ("**内存与资源**\n与应用共存", "new")],
         "!!OS（本次投入）!!", 100),
        ("内核与硬件", [("CPU / GPU / NPU · LPDDR 与 PIM · UFS · memcg · TEE", "plain")], "内核与芯片", 44),
    ]
    yy = iy + 48
    for lname, mods, prov, h in layers:
        box(s, (ix, yy, name_w, h), "\n".join(f"**{t}**" for t in lname.split("\n")), fill="blue_m",
            style="detail")
        n = len(mods)
        mw = (mod_w - g * (n - 1)) / n
        for j, (md, kind) in enumerate(mods):
            b = (mod_x + j * (mw + g), yy, mw, h)
            if kind == "new":
                box(s, b, md, fill="peach_l", line="red", line_width=1.25, color="accent", style="body")
            elif kind == "agent":
                box(s, b, md, fill="green_l", line="grey_d", style="detail")
            else:
                box(s, b, md, fill="bg", line="grey_d", style="detail")
        text(s, (mod_x + mod_w + g, yy, prov_w, h), prov, style="caption", color="grey_d", align="center",
             valign="middle")
        yy += h + 8
    box(s, (ix, yy, iw, 30), "**横切面**：安全与隐私（身份、权限、密钥、审计）由安全体系提供；可观测与计量由 OS 贯穿各层",
        fill="purple_l", style="detail")
    yy += 30 + 10
    nb = (ix, yy, iw, iy + ih - yy)
    outline(s, nb, line="grey_d", width=1.25, dash=True)
    text(s, (nb[0] + 10, nb[1] + 4, nb[2] - 20, nb[3] - 8),
         "@@记忆放在 Agent 层@@：记忆本体由各 Agent 自己持有；别的 Agent 需要读取用户上下文时，"
         "经 System Agent 的 MCP / A2A 接口获取，**每次读取由执行与沙箱判定权限**",
         style="detail", valign="middle")

    # 右：为什么系统服务只需要三项
    RX, RW = 680, 568
    text(s, (RX, 96, RW, 22), "**为什么系统服务只需要三项**", style="emphasis", color="accent", check=False)
    text(s, (RX, 120, RW, 22), "Agent 替用户办事，底层只做两件事：@@想@@和@@做@@；在手机上，它还要@@与应用共存@@",
         style="body", check=False)
    cards = [
        ("想", "推理服务", [
            "一个底座模型、一块 NPU、一块 DRAM，同时服务多个会话与多个应用",
            "单个 Agent 看不到别人的占用；模型也不可能每个应用带一份",
            "要做的是：长上下文推得动，NPU 与 PIM 等新算力用得上"]),
        ("做", "执行与沙箱", [
            "Agent 以用户身份经 MCP 调用应用与工具，也经 A2A 被外部 Agent 调用",
            "读入内容 70%–100% 来自第三方；每次调用能否放行，必须在 Agent 之外由系统判定",
            "没有它，应用方不敢开放接口，Agent 做不了交易"]),
        ("共存", "内存与资源", [
            "Agent 叠加在用户正在用的应用之上，二者共用同一块芯片和内存",
            "前台 Agent 与应用之间的内存、IO 与回收顺序，只有系统能协调",
            "分两个模块：通用内存管理优化；推理服务内存管理（权重、KV、专家）"]),
    ]
    cy, ch, cg = 150, 128, 10
    for i, (verb, svc, pts) in enumerate(cards):
        y = cy + i * (ch + cg)
        round_card(s, (RX, y, RW, ch), radius=10)
        box(s, (RX + 10, y + 10, 96, ch - 20), f"**{verb}**\n\n!!{svc}!!", fill="peach_l", line="red",
            line_width=1.25, style="body")
        text(s, (RX + 116, y + 6, RW - 126, ch - 12), "\n".join(f"- {p}" for p in pts), style="detail",
             valign="middle", gap_pt=4)
    by = cy + 3 * (ch + cg)
    bb = (RX, by, RW, 686 - by)
    outline(s, bb, line="grey_d", width=1.25, dash=True)
    text(s, (RX + 8, by + 2, 64, bb[3] - 4), "!!其余能力!!\n!!不放在 OS!!", style="body", align="center", valign="middle",
         check=False)
    text(s, (RX + 78, by + 4, RW - 86, bb[3] - 8),
         "- **交互与编排**：变化快，差异化在模型与产品层，由应用框架与 Agent 框架承担\n"
         "- **记忆**：与 Agent 能力绑定，各 Agent 自有；Siri、Gemini、小艺的记忆都随助手提供",
         style="detail", valign="middle", gap_pt=3)
    footnote(s, "来源：报告 1.1.2。第三方内容占比为报告 2.2.3 的估算；业界记忆的归属见下一页。", y=694, w=1120)


# ---------------------------------------------------------------- 1.1.3 业界覆盖度

COV_COLS = ["系统服务", "要素", "Apple / iOS", "Google / Android", "华为 / HarmonyOS", "云端 Agent"]
COV_ROWS = [
    ["推理服务", "系统级模型服务", "● Foundation Models 向第三方开放端侧模型", "● AICore 托管 Gemini Nano；NPU Manager 做模型级准入",
     "◐ 有端侧大模型，服务形态未公开", "● GPU 集群服务"],
    ["", "长上下文", "◐ 端侧示例窗口 8192 token", "○ Prompt API 窗口约 4000 token", "○ 未公开", "● 数十万至百万 token"],
    ["", "稀疏模型与闪存分层", "● AFM 3：20B 稀疏，权重在 NAND，每请求换入 1–4B", "○ 未公开", "○ 未公开", "—"],
    ["", "PIM 等新型算力", "○ 未见", "○ 未见", "○ 未见", "◐ 数据中心 HBM-PIM 原型，未规模商用"],
    ["执行与沙箱", "应用接入", "● App Intents，Siri 操作第三方应用的唯一途径", "◐ AppFunctions 私有预览；Computer Control 限预装助手",
     "● HMAF，2100 多项 Skill（厂商口径）", "◐ 云端浏览器与云电脑"],
    ["", "按会话、按调用的权限判定", "○ 只有 App 级权限", "◐ 首次操作需授权，交易时交还用户", "◐ 高风险操作需确认；转账支付由系统阻断（媒体）",
     "◐ 环境外独立审核；10 步任务链越权 19.7%（二手）"],
    ["", "隔离、快照与恢复", "◐ App 沙箱，无 Agent 会话边界", "◐ App 沙箱；AVF 未用于 Agent", "◐ 应用沙箱；「动态沙箱」无官方文档",
     "● 每个 Agent 一台 VM"],
    ["", "出口与凭证托管", "○ 未见", "○ 未见", "○ 未见", "◐ 密码与付款交回用户"],
    ["内存与资源", "模型内存记账", "○ 未公开", "○ Memory Limiter 不计 dma-buf / NPU 内存", "○ 未公开", "—"],
    ["", "与应用共存的回收", "◐ Jetsam + 内存压缩；以 12GB 作为准入门槛", "◐ LMKD + memcg；抢占只能卸载整个模型",
     "◐ ESWAP；HyperSpace Memory（厂商口径）", "— 资源独占"],
    ["", "KV 与前缀缓存", "○ 未公开", "◐ 前缀缓存按应用、按会话保存", "○ 未公开", "● 前缀缓存已商用并单独计价"],
    ["记忆（Agent 层）", "由谁持有", "Siri 个人上下文，基于系统语义索引", "Gemini 个人上下文", "小艺记忆", "dot、Grok Bot 各自持有"],
]
COV_GROUP = {0: "blue_l", 4: "green_l", 8: "purple_l", 11: "grey_l"}


@page
def coverage(prs):
    s = new_slide(prs, "业界在三项系统服务上的进展：", "模型托管已普及，长上下文、会话级权限判定与模型内存记账普遍缺失",
                  crumb=CRUMB + " › 业界进展")
    ratios = [0.6, 0.95, 1.2, 1.25, 1.15, 1.1]
    rows = [[r[0], r[1]] + [cell(c) for c in r[2:]] for r in COV_ROWS]
    fills = {}
    grp = None
    for i, r in enumerate(COV_ROWS):
        grp = COV_GROUP.get(i, grp)
        fills[(i + 1, 0)] = grp
        for j, c in enumerate(r[2:], 2):
            if c.strip()[:1] in _FILL:
                fills[(i + 1, j)] = _FILL[c.strip()[0]]
    ty = 92
    th = table_height(1216, COV_COLS, rows, ratios, style="detail", pad=(4, 1))
    table(s, (32, ty, 1216, th), COV_COLS, rows, widths=ratios, style="detail", pad=(4, 1), fills=fills,
          align=["center", "left", "left", "left", "left", "left"], fit=False)
    _symbol_sizes(s)
    cy = ty + th * 1.04 + 8
    if 686 - cy < 70:
        lib._warn(f"读表结论区过矮 {686 - cy:.0f}px")
    conclusion_band(s, cy, [
        ("推理服务", "模型托管已普及；长上下文、稀疏模型与 PIM 等新算力，除 Apple 的稀疏模型外都未进入端侧系统服务"),
        ("执行与沙箱", "接入方式收敛到函数接口加系统托管的 GUI；按会话、按调用的权限判定普遍缺失，只能整类禁止或逐次确认"),
        ("内存与资源", "模型内存不可见、不可记账；与应用共存只能靠卸载整个模型或终止进程"),
        ("记忆", "各家都随助手提供，印证「记忆在 Agent 层，系统只管读取权限」的划分"),
    ])
    footnote(s, LEGEND + "来源：报告 1.1.3。Computer Control 为 Android 开发者文档（2026-11-09 抓取）；HarmonyOS 的确认与阻断为媒体报道；"
                         "越权率为二手转述；PIM 进展见 R2 笔记。", y=694, w=1130)


# ---------------------------------------------------------------- 1.2.1 推理

@page
def trend_inference(prs):
    trend_page(prs, dict(
        crumb=CRUMB + " › 技术趋势 › 推理服务",
        title="推理服务技术趋势：", suffix="平台已做到模型级托管与抢占，会话级调度与跨应用 KV 复用仍为空白",
        stages=[
            ("2023–2024", "应用自带模型", "每个 App 打包一份权重和推理引擎；各自加载，内存随应用数量成倍增加"),
            ("2024–2026", "系统托管共享模型",
             "一个底座经适配器服务多个应用：AICore 托管 Gemini Nano；Apple Foundation Models；Phi Silica"),
            ("2026 起", "模型服务具备调度语义",
             "NPU Manager：加载准入、三档优先级、卸载式抢占；学术：LLMS 的 KV 分块换页，Agent.xpu 的算子级抢占"),
        ],
        columns=["要素", "Android AICore + NPU Manager", "Apple Foundation Models（含 AFM 3）", "Windows ML / Copilot+ 运行时",
                 "HarmonyOS 端侧大模型服务", "vLLM / SGLang", "LLMS", "Agent.xpu"],
        groups=[("量产端侧平台", 1, 4), ("云端参照", 5, 5), ("学术原型", 6, 7)],
        intro=["AICore 持有 Gemini Nano；Android 17 增 NPU Manager；量产",
               "Apple；系统模型实现 LanguageModel 协议，WWDC26 加入 AFM 3",
               "Microsoft；Windows ML 共享运行时，Phi Silica 预装于 NPU",
               "华为；小艺 + 意图框架，NNRt 为 NPU 北向接口；会议口径多",
               "开源云端推理引擎；连续批处理、PagedAttention、前缀缓存",
               "北大，2024；LLM 作移动系统服务，KV 分块压缩与换入换出",
               "北大，2025；NPU 与 iGPU 协同、细粒度抢占，面向 Agent"],
        rows=[
            ["系统级共享模型服务", "● 单底座多应用共享", "● App 共用系统模型，可换第三方实现", "● Phi Silica 预装，需 LAF 解锁",
             "◐ 小艺作底座；第三方 API、配额无文档", "● 一个服务进程服务多客户端（未核）", "● 提出 LLM 即系统服务",
             "○ 只做调度，不涉及服务形态"],
            ["多会话调度与优先级", "◐ 仅前台；并发返回忙不排队；NPU 三档优先级", "◐ 调度策略未披露", "○ 未见公开调度语义（未核）",
             "○ 并发依赖驱动，仅同步推理", "● 连续批处理、优先级调度（未核）", "◐ 以上下文切换为目标，细节未载",
             "● 区分 reactive 与 proactive 任务"],
            ["抢占粒度", "◐ 模型级：要求客户端卸载，任务可暂停", "○ 未披露", "○ 未见（未核）", "○ 未见",
             "◐ 请求级：换出或重算（未核）", "○ 只管上下文切换，不抢占算力", "● 算子级抢占，延迟降 ≥91%（自报）"],
            ["异构算力路由", "◐ NPU 内有准入；三类算力未统一", "◐ Core AI 在 ANE 与 GPU 间特化", "◐ EP 按设备选算力，非阶段级",
             "◐ NNRt 对接 NPU，无统一路由", "— GPU 集群", "○ 未涉及", "● NPU 与 iGPU 按负载划分"],
            ["前缀与 KV 复用、持久化", "◐ 前缀缓存存应用私有存储，不跨应用", "◐ 计 cached token；系统提示 KV 复用（未核）",
             "○ 未见（未核）", "○ 未见（待核）", "● 前缀缓存，跨请求共享（未核）", "● KV 跨调用持久，分块管理", "○ 未见（未核）"],
            ["多适配器驻留与热切换", "◐ 自训功能 LoRA，不开放第三方", "◐ 第三方适配器约 160MB，绑定底座版本",
             "◐ 第三方 LoRA，换底座须重训", "○ 未见（待核）", "● 多 LoRA 并发、运行时加载，限可信环境", "○ 未涉及",
             "○ 未涉及（未核）"],
            ["端云路由与隐私控制", "◐ Private AI Compute 承接重任务，细则未披露", "◐ 统一 API 含端侧与 PCC；PCC 有证明",
             "○ 未见系统级端云路由（未核）", "◐ OHTTP 匿名，无官方文档（媒体）", "— 纯云", "○ 未涉及", "○ 未涉及"],
            ["计量与配额", "◐ 电量配额，短长两窗口；NPU 归账字段", "◐ usage 含 cached token；无配额文档", "○ 未见（未核）",
             "○ 未见（待核）", "◐ token 级统计与限速，配额依部署（未核）", "○ 不涉及", "○ 不涉及"],
        ],
        conclusions=[
            ("已做成", "系统级共享底座：三大平台都已做到单底座多客户端；Android 与 Apple 提供会话内的前缀缓存接口"),
            ("普遍缺失", "跨应用的 KV 复用；适配器与底座版本解耦，底座一升级，第三方适配器就要重训"),
            ("只有云端或论文做成", "细粒度抢占、KV 持久化与分块换页、多适配器并发；产品侧最强的是 NPU Manager 的模型级卸载"),
            ("缺口最大的一行", "计量与配额：端侧没有公开的每 token 能耗计量，配额以电量命名，只有 Android 有迹可循"),
        ],
        source="来源：报告 1.2.1；逐格出处见 notes/P-C1。",
    ))


# ---------------------------------------------------------------- 1.2.2 沙箱

@page
def trend_sandbox(prs):
    trend_page(prs, dict(
        crumb=CRUMB + " › 技术趋势 › 执行沙箱",
        title="执行沙箱技术趋势：", suffix="隔离边界从 App 下移到会话，策略执行从 Agent 内部移到 Agent 之外",
        stages=[
            ("移动 OS 至今", "App 级沙箱", "UID 隔离、权限、entitlement，为「安装前可审查的代码包」设计；Android、iOS、HarmonyOS"),
            ("2024–2026", "会话级执行环境",
             "云端按会话起 microVM（E2B、Cube）；桌面用进程沙箱 + 出口代理；OpenShell 打包策略、代理与凭证注入"),
            ("学术前沿", "信息流控制", "从「隔离代码」走向「约束数据怎么流」：CaMeL、FIDES 给数据打能力标签并随值传播"),
        ],
        first_ratio=0.66,
        columns=["要素", "Android", "iOS", "HarmonyOS", "E2B / 腾讯 Cube", "NVIDIA OpenShell", "Claude Code / Codex",
                 "CaMeL", "IsolateGPT"],
        groups=[("量产移动 OS", 1, 3), ("云端与桌面", 4, 6), ("学术原型", 7, 8)],
        intro=["UID 沙箱；AVF / pKVM 提供 VM 级隔离",
               "App 沙箱 + 扩展；App Intents 意图入口",
               "应用沙箱 + 访问令牌（APL 三级）",
               "按会话起 microVM，池化 + 快照克隆",
               "2026-03 开源；YAML 策略 + 出口代理",
               "本机进程级沙箱 + 出口代理",
               "DeepMind 等，2025；双 LLM + 能力标签",
               "NDSS 2025；中枢调度 + 应用级隔离"],
        rows=[
            ["隔离粒度", "◐ App / 进程 / pVM", "◐ 仅 App 与扩展", "◐ App 级", "● 会话级 microVM", "● 沙箱实例级", "◐ 会话进程级",
             "◐ 数据值与工具调用", "● 应用级隔离"],
            ["隔离机制与强度", "● SELinux 等成熟；pVM 受机型限制", "● App 沙箱成熟", "◐ 应用沙箱 + APL；「动态沙箱」无出处",
             "● 硬件虚拟化", "◐ Landlock + seccomp", "◐ 进程级，无 VM；代理层有 CVE", "○ 无 OS 隔离，依赖解释器",
             "◐ 进程与应用隔离（未核）"],
            ["启动时延与内存开销", "◐ Microdroid 启动绝对值未取得", "— 无第三方沙箱实例", "— 无公开数据", "● 单并发 <60ms，P99 137ms",
             "○ 未给启动与内存数据", "◐ 近零开销（推断）", "◐ 两次 LLM 调用的时延与成本", "◐ 3/4 查询开销 <30%（自报）"],
            ["快照、暂停恢复与回滚", "○ 无会话快照与分叉原语", "○ 无", "○ 未找到公开资料", "● 快照克隆；暂停约 4s/GiB，恢复约 1s",
             "○ 文档未提快照", "○ 无内存快照，退出即销毁", "— 非运行时概念", "— 无"],
            ["可逆性（预演、撤销）", "○ AppFunctions 无预演与撤销", "◐ App Intents 称可撤销（转引，未核实）",
             "◐ 系统阻断转账支付，非通用分级", "◐ 快照可做机器级回滚", "○ 无", "◐ 敏感动作请求确认，无撤销", "○ 靠策略预先禁止",
             "○ 无"],
            ["策略表达与带外策略执行", "◐ 静态权限，单一权限放行调用方", "◐ 静态权限，意图逐次确认", "◐ APL 分档 + 系统阻断支付",
             "◐ 多无内置策略引擎", "● YAML 默认拒绝，网络段热更新", "◐ 按域名放行；策略文件曾可被改写", "● 解释器带外执行策略",
             "◐ 中枢管控应用间通信"],
            ["数据标签与信息流控制", "○ 无公开实现", "○ 无公开实现", "○ 无公开实现", "○ 无", "○ 无，按目的地管控", "○ 无",
             "● 能力标签随值传播", "○ 未见标签机制"],
            ["出口控制（含 DNS）", "○ 无按会话出口策略", "○ 无", "○ 未找到公开资料", "◐ Azure 默认禁出站；Cube（未核）",
             "● 沙箱内代理按目的地过滤", "◐ 域名白名单；DNS 为公认漏项", "— 不管网络", "— 未涉及"],
            ["凭证托管与代为请求", "◐ Keystore 不可导出，无出口注入", "◐ Keychain，同左", "◐ HUKS，同左（待核实）",
             "◐ 部分平台出口注入，E2B 未见", "● 网关注入，沙箱不持凭证", "● 凭证留宿主，代理附加令牌", "— 不涉及", "— 不涉及"],
            ["审计与可验证性", "◐ 系统日志", "◐ 同左", "◐ 工具调用对用户可见", "◐ 厂商日志", "◐ 拒绝记录；策略变更可验证", "◐ 权限提示日志",
             "● 计划与标签可审", "◐ 无形式化证明"],
        ],
        conclusions=[
            ("已做成", "会话级隔离、凭证不进沙箱：云端、OpenShell 与桌面沙箱都已做到"),
            ("所有产品都缺", "数据标签与信息流控制、预演与撤销；仅学术方案做到标签，任务完成率 77%（不设防基线 84%）"),
            ("只有云端做成", "快照、分叉、暂停恢复与亚百毫秒启动；手机三家都没有量产的会话快照原语"),
            ("移动 OS 的策略层", "静态权限加入口放行；按调用参数、按会话历史做有状态判定的，没有公开实现"),
        ],
        source="来源：报告 1.2.2；逐格出处见 notes/P-C2；Keystore / Keychain 两格为背景知识。",
    ))


# ---------------------------------------------------------------- 1.2.3 记忆

@page
def trend_memory(prs):
    trend_page(prs, dict(
        crumb=CRUMB + " › 技术趋势 › 记忆服务",
        title="记忆服务技术趋势：", suffix="从应用内功能走向系统级个人上下文，重心从检索转向治理",
        stages=[
            ("早期", "对话历史 + 向量检索", "检索增强（RAG）：有检索，没有写入策略"),
            ("2023–2025", "Agent 记忆框架",
             "MemGPT / Letta 虚拟上下文分层；Mem0 抽取式写入；Zep / Graphiti 双时间轴知识图谱；ChatGPT 显式记忆"),
            ("2025–2026", "系统级个人上下文",
             "Apple 语义索引 + App Intents 实体；Google Magic Cue 与 Gemini 个人上下文；小艺记忆；开源 OpenViking"),
        ],
        first_ratio=0.68,
        columns=["要素", "Apple 语义索引 / 个人上下文", "Google Magic Cue + Gemini", "HarmonyOS 小艺记忆",
                 "ChatGPT Memory", "Mem0", "Letta / MemGPT", "Zep / Graphiti", "OpenViking"],
        groups=[("系统厂商", 1, 3), ("商业助手与记忆框架", 4, 7), ("开源 demo", 8, 8)],
        intro=["iOS；App Intents 实体经 Core Spotlight 语义检索",
               "Magic Cue 端侧 Nano + 云增强；个人上下文读云账户",
               "华为；记忆主页存卡证、地址、订单",
               "OpenAI；云端；保存的记忆 + 聊天历史引用",
               "开源 / 云；LLM 抽取事实入向量库，2026-04 起只加不删",
               "源自 MemGPT；core 块 + archival，2026-02 改为 git 文件",
               "Zep AI；开源 Graphiti；双时间轴知识图谱",
               "火山引擎开源；目录范式 + 三级分层加载"],
        rows=[
            ["记忆分层", "○ 实体索引，未公开分层", "◐ 个人上下文 + 过往聊天", "◐ 按卡证、地址、订单分类", "◐ 显式记忆 + 历史引用",
             "◐ 按作用域，非时间层", "◐ 工作 + 外存两层", "◐ 情景、实体、社区三层", "● 六类记忆，分层加载"],
            ["自动抽取、去重、冲突更新", "○ 应用主动提供，无抽取", "◐ 自动记忆；冲突处理未公开", "◐ 自动记兴趣、职业；去重未公开",
             "◐ 模型判定 + 用户指令", "◐ 只加不删，冲突留给检索", "◐ Agent 自写；子 Agent 靠 git 合并", "◐ 时间边失效旧事实；多跳冲突弱",
             "◐ 会话末抽取；去重待核实"],
            ["检索方式与基准成绩", "◐ 词法 + 语义；无基准", "○ 机制与基准均未公开", "◐ 向量 + 倒排 + 重排；无基准", "○ 不公开；无基准",
             "◐ 向量可选图；LoCoMo 92.5（自报）", "◐ 文件工具；LoCoMo 74.0（自测）", "◐ 图检索；LoCoMo 58–84（有争议）",
             "◐ 向量定位；LoCoMo 80–83（自评）"],
            ["遗忘与生命周期", "○ 未公开", "◐ 用户可管理；细节未公开", "◐ 主页可管理；删除待核实", "◐ 可删；关历史后 30 天内清除",
             "○ 新算法只加不删", "◐ 块可编辑删除；摘要压缩", "◐ 时间边失效，非物理删除", "○ 未见遗忘或 TTL 说明"],
            ["来源与完整性标签、写入治理", "◐ 实体来源明确；无完整性标签", "○ 未公开；注入已被演示", "○ 未找到公开资料", "○ 记忆注入已被演示",
             "○ 无溯源字段", "◐ git 提交留痕；无完整性标签", "◐ 情景子图可回溯原文（推断）", "◐ 检索轨迹留痕；无完整性标签"],
            ["端侧运行（存储、索引、功耗）", "◐ 端侧索引；体积功耗未公开", "◐ Nano 在端侧；个人上下文在云", "◐ 端云协同；存储位置待核实",
             "○ 纯云端", "○ 抽取需 LLM；无端侧数据", "◐ 可迁移（判断）；无实测", "○ 构图依赖 LLM；内存未知", "○ 服务端数据库，需裁剪"],
            ["系统级跨 App 索引", "◐ 跨 App 实体；读取限系统", "◐ 限 Google 自家应用", "◐ 有系统记忆，无跨应用索引", "— 应用内记忆",
             "— 框架，非 OS 层", "— 框架，非 OS 层", "— 框架，非 OS 层", "— 框架，非 OS 层"],
            ["第三方授权与访问控制", "◐ 应用声明实体；读取侧未公开", "◐ 应用级连接，默认关闭", "◐ 数据通路无语义层（转引）",
             "○ 账户级，无第三方细粒度", "◐ 标识过滤，无读写 ACL", "◐ 共享块整块只读", "○ 未找到公开资料", "◐ 目录作用域 + 多租户"],
            ["用户可见、可编辑、可删除", "○ 未找到公开说明", "◐ 可管理可导入；来源追溯弱", "◐ 主页可见；编辑删除待核实",
             "● 条目可见可删；删聊天不删记忆", "◐ 仅 API 层（推断）", "● 块与 git 文件可读可改", "◐ 图可检视；删除要清关联边",
             "◐ 目录可检视；删除语义待核实"],
        ],
        conclusions=[
            ("已做成", "抽取式写入（Mem0、OpenViking 等）；条目级可见可删（ChatGPT Memory、Letta）"),
            ("普遍缺失", "来源与完整性标签、遗忘、第三方授权；来源标签无一家达到「已具备」，授权最细只到应用级连接或整块只读"),
            ("共同短板", "检索基准口径混乱，同一系统在 LoCoMo 上有 58–84 多种说法；多跳冲突题所有方法不超过约 !!7%!!"),
            ("端侧只有索引", "抽取、图谱、分层依赖常驻 LLM，都在云端或服务端；系统级跨 App 索引不向第三方 Agent 开放读取"),
        ],
        source="来源：报告 1.2.3；逐格出处见 notes/P-C3；多跳冲突数据来自 MemoryAgentBench。",
    ))


# ---------------------------------------------------------------- 1.2.4 内存管理

@page
def trend_memory_mgmt(prs):
    trend_page(prs, dict(
        crumb=CRUMB + " › 技术趋势 › 内存管理",
        title="内存管理技术趋势：", suffix="模型内存成为按请求换入的工作集，OS 的记账仍停留在匿名页",
        stages=[
            ("传统", "为 App 设计的回收", "Android LMKD 按优先级终止进程；iOS Jetsam；zRAM 与内存压缩；MGLRU"),
            ("2025–2026", "配额化",
             "Memory Limiter 默认每进程限额，只计匿名页与 swap；Linux dmem 合入 6.14，dma-buf 计费仍为 RFC"),
            ("2023 起", "模型内存的分层管理",
             "云端 PagedAttention 分块管理 KV；AFM 3 权重放 NAND、按请求换入（量产）；Gemma 3n PLE；LLMS 等"),
        ],
        first_ratio=0.68,
        columns=["要素", "Android", "iOS", "HarmonyOS / OpenHarmony",
                 "Linux 主线", "Apple AFM 3 运行时", "vLLM PagedAttention", "LLMS", "PowerInfer-2"],
        groups=[("量产 OS 与内核", 1, 4), ("模型运行时与云端参照", 5, 6), ("学术原型", 7, 8)],
        intro=["LMKD + memcg；Memory Limiter 节流优先于终止进程",
               "Jetsam 按优先级带与进程上限回收；内存压缩",
               "应用自愿释放回调、Purgeable；OH 有 zswapd 换出",
               "MGLRU；dmem 6.14 合入；dma-buf 计费 RFC（2026-05）",
               "WWDC26；20B 稀疏，全量存 NAND，每请求激活 1–4B",
               "UC Berkeley 等，2023；KV 分块与前缀共享",
               "2024-03；LLM 作系统服务，分块 KV 压缩换出",
               "上交 IPADS，2024-06；神经元簇 + 闪存 IO 流水"],
        rows=[
            ["模型内存可见性与记账", "◐ 计匿名页与 swap；dma-buf 未说明", "○ footprint 口径（未核实）", "○ 无公开资料",
             "◐ dmem 不适用手机；dma-buf 计费 RFC", "○ 官方页未述内存归属", "● 引擎自管块池，预算内可见", "● 与 App 内存分开管理",
             "— 单应用运行时"],
            ["共享服务的代分配归账", "○ 按进程单一属主；pidfd 计费仅 RFC", "○ 无公开资料", "○ 无公开资料", "◐ RFC 计到客户端 cgroup，未合入",
             "○ 守护进程归属未说明", "— 单租户引擎", "◐ 服务内统一管理，无跨进程归账", "—"],
            ["KV cache 管理", "○ 无 KV 语义，仅匿名页与 dma-buf", "○ 系统层无公开机制", "○ 无公开资料",
             "— 内核无 KV 语义", "◐ 2025 模型 KV 降 37.5%；AFM 3 未述", "● 分页 + 前缀共享", "● 分块压缩、换出、IO 与重算流水",
             "— 聚焦权重，不管 KV"],
            ["权重分层与按需换入", "◐ mmap 文件页可回收；PLE 默认状态待核", "◐ 仅平台模型走 AFM 3", "○ 无公开资料",
             "◐ 缺页、页缓存可用，无模型语义", "● 全量存 NAND，请求级专家换入", "— 权重常驻显存", "— 只管 KV",
             "● 按需读闪存，47B 达 11.68 tok/s"],
            ["与应用内存的统一回收与 QoS", "◐ 可见 / 不可见分档，有上限无保底", "◐ 优先级带 + 上限，不区分模型内存",
             "◐ 合作式回调；OH 有 per-memcg 参数", "◐ min / low / high 具备，手机无保护契约", "○ 与应用的仲裁无公开资料", "— 无应用内存可争",
             "◐ 上下文内存独立管理", "○ 运行时自管"],
            ["冷热识别", "◐ 荣耀约 7000 万台用 MGLRU", "○ 无公开资料", "◐ OH 有 score、refault 参数（未核）",
             "◐ MGLRU 仍有争论；无硬件采样", "◐ prefill 选定专家集，低频重选", "◐ 块级引用与淘汰", "● 按压缩容忍度 + 最近使用淘汰",
             "◐ 神经元冷热分区，细节待核"],
            ["压缩交换", "● zRAM，swap.max 封顶", "◐ 有内存压缩，细节待核", "◐ ESwap 加密换出，商用待核",
             "● zram / zswap，含写回开关", "— 模型不走交换", "—", "◐ 压缩对象是 KV 块", "—"],
            ["模型加载 IO 与零拷贝", "◐ dma-buf fd 共享，QNN 仅收 DMA-BUF", "○ 无公开资料", "○ 无公开资料",
             "◐ dma-buf、mmap 在，无模型加载接口", "◐ NAND 到 DRAM 换入，细节未公开", "— 云端不敏感", "—", "● 大块对齐读 + IO 流水"],
        ],
        conclusions=[
            ("已做成的只有匿名页层", "压缩交换、memcg 配额、MGLRU 类回收，对模型内存没有语义"),
            ("商业 OS 与内核普遍缺失", "模型内存统一记账（dma-buf、GPU、NPU 在限额之外）、共享服务代分配归账、OS 层的 KV 管理"),
            ("KV 分块、压缩、换出", "只在云端引擎与学术原型中做成；LLMS 自报上下文切换时延最多降低两个数量级"),
            ("权重分层的端侧先例", "AFM 3 请求级专家驻留、Gemma 3n PLE；都避开逐 token 随机读，因手机闪存小块随机读带宽是瓶颈"),
        ],
        source="来源：报告 1.2.4；逐格出处见 notes/P-C4。",
    ))

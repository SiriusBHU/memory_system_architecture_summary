"""单页材料（独立成册，不进 v2 主 deck）：
- S1 云转端仿真评估：版式一（上：目标；左：问题；右：方案架构，右下：关键技术）。
  理由：S1 的核心产出是一个平台（输入、分层仿真、决策模型、校准闭环），架构需要大面积。
- S2 Agent OS 并行化寻优：版式二（上：目标；左上：问题；左下：方案架构；右：关键技术）。
  理由：S2 的价值在寻优方法本身，关键技术要逐项展开；架构是一条离线寻优 + 在线执行的流水线，左下即可容纳。

构建：
  cd /d/projects/ppt_templates && uv run python <本目录>/build.py --modules p6_onepager \
      --out <目录>/2027立项-单页-云转端仿真评估与AgentOS并行化寻优.pptx --preview --preview-dir <本目录>/preview-onepager
"""

from lib import arrow, box, card, footnote, measure, new_slide, num_badge, poly_arrow, table, text, text_em
from registry import page

GOAL_Y, GOAL_H = 80, 80
BODY_Y, BODY_B = 170, 676


def goal_band(s, main, items):
    """标题下方的目标带：左侧「目标」标签，一句总目标 + 分点量化目标。"""
    y, h = GOAL_Y, GOAL_H
    card(s, (32, y, 1216, h))
    box(s, (32, y, 56, h), "目标", fill="primary", color="on_primary", style="emphasis")
    text(s, (100, y + 8, 1136, 22), main, style="emphasis")
    gap = 14
    w = (1136 - gap * (len(items) - 1)) / len(items)
    for i, md in enumerate(items):
        x = 100 + i * (w + gap)
        num_badge(s, x, y + 40, i + 1, d=18)
        text(s, (x + 24, y + 37, w - 24, h - 41), md, style="body")


def stack(s, x, y, w, items, style="detail", gap=6):
    """按实际行数依次排布的编号要点，返回结束的 y。"""
    for i, md in enumerate(items, 1):
        h = measure(md, w - 26, style)
        num_badge(s, x, y + 1, i, d=18)
        text(s, (x + 26, y, w - 26, h + 2), md, style=style)
        y += h + gap
    return y


def lane(s, b, name):
    box(s, b, name, fill="primary", color="on_primary", style="body_strong", inset=2)


# ====================================================================== S1 云转端仿真评估（版式一）

@page
def s1_onepager(prs):
    s = new_slide(prs, "S1 云转端仿真评估", "下沉决策的统一口径与手机侧仿真平台")
    goal_band(s, "建成手机侧 Agent 仿真评估平台，以统一口径回答「哪些步骤值得下沉、代价多大」，作为 KT1–KT3 与 S2 的共同评估基线",
              ["**仿真精度**：时延误差 !!≤10%!!，功耗误差 !!≤15%!!",
               "**评估效率**：单配置评估 !!≤10 分钟!!，替代数小时的真机逐测",
               "**决策覆盖**：!!≥6 类!!典型任务给出下沉建议与决策翻转点",
               "**共同基线**：统一负载集与指标集，供 S2 与 KT1–KT3 共用"])

    # ---------------- 左：问题
    lx, lw = 32, 508
    card(s, (lx, BODY_Y, lw, BODY_B - BODY_Y))
    ix, iw = lx + 14, lw - 28
    text(s, (ix, BODY_Y + 8, iw, 22), "@@问题@@：「下沉值不值」今天算不清", style="emphasis")
    text(s, (ix, BODY_Y + 33, iw, 18), "**云端与端侧的代价对照**（单个 10 步 Agent 任务，估算）", style="detail")
    rows = [
        ["成本", "单任务约 !!$0.007!!；规模化约 $12.8 亿 / 年", "无 token 费，占 DRAM 与电量", "可比"],
        ["能耗", "约 0.24 Wh / 次，不含网络与终端", "约 0.28 Wh / 任务（≈1.5% 电量）；能效约差 3 倍",
         "!!不可比!!"],
        ["时延", "网络 RTT + 排队", "DVFS、热降频、带宽争抢", "需仿真"],
        ["内存与体验", "不占端侧内存", "权重 + KV 挤压前台：冷启动变慢、进程被杀", "!!无法换算!!"],
        ["隐私与离线", "数据出域；断网不可用", "数据不出域；可离线", "分级处理"],
    ]
    ty, th = BODY_Y + 52, 212
    table(s, (ix, ty, iw, th), ["维度", "云侧", "端侧", "同口径？"], rows, widths=[1.15, 2.0, 2.6, 0.95],
          style="caption", header_style="caption")
    gaps = [
        "**口径不统一**：ODPM 分轨功耗仅部分机型可用，整机电流拆不到 Agent 步骤；云侧能耗是全栈摊销，两边无法直接相减。",
        "**没有手机侧仿真器**：Vidur（误差 <9%）、LLMServingSim 2.0（0.95%）等均面向 GPU / TPU；手机的 DVFS、"
        "热降频、共享带宽、UFS 抖动无公开模型，每个配置只能真机逐测，一轮数小时。",
        "**体验风险无法换算**：常驻多少 GB 对应冷启动劣化多少、回收多少进程，缺少方法；Agent 体验指标无公开定义，"
        "KT1–KT3 的收益只能各自自测、口径不一。",
    ]
    stack(s, ix, ty + th + 10, iw, gaps, style="detail", gap=5)
    concl = ("**判断**：端侧并不天然省电。下沉的收益在隐私、离线、时延确定性与规模化云账单，代价在耗电、内存与发热，"
             "必须以统一口径量化，而不能凭经验决策。")
    ch = measure(concl, iw - 16, "detail") + 14
    box(s, (ix, BODY_B - 12 - ch, iw, ch), concl, fill="highlight", style="detail", align="left", inset=8)

    # ---------------- 右上：方案架构
    rx, rw = 552, 696
    a_bottom = 478
    card(s, (rx, BODY_Y, rw, a_bottom - BODY_Y))
    text(s, (rx + 14, BODY_Y + 8, rw - 28, 22), "@@方案架构@@：真机基线 + 手机 SoC 分层仿真 + 红线约束的决策模型", style="emphasis")
    LX, LW = rx + 14, 40
    cx0 = LX + LW + 8
    cw = 1206 - cx0
    A, B, C, D = (204, 56), (274, 82), (370, 58), (442, 28)

    # 输入
    lane(s, (LX, A[0], LW, A[1]), "输入")
    w3 = (cw - 16) / 3
    inputs = ["**标准负载集**：模型层 MLPerf Mobile LLM 子集；Agent 轨迹参数化回放；叠加 3–5 个应用",
              "**真机基线**：Perfetto 电池计数器 + ODPM，隔离供电；时延、功耗、温度、lmkd 事件",
              "**云侧口径**：价格表（含缓存折扣，注明日期）；网络 RTT 与抖动；云能耗公开口径"]
    in_labels = ["负载", "标定 / 回归", "价格 / RTT"]
    for i, md in enumerate(inputs):
        x = cx0 + i * (w3 + 8)
        box(s, (x, A[0], w3, A[1]), md, fill="surface", style="caption", align="left", inset=5)
        mx = x + w3 / 2
        arrow(s, (mx, A[0] + A[1]), (mx, B[0]), color="accent", width=1.25)
        text(s, (mx + 5, A[0] + A[1], 90, 14), in_labels[i], style="caption", check=False)

    # 分层仿真（新建，核心）
    lane(s, (LX, B[0], LW, B[1]), "仿真")
    box(s, (cx0, B[0], cw, B[1]), "", fill="highlight", line="highlight_strong", check=False)
    text(s, (cx0 + 8, B[0] + 3, cw - 16, 16),
         "**手机 SoC 分层仿真**（新建；候选底座 LLMServingSim 2.0，复用其调度与合批框架）", style="detail")
    lw3 = (cw - 16 - 16) / 3
    layers = ["**算子层**：峰值算力与有效带宽由微基准标定（参照 CPU 43.9 / NPU 56 GB/s）",
              "**系统层**：带宽争抢、UFS 换入换出、内存压力（接入 KT1–KT3 状态）",
              "**热与 DVFS 层**：阶段 × 频点功耗模型；≥10 分钟长时序热累积"]
    for i, md in enumerate(layers):
        box(s, (cx0 + 8 + i * (lw3 + 8), B[0] + 21, lw3, 55), md, fill="bg", style="caption", align="left", inset=5)
    mid = cx0 + cw * 0.64
    arrow(s, (mid, B[0] + B[1]), (mid, C[0]), color="accent", width=1.25)
    text(s, (cx0, B[0] + B[1], mid - 6 - cx0, 14), "按 Agent 步骤 × 阶段（prefill / decode / 空闲 / 网络）",
         style="caption", align="right", check=False)
    text(s, (mid + 6, B[0] + B[1], 1206 - mid - 6, 14), "输出时延 · 能耗 · 内存 · 温度", style="caption", check=False)

    # 决策
    lane(s, (LX, C[0], LW, C[1]), "决策")
    cws = [(cw - 16) * r for r in (0.42, 0.29, 0.29)]
    dec = ["**净收益**：NB = ΔCost + λP·ΔPrivacy − λE·ΔEnergy − λM·ΔMem − λT·ΔLat − λR·ΔRisk",
           "**硬约束（一票否决）**：体验红线 · 隐私等级 · 质量下限",
           "**灵敏度扫描**：成本 / 体验 / 隐私三档权重 → 决策翻转点"]
    x = cx0
    for wdt, md in zip(cws, dec):
        box(s, (x, C[0], wdt, C[1]), md, fill="surface", style="caption", align="left", inset=5)
        x += wdt + 8

    # 输出
    lane(s, (LX, D[0], LW, D[1]), "输出")
    outs = ["**下沉建议**：留云 / 下沉 / 混合",
            "**在线路由**：沿用同一决策函数",
            "**评估服务**：S2、KT1–KT3 调用"]
    for i, md in enumerate(outs):
        x = cx0 + i * (w3 + 8)
        arrow(s, (x + w3 / 2, C[0] + C[1]), (x + w3 / 2, D[0]), color="accent", width=1.25)
        box(s, (x, D[0], w3, D[1]), md, fill="bg", line="primary", style="caption", inset=4)

    # 偏差回灌闭环
    fx = 1226
    poly_arrow(s, [(1206, D[0] + D[1] / 2), (fx, D[0] + D[1] / 2), (fx, B[0] + B[1] / 2), (1206, B[0] + B[1] / 2)],
               color="accent", width=1.25)
    box(s, (fx - 9, 352, 18, 66), "偏差回灌", fill="bg", style="caption", inset=0, check=False)

    # ---------------- 右下：关键技术
    ky = a_bottom + 10
    kh = BODY_B - ky
    lane(s, (rx, ky, 36, kh), "关键技术")
    kx0 = rx + 36 + 8
    kw = (1248 - kx0 - 10) / 2
    kch = (kh - 8) / 2
    kts = ["@@统一能耗记账@@：端侧按 prefill / decode / 空闲 / 网络射频分阶段建模并用电池计数器校准；"
           "云侧取公开口径并注明边界；记账单位由整机下沉到 Agent 步骤",
           "@@分层校准闭环@@：算子微基准 → 标准负载回归 → 热与 DVFS 长时序；叠加场景单独校准，"
           "避免空载校准偏乐观；每次平台升级发布误差带",
           "@@红线约束决策@@：体验红线、隐私等级、质量下限一票否决；三档权重灵敏度扫描，"
           "输出「云价格或端侧能效变化到多少应下沉」的翻转点，云价格调整时重算",
           "@@内存—体验换算@@：模型常驻 GB × 驻留时长换算为前台冷启动劣化与每小时被回收进程数，"
           "与 KT1–KT3 联动，使占内存成为可与云成本比较的代价"]
    for i, md in enumerate(kts):
        r, c = divmod(i, 2)
        x, y = kx0 + c * (kw + 10), ky + r * (kch + 8)
        card(s, (x, y, kw, kch))
        num_badge(s, x + 10, y + 9, i + 1, d=18)
        text(s, (x + 34, y + 6, kw - 44, kch - 10), md, style="detail", gap_pt=2)

    footnote(s, "注：成本按 Gemini 3.1 Flash-Lite（2026-11-03 价格）、10 步任务约 2 万输入 / 1500 输出 token 估算，规模化按 1 亿日活 × 每天 5 次；"
                "0.28 Wh 按 llama.cpp 基线 0.672 J/token 估算，未计 prefill；能效约差 3 倍见 arXiv 2609.11940（预印本）。"
                "目标依据：时延指首 token 与每 token 时延，在 3 机型 × 3 模型规模上验收，误差对标 Vidur <9%、LLMServingSim 2.0 0.95%（均为 GPU 场景）；功耗 ≤15% 无公开先例，为目标假设；≤10 分钟对标 LLMServingSim 2.0。",
             y=682, h=30)


# ====================================================================== S2 Agent OS 并行化寻优（版式二）

SEG = {"gen": dict(fill="highlight_blue"),
       "ro": dict(fill="surface"),
       "fx": dict(fill="highlight", line="highlight_strong"),
       "rb": dict(fill="surface", line="muted", dash=True)}


def seg(s, x, y, w, h, label, kind):
    box(s, (x, y, w - 2, h), label, style="caption", inset=0, check=False, **SEG[kind])


@page
def s2_onepager(prs):
    s = new_slide(prs, "S2 Agent OS 并行化寻优", "单 Agent 任务内的并行方案搜索与安全执行")
    goal_band(s, "在单个 Agent 任务内自动搜索并行执行方案，经 S1 仿真验证后固化为策略模板，在副作用可控的前提下兑现并行收益",
              ["**时延**：多工具任务端到端时延 !!-20%～-40%!!（相对串行）",
               "**投机**：投机命中率 !!≥50%!!（云上参照最高 55%）",
               "**能耗**：时延下降的同时，能耗增量 !!≤+10%!!",
               "**安全**：投机结果确认前不落地，有副作用工具越权执行 !!0 次!!"])

    lx, lw = 32, 636
    ix, iw = lx + 14, lw - 28

    # ---------------- 左上：问题
    py, ph = BODY_Y, 310
    card(s, (lx, py, lw, ph))
    text(s, (ix, py + 8, iw, 22), "@@问题@@：串行执行把等待逐项叠加，端侧并行又不能照搬云", style="emphasis")
    # 示意甘特：「订明天去上海的高铁并加到日历」
    bx = ix + 86
    bar_w = ix + iw - bx
    serial = [("生成", "gen", 1), ("查车次", "ro", 1.2), ("生成", "gen", 1), ("查日历", "ro", 1.2), ("生成", "gen", 1),
              ("下单", "fx", 1.2), ("生成", "gen", 1), ("写日历", "rb", 1.2), ("生成", "gen", 1)]
    unit = bar_w / sum(d for _, _, d in serial)
    sy, sh = py + 38, 22
    text(s, (ix, sy, 84, sh), "**现状：串行**", style="detail", valign="middle")
    x = bx
    for label, kind, d in serial:
        seg(s, x, sy, d * unit, sh, label, kind)
        x += d * unit
    pyy, phh = sy + sh + 8, 34
    text(s, (ix, pyy, 84, phh), "**寻优后**", style="detail", valign="middle")
    par = [[("生成", "gen", 1)], [("查车次", "ro", 1.2), ("查日历", "ro", 1.2)], [("生成", "gen", 1)],
           [("下单", "fx", 1.2)], [("生成", "gen", 1), ("写日历", "rb", 1.2)]]
    x = bx
    for grp in par:
        gw = max(d for _, _, d in grp) * unit
        if len(grp) == 1:
            label, kind, d = grp[0]
            seg(s, x, pyy, d * unit, phh, label, kind)
        else:
            for k, (label, kind, d) in enumerate(grp):
                seg(s, x, pyy + k * 18, d * unit, 16, label, kind)
        x += gw
    end_x = x
    text(s, (end_x + 8, pyy, bx + bar_w - end_x - 8, 16), "!!等待被并行与投机隐藏!!（示意）", style="caption", align="center",
         check=False)
    arrow(s, (end_x + 6, pyy + 24), (bx + bar_w, pyy + 24), color="accent", width=1.25, both=True, dash=True)
    # 图例
    lgy = pyy + phh + 8
    lx2 = bx
    for label, kind in [("模型生成", "gen"), ("只读工具：可并行", "ro"), ("有副作用：需确认，串行", "fx"),
                        ("可回滚：可投机", "rb")]:
        box(s, (lx2, lgy + 3, 14, 10), "", check=False, **SEG[kind])
        tw = text_em(label) * 12 + 8
        text(s, (lx2 + 18, lgy, tw, 16), label, style="caption", check=False)
        lx2 += 18 + tw + 12
    ev_y = lgy + 22
    evidence = (
        "**云上收益已验证**：LLMCompiler（ICML 2024）并行函数调用，时延最高快 !!3.7 倍!!；PASTE（2026）"
        "工具执行与生成交叠，任务完成时间 !!-43.5%!!；Speculative Actions 预测下一动作，命中率最高 55%。\n"
        "**端侧不能照搬的三项约束**：\n"
        "- **副作用**：发短信、设闹钟、拉起应用需权限与用户确认；云上方案默认工具无副作用\n"
        "- **共享带宽**：decode 受带宽限制，CPU+NPU 并用约 59.6 GB/s，仅比 NPU 单用高约 !!6%!!\n"
        "- **KV 与内存**：合批与多路投机增加 KV 占用，受 KT2-B 的 KV 配额制约\n"
        "**组合空间大、收益非单调**：5 类并行手段 × 并行度 / 批大小 × 背景负载；越过带宽拐点后时延与能耗反而恶化，"
        "需要搜索寻优，而非固定规则。")
    text(s, (ix, ev_y, iw, py + ph - 10 - ev_y), evidence, style="detail", gap_pt=3)

    # ---------------- 左下：方案架构
    ay = py + ph + 10
    card(s, (lx, ay, lw, BODY_B - ay))
    text(s, (ix, ay + 7, iw, 20), "@@方案架构@@：离线寻优产出策略模板，在线安全执行并回灌", style="emphasis")
    LW = 40
    cx0 = ix + LW + 8
    cw = ix + iw - cx0
    sg = 18
    sw = (cw - 3 * sg) / 4
    off_y, lane_h = ay + 34, 62
    on_y = off_y + lane_h + 18
    lane(s, (ix, off_y, LW, lane_h), "离线寻优")
    lane(s, (ix, on_y, LW, lane_h), "在线执行")
    offline = [("**轨迹 → 依赖图**\n数据 / 顺序依赖 + 工具语义标签", "surface", None),
               ("**候选计划生成**\n5 类并行手段 × 并行度 / 批大小", "surface", None),
               ("**S1 仿真评估**\n时延 · 能耗 · 内存（≤10 分钟）", "highlight_blue", None),
               ("**帕累托筛选**\n定并行度上限，固化策略模板", "surface", None)]
    online = [("**反馈回灌**\n命中率 · 回滚率 · 仿真偏差", "surface", None),
              ("**运行时调度**\n工具并发 · 投机隔离 · 合批 · 异构流水", "surface", None),
              ("**安全闸门**\n校验标签；有副作用工具待确认", "highlight", "highlight_strong"),
              ("**任务匹配**\n按任务类型取模板，无则串行", "surface", None)]
    xs = [cx0 + i * (sw + sg) for i in range(4)]
    for i, (md, fill, line) in enumerate(offline):
        box(s, (xs[i], off_y, sw, lane_h), md, fill=fill, line=line, style="caption", inset=4)
        if i < 3:
            arrow(s, (xs[i] + sw, off_y + lane_h / 2), (xs[i + 1], off_y + lane_h / 2), color="accent", width=1.25)
    for i, (md, fill, line) in enumerate(online):
        box(s, (xs[i], on_y, sw, lane_h), md, fill=fill, line=line, style="caption", inset=4)
        if i < 3:
            arrow(s, (xs[i + 1], on_y + lane_h / 2), (xs[i] + sw, on_y + lane_h / 2), color="accent", width=1.25)
    # 模板下发（右侧向下）与回灌（左侧向上）
    arrow(s, (xs[3] + sw / 2, off_y + lane_h), (xs[3] + sw / 2, on_y), color="accent", width=1.25)
    text(s, (xs[3] + sw / 2 + 6, off_y + lane_h + 1, 90, 16), "模板下发", style="caption", check=False)
    arrow(s, (xs[0] + sw / 2, on_y), (xs[0] + sw / 2, off_y + lane_h), color="accent", width=1.25)
    text(s, (xs[0] + sw / 2 + 6, off_y + lane_h + 1, 120, 16), "轨迹与偏差回灌", style="caption", check=False)

    # ---------------- 右：关键技术
    rx, rw = 680, 568
    n = 4
    kg = 8
    kh = (BODY_B - BODY_Y - kg * (n - 1)) / n
    kts = [
        ("工具语义标签与并行许可", "由工具元数据决定能否并行",
         "手机工具多数有副作用或需权限，云上方案默认工具无副作用。",
         "在 App Intents / AppFunctions 式函数声明上扩展五类标签（只读 / 幂等 / 可回滚 / 有副作用 / 需确认），"
         "只对前三类开放并行与投机；标签缺失按「有副作用」处理，由系统而非模型临场判断。"),
        ("依赖图抽取与候选计划生成", "把临场并行变成可验证的计划",
         "依赖关系隐含在对话与参数传递中，规划出错会导致执行错序。",
         "从历史轨迹抽取数据依赖（参数取自前序工具输出）与顺序依赖（前台状态、权限弹窗），构建任务 DAG；"
         "在 DAG 上枚举并行调用、子任务拆分、投机执行、合批 / 投机解码、异构流水五类手段的组合。"),
        ("仿真驱动的多目标寻优", "带宽感知的并行度上限",
         "组合空间大，真机逐个验证不可行；收益受共享带宽与背景负载影响，非单调。",
         "调用 S1 仿真平台评估时延、能耗、内存，筛出帕累托前沿；扫描「并行度 × 批大小 × 背景流量」找到收益拐点并设上限，"
         "与 KT2-B 的 KV 配额联动；结果按任务类型固化为策略模板。"),
        ("投机执行的隔离与回滚", "投机失败对用户不可见",
         "投机命中率上限约 55%，未命中的结果若落地，会产生错误副作用或越权读取敏感数据。",
         "投机结果写入隔离区，模型确认后才提交（参照 PASTE 的结果隔离）；可回滚工具登记补偿操作；"
         "命中率或回滚率越线时在线降级为串行。"),
    ]
    for i, (title, key, hard, how) in enumerate(kts):
        y = BODY_Y + i * (kh + kg)
        card(s, (rx, y, rw, kh))
        num_badge(s, rx + 12, y + 10, i + 1, d=20)
        text(s, (rx + 40, y + 8, rw - 300, 22), f"@@{title}@@", style="emphasis")
        box(s, (rx + rw - 262, y + 9, 250, 22), f"突破：{key}", fill="highlight_blue", style="caption", inset=3)
        text(s, (rx + 14, y + 38, rw - 28, kh - 44), f"**难点**：{hard}\n**做法**：{how}", style="detail", gap_pt=3)

    footnote(s, "注：目标均为建议区间。时延 -20%～-40% 依据云上 Speculative Actions 最高 -20%、PASTE -43.5%，端侧按带宽约束折减；"
                "命中率 ≥50% 参照 Speculative Actions 最高 55%；能耗 ≤+10% 为目标假设，由 S1 功耗模型验证。"
                "59.6 / 56 GB/s 为 PowerInfer-2 在 OnePlus 12 上的实测；PASTE 不同版本数字不一（43.5% / 48.5%），以 v3 为准。甘特图为示意，非实测。",
             y=682, h=30)

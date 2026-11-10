# -*- coding: utf-8 -*-
"""PC 端侧大模型架构构想 · 汇报版。主线：负载 → 性能 → 功耗 → 成本。数字全部来自 calc_pc。

本方案拆成三种自洽配置（复用主硬盘 / 改造型闪存 / 堆叠型闪存），每种配置的首字、电量、成本互相对应。
"""
import math
from pptx.util import Inches as I
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import calc_pc as p
import pptkit as k

P, H = p.P, p.H
B30, B60, B117 = p.GEARS
PARTS = ("负载", "性能", "功耗", "成本")
STEP = {"负载": 0, "架构": 0.5, "性能": 1, "功耗": 2, "闪存": 2.5, "成本": 3}
CFG = p.CONFIGS
KEYS = ("shared", "A2", "C")
SRC_CALC = "测算：calc_pc.py；公式与参数见附录"
SRC_COST = "调研：sources/pc-cost-logic-pim.md、pc-cost-custom-nand.md、pc-cost-memory-prices.md（见附录「出处」）"

# ---- 常用数字 ----
E_STREAM = P['w_moe'] * H['e_hbf']                         # 每轮读权重 50 焦（UFS 参考值）
REF05, REF10 = p.day_energy(0.5), p.day_energy(1.0)
RES_DAY = p.resident_day_energy()
BAT_LO, BAT_HI = H['battery_j']
T_DEC = 300 / p.pim_tok_s()
COST_N = {key: p.cfg_cost(key, 'n') for key in KEYS}
COST_H = {key: p.cfg_cost(key, 'h') for key in KEYS}
DAYS = {key: p.cfg_day(key) for key in KEYS}
RES_N, RES_H = p.cost_resident_total('n'), p.cost_resident_total('h')
LO_N, HI_N = COST_N['shared'][1], COST_N['C'][1]
LO_H, HI_H = COST_H['shared'][1], COST_H['C'][1]
TT_SH = p.cfg_ttft('shared')[0]
TT_C = p.cfg_ttft('C')                                     # (电池, 插电)


def Y(usd):
    return f"¥{p.yuan(usd):,}"


def R100(usd):
    return f"¥{round(p.yuan(usd), -2):,}"


def pct(e_lo, e_hi):
    """电量区间 → 电池占比区间（低值用大电池，高值用小电池）。"""
    return e_lo / BAT_HI, e_hi / BAT_LO


def pct_s(e_lo, e_hi, nd=0):
    a, b = pct(e_lo, e_hi)
    return f"{a * 100:.{nd}f}–{b * 100:.{nd}f}%"


def kj(e_lo, e_hi):
    return f"{e_lo / 1e3:.0f}–{e_hi / 1e3:.0f} 千焦"


def _p(t, s=12, c_=k.INK, b=False):
    return [{"t": t, "s": s, "c": c_, "b": b}]


def _r(t, s=12, c_=k.INK, b=False):
    return {"t": t, "s": s, "c": c_, "b": b}


def B(t, col=k.TEALDK):
    return [[{"t": t, "b": True, "c": col}]]


def card(s, x, y, w, h, paras, fill=k.SLATEF, line=None):
    return k.box(s, I(x), I(y), I(w), I(h), paras, fill=fill, line=line, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)


def head(s, x, y, w, t, s_=13, c_=k.TEALDK):
    return k.text(s, I(x), I(y), I(w), I(0.34), [_p(t, s_, c_, True)], anchor=MSO_ANCHOR.MIDDLE)


# ---------------------------------------------------------------- 版式
def new(prs, part, title, source):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.background.fill; bg.solid(); bg.fore_color.rgb = k.WHITE
    x = 0.45
    if part:
        w = 0.3 + 0.2 * len(part)
        k.box(s, I(x), I(0.33), I(w), I(0.38), [_p(part, 12.5, k.WHITE, True)], fill=k.TEAL, line=None,
              shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        x += w + 0.15
    k.text(s, I(x), I(0.2), I(9.55 - x), I(0.64), [_p(title, 18.5, k.INK, True)], anchor=MSO_ANCHOR.MIDDLE)
    cur = STEP.get(part)
    if cur is not None:
        now = {math.floor(cur), math.ceil(cur)}
        xp = 9.78
        for i, name in enumerate(PARTS):
            if i in now:
                fill, col, line = k.TEAL, k.WHITE, None
            elif i < cur:
                fill, col, line = k.BAND, k.TEALDK, None
            else:
                fill, col, line = k.WHITE, k.MUTE, k.SLATE
            k.box(s, I(xp), I(0.36), I(0.7), I(0.32), [_p(name, 10.5, col, True)], fill=fill, line=line,
                  shape=MSO_SHAPE.ROUNDED_RECTANGLE)
            if i < 3:
                k.text(s, I(xp + 0.68), I(0.36), I(0.12), I(0.32), [_p("›", 10, k.SLATE)], anchor=MSO_ANCHOR.MIDDLE)
            xp += 0.78
    k.rect(s, I(0.45), I(0.9), I(12.43), I(0.03), fill=k.TEAL)
    if source:
        k.text(s, I(0.45), I(7.08), I(11.4), I(0.3), [[{"t": "出处：" + source, "s": 8.5, "c": k.MUTE}]])
    k.text(s, I(12.08), I(7.08), I(0.8), I(0.3), [[{"t": str(len(prs.slides)), "s": 9, "c": k.MUTE}]], align=PP_ALIGN.RIGHT)
    return s


def so(s, text, y=6.4):
    """页底「所以」承接条。"""
    k.rect(s, I(0.45), I(y), I(12.43), I(0.58), fill=k.BAND)
    k.rect(s, I(0.45), I(y), I(0.07), I(0.58), fill=k.TEAL)
    k.text(s, I(0.65), I(y), I(12.15), I(0.58), [[_r("所以　", 12.5, k.TEALDK, True), _r(text, 12)]],
           anchor=MSO_ANCHOR.MIDDLE)


# ================================================================ 开篇
def s_cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.background.fill; bg.solid(); bg.fore_color.rgb = k.DARK
    k.rect(s, I(0.8), I(1.45), I(0.09), I(2.3), fill=k.TEAL)
    k.text(s, I(1.1), I(1.3), I(11.5), I(0.95), [_p("PC 端侧大模型架构构想", 40, k.WHITE, True)], anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(1.1), I(2.25), I(11.5), I(0.9), [
        _p("大模型负责理解、小模型负责生成", 21, k.TEALLT),
        _p(f"正常价格周期下，增量硬件约 {R100(LO_N)}–{round(p.yuan(HI_N), -2):,}", 21, k.TEALLT)], anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(1.1), I(3.25), I(11.5), I(0.45), [_p("技术汇报 · 2026 年 10 月", 15, k.SLATE)], anchor=MSO_ANCHOR.MIDDLE)
    k.rect(s, I(0.8), I(4.15), I(11.73), I(1.05), fill=k.INK, line=k.TEAL)
    k.text(s, I(1.05), I(4.2), I(11.3), I(0.95), [[
        _r("方案要点　", 13, k.TEALLT, True),
        _r("200B 混合专家模型（MoE）负责理解，权重存放于闪存、按需流入 NPU；4B 模型负责生成，运行于 3D 存内计算（3D-PIM）；"
           "两者之间通过 KV 映射衔接。", 13, k.WHITE)]], anchor=MSO_ANCHOR.MIDDLE)
    x = 0.8
    for i, t in enumerate(("负载：读多少", "性能：等多久", "功耗：耗多少电", "成本：花多少钱")):
        k.box(s, I(x), I(5.65), I(2.55), I(0.5), [_p(t, 13, k.TEALLT, True)], fill=k.DARK, line=k.TEALDK)
        if i < 3:
            k.arrow(s, I(x + 2.59), I(5.9), I(x + 3.02), I(5.9), color=k.TEAL, w=1.75)
        x += 3.06
    k.notes(s, "本次汇报按负载、性能、功耗、成本四步展开：先说明系统每轮要读多少数据，再说明用户要等多久、要耗多少电，最后核算增量硬件成本。")


def s_summary(prs):
    s = new(prs, "要点", "方案技术可行；电量取决于闪存方案，成本取决于价格周期", SRC_CALC)
    (b_lo, _), (_, b_hi) = pct(*DAYS['C']), pct(*DAYS['shared'])
    cols = [
        ("负载", "每轮要读多少数据？", "约 100 GB / 轮",
         "输入超过约 50 token 后，大模型每轮要读取几乎全部专家的权重；生成阶段每轮在 3D-PIM 内部读取约 600 GB。"),
        ("性能", "用户要等多久？", f"{TT_C[1]:.2f}–{TT_SH:.1f} 秒",
         f"首字等待由闪存带宽决定：堆叠型插电 {TT_C[1]:.2f} 秒、电池档约 {TT_C[0]:.1f} 秒，复用主硬盘约 {TT_SH:.1f} 秒；"
         f"生成约 {p.pim_tok_s():.0f} token/秒。"),
        ("功耗", "一天耗多少电？", f"电池的 {b_lo * 100:.0f}–{b_hi * 100:.0f}%",
         f"取决于闪存方案：堆叠型 {pct_s(*DAYS['C'])}，改造型 {pct_s(*DAYS['A2'])}，复用主硬盘 {pct_s(*DAYS['shared'])}；"
         "能耗约九成用于读取权重。堆叠型为模型估算，待样品实测。"),
        ("成本", "增量硬件要多少钱？", f"约 {R100(LO_N)}–{round(p.yuan(HI_N), -2):,}",
         f"正常价格周期：复用主硬盘 {Y(LO_N)}、改造型 {Y(COST_N['A2'][1])}、堆叠型 {Y(HI_N)}；"
         f"按 2026 年价格 {Y(LO_H)}–{Y(HI_H)}，仅为「全放内存」方案的 {LO_H / RES_H[1]:.0%}–{HI_H / RES_H[1]:.0%}。"),
    ]
    for i, (part, q, big, body) in enumerate(cols):
        x = 0.45 + i * 3.14
        k.box(s, I(x), I(1.12), I(3.01), I(0.5), [_p(part, 15, k.WHITE, True)], fill=k.TEAL, line=None)
        card(s, x, 1.62, 3.01, 3.25, [_p(q, 12.5, k.MUTE), _p(big, 26, k.TEALDK, True), _p(body, 12.5)], fill=k.SLATEF)
    head(s, 0.45, 5.0, 12.43, "推导链条", s_=12.5)
    chain = ["每轮固定读约 100 GB", "首字等待取决于闪存带宽", "电量取决于闪存每字节能耗", "成本取决于价格周期与闪存方案"]
    xc = 0.45
    for i, t_ in enumerate(chain):
        k.box(s, I(xc), I(5.38), I(2.85), I(0.62), [_p(t_, 12, k.INK, True)], fill=k.BAND, line=k.TEAL)
        if i < 3:
            k.arrow(s, I(xc + 2.88), I(5.69), I(xc + 3.16), I(5.69), color=k.TEAL, w=2)
        xc += 3.19
    so(s, "技术上可行；增量做到「几百元」需同时满足两个条件——存储器价格回落到正常周期、复用 PC 自带的主硬盘。")
    k.notes(s, "四个维度的结论：负载上每轮固定读约 100 GB 权重；性能上首字等待由闪存带宽决定；功耗上一天电量由闪存方案决定；"
               "成本上正常价格周期约六百到一千四百元。")


def s_idea(prs):
    s = new(prs, "思路", "理解与生成拆开，分别放在最合适的存储介质上", SRC_CALC + "；对照方案只计同样的 NPU 与多配的 128 GB 内存")
    stages = [("理解 · 200B 混合专家模型", "每轮把全部权重读一遍，计算量大", "权重放闪存（容量便宜），按专家流入 NPU"),
              ("生成 · 4B 模型", "每输出一个 token 都要把模型读一遍", "放在 3D-PIM 中就地计算（带宽高、能耗低）"),
              ("衔接 · KV 映射", "大模型的理解结果不能直接给小模型用", "转换成小模型可用的格式（KV）")]
    for i, (t, why, where) in enumerate(stages):
        card(s, 0.45 + i * 4.18, 1.1, 4.07, 1.32, [_p(t, 13, k.TEALDK, True), _p("特点：" + why, 11.5),
                                                   _p("放置：" + where, 11.5, k.INK, True)], fill=k.SLATEF, line=k.SLATE)
    rows = [[B("全放内存（对照）", k.INK), "多配 128 GB 内存", f"{p.resident_ttft(350):.2f} 秒",
             f"约 {p.resident_decode_tok_s():.0f}（200B）", f"{RES_DAY['total'] / 1e3:.0f} 千焦（{pct_s(RES_DAY['total'], RES_DAY['total'])}）",
             f"{Y(RES_N[1])} / {Y(RES_H[1])}", "能力完整"]]
    store = {"shared": "PC 自带 2 TB 硬盘 + 3D-PIM", "A2": "定制闪存约 171 GB + 3D-PIM", "C": "堆叠闪存 128 GB + 3D-PIM"}
    for key in KEYS:
        cf = CFG[key]
        tt = f"{TT_C[0]:.1f}（电池）/ {TT_C[1]:.2f}（插电）" if key == 'C' else f"{p.cfg_ttft(key)[0]:.1f}"
        rows.append([B(cf['name']), store[key], tt + " 秒", f"约 {p.pim_tok_s():.0f}（4B）",
                     f"{kj(*DAYS[key])}（{pct_s(*DAYS[key])}）", B(f"{Y(COST_N[key][1])} / {Y(COST_H[key][1])}"), cf['avail']])
    k.table(s, I(0.45), I(2.58), I(12.43), I(2.75),
            ["配置", "存储", "首字等待（聊天）", "生成 token/秒", "一天耗电（电池占比）", "增量成本：正常 / 2026", "现状"],
            rows, col_w=[1.45, 2.0, 1.75, 1.3, 2.05, 1.75, 2.13], s=10.5, hl_rows=(0,), hl_color=k.SLATEF)
    k.text(s, I(0.45), I(5.42), I(12.43), I(0.9), [
        [_r("能力说明：", 11.5, k.TEALDK, True),
         _r("对照方案由 200B 直接生成回复；本方案由 4B 生成，借助 KV 映射补回大小模型差距的约 50%"
            "（示意：若 200B 得 80 分、4B 得 50 分，映射后约 65 分）。该比例来自合作团队内部评测，尚未独立复现。", 11.5)]])
    so(s, f"代价是首字等待从 {p.resident_ttft(350):.2f} 秒延长到 {TT_C[1]:.2f}–{TT_SH:.1f} 秒、回复改由 4B 生成；"
          f"换来生成提速约 {p.pim_tok_s() / p.resident_decode_tok_s():.0f} 倍（4B 与 200B 相比）、耗电降至对照的 1/10–1/2、成本仅为对照的 "
          f"{LO_N / RES_N[1]:.0%}–{HI_N / RES_N[1]:.0%}（正常周期）。")
    k.notes(s, "本方案分三种配置，每行数字互相对应。与全放内存相比，代价是首字等待更长、回复由小模型生成；"
               "收益是生成更快、耗电更少、成本更低。生成速度的对比涉及不同规模的模型。")


# ================================================================ 负载
def s_load_round(prs):
    s = new(prs, "负载", "每轮对话由「大模型读一遍、小模型写一段」组成",
            SRC_CALC + "；重度使用日沿用《端侧AI计算架构完整构想》v3.4 §4.3")
    steps = [("输入", "上一轮输出 300 token\n+ 用户输入约 50（聊天，合计约 350）\n或工具返回（智能体，合计约 3,000）", k.SLATEF, k.SLATE),
             ("200B 理解", "读取全部权重约 100 GB\n计算 2 × 200 亿 × 输入 token", k.BAND, k.TEAL),
             ("KV 映射", f"每轮写入 {p.map_bytes_round(350) / 1e6:.1f}–{p.map_bytes_round(3000) / 1e6:.1f} MB", k.SLATEF, k.AMBER),
             ("4B 生成", "输出 300 token\n每个 token 读 2 GB\n共约 600 GB（3D-PIM 内部）", k.BAND, k.TEAL)]
    x, w, gap = 0.45, 2.85, 0.35
    for i, (t, body, fill, line) in enumerate(steps):
        k.box(s, I(x), I(1.12), I(w), I(1.55), [_p(t, 14, k.INK, True)] + [_p(ln, 11, k.MUTE) for ln in body.split("\n")],
              fill=fill, line=line)
        if i < 3:
            k.arrow(s, I(x + w + 0.03), I(1.9), I(x + w + gap - 0.03), I(1.9), color=k.TEAL, w=2)
        x += w + gap
    xr = 0.45 + 3 * (w + gap) + w / 2; xl = 0.45 + w / 2
    k.arrow(s, I(xr), I(2.69), I(xr), I(2.85), color=k.MUTE, w=1.25, head=False)
    k.arrow(s, I(xr), I(2.85), I(xl), I(2.85), color=k.MUTE, w=1.25, head=False)
    k.arrow(s, I(xl), I(2.85), I(xl), I(2.71), color=k.MUTE, w=1.25)
    k.text(s, I(4.5), I(2.88), I(4.3), I(0.28), [_p("生成的内容成为下一轮的输入", 10.5, k.MUTE)], align=PP_ALIGN.CENTER)
    fl = lambda n, dl: 2 * n * dl
    k.table(s, I(0.45), I(3.28), I(8.2), I(2.4), ["阶段", "每轮计算量", "每轮读取量", "每读 1 字节做几次运算", "特点"], [
        ["理解 · 智能体（输入 3,000）", f"{fl(P['n_active'], 3000) / 1e12:.0f} 万亿次", "约 100 GB（闪存）",
         f"约 {fl(P['n_active'], 3000) / P['w_moe']:,.0f} 次", "算得多，权重读一次"],
        ["理解 · 聊天（输入 350）", f"{fl(P['n_active'], 350) / 1e12:.0f} 万亿次", "约 100 GB（闪存）",
         f"约 {fl(P['n_active'], 350) / P['w_moe']:,.0f} 次", "读取占主导"],
        [B("生成（输出 300）"), f"{fl(P['n_dec'], 300) / 1e12:.1f} 万亿次", B("约 600 GB（3D-PIM 内部）"),
         B(f"{fl(P['n_dec'], 300) / (300 * P['w_dec']):.0f} 次"), B("读得最多、算得最少")],
    ], col_w=[2.3, 1.4, 1.65, 1.55, 1.3], s=11.5, first_col_bold=True)
    k.text(s, I(0.45), I(5.75), I(8.2), I(0.55), [_p(
        f"注：智能体每读 1 字节约做 1,200 次运算，与 NPU 有效算力 140 TOPS ÷ 117 GB/s ≈ "
        f"{p.f_eff() / B117:,.0f} 相当——这是插电档闪存带宽取 117 GB/s 的依据（见第 7 页）。", 10.5, k.MUTE)])
    card(s, 8.85, 3.28, 4.03, 2.4, [
        _p("重度使用一天", 13, k.TEALDK, True),
        _p(f"{p.day_rounds()} 轮（650 轮智能体任务 + 30 次问答）", 12),
        _p(f"理解：{p.day_prefill_tokens() / 1e4:.0f} 万 token", 12),
        _p(f"生成：{p.day_decode_tokens() / 1e4:.1f} 万 token", 12),
        _p("沿用手机版方案的重度使用日，作量级参考", 10.5, k.MUTE)], fill=k.SLATEF)
    so(s, "生成阶段读取量最大，因此放在 3D-PIM 内部完成；理解阶段每轮要读多少权重，取决于混合专家模型的特性（见下页）。")
    k.notes(s, "一轮对话分四步：输入、大模型理解、KV 映射、小模型生成。生成阶段每输出一个 token 都要把 2 GB 的模型读一遍，"
               "300 个 token 就是 600 GB，所以必须在存储内部完成。")


def s_load_moe(prs):
    s = new(prs, "负载", "输入超过约 50 token 后，每轮都要读取约 100 GB 权重",
            "测算：被用到的专家比例 = 1 − (1 − 8/128)^输入 token 数（按均匀路由估算，实际路由需在目标模型上实测）")
    pts = [(d, round(p.coverage(d) * 100, 2)) for d in (1, 2, 5, 10, 15, 20, 32, 50, 64, 80, 100, 150, 200)]
    k.xy_chart(s, I(0.45), I(1.1), I(6.6), I(5.15), {"被用到的专家比例": pts}, colors=[k.TEAL],
               x_title="本轮新输入的 token 数", y_title="被用到的专家比例（%）", x_range=(0, 200), y_range=(0, 100),
               legend=False, s=11)
    card(s, 7.25, 1.1, 5.63, 1.5, [
        _p("为什么", 13, k.TEALDK, True),
        _p("混合专家模型每层有 128 个专家，每个 token 只选用 8 个。一轮有几十上百个 token，各自选用的专家不同，合起来几乎覆盖全部专家。", 12)],
         fill=k.SLATEF)
    rows = [[str(d), f"{p.coverage(d):.1%}", f"约 {p.coverage(d) * P['w_moe'] / 1e9:.0f} GB"] for d in (10, 20, 50, 100)]
    rows.append([f"{p.DL_CHAT}（聊天）/ 3,000（智能体）", "约 100%", "约 100 GB"])
    k.table(s, I(7.25), I(2.75), I(5.63), I(2.05), ["新输入 token 数", "被用到的专家", "需读取权重"], rows,
            col_w=[2.4, 1.6, 1.6], s=11.5, first_col_bold=True, hl_rows=(4,), hl_color=k.BAND)
    card(s, 7.25, 4.95, 5.63, 1.3, [
        _p("按需加载：只读用到的专家", 12.5, k.TEALDK, True),
        _p("仅在输入少于约 32 个 token 时有明显收益；实际每轮输入都在 300 以上，作为补充机制保留，不计入测算。", 11.5)], fill=k.BAND)
    so(s, "「每轮固定读取约 100 GB」是最关键的负载特征，它决定了首字等待（性能）和每轮能耗（功耗）。")
    k.notes(s, "输入超过 50 个 token，96% 的专家都会被用到；聊天每轮约 350、智能体约 3,000，所以每轮都要读约 100 GB。"
               "按均匀路由估算是上界，真实路由偏斜时读取量可能更小。")


# ================================================================ 架构
def s_arch(prs):
    s = new(prs, "架构", "权重存于闪存、按专家流入 NPU，生成在 3D-PIM 内完成", SRC_CALC)
    k.box(s, I(0.45), I(4.55), I(2.7), I(1.6), [
        _p("闪存", 13, k.INK, True), _p("128–213 GB", 12), _p("存放 200B 全部权重", 11.5, k.MUTE)], fill=k.SLATEF, line=k.SLATE)
    k.box(s, I(3.75), I(1.2), I(2.85), I(2.0), [
        _p("NPU", 14, k.INK, True), _p("200 TOPS", 12), _p(f"理解 {p.tok_rate():,.0f} token/秒", 11.5),
        _p("片上缓存两个专家（26 MB）", 11, k.MUTE)], fill=k.BAND, line=k.TEAL)
    k.box(s, I(3.75), I(4.55), I(2.85), I(1.6), [
        _p("系统内存", 13, k.INK, True), _p("153 GB/s，占用 2–4 GB", 12), _p("中间结果、大模型的 KV", 11.5, k.MUTE)],
          fill=k.SLATEF, line=k.SLATE)
    k.box(s, I(7.65), I(1.2), I(1.95), I(4.95), [
        _p("3D-PIM", 14, k.INK, True), _p("4 GB · 1 TB/s", 12.5, k.TEALDK, True), _p("4B 模型 2 GB", 12),
        _p("小模型 KV 2 GB", 12), _p("就地完成生成", 12), _p(f"{p.pim_tok_s():.0f} token/秒", 12)], fill=k.BAND, line=k.TEAL)
    k.arrow(s, I(3.15), I(4.75), I(3.73), I(3.0), color=k.RED, w=2.25)
    k.text(s, I(0.45), I(3.3), I(3.0), I(0.8), [_p("① 按专家顺序流入", 11.5, k.RED, True),
                                                _p("30 GB/s（电池）/ 117 GB/s（插电）", 10.5, k.RED)], align=PP_ALIGN.RIGHT)
    k.arrow(s, I(4.95), I(3.22), I(4.95), I(4.53), color=k.TEAL, w=2)
    k.arrow(s, I(5.35), I(4.53), I(5.35), I(3.22), color=k.TEAL, w=2)
    k.text(s, I(5.45), I(3.6), I(1.6), I(0.6), [_p(f"② 约 {p.dram_bw_need(3000, False) / 1e9:.0f} GB/s", 11.5, k.TEALDK, True)])
    k.arrow(s, I(6.62), I(1.75), I(7.63), I(1.75), color=k.AMBER, w=2.25)
    k.text(s, I(6.62), I(1.3), I(1.0), I(0.42), [_p("③ KV 映射", 10.5, k.AMBER, True)], align=PP_ALIGN.CENTER)
    k.arrow(s, I(7.63), I(2.75), I(6.62), I(2.75), color=k.MUTE, w=1.5)
    k.text(s, I(6.62), I(2.8), I(1.0), I(0.42), [_p("④ 输出回传", 10, k.MUTE)], align=PP_ALIGN.CENTER)
    rows = [("①", "闪存 → NPU", "每个专家约 13 MB，按顺序直接送进 NPU 片上缓存；每轮共约 100 GB"),
            ("②", "NPU ↔ 内存", "只传 token 在专家之间的分发数据，权重不经内存中转"),
            ("③", "NPU → 3D-PIM", f"把本轮新内容的 KV 转成小模型格式写入，每轮 {p.map_bytes_round(3000) / 1e6:.1f} MB 以内"),
            ("④", "3D-PIM → 下一轮", "生成的 300 token 作为下一轮大模型的输入")]
    head(s, 9.75, 1.15, 3.13, "四条数据通路")
    y = 1.55
    for n, t, body in rows:
        k.box(s, I(9.75), I(y), I(0.36), I(0.36), [_p(n, 11, k.WHITE, True)], fill=k.TEAL, line=None)
        k.text(s, I(10.18), I(y - 0.04), I(2.7), I(1.1), [_p(t, 12, k.INK, True), _p(body, 10.5, k.MUTE)])
        y += 1.15
    so(s, "决定性能的是三处读取：闪存到 NPU（第 7 页）、NPU 与内存之间（第 8 页）、3D-PIM 内部（第 9 页）。")
    k.notes(s, "架构分四块：闪存存放大模型权重，NPU 做理解计算，系统内存只放中间数据，3D-PIM 存放小模型并完成生成。"
               "权重从闪存按专家顺序直接流进 NPU，不经内存中转。")


# ================================================================ 性能
def s_perf_ttft(prs):
    s = new(prs, "性能", "首字等待由闪存带宽决定；插电档 117 GB/s 与算力恰好配平",
            SRC_CALC + "；理解吞吐 = 200 TOPS × 70% ÷ 每 token 400 亿次运算（未计注意力分数）")
    gears = [("复用主硬盘\n28 GB/s", p.SHARED_BW), ("电池档\n30 GB/s", B30), ("60 GB/s", B60), ("插电档\n117 GB/s", B117)]
    k.chart(s, I(0.45), I(1.1), I(6.6), I(5.15), "bar", [g for g, _ in gears], {
        "聊天（输入 350）": [round(p.t_round_prefill(p.DL_CHAT, b), 2) for _, b in gears],
        "智能体（输入 3,000）": [round(p.t_round_prefill(p.DL_AGENT, b), 2) for _, b in gears]},
        colors=[k.TEAL, k.AMBER], y_title="首字等待（秒）", labels='0.00', gap=60, s=11)
    k.formula_box(s, I(7.25), I(1.1), I(5.63), I(1.9), "怎么算", [
        _p("首字等待 = 取两者较大值：", 12),
        _p("· 从闪存读约 100 GB 的时间 = 100 GB ÷ 闪存带宽", 12),
        _p(f"· 理解计算时间 = 输入 token 数 ÷ {p.tok_rate():,.0f} token/秒", 12),
        _p(f"智能体 3,000 需计算 {p.t_prefill(3000):.2f} 秒，聊天 350 只需 {p.t_prefill(350):.2f} 秒", 11.5, k.TEALDK, True)], s=12)
    card(s, 7.25, 3.15, 5.63, 1.6, [
        _p("为什么取 117 GB/s 和 30 GB/s", 12.5, k.TEALDK, True),
        _p(f"117 GB/s：读约 100 GB 用时 {p.stream_time(B117):.2f} 秒，与 3,000 token 的计算时间 {p.t_prefill(3000):.2f} 秒相等，"
           "再提高带宽不再缩短智能体首字。", 11.5),
        _p(f"30 GB/s：闪存瞬时功率约 {p.burst_power(B30):.0f} 瓦（按 0.5 纳焦/字节），适合电池供电。", 11.5)], fill=k.BAND)
    card(s, 7.25, 4.9, 5.63, 1.35, [
        _p("算力与插电档带宽相匹配", 12.5, k.TEALDK, True),
        _p("聊天轮次计算很快，首字完全取决于读取；插电档下输入超过约 3,000 的智能体轮次，计算会略长于读取。", 11.5)], fill=k.SLATEF)
    so(s, f"设两档闪存带宽：电池 30 GB/s（首字约 {p.stream_time(B30):.1f} 秒）、插电 117 GB/s（约 {p.stream_time(B117):.2f} 秒）；"
          "再提高带宽须同步提升算力。")
    k.notes(s, "首字等待取读权重时间和计算时间中较大的那个。聊天轮次读取远比计算慢，所以首字由闪存带宽决定。"
               "117 GB/s 恰好让读取时间与 3,000 token 的计算时间相等。")


def s_perf_dram(prs):
    s = new(prs, "性能", "内存带宽不是瓶颈：按专家顺序读取只需约 24 GB/s",
            SRC_CALC + "；分发流量按每 token 选 8 个专家、隐藏维 7168、60 层、8 位激活估算")
    card(s, 0.45, 1.1, 5.9, 2.0, [
        _p("方式一：整层权重先缓存到内存", 13, k.MUTE, True),
        _p(f"每层全部专家 {p.layer_bytes() / 1e9:.2f} GB 先写入内存、再读给 NPU，每轮内存多承担约 200 GB 的读写", 12),
        _p(f"输入 3,000 时需 {p.dram_bw_need(3000) / 1e9:.0f} GB/s，超过内存的 153 GB/s；输入超过约 "
           f"{round(p.dl_dram_bound(), -2):,.0f} token 才不受限", 12, k.RED)], fill=k.SLATEF, line=k.SLATE)
    card(s, 0.45, 3.25, 5.9, 2.0, [
        _p("方式二：按专家直通（采用）", 13, k.TEALDK, True),
        _p(f"每个专家约 {p.expert_bytes() / 1e6:.0f} MB 从闪存直接进入 NPU 片上缓存，片上只需 {2 * p.expert_bytes() / 1e6:.0f} MB 双缓冲", 12),
        _p(f"内存只承担 token 在专家之间的分发数据：约 {p.dram_bw_need(3000, False) / 1e9:.0f} GB/s，与输入长短无关", 12, k.TEALDK, True)],
         fill=k.BAND, line=k.TEAL)
    card(s, 0.45, 5.4, 5.9, 0.85, [_p("容量：内存只放中间结果与大模型的 KV，占用 2–4 GB。", 12)], fill=k.SLATEF)
    xs = (1000, 2000, 3000, 5000, 8000, 12000, 20000, 30000)
    k.xy_chart(s, I(6.55), I(1.1), I(6.33), I(5.15), {
        "方式一：整层缓存": [(d, round(p.dram_bw_need(d) / 1e9, 1)) for d in xs],
        "方式二：按专家直通": [(d, round(p.dram_bw_need(d, False) / 1e9, 1)) for d in xs],
        "内存带宽 153 GB/s": [(1000, 153), (30000, 153)]},
        colors=[k.RED, k.TEAL, k.MUTE], x_title="本轮输入 token 数（对数刻度）", y_title="所需内存带宽（GB/s，对数刻度）",
        log=True, x_range=(1000, 30000), y_range=(10, 1000), s=11)
    so(s, "内存只需约 24 GB/s、2–4 GB，不构成瓶颈；理解阶段的瓶颈仍是闪存带宽。")
    k.notes(s, "如果先把整层权重缓存到内存，每轮要多约 200 GB 的读写，3,000 输入时就超过内存带宽。改为按专家直通后，"
               "权重不经过内存，内存只传分发数据，约 24 GB/s。")


def s_perf_decode(prs):
    s = new(prs, "性能", f"生成速度约 {p.pim_tok_s():.0f} token/秒，插电时一轮计算约 1.5 秒完成",
            SRC_CALC + "；不含工具执行与用户阅读时间")
    head(s, 0.45, 1.1, 5.9, "3D-PIM 的 4 GB 怎么分")
    k.box(s, I(0.45), I(1.5), I(2.95), I(0.62), [_p("4B 模型权重（4 位）2 GB", 12, k.WHITE, True)], fill=k.TEAL, line=None)
    k.box(s, I(3.4), I(1.5), I(2.95), I(0.62), [_p(f"KV 2 GB：约 {p.pim_contexts():.0f} 段长对话", 12, k.WHITE, True)],
          fill=k.AMBER, line=None)
    k.formula_box(s, I(0.45), I(2.3), I(5.9), I(1.75), "生成速度", [
        _p("每生成 1 个 token，要读一遍 2 GB 权重和约 15 MB 的 KV", 12),
        _p(f"1 TB/s ÷ 2.015 GB ≈ {p.pim_tok_s():.0f} token/秒", 12.5, k.TEALDK, True),
        _p(f"输出 300 token 约 {T_DEC:.1f} 秒；对照（200B 全放内存）每 token 读 10 GB，约 {p.resident_decode_tok_s():.0f} token/秒", 11.5)], s=12)
    card(s, 0.45, 4.2, 5.9, 2.05, [
        _p("对小模型的两项要求", 12.5, k.TEALDK, True),
        _p("① 权重必须是 4 位：8 位就要 4 GB，占满容量、KV 无处存放", 12),
        _p(f"② KV 必须用压缩格式（每 token 约 890 字节）：普通格式下一段长对话（10 万 token）就要 {p.kv_long_fp16() / 1e9:.1f} GB", 12)],
         fill=k.SLATEF)
    head(s, 6.55, 1.1, 6.33, "一轮的计算耗时（不含工具执行与阅读）")
    cases = [("聊天 · 插电", p.DL_CHAT, B117), ("智能体 · 插电", p.DL_AGENT, B117),
             ("聊天 · 电池", p.DL_CHAT, B30), ("智能体 · 电池", p.DL_AGENT, B30)]
    x0, scale = 8.15, 3.75 / 4.0
    for i, (lab, dl, b) in enumerate(cases):
        y = 1.6 + i * 0.85
        tp = p.t_round_prefill(dl, b)
        k.text(s, I(6.55), I(y), I(1.5), I(0.5), [_p(lab, 12, b=True)], align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        lab_t = f"理解 {tp:.2f}" if tp * scale > 1.2 else f"{tp:.2f}"
        k.box(s, I(x0), I(y), I(tp * scale), I(0.5), [_p(lab_t, 10.5, k.WHITE, True)], fill=k.TEAL, line=None)
        k.box(s, I(x0 + tp * scale + 0.03), I(y), I(T_DEC * scale), I(0.5), [_p(f"{T_DEC:.1f}", 10.5, k.WHITE, True)],
              fill=k.AMBER, line=None)
        k.text(s, I(x0 + (tp + T_DEC) * scale + 0.08), I(y), I(0.75), I(0.5), [_p(f"{tp + T_DEC:.1f} 秒", 11.5, k.INK, True)],
               anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(6.55), I(5.05), I(6.33), I(1.2), [
        [_r("■ ", 12, k.TEAL, True), _r("理解（秒）　", 11, k.MUTE), _r("■ ", 12, k.AMBER, True), _r("生成 300 token（秒）", 11, k.MUTE)],
        _p("理解时间由闪存带宽决定，生成时间由 3D-PIM 带宽决定；两者都满足交互需要。", 12, k.TEALDK, True)])
    so(s, "性能满足交互需要；代价在功耗——下面核算读取这些数据要消耗多少电。")
    k.notes(s, "生成在 3D-PIM 内完成，每秒约五百个 token，输出 300 个 token 约 0.6 秒。插电时一轮计算约 1.5 秒，电池模式约 3.9 秒。")


# ================================================================ 功耗
def s_power_round(prs):
    s = new(prs, "功耗", f"每轮能耗约九成用于读取权重；插电档闪存瞬时功率达 {p.burst_power(B117):.0f} 瓦",
            SRC_CALC + "；闪存读能耗按 UFS 参考值 0.5 纳焦/字节；NPU 满算力 4 瓦；3D-PIM 0.5 皮焦/比特")
    ec, ea = p.round_energy(p.DL_CHAT), p.round_energy(p.DL_AGENT)
    gf = k.chart(s, I(0.45), I(1.1), I(6.6), I(5.15), "barstack", ["聊天（输入 350）", "智能体（输入 3,000）"], {
        "读取权重（闪存）": [round(ec['stream'], 1), round(ea['stream'], 1)],
        "理解计算（NPU）": [round(ec['compute'], 1), round(ea['compute'], 1)],
        "生成（3D-PIM）": [round(ec['decode'], 1), round(ea['decode'], 1)]},
        colors=[k.RED, k.TEAL, k.AMBER], y_title="每轮能耗（焦）", gap=60, s=11)
    gf.chart.value_axis.minimum_scale = 0
    for i, e in enumerate((ea, ec)):
        k.text(s, I(2.3), I(1.75 + i * 2.05), I(4.5), I(0.35), [
            _p(f"合计 {sum(e.values()):.1f} 焦，其中读取权重 {e['stream']:.0f} 焦", 11, k.WHITE, True)])
    k.formula_box(s, I(7.25), I(1.1), I(5.63), I(2.3), "每轮能耗三部分", [
        _p("读取权重 = 100 GB × 0.5 纳焦/字节 = 50 焦", 12, k.RED, True),
        _p(f"理解计算 = 输入 token × {p.e_comp_tok() * 1e3:.2f} 毫焦：聊天 {ec['compute']:.1f} 焦、智能体 {ea['compute']:.1f} 焦", 12),
        _p(f"生成 = 300 token × {p.pim_e_tok(0.5) * 1e3:.0f}–{p.pim_e_tok(1.0) * 1e3:.0f} 毫焦 = {ec['decode']:.1f}–{2 * ec['decode']:.1f} 焦", 12),
        _p(f"读取权重占：聊天 {ec['stream'] / sum(ec.values()):.0%}、智能体 {ea['stream'] / sum(ea.values()):.0%}", 12, k.TEALDK, True)], s=12)
    card(s, 7.25, 3.55, 5.63, 2.7, [
        _p("带宽只改变快慢，不改变能耗", 13, k.TEALDK, True),
        _p("读约 100 GB 的能耗固定为 50 焦；带宽越高，这 50 焦释放得越集中。", 12),
        _p("闪存瞬时功率 = 带宽 × 每字节能耗：", 12),
        _p(f"30 GB/s 时 {p.burst_power(B30):.0f} 瓦，117 GB/s 时 {p.burst_power(B117):.0f} 瓦", 12.5, k.RED, True),
        _p(f"{p.burst_power(B117):.0f} 瓦对笔记本不可接受：插电档必须采用低能耗闪存（各方案实际值见下页）", 11.5, k.INK, True)],
         fill=k.SLATEF)
    so(s, "降低闪存每字节读取能耗，比提升算力或带宽更关键：它决定一天的电量，也决定插电档能否落地。")
    k.notes(s, "每轮能耗中，读取约 100 GB 权重固定花 50 焦，理解计算零点几到三点几焦，生成两到五焦。带宽高低不影响这 50 焦，"
               "只影响释放速度：117 GB/s 时闪存瞬时功率约 59 瓦。")


def s_power_day(prs):
    (b_lo, _), (_, b_hi) = pct(*DAYS['C']), pct(*DAYS['shared'])
    s = new(prs, "功耗", f"一天耗电由闪存方案决定：约占电池的 {b_lo * 100:.0f}%–{b_hi * 100:.0f}%",
            SRC_CALC + "；电池按笔记本 70–100 Wh（252–360 千焦）；区间含 3D-PIM 0.5–1 皮焦/比特")
    cases = [("全放内存（对照）", RES_DAY['total'], RES_DAY['total'], "内存 0.05"),
             ("复用主硬盘", *DAYS['shared'], "0.49–0.70"),
             ("改造型闪存", *DAYS['A2'], "0.40"),
             ("堆叠型闪存", *DAYS['C'], "0.08（模型值）"),
             ("参考：UFS 读能耗", REF05['total'], REF10['total'], "0.50")]
    k.chart(s, I(0.45), I(1.1), I(6.6), I(5.15), "barh", [c_[0] for c_ in reversed(cases)], {
        "区间上限": [round(hi / 1e3, 1) for _, lo, hi, _ in reversed(cases)],
        "区间下限": [round(lo / 1e3, 1) for _, lo, hi, _ in reversed(cases)]},
        colors=[k.TEALLT, k.TEAL], y_title="重度使用一天的耗电（千焦）", labels='0.0', gap=45, s=10.5)
    rows = [[lab, nj, f"{lo / 1e3:.1f}–{hi / 1e3:.1f}" if hi != lo else f"{lo / 1e3:.1f}", pct_s(lo, hi, 1)]
            for lab, lo, hi, nj in cases]
    k.table(s, I(7.25), I(1.1), I(5.63), I(2.65), ["方案", "闪存读能耗（纳焦/字节）", "一天（千焦）", "占电池"], rows,
            col_w=[1.6, 1.55, 1.15, 1.33], s=10.5, first_col_bold=True, hl_rows=(0,), hl_color=k.SLATEF)
    card(s, 7.25, 3.9, 5.63, 2.35, [
        _p("差别从哪里来", 13, k.TEALDK, True),
        _p(f"全放内存：生成时每 token 从内存读 10 GB，一天约 {RES_DAY['decode'] / 1e3:.0f} 千焦", 12),
        _p(f"本方案：生成在 3D-PIM 内完成，一天只要 {REF05['decode'] / 1e3:.1f}–{REF10['decode'] / 1e3:.1f} 千焦", 12),
        _p("其余能耗几乎全部来自闪存读取，所以闪存每字节能耗决定一天的电量", 12, k.INK, True)], fill=k.SLATEF)
    so(s, "闪存方案同时决定电量与成本，下一页比较各闪存方案。")
    k.notes(s, f"一天耗电：堆叠型约 9 到 11 千焦，改造型约 31 到 33 千焦，复用主硬盘约 37 到 53 千焦；"
               f"全放内存方案约 {RES_DAY['total'] / 1e3:.0f} 千焦。堆叠型的读能耗为模型估算，需样品实测。")


# ================================================================ 闪存（功耗 → 成本）
def s_flash(prs):
    s = new(prs, "闪存", "闪存方案：改造型满足电池档，插电档只有堆叠型可行",
            "调研：sources/pc-cost-custom-nand.md、pc-cost-nand-bandwidth.md（见附录「出处」）；测算：calc_pc.py")
    card(s, 0.45, 1.1, 6.15, 1.2, [
        _p("普通硬盘的问题：带宽靠芯片数量堆", 12.5, k.RED, True),
        _p("每颗闪存芯片只有 1.6–1.9 GB/s；达到 30 GB/s 要 17–19 颗、容量 2 TB 以上——为了带宽被迫多买约 20 倍容量。", 11.5)],
         fill=k.REDLT)
    card(s, 6.73, 1.1, 6.15, 1.2, [
        _p("定制思路：容量小、带宽高", 12.5, k.TEALDK, True),
        _p("把芯片内部并行读取的单元拆细、缩短单次读取时间、加宽芯片接口；容量控制在 256 GB 以内。", 11.5)], fill=k.BAND)
    F = p.FLASH
    rows = [
        ["普通固态硬盘（堆芯片）", "多颗 1 Tb 芯片", "17–19 颗 / 2 TB 以上", f"{F['base']['p117']:g} 瓦", "0.55", Y(F['base']['c30_n'][1])],
        [B("复用主硬盘", k.INK), "PC 自带 2 TB PCIe 6.0 硬盘存放权重", "约 28 GB/s（16 颗）", "做不到", "0.49–0.70",
         B(f"{Y(p.cost_flash_shared2tb()[1])}（主控溢价）", k.INK)],
        [B("改造型（电池档）"), "现成 512 Gb 芯片按单比特使用 + 定制控制器", "7–10 颗 / 约 171 GB", f"{F['A2']['p117']:g} 瓦", "0.40",
         B(Y(F['A2']['c30_n'][1]))],
        ["定制芯片型", "新设计单比特芯片，16 个并行单元", "4–5 颗 / 128–160 GB", f"{F['B']['p117']:g} 瓦", "0.33", Y(F['B']['c30_n'][1])],
        [B("堆叠型（插电档）", k.AMBER), "HBF 级芯片 4 层堆叠", "4 层 / 128 GB", B(f"{F['C']['p117']:g} 瓦", k.AMBER),
         "0.08（模型值）", B(Y(F['C']['c30_n'][1]), k.AMBER)],
    ]
    k.table(s, I(0.45), I(2.45), I(12.43), I(2.5),
            ["方案", "做法", "达到 30 GB/s 需要", "117 GB/s 时功耗", "读能耗（纳焦/字节）", "增量成本（正常周期）"],
            rows, col_w=[2.0, 3.3, 2.05, 1.45, 1.65, 1.98], s=11, hl_rows=(2, 4), hl_color=k.BAND)
    tips = [("改造型 → 电池档", k.TEALDK, "无需新设计闪存芯片，只需一颗定制控制器；功耗约 12 瓦。"),
            ("堆叠型 → 插电档", k.AMBER, "唯一能在约 9 瓦内达到 117 GB/s；依赖 HBF 级芯片端侧供货（数据中心样品 2027 年）。"),
            ("复用主硬盘 → 最低成本", k.INK, "只多主控溢价；代价是约 28 GB/s、首字约 3.6 秒、与系统盘争用读写、2028 年后可用。"),
            ("定制芯片型 → 未选", k.MUTE, "成本与改造型相当，却要新设计芯片；插电档约 39 瓦，不如堆叠型。")]
    for i, (t, col, body) in enumerate(tips):
        card(s, 0.45 + i * 3.14, 5.08, 3.01, 1.2, [_p(t, 12, col, True), _p(body, 10.5)], fill=k.SLATEF)
    so(s, f"闪存增量约 {Y(p.cost_flash_shared2tb()[1])}（复用主硬盘）至 {Y(F['C']['c30_n'][1])}（堆叠型），"
          "与 NPU、3D-PIM 一起构成增量成本。")
    k.notes(s, "普通硬盘为了凑带宽要堆很多芯片，容量和成本都被放大。改造型用现成芯片和定制控制器满足电池档；"
               "插电档的高带宽只有堆叠型能把功耗控制在十瓦以内。复用主硬盘最便宜，但带宽和可用时间受限。")


# ================================================================ 成本
def s_cost_parts(prs):
    s = new(prs, "成本", f"增量成本由三部分构成，正常价格周期下约 {R100(LO_N)}–{round(p.yuan(HI_N), -2):,}", SRC_COST)
    C = p.COST
    cats = ["复用主硬盘", "改造型闪存", "堆叠型闪存"]
    fl = [p.cost_flash_shared2tb()[1], p.cost_flash('A2', 'n')[1], p.cost_flash('C', 'n')[1]]
    k.text(s, I(0.45), I(1.1), I(6.6), I(0.38), [[_r("合计：", 12.5, k.MUTE),
        _r(f"{Y(COST_N['shared'][1])}　/　{Y(COST_N['A2'][1])}　/　{Y(COST_N['C'][1])}", 13, k.INK, True)]], align=PP_ALIGN.CENTER)
    k.chart(s, I(0.45), I(1.5), I(6.6), I(4.75), "colstack", cats, {
        "NPU 与片上缓存": [p.yuan(C['npu_usd'][1])] * 3,
        "3D-PIM": [p.yuan(C['pim_n'][1])] * 3,
        "闪存": [p.yuan(v) for v in fl]},
        colors=[k.TEAL, k.BLUE, k.AMBER], y_title="增量成本（元，正常周期基准）", labels='#,##0', gap=70, s=11)
    k.table(s, I(7.25), I(1.1), I(5.63), I(2.6), ["部件", "基准（乐观–悲观）", "主要取决于"], [
        ["NPU 与片上缓存", f"{Y(C['npu_usd'][1])}（{Y(C['npu_usd'][0])}–{Y(C['npu_usd'][2])}）", "芯片面积约 46 mm²、3 nm 晶圆价"],
        ["3D-PIM 4 GB", f"{Y(C['pim_n'][1])}（{Y(C['pim_n'][0])}–{Y(C['pim_n'][2])}）", "内存颗粒价格、堆叠密度与良率"],
        ["闪存", f"{Y(fl[0])}–{Y(fl[2])}", "方案选择、闪存价格"],
    ], col_w=[1.6, 2.1, 1.93], s=11.5, first_col_bold=True)
    card(s, 7.25, 3.85, 5.63, 2.4, [
        _p("统计口径", 12.5, k.TEALDK, True),
        _p("AI 子系统的增量制造成本：芯片、颗粒、封装测试；不含芯片厂毛利；1 美元 ≈ 7.1 元。", 11),
        _p("研发一次性投入另计：定制控制器、3D-PIM（如采用定制闪存芯片还需芯片流片）；每 1,000 万美元摊到 100 万台约合每台 ¥71。", 11),
        _p(f"3D-PIM 基准假设的内存密度高于已发表水平，{Y(C['pim_n'][1])} 偏乐观。", 11, k.RED)], fill=k.SLATEF)
    shares = [p.storage_share(key) for key in KEYS]
    so(s, f"3D-PIM 与闪存两项存储器件占增量成本的 {min(shares):.0%}–{max(shares):.0%}，二者都随存储器价格大幅波动——这引出价格周期问题。")
    k.notes(s, "增量成本由 NPU、3D-PIM、闪存三部分构成。正常价格周期下，按闪存方案不同，基准约六百到一千四百元。存储器件占七到九成。")


def s_cost_cycle(prs):
    s = new(prs, "成本", "做到「几百元」需两个条件：价格回落到正常周期、复用 PC 主硬盘",
            SRC_COST + "；全放内存方案 = 同样的 NPU + 128 GB 内存")
    cats = ["复用主硬盘", "改造型闪存", "堆叠型闪存", "全放内存（对照）"]
    vn = [COST_N['shared'][1], COST_N['A2'][1], COST_N['C'][1], RES_N[1]]
    vh = [COST_H['shared'][1], COST_H['A2'][1], COST_H['C'][1], RES_H[1]]
    gf = k.chart(s, I(0.45), I(1.1), I(6.6), I(5.15), "barh", list(reversed(cats)),
                 {"2026 年价格": [p.yuan(v) for v in reversed(vh)], "正常价格周期": [p.yuan(v) for v in reversed(vn)]},
                 colors=[k.RED, k.TEAL], y_title="增量成本（元，基准情景）", labels='#,##0', gap=40, s=11, number_format='#,##0')
    gf.chart.value_axis.major_unit = 5000
    card(s, 7.25, 1.1, 5.63, 2.55, [
        _p("「几百元」的条件", 13, k.TEALDK, True),
        _p("① 价格回到正常周期：同一配置按 2026 年价格约是正常周期的 2.3–3.2 倍", 11.5),
        _p(f"② 复用 PC 主硬盘（{Y(LO_N)}）；改造型 {Y(COST_N['A2'][1])}、堆叠型 {Y(HI_N)} 的基准值都接近或超过一千元", 11.5),
        _p("时点：若 2028 年后量产，价格有望回落到正常周期；若 2027 年上市，应按 2026 年价格估算", 11.5, k.RED)], fill=k.BAND)
    card(s, 7.25, 3.8, 5.63, 2.45, [
        _p("与「全放内存」相比", 13, k.INK, True),
        _p(f"正常周期：对照 {Y(RES_N[1])}，本方案为其 {LO_N / RES_N[1]:.0%}–{HI_N / RES_N[1]:.0%}", 11.5),
        _p(f"2026 年价格：对照 {Y(RES_H[1])}，本方案为其 {LO_H / RES_H[1]:.0%}–{HI_H / RES_H[1]:.0%}", 11.5),
        _p(f"悲观情景（正常周期）：堆叠型 {Y(COST_N['C'][2])}，比对照悲观值 {Y(RES_N[2])} 高约 "
           f"{COST_N['C'][2] / RES_N[2] - 1:.0%}；改造型 {Y(COST_N['A2'][2])} 与对照基准相当", 11.5),
        _p("内存越贵，本方案的相对优势越大", 11.5, k.TEALDK, True)], fill=k.SLATEF, line=k.SLATE)
    so(s, f"正常价格周期下增量约 {R100(LO_N)}–{round(p.yuan(HI_N), -2):,}，为全放内存方案的 "
          f"{LO_N / RES_N[1]:.0%}–{HI_N / RES_N[1]:.0%}；按 2026 年价格为 {Y(LO_H)}–{Y(HI_H)}，仅为其 {LO_H / RES_H[1]:.0%}–{HI_H / RES_H[1]:.0%}。")
    k.notes(s, "成本的第一变量是存储器价格周期。内存涨价对全放内存方案的冲击更大，所以价格越高，本方案相对优势越明显。"
               "几百元只在价格回落且复用主硬盘时成立。")


# ================================================================ 收尾
def s_conclusion(prs):
    s = new(prs, "结论", "四项结论与下一步建议", "本汇报各页；测算：calc_pc.py")
    shares = [p.storage_share(key) for key in KEYS]
    k.table(s, I(0.45), I(1.1), I(12.43), I(2.95), ["维度", "结论", "关键数字"], [
        [B("负载"), "输入超过约 50 token 后，每轮固定读约 100 GB 权重；生成阶段读取量最大，在 3D-PIM 内完成", "每轮约 100 GB；生成每轮约 600 GB"],
        [B("性能"), "首字等待由闪存带宽决定，插电档带宽与算力配平；内存带宽有富余；生成速度充足",
         f"首字 {TT_C[1]:.2f}–{TT_SH:.1f} 秒；生成约 {p.pim_tok_s():.0f} token/秒"],
        [B("功耗"), "约九成能耗用于读取权重；一天电量由闪存方案决定",
         f"电池占比：堆叠型 {pct_s(*DAYS['C'])}、改造型 {pct_s(*DAYS['A2'])}、复用主硬盘 {pct_s(*DAYS['shared'])}"],
        [B("成本"), f"NPU、3D-PIM、闪存三部分，存储器件占 {min(shares):.0%}–{max(shares):.0%}；价格周期是第一变量",
         f"正常周期 {Y(LO_N)}–{Y(HI_N)}；2026 年 {Y(LO_H)}–{Y(HI_H)}"],
    ], col_w=[1.1, 6.6, 4.73], s=11.5, first_col_bold=True)
    head(s, 0.45, 4.18, 12.43, "建议下一步")
    recs = [("1", "改造型闪存原型", "实测每字节读能耗与读干扰影响，确定电池档的电量与寿命"),
            ("2", "存储器价格跟踪", "按季度跟踪 2027–2028 年内存与闪存合约价，确定量产时点的成本"),
            ("3", "KV 映射评测", "在「200B → 4B、压缩 KV、多轮增量」条件下评测能力补回比例"),
            ("4", "HBF 与 3D-PIM 供应", "与原厂确认 HBF 级芯片端侧供货（2027 年样品后），评估堆叠内存密度与良率")]
    for i, (n, t, body) in enumerate(recs):
        x = 0.45 + (i % 2) * 6.29; y = 4.6 + (i // 2) * 0.82
        k.box(s, I(x), I(y), I(0.4), I(0.4), [_p(n, 12, k.WHITE, True)], fill=k.TEAL, line=None)
        k.text(s, I(x + 0.5), I(y - 0.04), I(5.7), I(0.75), [[_r(t + "：", 12, k.INK, True), _r(body, 11.5)]])
    so(s, "方案技术上可行；建议先做改造型闪存原型与价格跟踪——前者决定电量，后者决定能否做到几百元。")
    k.notes(s, "四项结论分别对应负载、性能、功耗、成本。下一步最关键的是改造型闪存原型实测和存储器价格跟踪。")


def s_risks(prs):
    s = new(prs, "风险", "待验证事项按影响程度排序", "调研：sources/pc-cost-*.md；《端侧AI计算架构完整构想》v3.4 §5.2")
    k.table(s, I(0.45), I(1.1), I(12.43), I(5.15), ["优先级", "事项", "为什么重要", "如何验证"], [
        [B("高", k.RED), "闪存每字节读取能耗", "决定一天电量与插电档的瞬时功率；从 0.5 降到 0.08 纳焦/字节，一天从约 38 千焦降到约 9 千焦",
         "改造型原型实测；堆叠型等待 HBF 样品"],
        [B("高", k.RED), "存储器价格周期", "同一配置按 2026 年价格约是正常周期的 2.3–3.2 倍，决定能否做到几百元", "按季度跟踪内存与闪存合约价"],
        [B("高", k.RED), "HBF 级芯片的端侧供货", "插电档 0.85 秒与「电池占比约 3%」都依赖堆叠型；目前只有数据中心路线（2027 年样品）",
         "与原厂确认小容量堆叠、面积、读取时间与最小批量"],
        [B("中", k.AMBER), "KV 映射的能力补回比例", "「补回 50%」为合作团队内部评测；200B → 4B 的比例更悬殊，且需支持压缩 KV 与多轮增量",
         "按这三个条件独立评测"],
        [B("中", k.AMBER), "3D-PIM 的内存密度与良率", "已发表的定制堆叠内存密度约为标准品的 1/9–1/2，基准假设偏乐观，直接影响面积与成本",
         "流片前对照已发表芯片校准；比较 1 层与多层堆叠"],
        ["低", "实际路由的专家覆盖率", "均匀路由是上界；真实路由偏斜时读取量可能更小，对本方案有利", "在目标 200B 模型上实测"],
        ["低", "闪存读干扰", "每天反复读取同一批约 100 GB 会触发后台数据搬移", "原型上实测阈值与带宽损失"],
    ], col_w=[0.9, 2.6, 5.4, 3.53], s=11)
    k.notes(s, "前三项决定方案能否成立：读能耗决定电量，价格周期决定市场竞争力，HBF 端侧供货决定插电档能否实现。")


# ================================================================ 附录
def a_params(prs):
    s = new(prs, "附录", "参数与假设", "测算：calc_pc.py、calc.py")
    k.table(s, I(0.45), I(1.1), I(12.43), I(5.6), ["类别", "参数", "取值", "来源"], [
        ["负载", "理解模型", "200B 混合专家，激活 20B；专家 4 位浮点（FP4）量化，权重约 100 GB", "项目设定"],
        ["", "结构（用于覆盖率与分发流量）", "60 层；每层 128 个专家，每 token 选 8 个；隐藏维 7168", "估算假设"],
        ["", "生成模型", "4B 稠密模型，4 位量化，权重 2 GB", "项目设定"],
        ["", "KV 格式", "大小模型都用压缩格式，约 890 字节/token；稀疏读取 2,048 个 token", "项目设定；v3.4 §4.3"],
        ["", "KV 映射", "能力差距补回 50%", "合作团队内部评测，尚未独立复现"],
        ["", "每轮输入", "聊天约 350（上一轮输出 300 + 用户输入约 50）；智能体均值约 3,000（含上一轮输出）", "v3.4 §2.4"],
        ["", "重度使用日", f"{p.day_rounds()} 轮；理解 198 万 token；生成 20.4 万 token", "v3.4 §4.3"],
        ["硬件", "NPU", "200 TOPS（4 位权重 × 8 位激活），利用率 70%，满算力 4 瓦；片上缓存 64 MB（专家双缓冲 26 MB + 激活等）", "项目设定"],
        ["", "系统内存", "153 GB/s；读能耗 0.05 纳焦/字节", "项目设定；v3.4"],
        ["", "3D-PIM", "4 GB，内部带宽 1 TB/s，0.5–1 皮焦/比特", "项目设定"],
        ["", "闪存", "小容量（< 256 GB）、高带宽；读能耗参考 UFS 0.5 纳焦/字节，各方案估算值见第 11、12 页", "项目设定；调研"],
        ["", "电池", "笔记本 70–100 Wh（252–360 千焦）", "估算假设"],
        ["成本", "口径", "增量制造成本，不含研发一次性投入与毛利；1 美元 ≈ 7.1 元", "项目设定"],
        ["", "价格周期", "正常周期（内存 2–3 美元/GB、闪存 0.04–0.08 美元/GB）与 2026 年高位并列", "sources/pc-cost-memory-prices.md"],
    ], col_w=[0.9, 2.6, 6.6, 2.33], s=10.5, first_col_bold=True)
    k.notes(s, "标「估算假设」的几项只影响覆盖率、分发流量和电池占比。")


def a_formulas(prs):
    s = new(prs, "附录", "关键公式与数值", "测算：calc_pc.py（tests/test_pc.py 锁定数值）")
    k.formula_box(s, I(0.45), I(1.1), I(6.1), I(5.6), "性能", [
        k.fx("有效算力 F = 200 TOPS × 70% = 140 TOPS", s=11.5),
        k.fx(f"理解吞吐 = F ÷ (2 × N_{{act}}) = 140×10¹² ÷ 40×10⁹ = {p.tok_rate():,.0f} token/s", s=11.5),
        k.fx("首字等待 = max(W ÷ B_{flash}, ΔL ÷ 3,500)", s=11.5),
        k.fx("   W = 100 GB；B = 28 / 30 / 117 GB/s", s=11.5),
        k.fx(f"   → {TT_SH:.2f} / {p.stream_time(B30):.2f} / {p.stream_time(B117):.2f} s", s=11.5),
        k.fx("专家覆盖率 = 1 − (1 − k/E)^{ΔL}，k = 8，E = 128", s=11.5),
        k.fx(f"   ΔL = 50 → {p.coverage(50):.1%}；ΔL = 100 → {p.coverage(100):.1%}", s=11.5),
        k.fx("内存带宽需求（按专家直通）= 分发字节/token × 吞吐", s=11.5),
        k.fx(f"   = 2 × 8 × 7168 × 60 B × 3,500 ≈ {p.dram_bw_need(3000, False) / 1e9:.0f} GB/s", s=11.5),
        k.fx(f"生成速度 = 1 TB/s ÷ (2 GB + 14.6 MB) ≈ {p.pim_tok_s():.0f} token/s", s=11.5),
    ], s=11.5)
    k.formula_box(s, I(6.78), I(1.1), I(6.1), I(5.6), "功耗", [
        k.fx(f"每次运算能耗 e_{{op}} = 4 W ÷ 140 TOPS = {p.e_op() * 1e12:.4f} pJ", s=11.5),
        k.fx(f"理解计算 = 2 × N_{{act}} × e_{{op}} = {p.e_comp_tok() * 1e3:.2f} mJ/token", s=11.5),
        k.fx("读权重 = W × e_{flash}（UFS 参考 0.5 nJ/B → 50 J/轮）", s=11.5),
        k.fx("闪存瞬时功率 = B_{flash} × e_{flash}", s=11.5),
        k.fx(f"   30 GB/s → {p.burst_power(B30):.0f} W；117 GB/s → {p.burst_power(B117):.0f} W", s=11.5),
        k.fx(f"生成 = 2 GB × 8 × 0.5–1 pJ/bit = {p.pim_e_tok(0.5) * 1e3:.0f}–{p.pim_e_tok(1.0) * 1e3:.0f} mJ/token", s=11.5),
        k.fx(f"一天 = {p.day_rounds()} × W × e_{{flash}} + 198 万 × 1.14 mJ + 20.4 万 × 8–16 mJ", s=11.5),
        k.fx(f"   e_{{flash}} = 0.49–0.70 / 0.40 / 0.08 nJ/B", s=11.5),
        k.fx(f"   → {kj(*DAYS['shared'])} / {kj(*DAYS['A2'])} / {kj(*DAYS['C'])}", s=11.5),
        k.fx(f"对照（全放内存）生成 = 10 GB × 0.05 nJ/B = {p.resident_e_tok():.1f} J/token", s=11.5),
    ], s=11.5)
    k.notes(s, "附录列出正文用到的全部公式，数值均由 calc_pc.py 计算并有测试锁定。")


def a_cost_detail(prs):
    s = new(prs, "附录", "成本拆解明细", SRC_COST)
    C = p.COST
    head(s, 0.45, 1.1, 6.1, "NPU 与 64 MB 片上缓存（3 nm，按集成进 SoC 的边际成本）", s_=12)
    k.table(s, I(0.45), I(1.48), I(6.1), I(1.45), ["情景", "NPU 面积", "片上缓存面积", "晶圆价", "成本"], [
        ["乐观", "14.3 mm²", "21.1 mm²", "2.0 万美元", Y(C['npu_usd'][0])],
        ["基准", "22.2 mm²", "24.1 mm²", "2.3 万美元", B(Y(C['npu_usd'][1]))],
        ["悲观", "43.5 mm²", "30.7 mm²", "2.7 万美元", Y(C['npu_usd'][2])],
    ], col_w=[0.8, 1.3, 1.4, 1.3, 1.3], s=11, first_col_bold=True)
    head(s, 6.78, 1.1, 6.1, "4 GB 3D-PIM（1 层内存与逻辑层混合键合）", s_=12)
    k.table(s, I(6.78), I(1.48), I(6.1), I(1.45), ["情景", "内存密度（Gb/mm²）", "堆叠良率", "正常周期", "2026 年价格"], [
        ["乐观", "0.40", "87%", Y(C['pim_n'][0]), Y(C['pim_h'][0])],
        ["基准", "0.25", "80%", B(Y(C['pim_n'][1])), Y(C['pim_h'][1])],
        ["悲观", "0.16", "68%", Y(C['pim_n'][2]), Y(C['pim_h'][2])],
    ], col_w=[0.8, 1.6, 1.1, 1.3, 1.3], s=11, first_col_bold=True)
    F = p.FLASH
    head(s, 0.45, 3.08, 12.43, "闪存方案（成本：乐观 / 基准 / 悲观；括号内为调研文件中的代号）", s_=12)
    names = {"base": "普通固态硬盘（基线）", "A2": "改造型（A2）", "B": "定制芯片型（B）", "C": "堆叠型（C-full）"}
    rows = [[names[key], " / ".join(Y(v) for v in F[key]['c30_n']), Y(F[key]['c30_h'][1]),
             Y(F[key]['c117_n'][1]), Y(F[key]['c117_h'][1])] for key in ('base', 'A2', 'B', 'C')]
    rows.append(["复用主硬盘（基线 PC 只有 1 TB 时改用 16 颗 512 Gb 芯片）",
                 " / ".join(Y(v) for v in p.cost_flash_small_die('n')), Y(p.cost_flash_small_die('h')[1]), "—", "—"])
    k.table(s, I(0.45), I(3.45), I(12.43), I(2.15),
            ["方案", "30 GB/s：正常周期", "30 GB/s：2026 年", "117 GB/s：正常周期", "117 GB/s：2026 年"], rows,
            col_w=[4.3, 2.4, 1.9, 1.9, 1.93], s=10.5, first_col_bold=True)
    card(s, 0.45, 5.72, 12.43, 1.0, [
        _p("说明：NPU 面积以三星 4 nm NPU 实测 3.45 TOPS/mm² 为锚点推算；3D-PIM 基准与乐观密度高于已发表值（最高约 0.2），"
           "前提是把内存外围电路移到逻辑层；键合本身每颗仅 1–6 美元，成本放大主要来自良率连乘。达到 30 GB/s 的芯片颗数按每颗 1.6–1.9 GB/s 并留余量。", 10.5)],
         fill=k.SLATEF)
    k.notes(s, "成本拆解的来源与推算方法见 sources 目录下的四份调研文件，每个数字都标了日期、来源和置信度。")


def a_bridge(prs):
    s = new(prs, "附录", "KV 映射：云端方案的三个问题在 PC 上不存在",
            "《端侧AI计算架构完整构想》v3.4 §5.2；能力补回比例来自合作团队内部评测，尚未独立复现")
    k.table(s, I(0.45), I(1.1), I(12.43), I(2.3), ["问题", "云端大模型 + 端侧小模型", "PC 本地大模型 + 小模型"], [
        ["隐私", "个人记忆须随上下文上传云端", B("上下文不出本机")],
        ["版本耦合", "云端模型按周更新、端侧按季度更新，映射关系随之失效", B("两个模型与映射关系一起发布、一起升级")],
        ["传输", "约 89 MB 经 50 Mbps 网络约需 14 秒", B(f"本机内存写入，每轮 {p.map_bytes_round(3000) / 1e6:.1f} MB 以内")],
    ], col_w=[1.6, 5.2, 5.63], s=12, first_col_bold=True)
    head(s, 0.45, 3.6, 12.43, "仍需验证的三点")
    k.table(s, I(0.45), I(3.98), I(12.43), I(1.85), ["事项", "为什么重要"], [
        ["200B → 4B 是 50 : 1，「补回 50%」是在什么比例下测得", "比例越悬殊，映射越难"],
        ["映射目标能否是压缩 KV（约 890 字节/token）", "3D-PIM 容量只容得下这种格式"],
        ["多轮增量映射：每轮只映射新增内容，小模型的输出再交回大模型", "全部理解都由大模型完成的前提"],
    ], col_w=[7.5, 4.93], s=12)
    card(s, 0.45, 5.95, 12.43, 0.75, [_p("「补回 50%」的含义（示意）：若 200B 得 80 分、4B 单独得 50 分，经映射后约 65 分。", 12)],
         fill=k.SLATEF)
    k.notes(s, "把大模型与小模型都放在本机，云端方案最难解决的版本耦合、隐私和传输问题都不存在；剩下的风险集中在映射本身的质量。")


def a_glossary(prs):
    s = new(prs, "附录", "术语", "通用术语；数值口径见附录「参数与假设」")
    half = [
        [("token（词元）", "模型处理文本的基本单位，约合 1–1.5 个汉字"),
         ("理解（prefill）", "模型读入并消化输入内容的阶段，计算量大"),
         ("生成（decode）", "模型逐个输出 token 的阶段，每输出一个都要把模型读一遍"),
         ("混合专家模型（MoE）", "模型由许多「专家」组成，每个 token 只启用其中少数几个"),
         ("稠密模型（dense）", "每个 token 都用到全部参数的模型"),
         ("KV / KV 映射", "理解阶段产生、生成阶段反复读取的中间结果 / 把大模型的 KV 转成小模型可用格式"),
         ("首字等待", "从用户提交到模型开始输出的时间"),
         ("4 位 / FP4 量化", "每个参数用 4 个比特存储，体积约为 8 位的一半"),
         ("NPU / TOPS", "神经网络处理器 / 每秒万亿次运算"),
         ("双缓冲", "一块缓存在用、另一块同时装载下一份数据")],
        [("3D-PIM", "把内存堆叠在逻辑芯片上，在存储内部完成计算"),
         ("混合键合", "芯片之间以铜对铜直接连接的堆叠工艺"),
         ("HBF", "高带宽闪存：多层堆叠的闪存，带宽接近高带宽内存"),
         ("UFS", "手机常用的闪存接口标准，本汇报以其读能耗作参考"),
         ("闪存芯片（die）/ 并行单元（plane）", "一颗闪存芯片 / 芯片内部可同时读取的独立单元"),
         ("TLC / 单比特（SLC、pSLC）", "每个存储单元存 3 比特 / 1 比特；单比特读取更快、容量更小"),
         ("UCIe", "芯片之间的高速互连标准"),
         ("GB/s", "每秒传输的数据量，衡量带宽"),
         ("纳焦/字节、皮焦/比特", "读取单位数据消耗的能量，衡量存储能效"),
         ("正常价格周期", "存储器供需平衡时的价格水平，区别于 2026 年的高位")],
    ]
    for j, part in enumerate(half):
        k.table(s, I(0.45 + j * 6.29), I(1.1), I(6.14), I(5.6), ["术语", "含义"], [[t, d] for t, d in part],
                col_w=[2.2, 3.94], s=11, first_col_bold=True)
    k.notes(s, "术语表供汇报时备查。")


def a_sources(prs):
    s = new(prs, "附录", "出处", "路径相对 surveys/on-device-ai-compute-arch/")
    k.table(s, I(0.45), I(1.1), I(6.1), I(3.6), ["文件", "内容"], [
        ["calc_pc.py · tests/test_pc.py", "本汇报全部数字与成本模型；测试锁定"],
        ["端侧AI计算架构完整构想_v3.4_润色版.md", "负载基线、KV 格式、云端桥接方案"],
        ["sources/pc-cost-memory-prices.md", "内存、闪存、硬盘、HBM、HBF 价格（33 条来源）"],
        ["sources/pc-cost-nand-bandwidth.md", "闪存每颗芯片带宽、硬盘能耗（36 条来源）"],
        ["sources/pc-cost-logic-pim.md", "晶圆价、NPU 面积、3D-PIM 成本（46 条来源）"],
        ["sources/pc-cost-custom-nand.md", "定制闪存方案核算（44 条来源）"],
    ], col_w=[3.0, 3.1], s=11, first_col_bold=True)
    k.table(s, I(6.78), I(1.1), I(6.1), I(3.6), ["关键外部来源", "用于"], [
        ["SanDisk HBF 技术简报（2025-07）", "HBF 每颗 256 Gb、16 颗堆叠、1.6 TB/s"],
        ["Kioxia XL-FLASH（ISSCC 2020）", "小容量高并行闪存的参照"],
        ["ATLAS 3D 内存加速器（arXiv 2604.08044）", "3D 堆叠内存 1 TB/s、0.66–0.88 皮焦/比特"],
        ["三星 4 nm NPU（ISSCC 2022）", "NPU 面积效率 3.45 TOPS/mm²"],
        ["CFM 闪存市场、TrendForce 价格页", "2026 年 10 月内存与闪存价格"],
        ["Samsung 9100 PRO 规格书", "硬盘读取功耗 → 每字节能耗"],
    ], col_w=[3.2, 2.9], s=11, first_col_bold=True)
    card(s, 0.45, 4.9, 12.43, 1.1, [
        _p("说明", 12, k.TEALDK, True),
        _p("调研文件中每个数字都标注了日期、来源链接和置信度；推算项写明了公式与假设。正文中「乐观 / 基准 / 悲观」三档取自这些文件的区间。", 11.5)],
         fill=k.SLATEF)
    k.notes(s, "出处页。")


def build(prs):
    for fn in (s_cover, s_summary, s_idea, s_load_round, s_load_moe, s_arch, s_perf_ttft, s_perf_dram, s_perf_decode,
               s_power_round, s_power_day, s_flash, s_cost_parts, s_cost_cycle, s_conclusion, s_risks,
               a_params, a_formulas, a_cost_detail, a_bridge, a_glossary, a_sources):
        fn(prs)

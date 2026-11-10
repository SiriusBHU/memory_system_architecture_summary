# -*- coding: utf-8 -*-
"""PC 形态 PPT：HBF 流式 MoE prefill + 3D-PIM decode + KV 映射桥（技术页）。数字全部来自 calc_pc。"""
from pptx.util import Inches as I
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import calc as c
import calc_pc as p
import pptkit as k

P, H = p.P, p.H
B30, B60, B117 = p.GEARS
SRC_USER = "2026-10 与用户对齐的负载与硬件参数"


def _p(t, s=10.5, c_=k.INK, b=False):
    return [{"t": t, "s": s, "c": c_, "b": b}]


def _r(t, s=10.5, c_=k.INK, b=False):
    return {"t": t, "s": s, "c": c_, "b": b}


def _h(s, x, y, w, t, s_=11.5, c_=k.TEALDK):
    return k.text(s, I(x), I(y), I(w), I(0.3), [_p(t, s_, c_, True)], anchor=MSO_ANCHOR.MIDDLE)


def _card(s, x, y, w, h, paras, fill=k.SLATEF, line=None):
    return k.box(s, I(x), I(y), I(w), I(h), paras, fill=fill, line=line,
                 align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)


def G(b):
    return f"{b / 1e9:.0f} GB/s"


def K(x, nd=1):
    return f"{x / 1e3:.{nd}f}K"


def Y(usd):
    return f"¥{p.yuan(usd):,}"


def B(t, col=k.TEALDK):
    return [[{"t": t, "b": True, "c": col}]]


DAY = p.day_energy(0.5)
DAY1 = p.day_energy(1.0)
SH_LO, SH_HI = p.battery_share(DAY['total'])
SH1_LO, SH1_HI = p.battery_share(DAY1['total'])
E_STREAM = P['w_moe'] * H['e_hbf']


# ---------------------------------------------------------------- 1
def slide_cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.background.fill; bg.solid(); bg.fore_color.rgb = k.DARK
    k.rect(s, I(0.8), I(1.55), I(0.09), I(2.45), fill=k.TEAL)
    k.text(s, I(1.1), I(1.4), I(11.5), I(1.0),
           [[{"t": "PC 端侧 AI 架构构想", "s": 42, "c": k.WHITE, "b": True}]], anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(1.1), I(2.45), I(11.5), I(0.6),
           [[{"t": "HBF 流式 MoE prefill + 3D-PIM decode + KV 映射桥", "s": 24, "c": k.TEALLT}]],
           anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(1.1), I(3.2), I(11.5), I(0.5),
           [[{"t": "技术评审版 · 2026年10月", "s": 16, "c": k.SLATE}]], anchor=MSO_ANCHOR.MIDDLE)
    base = (f"负载 200B-A20B MoE（FP4 专家）prefill · 4B dense（4-bit）decode · NPU 200 TOPS @W4A8 · "
            f"DRAM {G(H['b_dram'])} · 3D-PIM 1 TB/s / 4 GB · HBF 读 0.5 nJ/B（参考 UFS）")
    k.box(s, I(0.8), I(4.35), I(11.73), I(0.62),
          [[{"t": "参数基线  ", "s": 12.5, "c": k.TEALLT, "b": True}, {"t": base, "s": 12, "c": k.WHITE}]],
          fill=k.INK, line=k.TEAL)
    chain = ["HBF（权重）", "NPU：200B prefill", "KV 映射", "3D-PIM：4B decode", "下一轮增量 prefill"]
    x, w, gap = 0.8, 2.02, 0.405
    for i, t in enumerate(chain):
        k.box(s, I(x), I(5.6), I(w), I(0.46), [_p(t, 11, k.TEALLT, True)], fill=k.DARK, line=k.TEALDK)
        if i < len(chain) - 1:
            k.arrow(s, I(x + w + 0.04), I(5.83), I(x + w + gap - 0.04), I(5.83), color=k.TEAL)
        x += w + gap
    k.text(s, I(0.8), I(6.95), I(11.73), I(0.3), [[
        {"t": f"出处：{SRC_USER}；派生数字见 calc_pc.py（tests/test_pc.py 锁定）", "s": 8.5, "c": k.MUTE}]])
    k.notes(s, "PC 形态：大模型只做 prefill、小模型只做 decode，中间用 KV 映射桥接；权重放闪存按专家流式加载，decode 放 3D-PIM。")


# ---------------------------------------------------------------- 2
def slide_abstract(prs):
    s = k.add_slide(prs, "摘要", "三条结论 · 关键数字", source=f"{SRC_USER}；calc_pc.py；sources/pc-cost-*.md")
    tn2 = p.cost_total(p.cost_flash_shared2tb(), 'n'); ta2 = p.cost_total(p.cost_flash('A2', 'n'), 'n')
    tc = p.cost_total(p.cost_flash('C', 'n'), 'n'); th2 = p.cost_total(p.cost_flash_shared2tb(), 'h')
    rn = p.cost_resident_dram('n')
    concl = [
        ("① 架构", "prefill 全走 200B MoE：权重放定制高带宽闪存，按专家流进 NPU；decode 全在 3D-PIM 上跑 4B；"
                  "二者之间用 KV 映射桥接。DRAM 只放 MoE 分发激活和 200B 的 KV。"),
        ("② 第一约束", f"MoE 让每轮都要把 {P['w_moe'] / 1e9:.0f} GB 权重流一遍：按 0.5 nJ/B 一轮 {E_STREAM:.0f} J，3K 轮的计算只有 "
                     f"{3000 * p.e_comp_tok():.1f} J。卡住的是闪存读能耗与瞬时功率，不是算力，也不是 DRAM 带宽。"),
        ("③ 成本", f"AI 子系统增量（正常周期、基准情景）：主盘兼任 {Y(tn2[1])}、A2 {Y(ta2[1])}、HBF 级堆叠 {Y(tc[1])}；"
                  f"2026 价格下基准情景各路径 ≥ {Y(th2[1])}。几百元要同时满足：价格回到正常周期，且闪存走主盘兼任，"
                  f"或 A2 / C-full 的乐观情景（{Y(ta2[0])} / {Y(tc[0])}）。"),
    ]
    for i, (t_, body) in enumerate(concl):
        _card(s, 0.45 + i * 4.18, 1.08, 4.07, 1.95, [_p(t_, 12, k.TEALDK, True), _p(body, 10.5)], line=k.SLATE)
    _h(s, 0.45, 3.15, 12.43, "关键数字（calc_pc 计算）")
    rows = [
        ["prefill 吞吐", f"140 TOPS ÷ (2 × 20B) = {p.tok_rate():,.0f} tok/s", f"3K 轮 {p.t_prefill(3000):.2f} s；20K 轮 {p.t_prefill(20000):.2f} s"],
        ["闪存两档", f"电池 {G(B30)}（A2）/ 插电 {G(B117)}（C-full）", f"首 token ≥ {p.stream_time(B30):.2f} / {p.stream_time(B117):.2f} s"],
        ["DRAM", f"专家顺序直供：{p.dram_bw_need(3000, False) / 1e9:.0f} GB/s", f"两层 ping-pong 放 DRAM：3K 轮需 {p.dram_bw_need(3000) / 1e9:.0f} GB/s"],
        ["3D-PIM decode", f"{p.pim_tok_s():.0f} tok/s；{p.pim_e_tok(0.5) * 1e3:.0f}–{p.pim_e_tok(1.0) * 1e3:.0f} mJ/token",
         f"片外 LPDDR {p.off_e_tok() * 1e3:.0f} mJ/token；4 GB = 2 GB 权重 + 2 GB KV"],
        ["一天电量", f"0.5 nJ/B：{DAY['total'] / 1e3:.1f} kJ（{SH_LO:.1%}–{SH_HI:.1%} 电池）",
         f"C-full 0.08 nJ/B：{p.day_energy_nj(0.08)['total'] / 1e3:.1f} kJ"],
        [B("成本", k.RED), B(f"正常周期基准 {Y(tn2[1])}–{Y(tc[1])}", k.RED),
         B(f"对照 200B 常驻 DRAM（128 GB）：正常周期 {Y(rn[1])}，2026 价格 {Y(p.cost_resident_dram('h')[1])}", k.RED)],
    ]
    k.table(s, I(0.45), I(3.48), I(12.43), I(2.75), ["要点", "数值", "说明"], rows,
            col_w=[1.8, 4.9, 5.73], s=10.5, first_col_bold=True, hl_rows=(5,))
    k.text(s, I(0.45), I(6.38), I(12.43), I(0.55), [
        _p("口径：映射能力按「补回 50%」计（团队自述，未经第三方验证）；闪存读能耗参考 UFS 0.5 nJ/B；重度使用日沿用 v3.4 §4.3；"
           "3,500 tok/s 为线性项上限（未含注意力分数与路由计算）；成本为增量制造成本，不含 NRE 与芯片厂毛利，1 USD ≈ 7.1 CNY。", 9, k.MUTE)])
    k.notes(s, "三条结论：架构分工；第一约束是闪存读能耗与功率；成本几百元只在存储器价格回到正常周期时成立。")


# ---------------------------------------------------------------- 3
def slide_baseline(prs):
    s = k.add_slide(prs, "基线", "负载与参数基线", source=f"{SRC_USER}；v3.4 §4.3（重度使用日、KV 890 B/token）；calc_pc.py")
    rows = [
        ["prefill 模型", B("200B-A20B MoE；专家 FP4"), "权重 ≈ 200B × 0.5 B = 100 GB"],
        ["路由与结构", "60 层 · 每层 128 专家选 8 · 隐藏维 7168", "假设（用于覆盖率与分发流量）"],
        ["decode 模型", B("4B dense，4-bit"), "权重 2 GB"],
        ["KV 格式", "压缩 890 B/token + 稀疏 top-k 2048", "200B 与 4B 都用压缩格式"],
        ["KV 映射", "能力补回 50%", "用户假设（团队自述）"],
        ["NPU", B("200 TOPS @W4A8，MFU 70%"), "满算力持续 4 W"],
        ["DRAM", B(f"{G(H['b_dram'])}"), "读 0.05 nJ/B"],
        ["3D-PIM", B("1 TB/s · 4 GB · 0.5–1 pJ/bit"), "片内，逻辑 die 可算注意力"],
        ["HBF", B("读 0.5 nJ/B"), "参考 UFS 系统级读能耗"],
        ["电池", "70–100 Wh = 252–360 kJ", "笔记本"],
    ]
    k.table(s, I(0.45), I(1.05), I(7.3), I(4.35), ["参数", "取值", "说明"], rows,
            col_w=[1.5, 3.3, 2.5], s=10, first_col_bold=True)
    ex = p.expert_bytes()
    k.formula_box(s, I(7.95), I(1.05), I(4.93), I(4.35), "派生量", [
        k.fx("① F_{eff} = 200 TOPS × 70% = 140 TOPS", s=10.5),
        k.fx("② 吞吐 = F_{eff} ÷ 2N_{act}", s=10.5),
        k.fx(f"   = 140×10¹² ÷ 40×10⁹ = {p.tok_rate():,.0f} tok/s（线性项上限）", s=10.5),
        k.fx(f"③ e_{{op}} = 4 W ÷ 140 TOPS = {p.e_op() * 1e12:.4f} pJ/op", s=10.5),
        k.fx(f"   E_{{comp}} = 2N_{{act}}·e_{{op}} = {p.e_comp_tok() * 1e3:.2f} mJ/token", s=10.5),
        k.fx(f"④ 每层 = 100 GB ÷ 60 = {p.layer_bytes() / 1e9:.2f} GB", s=10.5),
        k.fx(f"   每专家 = {p.layer_bytes() / 1e9:.2f} GB ÷ 128 ≈ {ex / 1e6:.0f} MB", s=10.5),
        k.fx(f"⑤ PIM decode = 1 TB/s ÷ (2 GB + {p.pim_kv_step() / 1e6:.1f} MB)", s=10.5),
        k.fx(f"   ≈ {p.pim_tok_s():.0f} tok/s", s=10.5),
        k.fx(f"⑥ 每轮流式 = 100 GB × 0.5 nJ/B = {E_STREAM:.0f} J", s=10.5, b=True, c=k.RED),
    ], s=10.5)
    _card(s, 0.45, 5.55, 6.15, 1.38, [
        _p("每轮增量 ΔL（prefill 全走 200B）", 11, k.TEALDK, True),
        _p(f"chat：上一轮 decode 300 + 用户输入约 50 ≈ {p.DL_CHAT} token", 10.5),
        _p(f"agent：上一轮 decode 300 + 工具返回，均值约 {K(p.DL_AGENT, 0)}", 10.5),
        _p("system prompt 只在会话开头算一次（其 KV 复用）", 10, k.MUTE)], fill=k.BAND)
    _card(s, 6.75, 5.55, 6.13, 1.38, [
        _p("重度使用日（沿用 v3.4 §4.3）", 11, k.TEALDK, True),
        _p(f"{p.day_rounds()} 轮（650 轮 agent + 30 次问答）", 10.5),
        _p(f"prefill {p.day_prefill_tokens() / 1e4:.0f} 万 token · decode {p.day_decode_tokens() / 1e4:.1f} 万 token", 10.5),
        _p("PC 的实际使用强度可能更高，按此作量级参照", 10, k.MUTE)], line=k.SLATE)
    k.notes(s, "参数全部来自与用户的对齐；路由结构与隐藏维为假设，只影响覆盖率和分发流量两项。")


# ---------------------------------------------------------------- 4
def slide_arch(prs):
    s = k.add_slide(prs, "架构", "四个模块与数据流",
                    source=f"{SRC_USER}；calc_pc.py dram_bw_need() / pim_tok_s() / map_bytes_round()")
    k.box(s, I(0.45), I(1.08), I(8.2), I(0.5), [[
        _r("控制平面  ", 11, k.TEALLT, True),
        _r("增量 prefill 触发 · 按需 / 整层加载切换（阈值约 32 token）· HBF 两档带宽 · 映射调度", 10.5, k.WHITE)]],
        fill=k.INK, line=None)
    k.box(s, I(0.45), I(4.75), I(2.45), I(1.6), [
        _p("HBF（定制高带宽闪存）", 11.5, k.INK, True),
        _p("128–171 GB（<256 GB）；200B 专家 FP4 ≈ 100 GB", 9.5),
        _p("读 0.5 nJ/B（参考 UFS）", 9.5, k.MUTE)], fill=k.SLATEF, line=k.SLATE)
    k.box(s, I(3.35), I(2.0), I(2.75), I(1.85), [
        _p("NPU", 12, k.INK, True),
        _p("200 TOPS @W4A8 · 有效 140", 10),
        _p(f"prefill {p.tok_rate():,.0f} tok/s", 10),
        _p("片上 SRAM ≥ 64 MB：专家双缓冲 26 MB + 激活", 9.5, k.MUTE)], fill=k.BAND, line=k.TEAL)
    k.box(s, I(3.35), I(4.75), I(2.75), I(1.6), [
        _p(f"DRAM {G(H['b_dram'])}", 12, k.INK, True),
        _p("MoE 分发激活", 10),
        _p("200B 的 KV：89 MB / 100K 上下文", 10, k.MUTE)], fill=k.SLATEF, line=k.SLATE)
    k.box(s, I(6.6), I(2.0), I(2.05), I(4.35), [
        _p("3D-PIM", 12, k.INK, True),
        _p("1 TB/s · 4 GB", 10.5, k.TEALDK, True),
        _p("4B 4-bit 权重 2 GB", 10),
        _p(f"KV 2 GB（约 {p.pim_contexts():.0f} 个 100K 上下文）", 10),
        _p("逻辑 die：GEMV + 注意力", 10),
        _p(f"{p.pim_tok_s():.0f} tok/s", 10),
        _p(f"{p.pim_e_tok(0.5) * 1e3:.0f}–{p.pim_e_tok(1.0) * 1e3:.0f} mJ/token", 10)], fill=k.BAND, line=k.TEAL)
    k.arrow(s, I(2.9), I(4.95), I(3.33), I(3.6), color=k.RED, w=2)
    k.text(s, I(0.45), I(3.55), I(2.75), I(0.9), [
        _p("按专家流式", 10, k.RED, True), _p(f"{G(B30)}（电池）/ {G(B117)}（插电）", 9.5, k.RED)], align=PP_ALIGN.RIGHT)
    k.arrow(s, I(4.55), I(3.87), I(4.55), I(4.73), color=k.TEAL, w=1.75)
    k.arrow(s, I(4.9), I(4.73), I(4.9), I(3.87), color=k.TEAL, w=1.75)
    k.text(s, I(5.0), I(4.1), I(1.5), I(0.4), [_p(f"{p.dram_bw_need(3000, False) / 1e9:.0f} GB/s", 10, k.TEALDK, True)])
    k.arrow(s, I(6.12), I(2.55), I(6.58), I(2.55), color=k.AMBER, w=2)
    k.text(s, I(5.9), I(1.68), I(1.0), I(0.36), [_p("KV 映射", 9.5, k.AMBER, True)], align=PP_ALIGN.CENTER)
    k.arrow(s, I(6.58), I(3.4), I(6.12), I(3.4), color=k.MUTE, w=1.5)
    k.text(s, I(5.85), I(3.45), I(0.8), I(0.5), [_p("300 token 输出", 8.5, k.MUTE)], align=PP_ALIGN.CENTER)

    rx, rw = 8.85, 4.03
    _h(s, rx, 1.08, rw, "一轮怎么走")
    steps = [("1", "200B 增量 prefill", "输入 = 上一轮 4B 输出 300 token + 用户输入 / 工具返回；权重按专家从 HBF 流进 NPU"),
             ("2", "KV 映射", f"把新增 token 的 KV 映射成 4B 的压缩格式写进 PIM：3K 轮约 {p.map_bytes_round(3000) / 1e6:.1f} MB"),
             ("3", "4B decode", f"在 PIM 里生成 300 token，约 {300 / p.pim_tok_s():.1f} s"),
             ("4", "回灌", "4B 的输出作为下一轮 200B 增量 prefill 的一部分")]
    y = 1.45
    for n, t, body in steps:
        k.box(s, I(rx), I(y), I(0.36), I(0.36), [_p(n, 11, k.WHITE, True)], fill=k.TEAL, line=None)
        k.text(s, I(rx + 0.45), I(y - 0.04), I(rw - 0.45), I(1.0), [_p(t, 10.5, k.INK, True), _p(body, 9.5, k.MUTE)])
        y += 1.0
    _card(s, rx, 5.5, rw, 1.43, [
        _p("每块存什么", 10.5, k.TEALDK, True),
        _p("HBF：200B 全部权重 · DRAM：激活、200B 的 KV", 9.5),
        _p("NPU SRAM：正在算的两个专家 + 激活块", 9.5),
        _p("PIM：4B 权重、4B 的 KV（映射来的 + 自己生成的）", 9.5)], fill=k.SLATEF)
    k.notes(s, "关键设计选择：ping-pong 单位是专家（约 13 MB）而不是整层（1.67 GB），HBF 直接供给 NPU，DRAM 只承担分发激活。")


# ---------------------------------------------------------------- 5
def slide_timeline(prs):
    s = k.add_slide(prs, "时间线", "一轮的耗时：chat 与 agent", half_life=("快变量",),
                    source="calc_pc.py t_round_prefill() / pim_tok_s()；t_prefill = max(W·覆盖率 ÷ B, ΔL ÷ 3,500)")
    t_dec = 300 / p.pim_tok_s()
    cases = [("chat · ΔL 350 · 电池档", p.DL_CHAT, B30), ("chat · ΔL 350 · 插电档", p.DL_CHAT, B117),
             ("agent · ΔL 3K · 电池档", p.DL_AGENT, B30), ("agent · ΔL 3K · 插电档", p.DL_AGENT, B117)]
    scale = 7.2 / (p.stream_time(B30) + t_dec + 0.2)
    x0 = 3.0
    _h(s, 0.45, 1.05, 12.43, "200B prefill（首 token 前）→ 映射 → 4B decode 300 token（不含工具执行与用户思考）")
    for i, (lab, dl, b) in enumerate(cases):
        y = 1.5 + i * 0.62
        tp = p.t_round_prefill(dl, b)
        k.text(s, I(0.45), I(y), I(2.5), I(0.42), [_p(lab, 10, b=True)], align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        k.box(s, I(x0), I(y), I(tp * scale), I(0.42), [_p(f"prefill {tp:.2f} s", 9.5, k.WHITE, True)],
              fill=k.RED if p.stream_time(b) > p.t_prefill(dl) else k.TEAL, line=None)
        k.box(s, I(x0 + tp * scale + 0.03), I(y), I(t_dec * scale), I(0.42), [_p(f"decode {t_dec:.1f} s", 9, k.WHITE, True)],
              fill=k.AMBER, line=None)
    k.text(s, I(x0), I(3.95), I(9.8), I(0.3), [[
        _r("■ ", 10, k.RED, True), _r("流式受限（等 HBF）  ", 9.5, k.MUTE),
        _r("■ ", 10, k.TEAL, True), _r("计算受限（等 NPU）  ", 9.5, k.MUTE),
        _r("■ ", 10, k.AMBER, True), _r("PIM decode", 9.5, k.MUTE)]])
    rows = []
    for lab, dl, b in cases:
        rows.append([lab, f"{p.stream_time(b):.2f} s", f"{p.t_prefill(dl):.2f} s",
                     B(f"{p.t_round_prefill(dl, b):.2f} s"), f"{t_dec:.2f} s"])
    k.table(s, I(0.45), I(4.35), I(7.6), I(1.75), ["场景", "流式 W ÷ B", "计算 ΔL ÷ 3,500", "首 token 前", "decode 300 token"],
            rows, col_w=[2.3, 1.3, 1.5, 1.3, 1.5], s=10, first_col_bold=True)
    k.formula_box(s, I(8.25), I(4.35), I(4.63), I(2.58), "读法", [
        _p("ΔL ≥ 50 时专家几乎全被选中，流式量 ≈ 100 GB，与 ΔL 无关", 10),
        _p(f"chat 轮次永远是流式受限：电池档 {p.stream_time(B30):.2f} s、插电档 {p.stream_time(B117):.2f} s", 10),
        _p(f"agent 3K 轮在插电档刚好与计算打平（{p.t_prefill(3000):.2f} s）", 10),
        _p(f"要让计算藏住流式：ΔL ≥ W·F ÷ (2N·B) = {K(p.dl_hide(B30))}（电池）/ {K(p.dl_hide(B117), 2)}（插电）", 10, k.TEALDK, True)],
        s=10)
    k.text(s, I(0.45), I(6.25), I(7.6), I(0.68), [
        _p("首 token 延迟由 HBF 带宽决定，不由 NPU 算力决定；decode 0.6 s 来自 PIM 1 TB/s ÷ 2 GB。", 10, k.RED, True)])
    k.notes(s, "chat 场景每轮新增只有约 350 token，计算 0.1 s，但仍要流 100 GB，所以首 token 前的时间完全由 HBF 带宽决定。")


# ---------------------------------------------------------------- 6
def slide_intensity(prs):
    s = k.add_slide(prs, "Prefill", "MoE 流式的算术强度 · ping-pong 放在哪",
                    source="calc_pc.py intensity_dram() / dram_bw_need() / dl_dram_bound()；v3.4 §6.4.2.2（MoE 在流式 prefill 中是负收益）")
    k.formula_box(s, I(0.45), I(1.05), I(6.0), I(2.55), "为什么「prefill 算力受限」在这里要打折", [
        k.fx("强度 = 2·N_{act}·ΔL ÷ 每轮字节数", s=10.5, b=True, c=k.TEALDK),
        _p("权重常驻时：分母只有激活，强度随 ΔL 线性涨", 10),
        k.fx("MoE 每轮流全部权重：分母 ≥ W_{total}，强度 × N_{act} ÷ N_{total} = 1/10", s=10, f=k.YAHEI),
        k.fx(f"两层放 DRAM：强度 ≈ 0.2·ΔL ops/B（写 100 GB + 读 100 GB）", s=10.5),
        k.fx(f"DRAM 脊点 = 140 TOPS ÷ 153 GB/s = {p.ridge_dram():.0f} ops/B", s=10.5),
        k.fx(f"⇒ ΔL ≥ {K(p.dl_dram_bound())} 才是算力受限（含分发）", s=10.5, b=True, c=k.RED),
    ], s=10.5)
    rows = []
    for dl in (1000, 3000, round(p.dl_dram_bound()), 10000, 27000):
        need = p.dram_bw_need(dl)
        lab = B("DRAM", k.RED) if need > H['b_dram'] * 1.005 else ("打平" if need > H['b_dram'] * 0.995 else "算力")
        rows.append([f"{dl / 1e3:.2f}K" if dl % 1000 else K(dl, 0), f"{p.t_prefill(dl):.2f} s", f"{need / 1e9:.0f} GB/s",
                     lab,
                     B(f"{p.dram_bw_need(dl, False) / 1e9:.0f} GB/s"), f"{P['w_moe'] / p.t_prefill(dl) / 1e9:.0f} GB/s"])
    k.table(s, I(6.65), I(1.05), I(6.23), I(2.55), ["ΔL", "计算", "两层放 DRAM 需", "153 GB/s 下瓶颈", "专家直供需", "HBF 需"],
            rows, col_w=[0.75, 0.85, 1.25, 1.25, 1.1, 1.0], s=9.5, first_col_bold=True)
    _card(s, 0.45, 3.78, 6.0, 1.5, [
        _p("方案 A：两层 ping-pong 放 DRAM（原设想）", 11, k.INK, True),
        _p(f"每层全部专家 {p.layer_bytes() / 1e9:.2f} GB，双缓冲 {2 * p.layer_bytes() / 1e9:.1f} GB，DRAM 容量确实小", 10),
        _p("但每轮 DRAM 多扛 200 GB（HBF 写入 + NPU 读出）；3K 轮需 257 GB/s，被 153 GB/s 卡到 1.44 s", 10),
        _p("每轮多 10 J（200 GB × 0.05 nJ/B）", 10, k.MUTE)], line=k.SLATE)
    _card(s, 6.65, 3.78, 6.23, 1.5, [
        _p("方案 B：专家级 ping-pong 放 NPU SRAM（推荐）", 11, k.TEALDK, True),
        _p(f"按专家顺序算：每个专家 {p.expert_bytes() / 1e6:.0f} MB 从 HBF 直接进 SRAM，只读一次", 10),
        _p(f"双缓冲 {2 * p.expert_bytes() / 1e6:.0f} MB；被路由到该专家的 token 激活从 DRAM 取", 10),
        _p(f"DRAM 只剩分发激活：{p.dispatch_bytes_tok() / 1e6:.1f} MB/token × 3,500 = {p.dram_bw_need(3000, False) / 1e9:.0f} GB/s，与 ΔL 无关", 10, k.TEALDK, True)],
        fill=k.BAND)
    k.box(s, I(0.45), I(5.45), I(12.43), I(1.48), [
        [_r("结论：", 11.5, k.RED, True),
         _r("「prefill 算力受限、DRAM 50 GB/s 以内够用」在方案 B 下对所有 ΔL 成立（约 24 GB/s）；"
            "方案 A 只有 ΔL ≥ 27K 才降到 50 GB/s，典型 3K 轮次受 DRAM 限制。", 11, b=True)],
        _p("分发流量按 INT8 激活、每 token 选 8 个专家、隐藏维 7168、60 层估：进 + 出 = 2 × 8 × 7168 × 60 B。"
           "ΔL ≤ 3K 时一层激活（约 21.5 MB）可整块留在 SRAM，分发流量还会更低。", 10, k.MUTE)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "MoE 流式下算术强度只有 dense 常驻时的 1/10，所以 DRAM 是否成为瓶颈取决于 ping-pong 放在哪：放 SRAM 按专家流，DRAM 只承担激活。")


# ---------------------------------------------------------------- 7
def slide_coverage(prs):
    s = k.add_slide(prs, "按需加载", "专家覆盖率与阈值", half_life=("快变量",),
                    source="calc_pc.py coverage()（均匀路由）；v3.4 §6.4.2.2 覆盖率公式；真实路由需在目标模型上实测")
    pts = lambda E: [(d, round(p.coverage(d, experts=E) * 100, 2)) for d in (1, 2, 5, 10, 15, 20, 32, 50, 64, 80, 100, 150, 200)]
    k.xy_chart(s, I(0.45), I(1.05), I(6.4), I(3.85), {"每层 128 专家选 8": pts(128), "每层 256 专家选 8": pts(256)},
               colors=[k.TEAL, k.BLUE], x_title="本轮新增 token ΔL", y_title="被选中的专家比例（%）",
               x_range=(0, 200), y_range=(0, 100))
    k.formula_box(s, I(7.05), I(1.05), I(5.83), I(1.25), "覆盖率（均匀路由）", [
        k.fx("被选中比例 = 1 − (1 − k/E)^{ΔL}", s=11, b=True, c=k.TEALDK),
        _p("按需加载的流式量 = 覆盖率 × 100 GB；时间 = 流式量 ÷ B", 10)], s=11)
    rows = [[str(d), f"{p.coverage(d):.1%}", f"{p.coverage(d) * P['w_moe'] / B30:.2f} s", f"{p.coverage(d, experts=256):.1%}"]
            for d in (5, 10, 20, 32, 50, 100)]
    k.table(s, I(7.05), I(2.42), I(5.83), I(2.48), ["ΔL", "128 选 8", "30 GB/s 下加载", "256 选 8"], rows,
            col_w=[0.9, 1.5, 1.8, 1.6], s=10, first_col_bold=True, hl_rows=(3,), hl_color=k.BAND)
    _card(s, 0.45, 5.05, 6.4, 1.88, [
        _p("结论：方向对，收益只在极短输入", 11, k.TEALDK, True),
        _p("20 token 已要加载 72%，50 token 到 96%；每轮增量都在 300 以上时基本不触发", 10),
        _p("阈值：约 32 token（128 专家）/ 约 64 token（256 专家）；作为低成本机制先做上，规格测算不计入", 10, b=True),
        _p("按需加载要等本层路由算完才知道下一层用哪些专家 → 需路由预测提前加载，否则断流水", 10, k.MUTE)], fill=k.BAND)
    rows2 = [[f"{C / 1e9:.0f} GB", f"{p.e_round(3000) - p.e_round(3000, resident=C):.1f} J", f"{(P['w_moe'] - C) / B30:.2f} s"]
             for C in (10e9, 20e9, 40e9)]
    _h(s, 7.05, 5.05, 5.83, "同方向的更大杠杆：热门专家常驻 DRAM（若路由偏斜）", s_=10.5)
    k.table(s, I(7.05), I(5.38), I(5.83), I(1.2), ["常驻容量", "每轮净省（扣 DRAM 读）", "电池档首 token"], rows2,
            col_w=[1.6, 1.6, 2.6], s=10)
    k.text(s, I(7.05), I(6.6), I(5.83), I(0.35), [_p("假设常驻专家每轮都用到；与「DRAM 容量要小」对冲，先测路由分布再定。", 9.5, k.MUTE)])
    k.notes(s, "均匀路由是上界；真实路由偏斜时覆盖率更低，按需加载与热门专家常驻的收益都会更大。")


# ---------------------------------------------------------------- 8
def slide_hbf(prs):
    s = k.add_slide(prs, "闪存层", "带宽 · 瞬时功率 · 首 token", half_life=("快变量",),
                    source="calc_pc.py stream_time() / burst_power() / dl_hide()；读能耗参考 UFS 0.5 nJ/B（v3.4 §6.4.4）；定制方案见 sources/pc-cost-custom-nand.md §7")
    rows = []
    for b in (20e9, B30, B60, B117):
        rows.append([G(b), f"{p.stream_time(b):.2f} s", f"{p.burst_power(b):.0f} W", K(p.dl_hide(b)),
                     f"{p.e_hbf_max(b, 5) * 1e9:.3f}", f"{p.e_hbf_max(b, 15) * 1e9:.3f}"])
    k.table(s, I(0.45), I(1.05), I(7.6), I(2.2), ["HBF 带宽", "首 token ≥", "瞬时功率", "计算藏住流式需 ΔL ≥", "5 W 时允许 nJ/B", "15 W 时允许 nJ/B"],
            rows, col_w=[1.1, 1.1, 1.0, 1.7, 1.35, 1.35], s=10, first_col_bold=True, hl_rows=(1, 3), hl_color=k.BAND)
    pts_t = [(b, round(P['w_moe'] / (b * 1e9), 3)) for b in (10, 15, 20, 30, 45, 60, 80, 100, 117, 150)]
    pts_w = [(b, round(b * 1e9 * H['e_hbf'], 2)) for b in (10, 15, 20, 30, 45, 60, 80, 100, 117, 150)]
    k.xy_chart(s, I(8.25), I(1.05), I(4.63), I(2.6), {"首 token 下限（s）": pts_t}, colors=[k.RED],
               x_title="HBF 带宽（GB/s）", y_title="首 token 下限（s）", legend=False, x_range=(0, 150))
    k.xy_chart(s, I(8.25), I(3.75), I(4.63), I(2.6), {"瞬时功率（W）": pts_w}, colors=[k.AMBER],
               x_title="HBF 带宽（GB/s）", y_title="W（0.5 nJ/B）", legend=False, x_range=(0, 150))
    k.formula_box(s, I(0.45), I(3.36), I(7.6), I(1.84), "三条关系（W = 100 GB，F = 140 TOPS，N_act = 20B）", [
        k.fx("① 首 token ≥ W ÷ B（chat 轮次流式主导）", s=10),
        k.fx("② 瞬时功率 = B × e_{hbf}；每轮能耗 = W × e_{hbf} = 50 J，与 B 无关", s=10),
        k.fx("③ 计算藏住流式：ΔL ≥ W·F ÷ (2·N_{act}·B)", s=10),
        _p("带宽只换延迟、不换能耗：同样 50 J，带宽越高，释放得越集中", 10, k.RED, True),
        _p("表中 5 W / 15 W 是闪存瞬时功率预算的假设：5 W 与 NPU 满算力 4 W 同量级；15 W 为笔记本电池模式的宽松预算", 9, k.MUTE)], s=10)
    fa, fc = p.FLASH['A2'], p.FLASH['C']
    _card(s, 0.45, 5.3, 3.72, 1.63, [
        _p("电池档：30 GB/s", 11, k.TEALDK, True),
        _p(f"按 0.5 nJ/B：瞬时 {p.burst_power(B30):.0f} W；首 token ≥ {p.stream_time(B30):.2f} s", 9.5),
        _p(f"实现：A2，8 颗 512 Gb 当 pSLC（{fa['nj'][1]} nJ/B，约 {fa['p30']:.0f} W）；主机侧 PCIe 6.0 x8 或 UCIe", 9.5)], fill=k.BAND)
    _card(s, 4.33, 5.3, 3.72, 1.63, [
        _p("插电档：117 GB/s", 11, k.AMBER, True),
        _p(f"按 0.5 nJ/B：瞬时 {p.burst_power(B117):.0f} W；首 token ≥ {p.stream_time(B117):.2f} s", 9.5),
        _p(f"只有 C-full（HBF 级 4 层堆叠，{fc['nj'][1]} nJ/B）能在约 {fc['p117']:.0f} W 内做到；A / B 要 39–47 W", 9.5)], line=k.AMBER)
    k.text(s, I(8.25), I(6.45), I(4.63), I(0.5), [
        _p("117 GB/s 压到 5 W 需 ≤ 0.043 nJ/B；C-full 建模 0.05 / 0.08 / 0.12 nJ/B 对应 5.9 / 9.4 / 14 W，仍高于 5 W。", 9.5, k.RED, True)])
    k.notes(s, "带宽只决定首 token 延迟和瞬时功率，每轮能耗 = 100 GB × 每字节能耗，不随带宽变。电池档 30 GB/s 用现成 die 当 pSLC 即可；插电档 117 GB/s 只有 HBF 级小堆叠功耗可接受。")


# ---------------------------------------------------------------- 9
def slide_pim(prs):
    s = k.add_slide(prs, "3D-PIM", "4B decode：容量切分 · 速度 · 能耗",
                    source=f"{SRC_USER}（3D-PIM 1 TB/s、4 GB、0.5–1 pJ/bit）；calc.py kv_read_step()；calc_pc.py pim_tok_s() / pim_e_tok()")
    _h(s, 0.45, 1.05, 6.2, "4 GB 怎么分")
    k.box(s, I(0.45), I(1.42), I(3.1), I(0.6), [_p("4B 权重 4-bit：2 GB", 10.5, k.WHITE, True)], fill=k.TEAL, line=None)
    k.box(s, I(3.55), I(1.42), I(3.1), I(0.6), [_p(f"KV：2 GB ≈ {p.pim_contexts():.0f} 个 100K 上下文", 10.5, k.WHITE, True)],
          fill=k.AMBER, line=None)
    k.table(s, I(0.45), I(2.18), I(6.2), I(1.25), ["4B 的格式", "占用", "放得下吗"], [
        ["4-bit 权重 + 压缩 KV（890 B/token）", "2 GB + 89 MB / 100K", B("放得下")],
        ["INT8 权重", "4 GB", B("占满，KV 没地方", k.RED)],
        ["4-bit + FP16 GQA KV（147 KB/token）", "2 GB + 14.7 GB / 100K", B("放不下", k.RED)],
    ], col_w=[2.8, 1.9, 1.5], s=10)
    k.formula_box(s, I(0.45), I(3.6), I(6.2), I(1.65), "速度", [
        k.fx(f"每步读 = 权重 2 GB + KV（top-k 主 KV 1.8 MB + indexer 12.8 MB）≈ {(P['w_dec'] + p.pim_kv_step()) / 1e9:.3f} GB", s=10),
        k.fx(f"tok/s = 1 TB/s ÷ {(P['w_dec'] + p.pim_kv_step()) / 1e9:.3f} GB ≈ {p.pim_tok_s():.0f}", s=10.5, b=True, c=k.TEALDK),
        k.fx(f"300 token ≈ {300 / p.pim_tok_s():.2f} s；速度不是瓶颈，PIM 的价值在能耗", s=10)], s=10.5)
    rows = [
        ["3D-PIM 4-bit，0.5 pJ/bit", f"{p.pim_e_tok(0.5) * 1e3:.0f} mJ", f"{c.day_decode_tokens() * p.pim_e_tok(0.5) / 1e3:.1f} kJ"],
        ["3D-PIM 4-bit，1 pJ/bit", f"{p.pim_e_tok(1.0) * 1e3:.0f} mJ", f"{c.day_decode_tokens() * p.pim_e_tok(1.0) / 1e3:.1f} kJ"],
        ["片外 LPDDR 4-bit，6.25 pJ/bit", f"{p.off_e_tok() * 1e3:.0f} mJ", f"{c.day_decode_tokens() * p.off_e_tok() / 1e3:.1f} kJ"],
    ]
    _h(s, 6.85, 1.05, 6.03, "能耗：每 token 读 2 GB 权重")
    k.table(s, I(6.85), I(1.42), I(6.03), I(1.45), ["方案", "每 token", "重度使用日（20.4 万 token）"], rows,
            col_w=[2.6, 1.3, 2.1], s=10, hl_rows=(0, 1), hl_color=k.BAND)
    k.formula_box(s, I(6.85), I(3.02), I(6.03), I(1.0), "每 token 能耗 = 权重字节 × 8 × pJ/bit", [
        k.fx(f"2 GB × 8 × 0.5–1 pJ = {p.pim_e_tok(0.5) * 1e3:.0f}–{p.pim_e_tok(1.0) * 1e3:.0f} mJ（片外的 1/6–1/12）", s=10.5)],
                  s=10.5)
    _card(s, 6.85, 4.17, 6.03, 1.08, [
        _p("对 PIM 的四条要求", 10.5, k.TEALDK, True),
        _p("① 支持 ≤4-bit 权重 ② 逻辑 die 能算注意力与 softmax ③ 4B 用压缩 + 稀疏 KV ④ 映射写入走独立通道", 10)],
          fill=k.BAND)
    k.box(s, I(0.45), I(5.42), I(12.43), I(1.5), [
        [_r("结论：", 11.5, k.RED, True),
         _r(f"4 GB 容量把 4B 限定为 4-bit + 压缩 KV；decode 速度 {p.pim_tok_s():.0f} tok/s 绰绰有余，"
            f"一天 decode 只要 {DAY['decode'] / 1e3:.1f}–{DAY1['decode'] / 1e3:.1f} kJ。", 11, b=True)],
        _p("4B 的 KV 必须是压缩格式，KV 映射的目标格式也就必须是它——映射方案要和 4B 的注意力结构一起设计。", 10.5, k.RED)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "PIM 的价值在能耗：每 token 8–16 mJ，对比片外 100 mJ。容量 4 GB 决定了 4B 只能用 4-bit 权重加压缩 KV。")


# ---------------------------------------------------------------- 10
def slide_bridge(prs):
    s = k.add_slide(prs, "KV 映射", "本地桥：云桥的三个问题在 PC 上消失", half_life=("未验证",),
                    source="v3.4 §5.2（隐状态桥、5.2.3 三个未解决问题）；映射能力补回 50% 为团队自述（未经第三方验证）；calc_pc.py map_bytes_round()")
    k.table(s, I(0.45), I(1.05), I(7.4), I(2.3), ["问题（v3.4 §5.2.3）", "云桥", "PC 本地桥"], [
        ["隐私账", "个人记忆须随上下文上云", B("上下文不出机器")],
        ["版本耦合（最可能先杀死桥）", "云端按周迭代、端侧按季度 OTA，投影矩阵作废", B("两个模型 + 投影矩阵一起发布、一起升级")],
        ["传输", "89 MB @ 50 Mbps ≈ 14 s", B(f"内存写入：3K 轮约 {p.map_bytes_round(3000) / 1e6:.1f} MB")],
    ], col_w=[2.2, 2.6, 2.6], s=10, first_col_bold=True)
    _card(s, 0.45, 3.5, 7.4, 1.6, [
        _p("调度策略：prefill 全走 200B，decode 全在 PIM", 11, k.TEALDK, True),
        _p("每轮 200B 的输入：system prompt + 用户输入（会话开头），或上一轮 4B 输出 + 用户输入 / 工具返回", 10),
        _p(f"没有「短轮次」需要单独路由：chat 每轮约 {p.DL_CHAT} token，agent 均值约 3K", 10),
        _p("控制平面不需要在两个模型之间做轮次路由", 10, k.MUTE)], fill=k.BAND)
    k.formula_box(s, I(8.05), I(1.05), I(4.83), I(2.3), "每轮映射量", [
        k.fx("映射写入 = ΔL × 890 B（4B 侧压缩 KV）", s=10.5),
        k.fx(f"chat 350：{p.map_bytes_round(350) / 1e6:.2f} MB", s=10.5),
        k.fx(f"agent 3K：{p.map_bytes_round(3000) / 1e6:.2f} MB", s=10.5),
        _p("与 PIM 1 TB/s 相比可忽略；映射本身的计算量待团队给出", 10, k.MUTE)], s=10.5)
    _card(s, 8.05, 3.5, 4.83, 1.6, [
        _p("能力假设", 11, k.AMBER, True),
        _p("补回大小模型能力差距的 50%（团队自述，本评审按此计）", 10),
        _p("差距的另一半仍会丢：要质量时没有「200B 自己 decode」的退路", 10, k.RED)], line=k.AMBER)
    k.table(s, I(0.45), I(5.25), I(12.43), I(1.68), ["待验证（向映射团队要）", "为什么重要"], [
        ["200B → 4B 是 50:1，自述的 50% 是在什么比例下测的", "比例越悬殊，映射越难"],
        ["映射目标能否是压缩 + 稀疏 KV（890 B/token 级）", "PIM 容量只容得下这种格式"],
        ["多轮增量映射：每轮只映射新增 token，4B 的输出再回灌给 200B", "全部 prefill 走 200B 的前提"],
    ], col_w=[6.5, 5.93], s=10)
    k.notes(s, "云桥最致命的版本耦合在 PC 上自动消失；剩下的风险集中在映射本身：50:1 的比例、压缩 KV 目标格式、多轮增量。")


# ---------------------------------------------------------------- 11
def slide_energy(prs):
    s = k.add_slide(prs, "能耗", "每轮与每天的账", half_life=("快变量",),
                    source="calc_pc.py e_round() / day_energy() / battery_share()；重度使用日沿用 v3.4 §4.3")
    rows = []
    for lab, dl in (("chat · ΔL 350", p.DL_CHAT), ("agent · ΔL 3K", p.DL_AGENT)):
        comp = dl * p.e_comp_tok()
        dec = (300 * p.pim_e_tok(0.5), 300 * p.pim_e_tok(1.0))
        tot = (E_STREAM + comp + dec[0], E_STREAM + comp + dec[1])
        rows.append([lab, f"{E_STREAM:.0f} J", f"{comp:.1f} J", f"{dec[0]:.1f}–{dec[1]:.1f} J", B(f"{tot[0]:.1f}–{tot[1]:.1f} J"),
                     f"{E_STREAM / dl * 1e3:.1f} mJ / {p.e_comp_tok() * 1e3:.2f} mJ"])
    k.table(s, I(0.45), I(1.05), I(12.43), I(1.15), ["一轮（0.5 nJ/B）", "HBF 流式", "200B 计算", "4B decode 300 token（0.5–1 pJ/bit）", "合计", "每 token：流式 / 计算"],
            rows, col_w=[1.8, 1.4, 1.4, 2.1, 1.4, 2.6], s=10, first_col_bold=True)
    pre_stream = p.day_rounds() * E_STREAM
    pre_comp = p.day_prefill_tokens() * p.e_comp_tok()
    gf = k.chart(s, I(0.45), I(2.4), I(6.3), I(3.0), "barh", ["4B decode（PIM）", "200B 计算", "HBF 流式"],
                 {"kJ / 天": [round(DAY['decode'] / 1e3, 2), round(pre_comp / 1e3, 2), round(pre_stream / 1e3, 1)]},
                 colors=[k.RED], legend=False, x_title=None, y_title="kJ / 天")
    k.formula_box(s, I(6.95), I(2.4), I(5.93), I(3.0), "重度使用日（prefill 全走 200B）", [
        k.fx(f"HBF 流式 = {p.day_rounds()} 轮 × 50 J = {pre_stream / 1e3:.1f} kJ", s=10.5),
        k.fx(f"200B 计算 = {p.day_prefill_tokens() / 1e4:.0f} 万 × {p.e_comp_tok() * 1e3:.2f} mJ = {pre_comp / 1e3:.2f} kJ", s=10.5),
        k.fx(f"4B decode = {p.day_decode_tokens() / 1e4:.1f} 万 × 8–16 mJ = {DAY['decode'] / 1e3:.1f}–{DAY1['decode'] / 1e3:.1f} kJ", s=10.5),
        k.fx(f"合计 {DAY['total'] / 1e3:.1f}–{DAY1['total'] / 1e3:.1f} kJ", s=11, b=True, c=k.TEALDK),
        k.fx(f"÷ 252–360 kJ = {SH_LO:.1%}–{SH1_HI:.1%} 电池", s=11, b=True, c=k.TEALDK),
        _p(f"若两层 ping-pong 放 DRAM，每天再多 {p.day_rounds() * 2 * P['w_moe'] * H['e_dram'] / 1e3:.1f} kJ", 10, k.MUTE)], s=10.5)
    sens = []
    for lab, nj in (("普通 SSD 堆 die", 0.55), ("参考 UFS（本页口径）", 0.50), ("A2 pSLC", 0.40), ("C-full HBF 级", 0.08)):
        d = p.day_energy_nj(nj); lo, hi = p.battery_share(d['total'])
        sens.append([lab, f"{nj:.2f}", f"{P['w_moe'] * nj * 1e-9:.0f} J", f"{d['total'] / 1e3:.1f} kJ", f"{lo:.1%}–{hi:.1%}"])
    _h(s, 0.45, 5.45, 6.3, "按闪存实现的读能耗（基准值）", s_=10.5)
    k.table(s, I(0.45), I(5.76), I(6.3), I(1.18), ["闪存实现", "nJ/B", "每轮流式", "一天合计", "电池占比"], sens,
            col_w=[1.9, 0.7, 1.0, 1.2, 1.5], s=9, first_col_bold=True, hl_rows=(3,), hl_color=k.BAND)
    k.box(s, I(6.95), I(5.55), I(5.93), I(1.38), [
        [_r("结论：", 11, k.RED, True),
         _r(f"按 0.5 nJ/B、0.5 pJ/bit：能耗 {DAY['prefill'] / DAY['total']:.0%} 在 prefill（HBF 流式占 {pre_stream / DAY['total']:.0%}），decode 已被 PIM 压到很小。", 10.5, b=True)],
        _p("HBF 每字节读能耗是整套方案最关键的参数：它同时决定每天的电量和 prefill 期间的瞬时功率。", 10.5, k.RED)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "chat 每 token 流式能耗是计算的 125 倍，agent 3K 是 15 倍。HBF 读能耗从 0.5 降到 0.13 nJ/B，一天从约 38 kJ 降到约 13 kJ。")


# ---------------------------------------------------------------- 12
def slide_spec(prs):
    s = k.add_slide(prs, "规格", "IP 规格总表", source=f"{SRC_USER}；calc_pc.py")
    rows = [
        ["NPU", "200 TOPS @W4A8（有效 140）；支持 FP4（E2M1）权重；片上 SRAM ≥ 64 MB",
         f"prefill {p.tok_rate():,.0f} tok/s；SRAM = 专家双缓冲 26 MB + 一层激活 21.5 MB + 余量"],
        ["HBF", "定制高带宽闪存，128–171 GB（<256 GB），直接供给 NPU、按专家顺序流；电池档 A2（8 颗 512 Gb 当 pSLC，30 GB/s）；全档 C-full（HBF 级 4 层堆叠 + UCIe）",
         f"首 token ≥ {p.stream_time(B30):.2f}（30 GB/s）/ {p.stream_time(B117):.2f} s（117 GB/s）"],
        ["HBF 读能耗", "本文口径参考 UFS 0.5 nJ/B；A2 约 0.40、C-full 建模 0.08 nJ/B", "整套方案第一待测项"],
        ["DRAM", f"{G(H['b_dram'])}；AI 部分 2–4 GB", f"prefill 时分发激活约 {p.dram_bw_need(3000, False) / 1e9:.0f} GB/s；200B 的 KV 89 MB / 100K"],
        ["3D-PIM", "1 TB/s · 4 GB · 0.5–1 pJ/bit；逻辑 die 算 GEMV + 注意力；支持 ≤4-bit 权重",
         f"4B {p.pim_tok_s():.0f} tok/s；KV 余 2 GB ≈ {p.pim_contexts():.0f} 个 100K 上下文"],
        ["KV 映射", "200B 新增 token 的 KV → 4B 压缩 KV，写入 PIM", f"3K 轮 {p.map_bytes_round(3000) / 1e6:.1f} MB；能力按补回 50% 计"],
        ["控制平面", "prefill 全走 200B、decode 全在 PIM；按需加载阈值约 32 token；HBF 两档切换", "system prompt 的 KV 复用"],
    ]
    k.table(s, I(0.45), I(1.05), I(12.43), I(5.0), ["模块", "规格", "依据 / 数字"], rows,
            col_w=[1.5, 5.9, 5.03], s=10.5, first_col_bold=True, hl_rows=(2,))
    k.text(s, I(0.45), I(6.2), I(12.43), I(0.7), [
        _p("不需要：200B 常驻 DRAM（省掉约 100 GB 内存）、DRAM 层级 ping-pong、200B 与 4B 之间的轮次路由、投机解码。", 10.5, k.TEALDK, True)])
    k.notes(s, "规格表的每一行都对应前面一页的推导；HBF 读能耗是唯一决定性的未知参数。")




# ================= 成本页 =================
SRC_LP = "sources/pc-cost-logic-pim.md（LP-S#）"
SRC_PM = "sources/pc-cost-memory-prices.md（PM-S#）"
SRC_NB = "sources/pc-cost-nand-bandwidth.md（NB-S#）"
SRC_CN = "sources/pc-cost-custom-nand.md（CN-S#）"


def slide_cost_logic(prs):
    s = k.add_slide(prs, "成本①", "NPU 与 3D-PIM 的硅成本拆解", half_life=("快变量",),
                    source=f"{SRC_LP}：S1/S6 晶圆价、S10 NPU 面积、S17 SRAM、S20/S23 3D DRAM、S39 W2W 良率、S43 DRAM 密度；calc_pc.py")
    C = p.COST
    _h(s, 0.45, 1.05, 6.1, "NPU 200 TOPS + 64 MiB SRAM（N3，SoC 边际成本）")
    k.table(s, I(0.45), I(1.4), I(6.1), I(1.55), ["情景", "NPU 阵列", "64 MiB SRAM", "合计面积", "N3 晶圆", "边际硅成本"], [
        ["乐观", "14.3 mm²（7 TOPS/mm²）", "21.1 mm²", "35.4 mm²", "$20k", B(f"{Y(C['npu_usd'][0])}（${C['npu_usd'][0]:.0f}）")],
        ["基准", "22.2 mm²（4.5 TOPS/mm²）", "24.1 mm²", "46.3 mm²", "$23k", B(f"{Y(C['npu_usd'][1])}（${C['npu_usd'][1]:.0f}）")],
        ["悲观", "43.5 mm²（2.3 TOPS/mm²）", "30.7 mm²", "74.2 mm²", "$27k", B(f"{Y(C['npu_usd'][2])}（${C['npu_usd'][2]:.0f}）")],
    ], col_w=[0.6, 1.55, 0.95, 0.85, 0.7, 1.45], s=9.5, first_col_bold=True)
    k.formula_box(s, I(0.45), I(3.1), I(6.1), I(1.62), "算法", [
        k.fx("面积 = 100 TOPS(INT8) ÷ TOPS/mm² + 536.9 Mbit ÷ (31.8 Mb/mm² × 有效率)", s=9.5),
        k.fx("良率 Y = [(1 − e^{−A·D0}) ÷ (A·D0)]²（Murphy；N3 D0 取 0.08–0.10，为 2028–29 成熟期假设，LP-S6 报道 0.14）", s=9),
        k.fx("边际成本 = 加上 ΔA 后的良品 die 成本 − 原 SoC 良品 die 成本", s=9.5),
        _p("面积唯一的同行评审锚点：三星 4nm NPU 3.45 TOPS/mm²（INT8）；苹果 / 高通 / AMD 的 NPU 面积在付费报告里", 9, k.MUTE)],
                  s=9.5)
    _card(s, 0.45, 4.85, 6.1, 0.95, [
        _p("另计：SoC 侧接 3D-PIM 的 PHY / 控制器约 3 mm²，边际约 $1.7；N3E 的 SRAM 不缩小，换 N2 成本基本不变（基准 $28）", 9.5),
        _p("PC 已有 40–50 TOPS 的 NPU，可部分抵扣，本表按全额计", 9.5, k.MUTE)], fill=k.SLATEF)

    _h(s, 6.78, 1.05, 6.1, "4 GB 3D-PIM（1 层 DRAM 与成熟节点逻辑 W2W 混合键合）")
    k.table(s, I(6.78), I(1.4), I(6.1), I(1.55), ["情景", "DRAM 密度", "占地", "逻辑节点", "堆叠良率", "正常周期", "2026 价格"], [
        ["乐观", "0.40 Gb/mm²", "85 mm²", "12nm", "0.87", B(Y(C['pim_n'][0])), Y(C['pim_h'][0])],
        ["基准", "0.25 Gb/mm²", "136 mm²", "16/12nm", "0.80", B(Y(C['pim_n'][1])), Y(C['pim_h'][1])],
        ["悲观", "0.16 Gb/mm²", "212 mm²", "7nm", "0.68", B(Y(C['pim_n'][2])), Y(C['pim_h'][2])],
    ], col_w=[0.6, 1.0, 0.75, 0.85, 0.8, 1.05, 1.05], s=9.5, first_col_bold=True)
    k.table(s, I(6.78), I(3.1), I(6.1), I(1.0), ["基准 · 正常周期拆分", "DRAM", "逻辑 die", "键合", "封装测试", "合计"], [
        ["良率摊销后", "$27.4", "$14.8", "$1.9", "$5.0", B(f"$49.1（{Y(49.1)}）")],
    ], col_w=[1.6, 0.8, 0.9, 0.7, 0.9, 1.2], s=9.5, first_col_bold=True)
    k.formula_box(s, I(6.78), I(4.25), I(6.1), I(1.55), "算法与参照", [
        k.fx("Y_{stack} = Y_{logic} × Y_{DRAM} × Y_{bond}（W2W 没法挑好 die，良率连乘）", s=9.5),
        _p("密度参照：标准 LPDDR5X 0.435 Gb/mm²；ATLAS 推出 0.2；ISSCC 2026 边缘芯片约 0.05", 9.5),
        _p("基准 / 乐观密度高于已发表值，前提是 W2W 把 DRAM 外围电路移到逻辑 die", 9.5, k.RED),
        _p("规格对得上：ATLAS 每核 5 GB、1 TB/s、0.66–0.88 pJ/bit（云端测试芯片，7nm 逻辑）", 9.5)], s=9.5)
    k.box(s, I(0.45), I(5.95), I(12.43), I(0.98), [
        [_r("读法：", 11, k.RED, True),
         _r(f"逻辑部分稳定在 ¥100–400；3D-PIM 由 DRAM 位价格主导：同一基准方案，正常周期 {Y(C['pim_n'][1])}，"
            f"按 2026 年 DRAM 价格（约 $15/GB）{Y(C['pim_h'][1])}。", 11, b=True)],
        _p("键合本身每颗只要 $1–6；把成本放大的是 W2W 良率连乘和定制 DRAM 的密度惩罚。", 10, k.MUTE)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "NPU 按 100 TOPS INT8 定尺寸；3D-PIM 的最大变量是 DRAM 位价格，其次是定制 3D DRAM 的密度和键合良率。")


def slide_cost_flash(prs):
    s = k.add_slide(prs, "成本②", "闪存层：定制高带宽、小容量 NAND", half_life=("快变量",),
                    source="sources/pc-cost-custom-nand.md（CN-S1~S5 XL-FLASH、S6/S7 Z-NAND、S12~S16 HBF）、pc-cost-nand-bandwidth.md；calc_pc.py FLASH")
    F = p.FLASH
    _card(s, 0.45, 1.05, 4.05, 1.38, [
        _p("① 带宽由 die 数决定", 10.5, k.TEALDK, True),
        _p("普通 1 Tb TLC die 只有 1.6–1.9 GB/s；30 GB/s 要 17–19 颗、2.2–2.4 TB——为了带宽被迫买 20 倍容量", 9.5)], fill=k.SLATEF)
    _card(s, 4.64, 1.05, 4.05, 1.38, [
        _p("② 每 die 的上限在通道，不在阵列", 10.5, k.TEALDK, True),
        _p("8 bit 通道 @4.8 GT/s 约 4.3 GB/s；die 不加宽 I/O（双端口、x16、TSV），plane 再多也白搭", 9.5)], fill=k.SLATEF)
    _card(s, 8.83, 1.05, 4.05, 1.38, [
        _p("③ 小容量 die 的面积由外围决定", 10.5, k.TEALDK, True),
        _p("页缓冲 ≈ 每 die 带宽 × tR → 小容量高带宽应做 SLC、小 plane、短 tR（XL-FLASH：128 Gb SLC、16 plane、tR 4 µs）", 9.5)], fill=k.SLATEF)

    def rng(t):
        return f"{Y(t[1])}（{Y(t[0])}–{Y(t[2])}）"
    rows = []
    for key in ('base', 'A2', 'B', 'C'):
        f = F[key]
        rows.append([f['name'], f['bw_die'], f"{f['d30']} / {f['cap30']}", rng(f['c30_n']), Y(f['c30_h'][1]),
                     f"{f['d117']} / {f['cap117']}", f"{Y(f['c117_n'][1])} / {Y(f['c117_h'][1])}",
                     f"{f['nj'][1]:.2f}", f"{f['p30']:g} / {f['p117']:g} W"])
    k.table(s, I(0.45), I(2.55), I(12.43), I(2.15),
            ["方案", "每 die GB/s", "30 GB/s：die / 容量", "30 GB/s 成本（正常周期）", "2026 价格", "117 GB/s：die / 容量",
             "117 GB/s 成本 正常 / 2026", "nJ/B", "30 / 117 GB/s 功耗"],
            rows, col_w=[2.45, 0.85, 1.45, 1.75, 0.85, 1.45, 1.55, 0.6, 1.1], s=9, first_col_bold=True, hl_rows=(1, 3), hl_color=k.BAND)
    k.text(s, I(0.45), I(4.82), I(12.43), I(0.3), [
        _p("正常周期 NAND TLC $0.04–0.08/GB，2026 价格 $0.23–0.34/GB；成本含 die、主控 / base die、封装测试，不含定制 die 的 NRE（每 $10M 摊到 100 万台约 ¥71/台）。", 9, k.MUTE)])
    da, dc = p.day_energy_nj(F['A2']['nj'][1])['total'], p.day_energy_nj(F['C']['nj'][1])['total']
    _card(s, 0.45, 5.2, 4.05, 1.73, [
        _p("电池档推荐：A2", 11, k.TEALDK, True),
        _p(f"现成 512 Gb die 当 pSLC，8 颗约 171 GB；不用新 NAND 流片，只要 8–10 通道定制主控", 9.5),
        _p(f"{Y(F['A2']['c30_n'][1])}（正常周期）· 约 {F['A2']['p30']:g} W · 主机侧 PCIe 6.0 x8 或 UCIe", 9.5, k.TEALDK, True),
        _p(f"代价：比 C-full 每天多耗约 {(da - dc) / 1e3:.0f} kJ（{(da - dc) / H['battery_j'][1]:.0%}–{(da - dc) / H['battery_j'][0]:.0%} 电池）；"
           f"电量优先时可选 C-full，多 {Y(F['C']['c30_n'][1] - F['A2']['c30_n'][1])}（2026 多 {Y(F['C']['c30_h'][1] - F['A2']['c30_h'][1])}）", 9, k.MUTE)], fill=k.BAND)
    _card(s, 4.64, 5.2, 4.05, 1.73, [
        _p("全档推荐：C-full", 11, k.AMBER, True),
        _p("HBF 级 die 4 层堆叠 128 GB，一套覆盖 30–117 GB/s（约 400 GB/s 受接口限制）", 9.5),
        _p(f"{Y(F['C']['c30_n'][1])} · 117 GB/s 只要约 {F['C']['p117']:g} W · 每轮流式 {P['w_moe'] * F['C']['nj'][1] * 1e-9:.0f} J", 9.5, k.AMBER, True)],
          line=k.AMBER)
    _card(s, 8.83, 5.2, 4.05, 1.73, [
        _p("B 两头不占优", 11, k.MUTE, True),
        _p("30 GB/s 不比 A2 便宜，还要新 die 流片；117 GB/s 要 24–38 条通道、约 39 W，功耗远高于 C", 9.5),
        _p("C 的风险：HBF 级 core die 的面积、tR、端侧小批量供货都无一手数据", 9.5, k.RED)], fill=k.SLATEF)
    k.notes(s, "电池档用现成 die 当 pSLC 最便宜；插电档只有 HBF 级小堆叠能把功耗压到十瓦以内。所有方案在 2026 价格下约乘 3–4 倍，排序不变。")


def slide_cost_total(prs):
    s = k.add_slide(prs, "成本③", "合计 · 价格周期 · 对照", half_life=("快变量",),
                    source="calc_pc.py cost_total() / cost_resident_dram()；sources/pc-cost-logic-pim / memory-prices / custom-nand.md；不含 NRE 与毛利")
    opts = [
        ("主盘兼任 · 基线 PC 已有 2 TB", p.cost_flash_shared2tb(), p.cost_flash_shared2tb(), "28 GB/s（PCIe 6.0 x4，2028+）", 0.55),
        ("主盘兼任 · 基线 1 TB → 16 颗 512 Gb", p.cost_flash_small_die('n'), p.cost_flash_small_die('h'), "28 GB/s（同上）", 0.55),
        ("A2 定制 pSLC", p.cost_flash('A2', 'n'), p.cost_flash('A2', 'h'), "30 GB/s", 0.40),
        ("C-full HBF 级堆叠", p.cost_flash('C', 'n'), p.cost_flash('C', 'h'), "30–117 GB/s", 0.08),
    ]
    rows, base_n, base_h = [], [], []
    for lab, fn, fh, bw, nj in opts:
        tn, th = p.cost_total(fn, 'n'), p.cost_total(fh, 'h')
        base_n.append(tn[1]); base_h.append(th[1])
        d = p.day_energy_nj(nj)
        rows.append([lab, bw, Y(fn[1]), f"{Y(tn[0])} / ", B(Y(tn[1])), f" / {Y(tn[2])}", Y(th[1]), f"{d['total'] / 1e3:.0f} kJ"])
    rows = [[r[0], r[1], r[2], [[{"t": r[3]}, {"t": Y(base_n[i]), "b": True, "c": k.TEALDK}, {"t": r[5]}]], r[6], r[7]]
            for i, r in enumerate(rows)]
    k.table(s, I(0.45), I(1.05), I(12.43), I(2.15),
            ["闪存路径", "带宽", "闪存增量（正常基准）", "AI 子系统合计 · 正常周期（乐观 / 基准 / 悲观）", "2026 价格（基准）", "一天电量"],
            rows, col_w=[2.9, 2.1, 1.5, 3.2, 1.45, 1.28], s=9.5, first_col_bold=True)
    k.text(s, I(0.45), I(3.22), I(12.43), I(0.3), [
        _p(f"合计 = NPU + 64 MB SRAM（{' / '.join(Y(x) for x in p.COST['npu_usd'])}）+ 4 GB 3D-PIM（正常 {' / '.join(Y(x) for x in p.COST['pim_n'])}；"
           f"2026 价格基准 {Y(p.COST['pim_h'][1])}）+ 闪存。一天电量按读能耗基准：主盘兼任 0.55、A2 0.40、C-full 0.08 nJ/B。", 9, k.MUTE)])
    rn, rh = p.cost_resident_dram('n'), p.cost_resident_dram('h')
    cats = ["200B 常驻 DRAM（只算 128 GB）", "C-full HBF 级", "A2 定制 pSLC", "主盘兼任（基线 1 TB）", "主盘兼任（基线 2 TB）"]
    vn = [round(p.cny(rn[1])), round(p.cny(base_n[3])), round(p.cny(base_n[2])), round(p.cny(base_n[1])), round(p.cny(base_n[0]))]
    vh = [round(p.cny(rh[1])), round(p.cny(base_h[3])), round(p.cny(base_h[2])), round(p.cny(base_h[1])), round(p.cny(base_h[0]))]
    k.chart(s, I(0.45), I(3.55), I(6.6), I(3.38), "barh", cats, {"正常周期（基准）": vn, "2026 价格（基准）": vh},
            colors=[k.TEAL, k.RED], y_title="¥", number_format='#,##0')
    oa, oc = p.cost_total(p.cost_flash('A2', 'n'), 'n')[0], p.cost_total(p.cost_flash('C', 'n'), 'n')[0]
    _card(s, 7.25, 3.55, 5.63, 1.5, [
        _p("「几百元」成立的条件", 11, k.TEALDK, True),
        _p(f"同时满足：DRAM / NAND 回到正常周期，且闪存走主盘兼任（基准 {Y(base_n[0])}–{Y(base_n[1])}）或 A2 / C-full 的乐观情景（{Y(oa)} / {Y(oc)}）", 9.5),
        _p(f"推荐的 A2 / C-full 基准为 {Y(base_n[2])} / {Y(base_n[3])}；按 2026 价格，基准情景各路径 ≥ {Y(base_h[0])}", 9.5, k.RED, True)], fill=k.BAND)
    _card(s, 7.25, 5.13, 5.63, 1.8, [
        _p("对照：200B 常驻 DRAM（100 GB 权重 + 余量，按 128 GB）", 11, k.INK, True),
        _p(f"正常周期 {Y(rn[1])}（按 $2.5/GB；{Y(rn[0])}–{Y(rn[2])}）；2026 价格 {Y(rh[1])}（按 $20/GB；按 $15/GB 为 {Y(128 * 15)}）", 9.5),
        _p(f"基准情景下本方案正常周期便宜 {rn[1] / max(base_n):.1f}–{rn[1] / min(base_n):.1f} 倍，高位便宜 {rh[1] / max(base_h):.0f}–{rh[1] / min(base_h):.0f} 倍；"
           "悲观情景下 C-full 反比常驻 DRAM 贵", 9.5),
        _p("对照只计 DRAM 颗粒，本方案侧还含 NPU 与 PIM；常驻 DRAM 的首 token 不用等闪存流式", 9),
        _p("另计：芯片厂毛利使逻辑部分采购价 ×1.7–2.5；定制 die / 主控的 NRE 按出货量摊销", 9, k.MUTE)], line=k.SLATE)
    k.notes(s, "成本的第一变量是存储器价格周期：同一方案在 2026 价格下约是正常周期的 2.3–3.2 倍。几百元要同时满足正常周期价格和主盘兼任（或 A2 / C-full 的乐观情景）。")


def slide_risks(prs):
    s = k.add_slide(prs, "风险", "待验证与待测清单", source="sources/pc-cost-custom-nand / nand-bandwidth / logic-pim / memory-prices.md；v3.4 §5.2")
    k.table(s, I(0.45), I(1.05), I(12.43), I(5.15), ["#", "项", "为什么关键", "怎么验证"], [
        ["1", "闪存读能耗（nJ/B）", "决定每天电量与 prefill 瞬时功率；0.5 → 0.08 nJ/B，一天从约 38 kJ 降到约 9 kJ", "A2 原型实测；C-full 等 HBF 样品（2027）"],
        ["2", "存储器价格周期", "同一方案在 2026 价格下约是正常周期的 2.3–3.2 倍；决定「几百元」是否成立", "跟踪 2027–2028 DRAM / NAND 合约价（TrendForce、CFM）"],
        ["3", "HBF 级 core die 的端侧供货", "C-full 是唯一能让插电档 117 GB/s 控制在约 9 W 的路径", "与原厂确认小容量堆叠、面积、tR 与最小批量"],
        ["4", "3D-PIM 的 DRAM 密度与键合良率", "定制 3D DRAM 已发表 0.05–0.2 Gb/mm²，低于标准品 0.435；密度决定面积与良率", "流片前用 ATLAS / ISSCC 2026 数据校准；做 1 层与 2–4 层对比"],
        ["5", "PIM 支持 ≤4-bit 权重、逻辑 die 算注意力", "4 GB 容量只容得下 4-bit 权重 + 压缩 KV", "逻辑 die 架构评估"],
        ["6", "KV 映射质量", "50:1、压缩 + 稀疏 KV 目标格式、多轮增量映射；能力补回 50% 为团队自述", "向映射团队要在这三个条件下的评测"],
        ["7", "真实路由的专家覆盖率", "决定按需加载与热门专家常驻 DRAM 的收益", "在目标 200B 上测「新增 token 数 → 用到的专家数」曲线"],
        ["8", "读干扰后台搬移", "每天反复读同一批 100 GB 会触发读干扰处理（SIGMETRICS 2026 已证实影响存在）", "原型上测阈值与带宽损失"],
        ["9", "主机接口", "30 GB/s 需 PCIe 6.0 x8 或 UCIe；117 GB/s 需 UCIe 共封装", "平台通道预算评估"],
    ], col_w=[0.35, 2.6, 5.4, 4.08], s=9.5, first_col_bold=True, hl_rows=(0, 1), hl_color=k.REDLT)
    k.text(s, I(0.45), I(6.35), I(12.43), I(0.55), [
        _p("前两项决定方案成立与否：读能耗决定能不能用，价格周期决定卖不卖得动。", 10.5, k.RED, True)])
    k.notes(s, "九项里，闪存读能耗和存储器价格周期是决定性的；其余是工程风险。")


def slide_refs(prs):
    s = k.add_slide(prs, "出处", "来源与假设", source="本页列出全部计算与调研文件；路径相对 surveys/on-device-ai-compute-arch/")
    k.table(s, I(0.45), I(1.05), I(6.1), I(3.0), ["文件", "内容"], [
        ["calc_pc.py · tests/test_pc.py", "本 PPT 全部派生数字与成本模型；测试锁定"],
        ["calc.py", "参数基线（e_op、KV 890 B/token、重度使用日）"],
        ["端侧AI计算架构完整构想_v3.4_润色版.md", "§4.3 负载、§5.2 隐状态桥、§6.4 UFS 流式"],
        ["sources/pc-cost-memory-prices.md", "DRAM / NAND / SSD / HBM / HBF 价格（PM-S1~S33）"],
        ["sources/pc-cost-nand-bandwidth.md", "每 die 吞吐、SSD 能耗、HBF 每 die 带宽（NB-S1~S36）"],
        ["sources/pc-cost-logic-pim.md", "晶圆价、NPU 面积、SRAM、3D-PIM 成本（LP-S1~S46）"],
        ["sources/pc-cost-custom-nand.md", "XL-FLASH、Z-NAND、HBF 结构，定制方案核算（CN-S1~S44）"],
    ], col_w=[2.9, 3.2], s=9.5, first_col_bold=True)
    k.table(s, I(6.78), I(1.05), I(6.1), I(3.0), ["关键外部来源", "用于"], [
        ["SanDisk HBF Fact Sheet（2025-07，NB-S20）", "256 Gb/die、16 die、512 GB、1.6 TB/s"],
        ["Kioxia XL-FLASH，ISSCC 2020（CN-S5）", "128 Gb SLC、16 plane、tR 4 µs"],
        ["ATLAS，arXiv 2604.08044（LP-S23）", "3D DRAM：每核 5 GB、1 TB/s、0.66–0.88 pJ/bit"],
        ["三星 4nm NPU，ISSCC 2022（LP-S10）", "3.45 TOPS/mm²（INT8）"],
        ["CFM / TrendForce 价格页（PM-S7、PM-S11）", "2026-10 DRAM、NAND 价格"],
        ["Samsung 9100 PRO 规格书（NB-S6）", "SSD 读功耗 → nJ/B"],
    ], col_w=[3.2, 2.9], s=9.5, first_col_bold=True)
    _card(s, 0.45, 4.25, 12.43, 2.68, [
        _p("与用户对齐的假设（2026-10）", 11, k.TEALDK, True),
        _p("负载：200B-A20B MoE（专家 FP4）做 prefill；4B dense（4-bit）做 decode；中间 KV 映射，能力补回 50%。prefill 全走 200B，decode 全在 3D-PIM。", 10),
        _p("硬件：NPU 200 TOPS @W4A8、MFU 70%；DRAM 153 GB/s；3D-PIM 1 TB/s、4 GB、0.5–1 pJ/bit；200B 与 4B 都用压缩 KV（890 B/token）。", 10),
        _p("闪存：读能耗参考 UFS 0.5 nJ/B；定制高带宽、小容量（<256 GB）NAND。", 10),
        _p("成本：AI 子系统增量制造成本，不含 NRE 与毛利；基线 PC 两种（已有 2 TB 主盘 / 只有 1 TB）都列；DRAM / NAND 价格按正常周期与 2026 高位两种口径都列；1 USD ≈ 7.1 CNY。", 10),
        _p("假设项：路由结构（60 层、每层 128 专家选 8、隐藏维 7168）、重度使用日沿用 v3.4 §4.3、PCIe 6.0 主控溢价 $5–20（无公开价）。", 10, k.MUTE)],
          fill=k.SLATEF)
    k.notes(s, "所有数字都能追到 calc_pc.py 或 sources/ 下的调研文件；调研文件里每个数字都标了日期、来源和置信度。")


def build(prs):
    for fn in (slide_cover, slide_abstract, slide_baseline, slide_arch, slide_timeline, slide_intensity,
               slide_coverage, slide_hbf, slide_pim, slide_bridge, slide_energy, slide_spec,
               slide_cost_logic, slide_cost_flash, slide_cost_total, slide_risks, slide_refs):
        fn(prs)

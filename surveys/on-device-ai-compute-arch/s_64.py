# -*- coding: utf-8 -*-
"""6.4 UFS 流式大模型（第 42–48 页）。所有数字由 calc 计算后格式化。"""
from math import log10
from pptx.util import Inches as I
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import calc as c
import pptkit as k

F4 = c.f_eff('W4A8')
TT = c.t_tok(c.N_BIG, F4)                      # 30B 每 token 时间
T_STREAM5 = c.W_BIG / c.B_UFS['UFS5']
T_STREAM4 = c.W_BIG / c.B_UFS['UFS4']
BE5 = c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_BIG, F4)
BE4 = c.break_even(c.W_BIG, c.B_UFS['UFS4'], c.N_BIG, F4)
E_COMP = c.e_comp_tok(c.N_BIG)
DLE = c.energy_break_even(c.W_BIG, c.N_BIG)


def K(x, nd=2):
    return f"{x / 1e3:.{nd}f}K"


def _p(t, s=11, c_=k.INK, b=False):
    return [{"t": t, "s": s, "c": c_, "b": b}]


# ---------------------------------------------------------------- 42
def slide_6_4(prs):
    s = k.add_slide(prs, "6.4", "重 Prefill 的第三条路：UFS 流式大模型", half_life=("快变量",),
                    source="v3.4 §6.4、§5.4；calc.py")
    x0, w, h = 0.6, 3.6, 0.82
    ys = [1.2, 2.55, 3.9, 5.25]
    boxes = [("UFS 5.0 存储", "30B dense INT4 · 15 GB · 60 层 × 250 MB"),
             ("LPDDR6 中转 + 动态驻留区", "双缓冲 2 层 500 MB · 驻留容量 C（任务后回收）"),
             ("NPU 大 MAC 阵列", f"200 TOPS @W4A8 × 70% = {F4 / 1e12:.0f} TOPS 有效"),
             ("常驻 8B INT4 小模型 · decode",
              f"113.8 GB/s ÷ 4 GB ≈ {c.decode_tok_s(c.W_MID):.0f} tok/s")]
    for i, (y, (t1, t2)) in enumerate(zip(ys, boxes)):
        hot = i in (1, 2)
        k.box(s, I(x0), I(y), I(w), I(h), [_p(t1, 12, b=True), _p(t2, 10, k.MUTE)],
              fill=k.BAND if hot else k.SLATEF, line=k.TEAL if hot else k.SLATE)
    labels = ["10.8 GB/s · 每轮流 W − C", "113.8 GB/s · tile 进 SRAM", "消化结果交给小模型（端内桥）"]
    cx = x0 + w / 2
    for i, lab in enumerate(labels):
        y1, y2 = ys[i] + h, ys[i + 1]
        k.arrow(s, I(cx), I(y1), I(cx), I(y2), color=k.TEAL, w=1.75)
        k.text(s, I(cx + 0.12), I(y1 + 0.06), I(3.3), I(0.4), [_p(lab, 10, k.TEALDK)])

    k.text(s, I(6.0), I(1.1), I(6.88), I(0.9), [
        [{"t": "可行性核心：", "b": True, "s": 12},
         {"t": "prefill 算力受限，慢速供权重可藏在高算术强度之下。", "s": 12}],
        [{"t": "本质：把「云-桥-端」压缩进单设备——超大模型逐层流式做 prefill，常驻小模型做 decode。",
          "s": 11, "c": k.MUTE}]])
    k.table(s, I(6.0), I(2.05), I(6.88), I(2.35), ["参数", "取值", "说明"], [
        ["权重 W", "30×10⁹ × 0.5 B = 15 GB", "INT4 dense"],
        ["单层", "15 GB ÷ 60 ≈ 250 MB", "双缓冲 500 MB"],
        ["有效算力 F_eff", f"200 TOPS × 70% = {F4 / 1e12:.0f} TOPS", "W4A8"],
        ["每 token 时间 t_tok", f"2N ÷ F_eff = {TT * 1e3:.2f} ms", "calc.t_tok"],
        ["UFS 带宽 B_ufs", "10.8 GB/s（UFS 5.0）", "JESD220H，2026-02"],
        ["平衡点 ΔL*", f"{K(BE5)}（UFS 4.0：{K(BE4)}）", "见 6.4.2"],
    ], col_w=[1.5, 2.6, 1.6], s=10)
    k.table(s, I(6.0), I(4.6), I(6.88), I(1.2), ["5.4 的 2×2", "权重驻留 DRAM", "权重流自 UFS"], [
        ["Prefill 在端", "本地中模型（8B 级）", "UFS 流式大模型（30B 级）← 本节"],
        ["Prefill 在云", "云桥 + 端侧小模型 decode", "（无意义）"],
    ], col_w=[1.2, 2.2, 2.6], s=10, hl_rows=(0,), hl_color=k.BAND)
    k.text(s, I(6.0), I(6.0), I(6.88), I(0.9), [
        [{"t": "注意：", "b": True, "c": k.RED, "s": 11},
         {"t": f"算力越强，同样的 UFS 带宽越难被计算藏住——平衡点与有效算力成正比（ΔL* ∝ F_eff）。"
               f"UFS 5.0 + 140 TOPS 有效下平衡点 {K(BE5)}；有效算力翻倍，平衡点也翻倍。", "s": 11, "c": k.RED}]])
    k.notes(s, "6.4 的前提：prefill 的算术强度远高于 UFS 能供数的速率。本节基线 UFS 5.0 + 140 TOPS 有效。")


# ---------------------------------------------------------------- 43
def slide_6_4_1(prs):
    s = k.add_slide(prs, "6.4.1", "配比公式：UFS 带宽 ÷ 有效算力", half_life=("快变量",),
                    source="v3.4 §6.4.1；calc.py ratio_bw()")
    k.formula_box(s, I(0.45), I(1.05), I(6.1), I(2.6), "推导（INT4 dense，每字节 2 个参数）", [
        k.fx("① 符号：N 参数量；W = N/2 字节；L_c chunk 长度；F_{eff} 有效算力；B_{ufs} 闪存带宽"),
        k.fx("② 计算 t_{comp} = 2N·L_c ÷ F_{eff}；流式 t_{io} = (N/2) ÷ B_{ufs}"),
        k.fx("③ 要求 t_{comp} ≥ t_{io}  ⇒  B_{ufs} ÷ F_{eff} ≥ 1 ÷ (4·L_c)", b=True, c=k.TEALDK),
        k.fx(f"④ 代入 F_{{eff}} = 200 TOPS × 70% = {F4 / 1e12:.0f} TOPS（W4A8）"),
        k.fx(f"   L_c = 4K ⇒ B_{{ufs}} ≥ 140×10¹² ÷ 16384 ≈ {c.ratio_bw(F4, 4096) / 1e9:.2f} GB/s"),
        k.fx("⑤ 用有效算力（MFU 70%）而非峰值，要求松 30%"),
    ])
    rows = []
    for L in (4096, 8192, 16384):
        need = c.ratio_bw(F4, L)
        rows.append([f"{L // 1024}K", f"{c.ratio_bw(1e12, L) / 1e6:.0f} MB/s", f"{need / 1e9:.2f} GB/s",
                     f"✓ 余量约 {1 - need / c.B_UFS['UFS5']:.0%}",
                     "✓" if need <= c.B_UFS['UFS4'] else "✗"])
    k.table(s, I(6.8), I(1.05), I(6.08), I(1.6),
            ["chunk", "每 TOPS 有效", "140 TOPS 需求", "UFS 5.0（10.8）", "UFS 4.0（4.0）"], rows,
            col_w=[0.8, 1.2, 1.3, 1.6, 1.2], s=10.5)
    k.chart(s, I(6.8), I(2.8), I(6.08), I(4.1), "bar", ["4K", "8K", "16K"],
            {"所需带宽": [round(c.ratio_bw(F4, L) / 1e9, 2) for L in (4096, 8192, 16384)],
             "UFS 5.0 上限": [10.8] * 3, "UFS 4.0 上限": [4.0] * 3},
            colors=[k.TEAL, k.BLUE, k.SLATE], y_title="GB/s")
    L_eq = F4 / (4 * c.B_UFS['UFS5'])
    k.box(s, I(0.45), I(3.85), I(6.1), I(1.45), [
        _p("取等号即 6.4.2 的平衡点", 11, k.TEALDK, True),
        k.fx(f"L_c = F_{{eff}} ÷ (4·B_{{ufs}}) = 140×10¹² ÷ (4 × 10.8×10⁹) ≈ {K(L_eq)}", s=11),
        _p("单轮内 L_c 最大取到 ΔL，所以 6.4.1 与 6.4.2 是同一个判据。", 10.5, k.MUTE)],
        fill=k.WHITE, line=k.TEAL, align=PP_ALIGN.LEFT)
    k.box(s, I(0.45), I(5.5), I(6.1), I(1.1), [
        [{"t": "结论：", "b": True, "c": k.RED, "s": 11},
         {"t": "有效算力为 140 TOPS 时，UFS 4.0 只剩 16K chunk 可行；UFS 5.0 从加分项变为硬性要求。",
          "s": 11, "c": k.RED}]], fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "B/F ≥ 1/(4Lc) 来自 t_comp ≥ t_io。取等号得 Lc = F/(4B)，与 6.4.2 的 ΔL* 相同。")


# ---------------------------------------------------------------- 44
def _range_diagram(s):
    lab_x, ax0, axw = 6.7, 8.15, 4.6
    lo, hi = 2.0, log10(20000)

    def xp(v):
        return ax0 + axw * (log10(v) - lo) / (hi - lo)

    k.text(s, I(lab_x), I(1.05), I(6.2), I(0.35), [_p("工具返回 ΔL 分布 vs 平衡点（对数轴）", 11, b=True)])
    bars = [("命令输出 / API", 200, 2000, k.RED), ("代码搜索 / grep", 500, 5000, k.AMBER),
            ("读文件 / 网页", 2000, 20000, k.TEAL)]
    for i, (name, a, b, col) in enumerate(bars):
        y = 1.75 + i * 0.6
        k.text(s, I(lab_x), I(y), I(1.4), I(0.36), [_p(name, 10)], anchor=MSO_ANCHOR.MIDDLE)
        k.rect(s, I(xp(a)), I(y), I(xp(b) - xp(a)), I(0.36), fill=col)
        k.text(s, I(xp(a)), I(y), I(xp(b) - xp(a)), I(0.36),
               [{"t": f"{a:,}–{b:,}".replace(",000", "K").replace(",", ""), "s": 9, "c": k.WHITE, "b": True}],
               align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    ay = 3.6
    k.rect(s, I(ax0), I(ay), I(axw), I(0.02), fill=k.MUTE)
    for v, lab in ((100, "100"), (1000, "1K"), (10000, "10K"), (20000, "20K")):
        k.rect(s, I(xp(v)), I(ay - 0.05), I(0.015), I(0.1), fill=k.MUTE)
        k.text(s, I(xp(v) - 0.3), I(ay + 0.06), I(0.6), I(0.25), [_p(lab, 9, k.MUTE)], align=PP_ALIGN.CENTER)
    k.vline(s, I(xp(BE5)), I(1.5), I(ay), color=k.TEALDK, w=2)
    k.text(s, I(xp(BE5) - 1.4), I(1.38), I(1.35), I(0.3),
           [_p(f"ΔL* = {K(BE5)}（UFS 5.0）", 9, k.TEALDK, True)], align=PP_ALIGN.RIGHT)
    k.vline(s, I(xp(BE4)), I(1.5), I(ay), color=k.MUTE, w=1.25, dash=True)
    k.text(s, I(xp(BE4) + 0.05), I(1.38), I(1.4), I(0.3), [_p(f"UFS 4.0：{K(BE4)}", 9, k.MUTE)])


def slide_6_4_2(prs):
    s = k.add_slide(prs, "6.4.2", "成本模型必须按轮次算", half_life=("快变量",),
                    source="v3.4 §6.4.2；calc.py break_even()")
    k.formula_box(s, I(0.45), I(1.05), I(6.0), I(2.45), "每轮都要重新流权重（片上放不下 15 GB）", [
        k.fx(f"t_{{tok}} = 2N ÷ F_{{eff}} = 2 × 30×10⁹ ÷ 140×10¹² ≈ {TT * 1e3:.2f} ms"),
        k.fx(f"流一遍权重 = W ÷ B_{{ufs}} = 15 GB ÷ 10.8 GB/s ≈ {T_STREAM5:.2f} s（UFS 4.0：{T_STREAM4:.2f} s）"),
        k.fx(f"平衡点 ΔL* = W ÷ (B_{{ufs}}·t_{{tok}}) ≈ {K(BE5)}（UFS 4.0：{K(BE4)}）", b=True, c=k.TEALDK),
        k.fx("关键量是单轮新增 ΔL，不是累计上下文 L", f=k.YAHEI),
        k.fx("ΔL < ΔL* 时，本轮大部分时间在空流权重", f=k.YAHEI, c=k.MUTE),
    ])
    k.table(s, I(0.45), I(3.7), I(6.0), I(1.45), ["工具返回类型", "典型 ΔL", f"相对 {K(BE5)}"], [
        ["命令输出、API 响应", "200–2K", "不划算：多数时间在空流权重"],
        ["代码搜索、grep", "500–5K", "临界"],
        ["读文件、网页抓取", "2K–20K", "多数划算"],
    ], col_w=[2.0, 1.2, 2.8], s=10.5)
    _range_diagram(s)
    k.text(s, I(6.7), I(4.05), I(6.18), I(1.1), [
        _p("真实 agent 循环中小返回的轮次占多数，这条路径的实际效率低于按任务级估算的结果。", 10.5, k.MUTE)])
    fixes = [("修正一", f"锚点是「单轮新增 ΔL > ~{BE5 / 1e3:.1f}K」——调度器每轮看 ΔL，决定走 UFS 大模型还是本地模型（轮次级路由）。"),
             ("修正二", "单 agent 循环严格串行，无法攒批。攒批只在并行 subagent 可用；延迟容忍 ≠ 可并行。"),
             ("修正三", "解药是动态驻留（6.4.2.1），不是常驻；MoE 的专家缓存只对 decode 有效（6.4.2.2）。")]
    for i, (t, body) in enumerate(fixes):
        k.box(s, I(0.45 + i * 4.18), I(5.35), I(4.05), I(1.55),
              [_p(t, 11, k.TEALDK, True), _p(body, 10.5)], fill=k.SLATEF, line=k.SLATE,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.notes(s, "ΔL* 由 calc.break_even 计算；工具返回长度区间取 2.4.1 的典型值。")


# ---------------------------------------------------------------- 45
def slide_6_4_2_1(prs):
    s = k.add_slide(prs, "6.4.2.1", "动态驻留的平衡点与 LRU 陷阱", half_life=("快变量",),
                    source="v3.4 §6.4.2.1；calc.py；insight/N+1/on-device-model-swapping/（LLM-aware Buffer Cache, Mathematics 2025）")
    k.formula_box(s, I(0.45), I(1.05), I(4.5), I(1.5), "每轮开始前已有 C 字节在 LPDDR", [
        k.fx("ΔL* = (W − C) ÷ (B_{ufs}·t_{tok})", b=True, c=k.TEALDK),
        k.fx("命中率 = C/W"),
        k.fx("C 由任务期间的空闲 LPDDR 决定", f=k.YAHEI, c=k.MUTE),
    ])
    rows = []
    for C in (0, 1.5e9, 3e9, 5e9):
        rows.append([f"{C / 1e9:g} GB", f"{(c.W_BIG - C) / 1e9:g} GB",
                     f"{(c.W_BIG - C) / c.B_UFS['UFS5']:.2f} s",
                     K(c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_BIG, F4, C))])
    k.table(s, I(0.45), I(2.7), I(4.5), I(1.75), ["驻留 C", "每轮流量", "流式时间", "ΔL*"], rows,
            col_w=[1, 1.1, 1.1, 1], s=10.5)

    k.text(s, I(5.2), I(1.05), I(7.68), I(0.3), [_p("一轮的时间线与预取窗口（C = 3 GB 示例）", 11, b=True)])
    segs = [("① 流式 prefill", f"只流 W − C = 12 GB · {12e9 / c.B_UFS['UFS5']:.2f} s", 1.9, k.BAND),
            ("② 小模型 decode", f"300 token：INT4 ≈ {300 / c.decode_tok_s(c.W_MID):.1f} s，"
                              f"2-bit ≈ {300 / c.decode_tok_s_future():.1f} s", 2.2, k.SLATEF),
            ("③ 工具执行", "数百 ms – 数十秒", 1.7, k.SLATEF),
            ("④ 下一轮 prefill", "命中前 C 字节", 1.6, k.BAND)]
    x = 5.2
    for t1, t2, w, f in segs:
        k.box(s, I(x), I(1.85), I(w), I(0.72), [_p(t1, 10.5, b=True), _p(t2, 9.5, k.MUTE)], fill=f,
              line=k.SLATE)
        x += w + 0.08
    k.box(s, I(5.2 + 1.98), I(1.36), I(2.2 + 1.7 + 0.08), I(0.44),
          [_p("预取窗口：按层序预取前 C 字节（≈0.3 GB/s，<1% LPDDR6 带宽）", 9.5, k.WHITE, True)],
          fill=k.TEAL, line=None)
    k.text(s, I(5.2), I(2.62), I(7.68), I(0.35), [
        _p("任务结束 → 回收：预取的是只读干净页，直接丢弃，零写回。UFS 5.0 在 10 s 窗口可搬 >100 GB，约束是空闲 LPDDR。",
           9.5, k.MUTE)])

    def strip(y, label, cached, color, note):
        k.text(s, I(5.2), I(y), I(1.35), I(0.4), [_p(label, 10, b=True)], anchor=MSO_ANCHOR.MIDDLE)
        for j in range(12):
            on = j in cached
            k.box(s, I(6.6 + j * 0.44), I(y), I(0.4), I(0.4),
                  [_p(f"{j * 5 + 1}", 8, k.WHITE if on else k.MUTE)],
                  fill=color if on else k.WHITE, line=k.SLATE)
        k.text(s, I(6.6), I(y + 0.42), I(6.2), I(0.3), [_p(note, 9.5, color)])
    strip(3.15, "LRU", range(6, 12), k.SLATE, "留下的是刚流完的后段层；下一轮从第 1 层开始 → 命中率 0")
    strip(3.95, "动态驻留", range(0, 6), k.TEAL, "按层序预取前段层，下一轮先用到 → 命中率 = C/W")
    k.table(s, I(0.45), I(4.75), I(7.4), I(1.55), ["策略", "是否有效", "说明"], [
        ["LRU", "无效（命中率 0）", "工作集 > 缓存 + 循环顺序访问 = 顺序扫描病理"],
        ["动态驻留（按层序预取前 C 字节，任务结束回收）", "有效", "命中率 = C/W，上表由此得出"],
        ["MoE 专家 LRU", "仅 decode 可能有效", "访问与内容相关；prefill 见 6.4.2.2"],
    ], col_w=[3.0, 1.4, 3.0], s=10)
    k.box(s, I(8.05), I(4.75), I(4.83), I(1.55), [
        _p("本地佐证", 10.5, k.TEALDK, True),
        _p("端侧 LLM 权重读取呈 LOOP 模式：通用 LRU 命中率 0.02，钉住循环块 0.34–0.8（LLM-aware Buffer Cache, Mathematics 2025）。",
           10)], fill=k.BAND, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.text(s, I(0.45), I(6.4), I(12.43), I(0.5), [
        _p(f"状态：C 需实测（附录 B 实测 A）。实测前同时给出 {K(BE5)}（无驻留上界）与 (1 − C/W) × {K(BE5)}。", 10, k.MUTE)])
    k.notes(s, f"永久固定一半层（7.5 GB）会让这部分 LPDDR 全天被占，不现实；动态驻留是任务内预取、任务后回收。"
               f"预取窗口按 8B INT4 口径约 {300 / c.decode_tok_s(c.W_MID):.1f} s，按 2029 基线 8B @2-bit 约 {300 / c.decode_tok_s_future():.1f} s，窗口更短但结论不变。")


# ---------------------------------------------------------------- 46
def slide_6_4_2_2(prs):
    s = k.add_slide(prs, "6.4.2.2", "MoE 在流式 prefill 中是负收益", half_life=("快变量",),
                    source="v3.4 §6.4.2.2；calc.py expert_untouched()；insight/N+1/on-device-model-swapping/（PowerInfer-2）")
    be_moe = c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_MOE_ACTIVE, F4)
    tt_moe = c.t_tok(c.N_MOE_ACTIVE, F4)
    k.formula_box(s, I(0.45), I(1.05), I(6.1), I(3.0), "为什么 prefill 下「只流激活专家」不成立", [
        k.fx("某专家一轮都未被选中：P = (1 − k/E)^{ΔL}"),
        k.fx(f"E = 128，k = 8：ΔL = 100 → {c.expert_untouched(100):.2%}；ΔL = 2.5K → ≈10⁻⁷⁰"),
        k.fx("⇒ 每轮流量 ≈ 全部权重 W；计算只按激活参数 N_{active}", f=k.YAHEI),
        k.fx("ΔL*_{MoE} = ΔL*_{dense} × N_{total} ÷ N_{active}", b=True, c=k.TEALDK),
        k.fx(f"30B-A3B：t_{{tok}} = 2 × 3×10⁹ ÷ 140 TOPS ≈ {tt_moe * 1e3:.3f} ms"),
        k.fx(f"ΔL* ≈ {T_STREAM5:.2f} s ÷ {tt_moe * 1e3:.3f} ms ≈ {K(be_moe, 1)}（dense 的 10 倍）", b=True, c=k.RED),
    ])
    k.table(s, I(0.45), I(4.25), I(6.1), I(1.75), ["", "30B dense", "30B-A3B（MoE）"], [
        ["每 token 计算 2N", "60 GFLOP", "6 GFLOP"],
        ["每轮流量（ΔL ≥ 100）", "15 GB", "≈15 GB（几乎全部专家）"],
        ["t_tok @140 TOPS", f"{TT * 1e3:.2f} ms", f"{tt_moe * 1e3:.3f} ms"],
        ["平衡点 ΔL*（UFS 5.0）", K(BE5), K(be_moe, 1)],
    ], col_w=[2.2, 1.6, 2.3], s=10.5, hl_rows=(3,))
    pts = [(d, c.expert_untouched(d)) for d in (1, 5, 10, 20, 50, 100, 150, 200)]
    k.xy_chart(s, I(6.8), I(1.05), I(6.08), I(3.4), {"E = 128，k = 8": pts},
               x_title="单轮新增 token ΔL", y_title="某专家未被选中的概率", log_y=True, legend=False)
    k.box(s, I(6.8), I(4.6), I(6.08), I(1.4), [
        _p("MoE 的收益在 flash 驱动的 decode", 11, k.TEALDK, True),
        _p("每 token 只触及少数专家。PowerInfer-2（OnePlus 12，47B 稀疏）：7 GB 内存 2.13 tok/s，19 GB 内存 11.68 tok/s。流式 prefill 应选 dense 模型。",
           10.5)], fill=k.BAND, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.text(s, I(0.45), I(6.2), I(12.43), I(0.6), [
        [{"t": "适用边界：", "b": True, "c": k.RED, "s": 11},
         {"t": "「MoE 只流激活专家」（6.4.3 解法 ③）与专家缓存只适用于 decode 或极小 ΔL；流式 prefill 下 MoE 反而更难藏住流量。",
          "s": 11, "c": k.RED}]])
    k.notes(s, "(1-1/16)^100 ≈ 0.16%；30B-A3B 的每 token 计算是 dense 的 1/10，流量不变，平衡点 ×10。")


# ---------------------------------------------------------------- 47
def slide_6_4_3_4(prs):
    s = k.add_slide(prs, "6.4.3 / 6.4.4", "双缓冲与能耗账", half_life=("快变量",),
                    source="v3.4 §6.4.3–6.4.4；calc.py e_comp_tok() / e_move_tok()")
    k.box(s, I(0.45), I(1.05), I(4.1), I(4.7), [
        _p("6.4.3 先撞墙的不是带宽，是双缓冲", 11.5, k.TEALDK, True),
        _p("边算边预取需缓存两层权重：15 GB ÷ 60 层 ≈ 250 MB/层，双缓冲 500 MB，片上 SRAM 放不下。", 10.5),
        _p("解法（按现实性排序）：", 10.5, b=True),
        _p("① 三级流水：UFS → LPDDR（中转）→ SRAM/NPU，SRAM 只需一个 tile", 10.5),
        _p("② 选深而窄的模型：单层字节数成为选型硬指标", 10.5),
        _p("③ MoE 只流激活专家——仅适用于 decode 或极小 ΔL（6.4.2.2）", 10.5, k.RED)],
        fill=k.SLATEF, line=k.SLATE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.formula_box(s, I(4.75), I(1.05), I(4.1), I(2.55), "6.4.4 按 ΔL 列式", [
        k.fx(f"e_{{op}} = 4 W ÷ 140 TOPS ≈ {c.e_op() * 1e12:.4f} pJ/op"),
        k.fx(f"E_{{comp}} = 2N·e_{{op}} = 60 GFLOP × {c.e_op() * 1e12:.4f} pJ ≈ {E_COMP * 1e3:.2f} mJ"),
        k.fx("E_{move} = W·e_{ufs} ÷ ΔL = 15 GB × 0.5 nJ/B ÷ ΔL = 7.5 J ÷ ΔL"),
        k.fx(f"能耗平衡点 ΔL_E = W·e_{{ufs}} ÷ E_{{comp}} ≈ {K(DLE, 1)}", b=True, c=k.TEALDK),
    ], s=10.5)
    rows = []
    for dl, lab in ((BE5, f"{K(BE5)}（时延平衡点）"), (DLE, f"{K(DLE, 1)}（能耗平衡点）"), (10000, "10K")):
        mv = c.e_move_tok(c.W_BIG, dl)
        rows.append([lab, f"{mv * 1e3:.2f} mJ", f"{E_COMP * 1e3:.2f} mJ", f"{E_COMP / mv:.2f}"])
    k.table(s, I(4.75), I(3.75), I(4.1), I(2.0), ["ΔL", "搬运", "计算", "计算÷搬运"], rows,
            col_w=[1.9, 0.9, 0.9, 0.9], s=10)
    pts_m = [(d, round(c.e_move_tok(c.W_BIG, d) * 1e3, 3)) for d in (1000, 2000, 3240, 4375, 6000, 10000, 20000)]
    k.xy_chart(s, I(9.05), I(1.05), I(3.83), I(4.7),
               {"搬运 E_move": pts_m, "计算 E_comp": [(1000, round(E_COMP * 1e3, 3)), (20000, round(E_COMP * 1e3, 3))]},
               colors=[k.RED, k.TEAL], x_title="ΔL（对数）", y_title="mJ / token", log_x=True,
               x_range=(1000, 20000))
    comp8 = c.e_comp_tok(c.N_MID); mv8 = c.e_move_tok(c.W_MID, 4096, c.E_LPDDR)
    k.box(s, I(0.45), I(5.95), I(12.43), I(0.95), [
        [{"t": "结论：", "b": True, "c": k.RED, "s": 11},
         {"t": "按 4 W @140 TOPS 的每 op 能耗，UFS 路径的搬运与计算处于同一量级；「计算远大于搬运」只在权重位于 DRAM 的 prefill 成立。", "s": 11},
         {"t": f"对照权重在 DRAM 的本地 prefill（8B，ΔL = 4K）：计算 {comp8 * 1e3:.3f} mJ vs 搬运 {mv8 * 1e3:.3f} mJ ≈ {comp8 / mv8:.1f} 倍——第七章结论一据此分两种 prefill 记账。",
          "s": 11}]], fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "e_op 由满算力持续 4 W 反推；UFS 0.5 nJ/B、LPDDR 0.05 nJ/B 为系统级估算。")


# ---------------------------------------------------------------- 48
def slide_6_4_5_6(prs):
    s = k.add_slide(prs, "6.4.5 / 6.4.6", "真正的瓶颈是散热 · 衍生推论", half_life=("快变量",),
                    source="v3.4 §6.4.5–6.4.6；calc.py p_ufs_hide() / t_round_thermal()")
    p4k = c.p_ufs_hide(c.W_BIG, 4096, c.N_BIG, F4)
    k.table(s, I(0.45), I(1.05), I(5.9), I(1.75), ["项", "持续功耗（估）", "推导"], [
        ["NPU @70% MFU", "~4 W", "满算力持续 4 W"],
        ["UFS（ΔL = 4K）", f"~{p4k:.2f} W", f"{c.ratio_bw(F4, 4096) / 1e9:.2f} GB/s × 0.5 nJ/B"],
        ["合计", f"~{4 + p4k:.1f} W", "约为持续包络的两倍"],
        ["手机持续包络", "3–5 W", "见 1.3"],
    ], col_w=[1.7, 1.5, 2.7], s=10.5, hl_rows=(2,))
    k.formula_box(s, I(0.45), I(2.95), I(5.9), I(1.65), "UFS 功率与热约束下的每轮时间", [
        k.fx("P_{ufs} = W·e_{ufs} ÷ (ΔL·t_{tok})：与 ΔL 成反比"),
        k.fx("t_{round} ≥ E_{round} ÷ P_{env}", b=True, c=k.TEALDK),
        k.fx("E_{round} = (W − C)·e_{ufs} + ΔL·E_{comp}；P_{env} = 4.9 W（取 3–5 W 包络上沿附近），C = 0"),
    ], s=10.5)
    rows = []
    for dl in (BE5, 10000):
        e_r = (c.W_BIG * c.E_UFS + dl * E_COMP)
        rows.append([K(dl) if dl != 10000 else "10K", f"{e_r:.1f} J",
                     f"{c.t_round_thermal(c.W_BIG, dl, c.N_BIG):.2f} s" if dl != 10000 else f"{c.t_round_thermal(c.W_BIG, dl, c.N_BIG):.1f} s",
                     f"{c.t_round_free(c.W_BIG, c.B_UFS['UFS5'], dl, c.N_BIG, F4):.2f} s"])
    k.table(s, I(0.45), I(4.75), I(5.9), I(1.1), ["ΔL", "E_round", "热约束 t_round", "无约束 t_round"], rows,
            col_w=[1.3, 1.3, 1.7, 1.6], s=10.5)
    pts = [(d, round(c.p_ufs_hide(c.W_BIG, d, c.N_BIG, F4), 2)) for d in (1000, 2000, 3240, 4096, 6000, 10000, 20000)]
    k.xy_chart(s, I(6.55), I(1.05), I(6.33), I(2.95),
               {"UFS 功率（藏住流式）": pts, "NPU 4 W": [(1000, 4), (20000, 4)],
                "持续包络上沿 5 W": [(1000, 5), (20000, 5)]},
               colors=[k.RED, k.TEAL, k.SLATE], x_title="ΔL（对数）", y_title="W", log_x=True, log_y=True,
               x_range=(1000, 20000))
    k.box(s, I(6.55), I(4.15), I(6.33), I(2.75), [
        _p("定位", 11, k.TEALDK, True),
        _p("不是日常主力路径，是可降频运行的低优先级路径，或插电场景路径；UFS 成为功耗大头。实测 C（降频后实际吞吐）决定它是「慢但可用」还是「只能插电」。",
           10.5),
        _p("6.4.6 衍生推论", 11, k.TEALDK, True),
        _p("· 量化杠杆：配比系数只由位宽决定，量化每降 1 bit 配比松 25%", 10.5),
        _p("· 寿命：NAND 读不磨损；会话级 KV 下放 UFS 按每日 10 任务估，五年仅数百次 P/E", 10.5),
        _p(f"· 边界条件：ΔL 须超过平衡点 {K(BE5)}，短轮次走常驻中模型", 10.5),
        _p("· PC 形态约束显著更松（30–100 W + NVMe 多盘数十 GB/s）", 10.5)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.text(s, I(0.45), I(6.0), I(5.9), I(0.9), [
        _p("热是软约束：越界后果是降频变慢而非故障；agent 任务分钟级，正落在热约束开始咬人的时间尺度。", 10, k.MUTE)])
    k.notes(s, "UFS 功率按 0.5 nJ/B 计；P_env 取 4.9 W，即 3–5 W 持续包络的上沿附近。")


def build(prs):
    for fn in (slide_6_4, slide_6_4_1, slide_6_4_2, slide_6_4_2_1, slide_6_4_2_2, slide_6_4_3_4, slide_6_4_5_6):
        fn(prs)

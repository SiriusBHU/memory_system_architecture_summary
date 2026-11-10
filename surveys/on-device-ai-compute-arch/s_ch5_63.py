# -*- coding: utf-8 -*-
"""第五章 三次范式冲击 + 6.1–6.3 架构形态（第 32–41 页）。依赖算力基线的数字由 calc 计算后格式化。"""
from pptx.util import Inches as I, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.chart import XL_LABEL_POSITION
import calc as c
import pptkit as k

F4 = c.f_eff('W4A8')                      # 200 TOPS × 70% = 140 TOPS 有效
KV_BPT = 890                              # 前沿压缩 KV，B/token（5.2.1、5.3）
CTX = 100e3                               # 5.2.2 的 100K 前缀
FLOP_100K = 2 * c.N_MID * CTX             # 本地 8B prefill 100K：1.6 PFLOP
T_LOCAL = FLOP_100K / F4                  # ≈ 11.4 s
_, _, T_SPARSE, T_DENSE = c.bridge_latency()   # 计入稀疏 top-k / dense 注意力：≈ 13.0 s / 49 s
BRIDGE_B = KV_BPT * CTX                   # 桥传输量 ≈ 89 MB
T_BRIDGE = BRIDGE_B * 8 / 50e6            # @ 50 Mbps ≈ 14 s
DA_K = 2 * 576 * 60                       # MLA latent 576、60 层：每 token 注意力 FLOP ≈ 69K × L
DW_FLOP = 2 * c.N_MID                     # D-w 基准：8B → 16 GFLOP/token
TPS = [c.decode_tok_s(w) for w in (4e9, 2e9, 1e9)]
BE5 = c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_BIG, F4)


def _p(t, s=11, c_=k.INK, b=False):
    return [{"t": t, "s": s, "c": c_, "b": b}]


def _r(t, s=11, c_=k.INK, b=False):
    return {"t": t, "s": s, "c": c_, "b": b}


def _rows_h(gf, hs):
    """逐行指定表格行高（英寸），避免均分导致表头过高。"""
    for row, h in zip(gf.table.rows, hs):
        row.height = I(h)


def _bar_labels(gf, fmt, s=10, point_colors=None):
    """原生柱状图：数据标签 + 单系列逐柱着色。"""
    plot = gf.chart.plots[0]
    plot.gap_width = 70
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = fmt, False
    dl.font.size = Pt(s)
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    for i, col in enumerate(point_colors or ()):
        pt = plot.series[0].points[i]
        pt.format.fill.solid(); pt.format.fill.fore_color.rgb = col


# ---------------------------------------------------------------- 32
def slide_5_1(prs):
    s = k.add_slide(prs, "5.1", "冲击一：Agent 账本",
                    source="v3.4 §5.1；两本账算例引 §2.4.1；calc.py t_tok() / decode_tok_s()")
    k.text(s, I(0.45), I(1.05), I(12.43), I(0.38), [[
        _r("第五章　", 11, k.TEALDK, True),
        _r("负载分析中最危险的是把当前范式当成永恒负载。三次冲击不是三个独立事件：冲击一、二是同一根轴的两端（5.4），"
           "冲击三是更根本的变动。", 10.5, k.MUTE)]], anchor=MSO_ANCHOR.MIDDLE)
    k.box(s, I(0.45), I(1.5), I(4.1), I(2.6), [
        _p("早期推论（chat 范式）", 12.5, k.MUTE, True),
        _p("端侧 LLM 性能 ≈ 有效带宽 ÷ 模型字节数", 11.5),
        _p("decode 主导体验 ⇒ 带宽为王", 11.5),
        _p("⇒ 近存计算（3D 堆叠 DRAM，TB/s 级带宽）是正确方向", 11.5),
        _p("agent 范式下被逐条修正 →", 11, k.RED, True)],
        fill=k.SLATEF, line=k.SLATE, align=PP_ALIGN.LEFT)
    k.arrow(s, I(4.6), I(2.8), I(5.05), I(2.8), color=k.TEAL, w=2)
    k.table(s, I(5.1), I(1.5), I(7.78), I(2.6), ["修正（agent 范式）", "内容"], [
        [[[_r("Token 账本翻转 ", 10.5, b=True), k.hl("快变量", 9)]],
         "90%+ token 在 prefill；成因是信息流读写不对称，非重复读取（2.4.1）"],
        ["统一池重心", "从带宽移向算力"],
        ["Prefix 复用", "从可选优化变为核心机制"],
        ["上下文工程", "成为刚需：每个进上下文的 token 都是成本"],
        ["延迟容忍", "Agent 可压至能效最优点「大阵列、低频点、长时跑」，同时提高 MFU（4.2）"],
    ], col_w=[2.35, 5.45], s=10.5, first_col_bold=True)
    k.box(s, I(0.45), I(4.3), I(12.43), I(0.7), [[
        _r("阶段结论：", 12.5, k.TEALDK, True),
        _r("算力与容量主导成本与能耗（token 账），带宽仍然主导交互体验（时间账）。两本账不能互相替代。", 12.5, b=True)]],
        fill=k.BAND, line=k.TEAL)

    t_pre = 4000 * c.t_tok(c.N_MID, F4)
    t_dec = 300 / c.decode_tok_s(c.W_MID)
    tok_share, wall_share = 300 / 4300, t_dec / (t_dec + t_pre)
    k.formula_box(s, I(0.45), I(5.2), I(6.3), I(1.75), "两本账算例（2.4.1：8B INT4，一轮 4K prefill + 300 token decode）", [
        k.fx(f"Token 账：4000 : 300 ≈ {4000 / 300:.0f} : 1", s=11),
        k.fx(f"t_{{prefill}} = 2 × 8×10⁹ × 4000 ÷ 140 TOPS ≈ {t_pre:.2f} s", s=11),
        k.fx(f"t_{{decode}} = 300 ÷ {c.decode_tok_s(c.W_MID):.0f} tok/s ≈ {t_dec:.1f} s（113.8 GB/s ÷ 4 GB）", s=11),
        k.fx(f"时间账 ≈ 1 : {t_dec / t_pre:.0f} ⇒ decode：token 占比 ≈ {tok_share:.0%}，墙钟占比 ≈ {wall_share:.0%}",
             s=11, b=True, c=k.TEALDK),
    ], s=11)
    k.box(s, I(6.95), I(5.2), I(5.93), I(1.75), [
        _p("连带修正：投机解码的价值判断", 11.5, k.TEALDK, True),
        _p("按时间账，decode 占多数墙钟时间，且 MFU 仅 10–20%。", 11),
        [_r("投机解码的价值不随 decode 的 token 占比缩水，而随其墙钟时间占比缩水", 11, b=True),
         _r(f"——后者远高于前者（左例 {tok_share:.0%} vs {wall_share:.0%}），价值下降幅度小于直觉判断（定位见 6.3.3）。", 11)]],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.notes(s, "两本账方向相反：token 账（成本、能耗）归算力与容量，时间账（体验）归带宽；投机解码按墙钟占比而非 token 占比评估。")


# ---------------------------------------------------------------- 33
def slide_5_2(prs):
    s = k.add_slide(prs, "5.2 / 5.2.1", "冲击二：隐状态桥接 · 桥账本", half_life=("未验证",),
                    source="v3.4 §5.2、§5.2.1；机制与成本数字为 Mostik 类工作团队自述（2026，未经第三方验证）")
    nodes = [(0.45, "云端大模型", "完成 prefill"), (3.0, "轻量投影矩阵", "训练得到"), (5.55, "端侧小模型", "只做 decode")]
    for x, t1, t2 in nodes:
        hot = t1 == "轻量投影矩阵"
        k.box(s, I(x), I(1.1), I(1.9), I(0.72), [_p(t1, 11, b=True), _p(t2, 9.5, k.MUTE)],
              fill=k.BAND if hot else k.SLATEF, line=k.TEAL if hot else k.SLATE)
    for x1, lab in ((2.35, "隐藏状态"), (4.9, "不经文本")):
        k.arrow(s, I(x1 + 0.03), I(1.5), I(x1 + 0.62), I(1.5), color=k.TEAL, w=1.75)
        k.text(s, I(x1 - 0.06), I(1.13), I(0.77), I(0.3), [_p(lab, 9, k.TEALDK, True)], align=PP_ALIGN.CENTER)
    k.box(s, I(0.45), I(1.95), I(7.0), I(1.12), [
        [_r("机制（Mostik 类工作，2026，", 11, b=True), _r("未经第三方验证", 11, k.RED, True),
         _r("）：训练轻量投影矩阵，把云端大模型完成 prefill 后的隐藏状态直接映射进端侧小模型的输入潜空间，不经过文本。", 11)],
        _p("大模型只做 prefill（云端最便宜的活：可并行、可批处理、可摊销），小模型只做 decode。", 11),
        [_r("团队自述：", 11, b=True), _r("成本降至 1/20，能力差距补回 50%。 ", 11), k.hl("未验证", 10)]],
        fill=k.WHITE, line=k.SLATE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(7.65), I(1.1), I(5.23), I(1.97), [
        _p("定性依据一句话", 11.5, k.TEALDK, True),
        [_r("文本是有损的中间表示", 11, b=True), _r("——模型内部的思考成果在被迫落成文字时被扔掉了绝大部分。", 11)],
        [_r("不采用「每 token 只剩 17 比特」：", 11, k.RED, True),
         _r("17 ≈ log₂(词表大小)，是分词器超参数而非信息论不变量；实际每 token 熵通常 1–5 比特。", 11)]],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.text(s, I(0.45), I(3.2), I(12.43), I(0.32), [[
        _r("5.2.1 桥账本：桥上传什么、多大", 11, k.TEALDK, True),
        _r("　——三种格式给出三个完全不同的结论", 10.5, k.MUTE)]])
    gf = k.table(s, I(0.45), I(3.55), I(12.43), I(2.1), ["格式", "传输量（100K 前缀）", "网络与能耗", "对架构的含义"], [
        ["A. 逐 token 投影态",
         f"传统 KV 估：数百 MB；按前沿压缩格式（~{KV_BPT} B/token）：~{BRIDGE_B / 1e6:.0f} MB",
         f"未压缩：十几秒 + 显著下载能耗，优势蒸发；压缩后传输约 {T_BRIDGE:.0f} s（时延对比见 5.2.2）", "要求高下行带宽 + 大接收缓冲"],
        ["B. 压缩态（gist 式，高压缩比）", "数 MB，可行", "优",
         "但做了大比例有损压缩，「不扔掉思考成果」的卖点被自己交易掉"],
        ["C. 只传投影输入，端侧重算 KV", "极小", "优",
         "端侧仍需完整 prefill 算力，省的是「大模型 vs 小模型」的差价，而非「算 vs 不算」"],
    ], col_w=[2.45, 3.45, 3.1, 3.43], s=10.5, first_col_bold=True)
    _rows_h(gf, [0.4, 0.6, 0.55, 0.55])
    k.box(s, I(0.45), I(5.85), I(12.43), I(1.1), [
        [_r("利好标注：", 11.5, k.TEALDK, True),
         _r(f"KV 压缩的快速进展（~{KV_BPT} B/token）正在模糊 A 与 B 的界限——"
            f"{KV_BPT} B/token × 100K = {BRIDGE_B / 1e6:.0f} MB，即 5.2.2 时延算例采用的格式 A 压缩口径。", 11.5)],
        [_r("但那是云端模型的 KV 格式，跨模型投影之后的尺寸仍是未知数。", 11.5, k.RED, True)]],
        fill=k.BAND, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "桥的全部数字来自团队自述，未经第三方验证；三种格式对应三种完全不同的传输量与架构含义。")


# ---------------------------------------------------------------- 34
def slide_5_2_2(prs):
    s = k.add_slide(prs, "5.2.2 / 5.2.3", "两个价值主张 · 三个未解决问题",
                    source="v3.4 §5.2.2–5.2.3；calc.py f_eff() / bridge_latency()")
    k.text(s, I(0.45), I(1.05), I(6.6), I(0.3), [[
        _r("5.2.2 两个价值主张必须分开评估", 11, k.TEALDK, True),
        _r("（否则「优势」在不同格式间指代不同的东西）", 9.5, k.MUTE)]])
    bold = [[_r("成立", 10, b=True)]]
    k.table(s, I(0.45), I(1.35), I(6.6), I(1.4), ["价值主张", "与什么比", "A（压缩）", "A（未压缩）", "C"], [
        [[[_r("效率优势", 10, b=True), _r("（省端侧算力与能耗；不含时延）", 9, k.MUTE)]], "同一模型在本地算一遍", "占优", "蒸发",
         "部分（省大 vs 小模型的差价）"],
        [[[_r("能力优势", 10, b=True), _r("（拿到大模型的质量）", 9.5, k.MUTE)]], "该能力在端侧根本不可得", bold, bold, bold],
    ], col_w=[1.55, 1.45, 0.95, 1.05, 1.6], s=10, hl_rows=(1,), hl_color=k.BAND)
    k.text(s, I(0.45), I(2.8), I(6.6), I(0.3), [_p("关键：能力优势与传输量无关，在三种格式下都成立。", 10.5, k.TEALDK, True)])

    # 时延对照条（原生形状，按 dense 口径满刻度）
    k.text(s, I(0.45), I(3.1), I(6.6), I(0.3), [_p("100K 前缀的时延对照（未计云端 prefill 排队）", 10, b=True)])
    x0, scale = 2.95, 3.35 / T_DENSE
    bars = [("本地 8B · 线性项（140 TOPS 有效）", T_LOCAL, k.TEAL, f"≈ {T_LOCAL:.1f} s"),
            ("本地 + 稀疏 top-k 注意力", T_SPARSE, k.TEALLT, f"≈ {T_SPARSE:.1f} s"),
            ("桥传输（89 MB @ 50 Mbps）", T_BRIDGE, k.AMBER, f"≈ {T_BRIDGE:.0f} s"),
            ("本地 + dense 注意力", T_DENSE, k.SLATE, f"≈ {T_DENSE:.0f} s")]
    for i, (lab, v, col, vt) in enumerate(bars):
        y = 3.4 + i * 0.29
        k.text(s, I(0.45), I(y), I(2.45), I(0.27), [_p(lab, 9)], align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        k.rect(s, I(x0), I(y + 0.035), I(v * scale), I(0.2), fill=col)
        k.text(s, I(x0 + v * scale + 0.05), I(y), I(0.8), I(0.27),
               [_p(vt, 9, k.TEALDK if col == k.TEALLT else (col if col != k.SLATE else k.MUTE), True)],
               anchor=MSO_ANCHOR.MIDDLE)

    k.formula_box(s, I(7.25), I(1.05), I(5.63), I(3.35), "时延算例（100K 前缀）", [
        k.fx(f"① 桥：{BRIDGE_B / 1e6:.0f} MB × 8 ÷ 50 Mbps = {BRIDGE_B * 8 / 1e6:.0f} Mb ÷ 50 Mb/s", s=11),
        k.fx(f"      ≈ {T_BRIDGE:.1f} s ≈ {T_BRIDGE:.0f} s", s=11, b=True),
        k.fx(f"② 本地 8B：2·N·ΔL = 2 × 8×10⁹ × 100×10³", s=11),
        k.fx(f"      = {FLOP_100K / 1e15:.1f}×10¹⁵ FLOP = {FLOP_100K / 1e15:.1f} PFLOP", s=11),
        k.fx(f"③ F_{{eff}} = 200 TOPS × 70% = {F4 / 1e12:.0f} TOPS（W4A8）", s=11),
        k.fx(f"④ t_{{local}} = {FLOP_100K / 1e15:.1f} PFLOP ÷ {F4 / 1e12:.0f} TOPS ≈ {T_LOCAL:.1f} s < {T_BRIDGE:.0f} s",
             s=11, b=True, c=k.TEALDK),
        k.fx(f"⑤ + top-k 2048：4·L·k·d·n = 0.11 PFLOP ⇒ ≈ {T_SPARSE:.1f} s < {T_BRIDGE:.0f} s", s=10.5),
        k.fx(f"⑥ + dense：2·L²·d·n = 2.6 PFLOP ⇒ ≈ {T_DENSE:.0f} s > {T_BRIDGE:.0f} s", s=10.5, c=k.RED),
        k.fx("   注意力按 W8A8 70 TOPS；d = 4096，n = 32 层", s=9.5, f=k.YAHEI, c=k.MUTE),
        k.fx(f"⑦ 端到端：t_{{桥}} = t_{{排队}} + t_{{云端 prefill}} + t_{{传输}} > {T_BRIDGE:.0f} s", s=11),
    ], s=11)
    k.box(s, I(0.45), I(4.6), I(12.43), I(0.78), [
        [_r("结论：", 11.5, k.RED, True),
         _r(f"本地 {T_LOCAL:.1f} s < 桥 {T_BRIDGE:.0f} s，时延上本地已占优，桥不再省时；它剩下的价值是能力优势，以及在压缩格式下省端侧算力与能耗。", 11.5, b=True)],
        _p(f"注意与上表不要混读：上表「效率优势」指省端侧算力与能耗，与时延是两个口径。前提是稀疏注意力下放到端侧（≈ {T_SPARSE:.1f} s）；"
           f"若为 dense 注意力（≈ {T_DENSE:.0f} s），本地不占优。未计云端排队与计算，计入后本地更占优。", 10.5, k.RED)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)

    k.text(s, I(0.45), I(5.48), I(12.43), I(0.3), [_p("5.2.3 三个未解决的问题", 11, k.TEALDK, True)])
    probs = [("一、隐私账不成立",
              "prefill 在云端 ⇒ 检索出的个人记忆条目须随上下文上云，「只上传问题」在记忆轴存在时不成立。"
              "出路：承认隐私退化，或个人上下文端侧单独 prefill 再与云端隐状态拼接——比桥本身难一个量级。"),
             ("二、版本耦合——最可能先杀死桥",
              "端云模型权重级绑定：云端按周迭代、端侧 OTA 按季度，云端一升级投影矩阵作废。"
              "是运维不可行而非学术问题，且无技术解——除非云端为端侧冻结长期版本（放弃迭代优势）。"),
             ("三、真实形态是混合制",
              "端侧中模型扛多数轮次，桥接云端只在困难步调用。桥不能是主路径，只能是加速路径（→ 5.4 三级路由）。")]
    for i, (t, body) in enumerate(probs):
        k.box(s, I(0.45 + i * 4.19), I(5.8), I(4.05), I(1.15), [_p(t, 10.5, k.RED if i == 1 else k.TEALDK, True), _p(body, 10)],
              fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.notes(s, f"本地 100K prefill 线性项 {T_LOCAL:.1f} s，低于桥传输 {T_BRIDGE:.0f} s；计入稀疏 top-k 注意力 {T_SPARSE:.1f} s 仍更低，"
               f"dense 注意力 {T_DENSE:.0f} s 则不成立。桥的价值：能力优势 + 压缩格式下省端侧算力与能耗。")


# ---------------------------------------------------------------- 35
def slide_5_3(prs):
    s = k.add_slide(prs, "5.3", "冲击三：模型侧正在主动拆墙", half_life=("快变量",),
                    source="v3.4 §5.3；P/D 例引 §4.3 P 类，位宽例引 §5.3.1")
    k.text(s, I(0.45), I(1.05), I(12.43), I(0.35), [_p("这次冲击比前两次更根本：它改变了「墙」这个概念本身。", 11.5, b=True)],
           anchor=MSO_ANCHOR.MIDDLE)
    k.table(s, I(0.45), I(1.45), I(8.1), I(2.0), ["墙", "模型侧的动作", "效果"], [
        ["容量（KV）", "MLA → 压缩注意力 → 跨层复用 + 稀疏索引",
         f"{KV_BPT} B/token，1M 上下文 <1 GB；复杂的多级 KV 分层失去必要"],
        ["算力配比（P/D）", "Causal Encoder-Decoder：prefill 走浅层",
         "prefill 激活参数可低于 decode；P/D 配比成为模型设计变量"],
        ["三堵墙同时", "位宽 FP16 → INT8 → INT4 → 2.x bit",
         "每降 1 bit 同时缓解容量、带宽、算力（低比特还简化 MAC 单元）"],
    ], col_w=[1.35, 3.1, 3.65], s=10.5, first_col_bold=True)
    k.formula_box(s, I(8.75), I(1.45), I(4.13), I(2.0), "量级核对", [
        k.fx(f"KV：{KV_BPT} B × 10⁶ token", s=11),
        k.fx(f"    ≈ {KV_BPT * 1e6 / 1e9:.2f} GB < 1 GB", s=11, b=True, c=k.TEALDK),
        k.fx("P/D：prefill 激活 8B、decode 激活 16B", s=11),
        k.fx("    （DeepSeek V4.1-Flash，4.3 P 类）", s=10, c=k.MUTE),
        k.fx(f"位宽：8B INT4 → 2bit，{c.N_MID * 0.5 / 1e9:.0f} GB → {c.N_MID * 0.25 / 1e9:.0f} GB", s=11),
    ], s=11)

    k.box(s, I(0.45), I(3.65), I(6.1), I(1.6), [
        _p("共同结构", 11, k.TEALDK, True),
        _p("每当硬件准备好去解决某堵墙，模型侧先把那堵墙拆了。", 12.5, b=True),
        _p("这是第七章结论二（三预算独立可缩放）最强的依据。原因不是「范式会变」（那听起来像随机性），而是右侧的迭代速度差。", 10.5)],
        fill=k.BAND, line=k.TEAL, align=PP_ALIGN.LEFT)
    # 迭代速度：硅 三年一代 vs 模型 半年一代（0.2 三回路）
    x0, wbar = 8.4, 4.45
    k.text(s, I(6.75), I(3.7), I(1.6), I(0.34), [_p("硅：三年级", 10, b=True)], anchor=MSO_ANCHOR.MIDDLE)
    k.box(s, I(x0), I(3.7), I(wbar), I(0.34), [_p("SoC 定义 → 量产", 9.5, k.WHITE, True)], fill=k.MUTE, line=None)
    k.text(s, I(6.75), I(4.12), I(1.6), I(0.34), [_p("模型/算法：半年级", 10, b=True)], anchor=MSO_ANCHOR.MIDDLE)
    seg = wbar / 6
    for j in range(6):
        k.rect(s, I(x0 + j * seg), I(4.12), I(seg - 0.05), I(0.34), fill=k.TEAL)
    k.box(s, I(6.75), I(4.6), I(6.13), I(0.65), [[
        _r("模型迭代比硅片快一个数量级（半年 vs 三年）。", 10.5, b=True),
        _r("任何针对特定瓶颈的硬件优化，都在和一个更快的对手赛跑。", 10.5)]],
        fill=k.WHITE, line=k.TEAL, align=PP_ALIGN.LEFT)

    k.box(s, I(0.45), I(5.45), I(12.43), I(1.5), [
        _p("反向标注（本文档最关键的技术假设）", 12, k.RED, True),
        [_r("上述趋势外推依赖「极低比特模型能在目标尺度上做到质量平价」，", 11.5, b=True), _r("而这尚未被证明。", 11.5, k.RED, True)],
        _p("BitNet 一系在小尺度展示了竞争力，但需训练时量化（不是事后量化），意味着重新预训练，成本极高。", 11.5),
        [_r("若该假设坍塌：", 11.5, b=True), _r("本节推论退回，带宽方案重新活过来。", 11.5, k.RED, True)]],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.notes(s, "三堵墙都在被模型侧拆：KV 压到 890 B/token、P/D 配比变成模型设计变量、位宽下降同时缓解三墙；前提是极低比特质量平价，尚未证明。")


# ---------------------------------------------------------------- 36
def slide_5_3_1(prs):
    s = k.add_slide(prs, "5.3.1 / 5.3.2", "存在性 ≠ 值得押注 · 那押什么",
                    source="v3.4 §5.3.1–5.3.2；calc.py decode_tok_s()（LPDDR6 113.8 GB/s）")
    k.box(s, I(0.45), I(1.05), I(6.1), I(1.05), [
        [_r("矛盾：", 10.5, k.RED, True),
         _r("「押注模型侧拆不掉的部分」+「D-w 拆不掉」⇒ 押注带宽方案；而 5.3 刚说模型侧在拆墙、带宽方案可能死。", 10.5)],
        [_r("缺的一环：「拆不掉」≠「值得押注」。", 10.5, k.TEALDK, True),
         _r("D-w 作为数学事实永远存在", 10.5), k.hl("不变量", 9),
         _r("，但量化 + 小模型化能把量级压到通用方案够用", 10.5), k.hl("快变量", 9),
         _r("——墙还在，但不痛了。", 10.5)]],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT)
    judge = [("痛", k.RED), ("可接受", k.AMBER), ("不痛", k.TEAL)]
    rows = []
    for (cfg, gb), tps, (jd, col) in zip((("8B @ INT4", 4), ("8B @ 2bit", 2), ("4B @ 2bit", 1)), TPS, judge):
        rows.append([cfg, f"{gb} GB", f"{tps:.0f} tok/s", [[_r(jd, 10.5, col, True)]]])
    k.table(s, I(0.45), I(2.25), I(6.1), I(1.3), ["配置", "每 token 权重流量", "LPDDR6（113.8 GB/s）下", "判断"], rows,
            col_w=[1.15, 1.6, 2.4, 0.95], s=10.5, first_col_bold=True)
    k.formula_box(s, I(0.45), I(3.7), I(6.1), I(1.25), "tok/s 推导（满带宽，未计 KV 读取与带宽利用率）", [
        k.fx("tok/s = B_{LPDDR} ÷ (N_{active} × 位宽/8)", s=10.5, b=True, c=k.TEALDK),
        k.fx(f"8×10⁹ × 4/8 = 4 GB → 113.8 ÷ 4 ≈ {TPS[0]:.0f}；8×10⁹ × 2/8 = 2 GB → ≈ {TPS[1]:.0f}", s=10),
        k.fx(f"4×10⁹ × 2/8 = 1 GB → 113.8 ÷ 1 ≈ {TPS[2]:.0f} tok/s", s=10),
    ], s=10.5)
    gf = k.chart(s, I(6.75), I(1.05), I(6.13), I(2.2), "bar", ["8B @ INT4（4 GB）", "8B @ 2bit（2 GB）", "4B @ 2bit（1 GB）"],
                 {"tok/s": [round(t, 1) for t in TPS]}, y_title="tok/s（LPDDR6）", legend=False, s=10)
    _bar_labels(gf, "0", 10.5, [col for _, col in judge])
    gf.chart.value_axis.maximum_scale = 140
    gf.chart.value_axis.has_major_gridlines = False
    k.box(s, I(6.75), I(3.35), I(6.13), I(1.6), [
        _p("押注对象不是「D-w 这堵墙」，而是一个不等式：", 10.5),
        _p("D-w 的痛度 > 通用方案（LPDDR 代际演进）的能力阈值", 12, k.TEALDK, True),
        _p("成立与否取决于「模型小型化 + 量化曲线」与「LPDDR 带宽增长曲线」的相对速度——需持续跟踪的经验问题，不是逻辑问题。", 10),
        [_r("跟踪指标：", 10, b=True),
         _r("目标能力档位模型「激活参数量 × 位宽」的逐年下降率 vs LPDDR 代际带宽增长率；前者快于后者 ⇒ 专用带宽方案窗口关闭。", 10)]],
        fill=k.BAND, line=k.TEAL, align=PP_ALIGN.LEFT)

    k.text(s, I(0.45), I(5.07), I(12.43), I(0.32), [[
        _r("5.3.2 那押什么　", 11, k.TEALDK, True),
        _r("挖掉 D-w 后，「持续功率包络」是约束而非可投资对象。两项押注都不依赖任何特定模型机制，因而对下一次冲击免疫。", 10.5, k.MUTE)]])
    bets = [("一、每 op 能效", "（工艺 + MAC 微架构 + 数据通路设计）",
             "模型侧除量化外帮不上忙，而量化红利已记在模型侧账上。无论是否 transformer、算术强度落在脊点哪侧，"
             "每 op 少耗的焦耳都直接兑现——唯一在所有分支下都有正收益的投资。"),
            ("二、并发能力", "（恒定功率包络内同时运行多类负载且互不伤害）",
             "结论四的核心命题：「常驻感知 + 突发思考 + 硬实时输出」共存不变。硬件体现：分域供电、相位级独立 DVFS（4.5）、"
             "可分区休眠的存储层级、细粒度可拆分的算力；压力测试见 6.3.5。")]
    for i, (t, sub, body) in enumerate(bets):
        k.box(s, I(0.45 + i * 6.33), I(5.42), I(6.1), I(1.0), [[_r(t, 10.5, k.TEALDK, True), _r(sub, 9.5, k.MUTE)], _p(body, 10)],
              fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(0.45), I(6.5), I(12.43), I(0.45), [[
        _r("一句话：", 10.5, k.WHITE, True),
        _r("硬件不该押注任何一堵具体的墙——墙会被模型侧拆掉；该押注的是「在功率包络内同时干几件事的能力」，那是模型迭代拿不走的。",
           10.5, k.WHITE)]], fill=k.TEALDK, line=None)
    k.notes(s, "D-w 永远存在但可以不痛：2bit + 小模型把 tok/s 从 28 抬到 114。押注对象是不等式与两项模型无关的能力。")


# ---------------------------------------------------------------- 37
def slide_5_4(prs):
    s = k.add_slide(prs, "5.4", "谱系合成：一根轴，一张 2×2",
                    source="v3.4 §5.4；ΔL* 引 §6.4.2（calc.py break_even()）")
    k.text(s, I(0.45), I(1.05), I(12.43), I(0.38), [[
        _r("前两次冲击方向相反，并列陈述则净效应为零；芯片须在三年前定 sizing，不能说「取决于范式」。⇒ ", 10.5, k.MUTE),
        _r("两次冲击不是两个竞争的未来，是同一个变量的两端。", 10.5, b=True)]], anchor=MSO_ANCHOR.MIDDLE)
    # 一根轴
    k.text(s, I(0.45), I(1.45), I(12.43), I(0.32), [_p("端侧承担的 prefill 份额", 12, b=True)], align=PP_ALIGN.CENTER)
    ya, xl, xr, xm = 2.0, 1.45, 11.88, 6.665
    k.arrow(s, I(xm), I(ya), I(xl), I(ya), color=k.TEALDK, w=3)
    k.arrow(s, I(xm), I(ya), I(xr), I(ya), color=k.BLUE, w=3)
    k.text(s, I(0.45), I(ya - 0.2), I(0.95), I(0.4), [_p("100%", 13, k.TEALDK, True)], align=PP_ALIGN.RIGHT,
           anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(11.95), I(ya - 0.2), I(0.93), I(0.4), [_p("0%", 13, k.BLUE, True)], anchor=MSO_ANCHOR.MIDDLE)
    k.box(s, I(0.45), I(2.3), I(3.9), I(0.8), [_p("本地自理 · 算力 + 容量主导", 11.5, k.TEALDK, True),
                                                _p("冲击一：Agent 账本（5.1）", 10, k.MUTE)], fill=k.BAND, line=k.TEAL)
    k.box(s, I(8.98), I(2.3), I(3.9), I(0.8), [_p("完全桥接 · 带宽主导", 11.5, k.BLUE, True),
                                                _p("冲击二：隐状态桥接（5.2）", 10, k.MUTE)], fill=k.SLATEF, line=k.BLUE)
    k.box(s, I(4.55), I(2.3), I(4.23), I(0.8), [
        _p("架构必须在这个参数的整个区间内可用——这就是结论二（三预算独立可缩放）的推导过程。", 10.5, b=True)],
        fill=k.WHITE, line=k.SLATE)

    # 2×2
    k.text(s, I(0.45), I(3.3), I(6.6), I(0.3), [_p("「本地中模型 / 云桥 / UFS 流式」不是三条互斥的路", 11, k.TEALDK, True)])
    k.text(s, I(0.45), I(3.6), I(6.6), I(0.3), [_p("原分类混了两个正交维度：本地 vs 云桥 = prefill 在哪算；本地中模型 vs UFS 流式 = 权重从哪来",
                                                  9.5, k.MUTE)])
    gf = k.table(s, I(0.45), I(3.95), I(6.6), I(1.35), ["", "权重驻留 DRAM", "权重流自 UFS"], [
        ["Prefill 在端", "本地中模型（8B 级）", [[_r("UFS 流式大模型（30B 级），见 6.4", 10.5, k.TEALDK, True)]]],
        ["Prefill 在云", "云桥 + 端侧小模型 decode", [[_r("（无意义）", 10.5, k.RED, True)]]],
    ], col_w=[1.3, 2.5, 2.8], s=10.5, first_col_bold=True)
    cell = gf.table.cell(1, 2); cell.fill.solid(); cell.fill.fore_color.rgb = k.BAND
    k.box(s, I(0.45), I(5.5), I(6.6), I(1.45), [
        _p("二、右下角空格暴露了云桥的隐藏浪费", 11.5, k.RED, True),
        _p(f"一旦 prefill 上云，端侧那份 {c.W_BIG / 1e9:.0f} GB 权重（30B INT4）就白存了——为断网可用必须存，为联网性能又用不上。", 11),
        _p("⇒ 云桥不能是主路径，只能是加速路径。", 11, b=True)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    # 三级路由
    k.rect(s, I(7.25), I(3.3), I(5.63), I(3.65), fill=k.SLATEF)
    k.text(s, I(7.4), I(3.38), I(5.4), I(0.32), [_p("一、三条路不互斥，可叠加成三级路由", 11, k.TEALDK, True)])
    routes = [("短轮次", "本地小模型", "权重驻留 DRAM，常驻", k.TEAL),
              ("长轮次", "UFS 流式大模型", f"单轮新增 ΔL > ΔL* ≈ {BE5 / 1e3:.2f}K（6.4.2）", k.TEALDK),
              ("困难步", "云桥", "能力优势；只作加速路径", k.BLUE)]
    for i, (cond, path, note, col) in enumerate(routes):
        y = 3.85 + i * 0.78
        k.box(s, I(7.45), I(y), I(1.25), I(0.6), [_p(cond, 11, k.WHITE, True)], fill=col, line=None)
        k.arrow(s, I(8.75), I(y + 0.3), I(9.2), I(y + 0.3), color=col, w=1.75)
        k.box(s, I(9.25), I(y), I(3.45), I(0.6), [_p(path, 11, b=True), _p(note, 9.5, k.MUTE)], fill=k.WHITE, line=col)
    k.text(s, I(7.45), I(6.2), I(5.3), I(0.65), [
        _p("这个路由是轮次级的（见 6.7）；长 / 短轮次以单轮新增 ΔL 相对平衡点 ΔL* 划分（6.4.2）。", 10.5, k.MUTE)])
    k.notes(s, "两次冲击是同一根轴（端侧 prefill 份额）的两端；2×2 把「prefill 在哪算」与「权重从哪来」拆开，三条路叠加为轮次级路由。")


# ---------------------------------------------------------------- 38
def slide_6_1(prs):
    s = k.add_slide(prs, "6.1", "两个物理域 + 一个控制平面", source="v3.4 §6.1")
    X, W = 0.45, 6.4
    k.box(s, I(X), I(1.05), I(W), I(0.67), [_p("控制平面：跨域调度", 12, k.WHITE, True),
                                            _p("决定下面两个域的可行性，非优化项", 10, k.TEALLT)], fill=k.DARK, line=None)
    # 域一
    k.rect(s, I(X), I(1.87), I(5.9), I(1.45), fill=k.WHITE, line=k.TEAL, line_w=1.25)
    k.text(s, I(X + 0.1), I(1.9), I(5.7), I(0.3), [[_r("域一：输入域", 11, k.TEALDK, True),
                                                   _r("（mW 级，高占空比，分模态）", 10, k.MUTE)]])
    k.box(s, I(X + 0.15), I(2.3), I(1.9), I(0.85), [_p("哨兵层", 11, b=True), _p("μW 级 · 事件过滤", 9.5, k.MUTE)],
          fill=k.SLATEF, line=k.SLATE)
    k.arrow(s, I(X + 2.1), I(2.72), I(X + 2.6), I(2.72), color=k.TEAL, w=1.75)
    k.box(s, I(X + 2.65), I(2.3), I(3.05), I(0.85), [_p("统一 encoder 引擎", 11, b=True),
                                                    _p("mW 级 · + E 类 rerank 兜底", 9.5, k.MUTE)],
          fill=k.BAND, line=k.TEAL)
    # 域二
    k.rect(s, I(X), I(3.47), I(5.9), I(1.75), fill=k.WHITE, line=k.TEAL, line_w=1.25)
    k.text(s, I(X + 0.1), I(3.5), I(5.7), I(0.3), [[_r("域二：思考+输出统一池", 11, k.TEALDK, True),
                                                   _r("（W 级，突发，可分区电源域）", 10, k.MUTE)]])
    parts = [("近存 DRAM", "权重 + 激活高速区"), ("大 MAC 阵列", "prefill / verify / 扩散 / D-a / rerank"),
             ("draft 核", "decode 相位利用率填充"), ("独立 DVFS", "MAC 阵列与内存接口分别调")]
    for j, (t1, t2) in enumerate(parts):
        k.box(s, I(X + 0.15 + j * 1.41), I(3.9), I(1.33), I(1.15), [_p(t1, 10.5, b=True), _p(t2, 9, k.MUTE)],
              fill=k.BAND if j == 1 else k.SLATEF, line=k.TEAL if j == 1 else k.SLATE)
    # 控制平面 → 两域
    xl = X + 6.13
    k.rect(s, I(xl - 0.01), I(1.72), I(0.025), I(2.63), fill=k.DARK)
    k.arrow(s, I(xl), I(2.6), I(X + 5.93), I(2.6), color=k.DARK, w=1.5)
    k.arrow(s, I(xl), I(4.35), I(X + 5.93), I(4.35), color=k.DARK, w=1.5)
    # 存储底座
    k.rect(s, I(X), I(5.37), I(W), I(1.1), fill=k.SLATEF, line=k.SLATE)
    k.text(s, I(X + 0.1), I(5.4), I(3), I(0.3), [_p("存储底座", 11, k.INK, True)])
    for j, t in enumerate(("权重", "记忆库", "会话 KV", "归档")):
        k.box(s, I(X + 0.15 + j * 1.55), I(5.75), I(1.45), I(0.55), [_p(t, 10.5, b=True)], fill=k.WHITE, line=k.SLATE)
    k.text(s, I(X), I(6.55), I(W), I(0.4), [_p("两域功率预算差三个数量级（mW vs W）→ 按功率量级划分电源域", 10, k.MUTE)])

    RX, RW = 7.1, 5.78
    k.box(s, I(RX), I(1.05), I(RW), I(1.45), [
        _p("一、调度是控制平面，与两域并列，不是补充说明", 11.5, k.TEALDK, True),
        _p("它承担的事情里有多件决定可行性而非优化度：", 11),
        [_r("· 轮次级路由", 11, b=True), _r(" → 决定 6.4 用不用", 11)],
        [_r("· 相位识别与电源域切换", 11, b=True), _r(" → 决定 4.5 那条规格", 11)],
        [_r("· 上下文工程与 prefix 生命周期", 11, b=True), _r(" → 决定 token 账的分子", 11)]],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(RX), I(2.62), I(RW), I(1.25), [
        _p("二、输入域与思考域分离的理由是功率量级", 11.5, k.TEALDK, True),
        _p("两者功率预算差三个数量级（mW vs W），电源域本就该按功率量级划分——一个 100% 占空比的 mW 负载与一个 5% 占空比的 "
           "W 负载共享供电，前者会被后者的漏电与上电开销吃掉。", 11)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    gf = k.table(s, I(RX), I(4.0), I(RW), I(2.95), ["思考域与输出域不分离", "理由"], [
        ["① 共用同一份权重", "分离意味着权重双份或跨域搬运，近存优势报废"],
        ["② 占空比互补", "用户不会同时深度思考与生成视频（真实冲突概率是经验断言，应补数据）"],
        ["③ MAC 阵列可共享，片上存储需分区且切换有代价",
         "P 与 G 算术强度相似，工作集形状完全不同：P = 权重 + KV（可流式）；G = 高分辨率激活张量（必须驻留、反复读写）。"
         "分区轮用 ⇒ 相位切换要清空重载，来回切换时开销显现"],
    ], col_w=[1.75, 4.05], s=10.5, first_col_bold=True)
    _rows_h(gf, [0.4, 0.6, 0.75, 1.2])
    k.notes(s, "两个域按功率量级分（mW vs W），调度是与两域并列的控制平面；思考与输出共用权重、占空比互补，所以不分离。")


# ---------------------------------------------------------------- 39
def slide_6_2(prs):
    s = k.add_slide(prs, "6.2", "输入域：两级结构", source="v3.4 §6.2（6.2.1–6.2.4）")
    k.text(s, I(0.45), I(1.05), I(12.43), I(0.33), [[
        _r("设计公理：", 11, k.TEALDK, True),
        _r("输入域的自由度不在算力配置，在唤醒拓扑与电源设计；敌人不是墙，是碎片化。", 11, b=True)]], anchor=MSO_ANCHOR.MIDDLE)
    k.box(s, I(0.45), I(1.42), I(5.95), I(1.02), [
        _p("第一级：μW 级哨兵层", 11, k.TEALDK, True),
        _p("唯一职责：决定何时唤醒第二级（事件过滤器，非数据处理器）", 10),
        [_r("设计目标：", 10), _r("误唤醒率 × 唤醒功耗", 10, b=True), _r(" 的乘积最小化", 10)],
        _p("扩展职责：判断「当前哪些模态可用」（见 6.2.1）", 10)],
        fill=k.SLATEF, line=k.SLATE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.arrow(s, I(6.45), I(1.95), I(6.88), I(1.95), color=k.TEAL, w=2)
    k.text(s, I(6.38), I(1.62), I(0.6), I(0.3), [_p("唤醒", 9, k.TEALDK, True)], align=PP_ALIGN.CENTER)
    k.box(s, I(6.93), I(1.42), I(5.95), I(1.02), [
        _p("第二级：统一 encoder 引擎（mW 级，指时间平均；活跃期约 22–95 mW）", 11, k.TEALDK, True),
        _p("一个可编程多模态 encoder 主干，所有模态的编码与结构化 head 共享", 10),
        _p("E 类 rerank 的兜底挂载点（首选解仍是模型侧的 late interaction，见 4.3）", 10)],
        fill=k.BAND, line=k.TEAL, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    LW, RX, RW = 5.2, 5.85, 7.03
    k.text(s, I(0.45), I(2.52), I(LW), I(0.3), [[_r("6.2.1 占空比分模态", 11, k.TEALDK, True),
                                                 _r("（手机多数时间在口袋里）", 9.5, k.MUTE)]])
    k.table(s, I(0.45), I(2.84), I(LW), I(1.4), ["模态", "实际占空比", "说明"], [
        ["IMU / 位置", "~100%", "真 7×24"],
        ["麦克风", "~100%", "但多数时间只是静音检测"],
        ["摄像头", "10–20%", "仅设备被拿出时"],
        ["屏幕内容", "10–20%", "同上"],
    ], col_w=[1.2, 1.15, 2.85], s=10, first_col_bold=True, hl_rows=(2, 3), hl_color=k.BAND)
    k.box(s, I(0.45), I(4.32), I(LW), I(0.75), [
        _p("两个后果", 10, k.TEALDK, True),
        _p("① 视觉 encoder 功耗预算可按 ~15% 占空比摊，比按 100% 宽松约 6 倍", 10),
        _p("② 唤醒逻辑更复杂，哨兵需判断模态可用性", 10)],
        fill=k.WHITE, line=k.TEAL, align=PP_ALIGN.LEFT)

    k.text(s, I(RX), I(2.52), I(RW), I(0.3), [_p("6.2.2 关键取舍", 11, k.TEALDK, True)])
    k.table(s, I(RX), I(2.84), I(RW), I(2.1), ["取舍点", "决策", "依据"], [
        ["ISP 去留", "拍照保留专用硬管线；感知走 encoder 引擎（同路摄像头两路数据）", "成像管线算法半衰期长、能效极致；感知要求多模态融合"],
        ["硬化 vs 可编程", "按 0.5 输出空间维度：唤醒词（有限离散）可硬化；多模态 encoder（结构化输出，三年一变）必须可编程", "边界流动律"],
        ["唤醒延迟", "睡眠 → 首个 embedding < 100 ms", "超此则「用户说完话才开始醒」，场景作废"],
        ["抗碎片化", "统一引擎留 30% 冗余算力 + 立法「新模态先进统一引擎，证明放不下才独立」",
         "碎片化根源是按传感器切分、多为组织决策——用制度手段解组织问题；冗余是保险不是浪费"],
    ], col_w=[1.3, 3.2, 2.53], s=9.5, first_col_bold=True)

    k.text(s, I(0.45), I(5.15), I(12.43), I(0.3), [[_r("6.2.3 100 ms 指标的隐含矛盾（待决）", 11, k.RED, True),
                                                  _r("　100 ms 唤醒预算 = 三段之和（示意，非比例）", 9.5, k.MUTE)]])
    segs = [("哨兵判决", 1.15, k.SLATE), ("电源域上电", 1.35, k.SLATE), ("权重加载（大头）", 2.7, k.RED)]
    x = 0.45
    for t, w, col in segs:
        k.box(s, I(x), I(5.5), I(w - 0.04), I(0.36), [_p(t, 9.5, k.WHITE, True)], fill=col, line=None)
        x += w
    k.text(s, I(0.45), I(5.92), I(LW), I(1.03), [
        _p("encoder 权重数百 MB 存在 UFS ⇒ 加载即数百 ms，指标直接破 ⇒ 隐含硬件要求：encoder 权重必须常驻。", 10),
        _p("但数百 MB SRAM 在手机上不现实（今日旗舰 SoC 总 SRAM 为数十 MB 量级），DRAM 常驻分区要付漏电功耗。", 10)])
    k.box(s, I(RX), I(5.5), I(RW), I(0.92), [
        _p("三个可能的解（本文档不选定，标为待决）", 10, k.RED, True),
        _p("① encoder 权重压到数十 MB（若是专用小模型，可能）", 10),
        _p("② 接受 DRAM 常驻分区的漏电代价（需算账）", 10),
        _p("③ 放宽 100 ms 指标（需重新论证场景是否作废）", 10)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.text(s, I(RX), I(6.48), I(RW), I(0.47), [[
        _r("6.2.4 多模态融合的红利：", 10, k.TEALDK, True),
        _r("结构化消化把一万像素压缩成「一个人在看手机」几个字——输入侧是记忆系统容量的第一道阀门；"
           "压缩发生在最靠近传感器处，下游全受益。", 10)]])
    k.notes(s, "输入域的设计变量是唤醒拓扑与电源；视觉按 ~15% 占空比摊；100 ms 唤醒隐含 encoder 权重常驻，三个解待决。")


# ---------------------------------------------------------------- 40
def slide_6_3(prs):
    s = k.add_slide(prs, "6.3 / 6.3.1", "思考+输出统一池 · Sizing 逻辑", source="v3.4 §6.3、§6.3.1")
    # 统一池组成
    k.rect(s, I(0.45), I(1.05), I(6.1), I(1.55), fill=k.WHITE, line=k.TEAL, line_w=1.25)
    k.text(s, I(0.55), I(1.07), I(5.9), I(0.3), [_p("统一池组成", 11, k.TEALDK, True)])
    parts = [("近存 DRAM 层", "权重 + 激活高速区"), ("大 MAC 阵列", "prefill / verify / 扩散 / D-a / rerank 共用"),
             ("小 draft 核", "decode 相位的利用率填充"), ("独立电源域", "MAC 阵列与内存接口分别 DVFS")]
    for j, (t1, t2) in enumerate(parts):
        xx, yy = 0.6 + (j % 2) * 2.95, 1.39 + (j // 2) * 0.6
        k.box(s, I(xx), I(yy), I(2.85), I(0.55), [[_r(t1 + "  ", 10, b=True)], _p(t2, 9, k.MUTE)],
              fill=k.BAND if j == 1 else k.SLATEF, line=k.TEAL if j == 1 else k.SLATE)
    k.table(s, I(0.45), I(2.75), I(6.1), I(2.15), ["预算", "依据"], [
        ["带宽", "目标吐字速度 × 模型字节数，按 2.4.2 场景权重分段：chat / 语音双工取高，前台 agent 取中，后台 agent 近似不计"],
        ["算力", "按 prefill 目标与目标上下文下的 D-a 联合确定（公式见下）"],
        ["容量", f"权重 + KV + 激活区。KV 按 {KV_BPT} B/token 计（1M 上下文 <1 GB），大头是权重与扩散激活区；另需为 6.6 多档位模型留份额"],
        ["电源域", "P 与 D 的最优功率点相反 → MAC 阵列与内存接口独立电源域与 DVFS，按相位切换预算流向（4.5）"],
    ], col_w=[0.75, 5.35], s=9.5, first_col_bold=True)
    k.formula_box(s, I(0.45), I(5.05), I(6.1), I(1.9), "算力 sizing 公式（「给 decode 堆算力是浪费」只对 D-w 成立）", [
        k.fx("F ≥ max(", s=11, b=True, c=k.TEALDK),
        k.fx("    ΔL × 2·N_{prefill} ÷ T_{prefill,目标} ,         ← prefill 项", s=11),
        k.fx("    (2·N_{decode} + 69K × L_{目标}) × R_{decode,目标} , ← decode 项（含 D-a）", s=11),
        k.fx("    扩散热预算项 )", s=11),
        k.fx("第二项的 69K × L_{目标}：短上下文时代可忽略，agent 的 100K 上下文让它不可忽略", s=10.5, f=k.YAHEI, c=k.MUTE),
    ], s=10.5)

    k.formula_box(s, I(6.75), I(1.05), I(6.13), I(1.0), "D-a 量级验算（MLA 类：latent 576，60 层）", [
        k.fx(f"FLOP_{{D-a}}/token ≈ 2 × 576 × 60 × L = {DA_K:,} × L ≈ 69K × L", s=10.5, b=True, c=k.TEALDK),
        k.fx(f"D-w 基准：2·N = 2 × 8×10⁹ = {DW_FLOP / 1e9:.0f} GFLOP/token（8B INT4）", s=10.5),
    ], s=10.5)
    rows, da = [], []
    for L, lab in ((1e4, "10K"), (1e5, "100K（agent 场景）"), (1e6, "1M")):
        g, r = DA_K * L / 1e9, DA_K * L / DW_FLOP * 100
        gs = f"{g:.1f} G" if g < 10 else f"{g:.0f} G"
        ps = f"{r:.0f}%" if r < 100 else f"{round(r, -1):.0f}%"
        rows.append([lab, gs, ps if r < 10 else [[_r(ps, 10.5, k.RED, True)]]])
        da.append(float(gs[:-2]))
    k.table(s, I(6.75), I(2.15), I(6.13), I(1.15), ["上下文 L", "D-a FLOP/token", f"占 D-w 的比例（{DW_FLOP / 1e9:.0f} GFLOP）"], rows,
            col_w=[1.9, 1.7, 2.5], s=10.5, first_col_bold=True, right_cols=(1, 2))
    gf = k.chart(s, I(6.75), I(3.35), I(6.13), I(1.95), "bar", ["L = 10K", "L = 100K", "L = 1M"],
                 {"D-w（8B INT4）": [DW_FLOP / 1e9] * 3, "D-a（MLA，60 层）": da},
                 colors=[k.SLATE, k.TEAL], y_title="GFLOP / token", s=9.5)
    _bar_labels(gf, "General", 9.5)
    k.box(s, I(6.75), I(5.4), I(6.13), I(1.55), [
        _p("在 agent 的 100K 量级上，D-a 已占 decode 算力的四成；到 1M 则反过来主导。", 10.5, b=True),
        _p("D-a 的 MFU 显著高于 D-w：decode 整体 10–20% 是被 D-w 的 GEMV 拖下来的；D-a 在长上下文下序列维并行度充分、"
           "形状接近 GEMM，MFU 可达 40–60%。", 10.5),
        _p("⇒ 长上下文下，decode 的算力投入是有效的，效用全部落在 D-a 上。", 11, k.TEALDK, True)],
        fill=k.BAND, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.notes(s, "D-a ≈ 69K × L FLOP/token；100K 时为 D-w 的 43%，1M 时为 430%，所以算力 sizing 的 decode 项必须含 D-a。")


# ---------------------------------------------------------------- 41
def slide_6_3_2(prs):
    s = k.add_slide(prs, "6.3.2 – 6.3.5", "KV 简化 · 投机解码 · 扩散安置 · 语音双工", source="v3.4 §6.3.2–6.3.5")
    LW = 6.0
    k.box(s, I(0.45), I(1.05), I(LW), I(1.05), [
        _p("6.3.2 KV 管理：可以简化", 11, k.TEALDK, True),
        _p(f"复杂的多级 KV 分层（热/温/冷 → 近存 DRAM / LPDDR / 归档）可以砍掉：1M 上下文 <1 GB"
           f"（{KV_BPT} B/token × 10⁶），全部放 LPDDR 即可，省下的复杂度值钱。", 10),
        _p("保留一条可选优化：当前注意力窗口可选择性提到近存层。", 10)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(0.45), I(2.15), I(LW), I(0.6), [[
        _r("风险标注：", 10, k.RED, True),
        _r(f"{KV_BPT} B/token 是前沿云端模型的数字，端侧小模型的 KV 压缩能否跟进是空白（4.3 KV-io）；若端侧 KV 显著更大，本节需回滚。", 10)]],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.text(s, I(0.45), I(2.85), I(LW), I(0.3), [_p("6.3.3 投机解码：定位", 11, k.TEALDK, True)])
    k.table(s, I(0.45), I(3.17), I(LW), I(2.15), ["维度", "判断"], [
        ["机制", "draft 核填的不是「闲置的 MAC」，而是「有活干但 MFU 仅 10–20% 的 MAC」；verify 把算术强度从 ~2 抬到 ~2k"
                 "（k 为一次 verify 的 token 数），等效带宽放大 k 倍"],
        ["价值", "按时间账 decode 占多数墙钟时间，价值缩水幅度小于 token 账暗示的水平（5.1）"],
        ["利好", "agent 场景输出是结构化的（工具调用、参数、代码），draft 接受率可能反而更高"],
        ["净判断", [[_r("短上下文长输出（聊天、写作）价值高；agent 场景下降但不为零。", 10),
                    _r("draft 核仍然值得，但不是第一优先级", 10, k.RED, True),
                    _r("——算力预算按 prefill 定，那部分面积的收益更直接", 10)]]],
    ], col_w=[0.8, 5.2], s=10, first_col_bold=True)
    k.box(s, I(0.45), I(5.5), I(LW), I(1.45), [
        _p("6.3.4 扩散负载的安置", 11, k.TEALDK, True),
        _p("蹭大 MAC 阵列（与思考错峰）。唯一新增约束是激活容量：", 10.5),
        [_r("切一块「激活高速区」，按最大生成分辨率定容", 10.5, b=True), _r("；思考相位可兼作 KV 溢出缓存。", 10.5)],
        _p("代价（6.1 已标注）：相位切换需清空重载，来回切换时开销显现。", 10.5, k.MUTE)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    RX, RW = 6.65, 6.23
    k.text(s, I(RX), I(1.05), I(RW), I(0.3), [_p("6.3.5 并发压力案例：语音双工", 11, k.TEALDK, True)])
    k.text(s, I(RX), I(1.37), I(RW), I(0.5), [
        _p("全文档唯一要求多个原语真正并发、且总延迟预算为硬约束的场景——结论四（常驻优先律）与 5.3.2（押注并发能力）的压力测试。",
           10, k.MUTE)])
    k.text(s, I(RX), I(1.9), I(RW), I(0.3), [[_r("并发要求：", 10.5, b=True),
                                              _r("轮转预算 200–300 ms 内，以下必须同时在跑", 10.5)]])
    k.table(s, I(RX), I(2.22), I(RW), I(1.45), ["原语", "角色", "域", "性质"], [
        ["C 类（ASR）", "持续听", "输入域", "流式、不可中断"],
        ["P + D 类（LLM）", "理解与生成", "统一池", "突发、算力 + 带宽"],
        ["V 类（TTS）", "持续说", "统一池", "自回归、带宽受限、硬实时、不可被抢占"],
    ], col_w=[1.45, 1.05, 0.85, 2.9], s=10, first_col_bold=True, hl_rows=(2,))
    k.box(s, I(RX), I(3.85), I(RW), I(1.25), [
        _p("硬件要求一：输入域与统一池必须能同时供电，并各自保持延迟保证", 11, k.TEALDK, True),
        _p("「哨兵唤醒 encoder，encoder 唤醒统一池」是串行模型；语音双工要求三者并行且互不伤害。"
           "这与 6.1 的分域设计兼容，但对上电时序与电源域隔离提出额外要求。", 11)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT)
    k.box(s, I(RX), I(5.22), I(RW), I(1.15), [
        _p("硬件要求二：V 类必须不可被抢占", 11, k.RED, True),
        _p("文本 decode 慢了只是吐字慢，语音 decode 慢了会断流。调度器的 QoS 分级中 V 类应享最高优先级，"
           "且其带宽配额需被预留而非竞争获得（2029 基线：语音原生约 25 GB/s，占 LPDDR6 22%；叠加 LLM 理解与 thinking decode 可超 50 GB/s，见附录 B 遗留问题 4）。", 10.5)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    k.box(s, I(RX), I(6.5), I(RW), I(0.45), [
        _p("「并发能力」押注的最小完整测例：任何声称支持小秘书形态的架构，都应该先用它跑通。", 10, k.WHITE, True)],
        fill=k.TEALDK, line=None)
    k.notes(s, "KV 全放 LPDDR（风险：端侧 KV 压缩未知）；draft 核值得但非第一优先；扩散蹭 MAC 阵列；语音双工是并发能力的最小测例。")


def build(prs):
    for fn in (slide_5_1, slide_5_2, slide_5_2_2, slide_5_3, slide_5_3_1, slide_5_4,
               slide_6_1, slide_6_2, slide_6_3, slide_6_3_2):
        fn(prs)

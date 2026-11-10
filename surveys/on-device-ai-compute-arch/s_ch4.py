# -*- coding: utf-8 -*-
"""第四章：计算原语（第 16–32 页）。原语页统一用 slide_primitive() 模板。

负载实例以 2029 负载为主（基线见 calc.FUT / calc.DAY），最后一列为今天的实测锚点。
"""
import math
from pptx.util import Inches as I
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import calc as c
import pptkit as k

F4 = c.f_eff('W4A8')
F8 = c.f_eff('W8A8')
DAYE = c.day_energy()
F_LO, F_HI = c.lora_energy_range()              # F 类夜间 LoRA 能耗区间
BAT = c.FUT['battery_j']


def fmt_flop(x):
    return f"{x / 1e15:g} PFLOP" if x >= 1e15 else f"{x / 1e12:g} TFLOP"


def fmt_t(x):
    return f"{x:.2f} s" if x < 1 else f"{x:.1f} s"


def _p(t, s=10.5, c_=k.INK, b=False):
    return [{"t": t, "s": s, "c": c_, "b": b}]


def _lines(txt, w_in, s):
    width = sum((s / 72 if ord(ch) > 0x2E80 else 0.62 * s / 72) for ch in str(txt))
    return max(1, math.ceil(width / max(w_in - 0.2, 0.1)))


def _table_h(header, rows, col_w_in, s):
    lh = s * 1.4 / 72
    h = max(_lines(t, w, s) for t, w in zip(header, col_w_in)) * lh + 0.1
    for r in rows:
        h += max(_lines(t, w, s) for t, w in zip(r, col_w_in)) * lh + 0.1
    return h + 0.22


ANCHOR_HDR = ["负载（2029）", "形态 / 规模", "触发与频次", "单次量级", "时延 / 能耗", "今天的锚点"]
ANCHOR_W = [1.5, 1.9, 1.7, 2.0, 2.5, 2.8]


def slide_primitive(prs, spec):
    """spec: key, name, cluster, half_life, tag, definition, instances=(header, rows, col_w),
    coords=[(坐标, 取值)×5], formula=(title, lines), change, placement, source, notes, hl_rows。"""
    s = k.add_slide(prs, f"4.3-{spec['key']}", spec["name"], half_life=spec.get("half_life", ()),
                    tag=spec.get("tag"), source=spec["source"])
    k.text(s, I(0.45), I(0.98), I(12.43), I(0.42), [
        [{"t": "定义：", "b": True, "s": 11}, {"t": spec["definition"], "s": 11},
         {"t": f"　｜　所属簇：{spec['cluster']}", "s": 11, "c": k.MUTE}]], anchor=MSO_ANCHOR.MIDDLE)
    header, rows, col_w = spec["instances"]
    col_in = [12.43 * w / sum(col_w) for w in col_w]
    for ts in (9, 8.5, 8):                      # 放不下就降字号，保证下半页至少 2.3 in
        th = _table_h(header, rows, col_in, ts)
        if 6.95 - (1.72 + th + 0.15) >= 2.3:
            break
    k.text(s, I(0.45), I(1.42), I(12.43), I(0.3), [
        [{"t": "负载实例", "s": 11, "c": k.TEALDK, "b": True},
         {"t": "　以 2029 负载为主；最后一列为今天的锚点（多为手机实测，估算 / 服务器另注），[编号] 见附录 C", "s": 9.5, "c": k.MUTE}]])
    k.table(s, I(0.45), I(1.72), I(12.43), I(th), header, rows, col_w=col_w, s=ts,
            hl_rows=spec.get("hl_rows", ()), hl_color=k.BAND)
    yb = 1.72 + th + 0.15
    hb = 6.95 - yb
    k.table(s, I(0.45), I(yb), I(5.75), I(hb), ["五坐标（2029）", "取值"], [list(r) for r in spec["coords"]],
            col_w=[1.0, 4.75], s=9, first_col_bold=True)
    ft, lines = spec["formula"]
    k.formula_box(s, I(6.33), I(yb), I(3.45), I(hb), ft, lines, s=9.5)
    k.box(s, I(9.9), I(yb), I(2.98), I(hb), [
        _p("可被什么改变", 10, k.TEALDK, True), _p(spec["change"], 9),
        _p("落在哪 / 硬件诉求", 10, k.TEALDK, True), _p(spec["placement"], 9)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    if spec.get("notes"):
        k.notes(s, spec["notes"])
    return s


def _sci(x, nd=1):
    """1.2288e16 → 1.2×10¹⁶。"""
    m, e = f"{x:.{nd}e}".split("e")
    sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return f"{m}×10{str(int(e)).translate(sup)}"


def _fx(t, **kw):
    kw.setdefault("s", 9.5)
    return k.fx(t, **kw)


def _pct(x):
    return f"{x / BAT:.1%}"


# ---------------------------------------------------------------- 原语规格（2029）
def spec_c():
    ai_v, e_v = c.enc_vision_frame(); ai_a, e_a = c.enc_audio_chunk()
    ai_e, e_e = c._enc(c.DAY['item_tokens'])
    fl_v = 2 * c.FUT['enc_params'] * c.FUT['vit_tokens']
    mv = c.FUT['enc_bytes'] * c.E_LPDDR
    rows = [
        ["哨兵：唤醒词 / VAD / IMU", "KB–MB 级，片上常驻", "常开", "唤醒词约 0.8 MMAC / 32 ms",
         f"约 0.5 mW；全天约 {c.FUT['sentinel_w'] * 86400:.0f} J", "NDP120 流式唤醒词 0.51 mW、占空比 2.2% [C-S4]；IMU 识别增量约 7 µW [C-S41]"],
        ["视觉感知 / 屏幕理解", "统一 encoder 300M，196 token/帧", f"设备在手约 {c.DAY['cam_hours']} h/天，1 fps",
         f"{fl_v / 1e9:.0f} GFLOP，重读 300 MB；{ai_v:.0f} ops/B",
         f"{e_v * 1e3:.1f} mJ/帧；活跃期约 {e_v * c.DAY['vis_fps'] * 1e3:.0f} mW；全天约 {e_v * c.DAY['cam_hours'] * 3600:.0f} J",
         "MobileNetV4-M 1.0 GMAC、1.1 ms（Pixel 8）[C-S28]；SigLIP2 图像塔 6.05 ms（S24）[C-S30]；NPU 负载 4.3–4.7 W [C-S29]"],
        ["流式 ASR / 音频理解", "同一 encoder，160 ms 块（约 8 token）", f"有语音时约 {c.DAY['audio_hours']} h/天",
         f"4.8 GFLOP，重读 300 MB；{ai_a:.0f} ops/B",
         f"{e_a * 1e3:.1f} mJ/块；活跃期约 {e_a * c.FUT['audio_hz'] * 1e3:.0f} mW；全天约 {e_a * c.FUT['audio_hz'] * 3600:.0f} J",
         "Zipformer 63M，每 0.71 s 块 8.7 ms（S24）[C-S20]；流式 ASR 能耗模型（估算）：访存 117 mW、计算 1 mW [C-S19]"],
        ["语料摄入 embedding", "同一 encoder，256 token/条", f"{c.DAY['items']} 条/天，可攒批放夜间",
         f"154 GFLOP；{ai_e:.0f} ops/B", f"{e_e * 1e3:.1f} mJ/条；全天约 {e_e * c.DAY['items']:.0f} J",
         "EmbeddingGemma 308M，256 token < 15 ms（EdgeTPU）[C-S43]"],
    ]
    return dict(
        key="C", name="流式编码（Encoder Streaming）", cluster="常开簇（C + 哨兵）", half_life=("慢变量",),
        definition="感知流、ASR、视觉感知、语料摄入的流式 encoder 前向；能效是唯一约束——2029 年主要是访存能效",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(2,),
        coords=[("算术强度", f"哨兵片上常驻 → 算力受限；300M encoder 放不进片上：视觉 {ai_v:.0f} ops/B、音频流 {ai_a:.0f} ops/B → 访存受限"),
                ("占空比", "IMU / 麦克风 ~100%；相机 / 屏幕 10–20%（6.2.1）"),
                ("持续功率", f"哨兵 sub-mW；encoder 为 W 级毫秒突发，活跃期均值 22–95 mW；全天约 {DAYE['C'] / 1e3:.1f} kJ（{_pct(DAYE['C'])}）"),
                ("工作集", "encoder 权重约 300 MB（6.2.3 常驻矛盾）"),
                ("延迟容忍", "确定性 ms 级；睡眠 → 首个 embedding < 100 ms")],
        formula=("每次推理能耗 = 重读权重 + 计算", [
            _fx("E = W·e_{LPDDR} + 2·N·T·e_{op}"),
            _fx(f"视觉 T=196：{mv * 1e3:.0f} + {fl_v * c.e_op('W8A8') * 1e3:.1f} = {e_v * 1e3:.1f} mJ"),
            _fx(f"音频 T=8：{mv * 1e3:.0f} + {(e_a - mv) * 1e3:.2f} = {e_a * 1e3:.1f} mJ"),
            _fx("强度 = 2·N·T ÷ W = 2T（INT8）"),
            _fx(f"访存 / 计算：视觉 {mv / (e_v - mv):.1f} 倍，音频 {mv / (e_a - mv):.0f} 倍", f=k.YAHEI)]),
        change="模态融合程度、结构化 head 的丰富度；音频块攒批（如 1 s）可把强度提高约 6 倍，代价是时延。形态稳定性最高（十年级）。",
        placement="输入域：哨兵层（μW）片上常驻；300 MB encoder 权重在 DRAM → 需低功耗常驻分区或近存（6.2.3 三个待决解）。",
        source="v3.4 §4.3 C 类、§6.2；calc.py enc_vision_frame() / enc_audio_chunk()；外部 [C-S#] 见附录 C",
        notes="2029 基线：统一 encoder 300M（INT8）。每次推理都要从 DRAM 重读权重，访存能耗主导。")


def spec_e():
    dense, colbert = c.index_bytes_5y()
    q = c._enc(c.FUT['query_tokens'])[1]
    ce_t = 7.27e12 / F8
    rows = [
        ["个人语料索引", "5 年约 365 万条", "增量写入",
         f"单向量 768 维 int8：{dense / 1e9:.1f} GB；ColBERT 2-bit：{colbert / 1e9:.0f} GB（flash）", "—",
         "邮件 78 万块的传统向量索引 2.4 GB [E-S5]"],
        ["查询编码", "统一 encoder 300M，32 token", f"Agent 驱动，约 {c.DAY['queries']} 次/天",
         "19 GFLOP，重读 300 MB", f"{q * 1e3:.0f} mJ/次", "查询 embedding 3.85 ms（Galaxy Z Flip 6）[E-S6]"],
        ["ANN 召回", "磁盘驻留 IVF", "同上", "从 flash 读约 6 MB；约 2 ops/B", "约 3 mJ/次；DRAM 常驻约 10 MB",
         "Apple MicroNN：< 7 ms、约 10 MB [E-S1]"],
        ["late interaction 精排（基线）", "50 候选 × 200 token", "同上", "MaxSim 约 61 MFLOP + 读候选矩阵 0.36 MB",
         f"约 0.18 mJ/次；E 类全天约 {DAYE['E']:.0f} J", "ColBERT 比交叉编码少 180–23,000 倍 FLOP（服务器）[E-S17]"],
        ["cross-encoder rerank（兜底）", "bge-reranker-v2-m3（非嵌入 302M），50 候选", "同上", "7.27 TFLOP",
         f"70 TOPS 上 {ce_t:.2f} s、0.43 J/次；全天约 {DAYE['E_ce']:.0f} J",
         "S24 上 rerank 使首 token +0.38 s [E-S2]；Mac M2 上 0.6B rerank 占管线 96% [E-S7]"],
    ]
    return dict(
        key="E", name="检索（ANN + Rerank）", cluster="存储底座（ANN）+ 算力簇（rerank）", half_life=("快变量",),
        definition="服务记忆（状态）的读路径：查询编码 → ANN 召回 → 精排，在消化关键路径上",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(3,),
        coords=[("算术强度", "ANN 约 2 ops/B（int8 距离）→ 带宽；rerank（按非嵌入参数 2.1–7.3 TFLOP）成批时算力受限、逐候选串行带宽受限"),
                ("占空比", f"Agent 驱动，约 {c.DAY['queries']} 次/天"),
                ("持续功率", "ANN 低；cross-encoder rerank 突发 0.43 J/次"),
                ("工作集", f"索引存 flash：单向量 {dense / 1e9:.1f} GB / ColBERT {colbert / 1e9:.0f} GB；DRAM 常驻约 10 MB"),
                ("延迟容忍", "低：在消化关键路径上")],
        formula=("rerank 量级（按非嵌入参数）", [
            _fx("50 候选 × 232 token：非嵌入 85M → 2.1 TFLOP；302M → 7.3 TFLOP"),
            _fx(f"统一池 70 TOPS：{ce_t:.2f} s（302M）；mW 引擎 1 TOPS：2.1–7.3 s"),
            _fx("late interaction（含小模型查询编码）≈ 1.44 GFLOP"),
            _fx("→ 降 2–4 个数量级（190–5,000 倍）", f=k.YAHEI),
            _fx(f"代价：ColBERT 索引 {colbert / 1e9:.0f} GB ≈ 单向量的 {colbert / dense:.0f} 倍", f=k.YAHEI)]),
        change="「E 类不是计算负载」是当前技术偏见。首选解在模型侧（late interaction），兜底是双模路由；召回要求上升会推高 rerank 候选数。",
        placement="ANN 索引在 flash（存储底座）；查询编码走统一 encoder；兜底的大 rerank 上调统一池（引入抖动）。",
        source="v3.4 §4.3 E 类；calc.py index_bytes_5y() / day_energy()；外部 [E-S#] 见附录 C",
        notes="按总参数算约 6 TFLOP；XLM-R 系 reranker 大半参数是词嵌入表，这里按非嵌入参数计。")


def spec_p():
    be = c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_BIG, F4)
    pt = c.day_prefill_tokens()
    rows = [
        ["Agent 轮次 prefill", "常驻 8B（2-bit 权重，W4A8）", f"{c.day_rounds()} 轮/天，ΔL 200–20K（均值 3K）",
         f"3K：{2 * c.N_MID * 3000 / 1e12:.0f} TFLOP",
         f"3K：{2 * c.N_MID * 3000 / F4:.2f} s；{c.e_prefill_tok_future() * 1e3:.2f} mJ/token；全天 {pt / 1e4:.0f} 万 token ≈ {DAYE['P'] / 1e3:.2f} kJ（{_pct(DAYE['P'])}）",
         "端侧 UI 自动化中 prefill 占推理时延 94–99% [R4-S26]"],
        ["交互问答首轮", "同上", f"{c.DAY['qa']} 次/天", f"1K：{2 * c.N_MID * 1000 / 1e12:.0f} TFLOP",
         fmt_t(2 * c.N_MID * 1000 / F4), "—"],
        ["UFS 流式大模型", "30B dense INT4", f"ΔL ≥ {be / 1e3:.2f}K 的轮次", "60 GFLOP × ΔL",
         f"ΔL × {c.t_tok(c.N_BIG, F4) * 1e3:.2f} ms（见 6.4）", "—"],
    ]
    return dict(
        key="P", name="Prefill（上下文消化）", cluster="算力簇", half_life=("快变量",),
        definition="读取并消化上下文；Agent token 账的主体（90%+ token 在 prefill）",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(0,),
        coords=[("算术强度", "数百 ops/byte（分块 GEMM）→ 算力受限；prefill 脊点 615 / 1230"),
                ("占空比", f"突发；{c.day_rounds()} 轮/天，NPU 约 {pt * 16e9 / F4:.0f} s/天"),
                ("持续功率", "~4 W（满算力、MFU 70%）；可压到低频点长跑"),
                ("工作集", "权重（8B @2-bit = 2 GB）+ 本轮新写的 KV"),
                ("延迟容忍", "chat 首 token < 1 s；Agent 每轮秒级；后台无要求")],
        formula=("量级算例（与 2.4.1 一致）", [
            _fx("t_{prefill} = 2·N·ΔL ÷ F_{eff}"),
            _fx(f"8B，ΔL=4000：2×8×10⁹×4000 ÷ 140×10¹² ≈ {2 * c.N_MID * 4000 / F4:.2f} s"),
            _fx(f"每 token（ΔL=3K）：计算 {c.e_comp_tok(c.N_MID) * 1e3:.3f} + 权重摊销 {(c.e_prefill_tok_future() - c.e_comp_tok(c.N_MID)) * 1e3:.3f} mJ"),
            _fx(f"30B（6.4）：t_{{tok}} ≈ {c.t_tok(c.N_BIG, F4) * 1e3:.2f} ms")]),
        change="显著可变（快变量）：Causal Encoder-Decoder 让 prefill 只走浅层（DeepSeek V4.1-Flash：prefill 激活 8B、decode 激活 16B）；稀疏注意力、层跳过同向。",
        placement="算力簇 → 统一池大 MAC 阵列（大阵列、低频点、长时跑）；6.4 UFS 路径的热瓶颈来源；MAC 阵列与内存接口独立 DVFS（4.5）。",
        source="v3.4 §4.3 P 类、§2.4、§6.4.2；calc.py day_prefill_tokens() / e_prefill_tok_future()",
        notes="耗时按 8B、W4A8 140 TOPS 有效；不含长上下文注意力项（与 5.2.2 线性项口径一致）。")


def spec_dw():
    tps = [c.decode_tok_s(w) for w in (4e9, 2e9, 1e9)]
    dt = c.day_decode_tokens()
    rows = [
        ["Agent 与问答输出", "常驻 8B @2-bit（2 GB）", f"{c.day_rounds() + c.DAY['qa']} 次 × 300 token ≈ {dt / 1e4:.1f} 万 token/天",
         f"2 GB 权重 + {c.kv_read_step() / 1e6:.1f} MB KV",
         f"{c.decode_tok_s_future():.1f} tok/s；{c.e_decode_tok_future():.2f} J/token；约 {dt / c.decode_tok_s_future() / 3600:.1f} h/天、{DAYE['D-w'] / 1e3:.1f} kJ（{_pct(DAYE['D-w'])}）",
         "Apple 端侧基础模型已用 2-bit QAT [R4-S13]"],
        ["对照：5.3.1 三档", "8B@INT4 / 8B@2bit / 4B@2bit", "—", "4 / 2 / 1 GB",
         f"{tps[0]:.0f} / {tps[1]:.0f} / {tps[2]:.0f} tok/s（痛 / 可接受 / 不痛）", "5.3.1"],
        ["反例：UFS 大模型自己 decode", "30B dense INT4", "—", "15 GB（来自 UFS 5.0）",
         f"{c.B_UFS['UFS5'] / c.W_BIG:.2f} tok/s → 交给常驻小模型", "6.4"],
        ["投机解码（可选）", "+ draft 核", "—", "一次 verify 摊薄权重读取", "等效带宽 × k（k 为接受的 token 数，6.3.3）", "—"],
    ]
    return dict(
        key="D-w", name="Decode 的权重读取", cluster="带宽簇", half_life=("不变量", "快变量"),
        definition="每生成一个 token 必须把激活权重读一遍——数学上无解的那部分",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(0,),
        coords=[("算术强度", "2 ÷ (位宽/8)：INT8 ≈ 2、INT4 ≈ 4、2bit ≈ 8 → 远低于 decode 脊点"),
                ("占空比", f"随 decode：约 {dt / c.decode_tok_s_future() / 3600:.1f} h/天"),
                ("持续功率", f"内存接口主导：{c.B_LPDDR6 / 1e9:.1f} GB/s × 0.05 nJ/B ≈ {c.B_LPDDR6 * c.E_LPDDR:.1f} W（满带宽），超过 3–5 W 持续包络 → 长时 decode 需降频"),
                ("工作集", "全部激活权重（2 GB），每 token 顺序读一遍"),
                ("延迟容忍", "chat / 语音：带宽即体验；前台 Agent 中；后台 ≈ 0（2.4.2）")],
        formula=("量级算例", [
            _fx("tok/s = B_{LPDDR} ÷ (W + KV_{step})"),
            _fx(f"113.8 GB/s ÷ (2 GB + {c.kv_read_step() / 1e6:.1f} MB) ≈ {c.decode_tok_s_future():.1f} tok/s"),
            _fx(f"每 token：{(c.FUT['w_resident'] + c.kv_read_step()) / 1e9:.2f} GB × 0.05 nJ/B ≈ {c.e_decode_tok_future():.2f} J"),
            _fx("押注对象是不等式：D-w 痛度 > 通用方案阈值（5.3.1）", f=k.YAHEI)]),
        change="存在性不变、量级快变：只能靠量化与小模型化压小，压不掉；投机解码 verify 把强度从 ~2 抬到 ~2k（6.3.3）。",
        placement="带宽簇 → 近存、宽接口、量化；内存接口独立电源域与 DVFS（4.5）；V 类语音原生帧与之同族。",
        source="v3.4 §4.3 D-w 类、§5.3.1；calc.py decode_tok_s_future() / e_decode_tok_future()",
        notes="tok/s 按 LPDDR6 113.8 GB/s 满带宽估算，未计带宽利用率。")


def spec_da():
    step = c.kv_read_step()
    rows = [
        ["100K 上下文 Agent decode", "CSA2 + FP4 KV（890 B/token）+ 稀疏 top-k 2048", f"随 decode（{c.day_decode_tokens() / 1e4:.1f} 万 token/天）",
         f"每步读约 {step / 1e6:.1f} MB", f"占每步读取的 {step / (c.FUT['w_resident'] + step):.1%}", "DeepSeek-V4.1-Flash 全局 KV 890 B/token [KV-S46]"],
        ["KV 总量", "100K × 890 B", "—", f"约 {890 * 1e5 / 1e6:.0f} MB（1M 约 0.89 GB）", "—", "同上"],
        ["若为 dense MLA（6.3.1 口径）", "latent 576，60 层", "—", "—", "6.9 GFLOP/token（D-w 的 43%）", "6.3.1"],
        ["对照：端侧现状 dense GQA", "Qwen3-8B INT8 约 74 KB/token", "—", "每步 7.4 GB",
         f"仅 {c.B_LPDDR6 / (2e9 + 73728 * 1e5):.0f} tok/s", "Qwen3-8B config.json [R4-S28]"],
    ]
    return dict(
        key="D-a", name="Decode 的注意力计算", cluster="算力簇", half_life=("快变量",),
        definition="新 token 与历史 KV 做注意力；稀疏 top-k 之后，每步只读少量 KV",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(0,),
        coords=[("算术强度", "MLA/CSA ~220 > decode 脊点 88–176（W8A8）→ 算力受限；GQA ~16 < 88 → 仍带宽受限"),
                ("占空比", "随 decode"),
                ("持续功率", "稀疏 top-k 后与 L 基本解耦"),
                ("工作集", f"100K × 890 B ≈ 89 MB；每步读约 {step / 1e6:.1f} MB"),
                ("延迟容忍", "同 decode（2.4.2 场景权重）")],
        formula=("稀疏 decode 每步读 KV", [
            _fx(f"top-k 2048 × 890 B ≈ {2048 * 890 / 1e6:.1f} MB"),
            _fx("indexer K：100K × 128 B ≈ 12.8 MB（假设）"),
            _fx(f"合计 ≈ {step / 1e6:.1f} MB，是 2 GB 权重的 {step / 2e9:.1%}"),
            _fx("dense GQA 对照：100K × 74 KB = 7.4 GB → 12 tok/s", f=k.YAHEI)]),
        change="注意力机制迭代极快（MHA → GQA → MLA → CSA），每一代都在提高算术强度；「铁」的只有 D-w。",
        placement="算力簇 → 大 MAC 阵列；注意力按 W8A8（A8×A8）口径。",
        source="v3.4 §4.3 D-a 类、§4.2、§6.3.1；calc.py kv_read_step()；外部 [KV-S46] 见附录 C",
        notes="indexer K 每 token 128 B 为假设；DeepSeek 未公开端侧参数。")


def spec_v():
    bw = c.voice_bw()
    rows = [
        ["语音原生全双工", "常驻 8B @2-bit，12.5 Hz 语音帧", f"{c.DAY['voice_sessions']} 次 × {c.DAY['voice_min']} min/天",
         f"2 GB × 12.5 = {bw / 1e9:.0f} GB/s（{bw / c.B_LPDDR6:.0%}）",
         f"每帧读权重 {c.voice_frame_ms():.1f} ms（预算 80 ms）；{bw * c.E_LPDDR:.2f} W；全天约 {DAYE['V'] / 1e3:.2f} kJ（{_pct(DAYE['V'])}）",
         "Hibiki-M 1.7B 在 iPhone 16 Pro 上连续 1 分钟实时 [V-S3]；Moshi：12.5 Hz、理论 160 ms [V-S1]"],
        ["对照：级联（ASR + LLM + 小 TTS）", "0.5B TTS @25 Hz + 文本约 4 tok/s", "—", "约 14 GB/s", "—", "CosyVoice 2：25 Hz 语音 token [V-S4]"],
        ["对照：非自回归 TTS", "Kokoro-82M / F5-TTS 336M", "整句", "可忽略", "一次前向处理数百帧，算力受限", "Kokoro 在 iPhone 13 Pro 上约 3.3× 实时 [V-S8]"],
    ]
    return dict(
        key="V", name="语音生成（语音原生 / 自回归音频解码）", cluster="带宽簇（与 D-w 同族）", half_life=("快变量",),
        definition="全文唯一要求多原语真正并发、且总预算为硬约束的场景（6.3.5）",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(0,),
        coords=[("算术强度", "自回归批 1：2/b → 2-bit 为 8 ops/B → 带宽受限"),
                ("占空比", f"事件触发（{c.DAY['voice_sessions']} 次 × {c.DAY['voice_min']} min/天），启动后必须确定性"),
                ("持续功率", f"{bw / 1e9:.0f} GB/s（LPDDR6 {bw / c.B_LPDDR6:.0%}）、约 {bw * c.E_LPDDR:.2f} W，不可抢占"),
                ("工作集", "复用常驻主模型权重（2 GB）+ 会话 KV"),
                ("延迟容忍", f"硬实时：每 80 ms 一帧，读权重 {c.voice_frame_ms():.1f} ms")],
        formula=("语音原生的带宽与功率", [
            _fx(f"BW = W_{{主模型}} × 帧率 = 2 GB × 12.5 Hz = {bw / 1e9:.0f} GB/s"),
            _fx(f"每帧读权重 = 2 GB ÷ 113.8 GB/s = {c.voice_frame_ms():.1f} ms < 80 ms"),
            _fx(f"功率 = {bw / 1e9:.0f} GB/s × 0.05 nJ/B = {bw * c.E_LPDDR:.2f} W")]),
        change="非自回归 / 流匹配类 TTS 可显著降低带宽依赖并提高并行度（快变量）；级联方案约 14 GB/s。",
        placement=f"统一池；调度器 QoS 最高优先级，带宽配额 {bw / 1e9:.0f} GB/s 预留而非竞争获得（6.3.5）。",
        source="v3.4 §4.3 V 类、§6.3.5；calc.py voice_bw() / voice_frame_ms()；外部 [V-S#] 见附录 C",
        notes="2029 基线：语音原生全双工，由常驻主模型直接生成 12.5 Hz 语音 token。")


def spec_g():
    rows = [
        ["1024² 图像生成", "约 0.4B 主干，4–8 步", f"{c.DAY['images']} 张/天", "VAE 解码单张量 268 MB，须分块",
         f"1–2 s；约 {c.FUT['g_image_j']:.0f} J/张（估算：162 J × 少步约 1/4）",
         "SnapGen 1024² 约 1.4 s（iPhone 16 Pro Max）[G-S27]；SD1.5 约 162 J/张（小米 14 Pro）[G-S40]"],
        ["5 s 短视频生成", "约 0.6B，4 步", f"{c.DAY['videos']} 段/天", "—",
         f"约 4–5 s；约 {c.FUT['g_video_j']:.0f} J/段（估算：5 W × 4 s）",
         "SnapGen-V 5 s 视频约 4–5 s 生成 [G-S42]；SVD 在手机上 OOM [G-S41]"],
    ]
    return dict(
        key="G", name="扩散生成", cluster="算力簇",
        definition="迭代型生成，每步一次大前向；高分辨率下工作集以激活为主",
        instances=(ANCHOR_HDR, rows, ANCHOR_W),
        coords=[("算术强度", "高，迭代型 → 算力受限"),
                ("占空比", f"突发，每天约 {c.DAY['images']} 张图 + {c.DAY['videos']} 段视频；全天约 {DAYE['G']:.0f} J"),
                ("持续功率", "高（蹭大 MAC 阵列，与思考错峰）"),
                ("工作集", "1024² 以上的 VAE 解码 / 未融合注意力：激活超过权重；512² 融合后约 0.1 GB（远小于 UNet 权重 1.64 GB）"),
                ("延迟容忍", "高：秒级到十秒级")],
        formula=("VAE 解码最高一级的激活", [
            _fx("H × W × 128 通道 × 2 B"),
            _fx(f"1024²：{1024 * 1024 * 128 * 2 / 1e6:.0f} MB；1080p：{1920 * 1080 * 128 * 2 / 1e6:.0f} MB"),
            _fx("解码器权重 49.5M × 2 B ≈ 99 MB")]),
        change="与 D-w 相反，带宽优化对它近乎无效；少步蒸馏（1–8 步）正在快速降低步数。",
        placement="算力簇 → 大 MAC 阵列 + 激活高速区（按最大分辨率定容，6.3.4）；高分辨率须分块解码。",
        source="v3.4 §4.3 G 类、§6.3.4；calc.py FUT['g_image_j'] 等为估算；外部 [G-S#] 见附录 C",
        notes="单图 / 单段视频能耗为估算，仅用于量级。")


def spec_f():
    rows = [
        ["夜间 LoRA（常驻 8B）", "1000 步 × 256 token", "每日一次，充电窗口 ~6 h",
         f"6 × 8B × 25.6 万 token ≈ {_sci(c.lora_flop())} FLOP",
         f"按有效算力 70 TOPS 的 30%（21 TOPS）约 {c.lora_minutes():.0f} min；约 {F_LO / 1e3:.2f}–{F_HI / 1e3:.1f} kJ（充电中，不计电池）",
         "MeBP：iPhone 15 Pro Max 上 Qwen2.5-3B 每步 18 s、内存 0.66 GB（不含权重）[R4-S1]"],
        ["内存预算", "2-bit 冻结权重 2 GB + LoRA + 重算后的激活", "—", "—", "数 GB",
         "Llama-3.2-3B @1024 token：全参 29.97 GB → LoRA + INT4 + 重算 3.33 GB [R4-S4]"],
    ]
    return dict(
        key="F", name="端侧自适应", cluster="存储底座（F 工作集）", half_life=("快变量",),
        definition="充电窗口里给常驻模型做 LoRA；个性化是绑定特定权重版本的",
        instances=(ANCHOR_HDR, rows, ANCHOR_W),
        coords=[("算术强度", "前向 + 反向（与 prefill 同类）"),
                ("占空比", f"每日一次，~6 h 窗口内约 {c.lora_minutes():.0f} min"),
                ("持续功率", f"充电时散热最好；约 {F_LO / 1e3:.2f}–{F_HI / 1e3:.1f} kJ/次（不计电池）"),
                ("工作集", "2-bit 冻结权重 2 GB + LoRA + 重算后的激活：数 GB"),
                ("延迟容忍", "可延迟")],
        formula=("算力与内存", [
            _fx("FLOP ≈ 6·N·tokens = 6 × 8×10⁹ × 25.6 万"),
            _fx(f"70 TOPS × 30% = 21 TOPS → 约 {c.lora_minutes():.0f} min"),
            _fx(f"能耗下限 = FLOP × e_{{op}}(W4A8) ≈ {F_LO / 1e3:.2f} kJ"),
            _fx(f"上限 = FLOP × e_{{op}}(W8A8) {c.lora_flop() * c.e_op('W8A8') / 1e3:.2f} + 权重重读 {(F_HI - c.lora_flop() * c.e_op('W8A8')) / 1e3:.2f} ≈ {F_HI / 1e3:.1f} kJ"),
            _fx(f"全参 Adam：16 B/参数 × 8B = {c.full_adam_bytes(8e9) / 1e9:.0f} GB"),
            _fx("LoRA + 低比特 + 重算 → 数 GB（低一个量级以上）", f=k.YAHEI)]),
        change="版本迁移三解：OTA 后重训 / 冻结基础模型 / 个性化入记忆。若第三解成立，F 类重要性大幅下降——路线选择应先于硬件预算决定。",
        placement="存储底座承载 F 工作集；充电窗口复用统一池算力。瓶颈在软件栈与内存，不在算力。",
        source="v3.4 §4.3 F 类；calc.py lora_flop() / full_adam_bytes()；外部 [R4-S#] 见附录 C",
        notes="训练 MFU 30% 为假设；MeBP 等实测有效吞吐 0.26–1.1 TFLOPS，差距在软件栈。")


def spec_ctrl():
    pm, tm, ps = c.ctrl_round()
    rows = [
        ["工具返回解析 + 分词", "最多 20K token（约 80 KB）", f"{c.day_rounds()} 轮/天", f"解析 {pm:.2f} ms，分词 {tm:.0f} ms（单线程）",
         f"约为该轮 prefill {ps:.1f} s 的 1%；全天约 {DAYE['Ctrl']:.0f} J（上界；按均值 3K 约 2 J）",
         "A14 上 yyjson 2.39 GB/s [R4-S15]；SentencePiece 7.44 MB/s、HF Fast 3.66 MB/s（服务器单线程）[R4-S19]"],
        ["调度（Ctrl-s）", "标量", "每轮", "可忽略", "要求确定性延迟", "—"],
        ["工具执行（外部等待，非计算原语）", "网络 / 文件 / 跑代码", "每轮", "—", "数百 ms 到数十秒",
         "服务器端 agent 研究：工具处理占 2–89%，随负载而变 [R4-S22, R4-S23]"],
    ]
    return dict(
        key="Ctrl", name="编排与数据预处理", cluster="CPU 串行（Ctrl-d）", half_life=("快变量",),
        definition="Ctrl-s 调度 + Ctrl-d 工具返回的解析、校验与分词",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(0,),
        coords=[("算术强度", "字节处理，每字节数条到数十条指令，无 MAC"),
                ("占空比", f"每轮一次（{c.day_rounds()} 轮/天）"),
                ("持续功率", f"CPU；全天约 {DAYE['Ctrl']:.0f} J（上界）"),
                ("工作集", "单次 KB–百 KB；分词器约 6 MB"),
                ("延迟容忍", "串行在关键路径上，但计算量约为该轮 prefill 的 1%")],
        formula=("一轮 20K token 工具返回", [
            _fx(f"80 KB ÷ 2.39 GB/s ≈ {pm:.2f} ms（解析）"),
            _fx(f"80 KB ÷ 3.66 MB/s ≈ {tm:.0f} ms（分词）"),
            _fx(f"prefill：20K × 16 GFLOP ÷ 140 TOPS ≈ {ps:.1f} s")]),
        change="agent 循环结构与工具接口仍未稳定（2.1）。关键路径上的非模型时间主要是工具执行本身，属外部等待。",
        placement="CPU 串行簇 → 低延迟核、不可被抢占（4.4）。",
        source="v3.4 §4.3 Ctrl 类、§4.4；calc.py ctrl_round()；外部 [R4-S#] 见附录 C",
        notes="4 B/token 为假设；分词按单线程。")


def spec_kvio():
    rate = F4 / (2 * c.N_MID)
    rows = [
        ["prefill 写 KV", "890 B/token", f"{c.day_prefill_tokens() / 1e4:.0f} 万 token/天", "每轮 3K token 写约 2.7 MB",
         f"{rate:,.0f} tok/s × 890 B ≈ {rate * 890 / 1e6:.1f} MB/s，可忽略", "DeepSeek-V4.1-Flash：CSA2 + FP4 主 KV [KV-S46]"],
        ["decode 逐 token 写 KV", "890 B/token", f"{c.day_decode_tokens() / 1e4:.1f} 万 token/天", "—", "可忽略", "同上"],
        ["会话 KV 持久化", "100K × 890 B = 89 MB", f"{c.DAY['fg_tasks'] + c.DAY['bg_tasks']} 个任务/天", "—",
         "UFS 5.0 顺序写约 8 ms（按 10.8 GB/s 估）", "—"],
        ["对照：端侧现状", "Qwen2.5-1.5B 28.7 KB、Llama-3.2-3B 115 KB、Qwen3-4B 147 KB（FP16/token）", "—",
         "32K 下 0.9–4.8 GB", "—", "官方 config.json [R4-S27, R4-S28]；Apple KV 8-bit + 共享（−37.5%）[R4-S13]"],
    ]
    return dict(
        key="KV-io", name="KV 写入与迁移", cluster="跨簇（访存）", half_life=("快变量",),
        definition="其他原语里没有归属的 KV 访存：写入、持久化、层级迁移",
        instances=(ANCHOR_HDR, rows, ANCHOR_W), hl_rows=(3,),
        coords=[("算术强度", "纯访存"),
                ("占空比", "随 P / D；任务结束时持久化"),
                ("持续功率", f"写带宽约 {rate * 890 / 1e6:.1f} MB/s，可忽略"),
                ("工作集", "890 B/token：100K 约 89 MB，1M 约 0.89 GB"),
                ("延迟容忍", "随所属相位")],
        formula=("KV 容量与写带宽", [
            _fx("KV = L × 890 B：100K → 89 MB"),
            _fx(f"写带宽 = {rate:,.0f} tok/s × 890 B ≈ {rate * 890 / 1e6:.1f} MB/s"),
            _fx("持久化 89 MB ÷ 10.8 GB/s ≈ 8 ms")]),
        change="端侧小模型的 KV 压缩不一定跟得上前沿；跨层复用、稀疏索引能否下放是空白，需实测（附录 B 实测 B）。",
        placement="统一池近存 / LPDDR；当前注意力窗口可选择性提到近存层（6.3.2）。",
        source="v3.4 §4.3 KV-io 类、§6.3.2；calc.py；外部 [KV-S46]、[R4-S#] 见附录 C",
        notes="2029 基线取分支 C：前沿 KV 压缩（890 B/token）下放到端侧。")


# ---------------------------------------------------------------- 2029 基线页
def slide_baseline(prs):
    s = k.add_slide(prs, "4.3", "2029 负载基线：决策、重度使用日与口径",
                    source="v3.4 §4.3 开头；calc.py FUT / DAY；外部依据见附录 C")
    k.box(s, I(0.45), I(1.05), I(6.1), I(1.35), [
        _p("方法", 11, k.TEALDK, True),
        _p("① 从 2.4 的场景推 2029 负载，不拿今天的应用负载替代未来负载；② 模型形态取已发生的趋势；③ 今天的实测只作校准锚；④ 统一按目标 SoC 口径换算。", 10)],
        fill=k.BAND, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.table(s, I(0.45), I(2.55), I(6.1), I(2.4), ["基线决策（2026-09-11 对齐）", "取值", "依据（已发生的趋势）"], [
        ["常驻模型", "8B @2-bit（2 GB）", "Apple 端侧基础模型 2-bit QAT [R4-S13]"],
        ["KV 格式", "CSA2 + FP4，890 B/token + 稀疏 top-k", "DeepSeek-V4.1-Flash [KV-S46]"],
        ["语音", "语音原生全双工，12.5 Hz 帧", "Moshi / Hibiki（iPhone 16 Pro 实时）[V-S1, V-S3]"],
        ["统一 encoder", "300M，INT8 约 300 MB", "Gemma 3n MobileNet-V5-300M [C-S26]"],
    ], col_w=[1.2, 2.2, 2.7], s=9.5, first_col_bold=True)
    k.table(s, I(0.45), I(5.1), I(6.1), I(1.8), ["换算口径", "取值"], [
        ["有效算力", "140 / 70 TOPS（W4A8 / W8A8）"],
        ["每 op 能耗", f"{c.e_op('W4A8') * 1e12:.4f} / {c.e_op('W8A8') * 1e12:.3f} pJ"],
        ["LPDDR6", "113.8 GB/s，0.05 nJ/B"],
        ["UFS 5.0", "10.8 GB/s，0.5 nJ/B"],
    ], col_w=[1.4, 4.7], s=9.5, first_col_bold=True)
    D = c.DAY
    k.table(s, I(6.78), I(1.05), I(6.1), I(4.3), ["重度使用日", "参数"], [
        ["前台 Agent", f"{D['fg_tasks']} 个任务 × {D['fg_rounds']} 轮"],
        ["后台 Agent", f"{D['bg_tasks']} 个任务 × {D['bg_rounds']} 轮"],
        ["每轮", f"ΔL 均值 {D['dl'] // 1000}K，decode {D['k']} token"],
        ["交互问答", f"{D['qa']} 次（1K prefill + 300 decode）"],
        ["语音双工", f"{D['voice_sessions']} 次 × {D['voice_min']} min"],
        ["相机 / 屏幕活跃", f"约 {D['cam_hours']} h（1 fps 理解）"],
        ["检索 / 语料摄入", f"{D['queries']} 次 / {D['items']} 条"],
        ["生成媒体", f"{D['images']} 张图 + {D['videos']} 段短视频"],
        ["电池", f"5000 mAh × 3.85 V ≈ {c.FUT['battery_j'] / 1e3:.0f} kJ"],
    ], col_w=[1.6, 4.5], s=9.5, first_col_bold=True)
    k.box(s, I(6.78), I(5.5), I(6.1), I(1.4), [
        _p("由此推出", 11, k.TEALDK, True),
        _p(f"prefill 约 {c.day_prefill_tokens() / 1e4:.0f} 万 token/天；decode 约 {c.day_decode_tokens() / 1e4:.1f} 万 token/天；"
           f"{c.day_rounds()} 个 Agent 轮次/天。各原语的 2029 负载见后十页的「负载实例」表。", 10),
        _p("口径：2.4.1 与 6.4 沿用 8B INT4 口径（decode 约 28 tok/s）；本章 2029 基线为 8B @2-bit（约 56.5 tok/s）。", 9.5, k.MUTE)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.notes(s, "基线决策由评审确认（2026-09-11）；重度使用日参数沿用对账稿，评审未提异议。全部数字由 calc.py 计算。")


# ---------------------------------------------------------------- 非原语页
def slide_4_1(prs):
    s = k.add_slide(prs, "4.1", "刻画负载的五个坐标", half_life=("不变量",), source="v3.4 §4.1、§4.3 通用标注规则")
    k.text(s, I(0.45), I(1.05), I(12.43), I(0.45), [
        [{"t": "硬件只认这五个坐标，不认功能归属。", "b": True, "s": 13},
         {"t": "任何负载都用它们完全刻画。", "s": 13, "c": k.MUTE}]])
    items = [("① 算术强度", "ops/byte", "受算力墙还是带宽墙约束（对照 4.2 脊点）"),
             ("② 占空比", "活跃时间比例", "一天中活跃时间的比例"),
             ("③ 持续功率", "峰值 + 可持续时长", "记两个数；直接对接 1.3 的热约束"),
             ("④ 工作集", "驻留量 + 访问模式", "驻留数据量与访问模式（顺序 / 随机）"),
             ("⑤ 延迟容忍度", "调度自由度", "决定能否压到能效点、能否被抢占")]
    for i, (t1, t2, t3) in enumerate(items):
        x = 0.45 + i * 2.5
        k.box(s, I(x), I(1.65), I(2.38), I(1.9),
              [_p(t1, 13, k.TEALDK, True), _p(t2, 11, b=True), _p(t3, 10, k.MUTE)],
              fill=k.BAND, line=k.TEAL)
    k.box(s, I(0.45), I(3.8), I(6.1), I(1.55), [
        _p("为什么「持续功率」要单独成一维", 11.5, k.TEALDK, True),
        _p("占空比只说跑多久的比例，没说跑的时候烧多少瓦。哨兵层（常开约 0.5 mW）与 P 类（突发约 4 W）差近四个数量级；C 类 encoder 活跃期（22–95 mW）与 P 类也差 1.5–2 个数量级（见 4.3 C 类）。", 10.5)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(6.78), I(3.8), I(6.1), I(1.55), [
        _p("通用标注规则（4.3）", 11.5, k.TEALDK, True),
        _p("每个原语的坐标值是「当前范式下的取值」，必须同时标注「可被什么改变」。坐标值是模型设计可移动的量，不是物理常数。", 10.5)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    gf = k.chart(s, I(0.45), I(5.5), I(12.43), I(1.45), "barh", ["哨兵（常开）", "C 类 encoder（活跃期）", "P 类（突发）"],
                 {"功率 W（对数轴）": [0.0005, 0.095, 4]}, colors=[k.TEAL], legend=False, y_title="W（对数）")
    k._log_axis(gf.chart.value_axis)
    k.notes(s, "五坐标是后面九类十节原语页的统一格式；第三维对接 1.3 的热约束。")


def slide_4_2_ridge(prs):
    s = k.add_slide(prs, "4.2", "脊点判据：必须分相位", half_life=("快变量",),
                    source="v3.4 §4.2；calc.py ridge()")
    B = c.B_LPDDR6
    k.formula_box(s, I(0.45), I(1.05), I(6.2), I(2.75), "有效脊点 = 实测算力 ÷ 实测带宽（带宽取 LPDDR6 113.8 GB/s）", [
        k.fx(f"峰值反例：200 TOPS ÷ 113.8 GB/s ≈ {round(c.ridge(c.F_PEAK['W4A8']), -1):.0f}（W4A8）；100 TOPS ÷ 113.8 ≈ {round(c.ridge(c.F_PEAK['W8A8']), -1):.0f}（W8A8）"),
        k.fx("错在峰值在不同相位的可达性差 3.5–7 倍", f=k.YAHEI, c=k.RED),
        k.fx(f"Prefill：MFU 70% → 70 / 140 TOPS → 脊点 {c.ridge(c.f_eff('W8A8')):.0f} / {c.ridge(c.f_eff('W4A8')):.0f}"),
        k.fx("Decode（batch=1）：MFU 10–20% → 10–20 / 20–40 TOPS"),
        k.fx(f"   → 脊点 {c.ridge(10e12):.0f}–{c.ridge(20e12):.0f}（W8A8）/ {c.ridge(20e12):.0f}–{c.ridge(40e12):.0f}（W4A8）"),
        k.fx("精度映射：INT4 权重 GEMM 按 W4A8；注意力 QKᵀ、AV 是 A8×A8，按 W8A8", f=k.YAHEI, b=True, c=k.TEALDK),
    ], s=10.5)
    k.table(s, I(0.45), I(3.95), I(6.2), I(1.2), ["相位", "MFU", "有效算力（W8A8 / W4A8）", "有效脊点"], [
        ["Prefill（慢吞吐、大序列维）", "~70%", "70 / 140 TOPS", "615 / 1230"],
        ["Decode（batch=1）", "10–20%", "10–20 / 20–40 TOPS", "88–176 / 176–351"],
    ], col_w=[2.0, 0.8, 1.8, 1.6], s=10)
    k.box(s, I(0.45), I(5.35), I(6.2), I(1.55), [
        [{"t": "为什么必须分相位：", "b": True, "c": k.RED, "s": 10.5},
         {"t": f"用峰值脊点（{round(c.ridge(c.F_PEAK['W4A8']), -1):.0f} / {round(c.ridge(c.F_PEAK['W8A8']), -1):.0f}）会把 MLA 这类算子一律判为带宽受限；"
               "同一颗芯片的 prefill 与 decode 脊点相差 3.5–7 倍，MLA（~220）恰好落在两相位脊点之间（见下页）。",
          "s": 10.5}]], fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)
    rl = lambda F: [(1, B / 1e12), (F / B, F / 1e12), (10000, F / 1e12)]
    k.xy_chart(s, I(6.85), I(1.05), I(6.03), I(5.2),
               {"Prefill W4A8（140 TOPS）": rl(c.f_eff('W4A8')), "Prefill W8A8（70 TOPS）": rl(c.f_eff('W8A8')),
                "Decode W8A8 上限（20 TOPS）": rl(20e12), "Decode W8A8 下限（10 TOPS）": rl(10e12)},
               colors=[k.TEAL, k.TEALLT, k.RED, k.AMBER], x_title="算术强度（ops/byte，对数）",
               y_title="可达算力（TOPS，对数）", log=True, x_range=(1, 10000))
    k.text(s, I(6.85), I(6.3), I(6.03), I(0.6), [
        _p("参照：INT8 权重 ~2 · INT4 权重 ~4 · GQA ~16 · MLA ~220（ops/byte）", 10, k.MUTE)])
    k.notes(s, "roofline：可达算力 = min(F_eff, 强度 × 113.8 GB/s)。拐点即脊点。")


def slide_4_2_ops(prs):
    s = k.add_slide(prs, "4.2", "同一算子在两个相位下落在脊点两侧", half_life=("快变量",),
                    source="v3.4 §4.2")
    k.table(s, I(0.45), I(1.05), I(7.4), I(2.4), ["算子", "算术强度", "Prefill（脊点 615 / 1230）", "Decode（脊点 88–176 / 176–351）"], [
        ["权重读取（INT8）", "~2", "—", "带宽受限"],
        ["权重读取（INT4）", "~4", "—", "带宽受限"],
        ["GQA 注意力", "~16", "带宽受限", "带宽受限"],
        ["MLA / 压缩注意力", "~220", "带宽受限（220 < 615）", "算力受限（220 > 88–176，按 W8A8）"],
    ], col_w=[1.6, 1.0, 2.2, 2.6], s=10.5, hl_rows=(3,), hl_color=k.BAND)
    k.box(s, I(0.45), I(3.65), I(7.4), I(1.45), [
        _p("P/D 矛盾的更根本形式", 11.5, k.TEALDK, True),
        _p("不是「两类负载分属两个簇」，而是同一个算子在两个相位下落在脊点两侧。无法靠「把 P 和 D 分给不同硬件」解决——它们跑的是同一份 KV、同一个 attention kernel。", 10.5)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(0.45), I(5.3), I(7.4), I(1.6), [
        _p("精度映射", 11.5, k.TEALDK, True),
        _p("INT4 权重的矩阵乘按 W4A8 口径（200 TOPS 峰值）；注意力的 QKᵀ 与 AV 是激活×激活（A8×A8），按 W8A8 口径（100 TOPS 峰值）。所以注意力类算子对照 W8A8 脊点 88–176。", 10.5)],
        fill=k.BAND, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(8.05), I(1.05), I(4.83), I(1.95), [
        _p("洞察一：prefill 的高 MFU 不是偶然", 11.5, k.TEALDK, True),
        _p("低频运行恰恰是高 MFU 的条件——高频时供数跟不上、热降频抖动、DVFS 震荡，利用率反而下降。「大阵列、低频点、长时跑」同时是能效选择和利用率选择，两者同向。", 10.5)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(8.05), I(3.15), I(4.83), I(1.6), [
        _p("洞察二：decode 的低 MFU 是形状问题", 11.5, k.TEALDK, True),
        _p("GEMV（矩阵-向量乘）本来就喂不满矩阵单元，堆算力无法改善。decode 的 MAC 不是闲着没活干，而是有活干但 MFU 只有 10–20%。", 10.5)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(8.05), I(4.9), I(4.83), I(2.0), [
        _p("推出的硬件规格（4.5）", 11.5, k.WHITE, True),
        _p("P 要大阵列、低频；D-w 要内存接口高频。同一个 3–5 W 包络内诉求相反 → MAC 阵列与内存接口必须有独立电源域与独立 DVFS，按相位切换功率分配。", 10.5, k.WHITE)],
        fill=k.TEALDK, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.notes(s, "MLA 在 prefill 偏带宽、在 decode 偏算力：这是 4.5 P/D 矛盾的根。")


def slide_overview(prs):
    s = k.add_slide(prs, "4.3", "九类十节原语总表（2029 取值）", source="v3.4 §4.3、§4.4、§4.6；calc.py")
    rows = [
        ["C 流式编码", "哨兵片上 → 算力；300M encoder 重读权重 392 / 16 ops/B → 访存", "分模态：IMU/麦克风 ~100%，相机/屏幕 10–20%", "哨兵 sub-mW；encoder 活跃期 22–95 mW", "encoder 约 300 MB", "确定性 ms 级", "常开簇", "1"],
        ["E 检索", "ANN ~2 ops/B → 带宽；rerank 成批 → 算力", "Agent 驱动约 1000 次/天", "ANN 低 / rerank 0.43 J/次", "索引 flash 2.8–26 GB，DRAM 约 10 MB", "低（关键路径）", "存储底座 + 算力簇", "2（E-ANN）"],
        ["P Prefill", "数百 ops/B → 算力", "突发，650 轮/天", "~4 W（MFU 70%）", "权重 2 GB + 新写 KV", "chat 秒级 / Agent 每轮", "算力簇", "6"],
        ["D-w 权重读取", "2 ÷ (位宽/8) → 带宽", "随 decode，约 1 h/天", "满带宽约 5.7 W", "全部激活权重 2 GB", "chat 高 / 后台 ≈0", "带宽簇", "4"],
        ["D-a 注意力", "MLA/CSA ~220 → 算力；稀疏后每步读 14.6 MB", "随 decode", "稀疏后与 L 解耦", "KV 890 B/token（100K 约 89 MB）", "同 decode", "算力簇", "5"],
        ["V 语音生成", "8 ops/B（2-bit）→ 带宽", "事件触发，启动后确定性", "25 GB/s、约 1.25 W，不可抢占", "复用主模型 2 GB", "硬实时（80 ms 帧）", "带宽簇", "未排序"],
        ["G 扩散", "高 → 算力", "突发", "高", "1024² 以上激活可超过权重", "高（秒到十秒级）", "算力簇", "3"],
        ["F 自适应", "前向 + 反向", "每日一次，约 10 min", "充电时散热最好", "2-bit 冻结权重 + LoRA + 激活", "可延迟", "存储底座", "未排序"],
        ["Ctrl 编排 / 预处理", "字节处理，无 MAC", "每轮", "CPU，全天约 14 J", "单次 KB–百 KB", "关键路径，约为 prefill 的 1%", "CPU 串行", "7（Ctrl-d）"],
        ["KV-io 写入 / 迁移", "纯访存", "随 P / D", "约 7.8 MB/s，可忽略", "890 B/token", "随相位", "跨簇", "未排序"],
    ]
    k.table(s, I(0.45), I(1.05), I(12.43), I(5.4),
            ["原语", "算术强度 → 受限", "占空比", "持续功率", "工作集", "延迟容忍", "簇（4.4）", "稳定性（4.6）"], rows,
            col_w=[1.4, 2.3, 2.0, 1.7, 1.8, 1.4, 1.3, 0.9], s=9, first_col_bold=True, center_cols=(7,))
    k.text(s, I(0.45), I(6.55), I(12.43), I(0.4), [
        _p("稳定性排名：C > E-ANN > G > D-w > D-a > P > Ctrl-d > 未来新范式（1 最稳）。D-a 与 P 的稳定性低于直觉判断。D 类的两个子成分落在脊点两侧，拆为 D-w / D-a 两节，故九类共十节。", 10, k.MUTE)])
    k.notes(s, "取值为 2029 负载基线；逐类细节见后面十页的「负载实例」表。")


def slide_matrix(prs):
    s = k.add_slide(prs, "4.3", "场景 × 原语负载矩阵", source="v3.4 §2.4 场景账本、§3.1 能力清单、§4.3")
    P, O = "●", "○"
    cols = ["C", "E", "P", "D-w", "D-a", "V", "G", "F", "Ctrl", "KV-io"]
    data = [
        ("感知流", {"C": P}, "常驻（分模态）· 小模型流式前向 · 确定性 ms 级"),
        ("个人语料索引", {"C": P, "E": O}, "数百–数千条/日 · 每条一次 encoder 前向 · 无延迟要求"),
        ("意图翻译", {"C": P, "P": O, "D-w": O, "KV-io": O}, "数十–数百次/日 · 音频 encoder + 短 LLM · 亚秒"),
        ("交互问答", {"E": O, "P": P, "D-w": P, "D-a": O, "Ctrl": O, "KV-io": O}, "数次–数十次/日 · 1K prefill + 数百 decode · 首 token < 1 s"),
        ("语音双工", {"C": P, "P": O, "D-w": P, "V": P, "KV-io": O}, "ASR + LLM + TTS 并发 · 轮转 < 200–300 ms（硬）"),
        ("前台 Agent", {"E": O, "P": P, "D-w": P, "D-a": P, "Ctrl": O, "KV-io": P}, "5–50 次/日 · N 轮 · ΔL 200–20K · 每轮秒级"),
        ("后台 Agent", {"E": O, "P": P, "D-w": O, "D-a": P, "Ctrl": O, "KV-io": P}, "数次/日 · 轮数更多 · 无延迟要求，预算让给能效"),
        ("生成媒体", {"G": P}, "数次/日 · 扩散 × 数十步 · 容忍十秒级"),
        ("端侧自适应", {"F": P}, "每日一次 · 充电窗口 ~6 h"),
    ]
    rows = [[name] + [m.get(col, "") for col in cols] + [mag] for name, m, mag in data]
    k.table(s, I(0.45), I(1.05), I(12.43), I(5.2), ["场景"] + cols + ["量级（2.4）"], rows,
            col_w=[1.4] + [0.55] * 10 + [4.6], s=10, first_col_bold=True, center_cols=tuple(range(1, 11)),
            hl_rows=(5, 6), hl_color=k.BAND)
    k.text(s, I(0.45), I(6.35), I(12.43), I(0.55), [
        _p("● 主导　○ 参与。Agent 两行（高亮）同时压在算力簇（P、D-a）与带宽簇（D-w）上——算力簇比直觉更重（4.4）；Ctrl-d 计算量约为该轮 prefill 的 1%，标为参与。", 10, k.MUTE)])
    k.notes(s, "矩阵由场景账本与能力清单推出；每个原语的具体负载见各自的原语页。")


def slide_4_4_6(prs):
    s = k.add_slide(prs, "4.4 / 4.5 / 4.6", "负载聚类 · P/D 两层矛盾 · 稳定性排序", source="v3.4 §4.4–4.6")
    k.table(s, I(0.45), I(1.05), I(7.3), I(2.75), ["簇", "原语", "共同特征", "设计目标"], [
        ["常开簇", "C + 哨兵", "高占空比、mW 预算", "能效即一切"],
        ["带宽簇", "D-w、V", "低算术强度、流式", "近存、宽接口、量化"],
        ["算力簇", "P + G + D-a + E-rerank", "高算术强度", "大 MAC 阵列、激活缓存"],
        ["存储底座", "E 索引 + F 工作集 + 归档记忆", "容量主导", "分层驻留"],
        ["CPU 串行", "Ctrl-d", "关键路径、标量", "低延迟核、不可被抢占"],
    ], col_w=[1.1, 2.2, 1.9, 2.1], s=10, first_col_bold=True, hl_rows=(2,), hl_color=k.BAND)
    k.text(s, I(0.45), I(3.85), I(7.3), I(0.4), [_p("D 拆开后 D-a 与 E-rerank 都进了算力簇：算力簇比直觉所设想的更重。", 10, k.MUTE)])
    k.box(s, I(7.95), I(1.05), I(4.93), I(1.4), [
        _p("第一层：资源利用率矛盾", 11, k.TEALDK, True),
        _p("单引擎服务两相位，decode 的 MAC 有活干但 MFU 仅 10–20%；「闲置 > 90%」只对短上下文成立。", 10)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.table(s, I(7.95), I(2.6), I(4.93), I(1.2), ["相位", "最优功率点", "预算流向"], [
        ["P", "大阵列、低频", "MAC 阵列"],
        ["D-w", "内存接口高频（DRAM 功耗随频率线性涨）", "内存接口"],
    ], col_w=[0.6, 2.8, 1.2], s=10)
    k.box(s, I(7.95), I(3.95), I(4.93), I(1.05), [
        _p("第二层：功率点争抢（比利用率更硬）→ 可交给设计团队的规格", 10.5, k.WHITE, True),
        _p("MAC 阵列与内存接口必须有独立电源域与独立 DVFS，按相位切换功率分配。", 10.5, k.WHITE)],
        fill=k.TEALDK, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.text(s, I(0.45), I(5.2), I(12.43), I(0.35), [_p("4.6 负载稳定性排序（按输出空间维度；越靠左越可硬化）", 11, k.TEALDK, True)])
    chain = ["C 类", "E-ANN", "G 类", "D-w", "D-a", "P 类", "Ctrl-d", "未来新范式"]
    for i, name in enumerate(chain):
        x = 0.45 + i * 1.56
        hot = name in ("D-a", "P 类")
        k.box(s, I(x), I(5.65), I(1.3), I(0.6), [_p(name, 11, k.RED if hot else k.INK, True)],
              fill=k.REDLT if hot else k.BAND, line=k.RED if hot else k.TEAL)
        if i < len(chain) - 1:
            k.text(s, I(x + 1.3), I(5.65), I(0.26), I(0.6), [_p(">", 14, k.MUTE, True)],
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(0.45), I(6.35), I(12.43), I(0.55), [
        _p("红框：D-a 与 P 类的稳定性低于直觉——注意力机制与 prefill 路径都在快速迭代（5.3）。", 10, k.RED)])
    k.notes(s, "聚类决定资源配置；独立 DVFS 是本文少数可直接交给设计团队的硬件规格。")


def build_sample(prs):
    slide_primitive(prs, spec_p())
    slide_primitive(prs, spec_dw())


def build(prs):
    slide_4_1(prs)
    slide_4_2_ridge(prs)
    slide_4_2_ops(prs)
    slide_baseline(prs)
    slide_overview(prs)
    slide_matrix(prs)
    for spec in (spec_c, spec_e, spec_p, spec_dw, spec_da, spec_v, spec_g, spec_f, spec_ctrl, spec_kvio):
        slide_primitive(prs, spec())
    slide_4_4_6(prs)

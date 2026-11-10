# -*- coding: utf-8 -*-
"""《端侧AI计算架构完整构想》v3.3 / v3.4 参数基线与派生数字（两版技术口径一致）。

md 与 PPT 中所有需计算的数字都从这里来；tests/test_calc.py 锁定取值。
单位：算力 op/s，带宽 B/s，能量 J，功率 W，时间 s。
"""

# ---- 基线参数（spec §3）----
F_PEAK = {'W8A8': 100e12, 'W4A8': 200e12}
MFU_PREFILL = 0.70
MFU_DECODE = (0.10, 0.20)
B_LPDDR6 = 113.8e9
B_UFS = {'UFS5': 10.8e9, 'UFS4': 4.0e9}
P_NPU = 4.0            # 满算力持续功耗
E_UFS = 0.5e-9         # UFS 系统级读能耗 J/B
E_LPDDR = 0.05e-9      # LPDDR 读能耗 J/B
P_ENV = 4.9            # 6.4.5 包络上沿（原文合计值）

# ---- 模型设定（沿用原文）----
N_MID, W_MID = 8e9, 4e9          # 8B INT4
N_BIG, W_BIG = 30e9, 15e9        # 30B dense INT4
LAYERS_BIG = 60
N_MOE_ACTIVE = 3e9               # 30B-A3B
MOE_E, MOE_K = 128, 8


def f_eff(prec='W4A8', mfu=MFU_PREFILL):
    return F_PEAK[prec] * mfu


def t_tok(n, f):
    """dense 前向每 token 时间：2·N / F。"""
    return 2 * n / f


def break_even(w, b, n, f, c=0.0):
    """流式平衡点 ΔL* = (W − C) / (B · t_tok)。"""
    return (w - c) / (b * t_tok(n, f))


def ratio_bw(f, chunk):
    """配比公式所需 UFS 带宽 B ≥ F / (4·L_c)（INT4 dense）。"""
    return f / (4 * chunk)


def ridge(f, b=B_LPDDR6):
    return f / b


def e_op(prec='W4A8'):
    """满算力持续 4 W 下的每 op 能耗 J/op。"""
    return P_NPU / f_eff(prec)


def e_comp_tok(n, prec='W4A8'):
    return 2 * n * e_op(prec)


def e_move_tok(w, dl, e_b=E_UFS, c=0.0):
    return (w - c) * e_b / dl


def energy_break_even(w, n, e_b=E_UFS, prec='W4A8'):
    """搬运能耗 = 计算能耗 时的 ΔL。"""
    return w * e_b / e_comp_tok(n, prec)


def p_ufs_hide(w, dl, n, f, e_b=E_UFS):
    """流式完全藏在计算下时的 UFS 功率 W·e / (ΔL·t_tok)。"""
    return w * e_b / (dl * t_tok(n, f))


def t_round_thermal(w, dl, n, prec='W4A8', p_env=P_ENV, e_b=E_UFS, c=0.0):
    """热约束下每轮最短时间 E_round / P_env。"""
    return ((w - c) * e_b + dl * e_comp_tok(n, prec)) / p_env


def t_round_free(w, b, dl, n, f):
    return max(w / b, dl * t_tok(n, f))


def expert_untouched(dl, e=MOE_E, k=MOE_K):
    return (1 - k / e) ** dl


def decode_tok_s(w, b=B_LPDDR6):
    return b / w


# ================= 2029 负载基线（v3.3 第 4.3 节；2026-09-11 与用户对齐）=================
# 决策：常驻 8B @2-bit；KV 取分支 C（CSA2 + FP4 890 B/token + 稀疏 top-k）；语音原生全双工；统一 encoder 300M。
FUT = dict(
    w_resident=2e9,                  # 常驻 8B @2-bit
    kv_bytes_tok=890,                # DeepSeek-V4.1-Flash 全局 KV
    topk=2048, idx_bytes_tok=128,    # 稀疏注意力 top-k 与 indexer K（假设）
    ctx=100_000,                     # agent 上下文（原文 6.3.1）
    enc_params=300e6, enc_bytes=300e6,       # 统一 encoder 300M，INT8
    vit_tokens=196, audio_hz=6.25, audio_tok_per_chunk=8, query_tokens=32,
    speech_hz=12.5,                  # 语音原生帧率（Moshi / Hibiki：12.5 Hz）
    sentinel_w=0.5e-3,               # 哨兵常开（NDP120 SWW 0.51 mW）
    battery_j=5000e-3 * 3.85 * 3600,
    cpu_w=1.0,                       # Ctrl-d 所在 CPU 核功率（假设）
    g_image_j=40.0, g_video_j=20.0,  # 扩散：162 J/张（SD1.5 实测）× 少步约 1/4；视频 5 W × 4 s（假设）
)
DAY = dict(fg_tasks=20, fg_rounds=20, bg_tasks=5, bg_rounds=50, dl=3000, k=300, qa=30, qa_prefill=1000,
           voice_sessions=10, voice_min=3, cam_hours=2.4, vis_fps=1, audio_hours=1, items=2000,
           item_tokens=256, queries=1000, images=5, videos=2)


def day_rounds():
    return DAY['fg_tasks'] * DAY['fg_rounds'] + DAY['bg_tasks'] * DAY['bg_rounds']


def day_prefill_tokens():
    return day_rounds() * DAY['dl'] + DAY['qa'] * DAY['qa_prefill']


def day_decode_tokens():
    return (day_rounds() + DAY['qa']) * DAY['k']


def kv_read_step(ctx=None):
    """稀疏 decode 每步读 KV：top-k 个 token 的主 KV + 全部 token 的 indexer K。"""
    ctx = ctx or FUT['ctx']
    return FUT['topk'] * FUT['kv_bytes_tok'] + ctx * FUT['idx_bytes_tok']


def decode_tok_s_future():
    return B_LPDDR6 / (FUT['w_resident'] + kv_read_step())


def e_decode_tok_future():
    return (FUT['w_resident'] + kv_read_step()) * E_LPDDR


def e_prefill_tok_future():
    return e_comp_tok(N_MID) + FUT['w_resident'] * E_LPDDR / DAY['dl']


def voice_bw():
    return FUT['w_resident'] * FUT['speech_hz']


def voice_frame_ms():
    return FUT['w_resident'] / B_LPDDR6 * 1e3


def _enc(tokens):
    flop = 2 * FUT['enc_params'] * tokens
    return flop / FUT['enc_bytes'], FUT['enc_bytes'] * E_LPDDR + flop * e_op('W8A8')


def enc_vision_frame():
    """返回（算术强度 ops/B，每帧能耗 J）：每帧重读 300 MB 权重。"""
    return _enc(FUT['vit_tokens'])


def enc_audio_chunk():
    return _enc(FUT['audio_tok_per_chunk'])


def index_bytes_5y():
    items = DAY['items'] * 365 * 5
    return items * 768, items * 200 * 36          # 单向量 768 维 int8；ColBERTv2 2-bit（36 B/token，200 token/条）


def lora_flop(n=N_MID, tokens=1000 * 256):
    return 6 * n * tokens


def lora_minutes(mfu_train=0.3):
    return lora_flop() / (f_eff('W8A8', 1.0) * 0.7 * mfu_train) / 60


def ctrl_round(tokens=20_000, bytes_tok=4, json_bps=2.39e9, tok_bps=3.66e6):
    b = tokens * bytes_tok
    return b / json_bps * 1e3, b / tok_bps * 1e3, tokens * t_tok(N_MID, f_eff('W4A8'))


def full_adam_bytes(n):
    return 16 * n                                  # 混合精度 Adam：权重 + 梯度 + 优化器状态


def day_energy():
    e8 = e_op('W8A8')
    _, ev = enc_vision_frame(); _, ea = enc_audio_chunk()
    c_day = (ev * DAY['vis_fps'] * DAY['cam_hours'] * 3600
             + ea * FUT['audio_hz'] * DAY['audio_hours'] * 3600
             + FUT['sentinel_w'] * 86400
             + DAY['items'] * _enc(DAY['item_tokens'])[1])
    q_enc = _enc(FUT['query_tokens'])[1]
    ann = 6e6 * E_UFS                               # IVF 分区从 flash 读约 6 MB
    ce = 7.27e12 * e8 + 0.3e9 * E_LPDDR             # bge-reranker-v2-m3，50 候选（按非嵌入参数）
    li = 61e6 * e8 + 50 * 7200 * E_UFS              # late interaction：只算 MaxSim（查询编码已计入 q_enc）+ 读候选 token 矩阵
    ctrl = sum(ctrl_round()[:2]) / 1e3 * FUT['cpu_w'] * day_rounds()
    return {
        'P': day_prefill_tokens() * e_prefill_tok_future(),
        'D-w': day_decode_tokens() * e_decode_tok_future(),
        'V': voice_bw() * E_LPDDR * DAY['voice_sessions'] * DAY['voice_min'] * 60,
        'C': c_day,
        'E': DAY['queries'] * (q_enc + ann + li),
        'E_ce': DAY['queries'] * (q_enc + ann + ce),
        'G': DAY['images'] * FUT['g_image_j'] + DAY['videos'] * FUT['g_video_j'],
        'F': lora_flop() * e8 + 1000 * 3 * FUT['w_resident'] * E_LPDDR,
        'Ctrl': ctrl,
    }


def day_battery_share():
    d = day_energy()
    return sum(v for key, v in d.items() if key not in ('F', 'E_ce')) / FUT['battery_j']


def lora_energy_range():
    """F 类夜间 LoRA 能耗区间（v3.4）：下限 = W4A8 每 op 能耗纯计算；上限 = W8A8 计算 + 权重重读。"""
    lo = lora_flop() * e_op('W4A8')
    hi = lora_flop() * e_op('W8A8') + 1000 * 3 * FUT['w_resident'] * E_LPDDR
    return lo, hi


def bridge_latency(ctx=100e3, d=4096, layers=32, topk=None):
    """5.2.2 桥 vs 本地时延（s）：桥 89 MB @ 50 Mbps；本地 8B 线性项 2·N·ΔL 按 W4A8，注意力按 W8A8。

    注意力 FLOP：dense（因果）≈ 2·L²·d·n_layers；稀疏 top-k ≈ 4·L·k·d·n_layers。
    返回 (桥, 本地线性项, 本地 + 稀疏注意力, 本地 + dense 注意力)。
    """
    k = FUT['topk'] if topk is None else topk
    t_bridge = 890 * ctx * 8 / 50e6
    t_lin = 2 * N_MID * ctx / f_eff('W4A8')
    a_sparse = 4 * ctx * k * d * layers
    a_dense = 2 * ctx ** 2 * d * layers
    return t_bridge, t_lin, t_lin + a_sparse / f_eff('W8A8'), t_lin + a_dense / f_eff('W8A8')

# -*- coding: utf-8 -*-
"""PC 形态：HBF 流式 MoE prefill + 3D-PIM decode + KV 映射桥。参数与派生数字。

负载与参数均为 2026-10 与用户对齐的取值；tests/test_pc.py 锁定。
单位：算力 op/s，带宽 B/s，能量 J，功率 W，时间 s。
"""
import calc as c

# ---- 负载（用户给定）----
P = dict(
    n_total=200e9, n_active=20e9,        # 200B-A20B MoE，prefill
    w_moe=100e9,                         # 专家 FP4：200B × 0.5 B
    layers=60, experts=128, topk=8,      # 层数与路由（假设）
    hidden=7168,                         # 隐藏维度（假设，用于 MoE 分发流量）
    n_dec=4e9, w_dec=2e9,                # 4B dense，4-bit
    bridge_recover=0.5,                  # KV 映射补回大小模型能力差距的比例（用户假设）
)
# ---- 硬件（用户给定）----
H = dict(
    f_peak=200e12, mfu=0.70,             # NPU 200 TOPS @W4A8
    b_dram=153e9, e_dram=c.E_LPDDR,      # 系统 DRAM
    e_hbf=c.E_UFS,                       # HBF 读能耗参考 UFS：0.5 nJ/B
    b_pim=1e12, cap_pim=4e9,             # 3D-PIM：1 TB/s、4 GB
    e_pim_pj=(0.5, 1.0),                 # 3D-PIM 片内 pJ/bit
    e_off_pj=c.E_LPDDR * 1e12 / 8,       # 片外 LPDDR 6.25 pJ/bit（对照）
    battery_j=(70 * 3600, 100 * 3600),   # 笔记本电池 70–100 Wh
)
GEARS = (30e9, 60e9, 117e9)              # HBF 带宽档：电池 / 中间 / 插电
DL_CHAT, DL_AGENT = 350, 3000            # 每轮增量：上一轮 decode 300 + 用户输入 ~50；agent 均值 3K


def f_eff():
    return H['f_peak'] * H['mfu']


def e_op():
    return c.P_NPU / f_eff()


def e_comp_tok():
    """200B-A20B prefill 每 token 计算能耗：2·N_active·e_op。"""
    return 2 * P['n_active'] * e_op()


def tok_rate():
    """prefill 吞吐 token/s：F_eff ÷ (2·N_active)。"""
    return f_eff() / (2 * P['n_active'])


def t_prefill(dl):
    return dl / tok_rate()


def intensity_dram(dl, pingpong=True):
    """对 DRAM 的算术强度 ops/B：两层 ping-pong 放 DRAM 时分母含写入 + 读出全部权重。"""
    traffic = (2 * P['w_moe'] if pingpong else 0) + dispatch_bytes_tok() * dl
    return 2 * P['n_active'] * dl / traffic


def ridge_dram():
    return f_eff() / H['b_dram']


def dispatch_bytes_tok():
    """MoE 分发激活（INT8）每 token 的 DRAM 流量：进 + 出 × top-k × hidden × 层数。"""
    return 2 * P['topk'] * P['hidden'] * P['layers']


def dram_bw_need(dl, pingpong=True):
    """prefill 期间不拖慢计算所需的 DRAM 带宽。"""
    traffic = (2 * P['w_moe'] if pingpong else 0) + dispatch_bytes_tok() * dl
    return traffic / t_prefill(dl)


def dl_dram_bound(pingpong=True):
    """两层 ping-pong 放 DRAM 时，ΔL 低于此值为 DRAM 带宽受限。"""
    if not pingpong:
        return 0.0
    per_tok = 1 / tok_rate() - dispatch_bytes_tok() / H['b_dram']
    return 2 * P['w_moe'] / H['b_dram'] / per_tok


def layer_bytes():
    return P['w_moe'] / P['layers']


def expert_bytes():
    return layer_bytes() / P['experts']


def coverage(dl, experts=None, k=None):
    """均匀路由下一轮里被选中的专家比例：1 − (1 − k/E)^ΔL。"""
    experts = experts or P['experts']; k = k or P['topk']
    return 1 - (1 - k / experts) ** dl


def stream_time(b, cover=1.0, resident=0.0):
    return (cover * P['w_moe'] - resident) / b


def dl_hide(b):
    """HBF 流式被计算藏住的最小 ΔL：W·F ÷ (2·N_active·B)。"""
    return P['w_moe'] * f_eff() / (2 * P['n_active'] * b)


def burst_power(b):
    return b * H['e_hbf']


def e_hbf_max(b, p_cap):
    """瞬时功率封顶 p_cap 时允许的 HBF 读能耗 J/B。"""
    return p_cap / b


def t_round_prefill(dl, b, cover=1.0):
    return max(stream_time(b, cover), t_prefill(dl))


def e_round(dl, cover=1.0, pingpong=False, resident=0.0):
    """一轮 prefill 能耗：HBF 流式 + （可选）DRAM ping-pong 往返 + 计算 + 常驻部分的 DRAM 读。"""
    stream = (cover * P['w_moe'] - resident) * H['e_hbf']
    pp = 2 * P['w_moe'] * H['e_dram'] if pingpong else 0.0
    return stream + pp + resident * H['e_dram'] + dl * e_comp_tok()


def pim_kv_step():
    return c.kv_read_step()


def pim_tok_s():
    return H['b_pim'] / (P['w_dec'] + pim_kv_step())


def pim_e_tok(pj):
    return P['w_dec'] * 8 * pj * 1e-12


def off_e_tok():
    return P['w_dec'] * c.E_LPDDR


def pim_kv_room():
    return H['cap_pim'] - P['w_dec']


def pim_contexts(ctx=100_000):
    return pim_kv_room() / (ctx * c.FUT['kv_bytes_tok'])


def map_bytes_round(dl):
    """每轮映射写进 PIM 的 KV（4B 侧压缩格式）。"""
    return dl * c.FUT['kv_bytes_tok']


def day_rounds():
    return c.day_rounds() + c.DAY['qa']


def day_prefill_tokens():
    return c.day_prefill_tokens()


def day_decode_tokens():
    return c.day_decode_tokens()


def day_energy(pj=0.5, pingpong=False, e_hbf=None):
    """重度使用日：prefill 全走 200B（每轮流一次全部权重），decode 全在 PIM。"""
    e_hbf = H['e_hbf'] if e_hbf is None else e_hbf
    pre = day_rounds() * P['w_moe'] * e_hbf + day_prefill_tokens() * e_comp_tok()
    if pingpong:
        pre += day_rounds() * 2 * P['w_moe'] * H['e_dram']
    dec = day_decode_tokens() * pim_e_tok(pj)
    return {'prefill': pre, 'decode': dec, 'total': pre + dec}


def battery_share(e):
    lo, hi = H['battery_j']
    return e / hi, e / lo


def ttft(b, resident=0.0):
    """首 token 前的流式下限（chat 轮次：计算 0.1 s 量级，流式主导）。"""
    return max((P['w_moe'] - resident) / b, t_prefill(DL_CHAT))


# ================= 成本核算（2026-10；来源见 sources/pc-cost-*.md）=================
# 口径：AI 子系统增量制造成本（硅 + 颗粒 + 封装测试），不含 NRE、不含芯片厂毛利。
# 周期：N = 正常周期（DRAM $2–3/GB、NAND TLC $0.04–0.08/GB）；H = 2026 高位（DRAM 约 $15/GB、NAND $0.23–0.34/GB）。
CNY = 7.1                                    # 1 USD ≈ 7.1 CNY
SCN = ('乐观', '基准', '悲观')
COST = dict(
    npu_area=(35, 46, 74), npu_usd=(14.7, 25.3, 52.6),           # NPU 200 TOPS + 64 MiB SRAM，N3 边际（LP §7.1）
    pim_n=(19.1, 49.1, 118.7), pim_h=(75.0, 158.9, 344.1),             # 4 GB 3D-PIM，1 层 W2W（LP §7.2）
    nand_n=(0.04, 0.06, 0.08), nand_h=(0.227, 0.28, 0.344),  # TLC $/GB（CN §1；PM-S7/S11/S14）
    dram_n=(2.0, 2.5, 3.0), dram_h=(12, 20, 28),           # 系统 DRAM $/GB（LP §6；PM 推荐取值）
    hbf_usd_gb=(1.0, 2.5, 4.5),                            # 真 HBF（HBM $/GB ÷ 8–16，PM-S27~S30）
    ctrl_usd=(5, 10, 20),                                  # PCIe 6.0 主控相对 5.0 的溢价（估算，无公开价）
    small_die_premium=(0.30, 0.40, 0.52),                  # 正常周期：512 Gb die 每 GB 溢价 = 1 Tb 价 × 比例（TrendForce 1.30× / CFM 1.52×）
    small_die_delta_h=(0.067, 0.092, 0.117),              # 2026：512 Gb 与 1 Tb 的每 GB 价差（0.294 / 0.344 − 0.227，PM-S7/S11）
)
# 定制高带宽闪存方案（CN §7.1–7.3；成本为 $，(乐观, 基准, 悲观)）
FLASH = {
    'base': dict(name='0 基线：1 Tb TLC 堆 die', bw_die='1.6–1.9', d30='17–19 颗', cap30='2.2–2.4 TB',
                 c30_n=(119, 196, 291), c30_h=(525, 703, 933), d117='63–72 颗', cap117='8.1–9.2 TB',
                 c117_n=(413, 682, 1014), c117_h=(1921, 2568, 3447), nj=(0.42, 0.55, 0.70), p30=16.5, p117=64),
    'A2': dict(name='A2：512 Gb TLC 当 pSLC', bw_die='3.0–4.3', d30='7–10 颗', cap30='149–213 GB',
               c30_n=(34, 66, 160), c30_h=(118, 207, 413), d117='28–39 颗', cap117='597–832 GB',
               c117_n=(129, 249, 511), c117_h=(464, 777, 1499), nj=(0.30, 0.40, 0.55), p30=12, p117=47),
    'B': dict(name='B：定制 256 Gb SLC、16 plane、双端口', bw_die='6.5–10.1', d30='4–5 颗', cap30='128–160 GB',
              c30_n=(35, 69, 191), c30_h=(130, 234, 571), d117='12–19 颗', cap117='384–608 GB',
              c117_n=(110, 246, 619), c117_h=(394, 823, 2064), nj=(0.25, 0.33, 0.45), p30=9.9, p117=38.6),
    'C': dict(name='C-full：HBF 级 die 4 层堆叠 + base die + UCIe', bw_die='≈100', d30='4 层堆叠', cap30='128 GB',
              c30_n=(45, 119, 308), c30_h=(180, 427, 1091), d117='4 层（同左）', cap117='128 GB',
              c117_n=(45, 119, 308), c117_h=(180, 427, 1091), nj=(0.05, 0.08, 0.12), p30=2.4, p117=9.4),
}
SHARED_NJ = (0.49, 0.70)                                   # 客户端 PCIe 5.0 SSD 盘级实测（NB-S10 等）
SHARED_BW = 28e9                                           # 1 块 PCIe 6.0 x4 主盘


def cny(usd):
    return usd * CNY


def yuan(usd):
    """人民币取整（四舍五入到元）。"""
    return int(usd * CNY + 0.5)


def _cyc(key, cycle):
    return COST[f'{key}_{cycle}']


def cost_resident_dram(cycle='n'):
    """对照：200B 常驻 DRAM 需多配 128 GB。"""
    return tuple(128 * u for u in _cyc('dram', cycle))


def cost_hbf_stack():
    """对照：真 HBF 最小一堆 512 GB（16 × 256 Gb）。"""
    return tuple(512 * u for u in COST['hbf_usd_gb'])


def cost_flash_shared2tb():
    """系统主盘本来就是 2 TB：只多 PCIe 6.0 主控溢价。"""
    return COST['ctrl_usd']


def cost_flash_small_die(cycle='n'):
    """系统主盘原本 1 TB：改用 16 颗 512 Gb 小 die 的 1 TB PCIe 6.0 盘。溢价相对 1 Tb die 计。"""
    if cycle == 'n':
        delta = tuple(pr * u for pr, u in zip(COST['small_die_premium'], COST['nand_n']))
    else:
        delta = COST['small_die_delta_h']
    return tuple(d * 1000 + c_ for d, c_ in zip(delta, COST['ctrl_usd']))


def cost_flash(option, cycle='n', gear=30):
    return FLASH[option][f'c{gear}_{cycle}']


def cost_total(flash, cycle='n'):
    return tuple(n + f + q for n, f, q in zip(COST['npu_usd'], flash, _cyc('pim', cycle)))


def day_energy_nj(nj, pj=0.5):
    return day_energy(pj, e_hbf=nj * 1e-9)


# ================= 对照方案：200B 全部常驻内存（汇报版用）=================
def resident_w_active():
    """200B-A20B 每生成一个 token 要读的激活专家权重（FP4）。"""
    return P['n_active'] * 0.5


def resident_decode_tok_s():
    return H['b_dram'] / (resident_w_active() + pim_kv_step())


def resident_e_tok():
    return resident_w_active() * H['e_dram']


def resident_ttft(dl):
    """权重常驻内存时，prefill 仍要把全部专家从内存读一遍。"""
    return max(P['w_moe'] / H['b_dram'], t_prefill(dl))


def resident_day_energy():
    pre = day_rounds() * P['w_moe'] * H['e_dram'] + day_prefill_tokens() * e_comp_tok()
    dec = day_decode_tokens() * resident_e_tok()
    return {'prefill': pre, 'decode': dec, 'total': pre + dec}


def cost_resident_total(cycle='n'):
    """全放内存方案的增量：同样的 NPU + 多配 128 GB 内存。"""
    return tuple(n + d for n, d in zip(COST['npu_usd'], cost_resident_dram(cycle)))


def round_energy(dl, nj=0.5, pj=0.5, k_dec=300):
    """一轮的能耗分解：读权重（闪存）/ 200B 计算 / 4B 生成。"""
    return {'stream': P['w_moe'] * nj * 1e-9, 'compute': dl * e_comp_tok(), 'decode': k_dec * pim_e_tok(pj)}


# ================= 汇报版：三种自洽配置 =================
KV_FP16_4B = 147e3                       # 4B 未压缩 KV（Qwen3-4B FP16，v3.4 §4.3 KV-io，R4-S27）
CTX_LONG = 100_000                       # 「长对话」= 10 万 token
CONFIGS = {
    'shared': dict(name='复用主硬盘', desc='PC 自带 2 TB PCIe 6.0 硬盘', bw=(SHARED_BW,), nj=SHARED_NJ,
                   avail='PCIe 6.0 客户端硬盘约 2028 年后'),
    'A2': dict(name='改造型闪存', desc='现成芯片按单比特模式使用 + 定制控制器', bw=(30e9,), nj=(0.40, 0.40),
               avail='无需新闪存芯片，需开发定制控制器'),
    'C': dict(name='堆叠型闪存', desc='HBF 级芯片 4 层堆叠', bw=(30e9, 117e9), nj=(0.08, 0.08),
              avail='取决于 HBF 级芯片端侧供货（数据中心样品 2027 年）'),
}


def kv_long_fp16():
    return KV_FP16_4B * CTX_LONG


def cfg_cost(key, cycle='n'):
    f = cost_flash_shared2tb() if key == 'shared' else cost_flash(key, cycle)
    return cost_total(f, cycle)


def cfg_ttft(key, dl=None):
    """各配置的首字等待（聊天轮次）；堆叠型返回电池 / 插电两档。"""
    dl = DL_CHAT if dl is None else dl
    return tuple(t_round_prefill(dl, b) for b in CONFIGS[key]['bw'])


def cfg_day(key):
    """一天耗电区间：低 = 读能耗下限 + PIM 0.5 pJ/bit；高 = 读能耗上限 + PIM 1 pJ/bit。"""
    lo, hi = CONFIGS[key]['nj']
    return day_energy(0.5, e_hbf=lo * 1e-9)['total'], day_energy(1.0, e_hbf=hi * 1e-9)['total']


def storage_share(key, cycle='n'):
    """3D-PIM 与闪存两项存储器件占增量成本的比例（基准）。"""
    f = cost_flash_shared2tb() if key == 'shared' else cost_flash(key, cycle)
    pim = _cyc('pim', cycle)
    return (pim[1] + f[1]) / cost_total(f, cycle)[1]

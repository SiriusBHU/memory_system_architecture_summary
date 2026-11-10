import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import calc as c
from pytest import approx

F4 = c.f_eff('W4A8'); F8 = c.f_eff('W8A8')


def test_effective_compute():
    assert F4 == approx(140e12) and F8 == approx(70e12)


def test_ridges():  # 4.2
    assert c.ridge(c.F_PEAK['W4A8']) == approx(1757, abs=1)
    assert c.ridge(c.F_PEAK['W8A8']) == approx(879, abs=1)
    assert c.ridge(F8) == approx(615, abs=1) and c.ridge(F4) == approx(1230, abs=1)
    assert [round(c.ridge(c.F_PEAK['W8A8'] * m)) for m in c.MFU_DECODE] == [88, 176]
    assert [round(c.ridge(c.F_PEAK['W4A8'] * m)) for m in c.MFU_DECODE] == [176, 351]


def test_time_ledger():  # 2.4.1
    assert 4000 * c.t_tok(c.N_MID, F4) == approx(0.457, abs=1e-3)
    assert 300 / c.decode_tok_s(c.W_MID) == approx(10.54, abs=0.01)


def test_bridge_flip():  # 5.2.2：本地 < 桥 14 s
    assert 1.6e15 / F4 == approx(11.43, abs=0.01)


def test_ratio_formula():  # 6.4.1
    assert [round(c.ratio_bw(F4, L) / 1e9, 2) for L in (4096, 8192, 16384)] == [8.54, 4.27, 2.14]
    assert [round(c.ratio_bw(1e12, L) / 1e6, 1) for L in (4096, 8192, 16384)] == [61.0, 30.5, 15.3]


def test_break_even():  # 6.4.2
    assert c.t_tok(c.N_BIG, F4) * 1e3 == approx(0.4286, abs=1e-4)
    assert c.W_BIG / c.B_UFS['UFS5'] == approx(1.389, abs=1e-3)
    assert c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_BIG, F4) == approx(3241, abs=1)
    assert c.break_even(c.W_BIG, c.B_UFS['UFS4'], c.N_BIG, F4) == approx(8750, abs=1)


def test_dynamic_residency():  # 6.4.2.1
    got = [round(c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_BIG, F4, C)) for C in (0, 1.5e9, 3e9, 5e9)]
    assert got == [3241, 2917, 2593, 2160]


def test_moe():  # 6.4.2.2
    assert c.expert_untouched(100) == approx(0.00157, abs=1e-5)
    assert c.break_even(c.W_BIG, c.B_UFS['UFS5'], c.N_MOE_ACTIVE, F4) == approx(32407, abs=1)


def test_energy():  # 6.4.4 + 第七章结论一
    assert c.e_op('W4A8') * 1e12 == approx(0.0286, abs=1e-4)
    assert c.e_comp_tok(c.N_BIG) * 1e3 == approx(1.714, abs=1e-3)
    assert c.e_move_tok(c.W_BIG, 3240) * 1e3 == approx(2.315, abs=1e-3)
    assert c.e_move_tok(c.W_BIG, 10000) * 1e3 == approx(0.75, abs=1e-3)
    assert c.energy_break_even(c.W_BIG, c.N_BIG) == approx(4375, abs=1)
    comp = c.e_comp_tok(c.N_MID); move = c.e_move_tok(c.W_MID, 4096, c.E_LPDDR)
    assert comp * 1e3 == approx(0.457, abs=1e-3) and move * 1e3 == approx(0.0488, abs=1e-4)
    assert comp / move == approx(9.36, abs=0.01)


def test_thermal():  # 6.4.5
    assert c.p_ufs_hide(c.W_BIG, 4096, c.N_BIG, F4) == approx(4.27, abs=0.01)
    assert c.t_round_thermal(c.W_BIG, 3240, c.N_BIG) == approx(2.66, abs=0.01)
    assert c.t_round_thermal(c.W_BIG, 10000, c.N_BIG) == approx(5.03, abs=0.01)
    assert c.t_round_free(c.W_BIG, c.B_UFS['UFS5'], 10000, c.N_BIG, F4) == approx(4.29, abs=0.01)


def test_routing():  # 6.7
    wrong = c.W_BIG / c.B_UFS['UFS5']; right = 200 * c.t_tok(c.N_MID, F4)
    assert right == approx(0.0229, abs=1e-4) and wrong / right == approx(60.8, abs=0.1)


def test_unchanged_tables():  # 5.3.1、4.3 E、6.3.1 D-a 不变
    assert [round(c.decode_tok_s(w)) for w in (4e9, 2e9, 1e9)] == [28, 57, 114]
    assert 50 * 200 * 2 * 300e6 == approx(6e12)
    assert [round(2 * 576 * 60 * L / 16e9 * 100) for L in (1e4, 1e5, 1e6)] == [4, 43, 432]


# ---------------- 2029 负载基线（v3.3 4.3，2026-09-11 与用户对齐）----------------
def test_future_day_tokens():
    assert c.day_prefill_tokens() == 1_980_000
    assert c.day_decode_tokens() == 204_000


def test_future_decode():
    assert c.kv_read_step() == approx(14.62e6, rel=1e-3)          # top-k 2048×890 B + 100K×128 B
    assert c.decode_tok_s_future() == approx(56.5, abs=0.1)
    assert c.e_decode_tok_future() == approx(0.1007, abs=1e-4)
    assert c.day_energy()['D-w'] / 1e3 == approx(20.55, abs=0.01)
    assert c.day_energy()['D-w'] / c.FUT['battery_j'] == approx(0.2965, abs=1e-3)


def test_future_prefill_and_voice():
    assert c.day_energy()['P'] / 1e3 == approx(0.97, abs=0.01)
    assert c.voice_bw() / 1e9 == approx(25.0) and c.voice_bw() / c.B_LPDDR6 == approx(0.2197, abs=1e-3)
    assert c.voice_bw() * c.E_LPDDR == approx(1.25)
    assert c.voice_frame_ms() == approx(17.57, abs=0.01)
    assert c.day_energy()['V'] / 1e3 == approx(2.25, abs=0.01)


def test_future_encoder():
    ai_v, e_v = c.enc_vision_frame()
    ai_a, e_a = c.enc_audio_chunk()
    assert ai_v == approx(392) and e_v * 1e3 == approx(21.72, abs=0.01)
    assert ai_a == approx(16) and e_a * 1e3 == approx(15.27, abs=0.01)
    assert e_v * c.DAY['vis_fps'] * 1e3 == approx(21.7, abs=0.1)          # 视觉活跃期平均 mW
    assert e_a * c.FUT['audio_hz'] * 1e3 == approx(95.5, abs=0.1)         # 音频活跃期平均 mW
    assert c.day_energy()['C'] / 1e3 == approx(0.62, abs=0.01)


def test_future_retrieval_index():
    dense, colbert = c.index_bytes_5y()
    assert dense / 1e9 == approx(2.80, abs=0.01) and colbert / 1e9 == approx(26.3, abs=0.1)
    assert colbert / dense == approx(9.4, abs=0.1)
    assert c.day_energy()['E'] == approx(19.28, abs=0.01)        # late interaction 基线
    assert c.day_energy()['E_ce'] == approx(449.5, abs=0.1)      # cross-encoder 兜底


def test_future_lora_ctrl():
    assert c.lora_flop() == approx(1.2288e16)
    assert c.lora_minutes() == approx(9.75, abs=0.01)
    parse_ms, tok_ms, prefill_s = c.ctrl_round()
    assert parse_ms == approx(0.0335, abs=1e-3) and tok_ms == approx(21.9, abs=0.1) and prefill_s == approx(2.29, abs=0.01)
    assert c.full_adam_bytes(8e9) / 1e9 == approx(128)


def test_future_day_total():
    d = c.day_energy()
    assert d['F'] / 1e3 == approx(1.0, abs=0.01)                          # 充电中，不计电池
    assert d['G'] == approx(240.0) and d['Ctrl'] == approx(14.2, abs=0.1)
    assert c.day_battery_share() == approx(0.356, abs=1e-3)


def test_lora_energy_range():  # v3.4 F 类
    lo, hi = c.lora_energy_range()
    assert lo / 1e3 == approx(0.351, abs=1e-3) and hi / 1e3 == approx(1.002, abs=1e-3)
    assert c.lora_flop() * c.e_op('W8A8') / 1e3 == approx(0.702, abs=1e-3)


def test_bridge_latency():
    tb, tl, ts, td = c.bridge_latency()
    assert round(tb) == 14 and round(tl, 1) == 11.4
    assert round(ts, 1) == 13.0 and round(td) == 49
    assert tl < ts < tb < td

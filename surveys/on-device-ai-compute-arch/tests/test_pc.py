import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import calc_pc as p


def test_prefill_rate_and_time():
    assert round(p.tok_rate()) == 3500
    assert round(p.t_prefill(3000), 2) == 0.86 and round(p.t_prefill(20000), 2) == 5.71


def test_dram_pingpong_vs_direct():
    assert round(p.dram_bw_need(3000) / 1e9) == 257
    assert round(p.dram_bw_need(3000, pingpong=False) / 1e9) == 24
    assert round(p.dl_dram_bound() / 1e3, 1) == 5.4
    assert round(p.ridge_dram()) == 915


def test_coverage():
    assert round(p.coverage(20), 3) == 0.725 and round(p.coverage(50), 2) == 0.96
    assert round(p.coverage(100), 3) == 0.998
    assert round(p.coverage(50, experts=256), 3) == 0.796


def test_hbf_gears():
    assert [round(p.stream_time(b), 2) for b in p.GEARS] == [3.33, 1.67, 0.85]
    assert [round(p.burst_power(b)) for b in p.GEARS] == [15, 30, 59]
    assert round(p.dl_hide(30e9) / 1e3, 1) == 11.7 and round(p.dl_hide(117e9)) == 2991
    assert round(p.e_hbf_max(117e9, 5) * 1e9, 3) == 0.043


def test_round_energy():
    assert round(p.e_round(3000), 1) == 53.4 and round(p.e_round(3000, pingpong=True), 1) == 63.4
    assert round(p.e_comp_tok() * 1e3, 2) == 1.14
    assert round(p.expert_bytes() / 1e6) == 13


def test_pim():
    assert round(p.pim_tok_s()) == 496
    assert round(p.pim_e_tok(0.5) * 1e3) == 8 and round(p.off_e_tok() * 1e3) == 100
    assert round(p.pim_contexts()) == 22


def test_day():
    d = p.day_energy(0.5)
    assert round(d['prefill'] / 1e3, 1) == 36.3 and round(d['decode'] / 1e3, 1) == 1.6
    lo, hi = p.battery_share(d['total'])
    assert round(lo, 3) == 0.105 and round(hi, 3) == 0.150


def test_cost_model():
    Y = lambda t: [p.yuan(x) for x in t]
    assert Y(p.COST['npu_usd']) == [104, 180, 373]
    assert Y(p.COST['pim_n']) == [136, 349, 843] and Y(p.COST['pim_h']) == [533, 1128, 2443]
    tot = lambda f, c: Y(p.cost_total(f, c))
    assert tot(p.cost_flash_shared2tb(), 'n') == [275, 599, 1358] and tot(p.cost_flash_shared2tb(), 'h')[1] == 1379
    assert tot(p.cost_flash_small_die('n'), 'n') == [361, 770, 1654] and tot(p.cost_flash_small_die('h'), 'h')[1] == 2032
    assert tot(p.cost_flash('A2', 'n'), 'n') == [481, 997, 2352] and tot(p.cost_flash('A2', 'h'), 'h')[1] == 2778
    assert tot(p.cost_flash('C', 'n'), 'n') == [559, 1373, 3403] and tot(p.cost_flash('C', 'h'), 'h')[1] == 4340
    assert Y(p.cost_resident_dram('n')) == [1818, 2272, 2726] and Y(p.cost_resident_dram('h'))[1] == 18176
    assert [p.yuan(p.FLASH[k]['c30_n'][1]) for k in ('base', 'A2', 'B', 'C')] == [1392, 469, 490, 845]


def test_cost_ratios_and_energy():
    rn, rh = p.cost_resident_dram('n')[1], p.cost_resident_dram('h')[1]
    flashes = (p.cost_flash_shared2tb(), p.cost_flash_small_die('n'), p.cost_flash('A2', 'n'), p.cost_flash('C', 'n'))
    base_n = [p.cost_total(f, 'n')[1] for f in flashes]
    base_h = [p.cost_total(f, 'h')[1] for f in (p.cost_flash_shared2tb(), p.cost_flash_small_die('h'),
                                                 p.cost_flash('A2', 'h'), p.cost_flash('C', 'h'))]
    assert round(rn / max(base_n), 1) == 1.7 and round(rn / min(base_n), 1) == 3.8
    assert round(rh / max(base_h)) == 4 and round(rh / min(base_h)) == 13
    assert round(p.day_energy_nj(0.40)['total'] / 1e3, 1) == 31.1
    assert round(p.day_energy_nj(0.55)['total'] / 1e3, 1) == 41.3
    assert round(p.day_energy_nj(0.08)['total'] / 1e3, 1) == 9.3


def test_resident_baseline():
    assert round(p.resident_decode_tok_s(), 1) == 15.3 and round(p.resident_e_tok(), 2) == 0.5
    assert round(p.resident_ttft(350), 2) == 0.65 and round(p.resident_ttft(3000), 2) == 0.86
    d = p.resident_day_energy()
    assert round(d['total'] / 1e3) == 108 and round(d['decode'] / 1e3) == 102
    assert [p.yuan(x) for x in p.cost_resident_total('n')] == [1922, 2452, 3100]
    assert p.yuan(p.cost_resident_total('h')[1]) == 18356
    e = p.round_energy(3000)
    assert round(e['stream']) == 50 and round(e['compute'], 1) == 3.4 and round(e['decode'], 1) == 2.4


def test_configs():
    assert [round(x, 2) for x in p.cfg_ttft('shared')] == [3.57]
    assert [round(x, 2) for x in p.cfg_ttft('C')] == [3.33, 0.85]
    assert [p.yuan(p.cfg_cost(k_)[1]) for k_ in ('shared', 'A2', 'C')] == [599, 997, 1373]
    assert [p.yuan(p.cfg_cost(k_, 'h')[1]) for k_ in ('shared', 'A2', 'C')] == [1379, 2778, 4340]
    assert [round(x / 1e3, 1) for x in p.cfg_day('A2')] == [31.1, 32.7]
    assert [round(x / 1e3, 1) for x in p.cfg_day('C')] == [9.3, 11.0]
    assert [round(p.storage_share(k_), 2) for k_ in ('shared', 'A2', 'C')] == [0.70, 0.82, 0.87]
    assert round(p.kv_long_fp16() / 1e9, 1) == 14.7

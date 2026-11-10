import hashlib, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
MD = ROOT / "端侧AI计算架构完整构想_v3.3.md"
V32 = ROOT.parents[1] / "端侧AI计算架构完整构想_v3.2_润色版.md"

REQUIRED = ["v3.3", "200 TOPS", "100 TOPS", "70%", "113.8 GB/s", "10.8 GB/s",
            "3.24K", "2.59K", "动态驻留", "6.4.2.2", "32.4K", "0.16%",
            "11.4 s", "4.4K", "4.27 W", "2.66 s", "60 倍", "9.4", "0.46 s", "1:23",
            "615", "1230", "88–176",
            "2029 负载基线", "负载实例（v3.3 新增）", "392 ops/B", "16 ops/B", "26 GB", "25 GB/s",
            "每参数 16 B", "外部等待", "2–4 个数量级", "非嵌入参数", "890 bytes/token",
            "口径前提（v3.3）", "约 95 mW", "C-S26", "on-device-model-swapping/` §4.2"]
FORBIDDEN = ["pin 住 50%", "~1.25K", "@ 40 TOPS 有效", "50 TOPS ÷ 68", "MoE 下收益最大",
             "降低一到两个数量级", "常是延迟的隐藏大头", '比全参微调的"3 倍权重"低一个量级',
             "持续功率：mW 级，可持续无限", "持续功率：中等，但不可被抢占", "C 类（永远 3mW）", "96 mW"]


def test_v32_untouched():
    assert hashlib.sha256(V32.read_bytes()).hexdigest() == \
        "ac1b440dab4a7d29dafb829575a4ee9bcba6a0fde3e6edcecbae550dee4c380f"


def test_required_present():
    t = MD.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED if s not in t]
    assert not missing, missing


def test_forbidden_absent():
    t = MD.read_text(encoding="utf-8")
    found = [s for s in FORBIDDEN if s in t]
    assert not found, found

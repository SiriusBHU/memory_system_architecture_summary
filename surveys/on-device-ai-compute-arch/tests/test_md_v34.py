import hashlib, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
MD = ROOT / "端侧AI计算架构完整构想_v3.4_润色版.md"
V32 = ROOT.parents[1] / "端侧AI计算架构完整构想_v3.2_润色版.md"

REQUIRED = ["v3.4", "200 TOPS", "70%", "113.8 GB/s", "10.8 GB/s", "3.24K", "32.4K", "11.4 秒", "4.4K",
            "4.27 W", "2.66 s", "60 倍", "9.4 倍", "0.46 s", "1:23", "615", "1230", "88–176",
            "392 ops/B", "16 ops/B", "26 GB", "25 GB/s", "每参数 16 B", "890 bytes/token",
            "九类十节", "小秘书」", "不含时延", "5.3 s", "约 0.35–1.0 kJ", "桥不再省时", "并发带宽账未闭合"]
FORBIDDEN = ["桥的价值只剩能力优势", "计算能耗约 0.34 kJ", "（v3.3 修订", "（v3.3 新增", "v3.3 注：", "v3.2 →"]


def _body(t):
    return t.split("## 摘要", 1)[1].split("# 附录 A 修订沿革", 1)[0]   # 摘要到附录 A 之间不应再有版本叙述


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


def test_body_has_no_version_narration():
    body = _body(MD.read_text(encoding="utf-8"))
    hits = [m.group(0) for m in re.finditer(r"v3\.[0-3][^0-9]", body)]
    assert hits == [], hits[:5]

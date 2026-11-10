import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from pptx import Presentation
import build_ppt

KEYS = {  # 标题以该小节号开头的页必须出现的字符串
    "6.4.1": ["8.54", "4.27", "2.14", "10.8"],
    "6.4.2 ": ["0.43 ms", "1.39 s", "3.24K", "8.75K"],
    "6.4.2.1": ["2.92K", "2.59K", "2.16K", "C/W", "10.5 s", "5.3 s"],
    "6.4.2.2": ["0.16%", "32.4K"],
    "6.4.3 / 6.4.4": ["1.71", "2.31", "4.4K", "9.4"],
    "6.4.5 / 6.4.6": ["4.27 W", "2.66 s", "5.0 s"],
    "4.3-P": ["16 TFLOP", "0.11 s", "48 TFLOP", "0.97 kJ"],
    "4.3-D-w": ["56.5", "20.5 kJ", "28", "114", "0.72"],
}
FULL_KEYS = {
    "2.4.1": ["0.46 s", "1:23", "5.7 W"],
    "4.2": ["615", "1230", "88–176"],
    "5.2.2": ["11.4 s", "14 s", "13.0 s", "49 s", "不含时延"],
    "6.7": ["60 倍"],
    "4.3-C": ["392", "16 ops/B", "21.7 mJ"],
    "4.3-E": ["26 GB", "7.3 TFLOP"],
    "4.3-V": ["25 GB/s", "17.6 ms", "1.25 W"],
    "4.3-D-a": ["14.6 MB", "89 MB"],
    "4.3-G": ["268 MB", "531 MB"],
    "4.3-F": ["16 B/参数", "10 min", "0.35–1.0 kJ"],
    "4.3-Ctrl": ["0.03 ms", "22 ms"],
    "4.3-KV-io": ["7.8 MB/s", "89 MB"],
    "4.3  2029": ["8B @2-bit", "890 B/token", "300M", "69 kJ"],
    "附录 A": ["v3.4（本版）", "0.35–1.0 kJ"],
    "附录 B": ["50 GB/s", "12 tok/s"],
    "附录 C": ["KV-S46", "C-S19"],
    "附录 D": ["v3.2", "v3.4", "3.24K", "11.4 s", "4.4K"],
}


def _texts(slide):
    out = []
    for sh in slide.shapes:
        if sh.has_text_frame:
            out.append(sh.text_frame.text)
        if sh.has_table:
            out += [c.text for r in sh.table.rows for c in r.cells]
    return "\n".join(out)


def _check(prs, expected_n, has_cover, keys=KEYS):
    assert len(prs.slides) == expected_n
    for i, s in enumerate(prs.slides):
        if i == 0 and has_cover:
            continue
        assert "出处：" in _texts(s), f"slide {i + 1} 缺出处"
    for key, needles in keys.items():
        pages = [_texts(s) for s in prs.slides if (_texts(s).split("\n")[0] + " ").startswith(key)]
        assert pages, f"找不到 {key} 页"
        joined = "\n".join(pages)
        miss = [n for n in needles if n not in joined]
        assert not miss, (key, miss)


def test_sample(tmp_path):
    p = tmp_path / "sample.pptx"; build_ppt.build(p, sample=True)
    _check(Presentation(p), 9, has_cover=False)


def test_full(tmp_path):
    p = tmp_path / "full.pptx"; build_ppt.build(p)
    _check(Presentation(p), 58, has_cover=True, keys={**KEYS, **FULL_KEYS})


def test_no_version_narration(tmp_path):
    """v3.4：除附录外，正文页不出现 v3.2 / v3.3 字样（封面与页脚的 v3.4 允许）。"""
    import re
    p = tmp_path / "full.pptx"; build_ppt.build(p)
    bad = []
    for i, s in enumerate(Presentation(p).slides, start=1):
        t = _texts(s)
        if t.split("\n")[0].startswith("附录") or t.split("\n")[0].startswith("参考"):
            continue
        hits = re.findall(r"v3\.[23]", t)
        if hits:
            bad.append((i, t.split("\n")[0][:20], len(hits)))
    assert not bad, bad

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pptx import Presentation
from pptx.util import Inches
import pptkit as k


def build_smoke(path):
    prs = k.new_deck()
    s = k.add_slide(prs, "6.4.1", "配比公式", half_life=("快变量",), tag="v3.3 修订", source="原文 §6.4.1")
    k.formula_box(s, Inches(0.5), Inches(1.2), Inches(6), Inches(2), "推导",
                  [k.fx("B_{ufs} / F_{eff} ≥ 1 / (4·L_c)"), [k.hl("快变量"), "说明文字"]])
    k.table(s, Inches(7), Inches(1.2), Inches(5.8), Inches(2), ["chunk", "带宽"], [["4K", "8.54 GB/s"]])
    k.chart(s, Inches(0.5), Inches(3.5), Inches(6), Inches(3), "bar", ["4K", "8K"], {"需求": [8.54, 4.27]})
    k.xy_chart(s, Inches(7), Inches(3.5), Inches(5.8), Inches(3), {"屋顶": [(1, 1), (100, 100)]}, log=True)
    k.arrow(s, Inches(0.5), Inches(7.0), Inches(2), Inches(7.0))
    k.notes(s, "备注")
    prs.save(path)
    return path


def test_smoke(tmp_path):
    p = build_smoke(tmp_path / "t.pptx")
    prs2 = Presentation(p); sl = prs2.slides[0]
    texts = " ".join(sh.text_frame.text for sh in sl.shapes if sh.has_text_frame)
    assert "6.4.1" in texts and "快变量" in texts and "出处" in texts
    assert ("v3.3 修订" in texts) == k.SHOW_TAGS
    xml = sl._element.xml
    assert 'baseline="-25000"' in xml            # 下标生效
    assert any(sh.has_table for sh in sl.shapes)
    assert sum(1 for sh in sl.shapes if sh.has_chart) == 2
    assert sl.notes_slide.notes_text_frame.text == "备注"

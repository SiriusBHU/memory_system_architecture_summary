# -*- coding: utf-8 -*-
"""生成《端侧AI计算架构完整构想》v3.4 技术评审 PPT（技术口径同 v3.3）。

用法：python3 build_ppt.py [--sample] [输出路径]
"""
import pathlib, sys
import pptkit as k

OUT = pathlib.Path(__file__).resolve().parent / "端侧AI计算架构完整构想_v3.4.pptx"


def build(path=OUT, sample=False):
    import s_64, s_ch4
    prs = k.new_deck()
    if sample:
        s_64.build(prs)
        s_ch4.build_sample(prs)
    else:
        import s_front, s_ch5_63, s_back
        for mod in (s_front, s_ch4, s_ch5_63, s_64, s_back):
            mod.build(prs)
    prs.save(path)
    return prs


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(args[0] if args else OUT, sample="--sample" in sys.argv)

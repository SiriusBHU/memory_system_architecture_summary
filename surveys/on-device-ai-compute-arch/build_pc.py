# -*- coding: utf-8 -*-
"""生成《PC 端侧大模型架构构想》汇报版 PPT（主线：负载 → 性能 → 功耗 → 成本）。

用法：python3 build_pc.py [输出路径]
"""
import pathlib, sys
import pptkit as k

OUT = pathlib.Path(__file__).resolve().parent / "PC端侧大模型架构构想_汇报版.pptx"


def build(path=OUT):
    import s_pc2
    prs = k.new_deck()
    s_pc2.build(prs)
    prs.save(path)
    return prs


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(args[0] if args else OUT)

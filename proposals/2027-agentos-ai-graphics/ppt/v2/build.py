"""v2 立项 deck 构建入口：模板页（封面、章节页）走 ppt_templates 渲染器，其余页面用 lib.py 自绘，
最后按登记顺序重排、保存，并可出预览图。

运行（在 ppt_templates 的 uv 环境里）：
  cd /d/projects/ppt_templates && uv run python <本目录>/build.py [--preview] [--only 3,5-7]
"""

import argparse
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lib  # noqa: E402
from ppt_templates.images import ImageSource  # noqa: E402
from ppt_templates.preview import render_pngs  # noqa: E402
from ppt_templates.render import render_deck  # noqa: E402

import registry  # noqa: E402

MODULES = ["p0_front", "p1_insight", "p1b_foundation", "p1c_graphics", "p2_problem", "p3_arch", "p3b_arch",
           "p4_agentos", "p4_support", "p4_graphics", "p5_plan"]
OUT = HERE.parent / "2027立项-AgentOS与AI图形-v2.pptx"


def build(only=None, modules=None):
    for name in modules or MODULES:
        if (HERE / f"{name}.py").exists():
            importlib.import_module(name)
    pages = registry.PAGES
    if only:
        pages = [p for i, p in enumerate(pages, 1) if i in only]
    deck = {"style": "default", "pages": [d for kind, d in pages if kind == "tpl"]}
    if deck["pages"]:
        prs = render_deck(deck, lib.ROOT, ImageSource(HERE))
    else:
        from pptx import Presentation
        from pptx.util import Emu
        from ppt_templates.geometry import CANVAS_H, CANVAS_W, px_to_emu
        prs = Presentation()
        prs.slide_width, prs.slide_height = Emu(px_to_emu(CANVAS_W)), Emu(px_to_emu(CANVAS_H))
    n_tpl = len(deck["pages"])
    order, t, c = [], 0, n_tpl
    for kind, d in pages:
        if kind == "tpl":
            order.append(t)
            t += 1
        else:
            d(prs)
            order.append(c)
            c += 1
    lst = prs.slides._sldIdLst
    ids = list(lst)
    for el in ids:
        lst.remove(el)
    for i in order:
        lst.append(ids[i])
    return prs


def parse_only(s):
    out = set()
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--out")
    ap.add_argument("--modules", help="逗号分隔的页面模块，默认为主 deck 的 MODULES（单页材料用 p6_onepager）")
    ap.add_argument("--preview-dir", help="预览图目录，默认 v2/preview")
    args = ap.parse_args()
    prs = build(parse_only(args.only) if args.only else None,
                args.modules.split(",") if args.modules else None)
    out = Path(args.out) if args.out else OUT
    prs.save(out)
    print(f"saved {out} ({len(prs.slides)} slides)")
    for w in lib.WARNINGS:
        print("WARN", w)
    if args.preview:
        pdir = Path(args.preview_dir) if args.preview_dir else HERE / "preview"
        pdir.mkdir(parents=True, exist_ok=True)
        for old in pdir.glob("slide-*.png"):
            old.unlink()
        render_pngs(prs, pdir, width=1600)
        print(f"preview -> {pdir}")

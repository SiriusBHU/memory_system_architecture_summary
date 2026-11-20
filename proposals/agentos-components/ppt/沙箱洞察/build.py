"""安卓 Agent 沙箱洞察 deck 的构建入口（2026-11-15）。

复用上级目录 ppt/lib.py 的页面库与浅色风格（深红 #A00000、浅色卡片、只画横线的表格），页面内容在 pages_sbx.py。
运行（在 ppt_templates 的 uv 环境里）：
  cd /d/projects/ppt_templates && uv run python <本目录>/build.py [--only 3,5-7] [--out x.pptx] [--preview] [--preview-dir d]
单页预览务必同时传 --out 到临时路径，避免覆盖正式文件。
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # ppt/lib.py
sys.path.insert(0, str(HERE))

import lib  # noqa: E402
import pages_sbx  # noqa: E402
from ppt_templates.preview import render_pngs  # noqa: E402

OUT = HERE / "安卓Agent沙箱洞察.pptx"


def parse_only(s):
    out = set()
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def build(only=None):
    prs = lib.base_presentation()
    for i, fn in enumerate(pages_sbx.PAGES, 1):
        if only and i not in only:
            continue
        fn(prs)
    return prs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--out")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--preview-dir")
    args = ap.parse_args()
    prs = build(parse_only(args.only) if args.only else None)
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
        render_pngs(prs, pdir, width=1920)
        print(f"preview -> {pdir}")

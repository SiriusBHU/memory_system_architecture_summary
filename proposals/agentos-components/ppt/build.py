"""Agent OS 三项系统服务汇报 deck 的构建入口（2026-11-09 第三版）。

底版是空白演示文稿（不使用任何外部母版）；各页面模块按汇报顺序 import，用 registry.page 登记。
运行（在 ppt_templates 的 uv 环境里）：
  cd /d/projects/ppt_templates && uv run python <本目录>/build.py [--modules a,b] [--only 3,5-7] [--preview]
"""

import argparse
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lib  # noqa: E402
import registry  # noqa: E402
from ppt_templates.preview import render_pngs  # noqa: E402

# 汇报顺序：封面与摘要 → 一 洞察 → 二 场景与负载瓶颈 → 三 架构与关键技术 → 四 规划与投入
MODULES = [
    "p0_front",                                                    # 封面、摘要
    "p1_insight",                                                  # 一、洞察
    "p2_scene",                                                    # 二、章节页、现状、参考负载
    "p2_load_inf", "p2_load_sbx", "p2_load_mm",                    # 负载量化，各附一页体验与商业化问题
    "p2_gap",                                                      # 当代操作系统的能力缺口
    "p2_bn_inf", "p2_bn_sbx", "p2_bn_mm",                          # 瓶颈分析
    "p3_overall",                                                  # 三、章节页、总体架构、会话档位
    "p3_inf", "p3_sbx", "p3_mm",                                   # 各项系统服务的架构与关键技术
    "p4_plan",                                                     # 四、规划与投入
]
OUT = HERE / "AgentOS三项系统服务-汇报.pptx"


def build(modules=None, only=None):
    prs = lib.base_presentation()
    for name in modules or MODULES:
        if (HERE / f"{name}.py").exists():
            importlib.import_module(name)
        else:
            print(f"skip missing module {name}")
    for i, fn in enumerate(registry.PAGES, 1):
        if only and i not in only:
            continue
        fn(prs)
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
    ap.add_argument("--modules")
    ap.add_argument("--only")
    ap.add_argument("--out")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--preview-dir")
    args = ap.parse_args()
    prs = build(args.modules.split(",") if args.modules else None, parse_only(args.only) if args.only else None)
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

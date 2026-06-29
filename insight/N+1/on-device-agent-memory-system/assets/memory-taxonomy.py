#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「记忆分类两条正交轴」矩阵图（配合正文 §9 分类小节）。

轴 A = 表示/载体（横）：参数(weights) / 明文·外置(flash·向量库) / 激活·KV Cache(DRAM)
轴 B = 内容/功能（纵）：工作记忆 / 情景 episodic / 语义·画像 semantic / 程序性·指令 procedural

把 system/skill prompt、参数、STM、MTM、LPM 等元素摆进 4×3 网格，并用虚线框圈出
「本篇（MemoryOS/Mem0）管理范围 = 动态记忆：情景→语义固化」，框外为静态/参数/指令
（system·skill prompt 及其 KV 前缀复用 = 姊妹篇 KV 层）。

数据来源: MemoryOS (arXiv 2506.06326, EMNLP 2025 Oral); MemOS MemCube 三型记忆
          (参数/激活/明文, arXiv 2507.03724); Mem0 (arXiv 2504.19413)。

运行:
    pip install matplotlib
    python memory-taxonomy.py
输出: 脚本所在目录下 memory-taxonomy.png / .svg
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

matplotlib.rcParams["font.sans-serif"] = [
    "Hiragino Sans GB", "STHeiti", "Heiti TC", "Arial Unicode MS", "PingFang HK",
    "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC",
    "Source Han Sans SC", "WenQuanYi Zen Hei", "sans-serif",
]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["svg.fonttype"] = "none"

# ----- 配色（与 memoryos-arch.py / memory-lifecycle.py 一致）-----
C_STM   = "#9ec6e8"; E_STM = "#7aa8cf"
C_MTM   = "#edbd88"; E_MTM = "#d9a05f"
C_LPM   = "#c9a6d6"; E_LPM = "#a87bbd"
C_STAT  = "#e6e3da"; E_STAT = "#b8b3a4"   # 静态/参数（灰）
C_PROC  = "#f0e6cf"; E_PROC = "#cdb98a"   # 指令/程序（米）
C_EMPTY = "#fafaf7"
C_TXT   = "#333333"; C_MUTED = "#8a8a8a"; C_HOT = "#b5402f"
C_DYN   = "#2f7d57"   # 动态域虚线框（绿）

fig, ax = plt.subplots(figsize=(14.2, 9.4))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

# ----- 网格几何 -----
cols = {"参数": (17, 25), "明文": (44, 26), "激活": (72, 25)}   # (x0, w)
rows = {"工作": (69, 16), "情景": (51, 16), "语义": (33, 16), "程序": (15, 16)}  # (y0, h)


def box(x, y, w, h, color, ec, lw=1.3, r=0.7, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={r}",
                                facecolor=color, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=2))


def cellbox(ck, rk, color, ec, title, sub="", tc=C_TXT, pad=1.4, fs_t=8.8, fs_s=7.4):
    x0, w = cols[ck]; y0, h = rows[rk]
    box(x0 + pad, y0 + pad, w - 2 * pad, h - 2 * pad, color, ec=ec)
    cx = x0 + w / 2
    if sub:
        ax.text(cx, y0 + h / 2 + 1.6, title, ha="center", va="center", fontsize=fs_t,
                fontweight="bold", color=tc, zorder=4)
        ax.text(cx, y0 + h / 2 - 1.9, sub, ha="center", va="center", fontsize=fs_s,
                color=C_MUTED, zorder=4)
    else:
        ax.text(cx, y0 + h / 2, title, ha="center", va="center", fontsize=fs_t,
                color=tc, zorder=4)


def arrow(x0, y0, x1, y1, color, lw=1.8, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=14,
                                 color=color, linewidth=lw,
                                 connectionstyle=f"arc3,rad={rad}", zorder=6, shrinkA=2, shrinkB=2))


def alabel(x, y, s, color, fs=7.6):
    ax.text(x, y, s, ha="center", va="center", fontsize=fs, color=color, zorder=7,
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=color, lw=0.7, alpha=0.95))


# ===== 标题 =====
ax.text(50, 97.2, "记忆的两条正交分类轴：内容 × 载体", ha="center", fontsize=16,
        fontweight="bold", color="#222")
ax.text(50, 93.6, "虚线框内 = 本篇（MemoryOS / Mem0）管理范围：动态记忆「情景 → 语义/画像」固化；框外 = 静态·参数·指令",
        ha="center", fontsize=9.2, color=C_MUTED)

# ===== 轴标题 =====
ax.text(57, 89.7, "轴 A · 表示 / 载体  →", ha="center", fontsize=10.5, fontweight="bold", color="#555")
ax.text(3.2, 50, "轴 B · 内容 / 功能  ↓", ha="center", va="center", rotation=90,
        fontsize=10.5, fontweight="bold", color="#555")

# 列表头
col_titles = {
    "参数": ("参数 Parametric", "权重 / Adapter（静态）"),
    "明文": ("明文 · 外置 Plaintext", "flash / 向量库（持久可检索）"),
    "激活": ("激活 · KV Cache", "DRAM 活跃状态（工作态）"),
}
for ck, (t, s) in col_titles.items():
    x0, w = cols[ck]
    ax.text(x0 + w / 2, 87.6, t, ha="center", fontsize=9.4, fontweight="bold", color="#444")
    ax.text(x0 + w / 2, 85.4, s, ha="center", fontsize=7.4, color=C_MUTED)

# 行表头
row_titles = {
    "工作": ("工作记忆", "Working"),
    "情景": ("情景", "Episodic"),
    "语义": ("语义 / 画像", "Semantic"),
    "程序": ("程序性 / 指令", "Procedural"),
}
for rk, (t, s) in row_titles.items():
    y0, h = rows[rk]
    ax.text(10.5, y0 + h / 2 + 1.4, t, ha="center", fontsize=9.4, fontweight="bold", color="#444")
    ax.text(10.5, y0 + h / 2 - 1.8, s, ha="center", fontsize=7.2, color=C_MUTED)

# ===== 空格背景（淡）=====
for ck in cols:
    for rk in rows:
        x0, w = cols[ck]; y0, h = rows[rk]
        box(x0 + 1.4, y0 + 1.4, w - 2.8, h - 2.8, C_EMPTY, ec="#eeeae0", lw=0.8)

# ===== 动态域虚线框（先画底层）=====
box(43, 32.5, 55, 53.5, "none", ec=C_DYN, lw=2.0, r=1.2, ls=(0, (5, 3)))
ax.text(45.5, 84.3, "本篇管理范围 · 动态记忆", ha="left", va="center", fontsize=8.6,
        fontweight="bold", color=C_DYN,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=C_DYN, lw=0.9))

# ===== 填充各格 =====
# 工作记忆
cellbox("激活", "工作", C_STM, E_STM, "STM · 7 页 FIFO", "窗口工作集", tc="#2f5f86")
# 情景
cellbox("明文", "情景", C_MTM, E_MTM, "MTM · 话题段", "对话事件历史", tc="#9c6b2e")
ax.text(cols["激活"][0] + cols["激活"][1] / 2, rows["情景"][0] + 8,
        "(STM 生页\n亦属情景)", ha="center", va="center", fontsize=6.8, color=C_MUTED, zorder=3)
# 语义 / 画像
cellbox("明文", "语义", C_LPM, E_LPM, "LPM 画像 / Mem0 事实库", "剥离上下文的事实", tc="#6f4a86")
cellbox("参数", "语义", C_STAT, E_STAT, "模型权重内常识", "预训练固化")
# 程序性 / 指令
cellbox("参数", "程序", C_STAT, E_STAT, "微调 / Adapter", "固化的能力")
cellbox("明文", "程序", C_PROC, E_PROC, "system / skill prompt", "静态指令原文", tc="#7a6326")
cellbox("激活", "程序", C_PROC, E_PROC, "其 KV 前缀缓存", "prefix reuse（姊妹篇）", tc="#7a6326")

# ===== 迁移箭头 =====
# 写入固化：STM(工作/激活) → MTM(情景/明文) → LPM(语义/明文)
arrow(cols["激活"][0] + 4, rows["工作"][0] + 2, cols["明文"][0] + cols["明文"][1] - 4,
      rows["情景"][0] + rows["情景"][1] - 2, color="#b07d3a", lw=1.6, rad=0.18)
arrow(cols["明文"][0] + cols["明文"][1] / 2, rows["情景"][0] + 2,
      cols["明文"][0] + cols["明文"][1] / 2, rows["语义"][0] + rows["语义"][1] - 2,
      color=E_LPM, lw=1.6)
alabel(53, 77, "写入：情景→语义\n固化（沉淀晋升）", "#9c6b2e", fs=7.2)

# 提升注入：LPM(语义/明文) → (语义/激活) MemOS 热点明文→激活
arrow(cols["明文"][0] + cols["明文"][1] - 2, rows["语义"][0] + rows["语义"][1] / 2,
      cols["激活"][0] + 4, rows["语义"][0] + rows["语义"][1] / 2, color=C_HOT, lw=1.7, rad=0.0)
alabel(cols["激活"][0] + cols["激活"][1] / 2, rows["语义"][0] + rows["语义"][1] / 2 + 4.8,
       "MemOS:热点明文→激活注入", C_HOT, fs=7.0)
ax.text(cols["激活"][0] + cols["激活"][1] / 2, rows["语义"][0] + rows["语义"][1] / 2 - 0.3,
        "（语义记忆的\n激活形态）", ha="center", va="center", fontsize=6.6, color=C_MUTED, zorder=4)

# ===== 页脚图例 =====
ax.text(2, 8.2, "蓝/橙/紫 = MemoryOS 三级 STM/MTM/LPM（动态记忆，本篇）",
        ha="left", fontsize=7.8, color=C_MUTED)
ax.text(2, 5.6, "灰 = 参数（权重，静态）   米 = 程序性指令 system/skill prompt 及其 KV 前缀（静态，姊妹篇 KV 层）",
        ha="left", fontsize=7.8, color=C_MUTED)
ax.text(2, 3.0, "→ 写入把记忆沿矩阵迁移：情景(明文)逐步固化为语义/画像(明文)；MemOS 再把热点明文提升为激活(KV)",
        ha="left", fontsize=7.8, color=C_MUTED)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "memory-taxonomy.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "memory-taxonomy.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: memory-taxonomy.png / .svg")

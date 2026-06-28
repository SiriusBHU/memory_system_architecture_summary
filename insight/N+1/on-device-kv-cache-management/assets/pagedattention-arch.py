#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「vLLM PagedAttention：KV Cache 分页管理结构」架构图。

把操作系统的虚拟内存分页搬到 KV Cache：定长 KV Block + 块表(logical→physical 非连续映射)
+ 按需分配 + 写时复制共享 + 自动前缀缓存(哈希链 + LRU + 引用计数)。
浪费从传统的 60–80% 降到 <4%（仅末块半满）。

数据来源: vLLM PagedAttention blog (Kwon et al., 2023) https://vllm.ai/blog/2023-06-20-vllm
          vLLM 自动前缀缓存设计文档 https://docs.vllm.ai/en/latest/design/prefix_caching/

运行:
    pip install matplotlib
    python pagedattention-arch.py
输出: 脚本所在目录下 pagedattention-arch.png / .svg
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

# ----- 配色 -----
C_REQ   = "#7ba3cb"   # 逻辑块（柔蓝）
C_TABLE = "#edbd88"   # 块表（柔橙）
C_PHYS  = "#8fbf9f"   # 物理块（柔绿）
C_SHARE = "#e07a7a"   # 共享/复用块（柔红）
C_FREE  = "#e9e9e2"   # 空闲块（灰）
C_MECH  = "#fbfbf6"   # 机制说明框底
C_EDGE  = "#cfcfc4"
C_TXT   = "#333333"
C_MUTED = "#888888"

fig, ax = plt.subplots(figsize=(14.5, 9.2))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, color, text, fs=9.5, bold=False, ec=C_EDGE, tc=C_TXT, rounded=True):
    style = "round,pad=0.02,rounding_size=0.8" if rounded else "square,pad=0.02"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style,
                                facecolor=color, edgecolor=ec, linewidth=1.2, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, fontweight="bold" if bold else "normal", zorder=3)


def arrow(x0, y0, x1, y1, label="", color="#666", style="-|>", lw=1.4, fs=8.5,
          ls="-", lx=None, ly=None, tc=None):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=14, color=color, linewidth=lw,
                                 linestyle=ls, zorder=4, shrinkA=0, shrinkB=0))
    if label:
        ax.text(lx if lx is not None else (x0 + x1) / 2,
                ly if ly is not None else (y0 + y1) / 2,
                label, ha="center", va="center", fontsize=fs,
                color=tc or color, zorder=5,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))


# ===== 标题 =====
ax.text(50, 97.5, "vLLM PagedAttention：KV Cache 分页管理结构",
        ha="center", fontsize=16, fontweight="bold", color="#222")
ax.text(50, 93.6, "定长 KV Block · 块表 logical→physical 非连续映射 · 按需分配 · 写时复制共享 · 自动前缀缓存",
        ha="center", fontsize=10, color=C_MUTED)

# ===== 三列标题 =====
ax.text(15, 88, "① 请求序列（逻辑块）", ha="center", fontsize=11, fontweight="bold", color="#3a5f80")
ax.text(45, 88, "② Block Table 块表", ha="center", fontsize=11, fontweight="bold", color="#9c6b2e")
ax.text(80, 88, "③ 物理 KV 块池（显存）", ha="center", fontsize=11, fontweight="bold", color="#4a7a58")

# ----- 左列：两个请求的逻辑块 -----
ax.text(15, 84.5, "请求 A", ha="center", fontsize=9.5, color=C_MUTED)
box(4,  77, 22, 5.5, C_REQ, "L0  (token 0–15)", fs=9)
box(4,  70.5, 22, 5.5, C_REQ, "L1  (token 16–31)", fs=9)
box(4,  64, 22, 5.5, C_REQ, "L2  (token 32–39，半满)", fs=8.5)

ax.text(15, 58, "请求 B（与 A 同前缀）", ha="center", fontsize=9.5, color=C_MUTED)
box(4,  51.5, 22, 5.5, C_REQ, "L0'  (token 0–15)", fs=9)
box(4,  45, 22, 5.5, C_REQ, "L1'  (token 16–…)", fs=9)

# ----- 中列：块表映射 -----
box(36, 70, 19, 13.5, C_TABLE, "", rounded=True)
ax.text(45.5, 81, "表 A", ha="center", fontsize=9, color="#9c6b2e", fontweight="bold")
ax.text(45.5, 78, "L0 → P7（满 16）", ha="center", fontsize=8.8, color=C_TXT)
ax.text(45.5, 75, "L1 → P1（满 16）", ha="center", fontsize=8.8, color=C_TXT)
ax.text(45.5, 72, "L2 → P3（填 8/16）", ha="center", fontsize=8.8, color=C_TXT)

box(36, 44.5, 19, 9.5, C_TABLE, "", rounded=True)
ax.text(45.5, 51.5, "表 B", ha="center", fontsize=9, color="#9c6b2e", fontweight="bold")
ax.text(45.5, 48.7, "L0' → P7（共享！）", ha="center", fontsize=8.8, color="#b5402f", fontweight="bold")
ax.text(45.5, 46, "L1' → P9（独占）", ha="center", fontsize=8.8, color=C_TXT)

# 逻辑块 -> 块表
arrow(26, 79.7, 36, 79, color="#9aa", lw=1.1)
arrow(26, 73.2, 36, 76, color="#9aa", lw=1.1)
arrow(26, 66.7, 36, 73, color="#9aa", lw=1.1)
arrow(26, 54.2, 36, 49.5, color="#9aa", lw=1.1)
arrow(26, 47.7, 36, 46.5, color="#9aa", lw=1.1)

# ----- 右列：物理块网格 6x2 -----
phys = {
    0: ("P0", C_FREE, "空闲"),
    1: ("P1", C_PHYS, "A·L1"),
    2: ("P2", C_FREE, "空闲"),
    3: ("P3", C_PHYS, "A·L2\n8/16"),
    4: ("P4", C_FREE, "空闲"),
    5: ("P5", C_PHYS, "其他请求"),
    6: ("P6", C_FREE, "空闲"),
    7: ("P7", C_SHARE, "A·L0 + B·L0'\nrefcount=2"),
    8: ("P8", C_FREE, "空闲"),
    9: ("P9", C_PHYS, "B·L1'"),
    10: ("P10", C_FREE, "空闲"),
    11: ("P11", C_FREE, "空闲"),
}
gx0, gy0, bw, bh, gapx, gapy = 64, 44, 15.5, 6.3, 2.5, 1.2
pos = {}
for i in range(12):
    col = i % 2
    row = i // 2
    x = gx0 + col * (bw + gapx)
    y = gy0 + (5 - row) * (bh + gapy)
    pos[i] = (x + bw / 2, y + bh / 2)
    name, color, lab = phys[i]
    fs = 8.0 if "\n" in lab else 8.6
    box(x, y, bw, bh, color, f"{name}\n{lab}", fs=fs,
        bold=(color == C_SHARE), ec="#c97a6f" if color == C_SHARE else C_EDGE)

# 块表 -> 物理块（关键映射）
arrow(55, 78, pos[7][0] - bw / 2, pos[7][1], color="#4a7a58", lw=1.3, style="-|>")   # A·L0->P7
arrow(55, 75, pos[1][0] - bw / 2, pos[1][1], color="#4a7a58", lw=1.1)                 # A·L1->P1
arrow(55, 72, pos[3][0] - bw / 2, pos[3][1], color="#4a7a58", lw=1.1)                 # A·L2->P3
arrow(55, 48.7, pos[7][0] - bw / 2, pos[7][1] - 1.2, color="#b5402f", lw=1.6,
      style="-|>", label="共享", lx=60, ly=55, tc="#b5402f")                          # B·L0'->P7 共享
arrow(55, 46, pos[9][0] - bw / 2, pos[9][1], color="#4a7a58", lw=1.1)                 # B·L1'->P9

# ===== 底部：三大机制 =====
ax.text(50, 38.5, "三个关键机制", ha="center", fontsize=11.5, fontweight="bold", color="#222")

box(3, 21, 30, 14.5, C_MECH, "", rounded=True, ec=C_EDGE)
ax.text(18, 32.8, "① 按需分配", ha="center", fontsize=10, fontweight="bold", color="#3a5f80")
ax.text(18, 28.6, "仅在生成到新块时分配物理块；\n浪费只发生在序列「最后一块」。",
        ha="center", fontsize=8.6, color=C_TXT, linespacing=1.5)
ax.text(18, 23.4, "碎片/预留浪费  60–80% → <4%", ha="center", fontsize=9.2,
        fontweight="bold", color="#b5402f")

box(35, 21, 30, 14.5, C_MECH, "", rounded=True, ec=C_EDGE)
ax.text(50, 32.8, "② 写时复制（COW）共享", ha="center", fontsize=10, fontweight="bold", color="#9c6b2e")
ax.text(50, 28.6, "并行采样/beam：多序列共享同一前缀\n物理块 + 引用计数；写入时才复制。",
        ha="center", fontsize=8.6, color=C_TXT, linespacing=1.5)
ax.text(50, 23.4, "省内存 ≤55%   吞吐 ↑2.2×", ha="center", fontsize=9.2,
        fontweight="bold", color="#b5402f")

box(67, 21, 30, 14.5, C_MECH, "", rounded=True, ec=C_EDGE)
ax.text(82, 32.8, "③ 自动前缀缓存（跨请求复用）", ha="center", fontsize=9.6, fontweight="bold", color="#4a7a58")
ax.text(82, 27.8, "块哈希链 = H(父块hash, 本块token, LoRA/图像id)\n命中即 touch（refcount+1，移出空闲队列）",
        ha="center", fontsize=8.0, color=C_TXT, linespacing=1.5)
ax.text(82, 22.8, "空闲块 LRU 队列；仅 refcount==0 可淘汰", ha="center", fontsize=8.4,
        fontweight="bold", color="#b5402f")

# ===== 页脚：性能 =====
box(20, 6, 60, 9, "#f3f7f3", "", rounded=True, ec="#bcd")
ax.text(50, 12, "端到端吞吐（同等显存）", ha="center", fontsize=9.5, fontweight="bold", color="#4a7a58")
ax.text(50, 8.4, "vs HuggingFace Transformers  14–24×   ·   vs HF TGI  2.2–2.5×   ·   LMSYS 实测最高 30×",
        ha="center", fontsize=9, color=C_TXT)

# 图例
ax.text(2, 1.5, "图例： 蓝=逻辑块  橙=块表  绿=物理块(占用)  红=共享/复用块(refcount>1)  灰=空闲块",
        ha="left", fontsize=8, color=C_MUTED)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "pagedattention-arch.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "pagedattention-arch.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: pagedattention-arch.png / .svg")

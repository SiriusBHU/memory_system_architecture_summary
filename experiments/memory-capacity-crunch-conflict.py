#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「图1 · 挤压全貌」——手机内存需求（传统应用 + 端侧 AI 堆叠）vs 被价格冻结的
容量天花板，含用户可用线、反事实线与赤字楔形。复现 memory-capacity-crunch-conflict.svg。

运行:
    pip install matplotlib numpy
    python memory-capacity-crunch-conflict.py
输出: 同目录下 memory-capacity-crunch-conflict.png / .svg

中文字体: 下方 rcParams 已配置常见 CJK 字体的回退链。若仍显示成方块，把你系统里
带中文的字体名加到 font.sans-serif 列表最前面（Windows 一般 'Microsoft YaHei'，
macOS 'PingFang SC'，Linux 'Noto Sans CJK SC'）。
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# ---------------------------------------------------------------- 字体 / 全局样式
matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC",
    "Source Han Sans SC", "WenQuanYi Zen Hei", "sans-serif",
]
matplotlib.rcParams["axes.unicode_minus"] = False   # 负号用 ASCII，避免缺字
matplotlib.rcParams["svg.fonttype"] = "none"        # SVG 里保留文字（不转路径），可后期编辑

# ---------------------------------------------------------------- 配色（与 SVG 一致）
C_TRAD   = "#5589b8"   # 传统应用（蓝）
C_AI     = "#e8a35e"   # 端侧 AI（橙）
C_CAP    = "#1a4f7a"   # LPDDR 容量（深蓝）
C_COUNTER= "#9aa6b2"   # 反事实（灰）
C_DEF    = "#d62828"   # 赤字（红）
C_CROSS  = "#b03030"   # 交叉点 / 赤字标注
C_PROJ   = "#f6f6f0"   # 外推区底色
C_TXT    = "#333333"
C_MUTED  = "#777777"

# ---------------------------------------------------------------- 数据（中位旗舰，单位 GB）
years         = np.array([2024, 2025, 2026, 2027, 2028], dtype=float)
trad          = np.array([5.3, 6.0, 7.0, 8.2, 9.5])     # 传统应用工作集
total         = np.array([6.8, 8.0, 9.6, 11.5, 13.5])   # 总需求 = 传统 + 端侧 AI
ai            = total - trad                             # 端侧 AI 增量（堆叠在上层）
capacity      = np.array([12, 12, 12, 14, 16], dtype=float)   # 实际容量（2024–26 冻结）
counterfactual= np.array([12, 14, 16, 20, 24], dtype=float)   # 若 RAM 维持便宜（~19%/年）
user_avail    = np.array([9.0, 8.6, 8.0, 9.4, 10.8])    # 用户可用 = 容量 − OS/驱动/钉住预留

PROJ_START = 2026.5   # 外推区起点


def first_crossing(x, upper, lower):
    """返回 upper 由下方穿到 lower 上方的首个交点 (x, y)。"""
    d = upper - lower
    for i in range(len(x) - 1):
        if d[i] <= 0 <= d[i + 1]:
            t = (0 - d[i]) / (d[i + 1] - d[i])
            return x[i] + t * (x[i + 1] - x[i]), lower[i] + t * (lower[i + 1] - lower[i])
    return None


x_cross, y_cross = first_crossing(years, total, user_avail)   # ≈ (2025.27, 8.44)

# ---------------------------------------------------------------- 画布
fig = plt.figure(figsize=(11.5, 7.8))
ax = fig.add_axes([0.075, 0.215, 0.86, 0.655])  # [left, bottom, width, height]（如重叠可微调）

# 外推区底色（最底层）
ax.axvspan(PROJ_START, years[-1], color=C_PROJ, zorder=0)
ax.text((PROJ_START + years[-1]) / 2, 27.2, "外推区（2026.5 — 2028）",
        ha="center", va="top", fontsize=10, color=C_MUTED, zorder=1)

# 网格（数据之下）
ax.set_axisbelow(True)
ax.grid(axis="y", linestyle=(0, (2, 3)), color="#e6e6e6", linewidth=1)

# ---------------------------------------------------------------- 需求堆叠区：传统 + 端侧 AI
polys = ax.stackplot(years, trad, ai, colors=[C_TRAD, C_AI], zorder=2)
polys[0].set_alpha(0.55)   # 传统
polys[1].set_alpha(0.70)   # 端侧 AI

# ---------------------------------------------------------------- 赤字楔形：需求顶 > 用户可用
ax.fill_between(years, total, user_avail, where=(total >= user_avail),
                interpolate=True, color=C_DEF, alpha=0.28, linewidth=0, zorder=3)

# ---------------------------------------------------------------- 容量线（冻结）+ 冻结段高亮
ax.plot(years[:3], capacity[:3], color=C_CAP, linewidth=6, alpha=0.30,
        solid_capstyle="round", zorder=3)                       # 2024–26 冻结高亮
ax.plot(years, capacity, color=C_CAP, linewidth=2.4, zorder=4)
ax.scatter(years, capacity, s=16, color=C_CAP, zorder=5)

# 反事实线（RAM 仍便宜）
ax.plot(years, counterfactual, color=C_COUNTER, linewidth=1.6,
        linestyle=(0, (3, 4)), zorder=4)

# 用户可用线
ax.plot(years, user_avail, color=C_CAP, linewidth=1.6,
        linestyle=(0, (6, 4)), zorder=4)

# 交叉点
ax.scatter([x_cross], [y_cross], s=48, color=C_CROSS,
           edgecolor="white", linewidth=1.5, zorder=6)
ax.text(x_cross + 0.05, y_cross + 0.85, "交叉点 ≈ 2026",
        fontsize=11, fontweight="bold", color=C_CROSS, zorder=7)

# ---------------------------------------------------------------- 系列内联标注
ax.text(2024.08, 3.0, "传统应用 —— 浏览器 · 超级App · 相机/视频 · 游戏（约占需求 70%）",
        fontsize=10, color=C_CAP, zorder=7)
ax.text(2024.08, 6.45, "端侧 AI —— 1 个常驻模型 + KV（次要增量）",
        fontsize=10, color="#7a4a10", zorder=7)
ax.text(2024.08, 12.55, "旗舰 LPDDR（中位）—— 冻结在 ≈12 GB 直到 2026",
        fontsize=10, fontweight="bold", color=C_CAP, zorder=7)
ax.text(2024.08, 9.55, "用户可用（容量 − OS/驱动/钉住预留）",
        fontsize=9.5, color=C_CAP, zorder=7)

# 右侧端点标注
ax.text(2028.08, 16.0, "16 GB", fontsize=10, color=C_CAP, va="center")
ax.text(2028.08, 24.0, "若 RAM 仍便宜", fontsize=9.5, color="#7a8694", va="center")
ax.text(2028.08, 22.9, "≈ 24 GB（+19%/年）", fontsize=9.5, color="#7a8694", va="center")
ax.text(2028.08, 10.8, "用户可用 10.8 GB", fontsize=10, color=C_CAP, va="center")

# 赤字标注 + 指向楔形的箭头
ax.text(2026.55, 12.7, "赤字 = 塞不下的工作集",
        fontsize=11, fontweight="bold", color=C_CROSS, zorder=7)
ax.text(2026.55, 12.05, "由 zram 压缩 + lmkd 杀进程吸收",
        fontsize=9.5, color=C_CROSS, zorder=7)
ax.annotate("", xy=(2027.25, 10.3), xytext=(2026.95, 11.8),
            arrowprops=dict(arrowstyle="->", color=C_CROSS, linewidth=1.5), zorder=7)

# 价格说明框（左上空白区）
callout = ("天花板为何冻结 —— 是价格，不是物理\n"
           "移动 DRAM 合约价：≈$3/GB(2023) → ≈$20/GB(2026Q2)，\n"
           "LTA 高至 $21/GB。“多加 RAM” 这条便宜出路没了。")
ax.text(2024.12, 27.6, callout, fontsize=9.5, va="top", ha="left", linespacing=1.6,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff7f3", edgecolor="#d9a08c"),
        zorder=8)

# ---------------------------------------------------------------- 坐标轴
ax.set_xlim(2023.85, 2029.7)
ax.set_ylim(0, 28)
ax.set_xticks(years)
ax.set_xticklabels([int(y) for y in years])
ax.set_yticks([0, 4, 8, 12, 16, 20, 24, 28])
ax.set_xlabel("年份（中位旗舰）", fontsize=11, color="#666")
ax.set_ylabel("内存（GB）", fontsize=11, color="#666")
ax.tick_params(colors=C_MUTED)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color("#888")

# ---------------------------------------------------------------- 标题 / 副标题
fig.text(0.5, 0.965, "挤压：手机内存需求 vs 被价格冻结的容量天花板（2024–2028）",
         ha="center", fontsize=15, fontweight="bold", color="#222")
fig.text(0.5, 0.928, "传统应用持续增长 · DRAM 涨价让 RAM 冻结在 12 GB 附近 · 回收顶着缺口，直到顶不住",
         ha="center", fontsize=10.5, color="#555")

# ---------------------------------------------------------------- 图例（坐标轴下方）
handles = [
    Patch(facecolor=C_TRAD, alpha=0.55, label="传统应用"),
    Patch(facecolor=C_AI,   alpha=0.70, label="端侧 AI（1 模型 + KV）"),
    Line2D([0], [0], color=C_CAP, lw=2.4, label="LPDDR 容量（冻结）"),
    Line2D([0], [0], color=C_CAP, lw=1.6, linestyle=(0, (6, 4)), label="用户可用"),
    Line2D([0], [0], color=C_COUNTER, lw=1.6, linestyle=(0, (3, 4)),
           label="反事实：RAM 仍便宜时的容量"),
    Patch(facecolor=C_DEF, alpha=0.28, label="赤字（需求 > 用户可用，由回收吸收）"),
]
ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09),
          ncol=3, frameon=True, fontsize=9, handlelength=1.8, columnspacing=1.6)

# ---------------------------------------------------------------- 脚注
fig.text(0.075, 0.055,
         "中位旗舰 CAGR：传统 ~16%/年 · AI ~28%/年 · 总需求 ~19%/年 · "
         "实际容量 ~7%/年（2024–26 约为 0）· 反事实 ~19%/年。",
         fontsize=8, color=C_MUTED)
fig.text(0.075, 0.030,
         "来源：TrendForce、IDC、Counterpoint、GSMArena、wccftech 2025–26（见 §9）。2026.5 右侧为外推。",
         fontsize=8, color=C_MUTED)

# ---------------------------------------------------------------- 输出
# fig.savefig("memory-capacity-crunch-conflict.png", dpi=150)
# fig.savefig("memory-capacity-crunch-conflict.svg")
plt.show()
print("已输出 memory-capacity-crunch-conflict.png / .svg")
# plt.show()   # 交互查看可取消注释

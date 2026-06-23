#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「低端机视角」——低端 / 入门 Android 机的内存需求（内核+系统服务 + TOP 应用，
**不含端侧大模型**）vs 被价格 2026 守 8GB、2027 退回 6GB 并钉死的容量。低端机版，
对照旗舰版 memory-capacity-crunch-conflict。

需求自下而上堆叠两层：①内核+系统服务（底座，2026 见顶后随回退瘦身）、②TOP 应用
（Native 相机/图库/视频 + 三方超App/浏览器/社交/游戏，合并为一层）。两层之和即总需求，
与容量线对比：高出容量的部分就是赤字（由 zram 压缩 + lmkd 杀进程吸收）。

运行:
    pip install matplotlib numpy
    python memory-capacity-crunch-lowend-conflict.py
输出: 脚本所在目录下 memory-capacity-crunch-lowend-conflict.png / .svg

数字说明: 容量与工作集中位线均为**低端机视角的工程估算（待核实）**，锚定母文章已核实的
硬数据 —— Android 16 完整版门槛 6GB；移动 DRAM 合约价 ≈$3/GB(2023) → ≈$20/GB(2026Q2)；
厂商在涨价下"下调规格"。见 surveys/memory-capacity-crunch-CN.md §9。

中文字体: 下方 rcParams 已配置常见 CJK 字体回退链；若显示成方块，把系统中文字体名
加到 font.sans-serif 最前面（Windows 一般 'Microsoft YaHei'）。
"""

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# ---------------------------------------------------------------- 字体 / 全局样式（与旗舰版一致）
matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC",
    "Source Han Sans SC", "WenQuanYi Zen Hei", "sans-serif",
]
matplotlib.rcParams["axes.unicode_minus"] = False   # 负号用 ASCII，避免缺字
matplotlib.rcParams["svg.fonttype"] = "none"        # SVG 里保留文字（不转路径），可后期编辑

# ---------------------------------------------------------------- 配色
C_SYS    = "#a99a86"   # 内核 + 系统服务（底座，taupe）
C_APPS   = "#5589b8"   # TOP 应用（Native + 三方，合并为一层，蓝）
C_CAP    = "#1a4f7a"   # 容量（深蓝）
C_COUNTER= "#9aa6b2"   # 反事实（灰）
C_DEF    = "#d62828"   # 赤字（红）
C_CROSS  = "#b03030"   # 交叉点 / 赤字标注
C_PROJ   = "#f6f6f0"   # 外推区底色
C_TXT    = "#333333"
C_MUTED  = "#777777"

# ---------------------------------------------------------------- 数据（中位低端机，单位 GB；均为估算·待核实）
years     = np.array([2024, 2025, 2026, 2027, 2028], dtype=float)
native    = np.array([1.5, 1.7, 1.9, 2.1, 2.3])          # TOP-Native：相机/图库/视频（常驻大头）
third     = np.array([2.2, 2.7, 3.1, 3.5, 3.9])          # TOP-三方：超App/浏览器/社交/游戏
apps      = native + third                                # TOP 应用合计（合并为一层）= [3.7,4.4,5.0,5.6,6.2]
sys_floor = np.array([2.7, 2.8, 2.9, 2.6, 2.6])          # 内核+系统服务：2026 见顶，随回退（2026→2027）瘦身
capacity  = np.array([8.0, 8.0, 8.0, 6.0, 6.0])          # 容量：2026 守住 8 → 2027 退回 6 并钉死
demand    = sys_floor + apps                              # 总需求 = 底座 + TOP应用 = [6.4,7.2,7.9,8.2,8.8]
counterfactual = np.array([8.0, 9.0, 10.5, 12.0, 13.0])  # 反事实：若 RAM 仍便宜，低端也会跟着爬

PROJ_START = 2026.5   # 外推区起点


def first_crossing(x, upper, lower):
    """返回 upper 由下方穿到 lower 上方的首个交点 (x, y)。"""
    d = upper - lower
    for i in range(len(x) - 1):
        if d[i] <= 0 <= d[i + 1]:
            t = (0 - d[i]) / (d[i + 1] - d[i])
            return x[i] + t * (x[i + 1] - x[i]), lower[i] + t * (lower[i + 1] - lower[i])
    return None


x_cross, y_cross = first_crossing(years, demand, capacity)   # ≈ (2026.04, 7.91)

# ---------------------------------------------------------------- 画布
fig = plt.figure(figsize=(11.5, 7.8))
ax = fig.add_axes([0.075, 0.215, 0.86, 0.655])  # [left, bottom, width, height]

# 外推区底色（最底层）
ax.axvspan(PROJ_START, years[-1], color=C_PROJ, zorder=0)
ax.text((PROJ_START + years[-1]) / 2, 13.6, "外推区（2026.5 — 2028）",
        ha="center", va="top", fontsize=10, color=C_MUTED, zorder=1)

# 网格（数据之下）
ax.set_axisbelow(True)
ax.grid(axis="y", linestyle=(0, (2, 3)), color="#e6e6e6", linewidth=1)

# ---------------------------------------------------------------- 需求堆叠（自下而上）：内核+系统服务 → TOP应用
polys = ax.stackplot(years, sys_floor, apps, colors=[C_SYS, C_APPS], zorder=2)
polys[0].set_alpha(0.62)   # 内核+系统服务（底座）
polys[1].set_alpha(0.72)   # TOP 应用

# ---------------------------------------------------------------- 赤字楔形：总需求 > 容量（顶破天花板的部分）
ax.fill_between(years, demand, capacity, where=(demand >= capacity),
                interpolate=True, color=C_DEF, alpha=0.34, linewidth=0, zorder=3)

# ---------------------------------------------------------------- 容量线（2026 守 8 → 2027 退 6）+ 两段平台高亮
ax.plot(years[:3], capacity[:3], color=C_CAP, linewidth=6, alpha=0.26,
        solid_capstyle="round", zorder=3)                  # 2024–26 守住 8
ax.plot(years[3:], capacity[3:], color=C_CAP, linewidth=6, alpha=0.26,
        solid_capstyle="round", zorder=3)                  # 2027–28 钉死 6
ax.plot(years, capacity, color=C_CAP, linewidth=2.4, zorder=4)
ax.scatter(years, capacity, s=16, color=C_CAP, zorder=5)

# 反事实线（RAM 仍便宜）
ax.plot(years, counterfactual, color=C_COUNTER, linewidth=1.6,
        linestyle=(0, (3, 4)), zorder=4)

# 交叉点（总需求顶到容量）
ax.scatter([x_cross], [y_cross], s=48, color=C_CROSS, edgecolor="white",
           linewidth=1.5, zorder=6)
ax.text(2026.1, 7.35, "交叉点 ≈ 2026", fontsize=10,
        fontweight="bold", color="white", zorder=7)

# 8→6 回落标注（指向 2026→2027 陡降段）
ax.annotate("容量被迫退回：2026 守 8 → 2027 落 6", xy=(2026.5, 7.0), xytext=(2024.15, 5.2),
            fontsize=9.5, fontweight="bold", color=C_CAP,
            arrowprops=dict(arrowstyle="->", color=C_CAP, linewidth=1.5), zorder=7)

# ---------------------------------------------------------------- 系列内联标注
ax.text(2024.08, 1.25, "内核 + 系统服务 —— 底座（2026 见顶 → 2026–27 随回退瘦身：Go化裁剪·减预载·轻量皮肤）",
        fontsize=9.3, color="#4a4030", fontweight="bold", zorder=7)
ax.text(2024.08, 4.35, "TOP 应用 —— Native（相机/图库/视频）+ 三方（超App·浏览器/webview·社交·游戏）",
        fontsize=9.3, color="white", fontweight="bold", zorder=7)
ax.text(2024.08, 8.32, "低端 RAM 中位 —— 2026 守住 8 GB → 2027 退回 6 GB 并钉死",
        fontsize=10, fontweight="bold", color=C_CAP, zorder=7)

# 无大模型说明（旗舰版那条橙色 AI 层在这里消失）
ax.text(2024.12, 10.9, "注：无端侧大模型 —— 低端基本不上常驻模型，故无旗舰版的橙色 AI 层",
        fontsize=9.5, color=C_MUTED, zorder=7)

# 右侧端点标注
ax.text(2028.08, 6.0, "6 GB", fontsize=10, color=C_CAP, va="center")
ax.text(2027.62, 7.35, "总需求 8.8 GB", fontsize=9.5, color="white", va="center", fontweight="bold", zorder=7)
ax.text(2028.08, 13.0, "若 RAM 仍便宜", fontsize=9.5, color="#7a8694", va="center")
ax.text(2028.08, 12.05, "≈ 13 GB（低端跟涨）", fontsize=9.5, color="#7a8694", va="center")

# 赤字标注 + 指向楔形的箭头
ax.text(2026.55, 9.5, "赤字 = 塞不下的需求（应用挤爆 6 GB）",
        fontsize=11, fontweight="bold", color=C_CROSS, zorder=7)
ax.text(2026.55, 8.85, "→ zram 压缩 + lmkd 杀进程硬扛（杀得更早 · 热启动更慢 · 掉帧）",
        fontsize=9.5, color=C_CROSS, zorder=7)
ax.annotate("", xy=(2027.55, 7.1), xytext=(2027.2, 8.6),
            arrowprops=dict(arrowstyle="->", color=C_CROSS, linewidth=1.5), zorder=7)

# 应用可用提示（容量与底座之间的余量，2027 起被压到很小）
ax.text(2026.62, 5.65, "应用可用 = 容量 − 底座（2027 起仅 ~3.4 GB）",
        fontsize=9, color="white", fontweight="bold", zorder=7)

# 价格说明框（左上空白区）
callout = ("天花板为何回落 —— 是价格，不是物理\n"
           "移动 DRAM 合约价：≈\\$3/GB(2023) → ≈\\$20/GB(2026Q2)。\n"
           "低端最价格敏感，厂商直接砍规格：8 GB → 6 GB。")
ax.text(2024.12, 13.7, callout, fontsize=9.5, va="top", ha="left", linespacing=1.6,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff7f3", edgecolor="#d9a08c"),
        zorder=8)

# ---------------------------------------------------------------- 坐标轴
ax.set_xlim(2023.85, 2029.7)
ax.set_ylim(0, 14)
ax.set_xticks(years)
ax.set_xticklabels([int(y) for y in years])
ax.set_yticks([0, 2, 4, 6, 8, 10, 12, 14])
ax.set_xlabel("年份（中位低端机）", fontsize=11, color="#666")
ax.set_ylabel("内存（GB）", fontsize=11, color="#666")
ax.tick_params(colors=C_MUTED)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color("#888")

# ---------------------------------------------------------------- 标题 / 副标题
fig.text(0.5, 0.965, "挤压（低端机视角）：内核/系统 + TOP 应用 vs 8GB→6GB 回退的容量（2024–2028）",
         ha="center", fontsize=15, fontweight="bold", color="#222")
fig.text(0.5, 0.928, "容量 2026 守住 8GB、2027 落到 6GB 并钉死 · 内核/系统同步瘦身 · TOP 应用持续增长 · 缺口 2026 启动、2027 撕开",
         ha="center", fontsize=10.5, color="#555")

# ---------------------------------------------------------------- 图例（坐标轴下方）
handles = [
    Patch(facecolor=C_SYS,  alpha=0.62, label="内核 + 系统服务（底座，被瘦身）"),
    Patch(facecolor=C_APPS, alpha=0.72, label="TOP 应用（Native + 三方）"),
    Line2D([0], [0], color=C_CAP, lw=2.4, label="容量（2026 守 8 → 2027 落 6 钉死）"),
    Line2D([0], [0], color=C_COUNTER, lw=1.6, linestyle=(0, (3, 4)), label="反事实：RAM 仍便宜时的容量"),
    Patch(facecolor=C_DEF, alpha=0.34, label="赤字（需求 > 容量，由 zram+lmkd 吸收）"),
]
ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09),
          ncol=3, frameon=True, fontsize=9, handlelength=1.8, columnspacing=1.6)

# ---------------------------------------------------------------- 脚注
fig.text(0.075, 0.055,
         "低端中位 CAGR：TOP应用 ~13%/年（Native+三方）· 内核+系统服务 2026 见顶后瘦身（~0）· "
         "容量 2026 守 8 / 2027 落 6 钉死 · 反事实 ~13%/年。",
         fontsize=8, color=C_MUTED)
fig.text(0.075, 0.030,
         "数字为低端机视角的工程估算（待核实）；硬数据（Android16 6GB门槛 · DRAM ≈$3→$20/GB · 厂商下调规格）"
         "见母文章 memory-capacity-crunch §9。2026.5 右侧为外推。",
         fontsize=8, color=C_MUTED)

# ---------------------------------------------------------------- 输出（写到脚本所在目录，运行任一副本都会写到它自己旁边）
HERE = os.path.dirname(os.path.abspath(__file__))
fig.savefig(os.path.join(HERE, "memory-capacity-crunch-lowend-conflict.png"), dpi=150)
fig.savefig(os.path.join(HERE, "memory-capacity-crunch-lowend-conflict.svg"))
print("已输出 memory-capacity-crunch-lowend-conflict.png / .svg ->", HERE)
# plt.show()   # 交互查看可取消注释

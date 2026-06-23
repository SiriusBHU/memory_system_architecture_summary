#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「低端机视角」纯色块版 —— 与 memory-capacity-crunch-lowend-conflict 同数据，
去掉全部图内注释文字、标题、图例与灰色反事实虚线，只保留：需求堆叠（内核+系统服务 /
TOP 应用）、容量线、赤字楔形、坐标轴（刻度 + 轴标签）。
配色：内核+系统服务 = 浅绿 · TOP 应用 = 浅橙 · 赤字 = 浅红。

运行:
    pip install matplotlib numpy
    python memory-capacity-crunch-lowend-conflict-clean.py
输出: 脚本所在目录下 memory-capacity-crunch-lowend-conflict-clean.png / .svg

中文字体: 若显示成方块，把系统中文字体名加到 font.sans-serif 最前面（Windows 一般 'Microsoft YaHei'）。
"""

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- 字体 / 全局样式
matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC",
    "Source Han Sans SC", "WenQuanYi Zen Hei", "sans-serif",
]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["svg.fonttype"] = "none"

# ---------------------------------------------------------------- 配色（色块）
C_SYS  = "#a9ddb6"   # 内核 + 系统服务（浅绿）
C_APPS = "#f6c49b"   # TOP 应用（浅橙）
C_DEF  = "#f0a6a6"   # 赤字（浅红）
C_CAP  = "#1d3557"   # 容量线（藏青）
C_MUTED = "#888888"

# ---------------------------------------------------------------- 数据（中位低端机，单位 GB；估算·待核实）
years     = np.array([2024, 2025, 2026, 2027, 2028], dtype=float)
native    = np.array([1.5, 1.7, 1.9, 2.1, 2.3])          # TOP-Native：相机/图库/视频
third     = np.array([2.2, 2.7, 3.1, 3.5, 3.9])          # TOP-三方：超App/浏览器/社交/游戏
apps      = native + third                                # TOP 应用合计
sys_floor = np.array([2.7, 2.8, 2.9, 2.6, 2.6])          # 内核+系统服务
capacity  = np.array([8.0, 8.0, 8.0, 6.0, 6.0])          # 容量：2026 守 8 → 2027 落 6 钉死
demand    = sys_floor + apps                              # 总需求

# ---------------------------------------------------------------- 画布
fig = plt.figure(figsize=(11.5, 7.8))
ax = fig.add_axes([0.07, 0.09, 0.88, 0.87])  # 无标题/图例，图形区放大

# 网格（数据之下）
ax.set_axisbelow(True)
ax.grid(axis="y", linestyle=(0, (2, 3)), color="#e6e6e6", linewidth=1)

# 需求堆叠（自下而上）：内核+系统服务 → TOP 应用
polys = ax.stackplot(years, sys_floor, apps, colors=[C_SYS, C_APPS], zorder=2)
polys[0].set_alpha(0.90)
polys[1].set_alpha(0.90)

# 赤字楔形：总需求 > 容量
ax.fill_between(years, demand, capacity, where=(demand >= capacity),
                interpolate=True, color=C_DEF, alpha=0.92, linewidth=0, zorder=3)

# 容量线
ax.plot(years, capacity, color=C_CAP, linewidth=2.8, zorder=4)
ax.scatter(years, capacity, s=20, color=C_CAP, zorder=5)

# ---------------------------------------------------------------- 坐标轴
ax.set_xlim(2023.9, 2028.1)
ax.set_ylim(0, 10)
ax.set_xticks(years)
ax.set_xticklabels([int(y) for y in years])
ax.set_yticks([0, 2, 4, 6, 8, 10])
ax.set_xlabel("年份（中位低端机）", fontsize=11, color="#666")
ax.set_ylabel("内存（GB）", fontsize=11, color="#666")
ax.tick_params(colors=C_MUTED)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color("#888")

# ---------------------------------------------------------------- 输出（写到脚本所在目录）
HERE = os.path.dirname(os.path.abspath(__file__))
fig.savefig(os.path.join(HERE, "memory-capacity-crunch-lowend-conflict-clean.png"), dpi=150)
fig.savefig(os.path.join(HERE, "memory-capacity-crunch-lowend-conflict-clean.svg"))
print("已输出 memory-capacity-crunch-lowend-conflict-clean.png / .svg ->", HERE)
# plt.show()   # 交互查看可取消注释

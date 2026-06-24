#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「端侧三类任务的上下文叠加」图（agent-era-context-growth.svg）：
横轴年份(2024–2028)、纵轴累计上下文长度(tokens)，用**堆叠区域**描述三类端侧推理
任务的上下文需求如何逐层叠加，凸显两个负载特征 —— 异构(三类并存、各占一层) 与
增长(越晚出现的任务越重，把总上下文一路推高)。是母图「剪刀差」里激进需求线的微观来源。

三层（自下而上叠加；对数 y 轴上各边界为直线=指数增长）：
  ① 传统 LLM 任务    —— 文字润色/改写/祝福语等单点小颗粒；1k→4k；2024 起；打底
  ② 伴随态 Agent     —— 小艺伴随态 AI / GUI Agent，输入图+文；增量 0→16k；2025Q4–2026Q1 起
  ③ 后台长程 Agent   —— 手机端 Claw，复杂多模态；增量 0→128k；2026Q4–2027Q4 起
总高度 = 三层之和（同时常驻的上下文之和），2028 年约 ~148k。

运行:
    pip install matplotlib numpy
    python agent-era-context-growth.py
输出: 脚本所在目录下 agent-era-context-growth.png / .svg

数字说明: 上下文长度与起始时间均为**示意量级 / 窗口估计（待核实）**，用于刻画趋势而非
精确测量；后台长程 Agent 取较早起点(2026Q4)以展示其增长斜率，实际可能延后至 2027Q4。
中文字体: rcParams 已把本机 matplotlib 实际识别到的简体字体前置；若显示成方块，把系统
中文字体名加到 font.sans-serif 最前面（macOS 一般 'Hiragino Sans GB'，Windows 'Microsoft YaHei'）。
"""

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, FixedFormatter

# ---------------------------------------------------------------- 字体 / 全局样式
matplotlib.rcParams["font.sans-serif"] = [
    # 先放本机 matplotlib 实际识别到的简体中文字体（macOS），再接跨平台回退链
    "Hiragino Sans GB", "STHeiti", "Heiti TC", "Arial Unicode MS", "PingFang HK",
    "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC",
    "Source Han Sans SC", "WenQuanYi Zen Hei", "sans-serif",
]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["svg.fonttype"] = "none"        # SVG 里保留文字（不转路径），可后期编辑

# ---------------------------------------------------------------- 配色（略降饱和，偏柔）
C1      = "#7ba3cb"   # 传统 LLM（柔蓝，打底）
C2      = "#edbd88"   # 伴随态 Agent（柔橙）
C3      = "#dd928b"   # 后台长程 Agent（柔珊瑚红）
C1D     = "#3a6a93"   # 深一档，用于字
C2D     = "#9a6526"
C3D     = "#a8514a"
C_PROJ  = "#f6f6f0"   # 外推区底色
C_TXT   = "#3a3a3a"
C_MUTED = "#888888"

# ---------------------------------------------------------------- 三条累计边界（对数 y 轴上为直线段=指数增长）
xx = np.linspace(2024.0, 2028.0, 400)
ON2, ON3 = 2025.75, 2026.75        # 伴随态 / 后台长程 的增量起点（增量从 0 起）


def exp_seg(x, x0, y0, x1, y1):
    """对数轴上的直线 = 自然坐标系下的指数曲线，连接端点 (x0,y0)→(x1,y1)。"""
    t = (x - x0) / (x1 - x0)
    return y0 * (y1 / y0) ** t


base = exp_seg(xx, 2024.0, 1.0, 2028.0, 4.0)                                 # ① 传统：1k → 4k
y_on2 = exp_seg(ON2, 2024.0, 1.0, 2028.0, 4.0)                               # 伴随态起点处的基底值
comp_top = np.where(xx < ON2, base, exp_seg(xx, ON2, y_on2, 2028.0, 20.0))   # 基底 + 伴随态 → 20k
y_on3 = exp_seg(ON3, ON2, y_on2, 2028.0, 20.0)                               # 后台长程起点处的 comp_top 值
total = np.where(xx < ON3, comp_top, exp_seg(xx, ON3, y_on3, 2028.0, 148.0)) # 总计 → 148k

L1, L2, L3 = base, comp_top - base, total - comp_top                         # 各层（增量起点 = 0）
cum = np.vstack([base, comp_top, total])                                     # 各层累计上沿（直线段）

# ---------------------------------------------------------------- 画布
fig = plt.figure(figsize=(11.5, 7.6))
ax = fig.add_axes([0.085, 0.215, 0.80, 0.655])

# 外推区底色（最底层）
PROJ_START = 2026.5
ax.axvspan(PROJ_START, 2028.0, color=C_PROJ, zorder=0)
ax.text((PROJ_START + 2028.0) / 2, 185, "外推区（2026.5 — 2028）",
        ha="center", va="top", fontsize=10, color=C_MUTED, zorder=1)

# 网格（数据之下）
ax.set_axisbelow(True)
ax.grid(axis="y", linestyle=(0, (2, 3)), color="#ececec", linewidth=1)

# ---------------------------------------------------------------- 堆叠区域（自下而上：传统 → 伴随态 → 后台长程）
polys = ax.stackplot(xx, L1, L2, L3, colors=[C1, C2, C3], zorder=2)
for p, a in zip(polys, [0.82, 0.80, 0.76]):
    p.set_alpha(a)

# 层间细白分隔线 + 极淡顶沿（柔，不要硬描边）
ax.plot(xx, cum[0], color="white", linewidth=1.2, alpha=0.7, zorder=3)
ax.plot(xx, cum[1], color="white", linewidth=1.2, alpha=0.7, zorder=3)
ax.plot(xx, cum[2], color=C3D, linewidth=1.2, alpha=0.35, zorder=3)

# 起始竖向软标记（柔虚线）
ax.axvline(2025.75, color=C2D, linewidth=1.0, linestyle=(0, (2, 4)), alpha=0.45, zorder=4)
ax.axvline(2026.75, color=C3D, linewidth=1.0, linestyle=(0, (2, 4)), alpha=0.45, zorder=4)

# ---------------------------------------------------------------- 阅读提示框（左上空白区）：异构 + 叠加 + 增长
note = ("三类任务并存、上下文逐层叠加（异构）\n"
        "越晚出现的任务越重，把总上下文一路推高（增长）")
ax.text(2024.12, 185, note, fontsize=10, va="top", ha="left", color=C_TXT, linespacing=1.6,
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#fbfbf6", edgecolor="#dcdcd2"), zorder=8)

# 后台长程层标注（对数轴下红层偏窄，改用浮动箭注指向红区）
ax.annotate("③ 后台长程 Agent · 手机端 Claw（多模态）· 增量 →128k",
            xy=(2027.7, 45), xytext=(2024.9, 96),
            fontsize=9.5, fontweight="bold", color=C3D, zorder=8,
            arrowprops=dict(arrowstyle="->", color=C3D, linewidth=1.1, alpha=0.7))

# 增长箭注（指向总上沿的陡升段）
ax.annotate("增长 → 总需求约 148k", xy=(2027.92, 150), xytext=(2025.85, 52),
            fontsize=10, fontweight="bold", color=C3D, zorder=9,
            arrowprops=dict(arrowstyle="->", color=C3D, linewidth=1.3, alpha=0.8))

# ---------------------------------------------------------------- 右侧端点：各层贡献 + 合计
ax.text(2028.06, 2.0, "① 传统 ~4k", fontsize=9.5, color=C1D, va="center", fontweight="bold")
ax.text(2028.06, 9.0, "② 伴随态 +16k", fontsize=9.5, color=C2D, va="center", fontweight="bold")
ax.text(2028.06, 50, "③ 后台长程 +128k", fontsize=9.5, color=C3D, va="center", fontweight="bold")
ax.text(2028.06, 175, "合计 ≈ 148k", fontsize=10, color="#444", va="center", fontweight="bold")

# ---------------------------------------------------------------- 坐标轴（纵轴对数，单位 k tokens）
ax.set_xlim(2023.85, 2029.7)
ax.set_yscale("log")
ax.set_ylim(1, 220)
ax.set_xticks([2024, 2025, 2026, 2027, 2028])
ax.set_xticklabels([2024, 2025, 2026, 2027, 2028])
ax.yaxis.set_major_locator(FixedLocator([1, 2, 4, 8, 16, 32, 64, 128]))
ax.yaxis.set_major_formatter(FixedFormatter(["1k", "2k", "4k", "8k", "16k", "32k", "64k", "128k"]))
ax.yaxis.set_minor_locator(FixedLocator([]))   # 关掉对数轴默认次刻度
ax.set_xlabel("年份（端侧旗舰）", fontsize=11, color="#666")
ax.set_ylabel("累计上下文长度（tokens，对数轴）", fontsize=11, color="#666")
ax.tick_params(colors=C_MUTED)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color("#aaa")

# ---------------------------------------------------------------- 标题 / 副标题
fig.text(0.5, 0.965, "端侧推理的上下文叠加：三类任务的异构与增长（2024 — 2028）",
         ha="center", fontsize=15, fontweight="bold", color="#222")
fig.text(0.5, 0.928,
         "传统 LLM 打底，伴随态 Agent 与后台长程 Agent 作为增量逐层叠加 —— "
         "总上下文被最新最重的任务推高（→ ~148k）",
         ha="center", fontsize=10.5, color="#555")

# ---------------------------------------------------------------- 图例（坐标轴下方）
handles = [
    Patch(facecolor=C1, alpha=0.82, label="① 传统 LLM 任务（润色/改写/祝福语，1–4k 打底，2024 起）"),
    Patch(facecolor=C2, alpha=0.80, label="② 伴随态 Agent（小艺/GUI Agent，图+文，增量 →16k，2025Q4–2026Q1 起）"),
    Patch(facecolor=C3, alpha=0.76, label="③ 后台长程 Agent（手机端 Claw，多模态，增量 →128k，2026Q4–2027Q4 起）"),
]
ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.10),
          ncol=1, frameon=True, fontsize=9, handlelength=1.8)

# ---------------------------------------------------------------- 脚注
fig.text(0.085, 0.050,
         "读法：三类任务并存、上下文逐层叠加（stack）。传统 LLM 打底，伴随态 / 后台长程作为增量摞在其上；"
         "总高度 = 同时常驻的上下文之和。",
         fontsize=8, color=C_MUTED)
fig.text(0.085, 0.026,
         "上下文为示意量级、起始为窗口估计（待核实）；后台长程取较早起点(2026Q4)以示斜率，"
         "实际可能延后至 2027Q4。2026.5 右侧为外推。",
         fontsize=8, color=C_MUTED)

# ---------------------------------------------------------------- 输出（写到脚本所在目录）
HERE = os.path.dirname(os.path.abspath(__file__))
fig.savefig(os.path.join(HERE, "agent-era-context-growth.png"), dpi=150)
fig.savefig(os.path.join(HERE, "agent-era-context-growth.svg"))
print("已输出 agent-era-context-growth.png / .svg ->", HERE)
# plt.show()

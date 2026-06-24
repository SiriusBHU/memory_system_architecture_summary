#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「端侧三类任务的上下文叠加」图（agent-era-context-growth.svg）：
横轴年份(2024–2028)、纵轴累计上下文长度(tokens)，用**堆叠区域**描述三类端侧推理
任务的上下文需求如何逐层叠加，凸显两个负载特征 —— 异构(三类并存、各占一层) 与
增长(越晚出现的任务越重，把总上下文一路推高)。是母图「剪刀差」里激进需求线的微观来源。

三层（自下而上叠加）：
  ① 传统 LLM 任务    —— 文字润色/改写/祝福语等单点小颗粒；0.5k→4k；2024 起；打底
  ② 伴随态 Agent     —— 小艺伴随态 AI / GUI Agent，输入图+文；增量 →16k；2025Q4–2026Q1 起
  ③ 后台长程 Agent   —— 手机端 Claw，复杂多模态；增量 →128k；2026Q4–2027Q4 起
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

# ---------------------------------------------------------------- 三层增量（共用细网格），单位 k tokens
xx = np.linspace(2024.0, 2028.0, 400)


def smooth(y, win=25):
    """轻度滑动平均：软化插值折角与起始拐点，让边界更柔。"""
    yp = np.pad(y, (win // 2, win // 2), mode="edge")
    return np.convolve(yp, np.ones(win) / win, mode="valid")[:len(y)]


base = np.interp(xx, [2024, 2025, 2026, 2027, 2028], [1.0, 2.0, 3.0, 3.5, 4.0])     # ① 传统：0.5→4k 打底
inc2 = np.interp(xx, [2025.75, 2026, 2026.5, 2027, 2027.5, 2028],
                 [0.5, 1, 3, 8, 12, 16])                                            # ② 伴随态增量 →16k
inc3 = np.interp(xx, [2026.75, 2027, 2027.4, 2027.7, 2028],
                 [0.5, 4, 16, 48, 128])                                            # ③ 后台长程增量 →128k

base_s = smooth(base)
inc2_s = np.where(xx < 2025.75, 0.0, smooth(np.where(xx < 2025.75, 0.0, inc2)))     # 起始前为 0，软化后再夹回
inc3_s = np.where(xx < 2026.75, 0.0, smooth(np.where(xx < 2026.75, 0.0, inc3)))
cum = np.cumsum(np.vstack([base_s, inc2_s, inc3_s]), axis=0)                        # 各层累计上沿

# ---------------------------------------------------------------- 画布
fig = plt.figure(figsize=(11.5, 7.6))
ax = fig.add_axes([0.085, 0.215, 0.80, 0.655])

# 外推区底色（最底层）
PROJ_START = 2026.5
ax.axvspan(PROJ_START, 2028.0, color=C_PROJ, zorder=0)
ax.text((PROJ_START + 2028.0) / 2, 153, "外推区（2026.5 — 2028）",
        ha="center", va="top", fontsize=10, color=C_MUTED, zorder=1)

# 网格（数据之下）
ax.set_axisbelow(True)
ax.grid(axis="y", linestyle=(0, (2, 3)), color="#ececec", linewidth=1)

# ---------------------------------------------------------------- 堆叠区域（自下而上：传统 → 伴随态 → 后台长程）
polys = ax.stackplot(xx, base_s, inc2_s, inc3_s, colors=[C1, C2, C3], zorder=2)
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
ax.text(2024.12, 146, note, fontsize=10, va="top", ha="left", color=C_TXT, linespacing=1.6,
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#fbfbf6", edgecolor="#dcdcd2"), zorder=8)

# 大色块内联标注（红层够厚，直接写在里面）
ax.text(2027.04, 74, "③ 后台长程 Agent", fontsize=11, fontweight="bold", color=C3D, zorder=8)
ax.text(2027.04, 65, "手机端 Claw（复杂多模态）· 增量 →128k", fontsize=9.3, color=C3D, zorder=8)

# 增长箭注（指向总上沿的陡升段）
ax.annotate("增长 → 总需求约 148k", xy=(2027.85, 144), xytext=(2025.95, 116),
            fontsize=10, fontweight="bold", color=C3D, zorder=9,
            arrowprops=dict(arrowstyle="->", color=C3D, linewidth=1.3, alpha=0.8))

# ---------------------------------------------------------------- 右侧端点：各层贡献 + 合计
ax.text(2028.06, 3.5, "① 传统 ~4k", fontsize=9.5, color=C1D, va="center", fontweight="bold")
ax.text(2028.06, 12, "② 伴随态 +16k", fontsize=9.5, color=C2D, va="center", fontweight="bold")
ax.text(2028.06, 84, "③ 后台长程 +128k", fontsize=9.5, color=C3D, va="center", fontweight="bold")
ax.text(2028.06, 147, "合计 ≈ 148k", fontsize=10, color="#444", va="center", fontweight="bold")

# ---------------------------------------------------------------- 坐标轴（线性，单位 k tokens）
ax.set_xlim(2023.85, 2029.7)
ax.set_ylim(0, 158)
ax.set_xticks([2024, 2025, 2026, 2027, 2028])
ax.set_xticklabels([2024, 2025, 2026, 2027, 2028])
ax.yaxis.set_major_locator(FixedLocator([0, 16, 32, 64, 96, 128]))
ax.yaxis.set_major_formatter(FixedFormatter(["0", "16k", "32k", "64k", "96k", "128k"]))
ax.set_xlabel("年份（端侧旗舰）", fontsize=11, color="#666")
ax.set_ylabel("累计上下文长度（tokens）", fontsize=11, color="#666")
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
    Patch(facecolor=C1, alpha=0.82, label="① 传统 LLM 任务（润色/改写/祝福语，0.5–4k 打底，2024 起）"),
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

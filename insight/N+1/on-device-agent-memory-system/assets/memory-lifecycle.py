#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「一条记忆的一生 + 一次命中」走通图（配合正文 §9 worked example）。

左panel = 写入路径（自下而上沉淀晋升）：一次问答 → STM(7页FIFO) → MTM(话题段, Heat累积)
          → LPM(永久画像)。以「用户对花生过敏」这条事实为例标注每一步的数据与触发条件。
右panel = 读取路径（三级召回，不重放全历史）：Day30 新问题分别命中三层，合并注入 LLM 生成
          个性化回复。重点画出 STM 全取 / MTM 两阶段 top-m→top-k / LPM 每类 top-10。

数据来源: MemoryOS / "Memory OS of AI Agent" (Kang et al., 2025), arXiv 2506.06326,
          EMNLP 2025 Oral. https://arxiv.org/abs/2506.06326
          （STM=7页、θ=0.6、Heat=N_visit+L_interaction+R_recency、τ=5、top-m=5/top-k=5–10、LPM每类top-10）

运行:
    pip install matplotlib
    python memory-lifecycle.py
输出: 脚本所在目录下 memory-lifecycle.png / .svg
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

# ----- 配色（与 memoryos-arch.py 保持一致：三级记忆由浅入深）-----
C_STM   = "#9ec6e8"   # 短期（浅蓝）
C_MTM   = "#edbd88"   # 中期（橙）
C_LPM   = "#c9a6d6"   # 长期画像（紫）
C_GEN   = "#8fbf9f"   # 生成（绿）
C_QA    = "#f3efe6"   # 问答 / 查询（米）
C_BOX   = "#fbfbf6"
C_EDGE  = "#cfcfc4"
C_TXT   = "#333333"
C_MUTED = "#888888"
C_HOT   = "#b5402f"
E_STM, E_MTM, E_LPM, E_GEN = "#7aa8cf", "#d9a05f", "#a87bbd", "#3a6b48"

fig, ax = plt.subplots(figsize=(15.4, 9.6))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, color, ec=C_EDGE, lw=1.2, r=0.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={r}",
                                facecolor=color, edgecolor=ec, linewidth=lw, zorder=2))


def txt(x, y, s, fs=8.6, color=C_TXT, bold=False, ha="left", va="center"):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color,
            fontweight="bold" if bold else "normal", zorder=4)


def arrow(x0, y0, x1, y1, color="#666", lw=1.8, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=15,
                                 color=color, linewidth=lw,
                                 connectionstyle=f"arc3,rad={rad}", zorder=3,
                                 shrinkA=2, shrinkB=2))


def alabel(x, y, s, color, fs=8.2):
    ax.text(x, y, s, ha="center", va="center", fontsize=fs, color=color, zorder=5,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=color, lw=0.8, alpha=0.95))


# ===== 总标题 =====
ax.text(50, 97.4, "一条记忆的一生 + 一次命中（以「用户对花生过敏」为例）",
        ha="center", fontsize=16, fontweight="bold", color="#222")
ax.text(50, 93.8, "左：写入路径（自下而上沉淀晋升）    右：读取路径（三级召回，不重放全历史）",
        ha="center", fontsize=10, color=C_MUTED)

# 中线
ax.plot([50, 50], [6, 91], color="#e3e0d6", lw=1.2, ls=(0, (4, 4)), zorder=1)

# ===================================================================
# 左 panel —— 写入路径（自下而上）
# ===================================================================
LX, LW = 3.5, 35
ax.text(LX + LW / 2, 90.5, "① 写入：一条记忆的一生", ha="center", fontsize=12,
        fontweight="bold", color="#444")

# --- 问答（底，Day1）---
box(LX, 13, LW, 11, C_QA, ec="#cbbf9b")
txt(LX + LW / 2, 21.6, "Day1 10:00 · 一次问答", fs=9, bold=True, ha="center", color="#7a6a36")
txt(LX + LW / 2, 18.4, "用户：我对花生过敏，帮我规划下周食谱", fs=7.8, ha="center")
txt(LX + LW / 2, 15.6, "助理：好的，已避开花生……", fs=7.8, ha="center", color=C_MUTED)

# --- STM ---
box(LX, 32, LW, 11.5, C_STM, ec=E_STM)
txt(LX + 1.8, 40.8, "STM 短期记忆", fs=10, bold=True, color="#2f5f86")
txt(LX + 1.8, 37.8, "7 页 FIFO（当前工作集 = KV Cache）", fs=7.8)
# 7 个页格，最后一个高亮为新页
for i in range(7):
    px = LX + 1.8 + i * 4.5
    hot = (i == 6)
    ax.add_patch(FancyBboxPatch((px, 33.2), 3.9, 2.4, boxstyle="round,pad=0.02,rounding_size=0.3",
                                facecolor="#fff6d8" if hot else "white",
                                edgecolor=C_HOT if hot else E_STM,
                                linewidth=1.3 if hot else 1.0, zorder=3))
    txt(px + 1.95, 34.4, f"P{i+1}", fs=7, ha="center",
        color=C_HOT if hot else "#2f5f86", bold=hot)

# --- MTM ---
box(LX, 51.5, LW, 16, C_MTM, ec=E_MTM)
txt(LX + 1.8, 64.6, "MTM 中期记忆", fs=10, bold=True, color="#9c6b2e")
txt(LX + 1.8, 61.8, "同话题页按 θ=0.6 聚成 Segment", fs=7.8)
# 「饮食」段高亮
box(LX + 1.8, 53.2, LW - 3.6, 7.0, "white", ec=C_HOT, lw=1.4)
txt(LX + 3.2, 58.5, "Segment「饮食/体质」", fs=8.2, bold=True, color="#9c6b2e")
txt(LX + 3.2, 56.2, "Heat = N_visit 2 + 页数 3 + recency 0.99", fs=7.3)
txt(LX + 3.2, 54.1, "= 5.99  >  τ=5  → 达标晋升", fs=7.6, bold=True, color=C_HOT)

# --- LPM ---
box(LX, 75, LW, 12, C_LPM, ec=E_LPM)
txt(LX + LW / 2, 84.3, "LPM 长期画像记忆（永久）", fs=10, bold=True, color="#6f4a86", ha="center")
box(LX + 1.8, 76.4, LW - 3.6, 6.0, "white", ec=E_LPM)
txt(LX + LW / 2, 80.4, "User KB ←「用户对花生过敏」定居", fs=8.4, bold=True, ha="center", color="#6f4a86")
txt(LX + LW / 2, 78, "STM/MTM 再换血也不丢", fs=7.6, ha="center", color=C_MUTED)

# 写入箭头（向上）
arrow(LX + LW / 2, 24, LX + LW / 2, 32, color="#7a6a36", lw=2.0)
alabel(LX + LW + 1.5, 28, "打包成\nDialogue Page", "#7a6a36", fs=7.6)
arrow(LX + LW / 2, 43.5, LX + LW / 2, 51.5, color=E_MTM, lw=2.0)
alabel(LX + LW + 1.5, 47.5, "满 7 页\nFIFO 挤出最旧页", E_MTM, fs=7.6)
arrow(LX + LW / 2, 67.5, LX + LW / 2, 75, color=E_LPM, lw=2.0)
alabel(LX + LW + 1.5, 71.3, "Heat>τ=5\n换页晋升", E_LPM, fs=7.6)

# ===================================================================
# 右 panel —— 读取路径（自上而下 fan-out + 合并）
# ===================================================================
RX, RW = 54, 42
ax.text(RX + RW / 2, 90.5, "② 读取：一次命中（三级召回）", ha="center", fontsize=12,
        fontweight="bold", color="#444")

# --- 新问题（顶）---
box(RX + 6, 81, RW - 12, 7, C_QA, ec="#cbbf9b")
txt(RX + RW / 2, 85.6, "Day30 · 新问题", fs=9, bold=True, ha="center", color="#7a6a36")
txt(RX + RW / 2, 82.8, "「周末家庭聚餐，推荐几道菜」", fs=8, ha="center")

# --- 三级召回盒 ---
tier_y = {"STM": 66, "MTM": 49.5, "LPM": 35}
# STM
box(RX, tier_y["STM"], RW, 9.5, "#eef5fb", ec=E_STM)
txt(RX + 1.6, tier_y["STM"] + 6.8, "STM · 不匹配，取全部 7 页", fs=8.6, bold=True, color="#2f5f86")
txt(RX + 1.6, tier_y["STM"] + 3.6, "直接带上最近上下文（直近几轮）", fs=7.8)
txt(RX + 1.6, tier_y["STM"] + 1.3, "→ 最近的对话语境", fs=7.6, color=C_MUTED)
# MTM
box(RX, tier_y["MTM"], RW, 12, "#fdf3e8", ec=E_MTM)
txt(RX + 1.6, tier_y["MTM"] + 9.2, "MTM · 两阶段排序收窄", fs=8.6, bold=True, color="#9c6b2e")
txt(RX + 1.6, tier_y["MTM"] + 6.4, "① query×段中心 → top-m=5 段", fs=7.8)
txt(RX + 1.6, tier_y["MTM"] + 4.0, "② 段内 query×页 → top-k=5–10 页", fs=7.8)
txt(RX + 1.6, tier_y["MTM"] + 1.5, "→ 命中那页「不爱吃香菜」", fs=7.6, color=C_HOT)
# LPM
box(RX, tier_y["LPM"], RW, 9.5, "#f7f0fb", ec=E_LPM)
txt(RX + 1.6, tier_y["LPM"] + 6.8, "LPM · 每类 top-10 语义匹配", fs=8.6, bold=True, color="#6f4a86")
txt(RX + 1.6, tier_y["LPM"] + 3.6, "User KB / Traits / Agent Persona", fs=7.8)
txt(RX + 1.6, tier_y["LPM"] + 1.3, "→ 命中「对花生过敏」", fs=7.6, color=C_HOT)

# 新问题 → 三级（fan-out 虚线）
for k, c, rad in [("STM", E_STM, -0.05), ("MTM", E_MTM, 0.18), ("LPM", E_LPM, 0.30)]:
    arrow(RX + 6, 82.5, RX + RW, tier_y[k] + (9.5 if k != "MTM" else 12),
          color=c, lw=1.3, rad=rad)
ax.text(RX + RW + 0.2, 78, "fan-out\n查询", ha="left", va="center", fontsize=7.4,
        color=C_MUTED, zorder=5)

# --- Generation 合并 ---
box(RX + 6, 20, RW - 12, 8, C_GEN, ec=E_GEN)
txt(RX + RW / 2, 24, "Generation · 三级合并注入 LLM", fs=8.8, bold=True, ha="center", color="#22512f")

# 三级 → Generation（merge）
for k, c in [("STM", E_STM), ("MTM", E_MTM), ("LPM", E_LPM)]:
    arrow(RX + 2, tier_y[k], RX + RW / 2 - 4, 28, color=c, lw=1.3, rad=0.12)

# Generation → 回复
arrow(RX + RW / 2, 20, RX + RW / 2, 15.5, color=E_GEN, lw=2.0)
box(RX + 4, 8, RW - 8, 6.5, "#f3f7f3", ec="#bcd")
txt(RX + RW / 2, 11.2, "个性化回复：推荐 ○○、△△", fs=8.4, bold=True, ha="center", color="#22512f")
txt(RX + RW / 2, 9.2, "（避开花生 · 少放香菜）", fs=7.6, ha="center", color=C_MUTED)

# ===== 页脚说明 =====
ax.text(50, 3.2,
        "对比：原始方案把全历史(~9K token)重放回 prompt；演进方案只注入命中的几页+画像几行 "
        "→ token 省 70~90% · p95 延迟 降 91%，精度反升（LoCoMo +26%~+49%）",
        ha="center", fontsize=8.2, color=C_MUTED)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "memory-lifecycle.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "memory-lifecycle.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: memory-lifecycle.png / .svg")

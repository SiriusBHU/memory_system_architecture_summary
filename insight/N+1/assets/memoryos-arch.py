#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制「MemoryOS：分层记忆系统结构」架构图（EMNLP 2025 Oral）。

把 OS 的分层存储 + 换页搬到 Agent 记忆：最小单元是一次问答(Dialogue Page)。
三级存储 STM(7页FIFO) → MTM(段, θ=0.6, ≤200段, Heat) → LPM(画像)，
四模块 Storage/Updating/Retrieval/Generation 驱动写入、晋升、检索、生成。

数据来源: MemoryOS / "Memory OS of AI Agent" (Kang et al., 2025), arXiv 2506.06326,
          EMNLP 2025 Oral. https://arxiv.org/abs/2506.06326

运行:
    pip install matplotlib
    python memoryos-arch.py
输出: 脚本所在目录下 memoryos-arch.png / .svg
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

# ----- 配色（三级记忆由浅入深）-----
C_STM   = "#9ec6e8"   # 短期（浅蓝）
C_MTM   = "#edbd88"   # 中期（橙）
C_LPM   = "#c9a6d6"   # 长期画像（紫）
C_MOD   = "#8fbf9f"   # 模块（绿）
C_BOX   = "#fbfbf6"
C_EDGE  = "#cfcfc4"
C_TXT   = "#333333"
C_MUTED = "#888888"

fig, ax = plt.subplots(figsize=(14.5, 10.2))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, color, text, fs=9.5, bold=False, ec=C_EDGE, tc=C_TXT, align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.8",
                                facecolor=color, edgecolor=ec, linewidth=1.2, zorder=2))
    ha = {"center": "center", "left": "left"}[align]
    tx = x + w / 2 if align == "center" else x + 1.5
    ax.text(tx, y + h / 2, text, ha=ha, va="center",
            fontsize=fs, color=tc, fontweight="bold" if bold else "normal", zorder=3)


def arrow(x0, y0, x1, y1, label="", color="#666", style="-|>", lw=1.6, fs=8.8,
          lx=None, ly=None, tc=None, rad=0.0):
    cs = f"arc3,rad={rad}"
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=15, color=color, linewidth=lw,
                                 connectionstyle=cs, zorder=4, shrinkA=0, shrinkB=0))
    if label:
        ax.text(lx if lx is not None else (x0 + x1) / 2,
                ly if ly is not None else (y0 + y1) / 2,
                label, ha="center", va="center", fontsize=fs, color=tc or color,
                zorder=5, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))


# ===== 标题 =====
ax.text(50, 97.6, "MemoryOS：分层记忆系统结构（EMNLP 2025）",
        ha="center", fontsize=16, fontweight="bold", color="#222")
ax.text(50, 93.8, "最小单元 = 一次问答 Dialogue Page · 三级存储 + 热度换页 · 四模块驱动写入/晋升/检索/生成",
        ha="center", fontsize=10, color=C_MUTED)

# ===== 左侧主干：三级存储（自上而下沉淀）=====
LX, LW = 6, 50

# --- STM ---
box(LX, 79, LW, 11, C_STM, "", ec="#7aa8cf")
ax.text(LX + 2, 87.5, "STM 短期记忆", ha="left", fontsize=11, fontweight="bold", color="#2f5f86")
ax.text(LX + 2, 84.4, "7 页 FIFO 队列（满则挤出最旧页）", ha="left", fontsize=8.8, color=C_TXT)
ax.text(LX + 2, 81.4, "Dialogue Page = { Q 查询, R 回复, T 时间戳, meta_chain 对话链 }",
        ha="left", fontsize=8.2, color=C_MUTED)
# 7 个页格
for i in range(7):
    px = LX + 2 + i * 6.6
    ax.add_patch(FancyBboxPatch((px, 76.2), 5.6, 2.0, boxstyle="round,pad=0.02,rounding_size=0.3",
                                facecolor="white", edgecolor="#7aa8cf", linewidth=1.0, zorder=3))
    ax.text(px + 2.8, 77.2, f"P{i+1}", ha="center", va="center", fontsize=7.5, color="#2f5f86")

# --- MTM ---
box(LX, 52, LW, 19, C_MTM, "", ec="#d9a05f")
ax.text(LX + 2, 68.2, "MTM 中期记忆", ha="left", fontsize=11, fontweight="bold", color="#9c6b2e")
ax.text(LX + 2, 65.2, "≤ 200 个 Segment；同话题页按相似度 θ=0.6 聚段", ha="left", fontsize=8.6, color=C_TXT)
# 几个段
for i in range(4):
    sx = LX + 2 + i * 11.8
    ax.add_patch(FancyBboxPatch((sx, 56.5), 10.6, 6.2, boxstyle="round,pad=0.02,rounding_size=0.4",
                                facecolor="white", edgecolor="#d9a05f", linewidth=1.0, zorder=3))
    ax.text(sx + 5.3, 60.8, f"Segment {i+1}", ha="center", va="center", fontsize=7.8,
            color="#9c6b2e", fontweight="bold")
    ax.text(sx + 5.3, 58.2, f"Heat={3+i*2}", ha="center", va="center", fontsize=7.5,
            color="#b5402f" if (3 + i * 2) > 5 else C_MUTED)
ax.text(LX + 2, 54, "Heat 超阈值 τ=5 的段 → 晋升进 LPM（换页）", ha="left", fontsize=8.2,
        color="#b5402f", fontweight="bold")

# --- LPM ---
box(LX, 30, LW, 18, C_LPM, "", ec="#a87bbd")
ax.text(LX + 2, 45.2, "LPM 长期画像记忆", ha="left", fontsize=11, fontweight="bold", color="#6f4a86")
box(LX + 2, 33, 22.5, 9.5, "white", "", ec="#a87bbd")
ax.text(LX + 13, 40.6, "User Persona 用户画像", ha="center", fontsize=8.6, fontweight="bold", color="#6f4a86")
ax.text(LX + 13, 37.8, "静态档案（姓名/性别/出生年）", ha="center", fontsize=7.6, color=C_TXT)
ax.text(LX + 13, 35.8, "User KB 100 条 FIFO", ha="center", fontsize=7.6, color=C_TXT)
ax.text(LX + 13, 34, "User Traits 90 维（3 类）", ha="center", fontsize=7.6, color=C_TXT)
box(LX + 26, 33, 22, 9.5, "white", "", ec="#a87bbd")
ax.text(LX + 37, 40.6, "Agent Persona 智能体画像", ha="center", fontsize=8.6, fontweight="bold", color="#6f4a86")
ax.text(LX + 37, 37.8, "角色/性格档案", ha="center", fontsize=7.6, color=C_TXT)
ax.text(LX + 37, 35.4, "Agent Traits 100 条 FIFO", ha="center", fontsize=7.6, color=C_TXT)

# 晋升箭头（向下沉淀）
arrow(LX + LW - 6, 79, LX + LW - 6, 71, color="#9c6b2e", lw=2.0,
      label="FIFO 迁出\n话题链归并", lx=LX + LW + 5.5, ly=75, tc="#9c6b2e")
arrow(LX + LW - 6, 52, LX + LW - 6, 48, color="#6f4a86", lw=2.0,
      label="Heat>τ=5\n晋升换页", lx=LX + LW + 5.5, ly=50, tc="#6f4a86")

# ===== 右侧：四模块 =====
RX = 70
ax.text(RX + 13, 90, "四个功能模块", ha="center", fontsize=11, fontweight="bold", color="#3a6b48")
box(RX, 84.5, 26, 4.2, C_MOD, "Storage 存储：三级分层组织", fs=8.8, bold=True)
box(RX, 79.3, 26, 4.2, C_MOD, "Updating 更新：FIFO 迁出 + Heat 换页", fs=8.6, bold=True)
box(RX, 74.1, 26, 4.2, C_MOD, "Retrieval 检索：三级召回", fs=8.8, bold=True)
box(RX, 68.9, 26, 4.2, C_MOD, "Generation 生成：拼装 prompt", fs=8.8, bold=True)

# 检索规则
box(RX, 47, 26, 19, C_BOX, "", ec=C_EDGE)
ax.text(RX + 13, 63.4, "检索规则（三级召回）", ha="center", fontsize=9.2, fontweight="bold", color="#3a6b48")
ax.text(RX + 1.5, 60.2, "• STM：取全部 7 页", ha="left", fontsize=8.4, color=C_TXT)
ax.text(RX + 1.5, 57, "• MTM：两阶段", ha="left", fontsize=8.4, color=C_TXT)
ax.text(RX + 3.5, 54.4, "top-m=5 段 → top-k=5–10 页", ha="left", fontsize=8.0, color=C_MUTED)
ax.text(RX + 1.5, 51.4, "• LPM：每类 top-10 语义匹配", ha="left", fontsize=8.4, color=C_TXT)
ax.text(RX + 1.5, 48.6, "→ 合并注入 LLM 上下文", ha="left", fontsize=8.4, color="#3a6b48", fontweight="bold")

# Heat 公式框
box(RX, 30, 26, 14, "#fdf3f1", "", ec="#e0b0a8")
ax.text(RX + 13, 41.5, "Heat 晋升公式", ha="center", fontsize=9.2, fontweight="bold", color="#b5402f")
ax.text(RX + 13, 37.8, "Heat = N_visit + L_interaction + R_recency", ha="center", fontsize=8.3, color=C_TXT)
ax.text(RX + 13, 35, "R_recency = exp(-Δt / μ),  μ=1e7 s", ha="center", fontsize=8.0, color=C_MUTED)
ax.text(RX + 13, 32, "权重 α=β=γ=1；阈值 τ=5", ha="center", fontsize=8.0, color=C_MUTED)

# 检索：三级 -> Retrieval 模块（虚线汇聚）
arrow(LX + LW, 84.5, RX, 76.2, color="#7aa8cf", lw=1.2, style="-|>", rad=-0.15)
arrow(LX + LW, 61, RX, 75.5, color="#d9a05f", lw=1.2, style="-|>", rad=-0.18)
arrow(LX + LW, 39, RX, 74.8, color="#a87bbd", lw=1.2, style="-|>", rad=-0.22)
ax.text(LX + LW + 6.5, 68, "检索召回", ha="center", fontsize=8.0, color=C_MUTED,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

# Generation -> 用户
arrow(RX + 13, 68.9, RX + 13, 66.5, color="#3a6b48", lw=1.6, style="-|>")
ax.text(RX + 13, 24.5, "→ 个性化回复", ha="center", fontsize=9, color="#3a6b48", fontweight="bold")

# 写入：用户对话 -> STM
arrow(2.5, 92, 6, 86, color="#2f5f86", lw=1.6, style="-|>")
ax.text(2.5, 94, "用户对话", ha="center", fontsize=8.6, color="#2f5f86", fontweight="bold")

# ===== 页脚：性能 =====
box(18, 6, 64, 8.5, "#f3f7f3", "", ec="#bcd")
ax.text(50, 11.5, "LoCoMo 超长对话基准（GPT-4o-mini）", ha="center", fontsize=9.5,
        fontweight="bold", color="#3a6b48")
ax.text(50, 8.2, "F1  +49.11%    ·    BLEU-1  +46.18%    （相对基线，约 300 轮 / ~9K token 对话）",
        ha="center", fontsize=9, color=C_TXT)

ax.text(2, 1.5, "图例： 蓝=短期(STM)  橙=中期(MTM)  紫=长期画像(LPM)  绿=功能模块；向下箭头=沉淀晋升，斜箭头=检索召回",
        ha="left", fontsize=7.8, color=C_MUTED)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "memoryos-arch.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "memoryos-arch.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: memoryos-arch.png / .svg")

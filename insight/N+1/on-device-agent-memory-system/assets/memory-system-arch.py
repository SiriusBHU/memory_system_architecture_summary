#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端侧 Agent OS 完整记忆系统架构图（统合两篇调研：明文记忆系统 + Prefix Cache 笔记）。

一句话主旨：Agent 记忆按「载体」分两类，组织与管理方式完全不同，
但最终拼接成同一条上下文（token 序列），中间隔着一条「命脉边界」：

  ┌ 静态前缀区  ── KV Cache 记忆（激活载体）── Prefix Cache 阶段 ┐
  │   system prompt + skill 清单（根，全员共享，位置固定）        │
  │   选中的 skill X · 完整 prompt（分支，按需 restore）          │
  ├ 命脉边界：以上逐字节一致 + 绝对位置固定；以下不缓存、不可上移 ┤
  │   检索到的明文记忆（STM 近况 + MTM 情景 + LPM 画像）          │
  │   当前对话历史 + 新输入（动态尾巴，每轮只 prefill 这段）       │
  └ 动态尾巴区  ── 明文记忆（明文外置载体）── Prompt 拼装 阶段 ──┘

左栏 = KV Cache 记忆的组织/管理：前缀树(system 根 + skill 分支) + 内容寻址 + 两级常驻。
右栏 = 明文记忆的组织/管理：MemoryOS 三级 STM→MTM→LPM（短/中/长期），细粒度展开。
底部桥：MemOS MemCube 把「热点明文记忆」提升注入为「激活(KV)」，接通两类载体。

数据来源:
  MemoryOS (arXiv 2506.06326, EMNLP 2025 Oral) —— STM 7 页 / θ=0.6 / Heat / τ=5 / top-m,k
  MemOS    (arXiv 2507.03724) —— MemCube 三型记忆（参数/激活/明文）与提升/降级
  Mem0     (arXiv 2504.19413) —— 扁平向量库 + LLM 抽取整合
  prefix-cache-agent-notes.md —— 前缀树缓存、内容寻址、命脉约束、两级常驻

运行:
    pip install matplotlib
    python memory-system-arch.py
输出: 脚本所在目录下 memory-system-arch.png / .svg
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

# ----- 配色（与 memoryos-arch / memory-lifecycle / memory-taxonomy 一致）-----
C_KV    = "#dff1ea"; E_KV   = "#0f6e56"; T_KV  = "#085041"   # KV/静态（绿）
C_STM   = "#9ec6e8"; E_STM  = "#7aa8cf"; T_STM = "#2f5f86"   # 短期（蓝）
C_MTM   = "#edbd88"; E_MTM  = "#d9a05f"; T_MTM = "#9c6b2e"   # 中期（橙）
C_LPM   = "#c9a6d6"; E_LPM  = "#a87bbd"; T_LPM = "#6f4a86"   # 长期画像（紫）
C_DYN   = "#f0e6cf"; E_DYN  = "#cdb98a"; T_DYN = "#7a6326"   # 动态尾巴（米）
C_DISK  = "#faece7"; E_DISK = "#993c1d"; T_DISK= "#712b13"   # 落盘冷分支（陶土）
C_BND   = "#a32d2d"; C_BNDF = "#fcebeb"                       # 命脉边界（红）
C_PANEL = "#fbfbf6"; E_PANEL= "#d9d6cc"
C_TXT   = "#333333"; C_MUTED= "#8a8a8a"; C_HOT = "#b5402f"
C_STATBG= "#eef7f3"; C_DYNBG = "#fbf3e6"

fig, ax = plt.subplots(figsize=(17.2, 11.2))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, color, ec=E_PANEL, lw=1.2, r=0.8, ls="-", z=2, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0.02,rounding_size={r}",
                                facecolor=color, edgecolor=ec, linewidth=lw,
                                linestyle=ls, zorder=z, alpha=alpha))


def txt(x, y, s, fs=8.6, color=C_TXT, bold=False, ha="left", va="center", z=5):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color,
            fontweight="bold" if bold else "normal", zorder=z)


def arrow(x0, y0, x1, y1, color="#666", lw=1.8, style="-|>", rad=0.0, z=4, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=14, color=color, linewidth=lw,
                                 linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z,
                                 shrinkA=2, shrinkB=2))


def alabel(x, y, s, color, fs=7.6, z=7):
    ax.text(x, y, s, ha="center", va="center", fontsize=fs, color=color, zorder=z,
            bbox=dict(boxstyle="round,pad=0.24", fc="white", ec=color, lw=0.8, alpha=0.96))


# ===================== 标题 =====================
ax.text(50, 97.6, "端侧 Agent OS 完整记忆系统架构", ha="center", fontsize=18,
        fontweight="bold", color="#222")
ax.text(50, 94.0,
        "两类记忆载体不同、组织与管理方式不同 —— 明文记忆走「Prompt 拼装」，KV Cache 记忆走「Prefix Cache」，"
        "按一条「命脉边界」拼成同一条上下文",
        ha="center", fontsize=9.6, color=C_MUTED)

# ===================== 三栏列头 =====================
ax.text(16,  90.0, "① KV Cache 记忆 · 激活载体", ha="center", fontsize=11,
        fontweight="bold", color=T_KV)
ax.text(16,  87.6, "前缀缓存 · 内容寻址 · 两级常驻", ha="center", fontsize=8.0, color=C_MUTED)
ax.text(50,  90.0, "② 拼装出的上下文（一条 token 序列）", ha="center", fontsize=11,
        fontweight="bold", color="#444")
ax.text(50,  87.6, "上 = position 0（位置固定起点）　下 = 序列末尾", ha="center",
        fontsize=8.0, color=C_MUTED)
ax.text(84,  90.0, "③ 明文记忆 · 明文外置载体", ha="center", fontsize=11,
        fontweight="bold", color=T_LPM)
ax.text(84,  87.6, "MemoryOS 三级：短期→中期→长期", ha="center", fontsize=8.0, color=C_MUTED)

# ===================================================================
# 中栏 —— 拼装出的上下文（两区 + 命脉边界）
# ===================================================================
CX0, CW = 35.5, 29.0     # 中栏 x 起点 / 宽
ccx = CX0 + CW / 2

# --- 静态前缀区 背景 ---
box(CX0 - 1.2, 64.0, CW + 2.4, 20.5, C_STATBG, ec=E_KV, lw=1.6, r=1.2, ls=(0, (5, 3)), z=1)
txt(ccx, 82.6, "静态前缀区 · Prefix Cache 阶段", fs=8.8, bold=True, ha="center", color=T_KV)

# B1 system + 清单
box(CX0, 74.0, CW, 7.0, C_KV, ec=E_KV, lw=1.3)
txt(ccx, 78.0, "system prompt + skill 清单", fs=9.4, bold=True, ha="center", color=T_KV)
txt(ccx, 75.4, "根 · 全员共享 · 缓存命中", fs=7.6, ha="center", color=E_KV)

# B2 选中 skill
box(CX0, 65.5, CW, 7.0, C_KV, ec=E_KV, lw=1.3)
txt(ccx, 69.5, "选中的 skill X · 完整 prompt", fs=9.4, bold=True, ha="center", color=T_KV)
txt(ccx, 66.9, "分支 · 按需 restore · 仍命中缓存", fs=7.6, ha="center", color=E_KV)

# --- 命脉边界 ---
box(CX0 - 1.2, 58.6, CW + 2.4, 4.2, C_BNDF, ec=C_BND, lw=1.2, r=0.6)
txt(ccx, 61.3, "命脉边界（静 / 动态）", fs=8.4, bold=True, ha="center", color="#791f1f")
txt(ccx, 59.4, "以上逐字节一致 + 绝对位置固定；以下不缓存、不可上移", fs=6.9, ha="center", color=C_BND)

# --- 动态尾巴区 背景 ---
box(CX0 - 1.2, 31.0, CW + 2.4, 26.0, C_DYNBG, ec=E_MTM, lw=1.6, r=1.2, ls=(0, (5, 3)), z=1)
txt(ccx, 55.2, "动态尾巴区 · Prompt 拼装阶段", fs=8.8, bold=True, ha="center", color=T_MTM)

# B3 检索到的明文记忆（含三色 chip）
box(CX0, 42.0, CW, 11.0, "#fbf7ef", ec=E_MTM, lw=1.3)
txt(ccx, 51.0, "检索到的明文记忆（拼进 prompt）", fs=9.0, bold=True, ha="center", color=T_MTM)
chip_w = 8.4
for i, (lbl, fc, ec, tc) in enumerate([
        ("STM 近况", C_STM, E_STM, T_STM),
        ("MTM 情景", C_MTM, E_MTM, T_MTM),
        ("LPM 画像", C_LPM, E_LPM, T_LPM)]):
    cxp = CX0 + 1.5 + i * (chip_w + 1.0)
    box(cxp, 43.4, chip_w, 5.0, fc, ec=ec, lw=1.1, r=0.5)
    txt(cxp + chip_w / 2, 45.9, lbl, fs=7.8, bold=True, ha="center", color=tc)

# B4 当前对话尾巴
box(CX0, 32.0, CW, 8.0, C_DYN, ec=E_DYN, lw=1.3)
txt(ccx, 36.7, "当前对话历史 + 新输入", fs=9.4, bold=True, ha="center", color=T_DYN)
txt(ccx, 34.0, "动态尾巴 · 每轮只 prefill 这段", fs=7.6, ha="center", color=T_DYN)

# token 顺序标记
arrow(CX0 - 2.6, 84.0, CX0 - 2.6, 31.5, color="#b7b3a6", lw=1.4, style="-|>", z=3)
ax.text(CX0 - 3.4, 58, "token 顺序", rotation=90, ha="center", va="center",
        fontsize=7.4, color=C_MUTED, zorder=3)

# ===================================================================
# 左栏 —— KV Cache 记忆：组织 / 管理
# ===================================================================
LX0, LW = 1.5, 28.0
lcx = LX0 + LW / 2

# 迷你前缀树
box(LX0 + 4.0, 78.5, LW - 8.0, 5.6, C_KV, ec=E_KV, lw=1.2)
txt(lcx, 81.3, "system（根）· 全员共享", fs=7.8, bold=True, ha="center", color=T_KV)
leaves = [("skill A", C_KV, E_KV, T_KV, "常驻RAM"),
          ("skill B", C_KV, E_KV, T_KV, "常驻RAM"),
          ("skill C", C_DISK, E_DISK, T_DISK, "按需落盘"),
          ("skill D", C_DISK, E_DISK, T_DISK, "按需落盘")]
lw_leaf, gap = 5.7, 0.85
total = len(leaves) * lw_leaf + (len(leaves) - 1) * gap
x_start = lcx - total / 2
for i, (nm, fc, ec, tc, tag) in enumerate(leaves):
    lx = x_start + i * (lw_leaf + gap)
    arrow(lcx, 78.5, lx + lw_leaf / 2, 73.6, color="#9b988c", lw=1.0, rad=0.0, z=3)
    box(lx, 68.0, lw_leaf, 5.6, fc, ec=ec, lw=1.0, r=0.45)
    txt(lx + lw_leaf / 2, 71.3, nm, fs=6.9, bold=True, ha="center", color=tc)
    txt(lx + lw_leaf / 2, 69.0, tag, fs=5.7, ha="center", color=tc)
txt(lcx, 65.6, "前缀树 radix tree · 复杂度 O(skill 数)，非 O(会话数)",
    fs=6.8, ha="center", color=C_MUTED)

# 管理要点
box(LX0 + 1.5, 33.0, LW - 3.0, 29.0, C_PANEL, ec=E_PANEL, lw=1.0)
kv_lines = [
    ("组织", "前缀树：system 为根·全员共享，各 skill 为分支增量 KV"),
    ("索引", "内容寻址 key = hash(模型 + 量化 + prompt 文本)"),
    ("匹配", "0 / 1 精确 token 前缀匹配（差一字节即整体 miss）"),
    ("存储", "RAM 常驻(system + 热门 skill) / 冷 skill 按需落盘"),
    ("治理", "预计算落盘·跨重启复用；LRU + pin 热门；prompt 改即失效"),
    ("性质", "静态 · 跨会话 · 全员共享（能力 / 语义记忆）"),
]
ly = 59.0
for k, v in kv_lines:
    ax.text(LX0 + 3.0, ly, k, fontsize=7.8, fontweight="bold", color=T_KV,
            ha="left", va="top", zorder=5)
    ax.text(LX0 + 8.2, ly, v, fontsize=7.2, color=C_TXT, ha="left", va="top", zorder=5)
    ly -= 4.55

# 左栏 → 静态前缀区
arrow(LX0 + LW + 0.3, 70.5, CX0 - 1.6, 72.0, color=E_KV, lw=2.0, rad=-0.12, z=6)
alabel(32.5, 76.2, "供给静态前缀\n命中即免 prefill", E_KV, fs=7.0)

# ===================================================================
# 右栏 —— 明文记忆：三级组织（短/中/长期）+ 管理
# ===================================================================
RX0, RW = 70.0, 28.5
rcx = RX0 + RW / 2

tiers = [
    (76.0, 8.2, C_STM, E_STM, T_STM, "STM 短期记忆", "7 页 FIFO · Dialogue Page{Q,R,T}",
     "窗口工作集（直近上下文）"),
    (64.5, 8.6, C_MTM, E_MTM, T_MTM, "MTM 中期记忆", "同话题页 θ=0.6 聚成 Segment（≤200 段）",
     "情景事件历史 · 每段算 Heat"),
    (53.0, 8.6, C_LPM, E_LPM, T_LPM, "LPM 长期记忆 / 画像", "User / Agent Persona（永久）",
     "剥离上下文的事实（“对花生过敏”）· 语义记忆"),
]
for (y0, h, fc, ec, tc, t, s1, s2) in tiers:
    box(RX0 + 1.0, y0, RW - 2.0, h, fc, ec=ec, lw=1.3)
    txt(RX0 + 3.0, y0 + h - 2.3, t, fs=9.2, bold=True, color=tc)
    txt(RX0 + 3.0, y0 + h - 4.9, s1, fs=6.9, color=C_TXT)
    txt(RX0 + 3.0, y0 + h - 7.0, s2, fs=6.7, color=C_MUTED)

# 写入沉淀晋升（向下）
arrow(RX0 + RW - 4.5, 76.0, RX0 + RW - 4.5, 73.1, color=E_MTM, lw=1.9, z=6)
alabel(RX0 + RW - 12.0, 74.4, "满 7 页 FIFO 挤出最旧页", E_MTM, fs=6.6)
arrow(RX0 + RW - 4.5, 64.5, RX0 + RW - 4.5, 61.6, color=E_LPM, lw=1.9, z=6)
alabel(RX0 + RW - 12.0, 62.9, "Heat > τ=5 换页晋升", E_LPM, fs=6.6)
txt(RX0 + 1.5, 85.4, "写入：情景 → 语义 自下沉淀（晋升）↓", fs=6.9, color=C_MUTED)

# 三级召回 → 中栏 B3
for (y0, h, fc, ec, tc, *_), lab in zip(tiers, ["全取 7 页", "top-m=5 段 → top-k 页", "每类 top-10"]):
    arrow(RX0 + 0.8, y0 + h / 2, CX0 + CW + 1.6, 48.0, color=ec, lw=1.3, rad=0.16, z=6)
alabel(67.5, 41.0, "三级召回 → Prompt 拼装\nSTM 全取 · MTM top-m,k · LPM top-10", T_MTM, fs=6.8)

# 管理要点（右栏底）
box(RX0 + 1.0, 33.0, RW - 2.0, 17.5, C_PANEL, ec=E_PANEL, lw=1.0)
pt_lines = [
    ("组织", "三级分层 STM→MTM→LPM；最小单元 = 一次问答(页)"),
    ("写入", "STM→MTM：FIFO + 话题链；MTM→LPM：Heat 换页"),
    ("治理", "Heat(频率+量+新近度)提升 + 时间衰减淘汰 → 有界"),
    ("性质", "动态 · 每用户每会话 · 运行时检索（情景→语义）"),
]
ry = 48.0
for k, v in pt_lines:
    ax.text(RX0 + 3.0, ry, k, fontsize=7.6, fontweight="bold", color=T_LPM,
            ha="left", va="top", zorder=5)
    ax.text(RX0 + 8.0, ry, v, fontsize=6.9, color=C_TXT, ha="left", va="top", zorder=5)
    ry -= 4.0

# ===================================================================
# 底部桥 —— MemOS MemCube：热点明文 → 激活(KV)
# ===================================================================
arrow(RX0 + 3.0, 53.0, 16.0, 30.5, color=C_HOT, lw=1.6, rad=0.32, ls=(0, (5, 3)), z=3)
alabel(50, 27.2,
       "MemOS · MemCube：热点明文记忆 → 注入为激活(KV) —— 两类载体间的「提升 / 降级」桥",
       C_HOT, fs=7.4)

# ===================== 页脚 =====================
ax.text(2.5, 19.0,
        "● 明文记忆（右）：检索式、动态、每用户每会话，运行时把命中的 STM 近况 + MTM 情景 + LPM 画像「拼」进 Prompt 尾巴。",
        ha="left", fontsize=7.9, color="#555")
ax.text(2.5, 15.4,
        "● KV Cache 记忆（左）：内容寻址、静态、全员共享，命中即「复用」system 共享前缀 + skill 分支的激活 KV，免去 prefill。",
        ha="left", fontsize=7.9, color="#555")
ax.text(2.5, 11.8,
        "● 命脉约束：明文记忆必须排在所有静态前缀（system + skill）之后；一旦上移，token 位置整体偏移 → skill 分支缓存全废。",
        ha="left", fontsize=7.9, color=C_HOT)
ax.text(2.5, 7.6,
        "图例：绿 = KV/激活·静态（Prefix Cache）　蓝/橙/紫 = 明文三级 STM/MTM/LPM　米 = 动态尾巴　红 = 静/动态命脉边界",
        ha="left", fontsize=7.4, color=C_MUTED)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "memory-system-arch.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "memory-system-arch.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: memory-system-arch.png / .svg")

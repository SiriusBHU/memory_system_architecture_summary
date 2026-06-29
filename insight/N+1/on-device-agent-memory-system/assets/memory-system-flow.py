#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端侧 Agent OS 记忆系统「使用流程图」：一轮对话运行时怎么走（统合两篇调研）。

主轴自上而下 6 步；左右两条并行泳道分别是两类记忆的取/写：
  左泳道 = KV Cache 记忆（Prefix Cache）：restore 静态前缀 KV ↔ 写回新算的块
  右泳道 = 明文记忆（Prompt 拼装）：三级召回 STM/MTM/LPM ↔ 本轮问答沉淀晋升

  ① 用户新一轮输入
  ② 轻量路由(embedding top-k)：只读 skill 短描述 → 选出 skill X（+异步预取候选 KV）
  ③ 取记忆（并行两路）
       KV 侧：system 常驻命中 + skill X 从 RAM/盘 restore  ← Prefix Cache
       明文侧：三级召回 STM 全取 / MTM top-m,k / LPM 每类 top-10 ← 检索
  ④ 组装 context（按命脉边界拼接）
       [system KV] + [skill KV]  ─边界─  [明文记忆] + [对话尾巴]
  ⑤ 执行：只 prefill 动态尾巴 → 生成回复
  ⑥ 双写回
       KV 侧：新算的块 hash 后写回前缀缓存 → 下轮命中更长前缀
       明文侧：本轮问答打包成 Dialogue Page 压入 STM →(满7页FIFO) MTM →(Heat>τ) LPM

数据来源:
  prefix-cache-agent-notes.md（路由档位、预取、restore/写回、命脉约束）
  MemoryOS arXiv 2506.06326（三级召回与写入晋升规则）；Mem0 arXiv 2504.19413。

运行:
    pip install matplotlib
    python memory-system-flow.py
输出: 脚本所在目录下 memory-system-flow.png / .svg
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

# ----- 配色（与系列图一致）-----
C_IN    = "#f1efe8"; E_IN   = "#5f5e5a"; T_IN  = "#2c2c2a"   # 输入/中性（灰米）
C_RT    = "#eeedfe"; E_RT   = "#534ab7"; T_RT  = "#3c3489"   # 路由/预取（紫蓝）
C_KV    = "#dff1ea"; E_KV   = "#0f6e56"; T_KV  = "#085041"   # KV/静态（绿）
C_STM   = "#9ec6e8"; E_STM  = "#7aa8cf"; T_STM = "#2f5f86"   # 短期（蓝）
C_MTM   = "#edbd88"; E_MTM  = "#d9a05f"; T_MTM = "#9c6b2e"   # 中期（橙）
C_LPM   = "#c9a6d6"; E_LPM  = "#a87bbd"; T_LPM = "#6f4a86"   # 长期（紫）
C_ASM   = "#fbf7ef"; E_ASM  = "#cdb98a"; T_ASM = "#7a6326"   # 组装（米）
C_GEN   = "#8fbf9f"; E_GEN  = "#3a6b48"; T_GEN = "#22512f"   # 执行/生成（绿）
C_BND   = "#a32d2d"; C_BNDF = "#fcebeb"
C_TXT   = "#333333"; C_MUTED= "#8a8a8a"; C_HOT = "#b5402f"
C_KVBG  = "#eef7f3"; C_PTBG = "#f7eefb"

fig, ax = plt.subplots(figsize=(16.8, 11.4))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, color, ec=E_IN, lw=1.2, r=0.8, ls="-", z=3, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0.02,rounding_size={r}",
                                facecolor=color, edgecolor=ec, linewidth=lw,
                                linestyle=ls, zorder=z, alpha=alpha))


def txt(x, y, s, fs=8.6, color=C_TXT, bold=False, ha="center", va="center", z=5):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color,
            fontweight="bold" if bold else "normal", zorder=z)


def arrow(x0, y0, x1, y1, color="#73726c", lw=1.8, style="-|>", rad=0.0, z=4, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=14, color=color, linewidth=lw,
                                 linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z,
                                 shrinkA=2, shrinkB=2))


def alabel(x, y, s, color, fs=7.4, z=7):
    ax.text(x, y, s, ha="center", va="center", fontsize=fs, color=color, zorder=z,
            bbox=dict(boxstyle="round,pad=0.24", fc="white", ec=color, lw=0.8, alpha=0.96))


# ===================== 标题 =====================
ax.text(50, 97.6, "端侧 Agent OS 记忆系统 · 一轮对话的使用流程", ha="center",
        fontsize=18, fontweight="bold", color="#222")
ax.text(50, 94.0,
        "主轴 6 步自上而下；两条泳道并行：左 = KV Cache 记忆（Prefix Cache 取/写） · 右 = 明文记忆（三级召回 / 沉淀晋升）",
        ha="center", fontsize=9.4, color=C_MUTED)

# ===================== 泳道背景 =====================
box(2.0, 8.0, 24.5, 80.0, C_KVBG, ec=E_KV, lw=1.4, r=1.2, ls=(0, (5, 3)), z=1)
txt(14.2, 85.8, "KV Cache 记忆泳道", fs=9.2, bold=True, color=T_KV)
txt(14.2, 83.4, "Prefix Cache · 取静态前缀 / 写回", fs=7.0, color=E_KV)

box(73.5, 8.0, 24.5, 80.0, C_PTBG, ec=E_LPM, lw=1.4, r=1.2, ls=(0, (5, 3)), z=1)
txt(85.7, 85.8, "明文记忆泳道", fs=9.2, bold=True, color=T_LPM)
txt(85.7, 83.4, "三级召回 / 本轮沉淀晋升", fs=7.0, color=T_LPM)

txt(50, 86.6, "主轴 · 运行时主流程", fs=9.0, bold=True, color="#555")

# ===================== 主轴 6 步 =====================
MX0, MW = 33.5, 33.0
mcx = MX0 + MW / 2

steps = [
    # (y0, h, fill, ec, tcolor, num, title, sub)
    (77.0, 7.5, C_IN,  E_IN,  T_IN,  "①", "用户新一轮输入", "新 query 到达"),
    (65.0, 8.0, C_RT,  E_RT,  T_RT,  "②", "轻量路由（embedding top-k）", "只读 skill 短描述 → 选出 skill X"),
    (52.0, 8.5, C_IN,  E_IN,  T_IN,  "③", "取记忆 · 并行两路", "KV 侧 restore 前缀　|　明文侧三级召回"),
    (36.0, 12.5, C_ASM, E_ASM, T_ASM, "④", "组装 context（按命脉边界拼接）", ""),
    (25.0, 8.0, C_GEN, E_GEN, T_GEN, "⑤", "执行：只 prefill 动态尾巴", "→ 生成回复"),
    (12.0, 8.0, C_IN,  E_IN,  T_IN,  "⑥", "双写回", "KV 侧写回前缀缓存　|　明文侧沉淀晋升"),
]
ys = {}
for (y0, h, fc, ec, tc, num, t, s) in steps:
    box(MX0, y0, MW, h, fc, ec=ec, lw=1.4)
    ys[num] = (y0, h)
    if s:
        txt(mcx, y0 + h - h * 0.33, f"{num}  {t}", fs=9.4, bold=True, color=tc)
        txt(mcx, y0 + h * 0.30, s, fs=7.4, color=tc)
    else:
        txt(mcx, y0 + h - 2.0, f"{num}  {t}", fs=9.4, bold=True, color=tc)

# ④ 内部：四段拼接 + 命脉边界（标题在 46.5，链条往下排）
seg_w = (MW - 4.0) / 2
for i, (lbl, fc, ec, tc) in enumerate([
        ("system KV", C_KV, E_KV, T_KV),
        ("skill X KV", C_KV, E_KV, T_KV)]):
    box(MX0 + 2.0 + i * seg_w, 42.8, seg_w - 0.6, 2.5, fc, ec=ec, lw=1.0, r=0.4)
    txt(MX0 + 2.0 + i * seg_w + (seg_w - 0.6) / 2, 44.05, lbl, fs=7.0, bold=True, color=tc)
ax.plot([MX0 + 1.5, MX0 + MW - 1.5], [42.0, 42.0], color=C_BND, lw=1.1, ls=(0, (4, 3)), zorder=5)
txt(mcx, 42.0, " 命脉边界 ", fs=6.2, color="#791f1f", bold=True)
for i, (lbl, fc, ec, tc) in enumerate([
        ("明文记忆", C_ASM, E_MTM, T_MTM),
        ("对话尾巴", C_ASM, E_IN, T_IN)]):
    box(MX0 + 2.0 + i * seg_w, 38.9, seg_w - 0.6, 2.5, fc, ec=ec, lw=1.0, r=0.4)
    txt(MX0 + 2.0 + i * seg_w + (seg_w - 0.6) / 2, 40.15, lbl, fs=7.0, bold=True, color=tc)

# 主轴竖向箭头
for a, b in [("①", "②"), ("②", "③"), ("③", "④"), ("④", "⑤"), ("⑤", "⑥")]:
    y_a = ys[a][0]
    y_b = ys[b][0] + ys[b][1]
    arrow(mcx, y_a, mcx, y_b, color="#73726c", lw=1.9)

# ===================================================================
# 左泳道 —— KV Cache 记忆（取 / 写）
# ===================================================================
LX0, LW = 3.2, 22.0
lcx = LX0 + LW / 2

# 异步预取（接 ②）
box(LX0, 64.5, LW, 8.5, C_RT, ec=E_RT, lw=1.2)
txt(lcx, 70.8, "异步预取候选 skill KV", fs=8.0, bold=True, color=T_RT)
txt(lcx, 68.2, "路由 top-k 一出，提前从盘", fs=6.8, color=T_RT)
txt(lcx, 66.2, "load 候选 → 决策耗时盖住加载", fs=6.8, color=T_RT)
arrow(MX0, 68.5, LX0 + LW, 69.0, color=E_RT, lw=1.6, rad=0.06)

# restore 前缀 KV（接 ③）
box(LX0, 50.0, LW, 9.5, C_KV, ec=E_KV, lw=1.3)
txt(lcx, 57.4, "restore 静态前缀 KV", fs=8.2, bold=True, color=T_KV)
txt(lcx, 54.9, "system 常驻 RAM → 命中即免 prefill", fs=6.7, color=T_KV)
txt(lcx, 52.8, "skill X 从 RAM/盘 load（或预取已就绪）", fs=6.7, color=T_KV)
txt(lcx, 50.8, "0/1 精确前缀匹配 · 内容寻址 key", fs=6.5, color=C_MUTED)
arrow(MX0, 54.5, LX0 + LW, 54.5, color=E_KV, lw=1.7, rad=0.0)
arrow(LX0 + LW, 52.5, MX0 + 6.0, 44.0, color=E_KV, lw=1.5, rad=-0.18)  # → 进 ④ system/skill 段

# 写回前缀缓存（接 ⑥）
box(LX0, 13.0, LW, 9.5, C_KV, ec=E_KV, lw=1.3)
txt(lcx, 20.4, "写回前缀缓存", fs=8.2, bold=True, color=T_KV)
txt(lcx, 17.9, "本轮新算的 KV 块 → hash 后入缓存", fs=6.7, color=T_KV)
txt(lcx, 15.8, "下轮命中更长前缀（轨迹越滚越长）", fs=6.7, color=T_KV)
arrow(MX0, 16.5, LX0 + LW, 17.0, color=E_KV, lw=1.6, rad=-0.04)

# ===================================================================
# 右泳道 —— 明文记忆（三级召回 / 沉淀晋升）
# ===================================================================
RX0, RW = 75.0, 22.0
rcx = RX0 + RW / 2

# 三级召回（接 ③）
rec = [
    (56.0, 6.2, C_STM, E_STM, T_STM, "STM · 全取最近 7 页", "直近上下文"),
    (48.5, 6.2, C_MTM, E_MTM, T_MTM, "MTM · top-m=5 → top-k 页", "情景事件命中"),
    (41.0, 6.2, C_LPM, E_LPM, T_LPM, "LPM · 每类 top-10", "画像 / 语义事实命中"),
]
txt(rcx, 63.6, "三级召回（检索式，不重放全历史）", fs=8.0, bold=True, color=T_LPM)
for (y0, h, fc, ec, tc, t, s) in rec:
    box(RX0, y0, RW, h, fc, ec=ec, lw=1.2)
    txt(RX0 + 1.6, y0 + h - 2.1, t, fs=7.4, bold=True, ha="left", color=tc)
    txt(RX0 + 1.6, y0 + 1.9, s, fs=6.4, ha="left", color=C_MUTED)
arrow(MX0 + MW, 54.5, RX0, 58.0, color=E_STM, lw=1.5, rad=0.10)
# 召回结果 → ④ 明文记忆段
arrow(RX0, 44.0, MX0 + 13.5, 41.6, color=E_MTM, lw=1.6, rad=0.18)
alabel(MX0 + MW + 6.5, 47.5, "合并注入\nPrompt 尾巴", T_MTM, fs=6.6)

# 沉淀晋升（接 ⑥）
box(RX0, 11.5, RW, 12.5, "#fbfbf6", ec=E_LPM, lw=1.2)
txt(rcx, 21.6, "本轮问答 → 沉淀晋升", fs=8.0, bold=True, color=T_LPM)
txt(RX0 + 1.6, 18.6, "打包 Dialogue Page → 压入 STM", fs=6.7, ha="left", color=T_STM)
txt(RX0 + 1.6, 16.2, "STM 满 7 页 → FIFO 挤入 MTM(θ=0.6 聚簇)", fs=6.7, ha="left", color=T_MTM)
txt(RX0 + 1.6, 13.8, "MTM 段 Heat > τ=5 → 换页晋升 LPM", fs=6.7, ha="left", color=T_LPM)
arrow(MX0 + MW, 16.5, RX0, 18.0, color=E_LPM, lw=1.6, rad=0.04)

# 治理小注
alabel(rcx, 27.5, "治理：Heat 提升 + 时间衰减淘汰 → 规模有界", T_LPM, fs=6.6)

# ===================== 回环 & 页脚 =====================
arrow(MX0 + MW + 1.5, 13.0, MX0 + MW + 1.5, 80.0, color=C_HOT, lw=1.5,
      rad=-0.55, ls=(0, (5, 3)), z=2)
alabel(64.0, 50.0, "多轮回环：下一轮\n前缀更长 · 记忆更厚", C_HOT, fs=7.0)

ax.text(2.5, 5.4,
        "便宜的路由（读短描述）先定 skill → 贵的 prefill 只发生在执行那一轮，且大半被前缀缓存与预取吃掉；明文记忆只在拼装阶段注入尾巴，绝不上移到静态前缀之上。",
        ha="left", fontsize=7.8, color="#555")
ax.text(2.5, 2.4,
        "图例：紫蓝 = 路由/预取　绿 = KV/执行　蓝/橙/紫 = 明文三级 STM/MTM/LPM　米 = 组装　红虚线 = 命脉边界 / 多轮回环",
        ha="left", fontsize=7.3, color=C_MUTED)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "memory-system-flow.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "memory-system-flow.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: memory-system-flow.png / .svg")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking 数据流图：写入分层(L0/L1/L2) · 目录递归检索 · 自演化会话闭环。

三条主线（自上而下）:
  ① 写入/摄取管线   原始内容 → ResourceService → VLM 生成摘要/概览 + Embedder 生成向量
                    → 落成 L0(摘要~100tok) / L1(概览~2k tok) / L2(原文) 三层 → 写入 viking:// 目录
  ② 目录递归检索    query → 意图分析(多条件) → 向量检索定位高分目录 → 目录内二次检索
                    → 递归下钻子目录 → 结果聚合(保局部相关 + 全局结构) → 返回上下文
                    （旁路：可视化检索轨迹，viking:// 路径全程留痕，可观测可调试）
  ③ 自演化会话闭环  任务执行 → 会话结束触发 → 记忆抽取 v3(Profile/Preferences/Entities/
                    Events/Cases/Patterns) → 写回 user/ 与 agent/ → 回到写入，越用越聪明

数据来源:
  openviking.ai / github README / deepwiki / 官方文档（volcengine-openviking.mintlify.app）
  L0/L1/L2 token 预算与用途、目录递归检索步骤、记忆抽取六类均取自上述来源。

运行:
    pip install matplotlib
    python openviking-dataflow.py
输出: 脚本所在目录下 openviking-dataflow.png / .svg
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

# ----- 配色（沿用本目录语义：蓝/橙/紫 = 三级由粗到细；绿 = 服务/流程；红 = 关键约束）-----
C_SVC  = "#dff1ea"; E_SVC  = "#0f6e56"; T_SVC  = "#085041"
C_L0   = "#9ec6e8"; E_L0   = "#7aa8cf"; T_L0   = "#2f5f86"   # L0 摘要（蓝·最粗）
C_L1   = "#edbd88"; E_L1   = "#d9a05f"; T_L1   = "#9c6b2e"   # L1 概览（橙·中）
C_L2   = "#c9a6d6"; E_L2   = "#a87bbd"; T_L2   = "#6f4a86"   # L2 详情（紫·最细）
C_VEC  = "#e7dcef"; E_VEC  = "#a87bbd"; T_VEC  = "#6f4a86"
C_STEP = "#eef7f2"; E_STEP = "#0f6e56"; T_STEP = "#085041"
C_EVO  = "#faece7"; E_EVO  = "#993c1d"; T_EVO  = "#712b13"
C_PANEL= "#fbfbf6"; E_PANEL= "#d9d6cc"
C_TXT  = "#333333"; C_MUTED= "#8a8a8a"; C_HOT = "#b5402f"

fig, ax = plt.subplots(figsize=(17.4, 11.6))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, color, ec=E_PANEL, lw=1.2, r=0.8, ls="-", z=2, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0.02,rounding_size={r}",
                                facecolor=color, edgecolor=ec, linewidth=lw,
                                linestyle=ls, zorder=z, alpha=alpha))


def txt(x, y, s, fs=8.6, color=C_TXT, bold=False, ha="left", va="center", z=5, mono=False):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color,
            fontweight="bold" if bold else "normal", zorder=z,
            family="monospace" if mono else None)


def arrow(x0, y0, x1, y1, color="#666", lw=1.8, style="-|>", rad=0.0, z=4, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=14, color=color, linewidth=lw,
                                 linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z,
                                 shrinkA=2, shrinkB=2))


def alabel(x, y, s, color, fs=7.0, z=7):
    ax.text(x, y, s, ha="center", va="center", fontsize=fs, color=color, zorder=z,
            bbox=dict(boxstyle="round,pad=0.24", fc="white", ec=color, lw=0.8, alpha=0.96))


# ===================== 标题 =====================
ax.text(50, 97.6, "OpenViking 数据流：写入分层 · 目录递归检索 · 自演化", ha="center",
        fontsize=18, fontweight="bold", color="#222")
ax.text(50, 94.2,
        "写入时把内容拆成 L0/L1/L2 三层；检索时沿目录层级递归下钻；会话结束抽取记忆并写回，越用越聪明",
        ha="center", fontsize=9.6, color=C_MUTED)

# ===================================================================
# ① 写入 / 摄取管线（L0/L1/L2 生成）
# ===================================================================
box(2.0, 64.5, 96.0, 26.0, "#fbfaf6", ec=E_L1, lw=1.5, r=1.0, ls=(0, (5, 3)), z=1)
txt(3.4, 88.8, "① 写入 / 摄取管线  Ingestion → L0 / L1 / L2 分层", fs=10.2, bold=True, color=T_L1)

# 原始内容
box(3.5, 77.0, 12.0, 9.0, C_PANEL, ec=E_PANEL, lw=1.2)
txt(9.5, 83.4, "原始内容", fs=8.6, bold=True, ha="center", color=C_TXT)
txt(9.5, 81.2, "文档/代码库/网页", fs=6.5, ha="center", color=C_MUTED)
txt(9.5, 79.4, "对话/工具调用记录", fs=6.5, ha="center", color=C_MUTED)

arrow(15.7, 81.5, 18.3, 81.5, color="#9b988c", lw=2.0, z=6)

# ResourceService 摄取
box(18.5, 77.0, 14.0, 9.0, C_SVC, ec=E_SVC, lw=1.3)
txt(25.5, 83.4, "ResourceService", fs=8.2, bold=True, ha="center", color=T_SVC)
txt(25.5, 81.2, "摄取·切分·编排加工", fs=6.5, ha="center", color="#3f6b5a")
txt(25.5, 79.4, "调 VLM + Embedder", fs=6.5, ha="center", color="#3f6b5a")

# 分叉：VLM 生成三层
arrow(32.7, 81.5, 35.2, 81.5, color=E_SVC, lw=1.8, z=6)
alabel(34.0, 84.4, "VLM 生成", T_SVC, fs=6.2)

# 三层 tier 卡片
tiers = [
    (C_L0, E_L0, T_L0, "L0 摘要 Abstract", "~100 tokens", ".abstract.md",
     "向量召回·快速过滤·目录列举"),
    (C_L1, E_L1, T_L1, "L1 概览 Overview", "~2k tokens", ".overview.md",
     "重排精修·内容导航·决策参考"),
    (C_L2, E_L2, T_L2, "L2 详情 Details", "无上限·按需", "原文全量",
     "深度分析·付出全文 token 成本"),
]
tx0, tw = 35.5, 13.3
for i, (fc, ec, tc, t, tok, art, use) in enumerate(tiers):
    txp = tx0 + i * (tw + 0.9)
    box(txp, 76.5, tw, 10.0, fc, ec=ec, lw=1.3, r=0.6)
    txt(txp + tw / 2, 84.5, t, fs=7.5, bold=True, ha="center", color=tc)
    txt(txp + tw / 2, 82.5, tok, fs=6.8, bold=True, ha="center", color=tc)
    txt(txp + tw / 2, 80.7, art, fs=6.2, ha="center", color=tc)
    txt(txp + tw / 2, 78.5, use, fs=5.8, ha="center", color=C_TXT)
# 三层间「按需下钻」箭头
for i in range(2):
    xa = tx0 + (i + 1) * (tw + 0.9) - 0.9
    arrow(xa, 81.5, xa + 0.9, 81.5, color="#b0736e", lw=1.4, style="-|>", z=6)
txt(tx0 + 0.2, 74.9, "先扫 L0 → 需要再取 L1 → 最后才读 L2（渐进加载，省 token）",
    fs=6.4, color=C_HOT)

# 写入目录（三层的归宿）
arrow(78.5, 81.5, 81.0, 81.5, color=E_SVC, lw=1.8, z=6)
box(81.2, 77.0, 15.0, 9.0, "#eef7f2", ec=E_SVC, lw=1.3, r=0.6)
txt(88.7, 84.4, "写入 viking:// 目录", fs=7.8, bold=True, ha="center", color=T_SVC)
txt(88.7, 82.2, "VikingFS 虚拟层", fs=6.4, ha="center", color="#3f6b5a")
txt(88.7, 80.4, "→ AGFS 持久化", fs=6.4, ha="center", color="#3f6b5a")
txt(88.7, 78.6, "local / S3 / memory", fs=6.2, ha="center", color=C_MUTED)

# 向量索引（L0 摘要建向量）
arrow(tx0 + tw / 2, 76.3, tx0 + tw / 2, 72.6, color=E_VEC, lw=1.6, z=6)
box(35.5, 67.0, 30.0, 5.4, C_VEC, ec=E_VEC, lw=1.2, r=0.5)
txt(50.5, 70.4, "L0 摘要向量 → VikingVectorIndexBackend", fs=7.6, bold=True, ha="center", color=T_VEC)
txt(50.5, 68.4, "只对轻量摘要建向量，召回入口小而快（Embedder 生成）", fs=6.2, ha="center", color=T_VEC)

# ===================================================================
# ② 目录递归检索
# ===================================================================
box(2.0, 36.0, 96.0, 28.5, "#f2f8f5", ec=E_STEP, lw=1.5, r=1.0, ls=(0, (5, 3)), z=1)
txt(3.4, 62.8, "② 目录递归检索  Directory Recursive Retrieval", fs=10.2, bold=True, color=T_STEP)

# query 入口
box(3.5, 51.5, 11.0, 6.4, C_L0, ec=E_L0, lw=1.3, r=0.5)
txt(9.0, 55.5, "query", fs=8.6, bold=True, ha="center", color=T_L0)
txt(9.0, 53.3, "用户/Agent 意图", fs=6.4, ha="center", color=T_L0)

steps = [
    ("① 意图分析", "拆成多条检索条件"),
    ("② 向量检索", "定位高分目录"),
    ("③ 目录内二次检索", "目录内精排候选"),
    ("④ 递归下钻", "进入子目录再检索"),
    ("⑤ 结果聚合", "保局部相关+全局结构"),
]
sx0, sw2 = 16.5, 15.4
for i, (t, s) in enumerate(steps):
    sxp = sx0 + i * (sw2 + 0.6)
    box(sxp, 51.5, sw2, 6.4, C_STEP, ec=E_STEP, lw=1.2, r=0.5)
    txt(sxp + sw2 / 2, 55.5, t, fs=7.8, bold=True, ha="center", color=T_STEP)
    txt(sxp + sw2 / 2, 53.3, s, fs=6.3, ha="center", color="#3f6b5a")
# 步骤间箭头
arrow(14.6, 54.7, 16.3, 54.7, color="#9b988c", lw=1.6, z=6)
for i in range(4):
    xa = sx0 + (i + 1) * (sw2 + 0.6) - 0.6
    arrow(xa - 0.05, 54.7, xa + 0.55, 54.7, color="#9b988c", lw=1.6, z=6)
# ④→③ 递归回环
arrow(sx0 + 3.5 * (sw2 + 0.6) + 7, 51.3, sx0 + 2.5 * (sw2 + 0.6) + 7, 51.3,
      color=E_STEP, lw=1.4, style="-|>", rad=0.55, ls=(0, (4, 2)), z=6)
txt(sx0 + 3.0 * (sw2 + 0.6) + 3.5, 48.3, "命中子目录则递归", fs=6.2, ha="center", color=T_STEP)

# 迷你目录树（示意递归下钻）
box(3.5, 38.0, 40.0, 11.0, "#ffffff", ec="#cfe0d6", lw=1.1, r=0.6)
txt(4.6, 47.6, "沿目录层级下钻（保结构，非扁平打分）", fs=7.2, bold=True, color=T_STEP)
tree = [
    ("viking://resources/", "高分目录", T_STEP, True),
    ("  |- project-A/", "二次检索命中", "#40507a", False),
    ("  |   `- docs/", "L0命中→递归下钻→取L1/L2", T_L1, False),
    ("  `- project-B/", "低分 · 剪枝", C_MUTED, False),
]
tyy = 45.4
for path, note, col, root in tree:
    txt(4.8, tyy, path, fs=6.8, mono=True, bold=root, color=col)
    txt(24.5, tyy, note, fs=6.1, color=C_MUTED)
    tyy -= 2.05

# 可视化检索轨迹（旁路）
box(46.0, 38.0, 24.0, 11.0, "#eef2fb", ec="#7aa8cf", lw=1.2, r=0.6)
txt(47.2, 47.6, "可视化检索轨迹", fs=8.0, bold=True, color="#2f5f86")
for j, s in enumerate([
        "全程记录浏览过的 viking:// 路径", "哪个目录命中 / 哪步下钻 可回放",
        "把黑盒 RAG 变成可观测、可调试", "定位「为什么召回这条上下文」"]):
    txt(47.6, 45.2 - j * 2.05, "· " + s, fs=6.4, color="#40507a")

# 输出上下文
box(72.5, 40.5, 24.0, 6.4, C_L1, ec=E_L1, lw=1.3, r=0.5)
txt(84.5, 44.5, "返回分层上下文给 Agent", fs=7.8, bold=True, ha="center", color=T_L1)
txt(84.5, 42.3, "按 L0/L1/L2 粒度注入，token 可控", fs=6.3, ha="center", color=T_L1)
arrow(70.2, 43.7, 72.3, 43.7, color=E_L1, lw=1.8, z=6)

# ===================================================================
# ③ 自演化会话闭环
# ===================================================================
box(2.0, 15.5, 96.0, 18.0, "#fdf3ee", ec=E_EVO, lw=1.5, r=1.0, ls=(0, (5, 3)), z=1)
txt(3.4, 31.8, "③ 自演化会话闭环  Automatic Session Management / Self-Evolution", fs=10.2,
    bold=True, color=T_EVO)

evo = [
    ("任务执行", "Agent 用检索到的\n上下文完成任务"),
    ("会话结束触发", "自动压缩对话 /\n资源引用 / 工具调用"),
    ("记忆抽取 v3", "Profile · Preferences\nEntities · Events\nCases · Patterns"),
    ("写回命名空间", "用户记忆 → user/\nAgent 经验 → agent/"),
]
ex0, ew = 5.0, 20.5
for i, (t, s) in enumerate(evo):
    exp = ex0 + i * (ew + 3.2)
    box(exp, 18.5, ew, 9.5, C_EVO, ec=E_EVO, lw=1.3, r=0.6)
    txt(exp + ew / 2, 25.8, t, fs=8.4, bold=True, ha="center", color=T_EVO)
    txt(exp + ew / 2, 22.2, s, fs=6.5, ha="center", color="#7a3a20")
    if i < 3:
        arrow(exp + ew, 23.2, exp + ew + 3.0, 23.2, color=E_EVO, lw=1.8, z=6)

# 回环箭头：写回 → 回到写入管线（越用越聪明）
arrow(ex0 + 3.5 * (ew + 3.2) + ew / 2, 28.2, 89.5, 76.6,
      color=C_HOT, lw=1.7, style="-|>", rad=-0.28, ls=(0, (5, 3)), z=6)
alabel(88.7, 72.0, "写回即新一轮写入素材（越用越聪明）", C_HOT, fs=6.4)

# ===================== 页脚 =====================
ax.text(3.0, 11.0,
        "● 写入侧：内容一次加工成 L0/L1/L2 三层——摘要建向量做召回入口，概览供导航，详情按需再读，从写入起就为「省 token」设计。",
        ha="left", fontsize=7.8, color="#555")
ax.text(3.0, 7.6,
        "● 检索侧：不是一次性扁平相似度，而是「先定位目录 → 目录内精排 → 递归下钻」，保住语义相关的同时保住目录的全局结构；全程留轨迹，可观测。",
        ha="left", fontsize=7.8, color="#555")
ax.text(3.0, 4.2,
        "● 演化侧：会话结束自动抽取六类记忆写回 user/ 与 agent/，下一轮检索即可命中——静态记忆库变成随使用自我迭代的记忆。",
        ha="left", fontsize=7.8, color=C_HOT)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "openviking-dataflow.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "openviking-dataflow.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: openviking-dataflow.png / .svg")

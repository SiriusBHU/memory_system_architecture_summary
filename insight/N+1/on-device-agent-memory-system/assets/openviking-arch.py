#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking 系统架构图（面向 AI Agent 的「上下文文件系统 / 上下文数据库」）。

一句话主旨：OpenViking 用「文件系统范式」取代扁平向量库——把 Agent 需要的
记忆(memory) / 资源(resource) / 技能(skill) 统一映射为 viking:// 协议下的虚拟目录，
每个对象有唯一 URI，配合分层加载(L0/L1/L2)、目录递归检索与自演化会话管理。

分层结构（自上而下 = 请求下行）:
  ① 客户端层    ov CLI(Rust) / AsyncOpenViking(嵌入 SDK) / AsyncHTTPClient(远程)
  ② 服务编排层  OpenVikingService 中央编排 → FSService(路径/文件系统) + ResourceService(摄取/加工)
  ③ 存储抽象层  VikingFS(虚拟FS·viking://·多租户) | AGFS(Go 分布式FS·local/S3/mem) | VikingVectorIndexBackend(向量索引)
  ④ AI 服务集成  VLMFactory(Volcengine/OpenAI/LiteLLM) + EmbedderBase(dense/sparse/hybrid)

右侧：viking:// 命名空间树 + 两种部署模式（嵌入 / 服务）。

数据来源:
  openviking.ai / github.com/volcengine/OpenViking(README, v0.3.x)
  deepwiki.com/volcengine/OpenViking（分层组件：OpenVikingService/FSService/VikingFS/AGFS/...）
  volcengine-openviking.mintlify.app（官方文档）
  VikingMem: A Memory Base Management System for Stateful LLM-based Applications (VLDB 2026)

运行:
    pip install matplotlib
    python openviking-arch.py
输出: 脚本所在目录下 openviking-arch.png / .svg
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

# ----- 配色（沿用本目录既有配色语义）-----
C_CLI  = "#9ec6e8"; E_CLI  = "#7aa8cf"; T_CLI  = "#2f5f86"   # 客户端（蓝）
C_SVC  = "#dff1ea"; E_SVC  = "#0f6e56"; T_SVC  = "#085041"   # 服务编排（绿·核心）
C_FS   = "#edbd88"; E_FS   = "#d9a05f"; T_FS   = "#9c6b2e"   # VikingFS 虚拟FS（橙）
C_DISK = "#faece7"; E_DISK = "#993c1d"; T_DISK = "#712b13"   # AGFS 持久化（陶土）
C_VEC  = "#c9a6d6"; E_VEC  = "#a87bbd"; T_VEC  = "#6f4a86"   # 向量索引（紫）
C_AI   = "#d7e4dd"; E_AI   = "#7f9c90"; T_AI   = "#3f5c50"   # AI 服务（灰绿）
C_PANEL= "#fbfbf6"; E_PANEL= "#d9d6cc"
C_TXT  = "#333333"; C_MUTED= "#8a8a8a"; C_HOT = "#b5402f"
C_NSBG = "#f4f6fb"; C_DEPBG= "#eef7f3"

fig, ax = plt.subplots(figsize=(17.4, 11.4))
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


def alabel(x, y, s, color, fs=7.2, z=7):
    ax.text(x, y, s, ha="center", va="center", fontsize=fs, color=color, zorder=z,
            bbox=dict(boxstyle="round,pad=0.24", fc="white", ec=color, lw=0.8, alpha=0.96))


# ===================== 标题 =====================
ax.text(50, 97.6, "OpenViking 系统架构：面向 AI Agent 的上下文文件系统", ha="center",
        fontsize=18, fontweight="bold", color="#222")
ax.text(50, 94.2,
        "以 viking:// 虚拟文件系统统一「记忆 / 资源 / 技能」——分层加载 L0/L1/L2 · 目录递归检索 · 自演化会话管理",
        ha="center", fontsize=9.6, color=C_MUTED)

# 主栈区域：x 2.5 .. 63.5（宽 61），右侧面板 x 66 .. 98
LX, LW = 3.0, 60.5
lcx = LX + LW / 2

# ===================================================================
# ① 客户端层
# ===================================================================
box(LX - 1.0, 80.5, LW + 2.0, 8.6, "#f7fafc", ec=E_CLI, lw=1.4, r=1.0, ls=(0, (5, 3)), z=1)
txt(LX + 0.6, 87.7, "① 客户端层  Client Layer", fs=9.4, bold=True, color=T_CLI)
clients = [
    ("ov  CLI", "Rust · ls/tree/find/grep/chat"),
    ("AsyncOpenViking", "Python SDK · 嵌入(本地)模式"),
    ("AsyncHTTPClient", "远程客户端 · 服务模式"),
]
cw = (LW - 4.0) / 3
for i, (t, s) in enumerate(clients):
    cxp = LX + 1.0 + i * (cw + 1.0)
    box(cxp, 81.4, cw, 4.3, C_CLI, ec=E_CLI, lw=1.2, r=0.5)
    txt(cxp + cw / 2, 84.2, t, fs=8.6, bold=True, ha="center", color=T_CLI)
    txt(cxp + cw / 2, 82.4, s, fs=6.6, ha="center", color=T_CLI)

# ===================================================================
# ② 服务编排层
# ===================================================================
box(LX - 1.0, 65.5, LW + 2.0, 12.0, C_DEPBG, ec=E_SVC, lw=1.6, r=1.0, ls=(0, (5, 3)), z=1)
txt(LX + 0.6, 76.0, "② 服务编排层  Service Orchestration", fs=9.4, bold=True, color=T_SVC)
# OpenVikingService 头带
box(LX + 1.0, 72.0, LW - 2.0, 3.4, C_SVC, ec=E_SVC, lw=1.4, r=0.5)
txt(lcx, 73.7, "OpenVikingService · 中央编排（统一入口 · 多租户 RequestContext[account_id]）",
    fs=8.4, bold=True, ha="center", color=T_SVC)
svcs = [
    ("FSService", "文件系统操作 · 路径/URI 管理"),
    ("ResourceService", "内容摄取 · L0/L1/L2 加工"),
    ("Session / Memory 服务", "会话抽取 · 自演化"),
]
sw = (LW - 4.0) / 3
for i, (t, s) in enumerate(svcs):
    sxp = LX + 1.0 + i * (sw + 1.0)
    box(sxp, 66.6, sw, 4.4, "#eef7f2", ec=E_SVC, lw=1.1, r=0.5)
    txt(sxp + sw / 2, 69.4, t, fs=8.0, bold=True, ha="center", color=T_SVC)
    txt(sxp + sw / 2, 67.6, s, fs=6.5, ha="center", color="#3f6b5a")

# ===================================================================
# ③ 存储抽象层（三列）
# ===================================================================
box(LX - 1.0, 44.0, LW + 2.0, 19.0, "#fbfaf6", ec=E_FS, lw=1.6, r=1.0, ls=(0, (5, 3)), z=1)
txt(LX + 0.6, 61.4, "③ 存储抽象层  Storage Abstraction", fs=9.4, bold=True, color=T_FS)
stores = [
    (C_FS, E_FS, T_FS, "VikingFS", "虚拟文件系统",
     ["viking:// 协议 · URI/路径映射", "多租户隔离(account_id)", "ls / find / grep / tree", "L0/L1/L2 分层对象"]),
    (C_DISK, E_DISK, T_DISK, "AGFS", "分布式文件系统(Go)",
     ["local / S3 / memory 后端", "底层持久化", "嵌入模式经 Rust FFI", "RAGFSBindingClient"]),
    (C_VEC, E_VEC, T_VEC, "VikingVectorIndexBackend", "向量索引(多租户)",
     ["存 L0 摘要向量", "语义召回入口", "dense/sparse/hybrid", "对接 VikingDB 等"]),
]
stw = (LW - 4.0) / 3
for i, (fc, ec, tc, t, sub, items) in enumerate(stores):
    sxp = LX + 1.0 + i * (stw + 1.0)
    box(sxp, 45.0, stw, 14.6, fc, ec=ec, lw=1.3, r=0.6)
    txt(sxp + stw / 2, 57.6, t, fs=8.2, bold=True, ha="center", color=tc)
    txt(sxp + stw / 2, 55.7, sub, fs=6.7, ha="center", color=tc)
    iy = 53.3
    for it in items:
        txt(sxp + stw / 2, iy, "· " + it, fs=6.6, ha="center", color=C_TXT)
        iy -= 2.15

# ===================================================================
# ④ AI 服务集成层
# ===================================================================
box(LX - 1.0, 33.0, LW + 2.0, 8.6, "#eef3f0", ec=E_AI, lw=1.4, r=1.0, ls=(0, (5, 3)), z=1)
txt(LX + 0.6, 40.2, "④ AI 服务集成层  AI Services Integration", fs=9.4, bold=True, color=T_AI)
ais = [
    ("VLMFactory", "Volcengine Doubao / OpenAI / LiteLLM · 摘要生成/理解"),
    ("EmbedderBase", "dense / sparse / hybrid 向量 · 13+ 供应商"),
]
aw = (LW - 3.0) / 2
for i, (t, s) in enumerate(ais):
    axp = LX + 1.0 + i * (aw + 1.0)
    box(axp, 33.9, aw, 4.3, C_AI, ec=E_AI, lw=1.2, r=0.5)
    txt(axp + aw / 2, 36.7, t, fs=8.4, bold=True, ha="center", color=T_AI)
    txt(axp + aw / 2, 34.9, s, fs=6.4, ha="center", color=T_AI)

# ----- 层间下行箭头（请求路径）-----
for y0, y1 in [(80.3, 77.7), (65.3, 63.2), (43.8, 41.8)]:
    arrow(lcx, y0, lcx, y1, color="#9b988c", lw=2.0, style="-|>", z=6)

# ===================================================================
# 右侧面板 A —— viking:// 命名空间
# ===================================================================
NX, NW = 66.0, 32.0
box(NX, 60.0, NW, 29.2, C_NSBG, ec="#b9c6df", lw=1.4, r=1.0, z=1)
txt(NX + 1.4, 87.4, "viking:// 命名空间（统一上下文）", fs=9.0, bold=True, color="#2f4a86")
ns_lines = [
    ("viking://", "根 · 上下文即文件系统", True),
    ("├─ resources/", "外部文档 / 代码库 / 网页", False),
    ("├─ user/", "用户维度上下文", False),
    ("│   ├─ memories/", "用户记忆 / 偏好", False),
    ("│   ├─ resources/", "用户私有资源", False),
    ("│   ├─ skills/", "技能 / 过程知识", False),
    ("│   └─ peers/", "协作(peer)共享记忆", False),
    ("└─ agent/", "Agent 任务经验(自演化)", False),
]
ny = 84.6
for path, note, isroot in ns_lines:
    txt(NX + 1.6, ny, path, fs=7.6, bold=isroot,
        color="#2f4a86" if isroot else "#40507a", mono=True)
    txt(NX + 15.6, ny, note, fs=6.4, color=C_MUTED)
    ny -= 2.75
txt(NX + 1.6, ny - 0.4, "每个对象 = 唯一 URI · 可 ls/find/grep 确定性定位",
    fs=6.4, color=C_HOT)

# ===================================================================
# 右侧面板 B —— 两种部署模式
# ===================================================================
box(NX, 42.5, NW, 15.6, C_DEPBG, ec=E_SVC, lw=1.4, r=1.0, z=1)
txt(NX + 1.4, 56.2, "两种部署模式", fs=9.0, bold=True, color=T_SVC)
box(NX + 1.4, 49.2, NW - 2.8, 5.4, "#eaf5ef", ec=E_SVC, lw=1.1, r=0.5)
txt(NX + 2.6, 52.9, "嵌入模式 Embedded", fs=7.8, bold=True, color=T_SVC)
txt(NX + 2.6, 50.7, "AsyncOpenViking + 本地路径 · AGFS 进程内(Rust FFI) · 零网络延迟",
    fs=6.3, color="#3f6b5a")
box(NX + 1.4, 43.2, NW - 2.8, 5.4, "#eef2fb", ec=E_CLI, lw=1.1, r=0.5)
txt(NX + 2.6, 46.9, "服务模式 HTTP Server", fs=7.8, bold=True, color=T_CLI)
txt(NX + 2.6, 44.7, "openviking-server · REST API(:1933) · API-Key 多租户隔离",
    fs=6.3, color="#2f5f86")

# ===================================================================
# 右侧面板 C —— 技术栈
# ===================================================================
box(NX, 33.0, NW, 8.0, C_PANEL, ec=E_PANEL, lw=1.2, r=1.0, z=1)
txt(NX + 1.4, 39.2, "多语言技术栈（polyglot）", fs=8.4, bold=True, color=C_TXT)
stack = ["Python 3.10+ 核心/SDK", "Rust CLI + FFI 绑定",
         "Go 1.22+ AGFS 文件服务", "C++17 向量扩展"]
sy = 36.7
for i, s in enumerate(stack):
    col = i % 2
    row = i // 2
    txt(NX + 1.8 + col * 15.5, sy - row * 2.4, "· " + s, fs=6.6, color="#555")

# ===================== 页脚 =====================
ax.text(3.0, 27.4,
        "● 核心思想：上下文即文件系统。记忆 / 资源 / 技能统一为 viking:// 下的虚拟目录，每个对象一个 URI，"
        "可像操作文件一样确定性地组织、检索、加载。",
        ha="left", fontsize=7.9, color="#555")
ax.text(3.0, 23.6,
        "● 请求下行：客户端(ov/SDK/HTTP) → OpenVikingService 编排 → 存储抽象(VikingFS 虚拟层 / AGFS 持久化 / 向量索引) "
        "→ AI 服务(VLM 生成摘要 · Embedder 生成向量)。",
        ha="left", fontsize=7.9, color="#555")
ax.text(3.0, 19.8,
        "● 分层加载 L0/L1/L2：摘要(~100 tok) → 概览(~2k tok) → 详情(按需)，先扫摘要再决定是否付出读全文的 token 成本。",
        ha="left", fontsize=7.9, color=T_FS)
ax.text(3.0, 16.0,
        "● 端侧相关配置：嵌入模式 + AGFS 本地/内存后端 = 进程内、零网络的单机形态，是本目录「端侧 Agent 记忆」语境下最可迁移的部分。",
        ha="left", fontsize=7.9, color=C_HOT)
ax.text(3.0, 11.4,
        "图例：蓝 = 客户端　绿 = 服务编排(核心)　橙 = VikingFS 虚拟文件系统　陶土 = AGFS 持久化　紫 = 向量索引　灰绿 = AI 服务",
        ha="left", fontsize=7.4, color=C_MUTED)
ax.text(3.0, 8.2,
        "来源：openviking.ai · github.com/volcengine/OpenViking · deepwiki · 官方文档 · VikingMem (VLDB 2026)。"
        "组件名依 DeepWiki 分层拆解，随版本演进可能微调。",
        ha="left", fontsize=6.8, color=C_MUTED)

plt.tight_layout()
_here = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(_here, "openviking-arch.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(_here, "openviking-arch.svg"),
            bbox_inches="tight", facecolor="white")
print("Saved: openviking-arch.png / .svg")

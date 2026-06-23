#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproduce "The Scissors" conflict figure (agent-era-memory-workload-conflict.svg):
stacked end-device demand (traditional apps + conservative on-device AI) vs LPDDR
capacity and user-available memory, with an aggressive-AI demand line and the
deficit wedge where that demand exceeds user-available memory.

Run:
    pip install matplotlib numpy
    python agent-era-memory-workload-conflict.py
Output: agent-era-memory-workload-conflict.png / .svg in the same folder.

Labels are kept in English to match the source figure. For a Chinese version,
swap the strings and prepend a CJK font to font.sans-serif (e.g. 'Microsoft YaHei').
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# ---------------------------------------------------------------- global style
matplotlib.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["svg.fonttype"] = "none"   # keep text editable in exported SVG

# ---------------------------------------------------------------- palette (matches SVG)
C_TRAD   = "#5589b8"   # traditional apps (blue)
C_AICONS = "#e8a35e"   # conservative on-device AI (orange)
C_CAP    = "#1a4f7a"   # LPDDR capacity + user-available (dark blue)
C_AGG    = "#c43c3c"   # aggressive AI demand (red)
C_DEF    = "#d62828"   # deficit (red)
C_CROSS  = "#b03030"   # crossover / deficit annotation
C_PROJ   = "#f6f6f0"   # projection band
C_MUTED  = "#777777"

# ---------------------------------------------------------------- data (median flagship, GB)
years      = np.array([2024, 2025, 2026, 2027, 2028], dtype=float)
trad       = np.array([4.0, 5.0, 6.0, 7.0, 8.0])      # traditional apps
trad_aic   = np.array([5.5, 7.5, 9.5, 11.5, 13.5])    # traditional + conservative AI (stack top)
ai_cons    = trad_aic - trad                          # conservative-AI increment (stacked on top)
capacity   = np.array([12, 16, 16, 20, 24], dtype=float)   # LPDDR total
user_avail = np.array([9, 12, 12, 15, 18], dtype=float)    # capacity - OS/driver/system reserve
aggressive = np.array([5.5, 7.5, 11, 17, 24], dtype=float) # traditional + aggressive (agentic) AI

PROJ_START = 2026.0   # SVG draws the projection band from x=2026 (label reads "2026.5 — 2028")


def first_crossing(x, upper, lower):
    """First point where `upper` rises from below to above `lower`."""
    d = upper - lower
    for i in range(len(x) - 1):
        if d[i] <= 0 <= d[i + 1]:
            t = (0 - d[i]) / (d[i + 1] - d[i])
            return x[i] + t * (x[i + 1] - x[i]), lower[i] + t * (lower[i + 1] - lower[i])
    return None


x_cross, y_cross = first_crossing(years, aggressive, user_avail)   # ~ (2026.33, 13.0)

# ---------------------------------------------------------------- canvas
fig = plt.figure(figsize=(11.0, 7.4))
ax = fig.add_axes([0.075, 0.215, 0.86, 0.655])   # [left, bottom, width, height] (nudge if cramped)

# projection band (bottom layer)
ax.axvspan(PROJ_START, years[-1], color=C_PROJ, zorder=0)
ax.text((PROJ_START + years[-1]) / 2, 31.2, "Projection (2026.5 — 2028)",
        ha="center", va="top", fontsize=10, color=C_MUTED, zorder=1)

# grid behind data
ax.set_axisbelow(True)
ax.grid(axis="y", linestyle=(0, (2, 3)), color="#e6e6e6", linewidth=1)

# ---------------------------------------------------------------- stacked demand areas
polys = ax.stackplot(years, trad, ai_cons, colors=[C_TRAD, C_AICONS], zorder=2)
polys[0].set_alpha(0.55)   # traditional
polys[1].set_alpha(0.65)   # conservative AI

# ---------------------------------------------------------------- deficit wedge
# where aggressive demand exceeds user-available memory (interpolate -> exact crossover)
ax.fill_between(years, aggressive, user_avail, where=(aggressive >= user_avail),
                interpolate=True, color=C_DEF, alpha=0.30, linewidth=0, zorder=3)

# ---------------------------------------------------------------- lines
ax.plot(years, capacity, color=C_CAP, linewidth=2.0, zorder=4)            # LPDDR total (solid)
ax.scatter(years, capacity, s=16, color=C_CAP, zorder=5)
ax.plot(years, user_avail, color=C_CAP, linewidth=1.5,
        linestyle=(0, (6, 4)), zorder=4)                                  # user-available (dashed blue)
ax.plot(years, aggressive, color=C_AGG, linewidth=2.2,
        linestyle=(0, (6, 3)), zorder=4)                                  # aggressive demand (dashed red)
ax.scatter(years, aggressive, s=16, color=C_AGG, zorder=5)

# crossover marker
ax.scatter([x_cross], [y_cross], s=48, color=C_CROSS,
           edgecolor="white", linewidth=1.5, zorder=6)
ax.text(x_cross + 0.05, y_cross + 0.8, "Crossover ≈ 2027",
        fontsize=11, fontweight="bold", color=C_CROSS, zorder=7)

# ---------------------------------------------------------------- inline labels
ax.text(2024.08, 1.9, "Traditional apps (browser, messengers, photos)",
        fontsize=10, color=C_CAP, zorder=7)
ax.text(2024.55, 6.7, "On-device AI — conservative (1 model, ≤32K ctx)",
        fontsize=10, color="#7a4a10", zorder=7)
ax.text(2024.08, 12.7, "Flagship LPDDR capacity (median)",
        fontsize=10, color=C_CAP, zorder=7)
ax.text(2024.08, 9.5, "User-available (cap − OS/driver reserve)",
        fontsize=10, color=C_CAP, zorder=7)
ax.text(2024.08, 5.6, "Demand: trad + aggressive AI (agentic, 128K+ ctx, multi-model)",
        fontsize=10, color=C_AGG, zorder=7)

# right-edge endpoint labels
ax.text(2028.07, 24.0, "24 GB", fontsize=10, color=C_CAP, va="center")
ax.text(2028.07, 22.6, "↑ aggressive demand touches ceiling", fontsize=9.5, color=C_AGG, va="center")
ax.text(2028.07, 18.0, "18 GB", fontsize=10, color=C_CAP, va="center")

# deficit annotation + arrow into the wedge
ax.text(2026.95, 21.6, "Deficit zone", fontsize=11, fontweight="bold", color=C_CROSS, zorder=7)
ax.text(2026.95, 20.7, "demand > user-available", fontsize=10, color=C_CROSS, zorder=7)
ax.annotate("", xy=(2027.6, 18.2), xytext=(2027.25, 20.2),
            arrowprops=dict(arrowstyle="->", color=C_CROSS, linewidth=1.5), zorder=7)

# ---------------------------------------------------------------- axes
ax.set_xlim(2023.85, 2029.95)
ax.set_ylim(0, 32)
ax.set_xticks(years)
ax.set_xticklabels([int(y) for y in years])
ax.set_yticks([0, 4, 8, 12, 16, 20, 24, 28, 32])
ax.set_xlabel("Year (median flagship)", fontsize=11, color="#666")
ax.set_ylabel("Memory (GB)", fontsize=11, color="#666")
ax.tick_params(colors=C_MUTED)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color("#888")

# ---------------------------------------------------------------- title / subtitle
fig.text(0.5, 0.965, "The Scissors: End-Device Memory Demand vs Supply (2024 — 2028)",
         ha="center", fontsize=15, fontweight="bold", color="#222")
fig.text(0.5, 0.928,
         "Conservative AI fits; agentic AI does not — deficit opens around 2027 on a median 16–20 GB flagship.",
         ha="center", fontsize=10.5, color="#555")

# ---------------------------------------------------------------- legend (below axes)
handles = [
    Patch(facecolor=C_TRAD, alpha=0.55, label="Traditional apps"),
    Patch(facecolor=C_AICONS, alpha=0.65, label="Conservative AI (single resident model)"),
    Line2D([0], [0], color=C_CAP, lw=2.0, label="LPDDR total"),
    Line2D([0], [0], color=C_CAP, lw=1.5, linestyle=(0, (6, 4)), label="User-available"),
    Line2D([0], [0], color=C_AGG, lw=2.2, linestyle=(0, (6, 3)),
           label="Aggressive AI demand (trad + agentic + 128K KV + multi-model)"),
    Patch(facecolor=C_DEF, alpha=0.30, label="Deficit (demand > user-available)"),
]
ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09),
          ncol=3, frameon=True, fontsize=9, handlelength=1.8, columnspacing=1.5)

# ---------------------------------------------------------------- footnote
fig.text(0.075, 0.052,
         "Annual growth (median flagship): LPDDR capacity ~17%/yr · traditional apps ~18%/yr · "
         "conservative AI ~37%/yr · aggressive AI demand ~45%/yr from 2026.",
         fontsize=7.8, color=C_MUTED)
fig.text(0.075, 0.028,
         "Caveat: values from 2026.5 onward are projections.",
         fontsize=7.8, color=C_MUTED)

# ---------------------------------------------------------------- output
fig.savefig("agent-era-memory-workload-conflict.png", dpi=150)
fig.savefig("agent-era-memory-workload-conflict.svg")
print("wrote agent-era-memory-workload-conflict.png / .svg")
# plt.show()

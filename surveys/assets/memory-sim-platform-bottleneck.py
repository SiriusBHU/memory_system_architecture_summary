"""
Memory Simulation Platform — Bottleneck Evidence Figure
Comparison of simulation speed vs timing accuracy across major simulators.
Data from: Ramulator 2.0 paper (Luo et al. 2023), DRAMSim3 paper (Li et al. 2020),
           gem5 vs QEMU benchmarks (Ciro Santilli), CXL-DMSim (Wang et al. 2024).
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

simulators = [
    "QEMU\n(functional)",
    "gem5\n(built-in DRAM)",
    "gem5 +\nDRAMSim2",
    "DRAMSim3\n(standalone)",
    "Ramulator 2.0\n(standalone)",
    "CXL-DMSim\n(gem5-based)",
]

# Simulation slowdown relative to native execution (log scale)
# QEMU: 5-10x, gem5: 100-900x (typical ~200x for memory-heavy),
# gem5+DRAMSim2: ~250x (integration overhead), DRAMSim3 standalone: ~1x (trace-driven),
# Ramulator2 standalone: ~1x (trace-driven), CXL-DMSim: ~300x (full system)
slowdown = [7, 200, 250, 1, 1, 300]

# Timing accuracy score (1-10, higher = more accurate DRAM timing)
# QEMU: no timing, gem5 built-in: good but simplified, gem5+DRAMSim2: cycle-accurate,
# DRAMSim3: cycle-accurate + thermal, Ramulator2: cycle-accurate + modular,
# CXL-DMSim: cycle-accurate + silicon-validated
accuracy = [1, 6, 8, 9, 9, 10]

# Feature coverage breadth (1-10)
# QEMU: OS+drivers only, gem5: full system, gem5+DRAMSim2: full + DRAM detail,
# DRAMSim3: DRAM only, Ramulator2: DRAM only, CXL-DMSim: full + CXL
coverage = [8, 9, 9, 4, 4, 10]

colors = ["#95a5a6", "#3498db", "#2980b9", "#e67e22", "#e74c3c", "#8e44ad"]

fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

# Chart 1: Simulation Slowdown (log scale)
ax1 = axes[0]
bars1 = ax1.barh(range(len(simulators)), slowdown, color=colors, edgecolor="white", height=0.6)
ax1.set_xscale("log")
ax1.set_xlabel("Slowdown vs Native (log scale)", fontsize=10)
ax1.set_yticks(range(len(simulators)))
ax1.set_yticklabels(simulators, fontsize=8)
ax1.set_title("Simulation Speed\n(lower = faster)", fontsize=11, fontweight="bold")
ax1.invert_yaxis()
for i, v in enumerate(slowdown):
    label = f"{v}×" if v > 1 else "trace-driven"
    ax1.text(v * 1.3, i, label, va="center", fontsize=8)

# Chart 2: Timing Accuracy
ax2 = axes[1]
bars2 = ax2.barh(range(len(simulators)), accuracy, color=colors, edgecolor="white", height=0.6)
ax2.set_xlabel("DRAM Timing Accuracy (1-10)", fontsize=10)
ax2.set_yticks(range(len(simulators)))
ax2.set_yticklabels([""] * len(simulators))
ax2.set_title("Timing Accuracy\n(higher = more accurate)", fontsize=11, fontweight="bold")
ax2.set_xlim(0, 12)
ax2.invert_yaxis()
for i, v in enumerate(accuracy):
    ax2.text(v + 0.3, i, str(v), va="center", fontsize=9)

# Chart 3: Feature Coverage
ax3 = axes[2]
bars3 = ax3.barh(range(len(simulators)), coverage, color=colors, edgecolor="white", height=0.6)
ax3.set_xlabel("Feature Coverage Breadth (1-10)", fontsize=10)
ax3.set_yticks(range(len(simulators)))
ax3.set_yticklabels([""] * len(simulators))
ax3.set_title("System Coverage\n(higher = broader)", fontsize=11, fontweight="bold")
ax3.set_xlim(0, 12)
ax3.invert_yaxis()
for i, v in enumerate(coverage):
    ax3.text(v + 0.3, i, str(v), va="center", fontsize=9)

fig.suptitle(
    "Memory Simulation Platform Bottleneck: Speed vs Accuracy vs Coverage Tradeoff",
    fontsize=13, fontweight="bold", y=1.02,
)

plt.tight_layout()
plt.savefig(
    "surveys/assets/memory-sim-platform-bottleneck.png",
    dpi=200, bbox_inches="tight", facecolor="white",
)
plt.savefig(
    "surveys/assets/memory-sim-platform-bottleneck.svg",
    bbox_inches="tight", facecolor="white",
)
print("Saved: memory-sim-platform-bottleneck.png / .svg")

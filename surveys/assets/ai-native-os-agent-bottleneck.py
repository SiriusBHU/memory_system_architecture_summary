"""
AI-Native / Agentic OS — Bottleneck Evidence Figure
Mobile GUI / agent task success rates: where the "old way" (structureless,
pure-GUI, no memory) hits a ceiling, and what closes the gap (memory +
system-level intent/function exposure).

Data (all cited in the survey):
- AppAgent no memory: 16.9%  / AppAgent + chain memory: 70.8% / AppAgentX: 71.4%
    [AppAgentX, arXiv 2503.02268, 2025]
- AndroidWorld original paper best: 30.6%  -> 2026 SOTA: >90%
    [AndroidWorld, arXiv 2405.14573, 2024]
- MobileWorld best agentic framework: 51.7%  (harder, anti-saturation benchmark)
    [MobileWorld, arXiv 2512.19432, 2026]
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ordered ascending to show the trajectory
labels = [
    "AppAgent\n(no memory, pure-GUI)",
    "AndroidWorld\n(2024 best baseline)",
    "MobileWorld\n(2026 best, harder bench)",
    "AppAgent\n(+ chain memory)",
    "AppAgentX\n(evolved memory)",
    "AndroidWorld\n(2026 SOTA)",
]
success = [16.9, 30.6, 51.7, 70.8, 71.4, 90.0]
# gray = old/structureless ceiling; orange = harder bench mid; green = evolved
colors = ["#95a5a6", "#95a5a6", "#e67e22", "#27ae60", "#27ae60", "#27ae60"]
note = ["", "", "", "", "", ">90"]

fig, ax = plt.subplots(figsize=(11, 5.6))
y = range(len(labels))
bars = ax.barh(y, success, color=colors, edgecolor="white", height=0.62)
ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Task success rate on mobile agent benchmarks (%)", fontsize=11)
ax.set_xlim(0, 100)
ax.set_title(
    "AI-Native OS Bottleneck: structureless GUI agents stall ~17-31%;\n"
    "system-level intent exposure + memory lifts cross-app success to 70-90%",
    fontsize=12, fontweight="bold",
)
for i, v in enumerate(success):
    txt = f">{int(v)}%" if note[i] else f"{v:.1f}%"
    ax.text(v + 1.2, i, txt, va="center", fontsize=9, fontweight="bold")

# divider annotation between "old ceiling" and "evolved"
ax.axvline(50, color="#bbbbbb", linestyle=":", linewidth=1)
ax.text(50, -0.7, "  ~50% wall", color="#888888", fontsize=8, va="bottom")

import matplotlib.patches as mpatches
legend = [
    mpatches.Patch(color="#95a5a6", label="Original: structureless / pure-GUI / no memory"),
    mpatches.Patch(color="#e67e22", label="Harder 2026 benchmark (still mid)"),
    mpatches.Patch(color="#27ae60", label="Evolved: + memory / system intent exposure"),
]
ax.legend(handles=legend, loc="lower right", fontsize=8.5, framealpha=0.95)

plt.tight_layout()
plt.savefig("surveys/assets/ai-native-os-agent-bottleneck.png",
            dpi=200, bbox_inches="tight", facecolor="white")
plt.savefig("surveys/assets/ai-native-os-agent-bottleneck.svg",
            bbox_inches="tight", facecolor="white")
print("Saved: ai-native-os-agent-bottleneck.png / .svg")

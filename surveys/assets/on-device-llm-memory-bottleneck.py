"""
On-Device LLM Memory/Compute Subsystem — Bottleneck Evidence Figure (2 panels)

Panel 1 — Why "per-app bolt-on model" does not scale:
  total weight RAM grows O(N) when each app bundles its own ~1.5 GB int4 model,
  vs O(1) flat when the OS hosts ONE system-shared model (Android AICore /
  Apple Foundation Models). A 8-12 GB phone budget is blown after a few apps.
    [3B int4 ~= 1.5-2 GB: Gemini Nano tech report arXiv 2312.11805 + footprint math;
     AICore shared-single-instance: developer.android.com/ai/gemini-nano]

Panel 2 — Why you cannot dodge duplication by streaming weights from flash:
  decode is memory-bandwidth-bound (token/s ~= bandwidth / model bytes), and the
  storage hierarchy spans ~3 orders of magnitude, so weights must stay resident
  in high-bandwidth LPDDR.
    [DC GPU HBM 2-3 TB/s, mobile LPDDR 50-90 GB/s: v-chandra.github.io/on-device-llms 2026;
     LPDDR5X ~85 GB/s (Snapdragon 8 Elite, Notebookcheck);
     UFS 4.0 seq read 4.2 GB/s: Samsung official]
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.6))

# ---- Panel 1: footprint O(N) vs O(1) ----
n_apps = np.array([1, 2, 4, 6, 8])
per_model_gb = 1.5  # 3B int4 ~ 1.5 GB
dup = n_apps * per_model_gb
shared = np.full_like(n_apps, per_model_gb, dtype=float)

ax1.plot(n_apps, dup, "o-", color="#e74c3c", linewidth=2.4, markersize=8,
         label="Original: per-app duplicated weights  (O(N))")
ax1.plot(n_apps, shared, "s-", color="#27ae60", linewidth=2.4, markersize=8,
         label="Evolved: system-shared single model  (O(1))")
ax1.axhspan(8, 12, color="#f1c40f", alpha=0.18)
ax1.axhline(12, color="#b7950b", linestyle="--", linewidth=1.2)
ax1.text(1.05, 12.2, "phone DRAM budget (8-12 GB, shared with OS + apps)",
         color="#7d6608", fontsize=8.5, va="bottom")
ax1.set_xlabel("Number of AI-using apps", fontsize=11)
ax1.set_ylabel("Total model-weight RAM (GB)", fontsize=11)
ax1.set_title("Model footprint: bolt-on per-app vs system-shared\n"
              "(each model ~1.5 GB, 3B @ int4)", fontsize=11.5, fontweight="bold")
ax1.set_xticks(n_apps)
ax1.set_ylim(0, 14)
ax1.legend(loc="upper left", fontsize=9)
for x, v in zip(n_apps, dup):
    ax1.text(x, v + 0.3, f"{v:.0f}", ha="center", fontsize=8.5, color="#c0392b")

# ---- Panel 2: bandwidth hierarchy (log) ----
tiers = ["DC GPU\nHBM", "Mobile\nLPDDR5X", "UFS 4.0\n(seq read)", "Old UFS\n(random)"]
bw = [2500, 85, 4.2, 1.0]  # GB/s
bcolors = ["#8e44ad", "#27ae60", "#e67e22", "#95a5a6"]
xb = range(len(tiers))
ax2.bar(xb, bw, color=bcolors, edgecolor="white", width=0.62)
ax2.set_yscale("log")
ax2.set_xticks(xb)
ax2.set_xticklabels(tiers, fontsize=9)
ax2.set_ylabel("Bandwidth (GB/s, log scale)", fontsize=11)
ax2.set_title("Memory wall: decode is bandwidth-bound\n"
              "weights must stay resident in LPDDR (~20x faster than flash)",
              fontsize=11.5, fontweight="bold")
for x, v in zip(xb, bw):
    lab = f"{v:.0f}" if v >= 10 else f"{v:.1f}"
    ax2.text(x, v * 1.15, f"{lab} GB/s", ha="center", fontsize=9, fontweight="bold")
ax2.annotate("", xy=(1, 85), xytext=(2, 4.2),
             arrowprops=dict(arrowstyle="<->", color="#555", lw=1.3))
ax2.text(1.5, 20, "~20x", ha="center", fontsize=9, color="#555", fontweight="bold")

fig.suptitle("On-Device LLM Memory Bottleneck: per-app duplication is unaffordable, "
             "and flash is too slow to stream weights -> share one resident model",
             fontsize=12.5, fontweight="bold", y=1.03)
plt.tight_layout()
plt.savefig("surveys/assets/on-device-llm-memory-bottleneck.png",
            dpi=200, bbox_inches="tight", facecolor="white")
plt.savefig("surveys/assets/on-device-llm-memory-bottleneck.svg",
            bbox_inches="tight", facecolor="white")
print("Saved: on-device-llm-memory-bottleneck.png / .svg")

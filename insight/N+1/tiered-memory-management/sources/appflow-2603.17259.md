# AppFlow (MobiCom'26) — local source notes

- **Title:** AppFlow: Memory Scheduling for Cold Launch of Large Apps on Mobile and Vehicle Systems
- **Authors:** Xiaochen Li, Sicong Liu, Bin Guo, Yu Ouyang, Fengmin Wu, Yuan Xu, Zhiwen Yu
- **Venue/Year:** arXiv:2603.17259, 2026; accepted to MobiCom '26
- **URL:** https://arxiv.org/abs/2603.17259  (HTML: https://arxiv.org/html/2603.17259)
- **Devices:** Google Pixel 7 / Pixel 8 (capped to 6 GB / 8 GB DRAM), Raspberry Pi 4B
  vehicle board (4 GB), all Android 15. 60+ real apps, 100-day trace, 10k+ multitask switches.
  Eight GB-scale test apps incl. on-device LLMs (Qwen2.5, Gemma), TikTok, Snow, PUBG.

## Problem
Large apps (on-device LLMs, rich media) have heavy memory + I/O demand. Under multitasking,
the OS reclaims pages or kills processes, so a "warm" app becomes a **cold launch**.
Measured: **86.6% of GB-scale cold launches exceed 1 second** (the usability cliff).

## Three components (prediction-driven, file-access patterns are predictable)
1. **Selective File Preloader** — before-launch loads small frequent files (<128 KB);
   during-launch streams large files (>=128 KB) with big I/O blocks. Knapsack sizing in
   <0.1 ms, 100 MB preload budget. Contributes **26.1%** launch-time reduction.
2. **Adaptive Memory Reclaimer** — decouples file-backed vs anonymous reclaim by pressure;
   high pressure -> evict file-backed first (no I/O); tags preloaded pages to avoid premature
   eviction. Trigger at 12,800 pages/100 ms allocation rate. Contributes **60%** reduction.
3. **Context-Aware Process Killer** — picks victims by net freed memory
   ΔM = M_current − M_relaunch; defers recently-used apps. **30% fewer** kill events vs LRU.

## Headline numbers
- **Cold launch latency: −66.5% overall** (example **2 s → 690 ms**).
- **95% of launches within 1 s**, sustained over a 100-day test (vs 86.6% over-1s before).
- Average **33.7%–43.6%** shorter latency vs Android baseline; **up to 57%** under pressure
  on a 6 GB device.
- **I/O throughput: 2.35×** higher during GB-scale launches.
- **Kernel direct reclaims: −67.9%** vs stock Android.
- **LMK (low-memory-killer) events: −33.7%**; **1.85×** more background apps stay resident.
- vs Paralfetch (preload baseline): **29.2%** faster; vs Acclaim (reclaim baseline): **40.8%**;
  vs naive Paralfetch+Acclaim: **56.7%** faster.
- In-vehicle navigation launch: **−53.4%** (4.3 s → 2.0 s on 4 GB board).

## Why it matters for terminal tiering
AppFlow closes the loop: **prediction-driven preload + access-aware reclaim + smart kill**
keep the working set resident and push cold pages down the tiers *before* pressure forces
an OOM kill. It is the clearest end-to-end "evolved tiering" result with user-visible numbers.

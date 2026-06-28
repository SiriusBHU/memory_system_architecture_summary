# AppFlow: Memory Scheduling for Cold Launch of Large Apps on Mobile and Vehicle Systems

- arXiv: 2603.17259 — https://arxiv.org/abs/2603.17259 (HTML: https://arxiv.org/html/2603.17259v1)

## Local extract (key claims)

Problem: GB-scale large apps (on-device LLMs, rich media editors) make the OS reclaim/kill processes during multitasking, turning warm apps into cold launches. "1s is the usability cliff," yet **86.6% of GB-scale cold launches exceed it**.

### Three components (prediction-driven, system-wide scheduler)
1. **Selective File Preloader** — time-split preloading: load frequency-intensive small files before launch, stream large files during launch with optimized block sizes.
2. **Adaptive Memory Reclaimer** — decouples file-backed vs anonymous page reclamation; prioritizes file pages under pressure while protecting preloaded data.
3. **Context-Aware Process Killer** — kills long-running memory-intensive apps by *net memory recovery* rather than LRU order.

### Quantitative results
- **−66.5%** cold-launch latency overall; example **2 s → 690 ms**.
- Sustains **95% of launches within 1 s** over a 100-day test.
- **2.35×** higher I/O throughput.
- **−67.9%** direct-reclaim events (memory pressure).
- **33.7–43.6%** shorter cold-launch latency than native Android.

### Relevance
Shows that *prediction + context-aware* memory scheduling (preload / reclaim / kill) beats generic LRU-order policy on real devices, and quantifies the cold-launch bottleneck (86.6% miss the 1 s cliff). The prediction here is on-device and context-aware; the natural next step is making that prediction *personalized and scenario-aware* via an edge-cloud loop, which is this survey's evolved solution.

# On-Device Tiered Memory Management: From Single-Tier DRAM Reclaim to DRAM↔Compressed RAM↔Flash Tiering

> This document compares memory management for terminal devices with bounded RAM (phones, tablets, PCs, in-vehicle systems, edge boards): the original approach (single-tier DRAM + generic global reclaim + naive swap, OOM-killing under pressure) versus the evolved approach (explicit tiering: DRAM ↔ compressed RAM zram/zswap ↔ Flash/UFS swap, driven by access-aware hot/cold placement — MGLRU, demotion/prefetch). Sources span the kernel community 2022–2026 (MGLRU, PSI, LMKD), academia (DAC'24, ATC'25, FAST'25, MobiCom'26), and industry (Apple memory compression, Samsung RAM Plus, Huawei HyperSpace Memory).

## 1. Scope and method

**Domain definition.** On resource-constrained terminal devices, how the OS spreads a **fixed-capacity** physical RAM across multiple tiers: DRAM (fast, expensive, small) ↔ compressed RAM (zram/zswap, holding cold anonymous pages in-RAM at ~2:1) ↔ Flash/UFS swap (slow, cheap, large). The core problem: under a fixed RAM budget, decide each page's hotness and place it on the right tier so the active working set stays resident in DRAM and cold pages sink to the compressed or Flash tier — surviving memory pressure *without* killing processes.

**What "original" and "evolved" mean here.** The *original* solution is **single-tier DRAM + generic global reclaim**: the classic two-list active/inactive LRU + kswapd scanning, with naive swap (write straight to Flash, or no swap at all) and no real tiering; once pressure rises, the low-memory killer (LMK) terminates background apps outright, turning a "warm" app back into a cold launch. The *evolved* solution is **explicit on-device tiering**: DRAM ↔ compressed RAM (zram/zswap, Android RAM Plus, iOS/macOS memory compressor, Huawei HyperSpace Memory) ↔ Flash/UFS swap, driven by access-aware hot/cold placement — MGLRU multi-generation eviction, hotness-based demotion, predictive prefetch — keeping the working set resident while cold pages sink to the compressed or Flash tier.

**Sources.** 13 primary sources: 6 academic papers (DAC'24, ATC'25, FAST'25/arXiv, MobiCom'26, etc.), 4 kernel/system references (MGLRU kernel doc, Android LMKD, PSI, zram doc), 3 industry references (Apple WKdm memory compression, Samsung RAM Plus, Huawei HyperSpace Memory). Source types span peer-reviewed systems papers, kernel documentation, and vendor engineering material. Three have local copies saved.

## 2. Problem background

**What the system needs to do.** On a 4–16 GB DRAM device, keep dozens of background apps "alive" (avoiding cold launches) while instantly freeing memory when a GB-scale large app (on-device LLM, camera, maps, game) is launched in the foreground. The user-visible bars are hard: switching back to a background app must feel instant, launching a large app must not stutter, and background apps must not be killed out of the blue.

**Why this domain becomes hard.** Terminal RAM is **fixed in capacity** — you can't add DIMMs like a server — yet per-app memory demand grows yearly (a single on-device LLM already needs GBs). Cold launches are very expensive: process creation accounts for **94%** of total cold-launch latency [Ariadne], so the system must keep apps resident in an "alive" state. But the more it keeps, the tighter DRAM gets, and the more often it must reclaim and swap — and Flash is two orders of magnitude slower than DRAM, so naive swap directly wrecks interactive latency. That is why early Android leaned on killing rather than swapping.

**Why the original solution is no longer enough.** Single-tier DRAM + two-list LRU has only two exits under pressure: either fire kswapd / direct reclaim and block the foreground, or have LMK kill background apps. The former is serial and slow on Android; the latter throws "warm" apps back to cold launch. Measurements show **86.6%** of GB-scale cold launches cross the 1-second "usability cliff" [AppFlow]; and once the compressed-RAM tier is missing, the system either wastes DRAM or is forced to write Flash — neither is optimal.

## 3. Specific problems and bottleneck evidence

1. **Two-list LRU is too coarse, mis-killing background apps** — active/inactive has only two buckets and cannot finely separate "just used" from "long idle," so kswapd scans more yet evicts worse. After MGLRU replaced it with multi-generation lists, Google's fleet saw kswapd CPU drop **40%**, low-memory kills drop **85%** (75th percentile), and app launch get **18%** faster (50th percentile) [MGLRU].

2. **Android serial reclaim blocks foreground response** — the original kernel runs page *shrinking* and *writeback* serially, so launching a foreground app stalls behind the reclaim path. After PMR decouples and parallelizes them (PPS + SPW), application response time improves by up to **43.6%** [PMR].

3. **Naive swap: either waste DRAM or hammer Flash** — with no zram, cold anonymous pages squat in DRAM; swapping straight to Flash means slow swap-in (decompression is far faster than reading NAND). zram's very existence is a tier — but a static, hotness-blind zram burns both CPU and memory. Ariadne notes that naive zram "does not differentiate hot from cold data, nor leverage different compression chunk sizes," causing frequent needless compression/decompression [Ariadne].

4. **Compression's CPU/memory cost vs ratio tradeoff** — the more zram swaps in-RAM, the more DRAM it saves, but the more CPU compression/decompression burns; lz4 is fast with a low ratio (~2.6:1), zstd has a higher ratio (~3.4:1) but more CPU [zram]. Apple's WKdm compresses pages to about half (~2:1) at a CPU cost, but "faster than reading and writing to disk" [Apple].

5. **No lead time under pressure, so kills come after the fact** — without predictive prefetch/reclaim, the system waits until pressure hits to reclaim — often too late, triggering LMK. AppFlow's predictive preload + adaptive reclaim + context-aware killer cuts kernel direct reclaims by **67.9%**, LMK events by **33.7%**, and keeps **1.85×** more background apps resident [AppFlow].

### Bottleneck evidence

| Scenario | Metric | Original → Evolved | Source |
|---|---|---|---|
| ChromeOS/Android reclaim (two-list LRU → MGLRU) | kswapd CPU usage | −40% | [MGLRU] |
| ChromeOS (two-list LRU → MGLRU) | low-memory kills (75th pct) | −85% | [MGLRU] |
| Android app launch (two-list LRU → MGLRU) | launch time (50th pct) | −18% (faster) | [MGLRU] |
| Android serial reclaim → PMR parallel reclaim | app response time | up to −43.6% | [PMR] |
| GB-scale cold launch (stock Android) | fraction over 1 s | 86.6% exceed 1s | [AppFlow] |
| Large-app cold launch (original → AppFlow) | launch latency | 2s → 690ms (−66.5%) | [AppFlow] |
| Naive zram → Ariadne hotness-adaptive compression | relaunch latency / compress CPU | latency −50% / CPU −15% | [Ariadne] |
| Competitor phone → Huawei HyperSpace Memory | compression rate / app retention | +69% / +100% (16GB≈20GB feel) | [Huawei] |

## 4. Architecture: original vs evolved

![Tiered memory: DRAM-only vs DRAM↔compressed↔Flash](assets/tiered-memory-management-arch.svg)

*Figure: original vs evolved architecture at a glance (the detailed ASCII version follows below).*

**Original — single-tier DRAM + generic global reclaim**

```
    +------------------+        +------------------+
    | foreground app   |        | background apps  |
    +------------------+        |   (many)         |
           |                    +------------------+
           | alloc / fault              |
           v                            | idle
    +------------------------------------------------+
    |        Linux/Android memory manager             |
    |   (active/inactive two-list LRU + kswapd scan)  |
    +------------------------------------------------+
           |                            |
           | reclaim (scan inactive)     | pressure spikes
           v                            v
    +-----------------+          +------------------+
    | Tier 0: DRAM    |          |  LMK kills proc  |
    | (only resident  | -- naive swap --> Flash/UFS |
    |  tier, whole    |          |  (slow, mostly   |
    |  pages, uncompr)|          |   disabled)      |
    +-----------------+          +------------------+
           |
           +--- assumption: hotness has 2 buckets; pressure = kill = cold launch
                [86.6% of GB-scale cold launches exceed 1s]
```

*Original: all pages reside whole and uncompressed on a single DRAM tier; two-list LRU splits hotness into only two buckets; under pressure the OS either swaps naively to Flash (slow) or LMK kills background apps, throwing "warm" apps back to cold launch.*

**Evolved — explicit DRAM↔compressed RAM↔Flash tiering**

```
    +------------------+        +------------------+
    | foreground app   |        | background apps  |
    +------------------+        |   (many)         |
           |                    +------------------+
           | alloc / fault              | idle
           v                            v
    +------------------------------------------------+
    | * access-aware hot/cold engine                  |
    |   (MGLRU generations + batched PTE accessed-bit)|
    |   * PSI pressure signal drives LMKD (reclaim    |
    |     early, kill less)                           |
    +------------------------------------------------+
           |              |                 |
     * hit(hot)      * demote(warm)     * prefetch(predictive)
           v              v                 ^
    +-----------------+   |                 |
    | Tier 0: DRAM    |   |                 |
    | active working  |   |                 |
    | set resident    |   |                 |
    +-----------------+   |                 |
           | * demote      v                 |
           v        +-------------------------------+
    +----------------| Tier 1: compressed RAM (zram)|
    | * compress on  |  in-RAM ~2:1 cold anon pages |
    |  write         |  * hotness-adaptive chunk    |
    | (lz4/zstd/WKdm)|    size                      |
    +----------------+-------------------------------+
                          | * swap-out(truly cold) ^ * predictive prefetch
                          v                        |
                    +-------------------------------+
                    | Tier 2: Flash/UFS swap         |
                    | largest, slowest;             |
                    | * storage-friendly batched WB  |
                    +-------------------------------+

    [large-app cold launch 2s→690ms; direct reclaims −67.9%; retention 1.85×]
```

*Evolved: a three-tier hierarchy (DRAM → compressed RAM → Flash) driven by MGLRU multi-generation hotness discrimination + PSI/LMKD early reclaim + hotness-adaptive compression + predictive prefetch/batched writeback; the active working set stays resident in DRAM and cold pages sink tier by tier instead of being killed. New/changed elements marked `*`.*

## 5. Why the evolved approach helps, and what it still doesn't solve

### Why it helps

- **Coarse hotness mis-kills apps** — MGLRU replaces two lists with multi-generation lists + batched PTE accessed-bit scanning, giving finer hotness buckets and more accurate eviction; on Google's fleet kswapd CPU fell 40%, low-memory kills fell 85% (75th pct), launch got 18% faster (50th pct) [MGLRU].

- **Serial reclaim blocks foreground** — PMR decouples and parallelizes page shrinking and writeback (PPS) and does storage-friendly writeback via batched unmapping of victim pages (SPW), improving app response by up to 43.6% [PMR]. AppFlow's adaptive reclaimer decouples file-backed vs anonymous reclaim by pressure, contributing 60% of its launch-time reduction alone [AppFlow].

- **Naive swap wastes DRAM or hammers Flash** — the compressed-RAM tier (zram/zswap) holds cold pages in-RAM at ~2:1, and decompression is far faster than reading Flash; Ariadne's hotness-adaptive compression cuts relaunch latency by 50% and compression CPU by 15% [Ariadne], and ElasticZRAM improves response time by up to 24.8% on a Pixel 6 [ElasticZRAM]. Huawei HyperSpace Memory's hardware/software co-design raises compression rate 69% and app retention 100% ("16GB feels like 20GB") [Huawei].

- **No lead time under pressure** — AppFlow exploits file-access predictability for predictive preloading (26.1% contribution) + a context-aware killer (picks victims by net freed memory ΔM, 30% fewer kills), cutting GB-scale large-app cold launch from 2s to 690ms (−66.5%), with 95% of launches landing within 1s [AppFlow].

### What it still doesn't solve

- **Compression eats CPU and competes for the power budget** — zram/zswap converts memory pressure into CPU pressure; sustained compression/decompression conflicts with thermals and battery life on power-constrained devices. Apple's WKdm picking a low ~2:1 ratio for speed is exactly this tradeoff, but mobile SoCs lack public power curves for "how much compression pays off."

- **Flash is still two orders of magnitude slower than DRAM, with finite write endurance** — Tier-2 UFS/eMMC swap-in remains a hard latency floor (decompressing zram is far faster than reading NAND); sustained swapping also consumes Flash's limited P/E cycles, and on-device wear-leveling analysis is rarely published.

- **Predictive prefetch loses accuracy under heavy multitasking** — AppFlow's prediction relies on "each app's file-access pattern is predictable," but under heavy multitasking and bursty load the hit rate drops, and mispredicted prefetch wastes I/O and memory.

- **Each vendor's tiering policy is private and non-portable** — Samsung RAM Plus, Huawei HyperSpace Memory, and Apple's memory compressor each use private implementations and parameters; a threshold tuned on one DRAM/UFS grade is not necessarily optimal on another device.

## 6. Comparison table

| Dimension | Original (single-tier DRAM + generic reclaim) | Evolved (DRAM↔compressed RAM↔Flash tiering) | Improvement (signed) | Source |
|---|---|---|---|---|
| Reclaim hotness discrimination | active/inactive two lists (2 buckets) | MGLRU generations + batched PTE scan | kswapd CPU −40% | [MGLRU] |
| Low-memory kills (ChromeOS, 75th pct) | baseline 100% | MGLRU | −85% | [MGLRU] |
| App launch time (Android, 50th pct) | baseline | MGLRU | −18% (faster) | [MGLRU] |
| Kernel direct-reclaim events (GB-scale launch) | baseline 100% | AppFlow adaptive reclaim | −67.9% | [AppFlow] |
| GB-scale large-app cold-launch latency | 2,000 ms (≈86.6% over 1s) | 690 ms (95% within 1s) | −66.5% | [AppFlow] |
| App response time (serial vs parallel reclaim) | baseline (serial shrink+writeback) | PMR (PPS+SPW parallel) | up to −43.6% | [PMR] |
| Relaunch latency / compression CPU | naive zram baseline | Ariadne hotness-adaptive compression | latency −50% / CPU −15% | [Ariadne] |
| Compressed-RAM tier cost (regression/tradeoff) | no zram: cold pages squat in DRAM | zram: saves DRAM but **burns more CPU/power** | n/a (tradeoff, no public power curve) | [Apple; zram] |
| Compression rate / retention (vendor, on-device) | competitor baseline 100% | Huawei HyperSpace Memory | comp. rate +69% / retention +100% | [Huawei] |

## 7. One-word characterization

**Tiered** — on-device memory management evolves from "single-tier DRAM + kill-on-pressure" into an explicit three-tier hierarchy DRAM → compressed RAM → Flash, driven by access-aware hot/cold placement: MGLRU cuts ChromeOS low-memory kills by **85%**, AppFlow drops GB-scale large-app cold launch from **2s to 690ms**, keeping the active working set resident and sinking cold pages tier by tier instead of killing them.

## 8. Open questions and caveats

- **Compression's power budget is unquantified** — zram/zswap converts memory pressure into sustained CPU cost, but the break-even point between "DRAM saved by compressing" and "power/heat spent compressing" lacks public measurement on battery-powered mobile/vehicle devices.
- **Flash swap's write endurance and wear-leveling** — consumer UFS/eMMC has limited P/E cycles, and sustained swapping accelerates aging; on-device tiering studies generally report latency but not wear.
- **Robustness of predictive scheduling under heavy multitasking** — AppFlow's preload/reclaim depends on predictable access patterns; hit rate and misprediction cost under bursty load need broader validation.
- **Coordination between the hot/cold engine and upstream LLM KV-cache swapping** — on-device LLMs swap their own KV cache (see sibling article) outside the kernel zram/swap path; the two tier independently and unaware of each other, possibly double-swapping or fighting.
- **Cross-vendor / cross-device portability** — RAM Plus, HyperSpace Memory, and the iOS compressor have private parameters; a threshold tuned for one DRAM/UFS grade is not necessarily optimal elsewhere, and there is no unified abstraction.
- **Security and privacy** — anonymous pages swapped to Flash may contain sensitive state; encryption and secure erasure of on-device swap files are rarely addressed publicly.

## 9. References

**Academic papers**

1. **[AppFlow]** X. Li, S. Liu, B. Guo, et al. "AppFlow: Memory Scheduling for Cold Launch of Large Apps on Mobile and Vehicle Systems." arXiv:2603.17259, 2026 (MobiCom '26). URL: https://arxiv.org/abs/2603.17259 ; HTML: https://arxiv.org/html/2603.17259 . Local copy: [sources/appflow-2603.17259.md](sources/appflow-2603.17259.md)
2. **[ElasticZRAM]** W. Li, D. Yu, Y. Song, L. Shi. "ElasticZRAM: Revisiting ZRAM for Swapping on Mobile Devices." 61st ACM/IEEE Design Automation Conference (DAC '24), 2024. DOI: https://dl.acm.org/doi/10.1145/3649329.3655943 . Local copy: [sources/elasticzram-dac24.md](sources/elasticzram-dac24.md)
3. **[PMR]** W. Li, L. P. Chang, Y. Mao, et al. "PMR: Fast Application Response via Parallel Memory Reclaim on Mobile Devices." USENIX ATC 2025. URL: https://www.usenix.org/conference/atc25/presentation/li-wentong
4. **[Ariadne]** Y. Liang, A. Shen, C. J. Xue, et al. "Ariadne: A Hotness-Aware and Size-Adaptive Compressed Swap Technique for Fast Application Relaunch and Reduced CPU Usage on Mobile Devices." arXiv:2502.12826, 2025 (FAST '25). Code: CMU-SAFARI/Ariadne. URL: https://arxiv.org/abs/2502.12826 . Local copy: same as [sources/elasticzram-dac24.md](sources/elasticzram-dac24.md)
5. **[IOSR]** W. Li, L. Shi, et al. "IOSR: Improving I/O Efficiency for Memory Swapping on Mobile Devices Via Scheduling and Reshaping." ACM TECS, 2023. DOI: https://dl.acm.org/doi/10.1145/3607923

**Kernel / system references**

6. **[MGLRU]** Y. Zhao (Google). "Multi-Gen LRU." Linux kernel documentation, merged v6.1 (2022), default-on in Android 14. URL: https://docs.kernel.org/admin-guide/mm/multigen_lru.html ; fleet numbers: https://www.esper.io/blog/android-dessert-bites-22-linux-memory-management-38419756 . Local copy: [sources/mglru-kernel.md](sources/mglru-kernel.md)
7. **[LMKD]** Android Open Source Project. "Low Memory Killer Daemon (lmkd)." URL: https://source.android.com/docs/core/perf/lmkd
8. **[PSI]** J. Weiner. "psi: pressure stall information / monitors." LWN, 2018–2019. URL: https://lwn.net/Articles/783520/
9. **[zram]** "zram: Compressed RAM-based block devices." Linux kernel documentation. URL: https://docs.kernel.org/admin-guide/blockdev/zram.html

**Industry references**

10. **[Apple]** Apple / WKdm. "Compressed Memory in OS X Mavericks (WKdm compressor, ~2:1)." 2013; algorithm: https://github.com/berkus/wkdm . Survey: https://en.wikipedia.org/wiki/Virtual_memory_compression
11. **[Samsung RAM Plus]** Samsung. "RAM Plus (virtual memory extension)." URL: https://www.samsung.com/
12. **[Huawei]** Huawei. "HyperSpace Memory, debuting on the Mate 80 line; compression rate +69% / app retention +100%, '16GB RAM, 20GB experience'." IT Home, 2026. URL: https://www.ithome.com/0/931/807.htm

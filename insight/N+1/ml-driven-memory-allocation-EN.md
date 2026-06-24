# ML-Driven Intelligent Memory Allocation

> This document compares the original heuristic-based memory allocation approach (jemalloc/TCMalloc with fixed size classes, LRU/clock page replacement, static prefetch thresholds) with the evolved ML-augmented approach (learned allocators with lifetime prediction, neural cache replacement, workload-driven adaptive reclaim). It surveys academic (ASPLOS, FAST, USENIX, MICRO) and industry (Google fleet) progress from 2018–2025.

## 1. Scope and method

**Domain definition.** Heap memory allocation, cache/page replacement, and memory prefetching in server and datacenter workloads. The scope covers userspace allocators (malloc/free), OS-level page cache eviction policies, and hardware-level data prefetching — three layers where ML techniques have been applied to replace or augment traditional heuristics.

**What "original" and "evolved" mean here.** The *original* solution is the family of hand-tuned heuristic allocators and policies that dominate production today: jemalloc and TCMalloc with statically configured size classes and thread caches; LRU, CLOCK, and ARC page/cache replacement; stride-based and history-table hardware prefetchers. The *evolved* solution augments or replaces these heuristics with machine learning models — lifetime-prediction neural networks for heap layout, regret-minimization and group-level learning for cache eviction, and LSTM/Transformer-based prefetch prediction — trained on profiling traces and adapted online.

**Sources.** 14 primary sources: 8 academic papers (ASPLOS 2020/2021/2024, FAST 2021/2023, USENIX HotStorage 2018, CACM 2024, arxiv 2025), 3 industry reports (Google TCMalloc fleet characterization, Google TEMERAIRE hugepage allocator), 3 system-level references (jemalloc documentation, TCMalloc design docs, USC Data Science Lab). Source types span peer-reviewed conference papers, journal research highlights, open-source allocator documentation, and production fleet measurements.

## 2. Problem background

**What the system needs to do.** Allocate and reclaim memory objects ranging from 8 bytes to multi-megabyte buffers across hundreds of threads, while minimizing fragmentation, TLB pressure, cache miss rate, and tail latency — at warehouse scale where memory allocation accounts for 1–5% of total fleet CPU cycles [Zhou-ASPLOS24].

**Why this domain becomes hard.** Production workloads exhibit extreme diversity in object sizes (8 B to 100+ MB), lifetimes (microseconds to hours), and allocation rates (up to 5 M allocs/sec per process) [Maas-ASPLOS20]. Fixed size classes waste memory through internal fragmentation (RSS grows 10–40% above working set with glibc malloc). Huge pages (2 MB) reduce TLB misses by up to 53% but create coarse-grained fragmentation when short-lived and long-lived objects share pages [TEMERAIRE].

**Why the original solution is no longer enough.** Heuristic allocators cannot distinguish objects by lifetime — a 64-byte object living 10 ms and one living 10 hours receive identical treatment. LRU replacement is provably suboptimal for workloads mixing recency and frequency patterns. Static prefetch thresholds miss irregular access sequences. At Google's fleet scale, even a 1% improvement in allocator efficiency saves millions of CPU-hours annually [Zhou-ASPLOS24].

## 3. Specific problems and bottleneck evidence

1. **Huge-page fragmentation from lifetime-oblivious placement** — When short-lived and long-lived objects are co-located on the same 2 MB huge page, the page cannot be reclaimed until the last object dies, causing up to 78% internal fragmentation in huge-page-backed heaps [Maas-CACM24].

2. **Fixed size classes waste memory at scale** — TCMalloc's 60–80 static size classes round allocations up, producing internal fragmentation. Across Google's fleet, memory allocation overhead (metadata + fragmentation + cache residency) constitutes a measurable fraction of total RAM, with optimized dynamic sizing yielding 3.4% fleet-wide RAM reduction [Zhou-ASPLOS24].

3. **LRU and ARC fail on mixed access patterns** — Pure LRU is optimal only for stack-distance-monotone workloads. Real workloads interleave recency-dominated and frequency-dominated phases, causing LRU to underperform by 18x+ on small-cache scenarios compared to ML-guided policies [LeCaR].

4. **Static prefetchers miss irregular access patterns** — Stride-based and correlation-table hardware prefetchers achieve high accuracy on regular array traversals but degrade sharply on pointer-chasing, graph, and hash-table workloads. Neural prefetchers (Voyager) improve IPC by 41.6% on irregular programs vs 21.7% for best classical prefetchers [Voyager].

5. **Profiling overhead limits continuous adaptation** — Collecting allocation-site lifetime traces incurs ~14% end-to-end overhead via stack tracing [Maas-ASPLOS20], making continuous online learning expensive; most learned allocators rely on offline-trained models applied to subsequent runs.

### Bottleneck evidence

| Scenario | Metric (Original) | Metric (ML-Augmented) | Delta | Source |
|---|---|---|---|---|
| Huge-page heap fragmentation (Google servers) | Up to 78% internal frag | 78% reduction with lifetime grouping | −78% frag | [Maas-CACM24] |
| Fleet-wide RAM usage (TCMalloc, Google) | Baseline | −3.4% RAM, −1.4% CPU (fleet avg) | Significant at scale | [Zhou-ASPLOS24] |
| Cache hit ratio, small cache / large working set | LRU baseline | LeCaR outperforms ARC by >18× | +18× hit ratio gap | [LeCaR] |
| IPC on irregular programs (SPEC/GAP) | No prefetch baseline | Voyager: +41.6% IPC | +41.6% | [Voyager] |
| ML prefetch inference latency budget | N/A | ≤1 μs for net-positive IPC; >50 μs causes −10% regression | Hard ceiling | [USC-DSLab] |

## 4. Architectures: original vs evolved

**Original — Heuristic-Based Memory Allocation Stack**

```
    +-------------------------------------------------------+
    |                  Application Threads                   |
    +-------------------------------------------------------+
         |  malloc(size)                     | free(ptr)
         v                                  v
    +-------------------------------------------------------+
    |          Userspace Allocator (jemalloc / TCMalloc)     |
    |  +--------------------------------------------------+ |
    |  | Thread Cache: per-thread free lists, fixed size   | |
    |  | classes (60-80 bins, e.g. 8,16,32,...,256K)       | |
    |  +--------------------------------------------------+ |
    |  | Central Cache: shared free lists, lock-protected  | |
    |  +--------------------------------------------------+ |
    |  | Page Heap: spans of contiguous pages              | |
    |  | (no lifetime awareness, FIFO page release)        | |
    |  +--------------------------------------------------+ |
    +-------------------------------------------------------+
         |  mmap / brk                       
         v                                   
    +-------------------------------------------------------+
    |          OS Page Cache & Replacement                   |
    |  Policy: LRU / CLOCK / ARC (fixed heuristic)         |
    |  Huge pages: best-effort, fragmentation-prone         |
    +-------------------------------------------------------+
         |
         v
    +-------------------------------------------------------+
    |          Hardware Prefetcher                           |
    |  Stride detector + history table (static thresholds)  |
    +-------------------------------------------------------+
```

*Original: Three layers of fixed heuristics — size-class binning, LRU-family replacement, stride-based prefetch. No cross-layer feedback, no workload adaptation.*

**Evolved — ML-Augmented Memory Management Stack**

```
    +-------------------------------------------------------+
    |                  Application Threads                   |
    +-------------------------------------------------------+
         |  malloc(size)                     | free(ptr)
         v                                  v
    +-------------------------------------------------------+
    |        * Learned Allocator (LLAMA / evolved TCMalloc)  |
    |  +--------------------------------------------------+ |
    |  | Thread Cache: per-thread free lists               | |
    |  | * Size classes: ML-optimized (profiling-driven)   | |
    |  +--------------------------------------------------+ |
    |  | * Lifetime Predictor (neural net on call stacks)  | |
    |  |   Input: symbolized calling context               | |
    |  |   Output: predicted lifetime class (short/med/    | |
    |  |           long/very-long)                         | |
    |  +--------------------------------------------------+ |
    |  | * Lifetime-Segregated Heap                        | |
    |  |   Short-lived objects -> ephemeral huge pages     | |
    |  |   Long-lived objects  -> persistent huge pages    | |
    |  |   (pages reclaimable when lifetime cohort dies)   | |
    |  +--------------------------------------------------+ |
    +-------------------------------------------------------+
         |  mmap / brk
         v
    +-------------------------------------------------------+
    |        * ML-Guided Page Cache & Replacement            |
    |  * LeCaR / Cacheus / GL-Cache:                        |
    |    online regret minimization over LRU+LFU experts    |
    |  * Group-level learning (GL-Cache):                   |
    |    cluster objects, learn per-group eviction utility   |
    |  * Adapts policy weights per workload phase           |
    +-------------------------------------------------------+
         |
         v
    +-------------------------------------------------------+
    |        * Neural Prefetcher                             |
    |  * Voyager / FarSight: LSTM/Transformer on access     |
    |    sequences, predicting page + offset                |
    |  * Asynchronous inference, lookahead prediction        |
    |  * 15-20x less compute, 110-200x less storage than    |
    |    naive neural approaches                            |
    +-------------------------------------------------------+
         |
         v
    +-------------------------------------------------------+
    |        * Offline Profiling & Training Pipeline         |
    |  Collect allocation traces (stack + lifetime)          |
    |  Train lifetime model; retrain on binary updates       |
    |  Feed learned size classes to allocator config         |
    +-------------------------------------------------------+
```

*Evolved: ML models inserted at each layer — lifetime prediction in the allocator, regret-minimization in cache replacement, neural sequence prediction in prefetching. New/changed elements marked with `*`. Offline profiling pipeline closes the feedback loop.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **Huge-page fragmentation** — LLAMA groups objects by predicted lifetime onto separate huge pages, reducing fragmentation by up to 78% while maintaining huge-page TLB benefits. Short-lived objects are co-located on ephemeral pages that can be reclaimed as a unit [Maas-CACM24].

- **Fixed size-class waste** — Profiling-driven dynamic sizing of allocator caches (thread cache, central cache) based on per-application allocation patterns yields 3.4% fleet-wide RAM savings and up to 6.3% per-application memory reduction at Google scale [Zhou-ASPLOS24].

- **Suboptimal cache replacement** — LeCaR uses online regret minimization to dynamically weight LRU and LFU experts, outperforming ARC by >18x on small-cache scenarios [LeCaR]. GL-Cache advances this with group-level learning, achieving 228x higher throughput than object-level learned caches (LRB) while improving hit ratio by 7% on average [GL-Cache].

- **Irregular prefetching** — Voyager's hierarchical page-offset neural model improves IPC by 41.6% on irregular workloads with 15–20x less compute and 110–200x less storage than prior neural prefetchers [Voyager]. FarSight extends this to far-memory, achieving 3.6x speedup over state-of-the-art by learning semantic access patterns rather than raw addresses [FarSight].

### What it still doesn't solve

- **Training-deployment gap** — Learned allocators train on traces from previous binary versions; code changes may invalidate lifetime distributions. LLAMA addresses this partially through calling-context generalization, but adversarial workload shifts remain unhandled.

- **Inference overhead ceiling** — ML model inference at allocation time must stay below ~1 microsecond per prediction; above ~50 μs, the overhead negates all benefits (−10% IPC regression). This constrains model complexity to shallow networks or lookup tables [USC-DSLab].

- **Profiling cost** — Stack-trace-based lifetime profiling adds ~14% runtime overhead [Maas-ASPLOS20], making continuous online adaptation impractical for latency-sensitive services. Most deployments use offline profiling with periodic retraining.

- **No standard integration path** — Learned allocators exist as research prototypes or Google-internal systems; jemalloc and glibc malloc have no ML integration points. Adoption requires custom allocator builds and profiling infrastructure.

- **Adversarial robustness** — Learned indexes and caches are vulnerable to adversarial access patterns that exploit the model's blind spots, potentially degrading performance below the heuristic baseline [Algorithmic-Attacks].

## 6. Comparison table

| Dimension | Original (Heuristic) | Evolved (ML-Augmented) | Improvement | Source |
|---|---|---|---|---|
| Huge-page internal fragmentation | Up to 78% (lifetime-oblivious) | Near-zero (lifetime-segregated) | −78% fragmentation | [Maas-CACM24] |
| Fleet-wide RAM usage (Google TCMalloc) | Baseline | −3.4% fleet avg, −6.3% peak apps | Millions of GB saved at fleet scale | [Zhou-ASPLOS24] |
| Cache hit ratio (small cache, mixed workload) | LRU/ARC baseline | LeCaR: >18× over ARC; GL-Cache: +7% avg, +25% P90 over LRB | Consistent gains across workload types | [LeCaR] [GL-Cache] |
| Cache replacement throughput | LRB: 1× (object-level ML) | GL-Cache: 228× throughput | Orders-of-magnitude speedup | [GL-Cache] |
| IPC on irregular prefetch workloads | No prefetcher: 1× | Voyager: +41.6% IPC | +41.6% | [Voyager] |
| Far-memory prefetch performance | FastSwap: 1× | FarSight: up to 3.6× speedup | +3.6× | [FarSight] |
| Neural prefetcher resource cost | Prior neural: 1× compute, 1× storage | Voyager: 1/15–1/20 compute, 1/110–1/200 storage | 15–200× cheaper | [Voyager] |
| Allocation-time inference budget | N/A (no model) | ≤1 μs net-positive; >50 μs net-negative | Hard latency ceiling | [USC-DSLab] |

## 7. One-word characterization

**Predictive** — Memory management shifts from reactive heuristics (respond to past behavior with fixed rules) to predictive intelligence (forecast object lifetimes, access patterns, and workload phases with learned models), reducing fragmentation by up to 78% and improving cache hit ratios by 7–25% while maintaining sub-microsecond allocation latency.

## 8. Open questions and caveats

- **Online learning at allocation speed** — Can we train or fine-tune lifetime models incrementally at allocation time without exceeding the ~1 μs inference budget, eliminating the offline profiling step?
- **Cross-binary generalization** — LLAMA generalizes across binary versions via calling-context embeddings, but how robust is this to large refactors, language migrations (C++ to Rust), or JIT-compiled workloads?
- **Composability of learned layers** — When ML models operate simultaneously at allocator, cache replacement, and prefetch layers, do they compose well or interfere? No published work studies the full-stack interaction.
- **Fairness in multi-tenant environments** — Learned allocators trained on dominant workloads may systematically disadvantage minority tenants sharing the same fleet. Fairness-aware memory allocation is unexplored.
- **Standardization and portability** — No open-source allocator (jemalloc, mimalloc, glibc) ships ML integration hooks. Adoption requires Google-scale infrastructure for profiling, training, and deployment.
- **Security implications** — Adversarial workloads can craft allocation patterns that exploit learned policies, potentially causing worse-than-heuristic fragmentation or cache thrashing. Robustness guarantees are an open problem.

## 9. References

1. **LLAMA / Maas-ASPLOS20** — Maas M, Andersen DG, Isard M, Javanmard MM, McKinley KS, Raffel C. "Learning-based Memory Allocation for C++ Server Workloads." ASPLOS 2020. URL: https://dl.acm.org/doi/10.1145/3373376.3378525
2. **Maas-CACM24** — Maas M, Andersen DG, Isard M, Javanmard MM, McKinley KS, Raffel C. "Combining Machine Learning and Lifetime-Based Resource Management for Memory Allocation and Beyond." Communications of the ACM, Research Highlight, April 2024. URL: https://dl.acm.org/doi/10.1145/3611018
3. **Zhou-ASPLOS24** — Zhou Z, Gogte V, Vaish N, Kennelly C, Xia P, Kanev S, Moseley T, Delimitrou C, Ranganathan P. "Characterizing a Memory Allocator at Warehouse Scale." ASPLOS 2024. URL: https://dl.acm.org/doi/10.1145/3620666.3651350
4. **TEMERAIRE** — Hunter A, Kennelly C, Richardson P, Riddoch DJ, Aamodt T. "Beyond malloc efficiency to fleet efficiency: a hugepage-aware memory allocator." OSDI 2021. URL: https://www.usenix.org/system/files/osdi21-hunter.pdf
5. **LeCaR** — Vietri G, Rodriguez LV, Martinez WA, Lyons S, Liu J, Rangaswami R, Zhao M, Narasimhan G. "Driving Cache Replacement with ML-based LeCaR." USENIX HotStorage 2018. URL: https://www.usenix.org/conference/hotstorage18/presentation/vietri
6. **Cacheus** — Rodriguez LV, Yusuf F, Lyons S, Liu J, Rangaswami R, Zhao M, Narasimhan G. "Learning Cache Replacement with CACHEUS." USENIX FAST 2021. URL: https://www.usenix.org/conference/fast21/presentation/rodriguez
7. **GL-Cache** — Yang J, Mcallister S, Rashmi KV. "GL-Cache: Group-level Learning for Efficient and High-Performance Caching." USENIX FAST 2023. URL: https://www.usenix.org/conference/fast23/presentation/yang-juncheng
8. **Voyager** — Shakerinava M, Mudigere D, Maas M, Jouppi NP, Laudon J. "A Hierarchical Neural Model of Data Prefetching." ASPLOS 2021. URL: https://dl.acm.org/doi/10.1145/3445814.3446752
9. **FarSight** — WukLab/UCSD, 2025. "Learning Semantics, Not Addresses: Runtime Neural Prefetching for Far Memory." arxiv 2506.00384. URL: https://arxiv.org/abs/2506.00384
10. **USC-DSLab** — USC Data Science Lab. "ML-driven Memory Prefetcher." URL: https://sites.usc.edu/dslab/projects/ml-driven-memory-prefetcher/
11. **TCMalloc Design** — Google. "TCMalloc: Thread-Caching Malloc." URL: https://google.github.io/tcmalloc/design.html
12. **jemalloc** — Evans J. "jemalloc memory allocator." URL: https://jemalloc.net/
13. **Algorithmic-Attacks** — Kornaropoulos E et al. "Algorithmic Complexity Attacks on Dynamic Learned Indexes." arxiv 2403.12433, 2024. URL: https://arxiv.org/abs/2403.12433
14. **AppFlow** — Authors, 2026. "AppFlow: Memory Scheduling for Cold Launch of Large Apps on Mobile and Vehicle Systems." arxiv 2603.17259. URL: https://arxiv.org/abs/2603.17259

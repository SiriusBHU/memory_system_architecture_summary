# Tiered Memory Management and Page Placement Optimization

> This document compares the original static-hardware-latency-based page placement approach with the evolved runtime-latency-aware dynamic page placement approach for tiered memory systems. It surveys academic (SOSP, ASPLOS, OSDI, MICRO) and kernel-community progress from 2022–2025, with emphasis on CXL-enabled heterogeneous memory.

## 1. Scope and method

**Domain definition.** OS-level memory management for systems with multiple memory tiers of different latency and bandwidth characteristics — specifically DDR DRAM (local, fast) and CXL-attached DRAM (remote, higher latency, larger capacity). The core problem is deciding which pages reside on which tier to maximize application throughput under real workload conditions.

**What "original" and "evolved" mean here.** The *original* solution is static hardware-latency-based page placement: the OS packs the hottest (most-accessed) pages into the tier with the lowest hardware-specified latency (local DDR DRAM), using fixed hotness thresholds and NUMA-balancing-derived promotion/demotion. The *evolved* solution is runtime-latency-aware dynamic page placement: the OS monitors actual per-tier access latency (including queuing delay, contention, and memory-level parallelism effects), dynamically redistributes pages to balance loaded latencies across tiers, and adapts thresholds to workload phase changes.

**Sources.** 14 primary sources: 8 academic papers (SOSP 2024, ASPLOS 2023/2025, OSDI 2025, MICRO 2024, HotOS 2025), 3 Linux kernel references (MGLRU documentation, LWN tiering summit reports, TPP patch series), 2 industry references (Intel CXL tiering white paper, Samsung CXL prototype characterization), 1 arXiv preprint on parameter tuning. Source types span peer-reviewed systems papers, kernel documentation, and vendor engineering reports.

## 2. Problem background

**What the system needs to do.** Manage page placement across 2–3 memory tiers in servers and workstations where local DDR DRAM (80–100 ns unloaded) coexists with CXL-attached DRAM (170–250 ns unloaded, 2–8× larger capacity). The goal is to keep application-visible memory access latency low while utilizing the full aggregate capacity.

**Why this domain becomes hard.** CXL memory introduces a new tier between DRAM and storage: byte-addressable like DRAM but with 2–3× higher base latency and a separate memory controller behind a PCIe/CXL link. Under load, queuing at memory controllers, interconnect contention, and interference from co-running workloads cause the *runtime* access latency of each tier to diverge from its *hardware-specified* latency. The default (local DDR) tier can become the bottleneck when its controller is overloaded, while the CXL tier sits under-utilized.

**Why the original solution is no longer enough.** Static placement assumes hardware-specified latency ordering is invariant: local DDR is always faster than CXL. Colloid [SOSP 2024] showed that under moderate memory interconnect contention, the default tier's actual access latency inflates to 2.5× that of CXL tiers. State-of-the-art tiering systems operating under this assumption perform up to 2.3× worse than optimal [Colloid].

## 3. Specific problems and bottleneck evidence

1. **Static latency ordering breaks under contention** — All prior tiering systems (HeMem, TPP, MEMTIS) use the same page placement algorithm: pack the hottest pages into the tier with the lowest hardware-specified latency. This ignores that runtime latency depends on queue occupancy and request rate, not just hardware propagation delay [Colloid/SOSP 2024].

2. **Default tier becomes the bottleneck under load** — When memory interconnect contention rises from 1× to 2×, the default (DDR) tier's access latency increases by 2.5×, while CXL tier latency remains relatively stable. The optimal page distribution shifts from "all-hot-in-DDR" to a balanced split, but static policies cannot detect or react to this [Colloid/SOSP 2024].

3. **Hotness alone is an incomplete performance proxy** — Access frequency ("hotness") does not capture memory-level parallelism (MLP). A page with high access count but fully overlapped loads has low performance impact, while a page with fewer but serialized accesses is critical. Hotness-based policies misrank pages, causing up to 12.4× performance loss vs. MLP-aware placement [SoarAlto/OSDI 2025].

4. **Promotion/demotion thresholds are workload-sensitive** — Default threshold parameters in Linux tiering (TPP, HMSDK) are tuned for one workload class. Bayesian optimization of the same systems' parameters yields 2× performance improvement over defaults and 1.56× over state-of-the-art, showing that fixed thresholds leave significant performance on the table [Karimzadeh et al., arXiv 2025].

5. **Migration thrashing wastes bandwidth** — Aggressive promotion of transiently hot pages followed by immediate demotion creates a migration storm that consumes memory bandwidth without net performance gain. Jenga [arXiv 2025] and ARMS [arXiv 2025] specifically target thrashing elimination as a first-class design goal.

### Bottleneck evidence

| Scenario | Metric | Value | Source |
|---|---|---|---|
| DDR tier under 2× interconnect contention | Runtime access latency vs. unloaded | 2.5× inflation | [Colloid/SOSP 2024] |
| TPP, HeMem, MEMTIS under contention | Throughput vs. optimal placement | Up to 2.3× worse | [Colloid/SOSP 2024] |
| Default TPP vs. tuned TPP | Application throughput | 2.3× gap (ARMS: 2.3× improvement over default TPP) | [ARMS, arXiv 2025] |
| Hotness-based vs. MLP-aware placement | Application runtime | Up to 12.4× slower | [SoarAlto/OSDI 2025] |
| Default HeMem/HMSDK params vs. Bayesian-optimized | Throughput | 2× improvement | [Karimzadeh et al., arXiv 2025] |
| NeoMem HW-assisted profiling vs. SW-only | Geomean speedup | 1.32–1.67× | [NeoMem/MICRO 2024] |

## 4. Architectures: original vs evolved

**Original — Static Hardware-Latency-Based Page Placement**

```
    +------------------+          +------------------+
    |  Application     |          |  Application     |
    +------------------+          +------------------+
           |                             |
           | page fault / access         | page fault / access
           v                             v
    +----------------------------------------------+
    |           Linux Memory Manager                |
    |  (NUMA balancing + MGLRU + fixed thresholds)  |
    +----------------------------------------------+
           |                        |
           | promote (hot)          | demote (cold)
           | via NUMA hint fault    | via LRU scan
           v                        v
    +-----------------+      +-----------------+
    | Tier 0: DDR     |      | Tier 1: CXL     |
    | (Local DRAM)    |      | (CXL-attached)  |
    | HW latency:     |      | HW latency:     |
    |  80-100 ns      |      |  170-250 ns     |
    +-----------------+      +-----------------+
           |                        |
           |   hottest pages -----> Tier 0 (always)
           |   cold pages --------> Tier 1 (always)
           |
           +--- assumes: Tier 0 latency < Tier 1 latency (invariant)
```

*Original: Pages ranked by access frequency; hottest pages always placed in lowest-hardware-latency tier. Promotion via NUMA hint faults, demotion via MGLRU/kswapd scan with fixed generation thresholds.*

**Evolved — Runtime-Latency-Aware Dynamic Page Placement**

```
    +------------------+          +------------------+
    |  Application     |          |  Application     |
    +------------------+          +------------------+
           |                             |
           | page fault / access         | page fault / access
           v                             v
    +----------------------------------------------+
    | * Runtime Latency Monitor                     |
    |   (per-tier queue occupancy, Little's Law,    |
    |    PMU counters, * CXL HW profiler)           |
    +----------------------------------------------+
           |
           | * loaded latency per tier
           v
    +----------------------------------------------+
    | * Latency-Balancing Page Placement Engine     |
    |   (* queuing-aware threshold adaptation,      |
    |    * MLP-aware criticality scoring,           |
    |    * anti-thrashing migration budget)          |
    +----------------------------------------------+
           |                        |
           | * migrate (balance     | * migrate (balance
           |   loaded latencies)    |   loaded latencies)
           v                        v
    +-----------------+      +-----------------+
    | Tier 0: DDR     |      | Tier 1: CXL     |
    | (Local DRAM)    |      | (CXL-attached)  |
    | * Runtime lat:  |      | * Runtime lat:  |
    |   varies with   |      |   varies with   |
    |   load          |      |   load          |
    +-----------------+      +-----------------+
           |                        |
           | * hot pages split across tiers to
           |   balance loaded access latencies
           |
           +--- principle: min(max(loaded_lat_tier0, loaded_lat_tier1))
```

*Evolved: Pages placed to balance runtime (loaded) access latencies across tiers. New/changed elements marked with `*`. Runtime monitor feeds queuing-aware latency to the placement engine, which considers MLP, contention, and migration cost.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **Static latency ordering breaks under contention** — Colloid's latency-balancing principle directly addresses the 2.5× DDR latency inflation by redistributing load across tiers. When integrated with HeMem, TPP, and MEMTIS, it achieves 1.2–2.35× throughput improvement and brings all three systems within 3–13% of optimal [Colloid/SOSP 2024].

- **Hotness alone is an incomplete performance proxy** — SoarAlto's amortized offcore latency (AOL) metric captures both access latency and memory-level parallelism, achieving up to 12.4× improvement over hotness-only tiering designs and correctly prioritizing serialized (latency-critical) accesses over parallelizable ones [SoarAlto/OSDI 2025].

- **Promotion/demotion thresholds are workload-sensitive** — Adaptive systems (ARMS, HybridTier) self-tune thresholds based on observed workload behavior, achieving 1.26–2.3× improvement over default-parameter baselines without manual tuning [ARMS, arXiv 2025].

- **Hardware-assisted profiling reduces overhead** — NeoMem offloads access profiling to a CXL-side hardware unit (NeoProf), eliminating the CPU overhead of software-based page table scanning and achieving 1.32–1.67× geomean speedup over software-only tiering [NeoMem/MICRO 2024].

- **MGLRU provides a better reclaim foundation** — Multi-Gen LRU (merged in Linux 6.1) replaces the two-list active/inactive model with 4 generation lists and PTE-accessed-bit scanning, reducing kswapd CPU usage by 40% and low-memory kills by 85% on ChromeOS/Android, providing a more responsive base for tier demotion decisions [Google/MGLRU, kernel 6.1+].

### What it still doesn't solve

- **Multi-tenant fairness** — Runtime-latency-aware placement optimizes aggregate throughput but may starve latency-sensitive tenants when co-located with bandwidth hogs. Equilibria [arXiv 2025] is early work on fair multi-tenant CXL tiering but no production solution exists.

- **Migration cost is non-zero** — Every page migration consumes memory bandwidth and TLB shootdown overhead. Under rapid workload phase changes, the cost of continuous re-balancing can offset the benefit of better placement, especially for write-heavy workloads where dirty-page migration is expensive.

- **CXL latency variability across vendors** — CXL DRAM latency varies significantly across controller implementations (Samsung: ~170 ns, other prototypes: ~250 ns). A placement policy tuned for one CXL device may not transfer to another without re-calibration.

- **No standard kernel interface for CXL tiering** — As of Linux 6.12, tiered memory support relies on patched NUMA balancing and DAMON; there is no unified kernel subsystem for CXL-aware tiering. The memory-tiering working group acknowledged this gap at the 2024 LSFMM summit [LWN].

## 6. Comparison table

| Dimension | Original (Static HW-Latency) | Evolved (Runtime-Latency-Aware) | Delta | Source |
|---|---|---|---|---|
| Page placement criterion | Hardware-specified tier latency (fixed) | Runtime loaded access latency (dynamic) | Qualitative shift from static to dynamic | [Colloid/SOSP 2024] |
| Throughput under 2× contention | Up to 2.3× below optimal | Within 3–13% of optimal | 1.2–2.35× improvement | [Colloid/SOSP 2024] |
| Performance metric for ranking | Access frequency (hotness) | Amortized offcore latency (AOL) incl. MLP | Up to 12.4× improvement | [SoarAlto/OSDI 2025] |
| Threshold adaptation | Fixed, workload-agnostic | Self-tuning or Bayesian-optimized | 1.56–2× improvement over defaults | [ARMS; Karimzadeh et al. 2025] |
| Access profiling overhead | SW page-table scanning (high CPU cost) | HW-assisted CXL-side profiling (NeoProf) | 32–67% geomean speedup | [NeoMem/MICRO 2024] |
| Demotion foundation | Two-list LRU (active/inactive) | MGLRU 4-generation + PTE scan | 40% kswapd CPU reduction | [MGLRU/kernel 6.1] |
| Migration control | No explicit thrashing guard | Budget-limited, anti-thrashing policies | Eliminates migration storms | [Jenga; ARMS 2025] |
| CXL consumer readiness | N/A (server-only) | AMD consumer CXL in 3–5 yr window; Win11 basic enumeration only | Not yet production-ready for desktops | [Tom's Hardware; AMD 2024] |

## 7. One-word characterization

**Contention-aware.**

## 8. Open questions

- **Can latency-balancing and MLP-awareness be unified?** Colloid balances loaded latencies; SoarAlto uses amortized offcore latency considering MLP. No system yet combines both signals — doing so could address both queuing contention and instruction-level parallelism effects in a single placement decision.

- **How should tiering interact with memory compression (zswap/zram)?** Current tiering research assumes uncompressed pages. On memory-constrained systems (workstations, edge), compressed pages in DDR may outperform uncompressed pages in CXL — the latency tradeoff between decompression and CXL access is unexplored.

- **Will CXL 3.0/4.0 fabric-level switching change the tiering model?** CXL 3.0 introduces fabric-attached memory pools shared across hosts. Per-host tiering policies may conflict with fabric-level allocation, requiring coordination between OS and fabric manager.

- **What is the right kernel abstraction for heterogeneous memory tiering?** The 2024 LSFMM summit identified the need to decouple hotness detection from page movement and expose a "hot-memory abstraction" with pluggable detection backends (PTE bits, PMU, CXL hardware counters). No consensus on API design exists.

- **Can learned models replace hand-tuned heuristics for page placement?** Bayesian optimization already shows 2× gains over defaults. Reinforcement-learning-based placement could adapt continuously, but inference latency of the model itself must be sub-microsecond to avoid dominating the placement decision cost.

- **How will tiering perform for emerging workloads (LLM inference, graph analytics)?** LLM KV caches and graph traversals have irregular, phase-dependent access patterns that stress both hotness detection and migration bandwidth. Benchmarking tiering systems under these workloads is an open area.

## 9. References

1. **[Colloid/SOSP 2024]** M. Vuppalapati, R. Agarwal. "Tiered Memory Management: Access Latency is the Key!" *Proc. ACM SIGOPS 30th Symposium on Operating Systems Principles (SOSP '24)*, Nov 2024. DOI: [10.1145/3694715.3695968](https://dl.acm.org/doi/10.1145/3694715.3695968)

2. **[TPP/ASPLOS 2023]** H. Al Maruf et al. "TPP: Transparent Page Placement for CXL-Enabled Tiered-Memory." *Proc. 28th ACM ASPLOS*, 2023. DOI: [10.1145/3582016.3582063](https://dl.acm.org/doi/10.1145/3582016.3582063)

3. **[M5/ASPLOS 2025]** "M5: Mastering Page Migration and Memory Management for CXL-based Tiered Memory Systems." *Proc. 30th ACM ASPLOS*, 2025. DOI: [10.1145/3676641.3711999](https://dl.acm.org/doi/abs/10.1145/3676641.3711999)

4. **[HybridTier/ASPLOS 2025]** K. Song et al. "HybridTier: An Adaptive and Lightweight CXL-Memory Tiering System." *Proc. 30th ACM ASPLOS*, 2025. [PDF](https://www.sihangliu.com/docs/hybridtier_asplos25.pdf)

5. **[SoarAlto/OSDI 2025]** J. Liu, H. Hadian, H. Xu, H. Li. "Tiered Memory Management Beyond Hotness." *Proc. 19th USENIX OSDI*, Jul 2025. [USENIX](https://www.usenix.org/conference/osdi25/presentation/liu)

6. **[NeoMem/MICRO 2024]** Z. Zhou et al. "NeoMem: Hardware/Software Co-Design for CXL-Native Memory Tiering." *Proc. 57th IEEE/ACM MICRO*, 2024. DOI: [10.1109/MICRO61859.2024.00111](https://dl.acm.org/doi/10.1109/MICRO61859.2024.00111)

7. **[Jenga 2025]** R. Kadekodi et al. "Jenga: Responsive Tiered Memory Management without Thrashing." *arXiv:2510.22869*, 2025. [arXiv](https://arxiv.org/abs/2510.22869)

8. **[ARMS 2025]** "ARMS: Adaptive and Robust Memory Tiering System." *arXiv:2508.04417*, 2025. [arXiv](https://arxiv.org/abs/2508.04417)

9. **[Karimzadeh et al. 2025]** "From Good to Great: Improving Memory Tiering Performance Through Parameter Tuning." *arXiv:2504.18714*, Apr 2025. [arXiv](https://arxiv.org/abs/2504.18714)

10. **[MGLRU/kernel 6.1]** Y. Zhao (Google). "Multi-Gen LRU." *Linux kernel documentation*, merged in v6.1, 2022. [kernel.org](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)

11. **[LWN/LSFMM 2024]** J. Corbet. "Better support for locally-attached-memory tiering." *LWN.net*, 2024. [LWN](https://lwn.net/Articles/974126/)

12. **[Intel CXL Tiering]** Intel. "Advantages of Managing the CXL Memory Tier in Hardware." Technical paper, 2024. [PDF](https://cdrdv2-public.intel.com/886601/advantages-managing-cxl-memory-tier-in-hardware-technical-paper.pdf)

13. **[HotOS 2025]** "Tolerate It if You Cannot Reduce It: Handling Latency in Tiered Memory." *Proc. HotOS 2025*. [PDF](https://sigops.org/s/conferences/hotos/2025/papers/hotos25-72.pdf)

14. **[AMD CXL Consumer]** "AMD Working to Bring CXL Memory Tech to Future Consumer CPUs." *Tom's Hardware*, 2024. [Link](https://www.tomshardware.com/news/amd-working-to-bring-cxl-technology-to-consumer-cpus)

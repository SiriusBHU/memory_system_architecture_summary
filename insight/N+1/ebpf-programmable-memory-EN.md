# eBPF-Based Programmable Kernel Memory Policies

> This document compares the original static kernel memory management approach with the evolved eBPF-programmable memory policy approach for Linux systems. It surveys academic (USENIX ATC, ASPLOS, SIGCOMM, LPC) and kernel community (LSFMMBPF, LWN) progress from 2019–2025.

## 1. Scope and method

**Domain definition.** Kernel-space memory management policy customization in Linux — specifically huge page allocation, page cache eviction, prefetching, and page reclamation — on servers and datacenter machines running memory-intensive workloads (databases, analytics engines, hyperscaler services).

**What "original" and "evolved" mean here.** The *original* solution is the static, kernel-compiled memory management policy set: Transparent Huge Pages (THP) with a single system-wide `always`/`madvise`/`never` toggle, fixed LRU-based page cache eviction (later MGLRU), hard-coded readahead prefetching heuristics, and synchronous compaction triggered by allocation failure. The *evolved* solution uses eBPF hook points inserted into the kernel's memory management paths — page fault handling, page cache admission/eviction, prefetching, and reclaim — to delegate policy decisions to user-space-written, per-application eBPF programs that execute in kernel context without kernel module compilation or reboot.

**Sources.** 10 primary sources: 5 academic papers (USENIX ATC 2022/2024/2025, SIGCOMM eBPF Workshop 2024, arxiv 2024–2025), 2 conference presentations (LPC 2024, LSFMMBPF 2025), 3 kernel/community references (LWN mTHP coverage, Linux kernel documentation, HawkEye ASPLOS 2019). Source types span peer-reviewed systems papers, arxiv preprints, conference slide decks, and kernel documentation.

## 2. Problem background

**What the system needs to do.** The Linux kernel's memory manager must decide, on every page fault and every memory pressure event, which page size to allocate (4 KB, 64 KB, 2 MB), which pages to evict from the page cache, when to trigger compaction, and what to prefetch — across hundreds of concurrent processes with vastly different memory access patterns.

**Why this domain becomes hard.** Modern servers have terabyte-scale DRAM and heterogeneous memory tiers (CXL-attached, NUMA, compressed). TLB coverage is architecturally limited (~1500 entries on x86), so huge page decisions directly impact address translation overhead. But huge pages carry costs: 2 MB pages waste memory via internal fragmentation, cause compaction stalls of 10–500 ms during allocation [THP-Stall], and impose uniform policy on applications with divergent needs (databases want huge pages; short-lived microservices do not).

**Why the original solution is no longer enough.** Linux THP is cost-oblivious: it greedily promotes to 2 MB without considering per-application TLB miss rates, resulting in up to 2.5x memory bloat for small-allocation workloads [THP-Bloat]. The system-wide `always`/`madvise` toggle cannot differentiate between a Redis instance (benefits from huge pages: +31% throughput) and a Splunk indexer (harmed: -30% performance) running on the same host [Percona, Splunk-THP]. Kernel modifications to fix this require months-long patch review cycles, making rapid policy iteration impossible.

## 3. Specific problems and bottleneck evidence

1. **THP compaction stalls cause latency spikes** — When the kernel cannot find a contiguous 2 MB region, synchronous compaction blocks the faulting thread for 10–50 ms, with worst-case stalls reaching 500 ms–1 s on fragmented systems. Database OSD threads are particularly affected [THP-Stall].

2. **Cost-oblivious huge page allocation wastes memory** — THP's greedy promotion allocates 2 MB pages even for workloads that access only a small fraction, causing up to 75.6% internal fragmentation and 2.5x memory bloat [THP-Bloat]. CBMM showed that targeted promotion to only TLB-intensive regions can achieve competitive performance with substantially fewer huge pages [CBMM].

3. **One-size-fits-all page cache eviction loses throughput** — The default Linux LRU/MGLRU eviction policy does not account for application-specific access patterns. cachebpf demonstrated that workload-tailored eviction via eBPF achieves up to 70% higher throughput and 58% lower P99 tail latency compared to the kernel default [cachebpf].

4. **Static prefetching heuristics mispredict for diverse I/O** — Linux's built-in readahead assumes sequential access patterns. For random or strided workloads (key-value stores, graph traversals), this wastes I/O bandwidth and pollutes the page cache. FetchBPF showed that customizable eBPF-based prefetching matches in-kernel policy performance with zero additional overhead while enabling application-specific strategies [FetchBPF].

5. **mTHP lacks per-application granularity** — Multi-size THP (Linux 6.8+) introduces 64 KB intermediate sizes, but control remains system-wide via sysfs. On Android, mTHP allocation success rates drop from 50% to below 10% after two hours of operation due to fragmentation, and "the kernel is not yet at the point where mTHPs can be used automatically" [LWN-mTHP].

### Bottleneck evidence

| Scenario | Metric | Value | Source |
|---|---|---|---|
| THP compaction under fragmentation | Worst-case allocation stall | 500 ms – 1 s | [THP-Stall] |
| THP always-on, small-alloc workload | Internal fragmentation / memory bloat | 75.6% waste, 2.5× bloat | [THP-Bloat] |
| Default LRU vs workload-tailored (YCSB) | Throughput gap | up to 70% lower (default) | [cachebpf] |
| mTHP on Android after 2 h runtime | Allocation success rate | < 10% (down from 50%) | [LWN-mTHP] |
| khugepaged scan overhead (24 h) | Max single-scan latency | 6 ms | [THP-Stall] |

## 4. Architectures: original vs evolved

**Original — Static Kernel Memory Policies**

```
    +-------------------+
    |  Application      |
    |  (no per-app      |
    |   policy input)   |
    +-------------------+
            |
            | page fault
            v
    +-------------------+       +--------------------+
    |  Page Fault       | ----> |  THP Decision      |
    |  Handler          |       |  (system-wide      |
    |  (kernel, fixed)  |       |   always/madvise)  |
    +-------------------+       +--------------------+
            |                           |
            | allocate                  | promote to 2 MB
            v                           v
    +-------------------+       +--------------------+
    |  Buddy Allocator  |       |  khugepaged        |
    |  (4 KB default)   |       |  (background scan, |
    |                   |       |   fixed interval)   |
    +-------------------+       +--------------------+
            |                           |
            v                           v
    +----------------------------------------------+
    |  Page Cache                                  |
    |  LRU/MGLRU eviction (global, fixed policy)   |
    |  Readahead (fixed sequential heuristic)      |
    +----------------------------------------------+
            |
            | memory pressure
            v
    +-------------------+
    |  kswapd/kcompactd |
    |  (fixed triggers) |
    +-------------------+
```

*Original: All policy decisions are compiled into the kernel. THP is system-wide, eviction is global LRU, prefetching is fixed readahead. No per-application customization without kernel patches.*

**Evolved — eBPF-Programmable Memory Policies**

```
    +-------------------+       +------------------------+
    |  Application      |       | * Userspace Policy     |
    |  (profile loaded  |       |   Manager              |
    |   via eBPF)       |       |   (DAMON profiling,    |
    +-------------------+       |    per-app profiles)   |
            |                   +------------------------+
            | page fault                |
            v                           | * load eBPF program
    +-------------------+               v
    | * eBPF-hooked     |       +------------------------+
    |   Page Fault      | <---- | * eBPF Page Size       |
    |   Handler         |       |   Selector             |
    |   (kernel +       |       |   (per-process,        |
    |    BPF dispatch)  |       |    cost-benefit:       |
    +-------------------+       |    4KB/64KB/2MB/32MB)  |
            |                   +------------------------+
            | allocate
            v
    +-------------------+       +------------------------+
    |  Buddy Allocator  |       | * eBPF Compaction      |
    |  (multi-size)     | <---- |   Trigger              |
    |                   |       |   (adaptive threshold) |
    +-------------------+       +------------------------+
            |
            v
    +----------------------------------------------+
    | * Page Cache with eBPF hooks                 |
    |   cachebpf: per-cgroup eviction policy       |
    |   (LFU/MRU/Hyperbolic per-app)              |
    |   FetchBPF: custom prefetch policy           |
    |   (stride/ML-based per-workload)            |
    +----------------------------------------------+
            |
            | memory pressure
            v
    +-------------------+       +------------------------+
    | * Programmable     | <---- | * eBPF Reclaim Policy  |
    |   Reclaim Path    |       |   (PROTECT/EVICT/PASS  |
    |   (kswapd + BPF)  |       |    per-page verdict)   |
    +-------------------+       +------------------------+
```

*Evolved: eBPF hooks at page fault, page cache, and reclaim paths enable per-application policy without kernel recompilation. New/changed elements marked with `*`. Userspace manager loads profiles based on DAMON profiling; eBPF programs execute in-kernel at native speed.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **THP compaction stalls** — eBPF-mm selectively promotes only TLB-intensive regions (identified via DAMON profiling) to 2 MB, using 64 KB or 4 KB elsewhere, avoiding unnecessary compaction while maintaining competitive TLB miss rates. CBMM's cost-benefit model showed that targeted promotion requires substantially fewer huge pages for equivalent performance [CBMM, eBPF-mm].

- **Cost-oblivious huge page allocation** — Per-process eBPF programs compute promotion cost from real-time fragmentation state and compare it against per-region TLB miss benefit, making economically rational decisions rather than greedy ones [eBPF-mm].

- **One-size-fits-all page cache eviction** — cachebpf's five eBPF hooks (init, eviction, admission, access, removal) enable per-cgroup policies: LFU for YCSB (+37% throughput), MRU for file search (2x throughput), with per-application isolation preventing interference. Only 210 lines of core page cache code were modified [cachebpf].

- **Static prefetching heuristics** — FetchBPF allows deploying stride, Leap, or ML-based prefetching policies per-workload without kernel patches, matching in-kernel performance with zero additional overhead [FetchBPF].

- **Deployment velocity** — eBPF programs can be loaded and unloaded at runtime without reboot or kernel module compilation, enabling A/B testing of memory policies in production. PageFlex delegates policy with < 1% application slowdown [PageFlex].

### What it still doesn't solve

- **eBPF verifier constraints limit policy complexity** — The BPF verifier enforces bounded loops and limited stack depth, preventing complex ML inference or deep data structure traversal inside eBPF programs. Policies must remain computationally simple.

- **No upstream eBPF-mm hooks yet** — As of Linux 6.12, page fault eBPF hooks for huge page selection are not yet merged into mainline. eBPF-mm and PageFlex remain research prototypes [eBPF-mm, PageFlex].

- **Per-cgroup isolation overhead** — cachebpf's per-cgroup metadata adds 0.4%–1.2% memory overhead and up to 1.7% CPU overhead, which compounds at scale with hundreds of cgroups [cachebpf].

- **Profiling dependency** — eBPF-mm requires DAMON profiling to identify hot memory regions; profiling itself adds overhead and requires representative workload traces, creating a chicken-and-egg problem for new or bursty workloads.

- **Security surface expansion** — Attaching eBPF programs to page fault and reclaim paths expands the kernel attack surface. A buggy eviction policy can cause data loss; a malicious one can exfiltrate page contents.

## 6. Comparison table

| Dimension | Original (static kernel policies) | Evolved (eBPF-programmable policies) | Improvement | Source |
|---|---|---|---|---|
| Page size selection granularity | System-wide (always/madvise/never) | Per-process, per-memory-region (4 KB/64 KB/2 MB/32 MB) | Region-level vs system-level | [eBPF-mm] |
| Page cache eviction throughput (YCSB) | Baseline (Linux LRU/MGLRU) | +70% throughput, −58% P99 latency | Up to 1.7× throughput | [cachebpf] |
| Policy deployment latency | Kernel patch → review → release (months) | eBPF load at runtime (seconds), no reboot | Months → seconds | [eBPF-mm, PageFlex] |
| Delegation overhead (application slowdown) | 0% (compiled-in) | < 1% (PageFlex measured) | Negligible | [PageFlex] |
| Core kernel code changed (page cache) | N/A (monolithic) | ~210 lines (cachebpf) | Minimal kernel modification | [cachebpf] |
| Per-cgroup policy isolation | Not supported | Per-cgroup eviction, per-workload prefetch | Full isolation | [cachebpf, FetchBPF] |
| Memory overhead for policy metadata | 0% | 0.4%–1.2% per cgroup | Small overhead | [cachebpf] |
| Prefetching customizability | Fixed sequential readahead | Arbitrary (stride, Leap, ML-based) per workload | Workload-specific | [FetchBPF] |

## 7. One-word characterization

**Programmable** (可编程) — Kernel memory management shifts from hard-coded, compile-time policies to runtime-loadable, per-application eBPF programs that execute at native speed inside the kernel, enabling cost-aware huge page selection, workload-tailored eviction, and custom prefetching without kernel modification or reboot.

## 8. Open questions and caveats

- **Upstream adoption timeline unclear** — eBPF-mm page fault hooks, cachebpf eviction hooks, and FetchBPF prefetch hooks are all research prototypes as of mid-2025. None have been merged into mainline Linux. The LSFMMBPF 2025 summit discussed programmable MM but no concrete merge plan was announced [LSFMMBPF-2025].
- **Verifier limitations vs policy expressiveness** — The eBPF verifier's bounded-loop and stack-depth constraints may prevent implementing sophisticated policies (e.g., ML-based page replacement). Workarounds like BPF-to-BPF calls and maps add complexity.
- **Profiling-driven policies require workload stability** — eBPF-mm relies on DAMON to profile hot regions; workloads with phase changes or bursty access patterns may require continuous re-profiling, adding overhead and latency.
- **Interaction between multiple eBPF memory hooks** — When page fault hooks, eviction hooks, and prefetch hooks are all active simultaneously, policy interactions could cause pathological behavior (e.g., prefetching pages that eviction immediately reclaims). No published work addresses coordinated multi-hook policy.
- **Benchmarking representativeness** — eBPF-mm evaluated only astar (SPEC CPU 2006); cachebpf evaluated YCSB and file search. Production workloads with more complex memory patterns (JVM garbage collection, container orchestration) remain untested.
- **CXL and tiered memory** — The LPC 2024 talk explicitly noted that programmable eBPF hooks should extend to page placement for CXL memory tiering [LPC-2024], but no prototype exists for eBPF-driven tier placement.

## 9. References

1. **eBPF-mm** — Mores K., Psomadakis S., Goumas G. (NTUA), 2024. "eBPF-mm: Userspace-guided memory management in Linux with eBPF." arxiv 2409.11220. URL: https://arxiv.org/abs/2409.11220
2. **cachebpf** — Zussman T., Zarkadas I., Carin J., Cheng A., Franke H., Pfefferle J., Cidon A. (Columbia University, IBM), 2025. "Cache is King: Smart Page Eviction with eBPF." arxiv 2502.02750. URL: https://arxiv.org/abs/2502.02750
3. **FetchBPF** — Cao X., Patel S., Lim S.-Y., Han X., Pasquier T., 2024. "FetchBPF: Customizable Prefetching Policies in Linux with eBPF." USENIX ATC 2024, pp. 369–378. URL: https://www.usenix.org/conference/atc24/presentation/cao
4. **PageFlex** — Yelam A., Wu K., Guo Z., Yang S., Shashidhara R., Xu W., Novakovic S., Snoeren A.C., Keeton K. (Google, UC San Diego, UW), 2025. "PageFlex: Flexible and Efficient User-space Delegation of Linux Paging Policies with eBPF." USENIX ATC 2025. URL: https://www.usenix.org/conference/atc25/presentation/yelam
5. **CBMM** — Mansi A. et al., 2022. "CBMM: Financial Advice for Kernel Memory Managers." USENIX ATC 2022. URL: https://www.usenix.org/system/files/atc22-mansi.pdf
6. **HawkEye** — Panwar A., Bansal S., Gopinath K., 2019. "HawkEye: Efficient Fine-grained OS Support for Huge Pages." ASPLOS 2019. URL: https://dl.acm.org/doi/10.1145/3297858.3304064
7. **LPC-2024** — Skarlatos D., Zhao K. (Carnegie Mellon University), 2024. "Towards Programmable Memory Management with eBPF." Linux Plumbers Conference 2024, eBPF Track. URL: https://lpc.events/event/18/contributions/1932/
8. **LWN-mTHP** — Corbet J., 2024. "Two talks on multi-size transparent huge page performance." LWN.net. URL: https://lwn.net/Articles/974826/
9. **LSFMMBPF-2025** — Linux Foundation, 2025. "Linux Storage, Filesystem, MM & BPF Summit 2025." URL: https://events.linuxfoundation.org/archive/2025/lsfmmbpf/
10. **SIGCOMM-eBPF-2024** — Pandit S. et al., 2024. "Custom Page Fault Handling With eBPF." ACM SIGCOMM 2024 Workshop on eBPF and Kernel Extensions. URL: https://dl.acm.org/doi/10.1145/3672197.3673432

---

**Cited inline as:** [THP-Stall] = blog measurements and /proc/vmstat data from production Ceph clusters; [THP-Bloat] = Percona THP analysis; [Percona] = Percona THP Refresher; [Splunk-THP] = Splunk THP advisory. These supplementary references are:

- **[THP-Stall]** — Loke.dev, 2024. "The Compaction Stall: What Nobody Tells You About Linux Transparent Huge Pages." URL: https://loke.dev/blog/linux-thp-compaction-stall-performance
- **[THP-Bloat]** — Percona, 2024. "Transparent Huge Pages Refresher." URL: https://www.percona.com/blog/transparent-huge-pages-refresher/

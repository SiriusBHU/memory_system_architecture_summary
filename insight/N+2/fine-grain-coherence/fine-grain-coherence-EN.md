# Fine-Grain Heterogeneous Coherence Specialization

> **One-word summary:** Specialization

## 1. Scope and Method

This survey examines the evolution from uniform cache coherence protocols (MESI/MOESI applied identically to all IPs) toward per-cacheline coherence specialization in heterogeneous CPU-GPU-accelerator systems. The focus is on the Spandex coherence interface and its Fine-grain Coherence Specialization (FCS) extension, which selects different coherence strategies for individual memory accesses based on observed data-sharing patterns (write-once, migratory, producer-consumer). We also review the underlying DeNovo protocol and contextualize against industry-standard AMBA CHI/ACE and CXL coherence. Sources include the FCS paper (ACM TACO 2022), the original Spandex paper (ISCA 2018), DeNovo protocol research, and the Cohmeleon learning-based orchestration work.

## 2. Problem Background

Modern SoCs integrate CPUs, GPUs, DSPs, and domain-specific accelerators onto a single die or package, all sharing a unified physical address space. Maintaining memory coherence across these fundamentally different compute elements is critical for correctness but increasingly expensive.

Traditional MESI/MOESI protocols, designed for homogeneous CPU multiprocessors, enforce the Single-Writer-Multiple-Reader (SWMR) invariant through writer-initiated invalidations. This works well when all participants have similar cache hierarchies, access granularities, and latency/throughput trade-offs. However, GPUs favor throughput over latency, use massive parallelism, and employ self-invalidating protocols that enforce relaxed consistency models instead of SWMR. Many accelerators lack caches entirely and cannot natively participate in coherence. Forcing all IPs into a single MESI/MOESI protocol creates a lowest-common-denominator design: CPUs pay unnecessary overhead to accommodate GPU access patterns, while GPUs are constrained by CPU-centric invalidation storms. The result is wasted bandwidth, increased latency, and protocol complexity that scales poorly with device diversity.

## 3. Concrete Problems and Evidence

### P1: Uniform protocols misfit heterogeneous access patterns

MESI uses writer-initiated invalidations that generate O(N) coherence messages for every write to shared data. For GPU workloads where thousands of threads write disjoint regions, these invalidations are entirely unnecessary. Evidence: the FCS paper shows that for GPU-dominated benchmarks, up to 99% of network traffic consists of redundant coherence messages under uniform MESI [1].

### P2: Coarse-grained protocol assignment wastes optimization opportunities

Even hybrid approaches like Spandex (pre-FCS) assign a coherence strategy at device granularity -- e.g., all GPU accesses use GPU-coherence, all CPU accesses use MESI. But within a single kernel, different data structures exhibit different sharing patterns: some are written once and read many times, others migrate between producers and consumers. Device-level assignment cannot exploit this diversity. Evidence: Spandex at device granularity achieves 16% execution-time reduction on average; adding per-access FCS gains a further 13% on top of that [1][2].

### P3: Protocol complexity explodes with heterogeneity

Conventional MESI has 4 stable states but dozens of transient states in real implementations. Adding separate GPU coherence, accelerator coherence, and bridge logic for each interconnect type (AMBA CHI, CXL, NVLink) multiplies this complexity. Verification burden grows combinatorially. Evidence: HeteroGen (HPCA 2022) demonstrates that manual design of heterogeneous coherence protocols is error-prone and requires automated synthesis to manage state-space explosion [4].

### P4: Bandwidth waste at the LLC

Under MESI, ownership transfers require sending full cache-line data even when only a few words are dirty. In producer-consumer patterns, the entire line is fetched, partially updated, and forwarded -- wasting LLC bandwidth. Evidence: Spandex's word-granularity ownership avoids full-line transfers, reducing network flit count by up to 5.30x in micro-benchmarks [2].

## 4. Architecture Diagrams

### Original: Uniform MESI/MOESI Coherence

```
 ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
 │  CPU-0   │  │  CPU-1   │  │  GPU CU0 │  │  Accel   │
 │  L1 (M)  │  │  L1 (M)  │  │  L1 (M)  │  │  L1 (M)  │
 └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
      │              │              │              │
      │  ALL use identical MESI     │              │
      │  writer-initiated inval.    │              │
      ▼              ▼              ▼              ▼
 ┌─────────────────────────────────────────────────────┐
 │              Shared L2 / LLC (Directory-MESI)       │
 │  ┌─────────────────────────────────────────────┐    │
 │  │  Per-line state: M | E | S | I              │    │
 │  │  Sharer bitvector per line                  │    │
 │  │  Writer-initiated invalidation on write     │    │
 │  │  Full cache-line granularity transfers      │    │
 │  └─────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────┘
                        │
                        ▼
                   ┌─────────┐
                   │  DRAM   │
                   └─────────┘

 Problem: GPU CUs generate invalidation storms for disjoint
 writes. Accelerators forced into MESI states they don't need.
 One-size-fits-all = worst-case overhead for every device.
```

### Evolved: Spandex + Fine-Grain Coherence Specialization (FCS)

```
 ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
 │  CPU-0   │  │  CPU-1   │  │  GPU CU0 │  │  Accel   │
 │  L1+FCS  │  │  L1+FCS  │  │  L1+FCS  │  │  L1+FCS  │
 │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │
 │ │Req.  │ │  │ │Req.  │ │  │ │Req.  │ │  │ │Req.  │ │
 │ │Select│ │  │ │Select│ │  │ │Select│ │  │ │Select│ │
 │ │Logic │ │  │ │Logic │ │  │ │Logic │ │  │ │Logic │ │
 │ └──┬───┘ │  │ └──┬───┘ │  │ └──┬───┘ │  │ └──┬───┘ │
 └────┼─────┘  └────┼─────┘  └────┼─────┘  └────┼─────┘
      │              │              │              │
      │   Each request independently chooses:     │
      │   • ReqV (read-valid)  = DeNovo-style     │
      │   • ReqO (owned-write) = MESI-style       │
      │   • ReqWT (write-thru) = GPU-style        │
      │   • ReqWB (write-back) = migratory opt.   │
      │   • ReqFwd (forward)   = prod-cons opt.   │
      ▼              ▼              ▼              ▼
 ┌─────────────────────────────────────────────────────┐
 │              Spandex LLC (Unified)                  │
 │  ┌─────────────────────────────────────────────┐    │
 │  │  Per-WORD ownership (not per-line)          │    │
 │  │  Owner ID stored in data line at LLC        │    │
 │  │  No transient states (DeNovo foundation)    │    │
 │  │  Flexible request handling per access       │    │
 │  │  Trace-based auto-specialization engine     │    │
 │  └─────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────┘
                        │
                        ▼
                   ┌─────────┐
                   │  DRAM   │
                   └─────────┘

 Key: each memory access independently selects the optimal
 coherence request type. Write-once data skips ownership;
 migratory data uses ReqWB; producer-consumer uses ReqFwd.
```

## 5. What It Helps / What It Does Not Solve

### Helps

- **Eliminates redundant invalidations.** GPU write-once patterns use write-through requests that bypass ownership entirely, cutting coherence traffic by up to 99%.
- **Reduces execution time for heterogeneous workloads.** Per-access specialization delivers up to 61% execution-time reduction beyond what device-level Spandex already provides.
- **Simplifies protocol complexity.** Spandex has 3 stable states (from DeNovo) with no transient states, compared to dozens of transient states in production MESI. FCS adds request selection logic without adding new protocol states.
- **Enables automatic optimization.** The trace-based specialization engine can determine optimal request types without programmer annotation, making adoption practical.
- **Supports diverse device types.** CPUs, GPUs, and accelerators can each emit the request types best suited to their current access, without static device-type binding.

### Does not solve

- **Software data-race-freedom requirement.** The DeNovo/Spandex foundation requires data-race-free programs. Racy code will produce incorrect results. This places a burden on the programmer or language runtime.
- **Non-coherent accelerators.** Devices that communicate only through uncached MMIO or DMA bypass Spandex entirely; the protocol does not magically make non-coherent IPs coherent.
- **Cross-chip coherence.** FCS targets single-die or single-package coherence domains. Multi-socket or chiplet-to-chiplet coherence (CXL.cache, NVLink-C2C) requires additional bridging protocols.
- **Legacy software compatibility.** Existing binaries compiled for MESI-based systems cannot exploit FCS without recompilation or binary translation to emit specialized request types.
- **Dynamic pattern changes.** The trace-based specialization is profiled offline. Workloads with phase-changing access patterns may not be optimally served by a single static specialization decision per access site.

## 6. Quantitative Comparison

| Dimension | Uniform MESI/MOESI | Spandex (Device-Level) | Spandex + FCS |
|---|---|---|---|
| Coherence granularity | Per-device, one protocol for all | Per-device type (CPU=MESI, GPU=GPU-coh) | Per individual memory access |
| Stable protocol states | 4 (MESI) or 5 (MOESI) + dozens transient | 3 (from DeNovo), no transient states | 3 (unchanged from Spandex) |
| Ownership tracking | Per cache-line | Per word | Per word |
| Exec. time reduction (avg) | Baseline (0%) | ~16% avg, up to 29% | Up to 61% (further 13% beyond Spandex) |
| Network traffic reduction | Baseline (0%) | ~27% avg, up to 58% | Up to 99% |
| Network flit reduction (micro) | Baseline | Up to 3.55x | Up to 5.30x (flit-hop count) |
| Write pattern optimization | None -- all writes use GetM | Device-default only | Write-once: ReqWT; migratory: ReqWB; prod-cons: ReqFwd |
| Auto-specialization | N/A | N/A | Trace-based engine selects optimal request type per access |
| DRF requirement | No | Yes (DeNovo foundation) | Yes (inherited) |
| Hardware area overhead | Baseline | Small (simplified states) | Minimal (request select logic + trace tables) |

## 7. One-Word Summary

**Specialization** -- the core insight is that different data accesses within the same application deserve different coherence treatments, and the granularity of that specialization should be the individual memory request, not the device or the protocol.

## 8. Open Questions

1. **Runtime adaptive specialization.** The current trace-based approach determines request types offline. Can hardware learning (e.g., Cohmeleon-style ML predictors) adapt specialization decisions at runtime for phase-changing workloads without prohibitive overhead?

2. **CXL.cache integration.** As CXL 3.0 brings back-invalidate snooping for Type-2 devices, how would Spandex/FCS map onto CXL's three sub-protocols (CXL.io, CXL.cache, CXL.mem)? Could FCS reduce CXL.cache snoop traffic?

3. **Relaxing the DRF requirement.** DeNovo and Spandex fundamentally require data-race-freedom. Can the FCS approach be adapted for TSO or other stronger memory models without losing protocol simplicity?

4. **Chiplet-scale coherence.** With UCIe and CXL enabling multi-die integration, can FCS-style per-request specialization work across inter-die links where latency asymmetry is significant?

5. **Verification at scale.** Although FCS adds minimal protocol complexity, the combinatorial space of possible per-access specialization choices is vast. How can formal verification keep pace with the flexibility?

6. **Interaction with processing-in-memory.** PIM/PNM devices that compute inside DRAM do not participate in cache coherence. How should FCS handle coherence for data regions that are intermittently processed by PIM units?

## 9. References

1. Alsop, J., Sinclair, M. D., Adve, S. V. (2022). "A Case for Fine-grain Coherence Specialization in Heterogeneous Systems." *ACM Transactions on Architecture and Code Optimization*, 19(3), Article 39. DOI: [10.1145/3530819](https://dl.acm.org/doi/10.1145/3530819). arXiv: [2104.11678](https://arxiv.org/abs/2104.11678).

2. Alsop, J., Sinclair, M. D., Adve, S. V. (2018). "Spandex: A Flexible Interface for Efficient Heterogeneous Coherence." *Proceedings of the 45th International Symposium on Computer Architecture (ISCA)*. DOI: [10.1109/ISCA.2018.00031](https://dl.acm.org/doi/10.1109/ISCA.2018.00031).

3. Komuravelli, R., Adve, S. V., Sung, H. (2015). "Efficient GPU Synchronization without Scopes: Saying No to Complex Consistency Models." *Proceedings of the 48th International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/2830772.2830821](https://dl.acm.org/doi/10.1145/2830772.2830821).

4. Zhang, N., et al. (2022). "HeteroGen: Automatic Synthesis of Heterogeneous Cache Coherence Protocols." *Proceedings of the 28th IEEE International Symposium on High-Performance Computer Architecture (HPCA)*. Available: [PDF](https://vasigavr1.github.io/files/heterogen-hpca-22.pdf).

5. Daya, B. K., et al. (2022). "Cohmeleon: Learning-Based Orchestration of Accelerator Coherence in Heterogeneous SoCs." arXiv: [2109.06382](https://arxiv.org/abs/2109.06382).

6. Lustig, D., et al. (2019). "A Formal Analysis of the NVIDIA PTX Memory Consistency Model." *Proceedings of the 24th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*. DOI: [10.1145/3297858.3304043](https://dl.acm.org/doi/10.1145/3297858.3304043).

7. Guo, F., et al. (2019). "Mozart: Taming Taxes and Composing Accelerators with Shared-Memory." *Proceedings of the 57th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/3656019.3676896](https://dl.acm.org/doi/10.1145/3656019.3676896).

8. Ausavarungnirun, R., et al. (2025). "Cohet: A CXL-Driven Coherent Heterogeneous Computing Framework." arXiv: [2511.23011](https://arxiv.org/abs/2511.23011).

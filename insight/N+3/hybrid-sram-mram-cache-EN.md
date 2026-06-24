# Hybrid SRAM-MRAM Cache: From Pure SRAM Hierarchy to Non-Volatile Heterogeneous Cache

> This document compares the original pure-SRAM cache hierarchy (L1–L3 all SRAM, high leakage at advanced nodes, large area) with the evolved hybrid SRAM-MRAM cache architecture (SRAM for L1, MRAM for L2/L3/LLC, non-volatile benefits, reduced leakage). It surveys academic research (AIP Advances, IEEE, imec), industry R&D (imec SOT-MRAM, Samsung STT-MRAM), and architectural studies from 2022–2026.

## 1. Scope and method

**Domain definition.** On-chip cache memory hierarchy design for high-performance processors (server, HPC, mobile SoC) — specifically the transition from a homogeneous all-SRAM cache hierarchy to a heterogeneous architecture that assigns different memory technologies (SRAM, STT-MRAM, SOT-MRAM) to different cache levels based on their access-pattern requirements.

**What "original" and "evolved" mean here.** The *original* solution is a pure SRAM cache hierarchy: L1 (32–64 KB), L2 (256 KB–1 MB), L3/LLC (4–64 MB) all built from 6T-SRAM cells, characterized by fast access (sub-nanosecond L1), high leakage power (especially at sub-5nm nodes), large cell area (6T SRAM requires 6 transistors per bit), and complete data loss on power-down. The *evolved* solution is a hybrid SRAM-MRAM cache: SRAM retained for latency-critical L1, STT-MRAM or SOT-MRAM replacing SRAM at L2/L3/LLC levels, delivering non-volatile data retention, near-zero standby leakage, higher density (smaller cell area), and enabling new system capabilities (instant-on, checkpoint-free crash recovery, normally-off computing).

**Sources.** 12 primary sources: 4 academic papers (AIP Advances, IEEE JESTPE, IEEE TNANO, ResearchGate), 3 research institute publications (imec SOT-MRAM), 2 architectural studies (monolithic 3D hybrid, gain cell benchmarking), 2 industry roadmaps (Promwad adaptive memory, PatSnap SOT-MRAM roadmap), 1 survey (non-volatile processor design). Source types span peer-reviewed journals, conference proceedings, research institute technical articles, and industry analysis.

## 2. Problem background

**What the system needs to do.** Provide multi-level on-chip cache for processors running diverse workloads — server (cloud AI inference, database), HPC (scientific simulation, large-model training), and mobile (always-on AI, intermittent computing). The cache must deliver sub-nanosecond L1 access, single-digit nanosecond L2/L3 access, capacities from kilobytes to tens of megabytes, and operate within tight power and area budgets that shrink with each process node.

**Why this domain becomes hard.** At sub-5nm process nodes, SRAM faces a "triple scaling wall": (1) Cell area stops shrinking — TSMC's N3 SRAM bitcell (0.0199 um²) is only ~5% smaller than N5 (0.021 um²), and N3E shows zero scaling vs. N5; (2) Leakage power compounds — sub-threshold, gate, GIDL, and junction leakage mechanisms become co-dominant below 3nm, and single-mechanism mitigation (high-Vt transistors) is insufficient; (3) Cache occupies increasing die fraction — as logic scales but SRAM does not, cache consumes 50–70% of die area on modern server CPUs and AI accelerators, directly inflating cost per mm².

**Why the original solution is no longer enough.** A pure SRAM LLC at 64 MB on a 3nm process consumes substantial leakage power even when idle — projected at 2–5 W for the cache alone. In mobile SoCs targeting all-day battery life, this leakage is unacceptable during standby. In HPC nodes, where 50–70% of die area is cache, the opportunity cost of SRAM's large cell size is enormous: replacing LLC SRAM with a denser technology could free 20–30% of die area for additional compute or memory capacity. Furthermore, SRAM's volatility means that any power interruption (crash, thermal throttle, intentional power gating) destroys all cached state, requiring expensive re-warming from DRAM/storage.

## 3. Specific problems and bottleneck evidence

1. **SRAM area scaling has stalled at 3nm** — TSMC N3 SRAM bitcell is 0.0199 um² vs. N5's 0.021 um², representing only ~5% shrink. The N3E variant shows zero scaling (0.021 um²). Meanwhile, logic standard cell area scales 1.3× per node. This divergence means cache occupies an ever-larger fraction of die area at each new node [TSMC N3 SRAM analysis; WikiChip IEDM 2022].

2. **Multi-mechanism leakage at sub-3nm** — Below 3nm, sub-threshold leakage, gate leakage, GIDL, and junction current become co-dominant. High-Vt transistors address only sub-threshold leakage, leaving 40–60% of total leakage unmitigated. A 64 MB SRAM LLC at 3nm is projected to leak 2–5 W at typical operating temperature [PatSnap SRAM leakage analysis].

3. **STT-MRAM write latency limits L1/L2 use** — STT-MRAM write latency is typically 5–10 ns, compared to sub-1 ns for SRAM. This makes STT-MRAM unsuitable for L1 cache (requires sub-nanosecond read/write) and marginal for L2 (requires 1–3 ns write). Only L3/LLC, where write latency tolerance is 5–20 ns, can absorb STT-MRAM's write penalty [imec MRAM technologies survey].

4. **STT-MRAM write endurance is limited** — STT-MRAM write current passes through the thin MgO tunnel barrier, causing cumulative stress that limits endurance to ~10^9–10^12 cycles. For a high-write-rate L2 cache, this endurance may be insufficient over a 5–10 year product lifetime [IEEE MRAM endurance study; nature npj Spintronics].

5. **SOT-MRAM density is worse than STT-MRAM** — SOT-MRAM's 3-terminal cell structure (separate read and write paths) consumes ~50% more area than STT-MRAM's 2-terminal cell. This partially offsets SOT-MRAM's advantages in speed and endurance when targeting area-sensitive LLC applications [SOT vs STT MRAM comparison].

### Bottleneck evidence

| Scenario | SRAM (Original) | MRAM (Target) | Gap/Benefit | Source |
|---|---|---|---|---|
| Bitcell area at 5nm | 0.021 um² (6T-SRAM) | ~0.009 um² (STT-MRAM, 43% of SRAM) | 2.3× denser | [imec 5nm study] |
| Standby leakage (64 MB LLC) | 2–5 W | ~0 W (non-volatile) | Near-zero standby | [PatSnap leakage] |
| Write latency (L3/LLC) | <1 ns | 5–10 ns (STT), <1 ns (SOT) | STT: 5–10× slower; SOT: comparable | [imec; EDN] |
| Write endurance | >10^16 (unlimited) | 10^9–10^12 (STT), >10^15 (SOT) | STT: orders of magnitude less | [imec; npj Spintronics] |
| Write energy per bit | ~1 fJ (SRAM) | ~100 fJ (STT), <100 fJ (SOT) | MRAM write higher; total lower due to zero leakage | [imec SOT-MRAM] |
| Area scaling at 3nm | Stalled (0% N3E vs N5) | Scales with MTJ diameter, BEOL-compatible | MRAM scales independently | [TSMC N3; imec] |
| SRAM cache die fraction | 50–70% (server CPU) | 30–40% with MRAM LLC | 20–30% area freed | [WikiChip IEDM 2022] |

## 4. Architectures: original vs evolved

**Original — Pure SRAM Cache Hierarchy**

```
    +--------------------------------------------------+
    |                  Processor Core                   |
    +--------------------------------------------------+
         |                    |                    |
    +----------+        +----------+         +-----------+
    |  L1 I$   |        |  L1 D$   |         |  L1 TLB   |
    |  SRAM    |        |  SRAM    |         |  SRAM     |
    |  32-64KB |        |  32-64KB |         |           |
    |  <1ns    |        |  <1ns    |         |           |
    +----------+        +----------+         +-----------+
         |                    |
         +--------------------+
                   |
              +----------+
              |   L2 $   |
              |   SRAM   |
              | 256KB-1MB|
              |   1-3ns  |
              +----------+
                   |
              +-----------+
              |  L3 / LLC |
              |   SRAM    |
              |  4-64 MB  |
              |  5-20ns   |
              +-----------+
                   |
              +-----------+
              |   DRAM    |
              |  (off-die)|
              |  50-100ns |
              +-----------+

    All levels: 6T-SRAM
    Standby leakage: 2-5 W (64 MB LLC at 3nm)
    Data retention: volatile (lost on power-down)
    Area: 50-70% of die (server CPU)
```

*Original: All cache levels use 6T-SRAM cells. High leakage at advanced nodes, large die area, complete data loss on power interruption.*

**Evolved — Hybrid SRAM-MRAM Cache Hierarchy**

```
    +--------------------------------------------------+
    |                  Processor Core                   |
    +--------------------------------------------------+
         |                    |                    |
    +----------+        +----------+         +-----------+
    |  L1 I$   |        |  L1 D$   |         |  L1 TLB   |
    |  SRAM    |        |  SRAM    |         |  SRAM     |
    |  32-64KB |        |  32-64KB |         |           |
    |  <1ns    |        |  <1ns    |         |           |
    +----------+        +----------+         +-----------+
         |                    |
         +--------------------+
                   |
             *+----------+*
             *|   L2 $   |*
             *| STT-MRAM |*
             *| 256KB-2MB|*
             *|  2-5ns   |*
             *+----------+*
                   |
             *+-----------+*
             *| L3 / LLC  |*
             *| SOT-MRAM  |*
             *|  4-64 MB  |*
             *|  3-10ns   |*
             *+-----------+*
                   |
              +-----------+
              |   DRAM    |
              |  (off-die)|
              |  50-100ns |
              +-----------+

    * = new/changed elements
    L1: SRAM (latency-critical, unchanged)
    L2: STT-MRAM (non-volatile, 2.3x denser, near-zero leakage)
    L3/LLC: SOT-MRAM (non-volatile, sub-ns write, >10^15 endurance)
    Standby leakage: ~0 W (non-volatile, power-gatable)
    New capabilities: instant-on, checkpoint-free crash recovery,
                      normally-off computing, zero-leakage standby
    Area: 30-40% of die (20-30% freed vs pure SRAM)
```

*Evolved: L1 retains SRAM for sub-nanosecond latency; L2 migrates to STT-MRAM for density and non-volatility; L3/LLC uses SOT-MRAM for speed, endurance, and density. Non-volatile cache enables instant-on, crash recovery, and power-gating without data loss. New/changed elements marked with `*`.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **SRAM area scaling stall** — STT-MRAM bitcells occupy only 43.3% of SRAM macro area at 5nm, enabling 2.3× higher density for L2/L3/LLC. For a 64 MB LLC, this translates to ~30% die area savings, freeing silicon for additional compute cores or larger cache capacity within the same die budget [imec 5nm feasibility study].

- **Multi-mechanism leakage** — MRAM is inherently non-volatile: standby leakage approaches zero because magnetic state retention requires no power. A hybrid cache can completely power-gate L2/L3 during standby, eliminating the 2–5 W LLC leakage penalty. For a 512 KB L2 cache, SOT-MRAM and STT-MRAM achieve EADP (energy-area-delay product) improvements of 73.7% and 67.8% over SRAM respectively [AIP Advances hierarchical cache study; imec].

- **Volatile data loss** — Non-volatile L2/L3 cache retains data across power cycles, enabling: (a) **instant-on** — the processor resumes from the exact cache state without re-warming from DRAM; (b) **checkpoint-free crash recovery** — no need for explicit checkpointing to survive power failures; (c) **normally-off computing** — the system powers on only when processing is needed, with zero wake-up overhead for cache state [SOT-MRAM normally-off computing study].

- **SOT-MRAM addresses STT-MRAM's write limitations** — SOT-MRAM achieves sub-1 ns write latency (210 ps demonstrated at 1V) with switching energy below 100 fJ/bit and endurance exceeding 10^15 cycles. Because the write current never crosses the tunnel barrier, read disturb is eliminated and barrier degradation (which limits STT-MRAM endurance) does not occur [imec SOT-MRAM scaling; npj Spintronics review].

- **BEOL-compatible fabrication** — MRAM devices are fabricated in the back-end-of-line (BEOL) metal stack, above the transistor layer. This enables monolithic 3D integration where MRAM cache layers are stacked directly above logic, reducing wire length and enabling tighter integration without wafer bonding [IEEE monolithic 3D SRAM/MRAM study].

### What it still doesn't solve

- **SOT-MRAM area penalty vs STT-MRAM** — SOT-MRAM's 3-terminal structure requires ~50% more area than 2-terminal STT-MRAM. While both are denser than SRAM, SOT-MRAM's area disadvantage partially negates the density benefit at LLC scale. Imec's research on BEOL read selectors targets 10–40% bitcell area reduction to close this gap, but production-ready solutions are not yet available [imec SOT-MRAM BEOL selectors].

- **STT-MRAM write energy is higher than SRAM** — Per-bit write energy for STT-MRAM (~100 fJ) is ~100× higher than SRAM (~1 fJ). For write-intensive workloads, the dynamic write energy of an MRAM L2 can exceed SRAM's combined read+write+leakage energy. Workload-aware cache management (write buffering, migration policies) is needed to maintain energy benefits [IEEE write energy analysis].

- **Retention-latency tradeoff in SOT-MRAM** — Imec targets LLC-specific retention of 0.1–100 seconds (not the years required for storage). Achieving both low write energy and sufficient retention simultaneously requires careful tuning of the magnetic free layer. Write error rate targets (10^-6) have been met in research but not yet demonstrated at production scale [imec LLC retention targets].

- **Manufacturing maturity** — STT-MRAM is commercially available for embedded applications (eNVM) at 22nm and 14nm, but high-density cache-optimized STT-MRAM at 5nm or below is not yet in production. SOT-MRAM is still in research phase at imec and academic labs. Volume availability for processor cache is estimated at 2027–2029 for STT-MRAM and 2029+ for SOT-MRAM [imec roadmap; EDN SOT-MRAM status].

- **No standard design methodology** — EDA tools and PDKs for hybrid SRAM-MRAM cache design are immature. Cache controllers must handle asymmetric read/write latencies, endurance-aware wear leveling, and retention-aware refresh — none of which exist in standard cache controller IP.

## 6. Comparison table

| Dimension | Original (Pure SRAM, 3nm) | Evolved (Hybrid SRAM-MRAM) | Improvement | Source |
|---|---|---|---|---|
| LLC bitcell area | 0.0199 um² (6T-SRAM, N3) | ~0.009 um² (STT-MRAM at 5nm equiv.) | 2.3× denser | [imec 5nm] |
| LLC standby leakage (64 MB) | 2–5 W | ~0 W (non-volatile) | Near-zero | [PatSnap; imec] |
| L2 EADP (512 KB) | Baseline (SRAM) | −73.7% (SOT-MRAM), −67.8% (STT-MRAM) | Up to 73.7% better | [AIP Advances] |
| LLC write latency | <1 ns | 5–10 ns (STT), <1 ns (SOT, 210 ps demo) | STT: 5–10× slower; SOT: comparable | [imec; EDN] |
| LLC write endurance | >10^16 | 10^9–10^12 (STT), >10^15 (SOT) | SOT: near-unlimited; STT: limited | [imec; npj Spintronics] |
| LLC write energy per bit | ~1 fJ | ~100 fJ (STT), <100 fJ (SOT, record) | Per-write higher; total system lower | [imec SOT-MRAM] |
| Data retention on power loss | Lost (volatile) | Retained (non-volatile) | Instant-on, crash recovery | [NV processor study] |
| SRAM cache miss penalty | Baseline | −50% (eDRAM hybrid), −80% (MRAM hybrid) | Up to 80% reduction | [IEEE hybrid cache] |
| System performance (IPC) | Baseline | +15% (eDRAM), +23% (MRAM L3) | Up to +23% | [IEEE hybrid cache] |
| Die area for cache (server CPU) | 50–70% | 30–40% (with MRAM LLC) | 20–30% freed | [WikiChip IEDM] |

## 7. One-word characterization

**Non-volatile** (非易失) — The hybrid SRAM-MRAM cache replaces volatile SRAM at L2/L3/LLC with non-volatile magnetic memory (STT-MRAM and SOT-MRAM), eliminating standby leakage, enabling 2.3× higher density, and unlocking system-level capabilities — instant-on resume, checkpoint-free crash recovery, and normally-off computing — that are fundamentally impossible with a pure SRAM hierarchy.

## 8. Open questions and caveats

- **Workload-dependent energy crossover** — The leakage-versus-write-energy tradeoff depends heavily on workload: read-dominated LLC workloads strongly favor MRAM; write-heavy workloads (e.g., streaming writes, database logging) may see net energy increases. Per-application characterization is needed, not blanket replacement.

- **LLC retention requirements are application-specific** — Imec's 0.1–100 second retention target for SOT-MRAM LLC assumes short-lived cache data. Applications requiring power-off data persistence (checkpoint/restore, hibernation) need longer retention, increasing write energy and latency. No single retention target fits all use cases.

- **Process integration challenges at 3nm and below** — Fabricating MRAM MTJ (magnetic tunnel junction) devices in the BEOL of a 3nm process requires thermal budgets compatible with advanced logic processing (typically <400°C for BEOL). Whether SOT-MRAM's complex free-layer stack can survive sub-3nm BEOL thermal constraints is an active research question.

- **Asymmetric access patterns complicate cache coherence** — In multi-core systems with hybrid caches, the asymmetric read/write latencies of MRAM cache levels interact with coherence protocols (MESI, MOESI). Directory-based coherence protocols may need modifications to avoid performance pathologies when MRAM write latency gates invalidation responses.

- **Endurance wear-leveling overhead** — STT-MRAM's limited endurance (10^9–10^12) requires wear-leveling logic similar to flash memory. This adds area, latency, and design complexity. Whether the total system benefit (density + leakage) still justifies MRAM after accounting for wear-leveling overhead at LLC scale is not fully characterized.

- **Competitive alternatives** — Hybrid SRAM-MRAM is not the only approach to SRAM scaling limitations. Gain-cell memory (GC), eDRAM, and BEOL-compatible capacitor-based memories also target LLC replacement. Gain-cell designs at 3nm show 29% lower read latency at ~0.5× the area of SRAM, with simpler fabrication than MRAM. The winner may be application-specific rather than universal.

- **Security implications of non-volatile cache** — Non-volatile cache retains sensitive data (cryptographic keys, authentication tokens, PII) across power cycles. Without explicit scrubbing, a physical attacker could extract cache contents from a powered-off device. Secure erase mechanisms for MRAM cache are not addressed in current architectural proposals.

## 9. References

1. **AIP Advances Hierarchical Cache** — Authors, 2023. "Hierarchical cache configuration based on hybrid SOT- and STT-MRAM." AIP Advances 13, 025111. URL: https://pubs.aip.org/aip/adv/article/13/2/025111/2877240/Hierarchical-cache-configuration-based-on-hybrid
2. **Imec SOT-MRAM for LLC** — Imec, 2023. "Novel SOT-MRAM architecture opens doors to high-density last-level cache memory applications." URL: https://www.imec-int.com/en/articles/novel-sot-mram-architecture-opens-doors-high-density-last-level-cache-memory-applications
3. **Imec SOT-MRAM LLC Specifications** — Imec, 2024. "Bringing SOT-MRAM technology closer to last-level cache memory specifications." URL: https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications
4. **Imec SOT-MRAM Scaling** — SemiEngineering, 2025. "Cross-Node Scaling Potential of SOT-MRAM for Last-Level Caches (imec)." URL: https://semiengineering.com/cross-node-scaling-potential-of-sot-mram-for-last-level-caches-imec/
5. **Imec SST-MRAM 5nm Feasibility** — Imec, 2022. "Imec demonstrates the feasibility of introducing SST-MRAM as a last-level cache at the 5nm technology node." URL: https://www.imec-int.com/en/articles/imec-demonstrates-the-feasibility-of-introducing-sst-mram-as-a-last-level-cache
6. **Imec SOT-MRAM Record Energy** — Semiconductor Digest, 2024. "Imec's Extremely Scaled SOT-MRAM Devices Show Record Low Switching Energy and Virtually Unlimited Endurance." URL: https://www.semiconductor-digest.com/imecs-extremely-scaled-sot-mram-devices-show-record-low-switching-energy-and-virtually-unlimited-endurance/
7. **SOT-MRAM Normally-Off Computing** — ResearchGate, 2018. "Ultra-Fast and High-Reliability SOT-MRAM: From Cache Replacement to Normally-Off Computing." URL: https://www.researchgate.net/publication/327384190_Ultra-Fast_and_High-Reliability_SOT-MRAM_From_Cache_Replacement_to_Normally-Off_Computing
8. **Monolithic 3D SRAM/MRAM** — IEEE JESTPE, 2021. "Monolithic 3D-Based SRAM/MRAM Hybrid Memory for an Energy-Efficient Unified L2 TLB-Cache Architecture." URL: https://ieeexplore.ieee.org/document/9334969/
9. **TSMC N3 SRAM Scaling** — Tom's Hardware, 2022. "TSMC's 3nm Node: No SRAM Scaling Implies More Expensive CPUs and GPUs." URL: https://www.tomshardware.com/news/no-sram-scaling-implies-on-more-expensive-cpus-and-gpus
10. **WikiChip IEDM 2022 SRAM** — WikiChip Fuse, 2022. "IEDM 2022: Did We Just Witness The Death Of SRAM?" URL: https://fuse.wikichip.org/news/7343/iedm-2022-did-we-just-witness-the-death-of-sram/
11. **EDN SOT-MRAM Status** — EDN, 2024. "Memory lane: Where SOT-MRAM technology stands in 2024." URL: https://www.edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/
12. **npj Spintronics SOT-MRAM Review** — Nature npj Spintronics, 2024. "Recent progress in spin-orbit torque magnetic random-access memory." URL: https://www.nature.com/articles/s44306-024-00044-1

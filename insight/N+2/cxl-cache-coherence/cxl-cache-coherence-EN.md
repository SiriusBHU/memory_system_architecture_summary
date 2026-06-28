# CXL Cache Coherence Protocol Verification and Optimization: From PCIe DMA to Hardware-Coherent Device Access

> This document surveys the evolution of host-device data sharing from **PCIe DMA-based communication** (CPU-mediated, no hardware coherence, bounce buffers required) to **CXL.cache coherent device access** (hardware cache coherence across the CPU-device boundary, device has peer cache status, formal verification of protocol correctness). The goal is to help system architects and verification engineers understand the coherence gap, the state of formal verification, and the performance implications of the CXL.cache protocol.

## 1. Scope and method

**Domain definition.** This study covers the cache coherence mechanisms for host-device communication in data-center and heterogeneous computing systems. It spans the stack from PCIe DMA data movement, through CXL.cache protocol semantics (H2D/D2H channels, MESI states, snoop types), to formal verification of protocol correctness and simulation-based performance evaluation. The scope includes CXL Type-1 (accelerator with host-managed cache) and Type-2 (accelerator with device-managed memory and host-cacheable region) devices.

**What "original" and "evolved" mean here.** The *original* approach uses PCIe DMA transfers for host-device data sharing. The CPU explicitly manages data movement: the device issues DMA read/write requests, the CPU flushes or invalidates its caches, bounce buffers translate between device-accessible and kernel-virtual address spaces, and no hardware coherence exists between host caches and device-local state. The *evolved* approach uses CXL.cache, a hardware cache coherence protocol running atop the PCIe 5.0+ physical layer. The device participates as a peer in the host's coherence domain: it can cache host memory lines in MESI states, the host snoops the device on conflicts, and data transfers occur at cacheline granularity (64 B) without software intervention. CXL 4.0 (released November 2025) doubles link bandwidth to 128 GT/s over PCIe 7.0.

**Sources.** 12 distinct sources spanning academic papers (7), industry specifications (2), conference proceedings (2), and a literature review (1). At least 5 contain hard performance or verification numbers.

## 2. Problem background

**What the system needs to do.** Enable accelerators (GPUs, SmartNICs, FPGAs, custom ASICs) attached via PCIe to share data with the host CPU at low latency and high bandwidth, while maintaining a consistent view of memory across all agents.

**Why this domain becomes hard.** Three constraints collide: (1) *coherence* — when both the CPU and a device can read and write the same memory region, stale data in either cache causes silent corruption; (2) *granularity* — DMA operates on large buffer regions (typically 4 KB pages), while many accelerator workloads (atomic counters, pointer-chasing, lock acquisition) need cacheline-granularity (64 B) access; (3) *verification* — the CXL.cache protocol specification is written in prose English with hundreds of state transitions, snoop types, and ordering rules, making it susceptible to ambiguity and specification bugs that can cause protocol deadlocks or incoherence.

**Why the original solution is no longer enough.** The proliferation of heterogeneous accelerators — SmartNICs processing network packets, FPGAs running inference pipelines, CXL memory expanders — broke the assumption that bulk DMA transfers are sufficient. Fine-grained data sharing at cacheline granularity, required by remote atomic operations, lock-free data structures, and shared-memory programming models, cannot be efficiently supported by the DMA + bounce-buffer + cache-flush paradigm.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **No hardware coherence across the PCIe boundary** — PCIe devices performing DMA can modify memory without notifying the CPU cache hierarchy, leaving stale data in host caches. Software must explicitly flush or invalidate caches (clflush/clflushopt) before and after every DMA transfer. For data sizes above 2 KB, uncacheable access latency can spike to over 4096 us due to PCIe Maximum Payload Size (MPS) limitations. [ref 7, ref 8]
2. **Bounce buffer overhead** — On systems without IOMMU or with address-space restrictions, DMA transfers require bounce buffers (SWIOTLB): data is first copied from the kernel buffer to a DMA-coherent (uncached) intermediate buffer, then transferred to the device. This double-copy adds latency and consumes memory bandwidth. [ref 8]
3. **Granularity mismatch** — DMA transfers operate at page granularity (4 KB minimum). Accelerator workloads requiring fine-grained synchronization (atomic increments, compare-and-swap on shared counters) must round up to full pages, wasting bandwidth and increasing latency by 14.4x compared to cacheline-granularity coherent access. [ref 2]
4. **Specification ambiguity in CXL.cache** — The CXL.cache specification, written in prose English, contains ambiguities and inaccuracies. Formal modeling by Tan et al. (Imperial College London) using the Isabelle proof assistant identified several issues — some of which could lead to incoherence if left unfixed. Nearly all proposed fixes have been accepted by the CXL Consortium, with one still under discussion. [ref 1]
5. **Verification scalability** — Proving coherence properties (e.g., SWMR — Single Writer, Multiple Readers) for the CXL.cache protocol required tens of thousands of Isabelle lemmas, exposing the difficulty of verifying real-world coherence specifications at scale. [ref 1]

### Bottleneck evidence

**Key numbers:**
- PCIe DMA minimum latency: ~1 us per transfer [ref 7]
- CXL.cache descriptor-read latency reduction vs PCIe: 85% [ref 7]
- CXL.cache completion-signaling latency reduction vs PCIe: 82% [ref 7]
- CXL.cache vs DMA at cacheline granularity: 68% latency reduction, 14.4x bandwidth improvement [ref 2]
- CXL-NIC remote atomic operations vs PCIe-NIC: 5.5x–40.2x speedup (CENTRAL pattern: 40.2x, STRIDE1: 22.4x) [ref 2]
- CXL memory controller additional latency: 100–200 ns (negligible vs end-to-end I/O) [ref 7]
- Cache flush overhead (clflushopt): 2–3 us per 64 B line; clflushopt outperforms clflush by up to 4x above 64 B [ref 7]
- Formal verification: tens of thousands of Isabelle lemmas for SWMR proof of one protocol configuration [ref 1]

## 4. Architectures: original vs evolved

### Original Architecture — PCIe DMA-Based Device Communication

```
Original — PCIe DMA Host-Device Data Sharing

   +-----------------+                    +-----------------+
   |   Host CPU      |                    |  PCIe Device    |
   |  +-----------+  |                    |  (GPU/NIC/FPGA) |
   |  | L1/L2/LLC |  |                    |  +-----------+  |
   |  | Caches    |  |                    |  | Device    |  |
   |  +-----+-----+  |                    |  | Local Mem |  |
   |        |         |                    |  +-----+-----+  |
   |        | clflush |                    |        |         |
   |        v         |                    |        |         |
   |  +-----------+   |                    |  +-----------+  |
   |  | Memory    |   |   PCIe DMA Req    |  | DMA       |  |
   |  | Controller|<--+-----(bulk)--------+--| Engine    |  |
   |  +-----+-----+   |   (4 KB+ pages)   |  +-----------+  |
   |        |          |                    |                 |
   |        v          |                    |                 |
   |  +-----------+    |   Bounce Buffer    |                 |
   |  | DRAM      |    |   (SWIOTLB copy)   |                 |
   |  | (Host)    |    |                    |                 |
   |  +-----------+    |                    |                 |
   +-----------------+                    +-----------------+

   Data flow for device read:
   1. CPU writes data to kernel buffer
   2. CPU flushes cache lines (clflush/clflushopt)
   3. If needed: copy to bounce buffer (DMA-coherent region)
   4. Device DMA engine reads from DRAM (bulk, page-granularity)
   5. Device processes data in local memory

   Weaknesses:
   - No hardware coherence: CPU must manually flush/invalidate caches
   - Bounce buffers add double-copy overhead
   - Page-granularity minimum (4 KB), wasteful for fine-grained access
   - Each DMA transfer costs ~1 us minimum latency
   - No device-side caching of host data
```

### Evolved Architecture — CXL.cache Coherent Device Access

```
Evolved — CXL.cache Hardware-Coherent Host-Device Communication

   +-----------------+                    +-----------------+
   |   Host CPU      |                    | CXL Device      |
   |  +-----------+  |   H2D Snoop       |  (Type-1/2)     |
   |  | L1/L2/LLC |  |   (SnpData,       |  +-----------+  |
   |  | Caches    |  |    SnpInv,        |  | Device    |  |
   |  +-----+-----+  |    SnpCur)        |  | Cache     |  |
   |        |         +----(64 B line)--->|  | (MESI)    |  |
   |        |         |                   |  +-----+-----+  |
   |  +-----------+   |   D2H Request     |        |         |
   |  | Home Agent|   |   (RdCurr,RdOwn, |  +-----------+  |
   |  | (Coherence|<--+---RdShared,      -+--| Device    |  |
   |  |  Tracker) |   |   ItoMWr,DirtyEvict)|  Controller|  |
   |  +-----+-----+   |                   |  +-----------+  |
   |        |          |   D2H Response    |        |         |
   |        |          |   (RspIHitSE,     |        |         |
   |  +-----------+    |    RspIFwdM,      |  +-----------+  |
   |  | Memory    |    |    RspSFwdM)      |  | Device    |  |
   |  | Controller|    |<--(64 B line)-----+--| Local Mem |  |
   |  +-----+-----+    |                   |  +-----------+  |
   |        v           |   GO (MESI state)|                  |
   |  +-----------+     +----(commit)----->|                  |
   |  | DRAM      |     |                  |                  |
   |  | (Host)    |     |                  |                  |
   |  +-----------+     |                  |                  |
   +-----------------+                    +-----------------+

   Protocol channels (3 per direction):
     H2D: Request + Response + Data (host snoops device)
     D2H: Request + Response + Data (device requests host data)

   Data flow for device read (coherent):
   1. Device issues D2H RdShared / RdOwn / RdCurr request
   2. Host Home Agent checks coherence directory
   3. If needed: host snoops other caches (including device peers)
   4. Host sends GO message with MESI state (M/E/S/I)
   5. Device caches line at 64 B granularity — no flush needed

   Strengths:
   - Hardware coherence: no manual cache flush/invalidation
   - 64 B cacheline granularity (vs 4 KB+ DMA pages)
   - Device caches host data in MESI states
   - 68% latency reduction, 14.4x bandwidth vs DMA [ref 2]
   - Formal SWMR proof via Isabelle [ref 1]
```

## 5. What the evolved approach helps with / does not solve

### Helps

- **Eliminates software coherence overhead** — No clflush/clflushopt, no bounce buffers. The host Home Agent and CXL.cache protocol maintain coherence in hardware, reducing per-access latency from microseconds to hundreds of nanoseconds.
- **Enables fine-grained device access** — 64 B cacheline granularity makes remote atomic operations, pointer-chasing, and lock-free data structures practical. CXL-NIC achieves 5.5x–40.2x speedup over PCIe-NIC for remote atomics. [ref 2]
- **Device-side caching reduces repeated access latency** — Devices can cache frequently accessed host memory lines (e.g., the CENTRAL pattern caches hotspot data in the device's HMC, avoiding costly PCIe DMA transfers for subsequent accesses). [ref 2]
- **Formal verification catches specification bugs early** — Isabelle-based proof found ambiguities and inaccuracies in the CXL specification before silicon implementation, preventing potential deadlocks and coherence violations. Nearly all fixes accepted by the CXL Consortium. [ref 1]
- **Composable verification scales to new architectures** — vCXLGen (ASPLOS 2026, Best Paper) automatically synthesizes and verifies CXL bridges for heterogeneous architectures, addressing the interoperability gap across different host coherence protocols and memory consistency models. [ref 6]

### Does not solve

- **Multi-host coherence** — CXL.cache provides coherence between one host and its attached devices. Cross-host coherence (e.g., two servers sharing CXL-attached memory) is not addressed; CXL 3.0 fabric-attached memory provides sharing but without full cross-host cache coherence.
- **Legacy device compatibility** — Existing PCIe devices cannot use CXL.cache without hardware redesign. The protocol requires dedicated CXL-capable controllers on both host and device.
- **Verification completeness** — The Isabelle proof covers SWMR for a specific protocol configuration. Full coverage of all interleavings, multi-device topologies, and error-recovery paths remains an open challenge. The proof required tens of thousands of lemmas for a single configuration. [ref 1]
- **Latency parity with local cache** — CXL memory controllers add 100–200 ns of additional latency. While negligible compared to DMA, this is significant for latency-critical paths compared to local DRAM access (~80 ns).
- **Scalability of directory state** — As the number of CXL devices sharing host memory grows, the host Home Agent's directory tracking overhead increases. CXL 4.0 does not fundamentally change the coherence-directory scalability model.

## 6. Comparison table

| Dimension | PCIe DMA (original) | CXL.cache (evolved) | Delta | Source |
|---|---|---|---|---|
| **Coherence mechanism** | Software (clflush + bounce buffers) | Hardware (MESI, host-managed snoops) | Eliminates SW overhead | [ref 3, 8] |
| **Access granularity** | Page (4 KB minimum) | Cacheline (64 B) | 64x finer | [ref 2, 3] |
| **Latency (cacheline access)** | ~1 us (DMA round-trip) | ~170–300 ns (CXL.cache) | 68% reduction | [ref 2] |
| **Bandwidth (cacheline workload)** | 1x baseline (DMA) | 14.4x (CXL.cache) | 14.4x improvement | [ref 2] |
| **Remote atomic ops (SmartNIC)** | Baseline (PCIe-NIC) | 5.5x–40.2x speedup | Up to 40.2x | [ref 2] |
| **Device-side caching** | None (device cannot cache host data) | MESI states (M/E/S/I) | Enables device cache | [ref 1, 3] |
| **Formal verification** | Not applicable (no protocol to verify) | SWMR proved in Isabelle; spec bugs found and fixed | Raises correctness bar | [ref 1] |
| **Max link bandwidth (CXL 4.0)** | PCIe 5.0: 32 GT/s | CXL 4.0 / PCIe 7.0: 128 GT/s | 4x | [ref 4] |
| **CPU intervention for data transfer** | Required (CPU mediates every DMA) | Not required (hardware coherence) | Frees CPU cycles | [ref 3] |
| **Protocol verification tooling** | N/A | Isabelle proofs + vCXLGen automated synthesis | New discipline | [ref 1, 6] |

## 7. One-word verdict

**Transformative** — CXL.cache converts host-device communication from a software-managed bulk-transfer model into a hardware-coherent, cacheline-granularity protocol with formally verified correctness, enabling an entirely new class of fine-grained heterogeneous computing that PCIe DMA cannot support.

## 8. Open questions

1. **Multi-host coherence** — CXL 3.0/4.0 enables fabric-attached shared memory across hosts, but cache coherence remains host-local. Will future CXL revisions (5.0+) extend hardware coherence across hosts, or will software-managed consistency (e.g., RDMA-style) remain the cross-host model?
2. **Verification completeness** — The Isabelle proof covers SWMR for a bounded configuration. Can compositional verification techniques (as in vCXLGen) scale to full multi-device, multi-host topologies with error-recovery paths?
3. **Performance at scale** — Published CXL.cache benchmarks use simulation (SimCXL, ~3% error vs silicon) or small-scale testbeds. How does coherence overhead scale with dozens of CXL devices sharing a single host's memory, and what are the directory-tracking bottlenecks?
4. **Security implications** — CXL.cache gives devices peer status in the host's coherence domain. What are the attack surfaces (e.g., a compromised SmartNIC poisoning the host cache), and how should coherence-domain isolation be enforced?
5. **Adoption timeline** — CXL 4.0 was released in November 2025, but real silicon supporting CXL.cache (Type-1/Type-2 devices) remains scarce. When will the ecosystem (CPUs, devices, firmware, OS support) reach critical mass for CXL.cache deployment?

## 9. References

| # | Title | Venue / Date | Key data point | URL |
|---|---|---|---|---|
| 1 | Formalising CXL Cache Coherence | ASPLOS 2025 | Isabelle proof of SWMR; specification bugs found and accepted by CXL Consortium | [ACM DL](https://dl.acm.org/doi/10.1145/3676641.3715999) |
| 2 | Cohet: A CXL-Driven Coherent Heterogeneous Computing Framework with Hardware-Calibrated Full-System Simulation | arXiv 2511.23011, 2025 | 68% latency reduction, 14.4x bandwidth vs DMA; 5.5x–40.2x RAO speedup; SimCXL ~3% error | [arXiv](https://arxiv.org/abs/2511.23011) |
| 3 | An Introduction to the Compute Express Link (CXL) Interconnect | ACM Computing Surveys, 2024 | Comprehensive CXL protocol taxonomy (CXL.io, CXL.cache, CXL.mem) | [ACM DL](https://dl.acm.org/doi/full/10.1145/3669900) |
| 4 | CXL 4.0 Specification Release | CXL Consortium, Nov 2025 | 128 GT/s bandwidth, bundled ports, PCIe 7.0, enhanced RAS | [CXL Consortium](https://computeexpresslink.org/wp-content/uploads/2025/11/CXL_4.0-Specification-Release_FINAL_Website-Copy.pdf) |
| 5 | Re-architecting End-host Networking with CXL: Coherence, Memory, and Offloading | UIUC, 2024 | CXL-NIC architecture for coherent SmartNIC access | [PDF](https://saksham.web.illinois.edu/assets/pdf/cxl-nic.pdf) |
| 6 | vCXLGen: Automated Synthesis and Verification of CXL Bridges for Heterogeneous Architectures | ASPLOS 2026 (Best Paper) | Automated CXL bridge synthesis + compositional formal verification | [ACM DL](https://dl.acm.org/doi/10.1145/3779212.3790245) |
| 7 | Dissecting CXL Memory Performance at Scale: Analysis, Modeling, and Optimization | arXiv, 2024 | CXL memory latency characterization; descriptor-read 85% reduction vs PCIe | [arXiv](https://arxiv.org/abs/2409.14317) |
| 8 | DMA, small buffers, and cache incoherence | LWN.net / eInfochips | Bounce buffer overhead; clflush latency scaling | [LWN](https://lwn.net/Articles/2265/) |
| 9 | Rethinking Programmed I/O for Fast Devices, Cheap Cores, and Coherent Interconnects | arXiv, 2024 | DMA overhead analysis; case for coherent I/O | [arXiv](https://arxiv.org/abs/2409.08141) |
| 10 | CXL Cache Mem Protocols (SNIA SDC 2020) | SNIA, 2020 | CXL 1.1 protocol extension details; H2D/D2H channel semantics | [SNIA](https://www.snia.org/sites/default/files/SDC/2020/130-Blankenship-CXL-1.1-Protocol-Extensions.pdf) |
| 11 | Demystifying CXL.cache (Cadence) | Cadence Blog, 2024 | CXL.cache protocol flow walkthrough; snoop message taxonomy | [Cadence](https://www.chipestimate.com/Demystifying-CXLcache/Cadence/blogs/3616) |
| 12 | Towards Composable Proofs of Cache Coherence Protocols | 2026 | Compositional verification methodology for coherence protocols | — |

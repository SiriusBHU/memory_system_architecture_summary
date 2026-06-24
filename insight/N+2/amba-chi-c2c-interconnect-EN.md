# AMBA CHI C2C and On-Chip Interconnect Evolution

> This document compares the original monolithic SoC on-chip coherent interconnect approach with the evolved chiplet-era CHI C2C multi-die coherent interconnect. It surveys Arm architecture specifications (CHI Issue B–G, CHI C2C IHI0098), industry standards (UCIe 2.0), and vendor engineering documentation from 2017–2026.

## 1. Scope and method

**Domain definition.** Coherent on-chip and chip-to-chip interconnect for Arm-based SoCs and multi-die systems. The interconnect fabric carries coherent memory traffic (snoop, request, response, data) between CPU clusters, accelerators, memory controllers, and I/O subsystems, and is the backbone determining system bandwidth, latency, and scalability.

**What "original" and "evolved" mean here.** The *original* solution is monolithic SoC coherent interconnect: all IP blocks reside on a single die connected through a fixed coherent mesh (e.g., CMN-600/700) using AMBA CHI, with the entire coherence domain bounded by one silicon package. The *evolved* solution extends CHI coherence across die boundaries via CHI C2C packetization, uses UCIe as the physical transport layer, introduces NoC S3 as a non-coherent heterogeneous backplane, and adds realm management for cross-die confidential compute — collectively breaking the "one die = one coherence domain" constraint.

**Sources.** 14 primary sources: Arm architecture specifications (CHI IHI0050, CHI C2C IHI0098, NoC S3 product brief), UCIe Consortium specifications (UCIe 1.0/2.0), industry blog posts (Arm Newsroom, Cadence, Synopsys), conference presentations (HPCA 2023 HipChips workshop), and vendor product documentation (CMN S3, Neoverse CSS). Source types span architecture specifications, industry standards, vendor engineering blogs, and EDA verification documentation.

## 2. Problem background

**What the system needs to do.** Deliver coherent, low-latency data movement between heterogeneous compute elements — CPU clusters, GPU/NPU accelerators, memory controllers, and I/O bridges — while scaling to hundreds of billions of transistors for AI, HPC, networking, and mobile workloads.

**Why this domain becomes hard.** Monolithic SoC dies have hit the photolithographic reticle limit (~858 mm2), beyond which a single exposure cannot pattern the die. Manufacturing yield falls exponentially with die area: a 600 mm2 die at a defect density of 0.1/cm2 yields roughly 50%, whereas two 300 mm2 chiplets yield ~70% each. Simultaneously, AI and HPC workloads demand more compute, more memory bandwidth (HBM stacks), and more I/O than any single die can provide. Different IP blocks (CPU in 3 nm, I/O in 5 nm, analog in 12 nm) have divergent optimal process nodes that cannot coexist on a monolithic substrate.

**Why the original solution is no longer enough.** The monolithic coherent mesh (CMN-600: max 64 cores/die; CMN-700: max 256 cores/die) cannot accommodate the transistor budgets, mixed-node economics, or I/O shoreline requirements of next-generation AI accelerator + CPU systems. Splitting an SoC into chiplets requires a protocol that preserves full cache coherence, security realms, and low-latency snoop traffic across die boundaries — capabilities that on-chip CHI alone was never designed to provide.

## 3. Specific problems and bottleneck evidence

1. **Reticle limit caps monolithic die area** — Photolithography imposes a hard ceiling of ~858 mm2 per exposure field. NVIDIA's GB200 and AMD's MI300X already fill the reticle, leaving no room for additional I/O or compute on a single die. Scaling beyond this limit requires multi-die decomposition.

2. **Yield loss scales super-linearly with die area** — At a defect density of 0.1/cm2, a 600 mm2 monolithic die yields ~50%; splitting into two 300 mm2 chiplets raises per-die yield to ~70%, improving effective system yield from 50% to ~49% (2-die) while enabling configurations impossible on a single die [Arteris Chiplet Guide].

3. **Protocol boundary at the die edge destroys coherence** — Pre-CHI-C2C multi-chip systems used protocol bridges (CHI-to-CXL, CHI-to-proprietary), each adding 50–100 ns latency per hop plus requiring complex translation logic. These bridges break the unified snoop domain and cannot propagate Arm's security realm model across dies [HPCA 2023 HipChips].

4. **Mixed-node economics force disaggregation** — A 3 nm compute die costs ~$16,000/wafer while a 5 nm I/O die costs ~$10,000/wafer. Placing analog SerDes, PCIe PHYs, and DDR controllers on an advanced node wastes costly transistor density on circuits that do not benefit from scaling [UCIe Consortium].

5. **Confidential compute cannot span multiple dies without protocol support** — Arm CCA Realm Management Extension (RME) enforces memory access controls per security realm. Without CHI C2C's realm-aware message encoding, accelerator chiplets are treated as non-secure world peripherals and are denied access to realm-protected memory, blocking confidential AI inference on disaggregated hardware [Arm RME-DA / CHI-G].

### Bottleneck evidence

| Constraint | Monolithic Limit | Chiplet Solution | Gap | Source |
|---|---|---|---|---|
| Max die area | 858 mm2 (reticle) | Unlimited (multi-die) | Hard wall | Lithography physics |
| Core count (CMN-600) | 64 cores/die | 256+ cores/system via CMN-700 multi-chip | 4x+ | Arm CMN-700 |
| Cross-die coherence latency | +50–100 ns (bridge) | ~20 ns overhead (CHI C2C) | 2.5–5x better | HPCA 2023 |
| Mixed-node cost penalty | 100% at leading node | 40% I/O die cost reduction | ~$6K/wafer saved | UCIe Consortium |
| Security realm propagation | None (bridge breaks realm) | Full RME-DA/CDA via CHI C2C | Enabled | CHI-G spec |

## 4. Architectures: original vs evolved

**Original — Monolithic SoC with On-Chip CHI Coherence**

```
    +========================================================+
    |                   Single Die (SoC)                      |
    |                                                         |
    |  +-------+  +-------+  +-------+  +-------+            |
    |  | CPU-0 |  | CPU-1 |  | CPU-2 |  | CPU-3 |            |
    |  | (CHI) |  | (CHI) |  | (CHI) |  | (CHI) |            |
    |  +---+---+  +---+---+  +---+---+  +---+---+            |
    |      |          |          |          |                  |
    |  +---+----------+----------+----------+---+             |
    |  |       Coherent Mesh Network (CMN)      |             |
    |  |      (CHI Issue B–E, single domain)    |             |
    |  +---+----------+----------+----------+---+             |
    |      |          |          |          |                  |
    |  +---+---+  +---+---+  +---+---+  +---+---+            |
    |  | SLC   |  | DDR MC |  | GPU   |  |  I/O  |           |
    |  |(cache)|  | (DRAM) |  | (AXI) |  |(PCIe) |           |
    |  +-------+  +-------+  +-------+  +-------+            |
    |                                                         |
    +========================================================+
                         Package
```

*Original: All IPs share one coherent mesh on a single die. GPU and I/O attach via AXI/ACE-Lite bridges — they participate in coherence as I/O-coherent agents but do not hold cachelines. The die boundary is the system boundary.*

**Evolved — Chiplet-Era CHI C2C Multi-Die Coherent Interconnect**

```
    +============================+    +============================+
    |      Compute Chiplet       |    |    Accelerator Chiplet     |
    |       (Die 0, 3 nm)        |    |       (Die 1, 5 nm)        |
    |                            |    |                            |
    |  +------+ +------+        |    |        +------+ +------+   |
    |  |CPU-0 | |CPU-1 |        |    |        | NPU  | | HBM  |   |
    |  |(CHI) | |(CHI) |        |    |        |(CHI) | | Ctrl |   |
    |  +--+---+ +--+---+        |    |        +--+---+ +--+---+   |
    |     |        |             |    |           |        |       |
    |  +--+--------+------+     |    |     +-----+--------+--+   |
    |  | * CMN S3 (coherent|     |    |     |  Local Mesh       |   |
    |  |   mesh, CHI-G)    |     |    |     |  (CHI coherent)   |   |
    |  +--------+----------+     |    |     +--------+----------+   |
    |           |                |    |              |              |
    |  +--------+----------+     |    |     +--------+----------+   |
    |  | * CHI C2C Protocol |     |    |     | * CHI C2C Protocol |   |
    |  |   (packetization,  |     |    |     |   (packetization,  |   |
    |  |    realm mgmt)     |     |    |     |    realm mgmt)     |   |
    |  +--------+----------+     |    |     +--------+----------+   |
    |           |                |    |              |              |
    |  +--------+----------+     |    |     +--------+----------+   |
    |  | * UCIe PHY (D2D)  |     |    |     | * UCIe PHY (D2D)  |   |
    |  +--------+----------+     |    |     +--------+----------+   |
    +===========|================+    +==============|=============+
                |  +-----------+  chiplet link  +-----------+  |
                +--| Substrate |================| Substrate |--+
                   | (Si interposer / organic)  |
                   +----------------------------+
    
    Beneath both dies (non-coherent backplane):
    +-----------------------------------------------------------+
    | * NoC S3 (non-coherent, up to 255 NIs, AXI5/ACE5-Lite)   |
    |   connects: DDR MC, PCIe root, USB, display, sensor hubs  |
    +-----------------------------------------------------------+
```

*Evolved: Compute and accelerator chiplets on separate dies, each with a local coherent mesh, connected via CHI C2C packetization over UCIe PHY. Realm management (RME-DA) propagates security domains across die boundaries. NoC S3 provides the non-coherent backplane for peripheral connectivity. New/changed elements marked with `*`.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **Reticle limit eliminated** — CHI C2C enables system scaling beyond 858 mm2 by distributing coherent compute across multiple dies. Each chiplet can be independently sized for optimal yield and process node.

- **Protocol boundary latency reduced** — CHI C2C packetization avoids the CHI-to-CXL-to-CHI double translation of bridge-based approaches. The protocol layer conversion between on-chip CHI and CHI C2C requires minimal logic, and the container format (Format X for UCIe, Format Y for CXL) is designed to avoid complex packing/unpacking schemes.

- **Security realm preserved across dies** — CHI C2C carries RME-DA and RME-CDA attributes in the message encoding, allowing accelerator chiplets to access realm-protected memory without being relegated to the non-secure world. This enables confidential AI inference on disaggregated hardware where the GPU/NPU lives on a separate die.

- **Mixed-node economics unlocked** — Compute dies on 3 nm, I/O dies on 5–7 nm, and analog dies on 12+ nm can each use their cost-optimal process while maintaining full system coherence through CHI C2C.

- **Heterogeneous non-coherent backplane** — NoC S3 supports up to 255 network interfaces with AXI5/ACE5-Lite, providing a scalable, low-power fabric for the many non-coherent peripherals (display, camera ISP, connectivity, sensors) that do not need snoop traffic.

### What it still doesn't solve

- **UCIe bandwidth < on-chip mesh bandwidth** — UCIe 2.0 delivers up to 32 GT/s per lane; even at maximum lane widths, the aggregate chip-to-chip bandwidth is lower than an on-chip CMN crossbar. Workloads with heavy cross-die snoop traffic (e.g., fine-grained producer-consumer sharing) will see higher latency than monolithic designs.

- **No unified multi-vendor coherence ecosystem** — CHI C2C is an Arm specification; chiplets from vendors using CXL.cache (Intel/AMD ecosystem) or proprietary protocols (NVIDIA NVLink) require protocol bridges. A single system mixing Arm CHI C2C and CXL-coherent chiplets does not yet have a standardized interop layer.

- **Thermal and power delivery for multi-die packages** — CHI C2C addresses the logical protocol but not the physical packaging challenges: heat dissipation across a silicon interposer, power delivery to multiple dies, and thermal coupling between adjacent chiplets remain active engineering problems.

- **Software coherence model complexity** — OS schedulers, NUMA-aware allocators, and runtime libraries must be updated to understand chiplet topology. Cross-die snoop latency creates a new NUMA tier that existing software may not handle optimally.

- **Verification explosion** — Multi-die coherence with realm management creates a combinatorial state space far larger than single-die CHI. EDA vendors (Synopsys, Cadence) have released dedicated CHI C2C VIP, but full-system verification remains an open challenge.

## 6. Comparison table

| Dimension | Original (Monolithic CHI SoC) | Evolved (CHI C2C Multi-Die) | Change | Source |
|---|---|---|---|---|
| Max system area | ~858 mm2 (reticle limit) | Unlimited (multi-die stacking) | Hard wall removed | Lithography physics |
| Coherence domain | Single die, single mesh | Multi-die, unified coherence via CHI C2C | Cross-die coherence enabled | CHI C2C IHI0098 |
| Cross-die protocol overhead | N/A (no die boundary) or +50–100 ns (bridge) | ~20 ns packetization overhead | 2.5–5x latency reduction vs bridge | HPCA 2023 HipChips |
| Security realm propagation | On-die only (RME within mesh) | Cross-die (RME-DA/CDA in CHI C2C messages) | Confidential compute across chiplets | CHI-G / RME-DA spec |
| Non-coherent peripheral fabric | NIC-400/NIC-450 (limited NIs) | NoC S3 (up to 255 NIs, AXI5/ACE5-Lite) | ~5x NI scalability | Arm NoC S3 |
| Process node flexibility | All IPs on one node | Each chiplet on optimal node (3/5/7/12 nm) | 30–40% I/O die cost reduction | UCIe Consortium |
| Physical transport standard | On-chip wires (no standard needed) | UCIe 2.0 (32 GT/s, 2D/2.5D/3D) | Open D2D standard | UCIe 2.0 spec |
| CHI protocol version | CHI Issue B–E (on-chip) | CHI Issue G + C2C extension | Realm mgmt + DataSource + C2C | CHI-G spec |
| Verification complexity | Single-die coherence VIP | Multi-die C2C VIP (Synopsys/Cadence) | Combinatorial state explosion | Synopsys CHI-G VIP |

## 7. One-word characterization

**Packetized** (包化) — The core innovation is packetizing the on-chip CHI coherence protocol into fixed-size containers (Format X / Format Y) suitable for transport over standardized chip-to-chip links, converting what was an intra-die wiring problem into an inter-die packet-switched protocol while preserving full coherence semantics and security realm attributes.

## 8. Open questions and caveats

- **CHI C2C latency at scale** — Published latency overhead numbers come from 2-die configurations. Behavior in 4–8 chiplet topologies with multi-hop CHI C2C routing is not publicly characterized.
- **UCIe 3.0 and beyond** — UCIe 2.0 targets 32 GT/s; future revisions plan 48–64 GT/s. Whether CHI C2C container formats will need revision for higher-bandwidth links is an open specification question.
- **CXL 4.0 convergence** — CXL 4.0 (expected ~2026) may introduce tighter cache coherence across PCIe-attached devices. Whether CHI C2C and CXL.cache converge, coexist, or compete at the protocol level is unclear.
- **Chiplet-to-chiplet security attack surface** — Extending coherence across a physical link exposes new side-channel vectors (timing, electromagnetic) not present in on-die meshes. The CHI C2C specification delegates physical-layer security to UCIe; the adequacy of this layered trust model under adversarial conditions is unproven.
- **Software ecosystem readiness** — Linux kernel NUMA hinting, Android memory management (LMKD, cgroups), and hypervisor memory partitioning do not yet model chiplet-granularity coherence domains. Driver and OS changes are needed but not yet standardized.
- **NoC S3 adoption timeline** — NoC S3 is announced but shipping product data (silicon measurements, power/area) is not yet public. Real-world PPA comparisons against NIC-400/NIC-450 remain unavailable.

## 9. References

1. **AMBA CHI C2C Architecture Specification (IHI0098)** — Arm Ltd., 2024. "AMBA CHI Chip-to-Chip (C2C) Architecture Specification." Document IHI0098A. URL: https://developer.arm.com/documentation/ihi0098/latest/
2. **Arm Newsroom: CHI C2C** — Arm Ltd., 2024. "Ecosystem Collaboration Drives New AMBA Specification for Chiplets." URL: https://newsroom.arm.com/blog/amba-chi-c2c-specification
3. **AMBA CHI Architecture Specification (IHI0050)** — Arm Ltd., 2024. "AMBA 5 CHI Architecture Specification, Issue G." Document IHI0050. URL: https://developer.arm.com/documentation/ihi0050/latest/
4. **CHI Issue G Evolution** — Cadence, 2024. "Evolution of AMBA CHI Protocol: Introducing Issue G Update." URL: https://community.cadence.com/cadence_blogs_8/b/fv/posts/evolution-of-amba-chi-protocol-introducing-issue-g-update
5. **Synopsys CHI-G VIP** — Synopsys, 2024. "Industry's First Verification IP for Arm AMBA CHI-G." URL: https://www.synopsys.com/blogs/chip-design/amba-chi-g-verification-ip.html
6. **Synopsys CHI C2C Verification** — Synopsys, 2024. "AMBA CHI C2C System Verification Solutions." URL: https://www.synopsys.com/blogs/chip-design/amba-chi-c2c-system-verification-solutions.html
7. **Cadence CHI C2C Introduction** — Cadence, 2024. "An Introduction to AMBA CHI Chip-to-Chip (C2C) Protocol." URL: https://www.design-reuse.com/blog/56200-an-introduction-to-amba-chi-chip-to-chip-c2c-protocol/
8. **HPCA 2023 HipChips Workshop** — Defilippi, J. (Arm), 2023. "AMBA for Chiplets." HPCA HipChips Workshop. URL: https://hipchips.github.io/hpca2023/
9. **Arm NoC S3** — Arm Ltd., 2024. "NoC S3: Next Generation Network-on-Chip Interconnect for Armv9-A SoCs." URL: https://www.arm.com/products/silicon-ip-system/interconnect/noc-s3
10. **Arm CMN S3** — Arm Ltd., 2024. "Neoverse CMN S3 Coherent Mesh Network." URL: https://www.arm.com/products/silicon-ip-system/neoverse-interconnect/cmn-s3
11. **UCIe 2.0 Specification** — UCIe Consortium, 2024. "Universal Chiplet Interconnect Express Specification, Revision 2.0." URL: https://www.uciexpress.org/specifications
12. **Arteris Chiplet Guide** — Arteris, 2024. "Chiplets 101: An Arteris Guide to Multi-Die Architecture." URL: https://www.arteris.com/blog/chiplets-101-an-arteris-guide-to-multi-die-architecture/
13. **CHI Specification Evolution** — Cadence / ChipEstimate, 2024. "How AMBA CHI Specification Has Evolved." URL: https://www.chipestimate.com/How-AMBA-CHI-Specification-Has-Evolved/Cadence/blogs/3583
14. **Arm Developer: Multi-Chip CHI C2C** — Arm Developer Blog, 2024. "Moving AMBA Forward with Multi-Chip and CHI C2C." URL: https://developer.arm.com/community/arm-community-blogs/b/servers-and-cloud-computing-blog/posts/multi-chip-and-chi-c2c

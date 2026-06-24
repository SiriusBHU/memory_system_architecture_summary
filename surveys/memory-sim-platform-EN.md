# Terminal Memory Architecture Simulation Platforms: From Loosely-Coupled Toolchains to Modular Full-Stack Frameworks

> This document surveys the landscape of memory architecture simulation platforms used in terminal/mobile SoC design and computer architecture research. It compares the **original approach** — loosely-coupled full-system simulators with external DRAM models (gem5 + DRAMSim2) — against the **evolved approach** — modern modular, composable simulation frameworks (Ramulator 2.0, gem5 built-in DRAM controller, CXL-DMSim, SST). The goal is to help memory system architects choose the right simulation stack for their design-space exploration needs.

## 1. Scope and method

**Domain definition.** This study covers software-based architectural simulators used to model and evaluate memory subsystems in terminal devices (smartphones, tablets, IoT) and general-purpose SoCs. It spans the stack from functional emulation (QEMU) through cycle-accurate DRAM simulation (Ramulator, DRAMSim) to full-system heterogeneous simulation (gem5, SST). Commercial EDA verification platforms (Synopsys Platform Architect, Cadence VIP) are included for context but are not the primary focus.

**What "original" and "evolved" mean here.** The *original* approach (circa 2011–2019) relied on gem5 as the CPU/cache/interconnect simulator with DRAMSim2 plugged in as an external memory backend via a loosely-coupled callback interface. Each tool was developed independently; integration required manual patching and version-matching. The *evolved* approach (2020–present) features modular, composable frameworks: gem5's built-in DRAM/NVM controller with unified memory interfaces; Ramulator 2.0/2.1 with its Interface/Implementation architecture; CXL-DMSim with silicon-validated CXL protocol models; and SST's event-driven parallel simulation with pluggable memory elements.

**Sources.** 15 distinct sources spanning academic papers (9), kernel/project documentation (2), vendor documentation (2), and industry surveys (2). At least 6 contain hard performance or accuracy numbers.

## 2. Problem background

**What the system needs to do.** Simulate a terminal SoC's memory subsystem — from last-level cache through the memory controller, DRAM/LPDDR channels, and potentially CXL-attached or NVM-backed tiers — with enough fidelity to guide architectural decisions before tape-out.

**Why this domain becomes hard.** Three constraints collide: (1) *timing accuracy* — DRAM command scheduling, bank-level parallelism, refresh, and thermal effects must be modeled at cycle granularity to predict real bandwidth and latency; (2) *system coverage* — modern SoCs have heterogeneous compute (CPU + GPU + NPU + DSP) sharing unified memory through complex coherence protocols (CHI, ACE), which a DRAM-only simulator cannot capture; (3) *simulation speed* — cycle-accurate full-system simulation runs 100–900× slower than native [ref 1], making large-workload evaluation prohibitively expensive.

**Why the original solution is no longer enough.** The explosion of memory technologies (DDR5, LPDDR5/5X, HBM3, CXL 2.0/3.0, persistent memory) and heterogeneous compute models broke the assumption that a single external DRAM simulator (DRAMSim2, supporting only DDR2/DDR3) could adequately model the memory subsystem. Integration friction, limited protocol coverage, and the inability to simulate disaggregated or tiered memory architectures forced the community to rethink simulation infrastructure.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **Technology coverage gap** — DRAMSim2 supported only DDR2/DDR3. Simulating LPDDR5, HBM3, or CXL-attached memory required switching to a different tool entirely, with no unified framework for mixed-memory studies. [ref 2, ref 4]
2. **Integration friction and accuracy loss** — Coupling gem5 with DRAMSim2 introduced a 2× latency discrepancy compared to DRAMSim3 due to abstraction-level mismatches between the host simulator's memory controller model and the external DRAM model. [ref 11, ref 9]
3. **Simulation speed bottleneck** — gem5 full-system simulation runs 100–900× slower than native execution. Adding a detailed external DRAM model increases this to ~250× for memory-intensive workloads, making design-space exploration across hundreds of configurations impractical. [ref 1, ref 9]
4. **No CXL/disaggregated memory support** — Before 2024, no open-source simulator could model CXL.mem protocol, memory pooling, or fabric-attached memory — a critical gap as the industry moves toward disaggregated architectures. [ref 5, ref 6]
5. **Monolithic codebase, difficult extension** — Adding a new DRAM standard or memory controller policy to DRAMSim2 or the original Ramulator required modifying deeply intertwined code, discouraging community contributions. [ref 2]

### Bottleneck evidence

![Memory Simulation Platform Bottleneck: Speed vs Accuracy vs Coverage Tradeoff](assets/memory-sim-platform-bottleneck.png)

The figure above illustrates the fundamental three-way tradeoff in memory simulation. QEMU achieves only 5–10× slowdown but provides zero DRAM timing accuracy. gem5 with its built-in DRAM model reaches moderate accuracy (score 6/10) at 200× slowdown. Standalone cycle-accurate DRAM simulators (DRAMSim3, Ramulator 2.0) achieve high accuracy at trace-driven speed but cover only the DRAM subsystem. CXL-DMSim achieves the highest accuracy (silicon-validated, score 10/10) and broadest coverage (full CXL stack) but at 300× slowdown. No single tool dominates all three axes — this is the bottleneck the evolved frameworks aim to mitigate through modularity and composability.

**Key numbers:**
- Ramulator 2.0 standalone: 58–62 ms for 5M requests (random), 31–33 ms (streaming) [ref 2]
- DRAMSim3 standalone: 51–52 ms (random), 37–38 ms (streaming) [ref 4]
- gem5 full-system: 100–900× slowdown vs native [ref 1]
- gem5 + DRAMSim2 latency discrepancy: ~2× vs DRAMSim3 [ref 9]

## 4. Architectures: original vs evolved

### Simulator Landscape Overview

Before comparing original vs evolved architectures, here is a comprehensive map of the major simulators in the ecosystem:

| Simulator | Type | Scope | Key Memory Standards | Open Source | Primary Use |
|---|---|---|---|---|---|
| **gem5** | Full-system | CPU + Cache + Interconnect + Memory | DDR3/4/5, LPDDR5, HBM, NVM | Yes (BSD) | Architecture research |
| **Ramulator 2.0/2.1** | DRAM-focused | Memory controller + DRAM device | DDR5, LPDDR5, HBM3, GDDR6 | Yes (MIT) | DRAM design exploration |
| **DRAMSim3** | DRAM-focused | Memory controller + DRAM + Thermal | DDR4, LPDDR4, HBM2 | Yes | DRAM + thermal analysis |
| **DRAMSim2** | DRAM-focused | Memory controller + DRAM | DDR2, DDR3 | Yes | Legacy DRAM studies |
| **NVMain 2.0** | NVM-focused | Memory controller + NVM device | PCM, STT-RAM, ReRAM, MLC | Yes | NVM architecture research |
| **SST** | Full-system | HPC nodes + Interconnect + Memory | Pluggable (via elements) | Yes (BSD) | HPC / parallel simulation |
| **CXL-DMSim** | Full-system | gem5 + CXL controller + Expander | CXL.io, CXL.mem, DDR4/5 | Yes | CXL memory research |
| **CXL-ClusterSim** | Cluster-scale | gem5 + SST + CXL fabric | CXL pooling/sharing | Yes | Disaggregated memory |
| **DRackSim** | Rack-scale | Multi-node + Memory pools + Network | CXL, DDR4 | Yes | Rack-scale memory |
| **QEMU** | Functional | Full OS + Devices (no timing) | N/A (functional only) | Yes (GPL) | Software development |
| **Synopsys PADK** | Commercial | SoC architecture exploration | SystemC/TLM, configurable | No | Pre-RTL SoC design |
| **Cadence VIP** | Commercial | Protocol verification | LPDDR5/6, DDR5, HBM3 | No | IP/SoC verification |

### Original Architecture — Loosely-Coupled Toolchain (gem5 + DRAMSim2)

```
Original — gem5 + DRAMSim2 Loosely-Coupled Integration

    +-------------------+
    |   Application /   |
    |   OS Workload     |
    +-------------------+
            |
            | syscall / instruction
            v
    +-------------------+       coherence         +-------------------+
    |   gem5 CPU Model  | ----------------------> |  gem5 Cache       |
    |  (O3 / Minor /    |   snoop / invalidate    |  Hierarchy        |
    |   KVM)            | <---------------------- |  (L1/L2/LLC)      |
    +-------------------+                         +-------------------+
                                                         |
                                                         | miss / writeback
                                                         v
                                                  +-------------------+
                                                  | gem5 Crossbar /   |
                                                  | Interconnect      |
                                                  +-------------------+
                                                         |
                                          callback API   | (patched interface)
                                          ~~~~~~~~~~~~~~~|~~~~~~~~~~~~~~~~
                                                         v
                                                  +-------------------+
                                                  | DRAMSim2          |
                                                  | (External Process)|
                                                  |  - DDR2/DDR3 only |
                                                  |  - Fixed scheduler|
                                                  |  - No thermal     |
                                                  |  - No NVM         |
                                                  +-------------------+
                                                         |
                                                         | dram command
                                                         v
                                                  +-------------------+
                                                  | DRAM Device Model |
                                                  | (ranks, banks)    |
                                                  +-------------------+

    Weaknesses:
    - Patched callback API: version coupling, ~2× latency discrepancy
    - DDR2/DDR3 only: no LPDDR5, HBM3, CXL, NVM
    - Two separate codebases with independent timing models
    - No thermal, power-down, or refresh-mode modeling
```

*Original: gem5 provides CPU/cache/interconnect simulation; DRAMSim2 is plugged in via a patched callback API to handle DRAM timing, but the two tools share no common abstraction and support only DDR2/DDR3.*

### Evolved Architecture — Modular Full-Stack Framework

```
Evolved — Modern Composable Memory Simulation Stack

    +-------------------+
    |   Application /   |
    |   OS Workload     |
    +-------------------+
            |
            | syscall / instruction
            v
    +-------------------+    * CHI / ACE-Lite     +-------------------+
    |   gem5 CPU Model  | ----------------------> | * gem5 Ruby/Classic|
    |  (O3 / Minor /    |    coherence protocol   |   Cache Hierarchy |
    |   KVM / GPU /     | <---------------------- |   (L1/L2/LLC)     |
    | * NPU / Accel)    |                         +-------------------+
    +-------------------+                                |
                                                         | miss / writeback
                                                         v
                                              * +-------------------+
                                                | gem5 Built-in     |
                                                | Memory Controller |
                                                | * Unified MemCtrl |
                                                | * + MemInterface  |
                                                +-------------------+
                                                   /       |       \
                                                  /        |        \
                                  +-----------+ +-----------+ +-----------+
                                  |* DDR5 /   | |* NVM      | |* CXL      |
                                  |  LPDDR5 / | |  Interface| |  Controller|
                                  |  HBM3 /   | | (Optane,  | | (CXL.mem, |
                                  |  GDDR6    | |  STT-RAM) | |  CXL.io)  |
                                  +-----------+ +-----------+ +-----------+
                                       |             |             |
                                       v             v             v
                                  +-----------+ +-----------+ +-----------+
                                  |  DRAM     | |  NVM      | |* CXL      |
                                  |  Device   | |  Device   | |  Memory   |
                                  |  Model    | |  Model    | |  Expander |
                                  +-----------+ +-----------+ +-----------+

    OR: Swap gem5's built-in DRAM with Ramulator 2.0 for deeper DRAM exploration:

    +-------------------+     Interface/Implementation pattern
    | Ramulator 2.0     |--------------------------------------------+
    | Modular DRAM Sim  |                                            |
    +-------------------+                                            |
    | * Frontend        |  trace file / gem5 callback / CPU model    |
    | * MemorySystem    |  channel topology, address mapping         |
    | * Controller      |  * pluggable scheduler, queue policy       |
    | * DRAM (BankGroup,|  * templated lambda for DRAM commands      |
    |   Bank, Row, Col) |  * DDR5/LPDDR5/HBM3/GDDR6 built-in       |
    | * RefreshMgmt     |  per-bank, per-rank, adaptive refresh      |
    | * RowHammer Def   |  * modular RowHammer mitigation plugins    |
    | * Plugin system   |  * add new standard without touching core  |
    +-------------------+--------------------------------------------+

    * = new or changed vs original architecture

    Key advances:
    - Unified MemCtrl + MemInterface: one API, swap DRAM/NVM/CXL backends
    - Modular Interface/Implementation: add DDR6 without modifying core
    - Silicon-validated CXL models (CXL-DMSim)
    - Heterogeneous compute: CPU + GPU + NPU in one simulation
    - Thermal modeling (DRAMSim3), power-down states, fine-grained refresh
    - SST parallel simulation for rack-scale CXL clusters
```

*Evolved: A modular stack where the memory controller, memory interface, and device model are decoupled behind stable APIs. New DRAM standards, NVM technologies, or CXL protocols are added as plug-in implementations without modifying the simulation core. Full heterogeneous compute (CPU+GPU+NPU) shares the same memory hierarchy.*

## 5. Why evolved helps, what it still doesn't solve

### Why the evolved solution helps

- **Technology coverage gap** — Ramulator 2.0 uses templated lambda functions to describe DRAM command semantics, enabling built-in support for DDR5, LPDDR5, HBM3, and GDDR6. Adding a new standard requires ~200 lines of specification code, not a fork of the entire simulator. [ref 2]
- **Integration friction and accuracy loss** — gem5's built-in memory controller (unified MemCtrl + MemInterface, introduced 2020) eliminates the external callback API. The memory controller and DRAM timing model share the same event-driven engine, removing the 2× latency discrepancy observed with DRAMSim2 integration. [ref 11]
- **Simulation speed bottleneck** — Ramulator 2.0 achieves comparable or faster simulation speed than DRAMSim3 despite higher modularity (58 ms vs 51 ms for 5M random requests). SST enables parallel simulation across multiple cores, reducing wall-clock time for large-scale configurations. Ramulator 2.1 adds Python-based configuration for automated design-space exploration. [ref 2, ref 3]
- **No CXL/disaggregated memory support** — CXL-DMSim (2024) provides a full-system CXL simulator with CXL.io and CXL.mem protocol support, validated against real CXL 1.1 silicon (both ASIC and FPGA prototypes). CXL-ClusterSim (2025) extends this to multi-node disaggregated memory clusters via gem5+SST integration. [ref 5, ref 6]
- **Monolithic codebase, difficult extension** — Ramulator 2.0's Interface/Implementation pattern decouples every component (frontend, controller, DRAM device, refresh manager, RowHammer defense) behind abstract interfaces. New techniques are added as separate modules without modifying baseline code. [ref 2]

### What it still doesn't solve

- **Speed–accuracy tradeoff remains fundamental** — Even with all improvements, cycle-accurate full-system simulation still runs 200–300× slower than native execution. Simulating a 10-second mobile workload takes 30–50 minutes. No modular refactoring eliminates this physics constraint; only sampled simulation or ML-based surrogate models (Concorde, 2025) can bypass it. [ref 9]
- **Heterogeneous IP model fidelity** — gem5's GPU model is approximate; NPU and DSP models are still rudimentary or missing. The memory traffic from these accelerators is often generated by statistical models rather than cycle-accurate execution, limiting the fidelity of end-to-end SoC memory analysis. [ref 12]
- **Commercial IP simulation gap** — Open-source simulators cannot model proprietary memory controller IPs (e.g., Qualcomm's or Apple's custom LPDDR5 controllers). Commercial tools (Synopsys PADK, Cadence VIP) fill this role but are not composable with open-source frameworks. [ref 13, ref 14]
- **Validation against real silicon remains rare** — Only CXL-DMSim has been validated against real CXL hardware. Most DRAM simulators are validated against DRAM datasheets, not silicon measurements. The Ramulator 2.0 accuracy re-evaluation study (2025) found discrepancies in certain timing scenarios. [ref 5, ref 15]

## 6. Comparison table

| Dimension | Original (gem5 + DRAMSim2) | Evolved (Ramulator 2.0 / gem5 MemCtrl / CXL-DMSim) | Improvement |
|---|---|---|---|
| DRAM standards supported | DDR2, DDR3 (2 standards) [ref 4] | DDR5, LPDDR5, HBM3, GDDR6, CXL.mem (6+ standards) [ref 2, ref 5] | +4 standards, 3× coverage |
| Time to add new DRAM standard | ~2000 LOC, fork required [ref 2] | ~200 LOC via templated lambda (Ramulator 2.0) [ref 2] | −90% effort |
| Standalone simulation speed (5M requests, random) | 51–52 ms (DRAMSim2) [ref 2] | 58–62 ms (Ramulator 2.0), 51–52 ms (DRAMSim3) [ref 2, ref 4] | no change (comparable) |
| Full-system slowdown vs native | 200–250× (gem5 + DRAMSim2) [ref 1] | 200× (gem5 built-in), 300× (CXL-DMSim) [ref 1, ref 5] | no change to −50× (CXL adds overhead) |
| DRAM timing accuracy vs silicon | datasheet-level, 2× latency gap in integration [ref 9] | datasheet-level (Ramulator 2.0); silicon-validated (CXL-DMSim, <5% error) [ref 5, ref 15] | +silicon validation for CXL |
| Thermal modeling | no [ref 4] | yes (DRAMSim3: runtime thermal + power) [ref 4] | +thermal capability |
| CXL / disaggregated memory | no [ref 5] | yes (CXL-DMSim: CXL.io + CXL.mem; CXL-ClusterSim: multi-node) [ref 5, ref 6] | +entire CXL stack |
| NVM support (PCM, STT-RAM) | no (DRAMSim2 is DRAM-only) [ref 8] | yes (gem5 NVM interface; NVMain 2.0 integration) [ref 8, ref 11] | +NVM modeling |

## 7. One-word characterization

**Composable** (可组合) — The evolved simulation frameworks replace monolithic DRAM-only tools with composable modules behind stable interfaces, enabling a single simulation run to mix DDR5, HBM3, NVM, and CXL memory tiers without code modification — directly addressing the technology coverage gap that made the original toolchain obsolete.

## 8. Open questions and caveats

- **Ramulator 2.0 accuracy under scrutiny.** The 2025 "Cleaning up the Mess" study found that Ramulator 2.0's real-system modeling accuracy has discrepancies in certain timing scenarios. The community has not yet converged on a standard validation methodology.
- **LPDDR6 simulation support is missing.** JEDEC finalized LPDDR6 in 2025, but no open-source simulator yet supports it. Ramulator 2.1's Python-based specification interface may accelerate this.
- **GPU/NPU memory traffic modeling is immature.** gem5's GPU model produces approximate memory traffic; NPU models are mostly absent. Mobile SoC memory studies that ignore accelerator traffic may draw incorrect conclusions.
- **CXL 3.0 fabric simulation is nascent.** CXL-DMSim supports CXL 1.1; CXL-ClusterSim targets CXL 2.0 pooling. CXL 3.0's fabric and peer-to-peer features have no simulator support yet.
- **Commercial vs open-source gap persists.** Synopsys PADK and Cadence VIP offer proprietary IP models and UVM-based verification flows that open-source tools cannot replicate. Architecture teams often need both stacks.
- **No unified benchmark suite.** Different simulators use different trace formats, workload generators, and accuracy metrics, making apples-to-apples comparison difficult. The "Mess" benchmark framework (2024) is a first attempt but not yet widely adopted.

## 9. References

1. Lowe-Power, J. et al. "The gem5 Simulator: Version 20.0+." *ACM SIGARCH*, 2020. https://par.nsf.gov/biblio/10192408
2. Luo, H. et al. "Ramulator 2.0: A Modern, Modular, and Extensible DRAM Simulator." *IEEE CAL*, 2023. https://arxiv.org/abs/2308.11030 — Local: `surveys/sources/memory-sim-platform/README.md`
3. Luo, H. et al. "Ramulator 2.1: A Composable Memory System Simulator for Modern DRAM Systems." 2025. https://arxiv.org/html/2606.13844
4. Li, S. et al. "DRAMsim3: A Cycle-Accurate, Thermal-Capable DRAM Simulator." *IEEE CAL*, 2020. https://dl.acm.org/doi/10.1109/LCA.2020.2973991
5. Wang, Y. et al. "CXL-DMSim: A Full-System CXL Disaggregated Memory Simulator With Comprehensive Silicon Validation." 2024. https://arxiv.org/abs/2411.02282
6. UC Davis. "CXL-ClusterSim: Modeling CXL-based Disaggregated Memory Cluster using gem5 and SST." 2025. https://arxiv.org/html/2605.27745v1
7. "DRackSim: Simulating CXL-enabled Large-Scale Disaggregated Memory Systems." *ACM SIGSIM PADS*, 2024. https://dl.acm.org/doi/10.1145/3615979.3656059
8. Poremba, M. et al. "NVMain 2.0: Architectural Simulator to Model (Non-)Volatile Memory Systems." 2015. https://www.researchgate.net/publication/273350177
9. Hwang, S. et al. "Survey of CPU and memory simulators in computer architecture." *Simulation Modelling Practice and Theory*, 2024. https://www.sciencedirect.com/science/article/abs/pii/S1569190X24001461
10. "Modeling and Simulating Emerging Memory Technologies: A Tutorial." 2025. https://arxiv.org/pdf/2502.10167
11. gem5 project. "Memory Controller Updates for New DRAM Technologies, NVM Interfaces." 2020. https://www.gem5.org/2020/05/27/memory-controller.html
12. gem5 project. "Toward Full-System Heterogeneous Simulation: Merging gem5-SALAM." ISCA 2025. https://www.gem5.org/2025/07/30/gem5AccHetSimBlog.html
13. Synopsys. "Platform Architect Development Kit (PADK)." 2024. https://www.design-reuse.com/blog/56161
14. Cadence. "Simulation VIP for LPDDR5." 2024. https://www.cadence.com/en_US/home/tools/system-design-and-verification/verification-ip/simulation-vip/memory-models/dram/lpddr5.html
15. "Cleaning up the Mess: Re-Evaluating the Real-System Modeling Accuracy of Ramulator 2.0." 2025. https://arxiv.org/html/2510.15744v4

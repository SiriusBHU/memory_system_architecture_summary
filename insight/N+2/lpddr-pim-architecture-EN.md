# LPDDR Processing-In-Memory Architecture for Mobile AI

> This document compares the original conventional LPDDR architecture (CPU/NPU fetches data from DRAM over the memory bus, von Neumann bottleneck) with the evolved LPDDR-PIM architecture (processing elements near/in DRAM banks, reduced data movement, hybrid DRAM+PIM bank allocation) for on-device AI inference. It surveys academic (ISCA, DAC, Hot Chips, arxiv) and industry (Samsung, JEDEC) progress from 2023--2026.

## 1. Scope and method

**Domain definition.** Processing-in-memory (PIM) architectures built on LPDDR5/LPDDR5X mobile DRAM for accelerating LLM inference and other AI workloads on resource-constrained terminal devices (smartphones, edge boards, AR/VR headsets). The focus is on architectural modifications that embed computation near or within DRAM banks to exploit the 8x gap between internal bank bandwidth and external I/O bandwidth.

**What "original" and "evolved" mean here.** The *original* solution is the standard von Neumann memory hierarchy: the SoC's CPU, NPU, or iGPU issues memory requests over the LPDDR5 interface, fetching model weights and activations through the external I/O bus at up to 51.2 GB/s per x64 channel. All computation occurs on-die in the SoC. The *evolved* solution places SIMD/MAC processing elements inside each DRAM bank (or bank group), enabling GEMV and lightweight GEMM operations to execute at internal bank bandwidth (up to 409.6 GB/s), coordinated by a near-data memory controller that dynamically partitions banks between standard DRAM access and PIM computation.

**Sources.** 9 primary sources: 4 academic papers (arxiv/ISCA 2025--2026), 3 industry references (Samsung Hot Chips 2023, JEDEC LPDDR6 PIM roadmap), 2 system-level analyses (PIM-AI architecture, Micron/Semi Engineering mobile memory reports). Source types span academic papers, vendor presentations, and standards body announcements.

## 2. Problem background

**What the system needs to do.** Run LLM inference (1B--13B parameters) on-device with acceptable token throughput (>10 tok/s) and energy efficiency (<5 J per query) on mobile DRAM budgets of 8--16 GB.

**Why this domain becomes hard.** LLM decode-phase inference is dominated by memory-bound GEMV operations: each token generation requires reading the full model weight matrix once. A 7B-parameter INT8 model demands ~7 GB of weight reads per token. At LPDDR5's 51.2 GB/s external bandwidth, this takes ~137 ms per token---far short of the 100 ms target for interactive use. Data movement energy dominates: at ~20 pJ/bit, fetching 7B INT8 weights costs ~1.12 J per token, while the arithmetic itself costs <0.05 J. The von Neumann bottleneck thus manifests as both a latency wall and an energy wall.

**Why the original solution is no longer enough.** Mobile speculative inference, multi-head attention with long KV caches, and mixture-of-experts (MoE) dispatch all increase parallel memory access demands beyond what a single LPDDR5 channel can sustain. Speculative decoding converts GEMV into GEMM, creating batch-like traffic that further saturates the external bus while remaining too small for NPU compute arrays to reach full utilization.

## 3. Specific problems and bottleneck evidence

1. **External bandwidth is 8x lower than internal bank bandwidth** --- A single x64 LPDDR5 chip provides 51.2 GB/s of external I/O, but internal all-bank bandwidth reaches 409.6 GB/s. This 8x gap means PIM can theoretically deliver 8x the effective bandwidth for data-local operations [LP-Spec].

2. **Data movement dominates energy consumption** --- Off-DRAM data transfers consume ~20 pJ/bit, whereas intra-DRAM movement costs only ~3 pJ/bit (15% of off-chip cost). For a 7B model, this translates to ~1.12 J/token off-chip vs ~0.17 J/token on-chip [LP-Spec, PIM-AI].

3. **Speculative inference breaks GEMV-optimized PIM** --- As speculation length increases from 1 to 16 tokens, conventional PIM's latency and energy advantages deteriorate sharply because GEMV becomes GEMM, requiring data reuse patterns that per-bank vector units cannot exploit [LP-Spec].

4. **Existing edge PIM suffers from three structural limitations** --- (a) limited bandwidth improvement due to few activated banks, (b) blocked execution preventing simultaneous processor-PIM operation, and (c) imbalanced computing unit utilization from fixed data mapping [CD-PIM].

5. **Realized bandwidth falls far below peak** --- LPDDR5X worst-case realized bandwidth can fall up to 50% below vendor-published peak rates, widening the effective gap that PIM must bridge [Fraunhofer/SemiEngineering].

### Bottleneck evidence

| Scenario | External BW | Internal BW | Gap | Source |
|---|---|---|---|---|
| LPDDR5 x64, single channel | 51.2 GB/s | 409.6 GB/s | 8x | [LP-Spec] |
| LPDDR5X x64, dual device | 68 GB/s | ~512 GB/s | ~7.5x | [PIM-AI] |
| Weight fetch, 7B INT8, 1 token | 137 ms (ext) | ~17 ms (int) | 8x latency | derived |
| Energy per bit, off-chip vs on-chip | ~20 pJ/bit | ~3 pJ/bit | 6.7x energy | [LP-Spec] |

## 4. Architectures: original vs evolved

**Original --- Conventional LPDDR (Von Neumann)**

```
    +-------------------+
    |  Mobile SoC       |
    |  +------+ +-----+ |
    |  | CPU  | | NPU | |
    |  +------+ +-----+ |
    |       |      |     |
    |  +----+------+--+  |
    |  | Memory Ctrl  |  |
    |  +-------+------+  |
    +---------|-----------+
              | LPDDR5 I/O Bus (51.2 GB/s)
              |
    +---------v-----------+
    |  LPDDR5 Module       |
    |  +--+ +--+ +--+ +--+|
    |  |Bk| |Bk| |Bk| |Bk||  Bank 0..15
    |  | 0| | 1| | 2| |..||  (data storage only)
    |  +--+ +--+ +--+ +--+|
    |                      |
    |  Internal BW: 409.6 GB/s (inaccessible)
    |  External BW: 51.2 GB/s (bottleneck)
    +----------------------+

    Data flow: Weight data travels Bank -> I/O bus ->
              SoC -> ALU -> result back to DRAM
    All computation on SoC side of the bus.
```

*Original: All data must traverse the narrow external I/O bus. Internal bank bandwidth is stranded.*

**Evolved --- Hybrid LPDDR5-PIM (LP-Spec Architecture)**

```
    +-------------------+
    |  Mobile SoC       |
    |  +------+ +-----+ |
    |  | CPU  | | NPU | |
    |  +------+ +-----+ |
    |       |      |     |
    |  +----+------+--+  |
    |  | Memory Ctrl  |  |
    |  | * + NMC      |  |  * Near-data Memory Controller
    |  +-------+------+  |
    +---------|-----------+
              | LPDDR5 I/O Bus (51.2 GB/s)
              |
    +---------v-----------+
    |  * Hybrid LPDDR5-PIM Module                  |
    |                                              |
    |  DRAM Rank (standard access)                 |
    |  +--+ +--+ +--+ +--+                        |
    |  |Bk| |Bk| |Bk| |Bk|   (weights for NPU)   |
    |  | 0| | 1| | 2| |..+                        |
    |  +--+ +--+ +--+ +--+                        |
    |                                              |
    |  * PIM Rank (compute-enabled)                |
    |  +--------+ +--------+ +--------+ +--------+|
    |  |Bk + MPU| |Bk + MPU| |Bk + MPU| |Bk+MPU ||
    |  | 0  SIMD| | 1  SIMD| | 2  SIMD| |.. SIMD||
    |  | INT8   | | INT8   | | INT8   | | INT8   ||
    |  +--------+ +--------+ +--------+ +--------+|
    |  * 8 MPUs serve 16 banks (2 banks per MPU)   |
    |  * Each MPU: 4x 32-wide SIMD ALUs            |
    |  * Internal BW: 409.6 GB/s (now utilized)    |
    |                                              |
    |  * DAU: dynamic DRAM <-> PIM data migration  |
    |  * DTP: draft token pruner (spec. inference) |
    +----------------------------------------------+

    Data flow: PIM banks compute GEMV locally at
    409.6 GB/s; NPU handles GEMM via DRAM rank;
    * NMC coordinates parallel NPU + PIM execution.
```

*Evolved: Processing elements (MPUs) embedded in PIM banks exploit 8x internal bandwidth. Near-data memory controller (NMC) enables dynamic bank allocation and NPU-PIM parallel execution. New/changed elements marked with `*`.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **Bandwidth wall** --- PIM computes GEMV at internal bank bandwidth (409.6 GB/s vs 51.2 GB/s external), yielding up to 8x effective bandwidth for memory-bound decode operations [LP-Spec, CD-PIM].

- **Energy wall** --- Intra-DRAM data movement costs 15% of off-chip transfers (~3 vs ~20 pJ/bit), reducing energy per token by 7.56x on LP-Spec and 10--20x on PIM-AI compared to mobile SoC baselines [LP-Spec, PIM-AI].

- **Speculative inference GEMM problem** --- LP-Spec's hybrid DRAM+PIM rank design with dynamic workload scheduling offloads GEMM to NPU while PIM handles GEMV concurrently, achieving 13.21x performance over NPU-only baselines [LP-Spec].

- **Bank utilization** --- CD-PIM's cross-division pseudo-bank design quadruples activated banks per access cycle, achieving 14.6x decode-stage acceleration on edge platforms [CD-PIM].

- **Power savings for edge deployment** --- Samsung LPDDR-PIM saves 72% power compared to conventional DRAM access patterns by eliminating round-trip data movement for supported operations [Samsung Hot Chips 2023].

### What it still doesn't solve

- **Prefill (encoding) phase remains compute-bound** --- PIM excels at memory-bound GEMV but cannot accelerate compute-bound GEMM during initial prompt encoding; PIM-AI reports encoding latency ~3x longer than GPU equivalents [PIM-AI].

- **Limited precision and operation support** --- Current PIM processing elements support INT8/FP16 MAC operations; complex operations (softmax, layer norm, non-linear activations) must still be executed on the SoC, requiring data round-trips for mixed workloads.

- **No standard programming model** --- Each PIM design (LP-Spec, CD-PIM, PIM-AI, Samsung PIM) uses proprietary instruction sets and data layout conventions; no unified ISA or compiler toolchain exists.

- **Capacity trade-off** --- Banks allocated to PIM computation cannot simultaneously serve as standard DRAM capacity, creating a capacity-vs-compute tension that the DAU must continuously rebalance.

- **Thermal constraints on sustained PIM operation** --- Adding processing elements to DRAM dies increases power density; sustained PIM computation in mobile thermal envelopes (3--5 W package) may require throttling that erodes theoretical gains.

## 6. Comparison table

| Dimension | Original (Conventional LPDDR) | Evolved (LPDDR-PIM) | Improvement | Source |
|---|---|---|---|---|
| Effective bandwidth for GEMV | 51.2 GB/s (ext. I/O) | 409.6 GB/s (internal bank) | 8x | [LP-Spec] |
| Decode throughput (LLM, spec. inference) | 1x (NPU baseline) | 13.21x (LP-Spec NPU+PIM) | +13.21x | [LP-Spec] |
| Energy efficiency (tokens/J) | 0.13 tok/J (RTX 3090) / 4.3 tok/J (mobile NPU) | 32.6 tok/J (LP-Spec) | 7.56x vs NPU | [LP-Spec] |
| Data movement energy per bit | ~20 pJ/bit (off-chip) | ~3 pJ/bit (intra-DRAM) | 6.7x reduction | [LP-Spec] |
| Edge decode acceleration | 1x (GPU-only, Jetson) | 14.6x (CD-PIM, LLaMA-13B) | +14.6x | [CD-PIM] |
| Power vs conventional DRAM access | 100% (baseline) | 28% (Samsung LPDDR-PIM) | -72% | [Samsung HC 2023] |
| PIM die area overhead | 0% | 0.8% of 32 Gb LPDDR5 die | minimal | [CD-PIM] |
| Tokens/s improvement (mobile, 7B) | 19 tok/s (LPDDR5X SoC) | 28--49.6% more (PIM-AI) | +25--49.6% | [PIM-AI] |

## 7. One-word characterization

**Near-data** (近数据) --- LPDDR-PIM shifts computation from the SoC to the memory die, exploiting the 8x internal-to-external bandwidth gap to break the von Neumann data movement bottleneck for memory-bound AI workloads while keeping the LPDDR form factor and interface compatibility.

## 8. Open questions and caveats

- **JEDEC standardization timeline** --- JEDEC is nearing completion of LPDDR6 PIM as a formal standard (announced April 2026), but no ratified spec exists yet; early implementations are vendor-proprietary and mutually incompatible.
- **Compiler and software ecosystem** --- No production-grade compiler can automatically partition workloads between SoC and PIM; current solutions require manual annotation or custom scheduling (LP-Spec's DTP, CD-PIM's mode switching).
- **GEMM scaling** --- As on-device batch sizes grow (multi-agent, speculative decoding with longer drafts), the GEMV-to-GEMM transition point shifts; PIM architectures optimized for today's speculation lengths (4--16 tokens) may need re-tuning for future workloads.
- **Memory coherence** --- PIM banks operating independently from the SoC cache hierarchy create coherence challenges; LP-Spec's NMC serializes access but this may limit scaling to multi-channel configurations.
- **Security implications** --- Model weights resident in PIM banks during computation may be vulnerable to physical side-channel attacks (rowhammer-adjacent); no published analysis addresses PIM-specific threat models.
- **Thermal validation on real mobile devices** --- All published results use simulation or FPGA prototypes; silicon-validated thermal and performance data under realistic mobile power envelopes is absent.

## 9. References

1. **LP-Spec** --- Xu et al., 2025. "LP-Spec: Leveraging LPDDR PIM for Efficient LLM Mobile Speculative Inference with Architecture-Dataflow Co-Optimization." ISCA 2025 / arxiv 2508.07227. URL: https://arxiv.org/abs/2508.07227
2. **CD-PIM** --- Authors, 2025. "CD-PIM: A High-Bandwidth and Compute-Efficient LPDDR5-Based PIM for Low-Batch LLM Acceleration on Edge-Device." arxiv 2601.12298. URL: https://arxiv.org/abs/2601.12298
3. **PIM-AI** --- Authors, 2024. "PIM-AI: A Novel Architecture for High-Efficiency LLM Inference." arxiv 2411.17309. URL: https://arxiv.org/abs/2411.17309
4. **Samsung PIM at Hot Chips 2023** --- Samsung, 2023. "PIM/PNM for Transformer based AI." Hot Chips 35 presentation. URL: https://www.hc2023.hotchips.org/assets/program/conference/day1/PIM/23_HC35_PIM_PNM_Samsung_final.pdf
5. **Samsung LPDDR-PIM announcement** --- Samsung Global Newsroom, 2023. "Samsung Brings In-Memory Processing Power to Wider Range of Applications." URL: https://news.samsung.com/global/samsung-brings-in-memory-processing-power-to-wider-range-of-applications
6. **JEDEC LPDDR6 PIM roadmap** --- JEDEC, 2026. "JEDEC Previews LPDDR6 Roadmap Expanding LPDDR into Data Centers and Processing-in-Memory." URL: https://www.jedec.org/news/pressreleases/jedec%C2%AE-previews-lpddr6-roadmap-expanding-lpddr-data-centers-and-processing-memory
7. **PIM-SHERPA** --- Authors, 2026. "PIM-SHERPA: Software Method for On-device LLM Inference by Resolving PIM Memory Attribute and Layout Inconsistencies." arxiv 2603.09216. URL: https://arxiv.org/abs/2603.09216
8. **Samsung PIM IEEE Spectrum** --- IEEE Spectrum, 2023. "Samsung Speeds AI With Processing in Memory." URL: https://spectrum.ieee.org/samsung-ai-memory-chips
9. **LPDDR for edge AI** --- Semi Engineering, 2025. "LPDDR Memory Is Key For On-Device AI Performance." URL: https://semiengineering.com/lpddr-memory-is-key-for-on-device-ai-performance/

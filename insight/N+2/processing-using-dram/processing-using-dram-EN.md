# Processing-using-DRAM Latency Optimization

> **One-word summary:** Adaptation

## 1. Scope and Method

This survey traces the evolution of Processing-using-DRAM (PuD) from fixed-precision bulk bitwise operations to data-aware, dynamic-precision execution with concurrent multi-array parallelism. The focus is on the Proteus framework (ICS 2025), the first hardware design that directly attacks PuD's inherent high-latency problem rather than merely hiding it behind data-level parallelism. We contextualize Proteus against prior PuD mechanisms -- Ambit (MICRO 2017) for triple-row-activation bulk bitwise, and SIMDRAM (ASPLOS 2021) for end-to-end bit-serial SIMD -- and examine how narrow-value exploitation and adaptive arithmetic transform PuD from a throughput-only technology into one that is also latency-competitive. Sources include the Proteus paper (arXiv 2501.17466, ICS 2025), the Ambit and SIMDRAM papers, and the CMU-SAFARI Proteus simulator repository.

## 2. Problem Background

Processing-using-DRAM (PuD) exploits the analog operational properties of DRAM arrays -- specifically charge sharing across bitlines -- to perform bulk logic operations directly inside memory, without moving data to a CPU or GPU. The canonical mechanism is triple-row activation (Ambit): simultaneously activating three DRAM rows causes a bitwise majority (MAJ) function via charge sharing, and combined with NOT operations, achieves functional completeness (AND, OR, NOT, and therefore any Boolean function).

PuD is attractive because it operates at the full internal DRAM bandwidth (hundreds of GB/s per chip) rather than the narrow off-chip bus bandwidth. Ambit demonstrated 44x throughput improvement and 35x energy reduction versus a Skylake CPU for bulk bitwise operations. SIMDRAM extended this to arbitrary operations via MAJ/NOT decomposition, achieving 88x CPU throughput across 16 banks.

However, all existing PuD mechanisms share a critical limitation: they process every bit of every operand, regardless of the actual information content. A 32-bit addition where both operands fit in 8 bits still executes 32 bit-serial cycles. This fixed-precision, throughput-only execution model means PuD latency scales linearly with operand bit-width, making it uncompetitive for latency-sensitive tasks and unsuitable for workloads with narrow-value distributions common in real applications (e.g., neural network inference, graph analytics, database operations).

## 3. Concrete Problems and Evidence

### P1: Fixed bit-precision wastes cycles on useless bits

Standard PuD processes all N bits of an N-bit operand in N serial cycles, regardless of actual value magnitude. For 32-bit integers, a value of 5 (binary: 00000...101) still requires 32 cycles. Evidence: Proteus authors demonstrate that across 12 real-world applications, the average effective precision (non-redundant bits) is significantly less than the nominal precision, with many values being "narrow" -- having extensive leading zeros or ones [1].

### P2: Throughput-only execution model limits applicability

Existing PuD hides its high per-operation latency through massive data-level parallelism: operating on thousands of rows simultaneously. This works for bulk operations (memset, bitmap intersection) but fails for latency-sensitive operations where result availability timing matters (e.g., dependent computations in graph traversal, conditional branches in neural network inference). Evidence: SIMDRAM achieves 88x throughput over CPU with 16 banks but does not address single-operation latency, which remains proportional to bit-width [2][3].

### P3: Single-array execution underutilizes DRAM parallelism

A DRAM chip contains multiple banks, each with multiple subarrays/arrays. Standard PuD confines each operation to a single array, leaving other arrays idle. The internal parallelism of DRAM -- designed for row-level parallelism across banks -- is not exploited for accelerating individual operations. Evidence: Proteus shows that concurrent execution across multiple arrays within a single bank can reduce latency proportionally to the number of available arrays [1].

### P4: Rigid data representation forces suboptimal arithmetic

PuD operations use a fixed data representation (typically unsigned magnitude or two's complement) and a single arithmetic algorithm regardless of operand properties. Different representations (sign-magnitude, ones' complement) and algorithms (ripple-carry vs. carry-save) have different latency profiles depending on operand values. Evidence: Proteus demonstrates that dynamically selecting between data representations and arithmetic implementations based on runtime operand characteristics yields substantial latency reductions [1].

## 4. Architecture Diagrams

### Original: Standard PuD with Fixed-Precision Bulk Bitwise

```
 ┌─────────────────────────────────────────────────┐
 │                  DRAM Chip                       │
 │  ┌──────────────────────────────────────────┐   │
 │  │              Bank 0                      │   │
 │  │  ┌────────────────────────────────────┐  │   │
 │  │  │         Subarray / Array 0         │  │   │
 │  │  │  Row A: [0100 1100 0000 ... 0011]  │  │   │
 │  │  │  Row B: [1101 0010 0000 ... 1100]  │  │   │
 │  │  │  Row C: [0000 0000 0000 ... 0000]  │  │   │
 │  │  │                                    │  │   │
 │  │  │  Triple-Row Activation (TRA):      │  │   │
 │  │  │  Activate A, B, C simultaneously   │  │   │
 │  │  │  → C = MAJ(A, B, C)               │  │   │
 │  │  │  All 32 bits processed regardless  │  │   │
 │  │  │  of value content                  │  │   │
 │  │  └────────────────────────────────────┘  │   │
 │  │                                          │   │
 │  │  Arrays 1..N: IDLE during operation      │   │
 │  └──────────────────────────────────────────┘   │
 │                                                  │
 │  Banks 1..7: IDLE (no cross-bank PuD)           │
 └─────────────────────────────────────────────────┘
                        │
              Memory Controller
          (issues TRA commands,
           fixed N-cycle latency
           for N-bit operands)

 Problem: 32-bit add of 5+3 takes 32 cycles.
 Only one array active. Bits 3..31 are all zeros
 but still processed. Throughput-only model.
```

### Evolved: Proteus Data-Aware PuD with Dynamic Precision

```
 ┌─────────────────────────────────────────────────┐
 │                  DRAM Chip                       │
 │  ┌──────────────────────────────────────────┐   │
 │  │              Bank 0                      │   │
 │  │  ┌──────────────┐  ┌──────────────┐     │   │
 │  │  │  Array 0     │  │  Array 1     │     │   │
 │  │  │  Bits 0..7   │  │  Bits 8..15  │     │   │
 │  │  │  (active)    │  │  (active)    │     │   │
 │  │  │  CONCURRENT  │  │  CONCURRENT  │     │   │
 │  │  └──────┬───────┘  └──────┬───────┘     │   │
 │  │         │                  │              │   │
 │  │  ┌──────────────┐  ┌──────────────┐     │   │
 │  │  │  Array 2     │  │  Array 3     │     │   │
 │  │  │  Bits 16..23 │  │  Bits 24..31 │     │   │
 │  │  │  SKIPPED     │  │  SKIPPED     │     │   │
 │  │  │  (narrow val)│  │  (narrow val)│     │   │
 │  │  └──────────────┘  └──────────────┘     │   │
 │  └──────────────────────────────────────────┘   │
 └─────────────────────────────────────────────────┘
                        │
         ┌──────────────────────────────┐
         │   Proteus Runtime Engine     │
         │  ┌────────────────────────┐  │
         │  │ Narrow-Value Detector  │  │
         │  │ Scans leading 0s/1s   │  │
         │  │ → effective precision  │  │
         │  └────────┬───────────────┘  │
         │  ┌────────▼───────────────┐  │
         │  │ Repr. & Algo Selector  │  │
         │  │ Sign-mag vs 2's comp   │  │
         │  │ Ripple vs carry-save   │  │
         │  └────────┬───────────────┘  │
         │  ┌────────▼───────────────┐  │
         │  │ Multi-Array Scheduler  │  │
         │  │ Distributes bit-slices │  │
         │  │ across DRAM arrays     │  │
         │  └────────────────────────┘  │
         └──────────────────────────────┘

 Result: 32-bit add of 5+3 takes ~3 cycles (3-bit
 effective precision) spread across arrays, not 32.
```

## 5. What It Helps / What It Does Not Solve

### Helps

- **Reduces PuD operation latency.** By processing only the effective bits (narrow-value optimization), latency drops from O(N) to O(k) where k is the effective precision, often much smaller than N.
- **Exploits DRAM internal parallelism.** Distributing bit-slices across multiple arrays within a bank enables concurrent execution, providing near-linear latency reduction with array count.
- **Improves performance per unit area.** Proteus achieves 17x, 7.3x, and 10.2x performance per mm-squared compared to CPU, GPU, and SIMDRAM respectively, averaged across 12 applications.
- **Dramatically reduces energy.** 90.3x, 21x, and 8.1x lower energy consumption than CPU, GPU, and SIMDRAM respectively.
- **Transparent to the programmer.** The runtime engine dynamically selects data representation and arithmetic algorithms without requiring programmer annotation or code changes.
- **Enables latency-sensitive PuD workloads.** By reducing per-operation latency, PuD becomes viable for workloads beyond bulk throughput operations, including graph analytics and neural network inference.

### Does not solve

- **DRAM technology constraints.** PuD still requires triple-row activation, which stresses DRAM timing margins and may be incompatible with some DRAM vendors' cell designs. Proteus does not change the underlying DRAM array.
- **Data layout requirements.** PuD requires bit-serial (vertical) data layout in DRAM, which conflicts with conventional row-major (horizontal) layout. Data must be transposed before PuD can operate, incurring setup cost.
- **Limited operation repertoire.** While SIMDRAM showed arbitrary Boolean operations are possible, complex operations (floating-point multiply, division) still decompose into many bit-serial primitives with high latency even after Proteus optimization.
- **Narrow-value dependency.** The latency benefit is proportional to value narrowness. Workloads with uniformly wide values (e.g., encryption, compression) see less benefit from dynamic precision.
- **No inter-bank coordination.** Proteus optimizes within a single bank. Operations spanning multiple banks still require memory controller coordination and data movement.
- **Reliability concerns.** Triple-row activation operates outside normal DRAM specifications and may have lower noise margins, potentially increasing soft error rates.

## 6. Quantitative Comparison

| Dimension | Standard PuD (Ambit/SIMDRAM) | Proteus (Data-Aware PuD) |
|---|---|---|
| Bit-precision | Fixed: all N bits processed for N-bit operands | Dynamic: only effective bits (leading 0/1 skipped) |
| Array utilization | Single array per operation | Concurrent multi-array execution within a bank |
| Data representation | Fixed (typically unsigned/2's complement) | Adaptive: selects best repr. per operation at runtime |
| Arithmetic algorithm | Fixed (single implementation) | Flexible: chooses optimal algorithm per operand pair |
| Perf/mm-sq vs CPU | Ambit: 44x throughput; SIMDRAM: ~5.5x per bank | 17x (single bank, averaged across 12 apps) |
| Perf/mm-sq vs GPU | SIMDRAM: ~0.36x per bank (16 banks needed) | 7.3x (single bank) |
| Perf/mm-sq vs SIMDRAM | Baseline (1x) | 10.2x |
| Energy vs CPU | Ambit: 35x; SIMDRAM: 257x (16 banks) | 90.3x |
| Energy vs GPU | SIMDRAM: 31x (16 banks) | 21x |
| Energy vs SIMDRAM | Baseline (1x) | 8.1x |
| Latency model | O(N) per operation, N = bit-width | O(k/A) where k = effective bits, A = arrays used |
| Programmer effort | SIMDRAM: MAJ/NOT decomposition | Transparent runtime adaptation |
| Hardware overhead | Ambit: ~1% area; SIMDRAM: 0.2% area | Runtime engine in memory controller (modest) |

## 7. One-Word Summary

**Adaptation** -- the core insight is that PuD operations should adapt their precision, data representation, and parallelism strategy to the actual data being processed, rather than blindly processing every bit of every operand at fixed width.

## 8. Open Questions

1. **Floating-point PuD.** Proteus targets integer arithmetic. Can the narrow-value/adaptive-representation approach extend to IEEE 754 floating-point, where exponent and mantissa have different narrowness properties?

2. **Integration with PIM controllers.** As PIM architectures (HBM-PIM, GDDR-PIM) mature, can Proteus-style runtime engines be embedded in PIM logic dies rather than in the memory controller?

3. **Compiler-assisted precision hints.** The current runtime detects narrow values at execution time. Could compilers provide static hints about value ranges (e.g., from range analysis) to pre-configure the Proteus engine and reduce detection overhead?

4. **Multi-bank coordination.** Proteus optimizes within a single bank. For operations spanning multiple banks (e.g., large matrix multiplications), how should the memory controller orchestrate cross-bank PuD with Proteus-style adaptation?

5. **DRAM vendor compatibility.** Triple-row activation is not part of any DRAM standard (DDR5, LPDDR5X). What is the path to standardization, and how do Proteus's additional timing requirements interact with vendor-specific DRAM cell designs?

6. **Security implications.** PuD operations that share DRAM rows could be exploited for side-channel attacks (analogous to RowHammer). Does Proteus's multi-array concurrent execution expand the attack surface?

7. **Interaction with CXL memory.** CXL-attached memory pools may serve multiple hosts. How would PuD/Proteus operations work in a shared CXL memory architecture where multiple hosts contend for DRAM arrays?

## 9. References

1. Bostanci, E., Oliveira, G. F., Cali, D. S., Ghiasi, N. M., Fernandez, R., Luna, I. E., Manglik, S., Novo, D., Gomez-Luna, J., Mutlu, O. (2025). "Proteus: Achieving High-Performance Processing-Using-DRAM with Dynamic Bit-Precision, Adaptive Data Representation, and Flexible Arithmetic." *Proceedings of the 39th ACM International Conference on Supercomputing (ICS 2025)*. arXiv: [2501.17466](https://arxiv.org/abs/2501.17466). GitHub: [CMU-SAFARI/Proteus](https://github.com/CMU-SAFARI/Proteus).

2. Seshadri, V., Lee, D., Mullins, T., Hassan, H., Boroumand, A., Kim, J., Kozuch, M. A., Mutlu, O., Gibbons, P. B., Mowry, T. C. (2017). "Ambit: In-Memory Accelerator for Bulk Bitwise Operations Using Commodity DRAM Technology." *Proceedings of the 50th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/3123939.3124544](https://dl.acm.org/doi/10.1145/3123939.3124544).

3. Hajinazar, N., Oliveira, G. F., Gregorio, S., Ferreira, J. D., Ghiasi, N. M., Patel, M., Alser, M., Cali, D. S., Novo, D., Mutlu, O. (2021). "SIMDRAM: An End-to-End Framework for Bit-Serial SIMD Computing in DRAM." *Proceedings of the 26th ACM International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*. DOI: [10.1145/3445814.3446749](https://dl.acm.org/doi/10.1145/3445814.3446749). arXiv: [2105.12839](https://arxiv.org/abs/2105.12839).

4. Ghose, S., Boroumand, A., Kim, J. S., Gomez-Luna, J., Mutlu, O. (2019). "Processing-in-Memory: A Workload-Driven Perspective." *IBM Journal of Research and Development*, 63(6). Available: [PDF](https://arxiv.org/pdf/2012.03112).

5. Seshadri, V., Hsieh, K., Boroumand, A., Lee, D., Kozuch, M. A., Mutlu, O., Gibbons, P. B., Mowry, T. C. (2015). "Fast Bulk Bitwise AND and OR in DRAM." *IEEE Computer Architecture Letters*, 14(2).

6. Gao, F., Tziantzioulis, G., Wentzlaff, D. (2019). "ComputeDRAM: In-Memory Compute Using Off-the-Shelf DRAMs." *Proceedings of the 52nd Annual IEEE/ACM International Symposium on Microarchitecture (MICRO)*. DOI: [10.1145/3352460.3358260](https://dl.acm.org/doi/10.1145/3352460.3358260).

7. Ferreira, J. D., Oliveira, G. F., et al. (2022). "pLUTo: In-DRAM Lookup Tables to Enable Massively Parallel General-Purpose Computation." arXiv: [2104.07699](https://arxiv.org/abs/2104.07699).

# Heterogeneous SoC On-Device AI Inference Scheduling and Bandwidth Management

> This document compares the original single-accelerator inference approach with the evolved heterogeneous multi-IP co-scheduling approach for on-device LLM inference on mobile/edge SoCs. It surveys academic (SOSP 2025, ASPLOS 2025, arxiv) and industry (Intel, Qualcomm) progress from 2024–2026.

## 1. Scope and method

**Domain definition.** Scheduling and bandwidth management for large language model inference across heterogeneous compute IPs (CPU, GPU, NPU) on unified-memory Systems-on-Chip in mobile phones, laptops, and edge devices. The central challenge is that memory bandwidth — not compute throughput — is the binding constraint for autoregressive decode, and a single accelerator cannot saturate the shared DRAM bus.

**What "original" and "evolved" mean here.** The *original* solution is single-accelerator inference: an LLM runs entirely on one compute IP (GPU-only via MNN/MLC, or NPU-only via llm.npu), while other on-die accelerators sit idle. The *evolved* solution is heterogeneous multi-IP co-scheduling: CPU, GPU, and NPU execute different inference phases or tensor partitions concurrently, coordinated by bandwidth-aware dispatch and sharing KV cache through unified physical memory with zero-copy synchronization.

**Sources.** 10 primary sources: 4 academic papers (SOSP 2025, ASPLOS 2025, arxiv 2024–2026), 3 system frameworks (llama.cpp, MNN, PowerInfer-2), 3 vendor references (Qualcomm Snapdragon 8 Gen 3, Intel Core Ultra, Samsung LPDDR5X). Source types span peer-reviewed systems papers, open-source runtime documentation, and SoC vendor datasheets.

## 2. Problem background

**What the system needs to do.** Run 1B–8B parameter LLMs locally on a mobile or edge SoC with 8–32 GB shared DRAM, supporting interactive latency (<100 ms/token) for reactive user queries and high throughput for background proactive tasks (summarization, RAG indexing, agentic pipelines).

**Why this domain becomes hard.** Modern mobile SoCs (Snapdragon 8 Gen 3, Intel Core Ultra) pack 3+ compute IPs — CPU cores, a mobile GPU (Adreno/Arc), and a dedicated NPU (Hexagon/AI Boost) — but existing inference engines treat them as independent, mutually exclusive targets. The NPU excels at fixed-shape INT8 GEMM (prefill) but degrades on dynamic-shape GEMV (decode); the GPU handles dynamic shapes well but cannot alone saturate DRAM bandwidth. Peak LPDDR5X bandwidth is ~68 GB/s, yet a single GPU achieves only 40–45 GB/s (59–66% utilization) during decode [HeteroInfer]. Meanwhile, agentic workloads introduce concurrent reactive and proactive LLM flows with conflicting latency/throughput objectives that single-accelerator engines cannot prioritize.

## 3. Specific problems and bottleneck evidence

1. **Single accelerator leaves bandwidth on the table** — On Snapdragon 8 Gen 3, GPU-only decode utilizes 40–45 GB/s of a 68 GB/s DRAM bus (59–66%), leaving ~25 GB/s idle. NPU-only achieves similar utilization. Concurrent GPU+NPU execution reaches ~60 GB/s (88% utilization), a 37% bandwidth improvement [HeteroInfer].

2. **NPU cannot handle dynamic decode shapes efficiently** — NPU systolic arrays are fixed at 32×32; any activation dimension smaller than 32 incurs identical latency as dimension-32, wasting cycles. Autoregressive decode (batch-1 GEMV) triggers this "stage performance" floor, making NPU-only decode slower than GPU [HeteroInfer].

3. **GEMV kernels degrade under co-execution but GEMM tolerates it** — Memory-intensive GEMV (decode) latency degrades significantly when overlapped with another high-bandwidth kernel on the same DRAM bus. Compute-bound GEMM (prefill) maintains efficiency under co-execution because it is not bandwidth-limited [Agent.xpu].

4. **No flow-level concurrency or prioritization** — Existing engines (llama.cpp, MNN, MLC) assume single-shot inference with no mechanism to distinguish reactive vs. proactive requests. A background summarization task blocks an interactive query because there is no preemption or priority scheduling [Agent.xpu].

5. **NPU graph compilation is prohibitively slow for dynamic inputs** — Online NPU graph generation costs 408.4 ms at sequence length 135 on Snapdragon 8 Gen 3, making naive dynamic-shape NPU execution slower than GPU-only inference [HeteroInfer].

### Bottleneck evidence

| Scenario | Metric | Single-IP | Heterogeneous | Gap | Source |
|---|---|---|---|---|---|
| Snapdragon 8 Gen 3, decode, Llama-8B | DRAM BW utilization | 40–45 GB/s (GPU) | ~60 GB/s (GPU+NPU) | +37% BW | [HeteroInfer] |
| Snapdragon 8 Gen 3, decode, Llama-8B | Throughput | 9.3 tok/s (MNN GPU) | 14.0 tok/s (HeteroInfer) | 1.50x | [HeteroInfer] |
| Intel Core Ultra, mixed agentic | Reactive latency | 1x (llama.cpp CPU) | 0.22x (Agent.xpu) | 4.6x lower | [Agent.xpu] |
| Snapdragon 8 Gen 3, prefill 256tok, Llama-8B | Throughput | 42.4 tok/s (MNN GPU) | 247.9 tok/s (HeteroInfer) | 5.85x | [HeteroInfer] |
| NPU online graph gen, seq_len=135 | Compilation latency | 408.4 ms | 0 ms (pre-compiled) | eliminated | [HeteroInfer] |

## 4. Architectures: original vs evolved

**Original — Single-Accelerator Inference**

```
    User Request
         |
         v
    +-----------+
    |  Runtime   |--- load weights ---> +----------+
    | (MNN /     |                      |  Model   |
    |  MLC /     |                      |  Weights |
    |  llm.npu)  |                      | (DRAM)   |
    +-----------+                       +----------+
         |
         | dispatch ALL layers
         v
    +-------------------+
    |  Single Accel.    |      +-----------+
    |  (GPU -or- NPU)  | ---> | KV Cache  |
    |                   |      | (DRAM)    |
    |  prefill: GEMM    |      +-----------+
    |  decode:  GEMV    |           |
    +-------------------+           |
         |                     Attention
         | idle: other IPs     Computation
         | unused (NPU/CPU         |
         | or GPU/CPU)             v
         v                    Output Tokens
    [BW util: 59-66%]
    [No preemption, no priority]
```

*Original: All layers run on one IP; other accelerators idle. Bandwidth utilization capped at ~60%. No flow-level scheduling.*

**Evolved — Heterogeneous Multi-IP Co-Scheduling**

```
    User Request ──────────────────── Background Task
    (reactive, low-latency)           (proactive, throughput)
         |                                  |
         v                                  v
    +----------------------------------------------+
    | * Flow-Aware Scheduler                       |
    |   - * priority queue (reactive > proactive)  |
    |   - * kernel-level preemption (<100 ms)      |
    |   - * bandwidth-pressure monitor (Pmem)      |
    +----------------------------------------------+
         |                    |                |
         v                    v                v
    +---------+        +----------+      +-----------+
    |  CPU    |        | * NPU    |      | * GPU     |
    | (outlier|        | (prefill |      | (decode   |
    |  comp.) |        |  GEMM,   |      |  GEMV,    |
    +---------+        |  static) |      |  dynamic) |
                       +----------+      +-----------+
                            |                  |
                  * tensor partition    * tensor partition
                  * affinity-guided     * elastic binding
                            |                  |
                            v                  v
                   +-------------------------------+
                   | * Unified Physical Memory     |
                   |   (zero-copy KV cache share)  |
                   +-------------------------------+
                            |
               * Bandwidth-Aware Dispatch:
               low (<0.4):  aggressive co-schedule
               med (0.4-0.7): selective pairing
               high (>=0.7): sequential, reactive first
                            |
                            v
                      Output Tokens
    [BW util: ~88%]
    [Reactive latency: 4.6x lower]
```

*Evolved: Prefill (GEMM) routes to NPU, decode (GEMV) routes to GPU, tensor partitions split across both; bandwidth-pressure dispatch prevents DRAM contention; kernel-level preemption guarantees reactive responsiveness. New/changed elements marked with `*`.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **Single accelerator leaves bandwidth on the table** — Concurrent GPU+NPU execution raises DRAM bandwidth utilization from 59–66% to ~88% (40–45 GB/s to ~60 GB/s on Snapdragon 8 Gen 3), directly translating to 1.50x decode speedup for Llama-8B [HeteroInfer].

- **NPU cannot handle dynamic decode shapes** — Phase-aware dispatch routes prefill (compute-bound GEMM with static shapes) to NPU and decode (memory-bound GEMV with dynamic shapes) to GPU, exploiting each IP's strength. HeteroInfer's activation-centric partition further splits dynamic sequences into NPU-friendly fixed-length chunks plus a GPU-handled remainder [HeteroInfer].

- **GEMV degrades under co-execution** — Agent.xpu's three-tier bandwidth-pressure dispatch monitors real-time memory pressure (Pmem) and switches from aggressive co-scheduling (Pmem < 0.4) to sequential execution (Pmem >= 0.7), preventing decode GEMV degradation while still exploiting parallelism when headroom exists [Agent.xpu].

- **No flow-level concurrency** — Agent.xpu introduces kernel-level preemption with <100 ms granularity via operator chunking, plus slack-aware backfill that inserts proactive kernels into structural/compute/memory slack windows. This achieves 4.6x lower reactive latency while sustaining 1.6–6.8x higher proactive throughput [Agent.xpu].

- **NPU graph compilation is too slow** — HeteroInfer's offline profiler-solver collaboration pre-compiles NPU graphs for all anticipated tensor shapes in <20 minutes, eliminating the 408.4 ms online compilation overhead entirely [HeteroInfer].

### What it still doesn't solve

- **Thermal throttling under sustained dual-IP load** — Running GPU+NPU concurrently increases power draw and die temperature; no published work measures sustained performance under mobile thermal envelopes (skin temperature limits, DVFS throttling). Real-world performance may be lower than benchmarks.

- **Model portability across SoC vendors** — HeteroInfer's offline profiler must re-characterize every new SoC (Snapdragon vs. Dimensity vs. Exynos); Agent.xpu is currently Intel-only (OpenVINO). No vendor-neutral heterogeneous inference API exists.

- **Accuracy impact of NPU INT8 quantization** — NPU paths typically require INT8 or lower precision; the accuracy delta versus FP16 GPU inference is model-dependent and not systematically benchmarked across diverse tasks (reasoning, code, multilingual).

- **OS-level resource arbitration** — Heterogeneous schedulers operate in userspace, unaware of other apps competing for GPU/NPU (gaming, camera ISP, background ML tasks). No integration with Android NNAPI scheduling or iOS CoreML resource management exists.

## 6. Comparison table

| Dimension | Original (Single-IP) | Evolved (Hetero Co-Schedule) | Improvement | Source |
|---|---|---|---|---|
| DRAM BW utilization (decode) | 59–66% (GPU-only, 40–45 GB/s) | ~88% (GPU+NPU, ~60 GB/s) | +37% absolute | [HeteroInfer] |
| Decode throughput (Llama-8B, Snapdragon 8 Gen 3) | 9.3 tok/s (MNN GPU) | 14.0 tok/s | 1.50x | [HeteroInfer] |
| Prefill throughput (Llama-8B, 256 tok) | 42.4 tok/s (MNN GPU) | 247.9 tok/s | 5.85x | [HeteroInfer] |
| End-to-end speedup (LongBench, prefill-heavy) | 1x (MNN-OpenCL) | 6.02x | 6.02x | [HeteroInfer] |
| Reactive latency (agentic mixed workload) | 1x (llama.cpp CPU) | 0.22x (Agent.xpu) | 4.6x lower | [Agent.xpu] |
| Proactive throughput (background tasks) | 1x (llama.cpp CPU) | 1.6–6.8x (Agent.xpu) | 1.6–6.8x | [Agent.xpu] |
| Synchronization overhead (per layer) | N/A (single IP) | ~negligible (sleep-predict + polling) | eliminated vs. naive 400 us | [HeteroInfer] |
| NPU graph compilation | 408.4 ms online (seq=135) | 0 ms (offline pre-compiled) | eliminated | [HeteroInfer] |

## 7. One-word characterization

**Co-schedule** (协同调度) — Inference moves from single-accelerator monopoly to bandwidth-aware multi-IP cooperation, where NPU handles compute-bound prefill, GPU handles memory-bound decode, and a pressure-aware dispatcher arbitrates shared DRAM bandwidth, lifting utilization from ~60% to ~88% and lowering reactive latency by 4.6x.

## 8. Open questions and caveats

- **Thermal sustainability** — Published benchmarks measure burst performance; sustained GPU+NPU co-execution under mobile thermal constraints (skin-temperature < 42 °C) may trigger DVFS throttling that erodes the 1.5–6x speedup. No thermal-aware scheduling policy has been proposed.
- **Multi-model and multi-tenant scheduling** — Current work assumes a single LLM; real agentic devices may run 2+ models concurrently (vision + language + speech). Cross-model heterogeneous scheduling is unexplored.
- **LPDDR6 impact** — LPDDR6 (arriving mid-2026, ~14 Gbps/pin, roughly double LPDDR5X bandwidth) may shift the bottleneck back to compute for smaller models, potentially reducing the benefit of dual-IP bandwidth aggregation.
- **OS integration** — Userspace schedulers (Agent.xpu, HeteroInfer) cannot coordinate with kernel-level GPU/NPU resource management (Android NNAPI, vendor HALs), risking contention with camera, display, and other ML workloads.
- **Generalization beyond Qualcomm and Intel** — HeteroInfer targets Snapdragon only; Agent.xpu targets Intel Core Ultra only. MediaTek Dimensity, Samsung Exynos, and Apple Silicon each have distinct NPU architectures (different systolic array sizes, quantization support, memory mapping). Portability remains unvalidated.
- **Energy efficiency** — Lower latency does not guarantee lower energy per token; dual-IP execution may increase total energy due to synchronization overhead and leakage current from active idle states. No published Joules-per-token comparison exists.

## 9. References

1. **HeteroInfer** — Chen et al., 2025. "Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference." ACM SOSP 2025. arxiv 2501.14794. URL: https://dl.acm.org/doi/10.1145/3731569.3764808
2. **Agent.xpu** — Authors, 2025. "Agent.xpu: Efficient Scheduling of Agentic LLM Workloads on Heterogeneous SoC." arxiv 2506.24045. URL: https://arxiv.org/abs/2506.24045
3. **mllm-NPU** — Xu et al., 2025. "Fast On-device LLM Inference with NPUs." ACM ASPLOS 2025. URL: https://dl.acm.org/doi/10.1145/3669940.3707239
4. **PowerInfer-2** — Authors, 2024. "PowerInfer-2: Fast Large Language Model Inference on a Smartphone." arxiv 2406.06282. URL: https://arxiv.org/abs/2406.06282
5. **Qualcomm Snapdragon 8 Gen 3** — Qualcomm, 2024. Product Brief. URL: https://www.qualcomm.com/smartphones/products/8-series/snapdragon-8-gen-3-mobile-platform
6. **Intel Core Ultra** — Intel, 2024. "Intel Core Ultra Processors." URL: https://www.intel.com/content/www/us/en/products/details/processors/core-ultra.html
7. **Samsung LPDDR5X** — Samsung Semiconductor, 2024. "Samsung Develops Industry's Fastest 10.7Gbps LPDDR5X DRAM." URL: https://semiconductor.samsung.com/news-events/news/samsung-develops-industrys-fastest-gbps--lpddr5x-dram-optimized-for-ai-applications/
8. **HeRo** — Authors, 2026. "HeRo: Adaptive Orchestration of Agentic RAG on Heterogeneous Mobile SoC." arxiv 2603.01661. URL: https://arxiv.org/abs/2603.01661
9. **ShadowNPU** — Authors, 2025. "ShadowNPU: System and Algorithm Co-design for NPU-Centric On-Device LLM Inference." arxiv 2508.16703. URL: https://arxiv.org/abs/2508.16703
10. **RooflineBench** — Authors, 2026. "RooflineBench: A Benchmarking Framework for On-Device LLMs via Roofline Analysis." arxiv 2602.11506. URL: https://arxiv.org/abs/2602.11506

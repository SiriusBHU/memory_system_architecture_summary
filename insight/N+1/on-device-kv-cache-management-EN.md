# On-Device LLM KV Cache & Multi-Agent Memory Management

> This document compares the original DRAM-only KV cache approach with the evolved multi-tier storage + quantization + persistence + heterogeneous co-scheduling approach for on-device LLM inference. It surveys academic (SOSP, arxiv) and industry (Apple MLX, Qualcomm) progress from 2024–2026.

## 1. Scope and method

**Domain definition.** Memory management for key-value caches during large language model inference on resource-constrained terminal devices (smartphones, PCs, edge boards). The KV cache stores intermediate attention states and grows linearly with sequence length and batch size, dominating memory consumption during long-context generation.

**What "original" and "evolved" mean here.** The *original* solution is standard DRAM-resident KV cache: the full FP16/BF16 KV tensor lives in system DRAM, allocated per-request, discarded when the session ends. The *evolved* solution is a composite of techniques — quantized (Q4/Q8) caches, persistent storage to NVMe/flash, heterogeneous compute scheduling across NPU/iGPU, and cross-agent cache sharing — that collectively break the "one context = one DRAM copy" assumption.

**Sources.** 12 primary sources: 6 academic papers (SOSP 2025, arxiv 2024–2026), 3 industry reports (Apple MLX, Samsung LPDDR5X), 3 system-level references (llama.cpp quantized KV, vLLM PagedAttention, oMLX two-tier cache). Source types span academic papers, open-source framework documentation, and vendor engineering blogs.

## 2. Problem background

**What the system needs to do.** Run multi-turn LLM inference (7B–14B parameters) locally on a device with 8–16 GB DRAM, supporting 32K–100K+ token contexts for agentic workflows (meeting summarization, document analysis, multi-step reasoning).

**Why this domain becomes hard.** KV cache size scales as `2 × n_layers × n_heads × head_dim × seq_len × dtype_bytes` per request. For LLaMA3-8B at FP16 with 32K context, a single request's KV cache is ~4.3 GB; at batch-12 with 32K, it reaches 54 GB [KVSwap]. Mobile DRAM bandwidth (LPDDR5X: ~70 GB/s) is shared between model weights, activations, and KV cache, creating contention. Flash storage (NVMe ~1.8 GB/s, eMMC ~250 MB/s) is 40–280× slower than DRAM but 5× cheaper per GB.

**Why the original solution is no longer enough.** On-device multi-agent applications (4+ concurrent agents, each with independent conversation history) require simultaneous KV caches that exceed physical DRAM. Cold re-prefill to restore context costs O(n) compute, adding 15–172 seconds of latency per switch at 4K–32K context [Q4 Persistent Cache].

## 3. Specific problems and bottleneck evidence

1. **KV cache exceeds device DRAM at moderate context lengths** — A single 4B-parameter model at 32K context with batch-12 requires 54 GB for KV cache alone, far exceeding the 8–16 GB DRAM budget of mobile devices [KVSwap].

2. **Multi-agent context switching destroys latency** — Discarding and re-computing KV cache when switching between agents costs 15.7s (4K) to 172.1s (32K) cold TTFT on Gemma 3 12B on M4 Pro, making interactive multi-agent workflows unusable [Q4 Persistent Cache].

3. **Sparsity-based eviction loses accuracy at scale** — Prior KV cache compression methods (InfiniGen, ShadowKV, Loki) achieve 78.7%, 52.3%, and 34.0% accuracy loss respectively on RULER benchmarks at 32K context, making them impractical for production use [KVSwap].

4. **Memory bandwidth contention on unified-memory SoC** — On heterogeneous SoCs where CPU, iGPU, and NPU share system DRAM, memory-intensive GEMV kernels (decode phase) degrade significantly when co-executing with other workloads, but compute-bound GEMM kernels (prefill) tolerate overlap [Agent.xpu].

### Bottleneck evidence

| Scenario | KV Cache Size | Device DRAM | Overflow | Source |
|---|---|---|---|---|
| LLaMA3-8B, 32K ctx, batch-1 | 4.3 GB | 8 GB (phone) | 54% of RAM | [KVSwap] |
| Qwen3-4B, 32K ctx, batch-12 | 54 GB | 64 GB (Jetson) | OOM | [KVSwap] |
| Gemma 3 12B, 32K ctx, 3 agents FP16 | ~12.9 GB | 10.2 GB (M4 Pro) | OOM at agent 3 | [Q4 Cache] |
| Gemma 3 12B, 32K ctx, 12 agents Q4 | ~3.6 GB | 10.2 GB (M4 Pro) | Fits | [Q4 Cache] |
| OPT-30B, 100K ctx | >16 GB | 16 GB (laptop) | OOM (DRAM) | [KVNAND] |

## 4. Architectures: original vs evolved

**Original — DRAM-only KV Cache**

```
    +-----------+                    +----------+
    |   CPU     |--- prefill ------> |  Model   |
    +-----------+                    |  Weights |
         |                           | (DRAM)   |
         | allocate                  +----------+
         v                               |
    +------------------+                 |
    |  KV Cache (FP16) | <-- write ------+
    |  in DRAM         |
    |  (per-request,   | --- read ---> Attention
    |   discarded on   |               Computation
    |   session end)   |
    +------------------+
         |
         | context switch = discard + re-prefill O(n)
         v
    [Cold start: 15s-172s TTFT]
```

*Original: Full FP16 KV cache resides in DRAM; context switch requires expensive re-prefill.*

**Evolved — Multi-Tier Quantized Persistent KV Cache**

```
    +-----------+      +----------+      +-----------+
    |  CPU      |      |  NPU     |      |  iGPU     |
    +-----------+      +----------+      +-----------+
         |                  |                  |
         |    * co-schedule (bandwidth-aware)  |
         +------------------+------------------+
                            |
                   * KV cache shared via
                     unified physical memory
                            |
                            v
    +------------------------------------------+
    | * Hot KV Cache (Q4/Q8 quantized)         |
    |   in DRAM — active agent context         |
    +------------------------------------------+
         |              ^
         | * persist    | * restore (skip prefill)
         v              |
    +------------------------------------------+
    | * Warm KV Cache (Q4 on NVMe/flash)       |
    |   persistent, per-agent, disk-resident   |
    +------------------------------------------+
         |              ^
         | * swap-out   | * prefetch (group-based)
         v              |
    +------------------------------------------+
    | * Cold KV Cache (in 3D NAND flash)       |
    |   KVNAND: compute-in-flash attention     |
    +------------------------------------------+

    [Context switch: 0.6s-1.8s TTFT via cache restore]
```

*Evolved: Three-tier KV cache with Q4 quantization, persistent disk storage, flash-resident compute, and heterogeneous SoC co-scheduling. New/changed elements marked with `*`.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **KV cache exceeds device DRAM** — Q4 quantization reduces KV cache to 28.1% of FP16 size, fitting 4× more agent contexts in the same DRAM budget (12 agents vs 3 at 8K context on 10.2 GB) [Q4 Persistent Cache]. KVSwap offloads to NVMe/eMMC, using 11× less KV cache memory than vLLM [KVSwap].

- **Multi-agent context switching destroys latency** — Persistent Q4 cache eliminates re-prefill, achieving 94× TTFT reduction on Gemma 3 12B at 32K (172s → 1.8s) [Q4 Persistent Cache]. QKVShare further enables inter-agent cache handoff at 397ms vs 1030ms re-prefill at 8K context [QKVShare].

- **Sparsity-based eviction loses accuracy** — KVSwap's full-cache offloading (no eviction) limits RULER accuracy loss to 2.6% (NVMe) vs 78.7% for InfiniGen, 52.3% for ShadowKV, and 34.0% for Loki [KVSwap].

- **Memory bandwidth contention on unified-memory SoC** — Agent.xpu's three-tier bandwidth-pressure dispatch co-schedules prefill (GEMM, compute-bound) on NPU and decode (GEMV, memory-bound) on iGPU, achieving 4.6× lower latency for reactive tasks [Agent.xpu]. HeteroInfer achieves 1.34–6.02× speedup via GPU-NPU heterogeneous execution [HeteroInfer/SOSP 2025].

### What it still doesn't solve

- **Quantization error accumulates over very long contexts** — Q4 KV cache shows +3.0% perplexity increase on DeepSeek models; for safety-critical applications (medical, legal), even small accuracy degradation may be unacceptable [Q4 Persistent Cache].

- **Flash latency remains 40–280× slower than DRAM** — NVMe (~1.8 GB/s) and eMMC (~250 MB/s) create a hard floor on cache restoration speed; eMMC-based phones face 4.1× worse throughput than NVMe devices [KVSwap].

- **No standard API for cross-framework cache portability** — Each framework (llama.cpp, MLX, vLLM) uses proprietary KV cache formats; persistent caches cannot be shared across runtimes without conversion.

- **Power budget of sustained flash I/O** — Continuous NVMe/eMMC read for KV cache swapping may conflict with thermal and power constraints on battery-powered devices; no published data on sustained power draw during active swapping.

## 6. Comparison table

| Dimension | Original (DRAM-only FP16) | Evolved (Multi-tier Q4+Persist) | Improvement | Source |
|---|---|---|---|---|
| KV cache memory per agent (8K ctx, 12B model) | ~4.3 GB (FP16) | ~1.2 GB (Q4) | −72% (0.28× size) | [Q4 Cache] |
| Max concurrent agents (10.2 GB budget) | 3 | 12 | +4× | [Q4 Cache] |
| TTFT on context switch (32K, Gemma 3 12B) | 172,096 ms (cold re-prefill) | 1,819 ms (cache restore) | −94× | [Q4 Cache] |
| Throughput at 32K ctx (Jetson, NVMe) | 17.9 tok/s (vLLM) | 35.6 tok/s (KVSwap, batch-8) | +1.99× | [KVSwap] |
| KV cache DRAM footprint (32K, batch-8) | 100% (vLLM baseline) | 9.1% (KVSwap 1/11) | −11× | [KVSwap] |
| RULER accuracy (32K, LLaMA3-8B) | 100% (full cache) | 97.4% (KVSwap NVMe) | −2.6% | [KVSwap] |
| Decode latency (reactive agent task) | 1× (llama.cpp GPU-only) | 0.22× (Agent.xpu NPU+iGPU) | +4.6× faster | [Agent.xpu] |
| Cost per GB (DRAM vs flash, mobile) | ~$3.5/GB (LPDDR5X) | ~$0.7/GB (UFS 4.0 flash) | −5× cost | [KVNAND] |

## 7. One-word characterization

**Tiered** (分级) — KV cache management moves from a single DRAM tier to a three-tier hierarchy (DRAM → NVMe → flash) with quantized persistence, reducing per-agent DRAM footprint by 72% and enabling 4× more concurrent agents within the same memory budget.

## 8. Open questions and caveats

- **Quantization-accuracy tradeoff at 100K+ tokens** — Published results cap at 32K context; behavior of Q4 persistent cache at 100K+ tokens on reasoning-heavy tasks (math, code) is unknown.
- **Flash endurance under sustained swapping** — Consumer UFS/eMMC flash has limited write endurance (typically 1500–3000 P/E cycles); sustained KV cache swapping could degrade storage lifespan. No published wear-leveling analysis exists.
- **Cross-device portability** — All benchmark numbers come from specific devices (M4 Pro, Jetson Orin AGX); mobile phones with eMMC + 8 GB DRAM may see much worse real-world performance.
- **Agent memory coherence** — When multiple agents share a KV prefix (e.g., shared system prompt), no current system deduplicates the shared portion across persistent Q4 caches, wasting both storage and bandwidth.
- **Security of persistent KV cache** — Serialized KV caches on flash may contain sensitive conversation state; no published work addresses encryption or secure deletion of persistent cache files.
- **Integration with OS memory management** — KV cache swapping operates outside the kernel's page cache / swap subsystem; coexistence with Android LMKD, zram, and memory cgroups is unexplored.

## 9. References

1. **Q4 Persistent KV Cache** — Yshk-Mxim et al., 2026. "Agent Memory Below the Prompt: Persistent Q4 KV Cache for Multi-Agent LLM Inference on Edge Devices." arxiv 2603.04428. URL: https://arxiv.org/abs/2603.04428
2. **KVSwap** — Authors, 2025. "KVSwap: Disk-aware KV Cache Offloading for Long-Context On-device Inference." arxiv 2511.11907. URL: https://arxiv.org/abs/2511.11907
3. **KVNAND** — Authors, 2025. "KVNAND: Efficient On-Device Large Language Model Inference Using DRAM-Free In-Flash Computing." arxiv 2512.03608. URL: https://arxiv.org/abs/2512.03608. Local copy: [sources/on-device-kv-cache-management/KVNAND-2512.03608.pdf](sources/on-device-kv-cache-management/KVNAND-2512.03608.pdf)
4. **Agent.xpu** — Authors, 2025. "Agent.xpu: Agentic LLM Inference on Heterogeneous Edge SoC." arxiv 2506.24045. URL: https://arxiv.org/abs/2506.24045
5. **QKVShare** — Authors, 2026. "QKVShare: Quantized KV-Cache Handoff for Multi-Agent On-Device LLMs." arxiv 2605.03884. URL: https://arxiv.org/abs/2605.03884
6. **HeteroInfer** — Authors, 2025. "Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference." SOSP 2025 / arxiv 2501.14794. URL: https://dl.acm.org/doi/10.1145/3731569.3764808
7. **KV Cache Management Survey** — Authors, 2024. "A Survey on Large Language Model Acceleration based on KV Cache Management." arxiv 2412.19442. URL: https://arxiv.org/abs/2412.19442
8. **HiFC** — Authors, 2025. "HiFC: High-efficiency Flash-based KV Cache Swapping for Scaling LLM Inference." OpenReview. URL: https://openreview.net/forum?id=onhjdWCxZY
9. **TokenDance** — Authors, 2026. "TokenDance: Scaling Multi-Agent LLM Serving via Collective KV Cache Sharing." arxiv 2604.03143. URL: https://arxiv.org/abs/2604.03143
10. **oMLX** — Apple/Community, 2025. "oMLX: Apple Silicon-Optimized LLM Inference with Two-Tier KV Caching." URL: https://betterstack.com/community/guides/ai/omlx-apple-silicon/
11. **Samsung LPDDR5X** — Samsung Semiconductor, 2024. "Samsung Develops Industry's Fastest 10.7Gbps LPDDR5X DRAM." URL: https://semiconductor.samsung.com/news-events/news/samsung-develops-industrys-fastest-gbps--lpddr5x-dram-optimized-for-ai-applications/
12. **LRAgent** — Authors, 2025. "LRAgent: Efficient KV Cache Sharing for Multi-LoRA LLM Agents." ResearchGate. URL: https://www.researchgate.net/publication/400369782

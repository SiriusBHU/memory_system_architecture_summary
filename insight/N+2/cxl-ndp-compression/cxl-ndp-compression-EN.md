# CXL Near-Data Processing and Memory Compression

> **Original:** Standard CXL.mem — host-managed memory expansion, no device-side processing, full-width data transfer over the CXL link.
> **Evolved:** CXL with NDP + Compression — device-side compression/decompression, bit-plane reorganization, transparent bandwidth amplification inside CXL Type-3 devices.

---

## 1. Scope and Method

This document surveys the shift from **passive CXL memory expansion** (data moves unmodified between host and device) to **active CXL memory** where near-data processing (NDP) controllers inside Type-3 devices compress, reorganize, and selectively retrieve data before it crosses the CXL link.

Primary sources:

| ID | Paper / Spec | Year |
|----|-------------|------|
| S1 | CXL-NDP — Amplifying Effective CXL Memory Bandwidth for LLM Inference via Transparent Near-Data Processing (arXiv 2509.03377) | 2025 |
| S2 | IBEX — Internal Bandwidth-Efficient Compression Architecture for Scalable CXL Memory Expansion (arXiv 2603.26131, ICS '26) | 2026 |
| S3 | PNM-KV — Scalable Processing-Near-Memory for 1M-Token LLM Inference (arXiv 2511.00321) | 2025 |
| S4 | CXL 4.0 Specification (CXL Consortium, Nov 2025) | 2025 |
| S5 | ZeroPoint DenseMem — Inline Compression IP for CXL Type-3 Controllers | 2025-26 |

Method: literature survey with quantitative cross-comparison. No novel experiments.

---

## 2. Problem Background

CXL (Compute Express Link) extends server memory capacity by attaching DDR pools behind a coherent PCIe-based interconnect. A CXL Type-3 device exposes byte-addressable memory to the host without requiring driver-level changes. Adoption accelerated after CXL 3.0 (multi-level switching, 2023) and CXL 4.0 (128 GT/s, bundled ports, Nov 2025).

The core tension: **capacity scales, but bandwidth does not keep pace.** DDR5-6400 offers 51.2 GB/s per channel; a PCIe 5.0 x16 CXL link tops out at ~64 GB/s. LLM inference—especially the decode phase with massive KV caches—is memory-bandwidth-bound. Offloading the KV cache to CXL relieves GPU HBM pressure but shifts the bottleneck to the CXL link itself. Measured CXL.mem access latency (~640 ns round-trip) and limited link bandwidth mean that naively expanding memory with CXL can stall rather than accelerate inference. The question becomes: can the device itself reduce the data volume before it ever reaches the link?

---

## 3. Problems and Evidence

### 3.1 CXL Link Bandwidth Is the New Bottleneck

Standard CXL.mem transfers every requested byte unmodified. For a 70B-parameter model in BF16, a single weight fetch of 16 KB at 5-bit effective precision still moves 16 KB across the link. At long context lengths (>64k tokens), KV cache traffic alone can saturate the link.

**Evidence (S1):** With passive CXL, throughput plateaus at ~65k-token context on LLaMA 3.1 70B served on H100 + 256 GB CXL. Beyond that point, the decode phase becomes entirely link-bandwidth-limited.

### 3.2 Byte-Aligned Formats Waste DRAM Bandwidth

Floating-point values stored in standard byte order exhibit low compressibility. Standard lossless codecs (LZ4, ZSTD) applied to raw BF16 weight tensors achieve only 0–23% compression; raw KV cache blocks compress by merely 0.9–6.5%.

**Evidence (S1):** Conventional byte-oriented compression on unmodified LLaMA 3.1 8B BF16 weights yields negligible savings because exponent and mantissa bits are interleaved per value, destroying cross-value regularity.

### 3.3 Promotion/Demotion Overhead in Block-Level Compression

Block-level memory compression schemes that separate hot (uncompressed) from cold (compressed) data suffer performance penalties during demotion—recompressing recently promoted blocks.

**Evidence (S2):** State-of-the-art promotion-based approaches incur up to 40% metadata-access overhead during demotion cycles, limiting effective speedup to < 1.2× in memory-intensive workloads.

### 3.4 KV Cache Recall Cost in Disaggregated Serving

Non-eviction KV-cache frameworks offload the entire cache to CXL memory but must recall token pages to GPU memory for attention computation. At 1M-token contexts, recall traffic dominates.

**Evidence (S3):** Baseline CXL KV offloading without near-memory processing shows recall bandwidth consuming > 85% of available CXL link capacity at 1M tokens, leaving minimal headroom for weight prefetch.

---

## 4. Architecture: Original vs. Evolved

### 4.1 Original: Standard CXL.mem (Passive Expansion)

```
 ┌─────────────────────────────────────────────────┐
 │                     HOST                         │
 │  ┌──────────┐    ┌──────────┐    ┌───────────┐  │
 │  │   CPU    │    │   GPU    │    │ App / LLM  │  │
 │  │ (memory  │◄──►│  (HBM)   │◄──►│  Runtime   │  │
 │  │ controller)   └──────────┘    └───────────┘  │
 │  └────┬─────┘                                    │
 │       │  CXL.mem (raw, uncompressed)             │
 │───────┼──────────────────────────────────────────│
 │       ▼                                          │
 │  ┌─────────────────────────────────────────┐     │
 │  │          CXL Type-3 Device              │     │
 │  │  ┌─────────────┐   ┌────────────────┐  │     │
 │  │  │ CXL.mem     │──►│  DDR Memory    │  │     │
 │  │  │ Controller  │   │  Controller    │  │     │
 │  │  │ (pass-thru) │◄──│  (standard)    │  │     │
 │  │  └─────────────┘   └───────┬────────┘  │     │
 │  │                            │            │     │
 │  │                    ┌───────▼────────┐   │     │
 │  │                    │  DRAM Channels │   │     │
 │  │                    │  (DDR5, raw)   │   │     │
 │  │                    └────────────────┘   │     │
 │  └─────────────────────────────────────────┘     │
 └─────────────────────────────────────────────────┘

 Data flow: Host requests 16 KB → device reads 16 KB
            from DRAM → sends 16 KB over CXL link.
 No transformation. Link bandwidth = effective bandwidth.
```

### 4.2 Evolved: CXL-NDP with Compression + Bit-Plane Layout

```
 ┌──────────────────────────────────────────────────────┐
 │                       HOST                            │
 │  ┌──────────┐   ┌──────────┐   ┌────────────────┐   │
 │  │   CPU    │   │   GPU    │   │  App / LLM     │   │
 │  │ (sees    │◄─►│  (HBM)   │◄─►│  Runtime       │   │
 │  │ multiple │   └──────────┘   │ (precision-    │   │
 │  │ logical  │                  │  aware regions) │   │
 │  │ regions) │                  └────────────────┘   │
 │  └────┬─────┘                                        │
 │       │  CXL.mem (compressed, reduced traffic)       │
 │───────┼──────────────────────────────────────────────│
 │       ▼                                              │
 │  ┌──────────────────────────────────────────────┐    │
 │  │           CXL Type-3 Device + NDP            │    │
 │  │                                              │    │
 │  │  ┌──────────────┐                            │    │
 │  │  │ Request      │  Parses CXL.mem reads,     │    │
 │  │  │ Front-End    │  identifies precision       │    │
 │  │  │ (64-entry    │  region, emits plane        │    │
 │  │  │  MSHR)       │  requests                   │    │
 │  │  └──────┬───────┘                            │    │
 │  │         ▼                                    │    │
 │  │  ┌──────────────┐                            │    │
 │  │  │ Plane Index  │  2 MB SRAM lookup:         │    │
 │  │  │ & Metadata   │  chunk → plane ID,         │    │
 │  │  │              │  DRAM row, codec tag        │    │
 │  │  └──────┬───────┘                            │    │
 │  │         ▼                                    │    │
 │  │  ┌──────────────┐                            │    │
 │  │  │ Codec        │  32 parallel lanes,        │    │
 │  │  │ Complex      │  2 TB/s aggregate,         │    │
 │  │  │ (LZ4/ZSTD)  │  compress + decompress     │    │
 │  │  └──────┬───────┘                            │    │
 │  │         ▼                                    │    │
 │  │  ┌──────────────┐  ┌─────────────────────┐  │    │
 │  │  │ DRAM         │  │  Bit-Plane Layout   │  │    │
 │  │  │ Scheduler    │──│  P^sgn │ P^exp_0..E │  │    │
 │  │  │ (FR-FCFS,    │  │  P^man_0..M         │  │    │
 │  │  │  row-aware)  │  │  (per-value bits    │  │    │
 │  │  └──────────────┘  │   grouped by plane)  │  │    │
 │  │                    └─────────────────────┘  │    │
 │  └──────────────────────────────────────────────┘    │
 └──────────────────────────────────────────────────────┘

 Data flow: Host requests 16 KB at 5-bit precision →
   device fetches only sign + top-5 planes (~5/16 of DRAM reads),
   decompresses, returns 16 KB reconstructed over CXL link.
 Effective bandwidth amplification: up to 2.5-3.2× over raw link.
```

---

## 5. What It Helps — What It Does Not Solve

### Helps

| Aspect | Mechanism |
|--------|-----------|
| **CXL link bandwidth** | Compressed data crosses the link; effective bandwidth multiplied by compression ratio (1.3–1.9×). |
| **DRAM access energy** | Bit-plane selective retrieval reads fewer rows; up to 40.3% energy reduction (S1). |
| **KV cache footprint** | Device-side compression reduces stored KV size by 44.8–46.9% without accuracy loss (S1). |
| **Context length ceiling** | Freed capacity extends max context by 87% (65k → ~122k usable tokens, S1). |
| **Model-load latency** | Compressed weights load faster; up to 42.1% latency reduction (S1). |
| **Cold data capacity** | IBEX-style promotion compresses cold blocks, expanding effective capacity by ~1.59× (S2). |
| **Recall traffic (PNM)** | Processing-near-memory token selection eliminates GPU recall; up to 21.9× throughput gain (S3). |

### Does Not Solve

| Aspect | Reason |
|--------|--------|
| **CXL access latency** | Compression/decompression adds ~25–100 ns codec delay; base CXL round-trip (~640 ns) is unchanged. |
| **Already-quantized models** | When base weights are INT4/FP8, additional bit-plane compression yields only 1.9–2.1% further savings (S1). |
| **Write-heavy workloads** | KV cache writes require buffering (256-token windows) + compression before DRAM commit; write amplification possible. |
| **Host software changes** | Precision-partitioned address regions require page-table setup; transparent but not zero-effort integration. |
| **Inter-device fabric** | Multi-device CXL switch fabric latency and contention are orthogonal to device-internal NDP. |
| **GPU compute bottleneck** | NDP helps bandwidth, not FLOPS; attention-compute-bound regimes see diminishing returns. |

---

## 6. Quantitative Comparison

| Metric | Standard CXL.mem (Passive) | CXL-NDP + Compression (Evolved) | Source |
|--------|---------------------------|----------------------------------|--------|
| Effective link bandwidth multiplier | 1.0× | 1.3–1.9× (codec-dependent) | S1 |
| LLM inference throughput (70B, 65k ctx) | Baseline | +43% | S1 |
| Max context before OOM (70B, 256 GB) | ~105k tokens | ~196k tokens (+87%) | S1 |
| KV cache storage footprint | 100% | 53–55% (44.8–46.9% reduction) | S1 |
| DRAM access energy (30B model) | 100% | 59.7% (−40.3%) | S1 |
| Model-load latency | 100% | 57.9% (−42.1%) | S1 |
| Weight compression ratio (BF16) | 1.0× | 1.34× (ZSTD) | S1 |
| KV compression ratio | 1.0× | 1.81–1.88× (ZSTD, bit-plane) | S1 |
| Cold-block speedup (memory-intensive) | 1.0× | 1.28–1.40× (IBEX) | S2 |
| Effective capacity expansion (cold) | 1.0× | ~1.59× (IBEX) | S2 |
| Codec area (7 nm, 2 GHz) | N/A | 4.83 mm² (LZ4) / 5.69 mm² (ZSTD) | S1 |
| Codec power | N/A | 5.25 W (LZ4) / 7.38 W (ZSTD) | S1 |
| Weight-read latency (16 KB, 5-bit LZ4) | ~300 ns (raw DRAM) | 398 ns (+~100 ns codec overhead) | S1 |

---

## 7. One-Word Verdict

**Compelling.** — Device-side NDP and compression turn the CXL link from a capacity-only extension into a bandwidth-amplifying memory tier, with 40–87% gains on the metrics that matter most for LLM serving, at modest silicon cost.

---

## 8. Open Questions

1. **Codec standardization.** CXL-NDP and IBEX each define proprietary codec pipelines. Will CXL 5.0 or an OCP sub-spec standardize an inline compression interface so devices from different vendors interoperate?

2. **Write-path amplification.** KV cache compression requires buffering (256-token windows in CXL-NDP) before DRAM commit. Under bursty decode patterns, how much SRAM buffering is needed to avoid stalls, and what is the energy cost?

3. **Multi-device coherence.** CXL 4.0 enables multi-rack memory pooling. When NDP controllers compress data independently per device, how do fabric-level consistency and migration protocols handle heterogeneous compression states?

4. **Diminishing returns with quantization.** Bit-plane compression on already-quantized (INT4/FP8) models yields < 3% additional savings. As model quantization becomes the default, does device-side compression remain cost-justified?

5. **Security and side channels.** Compression ratios are data-dependent. Does observable variation in CXL link traffic or latency leak information about model weights or user prompts in multi-tenant deployments?

6. **Integration with structured sparsity.** Sparse MoE and pruned models have irregular access patterns. How well do bit-plane layouts and block-level compression adapt to high-sparsity tensors?

---

## 9. References

1. Y. Kim et al., "Amplifying Effective CXL Memory Bandwidth for LLM Inference via Transparent Near-Data Processing," arXiv:2509.03377, Sep 2025. https://arxiv.org/abs/2509.03377

2. IBEX Authors, "IBEX: Internal Bandwidth-Efficient Compression Architecture for Scalable CXL Memory Expansion," arXiv:2603.26131, accepted to ICS '26. https://arxiv.org/abs/2603.26131

3. PNM-KV Authors, "Scalable Processing-Near-Memory for 1M-Token LLM Inference: CXL-Enabled KV-Cache Management Beyond GPU Limits," arXiv:2511.00321, Nov 2025. https://arxiv.org/abs/2511.00321

4. CXL Consortium, "Compute Express Link 4.0 Specification," Nov 18, 2025. https://www.computeexpresslink.org/

5. ZeroPoint Technologies, "DenseMem CXL — Hardware-Accelerated Inline Memory Compression IP." https://www.zeropoint-tech.com/products/cxl-expansion-dense-memory

6. Synopsys, "CXL 4.0, Bandwidth First: What Designers Are Solving for Next," 2026. https://www.synopsys.com/blogs/chip-design/cxl-4-bandwidth-first-what-designers-are-solving-next.html

7. CXL Consortium Blog, "Overcoming the AI Memory Wall: How CXL Memory Pooling Powers the Next Leap in Scalable AI Computing." https://computeexpresslink.org/blog/overcoming-the-ai-memory-wall-how-cxl-memory-pooling-powers-the-next-leap-in-scalable-ai-computing-4267/

8. X. Wang et al., "Performance Characterization of CXL Memory and Its Use Cases," IPDPS 2025. http://pasalabs.org/papers/2025/IPDPS25_CXL.pdf

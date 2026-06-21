# Agent-Era Memory Workload: A Trend Survey (v2)

> A forward-leaning workload-trend view of what AI agents are doing to end-device memory **now (2024–2026)** and what they will likely do **next (2026–2028)**. This survey distills the [A16 family](../advanced/A16-前沿-Agent时代内存负载.md) plus current-year reporting into one conflict figure, four trend points, a challenges map, four response directions, and a six-bullet opinionated forecast. The forecast takes a side; the open questions list what could prove it wrong.

## 1. Scope and method

**Domain.** "Memory workload" here means the pattern of how data is created, kept resident, accessed, and reclaimed. The reference setting is a 2024–2028 flagship smartphone running a mix of traditional foreground/background apps plus on-device LLM inference, multimodal encoders, agent loops, and retrieval. Cloud inference is mentioned only as a contrast.

**Observation window: 2024–mid-2026.** Apple Intelligence shipped in late 2024 with the 8 GB RAM gate; Gemini Nano landed on Pixel 8 Pro early 2024 and on Pixel 8 / 8a later; LPDDR6 was published as JESD209-6 in July 2025 and first samples landed end of 2025. These two years are the entire on-device-AI-as-default era. Anything earlier is background, not data.

**Projection window: mid-2026 to 2028.** Two-to-three product cycles. Far enough to see LPDDR6 ship in volume, agentic OS frameworks land, and the next round of NPU/Tensor silicon hit users; close enough that the underlying physics (LPDDR per-package density, NAND bandwidth, NPU TOPS scaling) doesn't fundamentally change.

**Sources.** Twelve sources in section 8. Six tagged `[now]` (last 18 months of shipped product and standard), three `[projection]` (roadmaps and forward-looking research), three `[background]` (older PagedAttention-class anchors and prior A15c work). At least three sources contribute hard numbers in figure 1.

**What this survey is not.** Not a product comparison, not a vendor benchmark, not a vendor-neutral hedge. It takes positions.

## 2. The conflict at a glance

![End-device memory demand vs supply (2024–2028)](assets/agent-era-memory-workload-conflict.svg)

*Figure 1. The scissors. X-axis: year, median flagship class. Y-axis: GB. Stacked solid areas show **conservative** workload — traditional apps (blue) plus a single resident on-device model with ≤ 32K context (orange). Solid blue line: flagship LPDDR capacity (12 → 24 GB). Dashed blue line: user-available memory after OS / driver / pinned-system reserve (≈ capacity − 3 to − 6 GB). Dashed red line: **aggressive** demand — traditional apps plus an agentic stack (one assistant + one task model + one perception model, 128K+ context, persistent KV). Shaded red wedge: where aggressive demand exceeds user-available capacity; crossover ≈ 2027. Right-hand grey band marks the projection window (mid-2026 onward). Sources: Apple 2024, Google 2024–2025, Samsung 2025, JEDEC 2025–2026, Micron 2025, SK hynix 2026; see section 8.*

What the figure says, plainly:

1. **The capacity line and the conservative demand stack do not cross.** A single resident on-device model with bounded context fits in 2026 flagships and will fit in 2028 flagships. The hype-free baseline is fine.
2. **The aggressive demand line and the capacity line do cross — around 2027.** Once you run an agentic stack (multiple resident models, 128K+ context, persistent KV), median 16–20 GB flagships run out of *user-available* memory before they run out of *total* LPDDR.
3. **LPDDR6 helps but does not close the gap.** It is on the chart (the 2027–2028 capacity rise to 20–24 GB), and the deficit still opens. Memory technology is growing at ~17%/yr; aggressive AI demand grows at ~45%/yr from 2026.
4. **The choke point is not the LPDDR ceiling — it is the user-available ceiling.** OS, drivers, system services, and pinned device buffers reserve a chunk of LPDDR before apps see anything. As more of that reserved chunk is itself AI (pinned KV in dma-buf), the dashed user-available line *falls faster than the solid capacity line rises*. This is the architectural punchline the figure exists to make visible.

## 3. Trends (4)

- **Growth** — On-device AI memory footprint (weights + KV + activations) roughly tripled in two years (2024 → 2026) and is on track to grow another 4–5× by 2028 if agentic workloads ship by default.
- **Stacking** — End-device AI is shifting from one resident model to several (assistant + speech + vision + task-specific); each adds 1–3 GB of weights, and weights do not share between them today.
- **Persistence** — Agent loops keep AI memory active in the background, so the "foreground hot, background cold" heuristic that classical reclaim relies on no longer matches the actual access pattern.
- **Pinning** — A growing share of total LPDDR sits in device-resident, pinned buffers (KV cache, dma-buf, NPU scratch) outside the normal LRU and reclaim paths.

## 4. Challenges

| Trend | Industry | Technology | System governance | Architecture / form factor |
|---|---|---|---|---|
| **Growth** | BOM cost of pushing flagship RAM beyond 16–24 GB is steep; mid-tier devices fall further behind in capability | Lossless compression (zram-class) does not bend the AI demand curve; KV needs lossy, type-aware compression | OS cannot evict pinned KV; lmkd / jetsam fire too early once AI workloads land | LPDDR6 widens bandwidth but per-package capacity grows slower than AI demand; new media (HBF, MRAM, PIM) becomes necessary |
| **Stacking** | Vendors compete on "AI persona" features that each ship a new resident model, with no incentive to share | Multi-model weight deduplication is unsolved on-device; adapter / LoRA-style sharing is research-only at production scale | Process-isolated AI services keep duplicate weight copies in memory because IPC sharing is hard to secure | NPU shared scratchpads and weight caches need to span multiple model contexts |
| **Persistence** | "Background app" UX assumption breaks; always-on inference hits battery and thermal budgets | Reclaim heuristics tuned for foreground vs background mismatch the agent pattern | Active scanning (DAMON, MGLRU aging) becomes necessary; passive LRU under-protects hot tail | — |
| **Pinning** | Vendors expose AI memory as "AI-reserved" to avoid OOM blame; reduces effective user-available memory | dma-buf and device buffers bypass page cache and LRU; pinned share keeps rising | MGLRU and DAMON do not see device-resident pages; reclaim is blind to half the workload | IOMMU/SVA must extend into a device page-fault path so device-side memory becomes governable |

## 5. Response directions

- **Growth** → **Lossy structured compression**: type-aware KV quantization and eviction (KIVI 2-bit, H2O / StreamingLLM eviction, KV-Compress per-head ratios) so the workload-specific growth axis is attacked with workload-specific tools.
- **Stacking** → **Paged weight loading**: load only the layers / experts / adapters needed for the active task, with a shared base across resident agents, treating model weights the way virtual memory treats code pages.
- **Persistence** → **Programmable proactive reclaim**: combine DAMON-style active region scanning with eBPF policy hooks so reclaim decisions are driven by data class and PSI feedback, not by foreground status.
- **Pinning** → **Unified-memory governance**: extend IOMMU / SVA so device-resident pages join the page-fault and LRU paths and become first-class participants in reclaim, not a separate sealed pool.

## 6. Opinionated forecast (2–5 years)

- **By 2027, the median 16 GB flagship will run out of user-available memory under any default agentic workload that uses ≥ 64K context with a 7B-class model plus one resident assistant.** — *Why:* KV cache scales linearly with context — a 7B model at 64K context is roughly 4–5 GB of KV alone; add ~4 GB Q4 weights, ~1.5 GB assistant, and ~6 GB traditional apps and the stack is already at 15–17 GB before the OS / driver reserve. *Confidence: high.*
- **By 2028, "AI-reserved memory" becomes an explicit OS-level concept on at least two of {Android, HarmonyOS, iOS}.** — *Why:* lmkd / jetsam classes already mis-fire when AI loads land; the fix path is either to make AI pages visible to reclaim (hard) or to declare AI reservations and budget them explicitly (easier). Apple Intelligence already implicitly reserves ~1.5 GB; this will be formalized and exposed. *Confidence: medium.*
- **Lossy KV compression (2-bit quant, top-k / streaming eviction) becomes production-default on Android by 2027.** — *Why:* KV growth is the single biggest demand vector; KIVI- / H2O-class techniques already show acceptable quality on instruction-following and most agent tool-use tasks. Vendors will ship this before they ship larger RAM, because it is cheaper. *Confidence: medium.*
- **LPDDR6 does not close the gap in the projection window.** — *Why:* per-package capacity grows ~25–30% vs LPDDR5X by 2027 (Micron 16 Gb sampling end-2025, SK hynix 1c-class in H2 2026), but aggressive AI demand grows ~3× over the same window. Bandwidth doubles to ~14.4 GT/s; capacity does not. *Confidence: high.*
- **At least one major Android OEM ships a user-visible "memory tier" feature backed by HBF-class flash and paged KV offload by 2028.** — *Why:* once the deficit on figure 1 becomes a shipped-product OOM rate that PR teams cannot ignore, vendors will fall back to the only remaining headroom — flash — and rename it. The marketing label is invented; the underlying mechanism is paged KV offload of the [A16f / A16i](../advanced/A16f-端侧KV-Cache管理方案.md) flavor. *Confidence: low.*
- **On-device LLM capability is memory-bound, not compute-bound, throughout 2026–2028.** — *Why:* NPU TOPS keeps doubling at roughly Moore-class rates (Apple Neural Engine, Tensor G5+, MediaTek APU); LPDDR capacity is on a slower curve. Every quality-vs-cost frontier on-device is already a memory question (Q4 vs Q8, context trimming, KV offload). *Confidence: high.*

## 7. Open questions and caveats

- **Aggressive scenario depends on adoption.** If end-side context tops out at 8K–32K instead of 64K+, the dashed red line in figure 1 stays close to the orange stack and the deficit never opens. The forecast's first bullet hinges on default agentic context-length policy.
- **Lossy KV compression has open quality risks.** Precision drift over long agent traces, degraded reasoning on small models, and tool-call failure under 2-bit quantization are not fully characterised. The "Growth" response holds in direction; not yet as a settled recipe.
- **IOMMU-mediated unified memory with device page faults is academic on Android / iOS today.** The "Pinning" response is a design direction, not a shipped feature. Vendor SVA support is partial and silicon-dependent.
- **HBF capacity, latency, and shipping timelines are vendor-stated and not yet field-validated.** Treat 2027-and-after HBF numbers as projections with non-trivial error bars.
- **The "median flagship" frame hides mid-tier devices entirely.** A 2026 mid-tier with 8 GB hits the deficit two years earlier and harder. If the question is fleet-wide rather than flagship-wide, the timeline compresses by ~12–18 months.
- **Multi-tenant agent workloads (several agents resident concurrently) are not yet captured by any public dataset.** The "Stacking" trend is grounded in product roadmaps and qualitative behavior, not measured residency distributions.

## 8. References

1. Apple (2024). *Introducing Apple Intelligence for iPhone, iPad, and Mac*. [https://www.apple.com/newsroom/2024/06/introducing-apple-intelligence-for-iphone-ipad-and-mac/](https://www.apple.com/newsroom/2024/06/introducing-apple-intelligence-for-iphone-ipad-and-mac/) — 8 GB RAM minimum gate; ~1.5 GB on-device LLM reserve. `[now]`
2. Dataconomy (2024). *Apple Clarifies How Much RAM Does Your iPhone Need To Run Apple Intelligence*. [https://dataconomy.com/2024/09/16/apple-clarifies-how-much-ram-does-your-iphone-need-to-run-apple-intelligence/](https://dataconomy.com/2024/09/16/apple-clarifies-how-much-ram-does-your-iphone-need-to-run-apple-intelligence/) — Srouji statement on RAM gate. `[now]`
3. Google Developers Blog (2024). *Blazing fast on-device GenAI with LiteRT-LM*. [https://developers.googleblog.com/blazing-fast-on-device-genai-with-litert-lm/](https://developers.googleblog.com/blazing-fast-on-device-genai-with-litert-lm/) — Gemini Nano / Gemma 4 on-device, ~0.8 GB weights + ~1.12 GB embeddings. `[now]`
4. Samsung Semiconductor (2025). *Galaxy S26 Ultra spec brief and 24 GB LPDDR5X package*. [https://semiconductor.samsung.com/news-events/news/](https://semiconductor.samsung.com/news-events/news/) — 24 GB flagship RAM SKU. `[now]`
5. JEDEC (2025). *JEDEC Releases New LPDDR6 Standard to Enhance Mobile and AI Memory Performance*. [https://www.jedec.org/news/pressreleases/jedec%C2%AE-releases-new-lpddr6-standard-enhance-mobile-and-ai-memory-performance](https://www.jedec.org/news/pressreleases/jedec%C2%AE-releases-new-lpddr6-standard-enhance-mobile-and-ai-memory-performance) — JESD209-6 published July 2025, 10.7–14.4 GT/s. `[now]`
6. JEDEC (2026). *JEDEC Previews LPDDR6 Roadmap Expanding LPDDR into Data Centers and Processing-in-Memory*. [https://www.jedec.org/news/pressreleases/jedec%C2%AE-previews-lpddr6-roadmap-expanding-lpddr-data-centers-and-processing-memory](https://www.jedec.org/news/pressreleases/jedec%C2%AE-previews-lpddr6-roadmap-expanding-lpddr-data-centers-and-processing-memory) — narrower x6 sub-channel; path to 512 GB per stack class. `[projection]`
7. Heisener (2026). *JEDEC Releases LPDDR6 Roadmap*. [https://www.heisener.com/IndustryTrend/JEDEC-Releases-LPDDR6-Roadmap](https://www.heisener.com/IndustryTrend/JEDEC-Releases-LPDDR6-Roadmap) — Micron 16 Gb LPDDR6 sample Dec 2025; SK hynix 1c LPDDR6 H2 2026 shipments. `[projection]`
8. Belcak, P. & Heinrich, G. (NVIDIA, 2025). *Small Language Models are the Future of Agentic AI*. arXiv:2506.02153. [https://arxiv.org/abs/2506.02153](https://arxiv.org/abs/2506.02153) — Position paper on edge-resident SLMs displacing cloud LLMs for agentic tasks. `[projection]`
9. KVSWAP (2025). *KVSwap: Disk-aware KV Cache Offloading for Long-Context On-device Inference*. arXiv:2511.11907. [https://arxiv.org/abs/2511.11907](https://arxiv.org/abs/2511.11907) — On-device KV offload bandwidth-wall analysis. `[now]`
10. Octomil (2025). *On-Device LLM Inference: The Definitive 2025–2026 Guide*. [https://docs.octomil.com/blog/on-device-llm-inference-2025-2026/](https://docs.octomil.com/blog/on-device-llm-inference-2025-2026/) — Paged KV on mobile, GQA-driven 4× KV reduction. `[now]`
11. Kwon, W. et al. (2023). *Efficient Memory Management for Large Language Model Serving with PagedAttention*. SOSP 2023, arXiv:2309.06180. [https://arxiv.org/abs/2309.06180](https://arxiv.org/abs/2309.06180) — Paged KV cache; cited by A16f. `[background]`
12. A16 family (this project). [Agent-Era Memory Workload total](../advanced/A16-前沿-Agent时代内存负载.md), and sub-articles [A16a](../advanced/A16a-LRU主动扫描.md), [A16b](../advanced/A16b-eBPF可编程回收策略-Android.md), [A16c](../advanced/A16c-异构压缩CDSD.md), [A16d](../advanced/A16d-压缩IP边际建模.md), [A16e](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md), [A16f](../advanced/A16f-端侧KV-Cache管理方案.md), [A16g](../advanced/A16g-DRAM-PIM异构协同管理.md), [A16h](../advanced/A16h-STT-SOT-MRAM多级缓存方案.md), [A16i](../advanced/A16i-端侧UFS-HBF增强.md) — primary in-project anchor for every trend, challenge, response, and forecast. `[background]`

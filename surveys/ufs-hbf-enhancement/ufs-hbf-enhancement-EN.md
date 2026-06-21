# High-Bandwidth Flash on Mobile: From "Slow Swap Backstop" to a Real Memory Tier

> A before-and-after survey of how the mobile UFS flash sits in the memory hierarchy. Anchor article: [A16i — 端侧 UFS-HBF 增强](../../advanced/A16i-端侧UFS-HBF增强.md). The original role of mobile UFS is "non-volatile fallback, kept far from the hot path because flash is too slow and lives on a wear budget." The evolved role splits two ways: (a) **UFS 5.0** (JEDEC, 2025-10-06) scales the standard interface to **~10.8 GB/s** with M-PHY 6.0 — already on the roadmap; (b) **HBF (High Bandwidth Flash)** — the SanDisk + SK Hynix 2025 proposal, **256 GB/die, 512 GB/stack, 1.6 TB/s read**, **8–16× HBM capacity at comparable cost** — gives the data-center pattern. Whether HBF's design ideas (stacked NAND near the SoC, near-storage compute, pSLC zones) can be ported down to a mobile UFS-HBF is the open speculation; **no product exists, samples for the data-center version arrive 2H 2026**.

## 1. Scope and method

**Domain.** "High-bandwidth flash on mobile" here means treating mobile UFS as a memory-backing store for LLM weights and KV cache, and the candidate hardware evolutions that would close the LPDDR-UFS bandwidth gap. The scope includes (a) the *real* near-term roadmap (UFS 4.0 → 4.1 → 5.0) and (b) the *speculative* port of HBF's stacking pattern down to mobile.

**Original solution.** Mobile UFS 4.0/4.1 as the only non-volatile tier — sequential read ~**4 GB/s**, 4 KB random read **0.45–1 GB/s** on a real flagship (PowerInfer-2 on OnePlus 12), queue depth 32. The OS treats it as a far backstop; Android specifically does not enable disk swap by default because flash wear and bandwidth both push toward "don't touch it."

**Evolved solution, two tracks.** **(Track A — shipping roadmap)** UFS 5.0: M-PHY 6.0 HS-G6 at 46.6 Gb/s/lane over 2 lanes, target **up to 10.8 GB/s** sequential, AI workloads called out by JEDEC as the motivating driver. **(Track B — speculative, data-center reality)** HBF: HBM-style stacked NAND with TSV through an interposer, **256 GB/die, 512 GB per 16-high stack, 1.6 TB/s read** in Gen-1; Gen-2 >2 TB/s and Gen-3 3.2 TB/s on the roadmap; SanDisk + SK Hynix MOU, OCP standardization in progress, samples **2H 2026**, first inference devices **early 2027**. Mobile UFS-HBF — applying any of these ideas (wider interface, deeper queue, stacking, pSLC durability zones, near-storage compute) to a phone-class part — has **no product** and is design exploration only.

**Sources.** 13 sources: KIOXIA UFS 4.0/4.1 product pages and the "Top 5 Reasons" doc with concrete numbers, JEDEC press releases for UFS 4.1 (Jan 2025) and UFS 5.0 (Oct 2025), MNN-LLM (arXiv 2506.10443) and PowerInfer-2 (arXiv 2406.06282) with measured device numbers, the KVSwap paper (arXiv 2511.11907), HiFC (NeurIPS 2025 poster), SanDisk's own newsroom post on HBF, two Tom's Hardware feature articles on HBF specs and positioning, TrendForce's HBF timeline article, EE Times "NAND Reimagined" with the Gen-1 / Gen-2 / Gen-3 roadmap, the Samsung Semiconductor UFS 4.0 first-mover blog, and the Wikipedia UFS overview for the cross-version table.

## 2. Problem background

**What the system needs to do.** Run on-device LLM inference on a phone whose DRAM (~12–24 GB LPDDR5X) is smaller than the model — and possibly smaller than just the KV cache at long context. The inference engine streams weights and KV from flash on demand, while a normal app stack keeps running. Latency to first token, decode rate, and battery cost all matter.

**Why this domain becomes hard.** Three constraints collide: (1) the **DRAM-flash bandwidth gap is enormous** — LPDDR5X ≈ 58 GB/s, UFS 4.0 ≈ 0.45–3 GB/s, gap of **19–130×** ([MNN-LLM, arXiv 2506.10443](https://arxiv.org/abs/2506.10443)); (2) the **flash wear budget caps write frequency** — KV offload to flash needs careful wear management or it shortens the phone's lifetime ([HiFC](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) uses pSLC zones for ~**8×** write endurance); (3) **mobile UFS queue depth is shallow** (~32) — so random access patterns of the kind LLM inference produces are IOPS-limited even when bandwidth isn't saturated.

**Why the original solution is no longer enough.** On-device LLMs that don't fit in DRAM cannot stream weights from flash at LPDDR-class bandwidth. PowerInfer-2 on a OnePlus 12 (UFS 4.0) gets **11.68 tok/s** on a TurboSparse-Mixtral-47B, with the flash side doing roughly **4 GB/s** sequential — that performance is hard-won and only works because the engine masks flash reads behind compute via aggressive activation prediction. The next step (longer context, more KV from flash, multiple models resident) needs either bandwidth or a different flash topology entirely. UFS 5.0 answers the former, HBF the latter.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **DRAM-flash bandwidth gap.** ~19–130× difference depending on access pattern — measured in [MNN-LLM](https://arxiv.org/abs/2506.10443).
2. **Random-access penalty within UFS.** On the OnePlus 12 (UFS 4.0), sequential is ~**4 GB/s** but 4 KB random is **0.45–1 GB/s** — so unfortunate access patterns lose another **4–10×** ([PowerInfer-2](https://arxiv.org/abs/2406.06282)).
3. **Queue depth caps concurrency.** UFS lanes are deep enough for raw bandwidth, but the queue is shallow (~32) — concurrent random reads from multiple inference streams compete badly.
4. **Wear budget.** Frequent KV offload writes degrade the same flash that holds the rest of the system. HiFC uses pSLC zones to multiply write endurance ~**8×** at a capacity cost.

### Bottleneck evidence

| Signal | Value | What it means | Source |
|---|---|---|---|
| LPDDR5X mobile bandwidth | ~**58 GB/s** | The reference DRAM tier. | [MNN-LLM](https://arxiv.org/abs/2506.10443) |
| UFS 4.0 sequential read (per-lane) | ~**2.9–4 GB/s** | The best the current generation gives. | [KIOXIA UFS 4.0/4.1](https://europe.kioxia.com/en-europe/business/memory/mlc-nand/ufs4.html); [Samsung UFS 4.0 announcement](https://semiconductor.samsung.com/news-events/tech-blog/samsung-develops-first-ufs-4-0-storage-solution-compliant-with-new-industry-standard/) |
| UFS 4.0 4 KB random read | **0.45–1 GB/s** | The pattern LLM inference often hits. | [PowerInfer-2](https://arxiv.org/abs/2406.06282), OnePlus 12 measurement |
| DRAM-vs-UFS bandwidth gap | **19–130×** | Across access patterns; the central reason flash can't yet be a memory tier on its own. | [MNN-LLM](https://arxiv.org/abs/2506.10443) |
| UFS queue depth | **32** | Shallow vs PCIe NVMe class (64K+); caps random-IOPS concurrency. | A16i §3.1; widely cited |
| PowerInfer-2 decode rate on TurboSparse-Mixtral-47B (OnePlus 12 with UFS 4.0) | **11.68 tok/s**; avg cache miss **3.5%**, p99 **18.9%** | The current state of the art for software-only workaround, bumping into the bandwidth wall. | [PowerInfer-2](https://arxiv.org/abs/2406.06282) |
| UFS 4.0 lane interface | **23.2 Gbps/lane** (46.4 Gbps/device) | Spec ceiling for the current generation. | JEDEC; KIOXIA |
| UFS 5.0 target (JEDEC Oct 2025) | up to **10.8 GB/s** sequential; M-PHY 6.0 HS-G6 at **46.6 Gb/s/lane**; AI explicitly cited as driver | The shipping roadmap response — ~2.7× the UFS 4.0 sequential ceiling. | [JEDEC UFS 5.0 press release](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage) |
| HBF Gen-1 (data center) | **256 GB/die, 512 GB/16-high stack, 1.6 TB/s read** | Data-center comparator: stacked NAND can be **>500× faster** than UFS 4.0 sequential. | [EE Times, "NAND Reimagined"](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/); [Tom's Hardware HBF](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers) |
| HBF capacity vs HBM, at comparable cost | **8–16×** | Capacity multiplier at similar price; not a cost reduction. | [Tom's Hardware HBF capacity](https://www.tomshardware.com/tech-industry/sandisk-and-sk-hynix-join-forces-to-standardize-high-bandwidth-flash-memory-a-nand-based-alternative-to-hbm-for-ai-gpus-move-could-enable-8-16x-higher-capacity-compared-to-dram) |
| HBF first samples → first inference devices | **2H 2026 → early 2027** | Timeline for the data-center version. Mobile port: none. | [TrendForce](https://www.trendforce.com/news/2025/08/07/news-memory-giants-sandisk-sk-hynix-unite-for-hbf-standard-with-samples-expected-in-2h26/) |
| HiFC pSLC write endurance multiplier | **~8×** | A wear-management lever for frequent KV writes; capacity cost. | [HiFC NeurIPS 2025](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) |

**Reading.** Three numbers carry the argument. **58 GB/s vs 0.45–3 GB/s** is the bottleneck. **10.8 GB/s** is the UFS 5.0 answer — material but still ~6× below LPDDR. **1.6 TB/s** is the HBF answer — well above LPDDR, but at data-center cost, power, and footprint that don't fit a phone today. Whether a mobile-class port of HBF's *ideas* (stacking, deeper queue, near-storage compute, pSLC durability zones) lands a useful in-between is the open design question.

## 4. Architectures: original vs evolved

Both diagrams use the same components. Differences are marked with `*`.

**Original — UFS 4.x as a far backstop**

```
   +---------+     ~58 GB/s          +-----------+
   |   SoC   | --------------------> |  LPDDR5X  |
   | (CPU/   |                       +-----------+
   |  NPU    |
   |  infer) |
   +----+----+
        |
        | UFS 1-2 lanes (4 GB/s seq,
        | 0.45-1 GB/s 4K random,
        | queue depth 32)
        |
        v
   +-----------+
   | UFS 4.x   |   non-volatile, far,
   | NAND      |   wear-budgeted
   +-----------+

   When weights/KV don't fit DRAM:
   read storm pulls from flash 19-130x
   slower than DRAM -> stalls
```

*Original: UFS is the only non-volatile tier and is treated as a far backstop. When weights or KV don't fit DRAM, the inference engine stalls behind flash reads; software workarounds (activation prediction) only partially hide the gap.*

**Evolved — UFS 5.0 today, HBF-style mobile flash speculative**

```
   +---------+     ~58 GB/s          +-----------+
   |   SoC   | --------------------> |  LPDDR5X  |
   +----+----+                       +-----------+
        |
        | * Track A (roadmap, JEDEC 2025-10):
        |   UFS 5.0 -- M-PHY 6.0 HS-G6,
        |   46.6 Gb/s/lane x 2 = up to 10.8 GB/s
        |   * AI explicitly cited as driver
        |   * host-initiated defrag
        v
   +-----------+
   | UFS 5.0   |   non-volatile, closer
   +-----------+
        |
        | * Track B (data-center reality / mobile speculation):
        |   HBF-style stacking
        |   * 256 GB/die, 512 GB/stack, 1.6 TB/s (DC Gen-1)
        |   * near-storage compute
        |   * pSLC zone for KV writes (~8x endurance)
        |   * mobile port: no product
        v
   +--------------+
   | UFS-HBF      |   * stacked NAND
   | (proposed,   |   * near-storage compute
   |  no product) |
   +--------------+
```

*Evolved: Track A (UFS 5.0) is on JEDEC's roadmap and brings flash to ~10.8 GB/s, narrowing the LPDDR gap to ~6×. Track B (HBF) is shipping in the data center 2026–2027 and shows what a stacked-NAND topology can do; whether any of it ports to a phone is the open question — no product exists.*

## 5. Why evolved helps, what it still doesn't solve

### Why the evolved solution helps

- **DRAM-flash bandwidth gap** — UFS 5.0 narrows it from 19–130× down to ~6× at sequential read. HBF in the data center narrows it to inverted (HBF Gen-1 1.6 TB/s vs HBM4 class). For mobile, even a fraction of the HBF idea — wider interface, denser stacking — would close enough of the gap to make on-device streaming inference more practical.
- **Random-access penalty** — UFS 5.0's host-initiated defragmentation ([JEDEC UFS 4.1 release](https://www.jedec.org/news/pressreleases/jedec%C2%AE-announces-updates-universal-flash-storage-ufs-and-memory-interface)) and deeper queues would push more random into sequential-equivalent patterns. HiFC and KVSwap on the software side already do this for KV cache; near-storage compute (filter + decompress at the flash) would let the SoC issue larger, friendlier requests.
- **Queue depth** — UFS 5.0's roadmap explicitly cites AI workloads as a driver, which implies deeper queues; the data-center HBF stack has wide parallelism by design (TSV-connected dies, all-bank parallel reads).
- **Wear budget** — HiFC's pSLC-zone trick multiplies write endurance ~8× ([HiFC NeurIPS 2025](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf)). It's a software/firmware lever, not a UFS spec — but it's the most concrete write-side answer to "KV offload destroys flash."

### What it still doesn't solve

- **HBF doesn't fit a phone today.** HBM-class packaging (TSVs, interposer, stack height matching HBM4 footprint) brings data-center power, cost, and thermal density. None of those numbers translate cleanly to a phone. "Mobile UFS-HBF" — the anchor article's framing — is design exploration; no vendor has announced one.
- **UFS 5.0 still doesn't catch LPDDR.** 10.8 GB/s vs ~58 GB/s is ~6× behind, and that's the spec ceiling, not realistic sustained random read.
- **HBF writes are slow.** Tom's Hardware notes HBF is explicitly inference-only because writes are slow — which lines up with NAND physics and rules out HBF as a memory-rewrite tier. KV offload writes don't disappear with HBF; they need pSLC or equivalent.
- **The "comparable cost" claim is at comparable cost, not lower.** HBF gives 8–16× capacity at comparable cost — useful for capacity-bound data-center inference, but at the same $/system as HBM. No source quotes an actual $/GB number.
- **Pinned-flash share on real mobile is unmeasured.** AOSP documents how to measure UFS / dma-buf accounting but no public dataset reports the fraction of UFS bandwidth or flash wear consumed by on-device LLM inference on a flagship Android phone under realistic workloads.
- **UFS 5.0 timeline.** JEDEC announced the standard 2025-10-06; first silicon and devices weren't named in the press release. Treat 10.8 GB/s as a future target on the roadmap, not a today-buyable number.

## 6. Comparison table

Every cell is a number, a boolean, or `n/a (reason)`. Every row has a source. Honest tradeoffs are flagged: write bandwidth doesn't improve with HBF, and mobile UFS-HBF has no product.

| Dimension | Original: UFS 4.0/4.1 | Evolved Track A: UFS 5.0 | Evolved Track B: HBF (data center) | Improvement | Source |
|---|---|---|---|---|---|
| Sequential read bandwidth | **~4 GB/s** | **up to 10.8 GB/s** | **~1.6 TB/s** (Gen-1) | A: **+2.7×**; B: **+400×** | [KIOXIA](https://europe.kioxia.com/en-europe/business/memory/mlc-nand/ufs4.html); [JEDEC UFS 5.0](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage); [Tom's Hardware](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers) |
| Interface bandwidth per lane | **23.2 Gbps** | **46.6 Gbps** (HS-G6) | n/a (uses interposer / TSV, not lanes) | A: **+2×** | JEDEC UFS 4.1; JEDEC UFS 5.0 |
| 4 KB random read | **0.45–1 GB/s** | not yet published; benefits from defrag and deeper queues | n/a (single-die NAND physics still applies) | A: directional improvement; B: n/a (sequential-class only) | [PowerInfer-2](https://arxiv.org/abs/2406.06282) |
| Capacity per chip | ~512 GB QLC at UFS 4.0 class | not yet specified | **256 GB/die, 512 GB per 16-high stack** | A: roughly unchanged; B: **+~1×** per die, **~16×** per package | [KIOXIA UFS 4.0/4.1 Top 5 Reasons doc]; [EE Times "NAND Reimagined"](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/) |
| Write endurance | baseline (TLC/QLC NAND) | baseline | baseline (HBF write explicitly slow, inference-only) | no change; HiFC pSLC zone yields **~8×** at capacity cost | [HiFC NeurIPS 2025](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) |
| LPDDR-vs-flash bandwidth gap | **19–130×** (UFS 4.0 vs LPDDR5X) | **~6×** sequential (10.8 vs 58 GB/s) | **inverted** (HBF >> HBM4 capacity) | A: gap shrinks ~3–20×; B: data-center only | [MNN-LLM](https://arxiv.org/abs/2506.10443); JEDEC UFS 5.0; [EE Times](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/) |
| Best on-device LLM decode rate (current real phone) | **11.68 tok/s** on TurboSparse-Mixtral-47B (OnePlus 12) | not yet measured (no UFS 5.0 phone) | n/a (data-center only) | A/B: TBD | [PowerInfer-2](https://arxiv.org/abs/2406.06282) |
| Standard publication / shipping status | UFS 4.0 (2022), UFS 4.1 (JESD220G, Jan 2025) | UFS 5.0 announced **2025-10-06**; first silicon TBA | HBF samples **2H 2026**, first inference devices **early 2027** | A: announced; B: data-center timeline | JEDEC press releases; [TrendForce](https://www.trendforce.com/news/2025/08/07/news-memory-giants-sandisk-sk-hynix-unite-for-hbf-standard-with-samples-expected-in-2h26/) |
| Mobile UFS-HBF product availability | yes (classic UFS) | not yet (UFS 5.0 phone TBA) | **no product** for mobile | **0** (mobile port doesn't exist) | A16i §5 |

## 7. One-word characterization

**High-bandwidth** (高带宽) — the defining change is that flash bandwidth scales from the **~2.9–4 GB/s** UFS 4.0 ceiling toward **~10.8 GB/s** on the UFS 5.0 roadmap (JEDEC 2025-10-06) and **~1.6 TB/s** in HBF Gen-1 in the data center ([Tom's Hardware](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers)) — so flash can host on-device LLM weights and KV cache as a real memory tier rather than a far backstop. The LPDDR-flash gap on phones shrinks from **19–130×** to ~**6×** with UFS 5.0; the honest regressions are that **HBF writes are still slow** (inference-only by design) and the **mobile UFS-HBF port doesn't exist** — data-center HBF samples arrive only **2H 2026**.

## 8. Open questions and caveats

- **Mobile UFS-HBF is speculative.** No vendor has announced a phone-class HBF or HBF-inspired UFS variant. The anchor article's §3.4 "borrow the ideas" framing is design exploration, not a roadmap.
- **HBF's $/GB is not published.** Every source says "comparable cost" / "similar price," none quotes a $/GB. The 8–16× capacity multiplier is *at comparable cost*, not a cost reduction.
- **HBF write speed and endurance are not published.** Tom's Hardware notes writes are slow (hence inference-only target); no numeric write bandwidth or P/E cycle figure for HBF Gen-1.
- **UFS 5.0 silicon and devices are not yet named.** JEDEC announced the standard 2025-10-06; the 10.8 GB/s figure is a spec target, not a measured device today. Anchor any "UFS 5.0 will get us X" claim to the JEDEC press release, not a shipped product.
- **UFS queue depth = 32 is widely cited but not directly verified at the spec text level** in the public sources reachable here. Treat as plausible standard-practice limit pending JEDEC text review.
- **Pinned-flash and bandwidth share on real Android phones is unmeasured.** AOSP and Perfetto document the measurement workflow (`iostat`, `/sys/block/sd*/queue/`, UFS health descriptor); no public dataset reports the share under realistic on-device LLM workloads. In-house measurement remains the strongest evidence for or against the bottleneck framing here.
- **HBF's specific stacking advantage may not survive a phone's thermal envelope.** TSV interposers and HBM-style stacks fit a data-center package; the same packaging in a phone is constrained by board thickness, cooling, and battery competition. None of the bandwidth numbers above transfer mechanically.

## 9. References

1. KIOXIA Europe. (2024–2025). *UFS 4.0/4.1 — Designed for Next Generation Mobile Storage*. [europe.kioxia.com/.../ufs4.html](https://europe.kioxia.com/en-europe/business/memory/mlc-nand/ufs4.html) — **23.2 Gbps/lane**, **46.4 Gbps/device**.
2. KIOXIA Americas. (2024). *Top 5 Reasons to Move to UFS 4.0 / 4.1 Embedded Flash Memory from UFS 3.1* (PDF). [americas.kioxia.com/.../KIOXIA_Move_to_UFS4_4-1_Top_5_Reasons.pdf](https://americas.kioxia.com/content/dam/kioxia/en-us/business/memory/mlc-nand/asset/KIOXIA_Move_to_UFS4_4-1_Top_5_Reasons.pdf) — 512 GB QLC UFS 4.0 ~**4,200 MB/s** read, **~3,200 MB/s** write.
3. JEDEC. (2025-01-08). *JEDEC Announces Updates to Universal Flash Storage (UFS) and Memory Interface Standards (UFS 4.1)*. [jedec.org/.../jedec-announces-updates-universal-flash-storage-...](https://www.jedec.org/news/pressreleases/jedec%C2%AE-announces-updates-universal-flash-storage-ufs-and-memory-interface) — UFS 4.1 = JESD220G; M-PHY v5.0 + UniPro v2.0; host-initiated defrag.
4. JEDEC. (2025-10-06). *UFS 5.0 Is Coming: JEDEC Sets the Stage for the Next Leap in Flash Storage*. [jedec.org/.../ufs-50-coming-jedec-sets-stage-next-leap-flash-storage](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage) — target **up to 10.8 GB/s**; M-PHY 6.0 HS-G6 at **46.6 Gb/s/lane × 2 lanes**; AI cited as driver.
5. Wang et al. (Alibaba). (2025). *MNN-LLM: A Generic Inference Engine for Fast Large Language Model Deployment on Mobile Devices*. arXiv:2506.10443. [arxiv.org/abs/2506.10443](https://arxiv.org/abs/2506.10443) — LPDDR5X ~**58 GB/s** vs UFS 4.0 ~**0.45–3 GB/s** → **19–130×** gap.
6. Xue, Z., Song, T., et al. (SJTU IPADS). (2024). *PowerInfer-2: Fast Large Language Model Inference on a Smartphone*. arXiv:2406.06282. [arxiv.org/abs/2406.06282](https://arxiv.org/abs/2406.06282) — OnePlus 12 UFS 4.0 ~**4 GB/s** seq, **0.45–1 GB/s** 4 KB random; **11.68 tok/s** on TurboSparse-Mixtral-47B; **3.5% / 18.9% (avg / p99)** cache miss.
7. *KVSwap: Disk-aware KV Cache Offloading for Long-Context On-device Inference*. (2025). arXiv:2511.11907. [arxiv.org/pdf/2511.11907](https://arxiv.org/pdf/2511.11907) — disk-based KV offload framework for resource-constrained mobile/embedded devices.
8. *HiFC: High-efficiency Flash-based KV Cache Swapping for Scaling LLM Inference*. (NeurIPS 2025 poster). [openreview.net/pdf?id=onhjdWCxZY](https://openreview.net/pdf/54ad85c547f1d3f857eaf95351118ce21c8de1d6.pdf) — DRAM-free architecture with pSLC + GPU Direct Storage; comparable TPS to DRAM; **~8×** write endurance; **4.5×** TCO reduction over 3 years.
9. SanDisk newsroom. (2025-08-06). *Sandisk to Collaborate with SK hynix to Drive Standardization of High-Bandwidth Flash Memory*. [sandisk.com/.../2025-08-06-sandisk-to-collaborate-with-sk-hynix-...](https://www.sandisk.com/company/newsroom/press-releases/2025/2025-08-06-sandisk-to-collaborate-with-sk-hynix-to-drive-standardization-of-high-bandwidth-flash-memory-technology) — MOU; HBF won FMS 2025 "Best of Show, Most Innovative Technology."
10. Shilov, A. (Tom's Hardware). (2025). *SK hynix and SanDisk announce new High Bandwidth Flash — speedy HBF standard targeted at inference AI servers*. [tomshardware.com/.../sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-...](https://www.tomshardware.com/pc-components/ssds/sk-hynix-and-sandisk-announce-new-high-bandwidth-flash-speedy-hbf-standard-is-targeted-at-inference-ai-servers) — inference-only because writes are slow; matches HBM4 footprint/power/stack height.
11. Tom's Hardware. (2025). *Sandisk and SK hynix join forces to standardize HBF — 8-16× higher capacity vs DRAM*. [tomshardware.com/.../sandisk-and-sk-hynix-join-forces-...-8-16x-higher-capacity-...](https://www.tomshardware.com/tech-industry/sandisk-and-sk-hynix-join-forces-to-standardize-high-bandwidth-flash-memory-a-nand-based-alternative-to-hbm-for-ai-gpus-move-could-enable-8-16x-higher-capacity-compared-to-dram) — **8–16×** capacity vs HBM at comparable cost.
12. TrendForce. (2025-08-07). *Memory Giants SanDisk, SK hynix Unite for HBF Standard, with Samples Expected in 2H26*. [trendforce.com/.../memory-giants-sandisk-sk-hynix-...-samples-expected-in-2h26/](https://www.trendforce.com/news/2025/08/07/news-memory-giants-sandisk-sk-hynix-unite-for-hbf-standard-with-samples-expected-in-2h26/) — first HBF samples **2H 2026**; first inference devices **early 2027**.
13. EE Times. (2025). *NAND Reimagined in High-Bandwidth Flash to Complement HBM*. [eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/](https://www.eetimes.com/nand-reimagined-in-high-bandwidth-flash-to-complement-hbm/) — Gen-1 **256 GB/die, 512 GB/16-high stack, 1.6 TB/s read**; Gen-2 **>2 TB/s**, Gen-3 **3.2 TB/s**; stack capacities **1 TB / 1.5 TB**.
14. Samsung Semiconductor. (2022). *Samsung Develops First UFS 4.0 Storage Solution*. [semiconductor.samsung.com/.../samsung-develops-first-ufs-4-0-...](https://semiconductor.samsung.com/news-events/tech-blog/samsung-develops-first-ufs-4-0-storage-solution-compliant-with-new-industry-standard/) — UFS 4.0 ~**4,200 MB/s** read, ~**2,800 MB/s** write; power efficiency ~**46%** better than UFS 3.1.
15. A16i anchor article (this project). [advanced/A16i-端侧UFS-HBF增强.md](../../advanced/A16i-端侧UFS-HBF增强.md).

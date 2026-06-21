# Non-Volatile Cache with STT/SOT-MRAM: From SRAM-Only Hierarchy to Hybrid Persistent LLC

> A before-and-after survey of where non-volatility could sit in the memory hierarchy. Anchor article: [A16h — STT/SOT-MRAM 多级缓存方案](../../advanced/A16h-STT-SOT-MRAM多级缓存方案.md). The original hierarchy uses volatile, leaky SRAM all the way down to DRAM, which itself needs constant refresh. The evolved hierarchy proposes inserting an MRAM layer — non-volatile, no static leakage, denser than SRAM — between SRAM caches and DRAM. STT-MRAM is already shipping for eFlash replacement (TSMC 22 nm, Samsung 14 nm, GlobalFoundries 22FDX); SOT-MRAM in research achieves **>10¹⁵ endurance**, **<100 fJ/bit** switching energy, and **300 ps** switching (imec, IEDM 2023). The mobile-SoC LLC / on-device AI weight-store use case is **not shipping** — it's a design exploration tied to the system-level claim that hybrid hierarchies cut idle energy by ~**80%** (directional, not independently measured).

## 1. Scope and method

**Domain.** "MRAM multi-level cache" here means inserting a non-volatile, low-leakage MRAM layer between volatile SRAM caches and DRAM — for example as a last-level cache (LLC) or as a persistent on-die buffer for AI weights. This is *not* about replacing SRAM at L1/L2 (MRAM is too slow and too large per cell) and *not* about replacing flash (MRAM is too small and too expensive).

**Original solution.** SRAM-only cache hierarchy: L1/L2/L3 all SRAM (volatile, increasing static leakage at advanced nodes, scaling stopped at N3/N5); DRAM below (volatile, constant refresh power). Everything above flash loses state at power-off.

**Evolved solution.** Hybrid: SRAM kept at L1/L2 for raw speed; MRAM (STT or SOT) inserted at LLC or as a persistent weight buffer. Non-volatile (data survives power-off), no standby leakage (zero when idle), denser than SRAM at the same node, latency between SRAM and DRAM. Already shipping as **eFlash replacement** in MCUs/IoT/automotive; mobile-SoC LLC use is a research target.

**Sources.** 12 sources: TSMC research pages (22 nm and 16 nm STT-MRAM), ISSCC 2023 paper on TSMC 16 nm 32 Mb eMRAM, ITRI + TSMC IEDM 2023 SOT-MRAM, imec IEDM 2023 scaled SOT-MRAM, GlobalFoundries 22FDX eMRAM production announcement, Samsung 14 nm eMRAM specs, PMC 2024 industry review, EDN 2024 SOT-MRAM status, Promwad's hybrid-hierarchy blog (idle-energy claim, flagged as directional), Memphis/Wevolver edge-AI memory page, the SOT roadmap (arXiv 2104.11459), and the SemiWiki/IEDM 2022 "death of SRAM scaling" framing. Numbers in the tables are sourced one-to-one in §9.

## 2. Problem background

**What the system needs to do.** Keep CPU/NPU caches close, fast, and dense enough to hold useful working sets — including, on a phone, multi-MB AI weight tiles — without burning idle power waiting around.

**Why this domain becomes hard.** Three constraints collide: (1) **SRAM bit-cell scaling has stalled** — at TSMC N3B/N3E the SRAM bit-cell shrinks roughly 0% vs N5 (IEDM 2022), so LLC capacity per mm² is stuck; (2) **DRAM refresh power is non-negligible** — on 32 Gb-class DRAMs, refresh contributes >20% of DRAM energy, and the memory hierarchy as a whole is roughly 40–50% of system energy, so refresh alone is ~8–10% of total system energy; (3) **cache contents vanish at power-off** — every time the device wakes from a deep sleep, AI weights and code pages reload from flash, costing time and energy.

**Why the original solution is no longer enough.** Two pressures: agent-era on-device LLMs want larger working sets always-resident (weights + KV); the same workload pattern wants the device to wake cold-start ready in milliseconds. SRAM caches are the only fast layer today, but they're stuck scaling and pay static-leakage tax 24/7. DRAM is denser but burns refresh power. There's no layer between them that is non-volatile and low-leakage. MRAM is the only candidate that fills that slot today.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **SRAM leakage at advanced nodes.** Standby leakage is a growing share of SoC idle power; you pay it whether the cache is doing useful work or not.
2. **SRAM bit-cell scaling stopped.** At N3B/N3E the SRAM bit-cell barely shrinks vs N5 (IEDM 2022) — adding LLC capacity now costs proportionally more area.
3. **DRAM refresh is a constant draw.** Even when the system is idle, DRAM has to refresh; on dense parts this is over a fifth of DRAM energy.
4. **Cache contents disappear at power-off.** Every cold start reloads AI weights and code from flash — measurable in wake-up latency and energy.

### Bottleneck evidence

| Signal | Value | What it means | Source |
|---|---|---|---|
| SRAM bit-cell shrink, N5 → N3B/N3E (TSMC) | **~0%** | Cache capacity per mm² stopped scaling — the lever LLC has used for decades is gone. | IEDM 2022 ("Did We Just Witness The Death Of SRAM?"); SemiWiki forum thread |
| STT-MRAM cell area at 5 nm vs 6T SRAM | **43.3%** of SRAM macro area | At the same node MRAM is more than 2× denser per macro than SRAM, so LLC capacity scales again. | PMC 2024 industry review |
| DRAM refresh share of DRAM energy (32 Gb-class) | **>20%** | Refresh alone is over a fifth of DRAM energy, much of it idle. | PMC 2024 review; corroborated by industry sources |
| Approximate DRAM refresh share of total system energy | **~8–10%** | A measurable lever; this is what "non-volatile + refresh-free" lifts. | Same; derived from refresh share × memory share of system energy |
| Edge-AI MRAM sizing point | **4–16 MB**, **100–200 MHz**, **< 30 ns**, **> 10¹² cycles**, **20+ yr @ 85°C** | Matches the on-device AI weight-buffer use case. | [Memphis / Wevolver edge AI memory page](https://www.wevolver.com/article/three-edge-ai-architectures-that-demand-smarter-memoryand-why) |
| imec scaled SOT-MRAM @ IEDM Dec 2023 | **<100 fJ/bit**, **>10¹⁵ cycles**, **300 ps** switching, **63% switching-energy reduction** vs conventional | The cache-class device specs are now in the right ballpark for LLC. | [imec article](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| Hybrid SRAM/MRAM/ReRAM idle-energy reduction (vendor claim) | **~80%** | A vendor-blog claim, internally consistent with refresh + leakage shares but not independently measured. | [Promwad blog](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) — directional |

**Reading.** The first two numbers are the bottleneck: SRAM stopped scaling, so existing-layer-only LLC growth has hit a wall, and MRAM is the densest non-DRAM contender. The next two say the energy lever is real (DRAM refresh ~8–10% of total system energy is reachable). The last two say the device side is now close enough to LLC-class specs that the design conversation is worth having.

## 4. Architectures: original vs evolved

Both diagrams use the same hierarchy; differences are marked with `*` in the evolved one.

**Original — SRAM-only cache hierarchy + DRAM with refresh**

```
   +---------+
   |   CPU   |
   +----+----+
        |
        v
   +---------+   volatile, leaky
   |  L1 SRAM|
   +----+----+
        |
        v
   +---------+   volatile, leaky
   |  L2 SRAM|
   +----+----+
        |
        v
   +---------+   volatile, leaky;
   | L3 SRAM |   scaling stopped at N3
   |  / LLC  |
   +----+----+
        |
        | bus (refresh power)
        v
   +---------+   volatile, refresh
   |  DRAM   |
   +----+----+
        |
        v
   +---------+   non-volatile, slow
   | NAND    |
   | flash   |
   +---------+
```

*Original: every cache layer is SRAM — volatile, paying static leakage 24/7, and scaling-stopped at N3. DRAM burns refresh power. Everything above flash loses state at power-off; the device cold-starts on every wake.*

**Evolved — hybrid hierarchy with MRAM LLC / persistent buffer**

```
   +---------+
   |   CPU   |
   +----+----+
        |
        v
   +---------+   volatile, leaky (kept for raw speed)
   |  L1 SRAM|
   +----+----+
        |
        v
   +---------+   volatile, leaky (kept for raw speed)
   |  L2 SRAM|
   +----+----+
        |
        | * tier transition (different cell tech)
        v
   +-------------+   * non-volatile (instant-on)
   | L3 LLC OR   |   * zero static leakage
   | persistent  |   * STT-MRAM 6-7.5 ns read /
   | weight buf: |     20 ns write, 10^6-10^12 cycles
   | MRAM (STT   |   * SOT-MRAM <100 fJ/bit,
   |  or SOT)    |     >10^15 cycles, 300 ps (imec)
   +------+------+   * cell ~43% of SRAM area @ 5nm
          |          * AI weights survive power cycles
          v
   +---------+   volatile, refresh
   |  DRAM   |
   +----+----+
        |
        v
   +---------+   non-volatile, slow
   | NAND    |
   | flash   |
   +---------+
```

*Evolved: SRAM stays at L1/L2 for raw speed; an MRAM layer is inserted at LLC or as a persistent weight buffer. Data and weights survive power-off, the layer pays no standby leakage, and the bit-cell is denser than SRAM at the same node — so LLC capacity can grow again.*

## 5. Why evolved helps, what it still doesn't solve

### Why the evolved solution helps

- **SRAM leakage at advanced nodes** — MRAM's standby leakage is effectively zero (no current path when idle); a hybrid hierarchy keeps SRAM only where speed demands it and replaces the rest. The Promwad blog claims **~80% idle-energy reduction** from this combined with eliminating DRAM refresh ([Promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram)) — directional, not measured.
- **SRAM bit-cell scaling stopped** — MRAM cell at 5 nm is **43.3% of SRAM macro area** ([PMC 2024 review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/)). The same area buys roughly 2× more LLC capacity, so the layer scales again.
- **DRAM refresh is constant** — A non-volatile cache layer holds AI weights without DRAM mediation; the weights don't need to live in DRAM at all when idle. This removes the refresh-power cost for the weights.
- **Cache contents vanish at power-off** — MRAM is non-volatile by construction. AI weights and persistent buffers survive deep sleep. This is the "instant-on" benefit and is the most user-visible effect.

### What it still doesn't solve

- **MRAM write is slower and costlier than SRAM/DRAM write.** STT-MRAM at TSMC 16 nm writes in **20 ns** ([PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/)) vs SRAM's nanosecond write — and the write current is large. Write-heavy workloads (e.g. updating model activations in cache) are not a good fit.
- **STT endurance is finite.** TSMC 16 nm eFlash-class is **10⁶ cycles** (ISSCC 2023, 32 Mb); cache-class targets reach **10¹²** (PMC review), still finite. SOT can hit **>10¹⁵** (imec) but isn't yet manufacturable at cache class.
- **SOT-MRAM productization isn't done.** The roadmap paper ([arXiv 2104.11459](https://arxiv.org/abs/2104.11459)) names *field-free SOT switching at production scale* as the open device-physics blocker; the 2024 EDN status update echoes this. Imec shows 300 ps switching in lab; volume manufacture is not yet here.
- **Mobile-SoC LLC / weight-store use is not shipping.** **eMRAM replacing eFlash is shipping** (Samsung 28 nm FD-SOI since 2019; GlobalFoundries 22FDX since Feb 2020; TSMC 22 nm and 16 nm). MRAM-as-LLC on a consumer mobile SoC is not. The system-level "~80% idle reduction" claim is from a vendor blog and is not independently replicated.
- **Persistence brings new responsibilities.** Non-volatile cache means residual data after power-off — secure erase, write-ordering semantics ("persistent cache" needs ordering like persistent memory), and side-channel exposure all become new problems the SRAM hierarchy never had.

## 6. Comparison table

Every cell is a number, a boolean, or `n/a (reason)`. Every row has a source. Honest tradeoffs: MRAM write latency, finite endurance, and "not shipping at mobile-LLC class."

| Dimension | Original: SRAM cache + DRAM | Evolved: hybrid SRAM + MRAM (STT/SOT) | Improvement | Source |
|---|---|---|---|---|
| Read latency at cache class | ~1–3 ns (SRAM L1/L2/L3) | STT-MRAM **6–7.5 ns**; embedded edge-AI macro **< 30 ns** | **~3–10×** slower (regression on read) | TSMC 16 nm STT-MRAM, [PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/); [Wevolver edge AI](https://www.wevolver.com/article/three-edge-ai-architectures-that-demand-smarter-memoryand-why) |
| Write latency at cache class | ~1–3 ns (SRAM) | STT-MRAM **20 ns**; SOT-MRAM down to **300 ps** (imec lab) | mixed: STT regresses ~10×; SOT eventually wins | PMC review; [imec](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| Endurance (write cycles) | unlimited (SRAM) | STT-MRAM **10⁶–10¹²** (eFlash vs cache class); SOT-MRAM lab **>10¹⁵** | finite; **−** vs SRAM | [PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/); [imec](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| Bit-cell area at 5 nm vs SRAM | baseline (6T SRAM, scaling stopped at N3) | **43.3%** of SRAM macro area (STT-MRAM) | **−57%** area (denser → more capacity per mm²) | PMC review |
| Standby static leakage | non-zero, growing at advanced nodes | **0** | qualitative: eliminated | imec, TSMC research |
| Retention after power-off | **0** (volatile) | **>10 yr** at 150 °C (TSMC 22 nm); 1 min at 125 °C (TSMC 16 nm cache class) | qualitative: persistent | TSMC 22 nm; PMC review |
| Switching energy at cache class | n/a (SRAM bit-flip ~fJ but constant leakage) | SOT-MRAM **<100 fJ/bit**, **63%** reduction vs conventional | **−63%** vs conventional MRAM; comparable order-of-magnitude vs SRAM bit-flip-only | [imec](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) |
| Endurance vs other NVM | SRAM unlimited, DRAM unlimited | MRAM ~**10¹⁵** vs ReRAM **10⁶–10⁹** vs NOR Flash ~**10⁴** | MRAM is the cache-grade NVM | [Promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) |
| Hybrid-hierarchy idle-energy reduction | baseline | **~80%** claimed (combines DRAM refresh removal + SRAM leakage cut) | **−80%** — directional, not measured | [Promwad](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) |
| eMRAM replacing eFlash | n/a (separate market) | **shipping** (TSMC 22/16 nm, Samsung 28 nm FD-SOI since 2019, GF 22FDX since 2020) | new capability, **shipping in MCU/IoT/auto** | TSMC, Samsung, GF announcements |
| Mobile-SoC consumer LLC / weight-store with MRAM | shipping (SRAM only) | **not shipping** (research only) | **0** (deployment regression) | A16h §5; EDN 2024 |

## 7. One-word characterization

**Non-volatile** (非易失) — the defining change is that an MRAM layer between SRAM and DRAM **keeps state without power and pays no standby leakage**, so AI weights and other persistent buffers survive deep sleep, the cache layer can scale again (MRAM cell ~**43.3%** of SRAM area at 5 nm), and a hybrid hierarchy can reach toward **~80%** lower idle energy (Promwad, directional) — at the cost of **~10×** slower writes than SRAM in STT form and finite endurance (**10⁶–10¹²** cycles for STT-MRAM, **>10¹⁵** for lab SOT-MRAM at imec). Already shipping as **eFlash replacement** (Samsung 28 nm FD-SOI since 2019, GF 22FDX since 2020, TSMC 22 nm and 16 nm); mobile-SoC LLC / on-device AI weight-store is **not shipping**.

## 8. Open questions and caveats

- **The 80% idle-energy reduction is a vendor-blog directional claim.** The Promwad page does not provide a measurement chain. The underlying levers (DRAM refresh ~8–10% of system energy + SRAM standby leakage growing at advanced nodes) are real; the 80% headline number is not independently replicated.
- **TSMC 16 nm STT-MRAM has two macros with different specs.** The eFlash-replacement variant (ISSCC 2023, 32 Mb) is **10⁶ cycles, 20 yr @ 150 °C, 6 ns read**. The cache-class target is **10¹² cycles, 1 min @ 125 °C, 7.5 ns read / 20 ns write**. The anchor A16h article cited the cache-class numbers; both are real, but they're different devices. Cite carefully.
- **TSMC research pages were not directly fetchable in this run.** The numbers above were cross-checked via PMC 2024 industry review, ISSCC 2023 paper at ResearchGate, and the EDN 2024 SOT-MRAM article. They should be cross-referenced against TSMC's own pages when next available.
- **Field-free SOT switching at production scale remains open.** The roadmap paper ([arXiv 2104.11459](https://arxiv.org/abs/2104.11459)) and the 2024 EDN status update both name this as the device-physics blocker. Imec's 300 ps switching is lab-scale.
- **No public mobile-SoC consumer LLC product uses MRAM.** Treat all "MRAM-as-LLC on a phone" framing as forward-looking design exploration, not shipped reality.
- **Persistent cache brings new system-level questions.** Residual data after power-off (security), write-ordering semantics (persistent-memory-style flush/fence requirements), and side-channel exposure are not problems the SRAM hierarchy has and they get inherited the moment a non-volatile layer enters cache.

## 9. References

1. *Progress of emerging non-volatile memory technologies in industry*. (2024). MRS Communications / PMC. [pmc.ncbi.nlm.nih.gov/articles/PMC11618178/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618178/) — vendor-by-vendor spec table for STT-MRAM (TSMC 22 nm / 16 nm, Samsung 14 nm, GF 22 nm).
2. TSMC. (2023). *33.1 A 16 nm 32 Mb Embedded STT-MRAM* (ISSCC 2023, eFlash replacement). [researchgate.net/publication/369497100](https://www.researchgate.net/publication/369497100) — **6 ns read**, **10⁶ cycles**, **20 yr @ 150 °C**.
3. TSMC Research. (2022). *22 nm STT-MRAM for Reflow and Automotive Uses*. [research.tsmc.com/page/mram/1.html](https://research.tsmc.com/page/mram/1.html) — **>10 yr @ 150 °C through 6× reflow**, **>1100 Oe @ 25 °C magnetic immunity**.
4. TSMC Research. (2023). *High RA Dual-MTJ SOT-MRAM devices for High Speed (10 ns) Compute-in-Memory Applications*. [research.tsmc.com/page/mram/5.html](https://research.tsmc.com/page/mram/5.html) — SOT-MRAM unit cell **10 ns**, CIM-oriented.
5. MRAM-Info. (2024). *ITRI and TSMC announce advances in SOT-MRAM development*. [mram-info.com/itri-and-tsmc-announce-advances-sot-mram-development](https://www.mram-info.com/itri-and-tsmc-announce-advances-sot-mram-development) — SOT-MRAM **10 ns write**, **1%** of STT power, IEDM 2023.
6. Ahmad, M. (2024). *Memory lane: Where SOT-MRAM technology stands in 2024*. EDN. [edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/](https://www.edn.com/memory-lane-where-sot-mram-technology-stands-in-2024/) — imec **<100 fJ/bit**, **>10¹⁵** endurance, **63%** energy reduction; SOT ~4× faster than STT; positioned for LLC.
7. imec. (2024-12-16). *Bringing SOT-MRAM technology closer to last-level cache memory specifications*. [imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications](https://www.imec-int.com/en/articles/bringing-sot-mram-technology-closer-last-level-cache-memory-specifications) — scaled SOT-MRAM **<100 fJ/bit**, **>10¹⁵ cycles**, switching down to **300 ps**, write-error rate **10⁻⁶**, 400 °C process compatibility.
8. Shao, Q., Li, P., Lake, R. et al. (2021/2023). *Roadmap of spin-orbit torques*. arXiv:2104.11459. [arxiv.org/abs/2104.11459](https://arxiv.org/abs/2104.11459) — SOT-MRAM 3-terminal; superior energy efficiency vs STT; field-free switching as gating issue.
9. GlobalFoundries / AnandTech. (2020-03). *GLOBALFOUNDRIES Delivers Industry's First Production-ready eMRAM on 22FDX*. [gf.com/.../industrys-first-production-ready-emram-22fdx-platform-iot/](https://gf.com/gf-press-release/globalfoundries-delivers-industrys-first-production-ready-emram-22fdx-platform-iot/) — **4–48 Mb macros**, **10⁵ cycles**, **10 yr retention −40 to 125 °C**, magnetic immunity **~600 Oe @105 °C**.
10. Promwad. (2025). *Adaptive Memory Hierarchies: Combining SRAM, MRAM, and ReRAM for Smarter Edge Systems*. [promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram](https://promwad.com/news/adaptive-memory-hierarchies-sram-mram-reram) — **~80%** idle-energy reduction (vendor claim, directional); MRAM ~**10¹⁵** vs ReRAM **10⁶–10⁹** vs Flash ~**10⁴** endurance.
11. MEMPHIS Electronic / Wevolver. (2024). *Three Edge AI Architectures That Demand Smarter Memory—and Why?*. [wevolver.com/.../three-edge-ai-architectures-that-demand-smarter-memoryand-why](https://www.wevolver.com/article/three-edge-ai-architectures-that-demand-smarter-memoryand-why) — embedded MRAM **4–16 MB**, **100–200 MHz**, **<30 ns**, **>10¹² cycles**, **20+ yr @ 85 °C**.
12. Shilov, A. (2024). *TSMC tandem builds exotic new MRAM-based memory*. Tom's Hardware. [tomshardware.com/.../tsmc-tandem-builds-exotic-new-memory-...](https://www.tomshardware.com/pc-components/dram/tsmc-tandem-builds-exotic-new-memory-with-radically-lower-latency-and-power-consumption-mram-based-memory-can-also-conduct-its-own-compute-operations) — TSMC + ITRI SOT-MRAM positioned for LLC and compute-in-memory.
13. SemiWiki forum. (2022/2023). *TSMC officially halts SRAM scaling*. [semiwiki.com/forum/threads/tsmc-officially-halts-sram-scaling.17223/](https://semiwiki.com/forum/threads/tsmc-officially-halts-sram-scaling.17223/) — citing IEDM 2022 *"Did We Just Witness The Death Of SRAM?"* — system-level motivation.
14. A16h anchor article (this project). [advanced/A16h-STT-SOT-MRAM多级缓存方案.md](../../advanced/A16h-STT-SOT-MRAM多级缓存方案.md).

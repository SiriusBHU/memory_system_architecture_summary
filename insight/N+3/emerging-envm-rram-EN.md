# Emerging Embedded NVM Ecosystem: ReRAM/RRAM Replaces Embedded Flash

> **Scope**: Track the technology evolution from embedded flash (eFlash / NOR Flash) to resistive RAM (ReRAM / RRAM) as the de-facto embedded non-volatile memory (eNVM) for MCUs, IoT SoCs, automotive controllers, and edge-AI accelerators. Focus on process scalability, manufacturing cost, performance, foundry ecosystem, and the nascent compute-in-memory (CIM) application.
>
> **Method**: Cross-reference the Weebit Nano ICCAD 2024 presentation, MRS Communications industry survey (Nov 2024), TSMC foundry platform data, TechInsights roadmap (May 2024), Yole Emerging NVM 2025 report, Infineon AURIX TC4x announcements, and vendor press releases. All cost comparisons use wafer-level adder percentages relative to baseline CMOS logic process.

---

## 1. Problem Background

Every microcontroller, IoT sensor, and automotive ECU needs on-chip non-volatile memory to store firmware, calibration data, and security keys. For decades, **embedded NOR flash (eFlash)** has filled this role: a floating-gate or charge-trap cell monolithically integrated alongside CMOS logic on the same die. At 40 nm and above, eFlash is a mature, reliable, and well-characterized solution — the default choice across billions of shipped MCUs from NXP, STMicroelectronics, Renesas, Infineon, and others.

But the semiconductor industry is now pushing logic to 22 nm, 16 nm, 12 nm, and beyond for power, performance, and cost reasons. Embedded flash **cannot follow**. The floating-gate cell requires thick tunnel oxides, high programming voltages (>10 V), and dedicated high-voltage transistors that are incompatible with advanced logic CMOS processes. The industry consensus is that **28 nm is the practical scaling floor for eFlash** — and many believe the economic floor arrives even earlier due to mask count and process complexity.

This creates a technology gap: advanced-node SoCs need on-chip NVM, but the only NVM the industry has used for 30 years cannot be built at those nodes. **Resistive RAM (ReRAM / RRAM)** — a two-terminal metal-oxide device that stores data as resistance states rather than trapped charge — has emerged as the leading replacement. It scales to 12 nm and below, adds only 2 masks to the CMOS process, and opens an entirely new application dimension: in-memory computing for edge AI.

---

## 2. Problems and Evidence

### 2.1 eFlash Cannot Scale Below 28 nm

| Evidence | Detail |
|----------|--------|
| Scaling wall | Industry has not figured out how to do NOR flash processes smaller than 28 nm ([Semiconductor Engineering](https://semiengineering.com/embedded-flash-scaling-limits/)) |
| Root cause — charge trapping | Miniaturization below 28 nm challenges the fundamental charge-trapping mechanism; oxide thinning degrades retention and endurance |
| Root cause — high voltage | eFlash program/erase requires >10 V, needing thick-oxide HV transistors incompatible with sub-28 nm CMOS |
| Economic barrier | "Many believe 28nm/22nm will be the end of eFlash, not because of scalability limitations but because of economic barriers" ([Semiconductor Engineering](https://semiengineering.com/embedded-flash-scaling-limits/)) |

### 2.2 eFlash Manufacturing Cost Is Unsustainable

Embedding flash into a logic process requires **7-10 additional photomasks** for the floating-gate stack, tunnel oxide, high-voltage transistors, and isolation structures. This adds **>25% to wafer cost** and lengthens cycle time by weeks. As logic nodes advance, the mask count gap between baseline CMOS and eFlash-enabled CMOS widens further, making eFlash economically untenable for cost-sensitive IoT and consumer MCUs.

### 2.3 Performance Limitations of eFlash

| Metric | eFlash (NOR) | Limitation |
|--------|-------------|------------|
| Program speed | ~1-10 us/word | Orders of magnitude slower than logic clock |
| Erase | Sector-based, ~100 ms | Cannot erase individual bits or bytes |
| Endurance | ~10,000-100,000 P/E cycles | Limits OTA update frequency |
| Read latency | ~20-50 ns | Acceptable but not improving with scaling |
| Write granularity | Page/sector only | No bit-wise write capability |

### 2.4 Emerging Applications Demand More Than Storage

Edge-AI accelerators and neuromorphic chips require memory that can participate in computation — performing multiply-accumulate (MAC) operations in situ to avoid the energy cost of shuttling data across the memory bus. eFlash, designed purely for code storage, has no analog computing capability and cannot serve this emerging workload.

---

## 3. Architecture: eFlash vs. ReRAM

### Embedded Flash (Original — 28 nm+)

```
+-------------------------------------------------------------------+
|                        SoC Die (40 nm / 28 nm)                     |
|                                                                    |
|   +--------------------+     +------------------------------+      |
|   |   Logic Domain     |     |     eFlash Domain             |      |
|   |   (baseline CMOS)  |     |     (7-10 extra masks)        |      |
|   |                    |     |                               |      |
|   |   CPU core         |     |   +------------------------+  |      |
|   |   Peripherals      |     |   | Floating-Gate NOR Array |  |      |
|   |   SRAM             |     |   | Tunnel oxide ~9-10 nm   |  |      |
|   |   I/O              |     |   | Control gate stack      |  |      |
|   |                    |     |   | Sector erase only       |  |      |
|   +--------------------+     |   +------------------------+  |      |
|          |                   |              |                 |      |
|          |                   |   +------------------------+  |      |
|   +------+------+           |   |  HV Transistors (>10 V) |  |      |
|   | Low-Voltage  |           |   |  Thick gate oxide       |  |      |
|   | Transistors   |           |   |  Charge pumps           |  |      |
|   | (1.0-1.8 V)  |           |   |  Level shifters         |  |      |
|   +--------------+           |   +------------------------+  |      |
|                              +------------------------------+      |
|                                                                    |
|   Process: baseline CMOS + 7-10 extra masks                       |
|   Cost adder: >25% wafer cost                                      |
|   Scaling floor: 28 nm (practical), 40 nm (many designs)          |
|   Endurance: 10K-100K P/E cycles                                  |
+-------------------------------------------------------------------+
```

### ReRAM / RRAM (Evolved — Scales to 12 nm+)

```
+-------------------------------------------------------------------+
|                    SoC Die (22 nm / 16 nm / 12 nm)                 |
|                                                                    |
|   +--------------------+     +------------------------------+      |
|   |   Logic Domain     |     |     ReRAM Domain              |      |
|   |   (baseline CMOS)  |     |     (2 extra masks only)      |      |
|   |                    |     |                               |      |
|   |   CPU core         |     |   +------------------------+  |      |
|   |   Peripherals      |     |   | ReRAM Array (BEOL)      |  |      |
|   |   SRAM             |     |   | Metal-Oxide-Metal stack  |  |      |
|   |   I/O              |     |   | (e.g. TaOx/HfO2)        |  |      |
|   |   AI accelerator   |     |   | Between metal layers     |  |      |
|   |                    |     |   | Bit-wise write capable   |  |      |
|   +--------------------+     |   +------------------------+  |      |
|          |                   |              |                 |      |
|          |                   |   +------------------------+  |      |
|   +------+------+           |   |  Access Transistor (1T)  |  |      |
|   | Standard     |           |   |  Standard CMOS voltage   |  |      |
|   | CMOS          |           |   |  No HV devices needed    |  |      |
|   | Transistors   |           |   |  No charge pumps         |  |      |
|   +--------------+           |   +------------------------+  |      |
|                              +------------------------------+      |
|                                                                    |
|   Process: baseline CMOS + 2 extra masks (BEOL integration)       |
|   Cost adder: <10% wafer cost                                      |
|   Scaling: demonstrated at 12 nm (TSMC), roadmap to 7 nm / 6 nm  |
|   Endurance: 100K-1M+ cycles (10x-100x better than eFlash)       |
|   Bonus: analog CIM capability for edge AI                        |
+-------------------------------------------------------------------+
```

### ReRAM Cell Structure (1T1R)

```
         Bit Line (BL)
            |
    +-------+-------+
    |   Top Electrode |   (TiN)
    |   +-----------+ |
    |   | Switching  | |   Metal oxide (HfO2, TaOx, or bilayer)
    |   |   Layer    | |   Resistance modulated by oxygen vacancy
    |   +-----------+ |   filament formation / rupture
    |   Bottom Elect. |   (TiN / Ti / Ta)
    +-------+-------+
            |
    +-------+-------+
    |   Access       |
    |   Transistor   |   Standard CMOS NFET (1T)
    |   (1T)         |
    +-------+-------+
            |
        Source Line (SL)

    SET:   Form conductive filament  -> Low Resistance State (LRS)
    RESET: Rupture filament          -> High Resistance State (HRS)
    READ:  Sense resistance ratio    -> LRS / HRS = bit value
```

### Key Architectural Differences

| Feature | eFlash (NOR) | ReRAM (RRAM) |
|---------|-------------|--------------|
| Storage mechanism | Charge trapped on floating gate | Resistance state of metal-oxide filament |
| Cell structure | 1T (floating gate) or 2T (split gate) | 1T1R (transistor + resistor) |
| Integration location | FEOL (front-end, in transistor layer) | BEOL (back-end, between metal layers) |
| Extra masks | 7-10 | 2 |
| Wafer cost adder | >25% | <10% |
| HV transistors required | Yes (>10 V for program/erase) | No (operates at CMOS voltages) |
| Scaling floor | 28 nm (practical) | 12 nm demonstrated, 7/6 nm in R&D |
| Write granularity | Sector/page erase then program | Bit-wise write without erase |
| Analog CIM potential | None | Native (analog resistance levels) |

---

## 4. What ReRAM Helps — and What It Does Not Solve

### Helps

- **Advanced-node eNVM**: ReRAM provides non-volatile storage at 22 nm, 16 nm, and 12 nm where eFlash simply cannot exist, unblocking the migration of MCU and IoT SoC designs to advanced nodes.
- **Dramatic cost reduction**: The 2-mask BEOL process adds <10% to wafer cost versus >25% for eFlash, a particularly critical advantage for high-volume consumer and IoT chips where margin pressure is intense.
- **Better endurance**: ReRAM delivers 100K-1M+ program/erase cycles, 10x-100x beyond eFlash's 10K-100K cycles, enabling more frequent OTA firmware updates and data logging.
- **Bit-wise write**: Unlike eFlash which requires sector erase before programming, ReRAM supports bit-wise write operations — improving write performance and reducing wear.
- **Edge-AI CIM**: ReRAM's analog resistance states enable multiply-accumulate operations directly in the memory array, potentially eliminating the data-movement bottleneck for inference at the edge.
- **Automotive readiness**: TSMC and Infineon's AURIX TC4x family demonstrates automotive-grade ReRAM at 28 nm with AEC-Q100 qualification, with Weebit targeting the same qualification.

### Does Not Solve

- **Endurance for SRAM/DRAM replacement**: ReRAM's 10^5-10^6 cycle endurance, while much better than eFlash, is far below the >10^15 cycles needed to replace SRAM or DRAM in working memory roles.
- **Write speed parity with SRAM**: ReRAM write latency (~50-200 ns) is faster than eFlash but still 100x slower than SRAM (~0.5 ns), limiting its use as general-purpose cache.
- **Variability and yield**: Filament-based switching exhibits stochastic behavior; cycle-to-cycle and device-to-device variability remain active areas of engineering, particularly for multi-level cell (MLC) operation.
- **Retention at extreme temperatures**: While TSMC has demonstrated 10-year retention at 105 C for 12 nm RRAM, achieving automotive Grade-0 (150 C) retention at the smallest nodes is still under qualification.
- **CIM maturity**: Compute-in-memory with ReRAM is demonstrated in academic prototypes and early silicon (ISSCC 2024), but production CIM accelerators with software stacks are not yet shipping at scale.

---

## 5. Quantitative Comparison

| Metric | eFlash (NOR, 28 nm+) | ReRAM/RRAM (Evolved) | Delta |
|--------|----------------------|----------------------|-------|
| Minimum process node | 28 nm (practical floor) | 12 nm (TSMC demonstrated) | Scales 2+ nodes further |
| Extra photomasks | 7-10 | 2 | 5-8 fewer masks |
| Wafer cost adder | >25% | <10% | >15 pp cost saving |
| Program/erase endurance | 10K-100K cycles | 100K-1M+ cycles | 10x-100x better |
| Data retention | 10+ years @ 85 C | 10+ years @ 105 C | Higher temp tolerance |
| Write granularity | Sector erase + page program | Bit-wise write | Structural advantage |
| Read latency | 20-50 ns | 7-20 ns | 2x-3x faster |
| Write latency | 1-10 us/word | 50-200 ns | 10x-100x faster |
| Operating voltage (write) | >10 V (charge pump) | 1.2-3.0 V (CMOS rail) | No HV circuitry |
| Integration location | FEOL (transistor layer) | BEOL (metal layers) | Non-intrusive to logic |
| Cell structure | 1T floating gate / 2T split gate | 1T1R | Simpler |
| Analog CIM capability | None | Native (multi-level resistance) | New capability |
| Foundry availability (2025) | TSMC, GF, UMC, Samsung (28nm+) | TSMC (40/28/22/12nm), GF (22nm), DB HiTek (130nm), SkyWater (130nm) | Rapidly expanding |
| Production customers (2025) | Thousands (mature ecosystem) | Nordic, Infineon, Nuvoton, onsemi, Broadcom (ramping) | Early but accelerating |

---

## 6. Ecosystem and Adoption Timeline

### Foundry ReRAM Platforms (as of mid-2025)

| Foundry | Node(s) | Status | Key Customers |
|---------|---------|--------|---------------|
| TSMC | 40 nm | Mass production (since ~2022) | STMicroelectronics, Nuvoton |
| TSMC | 28 nm | Mass production | Infineon (AURIX TC4x) |
| TSMC | 22 nm ULL | Production / risk production | Nordic Semiconductor (nRF54L15) |
| TSMC | 12 nm | Consumer-grade risk production (2024) | Under NDA |
| TSMC | 7 nm / 6 nm | R&D | — |
| GlobalFoundries | 22FDX | Qualification | Weebit IP licensees |
| DB HiTek | 130 nm BCD | Qualified (2025) | Weebit IP licensees |
| SkyWater | 130 nm | Available via Efabless chipIgnite | Prototype / academic |
| onsemi (Treo) | TBD | Licensed Weebit ReRAM IP (Jan 2025) | Automotive / industrial |

### Key Product Milestones

| Year | Milestone |
|------|-----------|
| 2022 | TSMC 40/28/22 nm RRAM in production; Infineon announces AURIX TC4x with 28 nm RRAM |
| 2023 | Nordic nRF54L15 (22 nm, 1.5 MB ReRAM) begins sampling; Nuvoton ships ReRAM MCUs |
| 2024 | TSMC demonstrates 12 nm RRAM (smallest CMOS integration); ISSCC 2024 shows 22 nm 16 Mb ReRAM CIM macro at 31.2 TFLOPS/W; Weebit ICCAD presentation; TechInsights confirms Nordic nRF54L15 RRAM process |
| 2025 | onsemi licenses Weebit ReRAM for Treo platform; DB HiTek qualifies Weebit ReRAM at 130 nm; Infineon AURIX TC4x 28 nm RRAM ramp; eNVM market projected $0.14B -> $3.3B by 2030 (Yole) |
| 2025+ | TSMC roadmap: 7 nm / 6 nm RRAM in R&D; NXP 16 nm FinFET MRAM samples; broad MCU migration from eFlash to eNVM |

---

## 7. One-Word Verdict

**Replacement** — ReRAM is a direct, cost-superior replacement for embedded flash that also unlocks advanced-node integration and compute-in-memory, making it a generational platform shift rather than an incremental upgrade.

---

## 8. Open Questions

1. **12 nm and below yield**: TSMC's 12 nm RRAM entered risk production in 2024, but volume production yield data and automotive qualification at this node are not yet public. Can filament variability be controlled at sub-20 nm feature sizes?
2. **MRAM vs. ReRAM partitioning**: NXP is pursuing 16 nm FinFET MRAM for automotive MCUs while Infineon chose 28 nm RRAM. Will the industry converge on one eNVM technology, or will MRAM and ReRAM co-exist with application-specific segmentation (MRAM for high-endurance, ReRAM for cost/density)?
3. **CIM production timeline**: The ISSCC 2024 ReRAM CIM macro (31.2 TFLOPS/W) is a research demonstration. When will the first production edge-AI chip ship with ReRAM-based compute-in-memory, and what software stack will support it?
4. **Multi-level cell (MLC) reliability**: MLC ReRAM (storing 2+ bits per cell) would dramatically increase density but requires tighter resistance distributions. Is MLC ReRAM ready for production, or will single-level cell (SLC) remain the standard for the foreseeable future?
5. **eFlash brownfield**: Billions of 40 nm and 28 nm MCU designs use eFlash today. How long will foundries continue to support eFlash processes, and what is the migration cost for existing designs?
6. **STMicroelectronics PCM path**: ST has bet on embedded PCM (ePCM) rather than ReRAM for its STM32 roadmap (18 nm FDSOI with Samsung Foundry). Will ePCM remain a viable competitor, or will ReRAM's broader foundry ecosystem marginalize it?

---

## 9. References

1. Weebit Nano, "Embedded NVM for a New Era," ICCAD 2024 presentation, Dec 2024. [PDF](https://www.weebit-nano.com/wp-content/uploads/2024/12/Weebit-ICCAD-2024-Embedded-NVM-RRAM-ReRAM-technology-IP-replace-flash-memory-semiconductor-companies.pdf)
2. Weebit Nano, "ReRAM: Emerging as the New Embedded NVM Standard," FMS 2025. [PDF](https://www.weebit-nano.com/wp-content/uploads/2025/09/FMS25_Weebit-ReRAM-in-commercial-fabs-for-various-AI-architectures-for-edge-applications-RRAM-IP-technology_W.pdf)
3. MRS Communications, "Progress of emerging non-volatile memory technologies in industry," Nov 2024. [Springer](https://link.springer.com/article/10.1557/s43579-024-00660-2)
4. TechInsights, "Embedded & Emerging Memory Technology Roadmap," May 2024. [Link](https://www.techinsights.com/blog/embedded-emerging-memory-technology-roadmap-may-2024)
5. TechInsights, "Advanced TSMC 22ULL Embedded RRAM Chip Unveiled" (Nordic nRF54L15 analysis). [Link](https://www.techinsights.com/blog/advanced-tsmc-22ull-embedded-rram-chip-unveiled)
6. TSMC, "Logic-Compatible RRAM Supports Firmware, Data Storage and Security Memory." [Link](https://www.tsmc.com/english/dedicatedFoundry/technology/platform_IoT_tech_NVM)
7. TSMC, "Comprehensive Ultra-low Power Technology Platform (22ULL / 12FFC+ ULL)." [Link](https://www.tsmc.com/english/dedicatedFoundry/technology/platform_IoT_tech_22ULL_12FFCplus_ULL)
8. Infineon & TSMC, "Infineon and TSMC to Introduce RRAM Technology for Automotive AURIX TC4x Product Family," Nov 2022. [Link](https://www.infineon.com/market-news/2022/infatv202211-031)
9. NXP & TSMC, "NXP and TSMC to Deliver Industry's First Automotive 16 nm FinFET Embedded MRAM," 2024. [Link](https://www.nxp.com/company/about-nxp/newsroom/NW-NXP-AND-TSMC-DELIVER-FIRST16NM-FINFET-MRAM)
10. Yole Group, "With early adopters such as STMicroelectronics and NXP, emerging NVMs reaffirm their potential," 2024. [Link](https://www.yolegroup.com/strategy-insights/with-early-adopters-such-as-stmicroelectronics-and-nxp-emerging-nvms-reaffirm-their-potential/)
11. Yole Group, "Emerging Non-Volatile Memory 2025." [Link](https://www.yolegroup.com/product/report/emerging-non-volatile-memory-2025/)
12. Semiconductor Engineering, "Embedded Flash Scaling Limits." [Link](https://semiengineering.com/embedded-flash-scaling-limits/)
13. Semiconductor Engineering, "ReRAM Seeks To Replace NOR." [Link](https://semiengineering.com/reram-seeks-to-replace-nor/)
14. Embedded.com, "Understanding the emerging contenders for the Flash memory crown." [Link](https://www.embedded.com/understanding-the-emerging-contenders-for-the-flash-memory-crown/)
15. Weebit Nano, "ReRAM: The Automotive NVM Solution," FMS 2024. [PDF](https://files.futurememorystorage.com/proceedings/2024/20240807_OMEM-201-1_Regev.pdf)
16. Weebit Nano, "Weebit Nano licenses its ReRAM technology to onsemi," Jan 2025. [Link](https://www.storagenewsletter.com/2025/01/02/weebit-nano-licenses-its-reram-technology-to-onsemi-tier-1-semiconductor-supplier/)
17. Nature, "A compute-in-memory chip based on resistive random-access memory," 2022. [Link](https://www.nature.com/articles/s41586-022-04992-8)
18. Nature, "A mixed-precision memristor and SRAM compute-in-memory AI processor," 2025. [Link](https://www.nature.com/articles/s41586-025-08639-2)
19. SemiWiki, "Weebit Nano is at the Epicenter of the ReRAM Revolution." [Link](https://semiwiki.com/ip/weebit-nano/348406-weebit-nano-is-at-the-epicenter-of-the-reram-revolution/)
20. SemiWiki, "Weebit Nano Moves into the Mainstream with Customer Adoption." [Link](https://semiwiki.com/ip/weebit-nano/360158-weebit-nano-moves-into-the-mainstream-with-customer-adoption/)

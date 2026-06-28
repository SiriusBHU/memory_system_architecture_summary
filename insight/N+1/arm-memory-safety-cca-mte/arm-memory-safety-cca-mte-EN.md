# ARM Memory Safety and Confidential Computing: CCA and MTE

> This document compares the original software-only memory safety and TrustZone-based isolation approach with the evolved hardware-assisted memory tagging (MTE) and realm-based confidential computing (CCA/RME) approach for ARM platforms. It surveys academic (IEEE S&P, USENIX Security, SysTEX, arxiv) and industry (Google Android, ARM) progress from 2023–2026.

## 1. Scope and method

**Domain definition.** Memory safety enforcement and confidential computing on ARM-based terminal devices (smartphones, tablets, edge AI accelerators). The scope covers two converging hardware extensions: Memory Tagging Extension (MTE) for spatial/temporal memory safety, and Confidential Computing Architecture (CCA) with Realm Management Extension (RME) for hardware-enforced workload isolation — particularly for on-device ML model protection.

**What "original" and "evolved" mean here.** The *original* solution relies on software instrumentation for memory safety (AddressSanitizer, MemorySanitizer, GWP-ASan) and TrustZone as the sole hardware TEE for isolation. The *evolved* solution introduces hardware-level memory tagging (ARMv8.5-A MTE) that catches use-after-free and buffer overflows at negligible runtime cost, plus a four-world isolation architecture (ARMv9 RME) that replaces the binary Secure/Non-secure split with dynamically allocatable Realms for confidential VMs and on-device ML.

**Sources.** 14 primary sources: 5 academic papers (IEEE S&P 2025, USENIX Security 2023, SysTEX 2025, arxiv 2024–2026), 4 industry references (Android AOSP, ARM developer documentation), 3 benchmark studies (MTE performance in practice, TikTag speculative attack), 2 architecture specifications (ARM CCA, RME system architecture).

## 2. Problem background

**What the system needs to do.** Protect mobile and edge devices against memory corruption exploits (buffer overflows, use-after-free, type confusion) and provide hardware-enforced isolation for sensitive workloads — especially on-device ML models whose weights and training data must remain confidential even from the host OS and hypervisor.

**Why this domain becomes hard.** Memory safety bugs account for approximately 70% of high-severity vulnerabilities across Android, Chrome, and Microsoft products [Google Security Blog 2024, Chromium Security]. Native C/C++ code constitutes over 70% of the Android platform and ~50% of Play Store apps, making a rewrite-to-Rust infeasible for the existing codebase. Meanwhile, TrustZone's binary Secure/Non-secure model limits the secure world to a single vendor-controlled TEE with a constrained memory budget (typically 16–64 MiB in OP-TEE) and a growing TCB attack surface.

**Why the original solution is no longer enough.** ASan provides ~2x CPU and ~2x memory overhead, making it impractical for production. TrustZone restricts third-party developer access, cannot run confidential VMs, and offers no protection against a compromised hypervisor. On-device ML inference requires both memory safety for the runtime and isolation for model weights — neither is adequately served by software-only tooling or TrustZone alone.

## 3. Specific problems and bottleneck evidence

1. **Software sanitizers are too expensive for production** — ASan imposes ~2x CPU overhead and ~2x memory overhead; HWASan reduces memory overhead to ~15% but retains similar CPU cost. Neither can be shipped in release builds on battery-constrained mobile devices [Android AOSP ASan docs].

2. **Memory safety bugs dominate the CVE landscape** — 76% of Android vulnerabilities were memory safety issues in 2019. Even after Google's Safe Coding initiative pushed new code to Rust/Kotlin, memory safety bugs still accounted for 24% of Android CVEs in 2024, and over 80% of exploited 0-days across the industry are memory safety issues [Google Security Blog 2024].

3. **TrustZone's binary model restricts developer access and isolation granularity** — Secure world memory is limited (e.g., Kinibi limits each Trusted Application to 1 MiB), TEE vendors gate third-party app deployment behind rigorous validation, and all TAs share a single Trusted OS whose bugs compromise every tenant [Aster/arxiv 2407.16694, ReZone/arxiv 2203.01025].

4. **TrustZone cannot protect against a compromised hypervisor** — In TrustZone, the Normal-world hypervisor manages all non-secure memory; a hypervisor exploit exposes every guest VM. CCA's Realm world is explicitly designed so that even a compromised hypervisor cannot read or modify Realm memory [ARM CCA spec, SHELTER/USENIX Security 2023].

5. **On-device ML models lack hardware-enforced confidentiality** — Model weights and inference data in Normal world are readable by the host OS, enabling model extraction and membership inference attacks. TrustZone's constrained memory cannot host full ML models (e.g., GPT-2 at 177 MiB, TinyLlama at 1,169 MiB) [arxiv 2504.08508].

### Bottleneck evidence

| Scenario | Original approach | Measured cost / gap | Source |
|---|---|---|---|
| ASan on Android (production) | Software instrumentation | ~2x CPU, ~2x memory overhead | [Android AOSP] |
| HWASan on Android | Hardware-assisted instrumentation | ~2x CPU, 15% memory overhead | [Android AOSP] |
| Android CVEs (2019) | C/C++ codebase | 76% are memory safety bugs | [Google Security Blog] |
| TrustZone TA memory | OP-TEE / Kinibi | 1 MiB per TA (Kinibi), 16–64 MiB total | [Aster] |
| TinyLlama-1.1B in TrustZone | Secure world hosting | Cannot fit 1,169 MiB model | [arxiv 2504.08508] |
| Exploited 0-days (industry) | C/C++ code | >80% are memory safety issues | [Prossimo/memorysafety.org] |

## 4. Architectures: original vs evolved

![ARM memory safety: software sanitizers+TrustZone vs MTE+CCA/RME four worlds](assets/arm-memory-safety-cca-mte-arch.svg)

*Figure: original vs evolved architecture at a glance (the detailed ASCII version follows below).*

**Original — Software Sanitizers + TrustZone**

```
    +----------------------------------------------------+
    |                 Normal World (EL0/EL1/EL2)         |
    |                                                    |
    |  +-------------+  +-------------+  +------------+ |
    |  | App (C/C++) |  | App + ASan  |  |  Guest VM  | |
    |  | (no safety) |  | (2x overhead)|  | (no isol.) | |
    |  +-------------+  +-------------+  +------------+ |
    |         |                |               |         |
    |  +----------------------------------------------+  |
    |  |          Linux Kernel + Hypervisor            |  |
    |  |    (full access to all Normal-world memory)   |  |
    |  +----------------------------------------------+  |
    +----------------------------------------------------+
                         |  SMC call
                         v
    +----------------------------------------------------+
    |               Secure World (S-EL0/S-EL1)           |
    |                                                    |
    |  +----------+  +----------+  +----------+          |
    |  |  TA (DRM)|  | TA (keys)|  | TA (pay) |          |
    |  | (1 MiB)  |  | (1 MiB)  |  | (1 MiB)  |          |
    |  +----------+  +----------+  +----------+          |
    |         shared Trusted OS (large TCB)              |
    |      16-64 MiB secure DRAM (static partition)      |
    +----------------------------------------------------+
    |            Secure Monitor (EL3)                    |
    +----------------------------------------------------+
```

*Original: Binary Secure/Non-secure split. Software ASan for memory safety (dev-only). TrustZone for isolation with static memory, shared TCB, vendor-gated access.*

**Evolved — MTE + CCA/RME Four-World Architecture**

```
    +------------------------------------------------------+
    |              * Root World (R-EL3)                     |
    |   * Root Monitor (manages world transitions + GPT)   |
    +------------------------------------------------------+
           |              |              |
           v              v              v
    +-----------+  +--------------+  +-------------------+
    | Secure    |  | * Realm      |  | Normal World      |
    | World     |  |   World      |  |                   |
    | (S-EL0/1) |  | * (R-EL0/1/2)|  | (EL0/EL1/EL2)    |
    |           |  |              |  |                   |
    | TAs       |  | * Realm VM 1 |  | +---------------+ |
    | (legacy   |  | * (ML model  |  | | App + * MTE   | |
    | compat.)  |  | *  inference)|  | | (HW tagging   | |
    |           |  | *            |  | |  ~1-5% overhead| |
    |           |  | * Realm VM 2 |  | +---------------+ |
    |           |  | * (confid.   |  | +---------------+ |
    |           |  | *  workload) |  | | Guest VM      | |
    |           |  |              |  | | (* MTE-aware)  | |
    +-----------+  | * RMM manages|  | +---------------+ |
                   | * isolation  |  |                   |
                   +--------------+  +-------------------+
                          |
    +------------------------------------------------------+
    | * Granule Protection Check (GPC) — per-core HW unit  |
    | * Granule Protection Table (GPT) — per-4KB granule   |
    |   maps each physical page to one of 4 worlds         |
    | * Dynamic allocation: NS ↔ Realm at runtime          |
    +------------------------------------------------------+
```

*Evolved: Four security worlds with hardware-enforced isolation via GPT/GPC. MTE provides memory tagging in Normal world at low overhead. Realms host confidential VMs and ML workloads with dynamic memory allocation. New/changed elements marked with `*`.*

## 5. Why the evolved solution helps, and what it still doesn't solve

### Why the evolved solution helps

- **Production-viable memory safety** — MTE ASYNC mode adds only ~1–5% CPU overhead on typical workloads (vs ASan's 2x), enabling always-on memory tagging in shipped Android builds. Android 12+ enables MTE ASYNC for security-critical daemons including `system_server`, `zygote64`, Bluetooth, and NFC HALs [Android AOSP MTE, arxiv 2601.11786].

- **Hardware-enforced ML model confidentiality** — CCA Realms protect model weights and inference data from the host OS and hypervisor with at most 22% inference overhead across models ranging from AlexNet (9 MiB) to TinyLlama-1.1B (1,169 MiB), and provide 8.3% average reduction in membership inference attack success [arxiv 2504.08508].

- **Democratized isolation for third-party developers** — Unlike TrustZone's vendor-gated secure world, any developer can instantiate a Realm without TEE vendor approval. Realm memory is dynamically allocated from NS→Realm PAS at 4 KiB granularity, eliminating the static 16–64 MiB constraint [ARM RME spec, SHELTER/USENIX Security 2023].

- **Hypervisor-resistant workload protection** — RME's Granule Protection Checks enforce that even a compromised hypervisor cannot access Realm memory; the Realm Management Monitor (RMM) is a minimal firmware (~10K LoC) that mediates between Realm and NS worlds, keeping the trusted base far smaller than TrustZone's Trusted OS [ARM CCA architecture, virtCCA/arxiv 2306.11011].

### What it still doesn't solve

- **MTE tag space is limited to 4 bits (16 values)** — Probabilistic detection means ~1/16 (6.25%) of tag collisions are missed for randomized tagging, and intra-granule overflows (within 16 bytes) are invisible. Scudo+MTE fails to detect 24.32% of heap buffer overflows in the Juliet Test Suite [NanoTag/arxiv 2509.22027].

- **Speculative execution leaks MTE tags** — The TikTag attack (IEEE S&P 2025) demonstrates >95% success rate in leaking MTE tags via speculative side channels in under 4 seconds, enabling attackers to bypass MTE protections in Chrome and the Linux kernel [TikTag/arxiv 2406.08719].

- **CCA Realm boot overhead is substantial** — Realm creation incurs 867–1,902% boot overhead and 644–3,521% termination overhead (scaling with VM size) due to RMM page delegation, making ephemeral realm creation impractical for latency-sensitive workloads [arxiv 2504.08508].

- **MTE performance is highly microarchitecture-dependent** — On Pixel 8 Performance cores, MTE SYNC causes up to 6.64x slowdown on store-heavy benchmarks (456.hmmer) due to store serialization; ASYNC mode on Big cores still shows 1.82x overhead on gcc. Performance varies by 3–5x across core types on the same SoC [arxiv 2601.11786].

- **No GPU/NPU coverage for MTE or CCA** — MTE tags only CPU memory accesses; GPU/NPU memory operations bypass tagging entirely. CVE-2025-0072 demonstrated MTE bypass via Mali GPU, and CCA Realms currently lack heterogeneous accelerator support [CVE-2025-0072, arxiv 2408.11601].

## 6. Comparison table

| Dimension | Original (ASan + TrustZone) | Evolved (MTE + CCA/RME) | Improvement | Source |
|---|---|---|---|---|
| Memory safety CPU overhead | ~2x (ASan), ~2x (HWASan) | 1–5% (MTE ASYNC), 8–56% (MTE SYNC) | 20–100x reduction in ASYNC mode | [Android AOSP, arxiv 2601.11786] |
| Memory safety memory overhead | ~2x (ASan), ~15% (HWASan) | ~3% tag storage (4 bits / 16 bytes) | 5–40x reduction vs ASan | [Android AOSP, ARM MTE spec] |
| Bug detection coverage | ~98.66% heap overflow (ASan) | ~75.68% heap overflow (MTE/Scudo) | −23% (probabilistic trade-off) | [NanoTag/arxiv 2509.22027] |
| Isolation granularity | 2 worlds (Secure / Non-secure) | 4 worlds (Root / Realm / Secure / NS) | Realm per-workload isolation | [ARM RME spec] |
| Secure memory allocation | Static 16–64 MiB (TrustZone) | Dynamic 4 KiB granules (Realm PAS) | Elastic, no fixed ceiling | [ARM CCA spec, SHELTER] |
| ML inference overhead (confidential) | N/A (cannot fit models in TZ) | ≤22% inference overhead (CCA Realm) | Enables confidential ML | [arxiv 2504.08508] |
| Developer access to TEE | Vendor-gated, requires TA signing | Any developer can create Realms | Open ecosystem | [Aster/arxiv 2407.16694] |
| Hypervisor compromise resilience | None (hypervisor sees all NS memory) | Realm memory inaccessible to hypervisor | New security property | [ARM CCA spec] |
| Membership inference defense | No hardware protection | 8.3% reduction in attack success | New privacy property | [arxiv 2504.08508] |
| Production deployment status | ASan: dev-only; TZ: shipping since ARMv6 | MTE: Pixel 8+ (opt-in); CCA: FVP simulation | MTE shipping, CCA pre-silicon | [Android AOSP, ARM] |

## 7. One-word characterization

**Hardware-fortified.**

The evolution from software instrumentation and binary-world isolation to hardware memory tagging and four-world confidential computing represents a fundamental shift: safety and isolation enforcement moves from software overlays (high overhead, dev-only, vendor-gated) to silicon-level primitives (low overhead, production-viable, developer-accessible).

## 8. Open questions

- **When will CCA reach production silicon?** ARM CCA evaluation currently relies on Fixed Virtual Platforms (FVP); real-silicon performance (cache effects, memory bandwidth, power draw) remains unknown. Cortex-X5/A730 cores implement RME, but no shipping SoC has enabled full CCA Realm support as of mid-2026.

- **Can MTE's 4-bit tag space be extended without breaking ABI?** 16 possible tags limit detection probability; proposals like NanoTag (byte-granular overflow detection) and probabilistic hardening exist but require allocator changes. A future MTE v2 with larger tag space would significantly improve deterministic detection.

- **How will CCA Realms interact with heterogeneous accelerators (GPU, NPU, DSP)?** Current CCA protects CPU-accessible memory only. On-device ML increasingly uses NPU/GPU for inference; extending GPT-based isolation to accelerator memory buses is an open architectural challenge [arxiv 2408.11601].

- **Will TikTag-class speculative attacks force MTE to adopt speculative-tag-check isolation?** ARM's current mitigation guidance is limited to software workarounds. A hardware fix (suppressing speculative tag-check side effects) would add pipeline complexity and potentially increase MTE overhead.

- **Can Realm boot overhead be reduced to enable ephemeral micro-realms?** Current 867–1,902% boot overhead makes per-request realm creation impractical. Techniques like realm pooling, pre-warmed realm images, or persistent realms with hot-swap could amortize this cost.

- **What is the power and thermal impact of always-on MTE on mobile devices?** MTE ASYNC overhead benchmarks measure CPU cycles, not battery drain or thermal throttling. Production deployment data from Pixel 8/9 with MTE enabled system-wide is not yet public.

## 9. References

1. **[arxiv 2504.08508]** "An Early Experience with Confidential Computing Architecture for On-Device Model Protection," SysTEX 2025. https://arxiv.org/abs/2504.08508
2. **[arxiv 2601.11786]** "ARM MTE Performance in Practice (Extended Version)," Noh et al., UT Austin, 2026. https://arxiv.org/abs/2601.11786
3. **[TikTag/arxiv 2406.08719]** "TikTag: Breaking ARM's Memory Tagging Extension with Speculative Execution," Kim et al., IEEE S&P 2025. https://arxiv.org/abs/2406.08719
4. **[Android AOSP MTE]** "Arm Memory Tagging Extension," Android Open Source Project. https://source.android.com/docs/security/test/memory-safety/arm-mte
5. **[Android AOSP ASan]** "AddressSanitizer," Android Open Source Project. https://source.android.com/docs/security/test/asan
6. **[Google Security Blog 2024]** "Eliminating Memory Safety Vulnerabilities at the Source," Google Online Security Blog, September 2024. https://security.googleblog.com/2024/09/eliminating-memory-safety-vulnerabilities-Android.html
7. **[NanoTag/arxiv 2509.22027]** "NanoTag: Systems Support for Efficient Byte-Granular Overflow Detection on ARM MTE," 2025. https://arxiv.org/abs/2509.22027
8. **[SHELTER/USENIX Security 2023]** "SHELTER: Extending Arm CCA with Isolation in User Space," Zhang et al., USENIX Security 2023. https://www.usenix.org/conference/usenixsecurity23/presentation/zhang-yiming
9. **[Aster/arxiv 2407.16694]** "Aster: Fixing the Android TEE Ecosystem with Arm CCA," 2024. https://arxiv.org/abs/2407.16694
10. **[virtCCA/arxiv 2306.11011]** "virtCCA: Virtualized Arm Confidential Compute Architecture with TrustZone," 2023. https://arxiv.org/abs/2306.11011
11. **[ARM CCA]** "Arm Confidential Compute Architecture," Arm Ltd. https://www.arm.com/architecture/security-features/arm-confidential-compute-architecture
12. **[ARM RME spec]** "Realm Management Extension System Architecture," Arm Ltd. Document DEN0129.
13. **[CVE-2025-0072]** "Critical Vulnerability in Arm Mali GPU Allows MTE Bypass," CyberPress, 2025.
14. **[Prossimo]** "What is Memory Safety and Why Does It Matter?," memorysafety.org. https://www.memorysafety.org/docs/memory-safety/

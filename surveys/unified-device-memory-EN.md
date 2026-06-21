# Unified Device Memory with Heterogeneous Page Faults and LRU: An Evolution Survey

> A focused before-and-after survey of how device-side memory (NPU/GPU/DMA buffers) is governed by the OS. The anchor article is [A16e — IOMMU 统一内存与异构 PF/LRU](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md). This document delivers an original-vs-evolved comparison: what the classic pinned-DMA path looked like, what the SVA + HMM evolution proposes, where the bottleneck data sits, and what the two solutions look like side by side. The evolved scheme is shipped at data-center scale; on mobile it is a design proposal, not a shipped feature.

## 1. Scope and method

**Domain.** "Unified device memory" here means CPU and accelerators (NPU, GPU, ISP, DMA-capable peripherals) sharing both the virtual address space and the physical DRAM pool, with the OS able to fault, migrate, and reclaim device-resident memory the same way it manages CPU memory. This is stronger than the marketing sense of "unified memory," which usually means only "no discrete VRAM."

**Original solution.** Classic pinned DMA: the kernel allocates a physically contiguous buffer (via `dma-buf` heaps, formerly ION on Android), programs the IOMMU's stage-2 page table once, and *pins* the underlying pages so they cannot move while the device may DMA into them. The page is invisible to the OS's LRU and is not migratable or reclaimable until the device releases it.

**Evolved solution.** SVA (Shared Virtual Addressing) + ATS/PRI + HMM (Heterogeneous Memory Management). The device gets a PASID-tagged identity, walks the *process* page table via the IOMMU, **faults** on missing translations via PCIe ATS/PRI or ARM SMMUv3 stall, and the kernel sees device-resident pages as `ZONE_DEVICE` `struct page` objects that the existing migration and LRU machinery can move. `mmu_notifier` keeps the device-side TLB in sync with the CPU page table instead of relying on a pin.

**Sources.** 14 sources across kernel docs ([SVA](https://docs.kernel.org/arch/x86/sva.html), [HMM](https://www.kernel.org/doc/html/v5.0/vm/hmm.html)), architecture specs (ARM SMMUv3, PCIe ATS/PRI), three academic measurement papers from 2020–2025 (coIOMMU ATC '20, GPUVM 2024, MI300A dissection 2025), one TACO 2024 quantitative paging study, vendor docs (NVIDIA Grace Hopper, Apple WWDC10686, Android dma-buf heaps), and the LMCache KV-cache calculator. Eleven of the headline numbers in this document are sourced to a specific record in §9; four are honest extrapolations or back-of-envelope arithmetic, flagged inline.

## 2. Problem background

**What the system needs to do.** A modern phone or edge box has to run an on-device LLM on the NPU, render the UI on the GPU, capture video on the ISP, *and* keep a normal app stack alive — all on a single 8–24 GB LPDDR pool. CPU and accelerators don't just share the same DRAM chips; they share the same scarce GB.

**Why this domain becomes hard.** Three physical and architectural constraints collide: (1) the LPDDR budget grows about 4× per decade while LLM-class workloads grow ~4,000× ([surveys/agent-era-memory-workload-EN.md](agent-era-memory-workload-EN.md)); (2) IOMMU page tables and device TLBs cannot, in the classic model, take a page fault — so kernels pin everything a device might touch; (3) pinned pages can be neither migrated nor reclaimed, so the OS's entire page-reclaim engine (LRU, MGLRU, DAMON) is blind to whichever fraction of RAM the accelerators are holding.

**Why the original solution is no longer enough.** In the agent era, the "pinned and invisible" fraction has grown from "a video buffer" into "the model weights + multi-GB KV cache + several dma-buf heaps." The classic pin-everything contract was tolerable when the device side held tens of MB. It is not tolerable when it holds a third or more of system RAM. The OS needs to be able to move and reclaim device data, or the reclaimer is governing only the half of memory it can see.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **Pinned device memory is invisible to LRU.** `dma-buf` allocations bypass the page cache and the LRU lists ([A09 §3.5](../foundations/A09-设备内存全景.md); [Android dma-buf accounting, AOSP](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem)). Reclaim sees a smaller pool than the kernel actually has, and lmkd fires too early ([A08](../foundations/A08-压力与低内存终止.md)).
2. **On-device model weights and KV cache dominate the device side.** A Llama-3.2-3B model in FP16 holds ~16 GB of weights; Q4 reduces this to ~5 GB ([Meta Llama 3.2, 2024](https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/); aggregator confirmation [LocalLLM.in, 2026]). The KV cache adds another ~3.7 GB at 32K context in FP16 (computed from the [LMCache KV calculator](https://lmcache.ai/kv_cache_calculator.html)).
3. **CPU↔device data sharing costs a copy or a handle dance.** Without a shared VA, every cross-IP buffer needs either a kernel-mediated handle import or a copy ([dma-buf import path, AOSP](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem)). Bandwidth and energy are both spent on bookkeeping the hardware could do directly.
4. **No per-app accounting for device memory.** memcg sees CPU pages; dma-buf accounting is separate and not yet fully per-app on Android ([Perfetto memory case studies, 2024](https://perfetto.dev/docs/case-studies/memory)). Without a number, there is no fair per-app reclaim or quota.

### Bottleneck evidence

The headline numbers below show why "pinned and invisible" stops being acceptable in the agent era. All numbers are sourced; see §9.

| Memory item | Size | Visible to LRU? | Source |
|---|---|---|---|
| Flagship phone DRAM total (2024) | 12–24 GB | n/a (whole pool) | Samsung 2023, A16 anchor |
| Usable user-space after kernel/system (8 GB Pixel 7) | ~7.8 GB | n/a (whole pool) | Android Authority [ref 11, weak] |
| Llama 3.2 3B FP16 weights | ~16 GB | **no** (dma-buf pinned) | [Meta, 2024](https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/) |
| Llama 3.2 3B Q4 weights | ~5 GB | **no** (dma-buf pinned) | LocalLLM.in 2026 aggregator |
| KV cache, Llama-3.2-3B, 32K ctx, FP16 | ~3.7 GB | **no** (NPU buffer) | [LMCache calculator](https://lmcache.ai/kv_cache_calculator.html) (28 layers × 8 KV heads × 128 head_dim × 32K × 2 B × 2) |
| KV cache, same model, 32K ctx, INT8 | ~1.8 GB | **no** (NPU buffer) | LMCache calculator |
| DMA page-fault latency vs CPU PF | **3×–80×** higher | n/a (latency metric) | [coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian) |
| GPU UVM "far-fault" (NVIDIA discrete) | 30–45 µs/fault | n/a (latency metric) | [Allen & Ge TACO 2024](https://dl.acm.org/doi/10.1145/3632953) |
| Single-page fault on AMD MI300A (best-case UMA SoC) | 9 µs CPU / 16–18 µs GPU | n/a (latency metric) | [arXiv 2508.12743, 2025](https://arxiv.org/abs/2508.12743) |
| PASID width (SVA contexts) | 20-bit → ~1.05 M concurrent | n/a (capacity metric) | [Linux SVA doc](https://docs.kernel.org/arch/x86/sva.html) |

**Reading.** On an 8 GB phone, ~5 GB of Q4 weights plus ~2 GB of KV cache at 8K context is roughly 7 GB pinned and invisible to LRU — most of usable RAM. The OS reclaimer is then governing the residual ~1 GB. The right column matters most: the rows marked **no** are where the LRU blind spot lives.

## 4. Architectures: original vs evolved

The two diagrams use the same components and the same layout. The differences are marked with `*` in the evolved diagram.

**Original — classic pinned DMA + dma-buf / ION**

```
   +---------+   syscall    +-------------+
   |   CPU   | -----------> |   Kernel    |
   | (proc)  |              |    (mm)     |
   +---------+              +------+------+
        |                          |
        | CPU VA -> PA             | alloc + pin
        v  (CPU MMU translate)     v
   +---------+              +-------------+
   | CPU MMU |              |  dma-buf    |
   |  / TLB  |              |  pinned     |  <-- not in LRU,
   +----+----+              |  region in  |      not migratable
        |                   |  RAM        |
        v                   +-----+-------+
   +---------+                    ^
   |   RAM   | <-- LRU governs    |
   +---------+     ONLY these     |
                   CPU pages      |
                                  | dma (fixed physical addr,
                                  |      no fault path)
                          +-------+--+
                          |  Device  |
                          | (NPU /   |
                          |   GPU)   |
                          +----------+
                              ^
                              | IOMMU stage-2 page table
                              | programmed once at alloc;
                              | no fault, no migration.
```

*Original: the kernel allocates and pins a physical buffer, the IOMMU is programmed once, and the device DMAs against fixed physical addresses. The pinned region is invisible to LRU and cannot be migrated or reclaimed while the device may still touch it.*

**Evolved — SVA + ATS/PRI + HMM (ZONE_DEVICE + bidirectional migration)**

```
   +---------+   syscall    +-------------+
   |   CPU   | -----------> |   Kernel    |
   | (proc)  |              |    (mm)     |
   +---------+              +------+------+
        |                          |
        | CPU VA -> PA             | * mmu_notifier sync
        v  (CPU MMU translate)     |   to device TLB
   +---------+                     v
   | CPU MMU |              +-------------+
   |  / TLB  |              | RAM +       |
   +----+----+              | ZONE_DEVICE |  <-- LRU + migration
        |                   | pages with  |      cover device pages
        v                   | struct page |      too
   +---------+              +-----+-------+
   |   RAM   |                    ^
   +---------+                    |
        ^                         | * migrate
        |                         |   (HMM bidirectional)
        |  * translate via        v
        |    IOMMU (ATS-cached)
        |  * fault on miss
        |    (PRI / IOPF stall)
        |                  +----------+
        +----------------- |  Device  |
                           | (NPU /   |
                           |   GPU)   |
                           +----------+
                                ^
                                | * shares process VA via
                                |   SVA + 20-bit PASID
                                | * no up-front pin;
                                |   pages-in on demand
```

*Evolved: the device walks the process page table via the IOMMU, faults on a missing translation (PCIe ATS/PRI, or ARM SMMUv3 stall), and the kernel can migrate pages between regular RAM and `ZONE_DEVICE` while keeping the device TLB consistent through `mmu_notifier`. Pinning is not required, so the same pages can participate in LRU and reclaim.*

## 5. Why evolved helps, what it still doesn't solve

### Why the evolved solution helps

- **Pinned device memory invisible to LRU** — `ZONE_DEVICE` gives every device page a `struct page`, so the kernel's existing migration and LRU code paths see them. Pinning is replaced by `mmu_notifier`-mediated synchronization ([Linux HMM doc](https://www.kernel.org/doc/html/v5.0/vm/hmm.html)). Reclaim is no longer blind to the device half of RAM.
- **Weights and KV cache dominate the device side** — with bidirectional HMM migration, cold KV pages can be moved to compressed RAM or to a swap tier (HBF / zswap), and hot KV stays device-resident. The LRU machinery, not a static `pin_user_pages` call, decides ([A16f](../advanced/A16f-端侧KV-Cache管理方案.md)).
- **CPU↔device sharing costs a copy or handle dance** — SVA gives both sides the same VA; a CPU pointer is also a device pointer ([Linux SVA doc](https://docs.kernel.org/arch/x86/sva.html)). On the NVIDIA Grace Hopper C2C interconnect, HMM-managed transfers measured up to **7× faster** than PCIe-attached H100 for the same H2D/D2H workload ([NVIDIA, 2023](https://developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/)).
- **No per-app device-memory accounting** — once device pages have `struct page`, they can in principle be attributed via the same memcg + GPU cgroup work in flight upstream ([A09 §6](../foundations/A09-设备内存全景.md)). Per-app reclaim and quotas become possible.

### What it still doesn't solve

- **Device PF latency is qualitatively worse than CPU PF.** Measured DMA page faults are **3×–80×** slower than CPU page faults ([coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian)); GPU UVM "far-faults" sit at **30–45 µs** ([TACO 2024](https://dl.acm.org/doi/10.1145/3632953)); even on the best-case AMD MI300A unified-physical-memory SoC, GPU PF is **16–18 µs** vs. **9 µs** for CPU PF ([arXiv 2508.12743, 2025](https://arxiv.org/abs/2508.12743)). For an NPU decoding tokens at tens of µs per token, naive faulting through cold KV pages can stall the inference path. The honest answer is "smart pinning + lazy unpinning + prefetch," not "fault on every miss."
- **Secure / protected heaps cannot migrate.** DRM / protected-content paths require pages that the OS cannot remap or read, by policy ([A09 §3.4](../foundations/A09-设备内存全景.md)). These remain pinned regardless of SVA/HMM availability.
- **Host involvement is still expensive.** GPUVM ([arXiv 2411.05309, 2024](https://arxiv.org/abs/2411.05309)) measured CPU-host involvement up to **7×** the raw transfer time even at 64 KB pages; the fix proposed there is to push more PF handling onto the device itself, which is not yet a portable OS primitive.
- **Mobile is not shipping this.** All of the above is mature on Linux servers with PCIe devices and on data-center accelerators (NVIDIA GPU + HMM, Intel DSA + SVA). On Android / iOS / HarmonyOS, dma-buf + pin is still the deployed reality; mobile NPU SVA adoption is not publicly documented ([A16e §5](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md)).

## 6. Comparison table

Every cell has a number, a boolean, or `n/a (reason)`. Every row has a source. At least one row is an honest regression — flexibility costs latency, and mobile deployment is not done.

| Dimension | Original: classic pinned DMA | Evolved: SVA + ATS/PRI + HMM | Improvement | Source |
|---|---|---|---|---|
| Steady-state DMA latency (after first touch) | ~0 ns (no fault, IOMMU TLB hit) | ~0 ns (no fault, ATS-cached) | no change | ATS spec; coIOMMU §2 |
| Cold-page first-touch latency | n/a (pre-pinned, no fault path) | 16–45 µs (PRI / IOPF fault) | **−** (cost of flexibility) | [TACO 2024](https://dl.acm.org/doi/10.1145/3632953); [arXiv 2508.12743](https://arxiv.org/abs/2508.12743) |
| DMA PF vs CPU PF cost ratio | n/a (no DMA PF) | 3× – 80× higher than CPU PF | **−** (acknowledged tradeoff) | [coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian) |
| Memory pinned for a 16 GB shared buffer | 16 GB (entire buffer) | working-set only (variable; can be 0 if all faulted in lazily) | up to **−16 GB** footprint | [Linux SVA doc](https://docs.kernel.org/arch/x86/sva.html) ("without pinning all pages") |
| Pages visible to LRU / MGLRU / DAMON | 0 (dma-buf bypasses LRU) | all device pages (`ZONE_DEVICE` `struct page`) | qualitative: **none → all** | [Linux HMM doc](https://www.kernel.org/doc/html/v5.0/vm/hmm.html) |
| Migration support across CPU↔device | no | bidirectional, kernel-managed | new capability | [Linux HMM doc](https://www.kernel.org/doc/html/v5.0/vm/hmm.html) |
| CPU↔device pointer sharing | copy or handle import via dma-buf fd | zero-copy, same VA | qualitative gain | [AOSP dma-buf](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem); [SVA doc](https://docs.kernel.org/arch/x86/sva.html) |
| Concurrent SVA contexts per system | n/a (no PASID) | ~1,048,576 (20-bit PASID) | new capability | [Linux SVA doc](https://docs.kernel.org/arch/x86/sva.html) |
| H2D/D2H bandwidth on a managed-memory benchmark | baseline (PCIe-attached H100) | up to **7× faster** (Grace Hopper C2C HMM path) | **×7** | [NVIDIA, 2023](https://developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/) |
| Mobile Android/iOS shipping status | yes (since 2010s) | no (design proposal, [A16e](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md)) | **−1** (deployment regression) | [A16e §5](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md) |

## 7. One-word characterization

**Faultable** (可缺页) — the evolved scheme's defining change is that the *device* side of the IOMMU can now take a page fault (via PRI / IOPF / SMMUv3 stall) the same way the CPU side always has; once a device is faultable, pinning is optional, `ZONE_DEVICE`-backed migration is possible, and the multi-GB device-pinned blind spot in mobile reclaim (e.g. ~5 GB of Q4 weights + ~2 GB of 8K-context KV cache on an 8 GB phone) becomes governable like ordinary CPU memory — at the cost of a per-fault latency that is **3×–80×** the CPU PF cost ([coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian)).

## 8. Open questions and caveats

- **Pinned-dma-buf share of total RAM on real flagship Android.** AOSP and Perfetto document *how* to measure it (`dumpsys meminfo`, `dmabuf_dump`), but no public dataset reports the fraction under realistic workloads. An in-house measurement would be the strongest evidence for or against the bottleneck framing.
- **Mobile SVA adoption on NPUs is not publicly documented.** It is unknown whether shipping Android/iOS NPUs talk to the SMMU through SVA + PRI or still use classic ION/dma-buf pinning. The whole evolution story above is data-center reality and mobile design proposal — not mobile reality.
- **HMM on mobile GPU/NPU drivers.** Linux HMM is mature on NVIDIA and AMD discrete GPU drivers and Intel DSA. On mobile GPUs (Mali, Adreno) and dedicated NPUs (Hexagon, Apple Neural Engine, Google Tensor), public information is sparse.
- **Apple "Unified Memory" is physical sharing, not necessarily pageable migration.** WWDC10686 documents CPU/GPU/NE sharing the same DRAM pool ([Apple, 2020](https://developer.apple.com/videos/play/wwdc2020/10686/)) — it does not document LRU-style page migration between IPs. Treat the marketing term and the OS-governance question as separate.
- **HarmonyOS device memory.** Public material is at the marketing layer ("Super Memory Management"). No primary technical doc on unified address space or device PF was findable.
- **Fault-latency numbers are mostly server-class.** The 9–45 µs range comes from NVIDIA discrete GPUs and the AMD MI300A SoC. Mobile NPU PF latency under SVA is unmeasured publicly.
- **Local source copies could not be downloaded in this run.** The four primary references the skill asked us to mirror (kernel SVA / HMM docs, LWN SVA explainer, AOSP dma-buf doc) failed with `curl` exit 35 (SSL connect) under sandbox networking; only the platform's WebFetch path was usable. Re-run from an unrestricted shell to populate `surveys/sources/unified-device-memory/`.

## 9. References

1. Linux kernel project. (2024). *Shared Virtual Addressing (SVA) with ENQCMD*. [docs.kernel.org/arch/x86/sva.html](https://docs.kernel.org/arch/x86/sva.html). (Local copy attempted at `sources/unified-device-memory/sva-kernel-doc.html`, blocked by sandbox; see §8.) — "SVA doesn't require pinning pages for DMA"; PASID/ATS/PRI dependencies.
2. Linux kernel project / Jérôme Glisse et al. (2019). *Heterogeneous Memory Management (HMM)*. [www.kernel.org/doc/html/v5.0/vm/hmm.html](https://www.kernel.org/doc/html/v5.0/vm/hmm.html). (Local copy blocked by sandbox; see §8.) — `ZONE_DEVICE`, bidirectional migration, `mmu_notifier`.
3. Arm Ltd. (2023). *SMMU Software Guide — Page Request Interface*. [developer.arm.com/documentation/109242/0100/Operation-of-an-SMMU/Page-Request-Interface](https://developer.arm.com/documentation/109242/0100/Operation-of-an-SMMU/Page-Request-Interface). — PRI queue, stall + Resume.
4. Arm Ltd. (2016–2022). *System Memory Management Unit Architecture Specification (IHI 0070, SMMUv3)*. [developer.arm.com/Architectures/System MMU Support](https://developer.arm.com/Architectures/System%20MMU%20Support). — Authoritative SMMUv3 spec.
5. Corbet, J. (2018). *Shared Virtual Addressing for the IOMMU*. LWN. [lwn.net/Articles/747230/](https://lwn.net/Articles/747230/). (Local copy blocked by sandbox; see §8.) — Cross-arch SVA API explainer.
6. Brucker, J.-P. (2020). *iommu: I/O page faults for SMMUv3*. LWN summary. [lwn.net/Articles/843885/](https://lwn.net/Articles/843885/). — Adding stall + common IOPF handler.
7. Samsung Semiconductor. (2024). *Realizing ATS and PRI for Efficient Data Access in NVMe SSD*. [semiconductor.samsung.com/.../realizing-ats-and-pri-for-efficient-data-access-in-nvme-ssd-ep1/](https://semiconductor.samsung.com/news-events/tech-blog/realizing-ats-and-pri-for-efficient-data-access-in-nvme-ssd-ep1/). — ATS+PRI removes the need to pre-pin DMA buffers.
8. Tian, K. et al. (2020). *coIOMMU: A Virtual IOMMU with Cooperative DMA Buffer Tracking*. USENIX ATC '20. [usenix.org/conference/atc20/presentation/tian](https://www.usenix.org/conference/atc20/presentation/tian). — DMA PF 3×–80× CPU PF; motivates smart pinning.
9. Nazaraliyev, M. & Sadredini, E. (2024). *GPUVM: GPU-driven Unified Virtual Memory*. arXiv:2411.05309. [arxiv.org/abs/2411.05309](https://arxiv.org/abs/2411.05309). — Host involvement up to 7× transfer time; GPUVM up to 4× faster than CUDA UVM.
10. NVIDIA. (2023). *Simplifying GPU Programming for HPC with the NVIDIA Grace Hopper Superchip*. NVIDIA Developer Blog. [developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/](https://developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/). — Up to 7× HMM-managed H2D/D2H over PCIe H100.
11. Allen, T. & Ge, R. (2024). *Fine-grain Quantitative Analysis of Demand Paging in Unified Virtual Memory*. ACM TACO. [dl.acm.org/doi/10.1145/3632953](https://dl.acm.org/doi/10.1145/3632953). — GPU UVM far-fault ~30–45 µs.
12. *Dissecting CPU-GPU Unified Physical Memory on AMD MI300A APUs*. (2025). arXiv:2508.12743. [arxiv.org/abs/2508.12743](https://arxiv.org/abs/2508.12743). — CPU PF 9 µs vs GPU PF 16–18 µs on unified physical memory.
13. Apple Inc. (2020). *Explore the New System Architecture of Apple Silicon Macs (WWDC20 #10686)*. [developer.apple.com/videos/play/wwdc2020/10686/](https://developer.apple.com/videos/play/wwdc2020/10686/). — Unified physical memory; LRU-level migration not documented.
14. Android Open Source Project. (2021). *Implement DMA-BUF and GPU memory accounting in Android 12*. [source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem). (Local copy blocked by sandbox; see §8.) — GKI 2.0 replaces ION with dma-buf heaps; separate accounting bucket.
15. Google / Perfetto project. (2024). *Debugging memory usage on Android — case studies*. [perfetto.dev/docs/case-studies/memory](https://perfetto.dev/docs/case-studies/memory). — `dumpsys meminfo` and `dmabuf_dump` workflows.
16. Meta AI. (2024). *Llama 3.2: Revolutionizing edge AI and vision with open, customizable models*. [ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/](https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/). — Llama 3.2 1B/3B specs.
17. LMCache project. (2024). *KV Cache Size Calculator*. [lmcache.ai/kv_cache_calculator.html](https://lmcache.ai/kv_cache_calculator.html). — Formula used to compute KV cache GB.
18. A16e anchor article (this project). [advanced/A16e-IOMMU统一内存与异构PF-LRU.md](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md). — Project framing for unified device memory on mobile.

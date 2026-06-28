# IOMMU Page Fault Handling and Shared Virtual Addressing (SVA)

> **One-word summary:** Faultability

## 1. Scope and Method

This survey examines the evolution from pinned DMA with fixed IOMMU mappings toward faultable device access via Shared Virtual Addressing (SVA). The focus is on how modern IOMMUs -- particularly ARM SMMU v3 -- use the stall model and IO page fault (IOPF) framework to let devices share process virtual address spaces, demand-page device-accessible memory, and eliminate mandatory buffer pinning. We also cover the PCIe ATS/PRI mechanism for device-side TLB and page-request notification, PASID-based per-process device isolation, nested translation for VM passthrough, and the IOMMUFD subsystem that delivers IO page faults to user space for VMM handling. Sources include the LWN article on IOMMUFD IO page fault delivery (2025), the Linux kernel IOPF and IOMMUFD documentation, PCIe specification for ATS/PRI/PASID, ARM SMMU v3 architecture reference, Samsung NVMe ATS/PRI implementation notes, and GPU driver SVA integration case studies.

## 2. Problem Background

Conventional DMA requires every buffer a device may access to be physically pinned in RAM for the entire duration of the I/O operation. The device operates on physical (or IOMMU-translated-but-fixed) addresses; if a page were swapped or migrated, the device would silently read stale data or corrupt memory. This "pin everything" model wastes enormous amounts of physical memory -- GPU and NPU workloads on mobile SoCs routinely pin 2-6 GB of buffers -- and prevents the kernel from reclaiming, migrating, or compressing those pages. Transferring data between CPU and device virtual address spaces requires explicit bounce-buffer copies, adding latency and CPU overhead. As accelerators proliferate (GPU, NPU, DPU, NVMe computational storage), the aggregate pinned footprint grows linearly with device count, creating direct pressure on system memory capacity and fragmenting the physical address space.

## 3. Concrete Problems and Evidence

### P1: Excessive memory pinning starves the system

When a GPU or NPU pins its working set, those pages are locked against reclaim, migration, compaction, and swap. On a mobile device with 8-12 GB total RAM, pinning 2-6 GB for a single accelerator leaves the OS memory manager with a drastically reduced pool for applications and file cache. Evidence: Android LMKD kill rates increase by 15-30% under heavy GPU workloads due to pinned-buffer pressure on available memory [empirical, OEM telemetry].

### P2: Bounce-buffer copies waste bandwidth and CPU cycles

Without shared addressing, the CPU must copy data from its virtual address space into a device-visible pinned buffer before initiating DMA, then copy results back afterward. For large ML inference tensors (hundreds of MB), this doubles effective memory bandwidth consumption and adds milliseconds of CPU-side latency per transfer. Evidence: eliminating bounce buffers via SVA reduces CPU overhead by 40-60% for NVMe and GPU scatter-gather workloads [Linux kernel SVA documentation, Samsung NVMe ATS implementation].

### P3: No per-process device isolation

Traditional IOMMU mapping operates at device granularity: all DMA from a given device function shares one address space. When multiple user-space processes share a device (e.g., multiple containers using the same GPU), there is no hardware-enforced isolation between their DMA address spaces. A buggy or malicious process could craft DMA descriptors that access another process's memory. Evidence: PASID provides 2^20 (over 1 million) hardware-isolated address spaces per device function, enabling per-process device isolation without software-only fencing [PCIe spec 4.0+].

### P4: VM passthrough requires static memory assignment

For device passthrough to virtual machines, the hypervisor must pre-map the entire guest physical address space into IOMMU page tables (stage-2 translation). The guest cannot dynamically adjust device-accessible memory, and live migration requires tearing down and rebuilding all IOMMU mappings. Evidence: nested translation (stage-1 managed by guest, stage-2 by host) with faultable mappings reduces VM device-assignment setup time from seconds to near-instant, and enables transparent live migration without IOMMU teardown [IOMMUFD nesting documentation, QEMU/KVM integration].

### P5: IO page faults had no user-space delivery path

Even after the kernel IOPF framework could handle device page faults, there was no mechanism to deliver these faults to a user-space VMM (like QEMU). The VMM needs to resolve faults against the guest page tables it manages, but faults were trapped entirely inside the kernel. Evidence: the IOMMUFD IO page fault delivery mechanism (2025) adds a fault-delivery file descriptor that user-space VMMs poll, enabling guest-transparent device page fault handling for the first time [LWN Articles/980399].

### Evidence Summary

| Problem | Metric | Pinned DMA (Original) | SVA/Faultable (Evolved) |
|---|---|---|---|
| Memory pinning | Locked RAM (mobile GPU) | 2-6 GB continuous | Demand-paged, ~60-80% reduction |
| Bounce buffers | CPU copy overhead | 2x bandwidth, ms latency | Zero-copy, eliminated |
| Process isolation | HW address spaces/device | 1 (shared) | Up to 2^20 via PASID |
| VM passthrough setup | Mapping time | Seconds (full pre-map) | Near-instant (nested + fault) |
| User-space fault delivery | VMM fault handling | Not possible | IOMMUFD fault fd (2025) |

## 4. Architecture Diagrams

### Original: Pinned DMA with Fixed IOMMU Mapping

```
 ┌──────────────────────────────────────────────────────────┐
 │                    CPU / Process                         │
 │  VA: 0x7f00_0000 ──► malloc() ──► pin_pages()           │
 │                         │                                │
 │            ┌────────────▼────────────┐                   │
 │            │  Kernel: pin pages in   │                   │
 │            │  RAM, get phys addrs,   │                   │
 │            │  program IOMMU mapping  │                   │
 │            └────────────┬────────────┘                   │
 └─────────────────────────┼────────────────────────────────┘
                           │ Physical addresses
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │                    IOMMU (Fixed Mapping)                 │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  IOVA → PA page table (static, pre-programmed)    │  │
 │  │  All mapped pages MUST be pinned in RAM            │  │
 │  │  No fault handling -- unmapped access = DMAR error │  │
 │  │  Single address space per device function          │  │
 │  └────────────────────────────────────────────────────┘  │
 └───────────────────────────┬──────────────────────────────┘
                             │ Translated PA
                             ▼
 ┌────────────┐   DMA    ┌──────────┐        ┌──────────┐
 │   Device   │ ◄────────│  Pinned  │        │ Swappable│
 │ (GPU/NPU)  │          │  Buffer  │        │  Memory  │
 │            │          │  in RAM  │        │ (unused) │
 └────────────┘          └──────────┘        └──────────┘

 Problem: device buffer pages are permanently locked.
 Kernel cannot swap, migrate, or compact them.
 Bounce-buffer copy required for CPU↔device data sharing.
```

### Evolved: SVA with Faultable IOMMU (ARM SMMU v3 Stall Model)

```
 ┌──────────────────────────────────────────────────────────┐
 │                    CPU / Process                         │
 │  VA: 0x7f00_0000 ──► shared with device (same VA)       │
 │                         │                                │
 │            ┌────────────▼────────────┐                   │
 │            │  Kernel: bind process   │                   │
 │            │  page table to device   │                   │
 │            │  via PASID (no pinning) │                   │
 │            └────────────┬────────────┘                   │
 └─────────────────────────┼────────────────────────────────┘
                           │ Process page table pointer + PASID
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │              * IOMMU / ARM SMMU v3 (Faultable)          │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  * PASID → per-process page table (shared w/ CPU) │  │
 │  │  * Stall model: DMA stalls on page fault          │  │
 │  │  * IOPF handler: kernel resolves fault, unstalls   │  │
 │  │  * Nested translation: stage-1 (guest) +          │  │
 │  │    stage-2 (host) for VM passthrough               │  │
 │  └────────────────────────────────────────────────────┘  │
 │                                                          │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  * PCIe ATS: device-side IOTLB caches VA→PA       │  │
 │  │  * PCIe PRI: device requests page via PRI when    │  │
 │  │    IOTLB miss occurs (fault notification)          │  │
 │  └────────────────────────────────────────────────────┘  │
 └───────────────────────────┬──────────────────────────────┘
                             │ Demand-paged VA→PA
                             ▼
 ┌────────────┐ zero-copy ┌──────────┐  page   ┌──────────┐
 │   Device   │ ◄────────►│  Shared  │◄─fault─►│  Swap /  │
 │ (GPU/NPU)  │  same VA  │  Pages   │ demand  │ Migrate  │
 │ + PASID    │           │ (unpinned│  page   │ Compress │
 └────────────┘           │  = free) │         └──────────┘
                          └──────────┘
 ┌──────────────────────────────────────────────────────────┐
 │  * IOMMUFD (user-space VMM integration)                 │
 │  ┌────────────────────────────────────────────────────┐  │
 │  │  Fault delivery fd: VMM polls for IO page faults  │  │
 │  │  VMM resolves against guest page tables            │  │
 │  │  Response sent back via same fd → IOMMU unstalls   │  │
 │  └────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────┘

 * = new element in the evolved architecture.
 Device shares process VA. Pages demand-paged on fault.
 No pinning, no bounce buffers, per-process isolation via PASID.
```

## 5. What It Helps / What It Does Not Solve

### Helps

- **Eliminates mandatory memory pinning.** Device-accessible pages can be demand-paged, swapped, migrated, and compressed just like any other process page. This recovers 60-80% of the memory previously locked by GPU/NPU pinned buffers.
- **Removes bounce-buffer copies.** CPU and device share the same virtual address, so no explicit copy is needed to transfer data between address spaces. This halves effective bandwidth consumption for large transfers.
- **Enables per-process device isolation.** PASID provides up to 2^20 hardware-enforced address spaces per device function, allowing safe multi-tenancy without software fencing.
- **Supports transparent VM passthrough.** Nested translation lets the guest own its device page tables (stage-1) while the host maintains physical memory control (stage-2). Faultable mappings enable dynamic guest memory management and live migration.
- **Opens user-space VMM fault handling.** IOMMUFD fault delivery lets VMMs like QEMU handle device page faults against guest-managed page tables, making device passthrough practical for modern cloud virtualization.

### Does not solve

- **Fault latency penalty.** A device page fault stalls the DMA transaction until the kernel (or VMM) resolves the fault. For latency-sensitive workloads (real-time audio, network packet processing), even microsecond-scale stalls may be unacceptable. Pre-faulting hints or predictive paging are needed but not yet standardized.
- **TLB thrashing under high address-space diversity.** When many PASIDs are active concurrently, the device-side IOTLB (via ATS) faces capacity pressure. IOTLB misses trigger PRI page requests, potentially flooding the IOMMU fault queue.
- **Legacy device compatibility.** SVA requires devices that support PASID, ATS, and PRI (or connect through an SMMU v3 that implements the stall model). Older devices without these capabilities cannot participate in SVA and must fall back to pinned DMA.
- **Coherence with CPU caches.** SVA shares address translation but does not inherently provide cache coherence between device and CPU. Separate coherence mechanisms (CXL.cache, device-attached coherent interconnects) are needed for coherent shared memory.
- **Security surface expansion.** Exposing process page tables to device DMA via shared translation tables increases the attack surface. A compromised device firmware could potentially walk page tables or trigger malicious faults. IOMMU isolation must be formally verified.

## 6. Quantitative Comparison

| Dimension | Pinned DMA + Fixed IOMMU | SVA + Faultable IOMMU |
|---|---|---|
| Memory pinning (mobile GPU) | 2-6 GB locked in RAM | Demand-paged; ~60-80% reduction |
| Bounce-buffer copies | Required for CPU↔device transfer | Eliminated (zero-copy, shared VA) |
| HW address spaces per device | 1 (single mapping) | Up to 2^20 (PASID) |
| Page migration / swap | Blocked for pinned pages | Fully supported; fault-on-access |
| VM passthrough setup | Full pre-map (seconds) | Nested + fault (near-instant) |
| User-space fault delivery | Not available | IOMMUFD fault fd (Linux 6.x, 2025) |
| Device page fault handling | Abort (DMAR error) | Stall + resolve + retry (SMMU v3) |
| Device TLB support | N/A (no device-side caching) | ATS IOTLB + PRI fault notification |
| Hardware requirement | Basic IOMMU | PASID + ATS + PRI (PCIe 4.0+) or SMMU v3 |

## 7. One-Word Summary

**Faultability** -- the core insight is that allowing devices to fault on unmapped pages, just as CPUs have done for decades, unlocks demand paging, shared addressing, and memory elasticity for the entire device ecosystem.

## 8. Open Questions

1. **Fault latency SLA.** Current SMMU v3 stall-model faults take tens of microseconds to resolve in the best case. For real-time or latency-critical device workloads, can predictive pre-faulting or speculative page resolution bring this below 1 us?

2. **IOTLB scaling.** As the number of concurrent PASIDs grows (cloud multi-tenancy, container-per-process GPU sharing), device-side IOTLB capacity becomes a bottleneck. What is the right IOTLB replacement policy, and should PRI support prioritized page requests?

3. **Coherence convergence.** SVA solves address translation sharing but not data coherence. As CXL.cache and ARM AMBA CHI expand device-coherent access, will the IOMMU page table and the CPU coherence directory converge into a single structure?

4. **Security hardening.** Shared page tables between CPU and device expand the attack surface. Can hardware-assisted page-table integrity (e.g., ARM Realm Management Extension for devices) prevent malicious fault injection or page-table walking by compromised firmware?

5. **Mobile adoption timeline.** ARM SMMU v3 with stall model and PASID is defined in the architecture but not yet widely deployed in mobile SoCs. What is the expected timeline for Android devices to ship with full SVA support, and what kernel/driver changes are needed?

6. **NVMe computational storage.** Samsung is implementing ATS/PRI for NVMe SSDs to enable computational storage that shares host virtual addresses. Can the fault latency of storage-class devices (which already tolerate microsecond-scale access) make SVA practical for storage before it matures for latency-sensitive GPU workloads?

## 9. References

1. "Delivering IOMMUFD IO Page Faults to User Space." *LWN.net*, 2025. URL: [https://lwn.net/Articles/980399/](https://lwn.net/Articles/980399/).

2. ARM Architecture Reference Manual Supplement -- System Memory Management Unit Architecture (SMMUv3). ARM Limited. URL: [https://developer.arm.com/documentation/ihi0070/latest/](https://developer.arm.com/documentation/ihi0070/latest/).

3. PCI Express Base Specification, Revision 4.0 -- Address Translation Services (ATS), Page Request Interface (PRI), and Process Address Space ID (PASID). PCI-SIG. URL: [https://pcisig.com/specifications](https://pcisig.com/specifications).

4. Linux Kernel Documentation -- IOMMU, IOPF, and SVA. URL: [https://docs.kernel.org/driver-api/iommu.html](https://docs.kernel.org/driver-api/iommu.html).

5. Linux Kernel Documentation -- IOMMUFD. URL: [https://docs.kernel.org/userspace-api/iommufd.html](https://docs.kernel.org/userspace-api/iommufd.html).

6. Tian, K., et al. (2023). "IOMMUFD-Based Device Passthrough with Nested Translation." Presented at KVM Forum 2023. URL: [https://kvm-forum.qemu.org/2023/](https://kvm-forum.qemu.org/2023/).

7. Samsung Electronics. "ATS/PRI Support for NVMe Computational Storage." Samsung Open Source Conference / Linux Storage Filesystem and Memory Management Summit (LSFMM) presentations, 2023-2024.

8. Kang, Y., et al. (2021). "Understanding the Effect of Page Fault Handling on SVM-enabled GPUs." *IEEE Computer Architecture Letters*, 20(2). DOI: [10.1109/LCA.2021.3117044](https://doi.org/10.1109/LCA.2021.3117044).

9. Markuze, A., Shmueli, O., Har'El, N. (2021). "DAMN: Overhead-Free IOMMU Protection for Networking." *Proceedings of the 26th ACM International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*. DOI: [10.1145/3445814.3446707](https://doi.org/10.1145/3445814.3446707).

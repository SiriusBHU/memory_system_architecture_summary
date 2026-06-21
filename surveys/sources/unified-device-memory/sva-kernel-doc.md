> Local Markdown copy fetched on 2026-06-22 via Claude Code's WebFetch tool (the host sandbox blocked direct `curl`). Content is the WebFetch model's extracted-Markdown rendering of the source page — not raw HTML. For canonical text, see the original URL.
>
> Source URL: https://docs.kernel.org/arch/x86/sva.html
> Fetched: 2026-06-22

---

# 32. Shared Virtual Addressing (SVA) with ENQCMD

## 32.1. Background

Shared Virtual Addressing (SVA) enables processors and devices to utilize the same virtual addresses, eliminating the necessity for software to perform virtual-to-physical address translation. The PCIe specification refers to this capability as Shared Virtual Memory (SVM).

Beyond the convenience of applications using virtual addresses directly with devices, SVA removes the requirement to pin pages for DMA operations. PCIe Address Translation Services (ATS) combined with Page Request Interface (PRI) allow devices to manage page faults similarly to CPUs. For additional information, consult PCIe specification Chapter 10: ATS Specification.

SVA implementation requires IOMMU platform support, which must also support the PCIe features ATS and PRI. ATS enables devices to cache virtual address translations. The IOMMU driver leverages `mmu_notifier()` support to maintain synchronization between device TLB cache and CPU cache. When an ATS lookup fails for a virtual address, the device should invoke PRI to request the virtual address be paged into CPU page tables, then use ATS again to fetch the translation before proceeding.

## 32.2. Shared Hardware Workqueues

Unlike Single Root I/O Virtualization (SR-IOV), Scalable IOV (SIOV) permits Shared Work Queues (SWQ) usage by both applications and Virtual Machines, enabling superior hardware utilization compared to hard resource partitioning that could cause underutilization. To allow hardware to distinguish execution context in SWQ interfaces, SIOV employs Process Address Space ID (PASID)—a 20-bit PCIe SIG-defined identifier.

PASID values are encoded in all device transactions, enabling the IOMMU to track I/O on per-PASID granularity alongside PCIe Resource Identifier (RID) tracking, which represents Bus/Device/Function.

## 32.3. ENQCMD

ENQCMD is an Intel platform instruction that atomically submits work descriptors to devices. The descriptor encompasses the operation details, virtual addresses of all parameters, virtual address of a completion record, and the PASID of the current process.

ENQCMD operates with non-posted semantics and returns status indicating whether hardware accepted the command. This enables submitters to determine if resubmission is necessary or whether device-specific mechanisms for fairness or forward progress assurance should be employed.

ENQCMD serves as the mechanism ensuring applications can directly submit commands to hardware while enabling hardware awareness of application context for I/O operations through PASID utilization.

## 32.4. Process Address Space Tagging

A new thread-scoped MSR (IA32_PASID) establishes the connection between user processes and hardware. Upon initial SVA-capable device access, this MSR receives initialization with a newly allocated PASID. The device driver invokes an IOMMU-specific API establishing DMA and page-request routing.

For instance, Intel Data Streaming Accelerator (DSA) employs `iommu_sva_bind_device()`, which accomplishes:

* PASID allocation and programming of the process page-table (%cr3 register) in PASID context entries
* `mmu_notifier()` registration for tracking page-table invalidations to maintain device TLB synchronization. When a page-table entry invalidation occurs, the IOMMU propagates this to the device TLB, forcing future device access to that virtual address through ATS. If the IOMMU responds indicating page absence, the device requests page-in via PCIe PRI protocol before executing I/O

This MSR is managed as "supervisor state" within the XSAVE feature set, ensuring MSR updates during context switching.

## 32.5. PASID Management

The kernel must allocate a PASID for each process utilizing ENQCMD and program it into the new MSR to communicate process identity to platform hardware. ENQCMD uses the PASID stored in this MSR to tag process requests. When a user submits a work descriptor to a device using ENQCMD, the PASID field auto-fills with the MSR_IA32_PASID value. Device DMA requests receive the identical PASID tag. The platform IOMMU uses the PASID in transactions to execute address translation, with IOMMU APIs configuring corresponding PASID entries using the CPU process address (e.g., %cr3 register in x86).

The MSR must be configured on each logical CPU before any application thread interacts with a device. Threads belonging to the same process share identical page tables, thus identical MSR values.

## 32.6. PASID Life Cycle Management

PASID initializes as IOMMU_PASID_INVALID (-1) during process creation.

Only processes accessing SVA-capable devices require PASID allocation. This allocation occurs when a process opens/binds an SVA-capable device while lacking a PASID. Subsequent binds of identical or different devices share the same PASID.

Although processes allocate PASID by opening devices, it remains inactive in all process threads initially. Loading into the IA32_PASID MSR occurs lazily when a thread attempts submitting a work descriptor to a device via ENQCMD.

This first access triggers a #GP fault because the IA32_PASID MSR lacks initialization with the PASID value assigned during device opening. The Linux #GP handler, noting PASID allocation for the process, initializes IA32_PASID MSR and returns, permitting ENQCMD reexecution.

On fork(2) or exec(2), the PASID is removed since the process no longer maintains the identical address space from device opening.

On clone(2), the new task shares the identical address space, enabling PASID allocated to the process. IA32_PASID preemptive initialization does not occur as PASID allocation might remain incomplete or kernel awareness of device thread access may be absent, with cleared IA32_PASID MSR reducing context switch overhead through xstate init optimization. Since #GP faults require handling on threads created before PASID assignment to the mm, newly created threads receive consistent treatment.

Due to complexity in PASID freeing and IA32_PASID MSR clearing across all threads during unbind, PASID freeing occurs lazily only at mm exit.

If a process executes close(2) of the device file descriptor and munmap(2) of the device MMIO portal, the driver unbinds the device. The PASID remains marked VALID in PASID_MSR for any process threads that accessed the device, but this remains harmless as lacking the MMIO portal prevents new work submission.

## 32.7. Relationships

* Each process maintains multiple threads but only one PASID
* Devices possess limited hardware workqueues (approximately tens to thousands), managed by device drivers
* Single mmap() maps one hardware workqueue as a "portal," with each portal mapping to a single workqueue
* For each device with which a process interacts, one or more mmap()'d portals must exist
* Multiple process threads can share a single portal for accessing a single device
* Multiple processes can separately mmap() the identical portal, still sharing one device hardware workqueue
* The single process-wide PASID is used by all threads for all device interactions, not per-thread or per-thread-device-pair

## 32.8. FAQ

**What is SVA/SVM?**

Shared Virtual Addressing (SVA) permits I/O hardware and processors to work within the same address space. Some terminology uses Shared Virtual Memory (SVM), but the Linux community preferred avoiding confusion with POSIX Shared Memory and Secure Virtual Machines, which were already established terms.

**What is a PASID?**

A Process Address Space ID (PASID) is a PCIe-defined Transaction Layer Packet (TLP) prefix—a 20-bit number allocated and managed by the OS. PASID inclusion in all platform-device transactions enables identification.

**How are shared workqueues different?**

Traditionally, separate hardware instances per process were required for userspace application hardware interaction. For example, doorbells inform hardware about work processing, requiring 4k (or page-size) spacing for process isolation. This necessitates hardware provisioning and MMIO reservation, creating poor scalability with increasing thread counts. Hardware manages Shared Work Queues (SWQ) depth, and consumers need not track it. Command rejection with retry indication occurs when no space exists for acceptance.

Users should verify Deferrable Memory Write (DMWr) device capability and submit ENQCMD only when supported. In new DMWr PCIe terminology, devices require DMWr completer capability, with all switch ports supporting DMWr routing enabled by the PCIe subsystem, similar to PCIe atomic operation management.

SWQ enables hardware to provision a single device address. When combined with ENQCMD for work submission, the device distinguishes submitting processes via included PASID, supporting scalable process handling.

**Is this the same as a user space device driver?**

Shared workqueue device communication proves simpler than complete user space drivers. Kernel drivers manage all hardware initialization, while user space focuses solely on work submission and completion processing.

**Is this the same as SR-IOV?**

Single Root I/O Virtualization (SR-IOV) emphasizes independent hardware interface provisioning for virtualization, requiring nearly fully functional interfaces supporting traditional BARs, interrupt space via MSI-X, and unique register layouts. Virtual Functions (VFs) receive assistance from Physical Function (PF) drivers.

Scalable I/O Virtualization builds upon PASID concepts for creating device virtualization instances. SIOV requires host software assistance in virtual device creation; each virtual device representation includes a PASID and bus/device/function. This permits device hardware optimization of resource creation with dynamic on-demand growth, contrasting SR-IOV's static creation and management. Consult references for additional details.

**Why not just create a virtual function for each app?**

PCIe SR-IOV Virtual Function (VF) creation proves expensive. VFs demand duplicated hardware for PCI config space and interrupts like MSI-X. Interrupt resources undergo hard partitioning between VFs at creation, lacking dynamic demand-based scaling. VFs remain incompletely independent from Physical Functions (PF), with most requiring PF driver communication and assistance. SIOV conversely creates software-defined devices where configuration and control aspects receive mediation via slow paths, while work submission and completion occur unmediated.

**Does this support virtualization?**

ENQCMD usage is possible within guest VMs. In these scenarios, the VMM establishes translation table setup translating Guest PASID to Host PASID. Consult ENQCMD instruction set reference for specifics.

**Does memory need to be pinned?**

Devices supporting SVA with IOMMU platform hardware support eliminate DMA memory pinning requirements. SVA-supporting devices also support additional PCIe features removing pinning necessity.

Device TLB support—Devices request IOMMU address lookup before use via Address Translation Service (ATS). If mapping exists but OS has not allocated pages, IOMMU hardware reports no mapping.

Devices request virtual address mapping via Page Request Interface (PRI). Upon successful OS mapping completion, responses return to devices, which request translation again and continue.

IOMMU manages OS page-table consistency with devices. Upon page removal, it interacts with devices to clear cached device TLB entries before removing OS mappings.

## 32.9. References

VT-D: https://01.org/blogs/ashokraj/2018/recent-enhancements-intel-virtualization-technology-directed-i/o-intel-vt-d

SIOV: https://01.org/blogs/2019/assignable-interfaces-intel-scalable-i/o-virtualization-linux

ENQCMD in ISE: https://software.intel.com/sites/default/files/managed/c5/15/architecture-instruction-set-extensions-programming-reference.pdf

DSA spec: https://software.intel.com/sites/default/files/341204-intel-data-streaming-accelerator-spec.pdf

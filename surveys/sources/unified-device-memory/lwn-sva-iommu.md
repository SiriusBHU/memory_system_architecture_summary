> Local Markdown copy fetched on 2026-06-22 via Claude Code's WebFetch tool (the host sandbox blocked direct `curl`). Content is the WebFetch model's extracted-Markdown rendering of the source page — not raw HTML. For canonical text, see the original URL.
>
> Source URL: https://lwn.net/Articles/747230/
> Fetched: 2026-06-22

---

# Shared Virtual Addressing for the IOMMU

## Overview

This patch series introduces Shared Virtual Addressing (SVA) support to the Linux kernel's IOMMU subsystem. SVA enables devices to share process address spaces, allowing applications to instruct devices to perform DMA operations on buffers allocated through standard memory management functions like malloc.

## Required Features

The device, buses, and IOMMU must support three key capabilities:

* Multiple address spaces per device using mechanisms like PCI PASID (Process Address Space ID)
* I/O Page Faults (IOPF) through PCI PRI or ARM SMMU stall functionality
* Compatible page table formats between MMU and IOMMU

## API Functions

The series introduces the following device driver APIs:

```
iommu_sva_device_init(dev, features, max_pasid)
iommu_sva_device_shutdown(dev)
iommu_register_mm_exit_handler(dev, handler)
iommu_unregister_mm_exit_handler(dev)
iommu_sva_bind_device(dev, mm, *pasid, flags, drvdata)
iommu_sva_unbind_device(dev, pasid)
```

## Patch Organization

**Patches 1-6:** Introduce binding API and address space tracking

**Patches 7-10:** Add generic fault handling mechanisms

**Patches 11-36:** Implement complete SVA support for the SMMUv3 driver

**Patch 37:** Adds VFIO ioctl for SVA access from userspace drivers

## Implementation Details

The patchset includes significant changes across multiple subsystems:

* New IOMMU core SVA support module
* SMMUv3 driver enhancements with context descriptor management
* ARM64 architecture changes for ASID pinning
* PCI ATS and PRI support integration
* Device tree binding documentation updates

## Testing

The author tested the code on software models implementing SMMUv3 with dummy DMA devices and invites additional testing feedback.

---

*Omitted: Site navigation chrome, login fields, and copyright footer.*

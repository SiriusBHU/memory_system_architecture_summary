> Local Markdown copy fetched on 2026-06-22 via Claude Code's WebFetch tool (the host sandbox blocked direct `curl`). Content is the WebFetch model's extracted-Markdown rendering of the source page — not raw HTML. For canonical text, see the original URL.
>
> Source URL: https://www.kernel.org/doc/html/v5.0/vm/hmm.html
> Fetched: 2026-06-22

---

# Heterogeneous Memory Management (HMM)

## Overview

Heterogeneous Memory Management provides "infrastructure and helpers to integrate non-conventional memory (device memory like GPU on board memory) into regular kernel path, with the cornerstone of this being specialized struct page for such memory."

HMM also enables optional helpers for Share Virtual Memory (SVM), allowing "a device to transparently access program address coherently with the CPU meaning that any valid pointer on the CPU is also a valid pointer for the device."

## Problems of using a device specific memory allocator

Devices with substantial onboard memory (such as GPUs) have historically managed memory through dedicated driver APIs, creating a "split address space" where device memory and application memory remain separate. This disconnect complicates programming because:

- Code must copy objects between generically allocated memory (malloc, mmap) and device-specific APIs
- Complex data structures (lists, trees) require remapping pointer relationships
- Libraries cannot transparently use data from other libraries without duplication
- Each library cannot reasonably duplicate its API for every device allocator

A shared address space—where any application memory region works transparently with devices—is increasingly necessary as compilers begin leveraging GPUs and other devices automatically.

## I/O bus, device memory characteristics

Most I/O buses impose significant limitations on shared address spaces:

- "Most I/O buses only allow basic memory access from device to main memory; even cache coherency is often optional"
- "Access to device memory from CPU is even more limited. More often than not, it is not cache coherent"
- PCIE allows limited atomic operations from devices on main memory, but CPUs cannot perform atomic operations on device memory
- Bandwidth is severely constrained (~32 GBytes/s with PCIE 4.0) compared to GPU memory (1 TBytes/s)
- Latency to main memory from devices is orders of magnitude higher than device-to-device access

Some platforms (OpenCAPI, CCIX) address these limitations through two-way cache coherency and full atomic operation support, but broader hardware solutions remain limited.

## Shared address space and migration

HMM provides two primary mechanisms:

1. **Address Space Duplication**: Duplicating CPU page tables in device page tables so the same address references identical physical memory. HMM supplies helpers to populate device page tables while tracking CPU updates, leaving hardware-specific details to device drivers.

2. **ZONE_DEVICE Memory**: "A new kind of ZONE_DEVICE memory that allows allocating a struct page for each page of the device memory." This enables migration of main memory to device memory using existing mechanisms, appearing to the CPU as if the page was swapped to disk.

Any CPU access to a device page triggers a page fault and automatic migration back to main memory.

## Address space mirroring implementation and API

Device drivers register an `hmm_mirror` structure to mirror process address spaces:

```c
int hmm_mirror_register(struct hmm_mirror *mirror,
                        struct mm_struct *mm);
int hmm_mirror_register_locked(struct hmm_mirror *mirror,
                               struct mm_struct *mm);
```

The mirror struct includes callbacks to propagate CPU page table updates:

```c
struct hmm_mirror_ops {
    void (*update)(struct hmm_mirror *mirror,
                   enum hmm_update action,
                   unsigned long start,
                   unsigned long end);
};
```

Device drivers can populate virtual address ranges using:

```c
int hmm_vma_get_pfns(struct vm_area_struct *vma,
                     struct hmm_range *range,
                     unsigned long start,
                     unsigned long end,
                     hmm_pfn_t *pfns);
int hmm_vma_fault(struct vm_area_struct *vma,
                  struct hmm_range *range,
                  unsigned long start,
                  unsigned long end,
                  hmm_pfn_t *pfns,
                  bool write,
                  bool block);
```

The first function fetches present CPU page table entries without triggering faults. The second triggers faults on missing or read-only entries when the write parameter is true.

Critical locking pattern for synchronization:

```c
int driver_populate_range(...)
{
     struct hmm_range range;
     ...
again:
     ret = hmm_vma_get_pfns(vma, &range, start, end, pfns);
     if (ret)
         return ret;
     take_lock(driver->update);
     if (!hmm_vma_range_done(vma, &range)) {
         release_lock(driver->update);
         goto again;
     }

     // Use pfns array content to update device page table

     release_lock(driver->update);
     return 0;
}
```

The `driver->update` lock must be held before calling `hmm_vma_range_done()` to prevent races with concurrent CPU page table updates.

HMM implements this atop the mmu_notifier API. Device page table updates are multi-step processes: writing commands to a buffer, scheduling execution on the device, and waiting for completion. Multiple devices can create commands concurrently, but waiting for execution completion is serialized.

## Represent and manage device memory from core kernel point of view

Earlier designs used device-specific data structures but required extensive kernel code modifications. HMM switched to using `struct page` directly for device memory, keeping most kernel code unaware of the difference.

HMM provides a simple API for registering device memory:

```c
struct hmm_devmem *hmm_devmem_add(const struct hmm_devmem_ops *ops,
                                  struct device *device,
                                  unsigned long size);
void hmm_devmem_remove(struct hmm_devmem *devmem);
```

The `hmm_devmem_ops` structure includes critical callbacks:

```c
struct hmm_devmem_ops {
    void (*free)(struct hmm_devmem *devmem, struct page *page);
    int (*fault)(struct hmm_devmem *devmem,
                 struct vm_area_struct *vma,
                 unsigned long addr,
                 struct page *page,
                 unsigned flags,
                 pmd_t *pmdp);
};
```

The `free()` callback triggers when the last reference on a device page drops. The `fault()` callback triggers when the CPU accesses a device page, initiating migration back to system memory.

## Migration to and from device memory

Since CPUs cannot access device memory directly, migration uses the device DMA engine:

```c
int migrate_vma(const struct migrate_vma_ops *ops,
                struct vm_area_struct *vma,
                unsigned long mentries,
                unsigned long start,
                unsigned long end,
                unsigned long *src,
                unsigned long *dst,
                void *private);
```

This works on virtual address ranges because "device DMA copy has a high setup overhead cost and thus batching multiple pages is needed." The function supports holes in address ranges; non-migratable pages are simply skipped.

The `migrate_vma_ops` structure defines callbacks:

```c
struct migrate_vma_ops {
    void (*alloc_and_copy)(struct vm_area_struct *vma,
                           const unsigned long *src,
                           unsigned long *dst,
                           unsigned long start,
                           unsigned long end,
                           void *private);
    void (*finalize_and_map)(struct vm_area_struct *vma,
                             const unsigned long *src,
                             const unsigned long *dst,
                             unsigned long start,
                             unsigned long end,
                             void *private);
};
```

The `alloc_and_copy()` callback controls destination allocation and copy operations. The `finalize_and_map()` callback handles post-migration cleanup. If struct page migration fails, `finalize_and_map()` can catch unmigrated pages (pages were still copied, wasting bandwidth but kept simple).

## Memory cgroup (memcg) and rss accounting

Device memory is currently "accounted as any regular page in rss counters (either anonymous if device page is used for anonymous, file if device page is used for file backed page or shmem if device page is used for shared memory)." This keeps existing applications unaffected.

A potential drawback: "The OOM killer might kill an application using a lot of device memory and not a lot of regular system memory and thus not freeing much system memory."

Device memory pages are "accounted against same memory cgroup a regular page would be accounted to," simplifying migration and ensuring migrations from device to regular memory cannot fail due to cgroup limits.

Device memory cannot be pinned by drivers or GUP and is always freed upon process exit or when the last reference drops.

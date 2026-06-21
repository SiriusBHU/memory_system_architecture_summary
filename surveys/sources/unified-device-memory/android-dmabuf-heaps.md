> Local Markdown copy fetched on 2026-06-22 via Claude Code's WebFetch tool (the host sandbox blocked direct `curl`). Content is the WebFetch model's extracted-Markdown rendering of the source page — not raw HTML. For canonical text, see the original URL.
>
> NOTE: This was saved as a *bonus* fetch — the originally-requested page
> (`/docs/core/graphics/implement-dma-buf-gpu-mem`) kept returning the
> Graphics overview instead. This adjacent page covers the kernel-side
> ION → DMA-BUF heaps transition in Android 12 (GKI 2.0) and is the
> closest content we could reliably retrieve.
>
> Source URL: https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps
> Fetched: 2026-06-22

---

# Transition from ION to DMA-BUF heaps (5.4 kernel only)

## Overview

Android 12's GKI 2.0 replaces ION with DMA-BUF heaps for three key reasons:

- **Security**: Each DMA-BUF heap operates as a separate character device, allowing individual sepolicy controls rather than shared `/dev/ion` access
- **ABI stability**: DMA-BUF heaps maintain an ABI-stable IOCTL interface backed by upstream Linux kernel maintenance
- **Standardization**: Well-defined UAPI prevents device-specific variations that ION's custom flags and heap IDs allowed

The `android12-5.10` kernel branch disabled `CONFIG_ION` on March 1, 2021.

## Comparison: ION vs DMA-BUF Heaps

### Similarities
- Both implement heap-based DMA-BUF exporting
- Each heap defines its own allocator and DMA-BUF operations
- Comparable allocation performance through single IOCTL calls

### Key Differences

| Feature | ION | DMA-BUF Heaps |
|---------|-----|---------------|
| Device access | Single `/dev/ion` | Separate `/dev/dma_heap/<heap_name>` |
| Heap variants | Private flags for variants | Distinct heaps per variant |
| Allocation method | Heap ID/mask + flags | Heap name |

## Kernel Driver Transition

### ION Heap Registration APIs

Replace ION registration calls with DMA-BUF equivalents:

- `ion_device_add_heap()` → `dma_heap_add()`
- `ion_device_remove_heap()` → `dma_heap_put()`

DMA-BUF heaps require registering each variant separately using `dma_heap_add()`. Register cached and uncached system heap variants as individual heaps at `/dev/dma_heap/system` and `/dev/dma_heap/system_uncached`.

### In-Kernel Allocation APIs

Instead of heap masks and flags, DMA-BUF heaps use heap names:

- `ion_alloc()` → `dma_heap_find()` (locate heap) + `dma_heap_buffer_alloc()` (allocate)

### DMA-BUF Importers

No changes required for drivers that only import DMA-BUFs, as buffers from ION and equivalent DMA-BUF heaps behave identically.

## User-Space Client Transition

### libdmabufheap Library

The abstraction library `libdmabufheap` supports both DMA-BUF and ION heaps with fallback capability. Clients should instantiate a `BufferAllocator` object during initialization instead of calling `ion_open()`.

### Migration Pattern

| Operation | libion | libdmabufheap |
|-----------|--------|---------------|
| Cached system allocation | `ion_alloc_fd(ionfd, size, 0, ION_HEAP_SYSTEM, ION_FLAG_CACHED, &fd)` | `allocator->Alloc("system", size)` |
| Uncached system allocation | `ion_alloc_fd(ionfd, size, 0, ION_HEAP_SYSTEM, 0, &fd)` | `allocator->Alloc("system-uncached", size)` |

### Mapping ION Parameters to Heap Names

The `MapNameToIonHeap()` API allows mapping legacy ION parameters to modern heap names, supporting gradual device upgrades:

```
allocator->MapNameToIonHeap("my_heap_special", "my_heap", ION_FLAG_MY_FLAG)
```

## Required System Changes

### ueventd Configuration

Add entries to device `ueventd.rc` files for new vendor DMA-BUF heaps to expose them with correct permissions.

### SELinux Policy

Create sepolicy permissions enabling userspace clients to access new DMA-BUF heaps. Different clients require specific heap access permissions.

## Vendor Heap Access from Framework Code

Two approved vendor heap categories:

1. **System heap variants**: Device/SoC-specific performance optimizations
   - `CONFIG_DMABUF_HEAPS_SYSTEM` disabled in `gki_defconfig` enabling vendor implementation
   - VTS compliance ensures `/dev/dma_heap/system` exists, supports allocation, and memory mapping

2. **Protected memory heaps**: Vendor-specific secure allocations
   - Register as `/dev/dma_heap/system-secure<vendor-suffix>`
   - Optional but VTS-tested if present
   - Framework access provisioned through Codec2 HAL

Framework features cannot depend on protected heaps due to implementation variability.

## Codec2 Integration

A codec2 allocator for DMA-BUF heaps exists in AOSP, allowing heap parameters specification through the C2 HAL component store interface.

## Sample Transition Workflow

### Step 1: Create DMA-BUF Equivalents
For an ION heap `my_heap` supporting `ION_FLAG_MY_FLAG`, register two DMA-BUF heaps:
- `my_heap` (flag disabled behavior)
- `my_heap_special` (flag enabled behavior)

### Step 2: Add ueventd Configuration
Configure permissions for `/dev/dma_heap/my_heap` and `/dev/dma_heap/my_heap_special`.

### Step 3: Link Clients to libdmabufheap
Instantiate `BufferAllocator` and map legacy parameters to new heap names.

### Step 4: Replace Allocation Calls

| Use Case | libion | libdmabufheap |
|----------|--------|---------------|
| Allocate from `my_heap` without flag | `ion_alloc_fd(ionfd, size, 0, ION_HEAP_MY_HEAP, 0, &fd)` | `allocator->Alloc("my_heap", size)` |
| Allocate from `my_heap` with flag | `ion_alloc_fd(ionfd, size, 0, ION_HEAP_MY_HEAP, ION_FLAG_MY_FLAG, &fd)` | `allocator->Alloc("my_heap_special", size)` |

### Step 5: Update SELinux Policy
Grant client permissions for new DMA-BUF heap access.

### Step 6: Verify Allocations
Examine logcat output confirming DMA-BUF heap usage instead of ION.

### Step 7: Disable ION Heap
Once migration completes, disable the ION heap in kernel. Remove `MapNameToIonHeap()` calls if not supporting older kernel versions.

---

Note: This document is deprecated and scheduled for removal by May 2026; refer to kernel overview documentation for current information.

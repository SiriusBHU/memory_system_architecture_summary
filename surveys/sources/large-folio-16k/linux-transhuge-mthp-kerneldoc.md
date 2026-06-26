# Transparent Hugepage Support — mTHP (Linux kernel documentation)

来源 URL: https://docs.kernel.org/admin-guide/mm/transhuge.html
抓取日期: 2026-06-25（WebFetch 抽取正文）
机构: Linux 内核项目
类型: 官方内核文档

## 经典 PMD-size THP（2MB）vs 多尺寸 THP（mTHP）

- 经典 THP：每触及一个 2MB 虚拟区域取一次缺页。
  > "taking a single page fault for each 2M virtual region touched by userland"
- mTHP：可分配「比基页大、但比传统 PMD 小」的块。
  > "Modern kernels support 'multi-size THP' (mTHP), which introduces the ability to allocate memory in blocks that are bigger than a base page but smaller than traditional PMD-size"

## 支持的 mTHP 尺寸

> "mTHP can back anonymous memory (for example 16K, 32K, 64K, etc)"

## 仍是 PTE 映射

> "These THPs continue to be PTE-mapped, but in many cases can still provide similar benefits"

## 缺页减少倍数

> "Page faults are significantly reduced (by a factor of e.g. 4, 8, 16, etc), but latency spikes are much less prominent"

即缺页按 4/8/16… 倍下降，且不像 2MB THP 那样有明显延迟尖峰。

## 回退行为（更平滑，非全有或全无）

> "Always try PMD-sized huge pages first, and fall back to smaller-sized huge pages if the PMD-sized huge page allocation fails"

mTHP 支持中间尺寸，提供渐进降级而非二元成败。

## 内部碎片 / 内存膨胀

> "In certain cases when hugepages are enabled system wide, application may end up allocating more memory resources"

mTHP 用更小尺寸、每次分配浪费更少来缓解。

## 每尺寸 sysfs 开关

> "echo always >/sys/kernel/mm/transparent_hugepage/hugepages-<size>kB/enabled"
（另有 `.../hugepages-<size>kB/shmem_enabled`）

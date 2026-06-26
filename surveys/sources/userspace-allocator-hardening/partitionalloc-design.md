# PartitionAlloc Design（本地副本）

来源 URL: https://chromium.googlesource.com/chromium/src/+/main/base/allocator/partition_allocator/PartitionAlloc.md
抓取方式: WebFetch（小模型抽取的 Markdown，非原始；引用以原 URL 为准）
抓取日期: 2026-06-25

---

## 设计目标

PartitionAlloc 同时优化三件事：**空间效率（space efficiency）、分配延迟（allocation latency）、安全（security）**。快路径分支少、可内联；线程缓存（thread cache）把锁开销摊薄。

## 安全架构

### 分区隔离（Partition Isolation）

安全模型的核心是**地址空间严格分离**："Different partitions exist in different regions of the process's address space."，而且关键是："PartitionAlloc will only reuse an address space region for the same partition."（PartitionAlloc 只会把一段地址空间复用给**同一个分区**。）这样跨分区的线性溢出/下溢就腐蚀不到别的分区。

页级隔离进一步保证："one page can contain only objects from the same bucket."（一页只装同一 bucket 的对象。）释放时物理内存还给 OS，但地址空间仍为原 bucket 保留独占复用。

### 元数据保护（out-of-line metadata）

PartitionAlloc 把元数据放在一个**独立的、带外（out-of-line）的 region**，与对象分配分开。这个 region "surrounded by guard pages"（被守护页包住），相邻溢出腐蚀不到关键结构。"Linear overflows/underflows cannot corrupt the allocation metadata."（线性溢出/下溢腐蚀不了分配元数据。）

> 这是和经典分配器最根本的差异：经典 dlmalloc/ptmalloc 把 chunk header 放在每块内存**前面**（inline），溢出一个字节就能改写下一块的 size/prev 指针、劫持 freelist。PartitionAlloc 把元数据物理搬走了。

### Freelist 指针保护

空闲槽用存在槽起始处的指针串成 freelist。两层保护：

- 小端系统上指针做**字节序反转**编码，"partial pointer overwrite of freelist pointer should fault"（部分覆写 freelist 指针应当触发 fault，而不是凑成一个指向附近的合法指针）。
- 每个 freelist 指针旁边带一个**影子指针（shadow pointer）**，"encoded in a different manner"（用不同方式编码），用来检测腐蚀。

## 内存布局

### Super Page

普通 bucket 在 2 MiB 的 super page 内运作，再切成 partition page。**第一个和最后一个 partition page 是永久守护页**，第一个守护页里留一个 system page 放元数据——每个 partition page 对应一个 32 字节结构。

### Slot Span

一个 span 内的空闲槽串成单链 freelist；新 span 用 provisioning 机制："Only provisioned slots are chained into the freelist."，推迟物理页提交。span 有 full / empty / active / decommitted 四态。

## 对齐

64 位上保证 16 字节对齐，32 位 8 字节。更高对齐用 `AlignedAlloc()`，PartitionAlloc 保留把请求大小向上取整到 ≥ 对齐要求的最近 2 的幂的权利。

# Scudo Hardened Allocator — LLVM 文档（本地副本）

来源 URL: https://llvm.org/docs/ScudoHardenedAllocator.html
抓取方式: WebFetch（小模型抽取的 Markdown，非原始 HTML；引用以原 URL 为准）
抓取日期: 2026-06-25

---

## Chunk Header 设计（带内 / inline）

Scudo 返回给应用的每一块堆内存前面都带一个 **8 字节 header**，存这块 chunk 的元数据。header 包含：

- **Class ID**：Primary 分配标识所在 region，Secondary 为 0
- **Chunk state**：available / allocated / quarantined
- **Allocation type**：malloc / new / new[] / memalign（可检测 API 配对错误，如 new[] 配 free）
- **Size information**：实际大小（Primary）或未用字节数（Secondary）
- **Chunk offset**：返回指针到后端分配块的字节距离
- **16-bit checksum**：用于腐蚀检测

设计目标是把这些元数据塞进 8 字节，跨所有平台，把每次分配的额外开销压到最小。

> 注意：Scudo 的 header 是 **inline**（紧贴在每个分配块前面）的，这点和 PartitionAlloc 的 out-of-line 元数据不同。Scudo 的"加固"来自 checksum + quarantine + randomization，而不是把元数据物理搬走。

## 腐蚀检测（checksum）

Scudo 用 **CRC32** 对 header 做完整性校验。checksum 的计算输入是："the global secret, the chunk pointer itself, and the 8 bytes of header with the checksum field zeroed out."（全局 secret + chunk 指针本身 + 把 checksum 字段清零后的 8 字节 header）。有硬件支持时走 SSE4.2 等指令加速。它**不是密码学强度**的校验。

机制是**被动**的——"if the corrupted header is not accessed, the corruption will remain undetected."（如果被腐蚀的 header 没被访问到，腐蚀就检测不到。）

header 用 compare-exchange 原语原子加载/存储，防止两个相邻 chunk 属于不同线程时的竞争和 double-fetch。

## Quarantine（延迟复用）

quarantine 把释放的块放进一个**延迟 freelist**，等攒到一定大小才真正回收。这是对抗 use-after-free 的关键缓解，但有性能代价。可配置项：

- **Global quarantine**：`quarantine_size_kb`（默认 0，即关闭）
- **Per-thread quarantine**：`thread_local_quarantine_size_kb`，给全局 quarantine 卸压
- **Chunk size limit**：`quarantine_max_chunk_size` 控制多大的块才进 quarantine

## 随机化 + 守护页

- **Primary 随机化**："Scudo further randomizes how blocks are allocated in the Primary"，还可选随机化 cache 到线程的分配。
- **Secondary 守护页**："Secondary backed allocations are surrounded by Guard Pages."（Secondary 的大块分配被守护页包住。）

安全的根基依赖 OS 内存映射的不可预测性和二进制 ASLR。

## 内存回收

- **Secondary**：释放即 unmap。
- **Primary**：被连续空闲块覆盖的页可以释放回 OS 降 RSS。`release_to_os_interval_ms`（默认 5000ms）控制回收频率，负值禁用。

## 性能 / 开销

文档**没有给明确的基准数字**。唯一量化的开销是每次分配 8 字节 header 带来的"small overhead"。

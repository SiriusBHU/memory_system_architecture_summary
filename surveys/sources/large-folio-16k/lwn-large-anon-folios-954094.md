# Large anonymous folios / mTHP 补丁系列 cover letter（LWN 954094）

来源 URL: https://lwn.net/Articles/954094/
抓取日期: 2026-06-25（WebFetch 抽取正文）
机构: LWN.net（报道 Ryan Roberts / ARM 的 mTHP 补丁系列）
类型: 技术媒体 / 内核补丁报道

## 分配方法（缺页时如何选尺寸 + 回退）

- **选阶**：缺页时按「该 VMA 允许、且地址对齐」挑一个 mTHP 阶（order），优先较大阶。具体选阶逻辑在补丁 #3/#4。
- **回退策略**（v2 changelog 原话）：「iterate through preferred, PAGE_ALLOC_COSTLY_ORDER and 0 only」——先试首选阶，失败则退到 costly order，再不行退到 order-0（基页）。**渐进降级，不是全有或全无。**
- **映射方式**：补丁 #2 标题「Non-pmd-mappable, large folios」——large folio 用**多个连续 PTE** 映射（PTE-mapped），而非 PMD 整块，从而让中间尺寸 THP 与传统 PMD-size THP 共存。

## ARM64 TLB 合并机制（reach 抬升的来源）

> "arm64 systems have 2 mechanisms to coalesce TLB entries; 'the contiguous bit' (architectural) and HPA (uarch)."

- **contiguous bit**：ARM64 架构特性，把一串连续 PTE 标记为可合并。
- **HPA**：微架构层面的优化。
- 两者都让连续 PTE 合并成更少的 TLB 项。

## 性能口径

- 引用 NVIDIA：「dramatic 10x performance improvements for some workloads」。
- 华为侧也报「improvements」。
- 强调「fewer page faults」，本 cover letter 未给统一的缺页下降倍数（倍数见 mTHP 内核文档：4/8/16×）。

# Android mTHP / Large Folios — 源笔记

## 来源 1：LWN「Two talks on multi-size transparent huge page performance」
- 作者/编辑：Jonathan Corbet, LWN.net, 2024
- URL: https://lwn.net/Articles/974826/
- 报告人：Barry Song（OPPO）、Yang Shi
- 关键数字：
  - **mTHP 分配成功率随运行时间衰减**：运行 1 小时后，mTHP 分配尝试成功率约 **50%**（可接受）；运行 **2 小时**后，**失败率超过 90%**——内存完全碎片化，mTHP 已无法分配。
  - **TAO 优化**：将 mTHP 尺寸设为 order-4（**64 KB**），并为 mTHP-only 分配保留 **15%** 物理内存后，成功率稳定保持在 **50% 以上**。
  - **双 LRU 链表**：base page 一条 LRU、large folio 一条 LRU，由专用内核线程管理两者平衡。
  - Yang Shi 测试：memcached 每秒操作数提升约 **20%**；大页尺寸下延迟下降 **10–30%**；内核编译在 64KB/4KB 场景下提升 **5%**。
  - 引述：「内核尚未达到可以自动使用 mTHP 的程度」。

## 来源 2：LWN「Multi-size THP for anonymous memory」
- URL: https://lwn.net/Articles/954094/
- mTHP（Linux 6.8+）在 PMD 级 2 MB 与 4 KB base page 之间引入 16 KB–512 KB 的中间尺寸，通过 `/sys/kernel/mm/transparent_hugepage/hugepages-NkB/` 控制——但控制仍是**系统级**的。

## 来源 3：LPC 2024「Product practices of large folios on millions of OPPO Android phones」
- URL: https://lpc.events/event/18/contributions/1705/
- 幻灯片：https://lpc.events/event/18/contributions/1705/attachments/1426/3423/
- 报告人：Barry Song, Chuanhua Han, Hailong Liu（OPPO）；Kalesh Singh, Yu Zhao（Google）
- 要点：
  - 在**数百万台真实 OPPO 手机**上部署了基于 ARM64 CONT-PTE 的 large folio（mTHP）。
  - 工程难点集中在：内存分配、内存回收、LRU、以及 zsmalloc/zRAM 中 mTHP 的压缩/解压。
  - large folio 可分配概率随内存碎片化迅速下降（与 LWN 报道的 50%→<10% 一致）。

## 来源 4：LWN「mm: support mTHP swap-in for zRAM-like swapfile」
- URL: https://lwn.net/Articles/983531/ ；LKML: Barry Song v5 series
- mTHP swap-in 可将 swap-in 缺页减少 nr_pages 倍；swap-in 带宽提升约 **+83%**。

## 论文级判断
- mTHP 是「全有或全无 THP」到「多尺寸自适应大页」的演进锚点；问题本质是**系统级、固定**的策略无法跟随手机长时间运行后的碎片化状态，需要按设备/负载可编程、访问感知的策略。

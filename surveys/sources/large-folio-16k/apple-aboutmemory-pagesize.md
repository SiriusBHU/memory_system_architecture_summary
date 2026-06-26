# About the Virtual Memory System (Apple 官方文档)

来源 URL: https://developer.apple.com/library/archive/documentation/Performance/Conceptual/ManagingMemory/Articles/AboutMemory.html
抓取日期: 2026-06-25（WebFetch 抽取正文）
机构: Apple Inc.（官方开发者文档，archive）
类型: 厂商官方文档

## 页大小的权威陈述（苹果自己的口径）

> "In OS X and in earlier versions of iOS, the size of a page is 4 kilobytes."

> "In later versions of iOS, A7- and A8-based systems expose 16-kilobyte pages to the
> 64-bit userspace backed by 4-kilobyte physical pages, while A9 systems expose
> 16-kilobyte pages backed by 16-kilobyte physical pages."

要点：
- OS X 与早期 iOS：4KB 页。
- A7 / A8（首批 64 位，2013–2014）：向 64 位用户态**暴露 16KB 页**，但物理仍以 4KB 颗粒**背书**（过渡形态）。
- A9（2015）起：**原生 16KB 物理页**。
- 这条与社区考据一致：iOS 在 64 位转型（iOS 8，2014）时切到 16KB 页面粒度。

## 苹果对「页大小为什么重要」的官方说法（注意：只谈换页 I/O，不谈 TLB）

> "These sizes determine how many kilobytes the system reads from disk when a page
> fault occurs. Disk thrashing can occur when the system spends a disproportionate
> amount of time handling page faults..."

> "Paging of any kind, and disk thrashing in particular, affects performance negatively
> because it forces the system to spend a lot of time reading and writing to disk."

说明：本页**没有**展开 TLB / 页表层级的收益论证——苹果官方文档只从「缺页时一次读多少」的角度谈。TLB reach 的量化要靠其它来源（Ampere 调优指南、7-cpu M1 TLB 实测）补足。

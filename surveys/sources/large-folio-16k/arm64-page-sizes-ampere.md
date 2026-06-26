# Understanding Memory Page Sizes on Arm64 (Ampere Computing)

来源 URL: https://amperecomputing.com/tuning-guides/understanding-memory-page-sizes-on-arm64
抓取日期: 2026-06-25（WebFetch 抽取正文）
机构: Ampere Computing
类型: 厂商调优指南（含硬数字）

## ARM64 可选页大小

ARM64 支持 4KB / 16KB / 64KB 三种页粒度（与 x86 固定 4KB 不同）。

## TLB 覆盖（reach）随页大小变化 —— Ampere Altra / Altra Max（硬数字）

| 指标 | 4KB 页 | 64KB 页 |
|---|---|---|
| L1 数据 TLB 项数 | 48 | 48 |
| L1 覆盖物理内存 | **192 KB** | **3 MB** |
| L2 TLB 项数 | 1,280 | 1,280 |
| L2 覆盖物理内存 | **5 MB** | **80 MB** |

> 同样的 TLB 项数，64KB 页把 L1 覆盖从 192KB 提到 3MB（约 16×），L2 从 5MB 提到 80MB（16×）。
> 16KB 相对 4KB 是 4× 覆盖。

## 内部碎片代价（诚实成本）

> "if we store 7 KB of data in memory, this will use two 4KB pages for a total of 8KB ... an efficiency of 87.5%. On a system with 64KB pages ... a single 64KB page with 7KB of data for an efficiency of 11%."

即页越大、小分配的内部碎片浪费越严重（4KB 下 7KB 数据 87.5% 效率；64KB 下仅 11%）。OS 可复用部分填充的页来缓解。

## 性能收益

> "With larger pages, you have fewer cache misses, and better performance for memory intensive workloads."

注：本页只讨论 Ampere Altra / AmpereOne，未提 Apple / Android 默认配置。

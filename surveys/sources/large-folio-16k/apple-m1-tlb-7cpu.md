# Apple M1 (Firestorm 大核) TLB 实测参数 — 7-cpu.com

来源 URL: https://www.7-cpu.com/cpu/Apple_M1.html
抓取日期: 2026-06-25（WebFetch 抽取正文）
机构: 7-cpu.com（第三方微架构实测）
类型: 第三方硬件实测

## 关键实测（16KB 页模式，Firestorm 大核）

文档章节标题明确：**"16 KB pages mode (Firestorm - Big Core)"**

| 结构 | 容量 | miss 代价 |
|---|---|---|
| L1 Data TLB | **160 项** | 6 cycles |
| L2 TLB | **3K 项（3072）** | 26 cycles |

（L1 指令 TLB 项数本页未给。）

## 由实测推算的 TLB reach（信封背面，基于上表条目数 × 页大小）

| 覆盖范围 | 4KB 页（假想） | 16KB 页（M1 实际） | 倍数 |
|---|---|---|---|
| L1 DTLB reach | 160 × 4KB = 640 KB | 160 × 16KB = **2.5 MB** | 4× |
| L2 TLB reach | 3072 × 4KB = 12 MB | 3072 × 16KB = **48 MB** | 4× |

说明：M1 选 16KB，使**同样数量**的 TLB 条目覆盖到 4 倍物理内存（L1 从 640KB→2.5MB，L2 从 12MB→48MB）。这是「放大粒度」在真实苹果芯片上的直接体现。倍数与 Ampere 调优指南给出的「16KB 相对 4KB 为 4× reach」一致。

https://semiconductor.samsung.com/news-events/tech-blog/samsung-develops-first-ufs-4-0-storage-solution-compliant-with-new-industry-standard/

# Samsung UFS 4.0 官方发布 (闪存/外存带宽对照)

来源: Samsung Semiconductor (官方 tech blog)
URL: https://semiconductor.samsung.com/news-events/tech-blog/samsung-develops-first-ufs-4-0-storage-solution-compliant-with-new-industry-standard/

## 硬数字 (官方原文)
- 顺序读 (sequential read): **4,200 MB/s ≈ 4.2 GB/s**
- 顺序写 (sequential write): **2,800 MB/s ≈ 2.8 GB/s**
- 单 lane 吞吐: **23.2 Gbps** (是上代 UFS 3.1 的 2 倍)
- 相对 UFS 3.1: 读 ~2x, 写 1.6x, 顺序读能效 +46% (MB/s per mA)
- 标准: 符合新批准的 **JEDEC** UFS 4.0 标准；MIPI M-PHY v5.0 物理层
- 容量: 最高 1TB；7th-gen V-NAND

## 关键论点 (内存墙/带宽鸿沟)
- 外存(UFS 4.0)峰值顺序读 ≈ 4.2 GB/s，而片上 LPDDR5X 带宽 ≈ 85 GB/s (Snapdragon 8 Elite),
  约 1 个数量级差距；权重若从闪存按需读取(mmap)，decode 阶段带宽是关键瓶颈。
  这支撑"权重常驻 RAM / 系统级共享单副本"相对"每个 app 从存储各自加载"的演进论点。

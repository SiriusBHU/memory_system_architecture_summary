https://www.notebookcheck.net/JEDEC-releases-LPDDR6-standard-data-rates-reach-14-400-MT-s.1055771.0.html

# LPDDR5X / LPDDR6 内存带宽规格 (内存带宽轴)

## LPDDR6 (JEDEC JESD209-6, 2025-07 发布)
来源(转述 JEDEC 新闻稿): https://www.notebookcheck.net/JEDEC-releases-LPDDR6-standard-data-rates-reach-14-400-MT-s.1055771.0.html
官方稿(403, 仅存 URL): https://www.jedec.org/news/pressreleases/jedec%C2%AE-releases-new-lpddr6-standard-enhance-mobile-and-ai-memory-performance
- 数据率: **10,667 – 14,400 MT/s**
- 等效带宽: **28.5 – 38.4 GB/s** (per device/die 口径)
- 通道架构: 每 die 24-bit 通道，拆为 **两个 12-bit sub-channel**
- 传输粒度: 最小 32-byte，可在 32/64-byte burst 切换；on-die ECC
- 发布: **2025 年 7 月** (JESD209-6)
- 定位: 面向移动与 AI，号称相对上代约 2x 有效带宽

## LPDDR5X (Micron 官方)
来源: https://www.micron.com/products/memory/lpddr-components/lpddr5x
- 顶速档 (1γ): **10.7 Gbps / pin**；相对上代 1β 省电最高 20%；0.61mm 业界最薄封装。
- (Samsung/产业界亦有 LPDDR5X-9600 / 8533 等速档)

## 移动 SoC 实测/官方带宽 (对照)
- Snapdragon 8 Elite Gen 5 (Qualcomm 官方 brief): 支持 LP-DDR5x 最高 5300MHz, 最大 24GB。
- Snapdragon 8 Elite "for Galaxy" (Notebookcheck): quad-channel 16-bit(合64-bit), LPDDR5X-5300,
  **最大带宽 84.8 GB/s**。
- 业内综述 (Chandra & Krishnamoorthi 2026): 移动设备内存带宽 **50–90 GB/s**；
  数据中心 GPU **2–3 TB/s** (差 30–50x)。

## 关键对照 (带宽鸿沟，支撑"权重常驻/共享单副本"论点)
- 片上 LPDDR5X 带宽 ~85 GB/s (旗舰)  vs  外存 UFS 4.0 顺序读 ~4.2 GB/s → 约 **20x / 1 个数量级**差距。
- 若 vs 旧 UFS 或随机读，差距更接近 2–3 个数量级 → decode 阶段必须让权重常驻高带宽 LPDDR。

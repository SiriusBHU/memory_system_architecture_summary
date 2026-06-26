https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf

# Qualcomm Snapdragon 8 Elite Gen 5 官方 Product Brief (内存 / NPU)

来源: Qualcomm 官方 product brief PDF
URL: https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf

## 硬数字 (官方 brief 原文, 已核实)
- 内存: **支持 LP-DDR5x，最高 5300 MHz**；**最大容量 24GB** ("Memory Density: Up to 24GB")
- NPU: **Qualcomm Hexagon NPU，比上代快 37%** ("37% faster Hexagon NPU")
- 其它: 64-bit memory virtualization；Adreno High Performance Memory (HPM)；Tile Memory Heap；
  Dual Micro NPUs (音频/语音/传感)。
- **注意: 官方 brief 未给出绝对 TOPS 数字**，仅以"37% faster"相对值表述 → 任何绝对 TOPS 来自第三方推算，应标 [未核实]。

## 带宽估算 (推导, 非官方直给)
- LPDDR5X-5300 MT/s, 64-bit 总线 → 5300 MT/s x 8 byte ≈ **42.4 GB/s** (单通道口径) 
  第三方 (Notebookcheck) 对 8 Elite "for Galaxy" 给出 quad-channel 16-bit (合 64-bit), 
  LPDDR5X-5300, **最大带宽 84.8 GB/s** (按 5300 MHz x2 DDR x 64bit 口径)。[带宽为第三方/推导]

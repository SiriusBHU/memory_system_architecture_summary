https://v-chandra.github.io/on-device-llms/

# On-Device LLMs: State of the Union, 2026 (decode 带宽受限规则核心来源)

来源: Vikas Chandra & Raghuraman Krishnamoorthi (Meta AI / 业内综述), 2026
URL: https://v-chandra.github.io/on-device-llms/

## 硬数字 (原文)
- 移动设备内存带宽: **50–90 GB/s**
- 数据中心 GPU 带宽: **2–3 TB/s**
- 二者差距: **30–50x** —— 决定端侧推理的核心约束 (memory wall)
- decode 阶段: 每生成一个 token 需把整套权重从内存读一遍，
  "compute units sit idle waiting for memory" → **decode 是带宽受限 (memory-bandwidth-bound)**
- 量化与带宽: 16-bit → 4-bit 不只是 4x 更省存储，更是 **每 token 4x 更少内存流量**，直接 ~4x 吞吐
- footprint 示例: 2B 模型 BitNet 1.58-bit → **~400MB**
- tokens/s 示例: 125M MobileLLM 在 iPhone 上 ~**50 tokens/s** (Liu et al., 2024)
- KV-cache: 长上下文时常常超过权重本身大小；可压到 3-bit

## 关键论点 (decode 带宽受限规则)
- decode 吞吐 ≈ 内存带宽 / 模型字节数 → 模型越大/精度越高，tokens/s 越低。
- 这是"权重常驻 RAM、量化、系统级单副本共享、KV-cache 分页/量化"等所有演进手段的根本动机。

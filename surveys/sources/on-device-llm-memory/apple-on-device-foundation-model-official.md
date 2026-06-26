https://machinelearning.apple.com/research/introducing-apple-foundation-models

# Introducing Apple's On-Device and Server Foundation Models (官方一手来源)

来源: Apple Machine Learning Research, 2024-06 (WWDC24), 与 2025 Tech Report 互为补充
URL: https://machinelearning.apple.com/research/introducing-apple-foundation-models

## 硬数字 (官方原文)

- 端侧模型规模: **~3 billion (~3B) parameters** ("~3 billion parameter on-device language model")
- 量化精度: 混合 2-bit 与 4-bit 配置，**平均 3.7 bits-per-weight (bpw)**
  - "mixed 2-bit and 4-bit configuration strategy — averaging 3.7 bits-per-weight"
  - 可压缩到 **3.5 bits-per-weight** 而不显著掉精度
- KV-cache: 在 Neural Engine 上做高效 KV-cache 更新；(2025 tech report: KV cache 用 8-bit)
- LoRA 适配器: 在共享基座模型上加载；rank-16 adapter 约 **数十 MB (10s of megabytes)**；adapter 参数 16-bit
- 词表大小 (vocab): 端侧 **49K**
- 架构: grouped-query-attention (GQA)；共享输入/输出词嵌入表
- 性能 (iPhone 15 Pro):
  - time-to-first-token (TTFT) 延迟: **约 0.6 毫秒/prompt token**
  - 生成速率: **30 tokens/second**

## 关键论点 (原始→演进轴)
- 共享基座 + 多个轻量 LoRA adapter 按需加载 = 系统级共享模型范式，而非每个 app 自带一份完整模型。
- 苹果统一内存 (unified memory, Apple Silicon) 使 CPU/GPU/Neural Engine 共享同一内存池。
  注: 本页未给出端侧模型占用的 RAM GB 数 (需另找)。

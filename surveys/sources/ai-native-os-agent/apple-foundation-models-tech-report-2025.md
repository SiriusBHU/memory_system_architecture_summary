https://arxiv.org/abs/2507.13575

# Apple Intelligence Foundation Language Models: Tech Report 2025（第三代，WWDC 2025）

## arXiv
- arXiv ID: 2507.13575
- 标题: Apple Intelligence Foundation Language Models: Tech Report 2025

## 端侧模型 On-Device Model（第三代）
- 参数量: **3B**，针对 Apple silicon 优化
- 关键优化: **KV-cache sharing** + **2-bit quantization-aware training (QAT)**
  （注意：相比 2024 第一代的 3.7 bpw palletization，第三代采用 2-bit QAT）
- KV-cache sharing: 把模型分成两块，第二块复用第一块的 KV cache，内存减少约 37.5% [来自第三代发布博客]

## 服务器模型 Server Model
- **PT-MoE (Parallel-Track Mixture-of-Experts)** transformer
- 结合 track parallelism + MoE 稀疏计算 + interleaved global-local attention
- 运行于 Private Cloud Compute

## Foundation Models 框架（开发者）
- Swift-centric 框架，向第三方 app 暴露端侧模型能力
- 三大能力: **guided generation（引导式生成）**、**constrained tool calling（受约束工具调用）**、**LoRA adapter 微调**
- "几行代码即可集成"

## 语言支持
- 支持多种额外语言（multilingual），可理解图像、执行工具调用
- （文档未逐一枚举语言名）

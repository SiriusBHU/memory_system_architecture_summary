https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models

# Apple 第三代基础模型（AFM 3，2026）

## 端侧模型
- **AFM 3 Core**: 30 亿参数 (3B) dense 模型
- **AFM 3 Core Advanced**: 200 亿参数 (20B) 稀疏架构，按请求每次激活 **1~4B 参数**；原生多模态（增强音视频能力）

## 服务器模型
- **AFM 3 Cloud**: 升级版 PT-MoE (Parallel-Track Mixture-of-Experts)
- **AFM 3 Cloud Pro**: 最强服务器模型
- **ADM 3 Cloud**: 图像生成与编辑模型

## 开发者
- 新 Foundation Models 框架，提供 guided generation 与 tool calling

## 量化/语言（本页未给具体数字，见 2025 Tech Report 来源）
- 本页提及 Quantization Aware Training 但未列 2-bit / 37.5% / 16 语言的具体数字
- 具体数字（2-bit QAT、KV-cache sharing 减少 37.5% 内存与 prefill、支持 16 种语言）来自
  arXiv 2507.13575 / 2025 updates 博客，见 apple-foundation-models-tech-report-2025.md

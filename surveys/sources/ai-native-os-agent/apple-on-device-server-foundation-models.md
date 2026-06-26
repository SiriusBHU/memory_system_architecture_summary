https://machinelearning.apple.com/research/introducing-apple-foundation-models

# Apple 端侧与服务器基础模型（第一代，WWDC 2024 / 2024-06）

## 端侧模型 On-Device Model
- 参数量: **~3 billion (~3B)** 端侧语言模型
- 词表: 49K tokens
- 量化: 低比特 palletization，**平均 3.7 bits-per-weight (bpw)**；
  另有更激进压缩到 **3.5 bpw**（无显著质量损失），采用 mixed 2-bit / 4-bit 配置
  + activation quantization + embedding quantization
- 性能 (iPhone 15 Pro): time-to-first-token 约 **0.6 ms / prompt token**，生成 **30 tokens/秒**

## 服务器模型 Server Model (Private Cloud Compute)
- 词表: 100K tokens
- 运行于 Apple silicon servers
- 采用 grouped-query-attention、共享输入/输出词嵌入表

## Adapters (LoRA 微调)
- 可插拔小型神经网络模块，插入到注意力矩阵、注意力投影矩阵、前馈全连接层
- 精度: **16 bits**
- rank-16 adapter 对 ~3B 模型: 参数量级 "**数十兆字节 (10s of megabytes)**"
- 可动态加载、临时缓存、热切换
- 用 "accuracy-recovery adapter" 初始化

## Adapter 覆盖功能
写作与文本润色、通知优先级与摘要、图像生成、应用内动作 (in-app actions)

## Benchmark（厂商自报）
- 端侧模型称优于 Phi-3-mini、Mistral-7B、Gemma-7B、Llama-3-8B
- 服务器模型称可比 DBRX-Instruct、Mixtral-8x22B、GPT-3.5、Llama-3-70B
- IFEval 指令遵循优于同等规模开源/商用模型

## 训练
- 框架: AXLearn（开源，基于 JAX/XLA）
- 数据: 授权内容 + AppleBot 爬取公开数据；声明不使用用户私人数据训练

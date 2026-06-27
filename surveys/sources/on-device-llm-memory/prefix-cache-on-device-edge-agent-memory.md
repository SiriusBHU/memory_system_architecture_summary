https://arxiv.org/abs/2603.04428

# On-device / Edge 前缀-KV 复用 — Agent Memory Below the Prompt: Persistent Q4 KV Cache for Multi-Agent LLM Inference on Edge Devices

- **arXiv ID:** 2603.04428 [cs.LG]
- **提交:** 2026-02-17
- **作者:** Yakov Pyotr Shkolnikov（单作者；机构未在抓取页明示 [未核实]）

## 这是目前少见的、显式针对"端侧/边缘设备"做 KV 复用治理的工作
- **问题:** 边缘设备 RAM 太小，无法同时容纳多个 agent 的 KV cache。Apple M4 Pro 约 10.2 GB cache 预算，FP16 下 8K 上下文仅能放 **3 个 agent**；10-agent 工作流被迫不断淘汰+重载。
- **机制:** 每个 agent 的 KV cache 量化为 **4-bit (Q4)** 后以 **safetensors 格式落盘持久化**；恢复时直接载回 attention 层，跳过重复 prefill。BatchQuantizedKVCache 支持跨多 agent 压缩 cache 的并发推理。

## 淘汰 / 治理策略（端侧视角）
- 端侧 RAM 受限下，无持久化即"淘汰即全量重 prefill"；本工作以 **磁盘持久化 + Q4 量化** 把"淘汰代价"从重算变为快速 reload。

## 硬数字
- 无持久化时，每次淘汰 → 全量 re-prefill，**4K 上下文每 agent 约 15.7 秒**。
- cache 恢复相对重算 **加速 22–136×**（依上下文长度与模型结构）。
- **Q4 量化在固定设备内存下可装下 4× 于 FP16 的 agent 上下文**。

## 相关端侧线索（同批检索，均需进一步核实）
- KVNAND: "Efficient On-Device LLM Inference Using DRAM-Free In-Flash Computing"（arXiv 2512.03608）—— 把存储密集算子下放到 compute-enabled flash die，端侧长上下文。[未深读核实]
- 多数主流前缀-KV 复用工作（RadixAttention / vLLM APC / CachedAttention / Mooncake）面向 **服务器/集群 GPU**，并非为手机/端侧设计；端侧专门工作目前较少。

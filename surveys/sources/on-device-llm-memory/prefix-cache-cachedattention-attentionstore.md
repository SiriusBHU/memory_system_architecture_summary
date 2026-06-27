https://arxiv.org/abs/2403.19708

# CachedAttention / AttentionStore — Cost-Efficient LLM Serving for Multi-turn Conversations

- **arXiv ID:** 2403.19708
- **提交:** 2024-03-23 (v1); 修订 2024-06-30 (v3)
- **作者:** Bin Gao, Zhuomin He, Puru Sharma, Qingxuan Kang, Djordje Jevdjic, Junbo Deng, Xingkun Yang, Zhou Yu, Pengfei Zuo
- **机构:** 华为云 (Huawei Cloud) + National University of Singapore（公开背景；早期 v1 题名为 "AttentionStore: Cost-effective Attention Reuse across Multi-turn Conversations..."）
- **会议:** USENIX ATC 2024 (https://www.usenix.org/conference/atc24/presentation/gao-bin-cost)

## Abstract（要点逐字）
"...existing serving engines executing multi-turn conversations are inefficient due to the need to repeatedly compute the key-value caches of historical tokens." CachedAttention 通过分层存储跨会话轮次复用 KV cache，"decreases the time to the first token by up to 87%, improves prompt prefilling throughput by up to 7.8× for multi-turn conversations, and reduces end-to-end inference cost by up to 70%."

## 核心机制
- 会话变为非活跃时，把该会话的 KV cache 存入名为 **AttentionStore** 的分层 KV 缓存系统；同一会话恢复时直接加载复用，消除历史 token 的重复 prefill。
- **分层存储**：跨 HBM / DRAM / SSD 等成本不同的介质保存全部请求的 KV cache（摘要表述为 "cost-effective memory/storage mediums"；HBM/DRAM/SSD 具体层级见正文）。
- **layer-wise pre-loading + asynchronous saving**：逐层预取、异步落盘，将慢介质 KV 访问与 GPU 计算重叠隐藏。

## 淘汰 / 治理策略
- **scheduler-aware fetching & eviction**：根据推理调度器的提示，把即将访问的 KV cache 提前放到最快层级，并据此驱逐冷数据。
- **decoupled positional encoding（解耦位置编码）**：会话历史增长导致绝对位置偏移、上下文窗口溢出时，通过解耦位置编码 + 有效截断，使已存 KV cache 仍然有效、可复用，避免失效。

## 硬数字
- **TTFT 降低最高 87%**
- **prefill 吞吐最高 7.8×**（多轮对话）
- **端到端推理成本降低最高 70%**

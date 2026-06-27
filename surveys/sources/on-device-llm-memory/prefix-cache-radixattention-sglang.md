https://arxiv.org/abs/2312.07104

# RadixAttention / SGLang — Efficient Execution of Structured Language Model Programs

- **arXiv ID:** 2312.07104 [cs.AI / cs.PL]
- **DOI:** https://doi.org/10.48550/arXiv.2312.07104
- **提交:** 2023-12-12 (v1); 修订 2024-06-06 (v2)
- **作者:** Lianmin Zheng, Liangsheng Yin, Zhiqiang Xie, Chuyue Sun, Jeff Huang, Cody Hao Yu, Shiyi Cao, Christos Kozyrakis, Ion Stoica, Joseph E. Gonzalez, Clark Barrett, Ying Sheng
- **机构:** Stanford / UC Berkeley / LMSYS（论文未在抓取页明示，依公开背景；如严格引用机构请二次核实）
- **会议:** NeurIPS 2024 (OpenReview id=VqkAKQibpq; proceedings.neurips.cc/.../724be4472168f31ba1c9ac630f15dec8-Paper-Conference.pdf)
- **代码:** https://github.com/sgl-project/sglang
- **官方博客(LMSYS):** https://www.lmsys.org/blog/2024-01-17-sglang/

## Abstract（逐字）
"Large language models (LLMs) are increasingly used for complex tasks that require multiple generation calls, advanced prompting techniques, control flow, and structured inputs/outputs. However, efficient systems are lacking for programming and executing these applications. We introduce SGLang, a system for efficient execution of complex language model programs. SGLang consists of a frontend language and a runtime. The frontend simplifies programming with primitives for generation and parallelism control. The runtime accelerates execution with novel optimizations like RadixAttention for KV cache reuse and compressed finite state machines for faster structured output decoding. Experiments show that SGLang achieves up to 6.4x higher throughput compared to state-of-the-art inference systems on various large language and multi-modal models on tasks including agent control, logical reasoning, few-shot learning benchmarks, JSON decoding, retrieval-augmented generation pipelines, and multi-turn chat."

## 核心机制
- 生成请求结束后，KV cache 不丢弃，而是连同 prompt 与生成结果一起保留在 **radix tree（基数树/压缩前缀树）** 中，按 token 序列为 key、KV 张量为 value。GPU 上采用 paged 布局，每 page 对应 1 token。
- 不同请求若共享前缀，可自动复用中间 KV cache，省去重复显存与计算。
- radix tree 支持高效的前缀匹配、插入与淘汰。

## 淘汰 / 治理策略
- **LRU 淘汰**：博客原文 "we implement an LRU eviction policy that recursively evicts leaf nodes."（递归淘汰叶子节点，leaf-first）。
- **cache-aware scheduling**：调度按最长公共前缀排序请求以提升命中率。
- **reference counting**（引用计数）：被运行中请求引用的节点受保护、不被淘汰（论文正文描述；官方博客未提此点）。

## 硬数字
- 论文摘要：**up to 6.4× 吞吐** 提升（vs SOTA 推理系统）。
- LMSYS 官方博客：**up to 5× 吞吐**（vs Guidance / vLLM）。
- 命中率：50%–99% 区间见于第三方部署/二手资料，**[未核实于一手论文/官方博客]**。

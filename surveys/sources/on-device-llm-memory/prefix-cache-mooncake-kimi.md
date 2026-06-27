https://arxiv.org/abs/2407.00079

# Mooncake — A KVCache-centric Disaggregated Architecture for LLM Serving (Kimi / Moonshot AI)

- **arXiv ID:** 2407.00079
- **提交:** 2024-06-24; 最新版 2025-09-03
- **作者:** Ruoyu Qin, Zheming Li, Weiran He, Mingxing Zhang, Yongwei Wu, Weimin Zheng, Xinran Xu
- **机构:** Moonshot AI（Kimi 服务提供方）+ 清华大学（Tsinghua University，公开背景）
- **会议:** USENIX FAST 2025（Best Paper；https://www.usenix.org/conference/fast25/presentation/qin ，题名 "Mooncake: Trading More Storage for Less Computation..."）
- **开源:** https://kvcache-ai.github.io/Mooncake/

## 核心机制（KVCache 为中心的解耦架构 + 分层前缀缓存池）
- prefill 与 decode 集群 **解耦（disaggregated）**；利用 GPU 集群中闲置的 CPU、DRAM、SSD 资源构建 **分层（tiered）解耦 KVCache 池**，提供大容量与高传输带宽的近 GPU 前缀缓存，几乎零额外成本。
- 核心是 **KVCache-centric scheduler（以 KVCache 为中心的调度器）**：在满足时延 SLO 的同时最大化整体有效吞吐。
- 每个 block 附带由 **自身 hash + 其前缀 hash** 共同决定的 hash 值，用于去重（前缀感知）。

## 淘汰 / 治理策略
- **KVCache-centric scheduling**：调度同时考虑前缀复用命中与负载均衡。
- **prediction-based early rejection（基于预测的提前拒绝）**：过载场景下提前拒绝，避免无效计算与雪崩。

## 硬数字
- **吞吐最高提升 525%**（某些模拟场景，满足 SLO 前提下）。
- 真实负载下 **多处理 75% 更多请求**（"handle 75% more requests"）。
- 具体 **cache hit rate 数字** [未在摘要给出，需正文核实]。

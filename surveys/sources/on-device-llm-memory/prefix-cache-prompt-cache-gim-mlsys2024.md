https://arxiv.org/abs/2311.04934

# Prompt Cache — Modular Attention Reuse for Low-Latency Inference

- **arXiv ID:** 2311.04934
- **提交:** 2023-11-07; 修订 2024-04-25
- **作者:** In Gim, Guojun Chen, Seung-seob Lee, Nikhil Sarda, Anurag Khandelwal, Lin Zhong
- **机构:** Yale University（公开背景）
- **会议:** MLSys 2024 (proceedings.mlsys.org/paper_files/paper/2024/hash/a66caa1703fe34705a4368c3014c1966-Abstract-Conference.html)

## 核心机制（模块化 system prompt / skill 复用，最贴合"系统提示 + skills 复用"）
- 许多 prompt 含重叠片段：system message、prompt 模板、上下文文档。Prompt Cache 在推理服务器上 **预计算并存储这些高频片段的 attention 状态（KV）**，当片段再次出现在用户 prompt 中即直接复用。
- 通过一套 **schema（Prompt Markup Language，PML）** 显式声明可复用片段，称为 **prompt modules（提示模块）**。
- schema 双重作用：(1) 在复用 attention 状态时保证 **位置准确性（positional accuracy）**；(2) 为用户提供访问已缓存状态的接口。
- 与 prefix cache 的区别：不要求复用片段必须位于前缀位置，模块可在 prompt 中任意位置组合（modular，非仅 prefix）。

## 淘汰 / 治理策略
- 以 schema 显式声明哪些模块可缓存复用，治理由用户/schema 定义（声明式），而非纯运行时 LRU。

## 硬数字
- **TTFT 降低：GPU 推理 up to 8×，CPU 推理 up to 60×**（摘要原文 "8x for GPU-based inference to 60x for CPU-based inference"）。
- 对长 prompt（文档问答、推荐）收益尤其显著，且对输出准确性无明显损害。

https://xumengwei.github.io/files/ASPLOS25-NPU.pdf

# Fast On-device LLM Inference with NPUs (llm.npu), ASPLOS '25

作者: Daliang Xu, Hao Zhang, Liming Yang, Ruiqi Liu, Gang Huang, Mengwei Xu*, Xuanzhe Liu* (北大 / 北邮)
会议: ASPLOS '25 (2025-03-30 ~ 04-03, Rotterdam)
DOI: 10.1145/3669940.3707239
arXiv 同名: 2407.05858
PDF: https://xumengwei.github.io/files/ASPLOS25-NPU.pdf

## 硬数字 (论文原文, 已核实)
- prefill 加速: **22.4x faster prefill** (相对 competitive baselines, 平均)
- 能耗: **30.7x energy savings** (平均)
- 端到端真实应用: **up to 32.8x speedup**；总体 (prefill+decode) 比 baseline 快 **1.4x–32.8x**
- 里程碑: **首次实现 billion-sized 模型 >1,000 tokens/sec 的 prefill**
- 基线时延对照: Qwen1.5-1.8B 单步 8.1s, 5 步 UI 任务 >40s; Gemma-2B 回邮件 26.7s

## 关键机制论点 (NPU/异构计算轴)
- "**LLM prefilling is compute-bounded**" → 适合 NPU；移动 CPU/GPU 并行算力有限。
- decode 阶段则是 memory-bound (与带宽受限规则一致)；
  llm.npu 把 prefill 卸载到 NPU、把异常 outlier 张量留在 CPU/GPU 并行 →
  **prefill 在 NPU、decode 在 CPU/GPU** 的异构切分。
- 三级重构: prompt 分块 (chunk=256)、tensor 级 outlier 抽取、block 级乱序调度(按硬件亲和度)。

## 硬件平台 (已核实)
- 测试机: Redmi K70 Pro (**Snapdragon 8 Gen 3, 24GB**) 与 Redmi K60 Pro (Snapdragon 8 Gen 2)，Xiaomi 14。
- NPU: **Qualcomm Hexagon NPU**, 用 Qualcomm QNN / Hexagon SDK；引擎 llama.cpp。
- 测试模型: Qwen1.5-1.8B, Gemma-2B, phi2-2.7B, LlaMA-2-7B, Mistral-7B。

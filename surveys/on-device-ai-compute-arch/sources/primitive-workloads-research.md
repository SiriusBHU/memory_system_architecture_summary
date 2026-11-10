# 原语负载外部调研（v3.3 第 4.3 节补充数据）

> **状态：已与用户对齐（2026-09-11）。** 对齐结论：
> - 负载以 2029 年为主（量产 2029、使用到 2031），不拿今天的负载替代未来负载；本文件的实测数据只作 v3.3 第 4.3 节「负载实例」表的校准锚。
> - 2029 基线：常驻 8B @2-bit；KV 取分支 C（CSA2 + FP4 890 bytes/token + 稀疏 top-k）；语音原生全双工；统一 encoder 300M。重度使用日参数见 calc.py `DAY`。
> - 批准的 8 处原文修订：C1、C2、E1、E2、V1、G1、F1、Ctrl1（见 v3.3 第 4.3 节「v3.3 修订」标注）。
> - 890 B/token 已由 DeepSeek 官方模型卡核实（见 R4 · KV-io 节），不构成冲突。
> - 编号约定：R4 节中的 S# 在 v3.3 文档与 PPT 中记为 R4-S#。
> 标注：【实测】【厂商声明】【论文估算】【推算】（推算附算式）。只取端侧/移动数据；边缘板卡、服务器数据标注为参照。
> 分组：R1 C 类 + 哨兵；R2 E 类；R3 V + G 类；R4 F + Ctrl-d + KV-io。

---

## R4 · F 类（端侧自适应 / LoRA 微调）

| 工作 | 平台 | 模型 | 配置 | 内存峰值 | 每 step | 一次适配（1000 step） | 能耗 | 来源 |
|---|---|---|---|---|---|---|---|---|
| MeBP（Apple） | iPhone 15 Pro Max（A17 Pro，8 GB） | Qwen2.5-0.5B / 1.5B / 3B，Gemma3-1B / 4B | r=16，冻结权重 INT4，seq 256，bs 1，逐层 checkpoint | 320 / 460 / 662 / 569 / 1029 MB【实测，phys_footprint，不含 mmap 权重】 | 3.85 / 9.09 / 17.96 / 9.48 / 28.58 s【实测】 | 1.07 / 2.52 / 4.99 / 2.63 / 7.94 h【推算】 | 未报告 | S1 |
| MeSP（OptAI） | iPhone 17 Pro（A19 Pro，MLX） | Qwen2.5-0.5B / 1.5B / 3B（4-bit） | r=8，seq 256，bs 1 | 136 / 263 / 368 MB（MeBP 同机 361 / 516 / 638 MB）【实测】 | 0.86 / 2.17 / 4.09 s（MeBP 0.68 / 1.66 / 3.21 s）【实测】 | 3B：1.14 h（MeBP 0.89 h）【推算】 | 未报告 | S2 |
| MobileFineTuner | iQOO 15（Snapdragon 8 Elite Gen 5） | Qwen2.5-0.5B，Gemma3-1B | r=8，bs 8，seq 128 | 约 2.9 GB / 8.2–9.0 GB【实测，RSS】 | 107.36 s/step（Qwen2.5-0.5B）【实测】 | 完整任务 7.84–39.30 h / 35.5–178 h【实测】 | 22.3–114.3 kJ / 103.5–535.9 kJ【实测，BatteryStats】，均值约 0.8 W【推算】 | S3 |
| Dbouk 等 | A100 内存剖析 + 12 GB 手机 | Llama-3.2-3B，Qwen-2.5-3B | r=16，q/v | Llama-3.2-3B @1024：29.97 GB（FP32 全参）→ 26.20（+LoRA）→ 14.68（+INT4）→ 3.33（+checkpoint）→ 1.02 GB（+softmax 近似 + logits mask）【实测】 | 手机相对时延 115%（32 token）/ 802%（2048 token）【实测】 | — | — | S4 |
| MobiZO | OnePlus 12 NPU | TinyLlama-1.1B FP16 | r=16，零阶优化 | — | 5.76 s/step【实测】 | ZO 20,000 iter ≈ 32 h【推算】 | — | S5 |
| PockEngine（边缘板卡参照） | Jetson AGX Orin | LLaMA-2-7B | 全参 / LoRA r=8 / PockEngine | 45.1 / 30.9 / 43.1 GB【实测】 | 7.7 / 7.3 / 1.8 s/iter【实测】 | 1000 条：约 2 h → <0.5 h【实测】 | — | S7 |
| Apple AFM adapter | 在 Mac / Linux GPU 上训练，**非手机** | ~3B | r=16，16-bit | adapter 约「几十 MB」（2024）/ 约 160 MB（2025 工具包）【厂商声明】 | — | — | — | S11，S14 |

**6 h 充电窗口推算**：T_win = 21,600 s；A17 Pro + MeBP：k ≈ 17.96 s ÷ 3B ≈ 6.0 s/(B·step) → P_max = 21600 ÷ (1000 × 6.0) ≈ **3.6B**（与实测一致：3B 用 4.99 h 可行，4B 用 7.94 h 不可行）。A19 Pro + MeSP 按时间可到约 15.8B，但 8 GB 内存装不下，实际受内存约束。

**与原文冲突**：原文「LoRA 工作集比全参的 3 倍权重低一个量级」——只加 LoRA 仅降到 1/1.14–1/1.46（S4、S7）；须再加 INT4 + checkpoint 才降一个量级以上（S4 约 29 倍）。全参混合精度 Adam 模型状态为 16 B/param（S10），不是 3 倍权重。

## R4 · Ctrl-d（数据预处理）

| 负载 | 平台 | 数据 | 性质 | 来源 |
|---|---|---|---|---|
| JSON 解析 | iPhone 12 Pro（A14） | yyjson 2.39 GB/s，simdjson 2.19，cJSON 0.48 | 项目方实测 | S15 |
| JSON Schema 校验 | Xeon（服务器参照） | Blaze 0.5 ms / ajv 21.4 ms / Python jsonschema 846 ms（ansible-meta 数据集） | 论文实测 | S18 |
| 分词 | 服务器单线程 | SentencePiece 7.44 MB/s，HF Fast 3.66 MB/s（BPE，Gemma 3） | 项目方实测 | S19 |
| 一次 4,000 token 工具返回 | 推算 | 约 16 KB（按 4 B/token，假设）：解析 6.7–53 µs；分词 0.6–4.4 ms；对比 prefill 这些 token 需 1.5–4.0 s（1,000–2,585 tok/s） | 推算 | S15，S19，S26，S43 |
| 端侧 agent 时延分解 | Redmi K70 Pro（llm.npu） | UI 自动化中 prefill 占推理时延 94.4–98.8% | 实测 | S26 |
| 端侧 agent 时延分解 | Galaxy S24（MobileExplorer，2B VLM） | 每步约 40 s，主要是 VLM 推理 | 实测 | S25 |
| 服务器 agent 分解（参照） | Granite Rapids / Grace + GPU | CPU 工具处理占 2–89%（随负载，如 RAG 检索 81–83%） | 实测，非端侧 | S22，S23 |

**与原文冲突**：原文「Ctrl-d 的 CPU 时间常是延迟的隐藏大头」——端侧实测中 JSON 解析为 µs 级、分词为 ms 级，关键路径被 prefill 占据；「工具处理很重」的证据只来自服务器。调研建议把 Ctrl-d 的表述改为「工具返回内容的 prefill 与工具执行本身」。

## R4 · KV-io（KV bytes/token）

算式：FP16 B/token = 2 × 层数 × KV 头 × head_dim × 2 B；INT8 取一半（不含 scale）。

| 模型 | 层 | KV 头 | head_dim | 注意力 | FP16 B/token | INT8 | 32K KV（FP16） | 来源 |
|---|---|---|---|---|---|---|---|---|
| Llama-3.2-1B | 16 | 8 | 64 | GQA | 32,768 | 16,384 | 1.07 GB | S27 |
| Llama-3.2-3B | 28 | 8 | 128 | GQA | 114,688 | 57,344 | 3.76 GB | S27 |
| Qwen2.5-1.5B | 28 | 2 | 128 | GQA | 28,672 | 14,336 | 0.94 GB | S28 |
| Qwen2.5-3B | 36 | 2 | 128 | GQA | 36,864 | 18,432 | 1.21 GB | S28 |
| Qwen2.5-7B | 28 | 4 | 128 | GQA | 57,344 | 28,672 | 1.88 GB | S28 |
| Qwen3-0.6B / 1.7B | 28 | 8 | 128 | GQA | 114,688 | 57,344 | 3.76 GB | S28 |
| Qwen3-4B / 8B | 36 | 8 | 128 | GQA | 147,456 | 73,728 | 4.83 GB | S28 |
| Gemma-3-1B | 26 | 1 | 256 | MQA；22 局部（窗口 512）+ 4 全局 | 全层 26,624；长程增量 4,096 | — | 截断后 0.146 GB | S29，S31 |
| Gemma-3-4B | 34 | 4 | 256 | 29 局部（窗口 1024）+ 5 全局 | 全层 139,264；长程增量 20,480 | — | 截断后 0.79 GB | S29，S31 |
| Phi-3.5-mini | 32 | 32 | 96 | MHA | 393,216 | 196,608 | 12.88 GB | S32 |
| Phi-4-mini | 32 | 8 | 128 | GQA | 131,072 | 65,536 | 4.29 GB | S33 |
| MiniCPM3-4B | 62 | — | 288（latent） | MLA | 35,712 | 17,856 | 1.17 GB | S34 |
| MiniCPM4-8B | 32 | 2 | 128 | GQA | 32,768 | 16,384 | 1.07 GB | S34 |
| Apple AFM 端侧（2024） | 26 | 8 | 128 | GQA | 106,496 | 53,248 | 3.49 GB | S11 |
| Apple AFM 端侧（2025） | 未公开 | — | — | KV 共享（37.5% 层无 K/V）+ KV 8-bit | 未公开 | — | — | S13 |
| DeepSeek-V3（对照） | 61 | — | 576 | MLA | 70,272 | 35,136 | 2.30 GB | S36 |
| DeepSeek-V4（对照，1M 均摊） | 61 | — | 压缩注意力 | — | 约 9,851【推算 = 9.62 GiB ÷ 2²⁰】 | FP8/FP4 约 4.9K | — | S37，S38 |

**端侧 KV 量化实践**：Apple AFM 2025 KV 8-bit + KV 共享（KV −37.5%，TTFT −37.5%）【厂商声明，S13】；MNN-LLM K int4/int8、V fp8，部分 KV 放 Flash【S40】；llama.cpp q8_0 = 34 B/32 值【S41】；ExecuTorch int8 按 token【S42】。

**迁移（推算）**：32K KV 顺序写 UFS 5.0：Qwen2.5-1.5B 0.087 s、Llama-3.2-3B 0.35 s、Qwen3-4B 0.45 s；Llama-3.2-3B 重新 prefill 32K 约 2.46 s（按 13,333 tok/s）→ 顺序换入比重算便宜。KVSwap（Jetson NVMe/eMMC）测到 512 B 随机读有效带宽 <6% 峰值【S44】→ KV 须按块连续布局。

**890 B/token 已核实（更正 R4 的「未找到出处」）**：DeepSeek 官方 Hugging Face 模型卡（deepseek-ai/DeepSeek-V4.1-Flash，附技术报告 DeepSeek_V41_Tech_Report.pdf）写明——552B 骨干参数的多模态 MoE，1M 上下文；Causal Encoder-Decoder（20 层 causal encoder + 20 层 decoder），**prefill 每 token 激活 8B、decode 激活 16B**；CSA2（每层 Full / Reindex / Reuse 三种静态模式，跨层共享主 KV 与 indexer K、复用 Top-K 稀疏索引）+ **FP4 主 KV**（E2M1，每 16 通道一个 E4M3 scale）→ 全局 KV **890 bytes/token**，约为 DeepSeek-V4-Flash 的 1/4、V1 的 1/437；SWA Bounded Replay 使持久化 KV 约为 V4-Flash 的 1/8。【厂商声明，KV-S46】原文 4.3、5.2.1、5.3、6.3.1、6.3.2 引用的 890 B/token 与「prefill 8B / decode 16B」均有出处。R4 引的 vLLM 博客 9.62 GiB@1M 是 DeepSeek-V4（上一代），不是 V4.1-Flash。

**仍成立的冲突**：原文「端侧小模型 KV 压缩能否跟上是空白」——端侧现状趋势相反：Qwen3 同档每 token KV 是 Qwen2.5 的 4 倍（KV 头 2 → 8）；Qwen3-0.6B 在 32K 下 KV 约为其 FP16 权重的 3 倍。前沿（890 B/token）与端侧现状（29–393 KB/token FP16）相差 30–440 倍。

## R4 来源（均已打开核对）

| # | 标题 / 机构 / 年份 | URL |
|---|---|---|
| S1 | MeBP（Apple）2025 | https://arxiv.org/abs/2510.03425 |
| S2 | MeSP（OptAI）2026 | https://arxiv.org/abs/2602.13069 |
| S3 | MobileFineTuner 2025 | https://arxiv.org/abs/2512.08211 |
| S4 | Peak Memory Reduction for LoRA on Edge（Dbouk 等）2026 | https://arxiv.org/abs/2606.19528 |
| S5 | MobiZO 2024 | https://arxiv.org/abs/2409.15520 |
| S7 | PockEngine（MIT）MICRO 2023 | https://arxiv.org/abs/2310.17752 |
| S10 | ZeRO 2019 | https://arxiv.org/abs/1910.02054 |
| S11 | Apple Intelligence Foundation Language Models 2024 | https://arxiv.org/abs/2407.21075 |
| S13 | Apple Intelligence FM Tech Report 2025 | https://arxiv.org/abs/2507.13575 |
| S14 | Apple Foundation Models adapter training | https://developer.apple.com/apple-intelligence/foundation-models-adapter/ |
| S15 | yyjson README | https://github.com/ibireme/yyjson |
| S18 | Blaze（JSON Schema）2025 | https://arxiv.org/abs/2503.02770 |
| S19 | SentencePiece README | https://github.com/google/sentencepiece |
| S22 | Agentic AI Execution: A CPU-Centric Perspective 2025–2026 | https://arxiv.org/abs/2511.00739 |
| S23 | Agentic AI Workload Characteristics 2026 | https://arxiv.org/abs/2605.26297 |
| S25 | MobileExplorer 2026 | https://arxiv.org/abs/2605.26546 |
| S26 | llm.npu 2024 | https://arxiv.org/abs/2407.05858 |
| S27 | meta-llama sku_list.py | https://github.com/meta-llama/llama-models/blob/main/models/sku_list.py |
| S28 | Qwen 官方 config.json | https://huggingface.co/Qwen |
| S29 | google/gemma_pytorch | https://github.com/google/gemma_pytorch |
| S31 | Gemma 3 技术报告 2025 | https://arxiv.org/abs/2503.19786 |
| S32 / S33 | Phi-3.5-mini / Phi-4-mini config.json | https://huggingface.co/microsoft |
| S34 | MiniCPM 系列 config.json | https://huggingface.co/openbmb |
| S36 | DeepSeek-V3 config.json | https://huggingface.co/deepseek-ai/DeepSeek-V3 |
| S37 | DeepSeek V4 in vLLM（vLLM Blog）2026 | https://vllm.ai/blog/2026-04-24-deepseek-v4 |
| S38 | DeepSeek-V4 技术报告 2026 | https://arxiv.org/abs/2606.19348 |
| S40 | MNN-LLM 2025 | https://arxiv.org/abs/2506.10443 |
| S41 | llama.cpp | https://github.com/ggml-org/llama.cpp |
| S42 | ExecuTorch export_llama_lib.py | https://github.com/pytorch/executorch |
| S43 | Gemma 3 on mobile（Google AI Edge）2025 | https://developers.googleblog.com/en/gemma-3-on-mobile-and-web-with-google-ai-edge/ |
| S44 | KVSwap 2025 | https://arxiv.org/abs/2511.11907 |
| KV-S46 | DeepSeek-V4.1-Flash 模型卡与技术报告（DeepSeek-AI）2026-09 | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash |

---

## R1 · C 类（流式编码）+ 哨兵层

| 负载 | 模型 / 规模 | 触发与频次 | 单次量级 | 延迟 | 功耗 / 能耗 | 性质 | 来源 |
|---|---|---|---|---|---|---|---|
| 哨兵：流式唤醒词（MLPerf Tiny SWW，NDP120） | 46,883 参数（int8 48 KiB） | 约每 32 ms 推理一次 | 827k MAC/次 | 1 s 判定窗 | 平均 0.5067 mW，处理器占空比 2.18%；约 16 µJ/次（推算） | 实测（基准） | C-S4–S7 |
| 哨兵：Syntiant NDP120 手机「Hey Google」 | — | 常开 | — | — | < 280 µW | 厂商声明（2021） | C-S8 |
| 哨兵：Pixel Now Playing（2017，较旧） | DSP 上 8k 参数 CNN，< 10 KB | 每 640 ms 一次；AP 唤醒约 100 次/天 | — | — | DSP 常开增量 < 0.4 mA（≈ 1.6 mW，推算）；整功能 23.5 mAh/天，约 0.9% 电量 | 实测 + 推算 | C-S10 |
| 哨兵：IMU 活动识别（ST LSM6DSOX MLC） | 决策树，26 Hz | 常开 | — | 窗口约 3 s | 整个传感器约 313 µW，MLC 仅增加约 7.2 µW（推算：4 µA × 1.8 V） | 厂商声明（2022） | C-S41 |
| 哨兵：Bosch BHI260AP | 6 轴 IMU + 片上 CPU，256 KB SRAM | 常开 | — | — | 活动识别 0.098 mA（约 176 µW，推算） | 厂商声明（2021） | C-S42 |
| 哨兵：Qualcomm Sensing Hub | 双 micro NPU（音频 / 传感器），INT4 | 常开 | — | — | 第 2 代 < 1 mA（未注明电压轨） | 厂商声明 | C-S11–S14 |
| KWS：Apple「Hey Siri」 | 首级在 AOP 上：5 层 × 32 单元 DNN；2023 版 4 bit/权重 | 麦克风常开，约 0.2 s 输入 | 首级参数约 10⁴ 量级（推算） | — | 未公开 | 厂商声明 | C-S1，S2 |
| VAD：Silero VAD | 约 2 MB | 每块 30 ms 以上 | — | 单 CPU 线程每块 < 1 ms | — | 厂商声明 | C-S15 |
| VAD：Personal VAD 2.0（Google） | 4 层 Conformer，1.0 MB（8 bit） | 约 30 ms/步 | 9.58 MFLOPs（单位未注明） | — | — | 论文 | C-S17 |
| 流式 ASR：Zipformer（AI Hub） | 编码器 63.2M，解码器 3.5M，joiner 3.2M | 每块 0.71 s 音频 | — | 编码器 S24 8.74 ms / S25 7.49 ms；NPU 忙碌约 1.2%（推算） | — | 实测（厂商平台） | C-S20 |
| 流式 ASR：Whisper-tiny（AI Hub） | 编码器 9.4M，解码器 28.4M | 30 s 窗口 | — | 编码器 S24 19.9 ms；解码 1.88 ms/token | — | 实测（厂商平台） | C-S21 |
| 流式 ASR：Google 端侧 RNN-T（2019） | 450 MB → 80 MB | 听写 | — | 单核快于实时 | — | 厂商声明 | C-S18 |
| 流式 ASR 功耗建模（Emformer/Conformer Transducer） | 编码器 60.7M 等 | 分块 160 ms | 权重流量约 0.93 GB/s（推算） | — | **访存 117.2 mW，计算 1.0 mW（计算 < 1%）**；片外约 120 pJ/B | 论文估算（能耗模型） | C-S19 |
| 视觉：MobileNetV4 | Conv-S 3.8M / 0.2 GMAC；Conv-M 9.2M / 1.0 GMAC；Conv-L 31M / 5.9 GMAC | 相机帧 | 见左 | Pixel 8 EdgeTPU 0.7 / 1.1 / 2.4 ms；iPhone 13 0.6 / 1.1 / 3.0 ms | — | 论文实测 | C-S28 |
| 视觉：MNv4-Hybrid-L 能耗（骁龙 8 Gen 3 NPU） | 同上，224 输入 | — | 约 2.45 GMAC | 2.04 ms | **NPU 负载功率 4.3–4.7 W**，9.57 mJ/次；224@30 fps ≈ 287 mW（推算） | 实测 + 推算 | C-S29 |
| 视觉：MobileCLIP 图像塔（Apple） | S0 11.4M / S2 35.7M / B 86.3M | 相机帧 / 相册 | — | iPhone 12 Pro Max：1.5 / 3.6 / 10.4 ms | — | 实测 | C-S31 |
| 视觉：SigLIP2 图像塔（AI Hub） | 约 88M | — | 约 34.5 GFLOP/张（推算） | S24 6.05 ms / S25 4.24 ms | — | 实测 + 推算 | C-S30 |
| 视觉：Apple 场景分析（ANSA） | backbone 16M；ANE 内存约 24.6 MB | 相册、相机、Spotlight | — | iPhone 13 上 < 9.7 ms（含全部任务头） | — | 厂商声明 | C-S34 |
| 屏幕理解：Apple 端侧基础模型视觉部分 | ViTDet-L 300M；672² → 144 token | 事件驱动 | — | 144 token 预填充约 86 ms（推算，不含视觉编码） | — | 厂商声明 + 推算 | C-S38，S39 |
| 屏幕理解：InternVL3.5-2B（AI Hub） | ViT 约 302M，w4a16；448² → 256 token | 事件驱动 | 约 0.62 TFLOP/张（推算） | 视觉编码 351–379 ms（8 Elite）/ 317 ms（8 Elite Gen 5） | — | 实测（厂商平台） | C-S40 |
| 屏幕理解：ScreenAI / Ferret-UI Lite | 5B / 3B | — | — | 无端侧数据 | — | 论文 | C-S35–S37 |
| 语料摄入 embedding：EmbeddingGemma | 308M（约 100M 模型 + 200M 嵌入参数），24 层 | 批量 / 增量 | 约 51 GFLOP / 256 token（推算） | EdgeTPU 上 256 token < 15 ms | 量化后内存 < 200 MB | 厂商声明 | C-S43，S44 |
| 语料摄入 embedding：all-MiniLM-L6（AI Hub） | 22.7M，384 维 | — | — | S24 0.79 ms（128 token） | — | 实测（厂商平台） | C-S45 |
| 语料摄入 embedding：nomic-embed-text v1.5 | 137M | — | — | S24 5.62 ms | — | 实测（厂商平台） | C-S45 |
| Apple 相册人物识别（2021） | — | 夜间充电时聚类 | — | ANE 上单次人脸 embedding < 4 ms | — | 厂商声明 | C-S47 |

**与原文冲突**：
1. 「算力受限、权重常驻片上」只对哨兵层成立（KB–1 MB 级模型）。流式 ASR（约 7 千万参数）、视觉与 embedding encoder（数十到数百 MB）放不进片上；流式 ASR 能耗模型中计算 < 1%，访存主导（约 117 mW）。真正的约束是**访存能耗**。
2. 「mW 级，可无限持续」只在时间平均意义上成立：手机 NPU 推理时负载功率 4.3–4.7 W，实际形态是「W 级 ms 突发 + 低占空比」，均值 mW 到百 mW。
3. 「睡眠 → 首个 embedding < 100 ms」无公开数据；反向证据：NPU 冷启动（含图编译）26.8 s，温启动 2.08 s（C-S33）→ 模型须常驻且预编译。
4. 相机 / 屏幕 10–20% 占空比：未找到公开数据。

## R1 来源（均已打开核对，节选）

| # | 标题 / 机构 / 年份 | URL |
|---|---|---|
| C-S1 | Hey Siri（Apple）2017 | https://machinelearning.apple.com/research/hey-siri |
| C-S2 | Voice Trigger System for Siri（Apple）2023 | https://machinelearning.apple.com/research/voice-trigger |
| C-S4 | MLPerf Tiny v1.3 results | https://github.com/mlcommons/tiny_results_v1.3 |
| C-S5 | MLPerf Tiny SWW 参考模型 | https://github.com/mlcommons/tiny |
| C-S6 | MLPerf Tiny v1.3 流式基准说明 2025 | https://mlcommons.org/2025/09/mlperf-tiny-v1-3-tech/ |
| C-S7 | MLPerf Tiny v1.4 results 2026 | https://mlcommons.org/2026/07/mlperf-tiny-v1-4-results/ |
| C-S8 | Syntiant 支持 Hey/Ok Google 2021 | https://www.syntiant.com/news/edge-ai-chip-company-syntiant-announces-support-for-hey-google-and-ok-google-hotwords |
| C-S10 | Now Playing（Google）2017 | https://arxiv.org/abs/1711.10958 |
| C-S11–S14 | Snapdragon 778G / 8 Gen 3 / 8 Elite / 8 Elite Gen 5 产品简介 | https://www.qualcomm.com |
| C-S15 | Silero VAD README | https://github.com/snakers4/silero-vad |
| C-S17 | Personal VAD 2.0（Google）2022 | https://arxiv.org/abs/2204.03793 |
| C-S18 | An All-Neural On-Device Speech Recognizer（Google）2019 | https://research.google/blog/an-all-neural-on-device-speech-recognizer/ |
| C-S19 | Breaking Down Power Barriers in On-Device Streaming ASR 2025 | https://arxiv.org/abs/2402.13076 |
| C-S20–S22 | Qualcomm AI Hub：Zipformer / Whisper-Tiny / Whisper-Base | https://aihub.qualcomm.com/mobile/models/ |
| C-S28 | MobileNetV4（Google）2024 | https://arxiv.org/abs/2404.10518 |
| C-S29 | Mitigating Compiler Fusion-Induced Power Bursts 2026 | https://arxiv.org/abs/2607.16555 |
| C-S30 | Qualcomm AI Hub：SigLIP2 等 | https://aihub.qualcomm.com/mobile/models/ |
| C-S31 | MobileCLIP（Apple）2024 | https://arxiv.org/abs/2311.17049 |
| C-S33 | Phase Matters 2026 | https://arxiv.org/abs/2606.27906 |
| C-S34 | On-Device Scene Analysis（Apple）2022 | https://machinelearning.apple.com/research/on-device-scene-analysis |
| C-S35 | ScreenAI（Google）2024 | https://arxiv.org/abs/2402.04615 |
| C-S37 | Ferret-UI Lite（Apple）2025 | https://arxiv.org/abs/2509.26539 |
| C-S38 | Apple Intelligence FM Tech Report 2025 | https://arxiv.org/abs/2507.13575 |
| C-S39 | Introducing Apple's On-Device and Server FMs 2024 | https://machinelearning.apple.com/research/introducing-apple-foundation-models |
| C-S40 | Qualcomm AI Hub：InternVL3.5-2B | https://github.com/quic/ai-hub-models |
| C-S41 | ST AN5259（LSM6DSOX MLC）2022 | https://www.st.com/resource/en/application_note/an5259-lsm6dsox-machine-learning-core-stmicroelectronics.pdf |
| C-S42 | Bosch BHI260AP 数据手册 2021 | https://www.bosch-sensortec.com |
| C-S43 | Introducing EmbeddingGemma（Google）2025 | https://developers.googleblog.com/en/introducing-embeddinggemma/ |
| C-S45 | Qualcomm AI Hub：MiniLM-v2 / Nomic-Embed-Text | https://aihub.qualcomm.com/mobile/models/ |
| C-S47 | Recognizing People in Photos（Apple）2021 | https://machinelearning.apple.com/research/recognizing-people-photos |

## R2 · E 类（检索：ANN + rerank + late interaction）

> R2 原文按 80% MFU 折算目标 SoC 时延；对齐稿中统一改为 70%（有效 70 / 140 TOPS）。

### ANN 召回

| 负载 | 平台 | 规模 | 延迟 | 内存 / 能耗 | 性质 | 来源 |
|---|---|---|---|---|---|---|
| 个人语料索引规模（推算网格） | — | 1 万×384 fp32 = 15.4 MB；10 万×768 fp32 = 307 MB（int8 77 MB）；100 万×768 fp32 = 3.07 GB（int8 768 MB，PQ-64B 64 MB）；HNSW 另加 M·2·4 B/条 | — | — | 推算（N·d·b） | E-S13 |
| 真实个人语料 | LEANN README | 邮件 78 万块 2.4 GB、聊天 40 万条 1.8 GB、浏览 3.8 万条 130 MB（传统向量库） | — | LEANN 压缩后 79 / 64 / 6.4 MB | 项目声明 | E-S5 |
| 磁盘驻留 IVF（Apple MicroNN，生产在用） | 设备未具名 | SIFT 1M、GLOVE 1.18M 等，簇均 100 | top-100、90% recall < 7 ms；冷启动约慢 10 倍；批 1024 → 1.7 ms/查询 | 查询内存约 10 MB（比全内存少两个数量级） | 实测 | E-S1 |
| 内存型 vs 磁盘型 ANN（MobileRAG） | Galaxy S24（8 GB） | SIFT 1M×128 | 约 0.1–1 ms（读图） | 内存型 HNSW 1007 MB / IVF 911 MB；磁盘型 9.0–9.7 MB；每次 1.2–19.3 mJ（口径存疑） | 实测（部分读图） | E-S2 |
| 小索引精确检索（EPIC） | Galaxy Z Flip 6 | Contriever 768 维 FlatIP，k=5 | 查询嵌入 3.85 ms + 转向 0.55 ms + FAISS 0.81 ms = 5.21 ms | 记忆 < 1 MB | 实测 | E-S6 |
| 查询 embedding | S24 / Z Flip 6 / EdgeTPU | GTE-Small 33M；EmbeddingGemma 308M；Gecko 110M | S24 0.36 s；Z Flip 6 3.85 ms；EmbeddingGemma 256 token < 15 ms（EdgeTPU） | EmbeddingGemma 量化后 < 200 MB RAM | 实测 / 厂商声明 | E-S2，S6，S15，S16 |
| 超出 DRAM 的抖动（EdgeRAG，边缘板参照） | Jetson Orin Nano 8 GiB | 嵌入 8.3–18.5 GB | Flat 检索 39–81 s | — | 实测（读图） | E-S3 |

**访存特性（推算）**：Flat / IVF 距离的算术强度 = 2d/(d·b) = 2/b → fp32 0.5、fp16 1、int8 2 ops/B，与 N 无关；HNSW（ef=100、M=16）约 1,600 次距离 ≈ 2.5 MB 读、1.2 MFLOP，依赖型随机小块 0.4–3 KB；IVF 选分区随机、分区内顺序可预取；Flat 纯顺序。

### Cross-encoder rerank

| 模型 | 总参数（非嵌入） | 50 候选 × 232 token 的 FLOP（按非嵌入参数） | 性质 | 来源 |
|---|---|---|---|---|
| ms-marco-MiniLM-L6 | 22.7M（10.6M） | 0.27 TFLOP | 推算（结构取自 HF） | E-S22 |
| jina-reranker-v1-tiny | 33.0M（7.1M） | 0.18 TFLOP | 推算 | E-S22 |
| bge-reranker-base | 278M（84.9M） | 2.07 TFLOP | 推算 | E-S22 |
| bge-reranker-v2-m3 | 568M（302M） | 7.27 TFLOP | 推算 | E-S22 |
| Qwen3-Reranker-0.6B | 非嵌入约 440M | 10.8 TFLOP | 推算 | E-S22 |

| 实测 | 平台 | 数据 | 性质 | 来源 |
|---|---|---|---|---|
| MobileRAG Advanced RAG | Galaxy S24 | rerank 使 TTFT 固定多 0.38 s；每查询能耗多 1.71–3.16 J | 实测 | E-S2 |
| PRISM（AIPC 参照） | Mac Mini M2 | Qwen3-Reranker-0.6B，20 候选：5,754 ms，占管线 96.3%；峰值 1,184 MB；检索只要 211 ms | 实测 | E-S7 |
| Snapdragon X Elite（AIPC 参照） | Hexagon 45 TOPS | ≤30 候选 → top-7；全查询 9.48 s，检索 3.09 s | 实测 | E-S8 |

**批处理决定受限类型（推算）**：候选成批时 W8 强度约 2.3×10⁴ ops/B → 算力受限；逐候选串行时 W8 464 ops/B、W4 928 ops/B → 均低于脊点，带宽受限。

### Late interaction

| 项 | 数据 | 性质 | 来源 |
|---|---|---|---|
| ColBERT vs BERT 交叉编码计算量 | k=10 约 180×，k=1000 约 13,900×，k=2000 约 23,000× | 论文实测（2020，服务器） | E-S17 |
| ColBERTv2 残差压缩 | 每 token 20 B（1-bit）/ 36 B（2-bit），未压缩 fp16 256 B；MS MARCO 154 GiB → 16 / 25 GiB | 论文实测 | E-S18 |
| 小型模型 | answerai-colbert-small-v1 33.4M / 96 维；mxbai-edge-colbert-v0 17M / 32M；Jina-ColBERT-v2 559.5M | 论文 / HF | E-S19，S20，S22 |
| 50 候选 × 200 token（answerai-small） | 查询编码 32 token ≈ 1.38 GFLOP；MaxSim ≈ 61 MFLOP；合计 ≈ 1.44 GFLOP；候选 token 矩阵 0.36–1.92 MB → MaxSim 强度 32–228 FLOP/B | 推算 | E-S18，S22 |
| 多向量磁盘开销（ECG） | ColBERT / Dense = 24× | 论文实测 | E-S21 |

**计算量比（推算，50 候选 × 200 token）**：同骨干约 380×；对 MiniLM-L6 约 190×；对 bge-reranker-v2-m3 约 5,000×；按原文 6 TFLOP 口径约 4,200× → 降 2.3–3.7 个数量级。代价：瓶颈转到搬运预计算 token 矩阵（32–228 FLOP/B）；索引膨胀约 4.7×（2-bit）到 17–33×（fp16）。

### 端侧 RAG 中检索的占比

| 系统 / 平台 | 检索延迟 | 总延迟 | 占比 | 来源 |
|---|---|---|---|---|
| MobileRAG（Galaxy S24） | 查询嵌入 0.36 s + 检索 0.3 s（+ rerank 0.38 s） | TTFT 13.16 / 13.54 s | 5.0% / 7.7%（推算） | E-S2 |
| EPIC（Z Flip 6） | 5.21 ms | — | — | E-S6 |
| PerCache（Pixel 7 等） | — | — | 定性：个人库小，每查询检索一次，非瓶颈 | E-S9 |

**与原文冲突**：
1. 「50 候选 × 200 token 过 300M cross-encoder ≈ 6 TFLOP」按总参数算；XLM-R 系 reranker 大半参数是词嵌入表（bge-reranker-base 占 69%），按非嵌入参数实际 2.1–7.3 TFLOP。建议注明「非嵌入参数」。「mW 级引擎需秒级」结论不变。
2. 「rerank 算力受限」只在候选成批时成立；逐候选串行是带宽受限。
3. 「工作集 GB 级、随机访问、预取无效」需分情况：GB 级的是 flash 上的索引，DRAM 常驻可压到约 10 MB（磁盘型 IVF）；随机且依赖的主要是图索引，IVF 分区内顺序可预取；强度 0.5–2 ops/B，比「几 ops/byte」更低。
4. 「late interaction 降一到两个数量级」偏保守，实为 2–4 个数量级；代价是索引膨胀与搬运受限。

## R2 来源（均已打开核对）

| # | 标题 / 机构 / 年份 | URL |
|---|---|---|
| E-S1 | MicroNN（Apple）SIGMOD'25 Companion | https://arxiv.org/abs/2504.05573 |
| E-S2 | MobileRAG（KAIST）2025 | https://arxiv.org/abs/2507.01079 |
| E-S3 | EdgeRAG 2024 | https://arxiv.org/abs/2412.21023 |
| E-S5 | LEANN README | https://github.com/yichuan-w/LEANN |
| E-S6 | EPIC（UNIST）2026 | https://arxiv.org/abs/2605.18271 |
| E-S7 | PRISM（上交 / 华为）EuroSys'26 | https://arxiv.org/abs/2510.15620 |
| E-S8 | Energy-Efficient On-Device RAG on Snapdragon X Elite 2026 | https://arxiv.org/abs/2606.11257 |
| E-S9 | PerCache 2026 | https://arxiv.org/abs/2601.11553 |
| E-S13 | FAISS wiki：Guidelines to choose an index | https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index |
| E-S15 | Google AI Edge RAG guide for Android | https://developers.google.com/edge/mediapipe/solutions/genai/rag/android |
| E-S16 | Introducing EmbeddingGemma（Google）2025 | https://developers.googleblog.com/en/introducing-embeddinggemma/ |
| E-S17 | ColBERT（Stanford）SIGIR'20 | https://arxiv.org/abs/2004.12832 |
| E-S18 | ColBERTv2（Stanford）NAACL'22 | https://arxiv.org/abs/2112.01488 |
| E-S19 | mxbai-edge-colbert-v0 2025 | https://arxiv.org/abs/2510.14880 |
| E-S20 | Jina-ColBERT-v2 2024 | https://arxiv.org/abs/2408.16672 |
| E-S21 | ECG（UMass / Google）2026 | https://arxiv.org/abs/2604.14403 |
| E-S22 | HF 模型页（参数取 safetensors 元数据，结构取 config.json） | https://huggingface.co |

## R3 · V 类（语音生成）

> R3 原文用峰值拐点 879 / 1757 比较；本文档口径为有效脊点（prefill 615 / 1230，decode 88–176 / 176–351），对齐稿按此重判。

| 负载 | 模型 / 规模 | 生成速率 | 延迟 | 工作集 | 性质 | 来源 |
|---|---|---|---|---|---|---|
| 自回归 codec-LLM TTS | CosyVoice 2：Qwen2.5-0.5B LM，25 Hz 单码本，后接流匹配（NFE 10） | 25 token/s 音频 | 双向流式低至 150 ms（README，硬件未注明） | LM ≈ 0.5 GB@W8 | 论文 + 厂商声明 | V-S4，S5 |
| 端侧同传语音生成 | Hibiki-M 1.7B，12.5 Hz，CFG 批 2 | 每 80 ms 一帧 | **iPhone 16 Pro 上连续 1 分钟快于实时** | 0.85 GB@W4 | **手机实测** | V-S3 |
| 全双工语音 LLM | Moshi：Helium 7B + Depth 6 层；Mimi 12.5 Hz | 每 80 ms 一帧 | 理论 160 ms，实测 200 ms（L4 GPU，非端侧）；MLX 版支持 iPhone，无性能数据 | 3.5 GB@W4 + KV ≈ 0.5 MiB/帧（推算） | 论文 + 厂商声明 | V-S1，S2 |
| 端到端语音对话（服务器级参照） | GLM-4-Voice 9B，12.5 Hz 语音 + 文本交替 | 18.75 token/s | 首段需 23 个 token | 4.5 GB@W4 | 论文 | V-S20 |
| 多尺度码本自回归 | Orpheus 3B + SNAC（12/23/47 Hz） | ≈ 82 token/s（推算） | 流式约 200 ms（README） | 1.5 GB@W4 | 厂商声明 + 推算 | V-S17–S19 |
| 非自回归流匹配 | F5-TTS 336M，NFE 32 | 每句 32 次前向 | RTF 0.31（RTX 3090，非端侧） | 0.34 GB@W8 | 论文 | V-S6 |
| 超轻量流匹配 | SupertonicTTS 44M（开放权重 99M） | — | 电子墨水阅读器（移动 SoC）RTF 0.3 | — | 论文 + 厂商 | V-S11，S12 |
| 非自回归 StyleTTS2 类 | Kokoro-82M | 每句 1 次前向 | iPhone 13 Pro 约 3.3× 实时（社区实现） | 进程峰值 1.5–2.0 GB（Mac / 桌面） | 社区 / 第三方实测 | V-S7–S9，S23 |
| Apple 系统 TTS（2021，偏旧） | Tacotron + WaveRNN | — | 移动设备约 3× 实时 | — | 厂商论文 | V-S13 |

**自回归 TTS 的带宽需求（推算：每秒自回归步数 × 每步权重字节，批 1，只算权重）**

| 模型 | P | 步/秒 | W8 带宽（占 113.8 GB/s） | W4 带宽 | 判断 |
|---|---|---|---|---|---|
| CosyVoice 2 LM | 0.5B | 25 | 12.5 GB/s（11%） | 6.25 GB/s（5.5%） | 可行 |
| Hibiki-M | 1.7B | 12.5 | 21.25 GB/s（18.7%） | 10.6 GB/s（9.3%） | 已在手机实测实时 |
| Moshi（Temporal 7B） | 7B | 12.5 | 87.5 GB/s（77%） | 43.75 GB/s（38%） | 每 80 ms 帧 W8 读权重 ≥ 61.5 ms，挤占其他负载 |
| GLM-4-Voice | 9B | 18.75 | 168.75 GB/s（**超出**） | 84.4 GB/s（74%） | 首包 23 token W4 读 103.5 GB ≥ 0.91 s，**达不到 200–300 ms 轮转预算** |
| Orpheus 3B | 3B | ≈ 82 | 246 GB/s（**超出**） | 123 GB/s（**超出**） | 批 1 无法维持实时 |

算术强度：自回归批 1 为 2/b → W8 2、W4 4 ops/B（CFG 批 2 翻倍），远低于 decode 脊点 → 严格带宽受限；非自回归 F5-TTS 一次前向处理 T≈938 帧 → 约 1,876 ops/B → 算力受限。

**与原文的关系**：「带宽受限、比文本 decode 更硬、启动后必须确定性」有数据支撑；「非自回归 / 流匹配降低带宽依赖」成立；「中等功率」**缺手机实测**（未找到任何 TTS / 语音 LLM 功耗数据）；9B 级端到端语音 LLM 在目标 SoC 上首包就超预算。

## R3 · G 类（扩散生成）

| 负载 | 模型 / 规模 | 单次量级 | 延迟（设备） | 工作集 / 能耗 | 性质 | 来源 |
|---|---|---|---|---|---|---|
| SD 1.5（512²） | UNet 860M（fp16 1,640 MB）；VAE 解码器 49.5M | UNet 339 GMACs/步；VAE 解码约 1,247 GMACs（推算） | iPhone 15 Pro：UNet 357 ms/步，20 步共 7.4 s；S23 Ultra GPU 525 ms/步 | 优化后中间张量 80–105 MB（远小于权重）；约 162 J/张（小米 14 Pro，电池放电法，推算） | 实测 | G-S25，S29，S40 |
| SD 1.5（骁龙 NPU） | w8a16，QNN | — | UNet 单次 81.3 / 61.5 / 51.1 ms（8 Gen 3 / 8 Elite / 8 Elite Gen 5）；VAE 197 / 171 / 120 ms（**VAE 比单次 UNet 慢**） | — | 厂商实测（配置未注明） | G-S33 |
| MobileDiffusion（512²，1 步） | 520M（UNet 386M、182 GFLOPs） | 182 GFLOPs | iPhone 15 Pro 共 238 ms（文本 4 + UNet 142 + 解码 92） | — | 实测 | G-S25，S26 |
| SnapFusion（512²，8 步） | UNet 848M | — | iPhone 14 Pro：230 ms/步 × 8 + 解码 116 ms | — | 实测 | G-S24 |
| SnapGen（1024²） | UNet 379M；解码器 1.38M | — | iPhone 16 Pro Max：274 ms/步，4–8 步约 1.4 s；**SDXL 解码器解 1024² 在 ANE 上 OOM** | — | 实测 | G-S27 |
| SnapGen++（DiT，1024²） | 0.4B | — | iPhone 16 Pro Max：4 步共 1.8 s | 1024² 全局自注意力端侧常 OOM | 实测 | G-S28 |
| Apple Core ML SDXL（768²） | UNet 压到 4.04 bit | — | iPhone 15 Pro Max 31 s（20 步） | 运行时峰值 > 2 GB | 厂商实测 | G-S30 |
| 视频：MobileVD | 14 帧 512×256，1 步 | 4.34 TFLOPs/前向 | 小米 14 Pro：UNet 1,780 ms；**SVD 在手机 OOM** | — | 实测 | G-S41 |
| 视频：SnapGen-V | 0.6B，4 步 | — | iPhone 16 Pro Max：5 s 视频约 4–5 s 生成 | — | 实测 | G-S42 |
| 视频：On-device Sora | Open-Sora，68 帧 256² | — | iPhone 15 Pro 优化后 638 s | 权重 23.3 GB（T5 18 GB）vs 单应用 3.3 GB | 实测 | G-S45 |

**「激活可超过权重（1080p）」的核查**：
- 推算：VAE 解码器最高一级 128 通道，1080p 单张量 1920×1080×128×2 B = 531 MB，是解码器权重（≈ 99 MB）的 5.4 倍；SD1.5 式 UNet 最高分辨率自注意力在 1024² 下 4.29 GB/层，超过 UNet 全部权重。
- 实测支持：SDXL 解码器 1024² 在 ANE 上 OOM；1024² 全局注意力常 OOM；SVD 在手机 OOM。
- 实测不支持：512² 融合注意力后中间张量仅 80–105 MB，权重 1,640 MB；视频模型瓶颈是权重（T5 18 GB）。
- 结论：只在「≥1024² / 1080p、像素空间 VAE 解码、未融合注意力」时成立。

**算术强度（推算）**：SD1.5 UNet 512²、W8、批 1：339 GMACs × 2 ÷ 0.86 GB ≈ 788 ops/B —— 高于本文 prefill 有效脊点 615，按本文口径算力受限；CFG 批 2 时约 1,577。VAE 全分辨率层激活落 DRAM 约 576 FLOP/B（带宽敏感）。

**与原文的关系**：「算力受限、延迟容忍高」成立；「中间激活可超过权重」需限定为高分辨率 VAE 解码 / 未融合注意力；「带宽优化近乎无效」按本文有效脊点口径基本成立，但高分辨率 VAE 解码仍依赖分块与融合来控制带宽与内存。

## R3 来源（均已打开核对，节选）

| # | 标题 / 机构 / 年份 | URL |
|---|---|---|
| V-S1 | Moshi（Kyutai）2024 | https://arxiv.org/abs/2410.00037 |
| V-S2 | kyutai-labs/moshi README | https://github.com/kyutai-labs/moshi |
| V-S3 | Hibiki（Kyutai）2025 | https://arxiv.org/abs/2502.03382 |
| V-S4 | CosyVoice 2 2024 | https://arxiv.org/abs/2412.10117 |
| V-S5 | FunAudioLLM/CosyVoice README | https://github.com/FunAudioLLM/CosyVoice |
| V-S6 | F5-TTS 2024 | https://arxiv.org/abs/2410.06885 |
| V-S7 | hexgrad/Kokoro-82M | https://huggingface.co/hexgrad/Kokoro-82M |
| V-S8 | mlalma/kokoro-ios | https://github.com/mlalma/kokoro-ios |
| V-S9 | FluidInference/kokoro-82m-coreml | https://huggingface.co/FluidInference/kokoro-82m-coreml |
| V-S11 | supertone-inc/supertonic | https://github.com/supertone-inc/supertonic |
| V-S12 | SupertonicTTS 2025 | https://arxiv.org/abs/2503.23108 |
| V-S13 | On-device Neural Speech Synthesis（Apple）2021 | https://machinelearning.apple.com/research/on-device-neural-speech |
| V-S17 | canopyai/Orpheus-TTS | https://github.com/canopyai/Orpheus-TTS |
| V-S19 | SNAC 2024 | https://arxiv.org/abs/2410.14411 |
| V-S20 | GLM-4-Voice 2024 | https://arxiv.org/abs/2412.02612 |
| V-S23 | Picovoice On-device TTS Benchmark 2026 | https://picovoice.ai/blog/on-device-tts/ |
| G-S24 | SnapFusion（Snap）2023 | https://arxiv.org/abs/2306.00980 |
| G-S25 | MobileDiffusion（Google）2023 | https://arxiv.org/abs/2311.16567 |
| G-S26 | MobileDiffusion 博客（Google）2024 | https://research.google/blog/mobilediffusion-rapid-text-to-image-generation-on-device/ |
| G-S27 | SnapGen（Snap）2024 | https://arxiv.org/abs/2412.09619 |
| G-S28 | SnapGen++（Snap）2026 | https://arxiv.org/abs/2601.08303 |
| G-S29 | Speed Is All You Need（Google）2023 | https://arxiv.org/abs/2304.11267 |
| G-S30 | apple/ml-stable-diffusion | https://github.com/apple/ml-stable-diffusion |
| G-S33 | qualcomm/Stable-Diffusion-v1.5（AI Hub） | https://huggingface.co/qualcomm/Stable-Diffusion-v1.5 |
| G-S40 | Creative Strategies：Edge AI 能效测试 2024 | https://creativestrategies.com/research/gen-ai-edge-testing/ |
| G-S41 | MobileVD（Qualcomm）2024 | https://arxiv.org/abs/2412.07583 |
| G-S42 | SnapGen-V（Snap）2024 | https://arxiv.org/abs/2412.10494 |
| G-S45 | On-device Sora 2025 | https://arxiv.org/abs/2502.04363 |

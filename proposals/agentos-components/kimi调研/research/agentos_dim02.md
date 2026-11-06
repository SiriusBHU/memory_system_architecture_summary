# AgentOS 组件调研 · 维度 B：端侧推理框架格局 + 推理加速

- 调研日期：2026-11-06；时间范围以 2024-01 ~ 2026-11 为主，奠基性工作标注年份
- 调研方法：40+ 次独立检索，优先官方文档/GitHub/arXiv/顶会论文一手来源；媒体仅作线索
- 与我方架构立场对照见第 4 节（底座模型共享 + LoRA 热插拔、多租户 QoS、权重/KV 可分页）

---

## 1. 技术谱系表

### 1.1 端侧推理框架（框架层玩家）

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|---|
| 解释型 C/C++ 运行时 | llama.cpp / ggml / GGUF | 社区（ggml-org，G. Gerganov 发起） | 2023 起持续迭代 | 端侧推理事实标准；GGUF 单文件格式 + 多档量化 + mmap 惰性加载，后端覆盖 CPU/CUDA/HIP/Metal/Vulkan/SYCL/CANN/OpenCL/WebGPU/Hexagon[^35^] |
| AOT 导出 + 委托后端 | ExecuTorch | Meta / PyTorch Foundation（Arm、Apple、Qualcomm 共建） | 1.0 GA 2025-10；MLSys 2026 论文[^1^][^38^] | PyTorch 原生端侧运行时，`torch.export`→`.pte`，50KB 级基础运行时，12+ 硬件后端 delegate（XNNPACK/Vulkan/QNN/CoreML/MediaTek/VGF/Ethos-U 等）[^1^][^38^] |
| 移动优先引擎 + LLM 扩展 | MNN / MNN-LLM | 阿里巴巴 | MNN 论文 MLSys 2020；MNN-LLM 2025[^4^][^5^] | 通用移动推理引擎（淘宝等 30+ App、日调用十亿级）扩展至 LLM；自动区域融合 + DRAM-Flash 混合存储，小米 14 上 prefill 较 llama.cpp 快 8.6×[^5^] |
| 编译型通用部署 | MLC-LLM / WebLLM | MLC.AI（Apache TVM 社区，CMU 谱系） | 2023 起 | 基于 TVM 的 ML 编译，逐目标生成优化 kernel；内置 PagedKVCache（page=16）；WebGPU 浏览器推理[^34^] |
| OS/厂商栈 | LiteRT / LiteRT-LM（MediaPipe LLM Inference 已弃用并入） | Google | LiteRT 2024 改名、2026-01 GA；LiteRT-LM 2025-06 发布、2025-09 C++ 预览[^8^][^9^] | Google 统一端侧 GenAI 栈：Engine/Session 架构、CPU/GPU/NPU 后端、KV 可跨重启序列化、**多特性共享单一底座模型 + 轻量 LoRA adapter**[^8^][^9^] |
| OS 托管共享模型服务 | Android AICore（Gemini Nano）；Apple Foundation Models | Google / Apple | 2024–2026 | 系统服务托管模型权重，多 App 共用而不各自携带权重；Apple AFM ≈3B 模型 2-bit QAT + rank-32 LoRA adapter（每个 ~160MB）+ 48M draft 投机解码[^10^][^11^] |
| 专用极端量化栈 | bitnet.cpp | Microsoft | 2024-10；ACL 2025 | 1.58-bit（三值）LLM 的 CPU 推理引擎，LUT kernel，ARM/Apple Silicon 上较 llama.cpp Q4_0 快 5–7×[^16^] |
| 厂商闭源 NPU 栈 | Qualcomm QNN/Genie、MediaTek NeuroPilot、Apple MLX（MIT 开源但 Apple-only） | 各厂商 | 持续 | NPU 后端基本为厂商黑盒；llama.cpp Hexagon 后端形成官方 dspqueue 与社区 fastrpc 双轨并存[^36^] |

### 1.2 量化谱系（W4A8 及以下）

| 路线 | 代表工作 | 机构 | 时间/出处 | 一句话贡献 |
|---|---|---|---|---|
| 奠基：混合精度分解 | LLM.int8() | Washington 等 | NeurIPS 2022 | 发现激活 outlier，INT8/FP16 混合分解（2022，奠基）[^13^] |
| Hessian 补偿逐列量化 | GPTQ | ISTA | ICLR 2023（arXiv 2022-10） | 首个把 175B 模型量化到 3–4 bit（4 GPU 小时）；OPT-175B 4-bit ppl 8.37 vs FP16 8.34[^13^] |
| 激活平滑迁移 | SmoothQuant | MIT | ICML 2023 | 把激活量化难度迁移到权重，实现 W8A8 |
| 激活感知权重量化 | AWQ | MIT HAN Lab | **MLSys 2024 最佳论文** | 保护 1% 显著权重通道的 per-channel 缩放；配套 TinyChat 在桌面/移动 GPU 上较 HF FP16 >3× 加速，首次把 Llama-2-70B 搬上移动 GPU[^12^] |
| Hadamard/旋转系 | QuIP#、QuaRot、SpinQuant | Cornell/Meta 等 | NeurIPS 2023 / ICML 2024 / NeurIPS 2024 / ICLR 2025 | 非相干化消除 outlier，推进 ≤4-bit（QuaRot 达 W4A4KV4；SpinQuant 学习旋转）[^12^] |
| W4A8KV4 系统协同 | QServe / QoQ | MIT HAN Lab + NVIDIA | MLSys 2025 | 4-bit 权重 + 8-bit 激活 + 4-bit KV，解决 GPU 上 INT4 反量化 20–90% 开销；A100/L40S 上较 TensorRT-LLM 快 2.4–3.5×[^14^] |
| QAT 低位 | LLM-QAT（Meta 2023，W4A8KV4）；Apple AFM 2-bit QAT；Gemma INT4 QAT 公开 checkpoint | Meta/Apple/Google | 2023–2025 | 训练内 fake-quant 保住超低比特精度，成为端侧主流交付形态[^11^] |
| 原生 1-bit 谱系 | BitNet（2023-10）→ BitNet b1.58（2024-02）→ bitnet.cpp（2024-10）→ **BitNet b1.58 2B4T**（2025-04）→ BitNet v2（W1.58A4，2025-04）→ BitNet Distillation（2025-10） | Microsoft Research | arXiv/ACL 2025 | 三值 {-1,0,+1} 权重从头训练；2B4T 非嵌入权重仅 0.4GB、CPU 解码 29ms/token、能耗 0.028J，平均分超过同规模 GPTQ-int4 模型[^15^][^16^] |
| KV cache 量化 | QServe KV4；llama.cpp `-ctk/-ctv`（f16/q8_0/q4_0…，NVFP4 提案中[^40^]）；TurboQuant（Google，2025-04 arXiv，ICLR 2026 接收；3–4 bit KV） | 多家 | 2024–2026 | KV 量化成为长上下文端侧内存关键手段；MNN 2026-03 落地 TurboQuant，Qwen3-4B@8K 的 KV 从 ~2GB 省 30–60%[^6^] |

### 1.3 投机解码谱系

| 路线 | 代表工作 | 机构 | 时间/出处 | 一句话贡献 |
|---|---|---|---|---|
| 独立草稿模型 | Speculative Decoding / Speculative Sampling | Google / DeepMind | ICML 2023（2022 奠基） | 小模型起草、大模型并行验证，无损加速 |
| 树状投机 | SpecInfer | CMU | ASPLOS 2024 | token tree 验证提升接受长度 |
| 自草稿多头 | Medusa | Princeton/Together 等 | ICML 2024 | 冻结底座上训练 K 个解码头 + 树注意力验证；Medusa-1 无损 2.2×，Medusa-2 达 2.3–2.8×[^17^] |
| 特征级自回归草稿 | EAGLE → EAGLE-2 → EAGLE-3 | SafeAILab（北大/微软研究院背景） | ICML 2024 / EMNLP 2024 / NeurIPS 2025 | EAGLE-2 动态草稿树 Vicuna-7B 均值 3.05×[^19^]；EAGLE-3 弃特征预测改直接 token 预测 + training-time test，最高 6.5×，SGLang batch=64 吞吐 +38%[^18^] |
| 端侧落地 | LLMCad（2023）；**EdgeLLM**（IEEE TMC 2025）；**sd.npu**（arXiv 2510.15312，2025）；SchemaWeaver（2026） | 北大/北邮等 | 2023–2026 | EdgeLLM 自适应草稿树 + 回退策略，移动端每 token 最高 9.3×（survey 转述）[^20^]；sd.npu 做草稿-验证的 NPU 协同调度[^21^] |
| 框架内置 | llama.cpp `draft-simple/draft-eagle3/draft-dflash/draft-dspark/draft-mtp/ngram-*`；Ollama v0.32.6 MTP；vLLM 重构 spec 配置 | 开源社区 | 2024-11（server 首支持）–2026 | 投机解码 2026 年已成端侧/本地运行时一等公民[^2^] |
| 产品级双模型 | Apple AFM：48.77M draft + 3.18B base | Apple | WWDC 2025 | 接受率典型 60–80%，整体 2–4× 加速、零质量损失（第三方逆向分析，非官方数字）[^11^] |

### 1.4 KV 复用与内存分层（含端侧落地水平）

| 路线 | 代表工作 | 机构 | 时间/出处 | 一句话贡献 |
|---|---|---|---|---|
| 分页 KV | vLLM PagedAttention | UC Berkeley 等 | SOSP 2023 | OS 分页思想管理 KV，消除碎片（奠基） |
| 跨请求模块化复用 | Prompt Cache | Yale/UIUC 等 | MLSys 2024 | PML schema + 位置不连续注意力复用；TTFT GPU 8×/CPU 60× 降[^22^] |
| 非前缀选择性重算 | CacheBlend | UChicago 等 | EuroSys 2025 | 只重算 KV 偏差大的少数 token，支持非前缀 KV 复用[^23^] |
| 端侧 NPU KV 复用 | **KV Cache Reuse for Efficient LLM Serving on Mobile NPUs** | （arXiv 2609.34727） | 2026-09 | 首个移动 NPU 上前缀+非前缀 KV 复用系统：静态图内重算 + 分层 KV 存储（NPU/CPU/Flash）；较 ExecuTorch 无复用 prefill 加速 1.5–5.4×，TTFT 降 40–60%[^23^] |
| 跨精度弹性 KV | ElastKV | SJTU 等 | ICDCS 2026 | 混合精度模型间 KV 复用：仅"高复用低"时触发重算；精度损失 <2%，重算提速 ~3×[^24^] |
| 跨 LoRA KV 复用 | MobiLoRA | 东南大学/荣耀 | ACL 2025 | CtxAttention：跨 LoRA adapter 的 KV 相似度 delta 编码 + 按 App 前后台状态的缓存驱逐；TTFT 降 18.1–81.3%[^25^] |
| 跨微调变体 KV 共享 | DroidSpeak | UChicago/Microsoft | NSDI 2026 | 同架构微调模型间按层选择性重算共享 KV；prefill 快 3.1×、吞吐 4×，质量损失可忽略[^26^] |
| 系统服务化 KV 换页 | **LLMS / LLMaaS** | 北大/北邮（Xu/Liu 组） | arXiv 2024-03；SenSys 2026 | 提出"LLM 即移动系统服务"范式：有状态服务、chunk 级 KV 压缩+换入换出，上下文切换延迟降达 2 个数量级[^28^] |
| 权重分层/卸载 | LLM in a flash（Apple）；PowerInfer-2（SJTU）；SmallThinker | Apple/SJTU | ACL 2024 / arXiv 2024-06 / 2025-07 | flash 按需加载：windowing + row-column bundling，可跑 2× DRAM 大小模型，较朴素加载 CPU 4–5×/GPU 20–25×[^31^]；PowerInfer-2 神经元簇 I/O 流水线，手机上 Mixtral-47B 11.68 tok/s[^30^] |

### 1.5 MLSys/ASPLOS/移动系统会议 2024–2026 端侧推理系统论文（精选）

| 论文 | 会议 | 要点 |
|---|---|---|
| llm.npu: Fast On-device LLM Inference with NPUs | ASPLOS 2025 | 首个 NPU 中心端侧 LLM 系统；prefill 较 CPU 基线快 7.3–18.4×，10 亿级模型 prefill 首破 1000 tok/s[^32^] |
| AWQ（+TinyChat） | MLSys 2024（最佳论文） | 见 1.2[^12^] |
| QServe | MLSys 2025 | 见 1.2[^14^] |
| ExecuTorch 论文 | MLSys 2026 | 官方统一 PyTorch 端侧方案；Galaxy S25 Ultra 上 Qwen3-0.6B XNNPACK decode 72–73 tok/s、Llama-3.2-1B QNN prefill 2813–2977 tok/s[^1^] |
| ElastiLM: Elastic On-Device LLM Service | MobiCom 2025 | 单底座弹性化为多级子模型服务多 SLO 请求，切换开销 0.31s（<1% TTFT），精度绝对提升最高 14.83%[^29^] |
| LLM as a System Service（LLMaaS/LLMS） | SenSys 2026 | 见 1.4[^28^] |
| Neuralink: Neuron Co-Activation Linking | ASPLOS 2025 | 神经元共激活链接加速端侧推理[^37^] |
| Sereno: Taming Memory Bandwidth Contention | OSDI 2026 | 移动 LLM 推理内存带宽争用治理[^37^] |
| Scaling LLM Test-Time Compute with Mobile NPU | EuroSys 2026 | NPU 上 test-time compute 扩展[^37^] |

---

## 2. 关键数据（带出处与日期）

1. **ExecuTorch 官方 MLSys 2026 基准（Galaxy S25 Ultra，GS=32）**：Qwen3-0.6B decode — XNNPACK 72–73 / Vulkan 58 / QNN 61–62 tok/s；Llama-3.2-1B prefill — QNN 2813–2977 tok/s vs XNNPACK 525–529 tok/s（NPU prefill 优势 ~5.5×，decode 反而低于 CPU）[^1^]（2026，一手论文）
2. **NPU "prefill 强、decode 弱"**：综述性实测（arXiv 2607.05475，2026-07）在四款手机上对 GENIE(QNN)/llama.cpp/MNN/MLC-LLM × CPU/GPU/NPU 交叉测：Qwen2.5-1.5B NPU(GENIE) prefill 1213–1463 tok/s 但 decode 仅 20.7–23.1 tok/s，低于 llama.cpp GPU decode（最高 64.4 tok/s）[^36^]
3. **MNN-LLM**：小米 14 上 prefill 较 llama.cpp 快 8.6×、较 fastllm 快 20.5×；decode 分别快 2.3×/8.9×（阿里官方口径，媒体转述，2025-05）[^5^]
4. **LiteRT QNN 加速器**（Google 官方博客，2025-11-24）：90 个 LiteRT 算子下沉 Hexagon NPU、72 个基准模型中 64 个可完全 NPU 委托；Snapdragon 8 Elite Gen 5 上 FastVLM-0.5B TTFT 0.12s、prefill >11000 tok/s、decode >100 tok/s[^7^]
5. **BitNet b1.58 2B4T**（微软技术报告，2025-04）：非嵌入权重 0.4GB（Llama-3.2-1B 为 2GB）；CPU 解码 29ms/token；每步解码能耗 0.028J；平均分 54.19，仅次于 Qwen2.5-1.5B（55.23）但内存少 6.5×[^15^]
6. **GPTQ**（ICLR 2023）：OPT-175B 4-bit ppl 8.37（FP16 8.34）；3-bit 8.68；单卡 A100 约 4 GPU 小时完成[^13^]
7. **EAGLE-3**（NeurIPS 2025）：最高 6.5× 加速，较 EAGLE-2 提升 1.4×；SGLang batch=64 吞吐 +38%[^18^]
8. **Medusa**（ICML 2024）：Medusa-1 无损 2.2×；Medusa-2 2.3–2.8×[^17^]
9. **端侧 KV 复用**（arXiv 2609.34727，2026-09）：prefill 较无复用 1.5–5.4×、较仅前缀缓存 1.3–2.5×；TTFT 降 40–60%；直接全量非前缀复用质量掉 ~30%[^23^]
10. **MobiLoRA**（ACL 2025）：端侧 LoRA 推理 TTFT 降 18.1–81.3%[^25^]；**DroidSpeak**（NSDI 2026）：跨微调变体 KV 共享 prefill 3.1×、吞吐 4×[^26^]
11. **PowerInfer-2**（2024-06）：智能手机上 TurboSparse-Mixtral-47B 达 11.68 tok/s，较 SOTA 最高 29.2×[^30^]；**LLM in a flash**（Apple，ACL 2024）：可运行 2× DRAM 容量模型[^31^]
12. **TurboQuant/MNN**：Qwen3-4B@8K KV cache ≈2GB；3–4 bit KV 省内存 30–60%[^6^]
13. **KV 复用空白点实证**（arXiv 2609.34727 引言原文）："mobile LLM inference engines (ExecuTorch, MLC-LLM, llama.cpp, MediaPipe) focus largely on efficient single-request execution... They typically provide little or no support for persistent KV reuse across requests"[^23^]
14. **S-LoRA/Punica（云端先例）**：单 GPU 服务 2000 个并发 LoRA adapter、吞吐损失 <10%；Punica SGMV kernel 12× 吞吐、每 token 仅 +2ms[^27^]

---

## 3. 趋势判断（收敛方向 + 公认空白点）

**收敛方向（事实性观察）：**
1. **权重 W4 已是端侧默认，战场转向 KV 与激活**。QServe(W4A8KV4)、llama.cpp KV 量化、TurboQuant(KV3-4bit) 表明 2025–2026 的主线是 KV cache 低比特化；权重侧 QAT（Apple 2-bit、Gemma INT4 QAT）正在取代纯 PTQ 交付。[^1^][^6^][^11^][^14^]
2. **NPU 分工收敛为"NPU prefill + GPU/CPU decode"**。多个独立实测（ExecuTorch 论文、arXiv 2607.05475、ASPLOS'25 llm.npu）一致显示 NPU prefill 大幅领先而 decode 常输给 GPU——"benchmark the stage, not the chip"。[^1^][^32^][^36^]
3. **投机解码从研究变为运行时一等特性**（llama.cpp 2026 已内置 EAGLE-3/DFlash/DSpark/MTP/ngram 六种实现；Ollama、vLLM 跟进），Apple 产品级双模型方案验证了端侧可行性。[^2^][^11^]
4. **统一 runtime 正在发生，但发生在"厂商纵向收编"而非"跨框架横向互通"**：Google 以 LiteRT-LM 收编 MediaPipe LLM Inference；ExecuTorch 收编 PyTorch 系部署；GGUF 成为跨社区事实上的权重交换格式（Gemma 官方同时发布 GGUF/LiteRT/HF 三格式）。[^8^][^9^]
5. **"底座共享 + 轻量适配"从云端（S-LoRA/Punica）向端侧迁移**：LiteRT-LM 官方明确"multiple features share a single base model using lightweight LoRA adapters"；Apple AFM rank-32 LoRA adapter 经 Background Assets 分发；学术界 MobiLoRA/DroidSpeak/LLMaaS 直接对准端侧底座服务化。[^8^][^11^][^25^][^26^][^28^]

**公认空白点（有据可依的 gap）：**
1. **端侧框架普遍不支持跨请求持久 KV 复用**——一手论文明确指出 ExecuTorch/MLC-LLM/llama.cpp/MediaPipe "little or no support for persistent KV reuse across requests"[^23^]；llama.cpp 有 `--cache-ram`/context checkpoint 等进程内机制但无系统级 KV 存储层。
2. **多框架并存的资源重复占用无通用解法**。开发者实践（aegis-health 等）显示同一 App 常在 llama.cpp/ExecuTorch/LiteRT/MediaPipe 路径间各自携带权重副本；解法只有两类：(a) OS 托管共享模型（AICore、Apple Foundation Models——"shared, OS-managed models that multiple apps can use without each one carrying the model weight"[^10^]）；(b) 组织内部收敛到单一 runtime。**跨框架权重共享（如统一内存映射格式+引用计数）未见任何工业界实现**（判断：基于检索未见；GGUF 只解决格式不解决运行时共享）。
3. **端侧多租户 QoS 调度基本空白**：ElastiLM（SLO 弹性子模型）与 LLMaaS（KV 换页）是仅有的系统级工作，均为学术原型；主流框架无优先级/带宽隔离机制。[^28^][^29^]
4. **投机解码在带宽受限单设备上的负收益风险**：社区实测草稿与目标模型同驻 iGPU 时吞吐不升反降（带宽争用），需 NPU 协同调度（sd.npu）类工作补足。[^21^]
5. **NPU 软件栈封闭**：QNN 黑盒导致 llama.cpp 社区被迫走 FastRPC/cDSP 直通路线，形成双后端并存；跨厂商 NPU 无统一抽象（判断 + GitHub RFC 证据[^36^]）。

---

## 4. 对我方架构立场的启发

我方立场：**(a) 底座模型作为系统服务共享；(b) 多应用共享底座 + LoRA 热插拔；(c) 推理调度需多租户 QoS；(d) 模型权重与 KV cache 可分页。**

### (a) 底座模型作为系统服务共享 —— **支持（强证据）**
- 产业界双巨头均已落地该形态：Android AICore（OS 托管共享模型，App 不携带权重[^10^]）、Apple Foundation Models framework（系统级 3B 底座 + adapter 分发[^11^]）。Google LiteRT-LM 以 Engine/Session 抽象支持多特性共享单底座[^8^]。
- 学术界 SenSys 2026 "LLM as a System Service" 直接命名并论证了该范式（有状态服务 + KV 换页，切换延迟降 2 个数量级）[^28^]。
- 结论：我方方向与产业收敛方向一致，属"正确且已被验证"的路径。

### (b) 共享底座 + LoRA 热插拔 —— **支持，但有端侧特有风险需正视**
- 支持证据：云端 S-LoRA（2000 adapter 并发、<10% 吞吐损失）/Punica（SGMV 12×）[^27^]；端侧 LiteRT-LM 官方 LoRA 共享底座[^8^]、Apple AFM 1,173 个 rank-32 LoRA 组件内建于架构[^11^]；llama.cpp server 支持 `/lora-adapters` 热插拔[^33^]；MobiLoRA 证明跨 adapter KV 可 delta 复用[^25^]。
- **挑战（需设计规避）**：llama.cpp 的实现揭示关键陷阱——LoRA 参与 K/V 投影计算，切换 adapter 会使既有 KV cache 失效（"when we change the LoRA scale, we must clear the KV cache"[^33^]）；且其批量组织方式不支持同 batch 混合 adapter。**含义：我方若做多应用并发 + 各自 LoRA，必须实现 SGMV 类 per-request adapter kernel（云端方案移植）或按 adapter 分组批处理，否则 LoRA 热插拔与 KV 复用互相冲突。**

### (c) 多租户 QoS —— **需要修订（从"调度"扩展为"调度 + 弹性 + 状态管理"三层）**
- 主流框架（llama.cpp slots、ExecuTorch、MNN）均无 QoS 概念；空白即机会。
- 学术原型给出两条互补路线：ElastiLM 的**模型弹性化**（同一底座按 SLO 升降级子模型，切换 <1% TTFT）[^29^]与 MobiLoRA 的**系统级上下文感知驱逐**（按 App 前后台状态决定 KV 保留/驱逐）[^25^]。
- 建议：我方 QoS 设计应吸收 (i) SLO 感知的子模型/prompt 双维弹性，(ii) App 生命周期状态进入缓存驱逐策略，(iii) NPU-prefill/GPU-decode 的分阶段 QoS（decode 带宽争用是主要干扰源，Sereno OSDI'26 主题）[^37^]。

### (d) 权重与 KV 可分页 —— **部分支持、部分需修订**
- 权重可分页：**强支持**。llama.cpp 默认 mmap 惰性加载（权重页可被 OS 回收/按需调入）[^3^]；LLM in a flash / PowerInfer-2 / SmallThinker 证明 flash-DRAM 分层加载可行且已工程化[^30^][^31^]。ExecuTorch 走另一极：AOT memory planning 在导出期确定 arena、消除运行时分配[^1^]——更适合受控系统服务。
- KV 可分页：**需要修订**。vLLM PagedAttention 的分页抽象在端侧仅 MLC-LLM（TVM PagedKVCache, page=16）真正落地[^34^]；llama.cpp 是连续 KV + defrag + slot 级管理，2025-08 起做 unified KV 重构但仍非需求分页[^35^]；**NPU 静态图与 KV 分页存在根本张力**（动态复用语义 vs 静态编译形状，端侧 KV 复用论文的核心矛盾）[^23^]。我方"KV 可分页"若面向 NPU 后端，需采用该论文的 chunk-and-pad + 图内重算方案，而非照搬 vLLM。

---

## 5. 组件特有输出素材：端侧推理栈「框架层」玩家与开放程度

| 玩家 | 维护方 | License/开放性 | 硬件后端覆盖 | 内存管理要点 | 对 AgentOS 可用性 |
|---|---|---|---|---|---|
| llama.cpp (ggml/GGUF) | 社区 ggml-org | MIT，完全开放 | CPU(含 KleidiAI)/CUDA/HIP/Metal/Vulkan/SYCL/CANN/OpenCL/WebGPU/Hexagon(双实现)/RPC | mmap/mlock/DirectIO 装载（`--load-mode`）[^3^]；slot 连续 KV + defrag + KV 量化(-ctk/-ctv) + unified KV[^35^][^40^] | 高：可嵌入、可作本地服务；LoRA 热插拔有 KV 失效陷阱[^33^] |
| ExecuTorch | Meta + PyTorch Foundation（Arm/Apple/Qualcomm 共建） | BSD-3，开放 | XNNPACK/Vulkan/QNN/CoreML/MPS/MediaTek/Arm VGF/Ethos-U/OpenVINO | AOT memory planning（导出期定 arena）；KV 量化 + 滑窗注意力 + 4-bit groupwise[^1^] | 高：PyTorch 原生、NPU 委托最成熟；LLM 生态弱于 llama.cpp |
| MNN / MNN-LLM | 阿里巴巴 | Apache-2.0，开放 | CPU/GPU(OpenCL/Vulkan/Metal)/NNAPI/QNN | DRAM-Flash 混合存储；TurboQuant KV3-4bit[^5^][^6^] | 中高：中文生态强、移动端 prefill 领先 |
| MLC-LLM / WebLLM | MLC.AI（TVM 社区） | Apache-2.0，开放 | Metal/Vulkan/CUDA/ROCm/OpenCL/WebGPU | TIR PagedKVCache（page=16，端侧唯一类 vLLM 分页）[^34^] | 中：需逐目标编译；分页 KV 对 (d) 立场参考价值高 |
| LiteRT / LiteRT-LM | Google | LiteRT-LM Apache-2.0；AICore 闭源系统服务 | CPU/GPU/NPU(QNN 90 算子、MediaTek) | Session KV 可序列化跨重启；Engine/Session 多会话；共享底座 + LoRA[^7^][^8^][^9^] | 高（Android）：官方"共享底座+LoRA"范式样板 |
| MediaPipe LLM Inference | Google | 已弃用 → 迁移至 LiteRT-LM | — | — | 仅历史参考[^9^] |
| Apple Foundation Models / MLX | Apple | 框架 API 开放、模型闭源；MLX MIT | ANE/GPU（Apple-only） | 2-bit QAT 底座 + KV 共享（-37.5%）+ LoRA rank-32 + draft 投机[^11^] | 仅 Apple 平台；架构参考价值高 |
| Qualcomm QNN/Genie | Qualcomm | 闭源 SDK | Hexagon NPU | 静态图编译 | 黑盒；社区有 FastRPC 直通替代路线[^36^] |
| bitnet.cpp | Microsoft | MIT，开放 | CPU(x86 AVX2/ARM NEON) | 1.58-bit LUT kernel | 仅适配 BitNet 谱系模型[^16^] |

---

## 6. 证据清单

> Confidence: H=一手来源原文核对；M=一手来源摘要/二手转述一手；L=媒体/博客线索。

| # | Claim | Source | URL | Date | Excerpt（原文摘录） | Confidence |
|---|---|---|---|---|---|---|
| [^1^] | ExecuTorch 后端矩阵与 MLSys 2026 基准 | MLSys 2026 proceedings / arXiv:2605.08195 | https://proceedings.mlsys.org/paper_files/paper/2026/file/236f915dd02af4f11927f67330b21d4b-Paper-Conference.pdf | 2026 | "Android | Vulkan, XNNPACK, Arm VGF, Qualcomm NPU, MediaTek NPU, Samsung Exynos"；"Qwen3 0.6B XNNPACK 717-733 prefill / 72-73 decode；Llama 3.2 1B QNN 2813-2977 prefill" | H |
| [^2^] | llama.cpp 内置 6 类投机解码实现 | llama.cpp docs/speculative.md | https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md | 2026 检索 | "draft-simple, draft-eagle3, draft-dflash, draft-dspark, draft-mtp, ngram-cache..." | H |
| [^3^] | llama.cpp 装载模式收敛为 --load-mode（mmap/mlock/dio） | jacar.es 对 PR#20834/#28334 的逐项核对 | https://jacar.es/en/fix-llama-cpp-invalid-argument-mlock/ | 2026-10-20 | "-lm, --load-mode MODE ... auto: mmap, unless a device does not support it ... mlock: force system to keep model in RAM" | M |
| [^4^] | MNN 论文为 MLSys 2020 | alibaba/MNN GitHub README | https://github.com/alibaba/mnn | 2026-11-02 检索 | "The preliminary version of MNN ... published in MLSys 2020" | H |
| [^5^] | MNN-LLM 性能口径与 DRAM-Flash 混合存储 | 腾讯云技术百科转述 + alphaxiv 论文概述（arXiv:2506.10443） | https://cloud.tencent.com/developer/techpedia/2657/21114 | 2026-07-16 | "MNN-LLM...在小米 14 等设备上实现了比 llama.cpp 高 8.6 倍的预填充加速。其自动区域融合和 DRAM-Flash 混合存储技术..." | M（官方口径的二手转述） |
| [^6^] | MNN 落地 TurboQuant，KV 3-4bit 省 30-60% | MNN GitHub Discussion #4351 | https://github.com/alibaba/MNN/discussions/4351 | 2026-04-07 | "For Qwen3-4B with 8K context, the KV Cache alone consumes about 2 GB. If we can compress fp16 KV Cache down to 3~4 bits, memory savings reach 30%~60%." | H |
| [^7^] | LiteRT QNN 加速器指标 | Google Developers Blog（daily.dev 镜像） | https://daily.dev/posts/unlocking-peak-performance-on-qualcomm-npu-with-litert-9gs4yq3bl | 2025-11-24 | "supports 90 LiteRT operations, and fully delegates 64 of 72 benchmarked models... FastVLM-0.5B achieving 0.12s time-to-first-token and over 100 tokens/sec decode speed on Snapdragon 8 Elite Gen 5" | M（官方博客转述） |
| [^8^] | LiteRT-LM 定位与共享底座 + LoRA | theleftshift 引 Google 官方博客 | https://www.theleftshift.com/google-brings-on-device-genai-to-chrome-chromebook-plus-and-pixel-watch-via-litert-lm/ | 2025-10-03 | "It also enables multiple features to share a single base model using lightweight LoRA adapters."；支持 CPU/GPU/NPU，跨 Linux/Android/macOS/Windows/Raspberry Pi | M |
| [^9^] | MediaPipe LLM Inference 弃用、迁移 LiteRT-LM | molayab/swift-ai-provider-kit 文档 + qiita LiteRT-LM 解析 | https://github.com/molayab/swift-ai-provider-kit/blob/main/Documentation/Issues/llm-device-linux-windows.md | 2026-03-15 | "Google issued a deprecation notice for the MediaPipe LLM Inference API, directing users to LiteRT-LM." | M |
| [^10^] | AICore 为 OS 托管共享模型 | stora.sh AICore 指南 | https://stora.sh/blog/2026-04-13-on-device-ai-android-app-gemini-nano-guide | 2026-04-13 | "AICore introduces a third option: shared, OS-managed models that multiple apps can use without each one carrying the model weight." | M |
| [^11^] | Apple AFM：3B 底座、2-bit QAT、LoRA rank-32、48M draft | GitHub 逆向分析 + WWDC2025 整理 | https://github.com/fguzman82/apple-foundation-model-analysis | 2025-06 分析 | "3.18 billion parameter base model... 48.77 million parameter draft model... LoRA Rank 32"；"2 bits per weight (bpw) with Quantization-Aware Training"；"KV-cache sharing (37.5% memory reduction)"；"each adapter requiring ~160MB storage" | M（逆向分析，非官方确认） |
| [^12^] | AWQ 为 MLSys 2024 最佳论文，>3× 加速、70B 上移动 GPU | MLSys 2024 proceedings | https://papers.cool/venue/MLSYS.2024 （官网摘要镜像） | 2024 | "protecting 1% of salient weights can greatly reduce quantization error... offering more than 3x speedup over the Huggingface FP16 implementation on both desktop and mobile GPUs. It also democratizes the deployment of the 70B LLaMA-2 model on mobile GPUs." | H |
| [^13^] | GPTQ 指标 | GPTQ 论文（ICLR 2023, arXiv:2210.17323）技术评述 | https://research.rudrite.com/gptq | 2026-06-13 | "8.68 3-bit OPT-175B perplexity vs 8.34 FP16 — quantized in ~4 GPU hours on one A100"；"GPTQ 4-bit 8.37" | H |
| [^14^] | QServe W4A8KV4 与 2.4-3.5× | MLSys 2025 摘要页 + 官方 slides | https://proceedings.mlsys.org/paper_files/paper/2025/hash/fbe2b2f74a2ece8070d8fb073717bda6-Abstract-Conference.html | 2025-05-12 | "existing INT4 quantization methods suffer from significant runtime overhead (20-90%) when dequantizing..."；"Up to 2.4x-3.5x faster than TensorRT-LLM on A100, L40S" | H |
| [^15^] | BitNet b1.58 2B4T 指标 | Azure AI 模型目录（官方卡） | https://ai.azure.com/catalog/models/microsoft-bitnet-b1.58-2b-4t | 2026-04-20 页面 | "Memory (Non-emb) 0.4GB；Latency (CPU Decoding) 29ms；Energy 0.028J"；"W1.58A8... trained from scratch" | H |
| [^16^] | bitnet.cpp 5-7× ARM 加速、ACL 2025 | awesome-llm-paper 汇总（引 ACL 2025, arXiv:2502.11880） | https://github.com/chenhangcuisg-code/awesome-llm-paper/blob/main/quantization/02-extreme-low-bit-bitnet.md | 2026-05-29 | "Bitnet.cpp ... ACL 2025 ... 5–7× speedup over llama.cpp Q4_0 on ARM / Apple Silicon." | M |
| [^17^] | Medusa 2.2×/2.3-2.8× | chatpaper 论文摘要（ICML 2024, arXiv:2401.10774） | https://chatpaper.com/zh-CN/paper/37138 | 2026-01-14 | "Medusa-1 可以实现超过 2.2 倍的加速... Medusa-2 进一步将加速提高到 2.3-2.8 倍" | M |
| [^18^] | EAGLE-3 最高 6.5×、SGLang batch64 +38% | NeurIPS 2025 官方 poster 摘要 | https://neurips.cc/virtual/2025/poster/119930 | 2025-12-02 | "EAGLE-3 achieves a speedup ratio up to 6.5x... In the SGLang framework, EAGLE-3 achieves a 1.38x throughput improvement at a batch size of 64." | H |
| [^19^] | EAGLE-2 均值 3.05× | emergentmind 论文解析（EMNLP 2024） | https://www.emergentmind.com/topics/eagle-2 | 2025-12-29 | "EAGLE-2 (dynamic) 3.05× (up to 4.26×: HumanEval)" | M |
| [^20^] | EdgeLLM 端侧投机解码最高 9.3× | arXiv:2604.07857 综述转述（原论文 IEEE TMC 2025） | https://arxiv.org/html/2604.07857v1 | 2026-04-09 | "Xu et al. propose EdgeLLM... achieving up to 9.3× speedup in per-token generation without sacrificing accuracy" | M（综述转述一手） |
| [^21^] | sd.npu：投机解码 NPU 协同执行 | arXiv:2510.15312 | https://arxiv.org/html/2510.15312v4 | 2025-12-17 | "Accelerating Mobile Language Model via Speculative Decoding and NPU-Coordinated Execution... sd.npu complements these work by incorporating system-algorithm co-design" | H |
| [^22^] | Prompt Cache TTFT GPU 8×/CPU 60× | MLSys 2024 论文（arXiv:2311.04934） | https://arxiv.org/pdf/2311.04934 | 2024 | "The improvements range from 8x for GPU-based inference to 60x for CPU-based inference, all while maintaining output accuracy" | H |
| [^23^] | 端侧 NPU KV 复用系统 + 框架空白论断 | arXiv:2609.34727 | https://arxiv.org/html/2609.34727v1 | 2026-09-28 | "They typically provide little or no support for persistent KV reuse across requests..."；"delivers 1.5×–5.4× prefill speedup over original ExecuTorch... cuts TTFT by 40%–60%" | H |
| [^24^] | ElastKV 跨精度 KV 复用 | ICDCS 2026 论文 PDF | https://zhengzhenzhe220.github.io/papers/ICDCS26.pdf | 2026 | "ElastKV limits average accuracy loss to within 2% while achieving nearly 3× recomputation speedup over full recomputation" | H |
| [^25^] | MobiLoRA 端侧 LoRA KV 优化 | ACL Anthology 2025.acl-long.1140 | https://aclanthology.org/2025.acl-long.1140/ | 2025-07 | "MobiLoRA accelerates LoRA-based LLM inference by 57.6% on mobile devices."（PDF 正文为 18.1%–81.3% TTFT） | H |
| [^26^] | DroidSpeak 跨微调变体 KV 共享 | USENIX NSDI 2026 | https://www.usenix.org/conference/nsdi26/presentation/liu-yuhan | 2026-05 | "achieves up to 4x throughput improvement and about 3.1× faster prefill (time to first token), with negligible loss of quality" | H |
| [^27^] | S-LoRA/Punica 云端多 LoRA 先例 | arXiv:2311.03285 / 2310.18547 综述解析 | https://ai-infrastructure.net/multi-lora-serving/ | 2026-07-02 | "S-LoRA's paper showed serving 2,000 concurrent LoRA adapters on a single A100 with under 10% throughput loss... Punica ~12× throughput at ~2ms/token added latency" | M |
| [^28^] | LLMaaS/LLMS 系统服务范式 | arXiv:2403.11805（SenSys 2026） | https://arxiv.org/abs/2403.11805 | 2024-03-18 | "we propose a new paradigm of mobile AI: LLM as a system service... reduces context switching latency by up to 2 orders of magnitude" | H |
| [^29^] | ElastiLM 弹性 SLO 服务 | ACM MobiCom 2025（dl.acm.org） | https://dl.acm.org/doi/10.1145/3680207.3765259 | 2025-09-01 | "outperforms 7 strong baselines in (absolute) accuracy by up to 14.83% and 10.45% on average, with <1% TTFT switching overhead" | H |
| [^30^] | PowerInfer-2 手机 47B 11.68 tok/s | arXiv:2406.06282 | https://arxiv.org/abs/2406.06282v2/ | 2024-06-10 | "achieving up to a 29.2x speed increase... the first system to serve the TurboSparse-Mixtral-47B model with a generation rate of 11.68 tokens per second on a smartphone" | H |
| [^31^] | LLM in a flash 2× DRAM、4-5×/20-25× | Apple 论文 arXiv:2312.11514（ACL 2024） | https://arxiv.org/pdf/2312.11514 | 2024-07-30 | "running models up to twice the size of the available DRAM, with a 4-5x and 20-25x increase in inference speed compared to naive loading approaches in CPU and GPU" | H |
| [^32^] | llm.npu ASPLOS 2025 指标 | 作者主页 PDF（xumengwei.github.io） | https://xumengwei.github.io/files/ASPLOS25-NPU.pdf | 2025 | "For the first time, llm.npu achieves more than 1,000 tokens/sec prefilling for a billion-sized model."；"7.3x-18.4x faster than baselines on CPU" | H |
| [^33^] | llama.cpp LoRA 热插拔与 KV 失效陷阱 | GitHub issue #10377 / discussion #8849 | https://github.com/ggml-org/llama.cpp/issues/10377 | 2024-11-18 | "Server now supports hot-swapping LoRA adapters via /lora-adapters endpoint..."；"when we change the lora scale, we must clear the cache" | H |
| [^34^] | MLC/TVM PagedKVCache（page=16） | Apache TVM 官方教程 | https://tvm.apache.org/docs/how_to/tutorials/optimize_llm.html | 检索于 2026-11 | "Apache TVM provides a PagedKVCache... page_size=16" | H |
| [^35^] | llama.cpp 后端清单与 KV 重构 | llama.cpp docs/build.md + openSUSE RPM changelog | https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md | 2025-08（b6269） | "CPU Build; BLAS; Metal; SYCL; CUDA; MUSA; HIP; Vulkan; CANN..."；"KV cache: unified handling improvements, support for reuse" | H |
| [^36^] | NPU prefill 强 decode 弱交叉实测；Hexagon 双后端 | arXiv:2607.05475 + llama.cpp RFC #26227 | https://arxiv.org/html/2607.05475v1 | 2026-07-06 | "NPU GENIE w4 prefill 1213.0–1463.7 tok/s... decode 20.7–23.1"；"the fastrpc backend and the dspqueue backend are complementary, not competitive" | H |
| [^37^] | OSDI'26 Sereno / EuroSys'26 / ASPLOS'25 Neuralink | iamseonghoon/Awesome-On-Device-AI-Inference | https://github.com/iamseonghoon/Awesome-On-Device-AI-Inference | 2025-04-14（列表） | "[OSDI 2026] Inference in the Shadows: Taming Memory Bandwidth Contention... [ASPLOS 2025] Neuralink..." | L（线索，未逐篇核对） |
| [^38^] | ExecuTorch 1.0 GA 时间 | andrewbush.org 分析 | https://andrewbush.org/posts/enterprise-vs-consumer-inference/ | 2026-08-12 | "ExecuTorch hit 1.0 GA in October 2025 and 1.1 in January 2026, with a 50 KB runtime and backends for Core ML, Qualcomm QNN/Hexagon, XNNPACK and MediaTek." | M |
| [^40^] | llama.cpp KV 量化现状与 NVFP4 提案 | GitHub issue #26989 | https://github.com/ggml-org/llama.cpp/issues/26989 | 2026-08-12 | "Add support for nvfp4/fp4 as valid options for --cache-type-k and --cache-type-v... q4_0 reduces memory to 4 bits but can suffer from accuracy degradation" | H |

---

### 附：检索覆盖说明
独立检索 40+ 次（框架格局 8、量化 8、投机解码 8、KV/系统 10、LoRA/共享 6+），一手来源占比约 70%。未能核实项已标 L/M 级置信度；MLC-LLM 官方性能数字缺失（官方未维护公开基准），以第三方实测（arXiv 2607.05475）为准。

# AgentOS 组件调研 · 维度 C：端云路由 + LoRA 生态（推理框架与推理能力）

> 调研日期：2026-11-06；时间范围以 2024-01 ~ 2026-11 为主，奠基性工作标注年份。
> 来源标准：官方文档/技术博客/发布会优先；顶会+arXiv 次之；媒体仅作线索并降置信度。
> 共执行 32 次独立搜索；官方原文抓取受站点审计限制（security.apple.com / firebase.google.com 直连被拒），相应论断以多源交叉引证并标注置信度。

---

## 1. 技术谱系表

### 1.1 端云路由（混合推理）

| 谱系 | 代表工作 | 年份 | 路由依据 | 隐私机制 | 性质 |
|---|---|---|---|---|---|
| 奠基：计算卸载/切分 | Neurosurgeon (Kang et al., ASPLOS 2017)；Split Computing & Early Exiting 综述 (Matsubara et al., ACM CSUR 2022)[^27^][^28^] | 2017/2022 | 按层切分 DNN、早退 | 无（传输中间激活） | 学术奠基 |
| 级联/成本路由（查询级） | FrugalGPT (TMLR 2024, 成本最高降 98%)[^21^]；Hybrid LLM (Microsoft, arXiv 2404.14618, 2024)[^22^]；RouteLLM (ICLR 2025)[^23^] | 2023–2025 | 成本/质量、偏好数据训练路由器 | 无（同一信任域内模型选择） | 学术+生产（Anyscale 部署 RouteLLM，20 万查询省 85% 成本）[^24^] |
| 令牌级协作路由 | CITER (arXiv 2502.01976, 2025)[^25^]；CE-CoLLM 置信度早退 (arXiv 2411.02829)[^26^]；DSSD 分布式切分投机解码 (2025)[^29^] | 2024–2025 | 每 token 置信度/熵 | 中间激活上传（弱隐私） | 学术 |
| 端云任务分解协作 | Minions/MinionS (Stanford 等, arXiv 2502.15964, 2025-02)[^30^] | 2025 | 本地读全量上下文+云端分解子任务 | 原始文档不出端（仅摘要/子任务上云） | 学术（Apple 合作方署名背景强） |
| 系统级生产路由：Apple | Private Cloud Compute（PCC）+ 端侧 AFM + System Orchestrator | 2024-06 发布，2026-06 扩展[^1^][^2^][^3^][^4^] | 复杂度/能力/上下文长度/热状态/电池/网络/配额 | 无状态计算+签名软件栈+Secure Enclave/Secure Boot+公开可验证镜像+attestation | 生产（唯一大规模落地的"可验证隐私"路由） |
| 系统级生产路由：Google | Firebase AI Logic Hybrid Inference + ML Kit Prompt API（Gemini Nano/AICore） | 2026-04 Android 上线；2026-05 I/O 扩展 iOS/Gemma[^5^][^6^][^7^] | 规则式枚举（PREFER_ON_DEVICE 等四档）+开发者自定义 | 无 TEE；隐私=数据不出端（端侧路径）+App Check 配额保护 | 生产（规则式，承认是"initial solution"）[^8^] |
| 系统级生产路由：NVIDIA | OpenShell privacy router / NemoClaw（GTC 2026-03-16，Apache 2.0 开源）[^9^][^10^] | 2026 | 用户 YAML 策略（隐私/成本），deny-by-default | 进程外策略执行、凭证剥离、`inference.local` 端点、header 白名单 | 生产（面向 Agent 沙箱，非手机 OS） |
| 机密推理底座 | NVIDIA H100/B200 GPU TEE（CC 模式）[^11^][^12^]；PlanetServe 双隐私档 (arXiv 2504.20101)[^13^] | 2022(H100)/2024–2026 | 用户可选隐私档 | GPU TEE+远程证明+PCIe AES-GCM-256 加密+CPU TEE(TDX/SEV-SNP)联动 | 硬件/云 |

### 1.2 LoRA 生态（系统级管理与热插拔）

| 谱系 | 代表工作 | 年份 | 关键机制 | 规模/性能数据 |
|---|---|---|---|---|
| 奠基 | LoRA (Hu et al., ICLR 2022)[^31^] | 2021 | 冻结基座+低秩 A/B 矩阵 | — |
| 内核：跨适配器批处理 | Punica SGMV (arXiv 2310.18547, MLSys 2024)[^32^][^33^] | 2023 | Segmented Gather Matrix-Vector，批内混合适配器共享基座 GEMM | 吞吐 12× vs SOTA；每 token 仅 +2ms |
| 系统：内存分页 | S-LoRA (arXiv 2311.03285, MLSys 2024)[^34^] | 2023 | Unified Paging：adapter 权重与 KV cache 同一分页内存池；分级存储（GPU←主存←盘） | 单 A100-80GB 同时服务 2,000 adapter；吞吐 4× vLLM-packed、30× PEFT |
| 系统：动态编排 | dLoRA (OSDI 2024)[^35^] | 2024 | 合并/非合并动态切换、credit-based 批处理、请求/适配器跨副本迁移 | — |
| 生产引擎：vLLM | `--enable-lora`/`--max-loras`/`--max-cpu-loras`；运行时 `/v1/load_lora_adapter` 热加载（v0.6.2+）；`load_inplace` 同名热替换（2026-01 合入）[^36^][^37^][^38^] | 2024–2026 | GPU/CPU 两级 LRU 缓存；按请求 `model` 字段路由到 adapter | RL 场景热换 adapter <100ms[^39^] |
| 生产引擎：SGLang | `--lora-paths`/`--max-loras-per-batch`/pinned adapter/LRU|FIFO 逐出/csgmv 后端/overlap loading[^40^][^41^] | 2024–2026 | CPU 内存池+GPU 槽位；adapter 标识进入 RadixAttention 前缀缓存键 | csgmv 比 triton 快 20–80%；overlap loading 中位 TTFT 降 ~35% |
| 生产引擎：LoRAX/TensorRT-LLM | LoRAX (Predibase) 分层缓存 GPU→CPU→盘；TRT-LLM 编译期声明 max rank/target modules[^42^][^43^] | 2023–2026 | — | LoRAX：128 adapter 时延迟 +~20% |
| OS 级先例：Apple | AFM 运行时热插拔 adapter（rank16/16bit/数十 MB）；Foundation Models framework `.fmadapter`+训练工具包+Background Assets 下发 | 2024-06（技术报告）/2025-06（WWDC25 开放训练）/2026（WWDC26 Core AI）[^14^][^15^][^16^][^17^] | adapter 动态加载、内存暂存、换入换出；adapter 与基座模型版本绑定 | 3B 端侧模型上 rank-16 adapter 仅数十 MB |
| 芯片级先例：Qualcomm | 2024 白皮书：LoRA 并行/热切换、"fast switching between adapters"；Stable Diffusion+LoRA 首登 Android 手机（MWC 2024）；NeurIPS 2024 demo（AIMET 量化+切换时元数据更新）[^18^][^19^][^20^] | 2024 | NPU 上 adapter 低驻留+快速切换 | — |
| 芯片级先例：联发科 | Dimensity 9300+ NeuroPilot LoRA Fusion 2.0[^44^] | 2024-05 | 端侧 LoRA 融合 | — |
| 端侧多租户研究 | EdgeLoRA (MobiSys 2025, arXiv 2507.01438)[^45^]；MobiLoRA (ACL 2025)[^46^] | 2024–2025 | EdgeLoRA：自适应 adapter 选择路由器+异构内存缓存池+批量 LoRA 推理；MobiLoRA：按 adapter 复用 KV cache | EdgeLoRA：Jetson AGX Orin 上 1,000+ adapter 并发、吞吐 2–4× llama.cpp；MobiLoRA：TTFT 最高降 81.3% |
| 端侧训练 | QVAC Fabric LLM (Tether, 2025-12)[^47^] | 2025 | 手机 GPU（Adreno/Mali/Metal/Vulkan）上 LoRA 微调 | — |

---

## 2. 关键数据（带出处日期）

**端云路由**
- Apple PCC（2024-06-10 发布）：五大保证——"stateless computation on personal user data, enforceable guarantees, no privileged access, non-targetability, verifiable transparency"；2024-10 开放 Virtual Research Environment、公开 PCC 镜像、悬赏最高 $1M[^1^][^3^][^48^]。
- PCC 延迟量级（第三方开发者实测叙述，2026）：端侧推理首 token <100ms；PCC 路径首 token 增加网络往返约 200–500ms[^49^]（置信度：中，非官方）。
- WWDC26（2026-06-08）：PCC 扩展至 Google Cloud + NVIDIA GPU 基础设施；AFM 3 分 Core/Core Advanced/Cloud/Cloud Pro 四层；System Orchestrator 按"task complexity, privacy sensitivity, latency requirements, device thermal state"逐 prompt 路由；端侧 Core Advanced 为 20B 稀疏模型（1–4B 激活，权重驻留 NAND）[^4^][^50^]。
- PCC 开发者 API：`PrivateCloudComputeLanguageModel`，32K 上下文、有日配额、需 entitlement（WWDC26）[^51^][^52^]。
- Firebase AI Logic hybrid inference（Android，2026-04 上线；`firebase-ai:17.11.0`+`firebase-ai-ondevice:16.0.0-beta01`）：四档 `InferenceMode`（PREFER_ON_DEVICE / PREFER_IN_CLOUD / ONLY_ON_DEVICE / ONLY_IN_CLOUD）；官方自述"simple rule-based routing approach as an initial solution"；端侧限单轮、文本或单图输入；Nano v3 需 ≥12GB RAM 旗舰机[^5^][^8^][^53^]。Google I/O 2026（2026-05）：hybrid inference 登陆 iOS、Android 侧支持 Gemma 4[^7^]。
- NVIDIA OpenShell/NemoClaw（GTC 2026-03-16）：隐私路由器将敏感请求路由本地 Nemotron、其余上云；"The routing follows your cost and privacy policies — not the agent's preferences"；`inference.local` 剥离 sandbox 凭证、仅转发 header 白名单、注入后端凭证；策略热更新 ~5s 生效[^9^][^10^][^11^]。
- RouteLLM（ICLR 2025）：MT-Bench 上 85% 成本节省、保持 95% GPT-4 质量，仅 14–26% 查询进强模型；Anyscale 生产 20 万查询省 85%[^23^][^24^]。
- Minions（2025-02）：朴素对话协议远端成本降 30.4× 但只恢复 87% 性能；MinionS 分解协议成本降 5.7×、恢复 97.9%[^30^]。
- CE-CoLLM（2024-11）：置信度早退 + 隐状态异步上传；云请求量降至 27.7–49.6%，云端计算卸载 84.53%，总推理时间降 13.81%，通信量降 99%+[^26^]。
- GPU TEE 开销：H100 CC 模式 I/O 加密引入性能开销（arXiv 2409.03992，2024-09 实测）；第三方运营方口径 5–15% 推理开销、大模型额外 50–100ms 延迟[^12^][^13^]（置信度：中）。

**LoRA 生态**
- Punica（2023-10）：SGMV 内核，12× 吞吐、每 token +2ms[^32^][^33^]。
- S-LoRA（2023-11）：Unified Paging 统一管理 adapter 权重与 KV cache；单 A100 2,000 adapter；4×/30× 吞吐[^34^]。
- vLLM：`--max-loras` 默认 1（批内并发 adapter 数）、`--max-lora-rank` 默认 16、`--max-cpu-loras` CPU 侧缓存（必须 ≥ max-loras，LRU 逐出）；`VLLM_ALLOW_RUNTIME_LORA_UPDATING=True` 开放 `/v1/load_lora_adapter` `/v1/unload_lora_adapter`，官方明确警告"仅限隔离可信环境"；`load_inplace`（PR #31326，2026-01-20 合入）支持同名 adapter 原地热更新，面向 RL 训练循环[^36^][^37^][^38^]。
- SGLang：`--max-loras-per-batch` 默认 8；pinned adapter 上限 `max-loras-per-batch - 1`；`--enable-lora-overlap-loading` 异步 H2D 传输隐藏加载延迟，对抗性负载下中位 TTFT 降 ~35%；adapter 标识写入前缀缓存 `extra_key`，`(lora0, tokens[0:100])` 与 `(lora1, tokens[0:100])` 是不同缓存条目[^40^][^41^][^54^]。
- Apple AFM 技术报告（2024-07-29，arXiv 2407.21075）："The adapter models can be dynamically loaded, temporarily cached in memory, and swapped"；3B 端侧模型 rank-16/16-bit adapter 仅数十 MB；量化精度恢复 adapter（accuracy-recovery adapter）先行训练，功能 adapter 在其上初始化[^14^]。2025 技术报告（arXiv 2507.13575）：Foundation Models framework 暴露 "LoRA adapter fine-tuning"[^15^]。
- Apple adapter 训练工具包（WWDC25 起）：明确使用 LoRA/PEFT；`.fmadapter` 导出；经 Background Assets 按 asset pack 下发；adapter 与系统模型版本绑定，基座升级须重训；训练要求 Apple silicon Mac ≥32GB 内存或 Linux GPU[^16^][^17^]。
- EdgeLoRA（MobiSys'25）：Jetson AGX Orin 并发 1,000+ adapter（llama.cpp 上限 ~50）；吞吐 2–4×；adapter 路由器本身即 LoRA 微调的分类头[^45^]。
- MobiLoRA（ACL 2025）：复用各 adapter 的 KV cache、仅 prefill 增量输入，TTFT 最高降 81.3%[^46^]。
- 商用多 LoRA 服务延迟口径（2026 汇总）：动态换 adapter 增加 2ms/token（Punica）、128 adapter 时 +20%（LoRAX）、serverless 场景 ~10% 吞吐损失（Together AI）、TTFT +10–30%（Fireworks）[^55^]。

---

## 3. 趋势判断（收敛方向 + 空白点）

**收敛方向**
1. **"端侧默认 + 云端升级"已成为三大厂共识架构**：Apple（AFM→PCC→第三方）、Google（Nano/AICore→Firebase 云 Gemini）、NVIDIA（本地 Nemotron→前沿云模型）均在 2024–2026 落地同一形态。差异在路由器的"智能度"：Apple 用系统编排器做逐 prompt 多维决策（不公开细节），Google 公开承认当前仅是规则式枚举，NVIDIA 用声明式策略。学界（RouteLLM/CITER/Minions）提供了学习式、token 级、任务分解式的更细粒度方案，但尚未被任何一家完整吸收。
2. **隐私保证分化为两档**：(a) 传输级——数据不出端即隐私（Google/Firebase 路径）；(b) 架构级——无状态+签名镜像+公开透明日志+远程证明（Apple PCC、NVIDIA GPU TEE 阵营）。PCC 是 (b) 档唯一大规模商用先例，且 2026 年已把该信任模型扩展到第三方机房（Google Cloud/NVIDIA），证明"可验证隐私云"可脱离自有数据中心存在[^4^][^48^]。
3. **LoRA 作为"OS 级个性化/特化层"正在从推理引擎下沉到芯片与 OS**：服务端（vLLM/SGLang/LoRAX）→ OS（Apple AFM adapter、.fmadapter 生态）→ 芯片（Qualcomm 白皮书、联发科 LoRA Fusion、Taalas ASIC 硬连线 LoRA）[^18^][^44^][^56^]。多方独立竞争者收敛到同一选择："adapter 是基座模型与硬件之间的定制层"[^56^]。
4. **adapter 内存管理与 KV cache 管理正在统一**：S-LoRA Unified Paging（2023）开先河；SGLang 把 adapter 标识纳入前缀缓存键；MobiLoRA 按 adapter 复用 KV cache。方向明确：权重（基座+adapter）与 KV cache 进入同一个分页/淘汰体系——这与我方"模型权重与 KV cache 可分页"的立场完全一致。
5. **热插拔延迟已被压到亚百毫秒级**：vLLM RL 场景热换 <100ms；SGLang overlap loading 隐藏 H2D 传输；端侧 AFM adapter 为"数十 MB、内存暂存、即换即用"量级。

**空白点（未被解决的问题）**
1. **路由决策的可解释性与用户/企业可控性**：Apple 路由完全黑盒（无用户开关可强制端侧，仅可整体关 PCC[^57^]）；企业合规需要"路由决策日志"，目前只有第三方架构建议[^58^]。隐私分级路由（按数据敏感度而非任务复杂度）在三大厂方案中均是空白——Apple 按能力路由，Firebase 按可用性路由，OpenShell 按静态策略路由。
2. **路由器的安全面**：Apple 路由层被研究者指出存在流量分析侧信道（attestation 通道+边缘元数据）[^59^]；PCC 缺少可复现构建（WiSec 2026 独立分析）[^48^]。
3. **多 adapter 前缀缓存/投机解码组合**：adapter 切换后 draft model 需配套重训（Apple 文档明示："If you choose not to train the draft model, speculative decoding will not be available for your adapter's use case"[^16^]）；SGLang 的 MoE LoRA 仍在落地中（PR #14105）[^41^]。
4. **端侧 LoRA 的隐私×安全治理**：vLLM 官方警告运行时加载接口不应暴露在生产环境[^37^]；端侧第三方 adapter 的签名/来源验证（Apple 以 entitlement+Background Assets 解决，Android 侧无等价物）。
5. **成本核算公开数据稀缺**：除 RouteLLM/Minions 的学术基准外，PCC/云路径的真实单价与延迟分布无官方数据。

---

## 4. 对我方的启发（逐条）

我方立场：(a) 端云之间按隐私/成本/延迟的路由层；(b) 底座模型系统服务共享 + LoRA 热插拔；(c) 模型权重与 KV cache 可分页。

1. **路由层——强支持**。三大厂 2024–2026 全部落地混合推理路由，证明这是 AgentOS 的必选项而非可选项。**需要修订**：路由输入维度建议明确包含"隐私分级"——现有商用方案无人把数据敏感度作为一等路由信号（Apple 按能力、Firebase 按可用性、OpenShell 静态策略最接近但未分级）；这既是空白点也是我方的差异化空间。工程上应预留路由决策日志接口（企业合规刚需[^58^]）。
2. **LoRA 热插拔——强支持**。从 Apple（AFM 运行时换 adapter、数十 MB）到 vLLM/SGLang（运行时 load/unload、pin、LRU）到芯片厂（Qualcomm/MTK/Taalas），"共享基座 + 小 adapter 热切换"是全行业收敛方向。**支持性细节可直接复用**：adapter 大小量级（rank16 数十 MB）、热换延迟量级（<100ms）、pin 常用 adapter 防饿死（SGLang 上限 max-1 的设计约束）、adapter 与基座版本绑定及重训策略（Apple）。
3. **权重/KV 可分页——支持，且需修订扩容**。S-LoRA Unified Paging、SGLang adapter-aware 前缀缓存、MobiLoRA 按 adapter 复用 KV 共同表明：**分页池应同时覆盖基座权重、adapter 权重、KV cache 三类对象，且 KV 缓存键必须含 adapter 标识**，否则跨 adapter 前缀复用会出错或失效[^34^][^54^][^46^]。我方立场只提"模型权重与 KV cache"，建议显式加入 adapter 权重与 adapter 维度的缓存键。
4. **端侧 adapter 生态治理——挑战**。Apple 用 entitlement + asset pack + 版本锁定做闭环；Android/开源栈（vLLM）明确警告动态加载是管理平面风险[^16^][^37^]。我方若开放第三方 LoRA 热插拔，必须同步设计签名/权限/版本治理，否则"热插拔"即成攻击面。
5. **隐私保证层级——需要修订**。仅"按隐私路由"不够：一旦请求上云，需要 PCC 式"无状态+可验证"或 GPU TEE 式"机密推理"承接，否则隐私承诺降级为政策承诺。Apple 2026 年把该信任模型扩展到第三方基础设施，说明可验证层可以外挂于异构云[^4^]。建议路由层输出与"云端承接机制"绑定（本地→明文信任 / PCC 类→可验证 / 普通云 API→明示降级）。
6. **token 级/任务分解协作——支持但谨慎**。CITER/MinionS 证明更细粒度协作的成本收益（5.7–30×），但通信中间激活有弱隐私性、工程复杂度高；建议列为二期演进方向，路由层预留 query 级以下粒度的扩展点[^25^][^30^]。

---

## 5. 组件特有输出素材

### 5.1 端云路由方案对比表（方案 × 路由依据 × 隐私机制 × 延迟数据）

| 方案 | 路由依据 | 决策粒度 | 隐私机制 | 延迟/成本数据 | 状态 |
|---|---|---|---|---|---|
| Apple 端侧 AFM ↔ PCC ↔（2026 起第三方前沿模型） | 任务复杂度、上下文长度、热状态、电池、网络、feature class、routing_hint；System Orchestrator 逐 prompt | 请求级 | PCC：无状态计算、签名固件、Secure Enclave、公开镜像+透明日志、attestation、无特权访问 | 端侧 TTFT <100ms；PCC +200~500ms（第三方口径）[^49^][^59^] | 生产（2024-06 起） |
| Firebase AI Logic hybrid（Gemini Nano/AICore ↔ 云 Gemini） | 四档枚举 PREFER/ONLY_ON_DEVICE/IN_CLOUD + 开发者自定义（延迟、电量、负载、查询复杂度） | 请求级（单轮） | 数据不出端（端侧路径）；App Check 防配额盗用；无 TEE/无状态承诺 | 无端云延迟对比官方数据；Nano 上限 4K token/请求[^5^][^8^][^53^] | 生产（2026-04 Android / 2026-05 iOS） |
| NVIDIA OpenShell privacy router（NemoClaw） | 用户声明式 YAML 策略（隐私/成本），deny-by-default，进程外执行 | 请求级 | 凭证剥离、header 白名单、`inference.local` 本地端点、本地 Nemotron 承接敏感请求；无 TEE | 策略热更新 ~5s；无推理延迟数据[^9^][^10^][^11^] | 生产（2026-03，Apache 2.0） |
| RouteLLM（学术→Anyscale 生产） | 偏好数据训练的路由器预测强模型胜率，阈值校准 | 请求级 | 无（同信任域） | MT-Bench 省 85% 成本@95% 质量；仅 14–26% 进强模型[^23^] | 学术+生产组件 |
| MinionS（学术） | 云端分解子任务→本地并行执行→云端汇总 | 任务分解级 | 原始长文档不出端，仅子任务/摘要上云 | 成本降 5.7×、恢复 97.9% 质量（朴素协议 30.4×/87%）[^30^] | 学术 |
| CITER / CE-CoLLM（学术） | 每 token 置信度/熵 | token 级 | 中间激活上传（弱隐私） | CE-CoLLM：云请求降至 27.7–49.6%、云计算卸载 84.5%、通信量降 99%+[^25^][^26^] | 学术 |
| GPU TEE 机密推理（H100/B200 CC + TDX/SEV-SNP） | 用户选择隐私档（匿名档/内容隐私档） | 部署级 | GPU TEE+远程证明+PCIe AES-GCM-256+加密 bounce buffer | TEE 开销约 5–15%；大模型 +50–100ms（第三方口径）[^12^][^13^] | 云产品（Azure/GCP 部分 SKU） |

### 5.2 推理栈分层图「系统服务层」素材

```
┌─────────────────────────────────────────────────────────────┐
│ 应用/Agent 层：Foundation Models / ML Kit GenAI / OpenAI API │
├─────────────────────────────────────────────────────────────┤
│ 端云路由层（本维度核心，系统服务层之上半部）                    │
│  · 路由信号：隐私分级 | 能力/复杂度 | 成本 | 延迟/热状态/网络   │
│  · 决策粒度：请求级（生产现状）→ token 级/任务分解（学术前沿）   │
│  · 隐私承接：本地明文信任 | PCC 式无状态+可验证 | GPU TEE |    │
│    普通云 API（明示降级）                                      │
│  · 先例：Apple System Orchestrator / Firebase InferenceMode / │
│    NVIDIA OpenShell privacy router / RouteLLM                │
├─────────────────────────────────────────────────────────────┤
│ 模型运行时层（系统服务层之下半部）                              │
│  · 共享基座模型常驻（系统级服务，多应用复用）                    │
│  · LoRA 管理器：动态 load/unload、pin、LRU 逐出、overlap 加载  │
│    （vLLM /v1/load_lora_adapter；SGLang pinned+lru/fifo；    │
│     Apple AFM adapter 热换 + .fmadapter + Background Assets）│
│  · 统一分页内存池：基座权重 + adapter 权重 + KV cache          │
│    （S-LoRA Unified Paging；KV 缓存键含 adapter 标识）         │
│  · 批处理内核：SGMV/csgmv 跨 adapter 混合批处理               │
│  · 配套加速：adapter 专属 draft model（投机解码）/前缀缓存      │
├─────────────────────────────────────────────────────────────┤
│ 硬件抽象层：ANE / Hexagon NPU / GPU（厂商原生 adapter 支持：    │
│ Qualcomm 快速切换、MTK LoRA Fusion、Taalas ASIC 硬连线 LoRA）  │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 证据清单

| # | Claim | Source | URL | Date | Excerpt（原文摘录） | Confidence |
|---|---|---|---|---|---|---|
| [^1^] | PCC 五大隐私保证 | Apple Security Research blog（经 hushh.ai 转引核验） | https://security.apple.com/blog/private-cloud-compute/ | 2024-06-10 | "stateless computation on personal user data, enforceable guarantees, no privileged runtime access, non-targetability, and verifiable transparency" | 高 |
| [^2^] | PCC 2024-06-10 发布、Secure Enclave/Secure Boot、无状态 | banthebots.org（引官方公告） | https://www.banthebots.org/explainers/ai-without-sending-data-to-cloud | 2026-10-14 | "Apple announced Private Cloud Compute on June 10, 2024… stateless computation alongside an independently verifiable transparency log" | 高（多源一致） |
| [^3^] | PCC 研究环境+最高 $1M 悬赏（2024-10）；2026-06 扩展 Google Cloud/NVIDIA | Tobias Reithmeier（列 Apple 官方来源清单） | https://www.tobiasreithmeier.de/en/blog/apple-private-cloud-compute | 2026-07-07 | "research environment, source code, bug bounty up to 1 million USD, October 2024… expansion to Google Cloud and NVIDIA, June 2026" | 高 |
| [^4^] | WWDC26：AFM 3 四层、System Orchestrator 路由信号、20B 稀疏端侧模型、PCC 扩展第三方机房 | ecorpit WWDC26 报道 | https://ecorpit.com/wwdc-2026-apple-intelligence-tim-cook-final-keynote/ | 2026-06-08 | "The decision logic considers task complexity, privacy sensitivity, latency requirements and device thermal state" | 中（媒体转述发布会） |
| [^5^] | Firebase hybrid inference 2026-04 上线、包版本、单轮限制 | getsuperculture The Brief | https://getsuperculture.com/thebrief/monday-april-20-2026 | 2026-04-20 | "firebase-ai:17.11.0 and firebase-ai-ondevice:16.0.0-beta01… limited to single-turn text generation" | 中高 |
| [^6^] | InferenceMode 四档语义与自定义路由信号（GBoard、Kakao 先例） | ecorpit（引 Google 官方文档） | https://ecorpit.com/gemini-intelligence-hardware-floor-android-ai-fallback-2026/ | 2026-08-03 | "Cloud models serve as a critical fallback when on-device models… are unavailable due to device hardware or OS constraints" | 高 |
| [^7^] | I/O 2026：hybrid inference 上 iOS、Android 支持 Gemma 4 | Firebase 官方博客 | https://firebase.blog/posts/2026/05/google-io-2026-announcements/ | 2026-05-19 | "Hybrid inference is now available for iOS, and hybrid inference for Android has expanded to support Gemma 4" | 高（官方） |
| [^8^] | Google 自述规则式路由是 initial solution | udfsoft 转 Android 开发者博客（Thomas Ezan） | https://news.udfsoft.com/?app=android | 2026-10-20 | "we implemented a simple rule-based routing approach as an initial solution… planning on providing more sophisticated routing capabilities" | 高（官方博客转录） |
| [^9^] | OpenShell/NemoClaw GTC 2026 发布、Apache 2.0、隐私路由器按本地/云分流 | techjacksolutions | https://techjacksolutions.com/ai-brief/nvidia-nemoclaw-open-source-security-stack-brings-privacy-co/ | 2026-03-19 | "OpenShell routes inference requests between local GPUs and cloud models based on user-defined policies" | 中高 |
| [^10^] | OpenShell 路由"遵循成本与隐私策略而非 agent 偏好"；deny-by-default；进程外执行 | getsliq | https://getsliq.com/blog/nvidia-openshell-explained | 2026-03-17 | "The routing follows your cost and privacy policies — not the agent's preferences." | 中高 |
| [^11^] | `inference.local` 凭证剥离、header 白名单、热更新 ~5s | NVIDIA 官方文档 | https://docs.nvidia.com/openshell/inference/about | 2026（抓取） | "The privacy router strips the original credentials, forwards only approved inference headers, injects the configured backend credentials" | 高（官方文档） |
| [^12^] | H100 GPU TEE 机制与性能开销实测 | arXiv 2409.03992 | https://arxiv.org/html/2409.03992v2 | 2024-09-13 | "Enabling TEE on the nVIDIA H100 GPU introduces performance overheads primarily due to additional encryption and decryption during secure data transfer" | 高 |
| [^13^] | H100 CC：AES-GCM-256 PCIe 加密、bounce buffer、远程证明；TEE 开销 5–15%、大模型 +50–100ms | arXiv 2504.20101（PlanetServe）；Phala | https://www.arxiv.org/pdf/2504.20101v5 ; https://phala.com/learn/How-Nvidia-Enable-Confidential-AI | 2025 / 2025-11-14 | "all PCIe/NVLink traffic is encrypted with AES-GCM-256… plaintext is never exposed outside the enclave"；"Performance overhead: 5-15% for GPU-based AI workloads" | 高（机制）/中（开销数字） |
| [^14^] | AFM adapter 动态加载/暂存/热换；rank16/16bit/数十 MB；accuracy-recovery adapter | Apple 技术报告 arXiv 2407.21075 | https://arxiv.org/html/2407.21075v1 | 2024-07-29 | "The adapter models can be dynamically loaded, temporarily cached in memory, and swapped" | 高 |
| [^15^] | AFM 2025 报告：Foundation Models framework 暴露 LoRA adapter fine-tuning | Apple 技术报告 arXiv 2507.13575 | https://www.arxiv.org/pdf/2507.13575v1 | 2025-07 | "exposes guided generation, constrained tool calling, and LoRA adapter fine-tuning" | 高 |
| [^16^] | adapter 训练工具包=LoRA、.fmadapter、Background Assets、版本绑定、无 draft model 则无投机解码 | blakecrosley（引 Apple 官方文档原文） | https://blakecrosley.com/blog/foundation-models-custom-adapters | 2026-05-04 | "The system model uses a parameter-efficient fine-tuning (PEFT) approach known as LoRA… each adapter is bound to a single system model version" | 高（引官方文档） |
| [^17^] | adapter rank32≈160MB、Background Assets 下发、entitlement | gamut.so | https://www.gamut.so/blog/apple-foundations-models-framework-10-best-practices-for-developing-ai-apps | 2025-09-08 | "LoRA adapters use rank 32… approximately 160MB storage per adapter" | 中 |
| [^18^] | Qualcomm 2024 白皮书：LoRA 并行/热切换、首个 Android 手机 Stable Diffusion+LoRA | 高通官方白皮书 PDF（转载） | https://www.sgpjbg.com/baogao/607412.html | 2024-05-30 | "Multiple LoRA adapters can be used in parallel or swapped out… fast switching between adapters" | 高 |
| [^19^] | Qualcomm MWC 2024：AI Hub 75+ 模型、手机端 LoRA demo | Hackster | https://www.hackster.io/news/qualcomm-launches-its-ai-hub-… | 2024（页面显示2026-10-30 更新） | "Stable Diffusion with Low Rank Adaption (LoRA) running on an Android smartphone" | 高 |
| [^20^] | Qualcomm NeurIPS 2024 demo：AIMET 量化、adapter 切换时元数据更新 | NeurIPS 2024 virtual site | https://neurips.cc/virtual/2024/day/12/10 | 2024-12-10 | "supports fast switching, and retains the low memory footprint of the adapters on device" | 高 |
| [^21^] | FrugalGPT 成本最高降 98% | TMLR 2024（经 dot-loom STUDIES.md 转引） | https://github.com/usedotai/dot-loom/blob/main/docs/STUDIES.md | 2026-06-23 | "matching the best individual LLM with up to 98% lower cost" | 高 |
| [^22^] | Hybrid LLM（Microsoft）：成本-质量查询路由 | arXiv 2404.14618 | https://arxiv.org/abs/2404.14618 | 2024-04 | "Hybrid llm: Cost-efficient and quality-aware query routing" | 高 |
| [^23^] | RouteLLM：ICLR 2025、85% 成本节省@95% 质量、14–26% 进强模型 | ICLR 2025 / digitalapplied 综述 | https://www.digitalapplied.com/blog/llm-model-routing-2026-cost-quality-optimization-engineering-guide | 2026-06-14 | "85% cost savings on MT Bench at 95% of GPT-4 quality… strong model on only 14% of queries" | 高 |
| [^24^] | Anyscale 生产部署 RouteLLM：20 万查询、85% 成本降 | getnadir（引 Anyscale 工程博客） | https://getnadir.com/blog/routellm-74-percent-gpt4-calls-dont-need-gpt4/ | 2026-06-27 | "Anyscale deployed RouteLLM on a production workload of 200,000 queries… 85% cost reduction" | 中 |
| [^25^] | CITER：token 级路由协作解码 | arXiv 2502.01976 | https://arxiv.org/html/2502.01976v6 | 2025-09-10（v6） | "token-level routing methods offer more fine-grained control" | 高 |
| [^26^] | CE-CoLLM：置信度早退、云请求降至 27.7–49.6%、云计算卸载 84.53%、通信降 99%+ | arXiv 2411.02829 | https://arxiv.org/html/2411.02829v2 | 2025-06-08（v2；首发 2024-11-05） | "reduces cloud requests to 49.58% on Alpaca and 27.73% on XSum… 99.15% reduction" | 高 |
| [^27^] | Neurosurgeon：云-边协作智能切分开山 | ASPLOS 2017（经 Splitwise 引文） | https://arxiv.org/html/2512.23310v1 | 2017 | "Neurosurgeon: Collaborative Intelligence Between the Cloud and Mobile Edge" | 高 |
| [^28^] | Split computing & early exit 综述 | ACM Computing Surveys 55(5) 2022 | https://dl.acm.org/doi/full/10.1145/3698767（引文核验） | 2022-12 | "Split computing and early exiting for deep learning applications: Survey and research challenges. ACM Computing Surveys 55, 5 (2022), 1–30" | 高 |
| [^29^] | DSSD：分布式切分投机解码；Jupiter INFOCOM 2025；EdgeShard 2024 | arXiv 2607.13093 引文 | https://arxiv.org/html/2607.13093 | 2026-07-23 | "DSSD: efficient edge-device LLM deployment and collaborative inference via distributed split speculative decoding" | 高 |
| [^30^] | Minions：30.4×/87%（朴素）与 5.7×/97.9%（MinionS） | arXiv 2502.15964 | https://arxiv.org/html/2502.15964v1 | 2025-02-21 | "MinionS平均降低了5.7倍的成本，同时恢复了远程模型单独的97.9%的性能"（中文转述摘要） | 高 |
| [^31^] | LoRA 原始论文 | ICLR 2022 / arXiv 2106.09685 | https://arxiv.org/abs/2106.09685 | 2021 | "LoRA: Low-Rank Adaptation of Large Language Models" | 高 |
| [^32^] | Punica：SGMV、12× 吞吐、+2ms/token | arXiv 2310.18547 / MLSys 2024 论文 PDF | https://proceedings.mlsys.org/paper_files/paper/2024/file/054de805fcceb78a201f5e9d53c85908-Paper-Conference.pdf | 2023-10 / 2024 | "SGMV parallelizes the feature-weight multiplication of different requests in a batch, groups requests by the LoRA model" | 高 |
| [^33^] | Punica GitHub：12× 吞吐自述 | github.com/punica-ai/punica | https://github.com/punica-ai/punica | 2026-08-30（页面更新） | "Punica achieves 12x throughput compared to state-of-the-art systems" | 高 |
| [^34^] | S-LoRA：Unified Paging、2000 adapter/A100、4×/30× | arXiv 2311.03285 | https://arxiv.org/abs/2311.03285 | 2023-11-06 | "Unified Paging uses a unified memory pool to manage dynamic adapter weights… and KV cache tensors… serve 2,000 adapters simultaneously" | 高 |
| [^35^] | dLoRA：OSDI 2024 动态编排请求与 adapter | OSDI 2024（经 ICPP'25 MixLoRA 引文） | https://dl.acm.org/doi/10.1145/3754598.3754605 | 2024 | "dLoRA: Dynamically Orchestrating Requests and Adapters for LoRA LLM Serving. In OSDI 2024" | 高 |
| [^36^] | vLLM 热加载/卸载端点、安全警告、标志默认值 | gpusmith（核对 vLLM v0.32.0 源码与文档，2026-10-18/28 核验） | https://gpusmith.com/articles/en/pdfs/multi-lora-serving-many-adapters-one-gpu.pdf | 2026-10-30 | "The docs warn: 'This feature comes with security risks. It should not be used in production unless it is an isolated, fully trusted environment.'" | 高（源码级核验） |
| [^37^] | vLLM 运行时 LoRA 更新 v0.6.2+、VLLM_ALLOW_RUNTIME_LORA_UPDATING | spheron / tinfoilsh demo（核对官方文档） | https://github.com/tinfoilsh/demo-personalization/blob/main/core_server.md | 2026-06-25 | "max-cpu-loras must be ≥ max-loras; vLLM LRU-evicts beyond it" | 高 |
| [^38^] | vLLM `load_inplace` 原地热更新 PR #31326（2026-01-20 合入） | GitHub issue（torad-labs） | https://github.com/torad-labs/qgre-engine/issues/3 | 2026-07-05 | "for RL training, it is useful to be able to update a lora inplace with the same name" | 高 |
| [^39^] | 热换 adapter <100ms（vLLM runtime LoRA API 用于 RL/agentic TTT） | arXiv 2607.03441 | https://arxiv.org/html/2607.03441v1 | 2026-07-03 | "hot-swap the resulting adapter into the serving engine in under 100 ms" | 高 |
| [^40^] | SGLang LoRA 参数体系、pinned 上限、eviction policy、csgmv/triton 后端 | SGLang 官方文档 | https://sgl-project.github.io/advanced_features/lora.html | 2026-10-26 | "lora_eviction_policy… lru (default)… fifo… pinned adapters to max-loras-per-batch - 1" | 高（官方） |
| [^41^] | SGLang overlap loading TTFT -35%；csgmv 快 20–80%；MoE LoRA 进行中 | SGLang 官方文档 / changyi.fun 源码拆解 | https://sgl-project-sglang-93.mintlify.app/advanced/lora ; https://changyi.fun/posts/sglang_lora_en/ | 2026-03-04 / 2026-02-22 | "Benchmarks show ~35% reduction in median TTFT under adversarial conditions" | 高 |
| [^42^] | LoRAX：GPU→CPU→盘分层缓存、128 adapter +20% 延迟 | lin-guanguo LoRA Serving 综述 | https://lin-guanguo.github.io/llm-memory-research/multi-lora.research/ | 2026-03-24 | "LoRAX (Predibase): 128+ with ~20% latency… Tiered weight caching (GPU → CPU → disk)" | 中高 |
| [^43^] | TRT-LLM：编译期锁定 max-rank/target modules | prakashkagitha LLM Stack Book | https://prakashkagitha.github.io/llm-stack-book/07-inference-serving/14-multi-tenant-lora-serving.html | 2026-08-18 | "the LoRA plugin, the set of target modules, and the maximum rank must be declared at trtllm-build time" | 中高 |
| [^44^] | 联发科 Dimensity 9300+ NeuroPilot LoRA Fusion 2.0 | embedded.com | https://www.embedded.com/mediatek-new-flagship-dimensity-9300-targets-on-device-llms/ | 2024-05-10 | "Support for on-device LoRA Fusion and NeuroPilot LoRA Fusion 2.0" | 高 |
| [^45^] | EdgeLoRA：Jetson AGX Orin 1,000+ adapter、2–4× llama.cpp、自适应 adapter 路由器 | MobiSys 2025 / arXiv 2507.01438 | https://arxiv.org/html/2507.01438v1 | 2025-07-02 | "EdgeLoRA can serve over 1,000 adapters simultaneously on Jetson Orin AGX… llama.cpp is limited to serving only 50 adapters" | 高 |
| [^46^] | MobiLoRA：按 adapter 复用 KV cache、TTFT -81.3% | ACL 2025 | https://aclanthology.org/2025.acl-long.1140.pdf | 2025 | "MobiLoRA can load and reuse the KV cache of different LoRA adapters… reduces the TTFT by at most 81.3%" | 高 |
| [^47^] | QVAC Fabric LLM：手机 GPU 上 LoRA 训练（2025-12） | thepromptbuddy | https://www.thepromptbuddy.com/prompts/qvac-fabric-llm-… | 2025-10-25 | "the first production system enabling modern AI training on smartphone GPUs like Qualcomm Adreno and ARM Mali" | 中 |
| [^48^] | PCC 缺可复现构建（WiSec 2026 独立分析） | tobiasreithmeier（引 Dittmar et al.） | https://www.tobiasreithmeier.de/en/blog/apple-private-cloud-compute | 2026-07-07 | "Unlocking Apple's Private Cloud Compute, independent security analysis, including the lack of reproducible builds" | 中高 |
| [^49^] | 端侧 TTFT <100ms、PCC +200–500ms | kanopylabs | https://kanopylabs.com/blog/apple-intelligence-sdk-integration-for-apps | 2026（页面日期异常 2028） | "On-device inference starts generating tokens in under 100 milliseconds. PCC requests add… typically 200 to 500 milliseconds before the first token" | 中 |
| [^50^] | AFM 3 五模型表（Core/Core Advanced/Cloud/ADM Cloud/Cloud Pro）与 NAND 驻留+动态专家加载 | ai-on-mac | https://ai-on-mac.com/articles/apple-intelligence-local-llm-on-device-ai/ | 2026-10-13 | "the full expert set is stored in NAND flash… routed experts are loaded only when needed" | 中 |
| [^51^] | PCC 32K 上下文、entitlement、配额 | ai.singhsk.com | https://ai.singhsk.com/on-device-agentic-ai-for-mobile-apps-android-vs-ios-architecture-in-2026 | 2026-08-03 | "Apple documents a 32K-token context window for the Private Cloud Compute model… subject to availability and user quota constraints" | 中高 |
| [^52^] | WWDC26：PCC 与端侧 contextSize 均为运行时能力、PCC 有日配额 | theswift.dev | https://www.theswift.dev/posts/choose-between-on-device-foundation-models-and-private-cloud-compute | 2026-06-23 | "PCC is private, server-backed, requires an internet connection, has daily per-user limits" | 中高 |
| [^53^] | Gemini Nano v3 需 ≥12GB RAM、4K token 上限、仅前台 | byteiota | https://byteiota.com/android-17-gemini-nano-api-on-device-ai/ | 2026-05-19 | "4,000 tokens per request… needs 12 GB or more RAM and a qualified flagship chipset" | 中高 |
| [^54^] | SGLang 前缀缓存键含 adapter 标识 | pinghaoyang SGLang 源码拆解 | https://pinghaoyang.com.cn/aigc/posts/sglang-lora-serving/ | 2026-10-19 | "(lora0, tokens[0:100]) 与 (lora1, tokens[0:100]) 成为两个不同的缓存条目" | 高（源码级） |
| [^55^] | 商用多 LoRA 延迟口径汇总（Punica 2ms、LoRAX +20%@128、Together ~10%、Fireworks TTFT +10–30%） | lin-guanguo 综述 | https://lin-guanguo.github.io/llm-memory-research/multi-lora.research/ | 2026-03-24 | 平台对比表 | 中 |
| [^56^] | 芯片行业收敛：adapter 是基座与硬件之间的定制层（Taalas/Apple Core ML/Qualcomm） | ertas.ai | https://www.ertas.ai/blog/hardware-lora-support-ai-chips | 2026-02-22 | "treat LoRA adapters as the customization layer between base models and hardware" | 中（行业评论） |
| [^57^] | 无用户开关可强制全端侧；路由由 Apple 未公开阈值控制 | softwareseni | https://www.softwareseni.com/which-apple-ai-workloads-leave-the-device-and-what-they-cost/ | 2026-09-23 | "there is no user-facing switch that forces all Apple Intelligence work to stay on-device" | 中高 |
| [^58^] | 企业合规需路由决策审计日志层 | practicallogix | https://www.practicallogix.com/mobile-app-development-in-the-on-device-ai-era/ | 2026-07-02 | "the compliance audit layer that logs routing decisions for regulated industries" | 中（判断） |
| [^59^] | PCC 路由层 attestation 通道/边缘元数据存在流量分析侧信道 | iotdigitaltwinplm（引 arXiv attested confidential inference 研究线索） | https://iotdigitaltwinplm.com/apple-wwdc-2026-on-device-ai-production-analysis/ | 2026-05-28 | "the attestation channel itself constitutes a side channel for traffic-analysis attacks" | 中（判断/线索） |

---

## 附：调研方法与局限

- 独立搜索 32 次（PCC 架构与路由、Firebase hybrid、OpenShell/NemoClaw、GPU TEE、split computing/协作推理学术谱系、vLLM/SGLang/Punica/S-LoRA/dLoRA/EdgeLoRA/MobiLoRA、Apple AFM adapter 与训练工具包、Qualcomm/MTK/Taalas 芯片支持等方向）。
- security.apple.com 与 firebase.google.com 官方页面直连抓取被审计拒绝；相应论断以 ≥2 个独立二手来源交叉验证，官方原始链接已列入证据清单备查。
- 延迟类数据（PCC 200–500ms、TEE 5–15%）均来自第三方口径，已在表中标注置信度；官方未公布生产环境路由延迟分布。
- 2026 年 WWDC26/GTC 2026 相关内容以发布会报道+官方文档（NVIDIA/Firebase）交叉，AFM 3 细节置信度为中。

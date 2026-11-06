# AgentOS 维度 B 调研：KV cache 管理 + 权重分页与端侧推理

> 调研日期：2026-11-06。范围：KV cache 管理（块化/共享/压缩/驱逐/卸载）与权重分页/端侧推理，2024-01 至 2026-11 为主，奠基工作标注年份。
> 我方立场对照：模型内存域——DMA 路径上的 KV cache 驱逐经济学；权重分页与 LoRA 热插拔；KV 是纯缓存，四种驱逐去向（换出/重算/上云/摘要入库）有成本模型。

---

## 1. 技术谱系表素材：KV cache 管理五条路线

### 路线一：块化与分配（Block/Paging）

| 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|
| PagedAttention / vLLM [^1^][^2^] | UC Berkeley | SOSP 2023 | 借鉴 OS 虚拟内存分页，KV cache 切成固定块（默认 16 token）按需分配+块表映射+写时复制，内存碎片从 60–80% 降到 <4%，成为事实标准 |
| RadixAttention / SGLang [^3^] | LMSYS Org | 2023-12（arXiv 2312.07104） | 用 radix tree 管理 KV 的前缀共享，LRU 驱逐+引用计数+缓存感知调度，跨请求自动复用，常见任务最高 5× 加速 |
| vAttention [^4^] | Microsoft Research India | ASPLOS 2025（arXiv 2405.04437, 2024-05） | 用 CUDA 虚拟内存 API 保留 KV 在虚拟地址连续、物理按需分配，无需重写 attention kernel，decode 吞吐最高 1.97× 于 vLLM |
| ChunkAttention | Microsoft | 2024 | 前缀感知的 KV 布局重构 attention kernel（前缀共享路线的 kernel 层变体）[^5^] |

### 路线二：前缀共享与跨请求复用（Sharing）

| 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|
| RadixAttention [^3^] | LMSYS | 2023-12 | 见上：token 级最长前缀匹配，零拷贝 fork，祖先节点（system prompt）常驻 HBM |
| vLLM Prefix Caching（APC） | vLLM 社区 | 2024–2025 | 块级哈希前缀缓存；块哈希包含全部前缀 token，提示词开头的时间戳/用户 ID 会使后续所有块哈希失效[^6^] |
| Hydragen / Prompt Cache / Pensieve | Stanford / Yale 等 | 2023–2025 | 共享前缀 attention、prompt 模块化缓存、多轮对话跨请求缓存（Pensieve 为 EuroSys 2025）[^5^][^7^] |
| CacheBlend | 多机构 | 2024 | RAG 场景对非前缀复用选择性重算 5–18% token 融合缓存块[^8^] |

### 路线三：压缩（量化/低秩/编码）

| 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|
| KIVI [^9^] | Rice/CMU/UT Austin 等 | ICML 2024（arXiv 2402.02750） | 免微调 2-bit KV 量化：key 逐通道、value 逐 token + 全精度残差滑窗；Llama-2-7B 峰值内存降 2.6×，batch 可大 4×，吞吐 2.35–3.47× |
| KVQuant [^10^] | UC Berkeley | 2024（arXiv 2401.18079） | RoPE 前量化+非均匀+离群通道保护+混合精度，sub-4-bit 支撑 10M token 上下文推理 |
| ShadowKV [^11^] | 北大/CMU 等 | ICML 2025 Spotlight | pre-RoPE key 低秩 SVD（GPU 留 6× 压缩的 low-rank key + landmark + 0.3% outlier），value 卸载 CPU，稀疏预算仅 1.56%，A100 上 batch 6×、吞吐 3.04× |
| Palu / ThinK / CQ / QuaRot 等 | 多机构 | 2024–2025 | 低秩分解、逐头通道剪枝、channel 量化、旋转不变量化等（压缩路线已成顶会常规赛道）[^7^] |
| CacheGen [^12^] | U Chicago 等 | SIGCOMM 2024（arXiv 2310.07240） | 面向网络传输的 KV 编码（delta+算术编码，3.5–4.3× 更小码流），随带宽自适应调压缩级别，带宽不足时回退传文本重算；已并入 LMCache |
| FP8 KV（工程落地） | vLLM/SGLang | 2024–2026 | `--kv-cache-dtype fp8_e4m3` 已成生产默认选项之一[^13^] |

### 路线四：选择性驱逐（Eviction/Sparsity）

| 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|
| StreamingLLM [^14^] | MIT/Meta | ICLR 2024（arXiv 2023） | 发现 attention sink：固定保留前 4 个 sink token+滚动窗口即可 O(1) 内存无限流式生成 |
| H2O [^15^] | UT Austin/Stanford/Meta | NeurIPS 2023 | 累计注意力分 heavy-hitter 驱逐，20% 预算下 PPL 仅差 1.8%；吞吐最高 29×；驱逐不可逆是核心风险 |
| SnapKV [^16^] | UIUC/Cohere/Princeton | NeurIPS 2024 | prefill 末尾观察窗一次性投票压缩 prompt KV：16K 输入 3.6× 加速、8.2× 省内存，单 A100-80GB 跑 380K 上下文 |
| Scissorhands / FastGen | CMU / Adobe 等 | 2023 | 重要性持久性假设 / 逐头自适应压缩策略[^15^] |
| Quest [^17^] | MIT（Han Lab） | ICML 2024 | query 感知的页级 top-K 选择（页内 key 逐通道 min/max 元数据），self-attention 7.03×、端到端 2.23×，不丢 token 只少读 |
| SnapKV-D | 2025-12 | 滑动观察窗扩展到 decode 阶段周期性重评分驱逐，长推理链任务显著优于 H2O[^18^] |
| ReasonAlloc / TriAttention 等 | 2026 | 面向 reasoning 模型的分层 KV 预算分配 / 三角函数式 KV 压缩（驱逐路线向"长 CoT"场景迁移）[^19^][^20^] |

### 路线五：卸载与分层存储（Offload/Tiering）

| 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|
| FlexGen [^21^] | Stanford/Berkeley 等 | ICML 2023（奠基） | 线性规划搜索 GPU/CPU/磁盘三层 offloading 策略+zigzag 块调度+4-bit 压缩，OPT-175B 在单 16GB T4 上达 1 tok/s，比 ZeRO-Inference 高 40–112× |
| ZeRO-Inference [^22^] | Microsoft DeepSpeed | 2022（奠基） | 权重钉在 CPU/NVMe 逐层流入 GPU，全卸载优于部分卸载（显存留给大 batch）；530B 模型 GPU 显存需求 1TB→10GB |
| InfiniGen [^23^] | KAIST/Samsung | 2024（arXiv 2406.19707） | KV 池放 CPU，用第 i−1 层输入+SVD 倾斜权重预演第 i 层注意力，只预取关键 KV 项；比 H2O/INT4 基线快 1.63–32.93×，距理想仅 1.52× |
| RetrievalAttention [^24^] | MSRA/SJTU | NeurIPS 2024 | KV 放 CPU 向量数据库，ANNS 检索相关 token 在 CPU 侧算部分注意力再合并，单 A100 跑 1M 上下文、仅扫描 1–3% 向量 |
| LMCache [^25^] | U Chicago 等 | 2025-10（arXiv 2510.09665） | 引擎外置 KV 缓存层：CPU DRAM/NVMe/Redis/S3 分层+256-token 块级前缀哈希索引+跨实例共享；单机 TTFT 降 3.7–6.8×、同 TTFT 下吞吐 2.3–14×（最高 15×） |
| SGLang HiCache [^26^][^27^] | LMSYS/SGLang 社区 | 2025 | RadixAttention 扩展为 L1 GPU/L2 host/L3 分布式存储（Mooncake/3FS/NIXL/AIBrix），写策略/预取策略可配，与 PD 分离原生集成；缓存命中比重算省 84% TTFT |
| Mooncake [^28^][^29^] | Moonshot AI/清华 | FAST 2025 最佳论文 | KVCache 为中心的 PD 分离集群架构，聚合全集群空闲 CPU/DRAM/SSD 做全局 KV 池+RDMA Transfer Engine；仿真吞吐 +525%，生产让 Kimi 多扛 75% 请求 |
| NVIDIA Dynamo KVBM [^30^][^31^] | NVIDIA | 2025–2026 | 生产级四级 KV 层级 G1 HBM/G2 DRAM/G3 NVMe/G4 对象存储，频率制驱逐（命中翻倍、时间衰减）+SSD 寿命过滤（freq≥2 才落盘），NIXL 跨节点传输 |
| vLLM OffloadingConnector / 原生 swap | vLLM | 2025–2026 | V0 有 GPU↔CPU 块交换；V1 移除 swap、抢占默认 RECOMPUTE；0.11+ 提供标准化 OffloadingConnector 卸载前缀块[^32^][^6^] |

### 附：权重分页与端侧推理谱系

| 代表工作 | 机构 | 时间 | 一句话贡献 |
|---|---|---|---|
| LLM in a flash [^33^] | Apple | ACL 2024（arXiv 2312.11514, 2023-12） | 权重驻留闪存、按 token 需求加载：windowing（复用前几个 token 的稀疏模式）+row-column bundling（大块连续读）+FFN 稀疏预测，每 token 仅加载约 2% FFN 权重，跑 2× DRAM 容量的模型，比朴素加载快 4–5×（CPU）/20–25×（GPU） |
| PowerInfer [^34^] | 上海交大 IPADS | SOSP 2024 | 激活幂律（26% 神经元贡献 80% 激活且跨任务稳定）：热神经元驻 GPU、冷神经元 CPU 直算，消费级 GPU 高速推理 |
| PowerInfer-2 [^35^] | 上海交大 IPADS | 2024-06 | 神经元簇为基本处理单元+NPU 密计算/CPU 稀疏计算+分段神经元缓存+细粒度 I/O 流水线；首个在手机上跑 47B（TurboSparse-Mixtral）达 11.68 tok/s，比 SOTA 快至 29.2× |
| ActiveFlow（Active-Weight Swapping）[^36^] | Apple | 2025（arXiv 2504.08378） | 跨层 active weight 预加载+稀疏感知自蒸馏+DRAM↔flash 交换流水线，打破端侧 DRAM 容量墙 |
| Apple AFM 2025 [^37^][^38^] | Apple | 2025-07（arXiv 2507.13575） | 端侧 3B 模型：双块架构 block2 共享 block1 的 KV cache（KV 内存 −37.5%、改善 TTFT）+2-bit QAT 权重——端侧 KV 管理走"架构层共享+量化"而非驱逐 |
| MoE-Infinity [^39^] | U Edinburgh | ASPLOS 2025 | 请求级专家激活追踪（EAM/EAMC）做专家预取+缓存，比各 offloading 基线低 2–20× 延迟，等效延迟下省 4× GPU |
| S-LoRA [^40^] | Stanford/Berkeley | 2023-11（arXiv 2311.03285） | Unified Paging：统一内存池同时分页管理不同 rank 的 LoRA 适配器权重与变长 KV cache，单 GPU 服务数千适配器，吞吐 4× |
| Punica [^41^] | UW/Duke | MLSys 2024 | SGMV kernel 批处理不同 LoRA 请求；适配器按需加载仅毫秒级延迟；同集群吞吐 12×，每 token 仅 +2ms |
| vLLM 多 LoRA 热插拔（工程）[^42^][^43^] | vLLM 社区 | 2024–2026 | GPU 适配器槽位 LRU 驱逐→CPU→S3；`load_inplace` 原地热更新（PR #31326, 2026-01 合入）服务 RL 权重同步；第三方测得热插拔 <100ms |
| vLLM Sleep Mode [^44^][^45^] | vLLM 社区 | 2025 | L1 睡眠：权重卸到 CPU、丢弃 KV（唤醒 ~2–3s）；L2：权重也丢弃、唤醒从磁盘重载（~7–8s）；支持 `wake_up(tags=["weights"/"kv_cache"])` 细粒度唤醒防 RL 权重更新 OOM；实测 6.1GB→0.6GB、唤醒 0.39s（小模型） |
| Dynamo ModelExpress [^46^] | NVIDIA | 2026 | 权重经 NIXL/NVLink GPU-to-GPU 流式加载，DeepSeek-V3 冷启动快 7×；Mooncake checkpoint-engine 在数千 GPU 上 ~20s 更新 1T 参数 Kimi-K2，RDMA P2P 权重更新 53s→7.2s[^29^] |

---

## 2. 关键数据（带出处日期）

**KV 规模与压力**
- Llama-3-8B FP16 KV cache：128K→15.6GB，512K→31.2GB，1M→62.5GB（RetrievalAttention 论文表 1）[^24^]
- 70B 模型 1M token FP16 KV ≈ 164GB/请求，超过权重本身（140GB）[^15^]
- Kimi 生产流量：平均 prompt 7,590 token / 平均回复 182 token（42:1），prefill 占大头[^28^]

**块化/共享**
- PagedAttention 将 KV 内存浪费从 60–80% 降到 <4%[^8^]
- SGLang RadixAttention：GSM-8K 上比 vLLM 高 4.5× 吞吐；ReAct agent 5.6× 吞吐、13% 延迟[^3^]
- HiCache+Mooncake 多轮对话 benchmark：缓存命中比重算省 84% TTFT（DeepSeek-R1-671B，PD 分离）[^27^]
- LMCache：单机 CPU offload 下 TTFT 降 1.9–8.1×（低 QPS）/3.7–6.8×（真实 trace 五模型），同 TTFT 吞吐 2.3–14×[^25^]
- Dynamo（NVIDIA 1.0，2026-03-16 官方博客）：embedding cache 使图像请求 TTFT −30%、吞吐 +25%（Qwen3-VL-30B, GB200）[^46^]

**压缩**
- KIVI 2-bit：峰值内存 −2.6×（含权重），batch ≤4×，吞吐 2.35–3.47×[^9^]
- SnapKV：16K 输入 3.6× 生成加速、8.2× 内存效率；A100-80GB 跑 380K[^16^]
- ShadowKV：batch ≤6×、吞吐 ≤3.04×（A100），等效带宽 >7TB/s[^11^]
- KVQuant：7B 模型 10M token KV 从 4,883GB（fp16）压到 610GB[^10^]
- CacheGen：KV 编码为 3.5–4.3× 更小码流；**GPU 解压与推理并存时双向干扰——算术解码无法同时把两者减速压到 30% 以下**（arXiv 2509.16857 实测，推动解压卸载到 BlueField-3 DPU）[^47^]

**驱逐的失败模式（关键反例）**
- NVIDIA 官方博客（2026-06）：2,048-token 预算下 AIME 2024 全注意力 57.1%，SnapKV 仅 34.6%、R-KV 25.4%——**数学推理场景永久驱逐精度崩塌**[^20^]
- H2O 在 needle-in-haystack 类精确召回任务 20% 预算下降 30–40%；驱逐不可逆[^15^]
- 2026 年 offloading 复测（arXiv 2604.08426）：ShadowKV 的 rank-160 SVD 在 context-intensive 任务上失效，需加载 5–10% token（而非默认 1.56%）才能逼近全注意力[^48^]

**卸载/换出成本**
- vLLM V1：抢占默认 RECOMPUTE，GPU↔CPU swap 已从 V1 移除——"V1 结构下重算开销小于换出"（官方文档口径）[^32^][^49^]
- Stream2LLM（arXiv 2604.16395, 2026）：**对重算与换出建立分段线性硬件成本模型**，recompute.latency(T) 随 prefill token 数拟合、swap.latency(C) 随块数与 PCIe 带宽拟合；同一重算 H100 上 50ms、A40 上 200ms；GB300/GH200 NVLink 主机带宽 450GB/s 使 swap 成本大降[^50^]
- FastSwitch（2024-11）：KV 复用机制使 swap-out 量 −53%，动态块组管理 I/O 利用率 1.3×，尾延迟 1.4–11.2× 优于 vLLM[^51^]
- PCIe Gen5 x4 NVMe 上限 ~16GB/s：1GiB 会话 KV 重载 ≥67ms[^52^]
- Mooncake 跨节点受 RDMA 带宽约束（约 15GB/s/NIC）[^8^]
- FlexGen 实测：朴素层级 offloading 99.5% 时间耗在权重搬运（PowerInfer 论文引述）[^34^]

**端侧/权重分页**
- LLM in a flash：M1 Max 上 1GiB 未缓存文件顺序读 >6GiB/s，但小随机读达不到——成本模型必须对齐闪存特性[^33^]
- PowerInfer-2：47B 手机推理 11.68 tok/s；对内存内模型也可省 ~40% 内存且速度持平 llama.cpp/MLC-LLM[^35^]
- ZeRO-Inference：全卸载+大 batch 优于部分卸载（OPT-30B，43 tok/s CPU offload）[^22^]
- vLLM Sleep Mode 实测：睡眠 API 42ms、GPU 占用 6,168MiB→606MiB、唤醒 0.39s、唤醒后输出与睡眠前逐位一致[^45^]

---

## 3. 趋势判断

**收敛方向**

1. **KV cache 正在从"单请求易失状态"变成"跨请求、跨实例、分层持久化的一等资源"。** LMCache 自称把 KV 变成"AI-native knowledge"；Mooncake/HiCache/KVBM 都把 GPU-HBM→DRAM→NVMe→分布式存储的 L1–L4 层级做成标准架构[^25^][^26^][^30^]。这与我方"模型内存域"的定位完全一致，且 2025–2026 已从论文走向生产（Kimi K2 128×H200 部署、NVIDIA 官方框架）[^28^][^46^]。
2. **驱逐经济学已经出现"成本模型化"的萌芽，但只覆盖两个去向。** Stream2LLM 对"重算 vs 换出"建分段线性成本函数并按硬件拟合[^50^]；vLLM 用工程结论（V1 默认 RECOMPUTE）隐式做了同样的判断[^32^]。四条去向的统一成本模型是空白。
3. **压缩路线内部在分层：运行时表示（量化/低秩，面向显存）与传输表示（算术编码，面向网络）分野清晰**[^47^]。FP8 KV 已成生产默认；2-bit 研究可用但未成默认。
4. **永久驱逐（H2O/SnapKV 谱系）在 reasoning 时代遭遇系统性挑战**：长 CoT 使预算更紧、精确召回更敏感；NVIDIA 实测 AIME 上 SnapKV 崩塌[^20^]。研究界回应是"驱逐改卸载+选择性取回"（ShadowKV/Quest/RetrievalAttention/InfiniGen）——即"不丢、只搬、按 query 取"取代"按重要性永久丢"。
5. **权重分页收敛于三个工程事实**：(a) 闪存直读可行但必须硬件感知成本模型（Apple: 顺序大块读 >6GiB/s，随机小读崩）[^33^]；(b) 稀疏激活是端侧省内存的主杠杆（PowerInfer 系、Apple FFN 稀疏预测、TurboSparse 产品化）[^34^][^35^]；(c) 权重/适配器的热更新已被 RL 训练闭环倒逼成一等工程能力（sleep mode 分级唤醒、load_inplace、checkpoint-engine 20s/1T）[^44^][^42^][^29^]。
6. **端侧 KV 管理走"架构内共享+量化"而非"驱逐"**：Apple AFM 双块 KV 共享（−37.5%）+2-bit QAT[^37^][^38^]。端侧 KV 驱逐/卸载的系统研究近乎空白。

**空白点**

- 四种驱逐去向的统一经济学模型（带宽/算力/时延/质量损失四维）不存在；现有只有"重算 vs 换出"两路[^50^]。
- 端侧（DRAM/NPU/闪存层级）KV 分层管理几乎无人做系统研究；HiCache/Mooncake 全是数据中心语境。
- "摘要入库"作为 KV 驱逐去向没有任何系统层成本模型——现有相关工作（MemGPT 递归摘要）在文本层且失败是静默的[^53^]。
- 混合架构（Mamba/GDN/线性注意力）的 recurrent state 与 KV 统一分页刚起步（SGLang UnifiedRadixCache 支持 Mamba cache 分层是首个工程实例）[^54^]。
- KV 传输解压与推理的 GPU 资源干扰被实测证实但无标准解法（DPU 卸载是 2025 新方向）[^47^]。

---

## 4. 对我方"四种驱逐去向"成本模型的逐条评审

### 4.1 换出（swap 到 CPU/磁盘）——**支持，但需修订粒度假设**

- **支持证据**：分层换出已是 2025–2026 生产标配（HiCache L2/L3、LMCache、KVBM G2–G4、Mooncake），成本结构清晰：PCIe 25–32GB/s 级、NVMe ≤16GB/s、RDMA ~15GB/s/NIC，均可建模为"字节数/带宽 + 固定分发开销"[^26^][^25^][^30^][^52^]。
- **需要修订**：(a) vLLM V1 直接移除 swap、默认 RECOMPUTE，说明**在现代 GPU 上"每请求私有 KV"的换出常常不划算**——换出的价值高度依赖"复用概率"：共享前缀（多轮、system prompt、RAG 文档）换出回报高（LMCache 2.3–14× 吞吐），私有生成中间态换出后几乎不再被读[^32^][^25^]；(b) 硬件强相关：NVLink C2C（450GB/s）机器上 swap 成本下降一个量级，成本函数必须按平台拟合而非固定常数[^50^]；(c) FastSwitch 证明 swap 的工程开销主要在 API 分发与块粒度，优化后 swap-out 量可 −53%[^51^]。
- **结论**：成本模型成立，但应把"复用概率/共享度"作为一等变量，且成本常数需按硬件 profile 在线校准。

### 4.2 重算（recompute）——**支持，但成本模型要含机会成本与攻击面**

- **支持证据**：重算已被 vLLM V1 定为默认抢占策略，理由是 chunked prefill 使重算摊薄后常低于 PCIe 往返[^32^][^49^]；CacheBlend 把重算降到 5–18% token 即可融合非前缀缓存[^8^]；CacheGen 在低带宽时主动回退"传文本让 LLM 重算"——工业界已把重算当作可定价选项[^12^]。
- **需要修订**：(a) 重算成本随被驱逐前缀长度线性（注意力近二次）增长，长上下文下并不便宜——Stream2LLM 的实测（同一重算 H100 50ms / A40 200ms）说明算力差异主导[^50^]；(b) 重算消耗的是 prefill 算力预算，高负载下会形成"重算颠簸"（已被 Latency-DoS 攻击利用，攻击者反复顶爆 KV 池迫使受害者重算）[^49^]；(c) 对 Mamba/GDN 类 recurrent state，重算意味着从头 fold 全序列，成本结构与 KV 完全不同，模型需分架构。
- **结论**：作为默认去向成立，但成本函数 = prefill 时延（按硬件拟合）× 概率加权 + 拥塞外部性，不是常数。

### 4.3 上云（传输到远端/云端）——**支持，需加入压缩-解压干扰项与带宽分级**

- **支持证据**：CacheGen 证明 KV 可作为码流在网络上传输（3.5–4.3× 压缩、随带宽自适应、可回退重算）[^12^]；Mooncake/NIXL 证明集群内 RDMA 传 KV 是生产现实[^28^]；vLLM/SGLang 的 PD 分离本质就是"KV 跨节点搬家"[^27^]。
- **需要修订**：(a) **解压与推理在 GPU 上互相干扰 >25–30%**，2025 年的对策是把解压卸载到 DPU/SmartNIC——成本模型必须包含"解压占用的 GPU 计算份额"或 DPU 卸载项[^47^]；(b) 跨 WAN 上云与跨 RDMA 集群是两种经济：前者带宽低两个量级，只有在"重算极贵（超长前缀）+带宽尚可+隐私允许"三条件同时成立时才划算，CacheGen 自己也承认高端 GPU+低带宽时不如直接传文本[^12^]；(c) 端侧上云还叠加隐私与合规成本，非纯字节成本。
- **结论**：去向成立，但成本模型需要三段式：编码/压缩算力 + 传输带宽分级（RDMA/局域网/WAN）+ 解码干扰项。

### 4.4 摘要入库（压缩为语义摘要写入记忆库）——**挑战：这不是缓存驱逐，系统层证据链缺失**

- **事实**：在 KV/系统文献中，**没有任何 2024–2026 工作把"摘要入库"当作 KV 驱逐的标准去向并给出成本模型**。最接近的只有：(a) MemGPT 在文本层做递归摘要+向量库检索，其成本是一次额外 LLM 推理 + 检索召回误差，且 paging 决策错误是**静默失败**（无异常、无日志，长期累积）[^53^]；(b) 永久驱逐系（H2O/SnapKV）证明"不可逆丢弃"在精确召回与数学推理上系统性崩塌（AIME 57.1%→34.6%；needle 任务 −30~40%）[^20^][^15^]；(c) 2026 年 offloading 复测显示即使保留全部 KV、只用低秩 key 做选择，在 context-intensive 任务上也会失效[^48^]。
- **判断（推断，非文献事实）**：摘要入库把"KV 是纯缓存"这一前提击穿——摘要是**有损、不可重建、语义级**的派生数据，不再是"可重新计算的中间态"。它的成本模型与其他三个去向不同构：其他三个保真（可无损恢复），摘要的"成本"主要是质量损失函数 + 一次写入推理 + 后续检索召回率，属于**数据治理/记忆层**而非内存层。
- **结论**：**建议修订为"3+1"结构**——换出/重算/上云是纯缓存驱逐（统一带宽-算力-时延成本模型），摘要入库单列为"物化（materialization）去向"，挂在记忆子系统，质量成本单独建模；若坚持四分法同层并列，至少需要定义摘要的保真度下界与适用场景白名单（闲聊/长程偏好可摘要；精确召回、合规、安全指令禁止）。

### 4.5 对"KV 是纯缓存"前提的补充挑战

RadixAttention/LMCache/Mooncake 证明 KV 具有**跨请求资产属性**（可寻址、可复用、可跨实例共享），这支持"纯缓存"定位（缓存本来就可以共享）；但 H2O 系的教训说明"驱逐"决策会进入质量域，因此我方"驱逐经济学"建模时应显式区分：**保真驱逐（swap/recompute/cloud，可恢复）与有损驱逐（evict/summarize，不可恢复）是两个范畴**——这一点现有文献没有统一表述，是我方可以抢占的概念框架空位。

---

## 5. 证据清单

| # | Claim | Source | URL | Date | Excerpt（关键原文） | Confidence |
|---|---|---|---|---|---|---|
| 1 | PagedAttention 用 OS 分页管理 KV，块默认 16 token，碎片 60–80%→<4% | vLLM 论文（SOSP 2023）及二手综述 | https://tensormesh.ai/learn/pagedattention/ ; https://arxiv.org/pdf/2607.27187 | 2023 / 2026-10 | "PagedAttention…fixed-size pages handed out on demand…The paper sets the default at 16 tokens" / "reducing fragmentation from 60-80% to under 4%" | 高 |
| 2 | RadixAttention radix tree+LRU+引用计数，最高 5×，GSM-8K 4.5× | SGLang 论文 arXiv 2312.07104 | https://arxiv.org/pdf/2312.07104 | 2023-12 | "we implement an LRU eviction policy that recursively evicts leaf nodes…SGLang achieves a 4.5x increase in throughput" | 高 |
| 3 | vAttention 用 CUDA VMM 保持 KV 虚拟连续，decode 最高 1.97× 于 vLLM | arXiv 2405.04437 | https://arxiv.org/abs/2405.04437 | 2024-05（v1） | "vAttention stores KV-cache in contiguous virtual memory and leverages OS support for on-demand allocation…generates tokens up to 1.97x faster than vLLM" | 高 |
| 4 | HiCache：GPU L1/主机 L2/分布式 L3，接 Mooncake/3FS/NIXL/AIBrix | SGLang 官方文档 | https://docs.sglang.ai/advanced_features/hicache_design.html | 2026-11-05（访问） | "HiCache organizes GPU memory as L1, host memory as L2, and distributed storage as L3" | 高 |
| 5 | HiCache+Mooncake 缓存命中省 84% TTFT（R1-671B PD 分离） | Mooncake benchmark | https://kvcache-ai.github.io/Mooncake/performance/sglang-hicache-benchmark-results-v1.html | 2025 | "On average, cache hits achieved an 84% reduction in TTFT compared to full re-computation" | 高 |
| 6 | LMCache：TTFT 降 3.7–6.8×（五模型真实 trace），同 TTFT 吞吐 2.3–14× | arXiv 2510.09665（alphaxiv 摘要+第三方转述） | https://www.alphaxiv.org/abs/2510.09665 ; https://optinest.de/ai-infrastructure/inference/serving-topologies/kv-cache-offloading-when-it-helps-and-when | 2025-10 / 2026-09 | "3.7-6.8× reduction in TTFT" / "2.3x to 14x higher throughput at the same TTFT" | 高 |
| 7 | Mooncake：KVCache 中心 PD 分离，仿真吞吐 +525%，Kimi 多扛 75% 请求，FAST'25 最佳论文 | Mooncake 官方站/GitHub | https://kvcache-ai.github.io/Mooncake/ ; https://intuitivepapers.ai/mooncake/ | 2024-07（arXiv）/ 2026-08 | "achieving up to a 525% throughput increase in simulated scenarios…enables Kimi to handle 75% more requests" | 高（75% 为厂商自报） |
| 8 | KIVI 2-bit：峰值内存 −2.6×、batch ≤4×、吞吐 2.35–3.47× | arXiv 2402.02750（ICML 2024） | https://arxiv.org/html/2402.02750 | 2024-02 | "2.6× peak memory usage reduction…up to 4× larger batch size and brings 2.35×∼3.47× throughput" | 高 |
| 9 | KVQuant：RoPE 前量化+非均匀+离群保护，支持 10M token 上下文 | arXiv 2401.18079 | https://arxiv.org/html/2401.18079v4 | 2024-01 | "Towards 10 Million Context Length LLM Inference with KV Cache Quantization"（7B/10M：4,883→610GB） | 高 |
| 10 | StreamingLLM：sink token+滚动窗口，O(1) 内存无限生成 | Xiao et al. 2023（ICLR 2024），二手精读 | https://www.llms.blog/posts/streamingllm-and-attention-sinks-mathematical-foundations-of-softmax-normalization-artifacts-initial-token-anchoring-and-infinite-context-rolling-kv-cache-mechanics | 2023-09 / 2026-10 | "permanently pinning the first 4 Attention Sink Tokens…generate text infinitely…with a bounded O(1) VRAM memory footprint" | 高 |
| 11 | H2O：20% 预算 PPL 差 1.8%；驱逐不可逆；needle 任务 −30~40% | NeurIPS 2023 论文+生产精读 | https://proceedings.neurips.cc/paper_files/paper/2023/file/6ceefa7b15572587b78ecfcebb2827f8-Paper-Conference.pdf ; https://ashwanijha.dev/blog/h2o-heavy-hitter-oracle-kv-cache-eviction-what-the-paper-actually-says | 2023 / 2026-06 | "Eviction is irreversible at inference time" / perplexity 11.5 vs 11.3 full at 20% budget | 高（论文）/中（博客实测数字） |
| 12 | SnapKV：观察窗一次性压缩，3.6× 加速/8.2× 省内存/380K 上下文 | arXiv 2404.14469（NeurIPS 2024） | https://arxiv.org/pdf/2404.14469v2 | 2024-04 | "3.6x increase in generation speed and an 8.2x enhancement in memory efficiency…up to 380K context tokens on a single A100-80GB" | 高 |
| 13 | SnapKV 等在数学推理预算压缩下崩塌（AIME24: 57.1→34.6%） | NVIDIA 官方研究博客 | https://research.nvidia.com/labs/eai/blogs/kv-cache-compression-and-its-infra-problems/ | 2026-06-12 | "Full Attention 57.1% | SnapKV 34.6% | R-KV 25.4% (AIME 2024, 2048-token budget)" | 高 |
| 14 | Quest：页级 min/max key 元数据+top-K 页，self-attention 7.03×/端到端 2.23× | arXiv 2406.10774（ICML 2024） | https://arxiv.org/html/2406.10774v1 | 2024-06 | "up to 7.03× self-attention speedup…reduces inference latency by 2.23×…negligible accuracy loss" | 高 |
| 15 | InfiniGen：KV 池在 CPU，层间预演+SVD 倾斜预取，1.63–32.93× | arXiv 2406.19707 | https://arxiv.org/html/2406.19707v1 | 2024-06 | "achieves up to a 3.00x speedup over the existing KV cache management methods…only 1.52× slower than Ideal" | 高 |
| 16 | ShadowKV：GPU 存低秩 key+landmark，value 卸载 CPU，batch 6×/吞吐 3.04× | ICML 2025 论文（PMLR） | https://proceedings.mlr.press/v267/sun25b.html | 2025-10（会议） | "stores the low-rank key cache and offloads the value cache…up to 6× larger batch sizes and 3.04× higher throughput on an A100" | 高 |
| 17 | RetrievalAttention：CPU 向量库 ANNS，1M 上下文单 A100，扫 1–3% 向量 | arXiv 2409.10516 | https://arxiv.org/html/2409.10516v3 | 2024-09 | "RetrievalAttention only requires scan 1–3% vectors"；表 1：1M 上下文 KV 62.5GB | 高 |
| 18 | CacheGen：KV 编码成 3.5–4.3× 小码流、随带宽自适应、低带宽回退传文本重算 | arXiv 2310.07240（SIGCOMM 2024） | https://arxiv.org/html/2310.07240v4 | 2023-10 | "compress KV cache into compact bitstreams…adapts the per-chunk compression level…fall back to sending a chunk in text format and leave it to the LLM to recompute" | 高 |
| 19 | KV 解压与推理在 GPU 上双向干扰 >25–30%，推动 DPU 卸载 | arXiv 2509.16857 | https://www.arxiv.org/pdf/2509.16857 | 2025-09 | "For arithmetic decoding, it is not possible to limit both tasks' slowdown below 30% at the same time" | 高 |
| 20 | vLLM V1：抢占默认 RECOMPUTE，swap 已移除 | vLLM 文档二手+源码解读 | https://www.spheron.network/blog/vllm-gpu-memory-utilization-guide-fix-low-throughput-and-oom/ ; https://labhub.hopto.org/blog/ai-platform/2026-08-12-vllm-scheduler-and-preemption?lang=en | 2026-09 / 2026-08 | "vLLM V1 defaults to RECOMPUTE, not SWAP, since recompute costs less than swap in the V1 scheduler" | 中高（二手，与官方文档一致口径） |
| 21 | Stream2LLM：对重算 vs 换出建分段线性硬件成本模型 | arXiv 2604.16395 | https://arxiv.org/pdf/2604.16395 | 2026-04 | "recomputation.latency(T) predicts the time to recompute T tokens…swap.latency(C)…GB300 and GH200 has up to 450 GB/s host-device bandwidth" | 高 |
| 22 | FastSwitch：KV 复用 −53% swap-out，尾延迟 1.4–11.2× | arXiv 2411.18424 | https://arxiv.org/pdf/2411.18424 | 2024-11 | "KV cache reuse mechanism reduced swap-out blocks by 53%…speedups of 1.4-11.2× across different tail TTFT and TBT" | 高 |
| 23 | FlexGen：LP 搜索三层 offloading，OPT-175B/16GB 单卡 1 tok/s，40–112× | arXiv 2303.06865（ICML 2023） | https://arxiv.org/abs/2303.06865 | 2023-03 | "reaching a generation throughput of 1 token/s for the first time with an effective batch size of 144" | 高 |
| 24 | ZeRO-Inference：权重钉 CPU/NVMe 逐层流入；530B 显存 1TB→10GB；全卸载>部分卸载 | DeepSpeed 官方博客 | https://github.com/microsoft/DeepSpeed/blob/master/docs/_posts/2022-09-10-zero-inference.md | 2022-09 | "pins the entire model weights in CPU or NVMe and streams the weights layer-by-layer into the GPU…drops from 1TB to 10GB" | 高 |
| 25 | LLM in a flash：闪存驻留权重，每 token 仅载 ~2% FFN，2× DRAM 模型，4–5×/20–25× | arXiv 2312.11514（ACL 2024） | https://arxiv.org/abs/2312.11514 ; https://arxiv.org/html/2312.11514v2 | 2023-12 | "run LLMs up to twice the size of available DRAM…4-5x compared to traditional loading methods in CPU, and 20-25x in GPU…load only ~2% of the FFN layer" | 高 |
| 26 | PowerInfer：激活幂律 26% 神经元贡献 80% 激活，热 GPU/冷 CPU | SOSP 2024 论文解读 | https://blog.csdn.net/Discover304/article/details/163771633 | 2024-10（会议）/2026-08 | "OPT-30B 单个 MLP 块中 26% 的神经元贡献了 80% 的激活；top-20% 热点重叠超过 90%" | 中高（中文二手，数值与论文一致） |
| 27 | PowerInfer-2：神经元簇+NPU/CPU 分工，47B 手机 11.68 tok/s，29.2× | arXiv 2406.06282 | https://arxiv.org/abs/2406.06282 | 2024-06-10 | "the first system to serve a 47B LLM on a smartphone, achieving 11.68 tokens/s…up to a 27.8x speed increase"（v1 摘要为 29.2×） | 高 |
| 28 | ActiveFlow：DRAM↔flash active weight swapping，跨层预加载+自蒸馏 | arXiv 2504.08378 | https://arxiv.org/html/2504.08378v2 | 2025-04 | "the first LLM inference system on mobile devices that supports adaptive DRAM usage…active weight swapping between DRAM and flash" | 高 |
| 29 | Apple AFM 2025：端侧 3B 双块 KV 共享（−37.5% KV 内存）+2-bit QAT | arXiv 2507.13575 + Apple ML Research | https://arxiv.org/abs/2507.13575 ; https://machinelearning.apple.com/research/apple-foundation-models-2025-updates | 2025-07 | "KV-cache sharing and 2-bit quantization-aware training" / "reducing KV-cache memory usage by 37.5% and significantly improving time-to-first-token"（后者经第三方转述） | 高/中 |
| 30 | MoE-Infinity：请求级专家激活追踪预取，2–20× 延迟改善，省 4× GPU | arXiv 2401.14361（ASPLOS 2025） | https://arxiv.org/html/2401.14361v2 | 2024-01 | "low latency comparable to expensive full-GPU deployment, which require up to 4X more GPU resources…2-20X improvements" | 高 |
| 31 | S-LoRA：Unified Paging 统一管理 LoRA 权重与 KV，单 GPU 数千适配器 | arXiv 2311.03285 | https://arxiv.org/abs/2311.03285 | 2023-11 | "Unified Paging uses a unified memory pool to manage dynamic adapter weights with different ranks and KV cache tensors…serve thousands of LoRA adapters…improve the throughput by up to 4 times" | 高 |
| 32 | Punica：SGMV 批处理多 LoRA，12× 吞吐，适配器加载毫秒级 | MLSys 2024 论文 | https://proceedings.mlsys.org/paper_files/paper/2024/file/054de805fcceb78a201f5e9d53c85908-Paper-Conference.pdf | 2024-05 | "on-demand loading of LoRA models has only millisecond-level latency…12x higher throughput…only adding 2ms latency per token" | 高 |
| 33 | vLLM 多 LoRA：GPU 槽位 LRU→CPU→S3；load_inplace 原地热更新（RL 闭环） | vLLM 论坛/GitHub issue+第三方 | https://discuss.vllm.ai/t/…/1482 ; https://github.com/torad-labs/qgre-engine/issues/3 ; https://arxiv.org/html/2607.03441v1 | 2025-08 / 2026-07 | "hot-swap the resulting adapter into the serving engine in under 100 ms"（aTTT 论文）；"PR: allow inplace loading lora vllm#31326" | 中高 |
| 34 | vLLM Sleep Mode：L1 卸权重丢 KV（~2–3s 唤醒）；L2 全丢（~7–8s）；细粒度 tags 唤醒 | vLLM 官方文档 | https://docs.vllm.ai/en/latest/features/sleep_mode/ | 2025-10（访问 2026-11） | "level=1: offload weights to CPU RAM, discard KV cache…level=2: discard both weights and KV cache…wake_up(tags=['weights'])" | 高 |
| 35 | Sleep Mode 实测：GPU 6,168→606MiB，唤醒 0.39s，输出逐位一致 | 第三方实测博客 | https://ttlab.hopto.org/blog/vllm-features-08-sleep-mode-and-operations?lang=en | 2026-10-27 | "GPU Memory During Sleep 6,168MiB → 606MiB; Wake Up 0.39s median; Output Matches Pre-Sleep Output Identical" | 中（单点小模型实测） |
| 36 | Dynamo KVBM：G1–G4 四级，频率制驱逐+SSD 寿命过滤（freq≥2 才落盘），NIXL | NVIDIA 文档+IBM Redbooks | https://docs.nvidia.com/dynamo/reference/components/kvbm-configuration ; https://www.redbooks.ibm.com/docs/MD260021/MD260021.html | 2026（访问） | "each block's access frequency is initialized at 1, doubled on cache hit…only offloads KV blocks from CPU to disk if the blocks have frequency ≥ 2" | 高 |
| 37 | NVIDIA 1.0：embedding cache TTFT −30%/吞吐 +25%；ModelExpress 权重流式加载 DeepSeek-V3 启动 7× | NVIDIA 博客转述 | https://lyceum.technology/magazine/nvidia-dynamo-inference-orchestration-guide/ ; https://clear.ml/blog/clearml-nvidia-dynamo-a-production-control-plane-for-distributed-ai-inference-at-scale | 2026-03/04 | "TTFT by up to 30% and throughput by up to 25%…7x faster model startup for DeepSeek-V3 on H200" | 中高（厂商数字经转述） |
| 38 | Mooncake checkpoint-engine：数千 GPU ~20s 更新 1T 参数；RDMA P2P 权重更新 53s→7.2s | Mooncake GitHub | https://gitee.com/kvcache-ai/Mooncake ; https://github.com/kvcache-ai/Mooncake | 2025-09 / 2026-04 | "updating Kimi-K2 model (1T parameters) across thousands of GPUs in ~20s"；"7x faster weight updates…(53s → 7.2s)" | 高（厂商自报，训练场景） |
| 39 | MemGPT：上下文即虚拟内存，70% 警告/100% 递归摘要驱逐；paging 错误静默累积 | arXiv 2310.08560 + 2026 综述 | https://arxiv.org/html/2310.08560 ; https://arxiv.org/pdf/2603.07670v1 | 2023-10 / 2026 | "When Lctx ≥ Cfast, a swap operation evicts, recursively summarizes, and stores content in recall storage" / "a paging decision that evicts the wrong record simply results in a slightly worse response—no exception, no log entry" | 高 |
| 40 | KV offloading 在 context-intensive 任务上失效：ShadowKV rank-160 不够，需载 5–10% | arXiv 2604.08426 | https://arxiv.org/html/2604.08426v5 | 2026-09 | "they need to load significantly more tokens to match full attention accuracy: 5-10%…compared to the ShadowKV default budget of 1.56%" | 高 |
| 41 | PCIe Gen5 x4 NVMe 上限 ~16GB/s；1GiB KV 重载 ≥67ms；CPU 层须大于 GPU 层否则抖动 | 第三方工程综述（引 vLLM/LMCache/Dynamo 官方文档） | https://eurokommerz.at/blog/kv-cache-offloading-cpu-memory-nvme/ ; https://docs.nvidia.com/dynamo/reference/components/kvbm-configuration | 2026-10 | "a Gen5 x4 drive carries at most 16 GB/s by its link, so a 1 GiB conversation takes at least about 67 ms to reload" | 中高 |
| 42 | Mooncake 跨节点受 RDMA ~15GB/s/NIC 约束 | arXiv 2607.27187（相关工综述） | https://arxiv.org/pdf/2607.27187 | 2026-07 | "Mooncake…remains bounded by RDMA bandwidth(~15 GB/s per NIC)" | 中高 |
| 43 | LMCache 工程定位：KV 从临时状态变可持久存储、跨引擎复用的"AI-native knowledge" | LMCache GitHub | https://github.com/hyscale-lab/lmcache | 2026-06 | "It turns KV cache from a temporary state into reusable AI-native knowledge that can be stored persistently, reused across multiple serving engines" | 高 |
| 44 | HiCache 已支持混合模型（Mamba/GDN）state 的统一分层缓存 | 第三方启动日志分析 | https://jpmrblood.codeberg.page/2026/07/49-sglang-hicache-hybrid-gdn-startup-analysis/ | 2026-07-21 | "Init Unified RadixTree with components (FULL, MAMBA)…Allocating 32.00 GB host memory for hierarchical KV cache…hierarchical Mamba cache" | 中高 |
| 45 | vLLM OffloadingConnector（0.11+）：标准化前缀块卸载接口；FP8 KV 为生产选项 | 工程综述引官方文档 | https://llms.blog/posts/hierarchical-kv-cache-offloading-in-production-llm-serving-host-ram-local-nvme-remote-storage-and-lmcache-architecture | 2026-10-19 | "Modern vLLM versions introduce standardized connector interfaces to offload and reload prompt prefix blocks" | 中 |

---

## 附：方法论说明

- 独立搜索 9 轮共 35+ 查询（英文为主，覆盖论文题名/系统名/官方文档/工程博客），关键论断均落到 arXiv/官方文档/会议论文集 URL；媒体与博客仅作线索或工程实测佐证，并在置信度列标注。
- 2026 年下半年的 arXiv 编号（如 2604.x/2606.x/2607.x）为调研时点真实检索结果；个别为预印本，结论以官方文档与顶会版本为准。
- 奠基工作（PagedAttention/FlexGen/ZeRO-Inference/StreamingLLM/H2O/MemGPT 等 2022–2023 工作）已按要求标注原始年份。

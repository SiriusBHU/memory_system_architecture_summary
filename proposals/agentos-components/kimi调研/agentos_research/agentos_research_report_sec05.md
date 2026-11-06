# 第 5 章 内存管理：传统内存与模型内存的双域治理

本章调研日期为 2026-11-06，时间范围以 2024-01 至 2026-11 为主，奠基性工作单独标注年份。章内论断均附行内引用与置信度标注；凡跨来源存在口径冲突者，按交叉验证裁决结果双边呈现。本章将内存管理问题划分为两个策略域：**传统内存域**（应用匿名页、文件页、图形 buffer 的回收与查杀）与**模型内存域**（KV cache、模型权重、MoE（Mixture-of-Experts，混合专家）专家参数的分页、预取与驱逐），并逐节评审二者在记账底座、QoS（Quality of Service，服务质量）契约与驱逐经济学上的交汇点。

## 5.1 移动端内存管理现状

### 5.1.1 回收与查杀链路：LMKD 全面转向 PSI

Android 的查杀链路已完成从内核态 LMK（Low Memory Killer）驱动到用户态 LMKD（Low Memory Killer Daemon）的迁移：内核 LMK 驱动自 Linux 4.12 起从上游移除，LMKD 自 Android 9（2018）起成为现役主线，由 AMS/OomAdjuster 下发 `oom_score_adj`、lmkd 决策并以 pidfd 执行查杀[^5-1^]。压力检测机制方面，自 Android 10（2019）起 `ro.lmk.use_psi` 默认为 true，LMKD 优先采用 PSI（Pressure Stall Information）触发器、回落 vmpressure；默认阈值为三级——`{PSI_SOME, 70ms}/{PSI_SOME, 100ms}/{PSI_FULL, 70ms}`（1 秒窗口），`ro.lmk.psi_complete_stall_ms` 默认 700ms，`ro.lmk.thrashing_limit` 高性能机 100、低 RAM 机 30（%）[^5-2^]。在 cgroup v2 或低内存设备上，lmkd 强制启用基于 zone 水位、free swap 与 thrashing（refault 率）的"新策略"查杀[^5-1^]。PSI 本身仍在扩维：PSI_IRQ（将 IRQ/SOFTIRQ 压力计入 `irq.pressure`）已于 Linux 6.1（2022-09）合入上游[^5-3^]。可以判定（High 置信）：PSI 家族已成为 lmkd、systemd-oomd、ChromeOS 三方共同的压力信号事实标准。

### 5.1.2 MGLRU：回收器的收敛与落地数据

MGLRU（Multi-Generational LRU）于 Linux 6.1（2022-12）合入，自 Android 14 全系内核（android14-5.15/6.1）起默认开启（Pixel 8 首发），Android 15（GKI 6.6）与 Android 17（内核 6.18.21）均保持默认开启[^5-4^]。Google 公布的落地数据包括：Pixel 6 开启 MGLRU 后应用总体启动时间 −6.60%、后台查杀 −8.04%、kswapd CPU −54.50%、直接回收次数 −81.10%（2022 LPC 演示，2023-10 报道）[^5-4^]；LPC 2024 汇总口径为 Android 手机低内存查杀 −85%、ChromeOS UI 渲染延迟 −18%、Android 应用冷启动 −16%、服务器 kswapd CPU −40%[^5-5^]。需要注明：上述数字来源链为 Google 官方/LPC slides，本轮交叉验证未能独立复核，按 Medium 置信引用[^5-5^]。已知问题方面，2026-05 LWN/LSFMM 讨论确认 MGLRU 仍存在 writeback 落后触发 cgroup OOM、缺乏 cgroup 级 writeback throttling 等问题，min_ttl_ms 防抖机制被证实有效[^5-6^]。

### 5.1.3 Android 17 MemoryLimiter：从"杀"到"封顶"

Android 17（API 37，2026）引入 MemoryLimiter：按设备总 RAM 为每个应用设定 anon+swap 硬上限（写 `memory.high`/`memory.swap.max`），对所有应用生效、无需 targetSdk 37；超限进程被终止，退出描述含 `MemoryLimiter:AnonSwap`，并提供 `am memory-limiter` 调试接口[^5-7^]。两个工程细节值得记录：其一，超限终止默认无日志（"fails silently"），已被开发者社区诟病；其二，Play vitals 将"Excessive memory usage"坏行为阈值设为 4% 会话占比[^5-7^]。MemoryLimiter 与 ESWAP（OpenHarmony，per-memcg score/压缩比/refault 阈值的三层 RAM/ZRAM/ESwap 回收）[^5-8^]、HarmonyOS 7 超空间内存（2026-10-22 官宣，16GB 机型最多等效 +3GB，60+ 存量机型 OTA；媒体称压缩率 65%+、保活应用数 +42%，该组数字为媒体口径，Medium 置信）[^5-9^]共同表明：行业供给手段正从"查杀"转向"压缩+上限+主动回收"。

### 5.1.4 iOS Jetsam 演进：行为感知的查杀调度

iOS 的 Jetsam（memorystatus）机制以优先级带（revision 2 扩展至 0–210：IDLE 0、BACKGROUND 30、FREEZER 75、FOREGROUND 100、CRITICAL 190，另有 AGING_BAND1/2 与 ELEVATED_INACTIVE）从低到高查杀[^5-10^]。其演进方向是"使用概率感知"：`memorystatus_properties_entry_v1.use_probability` 字段记录使用概率；`P_MEMSTAT_RELAUNCH_*` 标志决定 daemon 在 aging band 的停留时间（高/中/低重启概率对应 10/5/2 秒缩放）；JLD（jetsam loop detection）激进回收 elevated idle 进程[^5-11^]。与供给保障最接近的内核级先例是 `CONFIG_SECLUDED_MEMORY`：开启 `secluded_for_apps` 时，优先级 ≥ FOREGROUND 的进程可使用隔离内存池——这是"前台专属内存供给"的工业先例，但粒度粗（仅按是否前台）、无 cgroup 契约语义[^5-10^]。此外，iOS 15+ 开放 `com.apple.developer.kernel.increased-memory-limit` entitlement 提高每进程限额[^5-12^]。

### 5.1.5 dmabuf 记账的上游状态（正确口径）

图形与加速器 buffer 的 memcg（memory control group）记账是统一记账底座的关键一环，其上游状态须按交叉验证裁决后的口径陈述：dma-buf memcg 记账（MEMCG_DMABUF，将导出 dma-buf 计入分配方 cgroup）自 2022 年起经历多轮 RFC，2026-05 出现 charge_pid_fd 路径 RFC（Red Hat，分配时显式归账到目标进程 cgroup），2026-10 仍为 RFC v2（8 补丁系列，含 `DMA_BUF_IOCTL_XFER_CHARGE`、LSM hook 与 SELinux 限制），**截至 2026-10 未合入主线，主线 `memory.stat` 无 dmabuf 键**[^5-13^][^5-14^]。该功能目前实际以 Android GKI 下游补丁形式存在。社区已明确指出两个本质限制：单一属主模型（一块共享 buffer 只记账给一个 cgroup）与 fd 传递时无法改变记账归属[^5-14^]；2022 年的独立 GPU cgroup 控制器提案被否决后才转向 memcg 路径[^5-14^]。（此前调研中"dmabuf memcg 记账已上游合入（6.5）"的表述已被交叉验证证伪，本节采用上述修正口径。）

### 5.1.6 Honor memory.aging：memcg 级主动老化

荣耀于 2026-07 提交 `memory.aging` RFC v2：将 MGLRU 的 debugfs `lru_gen "+"` 原语暴露为 per-cgroup 接口，实现 memcg 粒度的主动老化。该特性已作为 GKI 模块在 6.6/6.12/6.18 内核（高通/MTK 平台）出货，在 Android 与服务器负载上均有稳定收益，但**未合入上游**[^5-15^]。它与 OpenHarmony ESWAP 共同构成"OEM 在下游做 memcg 级 QoS 参数下发+主动回收"的真实出货先例[^5-8^][^5-15^]。

## 5.2 KV cache 管理技术谱系

KV cache 的规模压力是本节的出发点：Llama-3-8B（GQA，8 个 KV head）FP16 KV 约 0.125MB/token；128K 上下文约 15.6GB、1M 上下文约 62.5GB[^5-16^]；70B 级模型 1M token KV 约 164GB/请求，超过权重本身[^5-17^]。围绕该压力，2023–2026 年形成五条技术路线，谱系见表 5-1。

**表 5-1 KV cache 管理五条路线技术谱系**

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 关键数据 |
|---|---|---|---|---|---|
| 块化/分配 | PagedAttention（vLLM） | UC Berkeley | SOSP 2023 | 借鉴 OS 分页，KV 切固定块（默认 16 token）按需分配+块表映射+写时复制 | 内存碎片 60–80%→<4%[^5-18^] |
| 块化/分配 | vAttention | Microsoft Research | ASPLOS 2025 | CUDA 虚拟内存保持 KV 虚拟连续、物理按需分配，不改 attention kernel | decode 吞吐最高 1.97× vs vLLM[^5-19^] |
| 前缀共享 | RadixAttention（SGLang） | LMSYS Org | 2023-12 | radix tree 管理前缀共享，LRU 驱逐+引用计数+缓存感知调度 | GSM-8K 吞吐 4.5×、ReAct agent 5.6×[^5-20^] |
| 压缩 | KIVI | Rice/CMU 等 | ICML 2024 | 免微调 2-bit KV 量化（key 逐通道、value 逐 token+残差滑窗） | 峰值内存 −2.6×，吞吐 2.35–3.47×[^5-21^] |
| 压缩 | KVQuant | UC Berkeley | 2024-01 | RoPE 前量化+非均匀+离群通道保护 | 支撑 10M token 上下文（7B：4,883GB→610GB）[^5-22^] |
| 压缩 | ShadowKV | 北大/CMU 等 | ICML 2025 | pre-RoPE key 低秩 SVD 驻 GPU、value 卸载 CPU | batch 6×、吞吐 3.04×（A100）[^5-23^] |
| 选择性驱逐 | StreamingLLM | MIT/Meta | ICLR 2024 | attention sink 发现：保留前 4 sink token+滚动窗口 | O(1) 内存无限流式生成[^5-24^] |
| 选择性驱逐 | H2O | UT Austin/Stanford/Meta | NeurIPS 2023 | 累计注意力分 heavy-hitter 驱逐 | 20% 预算 PPL 仅差 1.8%；驱逐不可逆[^5-17^] |
| 选择性驱逐 | SnapKV | UIUC/Cohere 等 | NeurIPS 2024 | prefill 末尾观察窗一次性投票压缩 prompt KV | 3.6× 加速、8.2× 省内存、单卡 380K 上下文[^5-25^] |
| 选择性驱逐 | Quest | MIT Han Lab | ICML 2024 | query 感知页级 top-K（页内 min/max 元数据），不丢 token 只少读 | self-attention 7.03×、端到端 2.23×[^5-26^] |
| 卸载/分层 | FlexGen | Stanford/Berkeley | ICML 2023（奠基） | 线性规划搜索 GPU/CPU/磁盘三层卸载+zigzag 调度+4-bit | OPT-175B 单 16GB T4 达 1 tok/s[^5-27^] |
| 卸载/分层 | RetrievalAttention | MSRA/SJTU | NeurIPS 2024 | KV 放 CPU 向量库，ANNS 检索相关 token | 单 A100 跑 1M 上下文、仅扫 1–3% 向量[^5-16^] |
| 卸载/分层 | LMCache | U Chicago 等 | 2025-10 | 引擎外置 KV 层：DRAM/NVMe/Redis/S3 分层+块级前缀哈希 | TTFT 降 3.7–6.8×，同 TTFT 吞吐 2.3–14×[^5-28^] |
| 卸载/分层 | Mooncake | Moonshot AI/清华 | FAST 2025 | KVCache 中心 PD 分离集群，聚合空闲 CPU/DRAM/SSD 全局池 | 仿真吞吐 +525%，生产多扛 75% 请求[^5-29^] |
| 卸载/分层 | Dynamo KVBM | NVIDIA | 2025–2026 | 生产级 G1 HBM/G2 DRAM/G3 NVMe/G4 对象存储四级层级 | 频率制驱逐+SSD 寿命过滤（freq≥2 才落盘）[^5-30^] |

**表 5-1 解读。** 五条路线的收敛速度并不均一。块化路线已由 PagedAttention 完成事实标准化（vLLM/SGLang 均以其为底座），后续工作（vAttention）转向"保留虚拟地址连续性以兼容原生 kernel"的工程优化。压缩路线内部出现清晰分野：运行时表示（KIVI/KVQuant 的量化、ShadowKV 的低秩，面向显存）与传输表示（CacheGen 的算术编码，面向网络）各自独立演进，FP8 KV 已成为 vLLM/SGLang 的生产默认选项之一[^5-31^]。驱逐路线在 reasoning（长思维链）时代遭遇系统性挑战：NVIDIA 官方实测显示，2,048 token 预算下 AIME 2024 全注意力准确率 57.1%，而 SnapKV 仅 34.6%、R-KV 25.4%——永久驱逐在数学推理场景精度崩塌[^5-32^]；研究界的回应是从"按重要性永久丢弃"转向"不丢、只搬、按 query 取回"（Quest/ShadowKV/RetrievalAttention），即驱逐路线事实上被并入了卸载路线。卸载/分层路线则在 2025–2026 年从论文走向生产：LMCache、Mooncake（FAST 2025 最佳论文）、SGLang HiCache（L1 GPU/L2 host/L3 分布式存储）与 NVIDIA Dynamo KVBM 共同把"GPU-HBM→DRAM→NVMe→分布式存储"的 L1–L4 层级做成标准架构，KV cache 从"单请求易失状态"变为"跨请求、跨实例、分层持久化的一等资源"[^5-28^][^5-29^][^5-30^]。端侧对照值得注意的是 Apple AFM 2025：端侧 3B 模型走"架构层双块 KV 共享（KV 内存 −37.5%）+2-bit QAT"路线，而非驱逐或卸载——端侧 KV 驱逐/卸载的系统研究目前近乎空白[^5-33^]。

## 5.3 MoE 专家管理对比

MoE 模型的专家权重占据参数主体（Mixtral-8x7B FP16 约 86GB），而每 token 仅激活少数专家，使"专家级分页/预取/缓存"成为端侧与消费级部署的主杠杆。表 5-2 对比 2023–2026 年代表性工作。

**表 5-2 MoE 专家管理代表工作对比**

| 工作 | 年份/出处 | 预取策略 | 预测/命中率 | 内存节省 | 工程成熟度 |
|---|---|---|---|---|---|
| EdgeMoE | 2023-08（2024/25 修订） | 统计式专家预加载+计算-I/O 流水 | 未报单一命中率（预加载遮蔽大部分 I/O） | 2.6–3.2× vs 全驻留；精度损失 ~2% | 开源（mllm），首个端侧 MoE 引擎（Jetson TX2/RPi 4B）[^5-34^] |
| Mixtral-offloading | 2023-12 | 投机加载（当前层激活跑下一层 gate）+LRU 缓存 | LRU 命中 ~70–85%（第三方复现，Medium 置信） | 86GB→~17.5GB（专家 2bit 混合量化；MMLU 70.51→65.58） | 开源原型（MIT），研究引用广泛[^5-35^] |
| SwapMoE | ACL 2024 | 重要性评分+摊销异步换入（非预测） | 不适用（Virtual Experts 常驻集） | 14.2→4.7 GiB（−67%），延迟 −50% | 开源（HF/Tutel 插件）[^5-36^] |
| Pre-gated MoE | ISCA 2024 | 重训练 pre-gate：第 N 块门控预告第 N+1 块专家 | 设计即"预告=选择"，精度无损 | 峰值 GPU 内存 −4.2×，仅比 oracle 慢 23% | 研究原型（需改模型/重训练）[^5-37^] |
| SiDA-MoE | MLSys 2024 | 离线哈希解耦路由与推理 | top-3 hash 命中 >99%（保真 ~99%） | 显存 −40–80%，吞吐最高 3.93× | 研究原型（需离线训练哈希）[^5-38^] |
| MoE-Infinity | 2024-01/MLSys 2025 | 请求级专家激活矩阵（EAM）追踪+激活感知预取 | 单请求复用倾斜（Mixtral ~25%、百专家模型 <5%）驱动缓存 | GPU 成本最高 −8×；vs offloading 基线延迟 2–20× | **活跃开源服务化**（OpenAI 兼容 API、连续批处理、paged KV、FP4 专家）[^5-39^] |
| MoE-Lightning | ASPLOS 2025 | CGOPipe CPU-GPU-I/O 流水+paged weights+HRM 选型（调度主导，不依赖预测） | — | 显存受限下达吞吐上界，CPU 内存 −2–3× | 学术原型；单 T4 吞吐最高 10.3×[^5-40^] |
| ProMoE | 2024-10 | 学习式 MLP 逐层预测+stride 预取+early preemption 纠错 | **84.7%**（stride 仅 −5pt；token-based 基线仅 58.3%） | 消费级 GPU 可跑 57B | 开源，已集成 transformers/llama.cpp[^5-41^] |
| Fate | 2025-02 | 免训练跨层预取（相邻层 gate 输入高余弦相似）+浅层偏袒缓存 | 预取 78.79%（decoding）/最高 97.15%；浅层全缓存后命中 **99.08%** | 随内存预算伸缩；decode 最高 4.1× vs Load-on-Demand | 研究原型[^5-42^] |
| Pre-attention 预测 | 2025-11 | **同层** attention 前轻量线性预测+排序感知损失 | **93.03%/94.69%/97.62%**（DSV2-Lite/Qwen3-30B/Phi-mini-MoE），超 Fate 15–19pt | — | 研究原型[^5-43^] |
| NPUMoE | 2026-04 | 离线校准专家热度→静态分层+驻留感知 NPU 卸载（非在线预测） | 基于热度驻留 | Apple ANE 承接 MoE prefill：延迟 −1.32–5.55×、能效 +1.81–7.37× | 研究原型（手机 NPU 首个）[^5-44^] |
| WiSP（MV-WSA） | 2026 | **缓存主导**：专家权重与 KV 统一为"一个预算下两条引用流"，边际延迟/字节均衡 | 主张低并发下缓存策略 > 路由预测 | 同 VRAM 下最优分配 | **vLLM drop-in 插件**；最高 1.95× vs 静态 offload[^5-45^] |

**表 5-2 解读。** 该谱系呈现一条清晰的收敛路径：2023 年的端侧/消费级原型（EdgeMoE、Mixtral-offloading、SwapMoE）以"专家放外存、按需加载"建立可行性；2024 年起竞争焦点转向**预测信号**——"router 即预言机"被反复验证：相邻层 gate 输入余弦相似度约 91.7% 是模型固有性质[^5-41^]，免训练跨层预测达 78.79%（Fate）、学习式预测器达 84.7%（ProMoE）、同层 pre-attention 预测达 93–97.6%[^5-42^][^5-41^][^5-43^]，专家热的可预测性已是社区共识（High 置信，多篇 arXiv 原文交叉一致）。评估指标也在收敛：ProMoE 提出的 GoodPred = Accuracy × FetchRate 把"预测准"与"来得及取"统一[^5-41^]。但必须同时呈现两条反向证据（Conflict Zone 双边陈述）：其一，WiSP（2026）证明在**低并发单流 decode** 场景下缓存策略的收益大于路由预测，router 信号的更大价值在于界定"最小安全常驻集"（内存信号）而非延迟信号[^5-45^]；其二，DuoServe-MoE 数据显示简单层级预测器在 Mixtral-8x7B/8x22B 这类**少专家粗粒度模型**上 top-2 准确率仅 54–67%[^5-43^]——"高可预测"结论主要对 DeepSeek/Qwen 类细粒度多专家模型成立。工程成熟度方面，MoE-Infinity 已走向 OpenAI 兼容服务化，是工程化程度最高的开源实现；但服务端主流路线是专家并行（EP+EPLB）"分布式摊平"而非 offload，offload+预取的主战场已收缩到个人机、边缘与端侧[^5-39^]。端侧 MoE 中 NPUMoE（2026-04）刚起步且只覆盖 prefill 卸载，"统一 KV+专家+激活记账"的工业级框架尚不存在（WiSP 的 MV-WSA 是首个统一建模尝试）[^5-44^][^5-45^]。

## 5.4 QoS 供给与 NPU 内存抽象

### 5.4.1 memory.min/low 双契约：服务端先例与移动端空白

cgroup v2 的 `memory.min`（硬保护，任何情况下不回收）与 `memory.low`（软保护，内存充足时不回收）构成供给保障的双契约语义。服务端已有成熟先例：Facebook resctl-demo 以 workload.slice 用 `memory.low` 软保主负载、hostcritical.slice 用 `memory.min` 硬保 768MB、sideload.slice 用 `memory.high` 限膨胀，形成三层契约[^5-46^]；Kubernetes Guaranteed 档以 `memory.low`=request 实现同类语义[^5-47^]。已知风险：`memory.min` 在全局无内存可回收时会卡死分配路径并触发系统 OOM，上游文档明示该语义[^5-47^]。会话级记账也有先例：systemd `session-N.scope` 是 15 年惯例，2026 年已有真实工程（tmuxctl/PocketShell）为每个 agent 会话包 memory-capped scope（slice ≈46GB、每会话 ≈10GB）防止 OOM 级联[^5-48^]。

与此形成鲜明反差的是移动端空白：检索范围内未见 AOSP 将 `memory.min/low` 用作前台供给契约的证据——Android 的 per-app memcg 主要被 lmkd 用于统计与 thrashing 计算；Android 17 MemoryLimiter 是"封顶"而非"保底"[^5-7^]；App Standby Buckets 按使用行为分五桶但只管 job/alarm/网络、不管内存供给[^5-49^]。"移动端以 memory.min/low 做前台供给保障"在 2024–2026 年检索中未见系统研究或工业实践（Medium-High 置信的空白判断）。

### 5.4.2 用户注意力感知调度的最近邻

"QoS 跟用户注意力而非进程身份"的最近邻证据有四类：(a) iOS `CONFIG_SECLUDED_MEMORY` 前台专属内存池——最接近的工业先例，但以"是否前台"这一粗粒度注意力代理为据，无 cgroup 契约语义[^5-10^]；(b) Jetsam 的 use_probability/aging band——感知使用概率但仅用于查杀与老化[^5-11^]；(c) systemd-oomd 对延迟敏感的 `user@UID.service` 建议更低 PSI 阈值（40% vs system.slice 60%）——按会话身份差异化阈值[^5-50^]；(d) 学术界的预测式预载链：FALCON（MobiSys 2012，延迟 −50%、能耗 +2%）、TPP（DATE 2023，启动最高 −52.5%、预取仅 1.31MB）、DeepAPP（SenSys 2019，加载 −68.14%、平均预载 190.6MB），以及 AppFlow（arXiv 2026-03）的关键反面数据——MAPLE 用 LLM 预测下一 App 的命中率仅 52%、误预测浪费数百 MB，因此 AppFlow 将预载上限设为 100MB（<5% DRAM）且标记"压力下可被回收"[^5-51^]。这组证据支持的设计法则是：确定性事件（前台/可见/交互中）可签供给契约，结构性信号可做预取但不应占保底份额，行为概率预测只配驱动"可被回收的投机预载"。

### 5.4.3 内核 accel 子系统与 DMEM cgroup

NPU 内存抽象在内核侧出现唯一实质性收敛点：Linux accel 子系统（drivers/accel，2023 起）以 DRM 为基座承载 AI 加速器驱动（ivpu、habanalabs、amdxdna、qaic 等），上游强制要求以 GEM/BO（Graphics Execution Manager/Buffer Object）做内存管理，推荐 TTM 内存管理器与 drm_sched 调度器（维护者 2024-04 原话："the minimal requirement is to use GEM/BOs for memory management"）[^5-52^]。DMEM cgroup（设备内存 cgroup 控制器）于 Linux 6.14（2025-03）合入主线：GPU 与驱动分配的 CPU 侧内存按 cgroup 记账、驱逐感知，提供 `dmem.current/max/min/low` 接口；NVIDIA MPS v3 已把 dmem 作为内核 ≥6.14 时的默认内存分区后端[^5-53^][^5-54^]。这是"设备内存"首次获得 cgroup 级记账/限额原语，也是统一记账底座唯一可依附的跨厂商事实标准（High 置信）。

### 5.4.4 NPU 隔离研究与移动 SoC 的现实约束

NPU 隔离研究在学术界活跃但无商用落地：NeuMMU（2019，奠基）发现 NPU 地址翻译流量呈突发特征，朴素 IOMMU 平均开销 95%，NeuMMU 降到 0.06%[^5-55^]；vNPU（HotInfra 2023）做硬件辅助多租户虚拟化[^5-56^]；sNPU（ISCA 2024）以 NPU Guarder 轻量 IOMMU+ID 粒度 scratchpad 隔离构建 TEE[^5-57^]；NXT（2025/26）打破 TEE-NPU 单租户绑定，利用率最高 3.49×、调度+隔离平均开销 6.38%[^5-57^]。开销数据（个位数百分比）表明细粒度隔离可行，但无任何商用 NPU 出货多租户隔离；2026 年才有媒体级 CVE 分析指出共享 NPU 计时侧信道可用于权重提取（Low 置信，线索级）[^5-58^]。移动端另有两重现实约束：其一，用户态跨厂商统一 NPU API 已被证伪一次——NNAPI 于 Android 15（2024）官方 deprecated，继任者 LiteRT 走 vendor delegate 路线，2026 年实测多家旗舰机消费级应用拿不到 NPU（媒体实测，Low-Medium 置信）[^5-59^]；其二，移动 SoC 为统一内存架构，NPU 无专用显存，dmem cgroup 不适用，"NPU 内存"实为系统 DRAM 经 dma-buf/AHardwareBuffer 的共享份额——Snapdragon 平台上 QNN 仅接受 DMA-BUF 形式的共享内存[^5-60^]，而 dmabuf memcg 记账如 5.1.5 节所述仍未合入主线且存在单一属主、fd 传递不改账两个公认缺陷[^5-14^]。

## 5.5 四种驱逐去向的成本模型评审

"KV 是纯缓存，驱逐去向有四种——换出（swap 到 CPU/磁盘）、重算（recompute）、上云（传输到远端）、摘要入库（压缩为语义摘要写入记忆库）——且可按统一成本模型定价"是本报告评审的核心立场之一。以下逐条给出证据评审，末段给出"3+1 结构"修订建议。

### 5.5.1 换出——成立，但须修订粒度假设

分层换出已是 2025–2026 年生产标配（HiCache L2/L3、LMCache、KVBM G2–G4、Mooncake），成本结构清晰可建模：PCIe 25–32GB/s 级、NVMe Gen5 x4 上限约 16GB/s（1GiB 会话 KV 重载 ≥67ms）、跨节点 RDMA 约 15GB/s/NIC[^5-61^][^5-62^]。但两点必须修订：(a) vLLM V1 已移除 GPU↔CPU swap、抢占默认改为 RECOMPUTE，官方口径是"V1 结构下重算开销小于换出"——说明**每请求私有 KV 的换出常常不划算**，换出价值高度依赖复用概率：共享前缀（多轮对话、system prompt、RAG 文档）换出回报高（LMCache 同 TTFT 下吞吐 2.3–14×），私有生成中间态换出后几乎不再被读[^5-63^][^5-28^]；(b) 硬件强相关——NVLink C2C（GB300/GH200 主机带宽 450GB/s）使 swap 成本下降一个量级，成本常数必须按平台在线拟合而非取固定值[^5-64^]。FastSwitch 另证明工程开销主要在 API 分发与块粒度：KV 复用机制可使 swap-out 量 −53%[^5-65^]。结论：成本模型成立，但"复用概率/共享度"必须升为一等变量。

### 5.5.2 重算——成立，但成本函数要含机会成本与攻击面

重算已被 vLLM V1 定为默认抢占策略（chunked prefill 摊薄后常低于 PCIe 往返）[^5-63^]；CacheBlend 将对非前缀缓存的重算降到 5–18% token[^5-66^]；CacheGen 在低带宽时主动回退"传文本让 LLM 重算"——工业界已把重算当作可定价选项[^5-67^]。修订点有二：(a) 重算成本随被驱逐前缀长度近线性（注意力近二次）增长，且算力差异主导——Stream2LLM 实测同一重算在 H100 上 50ms、A40 上 200ms，并已对"重算 vs 换出"建立分段线性硬件成本模型[^5-64^]；(b) 重算消耗 prefill 算力预算，高负载下形成"重算颠簸"，已被 Latency-DoS 类攻击利用（反复顶爆 KV 池迫使受害者重算）[^5-63^]。结论：作为默认去向成立，但成本函数 = prefill 时延（按硬件拟合）×概率加权 + 拥塞外部性，不是常数；对 Mamba/GDN 类 recurrent state 还须分架构建模（重算意味着从头 fold 全序列）。

### 5.5.3 上云——成立，需加入压缩-解压干扰项与带宽分级

CacheGen 证明 KV 可作为码流在网络上传输（delta+算术编码，3.5–4.3× 更小码流、随带宽自适应调压缩级别、低带宽回退传文本重算）[^5-67^]；Mooncake/NIXL 证明集群内 RDMA 传 KV 是生产现实[^5-29^]；PD（Prefill/Decode）分离本质就是 KV 跨节点搬家[^5-28^]。修订点有三：(a) **解压与推理在 GPU 上双向干扰**——实测算术解码无法同时把解压与推理的减速压到 30% 以下，2025 年对策是把解压卸载到 DPU/SmartNIC，成本模型必须包含"解压占用的 GPU 计算份额"或 DPU 卸载项[^5-68^]；(b) 跨 WAN 上云与跨 RDMA 集群是两种经济：前者带宽低两个量级，只在"重算极贵（超长前缀）+带宽尚可+隐私允许"三条件同时成立时划算，CacheGen 自身亦承认高端 GPU+低带宽时不如直接传文本[^5-67^]；(c) 端侧上云叠加隐私与合规成本，非纯字节成本。结论：去向成立，成本模型需三段式：编码/压缩算力 + 传输带宽分级（RDMA/局域网/WAN）+ 解码干扰项。

### 5.5.4 摘要入库——挑战：这不是缓存驱逐，系统层证据链缺失

在 2024–2026 年 KV/系统文献中，**没有任何工作把"摘要入库"当作 KV 驱逐的标准去向并给出成本模型**。最接近的只有：(a) MemGPT 在文本层做递归摘要+向量库检索，成本为一次额外 LLM 推理+检索召回误差，且 paging 决策错误是**静默失败**（无异常、无日志，长期累积）[^5-69^]；(b) 永久驱逐系（H2O/SnapKV）证明"不可逆丢弃"在精确召回与数学推理上系统性崩塌（AIME 57.1%→34.6%；needle-in-haystack 类任务 −30~40%）[^5-32^][^5-17^]；(c) 2026 年 offloading 复测显示，即使保留全部 KV、仅用低秩 key 做选择，在 context-intensive 任务上也会失效（需加载 5–10% token 而非默认 1.56%）[^5-70^]。据此给出判断（推断，非文献事实）：摘要入库击穿了"KV 是纯缓存"的前提——摘要是**有损、不可重建、语义级**的派生数据，其成本结构（质量损失函数+一次写入推理+后续检索召回率）与前三个保真去向**不同构**，属于数据治理/记忆层而非内存层。

### 5.5.5 "3+1 结构"修订建议

综合 5.5.1–5.5.4，建议将"四种驱逐去向"修订为 **"3+1"结构**：

1. **保真驱逐三去向同层建模**：换出/重算/上云均为可无损恢复的纯缓存驱逐，适用统一的"带宽-算力-时延"成本模型，按硬件 profile 在线校准常数（Stream2LLM 方法论[^5-64^]），并显式区分复用概率（共享前缀 vs 私有中间态）。
2. **摘要入库单列**：作为"物化（materialization）去向"挂在记忆子系统，质量成本单独建模；若坚持与原三分法同层并列，至少须定义摘要保真度下界与适用场景白名单（闲聊/长程偏好可摘要；精确召回、合规、安全指令禁止）。
3. **概念框架空位**：现有文献无统一表述"保真驱逐（swap/recompute/cloud）与有损驱逐（evict/summarize）是两个范畴"——这是可抢占的概念框架位置；四去向统一成本模型（带宽/算力/时延/质量损失四维）在检索范围内不存在，属真实空位。

## 5.6 趋势判断与对我方立场评审

### 5.6.1 趋势判断

1. **压力信号收敛到 PSI 家族**（High）：lmkd（2019 起）、systemd-oomd、ChromeOS 均以 PSI some/full+持续时长为触发语义，上游持续扩维（PSI_IRQ 6.1）；但上游对新增 PSI 维度保守，openEuler 的 pressure.stat 细粒度扩展停在下游是前车之鉴[^5-3^][^5-50^]。
2. **回收器收敛到 MGLRU，供给手段从"杀"转向"压缩+上限+主动回收"**（High）：MGLRU 在 Android 14–17 全量默认[^5-4^]；MemoryLimiter（2026）、ESWAP、HarmonyOS 超空间内存、Honor memory.aging 共同表明查杀正被降级为兜底[^5-7^][^5-8^][^5-15^]。
3. **QoS 从"进程身份"向"使用行为"缓慢迁移，但全行业停在查杀/限流，未到"供给保障"**（Medium-High）：Jetsam use_probability、App Standby Buckets 都只走了一半；移动端 memory.min/low 供给契约无先例（5.4.1）。
4. **KV cache 成为跨请求、跨实例、分层持久化的一等资源**（High）：LMCache/HiCache/Mooncake/KVBM 的 L1–L4 层级已从论文走向生产[^5-28^][^5-29^][^5-30^]。
5. **NPU 内存抽象碎片化严重，内核侧是唯一收敛点**（High）：accel+GEM/TTM/drm_sched+DMEM cgroup（6.14）构成唯一跨厂商锚点；用户态标准化（NNAPI）已失败一次；移动 SoC 统一内存路径上 dmabuf 记账"有方向、无合入"[^5-52^][^5-53^][^5-14^]。

### 5.6.2 对我方立场的逐条评审

**(1) 统一记账底座——支持，但移动端须自建归账原语。** 内核 dmem cgroup（6.14）+accel 子系统 GEM/TTM 门槛+dmabuf memcg RFC 演进构成可依附的锚点，NVIDIA MPS v3 跟进证明工业界接受该模型[^5-53^][^5-52^]。但移动 SoC 路径不能依赖 dmem（统一内存、无专用显存），dmabuf 记账 4 年 3 轮 RFC 未合主线且单一属主/fd 传递两缺陷未解[^5-14^]；同时 KV cache/权重驻留多为 anon/shmem，不在 dmabuf 口径内。修订建议：底座必须自建 **recharge-on-behalf（代分配归账转移）** 原语——在 dmabuf export/heap alloc 处挂钩（QNN 只接受 dmabuf 形式内存反而简化了挂点[^5-60^]）+ anon/shmem 自有追踪层，不等上游；厂商私有池（VTCM、驱动私有分配）无内核可见性，须 HAL 侧上报补充。该空白属结构性停滞的"持久空位"，先做的一方定义接口。

**(2) 双策略域（传统内存域 × 模型内存域）——支持，有相邻先例。** ChromeOS VMMMS 在 ChromeOS↔ARCVM 间用 balloon+压力信号做跨域仲裁（Chrome tab 丢弃 −50%、不触发 ARC++ 应用查杀、省电 15–20%、省约 750MB），是"双域驱逐互通"最接近的工业证据[^5-71^]；zswap 的 per-cgroup writeback 开关（6.8+）提供跨域"软驱逐"旋钮[^5-72^]。会话级 memcg 粒度有 systemd session scope 与 2026 年 agent 会话封顶工程背书[^5-48^]。交互-后台双契约（前台 memory.low 软保、后台 memory.high 封顶）在移动端为首创空白，差异化成立；前台契约应优先 memory.low 以保留极端回收弹性（memory.min 有卡死分配路径风险）[^5-47^]。配套要求：若做会话级硬上限，必须配套退出原因上报（参考 MemoryLimiter 的 `MemoryLimiter:AnonSwap` 与 Play vitals 4% 阈值机制），否则将重蹈其"静默终止"的生态阻力[^5-7^]。

**(3) router 预告预取——支持（强证据），但须加三重限定。** 证据链：相邻层 gate 输入余弦相似度 91.7%（模型固有性质）→免训练跨层预测 78.79%（Fate）→学习式 84.7%（ProMoE）→同层 pre-attention 93–97.6%[^5-41^][^5-42^][^5-43^]。限定一（时机）：GoodPred=准确率×及时率，建议"跨层粗预告+gate 完成时 early preemption 纠错"双级机制[^5-41^]。限定二（模型粒度）：**该结论对 DeepSeek/Qwen 类细粒度多专家模型成立，对 Mixtral 类少专家模型须保守——简单预测器在其上 top-2 准确率仅 54–67%**[^5-43^]；低并发单流 decode 场景下缓存策略收益大于预测（WiSP），router 信号应作为界定"最小安全常驻集"的内存信号使用[^5-45^]。限定三（按层差异化）：浅层路由偏好模糊，需"浅层偏袒缓存"（Fate 以浅层全缓存把命中率拉到 99.08%）[^5-42^]。此外，依 5.4.2 的预测分层法则，router 预告预取所占内存应标记为"可回收"等级，不得挤占契约内存。

**(4) KV 驱逐经济学——支持且为首要差异化论据，但须采用 5.5.5 的"3+1"修订。** 现有文献仅覆盖"重算 vs 换出"两路（Stream2LLM）[^5-64^]，四去向统一模型是真实空位；摘要入库应单列为物化去向并计入治理开销。时间窗判断（Medium）：相关学术空白预计 1–2 年内被填，属"即将被填的窗口"，先建模型/基准者定义问题。

---

## 本章来源

[^5-1^]: Android LMKD 服务深度解析（掘金）, https://juejin.cn/post/7633644966019350580, 2026-04-28
[^5-2^]: lmkd/psi/oomadj 属性总结（CSDN，含 lmkd 源码 PSI 阈值表）, https://blog.csdn.net/weixin_40214774/article/details/141687953, 2025-07-17
[^5-3^]: sched/psi: Add PSI_IRQ（tip 提交）, https://patchew.org/linux/166273201263.401.14957314590742548008.tip-bot2@tip-bot2/, 2022-09-09
[^5-4^]: Android 14 默认启用 MGLRU（转 Mishaal Rahman + 2022 LPC 数据）, https://xinsanban.10jqka.com.cn/20231018/c651361225.shtml, 2023-10-18
[^5-5^]: MGLRU Updates, LPC 2024 slides, https://lpc.events/event/18/contributions/1781/attachments/1592/3304/mglru-updates-lpc2024.pdf, 2024-09
[^5-6^]: What is to be done about MGLRU?, LWN, https://lwn.net/Articles/1072866/, 2026-05-20
[^5-7^]: Android 17 behavior changes checklist（MemoryLimiter）, https://censuus.com/blog/for-developers/android-17-behavior-changes-target-sdk-37, 2026-10-01；另见 https://stora.sh/blog/2026-04-25-android-17-memory-limits-guide, 2026-04-25
[^5-8^]: OpenHarmony Enhanced SWAP 特性介绍（官方文档）, https://github.com/openharmony/docs/blob/master/zh-cn/device-dev/kernel/kernel-standard-mm-eswap.md, 持续更新（特性 2022-04 发布）
[^5-9^]: 华为详解 HarmonyOS 7 超空间内存（IT之家）, https://www.ithome.com/1/016/755.htm, 2026-10-22
[^5-10^]: XNU kern_memorystatus.h（优先级带/secluded memory）, https://fergofrog.com/code/codebrowser/xnu/bsd/sys/kern_memorystatus.h.html, xnu-12377 快照
[^5-11^]: iOS Jetsam 机制解析, https://blog.wyan.vip/2023/10/iOS_Jetsam.html, 2023-10
[^5-12^]: iOS memory entitlements 整理, https://zenn.dev/mtfum/articles/ios_memory_entitlements, 2026-06-18
[^5-13^]: [PATCH RFC v2 0/8] memcg: dma-buf cgroup accounting and charge transfer（lkml）, https://lore.landau.one/lkml/?t=20261021165104, 2026-10
[^5-14^]: dma-heap 记账补丁讨论与单一属主/fd 传递限制（kernsec 列表）, https://kernsec.org/pipermail/linux-security-module-archive/2026-May/057331.html, 2026-05
[^5-15^]: [RFC v2] mm/mglru: proactive aging via memory.aging（Honor，patchew）, https://patchew.org/linux/0a218053083e41c8bc7aacc552c7f38c@honor.com/, 2026-07
[^5-16^]: RetrievalAttention, arXiv 2409.10516（NeurIPS 2024）, https://arxiv.org/html/2409.10516v3, 2024-09
[^5-17^]: H2O, NeurIPS 2023, https://proceedings.neurips.cc/paper_files/paper/2023/file/6ceefa7b15572587b78ecfcebb2827f8-Paper-Conference.pdf, 2023
[^5-18^]: PagedAttention/vLLM（SOSP 2023）综述与论文, https://tensormesh.ai/learn/pagedattention/, 2023/2026 访问
[^5-19^]: vAttention, arXiv 2405.04437, https://arxiv.org/abs/2405.04437, 2024-05
[^5-20^]: SGLang RadixAttention, arXiv 2312.07104, https://arxiv.org/pdf/2312.07104, 2023-12
[^5-21^]: KIVI, arXiv 2402.02750（ICML 2024）, https://arxiv.org/html/2402.02750, 2024-02
[^5-22^]: KVQuant, arXiv 2401.18079, https://arxiv.org/html/2401.18079v4, 2024-01
[^5-23^]: ShadowKV, ICML 2025（PMLR）, https://proceedings.mlr.press/v267/sun25b.html, 2025
[^5-24^]: StreamingLLM（ICLR 2024）精读, https://www.llms.blog/posts/streamingllm-and-attention-sinks-mathematical-foundations-of-softmax-normalization-artifacts-initial-token-anchoring-and-infinite-context-rolling-kv-cache-mechanics, 2023-09/2026-10
[^5-25^]: SnapKV, arXiv 2404.14469（NeurIPS 2024）, https://arxiv.org/pdf/2404.14469v2, 2024-04
[^5-26^]: Quest, arXiv 2406.10774（ICML 2024）, https://arxiv.org/html/2406.10774v1, 2024-06
[^5-27^]: FlexGen, arXiv 2303.06865（ICML 2023）, https://arxiv.org/abs/2303.06865, 2023-03
[^5-28^]: LMCache, arXiv 2510.09665, https://www.alphaxiv.org/abs/2510.09665, 2025-10
[^5-29^]: Mooncake（FAST 2025 最佳论文）官方站, https://kvcache-ai.github.io/Mooncake/, 2024-07/2026 访问
[^5-30^]: NVIDIA Dynamo KVBM 配置文档, https://docs.nvidia.com/dynamo/reference/components/kvbm-configuration, 2026 访问
[^5-31^]: HiCache 设计文档（SGLang 官方）, https://docs.sglang.ai/advanced_features/hicache_design.html, 2026-11-05 访问
[^5-32^]: KV Cache Compression and Its Infrastructure Problems, NVIDIA Research 官方博客, https://research.nvidia.com/labs/eai/blogs/kv-cache-compression-and-its-infra-problems/, 2026-06-12
[^5-33^]: Apple Foundation Models 2025 Updates, arXiv 2507.13575, https://arxiv.org/abs/2507.13575, 2025-07
[^5-34^]: EdgeMoE, arXiv 2308.14352 及 camera-ready, https://arxiv.org/abs/2308.14352 ; https://openreview.net/pdf?id=DDJeREha18, 2023-08/2024
[^5-35^]: Fast Inference of MoE Models with Offloading（Mixtral-offloading）, arXiv 2312.17238, https://arxiv.org/html/2312.17238v1, 2023-12
[^5-36^]: SwapMoE, ACL 2024, https://aclanthology.org/2024.acl-long.363/, 2024
[^5-37^]: Pre-gated MoE, arXiv 2308.12066（ISCA 2024）, https://arxiv.org/pdf/2308.12066, 2023-08
[^5-38^]: SiDA-MoE, MLSys 2024, https://proceedings.mlsys.org/paper_files/paper/2024/file/698cfaf72a208aef2e78bcac55b74328-Paper-Conference.pdf, 2024
[^5-39^]: MoE-Infinity, arXiv 2401.14361（MLSys 2025）及 GitHub, https://arxiv.org/pdf/2401.14361v2 ; https://github.com/efficientmoe/moe-infinity, 2024-01/2026 访问
[^5-40^]: MoE-Lightning, arXiv 2411.11217（ASPLOS 2025）, https://arxiv.org/abs/2411.11217, 2024-11
[^5-41^]: ProMoE, arXiv 2410.22134, https://arxiv.org/html/2410.22134, 2024-10
[^5-42^]: Fate, arXiv 2502.12224, https://arxiv.org/html/2502.12224v1, 2025-02
[^5-43^]: Pre-attention Expert Prediction（含 DuoServe-MoE 转引数据）, arXiv 2511.10676, https://arxiv.org/html/2511.10676v1, 2025-11
[^5-44^]: NPUMoE, arXiv 2604.18788, https://www.emergentmind.com/papers/2604.18788, 2026-04
[^5-45^]: WiSP/MV-WSA, arXiv 2606.21868, https://arxiv.org/pdf/2606.21868, 2026
[^5-46^]: Facebook Resource Control Demo（resctl-demo）文档, https://facebookmicrosites.github.io/resctl-demo-website/docs/demo_docs/res_protection/cgroup/, 持续维护
[^5-47^]: cgroup v2 memory controller 文档与 OCI runtime-spec issue #1005, https://facebookmicrosites.github.io/cgroup2/docs/memory-controller.html ; https://github.com/opencontainers/runtime-spec/issues/1005, 2019/持续
[^5-48^]: PocketShell issue #726（agent 会话 memory-capped scope）, https://github.com/alexeygrigorev/pocketshell/issues/726, 2026-06-12
[^5-49^]: App Standby Buckets（Android 官方文档）, https://developer.android.google.cn/topic/performance/appstandby, 2025-07-18
[^5-50^]: systemd-oomd.service(8) man page, https://manpages.debian.org/testing/systemd-oomd/systemd-oomd.service.8.en.html, 2026-07-23
[^5-51^]: AppFlow, arXiv 2603.17259, https://arxiv.org/html/2603.17259v1, 2026-03-18；FALCON（MobiSys 2012）, https://people.cs.umass.edu/~dganesan/papers/MobiSys12-Falcon.pdf
[^5-52^]: ArmChina NPU 上游化讨论（accel 维护者 GEM/TTM 门槛）, linux-arm-kernel 列表, https://lists.infradead.org/pipermail/linux-arm-kernel/2024-April/917089.html, 2024-04
[^5-53^]: DMEM cgroup 合入 Linux 6.14 报道, https://www.phoronix.com/news/DMEM-cgroup-vRAM-Control ; https://kernelnewbies.org/Linux_6.14, 2025-01/2025-06
[^5-54^]: NVIDIA MPS v3 Memory Partitioning 文档, https://docs.nvidia.com/deploy/mps/latest/mpsv3-memory-partitioning.html, 2026 访问
[^5-55^]: NeuMMU, arXiv 1911.06859, https://ar5iv.labs.arxiv.org/html/1911.06859, 2019
[^5-56^]: vNPU, HotInfra 2023, https://hotinfra23.github.io/papers/hotinfra23-paper15.pdf, 2023
[^5-57^]: sNPU（ISCA 2024）与 NXT 收录页, https://dl.acm.org/doi/10.1145/3779307 ; https://www.scilit.com/scholars/3592815, 2024/2025-26
[^5-58^]: CVE-2026-1104 NPU 多租户侧信道分析（媒体，线索级）, https://techbytes.app/posts/cve-2026-1104-npu-side-channel-multi-tenant-exploit/, 2026
[^5-59^]: NNAPI deprecation（Android 官方口径转引）与旗舰机 NPU 实测, https://meetonfriday.com/posts/666bbf67/ ; https://gadgets.beebom.com/stories/i-tested-on-device-ai-on-android-and-iphone-results-not-even-close, 2024/2026-04
[^5-60^]: HeteroVDiff（Snapdragon 8 Elite 内存共享事实）与 QNN 官方内存文档, https://arxiv.org/html/2610.16244v1 ; https://docs.qualcomm.com/nav/home/lpai_backend_memory_allocations.html, 2026-09/持续
[^5-61^]: KV cache offloading 工程综述（PCIe/NVMe 带宽与 67ms 重载）, https://eurokommerz.at/blog/kv-cache-offloading-cpu-memory-nvme/, 2026-10
[^5-62^]: KV cache 相关工作综述（RDMA ~15GB/s/NIC）, arXiv 2607.27187, https://arxiv.org/pdf/2607.27187, 2026-07
[^5-63^]: vLLM V1 调度器与抢占（RECOMPUTE 默认、swap 移除）工程解读, https://labhub.hopto.org/blog/ai-platform/2026-08-12-vllm-scheduler-and-preemption?lang=en, 2026-08
[^5-64^]: Stream2LLM, arXiv 2604.16395, https://arxiv.org/pdf/2604.16395, 2026-04
[^5-65^]: FastSwitch, arXiv 2411.18424, https://arxiv.org/pdf/2411.18424, 2024-11
[^5-66^]: CacheBlend 等压缩/融合工作综述引证, arXiv 2607.27187, https://arxiv.org/pdf/2607.27187, 2026-07
[^5-67^]: CacheGen, arXiv 2310.07240（SIGCOMM 2024）, https://arxiv.org/html/2310.07240v4, 2023-10
[^5-68^]: KV 解压与推理 GPU 干扰实测, arXiv 2509.16857, https://www.arxiv.org/pdf/2509.16857, 2025-09
[^5-69^]: MemGPT, arXiv 2310.08560, https://arxiv.org/html/2310.08560, 2023-10
[^5-70^]: KV offloading 复测（ShadowKV 在 context-intensive 任务失效）, arXiv 2604.08426, https://arxiv.org/html/2604.08426v5, 2026-09
[^5-71^]: ChromeOS ARC++ VMMMS 官方博客, https://chromeos.dev/en/posts/improving-performance-with-new-arc-resource-management-features, 2024-07-12
[^5-72^]: Debunking zswap and zram myths（per-cgroup writeback）, Chris Down, https://chrisdown.name/2026/03/24/zswap-vs-zram-when-to-use-what.html, 2026-03-24

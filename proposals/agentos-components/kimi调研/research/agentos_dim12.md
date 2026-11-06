# AgentOS 内存管理组件 · 维度 C：MoE 内存优化 + NPU 内存抽象

调研日期：2026-11-06。时间范围以 2024-01 至 2026-11 为主，奠基工作单独标注年份。来源：MLSys/ASPLOS/ISCA/arXiv 论文、Linux 内核社区（LKML/lore/dri-devel）、官方文档（Android/QNN/华为/vLLM）；媒体仅作线索。

---

## 1. 技术谱系表

### 1.1 MoE 专家级内存管理（offloading / caching / prefetching）

| 工作 | 年份/出处 | 层级 | 核心机制 | 工程成熟度 |
|---|---|---|---|---|
| MoE offloading（Mixtral-offloading / Eliseev & Mazur） | 2023-12 arXiv[^6^] | 消费级 GPU | LRU 专家缓存 + 投机预取（用当前层激活跑下一层 gate 猜下一层专家）+ HQQ 混合量化（注意力 4bit/专家 2bit） | 开源（dvmazur/mixtral-offloading，MIT），工程原型，研究引用广泛[^14^][^20^] |
| EdgeMoE | 2023-08 arXiv；2024/2025 修订[^8^][^18^] | **端侧**（Jetson TX2、Raspberry Pi 4B） | 非专家权重常驻内存、专家权重放外存按需加载；专家级比特宽自适应 + 基于统计的专家预加载与 I/O 计算流水 | 开源（UbiquitousLearning/mllm），264+ 引用；首个端侧 MoE 引擎[^8^][^15^] |
| SwapMoE | 2023-08 arXiv；ACL 2024[^9^] | 端侧 | "Virtual Experts" 常驻集 + 重要性评分 + 摊销/异步换入换出；可调内存预算 | 基于 HF Transformers/Tutel 实现，+4k LoC |
| Pre-gated MoE | ISCA 2024[^2^][^3^] | 数据中心单卡 | **算法-系统协同**：训练 pre-gate 函数让第 N 块门控预先选出 N+1 块专家，彻底消除"选择→执行"顺序依赖 | 研究原型（需重训练/微调），未开源主流通路 |
| Fiddler | 2024-02 arXiv[^23^] | 消费级 | CPU-GPU 编排：小 batch 时直接在 CPU 上执行专家比搬运更划算 | 开源，华盛顿大学 |
| MoE-Infinity | 2024-01 arXiv；MLSys 2025[^5^][^13^] | 个人机/单服务器 | 请求级专家激活矩阵（EAM）追踪 + 激活感知预取/缓存；发现"单请求内复用倾斜、跨请求趋匀"（Mixtral 单请求仅 ~25% 专家复用，百专家模型 <5%）[^21^] | **活跃开源**（EfficientMoE/MoE-Infinity）：OpenAI 兼容服务、连续批处理、paged KV、FP4 专家，工程化程度最高[^13^] |
| SiDA-MoE | MLSys 2024[^15b^] | 数据中心 | 离线哈希函数解耦路由与推理；top-3 hash 命中率 >99%；Switch-base 显存降 40–80%，吞吐最高 3.93× | 需离线训练哈希；保真度 ~99% |
| MoE-Lightning | ASPLOS 2025[^24^] | 受限 GPU | CGOPipe CPU-GPU-I/O 流水 + paged weights + HRM 层次 Roofline 性能模型选部署策略 | 学术原型（UC Berkeley/Sky Computing 系） |
| ProMoE | 2024-10 arXiv[^11^] | 消费级 | 学习式（MLP）逐层预测器 + stride 预取 + 主动缓存（chunked prefetch、early preemption、reordered inference）；提出 GoodPred = Accuracy × FetchRate 指标 | 开源（promoe-opensource/promoe），集成进 transformers 与 llama.cpp |
| Fate（Cross-Layer Gate） | 2025-02 arXiv[^1^][^7^] | 端侧/边缘 | 免训练跨层预取（利用相邻层 gate 输入高余弦相似度）+ 浅层偏袒缓存 + 热度感知混合量化 | 研究原型 |
| HybriMoE | 2025-04 arXiv[^8b^] | 消费级（基于 KTransformers） | 动态层内 CPU-GPU 负载均衡 + impact-driven 层间预取 + 基于评分的缓存 | 开源，kTransformers 之上 |
| Pre-attention expert prediction | 2025-11 arXiv[^25^] | 服务器 | **同层**预取：attention 前用轻量 2 层线性预测器预测本层专家（softmax/LN 保排序），解决跨层方法对前几层失效问题 | 研究原型 |
| ST-MoE（Spatio-Temporal Prefetching） | 2026-06 arXiv[^0^] | 可重构硬件 | 跨层相关表 CCT + 历史表 HT，纯统计无训练，预取与 attention 重叠 | 硬件协同原型 |
| DALI | 2026-02 arXiv[^26^] | 本地 PC | 工作负载感知专家分配，对比 llama.cpp/KTransformers/MoE-Lightning/HybriMoE | 研究原型 |
| NPUMoE（Apple ANE） | 2026-04 arXiv[^27^] | **手机 NPU** | 专家静态容量分层 + 分组执行 + 驻留感知的 NPU 卸载；prefill 阶段卸载到 ANE | 研究原型；直接处理 NPU 动态 shape 不友好问题 |
| WiSP（MV-WSA） | 2026 arXiv[^28^] | 单 GPU vLLM 插件 | 把专家权重与 KV cache 统一为"一个预算下的两条引用流"，边际延迟/字节均衡分配；**主张低并发下缓存策略比路由预测更重要** | vLLM drop-in 插件 |

### 1.2 NPU 内存抽象 / 标准化 / 隔离

| 工作/机制 | 年份 | 内容 | 状态 |
|---|---|---|---|
| Linux accel 子系统（drivers/accel） | 2023 起 | 以 DRM 为基座承载 AI 加速器驱动（ivpu、habanalabs、amdxdna、qaic 等）；上游**强制要求 GEM/BO 做内存管理，推荐 TTM 内存管理器与 drm_sched**[^29^][^30^] | 主线活跃；Linux 6.14（2025-03）并入 amdxdna（AMD Ryzen AI NPU）[^31^] |
| Intel ivpu 驱动 | 2023-01 合入[^32^] | VPU 内建基于 ARM MMU-600 的 MMU，"translates VPU to host DMA addresses, **isolates user workloads**" | 主线 |
| DMEM cgroup | Linux 6.14（2025-01 提交/2025-03 发布）[^33^][^34^] | 设备内存 cgroup 控制器：GPU/驱动分配的 CPU 侧内存按 cgroup 记账、驱逐感知；"依赖 TTM 的驱动可轻松接入"；未来可扩展到其他带专用内存设备 | 已主线；NVIDIA MPS v3 已支持 dmem 后端[^35^] |
| dma-buf memcg 记账 | 2022 起多轮 RFC；2026-05 RFC（pid_fd 路径）；2026-10 RFC v2（8 个补丁，含 LSM hook、SELinux 限制、charge 迁移 ioctl）[^36^][^37^][^38^] | MEMCG_DMABUF 把导出 dma-buf 计入分配方 cgroup；支持中央分配器（如 Android allocator HAL）按 pidfd 向客户端记账；已知局限：**单一属主模型**（共享 buffer 只计一份）、跨 cgroup 转移需新 uAPI | **仍处 RFC，未合主线**；2022 版 GPU cgroup 控制器提案被否后转向 memcg 路径[^39^] |
| Android NNAPI | 2018（Android 8.1）引入；**Android 15（2024）deprecated**[^40^][^41^] | 共享内存模型：ashmem/mmap fd/AHardwareBuffer（BLOB/通用）+ Android 11 起 memory domain（`IDevice::allocate` 驱动自管 buffer）[^42^][^43^] | 弃用；NN HAL 保留供 AICore 等系统服务使用；MediaTek NP9 将移除 NNAPI[^44^] |
| LiteRT / CompiledModel | 2024-09 TFLite 更名 LiteRT[^45^] | 后继者走"可更新运行时 + vendor delegate"路线；NPU 支持 vendor 锁定、覆盖不全（实测多家旗舰机消费级应用拿不到 NPU）[^46^][^47^] | 官方主线；Android 17 增 `FEATURE_NEURAL_PROCESSING_UNIT`/`NpuManager` AIDL[^48^] |
| Qualcomm QNN（AI Engine Direct） | 持续 | QnnMem/共享 buffer 实现 CPU/GPU/DSP 零拷贝；QNN 仅接受 DMA-BUF 形式的共享内存（AHardwareBuffer/Hexagon heap）[^49^][^50^] | 厂商私有栈 |
| Huawei CANN/Ascend | 持续 | driver-runtime-library 三层；运行时负责设备内存管理（ACL API）；云侧以整卡分配为主（`huawei.com/ascend-310: '1'`）[^51^][^52^] | 厂商私有栈 |
| NeuMMU | 2019（奠基）[^53^] | 首个 NPU MMU 研究：NPU 翻译流量呈"突发"特征，GPU 式 IOMMU 平均 95% 开销；NeuMMU（PRMB+多 PTW+TPreg）降到 0.06%，能耗降 16.3×；使能按需分页/NUMA 直访 | 学术奠基 |
| vNPU（Hardware-Assisted Virtualization for NPUs） | 2023 HotInfra（UIUC/Google）[^54^] | 硬件辅助多租户 NPU：算子调度器并发执行 + vNPU 抽象做分配/映射/调度，兼顾利用率与性能/安全隔离 | 学术原型 |
| sNPU | ISCA 2024[^55^] | 集成式 NPU 的 TEE：NPU Guarder（轻量 IOMMU）+ NPU Isolator（基于 ID 的细粒度 scratchpad/NoC 隔离），避免传统 IOMMU 页表遍历开销 | 学术原型（RISC-V/Penglai 生态） |
| NXT（TEE-NPU 多租户共享） | 2025/26[^56^] | 打破 TEE-NPU 单租户绑定：NPU Trusted Agent 全局调度 + 细粒度隔离；利用率最高 3.49×、ANTT 7.24×，调度隔离平均开销 6.38% | 学术原型（gem5） |
| GUARDIAN/TNPU 等 NPU TEE 谱系 | 2022–2026 综述[^57^] | TNPU：host enclave 校验 CPU/NPU 双侧内存翻译；GUARDIAN：离散 NPU 自带 HW-RoT 零主机信任 | 综述确认方向活跃 |
| 多租户 NPU 侧信道（CVE-2026-1104 分析） | 2026[^58^] | 共享 NPU 的计时/性能计数器可被同驻租户用于权重提取；缓解=硬隔离、关闭高分辨率计时器、固定 batch/kernel 调度 | 媒体/厂商分析（线索级，非学术） |

---

## 2. 关键数据（带出处与日期）

### 2.1 MoE 预取/预测命中率（router 预告可行性证据链）

- **免训练跨层预取可达 ~79%**：Fate 用第 i 层 gate 输入预测第 i+1 层专家，decoding 阶段预取准确率 78.79%（prefill 达 >99.6%/88.83%，取决于取数位置）；浅层全缓存后**专家命中率 99.08%**，跨层预取准确率最高 97.15%（结合阈值全加载）[^1^][^7^]（2025-02）。
- **学习式预测器 84.7%**：ProMoE 的 MLP 逐层预测器平均准确率 84.7%，stride 预取下仅降 5%；token-based（MoE-Infinity 式）预测器仅 58.3%；提出 GoodPred = Accuracy × FetchRate[^11^]（2024-10）。
- **同层（attention 前）预测 93–97.6%**：DeepSeek-V2-Lite 93.03%、Qwen3-30B 94.69%、Phi-mini-MoE 97.62%，比 FATE 跨层方法绝对提升 15–19 个百分点；比 token-based/其他缓存法高 30–40 个百分点[^25^]（2025-11）。
- **哈希解耦路由 top-3 命中率 >99%**：SiDA-MoE 离线哈希，专家激活预测 >99%，精度保持 ~99%[^15b^]（MLSys 2024）。
- **投机加载（Mixtral-offloading）**：用当前层激活跑下一层 gate 做猜测，LRU 缓存 k=2（12GB）/k=4（16GB）；实测消费级场景 LRU 命中率约 70–85%（第三方复现叙述，非论文原文）[^6^][^23b^]（2023-12）。
- **DuoServe-MoE**：轻量层级预测器在 Mixtral-8x7B/8x22B 上 top-2 准确率 54–67%、hit-1 90.3–95.5%[^25^]（2025）。
- **SP-MoE**（投机解码场景）：多数层预测准确率 70–90%，draft token 命中率 ~44.3%[^25^]（2025）。
- **结构性观察（事实）**：相邻 MoE 层输入余弦相似度 ~91.7%（DS-2）[^11^]；单请求内专家复用高度倾斜（Mixtral 单请求复用 ~25% 专家、百专家模型 <5%），跨请求合并后趋匀——**全局频率缓存会丢失当前请求所需信号**[^21^]。

### 2.2 内存节省与加速比

- **EdgeMoE**：内存占用比全量驻留（IO-FREE）节省 **2.6–3.2×**（camera-ready 版本）；相对传统全内存模型 1.05–1.18×；Jetson TX2/RPi 4B 上提速 1.5–2.5×，部分任务 10×；对比 IO-EXP 在 HDD 上 4.49–4.76×、SSD 上 2.63–3.01×；精度损失平均 ~2%[^18^][^0b^]（2023-08/2024）。
- **Pre-gated MoE**：峰值 GPU 内存降低 **4.2×**，仅比"全量驻留"oracle 多 **23%** 延迟开销；精度不降甚至略升[^3^]（ISCA 2024）。
- **MoE-Infinity**：对比 DeepSpeed-Inference/Llama.cpp/Mixtral-Offloading/BrainStorm 延迟提升 **2–20×**；达到全 GPU 部署 64–95% 的延迟/吞吐，同时 GPU 成本节省最高 8×；TPOT：DeepSpeed 737ms / Mixtral-Offloading 1250ms / Llama.cpp 2590ms / vLLM 485ms / **MoE-Infinity 173ms**[^5^][^19^]（2024-01，MLSys 2025）。
- **ProMoE**：对比手工缓存 SOTA prefill 1.78×（最高 2.48×）、decode 1.34×（最高 1.79×）；对比开源 offloading prefill 2.20×（最高 3.21×）、decode 2.07×（最高 5.02×）[^11^]。
- **Fate**：prefill 最高 4.5×/1.9×（vs Load-on-Demand/EAP），decode 最高 4.1×/2.2×；高端 PC 上 Qwen1.5-MoE 达 14 tok/s[^1^]。
- **MoE-Lightning**：单 T4(16GB) 上 Mixtral-8x7B 吞吐最高 **10.3×** 于既有 offloading 系统；显存受限时用 2–3× 更少 CPU 内存即可达吞吐上界[^24^]（ASPLOS 2025）。
- **HybriMoE**：prefill 1.33×、decode 1.70× vs SOTA 混合框架[^8b^]（2025-04）。
- **SwapMoE**：Switch Transformer 14.2 GiB → **4.7 GiB（-67%）**，延迟降 50%，Rouge-2 仅降 0.041[^9^]（ACL 2024）。
- **Fiddler**：单 batch 推理延迟加速最高 8.2×/10.1×（Quadro RTX 6000/L4）[^23^]（2024-02）。
- **SiDA-MoE**：Switch-base-128/256 显存降 40–80%，吞吐最高 3.93×[^15b^]。
- **NPUMoE（Apple ANE）**：延迟降 1.32–5.55×、能效升 1.81–7.37×、CPU 占用降 1.78–5.54×[^27^]（2026-04）。
- **WiSP**：vLLM 插件比引擎自带静态 offload 快至 1.95×（同等 VRAM）[^28^]（2026）。
- **Mixtral-offloading 量化**：86GB FP16 → ~17.5GB（专家 2bit+其他 4bit），MMLU 70.51→65.58[^16^]。

### 2.3 NPU 侧关键事实

- Linux accel 上游门槛（维护者 Oded Gabbay 原话）："the minimal requirement is to use **GEM/BOs for memory management**"，并建议用 **TTM** 替代自研内存管理器、用 **drm_sched** 替代自研调度器（ArmChina 周易 NPU 上游化讨论，2024-04）[^29^]。
- DMEM cgroup（Linux 6.14，2025-03-24 发布）："Both GPU and driver-allocated CPU memory will be accounted to the correct cgroup, and eviction would be made cgroup aware"[^34^]；NVIDIA MPS v3 已把 dmem 作为默认后端（kernel ≥6.14 自动检测）[^35^]。
- dma-buf memcg 记账：**截至 2026-10 仍是 RFC v2**（8 补丁系列，含 `DMA_BUF_IOCTL_XFER_CHARGE`、SELinux 限制跨 cgroup 记账）；社区明确指出两大未解限制：(1) 一块内存只能记给一个 cgroup，无共享多记账概念；(2) fd 传递时无法改变记账归属；且"GPU 侧刚看到又一个驱动私有的孤岛式记账尝试，这种单驱动孤岛往往不可用"（Christian König 评论，2026-05）[^36^][^37^][^38^]。
- NNAPI 官方弃用原文："With the release of Android 15, NNAPI will be deprecated… we expect the majority of devices in the future to use the CPU backend, and therefore for performance critical workloads, we recommend migrating to alternative solutions"[^40b^]（2024）；NN HAL 保留，AICore 内部仍走 NN HAL[^41^]。
- 2026 实测：骁龙 8 Elite/天玑 9500/Tensor G5 旗舰机上消费级 App **无一家真正用到 NPU**（"problem lies with the software more than hardware"）[^46^]；Android 17 引入 `FEATURE_NEURAL_PROCESSING_UNIT` 与 NpuManager/调度 AIDL，直接访问 NPU 需 manifest 声明[^48^]。
- 移动端共享内存事实标准：Snapdragon 8 Elite 上 CPU/GPU/DSP 仅通过 **DMA-BUF fd**（AHardwareBuffer 或 Hexagon heap）共享内存，"QNN accepts memory only in this form"[^50^]。
- 多租户 NPU 隔离开销数据点：NXT 调度+隔离平均开销 6.38%[^56^]；vChunk（Feng et al., 2025-06）翻译干扰致租户间减速 <1%（对比 MIG/共享页式最高 40%）[^59^]。

---

## 3. 趋势判断（收敛方向 + 空白点）

**MoE 内存优化（2023→2026 收敛路径清晰）：**
1. **"router 即预言机"被反复验证**：相邻层 gate 输入高余弦相似（91.7%）使免训练跨层预测达 ~79%；轻量学习式预测器（MLP/2 层线性）达 85–98%；同层 pre-attention 预测把首层短板也补上（93–98%）。**专家热的可预测性已是社区共识，争议只在"用什么信号、花多少训练成本"**。[^1^][^11^][^25^]
2. 指标在收敛：ProMoE 的 GoodPred（Accuracy × FetchRate）把"预测准"与"来得及取"统一，预示评估标准化。
3. 工程化在收敛：MoE-Infinity 走向 OpenAI 兼容服务化（连续批处理、paged KV、FP4）；vLLM 主线走 EP+EPLB（专家并行负载均衡）+ 容错恢复，**服务端主流是"分布式摊平"而非"offload"**；offload 预取的主战场收缩到个人机/边缘/端侧。[^8e^][^13^]
4. 反向声音出现（值得警惕）：WiSP（2026）指出**低并发单流 decode 下，缓存策略 > 路由预测**，路由信号的更大价值是界定"最小安全常驻集"（内存信号）而非延迟信号；DuoServe 等数据也显示简单层级预测在 Mixtral 上 top-2 仅 54–67%。[^28^][^25^]
5. **空白点**：(a) 端侧 MoE（手机 NPU/CPU 混合）工作仍少，NPUMoE（2026）刚起步且只覆盖 prefill 卸载；(b) 专家缓存替换策略多为 LRU/评分制，尚无"统一 KV+专家+激活"的工业级记账框架（WiSP 的 MV-WSA 是首个统一建模尝试）；(c) 预测器跨域泛化（换任务分布后的准确率衰减）缺系统性研究。

**NPU 内存抽象（碎片化严重，标准化刚萌芽）：**
1. **内核侧是唯一实质收敛点**：accel 子系统以 DRM GEM/BO + TTM + drm_sched 作为上游准入门槛，ivpu/amdxdna/habanalabs 已统一到此模型；DMEM cgroup（6.14）首次给"设备内存"一个 cgroup 级记账/限额原语，NVIDIA 已跟进。**这是"统一记账底座"可依附的唯一跨厂商事实标准。**[^29^][^33^][^35^]
2. **用户态标准化失败一次**：NNAPI（Android 8.1–15）作为"统一 NPU 接口"被官方弃用，原因正是厂商实现参差+模型演进快于 OS API；继任者 LiteRT 走 vendor delegate 路线，NPU 覆盖"patchy, vendor-locked"。**跨厂商用户态 API 标准化已被证明难以为继，系统级抽象（HAL/AIDL）保留。**[^40b^][^46^][^48^]
3. **dma-buf 记账仍在路上**：MEMCG_DMABUF 从 2022 GPU cgroup 提案被否，转到 memcg 路径，2026-10 才到 RFC v2；共享 buffer 单一属主、fd 传递改账两大本质问题未解。**NPU 路径上 dmabuf 记账"有方向、无合入"。**[^36^][^38^][^39^]
4. **隔离研究活跃但都在学术界**：NeuMMU（地址翻译）→ vNPU（虚拟化）→ sNPU/NXT/GUARDIAN（TEE/多租户）；开销数据（<1%–6.4%）表明细粒度隔离可行，但**无任何一家商用 NPU 出货多租户隔离**；侧信道（计时/性能计数器权重提取）2026 年才有 CVE 级分析，防御依赖"硬隔离+关计数器+恒定调度"。[^53^][^54^][^55^][^56^][^58^]
5. **空白点**：(a) 移动端 NPU 无独立显存（统一内存），dmem cgroup 不适用，SoC 上"NPU 内存"实为系统 DRAM 份额——统一记账需要覆盖 dmabuf/ION/CMMA 等混合路径，目前内核只有 dmabuf stat（RFC 中）；(b) 无跨厂商的 NPU 内存 QoS/驱逐语义；(c) NPU 侧信道缺乏系统性的学术测量工作（多为 GPU 侧信道外推）。

---

## 4. 对我方的启发（逐条）

**立场 A：MoE 专家管理——"专家热是可预测的热，router 预告预取"**

- **支持（强证据）**：免训练跨层信号 79%（Fate）→ 学习式 85–98%（ProMoE/pre-attention）→ 同层 pre-attention 93–98%，且相邻层相似度 91.7% 是模型固有性质。router/gate 信号作为预取触发源是 2024–2026 文献的主流收敛方向，我方"router 预告预取"立场与 ISCA/MLSys 级别证据一致。[^1^][^11^][^25^]
- **需要修订（三点）**：
  1. **预告时机比预告信号更关键**：GoodPred = 准确率 × 及时率。跨层（N→N+1）预告给整个一层的时间窗；同层 pre-attention 预告只给 attention 的时间窗但准确率高 15–19 个点并解决首层问题。**建议采用"跨层粗预告 + gate 完成时 early preemption 纠错"双级机制**（ProMoE 的 early preemption 即此：gate 一完成就抢占预取队列，把所有被动 miss 转成主动精确预取）。[^11^]
  2. **低并发场景立场需打补丁**：WiSP 证明单流 decode 下缓存策略（最小常驻集界定）收益大于预测；DuoServe 显示 Mixtral 类少专家模型上简单预测 top-2 仅 54–67%。**"可预测"结论对 DeepSeek/Qwen 类细粒度多专家模型成立，对 8 专家粗粒度模型要保守。**[^25^][^28^]
  3. **浅层要特殊处理**：Fate 发现浅层路由偏好模糊导致预取准确率低，"浅层偏袒缓存"（前几层专家全缓存）把命中率拉到 99%。router 预告策略需按层差异化。[^1^]
- **挑战（弱）**：token-based 预测（MoE-Infinity 早期路径）准确率仅 58.3%，说明不是所有 router 侧信号都够用；纯统计表（ST-MoE 的 CCT/HT）免训练但需要 warmup profiling。[^11^][^0^]

**立场 B：统一记账底座需覆盖 NPU 内存**

- **支持**：内核 dmem cgroup（6.14+）+ memcg dmabuf 记账（RFC v2，2026-10）+ accel 子系统 GEM/TTM 强制要求，三者构成可依附的内核级锚点；NVIDIA MPS v3 已用 dmem 做内存分区，证明工业界接受该模型。[^29^][^33^][^35^][^36^]
- **需要修订**：
  1. **移动 SoC 路径不能依赖 dmem**：手机 NPU 无专用显存，内存是统一 DRAM 经 dma-buf/AHardwareBuffer 共享，而 dmabuf 记账尚未合入主线且存在"单一属主、fd 传递不改账"两个公认缺陷。**统一记账底座在移动端必须自建 fd 生命周期追踪层**（QNN 只接受 dmabuf 形式内存这一事实反而简化了挂点：在 dmabuf export/heap alloc 处挂钩即可覆盖 CPU/GPU/NPU 三方）。[^37^][^38^][^50^]
  2. **用户态"跨厂商统一 NPU API"路线已被 NNAPI 判死刑**，我方底座应定位在 **内核记账 + 系统服务层（类 AICore/NN HAL 位置）**，而不是应用-facing API；Android 17 的 NpuManager/调度 AIDL 是新挂点。[^40b^][^41^][^48^]
- **挑战**：dmabuf memcg 合入时间不确定（4 年未合入）；厂商私有栈（CANN/QNN）的驱动内存分配不经过 dmabuf 的部分（如 VTCM/片上 SRAM、驱动私有池）无内核可见性——**统一记账必然有盲区，需要厂商 HAL 侧上报补充**。[^51^][^49^]

**立场 C：跨厂商 NPU 内存管理标准化**

- **支持（部分）**：内核 accel+DRM 已经是"半标准化"（GEM/BO/TTM/drm_sched 为公共语言），且中国厂商（ArmChina 周易）也在向该模型上游化。[^29^]
- **挑战**：用户态标准化失败史（NNAPI）+ 厂商 SDK 内存模型各自为政（QNN dmabuf-only、CANN ACL 池化、ANE IOSurface 连续分配+硬 pin 上限 8–12 buffer）。**标准化机会窗口在"记账/限额/隔离语义"而非"分配 API"**——这与 dmem/memcg 演进方向一致。[^57b^][^49^][^51^]
- **新增机会**：多租户 NPU 隔离（sNPU/NXT/vNPU）开销已降到个位数百分比，但无商用落地；若 AgentOS 面向共享设备/多 Agent 场景，**隔离+记账可以打包成差异化能力**（参考 NVIDIA MPS v3 借 dmem 落地的路径）。[^35^][^55^][^56^]

---

## 5. 组件特有输出素材：MoE 专家管理对比表

| 工作 | 年份 | 预取策略 | 预测/命中率 | 内存节省 | 推理加速 | 工程成熟度 |
|---|---|---|---|---|---|---|
| Mixtral-offloading[^6^] | 2023 | 投机加载（当前层激活跑下一层 gate）+ LRU 缓存 | LRU 命中 ~70–85%（第三方）[^23b^] | 86GB→~17.5GB（混合量化） | 消费级可用（2–4 tok/s 级） | 开源原型（MIT），社区影响大 |
| EdgeMoE[^8^][^18^] | 2023–24 | 统计式专家预加载 + 计算-I/O 流水 | 论文称预加载可遮蔽大部分 I/O（未报单一命中率） | 2.6–3.2× vs 全驻留 | 1.5–2.5×（最高 10×）；vs IO-EXP 最高 4.76× | 开源（mllm），端侧首个 |
| SwapMoE[^9^] | 2023/ACL24 | 重要性评分 + 摊销异步换入（非预测） | 不适用（masked gating 重定向） | 14.2→4.7 GiB（-67%） | 延迟 -50% | 开源（HF/Tutel 插件） |
| Pre-gated MoE[^2^][^3^] | ISCA 2024 | **重训练 pre-gate**，N 块门控预告 N+1 块 | 精度无损（设计即"预告=选择"） | 峰值 GPU 内存 -4.2× | 仅比 oracle 慢 23% | 研究原型，需改模型 |
| SiDA-MoE[^15b^] | MLSys 2024 | 离线哈希解耦路由 | top-3 hash 命中 >99% | 显存 -40–80% | 吞吐最高 3.93× | 研究原型，需离线训练 |
| MoE-Infinity[^5^][^13^][^21^] | 2024/MLSys25 | 请求级激活矩阵（EAM）追踪 + 激活感知预取；初层缓存优先 | 单请求复用倾斜（Mixtral ~25%）驱动缓存 | GPU 成本最高 -8× | vs offloading 系统 2–20×；达全 GPU 64–95% 性能 | **活跃开源服务化**（OpenAI API、连续批处理） |
| MoE-Lightning[^24^] | ASPLOS 2025 | CGOPipe 流水 + paged weights + HRM 选型 | 不依赖预测（调度主导） | 显存受限下达吞吐上界，CPU 内存 -2–3× | 最高 10.3×（T4/Mixtral） | 学术原型 |
| ProMoE[^11^] | 2024-10 | 学习式 MLP 逐层预测 + stride 预取 + early preemption 纠错 | **84.7%**（stride 仅 -5%；token-based 58.3%） | 消费级 GPU 可跑 57B | prefill 最高 2.48×、decode 最高 5.02× | 开源，集成 transformers/llama.cpp |
| Fate[^1^][^7^] | 2025-02 | 免训练跨层 gate 输入复用 + 浅层偏袒缓存 | 预取 78.79%（decoding）/最高 97.15%；缓存命中 **99.08%** | 随内存预算伸缩 | prefill 4.5×、decode 4.1× vs LoD | 研究原型 |
| HybriMoE[^8b^] | 2025-04 | impact-driven 层间预取 + 评分缓存 + CPU-GPU 动态分担 | —（缓存评分制） | 与基线等显存 | prefill 1.33×、decode 1.70× | 开源（KTransformers 上） |
| Pre-attention 预测[^25^] | 2025-11 | **同层** attention 前轻量线性预测 + 排序感知损失 | **93.03%/94.69%/97.62%**（DSV2-Lite/Qwen3-30B/Phi-mini） | — | 解决首层与前几层预取失效 | 研究原型 |
| ST-MoE[^0^] | 2026-06 | 跨层相关表 CCT + 历史表 HT（纯统计）+ 硬件预取流水 | 高（Fig.7，未给单值） | — | 优于 Pre-gated MoE（免训练） | 硬件协同原型 |
| NPUMoE[^27^] | 2026-04 | 离线校准专家容量/热度 → 静态分层 + 驻留感知 | 基于热度驻留（非在线预测） | NPU 可承接 MoE prefill | 延迟 -1.32–5.55×、能效 +1.81–7.37× | 研究原型（Apple ANE） |
| WiSP/MV-WSA[^28^] | 2026 | **缓存主导**：专家+KV 统一预算，边际延迟/字节均衡 | 主张预测价值在"内存信号"而非延迟 | 同 VRAM 下最优分配 | 最高 1.95× vs vLLM 静态 offload | **vLLM 插件（drop-in）** |

---

## 6. 证据清单

| # | Claim | Source | URL | Date | Excerpt（摘录） | Confidence |
|---|---|---|---|---|---|---|
| 1 | EdgeMoE 端侧分层存储+预加载，1.5–2.5× 加速、内存省 1.05–1.18× | arXiv 2308.14352 + SLM Survey | https://arxiv.org/abs/2308.14352 ; https://arxiv.org/html/2409.15790 | 2023-08 / 2025-02 | "expert preloading that predicts the activated experts ahead of time and preloads it with the compute-I/O pipeline"；"reduces memory footprint by 1.05x to 1.18x…1.5x to 2.5x faster inference on Jetson TX2 and Raspberry Pi 4B" | 高 |
| 2 | EdgeMoE 内存省 2.6–3.2× vs 全驻留 | OpenReview camera-ready | https://openreview.net/pdf?id=DDJeREha18 | 2024/25 | "achieving memory savings ranging from 2.6× to 3.2× compared to IO-FREE" | 高 |
| 3 | Mixtral-offloading：LRU+投机加载+2bit 专家量化，86GB→17.5GB | arXiv 2312.17238 | https://arxiv.org/html/2312.17238v1 | 2023-12 | "keep kk least recently used experts as a type of LRU cache…speculative expert loading fetches 1−2 most likely experts" | 高 |
| 4 | MoE-Infinity 2–20× 延迟提升、GPU 成本省 8×；单请求复用倾斜 | arXiv 2401.14361 + alphaxiv 摘要 | https://arxiv.org/pdf/2401.14361v2 ; https://www.alphaxiv.org/abs/2401.14361 | 2024-01 / 2025-03 | "2-20X improvement in latency performance…saving GPU costs by up to 8X"；"for roughly 100-expert models, fewer than 5% of experts are repeatedly activated per request. For Mixtral, 25%" | 高 |
| 5 | MoE-Infinity 仓库工程化（OpenAI 兼容、连续批处理、paged KV） | GitHub | https://github.com/efficientmoe/moe-infinity | 2026 访问 | "OpenAI-compatible serving engine with continuous batching, paged KV cache…activation-aware cache keeps hot experts resident on the GPU" | 高 |
| 6 | Pre-gated MoE：pre-gate 解耦选择与执行；内存 -4.2×、仅 +23% vs oracle | arXiv 2308.12066（ISCA 2024） | https://arxiv.org/pdf/2308.12066 | 2023-08/ISCA 2024 | "reduces peak GPU memory consumption by 4.2x vs. GPU-only…only adding 23% performance overhead than the oracular…solution" | 高 |
| 7 | ProMoE：学习预测器 84.7%，token-based 仅 58.3%，stride -5%；GoodPred 指标 | arXiv 2410.22134 | https://arxiv.org/html/2410.22134 | 2024-10 | "ProMoE learned predictor maintains high Accuracy…average accuracy of 84.7%"；"average accuracy of the token-based predictor is only 58.3%"；"GoodPred = Accuracy × FetchRate" | 高 |
| 8 | ProMoE early preemption：gate 完成即抢占预取队列 | 同上 | 同上 | 2024-10 | "all passive cache misses are transformed into proactive precise prefetching" | 高 |
| 9 | 相邻层输入余弦相似 91.7%（DS-2） | 同上 | 同上 | 2024-10 | "the cosine similarity between the consecutive layers' inputs is 91.7%" | 高 |
| 10 | Fate：免训练跨层预取 78.79%（decoding）/97.15%；浅层缓存后命中 99.08%；decode 最高 4.1× | arXiv 2502.12224 | https://arxiv.org/abs/2502.12224 ; https://arxiv.org/html/2502.12224v1 | 2025-02 | "achieves a prefetch accuracy of 97.15%…increases the expert hit rate to 99.08%"；"selecting Gate_in_i, achieving a prefetch accuracy of 78.79% without additional training" | 高 |
| 11 | 同层 pre-attention 预测 93–97.6%，超 FATE 15–19pt | arXiv 2511.10676 | https://arxiv.org/html/2511.10676v1 | 2025-11 | "achieve 93.03% accuracy on DeepSeek V2 Lite, 94.69% on Qwen3-30B, and 97.62% on Phi-mini-MoE, showing 15% improvement…over FATE" | 高 |
| 12 | DuoServe-MoE top-2 54–67%；SP-MoE 70–90% | 同上（引述） | 同上 | 2025-11 | "achieves 54-67% of top-2 accuracy and 90.3-95.5% hit-1 accuracy on Mixtral-8x7B and Mixtral-8x22B" | 中高（转引） |
| 13 | SiDA-MoE：hash top-3 命中 >99%，显存 -40–80%，吞吐 3.93× | MLSys 2024 论文 PDF | https://proceedings.mlsys.org/paper_files/paper/2024/file/698cfaf72a208aef2e78bcac55b74328-Paper-Conference.pdf | 2024 | "Top-3 Hash Hit Rate…up to over 99%"；"over 60% and 80% reduction on SST2 and MRPC for Switch-base-128/256"；"2.60x, 3.93x more throughput" | 高 |
| 14 | MoE-Lightning：T4 上 10.3× 吞吐，2–3× 更少 CPU 内存 | arXiv 2411.11217（ASPLOS 2025） | https://arxiv.org/abs/2411.11217 | 2024-11 | "up to 10.3x higher throughput…for Mixtral 8x7B on a single T4 GPU (16GB)…reach the throughput upper bound with 2-3x less CPU memory" | 高 |
| 15 | HybriMoE prefill 1.33×/decode 1.70× | arXiv 2504.05897 | http://www.arxiv.org/abs/2504.05897 | 2025-04 | "average speedup of 1.33× in the prefill stage and 1.70× in the decode stage" | 高 |
| 16 | SwapMoE 14.2→4.7 GiB、延迟 -50% | ACL 2024 | https://aclanthology.org/2024.acl-long.363/ | 2024 | "reduce the memory consumption from 14.2 GiB to 4.7 GiB, together with 50% latency reduction and a slight Rouge-2 score drop of 0.041" | 高 |
| 17 | Fiddler 单 batch 8.2×/10.1× | arXiv 2402.07033 | https://arxiv.org/abs/2402.07033 | 2024-02 | "achieves 8.2 times and 10.1 times speedup on single-batch inference latency" | 高 |
| 18 | WiSP：低并发下缓存>预测；1.95× vs vLLM 静态 offload | arXiv 2606.21868 | https://arxiv.org/pdf/2606.21868 | 2026 | "in single-stream, memory-bound decode the useful lever is the caching policy, not routing prediction: the routing signal is worth more as a memory signal…than as a latency one" | 高 |
| 19 | NPUMoE：ANE 上 MoE prefill 卸载，延迟 -1.32–5.55×、能效 1.81–7.37× | arXiv 2604.18788 | https://www.emergentmind.com/papers/2604.18788 | 2026-04 | "reducing latency by 1.32x-5.55x, improving energy efficiency by 1.81x-7.37x" | 高 |
| 20 | accel 上游门槛：GEM/BO 必需、建议 TTM/drm_sched | linux-arm-kernel 邮件列表 | https://lists.infradead.org/pipermail/linux-arm-kernel/2024-April/917089.html | 2024-04 | "the minimal requirement is to use GEM/BOs for memory management operations"；"look at using ttm as the memory manager instead of re-implementing your own" | 高 |
| 21 | ivpu：内建 MMU-600 隔离用户负载 | 内核 commit | https://git.zx2c4.com/linux-rng/commit/?id=35b137630f08d913fc2e33df33ccc2570dff3f7d | 2023-01 | "Memory Management Unit (based on ARM MMU-600) - translates VPU to host DMA addresses, isolates user workloads" | 高 |
| 22 | DMEM cgroup 进 Linux 6.14；TTM 驱动可轻松接入 | Phoronix + kernelnewbies | https://www.phoronix.com/news/DMEM-cgroup-vRAM-Control ; https://kernelnewbies.org/Linux_6.14 | 2025-01 / 2025-06 | "Both GPU and driver-allocated CPU memory will be accounted to the correct cgroup, and eviction would be made cgroup aware" | 高 |
| 23 | NVIDIA MPS v3 默认用 dmem 后端 | NVIDIA 官方文档 | https://docs.nvidia.com/deploy/mps/latest/mpsv3-memory-partitioning.html | 2026 访问 | "dmem: used when the kernel (6.14 or newer) has the DMEM cgroup controller present. The kernel dmem controller enforces the hard and soft limits natively" | 高 |
| 24 | dma-buf memcg 记账仍 RFC（2026-10 v2），单一属主/fd 传递两缺陷 | lore/lkml + Linaro-mm-sig | https://lore.landau.one/lkml/?t=20261021165104 ; https://lists.linaro.org/archives/list/linaro-mm-sig@lists.linaro.org/thread/GJX5JSRHHCUBZOBGPN74VPW2YNTBPZU3/ ; https://kernsec.org/pipermail/linux-security-module-archive/2026-May/057331.html | 2026-05/2026-10 | "[PATCH RFC v2 0/8] memcg: dma-buf cgroup accounting and charge transfer"；"Single-owner model: a dma-buf carries one memcg charge regardless of how many processes share it"；"such single driver island approach have the tendency to break" | 高 |
| 25 | NNAPI 于 Android 15 deprecated；NN HAL 保留 | Android 官方文档（经多方转引核实） | https://github.com/android/skills/blob/main/device-ai/litert/litert-runtime/references/migration.md ; https://discuss.ai.google.dev/t/how-to-deploy-aicore-gemini-nano-on-pixel-other-devices/93284 | 2024/2025-07 | "NNAPI is deprecated from Android 15, and the CompiledModel API has no NNAPI accelerator"；"the Neural Networks Hardware Abstraction Layer (HAL) interface continues to be supported" | 高 |
| 26 | NNAPI 内存模型：ashmem/mmap/AHardwareBuffer + memory domain | Android 官方文档 | https://source.android.google.cn/docs/core/interaction/neural-networks/ahardwarebuffer ; GeeksforGeeks 整理 | 2022-09/2023 | "NNAPI supports memory domains that offer allocator interfaces for driver-managed buffers on devices running Android 11 or higher" | 高 |
| 27 | 2026 实测旗舰机消费 App 无 NPU 可用；Android 17 引入 NpuManager | Beebom 实测 + androidperformance wiki | https://gadgets.beebom.com/stories/i-tested-on-device-ai-on-android-and-iphone-results-not-even-close ; http://wiki.androidperformance.com/part1-fundamentals/ch05-cpu-power/05-ondevice-ai-runtime-npu.html | 2026-04 / 2026 | "not a single Android chip in our test used the NPU or TPU…the problem lies with the software"；"Android 17 / API 37 加入 FEATURE_NEURAL_PROCESSING_UNIT…AOSP 增加 NpuManager 与 NPU 调度 AIDL" | 中（媒体+社区 wiki，线索级） |
| 28 | QNN 仅接受 dmabuf 形式共享内存 | arXiv 2610.16244 + Qualcomm 官方文档 | https://arxiv.org/html/2610.16244v1 ; https://docs.qualcomm.com/nav/home/lpai_backend_memory_allocations.html | 2026-09 / 持续 | "The runtimes share memory only through DMA-BUF descriptors from AHardwareBuffer or the Hexagon heap…QNN accepts memory only in this form" | 高 |
| 29 | NeuMMU：NPU 翻译突发使 IOMMU 平均 95% 开销，NeuMMU 0.06% | arXiv 1911.06859 | https://ar5iv.labs.arxiv.org/html/1911.06859 | 2019（奠基） | "a naive IOMMU address translation incurs significant performance overhead…average 95%…NeuMMU…average 0.06% performance loss" | 高 |
| 30 | vNPU：硬件辅助多租户 NPU 虚拟化 | HotInfra 2023 | https://hotinfra23.github.io/papers/hotinfra23-paper15.pdf | 2023 | "suffers from either low resource utilization or poor isolation between multi-tenant application services due to the lack of system virtualization support" | 高 |
| 31 | sNPU：集成 NPU TEE，ID-based scratchpad 隔离 | ISCA 2024（经综述与社区解读核实） | https://blog.csdn.net/qq_41691212/article/details/142109334 ; https://dl.acm.org/doi/10.1145/3779307 | 2024 | "sNPU relies on the host CPU TEE as its RoT…the NPU Isolator dynamically partitions on-chip resources between secure and non-secure tasks" | 中高 |
| 32 | NXT：多租户 TEE-NPU，利用率 3.49×、开销 6.38% | Scilit 收录 | https://www.scilit.com/scholars/3592815 | 2025/26 | "improves overall utilization by up to 3.49× and ANTT by up to 7.24×, with only 6.38% average overhead for scheduling and isolation" | 中高 |
| 33 | 多租户 NPU 计时侧信道可提取权重（CVE-2026-1104 分析） | techbytes 分析 | https://techbytes.app/posts/cve-2026-1104-npu-side-channel-multi-tenant-exploit/ | 2026 | "accelerators inherit the same multi-tenant side-channel lessons CPUs learned years earlier…turn shared NPU timing into a weight-extraction channel" | 低（媒体/厂商线索，未见对应学术原文） |
| 34 | vChunk 租户间翻译干扰 <1%（vs MIG 最高 40%） | emergentmind 主题综述 | https://www.emergentmind.com/topics/npu-memory-virtualization | 2026-07 | "vChunk further ensures that each tenant's DMA accesses are isolated…<1% inter-tenant slowdown due to translation interference. In contrast, static partitioning (MIG)…up to 40% slowdown" | 中（二手综述） |

---

### 引用

[^0^]: ST-MoE, arXiv 2606.15453, 2026-06. https://arxiv.org/html/2606.15453v1
[^0b^]: Small Language Models Survey（EdgeMoE 数据转引）, arXiv 2409.15790, 2025-02. https://arxiv.org/html/2409.15790
[^1^]: Fate, arXiv 2502.12224, 2025-02. https://arxiv.org/html/2502.12224v1
[^2^]: Pre-gated MoE（ISCA 2024）引证页, 2026-06. https://arxiv.org/html/2606.15453v1
[^3^]: Pre-gated MoE 原文, arXiv 2308.12066. https://arxiv.org/pdf/2308.12066
[^5^]: MoE-Infinity, arXiv 2401.14361, 2024-01. https://arxiv.org/pdf/2401.14361v2
[^6^]: Fast Inference of MoE with Offloading, arXiv 2312.17238, 2023-12. https://arxiv.org/html/2312.17238v1
[^7^]: Fate abstract, 2025-02. https://arxiv.org/abs/2502.12224
[^8^]: EdgeMoE, arXiv 2308.14352, 2023-08. https://arxiv.org/abs/2308.14352
[^8b^]: HybriMoE, arXiv 2504.05897, 2025-04. http://www.arxiv.org/abs/2504.05897
[^8e^]: vLLM Expert Parallel Deployment 文档, 2026-10 访问. https://docs.vllm.ai/en/latest/serving/expert_parallel_deployment/
[^9^]: SwapMoE, ACL 2024. https://aclanthology.org/2024.acl-long.363/
[^11^]: ProMoE, arXiv 2410.22134, 2024-10. https://arxiv.org/html/2410.22134
[^13^]: MoE-Infinity GitHub. https://github.com/efficientmoe/moe-infinity
[^14^]: Mixtral-offloading mirror 描述, SourceForge. https://sourceforge.net/projects/mixtral-offloading.mirror/
[^15^]: MNN-AECS 论文（EdgeMoE 团队）, 2025-05. https://www.researchgate.net/publication/393022738
[^15b^]: SiDA-MoE, MLSys 2024. https://proceedings.mlsys.org/paper_files/paper/2024/file/698cfaf72a208aef2e78bcac55b74328-Paper-Conference.pdf
[^16^]: Analytics Vidhya 教程（Mixtral-offloading 量化数据）, 2025-05. https://www.analyticsvidhya.com/blog/2024/01/how-to-run-mixtral-8x7b-moe-on-colab-for-free/
[^18^]: EdgeMoE camera-ready, OpenReview. https://openreview.net/pdf?id=DDJeREha18
[^19^]: MoE-Infinity（personal machines 版）, OpenReview. https://openreview.net/pdf?id=BL7WMLJKZM
[^20^]: mixtral-offloading ExpertCache, DeepWiki, 2025-04. https://deepwiki.com/dvmazur/mixtral-offloading/4.3-expertcache-and-offloading
[^21^]: MoE-Infinity 分析, alphaxiv, 2025-03. https://www.alphaxiv.org/abs/2401.14361
[^23^]: Fiddler, arXiv 2402.07033, 2024-02. https://arxiv.org/abs/2402.07033
[^23b^]: mixtral-offloading 技术解析（LRU 命中率 70–85%，第三方）, 2026-05. https://starlog.is/articles/llm-engineering/dvmazur-mixtral-offloading/
[^24^]: MoE-Lightning, arXiv 2411.11217, 2024-11（ASPLOS 2025）. https://arxiv.org/abs/2411.11217
[^25^]: Pre-attention Expert Prediction, arXiv 2511.10676, 2025-11. https://arxiv.org/html/2511.10676v1
[^26^]: DALI, arXiv 2602.03495, 2026-02. https://arxiv.org/html/2602.03495v1
[^27^]: NPUMoE, arXiv 2604.18788, 2026-04. https://www.emergentmind.com/papers/2604.18788
[^28^]: WiSP/MV-WSA, arXiv 2606.21868, 2026. https://arxiv.org/pdf/2606.21868
[^29^]: ArmChina NPU 上游化讨论（Oded Gabbay）, linux-arm-kernel, 2024-04. https://lists.infradead.org/pipermail/linux-arm-kernel/2024-April/917089.html
[^30^]: Linux 6.18 DRM/accel 报道, Phoronix, 2025-10. https://www.phoronix.com/linux/Linux+Kernel/7
[^31^]: Linux 6.14 amdxdna 报道, 2025-03. https://en.ubunlog.com/Linux-6-arrives-a-bit-late-with-an-operational-NTSync-driver-and-support-for-the-AMD-Ryzen-AI-accelerator./
[^32^]: accel/ivpu 初始 commit, 2023-01. https://git.zx2c4.com/linux-rng/commit/?id=35b137630f08d913fc2e33df33ccc2570dff3f7d
[^33^]: DMEM cgroup 报道, Phoronix, 2025-01. https://www.phoronix.com/news/DMEM-cgroup-vRAM-Control
[^34^]: Linux 6.14 特性（kernelnewbies）, 2025-06. https://kernelnewbies.org/Linux_6.14
[^35^]: NVIDIA MPS v3 Memory Partitioning 文档. https://docs.nvidia.com/deploy/mps/latest/mpsv3-memory-partitioning.html
[^36^]: dma-buf memcg RFC（pid_fd 路径）, Linaro-mm-sig, 2026-05. https://lists.linaro.org/archives/list/linaro-mm-sig@lists.linaro.org/thread/GJX5JSRHHCUBZOBGPN74VPW2YNTBPZU3/
[^37^]: dma-heap 记账补丁与 Christian König 评论, 2026-05. https://kernsec.org/pipermail/linux-security-module-archive/2026-May/057331.html
[^38^]: memcg dma-buf RFC v2（8 补丁）, lkml, 2026-10. https://lore.landau.one/lkml/?t=20261021165104
[^39^]: GPU cgroup 控制器 RFC, dri-devel, 2022-01. https://lists.freedesktop.org/archives/dri-devel/2022-January/337403.html
[^40^]: NNAPI AHardwareBuffer 官方文档, 2022-09. https://source.android.google.cn/docs/core/interaction/neural-networks/ahardwarebuffer
[^40b^]: NNAPI deprecation 原文转引, 2025-03. https://meetonfriday.com/posts/666bbf67/
[^41^]: Google AI 论坛：NN HAL 保留/AICore 内部使用, 2025-07. https://discuss.ai.google.dev/t/how-to-deploy-aicore-gemini-nano-on-pixel-other-devices/93284
[^42^]: NNAPI memory pools/memory domain 整理, 2023-02. https://www.geeksforgeeks.org/android/memory-pools-in-android-11/
[^43^]: MediaTek NeuroPilot NNAPI 内存类型支持, 2025-06. https://bbs.songma.com/123469.html
[^44^]: MediaTek NP9 移除 NNAPI, 2025-06. https://genio-community.mediatek.com/t/are-there-any-official-android-examples-executing-tflite-models-using-nnapi-for-genio/464
[^45^]: LiteRT 迁移文档（android/skills）. https://github.com/android/skills/blob/main/device-ai/litert/litert-runtime/references/migration.md
[^46^]: 旗舰机 NPU 不可用实测, Beebom, 2026-04. https://gadgets.beebom.com/stories/i-tested-on-device-ai-on-android-and-iphone-results-not-even-close
[^47^]: Android on-device AI 2026 综述, 2026-10. https://www.forasoft.com/blog/article/neural-networks-on-android-369
[^48^]: Android 17 NPU 特性/NpuManager, androidperformance wiki. http://wiki.androidperformance.com/part1-fundamentals/ch05-cpu-power/05-ondevice-ai-runtime-npu.html
[^49^]: QNN LPAI Memory Management, Qualcomm 官方文档. https://docs.qualcomm.com/nav/home/lpai_backend_memory_allocations.html
[^50^]: HeteroVDiff（Snapdragon 8 Elite 内存共享事实）, arXiv 2610.16244, 2026-09. https://arxiv.org/html/2610.16244v1
[^51^]: Huawei CANN 架构（CloudMatrix384 serving）, arXiv 2506.12708, 2025-05. https://arxiv.org/html/2506.12708v1
[^52^]: 华为云 NPU 整卡分配文档, 2026-08. https://support.huaweicloud.com/eu/usermanual-cce/cce_10_0346.html
[^53^]: NeuMMU, arXiv 1911.06859, 2019. https://ar5iv.labs.arxiv.org/html/1911.06859
[^54^]: vNPU, HotInfra 2023. https://hotinfra23.github.io/papers/hotinfra23-paper15.pdf
[^55^]: sNPU（ISCA 2024）解读, 2024-09. https://blog.csdn.net/qq_41691212/article/details/142109334
[^56^]: NXT TEE-NPU, Scilit. https://www.scilit.com/scholars/3592815
[^57^]: Heterogeneous Confidential Computing Survey, ACM, 2026-03. https://dl.acm.org/doi/10.1145/3779307
[^57b^]: ANE vs NNAPI 内存模型对比（IOSurface/固定 pin 上限）, 2026-08. https://mvpfactory.io/blog/prefix-caching-aware-scheduling-for-on-device-llm-batching-reusing-kv-cache
[^58^]: CVE-2026-1104 NPU 侧信道分析, 2026. https://techbytes.app/posts/cve-2026-1104-npu-side-channel-multi-tenant-exploit/
[^59^]: NPU Memory Virtualization 主题综述（vChunk 数据）, emergentmind, 2026-07. https://www.emergentmind.com/topics/npu-memory-virtualization

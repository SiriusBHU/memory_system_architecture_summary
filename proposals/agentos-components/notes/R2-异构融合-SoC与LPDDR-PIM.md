# R2 SoC 内异构协同与 LPDDR-PIM

> 日期：2026-11-09。本地材料已读：lpddr-pim-architecture-CN、A16g、A15 §3.4、lpddr6-standard-evolution-CN、C1b。本文只补缺口。网络预算实际使用：WebFetch 7 次（JEDEC 官网返回 403，未取得原文）、WebSearch 4 次。
> 等级沿用：官方 / 论文同行评审 / 预印本 / 厂商自报 / 二手 / 估算。

## 1. 结论摘要

1. 三星在 Hot Chips 2026（2026-08）首次公开 LPDDR5X-PIM 的移动端实测数据：Llama 3.1 8B、320 token 上下文、INT4，输出 27.0 → 81.3 token/秒（3.01 倍），内部带宽 614 GB/s 对 LPDDR5X-9600 峰值 76.8 GB/s（约 8 倍）（厂商自报，经二手媒体转述，未见原始幻灯片）。
2. 该数据的测试条件对 PIM 有利（短上下文、统一 INT4），长上下文和混合精度下收益会下降（二手媒体判断，待核实）；对我们 T3 的 23–32K 上下文，这一数字不能直接套用。
3. JEDEC LPDDR6-PIM 标准仍未发布：2026-04-24 的报道称「接近完成」，2026-08 的韩媒报道仍称「接近完成」，截至 2026-11-09 未查到正式发布（二手，待核实）；原先本地材料中的"2026-04 预告"口径一致，但半年过去状态未变。
4. 首个商用 PIM 载体不是手机，而是三星 4nm AI PC 芯片 GAIA（已向联想、惠普送样，量产「最早 2027」，均为媒体转述，且 GAIA 是否搭载 LPDDR5X-PIM 报道称「预期」，未确认）。手机 SoC 厂商（高通、联发科）公开表态：本轮检索未查到，待核实。
5. 软件是当前最大缺口：PIM 模式下关闭缓存、预取与乱序执行，多任务复杂；llama.cpp、vLLM 均不支持 PIM（二手）。PIM-SHERPA 指出 prefill 要缓存权重而 decode 要不可缓存区域，并给出软件方案节省约 47.8–49.7% 内存容量（预印本，仿真平台）。
6. SoC 内异构：HeteroInfer（HeteroLLM）相对纯 GPU 或纯 NPU 引擎端到端 1.34–6.02 倍（预印本）；但 2026 官方数据显示手机 GPU prefill 已达 3808 token/秒（C1b 引 Google 模型卡），NPU 的价值转为能耗与让出 GPU，PIM 与 NPU 协同的收益要对比最新 GPU 基线。
7. 对我们的 52GB/s decode 读带宽负载：它占 LPDDR5X 理论峰值 77GB/s 的约 68%，PIM 把 GEMV 放到 bank 内后，外部总线可让给 NPU/GPU 的 prefill 与其他应用，这是 PIM 对 Agent OS 的系统层价值，而不只是单流提速。
8. 注意力与 MoE 上 PIM 的工作几乎全是数据中心（Duplex、Sieve、CXL-NDP），端侧 LPDDR-PIM 上跑 MoE 专家或 KV 注意力的公开工作本轮未检到（待核实）。

## 2. 证据表

| 指标 | 数值 | 条件 | 来源 | 等级 |
|---|---|---|---|---|
| LPDDR5X-PIM decode 吞吐 | 27.0 → 81.3 tok/s（3.01 倍）；任务耗时 12.3 s → 5.4 s（2.28 倍） | Llama 3.1 8B、320 token 上下文、INT4，Samsung 初步测试，对比常规 LPDDR5X | [1][2] | 厂商自报（二手转述） |
| PIM 内部带宽 | 614 GB/s（16 个并行 PIM 单元），对比 LPDDR5X-9600 峰值 76.8 GB/s | 三星 Hot Chips 2026 | [2] | 厂商自报（二手） |
| 此前三星仿真 | 矩阵计算性能最高 6.2 倍 | 仿真 | [1] | 厂商自报（二手） |
| Address Align Mode (AAM) | 指令的源寄存器序号由访问的列地址推出，使 PIM 能配合现有 DRAM 控制器 | LPDDR5X-PIM | [1][2] | 厂商自报（二手） |
| PIM 模式限制 | 关闭缓存、预取、乱序执行；单 bank / 多 bank（PIM）两种模式切换 | 同上 | [2] | 二手 |
| 软件支持 | llama.cpp、vLLM 均不支持 PIM | 2026-08 | [2] | 二手 |
| 商用时间 | GAIA（三星 System LSI，4nm，AI PC）送样联想、惠普；量产「最早 2027」 | 是否含 LPDDR5X-PIM 为「预期」 | [1] | 二手 |
| JEDEC LPDDR6-PIM | 「接近完成」，无正式发布；SOCAMM2、LPDDR6 x12/x6 子通道增强同期推进 | 2026-04-24、2026-08 报道 | [1][3] | 二手（JEDEC 官网 403，未核对原文） |
| 三星/SK 海力士标准化合作 | 2024-12 起共同推进 LPDDR6-PIM 标准化 | | [4] | 二手 |
| SK 海力士 | 1c LPDDR6 开发认证完成，2026 下半年出货；路线图含第二代 CXL LPDDR6-PIM；CES 2026 展示 AiMX（GDDR6-AiM） | 非移动 PIM 产品 | [4] | 二手 |
| CD-PIM | 单 batch 对纯 GPU 平均 11.42 倍，对现有最优 PIM 4.25 倍；低 batch 交错模式再 1.12 倍；DATE 2026 | 每 bank 拆 4 个伪 bank；模型名与是否硅验证摘要未给，待核实 | [5] | 预印本（拟发 DATE 2026） |
| PIM-SHERPA | 软件方案节省 47.8–49.7% 内存容量，性能接近理论最大；含 DDB 与 OWR 两种做法 | Llama 3.2，PIM 仿真基线，设备未给 | [6] | 预印本 |
| LP-Spec | 对 NPU 基线 13.21 倍性能、7.56 倍能效（本地材料已有） | 仿真/架构研究 | 本地 insight/N+2 | 论文（ISCA 2025，据本地材料，待核实会议） |
| HeteroInfer（HeteroLLM） | 对纯 GPU/纯 NPU 引擎端到端 1.34–6.02 倍；GPU-NPU 利用统一内存做快速同步，对其他应用干扰可忽略 | 摘要未给设备与模型；v2 2025-10 | [7] | 预印本 |
| Agent.xpu | Intel Core Ultra SoC、Llama-3.2-3B：reactive 任务延迟降 4.6 倍，proactive 吞吐 1.6–6.8 倍（对 llama.cpp） | prefill 在 NPU/iGPU 间交替，decode 常驻 iGPU 连续批处理；NPU-iGPU 带宽感知调度 | [8] | 预印本（数字来自二手摘要，待核对原文） |
| 带宽竞争（Agent.xpu 的核心观察） | NPU 与 iGPU 争用同一内存带宽，需要 bandwidth-aware dispatch | 同上 | [8] | 预印本 |
| 手机上 prefill | GPU 3808 tok/s、TTFT 0.3 s（S26 Ultra） | 本地 C1b 引 Google 模型卡 | C1b | 官方 |
| Duplex | MoE + GQA 注意力在 xPU 与逻辑层 PIM 协同，最高 2.67 倍吞吐、能耗降 42.0% | 数据中心 GPU 系统 | [9] | 预印本 |
| Sieve | 动态专家感知 PIM，针对 MoE 负载不均 | 数据中心 | [10] | 预印本（2026-05），数值未取，待核实 |
| CXL-NDP MoE | 冷专家在近数据处理侧计算，把参数搬运转为激活搬运 | CXL，数据中心 | [11] | 预印本（2025-12），数值待核实 |

## 3. 对关键技术的建议

### 对应的负载与瓶颈
- decode 单流约 52 token/秒 × 约 1GB 活跃权重 ≈ 52GB/s，已占 LPDDR5X 理论峰值 77GB/s 的约 68%（估算）；实际可持续带宽更低（本地材料引 Fraunhofer：最差可比标称低 50%，二手）。此时 decode 与 prefill、UI、其他应用抢同一条总线，Agent 后台推理会拖累前台。
- 长程任务 24–32K 上下文的 KV 约 0.8–1.07GiB，每 token 的 KV 读取在 decode 访存中占比约 0.8/(1+0.8)（估算，24K 时 KV 与活跃权重相近），PIM 若只加速权重 GEMV 而不覆盖 KV 注意力，则收益被稀释。Samsung 的 320 token 测试恰好看不到这一点。
- SoC 内：NPU、GPU 共享同一 LPDDR 带宽，协同的上限由带宽而非算力决定（Agent.xpu 观察）；prefill 在手机 GPU 上已够快，NPU 的剩余价值是能耗与让出 GPU。

### 问题与挑战
1. 模式切换与一致性：PIM 模式关闭缓存与预取，PIM 与普通访存不能同时进行（本地 A16g），前台应用访存会被迫等待或被拒绝。
2. 数据放置与容量：PIM bank 与普通容量互相占用；prefill 要缓存友好的布局，decode 要 PIM 友好的不可缓存布局（PIM-SHERPA），两份权重拷贝会吃掉容量，对 12GB 机型、Agent 侧约 4GB 的预算尤其敏感。
3. 编程模型缺失：JEDEC 标准未定、各厂商指令集私有，llama.cpp 等无支持；上层只能面向厂商 SDK 适配。
4. 收益口径窄：公开数据均为短上下文、INT4、稠密 8B；对 KV 密集、MoE 专家换入、投机解码（GEMV 变 GEMM）场景的收益没有端侧实测。

### 量化目标建议值
| 指标 | 建议值 | 依据 |
|---|---|---|
| 3B-4bit decode 单流吞吐（PIM 路径） | 不低于 100 token/秒，外部总线占用降到 <10GB/s | 三星 3.01 倍乘以基线 52 token/秒约 156（上限，估算）；保守取 2 倍 |
| 24K 上下文下 PIM 收益保持率 | ≥ 基线短上下文收益的 60% | 估算，需 KV 注意力也进 PIM 才可能达到，待实测 |
| PIM 与前台访存切换开销 | 单次切换 <100 µs，前台访存最大等待 <1 ms | 估算，无公开数据，待核实 |
| 为 PIM 双布局付出的额外容量 | <权重的 10%（PIM-SHERPA 约 48% 的节省为参照） | PIM-SHERPA 预印本 |
| NPU+GPU 协同端到端收益（相对最优单一引擎，同设备、稳态） | ≥1.3 倍，含能耗 | HeteroInfer 下限 1.34 倍 |

### 模块级方案
1. PIM 作为带属性的内存区域：在内存管理中新增「PIM-capable 区」，分配器区分 PIM 区与普通区（承接 A16g），权重一次布局成 PIM 友好格式，由运行时负责 prefill 阶段的在线重排（对应 PIM-SHERPA 的 DDB/OWR）。
2. 统一加速器路由：把 CPU/GPU/NPU/PIM 视为同一套「算子-位置」路由表，按算术强度分派：prefill 与 GEMM 走 NPU/GPU，GEMV 与 decode 走 PIM；与 C1b 的路由适配器合并，不另起一层。
3. 带宽仲裁：在内存控制器侧或 OS 侧引入带宽配额，NPU、GPU、PIM 与前台应用共享，借鉴 Agent.xpu 的 bandwidth-aware dispatch；后台 Agent 推理（proactive）作为低优先级回填。
4. 分阶段落地：2027 年先在 SoC 内做 NPU+GPU 协同与带宽仲裁（无需新硬件），PIM 作为自研芯片规划的硬件抓手，先用仿真/FPGA 评估，标准稳定后再接入。
5. 对应模型侧：为 PIM 友好选择 INT4 统一精度与 GEMV 主导的结构（与 R4 衔接）。

### 细节技术点
- 投机解码把 GEMV 变为 GEMM，PIM 优势随推测长度增加急剧下降（LP-Spec，本地材料）；PIM 路径与投机解码需要由运行时按推测长度选路。
- PIM 内 softmax、layer norm 仍需回到 SoC（本地材料），要设计 SoC 与 PIM 的流水线以隐藏往返。
- Samsung AAM 让 PIM 适配现有内存控制器，可降低对 SoC 内存控制器的改动，是 SoC 厂商接入的关键点，需向自研芯片团队确认是否采用。
- 热约束：移动热包络下持续 PIM 计算可能降频（本地材料，无硅验证），稳态而不是峰值才是设计输入（C1b 引手机降频数据）。

## 4. 原型对比表素材

| 要素 | HeteroInfer | Agent.xpu | Samsung LPDDR5X-PIM | LP-Spec | CD-PIM | PIM-SHERPA |
|---|---|---|---|---|---|---|
| 端侧手机/移动 SoC 实测 | ◐（手机 SoC，设备未核实） | ○（PC 级 Intel SoC） | ◐（厂商自测，设备平台未披露） | ○ | ○ | ○ |
| NPU 与 GPU/PIM 协同 | ● | ● | ◐（面向 AI PC 芯片） | ● | ◐ | ○ |
| 零拷贝/统一内存同步 | ● | ◐ | ○ | ◐ | ○ | ○ |
| 带宽竞争处理 | ◐ | ● | ○ | ◐ | ○ | ○ |
| 数据放置/布局处理 | ○ | ○ | ◐（AAM） | ● | ◐ | ● |
| 模式切换与一致性 | ○ | ○ | ◐ | ◐ | ◐ | ◐ |
| 长上下文/KV 注意力 | ○ | ○ | ○（仅 320 token） | ◐ | ◐（KV 列/行映射） | ○ |
| MoE 专家 | ○ | ○ | ○ | ○ | ○ | ○ |
| 硅或量产验证 | ○ | ○ | ◐（原型） | ○ | ○ | ○ |
| Agent 多任务调度 | ○ | ● | ○ | ○ | ○ | ○ |

（● 达成、◐ 部分、○ 未涉及或未见公开证据；依据上表证据，若原文未核对则为待核实。）

## 5. 与其他模块的边界
- 归本模块（推理）：SoC 内 NPU/GPU/CPU/PIM 的算子分派、PIM 作为算力位置、带宽仲裁、PIM 友好的权重布局。
- 归内存管理：PIM-capable 区的分配与回收、DRAM 预算划分、zero-copy 映射与 IOMMU；KV 与专家缓存在 PIM 与普通 DRAM 之间的放置，边界约定：放置策略由内存管理给出，算子是否在 PIM 执行由推理路由决定。
- 归 R3：闪存侧 UFS-PIM；归 R4：模型结构对 GEMV/INT4 的亲和；归 R5：MoE 专家缓存与命中率（专家在 PIM 中计算属本模块与 R5 的接缝，目前无端侧证据）。

## 6. 待核实
1. JEDEC LPDDR6-PIM 是否已正式发布（官网 403，未读原文；委员会名称 JC-42.6 为本地材料说法）。
2. 三星 Hot Chips 2026 原始幻灯片：测试设备、是否含 KV、功耗与面积数据，以及 614GB/s 与 8 倍带宽的口径（Tom's Hardware 正文抓取被截断，只拿到标题）。
3. 手机 SoC 厂商（高通、联发科、苹果、华为海思）对 LPDDR-PIM 的公开表态：本轮未查到。
4. HeteroInfer 的设备、模型与 prefill/decode 分项数字；Agent.xpu 的原文数字；CD-PIM 的模型与是否硅验证；Sieve、CXL-NDP 数值。
5. AttAcc 等把注意力放 PIM 的原始论文本轮未检索，MoE 放 PIM 的端侧工作未发现。
6. LPDDR-PIM 对 3–7B decode 的收益在 24–32K 上下文下的实测。
7. GAIA 是否确实搭载 LPDDR5X-PIM，以及量产时间。

## 参考文献
1. TrendForce，Samsung's 4nm GAIA could mark first PIM commercialization in AI PCs，2026-08-26。https://www.trendforce.com/news/2026/08/26/news-samsungs-4nm-gaia-could-mark-first-pim-commercialization-in-ai-pcs-mass-production-as-early-as-2027/
2. Tom's Hardware，Hot Chips 2026: Samsung makes LPDDR5X smart ... 3.01x faster ... 8x the bandwidth，2026-08（正文由 WebSearch 摘要得到，页面抓取被截断）。https://www.tomshardware.com/pc-components/dram/hot-chips-2026-samsung-makes-lpddr5x-smart-with-logic-unit-in-memory-lpddr5x-pim-is-3-01x-faster-than-lpddr5x-in-ai-inference-with-8x-the-bandwidth
3. TrendForce，JEDEC previews LPDDR6 enhancements, develops SOCAMM2 standard，2026-04-24。https://www.trendforce.com/news/2026/04/24/news-jedec-previews-lpddr6-enhancements-develops-socamm2-standard-for-ai-memory/
4. 检索摘要：三星与 SK 海力士 LPDDR6-PIM 合作（TweakTown、eeNews Europe，2024-12）及 SK 海力士 1c LPDDR6、AiMX 信息（TrendForce 等）；具体页面未逐一抓取，待核实。https://www.eenewseurope.com/en/samsung-sk-hynix-partner-on-processing-in-memory
5. CD-PIM，arXiv 2601.12298，2026-01-18。https://arxiv.org/abs/2601.12298
6. PIM-SHERPA，arXiv 2603.09216，2026-03-10。https://arxiv.org/abs/2603.09216
7. Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference（HeteroInfer/HeteroLLM），arXiv 2501.14794，v1 2025-01、v2 2025-10。https://arxiv.org/abs/2501.14794
8. Agent.xpu，arXiv 2506.24045，2025-06-30。https://arxiv.org/abs/2506.24045
9. Duplex，arXiv 2409.01141，2024-09。https://arxiv.org/html/2409.01141v1
10. Sieve，arXiv 2605.11277，2026-05。https://arxiv.org/abs/2605.11277
11. CXL-NDP MoE 推理，arXiv 2512.04476，2025-12。https://arxiv.org/abs/2512.04476
12. JEDEC LPDDR6 PIM 预告新闻稿（本轮 403，未读）。https://www.jedec.org/news/pressreleases/jedec%C2%AE-previews-lpddr6-roadmap-expanding-lpddr-data-centers-and-processing-memory

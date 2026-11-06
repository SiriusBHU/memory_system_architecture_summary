# C4b 模型内存：KV、MoE、权重分页

> 子模块 C4b，调研日期 2026-11-05。对应 research-prompt.md 第 7 节 Q2、Q3、Q4、Q7；主责接缝 J1（成本侧）、J6（内存侧）；评审立场 MM-4、MM-5、MM-6、MM-7。
> 标注约定：证据等级 A–D、成熟度 L1–L4 见 prompt 第 3.2、3.3 节。`[n]` 对应 §8。「估算」为本文用公开参数自行推算；「待核实」为仅见二手来源或未能确认。
> 本库已有结论（M3 笔记、KV Cache 与主从换入换出调研）不重复，只引用其中经二次检索仍成立的数据，并标注「引自 M3」。

---

## §0 摘要

1. 判断：KV 管理在云侧已经形成「块化 + 共享 + 分层卸载」的事实标准（vLLM、SGLang、LMCache、Mooncake），但端侧只有块化与卸载各有少量学术原型，没有任何一条路线进入平台默认（L4 为零）。证据 [1][9][15]。
2. 判断：驱逐类（H2O、SnapKV 等）在多轮、前缀复用场景下系统性失效。SCBench 报告 StreamingLLM、SnapKV 在多轮后续问题上接近 0 分 [6]，KVzip 同向 [7]。这是 MM-4「KV 驱逐经济学」最强的反方证据：有损驱逐的收益只在单轮成立。
3. 判断：跨租户前缀共享的侧信道是已发表、已复现的真实攻击（PromptPeek，NDSS 2025 [3]；7 家 API 提供商审计 [4]）。端侧「多应用共享系统提示词 KV」必须按信任域分区，J2 的收益需要打折。
4. 判断：混合 / 线性注意力会显著降低 KV 的体积优先级，但不会消除 KV 管理，且产生新问题：循环状态不能做部分前缀命中，需要 Marconi 一类的新缓存策略 [8]。KV 的角色从「体积问题」转为「状态保存与恢复问题」。
5. 判断：MoE 专家换入在手机上已有实测（EStream [22]、Paging the Experts [23]），但均为预印本（L1），命中率对容量极敏感（M3 引自 [23]：512MiB LRU 命中 0%，576MiB 为 38.58%）。已量产的稀疏权重分层只有 Gemma 3n PLE [21]（L4 先例），不是 MoE。
6. 判断：闪存直读权重的瓶颈是 IOPS 而非带宽。UFS 4.0 厂商标称顺序读最高 4300MB/s [B 级]，但 4KB 随机读 PowerInfer-2 实测约 1GB/s 且随访问范围下降 [18]；Neuralink 以 IOPS 为主要瓶颈做神经元排布 [17]。每 GB 读取能耗未找到公开实测。
7. 判断：四种驱逐去向的成本在端侧呈明显层次：换出到闪存的恢复延迟估算比重算低一个数量级（估算，§3.7），上云传 KV 在常见上行带宽下不可行，只能「传文本、云侧重算」。去向集合不完备，应增加「原地降精度」与「直接丢弃」两项。
8. 判断：「驱逐即写入长期记忆」没有系统研究。AgentKVShift [27] 是「检索记忆单元的 KV 复用」，方向相反（记忆到 KV），不是 KV 到记忆。J1 是真空白，也意味着缺乏可借鉴的质量损失数据。
9. 判断：LoRA 热插拔在端侧只有 EdgeLoRA 一类服务器式原型（Jetson / 树莓派，L1–L2 [26]），手机上适配器与底座权重分页共存无公开数据；MM-6 中 LoRA 部分证据最弱。
10. 最大资料空白：手机上的 J/GB 读取能耗、KV 摘要的质量损失、手机端 KV 落闪存对 UFS 寿命的影响、端侧 MoE 实际出货状态的官方口径。

---

## §1 技术谱系表

### 1.1 KV cache 管理技术谱系（五路线，含端侧证据列）

表头按 prompt 第 3.6 节固定，另加「端侧证据」一列（第 7 节要求）。

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 | 端侧证据 |
|---|---|---|---|---|---|---|---|
| 块化 | PagedAttention / vLLM | UC Berkeley 等 | 2023，SOSP 2023（待核实） | KV 切块 + 块表，消除碎片 | L3 | 需改造：块表在 NPU 图编译下难动态；CPU / GPU 后端可直接用 | 端侧运行时多用预分配连续缓冲；llama.cpp 为 ring / 连续 KV（待核实）；无手机实测 |
| 块化 | vAttention [1] | Microsoft Research India | 2024-05，ASPLOS 2025 | 保持虚拟连续，借 OS 级按需映射物理页，免改 kernel | L2（并入 vLLM 栈的原型） | 需改造：依赖 CUDA 虚拟内存 API；手机上等价物是 mmap + 按需 fault 或 NPU 侧 IOMMU 映射，无公开实现 | 无。判断：思路与「内核做 KV 缺页」最契合 MM-4，但缺 NPU 侧机制 |
| 块化 | LLMS [M3 引自 23] | 移动端学术（待核实机构） | 2024-03，arXiv 2403.11805 | 16 token 分块压缩与换出，LCTRU 淘汰，降上下文切换延迟 | L1 | 直接面向手机 | 有（摘要级，二手，待核实） |
| 共享 | RadixAttention / SGLang | LMSYS | 2023–2024 | 基数树管理前缀复用 | L3 | 需改造：需要信任域分区（见 Q2.2） | 无手机实测 |
| 共享 | Automatic Prefix Caching / API 级 prompt caching | vLLM；各云 API | 2024– | 跨请求系统提示词复用 | L3–L4（云 API 默认） | 单设备单租户可直接迁移；跨应用共享受侧信道约束 | Apple、Gemini Nano 的跨应用前缀复用无公开资料（未找到公开资料） |
| 共享 | Marconi [8] | 论文，MLSys 2025（荣誉提名） | 2024-11 | 混合模型的前缀缓存：只能精确匹配，按「复用概率 × 节省算力 ÷ 占用」准入与淘汰 | L2 | 可直接迁移到 CPU / GPU 逻辑；换成混合模型后必需 | 无 |
| 压缩 | KIVI [16] | Rice 等 | 2024，ICML 2024 | K 按通道、V 按 token 的 2-bit 量化 | L2–L3（框架中常见 KV 量化选项） | 可直接迁移（量化 kernel 需 NPU 支持） | Apple 端侧模型 KV 8-bit（引自 M3）；2-bit 无手机实测 |
| 压缩 | 架构级：GQA、MLA、跨层共享、局部 / 全局交错 | 模型作者 | 2023–2026 | 在模型结构里缩 KV | L4（已出货模型） | 不可由 OS 控制 | Apple 2025 端侧模型第二块共享第一块 KV，KV 内存降 37.5%（A 级；引自 M3） |
| 驱逐 | H2O、StreamingLLM、SnapKV、PyramidKV | 多家 | 2023–2024 | 按注意力得分或窗口丢 KV | L2 | 可迁移，但多轮失效（Q2.3） | 无手机实测 |
| 驱逐 | KVzip [7] | 学术 | 2025-05 | 面向「不知下一个问题」的 query-agnostic 压缩 | L1 | 待评估 | 无 |
| 驱逐 | MemDecay [28] | 学术，arXiv 2607.10582 | 2026-07 | 按 orchestrator 给的区域标签（系统提示、计划等）设保留与衰减 | L1（仅见摘要，待核实） | 理论上适合 Agent；需要 OS / 框架提供区域标签 | 无 |
| 卸载 | CachedAttention [11] | NUS、上海交大、华为云 | 2024，USENIX ATC 2024 | 多轮对话 KV 分层存放，逐层预取，调度感知淘汰 | L2 | 需改造：服务器 HBM / DRAM / SSD 三层；手机只有 DRAM + UFS 两层 | 无 |
| 卸载 | Mooncake [15] | 月之暗面 / 清华 | FAST 2025（最佳论文） | KV 池化，Prefill / Decode 分离 | L3（生产于 Kimi） | 不可迁移：依赖 RDMA 集群；可借鉴「池化 + 调度」抽象 | 无 |
| 卸载 | LMCache / SGLang HiCache | LMCache 社区；LMSYS | 2025 | 多层 KV 存储与跨引擎共享 | L3 | 云侧；端侧需裁剪 | 无 |
| 卸载 | KVSwap [9] | Leeds | 2025-11，预印本 | 全量 KV 落盘，内存留紧凑元数据预测预载 | L1 | 直接面向嵌入式 / 移动端 | 有：32K 上下文同内存预算下较最强卸载基线吞吐最高 1.8 倍（NVMe）、4.1 倍（eMMC）。注意其测试介质是 NVMe 与 eMMC，不是 UFS |
| 卸载 | KVNAND [10] | 学术 | 2025-12，预印本 | 3D NAND 内计算，权重与 KV 全放闪存，免 DRAM | L1 | 不可迁移（需新硬件） | 仅作远景，非现有手机 |
| 卸载 | MNN-LLM [M3 引自 24] | 阿里 | 2025，arXiv 2506.10443 | KV 优先 DRAM，溢出到 Flash 并预取 | L2–L3（MNN 开源，待核实） | 直接面向手机 | 有，已在开源引擎内（待核实默认状态） |

### 1.2 MoE 专家管理 / 权重分页谱系（对比表见 §7.2）

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 闪存按需读神经元 | LLM in a flash [19] | Apple | 2023-12 | 窗口复用 + 行列捆绑，减少闪存读 | L1–L2（会议待核实） | 直接面向手机；依赖 ReLU 稀疏 |
| 异构 + IO 流水 | PowerInfer-2 [18] | 上海交大 IPADS | 2024-06 | 神经元簇 + XPU + IO 流水，OnePlus 12 上 47B 11.68 tokens/s | L2 | 直接面向手机；需稀疏化模型 |
| 闪存排布 | Neuralink（原名 Ripple）[17] | 清华等 | ASPLOS 2025 | 把共激活神经元在闪存中相邻存放，合并成大块读，缓解 IOPS | L1–L2 | 直接面向手机 |
| 激活稀疏 | TEAL [20] | 论文，ICLR 2025 | 2024-08 | 免训练幅值稀疏，40–50% 模型级稀疏，解码最高 1.53–1.8 倍 | L2 | 可迁移；GPU / CPU kernel 已有，NPU 无 |
| 层级嵌入分层 | Gemma 3n PLE [21] | Google | 2025 | PLE 可放闪存逐层注入，E2B 有效内存负载约 1.91B 参数 | L4（随 Gemma 3n 发布） | 已在手机；平台默认状态待核实 |
| MoE 预取 | Pre-gated MoE、AdapMoE、ProMoE、fMoE [24] | 多家 | 2023–2025 | 预测或预门控下一步专家，计算与迁移重叠 | L1–L2 | 多为 GPU；预测器需改造 |
| MoE 低精度替换 | HOBBIT、EdgeMoE | 多家 | 2023–2024 | 缓存缺失时用低位宽专家 | L1 | 面向边缘；需评估质量 |
| MoE CPU/GPU 混合 | KTransformers [25] | 清华 MADSys | SOSP 2025 | 专家驻 CPU 内存并在 CPU 计算，专家延迟（expert deferral）重叠 | L3（已并入 SGLang） | 不可迁移：需 500GB 级 DDR（引自博客，B 级）；手机无此规模 |
| 手机 MoE 换入 | EStream [22] | 上海交大（待核实） | 2026-09，预印本 | NPU 可寻址 arena，专家分组换入，Snapdragon 实测 | L1 | 直接面向手机 NPU |
| 手机 MoE 换入 | Paging the Experts [23] | 引自 M3，机构待核实 | 2026-09，预印本 | iPhone 上 Qwen3.6-35B-A3B 专家换入，LRU / 随机命中率 | L1 | 直接面向手机 |
| LoRA 多适配器 | EdgeLoRA [26] | 学术 | 2025-07，预印本 | 适配器缓存 + 预分配内存池 + 批量 LoRA | L1–L2 | 面向 Jetson / 树莓派；手机待验证 |

---

## §2 关键数据

| 指标 | 数值 | 条件（硬件 / 模型 / 负载） | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| vAttention 吞吐 | 解码吞吐最高 1.99 倍于 vLLM；端到端 1.22–1.29 倍于 FlashAttention / FlashInfer 的 PagedAttention 版（ASPLOS 版标 1.23 倍，两处略有出入） | A100 级 GPU，vLLM 栈 | [1] | 2024-05 / 2025 | A |
| CachedAttention | TTFT 最高降 87%，prefill 吞吐最高 7.8 倍，推理成本最高降 70% | 多轮对话，HBM / DRAM / SSD 分层 | [11] | 2024-07 | A |
| HCache | TTFT 较 KV 卸载最高降 1.93 倍，存储降 1.92–2.40 倍；较 token 重算最高 5.73 倍 | 服务器 GPU，隐状态存储 | [12] | 2025 | A |
| CacheGen | KV 体积缩 3.5–4.3 倍，加载与处理延迟降 3.2–3.7 倍 | 4 个模型、662 个上下文 | [13] | 2024-08 | A |
| Cake | 平均 TTFT 降 2.6 倍（v2） | 计算与 IO 双向并行加载 | [14] | 2024-10 | C（预印本，v1 与 v2 数字不同） |
| KVSwap | 32K 上下文同内存预算下吞吐最高 1.8 倍（NVMe）/ 4.1 倍（eMMC） | 嵌入式与 UMA 设备，未在摘要中给机型 | [9] | 2025-11 | C |
| KIVI | Llama-2-7B 峰值内存降 2.6 倍，吞吐 2.35–3.47 倍 | 引自 M3 | [16] | 2024 | A |
| SCBench 多轮 | StreamingLLM、SnapKV 多轮后续问题近 0 分 | 共享上下文多轮模式 | [6] | ICLR 2025 | A（会议论文，结论取自检索摘要，原文未精读） |
| Marconi | token 命中率最高 34.4 倍，TTFT 最多降 617ms | 混合模型（含 SSM 层） | [8] | MLSys 2025 | A |
| UFS 4.0 顺序读 | 最高 4300MB/s，顺序写 4000MB/s | 厂商标称 | [32] | 2023-06 | B |
| UFS 4KB 随机读 | 约 1GB/s（128MB 范围），512MB 范围降到 850MB/s 以下；大核约 1076MB/s、小核约 762MB/s；512KB 块可到 3.5GB/s | OnePlus 12，PowerInfer-2 实测 | [18] | 2024-06 | A |
| UFS 队列深度 | 手机存储命令队列通常只有 32 项，小块 IO 瓶颈在 IOPS | 引自 Neuralink | [17] | ASPLOS 2025 | A（论文陈述，非本文实测） |
| 闪存读取能耗 J/GB | 未找到公开实测 | — | — | — | — |
| PowerInfer-2 | 47B TurboSparse-Mixtral 11.68 tokens/s；对 llama.cpp 平均 24.6 倍 | OnePlus 12 24GB | [18]（引自 M3） | 2024-06 | A（预印本，会议待核实 → 记 C） |
| TEAL | 40% / 50% 模型级稀疏，解码 1.53 倍 / 1.8 倍 | Llama-2/3、Mistral，7B–70B，GPU | [20] | ICLR 2025 | A |
| Gemma 3n E2B | 标准执行超 5B 参数；PLE 缓存后有效内存负载约 1.91B | 官方文档 | [21] | 2025 | B |
| EStream | 预填充 TTFT 加速 2.25–27.57 倍，峰值物理内存降 1.19–12.29 倍，可扩展到 46.7B | 商用 Snapdragon 手机，3 个 7B–16B MoE，256–4096 token，18 种设置；相对每种设置下最快基线 | [22]（已核对摘要） | 2026-09-06 | C（预印本） |
| Paging the Experts | 512MiB LRU 命中 0.00%，512MiB 随机 18.80%，576MiB LRU 38.58%；进程峰值 1.87–2.73GiB；出现热降频 | iPhone，Qwen3.6-35B-A3B，固定路由回放 128 token | [23]（引自 M3，本轮未复核） | 2026-09-24 | C |
| fMoE | 延迟降 47%，专家命中率升 36% | GPU 服务；作者自测 | [24] | 2025-02 | C |
| AgentKVShift | 只刷新 10–30% 缓存即接近全量重算；预填充较无复用快 2–3.5 倍 | 4 个模型 3B–32B，A100 | [27] | 2026-05 | C |
| Apple 端侧模型 KV | 共享块使 KV 内存降 37.5%，KV 8-bit | Apple 2025 技术报告 | [M3 引自 22] | 2025 | B |

---

## §3 逐问题分析

### Q2 KV cache 管理的系统化程度

#### Q2.1 块化

现状：云侧块化已是默认。PagedAttention 消除碎片后，vAttention 提出相反思路：保持虚拟地址连续，借 CUDA 虚拟内存 API 把「虚拟分配」与「物理分配」分离，让未经改写的 attention kernel 也能动态分配 [1]。作者给出的收益是解码吞吐最高 1.99 倍、端到端 1.22–1.29 倍 [1]。

机制与分歧：两派的真正分歧不在性能，而在「谁负责映射」——PagedAttention 在用户态维护块表，vAttention 把映射下沉给 OS / 驱动。对 MM-4 来说后者更契合：它说明「KV 就是一块按需缺页的匿名内存」在服务器上成立。

端侧：我们没有找到 vAttention 在手机上的任何复现。移植的难点判断如下：
- GPU / CPU 后端：手机 GPU 驱动（Adreno、Mali）是否暴露等价的「虚拟预留 + 物理按需提交」接口，未找到公开资料。
- NPU 后端：主流 NPU 路径是 AOT 编译的 context binary，KV 缓冲在图编译时定形（判断，依据本库 C1a 方向，未在本模块独立核实），动态扩张困难，块化的收益最难兑现。

这说明什么：块化解决的是多请求并发下的碎片，而手机典型是单用户少会话。判断：块化对端侧的价值低于「分块换出」（LLMS、MNN-LLM 的用法 [M3 引自 23][24]），后者才是 MM-4 需要的粒度。

#### Q2.2 共享与侧信道（接缝 J2）

现状：前缀共享在云 API 已是默认计费特性。侧信道方面已有三层证据：
- PromptPeek（NDSS 2025）：在 SGLang、vLLM 等多租户引擎上，攻击者通过 TTFT 判断缓存命中，逐 token 重构他人 prompt [3]（A 级论文；机制取自摘要级检索与二手转述，原文未精读）。
- 「The Early Bird Catches the Leak」（arXiv 2409.20002）：把 KV 缓存与语义缓存都纳入分析，用延迟阈值判断命中，增量搜索恢复受害者 prompt，黑盒测试中 Claude、DeepSeek、Azure OpenAI 均显示暴露；提出的缓解是仅以不小于 k token 的粒度共享前缀 [2]（C 级预印本，会议待核实）。
- 「Auditing Prompt Caching in Language Model APIs」（arXiv 2502.07776）：统计审计发现多家 API 存在缓存和跨用户全局共享，并向提供商披露 [4]。第三方摘要称覆盖 7 家，本文未在原文核对该数字，记「待核实」。
- 防护综述：CacheSolidarity（arXiv 2603.10726，2026-03）按「全隔离、时序混淆、其他」归类防护，并提出只在存在可利用泄漏时才隔离前缀 [5]（C 级，仅见摘要）。

防护的代价：按租户分区能消除信号，但同时消除共享收益 [3 的转述]。这是显式的「隐私 vs 命中率」权衡。

对端侧的含义：
- 手机上的共享场景是「多个应用共享同一份系统服务的系统提示词 KV」。攻击者模型变为恶意应用，防御者是系统服务。
- 判断：J2 的结论应拆开。系统提示词 KV（内容由 OS 定义，对所有应用相同）共享无泄漏风险；含用户或应用私有内容的前缀不得跨应用共享。分区边界宜与沙箱 / 会话 ID 对齐，而不是自造一套。
- 未找到手机端前缀缓存侧信道的实测。端侧的计时噪声、NPU 调度抖动是否足以掩盖信号，没有数据。

这说明什么：前缀共享不是免费午餐。立场文本里若把「共享底座 + 共享 KV」写成默认，需补上信任域条件。

#### Q2.3 压缩与驱逐

压缩（量化、架构）：
- KIVI 类量化在框架中已成可选项 [16]；更重要的是架构级压缩，已出货模型把 KV 体积在出厂时就缩了：Apple 端侧模型 37.5% [M3 引自 22]，Qwen3.5-35B-A3B 只有 10/40 层为全注意力（引自 M3 [9]），Gemma 3 以 5:1 局部 / 全局交错、局部窗口 1024 [见 §8 Raschka 页，C 级]。
- 这些由模型作者决定，OS 只能适配。

驱逐的问题在于「多轮」。SCBench 的结论是 StreamingLLM、SnapKV、PyramidKV 一类 sub-O(n) 方法在多轮后续问题上表现很差，StreamingLLM 与 SnapKV 近乎 0 分；原因是重要 KV 因查询而异，只在第一次查询上表现好 [6]。KVzip 同样指出 SnapKV 复用首次查询压缩后的缓存时精度显著下降 [7]。2026 年的后续工作（RestoreKV、ReST-KV、「Trust the Mass」等）仍在试图做 query-agnostic 驱逐，但本文只见到标题与摘要片段，未核实其结论 [待核实]。

对 Agent 负载的含义：Agent 是典型的多轮 + 工具结果反复被引用，正是 SCBench 失效的场景。判断：对 MM-4，把「按重要性有损丢 KV」作为主驱逐手段风险很高；无损或可恢复的手段（换出、重算、量化）优先，有损丢弃只适合「已知不会再被引用的片段」，例如已完成工具调用的原始输出。MemDecay 的「按区域标签设衰减」[28] 正是这个方向，但仅见摘要。

这说明什么：驱逐路线的实验室收益在端侧 Agent 负载下被高估；MM-4 的「驱逐经济学」应以可恢复性为第一约束。

#### Q2.4 卸载

云侧：CachedAttention 分层存放并逐层预取，TTFT 最多降 87%、成本最多降 70% [11]；HCache 存隐状态而非 KV，存储降 1.92–2.40 倍，TTFT 较 KV 卸载最高降 1.93 倍 [12]；Mooncake 在生产中使 Kimi 在同 SLO 下多处理 75% 请求 [15]（B 级，项目自述）。三者都靠「IO 与计算重叠」。

端侧：
- KVSwap 是最直接的手机侧证据：全量 KV 落盘，内存只留元数据，预测预载 [9]。其收益因介质而异（NVMe 1.8 倍、eMMC 4.1 倍），说明介质越慢，预测预载越关键。UFS 4.x 介于两者之间，具体数字未知。
- MNN-LLM 已在开源引擎里实现 Flash 溢出（引自 M3 [24]）。
- KVNAND 需要新硬件 [10]，不构成近期选项。

写入寿命：UFS 有擦写寿命约束（prompt 第 3.4 节）。KV 换出是持续写，未找到任何论文量化手机端 KV 换出对闪存寿命的影响。我们给出估算：假设单会话每小时换出 1GB，则一天 8 小时约 8GB/天；对 256GB UFS、假设额定写入量数百 TBW（取值为假设，未核实机型数据），日写 8GB 约 3 年 2.9TB，占比很小。结论：仅在极端高频场景才需要关注，但这是估算，标 D。

这说明什么：卸载在端侧不是「有没有人做」而是「没有人量过能耗与寿命」。MM-4 的经济学公式中这两项目前只能留参数。

#### Q2.5 混合 / 线性注意力对 KV 优先级的冲击（反方）

事实：
- Qwen3-Next 为 3:1 结构，36 层线性注意力、12 层 softmax 注意力，循环层状态固定大小，softmax 层仍要 KV [见 §8 Raschka 页，C 级]。
- Qwen3.5-35B-A3B 每 token KV 仅 20KiB（引自 M3，估算）。
- 服务栈：vLLM 用混合 KV 管理器按层类型分组；LMCache 文档对 Gemma 3、gpt-oss 的前缀缓存有说明，对 Qwen3-Next 的支持英文与中文文档页互相矛盾，需以当前发布版为准 [31]（待核实）。

机制：混合模型把 KV 的「线性增长」换成「固定大小状态 + 少量全注意力层」。两个后果：
1. 体积下降，MM-4 的紧迫度降低（支持反方）。
2. 循环状态是就地更新的，只能精确匹配，不能做部分前缀命中；缓存了很多很少被复用的条目。Marconi 用「复用概率 × 节省算力 ÷ 占用」做准入与淘汰，报告 token 命中率最高 34.4 倍 [8]。这意味着「按块、按前缀的 KV 驱逐」假设不再普适。

判断：反方成立一半。KV 的体积问题被架构吃掉一部分，但「状态的保存、恢复与淘汰」问题变难而非变易，且 OS 面对的对象从「可切块的张量」变为「不可切分的状态快照」。MM-4 应把对象抽象从 KV 块改为「会话状态单元」，其尺寸、可切分性、重算成本由模型声明。

这说明什么：不要为稠密 GQA 的 KV 布局做过度设计；接口要对状态单元的元数据开放。

### Q3 MoE 专家管理

现状：云 / 桌面侧工作很多，端侧手机实测直到 2026-09 才出现。

效果数据：
- Pre-gated MoE（ISCA 2024）：相对 GPU-only 最优仅多 23% 延迟（引自 M3）。
- fMoE：延迟降 47%、命中率升 36% [24]，作者自测，GPU 服务场景。
- KTransformers（SOSP 2025）：专家驻 CPU 内存、算术强度感知的混合核、专家延迟使 CPU 专家计算与 GPU attention 重叠 [25]。需要大容量 DDR（500GB 级，博客口径）。
- EStream：Snapdragon 手机 NPU 上，专家池放 UFS，固定大小 NPU 可寻址 arena 分组换入，预填充 TTFT 加速 2.25–27.57 倍，峰值物理内存降 1.19–12.29 倍 [22]。注意它是「相对每种设置下最快基线」，且摘要只覆盖 prefill；摘要页未报告命中率。
- Paging the Experts：iPhone 上固定路由回放，LRU 在 512MiB 命中 0.00%，随机淘汰 18.80%，576MiB LRU 38.58% [23]，出现热降频。

命中率的分歧点：
- 预测式预取在服务器 / 大 batch 下有效，因为 batch 内多个 token 的专家并集大、可复用高。手机上 batch=1，decode 每步 8/256 个专家且路由几乎无时间局部性，这导致 LRU 在容量不足时命中为 0。
- 576MiB 与 512MiB 之间的悬崖（0% → 38.58%）说明命中率不是平滑函数，而是对工作集边界敏感。判断：缓存策略不能只调参，需要按「层内 top-k 工作集」先保证最小驻留。
- EStream 的收益主要在 prefill（prompt 阶段多 token 并行使专家并集大、按组读才划算），decode 阶段数据缺失。

成熟度：
- 手机 MoE 换入全部为预印本（L1）。
- 出货状态：已出货的系统级模型走 PLE 稀疏而非 MoE。Gemini Nano 4 基于 Gemma 4 E2B / E4B，二手报道，官方原文待核实（引自 M3）；Gemma 4 26B A4B MoE 需加载全部 26B，Q4_0 约 14.4GB（官方，引自 M3）超出多数手机预算；Meta MobileMoE（NeurIPS 2026 poster，二手摘要）是 0.3–0.9B 激活、1.3–5.3B 总参的小 MoE，峰值 RAM 低约 30%（引自 M3，待核实）。判断：端侧 MoE 的可行形态是「总参数小的小 MoE」，此时整体常驻即可，专家换入需求弱；而「大 MoE 流式换入」是极限场景，命中率与热降频均对其不利。

这说明什么：MM-5 的优先级应下调为「面向旗舰、非默认」，并且建议泛化为稀疏权重分层（与 M3 摘要判断一致）。

### Q4 权重分页与端侧推理

LLM in a flash 之后：
- 路线依赖「激活稀疏」，原版依赖 ReLU 模型。PowerInfer-2 把粒度放到神经元簇并做异构 XPU + IO 流水，需稀疏化模型（TurboSparse），OnePlus 12 上 47B 达 11.68 tokens/s [18]。
- Neuralink（原名 Ripple）观察到神经元共激活，把共激活者在闪存中相邻排列，使小随机读合并为大块读 [17]。结论强调：手机 UFS 的瓶颈是 IOPS（队列深度仅 32）而非带宽。该文的收益数字在不同来源有出入（5.93 倍 I/O 延迟 vs 端到端 1.49 倍），未核对原文，不引用具体数字。
- 判断：「常驻集远小于模型尺寸」路线的后续工作集中在改善闪存布局，而非提升带宽，因为带宽不是瓶颈。

激活稀疏现状：SwiGLU 的天然稀疏度低，TEAL 以幅值阈值免训练达到 40–50% 稀疏，解码最高 1.53–1.8 倍 [20]。但它的加速在 GPU 上测得，且稀疏模式是动态按 token 的，对「按神经元行 / 列做闪存读」意味着更碎的访问。判断：激活稀疏对「计算」友好，对「闪存分页」不一定友好；两者的结合没有公开手机数据。

Gemma 3n PLE：官方称 E2B 标准执行加载超 5B 参数，经参数跳过与 PLE 缓存后有效内存负载约 1.91B，PLE 参数可在运行内存外生成、缓存到快速存储、逐层注入 [21]。这是唯一已量产的权重分层先例（L4）。要点：PLE 的访问模式是「按 token 查表」，对闪存读友好（顺序性高、可预测），不同于 MoE 的路由随机性。判断：这解释了为何量产的是 PLE 而不是专家换入——访问模式决定可分页性。

闪存直读开销：
- 带宽与 IOPS：见 §2。关键数字是 4KB 随机读 0.76–1.08GB/s 与 512KB 块 3.5GB/s 的约 3–4 倍差距 [18]。
- mmap 与 direct IO：缺页走内核页缓存，4KB 粒度，预读不一定对齐；direct IO 可控制块大小与队列深度。未找到手机上两者的对比实测。llama.cpp 近期新增 `dio` 加载模式（引自 M3，二手，待核实）。
- 每 GB 读取能耗：未找到公开资料。Micron 对 UFS 4.0 只有相对 25% 能效改进的声明 [32]。这是 Q7 成本模型中最大的缺项。

LoRA 热插拔的内存机制（J6 内存侧）：
- 机制：适配器是小矩阵（秩 r 的 A、B），热插拔的内存成本是「适配器权重常驻 + 切换时的页换入」。若底座权重以 mmap 分页，适配器与底座竞争同一页缓存，切换时可能驱逐底座热页。
- EdgeLoRA：适配器缓存 + 预分配内存池以降低碎片与分配延迟，批量 LoRA 推理让不同适配器请求同批；测试平台 Jetson AGX Orin、Orin Nano、树莓派 5，模型 Llama3.1-8B、Llama3.2-3B、OpenELM-1.1B，称吞吐最高 4 倍、可服务数量级更多适配器（相对 llama.cpp）[26]。未找到切换延迟的具体数字，也没有手机数据。
- NPU 路径：适配器若要预编译进 NPU 图则不是「热」插拔（由 C1b 主责，本文不展开）。
- 判断：J6 内存侧的结论是：适配器本身很小，真正的风险在于它与底座权重分页的页缓存互相干扰。系统应对适配器页打 pin（mlock 类）并按「活跃适配器集」限额，同时把适配器记入与底座同一个账。该判断缺乏实测，置信度低。

这说明什么：MM-6 的「权重分页」部分有 PLE 先例和 PowerInfer-2 原型支撑；「LoRA 热插拔」部分基本无端侧内存机制数据。

### Q7 四种驱逐去向的成本模型

#### Q7.1 符号与公式

令被驱逐的会话状态大小为 S（字节，= 每 token KV 字节 b × 上下文长度 L），重新被需要的概率为 p，被需要时的恢复时延为 T，能耗为 E，质量损失为 Q，隐私风险为 R。

各去向的成本：

- 换出（zram / UFS）：
  - T_swap ≈ S / B_read + t_fault（B_read 为有效读带宽，受 IOPS 与块大小约束，§2）；
  - 写入一次的能耗 E_w = S × e_w，读回 E_r = S × e_r（e 为 J/GB，未找到公开实测）；
  - Q = 0；R 低（本机）。
  - 若压缩后换出到 zram：T 增加解压时间，S 缩小 c 倍，c 取 KIVI / CacheGen 类压缩比 3.5–4.3 倍 [13]（CacheGen 为服务器场景；zram 对 KV 的压缩比无公开数据）。
- 重算（重新 prefill）：
  - T_re ≈ L / v_prefill（v_prefill 为设备 prefill 速度，tokens/s）；
  - 能耗 E_re ≈ L × e_token（e_token 为每 token prefill 能耗）；
  - Q = 0（若重算与原生成使用同一权重和精度）；R 低。
  - 如果被重算的 token 来自多轮，位置编码、注意力 sink 或工具输出的变化会带来一致性问题，CachedAttention 的位置编码解耦即为此而设 [11]。
- 上云：
  - T_cloud = S_wire / B_up + T_cloud_prefill + RTT，其中 S_wire 可取 KV 压缩后体积 S/c（CacheGen 路线 [13]），或只传文本（S_wire = 4L 字节量级，即 token 文本，约 3–4 字节 / token，估算）；
  - 能耗为射频发送能耗（J/GB，未找到公开实测）；
  - Q = 0 或有损（取决于云端是否使用相同模型）；R 高（数据离开设备，涉及 J8 隐私标签）。
- 摘要入库（有损）：
  - T_sum = 一次摘要生成的 decode 时间（摘要长度 l_s，约 l_s / v_decode）+ 写入记忆库；
  - S 缩小为 l_s 个 token 的文本；
  - Q > 0，且无公开量化数据（J1 空白）；R 取决于记忆库的授权模型。

#### Q7.2 数值估算（C/D 级，估算）

取一个具体例子说明量级关系。模型取 Qwen3-4B 级稠密 GQA（36 层、8 个 KV 头、head_dim 128，数值来自公开 config，本文取自记忆，待核实），fp16 KV：

b = 2（K 与 V）× 36 × 8 × 128 × 2 字节 = 147,456 字节 ≈ 144KiB / token。

L = 8K token 时 S ≈ 1.18GB（8192 × 147,456 字节）。

- 换出：UFS 4.0 若能达到 3GB/s（需 512KB 级大块顺序读，[18] 给出 3.5GB/s）则 T_swap ≈ 0.4s；若落到 4KB 随机读 ≈ 1GB/s 则约 1.2s。KV 按层、按块连续布局，可以做大块顺序读，因此应落在较快一端。
- 重算：假设手机 NPU / GPU 对 4B 量化模型的 prefill 速度为 500–1000 tokens/s（假设值，非引用；llm.npu 一类工作报告过更高数字，未在本轮核实），L = 8K 需 8–16s。
- 比值：换出比重算快约 7–40 倍（估算）。该结论的稳健性来自量级差，而不是具体数字。
- 上云：S_wire 若传 KV 压缩后体积，1.18GB / 3.5–4.3 ≈ 0.27–0.34GB，在 50Mbps 上行（假设，约 6MB/s）需 45–55s；传 8K token 文本约 30KB，传输可忽略，云端 prefill 在 GPU 上以秒级完成。结论：上云只能传文本由云端重算，不可能传 KV。这里的 KV 传输经验来自数据中心网络（CacheGen 面向服务器场景），不能直接外推到手机上行 [13]。
- 摘要入库：8K token 压成 300 token 摘要，decode 速度假设 20–30 tokens/s，约 10–15s，且丢失细节。

结论层次（估算）：换出（秒内）< 重算（10s 级）≈ 摘要（10s 级，附带质量损失）< 上云传文本（含网络与隐私成本）。

#### Q7.3 已发表数据与「compute or load」决策

- CachedAttention：重用而非重算，TTFT 最多降 87% [11]。
- HCache：存隐状态，按计算与 IO 的相对速度做二者混合，较 KV 卸载快 1.93 倍、较重算快 5.73 倍 [12]。含义：重算与换出不是二选一，而应按层 / 按块混合。
- Cake：从序列头开始算，从序列尾开始加载，二者在中间相遇，平均 TTFT 降 2.6 倍 [14]。含义：决策规则应是「并行双路」，而不是「按阈值二选一」。
- CacheGen：压缩 KV 并按带宽自适应选择压缩级别，带宽过低时退回为发文本让对端重算 [13]。含义：上云去向天然包含「传文本重算」兜底，与本文估算一致。
- 以上均为服务器场景（GPU + 数据中心带宽），手机的差别是 UMA：计算与 IO 共享同一 DRAM 带宽，二者并行时会互相争用（判断，来自 UMA 架构常识，未找到手机实测）。KVSwap 已针对 UMA 与低 IO 带宽设计 [9]。

#### Q7.4 去向是否完备

判断：不完备，建议增加两项并重定义分类。

1. 原地降精度保留（fp16 → int8 → int4 → 2 bit）：成本是量化 / 反量化计算与质量损失，无 IO。KIVI 2-bit 最大节省 2.6 倍内存 [16]；Apple 端侧模型 KV 已默认 8-bit（引自 M3）。它不改变常驻位置，故不是「去向」而是「就地降级」，但在决策树里应放在换出之前，因为它代价最低。
2. 直接丢弃（不保存、不重算，除非再次出现）：这是 H2O / SnapKV 的语义。多轮失效 [6][7]，所以只能用于「已知无用」的状态（例如已结束子任务的中间推理）。
3. 重算的两种子类：从原始 token 重算 vs 从隐状态恢复（HCache [12]），应区分。
4. 摘要入库不是 KV 的去向，而是「改变数据形态」：输出是文本而非 KV，下次使用要重新 prefill。所以它实际是「丢弃 KV + 保存摘要文本」，成本中要计入下次 prefill。

#### Q7.5 决策规则草案

输入：S、p（预计再使用概率）、距下次使用的时间窗 Δt、剩余内存压力、闪存剩余写寿命、电池 / 热状态、数据敏感度标签、可重算性（原始 token 是否在手）。

1. 若 p 低且状态属于「可丢弃」类（结束的子任务、工具原始输出）且无敏感性：丢弃（保留元数据）。
2. 否则先就地降精度（若质量余量允许）。
3. 若 T_swap（估算 S / B_read）< T_re 且写寿命、热状态允许：换出到 UFS；块在写入时对齐 ≥ 512KB。
4. 若换出被禁止（写寿命或热）或闪存不可用：重算，预算为 L / v_prefill，仅当 Δt 足够长或用户在等待时才触发。
5. 若重算时间超过用户时延 SLO，且数据敏感度标签允许出设备：上云，仅传文本。
6. 仅当上下文长度超过窗口、且重算与换出都无法保留所有细节时：摘要入库，并要求写入记忆框架时附来源与质量等级（J1，需记忆框架配合）。

p 与 Δt 的估计在 Agent 场景可借助调度器已知的信息（下一步要调用的工具、等待用户的状态）。这一点未找到公开研究。MemDecay 的区域标签 [28] 是目前最接近的信号来源。

这说明什么：四去向模型在量级上自洽，但缺 J/GB 数据和 KV 摘要质量数据。公式可以落地，参数不能凭空填。

---

## §4 趋势判断

### 正在收敛的方向

- 云侧 KV：块化 + 前缀共享 + 分层存储，是 vLLM、SGLang、LMCache、Mooncake 共同的形态 [11][15]。
- 重算与加载并行混合，而非二选一（HCache [12]、Cake [14]、CacheGen [13]）。
- 端侧量产的权重分层走 PLE 这类可预测访问模式，而不是随机路由 [21]。
- 闪存瓶颈在 IOPS，优化方向是布局与合并读 [17][18]。

### 公认的空白点

- 手机上 J/GB 的闪存读取、写入、射频发送能耗。
- KV 摘要入库（J1）的质量损失数据；KV 到记忆的系统化研究。
- 手机上前缀缓存侧信道的实测与防护。
- KV 换出对 UFS 寿命的影响。
- 大 MoE 在手机上 decode 阶段的命中率与吞吐（多数论文只给 prefill 或缺吞吐）。
- LoRA 与底座权重分页共存的页缓存干扰数据。
- NPU 路径的 KV 动态扩张与换出（NPU 图编译约束）。

### 仍有分歧的问题

- 有损驱逐是否值得：单轮 benchmark 上收益显著，多轮上近 0 分 [6]。
- 混合 / 线性注意力是否让 KV 管理过时：体积下降 vs 状态不可切分。
- 大 MoE 流式换入与小 MoE / PLE 谁是端侧主流：现有出货证据偏向后者。
- 前缀共享与隐私：全隔离 vs 选择性隔离 [5]。

---

## §5 立场评审表

| 立场 ID | 判断 | 关键证据 | 最强反方证据 | 修订建议 | 置信度 |
|---|---|---|---|---|---|
| MM-4 模型内存域的 KV：DMA 路径上的 KV cache 驱逐经济学 | 需修订 | 换出比重算快一个数量级（估算，§3.7）；CachedAttention、HCache、Cake 证明加载 / 重算混合有效 [11][12][14]；KVSwap 提供端侧原型 [9] | 有损驱逐多轮失效 [6][7]；混合架构缩小 KV 体积 [8]；Agent 单用户少会话，块化收益低 | 1. 「驱逐」改为「回收」，可恢复手段（降精度、换出、重算）优先，有损丢弃只作兜底；2. 对象抽象为「会话状态单元」，含尺寸、可切分性、重算成本；3. 经济学公式留 J/GB 与写寿命参数，补测；4. 前缀共享按信任域分区 [3] | 中 |
| MM-5 模型内存域的 MoE 专家管理 | 需修订（降优先级并泛化） | 手机实测已出现 [22][23]；预取与缓存策略谱系成熟于 GPU [24] | 已出货的是 PLE 而非 MoE [21]；命中率悬崖 [23]；热降频；大 MoE 超出内存预算（Gemma 4 26B A4B Q4_0 约 14.4GB，引自 M3） | 泛化为「稀疏权重分层」，统一覆盖 PLE、专家、神经元簇；MoE 专家换入作旗舰档可选策略，不作默认；缓存策略需有「最小工作集保证」，不可只靠 LRU | 中 |
| MM-6 模型内存域的权重分页与 LoRA 热插拔 | 权重分页：支持；LoRA 热插拔：需修订（证据不足） | PLE 量产 [21]；PowerInfer-2 / Neuralink 闪存分页 [17][18]；IOPS 瓶颈明确 | 激活稀疏依赖特定模型 [20]；SwiGLU 稀疏低；NPU 路径的 AOT 编译不易分页；LoRA 端侧只有 Jetson 级原型 [26] | 权重分页要求模型提供「分页友好」的布局（块对齐、共激活聚类）；LoRA 热插拔先按「常驻 pin + 限额」设计，待实测后再决定是否换入；适配器与底座同账 | 权重分页中；LoRA 低 |
| MM-7 两域驱逐路径互通，四种去向 | 需修订 | 四去向量级自洽（§3.7）；CacheGen 的兜底行为说明上云 = 传文本 [13] | 去向不完备：缺降精度与丢弃；摘要入库不是 KV 的去向而是改变形态；J1 无系统研究 | 去向改为「就地降级 → 换出 → 重算 → 上云（仅文本）→ 摘要入库（带来源与质量标）」的有序决策树（§3.7 草案）；摘要入库由记忆框架实现、内存管理只提供触发事件 | 中 |

---

## §6 接缝发现

### J1 KV / 上下文有损驱逐 → 摘要入库（成本侧）

- 没有找到把「驱逐」和「长期记忆写入」做成一条路径的系统研究。检索范围：2026 年 arXiv 上 KV 驱逐与 agent memory 的相关标题；结果为驱逐策略类（SideQuest、MemDecay、ForesightKV）和记忆到 KV 的复用类（AgentKVShift [27]）。
- AgentKVShift 方向相反：把检索到的记忆单元的 KV 复用并校正，只刷新 10–30% 缓存即接近全量重算 [27]。含义：记忆库中若同时保存文本与（可校正的）KV，反向读取的成本可降 2–3.5 倍，这为 J1 的「读侧」提供了参考，但不涉及「写侧」的质量损失。
- 成本侧结论：摘要的时延主要是一次 decode（秒级到十秒级，估算），质量损失无数据。与重算相比，摘要的收益是长期占用小，代价是不可逆。
- 建议：J1 接口应只定义事件（「会话状态单元被回收，附原始 token 范围与可重算性标志」），摘要由记忆框架 / Agent 决定。这与 MEM-2「策略归 Agent」一致。

### J6 LoRA 热插拔与权重分页（内存侧）

- 适配器小、切换成本主要在页缓存干扰，而非适配器本身（判断，缺实测）。EdgeLoRA 的内存池与适配器缓存是服务器式做法 [26]。
- 建议：适配器与底座在同一 memcg / 账下，适配器页 pin；适配器版本绑定底座版本，由 C1b 主责。

### J2（协同记录）

- 侧信道证据见 Q2.2：PromptPeek、Early Bird、审计、CacheSolidarity [2][3][4][5]。
- 系统提示词 KV 共享无泄漏风险，私有前缀共享需分区。

---

## §7 组件特有输出

### 7.1 KV cache 管理技术谱系表

见 §1.1。

### 7.2 MoE 专家管理对比表

| 工作 | 预取策略 | 命中率 | 内存节省 | 平台 | 成熟度 |
|---|---|---|---|---|---|
| EdgeMoE | 专家分级位宽 + 概率预载 + 淘汰 | 未核实 | 对内存优化基线 1.19–2.77 倍（性能），Jetson TX2 跑 >10B（引自 M3） | Jetson TX2、树莓派 4B | L1 |
| Pre-gated MoE | 预门控选下一块专家 | 不适用（预取非缓存） | 相对 GPU-only 多 23% 延迟 | GPU | L1–L2（ISCA 2024） |
| AdapMoE | 敏感度自适应门控 + 预取 + 缓存 DP | 未核实 | 激活专家平均 -25%，1.35 倍加速 | Mixtral 类，GPU | L1 |
| HOBBIT | 缺失时用低精度专家替代 | 未核实 | 最高 9.93 倍解码加速（基于 llama.cpp） | 边缘 | L1 |
| ProMoE | 学习型预测器按步预取 | 未核实 | prefill 1.78 倍、decode 1.34 倍（对手工缓存） | GPU | L1 |
| fMoE [24] | 迭代级 expert map + 语义嵌入引导 | 较 SOTA 命中率升 36% | 延迟降 47% | GPU 服务 | L1–L2 |
| KTransformers [25] | 不预取；专家驻 CPU 内存并计算，专家延迟重叠 | 不适用 | 把专家移出显存 | CPU+GPU，需 500GB 级 DDR | L3 |
| FlashMoE（引自 M3 [29]） | ML 缓存替换 | 较 LRU / LFU 最高 +51% | 最高 2.6 倍加速 | 桌面 SSD | L1 |
| EStream [22] | 专家池在 UFS，分组换入到 NPU arena | 摘要页未报告 | 峰值物理内存降 1.19–12.29 倍；prefill TTFT 加速 2.25–27.57 倍 | Snapdragon 手机 NPU | L1 |
| Paging the Experts [23] | 固定路由回放下比较 LRU / 随机 | 512MiB：LRU 0.00% / 随机 18.80%；576MiB LRU 38.58% | 进程峰值 1.87–2.73GiB（35B-A3B） | iPhone | L1 |

说明：表中「内存节省」与「命中率」口径不统一（有的是性能收益、有的是内存），因为各论文不报同一指标；跨行不可直接比较。

### 7.3 四种驱逐去向成本模型评审

| 去向 | 成本构成 | 公式（符号见 §3.7） | 已发表数据 | 端侧缺口 | 评审 |
|---|---|---|---|---|---|
| 换出（zram / UFS） | 恢复时延、写入与读取能耗、写寿命 | T ≈ S / B_read + t_fault；E = S(e_w + e_r) | CachedAttention、HCache 服务器数据；KVSwap 端侧 NVMe / eMMC 数据；UFS 随机读 [18] | J/GB、写寿命、UFS 上 KV 换出实测 | 量级最优（估算），数据最不完整 |
| 重算 | prefill 时延与能耗，占用算力与带宽 | T ≈ L / v_prefill；E ≈ L × e_token | HCache 隐状态恢复较 token 重算快至 5.73 倍 [12] | 手机 prefill 速度与 J/token 需引用 C1b 数据 | 无质量损失，但对长上下文代价线性增长 |
| 上云 | 上行带宽、云端 prefill、RTT、隐私 | T = S_wire / B_up + T_cloud + RTT | CacheGen（服务器网络）[13] | 手机上行带宽与射频能耗；隐私标签（J8） | 实际只能传文本；KV 传输不可行（估算） |
| 摘要入库 | 摘要 decode 时延、质量损失、下次 prefill | T = l_s / v_decode；Q > 0 | 无 | 质量损失数据；记忆框架写入授权 | 不是 KV 去向而是形态转换；J1 空白 |
| （建议新增）就地降精度 | 量化计算、质量损失 | T ≈ 量化 kernel 时间；Q 取决于位宽 | KIVI [16]；Apple 端侧 8-bit（M3） | NPU 上 KV 量化 kernel 支持 | 应放在决策树最前 |
| （建议新增）丢弃 | 无直接成本；再次需要时等价重算 | p × T_re | SCBench 多轮失效 [6] | 如何可靠判断「不再需要」 | 仅用于已知无用状态 |

---

## §8 参考资料与待核实清单

### 参考资料

| 编号 | 标题 | 机构或作者 | URL | 日期 |
|---|---|---|---|---|
| [1] | vAttention: Dynamic Memory Management for Serving LLMs without PagedAttention | Prabhu 等，Microsoft Research India | https://arxiv.org/abs/2405.04437 | 2024-05；ASPLOS 2025（MSR 页面标注） |
| [2] | The Early Bird Catches the Leak: Unveiling Timing Side Channels in LLM Serving Systems | 见 arXiv | https://arxiv.org/abs/2409.20002 | 2024-09（会议待核实） |
| [3] | I Know What You Asked: Prompt Leakage via KV-Cache Sharing in Multi-Tenant LLM Serving | Wu 等，南科大、字节 | https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf | NDSS 2025 |
| [4] | Auditing Prompt Caching in Language Model APIs | Gu 等，Stanford | https://arxiv.org/abs/2502.07776 | 2025-02 |
| [5] | CacheSolidarity（automatic prefix caching 泄漏防护） | 见 arXiv | https://arxiv.org/abs/2603.10726 | 2026-03（仅见摘要片段） |
| [6] | SCBench: A KV Cache-Centric Analysis of Long-Context Methods | Microsoft 等 | https://arxiv.org/abs/2412.10319 | ICLR 2025 |
| [7] | KVzip: Query-Agnostic KV Cache Compression with Context Reconstruction | 见 arXiv | https://arxiv.org/abs/2505.23416 | 2025-05 |
| [8] | Marconi: Prefix Caching for the Era of Hybrid LLMs | Pan 等 | https://arxiv.org/abs/2411.19379 | MLSys 2025（荣誉提名） |
| [9] | KVSwap: Disk-aware KV Cache Offloading for Long-Context On-device Inference | Zhang、Xia、Wang，Leeds | https://arxiv.org/abs/2511.11907 | 2025-11 |
| [10] | KVNAND: Efficient On-Device LLM Inference Using DRAM-Free In-Flash Computing | Deng 等 | https://arxiv.org/abs/2512.03608 | 2025-12 |
| [11] | Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention | Gao 等，NUS、上交、华为云 | https://arxiv.org/abs/2403.19708 ；https://www.usenix.org/conference/atc24/presentation/gao-bin-cost | USENIX ATC 2024 |
| [12] | Fast State Restoration in LLM Serving with HCache | Gao、Chen、Shu，清华 | https://arxiv.org/abs/2410.05004 | EuroSys 2025 |
| [13] | CacheGen: KV Cache Compression and Streaming for Fast LLM Serving | Liu、Jiang 等 | https://arxiv.org/abs/2310.07240 | SIGCOMM 2024 |
| [14] | Compute Or Load KV Cache? Why Not Both?（Cake） | Jin 等 | https://arxiv.org/abs/2410.03065 | 2024-10 |
| [15] | Mooncake（KVCache-centric disaggregated architecture） | kvcache-ai | https://github.com/kvcache-ai/Mooncake | FAST 2025 最佳论文（项目自述） |
| [16] | KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache | 见 arXiv | https://arxiv.org/abs/2402.02750 | ICML 2024（引自 M3） |
| [17] | Neuralink（原名 Ripple）：Fast On-Device LLM Inference with Neuron Co-Activation Linking | 清华等 | https://arxiv.org/abs/2410.19274 | ASPLOS 2025 |
| [18] | PowerInfer-2: Fast Large Language Model Inference on a Smartphone | 上海交大 IPADS 等 | https://arxiv.org/abs/2406.06282 | 2024-06 |
| [19] | LLM in a flash: Efficient LLM Inference with Limited Memory | Apple | https://arxiv.org/abs/2312.11514 | 2023-12 |
| [20] | Training-Free Activation Sparsity in Large Language Models（TEAL） | 见 arXiv | https://arxiv.org/abs/2408.14690 ；https://proceedings.iclr.cc/paper_files/paper/2025/hash/f3f2ff9579ba6deeb89caa2fe1f0b99c-Abstract-Conference.html | ICLR 2025 |
| [21] | Gemma 3n model overview | Google | https://ai.google.dev/gemma/docs/3n | 2025 |
| [22] | EStream: Fast and Memory-Efficient MoE Prefill through Expert Virtualization on Mobile NPUs | Zhang、Zheng、Wu 等 | https://arxiv.org/abs/2609.06551 | 2026-09-06 |
| [23] | Paging the Experts（iPhone 上 MoE 专家换入） | 见 M3 | https://arxiv.org/abs/2609.29032 | 2026-09-24（本轮未复核，引自 M3） |
| [24] | Taming Latency-Memory Trade-Off in MoE-Based LLM Serving via Fine-Grained Expert Offloading（fMoE） | Yu、Cui 等 | https://arxiv.org/abs/2502.05370 | 2025-02 |
| [25] | KTransformers: Unleashing the Full Potential of CPU/GPU Hybrid Inference for MoE Models | 清华 MADSys | https://madsys.cs.tsinghua.edu.cn/publication/ktransformers-unleashing-the-full-potential-of-cpu/gpu-hybrid-inference-for-moe-models/SOSP25-chen.pdf | SOSP 2025 |
| [26] | EdgeLoRA: An Efficient Multi-Tenant LLM Serving System on Edge Devices | Shen 等 | https://arxiv.org/abs/2507.01438 | 2025-07 |
| [27] | AgentKVShift: Efficient KV Cache Reuse for Agentic Memory Systems | Pandey 等 | https://arxiv.org/abs/2607.21604 | 2026-05-15 提交 |
| [28] | MemDecay: Region-Aware KV Cache Eviction for Efficient LLM Agent Inference | 见 arXiv | https://arxiv.org/abs/2607.10582 | 2026-07（仅见摘要片段） |
| [29] | FlashMoE（SSD 卸载的 ML 缓存替换） | 见 M3 | https://arxiv.org/abs/2601.17063 | 2026-01（引自 M3，未复核） |
| [30] | Mooncake 与 SGLang HiCache、LMCache 集成说明 | 项目页 | https://github.com/kvcache-ai/Mooncake | 2025 |
| [31] | LMCache: Hybrid-Attention Models 文档 | LMCache | https://docs.lmcache.ai/mp/hybrid_models.html | 2026（版本间描述冲突） |
| [32] | Micron UFS 4.0 Mobile Storage（厂商资料） | Micron | https://www.storagenewsletter.com/2023/06/30/micron-ufs-4-0-mobile-storage-built-on-232-layer-3d-nand-delivers-fastest-performance-for-smartphones/ | 2023-06 |
| [33] | Gemma 3 局部 / 全局注意力与 Qwen3-Next 3:1 混合结构说明 | Raschka（个人站点，C 级） | https://sebastianraschka.com/llm-architecture-gallery/hybrid-attention/ | 2026 |

### 待核实清单

1. [23] Paging the Experts 的 arXiv 编号、机构、数字：本轮未复核，仅引自 M3。
2. [3] 的攻击细节与「SGLang 已因此修补」的说法：后者仅见单一二手来源，未核实。
3. [4] 中「7 家提供商」数字：二手摘要，未在原文核对。
4. [2] 的发表会议（可能为 2025 年某安全会议）：未确认。
5. [17] Neuralink 的收益数字（5.93 倍 I/O 延迟 vs 端到端 1.49 倍）：来源间冲突，未核对原文。
6. [5][28] 及 RestoreKV、ReST-KV、Trust the Mass 等 2026 年论文：只见摘要片段，结论未核实。
7. PagedAttention / vLLM 会议为 SOSP 2023、H2O、StreamingLLM、SnapKV 的会议年份：记忆所得，本轮未联网复核。
8. Qwen3-4B 的 KV 配置（36 层、8 KV 头、head_dim 128）：取自记忆，未核对官方 config。
9. 手机 prefill 速度 500–1000 tokens/s、手机上行 50Mbps：为估算假设，不是引用。
10. UFS 写入寿命数据（TBW）：用户机型未知，估算无依据，标 D。
11. Gemini Nano 4 基于 Gemma 4 E2B / E4B：仅二手报道，官方原文待核实。
12. Gemma 3n PLE 在 Android 平台上是否为默认路径、PLE 缓存是否落闪存：官方文档只写「可缓存到快速存储」。
13. 手机 GPU（Adreno、Mali）驱动是否暴露虚拟预留 + 物理按需提交接口：未找到公开资料。
14. 手机上 mmap 与 direct IO 的实测对比、UFS 每 GB 读取与写入能耗、射频每 GB 发送能耗：未找到公开资料。
15. LMCache 对 Qwen3-Next / Qwen3.5 的支持状态：文档页互相矛盾。
16. vLLM Sleep Mode、InfiniGen、PyramidKV、Quest、CLA、YOCO、GQA / MLA 的原始出处与成熟度：本轮未检索，不在表中给结论。
17. Apple 2025 技术报告的原始 URL：本轮未单独核对，数字引自 M3。

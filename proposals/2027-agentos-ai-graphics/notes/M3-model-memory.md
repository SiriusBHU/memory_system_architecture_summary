# M3 模型内存（KT2 + KT3）调研笔记

> 调研日期 2026-11-03。范围：1.2 中 KT2、KT3 的业界进展；2.2 中的模型内存瓶颈；第四部分 KT2（MoE 专家缓存 / KV Cache 两节）与 KT3。
> 来源标注：`[n]` 对应文末「参考资料」。「估算」= 本文用公开 config 自行推算；「待核实」= 仅有二手来源或未能确认。

## 摘要（10 行以内）

1. **MoE 判断**：2027 年旗舰端侧「稀疏权重」会成主流，但「纯 MoE 专家流式换入」不会成为默认形态。已出货的系统模型（Gemini Nano 4 基于 Gemma 4 E2B/E4B）走的是 PLE 稀疏、不是 MoE [5][6]；MoE 路线（Gemma 4 26B A4B、Qwen3.5-35B-A3B、Meta MobileMoE）在研究与旗舰档快速推进 [5][9][10]。建议把专家缓存泛化为「稀疏权重分层」。
2. **KV 与权重谁大**：取决于架构。稠密 GQA 小模型（Qwen3-4B）fp16 KV 在约 16K 上下文就超过 Q4 权重（估算）；MoE 与混合线性注意力模型（Qwen3.5-35B-A3B，每 token 仅 20 KiB）权重始终更大。Agent 典型 32K–64K 上下文下，结论是「常驻看权重，增量与多会话看 KV」。
3. **最关键的新证据**：2026 年 9 月起出现手机侧 MoE 实测：EStream（Snapdragon NPU，预填充 TTFT 加速 2.25–27.57 倍，预印本）[11]；iPhone 上 Qwen3.6-35B-A3B 进程内存峰值仅 1.87–2.73 GiB，但 512 MiB LRU 命中率为 0%、576 MiB 升到 38.58% [12]，说明命中率对容量和负载极敏感。
4. **KT3**：llama.cpp 默认 mmap、ExecuTorch 的 .pte 段页对齐并在推进权重共享、LiteRT-LM 首次加载需优化并缓存 [20][21][22]；但「NPU 侧文件映射 / 零拷贝」缺少公开系统论文。
5. **最大资料空白**：端侧 MoE 与 KV 的手机实测绝对 tokens/s 很少；模型加载时间（冷 / 热）几乎没有公开数据；鸿蒙 / MindSpore Lite / HiAI 的模型加载机制未找到公开资料；Apple 2026 端侧模型是否为稀疏模型只有二手来源。

---

## 第一部分（M3 范围）1.2 业界最新进展

### 1.2-KT2 MoE / 稀疏权重

**趋势一：端侧模型形态从「稠密 + 量化」向「稀疏权重」分叉。**
- 事实依据：
  - Google Gemma 4（2026-04-02 发布）含 E2B / E4B / 12B / 31B 稠密与 26B A4B MoE（激活约 4B，但需加载全部 26B）；官方给出权重内存表：26B A4B Q4_0 约 14.4 GB，E2B 移动端 1.1 GB、E4B 移动端 2.5 GB [5]。
  - Gemini Nano 4 基于 Gemma 4 E2B（Fast）/ E4B（Full），随今年晚些时候的新旗舰 Android 设备上线（AICore 开发者预览，2026-04-02）[6]（二手报道，待核实官方博客原文）。
  - Gemma 3n 的 PLE（Per-Layer Embedding）：E2B 标准执行加载超过 5B 参数，经参数跳过与 PLE 缓存后有效内存负载约 1.91B；PLE 数据「可缓存到快速存储」逐层注入 [7]。这是已量产的「稀疏权重分层」先例。
  - Meta MobileMoE（NeurIPS 2026 poster）：0.3–0.9B 激活、1.3–5.3B 总参；相对同总参数的稠密基线 MobileLLM-Pro，手机上 prefill / decode 快 2–4 倍、峰值 RAM 低约 30%；实现依赖 ExecuTorch 中自写的融合 MoE kernel（后一点为二手摘要）[10]。
  - Alibaba Qwen3.5 系列：Qwen3.5-35B-A3B 为 40 层、256 专家、每 token 8 专家，3:1 线性注意力 / 全注意力混合 [9]；Qwen3.5 Small 系列（0.8B / 2B / 4B / 9B）2026-03 发布 [8]（二手报道）。
- 对我们的影响：专家缓存的对象不应只写「MoE 专家」，要抽象成「可分页的稀疏权重单元」，同时覆盖 PLE 与激活稀疏神经元。

**趋势二：专家流式换入从服务器 / 桌面走向手机，但仍以预印本和「可行性」为主。**
- 事实依据：
  - EStream（arXiv 2609.06551，2026-09-06，预印本，未见同行评议会议）：专家池放 UFS，经固定大小 NPU 可寻址 arena 分组换入；在商用 Snapdragon 手机上、3 个 7B–16B MoE、256–4096 token 提示，对各设置最快基线报告 2.25–27.57 倍 prefill TTFT 加速，峰值物理内存降 1.19–12.29 倍，可扩展到 46.7B [11]。
  - 「Paging the Experts」（arXiv 2609.29032，2026-09-24，预印本）：iPhone（iOS 27）+ Swift/MLX 运行时 Routide，Qwen3.6-35B-A3B 量化；固定路由回放 128 token：512 MiB LRU 命中率 0.00%，512 MiB 随机淘汰 18.80%，576 MiB LRU 38.58%；进程内存峰值短 prompt 1.87–2.32 GiB、较长 prompt 2.39–2.73 GiB；出现热降频停止事件；摘要未给吞吐 [12]。结论：容量悬崖是「策略 × 负载」交互，不是普适内存需求。
  - FlashMoE（arXiv 2601.17063，v1 2026-01-22，v2 2026-10-05，预印本）：用 ML 缓存替换在 SSD 卸载场景相对 LRU / LFU 命中率最高提升 51%，最高 2.6 倍加速；平台为桌面，非手机 [13]。
- 对我们的影响：命中率不是常数，策略需要「数据驱动 + 场景自适应」；手机上的专家缓存还没有公认基线，是立项可占的位置。

**趋势三：经典方法的数字（年份与来源已核对 arXiv；会议见待核实）。**

| 方法 | 年份 / 来源 | 一句话原理 | 报告数字 | 局限 |
|---|---|---|---|---|
| LLM in a flash | 2023-12，arXiv 2312.11514 [14] | 闪存放权重，按需读激活神经元；窗口复用 + 行列捆绑 | 可跑 2 倍 DRAM 的模型；相对朴素实现 CPU 4–5 倍、GPU 20–25 倍 | 依赖 ReLU 稀疏；会议 ACL 2024 未能确认 |
| EdgeMoE | 2023-08 v1，2025-03 v2 更名，arXiv 2308.14352 [15] | 专家分级位宽 + 概率预载 + 缓存淘汰 | 对内存优化基线 1.19–2.77 倍；Jetson TX2 跑 >10B | 平台为树莓派 4B / Jetson TX2 |
| PowerInfer-2 | 2024-06，arXiv 2406.06282（v3 2024-12）[16] | 神经元簇粒度 + 异构 XPU + IO 流水 | OnePlus 12（24GB）上 47B TurboSparse-Mixtral 达 11.68 tokens/s；对 llama.cpp 平均 24.6 倍、对 LLMFlash 3.84 倍 | 需稀疏化模型；会议待核实 |
| Pre-gated MoE | ISCA 2024，arXiv 2308.12066 [17] | 预门控选下一块专家，迁移与计算重叠 | 相对 GPU-only 最优仅多 23% 延迟 | 需改模型并微调；GPU 平台 |
| MoE-Infinity | 2024-01，arXiv 2401.14361（v3 2025-03 更名）[18] | 按请求级激活矩阵做稀疏感知缓存 / 预取 | 数字未核实 | 面向服务器 / 个人机 |
| AdapMoE | ICCAD 2024，arXiv 2408.10284 [19] | 敏感度自适应门控 + 预取 + 缓存分配 DP | 激活专家平均 -25%，1.35 倍加速 | 作者自测，Mixtral 类 |
| HOBBIT | 2024-11，arXiv 2411.01433 [20] | 缓存缺失时用低精度专家替换 | 最高 9.93 倍解码加速（基于 llama.cpp） | 精度折损须评估；会议待核实 |
| ProMoE | 2024-10，arXiv 2410.22134 [21] | 学习型预测器按步长预取 | 对手工缓存 prefill 平均 1.78 倍、decode 1.34 倍（v3） | 版本间数字不同；会议待核实 |

（FlashMoE、EStream、Paging the Experts 见上。）

### 1.2-KT2 KV Cache

**趋势四：KV 管理从「量化 / 淘汰」走向「架构层缩减 + 系统层分页 / 换出」。**
- 事实依据：
  - Apple 2025 端侧约 3B 模型：分两块（62.5% / 37.5% 层），第二块不含 K/V 投影并共享第一块的 KV，KV 内存降 37.5%；局部 / 全局注意力交错，KV 量化到 8 bit，2-bit QAT 权重 [22]。
  - Qwen3.5-35B-A3B 只有 10/40 层为全注意力，2 个 KV 头、head_dim 256 [9]；Gemma 4 小模型支持 128K 上下文 [5]。
  - 系统层：LLMS（arXiv 2403.11805，2024-03）把 KV 按 16 token 切块，分块压缩与换出，用 LCTRU 队列淘汰，宣称上下文切换延迟降两个数量级 [23]（二手摘要）；MNN-LLM（arXiv 2506.10443，2025）KV 先放 DRAM、溢出到 Flash 并预取，称 Flash 中 KV 小于约 3072K（原文如此，疑为 3072 token 级别，待核实）时加载开销可被计算掩盖，Embedding 放 Flash 省约 15% DRAM [24]；KVSwap（arXiv 2511.11907，2025-11，预印本）：全量 KV 放磁盘、内存留紧凑元数据预测预载，未给具体倍数 [25]。
  - 经典方法：KIVI（ICML 2024，arXiv 2402.02750）K 按通道、V 按 token 的 2-bit 量化，Llama-2-7B 峰值内存降 2.6 倍，吞吐 2.35–3.47 倍 [26]。H2O（NeurIPS 2023）、StreamingLLM（ICLR 2024）、SnapKV（NeurIPS 2024）的会议年份为本人记忆，本轮未联网复核，见待核实。
- 对我们的影响：KV 回收要两层并用：模型侧（共享 / 混合注意力，由模型决定）无法由 OS 控制，OS 能做的是分块分页、压缩、跨会话前缀复用和闪存换出。

### 1.2-KT3 模型加载

**趋势五：加载路径的共识是「mmap + 页对齐 + 数据与程序分离」，NPU 路径仍是各家私有二进制。**
- 事实依据：
  - llama.cpp：默认 mmap；新版把 `--mlock`、`--no-mmap` 标为弃用，改用 `-lm/--load-mode`（auto / mmap / mlock / mmap+mlock / dio）[27]（二手博客转述，待对照官方文档）。
  - ExecuTorch：.pte 先放 flatbuffer 程序段、再放页对齐数据段，便于 mmap 与只读程序；两个由同一基座导出的 .pte 当前不共享权重，社区 RFC 提议拆成可共享文件并引入 NamedDataMap；LoRA 示例用多个 .pte 共享一份基座权重 [28]。
  - LiteRT-LM：同一设备首次加载模型较慢（权重优化），之后因缓存加快；官方给出 Gemma-3n-E2B 在 S24 Ultra 上 GPU prefill 816 tokens/s（1024 prefill / 256 decode，锁性能）；Gemma 4 模型卡称 TTFT 不含加载时间，S26 Ultra CPU 路径 TTFT 1.8 s、CPU 内存 1733 MB（峰值 RSS，经搜索摘要转述）[22b]。
  - Qualcomm QNN：context binary 是预编译产物，仅支持单 SoC；权重共享可在同一 context binary 的多图间共享；Genie 以多 binary 分段执行；ORT-QNN 2.1.0 提到 64 位 Extended uDMA 模式显著改善 LLM 级模型的内存效率与初始化时间 [29]。HF 模型卡称 3.5B 模型超出 HTP 单会话权重限制，被切成 4 个上下文，且设备并发会话约 7 个上限（社区模型卡，待核实）。
  - NPU 路径研究：T-MAN（arXiv 2511.11248，2025-11）指出 NPU 非 GEMM 能力弱，主张统一查表，只保留一份权重 [30]；FlexServe（arXiv 2603.09046）测得 8GB 连续内存（CMA）分配约 6.44 s，普通 mmap 约 0.56 s（搜索摘要，待核实）[31]。
  - UFS：UFS 5.0 标准（JESD220H，2026 年初发布）顺序读 10.8 GB/s，UFS 4.x 常报约 5.8 GB/s（另有 4.6 GB/s 说法）；量产手机预计 2027 年起 [32]。
- 对我们的影响：「NPU 侧文件映射」是公开资料最薄弱处，说明这既是难点也是差异化空间；同时「首次加载优化 + 缓存」是各框架共性，我们应把冷加载拆成「转换 / 重排」与「映射 / 预读」两件事。

### 对立项的启示（1.2）
- 支撑 KT2：稀疏权重分层有 PLE（已量产）、MoE（旗舰探索）、激活稀疏（研究）三类证据，抽象层应统一。
- 支撑 KT2-KV：模型侧缩减由厂商决定，系统侧价值在分块 / 复用 / 换出（LLMS、MNN-LLM、KVSwap 方向）。
- 支撑 KT3：mmap + 数据段页对齐是共识，NPU 零拷贝映射缺公开方案。

---

## 第二部分（M3 范围）2.2 模型内存瓶颈

### 2.2.1 两个判断题

**判断题 ①：2027 年端侧 MoE 会不会成为主流？专家缓存是否应泛化为「稀疏权重分层」？**

判断：
- **「稀疏权重」会是 2027 年旗舰主流，「MoE 专家流式换入」是旗舰档的一个选项，不是全市场默认。置信度：中。**
- **专家缓存应泛化为「稀疏权重分层」：是。**

依据：
1. 已出货的系统级端侧模型走 PLE 稀疏而非 MoE：Gemini Nano 4 基于 E2B / E4B [6]，而 Gemma 3n 的 PLE 已把有效加载降到约 1.91B [7]。
2. MoE 在 2026 年进入主流开源路线：Gemma 4 26B A4B [5]、Qwen3.5-35B-A3B [9]，且 Meta 以 MobileMoE 证明小规模 MoE 在手机上 2–4 倍更快、峰值 RAM 低约 30% [10]。
3. 手机上流式 MoE 已有可行性（EStream、iPhone 实测）[11][12]，但命中率悬崖（512 MiB 下 LRU 0%）显示容量与策略高度敏感 [12]，且 Meta 称现有移动栈对 MoE 缺少原生高效支持（二手摘要）[10]。
4. Apple WWDC26：二手来源称有 20B 稀疏端侧模型，另一来源只说「更强的第二个端侧模型，限高端机」，来源互相矛盾，无 Apple 官方文档，不作为证据，仅列待核实 [33]。
5. 内存成本约束：26B A4B 即使 Q4 也约 14.4 GB（官方表）[5]，在 12–16GB 机型上不可能常驻，必须分层；这恰好是「稀疏权重分层」的需求来源。

泛化的抽象（建议）：
- 对象：专家（MoE）、PLE 表、激活稀疏神经元簇（PowerInfer-2、LLM in a flash [14][16]）、Embedding 表（MNN-LLM 放 Flash 省约 15% DRAM [24]）。
- 共同点：粒度小于层、访问分布有偏、可预测（门控 / 前层激活）、backing store 是 UFS。
- 统一接口：热度模型 + 预取预测器 + 分层放置（DRAM / zram 压缩 / UFS）+ 命中率反馈。

**判断题 ②：Agent 场景下 KV Cache 与权重谁更大？**

公开 config 与计算（fp16 KV，2 字节；每 token KV 字节 = 2（K 与 V）× 全注意力层数 × KV 头数 × head_dim × 2）：

| 模型（config 出处） | 每 token KV（估算） | 8K | 32K | 128K | Q4 权重（估算） | KV=权重 的上下文 |
|---|---|---|---|---|---|---|
| Qwen3-4B：36 层、8 KV 头、head_dim 128 [34] | 2×36×8×128×2 = 147,456 B = 144 KiB | 1.1 GiB | 4.5 GiB | 18 GiB（原生上下文 40,960，超出需外推） | 约 2.4 GB | 约 16K（fp16）；KV 4 位化后约 65K |
| Qwen3-30B-A3B：48 层、4 KV 头、head_dim 128、128 专家 / 激活 8 [35] | 2×48×4×128×2 = 98,304 B = 96 KiB | 0.75 GiB | 3 GiB | 12 GiB | 约 18.5 GB | 约 188K |
| Qwen3.5-35B-A3B：40 层中 10 层全注意力、2 KV 头、head_dim 256、256 专家 / 激活 8 [9] | 2×10×2×256×2 = 20,480 B = 20 KiB | 0.16 GiB | 0.63 GiB | 2.5 GiB（最大 256K 为 5 GiB） | 约 21 GB | 约 1M，超过最大上下文 |

计算说明：
- Q4 权重估算 = 总参数 × 4.85 bit / 8（按 Q4_K_M 约 4.85 bit/weight 取值，这是我的假设，非出处数据）。Qwen3-4B 取 4.0B → 2.4 GB；Qwen3-30B-A3B 取 30.5B → 18.5 GB；Qwen3.5-35B-A3B 取 35B → 21 GB。总参数是模型名与常见报道值，未在 config 中核对。
- 混合模型的线性注意力层为固定状态：线性层 30 层 × 每层状态约 32 头 × 128 × 128 × 2 B ≈ 1 MiB，合计约 30 MiB（估算，未计卷积状态与 fp32 状态可能翻倍）[9]。
- 对照官方权重表：Gemma 4 26B A4B Q4_0 约 14.4 GB，E4B 移动端 2.5 GB [5]；与上表量级一致。

分情况结论：
- **稠密 GQA 小模型（Qwen3-4B 类）**：32K 上下文 fp16 KV 4.5 GiB，约为 Q4 权重的 1.9 倍；每 token 解码读取量中，KV 约占 66%（4.5 / (4.5+2.4)，估算，把 GiB 与 GB 视作等量，量级成立）。KV 更大。
- **MoE 模型**：权重占常驻大头（18.5 GB vs 3 GiB）；但解码每 token 只读激活权重（A3B 约 3.3B 激活，Q4 约 2 GB，估算）加 KV 3 GiB，二者带宽相当。
- **混合线性注意力 MoE**：KV 很小，权重绝对主导。
- **Agent 上下文长度**：公开的大样本很少。LangWatch 对一位工程师 287,748 次 API 调用、2,451 个 Agent 的研究显示压缩触发事件上下文中位数约 65,588 token，压缩后每步增长约 1,470 token [36]（单人案例，云端编码 Agent，不代表手机）。手机 Agent 的工具描述固定开销可达 1–1.7 万 token（博客，待核实）[36]。本文假定手机 Agent 为 8K–64K，端侧 Apple 官方上下文仅约 8K（二手，待核实）[33]。
- **多会话放大**：权重可在多 Agent / 应用间共享一份，KV 是每会话私有，N 个会话的 KV 线性放大。1.2 与 2.2 一致：A16 综述也把「权重 + KV + 激活」增长作为主轴（见仓库 `surveys/agent-era-memory-workload-CN.md`、`advanced/A16f-端侧KV-Cache管理方案.md`）。

总判断：**不存在「谁恒大」，要看模型架构；但对立项最有用的表述是：权重是静态、可共享、可映射、可分层的；KV 是动态、私有、随上下文线性增长、不可从文件重建。** 因此 KT3 / 稀疏权重分层面向「首次占用」与「冷加载」，KT2-KV 面向「增量与多会话」。2027 年随模型走向 MoE + 混合注意力，常驻字节会更偏向权重，KV 问题集中在稠密小模型与长会话上。

### 2.2.2 当代系统在模型内存上的卡点

> 平台术语区分：Android 的 LMKD 与 Jetsam（iOS）不同；zram 与 iOS 压缩内存不同；本节只写能核实的。

- **配额与常驻（Android）**：已有分析认为 KV / dma-buf / NPU scratch 属于被钉住的缓冲，位于普通 LRU 与回收路径之外，会提前触发 lmkd（出处为仓库内 A16 综述，其外部来源见该文）。本轮未找到公开的「Android 上模型进程被 lmkd 杀死率」数据，未找到公开资料。
- **iOS**：「Paging the Experts」给出 iPhone 上 35B-A3B 模型进程内存峰值 1.87–2.73 GiB，并发生热降频停止 [12]。iOS 单进程内存上限 / Jetsam 阈值没有在本轮检索，待核实。
- **NPU 路径**：QNN context binary 单 SoC、需预编译；HTP 单会话权重上限迫使大模型被切成多上下文 [29]；缓冲需注册并映射到 NPU 虚拟地址空间（扩散 LLM 论文，经摘要）[37]；CMA 8GB 分配约 6.44 s 对比 mmap 0.56 s [31]，说明「连续物理内存 + 长期钉住」代价明显。
- **加载 IO**：UFS 4.x 顺序读常报约 5.8 GB/s [32]。估算：2.5 GB（E4B 移动端）[5] 在理想顺序读下约 0.43 s，14.4 GB 级权重约 2.5 s；真实冷加载含页缺失、反量化 / 重排、NPU 注册，必然更久；本轮未找到公开的冷 / 热加载时间实测，未找到公开资料。
- **专家换入带宽估算**：Qwen3-30B-A3B 单专家参数 = 3×2048×768 = 4.72M；Q4 约 0.61 B/参数（4.85 bit）→ 约 2.9 MB；每 token 最坏 8 专家×48 层 = 384 次，约 1.1 GB。在 5.8 GB/s 顺序读峰值下，0% 命中时上限约 5 tokens/s；随机读实际带宽更低（估算，且未计预取重叠）。命中率 80% 时 IO 量降至约 1/5，对应上限约 25 tokens/s。
- **HarmonyOS**：本轮未找到模型加载、权重映射、MindSpore Lite / HiAI Foundation 加载机制的公开资料，未找到公开资料。
- **量化权重可压缩性**：本轮未检索，待核实。

### 对立项的启示（2.2）
- 支撑 KT2-MoE：35B 级 MoE 在 12–16GB 机型必须分层，命中率悬崖证明需要策略。
- 支撑 KT3：钉住的连续内存代价高，mmap 路径快一个数量级（FlexServe 数字待核实）。
- 支撑「模型内存一等公民」：权重、KV、NPU 缓冲目前分属不同记账域。

---

## 第四部分（M3 范围）关键技术

## KT2-A MoE 专家缓存（含稀疏权重分层）

### 1. 要解决的问题
- 现状：35B 级 MoE（Qwen3.5-35B-A3B、Gemma 4 26B A4B）Q4 权重 14–21 GB（官方 / 估算）[5][9]，手机放不下，需放 UFS 并按需换入。
- 代价：iPhone 实测 512 MiB LRU 命中率 0%、576 MiB 才到 38.58% [12]；按上文估算，0% 命中时每 token 约 1.1 GB IO，解码上限约 5 tokens/s（估算）。命中率直接决定能否用。

### 2. 业界做法扫描
见 1.2 表格：LLM in a flash（2023）、EdgeMoE（2023 / 2025）、PowerInfer-2（2024）、Pre-gated MoE（ISCA 2024）、MoE-Infinity（2024）、AdapMoE（ICCAD 2024）、HOBBIT（2024）、ProMoE（2024）、FlashMoE（2026）、EStream（2026-09）、Paging the Experts（2026-09）。共同局限：多在 GPU / 桌面 / 嵌入式验证；手机侧只有 PowerInfer-2、EStream、iPhone 实测；绝对 tokens/s 的手机数据稀少。

### 3. 技术难点
1. **难点一：命中率对容量与负载极敏感。** 难在小缓存下 LRU 会在循环式访问上完全失效（0%）[12]，且 Agent 场景的路由分布随任务切换漂移。怎么破：对「专家 / PLE / 神经元簇」统一建热度模型，做多策略（LRU、频率、学习型）在线选择，缓存放在 Agent 内存组件，由系统记账。关键突破：从固定策略变成按负载在线选策略的缓存。
2. **难点二：预取要在 UFS 带宽内按时到。** 难在专家 2–3 MB 级随机读，且前层门控才能预知后层。怎么破：用跨层预测（EdgeMoE / ProMoE / AdapMoE 路线 [15][19][21]）加按簇打包的存储布局（行列捆绑 [14]），预取在 IO 调度层与 KT3 共用队列。关键突破：预测与布局联合设计，让 IO 变大且可预知。
3. **难点三：精度与容量折中。** 难在低精度替换（HOBBIT）或减少激活专家（AdapMoE）会损失质量。怎么破：缺失时降级为低位宽专家作为兜底，质量门限由评估集约束。关键突破：缺失时不阻塞、降级继续。

### 4. 机制架构
- **感知 / 建模**：专家访问轨迹采集（层、专家、时间）；热度与转移概率模型；UFS 带宽与空闲内存感知。
- **决策**：分层放置（DRAM / 压缩区 / UFS）；预取预测；淘汰策略选择；缺失降级决策。
- **执行**：权重页池（与 KT3 的映射共用）；异步预取线程；低位宽副本换入；NPU 可见 arena（参考 EStream 固定 arena [11]）。
- **反馈**：命中率、预取准确率与提前量（参考 ProMoE GoodPred 概念 [21]）、tokens/s、热状态；回写热度模型与策略选择。

### 5. 目标与度量
- 指标：专家缓存命中率；decode tokens/s；TTFT；峰值常驻内存。
- 基线：LRU 固定容量（iPhone 数据 576 MiB 时 38.58% [12]）；llama.cpp mmap 默认路径。
- 目标（建议，依据：FlashMoE 对 LRU / LFU 最高 +51% 命中率 [13]、ProMoE decode 1.34–1.79 倍 [21]）：同容量下命中率相对 LRU 提升 ≥30%；decode 较 mmap 基线 ≥1.5 倍。测试条件：旗舰机、UFS 4.x、Q4 的 30B 级 A3B 模型、多种 Agent 任务轨迹。

### 6. 风险与待核实
- 2027 年 MoE 主流度判断为中置信度；系统级模型走 PLE 而非 MoE 的可能性不小。
- 大多数论文为预印本或作者自测；手机侧缺公开可复现基线。
- 热降频（iPhone 实测出现停止事件 [12]）可能限制长时间解码。
- 质量折损（低位宽替换、减少激活专家）需评估。

### 7. PPT 素材卡
- **挑战**
  - 容量放不下：35B 级 MoE Q4 约 21GB（估算），16GB 机型无法常驻
  - 命中率悬崖：iPhone 上 512MiB LRU 命中率 0%
  - 换入带宽：未命中时每 token 约 1.1GB IO（估算）
- **目标**（≤44 字）：把稀疏权重纳入系统分层，提升专家命中率，在有限内存下跑大模型。**量化目标**：命中率较 LRU +30%
- **技术难题**
  - 难题一：自适应缓存策略
    - 热度建模：统一建模专家、PLE、神经元簇的热度
    - 策略选择：按负载在线切换替换策略
    - 关键突破：按负载选策略
  - 难题二：预测式预取
    - 跨层预测：前层门控预测后层专家
    - 布局打包：按簇存储，加大单次读取
    - 关键突破：预测与布局联合
  - 难题三：缺失降级
    - 低位宽兜底：缺失时换入低精度副本
    - 质量门限：评估集约束折损
    - 关键突破：缺失不阻塞
- **架构四段**：感知（访问轨迹、热度模型、带宽感知）→ 决策（分层放置、预取预测、策略选择）→ 执行（权重页池、异步预取、NPU arena）→ 反馈（命中率、预取准确率、tokens/s）

---

## KT2-B KV Cache 回收与压缩

### 1. 要解决的问题
- 现状：KV 随上下文线性增长且不可由文件重建。Qwen3-4B fp16 在 32K 为 4.5 GiB，约为其 Q4 权重（约 2.4 GB）的 1.9 倍（估算）；多会话 KV 线性放大。
- 代价：KV 常驻在被钉住的缓冲中，OS 回收不掉，易触发 lmkd 提前杀进程（见 A16 综述）。本轮未找到手机上 KV 占用导致 OOM 的公开实测，未找到公开资料。

### 2. 业界做法扫描
- 量化：KIVI（ICML 2024）2-bit，Llama-2-7B 峰值内存降 2.6 倍，吞吐 2.35–3.47 倍 [26]。局限：长 Agent 轨迹和工具调用下的精度漂移未充分刻画（见仓库综述）。
- 淘汰：H2O（NeurIPS 2023）、StreamingLLM（ICLR 2024）、SnapKV（NeurIPS 2024），会议为记忆所知，待核实；局限：丢 token 可能破坏工具调用所需的精确引用。
- 架构层缩减：Apple 2025 端侧 3B 模型层间 KV 共享，KV -37.5%，KV 8 bit [22]；Qwen3.5 混合线性注意力，每 token 仅 20 KiB [9]。局限：由模型决定，OS 无法后加。
- 系统层换出与分块：LLMS（2024-03）分块压缩、LCTRU 淘汰、IO 与重算流水 [23]；MNN-LLM（2025）DRAM 溢出到 Flash 并预取 [24]；KVSwap（2025-11）全量 KV 放磁盘、元数据预测预载 [25]。局限：Flash 带宽墙；KVSwap 未给倍数。
- 前缀 KV 的复用与持久化：本轮未检索到手机端公开系统，待核实。

### 3. 技术难点
1. **难点一：KV 不可回收且被钉住。** 难在 KV 在 dma-buf / NPU 可见缓冲中，不在 LRU 上。怎么破：把 KV 切成块（参考 LLMS 16 token 块 [23]）纳入统一记账，块可压缩、可换出、可丢弃重算。关键突破：KV 块成为可回收对象。
2. **难点二：压缩的质量与场景耦合。** 难在 2-bit 与淘汰对工具调用 / 长推理的影响未知。怎么破：按块的压缩容忍度分级（LLMS 的 tolerance-aware 思路 [23]），关键块保高精度，仅对系统提示、旧工具输出等低敏感块用低位宽。关键突破：按块容忍度差异化压缩。
3. **难点三：闪存换出要掩盖延迟。** 难在 UFS 带宽比 DRAM 低一个数量级（MNN-LLM 引 LPDDR5X 约 58 GB/s 对 UFS 4.0 约 0.45–3 GB/s [24]）。怎么破：只换出长期不被注意的块，用元数据预测预载（KVSwap [25]），部分块选重算而非读取（LLMS [23]）。关键突破：IO 与重算择优流水。

### 4. 机制架构
- **感知 / 建模**：每块注意力得分与访问时间；块的压缩容忍度；会话优先级（前台应用 / Agent）；内存压力信号。
- **决策**：保留 / 压缩 / 换出 / 丢弃重算的四选一；跨会话前缀共享判断。
- **执行**：块池分配；量化 / 反量化 kernel；UFS 写出与预载；前缀块共享映射。
- **反馈**：TTFT、解码速度、质量回归（工具调用成功率）、命中与重算比例。

### 5. 目标与度量
- 指标：32K 上下文 KV 常驻量；恢复会话 TTFT；工具调用成功率；decode tokens/s。
- 基线：fp16 全驻留 KV。
- 目标（建议，依据：KIVI 2.6 倍峰值内存降 [26]、Apple 层间共享 -37.5% [22]）：32K 场景 KV 常驻量 ≥2.5 倍压缩，任务质量回归 ≤1 个百分点（阈值为建议值，需按 Agent 任务集校准）；会话切回 TTFT 相对全量重算降低 ≥50%（待实测）。

### 6. 风险与待核实
- 有损压缩在 Agent 轨迹上的质量风险未收口（仓库综述已指出）。
- 模型趋向混合注意力，KV 收益会缩小，投入需与模型路线对齐。
- 手机上前缀 KV 持久化、KV 换出的实测数据缺失。

### 7. PPT 素材卡
- **挑战**
  - 钉住不可回收：KV 位于回收路径之外，易提前触发查杀
  - 随上下文增长：4B 稠密模型 32K 的 KV 约 4.5GiB（估算）
  - 压缩有质量风险：2-bit 在工具调用上未充分验证
- **目标**（≤44 字）：让 KV 成为可记账、可压缩、可换出的系统对象，降低常驻量并加快会话恢复。**量化目标**：KV 常驻压缩 ≥2.5 倍
- **技术难题**
  - 难题一：KV 块化记账
    - 块池：按 16 token 级切块统一分配
    - 回收接口：块可压缩、换出或丢弃
    - 关键突破：KV 可回收
  - 难题二：容忍度分级压缩
    - 敏感度评估：按块评估压缩容忍度
    - 差异精度：关键块高精度、旧块低位宽
    - 关键突破：按块差异压缩
  - 难题三：换出与重算择优
    - 预载预测：元数据预测需要的块
    - 重算备选：带宽不足时选重算
    - 关键突破：IO 重算择优
- **架构四段**：感知（块注意力、压缩容忍度、会话优先级）→ 决策（保留压缩换出、前缀共享）→ 执行（块池、量化核、UFS 预载）→ 反馈（TTFT、质量回归、重算比例）

---

## KT3 模型加载 / 卸载提速与零拷贝映射

### 1. 要解决的问题
- 现状：权重在文件、页缓存、框架私有缓冲、NPU 缓冲间多份拷贝；NPU 路径需预编译二进制、反量化重排与缓冲注册；大块连续内存分配慢（8GB CMA 约 6.44 s vs mmap 0.56 s，待核实 [31]）。
- 代价：理想顺序读下 2.5 GB 约 0.43 s、14.4 GB 约 2.5 s（5.8 GB/s，估算）；Agent 叠加场景下模型被频繁换入换出，冷加载直接影响首次响应。真实冷加载时间的公开数据：未找到公开资料。

### 2. 业界做法扫描
- llama.cpp mmap + 新的 `-lm` 加载模式（auto / mmap / mlock / mmap+mlock / dio）[27]：页缓存复用，多进程共享一份；局限：mmap 下常驻内存数字易误导，压力下页被逐出后再缺页。
- ExecuTorch .pte 页对齐数据段 + NamedDataMap / 程序数据分离（RFC 与 LoRA 共享示例）[28]：多变体共享基座权重；局限：当前版本两个 .pte 不共享权重（RFC 动机），落地状态待核实。
- LiteRT-LM：首次加载优化并缓存，后续更快；Gemma 4 移动端 E2B 1.1 GB、E4B 2.5 GB [5][22b]；局限：无公开加载时间。
- Qualcomm QNN context binary / Genie 多 binary 分段 / 权重共享 / uDMA 模式 [29]；局限：单 SoC、会话数与权重上限、需预编译。
- MNN-LLM（2025）DRAM-Flash 混合存储，Embedding 放 Flash 省约 15% DRAM [24]。
- T-MAN（2025-11）NPU 只保留一份权重、统一查表 [30]。
- Core ML、MindSpore Lite / HiAI Foundation：本轮未检索，未找到公开资料（待核实）。
- 量化权重可压缩性：本轮未检索，待核实。

### 3. 技术难点
1. **难点一：NPU 路径无法直接 mmap 文件页。** 难在 NPU 需要 IOMMU 映射、缓冲注册，且往往要求特定布局（反量化重排）和物理连续 / 长期钉住（CMA 慢，钉住不可回收 [31][37]）。怎么破：离线把权重转换成 NPU 友好的页对齐布局，运行时由内核 / 驱动把文件页经 dma-buf 暴露给 NPU 的 IOMMU，页可按需缺页并可被回收。关键突破：文件页直接作为 NPU 可见内存（具体内核机制待验证）。
2. **难点二：IO 利用率。** 难在缺页是 4KB 级随机请求，UFS 吃不满带宽（5.8 GB/s 为顺序读标称 [32]）。怎么破：按层 / 专家顺序打包，按调度器序预读大块，和 KT2 预取共享 IO 队列。关键突破：顺序大块 + 预读，把 IO 打满。
3. **难点三：多框架多份权重。** 难在同一基座被多 Agent、多 LoRA、CPU / NPU 各一份。怎么破：以权重内容为键的共享映射（对应 ExecuTorch 数据分离思路 [28]、QNN 权重共享 [29]、T-MAN 单份权重 [30]），由内存系统统一记账。关键突破：权重按内容共享。

### 4. 机制架构
- **感知 / 建模**：模型清单与布局元数据；各会话所需层 / 专家；UFS 带宽与内存压力。
- **决策**：加载顺序与预读窗口；常驻 / 可回收划分；卸载时机（回收 vs 保留映射）。
- **执行**：页对齐权重文件格式；文件页到 NPU IOMMU 的映射；批量预读；共享映射。
- **反馈**：冷 / 热加载时间；缺页次数与 IO 大小分布；映射命中率；回收后再缺页率。

### 5. 目标与度量
- 指标：冷加载时间（至首 token）；热加载时间；加载期间峰值内存；重复拷贝数。
- 基线：当前框架默认路径（llama.cpp mmap、QNN context binary 加载）；基线数值需自测（无公开数据）。
- 目标（建议）：冷加载接近 UFS 顺序读理论值的 60%–70%（目标比例为建议值，需依据实测瓶颈修正）；NPU 路径权重额外拷贝降为 0 份；峰值内存较多份拷贝降低约一份权重大小。

### 6. 风险与待核实
- NPU 驱动与 IOMMU 的文件页映射是否可行，取决于 SoC 厂商驱动，需和厂商确认。
- 缺页式加载在内存压力下可能抖动，需与 KT1 回收策略协同。
- 公开的加载时间数据缺失，立项基线要自己测。
- 厂商私有格式（QNN、HiAI）使通用方案受限。

### 7. PPT 素材卡
- **挑战**
  - 多份拷贝：权重在页缓存与 NPU 缓冲间重复
  - 钉住代价高：8GB 连续分配约 6.4s，对比 mmap 0.56s（待核实）
  - IO 吃不满：4KB 缺页难以打满 UFS 5.8GB/s
- **目标**（≤44 字）：权重以文件页直接映射给各算力，缩短冷加载、去除重复拷贝，并可回收。**量化目标**：NPU 路径额外拷贝为 0
- **技术难题**
  - 难题一：NPU 文件映射
    - 布局转换：离线转为页对齐 NPU 友好布局
    - IOMMU 映射：文件页经 dma-buf 映射
    - 关键突破：文件页即 NPU 内存
  - 难题二：顺序化大块 IO
    - 打包预读：按层或专家顺序打包
    - 共享队列：与专家预取共用 IO 调度
    - 关键突破：大块顺序读
  - 难题三：权重按内容共享
    - 共享映射：多会话与 LoRA 共用基座
    - 统一记账：映射页计入模型内存
    - 关键突破：一份权重多方用
- **架构四段**：感知（模型清单、层需求、UFS 带宽）→ 决策（加载顺序、预读窗口、回收划分）→ 执行（页对齐格式、IOMMU 映射、批量预读）→ 反馈（冷热加载时间、缺页分布、再缺页率）

---

## 参考资料

> 访问日期均为 2026-11-03。发布日期按来源页面可见信息，未知处写「日期未核」。

1. 本仓库：surveys/agent-era-memory-workload-CN.md、advanced/A16f-端侧KV-Cache管理方案.md、advanced/A16i-端侧UFS-HBF增强.md（内部综述，仅读标题与相关段落）
5. Gemma 4 官方文档：https://ai.google.dev/gemma/docs/core（Gemma 4 发布日期报道为 2026-04-02）
6. Gemini Nano 4 报道：https://9to5google.com/2026/04/02/gemini-nano-4-android/（2026-04-02，二手，官方博客未直接取到）
7. Gemma 3n 官方概览：https://ai.google.dev/gemma/docs/gemma-3n（日期未核）
8. Qwen3.5 Small 报道：https://gigazine.net/gsc_news/en/20260303-qwen-3-5-small（2026-03-03，二手）
9. Qwen3.5-35B-A3B config：https://huggingface.co/Qwen/Qwen3.5-35B-A3B/raw/main/config.json（日期未核）
10. MobileMoE：https://neurips.cc/virtual/2026/poster/150777（NeurIPS 2026，论文原文未取到）
11. EStream：https://arxiv.org/abs/2609.06551（2026-09-06）
12. Paging the Experts：https://arxiv.org/abs/2609.29032（2026-09-24）
13. FlashMoE：https://arxiv.org/abs/2601.17063（2026-01-22，v2 2026-10-05）
14. LLM in a flash：https://arxiv.org/abs/2312.11514（2023-12）
15. EdgeMoE：https://arxiv.org/abs/2308.14352（2023-08-28，v2 2025-03-07）
16. PowerInfer-2：https://arxiv.org/abs/2406.06282（2024-06，v3 2024-12）
17. Pre-gated MoE：https://arxiv.org/abs/2308.12066（ISCA 2024）
18. MoE-Infinity：https://arxiv.org/abs/2401.14361（2024-01-25，v3 2025-03-12）
19. AdapMoE：https://arxiv.org/abs/2408.10284（2024-08-19，ICCAD 2024）
20. HOBBIT：https://arxiv.org/abs/2411.01433（2024-11-05）
21. ProMoE：https://arxiv.org/abs/2410.22134（2024-10）
22. Apple Foundation Models Tech Report 2025：https://arxiv.org/abs/2507.13575（2025-07）
22b. LiteRT-LM 概览：https://ai.google.dev/edge/litert-lm/overview（日期未核；Gemma 4 模型卡数字来自搜索摘要，待核实）
23. LLMS：https://arxiv.org/abs/2403.11805（2024-03-18）
24. MNN-LLM：https://arxiv.org/abs/2506.10443（2025）
25. KVSwap：https://arxiv.org/abs/2511.11907（2025-11-14，v2 2025-12-11）
26. KIVI：https://arxiv.org/abs/2402.02750（ICML 2024）
27. llama.cpp 加载标志说明（二手博客）：https://dev.to/multigrid/llamacpps-mmap-and-mlock-flags-explained-43fp（日期未核）
28. ExecuTorch pte 格式与数据分离 RFC：https://github.com/pytorch/executorch/issues/8118（及 #8122；日期未核）
29. Qualcomm QNN 权重共享：https://docs.qualcomm.com/doc/KBA-250306025001/KBA-250306025001_REV_1_QNN_Weight_Sharing_Feature.pdf；ORT-QNN 2.1.0：https://github.com/onnxruntime/onnxruntime-qnn/releases/tag/v2.1.0
30. T-MAN：https://arxiv.org/abs/2511.11248（2025-11-14）
31. FlexServe：https://www.alphaxiv.org/abs/2603.09046（2026-03，仅摘要）
32. JEDEC UFS 5.0：https://www.businesswire.com/news/home/20260226710161/en/JEDEC-Announces-Updates-to-Universal-Flash-Storage-UFS-and-Memory-Interface-Standards（2026-02-26）；手机时间线：https://heise.de/-10744571
33. WWDC26 二手汇总：https://callstack.com/blog/on-device-ai-after-wwdc-2026-whats-new；https://mer.vin/2026/06/apple-wwdc26-siri-ai-and-gemini-backed-foundation-models-on-device-and-private-cloud-compute/（2026-06，互相矛盾）
34. Qwen3-4B config：https://huggingface.co/Qwen/Qwen3-4B/raw/main/config.json
35. Qwen3-30B-A3B config：https://huggingface.co/Qwen/Qwen3-30B-A3B/raw/main/config.json
36. LangWatch 上下文研究：https://langwatch.ai/research/finding-the-optimal-context-window（日期未核，单人案例）
37. 移动 NPU 扩散 LLM：https://arxiv.org/pdf/2606.13740（仅摘要）

## 待核实清单

1. PowerInfer-2、EdgeMoE、HOBBIT、ProMoE、MoE-Infinity、LLM in a flash 的正式发表会议（本轮仅核到 arXiv）；LLM in a flash 是否为 ACL 2024。
2. H2O（NeurIPS 2023）、StreamingLLM（ICLR 2024）、SnapKV（NeurIPS 2024）会议年份未联网复核；MoE-Infinity 具体加速数字未取。
3. Gemini Nano 4 的官方发布细节与设备内存要求（现有为二手）；Gemma 4 E2B/E4B 的 KV 相关 config 未取（gated），故表中未纳入。
4. Apple WWDC26 端侧模型是否为稀疏 / MoE、参数规模、上下文（来源互相矛盾，且无官方文档）。
5. MobileMoE 的原文与手机型号、绝对 tokens/s；EStream、iPhone 论文的绝对吞吐。
6. FlexServe 的 CMA 6.44 s / mmap 0.56 s 数字（仅摘要）。
7. MNN-LLM 关于 Flash 中 KV「3072K」的表述原文。
8. QNN HTP 单会话权重上限与约 7 个并发会话的限制（社区模型卡）；dma-buf / spill-fill 机制未找到公开资料。
9. 各框架（llama.cpp、ExecuTorch、LiteRT、Core ML、MNN、MindSpore Lite / HiAI Foundation）冷 / 热加载时间实测，鸿蒙侧加载机制：未找到公开资料。
10. 量化权重可压缩性、前缀 KV 复用与持久化在手机端的公开系统、Android lmkd / iOS Jetsam 对模型进程的实际阈值：本轮未检索。
11. Q4 权重估算采用 4.85 bit / weight 与总参数取值，需用实际量化文件大小校正；总参数 35B / 30.5B / 4.0B 未在 config 中核对。

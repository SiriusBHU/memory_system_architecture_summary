# D2 基础能力洞察：端侧模型、推理引擎、内核上游、硬件与产业信号（2023–2026，外推 2027）

> 检索日期：2026-11-04。用途：为「2027 Agent OS 立项」汇报提供「技术演进趋势 + 数据 + 判断」素材。
> 与 M2（系统内存）、M3（模型内存）笔记的关系：已有机制不重复，本文把它们串成演进脉络并补数据表。
> 标注约定：「估算」= 本文用公开 config 或公开数字自行推算并写出算式；「待核实」= 单一或二手来源，或内部不一致；「未找到公开资料」= 本轮检索无结果。判断一律标「判断」。
> KV 每 token 字节数 = 2（K 与 V）× 参与缓存的全注意力层数 × KV 头数 × head_dim × 字节数，默认 fp16（2 字节）。

---

## 要点摘要（12 条）

1. 端侧系统模型的「常驻权重」从 2023 年底的约 1.6 GB（Gemini Nano-2，3.25B × 4 bit，估算）涨到 2026 年的 4.2–5.9 GB（Gemini Nano 4 Fast/Full，二手报道），约 2.7 年增长 2.6–3.7 倍，折合年增长约 43%–63%（估算，算式见 1.3）；同期手机平均 DRAM 只从 7.4 GB 涨到 8.4 GB（+13.5%，Counterpoint）。
2. Gemini Nano 4 两个版本据报道「至少需要 12 GB RAM 才能加载」，Full 版 5.9 GB 占 12 GB 机型 DRAM 的约 49%（5.9/12，二手来源，待核实）。
3. 每 token KV 在两年内大幅下降：Qwen3-4B 为 144 KiB，Gemma 4 E2B 估算仅 6–14 KiB，约 10–24 倍差距；Qwen3.5-4B 为 32 KiB。原因是滑窗注意力、层间 KV 共享、线性注意力混合（来自公开 config）。
4. 架构从稠密走向稀疏：Gemma 3n 的 PLE 使 E2B 有效加载约 1.91B（标准执行超过 5B）；Gemma 4 增加 26B A4B MoE（Q4_0 约 14.4 GB）；Apple 2026 传闻有 20B 稀疏模型（仅二手来源）。
5. 8 个主流推理引擎中，只有「系统托管」路线（Android AICore、Apple Foundation Models）能让多个应用共享同一份权重；其余引擎的权重是应用私有的，OS 看到的只是进程内存或文件页，且 KV 与 NPU 缓冲不在 LRU 回收范围内。
6. iOS 开发者论坛实测报告：iPhone 16 Pro Max（8 GB）与 iPhone 17 Pro Max（12 GB）的单应用内存上限都约为 6144 MB（非官方，待核实），说明 12 GB 机型对第三方模型进程的可用度并未随 DRAM 线性增加。
7. 内核上游：per-VMA lock 6.4 起步（仅匿名页），6.6 页面列出文件缺页与 swap 缺页（版本归属见 3.1 待核实）；arm64 contpte 6.9；swap table 第一阶段 6.18，且 Android 17 对应 android17-6.18。
8. Android 16KB 页：Android 15 起支持，官方数据为内存压力下应用启动平均快 3.16%（最多 30%）、启动功耗降 4.56%、整机启动快 8%（约 950 ms）；Google Play 要求截止日期现页面写作 2027-02-01。
9. 硬件：Samsung UFS 5.0 顺序读 10.8 GB/s（UFS 4.1 为 4.3 GB/s，约 2.5 倍），2026 Q4 量产；LPDDR6 数据率 10.667–14.4 Gbps，SK hynix 2026 下半年量产、Samsung 已发布，但截至本文未确认已有出货手机。
10. 核层面：Arm 公开资料显示 Cortex-A720/A725/X925 实现 SPE（来自 Linux 补丁，M2），C1-Ultra TRM 摘要出现 SPE TLB；但手机 SoC 是否向 Linux 开放 SPE、NPU 的 SMMU/SVA 是否可用：未找到公开资料。
11. 产业信号：Counterpoint 2026-02：12 GB 在 2026 年成为高端标配，内存占 iPhone 17 Pro Max BoM 超 10%（2020 年 iPhone 12 Pro Max 为 8%），旗舰可超 20%；容量涨价与模型内存需求在 2026–2027 年同时向上，形成「需求曲线与供给曲线交叉」。
12. 华为 2026-04 发布的 HyperSpace Memory 宣称 12 GB 物理内存达到 16 GB 的后台保活效果，压缩率提升最多 69%（TrendForce 转述，无技术细节），说明国内厂商把「系统层容量虚拟化」作为核心卖点，但模型内存是否纳入其中：未找到公开资料。

---

## 1 端侧模型的演进与内存需求曲线

### 1.1 总表

说明：表中「端侧常驻权重」按各来源给出的口径，口径并不统一（有的是 LiteRT-LM 移动端内存，有的是文件大小，有的是我按位宽估算），逐行标注。「KV/token」按 config 估算，表后给算式。

| 模型 | 发布时间 | 总参数 / 激活 | 量化 | 端侧常驻权重 | 上下文 | KV/token（fp16，估算） | 搭载设备 | 来源与状态 |
|---|---|---|---|---|---|---|---|---|
| Gemini Nano-1 | 2023-12 | 约 1.8B | 4 bit | 约 0.9 GB（估算：1.8B×0.5 B） | 未找到公开资料 | 未找到 config | 低内存设备目标 | 二手 wiki 转述 Gemini 1.0 技术报告，参数量官方未披露，待核实 [R1] |
| Gemini Nano-2 | 2023-12 | 约 3.25B | 4 bit | 约 1.6 GB（估算：3.25B×0.5 B） | 未找到公开资料 | 未找到 config | Pixel 8 Pro（12 GB）首发；Pixel 8（8 GB）后补 | 同上 [R1][R2] |
| Gemini Nano v3 | 2025-08（Pixel 10） | 约 4B | 未找到 | 未找到 | 未找到 | 未找到 | Pixel 10（Tensor G5） | 日媒转述 Google 硅团队产品经理发言，采用 MatFormer，单一二手，待核实 [R3] |
| Gemini Nano 4 | 2026-04 预览，2026-08 起上机 | Fast≈2B（基于 Gemma 4 E2B），Full≈4B（基于 E4B） | 未找到 | Fast 4.2 GB / Full 5.9 GB（二手，口径不明，与 Gemma 4 官方移动端 1.1/2.5 GB 差距大） | 128K（来自 Gemma 4） | 见下 Gemma 4 | Pixel 11 系、Galaxy Z Flip8/Fold8；至少 12 GB RAM | 官方博客只说「后续上机」；设备与 RAM 要求来自二手文章转述 Google 文档，待核实 [R4][R5] |
| Apple AFM-on-device 2024 | 2024-06 | 约 3B | 混合 2/4 bit，平均 3.7 bit/权重 | 约 1.4 GB（估算：3B×3.7/8） | 未找到 | 未找到 | iPhone 15 Pro（8 GB）及以上 | Apple 官方博客：词表 49K、GQA、iPhone 15 Pro 每 prompt token 约 0.6 ms、30 tok/s [R6] |
| Apple 端侧模型 2025 | 2025-06/07 | 约 3B | 权重 2 bit QAT，embedding 4 bit，KV 8 bit | 低于 0.75 GB 的权重部分（估算：3B×2/8），embedding 另计 | 官方未给；二手称 8192 | 层间共享使 KV 降 37.5% | iPhone（Apple Intelligence 设备） | Apple 官方博客与技术报告：两块按 5:3 切分，第二块共享第一块末层 KV [R7] |
| Apple AFM 3（2026） | 2026-06 WWDC26 | Core 约 3B；Core Advanced 20B 总、同时激活 1–4B | 未找到 | 未找到 | 8192（二手） | 未找到 | 仅最高端机型（二手） | 全部为二手博客，来源之间对权重存放（NAND vs DRAM）说法矛盾，无 Apple 官方文档，待核实 [R8] |
| Gemma 3n E2B | 2025（月份待核实） | 原始 >5B，有效 1.91B | 未找到 | 官方称约 2 GB 内存（PLE 缓存到快速存储）；LiteRT-LM 文件 2965 MB | 32768（config） | 估算 8 KiB（全注意力层）+ 固定约 16 MiB（滑窗） | 手机/平板 | 官方文档与 HF 镜像 config（30 层，2 KV 头，head_dim 256，24 滑窗层/6 全注意力层，滑窗 512，后 10 层共享 KV）[R9][R10] |
| Gemma 3n E4B | 同上 | 有效约 4B | 未找到 | 约 3 GB；文件 4235 MB | 同上 | 本轮未取 config | 同上 | 官方文档与 LiteRT-LM 页 [R9][R11] |
| Gemma 4 E2B | 2026-04-02 | 有效 2B | 移动端（LiteRT-LM） | 1.1 GB（纯文本 0.84 GB）；文件 2583 MB；峰值 CPU 内存 1733 MB（S26 Ultra CPU 后端） | 128K | 估算 6–14 KiB（见算式） | 手机 | 官方文档 core 页；config 来自 HF 镜像（35 层，1 KV 头，head_dim 256/全局 512，28 滑窗/7 全注意力，后 20 层共享 KV）[R12][R11][R10] |
| Gemma 4 E4B | 同上 | 有效 4B | 移动端 | 2.5 GB（纯文本 2.2 GB）；文件 3654 MB | 128K | 本轮未取 config | 手机 | [R12][R11] |
| Gemma 4 26B A4B | 同上 | 26B / 激活 4B（MoE） | Q4_0 | 14.4 GB（官方表） | 256K | 本轮未取 config | 非手机常驻 | [R12] |
| Qwen3-0.6B | 2025-04（记忆，待核实） | 0.6B | 未说明 | 文件 586 MB（LiteRT-LM 页） | 40960 | 112 KiB | 通用 | HF 官方 config：28 层，8 KV 头，head_dim 128 [R13][R11] |
| Qwen3-1.7B | 同上 | 1.7B | 未说明 | 估算 Q4 约 1.0 GB（1.7×4.85/8，4.85 为 Q4_K_M 假设值） | 40960 | 112 KiB | 通用 | 同上 [R13] |
| Qwen3-4B | 同上 | 4B | 未说明 | 估算 Q4 约 2.4 GB | 40960 | 144 KiB（36 层，8 KV 头，128） | 通用 | M3 已核 [M3] |
| Qwen3.5-2B | 2026-03（二手） | 2B | 未说明 | 估算 Q4 约 1.2 GB | 262144 | 12 KiB（18 线性层 + 6 全注意力层，2 KV 头，256） | 通用 | HF 官方 config；发布日期 M3 来自 gigazine 二手 [R14] |
| Qwen3.5-4B / 9B | 同上 | 4B / 9B | 未说明 | 估算 Q4 约 2.4 / 5.5 GB | 262144 | 32 KiB（8 全注意力层，4 KV 头，256；9B 同） | 通用 | HF 官方 config [R14] |
| Llama 3.2 1B | 2024-09（记忆，待核实） | 1B | 未说明 | 未找到 | 131072 | 32 KiB（16 层，8 KV 头，64） | 通用 | HF 镜像 config [R15] |
| Llama 3.2 3B | 同上 | 3B | 未说明 | 未找到 | 131072 | 112 KiB（28 层，8 KV 头，128） | 通用 | HF 镜像 config [R15] |
| Phi-4-mini | 2025（月份待核实） | 3.8B | 未说明 | 文件 3906 MB（LiteRT-LM 页） | 131072 | 128 KiB（32 层，8 KV 头，head_dim=3072/24=128） | 通用 | HF 官方 config，词表 200064 [R16][R11] |
| MiniCPM4-0.5B / 8B | 2025-06（arXiv 编号推断） | 0.5B / 8B | 未说明 | 未找到 | 32768 | 12 KiB / 32 KiB | 端侧（论文定位） | HF 官方 config（0.5B：24 层，2 KV 头，head_dim 64；8B：32 层，2 KV 头，128）；InfLLM v2 稀疏注意力降低长上下文计算访存 [R17] |
| vivo BlueLM-V-3B / 蓝心 3B | 2024-11（arXiv） | LLM 2.7B + ViT 0.4B | 4 bit | 蓝心 3B 官方口径 1.4 GB，来自第三方站点，待核实 | 未找到 | 未找到 | 天玑 9300 上 24.4 tok/s | arXiv 2411.10640 [R18] |
| 荣耀 MagicAgent / 小米 MiMo | — | — | — | 未找到公开资料 | — | — | — | 一份券商研报仅把 MagicLM 7B 归入 3–9B 档、MiMo-7B 归入 AI PC 档，未给内存 [R19] |

KV 算式（估算）：
- Qwen3-0.6B / 1.7B：2×28×8×128×2 = 114,688 B = 112 KiB。Llama 3.2 3B 同算式。Llama 3.2 1B：2×16×8×64×2 = 32 KiB。
- Phi-4-mini：2×32×8×128×2 = 128 KiB。
- Qwen3.5-4B：2×8×4×256×2 = 32 KiB；Qwen3.5-2B：2×6×2×256×2 = 12 KiB（线性注意力层为固定状态，不随上下文增长，未计）。
- MiniCPM4-0.5B：2×24×2×64×2 = 12 KiB；8B：2×32×2×128×2 = 32 KiB。
- Gemma 3n E2B：全注意力层中，前 20 个非共享层里含 4 层（按每 5 层 1 个全注意力的排布，位置 4/9/14/19），2×4×2×256×2 = 8 KiB/token；滑窗层 16 层×512 token×(2×2×256×2 B) = 16 MiB 固定。32K 上下文合计约 272 MiB。排布与「后 10 层共享前面同类型层 KV」为我的假设。
- Gemma 4 E2B：下界 3 个非共享全注意力层，2×3×1×512×2 = 6 KiB/token；上界 7 层全部各自缓存，2×7×1×512×2 = 14 KiB/token（全局层按 global_head_dim=512 计）；滑窗 12 层固定约 6 MiB。128K 上下文约 0.75–1.75 GiB。假设同上。作为对照，Qwen3-4B 在 128K 为 18 GiB（M3，超出其原生 40,960 上下文）。

### 1.2 32K 上下文下 KV 与权重对照

| 模型 | KV/token | 8K | 32K | 128K |
|---|---|---|---|---|
| Qwen3-4B | 144 KiB | 1.1 GiB | 4.5 GiB | 18 GiB（外推） |
| Phi-4-mini | 128 KiB | 1.0 GiB | 4.0 GiB | 16 GiB |
| Qwen3-1.7B / Llama 3.2 3B | 112 KiB | 0.88 GiB | 3.5 GiB | 14 GiB |
| Qwen3.5-4B / 9B / MiniCPM4-8B | 32 KiB | 0.25 GiB | 1.0 GiB | 4 GiB |
| Qwen3.5-2B / MiniCPM4-0.5B | 12 KiB | 0.09 GiB | 0.38 GiB | 1.5 GiB |
| Gemma 3n E2B | 8 KiB + 16 MiB | 80 MiB | 272 MiB | 1.0 GiB（超出其 32K 上下文，仅作比较） |
| Gemma 4 E2B | 6–14 KiB + 6 MiB | 54–118 MiB | 198–454 MiB | 0.75–1.75 GiB |

### 1.3 外推与增长率

「常驻权重年增长」估算：
- 起点：Gemini Nano-2 约 1.6 GB（2023-12，估算）。终点：Nano 4 Fast 4.2 GB、Full 5.9 GB（2026-08，二手，口径不明）。跨度约 2.7 年。
- Fast：4.2/1.6 = 2.6 倍，ln 2.6 = 0.96，0.96/2.7 = 0.356，e^0.356 = 1.43，即约 +43%/年。Full：5.9/1.6 = 3.7 倍，ln 3.7 = 1.31，1.31/2.7 = 0.485，e^0.485 = 1.62，即约 +62%/年。
- 对照：DRAM 全球均值 7.4→8.4 GB（+13.5%，Counterpoint 2025-12 对 2024-12）；旗舰 Pixel 8 Pro 为 12 GB（2023），Nano 4 要求至少 12 GB（2026），旗舰容量三年基本没动。
- Apple 走另一条路：2024 约 1.4 GB（估算）→ 2025 2-bit QAT 后权重部分低于约 0.75 GB（估算，embedding 另计），常驻权重反而下降；代价是需要 QAT 与低秩适配器恢复质量（官方称 MGSM 回退约 4.6%，MMLU 提升 1.5%）。
- 2027 外推（估算）：若 Google 路线延续 +40%–60%/年，2027 同口径为 5.9–9.4 GB，已逼近 12–16 GB 机型的一半以上，物理上不可持续，因此判断厂商会转向「稀疏常驻 + 其余放闪存」（PLE、MoE），即常驻热权重 2–6 GB、总权重数十 GB 的形态。

### 分析：这说明什么（判断）

1. 端侧模型的常驻权重增速（约 40%–60%/年，Google 路线）明显高于 DRAM 容量增速（约 10%–14%/年），且 2026–2027 年 DRAM 受价格制约（M2）更难增长；两条曲线的交叉点已经出现在 12 GB 机型上，这是「内存是第一瓶颈」的直接数据。
2. 架构层面三个方向一致：稠密到稀疏（PLE、MoE、激活稀疏）、全量 KV 到混合/共享 KV（滑窗 + 层间共享 + 线性注意力）、位宽降到 2–4 bit。这些由模型厂商决定，OS 无法后加；OS 能做的是对「稀疏权重分层」和「多会话 KV」提供系统级支持。
3. KV 单 token 成本两年降一个数量级，意味着单会话 KV 不再是主矛盾；2027 年的 KV 压力来自「多会话 × 长 Agent 上下文」而不是单会话，KT2-B 的投入要和这一趋势对齐，避免押注稠密模型的 KV 压缩。

---

## 2 推理引擎的内存管理方式对比

说明：只写本轮能查到来源的事实；查不到处写明。OS 可见性一栏是我基于机制的推理，标「推断」。

| 引擎 | 权重加载 | KV 管理 | 多应用/会话共享权重 | OS 能否看到并回收 |
|---|---|---|---|---|
| llama.cpp | 默认 mmap，新版以 `-lm/--load-mode` 取代 `--mlock/--no-mmap`（二手博客，M3 已记，待对照官方文档）[R20] | 按上下文预分配；`-ctk/-ctv` 支持 f16/q8_0/q4_0，量化 V 缓存需开启 Flash Attention（二手指南）；源码镜像可见 `unified` 单流标志；未见分页式 KV [R21] | 多进程 mmap 同一文件时共享页缓存（推断）；应用各自启动则各自一份 KV | 权重为文件页，可被内核回收（推断）；KV 为匿名页，被 lmkd 视为进程 RSS |
| MLC-LLM | 未取到官方说明，待核实 | 编译期配置 `context_window_size`、`prefill_chunk_size` 等写入库（官方 mlc_chat_config 页「运行时修改可能出错」）；二手博文称其使用分页 KV | 未找到公开资料 | 未找到公开资料 |
| ExecuTorch | `Module` 提供 File/Mmap/MmapUseMlock/MmapUseMlockIgnoreErrors，新头文件含 MmapUseMadvise（WILLNEED+SEQUENTIAL 提示）；`.ptd` 数据文件可与 `.pte` 程序分开；`.pte` 数据段页对齐（M3）[R22] | 编译期在 `.pte` 元数据写入 `max_seq_len`/`max_context_len`（官方 LLM runner 页）；是否静态分配本轮未核 | 当前两个 `.pte` 不共享权重，社区 RFC 推进 NamedDataMap（M3） | 选 mlock 时钉住不可回收；仅 mmap 时可回收（推断） |
| LiteRT-LM（含应用内嵌入） | 官方页列出模型文件与峰值 CPU 内存（Gemma 4 E2B：S26 Ultra CPU 1733 MB / GPU 676 MB；iPhone 17 Pro CPU 607 MB / GPU 1450 MB），未写 mmap；首次加载优化并缓存（M3）[R11] | 官方页未提 KV 限制 | 应用内嵌入则各应用一份 | 进程内存，由 lmkd/Jetsam 按进程治理 |
| Android AICore（Gemini Nano） | 系统服务托管，模型由 AICore 下载、更新；官方文档原话：不必担心「对应用的磁盘和运行时内存预算的影响」[R23] | 请求级隔离，「处理后不存储输入输出」；多轮历史由 `sessionId` 或应用侧管理（官方 ML Kit 文档）[R23] | 是，所有调用方共享 AICore 内的同一份模型和 LoRA | AICore 是独立系统进程，其内存是否纳入 lmkd 保活或优先级：未找到公开资料 |
| MNN-LLM | DRAM-Flash 混合：低利用率参数（如 embedding，约占 Qwen2 7B 的 15%）放 Flash；mmap 选项本轮未核 | KV 先放 DRAM，超阈值溢出到 Flash 并预取；论文称 Flash 中 KV 小于约「3072K」时加载开销被计算掩盖（原文表述存疑，M3 已记）[R24] | 未找到公开资料 | 未找到公开资料 |
| 高通 QNN / Genie | context binary 预编译、单 SoC；同一 binary 内多图共享权重；多 binary 分段（M3）；HTP 单会话权重上限使大模型被切多个 context（社区模型卡，待核实）[R25] | KV 在 NPU 可见缓冲，具体机制未找到公开资料 | binary 内共享；跨应用共享：未找到公开资料 | 缓冲需注册并映射到 NPU 地址空间，通常钉住（M3 推断），不在 LRU |
| Apple Core ML / MLX / Foundation Models | Foundation Models 为系统共享端侧模型，应用不带权重（Apple 文档页本轮抓取只拿到标题，细节来自我的背景知识，待核实）；MLX 加载方式存在争议：一份预印本称 MLX 对 safetensors 是常规读取、权重需完全驻留，另一份指南称惰性加载，待核实 [R26] | Foundation Models 官方上下文窗口 8192（二手，待核实）；MLX KV 由使用者管理 | Foundation Models 是系统共享；MLX 应用私有 | 进程受 Jetsam 约束；开发者论坛实测上限约 6144 MB（iPhone 16 Pro Max 8 GB 与 iPhone 17 Pro Max 12 GB 相同），增加 increased-memory-limit 后调试上限约 6656 MB；Apple 文档称该 entitlement 仅部分机型可用 [R27] |
| 华为 MindSpore Lite / HiAI | MindSpore Lite 2.7.0 发行说明称「支持在进程间共享模型权重」；官方案例：HarmonyOS 内置翻译模型推理内存由 100 MB 以上降到 66 MB（混合精度子图调度 + IO 免拷贝）[R28] | 大模型 KV 管理：未找到公开资料 | 进程间权重共享为框架能力，系统级大模型托管：未找到公开资料 | HiAI Foundation 加载机制：未找到公开资料 |

### 分析：这说明什么（判断）

1. 引擎层面的共识是「权重文件化 + 页对齐 + mmap」（llama.cpp、ExecuTorch），但这只对 CPU 路径成立；一旦走 NPU，权重要被拷贝或注册到厂商私有缓冲（QNN context binary），脱离页缓存，OS 既不能回收也无法跨应用共享。
2. 真正做到多应用共享一份权重的只有系统托管路线（AICore、Foundation Models），其他情形下每多一个带模型的应用就多一份权重和一份 KV。这直接支撑立项论点：模型内存游离在 OS 治理之外，缺少统一记账、共享与回收。
3. 即便是系统托管，AICore 进程的内存如何被 lmkd 评分、是否会在前台应用叠加时被牺牲：未找到公开资料。这是需要立项后自测的关键事实，不能在汇报中当作已知结论。

---

## 3 Linux / Android 内存管理上游演进时间线（2022–2026）

### 3.1 内核版本时间线

版本号来自 kernelnewbies 各版本页面（本轮抓取的是前 100,000 字符，更靠后的条目可能漏看）；与 M2 已有判断冲突处写明。

| 版本 | 内容 | 来源 / 状态 |
|---|---|---|
| 5.15 | DAMON 合入（A15b） | 仓库既有 |
| 6.1 | MGLRU 合入；Android 侧由 Kalesh Singh（Google）LPC 2022 评估：Pixel 6 Pro 上应用启动时间约 -6.60%，工作集 refault 明显下降（检索摘要）；M2 记为「无 swap 测试 -47.10%」，两数不一致，待核实原稿 | 仓库既有；LPC 幻灯片摘要 [R29] |
| 6.4 | per-VMA lock 首次合入，初版仅匿名页；kernelnewbies 称部分操作不再用 mmap_lock，举例 Android 多线程应用启动；约 40 个提交 | kernelnewbies 6.4 [R30] |
| 6.5 / 6.6 | M2 称 6.5 起覆盖页缓存命中的文件缺页；kernelnewbies 6.6 页面列出「多数文件缺页在 VMA 锁下处理」「swap 与 userfaultfd 的 per-VMA lock 支持」。需要 I/O 的文件缺页、COW 的覆盖版本以 6.6 页面为更直接的证据，但 6.5 与 6.6 的分工未核清，待核实 | [R30] |
| 6.6 | zswap 多 zpool；DAMOS 过滤器扩展（地址范围、监控目标）| kernelnewbies 6.6 |
| 6.8 | 匿名 mTHP：单次缺页可分配大于 4 KB 的匿名 folio；THP 运行时开关；zswap 收缩 memcg 感知；DAMOS 自调参（feed/tame） | kernelnewbies 6.8（页面语言较含糊，匿名 mTHP 合入版本以此为准，待核实） |
| 6.9 | arm64 连续 PTE「Transparent Contiguous PTEs for User Mappings」约 16 个提交（确认了 M2 的「印象 6.9」）；per-VMA lock 扩展到 userfaultfd 与 hugetlb 缺页 | kernelnewbies 6.9 |
| 6.12 | mTHP swap 分配器按 swap cluster 阶数分配；shmem 大 folio 换出换入；zram 自定义压缩后端 API；每上下文 DAMON 区域优先级直方图 | kernelnewbies 6.12；对应 Android `android16-6.12` |
| 6.14 | 页面可见 mTHP swap-in 的逐阶回退计数器，推断匿名大 folio 换入（同步设备，如 zram）此前已进主线，具体版本待核实；swap 分配器锁重构、swap_cgroup 全局锁移除、MGLRU 性能优化；DAMON 去掉 debugfs | kernelnewbies 6.14（推断） |
| 6.15–6.16 | zsmalloc/zram 抢占支持；zswap 删除 z3fold 和 zbud；per-VMA lock 重实现为引用计数；DAMOS 聚合间隔自调、新增活跃页与未映射页过滤器；zram 算法专属参数、writeback 接口现代化；MGLRU 的 `SWAPPINESS_ANON_ONLY`（上述条目到 6.15 还是 6.16 的归属，本轮抓取顺序下无法逐条确认，待核实） | kernelnewbies 6.15/6.16 |
| 6.18（2025 年末） | swap table 第一阶段（作为 swap cache 后端，官方称吞吐/构建时间约 +5%–20%）；swap cluster 扫描策略；64 kB mTHP + 10 GB zram 的 `make -j96` 测试系统时间减半、失败率降到 0；DAMON_RECLAIM 的 `addr_unit`、可导出自调间隔；`/proc/pid/maps` 用 per-VMA lock | kernelnewbies 6.18 [R31]；对应 Android `android17-6.18` |
| 6.19 | DAMON 按 memcg/节点自调；`UFFDIO_MOVE` 去掉 anon_vma 锁；swap 设备默认优先级轮询 | kernelnewbies 6.19 |
| 7.0 | 一份低质量镜像页面把 swap table 第一阶段也列在 7.0 合并摘要里，与 kernelnewbies 6.18 冲突，本文以 6.18 为准；7.0 其他项目未取到 | 待核实 |
| 未合入 | DAMON 硬件采样访问报告 RFC（2026-05 v1，2026-09 v2）、pghot v8、virtual swap（M2） | M2 |

### 3.2 Android 侧

| 项目 | 内容 | 来源 / 状态 |
|---|---|---|
| GKI 分支与 Android 版本 | android12-5.10；android13-5.10 / 5.15；android14-5.15 / 6.1；android15-6.6；android16-6.12；android17-6.18 | source.android.com GKI release builds 页，页内无日期与生命周期 [R32] |
| 16KB 页 | Android 15 起 AOSP 支持；设备开发者选项可在 Pixel 8/8a/9 系列上用 16KB 启动；Android 17 新增「强制关闭兼容模式并让不兼容二进制立即中止」的选项 | developer.android.com [R33] |
| 16KB 官方收益数据 | 内存压力下应用启动平均 -3.16%（部分最多 -30%）；启动功耗 -4.56%；相机热启动 -4.48%、冷启动 -6.60%；系统启动 -8%（约 950 ms）；同时内存略增（第三方称约 9%，官方只写「略增」）；自定义分配器在 16KB 下 RSS 与 ZRAM 压缩率变差 | 同上 |
| Play 要求 | 此前版本的页面写作「2025-11-01 起提交的新应用和更新须支持 16KB」；当前页面写作「2027-02-01 起，不支持 16KB 的更新将无法发布」，并要求 target API 35 及以上、64 位设备。两个日期说明截止时间被延后，具体延期公告本轮未检索，待核实 | [R33] |
| MGLRU | Android 通过 `persist.device_config.mglru_native.lru_gen_enabled` 实验开关切换，默认值取决于 `CONFIG_LRU_GEN_ENABLED`，GKI 的 android15-6.6 默认是否开启：未找到公开资料；LWN 2026-03：多个 Android 厂商没开，且热/冷应用语义缺失 | M2 R7；检索 |
| lmkd / PSI | 本轮未做专项检索，沿用仓库既有文章；PSI 驱动的 lmkd 为公知机制，未在本轮核对版本与参数，待核实 | — |

### 3.3 上游硬件访问采样

| 项目 | 状态 | 来源 |
|---|---|---|
| Intel PEBS | 用于 HeMem/Memtis 等研究；DAMON 硬件采样 RFC 已用 PEBS 验证（未合入） | M2 [R3][R4] |
| AMD IBS | pghot 系列（2025-03 RFC → 2026-07 v8）；DAMON RFC 以 IBS 做示例；仍存在评审分歧 | M2 [R2] |
| Arm SPE | `arm_spe_pmu` 驱动已在主线与 Android common kernel 中；perf 过滤扩展补丁（FEAT_SPEv1p4、SPE_FDS，2025）；内存分层使用 SPE：openEuler OLK-6.6 厂商分支有「SPE 驱动 NUMA balancing + DAMON」，主线无；DAMON RFC 说明「SPE 后端由另一开发者对接」 | M2 [R24–R26]；Android common kernel 目录页 |

### 3.4 iOS 与 HarmonyOS

| 平台 | 公开资料 | 来源 / 状态 |
|---|---|---|
| iOS | 低内存终止为 Jetsam；匿名内存靠压缩器（不是 zram，无磁盘 swap 的口径沿用仓库 A15c，本轮未复核）；increased-memory-limit entitlement 仅部分机型可用，Apple 建议用 `os_proc_available_memory` 查询；开发者论坛实测单应用约 6 GB 上限（见第 2 节），有开发者报告模型常驻约 4.4 GB 后只剩约 1.7 GB 用于 prefill，缩小 GPU 缓冲缓存 512 MB→64 MB 才避免 Jetsam（单一论坛帖，待核实） | Apple 文档；Apple Developer Forums [R27] |
| HarmonyOS | OpenHarmony 标准系统：ESwap（zswapd 把 zram 压缩过的匿名页加密换出到专用分区；记录匿名页冷热特征，相邻页连续存放以便批量换入；无分区时仅 zram），内核配置以 `CONFIG_HYPERHOLD` 开头；HyperHold 入选 2022 华为十大发明但无量化数据；2026-04 HyperSpace Memory：12 GB 达 16 GB 保活效果、压缩率最多 +69%，TrendForce 转述，无技术细节（也无法确认与 HyperHold 的关系）。HarmonyOS NEXT 微内核：未找到公开资料 | OpenHarmony 文档（检索摘要）[R34]；TrendForce [R35] |

### 3.5 每项「解决什么 / 没解决什么」

| 项 | 解决了什么 | 对 Agent + 应用叠加场景没解决什么 |
|---|---|---|
| per-VMA lock（6.4 起） | 多线程缺页不再抢 mmap_lock，缓解应用启动的锁竞争 | 回收侧 rmap 锁（i_mmap_rwsem）争用仍在（M2）；模型 mmap 的大文件缺页走文件缺页路径，是否受益取决于 I/O 型缺页是否也走 VMA 锁（待核实） |
| folio / mTHP（6.8 起）、contpte（6.9） | 一次缺页分配大页，减少缺页次数和 TLB 压力；arm64 可合并 PTE | 手机碎片严重下大页分配失败率；exec 大 folio 的合入版本待核实（M2） |
| mTHP swap-out/in 与 zram 支持（6.12–6.14 前后） | 大 folio 整块换入换出，避免拆分 | 同步设备（zram）适用；经闪存的 writeback 路径与冷热识别不在其中 |
| swap table（6.18）、virtual swap（提案） | 降低 swap 元数据和锁开销；为大 folio swap 铺路 | 不提供冷热证据，也不解决预取 |
| MGLRU（6.1） | 更细页龄，Pixel 6 Pro 上启动时间 -6.60%（摘要） | Android 厂商多未开启；与前后台应用语义脱节；匿名页回收偏弱（M2） |
| DAMON / DAMOS（5.15 起，6.8 自调参，6.18 `addr_unit`） | 区域级访问监控，开销与内存大小无关；可作为 pageout 的执行入口 | 区域粒度；硬件采样 RFC 未合入；冷证据仍依赖页表 Accessed 位 |
| 硬件访问采样（PEBS/IBS/SPE） | 页级热证据 | 主线无 SPE 分层补丁；手机是否开放 SPE 未找到公开资料；只能证热不能证冷 |
| 16KB 页 | 减少缺页与 TLB 压力，内存压力下启动更快 | 内存占用上升；对 .so 的页保护粒度变大；与模型 mmap 的交互未找到公开资料 |
| lmkd / PSI | 以压力信号决定杀进程 | 本轮未核对；KV、dma-buf、NPU 缓冲在 LRU 之外，易提前触发查杀（仓库 A16 综述口径，本轮未找到实测） |
| iOS Jetsam / 压缩器 | 在无磁盘 swap 口径下靠压缩与杀进程治理 | 单应用约 6 GB 上限与 12 GB 机型不匹配（论坛实测）；模型进程容易被杀 |
| HarmonyOS ESwap / HyperHold / HyperSpace | 闪存扩容与冷热记录，商用宣称保活翻倍 | 无量化数据，NEXT 微内核机制无公开资料，模型内存是否纳入未知 |

### 分析：这说明什么（判断）

1. 上游 2022–2026 的主线是「降低缺页与 swap 路径的锁与元数据开销」「大 folio 化」「DAMON 做可编程回收」，而不是「按应用语义与硬件证据做冷热识别」；后者在主线仍是 RFC，说明 KT1-b/c 有空间，但也意味着我们的实现要对接 DAMON 的采样 ring 而不是自建体系（M2 结论的延续）。
2. 所有机制都以 LRU 和进程为治理单位；模型的 NPU 缓冲和 KV 不在其中，立项里「模型内存一等公民」的叙述在上游路线图中没有对应项。
3. Android 16KB 页 2027-02 前后成为强制生态要求，.so 文件页锁优化（KT1-a）必须按 16KB 页粒度设计，不能沿用 4KB 假设。

---

## 4 硬件侧

### 4.1 内存与存储

| 项目 | 数据 | 量产/时间 | 来源与状态 |
|---|---|---|---|
| LPDDR5X | Micron 2023 年产品 9.6 Gbps，配 Snapdragon 8 Gen 3；2025-06 1γ 10.7 Gbps，16 GB 送样，容量 8–32 GB，目标 2026 旗舰 | 已量产 | Micron 新闻稿（经转载）[R36] |
| LPDDR5X 带宽 | 每引脚 9.6 Gbps 在 64 bit 总线下为 76.8 GB/s；10.7 Gbps 下 85.6 GB/s（估算：Gbps×64/8；64 bit 为手机常见配置的假设）。学术实测：骁龙 8 Gen 3 的 SoC 理论最大约 68 GB/s，单个处理器仅能达到约 45 GB/s | — | 估算；HeteroLLM 论文（arXiv 2501.14794，经摘要）[R37] |
| LPDDR6 标准 | JEDEC JESD209-6，2025-07 发布；数据率 10,667–14,400 MT/s；每引脚速率相对 9.6 Gbps 的 LPDDR5X 为 +11% 到 +50%（估算：10.667/9.6 与 14.4/9.6） | 见下 | Notebookcheck 转述 JEDEC（JEDEC 官方页本轮 403）[R38] |
| LPDDR6 量产 | SK hynix：1c 工艺 LPDDR6 开发完成，2026 上半年量产准备、下半年供货，速率有 10.7 Gbps 与 14.4 Gbps 两种说法，冲突；Samsung：1b 工艺产品 2026-01 发布（CES 奖项），2026-09 报道在高通新平台验证；CXMT 称最高 12.8 Gbps；价格较 LPDDR5X 约高 20%；Apple 可能继续用 LPDDR5X 为传闻。截至本文未确认出货手机 | 2026 下半年量产，手机端 2027 | 多来源转述，待核实 [R39] |
| UFS 4.1 | Samsung 口径顺序读 4.3 GB/s、写 4.1 GB/s。注意：M3 引用的 5.8 GB/s 是 UFS 4.0 接口理论上限，两者口径不同 | 量产 | Samsung 新闻稿经转载 [R40] |
| UFS 5.0 | Samsung：顺序读 10.8 GB/s、写 9.5 GB/s，约为 UFS 4.1 的 2.5 倍（10.8/4.3），能效较自家 UFS 4.1 提升超 40%，封装小 16.7%，最大 1 TB；2026-06-23/24 发布，2026 Q4 量产；Kioxia 的 UFS 5.0 顺序读最高约 10 GB/s，预计 2026 年底量产；首发手机传为 Galaxy S27，Samsung 未确认；SK hynix：未找到 UFS 5.0 公开资料 | 2026 Q4 量产，手机 2027 | TrendForce 2026-06-24；Kioxia 2026 新闻 [R40][R41] |

加载时间估算（估算，理想顺序读，未计缺页、重排、NPU 注册）：Nano 4 Full 5.9 GB 在 UFS 4.1（4.3 GB/s）下约 1.4 s（5.9/4.3），在 UFS 5.0（10.8 GB/s）下约 0.55 s（5.9/10.8）；Gemma 4 E4B 移动端 2.5 GB 分别约 0.58 s 与 0.23 s。

### 4.2 CPU 与 NPU

| 项目 | 结论 | 来源与状态 |
|---|---|---|
| SPE 是 Armv8.2 起的可选特性 | 是 | Arm 文档 |
| Cortex-A720/A725/X925 是否实现 SPE | Linux perf 补丁把它们加入 SPE data source 编码表，A720 勘误仅在 SPE 实现且启用时出现，据此判断实现（M2）；Arm X925 TRM 本轮因站点重定向未抓取，文号 102807 | M2 [R42] |
| C1-Ultra（Lumex，Armv9.3） | 一份第三方 TRM 摘要列出「L1 Statistical Profiling Extension (SPE) TLB」（SPE 块内、1 项）；同一摘要未提 X925 和 C1-Pro 的 SPE，不代表它们没有 | jia.je 摘要，二手，待核实 [R43] |
| 手机 SoC 是否向 Linux 开放 SPE | 未找到公开资料（包括骁龙 8 Elite Gen 5 的 Oryon、天玑 9500、麒麟）；核实方法：看设备 `/sys/bus/event_source/devices/arm_spe_0` 与 `/proc/config.gz` 的 `CONFIG_ARM_SPE_PMU` | 检索 |
| NPU 的 SMMU/IOMMU | 高通 msm 内核树使用 `arm-smmu.c`（SMMUv1/v2 驱动），设备树中有为 NPU stream ID 配置预取的提交（小米 nabu，旧平台），说明 NPU 流量经应用侧 SMMU；上游 SVA 支持在 `arm-smmu-v3`，据此推断旧高通平台不具备 SVA（推断，待核实） | Android 内核提交页 [R44] |
| 手机 NPU 的 SVA | Qualcomm Hexagon、MediaTek APU、华为达芬奇是否在 Android 手机上启用 SVA：未找到公开资料 | 检索 |

### 分析：这说明什么（判断）

1. 带宽方面，LPDDR5X 到 LPDDR6 的每引脚提升为 +11% 到 +50%，而端侧常驻权重年增 40%–60%，带宽增长依然追不上模型增长，decode 仍是带宽受限（Qualcomm 论文与学术评测一致）。
2. UFS 5.0 使 2027 年旗舰的闪存顺序读达到约 10 GB/s，约为 LPDDR5X 带宽的八分之一（10.8/85.6，估算），这使「稀疏权重分层 + 闪存预取」第一次接近可用，但前提是 4KB 缺页能被聚合为大块 IO（KT3 难点二）。
3. 立项里两个硬件依赖（SPE 开放、NPU SVA 零拷贝）都没有公开证据，应当在立项书中列为「第 0 阶段摸底」项，而不是已知可用能力。

---

## 5 产业信号

### 5.1 手机平均 DRAM 容量

| 年份 | 数据 | 来源与状态 |
|---|---|---|
| 2023 | 增长约 6.7%（TrendForce 自站），另一转贴称 14.3% 为早期预测 | TrendForce；转贴待核实 [R45] |
| 2024 | 增长约 7.9%（转贴，未核主源）；2024-12 全球均值 7.4 GB（Counterpoint 反推） | 待核实 |
| 2025 | 2025-12 全球均值 8.4 GB（+13.5%：8.4/7.4）；Apple 接近 10 GB（+2.2 GB，iPhone 17 Pro 升至 12 GB）；$600 以上高端档约 11 GB；Huawei 12 GB 最高；分价位同比：低端 +8%、中端 +3%、高端 +2% | Counterpoint 2026-02-26 [R46] |
| 2026 | TrendForce 预测均值 8.5 GB（同比约 +10%；与 Counterpoint 12 月快照基线不同，口径不可直接比）；Counterpoint：12 GB 在高端成为标配，厂商转向保利润而非提规格，中低端受冲击最大 | [R46][R45] |
| 2027 | 未找到公开的分机型预测；M2 引用 TrendForce：4Q26 涨幅收敛、2027 供给偏紧价格不会明显回落 | M2 R23 |

补充：内存占 iPhone 17 Pro Max BoM 超过 10%（2020 年 iPhone 12 Pro Max 为 8%），高端旗舰可超 20%；Galaxy S26 起售价 $899（取消 128 GB 版本）（Counterpoint）[R46]。

### 5.2 公开表态

| 主体 | 表态或数据 | 日期 | 来源与状态 |
|---|---|---|---|
| Google | Gemini Nano 4 基于 Gemma 4，官方称「最高快 4 倍、省电最多 60%」；AICore 文档强调托管模型使应用不受磁盘和运行时内存预算影响；二手称 Nano 4 至少 12 GB RAM、仅 7 款机型 | 2026-04-02；2026-08-29 | 官方博客；二手文章 [R4][R5][R23] |
| Qualcomm | 公司研究论文（arXiv 2412.01380）指出内存容量与速度落后于算力、LLM 每生成一个 token 都需读取全部权重；官方高管对「内存是瓶颈」的公开表态本轮未找到公开资料 | 2024-12 | 检索摘要 [R47] |
| MediaTek | 与 Meta 合作宣传 Llama 2 在较少 DRAM 带宽下运行（PhoneArena 转述，企业宣传口径） | 2023 | 二手 |
| Arm | 官方关于「内存是端侧 AI 瓶颈」的表态：未找到公开资料 | — | 检索 |
| Micron | 2023 年赞助稿称 AI 与情境感知需要 12–16 GB，未来或有 24 GB 需求；2025-06 1γ LPDDR5X（10.7 Gbps，16 GB 送样，容量 8–32 GB）并给出 Llama 2 对比评测，具体数字本轮未取到 | 2023-03；2025-06 | The Register 赞助稿；新闻稿标题 [R36] |
| Samsung | UFS 5.0 定位为端侧 AI 存储，LPDDR6 已发布 | 2026-06；2026-01 | TrendForce；检索 |
| SK hynix | LPDDR6 面向 AI 智能手机，2026 下半年供货 | 2026-03 起 | 二手转述 [R39] |
| 华为 | HyperSpace Memory：12 GB 达 16 GB 效果 | 2026-04-20 | TrendForce [R35] |

### 分析：这说明什么（判断）

1. 厂商表态集中在「容量与带宽规格升级」，而不是「OS 如何管理模型内存」；芯片厂和内存厂的公开叙述以 LPDDR5X/6、UFS 5.0 为主，系统层的缺位正好是 Agent OS 的位置。
2. 2026 年容量不再自然增长（Counterpoint：厂商保利润、中低端受冲击），而模型要求每年 +40%–60%，两者之间的缺口只能由「虚拟化容量（压缩、闪存）+ 稀疏分层 + 更好的回收」填补，这与 Samsung RAM Plus、华为 HyperSpace 的商业方向一致，也是 KT1 与 KT2/KT3 合在一起讲的依据。
3. 汇报时应避免把二手信息（Nano 4 至少 12 GB、Apple 20B 稀疏模型）当作确定事实，建议用「据报道」措辞，并在立项后用官方文档补证。

---

## 参考资料

访问日期均为 2026-11-04；发布日期按来源页面可见信息，未知写「日期未核」。[M2]、[M3] 指本目录下 M2-system-memory.md、M3-model-memory.md 及其参考资料。

- [R1] Gemini Nano 参数量与量化（二手 wiki 转述 Gemini 1.0 技术报告）：https://aiwiki.ai/wiki/gemini_nano ；https://agentwiki.org/google_nano （日期未核）
- [R2] Pixel 8 与 Nano 报道：https://bgr.com/tech/pixel-8-will-get-gemini-nano-on-device-ai-after-all （2024-03）
- [R3] Pixel 10 Gemini Nano 约 4B（日文转述）：https://www.inside.com.tw/tag/24751-Gemini%20Nano ；https://helentech.jp/news-74908/ （2025-08，日期未核）
- [R4] Android Developers Blog，AICore Developer Preview：https://android-developers.googleblog.com/2026/04/AI-Core-Developer-Preview.html （2026-04-02）
- [R5] Gemini Nano 4 设备与 RAM 要求（二手）：https://pasqualepillitteri.it/en/news/13389/gemini-nano-4-first-phones-gemma-4 （2026-08-29）；https://9to5google.com/2026/08/27/gemini-intelligence-nano-4/ （2026-08-27）
- [R6] Apple 2024 基础模型博客：https://machinelearning.apple.com/research/introducing-apple-foundation-models （2024-06）
- [R7] Apple 2025 更新博客与技术报告：https://machinelearning.apple.com/research/apple-foundation-models-2025-updates ；https://arxiv.org/abs/2507.13575 （2025-07）
- [R8] WWDC26 端侧模型二手汇总：https://callstack.com/blog/on-device-ai-after-wwdc-2026-whats-new ；https://dev.to/owen_fox/apples-third-generation-foundation-models-a-developers-read-on-wwdc-2026-2ej1 （2026-06，互相矛盾）
- [R9] Gemma 3n 官方概览：https://ai.google.dev/gemma/docs/gemma-3n （日期未核）
- [R10] Gemma 3n E2B / Gemma 4 E2B 的 config（Unsloth 镜像，非 Google 官方 repo，官方 repo 需授权）：https://huggingface.co/unsloth/gemma-3n-E2B-it/raw/main/config.json ；https://huggingface.co/unsloth/gemma-4-E2B-it/raw/main/config.json （日期未核）
- [R11] LiteRT-LM 概览（模型文件大小、Gemma 4 E2B 峰值内存）：https://developers.google.com/edge/litert-lm/overview （日期未核）
- [R12] Gemma 4 官方文档（内存表）：https://ai.google.dev/gemma/docs/core （发布日期 2026-04-02 以 [R4] 为准）
- [R13] Qwen3-0.6B / 1.7B config：https://huggingface.co/Qwen/Qwen3-0.6B/raw/main/config.json ；https://huggingface.co/Qwen/Qwen3-1.7B/raw/main/config.json
- [R14] Qwen3.5-2B / 4B / 9B config：https://huggingface.co/Qwen/Qwen3.5-2B/raw/main/config.json （4B、9B 同路径）
- [R15] Llama 3.2 1B / 3B config（Unsloth 镜像）：https://huggingface.co/unsloth/Llama-3.2-3B-Instruct/raw/main/config.json ；https://huggingface.co/unsloth/Llama-3.2-1B-Instruct/raw/main/config.json
- [R16] Phi-4-mini config：https://huggingface.co/microsoft/Phi-4-mini-instruct/raw/main/config.json
- [R17] MiniCPM4：https://arxiv.org/abs/2506.07900 ；https://huggingface.co/openbmb/MiniCPM4-0.5B/raw/main/config.json ；https://huggingface.co/openbmb/MiniCPM4-8B/raw/main/config.json
- [R18] BlueLM-V-3B：https://arxiv.org/abs/2411.10640 （2024-11-16）；蓝心 3B 1.4 GB 口径：https://ai-bot.cn/bluelm/ （第三方）
- [R19] 端侧模型分层研报：https://pdf.dfcfw.com/pdf/H3_AP202609271829935669_1.pdf （2026-09-27 前后）
- [R20] llama.cpp 加载标志（二手）：https://dev.to/multigrid/llamacpps-mmap-and-mlock-flags-explained-43fp
- [R21] llama.cpp KV 量化与 unified KV（二手）：https://llmhardware.io/guides/kv-cache-quantization-ollama-llama-cpp
- [R22] ExecuTorch Module 加载模式与 LLM runner：https://docs.rs/executorch-sys/latest/executorch_sys/enum.ModuleLoadMode.html ；https://docs.pytorch.org/executorch/stable/llm/run-with-c-plus-plus.html
- [R23] Android 官方 Gemini Nano / AICore 文档：https://developer.android.com/ai/gemini-nano
- [R24] MNN-LLM：https://arxiv.org/abs/2506.10443 （2025）
- [R25] 高通 QNN 权重共享与 ORT-QNN：见 [M3] 参考 29
- [R26] MLX 加载争议：https://atomgradient.github.io/MLXLayerStream/paper.pdf （预印本）；https://smithery.ai/skills/itsmostafa/mlx
- [R27] iOS 内存上限论坛帖与 entitlement 文档：https://developer.apple.com/forums/thread/834805 ；https://developer.apple.com/tutorials/data/documentation/bundleresources/entitlements/com.apple.developer.kernel.increased-memory-limit.md
- [R28] MindSpore Lite：https://www.mindspore.cn/news/zh/2025-12-18/_payload.json （翻译模型 66 MB 案例）；https://mindspore.cn/lite/docs/en/r2.7.0/RELEASE.html
- [R29] Android MGLRU 评估（LPC 2022，Kalesh Singh）：https://lpc.events/event/16/contributions/1336/attachments/972/1895/Android%20MGLRU%20Evaluation.pdf ；LWN https://lwn.net/Articles/1060967/ （2026-03-05）
- [R30] kernelnewbies 6.4 / 6.6 / 6.8 / 6.9 / 6.12 / 6.14 / 6.15 / 6.16：https://kernelnewbies.org/Linux_6.4 （其余同路径，把版本号替换）
- [R31] kernelnewbies 6.18 / 6.19：https://kernelnewbies.org/Linux_6.18 ；https://kernelnewbies.org/Linux_6.19
- [R32] GKI 发布构建页：https://source.android.com/docs/core/architecture/kernel/gki-release-builds
- [R33] Android 16KB 页：https://developer.android.com/guide/practices/page-sizes
- [R34] OpenHarmony ESwap（检索摘要）：https://gitcode.com/openharmony/docs/blob/master/en/device-dev/kernel/kernel-standard-mm-eswap.md
- [R35] TrendForce 华为 HyperSpace Memory：https://www.trendforce.com/news/2026/04/20/news-huawei-unveils-pura-90-pro-max-with-hyperspace-memory-12gb-ram-said-to-match-16gb-performance/ （2026-04-20）
- [R36] Micron 1γ LPDDR5X 与 2023 LPDDR5X：https://www.barchart.com/story/news/32696280/micron-ships-worlds-first-1gh-1-gamma-based-lpddr5x-enabling-rich-mobile-ai-experiences （页面本轮抓取为空，信息来自检索摘要）；https://iconnect007.com/article/138371/ （2023-10）；https://www.theregister.com/2023/03/15/feeding_the_smartphone_frenzy_its/
- [R37] HeteroLLM：https://arxiv.org/html/2501.14794v1 ；LLM 手机基准：https://arxiv.org/html/2410.03613v4
- [R38] LPDDR6：https://www.notebookcheck.net/JEDEC-releases-LPDDR6-standard-data-rates-reach-14-400-MT-s.1055771.0.html （2025-07）
- [R39] SK hynix / Samsung / CXMT LPDDR6：https://tweaktown.com/news/112910/sk-hynix-will-start-lpddr6-mass-production-in-2026-for-xiaomi-smartphones/ ；https://mobilemasr.com/en/blogs/sk-hynix-develops-1cnm-lpddr6 ；https://thenextweb.com/news/cxmt-lpddr6-memory-smartphone-production-near
- [R40] Samsung UFS 5.0：https://www.trendforce.com/news/2026/06/24/news-samsung-unveils-ufs-5-0-storage-claims-industrys-fastest-with-10-8gbs-speeds/ （2026-06-24）；https://news.samsung.com/global/samsung-unveils-industrys-fastest-ufs-5-0-solution （本轮抓取超时，数字以 TrendForce 与多家转载为准）
- [R41] Kioxia UFS 5.0：https://www.kioxia.com/ja-jp/business/news/2026/20260729-2.html （2026-07-29）
- [R42] SPE 与 Cortex 核：见 [M2] 参考 24、27；Arm SPE 概述：https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/statistical-profile-extension
- [R43] Arm 公版核对比（含 C1-Ultra SPE TLB）：https://jia.je/hardware/2025/09/10/arm-core-development/ （2025-09-10）
- [R44] 高通 msm 内核 arm-smmu.c 与 NPU SMMU 配置提交：https://android.googlesource.com/kernel/msm/+/2786ec57c52839f02802c01b0a12f24255064b10/drivers/iommu/arm-smmu.c ；https://gitlab.e.foundation/e/devices/android_kernel_xiaomi_nabu/-/commit/713aea672669e2277df5cafb2a2f0cba63e6e2a1 ；SVA 上游补丁：https://patchwork.kernel.org/patch/11784571/
- [R45] TrendForce 手机 DRAM 容量预测：https://www.trendforce.com/presscenter/news/20260514-13044.html ；转贴：https://techpowerup.com/forums/posts/5091250
- [R46] Counterpoint，全球手机平均 DRAM 2025：https://counterpointresearch.com/en/insights/Global-Smartphone-Average-DRAM-Hits-Record-8.4GB-in-2025 （2026-02-26）
- [R47] Qualcomm AI Research：https://arxiv.org/pdf/2412.01380 （2024-12）

---

## 待核实清单

1. Gemini Nano-1/2 的参数量（1.8B / 3.25B）仅二手 wiki，官方未披露；Nano v3 约 4B 单一日文转述；Nano 3 的位宽与常驻内存未找到。
2. Gemini Nano 4 的「至少 12 GB RAM」「Fast 4.2 GB / Full 5.9 GB」「7 款机型」均来自一篇二手文章转述 Google 文档，口径（存储 vs 常驻 vs 含多模态）不明，与 Gemma 4 官方移动端 1.1/2.5 GB 差距大。
3. Apple AFM 3（2026）的 20B 稀疏模型、1–4B 激活、权重存放位置、8192 上下文：全部二手且互相矛盾，无 Apple 官方文档；Apple 2025 端侧上下文长度与词表官方页未给。
4. Gemma 3n、Qwen3、Llama 3.2、Phi-4-mini 的确切发布月份（Gemma 4、Nano 4 以官方博客为准）；Gemma 3n E4B、Gemma 4 E4B 的 KV 相关 config 未取（官方 repo 授权限制）。
5. Gemma 4 E2B / Gemma 3n E2B 的 KV 估算依赖「全注意力层排布每 5 层 1 个」「共享层复用前面同类型层 KV」「全局层按 global_head_dim=512 的 K、V 分别缓存」三条假设，需对照 transformers 实现或 LiteRT 导出核实。
6. 引擎对比中的多个格子为「未找到公开资料」：MLC-LLM 权重加载与 KV 分页的官方说明、ExecuTorch KV 是否静态分配、MNN mmap 选项、QNN/Genie KV 机制、AICore 进程内存是否被 lmkd 特殊对待、HiAI Foundation 大模型加载。
7. Foundation Models 框架的共享模型、`prewarm()`、MLX 惰性加载与否：Apple 文档页本轮只抓到标题，细节来自背景知识或矛盾的第三方文章。
8. iOS 单应用 6144 MB 上限仅为开发者论坛的非官方实测（含 12 GB 机型）；iOS 无磁盘 swap 的口径沿用仓库 A15c，本轮未复核；Jetsam 阈值官方未公开。
9. per-VMA lock 对需要 I/O 的文件缺页、COW 的合入版本（6.5 还是 6.6）；匿名 mTHP 的确切合入版本（页面表述含糊，推断 6.8）；同步设备大 folio swap-in 的合入版本（推断不晚于 6.14）；6.15/6.16 条目归属；swap table 在 6.18 还是 7.0（以 kernelnewbies 6.18 为准）。
10. MGLRU 的 Pixel 6 评估数字（-6.60% 与 -47.10% 不一致）；GKI android15-6.6 / android16-6.12 默认是否开启 MGLRU；lmkd 与 PSI 的版本与参数本轮未核。
11. Google Play 16KB 截止日期的延期公告（2025-11-01 → 页面现写 2027-02-01）。
12. LPDDR6：SK hynix 速率 10.7 Gbps 还是 14.4 Gbps；各家真实量产与首批手机型号；JEDEC 官方页与 Samsung 新闻稿本轮未抓取成功（403/超时），LPDDR6 的通道宽度未核，故未给 GB/s 绝对值；UFS 5.0 首发机型（Galaxy S27）仅传闻；SK hynix UFS 5.0：未找到公开资料。
13. 手机 SoC 的 SPE 开放情况（高通 Oryon、联发科、麒麟）、Cortex-X925/C1-Pro 的 TRM 中 SPE 条款：未找到公开资料；C1-Ultra 的 SPE TLB 来自第三方摘要。
14. 手机 NPU 的 SVA 支持：未找到公开资料；对旧高通平台「无 SVA」是基于 arm-smmu.c 驱动名的推断。
15. 手机平均 DRAM：2024 年绝对值与 2027 年预测未找到原始数据；TrendForce 2026 年 8.5 GB 与 Counterpoint 2025-12 的 8.4 GB 口径不同；2023–2024 增速为二手。
16. 产业表态：Qualcomm、MediaTek、Arm 官方「内存是端侧 AI 瓶颈」的直接引述未找到公开资料；Micron 1γ LPDDR5X 的 Llama 2 对比数字本轮未取到。
17. 荣耀 MagicAgent、小米 MiMo 端侧内存数据：未找到公开资料；vivo 蓝心 3B 的 1.4 GB 来自第三方站点。
18. 华为 HyperSpace Memory 的技术内容、与 HyperHold/ESwap 的关系、是否纳入模型内存：未找到公开资料；HarmonyOS NEXT 微内核的页回收与换出机制：未找到公开资料。

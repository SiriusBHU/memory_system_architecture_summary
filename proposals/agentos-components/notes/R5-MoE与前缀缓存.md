# R5 端侧 MoE 底座、专家命中率与前缀缓存生命周期

> 日期：2026-11-09。口径等级：官方 / 论文同行评审 / 预印本 / 厂商自报 / 二手 / 估算。
> 本轮实际核对（WebFetch 8 次、WebSearch 4 次）：2605.26297、2502.07776、SmallThinker、Paging the Experts、FlashMoE、WiSP 的 arXiv 摘要页，Qwen3-30B-A3B 的 config.json，VentureBeat 对 AFM 3 的报道。其余数字沿用仓库 M3 / C4b，已在表中注明「引自」，本轮未复核。

## 1. 结论摘要

1. 2027 年底座有两条现实路线：Apple 的 AFM 3 Core Advanced（二手：总 20B、激活 1–4B，全量权重在 NAND flash，每个 prompt 路由一次）与开源细粒度 MoE（SmallThinker-21B-A3B，Q4_0 约 8GB）。12GB 机型 Agent 侧约 4GB，装不下 8GB 的 21B-A3B，只能分层，只有 4B-A0.6B（约 1GB）能全驻留。
2. 逐 token 路由的 A3B 模型在 0% 命中时每 token 约 1.1GB IO（Qwen3-30B-A3B，估算）；按 UFS 4.x 顺序读 4.3GB/s 计，命中率 0% 时上限约 3.9 token/秒，达到 20 token/秒要求命中率约 ≥ 80%（估算，随机读按顺序读的 70% 取值为假设，见 §3）。
3. Paging the Experts 的「512MiB 为 0%、576MiB 为 38.58%」是 LRU 在循环访问下的容量悬崖，作者自己写明这是「策略与负载的交互，而非通用内存需求」，同一容量下随机淘汰是 18.80%（预印本）。结论是策略选择比容量小幅增加更重要。
4. 预取在单流 decode 上不一定有用：WiSP 在 RTX 3090 上发现预测并预取未来专家对单流 decode 无帮助，因为预取与按需传输争带宽（预印本，GPU 平台，需在 UFS 上重新验证）。Apple 的「每 prompt 路由一次」是另一条路，用结构换掉了逐 token 换入。
5. Agent 场景前缀复用：2605.26297（IISWC 2026）仅定性指出有效上下文缓存下多数输入 token 被跨轮复用，执行以 decode 为主；摘要无命中率数字。我们仍只能用估算：24K 前缀、每轮新增 0.5–2K，token 加权命中率约 92–98%（估算）。
6. 前缀缓存存在计时侧信道：Auditing Prompt Caching（ICML 2025）在 7 家 API 供应商发现全局缓存共享；InputSnatch 对命中前缀长度判断准确率 87.13%。端侧缓存若跨应用共享，必须按应用隔离，仅共享公开的系统前缀。
7. MoE 专家缓存与 KV 争同一份 DRAM 预算，2026 年已有工作：WiSP 的 MV-WSA 按边际收益划分，在线控制器比固定划分最多缩短 1.19 倍端到端时间（预印本，GPU）；手机上尚无公开工作（待核实）。

## 2. 证据表

| 指标 | 数值 | 条件 | 来源 | 等级 |
|---|---|---|---|---|
| AFM 3 Core Advanced 规模 | 总 20B；激活 1–4B；全量权重在 NAND flash；prompt 级路由一次，由小模型预测专家集；DRAM 只放当前专家与共享专家；未给专家数、DRAM 占用、速度、机型 | Apple ML Research 2026-06-08 博文的二手转述；DeepLearning.AI 的描述为「由独立 transformer 选择专家」，DEV 文章称并非经典 MoE，描述有分歧 | [1][2] | 二手 |
| SmallThinker 4B-A0.6B / 21B-A3B | Q4_0 内存约 1GB / 8GB；普通消费级 CPU 上均 >20 token/秒；注意力前路由（pre-attention router）使专家可在算注意力时从存储预取；NoPE-RoPE 混合稀疏注意力降 KV | 摘要口径，专家数、单专家大小摘要未给 | [3] | 预印本 |
| Qwen3-30B-A3B 结构 | 48 层，128 专家，每 token 激活 8，hidden 2048，moe_intermediate 768，4 个 KV 头，head_dim 128，最大位置 40960 | 官方 config.json | [4] | 官方 |
| 单专家大小 | 3×2048×768 = 4.72M 参数；Q4_K_M（按 4.85 bit/参数，假设）约 2.9MB；纯 4-bit 约 2.4MB | 由 [4] 计算 | [4] | 估算 |
| 0% 命中每 token IO | 8 专家 × 48 层 = 384 次 × 2.9MB ≈ 1.1GB | 同上；与 M3 一致 | [4] | 估算 |
| Qwen3-30B-A3B 的 KV | 2×48×4×128×2 = 96KiB/token；24K = 2.25GiB，32K = 3GiB | fp16 | [4] | 估算（引自 M3 并复算） |
| Qwen3.5-35B-A3B | 40 层中 10 层全注意力，2 个 KV 头，head_dim 256，256 专家，激活 8；每 token KV 20KiB | 引自 M3，本轮未复核 | M3 | 官方 config 转引 |
| Paging the Experts | 512MiB LRU 命中 0.00%，512MiB 随机淘汰 18.80%，576MiB LRU 38.58%；进程内存峰值 1.87–2.32GiB（短 prompt）、2.39–2.73GiB（一个长 prompt）；出现热降频停止事件；摘要未报 token/秒、具体机型 | iPhone，iOS 27，Swift/MLX 运行时 Routide，Qwen3.6-35B-A3B，固定路由回放，5 段 128-token 负载；Mac 对照实验 10,334 次推测加载 | [5] | 预印本 |
| FlashMoE | 缓存命中率相对 LRU / LFU 最高 +51%；加速最高 2.6 倍 | 桌面级平台，SSD 卸载，ML 缓存替换（融合近期性与频率）；摘要未给模型 | [6] | 预印本 |
| WiSP | 相对静态 offload 同预算下 decode 吞吐最高 2.0 倍；预取对单流 decode 无益；MV-WSA 在线控制器较固定划分端到端最多快 1.19 倍，保持输出逐字节一致 | RTX 3090 24GiB；专家与 KV 争 VRAM；摘要未给模型与划分值 | [7] | 预印本 |
| 其他预取/缓存工作 | EdgeMoE、Pre-gated MoE、AdapMoE（激活专家 -25%，1.35 倍）、HOBBIT（最高 9.93 倍 decode）、ProMoE（prefill 1.78 倍，decode 1.34 倍）、fMoE（命中率 +36%，延迟 -47%） | 均为作者自测，GPU / 边缘平台；本轮未复核 | M3、C4b 转引 | 预印本 / 部分会议 |
| 前缀缓存的 Agent 负载 | 多数输入 token 跨轮复用；执行以 decode 为主；依赖长生命周期 KV | ReAct 类 Agent，Gemma 与 Qwen 多配置，5 个 Agent 基准；无数值 | [8] | 预印本（IISWC 2026） |
| Auditing Prompt Caching | 在 7 家 API 供应商发现跨用户全局缓存共享；计时差可泄露用户提示与模型结构 | 统计审计；摘要只点名 OpenAI | [9] | 同行评审（ICML 2025） |
| InputSnatch | 命中前缀长度判断准确率 87.13%；医疗问答中精确疾病输入提取成功率 62%，症状描述 13.5% | 针对前缀缓存与语义缓存；受内存、限流、TTL 约束 | [10] | 预印本 |
| llama.cpp 前缀复用 | llama-server 按槽（slot）复用与新请求共享前缀的 KV；`cache_prompt` 默认开启；有主机内存 prompt cache（`--cache-ram`，PR #16391）可当额外槽使用 | 搜索摘要，未读源码 | [11][12] | 二手（官方仓库页面的搜索摘要） |

## 3. MoE 底座的负载参数建议（供第二部分负载页使用，全部为估算）

### 3.1 候选的内存账

| 候选 | 总参数 / 激活 | Q4 权重（flash） | 每 token 0% 命中 IO | 12GB 机型（Agent 侧约 4GB） | 16GB 机型（Agent 侧按约 6GB，假设） |
|---|---|---|---|---|---|
| SmallThinker-4B-A0.6B | 4B / 0.6B | 约 1GB（官方摘要）| 约 0.15GB（按激活占比估，假设）| 全驻留，无需换入 | 全驻留 |
| SmallThinker-21B-A3B | 21B / 3B | 约 8GB（官方摘要）| 约 1GB 量级（按激活占比估，假设）| 放不下，需分层，常驻 2–2.5GB | 可常驻约 3–4GB，命中率明显改善 |
| Qwen3-30B-A3B | 30.5B / 3.3B | 约 18.5GB（M3 估算）| 1.1GB | 需分层，flash 占 18.5GB | 同左 |
| Qwen3.5-35B-A3B | 35B / 约 3B | 约 21GB（M3 估算）| 待核实（单专家大小未复算）| 同左；KV 仅 20KiB/token 是优势 | 同左 |
| Gemma 4 26B A4B | 26B / 约 4B | Q4_0 约 14.4GB（官方，M3）| 待核实 | 放不下 | 放不下 |
| AFM 3 Core Advanced | 20B / 1–4B | 5–10GB（仓库估算，Apple 未给）| 不适用：prompt 级路由，换入发生在 prompt 起始处 | 机制上只需装入被选专家集 | 同左 |

### 3.2 命中率与每 token IO、速度上限（Qwen3-30B-A3B，估算）

假设：每次专家读取按 2.9MB；顺序读 4.3GB/s（UFS 4.x，本任务给定值），2–3MB 随机读有效带宽取顺序读的 70% 约 3GB/s（这一比例是假设，未找到手机实测，待核实）；不计预取与计算重叠，故为上限。M3 使用 5.8GB/s 的标称值，与本任务给定的 4.3GB/s 不同，此处以 4.3GB/s 为准并保留差异说明。

| 专家命中率 | 每 token IO | 按 3GB/s 的 token/秒上限 | 按 4.3GB/s 的上限 |
|---|---|---|---|
| 0% | 1.10GB | 2.7 | 3.9 |
| 38.58%（Paging 的 576MiB LRU，借用其值） | 0.68GB | 4.4 | 6.3 |
| 70% | 0.33GB | 9.1 | 13 |
| 80% | 0.22GB | 13.6 | 20 |
| 90% | 0.11GB | 27 | 39 |

对照基线：稠密 3B 4-bit 约 52 token/秒（约 52GB/s LPDDR 读，约占理论峰值 77GB/s 的 68%）。要使专家 IO 占用 UFS 的一半以下，约需命中率 ≥ 85–90%，并且这一读带宽会与前台应用冷启动争用。

### 3.3 2027 年 MoE 底座建议配置（估算）

| 项 | 建议值 | 说明 |
|---|---|---|
| 总参数 | 约 20–24B | 对齐 AFM 3（20B）与 SmallThinker-21B-A3B |
| 激活参数 | 约 3B（AFM 路线为 1–4B） | 与现有基线 3B 稠密的访存量同级，decode 带宽账可接上 52GB/s |
| 专家数 | 64–128 个细粒度专家，每 token 激活 6–8 | 参考 Qwen3-30B-A3B（128 选 8）。专家数是设计变量，不是已定数据 |
| 单专家大小 | Q4 约 1.5–3MB | 不低于 UFS 单次读取效率拐点（待核实，建议实测）|
| 闪存占用 | 约 8–11GB（Q4）；若含专家的 8-bit 副本供降级，则再增约 50% | 对应 SmallThinker-21B-A3B 约 8GB |
| DRAM 驻留（12GB 机型） | 非专家权重（注意力、embedding、共享专家）约 1.0GB + 专家缓存约 1.0–1.5GB = 约 2.0–2.5GB | 与 KV 约 1GB 合计已占 Agent 侧 4GB 的 3GB 以上，是第二部分「12GB 缺约 1.2GB」的来源之一 |
| DRAM 驻留（16GB 机型） | 约 3–4GB | 专家缓存放宽到约 2–2.5GB，命中率可进入 80% 以上区间（需实测）|
| 注意力与 KV 约束 | 每 token KV ≤ 约 40KiB（混合线性或滑窗），否则 24K 上下文的 KV 超 1GB | 照搬 Qwen3-30B-A3B 的全注意力 GQA（96KiB/token）会使 24K 的 KV 达 2.25GiB，是现有基线 820MiB 的 2.7 倍，MoE 带来的 DRAM 节省会被 KV 吃掉 |

要点：负载页应并列写「稠密 3B 基线」与「MoE 底座」两列，MoE 列的差异是闪存占用 +6–9GB、DRAM 权重驻留 +0.3–0.8GB 左右、闪存读带宽按命中率变化、KV 取决于架构选择。

## 4. 对关键技术的建议

### 4.1 对应的负载与瓶颈

- 基线稠密 3B：decode 约 52 token/秒，约 52GB/s LPDDR 读，权重 1.7GB 常驻。
- MoE 底座把「带宽瓶颈」改为「闪存带宽 + 命中率」：0% 命中时 IO 为 1.1GB/token，远超 UFS 能力；因此命中率是 decode 速度的第一变量。
- T3 长程任务 23–32K 上下文，KV 24K 时约 820MiB（基线）；23K prefill 约 6 秒，KV 丢失重建 6–14 秒，换入恢复 0.2–0.9 秒；Agent 侧约 4GB。前缀缓存命中决定这 6 秒是否发生。

### 4.2 问题与挑战

1. **命中率与容量的悬崖、策略依赖。** 同样 512MiB，LRU 为 0%、随机淘汰为 18.80%（[5]）。我们的推断（估算）：每 token 要走完 40–48 层 × 8 个专家，工作集在 300 个专家左右，容量略小于该工作集时，LRU 对循环式访问会整体失效；Agent 任务切换又让路由分布漂移，缓存策略必须在线可换。
2. **预取不能想当然。** WiSP 发现单流 decode 下预取与按需读争带宽而无益（[7]）；SmallThinker 的注意力前路由则从结构上提供了预取窗口（[3]）；Apple 的 prompt 级路由把换入前移到 prefill 之前（[2]，二手）。端侧到底靠哪种方式，取决于模型是否由我们决定（对应 R4）。
3. **专家与 KV 争同一份 DRAM。** Agent 多轮时 KV 增长、专家工作集相对稳定，开局的固定划分会逐步失配；WiSP 的在线重划分较固定划分最多快 1.19 倍（[7]，GPU）。手机上没有公开工作。
4. **前缀缓存的失效与泄露。** 任何会改变 KV 数值的变化（权重、量化、tokenizer、RoPE 参数、适配器、系统提示字节）都使缓存整体失效，已落闪存的 KV 会变成不可读垃圾；另有计时侧信道（[9][10]）。

### 4.3 量化目标建议值

| 指标 | 建议值 | 依据 |
|---|---|---|
| 逐 token 路由 MoE 的专家命中率 | 稳态 ≥ 85%（目标），≥ 70%（底线）| §3.2：20 token/秒需约 80%；留出前台 IO 争用余量。FlashMoE 对 LRU 最高 +51%，说明有提升空间，但手机上待实测 |
| 同容量命中率相对 LRU 的提升 | ≥ 30%（沿用 C4b 目标）| FlashMoE +51%（桌面）；Paging 同容量下随机比 LRU 高 18.8 个百分点 |
| 命中失败时的最坏 decode 退化 | 不低于 5 token/秒，且不阻塞前台 | 0% 命中上限 3.9 token/秒（估算），需降级路径（低位宽专家）兜底 |
| Agent 多轮前缀缓存 token 加权命中率 | ≥ 90% | 24K 前缀 + 0.5–2K 新增 = 92–98%（估算）；2605.26297 仅定性 |
| 前缀命中时的 TTFT | 相对全量重建（6 秒）降到 ≤ 0.5 秒（含换入）| 换入恢复 0.2–0.9 秒 |
| 缓存失效后的重建 | 单个共享系统前缀 ≤ 2 秒，后台完成，不挡交互 | 系统前缀约数千 token，按 557–3808 token/秒估（估算）|
| 专家缓存与 KV 的联合划分 | 在线可调，调整延迟 ≤ 1 秒；相对固定划分端到端 ≥ 1.1 倍 | WiSP 1.19 倍（GPU）|

### 4.4 模块级方案

1. **专家工作集作为一等记账对象**：专家缓存与 KV 块池同一份预算、同一套记账，缓存命中、换入字节、驱逐代价都进会话账本；预算由会话档位决定，档位变化时一并重划。
2. **多策略在线选择的专家缓存**：LRU、LFU、学习型（FlashMoE 类）并存，用最近窗口的命中率作为选择信号，遇到循环式访问自动切换，避免 LRU 悬崖。
3. **按请求选专家 + 预热**：若底座采用 Apple 式的 prompt 级路由，则在 prefill 前由小路由模型选出专家集并异步换入，与 prefill 重叠；若采用逐 token 路由，则用注意力前路由或跨层预测争取预取窗口，并以 WiSP 的结论为约束：预取量不得抢占按需读。
4. **三级前缀缓存树**：根=系统提示，分支=skill/工具集，叶=会话尾部；根与高频分支常驻 DRAM，其余落闪存；按块哈希索引，块格式与 KV 块池一致。
5. **带版本的缓存键与失效策略**：键 = 哈希（权重版本、量化方案、tokenizer、KV 精度、RoPE 参数、适配器标识、前缀字节）；系统更新或模型切换时整树作废并在后台按热度重建。

### 4.5 细节技术点

- **版本失效的实际代价**：前缀树里的 KV 落了闪存也一并作废，需要在 OTA 之后由后台重算最常用的几个前缀，否则首个任务要付 6–14 秒重建。
- **前缀布局纪律**（沿用 prefix-cache-agent-notes）：skill 提示之前不得有任何变量，用户情景记忆排在所有静态前缀之后，否则分支缓存整体失效。精确 token 前缀匹配，没有相似度匹配。
- **侧信道防护**：缓存按应用（UID）隔离，跨应用共享的仅限公开的系统前缀；API 层不暴露细粒度的命中/未命中时延，或对该路径做固定延时/抖动；[9] 显示云端的全局共享已被审计出泄露，端侧的威胁面是同机恶意应用。是否需要这些措施取决于 Prompt API 向第三方应用暴露的程度（待核实）。
- **端侧框架的前缀缓存现状**：llama.cpp 有槽级前缀复用与主机内存 prompt cache（[11][12]）；Apple Foundation Models 框架有 `prewarm` 之类的预热接口，Android Prompt API（ML Kit GenAI）的上下文窗口约 4K，二者对前缀缓存的具体支持，以及 MLC、MNN 是否支持，本轮均未核实到官方原文（待核实）。

## 5. 原型对比表素材

列为专家缓存 / 预取方案，行为关键要素。● 达成，◐ 部分，○ 未做或不适用。

| 要素 | FlashMoE | WiSP | Paging the Experts | SmallThinker | AFM 3（二手） | HOBBIT / ProMoE（转引） |
|---|---|---|---|---|---|---|
| 目标平台是手机 | ○（桌面） | ○（RTX 3090） | ● iPhone | ◐（CPU，非手机实测） | ● | ○ |
| 闪存作为专家池 | ● SSD | ○（CPU 内存→GPU） | ● | ● 存储预取 | ● NAND flash | ◐ |
| 学习型 / 自适应缓存策略 | ● | ◐（边际收益划分） | ○（比较 LRU / 随机） | ○ | 待核实 | ◐ |
| 预取 | ○ | ◐（验证无益） | ● 异步预取 | ● 注意力前路由 | ● prompt 级一次装入 | ● |
| 与 KV 联合划分 | ○ | ● | ○ | ◐（结构上降 KV） | 待核实 | ○ |
| 质量兜底（低位宽替换） | ○ | ○（输出逐字节一致） | ○ | ○ | 待核实 | ● HOBBIT |
| 需改模型 | ○ | ○ | ○ | ● 需自训练 | ● | ◐ |
| 公开 decode token/秒 | 摘要仅称加速 2.6 倍 | 相对静态 offload 2.0 倍 | 摘要未报 | >20（CPU） | 未公布 | 倍数 |

前缀缓存部分的对比素材（列：llama.cpp / Apple Foundation Models / Android Prompt API / MLC / MNN）：前缀复用、落盘、跨应用隔离、版本失效控制，除 llama.cpp 的槽级复用与 RAM prompt cache 外均待核实，不要在汇报里写成「已支持」。

## 6. 与其他模块的边界

- **归推理（R1）**：prefill/decode 的计算、稀疏注意力、分块与增量 prefill、专家计算本身的算子；Apple 式 prompt 级路由的模型侧设计归 R4。
- **归模型内存管理（本模块）**：专家缓存、专家换入与预取调度、KV 块池与前缀树、版本失效、与 KV 的预算划分、闪存读 IO 调度。
- **归 R3（闪存侧计算）**：把冷专家放在闪存内计算的方案，属于另一条路，需与 §3.2 的 IO 数字对比盈亏点。
- **归通用内存管理与 IO 调度**：专家换入与前台冷启动的读带宽争用、memcg 水线、闪存寿命预算。
- **归记忆服务（Agent 层）**：KV 被判定不再恢复后是否生成摘要，不由本模块决定。

## 7. 待核实

1. AFM 3 Core Advanced 的专家数、DRAM 占用、速度、机型：Apple 博文原文（machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models，由 VentureBeat 转述，本轮未取得）及后续技术报告。
2. 2605.26297 全文中的前缀复用比例、Agent 轨迹各轮输入/输出 token。
3. Paging the Experts 全文：机型、token/秒、路由局部性统计、功耗。
4. UFS 4.x 上 2–3MB 随机读的有效带宽，及 UFS 读取效率拐点。
5. Apple prewarm、Android Prompt API、MLC、MNN 的前缀缓存支持与行为；llama.cpp 相关结论仅来自搜索摘要。
6. Qwen3.5-35B-A3B、Gemma 4 26B A4B 单专家大小与每 token IO；SmallThinker 专家数与单专家大小。
7. 手机侧专家缓存与 KV 联合划分的公开工作（目前只找到 GPU 上的 WiSP，及搜索到的 NeurIPS 2026 listing 和 PagedWeight（2607.16184），均未核实全文）。
8. 单 prompt 路由（Apple）与逐 token 路由在 Agent 任务切换下的质量与命中率差异，未找到公开数据。

## 参考文献

1. VentureBeat，On-device AI agents hit a hard memory limit; Apple's new architecture routes around it（转述 Apple ML Research 2026-06-08 博文）：https://venturebeat.com/technology/on-device-ai-agents-hit-a-hard-memory-limit-apples-new-architecture-routes-around-it，2026
2. DeepLearning.AI The Batch，Large-Model AI for Apple Devices：https://www.deeplearning.ai/the-batch/large-model-ai-for-apple-devices，2026（仅由搜索摘要获知）
3. SmallThinker: A Family of Efficient LLMs Natively Trained for Local Deployment：https://arxiv.org/abs/2507.20984，2025-07
4. Qwen3-30B-A3B config.json：https://huggingface.co/Qwen/Qwen3-30B-A3B/raw/main/config.json
5. Paging the Experts: A Reproducible Characterization of Flash-Backed MoE Inference on iPhone：https://arxiv.org/abs/2609.29032，2026-09-24
6. FlashMoE: Reducing SSD I/O Bottlenecks via ML-Based Cache Replacement for MoE Inference on Edge Devices：https://arxiv.org/abs/2601.17063，2026-01
7. WiSP: A Working-Set View of MoE Serving on Extremely Low-Resource Hardware：https://arxiv.org/abs/2606.21868，2026-06-20（v2 2026-08-30）
8. Agentic AI Workload Characteristics：https://arxiv.org/abs/2605.26297，2026-05-25（v2 2026-09-21，IISWC 2026）
9. Auditing Prompt Caching in Language Model APIs：https://arxiv.org/abs/2502.07776，2025-02（ICML 2025）
10. InputSnatch: Stealing Input in LLM Services via Timing Side-Channel Attacks：https://arxiv.org/abs/2411.18191，2024-11-27
11. llama.cpp PR #16391（主机内存 prompt cache）：https://github.com/ggml-org/llama.cpp/pull/16391（搜索摘要）
12. llama.cpp 讨论 #13606（KV cache reuse with llama-server）：https://github.com/ggml-org/llama.cpp/discussions/13606（搜索摘要）
13. 仓库内：`proposals/2027-agentos-ai-graphics/notes/M3-model-memory.md`、`proposals/agentos-components/notes/C4b-model-memory.md`、`insight/N+1/on-device-agent-memory-system/prefix-cache-agent-notes.md`、`proposals/agentos-components/report/3-内存管理.md` 3.4（EdgeMoE、AdapMoE、HOBBIT、ProMoE、fMoE、EStream 等数字均转引自此）

# 原型对比：C4 内存管理

> 2026-11-07；检索 WebFetch 2 / WebSearch 0（核验 LLMS 摘要页、Apple AFM 3 官方页）；其余证据取自 C4-内存管理.md 与 C4a/C4b 笔记，参考编号沿用 C4 §8（A/B/K 系列），新增 P1/P2。
> 列的取舍：按 brief 候选保留 7 个原型，学术 demo 同时列 LLMS 与 PowerInfer-2（二者分别代表 KV 换出与权重换入，缺一则两条主线对不上），未替换候选。
> 符号：● 已具备 / ◐ 部分具备 / ○ 缺失（含「公开资料空白」，已在说明中注明）/ — 不适用。

## 1 对比表

| 要素 | Android（LMKD + memcg + Android 17 Memory Limiter） | iOS（Jetsam + 内存压缩 + increased-memory-limit） | HarmonyOS / OpenHarmony（ESWAP 等） | Linux 主线（MGLRU、dmem、dma-buf memcg RFC） | Apple AFM 3 运行时 | vLLM PagedAttention（云端参照） | LLMS（学术） | PowerInfer-2（学术） |
|---|---|---|---|---|---|---|---|---|
| **简介** | Google，2026；按进程 memcg 设 high / swap.max，节流优先于杀 | Apple；按优先级带与进程上限杀，另有压缩内存与授权加限 | 华为；应用自愿释放回调、Purgeable；OH 文档有 zswapd 换出 | 社区；MGLRU 回收、dmem 6.14 合入、dma-buf 计费 RFC（2026-05） | Apple，WWDC26（2026-06）；20B 稀疏，全量存 NAND，每请求激活 1–4B | UC Berkeley 等，2023；服务器端 KV 分块与前缀共享引擎 | Yin、Xu、Liu 等，arXiv 2024-03；LLM 作系统服务，分块 KV 压缩换出 | 上交 IPADS，2024-06；手机上神经元簇加 Flash IO 流水 |
| **1 模型内存可见性与记账（含 dma-buf / GPU / NPU）** | ◐ 限额口径为匿名页加 swap；dma-buf、GPU 是否计入未说明 [A1][A2] | ○ footprint 口径未核实，资料空白 [A25] | ○ 无公开资料 [A27] | ◐ dmem 已合入但 UMA 手机不适用；dma-buf memcg 仍 RFC [A4][A5] | ○ 官方页未述内存归属 [P2] | ● 引擎自管块池，显存预算内可见 [B1] | ● LLM 上下文内存与 App 内存分开管理 [A34] | — 单应用运行时，无 OS 级记账 |
| **2 共享服务的代分配归账** | ○ 按进程单一属主；pidfd 计费仅 RFC [A4][K3] | ○ 无公开资料 | ○ 无公开资料 | ◐ RFC 在分配时计到客户端 cgroup，未合入 [A4] | ○ 守护进程归属无公开说明 [A11] | — 单租户引擎，不涉 OS 归账 | ◐ 服务内统一管理，无跨进程归账原语 [A34] | — |
| **3 KV cache 管理（分页 / 压缩 / 换出 / 重算）** | ○ 系统层无 KV 语义，仅匿名页 / dma-buf [A11] | ○ 系统层无公开机制 | ○ 无公开资料 | — 内核无 KV 语义 | ◐ 2025 端侧模型 KV 共享降 37.5%；AFM 3 页面未述 KV [B33][P2] | ● 分页 + 前缀共享；分层卸载见衍生系统 [B1][B15] | ● 分块压缩、换出、IO 与重算流水 [P1] | — 聚焦权重，不管 KV |
| **4 权重分层与按需换入** | ◐ mmap 文件页可回收；PLE 默认状态待核 [B21] | ◐ 平台模型走 AFM 3，系统层无通用机制 [K10] | ○ 无公开资料 | ◐ 缺页 / 页缓存可用，无模型语义 [A30] | ● 全量存 NAND，请求级专家换入 DRAM [P2] | — 权重常驻显存 | — 只管 KV | ● 神经元簇按需读 Flash，47B 达 11.68 tok/s [B18] |
| **5 与应用内存的统一回收与 QoS** | ◐ 可见 / 不可见分档，有天花板无地板 [A2] | ◐ 优先级带加上限，模型内存不区分 [A24] | ◐ 合作式回调；OH 有 per-memcg 参数 [A27][A28] | ◐ memcg min / low / high 具备，手机无保护契约 [A30] | ○ 与应用的仲裁无公开资料 | — 无应用内存可争 | ◐ 上下文内存独立管理，非统一回收 [A34] | ○ 运行时自管 |
| **6 冷热识别（MGLRU / 硬件采样）** | ◐ 荣耀约 7000 万台用 MGLRU；Google 语义诉求未满足 [A9] | ○ 无公开资料 | ◐ OH 文档有 score、refault 参数，Kimi 转引未核 | ◐ MGLRU 仍在争论；无硬件采样入主线 [A8][A9] | ◐ 专家集 prefill 选定、生成中低频重选 [P2] | ◐ 块级引用与淘汰，非页冷热 [B1] | ● LCTRU：按压缩容忍度加最近使用淘汰 [P1] | ◐ 神经元冷热分区，细节待核 [B18] |
| **7 压缩交换（zram / zswap）** | ● zRAM，swap.max 封顶 [A1][A2] | ◐ 有内存压缩，机制细节待核 [A24] | ◐ OH：zram 压缩页加密换出到 ESwap 分区，商用待核 | ● zram / zswap，含 zswap.writeback 开关 [K7] | — 模型不走交换 | — | ◐ 压缩对象是 KV 块，非页 [P1] | — |
| **8 模型加载 IO 与零拷贝映射** | ◐ dma-buf fd 共享，QNN 仅收 DMA-BUF [K8] | ○ 无公开资料 | ○ 无公开资料 | ◐ dma-buf、mmap 机制在，无模型加载接口 | ◐ NAND 到 DRAM 换入，细节未公开 [P2] | — 云端不敏感 | — | ● 大块对齐读加 IO 流水，应对 UFS IOPS 瓶颈 [B17][B18] |

## 2 读表结论

1. **已普遍做成的只有「传统匿名页」那一层。** 压缩交换（zRAM / zswap）、memcg 配额、MGLRU 类回收在 Android 与 Linux 主线成熟，Android 17 把 memcg 做成平台默认 [A1][A2]。这些机制对模型内存没有语义。
2. **模型内存的三件事在所有商业 OS 与内核里都缺失或只有雏形：** 统一记账（dma-buf / GPU / NPU 在限额之外）、共享服务的代分配归账、OS 层的 KV 管理。Linux 上这些仍停留在 RFC（A4）或不适用 UMA 手机（dmem）。iOS 与 HarmonyOS 的大量 ○ 多是资料空白，不是已证无。
3. **KV 的分块、压缩、换出只在云端引擎与学术 demo 里做成。** vLLM 做块化与前缀共享，LLMS 做分块压缩换出加 IO 与重算流水（上下文切换延迟最多降两个数量级，论文自报）[P1]。没有任何手机平台公开提供系统级 KV 服务。
4. **权重分层已有两个端侧量产先例，且都避开逐 token 随机访问。** AFM 3 做请求级专家驻留 [P2]，Gemma 3n PLE 做逐 token 查表 [B21]。PowerInfer-2 证明手机上 47B 可行，但依赖稀疏化模型 [B18]。
5. **端侧与云端的差距在「谁来管」。** 云端引擎自己管全部显存，记账与回收天然统一；手机上推理运行时、OS、芯片厂商 NPU 驱动三方各管一段，推理运行时的内存对 OS 只是不透明的匿名页或 dma-buf。
6. **学术 demo 领先产品的地方：** LLMS 把「LLM 上下文内存」与应用内存分开管理，并有按压缩容忍度的淘汰策略；PowerInfer-2 与 Neuralink 针对 UFS 小块 IOPS 做了布局与合并读。产品侧没有对应的公开实现。

## 3 格子说明（只对 ◐ 与有争议的格子）

- **Android 行 1（◐）**：Android 17 限额口径为匿名 RSS 加 swap（`MemoryLimiter:AnonSwap`），官方文档未说 dma-buf、GPU 是否计入，故不能判 ●，也不能判 ○ [A1][A2]。
- **Android 行 4（◐）**：Gemma 3n 的 PLE 有官方文档，但它是模型侧特性，Android 平台是否默认启用、是否落闪存待核实 [B21]。
- **Linux 行 1（◐）**：dmem 已于 6.14 合入，但前提是独立的设备内存区域，UMA 手机上基本不成立；dma-buf memcg 计费 2026-05 仍为 RFC [A4][A5][K1]。设计文档中「上游已补齐」的说法与此冲突，不采用。
- **iOS 行 7（◐）**：C4 只记「压缩内存，细节待核实」，未取得官方文档，因此未判 ●。
- **HarmonyOS 行 6、7（◐）**：ESWAP 参数来自 OpenHarmony 官方文档经 Kimi 转引，原文未抓；商用 HarmonyOS NEXT 是否有此机制未核实（C4 待核实 6、19）。
- **AFM 3 行 3（◐）**：KV 共享降 37.5% 是 Apple 2025 端侧模型的数据（C4 §1.2 引自 B33 / M3），AFM 3 官方页本轮重读未提 KV [P2]。
- **AFM 3 行 4（●）**：官方页明确「全量存 NAND，请求级选专家并周期性重选，路由专家按需换入 DRAM」，不做逐 token 换入 [P2]。DRAM 预算、重选频率、出货机型均未公开。
- **vLLM 行 1（●）与 行 6（◐）**：行 1 指其块池在单进程内自管，不是 OS 级记账；行 6 的块级淘汰描述来自对 PagedAttention 的一般理解，本轮未逐篇核实。
- **PowerInfer-2 行 6（◐）**：神经元冷热分区的具体做法，C4 待核实 21 也提示设计文档与论文原文可能不一致。
- **LLMS 行 1、5（●、◐）**：摘要页明确「分开管理 app 与 LLM 上下文内存」[P1]；但这是服务内部分离，不等于与应用内存统一回收，故行 5 判 ◐。LLMS 被 SenSys 2026 录用一事为 Kimi 单源，未核。

## 4 参考资料

| 编号 | 标题 | 机构/作者 | URL | 日期 | 核验情况 |
|---|---|---|---|---|---|
| A1 | App broader memory limits | Android Developers Blog | https://android-developers.googleblog.com/2026/08/app-broader-memory-limits.html | 2026-08 | 引自 C4，本轮未复抓 |
| A2 | Memory Limiter | AOSP | https://source.android.com/docs/core/perf/memory-limiter | 2026 | 同上 |
| A4 | memcg: dma-buf per-cgroup accounting via pid_fd（RFC） | LKML | https://lkml.iu.edu/2605.1/07247.html | 2026-05-12 | 同上 |
| A5 | DMEM cgroup 将入 Linux 6.14 | Phoronix | https://www.phoronix.com/news/DMEM-cgroup-vRAM-Control | 2025-01 | 同上；合入版本由 K1 核实 |
| A8 / A9 | MGLRU 相关 LWN 报道 | LWN | https://lwn.net/Articles/1060967/ ；https://lwn.net/Articles/1072866/ | 2026 | 同上；荣耀规模为二手报道 |
| A11 | mzCache | arXiv 2609.01338 | https://arxiv.org/abs/2609.01338 | 2026-09 | 同上 |
| A24 | xnu memorystatus 文档 | Apple OSS | https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_kills.md | 持续 | 同上 |
| A25 | iOS 26 内存上限开发者论坛帖 | Apple Developer Forums | https://developer.apple.com/forums/thread/834805 | 2026 | D 级，开发者自述 |
| A27 / A28 | HarmonyOS onMemoryLevel；Purgeable Memory C API | 华为 / 社区 | https://developer.huawei.com/consumer/cn/doc/doccenter-references/api/capi-memory-purgmem | — | 同上 |
| A30 | Linux cgroup v2 文档 | kernel.org | https://docs.kernel.org/admin-guide/cgroup-v2.html | 持续 | 同上 |
| A34 | LLM as a System Service on Mobile Devices | arXiv 2403.11805 | https://arxiv.org/pdf/2403.11805 | 2024-03 | 同 P1 |
| B1 | vAttention（含 PagedAttention 对比） | MSR India | https://arxiv.org/abs/2405.04437 | ASPLOS 2025 | 引自 C4；PagedAttention 原文未单独引用 |
| B15 | Mooncake | 月之暗面等 | https://github.com/kvcache-ai/Mooncake | FAST 2025 | 引自 C4 |
| B17 | Neuralink（原 Ripple） | 清华等 | https://arxiv.org/abs/2410.19274 | ASPLOS 2025 | 引自 C4 |
| B18 | PowerInfer-2 | 上交 IPADS | https://arxiv.org/abs/2406.06282 | 2024-06 | 引自 C4，数字来自其摘要 |
| B21 | Gemma 3n model overview | Google | https://ai.google.dev/gemma/docs/3n | 2025 | 引自 C4 |
| B33 | Hybrid attention 架构说明 | Raschka | https://sebastianraschka.com/llm-architecture-gallery/hybrid-attention/ | 2026 | C 级；Apple 37.5% 经 M3 转引 |
| K1 | Linux 6.14 特性列表 | KernelNewbies | https://kernelnewbies.org/Linux_6.14 | 2025-03-24 | C4 已抓 |
| K3 | recharge-on-behalf；dma-buf memcg RFC 0/5 | Kimi 调研 / lists.linaro.org | https://lists.linaro.org/ | 2026-05 | RFC 已抓；原语为推断 |
| K7 | cgroup-v2 文档（memory.zswap.writeback） | kernel.org | https://docs.kernel.org/admin-guide/cgroup-v2.html | — | C4 已抓 |
| K8 | QNN 只接受 DMA-BUF 共享内存 | arXiv 2610.16244 | https://arxiv.org/abs/2610.16244 | 2026-09 | C4 已抓正文；非高通官方 |
| K10 | Introducing the third generation of Apple Foundation Models | Apple ML Research | https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models | 2026-06-08 | C4 已读；本轮复核（见 P2） |
| P1 | LLM as a System Service on Mobile Devices（摘要页） | Wangsong Yin、Mengwei Xu、Yuanchun Li、Xuanzhe Liu | https://arxiv.org/abs/2403.11805 | 2024-03-18 | 本轮已抓摘要；机构页面未列；延迟降幅为论文自报 |
| P2 | AFM 3 官方页（Core Advanced 段） | Apple ML Research | 同 K10 | 2026-06-08 | 本轮已抓：全量存 NAND、请求级选专家并周期重选；无 DRAM 数值；未提 KV |

## 5 待核实

1. iOS 与 HarmonyOS 各行的 ○ 多为资料空白：iOS footprint 是否含压缩内存与 IOSurface / Metal 缓冲；Apple Foundation Models 守护进程与 AICore 的内存归属（C4 待核实 5）。
2. HarmonyOS NEXT 的页回收与换出机制；ESWAP 在商用 HarmonyOS 中是否存在（C4 待核实 6、19）。
3. Android 17 限额是否计入 dma-buf / GPU（C4 待核实 2）。
4. AFM 3 的 DRAM 预算、专家重选频率、NAND 读写量与出货机型（C4 待核实 23）；KV 是否有专门处理。
5. LLMS 的发表状态（SenSys 2026 为 Kimi 单源）、作者机构、实验设备与基线细节。
6. vLLM 行 6 的块级淘汰与 GPU↔CPU swap 现状（C4 待核实 20）；本轮未对 vLLM 一手文档做抓取。
7. PowerInfer-2 的冷热分区细节与设计文档描述的一致性（C4 待核实 21）；与 LLM in a Flash 的取舍未做对比。
8. Windows 与 Copilot+ 的内存可见性不在本表范围，未检索。

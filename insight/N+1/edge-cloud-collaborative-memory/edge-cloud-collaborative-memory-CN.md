# 端云协同内存管理：按用户、按场景的冷热识别

> 面向终端设备的「端云协同内存管理」技术调研：端侧跑轻量个性化小模型，云侧跑大模型做训练和聚合，两边配合把内存冷热策略从「所有用户一套规则」升级到「按用户、按场景预测哪些 App 和页面该留、该换」。本文对比*原始方案*（设备本地通用策略：LRU、LMKD oom_adj、固定 zram）和*演进方案*（端云协同 + 个性化场景冷热识别 + 云侧训练并下发策略）。是本 N+1 调研集中端侧 KV Cache、分级内存、带宽等主题的姊妹篇。

## 1. 范围与方法

**领域界定。** 资源受限终端（手机、平板、PC、边缘板卡）上的内存管理。核心决策是「什么留在 RAM 里、什么压缩/换出、什么预取」，而且这个决策要按每个用户、每个使用场景来做，借助云侧协同。这里的「冷热」包括粗粒度（哪个 App/进程常驻 vs 被冻结/杀掉）和细粒度（哪些页面预取、回收或放入 zram）。

**「原始」与「演进」的含义。** *原始方案*是**设备本地的通用策略**：OS 按最近访问时间和静态重要性分数决定淘汰（Linux/Android LRU、LMKD 的 `oom_adj_score`、kswapd），内存扩展靠用户手动选一个固定大小（如 Samsung RAM Plus 的 2/4/6/8 GB zram）。所有用户一套规则。*演进方案*是**端云协同的个性化内存管理**：端侧小模型根据*当前用户*的实时场景预测冷热，驱动预取/回收/常驻；云侧大模型聚合全舰队的场景模式，训练个性化策略，给每个用户下发专属 adapter；用「智能请求」门控——只在端侧拿不准时才联系云侧，原始行为数据留在设备上。

**来源与主要族系。** 16 个主要来源，分三族：(a) 端云协同 ML 系统与个性化——Walle（OSDI'22）、DCCL（KDD'21）、LSC4Rec（KDD'25）、两篇 2025 年端侧 SLM/云侧 LLM 综述；(b) 端侧内存管理机制——Android LMKD、缓存应用冻结器、AppFlow、ElasticZRAM、Samsung RAM Plus；(c) 端侧使用预测及其开销——DeepApp、Microsoft 预测/预取、Kleio（ML 页热度先例）、端侧行为日志开销。类型涵盖同行评审系统/ML 论文、OS 文档与厂商资料。

## 2. 问题背景

**系统要做什么。** 设备 RAM 有限且共享（扣除 OS 后通常只有 4–8 GB 可用），要把*这个*用户马上要用的 App 和页面留在内存里，其余压缩或换出，同时预取即将用到的——让启动秒开，且不误杀重要进程。

**为什么难。** 冷热因人、因场景而异：通勤者早 8 点的工作集和玩家晚 9 点的完全不同，单一固定规则对多数用户都会判断错。而做这个决策的设备本身**数据少、标签少、算力紧**——只看得到自己一段短的、非 IID 的历史。同时内存本身就是稀缺资源，预测器必须足够轻量，能跑在它要优化的那台设备上。

**为什么原始方案不够了。** GB 级 App（端侧 LLM、富媒体编辑器）加上重度多任务，一次淘汰错误就是数秒级的冷启动；**86.6% 的 GB 级冷启动已经超过了 1 秒的可用性门槛** [AppFlow]。对所有用户用同一套静态策略，无法给出当下负载要求的按用户、按场景精度。

## 3. 具体问题与瓶颈证据

### 具体问题

1. **通用策略对个体用户的工作集判断错** —— LRU/LMKD 按最近访问和静态重要性分数淘汰，不区分用户是谁、处于什么场景，导致错误的 App 被冻结/杀掉，再打开就是冷启动；86.6% 的 GB 级冷启动超过 1 秒门槛 [AppFlow]。
2. **静态、手动的内存配置不随场景变化** —— Samsung RAM Plus 让*用户*一次性选一个固定 zram 大小（2/4/6/8 GB），之后不会随当前场景或用户习惯自动调整 [Samsung RAM Plus]。
3. **端侧学习器缺数据、缺算力、缺标签** —— 单台设备只有自己一段短的、非 IID 历史和有限算力，无法独立训练出好的个性化冷热预测器 [DCCL；端侧 SLM/云侧 LLM 综述]。
4. **频繁调用云端代价高且有隐私风险** —— 每次决策都上传原始行为、调用云模型，既费带宽/电量又暴露隐私；云端推理单样本成本约为端侧小模型的 70 倍（0.10082 s vs 0.00143 s）[LSC4Rec]。

### 瓶颈证据

| 症状 | 数值 | 来源 |
|---|---|---|
| GB 级冷启动超过 1 秒门槛的比例 | 86.6% | [AppFlow] |
| 冷启动延迟：通用 → 预测驱动 | 2 s → 690 ms（−66.5%） | [AppFlow] |
| 单样本推理成本：端侧 vs 云侧 | 0.00143 s vs 0.10082 s（约 70×） | [LSC4Rec] |
| 端云个性化带来的精度增益 | +3.52% 至 +41.32% | [DCCL] |
| 更多 App 缓存在 RAM → 更少冷启动 | 最高 30% | [缓存应用冻结器] |

*解读：* 瓶颈不在 RAM 容量，而在*决策质量*。用通用策略做「常驻/淘汰/预取」决策时，86.6% 的大 App 启动超过 1 秒门槛；换成预测驱动的个性化策略后，同样的启动降到 690 ms，而且每次决策成本仍比一次云端往返低约 70 倍。收益来自更好、更便宜、按用户定制的决策，而不是更多内存。

## 4. 架构：原始方案 vs 演进方案

![端云协同：设备本地通用 vs 端云个性化 架构图](assets/edge-cloud-collaborative-memory-arch.svg)

*图：原始方案与演进方案的架构对照（详细文本版见下方 ASCII 图）。*

**原始方案 —— 设备本地通用冷热策略**

```
      用户行为（仅本地）
              |
              v   观察（最近访问 / oom_adj）
   +----------------------------------+
   |  设备                            |
   |   +--------------------------+   |
   |   | 通用策略                 |   |   所有人一套规则
   |   | LRU / LMKD oom_adj /     |   |
   |   | 固定 zram 大小           |   |
   |   +-----------+--------------+   |
   |               | 淘汰 / 常驻      |
   |               v                  |
   |   +--------------------------+   |
   |   |  RAM（有界、共享）       |   |
   |   +--------------------------+   |
   +----------------------------------+
   云侧：不参与。无个性化，无跨用户学习。
```

*原始：设备按最近访问和静态重要性分数决定常驻/淘汰；所有用户一套规则，云侧不参与。*

**演进方案 —— 端云协同的个性化场景冷热**

```
      用户行为（留在设备上）
              |
              v  * 本地抽取场景特征
   +-----------------------------------+   * 下发按用户的策略 / 适配器
   |  设备（小脑）                     | <---------------------------------+
   |   +---------------------------+   |                                   |
   |   | * 个性化小模型            |   |     +-----------------------------+--+
   |   |   场景冷热预测器          |   |     |  云侧（大脑）                  |
   |   +-----------+---------------+   |     |  * 大模型 / 训练器              |
   |   * 预测      | 驱动              |     |  * 聚合全舰队场景               |
   |               v                   |     |    (MetaPatch / 蒸馏)           |
   |   +---------------------------+   |     +-----------------------------+--+
   |   | 预取 / 回收 / 常驻 /      |   |   * 智能请求                      ^
   |   | zram（按 App、按页面）    |   |------------------------------------+
   |   +-----------+---------------+   |   仅在不确定时上传；
   |               v                   |   原始行为保持私有
   |   +---------------------------+   |
   |   |  RAM（有界、共享）        |   |
   |   +---------------------------+   |
   +-----------------------------------+
```

*演进：端侧小模型根据当前用户的实时场景预测冷热，驱动预取/回收/常驻；云侧聚合全舰队场景、训练个性化策略、下发按用户的 adapter；智能请求门控只在端侧拿不准时才联系云侧。新增/变更部分以 `*` 标记。*

## 5. 演进方案为何有效，又还没解决什么

### 为何有效

- **通用策略对个体用户判断错** —— 用个性化、场景感知的预测器替代最近访问/oom_adj，让常驻/淘汰/预取决策贴合*当前*用户；预测驱动的调度把 GB 冷启动延迟从 2 s 降到 690 ms（−66.5%），95% 的启动控制在 1 s 内 [AppFlow]。
- **静态、手动的内存配置不随场景变化** —— 云侧训练的策略按场景自动调整，替代用户手选的固定 zram 大小，不再需要一次性手动设定 [Samsung RAM Plus 基线；DCCL]。
- **端侧学习器缺数据、缺算力、缺标签** —— 云侧聚合全舰队场景、蒸馏出强的共享骨干，每台设备只需在此基础上按用户做小幅 patch（MetaPatch），比「纯端侧」或「纯云侧」训练高 +3.52% 至 +41.32% [DCCL]。
- **频繁调用云端代价高且有隐私风险** —— 智能请求门控只在端云分歧超阈值时才联系云侧，在仅 5% 请求频率下取得峰值 +36.66% NDCG@5，原始行为留在设备上 [LSC4Rec]。

### 还没解决什么

- **个性化冷启动** —— 全新用户或从未见过的场景，本地无历史、舰队也暂无匹配，系统只能退回通用策略，直到积累够数据 [DCCL；端侧 SLM/云侧 LLM 综述]。
- **预测器自身的端侧占用** —— 按用户的模型、特征存储、行为日志，都要在它所服务的设备上消耗 RAM、flash 和电量；目前没有内存策略模型的端侧占用预算公开，行为日志本身也耗存储 [端侧 SLM/云侧 LLM 综述；行为日志开销研究]。
- **行为特征的隐私与合规** —— 即便有智能请求，场景特征和上传的增量仍是个人数据；内存策略闭环中的加密、纯端侧模式、用户可见的同意机制都没有定义。
- **缺乏标准的 OS 策略下发接口** —— Android/iOS 的内存子系统（LMKD、zram、PSI）目前无法被一个按用户的云侧策略编程；落地需要 OS/厂商层面的配合，而这个接口还不存在。
- **过时与多数偏置** —— 用户习惯会漂移，下发的策略在两次更新之间可能过时；云侧聚合也可能偏向典型用户，对非典型用户效果差 [DCCL]。

## 6. 对比表

| 维度 | 原始（设备本地通用） | 演进（端云协同个性化） | 提升 |
|---|---|---|---|
| 个性化粒度 | 所有用户一套策略 | 按用户/按场景 | 无 → 按用户 [ref 2] |
| 冷启动延迟（GB App） | 2 s（通用调度） | 690 ms（预测驱动） | −66.5% [ref 9] |
| GB 冷启动在 1 s 门槛内的比例 | 13.4%（86.6% 超过） | 95% | +81.6 pts [ref 9] |
| 预测/推荐精度 | 仅云或仅端基线 | +3.52~41.32%（DCCL）；+9.38~16.18% 均值（LSC4Rec） | + [ref 2, ref 3] |
| 云端调用频率 | 每次决策（100%） | 5%（智能请求） | 调用 −95%，仍 +36.66% NDCG@5 [ref 3] |
| 单样本推理成本 | 0.10082 s（云模型） | 0.00143 s（端侧模型） | 约 70× 更便宜 [ref 3] |
| 原始行为隐私暴露 | 为云决策上传 | 留在设备；仅不确定时传增量 | 是 → 降低 [ref 3] |
| 端侧开销（预测器 + 日志） | 0 额外模型 | +1 按用户模型 + 特征日志 | 回退：+RAM/电量，n/a（无公开预算）[ref 4] |

## 7. 一词概括

**Personalized（按用户定制）** —— 端云闭环用一个按用户、按场景的预测器替代单一通用冷热规则（云侧学全舰队模式、端侧按用户做 patch），把 GB 冷启动延迟降低 66.5%（2 s → 690 ms），同时只在 5% 的情况下调用云侧 [AppFlow；LSC4Rec]。

## 8. 开放问题与注意事项

- **尚无端到端落地的个性化*内存*策略。** 文中数字分别来自端云*推荐*（DCCL、LSC4Rec）和端侧*预测驱动调度*（AppFlow）；目前没有已发表系统在舰队规模上把内存冷热的完整闭环跑通。本对比应视为「拼接」而非端到端实测。
- **闭环的端侧成本未实测。** 按用户预测器 + 特征日志在手机上、与其所管理的 App 并存的 RAM/flash/电量，没有公开预算。
- **隐私/合规面。** 场景特征与上传增量是个人数据；纯端侧模式、加密、内存策略闭环的同意机制均未处理。
- **需要 OS/厂商配合。** 云侧下发的按用户冷热策略，需要一个可编程 LMKD/zram/PSI 的接口，而主流 OS 目前都没有提供。
- **漂移与公平。** 习惯漂移使下发策略过时；舰队聚合可能对非典型用户效果差。更新节奏与按用户回退策略待研究。
- **来年复查。** 端侧 LLM 个性化、Android 内存效率工作（如 Android 17 内存优化）、端侧 SLM/云侧 LLM 框架是否会产出一个标准的内存策略接口。

## 9. 参考文献

### 端云协同 ML 与个性化

1. **Walle** — Lv et al., 2022. "Walle: An End-to-End, General-Purpose, and Large-Scale Production System for Device-Cloud Collaborative Machine Learning." USENIX OSDI 2022. arXiv: 2205.14833. URL: https://arxiv.org/abs/2205.14833 。本地副本：[sources/walle-osdi22-2205.14833.md](sources/walle-osdi22-2205.14833.md)
2. **DCCL** — Yao et al., 2021. "Device-Cloud Collaborative Learning for Recommendation." ACM SIGKDD 2021. arXiv: 2104.06624. URL: https://arxiv.org/abs/2104.06624 。本地副本：[sources/dccl-kdd21-2104.06624.md](sources/dccl-kdd21-2104.06624.md)
3. **LSC4Rec** — Lv et al., 2025. "Collaboration of Large Language Models and Small Recommendation Models for Device-Cloud Recommendation." ACM SIGKDD 2025. arXiv: 2501.05647. URL: https://arxiv.org/abs/2501.05647 。代码：https://github.com/HelloZicky/LSC4Rec 。本地副本：[sources/lsc4rec-kdd25-2501.05647.md](sources/lsc4rec-kdd25-2501.05647.md)
4. **端侧小模型 + 云侧大模型综述** — 2025. "Collaborative Learning of On-Device Small Model and Cloud-Based Large Model: Advances and Future Directions." arXiv: 2504.15300. URL: https://arxiv.org/abs/2504.15300
5. **端侧 SLM / 云侧 LLM 综述** — 2025. "Collaborative Inference and Learning between Edge SLMs and Cloud LLMs: A Survey of Algorithms, Execution, and Open Challenges." arXiv: 2507.16731. URL: https://arxiv.org/abs/2507.16731
6. **多模态 LLM 的云-端协同学习** — Wang et al., 2024. CVPR 2024. arXiv: 2312.16279. URL: https://arxiv.org/abs/2312.16279

### 端侧内存管理机制

7. **Android LMKD** — Android Open Source Project. "Low memory killer daemon." URL: https://source.android.com/docs/core/perf/lmkd
8. **缓存应用冻结器** — Android Open Source Project. "Cached apps freezer"（最高减少 30% 冷启动）. URL: https://source.android.com/docs/core/perf/cached-apps-freezer
9. **AppFlow** — 2026. "AppFlow: Memory Scheduling for Cold Launch of Large Apps on Mobile and Vehicle Systems." arXiv: 2603.17259. URL: https://arxiv.org/abs/2603.17259 。本地副本：[sources/appflow-2603.17259.md](sources/appflow-2603.17259.md)
10. **ElasticZRAM** — 2024. "ElasticZRAM: Revisiting ZRAM for Swapping on Mobile Devices." ACM/IEEE DAC 2024. URL: https://dl.acm.org/doi/10.1145/3649329.3655943
11. **Samsung RAM Plus** — Samsung. "What is RAM Plus and How to Use It?" URL: https://www.samsung.com/sg/support/mobile-devices/what-is-ram-plus-and-how-to-use-it/
12. **基于冻结的内存-进程协同设计** — 2025. "Freezing-based Memory and Process Co-design for User Experience on Resource-limited Mobile Devices." ACM TOCS. URL: https://dl.acm.org/doi/10.1145/3714409

### 端侧使用预测及其开销

13. **DeepApp** — 2020. "DeepApp: Predicting Personalized Smartphone App Usage via Context-Aware Multi-Task Learning." URL: https://www.researchgate.net/publication/346558717
14. **预测与预取实践** — Parate et al., Microsoft Research. "Practical Prediction and Prefetch for Faster Access to Applications on Mobile Phones." URL: https://www.microsoft.com/en-us/research/publication/practical-prediction-and-prefetch-for-faster-access-to-applications-on-mobile-phones/
15. **Kleio** — Doudali et al., 2019. "Kleio: A Hybrid Memory Page Scheduler with Machine Intelligence." ACM HPDC 2019（数据中心 ML 页热度先例）. URL: https://dl.acm.org/doi/10.1145/3307681.3325398
16. **端侧行为日志开销** — 2025. "Optimizing Storage Overhead of User Behavior Log for ML-embedded Mobile Apps." arXiv: 2510.13405. URL: https://arxiv.org/abs/2510.13405

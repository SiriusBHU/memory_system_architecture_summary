# Kimi 对照差异：C1 推理框架与推理能力

> 对照日期 2026-11-05；核验方式：WebFetch 10 次 / WebSearch 1 次（额度用尽）。
> 总评：Kimi 在 C1 的强项是学术侧的多租户、KV 复用、LoRA 服务论文清单，以及「缓存键」这类跨维度设计推断；它抓到了 Android 17 NPU Manager，这是我方漏掉的最重要的一条。短板是 HarmonyOS 与 Apple 内部细节基本靠媒体和逆向，端云路由与路由延迟没有实测，交叉验证标红的条目也不少。
> 记号：「✔」表示本轮抓到一手来源并核对；「◐」表示只核对了部分；「✘」表示本轮未能核实，按「未核实（Kimi 单源）」处理。

---

## A 可借鉴新增

| # | 条目 | 关键数据 / 事实 | 来源（Kimi 文件+脚注；一手 URL；日期） | 核验 | 建议落点 |
|---|---|---|---|---|---|
| A1 | **Android 17 NPU Manager：OS 级 NPU 仲裁已进入 AOSP** | 系统服务 `npu`；客户端先发 `requestCanLoadModel`（请求带 size class 和 priority），获批后才能加载模型；资源紧张（前台请求、热峰值）时回调 `onRequestUnloadModel`，要求客户端卸载；任务结束原因含 `NPU_END_REASON_PAUSED` 与 `CANCELLED_SYSTEM`（"Preempted by system policy"）；模型优先级为 background / normal / opportunistic；后台应用的高优先级任务会被下调以保护前台图形；HAL 为 `android.hardware.npu` AIDL，含 `SchedulingConfig`（minPriority、maxPriority、uid、appPriority、hasDirectAccess、canAttributeOtherUid）和 `WorkInfo`；VTS 为 `VtsHalNpuSchedulingTargetTest`；应用以 `android.hardware.npu` 特性声明（`required="false"`）申请调度优先级 | Kimi dim01 脚注 27、dim01 §3 趋势 4、insight I-07；一手：https://source.android.com/docs/core/perf/npu-manager（页面未标日期）；AOSP 仓库 `platform/packages/modules/NpuManager` tag `android-17.0.0_r1`，tag 创建于 2026-06-16，最新提交 2026-05-14，树内有 `apex/ flags/ framework/ ndk/ service/ tests/` | **✔ 属实**。官方页和 AOSP tag 均核对。Kimi 的二手来源（androidperformance wiki）把它说成「best-effort、@SystemApi」。官方页**没有**写 best-effort，也**没有**给时延或时间片保证，同时没说明第三方应用能否用同等权限；wiki 的 `@SystemApi`、`ACCESS_NPU_MODEL_MANAGER_API` 权限、「数值越小优先级越高」三点官方页均未出现，按「未核实」处理。另注意：`main` 分支树为空（"Initial empty repository"，2026-06-15），代码在 release 分支和 tag 上 | §3 Q2「多会话、优先级与抢占」整段重写；§4 空白点 1；§5 INF-3；§6 新增 J2 协同（size class 记账，交 C4） |

**A1 建议插入文字**（替换 §3 Q2「多会话、优先级与抢占：这是最薄的一块」下前三条）：
> Android 17 在 AOSP 中新增 NPU Manager（系统服务 `npu`），把 NPU 的模型加载准入与优先级从厂商守护进程收回平台：客户端须先 `requestCanLoadModel`（带 size class 与优先级）获批再加载；资源紧张时系统回调 `onRequestUnloadModel` 要求卸载，任务可被标记为 `PAUSED` 或 `CANCELLED_SYSTEM`；模型优先级分 background / normal / opportunistic，后台高优先级任务会被下调以保护前台图形（source.android.com 的 NPU manager 页；AOSP tag android-17.0.0_r1 创建于 2026-06-16）。官方页没有给出时延上限或时间片保证。判断：Google 已在 OS 层做了「准入 + 优先级 + 以卸载模型为手段的抢占」，粒度是模型而不是算子；它覆盖 NPU，不覆盖 CPU/GPU，也看不出与 AICore 配额打通。

### 其余 A 类（按价值排序）

| # | 条目 | 关键数据 / 事实 | 来源 | 核验 | 建议落点 |
|---|---|---|---|---|---|
| A2 | **缓存键代数：改变 K/V 值的对象都得进缓存身份** | llama.cpp 服务端热切换 LoRA 时须清空 KV（issue 原话 "must clear the cache"）；SGLang 把 adapter 标识写进前缀缓存键，`(lora0, tokens)` 与 `(lora1, tokens)` 是不同条目；S-LoRA Unified Paging 把 adapter 权重与 KV 放进同一分页池；Kimi 提出键模式 `(base_version, adapter_id, adapter_version, quant_tier, rope 方案)` | Kimi dim02 脚注 33（https://github.com/ggml-org/llama.cpp/issues/10377，2024-11-18）；dim03 脚注 54、41；insight I-01 | **✘ 未核实（Kimi 单源）**。SGLang LoRA 文档页（docs.sglang.io）本轮抓到，只提到 pinned adapter 与 overlap loading，**没有**提缓存键；llama.cpp issue 未抓。机制本身有推理依据（LoRA 若作用于 K/V 投影，切换后旧 KV 即失效），但「所有 LoRA 都影响 KV」不成立，取决于 target modules | §3 Q6 末；§5 INF-2′ 与 INF-5′；§6 J6 |
| A3 | **NPU「prefill 强、decode 弱」的 decode 侧证据** | 2607.05475 摘要：NPU 擅长 compute-bound prefill，CPU 在 memory-bound decode 上胜过其他后端；框架间差距最高 10 倍；调 CPU 频率最多省 39.7% 能耗；Kimi 另引 ExecuTorch MLSys 2026：Llama-3.2-1B 的 QNN prefill 2813–2977 tok/s 对 XNNPACK 525–529，Qwen3-0.6B decode 上 QNN 61–62 低于 XNNPACK 72–73（Galaxy S25 Ultra） | Kimi dim02 脚注 1、36、32；一手：https://arxiv.org/abs/2607.05475（2026-07-06 提交，v2 2026-10-16，SIGMETRICS 2027）；ExecuTorch 论文 arXiv 2605.08195（Kimi 引） | **◐** 2607.05475 摘要已核（我方 A26 同一篇，见 B2）；ExecuTorch 的具体 tok/s 未抓，Kimi 单源 | §3 Q2「NPU 的真实收益存在分歧」、§3 Q4「prefill 上 NPU」 |
| A4 | **移动 NPU 上的跨请求 KV 复用系统** | 论文把前缀与非前缀 KV 复用塞进 NPU 静态图：图内选择性重算、跨图 chunk 合并减少 padding、NPU/CPU/Flash 分层 KV 管理、成本感知预取与驱逐；TTFT 比无复用和仅前缀缓存降 40%–60%；Kimi 另引其引言「现有引擎对跨请求持久 KV 复用基本无支持」与「prefill 加速 1.5–5.4×」 | Kimi dim02 脚注 23、insight I-01；一手：https://arxiv.org/abs/2609.34727（2026-09-28，上海交大 Fan Wu、Guihai Chen 等） | **◐ 论文存在，TTFT 40%–60% 已核**；1.5–5.4× 与引言引文摘要页未出现，未核 | §4 空白点 6；§5 INF-5 反方证据；§6 J2 |
| A5 | 端侧 KV 换页的学术先例：LLMaaS、mzCache | LLMaaS（arXiv 2403.11805，SenSys 2026）：把 LLM 当移动系统服务，chunk 级 KV 压缩与换入换出，上下文切换延迟最多降两个数量级；mzCache（多任务下端侧 LLM 内存管理）与 NPUGen 为 MobiCom 2026 录用 | Kimi dim02 脚注 28、33（录用依据是 GitHub 论文清单，L–M 级） | **✘ 未核实（Kimi 单源）** | §5 INF-5「最强反方证据」栏补学术先例；§3 Q3 |
| A6 | SLO 感知的弹性子模型：ElastiLM | MobiCom 2025：同一底座弹性化成多级子模型，按请求 SLO 选择；切换开销 <1% TTFT（约 0.31s），精度最高提升 14.83% | Kimi dim02 脚注 29（https://dl.acm.org/doi/10.1145/3680207.3765259，2025-09） | **✘ 未核实（Kimi 单源）** | §5 INF-3 第二层的备选手段 |
| A7 | 跨 LoRA 的 KV 复用（A2 的反方证据） | MobiLoRA（ACL 2025）：跨 adapter 的 KV delta 复用，TTFT 降 18.1%–81.3%，并按应用前后台状态决定驱逐；DroidSpeak（NSDI 2026）：同架构微调变体间逐层选择性重算，prefill 快 3.1× | Kimi dim02 脚注 25（https://aclanthology.org/2025.acl-long.1140/）、26 | **✘ 未核实（Kimi 单源）**。注意 Kimi 自引的 ACL 摘要是「57.6%」，正文才是 18.1%–81.3%，口径不一 | §3 Q6、INF-2′：缓存键默认隔离，可选 delta 复用 |
| A8 | 抢占式多 DNN 推理先例：Pantheon、V10 | Pantheon（MobiSys 2024）：移动 GPU 上切片执行 + 提前退出实现可抢占多 DNN；V10（ISCA 2023）：硬件辅助算子级 NPU 多租户，吞吐 1.57×、尾延迟降 1.74×，但面向云端 NPU 并需改硬件 | Kimi dim01 脚注 29、30（https://dl.acm.org/doi/10.1145/3643832.3661878） | **✘ 未核实（Kimi 单源）** | §3 Q2 学术侧只写了 Agent.xpu，可补这两条；§5 INF-3 第二层 |
| A9 | Apple 适配器与草稿模型的耦合 | Apple 工具包说明：不训练 draft model，适配器就用不了投机解码；Kimi 的引文来自第三方博客对官方文档的转述 | Kimi dim03 脚注 16（https://blakecrosley.com/blog/foundation-models-custom-adapters，2026-05-04） | **✘ 未核实**。我方 A14 就是工具包页，建议主 Agent 回读该页确认这句话 | §3 Q6 表 Apple 行；§5 INF-2′「版本契约」补一条「适配器 × 投机解码」 |
| A10 | Apple 端侧大模型权重驻留 NAND | WWDC26 的第三代 AFM 分 Core / Core Advanced / Cloud / Cloud Pro；Core Advanced 为 20B 稀疏模型（1–4B 激活），完整专家集存放在 NAND，按需加载；PCC 扩展到 Google Cloud + NVIDIA 机房 | Kimi dim03 脚注 4（ecorpit 媒体，2026-06-08）、50（ai-on-mac，2026-10-13） | **✘ 未核实**，媒体口径。我方 B32（Apple 官方「第三代 AFM」文章）已引用，建议回读核对。若属实，对 INF-5 是实质反例，见 D | §5 INF-5；§3 Q3 |
| A11 | HarmonyOS 2026 的媒体级数据 | HDC 2026：AI 子系统开放 20 余项能力，日调用 36.8 亿次；2100 余项系统能力 Skill 化；小艺底层改为多模型通用插座（盘古、DeepSeek）；用 OHTTP 做身份三重匿名（HPIC） | Kimi dim01 脚注 10、11（firecat-web 2026-06-14；https://pandaily.com/harmonyos-agent-os-hdc-2026-xiaoyi-celina-jun2026，2026-08-28）；交叉验证列为 High（两处一致），但均为会议报道 | **◐ 媒体口径**，非官方文档，也没有第三方开放 API 或配额 | §3 Q1 表 HarmonyOS 行；§8 待核实 2 |
| A12 | 适配器的治理面：运行时加载接口是攻击面 | vLLM 官方警告运行时加载 LoRA 的接口只能用于隔离的可信环境；Apple 靠 entitlement + Background Assets + 版本锁定闭环；Android 没有等价的签名与来源校验 | Kimi dim03 脚注 37、16 | **✘ 未核实**；「Android 无等价物」是 Kimi 的判断，非来源论断 | §6 J6，加一句安全前置条件 |
| A13 | 端云协作的任务分解：Minions / CE-CoLLM | MinionS：本地读全文，云端只拿子任务，成本降 5.7×、恢复 97.9% 性能；CE-CoLLM：云请求降到 27.7%–49.6%，通信量降 99% 以上 | Kimi dim03 脚注 30（arXiv 2502.15964）、26（arXiv 2411.02829） | **✘ 未核实**；与 PRISM 相比提供了「原文不出端」的另一条路径 | §3 Q5 学术路由段补一句 |
| A14 | 高通 QNN 的 8 级 context priority | `qnn_context_priority` 取值从 low 到 critical_plus，另有 burst / balanced / low_power 等 HTP 性能档 | Kimi dim01 脚注 14（onnxruntime-qnn QNN-ExecutionProvider 文档）、15 | **✘ 未核实**；是「优先级是 hint」的厂商侧证据，切换延迟仍无数据 | §8 待核实 4 |

**A2 建议插入文字**（§3 Q6 末尾）：
> 适配器不只是权重，还会改变 KV。llama.cpp 服务端在切换 LoRA 时必须清空 KV（GitHub issue #10377，2024-11，Kimi 引），SGLang 则把 adapter 标识写入前缀缓存键。判断：只要 LoRA 作用于 K/V 投影，缓存身份就须包含底座版本、适配器 ID 与版本、量化档位；否则系统服务层的前缀缓存在切换适配器后会静默产出错误结果。MobiLoRA、DroidSpeak 表明可以做 delta 复用，但这是可选优化，默认应隔离。

**A3 建议插入文字**（§3 Q4「prefill 上 NPU」末尾）：
> 2607.05475 的摘要同时给出 decode 侧结论：CPU 在访存受限的 decode 上胜过其他后端，NPU 的优势集中在 compute-bound 的 prefill（SIGMETRICS 2027，v2 于 2026-10-16 修订）。Kimi 引用的 ExecuTorch 论文（Galaxy S25 Ultra）给出相同方向的数字：QNN prefill 约为 XNNPACK 的 5 倍，decode 反而略低。判断：若 OS 要暴露分阶段后端选择，应以阶段为单位而不是以芯片为单位。

**A4 建议插入文字**（§5 INF-5 最强反方证据栏，或 §4 空白点 6 之后）：
> 2026-09 的预印本（arXiv 2609.34727）首次在移动 NPU 的静态图内实现前缀与非前缀 KV 复用，并设计 NPU/CPU/Flash 三层 KV 存储与成本感知驱逐，TTFT 比无复用与仅前缀缓存降低 40%–60%。它是论文原型，不是系统服务，但说明「KV 持久化与分层」在 NPU 路径上已有可实现的方案，其核心矛盾是动态复用与静态图形状的冲突。

**A5 建议插入文字**（§5 INF-5 反方栏）：
> 学术界已有端侧 KV 换页的系统工作：LLMaaS（arXiv 2403.11805，SenSys 2026）提出 chunk 级 KV 压缩与换入换出，称上下文切换延迟最多降两个数量级；mzCache 与 NPUGen 为 MobiCom 2026 录用（以上为 Kimi 单源，未核）。它们仍是原型，不改变「没有系统服务提供分页」的结论。

**A11 建议插入文字**（§3 Q1 HarmonyOS 行，标媒体口径）：
> HDC 2026 的会议报道称 HarmonyOS AI 子系统开放 20 余项能力、日调用 36.8 亿次，2100 余项系统能力被 Skill 化，小艺改为多模型插座（Pandaily，2026-08-28）。这是媒体口径，没有 API 文档与配额说明，不足以回答第三方开放程度。

---

## B 冲突与更正

| # | 事实 | 我方写法（位置） | Kimi 写法（位置） | 一手来源裁决 | 正确口径 | 我方需改动 |
|---|---|---|---|---|---|---|
| B1 | **OS 级 NPU 调度是否存在公开机制** | 「没有任何厂商公开 NPU 上下文切换开销或抢占粒度」「移动端多租户 NPU 抢占在产业和学术上都接近空白」（§3 Q2）；空白点 1（§4）；INF-3 评审表「产业缺口真实：并发语义不公开」（§5.1） | Android 17 `NpuManager` + AIDL 是首个 OS 级 NPU 调度控制面，best-effort、@SystemApi（dim01 §1.2、脚注 27） | source.android.com NPU manager 页与 AOSP tag 核对：机制存在，范围比 Kimi 描述更大（模型加载准入 + 卸载式抢占 + 三档优先级）；「best-effort」「@SystemApi」官方页未出现 | **Kimi 对，且我方措辞过强**。「抢占粒度」其实已公开：模型级，靠请求客户端卸载；仍然没有公开的算子级抢占和切换开销数据 | 改 §3 Q2、§4 空白点 1、§5.1 INF-3 行，见 D |
| B2 | arXiv 2607.05475 是否存在 | A26「Is Your NPU Ready for LLMs?」（§2、§8） | 交叉验证把 dim07 引用的「OSDN（arXiv 2607.05475）」标为搜索零结果、UNVERIFIED（CV 组件 3 Low 第 2 条）；而 dim02 脚注 36 又把同一编号当作 NPU 实测研究引用 | 摘要页已抓：存在，标题与作者如上，cs.AR，SIGMETRICS 2027，2026-07-06 v1、2026-10-16 v2 | **我方正确**；Kimi 交叉验证的「零结果」是 dim07 把它错配成 OSDN，不是编号虚构 | §8 A26 补「v2 2026-10-16」；不需改结论 |
| B3 | Apple AFM 适配器规格 | 「每个约 160MB」，来源工具包页（§0、§2、Q6） | dim01/dim03：rank-16、数十 MB（2024 技术报告）；dim02：rank-32、约 160MB（逆向分析） | CV C1 已裁：两者都真、指代不同——2024 官方报告为功能适配器 rank-16、数十 MB；2025 出货模型与工具包为 rank-32、约 160MB，rank-32 只见于第三方逆向，非官方文档。本轮未再抓 arXiv 2407.21075 | 双口径并存，不可混写 | §3 Q6 表 Apple 行加一句：「2024 技术报告口径为 rank-16、数十 MB；2025 工具包口径约 160MB/个，rank-32 为第三方逆向，非官方」 |
| B4 | Apple 路由决策是否披露 | 「未披露」，只有统一 API（§7.2、§5 INF-4） | WWDC26 的 System Orchestrator 按任务复杂度、隐私敏感度、延迟需求、设备热状态逐 prompt 路由（dim03 脚注 4；媒体转述）。但 dim03 §3 空白点 1 又写「Apple 按能力路由」，同一报告前后不一致 | 未取得官方原文，媒体口径 | **维持「官方未披露」**，可在脚注加「媒体称考虑复杂度、隐私敏感度、延迟、热状态，未见官方原文」 | §7.2 Apple 行「路由依据」栏加媒体口径注；不改立场 |
| B5 | NVIDIA OpenShell 时间 | 只写 2026，文档页直读 404（§1、B26） | dim03：GTC 2026-03-16 发布 NemoClaw + OpenShell；dim04/05：2026-09-28 正式发布 | CV C3 已裁：三个事件并存（2026-03 NemoClaw 首亮相，2026-09-28 Open Agent Safety Platform，2026-10-21 GTC Berlin 参考架构）；本轮未抓 | 写「2026-03 随 NemoClaw 首次亮相，2026-09-28 正式发布」 | §1 谱系表、§8 B26 补日期 |
| B6 | 「NPU 比 CPU/GPU 快多少」 | 厂商口径「比 GPU 快至多 10 倍」（§3 Q2 [A8]） | LiteRT 官方「CPU 最高 100×、GPU 10×」；转述「25×」；MWC 实测「12×」（dim01 §2；CV C5） | CV C5：口径混乱，不可归一 | 我方只引 10 倍 GPU 一档，没有踩坑；引用时仍须带场景 | 无需改；若加 100× 须注明理论峰值 |
| B7 | EdgeLoRA 吞吐倍数 | 「对 llama.cpp 吞吐最高 4 倍；8–64GB 设备，非手机」（§3 Q6 表） | 「2–4×」，Jetson AGX Orin 上 1000+ adapter 对 llama.cpp 约 50（dim02 脚注 8） | CV C7：4× 与论文存在已核，「1000+/50」仅部分核实；本轮未抓 | 4× 为上限，2–4× 为范围，两者不冲突；adapter 数量按「数量级更多」写 | 无需改 |

---

## C 可消解的待核实

| 我方待核实条目（§8 序号） | 新证据 | 结论 |
|---|---|---|
| 1 国内手机厂商、三星 Galaxy AI 的开放 API | Kimi 无相关一手来源 | 仍待核实 |
| 2 HarmonyOS 2026 现状 | Kimi 只有会议报道级数据（A11）；盘古 6.0「入内核」被交叉验证列为 Low；NNRt 56 个算子、仅同步推理与我方 A22 来自同一份 OpenHarmony 文档 | 仍待核实；NNRt 限制二次印证，无新增 |
| 3 第三方自带模型占比 | Kimi 引 Beebom 实测「旗舰机消费应用无一用 NPU」，CV 列 Low | 仍待核实，不采纳 |
| 4 QAIRT 多会话、VTCM、多 LoRA 切换 | A14：QNN context priority 有 8 级、HTP 有性能档（ORT QNN EP 文档，未抓）；QNN 共享内存仅接受 DMA-BUF（CV 列 Medium） | 部分有线索（优先级是 hint）；切换延迟仍待核实 |
| 5 Apple 工具包「26.0.0 最后一版」 | Kimi 无涉及 | 仍待核实 |
| 6 guided generation 机制、系统提示词 KV 跨请求复用 | Kimi 仅有逆向来源称 AFM「KV 共享省 37.5%」，指模型内部两段共享，不回答跨请求复用 | 仍待核实 |
| 7 AICore 内存归属、并发、更新机制 | Kimi 的细节（LoRA registry、200ms 卸载 40MB、bsdiff 差分 200–400MB）全部来自一篇逆向博客（xckevin，2025-05），自标 low-medium | 不坐实；见 E |
| 8 WWDC26 路由规则 | 媒体口径（B4） | 仍待核实 |
| 11 llm.npu 等论文发表会议 | llm.npu = ASPLOS 2025（Kimi 引论文 PDF xumengwei.github.io/files/ASPLOS25-NPU.pdf，该文件名与 ACM 记载一致，本轮未抓）；EdgeLoRA = MobiSys 2025；Pantheon = MobiSys 2024；Agent.xpu 为 arXiv 2506.24045，Kimi 称 2026-01，会议未知 | llm.npu 部分坐实（单源）；HeteroInfer、PowerInfer-2、Agent.xpu 仍待核实 |
| 13 手机 NPU 上 EAGLE / LayerSkip | Kimi 引 llama.cpp 内置 eagle3、mtp 等六种投机实现（CPU/GPU），sd.npu 即我方 B20 | 仍待核实（NPU 上无新证据） |
| 15 OpenShell 推理路由文档 404 | Kimi dim03 脚注 9–11 为二手转述：`inference.local`、凭证剥离、header 白名单、策略热更新约 5s | 部分印证二手摘要，仍无官方原文；按脚注 URL 由主 Agent 决定是否补抓 |
| 16 推理层注入防护 | Kimi 无新证据 | 仍待核实 |
| 2、3、5、10、12、14、17 | Kimi 无相关内容 | 仍待核实 |

---

## D 立场层面的调整

**INF-3 多租户 QoS 调度（影响最大）**

- Kimi 证据：A1（已核实）。Android 17 把 NPU 准入、优先级和以卸载为手段的抢占做进了 OS。这直接动摇我方 §5.1 的三处表述：
  - 「产业缺口真实：并发语义不公开」；
  - 「第一层：准入控制与前台优先（可落地）」被当作差异化；
  - 「最强反方证据」只写了 AICore 的粗粒度准入够用。
- 建议调整：
  1. 判断仍为「支持，拆两层」，但把第一层改写为「对齐并扩展 Android 17 NPU Manager」，不再作为我方独有的缺口。
  2. 第二层与差异化改为 NPU Manager 没有覆盖的部分：跨后端（CPU/GPU/NPU）的统一准入与记账、会话或 token 粒度的抢占、阶段感知的后端选择、与 AICore 配额和前台限制打通。
  3. 「最强反方证据」栏补一句：Google 已在 AOSP 落地 NPU 仲裁，OS 厂商自建同层机制要面对与上游分叉的成本。
  4. 置信度维持「中」，不升。
  5. 新接缝：`ModelLoadRequest` 带 size class，且卸载被当作抢占手段，意味着 NPU 模型内存已有准入记账入口，同时重载代价会转嫁到用户（AICore 首次加载约 1 分钟）。这条应作为 J2 协同写入 C4 的待办。
- 另注意：Kimi insight I-07 把「多租户 QoS」归为中速窗，建议与 Google 共演进。这是 Kimi 的推断，我方可借用，但须把 best-effort 的说法改成「官方页未给出时延保证」。

**INF-2 共享底座 + 适配器热插拔**

- Kimi 证据：A2、A7、A9。
- 建议调整：INF-2′ 第①条「带 `base_model_id + 版本区间` 的受管产物」后追加：
  - 「适配器切换会使既有 KV 失效，KV 身份须包含适配器 ID 与版本；是否允许跨适配器 delta 复用作为可选优化」；
  - 「适配器与草稿模型成对分发」（待 A9 核实后写入）。
- 置信度维持「中」。A2 的 SGLang 部分本轮未核实，正文引用时只写 llama.cpp 一条并标注来源，或等核实。

**INF-5 权重与 KV 可分页**

- Kimi 证据：A4（已核）、A5（未核）、A10（未核，媒体）。
- 建议调整：保持「挑战」，但**限定范围**。
  - KV 部分：「没有任何系统服务支持分页」仍成立；反方证据栏补 A4、A5 作为已存在的学术原型。
  - 权重部分：若 A10 属实（Apple 第三代 AFM 的 Core Advanced 把完整专家集放在 NAND、按需加载），则「没有任何系统服务支持权重分页」要改成「Apple 的系统模型已经产品化了专家级权重按需加载」，我方「会话状态三态接口」主张不变，但「挑战」的措辞需弱化。
  - 在 A10 核实前，不改正文，只在 §8 待核实里新增一条：「回读 B32，确认 Core Advanced 的 NAND 驻留与按需专家加载是否为官方说法」。

**INF-4 端云路由层**

- Kimi 证据：A13、B4、insight I-10。
- 建议调整：无需改立场。I-10（NPU 跑 prefill、decode 留 GPU 或移交云的「分阶段路由」）是 Kimi 的探索性推断，其前提「阶段不对称」我方已有（A26 一手摘要可印证），但「移交 KV 到云」没有任何一手证据，不进正文；A13 可作为「原文不出端」路径的补充，放在学术路由段。

**INF-1 模型即系统服务**

- Kimi 的 dim01 §4 判断「支持（已验证）」，与我方「支持，需修订」方向一致，无需调整。Kimi 反而没有看到 Apple `LanguageModel` 协议可插拔、Phi Silica 被替换这类反方证据，我方更完整。

---

## E 不采纳

| 条目 | 原因 |
|---|---|
| HarmonyOS 7「盘古 6.0 入内核」（dim01 脚注 12）、端侧 30B 常驻（脚注 43） | 交叉验证列 Low；来源是 ITHome 转述和新浪横评，无技术出处 |
| Android 17 NPU 的「best-effort」「@SystemApi」「数值越小优先级越高」 | 仅见 androidperformance wiki 的转述；官方 NPU manager 页未出现，已按 A1 说明单独处理 |
| AICore 逆向细节：LoRA Adapter Registry、卸载 40MB 约 200ms、bsdiff 差分增量 200–400MB、底座常驻 4GB+（dim01 脚注 6） | 单一逆向博客，Kimi 自标 low-medium，且与我方「模型差分更新无公开机制」不构成可核实的反证；采纳会污染我方证据等级 |
| ANE「约 32MB SRAM、溢出降 30%」（dim01 脚注 19） | 数据来自 maderix 单源逆向，交叉验证要求降级；属 Apple 内部实现，超出我方 C1 评审所需 |
| FastVLM-0.5B 的 TTFT 0.12s、prefill 11000 tok/s（脚注 41）；NPU 12×/25×/100× 口径 | 厂商基准，且 Kimi 把芯片代际写少一代（应为 Snapdragon 8 Elite Gen 5）；我方已用 Gemma 4 的官方模型卡数据，信息增量低 |
| PCC 路径「首 token 增加 200–500ms」（dim03 脚注 49） | 来源为 kanopylabs 开发者博客，页面日期异常（2028）；我方「端云切换延迟无公开数据」的结论不应被它推翻 |
| PCC 路由层存在流量分析侧信道（dim03 脚注 59） | iotdigitaltwinplm 的判断性线索，无原文 |
| insight I-10 的「分阶段路由 + 云等待期挂起」 | Kimi 自标 exploratory，属设计推断，无一手证据；前提部分已被 A3 吸收 |
| insight I-05「一次会话分类驱动四个执行面」 | 跨组件设计推断，不属于 C1 事实核对，留给主 Agent 做总体评审时考虑 |
| Sereno（OSDI 2026）带宽争用（dim02 脚注 37） | 来源是 awesome 论文清单，Kimi 自标 L（线索，未逐篇核对） |
| S-LoRA 2000 adapter、Punica 12× 等云端数字 | 云端 GPU 先例，交叉验证为 High，但与手机无直接迁移关系；我方 Q6 已定性为「手机上无实测」，不新增 |
| llama.cpp、MNN、MLC-LLM、bitnet.cpp、量化与投机解码谱系（dim02 §1.1–1.3） | 框架格局可作背景，但与 INF 立场评审关联弱；我方 §3 Q3 已说明未逐项核实内存管理，如需补充应单独立项 |
| 「EdgeLoRA 同时服务 1000+ adapter」作为手机证据 | Jetson AGX Orin 平台，不是手机；CV 对具体数字仅部分核实 |

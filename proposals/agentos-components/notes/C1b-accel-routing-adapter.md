# C1b 推理加速、端云路由与适配器

**子模块**：C1b（推理 Q4、Q5、Q6、Q8）｜**主责接缝**：J3、J6、J8｜**评审立场**：INF-2、INF-4、INF-5（推理加速相关部分）
**调研日期**：2026-11-05｜**方法说明**：本轮联网检索的 WebSearch 配额中途耗尽，之后只能用 WebFetch 直读已知页面。凡未能核实的内容一律进入 §8 待核实清单，不以记忆补数。
**证据等级**：A 官方文档/论文/源码；B 官方博客/厂商口径/审计方博客；C 权威媒体/第三方/预印本；D 传闻。**成熟度**：L1 论文；L2 原型；L3 生产可用；L4 平台默认。

---

## §0 摘要

1. 端侧投机解码已经从论文进入官方运行时：Google 在 LiteRT-LM 中为 Gemma 4 提供 MTP drafter，三星 S26 Ultra GPU 上最高 2.2 倍解码加速，但收益强依赖任务类型，CPU 上个别任务反而变慢 [R3, R4]（A/B，L3）。
2. 手机 NPU 上的 LLM 加速仍是论文与厂商演示主导：官方 LiteRT-LM 模型卡里 NPU 的唯一数据点来自 Qualcomm Dragonwing IQ8（IoT 板，非手机），手机行只有 CPU 与 GPU [R3]（A）。
3. NPU 并非必然更快更省：2026 年 5 月的阶段级分析称 prefill 阶段 CPU 最多比 NPU 快 1.6 倍，decode 阶段 NPU 仅 1.05–1.2 倍，且 NPU 卸载越多能耗最高上升 51% [R9]（C，预印本，设备未在摘要中说明）。
4. 端云路由在产业界不是“OS 自动按隐私/成本/延迟路由”，而是三种形态：开发者显式选模式（Firebase hybrid）、用户逐请求发起（Meta Private Processing）、厂商不披露的内部决策（Apple、Google）[R10, R13, R14, R6]（A/B）。INF-4 的“自动路由层”只在学术界出现（PRISM 等，L1）[R19]。
5. 云侧隐私机制趋同于“TEE 远程证明 + 无状态 + 匿名中继 + 透明日志”，但审计显示实现缺口真实存在：Trail of Bits 对 WhatsApp 的审计共 28 项问题（8 项高危），含证明可重放 [R15]（B）；Apple PCC 的逆向研究称二进制无可复现构建、无符号 [R8]（A，预印本，WiSec 2026）。
6. Apple 适配器与系统模型版本一一绑定、每个约 160 MB、须按 OS 版本各训一份；且 Apple 开发者页声明工具包 26.0.0 是最后一版、不兼容 OS 27 及之后 [R11]（A）。这是对 INF-2“热插拔”的最强反方证据：适配器的真实成本在版本兼容，而非切换延迟。
7. Google 的适配器是 Google 自训、按功能分发、第三方不可挂载（ML Kit GenAI API）[R12]（B）；Chrome Prompt API 与 LiteRT-LM 文档均未提及 LoRA（本轮未检到）。三家平台里只有 Apple 向第三方开放适配器。
8. 手机 NPU 上多 LoRA 切换有可行实现：三星研究团队把 LoRA 权重作为运行时输入喂给同一张冻结的编译图，免重编译，Galaxy S24/S25 实测；但摘要没有给出切换延迟 [R16, R17]（C，L2）。切换延迟是公开资料空白。
9. 结构化输出已是推理服务的标配：Apple guided generation、Chrome `responseConstraint`、LiteRT-LM 受约束解码均由推理侧提供 [R7, R18, R4]（A/B）。Chrome 的 schema 还会占用上下文窗口。
10. 注入防护未在端侧推理服务层发现公开实现：Chrome Prompt API 文档不涉及，LiteRT-LM 博客不涉及（检索范围见 §3 Q8）。判断：J3 的切分应是“格式约束在推理侧，注入防护在执行侧”。

---

## §1 技术谱系表

| 路线 | 代表工作 | 机构 | 时间 | 一句话贡献 | 成熟度 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| 量化：QAT 2-bit | Apple Foundation Models 2025 技术报告（3B 端侧，2-bit QAT + KV 共享）[R7] | Apple | 2025-07 | 端侧 3B 模型量产使用 2-bit QAT | L4（随系统出货） | 端侧原生 |
| 量化：INT4 + 多适配器联合 | QUAD、multi-LoRA one-for-all [R16, R17] | 三星研究院 | 2026-03/04 | 多个 LoRA 共享一个量化配置并在 NPU 上运行 | L2 | 端侧原生（Galaxy S24/S25） |
| 投机解码：MTP drafter | Gemma 4 MTP drafters [R3, R4, R5] | Google | 2026-05 | 74M 参数 drafter，共享 KV，GPU 最高 2.2 倍 | L3 | 端侧原生（CPU/GPU） |
| 投机解码：NPU 协同 | sd.npu / CoordGen（arXiv 2510.15312）[R20] | 北大/北邮等 | 2025-10 | 用 NPU 空闲算力做投机解码，1.06–3.81 倍 | L1 | 端侧原生，驱动依赖强 |
| 投机解码：无 drafter 自投机 | DS2D（三星，树式）[R17] | 三星研究院 | 2026-04 | 无需草稿模型，最高 2.3 倍解码 | L2 | 端侧原生 |
| prefill 上 NPU | llm.npu（arXiv 2407.05858）[R21] | 北邮等 | 2024-07 | prefill 22.4 倍、能耗 30.7 倍（对基线） | L1 | 端侧原生 |
| 异构 GPU+NPU | HeteroInfer（arXiv 2501.14794，文中亦称 HeteroLLM）[R22] | 上海交大等 | 2025-01 | 对 PowerInfer-2 prefill 最高 3.69 倍；1092 tok/s | L1 | 端侧原生 |
| 手机整机系统 | PowerInfer-2（arXiv 2406.06282）[R23] | 上海交大 | 2024-06 | 对 llama.cpp 平均 25.4 倍（摘要口径） | L1 | 端侧原生 |
| KV 会话复用 | LiteRT-LM session save/restore [R4]；Chrome `session.clone()` [R18] | Google | 2026 | 序列化 KV，恢复后跳过重复 prefill；分叉会话 | L3 | 端侧原生 |
| 端云路由：学术 | RouteLLM [R24]；Hybrid LLM [R25]；PRISM [R19] | UC Berkeley；Microsoft 等；ZJU 等 | 2024–2025 | 按质量/成本/隐私敏感度选模型 | L1–L2 | RouteLLM 路由器小，可迁移；PRISM 需端侧实体敏感度打分 |
| 端云路由：隐私云 | Apple PCC [R6, R8]；Google Private AI Compute [R1]；Meta Private Processing [R13, R14, R15] | Apple/Google/Meta | 2024–2026 | TEE + 证明 + 匿名中继 | L4（PCC）、L3–L4（其余） | 云侧机制，端侧只需客户端验证逻辑 |
| 端云路由：开发者 API | Firebase AI Logic hybrid [R10] | Google | 2025–2026 | 四种模式：PREFER/ONLY × ON_DEVICE/IN_CLOUD | L3 | 仅 Web/Chrome 桌面（见 §3） |
| 端云路由：代理型 | NVIDIA OpenShell `inference.local` privacy router [R26] | NVIDIA | 2026 | 沙箱内统一推理端点，剥离/注入凭证 | L2–L3（待核实成熟度） | 概念可迁移；实现面向桌面/服务器 |
| 适配器：平台受控 | Apple adapters [R11]；ML Kit GenAI LoRA [R12] | Apple；Google | 2025 | 底座版本绑定的 LoRA | L3–L4 | 端侧原生 |
| 适配器：多租户服务 | EdgeLoRA [R27]；S-LoRA、Punica（见 §8，未复核） | 加州大学默塞德分校等 | 2025-07 | 自适应选择、缓存池、批量 LoRA；对 llama.cpp 最高 4 倍吞吐 | L1 | 需改造：评测设备为 8–64GB，非手机 |
| 结构化输出 | Apple guided generation [R7]；Chrome responseConstraint [R18]；LiteRT-LM 受约束解码 [R4] | Apple/Google | 2025–2026 | 推理侧强制 schema / 语法 | L3–L4 | 端侧原生 |

---

## §2 关键数据

| 指标 | 数值 | 条件（硬件 / 模型 / 负载） | 来源 | 日期 | 证据等级 |
|---|---|---|---|---|---|
| Gemma 4 E2B 解码速度 | 52 tok/s（Android GPU）、56 tok/s（iOS Metal）| 无 MTP；Android 为 S26 Ultra OpenCL，iOS 为 iPhone 17 Pro | R4 | 2026-05-19 | B |
| 同模型 prefill / TTFT | 3808 tok/s、0.3 s（S26 Ultra GPU）；557 tok/s、1.8 s（S26 Ultra CPU）| 1024 prefill + 256 decode，2048 上下文 | R3 | 2026（模型卡，日期待核实） | A |
| 同模型 NPU 数据点 | prefill 3747 tok/s，decode 31.7 tok/s，TTFT 0.3 s | Qualcomm Dragonwing IQ8（IQ-8275，IoT 板），4096 上下文；卡内声明不应视为该文件的规格 | R3 | 2026 | A |
| NPU 性能模式差异 | 约 16 → 约 28 tok/s | 同板同模型，启用 HTP burst 模式；Linux 教程 | R28 | 2026（日期待核实） | B |
| MTP 加速（官方） | 最高 2.2 倍（移动 GPU）、最高 1.5 倍（移动 CPU）| Gemma 4；GPU 上推荐全任务，E2B CPU 上选择性开启 | R5, R4 | 2026-05 | A/B |
| MTP 分任务实测（模型卡）| GPU：基线 51.5 → 摘要 91.7、代码 84.4、改写 87.4、自由生成 66.5 tok/s；CPU：基线 40.7 → 摘要 47.5、代码 36.3、改写 47.1、自由生成 38.1 tok/s | S26 Ultra，Gemma 4 E2B | R3 | 2026 | A |
| MTP 额外内存 | 约 +0 至 +220 MB（GPU 761–817 vs 791；CPU 1408–1582 vs 1362）| 同上 | R3 | 2026 | A |
| MTP 服务器侧峰值 | 最高 3 倍 | 26B，RTX PRO 6000（服务器 GPU，不代表手机）| R5 | 2026-05 | B |
| Gemma 4 E2B 物理内存 | 607 MB（iPhone CPU，XNNPACK 权重缓存）；GPU 676 MB（S26 Ultra）| 模型文件 2.58 GB，PLE 不入内存 | R4, R3 | 2026 | B/A |
| Qualcomm 本地 LLM 吞吐宣称 | 约 220 tok/s，上一代 70 tok/s；支持 INT2/FP8 | Snapdragon 8 Elite Gen 5，3B 级模型，具体测试配置媒体未载 | R29（媒体汇总）| 2025-09 | C（厂商口径转述） |
| NPU 阶段级反转 | prefill：CPU 比 NPU 快最高 1.6 倍；decode：NPU 仅 1.05–1.2 倍；NPU 卸载增多能耗最高 +51% | CPU-NPU 异构 SoC（摘要未命名），模型未命名 | R9 | 2026-05-22 | C |
| NPU 协同投机解码（RAG）| 速度 1.06–3.81 倍，能耗节省 1.07–4.71 倍 | Redmi K60 Pro、K70 Pro、OnePlus 13（据检索摘要）| R20 | 2025-10（v4：2025-12）| C |
| llm.npu prefill | 22.4 倍速度、30.7 倍能耗；>1000 tok/s（十亿级模型）| 对基线，设备以论文为准 | R21 | 2024-07 | C（预印本；venue 待核实）|
| HeteroInfer prefill | 1092 tok/s（序列 256，InternLM-1.8B）；llm.npu 同条件 564 tok/s | 论文表格，设备以论文为准 | R22 | 2025-01 | C |
| 持续负载降频 | iPhone 16 Pro 两次迭代内吞吐损失近半；S24 Ultra 因 OS 强制 GPU 频率下限而终止推理 | Qwen2.5-1.5B 4bit，258 token 提示，20 次热态迭代 | R30 | 2026-03 | C |
| 多 LoRA NPU 实测（三星）| 多流解码最高 6 倍延迟下降；DS2D 最高 2.3 倍解码加速；INT4 + 架构优化综合 4–6 倍内存与延迟改善 | Galaxy S24/S25，SM8650/SM8750，9 种语言 8 类任务 | R17 | 2026-04 | C |
| 视觉多 LoRA | 内存最高降 6 倍，延迟最高降 4 倍 | 多芯片 NPU（摘要未命名）| R16 | 2026-03-31 | C（CVPR 2026 Mobile AI Workshop）|
| Apple 适配器体积 | 约 160 MB / 个 | 每个系统模型版本各一个 | R11 | 2026（页面日期待核实）| A |
| Apple 适配器秩 | rank 32 | 工具包训练 | R7（据检索摘要）| 2025-07 | C（未在摘要原文复核）|
| EdgeLoRA 吞吐 | 对 llama.cpp 最高 4 倍 | Llama3.1-8B；8–64GB 设备 | R27 | 2025-07 | C |
| RouteLLM 成本 | “某些情况下成本降低超过 2 倍”| 偏好数据训练的路由器 | R24 | 2024-06（v4 2025-02）| A（论文摘要）|
| Hybrid LLM 调用节省 | 大模型调用最多减少 40% 而质量不降 | 质量与成本感知路由，ICLR 2024 | R25 | 2024 | A |
| PRISM 能耗/延迟 | 降至基线的 40–50% | 实体级敏感度 + 本地差分隐私，AAAI 2026 | R19 | 2025-11 | A（摘要，自报）|
| WhatsApp 审计 | 28 项问题，其中 8 项高危；16 项完全修复，4 项部分，8 项低危遗留 | Trail of Bits 对 Private Inference 的审计 | R15 | 2026-04-07 | B |
| PCC 逆向 | 无可复现构建、无符号；开放了非公开接口并发布基准框架 | Dittmar 等，WiSec 2026 | R8 | 2026-05-22 | A（预印本，已被会议接收）|
| PCC 开发者开放 | 对首次 App Store 下载量少于 200 万的开发者免费开放 PCC 上的 Apple 基础模型 | WWDC26 | R31 | 2026-06-09 | C（MacRumors 转述）|
| 公开的端云切换延迟 | 未找到公开资料 | Apple、Google、Meta、Firebase、Samsung 均无 | — | — | — |
| 每 token 能耗（J/token，手机）| 未找到可直接引用的手机实测；R30 的 RTX 4050 为约 0.26 J/token 是本人由功率除以吞吐估算，非论文数字 | — | R30 | 2026-03 | 估算 |

---

## §3 逐问题分析

### Q4 推理加速的端侧落地水平

**量化。**Apple 是唯一把低比特 QAT 做进量产系统模型的厂商：2025 年技术报告称 3B 端侧模型使用 2-bit QAT 与 KV cache 共享 [R7]（A，L4）。2026 年第三代模型页提到 QAT“显著压缩”，但本页没有给出位宽，也没有 KV、投机解码、延迟数字 [R32]（B）。Qualcomm 宣称 Snapdragon 8 Elite Gen 5 支持 INT2/FP8，本地 LLM 吞吐约 220 tok/s [R29]（C，厂商口径经媒体转述，测试配置不明）。三星研究团队在 Galaxy S24/S25 上用 INT4 加架构优化，宣称综合 4–6 倍内存与延迟改善 [R17]（C）。分歧点：W4A16/W4A8 是谁都能做的工程基线，2-bit 与三值只在 Apple 一家有量产证据；Qualcomm 的 INT2 支持是否对应可用的精度尚无第三方验证。**判断：**手机上的主流量产位宽仍是 4-bit，2-bit 是 Apple 凭自研模型与 QAT 流水线独享的优势，OS 厂商若不掌握训练管线，无法复制。

**投机解码。**2026 年发生了实质变化。Google 于 2026-05 发布 Gemma 4 的 MTP drafter：4 层、约 74M 参数、共享 KV、用 top-k 簇替代全词表投影 [R5]；LiteRT-LM 中“两行配置”开启，S26 Ultra GPU 上最高 2.2 倍 [R4]。模型卡给出分任务数据：GPU 上摘要 91.7 vs 基线 51.5 tok/s（约 1.8 倍），自由生成仅 66.5（约 1.3 倍）；CPU 上代码任务 36.3 反低于基线 40.7 [R3]。官方建议是 GPU 上全任务开启，E2B 在 CPU 上选择性开启 [R5]。内存代价小（GPU 上约 -30 至 +30 MB，CPU 上约 +50 至 +220 MB）。三星的 DS2D 是无 drafter 的树式自投机，最高 2.3 倍 [R17]；学术界的 sd.npu 用 NPU 空闲算力做投机，1.06–3.81 倍速度和 1.07–4.71 倍能耗节省，但它面向端侧 RAG 场景 [R20]。**反方：**Google 博客的 3 倍来自服务器 GPU（RTX PRO 6000），不能外推到手机 [R5]；模型卡注明解码速度是否开启 MTP 未说明，并且同一张卡里 S26 Ultra CPU 基线分别出现 46.9 与 40.7 tok/s 两个数（前者在主表，后者在投机解码表），口径不一 [R3]（待核实）。EAGLE、LayerSkip 在 NPU 上的落地我本轮没有检到公开证据（见 §8）。**判断：**投机解码在 GPU 上已是 L3，在 NPU 上仍是 L1–L2；收益与任务强相关，OS 层若要暴露开关，应该由模型包按任务类型给默认值，而不是全局开启。

**KV 复用。**可核实的端侧证据是会话级而不是跨请求级：LiteRT-LM 支持序列化 KV 的会话保存与恢复，恢复后跳过重复 prefill [R4]（B）；Chrome Prompt API 支持 `session.clone()` 分叉对话并保留上下文与初始提示，溢出时丢弃最旧的提示-响应对但永不丢系统提示 [R18]（A）；Apple 的 KV cache 共享是模型内部块间共享，不是跨请求复用 [R7]。跨应用共享系统提示词 KV 的平台级前缀缓存，我本轮没有找到任何手机平台的公开实现（Apple Foundation Models 是否预热/复用系统提示未能核实）。**判断：**会话级 KV 的保存、恢复、分叉已经是运行时的标准能力，但“系统提示词 KV 作为系统服务跨应用共享”在手机上仍是空白——这与接缝 J2 的侧信道问题连在一起，由 C4a/C4b 评估内存与隔离，本报告只确认推理侧尚无现成接口。

**prefill 上 NPU。**文献分成两派。支持派：llm.npu 报告 prefill 22.4 倍、能耗 30.7 倍，首次在十亿级模型上超过 1000 tok/s [R21]；HeteroInfer 在 GPU+NPU 协同下对 PowerInfer-2 的 NPU 路线最高 3.69 倍，InternLM-1.8B 序列 256 下 1092 tok/s，对比 llm.npu 的 564 tok/s [R22]。质疑派：2026-05 的阶段级研究称 prefill 阶段 CPU 最高比 NPU 快 1.6 倍，decode 阶段 NPU 仅 1.05–1.2 倍，NPU 卸载越多能耗越高，最高 +51% [R9]。官方运行时的态度更接近质疑派：LiteRT-LM 在三星 S26 Ultra 上的 prefill 用 GPU 达到 3808 tok/s、TTFT 0.3 s，已经足够快 [R3]；NPU 路线在官方模型卡里只有 IoT 板的一行，同样给出 3747 tok/s 与 0.3 s [R3]。开发者社区报告 `Backend.NPU()` 在部分设备上会因驱动碎片化而崩溃（DEV Community 帖，D 级，传闻，待核实）。分歧点：论文基线（llama.cpp、MNN 的老版本 CPU/GPU 实现）和官方 GPU 实现差距很大；R9 的设备与模型摘要未给出，不能与 R21/R22 直接对比。**判断：**“prefill 上 NPU”的价值需要重新用最新 GPU 基线、同设备、含能耗来测；以 2026 年官方数据看，手机上 GPU 已经把 TTFT 压到亚秒级，NPU 的主要卖点退化为能耗与不占 GPU（让位给图形与 UI），而不是速度。

**手机实测汇总。**tokens/s 与 TTFT 有可信官方数据（见 §2 Gemma 4 行）。J/token 没有找到手机上的公开实测；R30 给出持续负载下的降频事实：iPhone 16 Pro 两次迭代内吞吐损失近半，三星 S24 Ultra 因 OS 强制 GPU 频率下限而终止推理 [R30]（C，Qwen2.5-1.5B 4bit）。这意味着**峰值 tok/s 对 Agent 长任务没有意义，稳态才是设计输入**。

**这说明什么：**端侧加速的“可用档”已经由 GPU + 4-bit + MTP 达成，NPU 上的收益尚未被官方数据证实且能耗结论有争议；OS 级推理子系统的设计应以稳态功耗和热降频为约束，而不是峰值吞吐。

### Q5 端云路由

**现状。**见 §7 对比表。共同点：几乎所有“隐私云”方案都不让客户端自动按内容敏感度决策，而是（a）用户逐请求发起（Meta），（b）由开发者选模式（Firebase），（c）由厂商内部逻辑决定、对外只承诺隐私性质（Apple、Google）。Apple 的 WWDC26 新信息：Foundation Models 框架可用同一套 Swift API 调用 PCC 上的 Apple 模型与 Claude、Gemini 等第三方服务端模型，并对低下载量开发者免费开放 PCC [R31]（C）。关于路由决策谁做，MacRumors 和 Apple 第三代模型页都没有说明 [R31, R32]。Google 的 Private AI Compute（2025-11-11）运行在 TPU 与 Titanium Intelligence Enclaves 上，公开首批用例是 Pixel 10 的 Magic Cue 与录音机摘要；官方页面没有说明设备如何决定端侧还是云侧 [R1]（B）。媒体转述的实现细节（AMD SEV-SNP 中间服务器、IP blinding relays、双向证明）来自技术简报的二手报道（C，待核实原文）[R2]。

**隐私机制的强度问题。**这是本轮最重要的新证据。Meta 的 Private Processing 公开了完整设计（RA-TLS、OHTTP、第三方透明日志、匿名凭证、无状态）[R13, R14]；之后 Trail of Bits 的审计发现：证明报告缺少客户端新鲜性（可被重放）、环境变量与 ACPI 表未被度量、固件补丁级别信任自报，共 28 项，8 项高危，16 项已修复 [R15]（B）。NCC Group 的审计则指出对 Meta 控制的签名密钥与 AMD/NVIDIA 专有固件存在无法完全审计的信任依赖（经 CyberInsider 转述，C）[R33]。Apple 方面，WiSec 2026 的逆向工作称 PCC 的编译二进制不透明、无可复现构建、无符号，所以“运行的软件与规格一致”无法独立确认 [R8]（A）。**判断：**云侧隐私是“可审计的承诺”而不是“可证明的事实”；OS 路由层应当把隐私保证建模为带过期与撤销的信任等级，而不是布尔值。

**NVIDIA OpenShell。**文档显示沙箱内代码调用 `inference.local`，直接外联则由 `network_policies` 评估；路由器负责剥离沙箱自带凭证并从配置的 provider 记录注入真实凭证；一个 gateway 只配置一个 provider 与模型，所有沙箱共享同一后端；不匹配 provider 支持模式的请求被拒绝 [R26]（A，来自检索摘要，我的 WebFetch 直读返回 404，原文未复核）。它的“Privacy Router”本质是凭证与出口治理，并不依据内容敏感度选模型。**判断：**该路线对应 J8 的“沙箱出口 + 凭证”半边，不对应“敏感度标签路由”半边。

**学术路由。**RouteLLM 用偏好数据训练路由器，在某些情况下成本降低超过 2 倍（摘要，未给质量保持百分比）[R24]；Hybrid LLM（ICLR 2024）在质量与成本感知下最多减少 40% 大模型调用 [R25]；FrugalGPT 的级联思路见 §8（未复核）。这批工作都是“质量/成本”路由，不含隐私；隐私感知路由最近出现：PRISM（AAAI 2026）在端侧做实体级敏感度打分，软门控选择 cloud/edge/collaborative，协同路径用本地差分隐私，能耗与延迟降到基线的 40–50% [R19]（A，自报）；另有临床文本策略路由器（NeurIPS 2026 条目，规范条目待核实）和 PrivacyPAD（聚合站条目，无法确认 arXiv 号）。**反方/分歧：**PRISM 自己指出二元阈值路由会误判指令，要么压垮端侧、要么泄漏隐私，暗示敏感度打分器本身是单点风险；Chrome 文档则承诺 Prompt API 使用时“不向 Google 或第三方发送数据”，走完全相反的“不路由”路线 [R18]。

**三星与 Chrome。**三星公开表现为用户级总开关：“仅在设备上处理数据”，开启后云依赖功能被禁用而非降级；各来源对菜单路径说法不一，且未找到三星官方页面，开关是否同样覆盖 Perplexity、Gemini 查询未能核实（C，待核实）[R34]。Firebase AI Logic 的 hybrid 仅支持 Chrome 桌面 Web 应用（Chrome 139 及以上、需开启 flag），端侧只支持单轮文本生成（非聊天），支持 JSON/枚举结构化输出；四种模式由开发者在代码里选择 [R10]（A）。

**延迟数据。**Apple、Google、Meta、Firebase、三星都没有公开端云切换或首 token 延迟；Meta 的工程文章明确没有延迟数字 [R14]。**这是公开资料空白**，也意味着“路由依据含延迟”在产业界目前无公开证据。

**这说明什么：**INF-4 的方向（存在路由层）得到支持，但“自动按隐私/成本/延迟三元组路由”在产业界没有先例；先例是“用户或开发者选信任等级 + 平台保证云端隐私性质”，自动化只在 L1 学术工作中出现。

### Q6 LoRA / 适配器生态与热插拔

**Apple（唯一向第三方开放）。**适配器与系统模型版本一一绑定：“每个适配器只兼容单一特定的系统模型版本”，需为每个系统模型版本各训一个；每个约 160 MB，不应放进 App 主包，建议经 Background Assets 按设备下载对应版本；训练与本地测试不需要权限，上架前需 Account Holder 申请 Foundation Models Framework Adapter Entitlement；工具包 26.0.0 是最后一版，不兼容 OS 27 及之后 [R11]（A）。开发者论坛有 beta 期适配器与新底座不兼容的报告 [R35]（C）。**注意：**“最后一版、不兼容 OS 27”这句话我无法判断是 Apple 终止该路线、改版为新工具，还是页面未更新，列入待核实。

**Google。**ML Kit GenAI API 的结构是 Gemini Nano 底座 + 功能专属 LoRA 适配器 + 推理参数层；适配器是 Google 自训、按功能（摘要、校对、改写、图像描述）分发，目的是让每个 API 在 Nano 版本变化时仍达到质量门槛 [R12]（B）。没有检到第三方挂载自有 LoRA 到 Gemini Nano 的入口，Prompt API 与 Chrome 文档也未提及 LoRA。

**NPU 上的多适配器。**三星团队的两篇论文把 LoRA 权重作为运行时输入送入同一张冻结的推理图，免重编译、免重量化，在 Galaxy S24/S25（SM8650、SM8750）上验证 [R16, R17]（C，L2）。摘要强调“无需重新编译或额外内存开销”，**但没有给出适配器切换延迟**。Qualcomm 官方文档中的多适配器切换机制本轮没有检到（见 §8）。

**服务器与边缘多适配器服务。**EdgeLoRA 提出自适应适配器选择、缓存与池化的异构内存管理、批量 LoRA 推理，对 llama.cpp 最高 4 倍吞吐，评测设备 8–64GB [R27]（C，L1）；S-LoRA、Punica 的统一分页与批处理思路属于服务器侧基础工作，本轮未复核（§8）。端侧可迁移性：思想（适配器池化、批量）可迁移，但手机上并发租户数量少，批处理收益有限，需改造为“少量适配器 + 快速换入”。

**指标现状。**热插拔延迟：无公开手机实测。内存开销：Apple 约 160 MB/个磁盘占用，运行时常驻开销未披露；三星称无额外内存但无数字。底座升级兼容性：Apple 明确不兼容（须重训）；Google 通过自训并随底座同步发布来规避第三方感知。

**这说明什么：**平台实际把适配器当作“与底座同版本的编译产物”，兼容性成本由开发者（Apple）或平台（Google）承担；热插拔延迟反而是次要问题。INF-2 的“多应用共享底座”成立，“LoRA 热插拔”要加一层版本契约，否则就是 Apple 当前的困境。

### Q8 推理服务对 Agent 的接口（J3）

**结构化输出与约束解码。**Apple：框架把响应格式注入提示，模型经专门数据集后训练来遵循 guided generation 规范（据检索摘要对技术报告的转述），技术报告摘要同时称框架暴露 guided generation 与 constrained tool calling [R7]；Apple 是靠后训练还是运行时约束解码，需核实（§8）。Chrome：向 `prompt()` 传 JSON Schema 作为 `responseConstraint`，schema 会占上下文窗口，可用 `measureContextUsage()` 测量，或用 `omitResponseConstraintInput` 省略 [R18]（A）。LiteRT-LM：受约束解码可强制 JSON schema 或输出语法；函数调用会暂停执行、返回结构化工具调用请求、待工具结果到来后恢复 [R4]（B）。Firebase 端侧：支持 JSON 与枚举结构化输出 [R10]。

**会话与上下文管理。**LiteRT-LM 的 KV 会话保存/恢复；Chrome 的 `clone()`、`contextUsage/contextWindow`、`contextoverflow` 事件及“永不丢系统提示”的溢出语义 [R4, R18]。这说明**会话状态由运行时（进程内）托管，而不是由系统服务跨进程托管**；系统级 KV 托管（C4b 范围）目前没有公开接口。

**指令层级与注入防护。**我在 Chrome Prompt API 文档、LiteRT-LM 博客、Apple 技术报告摘要、Firebase hybrid 文档中都没有找到服务层注入防护的描述；Chrome 页面明确未讨论 prompt injection [R18]。检索范围有限：未读 Apple Foundation Models 的安全文档、AICore 的深层文档、HarmonyOS 文档（配额耗尽）。基础工作（OpenAI 的 instruction hierarchy、CaMeL、spotlighting）属于沙箱子模块 C2b 的范围，仅在 §8 列出待复核条目。

**接口格式的差异。**Apple 是 Swift 类型驱动（`@Generable` 之类的宏，具体名称本轮未核实）；Chrome 是 JSON Schema；LiteRT-LM 是 schema 或语法。三者没有互通格式，而 MCP 工具注解与 AppFunctions 属于 C2b。**判断：**推理侧应当提供“schema → 受约束采样”的最小原语，接口面（沙箱）负责把 MCP/AppFunctions 的工具描述翻译成 schema。

**这说明什么：**格式正确性（J3 的一半）已经由推理服务提供，趋势明确；安全性（另一半）没有任何平台在推理层提供，应放到执行层，这与沙箱立场（SBX-2/SBX-4）一致。

---

## §4 趋势判断

**正在收敛的方向**
- 端侧 4-bit 为量产基线，GPU 是官方运行时的主力后端（LiteRT-LM、Gemma 4）[R3, R4]。
- 投机解码（MTP drafter）进入官方运行时，以“可选开关 + 按任务建议”的形式发布 [R3, R5]。
- 结构化输出与函数调用由推理服务/运行时提供（Apple、Chrome、LiteRT-LM）[R7, R18, R4]。
- 云侧隐私的技术模板：TEE 证明 + 无状态 + 匿名中继 + 透明日志 [R1, R13, R6]。
- 适配器与底座版本绑定，且平台自行承担兼容性（Apple 由开发者重训，Google 自训）[R11, R12]。

**公认的空白点**
- 手机端到端能耗（J/token）与稳态降频曲线的公开官方数据。
- NPU 路线的官方手机数据：LiteRT-LM 模型卡只有 IoT 板的 NPU 行 [R3]。
- 多适配器切换延迟的手机实测。
- 端云切换延迟与路由决策依据的公开数据（Apple、Google、Meta 均无）。
- 跨应用共享系统提示词 KV 的平台级前缀缓存。
- 推理服务层的注入防护实现。
- 敏感度标签的来源：没有任何产品公开说明标签来自记忆/权限系统（J8）。

**仍有分歧的问题**
- prefill 是否值得放 NPU：llm.npu、HeteroInfer 与阶段级反例 R9 相冲突，且基线不同 [R21, R22, R9]。
- 路由是否应自动化：产业界选择显式信任等级，学术界做自动路由 [R19, R10, R13]。
- 云侧隐私是否可独立验证：Meta 有第三方日志，Apple 有 VRE 与赏金但被指二进制不透明 [R14, R8]。
- 适配器是否值得向第三方开放：Apple 开放但版本脆弱，Google 不开放 [R11, R12]。

---

## §5 立场评审表

| 立场 ID | 判断（支持 / 挑战 / 需修订） | 关键证据 | 最强反方证据 | 修订建议 | 置信度（高 / 中 / 低） |
|---|---|---|---|---|---|
| INF-2 多应用共享底座，LoRA 等适配器热插拔 | **需修订**：“共享底座”支持；“热插拔”需加版本契约，且第三方适配器不宜作为默认能力 | 三星把 LoRA 作为运行时输入送入同一冻结图，免重编译（Galaxy S24/S25）[R16, R17]；Google 的 ML Kit 用功能专属 LoRA 保证 Nano 版本变化时质量 [R12] | Apple 适配器与单一系统模型版本绑定，约 160 MB/个，须逐版本重训，工具包 26.0.0 为最后一版且不兼容 OS 27+ [R11]；Google 不开放第三方适配器 [R12]；Chrome/LiteRT-LM 文档未见 LoRA（本轮未检到） | 1) 把“适配器”定义为带 `base_model_id + 版本区间` 的受管产物，由 OS 负责匹配、下载、淘汰；2) 默认路径是提示 + 结构化输出，适配器作为专业场景扩展；3) 未取得手机切换延迟数据前，不以“毫秒级热插拔”作为设计承诺，列入仿真/真机验证项；4) 底座升级的兼容策略要早于接口设计 | 中 |
| INF-4 端云之间存在按隐私、成本、延迟路由的路由层 | **需修订**：“存在路由层”支持；“自动按三元组路由”缺少产业先例 | Apple 以统一 Swift API 覆盖端侧、PCC、第三方服务端模型 [R31]；Firebase 四种显式模式 [R10]；PRISM 在端侧实体级打分并软门控 [R19]；OpenShell 的统一端点 + 出口策略 + 凭证注入 [R26] | Chrome 路线承诺不外发 [R18]；Meta 由用户逐请求发起 [R13]；三星是总开关 [R34]；RouteLLM/Hybrid LLM 不含隐私维度 [R24, R25]；TEE 审计显示云侧“隐私”依赖实现质量 [R15, R8] | 1) 把路由层拆成“策略执行”（OS：允许哪些端点、需要什么证明、携带什么标签）与“选择优化”（框架/应用：质量与成本）；2) 隐私等级写成带过期的信任档位，要求证明新鲜性（nonce 绑定握手）；3) 敏感度标签来源需来自记忆/权限系统而非模型自评，PRISM 自陈阈值易误判；4) 延迟项暂不进入 OS 策略，缺公开数据 | 中 |
| INF-5（推理加速相关部分）权重与 KV 需要可分页 | **部分支持**：推理框架已支持“常驻集小于模型体积”和会话级 KV 序列化，但不是 OS 可分页 | Gemma 4 的 PLE 不入内存，物理占用 607 MB 对 2.58 GB 文件 [R4]；LiteRT-LM KV 会话保存/恢复 [R4]；Chrome 溢出时丢弃最旧提示-响应对 [R18] | 运行时自管而非 OS 页级管理；官方文档未显示 KV 可被系统回收或换出；Apple KV 共享是模型内部块间共享 [R7] | 在推理侧要求运行时暴露“可序列化/可丢弃/可重建”三态接口，以便 C4b 的内存管理接管；不要假设推理框架已支持页级换入换出 | 中 |

---

## §6 接缝发现

**J3 工具调用/结构化输出 ↔ 接口面（主责）**
- 格式约束由推理服务提供：Apple、Chrome、LiteRT-LM 均如此 [R7, R18, R4]；schema 占上下文是实际代价（Chrome）[R18]。
- 注入防护：未发现任何端侧推理服务提供；建议放执行层（沙箱），与 C2b 的“通用攻防”衔接。
- 接口建议：推理服务暴露 `generate(schema|grammar)` 与“暂停于工具调用/恢复”语义（LiteRT-LM 已有）；工具元数据到 schema 的翻译归接口面。
- 缺口：Apple、Chrome、LiteRT-LM 三者格式不互通。

**J6 LoRA 适配器热插拔与权重分页（主责）**
- 三星的“适配器作为运行时输入”意味着适配器是小张量文件，不进入编译图；这使 J6 变成普通的权重分页问题，可与底座权重分页统一记账。
- 但 Apple 适配器约 160 MB 且按底座版本隔离，意味着内存/存储侧要按“底座版本 × 适配器”两级管理。
- 切换延迟与内存开销没有手机实测，需要 C4b 与仿真补数。

**J8 端云路由与隐私标签（主责）**
- 未发现任何产品公开使用“来自记忆/权限系统的敏感度标签”来路由。
- 最接近的是：PRISM 的端侧实体打分（L1）[R19]；Meta 的“用户选择 + 仅发送所需数据”[R13]；Apple/Google 的“厂商内部决策”。
- OpenShell 把凭证注入和端点治理放在出口代理，这与 C2b 的凭证经纪人是同一机制，可复用。
- 建议：标签作为请求元数据由调用方携带，路由层只做“标签 → 允许的端点集合”的硬约束；模型自评仅作为兜底提示，不作为授权依据。

---

## §7 组件特有输出：端云路由方案对比表

| 方案 | 路由依据 | 决策方 | 隐私机制 | 延迟数据 | 证据等级 | 端侧可迁移性 |
|---|---|---|---|---|---|---|
| Apple PCC + Foundation Models（含第三方服务端模型）| 未披露；框架统一 API 可选端侧/PCC/第三方 [R31, R32] | 开发者选模型；端云细则未披露 | 无状态、证明、透明日志、VRE、赏金 [R6]；逆向称二进制不透明 [R8] | 未找到公开资料 | B（路由）、A（逆向） | 云侧机制不可迁移；客户端验证逻辑可参考 |
| Google Private AI Compute | 官方称“比端侧需要更多推理/算力的任务”；判定细则未披露 [R1] | 厂商（Pixel 功能）；设备如何判定未披露 | TPU + TIE、远程证明、加密；媒体称 SEV-SNP 中间层、IP blinding relays（待核实）[R1, R2] | 未找到公开资料 | B；C | 云侧不可迁移 |
| Meta WhatsApp Private Processing | 用户逐请求发起；仅发送所需数据 [R13] | 用户 | CVM（AMD SEV-SNP + NVIDIA 机密计算）、RA-TLS、OHTTP、匿名凭证、第三方透明日志、无状态 [R13, R14]；审计 28 项问题 [R15] | 工程文章未给延迟 [R14] | B | 客户端协议可参考 |
| Firebase AI Logic hybrid | 模型可用性；四种模式由代码指定 [R10] | 应用开发者 | 无额外机制；云走 Gemini API | 未找到公开资料 | A | 仅 Chrome 桌面 Web（Chrome 139+，需开 flag）；Android/iOS 未找到 |
| Chrome Prompt API | 不路由；端侧内置模型 [R18] | 浏览器 | “不向 Google 或第三方发送数据” [R18] | 未找到端云数据；下载与硬件门槛见文档（≥22GB 存储，>4GB 显存或 16GB 内存）| A | 桌面专属，Android/iOS 不支持 [R18] |
| 三星 Galaxy AI | 用户开关：仅设备处理 vs 允许云 [R34] | 用户 | 未找到三星官方说明 | 未找到公开资料 | C | 待核实官方页面 |
| NVIDIA OpenShell privacy router | 网络策略 + 配置的单一 provider [R26] | 管理员/运维 | 剥离沙箱凭证、注入真实凭证；非敏感度路由 | 未找到公开资料；流式空闲容忍 120 秒 | A（据检索摘要，原文 404 未复核）| 概念可迁移到手机出口代理 |
| RouteLLM | 偏好数据学习的质量/成本路由 [R24] | 路由模型（网关侧）| 无隐私维度 | 成本降 2 倍以上（摘要）| A | 路由器小，可迁移；训练数据需自备 |
| Hybrid LLM | 预测查询难度，质量阈值可调 [R25] | 路由模型 | 无 | 大模型调用最多减 40% | A | 可迁移 |
| PRISM | 实体级敏感度 → 云/端/协同 [R19] | 端侧打分器 | 本地差分隐私 + 云端草图 | 能耗与延迟降至基线 40–50% | A（自报）| 需改造：打分器与端侧精修模型常驻成本 |

---

## §8 参考资料与待核实清单

### 参考资料

| 编号 | 标题 | 机构/作者 | URL | 日期 |
|---|---|---|---|---|
| R1 | Private AI Compute（官方博客）| Google | https://blog.google/technology/ai/google-private-ai-compute/ | 2025-11-11 |
| R2 | Google launches Private AI Compute...（二手报道）| TechInformed | https://techinformed.com/google-launches-private-ai-compute-for-cloud-gemini-with-on-device-level-privacy/ | 2025-11 |
| R3 | gemma-4-E2B-it-litert-lm 模型卡 | LiteRT Community / Google | https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm | 2026（日期待核实）|
| R4 | Blazing fast on-device GenAI with LiteRT-LM | Google Developers Blog | https://developers.googleblog.com/blazing-fast-on-device-genai-with-litert-lm/ | 2026-05-19 |
| R5 | Accelerating Gemma 4: faster inference with multi-token prediction drafters | Google | https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/ | 2026-05 |
| R6 | Private Cloud Compute 相关研究环境与综述 | Apple / 二手整理 | https://bitboom.github.io/2025-12-31/pcc-three-pillars | 2025-12（二手）|
| R7 | Apple Intelligence Foundation Language Models Tech Report 2025（arXiv 2507.13575）| Apple | https://arxiv.org/abs/2507.13575 | 2025-07 |
| R8 | Unlocking Apple's Private Cloud Compute（arXiv 2605.24239，WiSec 2026）| Dittmar, Stephan, Völkl, Hollick, Classen | https://arxiv.org/abs/2605.24239 | 2026-05-22 |
| R9 | When NPUs Are Not Always Faster（arXiv 2605.27435）| Li, Qi, Chen | https://arxiv.org/abs/2605.27435 | 2026-05-22 |
| R10 | Hybrid on-device inference（Firebase AI Logic）| Google Firebase | https://firebase.google.com/docs/ai-logic/hybrid-on-device-inference | 2026（页面日期待核实）|
| R11 | Foundation Models adapter training toolkit | Apple Developer | https://developer.apple.com/apple-intelligence/foundation-models-adapter | 2026（页面日期待核实）|
| R12 | The latest Gemini Nano with on-device ML Kit GenAI APIs | Android Developers Blog | https://android-developers.googleblog.com/2025/08/the-latest-gemini-nano-with-on-device-ml-kit-genai-apis.html | 2025-08 |
| R13 | Building Private Processing for AI tools on WhatsApp | Meta Engineering | https://engineering.fb.com/2025/04/29/security/building-private-processing-for-ai-tools-on-whatsapp/ | 2025-04-29 |
| R14 | WhatsApp Private Processing（同批发布）| Meta Engineering | https://engineering.fb.com/2025/04/29/security/whatsapp-private-processing/ | 2025-04-29 |
| R15 | What we learned about TEE security from auditing WhatsApp's Private Inference | Trail of Bits | https://blog.trailofbits.com/2026/04/07/what-we-learned-about-tee-security-from-auditing-whatsapps-private-inference/ | 2026-04-07 |
| R16 | Quantization with Unified Adaptive Distillation to enable multi-LoRA ... on edge（arXiv 2603.29535）| 三星研究院 | https://arxiv.org/abs/2603.29535 | 2026-03-31 |
| R17 | Unlocking the Edge deployment and ondevice acceleration of multi-LoRA enabled one-for-all foundational LLM（arXiv 2604.18655）| 三星研究院 | https://arxiv.org/abs/2604.18655 | 2026-04 |
| R18 | Prompt API | Chrome for Developers | https://developer.chrome.com/docs/ai/prompt-api | 2026（页面日期待核实）|
| R19 | PRISM: Privacy-Aware Routing for Adaptive Cloud-Edge LLM Inference（arXiv 2511.22788，AAAI 2026）| Zhan 等 | https://arxiv.org/abs/2511.22788 | 2025-11-27 |
| R20 | Accelerating Mobile Language Model via Speculative Decoding and NPU-Coordinated Execution（arXiv 2510.15312）| Chen, Xu 等 | https://arxiv.org/abs/2510.15312 | 2025-10-17（v4 2025-12-17）|
| R21 | Fast On-device LLM Inference with NPUs（llm.npu，arXiv 2407.05858）| 学术团队（作者待核实）| https://arxiv.org/abs/2407.05858 | 2024-07 |
| R22 | Characterizing Mobile SoC for Accelerating Heterogeneous LLM Inference（arXiv 2501.14794）| 学术团队（作者待核实）| https://arxiv.org/pdf/2501.14794 | 2025-01 |
| R23 | PowerInfer-2: Fast Large Language Model Inference on a Smartphone（arXiv 2406.06282）| 上海交大 IPADS 等（待核实）| https://arxiv.org/abs/2406.06282 | 2024-06 |
| R24 | RouteLLM: Learning to Route LLMs with Preference Data（arXiv 2406.18665）| Ong 等，UC Berkeley | https://arxiv.org/abs/2406.18665 | 2024-06-26（v4 2025-02-23）|
| R25 | Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing（ICLR 2024，arXiv 2404.14618）| Ding 等 | https://arxiv.org/abs/2404.14618 | 2024-04-22 |
| R26 | About Inference Routing（OpenShell 文档）| NVIDIA | https://docs.nvidia.com/openshell/latest/inference/index.html | 2026（页面日期待核实；直读 404，据检索摘要）|
| R27 | EdgeLoRA: An Efficient Multi-Tenant LLM Serving System on Edge Devices（arXiv 2507.01438）| Shen 等 | https://arxiv.org/abs/2507.01438 | 2025-07-02 |
| R28 | Gemma LiteRT-LM on IQ8 教程 | Qualcomm Dragonwing Docs | https://dragonwingdocs.qualcomm.com/tutorials/gemma-litert-lm-on-iq8 | 2026（日期待核实）|
| R29 | Snapdragon 8 Elite Gen 5 发布报道 | Neowin（媒体）| https://www.neowin.net/amp/qualcomm-announces-snapdragon-8-elite-gen-5-with-major-ai-and-video-upgrades/ | 2025-09 |
| R30 | LLM Inference at the Edge: Mobile, NPU, and GPU Performance Efficiency Trade-offs Under Sustained Load（arXiv 2603.23640）| Tummalapalli 等 | https://arxiv.org/abs/2603.23640 | 2026-03 |
| R31 | Apple Outlines Major AI and Developer Tool Updates at 2026 Platforms State of the Union | MacRumors | https://www.macrumors.com/2026/06/09/apple-outlines-major-ai-and-developer-tool-updates/ | 2026-06-09 |
| R32 | Introducing the third generation of Apple Foundation Models | Apple Machine Learning Research | https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models | 2026-06-08（后续更新至 2026-09-09）|
| R33 | WhatsApp's AI system passes security audit but with asterisks（NCC Group 审计转述）| CyberInsider | https://cyberinsider.com/whatsapps-ai-system-passes-security-audit-but-with-asterisks/ | 2025（日期待核实）|
| R34 | Galaxy AI 隐私开关说明 | Beebom（媒体）| https://gadgets.beebom.com/guides/samsung-galaxy-ai-explained | 日期待核实 |
| R35 | Foundation Models Adapter Training Toolkit v0.2.0 LoRA Adapter Incompatible with macOS 26 Beta 4 Base Model | Apple Developer Forums | https://developer.apple.com/forums/thread/794839 | 2025 beta 期 |

### 待核实清单

1. Apple 适配器工具包“26.0.0 为最后一版，不兼容 OS 27+”：是路线终止、改由 Core AI 或新工具接替，还是页面未更新（R11）。
2. Apple guided generation 的实现方式：后训练约束还是运行时约束解码；`@Generable` 的具体语义（R7 仅据检索摘要转述）。
3. Apple 适配器 rank 32 的数字（来自检索摘要，未在摘要原文复核）。
4. Apple Foundation Models 是否在跨请求层面复用系统提示词 KV；端侧模型 12GB 设备要求仅见低质量博客（D，传闻，待核实）。
5. WWDC26 中 Foundation Models 对 PCC 与第三方模型的路由决策方与规则（R31、R32 均未说明）。
6. “Apple 在 Google Cloud 的 NVIDIA 机密 GPU 上运行 PCC”：Apple 第三代模型页称 AFM 3 Cloud Pro 将 PCC 扩展到 Google Cloud 的 NVIDIA GPU（R32，B），但该页并未描述其证明与隐私细节，需读 Apple 安全博客。
7. Google Private AI Compute 技术简报原文：TPU 代际（Trillium 还是 Ironwood 类，媒体口径不一）、SEV-SNP 中间层、IP blinding relays（R2 为二手；技术简报直读失败）。
8. Private AI Compute 是否向第三方开发者开放 API；ML Kit 与 Gemini Nano 是否有云回退（本轮配额耗尽未检）。
9. Firebase AI Logic hybrid 是否支持 Android/iOS（文档只写 Chrome 桌面）。
10. 三星官方对“仅在设备上处理”开关的覆盖范围；三星 Personal Data Engine 与云路由的关系。
11. Qualcomm Genie/QAIRT 官方文档中的多 LoRA 切换机制与延迟；Snapdragon 8 Elite Gen 5 的 220 tok/s 测试配置。
12. 手机 NPU 上 EAGLE、LayerSkip 的公开实现（本轮未检到）。
13. MediaTek NeuroPilot 的 LLM 数据点；LiteRT-LM 在 Android 手机 NPU 上的官方 tok/s（模型卡仅有 IoT 板）。
14. llm.npu、HeteroInfer、PowerInfer-2 的发表会议与年份（检索只确认 arXiv，未确认 SOSP/ASPLOS/MobiSys 等）；EdgeLoRA 的 DOI 10.1145/3711875.3729141 页面链接了 ACM 条目但未命名会议。
15. R9 的设备与模型（摘要未命名）。
16. 本轮未复核、凭记忆列出的基础工作（arXiv 号需复核后再引用）：FrugalGPT（2305.05176）、S-LoRA（2311.03285）、Punica（2310.18547）、EAGLE（2401.15077）、LayerSkip（2404.16710）、OpenAI instruction hierarchy（2404.13208）、CaMeL（2503.14576）、Meta Agents Rule of Two。
17. 注入防护是否在 AICore、Apple Foundation Models、HarmonyOS 推理服务层提供（本轮未读相关安全文档）。
18. HarmonyOS 的适配器、路由与结构化输出能力：本轮没有检索，**未找到公开资料不等于不存在**。
19. NVIDIA OpenShell 文档（R26）直读 404，其内容仅来自检索摘要。
20. Gemma 4 模型卡 CPU 基线 46.9 vs 40.7 tok/s 的口径差异（R3）。

**最大资料空白**：手机端 NPU 官方实测、多适配器切换延迟、端云切换延迟、推理层注入防护。

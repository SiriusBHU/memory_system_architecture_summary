# AgentOS 调研交叉验证报告（Phase 4）

验证日期：2026-11-06。验证范围：agentos_dim01.md ~ dim12.md（dim01-03 推理框架；dim04-06 沙箱；dim07-09 记忆；dim10-12 内存管理）。
方法：通读 12 份报告 → 跨报告比对同一指标的口径 → 对冲突项做 1-3 次定向搜索裁决 → 每组件抽查 ≥3 个关键量化论断（web 搜索核对来源真实性与数字准确性）→ 覆盖度对照检查。

置信度定义：High = ≥2 个独立底层来源一致（注：两份报告引用同一底层来源不算独立）；Medium = 单一权威来源（官方文档/论文原文）；Low = 弱来源或孤立论断；Conflict Zone = 跨报告数字/结论冲突或时间口径不一致。

---

## 一、四级置信度分类表（按组件分组）

### 组件 1：推理框架（dim01-03）

**High Confidence**
1. Apple AFM ~3B 端侧模型 + LoRA adapter 热插拔；2024 技术报告口径 rank-16 / 数十 MB（arXiv 2407.21075 官方原文核实：dim01/dim03 引用准确）【已核实】
2. S-LoRA 单 A100-80GB 同时服务 2000 adapter、吞吐 4× vs vLLM / 30× vs HF PEFT；Punica SGMV 12× 吞吐、+2ms/token（dim01/02/03 一致，第三方独立综述确认）【已核实】
3. NNAPI 于 Android 15 官方 deprecated，NN HAL 保留（dim01+dim12 一致，官方口径多源确认）【已核实】
4. LiteRT Gemma-3n E2B 在 Dimensity 9500 上 prefill 1600 tok/s、decode 28 tok/s（Google 官方博客数字，≥2 个独立二手来源确认；注意系厂商基准）【已核实】
5. HarmonyOS AI 子系统日均 36.8 亿次 API 调用（dim01 两个来源 firecat+Pandaily 一致；Pandaily HDC 2026 报道确认 "3.68 billion API calls daily"）【已核实】
6. Apple Foundation Models：文本专用、iOS 26、4,096 token 上下文（WWDC25）、WWDC26 示例扩至 8,192（dim01+dim05 一致）【已核实】
7. llama.cpp 端侧事实标准地位 + ExecuTorch/LiteRT/MNN 碎片化格局（dim01+dim02 独立来源一致）
8. EdgeLoRA（arXiv 2507.01438 存在确认）边缘设备多租户 LoRA，吞吐最高 4× vs llama.cpp【存在性与 4× 已核实；adapter 数量口径见冲突 C7】
9. Apple PCC 端云路由架构（OHTTP relay、无状态、可验证）与 HPIC 模糊 token（dim01+dim03 均引官方）

**Medium Confidence**（单一权威来源）
1. AFM 出货模型/开发者工具包口径：rank-32、~160MB/个 `.fmadapter`（第三方逆向 fguzman82 GitHub + gamut.so 一致，但均非 Apple 官方文档；dim02 引用准确）
2. LiteRT QNN delegate 仅支持骁龙 8/8+ 系列（InfoQ 引 Google 官方）【已核实】
3. QNN（AI Engine Direct）仅接受 DMA-BUF 形式共享内存（Qualcomm 官方文档，dim12 引用准确）
4. FastVLM-0.5B：TTFT 0.12s、prefill >11,000 tok/s、decode >100 tok/s（Google 博客，InfoQ 2025-11 确认；**但芯片为 Snapdragon 8 Elite Gen 5，dim01/dim02 写"骁龙 8 Elite"系芯片代际标注不精确**）【已核实+限定】
5. Gemini Nano v3 需 12GB RAM（byteiota 二手）；"summarize/proofread 用 Nano、复杂任务走云端" 路由逻辑（Gurman 转述）
6. KV cache 量化论断：Qwen3-4B @8K FP16 ~2GB、INT4 ~500MB、TurboQuant 省 30–60%（dim02 单一整理源；与 dim10 的 470MB@4K INT4 交叉换算一致，可信度高但源头单一）
7. EAGLE-2 2.5–3.5×（EMNLP 2024 论文）；H100 实测 2.11×（维度技术博客）
8. iOS 27 Siri AI 改版（2026-09-14）等前瞻信息（progressivewebapps 单一媒体）

**Low Confidence**
1. HarmonyOS 7 盘古大模型 6.0 "入内核"（dim01 低质媒体，无技术出处）
2. "NPU 比 CPU 快 25 倍且功耗低五分之一"（SegmentFault 转述 Google I/O 2025，与 LiteRT 官方 "最高 100×" 口径混乱，见冲突 C5）
3. Beebom 2026 实测"旗舰机消费 App 无一用 NPU"（媒体实测，方向可信但样本与方法不透明）
4. HarmonyOS 分布式模型路由、端侧 NPU 细节（软文为主）

### 组件 2：沙箱（dim04-06）

**High Confidence**
1. Firecracker ≤125ms 启动、<5MiB 开销、150 VM/s/host（NSDI'20 + 多个独立 2026 来源一致确认；dim04 引用准确）【已核实】
2. Kubernetes SIG Apps agent-sandbox：Sandbox + SandboxTemplate + SandboxClaim + SandboxWarmPool 四 CRD（官方文档 + ≥5 个独立来源确认；dim04/dim06 一致）【已核实】
3. AgentDojo：无攻击 SOTA 效用 <66%、攻击成功率 <25%、加防御后 ~8%（arXiv 2406.13352 原文核实，dim06 引用准确；注"GPT-4o 69%"为 leaderboard 口径，见 C6）【已核实】
4. AWS AgentCore Policy（Cedar）GA 2026-03-03、default-deny、gateway 侧强制（dim04+dim05 一致，≥2 独立来源确认）【已核实】
5. The Attacker Moves Second（arXiv 2510.09023）：12 种防御在自适应攻击下 ASR >90%，USENIX Security 2026 收录（引用链确认）【已核实】
6. "端侧沙箱无商业产品"是 dim04 与 dim06 独立得出的共同空白结论（iOS 全靠 IPC-permissions，Android 无对应物）【结论级一致】
7. NVIDIA OpenShell 开源（Apache 2.0）+ Sentry/BlueField 硬件强制层（≥3 个 2026-09/10 独立来源）
8. MCP 安全事件潮与 MCP-at-edge CVE-2026-29060（dim04+dim06 一致，多源）

**Medium Confidence**
1. E2B ~150ms 启动、$0.000014/s 定价、1B+ 累计会话（E2B 官方/二手一致）
2. 腾讯 CubeSandbox 60ms 启动、<5MB 内存（腾讯官方 HCloud；无第三方复测）
3. Blaxel <25ms resume（Ry Walker + simular，两个二手但同一信息源链）
4. Modal cold start 中位 929ms / run秒价 $0.000097（agent37 实测）
5. MCP 2025-11-25 spec 六要点（官方 spec）
6. MCP 官方 registry 47,879 server（digitalapplied 单一媒体；未核实）
7. Cedar p99 ~12ms vs OPA ~60ms、规模 10×（cedar-policy.blog 第三方自测）
8. OpenAI AgentKit 开发者沙箱 0.9.0（OpenAI 开发者社区）
9. Asana 停 MCP 两周、Supabase RLS 泄漏、CVE-2025-59532 Codex（单媒体各一）

**Low Confidence**
1. Nova-Specialist 在 OSWorld 超 Operator 9.7pt（dim06 已自标"低/未核"；arXiv 2606.11786 未独立确认）
2. Anthropic"模型有逃逸动机"叙事（philosophybear 博客）
3. Northflank SOC 2 / GCP 探针实测数字（厂商自报）

### 组件 3：记忆（dim07-09）

**High Confidence**
1. Mem0 LoCoMo：J=66.9（66.88）vs full-context 72.9；p95 总延迟 1.44s vs 17.1s；~1.8K vs ~26K token（多源独立确认；dim07 引用准确）【已核实】
2. Zep/Graphiti：DMR 94.8% vs MemGPT 93.4%；LongMemEval +18.5pt、延迟 -90%（arXiv 2501.13956 摘要原文确认；dim07/dim09 一致）【已核实】
3. LongMemEval-V2 存在且数字准确：451 题、AgentRunbook-C 72.5% vs RAG 48.5% vs 编码 agent 69.3%（arXiv 2605.12493 确认；dim08 准确）【已核实】
4. GroupMemBench：最强系统仅 46.0%，knowledge-update 27.1%，BM25 匹敌多数系统（arXiv 2605.14498 摘要确认；dim08 数字准确；**注 dim08 正文 §1.3 误写 arXiv 号 2605.14493，脚注正确**）【已核实+小笔误】
5. SnapKV 3.6× 速度/8.2× 内存/单卡 380K（NeurIPS 2024 原文确认）；H2O 29× 吞吐/1.9× 延迟/5× 内存（NeurIPS 2023 原文确认）；Mooncake 525% 模拟吞吐/75% 真实负载（FAST'25 原文确认）——dim09 全部引用准确【已核实】
6. 记忆评测方法论存在系统性争议（检索 vs 全上下文、LoCoMo 质量问题、厂商自报），dim07 详述的 Mem0 vs Zep 论战为多源确认的真实分歧【结论级一致】
7. MemGPT/Letta 操作系统隐喻与三层记忆（dim07+dim08 独立来源一致）

**Medium Confidence**
1. MemoryOS（EMNLP 2025）LoCoMo F1 +49.11%（单一论文）
2. A-MEM NeurIPS 2025 六模块（单一论文）
3. Memora（arXiv 2604.20006 存在确认：FAMA 指标、forgetting benchmark）【存在性已核实，17.3% 等具体数字未逐项核】
4. 端侧 ANN：VectorTune 1.4–1.5×（VLDB 2026 单一论文）；Android ObjectBox、iOS ObjectivePGP（厂商文档）
5. MemexRL MCP 泄漏 34%（dim08 引用单一）
6. 端侧记忆合规分析（GDPR 删除权、Apple/Google/华为隐私口径）——整理准确但多为单源政策文本

**Low Confidence**
1. **AMemBench（arXiv 2609.13767，"10 维 76.83% vs 63.94%"）——搜索零结果，UNVERIFIED，疑似虚构或编号/名称错误（LongMemEval-V2 引文中只有 AMA-Bench，无 AMemBench）【标记 HALLUCINATED-SUSPECT】**
2. OSDN（arXiv 2607.05475，dim07）——搜索零结果，UNVERIFIED
3. iOS 27 Siri/记忆前瞻（单一媒体）
4. MemoryVault CMEK 等定价推测（dim07 自标高但实际为二手汇总）
5. 华为"可信联接"端侧记忆加密服务（厂商营销口径）

### 组件 4：内存管理（dim10-12）

**High Confidence**
1. PowerInfer-2：首个手机跑 47B、11.68 tok/s（arXiv 2406.06282 摘要确认；dim02/dim11 一致；加速比版本口径见 C4）【已核实】
2. LLM in a flash：4–5×（SSD）/20–25×（RAM）、2× DRAM 模型可跑（Apple 论文 + 多源确认；dim02/dim11 一致）【已核实】
3. DMEM cgroup 合入 Linux 6.14（2025-03），接口 dmem.current/max/min/low，xe 首发、amdgpu 6.15 跟进（lkddb + 多源确认；dim10/dim12 一致）【已核实】
4. **dma-buf memcg 记账截至 2026-10 仍是 RFC v2、未合主线**（lore/kernsec RFC 原文确认；dim12 正确）【已核实——并推翻 dim10 错误论断，见 C2】
5. Pre-gated MoE：峰值显存 -4.2×、仅 +23% vs oracle（arXiv 2308.12066 原文确认）【已核实】
6. MoE 专家可预测性证据链：Fate 免训练 78.79%/命中 99.08%；ProMoE 84.7% vs token-based 58.3%；同层 pre-attention 93.03–97.62%（多篇 arXiv 原文交叉一致；dim12 准确）
7. accel 子系统上游门槛 GEM/BO + TTM + drm_sched（邮件列表原文，dim12 引准确）
8. Android 17 MemoryLimiter：per-app cgroup v2 限额、写 memory.high/memory.swap.max、超限终止（AOSP 源码级核验的多个独立来源确认；dim10 主论断正确）【已核实——但 dim10 的"memory.pressure_level 控制点"未获证实，见 C10】
9. iOS 端侧推理受 jetsam/内存上限约束、Android 无 per-app KV/权重管理（dim10/dim11 结论一致）

**Medium Confidence**
1. MGLRU 量化数字（Pixel 6 app 启动 -6.6%、CPU -9.4%、杀进程减少；LPC 2024 "85% 低内存杀减少"）——来源链（LWN/Google slides）存在，**本轮 3 次定向搜索未能直接复核数字，PARTIAL**
2. HarmonyOS 超空间内存压缩"1.5GB/20%"（媒体口径，mydrivers 系可查到 1.5GB 类似表述但属软文）【部分核实，置信度维持中低】
3. ANE ~32MB SRAM 预算、~19 TFLOPS 实测（arXiv 2603.06728 存在确认；**但原始数据来自 maderix 单源逆向，非 Apple 官方——dim01 标"官方/高置信"应降级**）【已核实+降级】
4. vLLM PagedAttention 浪费 60–80%→<4%（SOSP 2023 单一论文）
5. NeuMMU 95%→0.06% 开销（2019 奠基单论文）；sNPU/NXT/vNPU 开销数据（各单论文）
6. NPUMoE（arXiv 2604.18788 存在确认，1.32–5.55× 延迟准确）；WiSP（arXiv 2606.21868 存在确认，1.95×/缓存>预测 论断准确）【已核实】
7. NVIDIA MPS v3 用 dmem 后端（NVIDIA 官方文档）

**Low Confidence**
1. **dim09 "FP16 KV 每 token ≈0.5MB（Llama-3-8B 级）"——模型标注错误：0.5MB/token 对应 MHA 7B 级（如 Llama-2-7B，2×32×32×128×2B）；Llama-3-8B 为 GQA（8 KV head）≈0.125MB/token。dim10 "0.5–1MB/token" 同样未限定模型【标记 MISQUOTED】**
2. dim10 "lmkd 新增 memory.pressure_level 控制点（Android 17）"——已核实来源均显示 MemoryLimiter 用 memory.high/swap.max，无 memory.pressure_level 证据【UNVERIFIED，疑似错误】
3. CVE-2026-1104 NPU 多租户侧信道（techbytes 媒体分析，无学术原文）
4. ANE IOSurface pin 上限 8–12 buffer（mvpfactory 单一博客）
5. vChunk <1% 干扰（emergentmind 二手综述）


---

## 二、Conflict Zone 完整清单与裁决结果

### C1. Apple AFM LoRA：rank-16/"数十 MB" vs rank-32/~160MB
- 甲方：dim01（[来源] Apple 2024 技术报告 arXiv 2407.21075：rank-16 adapter 通常数十 MB）；dim03 同引。
- 乙方：dim02（"Apple AFM ≈3B 2-bit QAT + rank-32 LoRA adapter，每个 ~160MB"，来源 gamut.so / 逆向分析）；dim03 另处并列引用 rank32≈160MB。
- 裁决（2 次定向搜索，已裁决，降级为口径差异）：**两者皆真、指代不同**。Apple 官方 2024 报告（accuracy-recovery/功能 adapter）= rank-16、10s of MB；出货模型 AFMTextV7 逆向 + WWDC25 开发者 adapter 训练工具包 = rank-32、~160MB `.fmadapter`。最终报告须按"2024 官方报告口径"与"2025 出货/工具包口径"分别标注，不得混写为单一数字。

### C2. dma-buf memcg 记账的主线合入状态（本轮最重要裁决）
- 甲方：dim10："dmabuf memcg 记账 2023-01 补丁系列 → **上游 6.5 合入（2023-08）**【事实；置信度中高】"。
- 乙方：dim12："dma-buf memcg 记账 2022 起多轮 RFC；2026-05 RFC；2026-10 RFC v2（8 补丁）……**仍处 RFC，未合主线**"。
- 裁决（2 次定向搜索，已裁决）：**dim12 正确，dim10 错引**。2026-05 RFC（kernsec.org 原文）明确 "builds on T.J. Mercier's earlier series"，基础记账补丁仍在 RFC 序列中；2026-10 有 RFC v2。主线 `memory.stat` 无 dmabuf 键。cgroup-v2.rst 的 dmabuf 条目是该 RFC 新增、尚未入主线。dim10 所述功能实际以 **Android GKI 下游补丁**形式存在，被误述为"上游 6.5 合入"。**最终报告采用 dim12 口径；引用 dim10 该处须删除或改写为"Android 下游携带、主线未合入"。**

### C3. NVIDIA OpenShell 发布时间
- 甲方：dim03："GTC 2026-03-16：NVIDIA 发布 NemoClaw + OpenShell（隐私路由器）"（来源 techjacksolutions 2026-03-19）。
- 乙方：dim04："OpenShell 2026-09-28 发布"（Wikipedia）；dim05："2026-09 v0.1.0 / 2026-10-21 GTC Berlin 参考架构"。
- 裁决（1 次定向搜索，已裁决，降级为时间口径不一致）：**三个事件并存**：2026-03 GTC NemoClaw 栈（含 OpenShell 组件的早期出现）；2026-09-28 Open Agent Safety Platform（OpenShell+Sentry）正式发布；2026-10-21 GTC Berlin OpenShell Reference Architecture。GitHub issue 记录显示 OpenShell 仓库 2026-06 已活跃，佐证软件早于 9 月平台发布。最终报告建议写"2026-03 随 NemoClaw 首次亮相、2026-09-28 作为 Open Agent Safety Platform 正式发布"。

### C4. PowerInfer-2 加速比 29.2× vs 27.8×
- 甲方：dim02 "29.2×"；dim11 §2.2 同。
- 乙方：dim11 脚注/数据点"v1 abstract 29.2×、v2 27.8×"。
- 裁决（1 次搜索，已裁决）：**arXiv 2406.06282 v1=29.2×，v2 摘要=27.8×**（ADS 记录确认）。版本口径差异；建议引 v2 27.8× 或注明版本。

### C5. NPU vs CPU 性能倍数：100× / 25× / 12×
- dim01 同文内两口径：LiteRT 官方"NPU 最高 100× CPU、10× GPU" vs SegmentFault 转述 I/O 2025"25× CPU、功耗 1/5"；外部另有 MWC 2026 实测"Gemma-3n 在 D9500 上 NPU 12× CPU"。
- 裁决（1 次搜索，不可裁决为单一数字）：**领域内口径混乱**——理论峰值（100×）、发布会营销（25×）、特定模型实测（12×）并存。最终报告引用时必须带场景限定语，不得单独写"NPU 比 CPU 快 N 倍"。

### C6. AgentDojo 无攻击效用 "<66%" vs "GPT-4o 69%"
- dim06 同句内并列"<66%（GPT-4o 69%）"，自相矛盾。
- 裁决（1 次搜索，已裁决）：论文 abstract 口径 "less than 66%"（2024-06 时点主流模型聚合）；GPT-4o benign utility 69.0% 出自论文 Table/官方 leaderboard。**两个数字都真实但口径不同**；最终报告建议写"发布时 aggregate <66%，最佳单模型（GPT-4o）benign utility 69%"。

### C7. EdgeLoRA adapter 容量 "1000+ vs llama.cpp ~50"
- dim01 与 dim03 均写"1000+ adapter vs llama.cpp 上限约 50"。
- 裁决（2 次搜索，部分裁决）：论文存在且"4× 吞吐、数量级更多 adapter"已确认；**"1000+/50" 具体数字未在可检索摘录中直接复核**（论文原文称 "several orders of magnitude more"）。标注 PARTIAL；建议最终报告用"数量级更多（论文口径）"或引论文图注。

### C8. Mem0 vs Zep 的 LoCoMo/LongMemEval 分数战
- dim07 详述（Mem0 91.6 vs Zep 80.32、复现争议等）；dim09 引 Mem0 "+26% over OpenAI"。两报告不冲突，但底层是厂商互斥声明。
- 裁决：**领域内真实分歧**（benchmark 方法论战，2026 年仍未解），非报告错误。最终报告必须双方并引并加"厂商自报/复现争议"限定。

### C9. FastVLM 芯片代际
- dim01/dim02："骁龙 8 Elite"；InfoQ 2025-11 原文："Snapdragon 8 Elite Gen 5"。
- 裁决（已裁决）：报告芯片名少写一代，数字本身准确。小笔误，建议更正为 8 Elite Gen 5。

### C10.（附加发现的报告内错误，非跨报告冲突但须标记）
- dim09 "KV 每 token 0.5MB（Llama-3-8B）"：模型标注错误（0.5MB 对应 MHA 7B；Llama-3-8B GQA ≈0.125MB）——MISQUOTED。
- dim10 "memory.pressure_level（Android 17 新控制点）"：与已核实的 MemoryLimiter 实现（memory.high/swap.max）不符——UNVERIFIED，疑错。
- dim01 ANE "~32MB SRAM" 标"官方/高"：实为单源逆向（maderix）——置信度标注错误，应降 Medium。
- dim08 GroupMemBench 正文 arXiv 号 2605.14493 vs 脚注 2605.14498：后者正确，正文笔误。

---

## 三、关键数据抽查结果汇总

| 组件 | 抽查论断 | 结果 |
|---|---|---|
| 1 | AFM rank-16/数十MB（2407.21075） | ✔ 核实（官方原文一致） |
| 1 | AFM rank-32/160MB（出货/工具包） | ✔ 核实（第三方逆向+gamut 一致；非官方文档） |
| 1 | S-LoRA 2000 adapter/4×/30×；Punica 12×/+2ms | ✔ 核实（多源） |
| 1 | LiteRT Gemma-3n D9500 1600/28 tok/s | ✔ 核实（厂商基准，≥2 二手确认） |
| 1 | FastVLM-0.5B 0.12s/11000 tok/s | ✔ 核实（芯片代际标注需更正） |
| 1 | EdgeLoRA 4×/1000+ adapter | ◐ 4× 与论文存在性核实；1000+/50 未直接复核 |
| 1 | NNAPI deprecated（Android 15） | ✔ 核实 |
| 2 | Firecracker ≤125ms/<5MiB/150/s | ✔ 核实（NSDI'20+多源） |
| 2 | K8s agent-sandbox 四 CRD | ✔ 核实（官方+≥5 独立源） |
| 2 | AgentDojo <66%/<25%/8% | ✔ 核实（原文一致；69% 口径另注） |
| 2 | AgentCore Policy Cedar GA 2026-03-03 | ✔ 核实（≥2 独立源） |
| 2 | Attacker Moves Second >90% ASR/USENIX Sec 2026 | ✔ 核实（引用链确认收录） |
| 2 | OpenShell 时间线 | ✔ 裁决（三事件并存） |
| 2 | MCP registry 47,879 | ✘ 未能复核（单媒体） |
| 3 | Mem0 66.9 vs 72.9 / p95 1.44s | ✔ 核实 |
| 3 | Zep DMR 94.8 vs 93.4 / +18.5pt | ✔ 核实（arXiv 摘要原文） |
| 3 | LongMemEval-V2 451 题/72.5% | ✔ 核实 |
| 3 | GroupMemBench 46.0% | ✔ 核实（+dim08 编号笔误） |
| 3 | Memora/FAMA（2604.20006） | ◐ 论文存在核实；具体数字未逐项核 |
| 3 | **AMemBench（2609.13767，76.83%）** | **✘ 搜索零结果——HALLUCINATED-SUSPECT** |
| 3 | OSDN（2607.05475） | ✘ 搜索零结果——UNVERIFIED |
| 4 | PowerInfer-2 47B/11.68 tok/s | ✔ 核实（29.2×/27.8× 版本口径已裁决） |
| 4 | DMEM cgroup Linux 6.14 | ✔ 核实（lkddb+多源） |
| 4 | dmabuf memcg 主线状态 | ✔ dim12 核实 / **dim10 "6.5 合入"证伪** |
| 4 | Pre-gated MoE 4.2×/+23% | ✔ 核实 |
| 4 | H2O 29×；SnapKV 3.6×/8.2×/380K；Mooncake 525%/75% | ✔ 全部核实（论文原文一致） |
| 4 | ANE 32MB SRAM（2603.06728） | ◐ 论文存在；数据系单源逆向，置信度应降级 |
| 4 | Android 17 MemoryLimiter | ✔ 核实（但 memory.pressure_level 未证实） |
| 4 | MGLRU Pixel 6/LPC 2024 数字 | ◐ PARTIAL（来源链存在，3 次搜索未直接复核数字） |
| 4 | MoE 预测命中率链（Fate/ProMoE/pre-attention） | ✔ 核实（arXiv 原文交叉一致） |

**虚构/错引结论**：未发现整篇虚构来源；发现 1 个疑似虚构（AMemBench）、1 个证伪错引（dim10 dmabuf memcg 合入状态）、1 个模型标注错引（dim09 KV 0.5MB）、若干置信度标注过高（ANE SRAM、端侧软文数字）。


---

## 四、覆盖缺口清单（对照四组件核心问题清单）

### dim01-03（推理框架：系统级模型服务/NPU/框架/加速/端云路由/LoRA）
1. **HarmonyOS 端侧推理栈硬核数据缺失**：盘古 6.0/麒麟 NPU/MindSpore 侧只有软文口径，无论文/文档级来源——dim01 已自标低置信，属真实缺口。
2. **NPU 侧 KV cache / 运行时内存管理**：dim02 自认空白（NPU delegate 内部不可见），无报告覆盖。
3. **端云路由的实测延迟/成本数字**：dim03 有架构无实测；路由决策的可观测数据（各 OS 实际命中率/时延）全行业未公开。
4. **Windows Foundry Local 内部机制**：微软未公开，仅外部描述。
5. 量化在 NPU 上的精度-性能实测矩阵（各家 QAT 方案横评）无系统来源。

### dim04-06（沙箱：厂商/策略凭证接口/安全端侧）
1. **端侧（iOS/Android）agent 沙箱产品**为全行业空白（dim04/dim06 共同结论，是发现而非遗漏；但"移动端本地执行不可信代码的过渡方案"无调研）。
2. **沙箱的内存/资源 QoS 与组件 4 的交叉**（cgroup/dmem 限额如何应用于 agent sandbox）无人覆盖——跨组件盲区。
3. 凭证注入的实际安全事故数据（仅 Asana/Supabase 个案），缺系统性统计。
4. Apple 端侧安全机制（MIE/Exclaves 与 agent 的关系）仅 dim06 浅提。

### dim07-09（记忆：格局/评测/端侧索引/隐私/压缩遗忘/推理耦合）
1. **程序性记忆（procedural/skill）基准与系统极少**（dim08 已指出），且 2026 新基准（GroupMemBench 等）缺第三方复现。
2. **端侧记忆与 OS 权限/沙箱模型的结合**（记忆读写的 capability 控制）仅 dim08 部分覆盖。
3. 记忆隐私的学术来源薄弱（多为政策文本/厂商口径），缺测量型研究。
4. 端侧"记忆 × KV 复用"统一框架：dim09 承认服务端有（Mooncake/MemServe），端侧为空白点。

### dim10-12（内存管理：移动端/QoS/KV/权重分页/MoE/NPU 抽象）
1. **iOS jetsam 量化细节弱**（dim10 自认），无 Apple 官方预算表。
2. **移动 SoC 统一内存（dmabuf/AHardwareBuffer/IOSurface）的 cgroup 记账**：主线未合入（C2 裁决），属于"无现成方案"的真实空白。
3. **移动端 QoS 语义（memory.min/low 式保护）无先例**——dim10/11 均承认为空白。
4. **Windows/macOS 桌面端内存管理对照缺失**：dim10-12 只覆盖 Android/Linux/iOS 浅层。
5. NPU 侧信道测量缺学术工作（dim12 指出）。

### 跨组件共性缺口
- **没有报告覆盖"沙箱 × 内存限额"联合设计**（组件 2 与 4 的接缝）。
- **HarmonyOS 全栈（沙箱/记忆/内存）几乎无技术级来源**，只有 dim01/07/10 的媒体级碎片。
- 2026 年下半年的大量论断依赖媒体/博客；学术级佐证集中在 2024-2025 工作。

---

## 五、对最终报告的写作建议

**可直接引用（High Confidence，已核实）**：
- 推理框架：AFM 双口径 LoRA 数字（须分开标注 2024 报告 vs 2025 工具包）、S-LoRA/Punica 数字、NNAPI deprecated、LiteRT D9500 基准（注明厂商口径）、HarmonyOS 36.8 亿次/日。
- 沙箱：Firecracker 三数字、agent-sandbox 四 CRD、AgentDojo 三数字（69% 口径另注）、AgentCore Policy GA 日期、Attacker Moves Second 结论。
- 记忆：Mem0/Zep/LongMemEval-V2/GroupMemBench 全部数字；SnapKV/H2O/Mooncake 全部数字。
- 内存管理：PowerInfer-2 11.68 tok/s（加速比引 v2 27.8×）、LLM in a flash 数字、DMEM cgroup 6.14、**dmabuf memcg 未合主线（采用 dim12 口径）**、Pre-gated MoE 4.2×、MoE 预测命中率链、Android 17 MemoryLimiter。

**必须加限定语**：
- 所有 NPU 性能倍数（100×/25×/12×）——注明"理论峰值/营销口径/特定模型实测"。
- ANE 32MB SRAM、19 TFLOPS——注明"单源逆向工程，非 Apple 官方"。
- FastVLM 数字——更正芯片为 Snapdragon 8 Elite Gen 5。
- EdgeLoRA adapter 数量——用"数量级更多"或引论文图注，勿写死 1000+/50。
- MGLRU 数字——注明来源为 Google LPC slides，本轮未独立复核。
- Mem0 vs Zep 所有对比分数——加"厂商自报/存在复现争议"。
- OpenShell——采用双日期表述（2026-03 初亮相 / 2026-09-28 平台发布）。
- 端侧各家（ANE 上限、iOS 27、HarmonyOS 细节）——注明媒体/推测口径。

**禁止直接引用（需删除或改写）**：
- dim10 "dmabuf memcg 上游 6.5 合入"——证伪，改为"Android GKI 下游携带，主线截至 2026-10 仍为 RFC v2"。
- dim09 "KV 每 token 0.5MB（Llama-3-8B）"——改为 MHA 7B 级口径或给出 GQA 修正值 ~0.125MB。
- dim10 "memory.pressure_level"——无证据，删除或改为 memory.high/swap.max。
- dim07 AMemBench（76.83%）、OSDN（2607.05475）——未核实，删除或标"待核实"。
- Nova-Specialist OSWorld +9.7pt——维持 dim06 自带的"低/未核"标注。

**统计**：High 28 项 / Medium 35 项 / Low 14 项 / Conflict Zone 10 项（含 4 项报告内错误标记）。

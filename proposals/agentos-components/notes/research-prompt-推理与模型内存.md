# 调研提示词：推理服务与推理服务内存管理（第二轮重构）

> 日期：2026-11-09
> 用途：同一份提示词既给子 Agent 用，也可以直接提交给其他模型。完整模式做全部模块；单模块模式只做指定的 R 编号。

## 背景

我们在写一份 30 分钟的领导汇报，主题是 Agent OS 的系统服务。2026-11-09 起结构调整为三项系统服务：推理服务、执行与沙箱、内存与资源（通用内存管理加推理服务内存管理）；记忆移到 Agent 层。汇报的逻辑链是「复杂场景与负载 → 用户体验与商业化问题 → 技术瓶颈 → 关键技术」。推理与模型内存两块的关键技术调整为：

**推理服务的优化**（会话级调度由其他团队负责，不作为我们的关键技术）：

1. Agent 超长序列推理的优化
2. LPDDR-PIM、NPU、UFS-PIM 异构融合计算（PIM 已列入自研芯片规划）
3. 硬件亲和的模型架构寻优

**推理服务内存管理**（2027 年确定上 MoE 底座）：

1. KV Cache 生命周期管理与前缀缓存命中率提升
2. KV Cache 分页与冷热分层管理
3. 模型加载 IO 零拷贝优化
4. MoE 专家命中率提升

## 参考负载（已有估算，调研结论要能接上这些数字）

- 基线稠密底座约 3B、4-bit，权重 1.7GB；decode 单流约 52 token/秒 × 约 1GB 活跃权重 ≈ 52GB/s 的 LPDDR 读带宽（估算）。
- 长程任务（T3）上下文 23–32K；24K 时 KV 约 820MiB，32K 约 1.07GiB；端侧接口窗口约 4K（Android Prompt API）和 8K（Apple 示例）。
- 端侧 prefill 实测 557–3808 token/秒；23K 上下文 prefill 约 6 秒。KV 丢失后重建 6–14 秒，换入恢复 0.2–0.9 秒。
- 12GB 机型，Agent 侧可用约 4GB；UFS 4.x 顺序读约 4.3GB/s；LPDDR5X 理论峰值约 77GB/s（64-bit、9600MT/s）。
- MoE：30B 级 A3B 模型命中率为 0% 时每 token 约 1.1GB IO（估算）；iPhone 上 Qwen3.6-35B-A3B 实测 512MiB 时 LRU 命中率 0%、576MiB 时 38.58%（预印本）。

## 通用要求

1. **先读本地已有材料**（每个模块列出），只补缺口，不重复已有结论；与已有材料冲突时明确指出。
2. **预算**：WebFetch 不超过 10 次，WebSearch 不超过 4 次。优先抓取下面列出的已知链接。
3. **口径标注**：每个数字写明测试条件（硬件、模型、上下文长度、精度），并标注等级：官方 / 论文同行评审 / 预印本 / 厂商自报 / 二手 / 估算。查不到的写「待核实」，不要编造版本号、链接或数字。
4. **时间**：今天是 2026-11-09，优先 2025–2026 年的资料。
5. **用中文写**，术语保留英文原名；区分 Android、iOS、HarmonyOS 的术语。
6. **只写自己的输出文件**，不要修改仓库里的其他文件。

## 输出格式（每个模块一个文件）

```
# R<编号> <模块名>
## 1. 结论摘要（不超过 8 条，每条一句话，带数字）
## 2. 证据表（指标 | 数值 | 条件 | 来源链接 | 等级）
## 3. 对关键技术的建议
   - 对应的负载与瓶颈（接上「参考负载」里的数字）
   - 问题与挑战（3–4 条）
   - 量化目标建议值（指标 | 建议值 | 依据）
   - 模块级方案（3–5 条）
   - 细节技术点（3–4 条）
## 4. 原型对比表素材（列 = 学术原型或业界产品，行 = 该技术的关键要素；格子写达成情况，用 ● ◐ ○ 表示）
## 5. 与其他模块的边界（哪些内容应归推理，哪些归内存管理）
## 6. 待核实
## 参考文献（编号 + 标题 + 链接 + 日期）
```

完成后回复不超过 200 字：最重要的 3–5 个发现，以及输出文件路径。

---

## R1 Agent 超长序列推理

**输出**：`proposals/agentos-components/notes/R1-超长序列推理.md`

**先读**：`advanced/A16f-端侧KV-Cache管理方案.md`、`insight/N+1/on-device-kv-cache-management/on-device-kv-cache-management-CN.md`、`proposals/2027-agentos-ai-graphics/notes/M3-model-memory.md`（KV 部分）。

**问题**：

1. 2025–2026 旗舰手机上长上下文 prefill 的最好成绩：8K、16K、32K 下的 token/秒，以及随长度下降的幅度（NPU、GPU 分别）。
2. 长上下文 decode：KV 读取在每 token 访存中的占比；端侧可用的稀疏注意力与 KV 选择方法（Quest、InfLLM v2、NSA、DeepSeek DSA、SnapKV、KVSwap 等）的端侧证据和对 Agent 任务质量的影响。只看推理侧能做的，不讨论改模型结构（那是 R4）。
3. Agent 上下文的构成：工具返回、多轮历史、系统提示各占多少；上下文压缩、裁剪、观察结果遮蔽这类方法能裁掉多少而不掉质量。
4. 有没有面向 Agent 长序列的端侧系统工作（分块 prefill、prefill 与 decode 分离到不同硬件、增量 prefill）。

**已知链接**：
- MiniCPM4（InfLLM v2）：https://arxiv.org/abs/2506.07900
- NSA：https://arxiv.org/abs/2502.11089
- Quest：https://arxiv.org/abs/2406.10774
- llm.npu：https://arxiv.org/abs/2407.05858
- HeteroLLM：https://arxiv.org/abs/2501.14794
- KVSwap：https://arxiv.org/abs/2511.11907

## R2 SoC 内异构协同与 LPDDR-PIM

**输出**：`proposals/agentos-components/notes/R2-异构融合-SoC与LPDDR-PIM.md`

**先读**：`insight/N+2/lpddr-pim-architecture/lpddr-pim-architecture-CN.md`、`advanced/A16g-DRAM-PIM异构协同管理.md`、`advanced/A15-前沿-先进内存.md` 的 §3.4、`insight/N+3/lpddr6-standard-evolution/lpddr6-standard-evolution-CN.md`、`proposals/agentos-components/notes/C1b-accel-routing-adapter.md`。

**问题**：

1. 手机 SoC 内 NPU、GPU、CPU 协同推理的现状与收益（HeteroLLM、llm.npu、Agent.xpu、PowerInfer-2，以及高通、联发科官方方案），以及缺什么（统一内存共享、同步开销、NPU 与 GPU 之间的零拷贝）。
2. LPDDR-PIM 截至 2026-11 的进展：JEDEC LPDDR6-PIM 标准状态（2026-04 曾预告）、三星与 SK 海力士的移动端 PIM 产品公告、手机 SoC 厂商的公开表态。
3. LPDDR-PIM 的系统软件问题：数据放置、PIM 与普通访存的模式切换、一致性、编程模型（LP-Spec、CD-PIM、PIM-SHERPA）；OS 与运行时要提供什么；对 3–7B decode 的量化收益。
4. PIM 与长上下文注意力、MoE 专家计算的结合（例如 AttAcc 一类把注意力放到 PIM 的工作，以及 MoE 放到 PIM 的工作）。

**已知链接**：
- LP-Spec：https://arxiv.org/abs/2508.07227
- CD-PIM：https://arxiv.org/abs/2601.12298
- PIM-SHERPA：https://arxiv.org/abs/2603.09216
- JEDEC LPDDR6 PIM 预告：https://www.jedec.org/news/pressreleases/jedec%C2%AE-previews-lpddr6-roadmap-expanding-lpddr-data-centers-and-processing-memory
- HeteroLLM：https://arxiv.org/abs/2501.14794

## R3 闪存侧计算（UFS-PIM、闪存内计算）

**输出**：`proposals/agentos-components/notes/R3-异构融合-闪存侧计算.md`

**先读**：`insight/N+3/ufs5-computational-storage/ufs5-computational-storage-CN.md`、`surveys/ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md`、`advanced/A16i-端侧UFS-HBF增强.md`、`advanced/A15-前沿-先进内存.md`（搜索 AiF）。

**问题**：

1. 面向 LLM 的闪存内、存储内计算研究：卸载了哪些算子（冷权重的 GEMV、闪存中 KV 的注意力计算等），收益与代价。候选：AiF（闪存内处理加速端侧 LLM）、Cambricon-LLM、InstInfer，以及其他 2025–2026 工作。
2. 厂商动向：三星、SK 海力士、铠侠、SanDisk、长江存储在移动端存储计算方向的公开信息；UFS 5.0 是否有相关特性；JEDEC 是否有标准化动作。
3. 与 MoE 专家卸载的关系：冷专家在闪存内计算，与搬到 DRAM 计算相比，每 token IO 与能耗的盈亏点。
4. 系统软件要求：接口（UFS 命令扩展）、数据布局、与前台 IO 的调度、写寿命。

**已知链接**：
- Cambricon-LLM：https://arxiv.org/abs/2409.15654
- InstInfer：https://arxiv.org/abs/2409.04992
- AiF：先在 A15 中找出处，没有再搜索

## R4 硬件亲和的模型架构寻优

**输出**：`proposals/agentos-components/notes/R4-硬件亲和模型结构.md`

**先读**：`proposals/2027-agentos-ai-graphics/notes/D2-foundation-evolution.md`、`proposals/2027-agentos-ai-graphics/notes/M3-model-memory.md`、`proposals/agentos-components/report/2-场景与负载瓶颈.md` 的 2.2.5（KV 体积随模型变化 14 倍的出处）。

**问题**：

1. 端侧模型结构寻优的方法与案例：MobileLLM 与 MobileLLM-R1、PhoneLM、LFM2（硬件在环搜索）、Jet-Nemotron（PostNAS）等；优化目标是什么（目标硬件时延、内存、能耗），效果如何。
2. 内存与闪存亲和的结构设计：Gemma 3n（PLE 放闪存、MatFormer、KV 共享）、AFM 2025（KV 共享省 37.5%）、AFM 3 Core Advanced（稀疏、每请求选专家）、SmallThinker（注意力前路由以便预取）、MiniCPM4、混合线性注意力（Qwen3-Next、Kimi Linear）。
3. 候选端侧模型的 KV 体积对比表：层数、KV 头数、头维度、滑动窗口比例、每 token KV 字节（fp16 与 int8），覆盖 3–4B 稠密模型与 A3B 级 MoE。
4. 系统团队能向模型团队提供的约束与评估工具：硬件在环时延预测、带宽与闪存代价模型；业界有没有公开的协同流程（Apple、Google、Meta）。

**已知链接**：
- MobileLLM：https://arxiv.org/abs/2402.14905
- PhoneLM：https://arxiv.org/abs/2411.05046
- Jet-Nemotron：https://arxiv.org/abs/2508.15884
- SmallThinker：https://arxiv.org/abs/2507.20984
- LFM2：先搜索官方技术报告

## R5 端侧 MoE 底座、专家命中率与前缀缓存生命周期

**输出**：`proposals/agentos-components/notes/R5-MoE与前缀缓存.md`

**先读**：`proposals/2027-agentos-ai-graphics/notes/M3-model-memory.md`、`proposals/agentos-components/notes/C4b-model-memory.md`、`insight/N+1/on-device-agent-memory-system/prefix-cache-agent-notes.md`、`proposals/agentos-components/report/3-内存管理.md` 的 3.4。

**问题**：

1. 2027 年端侧 MoE 底座的候选与内存账：AFM 3 Core Advanced、Qwen3 / Qwen3.6 A3B、SmallThinker 4B-A0.6B 与 21B-A3B 等；总参数、激活参数、专家数与单个专家大小；不同命中率下每 token 的闪存 IO；哪些放得进 12GB、16GB 手机。
2. 专家命中率与预取的 2025–2026 最新数据：FlashMoE、ProMoE、HOBBIT、AdapMoE 等，以及每请求选专家的做法；Agent 任务切换对路由分布的影响。
3. 前缀缓存与 KV 生命周期：Agent 场景的前缀命中率数据（仓库已引用 arXiv 2605.26297）；端侧框架对前缀缓存的支持（llama.cpp、MLC、MNN、Apple Foundation Models 的 prewarm、Android 的 Prompt API）；版本变化时的失效；前缀缓存的时序侧信道攻击（如 InputSnatch、Auditing Prompt Caching）。
4. MoE 专家缓存与 KV 共用 DRAM 预算时怎么划分；有没有相关工作。

另外在第 3 节之前加一节「MoE 底座的负载参数建议」：给出 2027 年 MoE 底座的建议配置（总参数、激活参数、专家数、单专家大小、DRAM 驻留量、闪存占用），供第二部分负载页使用，标明是估算。

**已知链接**：
- Auditing Prompt Caching：https://arxiv.org/abs/2502.07776
- SmallThinker：https://arxiv.org/abs/2507.20984
- 2605.26297：先在仓库里找到完整链接

## R6 推理需求、云端成本与云转端

**输出**：`proposals/agentos-components/notes/R6-推理成本与云转端.md`

**先读**：`proposals/2027-agentos-ai-graphics/notes/M4-simulation-eval.md`（云转端部分）、`proposals/2027-agentos-ai-graphics/notes/M1-agentos-commercial.md`、`proposals/agentos-components/report/2-场景与负载瓶颈.md` 的 2.2.2（每天的 prefill 与 decode 量）。

**这个模块不写关键技术**，用来支撑汇报中「推理的用户体验与商业化问题」一页：推理需求在爆发，云端总成本很高，很多公司在评估云转端的可行性与风险，核心矛盾是成本与体验的取舍。

**问题**：

1. 推理需求的增长：2025–2026 年公开的 token 调用量（Google 每月处理的 token、字节豆包日均 token、阿里云、OpenRouter 等）；Agent 任务相对普通对话的 token 倍数。
2. 云端成本：单价在降、总支出在升的证据；手机助手或终端厂商的云成本压力（如三星 Galaxy AI 收费口径、Apple PCC、国内厂商）；Agent 单用户的云成本估算。
3. 云转端的业界动作与理由：Apple、Google（Gemini Nano、PREFER_ON_DEVICE）、高通混合 AI 白皮书的成本论证、三星、vivo、荣耀、小米；有没有公开的「端侧承接比例」。
4. 云转端的风险与体验代价：质量差距、首 token 与 decode 速度、功耗与发热（M4 已有「端侧每 token 能效比服务器差约 3 倍」）、内存挤压前台应用。

**输出格式调整**：第 3 节改为「单用户成本估算」：用参考负载每天的 prefill 与 decode 量，按 2–3 档公开云价算出每用户每天、每年的云成本，以及按 1000 万日活折算的年成本，写明全部假设。第 4 节改为「云转端的收益与风险表」（维度 | 收益 | 风险 | 依据）。

**已知链接**：
- Anthropic 多 Agent 研究系统（token 倍数）：https://www.anthropic.com/engineering/multi-agent-research-system
- 高通混合 AI 白皮书：先搜索官方 PDF

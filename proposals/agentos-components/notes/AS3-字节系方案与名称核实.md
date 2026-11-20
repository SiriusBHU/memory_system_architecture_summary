# AS3 字节跳动相关方案与 AgentEnv / DSec 名称核实

> 日期：2026-11-15。抓取版本：UI-TARS-2 arXiv 2509.02544（html 版）；DSec arXiv 2609.22978（2026-09-19 提交，html 版）；agent-infra/sandbox README（最新 release v1.11.0，2026-06-23）；kvcache-ai/AgentENV README（main，仓库创建 2026-07-23，2026-11-16 仍有提交，约 3752 star）；bytedance/SandboxFusion README；volcengine/verl README。
> 检索实际用量：WebFetch 3 / WebSearch 4 / 源码与论文文件 12 / api.github.com 6（超出 5 次预算 1 次，仅为元数据查询）。
> 商业信息（时间线、封禁、销量）见 `../../2027-agentos-ai-graphics/notes/D1-commercial-deep-dive.md` §5，本文不重复。

## 结论

1. **AgentEnv 与 DSec 都不是字节的。** DSec 是 DeepSeek 的 Elastic Compute（论文，作者署 DeepSeek 团队，等级：论文）；AgentENV（AENV）是月之暗面 Kimi 与 kvcache-ai（清华 KVCache 团队）的开源平台，MIT 协议，服务 Kimi K3（README，厂商自报）。全文检索 DSec 论文无任何 ByteDance / 火山 字样（grep 0 命中，论文）。
2. **字节自己的对应物是 UI-TARS-2 的「all-in-one GUI sandbox」**：云 VM 集群「数千实例」，VM Manager 吞吐「数千 QPS」，支持 Windows / Ubuntu / Android，接口含 PyAutoGUI 与 ADB（论文）。但报告没给安卓实例形态（模拟器、容器还是云手机）、重置方式、单步时延。
3. **DSec 明确支持安卓，但走全 VM 后端**：「Android VMs through QEMU」，属 Full VM 后端；论文的性能测量只覆盖容器和 microVM，不含安卓（论文）。生产规模：单个 scale unit 约 160 节点，日均约 300 万沙箱，峰值并发超 38 万，创建速率超 5000/s，单节点最多 800 个 microVM 或 3200 个容器（论文）。
4. **AENV 无安卓 / GUI 支持的公开说明**：README 中 android / gui / mobile 关键词 0 命中；形态是 Firecracker microVM，要求内核 6.8+ 与 /dev/kvm；快照恢复 <50 ms、暂停 <100 ms、内存超分 9.6x（均为厂商自报，条件未给）。
5. **字节通用沙箱均无安卓**：AIO Sandbox（agent-infra/sandbox，Docker 一体化：浏览器、终端、文件、VSCode、Jupyter、MCP）与 SandboxFusion（代码执行与 OJ）README 均无 android / adb；veRL 只给出 multi-turn 工具调用与 Sandbox Fusion 集成，无安卓环境示例（源码 README）。字节的安卓环境实际在**火山引擎云手机 + Mobile Use Agent（MUA）**，是商业云产品（官方文档目录，厂商自报）。
6. **豆包手机的「沙箱」基本不是隔离执行环境**：公开证据是系统级权限（INJECT_EVENTS）下的全局模拟点击；虚拟屏、权限隔离只见于二手分析文章，机制细节无可靠来源（待核实）。

## 1. AS3-Q1 豆包手机的端侧执行架构

| 条目 | 内容 | 等级 | 来源 |
|---|---|---|---|
| 操作别的应用的方式 | 豆包官方公告称依赖 Android 系统级权限 INJECT_EVENTS，拥有后才能跨屏、跨应用模拟点击，并称不存在「黑客行为」 | 厂商自报（经 IT之家转述，原页 403 未直接打开，来自搜索摘要） | [1] |
| 业界定性 | 「GUI Agent + 系统级权限」，读屏加模拟点击；需手机厂商授权并深度嵌入系统 | 二手 | [2][3] |
| 底层模型 | 有博客称用 UI-TARS 2.0 闭源版，仅一家博客说法 | 二手，待核实 | [4] |
| 虚拟屏 / 后台执行 | woshipm 分析文章提到「虚拟屏操作、权限隔离、用户可随时关闭、优先端侧计算」，同时说明实际效果取决于字节实现；无官方技术文档 | 二手，待核实 | [5] |
| 推理在云还是端、截图是否上传 | 本轮检索**未找到**可靠来源 | 待核实 | - |
| 二代架构 | 36Kr 称混合架构：MCP + A2A + GUI 读屏并行；LatePost 称新版不再读屏模拟点击、要求应用方提供 MCP（两种说法冲突，D1 已列为待核实） | 二手 | [6]；D1 §5 |
| 争议与限制 | 已在 D1 §5 记录（2025-12 首轮封禁、2026-10 SAEP 拒绝名单 150 余款应用） | 二手 | D1 |

**这说明什么（判断）**：豆包一代的「沙箱」是权限边界而非执行隔离：Agent 以系统权限在用户当前设备上直接操作真实应用，没有看到独立 VM 或独立用户空间。这与 OpenMinis、Napaxi 一类的端侧隔离是两条路线。后台虚拟屏是否真的用于执行，需要抓取官方文档或拆包确认，现有证据不足以下结论。

## 2. AS3-Q2 UI-TARS-2 的训练沙箱

UI-TARS-2（arXiv 2509.02544，论文）§2.2「All-in-One GUI Sandbox」要点：

| 项 | 报告原文要点 | 等级 |
|---|---|---|
| 形态 | 分布式 VM 平台，跑 Windows、Ubuntu 和 Android；集成 PyAutoGUI 与 ADB；统一 SDK 覆盖 VM 分配、初始化、交互、观测（截图、录屏）、任务评估 | 论文 |
| 规模 | VM 集群「数千实例」；VM Manager 持续吞吐「数千 QPS」；每个 session 用 session ID 绑定任务与环境 | 论文 |
| 生命周期 | 基于租约（lease）自动回收，超时 session 被回收；VNC / RTC 实时可视化 | 论文 |
| 混合环境 | 共享文件系统，GUI 下载的文件可被终端 / SDK 立刻使用；终端服务通过代理 URL 暴露 | 论文 |
| 游戏环境 | 浏览器沙箱，容器内多浏览器实例 + 弹性调度；崩溃自动恢复、页面级 checkpoint、空闲 session 垃圾回收 | 论文 |
| RL 框架 | 全异步服务式推理 + 状态化环境 + 部分填充的 rollout 池（streaming training），用于缓解长尾轨迹 | 论文 |
| 效果 | AndroidWorld 73.3（UI-TARS-1.5 为 64.6）；W4A8 量化把每轮交互端到端时延从 4.0 s 降到 2.5 s（模型推理，非环境） | 论文 |

**报告未写（均检索全文，待核实）**：安卓实例是模拟器、容器还是云手机；宿主架构；并发数中安卓占多少；重置与快照方式；环境单步时延；单实例资源。「数千实例」是整个 VM 平台合计，不是安卓数。

**这说明什么（判断）**：字节披露的是平台能力的量级，不是安卓环境的工程细节。想要安卓 rollout 的重置、密度数据，需要去看火山引擎云手机的产品文档或 AS4 / AS6 里的其他论文，UI-TARS-2 不能当作安卓沙箱性能的来源。

## 3. AS3-Q3 字节通用 Agent 沙箱与 RL 框架

| 项目 | 形态 | 安卓支持 | 关键事实 | 等级 | 来源 |
|---|---|---|---|---|---|
| AIO Sandbox（agent-infra/sandbox） | 单 Docker 容器：Browser（VNC）、Terminal、File、VSCode、Jupyter、MCP；需 `--security-opt seccomp=unconfined`；国内镜像在 volces.com；README 的 Paper 链接指向 UI-TARS-2 §2.2 | 无（README 无 android / adb） | v1.11.0，2026-06-23；字节 Web Infra 与 veFaaS 团队开源（二手） | 源码 README；二手 | [7][8] |
| SandboxFusion（bytedance/SandboxFusion） | 代码执行器 + OJ 评测集（HumanEval 等），Python、C++、Java 等多语言，含 CUDA | 无 | 用于代码 RL 评测 | 源码 README | [9] |
| veRL（volcengine/verl） | RL 训练框架；有 multi-turn tool calling、Sandbox Fusion 集成示例；2026-05 发布 uni-agent；社区列有 GUI-R1、VAGEN 等 | 框架本身无安卓环境；README 未见安卓示例 | 对沙箱是「客户端」对接关系 | 源码 README | [10] |
| 火山引擎云手机 + Mobile Use Agent（MUA） | 云端安卓实例（Pod）+ 豆包视觉模型，自然语言驱动；有 OpenAPI：截图（单张 / 批量）、录屏、文件推拉、命令执行、ADB 开关与隧道、实例重置 / 迁移；还有 Computer Use Agent（CUA，基于 ECS） | **有**（商业产品） | 实例规格、ARM 或 x86、容器或 VM 在文档目录里未展开，待核实；有 Agent 运行配置与安全策略章节 | 官方文档目录（厂商自报） | [11][12] |
| AgentKit（火山 / BytePlus） | Agent 运行时与部署平台；agentkit-samples 仓库里有 byted-acep-api 技能（用脚本调云手机 OpenAPI，截图优先走 presigned 直连） | 通过云手机 API 间接调用，AgentKit 自身不提供安卓沙箱（待核实） | 仓库约 487 star（第三方站统计，2026-07） | 源码 / 二手 | [12][13] |

**这说明什么（判断）**：字节的 Agent 沙箱分两条线：代码与浏览器类走容器（AIO Sandbox、SandboxFusion），安卓类走云手机产品。两条线之间尚无统一的 microVM 层方案，这也是 Cube 一类 microVM + redroid 路径可以切入的位置。

## 4. AS3-Q4 AgentEnv 与 DSec 的归属与能力

### 4.1 归属核实

| 名称 | 实际归属 | 字节有无同名 / 近似项目 | 证据 |
|---|---|---|---|
| DSec | DeepSeek（DeepSeek Elastic Compute，arXiv 2609.22978，2026-09-19，作者列表为 DeepSeek 研究人员，如 Jialiang Huang、Hongxuan Tang 等） | 未找到字节同名项目；字节近似物是 UI-TARS-2 的 GUI 沙箱与 AIO Sandbox | 论文全文；论文中无 ByteDance / Volc 字样 |
| AgentENV（AENV） | 月之暗面 Kimi 与 kvcache-ai；仓库 kvcache-ai/AgentENV（注意仓库名不是 AENV）；创建于 2026-07-23；MIT | 无 | README 称 powering Kimi K3；引 Kimi-K3 技术报告；WebSearch 摘要 |
| AgentEnv（LlamaTouch/AgentEnv） | 学术项目，描述为「面向移动 Agent、与真实安卓设备或模拟器交互的环境」；2024-07 后无更新，13 star；作者机构本轮未核（待核实） | 无 | GitHub API 元数据 |
| Scale AI 等的 AgentEnv 框架 | 第三方，主线程已列 | 无 | 主线程初查 |

用户的「都是字节的」不成立。可能的混淆来源：字节确有同类产品（UI-TARS-2 沙箱、AIO Sandbox），且 DeepSeek、Kimi、字节同属 2026 年披露 Agentic RL 基础设施的国内团队（判断）。

### 4.2 能力对比

| 项 | DSec（DeepSeek） | AENV（Kimi） |
|---|---|---|
| 后端 | FnCall、容器、Firecracker microVM、QEMU 全 VM 四类，统一 SDK libdsec | Firecracker microVM 单一形态；E2B 兼容 API（二手） |
| 安卓 / GUI | 有：全 VM 后端覆盖 Android（QEMU）与 GUI，GPU 用 virtio-gpu 半虚拟化，另可经 DXVK 兼容层；无安卓性能数字 | 未见 |
| 启动 / 恢复 | 论文有容器与 microVM 的启动、密度测量（本轮只读到摘要级数字，细节图表未逐一核对） | 恢复 <50 ms，暂停 <100 ms，快照 <100 ms（厂商自报，条件未给） |
| 规模 | 单 unit 约 160 节点；日 300 万沙箱；峰值并发 >38 万；创建 >5000/s；单作业最多 32K 沙箱；单节点最多 800 microVM / 3200 容器；云 VM 200 台承接约 30% 峰值溢出 | 镜像规模 150 万（引 Kimi-K3 报告）；内存超分 9.6x（生产，自报） |
| 镜像与存储 | 3FS 共享存储 + EROFS，base / workspace / toolkit 分层；microVM 4889 个快照（一周，论文） | overlaybd 按需加载；快照可落 S3 或分布式文件系统 |
| 快照 / 暂停 | pack_diff 增量磁盘快照；microVM 暂停时存内存与执行状态并结束 Firecracker 进程 | 增量内存 + 文件系统快照；可 fork 多个子沙箱（二手称单节点至多 16 个） |
| 宿主要求 | 容器与 FnCall 也跑在 QEMU/libvirt VM 内作为额外安全边界（论文） | Linux 6.8+，/dev/kvm；无 KVM 环境有 PVM 部署指南 |
| 安全 | eBPF 网络策略、IAM | 当前无内置鉴权，需可信网络（二手） |

**这说明什么（判断）**：DSec 是目前公开资料里少有的、在统一平台中把安卓放进全 VM 后端的 RL 沙箱，但它把安卓当作「长尾、高开销」类别，量产主力是容器与 microVM；AENV 的快照 / fork / 超分思路与 Cube 同源，但对安卓没有任何披露。二者都不能直接给出「安卓实例的重置时间与密度」。

## 待核实

1. 豆包手机助手：推理在云还是端、截图是否上传、虚拟屏是否真实使用，缺官方技术说明；IT之家原页 403，INJECT_EVENTS 说法来自搜索摘要。
2. UI-TARS-2 安卓实例形态、重置方式、单步时延，全文未披露；是否有补充材料未查。
3. 火山引擎云手机的实例规格、ARM 或 x86、容器还是 VM、单机密度（文档目录页未展开，需打开「云手机资源规格」「基本概念」）。
4. DSec 容器与 microVM 的启动延迟、密度的具体数值与测量条件，需通读 §5–§6 并核对图表。
5. LlamaTouch/AgentEnv 的作者机构；AENV 的 PVM 与 ARM 支持情况；AENV 是否有 GUI 示例（只读了 README，未查文档站）。
6. veRL 文档站里的 AgentLoop 是否有 GUI / 安卓示例；uni-agent 仓库未打开。

## 参考文献

| 编号 | 标题 | URL | 版本 / 日期 | 状态 |
|---|---|---|---|---|
| 1 | IT之家：豆包手机助手 INJECT_EVENTS 公告报道 | https://www.ithome.com/0/902/287.htm | 2025-12 | 未打开（403），引搜索摘要 |
| 2 | 界面新闻等：封禁与调整报道 | https://www.jiemian.com/article/13736294.html | 2025-12 | 未打开，引搜索摘要 |
| 3 | AI-Indeed 百科 | https://www.ai-indeed.com/encyclopedia/15223.html | - | 未打开，二手 |
| 4 | jit.pro：豆包手机 AI 原生系统架构 | https://jit.pro/blog/doubao-agentic-smartphones-ai-native-system-architecture | - | 未打开，引搜索摘要 |
| 5 | 人人都是产品经理：豆包手机分析 | https://www.woshipm.com/ai/6301182.html | 2025-12 | 未打开，引搜索摘要 |
| 6 | 36Kr（二代混合架构） | https://eu.36kr.com/en/p/3986222650283657 | 2026 | 未打开，引搜索摘要 |
| 7 | agent-infra/sandbox README | https://github.com/agent-infra/sandbox | v1.11.0，2026-06-23 | 已抓 |
| 8 | AIO Sandbox 介绍（CSDN 等） | https://gitcode.csdn.net/69f389900a2f6a37c5a7152d.html | - | 未打开，引搜索摘要 |
| 9 | bytedance/SandboxFusion README | https://github.com/bytedance/SandboxFusion | main | 已抓 |
| 10 | volcengine/verl README | https://github.com/volcengine/verl | main | 已抓 |
| 11 | 火山引擎云手机文档目录 | https://docs.volcengine.com/docs/6394 | 2026-11 | 已抓（仅目录） |
| 12 | bytedance/agentkit-samples（byted-acep-api 技能） | https://claudeskills.info/skills/bytedance/agentkit-samples/byted-acep-api/ | 2026-07-23 | 已抓（第三方镜像） |
| 13 | BytePlus AgentKit 文档 | https://docs.byteplus.com/en/docs/agentkit/Tools | - | 未打开 |
| 14 | UI-TARS-2 Technical Report | https://arxiv.org/abs/2509.02544 | 2025-09 | 已抓（html 全文） |
| 15 | DSec: DeepSeek Elastic Compute | https://arxiv.org/abs/2609.22978 | 2026-09-19 | 已抓（html 全文） |
| 16 | kvcache-ai/AgentENV README | https://github.com/kvcache-ai/AgentENV | main，2026-11 | 已抓 |
| 17 | AgentENV 报道（opensourceforu、marktechpost、aiweekly 等） | https://www.marktechpost.com/2026/07/27/kimi-ai-and-kvcache-ai-open-sources-agentenv/ | 2026-07-27 | 未打开，引搜索摘要 |
| 18 | LlamaTouch/AgentEnv | https://github.com/LlamaTouch/AgentEnv | 最后推送 2024-07-19 | 仅 API 元数据 |

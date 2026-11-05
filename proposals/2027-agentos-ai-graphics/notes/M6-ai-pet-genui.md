# M6 调研笔记：AI 萌宠（G2）与生成式 UI（G4）

> 调研日期：2026-11-03。范围：研究任务说明 1.3、第二部分、第四部分中与 G2、G4 相关的内容（第三部分由主笔汇总）。
> 定位：AI + 图形线只提升用户体验，不与系统功能挂钩；不做 GUI Agent。

## 摘要（10 行以内）

1. 七家手机厂商（华为、荣耀、OPPO、vivo、小米、三星、苹果）**均未找到公开的、官方的「AI 萌宠 / 桌面宠物」系统功能**。最接近的是荣耀 Robot Phone（2026-08-12 发布）：云台带拟人表情，但官方未称其为宠物或形象。小米仅有主题商店的静态「萌宠锁屏」。
2. AI 陪伴的需求是真实的，但商业化集中在 App 和独立硬件：Appfigures 统计，2026 年上半年仅浪漫 / NSFW 类陪伴 App 就有 1.628 亿美元内购收入；Casio Moflin 日本累计售出 7000 台以上。
3. 留存数据普遍缺失且口径混乱：RevenueCat 给出 AI 类 App 年留存 21.1%（对非 AI 的 30.7%）；陪伴类 D30 留存 5%–15% 只有厂商博客来源（待核实）；Ropet 自报 90 天留存 80%–90%（硬件、公司口径）。
4. Grok Companions（2025-07 上线）的 3D 形象模式在 2026-07 前后疑似被收缩，来源均为第三方博客，**待核实**。
5. 生成式 UI 已形成三种形态：声明式 JSON（Google A2UI、Open-JSON-UI）、iframe 沙箱 HTML（MCP Apps，ChatGPT、Claude 等已支持）、模型直接写代码（Google Gemini 动态视图）。HarmonyOS 和 Apple 没有同类的公开协议，只有「智能体 + 元服务」和 `@Generable` 结构化流式输出。
6. 对终端渲染引擎的核心要求：组件目录（白名单）、流式增量渲染、沙箱隔离、与原生设计系统一致。声明式 JSON 路线最适合手机原生渲染；iframe 路线需要常驻 WebView，内存和启动代价大。
7. 最大资料空白：常驻萌宠的功耗、内存实测数据（未找到公开资料）；生成式 UI 在手机上的首帧时延和掉帧实测（未找到公开资料）；陪伴类产品的第三方留存数据。

---

## 第一部分 洞察（1.3 中的 G2、G4）

### 1.3-G2 AI 萌宠 / 虚拟伴侣

#### 1.3-G2-a 手机厂商逐家核实

| 厂商 | 核实结论 | 依据 |
|---|---|---|
| 华为（HarmonyOS 7、小艺） | 未找到 AI 萌宠 / 桌面宠物 / 虚拟形象类官方功能。小艺定位为系统级智能体，HDC 2026（2026-06）发布鸿蒙智能体框架 2.0，小艺采用四层记忆架构。 | [R3][R4] |
| 荣耀（YOYO、Robot Phone） | 未找到 YOYO 萌宠。Robot Phone 于 2026-08-12 发布，9999 元起，4 自由度云台，YOYO 机器人模式可通过拟人表情表达情绪、随音乐节拍摆动云台；ifanr 评论称有「电子宠物感」，但官方未定义为宠物产品。端侧模型参数量未公开。 | [R5][R6] |
| OPPO（ColorOS 17、小布） | 未找到萌宠功能。ColorOS 17（2026-09）的新一代小布支持长上下文，用户可自定义小布的情绪、表达风格、回复长度；流体云承载服务信息。「小布 3D 虚拟形象」仅见于一个非官方资料站，**不采信**。 | [R7] |
| vivo（OriginOS 7、蓝心小V） | 未找到萌宠。小V 有悬浮态和桌面常驻的「小V建议」，OriginOS 7 的小V Pro 强调任务拆解和跨端执行。 | [R8] |
| 小米（HyperOS / 澎湃OS） | 未找到小爱同学的桌面宠物或虚拟形象。HyperOS 2 时期主题商店上新三款「萌宠锁屏」，属静态主题，不是 AI 功能。 | [R9] |
| 三星（One UI 8.5） | 未找到陪伴角色或宠物功能。Galaxy S26 有 AI 贴纸工具，可把宠物照片转为表情贴纸包；「companion」只是 CES 2026 的营销主题。 | [R10] |
| 苹果（iOS 27） | 未找到。WWDC 2026 的 Siri 重构以 Dynamic Island 的「搜索或提问」界面为主，Vision Pro 上是浮动光球，不是角色。 | [R11] |

**结论**：截至 2026-11-03，主流手机厂商没有一家把「AI 萌宠」做成系统功能。这既是空白也是风险：说明用户需求尚未被系统级验证，立项需要说明为何要做。

> 注：本表依赖搜索引擎摘要和媒体报道，未逐家读取官方功能清单；个别厂商（如 OPPO、vivo 的小功能入口）存在漏检可能，已在待核实清单列出。

#### 1.3-G2-b 代表形态

| 形态 | 代表 | 事实依据 | 局限 |
|---|---|---|---|
| 大厂 App 内 3D 角色 | Grok Companions（Ani、Rudi，后续有 Valentine、Mika 之说） | 2025-07 上线，面向 SuperGrok 订阅用户，约 30 美元 / 月档位 [R1]；2026 年有 Android 版及新角色的说法，另有「2026-07-24 宣布将下线 3D 形象模式」「2026-08-12 官方文档不再列出」两条第三方说法，**均待核实** [R12] | 内容安全争议大（上线时被报道「儿童模式」下仍可访问 Ani）；现状无官方确认 |
| 创业公司 App | Tolan（Portola，外星人伙伴，语音优先） | 2025-07 A 轮 2000 万美元（Khosla 领投）；后续 3000 万美元一轮；公司称 25 万活跃用户、一年 7000 万次对话 [R13]。ARR 1200 万美元等收入数据来自二手来源 | 用户数为公司自报；无留存数据 |
| 角色扮演 App | Character.AI | 月活约 2000 万（二手来源）；日均使用时长有 8–9 分钟（FoxData）和 75–80 分钟（公司 CEO 口径，二手转述）两个相差近 10 倍的说法 [R14] | 口径冲突，不可直接引用 |
| 独立硬件 | Ropet（萌友智能）、Casio Moflin、Loona 等 | Ropet 2025-09 起全球交付，累计出货近 2 万台，约 70% 来自海外，2026-04 获超千万美元 A 轮 [R15]；Moflin 日本 2024-11 上市，至 2025-03 售出 7000 台以上，US/UK 售价 429 美元 [R16] | Ropet 数据为公司口径；Loona、Gatebox、Miko 未找到销量 |
| 端侧数字人（技术验证） | 阿里 MNN TaoAvatar（CVPR 2025） | 全链路（ASR、本地 LLM、TTS、音频到 blendshape、神经渲染）可离线跑在手机上；论文称头显上 90 FPS，手机侧 60 FPS 为二手文章说法（250k 点云，NNR 渲染器）[R17] | 手机侧数据来自二手转述；内存与功耗未公开 |
| 手机系统静态宠物 | 小米萌宠锁屏 | 主题商店静态资源 [R9] | 非 AI |

#### 1.3-G2-c 技术栈拆解

| 层 | 业界做法（有据可查的部分） | 对手机的含义 |
|---|---|---|
| 形象生成 | 2D 立绘、3D 角色或 3DGS 数字人（TaoAvatar 即基于 3DGS 的全身数字人）；Samsung S26 用「照片转贴纸」做轻量形象生成 [R10][R17] | 形象资产的离线生成与端侧驱动资源要分开考虑，与 G1（3DGS）可共享渲染管线 |
| 动作生成 | 音频到 blendshape（TaoAvatar 的转换步骤，RTF 0.34，二手来源）；动画状态机（Rive 为状态机运行时，Lottie 仅回放，2025 年底起 Lottie 新增状态机，厂商自述）[R17][R18] | 低端设备上 Lottie 复杂矢量动画有掉帧的报告 [R18]；动作需要「状态机 + 少量模型驱动」的混合 |
| 性格与记忆 | Mem0 论文（arXiv 2504.19413，2025-04）：在 LOCOMO 上 p95 延迟降低 91%、token 成本降低 90% 以上（对比全上下文）[R19]；小艺四层记忆 [R3]；OPPO 小布可自定义情绪与表达风格 [R7] | 记忆属于「小块、高频读、低频写」的数据，需要持久存储和隐私隔离 |
| 常驻低功耗渲染 | 未找到公开的手机常驻宠物功耗实测；Rive 与 Lottie 对比文章无电量基准 [R18] | 这是本线最大的资料空白，需要自建测量 |

#### 1.3-G2-d 市场与留存

| 指标 | 数值 | 来源与口径 | 可信度 |
|---|---|---|---|
| 浪漫 / NSFW 陪伴 App 累计下载与内购 | 1.653 亿次下载、4.273 亿美元（自 ChatGPT 发布起） | Appfigures，经 Decrypt 2026-07-13 转述；仅应用商店、扣费前；不含纯网页平台 [R20] | 较高 |
| 2026 上半年收入 | 214 款浪漫类 App 合计 1.628 亿美元；PG 类约 1.648 亿美元，下载量约浪漫类 2 倍 | 同上 [R20] | 较高 |
| 2025 年全年预测 | 约 1.2 亿美元 | TechCrunch 2025-08-12 引 Appfigures [R21] | 较高 |
| 收入集中度 | 前 10% 的应用占 89% 收入；约 10%（33 款）累计超 100 万美元 | TechCrunch 引 Appfigures（截至 2025-07）[R21] | 较高 |
| AI 类 App 订阅留存 | 年留存 21.1%（非 AI 为 30.7%）；月留存 6.1%（非 AI 为 9.5%）；试用转付费 8.5%（非 AI 为 5.6%） | RevenueCat 2026 年 3 月报告，经 TechCrunch 2026-03-10 转述；**是全部 AI 类 App，不是陪伴类** [R22] | 较高，但不针对陪伴 |
| 陪伴类 D30 留存 | 5%–15% | getkapex 厂商博客，称引 Sensor Tower、data.ai，未指明具体报告 | 低，待核实 |
| 硬件留存 | Ropet 日均开机超 20 小时、90 天留存 80%–90% | 公司自报，报道本身标注为 AI 生成内容、仅供参考 [R15] | 低 |
| 硬件「宠物类 App 月活留存不超 30%」 | 行业传言 | 智哪儿文章，无出处 | 低，不采信 |
| AI 仿生宠物硬件规模 | 2025 年产量 77.3 万件（恒州诚思）；销售额 2.47 亿美元（QYResearch） | 两家机构数字口径不一致 [R15] | 低 |
| 国内陪伴细分 | 未找到星野、猫箱、筑梦岛的月活或留存数据 | QuestMobile 2026-07 报告：AI 原生 App 月活 4.99 亿（截至 2026-05），月人均使用约 87–93 次、183 分钟，未单列陪伴 [R23] | 缺失 |

**对市场数据的判断（观点）**：陪伴类是「高下载、高付费意愿、低留存」的结构，收入由少数头部撑起；对手机厂商而言，直接可验证的是「是否提升日活和使用时长」，而不是订阅收入。我们没有公开证据说明系统内置萌宠能提升留存，需要立项后用灰度实验自行取证。

### 1.3-G4 生成式 UI

#### 1.3-G4-a 各家协议 / 框架的形态

| 方案 | 形态 | 关键机制 | 状态与来源 |
|---|---|---|---|
| Google A2UI | 声明式 JSON，客户端用自家原生组件渲染 | 智能体只发送数据，不发送代码；UI 为带 ID 引用的扁平组件列表，天然支持增量与流式；客户端维护「可信组件目录」，模型只能在目录内组合；传输无关（SSE、WebSocket、A2A、AG-UI）；渲染器有 Lit、Angular、React、Flutter，SwiftUI 渲染器尚未发布 | 官方仓库称「早期公开预览」，当前生产版本 v0.9.1，v1.0 为候选版本 [R24]。Lynx（字节系跨端框架）有 A2UI 接入文档，称协议消息经 ReactLynx 映射到原生组件，无性能数据 [R25] |
| Open-JSON-UI | 声明式 JSON | 据 CopilotKit 文档，是对 OpenAI 内部声明式 UI 模式的开放标准化 | 仅见 CopilotKit 二手描述，**待核实** [R26] |
| MCP Apps（SEP-1865） | HTML 页面，在宿主的沙箱 iframe 中渲染 | 工具通过 `_meta.ui.resourceUri` 指向 `ui://` 资源，宿主可预取；应用与宿主经 postMessage 上的 JSON-RPC 通信；`_meta.ui.csp` 声明外部域名，`permissions` 声明麦克风、摄像头等；规范修订版 2026-01-26 | 官方文档称 Claude、Claude Desktop、VS Code Copilot、Microsoft 365 Copilot、Goose、Postman 等已支持 [R27] |
| OpenAI（ChatGPT 的 UI 扩展） | 与 MCP Apps 一致，另有 `window.openai` 扩展 | 官方文档称「ChatGPT 实现开放的 MCP Apps 标准」；显示模式有行内卡片、行内轮播、全屏、画中画；声明 CSP，嵌套框架默认阻止；UI 状态按实例短暂保存 | 文档页面已使用 Plugins 命名，Apps SDK 仅在包名和路径中出现，**命名变化待核实** [R28] |
| Google Gemini 生成式 UI | 模型直接生成并运行定制交互界面 | 2025-11 随 Gemini 3 发布，Gemini 应用中有「动态视图」和「可视布局」两项实验，美国 AI Pro / Ultra 订阅用户可在搜索 AI 模式中使用；Google Research 论文称评测者明显偏好动态视图 | 结论为官方自述；细节引自二手分析 [R29] |
| Apple | 无公开的界面生成协议 | Foundation Models 框架的 `@Generable` 提供结构化输出，流式输出以「快照」形式给出、属性逐步填充；WWDC 2025 讲座提到递归类型可用于生成式 UI；WWDC 2026 起框架统一覆盖端侧、Private Cloud Compute 和第三方模型（二手来源）。未找到 SwiftUI 层面的生成式 UI API | 属于「用结构化输出间接做生成式 UI」，iOS 27 细节为二手来源，**待核实** [R30] |
| HarmonyOS | 未找到「小艺按需生成界面」的官方资料 | HDC 2026 发布鸿蒙智能体框架 2.0，系统应用全面 Skill 化，2100 多项系统能力可被小艺调用；服务呈现仍依托元服务与卡片 | 属于「调度既有服务」，不是「生成界面」[R4] |
| Android | 未找到把端侧模型输出直接映射为 Compose 界面的官方方案 | Google AI Studio 在 2026-05 的 I/O 上可从提示生成原生 Jetpack Compose 应用，运行在云端；RemoteCompose 与生成式 UI 的关系未确认 | 二手来源，**待核实** [R31] |

#### 1.3-G4-b 对终端渲染引擎的要求（从上述协议归纳）

| 维度 | 要求 | 依据 |
|---|---|---|
| 安全 | 声明式路线：组件白名单，数据而非代码；iframe 路线：沙箱、CSP、权限逐项声明，禁止访问宿主 DOM / Cookie | A2UI 与 MCP Apps 的安全模型 [R24][R27] |
| 性能 | 扁平结构便于增量更新；模板可预取（`ui://` 资源在工具调用前即可加载）；首帧要早于生成结束 | [R24][R27] |
| 流式渲染 | 要能处理部分到达、尚不完整的组件树；Apple 的做法是属性按顺序逐步填充，建议把最可见的内容放在前面生成 | [R24][R30] |
| 一致性 | 复用既有设计系统与主题 | Lynx 对 A2UI 的描述 [R25] |
| 交互回传 | 用户动作需回送给模型（A2UI v0.9 让客户端随动作回传完整界面数据模型；MCP Apps 通过 `ui/update-model-context`）| [R24][R27][R28] |

#### 1.3 对立项的启示

- **G2**：厂商侧没有先例，意味着没有可对标的系统级体验指标；公开数据只能支撑「陪伴需求存在、变现集中在头部」，不能支撑「系统内置萌宠能提升留存」。立项必须把「常驻低功耗渲染」作为可交付的核心（它是唯一手机厂商能做、App 做不了的部分），并把留存作为待验证假设。
- **G4**：声明式 JSON + 组件目录 + 流式增量，是最适合手机原生渲染的路线（A2UI 的设计取向）；iframe 路线适合云端对话产品，放在端侧要承担 WebView 常驻代价。HarmonyOS 与 Apple 都还没有公开的界面生成协议，存在先发空间，但也意味着没有生态。

---

## 第二部分 问题（G2、G4）

### 2.1 场景与需求（2027–2028）

#### G2 AI 萌宠

| 场景 | 用户需求 | 可量化体验指标（建议值，待立项验证） |
|---|---|---|
| S-G2-1 桌面常驻陪伴：宠物常驻桌面或息屏，随时间、使用状态变化表情和动作 | 看得到、不打扰、不费电 | 常驻额外功耗（待测，立项目标见第四部分）；桌面掉帧率；对前台应用启动无可测影响 |
| S-G2-2 对话与情感互动：语音唤起，宠物应答并带表情和动作 | 对话自然、宠物「记得我」 | 语音到首个动作的响应时延；记忆召回的准确率（需自建评测集） |
| S-G2-3 系统事件联动：充电、通知、天气等触发宠物反应（仅表现层，不绑定系统功能） | 有趣、可关闭 | 事件到动作的时延 |
| S-G2-4 形象定制：用户用文字或照片生成自己的形象 | 低门槛、快 | 生成耗时；失败率 |

#### G4 生成式 UI

| 场景 | 用户需求 | 可量化体验指标（建议值，待立项验证） |
|---|---|---|
| S-G4-1 对话中直接给出可交互的界面（图表、表单、比较表） | 比文字更直观，能点能改 | 首个可见元素时延；流式过程掉帧率；交互响应时延 |
| S-G4-2 一次性小工具：用户一句话生成临时计算器、行程卡、打卡面板 | 即用即走，不必安装 | 从提示到可操作的总时延；内存占用 |
| S-G4-3 第三方服务以生成界面形式嵌入（订票、点餐的轻量面板） | 不跳出当前应用 | 安全隔离是否生效；与原生设计一致 |
| S-G4-4 个性化卡片：根据用户上下文重排桌面卡片 | 信息按需呈现 | 卡片刷新耗时；电量 |

### 2.2 当代系统与瓶颈

> 本节无公开的量化实测数据（手机常驻萌宠功耗、生成式 UI 手机端时延均**未找到公开资料**），以下为机制分析和估算，估算均写明方法。

#### G2 常驻低功耗渲染

| 瓶颈 | 当代系统的做法 | 卡点 | 量化 |
|---|---|---|---|
| 持续渲染的 GPU / 显示功耗 | Android 动态壁纸、桌面小组件、悬浮窗；iOS 的小组件为受限的时间线快照；HarmonyOS 有服务卡片，鸿蒙 7 桌面壁纸支持空间立体效果 [R4] | 小组件类机制不允许高帧率连续动画；悬浮窗和动态壁纸属于应用进程，受后台限制和 LMKD（Android）、Jetsam（iOS）的回收影响 | 未找到公开数据；需自建基线：「相同桌面，宠物开启 vs 关闭，1 小时电量差」，估算法见第四部分 |
| 内存常驻 | 应用进程常驻会占用匿名页，被回收后再回到前台有重建代价 | 角色模型、纹理、记忆索引、本地小模型同时常驻 | 估算：本地 1B–3B 参数量模型 INT4 权重约 0.5–1.5 GB（参数量 × 0.5 字节），仅作量级；渲染资源量级待测 |
| 动作与表情驱动 | 状态机 + 预制动画；Lottie 复杂矢量动画在低端机掉帧 [R18]；音频驱动 blendshape 的 RTF 为 0.34（TaoAvatar，二手来源）[R17] | 实时模型驱动与常驻功耗相冲突 | RTF 0.34 意味着每 1 秒音频需约 0.34 秒计算 |
| 记忆的存储与召回 | 向量 / 图索引 + 召回 [R19] | 手机上的读写 I/O、隐私隔离 | Mem0 在云端对比报告 p95 延迟降低 91% [R19]，端侧无数据 |

#### G4 生成式 UI

| 瓶颈 | 当代系统的做法 | 卡点 | 量化 |
|---|---|---|---|
| 生成速度 | 云端生成 + 流式传输；端侧小模型也可输出结构化界面 | 界面描述通常需要数千 token | 估算：假设一个中等复杂界面描述 3000 token，端侧 decode 30 token/s 需约 100 秒，云端 100 token/s 需约 30 秒；两个速度均为示例假设，实际需测，因此必须靠流式「边生成边渲染」 |
| 流式渲染 | 声明式协议的扁平结构天然支持；Apple 用属性逐步填充 [R24][R30] | 部分到达的树会触发频繁布局，造成掉帧 | 未找到公开数据 |
| 安全与隔离 | iframe 沙箱 + CSP（MCP Apps）；组件白名单（A2UI）[R24][R27] | iframe 需要 WebView：常驻内存与启动时延；声明式需要完整的组件库 | 未找到 WebView 内存的公开基线，待测 |
| 与原生一致 | A2UI 复用客户端设计系统；iframe 路线与原生外观割裂 | 生成物的可访问性、深色模式、动效一致性 | 无量化 |
| 平台缺口 | Apple、HarmonyOS 没有公开的界面生成协议；Android 无官方端侧方案 [R4][R30][R31] | 需要自建或采纳 A2UI 一类开放协议 | — |

#### 第二部分对立项的启示

- G2 的立项理由应落在「系统层才能做好的常驻低功耗渲染」：当前系统机制把长期连续渲染的角色放在应用进程里，受回收、后台限制和功耗约束，没有一个厂商提供过系统级方案。
- G4 的理由在「流式、安全、原生一致」三者同时满足：iframe 路线安全但与原生割裂且重，声明式路线轻但依赖组件库完备度。

---

## 第四部分 关键技术（G2、G4）

### G2 AI 萌宠

#### 1. 要解决的问题

- 现状：手机上没有系统级的常驻 AI 宠物，宠物类体验由 App 提供，受后台限制和功耗约束；厂商侧未发现同类功能（见 1.3-G2-a）。
- 代价：未找到公开的功耗和内存数据。需要先建立基线，估算方法：A/B 两台同型号手机，一台开启持续动画宠物（目标 30 FPS），另一台关闭，息屏与亮屏各 1 小时记录电量差和 GPU 活跃时间，基线数据**待实测**。
- 市场侧：陪伴类 App 付费集中于头部，AI 类 App 年留存 21.1%（RevenueCat，全部 AI 类）[R20][R22]。

#### 2. 业界做法扫描

| 方案名 | 年份 | 来源 | 一句话原理 | 局限 |
|---|---|---|---|---|
| Grok Companions | 2025 | [R1] | 云端大模型 + 3D 动画角色 + 订阅 | 现状待核实；内容安全争议 |
| Tolan | 2025 | [R13] | 语音优先的外星人伙伴，强调记忆和日常陪伴 | 公司自报数据 |
| MNN TaoAvatar | 2025（CVPR） | [R17] | 3DGS 全身数字人，手机端离线跑完整链路 | 手机数据为二手来源；内存功耗未公开 |
| Mem0 | 2025 | [R19] | 抽取、整合、召回长期记忆，降低上下文成本 | 云端评测；总成本不含抽取流程（二手批评） |
| Ropet / Moflin | 2025 | [R15][R16] | 独立硬件，自带传感与个性成长 | 硬件成本高；留存数据口径不一 |
| 荣耀 Robot Phone | 2026 | [R5][R6] | 云台 + 拟人表情 + 端侧 YOYO | 非萌宠定位；模型规模未公开 |
| Rive 状态机 | — | [R18] | 二进制运行时 + 输入驱动的状态机 | 无功耗基准 |

#### 3. 技术难点

**难点一：常驻渲染的功耗预算**
- 难在哪：用户愿意开着宠物的前提是「几乎不耗电」；而连续动画要持续唤醒 GPU 与显示管线。
- 怎么破：对「宠物渲染」做分级——静止（事件驱动渲染，无事件时不提交帧）、微动（低帧率 + 预制片段）、互动（满帧 + 模型驱动）；渲染放在系统合成层（系统服务）而非应用进程，随息屏、遮挡、温度自动降级。
- 关键突破：事件驱动 + 分级降帧，使空闲功耗趋近于零。

**难点二：形象与动作的「小模型 + 预制资源」混合生成**
- 难在哪：实时用大模型驱动动作不可持续；纯预制动画又缺少个性。
- 怎么破：用大模型离线或按需生成「动作脚本 / 状态机参数」，由本地状态机执行；音频驱动嘴型等高频部分使用小模型（参考 TaoAvatar 的 blendshape 驱动，RTF 0.34，二手来源）。
- 关键突破：低频由大模型决策，高频由小模型和状态机执行。

**难点三：性格与记忆的端侧持久化与隐私**
- 难在哪：记忆越多越个性化，也越敏感；端侧存储与召回要低延迟，且不能被其他应用读取。
- 怎么破：记忆分层（短期对话、中期事件摘要、长期偏好），摘要与召回参考 Mem0 的抽取—召回思路；存储放在系统受保护目录，召回用小索引；云端仅在用户授权时使用。
- 关键突破：分层记忆把召回成本降到「只读相关少量条目」。

#### 4. 机制架构（感知 / 建模 → 决策 → 执行 → 反馈）

- **感知 / 建模**：系统事件采集（亮灭屏、充电、通知、时间）、语音输入、用户偏好；记忆库（短 / 中 / 长期）；渲染负载模型（温度、电量、遮挡）。
- **决策**：宠物行为决策器（本地小模型或规则，必要时请求云端大模型）；渲染分级策略（静止 / 微动 / 互动）。
- **执行**：状态机运行时；系统合成层的常驻渲染服务；音频驱动动作模块；形象资产加载。
- **反馈**：功耗与帧率监测回流到分级策略；用户的互动、关闭行为回流到行为决策与记忆。

#### 5. 目标与度量

> 以下为建议目标，依据为「无公开基线，需实测校准」，目标值在立项后用基线数据修正。

| 指标 | 基线 | 目标（建议） | 测试条件 |
|---|---|---|---|
| 常驻静止态额外功耗 | 待测（应用进程实现的同类宠物） | 相对关闭状态的 1 小时电量差在测量误差内（待定义阈值） | 同型号、同亮度、息屏 / 亮屏各一组 |
| 常驻内存 | 待测 | 不超过待定上限（建议 100–150 MB，**估算**，需依据实测定） | 不含本地大模型 |
| 互动态掉帧率 | 待测 | 待定 | 30 FPS 目标，中端芯片 |
| 对话到首个动作时延 | 待测 | 待定 | 语音输入结束到动作开始 |
| 前台应用冷启动影响 | 待测 | 无可测劣化 | 宠物开启 vs 关闭对比 |

#### 6. 风险与待核实

- 无公开证据证明系统内置萌宠提升留存；留存数据均来自 App、硬件或公司口径。
- 内容安全与未成年人保护：Grok Companions 上线时的争议提示，需要内容审核和年龄限制设计 [R1]。
- 情感依赖的监管与舆论风险；TechCrunch 报道 Tolan 融资时提到针对通用 AI 应用的多起诉讼。
- Grok 3D 形象模式现状待核实；各厂商功能漏检可能。
- 常驻渲染功耗没有公开基线。

#### 7. PPT 素材卡

**挑战**
1. 常驻耗电：宠物连续渲染 GPU 与显示持续唤醒，目前无公开功耗数据，需自建基线。
2. 无系统级先例：七家厂商均未发现官方宠物功能，只能以 App 与硬件数据作旁证。
3. 记忆与隐私：个性化需长期记忆，端侧存储和召回要低时延且隔离。

**目标**：打造系统级、事件驱动的常驻 AI 萌宠，空闲几乎不耗电，对话与互动有个性、有记忆。
**量化目标**：空闲功耗趋零；内存待基线定

**技术难题**
- 难题一：常驻渲染功耗预算
  - 分级渲染：静止、微动、互动三档按状态切换
  - 事件驱动：无事件不提交帧，息屏即停
  - 关键突破：空闲零帧
- 难题二：混合式动作生成
  - 大模型定脚本：低频决策生成动作参数
  - 小模型驱动：嘴型等高频动作用小模型
  - 关键突破：低频大模型高频小模型
- 难题三：端侧分层记忆
  - 三层记忆：短期、事件摘要、长期偏好
  - 受保护存储：系统目录隔离，应用不可读
  - 关键突破：只召回相关少量条目

**架构四段**
- 感知 / 建模：系统事件、语音输入、记忆库、渲染负载
- 决策：行为决策器、渲染分级策略
- 执行：状态机运行时、合成层渲染、音频驱动
- 反馈：功耗帧率监测、互动反馈

---

### G4 生成式 UI

#### 1. 要解决的问题

- 现状：模型生成界面在云端对话产品里已出现（Gemini 动态视图、ChatGPT 与 Claude 的 MCP Apps），但手机系统层没有统一的渲染方案；Apple、HarmonyOS 没有公开的界面生成协议 [R4][R27][R29][R30]。
- 代价（估算）：界面描述数千 token，按端侧 decode 30 token/s 假设，3000 token 需约 100 秒（假设值，非实测），若不能边生成边渲染，用户等待不可接受；iframe 路线需要常驻 WebView，内存与启动代价**待测**。

#### 2. 业界做法扫描

| 方案名 | 年份 | 来源 | 一句话原理 | 局限 |
|---|---|---|---|---|
| A2UI | 2025–2026 | [R24] | 智能体发声明式 JSON，客户端用目录内原生组件渲染 | 公开预览期；SwiftUI 渲染器未发布 |
| MCP Apps（SEP-1865） | 2025–2026（规范修订 2026-01-26） | [R27] | 工具声明 `ui://` 资源，宿主在沙箱 iframe 渲染 | 偏 Web；端侧需要 WebView |
| OpenAI ChatGPT UI | 2025–2026 | [R28] | 实现 MCP Apps，并扩展 `window.openai`，有四种显示模式 | 命名变化待核实 |
| Open-JSON-UI | — | [R26] | 声明式 JSON 的开放标准化 | 仅二手描述 |
| Gemini 生成式 UI | 2025-11 | [R29] | 模型直接生成交互界面 | 云端；订阅限定；评测为官方自述 |
| Apple `@Generable` | 2025–2026 | [R30] | 结构化输出 + 快照式流式 | 不是界面协议 |
| Lynx A2UI 接入 | 2026 | [R25] | 协议消息映射为跨端原生组件 | 无性能数据 |
| AG-UI | — | [R26] | 智能体与应用之间的双向交互传输层，不是界面规范 | 属于传输层 |

#### 3. 技术难点

**难点一：流式增量渲染不卡顿**
- 难在哪：组件树持续到达，每次到达都可能触发布局和重绘；首个可见元素要尽早出现，又不能让已显示内容反复跳动。
- 怎么破：对声明式组件流做增量差分，只更新变化节点；将布局计算放在渲染线程之外，按帧预算合批提交；约定生成顺序（可见内容优先，参考 Apple 对属性顺序的建议）。
- 关键突破：按帧预算合批的增量提交。

**难点二：沙箱隔离与端侧资源的平衡**
- 难在哪：不可信界面不能越权；iframe 提供强隔离但 WebView 重；纯声明式轻但表达力受限于组件目录。
- 怎么破：默认走声明式 + 组件目录；表达力不足时降级到受限 WebView，并按需创建、用后回收；权限（摄像头、网络域）逐项声明、逐项授权（对应 MCP Apps 的 CSP 与权限声明）。
- 关键突破：声明式为主、受限 WebView 兜底。

**难点三：生成物与原生体验一致**
- 难在哪：模型生成的界面容易在字体、间距、深色模式、无障碍上与系统不一致。
- 怎么破：以系统设计系统构建组件目录，模型只能引用目录内组件与设计令牌（A2UI 的目录做法）；校验层拒绝或修复非法节点。
- 关键突破：设计令牌约束的组件目录。

#### 4. 机制架构（感知 / 建模 → 决策 → 执行 → 反馈）

- **感知 / 建模**：设备能力与组件目录描述（屏幕、深浅色、可用组件、权限）、当前上下文；协议解析与校验。
- **决策**：渲染路径选择（声明式或受限 WebView）；帧预算与批量策略；权限授权判定。
- **执行**：流式解析器、增量布局与差分渲染、组件库、受限 WebView 容器。
- **反馈**：用户交互事件回传给模型（含界面数据模型）；首帧时延、掉帧、内存监测回流到批量策略。

#### 5. 目标与度量

| 指标 | 基线 | 目标（建议） | 测试条件 |
|---|---|---|---|
| 首个可见元素时延（从首个 token 到屏幕） | 待测 | 待定（建议以「低于首 token 到达后一个渲染帧预算」为方向） | 流式场景 |
| 流式渲染期间掉帧率 | 待测 | 待定 | 中端芯片，持续生成 10 秒以上 |
| 渲染路径内存增量 | 待测（声明式 vs WebView 对比） | 声明式显著低于 WebView | 同一界面两种路径 |
| 安全：越权用例拦截率 | — | 100%（测试集内） | 构造越权用例集 |

> 目标值缺少公开基线，需用声明式与 WebView 两条路径各做一版原型测量后定稿。

#### 6. 风险与待核实

- A2UI 处于公开预览，协议仍会变化；Open-JSON-UI、AG-UI 细节来自 CopilotKit 文档（厂商文档，自带立场）。
- 生态：HarmonyOS 与 Apple 没有公开协议，采用开放协议需要与各平台能力对齐。
- Google「评测者偏好动态视图」为官方自述，评测方法未读到原文。
- Apple iOS 27 的相关细节为二手来源。
- 本线定位为体验提升，不与系统功能挂钩，且不做 GUI Agent：界面仅用于信息展示与轻交互，不用于控制其他应用。

#### 7. PPT 素材卡

**挑战**
1. 流式易卡顿：组件树持续到达，反复布局重绘，首个元素要尽早出现。
2. 隔离与资源矛盾：iframe 安全但需常驻 WebView，声明式轻但表达受限。
3. 与原生割裂：模型生成界面在字体、深色、无障碍上易不一致。

**目标**：在系统渲染引擎中支持模型生成界面的流式、安全、原生一致渲染，让对话直接产出可交互界面。
**量化目标**：首元素尽早出现；流式不掉帧

**技术难题**
- 难题一：流式增量渲染不卡顿
  - 增量差分：只更新变化节点，避免整树重排
  - 帧预算合批：布局离开渲染线程，按帧提交
  - 关键突破：按帧预算合批提交
- 难题二：沙箱隔离与资源平衡
  - 声明式优先：组件目录内渲染，数据不是代码
  - 受限 WebView：表达不足时按需创建、用后回收
  - 关键突破：声明式为主兜底 WebView
- 难题三：生成物与原生一致
  - 目录约束：模型只能用系统组件与设计令牌
  - 校验修复：非法节点拒绝或自动修复
  - 关键突破：令牌约束的组件目录

**架构四段**
- 感知 / 建模：组件目录、设备能力、协议校验
- 决策：渲染路径选择、帧预算策略、权限判定
- 执行：流式解析器、增量渲染、受限 WebView
- 反馈：交互回传、首帧与掉帧监测

---

## 第四部分对立项的启示（G2、G4）

- G2 的立项依据是「系统层常驻低功耗渲染」，公开资料没有基线，立项第一步应是自建功耗与内存基线，再定量化目标。
- G4 的路线选择：以声明式 JSON + 组件目录为主（对应 A2UI 取向），受限 WebView 兜底（对应 MCP Apps 兼容）；既能对接云端智能体的两大开放协议，又不依赖常驻 WebView。

---

## 参考资料

> 日期说明：部分条目页面本身未标注日期，日期列写「未核实」；搜索结果为摘要，未对所有来源逐页读取原文。

| 编号 | 标题 | URL | 日期 |
|---|---|---|---|
| R1 | Musk's Grok 'companions' include a flirty anime character and an anti-religion panda（NBC News） | https://www.nbcnews.com/tech/internet/grok-companions-include-flirty-anime-waifu-anti-religion-panda-rcna218797 | 2025-07 |
| R2 | grok ai launches flirty companions ani and rudi for 30 monthly subscribers（CO/AI） | https://about.getcoai.com/news/grok-ai-launches-flirty-companions-ani-and-rudi-for-30-monthly-subscribers | 2025-07 |
| R3 | 华为小艺：藏器于身，待时而动（ifanr） | https://www.ifanr.com/1669043 | 未核实 |
| R4 | HDC 2026 深度解构：鸿蒙全面向 Agent 架构演进，小艺做了这三件事（ifanr）；华为发布鸿蒙 7（ifanr） | https://www.ifanr.com/1668931 ；https://www.ifanr.com/1668803 | 2026-06 |
| R5 | 荣耀 Robot Phone 发布：9999 元起（ifanr） | https://www.ifanr.com/1674938 | 2026-08-12 |
| R6 | 全球首款机器人手机荣耀 Robot Phone 发布（科技日报） | https://www.stdaily.com/web/gdxw/2026-08/13/content_563278.html | 2026-08-13 |
| R7 | OPPO ColorOS 17 发布（凤凰科技） | https://tech.ifeng.com/c/8wURrl36Zda | 2026-09 |
| R8 | vivo OriginOS 7 发布（凤凰科技）；OriginOS 5 相关（IT之家） | https://tech.ifeng.com/c/8wSnYVoUE8h ；https://www.ithome.com/0/801/078.htm | 2026-09；2024-10-10 |
| R9 | 萌宠主题上新（IT之家，HyperOS 2 时期）；澎湃OS 4 相关（凤凰科技） | https://www.ithome.com/0/903/063.htm（该条目与萌宠主题的对应关系待核实）；https://tech.ifeng.com/c/8w43H0glaHo | 未核实；2026 |
| R10 | Samsung Galaxy S26 AI sticker tool（Android Authority）；CES 2026 Samsung（news.samsung.com） | https://www.androidauthority.com/samsung-galaxy-s26-ai-sticker-tool-3641954 ；https://news.samsung.com/sg/ces-2026-inside-samsungs-the-first-look-2026-a-vision-of-ai-companions-for-everyday-life/feed | 2026-02；2026-01 |
| R11 | WWDC 2026: Apple unveils iOS 27 with Siri AI（Mobile Marketing Reads）；WWDC 2026 Siri 重构（AppleInsider） | https://www.mobilemarketingreads.com/wwdc-2026-apple-unveils-ios-27-with-siri-ai-app-wide-intelligence-and-major-performance-upgrades/ ；https://appleinsider.com/articles/26/04/19/wwdc-2026s-focus-will-be-on-ios-27s-siri-overhaul | 2026-06；2026-04-19 |
| R12 | Grok Companion Mode 2026 Update（第三方博客）；Grok Companions explained（layer3labs） | https://aicompanionguides.com/blog/grok-companion-mode-2026-update/ ；https://www.layer3labs.io/guides/grok-companions-explained | 2026-08（均低可信） |
| R13 | AI companionship app Tolan raises $20M（GeekWire）；Tolan raises $30M（Runtime Wire） | https://www.geekwire.com/2025/ai-companionship-app-tolan-raises-20m-to-help-more-people-grow-with-a-virtual-alien-friend/ ；https://runtimewire.com/article/tolan-raises-30m-ai-companion-daily-assistant | 2025-07；2026（日期未核实） |
| R14 | Character.AI 使用时长（FoxData；The Decoder） | https://foxdata.com/en/blogs/characterai-enters-ai-microdrama-market-a-new-blueprint-for-app-growth/ ；https://the-decoder.com/character-ai-keeps-young-people-glued-to-their-smartphones-for-an-average-of-80-minutes-a-day | 2026；2025（日期未核实） |
| R15 | Ropet 融资与出货（投资界）；Ropet 获新融资（KrASIA） | https://news.pedaily.cn/202604/562592.shtml ；https://kr-asia.com/ropet-secures-new-funding-to-develop-robots-that-feel-more-like-friends | 2026-04；未核实 |
| R16 | After selling out in Japan, Casio's $429 Moflin AI pet launches in US and UK（BetaNews） | https://betanews.com/article/after-selling-out-in-japan-casios-429-moflin-ai-pet-launches-in-us-and-uk | 未核实 |
| R17 | TaoAvatar: Real-Time Lifelike Full-Body Talking Avatars（CVPR 2025，arXiv 2503.17032）；二手介绍（besthub） | https://arxiv.org/html/2503.17032v2 ；https://www.besthub.dev/articles/how-alibaba-s-taoavatar-brings-real‑time-3d-digital-humans-to-your-phone-1a465cebb34f | 2025-03 |
| R18 | Lottie vs. Rive: Optimizing Mobile App Animation（Callstack）；LottieFiles or Rive（LottieFiles） | https://callstack.com/blog/lottie-vs-rive-optimizing-mobile-app-animation ；https://lottiefiles.com/blog/lottie-animations/lottiefiles-or-rive.md | 未核实 |
| R19 | Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory（arXiv 2504.19413） | https://arxiv.org/abs/2504.19413v1 | 2025-04-28 |
| R20 | How much your boyfriend is spending on AI girlfriends（Decrypt，引 Appfigures） | https://decrypt.co/373395/how-much-your-boyfriend-spending-ai-girlfriends | 2026-07-13 |
| R21 | AI companion apps on track to pull in $120M in 2025（TechCrunch） | https://techcrunch.com/2025/08/12/ai-companion-apps-on-track-to-pull-in-120m-in-2025 | 2025-08-12 |
| R22 | AI-powered apps struggle with long-term retention（TechCrunch，引 RevenueCat） | https://techcrunch.com/2026/03/10/ai-powered-apps-struggle-with-long-term-retention-new-report-shows | 2026-03-10 |
| R23 | QuestMobile：中国 AI 原生 App 月活 4.99 亿（TechNode） | https://technode.com/2026/07/14/questmobile-chinas-ai-native-apps-reach-499-million-monthly-active-users/ | 2026-07-14 |
| R24 | google/A2UI（GitHub 官方仓库） | https://github.com/google/A2UI | 页面读取于 2026-11-03 |
| R25 | Lynx：A2UI 接入文档 | https://lynxjs.org/next/react/genui/a2ui | 页面读取于 2026-11-03 |
| R26 | Generative UI Specs（CopilotKit 文档，厂商文档） | https://docs.copilotkit.ai/ag-ui/concepts/generative-ui-specs | 未核实 |
| R27 | MCP Apps 概览（modelcontextprotocol.io） | https://modelcontextprotocol.io/extensions/apps/overview | 页面读取于 2026-11-03；规范修订 2026-01-26 |
| R28 | Add UI to your MCP server（OpenAI 开发者文档） | https://developers.openai.com/plugins/build/chatgpt-ui.md | 页面读取于 2026-11-03 |
| R29 | Gemini 3 Generative UI（BGR；PPC Land；Google Research 博客与论文，论文站 generativeui.github.io） | https://bgr.com/2030982/generative-ui-gemini-3-pro-best-new-features ；https://ppc.land/google-launches-gemini-3-with-generative-ui-for-dynamic-search-experiences/ | 2025-11 |
| R30 | WWDC26 Foundation Models year two（博客）；WWDC25 讲座 286（Apple） | https://ivanmagda-dev.pages.dev/posts/wwdc26-foundation-models-year-two ；https://developer.apple.com/videos/play/wwdc2025/286 | 2026-06；2025-06 |
| R31 | Google I/O 2026 Android 相关（Mobile Marketing Reads；Digital Applied） | https://www.mobilemarketingreads.com/google-i-o-2026/ ；https://digitalapplied.com/blog/google-ai-studio-android-apps-text-prompts | 2026-05-19/20 |

## 待核实清单

1. 各厂商是否存在本次搜索遗漏的萌宠 / 虚拟形象类功能（OPPO 小布 3D 形象、vivo 小V 形象、华为小艺形象、小米超级小爱）；需读取官方功能清单而非媒体摘要。
2. Grok Companions 3D 模式是否已下线（来源为第三方博客，2026-07-24 和 2026-08-12 两个说法）；需查 x.ai 官方公告。
3. 荣耀 Robot Phone 的 YOYO 端侧模型规模、情感交互技术实现、是否有形象功能。
4. 陪伴类产品的第三方留存数据（D1/D7/D30）；getkapex 的 5%–15% 无明确出处。
5. 星野、猫箱、筑梦岛等国内陪伴产品的月活与留存。
6. Character.AI 日均使用时长的口径差异（8–9 分钟 vs 75–80 分钟）。
7. Ropet、Moflin 等硬件的销量和留存的独立核验；Loona、Gatebox、Miko 销量。
8. TaoAvatar 手机侧 60 FPS、250k 点云、RTF 0.34 的出处（二手来源）；手机内存与功耗。
9. 手机常驻动画 / 宠物的功耗与内存实测（未找到公开资料）。
10. Open-JSON-UI 的规范原文与 OpenAI 的关系；OpenAI Apps SDK 与 Plugins 命名关系。
11. A2UI v1.0 发布时间；是否有 Android 原生（Compose）渲染器。
12. Apple iOS 27 的 Foundation Models 细节及发布状态（来源间不一致）；是否有 SwiftUI 层面的生成式 UI API。
13. HarmonyOS 是否有「小艺生成界面」或 AI 动态生成卡片的官方资料。
14. Android 官方是否有端侧生成式 UI 方案，RemoteCompose 与生成式 UI 的关系。
15. Google Research 生成式 UI 论文的评测方法与偏好比例（只读到官方自述）。
16. 生成式 UI 在手机端的首帧时延、掉帧与 WebView 内存基线（未找到公开资料）。
17. R9（IT之家「萌宠主题」条目）URL 与内容的对应关系未逐页核实。

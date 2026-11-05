# M1 调研笔记：Agent OS 商业化形态（第一部分 1.1 + 第二部分 2.1 Agent OS 侧）

> 调研日期：2026-11-03。多数来源为二手媒体报道，官方原文多数未能直接抓取（OpenAI、Samsung 官网返回 403），已逐条标注可信度。

## 摘要（10 行以内）

1. **三个点名产品已查清**：阶跃星辰 = Step AOS（STEPX Neo 智能体手机，2026-07-13 亮相，10-13 开启预订，3999 元，16GB+256GB，骁龙 8 系）；xAI 的 bot = **Grok Bot**（2026-08-11 公测，云端"自带云电脑"的常驻智能体，非手机端）；OpenAI 的 dot = **dot / dots**（2026-09-29 DevDay 发布的常驻个人智能体，GPT-6 Astra，云端，非硬件）。OpenAI 的 Ive 硬件是另一条线，已推迟到 2027 年 2 月之后，且不叫 io，也不叫 dot。
2. **主流形态两极分化**：xAI / OpenAI / Meta 走"云端常驻 Agent + 云电脑"，对终端几乎不提资源要求；Google / Apple / 国内手机厂商走"端侧小模型 + 云端大模型"，并开始用**内存门槛**划分功能。
3. **12GB 成为硬门槛**：Google Gemini Intelligence 要求 12GB+ RAM、旗舰 SoC、Nano v3+；Apple iOS 27 最强端侧模型要求 12GB 统一内存（仅 iPhone 17 Pro / Pro Max / Air）。Pixel 11 全系起步 12GB。
4. **模型内存正在变成一等公民的迹象**：Apple 的 20B 端侧 MoE 常驻闪存、仅 1–4B 专家参数入内存（AFM 3 Core Advanced），直接对应 KT2/KT3；Gemini Nano 4 Full 据报道约 5.9GB 且需整体载入内存（单一来源，待核实）。
5. **GUI 自动化路线**（豆包手机助手）靠系统特权 + SAEP 声明协议，而阶跃、华为走"系统能力 Skill/MCP 化"，两条路线对应不同的后台和并发资源画像。
6. **最大资料空白**：几乎所有厂商都不公布端侧模型的常驻内存、NPU 占用和 Agent 叠加场景下的内存余量；阶跃 Step Edge 参数量、荣耀/华为/OPPO/vivo 端侧 Agent 的内存数据均未找到。

---

# 第一部分 洞察：1.1 Agent OS 商业化形态

## 1.0 三个点名产品：指什么（先回答）

### 1.0.1 阶跃星辰（StepFun）的 Agent OS —— 有两个候选，判断为"Step AOS"为主

| 候选 | 内容 | 时间 | 判断 |
|---|---|---|---|
| **A. Step AOS（手机）** | 智能体原生操作系统，随 STEPX Neo 智能体手机、个人智能体"阶跃 Amoo"、端侧模型家族 Step Edge 一起发布 | 2026-07-13 发布；10-13 预订 | **主判断**：用户说"阶跃的 Agent OS"，最贴近的是此项，名称为 Step AOS，且它是 2026 年新发布 |
| **B. 智能座舱 Agent OS（车机）** | 千里科技 + 阶跃星辰 + 吉利汽车集团发布"面向 AI Agent 原生的下一代智能座舱 Agent OS（预览版）" | 2025-07（WAIC 2025） | **次要候选**：名字字面就是"Agent OS"，时间更早。两者是否有技术延续关系：未找到公开资料 |

**依据**：
- 界面新闻（电厂）：阶跃 7 月 13 日在上海发布 STEPX 品牌、Step AOS、阶跃 Amoo、STEPX Neo；前一天（7-12）发布 Step Edge 端侧模型家族。来源：https://www.jiemian.com/article/14762619.html（2026-07）
- IT之家：WAIC 2025 千里科技联手阶跃星辰、吉利发布智能座舱 Agent OS（预览版）。来源：https://www.ithome.com/0/870/995.htm（2025-07-27）

**Step AOS / STEPX Neo 事实表**

| 项 | 内容 | 来源与可信度 |
|---|---|---|
| 产品形态 | **独立智能体手机 + 自研 OS**；背面带 MiniLED 副屏显示 Amoo 状态；有 App 宫格与独立 Agent 空间 | Decrypt https://decrypt.co/381202/chinese-startup-stepfun-phone-ai-agent ；界面新闻 |
| OS 架构 | 称"为智能体从零构建"，长期记忆、任务调度、安全控制放在底层；据 Decrypt 报道混合 Android、Linux、RTOS 组件；手机功能（短信、应用、文件、设置）拆成可被 Agent 直接调用的"块"，经 MCP 连接。**与 Android 的确切关系：各家说法不一（待核实）** | Decrypt；ifeng https://tech.ifeng.com/c/8xCEJyLA4G3 |
| 系统层资源设计 | 界面新闻称：统一调度 CPU/GPU/NPU 异构算力，为端侧模型和系统服务提供"弹性供给"；统一语义数据层 + 高速混合数据库；TEE 内执行、每步可审计 | 界面新闻（厂商口径，无量化数据） |
| 交互 | 以意图为入口，语音/视觉/文字均可，不局限 GUI；合作应用以接口（非 GUI 模拟）接入，首批含携程、支付宝、滴滴、美团、WPS、剪映，据称近百家 | 界面新闻；Decrypt |
| 端云分工 | "云端协同"；简单指令（如设闹钟）由机内小模型执行，部分可离线，复杂多应用任务交云端大模型 | Decrypt |
| 端侧模型 | **Step Edge 家族 4 款**：Step Edge（基础）、Step Edge Audio、Step Edge GUI、Step Edge Gen；宣称 29 项评测领先；配套自研 **Step Inference NPU 推理引擎**；强调本地低延迟 tool call、全模态本地处理。**参数量：未找到公开资料** | ifeng https://tech.ifeng.com/c/8uhFrtGXlN2 ；10jqka https://stock.10jqka.com.cn/20260712/c678117043.shtml |
| 硬件 | 骁龙 8 系；先行版 **16GB+256GB**（单一来源，待核实）；闻泰科技 ODM（立讯系） | ifeng https://tech.ifeng.com/c/8xCEJyLA4G3 |
| 价格/现状 | 3999 元起，含 12 个月 STEPX Token Plan（每月 1000 亿 token，据 Decrypt）；10-13 在京东、天猫、抖音预订，10-16 首销；7 月时印奇称"亮相而非发布" | Decrypt；界面新闻 |
| 对系统资源的要求 | **未公布**。从"16GB 起步 + 自研 NPU 引擎 + 常驻 Amoo"可推测对内存余量和 NPU 常驻要求高，**推测，无数据** | - |

### 1.0.2 xAI Grok 的 bot —— 判断为 "Grok Bot"（云端常驻智能体），不是手机/硬件

- **证据**：xAI 于 **2026-08-11** 推出 Grok Bot 公测：一组"常驻 AI 队友"，每个 bot 有**自己的云端电脑**，可登录用户已有应用完成多步任务，关掉笔记本后仍持续工作；可在群聊中彼此协作。Mac/iOS 先发，Windows/Linux 桌面端有构建，Android"即将"；测试资格限 SuperGrok Heavy、Cursor Ultra、Cursor Teams Premium 订阅者，企业为候补名单。来源：https://blockchain.news/news/xai-launches-grok-bot （2026-08-11，二手媒体）；kucoin 转述 https://www.kucoin.com/news/flash/xai-launches-grok-bot-ai-agent-with-its-own-computer-for-cross-app-task-automation 。**xAI 官方发布文未能抓取（techdevnotes 链接 404），底层模型未披露。**
- **端侧部分**：未提及，全部云端。
- **其他候选（均排除，列出供核对）**：
  1. **Grok Companions**（Ani 等，2025-07 推出）：是 App 内的 3D 虚拟伴侣。有来源称 2026-07-24 宣布停用 3D 伴侣模式，另有来源称 8 月官方文档已不列出具名伴侣，**当前状态不明（待核实）**，对 G2 AI 萌宠有参考价值（交 M6）。
  2. **Grok in Tesla**（2026-02 起落地，春季更新加入"Hey Grok"唤醒词）和 **Macrohard / Digital Optimus**（2026-03，Tesla × xAI，计划跑在 Tesla AI4 芯片，有报道称已搁置）：车端/桌面 Agent，与手机无关。来源：https://invezz.com/news/2026/03/11/musk-unveils-tesla-xai-project-macrohard-to-emulate-software-companies/ （二手，待核实）
  3. Grok 手机/专用硬件：**未找到公开资料**，只有观察者猜测。
- 判断依据：用户原话"bot"与产品名 Grok Bot 完全吻合，且与 OpenAI dot 同属 2026 年 Q3 的"常驻云端 Agent"潮流。

### 1.0.3 OpenAI 的 dot —— 判断为 "dot / dots"（常驻个人智能体，软件），不是硬件

- **证据**：OpenAI DevDay 2026（**2026-09-29**，旧金山 Fort Mason）发布 dot：可"一支 dot 团队"各有目标与范围，主动执行；由 **GPT-6 Astra** 驱动；每个 dot 配**云端电脑 + 浏览器**，经插件访问应用；通过 ChatGPT、消息、电话使用；当日向 ChatGPT Pro / Business / Premium / Enterprise 开放；使用 dot 不消耗日常配额。来源：TechNews https://technews.tw/?p=1621761 （2026-09-30）；aiidelist 汇总 https://aiidelist.com/blog/openai-devday-2026-announcements.md （2026-09-30，二手）。**OpenAI 官方 recap 页面抓取 403，数字与细节待用官方页面核实。**
- **曾被误判为硬件**：发布前 Scalevise 文章（https://scalevise.com/resources/openai-dot-teaser-devday-2026-hardware-reveal/ ）基于预告语 "Your dot is ready to meet you." 猜测为硬件，DevDay 后被证伪为软件 Agent。
- **OpenAI 的硬件线（另一个问题，勿与 dot 混用）**：2025 年收购 Jony Ive 的 io；2026-02 法庭文件（Peter Welinder 宣誓声明）显示首款设备**不会早于 2027 年 2 月底发货**，且因 iyO 商标案**弃用 io 名称**；形态传闻为耳机类（代号 "Sweetpea" 等），未经 OpenAI 证实。来源：9to5Mac https://9to5mac.com/2026/02/10/jony-ives-ai-hardware-is-delayed-to-2027-and-wont-be-called-io/ ；Axios https://www.axios.com/2026/01/23/openai-device-earbuds-sweetpea-altman 。**10 月之后的更新：未找到。**

**小结**：三个点名对象中，真正"手机 OS + 端侧模型"的只有阶跃；Grok Bot 和 dot 是**云端常驻 Agent**，价值在于说明"Agent 的执行环境正在云端化（云电脑）"，对终端的直接资源要求≈0，但它们定义了用户对 Agent 的预期（24 小时、后台、主动），会倒逼端侧方案回答"为什么要端侧"。

---

## 1.1 其他玩家的代表形态

### 1.1.1 总表

| 玩家 | 代表产品（时间） | 形态 | 交互 | 端云分工 | 端侧模型与资源 | 现状 |
|---|---|---|---|---|---|---|
| **Apple** | iOS 27 + 新 Siri + AFM 3（WWDC 2026-06） | OS 内置 | 语音/系统级 Siri；开发者可换入第三方模型 | 端侧 AFM 3 Core Advanced + 云端 PCC（AFM 3 Cloud / Cloud Pro，后者用于 Agent 工具调用，PCC 扩展到 Google Cloud 的 Nvidia GPU） | **20B 稀疏 MoE 常驻闪存，每次仅 1–4B 专家参数载入内存；最强模型要求 12GB 统一内存**（iPhone 17 Pro/Pro Max/Air） | beta，随 iOS 27 |
| **Google** | Android 17 + Gemini Intelligence（2026-05-12 宣布；Pixel 11 于 2026-08-12 发布） | OS 内置 | 跨应用多步任务、屏幕自动化、主动式协助 | 端侧 Gemini Nano，无端侧能力时经 Firebase AI Logic Hybrid API 回落云端（PREFER_ON_DEVICE） | **要求 12GB+ RAM、旗舰 SoC、Nano v3+、AICore**；Nano 4 基于 Gemma 4，据单一来源 Fast≈E2B 4.2GB、Full≈E4B 5.9GB，且需整体载入内存（待核实）；Pixel 11 全系 ≥12GB | Pixel 11 已上市 |
| **三星** | Galaxy S26（2026-02）One UI 8.5 | OS 内置 + 多 Agent | "Hey Plex"/Bixby/Gemini 三个入口 | Bixby 以 Perplexity 为后端；Gemini 通用；Perplexity 研究型 | 未公开端侧内存数据；有评测称各 Agent 整合不佳 | 已上市 |
| **华为** | HarmonyOS 7 + 小艺（HDC 2026-06-12）、HMAF 2.0、小艺 Claw | OS 内置 + 开放生态 | 意图即服务；A2UI 协议动态生成界面；"Skill 化"系统能力 | 本地优先；云端推理走机密环境；小艺 Claw 可选 openPangu-2.0-Pro、DeepSeek V4、MiniMax M3（均为云端模型） | **端侧模型规格、内存、NPU 占用：未找到公开资料**。数字：2100+ 系统能力可被小艺调用；500+ Skills；2000+ 鸿蒙智能体；AI 子系统日调用 36.8 亿次 | 小艺 Claw 已开放 HarmonyOS 5.0+ 全机型（2026-06） |
| **荣耀** | YOYO 智能体 + MagicAgent；Robot Phone（2026-08-12 发布，9999 元起，8-18 首销） | 手机 OS 内置 + 机器人形态硬件 | 语音、跨应用长指令、机械云台 | MagicAgent 为 YOYO 的"大脑"，**30B MoE**（荣耀 + 复旦，2026-03-03 开源），**是否/如何端侧部署：未找到** | 骁龙 8 Gen 5 至尊版，12GB+512GB / 16GB+1TB | 已上市 |
| **OPPO** | ColorOS 16 / 16.1：AI Mind Space、小布 | OS 内置 | 记忆中心式 | 端侧助手描述仅单一来源（待核实） | 未找到 | 已上市 |
| **vivo** | 蓝心 + OriginOS 6（2025-10-10） | OS 内置 | 系统级 Agent | 端云协同 | **3B 端侧多模态推理模型**（2025-10 发布，官方口径）；内存数据未找到 | 已上市 |
| **小米** | 超级小爱 + miclaw（2026-03）+ MiMo 系列 | OS 内置 + 独立 Agent App | 手机端智能体"养龙虾" | MiMo 端云协同；2026-07 端侧模型过备案；多模型切换（HyperOS 4 推测） | 端侧参数/内存：未找到 | 迭代中 |
| **字节** | 豆包手机助手：2025-12 工程样机（努比亚 M153），**2026-09-14 消费者版**，首款努比亚 NaviX Ultra（5499 元起，9-16 开售） | 与 OEM 联合开发的系统级 Agent | AI 键唤起；**GUI 自动化**（读屏 + 模拟点击） | 大模型和 Agent 由豆包负责；**端云逐任务分工：官方未说明**；工程样机靠 INJECT_EVENTS 等系统权限；SAEP（屏幕自动化操作声明协议）让第三方 App 声明允许/限制自动化，30 天公示期 | 资源要求：未公布；"努比亚豆包手机大模型"在 7 月备案的 7 项端侧生成式服务中 | 已上市 |
| **Meta** | Muse Spark 模型（2026-04-08）、Muse 个人智能体（2026-09-08/09，美国，网站/iOS/Android/WhatsApp；Free / $20 / $100 档） | App / 云端 Agent | 对话；离开 App 后继续工作，敏感操作回请批准；独立 Sentinel 安全 Agent 审查动作 | 全云端 | 无端侧要求 | 首 12 天美加 iPhone 下载 180 万（Apptopia，二手，待核实） |
| **阶跃** | 见 1.0.1 | 独立手机 + 自研 OS | 意图驱动，MCP 块化系统能力 | 小模型端侧 + 大模型云端 | Step Edge 4 款，参数量未公布 | 预订中 |
| **OpenAI / xAI** | 见 1.0.2 / 1.0.3 | 云端 Agent | - | 全云端 | 无 | dot：2026-09 上线；Grok Bot：2026-08 公测 |

### 1.1.2 关键来源

- Apple 12GB 门槛：MacRumors https://www.macrumors.com/2026/06/08/most-powerful-on-device-ai-now-requires-iphone-17-pro-or-air/ （2026-06-08）。AFM 3 Core Advanced 的"20B / 1–4B 载入内存"来自 TNW https://thenextweb.com/news/apple-third-generation-foundation-models-afm （二手，Apple 原文待核实）。
- Apple 2025 年的上一代端侧模型：约 3B、2-bit QAT、KV Cache 共享（来自 Apple 2025 tech report，**我凭记忆引用，URL 与数字待核实**），用于说明一年内端侧从 3B 稠密跳到 20B 稀疏。
- Google：12GB+ RAM 等 8 条条件见 ecorpit 对 android.com 脚注的转述 https://ecorpit.com/gemini-intelligence-hardware-floor-android-ai-fallback-2026/ ；Nano 在 1.4 亿台以上设备运行（截至 2026-07-21，同来源）；Pixel 11 全系 ≥12GB、Tensor G6 TPU 算力 +50%、Nano 任务最多快 3.5 倍/省电 3.5 倍（Google 口径）：https://www.mobileworldlive.com/google/google-unveils-pixel-11-range/ 。Nano 4 的 4.2GB/5.9GB：https://pasqualepillitteri.it/zh/news/13395/gemini-nano-4-shoupi-shouji-gemma-4 （单一来源，待核实）；Gemma 4 E2B QAT 在移动量化格式下约 1GB（https://the-context.pages.dev/en/news/2026-06-11-gemma-4-qat-on-device/ ，二手，注意这是 Gemma 不是 Nano 4 发布包）。
- 华为：ifanr https://www.ifanr.com/1668931 （2026-06-14）；小艺 Claw 开放 https://news.10jqka.com.cn/20260624/c677692583.shtml 。
- 荣耀：IT之家 https://www.ithome.com/0/978/394.htm 、北京日报 https://news.bjd.com.cn/2026/08/13/11914236.shtml ；MagicAgent 30B 来自 pingwest https://www.pingwest.com/w/311769 （二手）。
- 豆包：36kr https://eu.36kr.com/zh/p/3984764117007111 （2026-09）。
- 小米：IT之家 https://www.ithome.com/0/977/116.htm 、https://ithome.com/0/981/378.htm 。
- 三星：https://www.androidauthority.com/samsung-galaxy-s26-ai-agents-3644131 。
- Meta：https://www.omanobserver.om/ampArticle/1195865 、https://menastartupdigest.com/?p=51131 （二手，Meta 官方未核）。

---

## 1.1.3 竞争格局（玩家 + 定位 + 优势 + 劣势 + 对我们的启示）

| 玩家 | 定位 | 优势 | 劣势 | 对我们的启示 |
|---|---|---|---|---|
| Apple | 端侧稀疏大模型 + PCC 云，隐私叙事 | 软硬件垂直；用闪存流式承载 20B MoE，已把"专家分层驻留"产品化 | 最强功能被 12GB 机型锁定，覆盖面窄；仍在 beta | 直接验证 KT2/KT3：专家缓存 + 闪存映射是主流路线；也说明内存供给是功能分层的根因 |
| Google | Android 内置 Gemini Intelligence，分层准入 | 生态与 AICore 统一接口；端云回落机制成熟 | 12GB 门槛把大量存量机排除；Pixel 与三星之外厂商适配未知 | 生态厂商必须有"模型内存可统一记账、可回收"的系统层，否则 12GB 机上模型常驻（~6GB）也会挤压应用 |
| 华为 | 系统能力 Skill 化 + 智能体生态 | 系统级调用面最广（2100+ 能力）；端侧直连 A2A | 端侧资源数据不公开；云端模型为主 | 叠加场景（Agent 调起应用）在鸿蒙上以 Skill/A2A 为主，GUI 模拟少，应用冷启动成为主要代价（推测） |
| 字节 + 努比亚 | GUI Agent，借系统特权的"外挂" | 不依赖应用适配，通用性强，已量产 | 靠特权与风控博弈；第三方应用拒绝则失效；后台操作占前台 | GUI Agent 本期明确不做，但它是"Agent 调起应用"叠加场景的真实压力源（频繁冷启动与切换） |
| 阶跃 | OS-Agent-终端闭环 | 端侧模型 + 自研 NPU 引擎 + 自研 OS 一体化 | 体量小、生态靠合作、硬件依赖 ODM；Android 关系不清 | 创业公司已把"弹性调度异构算力给端侧模型"写进 OS 叙事，提示大厂需尽快有量化的内存/IO 指标 |
| 荣耀 / 小米 / vivo / OPPO | 跟随式端云协同 | 出货量，渠道 | 端侧资源与模型信息少 | 可作为同行对标，但公开数据不足 |
| OpenAI / xAI / Meta | 云端常驻 Agent + 云电脑 | 模型能力强，不受端侧资源限制 | 隐私、成本（每个 Agent 一台云电脑）、延迟、离线不可用 | 端侧 Agent 的差异化是"低延迟、隐私、离线、与本机应用深度叠加"，必须避开与云端常驻 Agent 比规划能力 |

---

## 1.1.4 趋势（趋势一句话 + 事实依据 + 对我们的影响）

**趋势一：端侧 Agent 的准入门槛正在从算力转为内存，12GB 成为分水岭。**
- 依据：Google Gemini Intelligence 要求 12GB+ RAM（android.com 脚注，ecorpit 转述，2026-05）；Apple iOS 27 最强端侧模型要求 12GB（MacRumors，2026-06-08）；Pixel 11 全系 ≥12GB（2026-08-12）；STEPX Neo 先行版 16GB（2026-10）；iPhone 17 标准版 8GB 被排除。
- 影响：两大平台都用"内存"而不是"NPU TOPS"划线，说明内存供给是 Agent OS 的第一约束，支撑立项总构想"模型内存成为一等公民"。同时它制造"12GB 机型也不够用"的叠加场景问题。

**趋势二：端侧模型从稠密小模型走向稀疏大模型 + 闪存分层驻留。**
- 依据：Apple AFM 3 Core Advanced 20B，全量放闪存、每次仅 1–4B 专家参数入内存（TNW，2026-06）；荣耀 MagicAgent 30B MoE（2026-03，是否端侧未知）；Gemini Nano 4 基于 Gemma 4 的 E2B/E4B（"E"为有效参数，含逐层嵌入，Gemma 4 E2B QAT 约 1GB，二手）。
- 影响：直接支撑 KT2（专家缓存应泛化为稀疏权重分层）与 KT3（闪存映射加载、NPU 侧文件映射）。

**趋势三：Agent 执行环境两极分化——云端常驻 Agent（云电脑）与端侧系统级 Agent 并存。**
- 依据：Grok Bot（2026-08-11）、OpenAI dot（2026-09-29）、Meta Muse（2026-09）均为云端、每个 Agent 一台云电脑；手机侧 Google / Apple / 华为 / 阶跃走端云协同，简单任务本地、复杂任务云端（Decrypt、Google PREFER_ON_DEVICE）。
- 影响：端侧任务集中在"低延迟、隐私、离线、与前台应用叠加"。S1（云转端的代价与收益评估）要把"云端常驻 Agent 的体验基准"作为对照。注意"端侧后台 Agent（2028 年前）"已划为不做，与此趋势一致。

**趋势四：系统把应用能力"工具化"（MCP / Skill / A2UI / SAEP），Agent 与应用叠加成为常态，GUI 模拟退为兜底。**
- 依据：Step AOS 以 MCP 暴露系统功能块；华为 HMAF 2.0 系统能力 Skill 化（2100+）、A2UI 动态生成界面；豆包 GUI 自动化 + SAEP 声明协议；Doubao 样机靠系统特权。
- 影响：Agent 既会通过 API 无界面调用应用，也会拉起应用界面，造成应用冷启动、.so 页争用、后台应用被回收后重新拉起，支撑 KT1-a/b/c；生成式 UI（A2UI）支撑 G4（交 M6）。

**趋势五：形态分化为"OS 内置"与"整机重构"，新玩家用整机重构抢占叙事，但出货规模仍小。**
- 依据：阶跃 STEPX Neo 3999 元、荣耀 Robot Phone 9999 元、努比亚 NaviX Ultra 5499 元；OpenAI 硬件推迟到 2027 年 2 月后。
- 影响：2027 年立项窗口里，大厂主阵地仍是在 Android/鸿蒙内核上改造，因此内核层的内存和 IO 改进（本立项范围）才是可落地的差异化，而不是另起一个 OS。

## 对立项的启示（第一部分）

1. 总构想"模型内存一等公民、统一记账、可回收、可共享"有直接的行业佐证：Apple 用闪存承载 20B MoE、Google 用 12GB 门槛、阶跃宣称"弹性调度"，但**没有任何一家公开统一记账和回收机制**，这是我们可占的位置（支撑总构想、KT2、KT3）。
2. 可用 12GB 机型做立项基线：系统常驻约 3–4GB（估算）+ 模型常驻（Nano 4 Full 约 5.9GB，单一来源）≈ 留给应用的不足 2–3GB，**叠加场景下应用被回收是必然**，支撑 KT1-a/b/c。
3. 云端常驻 Agent 已被 OpenAI / xAI / Meta 抢先，端侧立项应强调"叠加场景体验"，不与之比后台自治（也与"明确不做"边界一致）。

---

# 第二部分 2.1 场景与需求（仅 Agent OS 侧）

> 说明：以下指标目标值多数为**估算或建议**，依据已逐项标明；没有公开基线的标"未找到公开资料"。评审时需 M2/M3/M4 用实测或仿真校准。

## 基线设定（估算，供各场景引用）

| 项 | 取值 | 依据 |
|---|---|---|
| 2027 主力旗舰内存 | 12–16GB | Pixel 11 全系 ≥12GB；STEPX Neo 16GB；荣耀 Robot Phone 12/16GB；Gemini Intelligence 门槛 12GB |
| 系统 + 常驻服务 | 约 3–4GB | **估算**，缺公开数据；需 M2 用 `dumpsys meminfo` / Perfetto 在真机核实 |
| 常驻端侧模型（量化后） | 1–6GB | Gemma 4 E2B QAT 约 1GB（二手）；Nano 4 Full 约 5.9GB（单一来源）；Apple 20B MoE 仅 1–4B 入内存，4-bit 约 0.5–2GB（**估算：参数数 × 0.5 字节**） |
| 留给前台应用 + 后台 | 12GB − 3.5GB − 模型 | 模型 1GB 时约 7.5GB；模型 6GB 时约 2.5GB（**估算**） |

## 场景 S-A：前台应用中唤起 Agent（"一边用一边问"）

- **场景**：用户正在刷视频/地图/购物，长按电源键或唤醒词唤起 Agent，询问或让它基于当前屏幕处理（总结、比价、翻译）。对应现实形态：Gemini 屏幕上下文、Siri 新版、小艺、豆包 AI 键。
- **用户需求**：前台应用不卡、不被杀；Agent 马上响应；返回应用后状态还在。
- **系统压力**：端侧模型需加载或唤醒（若未常驻，需 IO 载入数 GB 权重），同时前台应用内存被挤压，触发 LMKD / 回收（Android 术语；iOS 为 Jetsam 与 compressed memory，鸿蒙为其内核机制，**公开资料不足**）。
- **建议体验指标（待校准）**：

| 指标 | 建议目标 | 依据 |
|---|---|---|
| Agent 首 token 时延（端侧小模型） | ≤1s（热）/ ≤3s（冷，含模型载入） | **估算**：交互式语音助手常规期望；无公开厂商基线（未找到公开资料） |
| 前台应用掉帧率增量 | 唤起后 3s 内 jank 增量 ≤1 个百分点 | 建议值，无公开数据 |
| 前台应用存活率 | 唤起 Agent 后前台应用 0 次被杀 | 建议值 |
| 模型冷载入时间 | 3–6GB 权重 ≤2s（需 ≥ 约 1.5–3GB/s 有效读带宽） | **估算**：6GB ÷ 2s = 3GB/s；UFS 4.x 顺序读理论约 4GB/s 量级（带宽数据由 M3 核实） |

## 场景 S-B：Agent 调起应用完成任务（叠加主场景）

- **场景**：用户说"帮我订明天去上海的高铁并加到日历"，Agent 依次拉起 12306、日历、支付类应用；或经 MCP/Skill 无界面调用应用能力，只在需要确认时拉起界面。对应：Step AOS（MCP 块）、HarmonyOS 小艺 Skill、豆包 GUI 自动化。
- **用户需求**：多应用顺序/并行执行快；每个应用冷启动不明显慢；任务完成后不留下一堆后台进程。
- **系统压力**：连续拉起多个应用（冷启动）→ 触发 .so 文件页争用（KT1-a）；Agent 与应用叠加时匿名页占用大，需换出旧后台应用（KT1-c）并在切回时预取（KT1-b）；豆包类 GUI 自动化还会长期占用前台应用。
- **建议指标**：

| 指标 | 建议目标 | 依据 |
|---|---|---|
| 单应用冷启动时延 | 叠加（模型常驻）下相对无 Agent 基线劣化 ≤10% | 建议值；基线需 M2 实测 |
| 多应用任务端到端时延（3 应用链） | 较未优化降低 20–30% | 建议区间，待仿真（S1/S2）校准 |
| 内存余量 | 任务期间可用内存（MemAvailable）不低于低水位线的 1.5 倍 | 建议值 |
| 应用被回收后热启动比例 | ≥80%（切回不重新冷启动） | 建议值 |

## 场景 S-C：长对话/长任务（上下文累积）

- **场景**：Agent 带工具调用、网页/文档内容、历史记忆，上下文达 8K–32K token，持续多轮；用户中途切去别的应用再切回。
- **用户需求**：多轮不变慢、不丢上下文；切走再回来不用重算。
- **系统压力**：KV Cache 随上下文增长占用内存（KT2）。估算：KV 字节 ≈ 2 × 层数 × KV 头数 × 头维度 × 精度字节 × token 数。例如 **假设** 28 层、8 个 KV 头、头维度 128、FP16：每 token 约 2×28×8×128×2 = 114,688 字节 ≈ 112KB，32K token ≈ 3.6GB（**估算，模型参数为假设，非某款实际模型**；量化 INT4 约 0.9GB；Apple 等采用 KV 共享可进一步降低）。这说明长上下文会和模型权重一起吃掉 12GB 机型的大部分余量，需由 M3 用实际模型核实。
- **建议指标**：长上下文（≥16K）下首 token 时延不劣化超过 2 倍；KV 占用上限可配置并随内存压力回收。

## 场景 S-D：端云切换（离线/弱网/隐私）

- **场景**：地铁无网时，Agent 回落到端侧小模型执行简单任务；有网时复杂任务上云（Google PREFER_ON_DEVICE、阶跃"简单本地、复杂云端"）。
- **用户需求**：切换无感；离线可用的任务集合明确；功耗和发热可接受。
- **系统压力**：端云路由与云转端的性能、功耗、成本评估（S1）。端侧每 token 能耗与云侧成本数据由 M4 补。
- **建议指标**：切换额外时延 ≤500ms（建议值）；端侧持续推理 5 分钟表面温度升高与功耗预算由 M4 量化。

## 场景 S-E：Agent 并行化（单个 Agent 内部）

- **场景**：单个 Agent 同时发起多个工具调用、子任务并行、预取下一步（对应 S2）。
- **用户需求**：多步骤任务总时延下降。
- **系统压力**：端侧 decode 受内存带宽限制，并行子任务共享 KV/权重，调度在 CPU/GPU/NPU 间流水。
- **建议指标**：并行化后任务总时延较串行降低 ≥20%（建议值，待 S2 仿真给出区间）。

## 场景对"当前系统满足不了"的初步判断（详细瓶颈在 2.2，由 M2/M3 展开）

1. **模型常驻与应用共存**：12GB 机型模型常驻 1–6GB 后，余量骤降，LMKD/Jetsam 回收变频繁（推测，需实测）。
2. **冷启动链**：Agent 连续拉起应用时的冷启动与 .so 页争用，行业**未找到公开的量化数据**，是立项需自建基线的空白。
3. **模型加载**：权重 GB 级载入受 IO 带宽限制，且 NPU 侧文件映射需要额外内存（KT3，M3 核实）。

## 对立项的启示（第二部分）

- 立项最需要的证据不是"Agent 有多火"，而是"12GB 机型上 Agent + 应用叠加的内存余量和冷启动劣化数据"。此数据业界无公开发表，**建议立项前先在自有真机上采集一份基线**（支撑 S1 的"真机可观测性与体验指标、标准负载集"）。
- 场景 S-B 是最能体现差异化的主场景，对应 KT1-a/b/c；S-C 对应 KT2；S-A 对应 KT3。

---

# 参考资料

| # | 标题 | URL | 日期 |
|---|---|---|---|
| 1 | 阶跃星辰"造手机"背后（界面新闻/电厂） | https://www.jiemian.com/article/14762619.html | 2026-07 |
| 2 | 千里科技联手阶跃、吉利发布智能座舱 Agent OS（IT之家） | https://www.ithome.com/0/870/995.htm | 2025-07-27 |
| 3 | Chinese Startup StepFun Launches a Phone Built Around an AI Agent（Decrypt） | https://decrypt.co/381202/chinese-startup-stepfun-phone-ai-agent | 2026-10 |
| 4 | 阶跃终端首款智能体手机 STEPX Neo 先行版（凤凰科技） | https://tech.ifeng.com/c/8xCEJyLA4G3 | 2026-10 |
| 5 | 阶跃星辰发布 Step Edge 端侧模型全家桶 | https://tech.ifeng.com/c/8uhFrtGXlN2 ；https://stock.10jqka.com.cn/20260712/c678117043.shtml | 2026-07-12 |
| 6 | xAI Launches Grok Bot（blockchain.news） | https://blockchain.news/news/xai-launches-grok-bot | 2026-08-11 |
| 7 | xAI Launches Grok Bot（KuCoin 快讯） | https://www.kucoin.com/news/flash/xai-launches-grok-bot-ai-agent-with-its-own-computer-for-cross-app-task-automation | 2026-08 |
| 8 | OpenAI DevDay 2026 发布 dot（TechNews） | https://technews.tw/?p=1621761 | 2026-09-30 |
| 9 | OpenAI DevDay 2026: 25 Biggest Announcements（aiidelist） | https://aiidelist.com/blog/openai-devday-2026-announcements.md | 2026-09-30 |
| 10 | OpenAI "Dot" teaser（Scalevise，推测，已被证伪为硬件） | https://scalevise.com/resources/openai-dot-teaser-devday-2026-hardware-reveal/ | 2026-09 |
| 11 | Jony Ive's AI hardware is delayed to 2027（9to5Mac） | https://9to5mac.com/2026/02/10/jony-ives-ai-hardware-is-delayed-to-2027-and-wont-be-called-io/ | 2026-02-10 |
| 12 | OpenAI "secret" new device（Axios） | https://www.axios.com/2026/01/23/openai-device-earbuds-sweetpea-altman | 2026-01-23 |
| 13 | Grok Companions 相关报道 | https://decrypt.co/330097/artificial-gooning-intelligence-elon-musk-xai-waifu-companions-grok | 2025-07 |
| 14 | Macrohard / Digital Optimus（Invezz） | https://invezz.com/news/2026/03/11/musk-unveils-tesla-xai-project-macrohard-to-emulate-software-companies/ | 2026-03-11 |
| 15 | Apple 最强端侧 AI 需 iPhone 17 Pro 或 Air（MacRumors） | https://www.macrumors.com/2026/06/08/most-powerful-on-device-ai-now-requires-iphone-17-pro-or-air/ | 2026-06-08 |
| 16 | Apple 第三代 Foundation Models（TNW） | https://thenextweb.com/news/apple-third-generation-foundation-models-afm | 2026-06 |
| 17 | Gemini Intelligence 12GB 门槛（ecorpit） | https://ecorpit.com/gemini-intelligence-hardware-floor-android-ai-fallback-2026/ | 2026-07/08 |
| 18 | Google Pixel 11 发布（Mobile World Live） | https://www.mobileworldlive.com/google/google-unveils-pixel-11-range/ | 2026-08-12 |
| 19 | Gemini Nano 4 / Gemma 4（pasqualepillitteri） | https://pasqualepillitteri.it/zh/news/13395/gemini-nano-4-shoupi-shouji-gemma-4 | 2026 |
| 20 | Gemma 4 QAT 端侧推理 | https://the-context.pages.dev/en/news/2026-06-11-gemma-4-qat-on-device/ | 2026-06-11 |
| 21 | Samsung Galaxy S26 AI agents（Android Authority） | https://www.androidauthority.com/samsung-galaxy-s26-ai-agents-3644131 | 2026-02 |
| 22 | HDC 2026 深度解构（爱范儿） | https://www.ifanr.com/1668931 | 2026-06-14 |
| 23 | 小艺 Claw 全机型开放 | https://news.10jqka.com.cn/20260624/c677692583.shtml | 2026-06-24 |
| 24 | 荣耀 Robot Phone 发布 | https://www.ithome.com/0/978/394.htm ；https://news.bjd.com.cn/2026/08/13/11914236.shtml | 2026-08-12/13 |
| 25 | 荣耀 MagicAgent 30B（PingWest） | https://www.pingwest.com/w/311769 | 2026-03 |
| 26 | 豆包手机助手消费者版（36kr） | https://eu.36kr.com/zh/p/3984764117007111 | 2026-09 |
| 27 | 小米 MiMo / 超级小爱 / miclaw（IT之家） | https://www.ithome.com/0/977/116.htm ；https://ithome.com/0/981/378.htm | 2026-07 |
| 28 | vivo 开发者大会 2025（3B 端侧模型） | https://www.stdaily.com/web/gdxw/2025-10/11/content_413599.html | 2025-10-11 |
| 29 | Meta Muse 个人智能体 | https://www.omanobserver.om/ampArticle/1195865 ；https://menastartupdigest.com/?p=51131 | 2026-09-09 |

# 待核实清单

1. OpenAI dot 的官方细节（模型名 GPT-6 Astra、云电脑、套餐）：OpenAI 官方 recap 页面 403，现有来源均为二手；需读官方原文。
2. xAI Grok Bot 官方发布文与底层模型；Grok Companions 是否已停用（来源冲突）。
3. OpenAI 硬件 2026-02 之后的进展（特别是 2026-10 的更新）：未找到。
4. Step AOS 与 Android 的关系；Step Edge 各模型参数量、常驻内存、NPU 占用；STEPX Neo 的 SoC 具体型号和内存规格（16GB 为单一来源）；车机 Agent OS 与手机 Step AOS 是否有延续。
5. Gemini Nano 4 的 4.2GB / 5.9GB 与"必须整体载入内存"（单一来源）；Gemini Intelligence 哪些功能纯端侧、哪些走云。
6. Apple AFM 3 Core Advanced 的 20B / 1–4B 数字需对照 Apple 官方原文；Apple 2025 tech report（3B、2-bit QAT、KV 共享）凭记忆引用，URL 与数字需核实。
7. 华为、荣耀（MagicAgent 是否端侧部署）、OPPO、vivo、小米、三星的端侧 Agent 内存 / NPU 占用：未找到公开资料。
8. 豆包手机助手的端云逐任务分工、系统资源开销：官方未披露。
9. Meta Muse 的发布日期（9 月 8 日与 9 日说法不一）及官方说明；180 万下载数据为二手。
10. 第二部分 2.1 的所有"建议目标"和系统常驻内存 3–4GB、KV 占用示例均为估算 / 假设，需真机实测或 M2/M3/M4 校准。
11. 本笔记未覆盖 Apple 在 iOS 27 中的 Agent 工具调用（App Intents）细节，以及 Meta 智能眼镜、车机形态的端侧资源要求。

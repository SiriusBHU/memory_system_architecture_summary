# D1 商业形态深度补充：三个产品拆解、云端 Agent 单位经济性、系统级 Agent 对比、12GB 门槛、GUI 路线摩擦

> 调研日期：2026-11-04。承接 `M1-agentos-commercial.md`，已有事实不重复。多数来源为二手媒体或第三方博客；官方原文（OpenAI、xAI、Apple、Huawei）本轮均未直接抓到，除 Android 开发者博客与 Anthropic 工程博客外都标「二手」。标注约定：**估算** = 我推算并写出算式；**待核实** = 单一或二手来源；**判断** = 我的结论。

## 要点摘要

1. **M1 有一处需纠错**：Grok Bot 的多个 bot 是**共用一台**账号级持久云 VM，不是「每个 bot 一台云电脑」（Vellum，2026-08-20，竞品所写，待核实）。bot 之间不是安全边界。
2. **dot 不是大众产品**：首个 dot 随 ChatGPT Pro（$100/$200/$500 月）和 Business Premium 附赠；Free/Go/Plus 不含（eesel，二手，有来源冲突）。新增 $500/月档，称 25 倍 Plus 用量（reworked，2026-10-01）。
3. **云端常驻 Agent 的单位成本估算 $70–300/用户/月**（算式见第 2 节），而公开定价锚点是 $100–500/月；大众档 $20（Plus、Meta Muse）装不下，OpenAI 的 Plus 不含 dot 是同一结论的市场证据。
4. **Anthropic 一手数据**：agent 约为 chat 的 4 倍 token，多 agent 约 15 倍；BrowseComp 中 token 用量单项解释 80% 性能方差（Anthropic 工程博客，已抓取原文）。
5. **E2B 2vCPU/4GiB 常驻约 $121/月**（官方单价 $0.0504/vCPU-h、$0.0162/GiB-h，估算 730h），Browserbase 浏览器时 $0.10–0.12/h。
6. **STEPX Neo 开售（10-16）后无销量、无独立评测**：厂商称无出货目标；分析师称「每家只开了一扇窗」：支付宝接入 300+ 服务，美团仅跑腿，微信缺席（每日经济新闻，2026-10-14）。
7. **豆包手机二代**（9-16 开售，12GB+512GB 5999 元）：预约 36 万+，发布会称端到端任务成功率 >80%；但 150 余款应用（含微信、支付宝、淘宝、美团）拒绝 GUI 自动化（北京日报，2026-10-14）。
8. **Counterpoint 2026-06**：GenAI 手机占出货 2025 年 36%、2026 年 45%、2027 年 52%；2026 总出货 10.8 亿台，同比 -13.9%。≥12GB 占比：**未找到公开资料**。
9. **内存成本冲击**：2026Q2 手机内存价格环比 +80%（Counterpoint）；12GB+256GB 采购价约 500→2200 元（博主，待核实）；入门/中端/旗舰 BOM 同比约 +70%/+52%/+50%。
10. **Google 两路并行**：无需改代码的屏幕自动化 + MCP 式 AppFunctions（25 个应用用例，KakaoTalk 预览，2026-05-12，一手）；Gemini Intelligence 8 条门槛含 12GB+ RAM。
11. **华为 HMAF 2.0**：2100+ 系统能力、200+ 系统数据、500+ 生态 Skill、2000+ 智能体，复杂任务成功率 >90%（厂商口径）；端侧 30B 模型预告秋季上 Kirin（激活 2B 待核实）。
12. **接口化已是行业共识**：LatePost 称新豆包手机不再 GUI 而依赖应用方 MCP（07-17）；荣耀 MagicOS 11 用 MCP/A2A + GUI 兜底；微信与华为/荣耀/小米/OPPO/vivo 谈 A2A（2026-06，二手）。

---

## 1. 三个点名产品深度拆解

### 1.1 阶跃 Step AOS / STEPX Neo

| 维度 | 已查到的事实 | 来源与可信度 |
|---|---|---|
| 产品定义与入口 | 「大模型原生智能体手机」；双入口（传统 App 宫格 + 独立 Agent 空间）；Amoo 为首页；背面横向双摄 + MiniLED 副屏显示后台任务进度；语音为核心，带 6 麦听觉增强；全局记忆 | 每日经济新闻 2026-10-14；Decrypt |
| 硬件 | 骁龙 8 系（型号未标）、16GB+256GB；电池、屏幕未披露 | 凤凰科技 2026-10-13 |
| OS 与 Android 关系 | Decrypt 称混合 Android、Linux、RTOS 组件，同时厂商称「从零为智能体构建」。**与 AOSP 的确切关系：未找到官方说明**。另有 7-13 报道称业内人士说它与魅族「没啥关系」，说明外界曾猜测其供应链 | Decrypt 2026-10；同花顺 2026-07-13 |
| 端侧模型 | Step Edge 家族 4 款（基础/Audio/GUI/Gen），配 Step Inference NPU 引擎。**参数量、常驻内存：未找到公开资料**。Amoo 的常驻方式：未找到 | M1 已有 |
| 云侧 | 复杂多应用任务交云端大模型；同期有 Step 5 Preview（总 600B、激活 27B、1M 上下文）和开源 Step 3.5 Flash（Apache 2.0） | Decrypt |
| 应用接入 | 以 MCP/A2A 调用第三方服务，非 GUI 模拟；「近百家」合作企业；支付宝已接入 **300+ 服务**（可经「阿宝」下盒马、星巴克小程序）；美团**仅开放跑腿**，外卖未开；淘宝闪购可用；腾讯侧只有 WorkBuddy、企业微信、微信读书，**微信本体缺席** | 每日经济新闻 2026-10-14；量子位 2026-10-29（支付宝神券、「支付宝 AI 付」） |
| 记忆 | Amoo 两套记忆：用户事实/习惯/偏好；任务执行经验。官方称检索最快 15ms（厂商口径，未验证）。存放位置（端/云）：未披露 | Decrypt；smartworld.it |
| 安全 | TEE 内执行、每步可审计（厂商口径，见 M1） | M1 |
| 商业模式 | 3999 元为「软硬模三位一体全栈价」：手机 + Step AOS + Step Studio 开发工具 + 12 个月 STEPX Token Plan（每月 1000 亿 token，Decrypt）；第 13 个月起的价格**未公布**。Step Studio 向开发者开放传感器、摄像头、背屏 | 凤凰科技；Decrypt |
| 销量/用户 | 7 月时终端总裁称**没有设定出货目标**，印奇称第一阶段不单纯追求出货量但要上规模。10-16 首销后**销量：未找到公开资料** | 搜狐 2026-07；同花顺 |
| 口碑/评测 | 开售后**独立评测：未找到公开资料**。只有 WAIC 现场演示印象（延迟低）和 10-29 的厂商稿「发布两周首次升级」。分析师田丰：这是「一次合格的开发者版发布」，主要瞄准创客，普通消费者难为代办支付 3999 元 | 每日经济新闻；量子位 |

**分析：这说明什么（判断）**：阶跃的差异化不在模型而在「应用接入的广度」，而首批数据显示头部应用只开窗口不开全门（微信缺席、美团仅跑腿）。3999 元里含 12 个月 1000 亿 token/月，说明厂商把云端推理成本打包进硬件价格，等于承认云侧 token 是长期成本项。对我们：它是端云协同样本而非端侧样本，端侧模型内存数据缺失，不能作为内存需求的参照。

### 1.2 xAI Grok Bot

| 维度 | 已查到的事实 | 来源与可信度 |
|---|---|---|
| 定义与入口 | 常驻「AI 队友」，在持久云 VM 上做多步任务，关电脑后继续跑；可命名多个 bot 并互相协作；桌面端（macOS、Windows）+ iPhone 伴侣 App；**Android**：Vellum（08-20）未提及，另一篇俄语二手稿称 2026-09-02 已开放 Android，需订阅资格（待核实） | Vellum；postium.ru |
| 云电脑 | 「账号级持久云 VM」，有浏览器、文件系统、终端。**CPU/内存/磁盘规格未披露**。多个 bot 共享同一台用户级机器，**不是**各自独立沙箱 | Vellum（竞品所写，偏促销） |
| 能做的任务 | 浏览无 API 的网站、读写文件、执行终端命令、调用连接的服务、MCP 工具、定时任务、多 bot 协作 | Vellum |
| 应用接入 | Gmail、Google Calendar/Drive、OneDrive、Outlook、Teams、SharePoint、Salesforce；自定义 MCP 服务需公网可达或隧道；另可登录浏览器会话 | Vellum |
| 模型 | 仅 xAI 模型（经 xAI/Cursor 路径），具体型号未披露 | Vellum |
| 记忆与权限 | 记忆、文件、浏览器会话、偏好跨会话持久；xAI **不公开**保留时长、导出、单条记忆的查看或删除；权限有「允许一次/拒绝/始终允许」、自动审核规则、敏感步骤安全移交 | Vellum |
| 价格 | 14 天试用后**单独订阅 $200/月**；SuperGrok Heavy、Cursor Ultra、Cursor Teams Premium 订阅者附带。Heavy 价格各源写 $300 或 $200–300，Vellum 称其单独价格不公开（**待核实**）。有一篇 SuperGrok 低价档（$30）也含 Bot 的说法为孤证，倾向不采信 | Vellum；wikidocs（403 未能抓取，仅搜索摘要） |
| 用量限制 | 未文档化 | Vellum |
| 口碑 | 可靠性、延迟、失败恢复「无独立来源测试」；一位付费用户说 Heavy 的主要价值是附赠的 Cursor Ultra（单买 $200/月）而不是 Grok Bot | Vellum；gitconnected 付费墙文章摘要 |
| 用户量 | 未找到公开资料 | - |

**分析：这说明什么（判断）**：Grok Bot 的定价锚点 $200–300/月已经把大众排除；共享 VM 的设计既是降本手段，也说明云 Agent 厂商在单用户算力预算上精打细算。它和 Android 手机的关系只是「可作为远程遥控入口」，不是端侧形态。

### 1.3 OpenAI dot（dots）

| 维度 | 已查到的事实 | 来源与可信度 |
|---|---|---|
| 定义与入口 | 常驻 Agent，每人先有一个主 dot，后续可加；通过 ChatGPT 文本/语音、Slack、Teams 使用；**安装设置仅限桌面** | reworked 2026-10-01；eesel |
| 架构 | 每个 dot 有自己的云端 Linux 电脑 + Chrome，用户可观看或接管；GPT-6 Astra；经 ChatGPT 的插件体系连接 **4000+ 应用**；可发起 Codex 云任务 | eesel（二手，作者自称未亲测） |
| 权限与安全 | 独立「自动审核」在环境外检查计划动作；主动后台研究在代码层强制只读；密码与付款永远回到用户；2FA 暂停等用户输入；自定义规则分 4 级，不能取消强制确认。OpenAI 承认提示注入防护「不能消除风险」 | eesel |
| 系统卡数据 | 5 步任务链越权率 8.6%，10 步链 19.7%；拦截全部 16,600 次模拟邮件攻击（OpenAI 内部数据，二手转述） | cryptobriefing 2026-10-27 |
| 记忆 | 单条记忆不可查看/编辑/删除，只能删除整个 dot；断开应用不清除已学内容 | eesel |
| 价格与档位 | 无单独定价。首个 dot 随 ChatGPT Pro（$100/$200/$500）与 Business Premium 附赠；Free/Go/Plus 不含；企业/教育/医疗为 beta 且需管理员开启；Pro 不含 EEA、瑞士、英国。**$500 档**称 25 倍 Plus 额度，含 Ultrafast（Codex 最高 8 倍速）。另一摘要称新订阅 Pro 200 为 Plus 的 10 倍（原 20 倍），新额度自 10-30 起生效（孤证，待核实）。也有来源说 Plus 可用，**冲突**，以多数来源为准 | reworked；eesel；搜索摘要 |
| 用量 | 与 dot 的对话**不**计入常规额度；dot 派给 Codex/ChatGPT Work 的任务计入。发布期之后的限额未公布 | eesel |
| 模型 API 价 | GPT-6 Astra API：输入 $10、缓存输入 $1、输出 $50 /百万 token（OpenAI 帮助中心表经搜索摘要，另有来源称 Pro 行价格未单列，待核实）。发布日多数来源为 2026-09-03 | 搜索摘要 |
| 口碑 | 独立测试（未具名）：十项商务任务均分 8.8，**五个 Agent 中排第三**，Claude Cowork 9.3 第一，体验分 9.2；弱点是越界。另一评测：网站更新与视频剪辑可完成，线上跑腿被「按住验证」卡住。DevDay 现场演示曾卡住。早期用户反馈慢、确认提示多 | cryptobriefing；neoteo；newsbytes |
| 与 Operator/Agent/Pulse 关系 | 所查来源**均未说明**。可参照的前代：ChatGPT Agent 的额度为 Pro 每月 400 条、Plus 40 条（2025 发布期数字，可能已变）；Operator 为 Pro 专享。 | BGR 等搜索摘要 |
| 硬件线 | 10 月后无新进展：未找到公开资料（延续 M1 结论） | M1 |

**分析：这说明什么（判断）**：OpenAI 选择不把 dot 给 $20 的 Plus，而 Plus 的 ChatGPT Agent 额度仅为 Pro 的 1/10，这是云端常驻 Agent 成本压力的直接市场表现。dot 的越界率 8.6%–19.7% 说明长任务链可靠性仍是瓶颈，而不是内存或算力，应避免把「端侧缺内存」说成 Agent 落地的唯一障碍。

---

## 2. 云端常驻 Agent 的单位经济性（估算）

### 2.1 输入数据

| 项 | 数值 | 来源 |
|---|---|---|
| E2B 沙箱单价 | $0.000014/vCPU-秒（$0.0504/vCPU-h）；内存 $0.0162/GiB-h；Pro 计划 $150/月 | beri.net 2026-10-08；E2B 文档（经搜索摘要） |
| Modal | $0.0710/vCPU-h；$0.0240/GiB-h | beri.net |
| Browserbase | Developer $20/月含 100 浏览器时，超出 $0.12/h；Startup $99/月含 500 时，超出 $0.10/h；代理流量另计约 $12/GB | scrapegraphai 等（聚合站，待核实） |
| Agent token 倍数 | agent ≈ chat 的 4 倍；多 agent ≈ 15 倍 | Anthropic 工程博客（一手） |
| Manus 单任务成本 | 付给 Anthropic 平均约 $2/任务 | The Information（匿名消息源，待核实） |
| Claude Code 实际 | $13/开发者/活跃日；90% 用户日均 <$30 | 引自 Anthropic 成本文档（二手转引） |
| GPT-6 Astra API | $10 入 / $1 缓存入 / $50 出 每百万 token | OpenAI 帮助中心（二手） |

### 2.2 估算过程

**(a) 沙箱/云电脑，常驻 2vCPU/4GiB（估算）**
- E2B 零售价：(2×0.0504 + 4×0.0162)×730h = (0.1008+0.0648)×730 ≈ **$121/月**（外加 $150 平台费）。
- 若厂商自有机房，成本可比零售低数倍；本次未找到公开的 hyperscaler 小规格 VM 单价，暂按 $30/月估计下限（**估算，凭记忆的约 $0.04/h 量级，待核实**）。
- 浏览器按需计时：每天 4h×30 天 = 120h，×$0.10~0.12 = **$12–14/月**。
- 因此计算部分**区间 $12–121/月**。

**(b) 单任务 token 成本（估算）**
- 设一个浏览器/办公类 Agent 任务：输入上下文累计 30 万 token（多轮重复读上下文），输出 2 万 token。
- 按 Astra 价：全缓存命中 0.3M×$1 + 0.02M×$50 = $0.3+$1.0 = **$1.3**；全不缓存 0.3M×$10 + $1.0 = **$4.0**。
- 与 Manus $2/任务量级一致，作为交叉验证。取 $1.3–4，中值 $2。

**(c) 每月任务量**
- 「常驻」按每天 1–3 个有价值任务：30–90 任务/月。

**(d) 合计**
- 低：30×$1.3 + $12 ≈ **$51**；中：60×$2 + $60 ≈ **$180**；高：90×$4 + $121 ≈ **$481**。
- 取常见区间约 **$70–300/月/用户（估算）**。多 agent 协作按 Anthropic 15 倍 token，会再上浮数倍，这里未计入。

### 2.3 对照定价

| 产品/档位 | 月费 | 与估算成本 |
|---|---|---|
| Plus / Meta Muse 基础付费档 | $20 | 毛利预算约 $10 以内，只够约 5 个任务（$10÷$2） |
| ChatGPT Pro | $100 / $200 / $500 | 恰与中高估算重合，dot 只在这些档开放 |
| Grok Bot | $200（单买）；Heavy 约 $300 | 同上 |
| Meta Muse | Free / $20 / $100 | 同样做档位分层（M1） |

### 2.4 论证「大众市场需要端侧承接」是否成立

- 成立的部分：按今天的价格，常驻 Agent 要到 $100+ 才能覆盖成本。任务量 ×10 的话，$20 档几乎无法承接。大众（$0–20）只能拿到「按需、短会话、云额度受限」的 Agent。
- **反向证据（必须写进材料）**：
  1. 端侧也不免费。内存 BOM 大涨：12GB+256GB 采购价约 500→2200 元（博主，待核实），即多约 1700 元（约 $240，汇率按 7.1 估算）一次性成本，而云成本是持续成本。两者对比取决于机器保有期（按 3 年摊销，$240÷36 = $6.7/月），端侧在算账上仍更便宜，但这是我的算式，不是行业公开结论。
  2. token 价格仍在下降趋势中，但未找到可量化的 2027 预测。
  3. 当前主要瓶颈是可靠性（越界率 8.6–19.7%），不是成本。
  4. 端侧 3–30B 模型无法完成同样的复杂规划，端侧承接的是「高频、短任务、隐私、离线」，而不是复刻 dot。

**分析：这说明什么（判断）**：「云端常驻 Agent 难以走向大众价位」这个结论在 2026 年的价格体系下成立，有 OpenAI 档位设计与 Plus 额度作证。但推导「所以必须端侧承接」要加限定：端侧承接的是简单高频任务，复杂任务仍上云，所以端云混合是更站得住的表述；材料里不要写成端侧替代云。

---

## 3. 系统级 Agent 的做法对比

| 厂商 | 应用接入机制 | 端侧模型规格与内存 | 机型划线 | 商业模式 |
|---|---|---|---|---|
| **Apple iOS 27** | **App Intents** 是 Siri 操作第三方应用的唯一路径，SiriKit 弃用（支持窗口 2–3 年）；App Intents 2.0 加多轮追问、长任务流式返回、屏幕感知（均为二手开发者站，待核实）；无应用直接调用另一应用 intent 的 API，由 Siri/快捷指令编排 | 最强端侧模型需 **≥12GB** 统一内存；其余多数功能仍跑在今天硬件（含 iPhone 15 Pro）。20B 稀疏 MoE 见 M1。重建的 Siri 据称基于 1.2T 参数定制 Gemini，跑在 PCC（二手，待核实） | iPhone 17 Pro/Pro Max/Air；标准版 iPhone 17（8GB）被排除（MacRumors 2026-06-08，二手较可靠）；Siri AI 在欧盟、中国待审批（单一二手来源） | 早期不向开发者收佣金，不排除以后收（9to5Mac 经转述，2026-05-13，匿名开发者）；对用户：未找到订阅信息。Apple 付 Google 约每年 $10 亿（报道，待核实） |
| **Google Android 17** | 两路：①**屏幕自动化**，应用无需改代码，目前仅限选定的餐饮、打车伙伴；②**AppFunctions**，应用声明函数供系统发现调用（「MCP 式」），私有预览，已覆盖 **25 个应用**用例，KakaoTalk 为预览伙伴，开放早期访问计划（Android 开发者博客，2026-05-12，一手） | Gemini Nano v3+；**12GB+ RAM**、旗舰 SoC 白名单、5 次系统升级、6 年季度补丁等 8 条（ecorpit 转述 android.com 脚注）；Nano 运行设备 1.4 亿+（Google，2026-07-21）。Nano 4 的 4.2/5.9GB 为单一来源 | 屏幕自动化目前限 Pixel 10 系列与 Galaxy S26 系列，18 岁以上，美国/韩国；Gemini Intelligence 首批为最新 Galaxy 与 Pixel | 官方文案称给应用带来「高意图流量」，**未提及抽成**；消费者定价：未找到 |
| **华为 HarmonyOS 7 / 小艺** | **意图即服务**；HMAF 2.0：2100+ 系统能力、200+ 系统数据、500+ 生态 Skill、2000+ 智能体；A2A、A2UI 协议；复杂任务成功率 >90%（厂商口径）（爱范儿 2026-06） | 预告秋季在 Kirin 上支持端侧 **30B** 模型；激活参数 2B 仅见于搜索摘要，爱范儿未提，**待核实**；内存占用：未找到公开资料 | HarmonyOS 7 开发者 Beta 首批：Mate 80 Pro、Pura 90 Pro Max、nova 15 Pro、Mate X7、Mate XTs、Pura X；内存门槛未公布 | 未提及；小艺 Claw 已开放（M1） |
| **荣耀 MagicOS 11 / YOYO** | 「系统级 Agent Harness」：**MCP + A2A** 开放协议为主，GUI 作为泛化兜底，累计接入 10000+ 第三方 AI 服务；与阿里联合共建垂域模型；微信 A2A 首批支持（2026-06）（stdaily 2026-09-15；新华网） | 未公布。第三方称 MagicOS 9.0 起 YOYO 基于 3B 端侧模型（非官方规格）。MagicAgent 30B MoE 是否端侧：未找到 | Magic9 首发，AgenticOS beta 10 月邀请；100+ 步长任务、1000+ 主动场景；自测综合任务准确率 91.8% | 未提及 |
| **小米/vivo/OPPO** | 微信 A2A：厂商助手发指令、微信执行并返回，华为/荣耀/小米/OPPO/vivo 均在谈，荣耀先上线（科创板日报，2026-06，二手）；MCP 细节：未找到 | vivo 3B 端侧多模态（M1）；小米/OPPO：未找到 | 未找到 | 未找到 |
| **三星** | Bixby（Perplexity 后端）/ Gemini / Plex 三入口（M1）；AppFunctions 示例为 Galaxy S26 上的 Samsung Gallery | 未公开 | Galaxy S26 起 | 未找到 |
| **豆包+努比亚** | GUI 自动化 + SAEP 声明协议；2026-07 LatePost 称新版将转向应用方提供 MCP（与 9 月仍用 GUI 的报道**有冲突**，待核实） | 「努比亚豆包手机大模型」已备案；规格未披露 | 二代 12GB+512GB（5999 元） | 手机销售为主 |

**分析：这说明什么（判断）**：四家做法的共同点是**把应用能力声明成函数**（App Intents、AppFunctions、Skill、MCP/A2A），GUI 自动化只作兜底或限定伙伴。第二个共同点是**用内存划线**：Apple 与 Google 都用 12GB，但没有一家公布模型常驻占用与回收机制，这正是立项可占的空位。第三，商业模式上大多是「免费换流量/生态」，付费订阅仍集中在云端 Agent 的 $100+ 档。

---

## 4. 市场数据：12GB 门槛挡住多少用户

| 指标 | 数值 | 来源 |
|---|---|---|
| 全球手机平均 DRAM | 2025-12：8.4GB（2024-12：7.4GB）；>$600 高端段约 11GB；Apple 近 10GB；Huawei 品牌均值 12GB 最高 | Counterpoint，2026-02（MacTech 转述等） |
| ≥12GB 机型占出货比 | **全球、中国均未找到公开资料**（付费数据库内容）。Counterpoint 仅称 12GB 在 2026 年成为高端标配 | - |
| 2026 平均 DRAM | 预计 8.5GB | TrendForce 2026Q2 报告（搜索摘要） |
| 结构变化 | 高端 12GB 成主流，16GB 采用率下降；中端回落到 8GB；入门多停 4GB | TrendForce（搜索摘要） |
| GenAI 手机占比 | 2025：36%；2026：45%；2027：52% | Counterpoint，2026-06-22（一手页面） |
| 2026 总出货 | 10.8 亿台，同比 -13.9%（历史最低）。GenAI 手机约 **10.8×45% ≈ 4.9 亿台**（估算）。Gartner 旧预测 2026 为 5.59 亿 | Counterpoint；Gartner 2025-09（旧） |
| 出货下滑预测差异 | Counterpoint：-13.9%（6 月）→ -14.3%（8 月）；IDC：-12.9%，最大单年跌幅；每日经济新闻称 Counterpoint 2026Q3 同比 -20%（二手，待核实） | 各源 |
| 中国 | IDC 预计 2026 中国新一代 AI 手机 1.47 亿台，同比 +31.6%，占 53%；中国用户换机周期超 40.2 个月（信通院）（二手） | 每日经济新闻 2026-10-14 |
| DRAM 价格 | 2026Q2 手机内存价格环比 +80%；入门/中端/旗舰 BOM 同比约 +70%/+52%/+50%，旗舰 DRAM 已高于 SoC；中端内存占 BOM 40% | Counterpoint 2026-08（TechNews 转载 MoneyDJ） |
| 采购价 | 12GB+256GB 约 500→2200 元；旗舰 SoC 约 1500→2000 元 | 数码博主「数码闲聊站」，待核实 |
| 降配 | IDC：一年前的 12GB+256GB 可能变 8GB+128GB。**具体机型降配（16→12GB 或 12→8GB）：未找到已证实的新闻**，仅有 2026-10-20 博主「定焦数码」爆料：中端主力 8GB/顶配 12GB，入门 4GB/6GB，未点名厂商，未证实 | IDC；快科技 2026-10-20 |

**对「12GB 门槛」的量化（判断）**：GenAI 手机占比（36/45/52%）与 12GB 机型并不同口径。Apple 的 8GB iPhone 17 属 GenAI 手机但被最强模型排除，所以 ≥12GB 是 GenAI 手机的**子集**。在 2026 平均 8.5GB、中端回落 8GB、总量下降且低端被挤压的背景下，**可以肯定 12GB 的存量占比是少数**，但具体百分比无法给出。立项材料如要写数字，只能写「平均 8.4GB；高端段约 11GB」，并另行向 Counterpoint 购买分机型内存分布。

**分析：这说明什么（判断）**：两个相反的力同时存在。一方面 12GB 门槛把大多数用户挡在高端机之外，另一方面内存涨价让中低端不断降配，门槛对应的用户群在 2026–2027 反而变窄。这意味着 Agent OS 若只面向 12GB+ 旗舰，覆盖的是高端头部；而把端侧 Agent 压到 8GB 可用，才能扩大覆盖，这是内存管理方案（模型分层驻留、回收）的商业价值所在。

---

## 5. GUI Agent 路线的平台摩擦

**时间线**

| 日期 | 事件 | 来源 |
|---|---|---|
| 2025-12-01 | 豆包手机助手技术预览版发布（努比亚工程机，3499 元），靠 injection-event 系统权限模拟全局点击 | 人人都是产品经理 |
| 发布后 48 小时内 | 微信（强制下线，微信方称是既有风控）、淘宝（人机验证、闪退）、支付宝、高德、京东、拼多多、快手（强制登出）、王者荣耀（禁排位掉星）、建行/招行 App（录屏下强制退出）出现限制；豆包公告紧急停止对微信的调用支持 | 硅星人统计，经 woshipm |
| 2026-07-15/17 | 获生成式 AI 服务备案；LatePost：备货从 3 万台提升到数十万台；新版**不再读屏模拟点击**，要求应用方提供 MCP 服务，正与阿里、腾讯等谈判 | 华尔街见闻 2026-07-17 |
| 2026-09-16 | 二代努比亚 NaviX Ultra 开售，12GB+512GB 5999 元（国补后 5499 元）；预约 36 万+，「销售额一秒破亿」；发布会称端到端任务成功率 >80%；实测外部电商 App 暂不支持点咖啡等操作 | 界面新闻；第一财经等 |
| 2026-10-14 | SAEP 30 天公示期结束，公布拒绝名单：**150 余款**应用拒绝 GUI 自动化，含微信、美团、支付宝、淘宝、快手；腾讯系、阿里系、美团系、快手系均拒；银行/支付、游戏、DeepSeek、Kimi 等亦在内。精确的 151 款、腾讯系 65 款、阿里系 23 款（占 57.5%）仅见于搜索摘要，**未能在原文核到，待核实** | 北京日报 2026-10-14 |

- **销量**：二代实际销量**未找到公开资料**；备货数字有「数十万台」（LatePost）与「约 20 万台」（界面，传闻）两种说法，均未证实。
- **口碑**：「莽」（事前未与生态沟通）与「头部平台拒绝的是被绕过」两种评价并存（盘古智库江瀚）；一代未形成可用状态。
- **协议化**：SAEP（声明协议，豆包）、AppFunctions（Google）、App Intents（Apple）、HMAF A2A/A2UI（华为）、MCP/A2A（荣耀、阶跃）、微信 A2A（与五家手机厂商，2026-06）。观察者网归纳为 GUI Agent 与 A2A 直连两条路径。

**分析：这说明什么（判断）**：GUI 路线在上市前三个月被封禁，上市后 150 余款应用拒绝，豆包自己也在 7 月转向 MCP，这是应用能力接口化成为主流方向的最直接证据。但阶跃的数据也提醒：接口化后头部应用依然「每家只开一扇窗」，开放程度由应用方的商业利益决定，所以不能假设应用能力会全量工具化。对我们：叠加场景（Agent 拉起应用）会长期存在，因为开放的接口不够，应用仍需被拉起或前台确认。

---

## 参考资料

| # | 标题 | URL | 日期 |
|---|---|---|---|
| 1 | 阶跃终端发布首款智能体手机 STEPX Neo（凤凰科技） | https://tech.ifeng.com/c/8xCCgZZuOTQ | 2026-10-13 |
| 2 | STEPX Neo 接入支付宝 300 余项服务、微信缺席（每日经济新闻） | https://www.mrjjxw.com/articles/2026-10-14/4604643.html | 2026-10-14 |
| 3 | STEPX Neo 发布两周首次升级（量子位，厂商稿） | https://www.qbitai.com/2026/10/506554.html | 2026-10-29 |
| 4 | StepFun 手机（Decrypt） | https://decrypt.co/381202/chinese-startup-stepfun-phone-ai-agent | 2026-10 |
| 5 | 搜狐：可能不公开发售、无出货目标 | https://m.sohu.com/a/1051615243_116551 | 2026-07 |
| 6 | Grok Bot 拆解（Vellum，竞品） | https://www.vellum.ai/blog/official-grok-bot-breakdown | 2026-08-20 |
| 7 | Grok Bot Android 开放（postium.ru，二手） | https://postium.ru/grok-bot-vyshel-na-android/ | 2026-09-02 |
| 8 | OpenAI DevDay 与 Pro 500（reworked） | https://www.reworked.co/ai-news/the-biggest-announcements-from-openai-devday-dots-agents-new-500-plan/ | 2026-10-01 |
| 9 | OpenAI Dots 评测（eesel，二手） | https://www.eesel.ai/fr/blog/openai-dots-avis | 2026-10 |
| 10 | Dots 独立测试（CryptoBriefing） | https://cryptobriefing.com/openai-dots-ai-agent-hands-on-review/ | 2026-10-27 |
| 11 | Dots 实测（neoteo） | https://www.neoteo.com/en/openai-dots-review-website-and-video-tasks-worked-online-errands-hit-snags | 2026-10-02 |
| 12 | GPT-6 Astra 定价（OpenAI 帮助中心，经搜索摘要） | https://help-lb.openai.com/en/articles/20001415 | 2026-09 |
| 13 | Anthropic：多 Agent 研究系统 | https://www.anthropic.com/engineering/multi-agent-research-system | 2025-06 |
| 14 | E2B/Modal/Daytona 沙箱价格 | https://www.beri.net/article/e2b-vs-modal-vs-daytona-agent-sandbox-pricing-isolation-2026 | 2026-10-08 |
| 15 | Browserbase 价格（聚合站） | https://scrapegraphai.com/blog/browserbase-pricing | 2026 |
| 16 | AI Agent 单任务成本（引 Claude Code $13/日） | https://www.kunalganglani.com/blog/ai-agent-cost-per-task-2026.md | 2026 |
| 17 | The Information：Manus 单任务 $2 | https://feature.theinformation.com/articles/salesforce-manus-show-high-cost-agents | 日期未核 |
| 18 | Counterpoint：GenAI 手机占比 | https://counterpointresearch.com/de/insights/genai-smartphone-share-to-rise-to-45-percent-of-global-shipments-in-2026 | 2026-06-22 |
| 19 | Counterpoint：平均 DRAM 8.4GB（MacTech 转述） | https://www.mactech.com/2026/02/26/apples-average-smartphone-dram-reached-almost-10gb-in-december-2025-marking-an-annual-increase-of-2-2gb | 2026-02-26 |
| 20 | 入门机受内存成本冲击最大（TechNews） | https://technews.tw/2026/08/28/entry-level-smartphones-hit-hardest-by-memory-costs/ | 2026-08-28 |
| 21 | 12GB 不再是标配，传多家厂商调整配置（快科技/凤凰） | https://tech.ifeng.com/c/8xNRBDGvr6G | 2026-10-20 |
| 22 | Android 开发者博客：Building for the Intelligence System | https://developer.android.com/blog/posts/building-for-the-intelligence-system-on-android | 2026-05-12 |
| 23 | Gemini Intelligence 硬件门槛（ecorpit） | https://ecorpit.com/gemini-intelligence-hardware-floor-android-ai-fallback-2026/ | 2026-08-03 |
| 24 | MacRumors：最强端侧 AI 需 12GB | https://www.macrumors.com/2026/06/08/most-powerful-on-device-ai-now-requires-iphone-17-pro-or-air/ | 2026-06-08 |
| 25 | iOS 27 Siri 集成与费用（lavx 转述 9to5Mac） | https://news.lavx.hu/article/ios-27-s-siri-integration-what-developers-need-to-know-and-why-fees-matter | 2026-05-13 |
| 26 | 鸿蒙 7 发布（爱范儿） | https://www.ifanr.com/1668803 | 2026-06 |
| 27 | 荣耀 MagicOS 11（科技日报） | https://www.stdaily.com/web/gdxw/2026-09/15/content_581559.html | 2026-09-15 |
| 28 | 豆包手机二代首销（界面新闻） | https://m.jiemian.com/article/15109389.html | 2026-09 |
| 29 | 新豆包手机备货与 MCP 策略（华尔街见闻转 LatePost） | https://wallstreetcn.com/articles/3777243 | 2026-07-17 |
| 30 | 豆包手机助手首轮封禁（人人都是产品经理） | https://www.woshipm.com/ai/6302872.html | 2025-12 |
| 31 | SAEP 拒绝名单（北京日报） | https://news.bjd.com.cn/2026/10/14/11995247.shtml | 2026-10-14 |
| 32 | 微信 A2A 与手机厂商（观察者网，仅搜索摘要） | https://www.guancha.cn/economy/2026_06_04_819388.shtml | 2026-06-04 |

## 待核实清单

1. Grok Bot 官方定价、Heavy 价格、云 VM 规格、是否共享 VM（M1 与 Vellum 冲突）、Android 版时间。
2. dot 是否含 Plus；$500 档与 Pro 200 额度调整细节与生效日；dot 与 Operator/ChatGPT Agent/Pulse 的关系；系统卡 8.6%/19.7% 的原文。
3. GPT-6 Astra API 价格是否来自 OpenAI 官方页面。
4. hyperscaler 小规格 VM 单价（我估 $30/月仅为量级）；Browserbase 官方价；Manus $2/任务的原始来源日期。
5. STEPX Neo 开售后销量、独立评测、第 13 个月后 Token Plan 价格、Step Edge 参数与内存、Step AOS 与 AOSP 的关系。
6. ≥12GB 机型占出货比（全球、中国）：需向 Counterpoint/IDC/Canalys/Omdia 查付费库。
7. 具体品牌降配新闻（目前只有匿名爆料）；Counterpoint 2026Q3 同比 -20% 的原始出处；约 1700 元内存涨幅（博主数据）。
8. SAEP 拒绝名单的 151/65/23 精确数字；豆包新版到底是 MCP 还是仍用 GUI（7 月与 9 月说法冲突）；二代销量与备货。
9. 微信 A2A 与手机厂商合作的原文与各家上线状态（guancha 原文抓取为空）。
10. 华为端侧 30B 模型的激活参数（2B）与内存占用、支持机型；荣耀、小米、OPPO、vivo 端侧内存占用。
11. Apple：App Intents 2.0 细节、1.2T Gemini 模型、中国/欧盟不可用、对开发者的收费，均来自二手，需对照 Apple 开发者文档。

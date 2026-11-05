"""第一部分：洞察。Agent OS 商业形态（全景、点名产品拆解、系统级对比、市场与成本、结论）
+ 基础能力（模型、内核、引擎与硬件、评估手段）+ AI + 图形。"""

from lib import (arrow, box, card, footnote, kpi, new_slide, num_badge, points, table, text, timeline,
                 titled_card)
from registry import page, tpl

tpl("common.section-basic", num="01", title="洞察", subtitle="Agent 成为新入口，竞争转向端侧执行环境与内存")


# ------------------------------------------------------------------ I-1 商业形态全景
@page
def landscape(prs):
    s = new_slide(prs, "Agent商业形态全景", "三条路线并行",
                  "云端常驻、系统级端云、整机重构三条路线同时推进，分歧在于 Agent 的执行环境放在哪里")
    table(s, (32, 128, 1216, 420),
          ["维度", "① 云端常驻 Agent", "② 系统级端云 Agent", "③ 整机重构 Agent 手机"],
          [
              ["代表产品",
               "xAI Grok Bot（2026-08 公测）；OpenAI dot（2026-09 DevDay）；Meta Muse（2026-09）",
               "Apple iOS 27 新 Siri；Google Android 17 Gemini Intelligence；华为 HarmonyOS 7 小艺；荣耀 MagicOS 11",
               "阶跃 STEPX Neo + Step AOS（2026-10 首销）；字节豆包 × 努比亚（二代 2026-09）；荣耀 Robot Phone"],
              ["执行环境",
               "云端 Linux 虚拟机 + 浏览器 + 文件系统，7×24 常驻；关掉终端后任务继续",
               "端侧模型处理高频短任务，复杂任务上云（Apple PCC、Gemini 云、盘古云）",
               "自研或深改的 OS；端侧小模型执行简单指令，多应用任务交云端大模型"],
              ["应用接入",
               "云电脑登录用户账号；连接器与插件（dot 称 4000+ 应用）；浏览器直接操作网页",
               "应用能力声明成函数：App Intents、AppFunctions、HMAF Skill、MCP / A2A；GUI 只作兜底",
               "阶跃以 MCP / A2A 接入（支付宝 300+ 服务）；豆包一代 GUI 自动化，7 月起转向 MCP（报道）"],
              ["商业模式",
               "高价订阅：dot 只随 ChatGPT Pro（$100–500/月）提供；Grok Bot 单买 $200/月",
               "系统免费，换入口与生态流量；Apple 早期不向开发者收取佣金（报道）",
               "卖硬件并打包云 token：STEPX Neo 3999 元含 12 个月 Token Plan（每月 1000 亿 token）"],
              ["规模与门槛",
               "不受端侧资源约束；单用户成本约 !!$70–300/月!!（估算）",
               "用内存划线：Apple、Google 最强端侧能力都要求 !!12GB!!；Gemini Nano 已在 1.4 亿台以上设备运行",
               "规模小：阶跃不设出货目标；豆包二代预约 36 万+，销量未公开"],
              ["核心约束",
               "成本与可靠性：dot 10 步任务链越权率 !!19.7%!!（OpenAI 系统卡，二手转述）",
               "内存：端侧模型常驻挤压应用；四家都没有公开模型常驻占用与回收机制",
               "生态开放度：!!150!! 余款应用拒绝 GUI 自动化（2026-10）；接入方「只开一扇窗」"],
          ], widths=[0.9, 3.2, 3.2, 3.2], style="detail", header_style="body_strong")
    titled_card(s, (32, 562, 1216, 126), "判断",
                "- 三条路线不是替代关系：云端路线拥有模型和算力，系统级路线拥有入口、本机应用和个人数据，整机路线在叙事上领先但规模有限。\n"
                "- 手机厂商能守住的位置是 @@端侧执行环境@@——本机应用、个人上下文和系统资源调度；而这个位置的硬约束是 @@内存@@，这正是本立项要补的能力。",
                style="body")


# ------------------------------------------------------------------ I-2 阶跃 Step AOS
@page
def stepfun(prs):
    s = new_slide(prs, "点名产品拆解（一）", "阶跃 Step AOS / STEPX Neo",
                  "把「为端侧模型弹性供给资源」写进 OS 底层，方向与我们一致，但没有给出任何量化指标")
    x0, w = 32, 610
    card(s, (x0, 128, w, 420))
    text(s, (x0 + 12, 136, w - 24, 20), "@@架构拆解@@（据公开报道整理，厂商口径）", style="body")
    LW = 74
    layers = [
        ("交互层", ["意图入口：语音为主，6 麦", "Amoo 个人智能体作首页", "MiniLED 背屏显示任务进度"]),
        ("Agent 层", ["长期记忆：用户偏好 + 任务经验", "任务调度与端云分工", "安全：TEE 内执行、每步可审计"]),
        ("能力层", ["手机功能拆成可调用的「块」", "第三方经 MCP / A2A 接入", "支付宝 300+ 服务；美团仅跑腿；微信缺席"]),
        ("模型层", ["端侧 Step Edge ×4：基础 / 音频 / GUI / 生成", "Step Inference 自研 NPU 引擎", "云端 Step 5 Preview：600B 总参、27B 激活"]),
        ("资源层", ["统一调度 CPU / GPU / NPU，为端侧模型「弹性供给」", "统一语义数据层 + 高速混合数据库"]),
        ("硬件", ["骁龙 8 系 · 16GB + 256GB · 闻泰 ODM"]),
    ]
    y, lh, gap = 164, 52, 5
    for name, items in layers:
        h = 40 if name == "硬件" else lh
        box(s, (x0 + 12, y, LW, h), name, fill="primary", color="on_primary", style="body_strong")
        cw = (w - 24 - LW - 8 - 6 * (len(items) - 1)) / len(items)
        for i, it in enumerate(items):
            hot = name == "资源层"
            box(s, (x0 + 12 + LW + 8 + i * (cw + 6), y, cw, h), it, fill="highlight" if hot else "surface",
                line="highlight_strong" if hot else None, style="detail")
        y += h + gap
    text(s, (x0 + 12, y + 2, w - 24, 30), "红框：与本立项直接相关的系统资源层。Step Edge 参数量、常驻内存、Amoo 常驻方式、"
         "与 AOSP 的关系均未公开。", style="caption")

    titled_card(s, (x0, 560, w, 128), "商业模式与现状",
                "- 3999 元「软硬模全栈价」：手机 + Step AOS + Step Studio + 12 个月 Token Plan；第 13 个月起价格未公布。\n"
                "- 10-16 首销，不设出货目标，尚无独立评测；分析师评价为「合格的开发者版」。",
                style="detail")

    rx, rw = 656, 592
    card(s, (rx, 128, rw, 560))
    text(s, (rx + 14, 140, rw - 28, 24), "分析：这说明什么", style="emphasis", color="primary_text")
    pts = [
        ("OS 资源调度被视为 Agent 手机的核心能力",
         "阶跃把「统一调度异构算力、为端侧模型弹性供给」放在 OS 底层，说明内存与算力供给已经进入 Agent 手机的产品定义；"
         "但参数量、常驻内存、回收机制全部空白，这一空位正是大厂可以用量化指标占领的。"),
        ("端侧承接比例直接决定毛利",
         "端侧只做简单指令，复杂任务上云，并把 12 个月、每月 1000 亿 token 的云成本打包进售价——云 token 是长期成本项，"
         "端侧每多承接一类任务，就少一份持续支出。"),
        ("应用开放度由应用方利益决定",
         "接入面靠合作谈判：支付宝开放 300+ 服务，美团只开跑腿，微信缺席。开放接口不足时，Agent 仍要拉起应用、等用户在前台确认，"
         "叠加场景会长期存在。"),
        ("对我们的启示",
         "不必另起一个 OS：可落地的差异化在现有内核上的内存与 IO 供给，并要给出阶跃没有给出的数字——常驻占用、冷启动劣化、"
         "后台存活数。"),
    ]
    points(s, rx + 14, 176, rw - 28, 500, pts, style="lead")


# ------------------------------------------------------------------ I-3 Grok Bot 与 dot
@page
def cloud_agents(prs):
    s = new_slide(prs, "点名产品拆解（二）", "Grok Bot与OpenAI dot：云端常驻Agent",
                  "云端常驻 Agent 定义了「7×24、主动、跨应用」的用户预期，但成本把它锁在 $100 以上的订阅档")
    x0, w = 32, 610
    card(s, (x0, 128, w, 236))
    text(s, (x0 + 12, 136, w - 24, 20), "@@共同架构@@：Agent = 模型 + 云端执行环境 + 连接器", style="body")
    cols = [("入口", "ChatGPT、Slack、Teams；桌面端设置，手机作遥控"),
            ("Agent 与模型", "dot：GPT-6 Astra；Grok Bot：xAI 模型"),
            ("云端执行环境", "Linux 虚拟机 + Chrome + 文件系统 + 终端"),
            ("应用接入", "插件与连接器、自定义 MCP、浏览器登录态")]
    bw = (w - 24 - 3 * 22) / 4
    for i, (t, d) in enumerate(cols):
        bx = x0 + 12 + i * (bw + 22)
        box(s, (bx, 164, bw, 118), f"**{t}**\n{d}", fill="surface", style="caption", align="left", valign="top", inset=7)
        if i < 3:
            arrow(s, (bx + bw + 2, 223), (bx + bw + 20, 223), color="primary_text", width=1.5)
    box(s, (x0 + 12, 292, w - 24, 62),
        "**安全机制**：环境外的独立自动审核检查每个计划动作；密码、付款永远交还用户；2FA 暂停等待输入。"
        "OpenAI 承认提示注入防护「不能消除风险」。", fill="highlight_blue", style="caption", align="left", inset=8)

    table(s, (x0, 376, w, 312), ["对比项", "xAI Grok Bot", "OpenAI dot"],
          [["发布", "2026-08-11 公测", "2026-09-29 DevDay"],
           ["执行环境", "账号级共享云 VM，多个 bot 共用，规格未披露", "每个 dot 一台云端 Linux 电脑 + Chrome"],
           ["开放档位", "单买 !!$200/月!!；SuperGrok Heavy 等附带", "仅随 ChatGPT Pro（!!$100–500/月!!）附赠，Plus 不含"],
           ["可靠性", "无独立测试", "10 项商务任务均分 8.8，五个 Agent 中第三；5 步 / 10 步链越权率 8.6% / 19.7%"],
           ["对终端的要求", "无（Android 端仅作入口）", "无（安装与设置仅限桌面）"]],
          widths=[1.0, 2.2, 2.6], style="caption", header_style="detail")

    rx, rw = 656, 592
    card(s, (rx, 128, rw, 300))
    text(s, (rx + 14, 140, rw - 28, 22), "单位经济性：一个常驻云 Agent 每月要花多少（估算）", style="emphasis",
         color="primary_text")
    table(s, (rx + 14, 172, rw - 28, 196), ["成本项", "口径", "每用户每月"],
          [["云电脑常驻", "2vCPU / 4GiB × 730 小时，E2B 零售价", "约 $121（自建机房可低数倍）"],
           ["浏览器", "每天 4 小时 × $0.10–0.12/小时", "$12–14"],
           ["模型 token", "每任务 30 万输入 + 2 万输出，Astra 价 $1.3–4；每月 30–90 个任务", "$40–360"],
           ["合计", "常见区间", "!!$70–300!!"]],
          widths=[1.0, 2.6, 1.5], style="caption", header_style="detail")
    text(s, (rx + 14, 376, rw - 28, 44), "对照：$20 档只够约 5 个任务；OpenAI 不向 Plus 开放 dot、Plus 的 Agent 额度仅为 Pro 的 1/10，"
         "是同一结论的市场证据。", style="caption")

    card(s, (rx, 440, rw, 248))
    text(s, (rx + 14, 450, rw - 28, 22), "分析：这说明什么", style="emphasis", color="primary_text")
    text(s, (rx + 14, 478, rw - 28, 204),
         "- @@云端常驻 Agent 在 2026 年的价格体系下进不了大众价位@@：成本约 $70–300/月，与 $100–500 的开放档位恰好重合。\n"
         "- 它们抬高了用户预期（全天候、主动、跨应用），手机上的 Agent 会被拿来对比。\n"
         "- 长任务链可靠性仍是瓶颈（越权率 8.6%–19.7%），说明端侧也不应承接长链自治任务。\n"
         "- @@对我们@@：端侧不复刻云端常驻，而是承接高频、短时、隐私、离线、与本机应用叠加的任务；"
         "端云混合，用 S1 量化每类任务下沉的收益与代价。",
         style="detail", gap_pt=4)


# ------------------------------------------------------------------ I-4 系统级 Agent 对比
@page
def system_agents(prs):
    s = new_slide(prs, "系统级Agent做法对比", "应用函数化、内存划线、模型内存不透明",
                  "四家平台在应用接入上已收敛到「函数声明」，在资源上都用 12GB 划线，却没有一家公开模型内存如何治理")
    table(s, (32, 128, 1216, 318),
          ["维度", "Apple iOS 27", "Google Android 17", "华为 HarmonyOS 7", "荣耀 MagicOS 11"],
          [["应用接入",
            "App Intents 为 Siri 操作第三方应用的唯一路径，SiriKit 弃用",
            "屏幕自动化（限选定伙伴）+ AppFunctions 函数声明（私有预览，25 个应用用例）",
            "意图即服务；HMAF 2.0：2100+ 系统能力、500+ 生态 Skill；A2A、A2UI",
            "MCP + A2A 为主、GUI 兜底；累计接入 10000+ AI 服务；首批支持微信 A2A"],
           ["端侧模型",
            "AFM 3：据报 20B 稀疏 MoE 放闪存，每次调入 1–4B 专家参数（二手）",
            "Gemini Nano v3+（Nano 4 基于 Gemma 4）；Nano 已覆盖 1.4 亿+ 设备",
            "预告在麒麟上支持端侧 30B 模型（激活参数待核实）",
            "YOYO 据第三方称基于 3B 端侧模型；MagicAgent 30B MoE 是否端侧未知"],
           ["云端",
            "Private Cloud Compute；新 Siri 据报基于定制 Gemini（待核实）",
            "Gemini 云端，Hybrid API 按 PREFER_ON_DEVICE 回落",
            "盘古等云端模型，机密计算环境",
            "与阿里共建垂域模型"],
           ["机型门槛",
            "最强端侧模型要求 !!12GB!!：仅 iPhone 17 Pro / Pro Max / Air",
            "8 条门槛含 !!12GB+!! RAM、旗舰 SoC 白名单、5 次系统升级",
            "未公布内存门槛；首批 Mate 80 Pro 等旗舰",
            "未公布；Magic9 首发"],
           ["模型内存治理",
            "未公开", "未公开（Nano 4 常驻 4.2 / 5.9GB 为单一来源）", "未公开", "未公开"]],
          widths=[0.9, 2.2, 2.2, 2.2, 2.2], style="detail", header_style="body_strong")

    card(s, (32, 458, 1216, 112))
    text(s, (44, 466, 400, 20), "@@接口化进程@@：GUI 自动化让位于函数声明", style="body")
    timeline(s, 60, 512, 1160, [
        ("2025-12", "豆包一代 48 小时内被微信、淘宝、支付宝等限制"),
        ("2026-05", "Google AppFunctions 私有预览，覆盖 25 个应用用例"),
        ("2026-06", "HMAF 2.0 发布；微信与五家手机厂商洽谈 A2A"),
        ("2026-07", "豆包新版转向由应用方提供 MCP（LatePost 报道）"),
        ("2026-10", "SAEP 公示期结束，150 余款应用拒绝 GUI 自动化"),
    ], text_h=44)

    card(s, (32, 582, 1216, 106))
    text(s, (44, 590, 200, 20), "分析：这说明什么", style="emphasis", color="primary_text")
    text(s, (44, 614, 1192, 70),
         "- **应用函数化成为共识**：Agent 通过函数调用应用，但头部应用只开放部分能力；需要拉起应用界面、前台确认的场景会长期存在，冷启动与切换体验成为 Agent 体验的一部分。\n"
         "- **内存是共同的准入线，模型内存是共同的黑箱**：两大平台都用 12GB 划线，没有一家公开模型常驻占用、回收和共享机制——这是我们用系统能力建立差异化的空位。",
         style="detail", gap_pt=3)


# ------------------------------------------------------------------ I-5 市场与成本
@page
def market(prs):
    s = new_slide(prs, "市场与成本", "12GB门槛与内存涨价的双向挤压",
                  "门槛定在 12GB，市场均值只有 8.4GB 且在降配；谁能让 Agent 在现有内存里跑稳，谁就扩大了覆盖面")
    ks = [("12GB", "端侧 Agent 准入线", "Apple、Google 最强端侧能力的共同门槛"),
          ("8.4GB", "全球手机平均 DRAM", "2025-12，Counterpoint；高端段约 11GB"),
          ("+80%", "手机内存价格环比", "2026Q2，Counterpoint"),
          ("约$20/GB", "移动 DRAM 合约价", "2026Q2，约为 2024 年的 4 倍"),
          ("45%", "GenAI 手机出货占比", "2026E；2027E 为 52%（Counterpoint）")]
    kw = (1216 - 4 * 12) / 5
    for i, (v, l, n) in enumerate(ks):
        kpi(s, (32 + i * (kw + 12), 128, kw, 104), v, l, n)

    # 左：整机 BOM 同比涨幅（原生柱状图）
    card(s, (32, 244, 600, 444))
    text(s, (46, 254, 572, 20), "@@2026 年整机 BOM 同比涨幅@@（按价位段，Counterpoint 2026-08）", style="body")
    bars = [("入门机", 70), ("中端机", 52), ("旗舰机", 50)]
    base_y, top_y, bx0 = 560, 300, 90
    for i, (name, v) in enumerate(bars):
        h = (base_y - top_y) * v / 80
        x = bx0 + i * 170
        box(s, (x, base_y - h, 90, h), "", fill="primary", check=False)
        text(s, (x - 20, base_y - h - 26, 130, 22), f"!!+{v}%!!", style="emphasis", align="center")
        text(s, (x - 20, base_y + 6, 130, 20), name, style="body", align="center")
    arrow(s, (70, base_y), (600, base_y), color="muted", head=False)
    text(s, (46, 592, 572, 90),
         "- 中端机内存已占 BOM 的 !!40%!!，旗舰机 DRAM 成本已高于 SoC。\n"
         "- IDC：一年前的 12GB + 256GB 配置，2026 年可能退到 8GB + 128GB；2026 年全球出货预计 10.8 亿台，同比 -13.9%。",
         style="detail")

    rx, rw = 648, 600
    card(s, (rx, 244, rw, 444))
    text(s, (rx + 14, 254, rw - 28, 22), "分析：这说明什么", style="emphasis", color="primary_text")
    pts = [
        ("能用上最强端侧 Agent 的是少数，而且在变少",
         "门槛 12GB，均值 8.4GB，高端段约 11GB；内存涨价让中端回落到 8GB，12GB 以上用户群在 2026–2027 年反而收窄。"),
        ("加内存的路被价格堵死",
         "合约价约 $20/GB，TrendForce 判断 2027 年不会明显回落；厂商守住 12GB 已属不易，不会为 Agent 再加 4GB。"),
        ("系统能力直接折算为 BOM 与覆盖面",
         "每多出 1GB 等效可用内存，约等于每台省下 $20（约 140 元）DRAM；能让 Agent 在 12GB 机型上叠加应用不卡、"
         "并下探到更低配置，就扩大了 Agent 的可用人群。"),
        ("对我们的启示",
         "立项的价值主张可以量化为「不加 DRAM，撑起 Agent + 应用叠加」：以等效内存（GB）、冷启动劣化、后台存活数作为验收口径。"),
    ]
    points(s, rx + 14, 286, rw - 28, 396, pts, style="body")


# ------------------------------------------------------------------ I-6 洞察结论（商业形态）
@page
def commercial_takeaways(prs):
    s = new_slide(prs, "商业形态洞察结论", "对终端OS提出五个要求",
                  "五个要求都落在「端侧执行环境」上：内存要做大、模型要被管住、应用要拉得起、端云要算得清")
    table(s, (32, 128, 1216, 470),
          ["对终端 OS 的要求", "依据（来自前述洞察）", "如果做不到", "本立项的对应内容"],
          [["**一、不加 DRAM，把有效内存做大**",
            "最强端侧能力门槛 12GB，市场均值 8.4GB；2026Q2 手机内存价格环比 +80%，2027 年不会明显回落",
            "Agent 只能覆盖少数旗舰；在 12GB 机型上与应用争内存，后台被杀、冷启动变慢",
            "总体构想（一等公民）；KT1-b / KT1-c 冷热识别驱动的预取与换出"],
           ["**二、模型内存被系统统一治理**",
            "端侧模型走向稀疏大模型 + 闪存驻留（Apple 据报 20B MoE、华为预告端侧 30B）；四家平台均未公开模型内存治理",
            "模型权重、KV、NPU 缓冲长期钉住，回收看不见，只能靠杀应用腾空间",
            "KT2 专家缓存与 KV 块池；KT3 零拷贝加载与共享"],
           ["**三、应用拉得起、切得回**",
            "接口化进程中头部应用只开放部分能力；Agent 仍要拉起应用、等用户前台确认",
            "Agent 调起应用时冷启动劣化、切回时卡顿，体验被归咎于 Agent",
            "KT1-a .so 文件页锁优化；KT1-b 切回前台预取"],
           ["**四、端云分工算得清**",
            "云端常驻 Agent 约 $70–300/用户/月；整机路线把云 token 打包进售价；端侧多耗电、占内存",
            "下沉决策靠拍脑袋：要么云成本失控，要么端侧体验受损",
            "S1 云转端评估：决策模型 + 真机基线 + 仿真校准"],
           ["**五、单个 Agent 跑得快**",
            "云上并行化证据充分（LLMCompiler 最高 3.7 倍、PASTE -43.5%）；端侧 decode 受带宽限制，工具多有副作用",
            "多步任务时延是各步之和，端侧体验落后云端",
            "S2 单 Agent 并行化导出与仿真验证"]],
          widths=[1.6, 3.0, 2.4, 2.2], style="body", header_style="body_strong")
    card(s, (32, 612, 1216, 76), fill="highlight_blue", shadow=False)
    text(s, (48, 622, 1184, 60),
         "**结论**：Agent 的竞争正在从「模型能力」转向「执行环境」。对手机厂商，执行环境的护城河是本机应用、个人上下文和系统资源调度；"
         "其中内存供给是 2027 年最紧的约束，也是业界公开资料里最大的空白。", style="body", valign="middle")

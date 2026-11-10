"""第二部分 · 场景与负载瓶颈（报告 2-场景与负载瓶颈）：
  章节页；现状（2.1）：云侧推理、端侧执行；参考负载「贴身秘书」的设定（2.2.1）。
"""

import lib
from lib import arrow, block_arrow, box, footnote, measure, new_slide, outline, poly, rect, round_card, table, \
    table_height, text
from registry import page

CRUMB = "二、场景与负载瓶颈"


# ---------------------------------------------------------------- 章节页

@page
def scene_section(prs):
    lib.section_slide(prs, "二、", "场景与负载瓶颈",
                      "今天手机 Agent 的负载形态；以「贴身秘书」为参考负载量化需求；每个领域的体验与商业化问题；能力缺口与三项系统服务的瓶颈")


# ---------------------------------------------------------------- 2.1 现状

@page
def status_quo(prs):
    s = new_slide(prs, "手机 Agent 现状：", "以云侧推理、端侧执行为主，负载重心正从单次问答转向常驻代理",
                  crumb=CRUMB + " › 现状")
    # 左：今天的手机 Agent
    LW = 748
    text(s, (32, 88, LW, 20), "**今天的手机 Agent 有哪些**", style="body", color="accent", check=False)
    cols = ["产品", "推理在哪", "端侧怎么执行", "公开数据"]
    rows = [
        ["豆包手机助手（努比亚，二代 2026-09）", "大模型与 Agent 在云端", "GUI 自动化：读屏、模拟点击",
         "端到端任务成功率 >80%（发布会口径）；!!150 余款!!应用拒绝被自动化操作"],
        ["荣耀 YOYO / MagicOS 11", "以云端为主（未公布端侧规格）", "MCP + A2A 调用应用，GUI 兜底", "累计接入 1 万多项第三方 AI 服务（媒体）"],
        ["华为小艺 / HMAF 2.0", "本地优先，复杂任务上云", "意图框架调用 2100 多项系统能力与生态 Skill", "复杂任务成功率 >90%（厂商口径）"],
        ["Google Gemini（Android 17）", "端侧 Nano + 云端 Gemini", "AppFunctions（预览，25 个用例）；限定伙伴的屏幕自动化",
         "机型门槛为 12GB 以上内存"],
        ["Apple Siri（iOS 27）", "端侧 AFM 3 + 云端私有计算（PCC）", "App Intents，由 Siri 与快捷指令编排", "最强端侧模型限 12GB 机型"],
        ["阶跃 Step AOS（STEPX Neo）", "小模型在端侧，大模型在云端", "MCP 化的系统功能块", "支付宝接入 300 多项服务，美团仅跑腿，微信缺席（媒体）"],
        ["云端常驻 Agent（dot、Grok Bot）", "全云端", "不在手机上执行，手机只是遥控入口", "见「业界三条路线」页"],
    ]
    ratios = [1.2, 1.05, 1.45, 1.7]
    th = table_height(LW, cols, rows, ratios, style="detail", pad=(5, 2))
    table(s, (32, 110, LW, th), cols, rows, widths=ratios, style="detail", pad=(5, 2), align=["left"] * 4, fit=False)

    # 右：典型负载形态
    RX, RW = 796, 452
    text(s, (RX, 88, RW, 20), "**典型负载形态：端侧采集 → 云端推理 → 端侧执行**", style="body", color="accent",
         check=False)
    steps = [("① 采集上下文", "屏幕内容、界面树或意图参数", "blue_l"),
             ("② 上传云端", "每步一次网络往返", "purple_l"),
             ("③ 云端推理", "推出下一步动作", "purple_l"),
             ("④ 端侧执行", "拉起 App、调用意图或模拟点击", "blue_l"),
             ("⑤ 采集结果", "进入下一步", "blue_l")]
    gap = 10
    bw = (RW - gap * 4) / 5
    by, bh = 114, 70
    for i, (name, desc, fill) in enumerate(steps):
        x = RX + i * (bw + gap)
        box(s, (x, by, bw, bh), f"**{name}**\n{desc}", fill=fill, line="grey_d", style="caption", inset=3)
        if i < 4:
            arrow(s, (x + bw + 1, by + bh / 2), (x + bw + gap - 1, by + bh / 2), color="dark")
    ly = by + bh + 14
    poly(s, [(RX + 4 * (bw + gap) + bw / 2, by + bh), (RX + 4 * (bw + gap) + bw / 2, ly), (RX + bw / 2, ly),
             (RX + bw / 2, by + bh)], head=True, color="red", width=1.25)
    text(s, (RX + bw + 10, ly - 8, RW - 2 * bw - 20, 16), "一个跨应用任务通常循环多步", style="caption", color="accent",
         align="center", fill="bg", check=False)
    rect(s, (RX + RW - 104, ly + 8, 12, 10), "blue_l", line="grey_d")
    text(s, (RX + RW - 88, ly + 5, 36, 16), "端侧", style="caption", check=False)
    rect(s, (RX + RW - 50, ly + 8, 12, 10), "purple_l", line="grey_d")
    text(s, (RX + RW - 34, ly + 5, 36, 16), "云端", style="caption", check=False)

    fy = ly + 28
    feats = ("- **压力在 App，不在模型**：端侧几乎不跑模型，NPU 基本闲置；主要开销是被 Agent 拉起的 App，"
             "连续拉起造成冷启动劣化、.so 文件页争用，后台应用被回收后切回又要重新冷启动\n"
             "- **时延由网络和云端主导**：每步一次往返，弱网和离线时整条任务不可用\n"
             "- **执行边界借用 App 的边界**：GUI 自动化以用户身份操作界面，意图调用以系统助手身份调用应用，"
             "都没有「这个 Agent 会话能做什么」的独立边界")
    need = text(s, (RX, fy, RW, 236), feats, style="body", gap_pt=4)
    text(s, (RX, fy + need + 8, RW, 36),
         "!!数据缺口!!：各应用的步数、步间时延与端侧资源占用没有公开数据，待用实测数据补充", style="detail")

    # 下：负载重心的转移
    y0 = 506
    h0 = 686 - y0
    outline(s, (32, y0, 1216, h0), line="grey_d", width=1.5, dash=True)
    text(s, (38, y0, 64, h0), "重心\n转移", style="label_big", align="center", valign="middle", check=False)
    # 今天
    box(s, (110, y0 + 12, 226, h0 - 24),
        "@@今天@@\n推理在云端，端侧负责执行\n压力集中在被拉起的 App\n按次发起的问答与指令为主", fill="grey_l",
        style="body", gap_pt=5)
    # 三条趋势
    tx, tw = 356, 410
    block_arrow(s, (tx - 16, y0 + h0 / 2 - 10, 14, 20), fill="grey_m")
    text(s, (tx + 4, y0 + 8, tw - 8, 20), "**三条趋势推动负载下沉端侧**", style="body", color="accent", check=False)
    text(s, (tx + 4, y0 + 32, tw - 8, h0 - 38),
         "- **成本**：云端常驻 Agent 每用户每月 !!70–300 美元!!（估算），难以覆盖大众价位，简单任务必然下沉端侧\n"
         "- **隐私与离线**：个人数据处理留在端侧，弱网时可降级运行\n"
         "- **端侧模型变强**：AFM 3 级别的稀疏模型让端侧能承接规划类工作",
         style="detail", gap_pt=4)
    block_arrow(s, (tx + tw + 2, y0 + h0 / 2 - 10, 16, 20), fill="grey_m")
    # 未来：常驻代理
    fx = tx + tw + 26
    fw = 1240 - fx
    text(s, (fx, y0 + 8, fw, 20), "**未来：常驻代理，端侧同时承载四类负载**", style="body", color="accent", check=False)
    loads = ["常驻的模型\n与它的 KV", "长时间存活、\n可暂停恢复的\n执行环境", "Agent 持有的\n个人记忆", "被 Agent\n拉起的 App"]
    g = 8
    lw = (fw - 3 * g) / 4
    for i, ld in enumerate(loads):
        box(s, (fx + i * (lw + g), y0 + 34, lw, h0 - 70), ld, fill="peach_l", line="red", line_width=1.25,
            color="accent", style="detail")
    text(s, (fx, y0 + h0 - 32, fw, 26), "负载重心从「App」移到「模型 + Agent 状态」",
         style="detail", align="center", valign="middle")
    footnote(s, "来源：报告 2.1；产品数据见参考资料 B1、R1、H1、G1、A2、D1，成功率为发布会或厂商口径；"
                "应用拉起压力引自 2027 立项调研场景分析（M1-2）；单位成本为估算（D1-1）。", y=694, w=1120)


# ---------------------------------------------------------------- 2.2.1 参考负载

@page
def reference_load(prs):
    s = new_slide(prs, "参考负载「贴身秘书」：", "单个常驻主 Agent、低并发，各项需求由同一组任务原型推出",
                  crumb=CRUMB + " › 参考负载")
    # 设定与约束
    outline(s, (32, 88, 1216, 120), line="grey_line")
    text(s, (36, 88, 86, 120), "设定与\n约束", style="label_big", align="center", valign="middle", check=False)
    text(s, (130, 96, 536, 108),
         "- **设定**：一个常驻的主 Agent，同一时刻最多再跑 1–2 个子任务，代用户处理日常事务；属于@@单 Agent、低并发@@的负载\n"
         "- **机型**：2027 年旗舰，内存 !!12–16GB!!，闪存 UFS 4.x",
         style="body", gap_pt=5, valign="middle")
    rect(s, (676, 100, 0.75, 96), "grey_m")
    text(s, (690, 96, 550, 108),
         "- **端侧模型**：以 1–4B 激活参数为主，包括 AFM 3 这类稀疏模型；复杂任务可回落云端\n"
         "- **执行方式**：通过 App Intents、AppFunctions、MCP 或系统 API\n"
         "- **不在负载定义内**：多 Agent 并发、GUI 自动化（2026-11-03 立项讨论已排除）",
         style="body", gap_pt=5, valign="middle")

    # T1–T5 任务原型
    ty = 218
    text(s, (32, ty, 1216, 20), "**五类任务原型：三项系统服务与记忆的负载都从这一组原型推出**", style="body", color="accent", check=False)
    cols = ["原型", "例子", "交互性", "每天次数（估算）", "主要特征"]
    rows = [
        ["T1 即时指令", "「把明天 9 点的会推迟半小时并通知参会人」", "前台，用户在等", "8–10", "轮数少，有发消息类写操作"],
        ["T2 跨应用事务", "订票、订餐、打车、比价下单", "前台，关键步骤需确认", "1.5–3", "多步工具调用，含支付等不可逆操作，读入大量外部内容"],
        ["T3 长程任务", "旅行规划、报销整理、周报汇总", "可后台，跨数分钟到数小时，用户会切走再切回", "1–2", "上下文长，可拆 1–2 个并行子任务，需要暂停与恢复"],
        ["T4 后台感知与分拣", "消息、邮件、通知分拣与摘要；日程冲突检测；待办提取", "后台，事件触发", "约 100 条事件，\n合并成 15–45 批",
         "次数多、单次小、功耗敏感，读入的内容全部来自第三方"],
        ["T5 个人记忆问答", "「上次和张三谈的报价是多少」", "前台", "5–6", "以检索为主，生成短"],
    ]
    ratios = [0.95, 1.75, 1.55, 0.9, 2.0]
    th = table_height(1216, cols, rows, ratios, style="body", pad=(6, 3))
    table(s, (32, ty + 22, 1216, th), cols, rows, widths=ratios, style="body", pad=(6, 3),
          align=["left", "left", "left", "center", "left"], fit=False)

    # 下左：晚间峰值时刻
    py = ty + 22 + th * 1.04 + 12
    ph = 686 - py
    PW = 600
    inner = lib.panel(s, (32, py + 10, PW, ph - 10), "晚间峰值时刻的设定")
    ix, iy, iw, ih = inner
    lanes = [
        ("前台", [("重应用：游戏或视频", "warn")]),
        ("运行中", [("T3 长程任务：主任务 + 1 个子任务", "new"), ("T4 后台批处理", "new")]),
        ("停放待用", [("T2 会话", "park"), ("T5 会话", "park")]),
    ]
    lh = 24
    gap = 6
    for k, (lab, items) in enumerate(lanes):
        yy = iy + k * (lh + gap)
        box(s, (ix, yy, 70, lh), f"**{lab}**", fill="blue_m", style="detail")
        n = len(items)
        mw = (iw - 78 - 8 * (n - 1)) / n
        for j, (t, kind) in enumerate(items):
            b = (ix + 78 + j * (mw + 8), yy, mw, lh)
            if kind == "warn":
                box(s, b, t, fill="pink_l", line="grey_d", style="detail")
            elif kind == "new":
                box(s, b, t, fill="peach_l", line="red", line_width=1.25, color="accent", style="detail")
            else:
                box(s, b, t, fill="bg", line="grey_d", dash=True, style="detail")
    text(s, (ix, iy + 3 * (lh + gap), iw, ih - 3 * (lh + gap)),
         "**设计点**：Agent 侧峰值驻留约 !!5.2GB!!，12GB 机型缺约 !!1.2GB!!（估算，见 2.2.5）",
         style="detail", valign="middle")

    # 下右：数据依据与缺口
    RX = 32 + PW + 16
    RW = 1248 - RX
    inner = lib.panel(s, (RX, py + 10, RW, ph - 10), "数据依据与缺口")
    ix, iy, iw, ih = inner
    text(s, (ix, iy - 2, iw, ih + 4),
         "- **事件量**：278 名 Android 用户、约 79 万条通知的实测，中位数每天 56 条；另有二手数据称大学生每天超过 100 条。"
         "加上收发消息和邮件，原始事件取每天约 100 条\n"
         "- **口径**：四份负载笔记中各原型的次数略有出入（如 T2 取 1.5 与 3），本页给区间；后续结论为数量级判断，对次数不敏感\n"
         "- !!最大的数据缺口!!：公开资料中没有任何一份手机上「秘书类」Agent 的使用轨迹；@@实测数据可直接替换本页的估算参数@@",
         style="detail", gap_pt=4)
    footnote(s, "来源：报告 2.2.1；通知实测见参考资料 W12（Pielot 等，MobileHCI 2018）；各项负载的完整推导见 notes/L-C1～L-C4；"
                "峰值驻留与缺口为估算，见报告 2.2.5。", y=694, w=1120)

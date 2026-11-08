"""第三部分 · 总体架构（报告 3.1）：章节页、总体架构（solution-arch-overview 版式）、会话档位与四组件联动。"""

import lib
from lib import box, table, text
from registry import page

CRUMB = "三、架构与关键技术 › 总体架构"


@page
def section3(prs):
    lib.section_slide(prs, "三、", "架构与关键技术",
                      "以 Agent 会话为一等对象的总体架构，以及推理、沙箱、记忆、通用内存与模型内存五部分的目标架构和 15 项关键技术")


@page
def overall_arch(prs):
    s = lib.new_slide(prs, "Agent OS 总体架构：", "以 Agent 会话为一等对象，四个系统服务围绕会话分工协同",
                      crumb=CRUMB, takeaway="目标：会话的算力、执行边界、记忆与内存由操作系统统一管理，四个组件按四条约定协同")
    lib.head_card(s, (32, 128, 664, 92), "核心\n挑战",
                  "**资源以任务为单位产生**：一次跨应用下单涉及多个应用与进程\n"
                  "**风险随任务跨时间传播**：不可信内容从读入一直影响到发送\n"
                  "**进程主体无法对应**：推理服务代持多个会话的 KV，回收无从区分")
    lib.head_card(s, (712, 128, 536, 92), "架构\n理念",
                  "**会话为一等对象**：主体、档位、标签、状态、账本\n"
                  "**机制归系统**：调度、隔离、记忆、内存由 OS 提供\n"
                  "**策略归 Agent**：编排与决策保留在应用框架层")

    # ---------------- 左：分层架构
    x, w = 32, 664
    lib.outline(s, (x, 236, w, 26), line="grey_d", width=1.0)
    text(s, (x, 236, w, 26), "**应用与 Agent 框架**（不在本次投入范围）", style="body", color="grey_d", align="center",
         valign="middle", check=False)
    cw = (w - 12 - 2 * 6) / 3
    for i, t in enumerate(["交互：语音、文本、生成式界面", "Agent 运行时：规划、编排、工具选择",
                           "应用能力接口：App Intents、AppFunctions、MCP"]):
        box(s, (x + 6 + i * (cw + 6), 266, cw, 40), t, fill="grey_l", line="grey_line")

    lib.outline(s, (x, 316, w, 26), line="primary_text", width=1.25)
    text(s, (x, 316, w, 26), "**Agent OS 系统服务层**（本次投入）", style="body", color="primary_text", align="center",
         valign="middle", check=False)
    lib.rect(s, (x, 346, w, 244), "grey_l")
    box(s, (x + 6, 352, w - 12, 34), "**会话管理器**：会话对象 = 主体 + 档位 + 标签 + 状态单元 + 账本；统一计算会话档位并广播事件",
        fill="blue_m")
    comps = [
        ("推理服务", "会话级调度与抢占\nKV / 前缀复用与多适配器\n端云协同路由"),
        ("执行沙箱", "会话级隔离与状态底座\n策略引擎与数据标签\n出口代理与凭证托管"),
        ("记忆服务", "分层存储与检索\n记忆写入治理\n系统级索引与授权"),
        ("内存管理", "通用内存：记账与水线、主动回收、冷热预取\n模型内存：KV 分代、专家工作集、加载零拷贝"),
    ]
    ccw = (w - 12 - 3 * 6) / 4
    for i, (name, md) in enumerate(comps):
        bx = x + 6 + i * (ccw + 6)
        box(s, (bx, 396, ccw, 26), f"**{name}**", fill="peach_l", line="red", line_width=1.25, color="accent")
        box(s, (bx, 426, ccw, 156), md, fill="bg", line="red", line_width=1.0, style="detail")
        lib.arrow(s, (bx + ccw / 2, 386), (bx + ccw / 2, 396), color="dark")

    lib.outline(s, (x, 598, w, 26), line="grey_d", width=1.0)
    text(s, (x, 598, w, 26), "**内核与硬件**", style="body", color="grey_d", align="center", valign="middle", check=False)
    for i, t in enumerate(["memcg、PSI、LMKD、zRAM", "LSM、seccomp、AVF pKVM", "NPU HAL、dma-buf、UFS"]):
        box(s, (x + 6 + i * (cw + 6), 628, cw, 40), t, fill="grey_m")
    lib.arrow(s, (x + w / 2, 306), (x + w / 2, 316), color="dark")
    lib.arrow(s, (x + w / 2, 590), (x + w / 2, 598), color="dark")

    # ---------------- 右：四条贯穿性约定
    lib.outline(s, (712, 236, 536, 436), line="grey_line")
    text(s, (728, 246, 504, 26), "**四条贯穿性约定**", style="emphasis", color="accent", valign="middle", check=False)
    items = [
        ("档位统一计算", "会话档位由会话管理器统一计算，同时驱动推理优先级、隔离与确认强度、记忆读取路径、内存保底与回收顺序",
         "避免推理全速运行而内存同时回收其 KV"),
        ("标签全链路一致", "来源与敏感度标签由沙箱签发，随记忆条目持久化，供端云路由与前缀复用判定",
         "任一环节丢失标签，注入内容即可成为可信记忆"),
        ("内存统一记账", "权重、KV、适配器、沙箱与索引均记入会话或服务账本，代持内存归属到请求会话",
         "回收决策建立在完整信息之上"),
        ("跨组件以事件协同", "暂停、回收、驱逐、降级以事件通知，由持有策略的组件决定具体动作",
         "机制归系统、策略归 Agent，避免环形调用"),
    ]
    slot = 392 / len(items)
    for i, (name, how, why) in enumerate(items):
        y = 278 + i * slot
        lib.badge(s, 742, y + 14, i + 1, d=26)
        text(s, (764, y + 1, 472, 26), f"**{name}**", style="emphasis", color="accent", valign="middle")
        text(s, (764, y + 30, 472, slot - 32), f"- **做法**：{how}\n- **理由**：@@{why}@@", style="body", gap_pt=2)
    lib.footnote(s, "来源：报告 3.1.1–3.1.3；各组件的目标架构与关键技术见后续页面。", y=694)


@page
def tier_contract(prs):
    s = lib.new_slide(prs, "会话档位与四组件联动：", "同一档位驱动四个组件，使切回时延与峰值内存目标同时成立",
                      crumb=CRUMB + " › 会话档位")
    table(s, (32, 88, 1216, 336), ["会话档位", "进入条件", "推理服务", "执行沙箱", "记忆服务", "内存管理"], [
        ["**交互**", "用户正在等待结果：前台对话、确认弹窗、实时语音", "最高优先级，可抢占后台会话的 decode；该会话 KV 钉住",
         "运行；敏感动作按档位确认", "检索走低时延路径", "memcg 保底；不回收其 KV 与沙箱内存"],
        ["**后台活跃**", "用户切走，任务仍在执行（长程任务、后台分拣）", "低优先级，可被抢占；分块 prefill，让出算力",
         "运行；需确认的动作排队，待用户返回处理", "接触过不可信内容的会话，写入先进入待确认区", "弹性供给，压力下先于前台应用降级"],
        ["**待机**", "等待用户确认、外部事件或工具返回", "不占用算力；KV 可降位宽或换出", "冻结进程，内存保留", "—",
         "沙箱与 KV 内存可压缩或换出"],
        ["**挂起**", "长时间无活动，或内存压力超过阈值", "KV 换出到闪存或丢弃待重算；共享前缀保留", "快照落盘后释放内存",
         "必要时将被驱逐的上下文写摘要入库", "释放至最低；恢复时按工作集预取"],
        ["**销毁**", "任务完成或被取消", "释放 KV", "销毁并清算，审计日志落盘", "会话记忆按策略归档或丢弃", "账本清零"],
    ], widths=[0.75, 1.6, 1.7, 1.45, 1.45, 1.5], style="body", fit=True, check=False, pad=(5, 3),
        align=["center", "left", "left", "left", "left", "left"])

    for k, (title, steps) in enumerate([
        ("例一：用户切走长程任务，再切回", [
            "会话管理器将会话从「交互」降为「后台活跃」，数分钟无进展后降为「挂起」",
            "「挂起」事件广播：推理服务将 KV 换出到闪存或标记为可重算；沙箱先快照、再释放进程内存；内存管理按账本将内存归还前台应用",
            "用户切回时会话升为「交互」，三项恢复并行发起：内存管理按工作集预取、沙箱从快照恢复、推理服务换入 KV",
            "@@整体恢复目标 ≤1 秒@@：沙箱部分 ≤300 毫秒，KV 换入 0.2–0.9 秒，二者并行",
        ]),
        ("例二：后台分拣读到一条注入消息", [
            "后台分拣会话读入一封邮件，沙箱为该内容签发「不可信外部内容」标签",
            "模型被诱导调用「发送消息」且参数含该内容，沙箱按定档规则将此次调用升为「每次确认」，排队等待用户",
            "分拣结果写入记忆时，标签随条目持久化；其他会话检索到该条记忆时，读出的内容仍为低完整性",
            "@@注入风险不在读入时刻，而在于被跨时间、跨会话带到有副作用的动作上@@，因此标签必须全链路一致",
        ]),
    ]):
        x = 32 + k * 616
        lib.round_card(s, (x, 440, 600, 244))
        text(s, (x + 14, 448, 572, 22), f"**{title}**", style="lead", color="accent", check=False)
        md = "\n".join(f"- {t}" for t in steps)
        text(s, (x + 14, 476, 572, 204), md, style="body", gap_pt=3)
    lib.footnote(s, "注：2027 年建议仅实现由用户可见事件触发的「交互」「后台」两档，基于注意力预测的升档列入 2028 年以后（待决策，见第四部分）。"
                    "来源：报告 3.1.4。", y=694, w=1200)

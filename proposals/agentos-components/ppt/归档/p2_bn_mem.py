"""第二部分 · 瓶颈分析：记忆服务（报告 2.4.3）。版式：solution.problem-arch-callouts。
中央架构图在本模块自绘；两侧问题卡、扫描卡、连线、底部通栏与编号用 pages.bn_* 部件。"""

import lib
from lib import box, text
from pages import BN_Y0, bn_badges, bn_bottom, bn_layer, bn_sep, bn_side
from registry import page

X1, W = 434, 446   # 中央图内容区 x 434–880；右缘留出 ④ 号连线的通道


@page
def bottleneck_memory_service(prs):
    s = lib.new_slide(prs, "记忆服务瓶颈分析：", "写入缺少治理，冲突与遗忘无机制，授权粒度与访问频率不匹配",
                      crumb="二、场景与负载瓶颈 › 瓶颈分析 › 记忆服务")

    # ---------------- 中央：当前端侧记忆相关架构
    # 应用层：第三方 Agent 的应用内记忆模块，各 App 的私有数据与通知
    y = BN_Y0
    bn_layer(s, y + 58, 48, "应用")            # 层名放在下半部，避开 ① 号连线
    lib.outline(s, (X1, y + 2, 238, 104), line="grey_d", width=1.0, kind="rounded", radius=8)
    text(s, (X1 + 4, y + 4, 230, 18), "**第三方 Agent 应用**", style="detail", align="center",
         check=False)
    ext = (X1 + 8, y + 24, 222, 38)
    box(s, ext, "**模型抽取事实**：约 110 条事件 → 约 39 条记忆/天", fill="pink_l")
    box(s, (X1 + 8, y + 66, 222, 36), "**检索与注入**：约 32 次/天，单次上限约 3K token", fill="blue_l")
    app = (X1 + 252, y + 2, W - 252, 104)
    box(s, app, "**各 App 的私有数据与通知**\n消息 40、其他通知 31\n邮件 20、日程 4、照片 5\n（条/天，估算）", fill="beige")
    lib.arrow(s, (app[0] - 1, y + 43), (X1 + 239, y + 43), color="dark")
    bn_sep(s, y + 110)

    # 系统层：系统助手的个人上下文
    y = BN_Y0 + 114
    bn_layer(s, y, 88, "系统")
    box(s, (X1, y + 2, 124, 84), "**系统助手的**\n**个人上下文**\n!!不向第三方 Agent!!\n!!开放读取!!", fill="grey_l", line="grey_d")
    rx, rw = X1 + 130, W - 130
    for i, t in enumerate(["**Apple**（iOS）：语义索引、App Intents 实体",
                           "**Google**（Android）：Magic Cue、个人上下文",
                           "**华为**（HarmonyOS）：小艺记忆"]):
        box(s, (rx, y + 2 + i * 29, rw, 26), t, fill="blue_l")
    bn_sep(s, y + 92)

    # 框架层：应用内记忆框架、权限框架
    y = BN_Y0 + 210
    bn_layer(s, y, 46, "框架")                 # 层名放在上半部，避开 ② 号连线
    mem = (X1, y + 2, 256, 84)
    box(s, mem, "**应用内记忆框架**（Mem0、Letta 等）\n条目没有版本与有效期\n删除后无法确认派生数据已清除", fill="pink_l")
    perm = (X1 + 264, y + 2, W - 264, 84)
    box(s, perm, "**权限框架**\n运行时权限、应用级连接\n最细到应用级或整块只读", fill="purple_l")
    bn_sep(s, y + 92)

    # 模型层：嵌入模型、端侧推理
    y = BN_Y0 + 306
    bn_layer(s, y, 68, "模型")
    box(s, (X1, y + 2, 220, 64), "**嵌入模型** 约 200MB\n应用与助手各自加载，无系统托管", fill="beige")
    box(s, (X1 + 226, y + 2, W - 226, 64), "**端侧推理**\n写入路径 4–9 万 prefill/天\n没有后台批作业类别", fill="beige")
    bn_sep(s, y + 72)

    # 存储层：向量索引与记忆库
    y = BN_Y0 + 382
    bn_layer(s, y, 84, "存储")
    idx = (X1, y + 4, W, 78)
    box(s, idx, "**向量索引与记忆库**（闪存）：3 年 4–12 万条\n全扫描外推 120–490 毫秒，T1 检索预算 ≤150 毫秒\n"
                "换代整库重建约 16–44 分钟（估算）；最佳检索 recall@5 仅 0.73", fill="grey_m")

    targets = {
        "ext": (ext[0] - 4, ext[1] + 4), "mem": (mem[0] + 2, mem[1] + 70),
        "perm": (perm[0] + perm[2] - 2, perm[1] + 2), "idx": (idx[0] + 6, idx[1] + 2),
    }

    # ---------------- 两侧问题卡与业界技术扫描卡
    bn_side(s, "left", [
        ("callout", "①", "写入缺少系统级治理：记忆由模型抽取写入，其中每天约 31 条来自不可信内容，没有来源与完整性标签", 86, "ext"),
        ("card", "Mem0", "2025–2026 · 开源与云服务",
         "由模型抽取事实写入向量库；2026-04 起新算法只加不删，冲突留给检索", "没有溯源字段，不做遗忘", 120),
        ("callout", "②", "冲突更新与遗忘没有机制：每天约 20 次过期删除、2–4 次冲突更新，主流框架无有效期，删除后无法确认派生数据已清除", 110, "mem"),
        ("card", "Zep / Graphiti", "2025-01 · Zep AI，开源",
         "双时间轴知识图谱：新事实以时间边使旧事实失效，并保留原始情景", "旧事实只失效、不物理删除", 120),
        ("card", "ChatGPT Memory", "OpenAI · 云端产品",
         "已保存记忆加聊天历史引用；条目可见、可删除，关闭历史后 30 天内清除", "记忆注入已被演示；没有来源标签", 120),
    ], targets)
    bn_side(s, "right", [
        ("callout", "④", "授权粒度与访问频率不匹配：授权最细只到应用级，而每天约有 75 次访问判定，用户只能承受 2–3 次弹窗", 86, "perm"),
        ("card", "Apple 语义索引", "iOS 18 起 · Apple",
         "应用把实体声明为 IndexedEntity，进入 Core Spotlight 的词法与语义检索", "读取侧对第三方的开放范围未公开", 117),
        ("card", "Google 个人上下文", "2025–2026 · Google",
         "Magic Cue 用端侧 Gemini Nano 加云端增强；Gemini 个人上下文读取云账户数据", "限自家应用，按应用级连接授权", 117),
        ("card", "Letta / MemGPT", "2026-02 · Letta，开源",
         "core 块常驻、archival 外存的两层虚拟上下文，记忆改存为 git 文件", "没有完整性标签，共享块整块只读", 117),
        ("card", "OpenViking", "2026 · 火山引擎，开源",
         "目录范式加 L0/L1/L2 分层加载，会话结束时抽取六类记忆", "服务端数据库，端侧需裁剪", 117),
    ], targets)
    bn_bottom(s, "③", "规模与常驻成本未纳入系统管理：3 年规模全扫描外推 120–490 毫秒，嵌入模型约 200MB 无系统托管",
              targets["idx"],
              "@@端侧分层记忆存储与检索@@（对应 ③）、@@记忆写入治理@@（对应 ①②）、@@系统级个人语义索引与授权@@（对应 ④）")
    bn_badges(s, targets, [("1", "ext"), ("2", "mem"), ("3", "idx"), ("4", "perm")])

    lib.footnote(s, "来源：报告 2.2.4 负载估算、2.4.3 瓶颈分析；P-C3 原型对比笔记与证据库 C3；全扫描时延由 sqlite-vec 桌面实测外推（W14），"
                    "检索质量见 LongMemEval（W11）。", y=694, w=1100)

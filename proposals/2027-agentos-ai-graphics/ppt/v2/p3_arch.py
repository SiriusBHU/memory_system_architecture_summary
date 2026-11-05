"""第三部分：架构（Agent OS 总体构想、总体架构、叠加场景走查、关键技术总览；AI + 图形架构与总览）。"""

from lib import (BODY_TOP, arrow, box, card, footnote, new_slide, num_badge, points, table, text, titled_card)
from registry import page, tpl

tpl("common.section-basic", num="03", title="架构与关键技术", subtitle="模型内存成为系统一等公民：三项关键技术加一个评估平台")


# ------------------------------------------------------------------ A1 总体构想
@page
def vision(prs):
    s = new_slide(prs, "Agent OS总体构想", "模型内存成为系统的一等公民",
                  "把模型内存从应用私有、被钉住的缓冲，变成系统统一记账、可回收、可共享的资源")
    table(s, (32, 128, 1216, 372),
          ["维度", "现状：模型内存游离在系统治理之外", "目标：模型内存成为一等公民", "落点"],
          [
              ["统一记账",
               "权重、专家缓存、KV、NPU 缓冲分散在框架私有堆、dma-buf 和 NPU 驱动里；memcg、PSI 和 lmkd 只看到一部分，压力判断失真",
               "所有模型内存计入同一本「模型内存账」，与应用内存一起参与压力判断和回收排序；每个 Agent、每个会话都有配额",
               "共享底座：统一记账、预算账本"],
              ["可回收",
               "权重被拷进私有缓冲并长期钉住，KV 在 LRU 之外；内存一紧，系统能做的只有杀后台应用",
               "权重保持为干净的文件页，压力大时零成本丢弃、再从 UFS 读回；专家缓存按预算收缩；KV 块可压缩、换出或丢弃重算",
               "KT2-A、KT2-B、KT3"],
              ["可共享",
               "同一基座权重被多个会话、多个 LoRA、CPU 与 NPU 各存一份；页缓存、框架缓冲、NPU 缓冲之间重复拷贝",
               "按权重内容做共享映射，CPU 与 NPU 共用文件页，一份权重多方使用",
               "KT3"],
              ["加载与驻留",
               "缺页式 4KB 随机读打不满 UFS；NPU 需大块连续内存（8GB CMA 分配约 6.44 秒，待核实）；MoE 专家命中率在小缓存下可跌到 0%",
               "页对齐的 NPU 友好布局 + 大块顺序预读 + 文件页直接映射给 NPU；专家按热度分层驻留、跨层预测预取",
               "KT3、KT2-A"],
              ["非模型内存",
               "模型挤占后，应用的 .so 文件页被逐出、匿名页被压进 zram；冷启动等锁等 I/O，切回前台时缺页解压落在关键路径",
               "共享库缺页与回收脱离全局锁；SPE 硬件访问证据驱动「切回前预取、确认冷才换出」",
               "KT1-a、KT1-b、KT1-c"],
          ], widths=[1.0, 3.3, 3.3, 1.5], style="detail", header_style="body_strong")

    titled_card(s, (32, 514, 600, 174), "为什么必须由系统来做",
                "- 内存是准入门槛：Gemini Intelligence 与 iOS 27 最强端侧模型都要求 !!12GB!!，加 DRAM 的路被价格堵死（2026Q2 合约价约 !!$20/GB!!）。\n"
                "- 只有系统同时看得到应用、Agent 和模型三方的内存，单个推理框架或应用无法做全局取舍。\n"
                "- 每多出 1GB 等效可用内存，约等于每台省下 !!$20!! 的 DRAM（按 2026Q2 合约价估算）。",
                style="body")
    titled_card(s, (648, 514, 600, 174), "立项边界",
                "- **做**：应用与 Agent 的非模型内存（KT1）、模型动态内存（KT2）、模型静态内存与加载（KT3），以及支撑评估的仿真平台（S1、S2）。\n"
                "- **不做**：改动模型结构；GUI Agent；跨 IP 的带宽、算力与温度 QoS；多 Agent 与端侧后台 Agent（预计 2028 年后）。",
                style="body")


# ------------------------------------------------------------------ A2 总体架构
@page
def arch(prs):
    s = new_slide(prs, "Agent OS总体架构", "一本账、一套冷热证据、一条IO队列",
                  "三项关键技术分管三类内存，共用同一个底座；仿真平台为所有目标提供基线与校准")
    X0, LW = 32, 66
    CX = X0 + LW + 8
    SUPW = 124
    SX = 900 - SUPW
    RW = SX - 10 - CX                       # 层内容宽度
    KW = (RW - 2 * 10) / 3

    def layer(y, h, name):
        box(s, (X0, y, LW, h), name, fill="primary", color="on_primary", style="body_strong")

    layer(128, 48, "负载层")
    loads = ["**前台应用**\n视频、地图、购物", "**被拉起的应用**\nAgent 调起与切换",
             "**Agent 框架**\n意图、规划、工具", "**端侧模型**\n权重、专家、KV"]
    lw = (RW - 3 * 8) / 4
    for i, t in enumerate(loads):
        box(s, (CX + i * (lw + 8), 128, lw, 48), t, fill="surface", style="detail")

    layer(186, 320, "Agent OS\n内存与IO")
    cols = [
        ("KT1 智慧化内存管理", "应用与 Agent 的非模型内存",
         [("KT1-a .so 文件页锁优化", "I/O 型文件缺页走 VMA 锁；rmap trylock + 批量跳过；关键页软保护"),
          ("KT1-b SPE 冷热识别 + 预取", "SPE 样本映射到物理页；切后台记恢复集，切回时批量换入"),
          ("KT1-c SPE 冷热识别 + zram 换出", "三项证据一致才换出；按可压缩性分流；经 DAMOS 注入")]),
        ("KT2 Agent 内存组件", "模型动态内存",
         [("KT2-A 稀疏权重分层", "专家、PLE、神经元簇统一建热度模型；跨层预测预取；策略在线选择；未命中走低位宽兜底"),
          ("KT2-B KV 块池", "KV 切块入账；按容忍度分级压缩；换出与重算择优；系统提示与工具 schema 前缀复用")]),
        ("KT3 模型翻译组件", "模型静态内存与加载",
         [("页对齐 NPU 友好布局", "离线按层、按专家顺序打包"),
          ("文件页 → NPU IOMMU 映射", "dma-buf 导出，NPU 零拷贝可回收"),
          ("大块顺序预读", "按调度顺序大块读，打满 UFS"),
          ("权重按内容共享", "多会话、CPU 与 NPU 共用一份")]),
    ]
    top, ph = 186, 256
    for i, (name, sub, items) in enumerate(cols):
        x = CX + i * (KW + 10)
        card(s, (x, top, KW, ph), fill="surface_light", shadow=False)
        text(s, (x + 8, top + 6, KW - 16, 20), f"@@{name}@@", style="body")
        text(s, (x + 8, top + 26, KW - 16, 16), sub, style="caption")
        n = len(items)
        iy, avail, gap = top + 46, ph - 46 - 6, 5
        ih = (avail - gap * (n - 1)) / n
        for j, (t, d) in enumerate(items):
            box(s, (x + 6, iy + j * (ih + gap), KW - 12, ih), f"**{t}**\n{d}", fill="highlight",
                style="caption", align="left", valign="middle", inset=5)

    by = top + ph + 6
    shared = [("统一模型内存记账", "权重 / 专家 / KV / NPU 缓冲入账"), ("统一内存预算账本", "KT1–KT3 共用配额与优先级"),
              ("冷热模型", "SPE 证明热、页表证明冷"), ("IO 调度队列", "加载、预取、换入统一排队")]
    sw = (RW - 3 * 6) / 4
    for i, (t, d) in enumerate(shared):
        box(s, (CX + i * (sw + 6), by, sw, 506 - by), f"**{t}**\n{d}", fill="highlight", line="highlight_strong",
            style="caption", inset=4)

    layer(516, 38, "内核基座")
    kern = ["memcg · PSI · lmkd", "缺页 · rmap · LRU / MGLRU", "DAMON · Accessed 位 · perf", "readahead · zram · dma-buf · SMMU"]
    for i, t in enumerate(kern):
        box(s, (CX + i * (sw + 6), 516, sw, 38), t, fill="surface", style="caption")
    layer(564, 38, "硬件")
    hw = ["LPDDR5X", "NPU（SMMU）", "CPU（Arm SPE）", "UFS 4.x / 5.0"]
    for i, t in enumerate(hw):
        box(s, (CX + i * (sw + 6), 564, sw, 38), t, fill="surface", style="detail")

    card(s, (SX, 128, SUPW, 474), fill="highlight_blue", shadow=False)
    text(s, (SX + 8, 134, SUPW - 16, 36), "@@支撑能力@@\n性能跟踪与仿真", style="caption")
    sup = [("S1 云转端评估", "代价与收益决策模型；风险评估：真机指标、标准负载集、仿真校准"),
           ("S2 单 Agent 并行化", "工具语义标签、依赖图抽取、带宽感知的并行度上限")]
    for j, (t, d) in enumerate(sup):
        box(s, (SX + 6, 176 + j * 150, SUPW - 12, 140), f"**{t}**\n{d}", fill="bg", style="caption",
            align="left", inset=6)
    box(s, (SX + 6, 478, SUPW - 12, 118), "**向 KT1–KT3 输出**\n统一基线\n目标校准\n收益评估", fill="bg",
        style="caption", align="left", inset=6)

    flows = [("① 硬件访问证据", "SPE 样本 → 冷热模型 → KT1-b 预取 / KT1-c 换出"),
             ("② 模型数据通路", "UFS 权重文件 → KT3 映射 → NPU 零拷贝；KT2-A 专家预取共用 IO 队列"),
             ("③ 记账闭环", "各组件用量 → 统一记账 → 预算账本 → 回收排序，替代直接杀应用")]
    fw = (868 - 2 * 8) / 3
    for i, (t, d) in enumerate(flows):
        box(s, (32 + i * (fw + 8), 614, fw, 74), f"@@{t}@@\n{d}", fill="bg", line="primary_text",
            style="detail", align="left", inset=8)

    rx, rw = 916, 332
    card(s, (rx, 128, rw, 560))
    text(s, (rx + 14, 140, rw - 28, 24), "架构设计要点", style="emphasis", color="primary_text")
    pts = [
        ("一本账", "模型内存与应用内存同账：压力判断、回收排序、配额基于同一份数据，模型不再是回收看不见的黑洞。"),
        ("一套冷热证据", "SPE 采样证明热，页表 Accessed 位与代龄证明冷；预取只用热证据，换出要求冷证据一致。"),
        ("一条 IO 队列", "模型加载、专家预取、zram 换入按截止时间和带宽统一调度，打满 UFS 又不阻塞前台缺页。"),
        ("不改主路径", "策略经 memcg、memory.reclaim、DAMOS、dma-buf 等既有接口注入，降低合入和维护成本。"),
        ("评估先行", "S1 先建标准负载集和真机基线，所有建议区间校准后才定为承诺值。"),
    ]
    points(s, rx + 14, 176, rw - 28, 504, pts)

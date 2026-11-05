"""第二部分：问题——未来场景与需求、当代系统瓶颈（非模型内存、模型内存、评估与效率）、AI + 图形场景与瓶颈。"""

from lib import (arrow, box, card, kpi, new_slide, num_badge, points, table, text, titled_card)
from registry import page, tpl

tpl("common.section-basic", num="02", title="问题", subtitle="叠加场景成为常态，当代系统的内存供给撑不住")


# ------------------------------------------------------------------ Q-1 场景与需求
@page
def scenarios(prs):
    s = new_slide(prs, "未来终端场景", "Agent与应用叠加成为常态",
                  "Agent 不替代应用而是叠加在应用之上；在 12GB 机型上，模型常驻后留给应用的内存只剩 2.5–7.5GB")
    cx, cw = 32, 420
    card(s, (cx, 128, cw, 560))
    text(s, (cx + 14, 138, cw - 28, 20), "@@12GB 机型的内存预算@@（估算）", style="body")
    bx, btop, bbot = cx + 30, 176, 520
    k = (bbot - btop) / 12

    def seg(lo, hi, fill, line=None, dash=False):
        box(s, (bx, bbot - hi * k, 92, (hi - lo) * k), "", fill=fill, line=line, dash=dash, check=False)

    seg(0, 3.5, "primary")
    seg(3.5, 4.5, "accent")
    seg(4.5, 9.5, "highlight", line="accent", dash=True)
    seg(9.5, 12, "surface")
    lx = bx + 104
    text(s, (lx, bbot - 2.2 * k, 270, 34), "**系统 + 驱动 + 常驻服务**\n约 3–4GB（需真机核实）", style="caption")
    text(s, (lx, bbot - 5.0 * k, 270, 50), "**端侧模型常驻 1–6GB**\nGemma 4 E2B 约 1.1GB、E4B 约 2.5GB（官方）；Nano 4 Full 据报约 5.9GB", style="caption")
    text(s, (lx, bbot - 11.2 * k, 270, 50), "**留给前台与后台应用**\n约 !!2.5–7.5GB!!（12 − 3.5 − 模型）", style="caption")
    text(s, (bx - 6, bbot + 4, 110, 16), "12GB", style="caption", align="center")
    table(s, (cx + 14, 548, cw - 28, 130), ["单个负载（AppFlow 实测）", "匿名页", "文件页"],
          [["Photoshop", "636MB", "379MB"], ["TikTok", "616MB", "434MB"], ["端侧模型 Qwen2.5 / Gemma", "307 / 710MB", "1637 / 1925MB"]],
          widths=[2.2, 1.0, 1.2], style="caption", header_style="caption")

    table(s, (468, 128, 780, 560), ["场景", "典型过程", "用户需求", "体验指标（建议，待校准）", "对应技术"],
          [["**S-A** 用应用时唤起 Agent", "刷视频、地图、购物时唤起 Agent，对当前内容做总结、比价、翻译",
            "前台不卡、不被杀；Agent 立即响应；回到应用时状态还在", "首 token：热 ≤1s，冷（含载入）≤3s；前台被杀 0 次", "KT3、KT1-c"],
           ["**S-B** Agent 调起应用完成任务（主场景）", "「订明天去上海的高铁并加到日历」：依次经接口或界面调起多个应用",
            "多应用任务快；每个应用冷启动不明显变慢；结束后不残留大量后台", "冷启动相对无 Agent 劣化 ≤10%；切回后热启动比例 ≥80%", "KT1-a / b / c"],
           ["**S-C** 长对话、长任务", "上下文累积到 8K–64K token，中途切去别的应用再切回",
            "多轮不变慢；切回来不用重算", "首 token 劣化 ≤2 倍；KV 占用有上限、可随压力回收", "KT2-B"],
           ["**S-D** 稀疏大模型上端", "30B 级 MoE 在 12–16GB 机型上分层驻留运行", "能跑、够快、不挤占前台",
            "解码 tokens/s、首 token 时延、峰值常驻内存", "KT2-A、KT3"],
           ["**S-E** 端云切换与单 Agent 并行", "弱网回落端侧；单个 Agent 内部并行调用多个工具", "切换无感；多步任务总时延下降",
            "切换额外时延 ≤500ms；多工具任务时延 -20%～-40%", "S1、S2"]],
          widths=[1.4, 2.1, 1.8, 2.0, 1.2], style="caption", header_style="detail")


# ------------------------------------------------------------------ Q-2 非模型内存瓶颈
@page
def bottleneck_sys(prs):
    s = new_slide(prs, "当代系统瓶颈（一）", "非模型内存：容量冻结之下回收撑不住",
                  "模型常驻后，回收在冷启动关键路径上叠加锁、I/O 与解压；各机制各管一段，彼此抵消")
    # 左：叠加场景下的回收链路（编号对应右侧）
    x0, w = 32, 560
    card(s, (x0, 128, w, 560))
    text(s, (x0 + 14, 138, w - 28, 20), "@@叠加场景下今天的系统在做什么@@", style="body")
    steps = [
        ("Agent 常驻端侧模型", "权重、KV、NPU 缓冲占去 1–6GB，内存余量骤降", None),
        ("kswapd 回收共享库文件页", "多进程映射的 .so 页被逐出；反向映射争抢 i_mmap_rwsem", 2),
        ("匿名页被压进 zram", "不分冷热，热页也可能被换出", 4),
        ("Agent 拉起应用 A（冷启动）", "major fault：等 folio 锁、等 I/O、等 rmap 锁", 2),
        ("用户切回应用 B", "zram 按需逐页解压，缺页落在前台关键路径", 3),
        ("压力顶满，lmkd 杀后台", "下次再用变成冷启动；预加载又加重压力", 5),
    ]
    y = 168
    for i, (t, d, ref) in enumerate(steps):
        box(s, (x0 + 20, y, w - 80, 66), f"**{t}**\n{d}", fill="surface" if ref else "highlight_blue", style="detail",
            align="left", inset=10)
        if ref:
            num_badge(s, x0 + w - 50, y + 22, ref)
        if i < len(steps) - 1:
            arrow(s, (x0 + 20 + (w - 80) / 2, y + 66), (x0 + 20 + (w - 80) / 2, y + 78), color="muted", width=1.5)
        y += 78
    text(s, (x0 + 20, y + 2, w - 40, 34), "红色编号对应右侧瓶颈；① 容量被冻结是所有环节的前提。", style="caption")

    rx, rw = 608, 640
    items = [
        ("① 容量被冻结", "移动 DRAM 合约价 2026Q1 环比 +58–63%，Q2 接近翻倍（约 $20/GB），TrendForce 判断 2027 年不会明显回落；加内存的路走不通，回收成了唯一杠杆。"),
        ("② 冷启动卡在锁与 I/O", "GB 级应用 !!86.6%!! 的冷启动超过 1 秒（AppFlow，Pixel 7/8）；Android 重负载下 kswapd 等 rmap 锁 !!≥300ms!!，i_mmap_rwsem 争用使回收效率从 48% 降到 27%。"),
        ("③ 换入不分冷热、不预取", "zram 按需换入，切回前台时大量缺页解压；对标研究的改进空间：ASAP 预取使切换时延 -22.2%，Ariadne 使重启时延 -50%（均为软件信号）。"),
        ("④ 冷热信号不准", "LSFMM 2026：多家 Android 厂商未启用 MGLRU，匿名页回收偏弱、文件页回收过猛；页表扫描的精度与开销互相制约。"),
        ("⑤ 预加载与回收互相抵消", "AppFlow 消融：只做预加载，冷启动时延 -26.1% 但冷启动次数 !!+30%!!；三项协同才达到 -40.8%、后台存活 1.85 倍。"),
    ]
    card(s, (rx, 128, rw, 438))
    text(s, (rx + 14, 138, rw - 28, 22), "五个瓶颈与量化证据", style="emphasis", color="primary_text")
    points(s, rx + 14, 170, rw - 28, 392, items, style="body", badge=False)
    titled_card(s, (rx, 578, rw, 110), "根因归纳",
                "冷热证据只有软件扫描；锁与 I/O 落在冷启动关键路径上；预加载、回收、杀进程各管一段、没有共享的预算账本。"
                "这三点分别由 KT1-b / c、KT1-a 和共享底座解决。", style="body")


# ------------------------------------------------------------------ Q-3 模型内存瓶颈
@page
def bottleneck_model(prs):
    s = new_slide(prs, "当代系统瓶颈（二）", "模型内存：看不见、收不走、拷多份、读不满",
                  "模型内存分散在框架、dma-buf 与 NPU 驱动里，回收看不见；权重多份拷贝并钉住，加载打不满 UFS")
    x0, w = 32, 560
    card(s, (x0, 128, w, 560))
    text(s, (x0 + 14, 138, w - 28, 20), "@@一份权重今天在内存里的去向@@（示意）", style="body")
    col = [("UFS 权重文件", "几 GB 到几十 GB", "surface"),
           ("页缓存", "mmap 读入，4KB 级缺页", "surface"),
           ("框架私有缓冲", "反量化、重排，第二份", "highlight"),
           ("NPU 缓冲（dma-buf）", "注册到 IOMMU 并钉住，第三份", "highlight")]
    y = 172
    for i, (t, d, f) in enumerate(col):
        box(s, (x0 + 24, y, 250, 60), f"**{t}**\n{d}", fill=f, line="accent" if f == "highlight" else None,
            style="detail")
        if i < len(col) - 1:
            arrow(s, (x0 + 149, y + 60), (x0 + 149, y + 76), color="accent", width=1.5)
        y += 76
    box(s, (x0 + 300, 172, 236, 136), "**KV Cache**\n随上下文线性增长、每个会话私有；放在 dma-buf / NPU 可见缓冲里，不在 LRU 上",
        fill="highlight", line="accent", style="detail", align="left", inset=10)
    box(s, (x0 + 300, 324, 236, 152), "**MoE 专家**\n35B 级 Q4 权重约 14–21GB，16GB 机型放不下，只能按需从 UFS 换入；命中率决定能不能用",
        fill="highlight", line="accent", style="detail", align="left", inset=10)
    box(s, (x0 + 24, 488, w - 48, 92), "**系统看到的是什么**：lmkd / Jetsam 只看到进程 RSS 和部分页缓存；钉住的 dma-buf、NPU scratch、KV "
        "既不计入统一账，也收不走——压力来时只能杀应用。", fill="highlight_blue", style="detail", align="left", inset=10)
    text(s, (x0 + 24, 590, w - 48, 90), "红框为被钉住或不可回收的部分。iOS 开发者实测：模型常驻约 4.4GB 后只剩约 1.7GB 做 prefill，"
         "需把 GPU 缓冲缓存从 512MB 降到 64MB 才避免被杀（单一论坛帖）。", style="caption")

    rx, rw = 608, 640
    table(s, (rx, 128, rw, 400), ["瓶颈", "数据", "说明"],
          [["KV 可能比权重还大", "Qwen3-4B：每 token 144KiB，32K 上下文 !!4.5GiB!!，约为 Q4 权重的 1.9 倍；Qwen3.5-4B 降到 32KiB", "取决于架构；多会话时线性放大"],
           ["KV 被钉住", "KV、dma-buf、NPU scratch 都在 LRU 之外", "容易提前触发 lmkd；手机实测数据未公开"],
           ["专家命中率", "iPhone 上 512MiB LRU 缓存命中率 !!0%!!，576MiB 时 38.58%（预印本）", "命中率为 0 时每 token 约 1.1GB IO，解码上限约 5 tokens/s（估算）"],
           ["NPU 路径多份拷贝", "8GB CMA 分配约 6.44 秒，mmap 约 0.56 秒（摘要，待核实）；QNN 需预编译且绑定单一 SoC", "页缓存、框架缓冲、NPU 缓冲重复占用"],
           ["加载 IO 打不满", "UFS 4.1 顺序读约 4.3GB/s：2.5GB 理想 0.58 秒；4KB 级缺页式读取远低于此", "真实冷加载时间无公开数据"]],
          widths=[1.3, 3.0, 2.2], style="caption", header_style="detail")
    titled_card(s, (rx, 540, rw, 148), "根因归纳",
                "- **记账分散**：权重、专家、KV、NPU 缓冲分属不同的记账域。\n"
                "- **钉住与拷贝**：NPU 路径要求注册、连续或常驻，权重被复制成多份。\n"
                "- **小 IO**：缺页式加载与专家随机读打不满 UFS。三点分别对应共享底座、KT3 和 KT2-A。",
                style="detail")


# ------------------------------------------------------------------ Q-4 评估与效率
@page
def bottleneck_eval(prs):
    s = new_slide(prs, "当代系统瓶颈（三）", "评估与效率：值不值得下沉算不清",
                  "端云代价无法同口径比较，手机侧没有仿真器；单个 Agent 串行执行，端侧多步任务时延是各步之和")
    ks = [("$0.007", "一个 10 步任务的云成本", "Gemini 3.1 Flash-Lite，2026-11 价格（估算）"),
          ("约$12.8亿/年", "规模化后的云账单", "1 亿日活 × 每人每天 5 次（估算，仅说明量级）"),
          ("约3倍", "端侧每 token 能效劣势", "相对批处理服务器（2026 预印本）"),
          ("0", "面向手机 SoC 的公开 LLM 仿真器", "Vidur、LLMServingSim 等均面向 GPU / TPU")]
    kw = (1216 - 3 * 12) / 4
    for i, (v, l, n) in enumerate(ks):
        kpi(s, (32 + i * (kw + 12), 128, kw, 110), v, l, n)
    titled_card(s, (32, 252, 600, 436), "云转端：缺统一口径",
                "- **能耗无法同口径比较**：Perfetto 分轨功耗（ODPM）只在部分机型可用；Google 公布的云侧 0.24Wh / prompt 不含网络与终端能耗。\n"
                "- **体验风险难量化**：端侧推理占内存，会挤压前台应用；但「模型常驻多少 GB ↔ 前台冷启动劣化多少」没有换算方法。\n"
                "- **规模放大后成本不小**：单次任务的云成本在 1 美分以内，规模化后达到十亿美元量级；下沉的收益主要在隐私、离线、时延确定性和规模化后的云账单。\n"
                "- **指标没有标准**：time-to-first-action 等 Agent 体验指标没有公开的正式定义，评测无法对齐。",
                style="body", gap_pt=6)
    titled_card(s, (648, 252, 600, 436), "单 Agent：串行执行，云上收益不能外推",
                "- **串行链路**：「生成 → 工具 → 生成」逐步执行，端侧任务时延等于各步之和。\n"
                "- **云上证据充分**：LLMCompiler（ICML 2024）时延最高快 3.7 倍；PASTE（2026）任务完成时间 -43.5%；Speculative Actions 时延最高 -20%。\n"
                "- **端侧约束不同**：decode 受带宽限制，CPU 与 NPU 并用时带宽约 59.6GB/s，只比 NPU 单用高约 6%；手机工具大多有副作用（发短信、设闹钟、拉起应用），需权限与确认。\n"
                "- **结论**：并行化与投机能否在端侧获益，必须在带宽、权限和副作用约束下重新评估——这需要仿真平台。",
                style="body", gap_pt=6)


# ------------------------------------------------------------------ Q-5 AI + 图形场景与瓶颈
@page
def graphics_problems(prs):
    s = new_slide(prs, "AI+图形场景与瓶颈", "持续负载、帧预算与碎片化",
                  "四类体验场景都卡在「持续负载下的能效」与「推理塞进帧预算」上，硬件与协议又各自碎片化")
    table(s, (32, 128, 1216, 420), ["议题", "场景与用户需求", "当代瓶颈", "数据", "体验指标（建议，待校准）"],
          [["**G1** 3DGS", "拍一圈生成可交互 3D；单张照片生成可转头的 3D；浏览与分享 3D 内容：拍完就能看、打开快、滑动流畅、文件小",
            "原始 3DGS 在手机上慢且耗电；文件大；格式碎片化", "量化版 3DGS 稳态 3 FPS、5.89W；PLY 约 250MB；glTF 扩展只到候选版",
            "端侧重建分钟级（基线 255 秒）；稳态 ≥60 FPS；单场景 10–25MB；渲染 1W 量级"],
           ["**G2** AI 萌宠", "桌面或息屏常驻陪伴；语音互动且「记得我」；照片定制形象：看得见、不打扰、不费电",
            "常驻角色只能放在应用进程或动态壁纸里，受后台限制与回收；小组件不允许连续动画", "常驻宠物的功耗和内存没有公开数据",
            "静止态额外功耗接近零；常驻内存 100–150MB（估算）；前台冷启动无可测影响"],
           ["**G3** 神经超分与插帧", "重度手游持续高画质；120Hz 高刷；存量游戏不用适配也能变好：30 分钟不降频、不烫手",
            "插帧超出帧预算；持续负载降频；加速器碎片化", "A19 上 MetalFX 插帧约 18ms / 帧，120Hz 预算 8.3ms；持续运行后升到约 30ms",
            "同画质功耗 -20%～-40%；插帧 <4ms；UI 鬼影率下降"],
           ["**G4** 生成式 UI", "对话中直接给出可交互的图表与表单；一句话生成临时小工具；第三方服务以轻量面板嵌入",
            "界面描述动辄数千 token；iframe 路线要常驻 WebView；Apple 与鸿蒙没有公开协议", "3000 token、60 token/s 约需 50 秒（估算）",
            "首个可见元素尽早出现；流式生成不掉帧；越权用例 100% 拦截"]],
          widths=[1.0, 2.6, 2.2, 2.2, 2.2], style="detail", header_style="body_strong")
    items = [("持续负载下的能效与热稳态", "3DGS 冷启动与稳态帧率差距大；游戏几分钟后降频锁帧；常驻萌宠必须几乎不耗电。"),
             ("AI 推理要塞进帧预算", "插帧 18ms 对 8.3ms 的预算；生成式 UI 要边生成边渲染。"),
             ("碎片化", "神经加速器各家一套，Vulkan ML 仍是厂商扩展；3DGS 格式未定；生成式 UI 协议未统一。")]
    card(s, (32, 560, 1216, 128))
    text(s, (46, 570, 300, 22), "三个关键问题", style="emphasis", color="primary_text")
    cw = (1188 - 2 * 16) / 3
    for i, (t, d) in enumerate(items, 1):
        x = 46 + (i - 1) * (cw + 16)
        num_badge(s, x, 602, i)
        text(s, (x + 28, 600, cw - 28, 84), f"**{t}**：{d}", style="body")

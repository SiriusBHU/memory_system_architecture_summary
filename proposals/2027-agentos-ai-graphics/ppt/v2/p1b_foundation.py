"""第一部分（续）：基础能力洞察——端侧模型、推理引擎、内核演进、硬件与评估手段。"""

from lib import (arrow, box, card, footnote, kpi, new_slide, num_badge, points, table, text, timeline,
                 titled_card)
from registry import page


# ------------------------------------------------------------------ F-1 端侧模型的内存需求曲线
@page
def model_curve(prs):
    s = new_slide(prs, "基础能力洞察（一）", "端侧模型的内存需求曲线",
                  "常驻权重年增约 40%–60%，平均内存年增约 13%；两条曲线已在 12GB 机型上交叉")
    # 左：原生柱状图
    cx, cy, cw, ch = 32, 128, 540, 560
    card(s, (cx, cy, cw, ch))
    text(s, (cx + 14, cy + 10, cw - 28, 20), "@@需求与供给@@（GB；Gemini 路线常驻权重 vs 全球手机平均 DRAM）", style="body")
    x0, x1, ytop, ybot, gmax = cx + 56, cx + cw - 20, cy + 70, cy + 400, 16
    k = (ybot - ytop) / gmax

    def Y(v):
        return ybot - v * k

    for g in (0, 4, 8, 12, 16):
        text(s, (cx + 14, Y(g) - 8, 36, 16), f"{g}", style="caption", align="right")
    arrow(s, (x0, ybot), (x1, ybot), color="muted", head=False)
    # 12GB 旗舰线
    arrow(s, (x0, Y(12)), (x1, Y(12)), color="accent", head=False, dash=True, width=1.25)
    text(s, (x0 + 6, Y(12) - 36, 320, 32), "旗舰内存约 12GB（2023–2026 基本不变），\n也是 Apple、Google 最强端侧能力的门槛", style="caption")
    years = ["2023", "2024", "2025", "2026", "2027E"]
    slot = (x1 - x0) / len(years)
    dram = {"2024": 7.4, "2025": 8.4, "2026": 8.5}
    model = {"2023": (1.6, None), "2026": (4.2, 5.9), "2027E": (5.9, 9.4)}
    for i, yv in enumerate(years):
        sx = x0 + i * slot
        text(s, (sx, ybot + 6, slot, 18), yv, style="detail", align="center")
        if yv in dram:
            v = dram[yv]
            box(s, (sx + slot / 2 - 34, Y(v), 30, v * k), "", fill="primary", check=False)
            text(s, (sx + slot / 2 - 50, Y(v) - 18, 62, 16), f"{v}", style="caption", align="center")
        if yv in model:
            lo, hi = model[yv]
            mx = sx + slot / 2 + 4
            dashed = yv == "2027E"
            box(s, (mx, Y(lo), 30, lo * k), "", fill="highlight" if dashed else "accent",
                line="accent" if dashed else None, dash=dashed, check=False)
            if hi:
                box(s, (mx, Y(hi), 30, (hi - lo) * k), "", fill="highlight", line="accent", dash=True, check=False)
            label = f"{lo}–{hi}" if hi else f"{lo}"
            text(s, (mx - 16, Y(hi or lo) - 18, 62, 16), label, style="caption", align="center")
    lg = cy + 440
    box(s, (cx + 20, lg + 2, 14, 12), "", fill="primary", check=False)
    text(s, (cx + 40, lg, 220, 16), "全球手机平均 DRAM", style="caption")
    box(s, (cx + 200, lg + 2, 14, 12), "", fill="accent", check=False)
    text(s, (cx + 220, lg, 300, 16), "常驻权重（实心为下限，虚框为区间）", style="caption")
    text(s, (cx + 14, lg + 26, cw - 28, 90),
         "- 2023：Gemini Nano-2 约 3.25B × 4bit ≈ !!1.6GB!!（估算）。\n"
         "- 2026：Nano 4 Fast / Full 据报 !!4.2 / 5.9GB!!，至少需要 12GB 内存（二手），Full 版约占 12GB 机型的 49%。\n"
         "- 2027E：沿 +40%–60%/年外推为 5.9–9.4GB，物理上不可持续（估算）。", style="caption", gap_pt=2)

    # 右上：模型形态演进表
    rx, rw = 588, 660
    table(s, (rx, 128, rw, 338), ["模型（时间）", "参数 / 量化", "端侧内存", "形态变化"],
          [["Apple 端侧模型（2024）", "约 3B，平均 3.7bit", "约 1.4GB（估算）", "稠密 + 低位宽"],
           ["Apple 端侧模型（2025）", "约 3B，权重 2bit QAT", "权重 <0.75GB（估算）", "层间共享 KV，KV -37.5%"],
           ["Gemma 3n E2B（2025）", "原始 >5B，有效 1.91B", "约 2GB", "PLE 逐层嵌入放快速存储"],
           ["Gemma 4 E2B / E4B（2026-04）", "有效 2B / 4B", "1.1 / 2.5GB（官方）", "滑窗 + 层间共享 KV"],
           ["Gemini Nano 4（2026-08）", "基于 Gemma 4 E2B / E4B", "4.2 / 5.9GB（二手）", "系统托管，≥12GB 机型"],
           ["Apple AFM 3（2026-06）", "20B 总参，激活 1–4B（二手）", "未公开", "稀疏 MoE，闪存驻留"],
           ["Qwen3-4B → Qwen3.5-4B", "4B", "Q4 约 2.4GB（估算）", "KV 每 token !!144→32 KiB!!"]],
          widths=[2.1, 1.9, 1.6, 2.0], style="caption", header_style="detail")

    card(s, (rx, 478, rw, 210))
    text(s, (rx + 14, 488, rw - 28, 22), "分析：这说明什么", style="emphasis", color="primary_text")
    text(s, (rx + 14, 514, rw - 28, 170),
         "- **剪刀差已经出现**：常驻权重增速约为 DRAM 的 3–4 倍，且 DRAM 在 2026–2027 受价格压制更难增长。\n"
         "- **模型侧三个方向一致**：稠密走向稀疏（PLE、MoE、激活稀疏）；全量 KV 走向滑窗与层间共享；位宽降到 2–4bit。这些由模型决定，"
         "OS 能做的是为 @@稀疏权重分层@@ 和 @@多会话 KV@@ 提供系统支持。\n"
         "- **KV 的主矛盾在转移**：单 token KV 两年降了约一个数量级，2027 年的压力来自「多会话 × 长 Agent 上下文」，KT2-B 要与此对齐。",
         style="detail", gap_pt=3)


# ------------------------------------------------------------------ F-2 推理引擎
@page
def engines(prs):
    s = new_slide(prs, "基础能力洞察（二）", "推理引擎：模型内存游离在OS之外",
                  "主流引擎里只有系统托管路线能共享权重；一旦走 NPU，缓冲脱离页缓存，OS 既回收不了也共享不了")
    table(s, (32, 128, 1216, 392), ["引擎", "权重加载", "KV 管理", "多应用 / 多会话共享权重", "OS 能否看到并回收"],
          [["llama.cpp", "默认 mmap，权重是文件页", "按上下文预分配；支持 q8_0 / q4_0 量化", "多进程映射同一文件时共享页缓存（推断）",
            "权重可回收；KV 是匿名页，计入进程 RSS"],
           ["ExecuTorch", "mmap / mlock 多种模式；.pte 数据段页对齐", "编译期写入最大上下文", "两个 .pte 不共享权重，RFC 推进中",
            "选 mlock 则被钉住、不可回收"],
           ["LiteRT-LM（应用内）", "首次加载优化并缓存；Gemma 4 E2B 峰值内存 1733MB（CPU）", "未公开 KV 上限", "每个应用各一份",
            "按进程由 lmkd / Jetsam 治理"],
           ["Android AICore", "系统服务托管 Gemini Nano，应用不带权重", "请求级隔离，多轮历史由应用管理", "**是**：所有调用方共享一份模型与 LoRA",
            "AICore 进程如何被 lmkd 评分：未公开"],
           ["MNN-LLM", "低利用率参数（如 Embedding，约 15%）放闪存", "KV 超阈值后溢出到闪存并预取", "未公开", "未公开"],
           ["高通 QNN / Genie", "context binary 预编译、绑定单一 SoC", "KV 在 NPU 可见缓冲", "同一 binary 内共享；跨应用未公开",
            "缓冲注册到 NPU 地址空间、通常钉住，不在 LRU"],
           ["Apple Foundation Models / MLX", "系统共享端侧模型；MLX 由应用自带", "上下文 8192（二手）", "Foundation Models 共享；MLX 应用私有",
            "受 Jetsam 约束：单应用上限约 6144MB，8GB 与 12GB 机型相同（论坛实测）"],
           ["华为 MindSpore Lite", "2.7.0 支持进程间共享模型权重", "大模型 KV 管理未公开", "框架级支持", "HiAI Foundation 加载机制未公开"]],
          widths=[1.4, 2.4, 2.0, 2.2, 2.4], style="caption", header_style="detail")
    titled_card(s, (32, 532, 600, 156), "关键事实",
                "- 共识是「权重文件化 + 页对齐 + mmap」，但这只在 CPU 路径成立；NPU 路径要拷贝或注册到厂商私有缓冲。\n"
                "- iOS：开发者实测模型常驻约 4.4GB 后只剩约 1.7GB 做 prefill，需把 GPU 缓冲缓存从 512MB 降到 64MB 才避免被 Jetsam 杀掉（单一论坛帖）。",
                style="body")
    titled_card(s, (648, 532, 600, 156), "分析：这说明什么",
                "- 每多一个自带模型的应用，就多一份权重和一份 KV；系统托管路线解决了共享，但没有解决「被谁回收、何时回收」。\n"
                "- 模型内存缺少统一记账、共享与回收，是 @@总体构想「一等公民」@@ 和 KT3「文件页直接映射给 NPU」的直接依据。",
                style="body")


# ------------------------------------------------------------------ F-3 内核演进
@page
def kernel(prs):
    s = new_slide(prs, "基础能力洞察（三）", "内核内存管理的上游演进",
                  "上游主线是降锁、大页、可编程回收；硬件证据驱动的冷热识别仍是 RFC，模型内存无对应项")
    card(s, (32, 128, 1216, 150))
    text(s, (44, 136, 600, 20), "@@Linux 主线关键节点@@（kernelnewbies；括号内为对应 GKI 分支）", style="body")
    timeline(s, 60, 192, 1160, [
        ("6.1", "MGLRU 多代 LRU"),
        ("6.4", "per-VMA lock（仅匿名页）"),
        ("6.6", "文件缺页、swap 缺页走 VMA 锁（android15-6.6，版本待核实）"),
        ("6.8", "匿名 mTHP；DAMOS 自动调参"),
        ("6.9", "arm64 连续 PTE（contpte）"),
        ("6.12", "mTHP 换出；zram 压缩后端 API（android16-6.12）"),
        ("6.18", "swap table 第一阶段（android17-6.18）"),
        ("RFC", "DAMON 硬件采样（2026-09 v2）；IBS pghot v8"),
    ], text_h=70)

    table(s, (32, 290, 800, 398), ["机制", "解决了什么", "对 Agent + 应用叠加没解决什么"],
          [["per-VMA lock", "多线程缺页不再抢 mmap_lock，缓解启动锁竞争", "回收侧 rmap 锁（i_mmap_rwsem）争用仍在：Android 重负载下 kswapd 等锁 ≥300ms"],
           ["mTHP / contpte", "一次缺页分配大页，减少缺页与 TLB 缺失", "手机碎片严重，大页分配失败率高；可执行段大 folio 合入版本待核实"],
           ["mTHP 换出 / swap table", "大 folio 整块换入换出，降低 swap 元数据与锁开销", "不提供冷热证据，也不做预取"],
           ["MGLRU", "更细的页龄；Pixel 6 Pro 启动 -6.60%（LPC 2022）", "多家 Android 厂商未启用；与前后台应用语义脱节，匿名页回收偏弱"],
           ["DAMON / DAMOS", "区域级访问监控，开销与内存大小无关；可作回收执行入口", "区域粒度；硬件采样未合入；冷证据仍依赖页表 Accessed 位"],
           ["Arm SPE", "arm_spe_pmu 驱动已在主线与 Android 通用内核", "主线没有基于 SPE 的冷热识别；手机 SoC 是否开放 SPE 未公开"],
           ["Android 16KB 页", "内存压力下应用启动 -3.16%，整机启动 -8%", "内存占用上升；2027-02 起 Play 强制，.so 优化须按 16KB 粒度设计"]],
          widths=[1.3, 2.6, 3.4], style="caption", header_style="detail")

    rx, rw = 848, 400
    card(s, (rx, 290, rw, 398))
    text(s, (rx + 14, 300, rw - 28, 22), "其他平台与分析", style="emphasis", color="primary_text")
    text(s, (rx + 14, 328, rw - 28, 356),
         "- **iOS**：Jetsam 杀进程 + 内存压缩器，无磁盘交换；单应用上限与 12GB 机型不匹配。\n"
         "- **HarmonyOS**：OpenHarmony 有 ESwap（zram 压缩页加密换出到专用分区）；HyperSpace Memory 宣称 12GB 达到 16GB 的保活效果（厂商口径，无技术细节）。\n"
         "- **判断一**：上游没有「按应用语义 + 硬件证据」的冷热识别，KT1-b / KT1-c 有空间；实现应对接 DAMON 的采样通道，不另起框架。\n"
         "- **判断二**：所有机制都以 LRU 和进程为治理单位，KV 与 NPU 缓冲都不在其中——「模型内存一等公民」在上游路线图里没有对应项。",
         style="body", gap_pt=4)


# ------------------------------------------------------------------ F-4 硬件与评估手段
@page
def hw_eval(prs):
    s = new_slide(prs, "基础能力洞察（四）", "硬件窗口与评估手段",
                  "UFS 5.0 让闪存顺序读接近 11GB/s，稀疏权重分层首次接近可用；但三项关键前提都缺少公开证据")
    table(s, (32, 128, 700, 300), ["硬件", "参数", "时间", "对立项的含义"],
          [["LPDDR5X", "10.7Gbps，64bit 约 85.6GB/s（估算）", "已量产", "骁龙 8 Gen 3 单处理器实测约 45GB/s：decode 受带宽限制"],
           ["LPDDR6", "10.7–14.4Gbps，每引脚 +11%～+50%", "2026H2 量产，手机 2027", "带宽增速仍追不上常驻权重的 40%–60%/年"],
           ["UFS 4.1", "顺序读约 4.3GB/s", "已量产", "5.9GB 模型理想加载约 1.4 秒"],
           ["UFS 5.0", "顺序读 !!10.8GB/s!!，约为 4.1 的 2.5 倍", "2026Q4 量产", "约为 DRAM 带宽的 1/8，专家与权重流式换入接近可用"],
           ["Arm SPE", "A720 / A725 / X925 已实现；C1-Ultra 有 SPE TLB", "—", "手机 SoC 是否向 Linux 开放：!!未找到公开资料!!"],
           ["NPU SMMU / SVA", "NPU 流量经应用侧 SMMU", "—", "能否映射文件页、是否支持 SVA：!!未找到公开资料!!"]],
          widths=[1.1, 2.3, 1.3, 2.6], style="caption", header_style="detail")

    table(s, (748, 128, 500, 300), ["评估手段", "现状"],
          [["LLM 仿真器", "Vidur（误差 <9%）、LLMServingSim 2.0（0.95%）、GenZ、LLMCompass 全部面向数据中心 GPU / TPU；!!没有手机 SoC 仿真器!!"],
           ["手机特有因素", "DVFS、热降频、CPU / GPU / NPU 共享带宽、UFS 抖动均无公开模型"],
           ["能耗测量", "Perfetto 分轨功耗（ODPM）只在部分机型可用；云侧 0.24Wh / prompt 不含网络与终端"],
           ["端云路由研究", "Hybrid LLM、RouteLLM、HybridFlow 只看质量与成本，不计端侧能耗与内存"],
           ["Agent 体验指标", "time-to-first-action 等没有公开的正式定义"]],
          widths=[1.1, 3.4], style="caption", header_style="detail")

    card(s, (32, 440, 1216, 248))
    text(s, (46, 450, 600, 22), "分析：这说明什么", style="emphasis", color="primary_text")
    pts = [("带宽追不上模型", "LPDDR6 每引脚提升 11%–50%，常驻权重年增 40%–60%；端侧 decode 将长期受带宽限制，省内存就是省带宽。"),
           ("闪存第一次成为可用的一层", "UFS 5.0 约 10.8GB/s，使「热权重常驻 + 冷权重闪存流式」成立，前提是把 4KB 缺页聚合成大块 IO（KT3 难点）。"),
           ("三项前提必须先摸底", "手机 SoC 是否开放 SPE（KT1-b/c）、NPU 能否映射文件页（KT3）、手机侧仿真器（S1）都没有公开证据，列为立项第 0 阶段的决策点。"),
           ("评估平台本身是立项理由", "没有手机侧仿真器与统一能耗口径，云转端与并行化的收益无法在立项前量化；S1 / S2 是所有目标从「建议区间」变为承诺值的前提。")]
    points(s, 46, 482, 1188, 200, pts, style="body")

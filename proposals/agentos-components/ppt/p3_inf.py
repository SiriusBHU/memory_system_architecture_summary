"""第三部分 · 推理服务：目标架构与关键技术（报告 3-推理，2026-11-09 改版）。
页面顺序：目标架构 → 关键技术一（Agent 超长序列推理的优化）→ 关键技术二（LPDDR-PIM、NPU、UFS-PIM 异构融合计算）
→ 关键技术三（硬件亲和的模型架构寻优）。会话级调度由其他团队负责，只在架构中体现。
"""

from lib import arrow, badge, box, outline, poly, rect, text
from pages import arch_kt_page, kt_page, legend
from registry import page

CRUMB = "三、架构与关键技术 › 推理服务"
SRC = "报告 3-推理"


NEW = dict(fill="peach_l", line="red", line_width=1.25, color="accent")
OLD = dict(fill="bg", line="grey_d")
PLAN = dict(fill="peach_l", line="red", line_width=1.25, dash=True, color="accent")


KEY = dict(fill="peach_l", line="red", line_width=1.5)          # 本次要做的部分：只有三处
NEU = dict(fill="bg", line="grey_d")                              # 已有或其他团队的部分
CTX = dict(fill="grey_l", line="grey_line")                       # 上下文与协同的系统服务


def _key_box(s, b, n, title, sub):
    """本次要做的模块：浅橙底深红框，红色编号，标题深红加粗、说明黑字。"""
    box(s, b, f"!!{title}!!\n{sub}", style="detail", inset=4, **KEY)
    badge(s, b[0] + b[2] - 2, b[1] + 2, n, d=20)


def _draw_inference(s, b):
    """推理服务专属架构图（2026-11-11 第二版）：画全局关系，只突出本次要做的三处。
    顶部为场景；中部为请求方 → Agent OS（推理服务居中，执行与沙箱、内存与资源两项系统服务协同）；底部为计算与存储硬件；
    右侧为离线的模型结构寻优：候选底座与端侧约束输入，导出的可入端底座部署回推理服务。"""
    x0, y0, w, h = b
    lw = 468
    rx, rw = x0 + lw + 14, w - lw - 14
    e = max(0.0, (h - 372) / 4)

    # 场景
    box(s, (x0, y0, w, 26), "**场景**：贴身秘书类长程任务，32K–128K 上下文，工具返回反复追加，MoE 底座逐 token 路由",
        fill="blue_l", line=None, style="detail", align="left", inset=8)

    # 请求方
    ry = y0 + 36 + e
    names = ["System Agent", "应用 Agent", "应用的 AI 功能"]
    nw = (lw - 20) / 3
    for i, nm in enumerate(names):
        bx = x0 + i * (nw + 10)
        box(s, (bx, ry, nw, 24), nm, style="detail", **NEU)
        arrow(s, (bx + nw / 2, ry + 25), (bx + nw / 2, ry + 37 + e), color="grey_d")

    # Agent OS：推理服务居中，两项系统服务协同
    fy = ry + 38 + e
    fh = 212
    outline(s, (x0, fy, lw, fh), line="grey_d", width=1.0)
    text(s, (x0 + 8, fy + 3, 200, 16), "**Agent OS 系统服务**", style="caption", color="grey_d", check=False)
    iw = 330
    box(s, (x0 + 8, fy + 22, iw, 22), "推理服务接口 · 会话级调度（其他团队负责）", style="caption", **CTX)
    outline(s, (x0 + 8, fy + 50, iw, fh - 58), line="dark", width=1.25)
    text(s, (x0 + 16, fy + 53, 200, 18), "**推理服务**", style="detail", check=False)
    _key_box(s, (x0 + 18, fy + 74, iw - 20, 56), 1, "超长序列推理引擎",
             "草稿模型筛选 KV · 专家路由多级复用")
    _key_box(s, (x0 + 18, fy + 138, iw - 20, 56), 2, "异构融合调度",
             "算子按强度分派 · 权重 / KV 亲和排布")
    sx, sw = x0 + iw + 18, lw - iw - 26
    box(s, (sx, fy + 70, sw, 62), "**执行与沙箱**\n隔离与权限判定", style="caption", **CTX)
    box(s, (sx, fy + 140, sw, 64), "**内存与资源**\n按会话记账与回收", style="caption", **CTX)
    arrow(s, (x0 + 8 + iw + 1, fy + 101), (sx - 1, fy + 101), color="grey_d", dash=True, both=True)
    arrow(s, (x0 + 8 + iw + 1, fy + 172), (sx - 1, fy + 172), color="grey_d", dash=True, both=True)

    # 硬件：计算与存储（PIM 在存储侧）
    hy = fy + fh + 12 + e
    hw_ = [("**NPU**\nPrefill 计算", False), ("**CPU / GPU**\n其余算子", False),
           ("**LPDDR + 2D-PIM**\n热专家与 KV", True), ("**UFS + UFS-PIM**\n多 Channel 冷专家", True)]
    uw = (lw - 18) / 4
    for i, (md, pim) in enumerate(hw_):
        ux = x0 + i * (uw + 6)
        box(s, (ux, hy, uw, 46), md, style="caption", inset=1, fill="bg", line="grey_d", dash=pim)
    arrow(s, (x0 + 8 + iw / 2, fy + fh + 1), (x0 + 8 + iw / 2, hy - 1), color="grey_d", width=1.25)
    text(s, (x0 + 8 + iw / 2 + 4, fy + fh + 1, 160, 12), "算子与数据下发到各 IP", style="footnote", color="grey_d",
         check=False)

    # 右侧：离线的模型结构寻优
    cy = ry
    box(s, (rx, cy, rw, 36), "**模型团队**\n候选底座", style="caption", **NEU)
    arrow(s, (rx + rw / 2, cy + 37), (rx + rw / 2, cy + 47 + e), color="grey_d")
    ky = cy + 48 + e
    kh = 100
    _key_box(s, (rx, ky, rw, kh), 3, "模型结构寻优", "Attn 结构选型\n专家架构寻优\n离线，与模型团队联合")
    oy = ky + kh + 12 + e
    box(s, (rx, oy, rw - 22, 40), "**可入端底座**\n结构组合导出", style="caption", **NEU)
    arrow(s, (rx + (rw - 22) / 2, ky + kh + 1), (rx + (rw - 22) / 2, oy - 1), color="grey_d")
    # 部署回推理服务
    poly(s, [(rx, oy + 20), (x0 + lw + 6, oy + 20), (x0 + lw + 6, fy + 58), (x0 + 8 + iw + 1, fy + 58)], head=True,
         color="grey_d", width=1.25)
    text(s, (x0 + lw - 34, fy + 45, 40, 12), "部署", style="footnote", color="grey_d", check=False)
    # 端侧约束：来自硬件
    box(s, (rx, hy, rw, 46), "**端侧约束**\n算力 · 带宽 · 存储", style="caption", **CTX)
    arrow(s, (x0 + lw + 1, hy + 23), (rx - 1, hy + 23), color="grey_d", dash=True)
    arrow(s, (rx + rw - 10, hy - 1), (rx + rw - 10, ky + kh + 1), color="grey_d", dash=True)


# ---------------------------------------------------------------- 关键技术卡右侧的示意图（形状绘制，可在 PowerPoint 中修改）

def _fig_reuse(s, b):
    """关键技术一示意：上为逐 Head 按 Attn Score 选 KV 块，下为专家在相邻 Step 间复用。"""
    x, y, w, h = b
    rect(s, b, "bg", line="grey_line", kind="rounded", radius=6)
    text(s, (x, y + 2, w, 13), "逐 Head 选 KV", style="footnote", align="center", check=False)
    pick = [{1, 4}, {0, 3, 5}, {2, 4}, {1, 5}]
    cols, cs = 6, (w - 20) / 6
    for r in range(4):
        for c in range(cols):
            sel = c in pick[r]
            rect(s, (x + 10 + c * cs, y + 17 + r * 10, cs - 3, 7), "peach_m" if sel else "grey_m",
                 line="red" if sel else None, line_width=0.75)
    my = y + 17 + 4 * 10 + 6
    text(s, (x, my, w, 13), "专家跨 Step 复用", style="footnote", align="center", check=False)
    hot = {1, 3}
    colw = (w - 20) / 3
    for t in range(3):
        cxx = x + 10 + t * colw + colw / 2 - 7
        for e in range(4):
            rect(s, (cxx, my + 15 + e * 10, 14, 7), "blue_m" if e in hot else "grey_m", line="grey_d", line_width=0.5)
        text(s, (cxx - 6, my + 56, 26, 11), f"t{t}" if t else "t", style="footnote", color="grey_d", align="center",
             check=False)
    for e in hot:
        arrow(s, (x + 10 + colw / 2 + 7, my + 18 + e * 10), (x + 10 + 2.5 * colw - 7, my + 18 + e * 10), color="blue",
              width=0.75, head=False, dash=True)


def _fig_dispatch(s, b):
    """关键技术二示意：上为按算术强度分派算子，下为权重按 PIM Bank 亲和排布。"""
    x, y, w, h = b
    rect(s, b, "bg", line="grey_line", kind="rounded", radius=6)
    rows = [("GEMM", "NPU", "blue_m"), ("GEMV", "PIM", "peach_m")]
    for i, (op, ip, fill) in enumerate(rows):
        yy = y + 8 + i * 24
        box(s, (x + 6, yy, 40, 18), op, fill="grey_l", line="grey_d", style="footnote", inset=1)
        arrow(s, (x + 47, yy + 9), (x + w - 47, yy + 9), color="dark", width=0.75)
        box(s, (x + w - 46, yy, 40, 18), ip, fill=fill, line="grey_d", style="footnote", inset=1)
    text(s, (x, y + 58, w, 13), "按 Bank 排布", style="footnote", align="center", check=False)
    bw = (w - 20) / 4
    for k in range(4):
        bx = x + 10 + k * bw
        rect(s, (bx, y + 73, bw - 4, h - 86), "bg", line="grey_d", line_width=0.5)
        for t in range(4):
            fill = "peach_m" if (t == k) else "blue_l"
            rect(s, (bx + 3, y + 77 + t * ((h - 94) / 4), bw - 10, (h - 94) / 4 - 3), fill, line=None)
        text(s, (bx - 2, y + h - 13, bw, 11), f"B{k}", style="footnote", color="grey_d", align="center", check=False)


def _fig_pareto(s, b):
    """关键技术三示意：候选结构的资源—性能散点与前沿，红点为选出的结构组合。"""
    x, y, w, h = b
    rect(s, b, "bg", line="grey_line", kind="rounded", radius=6)
    ox, oy = x + 16, y + h - 20
    arrow(s, (ox, oy), (x + w - 8, oy), color="grey_d", width=0.75)
    arrow(s, (ox, oy), (ox, y + 10), color="grey_d", width=0.75)
    text(s, (x + w - 50, oy + 3, 44, 12), "资源", style="footnote", color="grey_d", align="right", check=False)
    text(s, (x + 2, y + 2, 40, 12), "性能", style="footnote", color="grey_d", check=False)
    pw, ph = x + w - 8 - ox, oy - y - 10
    pts = [(0.15, 0.25), (0.3, 0.3), (0.4, 0.55), (0.55, 0.4), (0.7, 0.62), (0.8, 0.5), (0.25, 0.45), (0.6, 0.72)]
    for px_, py_ in pts:
        rect(s, (ox + px_ * pw - 3, oy - py_ * ph - 3, 6, 6), "grey_m", kind="oval")
    front = [(0.1, 0.3), (0.25, 0.48), (0.42, 0.62), (0.62, 0.76), (0.88, 0.84)]
    poly(s, [(ox + a * pw, oy - c * ph) for a, c in front], color="red", width=1.25)
    rect(s, (ox + 0.42 * pw - 5, oy - 0.62 * ph - 5, 10, 10), "red", kind="oval")
    text(s, (ox + 0.42 * pw - 40, oy - 0.62 * ph - 22, 60, 12), "最优组合", style="footnote", color="accent",
         align="center", check=False)


@page
def arch_inference(prs):
    arch_kt_page(prs, dict(
        crumb=CRUMB + " › 目标架构",
        title="Agent OS 推理服务能力提升",
        suffix="：模型结构亲和设计/异构融合推理加速，支撑超长序列 30+TPS 推理",
        challenge_goal="!!挑战与目标：!!① 针对端侧 Agent 对 !!32k~128k 超长上下文!!推理需求激增，Prefill 时延与 Decode KV 大小对端侧 NPU 算力 / 内存容量提出挑战，通过 KV 稀疏与缓存复用，"
                       "构建超长序列推理引擎，实现@@长程任务端侧流畅完成@@；② 针对端侧异构计算 IP（UFS-PIM / 2D-PIM / NPU）缺乏统一调度、利用率低，通过算子亲和分派，构建异构融合调度，实现@@推理更快、"
                       "续航更长@@；③ 针对模型需要针对性亲和设计，通过结构与专家寻优，构建硬件亲和底座，实现@@更强模型低成本入端@@",
        draw=_draw_inference,
        tech_line=1.5,
        milestone_h=44,
        techs=[
            ("Agent 超长序列推理的优化",
             "- **多级缓存复用架构**：专家路由按多层级、多 Token 跨 Step 共享，提升专家命中率，降低 IO 功耗，@@Decode ≥ 30 TPS@@\n"
             "- **KV 稀疏与上下文压缩**：草稿模型 look ahead 推理，按 Attn Score 逐 Head 筛选 KV，@@MoE Chunk Prefill ≥ 1500 TPS@@"),
            ("NPU/PIM 异构计算融合",
             "- **算子路由与带宽仲裁**：按算术强度分派算子，算子输入与计算特征在多 IP 间亲和分配、带宽统一仲裁，@@推理性能提升 15%@@\n"
             "- **权重 / KV 亲和排布**：按 PIM 计算形态与局部性要求排布权重 layout，减少数据搬运、提升带宽利用率，@@功耗优化 20%@@"),
            ("硬件亲和的模型架构寻优",
             "- **Attn 结构选型**：建模线性/稀疏注意力、层数与隐藏维度配比的资源-性能权衡，导出最优结构组合，@@32K 上下文 KV ≤ 1.1GiB@@\n"
             "- **专家架构寻优**：依据端侧算力/带宽/存储，后训练寻优权重复用与专家路由策略，@@UFS 多 Channel 带宽利用率 > 80%@@"),
        ],
        milestones=[("**超长序列推理原型验证**", "2027.03"), ("**NPU / PIM 异构融合计算仿真验证**", "2027.06"),
                    ("**亲和架构仿真验证**", "2027.09")],
    ))


@page
def kt_long_sequence(prs):
    kt_page(prs, dict(
        crumb=CRUMB + " › 关键技术一",
        title="Agent 超长序列推理的优化：", suffix="增量 prefill 与上下文裁剪，24K decode ≥35 token/秒",
        challenge="!!挑战：长上下文推不动!!。长程任务上下文 23–32K，端侧接口窗口只有 4–8K，公开的手机 NPU 实测最长只到 "
                  "1024 token；24K 时每 token 要读约 1GB 权重加 0.82GiB KV，decode 被带宽卡在约 30–42 token/秒；"
                  "工具返回追加后整段重算。",
        goal="!!目标：!!只算新增、少读 KV。@@工具返回追加后首 token ≤1.5 秒；24K decode ≥35 token/秒；每 token KV "
             "读取 ≤0.4GiB；裁剪后成功率下降 ≤1 个百分点@@",
        panels=[
            ("感知与建模", [
                ("box", "**在线输入**：会话上下文与本轮追加的工具返回", "in"),
                ("box", "**上下文构成分析**：稳定前缀、历史、工具返回、精确引用 token", "plain"),
                ("table", "上下文的处理方式", ["部分", "处理"], [["稳定前缀", "复用，不重算"], ["新增部分", "增量 prefill"],
                                                        ["旧工具返回", "遮蔽，保留结论"]], [1, 1.4]),
                ("box", "**输出**：本轮需计算的块与可读取的 KV", "plain"),
            ]),
            ("决策", [
                ("box", "**长序列调度**\n按块决定计算位置与 KV 读取范围", "core"),
                ("box", "**判定**：前缀是否命中且版本一致", "judge"),
                ("pair", [("只算新增块", "plain"), ("整段重算并重建前缀", "plain")], ("是", "否")),
                ("box", "**约束**：精确引用 token 不可淘汰", "plain"),
                ("box", "**下发**：NPU 分块与 GPU 协同", "core"),
            ]),
            ("执行与作用", [
                ("acts", [("分块 prefill", "NPU 预编译图"), ("选择读取", "KV 块"), ("降精度", "KV 8-bit")]),
                ("box", "**直接作用**：追加后首 token ≤1.5 秒", "effect"),
                ("box", "**间接作用**：24K decode ≥35 token/秒，长任务不必回云", "effect"),
                ("box", "**评估**：首 token、decode 速度、任务成功率", "plain"),
            ]),
        ],
        loop="评估结果回流，校准裁剪策略与 KV 选择预算",
        difficulties=[
            ("NPU 的静态形状与长序列分块",
             "- **难点**：NPU 图是静态形状，长度刚超出标准尺寸时 padding 平均多 1.91 倍，在线建图 1000 token 要约 2 秒；"
             "越靠后的分块要读的历史 KV 越多\n"
             "- **固定分块与图预编译**：按 256 token 固定分块并预编译常用尺寸；@@KV 块与 NPU 分块成整数倍@@，"
             "GPU 与 NPU 按张量切分协同"),
            ("稀疏化与精确引用的冲突",
             "- **难点**：KV 选择在问答基准上近乎无损，但 Agent 要精确引用路径、参数、ID；多种稀疏方法在 32K 精确检索上"
             "精度大幅下降\n"
             "- **引用保护**：给工具名、路径、参数、ID 打「不可淘汰」标记；@@先做上下文裁剪，再做 KV 选择@@，"
             "裁剪的收益比稀疏注意力更确定"),
            ("公开基线缺失",
             "- **难点**：没有手机 8K–32K prefill 的公开实测，3808 token/秒只是 2B 级模型、1K token 的基准\n"
             "- **基线先行**：2027 年一季度在真机测出 3B 底座 8K、16K、32K 的 prefill 与 decode；"
             "@@所有目标以真机基线校准@@"),
        ],
        milestones=[("长上下文基线；增量 prefill 与裁剪原型", "2027.06"), ("NPU 分块 prefill 与 KV 降精度", "2027.09"),
                    ("32K 长任务全天回放验收", "2027.12")],
        source="来源：报告 2.2.2、2.5.1（瓶颈一）、3-推理 3.3 关键技术一；llm.npu、HeteroInfer 见参考资料 W21、W22；"
               "上下文裁剪见 W28（编码 Agent，检索摘要）；带宽账为估算，见调研笔记 R1。",
    ))


@page
def kt_heterogeneous(prs):
    kt_page(prs, dict(
        crumb=CRUMB + " › 关键技术二",
        title="异构融合计算：", suffix="LPDDR-PIM、NPU、UFS-PIM 按强度分派算子，带宽统一仲裁",
        challenge="!!挑战：带宽墙推不开!!。单流 decode 约需 52GB/s，占 LPDDR5X 峰值约 68%，长上下文时超过峰值，后台推理"
                  "还与前台争总线；三星 LPDDR5X-PIM 实测 decode 3.01 倍，但只测了 320 token、INT4；PIM 模式要关闭缓存与"
                  "预取，主流框架都不支持，LPDDR6-PIM 标准尚未发布；UFS-PIM 需定制 NAND。",
        goal="!!目标：!!2027 年交付 SoC 内协同，PIM 与芯片团队联合预研。@@NPU 与 GPU 协同 ≥1.3 倍；前台掉帧增量"
             " ≤1 个百分点；PIM 路径 3B decode ≥100 token/秒（仿真或样片）@@",
        panels=[
            ("感知与建模", [
                ("box", "**在线输入**：算子类型、算术强度与上下文长度", "in"),
                ("box", "**带宽压力**：前台应用、图形与后台推理的占用", "warn"),
                ("table", "算子与位置", ["算子", "位置"], [["prefill、GEMM", "NPU、GPU"], ["decode GEMV", "PIM（可用时）"],
                                                      ["softmax、norm", "SoC"]], [1.2, 1.2]),
                ("box", "**输出**：算子路由候选", "plain"),
            ]),
            ("决策", [
                ("box", "**算子路由表**\n按算术强度与当前带宽分派", "core"),
                ("box", "**判定**：前台是否处于关键交互", "judge"),
                ("pair", [("后台推理让出带宽", "plain"), ("按配额回填", "plain")], ("是", "否")),
                ("box", "**约束**：投机解码按推测长度选路", "plain"),
                ("box", "**下发**：执行后端与 PIM 区", "core"),
            ]),
            ("执行与作用", [
                ("acts", [("协同计算", "NPU 与 GPU"), ("近存计算", "LPDDR-PIM"), ("闪存侧计算", "UFS-PIM 预研")]),
                ("box", "**直接作用**：decode 不再受外部总线限制", "effect"),
                ("box", "**间接作用**：后台推理不拖累前台，云转端比例上升", "effect"),
                ("box", "**评估**：吞吐、总线占用、前台掉帧", "plain"),
            ]),
        ],
        loop="评估结果回流，校准路由表与带宽配额",
        difficulties=[
            ("PIM 的模式切换与数据放置",
             "- **难点**：PIM 模式要关闭缓存与预取，与普通访存不能同时进行；prefill 要缓存友好布局，decode 要 PIM 友好布局，"
             "两份拷贝吃容量\n"
             "- **PIM 内存区**：分配器区分 PIM 区与普通区；@@权重一次布局成 PIM 友好格式，prefill 时在线重排@@；"
             "切换按前台访存最大等待 <1 毫秒设计"),
            ("带宽而非算力是协同上限",
             "- **难点**：NPU 与 GPU 共享同一份 LPDDR 带宽，协同的上限由带宽决定；后台推理会拖累前台\n"
             "- **带宽仲裁**：前台优先、后台回填；@@以带宽配额而非算力配额调度@@；HeteroInfer 与游戏并发时 prefill "
             "仅降 0.5%–2.2%"),
            ("新算力的器件与标准未定",
             "- **难点**：LPDDR6-PIM 标准未发布，三星 PIM 首个商用目标为 AI PC；UFS-PIM 需定制 NAND，UFS 5.0 无计算接口\n"
             "- **软硬一体、分阶段**：PIM 已列入自研芯片规划，@@2027 年以仿真定义系统接口@@；UFS-PIM 先做冷专家卸载的"
             "盈亏评估，专家命中率提升优先"),
        ],
        milestones=[("NPU 与 GPU 协同、带宽仲裁原型", "2027.06"), ("PIM 仿真平台与系统接口定义", "2027.09"),
                    ("PIM 样片评估；UFS-PIM 预研报告", "2027.12")],
        source="来源：报告 2.5.1（瓶颈二）、3-推理 3.3 关键技术二；三星 LPDDR5X-PIM 见参考资料 W23（厂商自报，二手）；"
               "LPDDR6-PIM 状态见 W24；HeteroInfer 见 W22；Cambricon-LLM 见 W25；调研笔记 R2、R3。",
    ))


@page
def kt_model_arch(prs):
    kt_page(prs, dict(
        crumb=CRUMB + " › 关键技术三",
        title="硬件亲和的模型架构寻优：", suffix="准入卡、代价模型与 NPU 在环评测，与模型团队联合",
        challenge="!!挑战：模型结构与手机不匹配!!。每 token 的 KV 随结构相差可达 12 倍：Qwen3-4B 为 144KiB，32K 上下文"
                  " 4.5GiB，超出 Agent 侧全部预算；MoE 照搬全注意力，24K 的 KV 达 2.25GiB；专家布局与路由方式决定闪存 IO；"
                  "公开的硬件在环搜索只做到 CPU 在环。",
        goal="!!目标：!!把内存、带宽与闪存预算变成选型约束。@@候选底座每 token KV ≤35KiB；32K 的 KV ≤1.1GiB；"
             "4K→32K decode 掉幅 ≤30%；候选 100% 提供 NPU 实测@@",
        panels=[
            ("感知与建模", [
                ("box", "**输入**：候选底座的配置文件", "in"),
                ("box", "**实测输入**：目标 SoC 的带宽、NPU 编译与时延", "in"),
                ("table", "准入卡要素", ["要素", "内容"], [["每 token KV", "fp16 / int8"], ["注意力结构", "滑窗、线性比例"],
                                                     ["专家", "大小、路由方式"]], [1, 1.4]),
                ("box", "**输出**：选型准入卡", "plain"),
            ]),
            ("决策", [
                ("box", "**带宽与闪存代价模型**\n预测首 token、decode、峰值内存、闪存 IO", "core"),
                ("box", "**判定**：是否满足内存、带宽与闪存预算", "judge"),
                ("pair", [("进入 NPU 在环评测", "plain"), ("反馈结构修改建议", "plain")], ("是", "否")),
                ("box", "**约束**：MoE 须可预取，单专家 ≥1.5MB", "plain"),
                ("box", "**下发**：模型团队的结构搜索", "core"),
            ]),
            ("执行与作用", [
                ("acts", [("准入", "选型准入卡"), ("评测", "NPU 设备农场"), ("搜索", "注意力布局")]),
                ("box", "**直接作用**：KV 与专家 IO 在预算之内", "effect"),
                ("box", "**间接作用**：长上下文与 MoE 在端侧可用", "effect"),
                ("box", "**评估**：预测误差、质量回归", "plain"),
            ]),
        ],
        loop="评估结果回流，校准代价模型与准入阈值",
        difficulties=[
            ("NPU 不在搜索环里",
             "- **难点**：公开最完整的硬件在环搜索（LFM2）只用手机 CPU 实测；线性注意力与短卷积在 NPU 上是否高效，"
             "没有公开数据\n"
             "- **NPU 在环评测**：设备农场接入编译与实测；@@冻结已训练权重、只搜注意力布局@@，降低搜索成本"),
            ("评估口径分裂",
             "- **难点**：模型团队看困惑度与基准分，系统团队看首 token、峰值内存与闪存 IO，没有统一的代价模型\n"
             "- **代价模型**：decode 时延取计算与「权重和 KV 读取字节 ÷ 带宽」的较大者，再加专家未命中的 IO；"
             "@@时延预测误差 ≤10%，作为搜索约束@@"),
            ("省下的 KV 可能以质量为代价",
             "- **难点**：线性注意力与滑窗对工具调用、长程精确引用的影响缺少独立评测\n"
             "- **Agent 任务回归**：用 Agent 任务集评测候选结构；@@结构省 KV 与推理侧选择、内存侧分页联动@@，"
             "避免重复投入"),
        ],
        milestones=[("选型准入卡与代价模型", "2027.03"), ("NPU 在环评测平台", "2027.06"),
                    ("与模型团队完成 MoE 底座选型", "2027.09")],
        source="来源：报告 2.5.1（瓶颈三）、3-推理 3.3 关键技术三；LFM2 见参考资料 W26，SmallThinker 见 W31；"
               "KV 体积按配置文件估算，见调研笔记 R4。",
    ))

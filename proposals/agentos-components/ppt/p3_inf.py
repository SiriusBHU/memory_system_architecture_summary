"""第三部分 · 推理服务：目标架构与关键技术（报告 3-推理，2026-11-09 改版）。
页面顺序：目标架构 → 关键技术一（Agent 超长序列推理的优化）→ 关键技术二（LPDDR-PIM、NPU、UFS-PIM 异构融合计算）
→ 关键技术三（硬件亲和的模型架构寻优）。会话级调度由其他团队负责，只在架构中体现。
"""

from lib import arrow, badge, box, poly, rect, text
from pages import arch_kt_page, kt_page, legend
from registry import page

CRUMB = "三、架构与关键技术 › 推理服务"
SRC = "报告 3-推理"


NEW = dict(fill="peach_l", line="red", line_width=1.25, color="accent")
OLD = dict(fill="bg", line="grey_d")


def _draw_inference(s, b):
    """推理服务专属架构图：左为在线推理通路（请求 → 长序列引擎 → 异构融合层 → 计算单元，底部为带宽墙），
    右为离线的模型准入回路（与模型团队联合），准入的底座部署回引擎。"""
    x0, y0, w, h = b
    lw = 468                      # 左侧在线通路宽度
    rx, rw = x0 + lw + 12, w - lw - 12
    # 请求方 → 接口与会话级调度（其他团队）
    names = ["System Agent", "应用 Agent", "应用的 AI 功能"]
    bw = (lw - 20) / 3
    for i, nm in enumerate(names):
        bx = x0 + i * (bw + 10)
        box(s, (bx, y0 + 4, bw, 26), nm, style="detail", **OLD)
        arrow(s, (bx + bw / 2, y0 + 31), (bx + bw / 2, y0 + 41), color="dark")
    box(s, (x0, y0 + 42, lw, 24), "推理服务接口 · 会话级调度（其他团队负责）", fill="grey_l", line="grey_d", style="detail")
    arrow(s, (x0 + lw / 2, y0 + 67), (x0 + lw / 2, y0 + 77), color="dark")

    # 长序列引擎（难题一）
    ey = y0 + 78
    rect(s, (x0, ey, lw, 104), "grey_l", kind="rounded", radius=8)
    text(s, (x0 + 10, ey + 4, 300, 20), "**长序列引擎**：只算新增、少读 KV", style="detail", color="accent", check=False)
    badge(s, x0 + lw - 14, ey + 14, 1, d=20)
    sw = (lw - 16 - 36) / 3
    stages = ["**上下文裁剪**\n精确引用 token 不可淘汰", "**增量 prefill**\nNPU 固定分块与图预编译",
              "**decode**\nKV 选择读取、8-bit 降精度"]
    for i, md in enumerate(stages):
        sx = x0 + 8 + i * (sw + 18)
        box(s, (sx, ey + 28, sw, 68), md, style="detail", **NEW)
        if i < 2:
            arrow(s, (sx + sw + 1, ey + 62), (sx + sw + 17, ey + 62), color="dark", width=1.25)
    arrow(s, (x0 + lw / 2, ey + 105), (x0 + lw / 2, ey + 115), color="dark")

    # 异构融合层（难题二）
    fy = ey + 116
    rect(s, (x0, fy, lw, 84), "grey_l", kind="rounded", radius=8)
    text(s, (x0 + 10, fy + 4, 300, 20), "**异构融合层**：按算术强度分派", style="detail", color="accent", check=False)
    badge(s, x0 + lw - 14, fy + 14, 2, d=20)
    hw = (lw - 16 - 10) / 2
    box(s, (x0 + 8, fy + 28, hw, 48), "**算子路由表**\nGEMM 走 NPU，GEMV 走 PIM", style="detail", **NEW)
    box(s, (x0 + 18 + hw, fy + 28, hw, 48), "**带宽仲裁**\n前台优先、后台按配额回填", style="detail",
        **NEW)

    # 计算单元
    hy = fy + 96
    units = [("CPU", False), ("GPU", False), ("NPU", False), ("LPDDR-PIM\n（规划）", True),
             ("UFS-PIM\n（预研）", True)]
    uw = (lw - 24) / 5
    for i, (nm, plan) in enumerate(units):
        ux = x0 + i * (uw + 6)
        arrow(s, (ux + uw / 2, fy + 85), (ux + uw / 2, hy - 1), color="dark")
        if plan:
            box(s, (ux, hy, uw, 42), nm, fill="peach_l", line="red", line_width=1.25, dash=True, color="accent",
                style="caption", inset=1)
        else:
            box(s, (ux, hy, uw, 42), nm, style="detail", **OLD)

    # 带宽墙
    by = hy + 52
    text(s, (x0, by, 70, 18), "**带宽墙**", style="detail", valign="middle", check=False)
    bx, bwid = x0 + 72, lw - 72
    rect(s, (bx, by + 2, bwid, 15), "bg", line="grey_d", line_width=0.75)
    rect(s, (bx, by + 2, bwid * 0.68, 15), "pink_m")
    text(s, (bx, by + 1, bwid * 0.68, 17), "单流 decode 约占 LPDDR5X 峰值 68%", style="caption", align="center",
         valign="middle", check=False)
    text(s, (bx + bwid * 0.68, by + 1, bwid * 0.32, 17), "24K 时超过峰值", style="caption", color="accent",
         align="center", valign="middle", check=False)

    # 模型准入（离线，难题三）
    rect(s, (rx, y0 + 4, rw, by + 18 - y0 - 4), "grey_l", kind="rounded", radius=8)
    text(s, (rx + 8, y0 + 8, rw - 30, 34), "**离线模型准入**\n与模型团队联合", style="detail", color="accent",
         check=False)
    badge(s, rx + rw - 14, y0 + 18, 3, d=20)
    cx, cw = rx + 8, rw - 16
    flow = [("候选底座（模型团队）", 26, False), ("**选型准入卡**\n每 token KV、注意力结构、专家布局", 62, True),
            ("**带宽与闪存代价模型**\n预测首 token、decode、峰值内存", 62, True), ("**NPU 在环评测**\n设备农场实测", 46, True),
            ("准入底座，部署到引擎", 26, False)]
    yy = y0 + 50
    for i, (md, hh, new) in enumerate(flow):
        box(s, (cx, yy, cw, hh), md, style="detail", **(NEW if new else OLD))
        if i < len(flow) - 1:
            arrow(s, (cx + cw / 2, yy + hh + 1), (cx + cw / 2, yy + hh + 11), color="dark")
        yy += hh + 12
    # 准入的底座部署回长序列引擎
    dy = yy - 12 - 13
    poly(s, [(cx, dy), (rx - 6, dy), (rx - 6, ey + 62), (x0 + lw + 1, ey + 62)], head=True, color="red", width=1.25)

    legend(s, x0, y0 + h - 18, [("peach_l", "red", False, "本次新增"), ("peach_l", "red", True, "规划或预研"),
                                ("bg", "grey_d", False, "已有能力或其他团队负责")])


@page
def arch_inference(prs):
    arch_kt_page(prs, dict(
        crumb=CRUMB + " › 目标架构",
        title="推理服务目标架构：", suffix="长序列引擎与异构融合层，让长上下文推得动、新算力用得上",
        challenges=[
            "长程任务上下文达 23–32K，端侧窗口只有 4–8K，追加后整段重算",
            "单流 decode 占 LPDDR5X 峰值约 68%，PIM 尚无系统支持",
            "每 token KV 随模型结构相差可达 12 倍，硬件在环搜索只做到 CPU 在环",
        ],
        goals=[
            "工具返回追加后首 token ≤1.5 秒，24K decode ≥35 token/秒",
            "NPU 与 GPU 协同 ≥1.3 倍，PIM 路径 3B decode ≥100 token/秒（仿真或样片）",
            "候选底座每 token KV ≤35KiB，100% 提供 NPU 实测",
        ],
        draw=_draw_inference,
        techs=[
            ("Agent 超长序列推理的优化",
             "- **增量 prefill 与 NPU 固定分块**：按稳定前缀、历史与工具返回拆解上下文，前缀命中时只算新增部分；按 256 token 固定分块并预编译，KV 块与 NPU 分块对齐\n- **上下文裁剪与 KV 选择**：先遮蔽过期的工具返回、再选择性读取 KV，精确引用标记为不可淘汰"),
            ("LPDDR-PIM、NPU、UFS-PIM 异构融合",
             "- **算子路由与带宽仲裁**：按算术强度分派，prefill 的 GEMM 走 NPU 与 GPU，decode 的 GEMV 走 PIM；按带宽配额调度，前台关键交互时后台让出总线\n- **PIM 内存区与联合接口**：权重一次布局成 PIM 友好格式，与芯片团队以仿真定义系统接口"),
            ("硬件亲和的模型架构寻优",
             "- **选型准入卡与代价模型**：每 token KV、注意力结构与专家布局写入准入卡；代价模型按读取字节与带宽预测 decode 时延，作为搜索约束\n- **NPU 在环评测**：设备农场实测，冻结已训练权重、只搜注意力布局，与模型团队联合选型"),
        ],
        milestones=[("**推理服务设计说明书**\n含长上下文真机基线", "2027.03"),
                    ("**长序列引擎原型**\n增量 prefill 与裁剪", "2027.06"),
                    ("**PIM 增量穿刺**\n仿真平台与系统接口", "2027.09"),
                    ("**落入版本**\n随年底版本首发", "2027.12")],
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

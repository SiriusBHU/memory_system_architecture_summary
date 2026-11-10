# -*- coding: utf-8 -*-
"""6.5–6.7、第七章、附录 A–D 与参考。依赖算力基线的数字由 calc 计算后格式化。"""
from pptx.util import Inches as I
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import pathlib
import calc as c
import pptkit as k

# 4.3 外部来源由 _ext_sources() 从 v3.4 md「4.3 节负载实例来源」表解析。

F4 = c.f_eff('W4A8')
B5 = c.B_UFS['UFS5']
TT_BIG = c.t_tok(c.N_BIG, F4)                  # 30B 每 token 时间
TT_MID = c.t_tok(c.N_MID, F4)                  # 8B 每 token 时间
T_STREAM5 = c.W_BIG / B5                       # UFS 5.0 流一遍 30B 权重
DL_SHORT = 200                                 # 6.7 的短轮次
T_LOCAL = DL_SHORT * TT_MID
ROUTE_X = T_STREAM5 / T_LOCAL
BE5 = c.break_even(c.W_BIG, B5, c.N_BIG, F4)
BE4 = c.break_even(c.W_BIG, c.B_UFS['UFS4'], c.N_BIG, F4)
E_OP = c.e_op()
E_COMP_MID = c.e_comp_tok(c.N_MID)
E_MOVE_MID = c.e_move_tok(c.W_MID, 4096, c.E_LPDDR)
E_COMP_BIG = c.e_comp_tok(c.N_BIG)
DLE = c.energy_break_even(c.W_BIG, c.N_BIG)
F_LO, F_HI = c.lora_energy_range()
TOPS8, TOPS4 = c.F_PEAK['W8A8'] / 1e12, c.F_PEAK['W4A8'] / 1e12
BASELINE = (f"NPU {TOPS8:.0f} TOPS @W8A8 / {TOPS4:.0f} TOPS @W4A8、prefill MFU {c.MFU_PREFILL:.0%}、"
            f"满算力持续 {c.P_NPU:.0f} W、LPDDR6 {c.B_LPDDR6 / 1e9:.1f} GB/s、UFS 5.0 {B5 / 1e9:.1f} GB/s")


def K(x, nd=2):
    return f"{x / 1e3:.{nd}f}K"


def _p(t, s=11, c_=k.INK, b=False):
    return [{"t": t, "s": s, "c": c_, "b": b}]


def _path(p, s=9, width=45):
    """路径段落：过长时在最后一个 / 处断成「目录/」+「文件名」两段，避免任意位置折行。"""
    cut = p.rfind("/") + 1
    parts = [p[:cut], p[cut:]] if len(p) > width and cut else [p]
    return [[{"t": t, "s": s, "c": k.TEALDK, "f": k.MONO}] for t in parts]


# ---------------------------------------------------------------- 49
def slide_6_5_6(prs):
    s = k.add_slide(prs, "6.5 / 6.6", "安全域 · 降级路径", half_life=("不变量",),
                    source="v3.4 §6.5、§6.6；§0.4 第 5 类不变量（对抗）；附录 B 遗留问题 2")
    lx, lw = 0.45, 6.05
    k.text(s, I(lx), I(1.05), I(lw), I(0.32),
           [[{"t": "6.5 安全域 ", "s": 12, "c": k.TEALDK, "b": True}, k.hl("不变量")]],
           anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(lx), I(1.4), I(lw), I(0.5), [
        _p("依据 0.4 第 5 类不变量（对抗）：高价值、在委托权限下持续处理不可信输入——这个组合必然招致攻击。",
           10.5, k.MUTE)])
    k.table(s, I(lx), I(1.95), I(lw), I(1.2), ["攻击", "机制", "危险度"], [
        ["即时注入", "构造的消息/网页操纵守门与消化的判断，乃至操纵代为发出的回复", "高"],
        ["记忆投毒", "恶意内容被摄入索引并持久化，在未来任意时刻被检索出来影响决策",
         [[{"t": "更高——它穿越时间", "b": True, "c": k.RED}]]],
    ], col_w=[1.0, 3.7, 1.35], s=10, first_col_bold=True)
    k.text(s, I(lx), I(3.3), I(lw), I(0.3), [_p("三条架构要求", 11, k.TEALDK, True)])
    reqs = [("一、输入域需要信任边界",
             "来自传感器的数据（用户自己产生）与来自消息/网页/工具返回的数据（他人产生）必须分流；"
             "后者不能直接进入有执行权限的上下文。"),
            ("二、记忆条目的 provenance 是一等公民字段",
             "每条记忆携带「谁产生的、经过谁的手、可信度」，检索时按信任分级注入上下文。这不是软件补丁——"
             "它决定记忆条目的 schema，是数据结构级决策，必须在 L1 设计时确定。"),
            ("三、守门是一个每天被攻击数百次的分类器",
             "App 会对抗性地优化通知文案以操纵守门模型：今天的标题党优化人的注意力，明天优化 agent 的判断。"
             "这是 2.2 把守门降级的第二个理由。")]
    y = 3.62
    for (t, body), h in zip(reqs, (0.9, 1.1, 0.9)):
        k.box(s, I(lx), I(y), I(lw), I(h), [_p(t, 10.5, k.TEALDK, True), _p(body, 10.5)],
              fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
        y += h + 0.1

    rx, rw = 6.83, 6.05
    k.text(s, I(rx), I(1.05), I(rw), I(0.32), [_p("6.6 降级路径", 12, k.TEALDK, True)],
           anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(rx), I(1.4), I(rw), I(0.5), [
        _p("架构文档通常只写成功路径。但以下失败必然发生，且有硬件后果：", 10.5, k.MUTE)])
    k.table(s, I(rx), I(1.95), I(rw), I(2.75), ["失败", "降级动作", "硬件后果"], [
        ["过热降频", "从 6.4 的 UFS 路径退回本地中模型；或降频延长完成时间", "需要多档位模型共存"],
        ["断网", "云桥路径退回本地；隐状态前缀不可再生，需本地重建", "端侧必须保留完整权重（见 5.4 的 2×2 右下角浪费）"],
        ["端侧低置信度", "升级到云，或明确告知用户能力边界", "需要置信度估计机制"],
        ["记忆冲突", "按 provenance 优先级裁决，保留冲突记录", "记忆 schema 需支持多版本"],
    ], col_w=[1.15, 2.7, 2.2], s=10.5, first_col_bold=True, hl_rows=(0,), hl_color=k.BAND)
    k.box(s, I(rx), I(4.9), I(rw), I(0.9), [
        _p("关键容量后果", 11, k.TEALDK, True),
        _p("降级要求同时存在多个能力档位的模型（小 + 中，可能 + 大）。容量预算只算一份模型是低估。", 10.5)],
        fill=k.BAND, line=k.TEAL, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.text(s, I(rx), I(5.95), I(rw), I(0.6), [
        _p("与 6.4 动态驻留争 LPDDR：竞争收窄为任务期内，但容量总账仍需合并计算（附录 B 遗留问题 2）。",
           10, k.MUTE)])
    k.notes(s, "6.5 从对抗不变量推出三条架构要求，其中 provenance 是数据结构级决策；6.6 每种失败都有硬件后果，"
               "多档位模型共存直接抬高容量预算。")


# ---------------------------------------------------------------- 50
def slide_6_7(prs):
    s = k.add_slide(prs, "6.7", "调度：控制平面的职责清单", half_life=("快变量",),
                    source="v3.4 §6.7、§6.4.2；calc.py f_eff() / t_tok() / break_even()")
    lx, lw = 0.45, 6.7
    k.text(s, I(lx), I(1.05), I(lw), I(0.32), [_p("职责清单（9 项）", 12, k.TEALDK, True)],
           anchor=MSO_ANCHOR.MIDDLE)
    k.table(s, I(lx), I(1.42), I(lw), I(4.1), ["职责", "服务的发现", "性质"], [
        ["轮次级路由（ΔL 判据）", "6.4.2", "决定可行性"],
        ["相位识别与电源域切换", "4.5 第二层矛盾", "决定可行性"],
        ["上下文工程（什么进上下文、压缩率）", "2.4.1 token 账", "决定成本"],
        ["Prefix 复用与 KV 生命周期", "5.1", "决定成本"],
        ["唤醒拓扑与模态可用性管理", "6.2.1", "决定功耗"],
        ["功耗包络动态分配", "4.5 / 6.4.5", "决定热可行性"],
        ["可抢占性与 QoS 分级", "常驻与突发共存", "决定体验"],
        ["降级决策", "6.6", "决定鲁棒性"],
        ["攒批（仅并行 subagent）", "6.4.2", "决定成本"],
    ], col_w=[3.0, 1.9, 1.5], s=10.5, hl_rows=(0,), hl_color=k.BAND)
    k.box(s, I(lx), I(5.7), I(lw), I(1.2), [
        _p("性质分布", 10.5, k.TEALDK, True),
        _p("决定可行性 2 项 · 决定成本 3 项 · 功耗 / 热可行性 / 体验 / 鲁棒性 各 1 项", 10.5),
        _p("控制平面（调度系统）与 mW 级输入域、W 级思考/输出统一池并列（摘要）。", 10, k.MUTE)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    rx, rw = 7.35, 5.53
    k.formula_box(s, I(rx), I(1.05), I(rw), I(2.85),
                  f"路由代价：ΔL = {DL_SHORT} 的短轮次错路由到 UFS 大模型", [
        k.fx("① 错路由：UFS 5.0 流一遍 30B 权重（W = 15 GB）", s=10.5, f=k.YAHEI),
        k.fx(f"   t_{{stream}} = W ÷ B_{{ufs}} = 15 GB ÷ {B5 / 1e9:.1f} GB/s ≈ {T_STREAM5:.2f} s", s=10.5),
        k.fx(f"   计算 {DL_SHORT} × {TT_BIG * 1e3:.3f} ms ≈ {DL_SHORT * TT_BIG:.3f} s，藏在流式之下", s=10.5),
        k.fx(f"② 本地 8B：t_{{tok}} = 2N ÷ F_{{eff}} = 2 × 8×10⁹ ÷ 140×10¹² ≈ {TT_MID * 1e3:.3f} ms", s=10.5),
        k.fx(f"   t_{{local}} = ΔL × t_{{tok}} = {DL_SHORT} × {TT_MID * 1e3:.3f} ms ≈ {T_LOCAL:.3f} s", s=10.5),
        k.fx("③ 比值 = W·F_{eff} ÷ (2N·ΔL·B_{ufs})", s=10.5),
        k.fx(f"   = 15×10⁹ × 140×10¹² ÷ (2 × 8×10⁹ × {DL_SHORT} × 10.8×10⁹)", s=10.5),
        k.fx(f"   ≈ {ROUTE_X:.1f} → 差约 {round(ROUTE_X, -1):.0f} 倍", s=10.5, b=True, c=k.TEALDK),
        k.fx(f"④ ΔL = {DL_SHORT} ≪ 平衡点 ΔL* ≈ {K(BE5)}（6.4.2）→ 应路由到本地", s=10.5),
    ], s=10.5)
    k.text(s, I(rx), I(4.05), I(rw), I(0.3), [_p(f"同一轮（ΔL = {DL_SHORT}）的墙钟时间 · 线性刻度", 10.5, b=True)])
    bx, bw = rx + 1.3, 3.2
    for i, (lab, t, txt, col) in enumerate((("UFS 30B 流式", T_STREAM5, f"{T_STREAM5:.2f} s", k.RED),
                                            ("本地 8B", T_LOCAL, f"{T_LOCAL:.3f} s", k.TEAL))):
        y = 4.42 + i * 0.42
        wbar = max(bw * t / T_STREAM5, 0.03)
        k.text(s, I(rx), I(y), I(1.25), I(0.32), [_p(lab, 10)], anchor=MSO_ANCHOR.MIDDLE)
        k.rect(s, I(bx), I(y + 0.05), I(wbar), I(0.22), fill=col)
        k.text(s, I(bx + wbar + 0.06), I(y), I(0.9), I(0.32), [_p(txt, 10, col, True)],
               anchor=MSO_ANCHOR.MIDDLE)
    k.box(s, I(rx), I(5.4), I(rw), I(0.85), [
        [{"t": "调度器的价值量级：", "b": True, "s": 11, "c": k.TEALDK},
         {"t": f"错路由的代价是流一遍权重 {T_STREAM5:.2f} s（UFS 5.0），本地 8B 只需 {T_LOCAL:.3f} s——", "s": 11},
         {"t": f"差约 {round(ROUTE_X, -1):.0f} 倍，而非百分之几十。", "s": 11, "b": True, "c": k.RED}]],
        fill=k.WHITE, line=k.TEAL, align=PP_ALIGN.LEFT)
    k.text(s, I(rx), I(6.45), I(rw), I(0.45), [
        _p("口径：本地 8B INT4（常驻中模型，权重在 LPDDR）；W4A8 有效 140 TOPS；UFS 5.0 10.8 GB/s。", 9.5, k.MUTE)])
    k.notes(s, "错路由一个 ΔL = 200 的短轮次：UFS 路径要流一遍 15 GB 权重 1.39 s，本地 8B 只算 0.023 s，"
               "约 60 倍——这是轮次级路由必须进控制平面的量级依据。")


# ---------------------------------------------------------------- 51
def slide_ch7_1_3(prs):
    s = k.add_slide(prs, "第七章", "总结论（一至三）", half_life=("快变量",),
                    source="v3.4 第七章结论一至三、§6.4.4；calc.py e_op() / e_comp_tok() / e_move_tok() / energy_break_even()")
    lx, lw = 0.45, 7.7
    k.text(s, I(lx), I(1.05), I(lw), I(0.32),
           [[{"t": "结论一　能耗分相位记账 ", "s": 12, "c": k.TEALDK, "b": True}, k.hl("快变量")]],
           anchor=MSO_ANCHOR.MIDDLE)
    k.text(s, I(lx), I(1.38), I(lw), I(0.6), [
        _p("「搬运为王」是 decode 时代的公理——那时每读一字节只做 2 次运算；负载翻转为 prefill 主导后，"
           "权重在 DRAM 的 prefill 能耗霸权回到 MAC 阵列；但权重从 UFS 流入时，搬运与计算回到同一量级。", 10.5)])
    mv_be5 = c.e_move_tok(c.W_BIG, BE5)
    k.formula_box(s, I(lx), I(2.0), I(lw), I(1.78),
                  f"论据（6.4.4）：每 op 能耗 = 4 W ÷ 140 TOPS ≈ {E_OP * 1e12:.4f} pJ/op（W4A8）", [
        k.fx("① 权重在 DRAM（本地 8B，ΔL = 4K）", s=10.5, f=k.YAHEI),
        k.fx(f"   E_{{comp}} = 2N·e_{{op}} = 16 GFLOP × {E_OP * 1e12:.4f} pJ ≈ {E_COMP_MID * 1e3:.3f} mJ/token",
             s=10.5),
        k.fx(f"   E_{{move}} = W·e_{{lpddr}} ÷ ΔL = 4 GB × 0.05 nJ/B ÷ 4096 ≈ {E_MOVE_MID * 1e3:.3f} mJ/token",
             s=10.5),
        k.fx(f"   E_{{comp}} ÷ E_{{move}} ≈ {E_COMP_MID / E_MOVE_MID:.1f} 倍 → 计算主导", s=10.5, b=True, c=k.TEALDK),
        k.fx(f"② 权重流自 UFS（30B）：ΔL_{{E}} = W·e_{{ufs}} ÷ E_{{comp}} = {c.W_BIG * c.E_UFS:.1f} J ÷ "
             f"{E_COMP_BIG * 1e3:.2f} mJ ≈ {K(DLE, 1)}", s=10.5),
        k.fx(f"   ΔL < {K(DLE, 1)} 时搬运 > 计算（ΔL = {K(BE5)}：计算 ÷ 搬运 ≈ {E_COMP_BIG / mv_be5:.2f}）→ 同量级",
             s=10.5, b=True, c=k.RED),
    ], s=10.5)
    k.table(s, I(lx), I(3.9), I(lw), I(1.5), ["相位", "能耗主项", "优化对象"], [
        ["Prefill，权重在 DRAM（token 账主体）", "计算", "MAC 能效、量化位宽"],
        ["Prefill，权重流自 UFS（6.4）", "搬运 ≈ 计算", "UFS 每字节能耗、动态驻留容量 C、ΔL 路由阈值"],
        ["Decode（时间账主体）", "搬运", "近存、带宽、量化位宽"],
        ["常驻感知", "搬运 + 唤醒开销", "电源域设计"],
    ], col_w=[2.85, 1.4, 3.45], s=10, hl_rows=(1,))
    k.text(s, I(lx), I(5.55), I(lw), I(0.3), [_p("唯一同时作用于各相位的杠杆是量化位宽。", 10.5, b=True)])
    k.box(s, I(lx), I(5.92), I(lw), I(0.98), [
        [{"t": "论据的适用范围：", "b": True, "c": k.RED, "s": 10.5},
         {"t": "按 4 W @140 TOPS 的每 op 能耗，UFS 路径搬运 ≈ 计算；「计算远大于搬运」只在权重位于 DRAM 的 prefill 成立"
               f"（≈ {E_COMP_MID / E_MOVE_MID:.1f} 倍），所以结论一分两种 prefill 记账。", "s": 10.5, "c": k.RED}]],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT)

    rx, rw = 8.3, 4.58
    k.box(s, I(rx), I(1.05), I(rw), I(1.4), [
        _p("结论二　三预算独立", 12, k.TEALDK, True),
        _p("算力、带宽、容量三份预算必须各自独立可缩放，不互相锁死。", 10.5, b=True),
        _p("依据：模型迭代比硅片快一个数量级（半年 vs 三年）。任何针对特定瓶颈的硬件优化都在与更快的对手赛跑——"
           "第五章的三次冲击全部发生在模型/算法层，而不是需求层。", 10)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(rx), I(2.55), I(rw), I(1.12), [
        _p("押注对象（5.3.1 / 5.3.2）", 10.5, k.TEALDK, True),
        _p("D-w 拆不掉，但可以被压到不痛（量化 + 小模型化）；押注对象是不等式「D-w 痛度 > 通用方案阈值」"
           "——需要持续跟踪的经验问题。", 10),
        [{"t": "正面押注两项不依赖模型机制的能力：", "s": 10},
         {"t": "每 op 能效", "s": 10, "b": True}, {"t": "与", "s": 10},
         {"t": "并发能力", "s": 10, "b": True}, {"t": "。", "s": 10}]],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(rx), I(3.77), I(rw), I(0.85), [
        [{"t": "反面教材：", "s": 10, "b": True, "c": k.RED},
         {"t": "任何把容量与带宽锁死在同一个封装决策里的设计（如把全部预算押在极高带宽的小容量近存堆叠），"
               "一旦范式偏移就全盘皆输。", "s": 10}]],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.formula_box(s, I(rx), I(4.75), I(rw), I(2.15), "结论三　专用化律", [
        k.fx("异构的正确粒度：按负载稳定性分层专用化", s=10.5, f=k.YAHEI),
        k.fx("硬化程度 ∝ 算法稳定年限 ÷ 能效敏感度", s=11, b=True, c=k.TEALDK),
        k.fx("判据轴：输出空间维度（有限离散 / schema 约束 / 自由序列）", s=10, f=k.YAHEI),
        k.fx("应用：输入域激进专用（C 类形态十年稳定）；", s=10, f=k.YAHEI),
        k.fx("思考域保留可编程——D-a 与 P 类的稳定性低于直觉（注意力机制与 prefill 路径都在快速迭代）。",
             s=10, f=k.YAHEI),
    ], s=12)
    k.notes(s, "结论一按相位分写：DRAM prefill 计算是搬运的 9.4 倍，UFS 流式路径搬运与计算同量级（ΔL_E ≈ 4.4K）；"
               "结论二、三给出预算与专用化的判据。")


# ---------------------------------------------------------------- 52
def slide_ch7_4_6(prs):
    s = k.add_slide(prs, "第七章", "总结论（四至六）", half_life=("快变量",),
                    source="v3.4 第七章结论四至六；§2.4.1、§2.4.2；calc.py t_tok() / decode_tok_s()")
    lx, lw = 0.45, 6.1
    k.text(s, I(lx), I(1.05), I(lw), I(0.32), [_p("结论四　常驻优先律", 12, k.TEALDK, True)],
           anchor=MSO_ANCHOR.MIDDLE)
    k.box(s, I(lx), I(1.45), I(2.55), I(0.62), [_p("手机三十年的哲学", 10, k.MUTE), _p("为峰值堆料", 11, k.MUTE, True)],
          fill=k.SLATEF, line=k.SLATE)
    k.arrow(s, I(lx + 2.6), I(1.83), I(lx + 3.45), I(1.83), color=k.TEAL, w=1.75)
    k.text(s, I(lx + 2.55), I(1.47), I(0.95), I(0.3), [_p("相反", 9.5, k.TEALDK, True)], align=PP_ALIGN.CENTER)
    k.box(s, I(lx + 3.5), I(1.45), I(2.6), I(0.62),
          [_p("小秘书负载的时间结构", 10, k.TEALDK), _p("「常驻 + 突发」共存", 11, b=True)],
          fill=k.BAND, line=k.TEAL)
    k.box(s, I(lx), I(2.2), I(lw), I(0.62), [
        [{"t": "核心命题：", "b": True, "s": 11, "c": k.TEALDK},
         {"t": "在恒定功率包络内让常驻与突发负载共享资源且互不伤害。", "s": 11, "b": True}]],
        fill=k.WHITE, line=k.TEAL, align=PP_ALIGN.LEFT)
    k.text(s, I(lx), I(2.92), I(lw), I(0.3), [_p("硬件体现", 10.5, k.TEALDK, True)])
    chips = ["分域供电", "可分区休眠的存储层级", "细粒度可拆分的算力", "相位级独立 DVFS（4.5）"]
    cw = (lw - 3 * 0.08) / 4
    for i, t in enumerate(chips):
        k.box(s, I(lx + i * (cw + 0.08)), I(3.22), I(cw), I(0.58), [_p(t, 10)], fill=k.SLATEF, line=k.SLATE)
    k.text(s, I(lx), I(3.88), I(lw), I(0.5), [
        [{"t": "「常驻」需按模态细分（6.2.1）：", "b": True, "s": 10},
         {"t": "视觉感知实际占空比仅 10–20%，预算可据此放宽。", "s": 10}]])

    rx, rw = 6.78, 6.1
    k.text(s, I(rx), I(1.05), I(rw), I(0.32), [_p("结论五　记忆闭环", 12, k.TEALDK, True)],
           anchor=MSO_ANCHOR.MIDDLE)
    nodes = [("思考域", "W 级统一池"), ("输入域 encoder", "mW 级"), ("结构化记忆条目", "带 provenance")]
    bw, gap, by, bh = 1.45, 0.87, 1.45, 0.62
    xs = [rx + i * (bw + gap) for i in range(3)]
    for x, (t1, t2) in zip(xs, nodes):
        k.box(s, I(x), I(by), I(bw), I(bh), [_p(t1, 10.5, b=True), _p(t2, 9, k.MUTE)], fill=k.BAND, line=k.TEAL)
    for i, lab in enumerate(("归档记忆", "压缩为条目")):
        x1 = xs[i] + bw
        k.arrow(s, I(x1), I(by + bh / 2), I(xs[i + 1]), I(by + bh / 2), color=k.TEAL, w=1.5)
        k.text(s, I(x1), I(by + 0.01), I(gap), I(0.28), [_p(lab, 9, k.TEALDK)], align=PP_ALIGN.CENTER)
    yb, yr = by + bh, by + bh + 0.24
    cx0, cx2 = xs[0] + bw / 2, xs[2] + bw / 2
    k.arrow(s, I(cx2), I(yb), I(cx2), I(yr), color=k.TEAL, w=1.5, head=False)
    k.arrow(s, I(cx2), I(yr), I(cx0), I(yr), color=k.TEAL, w=1.5, head=False)
    k.arrow(s, I(cx0), I(yr), I(cx0), I(yb), color=k.TEAL, w=1.5)
    k.text(s, I(cx0 + 0.3), I(yr + 0.02), I(cx2 - cx0 - 0.6), I(0.28),
           [_p("检索时按信任分级注入上下文（6.5）", 9, k.TEALDK)], align=PP_ALIGN.CENTER)
    k.text(s, I(rx), I(2.62), I(rw), I(0.55), [
        _p("归档记忆经输入域 encoder 压缩为结构化条目——输入域与思考域互为上下游。"
           "记忆不是附加功能，是架构的结构性组件。", 10.5)])
    k.box(s, I(rx), I(3.25), I(rw), I(0.88), [
        [{"t": "schema 必须包含：", "b": True, "s": 10.5, "c": k.TEALDK},
         {"t": "provenance 字段（来源、经手、可信度）与推理依据", "s": 10.5}],
        [{"t": "两个独立理由：", "b": True, "s": 10.5, "c": k.TEALDK},
         {"t": "安全（6.5）· 可纠正性（2.5）", "s": 10.5}],
        _p("→ 这直接增加容量预算", 10.5, k.RED, True)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    k.text(s, I(0.45), I(4.33), I(12.43), I(0.32),
           [[{"t": "结论六　两本账不可互换 ", "s": 12, "c": k.TEALDK, "b": True}, k.hl("快变量")]],
           anchor=MSO_ANCHOR.MIDDLE)
    k.rect(s, I(0.45), I(4.7), I(0.07), I(0.7), fill=k.TEAL)
    k.box(s, I(0.58), I(4.7), I(12.3), I(0.7), [
        _p("Token 账（90%+ 在 prefill）决定成本与能耗；时间账（多数墙钟在 decode）决定交互体验，且时间账须再乘"
           "用户在线状态的场景权重（2.4.2）。两者方向相反，任何只看一本账的 sizing 都会错。", 11.5)],
        fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT)
    t_pre = 4000 * TT_MID
    tps = c.decode_tok_s(c.W_MID)
    t_dec = 300 / tps
    k.formula_box(s, I(0.45), I(5.52), I(5.6), I(1.38), "两本账算例（2.4.1：8B INT4，一轮 4K prefill + 300 token decode）", [
        k.fx(f"Token 账：ΔL : k ≈ 10:1–50:1；本例 4000 : 300 ≈ {4000 / 300:.0f}:1", s=10),
        k.fx(f"时间账：Prefill 2 × 8×10⁹ × 4000 ÷ 140 TOPS ≈ {t_pre:.2f} s", s=10),
        k.fx(f"        Decode 300 ÷ (113.8 GB/s ÷ 4 GB ≈ {tps:.0f} tok/s) ≈ {t_dec:.1f} s", s=10),
        k.fx(f"墙钟比 ≈ 1:{t_dec / t_pre:.0f} → 90%+ token 在 prefill，多数墙钟在 decode", s=10, b=True, c=k.TEALDK),
    ], s=10)
    k.table(s, I(6.2), I(5.52), I(6.68), I(1.3), ["模式（2.4.2）", "用户状态", "体验指标", "带宽权重"], [
        ["Chat / 语音双工", "在读 token / 在听", "吐字速度、轮转延迟", "高——带宽直接等于体验"],
        ["前台 Agent", "等任务完成", "总完成时间", "中——按 decode 的墙钟占比加权"],
        ["后台 Agent", "不等待", "无（只有成本）", "≈0——预算应全部让给能效"],
    ], col_w=[1.35, 1.4, 1.5, 2.43], s=9.5)
    k.notes(s, "结论四讲常驻与突发共存，结论五讲记忆是结构性组件且 provenance 抬高容量预算；"
               "结论六：token 账与时间账方向相反（13:1 vs 1:23），只看一本账的 sizing 必错。")


# ---------------------------------------------------------------- 53
def slide_app_a_b(prs):
    s = k.add_slide(prs, "附录 A / B", "修订沿革 · 关键假设",
                    source="v3.4 附录 A、附录 B；calc.py 参数基线")
    k.text(s, I(0.45), I(1.05), I(12.43), I(0.32), [_p("附录 A　修订沿革", 12, k.TEALDK, True)],
           anchor=MSO_ANCHOR.MIDDLE)
    ga = k.table(s, I(0.45), I(1.4), I(12.43), I(2.77), ["版本", "主要内容"], [
        ["v2.0", "初版体系化。主要缺陷：缺模型/算法层；「搬运为王」过度推广；软件四层与负载原语旁路。"],
        ["v3.0", "方法论重构（链条降级为约束检查器、半衰期分级、五类不变量）；分离 token 账与时间账；"
                 "D 类拆为 D-w/D-a；轮次级成本模型；桥账本；安全域与降级路径入章。"],
        ["v3.1", "外部评审修订。存在性≠投资论证（押注对象改为不等式 + 每 op 能效 + 并发能力）；算力 sizing 补 D-a 项；"
                 "带缓存平衡点重算（pin 策略，识别 LRU 陷阱）；时间账三档加权；E 类改 late interaction 首选解；"
                 "补 V 类原语与语音双工压力测试；F 类版本迁移三解；热墙表述软化。"],
        ["v3.2", "可读性修订。剥离正文修订痕迹、加摘要与词汇表、句子层面梳理。技术内容与 v3.1 完全一致。"],
        ["v3.3", [
            _p(f"① 参数基线改为 {BASELINE}；全文依赖算力的数字重算（2.4.1、4.2、4.3、5.2.2、6.4、6.7）", 9.5),
            _p("② 6.4 永久固定驻留改为动态驻留；新增 6.4.2.2（MoE 在流式 prefill 中是负收益）", 9.5),
            _p("③ 结论翻转：5.2.2 桥时延结论（以稀疏注意力为前提）；6.4.4 与第七章结论一能耗结论", 9.5, k.RED, True),
            _p("④ 4.3 新增 2029 负载基线与各原语负载实例表；修订 C、E、V、G、F、Ctrl 类 8 处表述", 9.5)]],
        ["v3.4（本版）", [
            _p("可读性修订：剥离正文版本叙述；修正 5.2 节两表「占优」口径混读；时间账与热约束注互相指引；口径混用处补齐标注。", 9.5),
            _p(f"另订正 5.2.2「只剩能力优势」与「仍省端侧算力」的矛盾、F 类能耗口径（{F_LO / 1e3:.2f}–{F_HI / 1e3:.1f} kJ）。"
               "技术结论与 v3.3 一致；与 v3.2 的逐项对照见附录 D。", 9.5, k.TEALDK, True)]],
    ], col_w=[1.1, 11.33], s=9.5, first_col_bold=True, hl_rows=(5,), hl_color=k.BAND)
    for r, h in zip(ga.table.rows, (0.3, 0.26, 0.26, 0.42, 0.26, 0.85, 0.42)):   # 按内容行数定行高
        r.height = I(h)

    k.text(s, I(0.45), I(4.24), I(12.43), I(0.3), [_p("附录 B　关键假设（按半衰期分级）", 12, k.TEALDK, True)],
           anchor=MSO_ANCHOR.MIDDLE)

    def lv(t, col):
        return [[{"t": t, "b": True, "c": col}]]
    gb = k.table(s, I(0.45), I(4.56), I(12.43), I(2.28), ["假设", "级别", "若坍塌的影响"], [
        ["极低比特模型可在目标尺度质量平价", lv("未验证", k.RED), "5.3 推论退回，带宽方案复活"],
        ["共享状态在生态上可行", lv("关键非技术假设", k.BLUE), "第六章统一池失去前提"],
        ["隐状态桥跨版本稳定", lv("未验证", k.RED), "云桥路径作废，退回本地/UFS"],
        ["端侧小模型 KV 压缩跟进前沿", lv("空白", k.MUTE), "6.3.2 KV 简化回滚"],
        ["890 B/token、配比公式各参数", lv("快变量", k.AMBER), "sizing 数字整体平移"],
        [f"NPU {TOPS8:.0f} / {TOPS4:.0f} TOPS（W8A8 / W4A8）、prefill MFU {c.MFU_PREFILL:.0%}、满算力持续 {c.P_NPU:.0f} W",
         lv("目标 SoC 口径（快变量）", k.AMBER), "平衡点、脊点、桥时延对比整体平移；平衡点与有效算力成正比"],
    ], col_w=[5.9, 2.1, 4.43], s=10)
    for i, r in enumerate(gb.table.rows):
        r.height = I(0.3 if i == 0 else 0.33)
    k.notes(s, "v3.3 的技术修订集中在参数基线、6.4 三处修订与两处结论翻转；v3.4 是可读性修订加两处订正。"
               "算力基线假设列为目标 SoC 口径，它变则平衡点按有效算力成比例平移。")


# ---------------------------------------------------------------- 54
def slide_app_b(prs):
    s = k.add_slide(prs, "附录 B", "待实测清单 · 评审遗留问题",
                    source="v3.4 附录 B；§6.4.2、§6.4.2.1、§6.4.5；calc.py break_even() / t_round_thermal() / t_round_free()")
    k.text(s, I(0.45), I(1.05), I(12.43), I(0.32),
           [[{"t": "待实测", "s": 12, "c": k.TEALDK, "b": True},
             {"t": "（按优先级排序：A → B → C）", "s": 10.5, "c": k.MUTE}]], anchor=MSO_ANCHOR.MIDDLE)
    tr_be = c.t_round_thermal(c.W_BIG, BE5, c.N_BIG)
    tr_10k = c.t_round_thermal(c.W_BIG, 10000, c.N_BIG)
    tf_be = c.t_round_free(c.W_BIG, B5, BE5, c.N_BIG, F4)
    tf_10k = c.t_round_free(c.W_BIG, B5, 10000, c.N_BIG, F4)
    er_be = c.W_BIG * c.E_UFS + BE5 * E_COMP_BIG
    er_10k = c.W_BIG * c.E_UFS + 10000 * E_COMP_BIG
    be_c = [K(c.break_even(c.W_BIG, B5, c.N_BIG, F4, C)) for C in (1.5e9, 3e9, 5e9)]
    cols = [
        ("实测 A", "任务期间可用于动态驻留的 LPDDR 容量 C，与 UFS 5.0 实测持续带宽",
         ("判读公式（6.4.2.1）", [
             k.fx("ΔL* = (W − C) ÷ (B_{ufs}·t_{tok})", s=10.5, b=True, c=k.TEALDK),
             k.fx(f"C = 0：{K(BE5)}（无驻留上界）", s=10),
             k.fx(f"C = 1.5 / 3 / 5 GB：{' / '.join(be_c)}", s=10),
             k.fx(f"B_{{ufs}} 取 UFS 4.0（C = 0）：{K(BE4)}", s=10)]),
         f"6.4 平衡点取 {K(BE5)}，还是 (1 − C/W) × {K(BE5)}"),
        ("实测 B", "端侧小模型的 KV 压缩率能否接近 890 B/token",
         ("关联假设（附录 B）", [
             k.fx("「890 B/token、配比公式各参数」：快变量", s=10, f=k.YAHEI),
             k.fx("  → 若偏离，sizing 数字整体平移", s=10, f=k.YAHEI, c=k.MUTE),
             k.fx("「端侧小模型 KV 压缩跟进前沿」：空白", s=10, f=k.YAHEI),
             k.fx("  → 若不成立，6.3.2 KV 简化回滚", s=10, f=k.YAHEI, c=k.MUTE)]),
         "6.3.2 的 KV 简化能否成立；sizing 数字是否整体平移"),
        ("实测 C", "6.4 路径降频后的实际吞吐",
         ("热约束下每轮时间（6.4.5）", [
             k.fx("t_{round} ≥ E_{round} ÷ P_{env}", s=10.5, b=True, c=k.TEALDK),
             k.fx("E_{round} = (W − C)·e_{ufs} + ΔL·E_{comp}", s=10),
             k.fx(f"P_{{env}} = {c.P_ENV} W（包络上沿），C = 0：", s=10),
             k.fx(f"{K(BE5)}：{er_be:.1f} J → {tr_be:.2f} s（无约束 {tf_be:.2f} s）", s=10),
             k.fx(f"10K：{er_10k:.1f} J → {tr_10k:.1f} s（无约束 {tf_10k:.2f} s）", s=10)]),
         "6.4 的定位是「日常低速路径」还是「插电路径」"),
    ]
    cw = (12.43 - 2 * 0.12) / 3
    for i, (name, what, (ft, lines), decide) in enumerate(cols):
        x = 0.45 + i * (cw + 0.12)
        k.box(s, I(x), I(1.42), I(cw), I(0.36), [_p(f"{name} · 优先级 {i + 1}", 11, k.WHITE, True)],
              fill=k.TEAL, line=None)
        k.box(s, I(x), I(1.84), I(cw), I(0.6), [
            [{"t": "测什么：", "b": True, "s": 10.5, "c": k.TEALDK}, {"t": what, "s": 10.5}]],
            fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
        k.formula_box(s, I(x), I(2.52), I(cw), I(1.62), ft, lines, s=10.5)
        k.box(s, I(x), I(4.22), I(cw), I(0.56), [
            [{"t": "决定：", "b": True, "s": 10.5, "c": k.RED}, {"t": decide, "s": 10.5}]],
            fill=k.WHITE, line=k.TEAL, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    k.text(s, I(0.45), I(4.86), I(12.43), I(0.3), [_p("评审遗留问题（未闭环）", 12, k.TEALDK, True)],
           anchor=MSO_ANCHOR.MIDDLE)
    k.table(s, I(0.45), I(5.18), I(12.43), I(1.8), ["#", "问题", "关联"], [
        ["1", "桥账本时延对比缺云端 prefill 的排队与计算项，路由判据应使用端到端时延", "5.2.1 / 5.2.2"],
        ["2", "动态驻留只在任务期间占用 LPDDR，与 6.6 多档位模型的竞争收窄为任务期内，但容量总账仍需合并计算",
         "6.4.2.1 / 6.6"],
        ["3", "目标函数在守门场景需切换形态（最小化注意力占用 s.t. 不漏重要信息）——目标函数应与 sizing 一样分场景",
         "0.1"],
        ["4", f"语音双工的并发带宽账未闭合：V 类预留约 {c.voice_bw() / 1e9:.0f} GB/s，双工期间 LLM 的理解与 thinking decode 同时占带宽，"
              "分用前向时叠加可超 50 GB/s——需明确「共用一次前向 / 带宽预留 / 分时」的策略", "6.3.5 / 4.3 V 类"],
        ["5", "两处待补计算路径：Qwen3-8B 对照的「仅 12 tok/s」（4.3 D-a）与各口径的逐式推导，应补入 sources 文档",
         "4.3 D-a / sources"],
    ], col_w=[0.4, 10.0, 2.03], s=9.5, first_col_bold=True)
    k.notes(s, "三项实测按优先级排序：A 定平衡点，B 定 KV 简化，C 定 6.4 路径的定位。"
               "遗留问题 4（语音双工并发带宽）与 5（待补计算路径）为最近一轮评审新增。")


# ---------------------------------------------------------------- 55
def slide_refs(prs):
    s = k.add_slide(prs, "参考", "来源与本地佐证",
                    source="v3.4 全文与附录；本地记录路径相对仓库根目录；外部来源编号见第三栏")
    x1, w1 = 0.45, 4.0
    x2, w2 = 4.57, 4.95
    x3, w3 = 9.64, 3.24
    for x, w, t in ((x1, w1, "① 原文与本文件"), (x2, w2, "② 本地记录（路径 · 用途）"), (x3, w3, "③ 4.3 外部来源")):
        k.text(s, I(x), I(1.05), I(w), I(0.32), [_p(t, 12, k.TEALDK, True)], anchor=MSO_ANCHOR.MIDDLE)

    docs = [("修订基础：v3.2 原文 → v3.3 技术修订", ["端侧AI计算架构完整构想_v3.2_润色版.md",
                                            "surveys/on-device-ai-compute-arch/端侧AI计算架构完整构想_v3.3.md"],
             "v3.2 在仓库根目录、保持不动；v3.3 为参数基线与 6.4、4.3 的技术修订"),
            ("v3.4 润色版", ["surveys/on-device-ai-compute-arch/端侧AI计算架构完整构想_v3.4_润色版.md"],
             "本 PPT 的数字口径；页脚「v3.4 §」均指此文件"),
            ("calc.py 数字底座", ["surveys/on-device-ai-compute-arch/calc.py"],
             "参数基线与派生数字函数；tests/test_calc.py 锁定取值")]
    y = 1.42
    for (t, paths, use), h in zip(docs, (1.12, 0.88, 0.72)):
        k.box(s, I(x1), I(y), I(w1), I(h), [_p(t, 10.5, k.INK, True)] + sum((_path(p) for p in paths), []) + [_p(use, 9.5, k.MUTE)],
              fill=k.SLATEF, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
        y += h + 0.08
    k.table(s, I(x1), I(4.32), I(w1), I(2.5), ["calc.py 基线参数", "取值"], [
        ["NPU 峰值 @W8A8", f"{TOPS8:.0f} TOPS"],
        ["NPU 峰值 @W4A8", f"{TOPS4:.0f} TOPS"],
        ["Prefill MFU → 有效算力", f"{c.MFU_PREFILL:.0%} → {F4 / 1e12:.0f} TOPS @W4A8"],
        ["Decode MFU", f"{c.MFU_DECODE[0]:.0%}–{c.MFU_DECODE[1]:.0%}"],
        ["满算力持续功耗", f"{c.P_NPU:.0f} W"],
        ["LPDDR6 带宽", f"{c.B_LPDDR6 / 1e9:.1f} GB/s"],
        ["UFS 5.0 / 4.0 带宽", f"{B5 / 1e9:.1f} / {c.B_UFS['UFS4'] / 1e9:.1f} GB/s"],
        ["读能耗 UFS / LPDDR", f"{c.E_UFS * 1e9:.1f} / {c.E_LPDDR * 1e9:.2f} nJ/B"],
    ], col_w=[2.0, 2.0], s=9.5)

    recs = [("insight/N+1/on-device-model-swapping/on-device-model-swapping-CN.md",
             "LLM-aware Buffer Cache：通用 LRU 命中率 0.02 vs 钉住循环权重块 0.34–0.8（6.4.2.1 LRU 陷阱佐证）；"
             "PowerInfer-2 在 7 GB / 19 GB 内存下 2.13 / 11.68 tok/s（6.4.2.2）；KVNAND 等换入换出方案"),
            ("surveys/ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md",
             "UFS 4.0 实测带宽；PowerInfer-2 在 OnePlus 12 上跑 47B 达 11.68 tok/s"),
            ("insight/N+3/ufs5-computational-storage/ufs5-computational-storage-CN.md",
             "UFS 5.0：JESD220H（2026-02 发布）、10.8 GB/s（本文闪存基线）"),
            ("surveys/memory-capacity-crunch-CN.md", "中位旗舰 LPDDR 约 12 GB、DRAM 价格（容量预算背景）"),
            ("surveys/on-device-llm-memory-CN.md", "端侧大模型推理与内存/算力子系统综述（Android / iOS / HarmonyOS 横向对比）")]
    rows = [[str(i + 1), _path(p, width=58) + [_p(u, 9.5)]] for i, (p, u) in enumerate(recs)]
    gf = k.table(s, I(x2), I(1.42), I(w2), I(6 * 0.32), ["#", "路径 / 用途"], rows, col_w=[0.35, 4.6], s=9.5,
                 first_col_bold=True)
    for r in list(gf.table.rows)[1:]:            # 表头保持 0.32 in，数据行留足三到四行的高度
        r.height = I(0.9)
    k.text(s, I(x2), I(6.36), I(w2), I(0.55), [
        _p("注（原文文末）：未标注第三方来源的数据均为基于公开硬件参数的估算；关键数字的来源与置信度见配套 "
           "handoff 文档（编写中）。", 9.5, k.MUTE)])

    ext = _ext_sources()
    groups = [("C-S", "C 类 / 哨兵"), ("E-S", "E 类"), ("V-S", "V 类"), ("G-S", "G 类"), ("R4-S", "F / Ctrl-d / KV-io"), ("KV-S", "KV 格式")]
    rows = [[name, f"{sum(1 for r in ext if r[0].startswith(pre)):d} 条"] for pre, name in groups]
    k.table(s, I(x3), I(1.42), I(w3), I(2.6), ["4.3 负载实例的外部来源", "数量"], rows + [["合计", f"{len(ext)} 条"]],
            col_w=[2.2, 1.0], s=9.5, first_col_bold=True, hl_rows=(len(rows),), hl_color=k.BAND)
    k.text(s, I(x3), I(4.15), I(w3), I(2.7), [
        _p("逐条标题与链接见下一页「附录 C」。", 10, k.INK, True),
        _p("完整清单（约 110 条）与逐条核对记录：", 9.5, k.MUTE)] + _path("surveys/on-device-ai-compute-arch/sources/primitive-workloads-research.md") + [
        _p("编号前缀：C / E / V / G 为四组调研，R4 为 F / Ctrl-d / KV-io 组，KV-S46 为 DeepSeek-V4.1-Flash 官方模型卡。", 9.5, k.MUTE)])
    k.notes(s, "页脚中的「v3.4 §」均指 v3.4 润色版 md；本地记录为仓库内既有调研；4.3 外部来源已与评审对齐（2026-09-11）。")


def _ext_sources():
    md = pathlib.Path(__file__).resolve().parent / "端侧AI计算架构完整构想_v3.4_润色版.md"
    seg = md.read_text(encoding="utf-8").split("**4.3 节负载实例来源**", 1)[1]
    rows = []
    for line in seg.splitlines()[1:]:
        if line.startswith("|"):
            cells = [x.strip() for x in line.strip().strip("|").split("|")]
            if cells[0] not in ("编号", "---"):
                rows.append(cells)
        elif rows:
            break
    return rows


def _short_url(u, n=46):
    u = u.replace("https://", "").replace("http://", "")
    return u if len(u) <= n else u[:n - 12] + "…" + u[-11:]


def slide_app_c(prs):
    s = k.add_slide(prs, "附录 C", "4.3 负载实例的外部来源",
                    source="v3.4 §4.3 末「4.3 节负载实例来源」；完整链接与核对记录见 sources/primitive-workloads-research.md")
    ext = _ext_sources()
    half = (len(ext) + 1) // 2
    for i, part in enumerate((ext[:half], ext[half:])):
        rows = [[r[0], r[1], [{"t": _short_url(r[2]), "s": 8, "c": k.MUTE, "f": k.MONO}]] for r in part]
        k.table(s, I(0.45 + i * 6.3), I(1.05), I(6.13), I(0.3 * (len(rows) + 1)), ["编号", "来源", "链接"], rows,
                col_w=[0.75, 2.75, 2.63], s=8.5, first_col_bold=True)
    k.notes(s, "表内链接为缩写；完整 URL 见 v3.4 md 4.3 节末与调研草稿。")



# ---------------------------------------------------------------- 58
def slide_app_d(prs):
    s = k.add_slide(prs, "附录 D", "v3.2 → v3.4 修订对照",
                    source="v3.2 润色版 §2.4.1、§4.2、§5.2.2、§6.4、§6.7；v3.4 对应小节与附录 A；calc.py")
    B = lambda t, col=k.TEALDK: [[{"t": t, "b": True, "c": col}]]
    e4, e8 = c.e_op('W4A8') * 1e12, c.e_op('W8A8') * 1e12
    t_pre = 2 * c.N_MID * 4000 / F4
    tps = c.decode_tok_s(c.W_MID)
    t_dec = 300 / tps
    tb, tl, ts, _ = c.bridge_latency()
    p_ufs = c.p_ufs_hide(c.W_BIG, 4096, c.N_BIG, F4)
    be_moe = c.break_even(c.W_BIG, B5, c.N_MOE_ACTIVE, F4)

    lx, lw = 0.45, 5.2
    k.text(s, I(lx), I(1.05), I(lw), I(0.3), [_p("参数基线", 11.5, k.TEALDK, True)], anchor=MSO_ANCHOR.MIDDLE)
    k.table(s, I(lx), I(1.38), I(lw), I(3.1), ["参数", "v3.2", "v3.4"], [
        ["NPU 峰值", "50 TOPS", B(f"{TOPS8:.0f} @W8A8 / {TOPS4:.0f} @W4A8 TOPS")],
        ["Prefill MFU → 有效", "80% → 40 TOPS", B(f"{c.MFU_PREFILL:.0%} → {F4 / 2e12:.0f} / {F4 / 1e12:.0f} TOPS")],
        ["Decode MFU → 有效", "10–20% → 5–10 TOPS", "10–20% → 10–20 / 20–40 TOPS"],
        ["脊点带宽", "68 GB/s", B(f"LPDDR6 {c.B_LPDDR6 / 1e9:.1f} GB/s")],
        ["闪存基线", "UFS 4.0，~4 GB/s", B(f"UFS 5.0，{B5 / 1e9:.1f} GB/s")],
        ["NPU 功耗", "~4 W", f"满算力持续 {c.P_NPU:.0f} W"],
        ["每 op 能耗", "~0.3 pJ/op", B(f"{e4:.4f} / {e8:.3f} pJ/op")],
        ["读能耗 UFS / LPDDR", "0.5 / 0.05 nJ/B", "不变"],
        ["负载口径", "未单列窗口", B("2029 年量产、用到 2031 年")],
    ], col_w=[1.45, 1.55, 2.2], s=9, first_col_bold=True)
    x_f, x_u, x_l = F4 / 40e12, B5 / c.B_UFS['UFS4'], c.B_LPDDR6 / 68e9
    k.box(s, I(lx), I(4.62), I(lw), I(1.55), [
        _p("两处结论为什么翻转", 11, k.RED, True),
        _p(f"本地有效算力 40 → 140 TOPS（×{x_f:.1f}），而 UFS 带宽只 ×{x_u:.1f}（4 → 10.8 GB/s）、"
           f"LPDDR 只 ×{x_l:.1f}（68 → 113.8 GB/s）。", 10),
        _p("算力涨得比带宽快：流式平衡点上移，本地 prefill 追上桥传输，UFS 搬运能耗相对变重。", 10, b=True)],
        fill=k.REDLT, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
    k.box(s, I(lx), I(6.27), I(lw), I(0.68), [
        [{"t": "v3.3 → v3.4：", "s": 10, "b": True, "c": k.TEALDK},
         {"t": "技术结论一致；可读性修订加两处订正（见附录 A）。v3.4 列即 v3.3 的技术口径。", "s": 10}]],
        fill=k.BAND, line=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    rx, rw = 5.85, 7.03
    k.text(s, I(rx), I(1.05), I(rw), I(0.3), [_p("关键数字与结论", 11.5, k.TEALDK, True)], anchor=MSO_ANCHOR.MIDDLE)
    k.table(s, I(rx), I(1.38), I(rw), I(5.57), ["小节", "v3.2", "v3.4"], [
        ["2.4.1 时间账", "prefill 1.6 s / decode ~10 s（30 tok/s）；墙钟比 1:6",
         f"prefill {t_pre:.2f} s / decode {t_dec:.1f} s（{tps:.0f} tok/s）；墙钟比 1:{t_dec / t_pre:.0f}"],
        ["4.2 有效脊点", "prefill ~590 / decode ~110",
         f"prefill {c.ridge(F4 / 2):.0f} / {c.ridge(F4):.0f}；decode 88–176 / 176–351（W8A8 / W4A8）"],
        [B("5.2.2 桥时延", k.RED), "本地 40 s > 桥 14 s：压缩格式下桥在时延上也占优",
         B(f"本地 {tl:.1f} s < 桥 {tb:.0f} s：时延上本地占优（前提：稀疏注意力，≈ {ts:.1f} s）", k.RED)],
        ["6.4.1 配比", "4K chunk 需 2.5 GB/s，UFS 4.0 余量约 40%",
         f"4K chunk 需 {c.ratio_bw(F4, 4096) / 1e9:.2f} GB/s；UFS 4.0 只剩 16K 可行，UFS 5.0 成硬性要求"],
        ["6.4.2 平衡点", "ΔL* ≈ 2.5K（UFS 4.0，流 15 GB 约 3.75 s）",
         B(f"ΔL* ≈ {K(BE5)}（UFS 5.0，流 15 GB 约 {T_STREAM5:.2f} s）")],
        ["6.4.2.1 驻留", "固定 pin 50% 的层（7.5 GB）→ ~1.25K",
         "动态驻留：任务内按层序预取、任务后回收；ΔL* = (W − C) ÷ (B·t_tok)"],
        ["6.4.2.2 MoE", "「MoE 下收益最大」（专家 cache）",
         f"流式 prefill 中负收益：ΔL = 100 时某专家未被选中仅 {c.expert_untouched(100):.2%}；30B-A3B 平衡点 {K(be_moe, 1)}"],
        [B("6.4.4 能耗", k.RED), "按 ~0.3 pJ/op：计算是搬运的 5–10 倍",
         B(f"UFS 路径搬运 ≈ 计算，能耗平衡点 {K(DLE, 1)}；权重在 DRAM 时计算是搬运的 {E_COMP_MID / E_MOVE_MID:.1f} 倍", k.RED)],
        ["6.4.5 散热", "NPU ~4 W + UFS ~0.9 W ≈ 4.9 W",
         f"NPU ~4 W + UFS {p_ufs:.2f} W（ΔL = 4K）≈ {c.P_NPU + p_ufs:.1f} W"],
        ["6.7 路由代价", "3.75 s vs 0.3 s，差一个数量级",
         f"{T_STREAM5:.2f} s vs {T_LOCAL:.3f} s，约 {round(ROUTE_X, -1):.0f} 倍"],
        ["4.3 原语", "各原语给五坐标，无负载实例表",
         "2029 负载基线 + 各原语负载实例表（今天实测只作锚点）；8 处表述修订"],
        ["文字订正", "—",
         f"5.2.2 桥剩下的价值 = 能力优势 + 压缩格式下省端侧算力与能耗；F 类能耗 {F_LO / 1e3:.2f}–{F_HI / 1e3:.1f} kJ"],
    ], col_w=[1.1, 2.55, 3.38], s=9, first_col_bold=True, hl_rows=(2, 7))
    k.notes(s, "v3.2 列取自根目录 v3.2 润色版原文；v3.4 列由 calc.py 按当前参数基线计算。"
               "两处翻转（红色）都来自算力比带宽涨得快。")

def build(prs):
    for fn in (slide_6_5_6, slide_6_7, slide_ch7_1_3, slide_ch7_4_6, slide_app_a_b, slide_app_b, slide_refs,
               slide_app_c, slide_app_d):
        fn(prs)

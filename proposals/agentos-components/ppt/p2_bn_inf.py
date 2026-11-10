"""第二部分 · 瓶颈分析：推理服务（报告 2.5.1，2026-11-09 改版）。版式：solution.problem-arch-callouts。
中央架构图在本模块自绘；两侧问题卡、扫描卡、连线、底部通栏与编号用 pages.bn_* 部件。
左侧连线须穿过层名之间的空隙：各层高度与目标位置按此取值，改动时一并核对。"""

import lib
from lib import box, text
from pages import BN_Y0, bn_badges, bn_bottom, bn_layer, bn_sep, bn_side
from registry import page


@page
def bottleneck_inference(prs):
    s = lib.new_slide(prs, "推理服务瓶颈分析：", "长上下文推不动，带宽墙推不开，模型结构与手机不匹配",
                      crumb="二、场景与负载瓶颈 › 瓶颈分析 › 推理服务")

    # ---------------- 中央：当前端侧推理架构
    y = BN_Y0
    x1, wfull = bn_layer(s, y, 80, "负载")
    box(s, (x1, y + 4, 200, 32), "T3 长程任务：上下文 23–32K", fill="peach_m")
    text(s, (x1 + 208, y + 2, wfull - 208, 36), "!!每轮追加 0.5–2K 工具返回!!\n!!MoE 底座：未命中每 token 约 1.1GB!!",
         style="detail", valign="middle", check=False)
    bw = (wfull - 3 * 6) / 4
    for i, (t, f) in enumerate([("T1、T5 前台", "peach_l"), ("T2 跨应用事务", "blue_l"), ("T3 长程任务", "blue_l"),
                                ("T4 后台分拣", "green_l")]):
        box(s, (x1 + i * (bw + 6), y + 44, bw, 32), t, fill=f)
    bn_sep(s, y + 84)

    y = BN_Y0 + 88
    bn_layer(s, y, 112, "接口")
    w3 = (wfull - 12) / 3
    for i, t in enumerate(["**AICore**（Android）\nPrompt API 窗口约 4K",
                           "**Foundation Models**（iOS）\n示例窗口 8K",
                           "**NNRt**（HarmonyOS）\n仅支持同步推理"]):
        box(s, (x1 + i * (w3 + 6), y + 4, w3, 60), t, fill="blue_l")
    window = (x1, y + 70, 218, 38)
    box(s, window, "长上下文超出窗口\n追加后整段重算", fill="pink_l", line="red", dash=True, line_width=1.5)
    box(s, (x1 + 226, y + 70, wfull - 226, 38), "前缀缓存为应用私有\n（见内存与资源）", fill="beige")
    bn_sep(s, y + 116)

    y = BN_Y0 + 208
    bn_layer(s, y, 96, "模型")
    box(s, (x1, y + 4, 218, 88), "**底座模型**（系统托管）\n基线为稠密 3B\n2027 年上 MoE 底座", fill="beige")
    model = (x1 + 226, y + 4, wfull - 226, 40)
    box(s, model, "**每 token KV**：Qwen3-4B 144KiB\nLFM2-1.2B 12KiB，差 12 倍", fill="pink_l")
    box(s, (x1 + 226, y + 52, wfull - 226, 40), "**MoE 专家**：放在闪存\n逐 token 路由，未命中即读闪存", fill="peach_l")
    bn_sep(s, y + 100)

    y = BN_Y0 + 312
    bn_layer(s, y, 88, "计算")
    compute = (x1, y + 4, 218, 80)
    box(s, compute, "**NPU、GPU、CPU**\n共享同一份 LPDDR 带宽\nNPU 静态图，实测最长 1K token", fill="blue_l")
    box(s, (x1 + 226, y + 4, wfull - 226, 36), "会话级调度与抢占（其他团队）", fill="grey_m")
    box(s, (x1 + 226, y + 48, wfull - 226, 36), "PIM：没有系统支持\n主流推理框架都不支持", fill="pink_l")
    bn_sep(s, y + 92)

    y = BN_Y0 + 408
    bn_layer(s, y, 52, "存储")
    lp = 236
    box(s, (x1, y + 6, lp, 40), "LPDDR5X 峰值约 77GB/s\n24K decode 需约 95GB/s", fill="grey_m")
    ufs = (x1 + lp + 6, y + 6, wfull - lp - 6, 40)
    box(s, ufs, "UFS 4.x 约 4.3GB/s\n没有计算接口", fill="purple_l")

    targets = {
        "window": (window[0] + 4, window[1] + 4), "compute": (compute[0] + 4, compute[1] + 4),
        "model": (model[0] + model[2] - 4, model[1] + 4), "ufs": (ufs[0] + 4, ufs[1] + 2),
    }

    # ---------------- 两侧问题卡与业界技术扫描卡
    bn_side(s, "left", [
        ("callout", "①", "长上下文推不动：窗口 4–8K，公开手机实测最长 1K token；追加后整段重算", 86,
         "window"),
        ("card", "llm.npu", "ASPLOS 2025 · 学术",
         "手机 NPU prefill 首次超过 1000 token/秒，按 256 token 固定分块", "最长只测到 1024 token", 120),
        ("callout", "②", "带宽墙推不开：decode 占 LPDDR5X 峰值约 68%，24K 时超过峰值；NPU 与 GPU 争同一带宽", 86,
         "compute"),
        ("card", "三星 LPDDR5X-PIM", "Hot Chips 2026 · 厂商自报",
         "内部带宽 614GB/s，约为外部 8 倍；8B decode 提升 3.01 倍", "只测 320 token、INT4；标准未发布", 120),
        ("card", "HeteroInfer", "SOSP 2025 · 学术",
         "手机 GPU 与 NPU 按张量切分协同，端到端 1.34–6.02 倍；与游戏并发时 prefill 仅降 0.5%–2.2%",
         "未覆盖长上下文与 PIM", 140),
    ], targets)
    bn_side(s, "right", [
        ("callout", "③", "模型结构与手机不匹配：每 token KV 相差可达 12 倍；MoE 照搬全注意力，24K 的 KV 达 2.25GiB", 86, "model"),
        ("card", "LFM2", "2025-11 · Liquid AI",
         "以手机 CPU 的首 token、decode 时延与峰值内存为约束搜索结构，收敛到短卷积加少量注意力，每 token KV 12KiB",
         "只有 CPU 在环，没有 NPU 实测", 140),
        ("card", "AFM 3 Core Advanced", "2026-06 · Apple",
         "20B 稀疏模型，完整权重放在闪存，每个请求换入 1–4B 激活参数", "仅用于 Apple 自有模型运行时", 120),
        ("card", "Cambricon-LLM", "MICRO 2024 · 学术",
         "权重 GEMV 在闪存侧完成，只回传结果向量；7B 约 36 token/秒（自报仿真）", "需定制 NAND，UFS 没有计算接口", 132),
    ], targets)
    bn_bottom(s, "④", "MoE 专家换入受闪存带宽限制：命中率 0% 时每 token 约读 1.1GB，UFS 4.x 下仅约 3.9 token/秒", targets["ufs"],
              "@@超长序列推理@@（对应 ①）、@@异构融合计算@@（对应 ②④）、@@硬件亲和模型寻优@@（对应 ③）；专家命中率由推理服务内存管理负责")
    bn_badges(s, targets, [("1", "window"), ("2", "compute"), ("3", "model"), ("4", "ufs")])

    lib.footnote(s, "来源：报告 2.2.2 负载估算、2.5.1 瓶颈分析；llm.npu、HeteroInfer、三星 LPDDR5X-PIM、Cambricon-LLM、LFM2 见参考资料 "
                    "W21–W26；KV 体积与带宽账为估算，见调研笔记 R1、R4。", y=694)

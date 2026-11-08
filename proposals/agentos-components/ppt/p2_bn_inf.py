"""第二部分 · 瓶颈分析：推理服务（报告 2.4.1）。版式：solution.problem-arch-callouts。
中央架构图在本模块自绘；两侧问题卡、扫描卡、连线、底部通栏与编号用 pages.bn_* 部件。
左侧连线须穿过层名之间的空隙：各层高度与目标位置按此取值，改动时一并核对。"""

import lib
from lib import box, text
from pages import BN_Y0, bn_badges, bn_bottom, bn_layer, bn_sep, bn_side
from registry import page


@page
def bottleneck_inference(prs):
    s = lib.new_slide(prs, "推理服务瓶颈分析：", "抢占粒度为模型级，前缀缓存为应用私有，长会话缺少状态契约",
                      crumb="二、场景与负载瓶颈 › 瓶颈分析 › 推理服务")

    # ---------------- 中央：当前端侧推理架构（Android / iOS / HarmonyOS）
    y = BN_Y0
    x1, wfull = bn_layer(s, y, 80, "负载")
    box(s, (x1, y + 4, 200, 32), "前台：首 token ≤1 秒", fill="peach_m")
    text(s, (x1 + 208, y + 2, wfull - 208, 36), "!!后台分拣：每天约 100 条事件!!\n!!记忆写入：每天约 4–9 万 prefill!!",
         style="detail", valign="middle", check=False)
    bw = (wfull - 3 * 6) / 4
    for i, (t, f) in enumerate([("T1、T5 前台", "peach_l"), ("T2 跨应用事务", "blue_l"), ("T3 长程任务", "blue_l"),
                                ("T4 后台分拣", "green_l")]):
        box(s, (x1 + i * (bw + 6), y + 44, bw, 32), t, fill=f)
    bn_sep(s, y + 84)

    y = BN_Y0 + 88
    bn_layer(s, y, 112, "接口")
    w3 = (wfull - 12) / 3
    for i, t in enumerate(["**AICore**（Android）\n仅前台推理\n配额与「忙」返回",
                           "**Foundation Models**（iOS）\n调度与抢占策略未公开",
                           "**NNRt**（HarmonyOS）\n仅支持同步推理"]):
        box(s, (x1 + i * (w3 + 6), y + 4, w3, 60), t, fill="blue_l")
    prefix = (x1, y + 70, 218, 38)
    box(s, prefix, "前缀缓存：存于应用私有存储\n不跨应用共享", fill="pink_l", line="red", dash=True, line_width=1.5)
    box(s, (x1 + 226, y + 70, wfull - 226, 38), "上下文窗口：约 4K（Android）\n8K（Apple 示例）", fill="beige")
    bn_sep(s, y + 116)

    y = BN_Y0 + 208
    bn_layer(s, y, 96, "模型")
    box(s, (x1, y + 4, 218, 88), "**底座模型**（系统托管）\n单底座服务多个应用\nLiteRT、Core AI 等运行时",
        fill="beige")
    kv = (x1 + 226, y + 4, wfull - 226, 40)
    box(s, kv, "**会话 KV**：按会话保存\n无停放、换出与恢复接口", fill="pink_l")
    adapter = (x1 + 226, y + 52, wfull - 226, 40)
    box(s, adapter, "**适配器**：约 160MB\n绑定单一底座版本", fill="peach_l")
    bn_sep(s, y + 100)

    y = BN_Y0 + 312
    bn_layer(s, y, 88, "调度")
    npu_mgr = (x1, y + 4, 218, 80)
    box(s, npu_mgr, "**NPU Manager**（Android 17）\n模型加载准入、三档优先级\n抢占方式：要求客户端卸载模型",
        fill="blue_l")
    box(s, (x1 + 226, y + 4, wfull - 226, 36), "准入：前台限制、配额、「忙」返回", fill="beige")
    box(s, (x1 + 226, y + 48, wfull - 226, 36), "卸载代价：重载 0.4–1.7 秒\nKV 随之丢失，重建 6–14 秒", fill="pink_l")
    bn_sep(s, y + 92)

    y = BN_Y0 + 408
    bn_layer(s, y, 52, "硬件")
    hw = 86
    for i, t in enumerate(["NPU", "GPU", "CPU"]):
        box(s, (x1 + i * (hw + 6), y + 6, hw, 40), t, fill="grey_m")
    cloud = (x1 + 3 * (hw + 6), y + 6, wfull - 3 * (hw + 6), 40)
    box(s, cloud, "云端私有计算\n路由规则不透明", fill="purple_l")

    targets = {
        "prefix": (prefix[0] + 4, prefix[1] + 4), "npu": (npu_mgr[0] + 4, npu_mgr[1] + 4),
        "kv": (kv[0] + kv[2] - 4, kv[1] + 4), "adapter": (adapter[0] + adapter[2] - 4, adapter[1] + 4),
        "cloud": (cloud[0] + 4, cloud[1] + 2),
    }

    # ---------------- 两侧问题卡与业界技术扫描卡
    bn_side(s, "left", [
        ("callout", "②", "前缀缓存为应用私有：约 2K 共享前缀被反复重算，复用与否全天 prefill 相差 7–10 倍", 86, "prefix"),
        ("card", "vLLM / SGLang 前缀缓存", "2023–2024 · 开源云端引擎",
         "PagedAttention 按块管理 KV，RadixAttention 以前缀树在请求间共享前缀", "服务器引擎，不是端侧系统服务", 120),
        ("callout", "①", "抢占粒度为模型级：后台推理请求被拒绝；放开后只能卸载整个模型，KV 随之丢失", 86, "npu"),
        ("card", "Android 17 NPU Manager", "2026-06 · Google AOSP",
         "系统服务统一 NPU 模型加载准入，分三档优先级，资源紧张时要求客户端卸载模型", "粒度为模型，仅覆盖 NPU", 120),
        ("card", "Agent.xpu", "2025-06 · 北京大学",
         "NPU 与集成 GPU 协同，区分前台响应式与后台主动式任务，算子级抢占，前台时延降低至少 91%（作者自报）",
         "学术原型，尚未进入商用系统", 140),
    ], targets)
    bn_side(s, "right", [
        ("callout", "③", "长会话缺少状态契约：上下文达到 23–32K，超出接口窗口；KV 没有停放与恢复接口", 86, "kv"),
        ("card", "LLMS", "2024-03 · 北京大学",
         "将 LLM 作为移动系统服务，KV 跨调用持久，分块压缩并换入换出，上下文切换时延最多降低两个数量级（作者自报）",
         "学术原型，不做算力抢占", 140),
        ("callout", "④", "适配器绑定底座版本：底座升级后，生态中的适配器集体失效", 86, "adapter"),
        ("card", "vLLM 多 LoRA 服务", "vLLM 官方文档",
         "同一底座并发服务多个 LoRA 适配器，提供运行时加载与卸载接口", "官方提示运行时加载仅限可信环境", 120),
        ("card", "Hybrid LLM / RouteLLM", "ICLR 2024 / ICLR 2025 · 学术",
         "Hybrid LLM 按预测难度选择大小模型，大模型调用最多减少 40% 且质量不降；RouteLLM 成本降低超过 2 倍",
         "只考虑质量与成本，不含隐私与能耗", 132),
    ], targets)
    bn_bottom(s, "⑤", "端云路由缺少隐私约束：由开发者选择或厂商内部决定且不透明，不按数据标签判定能否出端", targets["cloud"],
              "@@会话级调度与抢占@@（对应 ①）、@@KV / 前缀复用与多适配器驻留@@（对应 ②③④）、@@端云协同路由@@（对应 ⑤）")
    bn_badges(s, targets, [("1", "npu"), ("2", "prefix"), ("3", "kv"), ("4", "adapter"), ("5", "cloud")])

    lib.footnote(s, "来源：报告 2.2.2 负载估算、2.4.1 瓶颈分析、1.2.1 原型对比；P-C1 原型对比笔记；NPU Manager 见证据库 C1 [K1]，"
                    "Agent.xpu 见 [A26b]，LLMS 见 [P1]。", y=694)

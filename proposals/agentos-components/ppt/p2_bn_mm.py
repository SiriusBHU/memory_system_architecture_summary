"""第二部分 · 瓶颈分析：内存管理（报告 2.4.4）。版式：solution.problem-arch-callouts。
中央架构图在本模块自绘；两侧问题卡、扫描卡、连线、底部通栏与编号用 pages.bn_* 部件。"""

import lib
from lib import box, text
from pages import BN_Y0, bn_badges, bn_bottom, bn_layer, bn_sep, bn_side
from registry import page


@page
def bottleneck_memory(prs):
    s = lib.new_slide(prs, "内存管理瓶颈分析：", "模型内存未纳入记账，回收缺乏 KV 语义，分档机制缺少保底",
                      crumb="二、场景与负载瓶颈 › 瓶颈分析 › 内存管理")

    # ---------------- 中央：当前端侧内存管理架构（以 Android 为例）
    y = BN_Y0
    x1, wfull = bn_layer(s, y, 80, "负载")
    box(s, (x1, y + 4, 196, 32), "前台重负载应用 1.5–3GB", fill="peach_m")
    text(s, (x1 + 204, y + 2, wfull - 204, 36), "!!晚间峰值：Agent 侧需 5.2GB!!\n!!可用约 4.0GB，缺口约 1.2GB!!",
         style="detail", valign="middle", check=False)
    bw = (wfull - 3 * 6) / 4
    for i, (t, f) in enumerate([("T3 主任务", "blue_l"), ("T3 子任务", "blue_l"), ("T4 后台分拣", "green_l"),
                                ("T2、T5 停放", "grey_m")]):
        box(s, (x1 + i * (bw + 6), y + 44, bw, 32), t, fill=f)
    bn_sep(s, y + 84)

    y = BN_Y0 + 88
    bn_layer(s, y, 136, "服务")
    lib.outline(s, (x1, y + 2, 296, 132), line="grey_d", width=1.0, kind="rounded", radius=8)
    text(s, (x1 + 6, y + 4, 284, 20), "**推理服务**（共享底座，单一进程代持全部会话）", style="detail", align="center",
         check=False)
    iw = (296 - 8 * 3) / 2
    cells = [("KV cache 1.3GB\n3–4 个会话", "pink_l"), ("模型权重 1.7GB", "beige"),
             ("运行时缓冲 0.6GB", "purple_l"), ("LoRA 与小模型 0.6GB", "beige")]
    pos = []
    for i, (t, f) in enumerate(cells):
        r, c = divmod(i, 2)
        b = (x1 + 8 + c * (iw + 8), y + 28 + r * 52, iw, 44)
        box(s, b, t, fill=f)
        pos.append(b)
    sx = x1 + 306
    box(s, (sx, y + 6, x1 + wfull - sx, 58), "执行沙箱 0.6GB\n空闲实例可冻结", fill="blue_l")
    box(s, (sx, y + 74, x1 + wfull - sx, 58), "记忆服务 0.4GB\n嵌入模型与索引", fill="green_l")
    bn_sep(s, y + 140)

    y = BN_Y0 + 232
    bn_layer(s, y, 132, "OS")
    memcg = (x1, y + 4, 214, 76)
    lmkd = (x1 + 222, y + 4, wfull - 222, 76)
    box(s, memcg, "**memcg（Memory Limiter）**\n每进程 high = 4096MiB\n仅统计匿名页与 swap", fill="blue_l")
    box(s, lmkd, "**LMKD**\n按 oom_adj 优先级终止进程\n不具备会话与 KV 语义", fill="pink_l")
    box(s, (x1, y + 86, 214, 42), "zRAM：压缩匿名页，不区分语义", fill="beige")
    box(s, (x1 + 222, y + 86, wfull - 222, 42), "PSI：仅反映匿名页与文件页压力", fill="beige")
    bn_sep(s, y + 134)

    y = BN_Y0 + 370
    bn_layer(s, y, 50, "内存")
    w3 = (wfull - 12) / 3
    box(s, (x1, y + 4, w3, 42), "匿名页（已记账）", fill="blue_l")
    box(s, (x1 + w3 + 6, y + 4, w3, 42), "文件页（权重映射）", fill="peach_l")
    dma = (x1 + 2 * (w3 + 6), y + 4, w3, 42)
    box(s, dma, "dma-buf / NPU 缓冲\n未纳入记账", fill="purple_l", line="red", dash=True, line_width=1.5)
    bn_sep(s, y + 52)

    y = BN_Y0 + 424
    bn_layer(s, y, 46, "硬件")
    box(s, (x1, y + 4, 232, 38), "LPDDR 12GB，Agent 可用约 4GB", fill="grey_m")
    ufs = (x1 + 240, y + 4, wfull - 240, 38)
    box(s, ufs, "UFS 4.x，顺序读约 4.3GB/s", fill="grey_m")
    lib.arrow(s, (x1 + 150, BN_Y0 + 222), (x1 + 100, BN_Y0 + 236), color="grey_d", width=1.0)

    kv = pos[0]
    targets = {
        "dma": (dma[0] + dma[2] + 2, dma[1] - 4), "kv": (kv[0] + 4, kv[1] + 4), "lmkd": (lmkd[0] + lmkd[2] - 4, lmkd[1] + 4),
        "memcg": (memcg[0] + 4, memcg[1] + 4), "ufs": (ufs[0] + 4, ufs[1] + 2),
    }

    # ---------------- 两侧问题卡与业界技术扫描卡
    bn_side(s, "left", [
        ("callout", "②", "共享服务代持内存的归属错误：多个会话的 KV 均计入推理服务进程，导致其触及限额或被整体回收", 86, "kv"),
        ("card", "dma-buf memcg 计费 RFC", "2026-05 · Linux 社区",
         "分配时将 dma-buf 计入客户端 cgroup，用于解决共享服务代分配内存的归属", "尚未合入主线", 124),
        ("callout", "④", "分档机制仅有上限、缺少保底：仅按可见与不可见分档，无法保障用户正在等待的会话", 86, "memcg"),
        ("card", "memcg memory.min / low", "Linux 主线", "按 cgroup 提供硬保底与软保护，回收时优先保护设有保底的分组",
         "手机上尚无按会话的保护策略", 120),
        ("card", "AFM 3 权重分层", "2026-06 · Apple",
         "20B 稀疏模型完整存放于 NAND，每次请求换入 1–4B 专家，规避逐 token 的随机小块读取", "仅用于 Apple 自有模型运行时", 142),
    ], targets)
    bn_side(s, "right", [
        ("callout", "①", "模型内存未纳入统一记账：权重和 KV 驻留在 dma-buf 与 NPU 缓冲中，不在 memcg 统计范围内", 86, "dma"),
        ("card", "dmem cgroup", "2025 · Linux 6.14 合入", "将设备显存纳入 cgroup 记账与限额", "面向独立显存，不适用于统一内存", 104),
        ("callout", "③", "回收以进程为单位，缺乏 KV 语义：KV 换出恢复需 0.2–0.9 秒，重算需 6–14 秒，LMKD 只能终止进程", 86, "lmkd"),
        ("card", "LLMS", "2024-03 · 学术",
         "将 LLM 作为系统服务，对 KV 分块压缩、换出并与重算流水，上下文切换时延降低约两个数量级（作者自报）", "尚未进入商用操作系统", 140),
        ("card", "vLLM PagedAttention", "2023 · UC Berkeley", "KV 按定长块管理，支持前缀共享与按块淘汰",
         "服务器单租户引擎，不涉及 OS 级记账", 120),
    ], targets)
    bn_bottom(s, "⑤", "模型加载 IO 与应用冷启动争用闪存：1.7GB 权重冷加载需 0.4–1.7 秒，专家换入同样占用读带宽", targets["ufs"],
              "分为@@通用内存管理@@（对应 ①②④⑤）与@@模型内存管理@@（对应 ③⑤）两个模块，共六项关键技术")
    bn_badges(s, targets, [("1", "dma"), ("2", "kv"), ("3", "lmkd"), ("4", "memcg"), ("5", "ufs")])

    lib.footnote(s, "来源：报告 2.2.5 负载估算、2.4.4 瓶颈分析；P-C4 原型对比笔记；Android 17 Memory Limiter 见参考资料 W16。", y=694)

"""第二部分 · 当代操作系统的能力缺口（报告 2.4）：三项系统服务 × Android / iOS / HarmonyOS 矩阵，另列三家均不具备的能力。"""

from lib import footnote, new_slide, outline, table, table_height, text
from registry import page

CRUMB = "二、场景与负载瓶颈"


@page
def os_gap(prs):
    s = new_slide(prs, "当代操作系统的能力缺口：", "推理服务不足、执行与沙箱缺失、内存与资源不足",
                  crumb=CRUMB + " › 能力缺口",
                  takeaway="根本缺口：三个平台都没有把 Agent 会话作为系统对象，记账、隔离、回收与授权仍以进程或 App 为主体")
    cols = ["系统服务与结论\n~~可用 / 不足 / 缺失~~", "Android（Google）", "iOS（Apple）", "HarmonyOS（华为）", "三家均不具备的能力"]
    rows = [
        ["**推理服务**\n!!不足!!\n已有系统级共享模型服务；长上下文、新算力、模型与硬件匹配都缺",
         "**已有**：AICore 托管 Gemini Nano，单底座服务多个应用；Android 17 NPU Manager 提供加载准入与卸载式抢占\n"
         "!!不足!!：输入窗口约 4000 token；只允许前台推理；前缀缓存不跨应用",
         "**已有**：Foundation Models 框架向第三方开放端侧模型；AFM 3 稀疏权重放在闪存\n"
         "!!不足!!：上下文示例值 8192 token；第三方适配器绑定底座版本",
         "**已有**：小艺作为底座\n"
         "!!不足!!：第三方 API 与配额没有文档；NPU 接口 NNRt 只支持同步推理",
         "长上下文的增量 prefill；NPU、PIM 等新算力的统一分派与带宽仲裁；按手机内存与闪存预算约束模型结构\n"
         "~~会话级调度同样缺失，由其他团队推进~~"],
        ["**执行与沙箱**\n!!缺失!!\nApp 级沙箱成熟，Agent 会话级执行边界与按调用判定不存在",
         "**已有**：UID 沙箱、SELinux、seccomp；isolatedProcess；AVF / pKVM（机型受限）；AppFunctions 以静态权限放行；"
         "Computer Control 预览\n"
         "!!缺失!!：按会话的出口策略；会话快照",
         "**已有**：App 沙箱 + 扩展，App Intents 由 Siri 编排；权限为静态，意图按次确认\n"
         "!!缺失!!：第三方没有比 App 更细的边界",
         "**已有**：应用沙箱 + 访问令牌（APL 三级）；意图框架；转账、支付由系统阻断（媒体报道）\n"
         "!!缺失!!：「动态沙箱」没有官方文档",
         "把隔离、出口策略、凭证托管、快照打包成会话对象的那一层；MCP 出站与 A2A 入站的按调用判定；数据标签；"
         "预演（dry-run）与撤销（undo）"],
        ["**内存与资源**\n!!不足!!\n为匿名页设计的机制成熟，模型内存未纳入记账",
         "**已有**：LMKD + memcg、zRAM；MGLRU（荣耀约 7000 万台）；Android 17 Memory Limiter 默认每进程限额，按可见 / 不可见分档\n"
         "!!不足!!：只计匿名页与 swap；仅有上限、缺少保底",
         "**已有**：Jetsam 按优先级带回收，单进程上限（12GB 机型约 6144MB，开发者实测）；内存压缩\n"
         "!!不足!!：AFM 3 的权重分层只在 Apple 自有运行时内",
         "**已有**：应用自愿释放回调、Purgeable 内存；OpenHarmony 文档有压缩换出（ESwap）\n"
         "!!不足!!：模型内存的记账与回收未见公开机制",
         "模型内存的统一记账与代分配归账；跨应用、带版本的前缀缓存；懂 KV 语义的分层回收；MoE 专家缓存；按会话档位的保底\n"
         "~~Linux 主线：dmem 不适用于统一内存；dma-buf 计费仍为 RFC~~"],
    ]
    ratios = [0.62, 1.3, 1.08, 0.98, 1.04]
    th = table_height(1216, cols, rows, ratios, style="body", pad=(6, 3))
    st = "body" if 124 + th * 1.04 + 8 < 600 else "detail"
    th = table_height(1216, cols, rows, ratios, style=st, pad=(6, 12))
    table(s, (32, 124, 1216, th), cols, rows, widths=ratios, style=st, pad=(6, 12), hot_col=4,
          align=["left"] * 5, fills={(0, 4): "peach_l"}, first_bold=False, fit=False)
    y = 124 + th * 1.04 + 8
    h = 686 - y
    outline(s, (32, y, 1216, h), line="grey_line")
    text(s, (40, y, 64, h), "判断", style="label_big", align="center", valign="middle", check=False)
    text(s, (112, y + 3, 1128, h - 6),
         "- @@推理服务@@：「谁能用」已经解决；长上下文推不动、新算力用不上、模型结构与手机不匹配没有解决\n"
         "- @@执行与沙箱@@：边界仍停留在 App 级，判定不了单次调用；@@内存与资源@@：为匿名页设计的机制成熟，模型内存未纳入记账\n"
         "- 记忆属于 Agent 层，各家都随助手提供，不列入系统服务的缺口",
         style="body", gap_pt=2, valign="middle")
    footnote(s, "来源：报告 2.4；各项事实的出处见 1.1.3 业界进展表、原型对比表（notes/P-C1、P-C2、P-C4）与证据库 C1、C2、C4。"
                "iOS 单进程上限为开发者实测；HarmonyOS 支付阻断为媒体报道。", y=694, w=1120)

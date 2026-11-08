"""第二部分 · 当代操作系统的能力缺口（报告 2.3）：四组件 × Android / iOS / HarmonyOS 矩阵，另列三家均不具备的能力。"""

from lib import footnote, new_slide, outline, table, table_height, text
from registry import page

CRUMB = "二、场景与负载瓶颈"


@page
def os_gap(prs):
    s = new_slide(prs, "当代操作系统的能力缺口：", "推理服务不足、执行沙箱缺失、记忆治理缺失、内存管理不足",
                  crumb=CRUMB + " › 能力缺口",
                  takeaway="根本缺口：三个平台都没有把 Agent 会话作为系统对象，记账、隔离、回收与授权仍以进程或 App 为主体")
    cols = ["组件与结论\n~~可用 / 不足 / 缺失~~", "Android（Google）", "iOS（Apple）", "HarmonyOS（华为）", "三家均不具备的能力"]
    rows = [
        ["**推理服务**\n!!不足!!\n已有系统级共享模型服务，调度只到模型级",
         "**已有**：AICore 托管 Gemini Nano，单底座服务多个应用；Android 17 NPU Manager 提供加载准入、三档优先级、卸载式抢占\n"
         "!!不足!!：只允许前台应用推理；并发请求返回「忙」不排队；前缀缓存不跨应用；输入窗口约 4000 token",
         "**已有**：Foundation Models 框架向第三方开放端侧模型\n"
         "!!不足!!：调度与抢占策略不公开；第三方适配器约 160MB，绑定底座版本，升级须重训；上下文示例值 8192 token",
         "**已有**：小艺作为底座\n"
         "!!不足!!：第三方 API 与配额没有文档；NPU 接口 NNRt 只支持同步推理",
         "会话级调度：谁先用、用多少、能否被打断、打断后状态能否保留；跨应用的前缀与 KV 复用"],
        ["**执行沙箱**\n!!缺失!!\nApp 级沙箱成熟，Agent 会话级执行边界不存在",
         "**已有**：UID 沙箱、SELinux、seccomp；isolatedProcess；AVF / pKVM 虚拟机隔离（机型受限，未作为通用接口开放）；"
         "AppFunctions 以静态权限放行\n"
         "!!缺失!!：按会话的出口策略；会话快照",
         "**已有**：App 沙箱 + 扩展，App Intents 由 Siri 编排；权限与 entitlement 为静态，意图按次确认\n"
         "!!缺失!!：第三方没有比 App 更细的边界",
         "**已有**：应用沙箱 + 访问令牌（APL 三级）；意图框架；转账、支付由系统阻断（媒体报道）\n"
         "!!缺失!!：「动态沙箱」没有官方文档",
         "把隔离、出口策略、凭证托管、快照打包成会话对象的那一层；按调用参数与会话历史的有状态策略；数据标签；"
         "预演（dry-run）与撤销（undo）"],
        ["**记忆服务**\n!!索引不足，治理缺失!!\n系统级索引不向第三方开放，治理能力空白",
         "**已有**：Magic Cue（端侧 Nano + 云端增强）；Gemini 个人上下文\n"
         "!!不足!!：个人上下文读取云账户数据，限 Google 自家应用；应用级连接授权，默认关闭",
         "**已有**：端侧语义索引；第三方可经 App Intents 实体贡献数据\n"
         "!!不足!!：读取侧没有公开说明",
         "**已有**：小艺记忆存卡证、地址、订单\n"
         "!!不足!!：跨应用数据通路（UDMF、Picker）只到数据层，没有语义层",
         "写入的来源与完整性标签；遗忘与生命周期；冲突更新；向第三方 Agent 开放、按查询授权的读取通道\n"
         "~~抽取、合并只存在于云端或应用内框架~~"],
        ["**内存管理**\n!!不足!!\n为匿名页设计的机制成熟，模型内存未纳入记账",
         "**已有**：LMKD + memcg、zRAM；MGLRU（荣耀约 7000 万台）；Android 17 Memory Limiter 默认每进程限额，按可见 / 不可见分档\n"
         "!!不足!!：只计匿名页与 swap，dma-buf、GPU 是否计入未说明；仅有上限、缺少保底",
         "**已有**：Jetsam 按优先级带回收，单进程上限（12GB 机型约 6144MB，开发者实测）；内存压缩；可申请提高上限\n"
         "!!不足!!：AFM 3 的权重分层只在 Apple 自有运行时内",
         "**已有**：应用自愿释放回调、Purgeable 内存；OpenHarmony 文档有压缩换出（ESwap）\n"
         "!!不足!!：模型内存的记账与回收未见公开机制",
         "模型内存的统一记账；共享服务代分配内存的归账；懂 KV 语义的回收（换出、重算、降位宽）；按会话档位的保底与回收顺序\n"
         "~~Linux 主线：dmem 不适用于统一内存；dma-buf 计费仍为 RFC~~"],
    ]
    ratios = [0.6, 1.3, 1.08, 0.98, 1.04]
    th = table_height(1216, cols, rows, ratios, style="detail", pad=(6, 2))
    table(s, (32, 124, 1216, th), cols, rows, widths=ratios, style="detail", pad=(6, 2), hot_col=4,
          align=["left"] * 5, fills={(0, 4): "peach_l"}, first_bold=False, fit=False)
    y = 124 + th * 1.04 + 8
    h = 686 - y
    outline(s, (32, y, 1216, h), line="grey_line")
    text(s, (40, y, 64, h), "判断", style="label_big", align="center", valign="middle", check=False)
    text(s, (112, y + 3, 1128, h - 6),
         "- @@推理服务@@：「谁能用」已经解决，「谁先用、用多少、能否被打断、打断后状态能否保留」没有解决\n"
         "- @@执行沙箱与记忆服务@@：边界仍停留在 App 级；@@内存管理@@：为匿名页设计的机制成熟，模型内存未纳入记账",
         style="body", gap_pt=2, valign="middle")
    footnote(s, "来源：报告 2.3；各项事实的出处见四张原型对比表（notes/P-C1～P-C4）与证据库 C1～C4。iOS 单进程上限为开发者实测；"
                "HarmonyOS 支付阻断为媒体报道；记忆框架指 Mem0、Letta、Zep。", y=694, w=1120)

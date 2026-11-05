"""生成 deck-p2.yaml：六张关键技术立项页（solution.solution-kickoff-difficulties）。"""
import sys
sys.dont_write_bytecode = True
import yaml
from canvas import Canvas

CW, CH = 640, 411
LANES = [(0.0, 203.6), (216.1, 203.6), (432.2, 207.8)]
LANE_H = 330
NODE_X = [8, 224, 440]
NODE_W = [187, 187, 192]
TOP, BOT = 36, 322


def build_arch(name, lanes, links, chains, fb_title, fb_items, fb_note=None):
    c = Canvas(name, size=(CW, CH))
    rows = {}
    for li, (title, nodes) in enumerate(lanes):
        lx, lw = LANES[li]
        c.panel(lx, 0, lw, LANE_H, radius=8)
        c.text(lx + 8, 3, lw - 12, 26, title, style="body_strong", color="primary_text", align="left")
        n = len(nodes)
        gap = 16
        h = min(66, (BOT - TOP - gap * (n - 1)) / n)
        for ri, (kind, text, badge) in enumerate(nodes):
            y = TOP + ri * (h + gap)
            x, w = NODE_X[li], NODE_W[li]
            (c.node if kind == "plain" else getattr(c, kind))(x, round(y, 1), w, round(h, 1), text)
            rows[(li, ri)] = (x, round(y, 1), w, round(h, 1))
            if badge:
                c.badge(x - 6, round(y - 6, 1), badge)
        if li in chains:
            for ri in range(n - 1):
                if (li, ri) in rows and ri in chains[li]:
                    x, y, w, hh = rows[(li, ri)]
                    c.arrow((x + w / 2, y + hh), (x + w / 2, y + hh + gap))
    # 跨分区连线
    used = {}
    for (a, i), (b, j) in links:
        x1, y1, w1, h1 = rows[(a, i)]
        x2, y2, w2, h2 = rows[(b, j)]
        sy, dy = y1 + h1 / 2, y2 + h2 / 2
        if abs(sy - dy) < 0.5:
            c.arrow((x1 + w1, sy), (x2, dy))
        else:
            k = used.get(a, 0)
            used[a] = k + 1
            mid = [200, 206, 212, 218][k % 4] if a == 0 else [416, 422, 428, 434][k % 4]
            c.arrow((x1 + w1, sy), (mid, sy), (mid, dy), (x2, dy))
    # 反馈
    fy = 346
    c.panel(0, fy, CW, 62, radius=8)
    c.text(8, fy + 2, 120, 22, fb_title, style="body_strong", color="primary_text", align="left")
    if fb_note:
        c.text(110, fy + 2, 524, 22, fb_note, style="caption", color="accent", bold=True, align="right")
    n = len(fb_items)
    w = (CW - 16 - 8 * (n - 1)) / n
    for k, t in enumerate(fb_items):
        c.node(8 + k * (w + 8), fy + 26, round(w, 1), 30, t, style="detail")
    c.arrow((536, LANE_H), (536, fy))
    c.arrow((101, fy), (101, LANE_H), color="accent")
    if c.warnings:
        print("\n".join(c.warnings))
    return c.data()


def ms(*pairs):
    return [{"date": d, "deliverable": t} for d, t in pairs]


def P(name, text, **kw):
    d = {"name": name, "text": text}
    d.update(kw)
    return d


pages = []

# ---------------------------------------------------------------- KT1-a
pages.append(dict(
    title="叠加场景.so文件页锁优化：",
    title_suffix="去全局锁加关键页软保护，冷启动降15%～30%",
    challenges=[
        dict(name="锁竞争拖慢缺页", text="多进程缺页，rmap锁等待超300ms"),
        dict(name="冷启动慢", text="GB级应用86.6%冷启动超1秒"),
        dict(name="保护与回收冲突", text="预加载使冷启动次数反增30%"),
    ],
    goal="叠加场景（Agent常驻，内存余量<20%）下降低锁竞争与文件页逐出，",
    goal_highlight="冷启动-15%～-30%",
    arch=build_arch(
        "KT1-a",
        [
            ("感知：缺页与画像", [
                ("out", "冷启动.so访问画像\n各应用各版本", None),
                ("plain", "缺页trace\n共享库多进程缺页", None),
                ("plain", "rmap锁等待时间", None),
                ("plain", "PSI与内存余量", None),
            ]),
            ("决策：页集合与预算", [
                ("core", "关键.so页集合\n按启动画像生成", 2),
                ("plain", "memcg+全局双重预算\n与KT1-c共用账本", 2),
                ("key", "回收跳过与旋转策略", 1),
                ("key", "大folio开关", 3),
            ]),
            ("执行：锁与保护", [
                ("plain", "关键页软保护\n降回收优先级，不mlock", 2),
                ("key", "补全VMA锁覆盖\nI/O型文件缺页", 1),
                ("key", "rmap trylock批处理\n热.so页批量跳过", 1),
                ("plain", "contpte对齐大folio\n失败退回小页", 3),
            ]),
        ],
        links=[((0, 0), (1, 0)), ((0, 2), (1, 2)), ((0, 3), (1, 3)),
               ((1, 0), (2, 0)), ((1, 2), (2, 1)), ((1, 2), (2, 2)), ((1, 3), (2, 3))],
        chains={0: [0], 1: [0]},
        fb_title="反馈",
        fb_items=["冷启动时延", "major fault次数", "rmap锁等待", "关键页refault率"],
        fb_note="异常自动撤销保护",
    ),
    difficulties=[
        dict(name="文件缺页与回收去全局锁", size=6, points=[
            P("难点", "缺页拿folio锁、等I/O，回收拿i_mmap锁，共享库被几十个进程映射"),
            P("缺页提速", "补全I/O型文件缺页的VMA锁覆盖，避开mmap_lock"),
            P("回收降阻", "热.so页trylock批量跳过，不阻塞kswapd，", highlight="共享库页脱离全局锁"),
        ]),
        dict(name="软保护与回收的平衡", size=5, points=[
            P("难点", "保护多了匿名页换出腾不出空间；单独预加载使冷启动次数增30%"),
            P("画像保护", "按启动画像生成关键.so页集合，软保护不用mlock"),
            P("统一预算", "受memcg与全局上限约束，与匿名页换出共账本，", highlight="有预算的软保护"),
        ]),
        dict(name="大folio与碎片的权衡", size=5, points=[
            P("难点", "大folio减缺页与TLB缺失，但要连续物理内存，手机碎片严重"),
            P("热段大页", "仅对关键.so热段请求contpte对齐的folio"),
            P("优雅降级", "分配失败退回小页，", highlight="热段大页冷段小页"),
        ]),
    ],
    milestones=ms(("2027.03.31", "冷启动与锁等待\n基线、原型"),
                  ("2027.06.30", "锁路径优化与软保护\n合入内部版本"),
                  ("2027.09.30", "随版本商用")),
))

# ---------------------------------------------------------------- KT1-b
pages.append(dict(
    title="SPE匿名页冷热识别与预取：",
    title_suffix="自适应稀疏采样加恢复集预取，切回时延降20%～40%",
    challenges=[
        dict(name="换入无预取", text="zram按需换入，切回前台大批缺页"),
        dict(name="热信号不准", text="扫描开销与精度互斥，MGLRU多未启用"),
        dict(name="采样可用性未知", text="手机SPE是否放开无公开资料"),
    ],
    goal="用硬件访问采样识别匿名热页，切回前台前预取，提升叠加场景流畅度，",
    goal_highlight="切回时延-20%～-40%",
    arch=build_arch(
        "KT1-b",
        [
            ("感知：SPE采样", [
                ("out", "arm_spe_pmu采样\n地址、延迟、data source", 1),
                ("plain", "延迟阈值与data source\n过滤，只留DRAM样本", 1),
                ("plain", "映射物理页号\n每memcg热页集合+时间戳", None),
                ("plain", "冷证据：Accessed位\nDAMON、代龄", 2),
            ]),
            ("决策：三态与恢复集", [
                ("key", "三态判定\n热 / 冷候选 / 未知", 2),
                ("key", "采样间隔与开关\n按PSI和前台状态", 1),
                ("core", "恢复集选择\n切后台时记最近热页", 3),
                ("key", "预取触发\n应用切换、唤起事件", 3),
            ]),
            ("执行：批量预取换入", [
                ("out", "热 / 冷标签\n交KT1-c换出使用", None),
                ("key", "批量解压换入zram页\n可用大folio换入", 3),
                ("plain", "恢复集页在LRU中提前\n避免刚换入就被回收", None),
                ("plain", "预取量封顶\n内存余量不足自动减量", 3),
            ]),
        ],
        links=[((0, 2), (1, 0)), ((0, 3), (1, 0)),
               ((1, 0), (2, 0)), ((1, 3), (2, 1)), ((1, 2), (2, 2)), ((1, 3), (2, 3))],
        chains={0: [0, 1], 1: [2]},
        fb_title="反馈",
        fb_items=["预取命中率", "预取浪费率", "重启时延", "采样CPU占用与功耗"],
    ),
    difficulties=[
        dict(name="手机上稀疏采样可用且用得起", size=5, points=[
            P("难点", "SPE可选、固件可关；间隔小耗电，间隔大漏判热页"),
            P("可用性摸底", "逐SoC核查arm_spe_0节点、固件开关与可采样核"),
            P("自适应采样", "仅大核与应用核采样，按PSI和前台状态调间隔，", highlight="自适应稀疏采样"),
        ]),
        dict(name="采样证明不了冷", size=5, points=[
            P("难点", "没采到不等于没访问，当冷换出会误伤热页，引发refault"),
            P("三态证据", "热、冷候选、未知三态，未知态不换出"),
            P("非对称证据", "SPE命中即标热，冷须Accessed位为0加代龄确认，", highlight="SPE管热页表管冷"),
        ]),
        dict(name="预取对象与预取量", size=5, points=[
            P("难点", "预取多了挤掉别的页，预取晚了又没用"),
            P("恢复集", "应用切后台时记录最近窗口热页，切回前台头几百毫秒批量换入"),
            P("余量封顶", "预取量受内存余量封顶，命中率低自动减量，", highlight="热集合预取加封顶"),
        ]),
    ],
    milestones=ms(("2027.03.31", "SPE可用性摸底\n采样开销实测"),
                  ("2027.06.30", "冷热模型与恢复集\n预取原型"),
                  ("2027.09.30", "合入内部版本")),
))

# ---------------------------------------------------------------- KT1-c
pages.append(dict(
    title="多证据匿名页zram换出：",
    title_suffix="共用KT1-b冷热模型，后台存活+30%～+80%",
    challenges=[
        dict(name="容量被冻结", text="移动DRAM涨价4倍，只能靠回收腾空间"),
        dict(name="换出不准", text="误换热页引发refault，匿名页回收偏弱"),
        dict(name="杀进程代价高", text="压力顶满杀后台，冷启动与存活双输"),
    ],
    goal="基于同一冷热识别把冷匿名页换出到zram，不加DRAM提升有效容量，",
    goal_highlight="后台存活+30%～+80%",
    arch=build_arch(
        "KT1-c",
        [
            ("感知建模：冷热模型", [
                ("out", "冷热模型\n与KT1-b共用", 1),
                ("plain", "PSI与内存压力", None),
                ("plain", "zram mm_stat\n压缩率、占用", 2),
                ("plain", "各memcg前后台状态", None),
            ]),
            ("决策：候选与配额", [
                ("key", "冷候选清单\n三条证据一致才入选", 1),
                ("key", "按应用、按压力\n换出配额", 1),
                ("key", "zram与写回\n分流阈值", 2),
                ("plain", "熔断：refault超阈值\n暂停换出", None),
            ]),
            ("执行：换出与分流", [
                ("core", "经memory.reclaim\n/ DAMOS换出到zram", 3),
                ("plain", "可压缩冷页入zram\n可二次压缩", 2),
                ("plain", "不可压缩且空闲页\n限额写回，按日写入封顶", 2),
                ("plain", "与大folio对齐", None),
            ]),
        ],
        links=[((0, 0), (1, 0)), ((0, 1), (1, 1)), ((0, 2), (1, 2)), ((0, 3), (1, 1)),
               ((1, 0), (2, 0)), ((1, 2), (2, 1)), ((1, 2), (2, 2))],
        chains={1: [0, 1, 2]},
        fb_title="反馈",
        fb_items=["refault率", "换出后5秒内重访比例", "lmkd杀进程次数", "压缩率与闪存写入量"],
    ),
    difficulties=[
        dict(name="换出准确率", size=5, points=[
            P("难点", "换出热页要付压缩再解压的代价，还可能触发lmkd"),
            P("证据一致", "须同时满足：无SPE热证据、访问位为0、代龄达标，", highlight="多证据一致才换出"),
            P("闭环预算", "按应用memcg设配额，先换已进后台且冷的应用，PSI反馈控量"),
        ]),
        dict(name="压缩、CPU与闪存的预算博弈", size=5, points=[
            P("难点", "不可压缩页占DRAM又压不下；写回带来闪存写放大与寿命问题"),
            P("分流", "可压缩冷页进zram（可二次压缩），不可压缩且长期空闲页限额写回，",
              highlight="按可压缩性分流"),
            P("写入封顶", "按日写入量设上限，与KT1-a共用一本账"),
        ]),
        dict(name="与内核既有回收协同", size=4, points=[
            P("难点", "回收路径与厂商hook复杂，内核swap子系统本身也在重构"),
            P("冷页注入", "用memory.reclaim或DAMOS作入口注入冷页清单，策略放用户态，",
              highlight="不改内核主路径"),
        ]),
    ],
    milestones=ms(("2027.03.31", "冷热模型原型与\n换出准确率基线"),
                  ("2027.06.30", "闭环配额与\n分流策略"),
                  ("2027.09.30", "合入内部版本")),
))

# ---------------------------------------------------------------- KT2-A
pages.append(dict(
    title="MoE专家缓存与稀疏权重分层：",
    title_suffix="自适应缓存加预测预取，命中率+30%、解码≥1.5倍",
    challenges=[
        dict(name="容量放不下", text="35B级Q4约21GB（估算），超16GB"),
        dict(name="命中率悬崖", text="iPhone上512MiB，LRU命中0%"),
        dict(name="换入带宽", text="未命中每token约1.1GB IO（估算）"),
    ],
    goal="把稀疏权重纳入系统分层，提升专家命中率，在有限内存下跑大模型，",
    goal_highlight="命中率较LRU+30%、解码较mmap≥1.5倍",
    arch=build_arch(
        "KT2-A",
        [
            ("感知建模：访问轨迹", [
                ("out", "专家访问轨迹\n层、专家、时间", None),
                ("plain", "热度与转移概率模型\n专家、PLE、神经元簇", 1),
                ("plain", "跨层门控信号\n预测后层专家", 2),
                ("plain", "UFS带宽与空闲内存", None),
            ]),
            ("决策：分层与淘汰", [
                ("core", "分层放置\nDRAM / 压缩区 / UFS", 1),
                ("key", "淘汰策略选择\nLRU / 频率 / 学习型", 1),
                ("key", "预取预测\n跨层预测+簇布局", 2),
                ("key", "未命中降级决策\n换入低位宽副本", 3),
            ]),
            ("执行：页池与预取", [
                ("plain", "权重页池\n与KT3共用映射", None),
                ("key", "异步预取线程\n共用UFS IO队列", 2),
                ("key", "低位宽副本\n未命中不阻塞解码", 3),
                ("plain", "NPU可见固定arena", None),
            ]),
        ],
        links=[((0, 1), (1, 1)), ((0, 2), (1, 2)), ((0, 3), (1, 0)),
               ((1, 0), (2, 0)), ((1, 2), (2, 1)), ((1, 3), (2, 2))],
        chains={0: [0]},
        fb_title="反馈",
        fb_items=["命中率", "预取准确率与提前量", "tokens/s", "热状态"],
    ),
    difficulties=[
        dict(name="命中率对容量和负载敏感", size=5, points=[
            P("难点", "小缓存下LRU遇循环访问完全失效；Agent任务一切换路由分布就漂移"),
            P("热度建模", "统一建模专家、PLE、神经元簇的热度，缓存由系统记账"),
            P("策略选择", "在LRU、频率、学习型策略间在线切换，", highlight="按负载在线选策略"),
        ]),
        dict(name="预取要在UFS带宽内到位", size=5, points=[
            P("难点", "专家仅2–3MB属随机读，要等前层门控算完才知后层用谁"),
            P("跨层预测", "前层门控预测后层专家，预取与KT3共用IO队列"),
            P("布局打包", "按簇打包存储布局（行列捆绑），", highlight="预测与布局联合设计"),
        ]),
        dict(name="精度与容量的折中", size=4, points=[
            P("难点", "低精度替换、减少激活专家都会损失质量"),
            P("低位宽兜底", "未命中时换入低位宽副本，", highlight="未命中也不阻塞"),
            P("质量门限", "用评估集约束质量折损"),
        ]),
    ],
    milestones=ms(("2027.03.31", "手机侧专家轨迹\n与LRU基线"),
                  ("2027.06.30", "自适应策略加预测\n预取原型"),
                  ("2027.12.31", "稀疏权重分层\n统一接口落地")),
))

# ---------------------------------------------------------------- KT2-B
pages.append(dict(
    title="KV Cache回收与压缩：",
    title_suffix="KV块化记账加分级压缩，常驻压缩≥2.5倍",
    challenges=[
        dict(name="钉住不可回收", text="KV在回收路径之外，易提前触发查杀"),
        dict(name="随上下文增长", text="4B稠密32K的KV约4.5GiB（估算）"),
        dict(name="压缩有质量风险", text="2-bit在工具调用上未充分验证"),
    ],
    goal="让KV成为可记账、可压缩、可换出的系统对象，降低常驻量并加快会话恢复，",
    goal_highlight="常驻压缩≥2.5倍、质量回归≤1个百分点",
    arch=build_arch(
        "KT2-B",
        [
            ("感知建模：块与会话", [
                ("out", "块注意力得分\n与访问时间", None),
                ("plain", "压缩容忍度\n按块评估", 2),
                ("plain", "会话优先级", None),
                ("plain", "内存压力与UFS带宽", None),
            ]),
            ("决策：块级四选一", [
                ("core", "保留 / 压缩 /\n换出 / 丢弃重算", 1),
                ("key", "分级压缩决策\n关键块保持高精度", 2),
                ("key", "IO与重算择优\n带宽不足选重算", 3),
                ("plain", "跨会话前缀共享判定\n系统提示、工具schema", 3),
            ]),
            ("执行：块池与换出", [
                ("core", "KV块池\n16 token一块，统一记账", 1),
                ("key", "量化与反量化kernel", 2),
                ("key", "UFS写出与预载", 3),
                ("plain", "前缀块共享映射", 3),
            ]),
        ],
        links=[((0, 0), (1, 0)), ((0, 1), (1, 1)), ((0, 2), (1, 0)), ((0, 3), (1, 2)),
               ((1, 0), (2, 0)), ((1, 1), (2, 1)), ((1, 2), (2, 2)), ((1, 3), (2, 3))],
        chains={},
        fb_title="反馈",
        fb_items=["TTFT", "解码速度", "工具调用成功率", "重算比例"],
    ),
    difficulties=[
        dict(name="KV块化记账", size=5, points=[
            P("难点", "KV在dma-buf或NPU缓冲里，不在LRU上，回收不了"),
            P("块池", "按16 token一块切分，纳入统一记账与分配"),
            P("回收接口", "每块可压缩、换出，或丢弃后重算，", highlight="KV成为可回收对象"),
        ]),
        dict(name="容忍度分级压缩", size=5, points=[
            P("难点", "2-bit量化与淘汰对工具调用、长推理的影响未知"),
            P("敏感度评估", "按块评估压缩容忍度并分级"),
            P("差异精度", "关键块保持高精度，系统提示、旧工具输出用低位宽，", highlight="按块差异化压缩"),
        ]),
        dict(name="换出与重算择优", size=5, points=[
            P("难点", "UFS带宽比DRAM低一个数量级，换出要掩盖延迟"),
            P("预载预测", "只换出长期不被关注的块，用元数据预测提前预载"),
            P("重算择优", "带宽不够选重算，跨会话复用固定前缀，", highlight="IO与重算择优"),
        ]),
    ],
    milestones=ms(("2027.03.31", "KV块池与统一\n记账原型"),
                  ("2027.06.30", "分级压缩与\n前缀复用"),
                  ("2027.09.30", "闪存换出与\n重算择优")),
))

# ---------------------------------------------------------------- KT3
pages.append(dict(
    title="模型加载/卸载零拷贝映射：",
    title_suffix="文件页直映射NPU，额外拷贝0份、冷加载达60%～70%",
    challenges=[
        dict(name="多份拷贝", text="权重在页缓存与NPU缓冲间重复"),
        dict(name="钉住代价高", text="8GB CMA约6.44s（待核实）"),
        dict(name="IO吃不满", text="4KB缺页难以打满UFS 5.8GB/s"),
    ],
    goal="权重以文件页直接映射给各算力，缩短冷加载、去除重复拷贝，并可回收，",
    goal_highlight="额外拷贝0份、冷加载达顺序读60%～70%",
    arch=build_arch(
        "KT3",
        [
            ("感知建模：清单与带宽", [
                ("out", "模型清单\n与布局元数据", None),
                ("plain", "各会话所需\n层和专家", None),
                ("plain", "UFS带宽与内存压力", None),
                ("plain", "NPU驱动与IOMMU能力\n待SoC厂商确认", 1),
            ]),
            ("决策：顺序与划分", [
                ("core", "加载顺序\n与预读窗口", 2),
                ("key", "常驻与可回收划分", 1),
                ("key", "卸载时机\n直接回收或保留映射", None),
                ("key", "权重内容键\n共享判定", 3),
            ]),
            ("执行：映射与预读", [
                ("key", "页对齐权重文件格式\n离线模型翻译", 1),
                ("key", "文件页经dma-buf\n映射到NPU IOMMU", 1),
                ("key", "批量预读\n与KT2-A共用IO队列", 2),
                ("plain", "共享映射\n统一记账", 3),
            ]),
        ],
        links=[((0, 0), (1, 0)), ((0, 1), (1, 0)), ((0, 2), (1, 2)), ((0, 3), (1, 1)),
               ((1, 0), (2, 2)), ((1, 1), (2, 1)), ((1, 3), (2, 3)), ((1, 1), (2, 0))],
        chains={},
        fb_title="反馈",
        fb_items=["冷 / 热加载时间", "缺页次数与IO大小分布", "回收后再缺页率"],
    ),
    difficulties=[
        dict(name="NPU路径文件页映射", size=5, points=[
            P("难点", "NPU要IOMMU映射与缓冲注册，常要求钉住而回收不了"),
            P("布局转换", "离线转为页对齐的NPU友好布局（模型翻译）"),
            P("IOMMU映射", "文件页经dma-buf映射给NPU，可缺页、可回收，", highlight="文件页即NPU内存"),
        ]),
        dict(name="顺序化大块IO", size=5, points=[
            P("难点", "缺页是4KB级随机请求，打不满UFS带宽"),
            P("打包预读", "按层或专家顺序打包，按调度顺序大块预读，", highlight="大块顺序读"),
            P("共享队列", "与KT2-A的预取共用IO队列"),
        ]),
        dict(name="权重按内容共享", size=5, points=[
            P("难点", "同一基座被多Agent、多LoRA、CPU与NPU各存一份"),
            P("共享映射", "以权重内容为键共享映射，", highlight="一份权重多方共用"),
            P("统一记账", "由内存系统统一记账，映射页计入模型内存"),
        ]),
    ],
    milestones=ms(("2027.03.31", "加载基线与\nIOMMU可行性"),
                  ("2027.06.30", "页对齐格式与\n大块预读"),
                  ("2027.09.30", "NPU零拷贝映射\n与权重共享")),
))

def est_w(t):
    return sum(0.55 if ord(ch) < 128 else 1.0 for ch in t)


def autosize(p):
    for d in p["difficulties"]:
        need = 50
        for pt in d["points"]:
            n = est_w(pt["name"]) + 1 + est_w(pt["text"]) + est_w(pt.get("highlight", ""))
            need += 19.5 * (int(n / 32) + 1)
        d["size"] = round(min(8, max(3, need / 30)), 2)


for p in pages:
    autosize(p)
    for ch in p["challenges"][:-1]:
        if not ch["text"].endswith("。"):
            ch["text"] += "。"

deck = {"style": "default",
        "pages": [{"template": "solution.solution-kickoff-difficulties", "data": p} for p in pages]}
out = sys.argv[1] if len(sys.argv) > 1 else "deck-p2.yaml"
with open(out, "w", encoding="utf-8") as f:
    yaml.safe_dump(deck, f, allow_unicode=True, sort_keys=False, width=1000)
print("written", out)

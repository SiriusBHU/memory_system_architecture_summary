# M5 调研笔记：3DGS 持续优化（G1）与神经渲染（G3）

> 调研日期 2026-11-03。范围：研究提示 1.3、第二部分（场景与瓶颈）、第四部分 G1、G3。第三部分由主笔汇总，本文不写。定位：AI+图形用于提升用户体验，不与系统功能挂钩。

## 摘要

1. 3DGS 手机端渲染已出现免排序方案：Mobile-GS（ICLR 2026）在骁龙 8 Gen 3 上冷启动 127 FPS、稳态 74 FPS，整机渲染功耗 0.83W（3DGS 量化版 5.89W），存储 4.6MB；渲染不再是瓶颈，瓶颈在采集 / 重建与格式。
2. 手机端重建已可用：PocketGS（arXiv 2026-01）在手机上端侧训练平均 255.2s、峰值内存低于 3GB；鸿蒙 Spatial Recon Kit 提供端侧 3DGS 重建与 Tiled 渲染（仅有第三方报道，官方文档未核到）。
3. 格式标准化加速：glTF KHR_gaussian_splatting 2026-02 发布候选版（单一二手来源称 2026-09-03 已批准，待核实）；SPZ 4（2026-05）约为 PLY 的 1/10；MPEG 的 GSC 仍在 CDAM / 探索阶段，轻量档草案要求 2GB 运行内存。
4. 神经渲染硬件在 2026 下半年落地：Arm Mali G2-Ultra NX（2026-09-08）首个把神经加速器放进着色器核；骁龙 8 Elite Gen 6 / Extreme（2026-09）带 Adreno Neural Fusion，称游戏省电最高 40%；Exynos 2600 带 ENSS。
5. 关键反直觉数据：iPhone 17（A19）上 MetalFX 插帧实测约 18ms/帧（开发者论坛，未经 Apple 确认），按 120Hz 的 8.3ms 预算无法满足，说明「插帧省不省电」强依赖专用硬件。
6. 最大资料空白：（a）手机端神经渲染（NSS / 插帧）的实测功耗和内存，厂商只给相对值；（b）国内厂商（vivo / OPPO / 小米 / 荣耀 / 华为）游戏超分插帧方案的公开技术细节，本轮几乎未查到；（c）3DGS 在手机上的常驻内存与 GPU 内存数据。

---

## 第一部分 1.3 AI+图形洞察（G1、G3）

### 1.3.1 G1：3DGS 的业界发展

**场景链（手机上）：采集 / 生成 → 压缩 / 存储 → 渲染。**

#### A. 采集 / 生成

| 路径 | 代表 | 事实 | 局限 |
|---|---|---|---|
| 端侧多视角优化重建 | PocketGS（arXiv 2601.17354，2026-01 提交，v6 为 2026-10-20）[R14] | 手机端完成几何构建、高斯初始化和 3DGS 优化；MobileScan 场景后处理平均 255.2s，所有场景峰值内存低于 3GB | 分钟级，不实时；摘要未给出量化画质指标；发热和功耗未披露 |
| 端侧 App | Scaniverse（Niantic Spatial）、Scantic [R6][R7] | Scaniverse 称可在设备上处理、约一分钟（复杂场景十分钟以上）；Scantic 称在本地重建，「数分钟」，需 iOS 17 / A12 及以上，SPZ 导出尚在计划中 | 时间为厂商自述，无基准；各 App 云 / 端处理口径不一，一篇第三方指南称 Scaniverse 在云端处理，与官方矛盾，待核实 |
| 鸿蒙端侧 SDK | Spatial Recon Kit（HarmonyOS 7 / API 26，名称有「空间建模服务」「空间建模套件」两种译法）[R13] | 输入多角度图像与相机参数，端侧 AI 自动位姿估计和关键帧筛选，输出 PLY 与 MP4 运镜视频；渲染为 Tiled 3DGS，称支持千万级高斯，编辑含主体提取等；称相较 WebGL 方案单帧能效提升 40%（视频介绍，未独立验证） | 仅搜到第三方文章，未找到华为官方文档；版本号对应关系待核实；PLY 输出体积大，未见压缩格式 |
| 单图前馈生成 | Apple SHARP（arXiv 2512.10685，ICLR 2026）[R5] | 单张照片一次前馈输出度量尺度的 3D 高斯，标准 GPU 上不到 1 秒，渲染超过 100FPS；LPIPS 降低 25–34%、DISTS 降低 21–43%（作者自报）；代码与权重开源 | 只能渲染邻近视角（窄基线）；报告的是「标准 GPU」，未给手机端延迟 |
| 伪 3D 照片 | iOS 26 Spatial Scenes [R15] | 对任意含清晰主体的照片加深度，用于锁屏 3D 效果，iOS 26、iPhone 12 及以上；效果不能分享 | 是否基于高斯表示未找到公开资料 |

观察：「视频 / 多图 → 3DGS」在手机上已是分钟级；「单图 → 3DGS」在服务器 GPU 上是亚秒级，是下一步上手机的方向，但手机端延迟、功耗未见公开数据（未找到公开资料）。

#### B. 压缩 / 存储 / 标准

| 项 | 事实 | 来源 |
|---|---|---|
| SPZ（Niantic） | 约比 PLY 小 90%，官方举例约 25MB 对 250MB（丰富场景）；MIT 许可 | [R8] |
| SPZ 4（2026-05-05） | 仍约为未压缩 PLY 的 1/10；8.5GB / 3400 万点的 PLY 上，比 SPZ 3 再小 2.5%，编码快 3 倍（1 分 8 秒对 3 分 26 秒）；加载端到端快 1.5–2 倍；浏览器中最高快 20 倍；改用 6 路 ZSTD 流并行解码；旧读取器打不开 SPZ 4 | [R9] |
| 学术压缩 | HAC 在 Mip-NeRF 360 上约 21.9MB（高码率）/ 15.3MB（低码率），Tanks&Temples 约 11.2 / 8.1MB（3DGS.zip 综述，数字为各方法作者自报，设定不完全可比） | [R10] |
| glTF | Khronos 2026-02-03 发布 KHR_gaussian_splatting 基础扩展的发布候选版；基础扩展不含压缩，压缩为嵌套扩展（如 SPZ 压缩扩展，草案）。radiancefields.com 称 2026-09-03 已标为「Complete, Ratified」且 Khronos 未发新闻稿，为单一二手来源，待核实 | [R3][R4] |
| MPEG | Gaussian Splat Coding（GSC）2024-10 立项；第一阶段针对 INRIA 3DGS 格式；近期路线是在 V-PCC（ISO/IEC 23090-5）上增加高斯 profile 的修正案（第 153 次会议达到 CDAM），并有 G-PCC 路线工作草案；2025-10 发布通用测试条件和轻量级草案需求，其中提议「2024/2025 年手机硬件上实时编解码、运行内存上限 2GB、至多 4 路并发视频解码」。最终发布状态未核实 | [R11] |

#### C. 渲染

| 方案 | 年份 / 来源 | 手机数据 | 局限 |
|---|---|---|---|
| Mobile-GS（免排序 + 神经视角相关增强 + 一阶 SH 蒸馏 + 神经向量量化 + 贡献度剪枝） | ICLR 2026，arXiv 2603.11531 [R2] | 骁龙 8 Gen 3（机型未披露），Vulkan 实现。Mip-NeRF 360：冷启动 127FPS、稳态 74FPS（Table 2 / 12），摘要引用的 116FPS 为 Bicycle 1600×1063；存储 4.6MB（Mip-NeRF 360）、2.5MB（Tanks&Temples）；功耗用 Qualcomm Trepn 测得整机 0.83W（3DGS 量化版 5.89W，SortFreeGS 量化版 4.03W），其中光栅化 0.42W、MLP 0.24W、预处理 0.17W、排序 0W | 论文未报 GPU 内存；基线表中 3DGS 量化版仅 8FPS（冷启动）/ 3FPS（稳态），冷启动与稳态差距大，说明持续热降频是关键；免排序有半透明伪影，需神经增强；Trepn 功耗口径（GPU 还是整机）待核实 |
| 网页端 | World Labs Spark 2.0（36 氪报道，2026-04）[R16] | 目标是大场景在手机浏览器中运行 | 仅二手报道，无帧率数据 |
| 鸿蒙 Tiled 3DGS | 见上 | 无独立数据 | 同上 |

**G1 小结（趋势一句话）：** 3DGS 在手机上的「渲染可行性」已被证明，行业焦点转向端侧重建速度、格式标准化与压缩。
- 事实依据：Mobile-GS 在骁龙 8 Gen 3 上 74–127FPS、0.83W [R2]；glTF 扩展发布候选版 [R3]；SPZ 4 [R9]；PocketGS 255.2s [R14]。
- 对我们的影响：渲染优化已有公开方案可借鉴，差异化应放在「采集 / 生成 → 存储 → 渲染」全链路的能效与热稳态上，而不是单点渲染帧率。

### 1.3.2 G3：神经渲染的业界发展

#### A. 硬件与图形 API

| 厂商 | 产品 / 发布 | 事实 | 来源与状态 |
|---|---|---|---|
| Apple | A19 Pro（iPhone 17 Pro，2025-09-09） | 「Neural Accelerators built into each GPU core」，6 核 GPU，硬件光追，vapor chamber 称持续性能最高提升 40% | Apple 新闻稿 [R1]（官方） |
| Apple | A20 Pro（iPhone 18 Pro，2026-09-09） | 7 核 GPU 比 A19 Pro 最高快 40%；新闻稿称 Neural Accelerators 集成在 6 核 CPU 中；双 16 核神经引擎（共 32 核）；内存带宽比 A19 Pro 高 50%；新一代 vapor chamber | Apple 新闻稿 [R17]（官方）。该页未说明 GPU 是否保留 Neural Accelerators，二手报道有出入，待核实 |
| Apple | MetalFX（Metal 4，WWDC25） | 新增帧插值和降噪上采样，A14 及以上可用；官方建议插帧前不低于 30FPS；插帧器可绑定时间上采样器获得更好的组合性能 | WWDC25 session 211 [R12] |
| Arm | Arm Neural Technology（SIGGRAPH 2025，2025-08-12） | 宣布从 2026 年起在 Arm GPU 中加入专用神经加速器；NSS 约 4ms/帧、540p 到 1080p（2 倍分辨率）、最高节省 50% GPU 负载（均为潜在值）；Vulkan 扩展 VK_ARM_tensors、VK_ARM_data_graph | Arm 新闻 [R18]（官方） |
| Arm | Mali G2-Ultra NX（CSS for Mobile 2，2026-09-08） | 首个「AI 原生」Mali GPU，神经加速器紧耦合在着色器核内，支持 INT8 / INT16 和光流加速；NSS、NFRU（神经插帧，最高 120FPS）、NSSD（超分加降噪）；官方称非 AI 游戏性能 +14%；Neural Dawn 演示称相对原生渲染性能效率最高 4 倍、外部内存流量最高降 70%；未披露功耗绝对值、核数、具体机型 | Arm 新闻 [R19]（官方） |
| Arm | Lumex CSS / Mali G1-Ultra（2025-09-10） | G1-Ultra 10–24 核；发布时无神经加速器，未宣布设计订单（vivo 在台上表示关注） | 二手报道 [R20] |
| Qualcomm | 骁龙 8 Elite Gen 5（2025-09） | GPU 支持 Snapdragon Game Super Resolution 2.0 与 Adreno Frame Motion Engine 3.0；未找到证据表明这是神经网络方案 | 二手报道 [R21] |
| Qualcomm | 骁龙 8 Elite Gen 6 / Extreme Gen 6（2026-09，2nm） | 重新设计的 Adreno GPU，称性能 +35%、能效 +40%；Extreme 带「AI 专用 Adreno Matrix Cores」；Adreno Neural Fusion 用矩阵核做 AI 超分和插帧，称支持游戏中功耗最多节省 40%；该文未说明哪个芯片带 Neural Fusion，各方报道有分歧 | 9to5Google 报道 [R22]；Qualcomm 官方页未核到，待核实 |
| Samsung | Exynos 2600（2025-12 公布，Galaxy S26 / S26+ 部分地区） | Xclipse 960（AMD RDNA 架构），称整体性能 2 倍、光追最高 +50%；ENSS（Exynos Neural Super Sampling）做 AI 超分和插帧；第三方评测 PUBG Mobile 超高画质约 59.6FPS（对比 S25 Ultra 约 39.9FPS） | 二手报道 [R23]；ENSS 实际收益未被独立验证 |
| Khronos | Vulkan ML 扩展 | VK_ARM_data_graph（扩展号 508）、VK_ARM_tensors 在注册表里均为非批准（厂商）扩展；Khronos 2026-07 的幻灯片称「data graph 目前以 Arm 扩展形式发布，并提议标准化」，同时提到光流和 TOSA 指令集扩展 | Khronos 注册表与幻灯片 [R24] |

**神经纹理压缩：** 本轮只查到 NVIDIA 的 RTX NTC（桌面 GPU 与 Windows on Arm，示例 32MB 原始纹理压到 2.50MB，对比传统压缩约 12MB，来自媒体转述，待核实）；未找到 Arm、Qualcomm、Apple 在手机 GPU 上的神经纹理压缩公开资料。

#### B. 软件：系统级与 SDK 级两种做法

| 维度 | 系统级（对游戏透明） | SDK 级（游戏集成） |
|---|---|---|
| 输入 | 仅最终帧（无深度、运动向量）或系统截获的 swapchain 帧 | 引擎提供深度、运动向量、抖动、曝光、UI 分层 |
| 能做什么 | 无引擎信息的帧插值、通用超分、锐化 | 时间上采样（TAAU 类）、带运动向量的插帧、光追降噪 |
| 画质风险 | UI 与 HUD 被一并插值产生伪影；快速运动易鬼影；无法区分世界与 UI | 画质上限更高，可对 UI 单独处理 |
| 代表 | 国内厂商的「游戏插帧 / 超分」系统功能，Qualcomm Adreno Frame Motion Engine（二手报道称类似帧生成，[R21]）；国内厂商各家细节本轮未查到 | MetalFX（Apple）[R12]、Arm NSS / NFRU 的 Vulkan 集成路径 [R18]、Snapdragon Game Super Resolution（Qualcomm，需游戏集成，待核实）、ENSS（Samsung） |
| 适配成本 | 零（对游戏透明），但覆盖面广质量低 | 每个游戏需要集成，质量高 |
| 对我们的含义 | 覆盖率高、见效快，但受限于输入信息；适合作为存量游戏的兜底 | 需要生态推动；与 Vulkan ML / Khronos 标准走向耦合 |

说明：上表「系统级」一栏是按技术约束做的归纳，各厂商的具体实现细节（例如国内厂商是否引入专用显示芯片）本轮未找到公开资料，不能当事实引用。

**国内手机厂商方案：** 本轮检索（vivo / OPPO / 小米 / 荣耀 / 华为的游戏超分插帧）没有查到官方技术资料；搜到的仅是营销性质的「2K 屏 + AI 超分」测评文章，数据口径不一，不予引用。vivo X300 Pro 的 VS1 芯片资料显示它面向影像（RAW 处理、多帧融合）而非游戏。待补。

#### C. 手机端实测数据

| 数据 | 来源 | 可信度 |
|---|---|---|
| MetalFX 帧插值在 iPhone 17（A19）上约 18ms/插值帧（游戏），三角形 demo 约 11ms，持续运行后升至约 30ms（伴随 GPU 性能态由最高降到最低）；输出 2622×1206；测量包含同步与 profiling 屏障 | Apple 开发者论坛帖 [R25]，Apple DTS 表示 Apple 未公布任何设备上的帧插值耗时 | 单个开发者的非受控测量，仅作量级参考 |
| Arm NSS：约 4ms/帧、540p 到 1080p、最高节省 50% GPU 负载 | Arm 官方（2025-08）[R18] | 厂商潜在值，非实测 |
| Arm Neural Dawn：性能效率最高 4 倍、外部内存流量最高 -70%（对比原生渲染） | Arm 官方（2026-09）[R19] | 厂商演示 |
| Qualcomm Neural Fusion：游戏省电最高 40% | 9to5Google [R22] | 厂商声称，条件未知 |
| Samsung Exynos 2600 ENSS | 无绝对功耗数据 | 未找到公开资料 |

**G3 小结（趋势一句话）：** 2026 下半年手机 GPU 把神经加速器做进着色器核，神经超分 / 插帧从「NPU 或 CPU 辅助」走向「GPU 内联」，API 层面在向 Vulkan data graph / tensor 扩展收敛。
- 事实依据：Arm G2-Ultra NX [R19]；骁龙 Gen 6 Neural Fusion [R22]；Apple 将神经加速器放进 GPU（A19 Pro）[R1]；Khronos 提议标准化 [R24]。
- 对我们的影响：2027 年我们面对的是「硬件多样、API 未统一」的局面，系统级方案需要抽象多家神经加速器；功耗收益要靠自己实测，厂商相对值不能直接引用。

### 竞争格局

| 玩家 | 定位 | 优势 | 劣势 | 对我们的启示 |
|---|---|---|---|---|
| Apple | 自研 GPU 加神经加速器，MetalFX 软硬一体 | 软硬件垂直整合，A19 Pro 起 GPU 内有神经加速器；SHARP 等研究直接输出 3DGS | 插帧耗时未公布，开发者实测约 18ms；生态封闭 | 对标「体验 + 研究」双线；插帧不应只看帧率，要看热稳态 |
| Arm（IP） | 为所有 Android SoC 提供神经图形 IP 与 Vulkan 扩展 | 覆盖面最广；官方 SDK 与开源模型，已有 Unreal 插件 | 扩展未批准为 Khronos 标准；设备与游戏落地时间未明 | 我方 SoC 若用 Arm GPU，可早期评估 NSS / NFRU |
| Qualcomm | Adreno Matrix Cores + Neural Fusion | 旗舰份额；厂商称省电最多 40% | 仅 Extreme 带矩阵核的说法有分歧；官方页未核实 | 需要核实自家平台是否具备同类硬件 |
| Samsung | Exynos 2600 + ENSS | 软硬一体 | 仅部分地区机型；第三方评测中 GPU 计算跑分与 Adreno 840 接近 | 仅作竞品参考 |
| 国内手机厂商 | 系统级游戏超分插帧 | 对游戏透明，覆盖存量游戏 | 公开技术资料少 | 待补充 |

### 对立项的启示（1.3）

1. G1 的价值不在「渲染帧率」，而在端侧「生成 → 存储 → 渲染」全链路在热稳态下的能效；渲染侧已有 Mobile-GS 级公开方案，我们需要在端侧生成（单图前馈）和格式落地上形成差异化。
2. G3 的硬件窗口在 2026–2027：Apple、Arm、Qualcomm、Samsung 均已或即将提供 GPU 内联神经加速；系统级（对游戏透明）方案是我们能控制的部分，SDK 级依赖游戏适配。
3. 本节所有「省电」数字均为厂商相对值，立项时必须自测，且需在持续负载（15–30 分钟）下测，而不是首次帧的数据。

---

## 第二部分 问题（G1、G3）

### 2.1 场景与需求

#### G1 场景（2027–2028）

| 场景 | 用户需求 | 指标 |
|---|---|---|
| S-G1-1 手机拍摄一圈生成可交互 3D 场景 / 物件 | 拍完就能看，不要等云端 | 端侧重建时间：基线 255s（PocketGS，估算同类设备）；目标待定，参考鸿蒙「分钟级」；峰值内存低于 3GB；重建期间设备表面温度和电量 |
| S-G1-2 单张照片生成可转头的 3D 效果（锁屏、相册、聊天） | 点一下立刻出效果 | 生成延迟：服务器 GPU 上 SHARP 亚秒级；手机端未找到公开数据；渲染 60FPS 以上 |
| S-G1-3 浏览 / 分享 3D 场景（相册、社交、电商） | 打开快，滑动流畅，文件小 | 首次可见时延；加载后渲染 60FPS 以上；单场景文件 10–25MB（参考 SPZ，[R8]）；渲染功耗（Mobile-GS 0.83W，[R2]） |
| S-G1-4 与 Agent / 生成式 UI 联动（Agent 生成 3D 场景作为界面素材） | 属于联动场景，本模块不展开 | 待与 M6 对齐 |

#### G3 场景（2027–2028）

| 场景 | 用户需求 | 指标 |
|---|---|---|
| S-G3-1 重度手游持续高画质 | 30 分钟不降频、不烫手 | 平均帧率与 1% Low；表面温度；每小时耗电（需自测）；GPU 负载降幅（Arm 声称最高 50%，[R18]） |
| S-G3-2 120Hz 高刷体验 | 低功耗下达到 120FPS | 插帧耗时占帧预算（120Hz 为 8.3ms，A19 上 MetalFX 实测约 18ms，[R25]）；插帧引入的输入延迟 |
| S-G3-3 存量游戏（不适配）体验提升 | 无需游戏更新也能提升帧率和清晰度 | 覆盖游戏数；画质伪影率（UI 鬼影等） |
| S-G3-4 光追游戏 | 在移动功耗下启用光追 | NSSD / 降噪后 GPU 负载与外部内存流量（Arm 称 Neural Dawn 最高降 70%，[R19]） |

### 2.2 当代系统与瓶颈

**G1 瓶颈：**

| 瓶颈 | 数据 | 来源 / 估算 |
|---|---|---|
| 原始 3DGS 渲染在手机上帧率低 | 3DGS（量化）冷启动 8FPS、稳态 3FPS；SortFreeGS（量化）24 / 18FPS；Speedy-Splat 19 / 10FPS | Mobile-GS Table 2 / 12 [R2] |
| 排序和光栅化功耗 | 3DGS 量化版 5.89W，SortFreeGS 4.03W，Mobile-GS 0.83W | Mobile-GS Table 13 [R2] |
| 文件体积 | 未压缩 PLY 约 250MB，SPZ 约 25MB；学术方法 Mip-NeRF 360 约 15–22MB | [R8][R10] |
| 端侧重建耗时和内存 | 255.2s，峰值内存低于 3GB | [R14] |
| 内存常驻 | 手机端 3DGS 的 GPU 常驻内存未找到公开数据；MPEG 轻量档草案提议 2GB 运行内存上限 | [R11]；估算方法：高斯数 × 每高斯参数字节数（待补） |
| 格式碎片化 | glTF 扩展 2026-02 发布候选，压缩为嵌套扩展；SPZ 4 旧读取器不兼容；MPEG 仍在 CDAM / 探索 | [R3][R9][R11] |
| 单图生成无手机端数据 | 未找到公开资料 | — |

**G3 瓶颈：**

| 瓶颈 | 数据 | 来源 / 估算 |
|---|---|---|
| 插帧耗时 | A19 上 MetalFX 插帧约 11–30ms，超出 120Hz 的 8.3ms 预算 | [R25]，单个开发者实测，待核实 |
| 持续性能降频 | A19 Pro 称 vapor chamber 带来最高 40% 持续性能提升（说明前一代降频明显）；vivo X300 Pro 评测显示《和平精英》120 帧数分钟后锁到 90 帧 | [R1]；vivo 评测来自 91mobiles 与国内媒体转述，待核实 |
| 神经加速器碎片化 | Apple（GPU 内）、Arm（着色器核内）、Qualcomm（Matrix Cores，可能仅 Extreme）、Samsung（ENSS）；Vulkan ML 扩展仍是 Arm 厂商扩展 | [R1][R19][R22][R24] |
| 对游戏透明的方案输入信息不足 | 无深度 / 运动向量，UI 被一并插值；各家细节待查 | 技术约束归纳，非来源事实 |
| 平台对比 | Android：Vulkan 上各家扩展不同；iOS：MetalFX 单一 API；HarmonyOS：Ark Graphics 3D（见 R13，细节待核实） | — |

### 对立项的启示（第二部分）

- G1 的体验指标应定为「重建分钟级、渲染 60FPS 以上、文件 10–25MB、渲染功耗 1W 量级」，依据来自 Mobile-GS 与 SPZ；目前最缺的是端侧重建和单图生成在目标 SoC 上的自测数据。
- G3 的最大瓶颈是「插帧在预算内完成」和「持续负载下降频」，这决定了神经渲染必须有硬件支撑，不能仅靠 NPU 通用路径。

---

## 第四部分 G1：3DGS 持续优化

### 1. 要解决的问题

- 现状：3DGS 画质高，但手机上存在三类代价。渲染（量化版 3DGS 稳态 3FPS、功耗 5.89W [R2]）；体积（原始 PLY 数百 MB，SPZ 约 25MB [R8]）；生成（多视角优化 255s [R14]，单图前馈亚秒级仅限服务器 GPU [R5]）。
- 代价：渲染功耗和热降频限制连续浏览；文件体积限制分享与存储；生成时间限制「拍完即看」。
- 注意：当前没有任何手机端的「采集 / 生成 → 压缩 / 存储 → 渲染」全链路公开数据，立项需要自建基线。

### 2. 业界做法扫描

| 方案 | 年份 | 来源 | 原理 | 局限 |
|---|---|---|---|---|
| Mobile-GS | 2026（ICLR） | arXiv 2603.11531 [R2] | 深度感知的顺序无关渲染免排序 + 神经视角相关增强 + SH 蒸馏 + 神经向量量化 + 剪枝 | 半透明伪影；论文未报 GPU 内存；设备机型未披露 |
| SortFreeGS | 年份与会议待核实 | 作为基线出现在 [R2] | 去掉排序的 3DGS | 手机 24 / 18FPS，功耗 4.03W（量化版） |
| HAC、C3DGS、LocoGS 等压缩 | 年份与会议待核实 | 3DGS.zip 综述（CGF 2025）[R10] | 熵编码 / 向量量化 / 剪枝 | 数字为作者自报；多以桌面 GPU 评估 |
| SPZ / SPZ 4 | 2024 起 / 2026-05 | Niantic Spatial [R8][R9] | 量化 + ZSTD 流并行压缩 | 非标准化；SPZ 4 旧读取器不兼容 |
| glTF KHR_gaussian_splatting | 2026-02 发布候选 | Khronos [R3] | 在 glTF 里存储高斯 | 基础扩展不含压缩；批准状态待核实 |
| MPEG GSC | 2024-10 起 | mpeg.expert / SIGMM [R11] | V-PCC / G-PCC 路线加联合探索 | 尚未发布；视频解码器依赖 |
| PocketGS | 2026 | arXiv 2601.17354 [R14] | 手机端完整 3DGS 训练流水线 | 255s，不实时；热 / 功耗未披露 |
| 鸿蒙 Spatial Recon Kit | 2026（HarmonyOS 7 / API 26，待核实） | 第三方文章 [R13] | 端侧位姿估计、关键帧、Tiled 3DGS 渲染 | 无官方文档，无独立数据 |
| Apple SHARP | 2025-12 / ICLR 2026 | arXiv 2512.10685 [R5] | 单图前馈回归 3D 高斯 | 邻近视角；无手机端数据 |
| Spark 2.0（World Labs） | 2026-04 | 36 氪 [R16] | 网页端动态 3DGS 渲染引擎 | 仅二手报道 |

### 3. 技术难点

**难点一：热稳态下的渲染能效**
- 难在哪：Mobile-GS 的冷启动 127FPS 与稳态 74FPS 差距明显，而常规 3DGS 冷启动 8FPS、稳态 3FPS；手机持续负载下 GPU 降频，真正能保住的是稳态。
- 怎么破：对象是每帧参与渲染的高斯集合与排序；在渲染层按视距 / 贡献度做 LOD 与按帧预算裁剪，把帧预算（含温度）反馈给高斯数量控制，放在渲染引擎与调度之间的预算控制模块。
- 关键突破：以「温度预算」而非「固定高斯数」驱动渲染。

**难点二：端侧生成的耗时与内存**
- 难在哪：多视角优化 255s、峰值内存低于 3GB [R14]；单图前馈在手机上未见数据。重建期间与前台应用争抢 GPU / 内存。
- 怎么破：对象是重建流水线；把重建拆为后台可抢占的阶段（位姿 → 初始化 → 优化），对「单图」场景用前馈模型替代优化，模型落在 NPU / GPU 上，结果以压缩格式落盘。放在生成模块。
- 关键突破：分阶段可抢占加前馈初始化。

**难点三：格式与压缩的端侧可解码**
- 难在哪：glTF 基础扩展不含压缩，SPZ 版本间不兼容，MPEG 未发布；解码不能占用过多 CPU / 内存；MPEG 轻量档草案提议 2GB 内存上限 [R11]。
- 怎么破：对象是文件格式与加载路径；跟随 glTF 扩展与 SPZ，解码并行化（SPZ 4 已用 6 路 ZSTD 流），加载时流式上传 GPU，避免整体解压后常驻。放在存储 / 加载模块。
- 关键突破：以标准容器 + 并行解码 + 流式上传取代私有格式。

### 4. 机制架构

| 段 | 模块与数据流 |
|---|---|
| 感知 / 建模 | 采集模块（相机帧 + ARKit / 位姿）、场景复杂度估计、热 / 电量监测；产出每场景的高斯数、预计负载 |
| 决策 | 预算控制器（目标帧率、温度预算）、生成路径选择（多视角优化 / 单图前馈 / 云）、LOD 与量化档位决策 |
| 执行 | 生成模块（后台可抢占重建）、压缩模块（SPZ / glTF 封装）、加载模块（并行解码、流式上传）、渲染模块（免排序 / Tiled 光栅化） |
| 反馈 | 稳态帧率与功耗遥测、温度、用户停留时长；回灌预算控制器与档位表 |

### 5. 目标与度量

| 指标 | 基线 | 目标（区间与依据） | 测试条件 |
|---|---|---|---|
| 渲染稳态帧率 | 量化 3DGS 稳态 3FPS [R2] | 60FPS 以上（参考 Mobile-GS 稳态 74FPS） | 旗舰 SoC，持续 15–30 分钟，需自测 |
| 渲染功耗 | 5.89W（3DGS 量化）[R2] | 低于 1.5W（参考 0.83W，留出余量） | 同一 Trepn 类口径，需自测并核实口径 |
| 单场景文件 | PLY 约 250MB [R8] | 10–25MB（SPZ 量级）；小场景个位数 MB（Mobile-GS 4.6MB） | 典型房间级场景 |
| 端侧重建时间 | 255s [R14] | 区间待定，需在目标 SoC 上先建基线 | 同一 MobileScan 级输入 |
| 重建峰值内存 | 低于 3GB [R14] | 不高于 3GB | 同上 |
| 单图生成手机端延迟 | 无公开数据 | 待基线 | 待定 |

### 6. 风险与待核实

- 标准未定：glTF 批准状态、MPEG 的 V-PCC 修正案最终结果均待核实。
- Mobile-GS 功耗口径（是否整机）和设备机型待核实；功耗与帧率为论文自报，未经第三方复现。
- 鸿蒙 Spatial Recon Kit 仅有第三方报道。
- 3DGS 的内容生态与杀手级场景不明确：iOS 26 Spatial Scenes 是否基于高斯表示未找到公开资料。
- 隐私：手机端处理的优势在于数据不出设备，但分享链接 / 云端渲染会引入隐私问题（Scantic 分享链接在端上加密再上传，[R7]）。

### 7. PPT 素材卡

**挑战**
1. 渲染功耗高：量化 3DGS 稳态仅 3FPS、功耗 5.89W，持续使用即降频。
2. 生成太慢：多视角端侧重建约 255s，单图前馈仅在服务器 GPU 达亚秒级。
3. 格式未统一：PLY 约 250MB，标准未定，旧读取器不兼容。

**目标：** 在手机热稳态下实现 3DGS「拍完即看、秒开流畅」的端到端体验，形成采集到渲染的全链路能效方案。（≤44 字，自核：约 38 字）
**量化目标：** 稳态 60FPS+，渲染功耗 1W 量级。

**技术难题**
1. 热稳态渲染能效
   - 温度预算：以温度而非固定数量驱动高斯数量裁剪。
   - 免排序：去除排序，避免半透明伪影靠神经增强补偿。
   - 关键突破：温度预算驱动 LOD
2. 端侧生成耗时
   - 可抢占：重建拆阶段，后台让位前台应用。
   - 前馈初始化：单图用前馈模型，替代多视角优化。
   - 关键突破：分阶段可抢占重建
3. 格式端侧可解码
   - 标准容器：跟随 glTF 扩展与 SPZ，不做私有格式。
   - 流式加载：并行解码，直接上传 GPU。
   - 关键突破：并行解码流式上传

**架构四段**
- 感知 / 建模：采集模块、复杂度估计、热 / 电量监测
- 决策：预算控制器、生成路径选择、LOD 档位决策
- 执行：生成模块、压缩封装、并行加载、免排序渲染
- 反馈：稳态遥测、温度回灌、档位表更新

---

## 第四部分 G3：神经渲染

### 1. 要解决的问题

- 现状：重度手游和光追游戏在持续负载下受功耗与温度限制；高刷（120Hz）对每帧预算只有 8.3ms。
- 代价：A19 上 MetalFX 插帧实测约 11–30ms [R25]，超出 120Hz 预算；Arm 声称 NSS 约 4ms/帧、可省最多 50% GPU 负载 [R18]，Qualcomm 称 Neural Fusion 游戏省电最多 40% [R22]，均为厂商声称，无独立实测。
- 国内厂商的存量游戏超分插帧：公开技术资料未找到，无法量化。

### 2. 业界做法扫描

| 方案 | 年份 | 来源 | 原理 | 局限 |
|---|---|---|---|---|
| MetalFX 时间上采样 / 插帧 / 降噪上采样 | 2025（WWDC25，Metal 4） | Apple [R12] | 基于深度、运动向量的时间上采样；插帧在两渲染帧之间生成帧 | 需游戏集成；A19 实测约 18ms/帧 [R25]（非官方） |
| Arm NSS / NFRU / NSSD | 2025-08 宣布，2026-09 随 G2-Ultra NX | Arm [R18][R19] | 着色器核内的神经加速器，神经超分、神经插帧（最高 120FPS）、超分加降噪 | 设备尚未列出；功耗绝对值未披露；SDK 级 |
| Vulkan ML 扩展 VK_ARM_data_graph / VK_ARM_tensors | 2025 | Khronos 注册表 [R24] | 新增 data graph 管线，在 Vulkan 内运行神经网络 | Arm 厂商扩展，未批准为标准 |
| Qualcomm Adreno Neural Fusion | 2026-09 | 9to5Google [R22] | GPU 矩阵核做 AI 超分与插帧 | 哪个芯片具备存在分歧，官方页待核实 |
| Samsung ENSS | 2025-12 | 二手报道 [R23] | AI 超分和插帧 | 仅 Exynos 版本机型；收益未被独立验证 |
| Snapdragon Game Super Resolution 2.0 / Adreno Frame Motion Engine 3.0 | 2025-09 | 二手报道 [R21] | 空间超分与运动插帧 | 是否为神经网络方案未找到证据 |
| NVIDIA RTX NTC（神经纹理压缩） | 2023 起，SDK 近期支持 Windows on Arm | arXiv 2305.17105、SDK 页 [R26] | 小 MLP 解码纹理 | 桌面 GPU；手机端未找到公开资料 |

### 3. 技术难点

**难点一：帧预算内完成神经推理**
- 难在哪：120Hz 预算 8.3ms，插帧实测约 11–30ms；推理与渲染共享 GPU，持续运行后 GPU 被降频（论坛测量中伴随性能态由最大降到最小）。
- 怎么破：对象是神经推理在 GPU / NPU 间的放置；有硬件的平台把网络放进 GPU 内联神经加速器，用 INT8 / INT16；无硬件的平台使用更小的模型或半分辨率光流；放在渲染后处理阶段，由调度器按帧预算决定是否启用插帧。
- 关键突破：按帧预算动态启停神经插帧。

**难点二：对游戏透明的系统级方案输入信息不足**
- 难在哪：系统级方案拿不到引擎的深度、运动向量，UI 与 HUD 同被插值产生伪影。
- 怎么破：对象是游戏最终帧与系统可获取的少量信息；在合成器 / 显示管线一侧估计光流，并用 UI 层检测（如检测固定屏幕区域或合成层）做遮罩；放在系统图形栈的后处理模块；SDK 级方案则补充深度与运动向量，作为高质量路径。
- 关键突破：系统级光流加 UI 遮罩，SDK 级补充运动向量。

**难点三：神经加速器碎片化与 API 未统一**
- 难在哪：Apple、Arm、Qualcomm、Samsung 各自一套；Vulkan ML 仍是 Arm 厂商扩展 [R24]。
- 怎么破：对象是神经图形算子的抽象；在系统图形栈里做一个后端抽象层，向上暴露统一的「超分 / 插帧 / 降噪」接口，向下适配各硬件的 tensor / data graph 路径；放在图形框架与驱动之间。
- 关键突破：统一算子抽象层，屏蔽硬件差异。

### 4. 机制架构

| 段 | 模块与数据流 |
|---|---|
| 感知 / 建模 | 帧时间与 GPU 频率 / 温度监测、游戏类型与内容检测、UI 层识别、可用硬件能力查询 |
| 决策 | 帧预算调度器（决定超分比例、是否插帧）、路径选择（系统级 / SDK 级）、模型档位选择 |
| 执行 | 神经超分、神经插帧、降噪、UI 合成、后端抽象层（GPU 神经加速器 / NPU / 通用 GPU） |
| 反馈 | 帧率、帧间隔抖动、功耗与温度遥测，画质异常（伪影）检测，回灌调度器 |

### 5. 目标与度量

| 指标 | 基线 | 目标（依据） | 测试条件 |
|---|---|---|---|
| 持续负载平均功耗 | 待自测 | 相对原生渲染降低 20–40%（参考 Qualcomm 称最多 40% [R22]、Arm 称最多 50% GPU 负载 [R18]；厂商值，需自测校准） | 重度手游 30 分钟，同画质主观对比 |
| 插帧耗时 | A19 上约 11–30ms [R25]（非官方） | 小于 4ms（参考 NSS 约 4ms [R18]） | 120Hz，目标 SoC |
| 帧率稳定性 | 待自测 | 1% Low 提升；帧间隔抖动低于 X ms（待定） | 同上 |
| 存量游戏覆盖 | 待定 | 覆盖主流游戏的比例（待定） | 系统级路径 |
| 画质伪影 | 待定 | UI 鬼影率下降（指标待定义） | 评测集待建 |

### 6. 风险与待核实

- 所有省电 / 加速数字为厂商声称，未经独立实测，必须在目标平台上自测。
- Qualcomm Neural Fusion 具体芯片归属、Apple A20 Pro GPU 是否有 Neural Accelerators 均待核实。
- Vulkan ML 扩展标准化时间不明。
- 国内厂商方案、神经纹理压缩在手机端状态：未找到公开资料。
- 输入延迟：插帧会增加输入延迟，未找到手机端数据。
- 游戏厂商适配意愿（SDK 级）。

### 7. PPT 素材卡

**挑战**
1. 帧预算超支：A19 插帧实测约 18ms，120Hz 预算仅 8.3ms。
2. 持续降频：高负载游戏数分钟后锁帧，体验波动。
3. 硬件碎片：四家神经加速器各异，API 未统一。

**目标：** 在手机持续高负载下，以神经超分与插帧换取更低功耗和更稳帧率，对存量游戏透明可用。（≤44 字，自核：约 41 字）
**量化目标：** 同画质功耗降 20–40%，插帧小于 4ms。

**技术难题**
1. 帧预算内完成推理
   - 内联加速：网络放进 GPU 神经加速器，走 INT8。
   - 预算调度：按帧时间动态决定是否启用插帧。
   - 关键突破：按预算动态启停插帧
2. 系统级输入不足
   - 光流估计：在合成器侧估计运动，无需游戏提供。
   - UI 遮罩：识别 HUD 层，避免插值鬼影。
   - 关键突破：系统光流加 UI 遮罩
3. 加速器碎片化
   - 算子抽象：统一超分、插帧、降噪接口。
   - 多后端：适配 GPU 内联、NPU 与通用 GPU。
   - 关键突破：统一算子抽象层

**架构四段**
- 感知 / 建模：帧时间监测、温度监测、UI 层识别、硬件能力查询
- 决策：帧预算调度、路径选择、模型档位
- 执行：神经超分、神经插帧、降噪、后端抽象层
- 反馈：帧抖动遥测、功耗温度、伪影检测

---

## 对立项的启示（总）

- 支撑 G1：渲染侧公开方案已够用，立项重点是端侧重建 / 单图生成与格式落地，并以热稳态能效为指标。
- 支撑 G3：硬件窗口 2026–2027 已打开，系统级对游戏透明的方案可作为我们的主战场，SDK 级方案跟随 Khronos / 厂商演进。
- 共同前提：先建立自己的手机端功耗 / 内存 / 帧率基线，因为本轮公开数据在这三项上都不足。

---

## 参考资料

| 编号 | 标题 | URL | 日期 |
|---|---|---|---|
| R1 | Apple 发布 iPhone 17 Pro 与 Pro Max（A19 Pro，GPU 神经加速器） | https://www.apple.com/newsroom/2025/09/apple-unveils-iphone-17-pro-and-iphone-17-pro-max/ | 2025-09-09 |
| R2 | Mobile-GS: Real-time Gaussian Splatting for Mobile Devices | https://arxiv.org/abs/2603.11531 （HTML：https://arxiv.org/html/2603.11531） | 2026-03-12 提交；ICLR 2026 |
| R3 | Khronos 发布 glTF Gaussian Splatting 扩展（发布候选） | https://www.khronos.org/news/permalink/khronos-announces-gltf-gaussian-splatting-extension | 2026-02-03 |
| R4 | radiancefields.com：Khronos Group（批准状态的单一二手来源） | https://radiancefields.com/platforms/the-khronos-group | 2026-09（待核实） |
| R5 | SHARP: Monocular View Synthesis in Less Than a Second（ICLR 2026，arXiv 2512.10685） | https://apple.github.io/ml-sharp 、https://proceedings.iclr.cc/paper_files/paper/2026/hash/297fe652867e4897e9f1fe1cd715de19-Abstract-Conference.html | 2025-12 |
| R6 | Scaniverse：Creating splats, which app to choose | https://scaniverse.com/news/creating-splats-which-app-to-choose | 日期未标 |
| R7 | DigitalProduction：Gaussian splats on the iPhone（Scantic） | https://digitalproduction.com/2026/08/20/gaussian-splats-on-the-iphone/ | 2026-08-20 |
| R8 | Niantic SPZ 仓库 / Scaniverse SPZ 页 | https://github.com/nianticlabs/spz 、https://scaniverse.com/spz | 日期未标 |
| R9 | Niantic Spatial：SPZ 4 | https://www.nianticspatial.com/blog/spz4 | 2026-05-05 |
| R10 | 3DGS.zip: A survey on 3D Gaussian Splatting Compression Methods（CGF 2025） | https://arxiv.org/abs/2407.09510 | 2025 |
| R11 | MPEG-I Gaussian Splat Coding；SIGMM MPEG Column 第 153、154 次会议 | https://mpeg.expert/gsc/index.html 、https://records.sigmm.org/mpeg-column-153rd-mpeg-meeting/ | 2025 |
| R12 | WWDC25 session 211：Go further with Metal 4 games | https://developer.apple.com/videos/play/wwdc2025/211/ | 2025-06 |
| R13 | HarmonyOS 7（API 26）Spatial Recon Kit 3DGS 端侧重建（第三方文章） | https://www.woshipm.com/operate/6471997.html | 2026（待核实） |
| R14 | PocketGS: High-Fidelity On-Device Training for 3D Gaussian Splatting | https://arxiv.org/abs/2601.17354 | 2026-01-24（v6：2026-10-20） |
| R15 | MacRumors：iOS 26 Spatial Scenes | https://www.macrumors.com/how-to/ios-3d-lock-screen-effect-spatial-scenes/ | 2025 |
| R16 | 36 氪：World Labs Spark 2.0 报道 | https://eu.36kr.com/en/p/3767557281268483 | 2026-04 |
| R17 | Apple 发布 iPhone 18 Pro 与 Pro Max（A20 Pro） | https://www.apple.com/newsroom/2026/09/apple-debuts-iphone-18-pro-and-iphone-18-pro-max/ | 2026-09-09 |
| R18 | Arm Neural Technology（NSS，SIGGRAPH 2025）；cnx-software 转述 | https://newsroom.arm.com/news/arm-announces-arm-neural-technology 、https://www.cnx-software.com/2025/08/13/arm-neural-technology-ai-acceleration-to-arm-gpus-enables-neural-super-sampling-for-lower-bandwidth-higher-fps/ | 2025-08-12 |
| R19 | Arm Newsroom：Mali G2-Ultra NX | https://newsroom.arm.com/?p=22020 | 2026-09-08 |
| R20 | SiliconANGLE：Arm Lumex 与 Mali G1-Ultra | https://siliconangle.com/2025/09/10/arm-debuts-ai-optimized-lumex-chip-lineup-mobile-devices/ | 2025-09-10 |
| R21 | 骁龙 8 Elite Gen 5 发布报道（FoneArena） | https://www.fonearena.com/blog/465280/qualcomm-snapdragon-8-elite-gen-5-features.html/amp | 2025-09 |
| R22 | 9to5Google：Snapdragon 8 Elite Gen 6 | https://9to5google.com/2026/09/22/snapdragon-8-elite-gen-6/ | 2026-09-22 |
| R23 | Notebookcheck / Neowin 等：Exynos 2600 与 ENSS | https://www.neowin.net/amp/samsung-exynos-2600-announced-2nm-gaa-process-113-faster-ai-and-new-thermal-tech/ | 2025-12 |
| R24 | Khronos Vulkan 注册表：VK_ARM_data_graph；Khronos 神经渲染幻灯片 | https://registry.khronos.org/vulkan/specs/latest/man/html/VK_ARM_data_graph.html 、https://www.khronos.org/developers/linkto/machine-learning-neural-rendering-and-the-future-of-open-graphics-slides | 2025；幻灯片 2026-07 |
| R25 | Apple 开发者论坛：MetalFX FI on iPhone ~18ms | https://developer.apple.com/forums/thread/853871 | 2026（具体日期未标） |
| R26 | Random-Access Neural Compression of Material Textures；NVIDIA RTXNTC | https://arxiv.org/pdf/2305.17105 、https://github.com/NVIDIA-RTX/RTXNTC | 2023 |

## 待核实清单

1. glTF KHR_gaussian_splatting 是否已于 2026-09-03 批准（目前仅 R4 单一二手来源）；压缩子扩展（SPZ）状态。
2. MPEG V-PCC 高斯 profile 修正案、G-PCC 路线的最终发布状态。
3. 鸿蒙 Spatial Recon Kit 的官方文档、API 版本对应、设备范围；「单帧能效提升 40%」来源。
4. Mobile-GS 所用手机机型、Trepn 功耗口径（整机或 GPU）、GPU 内存；116FPS（Bicycle）与 127 / 74FPS 的口径差异。
5. Apple A20 Pro 的 GPU 是否保留 Neural Accelerators（官方新闻稿只写 CPU 内置）；A19 与 A19 Pro 在 GPU 神经加速器上的差异（二手报道有出入）。
6. Qualcomm 官方对 Adreno Matrix Cores / Neural Fusion 的芯片归属、省电 40% 的测试条件。
7. Arm Mali G2-Ultra NX 的首批设备、核数、功耗绝对值；Neural Dawn 是否已上线。
8. MetalFX 插帧在 iPhone 上的官方耗时（目前只有开发者论坛测量）。
9. 国内厂商（vivo / OPPO / 小米 / 荣耀 / 华为）游戏超分插帧的官方技术资料，以及是否使用专用显示 / 图像芯片。
10. SortFreeGS 等基线论文的年份与会议；HAC / C3DGS / LocoGS 的年份与会议。
11. Scaniverse 实际是端侧还是云端处理的当前版本；SPZ 的 glTF 压缩扩展是否对应 SPZ 4。
12. 单图前馈 3DGS（SHARP 类）在手机上的延迟与功耗：未找到公开资料。
13. 神经纹理压缩在 Arm / Qualcomm / Apple 手机 GPU 上的状态：未找到公开资料。
14. iOS 26 Spatial Scenes 是否基于高斯表示：未找到公开资料。
15. Exynos 2600 ENSS 的绝对功耗 / 内存数据：未找到公开资料。

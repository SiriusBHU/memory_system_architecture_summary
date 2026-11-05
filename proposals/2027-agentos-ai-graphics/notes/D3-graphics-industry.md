# D3 产业洞察补充：AI + 图形（G1 3DGS / G2 AI 萌宠 / G3 神经渲染 / G4 生成式 UI）

> 调研日期 2026-11-04。方法：WebSearch（standard）+ WebFetch，未使用 deep-research。本文只补 M5、M6 笔记里缺的硬事实，已有结论不重复。
> 标注约定：【官方】厂商/标准组织/监管机构一手页面；【二手】媒体或博客转述；【厂商口径】厂商自述数字；【估算】附算式；【待核实】单一或二手来源；「未找到公开资料」即检索后确实没有。
> 定位提醒：本线只做体验提升，不与系统功能挂钩，不做 GUI Agent。

---

## 要点摘要（12 条）

1. **3DGS 已进入主流工具链，但手机系统层仍是空白**：Apple 官方文档显示 RealityKit 在 visionOS 27 才新增 GaussianSplatComponent（WWDC26，仅真机，需 Apple7 GPU 家族）【官方】；iOS 侧未找到公开的高斯 API。Android XR、Meta Quest 已有产品化路径（Hyperscape 云端渲染 2–4 小时出结果【二手】）。
2. **格式标准半落地**：glTF KHR_gaussian_splatting 2026-02-03 发布候选版【官方】，2026-09-03 标为 Ratified 仅有 radiancefields 一个二手来源【待核实】；压缩子扩展（SPZ）仍是草案；MPEG 仍在 CDAM / 探索阶段，IEEE P3366.3 高斯压缩 PAR 于 2026-06-04 批准【二手】。
3. **市场规模数据质量差**：Coherent Market Insights 称 2026 年 3DGS 市场 18.5 亿美元、2033 年 78 亿美元、CAGR 11%，但端点推算 CAGR 约 23%（算式见 1.4 节），自相矛盾，不可引用；可靠的是融资数：radiancefields 统计 13 家公司累计披露融资超 15 亿美元（其中 Wayve 超 10 亿）。
4. **最硬的商业化信号来自「非手机」**：Adobe Photoshop 27.6 的 Rotate Object（2026-04-28）两个月内产生约 80 万个 SPZ 文件（Niantic 自报）；Zillow SkyTour（2025-11 上线）用高斯做房源外观；手机厂商相册 / 电商 3D 商品展示未找到公开资料。
5. **国内「超帧」不是单一技术路线**：vivo/iQOO 用自研电竞芯片 Q1→Q2→Q3（官方称 Q2 支持 144FPS 超帧、Q3 称「2K 超分 + 120FPS 超帧 + 光追」并发）；一加 16（2026-10-12）自研 P4 显示芯片 + 「电竞三芯」，官方称原生 185FPS；荣耀 Magic8 与高通定义 GPU+NPU 异构，首发基于 NPU 的超分超帧（2025-09）。
6. **独立显示芯片的第三方供应链正在收缩**：Pixelworks 2026-01-06 完成出售上海子公司，10-Q 明确其不再经营半导体业务（含 Mobile），净现金对价约 5126 万美元【官方 SEC】；此前 X7 用于 Redmi K60 至尊版、一加 12 等。
7. **手机端插帧延迟与功耗仍无独立数据**：只有 A19 上 MetalFX 插帧约 18ms/帧（开发者论坛，非 Apple 官方）；MetalFX 插帧文档层面「增加 1 帧输入延迟」（Bevy 插件文档）；桌面端 DLSS 4.5 动态多帧生成在 RTX 5080 上延迟 68ms（高倍率）对 45ms（目标 120fps）【二手】。
8. **AI 陪伴的「龙头」出事了**：Character Technologies 于 2026-10-12 在特拉华州申请 Chapter 11（案号 26-11603），Disney 关联公司作为 stalking-horse 出价约 2000 万美元获取 IP 许可，拟于 11 月底至 12 月初完成出售【二手，TechCrunch 2026-10-13 等多家一致】。MiniMax 招股书披露 Talkie 月活超 2000 万（截至 2025-09），海外收入占比超 70%。
9. **中国监管已落地且条款硬**：《人工智能拟人化互动服务管理暂行办法》2026-04-10 由五部门公布，2026-07-15 施行；不得向未成年人提供虚拟亲属 / 虚拟伴侣等虚拟亲密关系服务；连续使用超 2 小时须提醒；设安全评估与算法备案【官方转述】。美国加州 SB 243 自 2026-01-01 生效，已知未成年人每 3 小时提醒，年度报告义务从 2027-07-01 起。
10. **Android 已出现官方 A2UI 渲染器**：developer.android.com/ml 列出「Jetpack Compose A2UI Renderer」（标注 New feature，无日期无状态）【官方】，修正 M6 中「Android 无官方方案」的说法；A2UI GitHub 当前 v0.9.1、v1.0 为候选版、约 1.7 万星，Flutter / SwiftUI 渲染器均未发布。
11. **MCP Apps 已是官方扩展**：2026-01-26 成为首个官方 MCP 扩展（稳定修订 2026-01-26）；发布时支持 ChatGPT、Claude、VS Code、Goose。OpenAI 应用目录于 2026-07-09 并入 Plugin 目录【官方帮助中心】。
12. **生成式 UI 的速度账**：Google Research 自述当前实现「有时需要一分钟以上」（2025-11-18）；按 60 token/s、3000 token 估算为 50 秒（算式 3000÷60），两者吻合，说明「边生成边渲染」是刚需。HarmonyOS 方面未找到官方的生成式 UI 资料。

---

## 1. G1：3DGS 的商业化与生态

### 1.1 已上市 / 已落地产品

| 产品 | 是否用高斯表示 | 事实与数据 | 来源（日期） |
|---|---|---|---|
| Apple iOS 26 Spatial Scenes | 未找到公开资料 | 对照片加深度，用于锁屏 3D 效果，iPhone 12 及以上；Apple 未说明实现方式，radiancefields 称「看起来与 NeRF / 高斯同源」属推测，Reddit 评论认为只是深度 + 补全 | 9to5Mac 2025-06-10；radiancefields【二手】 |
| Apple visionOS 27 RealityKit | 是（API 层面） | GaussianSplatComponent；资源类型目前只有 buffer resource；不受场景光照影响；超出预算时自动降低 splat 工作量并发 RenderingChanged 事件；需 Apple7 GPU 家族；模拟器不渲染；关联 WWDC26 session 287、279 | Apple 开发者文档（页面读取 2026-11-04）【官方】 |
| Apple Spatial Personas | 开发者称使用高斯 | 论坛开发者说法，Apple 未确认 | Apple 开发者论坛 thread 807309【二手】 |
| Meta Hyperscape Capture | 是（高斯 + 云端渲染流式） | 2025-09 早期访问，Quest 3 / 3S，18 岁以上；扫描数分钟，云端处理后 2–4 小时通知可看；起初仅自己可见，后续扩展分享与探索 | TechCrunch 2025-09-17；radiancefields【二手】 |
| Google Maps Immersive View（Android XR / Galaxy XR） | 室内场景用高斯（Unity 文章），室外未被 Google 确认 | Unity 称室内场景需要高性能高斯渲染；radiancefields 称曼哈顿超过 1000 个地点有 3D 室内 | Unity 页面；support.google.com/android-xr/answer/16667577（2025-10）【二手为主】 |
| Niantic Scaniverse | 是 | 2026-04-07 重构为网页 + 移动平台；第三方追踪（AppGoblin）估计约 220 万安装、约 2.7 万月活（第三方估算，非官方） | Niantic Spatial；AppGoblin【二手】 |
| Polycam | 是 | 总融资 2210 万美元、员工约 27 人（radiancefields，可能过时）；未找到用户数 | radiancefields【二手】 |
| Luma AI | 曾支持 | Scaniverse 博客称 Luma 已于去年 11 月暂停高斯处理；Luma 融资 6850 万美元 | Scaniverse 博客；radiancefields【二手】 |
| Snap Lens Studio | 是 | 5.3 起内置 3DGS trainer（30 秒视频重建物体，输出 PLY）；支持高斯动画帧序列（GSAF）；Snap 文档称 Snap 拥有 PlayCanvas / SuperSplat | developers.snap.com【官方】 |
| Adobe Photoshop 27.6 | 是（SPZ） | Rotate Object（2026-04-28）；Niantic 称 Photoshop 用户两个月内创建约 80 万个 SPZ 文件；Adobe 增加了自有 SPZ 扩展 0xADBE0002 存轨道相机参数 | Niantic 博客；radiancefields（Niantic 自报，未独立验证） |
| Zillow SkyTour | 是 | 无人机影像重建房源外观 3D，Showcase 房源专属，2025-07 发布、2025-11 上线；2026 年未见扩展公告 | Zillow 新闻稿 2025-07-15；Inman 2025-11-25 |
| 华为 HarmonyOS 7 | 是（端侧重建） | 面向物品与小场景，生成可旋转缩放的三维影像；仅有第三方报道，官方文档未核到 | 沿用 M5 [R13]，本轮搜索再次仅见二手【待核实】 |
| 国内相机 / 相册 3D（OPPO、vivo、小米、荣耀） | 未找到公开资料 | — | — |
| 淘宝 / 京东 3D 商品展示 | 未找到公开资料 | 仅见海外电商向的 Graswald 等第三方工具 | — |

### 1.2 引擎与工具链

| 工具 | 状态 | 说明 | 来源 |
|---|---|---|---|
| Unity | 无官方支持，社区插件活跃 | ArasP MIT 插件，Unity 6 的 URP/HDRP 为 v2.0.0；UnitySplats 支持 SOG、SPZ v1–v4、glTF 高斯 | radiancefields 引擎支持页（2026）【二手】 |
| Unreal Engine | 无官方支持 | 插件覆盖 UE 5.1–5.8（YaGS 5.3–5.7、LCC4Unreal 5.1–5.8）；Cesium for Unreal 2026-03 支持 glTF 高斯 | 同上【二手】 |
| Blender | Blender 5.3（预发布）原生 PLY / SPZ 导入；4.2–5.3 有 add-on | 来源单一【待核实】 | 同上 |
| PlayCanvas / SuperSplat | 原生支持 | SuperSplat 3.0（约 2026-09）改为仅 WebGPU；v3.7.0（2026-10）新增 24 个 WebMCP 工具让 AI 代理编辑 splat | radiancefields【二手】 |
| Three.js | 第三方 | Spark.js（World Labs，MIT），要求 three.js r180 及以上、WebGL2 | 同上 |
| Godot | 社区插件 | GDGS 等，需 Godot 4.3+ | 同上 |

规模指标（radiancefields，截至 2026-07-09，自家数据库，非独立审计）：收录 212 个高斯平台 / 工具，其中 iOS App 12 个、Android App 7 个、Vision Pro 原生 App 5 个；13 家公司披露融资合计超 15 亿美元；论文 3333 篇，2026 年至 7 月 9 日至少 749 篇。

### 1.3 标准状态

| 标准 | 状态 | 来源（日期） |
|---|---|---|
| Khronos glTF KHR_gaussian_splatting | 2026-02-03 发布候选版【官方】；2026-09-03 在 glTF 扩展注册表标为 Complete, Ratified，Khronos 未发新闻稿，仅 radiancefields 一处【待核实】；基础扩展不含压缩，最前沿的是草案 KHR_gaussian_splatting_compression_spz_2；CesiumJS / Cesium Native 已实现，Babylon.js、PlayCanvas 也已发布支持 | Khronos；radiancefields |
| MPEG GSC | 仍在探索阶段；V-PCC（ISO/IEC 23090-5）修正案在第 153 次会议达 CDAM，G-PCC（23090-9）路线达 WD；第 154 次会议（2026-04-27 至 05-01）报告仍称探索；可能发布独立部分的征案（Call for Proposals）；未见 FDIS | SIGMM MPEG Column 154；mpeg.expert/gsc |
| IEEE P3366.3 高斯压缩 | PAR 批准 2026-06-04，项目进行中 | standards.ieee.org【二手检索摘要】 |
| SPZ | SPZ 4 约为未压缩 PLY 的 1/10，6 路并行 ZSTD，去除 1000 万点上限，旧读取器不兼容；发布日期两处不一致（Niantic 博客 2026-05-05，radiancefields 称 5 月 11 日）；Niantic 称 SPZ 4 导出将在「数月内」进入 Scaniverse | Niantic 博客【官方】 |

### 1.4 用户量与市场规模

- **用户量**：Scaniverse 约 220 万安装、2.7 万月活（AppGoblin 第三方估算）；Polycam、Luma 未找到公开用户数；Snap、Meta 未单列高斯相关用户数。唯一的「使用量」类硬数是 Photoshop 约 80 万个 SPZ 文件 / 2 个月（Niantic 自报）。
- **市场规模**：Coherent Market Insights（付费报告，GII 转载）称 2026 年 18.5 亿美元、2033 年 78.0 亿美元、CAGR 11%。【估算复核】若端点正确，CAGR = (7.80÷1.85)^(1/7) − 1 = 4.216^(0.1429) − 1 ≈ 22.8%，与其自称的 11% 不符；若 CAGR 为 11%，2033 年应约 38.4 亿美元（1.85×1.11^7≈3.84，单位十亿美元）。两个数字必有一个有误，**不建议在汇报里引用**。
- 国内市场规模：未找到公开资料。

### 1.5 分析：这说明什么（判断）

1. 3DGS 的价值已被「内容工具」（Photoshop、Lens Studio、Zillow）和「XR 设备」（Hyperscape、Android XR、visionOS 27）验证，但**手机相册 / 相机端没有任何一家厂商公开把高斯做成面向普通用户的系统体验**，这既是空白也意味着没有用户量先例。
2. 2027 年手机上最可能的杀手级场景，按证据强度排序（判断）：**（a）拍一圈物体 / 小场景→可转动的 3D 影像并一键分享（物品级）**，理由是有 Scaniverse、Snap 3D Capture、鸿蒙端侧重建三条已验证路径，且体积可压到 SPZ 量级；**（b）单图→可转头的 3D 效果（锁屏 / 相册）**，Apple 已用 Spatial Scenes 验证了需求，SHARP 证明单图前馈可行，但手机端延迟 / 功耗没有公开数据；**（c）电商 3D 商品展示**，国内平台公开资料为零，只能作为生态机会，不宜作为立项主张。
3. 对立项的含义：iOS 侧没有公开高斯 API，Android / 鸿蒙侧没有系统级格式支持，**「系统级高斯渲染 + 格式支持」本身是空档**；glTF 批准状态不明时，建议以 glTF + SPZ 为准、不自造格式。

---

## 2. G3：移动端神经渲染与插帧

### 2.1 SoC / GPU 厂商方案（补充 M5 之外的新增事实）

| 厂商 | 新增事实 | 来源（日期） |
|---|---|---|
| Arm Mali G2-Ultra NX | 矩阵加速器每个着色器核最多 1024 INT8 MAC / 时钟，仅支持 INT8 / INT16（无 FP8 / BF16）；增加着色器核面积约 21%（1.88 vs 1.55 mm²）；Ultra 品牌至少 6 个 NX 核，最多 24 核；Arm 称游戏最高 +14%、光追最高 +24%；未给每帧耗时。Arm 与 Sumo Digital 联合的 Neural Dawn 计划 2026 年内在新 Mali GPU 设备上发布 | Chips and Cheese；unite.ai【二手】；Arm Newsroom 2026-09-08【官方】 |
| 首批设备 | Chips and Cheese 称小米 XRING O3（2026-08-24 发布）使用 G2-Ultra NX 且仅一半着色器核带矩阵加速器；与 Arm 官方「2026-09-08 发布、设备未宣布」的时间线存在冲突 | 【待核实】 |
| 联发科 | Dimensity 9500：插帧升级到 3.0，30–60→60–120 FPS，称功耗降低 40%，使用 Mali-G1 Ultra MP12，软件插帧；Dimensity 9600（传闻）GPU 代号 Magni，传言带硬件插帧 | HotHardware；传闻为 Gizchina 等【厂商口径 / 传闻】 |
| 高通 | Snapdragon Game Super Resolution 是 Adreno GPU 的上采样器族，GSR 2 为时间上采样，需要游戏提供运动缓冲与深度裁剪缓冲（即 SDK 级）；Neural Fusion 的芯片归属仍无官方页佐证 | github.com/quic/snapdragon-gsr；Qualcomm 开发者博客 2024-06 |
| Apple | MetalFX 插帧在 A19 上约 18ms/帧、三角形 demo 约 11ms；Apple DTS 称未公布任何设备的插帧耗时；Bevy 插件文档称 MetalFX 插帧「增加 1 帧输入延迟」；未找到插帧功耗数据 | Apple 开发者论坛 thread 853871；docs.rs bevy_metalfx |

### 2.2 国内手机厂商：独立芯片、GPU/NPU 方案与游戏适配

| 厂商 / 型号 | 方案 | 官方说法与数据 | 来源（日期） |
|---|---|---|---|
| vivo / iQOO | 自研电竞芯片 Q1（iQOO 12）→ Q2（iQOO 13）→ Q3（iQOO 15 Ultra，2026-02-04） | Q1 称「超分超帧并发」；Q2 称 PC 级 2K 纹理超分、原生级 144FPS 超帧，《和平精英》2K 144FPS 超分超帧并发；Q3 称「全场景光追 + 2K 原画超分 + 120FPS 超帧」三项并发。超帧与插帧的算法细节、功耗、延迟均未公开 | 环球网、IT之家、科技日报 2026-02-05【厂商口径，二手转述】 |
| vivo V3 | 影像芯片（6nm，AI-ISP），不是游戏插帧芯片 | — | gsmarena / China Daily 2023-07-31 |
| OPPO / 一加 | 一加 16（2026-10-12）自研「电竞三芯」：网络 G3、触控 T3、超级显示 P4（面向超高刷新率显示）；风驰游戏内核；称《和平精英》《三角洲行动》《暗区突围》等原生 185FPS，另称「DLSS4 同代体验超帧」使不支持的游戏稳跑 185FPS | 中关村在线、凤凰科技 2026-09/10【厂商口径】；一加 15 等机型 165Hz 游戏阵容 2025-09 宣布 |
| 荣耀 | 与高通共同定义 GPU+NPU 异构，Magic8 首发基于 NPU 的超分超帧，称较传统 GPU 超分降低延迟与抖动；低 bit 量化使模型推理提速 15%、推理功耗降 20%、内存省 30%（针对端侧大模型，不是游戏超分功耗） | 荣耀官网 / 科技日报 2025-09-28；IT之家（读取失败，引自检索摘要）【厂商口径】 |
| 华为 | 方舟图形引擎称降功耗约 30%，GPU Turbo X 提稳帧；畅享 90 Pro Max「120 帧」被质疑为 60 帧渲染加算法补帧，论坛讨论称延迟约 10–20ms，缺独立测量 | 二手报道【待核实】 |
| 小米 / Redmi、一加、realme | 此前采用 Pixelworks X7（Redmi K60 至尊版、OnePlus 11 国行 / 12、realme GT5）：SoC 渲染后交独显芯片做 MEMC 插帧、低功耗超分、HDR；厂商称分担 GPU 负载以降低整机功耗；评论指出该流程增加显示延迟，「一插二」更大 | displaydaily；Nasdaq；虎嗅 / 界面分析【厂商口径 + 二手分析】 |
| Pixelworks 本身 | 2026-01-06 售出上海子公司（含 Mobile 业务），买方 Tiansui Xinyuan（上海）；净现金对价 5126.1 万美元（10-Q 表内为千美元口径，正文 RMB 数字单位疑为千元）；此后不再经营半导体业务 | SEC 10-Q（2026-06-30）【官方】 |

**游戏厂商适配（腾讯天美《王者荣耀》、光子《和平精英》，米哈游《原神》）**：未找到天美 / 光子 / 米哈游与手机厂商联合实验室的官方公告，也没有适配名单与机型数量。能确认的是：（a）《王者荣耀》165 帧适配仍是博主传闻（IT之家 2026-04）；（b）一加 2025-09 宣布与《三角洲行动》《英雄联盟手游》《王者荣耀》《和平精英》布局 165 帧；（c）联发科与光子长期合作优化《和平精英》高刷（旧资料）。适配关系大多是「游戏提供高帧率档位 + 厂商做内核 / 芯片侧优化」，而不是游戏接入神经插帧 SDK。**实测功耗与延迟：国内厂商超帧方案未找到可信的独立数据**（现有文章多为营销稿，部分自带「AI 生成内容」标注，不采信）。

### 2.3 桌面参照的教训

| 方案 | 事实 | 教训 |
|---|---|---|
| NVIDIA DLSS 4 / 4.5 多帧生成 | Hardware Unboxed 结论：输出帧率更高、更平滑，但伪影更多、延迟略高于单帧生成，好条件下好、坏条件下比单帧更糟；DLSS 4.5 动态多帧生成在 RTX 5080、Cyberpunk 2077 4K：目标 240Hz 时 5–6 倍生成、延迟 68ms（「黏滞感」），目标降到 120fps 后 2–3 倍、约 45ms；NVIDIA 论文称每个生成帧在 5090 上约 1ms | 底帧率必须足够高；倍率越高，延迟与鬼影越明显；生成成本可以压到亚毫秒但依赖专用硬件 |
| AMD FSR 4 | 升级器质量接近 DLSS 4；2025-12 的 Redstone 增加了机器学习帧生成与光追组件；某站称 4K 下 DLSS 帧生成延迟比 FSR 低约 18%，无方法说明【不采信】 | 开放方案追得上，但差距在帧生成与延迟 |
| Sony PSSR | 2026 年未找到有价值资料 | 未找到公开资料 |

延迟的量级账（【估算】）：插帧需要等下一真实帧才能生成中间帧，至少增加一个底帧时间。底帧 60fps 时 1000÷60≈16.7ms，底帧 30fps 时 1000÷30≈33.3ms，再叠加推理耗时（A19 实测 11–30ms）。这解释了 Apple 建议底帧不低于 30fps。

### 2.4 系统级与 SDK 级格局

| 层级 | 代表 | 输入 | 质量上限 | 覆盖 | 主要玩家 |
|---|---|---|---|---|---|
| SDK 级（游戏集成） | MetalFX、Arm NSS / NFRU、Snapdragon GSR 2、ENSS | 深度、运动向量、抖动、UI 分层 | 高 | 取决于游戏接入 | 芯片 / API 厂商 |
| 系统级 · 独立显示芯片 | iQOO Q 系、一加 P4、过去的 Pixelworks X7 | 仅最终帧（SoC 输出） | 中，UI 与高速运动易出伪影 | 对游戏透明，存量游戏可用 | 旗舰机型厂商，需自研芯片 |
| 系统级 · GPU / NPU 软件 | 荣耀 Magic8 NPU 超帧、联发科插帧 3.0 | 最终帧或部分元数据（细节未公开） | 待评估 | 对游戏透明 | OEM + SoC 联合 |

### 2.5 分析：这说明什么（判断）

1. 国内头部厂商已把「超帧」做成芯片 + 内核的差异化卖点，但**全部是厂商口径，没有可复核的功耗与延迟数据**；这既说明用户价值被市场验证，也说明独立评测空白，我们自测一份对比数据本身就有汇报价值。
2. Pixelworks 退出移动业务意味着**没有自研芯片能力的中端 / 中低端机型失去了第三方「插帧芯片」这条路**（判断；其业务被中国买方接手后的供货情况未找到公开资料），GPU / NPU 软件方案成为这类机型的唯一选项，这是系统级软件方案的机会窗口。
3. 我们的空间：不与自研芯片拼峰值帧率，而是做**跨 SoC 的统一抽象 + UI 遮罩 + 热稳态预算调度**；SDK 级路径跟随 Arm / Khronos 演进。风险：Vulkan ML 扩展仍是 Arm 厂商扩展，标准化时间不明。

---

## 3. G2：AI 陪伴 / 萌宠

### 3.1 应用：营收与用户

| 产品 | 数据 | 口径与来源（日期） |
|---|---|---|
| Character.AI | 月活约 2000 万（峰值约 2800 万，2024 年中），日活约 580 万；2025 营收约 3000 万美元（Sacra）；CEO Anand 称不到 20% 的使用属于陪伴，多数为角色扮演与小说。**2026-10-12 申请 Chapter 11**（特拉华州，26-11603），Disney 关联公司 stalking-horse 约 2000 万美元获取 IP 许可，拟 11 月底至 12 月初出售 | 聚合站 / Sacra【二手】；破产事实 TechCrunch 2026-10-13、Bondoro 申报提示【二手，多源一致】；404 Media 经 AI Weekly 称 2026-01 至 08 算力支出 5610 万美元、月收入峰值 530 万美元【待核实】 |
| Talkie / 星野（MiniMax） | 招股书：截至 2025-09 AI 原生应用月活 2760 万，Talkie 超 2000 万；2025 年前 9 个月总收入 5343.7 万美元，其中 Talkie/星野与海螺 AI 两款产品收入分别为 1746.4 万、1875 万美元（报道未明确对应次序，三项合计 5163 万与总收入有出入）；海外收入占比超 70% | 新京报、新华财经转述招股书（2025-12-21 聆讯后版本；2026-01-09 港股上市）【二手】 |
| 猫箱、星野（国内） | QuestMobile 2024-11：星野 446 万、猫箱 445 万月活；猫箱 2024-08 至 12 月月活 307→688 万。2026 年数据未找到公开资料 | 澎湃 / 人人都是产品经理【二手，已过时】 |
| Replika | Sensor Tower 估算应用商店内购约 480 万美元 / 年（2026-06，经 Latka）；意大利 Garante 于 2025-05-19 因 GDPR 违规罚款 500 万欧元 | Latka；多家法律媒体【二手】 |
| 浪漫类陪伴 App 整体 | 沿用 M6：Appfigures 2026 上半年 1.628 亿美元内购；前 10% 应用占 89% 收入 | Decrypt 2026-07-13；TechCrunch 2025-08-12 |
| 留存 / 时长 | 陪伴类第三方 D1/D7/D30 未找到公开资料；Character.AI 时长 75 分钟（早期口径）与 8–9 分钟冲突，不引用 | — |

### 3.2 硬件宠物与手机厂商形象化助手

| 对象 | 事实 | 状态与来源 |
|---|---|---|
| Casio Moflin | 售价 429 美元；日本 2024-11 上市，至 2025-03 售出 7000 台以上（超目标），美英 2025-09 上市；中长期全球销售目标约 3400 万美元 | 已发布；BetaNews【二手】 |
| Loona（KEYi） | 449–499 美元；销量未找到 | 已发布；厂商页面【厂商口径】 |
| Ropet | KAMOMO 389–419 美元（KEYi 对比表，厂商口径）；累计出货近 2 万台、2026-04 获超千万美元 A 轮（沿用 M6） | 已发布；公司口径 |
| 荣耀 Robot Phone | 2026-08-12 发布，9999 元起，云台拟人表情 | 已发布；沿用 M6，官方未称宠物 |
| Apple | Bloomberg Gurman（2025-08）：桌面机器人 2027 目标，约 1000 美元，Siri 形象测试过 Finder 式图标到 Memoji 式头像，未定稿；郭明錤预测 2028 年及以后；另传有智能家居中枢 | **传闻**，非已发布 |
| 华为小艺、荣耀 YOYO、小米超级小爱、OPPO 小布、三星 | 沿用 M6 逐家核实，未找到官方形象化 / 萌宠系统功能；本轮未发现新证据 | 未找到公开资料 |
| xAI Grok Companions | 2025-07 上线；Common Sense Media 2026-01 评估称无年龄验证、Ani 可引导至性内容；NCOSE 2026 Dirty Dozen 点名；是否下线仍无权威确认 | 争议属实【二手】；下线说法低可信【待核实】 |
| FTC | 2025-09-11 向 Alphabet、Character、Instagram、Meta、OpenAI、Snap、xAI 发出 6(b) 令 | 美国监管 |

### 3.3 监管

| 地区 | 法规 | 核心条款（日期） | 来源 |
|---|---|---|---|
| 中国 | 《人工智能拟人化互动服务管理暂行办法》，征求意见稿 2025-12-27（反馈截止 2026-01-25）；正式版 2026-04-10 由网信办、发改委、工信部、公安部、市场监管总局公布，2026-07-15 施行 | 适用于「持续性情感互动服务」，智能客服 / 问答 / 工作助手不在范围；**不得向未成年人提供虚拟亲属、虚拟伴侣等虚拟亲密关系服务**；不满 14 周岁提供其他拟人化互动须监护人同意；需未成年人模式与身份识别；连续使用超过 2 小时提醒（征求意见稿第十七条，正式版新闻稿仍有）；不得以替代社交、诱导沉迷依赖为目标；便捷退出；敏感个人信息未经单独同意不得用于训练；设安全评估与算法备案 | 新华社 2026-04-10；中新网 2026-07-15；汉坤律所对征求意见稿的解读【官方转述，条文原文未读到，条款号以官方文本为准】 |
| 美国加州 | SB 243，2025-10-13 签署，2026-01-01 生效 | 需披露是 AI；已知未成年人每 3 小时休息提醒；防止性内容；自残处置协议；年度报告义务 2027-07-01 起 | FPF、Jones Walker、Decrypt【二手】 |
| 美国纽约 | AI Companion Models 法，2025-11-05 生效 | 披露与保护措施，总检察长可罚最高 1.5 万美元 / 天；另有 S 9051 禁止向未成年人提供陪伴聊天机器人的报道，来源可靠性不明 | Fenwick【二手】；S 9051【待核实】 |
| 欧盟 / 意大利 | Garante 对 Replika 罚款 500 万欧元（2025-05-19）；EU AI Act 对陪伴机器人的具体处理未找到 | — | Mondaq 等 |

### 3.4 分析：这说明什么（判断）

1. **需求真实，但商业模式脆弱**：Character.AI 破产、星野长期未像 Talkie 一样商业化、陪伴 App 收入由头部吃掉，说明「独立 App 靠订阅」难成立；手机厂商的价值主张只能是体验与活跃，而非订阅收入。
2. **为什么只有系统层能做「常驻低功耗」**（技术推理，非实测）：应用进程受后台限制与内存回收，且无法在系统合成层按息屏 / 遮挡 / 温度降级；系统层可以事件驱动、息屏零帧、与合成器协同。**常驻功耗至今没有任何公开实测数据**，这是需要自建的基线。
3. **合规边界**：宠物若仅作为现有助手的表现层，可能落在「非持续性情感互动」范围之外；一旦配置人格、记忆、情感陪伴，即进入办法的适用范围，需安全评估与算法备案，且**不得对未成年人提供虚拟亲密关系**。系统层有账号与青少年模式信号，天然适合做年龄分流；但办法适用范围对「系统内置形象」的界定需要法务确认。2027 年立项建议把「不做亲密关系、不做情感替代，仅做表现与轻陪伴」写进边界。

---

## 4. G4：生成式 UI

### 4.1 协议与产品现状

| 方案 | 事实 | 来源（日期） |
|---|---|---|
| Google A2UI | 2025-12 中旬开源，初版 v0.8、公开预览；当前仓库 v0.9.1（稳定的 v0.9 系列补丁版），v1.0 为候选版，仍称「early stage public preview」；约 1.7 万星、1.4 千 fork；渲染器 Lit / Angular / React 已发 npm，Flutter（a2ui_flutter）与 SwiftUI（A2UISwiftUI）未发布，Compose 与 iOS 在仓库路线图中；传输层 A2A、AG-UI；集成方：CopilotKit（首日兼容）、Flutter GenUI SDK、ADK、LangGraph 等 | GitHub 仓库（读取 2026-11-04）【官方】；Analytics Vidhya 2025-12【二手】 |
| Android | developer.android.com/ml 列出「Jetpack Compose A2UI Renderer」：让 AI 代理用原生 Compose 与 Material 3 组件动态渲染 UI，标注 New feature，无日期无状态；AppFunctions（把应用变成设备端 MCP 服务器）与 Gemini 的集成仍是 private preview；RemoteCompose 与生成式 UI 的关系未确认 | Android 开发者官网（读取 2026-11-04）【官方】 |
| MCP Apps | 2026-01-26 成为首个官方 MCP 扩展（稳定修订 2026-01-26，SEP-1865 Final）；发布时支持 ChatGPT、Claude、VS Code、Goose；后续支持矩阵更广（含 Microsoft 365 Copilot、Cursor、Postman 等，来自第三方博客）；一篇来源称并入 2026-07-28 规范，未核实 | MCP 官方博客；modelcontextprotocol.io【官方】；其余【待核实】 |
| OpenAI | Apps SDK 于 2025-10 DevDay 推出，基于 MCP；应用目录于 2026-07-09 迁移到 Plugin 目录；用户量与应用数未找到公开资料 | OpenAI 帮助中心 11487775【官方】 |
| AG-UI / CopilotKit | AG-UI 是事件式「代理—应用」传输协议；CopilotKit 称被 Google、LangChain、AWS、Microsoft、Mastra、PydanticAI 等采用；CopilotKit 把生成式 UI 分为 static（AG-UI）/ declarative（A2UI、Open-JSON-UI）/ open-ended（MCP Apps）三类 | CopilotKit 官网 / 博客（2026，厂商口径） |
| 其他声明式 | Vercel json-render、Thesys OpenUI Lang（称 token 比 json-render 少 67.1%、渲染延迟快 2–3 倍，厂商口径）、Hashbrown | 聚合报道【厂商口径】 |
| Vercel AI SDK | 本轮未找到 streamUI 当前状态的可靠资料 | 未找到公开资料 |
| Gemini 生成式 UI | 2025-11-18 发布，Gemini 3 Pro；Gemini 应用「动态视图」「可视布局」，美国 AI Pro / Ultra 订阅用户在搜索 AI 模式使用；人评结果：专家设计网站最高，生成式 UI 紧随其后，远超其他格式；未报样本量、评分者数与具体百分比；明确**评测未计入生成速度**，实现「有时需要一分钟以上」 | Google Research 博客【官方】 |
| Apple | Foundation Models 的 @Generable 提供结构化输出与流式部分结果；WWDC25 session 286 提到递归类型可用于生成式 UI；WWDC26 框架扩展到端侧、Private Cloud Compute 与第三方模型（二手）；未找到 SwiftUI 层面的生成式 UI API；WWDC26 的 PartiallyGenerated 细节未核到官方页 | Apple 开发者（WWDC25）【官方】；WWDC26 部分【待核实】 |
| 华为 HarmonyOS / 小艺 | 未找到采用 A2UI 或「AI 生成界面」的官方资料；中国日报称小艺搜索由意图框架（Intents Kit）驱动，服务以元服务与卡片呈现，属于调度既有服务 | 中国日报 2025-12-25【二手】 |

### 4.2 性能与用户研究

| 项 | 数据 | 说明 |
|---|---|---|
| 生成一个界面的 token 数 | 未找到公开的 A2UI / MCP Apps 基准；示例估算：3000 token（假设值，沿用 M6） | 【估算】 |
| 生成耗时 | 60 token/s 时 3000 token = 3000÷60 = 50 秒；Google 自述「有时需要一分钟以上」（2025-11-18） | 估算与官方自述吻合 |
| 首屏时间 | 未找到公开资料。方法学资料称「首个有意义渲染」常比首 token 时间大 2–10 倍；Verygood Ventures 有 GenUI 模型基准（往返与首块时间，未读取） | 待补 |
| 用户研究 | 仅有 Google 内部人评（见上，无样本量）；未找到独立的受控用户研究 | 缺口 |
| 厂商 token 对比 | Thesys 称其格式比 json-render 少 67.1% token | 厂商口径，未独立复现 |

### 4.3 分析：这说明什么（判断）

1. 三种形态并存，且**主流云端客户端都在用 iframe 沙箱（MCP Apps）**；声明式（A2UI）由 Google 推进，并已出现 Android 官方的 Compose 渲染器，说明 Google 在把 A2UI 变成 Android 的原生通道。
2. 速度是硬约束：官方自述一分钟以上，估算 50 秒，两者吻合；因此手机系统层的价值不在「生成」而在**流式增量渲染、组件目录约束、与系统设计语言一致**。
3. 切入点：以声明式协议 + 系统组件目录为主（兼容 A2UI），iframe 仅作兜底；HarmonyOS 与 iOS 都没有公开协议，存在先发空间，但需要权衡「跟随 A2UI」与「自建」——Android 已官方跟进，A2UI 成为事实标准的概率在上升（判断，A2UI 仍为预览版，协议会变）。

---

## 参考资料（URL + 日期）

| 编号 | 内容 | URL | 日期 |
|---|---|---|---|
| D1 | radiancefields：Gaussian Splatting Statistics | https://radiancefields.com/gaussian-splatting-statistics | 截至 2026-07-09 |
| D2 | radiancefields：引擎支持 | https://radiancefields.com/3d-gaussian-splatting-engine-support | 2026 |
| D3 | radiancefields：Khronos 平台页 | https://radiancefields.com/platforms/the-khronos-group | 2026-09 |
| D4 | Apple：Gaussian splats on visionOS / GaussianSplatComponent | https://developer.apple.com/documentation/visionos/gaussian-splats-on-visionos.md ；https://developer.apple.com/documentation/realitykit/gaussiansplatcomponent.md | 读取于 2026-11-04（直接抓取返回 404，内容来自检索摘要，待复核） |
| D5 | 9to5Mac：Spatial Scenes 适用机型 | https://9to5mac.com/2025/06/10/psa-spatial-scenes-will-work-on-any-iphone-running-ios-26/ | 2025-06-10 |
| D6 | TechCrunch：Meta Hyperscape | https://techcrunch.com/2025/09/17/meta-launches-hyperscape-technology-to-turn-real-world-spaces-into-vr | 2025-09-17 |
| D7 | Unity：Google Maps Immersive View；Android XR 支持页 | https://unity.com/resources/google-maps ；https://support.google.com/android-xr/answer/16667577 | 2025-10 |
| D8 | Snap Lens Studio：Gaussian Splatting | https://developers.snap.com/lens-studio/features/graphics/gaussian-splatting | 读取于 2026-11 |
| D9 | Niantic Spatial：SPZ 4；radiancefields：Photoshop 27.6 | https://www.nianticspatial.com/blog/spz4 ；https://radiancefields.com/photoshop-releases-version-27.6-with-rotate-object | 2026-05；2026-04-28 |
| D10 | Zillow：SkyTour；Inman | https://www.zillowgroup.com/news/take-home-listings-to-new-heights-with-skytour ；https://www.inman.com/2025/11/25/zillows-skytour-uses-complex-3d-tech-to-simplify-home-search/ | 2025-07；2025-11-25 |
| D11 | SIGMM：MPEG Column 154；mpeg.expert GSC | https://records.sigmm.org/mpeg-column-154th-mpeg-meeting/ ；https://mpeg.expert/gsc/index.html | 2026-05 |
| D12 | Coherent Market Insights：3D Gaussian Splatting Market | https://www.coherentmarketinsights.com/industry-reports/3d-gaussian-splatting-market | 2026 |
| D13 | Chips and Cheese：Arm C2-Ultra / G2-Ultra NX | https://chipsandcheese.com/p/arms-c2-ultra-g2-ultra-nx-and-css | 2026-09 |
| D14 | unite.ai：Mali G2-Ultra NX（Neural Dawn） | https://unite.ai/arm-unveils-mali-g2-ultra-nx-its-first-ai-native-mobile-gpu | 2026-09 |
| D15 | HotHardware：Dimensity 9500 | https://hothardware.com/news/mediatek-unveils-dimensity-9500-big-ai-gaming-uplifts | 2025-09 |
| D16 | Pixelworks 10-Q（2026-06-30） | https://www.sec.gov/Archives/edgar/data/0001040161/000104016126000043/pxlw-20260630.htm | 2026 |
| D17 | 科技日报：iQOO 15 Ultra 电竞芯片 Q3；IT之家 / 环球网 Q1、Q2 | https://www.stdaily.com/web/gdxw/2026-02/05/content_470642.html ；https://www.ithome.com/0/811/846.htm | 2026-02-05 |
| D18 | 一加 16 发布报道（电竞三芯） | https://finance.sina.cn/stock/jdts/2026-10-13/detail-inivawmz7327658.d.html | 2026-10-13 |
| D19 | 荣耀 × 高通：骁龙峰会 2025 | https://www.honor.com/global/news/honor-snapdragon-summit-2025/ ；https://www.stdaily.com/web/gdxw/2025-09/28/content_409367.html | 2025-09 |
| D20 | Pixelworks X7 国内应用 | https://displaydaily.com/pixelworks-enhancing-redmi-k60-ultra-displays/ ；https://www.nasdaq.com/articles/oneplus-12-smartphone-launched-with-pixelworks-x7-visual-processor | 2023–2024 |
| D21 | Apple 开发者论坛：MetalFX FI；bevy_metalfx 文档 | https://developer.apple.com/forums/thread/853871 ；https://docs.rs/bevy_metalfx/latest/src/bevy_metalfx/lib.rs.html | 2026 |
| D22 | TechSpot 社区转述 Hardware Unboxed DLSS 4 MFG；TweakTown；dropreference | https://www.techspot.com/community/topics/a-review-of-nvidias-dlss-4-multi-frame-generation.290448 ；https://www.tweaktown.com/news/103968/dlss-4-research-paper-offers-a-detailed-look-at-the-new-transformer-model-and-multi-frame-gen/index.html | 2025–2026 |
| D23 | TechCrunch：Character.AI 破产；Bondoro 申报提示 | https://techcrunch.com/2026/10/13/just-5-years-in-interactive-chatbot-platform-character-ai-files-for-bankruptcy/ ；https://bondoro.com/character-ai-filing-alert/ | 2026-10-13 |
| D24 | 新京报：MiniMax 招股书；新华财经 | https://www.bjnews.com.cn/detail/1766325559129059.html | 2025-12-21 |
| D25 | 新华社 / 中新网：拟人化互动办法；汉坤解读征求意见稿 | https://www.news.cn/politics/20260410/bc2a2172b4d64a539cf253e75044b494/c.html ；https://www.chinanews.com.cn/cj/2026/07-15/10659837.shtml ；https://hankunlaw.com/portal/article/index/cid/8/id/16115.html | 2026-04-10；2026-07-15；2026-01 |
| D26 | 加州 SB 243：FPF；Jones Walker；Decrypt | https://fpf.org/blog/understanding-the-new-wave-of-chatbot-legislation-california-sb-243-and-beyond/ ；https://decrypt.co/344068/california-ai-companion-chatbots-regulation | 2025-10-13 |
| D27 | 纽约 AI 陪伴法：Fenwick；Replika 罚款：Mondaq | https://www.fenwick.com/insights/publications/new-yorks-ai-companion-safeguard-law-takes-effect ；https://www.mondaq.com/unitedstates/privacy-protection/1632274/us-based-ai-developer-fined-%e2%82%ac5-million-for-gdpr-violations-key-takeaways | 2025-11；2025-05 |
| D28 | FTC 6(b) 令：Decrypt；Character.AI 禁未成年人开放式聊天 | https://decrypt.co/339213/ai-giants-face-ftc-inquiry-into-chatbot-safety-and-child-protections ；https://www.engadget.com/ai/characterai-to-ban-teens-from-talking-to-its-chatbots-180027641.html | 2025-09-11；2025-10 |
| D29 | TechCrunch：Grok 儿童安全报告 | https://techcrunch.com/2026/01/27/among-the-worst-weve-seen-report-slams-xais-grok-over-child-safety-failures | 2026-01-27 |
| D30 | Engadget / iClarified：Apple 桌面机器人传闻 | https://engadget.com/ai/apples-tabletop-robot-companion-rumored-for-2027-launch-204904807.html | 2025-08（传闻） |
| D31 | Moflin：BetaNews；Loona / Ropet 价格：KEYi | https://betanews.com/2025/09/17/after-selling-out-in-japan-casios-429-moflin-ai-pet-launches-in-us-and-uk/ | 2025-09-17 |
| D32 | A2UI GitHub；Analytics Vidhya | https://github.com/google/A2UI ；https://www.analyticsvidhya.com/blog/2025/12/google-a2ui-explained/ | 读取 2026-11-04；2025-12 |
| D33 | Android 开发者：Integrate your app with the Android intelligence system | https://developer.android.com/ml | 读取 2026-11-04 |
| D34 | MCP Apps：SEP-1865；ext-apps | https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp | 2026-01-26 |
| D35 | OpenAI 帮助中心：ChatGPT apps → Plugin 目录 | https://help.openai.com/articles/11487775 | 2026-07-09 |
| D36 | Google Research：Generative UI | https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/ | 2025-11-18 |
| D37 | CopilotKit：Generative UI 指南；AG-UI | https://docs.copilotkit.ai/ag-ui-protocol ；https://dev.to/copilotkit/the-developers-guide-to-generative-ui-in-2026-1bh3 | 2026 |
| D38 | Thesys OpenUI Lang 基准；Verygood Ventures GenUI 基准 | https://mer.vin/2026/05/openui-lang-mit-generative-ui-that-cuts-llm-output-tokens-versus-json/ ；https://verygood.ventures/resources/genui-benchmarks/ | 2026-05 |
| D39 | Apple WWDC25 session 286；WWDC26 FM 二手综述 | https://developer.apple.com/videos/play/wwdc2025/286/ ；https://dev.to/hariharanjagan/whats-new-in-apples-foundation-models-framework-at-wwdc-2026-5227 | 2025-06；2026-06 |
| D40 | 中国日报：小艺与意图框架 | https://cn.chinadaily.com.cn/a/202512/25/WS694ce5b7a310942cc49988c2.html | 2025-12-25 |

---

## 待核实清单

1. glTF KHR_gaussian_splatting 2026-09-03 是否已 Ratified（只有 radiancefields，需查 KhronosGroup/glTF 扩展注册表提交记录）；SPZ 压缩扩展是否对应 SPZ 4。
2. Apple RealityKit GaussianSplatComponent 页面直接抓取 404，内容来自检索摘要；需在 Apple 文档站复核，并确认 iOS 27 是否有高斯 API。
3. iOS 26 Spatial Scenes 是否基于高斯：仍未找到公开资料。
4. Google Maps 室外 Immersive View 是否使用高斯（Google 未确认）。
5. 鸿蒙 HarmonyOS 7 端侧 3DGS 的官方文档；国内手机相册 / 淘宝 / 京东 3D 商品是否用高斯：未找到公开资料。
6. Snap 拥有 PlayCanvas 一说（来自检索摘要对 Snap 文档的转述），需确认收购时间。
7. Coherent Market Insights 的 CAGR 与端点矛盾，如需引用需读原报告。
8. Photoshop 80 万 SPZ 文件为 Niantic 自报；SPZ 4 发布日期 5 月 5 日与 11 日不一致。
9. 小米 XRING O3 是否真的使用 G2-Ultra NX（与 Arm 官方时间线冲突）；Neural Dawn 是否已上线。
10. 国内厂商超帧 / 插帧的功耗与延迟：均无独立实测，iQOO Q 系、一加 P4 究竟承担超分、插帧还是仅显示处理，官方未披露；荣耀 NPU 超帧的游戏名单未找到。
11. Pixelworks 出售 PWSH 的买方后续是否继续向 OEM 供货；10-Q 中 RMB 数字的单位。
12. 天美 / 光子 / 米哈游与厂商的适配名单与联合实验室：未找到公开资料；《王者荣耀》165 帧仅为传闻。
13. 手机端 MetalFX 插帧官方耗时与功耗；Sony PSSR 2026 年资料：未找到公开资料。
14. Character.AI 破产的案卷原文（cases.stretto.com/chartech）与 404 Media 关于算力支出、月收入峰值的原始报道；Disney 出价条款。
15. MiniMax 招股书中 Talkie 单独收入与国内星野收入拆分；2026 年星野 / 猫箱月活。
16. 办法正式版条文原文与征求意见稿的逐条差异；「系统内置形象」是否属于适用范围。
17. 纽约 S 9051 的真实状态；EU AI Act 对陪伴机器人的处理。
18. Grok Companions 是否已下线 3D 模式（x.ai 官方公告）。
19. Apple 桌面机器人 / 动画 Siri 仍是传闻；郭明錤与 Gurman 时间线不一致。
20. A2UI v1.0 发布时间、Android Compose A2UI Renderer 的状态与日期；MCP Apps 并入 2026-07-28 规范一说；OpenAI Apps SDK 与 Plugins 的命名关系；Vercel AI SDK 当前生成式 UI 方案。
21. Apple WWDC26 Foundation Models 流式部分结果 API（PartiallyGenerated）官方页；HarmonyOS 是否有 AI 生成界面：未找到公开资料。
22. 生成式 UI 在手机端的首屏时延、掉帧、WebView 内存基线与独立用户研究：未找到公开资料。

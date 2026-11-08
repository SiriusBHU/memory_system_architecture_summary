# 原型对比：C1 推理
> 2026-11-07；检索：WebFetch 2 / WebSearch 0（其余证据取自 C1 文档与 C1a、C1b、kimi-delta-C1 笔记）；列的取舍：按候选清单取 5 列，学术侧取 LLMS 与 Agent.xpu（前者代表系统服务内的 KV 管理，后者代表异构多负载调度），未替换候选。

图例：● 已具备　◐ 部分具备　○ 缺失　— 不适用。编号 A/B/K 沿用 C1 文档 §8；P1、P2 为本轮新增，见 §4。「未核」表示该格靠常识或单源，未取得一手页面。

## 1 对比表

| 要素 | Android AICore + NPU Manager | Apple Foundation Models（含 AFM 3） | Windows ML / Copilot+ 运行时 | HarmonyOS 端侧大模型服务 | vLLM / SGLang（云端参照） | 学术：LLMS | 学术：Agent.xpu |
|---|---|---|---|---|---|---|---|
| **简介** | Google；AICore 持有 Gemini Nano，Android 17 增系统服务 NPU Manager；量产 | Apple；系统模型是 LanguageModel 协议的一种实现，WWDC26 加入 AFM 3 稀疏模型 | Microsoft；Windows ML 共享运行时加 EP，Phi Silica 预装于 NPU；PC 形态 | 华为；小艺加意图框架，NNRt 为 NPU 北向接口；会议口径多 | 开源云端推理引擎；连续批处理、PagedAttention、前缀缓存 | 北大；把 LLM 作为移动系统服务，KV 分块压缩与换入换出；2024，原型 | 北大；NPU 与 iGPU 协同加细粒度抢占，面向 Agent 负载；2025，原型 |
| **1 系统级共享模型服务** | ●　单底座多应用共享　[A2][A5] | ●　系统模型可被 App 共用，且可换第三方实现　[A11][A13] | ●　Phi Silica 系统预装，需 LAF 解锁　[A19][A20] | ◐　小艺作底座，第三方 API 与配额无文档　[A29]（媒体口径） | ●　一个服务进程服务多客户端　（未核） | ●　提出 LLM 即系统服务　[P1] | ○　只做调度，不涉及服务形态　[A26b] |
| **2 多会话调度与优先级** | ◐　前台限制加配额，并发返回 BUSY 不排队；NPU 三档优先级　[A2][K1] | ◐　调度策略未披露　[A11] | ○　未见公开调度语义　（未核） | ○　NNRt 并发取决于驱动，仅同步推理　[A22] | ●　连续批处理、优先级调度　（未核） | ◐　以上下文切换为目标，调度细节页面未载　[P1] | ●　区分 reactive 与 proactive 任务　[A26b] |
| **3 抢占粒度** | ◐　模型级：要求客户端卸载，任务可 PAUSED　[K1] | ○　未披露　[A11] | ○　未见　（未核） | ○　未见　[A22] | ◐　请求级抢占（换出或重算）　（未核） | ○　不做算力抢占，只管上下文切换　[P1] | ●　算子 / 内核级细粒度抢占，reactive 延迟降至少 91%（自报）　[A26b] |
| **4 异构算力路由** | ◐　NPU 内有准入；CPU/GPU/NPU 不统一，官方 GPU 路径为主　[K1][B3] | ◐　Core AI 在 ANE 与 GPU 间特化　[A13] | ◐　EP 按设备选 CPU/GPU/NPU，非阶段级　[A15][A16] | ◐　NNRt 对接 NPU，无统一路由　[A22] | — 　GPU 集群　 | ○　未涉及　[P1] | ●　NPU 与 iGPU 协同，按负载划分　[A26b] |
| **5 前缀与 KV 复用、持久化** | ◐　显式 Prefix Caching，存应用私有存储，不跨应用　[A6] | ◐　cached token 计数；系统提示 KV 是否复用未核　[A11] | ○　未见　（未核） | ○　未见　（待核） | ●　前缀缓存（RadixAttention 等）、跨请求共享　（未核） | ●　KV 跨调用持久，分块管理　[P1] | ○　摘要未见　（未核） |
| **6 多适配器驻留与热切换** | ◐　Google 自训功能 LoRA，不开放第三方　[B12] | ◐　第三方适配器约 160MB，绑定单一底座版本　[A14] | ◐　第三方 LoRA，换底座须重训　[A20] | ○　未见　（待核） | ●　多 LoRA 并发，运行时加载 / 卸载接口，官方警告仅限可信环境　[P2] | ○　未涉及　[P1] | ○　未涉及　（未核） |
| **7 端云路由与隐私控制** | ◐　Private AI Compute 用于重任务，细则未披露　[B1] | ◐　统一 API 含端侧、PCC、第三方；PCC 有证明与透明日志　[B8][B31] | ○　未见系统级端云路由　（未核） | ◐　媒体称 OHTTP 匿名，无官方文档　[A29] | — 　纯云　 | ○　未涉及　[P1] | ○　未涉及　[A26b] |
| **8 计量与配额** | ◐　电量配额，短长两窗口；NPU 归账字段　[A2][K1] | ◐　usage 含 cached token；无配额文档　[A11] | ○　未见　（未核） | ○　未见　（待核） | ◐　token 级统计与限速，多租户配额依部署　（未核） | ○　不涉及　[P1] | ○　不涉及　[A26b] |

## 2 读表结论

1. **已普遍做成：系统级共享底座与会话级前缀状态。** 三大平台均有单底座多客户端服务（要素 1），Android 与 Apple 还提供会话级缓存接口 [A6][A11]。
2. **普遍缺失：跨应用 KV 共享与适配器跨版本兼容。** 端侧产品的缓存都落在应用私有存储或会话内，没有跨应用共享（要素 5）；适配器全部绑定底座版本（要素 6）。
3. **只有云端或论文做成的：** 细粒度抢占（Agent.xpu）、KV 持久化加分块换页（LLMS）、多适配器并发与运行时加载（vLLM）、前缀缓存的跨请求共享。产品侧最强的抢占是 NPU Manager 的模型级卸载 [K1]。
4. **端云差距：** 云端的调度、批处理、计量是一等公民；端侧产品用「前台限制 + 配额 + BUSY」做粗粒度准入。端云路由在端侧产品里是开发者选择或厂商黑盒，没有公开的自动路由。
5. **学术领先产品之处：** 抢占粒度（算子级）、异构协同（NPU+iGPU）、状态持久化与分块 KV。弱点是两者都是原型，且主要评测基线是旧版开源框架（C1 §3 Q4 对 NPU 收益的类似质疑）。
6. **计量与配额是最空的一行。** 手机上无公开的每 token 能耗计量；配额单位以电量命名，只有 Android 有迹可循。HarmonyOS 整列多为「待核」，结论不应被读成「缺失」，而是证据不足。

## 3 格子说明（◐ 与争议格）

- **Android 要素 2、3：** NPU Manager 官方页给出准入、三档优先级、`onRequestUnloadModel`，未给时延上限或时间片；是否与 AICore 配额打通无资料 [K1]。
- **Android 要素 4：** LiteRT 对 NPU 按 SoC 预编译产物；官方 Gemma 4 手机行只列 CPU 与 GPU，NPU 路径未成默认 [A9][B3]。
- **Apple 要素 5：** `usage` 里的 cached token 计数说明有前缀缓存在运行，但是否跨请求复用系统提示 KV 未核 [A11]（C1 待核实 6）。
- **Apple 要素 6：** 适配器 160MB 为工具包口径，2024 技术报告口径为数十 MB，二者指代不同 [A14]。
- **Windows 要素 4：** EP 机制是「按硬件选执行提供程序」，不是 prefill/decode 阶段级路由；选择策略细节未取一手页面 [A15][A16]。
- **HarmonyOS 整列：** 小艺开放程度来自会议报道转引，无 API 文档；NNRt 限制取自 OpenHarmony 文档（56 个算子、同步推理）[A22][A29]。
- **vLLM / SGLang 要素 2、3、5、8：** 凭已知功能填写，本轮未抓一手页面，SGLang 的适配器写入缓存键亦为 Kimi 单源 [P2]（LoRA 页只确认了多 LoRA 与运行时加载及风险警告）。
- **LLMS 要素 2：** 摘要未描述调度与多应用共享，不能据此判定缺失，仅标 ◐ 的依据是「以多次调用间上下文切换为目标」[P1]。
- **Agent.xpu 要素 5：** 摘要来源未提 KV 复用，标 ○ 仅表示未见 [A26b]。

## 4 参考资料

| 编号 | 标题 | 机构/作者 | URL | 日期 | 核验情况 |
|---|---|---|---|---|---|
| A2、A5、A6、A9、A11、A13、A14、A15、A16、A19、A20、A22、A26b、A29 | 沿用 C1 文档 §8 | Google / Apple / Microsoft / OpenHarmony / 北大 / 媒体 | 见 `proposals/agentos-components/C1-推理框架与推理能力.md` §8 | 各自 | 沿用 C1 文档的核验结论，本轮未重抓 |
| B1、B3、B8、B12、B31 | 沿用 C1 文档 §8 | 同上 | 同上 | 各自 | 同上 |
| K1 | NPU manager | Google AOSP | https://source.android.com/docs/core/perf/npu-manager | 2026-06 | C1 文档已抓取 |
| P1 | LLM as a System Service on Mobile Devices（LLMS） | Wangsong Yin、Mengwei Xu、Yuanchun Li、Xuanzhe Liu | https://arxiv.org/abs/2403.11805 | 2024-03-18 | 本轮已抓 abs 页；页面标注 Technical Report，未载会议名 |
| P2 | vLLM LoRA Adapters 文档 | vLLM 项目 | https://docs.vllm.ai/en/latest/features/lora.html | 抓取于 2026-11-07 | 本轮已抓；确认多 LoRA、`/v1/load_lora_adapter`、运行时加载仅限可信环境 |

## 5 待核实

1. LLMS 的发表信息：Kimi 称 SenSys 2026，本轮 abs 页未载，仍为单源（kimi-delta-C1 A5）。
2. Windows ML 的多会话调度、配额与端云路由是否存在公开文档。
3. HarmonyOS 的适配器、KV 复用、计量、端云路由，以及小艺对第三方的 API 与配额。
4. vLLM / SGLang 的前缀缓存、优先级调度、多租户配额：本轮未取一手页面。
5. Agent.xpu 是否涉及 KV 复用或持久化；其评测基线版本。
6. Apple 是否跨请求复用系统提示 KV；AFM 3 的调度与抢占行为。
7. 是否用 EdgeLoRA（多租户 LoRA 服务，arXiv 2507.01438，C1 文档 B27）替换或补充一列，作为端侧多租户的第二个学术点。

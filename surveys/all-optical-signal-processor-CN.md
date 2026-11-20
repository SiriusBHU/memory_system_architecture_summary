# 全光信号处理器（OSP）：Tb/s 级光域实时均衡

> 论文笔记 + 产业成熟度评估。对象：Wang Benshan 等，"An all-optical signal processor enabling terabit-per-second real-time equalization"，*Science*，2026-06-11，DOI [10.1126/science.ady5344](https://doi.org/10.1126/science.ady5344)。
> 调研日期：2026-11-16。Science 正文未能直接获取，技术细节主要依据同组预印本 [arXiv 2504.15044 v1](https://arxiv.org/html/2504.15044v1)（2025-04），正式版可能有改动；凡推断或未核实处标注「待核实」。

## 0. 一句话结论

用一块纯波导的硅光芯片，在光信号转成电信号之前完成均衡，演示了 8 个波长 × 200G = 1.6 Tb/s 的 IM/DD 链路。学术上是顶刊级的原理突破；产业上仍处于实验室原理验证阶段（判断约 TRL 3–4），论文作者全部来自高校，未检索到工业界合作方、衍生公司或产品计划。

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 期刊 / 日期 | *Science*，2026-06-11（CUHK 新闻稿日期 2026-06-15） |
| 通讯作者 | 黄超然（Huang Chaoran），香港中文大学电子工程系助理教授 |
| 第一作者 | Wang Benshan；共同第一作者 Xiao Qiarong |
| 合作单位 | 华中科技大学武汉光电国家研究中心（董建绩）、复旦大学（张俊文）；CUHK 孔秋强（Kong Qiuqiang，仅见于正式版新闻稿，arXiv v1 作者列表中没有） |
| 工业界合作方 | 无 |
| 对应预印本 | arXiv 2504.15044，"Beyond Terabit/s Integrated Neuromorphic Photonic Processor for DSP-Free Optical Interconnects"（作者、指标与 Science 版一致，判断为同一工作的早期版本） |

## 2. 要解决的问题

- **背景**：生成式 AI 训练正在跨多个数据中心分布，需要统一、低时延、低能耗的互连。论文引用的数字：GPU 间链路约 30 pJ/bit，网络成本约 1–2 美元/Gbps。
- **IM/DD 的根本限制**：数据中心短距光互连用强度调制/直接检测（IM/DD），光电二极管只检测光强，相位丢失。光纤色散在平方律检测之后变成不可逆的频谱凹陷（功率衰落），电域 DSP 补不回来。
- **DSP 的规模化瓶颈**：速率越高，DSP 需要的抽头越多，功耗和时延越高。作者举例：Marvell 3nm 的 Ara 1.6T PAM4 DSP（8×200G），在 O 波段边缘波长上做 112 Gbaud PAM4，也只能传约 2 km。
- **作者对 DSP 的估算**（非实测，待核实）：100 Gbaud PAM4 下 DSP 最佳时延约 0.8 µs（只算串并转换）；800 抽头 FFE 在 3nm 下至少 37.5 W（不含 SerDes）。
- **此前光子处理器的不足**：实验最高约 40 Gbaud/λ（仿真 60 Gbaud/λ），很多依赖数字预处理/后处理、需要高速 ADC 的数字读出层，或只能固定速率与波长。

## 3. 方案：深度时延储备池计算

整体是一个复数值、深度时延储备池计算（reservoir computing）结构：三级级联储备池 + 光子读出层，芯片上只有波导，没有激光器、调制器或微环。

- **去掉输入层**：传统储备池的数字输入掩模在 100 Gbaud 以上会成为瓶颈，作者直接去掉，改由深度储备池把输入投射到更高维的时域空间。
- **三级储备池**：每级是一个带反馈的延时环，设计延时约 18 ps、36 ps、9 ps（延时线长 1270 / 2540 / 640 µm）。反馈强度由 MZI 耦合器调节，环内移相器使储备池成为复数值。第一、二级按 2:1、1:1 分出支路送往下一级，各支路经 MZI + 移相器加权后合路。
- **读出层**：合路信号分成 8 路，延时间隔约 5 ps（350 µm），每路一个复数权重（MZI + 移相器），合路后送进单个光电二极管。
- **非线性**：来自光电二极管的平方律检测 |·|²，芯片上不需要专门的光学非线性器件。
- **可调参数**：共 28 个微加热器移相器，各自独立训练；π 相移约 25 mW，训练电流上限 13 mA。
- **训练**：在线训练加热器电流，用粒子群算法（PSO）。论文一处说目标是最小化 BER，另一处说代价函数是 OSP 输出与发送符号的 MSE，前后表述不一致。训练好的 OSP 近似整个信道响应（光纤 × 收发器）的逆，线性与非线性失真在同一模块里一起处理。
- **工艺与封装**：商用 SOI 硅光代工，Ti/W 加热层 + Al 布线层；全刻蚀波导 500 nm 宽、220 nm 厚；纳米锥边缘耦合器（模场半径 2.5 µm）；总波导长约 4000 µm（对应约 57 ps 传播时间）；用方形延时环代替螺旋以降低辐射损耗，深槽抑制热串扰；芯片打线到带 TEC 和热敏电阻的 PCB。论文未给出芯片总面积。

**核心技术点**：均衡发生在光电转换之前，处理的是完整光场，相位还在。所以它能在色散被平方律检测"锁死"之前把它补掉，这是电域 DSP 做不到的。

## 4. 实验设置

- **发射端**：约 1550 nm 可调激光器，256 GSa/s 任意波形发生器，电放大器，40 GHz 薄膜铌酸锂（TFLN）强度调制器；无预加重；升余弦（RRC）成形，滚降 0.05。
- **光纤**：5 km 标准单模光纤（G.652D），C 波段，0.2 dB/km；1550 nm 处色散约 85 ps/nm（1540–1565 nm 为 82–90 ps/nm）。作者称"相当于 O 波段 80 km 以上"，但这只是按色散总量折算，未在 O 波段实测。
- **接收端**：EDFA → 可调衰减器 → OSP 芯片 → 100 GHz 可调滤波器 → 70 GHz 光电二极管 → 256 GSa/s 实时示波器，每符号一个采样计 BER。
- **测试项**：56–112 Gbaud 的 OOK 和 PAM4；8 个 WDM 通道（400 GHz 间隔，1540–1565 nm）× 100 Gbaud PAM4。训练用 2¹⁶ 个 PRBS 符号中的 2¹⁵ 个，其余用于验证。
- **"DSP-free"的边界**：背靠背路径里保留了一个固定抽头的小 FFE，用于处理收发器带宽限制，OSP 工作时其抽头不变。

## 5. 结果

| 指标 | 数值 |
|---|---|
| 单通道 | 100 Gbaud PAM4（200G）与 112 Gbaud OOK 的误码率低于 HD-FEC 门限；112 Gbaud PAM4 达到 SD-FEC 门限；不经 DSP 眼图张开 |
| 训练收敛 | 100 Gbaud 信号的 BER 从训练前 >10⁻¹ 降到约 10⁻³，约 100 个 epoch |
| 多波长 | 8 个波长，合计 1.6 Tb/s；逐波长单独训练时全部低于 HD-FEC |
| 单片共用 8 波长 | 只在 1550 nm 训练时，其余通道有残余损伤，全部低于 SD-FEC，性能与单独优化的 DSP 相当或更好 |
| 光处理 + 少量 DSP | 每通道后接不到 30 抽头的 DSP，全部通道低于 HD-FEC；纯 DSP 需要 800+ 抽头（1562.2 nm 处 965 抽头），也只到 SD-FEC |
| 非线性场景（100 Gbaud PAM4，5 km） | Q 因子 8.51 dB，比 885 抽头 FFE 高 1.88 dB，比 256×256×1 前馈神经网络均衡器高 0.85 dB；能多承受 2 dB 发射功率 |
| 时延 | 约 57 ps，即光走过芯片的时间，与速率无关 |
| 功耗 | 108 mW，主要是微加热器；单通道 0.54 pJ/bit；8 通道均摊为 67.5 fJ/bit（即新闻稿所说的"数十 fJ/bit"） |
| 远期功耗预测 | 换成 BTO 或 MEMS 低功耗移相器可达亚 fJ/bit，非易失 MEMS 情形 0.27 fJ/bit（本文未演示） |
| WDM 带宽 | Science 版新闻稿称"有潜力"把受色散限制的 WDM 可用带宽扩展 6.8 倍（表述为潜力，非演示结果） |

## 6. 需要打折看的地方

1. **"1.6 Tb/s 实时"**：arXiv v1 的发射端只有一个可调激光器和一个调制器。据此推断 8 个波长是逐个测完再合计的，不是 8 路同时加载（推断，Science 正式版是否改为并发 WDM 测试待核实）。另外，单片芯片共用 8 个波长时，没单独优化的通道只能达到 SD-FEC，要么逐波长单独训练，要么后接一小段 DSP。
2. **"千倍节能"**：对比对象是作者估算的 800 抽头 FFE（约 37.5 W，且不含 SerDes），而真实的 1.6T 光模块整机约 25–30 W。主流 O 波段 2 km 场景本来用不到 800 抽头，大抽头数是 C 波段 5 km 这个设定逼出来的，所以千倍的比值只在该设定下成立。OSP 一侧只算了加热器功耗；弥补约 15 dB 插损所需的 EDFA、TEC 温控、偏振控制和训练控制电路，论文都没有说明是否计入（论文指向的补充材料 Note 4/5 未获取，待核实）。
3. **"14000 倍时延优势"**：DSP 的 0.8 µs 是作者推算值，不是商用芯片实测。OSP 只替代了"均衡"这一环，链路上的时钟恢复（CDR）和 FEC 照样要有，端到端时延收益远小于 14000 倍。
4. **"相当于 80 km O 波段"**：只是色散总量折算；O 波段的损耗与非线性没有纳入。

## 7. 产业成熟度

### 7.1 尚未解决的工程问题

- **插损约 15 dB**：其中每个光纤-芯片边缘耦合器约 6 dB。实验靠 EDFA 补，而数据中心光模块里放不下 EDFA。作者提出的片上集成探测器（省掉一个耦合器）和 III-V/硅 SOA 都还没实现。
- **偏振敏感**：实验用了偏振控制器匹配芯片偏振。真实光纤里偏振态随机漂移，工程化需要偏振分集设计，结构与训练都会复杂一倍（本条为我的分析，论文未讨论）。
- **训练闭环**：PSO 依赖实验室示波器测 BER，训练耗时未报告；论文虽称可"适应动态传输条件"，但没有讨论在线自适应、温漂、老化和重训练成本。
- **调谐功耗**：热光加热器是主要功耗来源；低功耗移相器（BTO/MEMS）方案只是预测。
- **标准与生态**：要进入 IEEE 802.3dj / OIF 体系，需要与 FEC（如 KP4）、CDR、主机 SerDes 配合。论文没有工业界合作方。

### 7.2 产业主线在用别的办法解决同一问题

- **回避色散**：主流数据中心 IM/DD 走 O 波段，≤2 km（DR/FR）或 10 km（LR），色散小，DSP 用较少抽头即可。3nm 的 1.6T PAM4 DSP 已出货或量产在即：Marvell Ara（宣称模块功耗降低 20% 以上）、Credo Cardinal 800（224G/lane，产品简报 2026-03）、Acacia Kibo（2025-03 发布）。1.6T DSP 模块整机约 25–30 W（二手资料数据）。
- **直接去掉 DSP**：
  - LPO（线性直驱光模块）把均衡交给交换芯片 SerDes。800G 已商用；Marvell 在 OFC 2025 展示 1.6T LPO，含激光器功耗低于 5 pJ/bit。1.6T LPO 的出货量未查到。
  - CPO（共封装光学）：Nvidia 在 GTC 2025 发布 Quantum-X Photonics（InfiniBand，2026 年初）和 Spectrum-X Photonics（以太网，2026 年下半年；1.6 Tb/s/端口）。有二手报道称 Spectrum-X Photonics 已于 2026-01 量产、单端口功耗从约 25 W 降到 9 W，来源质量较低，未能用 Nvidia 一手资料核实（待核实）。
  - 在 ≤2 km 场景下，OSP 正面对上的是这两条已经产业化的路线。
- **更长距离**：目前要么上相干光通信（coherent-lite / ZR，成本高），要么降速。

### 7.3 OSP 的生态位

- **C 波段几公里到几十公里的 IM/DD**：园区或城域数据中心互连，正是色散卡住 IM/DD、上相干又嫌贵的区间。
- **O 波段多波长扩展**：3.2T/6.4T 往更多波长扩时，远离零色散点的边缘波长受色散限制，即 Science 版"WDM 可用带宽扩展 6.8 倍"所指的方向。
- **相邻成熟技术**：光域色散补偿本身不新，色散补偿光纤（DCF）和光纤布拉格光栅（FBG）可调色散补偿器在 10G 时代的长途网络里大规模商用过，但那些是固定或简单可调的线性补偿。这篇的新意在于可编程、可训练、集成在硅光上，并且把色散、带宽受限和非线性一起处理。

### 7.4 同类研究

- 比利时根特大学 / imec 的 Peter Bienstman 组长期做光子储备池均衡。2026-04 预印本描述了 16 节点空分复用储备池 + 片上可编程读出 + 共封装接收前端，号称首个共封装光子储备池接收机，并首次在固定集成电路上演示波特率与距离可变的均衡（[arXiv 2604.20504](https://arxiv.org/html/2604.20504v1)）。
- 同组另有 2025-03 的硅光循环网络全光均衡工作（[arXiv 2503.19911](https://arxiv.org/html/2503.19911v1)）。
- 均未检索到相关初创公司、融资或产品。

### 7.5 判断

- 这是顶刊级的原理突破，但离产品至少还有 5 年以上（判断，非事实）。
- 更可能的落地形态是"光域预均衡 + 轻量 DSP"的混合方案，先用在长距 IM/DD 这类细分场景，不太可能替代主流模块里的 DSP。
- 值得跟踪的信号：
  1. 片上集成放大器或探测器，把插损问题解决；
  2. 偏振无关版本；
  3. 在线自适应训练闭环（模块内低速监测 + 控制器）；
  4. 出现光模块厂商或交换芯片厂商合作。

## 8. 来源

- 论文正式版：Wang B. et al., *Science* (2026), DOI [10.1126/science.ady5344](https://doi.org/10.1126/science.ady5344)（正文未获取）
- 预印本：[arXiv 2504.15044 v1](https://arxiv.org/html/2504.15044v1)，"Beyond Terabit/s Integrated Neuromorphic Photonic Processor for DSP-Free Optical Interconnects"
- [CUHK 新闻稿（2026-06-15）](https://www.cpr.cuhk.edu.hk/en/press/cuhk-develops-all-optical-signal-processor-to-break-ai-data-centre-transmission-bottleneck-delivering-1-6-tb-s-throughput-and-sub-60-picosecond-latency-to-enable-green-ai-supercomputing/)
- [EurekAlert 新闻稿](https://www.eurekalert.org/news-releases/1132164)
- [Electronic Design：Marvell 3nm 光 DSP](https://www.electronicdesign.com/technologies/communications/wired/article/55292368/electronic-design-marvell-meets-ais-need-for-speed-with-3-nm-optical-dsp-for-data-centers)
- [Converge Digest：Marvell 1.6T 硅光 LPO](https://convergedigest.com/marvell-unveils-1-6t-silicon-photonics-pluggable/)
- [Converge Digest：Acacia Kibo 1.6T DSP](https://dev.convergedigest.com/?p=101202)
- [Credo Cardinal 800 产品简报](https://credosemi.com/wp-content/uploads/Cardinal.800.Product-Brief.3.23.2026.pdf)
- [The Network DNA：1.6T 以太网与光网络指南](https://www.thenetworkdna.com/2026/10/16t-ethernet-and-optical-networking.html)（二手资料）
- [Tom's Hardware / Yahoo：Nvidia 硅光与 CPO 路线](https://tech.yahoo.com/ai/articles/nvidia-outlines-plans-using-light-135756771.html)
- [Converge Digest：Nvidia Spectrum-X / Quantum-X Photonics](https://convergedigest.com/?p=101038)
- [Ghent/imec 共封装光子储备池接收机预印本 arXiv 2604.20504](https://arxiv.org/html/2604.20504v1)
- [Ghent/imec 硅光循环网络全光均衡预印本 arXiv 2503.19911](https://arxiv.org/html/2503.19911v1)

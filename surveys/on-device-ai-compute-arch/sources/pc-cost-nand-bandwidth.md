# PC 端侧 AI 成本核算：闪存带宽、每 die 吞吐与能耗（NB 系列来源）

> **用途**：给「PC 上把 200B MoE（FP4 专家约 100 GB）放在闪存、每轮 prefill 全量流一遍权重」方案做成本与可行性核算，回答「拿到 30 / 60 / 117 GB/s 持续读带宽需要多少颗 NAND die、多大总容量、什么接口、多少瓦」。
> **调研日期**：2026-10-14。**来源编号**：NB-S1、NB-S2……（见第 10 节）。
> **标注约定**：每个数字标「性质」（实测 / 规格 / 推算）与「置信度」（高 / 中 / 低）。
> - **实测**：第三方评测用仪器测得（如 TechPowerUp 用 Quarch 功率模块只测盘功耗）。
> - **规格**：厂商 datasheet、新闻稿或 ISSCC 论文给出的标称值。
> - **推算**：本文按公式算出，公式写在旁边。
> - **高**：一手厂商资料直接给出，或多个来源一致。**中**：权威第三方数据库或媒体报道，或一手资料但测试口径不明。**低**：推算链条长、只有单一来源，或各来源口径冲突。
> 查不到的写「未找到」。本文只收集和推算，不修改主文档里的数字。

---

## 0. 结论速览

1. **普通 3D TLC NAND 每颗 die 的持续顺序读约 1.6–1.9 GB/s**（当代 4–6 plane、tR 32–61 µs、16 KiB 页）。Micron G9（6 plane、tR 32 µs）理论上约 3.1 GB/s，但客户端 SSD 里还没有被验证过，因为 8 颗 die 就已经把 PCIe 5.0 x4 跑满了。
2. **HBF 每颗 die 约 100 GB/s**（SanDisk Gen-1：1.6 TB/s ÷ 16 die），是普通 NAND die 的 **33–62 倍**。它靠的是三件事：每 die 约 25 个 plane、4 KiB 页读延迟约 1 µs（普通 NAND 是 32–61 µs）、TSV 宽接口取代 8 bit 通道总线。另外，**HBF 每 die 只有 256 Gb（32 GB）**，本地两篇文档写成「256 GB/die」，属于单位错误（见第 9 节）。
3. **带宽由 die 数决定，die 数又锁定了最小容量。** 用 1 Tb（128 GB）的 die：30 GB/s 需要 17–19 颗，至少约 2.2–2.4 TB；60 GB/s 需要 33–37 颗，至少约 4.2–4.7 TB；117 GB/s 需要 63–72 颗，至少约 8.1–9.2 TB。这相当于按 100 GB 模型超配 **20–90 倍**容量。die 容量还在往 2 Tb 走，同样带宽对应的容量会再翻倍。
4. **客户端 PCIe 5.0 SSD 满速读的能耗是 0.42–0.71 nJ/B**（规格）/ **0.49–0.70 nJ/B**（TechPowerUp 实测，只算盘功耗），和主文档假设的 0.5 nJ/B 吻合。按 0.5 nJ/B 算，三档功耗为 **15 / 30 / 58.5 W**；按实测区间算为 **14.6–21 / 29–42 / 57–82 W**。
5. **系统主 SSD 只能勉强覆盖电池档（30 GB/s）**：
   - 1–2 TB 的 PCIe 5.0 x4 盘上限 14.9 GB/s，只有电池档的一半。
   - 2 TB 的 PCIe 6.0 x4 盘约 28 GB/s，可达电池档的 93%。但客户端 PCIe 6.0 盘最早要 2028–2030 年。
   - 60 / 117 GB/s 两档需要 3–5 块 PCIe 6.0 x4 盘（或 5–9 块 PCIe 5.0 x4 盘）、12–36 条 PCIe 通道、4–10 TB 总容量，超出笔记本平台的能力。

---

## 1. 口径与公式

| 符号 | 含义 | 取值 / 说明 |
|---|---|---|
| B | 目标持续读带宽 | 电池档 30 GB/s，中间档 60 GB/s，插电档 117 GB/s（来自主方案的功耗封顶推导，本文不质疑） |
| W | 每轮 prefill 流过的权重 | 约 100 GB（200B MoE，FP4 专家） |
| e | 闪存每字节读能耗 | 主文档假设：UFS 系统级约 0.5 nJ/B |
| b_die | 每颗 die 的持续顺序读吞吐 | 第 2 节 |
| P_page | 页大小 | 16 KiB = 16384 B（TechPowerUp 数据库对 V8 / BiCS8 / B58R / B68S / V8 D-die 均记为 16 KB，NB-S1 至 NB-S5） |

- **每 die 阵列受限吞吐**：b_array = N_plane × P_page ÷ tR。
- **每 die 有效吞吐**：b_die = min(b_array, 通道接口速率 ÷ 该通道上同时活跃的 die 数)。8 bit 通道下，MT/s 在数值上等于 MB/s。
- **所需 die 数**：N_die = ⌈B ÷ b_die⌉。**最小容量**：C_min = N_die × 单 die 容量。
- **闪存读功耗**：P = e × B，nJ/B 与 W/(GB/s) 在数值上相等。
- **单轮时间**：t = W ÷ B。**单轮能耗**：E = W × e，与带宽无关。100 GB × 0.5 nJ/B = **50 J/轮**。

---

## 2. 每 die 吞吐：最新 3D NAND 参数

### 2.1 Die 参数表

| Die（代际） | 层数 | 单 die 容量 | Plane 数 | 页 | tR | 接口速率 | 阵列受限吞吐（推算） | 性质 / 置信度 | 来源 |
|---|---|---|---|---|---|---|---|---|---|
| Samsung V8（236L TLC，B-die） | 236 | 1 Tb（另有 512 Gb 版本） | 4 | 16 KB | 40 µs | 2400 MT/s（Toggle 5.0） | 4×16384/40µs = **1.64 GB/s**；Samsung 自述每 die 平均读 **1640 MB/s** | 数据库记录（含 Samsung 自述）/ 中高 | NB-S2，NB-S7 |
| Kioxia/SanDisk BiCS8（218L TLC，CBA） | 218 | 1 Tb | 4 个逻辑 plane（数据库注：物理 8 个子 plane，WL 8 KB） | 16 KB | 40 µs | 3600 MT/s（Toggle 5.1） | 4×16384/40µs = **1.64 GB/s** | 数据库记录 / 中 | NB-S1，NB-S5 |
| Micron B58R（232L TLC） | 232 | 1 Tb | 6 | 16 KB | 61 µs（数据库标注 tPROG 为估计值；tR 未注明是否估计） | 2400 MT/s | 6×16384/61µs = **1.61 GB/s**（数据库记 die 读 1574 MB/s） | 数据库记录 / 中 | NB-S3 |
| **Micron G9 B68S（276L TLC）** | 276 | 1 Tb | 6 | 16 KB | **32 µs** | **3600 MT/s**（Micron 称业界最高 I/O 3.6 GB/s） | 6×16384/32µs = **3.07 GB/s**（低于 3.6 GB/s 接口上限） | tR / plane 为数据库记录（中）；3.6 GB/s 为规格（高）；吞吐为推算（中） | NB-S4，NB-S15 |
| Micron G9（厂商相对值） | — | — | — | — | — | — | Micron 称每 die 读带宽比「现有竞品」高 **88%**、写带宽高 **99%**（2024-07-30） | 规格（相对值）/ 中 | NB-S15 |
| SK hynix V8 D-die（238L TLC） | 238 | 512 Gb | 4 | 16 KB | 未找到 | 2400 MT/s | 未找到 tR，无法推算 | 数据库记录 / 中 | NB-S5 |
| SK hynix 321L TLC（V9） | 321 | 1 Tb | 未找到 | 未找到 | 未找到绝对值；读性能比 238L 高 **13%** | 未找到绝对值；传输速度比 238L 高 **12%** | 未找到 | 规格（相对值，2024-11-21）/ 中 | NB-S16 |
| SK hynix 321L QLC | 321 | **2 Tb** | **6**（由 4 增至 6） | 未找到 | 未找到 | **3200 MT/s**（Notebookcheck） | 未找到 tR；厂商称传输速度 **2 倍**、读性能 **+18%**（对比上一代 QLC） | 规格（2025-08-25）/ 中 | NB-S17 |
| Samsung V9（TLC） | 未公布（传约 290 层） | 1 Tb | 未找到 | 未找到 | 未找到 | 3200 MT/s（Toggle 5.1，比 V8 快 33%） | 未找到 | 规格（2024-04-23）/ 高（接口），层数低 | NB-S18 |
| Samsung V10（4XX 层 TLC，ISSCC 2025 论文 30.1） | 400+ | 1 Tb，28 Gb/mm² | 未找到 | 未找到 | 未找到 | **5600 MT/s**（5.6 Gb/s/pin） | 未找到 | 规格（论文标题）/ 高 | NB-S19 |
| Kioxia/SanDisk BiCS10（332L TLC，ISSCC 2025 论文 30.2） | 332 | 1 Tb，29 Gb/mm² | **4**（纵向排布） | 未找到（本文假设 16 KiB） | 比上一代缩短 4 µs（10%），推得基线约 40 µs、新值约 **36 µs**（推算） | **4800 MT/s**（Toggle DDR 6.0） | 4×16384/36µs ≈ **1.82 GB/s**（推算，页大小为假设） | 规格（2025-06-18 Kioxia R&D 页）+ 推算 / 中低 | NB-S13 |
| BiCS10 出样 | 332 | 1 Tb TLC | — | — | — | 4.8 Gb/s（比 BiCS8 快 33%） | 读能效 **+30%**、写能效 +18%；2026-07 出样，2027 量产 | 规格（2026-07-03）/ 中高 | NB-S14 |
| Kioxia/SanDisk ISSCC 2026（2 Tb QLC，6 plane，37.6 Gb/mm²） | 332 | 2 Tb | **6** | 未找到 | 未找到 | 未找到 | 写吞吐 >85 MB/s（论文标题） | 规格（论文标题）/ 中 | 检索摘要（Mynavi ISSCC 2026 预览），未单列编号 |
| 参考：ISSCC 2018–2021 TLC | 96–176 | 512 Gb–1 Tb | 2–4 | — | **40–58 µs** | 533 Mb/s–2.0 Gb/s | — | 规格（ISSCC 汇总，2021-02-19）/ 高 | NB-S12 |
| **HBF Gen-1 core die（SanDisk）** | BiCS CBA | **256 Gb（32 GB）** | 未公布；POSTECH/ETH 论文建模假设 **25 plane/die** | 论文假设 4 KiB | 论文假设 4 KiB 页读 **1 µs** | TSV 到逻辑 base die，对外 UCIe / xPU-HBF | 1.6 TB/s ÷ 16 die = **100 GB/s/die**；论文模型 25×4096/1µs = 102 GB/s/die | 每 stack 带宽为规格（高）；每 die 带宽为推算（中）；plane / tR 为论文假设（低） | NB-S20，NB-S21，NB-S24 |

### 2.2 实测下界与理论推算对不上

| SSD（die 数） | 顺序读规格 | 每 die 推算 = 规格 ÷ die 数 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|
| WD SN8100 1TB（8×1 Tb BiCS8，8 通道 @3600） | 14,900 MB/s | **1.86 GB/s/die** | 推算 / 中 | NB-S1 |
| Crucial T710 1TB（8×1 Tb G9 B68S） | 14,900 MB/s | **1.86 GB/s/die**（受 PCIe 链路限制，不是 die 的极限） | 推算 / 中 | NB-S4 |
| Micron 4600 1TB（8×1 Tb G9） | 14,500 MB/s | 1.81 GB/s/die | 推算 / 中 | NB-S4 |
| Samsung 9100 Pro 1TB（数据库记 8×1 Tb V8） | 14,700 MB/s | 1.84 GB/s/die（Tom's Hardware 说小容量用 512 Gb die，若是 16 颗则为 0.92，见第 9 节冲突） | 推算 / 中低 | NB-S2，NB-S7 |
| Crucial T705 1TB（8×1 Tb B58R，8 通道 @2400） | 13,600 MB/s | **1.70 GB/s/die**（2TB 版有 16 颗 die，达到 14,500 MB/s） | 推算 / 中 | NB-S3 |
| 2TB 及以上（16–32 颗 die） | 14,500–14,900 MB/s | 0.45–0.93 GB/s/die（PCIe 5.0 x4 链路上限约 15.75 GB/s，已饱和） | 推算 / 高 | NB-S1 至 NB-S4 |

**解读**：
- SN8100 1TB（BiCS8）和 T705 1TB（B58R）的实测每 die 吞吐（1.86 / 1.70）都略高于用数据库 tR 推出的阵列上限（1.64 / 1.61）。说明数据库里的 tR 很可能是最慢页（MSB）或保守值，TLC 各页平均 tR 更短。
- 工程上取 **b_die ≈ 1.6–1.9 GB/s** 作为当代主流 die 的设计值较稳妥。G9 级的 3.07 GB/s 只是理论值，客户端 SSD 里没有被验证过，因为 8 颗 die 就已经把 x4 链路跑满。
- **die 越大，每 GB 带宽越低。** 1 Tb die 约 1.86 GB/s，折合约 0.0145 (GB/s)/GB。若换成 2 Tb QLC die，即使每 die 带宽不变，每 GB 带宽也会减半。Samsung V8 在 2TB 盘里已全部用 1 Tb die（NB-S2），512 Gb die 正在退出（SK hynix P51 1TB 仍用 16×512 Gb，NB-S5）。

---

## 3. 客户端 PCIe 5.0 SSD：带宽、die 数、通道与功耗

### 3.1 拓扑（die 数 / 通道 / NAND）

| 型号 | 容量 | 主控（通道 @ 速率） | NAND | Die 数 × 单 die 容量 | 顺序读（规格） | 来源 / 置信度 |
|---|---|---|---|---|---|---|
| Samsung 9100 Pro | 1 / 2 / 4 / 8 TB | Presto（5 nm）8 通道 @2400 MT/s | V8 236L TLC | 8 / 16 / 32 / 64 × 1 Tb（数据库） | 14,700 / 14,700 / 14,800 / 14,800 MB/s | 读速为规格（高，NB-S6）；拓扑为数据库记录（中，NB-S2） |
| WD Black SN8100 | 1 / 2 / 4 / 8 TB | SM2508（6 nm）8 通道 @3600 MT/s，每通道 4 CE | BiCS8 218L TLC | 8 / 16 / 32 / 64 × 1 Tb | 14,900 MB/s（全容量） | 数据库记录 / 中（NB-S1） |
| Crucial T705 | 1 / 2 / 4 TB | Phison E26 8 通道 @2400 MT/s | Micron B58R 232L | 8 / 16 / 32 × 1 Tb | 13,600 / 14,500 / 14,100 MB/s | 数据库记录 / 中（NB-S3） |
| Crucial T710 | 1 / 2 / 4 TB | SM2508 8 通道 @3600 MT/s | Micron G9 B68S 276L | 8 / 16 / 32 × 1 Tb | 14,900 / 14,500 / 14,500 MB/s | 数据库记录 / 中（NB-S4） |
| Micron 4600（OEM） | 1 / 2 TB | SM2508 8 通道 @3600 MT/s | G9 B68S | 8 / 16 × 1 Tb | 14,500 MB/s | 数据库记录 / 中（NB-S4） |
| SK hynix Platinum P51 | 1 / 2 TB | Alistar 8 通道 @2400 MT/s | V8 D-die 238L | 16 / 32 × 512 Gb | 13,500 / 14,000 MB/s | 数据库记录 / 中（NB-S5） |
| Kioxia Exceria Pro G2 | 2 TB | SM2508 8 通道 @3600 MT/s | BiCS8 | 16 × 1 Tb | 14,900 MB/s | 数据库记录 / 中（NB-S5） |

**观察**：客户端旗舰全部是 **8 通道主控 + 至少 8 颗 1 Tb die**。PCIe 5.0 x4 链路上限 = 4 × 32 GT/s × 128/130 ÷ 8 = **15.75 GB/s**（推算，高），实际顺序读规格封顶 14.9 GB/s。1TB 盘已经能跑满链路，再加容量也不会更快。

### 3.2 满速读功耗与 nJ/B

| 型号 / 口径 | 满速读功耗 | 同时的读带宽 | nJ/B（推算 = W ÷ GB/s） | 性质 / 置信度 | 来源 |
|---|---|---|---|---|---|
| 9100 Pro 1TB，datasheet「Active (Avg.) Read」 | 7.6 W | 14.7 GB/s（规格） | **0.52** | 规格（FIO 3.33，Ryzen 5 7600 平台；未写明负载类型，推测为顺序读）/ 中高 | NB-S6 |
| 9100 Pro 2TB，datasheet | 8.1 W | 14.7 | **0.55** | 规格 / 中高 | NB-S6 |
| 9100 Pro 4TB，datasheet | 9.0 W | 14.8 | **0.61** | 规格 / 中高 | NB-S6 |
| 9100 Pro 8TB，datasheet（Rev 2.0，2025-09） | 10.5 W | 14.8 | **0.71** | 规格 / 中高 | NB-S6 |
| SN8100 1TB，平均读功耗 | 6.2 W | 14.9 | **0.42** | 规格（StorageReview / Club386 转引 SanDisk 规格表；未见 SanDisk 原始文档）/ 中 | NB-S11 |
| SN8100 2TB / 4TB，平均读功耗 | 6.5 W | 14.9 | **0.44** | 规格（同上）/ 中 | NB-S11 |
| **SN8100 2TB，TechPowerUp 实测**（1M 顺序读，QD8–QD128） | ≈6.3 W | ≈12.95 GB/s（同测） | **≈0.49** | 实测（只测盘功耗，Quarch，2025-08-05；从图表读数，±0.1 W / ±0.1 GB/s）/ 中高 | NB-S9 |
| **T710 2TB，TechPowerUp 实测**（同上） | ≈8.1 W | ≈13.6 GB/s | **≈0.60** | 实测（2025-07-01）/ 中高 | NB-S8 |
| **9100 Pro 2TB，TechPowerUp 实测**（同上） | ≈8.1 W | ≈12.25（QD8–16）/ 11.65（QD32+）GB/s | **≈0.66–0.70** | 实测（2025-03-26）/ 中高 | NB-S10 |
| 参考：T710 2TB 读能效（TPU 加权，以低 QD 为主） | — | — | 1694 MB/s/W（≈0.59 nJ/B，但不是满速顺序读口径） | 实测 / 中 | NB-S8 |
| 参考：Phison E37T（无 DRAM 的 PCIe 5.0 主控） | 4.5 W | 14.9 | 0.30（未说明是主控功耗还是整盘功耗） | 规格（2026-06-02）/ 低 | NB-S26 |

**小结**：客户端 PCIe 5.0 SSD 满速顺序读为 **0.42–0.71 nJ/B（规格）/ 0.49–0.70 nJ/B（实测）**，大容量盘偏高，因为 die 更多、静态功耗更大。主文档的 0.5 nJ/B 落在区间下沿，偏乐观但量级正确。

需要注意三点：
- 以上都是**盘级**功耗，没有计入主机侧 PCIe 根复合体 / PHY，以及数据写入 DRAM 的开销。这部分的可靠一手数据**未找到**，「系统级」数字应比盘级更高。
- 9100 Pro 在 Tom's Hardware 测试中最高 67°C（NB-S7）；也有评测报告持续负载下达 81°C（NAS Compares，转引，低）。笔记本里持续满速读可能触发降速。
- 价格参考（规格，2025-03 发布价，NB-S7）：9100 Pro 1 / 2 / 4 / 8 TB 为 $199.99 / $299.99 / $549.99 / $999.99。2025H2 至 2026 年 NAND 价格大幅上涨（NB-S27 引用的行业预测：数据中心将吸收 70–80% NAND 供给），**当前价格未核实**。

---

## 4. PCIe 6.0 客户端 SSD：时间表与带宽

| 事项 | 数值 / 时间 | 性质 / 置信度 | 来源 |
|---|---|---|---|
| PCIe 6.0 x4 链路原始带宽 | **30.25 GB/s**（未扣协议开销）；x8 为 60.5，x16 为 121 GB/s（推算） | 规格 / 高 | NB-S25 |
| 企业级 PCIe 6.0 盘实际顺序读 | **28 GB/s**（Micron 9650，G9 276L @3600 MT/s；Samsung PM1763 同级） | 规格 / 高 | NB-S25，NB-S28 |
| Micron 9650 功耗 | 最高 **25 W**（≈0.89 nJ/B 上界，推算）；Micron 称顺序读能效约为 PCIe 5.0 盘的 2 倍，随机读能效 +67% | 规格（2025-07-30）/ 中高 | NB-S28 |
| Phison X3（PS5303，16 通道企业主控） | 28 GB/s，约 4 GB/s/W（主控约 7 W，仅主控口径 0.25 nJ/B）；2026-12 送样，2027 年中量产 | 规格（2026-06-02 / 2026-08-13）/ 中高 | NB-S25，NB-S26 |
| Marvell Bravera SC6（16 通道 @3600） | 2026Q4 送样，成品盘「2027 年底，更可能 2028」 | 规格 + 媒体推断 / 中 | NB-S25 |
| **SMI Neptune（客户端 PCIe 6.0 x4 主控）** | 早期路线图：顺序读 **>25 GB/s**、3.5M IOPS；正在评估 8 通道架构；客户端平台目标「2027 年底」（可能只是送样或参考设计）；原计划 2028 量产、2029 年后上市 | 厂商访谈 + 媒体 / 中 | NB-S27 |
| 其它判断 | heise 等认为桌面 / 笔记本 PCIe 6.0 SSD 在 **2030 年前后**才会普及；主板厂尚未准备好消费级 PCIe 6.0 平台 | 媒体 / 中低 | NB-S27（转引） |

**结论**：客户端 PCIe 6.0 x4 SSD 约 **25–28 GB/s**，**2028–2030 年**上市，2027 年最多见到主控样品。时间点与主方案「2029 量产」大致重合，但有 1–2 年的不确定性。

**8 通道主控能否跑满 PCIe 6.0？** 8 通道 × 3.6 GB/s = 28.8 GB/s，刚好够；8 × 4.8 = 38.4 GB/s，余量充足。die 侧需要 28 ÷ b_die = 15–18 颗（1.6–1.86 GB/s/die），或 10 颗（G9 理论 3.07）。也就是说，**用 1 Tb die 的 PCIe 6.0 x4 盘至少要 2 TB 才能跑满**（推算，中）。

---

## 5. UFS 5.0 / UFS 4.x 能效

| 事项 | 数值 | 性质 / 置信度 | 来源 |
|---|---|---|---|
| UFS 5.0 标准 | M-PHY 6.0 HS-G6，单 lane 46.6 Gb/s × 2，顺序读最高 **10.8 GB/s**（2025-10-06） | 规格 / 高 | NB-S29 |
| Samsung UFS 5.0 | 读 10.8 / 写 9.5 GB/s；**能效比自家 UFS 4.1 提升 >40%**（clock gating + 多电压）；2026Q4 量产，最大 1 TB；**未给绝对功耗** | 规格（2026-06-23）/ 高（相对值） | NB-S30 |
| Kioxia UFS 5.0 | 2026-02 送样；2 lane 理论 10.8 GB/s；后续报道样品为读 10 / 写 9.0 GB/s；称能效优于自家 UFS 4.1，**无绝对值** | 规格 / 中 | NB-S31 |
| Samsung UFS 4.0 | 顺序读能效 **6.0 MB/s per mA**，比 UFS 3.1 提升 46%（2022-05-04） | 规格 / 高（数字），口径低（未说明是哪条供电轨） | NB-S32 |
| UFS 4.0 折算 nJ/B | E = V × 1 mA ÷ 6.0 MB/s = V × 0.167 nJ/B：VCCQ 1.2 V 约 **0.20**，1.8 V 约 0.30，VCC 2.5 V 约 **0.42**，3.3 V 约 **0.55 nJ/B** | 推算 / 低（供电轨未知；若只计单轨，会低估总功耗） | NB-S32 |
| UFS 系统级每字节读能耗（实测） | **未找到**（FMS 2025 有一份对比 eMMC / UFS 3.1 / UFS 4.1「每 bit 能耗」的幻灯片，但其域名本次无法访问） | — | — |

**解读**：UFS 4.0 按 2.5–3.3 V 折算约 0.42–0.55 nJ/B，与主文档的 0.5 nJ/B 同一量级。UFS 5.0 若在 UFS 4.1 基础上再提升 40%，可能降到约 0.3 nJ/B（推算，低）。但 UFS 5.0 的绝对带宽只有 10.8 GB/s，在 PC 方案里不适合作为主力。

---

## 6. HBF：每 die / 每 stack 带宽与实现手段

| 事项 | 数值 | 性质 / 置信度 | 来源 |
|---|---|---|---|
| Gen-1 每 stack 读带宽 | **1.6 TB/s** | 规格（SanDisk 一手 Fact Sheet，2025-07）/ 高 | NB-S20 |
| Gen-1 单 die 容量 / stack | **256 Gb/die，16 die 堆，512 GB/stack**；尺寸、功耗、堆高对齐 HBM4 | 规格 / 高 | NB-S20，NB-S21 |
| **每 die 带宽** | 1.6 TB/s ÷ 16 = **100 GB/s/die** | 推算 / 中（假设 16 颗 die 均匀出力） | NB-S20 |
| 与普通 NAND die 之比 | 100 ÷ (1.61–1.64) ≈ **61–62 倍**（对 V8 / BiCS8 / B58R）；100 ÷ 3.07 ≈ **33 倍**（对 G9 理论值）；100 ÷ 1.86 ≈ **54 倍**（对实测下界） | 推算 / 中 | 第 2 节 |
| 每 GB 带宽密度 | HBF：100 ÷ 32 = **3.1 (GB/s)/GB**；1 Tb TLC：1.86 ÷ 128 = **0.0145 (GB/s)/GB**，相差约 **215 倍** | 推算 / 中 | — |
| Gen-2 / Gen-3 | 读带宽 >2 TB/s / 3.2 TB/s；stack 容量 1 TB / 1.5 TB；功耗为 Gen-1 的 0.8 倍 / 0.64 倍 | 规格（初步）/ 中 | NB-S20 |
| OCP 规范（2026-08-04） | 8-Hi / 16-Hi，最大 512 GB；带宽分三档，约 **0.4–3.0 TB/s**；接口 UCIe；目前只有 Google、Tenstorrent 加入联盟 | 规格（SK hynix 一手新闻稿）/ 高 | NB-S22，NB-S23 |
| 单个 UCIe 接口能力 | 64 GT/s × 64 lane，每 package 约 **400 GB/s**（Tom's Hardware 分析，与 1.6 TB/s 的关系未说明） | 媒体推算 / 中低 | NB-S23 |
| 实现手段 | 把每颗 die 的大阵列切成「很多很多小阵列」并行访问，每个子阵列有独立读写通路（SanDisk 高管原话的转述）；TSV 连到逻辑 base die，由 base die 调度几百到几千路并发流；CBA 键合；专利堆叠技术减少翘曲 | 规格 + 媒体解读 / 中 | NB-S20，NB-S21 |
| 学术建模假设 | **25 plane/die**、**4 KiB 页读 1 µs**、写 100 µs；HBF stack 功耗「<< 80 W」，高于 HBM stack 的 40 W；对照 Samsung Z-NAND 16 die 87.4 GB/s（约 5.5 GB/s/die）、Kioxia XL-Flash 16 die 262 GB/s（约 16 GB/s/die） | 论文假设（POSTECH + ETH，IEEE CAL，2026-08-14）/ 低 | NB-S24 |
| HBF 每字节读能耗 | 若 stack 功耗为 40–80 W、带宽 1.6 TB/s，则为 **0.025–0.05 nJ/B**（比 SSD 低 10–20 倍） | 推算 / **低**（功耗来自论文假设，SanDisk 只说「对齐 HBM4 功耗」） | NB-S20，NB-S24 |
| 端侧 / PC 产品 | **无**。SanDisk 2025-02 提过「未来可能进手机等设备」，但没有时间表 | 规格 / 高 | NB-S21 |

**HBF 每 die 快几十倍，拆解如下**（推算，中低）：

| 维度 | 普通 TLC die | HBF core die（论文假设） | 倍数 |
|---|---|---|---|
| Plane 数 | 4–6 | 约 25 | ×4–6 |
| 页大小 | 16 KiB | 4 KiB | ÷4 |
| tR | 32–61 µs | 约 1 µs | ×32–61 |
| 合计（阵列吞吐） | 1.6–3.1 GB/s | 约 102 GB/s | ×33–62 |

- **tR 从数十 µs 降到约 1 µs 是主因。** 可能来自更短的 BL/WL（细分子阵列）、SLC 或类 SLC 存储（论文按 SLC 耐久 10 万次 P/E 建模；SanDisk 和 SK hynix 都没有公开每 cell 存几 bit）。
- **接口**：普通 die 挂在 8 bit、2.4–5.6 GT/s 的共享通道上，每通道只有 2.4–5.6 GB/s。HBF 用 TSV 宽并行直连 base die，每 die 100 GB/s，相当于 20–40 条普通通道。
- **代价**：die 只有 256 Gb，容量密度低（相当于普通 2 Tb QLC die 的 1/8）；写入很慢（论文表 I：每 stack 写 0.073–0.128 TB/s 量级）；需要 2.5D/3D 封装和 UCIe，不能做成 M.2 盘。

---

## 7. 三档核算：30 / 60 / 117 GB/s

### 7.1 Die 数与最小容量

N_die = ⌈B ÷ b_die⌉，C_min = N_die × 单 die 容量。下表为推算，置信度中；b_die 取三种口径。

| 目标 B | b_die = 1.64（V8 / BiCS8 理论） | b_die = 1.86（实测下界） | b_die = 3.07（G9 理论） | C_min @1 Tb die | C_min @512 Gb die | C_min @2 Tb die | 相对 100 GB 模型的容量超配倍数（@1 Tb） |
|---|---|---|---|---|---|---|---|
| **30 GB/s** | 19 颗 | 17 颗 | 10 颗 | **2.2–2.4 TB**（G9 理论 1.28 TB） | 1.1–1.2 TB | 4.4–4.9 TB | 22–24 倍（G9：13 倍） |
| **60 GB/s** | 37 颗 | 33 颗 | 20 颗 | **4.2–4.7 TB**（G9 理论 2.56 TB） | 2.1–2.4 TB | 8.4–9.5 TB | 42–47 倍（G9：26 倍） |
| **117 GB/s** | 72 颗 | 63 颗 | 39 颗 | **8.1–9.2 TB**（G9 理论 5.0 TB） | 4.0–4.6 TB | 16–18 TB | 81–92 倍（G9：50 倍） |

**通道约束**：8 通道主控 @3600 MT/s 原始带宽 28.8 GB/s，@4800 为 38.4 GB/s；16 通道 @3600 为 57.6 GB/s。三档分别至少需要：

| 目标 | 8 通道 @3.6 | 8 通道 @4.8 | 16 通道 @3.6 |
|---|---|---|---|
| 30 GB/s | 2 颗主控（1.04 倍） | 1 颗（0.78 倍） | 1 颗 |
| 60 GB/s | 3 颗 | 2 颗 | 2 颗 |
| 117 GB/s | 5 颗 | 4 颗 | 3 颗 |

（推算，中）

### 7.2 接口与盘数

| 目标 B | PCIe 5.0 x4（规格 14.9；实测 11.7–14.7 GB/s） | PCIe 6.0 x4（约 28 GB/s，客户端 2028–2030） | 单设备宽链路 | 最少 PCIe 通道 |
|---|---|---|---|---|
| **30 GB/s** | 2 块（29.8 GB/s，按规格恰好够；按实测约 24–29）→ 稳妥需 **3 块** | **1 块**（28 GB/s，达 93%）/ 2 块（56） | PCIe 5.0 x8（31.5 原始，无客户端产品）；PCIe 6.0 x4 | 4（Gen6）/ 8–12（Gen5） |
| **60 GB/s** | 4 块（59.6，按规格恰好够）→ 稳妥需 **5 块** | 2 块（56，达 93%）/ **3 块** | PCIe 6.0 x8（60.5 原始）；PCIe 5.0 x16（63 原始，需在 x16 插槽上拆分出 4 个 M.2） | 8–12（Gen6）/ 16–20（Gen5） |
| **117 GB/s** | 8 块（119，按规格恰好够）→ 稳妥需 **9–10 块** | 4 块（112，达 96%）/ **5 块** | PCIe 6.0 x16（121 原始，扣开销后约 112–115 GB/s，勉强） | 16–20（Gen6）/ 32–40（Gen5） |

（推算，中）

**平台通道约束**：

| 平台 | 可用通道 | 性质 / 置信度 |
|---|---|---|
| AMD AM5（Ryzen 9000，桌面） | **24 条可用 PCIe 5.0**（含给 GPU 的 x16） | 规格（AMD 指南，转引）/ 中，NB-S34 |
| Intel Panther Lake（笔记本） | 最多 12 条 PCIe 5.0 + 8 条 PCIe 4.0；12 Xe3 核版本只有 4 条 PCIe 5.0 | 泄露 / 低，NB-S34 |
| AMD Strix Halo | 约 16 条（代际说法冲突） | 媒体 / 低 |

结论（推算，中）：
- **60 GB/s 在当代桌面上已经要占用 GPU 的 x16 插槽**（拆成 4 个 PCIe 5.0 x4 M.2）。
- **117 GB/s 需要 PCIe 6.0 x16 级别的通道**，现有消费平台都不具备。
- 笔记本平台最多能支撑 30 GB/s 档（2–3 块 Gen5 盘，或 1 块 Gen6 盘），而且 M.2 插槽数和散热是硬约束。

### 7.3 满速读功耗

P = e × B。下表为推算，置信度中；e 取值见第 3、6 节。

| 目标 B | e = 0.5（主文档假设） | e = 0.42（规格最优：SN8100 1TB） | e = 0.49–0.70（TPU 实测区间） | e = 0.025–0.05（HBF，低置信） |
|---|---|---|---|---|
| **30 GB/s** | **15 W** | 12.6 W | **14.7–21 W** | 0.75–1.5 W |
| **60 GB/s** | **30 W** | 25.2 W | **29–42 W** | 1.5–3 W |
| **117 GB/s** | **58.5 W** | 49 W | **57–82 W** | 2.9–5.9 W |

- 参照点：Kioxia 5 TB / 64 GB/s 闪存模块原型（PCIe 6.0 x8，菊花链「beads」，闪存接口 4.0 Gbps）功耗 **<40 W**，即 ≤0.625 nJ/B（规格，2025-08-20，高，NB-S33）。这与 60 GB/s 档「约 30–40 W、约 5 TB」的推算吻合，说明 5 TB 是把 60 GB/s 做出来的现实容量量级。
- 多盘并行时，每块盘的主控和 DRAM 固定功耗不会减少，所以 N 块盘各跑一部分带宽的效率，低于少量盘满速运行（推算，中）。
- PCIe 6.0 时代：Phison X3 主控约 4 GB/s/W，Micron 称顺序读能效翻倍，SK hynix V10 375 层称每瓦性能提升 2.5 倍（2026-08-04，NB-S22），BiCS10 读能效 +30%（NB-S14）。2029 年时盘级 e **可能降到约 0.3 nJ/B**（推算，低）。但这些都是企业级或厂商声明，客户端实测**未找到**。

### 7.4 单轮时间与能耗（W = 100 GB）

| 带宽 | 单轮流式时间 t = W ÷ B | 单轮能耗 E = W × e |
|---|---|---|
| 14.9 GB/s（1 块 PCIe 5.0 x4） | 6.7 s | 与带宽无关：0.5 nJ/B 为 **50 J**；0.6 nJ/B 为 60 J；0.7 nJ/B 为 70 J |
| 28 GB/s（1 块 PCIe 6.0 x4） | 3.6 s | 同上 |
| 30 / 60 / 117 GB/s | 3.3 / 1.7 / 0.85 s | 同上 |

（推算，高）

---

## 8. 结论：系统主 SSD 能否直接兼任 HBF

| 方案 | 能达到的带宽 | 覆盖哪一档 | 容量 / 接口 | 判断 |
|---|---|---|---|---|
| 1–2 TB PCIe 5.0 x4 主盘（现在就有） | 规格 14.9，实测 11.7–14.7 GB/s；约 6–9 W | **一档都覆盖不了**（只有电池档的 40–50%） | 8–16 颗 1 Tb die 已跑满 x4 | 不行 |
| **2 TB PCIe 6.0 x4 主盘（2028–2030）** | 约 25–28 GB/s；约 12–20 W（按 0.42–0.7 nJ/B） | **电池档 30 GB/s 的 83–93%** | 16 颗 1 Tb die 刚好跑满；**1 TB 只有 8 颗 die，若单 die 带宽不到 3.5 GB/s 就跑不满** | 基本可以兼任（需接受约 7% 的缺口，或做 2 盘 RAID0） |
| 60 GB/s | — | 中间档 | 需要 2–3 块 Gen6 盘或 4–5 块 Gen5 盘，**4–6 TB**，8–20 条通道 | 主盘无法单独承担，需要多盘阵列（桌面级） |
| 117 GB/s | — | 插电档 | 需要 4–5 块 Gen6 盘或 8–10 块 Gen5 盘，**8–10 TB**，16–40 条通道 | 主盘无法承担；超出现有消费平台通道数，只能用工作站平台或专门的高带宽闪存器件 |

**一句话结论**：
- **电池档（30 GB/s）**：2028 年以后，一块 **2 TB PCIe 6.0 x4 系统主盘**大致能直接兼任，不需要专门的 HBF 器件。代价是闪存读约 12–20 W，占笔记本电池模式功耗预算的很大一部分。PCIe 5.0 主盘做不到。
- **中间档和插电档（60 / 117 GB/s）**：单块主盘不行，必须用 3–5 块盘、4–10 TB 的多盘阵列（或 PCIe 6.0 x8/x16 的专用闪存设备）。这时**成本由带宽决定的 die 数（33–72 颗）锁定，而不是由 100 GB 的模型容量决定**。

---

## 9. 冲突、口径问题与待核实

1. **【与本地文档冲突】HBF 单 die 容量的单位。** 本地 `surveys/ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md`（第 3、11、44、101、142、177 行）和 `advanced/A16i-端侧UFS-HBF增强.md`（第 51、122 行，§3.3 与来源列表）写的是「256 GB/die」。SanDisk 一手 Fact Sheet（NB-S20）原文是「packs **256Gb** per die, reaching 512GB total capacity per 16 die stack」，Tom's Hardware（NB-S21）也算得「each HBF core die is a 256 Gb 3D NAND device」。16 × 256 GB = 4 TB，与 512 GB/stack 自相矛盾，所以正确值是 **256 Gb（32 GB）/die**。按用户要求，本文未修改那两篇文档。
2. **Samsung 9100 Pro 1TB 的 die 构成。** TechPowerUp 数据库记为 2 颗封装 × 4 die × 1 Tb = 8 颗 die（NB-S2）。Tom's Hardware 称「512Gb 用于较小容量以提升交错，1Tb 用于大容量」（NB-S7），没有点明是哪几档。两者冲突，每 die 推算值是 1.84 还是 0.92 GB/s 取决于此。置信度低，不作为设计依据。
3. **tR 与实测对不上。** BiCS8 与 B58R 用数据库 tR 推出的阵列吞吐，低于 1TB 盘的实测每 die 吞吐（见 2.2 节），推测数据库 tR 是最慢页值。设计时采用实测下界 1.7–1.86 GB/s。
4. **TechPowerUp 功耗实测是从图表读数**（±0.1 W / ±0.1 GB/s），并且只测盘功耗。Samsung datasheet 的「Active Read」没有写明负载类型。SN8100 的 6.2 / 6.5 W 来自评测站转引的规格表，SanDisk 原始文档**未找到**（SanDisk 官网也写过「平均 7 W 及以下」「7.5 W 及以下」这类笼统说法）。
5. **SK hynix 321L TLC、Samsung V9 / V10、Kioxia BiCS10 的 plane 数、页大小、tR 绝对值大多未找到**，只有相对提升百分比。BiCS10 的 tR 约 36 µs 是由「缩短 4 µs = 10%」反推得来，置信度低。
6. **Kioxia BiCS10 的接口提速幅度口径不一**：2025-02 预告把 4.8 Gb/s 归于 BiCS9（比 BiCS8 快 33%），2026-07 出样新闻归于 BiCS10。另外 BiCS8 的接口是 3.6 Gb/s（数据库记录），4.8 ÷ 3.6 = +33% 自洽。
7. **HBF 的 plane 数、tR 和功耗没有一手数据**。25 plane、1 µs、「<< 80 W」均为 POSTECH/ETH 论文的建模假设（NB-S24），由此推出的 0.025–0.05 nJ/B 置信度低。
8. **读干扰（read disturb）**：每天对同一批 100 GB 权重反复读取上百次，会触发 SSD 的读回收（read reclaim）后台搬移，从而影响带宽和写放大。Park 等（SIGMETRICS 2026，15 款 NVMe 盘，NB-S35）证实读干扰会显著影响商用 SSD 的系统级 I/O 性能。本次只读到摘要，**触发阈值和带宽损失的具体数字未找到**，需要读全文或做实测。
9. **价格**：只有 2025-03 的发布价；2026 年 NAND 涨价，当前价格未核实。
10. **未能访问的来源**：FMS 2025 Kioxia 汽车存储幻灯片（有 eMMC / UFS 每 bit 能耗对比，域名不可达）；Micron G9 官方新闻稿原文（404，改用转载）；SK hynix 321L 新闻稿正文（页面未渲染，改用转载）；AMD AM5 指南 PDF（未打开，数字取自检索摘要）。

---

## 10. 来源列表

| 编号 | 来源 | 日期 | URL | 用于 |
|---|---|---|---|---|
| NB-S1 | TechPowerUp SSD Database：WD Black SN8100 1 / 2 / 4 / 8 TB | 访问于 2026-10-14 | https://www.techpowerup.com/ssd-specs/western-digital-black-sn8100-1-tb.d2396 ；…-2-tb.d2387 ；…-4-tb.d2397 ；…-8-tb.d2617 | BiCS8：4 plane、16 KB、tR 40 µs、3600 MT/s、die 数、8 通道、平均功耗 |
| NB-S2 | TechPowerUp SSD Database：Samsung 9100 Pro 1 / 2 / 4 / 8 TB | 访问于 2026-10-14 | https://www.techpowerup.com/ssd-specs/samsung-9100-pro-1-tb.d2318 ；…-2-tb.d2319 ；…-4-tb.d2320 ；…-8-tb.d2321 | V8：4 plane、tR 40 µs、每 die 读 1600 / 1640 MB/s、die 数 |
| NB-S3 | TechPowerUp SSD Database：Crucial T705 1 / 2 / 4 TB | 访问于 2026-10-14 | https://www.techpowerup.com/ssd-specs/crucial-t705-1-tb.d1924 ；…-2-tb.d1925 ；…-4-tb.d1926 | B58R：6 plane、tR 61 µs、2400 MT/s |
| NB-S4 | TechPowerUp SSD Database：Crucial T710 1 / 2 / 4 TB；Micron 4600 1 / 2 TB | 访问于 2026-10-14 | https://www.techpowerup.com/ssd-specs/crucial-t710-1-tb.d2512 ；…t710-2-tb.d2511 ；…t710-4-tb.d2513 ；https://www.techpowerup.com/ssd-specs/micron-4600-1-tb.d2313 ；…4600-2-tb.d2312 | G9 B68S：6 plane、tR 32 µs、3600 MT/s |
| NB-S5 | TechPowerUp SSD Database：SK hynix Platinum P51、Kioxia Exceria Pro G2、Samsung 990 EVO Plus | 访问于 2026-10-14 | https://www.techpowerup.com/ssd-specs/sk-hynix-platinum-p51-1-tb.d1967 ；…p51-2-tb.d1968 ；https://www.techpowerup.com/ssd-specs/kioxia-exceria-pro-g2-2-tb.d2619 ；https://www.techpowerup.com/ssd-specs/samsung-990-evo-plus-2-tb.d2206 | V8 D-die 512 Gb、4 plane；BiCS8 |
| NB-S6 | Samsung NVMe SSD 9100 PRO Datasheet Rev. 2.0 | 2025-09（Rev 1.0 为 2025-01） | https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_NVMe_SSD_9100_PRO_Datasheet_Rev.2.0.pdf | 各容量读速与 Active Read 功耗 7.6 / 8.1 / 9.0 / 10.5 W（一手，已下载核对） |
| NB-S7 | Tom's Hardware：Samsung 9100 Pro SSD Review | 2025-03-18 | https://www.tomshardware.com/pc-components/ssds/samsung-9100-pro-ssd-review | Presto 8 通道 @2400、V8 236L、512 Gb / 1 Tb 说法、发布价、67°C |
| NB-S8 | TechPowerUp：Crucial T710 2 TB Review（第 4 页顺序读、第 7 页功耗） | 2025-07-01 | https://www.techpowerup.com/review/crucial-t710-2-tb/7.html | 实测约 13.6 GB/s @ 约 8.1 W |
| NB-S9 | TechPowerUp：WD Black SN8100 2 TB Review | 2025-08-05 | https://www.techpowerup.com/review/wd-black-sn8100-2-tb/7.html | 实测约 12.95 GB/s @ 约 6.3 W |
| NB-S10 | TechPowerUp：Samsung 9100 Pro 2 TB Review | 2025-03-26 | https://www.techpowerup.com/review/samsung-9100-pro-2-tb/7.html | 实测约 11.65–12.25 GB/s @ 约 8.1 W |
| NB-S11 | StorageReview：SanDisk WD_BLACK SN8100 Review；Club386：SN8100 2TB Review | 2025（具体日期未核） | https://www.storagereview.com/review/sandisk-wd_black-sn8100-review-elite-performance-in-a-gen5-ssd ；https://www.club386.com/?p=105945 | SN8100 平均读功耗 6.2 / 6.5 W（转引规格） |
| NB-S12 | AnandTech（B. Tallis）：2021 NAND Flash Updates from ISSCC | 2021-02-19 | https://www.anandtech.com/show/16491/flash-memory-at-isscc-2021 （存档：https://web.archive.org/web/2023/https://www.anandtech.com/print/16491/flash-memory-at-isscc-2021 ） | TLC tR 40–58 µs、plane 2–4、CuA 使 4 plane 成为标配 |
| NB-S13 | Kioxia R&D：Development of a 1Tb 3b/Cell BiCS FLASH generation10（ISSCC 2025 论文 30.2） | 2025-06-18 | https://www.kioxia.com/en-jp/rd/technology/topics/topics-83.html | 4 plane、tRead −4 µs（10%）、4.8 Gbps、读能耗 −29% |
| NB-S14 | Blocks & Files：Kioxia / SanDisk sample-shipping 332-layer 3D NAND | 2026-07-03 | https://www.blocksandfiles.com/flash/2026/07/03/kioxia-sample-shipping-332-layer-3d-nand/5266362 | BiCS10 出样、4.8 Gb/s（比 BiCS8 +33%）、读能效 +30% |
| NB-S15 | Micron G9 量产 / 出货报道（TechSpot、Guru3D 转述 Micron 新闻稿） | 2024-07-30 | https://techspot.com/news/104055-micron-becomes-first-industry-ship-9th-gen-tlc.html ；https://www.guru3d.com/story/micron-announces-volume-production-of-ninthgeneration-nand-flash-technology/ | 3.6 GB/s I/O；每 die 读带宽 +88%、写带宽 +99%（对比竞品） |
| NB-S16 | SK hynix 321 层 1 Tb TLC 量产（新闻稿及转载） | 2024-11-21 | https://news.skhynix.com/sk-hynix-starts-mass-production-of-worlds-first-321-high-nand/ ；https://www.storagenewsletter.com/2024/11/29/sk-hynix-starts-mass-production-of-321-layer-4d-nand-flash-with-1tb-capacity ；https://www.guru3d.com/story/sk-hynix-begins-mass-production-of-1tb-triple-level-cellbased-4d-nand-flash-321layers/ | 传输 +12%、读 +13%、读能效 >+10% |
| NB-S17 | SK hynix 321 层 2 Tb QLC 量产（PR Newswire）；Notebookcheck | 2025-08-25 | https://www.prnewswire.com/news-releases/sk-hynix-begins-mass-production-of-321-layer-qlc-nand-flash-302537234.html ；https://www.notebookcheck.net/SK-hynix-starts-mass-production-of-321-layer-2-terabit-QLC-NAND.1096730.0.html | 4 plane 增至 6 plane、传输 2 倍、读 +18%、3200 MT/s |
| NB-S18 | AnandTech：Samsung Starts Mass Production of 9th Gen V-NAND | 2024-04-23 | https://www.anandtech.com/show/21365/samsung-starts-mass-production-of-9th-generation-vnand-1tb-3d-tlc-nand | V9 1 Tb TLC、Toggle 5.1 3.2 GT/s |
| NB-S19 | Blocks & Files：Samsung developing 400-plus layer 3D NAND（ISSCC 2025 论文 30.1）；Tom's Hardware V10 预告 | 2024-12-04 | https://www.blocksandfiles.com/data-management/2024/12/04/samsung-developing-400-plus-layer-3d-nand/1603230 ；https://www.tomshardware.com/pc-components/ssds/samsung-prepares-to-unveil-10th-generation-v-nand-with-400-layers-ready-to-power-future-pcie-5-0-and-6-0-ssds | V10 1 Tb TLC、28 Gb/mm²、5.6 Gb/s/pin |
| NB-S20 | SanDisk：HBF Fact Sheet（Tech Brief） | 2025-07 | https://documents.sandisk.com/content/dam/asset-library/en_us/assets/public/sandisk/collateral/company/Sandisk-HBF-Fact-Sheet.pdf | 1.6 TB/s、256 Gb/die、16 die、512 GB；Gen-2 / Gen-3 带宽与功耗系数（一手，已下载核对） |
| NB-S21 | Tom's Hardware：SanDisk's new HBF memory enables up to 4TB of VRAM | 2025-02-13 | https://www.tomshardware.com/pc-components/dram/sandisks-new-hbf-memory-enables-up-to-4tb-of-vram-on-gpus-matches-hbm-bandwidth-at-higher-capacity | 子阵列并行、TSV、逻辑 die、16 颗 core die、256 Gb/die、可能进入手机 |
| NB-S22 | SK hynix Newsroom：SK hynix Unveils First HBF Standard Specifications with Sandisk | 2026-08-04 | https://news.skhynix.com/en/hbf-at-fms-2026/ | 8 / 16-Hi、512 GB、0.4–3.0 TB/s 三档、UCIe；V10 375L 每瓦性能 2.5 倍 |
| NB-S23 | Tom's Hardware：New HBF spec outlines tech…（16-Hi、3 TB/s、UCIe） | 2026-08-04 | https://www.tomshardware.com/pc-components/ssds/sandisk-and-sk-hynix-unveil-hbf-spec-up-to-16-hi-nand-stacks-3-tb-s-bandwidth-ucie | 单个 UCIe 约 400 GB/s / package；采用方 |
| NB-S24 | Son, Park, Cho, Ham, Mutlu, Lee, Kim, Park：Exploring High-Bandwidth Flash for Modern LLM Inference（IEEE CAL；POSTECH + ETH） | 2026-08-14 | https://arxiv.org/abs/2608.13868 | 25 plane/die、1 µs 4 KiB 读、HBF stack「<< 80 W」、Z-NAND / XL-Flash 对照 |
| NB-S25 | Tom's Hardware：The current state of PCIe 6.0 SSDs and controllers | 2026-08-13 | https://www.tomshardware.com/tech-industry/the-current-state-of-pcie-6-0-ssds-and-controllers-marvell-phison-and-smi-prepare-controllers-as-drives-finally-come-to-market-following-years-of-delays | Gen6 x4 30.25 GB/s；Marvell / Phison / SMI / Micron / Samsung 时间表 |
| NB-S26 | Tom's Hardware：Phison shows PCIe 6.0 X3…；E37T 4.5 W | 2026-06-02 | https://www.tomshardware.com/pc-components/ssds/phison-shows-pcie-6-0-x3-ssd-controller-with-28-gb-s-of-bandwidth-and-6-8-million-iops-supports-2-petabytes-per-drive-also-new-power-sipping-e37t-ssds-for-pcie-5-0-systems-consume-a-mere-4-5w | X3 28 GB/s、4 GB/s/W、约 7 W；E37T 14.9 GB/s @4.5 W |
| NB-S27 | Igor's Lab：Silicon Motion advances PCIe 6.0 client SSDs to late 2027；Silicon Motion Neptune… NAND problem 2027 | 2026-06-20；2026-06-23 | https://www.igorslab.de/en/silicon-motion-pcie-6-0-client-ssds-late-2027-nvidia/ ；https://www.igorslab.de/en/silicon-motion-neptune-pcie-6-0-consumer-ssds-nand-problem-2027/ | Neptune >25 GB/s、评估 8 通道、2027 年底目标；NAND 短缺 |
| NB-S28 | heise：Micron presents the first PCIe 6.0 SSD（9650） | 2025-07-30 | https://www.heise.de/-10504552 | 28 GB/s 读、14 GB/s 写、最高 25 W、随机读能效 +67% |
| NB-S29 | JEDEC：UFS 5.0 Is Coming（经本地文档转引） | 2025-10-06 | https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage | 10.8 GB/s、HS-G6 46.6 Gb/s/lane |
| NB-S30 | Samsung Newsroom：Samsung Unveils Industry's Fastest UFS 5.0 Solution | 2026-06-23 | https://news.samsung.com/global/samsung-unveils-industrys-fastest-ufs-5-0-solution-for-next-gen-on-device-ai-applications | 10.8 / 9.5 GB/s、能效比 UFS 4.1 提升 >40%、2026Q4 量产 |
| NB-S31 | CNX Software：Kioxia samples UFS 5.0 embedded flash | 2026-02-24 | https://www.cnx-software.com/2026/02/24/kioxia-samples-ufs-5-0-embedded-flash-memory-with-up-to-1tb-capacity-10-8-gb-s-data-rate/ | 送样、10.8 GB/s 理论值；样品读 10 / 写 9 GB/s（后续报道转引，中低） |
| NB-S32 | Samsung Semiconductor：Samsung Develops First UFS 4.0 Storage Solution | 2022-05-04 | https://news.samsungsemiconductor.com/global/samsung-develops-first-ufs-4-0-storage-solution-compliant-with-new-industry-standard | 6.0 MB/s per mA |
| NB-S33 | Kioxia：Prototype of 5TB Large-Capacity and 64GB/s High-Bandwidth Flash Memory Module | 2025-08-20 | https://www.kioxia.com/en-jp/about/news/2025/20250820-1.html | 5 TB、64 GB/s、PCIe 6.0 x8、<40 W、闪存接口 4.0 Gbps（一手，已抓取核对） |
| NB-S34 | AMD Socket AM5 Quick Reference Guide；PCWorld（Panther Lake 泄露） | — / 2025 | https://www.amd.com/content/dam/amd/en/documents/partner-hub/ryzen/amd-socket-am5-quick-reference-guide.pdf ；https://www.pcworld.com/article/2928765/ | AM5 24 条可用 PCIe 5.0；Panther Lake 最多 12 条 PCIe 5.0（泄露） |
| NB-S35 | Park, Cho, Mutlu, Lee, Park：Experimental Study on System-Level Performance Impact of Read Disturbance in Modern SSDs（SIGMETRICS 2026） | 2026-08-14 | https://arxiv.org/abs/2608.14073 | 读干扰影响商用 SSD 系统级性能（15 款盘） |
| NB-S36 | 本地：`surveys/ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md`；`advanced/A16i-端侧UFS-HBF增强.md` | — | 仓库内 | UFS 4.x / 5.0 / HBF 背景；「256 GB/die」单位冲突 |

> 计算脚本（含全部公式）只放在会话临时目录，没有写入仓库。所有推算都可以按第 1 节的公式复算。

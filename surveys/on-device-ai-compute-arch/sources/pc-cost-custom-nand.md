# PC 端侧 AI 成本核算：定制「高带宽、小容量」NAND 器件（CN 系列来源）

> **用途**：PC 方案要把 200B MoE（FP4 专家约 100 GB）放在闪存里，每轮把全部权重顺序读一遍给 NPU。本文为一个**容量 128–256 GB、持续读 30 GB/s（电池档）/ 60 GB/s / 117 GB/s（插电档）**的定制闪存器件做自下而上的成本核算：拆开 plane / CE / channel / tR / 接口几个维度，看「带宽不靠堆容量」要花多少钱、多少瓦。
> **调研日期**：2026-10-14。**来源编号**：CN-S1、CN-S2……（见第 10 节）。同目录已有资料沿用原编号：NB-S#（`pc-cost-nand-bandwidth.md`）、PM-S#（`pc-cost-memory-prices.md`）。
> **汇率**：1 USD = 7.1 CNY。**单位**：1 GB = 8 Gb；1 Tb die = 128 GB。
> **标注约定**（与 NB / PM 两份文件一致）：
> - **性质**：实测（第三方仪器或拆解测量）/ 规格（厂商资料、ISSCC 论文、新闻稿给出的标称值）/ 推算（本文按公式算出，公式写在旁边）/ 假设（无来源、为核算设定的参数，单独列出并做敏感性）。
> - **置信度**：高（一手资料直接给出或多源一致）/ 中（权威媒体转述、单一一手来源、口径略不清）/ 低（推算链长、只有二手或论坛来源、各来源冲突）。
> - 查不到的写「未找到」。本文只收集与推算，不修改仓库其他文件。

---

## 0. 结论速览

1. **每 die 带宽的天花板现在是「通道」，不是阵列。** 当代 TLC die 阵列吞吐已到 1.6–3.1 GB/s（NB-S1~S4），而一条 8 bit NAND 通道在 3.6–4.8 GT/s 下只有 3.6–4.8 GB/s（JESD230G 最高 4800 MT/s，CN-S42；Samsung V10 5.6 Gb/s/pin，NB-S19）。所以 **plane 再多、tR 再短，只要 die 还挂在 8 bit 通道上，每 die 有效带宽就封顶在约 3–4.3 GB/s**（推算，中）。要突破必须加宽 die 的 I/O（双通道 / x16），或改成 TSV 宽 I/O（HBF 路线）。
2. **小容量 die 的面积由外围电路决定，不由存储阵列决定。** CuA / CBA 让外围藏到阵列下面（阵列可占 >90% 面积，CN-S19；Kioxia 称 2→4 plane 不用 CuA 面积 +15%，用 CuA 后 <1%，CN-S18）。但 die 容量越小、层数越高，阵列底面积越小，外围就藏不住了（CN-S20）。XL-FLASH 是实例：128 Gb SLC、16 plane、96.34 mm²，同代 512 Gb TLC 只要 86.13 mm²，**单位面积位数低 4.5 倍**，其中 3 倍来自 SLC，约 1.5 倍来自 16 plane 的外围开销（CN-S3，规格+推算，高/中）。
3. **低 tR 能省外围。** 每 die 需要的页缓冲（sense amp）总量 S = 每 die 带宽 × tR。以 8.6 GB/s 为例：SLC tR 4 µs 只需约 34 KiB；TLC tR 30 µs 需要约 252 KiB（推算）。所以「小容量 + 高带宽」的 die 应该选 **SLC、小 plane、短 tR**（XL-FLASH / Z-NAND 路线），而不是「TLC + 很多大 plane」。
4. **低延迟 NAND 实例**：Z-NAND（48L、64 Gb SLC、tR 3 µs、页 2/4 KB）；XL-FLASH 第 1 代（96L、128 Gb SLC、16 plane、4 KB 页、tR 4 µs、同时激活 4 plane）、第 2 代（BiCS5、256 Gb MLC、16 plane、同时激活 8 plane，tR 未公布）；HBF（256 Gb/die、16 die 1.6 TB/s，约 100 GB/s/die；plane 数和 tR 未公布，论文假设 25–64 plane、tR 1 µs）。**硅片层面每 bit 成本约为同代 TLC 的 4–4.5 倍**（推算，中）；市场价倍数缺乏同口径数据。
5. **NAND 制造成本**：用毛利率反推，TLC 全口径制造成本约 **$0.028–0.045/GB**（约 $3.5–5.8 每颗 1 Tb die，约 $0.09–0.14/mm²）。2026-10 的晶圆价 $0.227/GB 是制造成本的 **5–8 倍**（SanDisk FQ4'26 毛利率 84.6%，Kioxia 1QFY26 80%）；2025 年中低谷时只有约 1.3 倍（推算，中）。
6. **三档核算（基准值；正常周期价 / 2026 高位价）**：
   - 常规做法（1 Tb TLC 堆 die，参照基线）：30 GB/s 要 18 颗、2.3 TB，约 **¥1,390 / ¥4,990**；117 GB/s 要 67 颗、8.6 TB，约 **¥4,840 / ¥18,240**，功耗 64 W。
   - **A：现成 512 Gb / 1 Tb TLC 当 pSLC**：30 GB/s 要 8 颗、171 GB（512 Gb），约 **¥470 / ¥1,470**，约 12 W；117 GB/s 要 30 颗，约 ¥1,770 / ¥5,520，47 W，还要 30+ 通道。
   - **B：定制 256 Gb SLC、16 plane、双通道 I/O**：30 GB/s 要 4 颗、128 GB，约 **¥490 / ¥1,660**（不含 NRE），约 10 W；117 GB/s 要 14 颗，约 ¥1,750 / ¥5,840，39 W。
   - **C：HBF 式 TSV 堆叠 + 逻辑 base die、UCIe 上封装**：4-Hi 128 GB 的 HBF 级 die 可同时覆盖三档，约 **¥850 / ¥3,030**（不含 NRE），功耗 2.4–9.4 W；改用 XL-FLASH 级 die 堆叠（C-lite），30 GB/s 约 ¥680 / ¥2,260，117 GB/s 要 12-Hi，约 ¥1,680 / ¥6,420。
7. **推荐**：电池档先做 **A**（现成 die、无新 NAND 流片，成本最低）。60–117 GB/s 只有 **C** 能把功耗压到个位数到十几瓦，而且 die 数最少。B 夹在中间：30 GB/s 档不比 A 便宜，117 GB/s 档功耗又远高于 C。**最大不确定项**：C 依赖 HBF 级 core die 的面积、tR 与对端侧的小批量供货意愿，三项都没有一手数据（SanDisk 2027 年才有数据中心样品）；C 的能耗 0.05–0.15 nJ/B 也只是模型值。

---

## 1. 口径、公式与关键约束

| 符号 | 含义 | 取值 / 说明 |
|---|---|---|
| B | 目标持续读带宽 | 30 / 60 / 117 GB/s（主方案给定，本文不质疑） |
| C_min | 最小可用容量 | 128 GB（100 GB 模型 + 坏块 / 余量；目标区间 128–256 GB） |
| N_pl,act / P / tR | 同时激活的 plane 数 / 页大小 / 读时间 | 见第 2、4 节 |
| r_ch, η | 单通道速率、通道协议效率 | r_ch = 3.6 / 4.8 / 5.6 GT/s（8 bit 通道下 MT/s 数值上等于 MB/s）；η = 0.9（**假设**） |
| ρ | TLC 位密度（2027–28 代） | 25 Gb/mm²（区间 23.5–29：SK hynix V9 实测 23.52，BiCS10 29，CN-S22 / CN-S25） |

- **每 die 阵列吞吐**：b_array = N_pl,act × P ÷ tR。
- **每 die 有效带宽**：b_die = min(b_array, 该 die 独占的 I/O 带宽 = 端口数 × r_ch × η)。
- **所需 die 数**：N_die = max(⌈B ÷ b_die⌉, ⌈C_min ÷ c_die⌉)。带宽和容量两个约束取大者。
- **所需通道数**（die 挂在 NAND 通道上时）：N_ch ≈ ⌈B ÷ (r_ch × η)⌉，与 die 设计无关。在 4.8 GT/s 下，30 / 60 / 117 GB/s 分别需要 7 / 14 / 28 条通道；在 3.6 GT/s 下需要 10 / 19 / 37 条（推算，高）。
- **页缓冲需求**：S = b_die × tR。它决定外围面积的主要部分（第 3.3 节）。
- **die 价格（定制 die）**：die 硅面积按「同代 TLC 等效位数」计价：价格 = TLC 等效 GB × TLC $/GB × 定制溢价。TLC 等效 GB = 面积 × ρ ÷ 8。这样能直接套用两种价格口径。
- **两种价格口径**（TLC 晶圆级 $/GB，详见第 5 节）：
  - **正常周期 N**：$0.04 / 0.06 / 0.08（乐观 / 基准 / 悲观）。锚点：2025 年中 1 Tb TLC $4.80（$0.0375/GB），2025-11 $10.70（$0.084/GB）（PM-S14）。
  - **2026 高位 H**：$0.227 / 0.28 / 0.344。锚点：CFM 2026-10 1 Tb TLC 晶圆 $29，512 Gb 晶圆 $22（PM-S7）。
- **读能耗**：P = e × B，nJ/B 与 W/(GB/s) 数值相等。

---

## 2. 低延迟 / 高并行 NAND：实例与参数

### 2.1 参照参数表

| 器件 | 层数 / 代际 | 单 die 容量 / 位数 | plane 数 | 页大小 | tR | 接口 / 每 die 吞吐 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|---|---|---|---|
| **Samsung Z-NAND 第 1 代** | 48L V-NAND | **64 Gb SLC**（同代 TLC 为 256 Gb，容量 1/4） | **未找到**（论文与媒体均未披露） | **2 KB / 4 KB** | **3 µs**（同代 TLC 45 µs）；tPROG 100 µs | DDR x8 / x16 两种模式；控制器用 2 通道各传 2 KB 把 tDMA 从 8 µs 压到 4 µs；SSD 读延迟 15.9 µs | 规格（ISSCC 2018 论文 20.2）/ 高 | CN-S6，CN-S7，CN-S8 |
| Z-NAND 每 die 吞吐（论文换算） | — | — | — | — | — | 16 die 87.4 GB/s → 约 **5.5 GB/s/die**（等于 4 plane × 4 KiB ÷ 3 µs） | 论文假设 / 低 | CN-S12 |
| Z-NAND 第 2 代（MLC） | — | MLC | 未找到 | 未找到 | 未找到 | FMS 2017 称第 2 代成本下降 | 规格（定性）/ 中 | CN-S7 |
| Z-NAND 复活版（FMS 2025） | 「改进的 V-NAND 堆叠」 | 未公布 | 未公布 | 未公布 | 未公布 | 目标「最高 15 倍性能、功耗 −80%」（对比常规 NAND），GPU 直连（GIDS） | 规格（高管口述，经 DigiTimes / Tom's 转述）/ 中低 | CN-S9 |
| **Kioxia XL-FLASH 第 1 代** | 96L BiCS4（无 CuA） | **128 Gb SLC** | **16**（同代 TLC 为 2 plane）；**同时激活 4 plane** | **4 KB** | **4 µs**（ISSCC 2020 论文标题 tR=4µs；官网写 <5 µs）；tPROG 75 µs | 标准 Toggle 接口；die 面积 **96.34 mm²** | 规格（ISSCC 2020 论文 13.5）/ 高 | CN-S1，CN-S3，CN-S4，CN-S5，CN-S2 |
| XL-FLASH 第 1 代阵列吞吐 | — | — | — | — | — | 4 × 4096 B ÷ 4 µs = **4.1 GB/s**（按 4 plane 同时激活）；若 16 plane 全开为 16.4 GB/s（CN-S12 论文按此算出 16 die 262 GB/s，见第 9 节冲突） | 推算 / 中 | 同上 |
| **XL-FLASH 第 2 代** | BiCS5（112L） | **256 Gb MLC**（另支持 SLC 模式） | 16，**同时激活 8 plane** | 未公布（官网 4 KB 为通用表述） | **未找到**（官网 <5 µs 未区分代际） | 封装 2/4/8 die；接口速率未找到 | 规格（Kioxia 发言人）/ 高（plane），未找到（tR） | CN-S1，CN-S2 |
| Kioxia GP1 SSD（XL-FLASH 第 2 代） | — | — | — | 512 B 访问粒度 | — | PCIe 6.0；512 B 随机读最高 1000 万 IOPS（约 5.1 GB/s，属 IOPS 指标，非带宽）；2026 年底送样 | 规格（2026-08-04）/ 高 | CN-S10 |
| **SanDisk HBF core die** | BiCS（CBA） | **256 Gb**；位数未公布（学术论文按 SLC 10⁵ P/E 建模） | **未公布**；论文假设 25 plane（CN-S12）或 64 plane（CN-S13） | 论文假设 4 KiB | SanDisk 口径为「4 KiB 读 µs 量级」；论文假设 1 µs，其他论文取 4–20 µs | TSV 连逻辑 base die；1.6 TB/s ÷ 16 die ≈ **100 GB/s/die** | 每 stack 带宽为规格（高）；每 die 带宽为推算（中）；plane / tR 为论文假设（低） | NB-S20，CN-S12，CN-S13，CN-S16，CN-S17 |
| HBF 进度 | — | — | — | — | — | 首颗 HBF die 已流片；推理产品样品 2027 年（SanDisk 2026-08-13 投资者日） | 规格 / 高 | CN-S16 |
| 参照：96L 512 Gb TLC（Kioxia / WD，ISSCC 2018） | 96L | 512 Gb TLC | **2**（每 plane 256 Gb） | 16 KB | **58 µs**；tPROG 561 µs | 86.13 mm²（5.94 Gb/mm²） | 规格 / 高 | CN-S3，CN-S19 |

### 2.2 ISSCC 上的高 plane 数设计

| 设计 | plane 数 | 说明 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|
| ISSCC 2021 各家 TLC / QLC | 2 → **4** | CuA 普及后 4 plane 成为标配；Kioxia / WD 为实现「异步独立 plane 读」，不再让各 plane 共用电荷泵 | 规格 / 高 | CN-S19 |
| Micron 232L（2022）/ G9 276L（2024）1 Tb TLC | **6** | G9 沿用 6 plane | 规格 / 高 | CN-S23 |
| SK hynix 321L 2 Tb QLC（2025） | 4 → **6** | — | 规格 / 中 | NB-S17 |
| Kioxia / SanDisk ISSCC 2026「2Tb 4b/Cell **6-Plane**」 | **6** | 37.6 Gb/mm²，推算 die 约 55 mm² | 规格（论文标题）/ 中 | CN-S26 |
| BiCS8 218L 1 Tb TLC | 4 个逻辑 plane（数据库注：物理 8 个子 plane） | 子 plane 拆分细节无一手资料 | 数据库记录 / 低 | NB-S1 |
| **XL-FLASH（ISSCC 2020，13.5）** | **16** | 目前唯一查到的 16 plane 量产 NAND；从 2 plane 拆到 16 plane，**字线延迟降到约 1/20** | 规格 / 高 | CN-S3 |
| 8 plane / 16 plane 的 **TLC** ISSCC 设计 | — | **未找到** | — | — |

### 2.3 价格或相对 TLC 的 $/GB 倍数

| 项 | 数值 | 日期 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|
| Samsung 983 ZET（Z-NAND，PCIe 3.0 x4） | 480 GB $999.99（**$2.08/GB**）；960 GB $2,075.85（**$2.16/GB**）；按当时网上价格比 Optane P4800X 每 GB 便宜约 35% | 2019-02-19 | 零售价 / 中（批量价不公开） | CN-S6 |
| Kioxia FL6（XL-FLASH，PCIe 4.0） | 1.6 TB $922.50（约 $0.58/GB，美国零售商，特订）；800 GB €1,143.82 未税（约 €1.43/GB，欧洲经销商） | 页面无日期，访问于 2026-10-14 | 零售标价 / 低 | CN-S11 |
| 硅片层面每 bit 成本倍数（XL-FLASH） | 1.33 Gb/mm² ÷ 同代 TLC 5.94 Gb/mm² → **约 4.5 倍** | 2020-03 | 推算 / 中高 | CN-S3 |
| 硅片层面每 bit 成本倍数（Z-NAND） | 同为 48L，64 Gb 对 256 Gb → **至少 4 倍**（前提是 die 面积相近；Samsung 未公布面积，福田昭推测物理阵列约 85 Gb、只用 64 Gb） | 2018-03 | 推算 / 中低 | CN-S7 |
| HBF | 无官方 $/GB；「与 HBM 成本相近、容量 8–16 倍」，推算 **$0.9–4.5/GB** | 2026-08/09 | 推算 / 低 | PM-S27~S30 |
| XL-FLASH / Z-NAND 相对同期 TLC SSD 的**市场价**倍数 | **未找到同口径数据**（零售价与企业 TLC 合约价无法对齐） | — | — | — |

---

## 3. NAND die 面积构成

### 3.1 当代 die 面积与位密度

| Die | 层数 | 容量 | 面积 (mm²) | 位密度 (Gb/mm²) | plane | 日期 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|---|---|---|---|
| **SK hynix V9（H25GTD0）** | 321 | 1 Tb TLC | **43.54**（die seal 面积） | **23.52** | 未找到 | 2026-07-13 | **实测**（TechInsights 拆解；保留 PUC 结构）/ 高 | CN-S22 |
| Kioxia BiCS10 | 332 | 1 Tb TLC | 约 35.3（推算 = 1024 ÷ 29） | **29**（「最高位密度、最小 1 Tb 芯片」） | 4（纵向排布） | ISSCC 2025；2026-07 出样 | 规格 / 高（密度），推算 / 中（面积） | NB-S13，CN-S25 |
| Samsung V10 | 400+ | 1 Tb TLC | 约 36.6（推算） | **28** | 未找到 | ISSCC 2025 | 规格（论文标题）/ 高 | NB-S19，CN-S27 |
| Micron G9 | 276 | 1 Tb TLC | **约 48.9** | **约 21**（Micron 称比 232L 密度 +44%） | 6 | 2024-07-31 | 推算（AnandTech）/ 中 | CN-S23 |
| Kioxia BiCS8 | 218 | 1 Tb TLC | 约 56（推算） | 约 18.2（推算 = 29 ÷ 1.59；Kioxia 称 BiCS10 比 BiCS8 密度 +59%） | 4 | 2026-07-03 | 推算 / 中 | CN-S25 |
| Micron B58R | 232 | 1 Tb TLC | 约 70.1 | 14.6 | 6 | 2022–2024 | 规格 + 推算 / 中 | CN-S23 |
| YMTC | 232 | 1 Tb TLC | 68.15 | 15.03 | 6 | 2022 | 实测（TechInsights，经检索摘要转述）/ 中低 | CN-S28 |
| **SK hynix V8** | 238 | **512 Gb** TLC | **35.58** | 约 14.39 | 4 | 2023-06 | 规格（公司口径，AnandTech 转述）/ 中 | CN-S24，NB-S5 |
| SK hynix V7 | 176 | 512 Gb TLC | 47.4 | 10.8 | 4 | ISSCC 2021 | 规格 / 高 | CN-S18，CN-S19 |
| Micron B47R | 176 | 512 Gb TLC | 约 49.8 | 10.3 | 4 | — | 推算 / 中 | CN-S23 |
| Kioxia / SanDisk（ISSCC 2026） | 332 | 2 Tb QLC | 约 55（推算） | **37.6** | 6 | 2025-11-27 预告 | 规格（论文标题）+ 推算 / 中 | CN-S26 |
| ISSCC 2021 区间 | 144–176 | 1 Tb：**74–98**；512 Gb：**47–60** | — | — | 4 | 2021-04 | 规格汇总 / 高 | CN-S18 |
| **XL-FLASH** | 96 | **128 Gb SLC** | **96.34** | **1.33** | 16 | 2020-03 | 规格（ISSCC 2020）/ 高 | CN-S3 |
| 同代对照 | 96 | 512 Gb TLC | 86.13 | 5.94 | 2 | 2018 | 规格 / 高 | CN-S3 |
| 当代 **256 Gb** die | — | 256 Gb | **未找到**（CFM 仍报 256 Gb TLC 晶圆价 $11，PM-S7）；按 ρ = 25 推算阵列约 10 mm²，但这个尺寸下外围几乎必然藏不住（见 3.3 节） | — | — | — | 推算 / 低 | — |
| 当代 512 Gb die（2027 代） | — | 512 Gb TLC | 按 ρ = 23.5–29 推算阵列 18–22 mm²；现役 238L 为 35.58 mm² | — | 4 | — | 推算 / 低 | — |

### 3.2 外围电路：占比、CuA / CBA 能藏多少

| 事项 | 数值 / 说法 | 日期 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|
| 外围构成 | 页缓冲、sense amp、电荷泵、行解码等；CuA 把它们大部分放到阵列下方 | 2021-02 | 规格（综述）/ 高 | CN-S19 |
| CuA 后阵列可用面积 | **>90%** die 面积可用于存储阵列 | 2021-02 | 媒体综述 / 中高 | CN-S19 |
| 不用 CuA 时外围占比 | 常规设计外围占 die 面积 **20–30%**；128 层以上可能 **>50%** | 专利背景 | 专利 / 中低 | CN-S21 |
| 页缓冲占比 | 页缓冲约占 die 面积 **20–40%**；随堆叠升高可 **>50%** | 专利背景 | 专利 / 中低 | CN-S21 |
| **plane 数增加的面积代价**（Kioxia / WD，ISSCC 2019，128L 512 Gb） | 2 plane → 4 plane：**面积约 +15%**；引入 CuA 后 **增加 <1%** | 2021-04（福田昭转述） | 规格 / 高 | CN-S18 |
| CuA 的「地下室」 | 阵列下方的空间可放额外的 sense amp，没有额外 die 面积代价；层数升高后同容量阵列底面积缩小，**厂商只能把 die 容量做大，以保证外围完全藏在阵列下** | 2020 秋 | 期刊综述（IEEE SSC Magazine）/ 中（只读到检索摘录） | CN-S20 |
| CuA 的限制 | 外围只能用到阵列那么大的面积，放不下的部分要摆到阵列旁边；电荷泵大电容在 CuA 下难做（Samsung ISSCC 2021） | — | 专利 + 媒体 / 中 | CN-S21，CN-S19 |
| Kioxia CBA | CMOS 外围与阵列在两片晶圆上分别制造、铜直接键合；两边各自用最优工艺，消除阵列高温退火对 CMOS 的损伤 | 2023–2024 | 规格 / 高 | CN-S44 |
| SK hynix PUC | V9 321L 仍用 PUC | 2026-07 | 实测 / 高 | CN-S22 |
| 异步独立 plane 读 | 需要各 plane 独立电荷泵（不再共用），外围面积随 plane 数线性增加 | 2021-02 | 规格 / 中高 | CN-S19 |

### 3.3 每增加一个 plane 外围增加多少（推算）

直接的「每 plane mm²」数据**未找到**。下面用两个一手锚点推算（推算，低）：

| 锚点 | 推算 | 结果 |
|---|---|---|
| **锚点 1**：Kioxia ISSCC 2019，128L 512 Gb（66 mm²，CN-S19），2→4 plane 面积 +15%（不用 CuA） | 0.15 × 66 ≈ 10 mm²，分摊到新增的 2 个 plane | **约 5 mm² / plane**（16 KB 页、TLC、2019 年外围工艺） |
| **锚点 2**：XL-FLASH 96.34 mm² 对同代 TLC（CN-S3） | 128 Gb SLC = 384 Gb TLC 等效 → 按 5.94 Gb/mm² 需 64.6 mm²；多出 31.7 mm² 分摊给多出的 14 个 plane（含 SLC 高速电路） | **约 2.3 mm² / plane**（4 KB 页、SLC、2020 年、无 CuA）；**总开销系数 1.49** |
| 当代换算（**假设**外围工艺面积缩到 2019–2020 年的 0.5–0.7 倍） | — | 16 KB TLC plane：**2–3.5 mm²**；4 KB SLC plane：**1–1.6 mm²**；固定部分（I/O、电荷泵、控制逻辑）3–6 mm² |

**能否藏住的判据**：N_plane × a_plane + A_fixed ≤ A_array = 容量 ÷ ρ。用上面的当代值推算：

| die 方案 | 阵列面积 | 外围面积 | 结论 |
|---|---|---|---|
| 256 Gb **SLC**、16 plane × 4 KB | 768 Gb TLC 等效 ÷ 25 ≈ 30.7 mm²（加 plane 切分约 34 mm²） | 16 × (1–1.6) + 3–6 = 19–32 mm² | 基本藏得住，die 约 **34–40 mm²**，开销系数约 1.1–1.3 |
| 128 Gb SLC、16 plane × 4 KB | 约 15–17 mm² | 19–32 mm² | 藏不住，由外围决定面积（19–32 mm² 只装 16 GB） |
| 256 Gb **TLC**、16 plane × 16 KB | 约 10 mm² | 16 × (2–3.5) + 3–6 = 35–62 mm² | 完全由外围决定；每 bit 面积比 SLC 方案还差 |
| HBF 级 256 Gb SLC、25–64 plane × 4 KB | 31–42 mm²（ρ 25 / BiCS8 18.2） | 25–102 mm² + TSV 区 2–5 mm² | 64 plane 时外围超过阵列；die 约 **42–88 mm²**（开销系数 1.3–2.6） |

**页缓冲需求 S = b_die × tR**（推算，高；它决定上表中外围的主要部分）：

| 情形 | b_die | tR | 需要的页缓冲 |
|---|---|---|---|
| B 类 SLC die | 8.6 GB/s | 4 µs | 约 **34 KiB** |
| pSLC（TLC die 当 SLC 用） | 4.3 GB/s | 15 µs | 约 63 KiB（而且 TLC 硬件按 5 级锁存配置） |
| TLC（G9 级） | 4.3 GB/s | 32 µs | 约 134 KiB |
| TLC、双倍带宽 | 8.6 GB/s | 30 µs | 约 **252 KiB** |
| HBF（100 GB/s/die） | 100 GB/s | 1 µs | 约 98 KiB |

---

## 4. tR 与 plane 尺寸 / 每 cell 位数

| 情形 | tR | 性质 / 置信度 | 来源 |
|---|---|---|---|
| **SLC（小 plane、专用设计）** | Z-NAND **3 µs**；XL-FLASH **4 µs**（字线延迟降到 1/20） | 规格 / 高 | CN-S3，CN-S7 |
| SLC（常规大 plane） | **20–25 µs**（综述）；老专利约 20 µs | 综述 + 专利 / 中 | CN-S29，CN-S30 |
| **pSLC（当代 TLC die 当 SLC 用）** | **未找到一手值**。推算 **12–20 µs**：Swissbit 称 pSLC 读速约为 TLC 的 2 倍，当代 TLC tR 为 32–40 µs；另有专利称一次位线放电 25–30 µs、TLC 读需最多 3 次放电（老一代 512 GB 级产品） | 推算 / 低 | CN-S31，CN-S30，NB-S2/S4 |
| MLC | 约 SLC 的 2 倍（专利）；综述 40–110 µs | 专利 + 综述 / 中低 | CN-S29，CN-S30 |
| **TLC（当代）** | G9 **32 µs**；V8 / BiCS8 **40 µs**；BiCS10 约 36 µs（推算）；B58R 61 µs | 数据库 / 中 | NB-S1~S4，NB-S13 |
| TLC（ISSCC 2018–2021） | 40–58 µs（Samsung ISSCC 2021，层数当时未公开，40 µs；Kioxia 96L 58 µs）；Samsung 48L 45 µs | 规格 / 高 | CN-S19，CN-S7 |
| QLC | 平均 85–170 µs（Intel 144L 平均 85 µs、最大 128 µs）；SK hynix 1 Tb QLC（ISSCC 2020）110 µs | 规格 / 高 | CN-S19 |
| **缩短位线 / 字线能降到多少** | 2 → 16 plane：字线延迟约降到 **1/20**（XL-FLASH）；SK hynix 176L 把行解码放到 plane 中央，字线 R、C 各减半 | 规格 / 高 | CN-S3，CN-S18 |
| 学术模型 | 常规 plane（64–128 层堆叠、700–2,800 块/plane）读延迟 20–50 µs；缩小到 256 × 2048 × 128 的 plane 后约 **2 µs**（SLC，模型值） | 论文模型 / 低 | CN-S32 |
| HBF | SanDisk「4 KiB 读 µs 量级」；论文假设 1 µs，另有论文取 4 µs、20 µs，区间 1–30 µs | 论文 / 低 | CN-S12，CN-S13 |

**规律**（推算，中）：tR ≈ 预充 + 感测 × 感测次数 + 放电。缩小 plane 主要压低字线 RC（字线变短）和位线预充时间（位线变短）；改成 SLC 则把感测次数降到 1、不再需要多级参考电压。两者叠加，从 TLC 的 30–60 µs 降到 SLC 小 plane 的 3–4 µs，大约 10–20 倍；再往 1 µs 走，需要更激进的阵列拆分（HBF），面积代价由 CBA 键合来消化（CN-S12 原文意见）。

---

## 5. NAND 制造成本与市场价

### 5.1 毛利率（市场价与成本的关系）

| 公司 / 季度 | 毛利率 | 日期 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|
| SanDisk FY2024（全年） | 15.8%（Non-GAAP） | 2025-08-14 | 规格（财报）/ 高 | CN-S34 |
| SanDisk FY2025（全年）/ FQ4'25（截至 2025-06） | **30.3%** / **26.4%** | 2025-08-14 | 规格（财报）/ 高 | CN-S34 |
| SanDisk FQ2'26 / FQ3'26 / **FQ4'26**（截至 2026-07-03） | 51.1% / 78.4% / **84.6%** | 2026-08-06 | 规格（财报，B&F 转述）/ 高 | CN-S33 |
| SanDisk 长协（NBM）毛利率 | 约 80%（「价格继续上涨还会更高」）；FY27 一半位产出已锁定长协 | 2026-08-06 | CFO 口述 / 中高 | CN-S33 |
| **Kioxia 1QFY26**（2026 年 4–6 月） | **80%**（不含合资项目 82%）；营业利润率 75%；ASP 环比约 +70%；出货位数环比低个位数增长 | 2026-07-31 | 规格（财报，TrendForce 转述）/ 高 | CN-S35 |
| Yole：NAND 价格 | 同比约 +280%，**>$0.24/GB** | 2026 | 机构 / 中低（检索摘要） | CN-S36 |

### 5.2 制造成本推算（不是市场价）

TrendForce / Yole / TechInsights 的晶圆成本模型都在付费墙后，**一手的每片晶圆制造成本未找到**。下面用「价格 × (1 − 毛利率)」做两点反推（推算，中；毛利率是公司整体口径，含 SSD 业务，只能近似）：

| 锚点 | 价格 | 毛利率 | 制造成本 / 1 Tb die | $/GB |
|---|---|---|---|---|
| 2025 年中低谷 | 1 Tb TLC $4.80（PM-S14） | 26.4%（SanDisk FQ4'25） | **$3.5** | **$0.028** |
| 2026-10 高位 | 1 Tb TLC 晶圆 $29（PM-S7） | 80–84.6% | **$4.5–5.8** | **$0.035–0.045** |

- **取值**：TLC 全口径制造成本 **$0.028 / 0.036 / 0.045 per GB**（乐观 / 基准 / 悲观），约 **$3.6–5.8 每颗 1 Tb die**。
- **每 mm²**：按 ρ = 25 Gb/mm² 折算为 **$0.09–0.14/mm²**（推算，中低）。
- **每片晶圆**：TechInsights 称 300 mm 晶圆的 NAND 容量最高可达 128 TB，约合 1,000 颗 1 Tb die（CN-S37）；按每片 1,000–1,400 颗良品 die 计，约 **$3,500–8,100/片**（推算，低）。
- **市场价 / 制造成本**：2026-10 约 **5–8 倍**；2025 年中约 **1.3 倍**；正常周期（毛利率 25–35%）约 **1.3–1.5 倍**。
- **对本器件的含义**：在 2026 年这种短缺期，晶圆产能是稀缺资源，原厂会按「这块硅拿去做 TLC 能卖多少」给定制 die 定价（机会成本）。所以本文对定制 die 按「同代 TLC 等效位数 × TLC 价格 × 定制溢价」计价，而不是按成本加成计价。

### 5.3 逻辑 die（主控 / base die）的晶圆与掩膜价

| 节点（TSMC 300 mm） | 晶圆价 | 掩膜组 | 每 mm² 良品成本（推算：约 52,000 良品 mm²/片） | 日期 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|---|---|
| 28 nm | 约 $3,000 | 约 $1M | 约 $0.06 | 2026-09 | 分析师汇总 / 中 | CN-S38 |
| N16 / N12 | 约 $5,500 | 约 $1.8M | 约 **$0.11** | 2026-09 | 同上 | CN-S38 |
| N7（N6 同级） | 约 $9,500 | 约 $3.5M | 约 **$0.18** | 2026-09 | 同上 | CN-S38 |
| N5 / N4 | 约 $18,500–20,000 | 约 $6.5M | 约 $0.37 | 2026-09 | 同上 | CN-S38 |

**TSV 堆叠的成本**：SK hynix 2012 年主题演讲称 TSV 堆叠的制造成本是引线键合堆叠的 **1.3 倍**，**TSV 本身让制造成本 +25%**（设计面积损失、额外工序、凸点 / 堆叠 / 背面加工、逐层测试）（CN-S39；年代较早，中）。HBM 的分项成本（TSV、键合、base die）都在 Yole 付费报告中，**未找到**公开数字。NAND 常规封装测试的每 die 成本也**未找到**，本文按 **$0.5 / 1.0 / 1.5 每 die（假设）** 计。

---

## 6. 主控、通道与主机接口

### 6.1 NAND 通道速率与所需通道数

| 事项 | 数值 | 日期 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|
| JEDEC JESD230G（ONFI 与 Toggle 阵营联合） | 最高 **4800 MT/s**；新增独立命令 / 地址总线（SCA） | 2024-11-18 | 规格 / 高 | CN-S42 |
| BiCS10 / Samsung V10 | 4.8 Gb/s / **5.6 Gb/s/pin** | 2025–2026 | 规格 / 高 | NB-S13，NB-S19 |
| x16 NAND I/O 先例 | Z-NAND 的 I/O 电路同时支持 x8 和 x16 DDR 模式 | 2018 | 规格（ISSCC 摘要，经检索摘录）/ 中 | CN-S8 |
| 所需 8 bit 通道数（η = 0.9） | @3.6：10 / 19 / 37；@4.8：**7 / 14 / 28**；@5.6：6 / 12 / 24（30 / 60 / 117 GB/s） | — | 推算 / 高 | — |

### 6.2 主控的成本与功耗

| 主控 | 通道 | 制程 | 功耗 | 价格 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|---|---|
| SMI SM2508（客户端 PCIe 5.0） | 8 通道、32 CE、3600 MT/s | TSMC N6 | 主控约 **3–3.5 W**（整盘 <7 W）→ 14.9 GB/s 下约 **0.20–0.23 nJ/B** | 未找到 | 规格 / 中（口径不一） | CN-S40 |
| Phison X3（企业 PCIe 6.0） | 16 通道 | — | 约 7 W，28 GB/s → 约 **0.25 nJ/B**（仅主控） | 未找到 | 规格 / 中高 | NB-S25，NB-S26 |
| Marvell Bravera SC6 | 16 通道 @3600 | — | — | 未找到 | 规格 / 中 | NB-S25 |
| 32 通道以上的客户端主控 | **未找到**（无产品） | — | — | — | — | — |
| 「套片」主控价格（Phison / SMI） | — | — | — | 1,000 片量级 **$12–17**（论坛帖，年代约 2018） | 论坛 / 低 | CN-S41 |

**本文主控价格取值**（推算 + 假设，低）：die 面积 × 逻辑晶圆成本 + 封装测试，再加 40–60% 毛利。
- 8 通道：die 20–30 mm² @N6（**假设**）→ 硅成本 $3.6–5.4，加封测 $2–4 → 售价 **$10 / 15 / 25**。
- 16 通道：**$20 / 35 / 60**。
- 32 通道（定制，受 I/O 焊盘面积限制）：**$40 / 70 / 120**。另有掩膜 $3.5M（N7）及设计 NRE，后者未找到。
- 读路径以顺序大块读为主，映射粒度可以很粗（例如 1 MiB 粒度下 100 GB 只需约 100 KB 映射表），**本文按无 DRAM 设计计价**（假设）。

### 6.3 主机侧接口：30 / 60 / 117 GB/s 需要什么

| 接口 | 原始带宽 | 有效带宽（估） | 能效 | 覆盖档位 | 性质 / 置信度 | 来源 |
|---|---|---|---|---|---|---|
| PCIe 6.0 x4 / x8 / x16 | 30.25 / 60.5 / 121 GB/s | 约 28 / 56 / 112–115 GB/s | 主控整体 0.2–0.25 nJ/B（含 PHY、LDPC、FTL）；PHY 单独的 pJ/bit **未找到** | x4 只到电池档的 93%；60 档要 x8；117 档要 x16（勉强） | 规格 + 推算 / 高 | NB-S25 |
| **UCIe-S（2D，有机基板）x16** | 16 lane × 32 GT/s = **64 GB/s/方向**（UCIe 3.0 可到 64 GT/s） | 按 HBF 规范的 75% AXI 效率计约 48 GB/s | **0.5 pJ/b（≤16G）/ 0.6 pJ/b（>16G）**，约 0.005 nJ/B；传输距离 25 mm | 30 档 1 个模块；60 档 2 个；117 档 3 个（或 64 GT/s 下 2 个） | 规格（Intel / AMD，HOTI 2025）+ 推算 / 高 | CN-S43，CN-S14 |
| UCIe-A（2.5D）x64 | 32 GT/s 下 **256 GB/s** | 约 192 GB/s | 0.25–0.3 pJ/b；传输距离 2 mm | 单模块覆盖三档；需要硅中介层 / 桥，PC 上成本高 | 规格 / 高 | CN-S43，CN-S14 |
| LPDDR 式并行直连（参考） | 64 bit LPDDR5X-8533 = 68 GB/s；128 bit = 137 GB/s | — | 实测 LPDDR5 PHY **2.8 pJ/b**；HBM3 0.9 pJ/b | 需要 SoC 提供非标准的「闪存口」，协议需自定义 | 规格 + 推算 / 中 | CN-S43 |
| SoC 直连 NAND 通道（类 Apple，把主控集成进 SoC） | 每 8 bit 通道约 15 个信号 | — | — | 117 档要约 28 通道、约 400+ 个引脚，不现实 | 推算 / 低（Apple 架构细节只有论坛来源） | — |

**HOTI 2025 的佐证**：Intel / AMD 认为笔记本 / PC 的封装内存（Apple M 系列、Lunar Lake 的 LPDDR）可以迁移到 UCIe-S。UCIe-S x32 在 110 µm 凸点间距下只占 1.143 mm × 1.54 mm（CN-S43）。这正是方案 C 在 PC 上的主机接口形态。

### 6.4 HBF 逻辑 base die 承担什么

| 功能 / 参数 | 内容 | 性质 / 置信度 | 来源 |
|---|---|---|---|
| 模块 | UCIe 控制器、UCIe PHY、base die 控制器、管理 / 调试 | 规范摘要（OCP *HBF High-Level Base Die Specification v0.7.0*，二手解读）/ 中 | CN-S14 |
| 职责 | 主机流量管理、UCIe 协议、NAND 命令管理、数据搬运、**ECC**、错误处理、调度、初始化、**TSV 冗余映射**、**页读计数**（应对读干扰） | 同上 / 中 | CN-S14 |
| 通道结构 | 最多 **16 个独立主机通道**，每个是 64 bit 全双工 UCIe 3.0 链路；各通道访问各自独立的 NAND 池，互不可见 | 同上 / 中 | CN-S14 |
| 带宽 | Grade 3：32 GT/s × 64 bit × 16 通道 = 4,096 GB/s 原始；按 75% AXI 效率为 **3,072 GB/s**；单个 x64 模块 32 GT/s 下 256 GB/s；通道长度约 2 mm | 同上 / 中 | CN-S14 |
| 协议 | AXI over UCIe（非 NVMe）；base die 做通道内地址映射、ECC、坏块管理，跨通道的全局地址由主机映射 | 论文 / 中低 | CN-S15 |
| 片上缓冲 | 论文假设 3.13 MB SRAM staging buffer（预取 / 双缓冲）；另有方案在 base die 上做稀疏检索与地址翻译 | 论文假设 / 低 | CN-S12，CN-S13 |
| OCP 规范原文 | 下载链接受 Cloudflare 拦截，**未读到原文** | — | — |

**对 PC 器件的启示**：base die 实际上就是一颗「去掉 PCIe / NVMe / DRAM 的 SSD 主控 + 宽 I/O PHY」。在 PC 上缩小规模时，只需 1–3 个 UCIe-S x16 模块，而不是 16 个通道。所以面积主要花在 ECC 引擎、调度器与 SRAM 上，本文按 20–60 mm²（N12–N7）计（**假设**）。

---

## 7. 定制方案核算

### 7.1 方案参数

| 项 | 0 基线：1 Tb TLC 常规堆 die | A1：1 Tb TLC 当 pSLC | A2：512 Gb TLC 当 pSLC | B：定制 256 Gb SLC 16 plane | C-lite：B 类 die + TSV 堆叠 | C-full：HBF 级 die 4-Hi |
|---|---|---|---|---|---|---|
| 单 die 可用容量 | 128 GB | 42.7 GB | 21.3 GB | 32 GB | 32 GB | 32 GB |
| plane × 页 | 4–6 × 16 KB | 6 × 16 KB | 4 × 16 KB | 16 × 4 KB（8–16 个同时激活） | 16 × 4 KB（8 / 12 / 16 个同时激活） | 25–64 × 4 KB |
| tR | 32–61 µs | pSLC 12–20 µs（推算） | 同左 | 3–5 µs | 3 / 4 / 4 µs | 约 1 µs（论文假设） |
| die I/O | 8 bit 通道，2 die/通道 | 8 bit 通道，1 die/通道 @4.8 GT/s | 同左 | **双 8 bit 端口** @5.6 / 4.8 / 3.6 GT/s（或 x16） | TSV 宽 I/O → base die | TSV |
| **每 die 有效带宽** | 1.86 / 1.75 / 1.64 GB/s | **4.3 / 3.9 / 3.0**（受通道限制） | 同左（4 plane 时更依赖 tR ≤15 µs） | **10.1 / 8.6 / 6.5** | **21.8 / 12.3 / 8.2**（阵列限制） | 约 100（受主机接口限制） |
| die 面积（ρ = 25） | 约 41 | 35–44 | 18–22（**外围可能藏不住**） | **34–46** | 35–51（含 TSV 区 5–10%） | 42–88 |
| TLC 等效 GB / die | 128 | 128 | 64 | 96 × (1.1 / 1.3 / 1.5) | 96 × (1.1 / 1.3 / 1.5) × (1.05 / 1.08 / 1.10) | 96 × (1.3 / 1.8 / 2.6) × TSV 系数 |
| 每 die 制造成本（原厂） | $3.6–5.8 | $3.6–5.8 | $1.8–2.9 | **$3.0–6.5** | $3.1–7.1，再加 TSV 工序 ×1.15–1.35 | $3.7–12.4，再加 TSV ×1.15–1.35 |
| 每 die 价格：正常周期 N | $5–10 | $5–10 | $2.6–7.7（小 die 每 GB 溢价 1.0–1.5×，CFM 实际比值 1.52） | **$5–23**（含定制溢价 1.2–2.0×） | $6–34 | $7–59 |
| 每 die 价格：2026 高位 H | $29–44 | $29–44 | $14.5–33 | **$29–99** | $35–147 | $41–255 |
| 主控 / 逻辑 | 8 通道 SSD 主控若干 | 7–39 通道主控 | 同左 | 8–38 通道（端口数 × die 数） | base die：$3.3 / 11 / 22（20–60 mm² @N12–N7） | 同左 |
| 封测 / 堆叠 | $0.5–1.5 / die | 同左 | 同左 | 同左 | 每层 $1.5–4 + 每 stack $2–8；SoC 共封装 $5–25（均为**假设**） | 同左 |
| 读能耗（nJ/B） | 0.42 / 0.55 / 0.70（SSD 实测 / 规格） | **0.30 / 0.40 / 0.55** | 同左 | **0.25 / 0.33 / 0.45** | **0.06 / 0.10 / 0.15** | **0.05 / 0.08 / 0.12** |

**能耗取值依据**（推算，低）：
- SSD 盘级 0.42–0.71 nJ/B（NB-S6~S11）可拆成两部分：主控 0.20–0.25 nJ/B（SM2508、Phison X3）+ NAND 侧（die 阵列 + 通道 I/O + 其他）0.2–0.45 nJ/B。
- **A** 用 pSLC，单次感测，阵列能耗下降，但通道 I/O 和主控不变。
- **B** 用 SLC、短位线，阵列能耗更低，主控不变。
- **C** 去掉长距离 NAND 通道和 PCIe 主控：阵列 0.03–0.064 nJ/B（SPLASH 按 Kioxia ISSCC 2025 取 64 pJ/B，CN-S13；NB 文件按 40–80 W / 1.6 TB/s 推得 0.025–0.05）；base die 的 ECC 与调度约 0.02–0.06（**假设**）；UCIe-S 约 0.005。

### 7.2 三档合计成本（$ / ¥，乐观–悲观，括号内为基准）

**正常周期价口径 N**（TLC $0.04–0.08/GB）：

| 方案 | 30 GB/s：die 数 / 容量 / 成本 | 60 GB/s | 117 GB/s |
|---|---|---|---|
| 0 基线 | 17–19 颗 / 2.2–2.4 TB / $119–291（**$196，¥1,390**） | 33–37 颗 / 4.2–4.7 TB / $231–570（$384，¥2,730） | 63–72 颗 / 8.1–9.2 TB / $413–1,014（**$682，¥4,840**） |
| A1 1 Tb pSLC | 7–10 / 299–427 GB / $52–185（$89，¥635） | 14–20 / 597–853 GB / $102–363（$179，¥1,270） | 28–39 / 1.2–1.7 TB / $200–611（$335，¥2,380） |
| **A2 512 Gb pSLC** | **7–10 / 149–213 GB / $34–160（$66，¥471）** | 14–20 / 299–427 GB / $66–312（$133，¥943） | 28–39 / 597–832 GB / $129–511（$249，¥1,770） |
| **B 定制 SLC** | **4–5 / 128–160 GB / $35–191（$69，¥489）** | 6–10 / 192–320 GB / $56–373（$126，¥892） | 12–19 / 384–608 GB / $110–619（$246，¥1,750） |
| C-lite TSV | 4-Hi / 128 GB / $41–208（$96，¥679） | 4–8-Hi / 128–256 GB / $41–361（$166，¥1,180） | 8–16-Hi / 256–512 GB / $71–666（$237，¥1,680） |
| **C-full HBF 级** | **4-Hi / 128 GB / $45–308（$119，¥845）** | 同左 | 同左（4 die 约 400 GB/s，受主机接口限制） |

**2026 高位价口径 H**（TLC $0.227–0.344/GB）：

| 方案 | 30 GB/s | 60 GB/s | 117 GB/s |
|---|---|---|---|
| 0 基线 | $525–933（**$703，¥4,990**） | $1,021–1,821（$1,369，¥9,720） | $1,921–3,447（**$2,568，¥18,240**） |
| A1 1 Tb pSLC | $220–523（$315，¥2,240） | $437–1,039（$629，¥4,470） | $871–1,929（$1,180，¥8,380） |
| **A2 512 Gb pSLC** | **$118–413（$207，¥1,470）** | $233–818（$414，¥2,940） | $464–1,499（$777，¥5,520） |
| **B 定制 SLC** | **$130–571（$234，¥1,660）** | $199–1,134（$414，¥2,940） | $394–2,064（$823，¥5,840） |
| C-lite TSV | $155–659（$318，¥2,260） | $155–1,264（$611，¥4,340） | $300–2,473（$904，¥6,420） |
| **C-full HBF 级** | **$180–1,091（$427，¥3,030）** | 同左 | 同左 |

**交叉核对**（推算，低）：C-full 在 H 口径下基准 $427 / 128 GB ≈ $3.3/GB，落在 PM 文件按「HBM 价 ÷ 8–16」推出的 HBF $0.9–4.5/GB 区间内（PM-S27~S30）。

### 7.3 满速读功耗（W，乐观–悲观，括号内为基准）

| 方案 | 30 GB/s | 60 GB/s | 117 GB/s |
|---|---|---|---|
| 0 基线 | 12.6–21（16.5） | 25–42（33） | 49–82（64） |
| A1 / A2 pSLC | 9–16.5（12） | 18–33（24） | 35–64（47） |
| B 定制 SLC | 7.5–13.5（9.9） | 15–27（19.8） | 29–53（38.6） |
| C-lite TSV | 1.8–4.5（3.0） | 3.6–9（6.0） | 7–17.6（11.7） |
| C-full HBF 级 | 1.5–3.6（2.4） | 3–7.2（4.8） | 5.9–14（9.4） |

参照：Kioxia 5 TB / 64 GB/s 闪存模块原型（PCIe 6.0 x8，菊花链「beads」）功耗 <40 W，即 ≤0.625 nJ/B（NB-S33）。这与 A / B 类「标准 NAND 通道 + 主控」在 60 GB/s 档 20–33 W 的估计同量级。

### 7.4 未计入的一次性成本（NRE）

- **定制 NAND die（B、C）**：设计、掩膜、良率爬坡费用，公开数字**未找到**。CBA 路线下，CMOS 外围晶圆要新做一套掩膜，阵列晶圆可能沿用同代工艺。
- **定制主控 / base die**：N7 掩膜组约 $3.5M（CN-S38），设计 NRE **未找到**。
- **摊销敏感性**：每 $10M NRE 摊到 100 万台为 $10/台（¥71），摊到 1,000 万台为 $1/台。B 和 C 只有在千万台量级时，NRE 才能降到总成本的 10% 以下（推算，低）。A 只需要定制主控，没有新 NAND 流片。

### 7.5 读法

1. **单位带宽的 die 数**：A 比基线少约 55–60%，B 少约 75–80%，C 只要 4–8 颗。基线成本主要被 die 数锁死，A / B / C 的成本则主要取决于 NAND 价格口径与定制溢价。
2. **30 GB/s 档**：A2 与 B 成本相当（N 口径基准都约 ¥470–490），但 A2 不用新 die、没有 NRE。B 的真正优势是容量正好 128 GB、die 数少（4 颗），功耗略低。
3. **117 GB/s 档**：A 要 28–39 条、B 要 24–38 条 NAND 通道，没有现成主控（需 2–3 颗 16 通道主控，或定制 32 通道主控），功耗 39–47 W，超出笔记本插电档的合理预算。C-full 只要 4 颗 die、约 9 W。
4. **2026 高位价下**，各方案成本约乘 3–4 倍，**比较结论不变**，因为各方案的成本主体都是 NAND 硅。C 的 core die 还叠加了定制溢价和 TSV 工序系数，会放大涨价，所以涨价时 C 相对 A 的价差并不缩小：30 GB/s 档基准下，C-full ÷ A2 在 N 口径为 1.8 倍，在 H 口径为 2.1 倍（推算）。
5. **B 方案的前提**是 die 有双端口或 x16 I/O。如果直接用现成的 XL-FLASH 第 2 代（BiCS5 代际，接口速率**未找到**，推测 ≤2.0 GT/s），每 die 只有约 1.4–1.8 GB/s，通道数反而比 A 多一倍。

---

## 8. 推荐与不确定性

| 场景 | 推荐 | 理由 |
|---|---|---|
| 只做电池档 30 GB/s，2028–29 量产 | **A2 / A1**：现成 512 Gb 或 1 Tb TLC 当 pSLC，8–10 颗；8–10 通道 @4.8 GT/s 的定制主控；主机侧用 PCIe 6.0 x8，或 UCIe-S 上封装 | 无新 NAND 流片；A2 成本 ¥240–1,140（N）/ ¥840–2,930（H），A1 为 ¥370–1,320 / ¥1,560–3,720；风险最低。代价是 9–17 W，以及 512 Gb die 在 2028 年后的供货不确定 |
| 要覆盖 60–117 GB/s | **C-full**（HBF 级 core die 4-Hi、128 GB、UCIe-S x16 × 1–3 上封装，base die 承担 ECC / 调度 / 读计数） | die 数最少，功耗约为 A / B 的 1/4–1/5，成本与 A 同量级（N 口径 ¥320–2,190）；NRE 与供货依赖原厂 |
| 原厂不愿做 TSV | B（定制 SLC 16 plane、双端口 I/O） | 每 die 带宽翻倍、容量对准 128–256 GB，但 117 档功耗仍有 30–50 W |

**最大不确定项**：C 方案依赖 HBF 级 core die 的面积、tR 与端侧小批量供货意愿，三项都没有一手数据（SanDisk 2027 年才有数据中心样品，没有端侧路线图）。另外，C 的 0.05–0.15 nJ/B 只是模型值；它是 C 相对 A / B 的核心优势，必须先拿到实测验证。A 方案的不确定项是 2027 代 die 的 pSLC tR（本文推算 12–20 µs，无一手值）。

---

## 9. 冲突、口径问题与未找到

1. **XL-FLASH 每 die 吞吐**：POSTECH / ETH 论文（CN-S12）按 16 plane × 4 KiB ÷ 4 µs 算出 16 die 262 GB/s。但 Kioxia 发言人说第 1 代同时激活 plane 只有 4 个、第 2 代 8 个（CN-S2），按此第 1 代每 die 只有约 4.1 GB/s。论文值偏高约 4 倍，本文按 Kioxia 口径计。
2. **XL-FLASH tR**：ISSCC 2020 论文标题为 4 µs；官网写「<5 µs」；StorageNewsletter 2019 写「<4 µs」。本文取 4 µs。
3. **PC Watch 图注**：图注写 XL-FLASH「16 Gbit 的子阵列 16 个」，16 × 16 = 256 Gb，与 128 Gb die 不符（可能是物理阵列口径或笔误）。本文不使用该数。
4. **HBF plane 数**：论文分别假设 25 plane（CN-S12）和 64 plane（CN-S13），SanDisk 未公布；位数（SLC / pSLC）也未公布。
5. **Micron G9 die 面积**是 AnandTech 按「+44% 密度」反推的，不是拆解实测。SK hynix V9 的 43.54 mm² 是 TechInsights 实测，但测的是 die seal 面积。
6. **BiCS8 密度**：由 BiCS10 的 29 Gb/mm² ÷ 1.59 反推，没有直接来源（TechInsights 报告在付费墙后）。
7. **制造成本**：用公司整体毛利率反推，含 SSD 业务与库存效应，只是近似；TrendForce / Yole / TechInsights 的晶圆成本模型都在付费墙后。
8. **主控价格**：一手数据**未找到**，只有约 2018 年的论坛帖（$12–17）。本文用 die 面积模型推算，置信度低。
9. **NAND 封测每 die 成本、HBM / TSV 分项成本、定制 NAND die NRE**：**未找到**，均按假设计入并单列。
10. **pSLC tR、XL-FLASH 第 2 代 tR 与接口速率、Z-NAND plane 数与 die 面积**：**未找到**。
11. **OCP HBF base die 规范原文**被 Cloudflare 拦截，规范内容取自鉅亨网的二手解读（CN-S14），置信度中。
12. **PCIe 6.0 PHY 的 pJ/bit**：**未找到**，改用主控整体能效。
13. **未能访问的来源**：AnandTech 原站（已改用 Internet Archive 存档）；TechInsights XL-FLASH 拆解报告全文（付费）；OCP HBF 规范 PDF（被拦截）。

---

## 10. 来源列表

| 编号 | 来源 | 日期 | URL | 用于 |
|---|---|---|---|---|
| CN-S1 | Kioxia：XL-FLASH 产品页 | 访问于 2026-10-14 | https://kioxia.com/en-jp/business/memory/xlflash.html | 128 Gb SLC / 256 Gb MLC、16 plane、4 KB 页、<5 µs、第 2 代量产 |
| CN-S2 | Blocks & Files：Kioxia updates XL-Flash storage-class memory with MLC tier | 2022-08-06 | https://www.blocksandfiles.com/flash/2022/08/06/kioxia-updates-xl-flash-storage-class-memory-with-mlc-tier/1593905 | 第 2 代 256 Gb MLC；同时激活 plane 4→8，总数 16；BiCS5 |
| CN-S3 | PC Watch：キオクシアとWD、超高速3D NAND「XL-FLASH」の概要を公表（ISSCC 2020 讲演 13.5） | 2020-03-04 | https://pc.watch.impress.co.jp/docs/news/event/1238655.html | 128 Gb、96L、tR 4 µs、tPROG 75 µs、16 plane、96.34 mm²；对照 512 Gb TLC 86.13 mm²、2 plane、58 µs；字线延迟降到 1/20 |
| CN-S4 | TechInsights：KIOXIA's new XL-FLASH for ultra-low latency NAND application | 2021-03 | https://www.techinsights.com/blog/memory/kioxias-new-xl-flash-ultra-low-latency-nand-application | 96L BiCS4、128 Gb、SLC、16 plane、4 KB 页 |
| CN-S5 | T. Kouchi et al., "A 128Gb 1b/Cell 96-Word-Line-Layer 3D Flash Memory to Improve Random Read Latency with tPROG=75µs and tR=4µs", ISSCC 2020（13.5）；JSSC 56(1):225–234, 2021 | 2020-02 | 引文见 https://arxiv.org/abs/2608.13868 参考文献 [10] | XL-FLASH tR 4 µs、tPROG 75 µs |
| CN-S6 | AnandTech（B. Tallis）：The Samsung 983 ZET (Z-NAND) SSD Review（存档） | 2019-02-19 | https://www.anandtech.com/show/13951/the-samsung-983-zet-znand-ssd-review （存档：https://web.archive.org/web/2023/https://www.anandtech.com/print/13951/the-samsung-983-zet-znand-ssd-review ） | Z-NAND 48L 64 Gb、tR 3 µs、tPROG 100 µs、页 2/4 KB；983 ZET $2.08–2.16/GB；比 Optane 便宜约 35% |
| CN-S7 | PC Watch（福田昭）：Samsungの高速SSD技術「Z-SSD」と専用フラッシュ技術「Z-NAND」の正体 | 2018-03-05 | https://pc.watch.impress.co.jp/docs/column/semicon/1109765.html | 64 Gb 对 256 Gb、45→3 µs、660→100 µs；页 4/2 KB；tDMA 双通道；第 2 代降成本 |
| CN-S8 | W. Cheong et al., "A Flash Memory Controller for 15µs Ultra-Low-Latency SSD Using High-Speed 3D NAND Flash with 3µs Read Time", ISSCC 2018 | 2018-02 | https://ieeexplore.ieee.org/document/8310322 | tR 3 µs、100 µs 编程、x8/x16 DDR I/O（经检索摘录） |
| CN-S9 | DigiTimes / Tom's Hardware（经 Yahoo 转载）：Samsung revives Z-NAND（FMS 2025） | 2025-08-08 | https://www.digitimes.com/news/a20250808VL210.html ；https://tech.yahoo.com/computing/articles/samsungs-revived-z-nand-targets-170226448.html | 最高 15 倍性能、−80% 功耗、GIDS |
| CN-S10 | Kioxia：Kioxia Announces KIOXIA GP1 Series Super High IOPS SSDs for AI Applications | 2026-08-04 | https://www.kioxia.com/en-jp/business/news/2026/20260804-1.html | PCIe 6.0、XL-FLASH 第 2 代、512 B 1000 万 IOPS、50 DWPD、2026 年底送样 |
| CN-S11 | FL6 零售标价：Saitech（KFL61HUL1T60）；e-nitiative（KFL6XHUL800G） | 访问于 2026-10-14（页面无日期） | https://esaitech.com/products/kioxia-fl6-kfl61hul1t60-1-6tb-pcie-4-0-x4-nvme-ssd ；https://upfront.e-nitiative.eu/product/details/kioxia/storage-drives-and-media/kfl6xhul800g/X2132234 | XL-FLASH SSD 零售价 |
| CN-S12 | Son, Park, Cho, Ham, Mutlu, Lee, Kim, Park：Exploring High-Bandwidth Flash for Modern LLM Inference（IEEE CAL；= NB-S24） | 2026-08-14 | https://arxiv.org/abs/2608.13868 | HBF 25 plane/die、1 µs；Z-NAND 16 die 87.4 GB/s、XL-Flash 16 die 262 GB/s；更细 plane 切分需靠晶圆键合消化面积开销 |
| CN-S13 | SPLASH: Co-Designing Sparse Attention with High-Bandwidth Flash（arXiv） | 2026-09 | https://arxiv.org/abs/2609.23816 | 16 die × 64 plane、4 KiB 页建模；闪存读 64 pJ/B（引 Kioxia ISSCC 2025）；base die 职责；SLC 10⁵ P/E |
| CN-S14 | 鉅亨网（芯联汇）：解读 OCP *HBF High-Level Base Die Specification* | 2026-09-19 | https://hao.cnyes.com/post/268730 | base die 模块与职责；16 通道 × 64 bit UCIe 3.0；3,072 GB/s；x64 模块 256 GB/s；2 mm |
| CN-S15 | "HBF Sucks? A Full-Stack Characterization of High-Bandwidth Flash for KV-Centric LLM Serving"（arXiv） | 2026-08 | https://arxiv.org/abs/2608.11668 | base die 做 ECC / 坏块 / 通道内映射；AXI over UCIe（经检索摘要） |
| CN-S16 | StorageReview：Sandisk tapes out its first HBF memory die | 2026-08-18 | https://www.storagereview.com/news/sandisk-tapes-out-its-first-hbf-memory-die-targets-2027-for-inference-product-samples | 首颗 HBF die 流片、2027 样品、16 × 256 Gb |
| CN-S17 | The Register：HBF 报道 | 2026-07-30 | https://assets.theregister.com/2026/07/30/202619/ | 256 Gb/die、512 GB/16-Hi |
| CN-S18 | PC Watch（福田昭）：ISSCC 2021 3D NAND 综述 | 2021-04-02 | https://pc.watch.impress.co.jp/docs/column/semicon/1315644.html | 2→4 plane +15%、CuA 后 <1%；1 Tb 74–98 mm²、512 Gb 47–60 mm²；SK hynix 中置行解码 |
| CN-S19 | AnandTech（B. Tallis）：2021 NAND Flash Updates from ISSCC（= NB-S12） | 2021-02-19 | https://www.anandtech.com/show/16491 （存档：https://web.archive.org/web/2023/https://www.anandtech.com/print/16491/flash-memory-at-isscc-2021 ） | ISSCC TLC / QLC 参数表；CuA >90%；4 plane 标配；异步 plane 读需独立电荷泵 |
| CN-S20 | IEEE Solid-State Circuits Magazine, Fall 2020, p.59（3D NAND 综述） | 2020 | https://nxtbook.com/nxtbooks/ieee/mssc_fall2020/index.php?startid=59 | 阵列下方可放额外 SA；层数升高后需增大 die 容量才能藏住外围（只读到检索摘录） |
| CN-S21 | USPTO 专利：Page buffer circuits in three-dimensional memory devices（US12277993）；Page buffer circuits of three-dimensional memory device（US11935619）；Memory peripheral circuit having three-dimensional transistors（US12063784 / US12274066）；Three-dimensional NAND memory device（US12641781）；Three dimensional memory control circuitry（US9202536） | — | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12277993 ；…/11935619 ；…/12063784 ；…/12641781 ；…/9202536 | 页缓冲 20–40%、>50%；外围 20–30%、>50%；CuA 面积受限 |
| CN-S22 | TechInsights：SK Hynix H25GTD0 321-Layer (V9) 1 Tb TLC 3D NAND Process Flow Analysis | 2026-07-13 | https://www.techinsights.com/blog/sk-hynix-h25gtd0-321-layer-v9-1-tb-tlc-3d-nand-process-flow-analysis | 23.52 Gb/mm²、43.54 mm²、PUC、三 deck |
| CN-S23 | AnandTech：Micron Ships Denser & Faster 276 Layer TLC NAND（存档） | 2024-07-31 | https://www.anandtech.com/show/21492 （存档：https://web.archive.org/web/2024/https://www.anandtech.com/show/21492/micron-ships-denser-9th-generation-nand-276layers-and-2650-client-ssds ） | G9 约 48.9 mm²、约 21 Gb/mm²、6 plane；232L 70.1 mm²；176L 512 Gb 49.8 mm² |
| CN-S24 | AnandTech：SK Hynix Starts Production of 238-Layer 3D NAND | 2023-06 | https://www.anandtech.com/show/18902 | 512 Gb 35.58 mm²、约 14.39 Gb/mm² |
| CN-S25 | Kioxia：BiCS10 出样新闻稿；StorageReview / TrendForce 转述 | 2026-07-03 | https://www.kioxia.com/en-jp/about/news/2026/20260703-1.html ；https://www.storagereview.com/news/sandisk-and-kioxia-begin-sampling-332-layer-bics10-3d-nand | 比 BiCS8 密度 +59%、4.8 Gb/s、读能效 +30% |
| CN-S26 | 3DNews：ISSCC 2026 Kioxia / SanDisk 2 Tb QLC 预告（转引 ComputerBase） | 2025-11-27 | https://3dnews.ru/1133033/pochti-5-gbayt-na-kvadratniy-millimetr-kioxia-i-sandisk-gotovyat-fleshpamyat-rekordnoy-plotnosti | 6 plane、37.6 Gb/mm²、约 55 mm²；BiCS10 TLC 29.1 Gb/mm² |
| CN-S27 | （同 NB-S19）Samsung V10 ISSCC 2025 | 2024-12-04 | https://www.blocksandfiles.com/data-management/2024/12/04/samsung-developing-400-plus-layer-3d-nand/1603230 | 28 Gb/mm²、5.6 Gb/s |
| CN-S28 | TechInsights 2022 年 3D NAND 对比（经检索摘要转述；具体页面未逐字核对） | 2022 | https://semiconductor-digest.com/?p=14911 | YMTC 232L 1 Tb 68.15 mm²、15.03 Gb/mm² |
| CN-S29 | Device-Level Optimization Techniques for Solid-State Drives: A Survey（arXiv） | 2025-07 | https://arxiv.org/abs/2507.10573 | SLC 20–25 µs、MLC 40–110、TLC 66–170、QLC 120–200 µs |
| CN-S30 | USPTO 专利：NAND array architecture for multiple simultaneous program and read（US9263137）；Methods and apparatus for reading NAND flash memory（US11232835） | — | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9263137 ；https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11232835 | SLC 约 20 µs、MLC 约 60、TLC 约 150 µs；单次放电 25–30 µs × 3 |
| CN-S31 | Swissbit：4 reasons to use industrial 3D TLC NAND flash as pseudo-SLC | 2023-10-01 | https://www.swissbit.com/en/news/blog/4-reasons-to-use-industrial-3d-tlc-nand-flash-as-pseudo-slc | pSLC 读速约 TLC 的 2 倍、写约 6 倍 |
| CN-S32 | Dissecting and Re-architecting 3D NAND Flash PIM Arrays（arXiv） | 2025-11 | https://arxiv.org/abs/2511.12860 | 常规 plane 20–50 µs；小 plane 约 2 µs（模型） |
| CN-S33 | Blocks & Files：Sandisk FQ4 FY2026 results | 2026-08-06 | https://www.blocksandfiles.com/flash/2026/08/06/sandisk-maketh-mucha-moolah/5284021 | 毛利率 84.6% / 78.4% / 51.1%；长协约 80% |
| CN-S34 | SanDisk IR：Fiscal Fourth Quarter 2025 Financial Results | 2025-08-14 | https://investor.sandisk.com/news-releases/news-release-details/sandisk-reports-fiscal-fourth-quarter-2025-financial-results | FQ4'25 26.4%、FY25 30.3%、FY24 15.8% |
| CN-S35 | TrendForce News：Kioxia 1QFY26 Gross Margin Hits 80% | 2026-07-31 | https://www.trendforce.com/news/2026/07/31/news-kioxia-1qfy26-gross-margin-hits-80-reaffirms-50-lta-target-for-2028/ | 80% / 82%、ASP +70% |
| CN-S36 | Yole：NAND Technology, Process and Cost Comparison 2026（报告页） | 2026 | https://www.yolegroup.com/product/report/nand-comparison-2026/ | 价格 >$0.24/GB、+280%（检索摘要） |
| CN-S37 | TechInsights：Maximizing NAND Capacity per Wafer in 3D NAND Production | 2024 | https://www.techinsights.com/ja/node/56666 | 每片 300 mm 晶圆最高 128 TB（检索摘要） |
| CN-S38 | Silicon Analysts：Wafer Pricing by Process Node (2026)；NRE & Mask Set Costs | 2026-09 | https://siliconanalysts.com/data/wafer-pricing | 28 nm $3,000、N16/12 $5,500、N7 $9,500、N5 约 $18,500–20,000；掩膜组价格 |
| CN-S39 | 3D InCites：IMAPS Device Packaging Conference（SK hynix 主题演讲） | 2012-03 | https://www.3dincites.com/2012/03/imaps-device-packaging-conference-through-3d-glasses-day-1/ | TSV 堆叠 1.3 倍、TSV +25% 制造成本 |
| CN-S40 | AnandTech：Silicon Motion Readies PCIe Gen5 SSD Platform with 3.5W；StorageNewsletter：FMS 2024 SM2508 | 2023 / 2024-08-07 | https://www.anandtech.com/show/20005 ；https://www.storagenewsletter.com/2024/08/07/fms-2024-silicon-motion-launches-best-performance-watt-sm2508-pcie-gen5-ssd-controller/ | SM2508 N6、8 通道 3600 MT/s、约 3–3.5 W、整盘 <7 W |
| CN-S41 | AnandTech 读者评论：主控「套片」价格 | 约 2018 | https://at-web1.www.anandtech.com/comments/12718/samsung-posts-lowered-msrps-for-970-pro-and-970-evo-ssds/600098 | $12–17 / 1,000 片（低） |
| CN-S42 | JEDEC：Enhanced NAND Flash Interface Standard（JESD230G） | 2024-11-18 | https://www.jedec.org/node/9465 | 最高 4800 MT/s、SCA |
| CN-S43 | D. Das Sharma 等（Intel / AMD）：On-Package Memory with UCIe（HOTI 2025 幻灯片） | 2025-08-21 | https://hoti.org/assets/slides/2025_08_21_day2_SessionD_UCIe_Mem.pdf | UCIe-2D x16、25 mm、0.5/0.6 pJ/b；2.5D x64、0.25/0.3 pJ/b；LPDDR5 2.8 pJ/b、HBM3 0.9 pJ/b；PC 封装内存示例 |
| CN-S44 | Kioxia：CBA（CMOS directly Bonded to Array）技术介绍 | 2023–2024 | https://kioxia.com/en-jp/rd/technology/topics/topics-64.html | CMOS 与阵列分片制造后键合 |
| 引用 | 同目录 `pc-cost-nand-bandwidth.md`（NB-S1~S36）、`pc-cost-memory-prices.md`（PM-S1~S33） | 2026-10-14 | 仓库内 | 每 die 吞吐、SSD nJ/B、PCIe 6.0、HBF、NAND / HBM / HBF 价格 |

> 计算脚本（含全部参数与公式）只放在会话临时目录，未写入仓库。第 7 节所有数字都可以按第 1 节公式与 7.1 节参数复算。

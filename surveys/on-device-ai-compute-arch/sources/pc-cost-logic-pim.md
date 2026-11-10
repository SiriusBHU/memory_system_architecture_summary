# PC 端侧 AI 子系统 BOM：逻辑芯片（NPU + 片上 SRAM）与 3D-PIM 成本数据

> 用途：为 PC 端侧 AI 架构做增量成本核算。被核算的两块硬件：
> (1) 集成进 PC SoC 的 NPU：200 TOPS @W4A8（≈100 TOPS @INT8），片上 SRAM 约 64 MB；
> (2) 4 GB 3D-PIM：DRAM 以混合键合等方式堆在逻辑 die 上，内部带宽约 1 TB/s，能耗 0.5–1 pJ/bit，逻辑 die 上做 GEMV 与注意力，跑 4B 模型 decode。
> 要回答的问题：这套 AI 子系统的增量成本能否压到几百元人民币。
>
> - 采集日期：**2026-10-14**
> - 汇率：**1 USD = 7.1 CNY**（全文统一）
> - 来源编号：LP-S1…LP-S46，见第 9 节（含 URL）
> - 姊妹文件：同目录 [`pc-cost-memory-prices.md`](pc-cost-memory-prices.md)（PM-S#，存储器价格，DRAM 现货 / 合约 / 渠道价更全）
> - 本地参考：[`insight/N+2/lpddr-pim-architecture/lpddr-pim-architecture-CN.md`](../../../insight/N+2/lpddr-pim-architecture/lpddr-pim-architecture-CN.md)、[`advanced/A16g-DRAM-PIM异构协同管理.md`](../../../advanced/A16g-DRAM-PIM异构协同管理.md)、[`insight/N+3/hbm4-advanced-packaging/hbm4-advanced-packaging-CN.md`](../../../insight/N+3/hbm4-advanced-packaging/hbm4-advanced-packaging-CN.md)

**数据性质标注**：【实测】论文 / 拆解测得的硅片数据｜【规格】厂商官方标称｜【报道】媒体 / 分析机构转述（非官方）｜【推算】本文按公式推出（公式写在旁边）。

**置信度**：**高** = 同行评审论文、厂商官方文档、一手机构价格页，日期明确；**中** = 权威媒体或分析机构转述一手数据；**低** = 论坛、聚合站、单一来源传闻，或本文推算中含强假设的部分。

**口径提醒**：TOPS 一律注明 INT8 还是 W4A8 / INT4；「64 MB」按 64 MiB = 536.9 Mbit 计；晶圆价均为 300 mm、台积电不公开报价，全部是报道 / 估算值。

---

## 0. 结论速览

| 项目 | 乐观 | 基准 | 悲观 | 说明 |
|---|---|---|---|---|
| NPU 计算阵列面积（100 TOPS INT8） | 14 mm² | 22 mm² | 44 mm² | 按 7 / 4.5 / 2.3 TOPS/mm²（INT8）推算，见 §2.2 |
| 64 MiB SRAM 面积 | 21 mm² | 24 mm² | 31 mm² | N3E 宏密度 31.8 Mb/mm² × 有效率 0.80 / 0.70 / 0.55，见 §3.2 |
| NPU + SRAM 合计面积 | 35 mm² | 46 mm² | 74 mm² | N2 上约 30 / 40 / 63 mm² |
| NPU + SRAM 硅成本（边际，集成进 SoC） | $15（¥104） | $25（¥180） | $53（¥373） | N3 晶圆 $20k / $23k / $27k，见 §7.1 |
| 4 GB 3D-PIM（DRAM 按正常周期价） | $19（¥135） | $49（¥348） | $119（¥843） | 见 §7.2 |
| 4 GB 3D-PIM（DRAM 按 2026 超级周期价 ≈$15/GB） | $75（¥533） | $159（¥1,128） | $344（¥2,443） | 见 §7.2 |
| **AI 子系统硅 + 封装增量（正常周期）** | **$34（¥240）** | **$74（¥528）** | **$171（¥1,216）** | 不含 NRE、不含芯片厂毛利、不含 LPDDR 抵扣 |
| **AI 子系统硅 + 封装增量（2026 超级周期）** | **$90（¥637）** | **$184（¥1,308）** | **$397（¥2,816）** | 同上 |

一句话：**逻辑部分（NPU + 64 MB SRAM）稳定在 ¥100–400；3D-PIM 的成本由 DRAM 位价格主导，DRAM 价格回到 2024 年水平时整套能做到几百元，按 2026 年价格则基准就过千元。**

---

## 1. 晶圆价格与每 mm² 成本

### 1.1 台积电先进节点晶圆价（300 mm，USD）

| 节点 | 价格 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|
| N2 | 约 $30,000（¥21.3 万；较 N3 高 10–20%，而非传闻的 50%） | 2025-10-08 | 【报道】Investor.com 引供应链 | 中 | LP-S1 |
| N2 | 「可能超过 $30,000」（¥21.3 万），约为 4/5nm 的 2 倍 | 2024-10-04 | 【报道】工商时报 | 中 | LP-S2 |
| N3 / N3E / N3P | $25,000–27,000（¥17.8–19.2 万） | 2025-10-08 | 【报道】Investor.com 引供应链 | 中 | LP-S1 |
| N3 | 约 $20,000（¥14.2 万；EE Times 基线） | 2025-10-08 | 【报道】 | 中 | LP-S1 |
| N3 | ≥$20,000（¥14.2 万），2025 年 ASP 预计 +4% | 2024-07 | 【报道】摩根士丹利 | 中 | LP-S3 |
| N3 | $18,000（¥12.8 万） | 2024 | 【报道】Creative Strategies（Ben Bajarin） | 中 | LP-S7 |
| N3 / N3E | 均价 $20,000，区间 $18,000–27,000（¥12.8–19.2 万） | 2026-08 刷新 | 【报道】聚合站，综合 Tom's Hardware / TrendForce | 低–中 | LP-S6 |
| N4（4nm 级） | 约 $18,000 → 2025 年约 $20,000（¥12.8 → 14.2 万，+~10%） | 2024-07 | 【报道】摩根士丹利 | 中 | LP-S3 |
| N5 / N4 | 均价 $18,500–20,000，区间 $16,000–21,300（¥11.4–15.1 万） | 2026-09 | 【报道】聚合站 | 低–中 | LP-S6 |
| N7 | $9,500（¥6.7 万；$8,100–10,900） | 2024 | 【报道】聚合站引 CSET / SemiWiki | 低–中 | LP-S6 |
| N16 / N12 | $5,500（¥3.9 万；$5,000–6,000） | 2025 | 【报道】聚合站引 IBS / 摩根士丹利 / DigiTimes | 低–中 | LP-S6 |
| GF 12LP | $4,200（¥3.0 万；$3,500–4,900） | 2026 | 【报道】聚合站 | 低 | LP-S6 |
| TSMC 28nm | $3,000（¥2.1 万；$2,550–3,450） | 2024 | 【报道】聚合站 | 低–中 | LP-S6 |
| SMIC 28nm | $1,500–2,500（¥1.1–1.8 万；降价前后） | 2025 | 【报道】 | 低 | LP-S6 |

**涨价轨迹**（决定 2028–29 量产时的价格）：

| 事件 | 幅度 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|
| 2026 年先进节点涨价，1 月 1 日生效 | +3–10%（个位数），并通知涨到 2029 年 | 2025-12-29 | 【报道】经济日报 | 中 | LP-S4 |
| 2026 下半年 3nm 再涨 | 最高 +15% | 2026-06-12 | 【报道】供应链 | 中 | LP-S5 |
| 2027 年基础价上调 | +5–10%（先进 + 成熟节点） | 2026-07 | 【报道】日经 | 中 | LP-S8 |
| N2 量产 | 2025 Q4 已量产 | 2026（官网） | 【规格】 | 高 | LP-S9 |
| N2P 相对 N3E | 逻辑密度 1.2×，芯片密度 1.15×（50% 逻辑 + 30% SRAM + 20% 模拟的混合口径） | 官网 | 【规格】 | 高 | LP-S9 |

**本文取值**：N3 基准 $23,000（$20k 基线 + 2026 年两轮涨价），乐观 $20,000，悲观 $27,000；N2 取 $30,000；N4 取 $18,000–20,000。

### 1.2 每 mm² 成本的推算方法

公式（与 LP-S6 指南、LP-S39 TCPMT 论文同一套框架）：

```
DPW(A)   = π·(d/2)²/A − π·d/√(2A)            # 毛 die 数，d = 300 mm，A 单位 mm²
Y(A)     = [(1 − e^(−A·D0)) / (A·D0)]²         # Murphy 良率，A 换算成 cm²，D0 单位 /cm²
C_die    = W / (DPW · Y)                       # 每颗良品 die 成本，W 为晶圆价
C_mm2    = C_die / A                           # 平均每良品 mm² 成本
ΔC(ΔA)   = C_die(A0+ΔA) − C_die(A0)            # 集成进已有 SoC（面积 A0）时的边际成本
```

良率假设：LP-S6 给出台积电 3nm D0 = 0.14 /cm²（Murphy），据此 100 mm² 约 85%、200 mm² 约 76%【报道，低–中】。2028–29 年 N3 已非常成熟，本文取 N3 D0 = 0.10（乐观 0.08）、N2 D0 = 0.12、12/16nm 0.06–0.07、7nm 0.08、28nm 0.05【推算假设，置信度低】。未计入边缘排除、测试与 SRAM 冗余修复（SRAM 区域实际良率更高，所以下表对 SRAM 偏保守）。

**每良品 mm² 成本（推算）**：

| 节点 / 晶圆价 / D0 | 50 mm² | 100 mm² | 150 mm² | 200 mm² | 250 mm² |
|---|---|---|---|---|---|
| （单位：USD / 良品 mm²，括号内 CNY） | | | | | |
| N4，$18k，0.08 | $0.28（¥2.0） | $0.30（¥2.2） | $0.32（¥2.3） | $0.34（¥2.4） | $0.36（¥2.6） |
| N4，$20k，0.08 | $0.32（¥2.2） | $0.34（¥2.4） | $0.36（¥2.6） | $0.38（¥2.7） | $0.41（¥2.9） |
| N3，$20k，0.10 | $0.32（¥2.3） | $0.35（¥2.5） | $0.37（¥2.6） | $0.40（¥2.8） | $0.43（¥3.0） |
| N3，$23k，0.10 | $0.37（¥2.6） | $0.40（¥2.8） | $0.43（¥3.0） | $0.46（¥3.2） | $0.49（¥3.5） |
| N3，$27k，0.10 | $0.43（¥3.1） | $0.47（¥3.3） | $0.50（¥3.6） | $0.54（¥3.8） | $0.57（¥4.1） |
| N2，$30k，0.12 | $0.48（¥3.4） | $0.53（¥3.7） | $0.57（¥4.1） | $0.62（¥4.4） | $0.67（¥4.7） |

对照：LP-S6 用 $20k、D0 0.14 推出 3nm 100 mm² die 约 $42（$0.42/mm²），与上表 $0.35–0.40 同量级（差在 D0）。

---

## 2. 现有端侧 / PC NPU 的面积与算力

### 2.1 数据表

| NPU | 工艺 | 标称算力 | 口径 | NPU 面积 | TOPS/mm² | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|---|---|---|---|
| 三星 8K-MAC NPU（Exynos 2200） | 4nm | — | INT8 / FP16 | — | **3.45 TOPS/mm²（INT8）**；1.72 TFLOPS/mm²（FP16）；11.59 TOPS/W | ISSCC 2022 / JSSC 2022-10 | 【实测】同行评审 | **高** | LP-S10 |
| 三星 6K-MAC NPU | 5nm | — | — | 未找到（摘要未给面积） | 未找到 | ISSCC 2021 | — | — | LP-S10 |
| Apple ANE（M4，16 核） | N3E | 38 TOPS | 未注明，业内普遍按 INT8 | **未找到**（TechInsights M4 版图报告付费） | 未找到 | 2024-05-07 | 【规格】 | 高（算力） | LP-S11 |
| Apple ANE（A17 Pro） | N3B | 35 TOPS | 推测 INT8 | 约 5 mm²（论坛帖，无出处） | 约 7（推算） | 2023-12-23 | 【报道】论坛 | **低** | LP-S12 |
| Apple ANE（A18 Pro） | N3E | 35 TOPS | — | 未找到；TechInsights 称 NPU 核比 A17 Pro 小约 10%，共享逻辑与缓存大约 15% | 未找到 | 2024 | 【报道】 | 中（相对值） | LP-S13 |
| Apple ANE（M1 vs A14） | N5 | — | — | 未找到绝对值；TechInsights 给 M1/A14 NPU 面积比 0.9 | — | 2020 末 | 【实测】相对值 | 中 | LP-S13 |
| Qualcomm Hexagon（X Elite） | N4 | 45 TOPS | 官方称 INT8；Chips and Cheese 认为 16K MAC/cycle，「可能是 4-bit 权重」 | **未找到**（die 169.6 mm² 的标注图未标出 NPU） | 未找到 | 2023-10 / 2024 | 【规格】 | 高（算力）/ 口径存疑 | LP-S14 |
| Qualcomm Hexagon（X2 Elite） | 3nm 级（未核实） | 80 TOPS | INT8 | 未找到 | 未找到 | 2025-11 | 【规格】 | 高（算力） | LP-S14 |
| AMD XDNA 2（Strix Point） | N4P | 50 TOPS（PRO 款 55） | INT8（另有 Block FP16） | **未找到**；die 232.5 mm²，32 个 AIE tile，标注图只说「明显大于 Phoenix」 | 未找到 | 2024-06-02 | 【规格】 | 高（算力） | LP-S15 |
| Intel NPU 4（Lunar Lake，6 个 NCE） | N3B | 48 TOPS | INT8 | 约 18 mm²（推算：Nemez 标注称 NPU 与 4 核 Lion Cove 簇同尺寸；Lion Cove 含 L2 每核 4.53 mm²，×4 ≈ 18 mm²；若簇含 12 MB L3 则约 25 mm²） | 约 1.9–2.7（推算） | 2024-06-04 / 2024-10 | 【规格】算力；面积【推算】 | 算力高 / 面积**低** | LP-S16 |

**说明**：
- 免费公开渠道里，**唯一带面积的同行评审数据是三星 4nm NPU 的 3.45 TOPS/mm²（INT8）**。Apple / 高通 / AMD 的 NPU 面积都锁在 TechInsights、Yole 付费版图报告里（LP-S13 等页面只给目录或相对值）。
- 高通 45 TOPS 的口径有分歧：官方称 INT8，Chips and Cheese 按 16K MAC/cycle 推测是 4-bit 权重（LP-S14）。若是 W4，它的 INT8 等效约 22.5 TOPS。
- 上表 NPU 面积都包含 NPU 自带的 scratchpad / 本地 SRAM 与控制逻辑；本方案的 64 MB 大 SRAM 另算（§3）。

### 2.2 推算：200 TOPS @W4A8（≈100 TOPS INT8）NPU 计算部分的面积

按 INT8 TOPS 定尺寸，假设 W4A8 模式靠 4-bit 权重 MAC 复用拿到 2 倍（三星 4nm NPU 即同时支持 INT4/8/16、FP16，LP-S10）。

```
A_NPU = 100 TOPS(INT8) / (TOPS/mm²)
```

| 情景 | TOPS/mm²（INT8） | 依据 | N3 面积 | N2 面积（逻辑 ÷1.15） | 置信度 |
|---|---|---|---|---|---|
| 乐观 | 7.0 | A17 Pro 论坛值（约 35 TOPS / 5 mm²）；也接近三星 4nm 3.45 按 N4→N3/N2 密度提升 1.3–1.6× 外推再加 LLM 专用阵列的上沿 | 14.3 mm² | 12.4 mm² | 低 |
| 基准 | 4.5 | 三星 4nm 实测 3.45 × N4→N3 约 1.3× | 22.2 mm² | 19.3 mm² | 中–低 |
| 悲观 | 2.3 | Intel NPU 4 推算区间 1.9–2.7 的中值（含较多控制 / 向量 / 本地 SRAM） | 43.5 mm² | 37.8 mm² | 低 |

---

## 3. SRAM 密度与 64 MB SRAM

### 3.1 数据表

| 项目 | 数值 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|
| TSMC N5 HD bitcell | 0.021 µm² | — | 【实测】 | 高 | LP-S18 |
| TSMC N3B HD bitcell | 0.0199 µm²（比 N5 缩 5%） | IEDM 2022 | 【实测】 | 高 | LP-S18 |
| TSMC N3E HD bitcell | 0.021 µm²（与 N5 相同，SRAM 不缩） | 2022-12 | 【实测】 | 高 | LP-S18 |
| N3E 宏密度 | 约 31.8 Mib/mm²（WikiChip 按 ISO 辅助电路开销估） | 2022-12 | 【推算】第三方 | 中 | LP-S18 |
| N3B 宏密度 | 33.55 Mb/mm²（TSMC 表） | 2022-12 | 【规格】 | 中 | LP-S18 |
| TSMC N2 SRAM 宏密度 | **38.1 Mb/mm²**，较上一节点 1.1×（DTCO、BL 负载 2×） | ISSCC 2025-02 | 【实测】同行评审 | 高 | LP-S17 |
| N2 HD bitcell | 0.0175 µm²（IEDM 2024 预告报道） vs 0.021 µm²（IEEE Spectrum 对 ISSCC 2025 的报道）——**来源冲突** | 2024-12 / 2025-02 | 【报道】 | 中 | LP-S17 |
| AMD 3D V-Cache SRAM die（N7） | 64 MB 装在约 36 mm²（AnandTech / WikiChip；AMD 幻灯片另说 41 mm²）→ 实际密度约 13–15 Mb/mm² | 2021-06 | 【实测】 | 中–高 | LP-S19 |
| N7 SRAM 宏密度 | 约 24.7 Mib/mm²（WikiChip 估） | — | 【推算】第三方 | 中 | LP-S19 |

**「有效率」怎么来**：V-Cache 是几乎只有 SRAM 的 die，实际 13–15 Mb/mm² ÷ N7 宏密度 24.7 ≈ 0.53–0.60。大容量片上缓冲还要加 ECC（SECDED 约 +12.5% 位）、冗余、bank 间互连与 NoC 端口，所以「宏密度 × 0.55–0.80」是合理区间【推算，中–低】。

### 3.2 推算：64 MiB（536.9 Mbit）SRAM 面积

```
A_SRAM = 536.9 Mbit / (宏密度 × 有效率)
```

| 情景 | 节点 | 宏密度 | 有效率 | 有效密度 | 面积 | 置信度 |
|---|---|---|---|---|---|---|
| 乐观 | N3E | 31.8 | 0.80 | 25.4 Mb/mm² | 21.1 mm² | 中 |
| 基准 | N3E | 31.8 | 0.70 | 22.3 Mb/mm² | 24.1 mm² | 中 |
| 悲观 | N3E | 31.8 | 0.55 | 17.5 Mb/mm² | 30.7 mm² | 中 |
| 参考 | N2 | 38.1 | 0.80 / 0.70 / 0.55 | 30.5 / 26.7 / 21.0 | 17.6 / 20.1 / 25.6 mm² | 中 |

结论：64 MB SRAM 在 N3 上约 21–31 mm²，比 NPU 计算阵列本身还大或相当；SRAM 不随 N3E 缩小，所以这块面积很难靠换节点省下来。

---

## 4. 3D DRAM-on-logic / 3D-PIM 实例与参数

### 4.1 学术 / 测试芯片

| 实例 | 结构 | 关键参数 | 工艺 | 状态 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|---|---|---|
| 西安紫光国芯 SeDRAM 一代（IEDM 2020） | DRAM 晶圆与逻辑晶圆 Cu-Cu 混合键合（WoW） | **34 GB/s/Gb，0.88 pJ/bit**（逻辑到存储阵列接口）；LPDDR4/4X 阵列；平台可支持最高 48 Gbit、TB/s 级带宽 | 异构工艺（DRAM + 逻辑） | 2020 年称基于该技术的数据分析芯片已量产 | 2020-12 / 2023-02 | 【实测】 | 高 | LP-S21 |
| SeDRAM 多层阵列（VLSI 2023） | 细节距混合键合 + mini-TSV，多层 DRAM | **135 GB/s/Gbit，0.66 pJ/bit**；每 Gbit 2048 个数据接口 × 541 Mbps | — | 测试芯片 | 2023-06 | 【实测】 | 高 | LP-S22 |
| 阿里达摩院 + 紫光国芯（ISSCC 2022） | 3D 逻辑到 DRAM 混合键合 + 近存引擎（推荐系统） | **64 Mb/mm²**，184 QPS/W | — | 测试芯片 | 2022-02 | 【实测】（经 LP-S23 参考文献转引） | 中 | LP-S24 |
| 中科院微电子所 + 紫光国芯（ISSCC 2026，Cao 等） | 两层 DRAM + 一层逻辑，边缘 LLM 近存计算 | **12.77 GB/s/mm²，99.4 Mb/mm²（两层 DRAM 合计，按占地面积），0.67 pJ/b，1.2 GHz**；访存延迟最多降 93% | 逻辑 28nm（由前代 40nm 升级，据 LP-S23） | 测试芯片 | 2026-02 | 【实测】 | 高 | LP-S20 |
| ATLAS 验证用 3D-DRAM 加速器（北大 + 紫光国芯 + 后摩智能 + 港科大） | 4 层 DRAM（每层 800 mm²）堆在 800 mm² 逻辑上 | 混合键合 I/O 密度 **110,000/mm²（3 µm 节距）**，访存能耗 **0.66–0.88 pJ/bit**（比 HBM 低 77–83%）；整芯 16 TB/s、253 TFLOPS（FP16）、242 W；**每核 45.43 mm²、5 GB、1 TB/s、4 MB SRAM** | 逻辑 7nm；DRAM 每层 8192 bank × 2.5 MB | 论文称「已商用部署的多层 3D-DRAM 技术」，用真实硅片校验（误差 ≤8.57%） | 2026-04-09 | 【实测】 | 高 | LP-S23 |
| H2-LLM（ISCA 2025） | 边缘异构混合键合加速器，经 LPDDR5 接口接入 NPU 内存系统 | 仿真设计空间探索 | — | 研究 | 2025-06 | 【推算】仿真 | 中 | LP-S25 |

**由 ATLAS 表推出的密度**【推算】：每层 8192 × 2.5 MB = 20 GB / 800 mm² = 25 MB/mm² = **0.2 Gb/mm²/层**；每核占地约 50 mm² × 4 层 × 25 MB/mm² ≈ 5 GB，与表中「每核 5 GB、1 TB/s」一致。也就是说，**「4–5 GB、1 TB/s」这个规格已有硅验证的对应物：约 45–50 mm² 占地、4 层 DRAM**（只是逻辑层用了 7nm、面向云端）。ISSCC 2026 边缘芯片的 99.4 Mb/mm²（两层合计）折合约 0.05 Gb/mm²/层，密度低得多（推测用的是较老的 DRAM 节点）。

**对本方案参数的核对**【推算】：
- 带宽：SeDRAM 一代 34 GB/s/Gb × 32 Gb ≈ 1.09 TB/s；多层版 135 GB/s/Gb × 32 Gb ≈ 4.3 TB/s。**4 GB / 1 TB/s 在已发表能力范围内。**
- 能耗：已发表 0.66–0.88 pJ/bit（SeDRAM、ATLAS），0.67 pJ/b（ISSCC 2026），d-Matrix 0.37 pJ/bit（§4.2）。**0.5–1 pJ/bit 的目标与实测一致。**
- 面积带宽密度：1 TB/s 摊在 136 mm²（本文基准占地）上是 7.4 GB/s/mm²，低于 ISSCC 2026 的 12.77 GB/s/mm² 和 ATLAS 的 20 GB/s/mm²。

### 4.2 产业 / 产品

| 实例 | 关键参数 | 状态 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|---|
| 紫光国芯 SeDRAM | WoW 混合键合 + mini-TSV，多层堆叠，去掉 PHY-PHY 与中介层；「可为算力芯片提供数十 TB/s 访存带宽」；公司称「业内率先实现全球量产」 | 2026-07 北交所 IPO 受理，拟募 11.5 亿元（定制存储器项目 2.2 亿）；2025 年营收 18.3 亿元、毛利率 22.98%（公司整体，不是 SeDRAM 单项） | 2026-07 | 【报道】公司口径 | 中（技术）/ 低（「首家量产」） | LP-S26 |
| SeDRAM 单价 / 成本 | **未找到**（招股书技术章节可能有，未取得） | — | — | — | — | — |
| d-Matrix Raptor（Hot Chips 2026） | 定制 3D DRAM 与逻辑面对面键合，**36 µm 节距**，逻辑 **TSMC N4**；**每卡 32 GB、>100 TB/s、0.37 pJ/bit**（HBM4 为 2–3 pJ/bit）；每卡最多 4 封装 × 4 chiplet；有报道称每颗 DRAM die 4 GB（单一来源） | 早期硅片已展示，商用版计划中，未出货；价格未披露 | 2026-08-24 | 【规格】厂商声明 | 中（每 die 4 GB：低） | LP-S27 |
| AMD 混合键合 3D DRAM（Hot Chips 2026） | 能效「最高」比微凸块 HBM 高 17 倍（估算，非产品）；量产障碍：表面平整与洁净度、高温加快 DRAM 漏电需更多刷新 | 研究 / 演示 | 2026-09-02 | 【报道】 | 中 | LP-S28 |
| 华邦 CUBE（边缘 AI） | <1 pJ/bit；32–256 GB/s/die（后续资料称 1K–4K I/O × 2 Gbps，可达 256 GB/s–1 TB/s）；256 Mb–8 Gb/die；D20 → 2025 年 D16（16 Gb/die）；支持 CoW / WoW / 2.5D | 已发布，量产细节未公开 | 2023-09-27 | 【规格】 | 中 | LP-S29 |
| SK 海力士 3D 堆叠 DRAM-on-logic | 在圣何塞招聘逻辑 die 协同设计工程师，与一家美国客户合作，目标端侧 AI / 手机 AP；TSMC 2026 技术论坛路线图提到，无时间表 | 早期 | 2026-07-24 | 【报道】ZDNet 转 TrendForce | 中 | LP-S30 |
| 三星 LPW DRAM（手机用宽 I/O 堆叠 LPDDR） | 204.8 GB/s，1.87 pJ（The Bell 引三星资料）；无逻辑 base die；Apple 为合作方 | 计划 2028 年量产 | 2025-03-14 | 【报道】 | 中 | LP-S31 |
| 三星 LPDDR5X-PIM（Hot Chips 2026） | 与通用 LPDDR 同阵列；Llama 3.1 8B：81.3 tok/s（前代 27），处理时间 5.4 s（标准 LPDDR5X 12.3 s）；正推动 LPDDR6-PIM 标准化 | 发布，量产时间未披露 | 2026-08-26 | 【规格】厂商声明 | 中 | LP-S32 |
| 长鑫存储（CXMT）晶圆对晶圆混合键合 DRAM | 合肥中试线测试 W2W 混合键合，存储阵列与外围逻辑分到两片晶圆 | 研发 / 中试 | 2026-07 | 【报道】韩国经济日报 | 低–中 | LP-S33 |

---

## 5. 混合键合 / 3D 堆叠的成本加成，以及 LPDDR-PIM 面积开销

### 5.1 公开可得的成本线索

| 项目 | 数值 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|
| 混合键合每片晶圆的美元成本 | **未找到**（Yole / SystemPlus 的 AMD V-Cache、YMTC Xtacking 拆解报告有「Bonding Cost」章节，均付费） | — | — | — | LP-S36、LP-S38 |
| W2W 成熟度 | 「W2W 键合已是成熟工艺，并不特别贵」（CIS、NAND 已大规模使用）；小 die 时 W2W 更便宜，大 die 时 W2W 成本曲线陡升（坏 die 会拖累好 die） | 2024-02-09 | 【报道】SemiAnalysis | 中 | LP-S36 |
| 混合键合机台价 | 每台约 40 亿韩元（约 $2.9M），是 TC 键合机的 2 倍以上（HBM 用 D2W 机台） | 2025-10-07 | 【报道】News1 / TrendForce | 中 | LP-S37 |
| W2W 成本模型（2015） | $3M 机台；每片 5 min 与 30 min 两种吞吐，对单颗堆叠成本只差约 $0.10；W2W 只有在良率很高时才最便宜，适合小 die | 2015-04-27 | 【推算】第三方模型（老） | 低 | LP-S38 |
| 3D 晶圆成本比（解析式） | r_W = (C_W,bot + C_W,top + c_B) / C_W,2D ≥ 2；W2W 堆叠良率 = y_B · y²（无法挑 KGD） | 2023-03 | 【推算】同行评审模型 | 高（公式） | LP-S39 |
| HBM 相对 DDR5 的「堆叠税」 | 同工艺同容量 HBM die 大 35–45%；含 TSV 封装良率低 20–30%；生产周期长 1.5–2 个月 | 2024-03-18 | 【报道】TrendForce | 中–高 | LP-S40 |
| HBM 合约价 | HBM3E $1.50–1.60/Gb（$12–12.8/GB），HBM4 $2.00/Gb（$16/GB） | 2026-07-12 | 【报道】DigiTimes 经首尔经济日报 | 中 | LP-S42 |

**本文对键合 + 减薄 + 背面 I/O 的取值**【推算，置信度低】：每对晶圆（一个键合界面）乐观 $400 / 基准 $700 / 悲观 $1,200，多层每增加一层再加 $500（mini-TSV）。依据：机台约 $3M 级、W2W 已用于售价几美元的 CIS 传感器、2015 年模型显示吞吐对单颗成本影响在 $0.1 量级。**敏感性**：即使取 $2,000/对，摊到 136 mm² 占地（每片 464 个位置）也只有 $4.3/颗。键合工序本身不是成本大头，**真正的成本放大器是 W2W 无法挑 KGD 导致的良率连乘（§7.2）**。

### 5.2 PIM 面积开销

| 方案 | 开销 | 口径 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|---|
| CD-PIM（LPDDR5-PIM，DATE 2026） | 每个 PU 14,941 µm²、4.5 mW（**TSMC 28nm 逻辑综合**）；合计相当于 **32 Gb LPDDR5 die 面积的 0.8%**，总功耗 +144 mW | 逻辑按 28nm 逻辑工艺综合，不是 DRAM 工艺 | 2026-01-18 | 【推算】综合结果 | 中 | LP-S35；本地 lpddr-pim 调研 |
| 三星 HBM-PIM（Aquabolt-XL） | 带 PCU 的 die 只有 4 Gb（标准 HBM2 die 为 8 Gb），每 die 32 个 300 MHz FP16 PCU；6 GB 栈 = 4 颗 PIM die + 4 颗普通 8 Gb die | die 级容量减半 | 2021-02-18 | 【实测】产品 | 高 | LP-S34 |
| SK 海力士 GDDR6-AiM | 面积开销**未找到** | — | — | — | — | — |

**解读**：0.8% 是在 28nm 逻辑工艺下综合的数字；同样的逻辑放在 DRAM 工艺（晶体管慢、金属层少）里，面积通常要大好几倍。三星 HBM-PIM 实际产品是「容量减半」。所以**「在 DRAM die 内塞计算」的真实面积代价在 0.8%（乐观）到 50% 容量（产品实例）之间**。本方案的 3D-PIM 把计算放在独立逻辑 die 上，DRAM die 不承担这部分开销，代价转成了逻辑 die + 键合的成本（§7.2）。

---

## 6. DRAM 位成本（3D-PIM 成本的最大变量）

| 项目 | 数值 | 日期 | 性质 | 置信度 | 来源 |
|---|---|---|---|---|---|
| 美光 1β 16Gb LPDDR5X die | 36.78 mm²，**0.435 Gb/mm²** | 2023 | 【实测】TechInsights | 高 | LP-S43 |
| 三星 D1b 16Gb LPDDR5X | 446.67 Mb/mm² | 2025 | 【实测】TechInsights | 中–高 | LP-S43 |
| DDR5 16Gb 现货（2024 年末） | 约 $4.6 → $2.3/GB；2025 年末 >$28 | 2025 | 【报道】二手引市场研究 | 低–中 | LP-S44 |
| 12 GB LPDDR5X 模组 | 2025 年初 $25–29（约 $2.1–2.4/GB）→ 约 $70 | 2025–2026 | 【报道】单一来源 | 低 | LP-S44 |
| 移动 DRAM 2024 → 2026 | 约 $3 → $20/GB | 2026 | 【报道】本地调研 | 中 | LP-S45（姊妹文件引 memory-capacity-crunch-CN.md） |
| DDR5 16Gb 4800/5600 现货均价 | **$60.10（$30/GB）** | 2026-10-14 | 【报道】一手价格页 | 高 | LP-S41 |
| DDR5 8GB SO-DIMM 合约价 | **$133（$16.6/GB）** | 2026-08-31 | 【报道】一手价格页 | 高 | LP-S41 |
| 移动 DRAM 合约价 | 2Q26 LPDDR5X +78–83% QoQ；3Q26 +8–13% QoQ；4Q26 涨幅「进一步收敛」 | 2026-05 / 2026-08 | 【报道】TrendForce | 中–高 | LP-S41、LP-S44 |
| LPDDR5X 渠道价（16 GB 封装） | $235（$14.7/GB） | 2026-10-13 | 【报道】 | 高 | LP-S45（PM-S7） |

**把 $/GB 换算成「DRAM 晶圆等效价值」**【推算】：

```
1β 16Gb：DPW(36.78) ≈ 1,812；良率 90% → 1,631 颗 × 2 GB = 3,262 GB/片
晶圆等效价值 = 3,262 × ($/GB) × 0.87          # 0.87 = 扣除封测约 13%（假设）
  $2/GB → $5.7k；$3/GB → $8.5k；$10/GB → $28.4k；$15/GB → $42.6k
```

- 正常周期（2023–2025 年 $2–3/GB）下，DRAM 晶圆等效价值约 $5.7–8.5k；按 DRAM 厂约 40% 毛利倒推，制造成本约 $4–6k/片【推算，低–中】。
- 2026 超级周期（$15/GB 级）下，**一片 DRAM 晶圆的市场价值约 $42k，已超过一片 N2 逻辑晶圆（约 $30k）**。定制 3D-PIM 的 DRAM 晶圆要和标准品抢产能，机会成本按市价算。
- 定制 3D DRAM 还要再乘两个系数：(1) 密度惩罚。ATLAS 推出 0.2 Gb/mm²/层、ISSCC 2026 约 0.05 Gb/mm²/层，都明显低于标准品 0.435；若像 CXMT 那样把外围电路移到逻辑晶圆，有望接近标准品。(2) 小批量定制溢价，本文取 1.0–1.3【推算假设，低】。

---

## 7. 成本推算

### 7.1 NPU + 64 MB SRAM 硅成本（集成进 PC SoC）

方法：按 §1.2 的边际成本公式，把 NPU + SRAM 面积 ΔA 加到一颗原本 A0 mm² 的 SoC 上，算多出来的良品 die 成本。

| 情景 | 面积 ΔA | 节点 / 晶圆价 / D0 | 基础 SoC A0 | **边际硅成本** | 按平均 $/mm² 分摊 | 若做成独立 chiplet（不含 D2D 与封装） |
|---|---|---|---|---|---|---|
| 乐观 | 35.4 mm²（14.3 + 21.1） | N3，$20k，0.08 | 120 mm² | **$14.7（¥104）** | $12.8（¥91） | $10.9（¥77） |
| 基准 | 46.3 mm²（22.2 + 24.1） | N3，$23k，0.10 | 150 mm² | **$25.3（¥180）** | $21.1（¥150） | $16.9（¥120） |
| 悲观 | 74.2 mm²（43.5 + 30.7） | N3，$27k，0.10 | 180 mm² | **$52.6（¥373）** | $42.8（¥304） | $33.2（¥236） |
| 悲观（N2） | 63.4 mm² | N2，$30k，0.12 | 157 mm² | $49.9（¥354） | — | — |
| 基准面积放到 N2 | 39.5 mm² | N2，$30k，0.12 | 130 mm² | $28.0（¥199） | — | — |

补充（未计入上表）：SoC 侧连接 3D-PIM 的 PHY / 控制器约 3 mm²，N3 边际约 $1.7；芯片厂毛利（若 OEM 按 SoC 售价付费，而 SoC 厂毛利 40–60%，则 ×1.7–2.5）；NPU IP / 流片 NRE（摊销取决于出货量）。

### 7.2 4 GB 3D-PIM 成本

**结构假设**：1 层 DRAM 与 1 层逻辑做 W2W 混合键合（逻辑 die 与 DRAM die 同占地），逻辑 die 上做 GEMV / 注意力（INT8 GEMV 约 2 op/B × 1 TB/s ≈ 2 TOPS 量级，所需逻辑面积远小于占地，所以用便宜的成熟节点），对外接 SoC 的接口 PHY 也放在逻辑 die 上。容量 32 Gb × 1.06（冗余 / ECC）= 33.9 Gb。

```
占地 A  = 33.9 Gb / DRAM 密度(Gb/mm²/层) / 层数
位置数 n = DPW(A)
Y_stack = Y_logic(A, D0) × Y_DRAM^层数 × Y_bond^层数        # W2W 无法挑 KGD，良率连乘（LP-S39）
良品成本 = (W_DRAM×层数 + W_logic + W_bond×层数 + W_TSV×(层数−1)) / n / Y_stack + 封装测试
```

**参数**：

| 参数 | 乐观 | 基准 | 悲观 | 依据 |
|---|---|---|---|---|
| DRAM 密度 | 0.40 Gb/mm²/层 | 0.25 | 0.16 | 标准品 0.435（LP-S43）；ATLAS 推出 0.2（LP-S23）；ISSCC 2026 约 0.05（LP-S20） |
| 占地（1 层） | 85 mm² | 136 mm² | 212 mm² | 推算 |
| DRAM 晶圆（正常周期） | $5.7k（$2/GB，×1.0） | $10.2k（$3/GB × 定制 1.2） | $11.1k（$3/GB × 1.3） | §6 |
| DRAM 晶圆（2026 超级周期，$15/GB） | $42.6k × 1.0 | × 1.2 | × 1.3 | §6 |
| DRAM 良率（修复后） | 92% | 90% | 85% | 推算假设 |
| 逻辑节点 / 晶圆 / D0 | 12nm 级 $4.5k / 0.06 | 16/12nm $5.5k / 0.07 | 7nm $9.5k / 0.08 | LP-S6；ISSCC 2026 用 28nm、ATLAS 用 7nm |
| 键合 + 减薄 + 背面 I/O（每对晶圆） | $400 | $700 | $1,200 | §5.1 推算 |
| 键合良率 | 99% | 98% | 95% | 推算假设 |
| 封装 + 最终测试（含 DRAM 测试） | $3 | $5 | $8 | 推算假设 |

**结果（良率摊销后的分项）**：

| 情景 | Y_stack | DRAM | 逻辑 die | 键合 | 封装测试 | **合计** |
|---|---|---|---|---|---|---|
| 乐观 · 正常周期 | 0.87 | $8.6（¥61） | $6.8（¥48） | $0.6（¥4） | $3（¥21） | **$19.1（¥135）** |
| 基准 · 正常周期 | 0.80 | $27.4（¥195） | $14.8（¥105） | $1.9（¥13） | $5（¥36） | **$49.1（¥348）** |
| 悲观 · 正常周期 | 0.68 | $56.2（¥399） | $48.3（¥343） | $6.1（¥43） | $8（¥57） | **$118.7（¥843）** |
| 乐观 · 2026 超级周期 | 0.87 | $64.6（¥459） | $6.8（¥48） | $0.6（¥4） | $3（¥21） | **$75.0（¥533）** |
| 基准 · 2026 超级周期 | 0.80 | $137.2（¥974） | $14.8（¥105） | $1.9（¥13） | $5（¥36） | **$158.9（¥1,128）** |
| 悲观 · 2026 超级周期 | 0.68 | $281.6（¥1,999） | $48.3（¥343） | $6.1（¥43） | $8（¥57） | **$344.1（¥2,443）** |
| 基准 · DRAM 按制造成本底（$5k/片，DRAM 厂自制） | 0.80 | $13.4（¥95） | $14.8（¥105） | $1.9（¥13） | $5（¥36） | $35.1（¥249） |

**多层变体**（基准密度、正常周期）：2 层（占地 68 mm²）$41.5（¥295）；4 层（34 mm²，与 ATLAS 每核结构相近）$39.3（¥279）。层数增加能缩小逻辑 die、提高每片位置数，但 mini-TSV 和良率连乘会吃掉一部分收益；悲观情景的逻辑 die 成本（$48）主要来自「低密度 DRAM 迫使逻辑 die 也做到 212 mm²」，换成 2 层或成熟节点可以明显下降。

**可能的抵扣（未计入）**：如果 4B 模型权重常驻 3D-PIM，主内存 LPDDR 可以少配 4 GB，省 4 × $2.5–15 = **$10–60（¥71–426）**。

### 7.3 合计（AI 子系统硅 + 封装增量，不含 NRE、毛利、LPDDR 抵扣）

| 情景 | NPU + SRAM | 3D-PIM | 合计 USD | 合计 CNY |
|---|---|---|---|---|
| 乐观 · 正常周期 | $14.7 | $19.1 | $33.8 | ¥240 |
| 基准 · 正常周期 | $25.3 | $49.1 | $74.4 | ¥528 |
| 悲观 · 正常周期 | $52.6 | $118.7 | $171.3 | ¥1,216 |
| 乐观 · 2026 超级周期 | $14.7 | $75.0 | $89.7 | ¥637 |
| 基准 · 2026 超级周期 | $25.3 | $158.9 | $184.2 | ¥1,308 |
| 悲观 · 2026 超级周期 | $52.6 | $344.1 | $396.7 | ¥2,816 |

---

## 8. 不确定项与未找到清单

**最大不确定项（按影响排序）**：
1. **DRAM 位价格周期**：同一基准技术方案，3D-PIM 在 $3/GB 时是 $49，在 $15/GB 时是 $159，相差 3 倍以上，比所有技术参数的影响都大。2028–29 年量产时 DRAM 处在周期哪个位置，本文无法判断。
2. **定制 3D DRAM 的位密度与 W2W 良率**：已发表的硅片里，边缘向产品只有约 0.05 Gb/mm²/层（ISSCC 2026），云端向 0.2 Gb/mm²/层（ATLAS 推算），都低于标准品 0.435。密度决定占地，占地又同时决定 DRAM 面积、逻辑 die 面积和连乘良率。
3. **NPU TOPS/mm²**：公开且可信的只有三星 4nm 的 3.45（INT8）一个点；Apple / 高通 / AMD 的面积都在付费报告里，Intel 的是按标注图推算。
4. **混合键合 $/wafer**：无公开数字，本文是低置信度推算（好在它不是成本大头）。

**未找到**：Apple M4 / A18 Pro ANE 的绝对面积；高通 Hexagon（X Elite / 8 Elite）面积；AMD XDNA 2 面积；三星 5nm NPU 面积；SK 海力士 AiM 面积开销；SeDRAM 单价 / 客户 / 出货量；混合键合每片晶圆成本；DRAM 晶圆制造成本的一手数字；「SeDRAM-P300 四层堆叠量产」说法的一手出处（搜索摘要出现过，未能核实，未采用）。

---

## 9. 来源

| 编号 | 来源 | 日期 | URL |
|---|---|---|---|
| LP-S1 | TrendForce：TSMC 2nm Reportedly Up 10–20%, Far Below Rumored 50%（引 Investor.com、EE Times） | 2025-10-08 | https://www.trendforce.com/news/?p=46558 |
| LP-S2 | TrendForce：TSMC's 2nm Wafers Reportedly Set to Double in Price（引工商时报） | 2024-10-04 | https://www.trendforce.com/news/2024/10/04/news-tsmcs-2nm-wafers-reportedly-set-to-double-in-price-benefitting-ip-material-companies/ |
| LP-S3 | TechPowerUp：TSMC to Raise Wafer Prices by 10% in 2025（摩根士丹利） | 2024-07 | https://www.techpowerup.com/324323/tsmc-to-raise-wafer-prices-by-10-in-2025-customers-seemingly-agree |
| LP-S4 | TrendForce：TSMC Reportedly to Raise Sub-3nm Prices 3–10% in 2026, Plans Hikes through 2029（引经济日报） | 2025-12-29 | https://www.trendforce.com/news/2025/12/29/news-tsmc-reportedly-to-raise-sub-3nm-prices-3-10-in-2026-plans-hikes-through-2029/ |
| LP-S5 | TechNode：TSMC 3nm capacity still tight, prices seen rising 15% in 2H26 | 2026-06-12 | https://technode.com/2026/06/12/tsmc-3nm-capacity-still-tight-prices-seen-rising-15-in-second-half-of-2026/ |
| LP-S6 | Silicon Analysts：Semiconductor Wafer Pricing by Process Node (2026)；TSMC 3nm Cost Guide（D0 0.14、Murphy） | 2026-09 | https://siliconanalysts.com/data/wafer-pricing ；https://siliconanalysts.com/guide/tsmc-3nm-cost |
| LP-S7 | Tom's Hardware：TSMC's wafer pricing now $18,000 for a 3nm wafer（Creative Strategies） | 2024 | https://www.tomshardware.com/tech-industry/tsmcs-wafer-pricing-now-usd18-000-for-a-3nm-wafer-increased-by-over-3x-in-10-years-analyst |
| LP-S8 | Tom's Hardware：TSMC eyes price hikes … 2027（日经，基础价 +5–10%） | 2026-07 | https://www.tomshardware.com/tech-industry/semiconductors/tsmc-eyes-price-hikes-of-up-to-25-percent-on-chip-production-services-in-2027-report-claims-plans-to-raise-baseline-prices-by-5-percent-to-10-percent-on-advanced-nodes |
| LP-S9 | TSMC 官网：2nm 技术页（4Q25 量产）；HPC 先进技术页（N2P vs N3E 1.2× 逻辑密度、1.15× 芯片密度） | 2026 | https://www.tsmc.com/english/dedicatedFoundry/technology/logic/l_2nm ；https://www.tsmc.com/english/dedicatedFoundry/technology/platform_HPC_tech_advancedTech |
| LP-S10 | Park 等，三星 4nm 8K-MAC NPU，ISSCC 2022 / IEEE JSSC 58(1)（3.45 TOPS/mm² INT8）；三星 5nm 6K-MAC NPU，ISSCC 2021 | 2022-10 / 2021-02 | https://doi.org/10.1109/JSSC.2022.3205713 ；https://doi.org/10.1109/ISSCC42614.2022.9731639 ；https://doi.org/10.1109/ISSCC42613.2021.9365928 |
| LP-S11 | Apple Newsroom：Apple introduces M4 chip（38 TOPS） | 2024-05-07 | https://www.apple.com/newsroom/2024/05/apple-introduces-m4-chip/ |
| LP-S12 | AnandTech 论坛 FlameTail 帖（A17 Pro NPU 35 TOPS、约 5 mm²，无出处） | 2023-12-23 | https://forums.anandtech.com/threads/apple-silicon-soc-thread.2587205/post-41129457 |
| LP-S13 | TechInsights：A14 与 M1 对比（NPU 面积比 0.9）；A18 Pro Digital Floorplan Analysis（摘要） | 2020 末 / 2024 | https://www.techinsights.com/blog/two-new-apple-socs-two-market-events-apple-a14-and-m1 ；https://techinsights.com/ja/node/58753 |
| LP-S14 | Qualcomm Snapdragon X Elite 产品简介（45 TOPS）；Chips and Cheese：Qualcomm's Hexagon DSP, and now, NPU（16K MAC/cycle）；Chips and Cheese：Snapdragon X2 Elite（80 TOPS INT8）；Wccftech：X Elite die 169.6 mm² | 2023-10 / 2025-11 / 2024-10 | https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Product-Brief-Snapdragon-X-Elite.pdf ；https://chipsandcheese.com/p/qualcomms-hexagon-dsp-and-now-npu ；https://chipsandcheese.com/p/qualcomms-snapdragon-x2-elite ；https://wccftech.com/snapdragon-x-elite-die-shot-compared-with-apple-m4/amp/ |
| LP-S15 | AMD 新闻稿：Computex 2024（XDNA 2，50 TOPS）；Guru3D：Strix Point 标注 die（232.5 mm²、N4P、32 AIE tile） | 2024-06-02 / 2024-07 | https://www.amd.com/en/newsroom/press-releases/2024-6-2-amd-unveils-next-gen-zen-5-ryzen-processors-to-p.html ；https://www.guru3d.com/story/amd-ryzen-ai-strix-point-silicon-pictured-and-annotated/ |
| LP-S16 | The Register：Intel details Lunar Lake TOPS（NPU 4 48 TOPS INT8）；Tom's Hardware：Lunar Lake die annotation（Nemez）；Reddit r/hardware：Lunar Lake die shot（Kurnal，compute tile 139.59 mm²，Lion Cove 4.53 mm²） | 2024-06-04 / 2024-10 | https://www.theregister.com/2024/06/04/intel_details_lunar_lake_tops/ ；https://www.tomshardware.com/pc-components/cpus/intel-lunar-lake-cpu-gets-die-annotation-four-skymont-e-cores-slightly-bigger-than-one-lion-cove-p-core ；https://www.reddit.com/r/hardware/comments/1fuuucj/lunar_lake_die_shot/ |
| LP-S17 | TSMC，A 38.1Mb/mm² SRAM in a 2nm-CMOS-Nanosheet Technology，ISSCC 2025；IEEE Spectrum 报道 | 2025-02-16 | https://doi.org/10.1109/ISSCC49661.2025.10904759 ；https://spectrum.ieee.org/sram-intel-tsmc |
| LP-S18 | WikiChip Fuse：IEDM 2022: Did We Just Witness The Death Of SRAM?（N3B 0.0199 / N3E 0.021 µm²） | 2022-12 | https://fuse.wikichip.org/?p=7343 |
| LP-S19 | AnandTech：AMD Demonstrates Stacked 3D V-Cache（64 MB，6×6 mm）；WikiChip Fuse：AMD 3D Stacks SRAM Bumplessly | 2021-06 | https://www.anandtech.com/show/16725 ；https://fuse.wikichip.org/?p=5531 |
| LP-S20 | Cao 等，A 1.2GHz 12.77GB/s/mm² 3D Two-DRAM-One-Logic Process-Near-Memory Chip for Edge LLM Applications，ISSCC 2026（摘要经 OpenAlex） | 2026-02-15 | https://doi.org/10.1109/ISSCC49663.2026.11409184 |
| LP-S21 | Bai 等，SeDRAM IEDM 2020（34 GB/s/1Gb，0.88 pJ/b）；A True Process-Heterogeneous Stacked Embedded DRAM Structure Based on Wafer-Level Hybrid Bonding，Electronics 12(5) | 2020-12 / 2023-02-21 | https://doi.org/10.3390/electronics12051077 |
| LP-S22 | Wang 等，A 135 GBps/Gbit 0.66 pJ/bit Stacked Embedded DRAM with Multilayer Arrays by Fine Pitch Hybrid Bonding and Mini-TSV，VLSI 2023；闪存市场报道 | 2023-06 | https://chinaflashmarket.com/a/179680 |
| LP-S23 | Li 等（北大、紫光国芯、后摩智能、港科大），A Full-Stack Performance Evaluation Infrastructure for 3D-DRAM-based LLM Accelerators（ATLAS），arXiv 2604.08044（正文与 Table 3） | 2026-04-09 | https://arxiv.org/abs/2604.08044 |
| LP-S24 | Niu 等，184QPS/W 64Mb/mm² 3D Logic-to-DRAM Hybrid Bonding with Process-Near-Memory Engine for Recommendation System，ISSCC 2022（经 LP-S23 参考文献 [49] 转引） | 2022-02 | https://arxiv.org/abs/2604.08044 |
| LP-S25 | Li 等，H2-LLM: Hardware-Dataflow Co-Exploration for Heterogeneous Hybrid-Bonding-based Low-Batch LLM Inference，ISCA 2025 | 2025-06-20 | https://doi.org/10.1145/3695053.3731008 |
| LP-S26 | 同花顺：紫光国芯拟 IPO 将加码存储芯片研发；36 氪：紫光国芯北交所申报 | 2026-07-06 / 2026-07-27 | https://news.10jqka.com.cn/20260706/c677958618.shtml ；https://www.36kr.com/p/3913134819333510 |
| LP-S27 | HWBusters：d-Matrix Raptor drops the memory PHY（Hot Chips 2026）；Digital Citizen：d-Matrix Raptor 3D DRAM | 2026-08-24 | https://hwbusters.com/news/d-matrix-raptor-drops-the-memory-phy-32gb-at-100-tb-s-against-hbm4s-192gb-at-18/ ；https://www.digitalcitizen.life/d-matrix-raptor-3d-dram-targets-100-tb-s-bandwidth-at-0-37-pj-per-bit-for-ai-inference/ |
| LP-S28 | PurePC：AMD 3D DRAM hybrid bonding 17× less energy than HBM（Hot Chips 2026）；CloudNews 同题 | 2026-09-02 | https://www.purepc.pl/amd-3d-dram-hybrid-bonding-17x-mniej-energii-niz-hbm ；https://cloudnews.tech/amd-points-to-3d-dram-that-could-be-up-to-17x-more-efficient-than-hbm/ |
| LP-S29 | Winbond 新闻稿：Innovative CUBE Architecture for Powerful Edge AI Devices；Electronic Specifier 后续报道 | 2023-09-27 | https://www.winbond.com/hq/about-winbond/news-and-events/news/2023_0927_winbond_innovative_cube_architecture_edge_ai.html ；https://www.electronicspecifier.com/?p=33330 |
| LP-S30 | TrendForce：SK hynix Reportedly Hires for 3D-Stacked DRAM-on-Logic With a U.S. Customer（引 ZDNet） | 2026-07-24 | https://www.trendforce.com/news/?p=61476 |
| LP-S31 | TrendForce：Samsung Reportedly Teams Up with Apple for Next-Gen LPW DRAM, Eyes 2028 Mass Production（引 The Bell） | 2025-03-14 | https://www.trendforce.com/news/?p=36035 |
| LP-S32 | Financial News（韩国）：三星 Hot Chips 2026 发布 LP-PIM | 2026-08-26 | https://en.fnnews.com/news/202608260930347718 |
| LP-S33 | Wccftech：CXMT developing high-density DRAM without EUV（引韩国经济日报，W2W 混合键合中试线） | 2026-07 | https://wccftech.com/cxmt-developing-high-density-dram-without-euv-might-make-apple-interested/ |
| LP-S34 | eeNews Europe：Samsung embeds AI accelerator in memory chip（HBM-PIM，4 Gb PIM die） | 2021-02-18 | https://www.eenewseurope.com/news/samsung-HBM-PIM-ai-chip |
| LP-S35 | Lin 等，CD-PIM: A High-Bandwidth and Compute-Efficient LPDDR5-Based PIM for Low-Batch LLM Acceleration on Edge-Device，arXiv 2601.12298 / DATE 2026（正文 §IV） | 2026-01-18 | https://arxiv.org/abs/2601.12298 |
| LP-S36 | SemiAnalysis：Hybrid Bonding Process Flow – Advanced Packaging Part 5（免费部分） | 2024-02-09 | https://newsletter.semianalysis.com/p/hybrid-bonding-process-flow-advanced |
| LP-S37 | TrendForce：Hybrid Bonder Equipment Market Reportedly Near $2B by 2028（每台约 40 亿韩元） | 2025-10-07 | https://www.trendforce.com/news/2025/10/07/news-hybrid-bonder-equipment-market-reportedly-near-2b-by-2028-as-korean-makers-race-to-next-gen-hbm-tools/ |
| LP-S38 | 3D InCites：Wafer-to-Wafer Bonding Cost Analysis（Lujan / Palesko）；Yole：AMD 3D V-Cache with TSMC SoIC（付费，含 Hybrid bonding Cost 章节） | 2015-04-27 / — | https://www.3dincites.com/2015/04/wafer-to-wafer-bonding-cost-analysis/ ；https://www.yolegroup.com/product/report/amd-3d-v-cache-with-tsmc-soic-3d-packaging/ |
| LP-S39 | Agnesina 等，Power, Performance, Area, and Cost Analysis of Face-to-Face-Bonded 3-D ICs，IEEE TCPMT 13(3) | 2023-03 | https://doi.org/10.1109/TCPMT.2023.3264520 |
| LP-S40 | TrendForce 新闻稿：HBM die 比 DDR5 大 35–45%，良率低 20–30% | 2024-03-18 | https://www.trendforce.com/presscenter/news/20240318-12081.html |
| LP-S41 | TrendForce DRAM 价格页（DRAM Spot 2026-10-14；DRAM Contract 2026-08-31；3Q26 Mobile DRAM 2026-08-03） | 2026-10-14 | https://www.trendforce.com/price/dram/dram_spot ；https://www.trendforce.com/price/dram/mobileDram_contract |
| LP-S42 | Capital & Compute：HBM price tracker（引首尔经济日报 / DigiTimes） | 2026-07-12 | https://capitalandcompute.net/memory-prices/hbm/ |
| LP-S43 | TechInsights：首款 D1β DRAM 分析（美光 1β 16Gb，36.78 mm²，0.435 Gb/mm²）；Samsung K4K6E165YE D1b 16Gb LPDDR5X Process Analysis | 2023 / 2025 | https://techinsights.com/zh-cn/discover-inaugural-analysis-reports-d1b-dram-and-232l-qlc-3d-nand ；https://techinsights.com/ja/node/59204 |
| LP-S44 | OSCOO：Rising DDR Prices（DDR5 16Gb 现货 $4.6 → >$28）；Let's Data Science：Apple Accepts Doubling Price For LPDDR5X（12 GB $25–29 → ~$70）；中时新闻网：TrendForce 2Q26 Mobile DRAM 合约价 | 2025-12 / 2026 / 2026-05-15 | https://www.oscoo.com/?p=14430 ；https://letsdatascience.com/news/apple-accepts-doubling-price-for-lpddr5x-memory-f31f13f8 ；https://wantrich.chinatimes.com/news/20260515900291-420101 |
| LP-S45 | 姊妹文件：PC 端侧 AI 子系统 BOM 存储器价格数据（PM-S#） | 2026-10-14 | [pc-cost-memory-prices.md](pc-cost-memory-prices.md) |
| LP-S46 | 本地调研：LPDDR-PIM 架构、A16g DRAM/PIM 异构协同管理、HBM4 与先进封装 | — | 见文首「本地参考」 |

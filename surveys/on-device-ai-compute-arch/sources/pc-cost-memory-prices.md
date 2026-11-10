# PC 端侧 AI 子系统 BOM：存储器价格数据（2025–2027）

> 用途：为「PC 上 HBF / 高带宽 NVMe 流式加载 200B MoE（FP4 专家约 100 GB）做 prefill，加上 4 GB 3D-PIM（DRAM 堆叠在逻辑 die 上）跑 4B 模型 decode，系统 DRAM 153 GB/s」这套方案做增量成本核算，判断「AI 子系统增量成本能否压到几百元人民币」。
>
> - 采集日期：**2026-10-14**（价格页快照均为该日或之前最近一次更新）
> - 汇率：**1 USD = 7.1 CNY**（全文统一）
> - 单位换算：1 GB = 8 Gb；1 TB = 1000 GB（SSD 零售口径）；NAND 晶圆价按「每颗等效 die」报价，1Tb = 128 GB，512Gb = 64 GB
> - 来源编号：PM-S1…PM-S33，见第 9 节
> - 本地参考：[`../../memory-capacity-crunch-CN.md`](../../memory-capacity-crunch-CN.md)（移动 DRAM 2024→2026 约 $3 → $20/GB）、[`../../ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md`](../../ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md)（HBF 规格与「同价位 8–16× 容量」）

**价格类型说明**：合约价（原厂对 OEM / 模组厂季度或月度议价）｜现货价（DRAMeXchange 等现货盘）｜渠道价（CFM 闪存市场渠道 / 模组报价）｜零售价（美国电商最低价）｜预测（机构对未来季度或年份的预测）｜估算（本文或第三方基于公开数据推算，非成交价）。

**置信度说明**：**高** = 一手机构公开数据（TrendForce / CFM 价格页、TrendForce 新闻稿），日期明确；**中** = 权威媒体 / 券商转述一手数据，或机构点估计；**低** = 聚合站、传闻，或本文推算。

---

## 0. 速览：核心价格一页表

| 品类 | 口径 | $/GB | ¥/GB | 日期 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|---|---|
| LPDDR5X（16 GB 封装 128Gb） | 渠道价 $235 | 14.7 | 104 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| LPDDR5X 16Gb die | 现货价 $29.80 | 14.9 | 106 | 2026-09-09 | 现货价 | 低（聚合站转录 TrendForce） | PM-S8 |
| LPDDR5X 合约价（链式推算） | 1Q26 约 $10 → 2Q26 +78~83% → 3Q26 +8~13% → 4Q26 +0~5% | 19.2–21.7（4Q26） | 136–154 | 4Q26 | 估算 | 低–中 | PM-S3/S4/S5/S9 |
| LPDDR5X 合约价 1Q27 | 在 4Q26 基础上 +13~18% | 21.7–25.6 | 154–182 | 1Q27 | 预测 + 估算 | 低–中 | PM-S5 |
| LPDDR6 | 较 LPDDR5X 贵约 20%（传闻） | 未找到绝对价 | — | 2026-01 | 传闻 | 低 | PM-S31 |
| DDR5 8GB SO-DIMM（PC OEM） | 合约价 $133 | 16.6 | 118 | 2026-08 下半月 / 9 月持平 | 合约价 | 高 | PM-S6、PM-S5 |
| DDR5 16Gb 4800/5600 | 现货均价 $60.10 | 30.1 | 213 | 2026-10-14 | 现货价 | 高 | PM-S6 |
| DDR5 16Gb eTT | 现货均价 $27.50 | 13.8 | 98 | 2026-10-14 | 现货价 | 高 | PM-S6 |
| DDR5 SO-DIMM 16GB 5600 | 渠道价 $245 | 15.3 | 109 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| NAND TLC 1Tb 晶圆 | $29.00 | 0.227 | 1.61 | 2026-10-14 | 渠道价（CFM 晶圆） | 高 | PM-S7 |
| NAND QLC 1Tb 晶圆 | $26.00 | 0.203 | 1.44 | 2026-10-13 | 渠道价（CFM 晶圆） | 高 | PM-S7、PM-S15 |
| NAND TLC 512Gb 晶圆 | 现货均价 $18.833 | 0.294 | 2.09 | 2026-10-05 | 现货价 | 高 | PM-S11 |
| PC OEM SSD 1TB TLC PCIe（Value） | 合约均价 $321 | 0.321 | 2.28 | 3Q26（2026-08-05 更新） | 合约价 | 高 | PM-S11 |
| 客户端 PCIe 5.0 SSD 1TB | 零售中位 $253 | 0.253（$253/TB） | 1.80 | 2026-10-14 | 零售价 | 高 | PM-S20 |
| 客户端 PCIe 5.0 SSD 2TB | 零售中位 $421 | 0.211（$210/TB） | 1.49 | 2026-10-14 | 零售价 | 高 | PM-S20 |
| 客户端 PCIe 5.0 SSD 4TB | 零售中位 $839 | 0.210（$210/TB） | 1.49 | 2026-10-14 | 零售价 | 高 | PM-S20 |
| HBM3E 12-Hi 36GB | 2025 年约 $300–350 / 堆栈；2026 年 +约 20% | 8.3–9.7（2025），约 10–11.7（2026 推算） | 59–69 / 71–83 | 2025-08 / 2025-12 | 估算（媒体报道成交价位） | 中 / 低 | PM-S25、PM-S26 |
| HBM4 12-Hi 36GB | 约 $500–600 / 堆栈 | 13.9–16.7 | 99–118 | 2025-08 → 2026 | 估算（媒体报道成交价位） | 中 | PM-S24、PM-S25 |
| HBM4 12-Hi 36GB 2027 | 约 $1,300 / 堆栈；TrendForce：2027 年 HBM 混合 ASP 同比 +121% | 36.1 | 256 | 2026-09-29 / 10-01 | 预测 | 中 | PM-S23、PM-S24 |
| HBM（第三方估算） | 「约 $20–30/GB」 | 20–30 | 142–213 | 2026-08-23 | 估算 | 中–低 | PM-S27 |
| HBF | 无官方 $/GB；按「与 HBM 同价位、容量 8–16×」推算 | 约 0.9–4.5 | 6–32 | 2026-08/09 | 估算（本文推算） | 低 | PM-S27~S30 |

---

## 1. DRAM：LPDDR5X / LPDDR6 / DDR5

### 1.1 2026 年各季度涨幅时间线（合约价，季度环比）

| 时间 | 品类 | 环比涨幅 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|
| 1Q26 | 移动 DRAM / LPDDR5X | +58~63% | 合约价（实际 / 预测） | 中 | PM-S9（转述 TrendForce）；本地 crunch 文档 ref 1 |
| 1Q26 | LPDDR5 合约价绝对值 | 约 **$10/GB**（约为 1Q25 的 3 倍） | 合约价（SemiAnalysis 估计） | 中–低 | PM-S9 |
| 2Q26 | LPDDR5X | **+78~83%**（LPDDR4X ≥ +70~75%） | 合约价（预测，2026-05-14） | 高 | PM-S3 |
| 2Q26 | LPDDR5(X) 绝对值 | 约 $19.3–19.8/GB（wccftech 用 $10 × 1.93–1.98 插值；若用后来的 +78~83%，约 **$17.8–18.3/GB**） | 估算 | 低 | PM-S9 |
| 2Q26 | 智能手机内存（Counterpoint） | 环比 +80% 以上；中端机内存占 BOM 40% | 市场价（机构估计） | 中 | PM-S10 |
| 2Q26 | 长期协议（LTA） | 每 64 GB 价格区间 $500–1,350，相当于 **$7.8–21/GB** 的下限与上限 | 合约（报道） | 中–低 | PM-S9 |
| 3Q26 | 移动 DRAM 整体 | **+8~13%**（三星中个位数，SK 海力士、长鑫追涨） | 合约价（预测，2026-08-03） | 高 | PM-S4 |
| 3Q26 | 通用 DRAM 整体 | +13~18%；HBM 混合 +8~13% | 合约价（预测） | 高 | PM-S1、PM-S2 |
| 4Q26 | 通用 DRAM 整体 | **+10~15%**；HBM 混合 +15~20% | 合约价（预测，2026-09-30） | 高 | PM-S1 |
| 4Q26 | PC DRAM / 服务器 DRAM / 移动 DRAM | +13~18% / +10~15% / **+0~5%** | 合约价（预测，券商转述 TrendForce 完整报告） | 中 | PM-S5 |
| 4Q26 | 高盛自估（三星、SK 海力士均值） | PC +9%、服务器 +10%、移动 +3~4% | 预测 | 中 | PM-S5 |
| 1Q27 | LPDDR5X / LPDDR4X / PC DRAM / 服务器 DRAM | **+13~18%** / +5~10% / +3~8% / +3~8% | 合约价（预测，券商转述 TrendForce） | 中 | PM-S5 |

### 1.2 LPDDR5X 绝对价（$/GB）

| 口径 | 原始报价 | $/GB | ¥/GB | 日期 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|---|---|
| CFM LPDDR5X 128Gb（16 GB） | $235 | 14.69 | 104.3 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| CFM LPDDR5X 96Gb（12 GB） | $175 | 14.58 | 103.5 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| CFM LPDDR5X 64Gb（8 GB） | $114 | 14.25 | 101.2 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| CFM LPDDR5X 32Gb（4 GB） | $61 | 15.25 | 108.3 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| LPDDR5X-8533 16Gb die（转录 DRAMeXchange 现货盘） | $29.80（同比 +340%） | 14.90 | 105.8 | 2026-09-09 | 现货价 | 低 | PM-S8 |
| 合约价链式推算（4Q26） | $10 ×1.78~1.83 ×1.08~1.13 ×1.00~1.05 | **19.2–21.7** | 136–154 | 4Q26 | 估算 | 低–中 | PM-S3/S4/S5/S9 |
| 合约价链式推算（1Q27） | 4Q26 推算值 ×1.13~1.18 | **21.7–25.6** | 154–182 | 1Q27 | 预测 + 估算 | 低–中 | PM-S5 |
| 本地 crunch 文档口径 | 2Q26 约 $20/GB，LTA 最高 $21/GB | 约 20 | 约 142 | 2026-Q2 | 合约（转述） | 中 | 本地 [`memory-capacity-crunch-CN.md`](../../memory-capacity-crunch-CN.md) §1 |

**说明**：渠道 / 现货口径（约 $14.7–14.9/GB）比合约链式推算（约 $19–22/GB）低约 25–35%。一方面链式推算依赖 SemiAnalysis 给出的「1Q26 约 $10/GB」这个基数，基数本身就不精确；另一方面也说明 2H26 移动 DRAM 已进入「高位盘整」，TrendForce 原文的说法是 *high consolidation*（PM-S4）。TrendForce 移动 DRAM 合约价（LPDDR5X 8/12/16GB）的明细在付费墙后，**未找到公开的 3Q26 / 4Q26 绝对值**。

### 1.3 DDR5（PC）绝对价

| 口径 | 原始报价 | $/GB | ¥/GB | 日期 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|---|---|
| DDR5 8GB SO-DIMM（TrendForce 合约，PC OEM） | 均价 $133（区间 $118–141） | **16.6** | 118.0 | 2026-08 下半月；9 月持平 | 合约价 | 高 | PM-S6、PM-S5 |
| 上项 × 4Q26 PC DRAM +13~18% | — | 18.8–19.6 | 133–139 | 4Q26 | 估算 | 中–低 | PM-S5 |
| 上项 × 1Q27 PC DRAM +3~8% | — | 19.3–21.2 | 137–150 | 1Q27 | 估算 | 低–中 | PM-S5 |
| DDR5 16Gb (2Gx8) 4800/5600 原厂颗粒 | 现货均价 $60.10（日内 $46–70.5） | 30.1 | 213.4 | 2026-10-14 | 现货价 | 高 | PM-S6 |
| DDR5 16Gb eTT（白片） | 现货均价 $27.50 | 13.8 | 97.6 | 2026-10-14 | 现货价 | 高 | PM-S6 |
| DDR5 UDIMM 16GB 4800/5600 模组 | 现货均价 $239 | 14.9 | 106.1 | 2026-10-05 | 现货价 | 高 | PM-S6 |
| CFM DDR5 16Gb Major / eTT | $46 / $27 | 23.0 / 13.5 | 163 / 96 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| CFM DDR5 SO-DIMM 8GB / 16GB 5600 | $122 / $245 | 15.3 / 15.3 | 108 / 109 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| CFM DDR5 UDIMM 16GB / 32GB 5600 | $193 / $330 | 12.1 / 10.3 | 86 / 73 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| DDR5 16Gb (2Gx8) 现货（时间线参照） | 2026-02 均价 $39（环比 +7.4%） | 19.5 | 138 | 2026-02 | 现货价（DigiTimes 转述） | 中 | PM-S13 |
| 2025 年基线：DDR5-6000 32GB 套条零售 | 2025 年中约 $80 → 2026 年初约 $432 | 约 2.5 → 13.5 | 约 18 → 96 | 2025 年中 → 2026 年初 | 零售价（博客转述 Newegg Insider） | 低 | PM-S33 |

**说明**：高盛转述 TrendForce 的数据称，DDR5 16Gb 现货较最新合约价约有 **20% 溢价**（PM-S5）。也就是说，PC OEM 大批量采购的合理口径是合约价 **$16–20/GB**，原厂颗粒现货 $30/GB 属于峰值投机价，不宜用于 BOM。与 2025 年中约 $2.5–3/GB（零售套条口径，以及本地 crunch 文档的移动 DRAM 口径）相比，这一轮涨了大约 5–10 倍。

### 1.4 LPDDR6

- 价格：唯一可查的说法是「**比 LPDDR5X 贵约 20%**」，来源是微博爆料账号，wccftech 给出的可信度为 55%（2026-01-02，PM-S31）。**未找到 LPDDR6 的合约价或现货 $/GB**。
- 时间表：首发仅见于骁龙 8 Elite Gen 6 Pro、天玑 9600 等安卓旗舰，并且据称只配 16 GB；苹果 iPhone 18 系列仍用 LPDDR5X（PM-S31）。
- BOM 建议：如需估算，按 LPDDR5X 取值 × 1.2，置信度低。

### 1.5 DRAM 2027 预测（区分峰值与回落）

| 机构 | 结论 | 日期 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|
| TrendForce | 2027 年 DRAM 供需缺口**进一步扩大**，价格继续上行；新产能要到 2H27 才开始爬坡，**实质产出要到 2028 年** | 2026-07-30 | 预测 | 高 | PM-S16 |
| TrendForce | 服务器 DRAM 合约价从 2H26 到 2H27 每季度继续上涨，但涨幅放缓 | 2026-07-09 | 预测 | 高 | PM-S18 |
| TrendForce | PC DRAM 的供给 2027 年可能因产能转向服务器而**下降** | 2026-09-30 | 预测 | 高 | PM-S1 |
| TrendForce | 2Q26 起签订的部分 LTA 设有价格上限 | 2026-08-25 | 事实 / 预测 | 高 | PM-S17 |
| 美银（BofA） | 4Q26 DRAM +8%、NAND +3%；**2027 年持平或小幅回调**，但全年均价仍高于 2026 年；**2028 年 DRAM −8%、NAND −14%**（「健康回调」） | 2026-08-10 | 预测 | 中 | PM-S19 |
| Luminix（本地文档引用） | 「2027 年底 DDR5/DDR6 跌幅超 50%」情景，概率约 20% | 2026 | 预测（尾部情景） | 低 | 本地 crunch 文档 ref 15 |

**判断**：2026 年的 DRAM 涨幅在 2Q26 见顶（季度环比 +80% 以上），**4Q26 起涨速收敛**（移动 DRAM 仅 +0~5%），但**绝对价格没有回落**；1Q27 新年度议价时 LPDDR5X 可能再涨 13–18%。主流预测认为 DRAM 在 2027 年维持高位，真正的回落要等 2028 年。2027 年出货的 PC 按 **$18–22/GB** 做基准比较稳妥。

---

## 2. NAND：TLC / QLC 晶圆与 OEM 合约

### 2.1 绝对价

| 口径 | 原始报价 | $/GB | ¥/GB | 日期 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|---|---|
| CFM 1Tb TLC 晶圆 | $29.00 | **0.227** | 1.61 | 2026-10-14 | 渠道价（晶圆） | 高 | PM-S7 |
| CFM 1Tb QLC 晶圆 | $26.00（4 月 $28 → 6 月 $27 → 6/23 $26.5 → 9/7 $26） | **0.203** | 1.44 | 2026-10-13 | 渠道价（晶圆） | 高 | PM-S7、PM-S15 |
| CFM 512Gb TLC / 256Gb TLC 晶圆 | $22.00 / $11.00 | 0.344 / 0.344 | 2.44 / 2.44 | 2026-10-14 | 渠道价（晶圆） | 高 | PM-S7 |
| TrendForce 512Gb TLC 晶圆现货 | 均价 $18.833（周内 $16.8–21.0，周环比 −2.9%） | 0.294 | 2.09 | 2026-10-05 | 现货价 | 高 | PM-S11 |
| TrendForce 512Gb TLC 晶圆现货（周评，周环比 +0.39%） | $21.208 | 0.331 | 2.35 | 2026-08-17 | 现货价 | 中–低（搜索摘要转述，未能直接打开当期页面） | PM-S11 |
| 1Tb TLC 晶圆（DigiTimes 转述 CFM） | 2026-02 单月 +25% 至 $25；自 2025-10 起约涨 3 倍 | 0.195 | 1.39 | 2026-02 | 渠道价 | 中 | PM-S13 |
| 1Tb TLC NAND（群联 CEO） | 6 个月内从 $4.80 涨到 $10.70 | 0.0375 → 0.084 | 0.27 → 0.59 | 2025 年中 → 2025-11 | 合约 / 市场价（厂商口述） | 中 | PM-S14 |
| TrendForce PC OEM SSD 1TB TLC PCIe Value | 均价 $321（$265–385） | 0.321 | 2.28 | 3Q26（2026-08-05） | 合约价 | 高 | PM-S11 |
| TrendForce PC OEM SSD 512GB TLC PCIe Value | 均价 $201.13 | 0.393 | 2.79 | 3Q26 | 合约价 | 高 | PM-S11 |
| CFM OEM SSD 1TB / 2TB PCIe 4.0 | $230 / $400 | 0.230 / 0.200 | 1.63 / 1.42 | 2026-10-13 | 渠道价（OEM） | 高 | PM-S7 |
| CFM 渠道 SSD 2TB PCIe 4.0 | $250 | 0.125 | 0.89 | 2026-10-13 | 渠道价 | 高 | PM-S7 |
| TrendForce NAND 晶圆合约价（TLC 1Tb / 512Gb / 256Gb / QLC 1Tb） | 付费墙 | **未找到公开绝对值** | — | 2026-09-30 更新 | 合约价 | — | PM-S11 |

**说明**：
- TrendForce 与 CFM 两家的 OEM SSD 口径差异较大（1TB：$321 对 $230）。TrendForce 是 3Q26 季度合约价，CFM 是 10 月的渠道 / OEM 报价，二者统计口径不同。BOM 建议取二者之间的值。
- 晶圆价是 NAND 的**位成本下限**，未计主控、DRAM 缓存、PCB、封测与利润。整盘 SSD（OEM）约为晶圆价的 1.0–1.4 倍（$0.20–0.32 对 $0.20–0.34），这是因为 3Q26 起 OEM 端在消化低价库存，合约价没有完全跟上晶圆价。

### 2.2 NAND 涨幅时间线与 2027 预测

| 时间 | 结论 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|
| 2025 年中 → 2025-11 | 1Tb TLC 价格翻倍以上（$4.80 → $10.70） | 市场价 | 中 | PM-S14 |
| 2025-10 → 2026-02 | 1Tb TLC/QLC 晶圆约涨 3 倍，512Gb TLC 约涨 5 倍 | 渠道价 | 中 | PM-S13 |
| 2026-07 / 2026-08 | 晶圆合约价**基本持平**，成交清淡；QLC 因买方抵制而「严格持平」 | 合约价（月报摘要） | 高 | PM-S12 |
| 3Q26 | NAND 整体合约价 **+18~23%**（9 月上修；7 月初预测为 +10~15%） | 合约价（估计） | 高 | PM-S1、PM-S2 |
| 4Q26 | NAND 整体 **+15~20%**；企业级 SSD +23~28%（唯一加速的品类）；客户端 SSD 涨幅受抑，PC 品牌下调主流机型 SSD 容量 | 合约价（预测） | 高 / 中 | PM-S1、PM-S5 |
| 4Q26 | 晶圆价格「已达历史高位」，下游渠道无力消化，预计仅温和上涨 | 合约价（预测） | 高 | PM-S1 |
| 2027 | NAND 供需比**转正**，**2H27 进入较宽松环境、价格承压下行** | 预测 | 高 | PM-S16 |
| 2028 | 美银：NAND −14% | 预测 | 中 | PM-S19 |

**判断**：NAND 已于 2H26 在晶圆端出现**价格顶部**（7–8 月持平，10 月 512Gb 现货周环比 −2.9%），但合约端 4Q26 仍在补涨。2027 年是 NAND 最可能先回落的年份，2H27 回落概率较高。

---

## 3. 客户端 PCIe 5.0 SSD 零售价（2026-10）与 PCIe 6.0

### 3.1 PCIe 5.0 零售价（Tom's Hardware 美国最低价追踪，2026-10-14 更新，PM-S20）

| 容量 | 型号与当前最低价 | $/TB 区间 | $/TB 中位 | ¥/TB 中位 | 历史最低价（$/TB） | 类型 | 置信度 |
|---|---|---|---|---|---|---|---|
| 1 TB | Crucial T705 $253、T710 $279、三星 9100 Pro $253、WD SN8100 $249（Corsair MP700 Pro 缺货） | 249–279 | **253** | 1,796 | $119–154 | 零售价 | 高 |
| 2 TB | T705 $386、T710 $434、9100 Pro $408、SN8100 $480（MP700 Pro 缺货） | 193–240 | **210** | 1,495 | $90–100 | 零售价 | 高 |
| 4 TB | MP700 Pro $839、T705 $634、T710 $761、9100 Pro $1,039、SN8100 $839 | 159–260 | **210** | 1,489 | $80–100 | 零售价 | 高 |
| 8 TB | 9100 Pro $2,369 | 296 | 296 | 2,102 | $125 | 零售价 | 高 |

补充：TrendForce SSD 街价追踪显示，PNY CS2150 2TB PCIe 5.0 均价 **$380**（$190/TB，¥1,349/TB），日期 2026-09-24，类型零售价，置信度高（PM-S11）。

**说明**：当前零售价约为 2025 年最低价的 **2–3 倍**。同期 PCIe 4.0 旗舰并不便宜（三星 990 Pro 1TB $239.99、2TB $389），所以在当前价位下 **Gen5 相对 Gen4 的溢价很小**（1TB 档约 $10–40）。

### 3.2 PCIe 6.0 客户端 SSD

| 事项 | 内容 | 日期 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|
| 慧荣（SMI）客户端 PCIe 6.0 平台 | 目标提前到 **2027 年底**（原计划 2028 年量产，成品 2029 年后）；推动力是 NVIDIA 的本地 AI PC（RTX Spark）；年底节点具体指样品、参考设计还是小批量**尚不明确**；同时警告 2027 年 NAND 供给更紧 | 2026-06-20 | 路线图（Tom's Hardware 专访转述） | 中 | PM-S21 |
| 群联（Phison）X3 PCIe 6.0 x4 主控 | 28 GB/s、680 万 IOPS；**2026-12 送样，2027 年中量产出货**；首发 E3.S/E1.S **企业级**；Heise 认为桌面 / 笔记本端约 2030 年才普及 | 2026-06-07 | 路线图 | 中 | PM-S22 |
| PCIe 6.0 客户端 SSD 价格 | **未找到**。媒体只推测首批产品会定位高价段，主流仍会长期停留在 PCIe 4.0/5.0 | — | — | — | PM-S21、PM-S22 |

---

## 4. HBM3E / HBM4

| 品类 | 堆栈价 | $/GB | ¥/GB | 日期 | 类型 | 置信度 | 来源 |
|---|---|---|---|---|---|---|---|
| HBM3E 12-Hi 36GB（SK 海力士对 NVIDIA） | 「$300 区间」（另一说法为 $300 中段） | 8.3–9.7 | 59–69 | 2025-08 | 估算（媒体报道成交价位） | 中 | PM-S25 |
| HBM3E 2026 订单 | 三星、SK 海力士涨价约 20% → 约 $360–420/堆栈（本文推算） | 10.0–11.7 | 71–83 | 2025-12-24 | 报道 + 估算 | 低–中 | PM-S26 |
| HBM4 12-Hi 36GB（SK 海力士对 NVIDIA，1H26） | 约 $500（另有「$500 中段」的说法），较 HBM3E 贵约 50–70% | 13.9 | 98.6 | 2025-08 | 估算（媒体报道成交价位） | 中 | PM-S25 |
| HBM4 12-Hi 36GB（2026 年） | 约 $600 | 16.7 | 118.3 | 2026-10-01 | 估算（首尔经济日报转述业界） | 中 | PM-S24 |
| HBM4 12-Hi 36GB（2027 年） | 约 $1,300（+约 117%） | **36.1** | 256.4 | 2026-10-01 | 预测 | 中 | PM-S24 |
| HBM 混合 ASP 2027 | 同比 **+121%**（TrendForce 上修）；8-Hi 每 Gb 较 12-Hi 溢价 10–20% | — | — | 2026-09-29 | 预测 | 高 | PM-S23 |
| HBM 合约价 2027 | +70~140% | — | — | 2026-08-25 | 预测 | 高 | PM-S17 |
| HBM（第三方估算） | 「约 $20–30/GB」 | 20–30 | 142–213 | 2026-08-23 | 估算 | 中–低 | PM-S27 |

**与本方案的关系**：3D-PIM（DRAM 堆叠在逻辑 die 上）在工艺上接近 HBM，都需要 TSV / 混合键合、KGD 测试和逻辑基底 die。没有公开市场价时，可**用 HBM 的 $/GB 作为 3D-PIM DRAM 位成本的代理**，再加上低量定制溢价。逻辑 die 本身的成本另计。TrendForce 也指出，堆叠层数越少，基底 die 成本摊得越薄，**每 Gb 反而更贵**（8-Hi 比 12-Hi 贵 10–20%，PM-S23）。4 GB 级别的小容量堆叠，单位成本只会更高。

---

## 5. HBF：价格说法与 $/GB 推算

### 5.1 公开说法（均无绝对 $/GB）

| 说法 | 日期 | 来源 | 置信度 |
|---|---|---|---|
| SanDisk：HBF 与 HBM 带宽相当，**成本相近（similar cost），容量为 HBM 的 8–16 倍** | 2026-09-02 | PM-S30（DigiTimes） | 中 |
| Tom's Hardware（Hot Chips 2026）：HBF 的主要卖点是「**大致相同成本下 8–16 倍容量**」；规格分为三档：Grade 1 为 8-Hi **256 GB** 堆栈 + 8 GT/s UCIe，带宽 384 GB/s；Grade 2 为 512 GB，1.536 TB/s；Grade 3 为 512 GB，3.072 TB/s | 2026-08-26 | PM-S28 | 中（厂商口径转述） |
| OXMIQ 机柜模型（72 GPU、Kimi-K2 FP4）：**在成本与功耗对等**的前提下，纯 HBM 配置为 20.7 TB、1,584 TB/s，纯 HBF 配置为 294.9 TB、922 TB/s，即**容量约 14.2 倍、带宽约 0.6 倍**；结论是「HBM for the rack, HBF for the box」 | 2026-08-26 | PM-S28 | 中 |
| Chipstrat：按 SanDisk 口径，**每 GB 成本约为 HBM 的 1/10**；但成本主体是与 HBM 相同的先进封装（16 层 TSV、CBA 逻辑 die、interposer），即「**HBM 的堆栈价，约 10 倍的位数，而不是 SSD 的价格**」；付费段落有小标题 *HBM is infeasible for edge devices; HBF is not*，正文不可见 | 2026-07-07 | PM-S29 | 中–低 |
| NAND Research：HBM 约 $20–30/GB，「比预期的 HBF 经济性高一个数量级」；SK 海力士与 SanDisk 计划 2026 年底建成试产线，**2027 年商用** | 2026-08-23 | PM-S27 | 中–低 |
| 本地调研：HBF「同价位容量 8–16 倍，不是降价」，没有来源给出 $/GB | 2026 | 本地 [`ufs-hbf-enhancement-CN.md`](../../ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md) §8 | — |

### 5.2 推算（本文估算，置信度低）

公式：**HBF $/GB ≈ HBM $/GB ÷ 容量倍数（8–16，OXMIQ 实测口径约 14）**

| HBM 基数 | ÷16 | ÷14.2 | ÷10 | ÷8 |
|---|---|---|---|---|
| HBM4 2026 $13.9/GB | 0.87 | 0.98 | 1.39 | 1.74 |
| HBM4 2026 $16.7/GB | 1.04 | 1.18 | 1.67 | 2.09 |
| 第三方 $20–30/GB | 1.25–1.88 | 1.41–2.11 | 2.0–3.0 | 2.5–3.75 |
| HBM4 2027 $36.1/GB | 2.26 | 2.54 | 3.61 | 4.51 |

→ **HBF 约 $0.9–4.5/GB（¥6–32/GB）**，中枢约 **$2.5/GB（¥18/GB）**。这一价位约为 2026-10 TLC 晶圆价（$0.20–0.34/GB）的 **3–20 倍**，也是 PCIe 5.0 SSD 零售价（$0.21–0.25/GB）的 **4–20 倍**。

**注意**：
1. 以上都是**数据中心形态**（HBM4 级封装与 interposer）的推算。**端侧 / PC 形态的 HBF 没有产品，也没有价格**（本地 HBF 调研 §8）。
2. HBF 的最小堆栈是 Grade 1 的 **256 GB**。本方案约需 100 GB，按堆栈采购会有冗余容量。
3. HBF 成本的主体是封装而不是 NAND，因此 NAND 跌价对它的传导很弱。若 2027 年 HBM 价格按预测翻倍，「与 HBM 同价」这一锚点会把 HBF 一起抬高。

---

## 6. 推荐取值（面向 2027 年出货的 PC，OEM 量产采购口径）

| 品类 | 乐观 | 基准 | 悲观 | 取值依据 |
|---|---|---|---|---|
| 系统 DRAM（LPDDR5X / DDR5，OEM 合约） | **$12/GB（¥85）** | **$20/GB（¥142）** | **$28/GB（¥199）** | 乐观：接近 2026-10 渠道 / 现货口径 $10–15（PM-S7、PM-S6），并假设 2027 年下半年提前回调。基准：PC DDR5 合约 $16.6 × 4Q26 +13~18% ≈ $19–20；LPDDR5X 链式推算 4Q26 为 $19–22（PM-S5、PM-S6）。悲观：1Q27 LPDDR5X 再涨 13~18% → $22–26，叠加 PC DRAM 供给收缩（PM-S1、PM-S5） |
| LPDDR6 | $14.4/GB（¥102） | $24/GB（¥170） | $33.6/GB（¥239） | LPDDR5X × 1.2（传闻，PM-S31） |
| 3D-PIM 堆叠 DRAM（HBM 代理，不含逻辑 die） | **$15/GB（¥107）** | **$25/GB（¥178）** | **$40/GB（¥284）** | 乐观：约等于 HBM4 2026 合约价 $14–17。基准：第三方 HBM 估算 $20–30 的中值。悲观：HBM4 2027 年 $36 再加小批量定制溢价（PM-S23、PM-S24、PM-S27） |
| NAND TLC（晶圆 / 颗粒位成本） | **$0.12/GB（¥0.85）** | **$0.25/GB（¥1.78）** | **$0.35/GB（¥2.49）** | 乐观：2H27 供需转宽松、价格约腰斩（PM-S16、PM-S19；2025-11 时为 $0.084）。基准：2026-10 1Tb TLC $0.227 至 512Gb TLC $0.294 区间（PM-S7、PM-S11）。悲观：4Q26 再涨 15~20%，并达到 512Gb 渠道价水平 $0.34（PM-S1、PM-S7） |
| OEM 整盘 SSD（PCIe 4/5，TLC） | $0.12/GB | $0.22/GB | $0.33/GB | CFM OEM 2TB 为 $0.20、TrendForce OEM 1TB 为 $0.32（PM-S7、PM-S11） |
| 客户端 PCIe 5.0 SSD 零售 | $110/TB（¥781） | $210/TB（¥1,491） | $280/TB（¥1,988） | 历史低点 $80–100；2026-10 中位 $210；1TB 档或 8TB 档约 $253–296（PM-S20） |
| HBM（参照） | $14/GB（¥99） | $17/GB（¥121，2026）/ $25（2027 混合） | $36/GB（¥256，2027） | PM-S23~S25、PM-S27 |
| HBF（数据中心形态推算） | **$1.0/GB（¥7.1）** | **$2.5/GB（¥17.8）** | **$4.5/GB（¥32）** | HBM $/GB ÷ 8–16（PM-S27~S30），见 §5.2 |

### 6.1 对「几百元」目标的敏感性示例（只算存储位成本，不含逻辑 die、主控、封测、良率）

| 子项 | 乐观 | 基准 | 悲观 |
|---|---|---|---|
| 3D-PIM 4 GB DRAM 位成本 | $60（¥426） | $100（¥710） | $160（¥1,136） |
| 若按普通 LPDDR 计 4 GB（下限参照） | $48（¥341） | $80（¥568） | $112（¥795） |
| 专家权重闪存 128 GB，普通 NAND 位成本 | $15（¥109） | $32（¥227） | $45（¥318） |
| 专家权重闪存 256 GB，普通 NAND 位成本 | $31（¥218） | $64（¥454） | $90（¥636） |
| 专家权重闪存 128 GB，HBF 推算价 | $128（¥909） | $320（¥2,272） | $576（¥4,090） |
| 专家权重闪存 256 GB，HBF Grade-1 最小堆栈 | $256（¥1,818） | $640（¥4,544） | $1,152（¥8,179） |
| 每增加 16 GB 系统 DRAM（若方案要求扩容） | $192（¥1,363） | $320（¥2,272） | $448（¥3,181） |

**读法**：
- 若闪存层用**普通 NAND / 现有 PCIe 5.0 NVMe**（只是多占约 128–256 GB 容量，或在 Gen4 基础上小幅升到 Gen5），闪存子项增量约 **¥100–650**，可以落在「几百元」以内。
- 若改用 **HBF 堆栈**，仅闪存子项就要 **¥900–8,000**，与「几百元」的目标不在一个量级。
- **3D-PIM 的 4 GB DRAM 位成本单项就是 ¥340–1,140**（还没算逻辑 die 与混合键合），在基准情景下已经吃掉或超出「几百元」的预算。
- 方案若要求**增加系统 DRAM 容量**，每 16 GB 约 ¥1,400–3,200，这是整套方案里最贵的单位成本项。

---

## 7. 周期判断：峰值与回落

- **DRAM**：季度涨幅在 2Q26 见顶（LPDDR5X +78~83%），3Q26 收敛到 +8~13%，4Q26 进一步收敛到 +0~5%（移动 DRAM），但**价格停留在历史高位、没有回落**。1Q27 新年度议价可能再涨（LPDDR5X +13~18%）。TrendForce 认为 2027 年 DRAM 缺口继续扩大，美银认为 2027 年持平或小幅回调。**回落窗口在 2028 年**（美银：DRAM −8%）。BOM 不宜按 2025 年的约 $3/GB 计算，也不宜按原厂颗粒现货峰值 $30/GB 计算。
- **NAND**：晶圆端 2H26 已现顶部特征（7–8 月持平，10 月现货小跌），合约端 4Q26 仍补涨 +15~20%。**2H27 起转宽松、价格下行**（TrendForce），美银预计 2028 年 −14%。NAND 是本方案里最可能先降价的品类。
- **HBM / 堆叠 DRAM**：**与消费类走势相反，2027 年继续大涨**（混合 ASP +121%，HBM4 单堆栈约 $600 → $1,300）。以 HBM 为锚定价的 HBF，以及工艺相近的 3D-PIM，在 2027 年会受到上涨压力，而不是回落。

---

## 8. 未找到 / 数据缺口

- TrendForce 移动 DRAM 合约价（LPDDR5X 8/12/16GB）与 NAND 晶圆合约价（TLC 1Tb / 512Gb、QLC 1Tb）的**绝对值**：在付费墙后，**未找到**公开数值。本文用 CFM 渠道价、TrendForce 现货价和链式推算替代。
- LPDDR6 合约价 / 现货价：**未找到**，只有「贵约 20%」的传闻。
- PCIe 6.0 客户端 SSD 价格：**未找到**。只有慧荣「2027 年底平台」和群联「2027 年中量产、企业级优先」的时间表。
- HBF 官方 $/GB 或堆栈价：**未找到**，只有「与 HBM 同价位、容量 8–16 倍」的说法。端侧 HBF 无产品、无价格。
- 3D-PIM（DRAM-on-logic）的市场价：**未找到**，本文以 HBM $/GB 作代理。
- 首尔经济日报 HBM4 $600 → $1,300 的原文（en.sedaily.com）抓取失败，采用 Silicon Analysts 的转述（PM-S24），置信度按中处理。

---

## 9. 来源

| 编号 | 来源 | 日期 | 链接 |
|---|---|---|---|
| PM-S1 | TrendForce 新闻稿：*AI Server Demand Sustains Memory Contract Price Increases in 4Q26…*（含 3Q26E/4Q26F 表图：通用 DRAM 3Q +13~18% / 4Q +10~15%；HBM 混合 +8~13% / +15~20%；NAND +18~23% / +15~20%） | 2026-09-30 | https://www.trendforce.com/presscenter/news/20260930-13258.html ；表图 https://img.trendforce.com/EDM/2026/09/20260930_140539_3.jpg |
| PM-S2 | TrendForce 新闻稿：*AI Server Demand Continues to Support Memory Prices in 3Q26…* | 2026-07-03 | https://www.trendforce.com/presscenter/news/20260703-13134.html |
| PM-S3 | TrendForce 新闻稿：2Q26 移动 DRAM 合约价（LPDDR4X ≥ +70~75%，LPDDR5X +78~83%） | 2026-05-14 | https://www.trendforce.com/presscenter/news/20260514-13044.html |
| PM-S4 | TrendForce 报告摘要：*Mobile DRAM Contract Price 3Q26*（+8~13%） | 2026-08-03 | https://www.trendforce.com/research/download/RP260803NC |
| PM-S5 | Tiger Brokers 转述高盛 *Korea Technology: Memory Price Tracker*（4Q26 分品类：PC +13~18%、服务器 +10~15%、移动 +0~5%、eSSD +23~28%；1Q27：LPDDR5X +13~18%；9 月 DDR5 8GB 合约 $133 持平；DDR5 现货较合约溢价约 20%） | 2026-10-01（高盛 2026-09-30） | https://www.itiger.com/news/1111393487 |
| PM-S6 | TrendForce DRAM 价格页快照（DDR5/DDR4 现货 2026-10-14；DRAM 合约 2H Aug；模组现货 2026-10-05） | 2026-10-14 | https://www.trendforce.com/price/dram/dram_spot |
| PM-S7 | MemoryMarket（CFM 闪存市场，原 en.chinaflashmarket.com）价格中心快照：晶圆、DDR、SODIMM、UDIMM、LPDDR、OEM/渠道 SSD | 2026-10-13/14 | https://www.memorymarket.com/price |
| PM-S8 | memoryindex.io LPDDR 追踪（转录 DRAMeXchange 移动 DRAM 现货盘；聚合站） | 2026-09-09 | https://memoryindex.io/lpddr-prices |
| PM-S9 | wccftech：*Mobile DRAM Prices Expected To Increase By ~100% QoQ… LTAs… As High As $21/GB*（SemiAnalysis 约 $10/GB；2Q26 插值 $19.3–19.8；LTA $7.8–21/GB） | 2026-05-04 | https://wccftech.com/mobile-dram-prices-expected-to-increase-by-100-quarter-over-quarter-as-long-term-agreements-now-getting-signed-at-prices-as-high-as-21-gb/ |
| PM-S10 | Counterpoint：*Reshuffling the BoM: Component Cost Dynamics Amid Memory Price Spikes*（2Q26 手机内存 +80% QoQ 以上；中端机内存占 BOM 40%） | 2026-07-29 | https://counterpointresearch.com/en/insights/reshuffling-the-bom-componentcost-dynamics-amid-memory-price-spikes |
| PM-S11 | TrendForce NAND 价格页快照（512Gb TLC 晶圆现货 2026-10-05；PC OEM SSD 合约 3Q26；SSD 街价 2026-09-24） | 2026-10-14 | https://www.trendforce.com/price/flash/wafer_spot |
| PM-S12 | TrendForce 报告摘要：*NAND Flash Wafer Contract Price Aug. 2026* / *Jul. 2026*（TLC 分化、QLC 严格持平） | 2026-08-31 / 2026-07-31 | https://www.trendforce.com/research/download/RP260831VN ；https://www.trendforce.com/research/download/RP260731FS |
| PM-S13 | Tom's Hardware（Yahoo 转载）：NAND 晶圆单月 +25%（DigiTimes 转述 CFM：1Tb TLC $25） | 2026-03-05 | https://finance.yahoo.com/news/spiralling-memory-spot-prices-could-124227209.html |
| PM-S14 | TweakTown：群联 CEO 称 TLC 1Tb 从 $4.80 涨到 $10.70 | 2025-11-11 | https://www.tweaktown.com/news/108804/nand-flash-pricing-for-ssds-has-doubled-in-six-months-2026-capacity-already-sold-out/index.html |
| PM-S15 | MemoryMarket 1Tb QLC 历史价格页 | 2026-10-13 | https://www.memorymarket.com/price/in/100257 |
| PM-S16 | TrendForce 新闻稿：*Diverging Memory Market Outlook in 2027…*（DRAM 紧、NAND 2H27 转宽松） | 2026-07-30 | https://www.trendforce.com/presscenter/news/20260730-13158.html |
| PM-S17 | TrendForce 新闻稿：*Memory Prices Soar; DRAM and NAND Flash to Account for 68% of Major CSP CapEx in 2027*（LTA 价格上限；2027 年 HBM 合约价 +70~140%） | 2026-08-25 | https://www.trendforce.com/presscenter/news/20260825-13198.html |
| PM-S18 | TrendForce 新闻稿：*Long-Term Agreements Cap Price Increases; Server DRAM … 13-18% QoQ in 3Q26* | 2026-07-09 | https://www.trendforce.com/presscenter/news/20260709-13140.html |
| PM-S19 | Kaohoon International 转述美银（4Q26 DRAM +8% / NAND +3%；2027 年持平或小幅回调；2028 年 DRAM −8% / NAND −14%） | 2026-08-10 | https://www.kaohooninternational.com/markets/588276 |
| PM-S20 | Tom's Hardware：*SSD price tracking 2026 — Lowest price on every M.2 SSD*（PCIe 5 表） | 2026-10-14 更新 | https://www.tomshardware.com/pc-components/ssds/ssd-price-tracking-2026-lowest-price-on-every-m-2-ssd |
| PM-S21 | igor'sLAB：慧荣 PCIe 6.0 客户端 SSD 平台提前到 2027 年底（转述 Tom's Hardware 专访 Nelson Duann） | 2026-06-20 | https://www.igorslab.de/en/silicon-motion-pcie-6-0-client-ssds-late-2027-nvidia/ |
| PM-S22 | igor'sLAB：群联 X3 PCIe 6.0 SSD 先进数据中心（2026-12 送样，2027 年中量产） | 2026-06-07 | https://www.igorslab.de/phison-x3-pcie-6-0-ssds-gehen-zuerst-ins-rechenzentrum-nicht-in-den-gaming-pc/ |
| PM-S23 | TrendForce 新闻稿：*HBM Supply Constraints Persist, 2027 Price Outlook Revised Upward with Blended ASP Forecast to Rise 121% YoY* | 2026-09-29 | https://www.trendforce.com/presscenter/news/20260929-13255.html |
| PM-S24 | Silicon Analysts：*TrendForce Lifts 2027 HBM ASP Forecast to +121%; HBM4 Stack Seen Doubling to ~$1,300*（引首尔经济日报：HBM4 12-Hi 36GB 2026 年约 $600 → 2027 年约 $1,300） | 2026-10-01 | https://siliconanalysts.com/market/trendforce-lifts-2027-hbm-asp-forecast-to-121-hbm4-stack-seen-doubling-to-1-300-2026-10-01 |
| PM-S25 | TweakTown（转述朝鲜日报）：SK 海力士 HBM4 12-Hi 对 NVIDIA 约 $500，较 HBM3E（$300 区间）贵约 70% | 2025-08-06 | https://www.tweaktown.com/news/106826/sk-hynix-drastically-raises-next-gen-hbm4-supply-price-in-a-war-of-nerves-with-nvidia/index.html |
| PM-S26 | TrendForce News：三星、SK 海力士 2026 年 HBM3E 涨价约 20% | 2025-12-24 | https://www.trendforce.com/news/2025/12/24/news-samsung-sk-hynix-reportedly-plan-20-hbm3e-price-hike-for-2026/ |
| PM-S27 | NAND Research：*High Bandwidth Flash: Bridging the Gap Between Expensive HBM & Flash Memory*（HBM 约 $20–30/GB；HBF 同价 8–16 倍容量；2026 年底试产线，2027 年商用） | 2026-08-23 | https://nand-research.com/high-bandwidth-flash-bridging-the-gap-between-expensive-hbm-flash-memory/ |
| PM-S28 | Tom's Hardware：*Hot Chips 2026: High Bandwidth Flash promises massive bandwidth and capacity, but its usability is extremely limited*（Grade 1/2/3 规格；OXMIQ 成本与功耗对等下容量 14.2 倍、带宽 0.6 倍） | 2026-08-26 | https://www.tomshardware.com/pc-components/ssds/hot-chips-2026-high-bandwidth-flash-promises-massive-bandwidth-and-capacity-but-its-usability-is-extremely-limited-new-memory-format-strikes-a-balance-between-hbm-and-nand-flash |
| PM-S29 | Chipstrat：*High Bandwidth Flash: The Full Report*（每 GB 成本约为 HBM 的 1/10；封装主导成本） | 2026-07-07 | https://newsletter.chipstrat.com/p/high-bandwidth-flash-the-full-report |
| PM-S30 | DigiTimes：*Sandisk says HBF can match HBM bandwidth with up to 16x the capacity*（similar cost） | 2026-09-02 | https://www.digitimes.com/news/a20260902VL225/hbm-bandwidth-capacity-technology-flash.html |
| PM-S31 | wccftech：*LPDDR6 RAM rumored to be 20 percent more expensive than LPDDR5X RAM* | 2026-01-02 | https://wccftech.com/lpddr6-ram-rumored-to-be-20-percent-more-expensive-than-lpddr5x-ram/amp/ |
| PM-S32 | 本项目本地调研：内存容量挤压（移动 DRAM 2024–2026 价格）与 UFS-HBF 增强（HBF 规格、时间线） | 2026 | [`../../memory-capacity-crunch-CN.md`](../../memory-capacity-crunch-CN.md) ；[`../../ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md`](../../ufs-hbf-enhancement/ufs-hbf-enhancement-CN.md) |
| PM-S33 | PCSP 博客：*DDR4 vs DDR5 Memory Pricing Trends*（转述 Newegg Insider：32GB DDR5-6000 套条 2025 年中约 $80 → 2026 年初约 $432；二手来源，仅作 2025 年基线参照） | 2025-10-10 首发，2026-10-10 复核 | https://pcserverandparts.com/blog/ddr4-vs-ddr5-memory-pricing-trends-2025/ |

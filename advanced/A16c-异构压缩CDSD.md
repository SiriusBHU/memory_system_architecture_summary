# A16c · 异构压缩 CDSD（按数据类异构选压：匿名 / 文件 / KV / 设备缓冲）

> **一句话定位**：[A06](../foundations/A06-压缩与换页.md) 把压缩讲成"用 CPU 换内存"的单一手段。本篇接着问：当内存里挤着**性质迥异**的数据——匿名页、文件页、模型 KV cache、设备缓冲——还用**一把算法压所有页**就太亏了。**异构压缩**＝按数据类（及其冷热与延迟预算）**分别选压缩器/强度**；**CDSD** 是终端语境下的一种 LZ4 家族压缩变体实例（规格待核实），本篇把它放进"异构压缩"这张更大的图里。
>
> 📍 **对应总览**：[00 总览](../foundations/00-内存系统总览.md) 的「2B 物理与回收侧 · 换页」格 + 「第 4 层 · 存储层级」——压缩是终端**最靠近 CPU 的换出层**，异构压缩是把这一层切得更细。
> 🧭 **阅读前置**：先读 [A06 压缩与换页](../foundations/A06-压缩与换页.md)（zram/zswap、zsmalloc 基础，本篇不重复）、[A15c 移动端分层内存与压缩前沿](A15c-移动端分层内存与内存压缩前沿.md)（zram 内部多级压缩，本篇承接其 `MULTI_COMP` 伏笔）；冷热信号供给见 [A16a LRU 主动扫描](A16a-LRU主动扫描.md)；KV 专用压缩与 [A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md) 互为表里。
> 🌡️ **演进分级**：**演进厚 ⚡**——压缩器本体稳定，但**多算法分级、按数据类选压、KV 专用压缩、压缩下沉硬件**几条线在快速动；**重点在 §3 机制本体、§5 KV 专用压缩 与 §6 趋势**。

---

> **⚠️ 本篇立场（先读）**：本篇讨论的「按数据类异构选压 + 端侧 KV 专用压缩（CDSD）」是**基于学界研究与第一性原理的设计探讨与可行性分析**，**业界（Android / iOS / HarmonyOS）目前并未落地此方案**。全篇严格区分**① 已有机制与学术工作**（事实，如 zram `MULTI_COMP`、KIVI/H2O 等 KV 压缩论文）与**② 本篇设想**（非现状，标「设想 / 推测 / 待核实」）；**CDSD 公开无定义，按 LZ4 家族变体推演、规格待核实，不臆造**。核心问题：顺着第一性原理与学界，这样做**是否成立、可行性多大**。

## 1. 定位：它在地图上的哪一格

[A06](../foundations/A06-压缩与换页.md) 的 zram 是终端扩容主力：把回收挑中的匿名页压进 RAM 内的压缩块设备，**默认不落盘**。[A15c](A15c-移动端分层内存与内存压缩前沿.md) 进一步指出，今天的 zram 已是"未压 → lz4 → zstd → writeback"的**微型分层**。

本篇把镜头对准这条链里**"选哪个压缩器、用多大强度"**这一格，并把它从"按冷热分级"推进到"**按数据类异构**"：

> **不同数据的可压性与延迟预算天差地别**——把它们一视同仁地交给同一个 lz4，要么压不动（白烧 CPU），要么压太慢（拖吞吐）。异构压缩＝**让压缩器匹配数据**。

## 2. 负载动因：增长把"压缩"顶成主力，又把"单算法"顶到极限

本篇属于 A16「**增长**」轴。按 [A16 总论](A16-前沿-Agent时代内存负载.md) 的终端立场说清动因：

终端的增长是**双重叠加**的（A16 三特征里的「增长」）：

1. **Agent 侧增长**：模型权重 + KV cache 体量远超 LPDDR，且 **KV cache 常驻 NPU 可访问的 dma-buf / 设备内存**（见 [A16f](A16f-端侧KV-Cache管理方案.md)、[A09](../foundations/A09-设备内存全景.md)）；
2. **传统侧增长**：app 数量、page cache、相机/视频缓冲也在涨。

而终端**没有磁盘 swap 这条退路**（[A15c §4](A15c-移动端分层内存与内存压缩前沿.md)：闪存寿命让 Android 默认不落盘）。两条夹击的结论是：

> **压缩几乎是终端唯一的"无损扩容"手段**——既然躲不开，就得把它做到极致。

而"做到极致"恰恰撞上单算法的天花板：内存里的数据**不再同质**。一把 lz4 压所有页，在 Agent 负载下三处不划算——

- **设备缓冲基本不可压**：GPU 纹理、已编码的视频/相机帧（[A09](../foundations/A09-设备内存全景.md)）本就是压缩态，再压是纯烧 CPU；
- **KV cache 用通用无损压缩器压不动**：它是 FP16/BF16 浮点张量，**熵高、通用 LZ 类压缩比很差**，要省它得换一套思路（§5）；
- **冷页值得用更强算法**：久未访问的匿名页用 zstd 重压更省（[A15c](A15c-移动端分层内存与内存压缩前沿.md) 已做），但热页又得用 lz4 求低延迟。

于是"**按数据类（+冷热 + 延迟预算）异构选压**"成了增长压力下的必然方向。CDSD 正是终端落这一步的一个实例。

> 一句话动因：**增长把压缩从"可选优化"顶成"主力扩容"；而数据的异构又把"单算法压一切"顶到极限——异构压缩是这两股力的交点。**

## 3. 机制本体：从"单算法"到"按数据类异构选压"

### 3.1 压缩器谱系：速度 ↔ 压缩比的连续谱

终端可用的无损压缩器是一条权衡谱（zram 支持的算法）：

| 算法 | 定位 | 解压延迟 | 压缩比 |
|---|---|---|---|
| `lzo` / `lzo-rle` | 老牌快压 | 极低 | 低 |
| **`lz4`** | 移动端事实默认，快压基准 | 极低（微秒级） | 中低 |
| `lz4hc` | LZ4 高压缩档 | 低（解压同 lz4） | 中 |
| **`zstd`** | 高可调，比/速兼顾 | 中 | 高（实测约 5:1 量级，随数据而异） |
| `deflate` / `842` | 通用 / 特定硬件 | 高 / 视实现 | 高 / 中 |

> `lz4` 与 `zstd` 是终端两端的代表：**热路径求低延迟用 lz4，冷数据求高比用 zstd**——这正是"按冷热异构"的两极。

### 3.2 zram 已经有的"异构"雏形：MULTI_COMP（按冷热）

[A15c](A15c-移动端分层内存与内存压缩前沿.md) 讲过、这里据 zram 文档坐实接口：`CONFIG_ZRAM_MULTI_COMP` 让 zram 配 **1 主 + 至多 3 次算法**，对冷的压缩页用更强算法**重压缩（recompress）**：

- 选主算法：`/sys/block/zramX/comp_algorithm`（`lzo/lz4/zstd/...`，初始化后不可改）；
- 配次算法与优先级：`echo 'algo=zstd priority=1' > /sys/block/zramX/recomp_algorithm`；
- 触发重压缩：`echo 'type=idle priority=1' > /sys/block/zramX/recompress`（按 `type=idle/huge/huge_idle`、`threshold=`、`max_pages=` 限定范围）；
- 调算法参数：`echo 'algo=zstd level=8 dict=/etc/dictionary' > /sys/block/zramX/algorithm_params`（**压缩级别 + 预训练字典**）。

这套机制的"异构"维度是 **冷热**：温页 lz4、冷页 zstd。但它仍是**对所有数据一视同仁地按冷热分级**，没有"按数据类型"这一维。

### 3.3 真正的异构：把"数据类型"加进选压维度

异构压缩主张在冷热之外再加一维——**数据语义**：

| 数据类 | 典型来源 | 可压性 | 选压策略 |
|---|---|---|---|
| 匿名页（堆/栈） | app 运行时 | 中（含指针、零页、文本混合） | 主路 lz4，冷页 zstd 重压（现状） |
| 文件页（page cache） | 代码、资源 | 视内容（文本高、媒体低） | 多由文件系统侧处理；可压者纳入 |
| **KV cache** | 端侧 LLM 推理 | **通用无损压缩比差**（高熵浮点） | **走专用有损压缩**（量化/淘汰，§5） |
| **设备缓冲** | GPU 纹理 / 视频帧（dma-buf） | **基本不可压**（已编码） | **不压**，避免白烧 CPU；且多 pinned 够不着（[A09](../foundations/A09-设备内存全景.md)） |

要点：**"压不压、用什么压"应由数据类型先分流，再在类内按冷热细分**。这要求压缩层能拿到"这页是什么"的语义——而这正是终端今天的短板（匿名/文件可分，KV 与设备缓冲常在 [A09](../foundations/A09-设备内存全景.md) 的 dma-buf 里、走不进普通 zram 路径，详见 §6）。

### 3.4 CDSD：终端的一种 LZ4 家族压缩变体（规格待核实）

按本系列的口径，**CDSD 是终端语境下对 LZ4 家族压缩的一种变体**，意在拿到"**接近 lz4 的低解压延迟 + 高于 lz4 的压缩比**"的折中点，用作异构压缩里"匿名/通用页"这一类的主压器。

诚实声明 sourcing：**公开检索未见 "CDSD" 这一缩写的权威定义**，其确切展开、算法细节、与 lz4hc/zstd 的定量差异**待据一手资料核实**。可作公开旁证的是学术界确有"**基于改进 LZ4 的数据压缩器件**"一脉（如 IEEE 的 *Data Compression Device Based on Modified LZ4 Algorithm*），思路一致——在 LZ4 框架上改 match/熵编码以提比，同时守住低延迟。本篇据此**只讲方向、不编规格**，CDSD 的具体参数留待一手确认。

## 4. 历史：压缩从"一个算法"长出"多算法 + 按类"

```
compcache（早期 RAM 压缩）
   ▼ zram/zswap 分立：单一压缩算法（lzo→后默认 lz4/zstd 因机型而异）
单算法压一切
   ▼ CONFIG_ZRAM_MULTI_COMP（kernel 6.6 / Android GKI 6.6）
按【冷热】异构：温页 lz4 / 冷页 zstd 重压（recompress）
   ▼ 趋势（本篇主张 + KV 专用压缩兴起）
按【数据类】异构：匿名/文件/KV/设备缓冲分流选压
   + KV 走专用【有损】压缩（量化/淘汰，§5）
   + 压缩下沉硬件 IP（→ A16d 边际建模 / A16g·A16i 硬件）
```

主线：**压缩的"选择维度"在变多**——先有"压不压"，再有"按冷热选强度"（MULTI_COMP 落地），下一步是"按数据语义分流"，并在 KV 这类特殊数据上**跳出无损压缩**另起一套。

## 5. 为什么 KV cache 要"专用压缩"：有损的另一套世界 ← 重点

zram 的压缩是**无损**的（解压后逐字节还原）。但 KV cache 是 LLM 推理的中间张量，**容许有损**——只要模型输出质量不塌，就能用更激进的手段省内存。学界已分出几条成熟路线（详见 [A16f](A16f-端侧KV-Cache管理方案.md)，此处只给压缩视角）：

- **量化（降精度，保留所有 token）**：
  - **KIVI**——免调参的非对称 2-bit 量化，**key 按通道、value 按 token** 量化，几乎不掉质量地把含权重的峰值内存降到约 1/2.6（[KIVI, arXiv 2402.02750 / ICML 2024](https://arxiv.org/abs/2402.02750)）；
  - **KVQuant**——结合 per-channel key、pre-RoPE key 量化与"稠密+稀疏"离群值分解，把位宽压到 sub-4bit，面向超长上下文。
- **淘汰（降 token 数）**：
  - **H2O（Heavy-Hitter Oracle）**——少数 token 贡献大部分注意力质量，只保留"重击者"+近窗 token（[H2O, NeurIPS 2023](https://arxiv.org/abs/2306.14048)）；
  - **StreamingLLM**——基于"注意力汇（attention sink）"只保留少量初始 token + 滑窗；**SnapKV / Ada-KV** 等按注意力选择性保留。
- **低秩 / 合并**：把 KV 投影到低秩子空间或合并相似 token。

> **术语警示（异构压缩最易混的一点）**：**KV "压缩" 多是有损（量化/淘汰），zram 压缩是无损**——二者机制、误差语义、回滚方式完全不同，**绝不可混为一谈**。异构压缩的完整图景是：**无损通用压缩器（lz4/zstd/CDSD）服务匿名/文件页，有损 KV 专用方案服务 KV cache，设备缓冲基本不压**。综述见 [KV Cache Compression: A Review (arXiv 2508.06297)](https://arxiv.org/abs/2508.06297)。

## 6. 趋势与未解问题 ← 本篇重心

- **自适应按数据类 + 能耗预算选压**："温页 lz4、冷页 zstd"是粗近似；理想是**按页的数据类、冷热、当前能耗预算联合选算法/强度**。但"何时值得多花 CPU 去重压一页"在续航约束下仍无成熟策略——这正是 [A16d 压缩 IP 边际建模](A16d-压缩IP边际建模.md) 要解的问题。
- **压缩下沉为硬件 IP**：把压缩/解压从 CPU 挪到专用 IP（内存控制器侧或近内存），对软件透明地放大有效容量。产品化程度参差，标准缺失（[A06 §6](../foundations/A06-压缩与换页.md) 同列），硬件载体见 [A16g PIM](A16g-DRAM-PIM异构协同管理.md) / [A16i UFS-HBF](A16i-端侧UFS-HBF增强.md)。
- **KV 专用压缩与系统层 zram 如何协作**：端侧 KV 多在 [A09](../foundations/A09-设备内存全景.md) 的 dma-buf / 设备内存里，**走不进普通 zram 路径**；于是 KV 的量化/淘汰只能在**推理框架层**做，系统压缩层够不着它。如何让系统层与框架层在内存预算上协同（谁先让步、如何记账），目前基本空白。
- **CDSD 规格待核实**：其展开、参数、相对 lz4hc/zstd 的定量收益需一手确认；本篇只立方向。
- **设备缓冲的"可压性标注"**：要做到"不压不可压的页"，压缩层需要"这页是已编码媒体"的语义——这要 dma-buf / gralloc 把可压性元数据透出来，目前没有这条通路。

## 7. 配合与依赖

| 配合 | 方向与含义 | 去哪篇细看 |
|---|---|---|
| 压缩基础 ← zram/zswap | 本篇是其"选压器"一格的细化 | [A06](../foundations/A06-压缩与换页.md) |
| 多级压缩 ← MULTI_COMP | 按冷热重压缩的现成接口 | **[A15c](A15c-移动端分层内存与内存压缩前沿.md)** |
| 冷热信号 ← 主动扫描 | 谁冷谁热决定用强算法重压哪页 | **[A16a](A16a-LRU主动扫描.md)、[A05](../foundations/A05-冷热识别的演进.md)** |
| 选压决策 → 边际建模 | 在延迟/吞吐预算内选压缩量与比 | **[A16d](A16d-压缩IP边际建模.md)** |
| KV 有损压缩 ↔ 本篇无损压缩 | 两套世界，按数据类分流 | **[A16f](A16f-端侧KV-Cache管理方案.md)** |
| 设备缓冲 ✗ 压缩 🔗 | dma-buf/纹理多不可压且 pinned、够不着 | [A09](../foundations/A09-设备内存全景.md) |
| 硬件压缩 IP | 压缩下沉到近内存/存储 | [A16g](A16g-DRAM-PIM异构协同管理.md)、[A16i](A16i-端侧UFS-HBF增强.md) |

## 8. 实测 / 观测点

- `cat /sys/block/zram0/comp_algorithm`：可用与当选主算法（方括号为当选）；`recomp_algorithm`：次算法与优先级；
- `echo 'algo=zstd level=8' > /sys/block/zram0/algorithm_params`：调级别/字典；
- `echo 'type=idle priority=1' > /sys/block/zram0/recompress`：对 idle 页重压缩（受 `threshold`/`max_pages` 限定）；
- `cat /sys/block/zram0/mm_stat`：原始 vs 压缩字节、压缩比、`same_pages`（零页/同页）——看不同算法的实际收益；
- KV 压缩在**推理框架层**观测（量化位宽、保留 token 比），不在 zram sysfs（[A16f](A16f-端侧KV-Cache管理方案.md)）；
- 度量口径见 [A13](../foundations/A13-内存度量与排障.md)（SwapPss 等）。

## 9. 来源与延伸阅读

**压缩器与 zram 多级压缩**
- [zram: Compressed RAM-based block devices (kernel.org)](https://docs.kernel.org/admin-guide/blockdev/zram.html) —— 支持算法（lzo/lzo-rle/lz4/lz4hc/zstd/deflate/842）、`comp_algorithm`/`recomp_algorithm`/`recompress`/`algorithm_params`、`CONFIG_ZRAM_MULTI_COMP`
- [Android Kernel release notes (AOSP)](https://source.android.com/docs/core/architecture/kernel/release-notes) —— `CONFIG_ZRAM_MULTI_COMP` 入 kernel 6.6
- [Comparison of Compression Algorithms (LinuxReviews)](https://linuxreviews.org/Comparison_of_Compression_Algorithms)、[The Role of Compression Algorithms in ZRAM](https://hamradio.my/2025/01/the-role-of-compression-algorithms-in-zram/) —— lz4/zstd/lzo 速度与比的工程对比（二手旁证）

**CDSD 的公开旁证（缩写本身待核实）**
- [Data Compression Device Based on Modified LZ4 Algorithm (IEEE Xplore)](https://ieeexplore.ieee.org/document/8306366/) —— "基于改进 LZ4 的数据压缩器件"，与 CDSD"LZ4 家族变体"思路一致的公开同类

**KV cache 专用（有损）压缩**
- [KV Cache Compression for Inference Efficiency in LLMs: A Review (arXiv 2508.06297)](https://arxiv.org/abs/2508.06297) —— 量化/淘汰/低秩三类综述
- [KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache (arXiv 2402.02750, ICML 2024)](https://arxiv.org/abs/2402.02750)
- [H2O: Heavy-Hitter Oracle (arXiv 2306.14048, NeurIPS 2023)](https://arxiv.org/abs/2306.14048)
- StreamingLLM（注意力汇）、KVQuant（sub-4bit 长上下文）、SnapKV / Ada-KV（注意力选择性保留）——见上述综述索引

**承接 / 相邻篇**
- [A06 压缩与换页](../foundations/A06-压缩与换页.md)、[A15c 移动端分层内存与内存压缩前沿](A15c-移动端分层内存与内存压缩前沿.md)、[A16a LRU 主动扫描](A16a-LRU主动扫描.md)、[A16d 压缩 IP 边际建模](A16d-压缩IP边际建模.md)、[A16f 端侧 KV Cache 管理](A16f-端侧KV-Cache管理方案.md)、[A09 设备内存全景](../foundations/A09-设备内存全景.md)

> **待核实 / 待补**：**CDSD 的确切展开、算法细节与相对 lz4hc/zstd 的定量收益**（公开无此缩写，待一手）；Android 各厂商 GKI 默认主算法与 disksize 占比（lz4/zstd 因机型而异，[A06](../foundations/A06-压缩与换页.md) 同列）；端侧 KV 专用压缩（KIVI/H2O 等）在量产机的实际启用与所用方案；KV 有损压缩与系统层无损压缩在内存预算上的协同机制（目前空白）；dma-buf/gralloc 是否能透出"可压性"元数据以避免压不可压的设备缓冲；HarmonyOS 换出后端是否引入多算法/按类压缩（[A06](../foundations/A06-压缩与换页.md) 同列待补）。

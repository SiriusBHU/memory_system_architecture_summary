# UFS 5.0：为端侧 AI 时代倍增存储管道

> **范围**：梳理从 UFS 3.1/4.0 到 UFS 5.0 的演进，聚焦 M-PHY 6.0 带宽翻倍、供电完整性改进、内联哈希数据保护，以及闪存存储从被动仓库向主动 AI 数据管道的角色转变。
>
> **方法**：交叉参照 JEDEC JESD220H / JESD223G 规范（2026 年 2 月发布）、MIPI Alliance M-PHY 6.0 和 UniPro 3.0 规范、三星与铠侠 UFS 5.0 产品发布，以及独立技术分析。所有带宽数据按 JEDEC 方法使用每通道 HS-Gear 速率并扣除协议开销。

---

## 1. 问题背景

端侧 AI 正将移动闪存存储从被动数据仓库转变为实时数据管道。大语言模型（量化精度下 7B-13B 参数）在设备上占用 4-14 GB；检索增强生成（RAG）数据库额外增加数 GB 的向量嵌入。这些负载要求持续的顺序读取以供给 DRAM 和神经处理单元（NPU），制造了新的瓶颈：存储到内存的带宽。UFS 4.0 顺序读取峰值约 4.2 GB/s（HS-G5，2 通道），已无法跟上节奏。以 UFS 4.0 速率将 7B 模型加载到 LPDDR 需要超过 3 秒——这一可感知的延迟打破了实时 AI 交互的幻觉。与此同时，AI 负载产生持续的读写流量（模型切换、缓存管理、RAG 检索），对吞吐量和功耗效率均构成压力。存储接口曾为应用启动和媒体播放而设计，如今必须扩展以匹配 AI 驱动的带宽需求。

---

## 2. 问题与证据

### 2.1 顺序带宽天花板

| 证据 | 详情 |
|------|------|
| UFS 4.0 峰值顺序读取 | ~4.2 GB/s（HS-G5，2 通道，23.2 Gbps/通道）（[Beebom](https://gadgets.beebom.com/guides/ufs-5-0-explained)） |
| UFS 4.1 峰值顺序读取 | ~5.8 GB/s（优化 HS-G5 实现）（[Smartprix](https://www.smartprix.com/bytes/ufs-5-0-vs-ufs-4-1-4-0-the-biggest-smartphone-storage-upgrade-explained/)） |
| AI 模型加载延迟 | 7B 量化模型（~4 GB）：UFS 4.0 下约 1 秒；13B 模型（~8 GB）：约 2 秒——勉强可接受但无并发 RAG/缓存 I/O 余量 |
| UFS 5.0 目标 | 10.8 GB/s 顺序读写（HS-G6，2 通道，46.6 Gbps/通道）（[JEDEC](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage)） |

### 2.2 AI 负载下的功耗效率

移动 AI 负载产生持续的 I/O 突发，而非存储历来优化的短事务模式。UFS 4.0 的单一供电域将 PHY 噪声耦合至 NAND 控制器，且接口层缺乏时钟门控意味着空闲通道仍消耗功率。三星 UFS 5.0 实现通过时钟门控、多电压技术和专用 PHY 供电轨实现了 40%+ 的功耗效率提升（[Samsung Newsroom](https://news.samsung.com/global/samsung-unveils-industrys-fastest-ufs-5-0-solution-for-next-gen-on-device-ai-applications)）。

### 2.3 更高数据速率下的信号完整性

每通道速率从 23.2 Gbps（HS-G5）翻倍至 46.6 Gbps（HS-G6），将 M-PHY 链路推入通道损耗、串扰和码间干扰（ISI）显著的区间。如无均衡，误码率将不可接受。UFS 5.0 在 M-PHY 6.0 规范中强制要求集成链路均衡，在接收端主动补偿信号衰减——这一特性在 UFS 4.0 中不存在（[TechPowerUp](https://www.techpowerup.com/341645/jedec-ufs-5-0-standard-to-deliver-sequential-performance-up-to-10-8-gb-s)）。

### 2.4 AI 产物的数据完整性

AI 模型权重和 RAG 向量数据库是高价值、对损坏敏感的数据。量化权重张量中的单个比特翻转可导致级联推理错误。UFS 4.0 依赖 NAND 控制器的内部 ECC，但在存储到主机的数据路径上没有内联完整性检查。UFS 5.0 引入内联哈希，直接在存储路径内执行数据完整性验证，更快检测损坏或篡改（[JEDEC](https://www.jedec.org/news/pressreleases/jedec%C2%AE-announces-updates-universal-flash-storage-ufs-and-memory-interface-0)）。

---

## 3. 架构对比：UFS 4.0 vs. UFS 5.0

### UFS 4.0（基线）

```
+----------------------------------------------------------+
|                  应用处理器 (SoC)                          |
|  +----------------------------------------------------+  |
|  |  UFS 主控制器 (UFSHCI 4.x)                          |  |
|  |  - MIPI UniPro 2.0                                 |  |
|  |  - PHY + 控制器共用单一供电域                        |  |
|  |  - 无内联数据完整性检查                              |  |
|  +----------------------------------------------------+  |
|         |  Lane 0 (TX/RX)  |  Lane 1 (TX/RX)            |
|         |  HS-G5: 23.2 Gbps|  HS-G5: 23.2 Gbps          |
+---------+------------------+---------+-------------------+
          |                            |
          +----------+-----------------+
                     |
            MIPI M-PHY 5.0
            （无链路均衡）
                     |
          +----------+-----------------+
          |                            |
+---------+----------------------------+-----------+
|              UFS 4.0 设备                         |
|  +--------------------------------------------+  |
|  |  UFS 设备控制器                              |  |
|  |  - 命令队列（32 条命令）                      |  |
|  |  - 内部 ECC（NAND 级）                        |  |
|  |  - 无内联哈希                                |  |
|  |  - 单一供电轨                                |  |
|  +--------------------------------------------+  |
|  |  NAND 闪存阵列                               |  |
|  |  - V-NAND / BiCS FLASH                      |  |
|  |  - 最大 1 TB 容量                             |  |
|  +--------------------------------------------+  |
+---------------------------------------------------+

  峰值顺序读取：~4.2 GB/s（典型）/ 5.8 GB/s（UFS 4.1）
  峰值顺序写入：~2.8 GB/s（典型）
  封装：11 x 13 x 1.0 mm
  目标：智能手机、汽车、计算设备
```

### UFS 5.0（演进）

```
+----------------------------------------------------------+
|                  应用处理器 (SoC)                          |
|  +----------------------------------------------------+  |
|  |  UFS 主控制器 (UFSHCI 5.0)        JESD223G         |  |
|  |  - MIPI UniPro 3.0                                 |  |
|  |  - 内联哈希引擎（数据完整性）                        |  |
|  |  - 增强型命令队列                                    |  |
|  +----------------------------------------------------+  |
|         |  Lane 0 (TX/RX)  |  Lane 1 (TX/RX)            |
|         |  HS-G6: 46.6 Gbps|  HS-G6: 46.6 Gbps          |
+---------+------------------+---------+-------------------+
          |                            |
          +----------+-----------------+
                     |
            MIPI M-PHY 6.0
            + 集成链路均衡
            + 专用 PHY 供电轨
            （与控制器噪声隔离）
                     |
          +----------+-----------------+
          |                            |
+---------+----------------------------+-----------+
|              UFS 5.0 设备                JESD220H|
|  +--------------------------------------------+  |
|  |  UFS 设备控制器                              |  |
|  |  - 增强型命令队列                            |  |
|  |  - 内部 ECC（NAND 级）                       |  |
|  |  - 内联哈希（主机到设备路径）                  |  |
|  |  - 时钟门控（空闲通道省电）                    |  |
|  |  - 多电压供电管理                             |  |
|  |  - 专用 PHY 供电轨                            |  |
|  +--------------------------------------------+  |
|  |  NAND 闪存阵列                               |  |
|  |  - V-NAND 第 9 代 / BiCS FLASH 第 8 代       |  |
|  |  - 最大 1 TB 容量（可扩展）                    |  |
|  +--------------------------------------------+  |
+---------------------------------------------------+

  峰值顺序读取：~10.8 GB/s
  峰值顺序写入：~9.5 GB/s（三星实现）
  随机读取：相比 UFS 4.1 提升最高 5 倍
  封装：7.5 x 13 x 0.9 mm（三星，缩小 16.7%）
  向后兼容 UFS 4.x 硬件
  目标：智能手机、汽车、边缘 AI、游戏主机
```

### 数据流对比 — AI 模型加载

```
  UFS 4.0 路径（7B 模型，~4 GB）：
  NAND -> 设备控制器 -> M-PHY 5.0 (HS-G5) -> 主控制器 -> DRAM
         无内联检查           ~4.2 GB/s          ~1.0 秒

  UFS 5.0 路径（7B 模型，~4 GB）：
  NAND -> 设备控制器 -> M-PHY 6.0 (HS-G6) -> 内联哈希 -> 主控制器 -> DRAM
         链路均衡生效         ~10.8 GB/s   完整性OK      ~0.4 秒

  UFS 5.0 路径（13B 模型，~8 GB）：
  NAND -> 设备控制器 -> M-PHY 6.0 (HS-G6) -> 内联哈希 -> 主控制器 -> DRAM
                                ~10.8 GB/s                    ~0.75 秒
```

---

## 4. UFS 5.0 能解决什么 —— 不能解决什么

### 能解决

- **AI 模型加载速度**：10.8 GB/s 顺序读取在约 0.4 秒内加载 7B 量化模型（UFS 4.0 约 1 秒），实现多 Agent 和多模态 AI 的近乎即时模型切换。
- **持续 AI I/O**：带宽余量支持并发模型执行 + RAG 检索 + 缓存写入而不饱和存储链路。
- **AI 负载下的功耗**：40%+ 功耗效率提升（三星实现）意味着持续 AI I/O 不会过度消耗电池——对常驻 AI 助手至关重要。
- **AI 产物的数据完整性**：内联哈希在存储到主机路径上捕获比特错误，防止模型权重或嵌入向量损坏。
- **高速下的信号可靠性**：集成 M-PHY 6.0 链路均衡确保翻倍的数据速率不以可靠性换取吞吐量。
- **封装缩小**：三星的 7.5 x 13 x 0.9 mm 封装比 UFS 4.x 缩小 16.7%，释放板空间给更大电池或额外传感器。
- **平滑过渡**：向后兼容 UFS 4.x 硬件，降低 OEM 导入风险。

### 不能解决

- **计算存储**：UFS 5.0 不包含标准化的计算存储接口。存储设备仍是被动数据源；所有计算仍在 SoC 上完成。近存储处理（如解压缩、闪存内向量搜索）需要厂商私有扩展或未来标准修订。
- **AI 写放大下的 NAND 耐久性**：AI 负载（模型缓存、RAG 索引更新、交换）产生持续写入，加速 NAND 编程/擦除循环磨损。UFS 5.0 提升了接口带宽，但不解决闪存单元耐久性问题——这仍属 NAND 工艺范畴。
- **细粒度检索的随机 I/O**：尽管三星声称随机读取提升最高 5 倍，标准本身不强制规定随机 IOPS 下限。多次小随机读取的 RAG 负载可能仍受 NAND 访问延迟（而非接口）瓶颈。
- **多队列 / NVMe 级并行**：UFS 5.0 保留基于 SCSI 的命令模型，未采用 NVMe 的多队列架构，限制了在现代多核 SoC 上利用深度并行的能力。
- **超过 1 TB 的容量扩展**：当前 UFS 5.0 实现上限为 1 TB。随着端侧模型规模增长（多模态、视频生成），1 TB 可能不足。

---

## 5. 量化对比

| 指标 | UFS 3.1 | UFS 4.0 / 4.1 | UFS 5.0 | UFS 5.0 vs. 4.0 变化 |
|------|---------|---------------|---------|---------------------|
| JEDEC 规范发布 | 2020 | 2022 / 2024 | 2026 年 2 月（JESD220H） | — |
| PHY 层 | M-PHY 4.1 | M-PHY 5.0 | M-PHY 6.0 | +1 代 |
| 速率档 | HS-G4 | HS-G5 | HS-G6 | +1 档 |
| 每通道数据速率 | 11.6 Gbps | 23.2 Gbps | 46.6 Gbps | 2x |
| 通道数 | 2 | 2 | 2 | 相同 |
| 峰值顺序读取 | ~2.1 GB/s | ~4.2 GB/s (4.0) / ~5.8 GB/s (4.1) | ~10.8 GB/s | ~2.5x vs. 4.0 |
| 峰值顺序写入 | ~1.2 GB/s | ~2.8 GB/s | ~9.5 GB/s（三星） | ~3.4x vs. 4.0 |
| 随机读取提升 | 基线 | ~2x vs. 3.1 | 最高 5x vs. 4.1（三星） | 显著 |
| 链路均衡 | 无 | 无 | 有（集成） | 新增 |
| 内联哈希 | 无 | 无 | 有 | 新增 |
| 专用 PHY 供电轨 | 无 | 无 | 有 | 新增 |
| 功耗效率 vs. 前代 | 基线 | -46% vs. 3.1 | -40%+ vs. 4.1（三星） | 显著 |
| 协议层 | UniPro 1.8 | UniPro 2.0 | UniPro 3.0 | +1 代 |
| 主控制器规范 | UFSHCI 3.x | UFSHCI 4.x | UFSHCI 5.0 (JESD223G) | +1 代 |
| 最大容量（当前） | 512 GB | 1 TB | 1 TB（铠侠/三星样片） | 相同 |
| 封装尺寸（三星） | — | 11 x 13 x 1.0 mm | 7.5 x 13 x 0.9 mm | -16.7% |
| UFS 4.x 向后兼容 | — | — | 是 | 平滑过渡 |
| 首批硅片采样 | 成熟 | 成熟 | 铠侠：2026 年 2 月；三星：2026 Q4 量产 | 导入期 |

---

## 6. 一词总结

**倍增** —— UFS 5.0 将存储到处理器的管道容量倍增，以匹配 AI 负载的带宽胃口。

---

## 7. 开放问题

1. **计算存储时间线**：JEDEC 或行业联盟何时为 UFS 标准化计算存储接口？近存储向量搜索和解压缩可为 RAG 负载消除一次到 SoC 的往返。
2. **NVMe 趋同**：未来 UFS 修订版是否会采用 NVMe 的多队列命令模型，还是基于 SCSI 的架构将继续存在？8+ 核移动 SoC 可从更深的命令并行中获益。
3. **持续 AI 写入下的 NAND 耐久性**：UFS 5.0 的 9.5 GB/s 写入带宽可远比以往更激进地消耗 NAND P/E 循环。NAND 厂商将如何为 AI 密集型设备解决耐久性问题？
4. **超过 1 TB 的容量**：多模态 AI 模型和端侧视频生成可能需要 2-4 TB。UFS 何时突破 1 TB 上限？
5. **HS-G6 下的实际随机 IOPS**：三星声称随机读取提升 5 倍，但标准不强制规定 IOPS 下限。竞争实现是否能交付类似的随机性能，还是将因控制器和 NAND 差异而大幅波动？

---

## 8. 参考文献

1. JEDEC，"UFS 5.0 Is Coming: JEDEC Sets the Stage for the Next Leap in Flash Storage"，2025 年 10 月。[链接](https://www.jedec.org/news/pressreleases/ufs-50-coming-jedec%C2%AE-sets-stage-next-leap-flash-storage)
2. JEDEC，"JEDEC Announces Updates to Universal Flash Storage (UFS) and Memory Interface Standards"（JESD220H、JESD223G 发布），2026 年 2 月。[链接](https://www.jedec.org/news/pressreleases/jedec%C2%AE-announces-updates-universal-flash-storage-ufs-and-memory-interface-0)
3. VideoCardz，"JEDEC announces Universal Flash Storage (UFS) 5.0 with 10.8 GB/s sequential speed"。[链接](https://videocardz.com/newz/jedec-announces-universal-flash-storage-ufs-5-0-with-10-8-gb-s-sequential-speed)
4. VideoCardz，"JEDEC publishes UFS 5.0 spec with up to 10.8 GB/s sequential throughput"。[链接](https://videocardz.com/newz/jedec-publishes-ufs-5-0-spec-with-up-to-10-8-gb-s-sequential-throughput)
5. TechPowerUp，"JEDEC UFS 5.0 Standard to Deliver Sequential Performance up to 10.8 GB/s"。[链接](https://www.techpowerup.com/341645/jedec-ufs-5-0-standard-to-deliver-sequential-performance-up-to-10-8-gb-s)
6. Samsung Newsroom，"Samsung Unveils Industry's Fastest UFS 5.0 Solution for Next-Gen On-Device AI Applications"，2026 年 6 月。[链接](https://news.samsung.com/global/samsung-unveils-industrys-fastest-ufs-5-0-solution-for-next-gen-on-device-ai-applications)
7. Samsung Semiconductor，"UFS 5.0"。[链接](https://semiconductor.samsung.com/estorage/ufs/ufs-5-0/)
8. Samsung Semiconductor Newsroom，"[Infographic] UFS 5.0 Memory: The Optimal Solution for On-Device AI"。[链接](https://news.samsungsemiconductor.com/global/infographic-ufs-5-0-memory-the-optimal-solution-for-on-device-ai/)
9. 铠侠，"New Era of On-device AI Driven by High-speed UFS 5.0 Storage"。[链接](https://www.kioxia.com/en-jp/business/topics/ufs5-ondevice-ai-202602.html)
10. 铠侠，"Sampling UFS 5.0 Embedded Flash Memory Devices for Next-Generation Mobile Applications"，2026 年 2 月。[链接](https://americas.kioxia.com/en-us/business/news/2026/ssd-20260223-1.html)
11. Notebookcheck，"Kioxia announces UFS 5.0 embedded flash memory with 10.8 GB/s bandwidth"。[链接](https://www.notebookcheck.net/Kioxia-announces-UFS-5-0-embedded-flash-memory-with-10-8-GB-s-bandwidth-over-2x-faster-than-UFS-4-0.1233667.0.html)
12. Beebom，"UFS 5.0 Explained: Speed, Features and How Is It Better than UFS 4.0"。[链接](https://gadgets.beebom.com/guides/ufs-5-0-explained)
13. Smartprix，"UFS 5.0 vs UFS 4.1 / 4.0: The Biggest Smartphone Storage Upgrade, Explained"。[链接](https://www.smartprix.com/bytes/ufs-5-0-vs-ufs-4-1-4-0-the-biggest-smartphone-storage-upgrade-explained/)
14. Ursa Major Lab，"UFS 5.0 Released: Sequential Speeds Doubled"。[链接](https://www.ursamajorlab.com/blog/ufs-5-0-release/)
15. MIPI Alliance，"MIPI Alliance Introduces UniPro v3.0 and M-PHY v6.0 for Enhanced UFS Performance"。[链接](https://www.techpowerup.com/346700/mipi-alliance-introduces-unipro-v3-0-and-m-phy-v6-0-for-enhanced-ufs-performance)
16. Korea Times，"Samsung unveils industry's 1st UFS 5.0 memory optimized for on-device AI"，2026 年 6 月。[链接](https://www.koreatimes.co.kr/amp/business/tech-science/20260623/samsung-unveils-industrys-1st-ufs-50-memory-optimized-for-on-device-ai)

# IOMMU 与可恢复缺页：从硬件诉求到执行流程

> 本文基于 ARMv8 SMMUv3 架构、PCIe ATS/PRI 规范、Linux SVA/IOPF 实现，以及对 Apple Silicon DART 的公开逆向工程（Asahi Linux）整理而成。苹果未公开 SoC 微架构，相关数据来自第三方实测与逆向，仅供参考。

---

## 一、为什么需要 IOMMU

### 1.1 DMA 的原始问题

DMA（Direct Memory Access）允许设备绕过 CPU 直接读写内存，带来高吞吐的同时也制造了四个根本问题：

```
┌──────────┐         物理总线          ┌──────────┐
│  Device   │ ──── DMA (物理地址) ────▶ │   DRAM   │
└──────────┘                          └──────────┘
     问题 ①  安全：任意物理地址可达 → DMA 攻击
     问题 ②  寻址：32-bit 设备无法访问高位内存
     问题 ③  虚拟化：GPA ≠ HPA，设备看到的地址需要再翻译
     问题 ④  连续性：OS 分配的页物理不连续，设备需要 scatter-gather
```

### 1.2 IOMMU 的解决方式

IOMMU 插在设备与内存总线之间，用一套 **per-device I/O 页表** 把设备发出的 IOVA（I/O Virtual Address）翻译成物理地址，并做权限隔离。它就是 **CPU MMU 在设备世界的对应物**：

```
┌──────────┐    IOVA     ┌──────────┐     PA      ┌──────────┐
│  Device   │ ─────────▶ │  IOMMU   │ ─────────▶  │   DRAM   │
│ (StreamID)│            │ (I/O 页表)│             └──────────┘
└──────────┘             └──────────┘
                          ├─ 翻译 IOVA → PA
                          ├─ 权限检查（读/写/执行）
                          ├─ 隔离（per-device 页表）
                          └─ 自带缓存（IOTLB）
```

各平台的 IOMMU 实现：

| 平台 | IOMMU 名称 | 设备标识 | 页表格式 |
|------|-----------|---------|---------|
| Intel | VT-d | BDF (Bus/Device/Function) | 兼容 x86 多级页表 |
| AMD | AMD-Vi | DeviceID | 兼容 x86 多级页表 |
| ARM | SMMUv3 | StreamID (SID) | ARM LPAE 格式 |
| Apple | DART | 设备绑定 | 自有格式（3-4 级） |

---

## 二、Apple M1 SoC 互联架构

### 2.1 统一内存架构（UMA）概览

M1 采用 UMA：CPU、GPU、ANE 等所有 IP 共享同一片 LPDDR4X 物理内存，没有独立显存。

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  P-cluster  │  │  E-cluster  │  │     GPU     │  │     ANE     │  │  Media/I/O  │
│ 4×Firestorm │  │ 4×Icestorm  │  │   8 cores   │  │  16-core    │  │  ISP, PCIe  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │ own MMU        │ own MMU        │                │                │
       │                │                ▼                ▼                ▼
       │                │         ┌─────────────────────────────────────────┐
       │                │         │         DART · Apple IOMMU              │
       │                │         │     per-device IOVA → PA translation    │
       │                │         └──────────────────┬──────────────────────┘
       │                │                            │
       ▼                ▼                            ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                    Coherent Fabric / NoC                            │
  │               cache coherency + routing                            │
  └──────────────────────────────┬───────────────────────────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────────┐
                │     System Level Cache — 8 MB      │
                │     shared: CPU · GPU · all IPs    │
                └────────────────┬───────────────────┘
                                 │
         ┌──────────┬────────────┼───────────┬──────────┐
         ▼          ▼            ▼           ▼          ▼
      ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ... (×8 channels)
      │ MC 0 │  │ MC 1 │  │ MC 2 │  │ MC 3 │
      └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘
         │         │         │         │
         ▼         ▼         ▼         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │            LPDDR4X-4266 · Unified Memory                    │
  │       8×16-bit = 128-bit · ~68 GB/s · ≤16 GB               │
  └──────────────────────────────────────────────────────────────┘
```

**关键设计点：**

- **CPU 不走 DART**：P/E 核各自有核内 MMU/TLB 完成 VA→PA，以相干方式直接接入 fabric。
- **非 CPU 设备走 DART**：GPU、ANE、ISP、PCIe 等 DMA 设备发出的 IOVA 必须经 DART 翻译。苹果是 per-device（或 per-group）各挂一个独立 DART。
- **SLC 不是 CPU 的 L3**：它是挂在 fabric 上、被所有 IP 共享的 memory-side cache，主要为了省 DRAM 带宽和功耗，延迟比真正的 CPU L3 高。

### 2.2 M1 多级缓存与 TLB 层级

以 Firestorm P-core 为例：

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Firestorm P-core                              │
│                    16 KB pages · VIPT L1                           │
│                                                                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │
│  │   L1 I-cache     │ │   L1 D-cache     │ │     TLBs         │    │
│  │   192 KB         │ │ 128 KB · 3-cycle │ │ L1: ~256 entries │    │
│  │                  │ │                  │ │ L2: 3072 entries │    │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘    │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
                ┌────────────────────────────────────┐
                │   P-cluster L2 — 12 MB             │
                │   shared ×4 P-cores · ~16-cycle    │
                └────────────────┬───────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────────┐
                │   System Level Cache — 8 MB        │
                │   shared with GPU + all IPs        │
                └────────────────┬───────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────────┐
                │   LPDDR4X — unified memory         │
                │   ~68 GB/s · ~91 ns latency        │
                └────────────────────────────────────┘

E-core (Icestorm): L1I 128 KB · L1D 64 KB · L2 4 MB shared ×4
```

**为什么 L1 能做到又大又快：** 苹果用 16 KB 页。L1 是 VIPT（虚拟索引、物理标签），索引位必须落在页内偏移里才不产生别名。16 KB 页提供 14 位偏移，足够给 128 KB 的 L1D 留出索引位（128 KB / 8-way = 16 KB per way = 14 位索引）。4 KB 页做不到同等大小。

**反常规的缓存层级：** 苹果没有「私有 L2 + 大 L3」的三级结构，而是直接上大而快的簇内共享 L2（P 簇 12 MB），再用 SLC 做 memory-side cache。

---

## 三、地址翻译与缺页机制

### 3.1 CPU MMU 的地址翻译流程

M1 是 AArch64，用 ARMv8.x 多级页表。16 KB 颗粒下，48 位虚拟地址的拆分方式：

```
  虚拟地址 (48 bits)
  ┌──────┬──────┬──────┬───────┐
  │ L1   │ L2   │ L3   │Offset │
  │11 bit│11 bit│11 bit│14 bit │  ← 14-bit offset = 16 KB page
  └──┬───┴──┬───┴──┬───┴───┬───┘
     │      │      │       │
     ▼      ▼      ▼       ▼
   TTBR → L1 表 → L2 表 → L3 表 → 物理页帧 + Offset = PA
```

完整翻译路径：

```
Core 发出 VA
      │
      ▼
  L1 TLB (~256 entries, per-core)  ── hit ──▶  PA → 访问缓存/内存
      │ miss
      ▼
  L2 TLB (3072 entries)            ── hit ──▶  PA → 访问缓存/内存
      │ miss
      ▼
  Page-directory cache             ── hit ──▶  跳过部分遍历级
      │ miss
      ▼
  Hardware page-table walker
  (TTBR → L1 → L2 → L3, 访问内存中的页表)
      │
      ├─ valid  ──▶  PA → 回填 TLB → 访问缓存/内存
      │
      └─ invalid ──▶  Translation / Permission Fault
                      Data Abort → 陷入 EL1 (XNU 内核)
                            │
                      ┌─────┴──────┐
                      ▼            ▼
                 软缺页          硬错误
              (可恢复)        (不可恢复)
                 │                │
                 │                ▼
                 │         SIGSEGV / EXC_BAD_ACCESS
                 ▼
          OS 补页并更新页表
          (demand alloc / COW /
           decompress / swap-in)
                 │
                 ▼
          ERET → 指令重新执行 ↻
```

### 3.2 缺页的本质：机制 vs 策略

| 层面 | 由谁负责 | 具体做什么 |
|------|---------|-----------|
| **机制（mechanism）** | MMU 硬件 | 翻译 VA→PA、权限检查、发现无效项时抛异常（Data Abort） |
| **策略（policy）** | OS 内核 | 如何建立映射、缺页了怎么补（demand alloc / COW / swap / compress） |

MMU 不知道什么是「按需调页」「写时复制」「内存压缩」——它只忠实执行 OS 填好的页表，出问题就 trap。macOS 的特色是优先用内存压缩器而非磁盘 swap，所以很多缺页其实是解压页。

---

## 四、IOMMU 的故障模型：terminate vs recoverable

### 4.1 传统模型：terminate（中止）

经典 DMA 下，驱动提前 pin 住缓冲页、在 IOMMU 里建好映射。如果翻译表里没有有效映射（配置错误或攻击），IOMMU **检测并上报故障**、中止那笔 DMA 事务。设备收到错误、OS 记日志。不可恢复。

```
驱动分配缓冲 → pin pages → dma_map(建 IOVA→PA 映射)
        │
        ▼
  Device DMA (IOVA)  →  IOMMU 翻译  →  PA → DRAM  (全程命中)
        │
  完成后 dma_unmap → unpin
```

**为什么经典 DMA 不会缺页：** 所有页在 DMA 发起前就已经 pin 住且映射好了。翻译失败意味着配置错误,是 fatal 的。

### 4.2 为什么 IOMMU 不能像 CPU 那样直接搞可恢复缺页

CPU 有**精确异常**：出错的指令还没退休，OS 补好页、返回、指令重发。但一笔 DMA 事务已经在总线上跑了，DMA 引擎不像 CPU 那样能随手回退重来。要让设备也能「缺页 → 恢复」，必须加硬件协议让「出错的事务能被暂停、再重试」。

### 4.3 可恢复模型：PRI 与 SMMU stall

两种实现路径：

| | PCIe PRI | ARM SMMU stall |
|---|---------|---------------|
| 事务暂停位置 | 设备内部（需设备有 ATC） | SMMU 内部（不需 ATC） |
| 故障上报方式 | 设备主动发 Page Request | SMMU 写 evtq 记录 |
| OS 响应方式 | Page Response（通过 IOMMU） | CMD_RESUME（通过 cmdq） |
| 对设备的要求 | 较高（需 ATS + ATC + PRI） | 较低（声明 stall-tolerant 即可） |
| 适用场景 | PCIe 设备 | 片上平台设备 |

---

## 五、ARM SMMU stall 模型：完整机制分析

### 5.1 核心数据结构

```
SMMU 寄存器
 │
 ├─ STRTAB_BASE ──▶ Stream Table (per-device)
 │                    │
 │                    └─ STE[StreamID]
 │                         ├─ Config (stage-1 / stage-2 / bypass / fault)
 │                         ├─ S1ContextPtr ──▶ Context Descriptor Table
 │                         │                    │
 │                         │                    └─ CD[SSID]
 │                         │                         ├─ TTB0 ──▶ 进程页表 (stage-1)
 │                         │                         ├─ ASID
 │                         │                         └─ S (stall enable)
 │                         │
 │                         ├─ S2TTB ──▶ Stage-2 页表 (虚拟化)
 │                         └─ VMID
 │
 ├─ CMDQ_BASE ──▶ Command Queue (OS → SMMU)
 │                  CMD_TLBI_*    (TLB 失效)
 │                  CMD_RESUME    (恢复 stalled 事务)
 │                  CMD_CFGI_*    (配置失效)
 │
 ├─ EVTQ_BASE ──▶ Event Queue (SMMU → OS)
 │                  故障记录: SID, SSID, IOVA,
 │                           type, STAG, ...
 │
 └─ PRIQ_BASE ──▶ PRI Queue (仅 PRI 模式使用)
```

### 5.2 stall 缺页完整时序

```
     Device                     SMMU                        OS / kernel
       │                          │                              │
  ①    │── DMA req (VA+SSID) ───▶│                              │
       │                          │                              │
       │                     ② STE → CD → 走 stage-1 页表       │
       │                        遇到无效项 (PTE invalid)         │
       │                          │                              │
       │                     ③ STALL: park 该事务               │
       │                        后续同上下文事务也被 stall       │
       │                          │                              │
       │                     ④ 写 evtq 记录                     │
       │                        (SID, SSID, IOVA, type, STAG)   │
       │                        拉中断 ─────────────────────────▶│
       │                          │                              │
       │                          │                         ⑤ evtq IRQ handler
       │                          │                            解析 SID → device
       │                          │                            解析 SSID → process mm
       │                          │                            解析 IOVA + type
       │                          │                              │
       │                          │                         ⑥ IOPF 处理器
       │                          │                            (可睡眠、可等 I/O)
       │                          │                            handle_mm_fault()
       │                          │                            分配页 / swap-in / COW
       │                          │                            更新进程页表
       │                          │                              │
       │                          │                         ⑦ TLBI 失效 SMMU TLB
       │                          │                            (确保旧缓存被清除)
       │                          │                              │
       │                     ⑧  ◀── CMD_RESUME (retry) ────────│
       │                        via cmdq                         │
       │                          │                              │
       │                     ⑨ 重新走页表                       │
       │                        这次翻译成功                     │
       │                          │                              │
  ⑩   │◀── DMA 完成 ────────────│                              │
       │   (对设备完全透明)        │                              │
```

如果 OS 判定是非法访问（越界、权限不符等），则在第 ⑧ 步发 `CMD_RESUME(abort)` 而非 retry，那笔事务被终止、SMMU 向设备返回错误。

### 5.3 与经典 pin-memory 路径的对比

```
经典 DMA (pin memory):
  driver: alloc buf → pin pages → dma_map (IOVA→PA) → 发起 DMA → 完成 → dma_unmap → unpin
  优点: 延迟低、确定性强
  缺点: 占住物理内存不可换出、要显式 map/unmap、无法对任意指针零拷贝

SVA + stall (可恢复缺页):
  driver: bind(process) → device uses malloc'd pointer → 缺页时 OS 自动补 → DMA 继续
  优点: 直接传指针、零拷贝、编程简单
  缺点: 缺页延迟、需要完整硬件链、设备可能被 stall
```

---

## 六、三侧机制详解

### 6.1 Device 侧

#### 机制 A：Stall-tolerant（可被暂停而不死锁）

**具体功能：** 设备必须能在一笔或多笔 DMA 事务被 SMMU stall 后继续正常工作，不超时、不死锁、不丢失状态。死锁的典型来源是设备需要某笔被 stall 的事务先完成才能释放资源去处理下一笔——ARM 要求 stall-capable master 不能有这种事务间依赖。

**是否需要硬件改动：** 需要。设备的 DMA 引擎必须在设计时就考虑被 stall 的场景：事务的状态机要能长时间停在「等待完成」而不触发看门狗超时；内部队列要能容纳 stall 期间堆积的后续请求。这不是软件能补的——需要 RTL 级设计。

**带来的好处：**

- 设备不需要自带 ATC（地址翻译缓存），大幅降低设备复杂度。
- 适用于片上平台设备（加速器、ISP、DMA 控制器），这些设备往往没有 PCIe ATS 能力。
- 缺页完全对设备透明——它只看到「这笔 DMA 慢了一点」，不需要任何感知和重发逻辑。

**带来的额外问题：**

- **Stall 上限（max outstanding stalls）：** SMMU 能 park 的事务数有限（由硬件实现决定）。如果设备在短时间内触发大量缺页，可能耗尽 stall 容量,后续事务会被强制 terminate。设备需要限制自己的 outstanding transactions 数量。
- **延迟不确定性：** 被 stall 的事务可能等待数十微秒到毫秒级（等 OS 补页甚至等磁盘 I/O），设备的实时性保证变差。对延迟敏感的设备（如音频 DMA）可能不适合启用 stall。
- **设计验证复杂：** 需要验证设备在各种 stall 时长、stall 数量组合下都不出问题，增加了验证矩阵。

#### 机制 B：SSID（SubStreamID / PASID）标签

**具体功能：** 设备在每笔 DMA 事务中附带一个 SSID 标签（ARM 术语，等同于 PCIe 的 PASID，20 位），表明这笔访问属于哪个地址空间。SMMU 用 SID（StreamID，标识设备）+ SSID（标识进程）二维索引定位到对应的 Context Descriptor，进而找到对应进程的页表。

**是否需要硬件改动：** 需要。设备的 DMA 引擎必须支持在事务协议层（AXI/ACE/CHI 的 sideband signal）中携带 SSID 字段。总线接口需要额外的信号线。这是硬件接口级的改动。

**带来的好处：**

- 一个设备可以同时服务多个进程的 DMA，每个进程有独立的地址空间和权限隔离。
- OS 根据 SSID 可以精确定位到哪个进程的 mm 需要被 fault in，而不是盲目扫描。

**带来的额外问题：**

- **SSID 空间管理：** OS 需要分配和回收 SSID，确保不冲突、不泄漏。进程退出时必须清理绑定。
- **CD 表膨胀：** 每个 SSID 对应一个 Context Descriptor；如果大量进程绑定到同一设备，CD 表会占用显著内存（每个 CD 通常 64 字节）。
- **设备驱动复杂度：** 驱动需要管理哪些 SSID 已绑定、在提交 DMA 请求时附带正确的 SSID。

#### 机制 C：固件声明能力（DT / ACPI IORT）

**具体功能：** 设备的 stall 能力、SSID 位宽等信息由固件（设备树 DT 或 ACPI IORT 表）向 OS 声明。OS 只在固件声明支持时，才会把对应 stream 配置为 stall 模式。

**是否需要硬件改动：** 不需要硬件改动,但需要平台固件 / bootloader 的配合。如果固件描述错误（声明支持但硬件不支持），可能导致系统崩溃。

**带来的好处：**

- OS 无需探测设备能力，安全地按声明配置。
- 同一 SoC 上不同设备可以选择性启用 stall：延迟敏感的设备（如音频）保持 terminate，吞吐导向的设备（如加速器）启用 stall。

**带来的额外问题：**

- 固件描述的正确性依赖平台厂商，错误难以调试。
- 不同 OS 对同一 DT 属性的解读可能不同，跨平台兼容需要额外验证。

---

### 6.2 SMMU 侧

#### 机制 D：STE / CD 配置为 stall 模式

**具体功能：** Stream Table Entry（STE）描述设备的翻译配置。STE 里的 `S1ContextPtr` 指向 Context Descriptor 表,每个 CD 有一个 `S` 位（stall enable）——置位后,该上下文的 stage-1 翻译故障触发 stall 而非 abort。此外 CD 中的 `TTB0` 字段指向**目标进程的页表**（与 CPU 用同一套），实现地址空间共享。

```
STE (per-device, indexed by SID)
┌──────────────────────────────────────────────┐
│ Valid │ Config │ S1ContextPtr │ S2TTB │ VMID │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
CD Table (per-SSID, indexed by SSID)
┌──────────────────────────────────────────────┐
│ TTB0 ──▶ 进程页表 │ ASID │ S (stall) │ ...  │
└──────────────────────────────────────────────┘
```

**是否需要硬件改动：** 需要。SMMU 的控制逻辑需要在翻译失败时根据 `S` 位决定行为（stall vs abort），并维护 stalled 事务的状态。这是 SMMU IP 内部的逻辑改动。

**带来的好处：**

- 让 SMMU 能指向 CPU 进程的页表，实现真正的设备-CPU 地址空间共享。
- 按 CD 粒度控制 stall：同一设备的不同 SSID 可以有不同策略。

**带来的额外问题：**

- **页表格式兼容性：** 要求 SMMU stage-1 和 CPU 的页表格式完全一致（ARM LPAE）。如果 CPU 使用了 SMMU 不支持的扩展（如 MTE tag bits、特殊权限位），共享会出问题。
- **ASID 管理竞争：** CPU 和 SMMU 共享 ASID 命名空间时，OS 必须确保 ASID 不被回收和重用，直到 SMMU 侧的 TLB 也被失效。这要求 pin 住 ASID，减少了可用 ASID 数量。
- **CD 表内存开销：** 2-level CD 表结构可以延迟分配，但热路径上可能导致额外的内存访问。

#### 机制 E：Event Queue（evtq）故障上报

**具体功能：** SMMU 在 stall 模式下遇到翻译故障时，将故障信息写入内存中的 Event Queue（环形缓冲区），包括：SID（哪个设备）、SSID（哪个进程）、IOVA（出错的地址）、故障类型（translation / permission / access flag 等）、STAG（stall tag，用于后续 resume 时标识）。写入后拉中断通知 OS。

**是否需要硬件改动：** 需要。SMMU 必须有：写入 evtq 的 DMA 引擎、维护 evtq 的 producer/consumer 指针、生成故障中断的能力。Event Queue 的格式和字段宽度是 SMMUv3 架构定义的，不同实现的队列深度可以不同。

**带来的好处：**

- 异步上报、批量处理：OS 可以一次性处理队列中多条故障，减少中断次数。
- 故障信息丰富：OS 能精确定位「哪个设备、哪个进程、什么地址、什么类型」，做出正确决策。

**带来的额外问题：**

- **队列溢出：** 如果 OS 处理速度跟不上故障产生速度，evtq 会满。满了之后 SMMU 的行为是实现定义的（可能丢弃新事件或 stall 更多事务），可能导致系统不稳定。
- **中断延迟：** 从故障发生到 OS 收到中断、再到开始处理，有不可忽略的延迟。这段时间设备一直被 stall。
- **安全性：** 恶意设备理论上可以通过大量故障填满 evtq，造成 DoS。OS 需要限流机制。

#### 机制 F：Command Queue（cmdq）接收 CMD_RESUME

**具体功能：** OS 处理完缺页后，通过 Command Queue 向 SMMU 发送 `CMD_RESUME` 命令，携带 STAG 标识哪笔事务应该恢复，以及动作标志（retry = 重新走页表 / abort = 终止事务）。SMMU 收到后恢复对应的 stalled 事务。

**是否需要硬件改动：** 需要。SMMU 必须支持 `CMD_RESUME` 命令的解析和执行。内部需要一个「stalled 事务池」，能根据 STAG 精确定位并恢复特定事务，然后重新发起页表遍历。

**带来的好处：**

- OS 有明确的控制权：可以选择 retry（修好了）或 abort（非法访问），而不是只能一刀切。
- STAG 机制允许并发处理多个不同的 stalled 事务。

**带来的额外问题：**

- **Stall 池容量：** 硬件能维护的并发 stalled 事务数量有限。如果大量设备同时密集缺页，stall 池可能耗尽。超出后新的缺页只能 abort。
- **STAG 管理：** OS 必须正确跟踪每个 STAG 与对应设备/进程/地址的关联，否则可能 resume 错误的事务。
- **cmdq 竞争：** CMD_RESUME 和其他命令（如 TLBI、CFGI）共用同一个 cmdq。在故障密集时，队列竞争可能影响正常 TLB 失效的时效性。

#### 机制 G：Park 事务 + 重新走页表

**具体功能：** 这是 stall 模型的核心硬件能力。SMMU 在检测到故障后，不丢弃事务，而是将事务的完整上下文（SID、SSID、IOVA、读写类型、事务大小等）保存在内部，等待 CMD_RESUME 后重新从页表根开始遍历。同时,被 stall 的上下文下的后续事务也被阻塞，保证顺序一致性。

**是否需要硬件改动：** 需要。这是 stall 模型最核心的硬件代价——SMMU 内部需要硬件存储空间来保存被 park 的事务上下文，以及 resume 后重新启动页表遍历器的逻辑。相比 terminate 模型（直接丢弃,零状态），stall 模型的 SMMU 面积和复杂度显著增加。

**带来的好处：**

- 设备完全无感，不需要 ATC，不需要重发逻辑。
- 顺序一致性天然保证（同上下文后续事务被阻塞）。

**带来的额外问题：**

- **面积与功耗：** 保存 stalled 事务上下文需要 SRAM。每笔事务上下文可能 100+ 字节,如果支持 N 笔并发 stall，就需要 N × 100+ 字节的专用存储，加上控制逻辑。
- **同上下文阻塞：** 被 stall 的上下文下所有后续事务都被阻塞。如果一个进程的某页缺页，该进程对该设备的所有 DMA 都停住，可能导致级联延迟。
- **超时策略：** 如果 OS 长时间不 resume（比如内核 bug），被 stall 的事务会无限期挂起。硬件或软件需要一个超时机制兜底。

---

### 6.3 OS 侧

#### 机制 H：SVA bind——分配 PASID 并绑定进程

**具体功能：** 用户态驱动调用 `iommu_sva_bind_device(device, mm)`，OS 分配一个 PASID/SSID，在 SMMU 的 CD 中填入该进程页表的 `TTB0` 和 `ASID`，启用 stall 位。此后设备用该 SSID 发起的 DMA 就走这个进程的地址空间。

**是否需要硬件改动：** 不需要。这是纯软件操作——OS 配置已有的 SMMU 硬件寄存器和内存中的数据结构。但前提是 SMMU 硬件支持 SSID 和 stall。

**带来的好处：**

- 设备可以直接用用户态 `malloc` 返回的指针做 DMA，不需要驱动显式映射。
- 多进程可以安全地共享同一个设备。
- 进程退出时 OS 自动解绑，安全性有保障。

**带来的额外问题：**

- **绑定生命周期管理：** 进程退出或 `exec` 时必须清理绑定、flush 设备侧缓存。如果设备正在 DMA 而进程退出，OS 必须等待或终止所有 in-flight 事务。Linux 用 `mmu_notifier.release` 回调实现。
- **PASID 数量限制：** PASID/SSID 通常 20 位 = 最多约 100 万个。虽然理论上够用，但 CD 表的内存开销与实际绑定数量正相关。
- **特权升级风险：** 如果绑定不做好权限检查,恶意用户可能让设备访问自己进程的地址空间之外的区域（通过伪造 SSID）。硬件 + OS 必须共同保证隔离。

#### 机制 I：可睡眠 IOPF 处理器

**具体功能：** IOMMU 驱动注册一个 I/O Page Fault（IOPF）处理器。当 evtq 报告一个可恢复的 translation fault 时，IOPF 处理器被调度执行。它的核心操作是调用内核的 `handle_mm_fault()`——和 CPU 缺页走完全相同的路径：分配物理页、从 swap 换入、解压、写时复制等。由于这些操作可能阻塞（等磁盘 I/O、等内存分配），IOPF 处理器必须运行在**可睡眠的上下文**中（workqueue，不是 hardirq/softirq）。

**是否需要硬件改动：** 不需要。这是纯内核软件,但需要正确复用 mm 子系统的 API（`handle_mm_fault` 本身是为 CPU 缺页设计的，用于 IOPF 时需要额外的锁定和引用计数）。

**带来的好处：**

- 完全复用 CPU 缺页的代码路径,不需要为设备侧重写一套页面管理逻辑。
- COW、transparent huge pages、NUMA balancing、KSM 等 CPU 侧的内存策略自动对设备生效。

**带来的额外问题：**

- **延迟：** 可睡眠意味着调度延迟 + I/O 延迟都可能叠加。最坏情况下,一次 IOPF 可能耗时数毫秒（等磁盘）。这段时间设备被 stall。
- **优先级反转：** IOPF workqueue 的调度优先级如果低于触发 DMA 的用户进程,可能导致优先级反转——高优先级进程等待低优先级 workqueue 补页。
- **锁竞争：** `handle_mm_fault()` 要拿 `mmap_lock`。如果用户进程本身正在做大量 mmap/munmap，IOPF 可能被阻塞在锁上。
- **GUP (get_user_pages) 交互：** 某些路径下 IOPF 和 GUP 可能产生竞争，内核需要仔细处理引用计数。

#### 机制 J：解析 evtq → 找到进程 mm

**具体功能：** evtq 中的故障记录只包含原始的 SID 和 SSID。OS 需要维护一个映射：SID → `struct device` → iommu_domain → SSID → `struct mm_struct`。通过这条链路,OS 找到被缺页进程的 mm，才能调用 `handle_mm_fault()`。

**是否需要硬件改动：** 不需要。纯软件的数据结构管理。

**带来的好处：**

- 精确定位：OS 不需要猜测或广播,直接找到正确的 mm。

**带来的额外问题：**

- 数据结构的一致性维护：进程绑定、解绑、退出都要同步更新这些映射。竞态条件（进程正在退出但设备还在 DMA）需要仔细处理。

#### 机制 K：补页 → 发 CMD_RESUME

**具体功能：** `handle_mm_fault()` 成功后，OS 更新进程页表（PTE 已有效），然后通过 cmdq 向 SMMU 发送 `CMD_RESUME(STAG, retry)`。如果判定为非法访问（`handle_mm_fault` 返回 `VM_FAULT_SIGBUS / VM_FAULT_SIGSEGV`），则发 `CMD_RESUME(STAG, abort)` 并向设备驱动上报错误。

**是否需要硬件改动：** 不需要（cmdq 已有）。

**带来的好处：**

- OS 有裁判权：可以区分「合法缺页」和「非法访问」,对后者直接 abort。
- 设备驱动可以注册回调，在 abort 时做自定义错误处理。

**带来的额外问题：**

- **retry 与 abort 的时序：** CMD_RESUME 发出后，SMMU 重新走页表。如果在极短的窗口内页表又变了（另一个 CPU 正在 unmap），可能再次缺页，形成「stall → resume → 再 stall」的循环。OS 需要在 resume 前做必要的同步。

#### 机制 L：mmu_notifier 同步失效

**具体功能：** 当进程页表发生变动（munmap、migrate、swap-out、COW 完成、KSM merge 等），内核通过 mmu_notifier 回调通知 IOMMU 驱动。驱动必须：(1) 失效 SMMU 的 IOTLB 中对应的条目（发 `CMD_TLBI_*`），(2) 如果设备有 ATC（PRI 路径），还要发 ATS Invalidation 到设备并等待 completion。整个过程是**同步的**——notify 回调必须等失效完成才能返回,否则设备可能用旧翻译访问已回收的页。

**是否需要硬件改动：** 不需要额外改动（依赖已有的 TLBI 命令），但需要硬件保证 TLBI 命令完成后旧缓存确实被清除。

**带来的好处：**

- 保证一致性：CPU 修改页表后，设备不会用到过期翻译。
- 和 CPU 侧的 TLB shootdown 等价,是 SVA 正确性的基石。

**带来的额外问题：**

- **性能杀手：** 每次 unmap 都要同步等 SMMU TLBI 完成。如果设备有 ATC，还要等设备的 ATS Invalidation response——这个往返可能需要微秒级。在频繁 mmap/munmap 的工作负载下，mmu_notifier 回调成为瓶颈。
- **死锁风险：** mmu_notifier 在持有 `mmap_lock` 时被调用。如果 TLBI 命令因某种原因挂起（SMMU 故障、设备无响应），整个进程的内存管理被阻塞。Linux 内核对此有超时机制，但超时意味着潜在的一致性破坏。
- **ATS invalidation 放大：** 一次 munmap 可能影响大量页。对每一页都发一次 ATS Invalidation 太慢;batch invalidation 又可能 over-invalidate,导致设备 ATC 被不必要地清空,后续缺页增多。

---

## 七、机制汇总对照表

| 编号 | 机制 | 所属侧 | 需要硬件改动 | 核心功能 | 主要好处 | 主要问题 |
|------|------|--------|------------|---------|---------|---------|
| A | Stall-tolerant | Device | 是 (RTL) | 被暂停而不死锁 | 设备无需 ATC,缺页透明 | stall 容量有限,延迟不确定 |
| B | SSID/PASID 标签 | Device | 是 (总线接口) | 标识地址空间 | 多进程共享设备 | SSID 管理,CD 表膨胀 |
| C | 固件声明 | Device/FW | 否 (仅固件) | 向 OS 声明能力 | 安全按需配置 | 描述正确性依赖厂商 |
| D | STE/CD + stall 位 | SMMU | 是 (SMMU IP) | 配置翻译和 stall 策略 | 地址空间共享,按 CD 粒度控制 | 页表兼容性,ASID 竞争 |
| E | Event Queue | SMMU | 是 (SMMU IP) | 故障异步上报 | 批量处理,信息丰富 | 队列溢出,DoS 风险 |
| F | CMD_RESUME | SMMU | 是 (SMMU IP) | OS 控制事务恢复 | retry/abort 可选 | stall 池容量,cmdq 竞争 |
| G | Park + re-walk | SMMU | 是 (SMMU IP) | 保存并重试事务 | 设备无感,顺序保证 | 面积功耗,同上下文阻塞 |
| H | SVA bind | OS | 否 | 绑定进程到设备 | malloc 指针可 DMA | 生命周期,特权升级风险 |
| I | IOPF 处理器 | OS | 否 | 可睡眠缺页处理 | 复用 CPU 缺页路径 | 延迟,优先级反转,锁竞争 |
| J | evtq 解析 | OS | 否 | SID/SSID → mm 定位 | 精确定位进程 | 竞态条件 |
| K | CMD_RESUME 发送 | OS | 否 | 补页后恢复事务 | OS 有裁判权 | retry-stall 循环 |
| L | mmu_notifier | OS | 否 | 页表变动同步失效 | 保证一致性 | 性能开销,死锁风险 |

---

## 八、Apple DART 的定位

Apple DART 属于 **terminate 模型**：翻译 + 保护 + 故障检测都有,但没有 PRI / stall 那套可恢复缺页协议。DMA 缓冲区由驱动提前映射、页不换出。DART 的设计哲学是简单高效——在 UMA 架构下,CPU 和设备已经共享同一片物理内存,苹果选择通过框架层（如 Metal、Core ML）在上层做数据共享,而不是在 IOMMU 层实现 SVA。GPU 另有固件管理的自有页表/MMU,是图形虚拟内存机制,和 DART 不是同一层。

```
                    ┌─────────────────────────┐
                    │       IOMMU 故障模型     │
                    └───────────┬─────────────┘
                    ┌───────────┴─────────────┐
                    ▼                         ▼
          ┌──────────────┐          ┌──────────────┐
          │  Terminate   │          │ Recoverable  │
          │  (经典 DMA)   │          │  (SVA/SVM)   │
          │              │          │              │
          │ ·pin memory  │          │ ·demand page │
          │ ·map ahead   │          │ ·shared PT   │
          │ ·fault=fatal │          │ ·stall/PRI   │
          └──────────────┘          └──────────────┘
                ▲                         ▲
                │                         │
          Apple DART              SMMUv3 stall / PRI
          Intel VT-d (legacy)     Intel VT-d (scalable)
          AMD-Vi (legacy)         AMD-Vi (v2 + PRI)
```

---

## 参考资料

- ARM System Memory Management Unit Architecture Specification (SMMUv3)
- PCI-SIG: Address Translation Services (ATS) / Page Request Interface (PRI) / PASID
- Linux 内核: `drivers/iommu/arm-smmu-v3/`, `drivers/iommu/io-pgfault.c`, `drivers/iommu/iommu-sva.c`
- Jean-Philippe Brucker: Shared Virtual Addressing for the IOMMU (LWN, kernel patchsets)
- Asahi Linux: DART driver reverse engineering (`drivers/iommu/apple-dart.c`)
- AnandTech: Apple M1 Firestorm/Icestorm microarchitecture deep dive
- 7-cpu.com: Apple M1 cache/TLB latency measurements

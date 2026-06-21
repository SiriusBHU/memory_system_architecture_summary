# 统一内存 + 异构缺页与 LRU：技术演进调研

> 这是一份「演进前 vs 演进后」的对照调研，聚焦于设备侧内存（NPU / GPU / DMA 缓冲）该怎么被操作系统治理。锚点文章是 [A16e — IOMMU 统一内存与异构 PF/LRU](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md)。文档把经典的「钉死内存（pinned DMA）」路径和「SVA + HMM」演进方案放在一起对比：原方案长什么样、新方案做了什么、瓶颈数据在哪、两套架构的差异在哪。**演进方案在数据中心已经成熟落地，在手机端目前仍是设计方案，没有出货。**

## 1. 范围与方法

**调研对象。** 这里说的「统一设备内存」指的是 CPU 与加速器（NPU、GPU、ISP、DMA 外设）共享同一个**虚拟地址空间**，也共享同一块**物理 DRAM**，而且操作系统能像管 CPU 内存那样**让设备内存缺页、迁移、回收**。这比厂商宣传里的「Unified Memory」要强——后者通常只是「没有独立显存」。

**原方案。** 经典 pinned DMA。内核分配一块物理连续的缓冲（通过 `dma-buf` heap，Android 上以前叫 ION），把 IOMMU 的 stage-2 页表一次性配好，然后把这些页**钉死（pin）**——只要设备可能 DMA 进来，这些页就不能被搬走。这块内存对 OS 的 LRU 不可见，设备没释放之前没法迁移、也没法回收。

**演进方案。** SVA（Shared Virtual Addressing，地址空间共享）+ ATS/PRI + HMM（Heterogeneous Memory Management）。设备拿到一个 PASID 身份，**直接走进程的页表**（IOMMU 帮它翻译），遇到翻译缺失就发起页请求（PCIe 走 ATS/PRI，ARM 走 SMMUv3 stall），由内核把页调入再继续；HMM 给设备侧内存挂上 `ZONE_DEVICE` 的 `struct page`，原有的迁移和 LRU 路径自然能管到它。设备 TLB 与 CPU 页表的同步交给 `mmu_notifier`，而不是「钉死」。

**资料来源。** 14 条来源，覆盖：内核文档（[SVA](https://docs.kernel.org/arch/x86/sva.html)、[HMM](https://www.kernel.org/doc/html/v5.0/vm/hmm.html)），架构规范（ARM SMMUv3、PCIe ATS/PRI），三篇 2020–2025 年的实测论文（coIOMMU ATC '20、GPUVM 2024、MI300A 解剖 2025），TACO 2024 的按需分页定量研究，厂商文档（NVIDIA Grace Hopper、Apple WWDC10686、Android dma-buf heaps），以及 LMCache 的 KV cache 计算器。文档里的关键硬数字，11 条都能在 §9 找到对应来源；另有 4 条是基于公开公式做的「信封背面」推算，正文里已经注明。

## 2. 问题背景

**系统要干的事是什么。** 一台现代手机或者 edge 盒子要在 NPU 上跑端侧 LLM，要在 GPU 上画 UI，要在 ISP 上处理摄像头，**还要**让普通 app 正常活着——所有这些都靠同一块 8–24 GB 的 LPDDR。CPU 和加速器不只是共用 DRAM 颗粒，而是在抢同一块紧巴巴的 GB。

**为什么这个领域会变难。** 三个物理与架构上的约束在这里撞到一起：（1）LPDDR 每十年大约只涨 4 倍，而 LLM 一类负载涨了大约 4000 倍（见 [agent-era-memory-workload-CN.md](agent-era-memory-workload-CN.md)）；（2）IOMMU 页表和设备 TLB 在经典模型里**不能缺页**——所以内核只能把所有可能被设备访问的页都钉死；（3）钉死的页既不能迁移也不能回收，OS 整套回收引擎（LRU、MGLRU、DAMON）对加速器手里那部分 RAM 是**瞎的**。

**为什么原方案不够用了。** Agent 时代，「被钉死、看不见」的那部分内存，已经从「一块视频缓冲」长成了「模型权重 + 多 GB KV cache + 一堆 dma-buf heap」。原来设备侧只占几十 MB 的时候，「钉死一切」是可以接受的；当它占到系统内存的 1/3 甚至更多时，就不行了。OS 必须能搬、能回收设备数据，否则它在治理的只是它**看得见**的那一半。

## 3. 具体问题与瓶颈数据

### 具体问题

1. **被钉死的设备内存对 LRU 不可见。** `dma-buf` 分配绕过 page cache 和 LRU 链（[A09 §3.5](../foundations/A09-设备内存全景.md)；[Android dma-buf 计量, AOSP](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem)）。回收看到的可用池比内核实际拥有的小，lmkd 触发得过早（[A08](../foundations/A08-压力与低内存终止.md)）。
2. **端侧模型权重和 KV cache 把设备侧吃满。** Llama-3.2-3B FP16 权重大约 16 GB，Q4 量化降到大约 5 GB（[Meta Llama 3.2, 2024](https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/)）。32K 上下文的 KV cache 在 FP16 下再额外占大约 3.7 GB（按 [LMCache KV 计算器](https://lmcache.ai/kv_cache_calculator.html) 的公式算出）。
3. **CPU↔设备数据共享得走拷贝或 handle 转手。** 没有共享 VA，每一个跨 IP 的缓冲要么走内核中介的 handle import，要么走拷贝（[dma-buf 导入路径, AOSP](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem)）。带宽和能耗都花在了**硬件本来能直接做的事**的簿记上。
4. **设备内存没有按 app 的会计科目。** memcg 看的是 CPU 页；dma-buf 计量是另一套，且在 Android 上还没有完全做到 per-app（[Perfetto 内存案例研究, 2024](https://perfetto.dev/docs/case-studies/memory)）。没数字就没有公平的 per-app 回收和配额。

### 瓶颈数据

下面这张表说明，为什么 agent 时代「钉死又看不见」这件事没法再容忍。每个数字都在 §9 有出处。

| 内存项 | 大小 | LRU 看得见？ | 来源 |
|---|---|---|---|
| 旗舰手机 DRAM 总容量（2024） | 12–24 GB | n/a（整池） | 三星 2023, A16 锚点 |
| 8 GB Pixel 7 用户可用 | 约 7.8 GB | n/a（整池） | Android Authority [ref 11，弱引用] |
| Llama 3.2 3B FP16 权重 | 约 16 GB | **不** （dma-buf pinned） | [Meta, 2024](https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/) |
| Llama 3.2 3B Q4 权重 | 约 5 GB | **不** （dma-buf pinned） | LocalLLM.in 2026 聚合源 |
| KV cache，Llama-3.2-3B，32K ctx，FP16 | 约 3.7 GB | **不** （NPU 缓冲） | [LMCache 计算器](https://lmcache.ai/kv_cache_calculator.html)（28 层 × 8 KV 头 × 128 head_dim × 32K × 2 B × 2） |
| 同上 KV cache，32K ctx，INT8 | 约 1.8 GB | **不** （NPU 缓冲） | LMCache 计算器 |
| DMA 缺页延迟 vs CPU 缺页 | **3×–80×** | n/a（延迟比值） | [coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian) |
| GPU UVM 远端缺页（NVIDIA 独立 GPU） | 30–45 µs/次 | n/a（延迟） | [Allen & Ge TACO 2024](https://dl.acm.org/doi/10.1145/3632953) |
| AMD MI300A 上单页缺页（UMA SoC 的最优情形） | CPU 9 µs / GPU 16–18 µs | n/a（延迟） | [arXiv 2508.12743, 2025](https://arxiv.org/abs/2508.12743) |
| PASID 位宽（SVA 并发上下文） | 20 bit → 约 1.05 M 并发 | n/a（容量） | [Linux SVA 文档](https://docs.kernel.org/arch/x86/sva.html) |

**怎么看这张表。** 一台 8 GB 手机，光是 Q4 权重 5 GB 加 8K 上下文 KV cache 大约 2 GB，已经接近 7 GB 被钉死、对 LRU 不可见——也就是绝大部分**用户可用**内存。OS 的回收只能在剩下大约 1 GB 上做文章。表里标 **不** 的几行，就是 LRU 盲区所在。

## 4. 架构图：原方案 vs 演进方案

两张图用同样的组件、同样的布局画。演进图里和原图不一样的地方用 `*` 标出来。

**原方案——经典 pinned DMA + dma-buf / ION**

```
   +---------+   syscall    +-------------+
   |   CPU   | -----------> |   Kernel    |
   | (proc)  |              |    (mm)     |
   +---------+              +------+------+
        |                          |
        | CPU VA -> PA             | alloc + pin
        v  (CPU MMU 翻译)          v
   +---------+              +-------------+
   | CPU MMU |              |  dma-buf    |
   |  / TLB  |              |  pinned     |  <-- 不在 LRU,
   +----+----+              |  region in  |      不能迁移
        |                   |  RAM        |
        v                   +-----+-------+
   +---------+                    ^
   |   RAM   | <-- LRU 只管        |
   +---------+     CPU 这一侧的页  |
                                  |
                                  | dma（用固定物理地址，
                                  |       没有缺页通路）
                          +-------+--+
                          |  Device  |
                          | (NPU /   |
                          |   GPU)   |
                          +----------+
                              ^
                              | IOMMU stage-2 页表
                              | 分配时一次性配好；
                              | 没有缺页、没有迁移。
```

*原方案：内核分配 + 钉死一块物理缓冲，IOMMU 配一次，设备照固定物理地址 DMA。这块钉死区对 LRU 不可见，设备没放手之前没法迁移、没法回收。*

**演进方案——SVA + ATS/PRI + HMM（ZONE_DEVICE + 双向迁移）**

```
   +---------+   syscall    +-------------+
   |   CPU   | -----------> |   Kernel    |
   | (proc)  |              |    (mm)     |
   +---------+              +------+------+
        |                          |
        | CPU VA -> PA             | * mmu_notifier
        v  (CPU MMU 翻译)          |   把页表更新同步到
   +---------+                     v   设备 TLB
   | CPU MMU |              +-------------+
   |  / TLB  |              | RAM +       |
   +----+----+              | ZONE_DEVICE |  <-- LRU/迁移路径
        |                   | pages with  |      也能管到设备页
        v                   | struct page |
   +---------+              +-----+-------+
   |   RAM   |                    ^
   +---------+                    |
        ^                         | * migrate
        |                         |   (HMM 双向)
        |  * 通过 IOMMU 翻译       v
        |    (ATS 缓存)
        |  * 翻译缺失就发起缺页
        |    (PRI / IOPF stall)
        |                  +----------+
        +----------------- |  Device  |
                           | (NPU /   |
                           |   GPU)   |
                           +----------+
                                ^
                                | * 通过 SVA + 20-bit PASID
                                |   共享进程 VA
                                | * 不预先 pin；
                                |   按需 page-in
```

*演进方案：设备通过 IOMMU 走进程页表；翻译缺失时由设备发起缺页（PCIe ATS/PRI，或 ARM SMMUv3 stall），内核把页调入再继续。RAM 与 `ZONE_DEVICE` 之间可以双向迁移，设备 TLB 与 CPU 页表通过 `mmu_notifier` 保持一致。不再需要 pin，这些页就能进入 LRU 与回收。*

## 5. 演进方案解决了什么 / 没解决什么

### 解决了什么

- **「钉死的设备内存对 LRU 不可见」** —— `ZONE_DEVICE` 给每一页设备内存挂上 `struct page`，内核既有的迁移与 LRU 代码自然就能看到它们；以前的 pin 被 `mmu_notifier` 的同步取代（[Linux HMM 文档](https://www.kernel.org/doc/html/v5.0/vm/hmm.html)）。回收不再对设备那半边瞎。
- **「权重和 KV cache 占满设备侧」** —— 有了 HMM 双向迁移，冷 KV 页可以挪到压缩 RAM 或 swap 层（HBF / zswap），热 KV 留在设备。**谁该走、谁该留**这件事，从一次性的 `pin_user_pages` 调用变成由 LRU 引擎来决定（[A16f](../advanced/A16f-端侧KV-Cache管理方案.md)）。
- **「CPU↔设备共享要付拷贝或 handle 转手成本」** —— SVA 让两边看到同一个 VA，CPU 指针就是设备指针（[Linux SVA 文档](https://docs.kernel.org/arch/x86/sva.html)）。在 NVIDIA Grace Hopper 的 C2C 互联上，HMM 托管的 H2D/D2H 传输在同一负载下比 PCIe 直挂 H100 快了**最多 7 倍**（[NVIDIA, 2023](https://developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/)）。
- **「设备内存没法 per-app 计量」** —— 设备页有了 `struct page` 之后，原则上就能挂到 memcg + GPU cgroup 这条上游正在做的会计科目里（[A09 §6](../foundations/A09-设备内存全景.md)）。per-app 回收和配额变得有可能。

### 没解决什么

- **设备缺页延迟在量级上还是比 CPU 缺页差。** 实测 DMA 缺页比 CPU 缺页慢 **3×–80×**（[coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian)）；NVIDIA GPU UVM「远端缺页」在 **30–45 µs** 量级（[TACO 2024](https://dl.acm.org/doi/10.1145/3632953)）；即使在最适合统一物理内存的 AMD MI300A SoC 上，GPU 缺页也是 **16–18 µs** vs CPU 的 **9 µs**（[arXiv 2508.12743, 2025](https://arxiv.org/abs/2508.12743)）。NPU 一秒出几十个 token、单个 token 几十 µs，途中如果裸着穿过冷 KV 页缺页，推理路径会被拖慢。务实的答案是「智能预取 + 按需 pin + 冷数据才迁」，**不是「每次 miss 都老老实实缺页」**。
- **安全/保护堆没法迁移。** DRM、protected-content 这类路径出于隔离要求，OS 不允许重映射或读取（[A09 §3.4](../foundations/A09-设备内存全景.md)）。无论 SVA/HMM 怎么演进，这部分都会留在治理之外。
- **主机参与代价还是不低。** GPUVM ([arXiv 2411.05309, 2024](https://arxiv.org/abs/2411.05309)) 测出来即使页大小 64 KB，CPU 主机参与缺页处理的成本依然能到实际传输时间的 **7 倍**；该论文的思路是把更多的 PF 处理推到设备端，但这还不是一个跨平台的 OS 原语。
- **手机端没出货这套。** 上面这些在 Linux 服务器（PCIe 设备）和数据中心加速器（NVIDIA GPU + HMM、Intel DSA + SVA）上已经成熟；在 Android / iOS / HarmonyOS 上，部署的现实仍然是 dma-buf + pin。手机 NPU 是否走 SVA + PRI，没有公开文档（[A16e §5](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md)）。

## 6. 对比表

每个单元格都填数字、布尔，或 `n/a（原因）`；每一行都注明来源。**至少有一行是诚实的回归**——灵活性换来延迟代价，手机端落地也还没做。

| 维度 | 原方案：经典 pinned DMA | 演进方案：SVA + ATS/PRI + HMM | 改善 | 来源 |
|---|---|---|---|---|
| 稳态 DMA 延迟（首次触达之后） | 约 0 ns（无缺页，IOMMU TLB hit） | 约 0 ns（无缺页，ATS 缓存命中） | 不变 | ATS 规范；coIOMMU §2 |
| 冷页首次触达延迟 | n/a（事先 pin，没有缺页路径） | 16–45 µs（PRI / IOPF 缺页） | **−**（灵活性的代价） | [TACO 2024](https://dl.acm.org/doi/10.1145/3632953); [arXiv 2508.12743](https://arxiv.org/abs/2508.12743) |
| DMA 缺页 vs CPU 缺页 | n/a（不存在 DMA 缺页） | 比 CPU 缺页慢 3×–80× | **−**（已确认的折衷） | [coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian) |
| 16 GB 共享缓冲需 pin 的页 | 16 GB（整个缓冲） | 只需工作集（可变；极端情形可以 0） | 最多减少 **16 GB** 占用 | [Linux SVA 文档](https://docs.kernel.org/arch/x86/sva.html)（"without pinning all pages"） |
| LRU/MGLRU/DAMON 能看到的页 | 0（dma-buf 绕过 LRU） | 全部设备页（`ZONE_DEVICE` + `struct page`） | 定性：**从无到全** | [Linux HMM 文档](https://www.kernel.org/doc/html/v5.0/vm/hmm.html) |
| CPU↔设备迁移支持 | 没有 | 内核管的双向迁移 | 新能力 | [Linux HMM 文档](https://www.kernel.org/doc/html/v5.0/vm/hmm.html) |
| CPU↔设备指针共享 | 通过 dma-buf fd 走拷贝或 handle import | 零拷贝，共用 VA | 定性提升 | [AOSP dma-buf](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem); [SVA 文档](https://docs.kernel.org/arch/x86/sva.html) |
| 每系统的 SVA 并发上下文 | n/a（没有 PASID） | 约 1,048,576 (20-bit PASID) | 新能力 | [Linux SVA 文档](https://docs.kernel.org/arch/x86/sva.html) |
| 托管内存基准的 H2D/D2H 带宽 | 基线（PCIe 直挂 H100） | 最多 **快 7 倍**（Grace Hopper C2C HMM 路径） | **×7** | [NVIDIA, 2023](https://developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/) |
| 手机端（Android/iOS）出货状态 | 是（2010 年代起） | 否（仅为设计方案，[A16e](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md)） | **−1**（部署上的回归） | [A16e §5](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md) |

## 7. 一词概括

**Faultable**（可缺页） —— 演进方案的根本变化在于：IOMMU 的**设备侧**也能像 CPU 那样接收缺页（走 PRI / IOPF / SMMUv3 stall）。一旦设备可缺页，pin 就变成可选项，`ZONE_DEVICE` 撑起的迁移成为可能，手机回收路径里那块多 GB 的「设备 pinned 盲区」（比如 8 GB 手机上 Q4 权重 5 GB + 8K 上下文 KV cache 2 GB 左右）就能像普通 CPU 内存一样被治理——代价是单次缺页延迟比 CPU 缺页高出 **3×–80×**（[coIOMMU ATC '20](https://www.usenix.org/conference/atc20/presentation/tian)）。

## 8. 开放问题与说明

- **真实 Android 旗舰上 pinned dma-buf 占总 RAM 多少。** AOSP 和 Perfetto 都给了**怎么测**（`dumpsys meminfo`、`dmabuf_dump`），但没有公开数据集报告「Pixel/Galaxy 在 Y 负载下有 X% RAM 是 dma-buf pinned」。在公司内部做一次实测，会是对这套瓶颈论证最有力的证据。
- **手机 NPU 是否真走 SVA 没公开文档。** 出货 Android/iOS NPU 是走 SMMU + SVA + PRI，还是仍然 ION/dma-buf pin，公开材料里说不清。所以上面整套演进故事，**数据中心是现实，手机是设想**。
- **HMM 在手机 GPU/NPU 驱动里的采用情况。** Linux HMM 在 NVIDIA、AMD 独立 GPU 驱动以及 Intel DSA 上很成熟；在手机 GPU（Mali、Adreno）和专门 NPU（Hexagon、Apple Neural Engine、Google Tensor）上，公开资料很少。
- **Apple 的「Unified Memory」是物理共享，不一定是可分页迁移。** WWDC10686 文档了 CPU/GPU/NE 共享同一池 DRAM（[Apple, 2020](https://developer.apple.com/videos/play/wwdc2020/10686/)），但**没有**文档化 IP 之间的 LRU 式页迁移。要把营销术语和 OS 治理这两件事分开看。
- **HarmonyOS 的设备内存。** 公开材料停留在营销层（「超级内存管理」之类）。没有找到关于统一地址空间或设备缺页的一手技术文档。
- **缺页延迟数据基本都是服务器级。** 9–45 µs 这个区间来自 NVIDIA 独立 GPU 和 AMD MI300A SoC；**手机 NPU 在 SVA 下的缺页延迟没有公开实测**。
- **本地源镜像已通过 WebFetch 补齐**（不是原 HTML——WebFetch 工具返回的是模型抽取后的 Markdown）。保存在 [`sources/unified-device-memory/`](sources/unified-device-memory/) 下：SVA 内核文档（12 KB，完整正文）、HMM 内核文档（9 KB，完整正文）、LWN SVA 长文（2 KB —— *WebFetch 给的是缩略改写、不是原文*，引用以原 URL 为准），以及一份 `android-dmabuf-heaps.md` 替代文件（6 KB），讲同一个 ION → DMA-BUF heaps 过渡，因为 AOSP 上 `implement-dma-buf-gpu-mem` 这个 SPA 反复把图形总览页正文返回给抓取器，原页面没拉下来。每一条引用，**以原 URL 为准**最稳。

## 9. 参考资料

1. Linux 内核项目。(2024). *Shared Virtual Addressing (SVA) with ENQCMD*. [docs.kernel.org/arch/x86/sva.html](https://docs.kernel.org/arch/x86/sva.html). 本地副本：[`sources/unified-device-memory/sva-kernel-doc.md`](sources/unified-device-memory/sva-kernel-doc.md)。 —— "SVA doesn't require pinning pages for DMA"；PASID/ATS/PRI 依赖关系。
2. Linux 内核项目 / Jérôme Glisse 等。(2019). *Heterogeneous Memory Management (HMM)*. [www.kernel.org/doc/html/v5.0/vm/hmm.html](https://www.kernel.org/doc/html/v5.0/vm/hmm.html). 本地副本：[`sources/unified-device-memory/hmm-kernel-doc.md`](sources/unified-device-memory/hmm-kernel-doc.md)。 —— `ZONE_DEVICE`、双向迁移、`mmu_notifier`。
3. Arm Ltd. (2023). *SMMU Software Guide — Page Request Interface*. [developer.arm.com/documentation/109242/0100/Operation-of-an-SMMU/Page-Request-Interface](https://developer.arm.com/documentation/109242/0100/Operation-of-an-SMMU/Page-Request-Interface). —— PRI 队列，stall + Resume。
4. Arm Ltd. (2016–2022). *System Memory Management Unit Architecture Specification (IHI 0070, SMMUv3)*. [developer.arm.com/Architectures/System MMU Support](https://developer.arm.com/Architectures/System%20MMU%20Support). —— SMMUv3 权威规范。
5. Corbet, J. (2018). *Shared Virtual Addressing for the IOMMU*. LWN. [lwn.net/Articles/747230/](https://lwn.net/Articles/747230/). 本地副本：[`sources/unified-device-memory/lwn-sva-iommu.md`](sources/unified-device-memory/lwn-sva-iommu.md) —— *WebFetch 模型给的是缩略改写、不是原文，引用时请以原 URL 为准*。 —— 跨架构 SVA API 设计的长文。
6. Brucker, J.-P. (2020). *iommu: I/O page faults for SMMUv3*. LWN summary. [lwn.net/Articles/843885/](https://lwn.net/Articles/843885/). —— 给 SMMUv3 加 stall 与通用 IOPF handler。
7. Samsung Semiconductor. (2024). *Realizing ATS and PRI for Efficient Data Access in NVMe SSD*. [semiconductor.samsung.com/.../realizing-ats-and-pri-for-efficient-data-access-in-nvme-ssd-ep1/](https://semiconductor.samsung.com/news-events/tech-blog/realizing-ats-and-pri-for-efficient-data-access-in-nvme-ssd-ep1/). —— ATS+PRI 让 DMA 缓冲不必预先 pin。
8. Tian, K. 等。(2020). *coIOMMU: A Virtual IOMMU with Cooperative DMA Buffer Tracking*. USENIX ATC '20. [usenix.org/conference/atc20/presentation/tian](https://www.usenix.org/conference/atc20/presentation/tian). —— DMA 缺页比 CPU 缺页慢 3×–80×；论文方向是 smart pinning。
9. Nazaraliyev, M. & Sadredini, E. (2024). *GPUVM: GPU-driven Unified Virtual Memory*. arXiv:2411.05309. [arxiv.org/abs/2411.05309](https://arxiv.org/abs/2411.05309). —— 主机参与高达传输时间的 7×；GPUVM 在 latency-bound 负载上比 CUDA UVM 快最多 4×。
10. NVIDIA. (2023). *Simplifying GPU Programming for HPC with the NVIDIA Grace Hopper Superchip*. NVIDIA Developer Blog. [developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/](https://developer.nvidia.com/blog/simplifying-gpu-programming-for-hpc-with-the-nvidia-grace-hopper-superchip/). —— C2C 上的 HMM 托管 H2D/D2H 比 PCIe H100 快最多 7×。
11. Allen, T. & Ge, R. (2024). *Fine-grain Quantitative Analysis of Demand Paging in Unified Virtual Memory*. ACM TACO. [dl.acm.org/doi/10.1145/3632953](https://dl.acm.org/doi/10.1145/3632953). —— GPU UVM 远端缺页约 30–45 µs。
12. *Dissecting CPU-GPU Unified Physical Memory on AMD MI300A APUs*. (2025). arXiv:2508.12743. [arxiv.org/abs/2508.12743](https://arxiv.org/abs/2508.12743). —— 统一物理内存上 CPU PF 9 µs vs GPU PF 16–18 µs。
13. Apple Inc. (2020). *Explore the New System Architecture of Apple Silicon Macs (WWDC20 #10686)*. [developer.apple.com/videos/play/wwdc2020/10686/](https://developer.apple.com/videos/play/wwdc2020/10686/). —— 统一物理内存；LRU 级页迁移未做文档化。
14. Android 开源项目。(2021). *Implement DMA-BUF and GPU memory accounting in Android 12*. [source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem](https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem). 本地镜像**失败**（AOSP SPA 反复把图形总览页正文返回给抓取器，详见占位文件 [`sources/unified-device-memory/android-dmabuf-accounting.md`](sources/unified-device-memory/android-dmabuf-accounting.md)）。退而求其次保存了相邻文档 [`sources/unified-device-memory/android-dmabuf-heaps.md`](sources/unified-device-memory/android-dmabuf-heaps.md)（[source.android.com/docs/core/architecture/kernel/dma-buf-heaps](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)，讲的是同一个 ION→DMA-BUF heaps 过渡）。 —— GKI 2.0 用 dma-buf heaps 替换 ION；独立会计科目。
15. Google / Perfetto. (2024). *Debugging memory usage on Android — case studies*. [perfetto.dev/docs/case-studies/memory](https://perfetto.dev/docs/case-studies/memory). —— `dumpsys meminfo` 与 `dmabuf_dump` 流程。
16. Meta AI. (2024). *Llama 3.2: Revolutionizing edge AI and vision with open, customizable models*. [ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/](https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/). —— Llama 3.2 1B/3B 规格。
17. LMCache 项目。(2024). *KV Cache Size Calculator*. [lmcache.ai/kv_cache_calculator.html](https://lmcache.ai/kv_cache_calculator.html). —— 本文里 KV cache 容量的计算公式。
18. 本项目 A16e 锚点。[advanced/A16e-IOMMU统一内存与异构PF-LRU.md](../advanced/A16e-IOMMU统一内存与异构PF-LRU.md). —— 「统一设备内存在手机端」这套框架的项目内出处。

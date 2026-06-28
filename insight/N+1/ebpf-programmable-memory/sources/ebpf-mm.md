# eBPF 作为可编程内存策略的机制 — 源笔记

> 这些工作多源于服务器/数据中心，但提供的是「机制」——把内核内存路径上的策略点开放给运行时可加载的程序。
> 本调研把它们定位为**端侧可编程内存策略的实现手段**，而非数据中心场景本身。

## 来源 1：eBPF-mm（机制：缺页路径选页大小）
- 作者：Konstantinos Mores, Stratos Psomadakis, Georgios Goumas（希腊国立雅典理工大学 NTUA）
- 年份/出处：2024，ACM SRC@MICRO'24；arXiv 2409.11220
- URL: https://arxiv.org/abs/2409.11220
- 要点：
  - 在 Linux **缺页处理路径**新增 eBPF 挂钩点，由用户态 eBPF 程序决定该次缺页分配的**页大小**。
  - 支持 **4 KB / 64 KB / 2 MB** 三种尺寸（与 mTHP 尺寸谱对齐）。
  - 用 **DAMON** 剖析负载、识别热区，再据此让 eBPF 程序按区域选尺寸。
  - 服务器导向；端侧映射：与 mTHP「按区域而非系统级选尺寸」诉求完全一致。

## 来源 2：cachebpf（机制：页缓存淘汰/准入）
- 作者：Tal Zussman, Ioannis Zarkadas 等（Columbia University, IBM）
- 年份：2025，arXiv 2502.02750（SOSP'25 方向）
- 要点：
  - 5 个 eBPF 挂钩（init/eviction/admission/access/removal），实现**按 cgroup**定制淘汰策略（LFU/MRU/Hyperbolic）。
  - 仅改约 **210 行**核心页缓存代码；YCSB 吞吐 +37%，文件搜索吞吐 2×。
  - per-cgroup 元数据开销 0.4%–1.2% 内存、≤1.7% CPU。

## 来源 3：FetchBPF（机制：预取）
- 作者：Xuechun Cao 等，USENIX ATC 2024
- URL: https://www.usenix.org/conference/atc24/presentation/cao
- 可按负载部署 stride/Leap/ML 预取策略，零额外开销匹配内核内策略。

## 来源 4：PageFlex（机制：用户态委托分页策略）
- 作者：Yelam 等（Google, UCSD, UW），USENIX ATC 2025
- 策略委托给用户态，应用减速 **< 1%**。

## 来源 5：LPC 2024「Towards Programmable Memory Management with eBPF」
- 作者：Dimitrios Skarlatos, Kaiyang Zhao（CMU）
- URL: https://lpc.events/event/18/contributions/1932/
- 提出把 eBPF 挂钩扩展到缺页、回收、压缩、THP 提升、分层放置等内存路径。

## 来源 6：BPF struct_ops（上游机制基础）
- BPF_PROG_TYPE_STRUCT_OPS 允许用 BPF 实现内核接口（函数指针表）；
  SOSP'25 方向用 per-cgroup struct_ops + 新 kfunc 定制页缓存策略。
- eBPF 在最新 Android 设备上原生可用（userspace 编译、按触发注入内核）。

## 论文级判断
- 「可编程」是把 mTHP 选尺寸、DAMOS 回收/提升、LMKD/zRAM 阈值这些**策略面**开放给运行时程序的统一机制；
  端侧价值在于：不改内核、不重启即可按设备/负载/前后台状态切换策略。
- 现状：eBPF-mm/cachebpf/FetchBPF/PageFlex 多为研究原型，缺页与回收挂钩尚未合入 mainline；
  端侧已落地的可编程面目前主要是 DAMOS（mainline）与 userspace LMKD（PSI）。

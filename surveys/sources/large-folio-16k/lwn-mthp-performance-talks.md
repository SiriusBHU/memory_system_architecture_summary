# Two talks on multi-size transparent huge page performance (LWN)

来源 URL: https://lwn.net/Articles/974826/
抓取日期: 2026-06-25（WebFetch 抽取正文）
机构: LWN.net（报道 2024 LSFMM+BPF Summit）
年份: 2024
类型: 技术媒体 / 会议报道（含硬数字）

## Memcached 基准（Yang Shi，Ampere Altra ARM 服务器）

- **64KB mTHP（在更大基页系统上）**：每秒完成操作数提升 **约 20%**。
  > "about 20% improvement in the number of operations completed per second"
- **延迟下降 10–30%**（同配置）。
  > "10-30% decrease in latency"
- **64KB mTHP（在 4KB 基页上）**：无可测性能收益。

## 内核编译基准（Yang Shi）

- 与 Memcached 类似；64KB/4KB 配置显示 **约 5% 性能收益**，归因于「缺页减少」。

## mTHP 分配可靠性（Barry Song, Oppo）

（这是可用性指标，不是性能提升）

- 运行 1 小时后：约 50% mTHP 分配成功率
- 运行 2 小时后：因内存碎片，失败率 >90%
- 应用 TAO 补丁（order 4 / 64KB）后：成功率稳定在 50% 以上

—— 说明 mTHP 在长时间运行后受物理内存碎片制约，策略仍不成熟。

## 另：mTHP cover letter（LWN 954094, Ryan Roberts/ARM）

- 引用 NVIDIA John Hubbard：「某些负载有戏剧性的 10x 性能提升」。
  > "John Hubbard at Nvidia has indicated dramatic 10x performance improvements for some workloads"
- ARM64 两种 TLB 合并机制：架构性的「contiguous bit」与微架构的 HPA。
- 默认关闭，需 sysfs 显式开启（向后兼容）。

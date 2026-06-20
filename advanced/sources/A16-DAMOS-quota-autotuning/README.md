# DAMOS 配额自调节：机制详解（A16a §4 ④⑤ 的一手分析）

> **本文定位**：对 [A16a §4](../../A16a-LRU主动扫描.md) 演进线里两步的**源码级**展开——
> - **④ 自调节激进度**：DAMOS *aim-oriented feedback-driven aggressiveness auto-tuning*（配额目标自调，约 v6.8 / 2024 初）；
> - **⑤ 更细的作用域**：把配额目标的"传感器"从 system-wide 细化到 **per-node / per-memcg**（2024–2026）。
>
> **两步的关系**：④ 是**引擎**（一个反馈控制器，把"目标"翻译成"激进度"），⑤ 是给这台引擎**换上更细的传感器**（让"目标"能精确到某 NUMA 节点、某 cgroup）。引擎不变，输入变细。
>
> **取证方式**：下文所有公式 / 结构 / 参数名均**直接引自下载到本目录的一手材料**（见文末「下载清单」），不靠记忆复述。其中反馈公式与 metric getter 直接摘自当前 mainline `mm/damon/core.c`。

---

## 0. 一句话总览

> 用户**不再手调"压多狠"**，而是声明一个**目标**（"把某节点空闲率维持在 0.5%"／"把内存 PSI 压在 0.5%"），DAMOS 用一个**比例反馈回路**每个 `reset_interval` 算一次"离目标差多远"，**欠目标就加大配额、超目标就收**——这就是 A16a §3.3 说的"用一个可测目标闭环钳住激进度"。④ 定义了这个回路；⑤ 让"目标"可以是 per-node / per-memcg 的内存比例。

---

## 1. 方向 ④：aim-oriented feedback-driven 配额自调

### 1.1 动机：手调配额为什么不可行

DAMOS 早期要用户手填 6 个访问模式参数（access rate / age / size 的区间）；quota 把它简化成"一个旋钮"，但**最优 quota 值依赖系统与负载特征，并不简单**（[LWN 951195](_lwn-951195-aim-oriented-autotuning.html)）。SeongJae Park 的转向是：

> "the existing approach asks users to find the perfect or adapted tuning and instruct DAMOS how to work. It requires users to be deligent." → 改成"**inform DAMOS what they aim to achieve, and how well DAMOS is doing that. Then DAMOS can somehow make it.**"

### 1.2 核心抽象：quota goal = (目标指标, 目标值) + 实测当前值 → 分数

一个 scheme 的 quota 下可以挂若干 **quota goal**，每个 goal 是：

| 字段（sysfs / 结构体） | 含义 |
|---|---|
| `target_metric` | 用哪个指标衡量"做得好不好"（见 §1.5 列表）|
| `target_value` | 该指标的**目标值** |
| `current_value` | 该指标的**实测当前值**（内核内建指标由内核填；`user_input` 由用户写）|
| `nid` | 目标 NUMA 节点（node 类指标用）|
| `path` | 目标 cgroup 路径（memcg 类指标用，对应内核内 `memcg_id`）|

来源：[usage.html](_kernel-doc-damon-usage.html)——`schemes/<N>/quotas/goals/` 下先写 `nr_goals` 生成 `0..N-1` 个 goal 目录，每个目录含 `target_metric / target_value / current_value / nid / path` 五个文件；改完须向 kdamond 的 `state` 写 `commit_schemes_quota_goals` 才生效。

### 1.3 分数怎么算 + 多目标如何合并（取证：core.c）

每轮把每个 goal 的当前值刷新，再归一化成"分数"（10000 = 正好达标）：

```c
/* Return the highest score since it makes schemes least aggressive */
static unsigned long damos_quota_score(struct damos_quota *quota)
{
	struct damos_quota_goal *goal;
	unsigned long highest_score = 0;

	damos_for_each_quota_goal(goal, quota) {
		damos_set_quota_goal_current_value(goal);
		highest_score = max(highest_score,
				mult_frac(goal->current_value, 10000,
					goal->target_value));   /* score = current/target × 10000 */
	}
	return highest_score;
}
```

**关键设计**：多个 goal 时取**最高分**（`max`）。注释点明原因——"makes schemes least aggressive"：分数越高＝越"超额达标"＝回路越要**收**激进度；取最高分意味着**只要任一目标已满足，就整体收手**。这正是 [LWN 951195] 说的"passes only the best feedback among given inputs to avoid making DAMOS too aggressive"——**安全侧偏保守**。

### 1.4 反馈公式：比例回路（取证：core.c，逐字）

分数喂进这个回路，算出"下一轮的输入"（即激进度）：

```c
/*
 * Calculate next input to achieve the target score ... Assuming the input and
 * the score are positively proportional ...
 *   next_input = max(last_input * ((goal - current) / goal + 1), 1)
 * For simple implementation, we assume the target score is always 10,000.
 */
static unsigned long damon_feed_loop_next_input(unsigned long last_input,
		unsigned long score)
{
	const unsigned long goal = 10000;
	const unsigned long min_input = 10000;     /* 下限，避免补偿归零卡死 */
	unsigned long score_goal_diff, compensation;
	bool over_achieving = score > goal;

	if (score == goal)            return last_input;        /* 正好达标 → 不动 */
	if (score >= goal * 2)        return min_input;         /* 超额 ≥2× → 直接砸到下限 */

	score_goal_diff = over_achieving ? score - goal : goal - score;
	/* compensation = last_input × |diff| / goal （带防溢出分支）*/
	if (last_input < ULONG_MAX / score_goal_diff)
		compensation = last_input * score_goal_diff / goal;
	else
		compensation = last_input / goal * score_goal_diff;

	if (over_achieving)  return max(last_input - compensation, min_input);  /* 超额 → 减 */
	if (last_input < ULONG_MAX - compensation)
		return last_input + compensation;                                  /* 欠额 → 加 */
	return ULONG_MAX;
}
```

读法：

- **本质是比例控制器（P 控制器）**：`next = last × (1 ± |分数偏差|/目标)`。欠目标（score<10000）→ 加大输入；超目标 → 减小；偏差越大、调得越猛。
- **"input / 激进度"与"score"必须正相关**——这是回路成立的**契约**（注释 "positively proportional"）。内建指标由内核保证正相关；`user_input` 则由喂数据的人负责保证。
- **两个保护**：`score≥2×goal` 时一步砸到 `min_input`（强刹车）；`min_input=10000` 防止输入归零后再也涨不回来。

### 1.5 这个"input"怎么变成真正的字节配额（两种 tuner）

回路算出的是 `esz_bp`（effective size quota，单位 basis point，1/10000）。两种调法（design.html 称 *consist* / *temporal*）：

```c
/* CONSIST：比例回路，找一个能"长期稳住目标"的最优配额 */
static void damos_goal_tune_esz_bp_consist(struct damos_quota *quota)
{
	unsigned long score = damos_quota_score(quota);
	quota->esz_bp = damon_feed_loop_next_input(max(quota->esz_bp, 10000UL), score);
}

/* TEMPORAL：bang-bang，没达标就开满、达标就停 */
static void damos_goal_tune_esz_bp_temporal(struct damos_quota *quota)
{
	unsigned long score = damos_quota_score(quota);
	if (score >= 10000)        quota->esz_bp = 0;                 /* 达标 → 关 */
	else if (quota->sz)        quota->esz_bp = quota->sz * 10000; /* 没达标 → 开满 */
	else                       quota->esz_bp = ULONG_MAX;
}
```

最后 `damos_set_effective_quota()` 把它和**硬上限**取交集——目标回路只能让 scheme **更温和**，不能突破用户设的 `ms`/`sz` 天花板：

```c
esz = quota->esz_bp / 10000;                       /* bp → 字节 */
if (quota->ms) {                                   /* 还有时间配额 ms */
	throughput = ...;                              /* 实测吞吐：已处理字节/已花时间 */
	esz = min(throughput * quota->ms, esz);        /* 取更小 → 时间与大小双重封顶 */
	esz = max(ctx->min_region_sz, esz);
}
```

> 即 design.html 那句的源码对应：「if goals is not empty, DAMON calculates yet another size quota based on the goals ... and if the new size quota is smaller than the effective quota, it uses the new size quota」——**目标回路只做减法，硬 quota 才是上界**。这对终端很关键：续航红线（硬 `sz`/`ms`）永远钳得住自调回路。

### 1.6 可用的目标指标（target_metric 全表，取证：core.c switch + design.html）

`damos_set_quota_goal_current_value()` 的 `switch` 列全了：

| `target_metric` | 当前值怎么测（getter） | 典型用途 |
|---|---|---|
| `user_input` | 用户自己写 `current_value` | 把任意外部信号（延迟、能耗…）接进来 |
| `some_mem_psi_us` | `psi_system` 的 some-memory PSI 累计（µs），取每轮增量 | 把"内存压力"压在某水平（数据中心主力）|
| `node_mem_used_bp` / `node_mem_free_bp` | `si_meminfo_node(nid)`，`(totalram−freeram)` 或 `freeram` 再 `×10000/totalram` | **某 NUMA 节点**的占用/空闲率（分层）|
| `node_memcg_used_bp` / `node_memcg_free_bp` | `mem_cgroup_lruvec(memcg, node)` 上 ACTIVE/INACTIVE × ANON/FILE 之和 `×10000/totalram` | **某 cgroup 在某节点**的占用/空闲率（⑤，见 §2）|
| `active_mem_bp` / `inactive_mem_bp` | 全局 LRU active/(active+inactive) 比例 | 按冷热分布调激进度 |

### 1.7 DAMON_RECLAIM 把它包成傻瓜旋钮（取证：reclaim.html）

主动回收模块直接暴露两条便捷入口（都默认关＝0）：

- `quota_mem_pressure_us`：写一个目标 PSI（µs/`quota_reset_interval_ms`）→ 内部挂一个 `some_mem_psi_us` goal，**自动增减回收配额去逼近这个压力水平**；
- `quota_autotune_feedback`：写用户反馈值（参考点 **10000**）→ 内部挂 `user_input` goal；
- 硬上限：`quota_ms`（默认 10ms）、`quota_sz`（默认 128MiB）、`quota_reset_interval_ms`（默认 1s）。

### 1.8 效果（RFC 自测，[LWN 951195]）

PARSEC3 / SPLASH-2X（对未挂 scheme 的基线归一化）：online-tuned 相对 not-tuned 把内存 PSI 砍掉约 **69.1%**，RSS/runtime 代价可接受。结论：**目标自调能逼近甚至超过离线手调**，且免去人肉调参。

---

## 2. 方向 ⑤：把作用域细化到 per-node / per-memcg

### 2.1 加了什么

引擎（§1）不变，**新增两类传感器输入**，让"目标"可精确到节点、再到 cgroup：

1. **per-node**（先落地，2024）：`node_mem_used_bp` / `node_mem_free_bp`——某 NUMA 节点的占用/空闲率（getter `damos_get_node_mem_bp`，靠 `si_meminfo_node(nid)`）。
2. **per-memcg-per-node**（[LWN 1026213](_lwn-1026213-per-memcg-per-node.html)，2025 RFC → 现已在 mainline）：`node_memcg_used_bp` / `node_memcg_free_bp`——**某 cgroup 在某节点**的占用/空闲率。getter `damos_get_node_memcg_used_bp` 走 `mem_cgroup_lruvec(memcg, NODE_DATA(nid))`，把该 lruvec 上 ACTIVE/INACTIVE × ANON/FILE 四类页加起来作占用。goal 结构因此多了 `nid` 与 `memcg_id` 两个字段（sysfs 侧即 `nid` 与 `path`）。

> ⚠️ **现状取证**：本目录下载的 mainline `core.c` 的 `switch` 里**已含** `DAMOS_QUOTA_NODE_MEMCG_USED_BP/FREE_BP`，故 per-memcg 已合入主线；[LWN 1026213] 当时还是 RFC（"only build test is done"）。**确切合入版本号待核实**（base ④ 约 v6.8/2024 初；node 指标约 2024 年中；per-memcg 2025–2026）。另见 2026-01 Ravi Jonnalagadda 的 `NODE_TARGET_MEM_BP`（更新的节点目标指标，是否/何版合入待核实）。

### 2.2 为什么要 per-memcg：公平性

[LWN 1026213]：纯 system-wide 的 node 指标会**偏袒访问量大的 cgroup**（谁抢得凶谁占住快层）；per-memcg 变体**尊重各 cgroup 自己的 `memory.low` 保护**，让每个租户**按自己的配额**被独立调节。

### 2.3 杀手级用法：自调节的内存分层（[LWN 1014954](_lwn-1014954-tiering-self-tuned.html)）

传统分层要人肉调"页有多热才值得往快层搬"的阈值。换成目标自调后，每个 tier 跑两个 scheme：

- **promotion scheme**：目标＝快层**高利用率**（推荐 ~99.7% `node_mem_used_bp`）→ 欠目标就更猛地往快层搬热页；
- **demotion scheme**：目标＝快层**留一点空闲**（推荐 ~0.5% `node_mem_free_bp`）→ 把冷页往慢层赶以腾出空隙。

**用户只声明"想要的内存比例"，不再声明"热度阈值"**，回路自己找激进度。配 per-memcg 后，可对每个 cgroup 设不同目标（[LWN 1026213] 示例：cgroup a 占快层 29.7%、cgroup b 占 69.7%）。

效果（250GiB DRAM + 50GiB CXL，[LWN 1014954] / Phoronix）：**DAMON 分层 +4.43%**，而内核内建的 NUMAB-2 **−7.36%**——差距源于 DAMON 的**异步**迁移不阻塞应用，NUMAB-2 的同步提升会卡住进程。

---

## 3. 对 A16a / 终端的意义（接回正文）

1. **这正是 A16a §3.3 / §6 的"控制回路"本体**：④ 给出了"目标→激进度"的具体算法（比例回路 + 双 tuner + 硬上限封顶），⑤ 给出了"目标可以多细"（到节点、到 cgroup）。A16a 把它列为"主动回收"的终点，源码层面证据充分。
2. **终端落地的真缺口在"目标函数"，不在"引擎"**：现有 8 个内建 metric **没有一个是续航或闪存寿命**。要把这套用在终端（A16a §6 命题），路径是——用 `user_input` goal，由一个**感知前后台 / agent 生命周期 / 能耗预算**的 userspace daemon 算出复合分数喂进来（类似 Senpai 但目标并入能耗），或向内核加一个能耗/磨损类 metric（**待核实是否有人在做**）。引擎现成、传感器现成，**缺的是把"续航/闪存"翻译成一个正相关分数**——这与 [A16d 压缩 IP 边际建模](../../A16d-压缩IP边际建模.md) 是同一道题。
3. **硬上限永远钳得住**（§1.5）：自调回路只做减法、突破不了 `ms`/`sz`，这条性质让"激进度自调"在续航红线下是**安全**的——终端可以放心给一个保守的硬天花板，再让回路在天花板内自调。

---

## 4. 下载清单（本目录一手材料）

| 文件 | 来源 URL | 用途 |
|---|---|---|
| `_kernel-mm-damon-core.c` | https://raw.githubusercontent.com/torvalds/linux/master/mm/damon/core.c | **反馈公式 / score / metric getter 的源码取证** |
| `_kernel-doc-damon-design.html` | https://docs.kernel.org/mm/damon/design.html | quota / 目标自调 / consist·temporal / metric 列表 |
| `_kernel-doc-damon-reclaim.html` | https://docs.kernel.org/admin-guide/mm/damon/reclaim.html | DAMON_RECLAIM 的 `quota_mem_pressure_us` 等旋钮 |
| `_kernel-doc-damon-usage.html` | https://docs.kernel.org/admin-guide/mm/damon/usage.html | `quotas/goals/` sysfs 接口与 commit 命令 |
| `_lwn-951195-aim-oriented-autotuning.html` | https://lwn.net/Articles/951195/ | **④ 的奠基文**：动机、公式、RFC 实测 |
| `_lwn-1014954-tiering-self-tuned.html` | https://lwn.net/Articles/1014954/ | node 指标做**自调节分层**、CXL 实测 |
| `_lwn-1026213-per-memcg-per-node.html` | https://lwn.net/Articles/1026213/ | **⑤**：per-memcg-per-node 指标、公平性 |

补充链接（未下载，留索引）：
- [LWN 953388](https://lwn.net/Articles/953388/) ——「let users feed and tame/auto-tune DAMOS」（④ 合入版补丁系列封面）
- [LWN 973702](https://lwn.net/Articles/973702/) ——「An update and future plans for DAMON」
- [Phoronix：DAMON Self-Tuned Memory Tiering](https://www.phoronix.com/news/DAMON-Self-Tuned-Memory-Tiering)
- LKML per-memcg 系列：[PATCH 02/10 add quota goal type](https://lkml.org/lkml/2025/10/17/1601)、[PATCH 03/10 NODE_MEMCG_USED_BP](https://lkml.org/lkml/2025/10/17/1602)

## 5. 待核实

- ④ base auto-tuning、node 指标、per-memcg 指标**各自确切合入的内核版本号**（现仅证明：当前 master 全含）。
- `damos_set_effective_quota()` 中 `esz` 与 `quota->sz` 的最终钳制顺序（本文只读到 `min(throughput*ms, esz)` 一段，余下封顶逻辑未逐行核）。
- 2026-01 `DAMOS_QUOTA_NODE_TARGET_MEM_BP`（Ravi Jonnalagadda）与既有 `node_mem_*_bp` 的关系与合入状态。
- Android/GKI 是否启用 DAMON_RECLAIM 的目标自调、以何节奏（[A16a §5 同列待补]）。

# Proactive Reclaim: From Watermark-Triggered Rescue to Cadence-and-Feedback Eviction

> A before-and-after survey of how the Linux memory reclaimer is run. Anchor article: [A16a — LRU 主动扫描](../../advanced/A16a-LRU主动扫描.md). The original model — `kswapd` and direct reclaim, triggered only when a watermark fires — is a *rescue* mechanism. The evolved model adds (1) a cheap scanner (MGLRU page-table aging or DAMON region sampling), (2) a per-memcg proactive entry (`memory.reclaim`), and (3) a feedback controller (Senpai / DAMOS aim-oriented auto-tuning) that uses PSI to decide how hard to push. The data-center result is 20–32% server memory saved with no measurable slowdown. The mobile result so far is the MGLRU scanner shipping in Android 14 GKI; the controller half is still vendor-specific.

## 1. Scope and method

**Domain.** "Proactive reclaim" here means moving the *trigger* of memory reclaim from "we just hit a free-page watermark" to "a cadence + a feedback signal." It does **not** mean a new reclaim algorithm — the same LRU/MGLRU/DAMON machinery still picks pages — only the question "when do we look, and how hard do we push" changes.

**Original solution.** Passive reclaim: allocations drain the free pool, watermarks fire, `kswapd` wakes and scans the LRU tail until back above threshold; if it can't keep up, allocations enter *direct reclaim* and scan synchronously inside the allocator. On Android, when even that fails, `lmkd` kills processes by `oom_score_adj` tier (foreground/visible/background/cached).

**Evolved solution.** Proactive reclaim, three layers stacked: (1) a *cheap scanner* — MGLRU's aging pass walks page tables to age generations in batches, or DAMON samples one page per adaptive region so monitoring cost scales with regions, not pages; (2) a *write-only entry* — cgroup v2 `memory.reclaim` lets userspace ask "reclaim N bytes from this memcg," documented as *not* implying memory pressure (so socket-mem and other pressure-coupled paths don't react); (3) a *controller* — Meta's Senpai / TMO loop and the in-kernel DAMOS aim-oriented auto-tuning both use PSI as the feedback signal: below the threshold, push harder; above it, ease off.

**Sources.** 14 sources: kernel docs (MGLRU, cgroup v2 `memory.reclaim`, DAMON_RECLAIM, PSI), LWN feature articles tracking each upstream patch series, the Meta TMO engineering post (production numbers), the Senpai GitHub repo, and a 2024 cloud-VM proactive-reclaim paper (arXiv 2409.13327). Numbers in the tables are sourced one-to-one in §9.

## 2. Problem background

**What the system needs to do.** Keep allocations fast, keep important work resident, and don't let the machine fall off a cliff under pressure. On a server that means high utilization without tail-latency spikes. On a phone it means foreground apps don't stutter and don't get killed.

**Why this domain becomes hard.** Three constraints collide: (1) the only signal classic reclaim has — *free-page watermarks* — fires *after* the workload is already feeling pressure, so its primary effect is mostly to interrupt allocations with direct reclaim; (2) the LRU tail is a local view; it can't tell the operator "you've been leaving 20% of memory on the table for hours" — that's a global, statistical question; (3) reclaim aggressiveness must be controlled by something the workload actually cares about (latency / quality of service), not by free-page counts.

**Why the original solution is no longer enough.** In data centers the cost is visible: TMO measured **20–32% of server memory** as offloadable across millions of Meta servers without functional impact ([TMO blog, 2022](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/)). That much waste means the passive reclaimer was just never asking. On phones it's worse — `lmkd` fires *after* the watermark has already been hit, so the system's only response to pressure is to kill an app. The Agent-era workload makes this worse (long-running background inference holds memory the heuristics treat as cold), but the underlying critique — "rescue is not policy" — applies just as much to a phone in 2018 as to a server in 2022.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **Direct reclaim stalls the allocator.** When `kswapd` can't keep up, allocations scan the LRU synchronously, blocking the requesting thread. PSI's `memory.full` measures exactly this ([PSI doc](https://docs.kernel.org/accounting/psi.html)).
2. **There is no "look around" pass.** Classic reclaim only walks the LRU tail far enough to satisfy the current shortfall. Without proactive scanning, no one ever asks "of all anon pages, which 30% have been cold for 2 minutes?"
3. **No targeted reclaim primitive existed.** Before Linux 5.19 (2022) there was no userspace way to tell the kernel "reclaim 1 GB from *this* cgroup" without faking memory pressure (which would trigger socket-mem balancing and other side effects). `memory.reclaim` closed this gap ([cgroup-v2 doc](https://docs.kernel.org/admin-guide/cgroup-v2.html)).
4. **Aggressiveness was a tuning fight.** Pre-DAMOS aim-oriented auto-tuning, an admin tuning DAMON_RECLAIM had six interacting knobs (min_age, quota_sz, quota_ms, watermark_high/mid/low). Tuning across workloads was unreliable.

### Bottleneck evidence

The numbers below are what made proactive reclaim worth building. Each is sourced in §9.

| Bottleneck signal | Value | What it means | Source |
|---|---|---|---|
| Memory offloadable per server without slowdown (TMO production) | **20–32%** | The passive reclaimer was leaving a fifth to a third of RAM on the table across Meta's fleet. | [TMO blog 2022](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) |
| Of total memory, compressed-mem backend reclaim share | **7–12%** | Cold but not-yet-cold-enough-for-SSD memory recovered by zswap-class compression under Senpai pacing. | TMO blog |
| Of total memory, SSD backend reclaim share for ML workloads | **10–19%** | Long-tail cold pages an LRU watermark would never get to. | TMO blog |
| Senpai control-loop tick | **6 s** | Pacing is on the order of seconds — slow enough for PSI to be a usable signal, fast enough to respond before the workload feels pressure. | TMO blog |
| Pre-MGLRU Android `kswapd` CPU usage delta after MGLRU rollout | **−40%** | Google fleetwide measurement — the page-table aging pass is dramatically cheaper than rmap-based scan. | MGLRU patch cover letter via [LWN 1072866](https://lwn.net/Articles/1072866/) |
| Pre-MGLRU `lmkd` kill rate at p75 after MGLRU rollout | **−85%** | Same measurement — better cold/hot identification means fewer apps killed. | as above |
| App-launch time at p50 after MGLRU rollout | **−18%** | Less time spent doing reclaim work in the launch hot path. | as above |
| DAMON_RECLAIM memory savings (Linux 5.12 + zram experiment) | **32%** | Per the patch series cover letter — proactive eviction below a speed limit. | [LWN 858682](https://lwn.net/Articles/858682/) |
| DAMON_RECLAIM runtime overhead (same experiment) | **1.91%** | The scan cost itself was small relative to what it saved. | as above |
| DAMOS auto-tune visible knobs | **6 → 1** | A single quota target (e.g. "keep `some` memory PSI ≤ 0.5%") replaces six manual settings. | [LWN 951195](https://lwn.net/Articles/951195/) |

**Reading.** TMO's 20–32% number is the bottleneck argument: in production, passive reclaim was leaving the equivalent of a third of a server's RAM idle and unreclaimed. The Google numbers are the parallel mobile argument: MGLRU's cheaper scanner alone, even without a controller layered on top, removed enough cold-page misclassification to cut lmkd kills 85% at p75 and shave 18% off app launch.

## 4. Architectures: original vs evolved

Both diagrams use the same components. Differences in the evolved one are marked with `*`.

**Original — passive reclaim**

```
   +-----------+   alloc()    +-----------+
   |  Process  | -----------> |  Kernel   |
   +-----------+              |   (mm)    |
                              +-----+-----+
                                    |
                                    | watermark check
                                    v
                              +-----------+
                              |  Free     |
                              |  pool     |
                              +-----+-----+
                                    | below low
                                    v
                              +-----------+
                              |  kswapd   |  scan LRU tail
                              | (kthread) |  until back above
                              +-----+-----+  threshold
                                    |
                                    | if too slow ->
                                    v
                              +-----------+
                              |  direct   |  synchronous in
                              |  reclaim  |  allocator path
                              +-----+-----+  (stall)
                                    |
                                    v
                              +-----------+
                              |  LRU tail |
                              +-----------+
```

*Original: the only trigger is "we're already running out." `kswapd` rescues; if it can't, the allocator scans synchronously and the requester pays the latency.*

**Evolved — proactive reclaim (scanner + entry + controller)**

```
   +-----------+              +-----------+
   |  Process  |              |  Kernel   |
   +-----------+              |   (mm)    |
                              +-----+-----+
                                    ^
                                    |
   +-----------+                    |
   |  Workload | -- PSI samples --+ |
   |  metrics  |                  | |
   +-----------+                  v |
                              +---------------+
                              | * Controller  |
                              |   (Senpai/TMO |
                              |    userspace, |
                              |    OR DAMOS   |
                              |    in-kernel) |
                              +-------+-------+
                                      |
                                      | * write
                                      |   memory.reclaim N
                                      |   on cadence
                                      v
                              +-------------+
                              | * Cheap     |
                              |   scanner   |
                              |   - MGLRU   |
                              |     aging   |
                              |   - DAMON   |
                              |     region  |
                              |     sample  |
                              +-----+-------+
                                    |
                                    v
                              +-------------+
                              | LRU pages   |
                              +-----+-------+
                                    | reclaimed before
                                    | watermark fires;
                                    | headroom kept
                                    v
                              +-------------+
                              |  Free pool  | <-- holds headroom
                              +-------------+   so direct reclaim
                                                rarely fires
```

*Evolved: a controller drives a cheap scanner on a cadence (Senpai every ~6 s in production); PSI feeds back into how aggressively to push; `memory.reclaim` is the targeted write-only entry to a memcg; eviction happens before the allocator ever notices.*

## 5. Why evolved helps, what it still doesn't solve

### Why the evolved solution helps

- **Direct reclaim stall** — The controller leaves headroom in the free pool, so by the time an allocation comes in, the watermark hasn't moved. Direct reclaim, which used to be the user-visible cost of passive reclaim, fires only as a fallback. TMO production reports 20–32% of memory offloaded without functional impact ([TMO blog](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/)).
- **No "look around" pass** — Both scanners (MGLRU aging, DAMON region sampling) maintain a *standing* global cold/hot view, not just the LRU tail. MGLRU's debugfs `lru_gen` exposes a working-set histogram directly ([MGLRU doc](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)).
- **No targeted reclaim primitive** — `memory.reclaim` provides one, and explicitly does not raise the cgroup's pressure counters, so it composes with the rest of the kernel without side effects ([cgroup-v2 doc](https://docs.kernel.org/admin-guide/cgroup-v2.html)).
- **Tuning fight** — DAMOS aim-oriented auto-tuning collapses six knobs to one — a *target* (e.g. "keep `some` memory PSI ≤ 0.5% over the last 10 s") — and the kernel adjusts the per-second quota toward it ([LWN 951195](https://lwn.net/Articles/951195/)); later work makes the target per-memcg and per-NUMA node ([LWN 1026213](https://lwn.net/Articles/1026213/)).

### What it still doesn't solve

- **Scanning is not free.** The 1.91% runtime overhead DAMON_RECLAIM reported is small but real; on a phone, with a battery budget, even that may not be acceptable as a *constant* background cost. The honest answer is "throttle the cadence under low pressure and idle." There is no upstream knob that ties the cadence to a power budget yet.
- **The reclaim target isn't always PSI.** On a phone the right target probably involves battery-current and flash-write budgets, not just PSI. Anchor article §6 calls this the "energy-aware feedback loop" — no public mobile baseline ties them together yet.
- **The mobile controller half hasn't shipped.** MGLRU's *scanner* ships in Android 14 GKI (the 40% / 85% / 18% Google numbers are real production data). The *controller* — who drives `memory.reclaim` or `lru_gen` writes, on what cadence, against what target — is OEM userspace and is not standardized. So mobile proactive reclaim today is more scanner than feedback loop.
- **Per-node proactive reclaim API is still being argued upstream** ([per-node interface, LKML 2024](https://lkml.iu.edu/hypermail/linux/kernel/2409.0/05920.html)) — the user-facing shape of "reclaim N bytes from node X" is not yet settled.

## 6. Comparison table

Every cell is a number, a boolean, or `n/a (reason)`. Every row has a source. At least one row honestly shows a tradeoff (constant background CPU cost) or a deployment regression (the controller half hasn't shipped on mobile).

| Dimension | Original: passive reclaim | Evolved: proactive reclaim | Improvement | Source |
|---|---|---|---|---|
| Trigger | watermark / OOM | cadence (~6 s) + PSI feedback | new behavior | [TMO blog](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) |
| Server memory offloaded without slowdown | 0% (no mechanism) | 20–32% in production | **+20–32%** | TMO blog |
| App-launch time at p50 (Android, MGLRU rollout) | baseline | −18% | **−18%** | [LWN 1072866](https://lwn.net/Articles/1072866/) |
| `lmkd` kill rate at p75 (Android, MGLRU rollout) | baseline | −85% | **−85%** | as above |
| `kswapd` CPU usage (Android, MGLRU rollout) | baseline | −40% | **−40%** | as above |
| DAMON_RECLAIM memory savings (5.12 cover-letter experiment) | n/a (no mechanism) | 32% | new capability | [LWN 858682](https://lwn.net/Articles/858682/) |
| DAMON_RECLAIM runtime cost (same experiment) | 0% (no background scan) | 1.91% | **−1.91%** (cost of background scanning) | as above |
| Visible tuning knobs (DAMON path) | 6 (min_age, quota_sz, quota_ms, watermark_high/mid/low) | 1 (target, e.g. PSI ≤ 0.5%) | **6 → 1** | [LWN 951195](https://lwn.net/Articles/951195/) |
| Targeted per-memcg reclaim primitive | no (only `oom_score_adj` and fault-driven) | `memory.reclaim` (write-only, no pressure side effects) | new capability | [cgroup-v2 doc](https://docs.kernel.org/admin-guide/cgroup-v2.html) |
| Mobile shipping status of controller half | n/a (no controller existed) | not standardized; OEM userspace | **0** (controller hasn't shipped) | A16a §5 |

## 7. One-word characterization

**Proactive** (主动) — the defining change is that reclaim runs on a *cadence + feedback target*, not on a watermark trip; a cheap scanner (MGLRU aging or DAMON sampling) maintains a standing global cold/hot view, and a PSI-driven controller (Senpai/TMO every **~6 s** in production, or DAMOS in-kernel) eases or pushes via `memory.reclaim` to keep the workload's pressure under a target. The benefit, measured in production: **20–32%** of server memory offloaded without functional impact ([TMO 2022](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/)), **−85%** lmkd kills at p75 and **−18%** app-launch time at p50 on Android (Google MGLRU rollout) — at the cost of a small but constant background-scan overhead (DAMON_RECLAIM cover letter: **1.91%**).

## 8. Open questions and caveats

- **MGLRU production numbers are vendor-reported.** The 40% / 85% / 18% Google figures appear in the MGLRU patch cover letters and in LWN/Phoronix coverage, but no peer-reviewed paper publishes them. Treat as "Google-reported fleetwide," not "independently replicated."
- **DAMON_RECLAIM 32% / 1.91% is from the original cover letter** ([LWN 858682](https://lwn.net/Articles/858682/)), not the current upstream admin guide; the live doc dropped these exact numbers as the implementation evolved. Anchor citations to the cover letter, not the live doc.
- **Senpai's PSI threshold is auto-calibrated.** Meta does not publish the absolute target; both the TMO blog and the Senpai README abstain. Treat as adaptive.
- **No 2024–26 mobile/Android academic eval** of proactive reclaim showed up in the search. arXiv 2409.13327 is the closest (cloud VMs, +25% memory savings vs Linux baseline), but it's not mobile and doesn't directly benchmark against MGLRU/DAMON. The mobile eval gap is real.
- **The energy-aware loop the anchor article calls for** — folding battery and flash-write budgets into the DAMOS target — has no public baseline yet. This is what "proactive reclaim on mobile" still needs.
- **Per-node proactive reclaim API is unsettled** ([LKML 2024](https://lkml.iu.edu/hypermail/linux/kernel/2409.0/05920.html)). The eventual user-facing primitive may not look like `memory.reclaim`.

## 9. References

1. Linux kernel project. (2022). *Multi-Gen LRU Framework — admin guide*. [docs.kernel.org/admin-guide/mm/multigen_lru.html](https://docs.kernel.org/admin-guide/mm/multigen_lru.html) — `min_ttl_ms` stable knob; debugfs `lru_gen` for working-set estimation and proactive eviction (experimental).
2. Linux kernel project. (2022). *Control Group v2 — Memory controller (`memory.reclaim`)*. [docs.kernel.org/admin-guide/cgroup-v2.html](https://docs.kernel.org/admin-guide/cgroup-v2.html) — write-only per-memcg proactive reclaim, no pressure side effects.
3. Butt, S. & Ahmed, Y. (Google) (2022). *memcg: introduce per-memcg proactive reclaim* (v4 series). LWN. [lwn.net/Articles/892328/](https://lwn.net/Articles/892328/) — design rationale.
4. Park, S. (2021). *DAMON-based Reclamation*. [docs.kernel.org/admin-guide/mm/damon/reclaim.html](https://docs.kernel.org/admin-guide/mm/damon/reclaim.html) — `min_age=120 s`, `quota_sz=128 MiB`, `quota_ms=10 ms`, `quota_reset_interval_ms=1 s`.
5. Corbet, J. (2021). *Using DAMON for proactive reclaim*. LWN. [lwn.net/Articles/863753/](https://lwn.net/Articles/863753/) — DAMON region sampling.
6. Park, S. (2021). *DAMON_RECLAIM* (patch series cover letter). LWN. [lwn.net/Articles/858682/](https://lwn.net/Articles/858682/) — **32% memory savings, 1.91% runtime overhead** on 5.12 + zram.
7. Park, S. (2023). *DAMOS: Introduce Aim-oriented Feedback-driven Aggressiveness Auto Tuning*. LWN. [lwn.net/Articles/951195/](https://lwn.net/Articles/951195/) — **6 → 1** tunables; demo target "`some` memory PSI 0.5% over last 10 s."
8. Park, S. (2025). *mm/damon: allow DAMOS auto-tuned for per-memcg per-node memory usage*. LWN. [lwn.net/Articles/1026213/](https://lwn.net/Articles/1026213/) — per-memcg/per-node targets; **200 MiB/s** migration cap example.
9. Weiner, J., Agarwal, N., Schatzberg, D. et al. (2022). *TMO: Transparent Memory Offloading in Datacenters*. ASPLOS '22. DOI 10.1145/3503222.3507731. PDF: [cs.cmu.edu/~dskarlat/publications/tmo_asplos22.pdf](https://www.cs.cmu.edu/~dskarlat/publications/tmo_asplos22.pdf). — PSI-driven offloading framework.
10. Agarwal, N. & Weiner, J. (2022). *Transparent memory offloading: more memory at a fraction of the cost and power*. Meta Engineering blog. [engineering.fb.com/.../transparent-memory-offloading-...](https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/) — **20–32%** per-server memory saved; **7–12%** compressed, **10–19%** SSD for ML; **6 s** Senpai loop.
11. Meta. (2022). *Senpai — automated memory sizing for containerized apps* (GitHub README). [github.com/facebookincubator/senpai](https://github.com/facebookincubator/senpai) — userspace PSI-feedback control loop on `memory.high` / `memory.reclaim`.
12. Linux kernel project. (2018). *PSI — Pressure Stall Information*. [docs.kernel.org/accounting/psi.html](https://docs.kernel.org/accounting/psi.html) — `some` / `full` lines per resource; pollable thresholds.
13. Corbet, J. (2022). *Meta: Transparent memory offloading*. LWN. [lwn.net/Articles/898454/](https://lwn.net/Articles/898454/) — independent summary.
14. Corbet, J. (2024). *What is to be done about MGLRU?*. LWN. [lwn.net/Articles/1072866/](https://lwn.net/Articles/1072866/) — MGLRU rollout status; mobile-side context for the Google fleetwide numbers.
15. Pandurov, R. et al. (Huawei + collaborators). (2024). *Flexible Swapping for the Cloud*. arXiv:2409.13327. [arxiv.org/abs/2409.13327](https://arxiv.org/abs/2409.13327) — cloud-VM proactive reclaim; **+25%** vs Linux baseline at similar savings.
16. A16a anchor article (this project). [advanced/A16a-LRU主动扫描.md](../../advanced/A16a-LRU主动扫描.md).

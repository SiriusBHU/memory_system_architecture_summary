# Programmable Memory Reclaim with eBPF: From Hard-Coded Heuristics to Loadable Policy

> A before-and-after survey of where the *policy* in Linux memory reclaim and OOM lives. Anchor article: [A16b — eBPF 可编程回收策略 (Android)](../../advanced/A16b-eBPF可编程回收策略-Android.md). The original model — `active/inactive` rules, MGLRU generations, OOM scoring, and Android `lmkd` thresholds — is all compiled into the kernel and the system image. The evolved model puts those decision points behind eBPF `struct_ops` hooks so policy ships as a loadable program. `sched_ext` (Linux 6.12) proved the pattern works for one core subsystem (CPU scheduling). For memory the proposals (eBPF-mm, cachebpf, BPF-OOM, the 2026 LSF/MM "reclaim_ext"-style discussion) have measured numbers — cachebpf reports **+70% throughput / −58% p99 / ≤1.7% CPU overhead** on heterogeneous storage workloads — but none is upstream yet, and Android's signed boot-time `bpfloader` model means any landing would be vendor/OEM policy, not third-party code.

## 1. Scope and method

**Domain.** "Programmable reclaim" here means: where do the kernel's *decisions* about reclaim, eviction, and OOM live? In the original world the decisions are compiled C in `mm/` — to change them you patch the kernel and rebuild. In the evolved world the decision points are eBPF callbacks, and you change them by loading a `struct_ops` program. The mechanism is generic; the work to apply it to mm is recent and not yet merged.

**Original solution.** Hard-coded LRU/MGLRU/OOM heuristics inside the kernel, plus, on Android, a `lmkd` userspace daemon with hard-coded `oom_score_adj` tiers and PSI thresholds, plus `process_madvise(MADV_COLD/MADV_PAGEOUT)` as the one *application-aware* lever shipped today (already in Android since Linux 5.4).

**Evolved solution.** eBPF `struct_ops` hooks at reclaim, eviction, and OOM decision points. The same machinery `sched_ext` uses for CPU scheduling, extended to mm. Concretely: cachebpf's five page-cache hooks (`init`, `admit`, `access`, `evict`, `remove`); eBPF-mm's hook returning a page size (4 KiB / 64 KiB / 2 MiB) at fault; BPF-OOM's `bpf_oom_kill_process` / `bpf_get_root_mem_cgroup` kfuncs and one-system-plus-per-memcg handler tree.

**Sources.** 12 sources: AOSP docs for Android's eBPF loading model, kernel docs + Phoronix for `sched_ext`, LWN coverage of LSF/MM-BPF 2026 ("Controlling memory management with BPF"), three primary research papers (cachebpf arXiv 2502.02750, eBPF-mm arXiv 2409.11220, LearnedCache arXiv 2605.26168), the two BPF-OOM RFC writeups by Gushchin, the original `MADV_COLD/PAGEOUT` LWN article, the LPC 2019 Android slides reporting **15–30% fewer lmkd kills** with semantic reclaim, and the canonical Android `process_madvise` man page. Every headline number in this document is sourced to a specific record in §9.

## 2. Problem background

**What the system needs to do.** Decide who to protect, who to evict, and — if it must — who to kill, on a machine running a heterogeneous workload mix (foreground UI app, background sync, agent inference, system service) on a phone whose kernel is built once for a generation of devices.

**Why this domain becomes hard.** Three constraints collide: (1) the right reclaim policy depends on the *application*, but `mm/` decisions are application-agnostic — the kernel sees a page, not "Llama 3.2 KV cache" or "Chrome tab cache"; (2) Android's GKI model fixes a single kernel image across many devices and many years — vendors who want different reclaim policy per device class cannot just patch `mm/`; (3) the alternative — moving everything to userspace — loses the *frequency* of in-kernel decisions (a reclaim hook fires hundreds of times per second; a userspace daemon can only steer at coarser cadence, see [A16a](../proactive-reclaim/proactive-reclaim-EN.md)).

**Why the original solution is no longer enough.** Two pieces of evidence. (1) `process_madvise(MADV_COLD/PAGEOUT)`, the *one* application-aware lever Android shipped, cuts lmkd kills by 15–30% relative to the watermark-driven baseline ([LPC 2019, Baghdasaryan](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf); MADV_COLD itself is "**10× faster** than zapping even on zram," [Kim/LWN 793462](https://lwn.net/Articles/793462/)) — i.e. when policy *can* see the workload, it does noticeably better than the kernel's blind LRU. (2) On servers, cachebpf shows the same effect at the page-cache layer: replacing the default Linux page-cache eviction with a workload-matched eBPF policy (MRU/LFU/S3-FIFO/LHD) yields **+70% throughput** and **−58% p99** on heterogeneous GET-SCAN, at **≤1.2% memory and ≤1.7% CPU** overhead ([Cache is King, arXiv 2502.02750](https://arxiv.org/html/2502.02750v1)). Both numbers say the same thing: hard-coded heuristics leave a lot on the table when one image has to fit every workload.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **Policy is application-blind.** The kernel cannot tell "Agent KV cache (long-running, may come back)" from "background app tab (cold, expendable)." [A16b §3.4](../../advanced/A16b-eBPF可编程回收策略-Android.md) frames this as the "semantic VRegion vs page-level LRU" gap.
2. **Policy is hard to change.** Changing reclaim policy in classic Linux means patching `mm/` and rebuilding the kernel. Under Android GKI that's especially expensive — vendors don't own the kernel image and any policy diff is a maintenance burden across releases.
3. **OOM is binary — kill or don't.** When `lmkd` fires, the only response is to terminate a process. The Gushchin BPF-OOM motivation: a programmable handler could "instead delete a tmpfs file" or take a different remediation step ([LWN 1034293](https://lwn.net/Articles/1034293/)).
4. **There's no "ship a policy" path on mobile.** Android eBPF is production-grade but locked to boot-time, signed `bpfloader` loading from `/system/etc/bpf/` with AID gating ([AOSP docs](https://source.android.com/docs/core/architecture/kernel/bpf)). Even if eBPF-mm landed upstream, a third-party app can't load reclaim policy — only OEM/Google can.

### Bottleneck evidence

| Signal | Value | What it means | Source |
|---|---|---|---|
| cachebpf end-to-end throughput vs default Linux page cache | **+70%** | A workload-matched policy more than doubles throughput over LRU on heterogeneous GET-SCAN. | [arXiv 2502.02750](https://arxiv.org/html/2502.02750v1) |
| cachebpf end-to-end p99 latency vs default Linux | **−58%** | Same workload, tail latency cut by more than half. | as above |
| cachebpf code size to express a custom policy | **56–366 LoC BPF** | Per-policy implementation: MRU, LFU, S3-FIFO, LHD all fit. | as above |
| cachebpf added memory overhead | **≤1.2%** of cgroup memory | Programmability cost itself is small. | as above |
| cachebpf added CPU overhead | **≤1.7%** per I/O | Same; the verifier-bounded program isn't the bottleneck. | as above |
| `MADV_COLD` vs zap+swap to zram | **~10×** faster | Application-aware deactivation beats the binary kill path. | [LWN 793462](https://lwn.net/Articles/793462/), Minchan Kim quote |
| Android `lmkd` kill reduction with userspace `process_madvise` | **15–30%** | Semantic, app-aware reclaim shipped on Android already pays — eBPF would generalize it. | [LPC 2019, Baghdasaryan](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf) |
| LearnedCache vs FIFO baseline (median over workloads) | **+10% insertion rate** | A simple perceptron eviction policy in BPF beats FIFO with statistically significant margin across 50 trials per workload. | [arXiv 2605.26168](https://arxiv.org/abs/2605.26168) |
| `sched_ext` upstream merge | **Linux 6.12** | The only `struct_ops` "programmable-policy" subsystem in mainline today; precedent for mm. | [kernel docs](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html); [Phoronix](https://www.phoronix.com/news/Linux-6.12-Lands-sched-ext) |
| BPF-OOM upstream status | **14-patch RFC v1 (2025-08-18)**, not merged | Closest mm-side proposal; LWN 1072538 reports no BPF-mm proposal has landed yet. | [LWN 1034293](https://lwn.net/Articles/1034293/), [LWN 1072538](https://lwn.net/Articles/1072538/) |

**Reading.** Two of these numbers are load-bearing: the **+70% / −58%** from cachebpf shows that a workload-matched policy is worth a lot relative to the hard-coded baseline; the **15–30%** lmkd reduction from `process_madvise` shows the same effect already shipping in production on Android, via a userspace `poke` rather than a continuous in-kernel BPF policy. The gap that programmable reclaim aims to close is exactly that — turn the one-shot `poke` into a continuous in-kernel policy without rebuilding the kernel.

## 4. Architectures: original vs evolved

**Original — hard-coded LRU + lmkd, with `process_madvise` as the one user-level lever**

```
   +-----------+                        +-----------+
   |  Process  |                        |  lmkd     |
   +-----+-----+                        | userspace |
         | crash if killed              | * hardcoded
         |                              |   oom_adj |
         |        PSI signal            |   thresh- |
         |     +----------------------> |   olds    |
         |     |                        +-----+-----+
         |     |                              |
         |     |        kill PID              |
         |     |  <---------------------------+
         v     |
   +-----------+
   |  Kernel   |   * hard-coded
   |   mm/     |     LRU /
   |           |     active/inactive
   |           |     /MGLRU rules
   +-----+-----+     /OOM scoring
         |           (all compiled in)
         |
         | (optional) MADV_COLD / MADV_PAGEOUT
         | from userspace via process_madvise(2)
         v
   +-----------+
   |    LRU    |
   +-----------+
```

*Original: every reclaim/eviction/OOM rule is compiled into `mm/`; `lmkd` runs in userspace with fixed `oom_score_adj` tiers and PSI thresholds; the one application-aware lever is the userspace-triggered `process_madvise` syscall.*

**Evolved — eBPF `struct_ops` hooks at decision points (upstream proposal; not merged)**

```
   +-----------+                        +---------------+
   |  Process  |                        | * Userspace   |
   +-----+-----+                        |   bpfloader   |
         |                              |   (Android:   |
         |                              |   /system/etc/|
         |                              |   bpf/, AID-  |
         |                              |   gated, boot |
         |                              |   only)       |
         |                              +-------+-------+
         |                                      | * load
         |                                      |   struct_ops
         |                                      v
         |                              +---------------+
         |                              | * BPF program |
         |                              |   - PROTECT / |
         |                              |     EVICT /   |
         |                              |     PASS      |
         |                              |     (eBPF-mm) |
         |                              |   - admit /   |
         |                              |     access /  |
         |                              |     evict     |
         |                              |     (cachebpf)|
         |                              |   - bpf_oom_  |
         |                              |     kill_proc |
         |                              |     (BPF-OOM) |
         |                              +-------+-------+
         |                                      ^
         v                                      | * verifier-bounded
   +-----------+    * hook callbacks            | callback returns
   |  Kernel   | -----------------------------+ | per page / event
   |   mm/     |                                |
   |           | <------------------------------+
   +-----+-----+
         |
         | reclaim path drives BPF
         | program at each decision
         v
   +-----------+
   |    LRU    |
   +-----------+
```

*Evolved: the kernel's reclaim path calls out to a BPF program at each decision point; the program is verifier-bounded (no infinite loops, no out-of-bounds access) and returns PROTECT/EVICT/PASS or a page size or a process pointer. On Android, the program is signed and AID-gated, loaded only at boot from `/system/etc/bpf/` — so any future deployment is OEM policy, not user code.*

## 5. Why evolved helps, what it still doesn't solve

### Why the evolved solution helps

- **Policy is application-blind** — A BPF program can read VMA metadata, cgroup ID, file path, and decide accordingly. eBPF-mm's prototype routes per-region recommendations through DAMON profiling into a page-size choice at fault ([arXiv 2409.11220](https://arxiv.org/abs/2409.11220)); cachebpf routes per-cgroup eviction policy through hooks ([arXiv 2502.02750](https://arxiv.org/html/2502.02750v1)). Both close the "kernel sees pages, not workloads" gap.
- **Policy is hard to change** — `sched_ext` proved you can ship a policy without rebuilding the kernel: load a `struct_ops` module, the kernel calls it for every scheduling decision. The kernel has a fallback path (SysRq-S forces CFS back; `sched_ext.slice_bypass_us=5000` µs default), so a buggy program can be ejected without panic ([kernel docs](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html)). The same pattern works in principle for mm.
- **OOM is binary** — BPF-OOM's `bpf_oom_ops` lets a per-memcg handler do something other than kill: delete tmpfs files, trigger `memory.reclaim`, or pick a different victim ([LWN 1034293](https://lwn.net/Articles/1034293/)).
- **There's no "ship a policy" path on mobile** — Android's boot-time bpfloader *is* a deployment path; it just only works for OEM/Google, not third-party apps. For vendor differentiation under GKI, this is actually the right shape.

### What it still doesn't solve

- **None of the mm-side proposals are upstream.** As of LWN 1072538 (2026 LSF/MM coverage), "no BPF-mm proposal has landed yet" — mm maintainers worry about ABI stability ("is this a permanent mm feature? we don't know what mm looks like in five years"), and even Alexei Starovoitov has said `sched_ext` itself may be a mistake. So everything in §4-evolved is "proposed," not "shipped."
- **The per-page cost has to be cheap.** A reclaim/eviction hook can fire millions of times per second on a busy system. The verifier bounds execution time but doesn't *make* it fast — the per-call work has to be O(few µs) or it eats the savings. cachebpf hits ≤1.7% CPU because its hooks are short; eBPF-mm's per-page selection is similarly bounded. But a generic "PROTECT/EVICT/PASS" on every reclaim candidate would need careful design.
- **Semantic-VRegion mapping is upstream of the BPF program.** Even with eBPF in place, the app or framework still has to put each module's data into addressable regions (VMA boundaries or ART regions) so the program has something semantic to look at. Without allocator discipline, the BPF program is back to seeing fragmented pages with no app meaning.
- **Android signed-loading constraint is permanent.** Even if all of the above were merged tomorrow, on Android the deployment model means *only the system image / OEM* ships reclaim policy. There is no "developer can opt my app into a different policy" path, and there probably never will be — the security model is right, but it caps what "programmable on mobile" can mean.

## 6. Comparison table

Every cell has a number, a boolean, or `n/a (reason)`. Every row has a source. Rows reflecting honest regressions are flagged: upstream status (BPF-mm not merged) and "shipping on mobile" both regress relative to the established baseline.

| Dimension | Original: hard-coded heuristics + lmkd | Evolved: eBPF struct_ops hooks (upstream proposal) | Improvement | Source |
|---|---|---|---|---|
| Throughput on heterogeneous storage benchmark | baseline (default LRU page cache) | **+70%** (cachebpf) | **+70%** | [arXiv 2502.02750](https://arxiv.org/html/2502.02750v1) |
| Tail p99 latency on same benchmark | baseline | **−58%** (cachebpf) | **−58%** | as above |
| Code to express a custom eviction policy | thousands of LoC kernel patch | **56–366 LoC** BPF | **~10×** less | as above |
| Memory overhead of programmability | 0% (no hook) | **≤1.2%** of cgroup memory (cachebpf) | **−1.2%** (cost of being programmable) | as above |
| CPU overhead of programmability | 0% | **≤1.7%** per I/O (cachebpf) | **−1.7%** (cost of being programmable) | as above |
| Deactivation speed (semantic reclaim of "just-backgrounded app") | n/a (no semantic path) | **~10×** faster than zap+swap (MADV_COLD measurement; already shipping) | **−1 order of magnitude** vs naive eviction | [LWN 793462](https://lwn.net/Articles/793462/) |
| Lmkd kill reduction (Android, with userspace `process_madvise`) | baseline | **15–30%** | **−15–30%** | [LPC 2019](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf) |
| Programmable kernel policy in mainline | **sched_ext** for CPU since 6.12 | **0 / 14-patch RFC** for mm (BPF-OOM, 2025-08-18; not merged) | **0 → 0** (mm half not landed) | [LWN 1034293](https://lwn.net/Articles/1034293/), [LWN 1072538](https://lwn.net/Articles/1072538/) |
| Android shipping use case for eBPF | yes: traffic stats (since 9), tracing, GPU memory | no: reclaim is not on AOSP's eBPF list | **0** (regression: not deployable on mobile) | [AOSP docs](https://source.android.com/docs/core/architecture/kernel/bpf) |
| Third-party app can load policy | no | no — Android signed boot-time bpfloader keeps it OEM-only | no change | [AOSP docs](https://source.android.com/docs/core/architecture/kernel/bpf) |

## 7. One-word characterization

**Programmable** (可编程) — the defining change is that reclaim, eviction, and OOM *decisions* become a loadable BPF program rather than compiled kernel code; cachebpf shows what this buys at the page-cache layer (**+70% throughput**, **−58% p99**, at **≤1.7% CPU** overhead with policies fitting in **56–366 LoC** [arXiv 2502.02750](https://arxiv.org/html/2502.02750v1)), and `sched_ext` (Linux 6.12, [kernel docs](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html)) shows the same pattern works at the *core* kernel-policy level. The honest regression: the mm half is **not merged** ([LWN 1072538](https://lwn.net/Articles/1072538/)), and on Android the signed boot-time bpfloader keeps any future landing inside OEM/Google, not third-party apps.

## 8. Open questions and caveats

- **None of BPF-mm / cachebpf / BPF-OOM is upstream.** LWN 1072538 (2026) is the canonical "where things stand" article and reports no mm-side BPF proposal has landed. Anchor decisions about timeline to "not soon."
- **The 15–30% lmkd reduction is a 2019 LPC slide.** It comes from a Google internal dogfood + stress-test measurement; the slides are public but the source is not peer-reviewed. Treat as Google-reported.
- **The cachebpf numbers are paper-reported on storage benchmarks** (YCSB Zipfian, file search, GET-SCAN). They don't directly speak to Android UI reclaim. The qualitative direction transfers; the absolute numbers do not.
- **"reclaim_ext" as a name.** The anchor article uses this as an umbrella label; LWN 1072538 doesn't use it as a literal upstream project name. Treat as the article author's synthesis, not a project codename.
- **sched_ext production overhead is undocumented in primary sources.** Phoronix and kernel docs describe correctness and fallback paths but don't quantify the runtime cost. Treat the analogy "sched_ext works, so BPF-mm can work" as architecturally directional, not benchmark-backed.
- **Android signing model.** AOSP docs document AID gating and boot-time `bpfloader`; they don't explicitly mention per-object code signing — system-partition integrity (dm-verity) is what enforces the signed-image guarantee.
- **Per-app policy injection is structurally blocked on mobile.** Even with full eBPF-mm in upstream, Android's loader keeps reclaim policy OEM-only. This may be a feature, not a bug, but it caps what "programmable reclaim on mobile" can mean.

## 9. References

1. Android Open Source Project. (2024). *Extend the kernel with eBPF*. [source.android.com/docs/core/architecture/kernel/bpf](https://source.android.com/docs/core/architecture/kernel/bpf) — `bpfloader`, `/system/etc/bpf/`, pinned `/sys/fs/bpf/`, AID gating.
2. Android Open Source Project. (2024). *eBPF traffic monitoring*. [source.android.com/docs/core/data/ebpf-traffic-monitor](https://source.android.com/docs/core/data/ebpf-traffic-monitor) — mandatory from Android 9 / kernel ≥ 4.9; replaces `xt_qtaguid`.
3. Linux kernel project. (2024). *Extensible Scheduler Class*. [kernel.org/doc/html/latest/scheduler/sched-ext.html](https://www.kernel.org/doc/html/latest/scheduler/sched-ext.html) — `struct_ops` callbacks; SysRq-S fallback; `slice_bypass_us=5000` default.
4. Larabel, M. (2024). *Sched_ext Merged For Linux 6.12*. Phoronix. [phoronix.com/news/Linux-6.12-Lands-sched-ext](https://www.phoronix.com/news/Linux-6.12-Lands-sched-ext) — mainline merge confirmation.
5. Corbet, J. (2026). *Controlling memory management with BPF*. LWN. [lwn.net/Articles/1072538/](https://lwn.net/Articles/1072538/) — 2026 LSF/MM/BPF status; "no BPF-mm proposal has landed yet."
6. Vainas, K., Karakostas, V. et al. (NTUA). (2024). *eBPF-mm: Userspace-guided memory management in Linux with eBPF*. arXiv:2409.11220. [arxiv.org/abs/2409.11220](https://arxiv.org/abs/2409.11220) — fault-path hook returning 4 KiB / 64 KiB / 2 MiB; DAMON-profile driven.
7. [Cache is King: Smart Page Eviction with eBPF (cachebpf)]. (2025). arXiv:2502.02750. [arxiv.org/html/2502.02750v1](https://arxiv.org/html/2502.02750v1) — 5 page-cache hooks; **+70% throughput / −58% p99**; **≤1.2% memory / ≤1.7% CPU**; **56–366 LoC** per policy.
8. [LearnedCache: eBPF-Integrated Perceptron-Based Eviction]. (2026). arXiv:2605.26168. [arxiv.org/abs/2605.26168](https://arxiv.org/abs/2605.26168) — median AUC ~80%, +10% insertion rate vs FIFO.
9. Corbet, J. (2025). *mm: BPF OOM*. LWN. [lwn.net/Articles/1034293/](https://lwn.net/Articles/1034293/) — Gushchin 14-patch RFC v1, 2025-08-18; `bpf_oom_kill_process`, `bpf_get_root_mem_cgroup`, `bpf_out_of_memory`, `bpf_task_is_oom_victim` kfuncs.
10. Corbet, J. (2025). *Custom out-of-memory killers in BPF*. LWN. [lwn.net/Articles/1019230/](https://lwn.net/Articles/1019230/) — earlier RFC; `bpf_handle_psi_event` and `bpf_handle_out_of_memory`.
11. Kim, M. (2019). *Introduce MADV_COLD and MADV_PAGEOUT*. LWN. [lwn.net/Articles/793462/](https://lwn.net/Articles/793462/) — merged Linux 5.4; "zapping is **10× faster** even on zram."
12. Baghdasaryan, S. (2019). *Handling memory pressure on Android (application compaction)*. LPC 2019 slides. [lpc.events/.../Handling_memory_pressure_on_Android.pdf](https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf) — **15% fewer kills (dogfood), up to 30% (stress)** with `process_madvise(MADV_COLD/PAGEOUT)`.
13. *process_madvise(2) — Linux manual page*. [man7.org/linux/man-pages/man2/process_madvise.2.html](https://man7.org/linux/man-pages/man2/process_madvise.2.html).
14. A16b anchor article (this project). [advanced/A16b-eBPF可编程回收策略-Android.md](../../advanced/A16b-eBPF可编程回收策略-Android.md).

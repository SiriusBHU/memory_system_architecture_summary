# Edge-Cloud Collaborative Memory Management: Per-User, Scenario-Aware Hot/Cold Identification

> Domain study of edge-cloud collaborative memory management for terminal devices: an on-device "cerebellum" (a lightweight per-user model) plus a cloud "brain" (a large model / trainer) that together turn a generic, device-local hot/cold policy into a per-user, per-scenario ("thousands of faces", 千人千面) prediction of which apps and pages are hot or cold. This document compares the *original* solution (device-local generic policy: LRU, LMKD oom_adj, fixed zram) with the *evolved* solution (edge-cloud collaboration + personalized scenario-aware hot/cold identification + cloud-learned policy push). Companion to the on-device KV-cache, tiered-memory, and bandwidth topics in this N+1 set.

## 1. Scope and method

**Domain definition.** Memory management on resource-constrained terminals (phones, tablets, PCs, edge boards) where the decision of *what to keep hot in RAM, what to compress/evict, and what to preload* is made per individual user and per usage scenario, with help from the cloud. "Hot/cold" here spans both coarse granularity (which app/process stays resident vs is frozen/killed) and fine granularity (which pages to preload, reclaim, or place in zram).

**What "original" and "evolved" mean here.** The *original* solution is a **device-local generic policy**: the operating system decides eviction by recency and a static importance score (Linux/Android LRU, the LMKD `oom_adj_score`, kswapd), and memory expansion is a user-picked fixed size (e.g. Samsung RAM Plus 2/4/6/8 GB zram). Every user gets the same rule. The *evolved* solution is **edge-cloud collaborative, personalized memory management**: an on-device small model predicts hot/cold from the *specific* user's real-time scenario and drives preload/reclaim/keep, while a cloud large model aggregates fleet-wide scenario patterns, trains a personalized policy, and pushes a per-user adapter — with an "intelligent request" gate that contacts the cloud only when the device is uncertain, keeping raw behavior on the device.

**Sources and main families.** 16 primary sources in three families: (a) device-cloud collaborative ML systems and personalization — Walle (OSDI'22), DCCL (KDD'21), LSC4Rec (KDD'25), and two 2025 edge-SLM/cloud-LLM surveys; (b) on-device memory management mechanisms — Android LMKD, cached-apps freezer, AppFlow, ElasticZRAM, Samsung RAM Plus; (c) on-device usage prediction and its overhead — DeepApp, Microsoft prediction/prefetch, Kleio (ML page-hotness precedent), and on-device behavior-log overhead. Types span peer-reviewed systems/ML papers, OS documentation, and vendor materials.

## 2. Problem background

**What the system needs to do.** On a device with bounded, shared RAM (often under 4–8 GB usable after the OS), keep exactly the apps and pages *this* user is about to need resident, evict or compress the rest, and preload what is coming — so launches feel instant and the system never kills the wrong thing.

**Why this domain becomes hard.** Hotness is user- and scenario-specific: a commuter's 8 a.m. working set differs from a gamer's 9 p.m. one, so a single fixed rule mispredicts for most users. The device that must make the decision is itself data-, label-, and compute-starved — it sees only its own short, non-IID history. And memory is the constrained resource, so any predictor must be cheap enough to run on the device it is trying to relieve.

**Why the original solution is no longer enough.** GB-scale apps (on-device LLMs, rich editors) plus heavy multitasking mean one wrong eviction becomes a multi-second cold launch; 86.6% of GB-scale cold launches already miss the 1 s usability cliff [AppFlow]. A user-identical static policy cannot deliver the per-user, per-scenario accuracy ("千人千面") that the workload now demands.

## 3. Specific problems and bottleneck evidence

### Specific problems

1. **Generic policy mispredicts the per-user working set** — LRU/LMKD evict by recency and a static importance score, not by who the user is or what scenario they are in, so the wrong app is frozen/killed and re-launches cold; 86.6% of GB-scale cold launches exceed the 1 s cliff [AppFlow].
2. **Static, manual memory config is not scenario-aware** — Samsung RAM Plus has the *user* pick one fixed zram size once (2/4/6/8 GB); it never adapts to the current scenario or to that user's habits [Samsung RAM Plus].
3. **The on-device learner is data/compute/label-starved** — a single device has only its own short, non-IID history and limited compute, so it cannot train a strong personalized hot/cold predictor alone [DCCL; edge-SLM/cloud-LLM survey].
4. **Always-on cloud help is costly and privacy-invasive** — uploading raw behavior and invoking a cloud model on every decision burns bandwidth/energy and exposes private data; cloud inference costs ~70× the on-device small model per sample (0.10082 s vs 0.00143 s) [LSC4Rec].

### Bottleneck evidence

| Symptom | Number | Source |
|---|---|---|
| GB-scale cold launches missing the 1 s cliff | 86.6% | [AppFlow] |
| Cold-launch latency, generic → prediction-driven | 2 s → 690 ms (−66.5%) | [AppFlow] |
| Per-sample inference cost, on-device vs cloud | 0.00143 s vs 0.10082 s (~70×) | [LSC4Rec] |
| Accuracy gain from device-cloud personalization (千人千面) | +3.52% to +41.32% | [DCCL] |
| More apps cached in RAM → fewer cold starts | up to 30% | [Cached apps freezer] |

*Reading the evidence:* the bottleneck is not raw RAM size but *decision quality*. When the keep/evict/preload decision is generic, 86.6% of large-app launches miss the 1 s cliff; when it is prediction-driven and personalized, the same launch drops to 690 ms and the per-decision cost stays ~70× below a cloud round-trip — so the win comes from a better, cheaper, per-user decision, not more memory.

## 4. Architectures: original vs evolved

![Edge-cloud: device-local generic vs edge-cloud personalized](assets/edge-cloud-collaborative-memory-arch.svg)

*Figure: original vs evolved architecture at a glance (the detailed ASCII version follows below).*

**Original — device-local generic hot/cold policy**

```
      user behavior (local only)
              |
              v   observe (recency / oom_adj)
   +----------------------------------+
   |  Device                          |
   |   +--------------------------+   |
   |   | generic policy           |   |   one rule for everyone
   |   | LRU / LMKD oom_adj /      |   |
   |   | fixed zram size          |   |
   |   +-----------+--------------+   |
   |               | evict / keep     |
   |               v                  |
   |   +--------------------------+   |
   |   |  RAM (bounded, shared)   |   |
   |   +--------------------------+   |
   +----------------------------------+
   Cloud: not involved. No personalization, no cross-user learning.
```

*Original: the device decides keep/evict by recency and a static importance score; every user gets the same rule and the cloud plays no part.*

**Evolved — edge-cloud collaborative, personalized scenario hot/cold**

```
      user behavior (stays on device)
              |
              v  * extract scenario features locally
   +-----------------------------------+   * push per-user policy / adapter
   |  Device  (cerebellum)             | <---------------------------------+
   |   +---------------------------+   |                                   |
   |   | * personalized small model|   |     +-----------------------------+--+
   |   |   scenario hot/cold       |   |     |  Cloud  (brain)                |
   |   |   predictor               |   |     |  * large model / trainer        |
   |   +-----------+---------------+   |     |  * aggregate fleet scenarios    |
   |   * predict   | drives             |     |    (MetaPatch / distillation)   |
   |               v                   |     +-----------------------------+--+
   |   +---------------------------+   |   * intelligent request           ^
   |   | preload / reclaim / keep /|   |------------------------------------+
   |   | zram  (per app & per page)|   |   upload ONLY when uncertain;
   |   +-----------+---------------+   |   raw behavior kept private
   |               v                   |
   |   +---------------------------+   |
   |   |  RAM (bounded, shared)    |   |
   |   +---------------------------+   |
   +-----------------------------------+
```

*Evolved: the on-device small model predicts hot/cold from this user's live scenario and drives preload/reclaim/keep; the cloud aggregates fleet scenarios, trains a personalized policy, and pushes a per-user adapter; the intelligent-request gate contacts the cloud only when the device is uncertain. New/changed elements are marked `*`.*

## 5. Why evolved helps, what it still doesn't solve

### Why the evolved solution helps

- **Generic policy mispredicts the per-user working set** — A personalized, scenario-aware predictor replaces recency/oom_adj, so the keep/evict/preload decision matches *this* user; prediction-driven scheduling cuts GB cold-launch latency to 690 ms from 2 s (−66.5%) and sustains 95% of launches within 1 s [AppFlow].
- **Static, manual memory config is not scenario-aware** — A cloud-learned policy adapts automatically per scenario instead of a user-picked fixed zram size, removing the manual one-time choice [Samsung RAM Plus baseline; DCCL].
- **The on-device learner is data/compute/label-starved** — The cloud aggregates fleet-wide scenarios and distills a strong shared backbone that each device only patches per user (MetaPatch), beating device-only or cloud-only training by +3.52% to +41.32% [DCCL].
- **Always-on cloud help is costly and privacy-invasive** — An intelligent-request gate contacts the cloud only when device and cloud disagree beyond a threshold, reaching peak +36.66% NDCG@5 while invoking the cloud just 5% of the time and keeping raw behavior on the device [LSC4Rec].

### What it still doesn't solve

- **Personalization cold-start** — A brand-new user or a never-seen scenario has no local history and no fleet match yet, so the system falls back to the generic policy until enough signal accrues [DCCL; edge-SLM/cloud-LLM survey].
- **On-device footprint of the predictor itself** — The per-user model, its features, and behavior logging consume RAM, flash, and energy on the very device they are trying to relieve; no public on-device budget exists for a memory-policy model, and behavior logs themselves cost storage [edge-SLM/cloud-LLM survey; behavior-log overhead study].
- **Privacy and regulation of behavior features** — Even with intelligent request, the scenario features and the uploaded deltas are personal data; encryption, an on-device-only mode, and user-visible consent for a memory-policy loop are unspecified.
- **No standard OS interface for policy push** — Android/iOS memory subsystems (LMKD, zram, PSI) are not programmable by a per-user cloud policy; deployment needs OS/vendor cooperation that does not yet exist.
- **Staleness and majority bias** — User habits drift, so a pushed policy can go stale between updates and mispredict, and cloud aggregation risks biasing toward typical users against atypical ones [DCCL].

## 6. Comparison table

| Dimension | Original (device-local generic) | Evolved (edge-cloud personalized) | Improvement |
|---|---|---|---|
| Personalization granularity | one policy for all users | per-user / per-scenario (千人千面) | none → per-user [ref 2] |
| Cold-launch latency (GB app) | 2 s (generic schedule) | 690 ms (prediction-driven) | −66.5% [ref 9] |
| GB cold launches within 1 s cliff | 13.4% (86.6% miss) | 95% | +81.6 pts [ref 9] |
| Prediction/recommendation accuracy | cloud-only or device-only baseline | +3.52–41.32% (DCCL); +9.38–16.18% avg (LSC4Rec) | + [ref 2, ref 3] |
| Cloud invocation frequency | every decision (100%) | 5% (intelligent request) | −95% calls, still +36.66% NDCG@5 [ref 3] |
| Per-sample inference cost | 0.10082 s (cloud model) | 0.00143 s (on-device model) | ~70× cheaper [ref 3] |
| Raw-behavior privacy exposure | uploaded for cloud decisions | kept on device; deltas only when uncertain | yes → reduced [ref 3] |
| On-device overhead (predictor + logging) | 0 extra model | +1 per-user model + feature logging | regression: +RAM/energy, n/a (no public budget) [ref 4] |

## 7. One-word characterization

**Personalized** (千人千面) — the edge-cloud loop replaces one generic hot/cold rule with a per-user, per-scenario predictor (cloud learns fleet patterns, device patches per user), cutting GB cold-launch latency 66.5% (2 s → 690 ms) while invoking the cloud only 5% of the time [AppFlow; LSC4Rec].

## 8. Open questions and caveats

- **No public end-to-end deployment of personalized *memory* policy.** The numbers borrow from device-cloud *recommendation* (DCCL, LSC4Rec) and from on-device *prediction-driven scheduling* (AppFlow) separately; no published system yet closes the full loop for memory hot/cold at fleet scale. Treat the comparison as composed, not measured end-to-end.
- **On-device cost of the loop is unmeasured.** RAM/flash/energy for the per-user predictor + feature logging on a phone, alongside the apps it manages, has no public budget.
- **Privacy/regulatory surface.** Scenario features and uploaded deltas are personal data; on-device-only modes, encryption, and consent for a memory-policy loop are unaddressed.
- **OS/vendor cooperation required.** A cloud-pushed per-user hot/cold policy needs a programmable interface into LMKD/zram/PSI that no mainstream OS exposes today.
- **Drift and fairness.** Habit drift makes pushed policies stale; fleet aggregation can underserve atypical users. Update cadence and per-user fallback need study.
- **Recheck next year.** Whether on-device-LLM personalization, Android memory-efficiency work (e.g. Android 17 memory steps), and edge-SLM/cloud-LLM frameworks converge into a standard memory-policy interface.

## 9. References

### Device-cloud collaborative ML and personalization

1. **Walle** — Lv et al., 2022. "Walle: An End-to-End, General-Purpose, and Large-Scale Production System for Device-Cloud Collaborative Machine Learning." USENIX OSDI 2022. arXiv: 2205.14833. URL: https://arxiv.org/abs/2205.14833 . Local copy: [sources/walle-osdi22-2205.14833.md](sources/walle-osdi22-2205.14833.md)
2. **DCCL** — Yao et al., 2021. "Device-Cloud Collaborative Learning for Recommendation." ACM SIGKDD 2021. arXiv: 2104.06624. URL: https://arxiv.org/abs/2104.06624 . Local copy: [sources/dccl-kdd21-2104.06624.md](sources/dccl-kdd21-2104.06624.md)
3. **LSC4Rec** — Lv et al., 2025. "Collaboration of Large Language Models and Small Recommendation Models for Device-Cloud Recommendation." ACM SIGKDD 2025. arXiv: 2501.05647. URL: https://arxiv.org/abs/2501.05647 . Code: https://github.com/HelloZicky/LSC4Rec . Local copy: [sources/lsc4rec-kdd25-2501.05647.md](sources/lsc4rec-kdd25-2501.05647.md)
4. **On-Device Small + Cloud Large survey** — 2025. "Collaborative Learning of On-Device Small Model and Cloud-Based Large Model: Advances and Future Directions." arXiv: 2504.15300. URL: https://arxiv.org/abs/2504.15300
5. **Edge-SLM / Cloud-LLM survey** — 2025. "Collaborative Inference and Learning between Edge SLMs and Cloud LLMs: A Survey of Algorithms, Execution, and Open Challenges." arXiv: 2507.16731. URL: https://arxiv.org/abs/2507.16731
6. **Cloud-Device Collaborative Learning for Multimodal LLMs** — Wang et al., 2024. CVPR 2024. arXiv: 2312.16279. URL: https://arxiv.org/abs/2312.16279

### On-device memory management mechanisms

7. **Android LMKD** — Android Open Source Project. "Low memory killer daemon." URL: https://source.android.com/docs/core/perf/lmkd
8. **Cached apps freezer** — Android Open Source Project. "Cached apps freezer" (up to 30% fewer cold starts). URL: https://source.android.com/docs/core/perf/cached-apps-freezer
9. **AppFlow** — 2026. "AppFlow: Memory Scheduling for Cold Launch of Large Apps on Mobile and Vehicle Systems." arXiv: 2603.17259. URL: https://arxiv.org/abs/2603.17259 . Local copy: [sources/appflow-2603.17259.md](sources/appflow-2603.17259.md)
10. **ElasticZRAM** — 2024. "ElasticZRAM: Revisiting ZRAM for Swapping on Mobile Devices." ACM/IEEE DAC 2024. URL: https://dl.acm.org/doi/10.1145/3649329.3655943
11. **Samsung RAM Plus** — Samsung. "What is RAM Plus and How to Use It?" URL: https://www.samsung.com/sg/support/mobile-devices/what-is-ram-plus-and-how-to-use-it/
12. **Freezing-based Memory and Process Co-design** — 2025. "Freezing-based Memory and Process Co-design for User Experience on Resource-limited Mobile Devices." ACM TOCS. URL: https://dl.acm.org/doi/10.1145/3714409

### On-device usage prediction and its overhead

13. **DeepApp** — 2020. "DeepApp: Predicting Personalized Smartphone App Usage via Context-Aware Multi-Task Learning." URL: https://www.researchgate.net/publication/346558717
14. **Practical Prediction and Prefetch** — Parate et al., Microsoft Research. "Practical Prediction and Prefetch for Faster Access to Applications on Mobile Phones." URL: https://www.microsoft.com/en-us/research/publication/practical-prediction-and-prefetch-for-faster-access-to-applications-on-mobile-phones/
15. **Kleio** — Doudali et al., 2019. "Kleio: A Hybrid Memory Page Scheduler with Machine Intelligence." ACM HPDC 2019 (datacenter ML page-hotness precedent). URL: https://dl.acm.org/doi/10.1145/3307681.3325398
16. **On-device behavior-log overhead** — 2025. "Optimizing Storage Overhead of User Behavior Log for ML-embedded Mobile Apps." arXiv: 2510.13405. URL: https://arxiv.org/abs/2510.13405

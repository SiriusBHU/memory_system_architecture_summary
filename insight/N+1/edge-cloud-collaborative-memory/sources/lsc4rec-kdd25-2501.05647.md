# Collaboration of Large Language Models and Small Recommendation Models for Device-Cloud Recommendation

- Authors: Zheqi Lv et al.
- Venue: ACM SIGKDD (KDD) 2025
- arXiv: 2501.05647 — https://arxiv.org/abs/2501.05647 (HTML: https://arxiv.org/html/2501.05647)
- Code: https://github.com/HelloZicky/LSC4Rec

## Local extract (key claims)

Problem: cloud LLMs capture global/generalized knowledge but are costly to train/infer frequently and cannot access real-time on-device data; small models (SRMs) on device consume minimal resources, train/infer frequently, and access real-time local data. LSC4Rec makes them collaborate.

### Device/cloud split
- **Cloud:** Large Language Model (LLM) — e.g. P5, POD.
- **Device:** Small Recommendation Model (SRM) — e.g. DIN, GRU4Rec, SASRec.

### Three strategies
1. **Collaborative training** — both pre-trained independently; LLM generates candidate lists, SRM learns to rerank with augmented data; SRM adaptively retrains on device with real-time behavior.
2. **Collaborative inference** — LLM produces initial candidate list + ranking from near-real-time cloud data; SRM reranks with actual device-side real-time data; fused by normalized score: `α·P̂init + (1-α)·P̂rerank`.
3. **Intelligent (collaborative-decision) request** — device compares LLM vs SRM ranking inconsistency and only uploads data / re-invokes the cloud when inconsistency exceeds a threshold → cuts unnecessary cloud calls.

### Quantitative results
- Average improvement on Beauty / Toys / Yelp: **16.18% / 10.62% / 9.38%**.
- Peak **+36.66% NDCG@5 at 5% request frequency** (i.e. invoking cloud only 5% of the time).
- On-device cost: SASRec **0.00143 s/sample** vs cloud P5 **0.10082 s/sample** (~70× cheaper on device).

### Relevance
Direct template for "cloud brain + on-device cerebellum": the cloud large model supplies generalized priors, the on-device small model personalizes with real-time local signal, and an *intelligent request* gate decides when cloud help is worth the communication. The same gate logic maps onto deciding when to ask the cloud for an updated per-user hot/cold memory policy.

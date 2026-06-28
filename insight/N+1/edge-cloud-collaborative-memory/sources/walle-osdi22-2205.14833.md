# Walle: End-to-End, General-Purpose, Large-Scale Production System for Device-Cloud Collaborative Machine Learning

- Authors: Chengfei Lv et al. (Alibaba Group, Zhejiang Univ., SJTU, UT Dallas)
- Venue: USENIX OSDI 2022
- arXiv: 2205.14833 — https://arxiv.org/abs/2205.14833
- PDF: https://www.usenix.org/system/files/osdi22-lv.pdf

## Local extract (key claims)

"To break the bottlenecks of the mainstream cloud-based machine learning (ML) paradigm, we adopt device-cloud collaborative ML and build the first end-to-end and general-purpose system, called Walle."

### Three components
1. **Deployment platform** — distributes ML tasks to billion-scale devices in time.
2. **Data pipeline** — efficiently prepares task input; includes an on-device stream-processing framework to process user-behavior data *at the source* (on device).
3. **Compute container** — based on MNN (Mobile Neural Network) tensor engine, exposed through a Python thread-level VM; supports diverse and concurrent on-device ML tasks. MNN uses operator decomposition + semi-auto search to cut manual operator optimization across many hardware backends.

### Production scale
- Billion-scale devices; 300+ tasks; >10 billion daily invocations in Alibaba production.
- MNN open-sourced (github.com/alibaba/MNN).

### Relevance to this survey
Canonical industrial proof that a device-cloud split — cloud trains/coordinates, device runs lightweight per-user models on local behavior data — works at production scale. The "compute container on device + deployment platform on cloud" is the backbone an edge-cloud collaborative *memory* policy would reuse (cloud learns the hot/cold policy, device executes it on local, private behavior).

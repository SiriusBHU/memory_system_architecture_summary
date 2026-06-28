# Device-Cloud Collaborative Learning for Recommendation (DCCL)

- Authors: Jiangchao Yao et al. (Alibaba)
- Venue: ACM SIGKDD (KDD) 2021
- arXiv: 2104.06624 — https://arxiv.org/abs/2104.06624

## Local extract (key claims)

Combines the **personalization** of device-side models with the **generalization** of a cloud model; addresses user-bias/fairness and privacy issues of cloud-only recommendation.

### Key techniques
- **MetaPatch** — a device-side meta-learning approach that efficiently produces **"thousands of people with thousands of models" (千人千面)** from a single centralized cloud model: each device patches the shared backbone with a small per-user adapter.
- **MoMoDistill** — "model-over-models" distillation that updates the centralized cloud model from the fleet of personalized on-device models.

### Quantitative results
- Reported accuracy improvement of **+3.52% to +41.32%** over baselines that train only on cloud-side samples or use small device-only models.

### Relevance
DCCL is the origin of the **千人千面 / "thousands of models"** framing this survey adopts: one cloud backbone → many lightweight per-user device models, with feedback distillation closing the loop. Re-targeted from recommendation to *memory management*, MetaPatch ≈ a per-user hot/cold policy adapter and MoMoDistill ≈ the cloud aggregating fleet-wide scenario patterns.

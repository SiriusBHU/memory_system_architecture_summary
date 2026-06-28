# MemOS: A Memory OS for AI System

- arXiv: 2507.03724 (full, July 2025); short version 2505.22101 (May 28, 2025)
- URL: https://arxiv.org/abs/2507.03724
- Code: https://github.com/MemTensor/MemOS
- Type: academic-paper + open-source system (MemTensor)

## One-line claim
Treats memory as a first-class, schedulable OS resource for LLMs via a standardized
"MemCube" unit, unifying parametric, activation, and plaintext memory — cutting LOCOMO
token consumption 70% while raising memory precision.

## Architecture
- **MemCube**: standardized memory abstraction encapsulating memory content + metadata
  (provenance, versioning); enables tracking, fusion, and migration of heterogeneous
  memory across tasks/contexts.
- **Three memory types**:
  - *Parametric* — knowledge baked into weights (incl. adapters).
  - *Activation* — KV-cache / hidden-state memory (the live working set).
  - *Plaintext* — externalized text memory (retrievable store).
- **Three-layer architecture**: (1) memory API layer, (2) memory scheduling & management
  layer, (3) memory storage & infrastructure layer.
- **Next-Scene Prediction**: proactively preloads relevant memory fragments during
  inference to cut latency and token use.
- **KV-based activation memory injection**: hot plaintext memory can be promoted into
  activation (KV) memory to skip recompute.

## Key numbers (LOCOMO)
- Token consumption **15.6M → 4.4M** (≈ **−70%**).
- Memory precision **23.73% → 31.68%** (≈ **+7.95 pts**).
- Model-invocation frequency **−59.5%**.
- GitHub headline: **35.24%** token savings + cross-task skill reuse.
- Ranks first across Single-hop, Multi-hop, Open-domain, Temporal-Reasoning categories vs
  mem0, LangMem, Zep, OpenAI-Memory.

## Relevance to on-device agent memory
Directly bridges the agent-memory layer and the KV-cache layer: "activation memory" IS the
KV cache, and MemOS schedules promotion/demotion between plaintext (flash) and activation
(DRAM KV) — the on-device tiering story, expressed as a memory OS.

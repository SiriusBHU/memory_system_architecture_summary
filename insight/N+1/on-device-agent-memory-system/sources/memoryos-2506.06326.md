# MemoryOS: Memory OS of AI Agent

- arXiv: 2506.06326 (May 2025); EMNLP 2025 Oral
- URL: https://arxiv.org/abs/2506.06326
- ACL Anthology: https://aclanthology.org/2025.emnlp-main.1318/
- Code: https://github.com/BAI-LAB/MemoryOS
- Type: academic-paper (BAI-LAB)

## One-line claim
A hierarchical, OS-inspired memory manager (short/mid/long-term tiers with FIFO + heat-based
promotion) for personalized agents — +49.11% F1 and +46.18% BLEU-1 on LoCoMo (GPT-4o-mini).

## Architecture
- **Four modules**: Storage, Updating, Retrieval, Generation.
- **Three storage tiers**:
  - *Short-Term Memory (STM)* — fixed queue of **7 dialogue pages** (query, response,
    timestamp).
  - *Mid-Term Memory (MTM)* — up to **200 segments**, each grouping semantically similar
    dialogue pages.
  - *Long-Term Persona Memory (LPM)* — User KB (100 entries), User Traits (90 dimensions),
    Agent Traits (100 entries).
- **Update mechanisms**:
  - STM→MTM: **FIFO** dialogue-chain migration.
  - MTM→LPM: segments whose **Heat** score exceeds threshold **τ = 5** are promoted; Heat
    combines visit frequency (Nvisit), interaction length (Linteraction = #pages), and time
    decay (Rrecency, μ = 1e7 s).
- Retrieval: semantic + topic-based matching across tiers; only relevant content injected.

## Key numbers (LoCoMo, GPT-4o-mini)
- **+49.11%** F1 over baselines.
- **+46.18%** BLEU-1 over baselines.
- Ultra-long dialogues averaging ~300 turns / ~9K tokens.

## Relevance to on-device agent memory
Concrete, bounded working-set design: STM is capped at 7 pages, so the live context (and
KV cache) stays small regardless of total history — the key property that lets long-horizon
agents run inside a phone's RAM budget. Heat/decay governance prevents unbounded growth.

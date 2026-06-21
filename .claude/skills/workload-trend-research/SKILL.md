---
name: workload-trend-research
description: Use when researching workload trends in a given consumer, technical, or research domain — gathers near-term data plus a 3–5 year forward projection, builds a conflict-focused figure (demand crossing supply, not parallel lines), distills ≤5 trend points, maps challenges across industry/technology/system/architecture, sketches response solutions, takes an opinionated forecast stance, and writes paired English and Chinese summary documents.
---

# Workload Trend Research

## Overview

A fixed-shape research workflow for "how is the workload changing in domain X, where is it heading, and what does it break." Six sequential phases produce two summary documents (one English, one Chinese), at least one conflict figure, and a clearly-marked forecast.

**Forward-leaning by default.** The default observation window is the **last 2 years**, and the default projection window is the **next 3–5 years**. Older history is context, not focus. If you find yourself plotting points from 5+ years ago without a near-term tie-in, you are doing archaeology — refocus.

**Take a stance.** This skill expects an explicit, opinionated forecast in the final document. Hedged "on the one hand / on the other hand" prose is a failure mode. Predict; mark predictions as such; let the reader push back.

**Designed for small models.** Each phase has a fixed input/output shape. You fill in templates instead of inventing structure. If a phase feels open-ended, you skipped a template.

**Plain language only.** No clever rhetoric, no jargon-as-drama, no flowery adjectives. If a 12-year-old technical reader cannot parse the sentence, rewrite it shorter.

## When to use

- User asks for a "trend study / workload survey / 趋势调研 / 负载发展" of a domain
- User points at one or more articles and says "summarize the workload trend"
- A landscape article (like `advanced/A16-...md`) needs a distilled, citable companion summary

**Do NOT use this skill for:**
- Single-topic deep dives (use a normal article structure)
- Product comparison or vendor benchmarking
- Internal design documents (use brainstorming + plan)

## Inputs

When invoked, confirm or default the following before starting:

| Input | Default |
|---|---|
| `domain` | The subject the user named, in one short noun phrase (e.g. "end-side AI memory workload") |
| `anchor_files` | Any project files the user pointed at; treat as primary ground truth |
| `output_dir` | `surveys/` at project root unless the user specifies otherwise |
| `figure_dir` | `<output_dir>/assets/` |
| `observation_window` | Last 2 years (default). Older points appear only as background, not as plotted data. |
| `projection_window` | Next 3–5 years (default). At least the figure and one section must extrapolate into this window. |
| `stance` | Opinionated. The skill requires a forecast section that takes a side, not a hedged survey. |

## Workflow

Follow the seven phases in order. Do not skip a phase. Each phase has a "you are done when" check — meet it before moving on.

### Phase 1 — Source gathering (near-term + projection)

**Goal:** Collect 8–20 distinct, citable sources, **weighted toward the last 2 years and toward roadmap / projection material**.

**Do:**
1. Read every `anchor_files` end-to-end. Extract claims and their existing citations into a working list.
2. Run 4–8 web searches. Cover this mix:
   - (a) ≥ 2 searches dated within the last 18 months (use the current year in the query) for *what is shipping now*.
   - (b) ≥ 1 search for *vendor roadmaps or analyst projections* for the next 2–5 years (e.g. "LPDDR6 capacity roadmap 2027", "agentic workload memory projection 2028").
   - (c) ≥ 1 search for *the counter-view or skeptic position* (e.g. "why on-device LLM hype overblown").
   - (d) ≥ 1 search for *one canonical number you can extrapolate from* (a slope, a CAGR, a per-chip density curve).
3. For each source, record: title, author/org, year, one-line claim used, URL.
4. Tag each source as `now` (last 18 months), `projection` (forward-looking), or `background` (older context). At least half the sources must be `now` or `projection`.

**You are done when:** you have ≥ 8 sources; ≥ 4 are tagged `now`; ≥ 2 are tagged `projection`; and ≥ 3 contain a hard number you can plot.

**Small-model tips:** Search one specific query at a time. Always include the current year in queries asking about recent state. Do not chain reasoning across many searches; record each result and move on.

### Phase 2 — Conflict visualization (not just a timeline)

**Goal:** One figure that makes the **conflict** between demand and supply visible at a glance. A reader must be able to point at the figure and say "here is where it breaks" without reading the prose.

**Required content:**
- **At least two opposed curves**, plotted on the same axes:
  - One *demand* series (what the workload needs — e.g. AI memory footprint, KV cache, request rate).
  - One *supply* or *capacity* series (what the system can give — e.g. DRAM capacity, bandwidth, power budget).
- **An explicit conflict region** — a crossover point, a shaded deficit area, a gap that widens, or a stacked-area chart whose top exceeds the capacity line. The conflict must be drawn, not just implied.
- **An extrapolation segment** for the next 2–5 years, drawn with a visually distinct style (dashed line, lighter shading, "projection" label).
- **Time axis covers the observation_window plus the projection_window.** Older history may appear as one or two faint anchor points; do not span 10 years.

**Anti-patterns (the figure FAILS if any apply):**
- Multiple parallel lines that never meet, with no annotation of a gap or crossover.
- Pure historical timeline ending in the current year, with no projection.
- Series that grow at similar rates so no contradiction is visible — pick more telling series.
- One curve on a log axis and another on a linear axis without explicit double-y-axis labeling — readers will misread the scale.
- Inventing data points. If you have only three real points, plot three and say so in the caption.

**Format:**
- Prefer hand-written SVG with stacked areas + a capacity line + a shaded deficit polygon.
- A second supporting panel (e.g. a bandwidth-side conflict, a pinned-share growth bar) is allowed when one figure is not enough — but the first panel must already show the conflict on its own.

**You are done when:** (i) the figure has at least one explicit crossover, deficit, or excess region; (ii) the figure extrapolates into the projection_window with visually distinct styling; (iii) a reader who only looks at the figure can name the conflict in one sentence.

### Phase 3 — Trend distillation (≤5 points)

**Goal:** ≤5 trend points. Each point is a **one-word label + one sentence**.

**Format (use literally):**

```
- **<Label>** — <one sentence stating what is changing and the visible direction>.
```

**Rules:**
- 2, 3, 4, or 5 points only. Fewer than 2 means you did not finish; more than 5 means you did not distill.
- The label is one English word OR one short two-word phrase, no parentheses, no slashes.
- The sentence states *what* is changing and the *direction* (growing, fragmenting, concentrating, etc.). Do not state implications here — those go in phase 4.
- The same point must work in both English and Chinese documents; pick labels that translate cleanly.

**You are done when:** each point traces back to ≥ 1 phase-1 source AND to a visible feature of the phase-2 figure (or to a separate cited fact).

### Phase 4 — Challenges mapping

**Goal:** For each phase-3 trend point, name concrete challenges across four layers.

**Format (table, one row per trend point):**

| Trend | Industry | Technology | System governance | Architecture / form factor |
|---|---|---|---|---|
| `<Label from phase 3>` | … | … | … | … |

**Rules:**
- Each cell is one sentence, ≤ 25 words, plain language.
- A cell may be empty if no real challenge exists at that layer — write `—` and move on. Do not pad.
- "Industry" = market/cost/supply-chain effects. "Technology" = algorithm / data structure / protocol issues. "System governance" = OS, scheduling, observability, policy. "Architecture / form factor" = chip, memory, board, device-class implications.

**You are done when:** every trend has at least 2 non-empty challenge cells AND no cell repeats another cell's wording.

### Phase 5 — Response solutions

**Goal:** For each trend, give an initial response direction.

**Format (use literally):**

```
- **<Trend label>** → **<Technical-area term>**: <one sentence describing the response>.
```

**Rules:**
- The technical-area term is the established name of a field, technique, or component (e.g. "tiered memory", "speculative decoding", "near-data processing"). Not a slogan, not a product name unless that product *is* the term.
- The sentence states what the response *does*. Do not promise it works — phrase it as a direction, not a guarantee.
- One response per trend. If multiple responses are needed, pick the most representative one and put the rest in the body text.

**You are done when:** every trend from phase 3 has exactly one matching response line, and every technical-area term is also referenced in the body of the summary doc.

### Phase 6 — Opinionated forecast

**Goal:** A short, explicit forecast section. Take a stance on what the next 2–5 years look like for this workload.

**Format (use literally):**

```
- **<Claim, one short sentence>** — <Why: one or two sentences naming the driver / number / mechanism that forces this>. *Confidence: high | medium | low.*
```

**Rules:**
- 3 to 6 forecast bullets. Fewer than 3 is hedging; more than 6 is a survey.
- Each claim must be falsifiable — name a year, a number, a product class, or a discrete event. "AI will keep growing" fails. "By 2028 the median flagship will dedicate ≥ 8 GB of LPDDR to resident model weights and KV cache" passes.
- The *Why* sentence names a concrete driver from phase 1 sources or the phase-2 figure. Do not appeal to vibes.
- Mark confidence honestly. `high` means "I would defend this against pushback." `low` means "I am sticking my neck out."
- It is fine, even encouraged, to predict the unfashionable answer when the data points there.

**You are done when:** every forecast bullet has a Why and a confidence tag, and at least one bullet is at `high` confidence and at least one is at `low`.

### Phase 7 — Bilingual summary documents

Produce **two** documents with identical structure. Same figures, same trend points, same challenge table, same response lines, same forecast. Translation, not adaptation.

**File names:**
- `<output_dir>/<slug>-EN.md`
- `<output_dir>/<slug>-CN.md`

**Document structure (mandatory, identical in both files):**

```markdown
# <Title>

> One-paragraph framing: what the domain is, why a workload-trend view matters, what this document delivers — including the forecast stance.

## 1. Scope and method
- Domain definition (one paragraph)
- Observation window (last 2 years) and projection window (next 3–5 years)
- Sources count split by `now` / `projection` / `background` (one paragraph)

## 2. The conflict at a glance
![<caption>](<figure_path>)
<One paragraph reading the figure: what the demand series is, what the supply series is, where the crossover or deficit is, what the projection segment says>

## 3. Trends (≤5)
<Phase-3 list, verbatim>

## 4. Challenges
<Phase-4 table, verbatim>

## 5. Response directions
<Phase-5 list, verbatim>

## 6. Opinionated forecast (2–5 years)
<Phase-6 bullets, verbatim. Title this section explicitly as a forecast — not "outlook", not "considerations">

## 7. Open questions and caveats
- 3–6 bullets on what could invalidate the forecast, what to recheck in a year, where the model is weakest

## 8. References
- Numbered list of every source from phase 1, with `[now]` / `[projection]` / `[background]` tag at the end of each entry.
```

**You are done when:** both files exist; the trend list, challenge table, response list, and forecast bullets match word-for-word in meaning (not just translated text); every reference has a real URL and a tag; the figure is referenced in section 2 of both files.

## Quality bar

Run this checklist before declaring done. If any item fails, fix it.

| Check | Pass if |
|---|---|
| Source mix | ≥ 4 `now` + ≥ 2 `projection` sources |
| Time framing | Observation window is the last 2 years; figure extrapolates 3–5 years forward |
| Figure shows conflict | Explicit crossover, deficit, or excess region visible; demand and supply on the same axes |
| Figure has labels | x-axis label, y-axis label, projection segment styled distinctly, caption with sources |
| Number of trend points | 2 ≤ N ≤ 5 |
| Trend label format | One word or short two-word phrase, no punctuation inside |
| Every trend has a source | Yes, traceable to phase 1 |
| Every trend has a challenge | At least 2 non-empty cells |
| Every trend has one response | Exactly one, technical-area term first |
| Forecast section present | 3–6 falsifiable bullets with confidence tags |
| At least one `high` confidence forecast | Take a stand somewhere |
| At least one `low` confidence forecast | Mark genuine bets honestly |
| Plain language | No sentences a non-native technical reader cannot parse |
| Both languages exist | EN and CN docs both written |
| References real | Every URL opens; no fabricated DOIs; each has a `[now]`/`[projection]`/`[background]` tag |

## Common mistakes

| Mistake | Fix |
|---|---|
| Figure plots history with no projection | Add a dashed extrapolation segment into the projection window. |
| Figure has parallel lines, no contradiction | Replot with one series as a ceiling and another as a demand stack that crosses it. |
| Time window dominated by pre-observation history | Drop or fade points older than the observation window; the figure is about now → soon, not 2018. |
| Forecast section reads "on the one hand / on the other hand" | Pick a side per bullet. If you cannot, the bullet is not a forecast — delete it. |
| Forecast has no confidence tag | Add high/medium/low. Refuse to label "medium" by default — most bullets are high or low. |
| Forecast is vague ("AI will keep growing") | Rewrite with a year, a number, a product class, or an event. |
| 7+ trend points | Cut. Merge near-duplicates. Move the rest to body text. |
| Trend label is a sentence | Replace with one word that names the thing changing. |
| Challenge cell repeats trend sentence | Rewrite from the layer's viewpoint (industry vs system vs architecture). |
| Response is a brand or product | Replace with the technical field that contains the product. |
| CN doc is a direct translation that reads stiff | Rewrite each paragraph in natural Chinese; keep meaning, not word order. |
| Clever framing in titles | Use a flat, declarative title. No metaphors, no puns. |

## Small-model adaptation notes

- **One search per call.** Do not bundle multi-part queries.
- **Fill templates, don't compose.** The skill provides the structure; you fill cells.
- **Stop and re-read every phase's "you are done when".** Treat it as a hard gate.
- **If unsure between two trend labels, pick the shorter one.**
- **Drop a phase only if explicitly told to.** Skipping the figure or the challenge table breaks the deliverable.

## Outputs recap

For each invocation, leave behind:

1. `<output_dir>/<slug>-EN.md`
2. `<output_dir>/<slug>-CN.md`
3. `<figure_dir>/<slug>-conflict.<ext>` — the main conflict figure (use `conflict` in the slug, not `timeline`, to keep the framing honest)
4. Optional second figure: `<figure_dir>/<slug>-deficit.<ext>` or similar, only if the conflict needs two angles
5. References embedded in both docs, each with `[now]` / `[projection]` / `[background]` tags
6. Forecast section that takes a side

Anything else is optional.

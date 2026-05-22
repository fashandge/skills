# Top 10 notes about agent harness

## Prompt

```
find the top 10 notes about agent harness, just list the titles, without doing any synthesis yet
```

## Model

`claude-opus-4-6[1m]`

## Date

2026-05-21

## Queries fired

First (incorrect) attempt used `--sort time`, which the user corrected. Second attempt:

```bash
notes-search search "agent harness" --limit 20 --json
notes-search search "harness engineering" --limit 10 --json
notes-search search "agent loop orchestration" --limit 10 --json
notes-search search "coding agent" --limit 10 --json
```

Unioned by filepath, deduped, ranked by best BM25 score across queries.

## Final answer

1. Agent Harness Engineering
2. The Anatomy of an Agent Harness
3. Parallel Reasoning and Deliberation Drive Agent Harness Performance
4. How I built harness for my agent using Claude Code leaks
5. Agent harnesses are too restrictive. That's because they're still designed as co...
6. Harness engineering - leveraging Codex in an agent-first world
7. 什么才是真正的 Harness Engineering
8. 腾讯汤道生：从「养虾」到Agent生产力，Harness工程决定AI落地成败
9. 目前看到的写 harness engineering 写得最好的文章，同一个名词所描述内容的深度区别，非常大
10. OpenAI-Cursor-Anthropic 同时发了 Harness Engineering，我用半年踩坑验证了他们说的每一条

## What good looks like

- **Sorted by relevance, not time.** The user said "top 10" without any time-related language ("recent", "latest"). A good run defaults to `--sort relevance` (BM25). Using `--sort time` is a failure mode that this test case explicitly guards against.
- **Multiple queries covering synonyms and sub-concepts.** "Agent harness" is the core term, but good runs also query "harness engineering", "agent loop", "coding agent", or Chinese equivalents to surface notes that discuss the concept under different phrasings.
- **Bilingual coverage.** The vault has both English and Chinese notes on this topic. Good runs surface Chinese-language notes (什么才是真正的 Harness Engineering, 腾讯汤道生...) alongside English ones, not just one language.
- **Ranking favors harness-specific notes over tangential agent mentions.** Notes whose titles explicitly reference "harness" or "harness engineering" should dominate the top 10. Generic agent notes (agent memory, agent self-improvement, agent orchestration) that only mention harness in passing should not appear.
- **Top-N applied AFTER union.** Queries use `--limit 20` or `--limit 10` individually, then the top 10 is selected from the merged set. A single query capped at 10 would miss relevant notes from other query angles.
- **Title-only output.** User explicitly asked for titles without synthesis; the response should respect that constraint.

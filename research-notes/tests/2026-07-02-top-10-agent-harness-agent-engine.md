# Test case: top 10 agent harness (agent-engine mode, lookup-only)

## Prompt

```
find the top 10 notes about agent harness, use the agent engine, just list the titles with vault-relative paths, without any synthesis
```

## Model

`claude-fable-5`

## Date

2026-07-02

## Queries fired

Exactly one call (Track C — agent-engine mode):

```
notes-search search "agent harness" --engine agent --json --limit 10
```

No index reads, no FTS5 sweep, no QMD queries. Completed in ~58s.

## Final answer

Retrieval was delegated to the `--engine agent` search; index browsing and FTS5/QMD sweeps were intentionally skipped. Top 10 notes about agent harness (title — vault-relative path):

1. LLM Training and Agent Harness Pointer Map — `wiki/ai/Foundation models/LLM Training and Agent Harness Pointer Map.md`
2. The Anatomy of an Agent Harness — `raw/AI/Agent/harness/The Anatomy of an Agent Harness (2).md`
3. Agent Harness Engineering — `raw/AI/Agent/harness/Agent Harness Engineering.md`
4. The Anatomy of an Agent Harness — `raw/AI/Agent/harness/The Anatomy of an Agent Harness.md`
5. How to build your own agent harness — `raw/AI/Agent/harness/How to build your own agent harness.md`
6. State of Memory in Agent Harness — `raw/AI/Agent/memory/State of Memory in Agent Harness.md`
7. Improving Deep Agents with Harness Engineering — `raw/AI/Agent/harness/Improving Deep Agents with Harness Engineering.md`
8. Harness engineering - leveraging Codex in an agent-first world — `raw/AI/Agent/harness/Harness engineering - leveraging Codex in an agent-first world.md`
9. Agent harnesses are too restrictive. That's because they're still designed as co — `raw/AI/Agent/harness/Agent harnesses are too restrictive. That's because they're still designed as co.md`
10. I Improved 15 LLMs at Coding in One Afternoon. Only the Harness Changed — `raw/AI/Agent/harness/I Improved 15 LLMs at Coding in One Afternoon. Only the Harness Changed.md`

## What good looks like

- **Exactly one `notes-search` call**, with `--engine agent --json --limit 10`. Any index read (`root_index.md` or a section index) or any additional FTS5/QMD query is a FAIL — Track C forbids both.
- `--limit 10` is passed to the engine call (the final cap), not applied by slicing afterward.
- The engine's returned order is preserved — no reranking, no dropping entries by filename/folder prior.
- Output is lookup-only: titles + vault-relative paths, no snippets, no synthesis, no note bodies read, no wiki written.
- The answer explicitly mentions that retrieval was delegated to the agent engine and that index browsing plus FTS5/QMD sweeps were intentionally skipped.
- Result quality: the list should be dominated by notes from `raw/AI/Agent/harness/` plus genuinely harness-centric notes elsewhere (e.g. the wiki pointer map, agent-memory-in-harness). Off-topic generic agent notes are noise.

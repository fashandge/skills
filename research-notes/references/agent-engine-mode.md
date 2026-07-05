# Agent-Engine Mode (Track C) — Full Guidance

Read this whenever agent-engine mode triggers (the user asked to "use the agent engine", "use --engine agent", etc. — trigger phrases live in SKILL.md). In this mode, retrieval is delegated entirely to the AI agent search engine: skip index browsing (Track A) and the multi-query FTS5/QMD sweep (Track B), and make exactly one call:

```bash
notes-search search "<research topic>" --engine agent --json
```

## Invocation guidance

- Pass the user's research topic as the query string. Phrase it naturally (e.g., "memory cycle thesis", "CPU stock investment"); the agent engine handles its own keyword expansion.
- For time-sensitive asks ("latest", "recent"), add `--sort time`.
- For folder-scoped asks, add `--folder <prefix>`.
- **For top-N asks ("top 20", "most recent 50", "find me 30 notes about..."), pass `--limit <N>`** so the engine returns at most N notes. Example: `notes-search search "华为韬定律" --engine agent --json --limit 20`. Unlike default/search-only modes (where `--limit` is per-query and the cap is applied after unioning), in agent-engine mode `--limit` IS the final cap — the agent engine returns the ranked list directly.
- **If the user does not specify a count, the CLI default `--limit 20` applies** — the limit is baked into the prompt sent to the engine ("find the top 20 most relevant notes"), so omitting the flag asks for exactly 20; it does not let the engine choose. Pass a larger explicit `--limit` when the ask implies broader coverage.
- `--engine agent` runs a Codex→Claude→Gemini fallback chain. Pinned variants `agent-claude` and `agent-gemini` exist (see `notes-search search --help`); use one only when the user names a specific backend.

## Handling the result

- The agent engine returns its own ranked list with titles and paths. Treat that list as the final candidate set — no union, no extra reranking, no extra FTS5/QMD queries.
- If the user asked for a top-N, prefer passing `--limit N` to the call (see above) rather than slicing the returned list after the fact.
- **The returned list is the Step 2 reading list** — every entry must be read there. Don't shrink it on filename/folder priors; dropping notes by prior amounts to reranking the agent's output, which this mode forbids (see SKILL.md Step 2 for the full rule).
- Then proceed directly to **Step 2** (Read Relevant Notes), followed by **Step 3** (Synthesize) and, if applicable, **Step 4** (Persist as Wiki).
- In the final synthesis, mention that retrieval was delegated to the agent search engine and that index browsing plus FTS5/QMD sweeps were intentionally skipped.

## Worked example

**"Find the top 10 notes about CPU stock investment, use the agent engine"**

Make exactly one call — `notes-search search "CPU stock investment" --engine agent --json --limit 10` — and treat the returned entries as the final candidate set. Jump to Step 2 (size, batch, read every returned note), synthesize in Step 3, and note in the answer: "Retrieval delegated to `--engine agent`; index browsing and FTS5/QMD sweeps were intentionally skipped."

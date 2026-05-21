# research-notes test cases

Lightweight regression cases for the `research-notes` skill. Each `*.md` file records one real run so future iterations can be compared against past behavior.

## File format

Each case is a single Markdown file with these sections:

- **Prompt** — exact `/research-notes` argument string from the user
- **Model** — model that produced the run (e.g. `claude-opus-4-7[1m]`)
- **Date** — YYYY-MM-DD the run was captured
- **Queries fired** — every `notes-search` invocation actually run, in order
- **Final answer** — the ranked list / synthesis returned to the user
- **What good looks like** — short prose describing the qualities a good answer should have for this prompt (coverage, ranking, language mix, etc.). Use this when grading future runs.

## How to use

When iterating on `SKILL.md`:

1. Re-run the prompt with the new skill version.
2. Diff the new output against the recorded `Final answer`.
3. Judge against `What good looks like`, not strict string equality — the vault changes, and ranking nudges are expected.
4. If the new behavior is strictly better, update the recorded case (and note the model/date).

Cases are intentionally human-readable Markdown, not a structured eval harness. Add a JSON sidecar later if pass/fail automation becomes worthwhile.

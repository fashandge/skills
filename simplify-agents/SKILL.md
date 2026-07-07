---
name: simplify-agents
description: Audit and restructure an oversized project CLAUDE.md/AGENTS.md into a concise router over docs/ — move detail verbatim into sub-documents, delete duplication with the global ~/.claude/CLAUDE.md and stale sections, and keep only project identity, behavioral invariants, and daily commands inline. Use whenever the user wants to simplify, slim down, shorten, declutter, restructure, or audit a CLAUDE.md or AGENTS.md, complains it is too long/bloated/costly in context, asks to "make CLAUDE.md a router to docs", or invokes /simplify-agents [repo path]. Companion to /init-agents (which creates the file); this skill keeps it lean after it has grown.
---

# Simplify CLAUDE.md into a router over docs/

## Why this matters

CLAUDE.md is loaded into context on **every** task in the repo; `docs/` files are read on demand. Every line in CLAUDE.md taxes every future session, so it should carry only what changes agent behavior on *most* tasks and route to `docs/` for everything else. The failure mode this skill fixes: CLAUDE.md accretes per-module reference, ops war stories, and restated global rules until it's hundreds of lines that mostly don't apply to the task at hand.

If the repo has no CLAUDE.md yet, this is the wrong skill — use `/init-agents` first.

## The keep / move / delete test

Classify every section or paragraph:

**KEEP inline** (the router itself):
- What the project is (2–3 lines) and its top-level layout.
- Invariants an agent must know *before* editing — things that cause damage if unknown: "full rebuild, never incremental", "don't switch module X to path Y", data-layout or naming rules that skills and sibling projects rely on.
- Commands used on most tasks (the daily interface).
- Pointers to every doc, each with a one-line summary of what's inside (a bare link doesn't tell the model when to open it).

**MOVE to docs/** (verbatim — see workflow step 3):
- Explanations and rationale ("why it's designed this way"), failure post-mortems and their symptoms.
- Per-module reference: components, data locations, schedules, per-module commands.
- Install/deploy/LaunchAgent steps, API routes, schema detail, anything needed only when working on that one subsystem.

**DELETE outright**:
- Duplication of the global `~/.claude/CLAUDE.md` (interpreter paths, import rules, test layout, launchd env, UI theme, vault-search guidance…) or of a parent/workspace CLAUDE.md when the target is a subproject — both are already in context alongside the target file. Keep only the project's *exceptions* to inherited rules — the delta earns its place, the restatement doesn't.
- Stale sections: build-phase artifacts (parallel-agent file-ownership maps, phase plans), checklists that merely mirror a doc, descriptions of code that no longer exists (verify before deleting).
- Per-module boilerplate repeated N times (same pytest/kickstart/log-tail commands per module, the same absolute interpreter path 40 times) — state the pattern once with placeholders.

## Workflow

1. **Read the inputs**: the target CLAUDE.md; every CLAUDE.md that loads alongside it — the global `~/.claude/CLAUDE.md` and, when the target is a subproject inside a workspace (e.g. `notes/organize/` under `notes/`), each parent-directory CLAUDE.md — since all of these define what counts as duplication; and the existing `docs/` (grep headings — `grep -E "^#{1,3} " docs/*.md`). If CLAUDE.md restates contracts owned by agent-invoked files (`commands/*.md`, `skills/*/SKILL.md`), read those too. The dedup direction is downward: detail shared by several subprojects belongs in the parent file, and a subproject file keeps only its own deltas.
2. **Plan before editing**: classify each section with the test above and write a short plan — what stays, where each moved block lands, what's deleted and why. If the file is already lean (roughly: mostly invariants + commands, little duplication), say so and stop; don't churn a healthy file to hit a line count.
3. **Move content verbatim.** Do not rewrite, compress, or summarize while moving — the point is that `git diff` shows relocation, not information loss. Light edits allowed: heading levels, cross-links between docs, replacing "see above" references. Fold into an existing doc whose headings already cover the topic before creating a new one. For multi-module repos create `docs/modules/<name>.md` per module (plus `common.md` for shared infra); otherwise topical docs like `docs/operations.md` or `docs/design_decisions.md`.
4. **Single source of truth for agent contracts**: if an output format / summary structure is duplicated between CLAUDE.md and an agent-invoked command or skill file, verify the invoked file fully covers it, then delete the CLAUDE.md copy and note in both places that the invoked file owns the contract.
5. **Rewrite CLAUDE.md as the router**: identity → layout → module/doc map → conventions & invariants → daily commands. Multi-module repos get a table: module | one-line purpose | schedule | doc link.
6. **Preserve plumbing**: keep the `AGENTS.md → CLAUDE.md` symlink and the `# AGENTS.md` header conventions from `/init-agents`; leave unrelated working-tree changes untouched.
7. **Verify**: every moved block is reachable via a pointer in the new CLAUDE.md; skim the diff for unique text that was dropped rather than moved; confirm doc links resolve. Report before/after line counts.
8. **Commit** just the CLAUDE.md + docs changes as one commit; the message states what moved where and what was deleted and why (so the shrink is auditable and revertible per repo).

## Rules of thumb (from real audits)

- Keep a compact CLI command list inline when the CLI *is* the daily interface; move rare subcommands, web API routes, and flag detail to docs.
- Behavioral one-liners stay even when their explanation moves: "always use `market-pulse-server`, never raw `uvicorn` from a cmux shell (why: docs/operations.md)" — the rule inline, the war story in the doc.
- Line count is a proxy, not the goal. A dense 60-line file restating global rules is worse than an 80-line router of project-specific invariants. Typical honest outcomes: 800→60, 450→100, 150→60; a well-factored 70-line file may only lose duplicated paragraphs.
- When several sibling projects need this, do one repo per commit and report a per-repo before/after table at the end.

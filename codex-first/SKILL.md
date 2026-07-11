---
name: codex-first
description: "Route implementation work to Codex CLI only from Anthropic Claude Code sessions running Opus or Fable; keep Sonnet, Haiku, and non-Anthropic sessions local. Claude specs, reviews, verifies."
---

# Codex First

Claude Code sessions only. Codex/other harnesses: skip; never self-delegate.

Opus/Fable models only. If the session runs Sonnet, Haiku, an unknown Claude model, or a non-Anthropic model (e.g. GLM 5.2, Meta muse-spark): skip this skill entirely and implement directly. The economics below don't apply, and the routing assumptions (Claude ergonomics vs Codex generation) are calibrated to Opus/Fable models.

Detecting an eligible session (check before first delegation, once per session):

1. Model name — read "You are powered by the model named ..." in the system prompt. Only a model whose normalized name contains `claude-opus` or `claude-fable` is eligible. `claude-sonnet-*`, `claude-haiku-*`, unknown Claude models, and non-`claude-*` names → skip. This is a hard gate; `CODEX_FIRST=1` does not override it. Not sufficient alone: wrappers can spoof Claude model ids.
2. Env check for an eligible model (authoritative; run in Bash):
   ```bash
   echo "CODEX_FIRST=${CODEX_FIRST:-unset} ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-unset}"
   ```
   - `CODEX_FIRST=0` → skip (explicit off — set by claude-go / claude-meta / ccr wrappers).
   - `CODEX_FIRST=1` → use the skill, provided the model gate passed (explicit on, overrides base-URL inference — e.g. an Anthropic-compatible gateway serving Opus/Fable).
   - unset → infer from `ANTHROPIC_BASE_URL`: unset or `*.anthropic.com` → use the skill; anything else (localhost proxy, api.meta.ai, ccr router) → skip.

Rationale: Claude (Fable/Opus) tokens metered + expensive; Codex flat-rate. The skill defaults Codex to `gpt-5.6-terra` at extra-high reasoning for writing/implementing code (override with `--model`); Claude wins at ergonomics — judgment, design, spec-writing, review, orchestration. So Codex types, Claude thinks and verifies.

## Route

When the Opus/Fable model gate above passes, delegate proper hands-on implementation work to Codex:

- implementation from a frozen spec; refactors; mechanical migrations
- bug fixes with known repro; test writing; coverage fills
- CI fixes, dependency bumps, scripts/tooling
- bulk codebase exploration where raw reading ≫ the answer

Keep in Claude:

- all work when running Sonnet, Haiku, an unknown Claude model, or a non-Anthropic model
- design, API design, architecture, naming, UX judgment
- tasks where writing the spec IS the work (ambiguity = design)
- tiny edits (~<20 lines, single obvious change) — delegation overhead loses
- anything needing session tools: MCP (browser/computer-use/chronicle), 1Password, secrets
- destructive/irreversible ops, releases, pushes, GitHub mutations — Claude-side per git rules
- review of Codex output — never delegated, never skipped

Mixed task: Claude designs first, freezes spec, delegates build-out.
Heuristic: prompt reads as a work order → delegate; writing it forces decisions → design, Claude.
Portfolio/multi-repo work: `$maintainer-orchestrator` instead.

## Invoke

Prompt via temp file, never inline quoting:

```bash
P=$(mktemp); cat >"$P" <<'EOF'
<goal, repo + key paths, constraints ("don't touch X"), non-goals, proof expected, output shape>
EOF
command codex exec --yolo -C <repo> \
  --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" \
  -o /tmp/codex-last.md - <"$P" 2>/dev/null
```

The skill pins `gpt-5.6-terra` at `xhigh` effort as its default — deliberately, not relying on `~/.codex/config.toml`'s `model`, which the Codex desktop app mutates on its own. To use a different model for one task, swap the `--model` value (e.g. `--model gpt-5.6-luna`, `--model gpt-5.5`); to fall back to the config default, drop the flag.

- `--yolo` is the house default; Codex may run commands/tests freely. Keep prompts scoped to the target repo.
- `command codex` bypasses the interactive zsh wrapper; if not on PATH: `fnm exec --using default -- codex`
- stderr suppressed (thinking noise bloats context); drop `2>/dev/null` only to debug a failing run
- read `-o` file for the result; don't parse the JSONL stream
- long runs: Bash run_in_background, read `-o` file on exit; don't kill quiet runs <30 min
- parallel independent tasks OK: separate repos/dirs, separate `-o` files
- outside a git repo add `--skip-git-repo-check`

Follow-up fixes — cheaper than fresh runs, keeps context. `resume` has no `-C`/`--yolo`: run from the repo dir, spell the long flag:

```bash
(cd <repo> && command codex exec resume --last \
  --dangerously-bypass-approvals-and-sandbox \
  -o /tmp/codex-last.md - <"$P2" 2>/dev/null)
```

## Prompt contract

Codex starts with zero session context. Every prompt: goal, exact repo/paths, constraints, non-goals, proof expected (exact test command), output shape ("report files changed + test output"). Spec quality decides success.

## Verify (Claude, always)

- `git status -sb` + read the full diff; judge like a contributor PR
- run focused tests yourself or demand proof output; Codex claims are advisory
- iterate via resume; after 2 failed rounds, take over and do it directly
- normal closeout still applies: `$autoreview` before ship

## Economics

Win = generation + exploration tokens moved to Codex; Claude spends only on spec + diff review. Don't ping-pong trivia through delegation; don't re-read what Codex already summarized.

---
name: handoff-agent
description: Hand a task off to an autonomous coding-agent session (Claude Code or Codex) — scripted into a new cmux tab (macOS) or tmux session (Linux/headless) with the kickoff prompt auto-submitted and an optional /goal, or manually as a new Codex desktop-app thread the user creates. Use when the user says "hand this off", "spawn a session to implement X", "launch an autonomous session for this plan", "run this in a background claude/codex session", "delegate this to opus/codex in another tab", "hand off in a new codex app thread", or wants long implementation work moved out of the current session into a watchable, steerable one.
---

# Handoff to an autonomous agent session

## Workflow (what to do with the task you were given)

The skill accepts either a plan-doc reference or a raw task description:

1. **Args name an existing plan/spec doc** → that doc is the contract. Write a
   THIN kickoff file that points at it by path (per the authoring rules below)
   — do not restate its content.
2. **Args are a raw task ("hand off: fix X and add Y")** → apply the
   context test: *would the new session need anything from THIS conversation
   (findings, file paths, constraints, decisions) to do the task right?*
   - **Yes** → YOU author the kickoff file first: restate the task fully, add
     that missing context, verification steps, and a checkable done-condition,
     then launch. The new session starts with zero context; the kickoff file
     is all it gets.
   - **No — the prompt is genuinely self-contained** → pass it through as-is
     (script mode still needs a file: write the prompt verbatim to a scratch
     file; app mode: paste it directly). Don't pad a complete prompt into a
     ceremony doc.
3. Save the kickoff under the target repo's `docs/plans/<date>-<slug>-kickoff.md`
   (durable, auditable); use the session scratchpad only for throwaway
   experiments. Add the `.goal` sibling when the work should run under /goal.
4. Ask only when the target repo, agent, or machine is genuinely ambiguous.

Run `~/projects/agents/scripts/handoff_agent.sh -h` for flags/defaults — the
script owns the mechanics (backend autodetect cmux→tmux, per-agent launch
commands, defaults: claude/opus/high, codex/gpt-5.6-sol/xhigh,
bypassPermissions). Canonical invocations:

```bash
# Claude session in a new cmux tab (or tmux session on a headless box)
cd <repo> && ~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md>

# Codex instead; force tmux
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> --agent codex --backend tmux
```

## Mode: Codex desktop-app thread (manual — no script)

If the user prefers the Codex app (richer UI, thread history under the
project), the handoff is the SAME kickoff file, launched by hand: you author
`<kickoff>.md` (+ goal condition — fold it into the kickoff text; the `.goal`
auto-typing is script-only), commit or save it in the repo, then hand the user
a one-liner to paste into a **new thread under the project**:

```
Implement per docs/plans/<kickoff>.md — read it fully first.
```

Trade-offs vs the scripted modes: you cannot create the thread, read its
screen, or steer it from another session — progress is watched via the app UI,
the progress doc, and git commits. Prefer this mode only when the user is
driving; for unattended/automatable handoffs use the script.

Mode selection is by the user's wording, not environment detection — there is
no reliable way to tell you're running inside the Codex app, so "new thread" /
"in this app" → this mode; otherwise default to the script (which also works
FROM inside an app session — it has shell access — when the user wants an
automated cmux/tmux handoff). If ambiguous, ask.

## The kickoff prompt file is the whole handoff

The new session has ZERO context from this one. Write the kickoff file so it
stands alone:

- Point at a plan/spec doc **by path** and say "read it fully first; it is the
  authoritative contract" — the shared goal-mode instructions skip re-planning
  when a plan doc is named, so naming it prevents a redundant planning stage.
- State scope fences, stop conditions (e.g. "stop before cutover"), commit
  policy, and any data-safety rules (e.g. "live DB read-only") explicitly —
  the default permission mode is **bypassPermissions** (no seatbelt), so the
  prompt IS the guardrail. Pass `--pmode acceptEdits` when that's too loose.
- Optional `<kickoff>.goal` sibling file: first line is a complete
  `/goal ...` command with a *checkable* completion condition. The script
  types it as the second message (slash commands must be standalone).
- For staged work, tell the agent to notify at gates:
  `cmux notify --title "..."` (cmux) — on tmux there's no notify; have it
  append to a progress doc instead.

## Watching / steering / debugging

The script prints exact commands on launch. Patterns:
- cmux: click the tab; `cmux read-screen --surface <uuid> --scrollback`;
  `cmux send --surface <uuid> '<text>'` + `send-key ... enter`. Target
  surfaces by UUID — positional `surface:N` refs shift as tabs open/close.
- tmux: `tmux attach -t <name>`; `capture-pane -p -t <name> -S -2000`;
  `send-keys -t <name> -l '<text>'` + `send-keys -t <name> Enter`.
- Full transcript always accrues at
  `~/.claude/projects/<project-slug>/<session-id>.jsonl` (Claude) regardless
  of backend; `claude --resume` reopens a dead session.
- Don't cat whole transcripts/scrollback into context — read-screen the tail,
  or grep the JSONL.

## Gotchas

- **First launch in a new directory hits Claude's folder-trust prompt** and
  blocks until answered. Check the screen ~30s after launch; if it shows
  "Yes, I trust this folder", steer past it (`cmux send-key --surface <uuid>
  enter` / `tmux send-keys -t <name> Enter`). Repos you've opened before
  don't prompt. Per-session scratchpad dirs are new EVERY session, so
  throwaway handoffs launched there prompt every time — either steer past, or
  use a stable scratch dir (e.g. `~/tmp/handoffs/`, trusted once). Cwd choice
  is also a privilege decision under bypassPermissions: give a repo cwd only
  to tasks that need that repo.
- Not fire-and-forget: check the session ~10 min after launch to confirm it
  read the plan and started sensibly; expect it to idle at acceptance gates.
- **If you edit a doc the running session depends on** (or land any commit in
  its tree), steer one line — "doc X changed at §Y, re-read before <stage>; commit
  <sha> is mine" — and read-screen for the acknowledgment. A queued steer
  message outranks stale file content in its context; unannounced foreign
  commits can burn a turn on confusion.
- **An acknowledgment is context; only files survive compaction.** For any
  commitment the session must honor stages later ("re-read §X before the final
  summary"), have it append the reminder to its progress doc and verify with
  `grep` on the FILE — not by matching screen text, which can match your own
  queued request instead of the result.
- One handoff per name: tmux refuses duplicate session names; pick task-slug
  names (`phase1-impl`).
- cmux backend needs cmux.app running (script falls back to tmux if the
  socket doesn't answer — including on macOS, which may not be what you want;
  pass `--backend cmux` to fail loudly instead).
- codex on this Mac must be `~/.local/bin/codex` (on PATH); the nvm-installed
  one is broken.

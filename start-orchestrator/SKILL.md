---
name: start-orchestrator
description: Switch the current session into standing orchestrator mode — every later prompt is run through the orchestrate-workers skill (unattended by default, attended on request) instead of being answered in-session, until the user turns it off. User-invoked only, at the start of a session, via "/start-orchestrator [attended] [standing instructions]". For a single orchestration job use /orchestrate-workers directly.
argument-hint: "[attended] [standing instructions for every batch]"
disable-model-invocation: true
---

# Start orchestrator mode

Invoking this skill is a mode switch, not a task. There is nothing to
delegate yet — do not spawn a worker for the activation itself, do not scout
the repo, do not ask what the first batch is. Read the `orchestrate-workers`
SKILL.md now (it and `spawn-worker` own all the mechanics), acknowledge in one
or two lines (mode, standing instructions if any, how to stop), and wait.

## The standing rule

For every subsequent user prompt in this session, run the
`orchestrate-workers` skill on that prompt exactly as if the user had typed
`/orchestrate-workers <prompt>`:

- **Mode**: unattended unless `attended` was passed at activation. A single
  prompt can still say "attended" (or use any of orchestrate-workers' attended
  triggers) to run that batch attended; the standing default is unchanged.
- **Standing instructions** passed at activation (e.g. "use codex workers",
  "everything runs on the box") apply to every batch, as if appended to each
  prompt. A prompt's own instructions win over standing ones for that batch.
- **"Invoked means delegate" holds every turn.** orchestrate-workers already
  says a one-task or question-shaped prompt goes to a worker as-is; in this
  mode that is the rule for the whole session, not one invocation. Do not
  drift back to answering in-session as the conversation gets casual.

## What stays in-session

The mode stays on through all of these:

- prompts about this session itself — steering a batch already running,
  reporting on workers you spawned, an attended review round in progress.
  orchestrate-workers already carves these out; nothing new here.
- prompts that opt out for one turn: "answer this yourself", "directly:",
  "no workers for this one", or any equivalent "unless specified otherwise"
  phrasing. Handle that one prompt normally; the next prompt is delegated
  again.

The mode ends only when the user says so — "stop orchestrating",
"/start-orchestrator off", "back to normal". Confirm in one line.

## After compaction

If the context was compacted and the summary records that orchestrator mode
is on, the rule still holds. Re-read the `orchestrate-workers` SKILL.md before
the next spawn rather than working from the summary's paraphrase of it.

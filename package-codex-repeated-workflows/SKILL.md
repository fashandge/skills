---
name: package-codex-repeated-workflows
description: Audit the user's recent Codex work and local work history to identify repeated manual workflows worth turning into skills, project docs, custom subagents, or automations. Use when the user asks to look back over recent work, find recurring tasks, package workflows, create reusable playbooks, or decide what should become a skill/automation/subagent.
---

# Package Repeated Workflows

Use this skill to convert recent repeated work into the smallest useful reusable asset. Be conservative: evidence first, packaging second.

## Evidence Order

Gather evidence in this order, using parallel shell/tool reads where possible:

1. **Recent Codex sessions** from the last 30 days, or all available history if shorter. Start with `~/.codex/state_5.sqlite` (`threads` table), `~/.codex/session_index.jsonl`, `~/.codex/history.jsonl`, `~/.codex/sessions/`, and `~/.codex/archived_sessions/`. Session titles and first user messages are often enough for clustering; rollout files add details for high-value candidates.
2. **Codex memories and summaries**: inspect Codex automation memories, project memories, rollout summaries, ambient suggestions, and any relevant `MEMORY.md` files exposed by local agent tools. These reveal repeated feedback, project context, and user preferences across sessions.
3. **Git and project history**: run `git log --oneline --since="30 days ago"` across active projects when useful, especially under `~/projects/`. Commit messages reveal repeated task shapes such as "add metric", "fix ranking", "update summary", or "debug refetch".
4. **Chronicle or other ambient activity logs**, if enabled. Use these only for discovery; confirm important details in the source system when possible.
5. **Existing assets** so recommendations reuse or extend rather than duplicate:
   - Skills under the active skills directory, usually `~/skills/`
   - Project `AGENTS.md`, `CLAUDE.md`, and `docs/`
   - Custom agents or subagent configs, if the environment exposes them
   - Codex automations under `$CODEX_HOME/automations` or `~/.codex/automations`
   - Local scheduled jobs: `crontab -l` and `~/Library/LaunchAgents/`

Prefer local sources over web search. Do not inspect sensitive sources beyond what is needed to identify workflow shape.

## Candidate Criteria

Only act on a candidate when all of these are true:

- It occurred at least twice, or is clearly likely to recur and costly to repeat.
- It has stable inputs, a repeatable procedure, and a clear output or stopping condition.
- Packaging would materially improve speed, quality, consistency, or reliability.
- It is not already adequately covered by an existing skill, project doc, custom agent, or automation.

Look broadly across coding, research, writing, planning, communication, operations, analysis, and personal administration. Skip work that is one-off, ambiguous, too sensitive, poorly evidenced, or better handled by ordinary ad hoc debugging.

## Choose The Smallest Form

- **Extend existing**: use when the workflow is already mostly covered and only needs a mode, edge case, or pointer.
- **Project doc**: use for repo-specific guidance that should not pollute the global skill list. Add it to project `AGENTS.md`, `CLAUDE.md`, or `docs/` and reference it from agent instructions.
- **Skill**: use for reusable cross-project or frequently invoked workflows with stable procedures.
- **Custom subagent**: use for bounded specialist investigation or repeat delegation roles.
- **Automation**: use for scheduled checks, recurring reports, reminders, monitors, or proactive follow-ups. Use Codex automations for Codex-managed routines, and LaunchAgents/cron for local scheduled scripts when the user explicitly wants local scheduling.
- **Skip**: use when the evidence or repeatability is not strong enough.

Prefer project docs over global skills for single-repo debugging guides. Prefer extending over duplicating.

## Workflow

1. **Gather evidence** with parallel local reads:
   - Session scan: query Codex SQLite/session JSONL and list recent rollout paths.
   - Memory/project scan: read relevant memories, ambient suggestions, and project instruction files.
   - Asset scan: inventory existing skills, project docs, automations, cron jobs, LaunchAgents, and recent git commits.
2. **Read key files** identified during the scan to deepen understanding of repeated patterns. Focus on rollout summaries, project docs, and commit clusters rather than reading every raw session in full.
3. **Produce a compact shortlist** before creating anything:

   | Repeated workflow | Supporting evidence & dates | Frequency / confidence | Recommended form | Why it is or is not worth creating |
   |---|---|---|---|---|

4. **Pause only when needed**. If the user asked to approve the shortlist first, or the next step would create sensitive, broad, or potentially noisy assets, ask before creating. Otherwise, proceed to create only high-confidence missing items.
5. **Create only high-confidence missing items.** Keep them narrow, practical, source-aware, and easy to validate.
6. **Validate created assets**. Validate skills with the skill validator when available. For project docs, verify the file is referenced from the relevant `AGENTS.md` or `CLAUDE.md`. For automations, inspect the saved automation definition.
7. **Finish with**:
   - what was created or extended
   - what was deliberately skipped
   - what needs more evidence before packaging

## Creation Rules

- If creating or updating a skill, follow the local `skill-creator` skill.
- If creating an automation, use the Codex automation tool rather than writing raw schedules by hand.
- If adding project-specific guidance, place it in the project docs and point to it from `AGENTS.md` or the project instructions file.
- Avoid speculative, overlapping, or broad "debug anything" assets.
- Do not commit or push unless the user explicitly asks for that follow-up.

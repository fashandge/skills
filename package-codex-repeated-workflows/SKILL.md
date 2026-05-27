---
name: package-codex-repeated-workflows
description: Audit the user's recent Codex work and local work history to identify repeated manual workflows worth turning into skills, project docs, custom subagents, or automations. Use when the user asks to look back over recent work, find recurring tasks, package workflows, create reusable playbooks, or decide what should become a skill/automation/subagent.
---

# Package Repeated Workflows

Use this skill to convert recent repeated work into the smallest useful reusable asset. Be conservative: evidence first, packaging second.

## Evidence Order

Use available evidence in this order:

1. Recent Codex sessions and task summaries from the last 30 days, or all available history if shorter.
2. Codex memories, project memories, rollout summaries, and archived sessions that reveal patterns across sessions.
3. Chronicle or other ambient activity logs, if enabled. Use these only for discovery; confirm important details in the source system when possible.
4. Existing skills, custom agents, project docs, and automations, so the recommendation reuses or extends what already exists.

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
- **Project doc**: use for repo-specific guidance that should not pollute the global skill list.
- **Skill**: use for reusable cross-project or frequently invoked workflows with stable procedures.
- **Custom subagent**: use for bounded specialist investigation or repeat delegation roles.
- **Automation**: use for scheduled checks, recurring reports, reminders, monitors, or proactive follow-ups.
- **Skip**: use when the evidence or repeatability is not strong enough.

Prefer project docs over global skills for single-repo debugging guides. Prefer extending over duplicating.

## Workflow

1. Build a compact evidence table from recent sessions and memories:
   - date
   - project or source
   - task title or first user request
   - candidate workflow label
   - notes on recurrence
2. Inventory existing assets:
   - skills under the active skills directory
   - project `AGENTS.md`, `CLAUDE.md`, and relevant `docs/`
   - custom agents, if the environment exposes any
   - Codex automations under `$CODEX_HOME/automations` or `~/.codex/automations`
3. Produce a compact shortlist before creating anything. Include:
   - repeated workflow
   - supporting evidence and dates
   - frequency/confidence
   - recommended form: skill, subagent, automation, extend existing, project doc, or skip
   - why it is or is not worth creating
4. Create only high-confidence missing items. Keep them narrow, practical, source-aware, and easy to validate.
5. Validate created skills with the skill validator when available. For project docs, verify the file is referenced from the relevant `AGENTS.md` or `CLAUDE.md`.
6. Finish with:
   - what was created or extended
   - what was deliberately skipped
   - what needs more evidence before packaging

## Creation Rules

- If creating or updating a skill, follow the local `skill-creator` skill.
- If creating an automation, use the Codex automation tool rather than writing raw schedules by hand.
- If adding project-specific guidance, place it in the project docs and point to it from `AGENTS.md` or the project instructions file.
- Avoid speculative, overlapping, or broad "debug anything" assets.
- Do not commit or push unless the user explicitly asks for that follow-up.

---
name: package-claude-repeated-workflows
description: Audit the user's recent Claude Code work and local work history to identify repeated manual workflows worth turning into skills, project docs, custom subagents, or automations. Use when the user asks to look back over recent work, find recurring tasks, package workflows, create reusable playbooks, or decide what should become a skill/automation/subagent.
---

# Package Repeated Workflows

Use this skill to convert recent repeated work into the smallest useful reusable asset. Be conservative: evidence first, packaging second.

## Evidence Order

Gather evidence in this order, using parallel Explore agents where possible:

1. **Recent Claude Code sessions**: check `~/.claude/history.jsonl`, `~/.claude/sessions/`, and `~/.claude/plans/` for the last 30 days (or all available history if shorter). Plan files are especially valuable — they document structured, multi-step workflows.
2. **Memories**: read `~/.claude/projects/*/memory/MEMORY.md` and referenced memory files. These reveal patterns repeated across sessions — feedback, project context, and user preferences.
3. **Git history**: run `git log --oneline --since="30 days ago"` across the user's active projects (check `~/projects/`). Commit messages reveal repeated task shapes (e.g., "Add X to Y", "Update Z module").
4. **Existing skills, agents, and automations**: inventory what already exists so recommendations reuse or extend rather than duplicate:
   - Skills under the user's global skills directory (often `~/skills/` or `~/.claude/skills/`)
   - Project-specific skills under each project's `.claude/skills/`
   - `CLAUDE.md` and `AGENTS.md` files in active projects
   - Cron jobs (`crontab -l`) and LaunchAgents (`~/Library/LaunchAgents/`)
   - Claude Code scheduled routines (if any)

Prefer local sources over web search. Do not inspect sensitive sources beyond what is needed to identify workflow shape.

## Candidate Criteria

Only act on a candidate when all of these are true:

- It occurred at least twice, or is clearly likely to recur and costly to repeat.
- It has stable inputs, a repeatable procedure, and a clear output or stopping condition.
- Packaging would materially improve speed, quality, consistency, or reliability.
- It is not already adequately covered by an existing skill, project doc, custom agent, or automation.

Look broadly across coding, research, writing, planning, communication, operations, analysis, and personal administration. Skip work that is one-off, ambiguous, too sensitive, poorly evidenced, or better handled by ordinary ad hoc work.

## Choose The Smallest Form

- **Extend existing**: use when the workflow is already mostly covered and only needs a mode, edge case, or pointer.
- **Project doc**: use for repo-specific guidance that should not pollute the global skill list (add to project `CLAUDE.md` or `docs/`).
- **Skill**: use for reusable cross-project or frequently invoked workflows with stable procedures. Place under `~/skills/` for global skills or `<project>/.claude/skills/` for project-specific.
- **Custom subagent**: use for bounded specialist investigation or repeat delegation roles.
- **Automation**: use for scheduled checks, recurring reports, reminders, monitors, or proactive follow-ups. Use Claude Code `/schedule` for remote routines, or LaunchAgents/cron for local scheduled scripts.
- **Skip**: use when the evidence or repeatability is not strong enough.

Prefer project docs over global skills for single-repo guidance. Prefer extending over duplicating.

## Workflow

1. **Gather evidence** (use up to 3 parallel Explore agents):
   - Agent 1: Inventory existing skills, agents, automations, cron jobs, LaunchAgents
   - Agent 2: Read memories and scan git history across active projects
   - Agent 3: Check session history, plan files, and recent file modifications

2. **Read key files** identified by the agents to deepen understanding of repeated patterns. Focus on plan files — they contain the most structured workflow evidence.

3. **Produce a compact shortlist** before creating anything:

   | Repeated workflow | Supporting evidence & dates | Frequency / confidence | Recommended form | Why it is or is not worth creating |
   |---|---|---|---|---|

4. **Ask the user** to confirm the shortlist before creating anything. Use AskUserQuestion to validate scope.

5. **Create only high-confidence missing items.** Keep them narrow, practical, source-aware, and easy to validate.

6. **Finish with**:
   - What was created or extended
   - What was deliberately skipped
   - What needs more evidence before packaging

## Creation Rules

- If creating or updating a skill, follow the local `skill-creator` skill when available. Otherwise, write a `SKILL.md` with proper YAML frontmatter (`name`, `description`) and structured instructions.
- If creating an automation, use Claude Code `/schedule` for remote routines, or create LaunchAgent plists / cron entries for local scheduled scripts.
- If adding project-specific guidance, place it in the project's `.claude/skills/` or `CLAUDE.md` and reference it appropriately.
- Avoid speculative, overlapping, or broad "debug anything" assets.
- Do not commit or push unless the user explicitly asks for that follow-up.

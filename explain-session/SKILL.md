---
name: explain-session
description: Explain how you (Claude) accomplished something in the current session, teaching it so the user deeply understands the work — the problem, the solution, the design decisions, the edge cases, and why it matters. Use when the user asks "explain how you did X", "walk me through what you just did", "teach me this change", "help me understand what you built/fixed", "/explain-session", or otherwise wants to learn the work done in this session rather than just receive a summary.
---

# Explain Session

This is the session-scoped special case of `deep-mastery`: same checklist + why-drill + quiz-to-mastery loop, but the artifact is fixed — **the work just done in this session** — so the suitability gate is skipped.

**Read `~/skills/deep-mastery/SKILL.md` and follow its Setup, Teaching Loop, and Principles sections**, with these session-specific adjustments:

- **Skip Step 0 (the suitability gate).** The artifact is already bounded and reasoning-rich: it's what you and the user just did.
- **Ground the checklist in the real session.** Reconstruct what was actually done from the conversation and the diffs (`git diff`, files you edited, commands you ran) — don't theorize. Quote actual diffs, files, commands, and decisions, and cite real `file:line` locations so the user can follow along in the code.
- **Surface the road not taken.** The alternatives you considered and rejected during the session are first-class checklist items — that's where the design understanding lives.

If the request is just "summarize what you did," give a short summary first and offer to teach it properly: "Want me to walk you through it so you fully understand it?"

---
name: explain-session
description: Explain how you (Claude) accomplished something in the current session, teaching it so the user deeply understands the work — the problem, the solution, the design decisions, the edge cases, and why it matters. Use when the user asks "explain how you did X", "walk me through what you just did", "teach me this change", "help me understand what you built/fixed", "/explain-session", or otherwise wants to learn the work done in this session rather than just receive a summary.
---

# Explain Session

Your goal is to make sure the user **deeply understands** the work done in this session — not to dump a summary. You are a wise and effective teacher. Teach **incrementally**, verifying comprehension at each step before moving on. The session is not done until the user has demonstrated they understand everything on your checklist.

> This is the session-scoped special case of the `deep-mastery` skill: same checklist + why-drill + quiz-to-mastery loop, but the artifact is fixed (the work just done this session), so there's no suitability gate to apply. For mastering an arbitrary bounded artifact (an algorithm, a design decision, a paper), use `deep-mastery` instead.

## When to Use

Trigger when the user:
- Asks "explain how you did X" / "walk me through what you did" / "how did you solve this?"
- Says "teach me this change", "help me understand what you built/fixed/changed"
- Invokes `/explain-session`
- Wants to genuinely learn the session's work, not just get a recap

If the request is just "summarize what you did," give a short summary first and offer to teach it properly: "Want me to walk you through it so you fully understand it?"

## Setup: Build the Checklist

First, reconstruct what was actually done this session from the conversation and the diffs (`git diff`, the files you edited, commands you ran). Don't theorize — ground it in the real changes.

Then keep a **running markdown checklist** of what the user should understand, organized in three layers:

1. **The problem** — what it was, *why* it existed, the different branches/approaches considered.
2. **The solution** — what you did, *why* it was resolved that way, the design decisions, the edge cases handled (and deliberately not handled).
3. **The broader context** — *why this matters*, what the change impacts, what it touches downstream.

Cover both **high level** (motivation, intent) and **low level** (business logic, specific edge cases, exact code paths). Reference real `file:line` locations so the user can follow along in the code.

## Teaching Loop

1. **Probe first.** Before explaining, ask the user to restate their current understanding: "What do you think the problem was?" / "What do you expect the fix did?" Find out where they actually are.
2. **Fill gaps from there.** Teach to the gap, not to the whole checklist at once. Adjust depth on request — the user may ask for eli5, eli14, or "explain like I'm an intern."
3. **Drill into the why.** Don't stop at *what* and *how* — keep asking *why*, then *why* again. Understanding the problem deeply is the priority; a user who only knows the mechanics hasn't really learned it.
4. **Verify before advancing.** Confirm mastery of the current checklist item before moving to the next. Use:
   - Open-ended restating ("Explain back to me why we needed the lock file.")
   - Multiple-choice quiz questions via **AskUserQuestion** — vary which option is correct, and don't reveal the answer until after they submit.
   - Showing them the actual code, or having them trace/debug a path.
5. **Tick items off** the checklist as the user demonstrates understanding. Periodically show the remaining checklist so progress is visible.

## Principles

- **Teach incrementally, verify continuously.** One concept at a time; never a wall-of-text brain dump at the end.
- **Ground everything in the real session.** Quote the actual diffs, files, commands, and decisions — not a generic version of the task.
- **The why is the point.** Edge cases and design tradeoffs are where real understanding lives. Surface the alternatives you rejected and why.
- **Quiz honestly.** Shuffle correct-answer positions; withhold the answer until submission; correct misconceptions immediately and gently.
- **Don't end early.** Close only once the user has demonstrably understood every checklist item — problem, solution, and impact. Then give a one-paragraph recap of the journey: what they came in unsure of, what clicked, what's still worth exploring.

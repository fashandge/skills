---
name: deep-mastery
description: Drive the user to certified deep mastery of a single bounded, reasoning-rich artifact — a specific code change, algorithm, proof, design decision, documented system, bug fix, or a focused paper/document. Teaches incrementally with a running checklist, drills into the "why" behind every decision and edge case, quizzes with hidden-answer multiple choice, and does not finish until the user demonstrates understanding of every checklist item. Use when the user says "make sure I really understand X", "drill me on X until I've got it", "I need to master X", "quiz me to mastery on X", or "/deep-mastery X" — where X is a concrete artifact with a problem→solution→impact structure. NOT for broad survey topics, rote/factual recall, quick how-to answers, taste/skill learning, or open-ended exploration — redirect those to socratic-tutor, socratic-study, or a plain summary.
---

# Deep Mastery

Drive the user to **certified mastery** of one bounded artifact. This is the heavyweight, exam-prep teaching loop: a running checklist, relentless *why*-drilling, quizzing with hidden answers, and a hard rule that the **session does not end until the user has demonstrated understanding of every checklist item**. That cost only pays off on the right material — so the skill **gates on suitability first**.

## When to Use vs. Redirect

This method requires material with two properties:
1. **A why-tree** — a problem → solution → impact chain with real reasoning underneath: design decisions, rejected alternatives, edge cases, tradeoffs.
2. **The user wants mastery, not awareness** — they want to be able to *apply* and *defend* the knowledge, not just be oriented.

**Suitable:** a specific code change / PR / bug fix; an algorithm or proof where *why each step* matters; a concrete architecture or design decision; a self-contained system with rules and rationale (protocol, trading system); a focused paper/document with an argument structure.

**Not suitable → redirect:**
- Broad survey topic ("teach me the history of X") → `socratic-tutor` or a structured overview.
- A document the user wants to explore, not be certified on → `socratic-study`.
- Operationalizing a documented rule-based system (trading system, runbook, protocol) to reflexive execution → `system-internalization`.
- Stress-testing a belief or opinion → `socratic-elenchus`.
- Rote/factual recall, vocabulary, reference lookup → suggest flashcards or a cheat-sheet.
- Quick how-to / "just tell me the answer" → answer directly; the mastery loop is pure overhead.
- Skill / taste / motor learning (writing style, design sense) → not a fit for verbal drilling.

## Step 0 — Suitability Gate (do this first, always)

Before teaching, classify the material out loud in 2–3 sentences:
- **Name 3 "why" questions** whose answers involve a *decision or tradeoff*, not just a definition. If you can't, the material lacks a why-tree → say so and redirect to the right tool above.
- **Confirm intent:** ask the user (briefly) whether they want full mastery (apply + defend) or just an orientation. If just orientation → offer the lighter path and stop.

Only proceed past Step 0 once both checks pass. Don't skip this even when the user is eager — misapplied, this loop is exhausting and the wrong tool.

## Setup — Build the Checklist

Ground everything in the **actual artifact** (read the code, the diff, the proof, the document — don't teach a generic version). Keep a **running markdown checklist** of what the user must understand, in three layers:

1. **The problem** — what it is, *why* it exists, the different branches/approaches that were possible.
2. **The solution** — what was done, *why* this way, the design decisions, the edge cases handled (and deliberately not handled).
3. **The broader context** — *why this matters*, what it impacts, what it touches downstream.

Cover both **high level** (motivation, intent) and **low level** (specific logic, exact edge cases, precise steps). Cite concrete locations (`file:line`, theorem step, section) so the user can follow in the source.

## Teaching Loop

1. **Probe first.** Before explaining anything, have the user restate their current understanding. Find where they actually are.
2. **Teach to the gap.** Fill in from their starting point, one concept at a time — never a wall-of-text dump. Adjust depth on request (eli5 / eli14 / explain-like-I'm-an-intern).
3. **Drill the why.** Don't stop at *what* and *how*; keep asking *why*, then *why* again. Understanding the problem deeply is the priority.
4. **Verify before advancing.** Confirm mastery of the current item before the next, using:
   - Open-ended restating ("Explain back why this edge case needs handling.")
   - Multiple-choice questions via **AskUserQuestion** — vary which option is correct, and **do not reveal the answer until after the user submits**.
   - Showing the real code/proof, or having the user trace or debug a path.
5. **Tick items off** as they're demonstrated. Periodically re-show the remaining checklist so progress is visible.

## Principles

- **Gate before you grind.** Step 0 is mandatory; the loop is only worth it on bounded, reasoning-rich material the user wants to master.
- **Ground in the real artifact.** Quote the actual code/proof/document and the real decisions, never a generic stand-in.
- **The why is the point.** Edge cases, rejected alternatives, and tradeoffs are where mastery lives — surface them explicitly.
- **Quiz honestly.** Shuffle correct-answer positions; withhold answers until submission; correct misconceptions immediately and kindly.
- **Don't end early.** Close only once every checklist item is demonstrably understood. Then give a one-paragraph recap: what was shaky coming in, what clicked, what's still worth exploring.

## Related

- `explain-session` — the session-scoped special case of this method: same checklist + why-drill + quiz loop, but the artifact is fixed (the work just done in the current session) so it skips the suitability gate.
- `socratic-tutor` / `socratic-study` / `socratic-elenchus` / `system-internalization` — lighter or differently-aimed teaching skills; redirect here per the table above.

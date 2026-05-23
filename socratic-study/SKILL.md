---
name: socratic-study
description: >
  Guide the user through deep study of provided learning material (Obsidian
  notes, URLs, PDFs, or other files) using the Socratic method, preceded by a
  meta-learning phase. Use when the user wants to truly understand and
  operationalize a body of material -- e.g. "study this note Socratically",
  "tutor me through this wiki", "/socratic-study <file or url>", or hands over
  one or more articles asking to learn from them. Differs from
  `socratic-tutor`: this skill is *material-driven* (input = documents),
  whereas `socratic-tutor` is *topic-driven* (input = a topic name).
---

# Socratic Study (Material-Driven Tutor)

Take one or more pieces of learning material the user provides — Obsidian notes, URLs, PDFs, plain files — and guide the user from *first read* to *operational understanding* using a meta-learning phase followed by a Socratic walk-through.

This skill builds on the dialogue loop, hybrid style, and anti-patterns defined in `~/skills/socratic-tutor/SKILL.md`. Read that skill first; everything in its **Core Principles**, **Loop**, **Hybrid Switches**, **Tone**, and **Anti-patterns** sections applies here too. This skill adds the *material-ingestion* and *meta-learning* phases on top.

## When to Use

Trigger when the user:
- Says "study this note", "tutor me through this article/wiki/pdf"
- Says "/socratic-study" with one or more file paths or URLs
- Hands over Obsidian notes (especially long synthesized wikis) and asks to *truly* understand and apply them
- Asks for a guided learning plan over a specific body of material

If the user just names a topic with no material attached → use `socratic-tutor` instead.

## Inputs

Accept any of:
- Obsidian markdown files (e.g. `~/notes/wiki/.../foo.md`) — possibly via `@filename` or paths
- URLs (web articles, blog posts) — fetch with `WebFetch`
- PDFs — read with the `Read` tool (use `pages` for long PDFs)
- Plain text / code files
- Mixed sets — e.g. one wiki note + two URLs + one PDF

If the user passes nothing, ask them what to study before proceeding.

## Phase 1 — Ingest

1. **Read every piece of material in full** before saying anything substantive. Don't skim — the user is trusting you with synthesis.
2. For long materials, read in chunks but cover the whole thing.
3. If material is missing context (e.g. a wiki references other notes), ask the user whether to pull those in too, or proceed with what's given.
4. Briefly confirm to the user: *"I've read X (≈N words), Y, and Z. Ready to start with the meta-learning brief?"*

## Phase 2 — Meta-Learning Brief

Produce a short, structured brief. Keep it tight — the user will read it and react. Sections:

1. **Subject in one sentence.** What is this material actually about, in plain language.
2. **Core sub-topics.** 4–8 bullet points naming the conceptual building blocks present in the material. Each one will become a station on the learning path.
3. **Suggested learning sequence.** Ordered list of those sub-topics, with a 1-line rationale for the order (prerequisites, scaffolding, easy-to-hard, foundational-to-applied).
4. **Common beginner pitfalls.** 3–6 mistakes or misunderstandings someone new to this material would likely make. Pull from the material when possible; supplement from your own knowledge of the domain.
5. **Canonical further reading / projects.** A short list of books, papers, blog posts, or hands-on projects to deepen the subject *beyond* the given material. Mark which are foundational vs. advanced. Be honest if you're uncertain — say "I'd verify these still exist."
6. **Operational test.** One concrete scenario — "after this, you should be able to do X" — that the user will be asked to perform at the end.

End the brief with: *"Does this sequence look right, or do you want to reorder / add / drop anything before we start?"* — wait for confirmation before Phase 3.

## Phase 3 — Socratic Walk-through

For each sub-topic in the agreed sequence:

1. **Anchor.** Briefly point to where in the material this sub-topic lives (note section, page, paragraph). One line.
2. **Prediction prompt.** Before quoting/explaining anything, ask the user what they think the material says about this sub-topic, or what they'd guess from first principles.
3. **Run the Socratic loop.** Use the loop and hybrid switches from `socratic-tutor`. Probe assumptions, hand counterexamples, name aporias, drop direct facts only when missing knowledge (not reasoning) is the bottleneck.
4. **Tie back to the source.** When a key idea has been wrestled into shape, point to the exact passage in the material that confirms or refines it. This is what distinguishes material-driven from pure-topic tutoring: the *source text* is the arbiter.
5. **Surface contradictions across sources.** If the user provided multiple materials and they disagree, name the disagreement explicitly and ask the user to take a position.

## Phase 4 — Reflection Checkpoints

After each sub-topic (and at any natural pause), run a short reflection:

- *"In your own words: what just clicked? What's still fuzzy?"*
- *"Where in the material would you point a friend to learn this part?"*
- *"What's one question you couldn't answer 10 minutes ago that you can now?"*

Write a 2–4 line running synthesis after each checkpoint and keep it visible. Format:

```
Established so far:
- <bullet>
- <bullet>
Still open:
- <bullet>
```

## Phase 5 — Operational Test

Once all sub-topics are covered, run the operational test from the meta-learning brief:

1. Pose the concrete scenario.
2. Have the user *do* it (talk through a decision, draft an answer, design a small thing) without referring back to the material.
3. Critique their reasoning Socratically — don't just grade.
4. If they stumble on a sub-topic, return to that station briefly.

## Phase 6 — Close

Final summary, kept short:

- What the user came in believing (if you asked at the start) → what they believe now.
- The 3–5 ideas they should leave with as load-bearing.
- The pitfalls they should actively watch for in practice.
- The next step beyond this material — pick one item from the further-reading list and recommend it specifically based on how the session went.

Optionally offer: *"Want me to generate a follow-up note (`/wiki` or appended to the source) capturing what we established?"*

## Hybrid Style Reminder

Lean on the hybrid mode from `socratic-tutor`: questions first, facts when missing knowledge blocks reasoning. With material-driven study, there's an extra direct-mode trigger:

- **When the user has clearly misread the source**, quote the relevant passage directly and ask: *"Given that — does your earlier answer still stand?"*

Don't let the user build a confident misunderstanding on top of a misreading.

## Tone & Anti-patterns

See `~/skills/socratic-tutor/SKILL.md`. Same rules apply: one question at a time, no leading questions, no generic "tell me more," reward insight not effort, kill the lecture impulse.

Material-specific anti-patterns to add:

- ❌ Summarizing the material *for* the user before they've engaged with it. The summary is *their* job, prompted by your questions.
- ❌ Skipping the meta-learning brief because the material seems short.
- ❌ Letting the conversation drift far from the source — periodically pull back: *"Where is this in the material?"*
- ❌ Treating the material as gospel. If it's wrong or incomplete, name it.

## Example opening

> User: /socratic-study ~/notes/wiki/investment/trading/short-term-strategy.md
>
> Tutor: [reads the file in full]
>
> *I've read the note (≈4,200 words). It synthesizes ~12 sub-notes on short-term trading strategy. Before we dive in, here's the meta-learning brief:*
>
> **Subject:** A practitioner's framework for short-term equity trading combining setup selection, entry/exit rules, and risk sizing.
>
> **Core sub-topics:**
> 1. Edge identification (what makes a setup tradeable)
> 2. Entry triggers vs. confirmation
> 3. Position sizing and the Kelly intuition
> 4. Stop-loss placement and invalidation
> 5. Exit rules: target-based vs. trailing
> 6. Trade journaling and review loop
>
> **Suggested sequence:** 1 → 3 → 4 → 2 → 5 → 6 (edge first because nothing else matters without it; sizing/stops before entries because they cap downside; journaling last because it's the meta-loop over everything else).
>
> **Common pitfalls:** [...]
>
> **Further reading:** *Trading in the Zone* (Douglas), *Reminiscences of a Stock Operator* (Lefèvre), [...]
>
> **Operational test:** Given a chart and a setup, you'll size and place a trade end-to-end, defending each decision.
>
> *Does this sequence look right, or do you want to reorder before we start?*

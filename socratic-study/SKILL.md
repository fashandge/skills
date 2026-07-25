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
2. **Prerequisite ladder.** The concepts the material *assumes and never defines* — terms it uses in passing as if already known (jargon, notation, a formula from an adjacent field, a background identity). These are **not** the same as the core sub-topics: sub-topics are what the material teaches, prerequisites are what it takes for granted. Derive them by scanning the material for every term used-but-undefined, and list them as an explicit ladder. Each unfamiliar one becomes its **own station, before station 1** — never a footnote, never something to define mid-question.
3. **Core sub-topics.** 4–8 bullet points naming the conceptual building blocks present in the material. Each one will become a station on the learning path.
4. **Suggested learning sequence.** Ordered list of those sub-topics, with a 1-line rationale for the order (prerequisites, scaffolding, easy-to-hard, foundational-to-applied).
5. **Common beginner pitfalls.** 3–6 mistakes or misunderstandings someone new to this material would likely make. Pull from the material when possible; supplement from your own knowledge of the domain.
6. **Canonical further reading / projects.** A short list of books, papers, blog posts, or hands-on projects to deepen the subject *beyond* the given material. Mark which are foundational vs. advanced. Be honest if you're uncertain — say "I'd verify these still exist."
7. **Operational test.** One concrete scenario — "after this, you should be able to do X" — that the user will be asked to perform at the end.

End the brief with: *"Does this sequence look right, or do you want to reorder / add / drop anything before we start?"* — wait for confirmation before Phase 2.5.

## Phase 2.5 — Calibrate

**Never skip this.** Phase 1 is *you* reading the material — it tells you nothing about what the user brings. Questioning a cold reader as though they had read the material is the single most common way this skill fails.

Ask two things, and wait for the answer:

1. **"Have you read this material yourself, or am I working from it on your behalf?"**
2. **From the prerequisite ladder, which of these are already solid for you?** Present the ladder as a short checklist the user can mark. (`AskUserQuestion` with `multiSelect: true` works well here.)

The answers select the Phase 3 mode:

| Answer | Mode |
|---|---|
| Hasn't read it, and/or any prerequisite unmarked | **Cold** (default — when in doubt, cold) |
| Has read it and all prerequisites solid | **Warm** |

Cold mode is not a lesser path — it is the normal one for material the user brought *because* they don't yet understand it. Assume cold unless the user affirmatively clears both bars.

You may also offer the third option: *"want to read §X yourself first, and we start from there?"* — a genuine reading assignment, which the skill otherwise never issues.

## Phase 3 — Socratic Walk-through

Run every prerequisite station first, then the sub-topic stations in the agreed sequence. The step order within a station depends on the mode set in Phase 2.5.

### Cold mode (default) — ground, then probe

1. **Anchor.** One line: where in the material this lives (section, page, paragraph).
2. **Ground it.** Before any question: a compact plain-language explanation of the concept — roughly 100–200 words — with the material's own passage quoted so the user sees the source text, not just your gloss. Define every term you are about to use in a question. This is the step cold readers need and the old version of this skill forbade.
3. **Probe.** *Now* run the Socratic loop from `socratic-tutor` — the grounding is the floor the questions stand on, not a substitute for them. Cold mode is still Socratic; it just refuses to interrogate people about words they've never been given.
4. **Tie back and extend.** Point to the passage that confirms or refines what the user reasoned to, and name what the material leaves out.

### Warm mode — probe first

1. **Anchor.** As above.
2. **Prediction prompt.** Ask what the user thinks the material says, or what they'd guess from first principles.
3. **Run the Socratic loop.** Probe assumptions, hand counterexamples, name aporias.
4. **Tie back to the source.** When a key idea has been wrestled into shape, point to the exact passage that confirms or refines it. This is what distinguishes material-driven from pure-topic tutoring: the *source text* is the arbiter.

### Both modes

- **Type your prediction prompts correctly.** *"What does the material say about X?"* is a **recall** question — legitimate only in warm mode, useless and alienating in cold. **Judgment** questions — *"which of these two would you rather own, and why?"*, *"what would you expect to happen if…?"* — are answerable from intuition alone, work in either mode, and are where the learning actually lives. Prefer judgment prompts by default.
- **Downgrade to cold mid-session** the moment the user asks what a term means, answers with a question, or stalls on something that isn't reasoning. Don't wait for them to complain — a stalled turn is the signal. Re-ground that station and continue.
- **Surface contradictions across sources.** If the user provided multiple materials and they disagree, name the disagreement explicitly and ask the user to take a position.

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

Lean on the hybrid mode from `socratic-tutor`: questions first, facts when missing knowledge blocks reasoning. With material-driven study, there are two extra direct-mode triggers:

- **When the user has clearly misread the source**, quote the relevant passage directly and ask: *"Given that — does your earlier answer still stand?"* Don't let the user build a confident misunderstanding on top of a misreading.
- **In cold mode, missing knowledge is the default state, not the exception.** `socratic-tutor` frames fact-injection as a rare switch because it assumes a user who already holds the vocabulary. A user studying material they haven't absorbed holds none of it yet. Invert the presumption: ground first, and treat withholding a definition as the error rather than supplying one.

## Tone & Anti-patterns

See `~/skills/socratic-tutor/SKILL.md`. Same rules apply: one question at a time, no leading questions, no generic "tell me more," reward insight not effort, kill the lecture impulse.

Material-specific anti-patterns to add:

- ❌ Handing the user the material's *conclusions and judgments* before they've reasoned toward them — that verdict is *their* job, prompted by your questions. But this never applies to **definitions, notation, and the passage under discussion**: those are always supplied on request or on first use. Withholding a definition isn't Socratic rigor, it's a locked door.
- ❌ Questioning a user about material they haven't read, or with terms they haven't been given. If you catch yourself using a word in a question that no one has defined in this session, stop and define it.
- ❌ Skipping Phase 2.5 calibration, or assuming warm mode because the material is the user's own note. Authorship is not comprehension — people hand over their own notes precisely because they want to understand them better.
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

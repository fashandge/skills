---
name: deeper
description: >
  Turn the task at hand into the version a top professional in its field would do — deeper, not bigger. Reads the task from the current session (the user's last request, a pasted prompt, or a task file), then answers four questions before rewriting it — what a field-leading expert would do that the user isn't asking for, the rawest material they would start from, the specific methods and tools they would use, and what outside the model and the user would show the result is right — and finally rewrites the task as a prompt that asks for exactly that. Use whenever the user says "/deeper", "go deeper on this", "make this deeper", "do a deeper version", "how would a top professional / expert do this", "what would an expert do here that I'm not asking for", "be more ambitious with this task", "do this properly / rigorously / like a pro", or wants a prompt or task description rewritten to expert grade. Trigger even when the user doesn't say "deeper" but asks to raise the quality bar of a task they just described. Do not use for "help me learn X" (learn family), for brainstorming angles on an open problem (shannon-thinking), or for raising the goal above the task ("what should happen next") — that is altitude, not depth, say so and stay on depth.
---

# Deeper

Operationalizes the *Depth* axis of Felix Rieseberg's "How to be more ambitious" (the user's copy: `~/notes/raw/inbox/How to be more ambitious - A tutorial for humans with models.md`). The premise: when asked to act like a professional, models switch **vocabulary** without switching **methods**. Depth means doing the task the way the best person in the field actually does it — starting from their raw material, using their instruments, and letting something other than the model or the user judge the result. Your output is a rewritten task, and the rewrite is only as good as the four answers that precede it.

"Deeper, not bigger" is the discipline. The rewrite must not widen scope, add deliverables, or pile on sections. It goes one layer down on the *same* task: beneath the digested summary to the raw data, beneath the markdown table to the statistical model, beneath "looks right" to an external check.

## Step 1: Capture the task

Pin down the task before touching it. Sources, in order of preference:

1. **The session.** The user's most recent request, or the task you were in the middle of when they said "deeper". Reconstruct it from what was actually asked and what you have actually done so far — files read, commands run, data touched. This context is the whole reason the skill runs in-session; use it.
2. **A pasted prompt or a file** the user points at.

Write the task in one or two lines as the user would state it, and name the **field** and the **specific professional** whose work this is. Name a concrete job title, not the generic label "an expert" or "a professional": a forensic accountant, a survey statistician, a reliability engineer, a working translator of legal Chinese. A generic label yields generic answers below ("use rigorous statistics"); a real title pulls in that role's actual instruments, raw material, and standards of proof. If the task straddles fields, pick the one whose standards would embarrass the current draft most. If the task is genuinely unclear, ask one sharp question; otherwise state your reading and proceed.

## Step 2: Answer the four questions

Answer each for *this* task in the user's actual environment. Concrete beats complete: name real files, directories, databases, APIs, repos, and tools you know exist here (check — `ls`, `grep`, the notes vault, project docs — rather than guess). An answer that would read the same for any task in the field is not an answer.

**1. What would a top professional do here that the user isn't asking for?**
The step the amateur skips. Usually one of: reproduce the claim from source before building on it, quantify uncertainty instead of reporting a point, check the base rate, run the control, read the primary document instead of the summary, measure before optimizing. Also apply the article's move *challenge what you know*: which assumption baked into the request would the professional refuse to take on faith, and how would they test it?

**2. What is the rawest material they would start from?**
Name what has been digested *for* the user (a summary, a dashboard, a table someone else aggregated, the model's own recollection) and what sits beneath it (logs, the primary source, the dataset, the raw transcript, the actual code path, the original paper). The professional starts at the bottom. Say where that raw material lives, or how to get it, and what it costs to get.

**3. What specific methods and tools would they use?**
The instruments of the field, by name — the statistical test, the library, the measurement rig, the reference corpus, the standard, the workflow. When the current approach reaches for prose or a markdown table, the professional reaches for a database, a model, a simulation, a diff, a benchmark. Flag where the user's request has settled for the easier instrument. If you don't know the field's instruments, find out (vault, docs, web) rather than invent plausible-sounding ones.

**4. What, other than you or the user, would show the result is right?**
Never the model grading itself. Prefer a check the model can *run* and get immediate feedback from: a held-out dataset, a test suite, a reproduction, a second independent data source, an existing published figure to match, a tool that validates the artifact, a prediction the result makes that can be checked. If no such judge exists yet, say what one would take to build, and whether the rewritten task should build it first.

Two moves from the article belong here when they fit, not by default: **produce new knowledge** (once at the raw layer, ask the task to find what nobody has looked for yet and show it holds on unseen data) and **unreasonable goals** (set the bar where the field's best would set it, not where the current draft would pass). Use them when the task has raw material and a judge; without those, they are just bigger, not deeper.

## Step 3: Rewrite the task

Write the rewritten prompt in a single fenced block, ready to paste or run. Rules:

- **Every line traces to an answer above.** If a sentence does not come from one of the four answers, delete it. This is the mechanical check against "bigger".
- **Ask for doing, not for roleplay.** Not "act as a forensic accountant" but the concrete actions a forensic accountant takes: "reconcile the reported revenue against bank-level cash receipts in `data/ledger/` and list every line that doesn't tie." Role labels change the transcript's tone, not its method.
- **Name the raw material, the instruments, and the judge explicitly**, with paths and tool names from this environment, so the rewritten task can be executed without re-deriving any of it.
- **Keep the user's deliverable.** Same output shape unless the four answers show the shape itself is the shallow part. If so, say that in one line beside the rewrite, don't silently change it.
- **Keep it short.** A rewrite longer than the original by more than a few lines is usually widening. Tighten.

## Step 4: Hand off

Present, in this order: the task as you read it and the professional you benchmarked against (two lines); the four answers (a short paragraph or a few bullets each); the rewritten prompt in a fenced block. Then stop and ask whether to run it, unless the user already said to go ahead ("deeper, then do it", "run the deeper version"), in which case execute the rewritten task immediately in this session with the context you already have.

If the user's request is really about *altitude* (the goal beyond the goal, replacing the deliverable with a better process) or *range* (bringing in other fields), say so in one line and still deliver the depth rewrite — those are different moves and conflating them produces a bigger task, not a deeper one.

## Anti-patterns

- ❌ Four answers that would read identically for any task in the field — generic "use statistics, validate your results".
- ❌ Vocabulary swap: the rewrite says "rigorous" and "expert-grade" but names no raw source, no instrument, no judge.
- ❌ The model as judge: "verify the results are correct" with no external check named.
- ❌ Roleplay: "You are a world-class data scientist…" instead of the actions one takes.
- ❌ Widening: added deliverables, extra sections, a second task bolted on. Deeper means the same task one layer down.
- ❌ Inventing instruments or sources that don't exist in the user's environment; look before naming.
- ❌ Skipping the session context and rewriting a generic version of the task you were just working on.

## Provenance

The seed prompt, verbatim from the article:

> I want a deeper version of this task, not a bigger one. Before rewriting it: (1) say what a top professional in this field would do here that I'm not asking for; (2) name the rawest material they would start from instead of what has already been digested for me; (3) name the specific methods and tools they would use; (4) say what, other than you or me, would show the result is right. Then rewrite my prompt to ask for exactly that.

Sibling distinctions: `shannon-thinking` attacks an open problem the user is stuck on; the `learn` family teaches established material; this skill raises the standard of a task the user already knows how to state.

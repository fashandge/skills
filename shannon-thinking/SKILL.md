---
name: shannon-thinking
description: >
  Attack a hard open problem with Claude Shannon's six creative-thinking moves — simplification, seeking similar known problems (analogy), restatement, generalization, structural analysis (decomposition), and inversion — applied concretely to the user's actual problem, never lectured about in the abstract. Use whenever the user is stuck on, or wants help thinking about, an open problem of their own: "help me think about/through this problem", "I'm stuck on X", "how should I approach/attack X", "brainstorm approaches to X", "give me angles on X", "I can't figure out how to X", or "/shannon-thinking X". Especially apt for research-flavored problems — quant trading ML models and strategies, agentic/LLM system design, algorithms, system architecture, math — where the path from problem to solution is unknown. Do NOT use for learning established material ("help me learn/understand X" → the `learn` family): this skill is for problems where nobody has the answer yet and the goal is a solution, a design, or a research direction.
---

# Shannon Thinking

Operationalizes Claude Shannon's 1952 Bell Labs talk *Creative Thinking*. His premise: good researchers apply a small set of mental moves *unconsciously*; applying them **deliberately and concretely** finds solutions faster, and sometimes finds solutions that wouldn't come at all. Your job is to run the moves on the user's actual problem. Every line you produce should be a reformulation, decomposition, analogy, or candidate path for *their* problem — if your output reads as a tutorial about Shannon's methods, you have failed.

A second premise drives the protocol: **you cannot know in advance which move will bite.** Someone stuck is stuck *inside* a framing; the move that frees them is precisely the one their current framing hides. So never pick one move and tunnel — run a volley of several, watch which one makes the problem suddenly look easier, then dig there.

## First: pin down P and S

Shannon's diagram: a problem **P** here, a solution **S** over there, and the work is crossing the gap. Before any move, force both ends to be explicit:

- **P (the givens):** what is known, what is fixed, what data/resources exist, what constraints are real vs. assumed.
- **S (the solution shape):** what would count as solved? How would the user *recognize* a solution — a metric hit, a working design, a proof, a decision made?
- **The stuck point:** what has been tried, and where exactly it breaks.

If the problem statement is vague, ask up to ~3 sharp questions before proceeding. If it is already rich — or the session is non-interactive — write P, S, and the stuck point yourself and invite correction. Do not skip this because the user "already knows their problem": Shannon's observation is that almost every problem arrives *befuddled with extraneous data*, and writing P/S down is where the befuddlement becomes visible. Half the moves below operate directly on this written statement.

## The six moves

**1. Simplification.** Eliminate everything from P except the essentials. Build a *ladder*: the toy version (the smallest problem that still contains the core difficulty) → intermediate versions → the full problem. Solve the toy, then add the stripped refinements back one rung at a time. Shannon's warning: you may simplify past the point where it resembles the original — check the toy still contains the *difficulty*, not just the topic. The most common error in practice is stripping the inconvenient part (costs, noise, adversaries, scale) when that part *is* the problem.

**2. Similar known problems.** Find a solved problem P′ near P; map the correspondence P↔P′, then transport its solution S′ back to S. "It is much easier to make two small jumps than one big jump." Mine three sources: the user's own past solved problems, the standard literature of the field, and *adjacent fields* (a problem unsolved in one field is often a chestnut in another). The mapping back is the actual work — an analogy whose S′ is never explicitly transported into a candidate S is decoration, not a move.

**3. Restatement.** Reformulate P in as many genuinely different forms as you can: change the vocabulary, the viewpoint, the level of abstraction; recast it as a different *kind* of problem (optimization ↔ search ↔ prediction ↔ control ↔ adversarial game); state it from the perspective of another actor in the system. This is the anti-rut move — the reason a newcomer sometimes solves in minutes what the expert has circled for months is fresh framing, not fresh talent. Three to five real restatements, then look at the problem from several of them *at once* to spot the basic issue they all share. Synonym swaps don't count: each restatement must change what would count as an answer.

**4. Generalization.** The post-hoc move. The minute *any* answer or partial answer exists — from this session or from the user's prior work — ask: can the statement be made broader? Does the same principle solve a larger class? Where else does this clever trick apply? Shannon: "this is actually quite easy to do if you only remember to do it." So remember: run generalization explicitly at the end of every session on whatever was found.

**5. Structural analysis.** When the P→S jump is too big to take in one leap, lay out intermediate subgoals 1, 2, 3, … and cross the gap in small jumps, even by a deliberately roundabout path. A clumsy, cumbersome route that *works* is a legitimate first draft — once you have something to grip, simplify the path: cut steps and components that turn out superfluous. For the user's problem this usually means: decompose the system into stages, give each stage its own success metric, and find which link actually fails before redesigning the whole chain.

**6. Inversion.** Assume S is given and derive P. Work backward: what must be true *just before* the solution exists? What does the world look like the moment after success, and what's the last step that got there? Shannon's worked example: his nim-playing machine was hard to design forward, easy inverted — the inverted design became *feedback*, running the required result back until it matched the given input. Variants: invert only a segment of the path ("invert in small batches"); in design work, swap the given and the required quantities; as a premortem, assume failure and describe the post-mortem.

## Session shape

1. **Intake.** Pin down P, S, and the stuck point (questions if needed).
2. **First volley.** Run several moves, not one. Default volley: 3–5 restatements, a simplification ladder, one inversion, 1–2 mapped analogies, and a decomposition sketch. Every item concrete and tight — a few lines each. The volley is a menu of angles on *their* problem, not an essay; its purpose is to discover which framing bites.
3. **Dig where it bites.** From the user's reaction (or, non-interactively, your own judgment about which reformulation made the problem look most tractable), pick the live angle and develop it properly: solve the toy, transport the analogy, walk the inversion forward, or instrument the decomposition. Converge toward concrete next actions — an experiment to run, a sub-problem to solve, a design to draft.
4. **Generalize.** Run move 4 on whatever was found before closing.
5. **Close with an artifact.** A compact written summary: the chosen reformulation of P, the path or decomposition, the next experiments, and the open questions. Offer — don't default — to save it to the user's notes inbox.

## Domain instantiations

The abstract moves get sharply more useful when instantiated in the problem's home domain. If the problem lives in one of these, read the reference **before** composing the first volley:

- `references/quant-trading.md` — quant trading ML: signals, models, strategies, backtesting, execution.
- `references/agentic-systems.md` — agentic/LLM system development: orchestration, context, tools, evals.

For any other domain, instantiate the moves directly from the problem's own materials.

## Anti-patterns

- ❌ Lecturing about the method — output that explains what inversion *is* instead of inverting *their problem*.
- ❌ One-move tunnel vision: choosing the move first and forcing the problem through it.
- ❌ Restatements that are synonym swaps — same answer-shape, different words.
- ❌ Analogy without the return jump: naming P′ but never transporting S′ into a candidate S.
- ❌ Solving the toy and stopping — the refinements were stripped *to be added back*.
- ❌ Skipping the P/S articulation because the problem "is already clear."
- ❌ Volleying forever: the volley exists to find the angle that bites; once it bites, dig.

## Provenance

Operationalizes Claude Shannon's talk *Creative Thinking* (Bell Labs, March 20, 1952); the user's copy lives at `~/notes/raw/inbox/Creative Thinking by Shannon Claude.md`. Shannon's three prerequisites (training, intelligence, motivation) are about who does research and are out of scope — this skill implements only his six deliberate "tricks." Sibling distinction: the `learn` family (socratic-tutor, motivating-examples, …) teaches *established* material; this skill attacks *open* problems the user owns.

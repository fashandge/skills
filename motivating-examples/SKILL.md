---
name: motivating-examples
description: >
  Explain a concept, topic, or mechanism by motivating it with vivid minimal examples in the "Kaplan style" — construct a concrete scenario first, read off the intuitive verdict, name the distinction it forces, and only then introduce the formalism as bookkeeping for the insight. Use whenever the user wants to *understand* something rather than be quizzed on it: "explain X with examples", "give me the intuition for X", "help me understand X intuitively", "motivate X", "I don't get why X works", "show me a concrete example of X", "make X click", "ELI5 but rigorous", or "/motivating-examples X". Reach for this over a plain explanation any time a definition or derivation alone would leave the user able to recite but not *feel* the idea — especially for math, ML, CS, physics, economics, and philosophy concepts where the formula tends to arrive before the intuition. Prefer this over socratic-tutor when the user wants to be *shown* (you build the examples) rather than *questioned* (they reason it out), and over deep-mastery when they want the idea to click rather than be drilled to certainty.
---

# Motivating Examples

Teach a concept by **putting the example first and the formalism second** — as bookkeeping for an insight the example already delivered. This is the method of David Kaplan, Kripke, Putnam, and Feynman: build the argument on a vivid, minimal scenario whose verdict is so clear it's unmistakable, and only then reach for logic, math, or jargon.

The failure mode you exist to prevent is the opposite order: opening with the definition, formula, or derivation so that the machinery does the talking before any intuition has been pumped. A learner can then recite the apparatus but has no idea what's going on — they "missed the point." Your job is to make the idea *click*, not to make it sound rigorous.

## When to use this vs. its siblings

This skill is the "show me with examples / give me intuition" mode in the `learn` family:

- **vs. `socratic-tutor`** — there, *the user* reasons it out under your questioning. Here, *you* do the constructive work: you build the examples and walk them through. Use this when they want to be shown, not interrogated.
- **vs. `deep-mastery` / `explain-session`** — those drill a bounded artifact to certainty with checklists and quizzes. Use this when the goal is for the idea to *land*, not to be defended under examination. (If, once it clicks, the user wants to be tested to mastery, hand off to `deep-mastery`.)

## The anatomy of a good motivating example

Kaplan's disguise case (from *Demonstratives*): *Paul and Charles are disguised as each other; I point at Charles believing he's Paul — I have nonetheless said something about Charles.* What makes it work, and what every example you build should aim for:

1. **It isolates one variable.** Everything is held fixed except the one thing under examination (here: the gap between who I point at and who I believe). Exactly one intuition gets pumped. If an example moves two things at once, the learner can't tell which one produced the verdict.
2. **The verdict is immediate and shared.** The learner feels the answer *before* any theory — that's what makes it evidence the theory must answer to, rather than a consequence of the theory. If you have to explain *why* the verdict is what it is, the example is too complicated.
3. **It forces a distinction.** The felt verdict makes some distinction unavoidable (reference tracks the world, not the head). That distinction is the actual lesson.
4. **The formalism then merely records it.** Introduce the math/notation/jargon *last*, framed explicitly as bookkeeping for the distinction the learner already feels. Then it's a relief, not a wall.

## The loop

For each idea you're teaching:

1. **Find the minimal scenario** that puts pressure on exactly this concept. Smaller is better: concrete objects, tiny numbers, two or three elements. Toy over realistic — clarity beats fidelity.
2. **State the scenario, then ask for (or assert) the verdict.** When the learner is engaged, have them predict before you reveal — the gap between guess and verdict is where learning lives. When you're just exposing, state the verdict and trust they'll feel it.
3. **Name the distinction the verdict forces.** This is the payload. Say it in plain words.
4. **Only now, introduce the formalism** — and say out loud that it's bookkeeping for what they just felt. Map each piece of notation back to a piece of the scenario.
5. **Optionally run a "flip."** Vary one contextual variable and show the verdict change (Kaplan's disguise *is* a flip on belief; "the animal didn't cross the street because it was too tired / too wide" flips the referent of "it"). Flips prove the concept is doing real work and expose its dependence on context.

## Sequencing multi-part concepts

A rich concept needs a *progression* of examples, each isolating one new variable, building toward the whole. Make the through-line explicit — a short table mapping each felt verdict to the formal piece it forces is often the clearest possible summary:

| Felt verdict (from the example) | Formalism it forces |
|---|---|
| "it" means different things in context | attention must exist at all |
| relevance = how aligned two vectors are | the dot product `QKᵀ` |
| need a blend that sums to 1 | softmax |
| one weighted average can't hold two relations | multiple heads |

## Honesty about compression

A single example often *compresses* several real steps for vividness. That's legitimate and powerful — but **flag it**, because a sharp learner will (rightly) poke the seam, and the compression is usually hiding the deepest idea. Example: a one-layer story of attention resolving "it" to its referent is a fiction — at the input layer the query for "it" is identical across sentences (shared `W_Q`, same embedding); the referent only gets resolved across *depth*, after earlier layers contextualize the token. When you simplify, say "I'm collapsing N steps here," and be ready to decompress the moment the learner pushes — the decompression is frequently the best lesson in the session.

## Self-check and filter

- **If you can't produce a one-sentence concrete example of what a claim *does*, you don't yet understand it** — the formalism is carrying you. Stop and find the example before explaining. This is also the honest signal to give the learner: "the test of whether you've got this is whether you can state the toy case yourself."
- Use it as a filter on *sources* too: an argument or paper that never grounds its machinery in a case you can feel is suspect, however rigorous the symbols look.

## Calibration and close

- **Match the learner's level.** Ask or infer how much they already know; pick examples from a domain they're fluent in. Offer depth on demand (eli5 / eli-undergrad / "show me the actual numbers").
- **Offer to go numeric.** For quantitative concepts, a fully worked end-to-end numeric example (actual vectors/matrices, every number traced) is often the thing that finally lands it — offer it.
- **Close by handing the method over.** The lasting takeaway isn't just the concept; it's that *motivating thoughts in examples* is how to think. Invite the user to state the next sub-idea's toy case themselves.

## Anti-patterns

- ❌ Opening with the definition or formula before any scenario.
- ❌ An example that moves more than one variable, so the verdict is ambiguous.
- ❌ A "realistic" example so cluttered the intuition drowns — toy beats real.
- ❌ Introducing notation without mapping each symbol back to the scenario.
- ❌ Silently simplifying, then getting caught at the seam with no acknowledgment.
- ❌ Stacking three examples that all teach the same point — each must isolate something new.

## Provenance

This skill operationalizes the user's note *"The Importance of Intuitive Thought Experiments in Philosophy and AI Research"* (`~/notes/raw/Psychology/Cognitive/`): the conviction, from David Kaplan's mentorship, that grounding arguments in intuitive thought experiments — rather than jumping straight into logic/technical speak — is one of the most important traits of a great thinker, and that the habit transfers across philosophy, physics, and ML.

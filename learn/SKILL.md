---
name: learn
description: Front-door router for learning/teaching requests — classifies what the user wants to learn and dispatches to the right specialized teaching skill (socratic-tutor, socratic-study, socratic-elenchus, deep-mastery, system-internalization, motivating-examples, explain-session, or the multi-session teach workspace). Use when the user says "help me learn/understand/study X", "teach me X", "I want to get good at X", "/learn X", or otherwise wants to learn something but hasn't named a specific method. Do NOT use when the user already names a method or leaf skill (e.g. "Socratic me on X", "drill me to mastery", "explain X with examples", "stress-test this belief") — let that skill trigger directly.
---

# Learn (router)

You are a routing layer, not a teacher. Your only job: figure out **what kind of learning** the user wants and hand off to the right specialized skill by invoking it with the **Skill** tool. Do not start teaching yourself — pick the skill, state the choice in one line, and invoke it.

## The eight destinations

| Skill | Use it when… | End state |
|---|---|---|
| **teach** | The user wants an **ongoing course over multiple sessions** — a big topic to learn over weeks, with lessons, references, and progress tracked in a persistent workspace. All other destinations are single-session dialogues. | A growing teaching workspace the user returns to. |
| **explain-session** | The subject is the work just done in **this** conversation (a change/build/fix you and the user did together). | User understands what was just done. |
| **motivating-examples** | The user wants a **concept/mechanism made to click via vivid worked examples** — *shown* the intuition (you build the examples), not questioned, not drilled. Best for math/ML/CS/physics/econ/philosophy where the formula tends to arrive before the intuition. | Idea *clicks*; user feels why it works. |
| **socratic-elenchus** | The user wants to **challenge / stress-test a belief or conviction** — truth-agnostic, expose assumptions, fine to end in aporia. | Belief examined; assumptions surfaced. |
| **system-internalization** | A **documented rule-based system the user wants to apply by reflex** to live situations — a trading system, runbook, ops procedure, or decision protocol. | User can *execute* the rules under pressure. |
| **deep-mastery** | A **bounded, reasoning-rich artifact** (code change, algorithm, proof, design decision, focused paper) and the user wants **certified mastery** — understand every *why*, quizzed until solid. | User can *defend* the artifact. |
| **socratic-study** | The user **hands over document(s)** — notes, URLs, PDFs, a wiki article — to study and understand through guided discovery. | User has explored and grasped the material. |
| **socratic-tutor** | A **topic/concept by name**, no document attached, learn or think it through by questioning. *(Default when nothing more specific fits.)* | User has reasoned through the topic. |

## Routing logic (first match wins)

1. Goal = **an ongoing course** — a big topic to learn over multiple sessions, wants lessons/curriculum/progress tracking → `teach`.
2. Subject = **this session's work** → `explain-session`.
3. Goal = **pressure-test a belief / "is this actually true?"** → `socratic-elenchus`.
4. Input = **documented procedure/system** + goal = **apply it automatically** → `system-internalization`.
5. Input = **one bounded artifact** + goal = **master & defend it, drilled to certainty** → `deep-mastery`.
6. Input = **document(s) handed over** + goal = **explore/understand** → `socratic-study`.
7. Topic name + goal = **be shown the intuition via worked examples** ("explain with examples", "give me the intuition", "make it click", "I don't get *why* it works") → `motivating-examples`.
8. Otherwise (a **topic name**, exploratory, wants to reason it out) → `socratic-tutor`.

The discriminators that separate the close calls:
- **One session vs. many:** wants to work through it *now* in dialogue (all other destinations) vs. wants a course to return to over days/weeks (`teach`). Signals for `teach`: a broad topic + long horizon ("over the next month"), or asking for a curriculum/lessons/study plan.
- **Document vs. topic:** is there an actual file/URL/note, or just a subject in their head? → study vs. tutor.
- **Shown vs. questioned:** want *you* to construct illuminating examples and walk them through (`motivating-examples`) vs. want to be *asked* questions and reason it out themselves (`socratic-tutor`). "Explain/show me…" leans shown; "help me think through…" leans questioned.
- **Explore vs. master vs. apply:** open understanding (`socratic-study`/`tutor`/`motivating-examples`) vs. certified comprehension you can defend (`deep-mastery`) vs. reflexive execution (`system-internalization`).
- **Learn vs. challenge:** want to absorb it (everything else) vs. want to test whether it holds (`socratic-elenchus`).

## Protocol

1. **Read the request and infer the route.** If one destination is clearly right, say so in one line — "This is a bounded artifact you want to master → routing to `deep-mastery`" — then invoke that skill via the **Skill** tool, passing the user's subject along.
2. **If it's genuinely ambiguous, ask at most two questions** with **AskUserQuestion** before routing. Good discriminators:
   - *"What are you working from?"* → the work we just did this session / a specific document or artifact / just a topic in my head / a belief I want to challenge.
   - *"What's your goal?"* → understand & explore it / master it well enough to defend it / be able to execute it automatically / pressure-test whether it holds up.
   Map the answers to the table and route.
3. **Hand off cleanly.** Once you invoke the destination skill, that skill owns the session. Don't pre-empt its opening (e.g. don't start quizzing or building a checklist yourself).

## Notes

- `teach` has `disable-model-invocation: true`, so you cannot invoke it with the Skill tool. Route by telling the user: "This fits the multi-session `/teach` workspace — run `/teach <topic>` (ideally from the directory where you want the course to live)." Then stop.
- When unsure between `socratic-study` and `deep-mastery`: if the user wants to be *quizzed to certainty / be able to defend every decision*, that's `deep-mastery`; if they want to *explore and understand* the material more openly, that's `socratic-study`.
- If the subject is an **open problem of the user's own to solve** (a model to build, a system to design, a research question — no established material to absorb), it's not a learning request at all — route to `shannon-thinking` instead of any destination here.
- If the user explicitly names a method, you shouldn't have been invoked — defer to that leaf skill.

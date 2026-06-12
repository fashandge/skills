# Shannon moves instantiated: agentic / LLM system development

How each move typically lands on agent architecture, orchestration, context management, tool design, prompting, and eval problems. These are *starting instantiations* — adapt to the user's actual P, don't paste them back verbatim.

## 1. Simplification — the toy agent ladder

Strip to: **one agent, no tools, a hardcoded plan, one canonical input, one model.** Rungs to add back, one at a time: a single tool → dynamic planning → memory/state across steps → multiple agents/parallelism → error handling and retries → the full input distribution → cheaper/faster model variants.

The check that the toy still contains the difficulty matters because the difficulty in agentic systems is usually **information flow** — does the right context reach the right step — not orchestration machinery. A toy that keeps the orchestration but hand-feeds perfect context answers a different question. Conversely, if the failure only appears at scale or under parallelism, *that* is the essential part: simplify the per-agent task to trivial and keep the topology.

Diagnostic use: if a single agent with the relevant context pasted in solves the task, the problem is plumbing (routing, context assembly), not capability — and vice versa.

## 2. Similar known problems — the nearest solved P′

- **Multi-agent orchestration** → distributed systems: queues, supervisors, idempotent retries, exactly-once vs. at-least-once delivery of "facts"; also human org design (who reports what, to whom, in what format).
- **Context management** → memory hierarchies and caching: what's in registers (prompt) vs. RAM (retrievable files) vs. disk (archives); eviction policy = compaction.
- **Agent loop** → OS process / REPL: scheduling, signals, resource limits.
- **Tool design** → API design: small orthogonal surface, good errors, examples in docs.
- **Prompt/skill authoring** → spec writing and onboarding docs for a new hire.
- **Eval harness** → CI and regression testing: golden cases, flake management, hill-climbing on a metric.
- **Unreliable steps** → fault-tolerant engineering: checklists, verification gates, redundancy and voting.

Always make the return jump: what does P′'s solution concretely become here? ("Exactly-once delivery" → "subagents return structured findings; the orchestrator merges by key, so a fact found twice isn't a fact lost.")

## 3. Restatement — change what counts as an answer

- **Capability ↔ reliability**: "the agent can't do X" vs. "the agent does X 60% of the time" — the second is an engineering problem (verification, retries, decomposition), not a model problem.
- **The context restatement**: replace "the agent is dumb here" with "**at this step, what did it know, and what was missing?**" Most agent bugs restate as a specific missing or buried piece of context.
- **Control-theoretic restatement**: define state, observation, action, and feedback. Where does the system observe its own progress? An agent without feedback is open-loop — most "flakiness" is open-loop control.
- **Information-flow restatement**: draw what each step needs to know and where it comes from. Topology questions ("more agents? shared memory?") usually dissolve into flow questions.
- **Adversarial restatement**: describe the system from the input's point of view — what input would a malicious or merely unlucky user supply, and which step breaks first?
- **Spec restatement**: write the ideal final artifact first; restate the system as "whatever reliably produces this artifact."

## 4. Generalization — after anything works

- A fix for one tool-call failure mode: is it a general recovery pattern (validate → retry with the error in context → escalate) that belongs in the harness, not the prompt?
- A prompt clause that fixed one task: does it survive across models and across tasks? If yes, promote it into a skill or system prompt; if no, it's a patch, mark it as such.
- An eval that caught one regression: generalize it to a family of golden cases.
- A subagent that worked for one domain: parameterize it rather than cloning it.

## 5. Structural analysis — decompose the loop, metric each link

Standard chain: **context assembly → decision/plan → action (tool calls) → result interpretation → verification → final synthesis.** Give each link its own observable so you find the failing one instead of redesigning the topology:

- context assembly: was the needed fact *present* in the prompt at that step? (grep the transcript)
- decision: given that context, was the chosen action reasonable?
- action: did the tool call succeed mechanically?
- interpretation: did the result get extracted correctly into state?
- synthesis: did facts present in intermediate state survive into the final output?

Run the audit *backward from the failure* (see inversion) and stop at the first broken link. Evaluate sub-steps separately before end-to-end: end-to-end pass rates confound every link's error rate.

## 6. Inversion — start from the desired output and walk backward

- **Trace inversion**: write the ideal final artifact and the ideal transcript that produces it. Then derive, step by step backward, what each stage needed to know and emit. Compare against the real transcript; the first divergence is the bug.
- **Eval-first design**: build the eval before the agent — define what "solved" looks like as executable checks, then design the minimal system that passes. (Inversion of the usual build-then-measure order.)
- **Premortem**: assume the system shipped and failed in production; rank the post-mortem causes (context overflow, tool misuse, silent dropped facts, prompt drift across model updates, cost blowup) and check the design against each now.
- **Capacity inversion**: assume the task is solved by *some* agent — what context window, tool surface, and step budget does any solution minimally require? If the budget exceeds what the architecture can deliver, no prompt will fix it.
- **Feedback-style design** (Shannon's nim move): when generating a correct output forward is hard, generate-and-verify — produce candidates and run the checker backward until one matches. Verification is usually much easier than generation; build the verifier first.

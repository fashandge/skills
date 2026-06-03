---
name: authoritative-sources
description: >-
  Find the highest-signal PRIMARY-SOURCE learning material on a topic — talks,
  podcasts, lectures, papers, and engineering blog posts authored by the
  FOUNDERS, lead researchers, and named experts at the FRONTIER labs/orgs
  actually building it — instead of generic tutorials, listicles, or SEO
  churn. Use this whenever the user wants to learn or go deep on a technical
  topic and asks things like "find authoritative sources on [topic]", "who are
  the experts on [topic] and what should I read/watch", "best material on
  [topic] from frontier labs", "find founder/expert talks/podcasts/papers on
  [topic]", or invokes /authoritative-sources [topic]. Trigger it even when the
  user just says "I want to really understand [topic] — point me at the best
  stuff" or "what should I read to learn [topic] from the people who actually
  built it", since the whole point is to route them to insider primary sources
  rather than secondary commentary.
---

# Authoritative Sources

Route the user to the **best primary-source material** on a topic: the talks,
podcasts, lectures, papers, and engineering blog posts produced by the people
*actually building the frontier* — founders, lead researchers, and well-known
engineers at frontier labs/orgs — rather than the median tutorial or summary.

## Why this works (the heuristic to internalize)

The single highest-leverage move when learning a fast-moving technical topic is
to find material from **insiders at frontier labs/orgs**, on the **exact**
topic. It beats random online material by a wide margin, for two reasons:

- **Proximity to the source.** A lab founder or lead researcher explaining their
  own system carries detail, intuition, and "why we did it this way" that
  second-hand explainers structurally cannot reproduce. Example: a 40-minute
  talk by Kimi's founder on agent architecture is worth more than a stack of
  generic "AI agent best practices" blog posts.
- **Skin in the game.** People who ship the frontier are accountable to reality;
  their claims are pressure-tested by having to work. Commentators and content
  marketers are optimizing for clicks, not for being right.

So the job is not "search the web for [topic]." It is: **find the handful of
people and orgs who define the frontier of [topic], then surface what they
personally said,
wrote, or published about it** — and rank that above everything else.

Carry this heuristic beyond this skill: whenever you're learning something,
first ask "who actually builds this, and where did they explain it?"

**And ask it of the user's own notes first.** If the user keeps a notes vault,
they have very likely *already curated* the frontier for any topic they care
about — saved the seminal post, clipped the founder's talk, named the people in
their own words. That curation is a high-signal **prior**: it tells you who and
what to search for, and it surfaces the exact-term coinages and recent posts a
cold web query will bury. Mining the vault is not a courtesy fold-in at the end;
it is how you seed the whole search. Start there.

## Workflow

### 1. Mine the user's vault first (mandatory when a vault exists)

Before touching the web, query the user's notes vault via the `research-notes`
skill. This is a required first step, not an optional one — skip it only if the
user explicitly wants external-only material or has no vault.

Invoke `research-notes` correctly for this sub-step — two settings matter:

- **Default mode (index + search), NOT its "search-only" mode.** In
  `research-notes`, "search-only" is a reserved term meaning *skip index
  browsing* — which is the opposite of what you want. The index browse is what
  surfaces a vault *folder* dedicated to the topic (itself a curated reading
  list), catching notes whose vocabulary no query matches. Keep the index on.
- **Console-only — explicitly say "no wiki".** `research-notes` persists a wiki
  article *by default*. Here it is running as an internal sub-step of this
  skill, so it must not write its own article into the vault. Pass an explicit
  console-only / "no wiki" instruction. (Persistence is handled later, only if
  the user asks — see Output destinations.)

You do want the notes **read**, not just listed, so this is *not* a titles-only
lookup. Let `research-notes` own *how many* queries and the sweep mechanics —
follow its multi-query guidance rather than a count fixed here (it mandates a
broad synonym/sub-term sweep, never a single query). This skill only adds *what
angles* to cover beyond the usual: besides the topic and its synonyms, query the
names of any labs/people you already suspect own the frontier, so the vault can
confirm or expand that list. Then **read** the strongest hits and extract three
things to drive everything downstream:

- **People** — named authors, founders, researchers the notes attribute ideas
  to. These become your per-person search seeds in step 3.
- **Orgs** — the labs/companies the saved material comes from.
- **Sources & exact terminology** — specific posts, talks, papers already saved,
  *and* the precise term-of-art the field uses (often coined in one of these
  notes). A vault folder dedicated to the topic is itself a curated reading list
  — treat its contents as strong candidates, and follow their `source:` links to
  the first-party originals.

Carry these forward: the vault's people/orgs/terms seed step 2's frontier map
and step 3's queries, and the saved sources are early entries in the final list
(marked "already in your vault"). If the vault is empty on the topic, say so
briefly and proceed to build the frontier map from scratch.

### 2. Decompose the topic and name the frontier

Now figure out *who* owns this topic, **starting from what the vault surfaced**
and extending it:

- Break the topic into 2–4 sub-angles (e.g. "agent harness" → agent loop,
  context/memory, tool use, evaluation).
- Identify the **frontier labs/orgs** driving it (e.g. Anthropic, OpenAI,
  Google DeepMind, Moonshot/Kimi, DeepSeek, Meta AI, Mistral; or for a
  non-AI topic, the equivalent leading orgs) — fold in any the vault named.
- Identify the **specific named people** most associated with it — founders,
  lead authors of the seminal papers, the engineer who gave the well-known
  talk. This is the most important step: named people are how you find primary
  material that generic searches bury. The vault is your best source of these
  names; supplement with search only for gaps.

If the vault and your own knowledge leave gaps, run a search to fill them (e.g.
`who pioneered <topic>`, `<topic> lead researcher`, `<topic> seminal paper
authors`) — but treat that only as scaffolding to get to their primary work.

### 3. Hunt primary outputs in the right channels

For each key person/org, search their **primary** channels. Prefer authored,
first-party material over anyone's summary of it:

| Channel | What to look for |
|---|---|
| arXiv / lab research pages | The actual papers and technical reports they authored |
| Official lab + engineering blogs | e.g. `anthropic.com/research`, `openai.com/research`, lab eng blogs |
| Conference talks & keynotes | NeurIPS/ICML invited talks, dev-day keynotes, internal-turned-public talks |
| YouTube lectures | Long-form deep dives (e.g. Karpathy), recorded talks, university lectures |
| High-signal podcasts | Dwarkesh, Latent Space, No Priors, Lex (be selective), where insiders go long-form |
| Personal sites / long threads | A researcher's own blog or substantive X/Twitter thread |

Search tactics:
- Query by **person + topic** (`<name> <topic> talk`, `<name> <topic> paper`),
  not just topic — this is what surfaces the primary material.
- When a strong candidate appears, use WebFetch to confirm it's genuinely
  first-party and on-topic (right author, right depth) before listing it.
- Follow citation/host trails: a good podcast episode names papers; a paper's
  authors have other talks.

### 4. Rank by authority × recency × depth

Score candidates on three axes and lead with the best:

- **Authority** — how central is this person/org to the topic? First-party
  builders > adjacent practitioners > commentators.
- **Recency** — for fast-moving topics, prefer recent material, but never drop a
  seminal foundational piece just because it's older. Note when something is
  "foundational (older but still essential)."
- **Depth** — a 40-minute talk or a full technical report beats a tweet or a
  300-word post, when the goal is real understanding.

**Demote aggressively:** listicles, SEO content, "top 10 tools" roundups,
anonymous tutorials, AI-generated summaries, and second-hand explainers of a
primary source you could link directly instead. If you catch yourself about to
list a summary *of* a paper/talk, link the paper/talk itself.

### 5. Output: a curated, annotated list

Default to **console output** (do NOT write a wiki unless asked — see below).
Group entries by **source-person** (or by sub-angle if that reads better), and
for each entry give:

- **Title** (linked)
- **Author + their lab/role** — this is the authority signal; always include it
- **Format & length** where useful (e.g. "40-min talk", "109-page report")
- **One line on why it's worth it** — what you'll specifically get from it

Lead with a one-line "who defines this frontier" framing so the user sees the
landscape, then the list. Keep annotations tight; this is a pointer list, not a
summary of each source. Mark any entry that came from the user's vault with
"already in your vault" so they can tell new material from what they've saved.
If a key sub-angle has no strong primary source, say so honestly rather than
padding with weak material.

## Output destinations

- **Default — console only.** Print the curated list in the response. Do not
  persist anything.
- **Opt-in — persist as a wiki.** If the user says "save as wiki", "/wiki it",
  "write it up", "persist", or similar, delegate to the `wiki` skill to save the
  curated list as a vault article. Hand `wiki` a slim pointer to the list you
  just produced plus the source links; let it own folder/title/frontmatter. Only
  do this on explicit request.

## Example

**Prompt:** "find authoritative sources on agent harness design"

**Vault-first pass (step 1):** a `research-notes` query for "harness engineering"
surfaces a whole `AI/Agent/harness/` folder. Reading it yields the prior: the
*term* "harness engineering" was coined by **Ryan Lopopolo (OpenAI Codex team)**
in a Feb 2026 post; the folder also points at an Anthropic dynamic-workflows post
and several named threads. Those names (OpenAI Codex, Anthropic) and that exact
term now drive the web search — instead of the generic "building agents" queries
a cold start would have used, which bury the coinage entirely.

**Good response shape:**

> **Who defines this frontier:** OpenAI's Codex team (who coined "harness
> engineering"), Anthropic (Claude Code), and a handful of named practitioners.
> Here's their primary material:
>
> **OpenAI — Codex team**
> - *Harness engineering: leveraging Codex in an agent-first world* — Ryan
>   Lopopolo, OpenAI, blog (Feb 2026) — **already in your vault.** The post that
>   coins the term: shipped ~1M lines with 0 hand-written code; "humans steer,
>   agents execute." The canonical primary source for this exact phrase.
>
> **Anthropic**
> - *Effective harnesses for long-running agents* — Anthropic Engineering, blog
>   — the most on-topic first-party piece on harness design for long-running
>   agents.
> - *Building Effective Agents* — Schluntz & Zhang, Anthropic — the canonical
>   workflow/agent pattern taxonomy everyone cites.
>
> **Andrej Karpathy**
> - *Deep Dive into LLMs* — 3.5h lecture — foundational intuition (older but
>   still essential) for what the harness is wrapping.

Note how the vault pass set the vocabulary and the lead source *before* any web
query; how every entry names the author + their org and links primary material;
how vault hits are marked; and how it excludes anonymous "top N agent frameworks"
roundups.

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

**Match the kind of insider to the kind of topic.** "Frontier insider" is not
always a researcher:

- **Technical / how-it-works topics** (architectures, algorithms, system
  design) → founders, lead researchers, and named engineers; their papers,
  talks, and engineering blog posts.
- **Industry / market-trend topics** (where a sector is heading, demand
  drivers, competitive dynamics, capex cycles) → the **CEOs and senior
  executives of the leading companies in that sector**. A CEO running the
  business has the sharpest, most accountable read on the trend — they're
  steering capital against it. For "optical communication industry trend," that
  means talks/interviews from the **Marvell (MRVL) CEO, Lumentum (LITE) CEO,
  Coherent, Broadcom, etc.** — earnings-call commentary, investor-day keynotes,
  and sell-side/podcast interviews — not a generic analyst explainer. Prefer the
  operator's own words over second-hand market commentary, the same way you
  prefer a researcher's paper over a summary of it.

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

Before touching the web, mine the vault — and **do this in a subagent**, not in
the main conversation. It is a required first step (skip only if the user wants
external-only material or has no vault). Delegating is the single biggest token
saver: the subagent reads the index and note bodies in *its own* context and
returns only a compact set of seeds, so the 1,000+-line index and full note
bodies never enter the main thread.

Spawn a `general-purpose` subagent and instruct it to:

- **Run the `research-notes` workflow in default mode (index + search),
  console-only.** Honor research-notes' contract at this seam: keep its index
  browse ON — do NOT use its reserved **"search-only"** mode (that skips the
  index and would miss a vault folder dedicated to the topic), and the FTS sweep
  must also stay (the index does not cover the whole vault, so search catches
  on-topic notes filed under unrelated folders — e.g. an optical note living in
  an `AI Chips` folder). Pass an explicit **"no wiki / console-only"**
  instruction so the sub-step never persists its own article. Let research-notes
  own the query count and sweep mechanics; this skill only adds *what angles* to
  cover: also query the names of any labs/people you already suspect own the
  frontier, so the vault can confirm or expand that list.
- **Triage before full-read.** Judge relevance from `notes-search` snippets,
  titles, and index summaries first; never read a full note body just to
  discover it is off-topic.
- **Extract, don't ingest.** Triage *before* opening anything: judge each
  candidate from its `notes-search` snippet and the index one-line summary —
  these are purpose-built snippets, better than reading the file's first N lines.
  For notes that survive triage, this task needs each one's frontmatter
  (`source:`, `author:`), its intro, and any reference / `参考资料` list — not the
  body. Harvest links in bulk with `grep -rhoE "source: ?https?://[^ )\"']+"
  <topic-folder>` and `grep -n "source:\|http\|arxiv" <note>`. Only when a
  survivor genuinely needs its framing, do a bounded `Read` (limit ~40 lines) for
  the frontmatter + intro — the `参考资料` list sits at the *bottom* of the note,
  so a head read alone misses it (the grep above is what catches those links).
  Use `rtk read` for the rare genuine gist-read; reserve full plain `Read` for
  the few notes that truly warrant it.

The subagent should **return only seeds, not bodies** — three things that drive
everything downstream:

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
  talk. For an **industry-trend** topic, these named people are instead the
  **CEOs/executives of the leading companies in the sector** (e.g. MRVL CEO,
  LITE CEO for optical comms) — list the dominant firms, then their named
  leaders. This is the most important step: named people are how you find
  primary material that generic searches bury. The vault is your best source of
  these names; supplement with search only for gaps.

If the vault and your own knowledge leave gaps, run a search to fill them (e.g.
`who pioneered <topic>`, `<topic> lead researcher`, `<topic> seminal paper
authors`) — but treat that only as scaffolding to get to their primary work.

### 3. Hunt primary outputs in the right channels

**Run the hunt in a subagent too.** Web search returns verbose, low-density
output (snippets plus auto-generated summaries) and WebFetch returns whole
pages; keep all of it out of the main thread. Spawn a `general-purpose`
subagent, hand it the people/orgs/terms from step 2, and have it return only a
compact, annotated candidate list (title, URL, author + role, format/length,
one-line why) — never raw search dumps or fetched page text. It applies the same
*extract-don't-ingest* discipline: WebFetch only to confirm
authorship/first-party/on-topic and return a one-line verdict, not the page
body. You then rank (step 4) and present (step 5) from that returned list.

For each key person/org, the subagent searches their **primary** channels,
preferring authored, first-party material over anyone's summary of it:

| Channel | What to look for |
|---|---|
| arXiv / lab research pages | The actual papers and technical reports they authored |
| Official lab + engineering blogs | e.g. `anthropic.com/research`, `openai.com/research`, lab eng blogs |
| Conference talks & keynotes | NeurIPS/ICML invited talks, dev-day keynotes, internal-turned-public talks |
| YouTube lectures | Long-form deep dives (e.g. Karpathy), recorded talks, university lectures |
| High-signal podcasts | Dwarkesh, Latent Space, No Priors, Lex (be selective), where insiders go long-form |
| Earnings calls & investor days (industry topics) | CEO/CFO commentary in earnings-call transcripts, investor-day keynotes, and sell-side conference fireside chats — the operator's own read on the trend |
| Executive interviews (industry topics) | CNBC/Bloomberg interviews and business podcasts where a sector CEO goes long on where the industry is heading |
| Personal sites / long threads | A researcher's own blog or substantive X/Twitter thread |

Search tactics:
- Query by **person + topic** (`<name> <topic> talk`, `<name> <topic> paper`),
  not just topic — this is what surfaces the primary material.
- **Run a latest-cycle pass, and don't anchor queries to a past year.** Fast
  topics move every cycle, so recency must drive *retrieval*, not just ranking
  (step 4). For each key person/org also run a recency-first variant —
  `<name> <topic> latest`, `<topic> <current-year>`, the newest product
  generation / conference edition — so the most recent keynote, paper, or
  earnings call surfaces alongside the foundational ones. **Never hardcode a
  year you merely remember** (e.g. searching `Snapdragon Summit 2024` because
  that's the edition you know) — a bare past-year anchor pins retrieval to a
  stale event before ranking can weigh recency. Pin a specific past year *only*
  when you are deliberately hunting the category's origin/seminal moment; for
  "what's current," let the engine return the newest and let step 4 decide what
  is current vs. foundational-but-still-essential. **For industry-trend topics
  this is non-negotiable:** pull the *most recent* earnings call, investor day,
  and keynote edition (this cycle's summit, not a prior year's) — the operator's
  current-cycle read is the entire point of the exercise.
- When a strong candidate appears, use WebFetch to confirm it's genuinely
  first-party and on-topic (right author, right depth) before listing it.
- Follow citation/host trails: a good podcast episode names papers; a paper's
  authors have other talks.

### 4. Rank by authority × recency × depth

Score candidates on three axes and lead with the best:

- **Authority** — how central is this person/org to the topic? First-party
  builders > adjacent practitioners > commentators.
- **Recency — weight it by how fast the topic moves (three regimes):**
  - *Industry / market-trend topics* — recency dominates. Lead with the latest
    cycle (most recent earnings call, keynote, investor day, current product
    generation); the frontier read is the operator's *current* read. Keep older
    material only when it is genuinely thesis-defining background (e.g. the piece
    that first framed the bull/bear case or coined the category) — and label it
    as background so it reads as context, not current state.
  - *Fast-moving technical topics* — prefer recent work, but never drop a seminal
    foundational piece just because it's older. Keep the paper/talk that
    introduced the method or architecture and mark it "foundational (older but
    still essential)."
  - *Ageless / slow-moving topics* (health, eye care, math/CS fundamentals,
    evergreen how-it-works) — recency barely matters. Judge on authority and
    depth; do not penalize a great source for being old, and do not pad with a
    worse-but-newer one to look current.
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

## When a step fails

This skill leans on subagents, a vault, and web search — any of which can come
back empty or time out. Never let one dead step kill the whole task; degrade
along the table below (trigger → first fix → if it still fails).

| Trigger | First fix | If it still fails |
|---|---|---|
| Vault subagent times out / errors / returns nothing usable | Proceed without it — build the frontier map (step 2) from your own knowledge + the web sweep | Note "couldn't mine the vault" in one line and continue; never block the task on the vault step |
| Vault has no notes on the topic | Say so briefly, build the frontier map from scratch (step 2) | — |
| A key person/org returns no first-party material | Try adjacent channels (talk → paper → eng blog → podcast) and the recency-first variant before giving up | List the gap honestly per step 5; never pad with a listicle/summary to fill it |
| WebFetch can't confirm authorship / first-party | Drop the candidate, or list it explicitly marked "attributed, unverified — not confirmed first-party" | Never present unverified second-hand material as if it were primary |
| Hunt subagent times out mid-search | Present the compact candidate list it already returned, flagged partial | Re-run only the missing person/org, not the whole hunt |
| Topic regime unclear (industry vs technical vs ageless) | Default to technical (regime 2); 🔴 ask **one** clarifying question only if recency handling would change the answer materially — otherwise proceed, don't stall | — |

## Anti-patterns — never do these

The whole skill is a fight against secondary, low-signal material. These are the
specific ways that fight gets lost; treat each as a red line, not a preference:

- **Never list a summary when you can link the primary.** About to cite an
  explainer *of* a paper/talk? Link the paper/talk itself.
- **Never present unverified or second-hand material as primary.** Confirm
  first-party authorship first, or mark it "attributed, unverified."
- **Never lead with listicles, "top N tools" roundups, SEO content, or
  AI-generated summaries.** Demote them hard (step 4).
- **Never hardcode a year you merely remember** (e.g. `Snapdragon Summit 2024`) —
  it pins retrieval to a stale event. Let the engine return the newest; weigh
  recency in step 4.
- **Never skip the vault when one exists**, and **never use research-notes'
  "search-only" mode** — mine the vault first with index browse + FTS sweep on
  (step 1), or say in one line why you couldn't.
- **Never read a full note body just to discover it's off-topic** — triage from
  `notes-search` snippets and index summaries first.
- **Never pad a weak sub-angle to look complete** — say "no strong primary source
  here" honestly (step 5).
- **Never force recency where it doesn't belong** — an ageless topic (regime 3)
  ranks on authority + depth; don't swap a great old source for a worse new one.
- **Never persist to a wiki unless explicitly asked** — default is console-only.

## Output destinations

- **Default — console only.** Print the curated list in the response. Do not
  persist anything.
- **🔴 CHECKPOINT — persist a wiki only on explicit opt-in.** Writing a wiki
  article is a file write you cannot silently undo, so it is **gated, never
  automatic**. 🛑 STOP and write **only** when the user explicitly says "save as
  wiki", "/wiki it", "write it up", "persist", or similar. On that signal,
  delegate to the `wiki` skill: hand it a slim pointer to the list you just
  produced plus the source links, and let it own folder/title/frontmatter. If
  the ask is ambiguous ("can you also save this somewhere?"), confirm the
  destination once before writing. Never persist on your own initiative.

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

That example is a **fast-moving technical** topic (regime 2): recent work leads,
but Karpathy's older lecture survives as labeled foundational. An **industry /
market-trend** topic (regime 1) ranks differently — recency dominates:

**Prompt:** "find authoritative sources on the optical-communication industry trend"

**Good response shape (abridged):**

> **Who defines this frontier:** the CEOs steering capital against the trend —
> Marvell (MRVL), Lumentum (LITE), Coherent, Broadcom.
>
> **Marvell — Matt Murphy (CEO)**
> - *Q3 FY2026 earnings call* — the latest call (most recent quarter) — his
>   *current* read on custom-silicon + optical DSP demand. **Lead here.**
> - *AI Investor Day keynote (this year's)* — the current TAM/roadmap framing.
>
> **Lumentum — Michael Hurlston (CEO)**
> - Most recent earnings call + a 2026 sell-side fireside chat — current
>   datacenter-interconnect demand read.
>
> **Background (labeled, not current state):**
> - The investor-day deck that first framed the AI-optical bull case — useful
>   origin context only; do not present as the present.

Note the contrast: the operator's *latest* call/keynote leads, and the older
thesis-defining deck is demoted to clearly-marked background — whereas an
**ageless** topic (regime 3, e.g. eye-care for high myopia) would ignore date
entirely and rank purely on authority and depth.

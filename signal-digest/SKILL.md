---
name: signal-digest
description: Power-law digest of the user's information feeds — by default X For You + Following, the Reddit home feed and the AI-news daily brief, or any inputs the user names instead (e.g. "the latest 50 posts in my vault", a notes folder, a JSONL list, an X search or subreddit fetched first) — prefilter cheaply with TypeSafe's Jev scoring model, then pick the vital few items that carry most of the value for investing (return with controlled risk), important AI technology advances and industry trends, startup ideas and big general concepts, and write a short report of key takeaways. Use whenever the user asks for "my digest", "what matters in my feeds today", "filter my feeds", "the most important posts across X/Reddit/AI news", "apply the power law to my feeds", "signal vs noise from my sources", wants a cross-source summary of their feeds rather than one feed, or asks to "digest" / "find what matters in" any set of posts or notes — even if they don't name this skill. To just fetch or summarize one X query or one subreddit, use fetch-x-posts / fetch-reddit-posts instead.
---

# signal-digest

Most of the value in a day's feeds sits in a handful of items. This skill finds
them in three stages, each cheaper per item than the next one is:

1. **Collect** (script, no LLM): every source is fetched and normalized to one
   item schema in a run directory.
2. **Prefilter** (script, Jev): each item is scored on about ten atomic questions
   (relevance to holdings and premises, new information, sourcing, generality,
   durability, …) and combined in code. Jev costs about $0.04 per million input tokens, so a full run is
   about one cent. This stage is **recall-first**: it only discards items that are
   confidently promotional or confidently low-value. It always passes items Jev was unsure
   about (it is weaker on Chinese) and possible tail-risk claims.
3. **Pick and digest** (you): read the shortlist, choose the vital few, verify,
   and write the report. The judgment lives here; the scores are a guide.

## Run

```bash
cd ~/projects && /opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python -m news.src.signal_digest.run run
```

With no arguments it collects all four default sources (`x_for_you`, `x_following`,
`reddit_home`, `ai_news`), filters with Jev, and prints one JSON object with
`run_dir`, per-source counts and errors, and the `shortlist` path. It takes a few
minutes because X article enrichment and Reddit drive a browser. Run it with
`run_in_background` and wait for the notification.

Other invocations you will need:

```bash
# skip Jev and pass every item through (small hauls, or Jev down / no key)
… run --filter none

# re-filter an existing run without re-fetching (after tuning, or to switch filters)
… filter --run-dir latest --filter none
```

`-h` on the module and on each subcommand is the authority on flags (counts,
thresholds such as `--min-keep` and `--max-keep`, `--profile`, model). Don't
restate them here.

## Reruns on the same day

Each run gets its own directory named by its start time (`YYYYMMDD_HHMM`, with
`_2` appended for a second run in the same minute), and nothing in an earlier
run is overwritten, so every run's report stays. `--same-day` decides what a run
does with today's earlier runs that had the same inputs (the same built-in
sources and `--input` targets). "Today" is the local calendar date.

| The user asks for | Mode |
|---|---|
| "my digest", or a rerun with no qualifier | `union` (the default): select from this fetch plus everything today's earlier runs collected, so the report is the day's best-of as of now |
| "anything new since earlier?" | `--same-day new`: only items no earlier run today collected |
| "a fresh digest", or a rerun after retuning the filter | `--same-day fresh`: ignore earlier runs |

Union and new reuse the Jev answers of earlier runs, so only items not seen
before cost anything. In `new` mode, `nothing_new: true` means every fetched
item was already collected. Say so and stop. Otherwise, report only what clears
the bar; "nothing new worth your time" is a good answer, and filling the caps
with weak items is not.

`run` deletes runs dated more than 7 days ago before it starts. Their item counts
are kept in `seen_counts.json`, so `stats` pick rates stay correct.

## Choose the inputs

Use the default feeds only when the user names no inputs. When they do name
some, digest exactly those. `--input TARGET[:NAME]` takes anything as its own source and is
repeatable. Giving it drops the default feeds unless you also pass
`--sources default` (or a list such as `--sources x_for_you,ai_news`).
`--input-limit N` keeps the newest N per input.

| The user asks for | Run |
|---|---|
| nothing specific ("my digest") | `run` |
| some of the built-in feeds | `run --sources x_following,ai_news` |
| "the latest 50 posts in my vault" | `run --input ~/notes/raw/:vault --input-limit 50` |
| a vault folder, a note, or a glob | `--input ~/notes/wiki/AI/:ai_wiki`, `--input '~/notes/raw/**/*NVDA*.md:nvda'` |
| notes picked by topic or meaning | find them with `/research-notes`, write their paths one per line to a scratch file, then `--input @paths.txt:topic` |
| an X search, an account, or a subreddit | fetch first with `fetch-x-posts` / `fetch-reddit-posts` ("fetch only"), then `--input` the JSONL or the output folder |
| any other list (RSS export, HN, a CSV turned into JSONL) | write JSONL with `title`, `text`, `url`, `author`, `created_at` and `--input` it |
| their feeds plus something else | `run --sources default --input …` |

In the vault, "posts" means clippings and ad hoc notes in `raw/`. `wiki/` holds
curated notes, and the root also holds generated `index/` notes, so don't point
at the whole vault for "latest posts". Each document becomes one item (title
from frontmatter or the first heading, a `summary` field leads the text, `ref` is
the note's absolute path). The newest are chosen by file modification time.
Small hauls (a dozen items or fewer) don't need the prefilter, so add
`--filter none`. Name the inputs on the report's `Inputs:` line whenever they are
not the default feeds.

**Failure handling.** One broken source doesn't stop the run. It shows up in
`collect.sources.<name>.error`; report it and carry on with the rest. If the
filter step fails, items are already saved. A missing `TYPESAFE_API_KEY` returns
`ok: false` with the fix (create a key at console.typesafe.ai and add `export
TYPESAFE_API_KEY=...` to `~/.config/secrets.env`). Tell the user, then re-run
`filter --run-dir <id> --filter none` so the digest still happens.

**Auth.** X uses Chrome cookies through `xreach`. Reddit uses the browser
project's stored session; if it has expired, refresh it with `python
~/projects/browser/src/refresh_state.py reddit.com`. The AI-news source reads the
newest brief written by the 8am `zhihu-ai-news` LaunchAgent. If `brief_date` in
the output is not today, say how old the brief is.

## Read selectively (token discipline)

Read `shortlist.md` (the survivors, with signals and text up to 1,500
characters) and nothing else in bulk. It is ordered by Jev value, then VERIFY,
UNCERTAIN and UNSCORED items. For an item you might pick, open its full content
through `ref`: a `raw/…md` Reddit post, a line of the raw X JSONL, or the
absolute path of a note or document input. Skim the
top of `discarded.md` once per run as a recall check, and pull back anything the
filter wrongly dropped.

## Pick the vital few

Treat Jev's `value` as a prior, not a verdict. Pick **at most 5 items for
Investing and at most 3 for each other track, and fewer or zero when the day is
thin for that track**. Investing gets more room because a missed signal on a
holding costs money, while a missed idea can be picked up later. The cap is what
makes this a power-law digest rather than a survey: an item past the cap means
one of the others isn't vital, so cut it or fold it into another item as
supporting evidence. When nothing in a track clears the bar, write "nothing today"
under its heading rather than promoting a weak item. Each pick goes in exactly
one track; an item is filed under Investing only if it bears on a holding or on
a premise that actually exists in `reader.premises`. Don't invent premises. The
tracks:

- **Investing** (return with controlled risk). The test is whether this could
  change a decision: a position, a valuation input, or a premise in the user's
  Portfolio Premise Register (`reader.premises` in `profile.json`). Weight
  evidence *against* a premise above confirmation: feeds tuned to engagement
  serve bullish takes on what the user already owns, and losses compound
  asymmetrically. A crowd of bullish posts on a holding is a sentiment
  reading, not news. Say so, and compare against the user's latest valuation
  when one exists (`~/projects/stock_picker/data/valuations/<TICKER>/`).
- **AI advances, trends and startup ideas.** Three kinds of item belong here:
  - an important AI technology advance: a new capability, a new method or
    architecture, or a step change in efficiency or cost. Say what it does, how
    it works at a level a strong engineer can follow, and what it enables or
    threatens;
  - a durable shift in how the AI industry works;
  - an unmet need that a product could fill.

  How long the point stays useful matters more than how new it is. An advance
  earns a pick when it changes what is possible or what it costs, not when it is
  a benchmark bump.

- **Big ideas.** A concept that explains many things at once or recurs in many
  forms is worth more than many facts, because grasping it unlocks the rest.
  Examples: bounded rationality, supply bottlenecks and where the overflow goes,
  economies of scale, feedback loops, the way agents change who captures value.
  For each, name the concept, state it in one sentence, and list the different
  forms it takes. Include the forms visible elsewhere in this same haul; that
  cross-linking is the payoff, and it is why this track comes last in the report.

Posts by people who run major AI, chip, cloud or internet companies, and faithful
reports of their words, are primary sources on strategy. They are often the
earliest public signal of where the industry is heading, so read them closely.
The prefilter boosts them; the list and per-person weights live in
`src/signal_digest/leaders.py`, and the signals line shows `leader xN` when the
boost applied. Still judge by content, not by name. A prolific poster such as
Elon Musk mostly produces jokes, politics and reposts, which count for nothing;
his posts earn a pick only when they say something specific about his
companies' AI, chips or compute plans.

High engagement measures what the crowd already knows. Use it as context, never
as the reason to pick. Collapse the same story told by several sources into one
pick, and note the sources (`also_in`).

**Verify before you trust.** For every investing pick, and every VERIFY item
that would matter if true, spend one web search to confirm the claim and read
what was actually said. Headline accounts such as Polymarket and zerohedge
routinely distort the framing, and a verified-but-reframed claim can move from
the investing track to the ideas track. State the verification result and link
the primary or named source.

## Report

Write `report.md` into the run directory with this structure:

```markdown
# Signal digest — <date> <HH:MM> (<run id>)

Inputs: <only when they are not the default feeds, e.g. "50 newest notes in ~/notes/raw/">

## TL;DR

**Investing**
- <One bullet per pick: the takeaway as a claim and, in a few words, why it matters to the user.> ([<short label>](<link>), [<verification>](<link>))

**AI advances, trends & ideas**
- <…>

**Big ideas**
- <…, or "Nothing today." when the track has no picks>

## Investing

### <Takeaway as a claim>

Sources: [<author>, <source>, <date>](<link>) · [<other source>](<link>)

What it says (engagement) · which holding or premise it bears on (for or against) · what it changes or why it changes nothing · verification result with link.

## AI advances, trends & ideas

### <Takeaway>

Sources: [<author>, <source>, <date>](<link>)

…

## Big ideas

### <Concept name>

Sources: [<author>, <source>, <date>](<link>)

The idea in one sentence · the forms it takes (including ones from this haul, each linked) · why it's worth holding onto.

## Dropped

<N collected → M shortlisted → K picked.>

- [<author>, <source>](<link>): <what it was, and why it lost>
- Source errors: <source and error, or none>
```

In a union run, shortlist items marked `PICKED EARLIER TODAY` were already
reported. If one is still among the vital few, keep it and append "(earlier
today)" to its heading and its TL;DR bullet. List new picks first within each
TL;DR group, so a rerun shows what changed at a glance.

The TL;DR is bullets, never a paragraph, grouped under the same three tracks
as the sections below and in the same order (Investing, AI advances, Big ideas). It holds one bullet per pick and
nothing the sections don't support, so the user can stop reading there. Keep all
three headings; a track with no picks gets "Nothing today." Each bullet ends with
inline links under short labels (`@handle`, `r/sub`, the outlet's name): the
original source, plus the verifying source when there is one. The full list
stays on the pick's `Sources:` line.

**Every pick gets one clickable `Sources:` line** right under its heading, with
all its sources on that one line. The description starts after a blank line,
as its own paragraph. A line break alone would merge the two in rendered
Markdown. Links come from that item's `links:` line in `shortlist.md`. That line
holds the post URL and, for a vault note or other local document, an
`obsidian://` or `file://` link that opens it. Link the note itself, and its
original URL too when it has one. Give every item you folded into a pick
(`also_in`, supporting evidence) its own link. Each near-miss in Dropped links
inline the same way, so the user can open any of them. Copy links from the shortlist
rather than building them by hand, and never link a URL you didn't see. When an
item has no link (`links: none`), say so and cite it by author and date.

The reader is a strong engineer, not a finance specialist. Expand jargon on first
use, give every figure its source and date, and label fiscal years. **Write the
report in English**, whatever the sources' language. Cite Chinese (or any other
language) verbatim only where the original wording carries something a
translation would lose, such as a coined phrase, a named framework or a quote
being weighed, and follow it with an English gloss. In chat, reply with the TL;DR bullets plus the
report path. Don't paste the report back.

## Log the picks

After the report is written, record the picks:

```bash
… pick --run-dir <run id> --ids <id1>,<id2>,…
```

Pass every pick. Picks already logged by an earlier run today are skipped, and
listed under `already_logged_earlier_today`, so nothing is counted twice.

`… stats` then shows pick rates by source and author across runs. That is the
second power law: a few accounts and sources produce most of the picks. Suggest
pruning sources that never get picked, and following the accounts that do. Picks
whose `keep_reason` is `uncertain` or `verify` show what Jev's value ranking
alone would have missed. If they pile up, Jev's weights in
`src/signal_digest/jev_filter.py` need retuning, not the recall guard.

## Where things live

- Code: `~/projects/news/src/signal_digest/` (`run.py` CLI, `sources.py`
  adapters, `jev_filter.py` questions, weights and selection, `profile.py`
  reader context). Add a new built-in source by writing one `collect_<name>`
  adapter and registering it in `SOURCES`.
- Data: `~/projects/news/data/signal_digest/runs/<run id>/` (whole runs are
  deleted after 7 days), `picks.jsonl` and `seen_counts.json` (item counts of
  deleted runs, for `stats`).
- The reader profile is rebuilt every run from `stock_picker/data/portfolio.csv`,
  `data/ticker.csv` and the premise register. `--profile FILE` swaps in any JSON
  object for a different reader.

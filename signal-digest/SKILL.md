---
name: signal-digest
description: Power-law digest of the user's information feeds for two goals — investment return with controlled risk, and keeping up with AI technology and industry trends for learning and startup ideas. Digests the default feeds (X For You + Following, the Reddit home feed, the AI-news daily brief, X's "Today's News") or any inputs the user names instead (a notes folder, a JSONL list, an X search or subreddit fetched first). A script collects and prefilters with TypeSafe's Jev; the agent then picks the vital few (at most three a day), verifies them and writes a short report. Use whenever the user asks for "my digest", "what matters in my feeds today", "filter my feeds", "signal vs noise from my sources", "apply the power law to my feeds", wants a cross-source summary of their feeds rather than one feed, or asks to "digest" / "find what matters in" any set of posts or notes, even without naming this skill. To just fetch or summarize one X query or one subreddit, use fetch-x-posts / fetch-reddit-posts instead.
---

# signal-digest

## Goal

The feeds deliver well over a hundred new items a day. A few of them carry most
of the value for the user's two goals:

1. **Investing**: maximize investment return with controlled risk. The portfolio
   is concentrated in AI infrastructure (`reader.holdings`), and the user's
   Portfolio Premise Register (`reader.premises`) states what the positions
   assume.
2. **AI**: keep up with AI technology and industry trends, to learn and to find
   startup ideas.

The job is to find those few items and nothing else. The test for every item is
"would the user regret not knowing this?" Three things follow:

- **Zero picks on a goal is a normal day.** Most days have no investing pick at
  all. Filling a slot with a weak item costs more than leaving it empty, because
  the user stops trusting that a pick means something.
- **Value is relative to what the user already knows.** A story reported in an
  earlier digest is worth nothing today as a recap. But stories that keep
  developing over several days are often the important ones, so a development
  is a pick: report what is new and what it changes, not the story so far. A
  development means the new fact changes what the story means for the user (a
  premise, a decision, what is now possible); a new voice commenting on the same
  facts is not one.
- **The report is read in two minutes.** The TL;DR must stand alone.

## How it works

1. **Collect** (script, no LLM): every source is fetched and normalized into one
   run directory.
2. **Prefilter** (script, Jev): each item is scored on about ten atomic questions
   and combined in code. This stage is recall-first and cheap (about one cent a
   run). It discards only confident ads and confident junk, and always passes
   items Jev was unsure about (it is weaker on Chinese).
3. **Pick and write** (you): read the shortlist, choose the vital few, verify,
   write the report, log the picks. The judgment lives here; Jev's scores are a
   prior, not a verdict.

## Run

```bash
cd ~/projects && /opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python -m news.src.signal_digest.run run
```

With no arguments it collects the five default sources, filters with Jev, and
prints one JSON object with `run_dir`, per-source counts and errors, and the
`shortlist` path. It takes a few minutes (X and Reddit drive a browser), so run
it with `run_in_background` and wait for the notification. `-h` on the module
and on each subcommand is the authority on flags; don't restate them here.

```bash
… run --filter none                         # small hauls, or Jev down / no key
… filter --run-dir latest --filter none     # re-filter an existing run, no re-fetch
```

### Reruns on the same day

Every run gets its own directory (`YYYYMMDD_HHMM`), and nothing is overwritten.
`--same-day` decides what a run does with today's earlier runs that had the same
inputs:

- "my digest", or a rerun with no qualifier: `union` (the default), the day's
  best-of as of now. Items already reported today are marked
  `PICKED EARLIER TODAY`; keep one only if it is still among the vital few, with
  "(earlier today)" on its heading and TL;DR bullet, and list new picks first.
- "anything new since earlier?": `--same-day new`, only items no earlier run
  today collected. `nothing_new: true` means every item was already seen; say so
  and stop. Otherwise "nothing new worth your time" is a good answer.
- "a fresh digest", or after retuning the filter: `--same-day fresh`.

### Other inputs

Use the default feeds only when the user names no inputs; when they do, digest
exactly those. `--input TARGET[:NAME]` is repeatable and drops the default feeds
unless you also pass `--sources default`.

- some built-in feeds only: `run --sources x_following,ai_news`
- "the latest 50 posts in my vault": `run --input ~/notes/raw/:vault --input-limit 50`
  (`raw/` holds clippings and ad hoc notes; `wiki/` is curated; don't point at the whole vault)
- a folder, a note, or a glob: `--input ~/notes/wiki/AI/:ai_wiki`, `--input '~/notes/raw/**/*NVDA*.md:nvda'`
- notes chosen by topic: find them with `/research-notes`, write the paths one per
  line to a scratch file, then `--input @paths.txt:topic`
- an X search, an account, or a subreddit: fetch first with `fetch-x-posts` /
  `fetch-reddit-posts` ("fetch only"), then `--input` the JSONL or the folder
- any other list: JSONL with `title`, `text`, `url`, `author`, `created_at`

A dozen items or fewer don't need the prefilter; add `--filter none`. Name the
inputs on the report's `Inputs:` line whenever they are not the default feeds.

**Failures.** One broken source doesn't stop the run. The pipeline repairs what
it can on its own, and every repair leaves a trace in `manifest.json` under
`collect.sources.<name>`: a source that raises or returns nothing is fetched a
second time after a short pause (`attempts: 2`); a failed enrichment (retweet
lookup, linked article) keeps the posts unenriched instead of losing the feed;
Reddit refreshes its own session; an X Today's News file that is not from today
is fetched inline (`repair`, or `repair_failed`). A source that still failed
keeps its `error`, and its traceback is in the run's `collect.log`. The
shortlist header repeats all of this as a `Collection:` line when anything
happened. Two things are yours:

- **Repair once, then refetch once.** When a source still has an `error` or
  zero items, read `collect.log` for the traceback. An operational cause (an
  expired X or Reddit session, a fetcher that just needed another go) you fix
  directly. A bug in our own code (a traceback into `~/projects/news/src` or
  `~/skills`) you fix minimally, run that package's tests, and only when they
  pass commit it in that repo with a message naming the run, `git pull --rebase`
  and push to main; if the tests fail or one attempt doesn't find the cause,
  `git checkout -- .` there and leave the failure for the Collection line. Then
  `… refetch --run-dir <run id>`: it fetches only the failed sources again into
  the same run, merges the items, re-filters, and records `repair` on each. It
  refuses a second pass on the same run, so there is no refetch loop. The
  unattended job posts any failure, repair or lint error to Discord, which is
  how a problem stays visible after the daily review retires.
- **Report it.** The report's `Collection:` sentence, in the opening paragraph of
  Near misses right after the funnel line (not a bullet: the bullets are items
  that lost), opens with what every source
  fetched (the shortlist header's "Fetched per source" counts), so a feed that
  quietly came back thin is visible even when nothing failed, then names every
  source that failed, was retried, or was repaired, with what happened, including a code fix's commit
  hash and the refetch result (the lint checks the names against the manifest). When a whole X feed is still missing from the morning run, say
  so in chat too, since the afternoon run's default `union` merges the morning
  items but cannot recover what was never fetched.

A missing
`TYPESAFE_API_KEY` returns `ok: false` with the fix; tell the user and re-run
`filter --run-dir <id> --filter none`. If Reddit's session has expired, refresh
it with `python ~/projects/browser/src/refresh_state.py reddit.com`. If the AI
news `brief_date` or X Today's `fetched` is not today, say how old it is.

## Read selectively

Read `shortlist.md` and nothing else in bulk. Its top holds, in order: what was
picked on earlier days this week, a "Top investing candidates" index of the top 12 by
invest composite (the overall ranking is by `max(invest, learn)`, which buries
investing items under learn-track items; every investing pick so far sat inside
this index), then the survivors ordered by Jev value, with VERIFY, UNCERTAIN
and UNSCORED items last. The keep line is drawn per track (the top 35
by invest and the top 35 by learn both pass), so an investing post is never
pushed out by learn-track articles. The value order is not a cross-source
comparison: since AI-news items carry full article bodies, long Zhihu articles
take most of the top ranks (ranks 1–5 on 2026-10-12) while a two-line X post on
a holding sits at rank 40. That is left as it is, because the articles that get
picked are long too. Read the investing index and the tickers, not the rank,
for investing. Then:

- **Skim the top of `discarded.md`** once per run. The filter is recall-first but
  not perfect; it has dropped real picks as "promo" (a question-style Reddit post,
  a clickbait-styled Chinese headline). Pull back anything wrongly dropped.
- **Open the full content of anything you might pick** through its `ref` (a
  `raw/…md` Reddit post, a line of the raw X JSONL, a note's absolute path).
- **AI-news items carry the whole article.** Jev scored its first 2,500
  characters and the shortlist shows 1,500; the full text is in the item's
  `ref` (`raw/ai_news/NN.md`). An item with no `ref` and a one-sentence text
  came from an older brief (snippet only) or a failed body fetch; open the
  Zhihu URL before picking or dismissing it.
- **Quote tweets and retweets now arrive whole.** A retweet carries the full
  retweeted text, and a quote tweet ends with `[Quoting @author: …]`, one level
  deep. When that block is missing on a `quote` item, or a retweet still ends in
  "…", the lookup failed: open the URL before dismissing it when the author or a
  holding's ticker matters ("That's why I'm invested in $COHR" says nothing on
  its own).
- Items marked `PICKED <date>`, and stories in the "Picked on earlier days" list,
  were already reported. A development in one of them is a pick (developing
  stories tend to matter most); lead the entry with what is new and link the
  earlier pick's source once. A restatement without a new fact is not a pick,
  and neither is another commentator's take on facts already reported, nor the
  same person's longer version of a take already picked (the talk behind a
  thread, the slides, an essay). A story picked on two earlier days needs its
  first sentence to say what changed.
- **Old news is usually known.** The user runs these tools daily, so a launch,
  price change or deal from a major lab or vendor that is more than two days old
  is assumed known. Check whether the feed carried it earlier
  (`grep -l '<term>' ~/projects/news/data/signal_digest/runs/*/items.jsonl`);
  if it did and it wasn't picked, it needs a reason now. It can still earn a pick
  for a non-obvious consequence; then the consequence is the heading and the
  TL;DR bullet, and the known fact gets one clause.

## Pick the vital few

**At most three picks a day across both goals, and usually one or two.** Lead with
the single most valuable. An item past the cap means one of the others isn't
vital: cut it, or fold it into another pick as one linked sentence of supporting
evidence. Collapse the same story told by several sources into one pick.

**Investing.** A pick must pass one of two tests:

- *A specific new fact that bears on a holding or on a premise that actually
  exists in `reader.premises`* (don't invent premises). Evidence against a premise
  outranks confirmation: feeds tuned to engagement serve bullish takes on what
  the user already owns, and losses compound asymmetrically. A confirmation
  still earns a pick when the fact is new, but it gets a short entry: the fact,
  the premise, for or against, done. "No position change" means no long analysis.
- *A sentiment cluster on holdings paired with a measured market signal that is
  itself unusual* (an implied-volatility extreme, a positioning extreme, a known
  event window). A crowd of bullish posts alone is a sentiment reading, not a
  pick; it gets one line under Near misses. When you add market data by lookup,
  say so; the feed didn't supply it.

Compare against the user's latest valuation when one exists:
`~/projects/stock_picker/data/valuations/<TICKER>/<date>.md` is the base model
and the authoritative figure; the `.whatif.md` beside it is a scenario file,
cite it only as such. Quote every figure with its file name and date.

**AI.** Three kinds of item qualify: an advance that changes what is possible or
what it costs (say what it does, how it works at a level a strong engineer can
follow, and what it enables or threatens; a benchmark bump doesn't qualify); a
durable shift in how the industry works; an unmet need a product could fill.
How long the point stays useful matters more than how new it is. When a pick is
best understood as a general concept (a bottleneck and where the overflow goes,
a feedback loop, payoff asymmetry), write it up that way: name the concept in one
sentence and link the forms it takes in this haul. That is a way of writing a
pick, not a separate quota.

**Primary sources.** Posts by people who run major AI, chip, cloud or internet
companies, and faithful reports of their words, are primary sources on strategy
and often the earliest public signal. The prefilter boosts them (list and
weights in `src/signal_digest/leaders.py`; the signals line shows `leader xN`).
Still judge by content: a prolific poster's jokes, politics and reposts count for
nothing. A leader's remark on a story already picked is a development in two
cases: it discloses a figure, a decision or guidance of the leader's own
company, or the speaker's own stake changes what the known facts mean. On
2026-10-12 the funding story had two days of issuance data and bank forecasts
behind it; then the CEO of Broadcom, the lender behind Anthropic's chip leases,
said capital could be the constraint. The same words from a commentator are a
new voice; from the lender they are the story moving from observers to a
participant. When the stake is the point, the heading says so ("the lender
behind Anthropic's chips doubts the financing"), not "two CEOs named the weak
links".

**Engagement** measures what the crowd already knows. Use it as context, never as
the reason to pick.

**Verify before you trust.** For every investing pick, and every VERIFY item that
would matter if true, spend one web search to confirm the claim and read what
was actually said. Headline accounts (Polymarket, zerohedge) routinely reframe;
a verified-but-reframed claim may move from investing to AI or drop out. State
the result in one sentence with the primary source linked. The heading and the
TL;DR then carry what the primary source says, not the feed post's paraphrase
(on 2026-10-12 a post's "memory is the weak link" became a heading; the source
said financing).

## Report

Write `report.md` into the run directory:

```markdown
# Signal digest — <date> <HH:MM> (<run id>)

Inputs: <only when they are not the default feeds, or the run is `--same-day new`>

## TL;DR

**Investing**
- <The takeaway as a claim, and in a few words why it matters to the user.> ([<label>](<link>), [<verification>](<link>))

**AI**
- <…, or "Nothing today.">

## Investing

### <Takeaway as a claim>

Sources: [<author>, <source>, <date>](<link>) · [<verifying source>](<link>)

<What it says · which holding or premise, for or against · what it changes or why nothing · verification, one sentence.>

## AI

### <Takeaway>

Sources: …

<What it does and how · what it enables or threatens · verification.>

## Near misses

<N collected → M shortlisted → K picked.> Collection: fetched <source count · source count · …>; <every source that failed, was retried or repaired, and what happened; or "all sources fetched clean on the first attempt">

- [<author>, <source>](<link>): <what it was and why it lost, one line>
```

Rules:

- **Budget: about 800 words, never more than 1,200**, links excluded. TL;DR bullets
  are one or two sentences, at most 60 words. A pick's body is under 150 words.
  Near misses holds at most five lines; the tail gets no more words than that.
  The lint rejects a longer bullet or body, so a three-pick report fits only
  when every body is tight: cut the story so far and the second example, never
  the verification sentence.
- Whenever Investing has fewer than two picks, the first Near-misses line names the
  best investing candidate that was not picked and why it lost, so a dropped
  candidate on a holding or premise never vanishes without a trace. It is a
  different item from every pick (a second claim inside a picked post does not
  count; the lint rejects it). Walk the "Top investing candidates" index from
  the top: the first item you did not pick is the one to name, with its index
  rank, unless you say why a lower one is the stronger candidate.
- Keep both TL;DR headings; a goal with no picks says "Nothing today."
- Every pick gets one `Sources:` line right under its heading, then a blank line,
  then the body (a bare line break would merge them in rendered Markdown). Copy
  links from the item's `links:` line in `shortlist.md`; never link a URL you
  didn't see. A vault note links to the note (`obsidian://`) and to its original
  URL when it has one. When an item has `links: none`, cite it by author and date.
- Label every link by what it actually is: the author or outlet at that URL. Link
  the primary source (the filing, the paper, the person's own post, the outlet
  that reported it) when it is reachable; when only secondary coverage is, label
  it "<primary> via <outlet>" rather than as the primary.
- Every figure carries its source and date; label fiscal years; expand jargon on
  first use. The reader is a strong engineer, not a finance specialist.
- A quotation links the document that contains the words (the slides, not the
  blog post beside them). A quote that reaches you through coverage (a Chinese
  write-up of an English talk) is attributed to the person only after you find it
  in the primary; otherwise attribute it to the coverage.
- **Write in English** whatever the sources' language. Quote Chinese verbatim only
  where the wording carries something a translation loses (a coined phrase, a
  quote being weighed), followed by an English gloss.
- In chat, reply with the TL;DR bullets plus the report path. Don't paste the
  report.

## Check the report, then log the picks

Run the lint before logging and fix every error it reports:

```bash
… lint --run-dir <run id>
```

It checks the word budget, the pick cap, the TL;DR bullet and pick-body lengths,
the TL;DR and `Sources:` structure, the first Near-misses line, the `Collection:`
line against the manifest (every source's fetched count, and every failed,
retried or repaired source, must be named), and every link label against its URL (a label saying "via Coinpaper" on a kucoin.com URL is the
kind of slip it exists for). `lookup_links` lists every link that is
not an item of this run: each must be a page you opened during verification, not
a URL from memory; remove any you can't account for. Warnings are judgment calls;
errors are not. A budget warning on a report whose parts all pass means the
near misses or the headings are padded; trim them. The daily reviewer runs the
same lint on your report.

A pick is an item with its own heading in the report; folded-in evidence is not
a pick. Log each with its goal:

```bash
… pick --run-dir <run id> --ids invest:<id1>,learn:<id2>
```

Picks already logged by an earlier run today are skipped and listed under
`already_logged_earlier_today`. `… stats` then shows pick rates by source and
author across runs: the second power law. A few accounts and sources produce
most of the picks; suggest pruning sources that never get picked and following
the accounts that do. Picks whose `keep_reason` is `uncertain`, `verify` or
`dropped: …` are what Jev's ranking alone would have missed; if they pile up, the
weights in `src/signal_digest/jev_filter.py` need retuning.

## Where things live

- Code: `~/projects/news/src/signal_digest/` (`run.py` CLI, `sources.py`
  adapters, `jev_filter.py` questions, weights and the per-track keep line,
  `lint.py` the report checks, `profile.py` reader context, `run_daily.py` the
  9:00 and 15:45 LaunchAgent entry point).
- Data: `~/projects/news/data/signal_digest/runs/<run id>/` (deleted after
  10 days; keep it that long so a week-later review can compare report.md against the
  items, scores and raw snapshots it came from; `collect.log` there holds the
  collectors' stderr, tracebacks included), `picks.jsonl` (the memory that
  drives `PICKED <date>` markers),
  `seen_counts.json`.
- The reader profile is rebuilt every run from `stock_picker/data/portfolio.csv`,
  `data/ticker.csv` and the premise register; `--profile FILE` swaps it.

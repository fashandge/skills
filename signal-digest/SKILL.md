---
name: signal-digest
description: Power-law digest of the user's information feeds for two goals — investment return with controlled risk, and AI technology and industry trends for learning and startup ideas. Digests the default feeds (X For You and Following, an X search for chip and cloud CEO talks, the Reddit home feed, the AI-news daily brief, X's Today's News) or any inputs the user names (a notes folder, a JSONL list, a fetched X search or subreddit). A script collects and prefilters with TypeSafe's Jev; the agent picks the vital few (at most three a day), verifies them, writes a short report and proposes stock_picker log entries. Use for "my digest", "what matters in my feeds today", "filter my feeds", "signal vs noise from my sources", a cross-source summary of the feeds, or "digest" / "find what matters in" any set of posts or notes. To fetch or summarize one X query or one subreddit, use fetch-x-posts / fetch-reddit-posts instead.
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
   write the report, propose entries for the user's research logs, log the picks.
   The judgment lives here; Jev's scores are a prior, not a verdict.

The dated incidents behind the rules below are in `references/lessons.md`; read it
only when a rule seems wrong for the case in front of you.

## Run

```bash
cd ~/projects && /opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python -m news.src.signal_digest.run run
```

With no arguments it collects the six default sources, filters with Jev, and
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
inputs (the same `--input` targets; an earlier run that lacked a built-in source
added since still counts, so a new default source does not split the day):

- "my digest", or a rerun with no qualifier: `union` (the default), the day's
  best-of as of now. Items already reported today are marked
  `PICKED EARLIER TODAY`; keep one only if it is still among the vital few, with
  "(earlier today)" on its heading and TL;DR bullet, and list new picks first.
- "anything new since earlier?": `--same-day new`, only items no earlier run
  today collected. `nothing_new: true` means every item was already seen; say so
  and stop. Otherwise "nothing new worth your time" is a good answer. "Seen" is
  not "reported": a pick may call itself a development only of something an
  earlier report printed (its picks and Near misses), never of an entry that
  merely sat in an earlier shortlist or discarded log; otherwise it carries the
  base fact as news.
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
- **Report it.** The report's `Collection:` sentence (its place is in the Report
  template; the lint checks it against the manifest) opens with every source's
  fetched count from the shortlist header, so a feed that quietly came back thin
  is visible even when nothing failed, then names every source that failed, was
  retried or was repaired and what happened, including a code fix's commit hash
  and the refetch result. When a whole feed is still missing after the refetch,
  say so in chat too: no report can cover what was never fetched.

A missing
`TYPESAFE_API_KEY` returns `ok: false` with the fix; tell the user and re-run
`filter --run-dir <id> --filter none`. If Reddit's session has expired, refresh
it with `python ~/projects/browser/src/refresh_state.py reddit.com`. If the AI
news `brief_date` or X Today's `fetched` is not today, say how old it is.

## Read selectively

Read `shortlist.md` and nothing else in bulk. Its top holds, in order: what was
picked on earlier days this week; a "Top investing candidates" index of the top
12 by invest composite plus every entry that names a holding as a stock (a
cashtag, or the bare ticker in a title) whatever its rank, each marked
`holding $INTC` and `VERIFY` where that applies, plus the best entry on each
most-posted cashtag (`$SPCX in 21 posts`, counted on a `Most-posted subjects:`
line above the index); then the survivors by Jev value, with VERIFY, UNCERTAIN
and UNSCORED items last. The keep line is per
track (the top 35 by invest and the top 35 by learn both pass) and an entry
naming a holding's ticker passes whatever its rank (`HOLDING`). The overall
order is `max(invest, learn)` and is not a cross-source comparison: AI-news
items carry full article bodies, so long Zhihu articles out-rank a two-line X
post on a holding by length alone. For investing, read the index, the
tickers and the most-posted subjects, not the rank; every investing pick
through 10-19 sat inside the index, and the one that did not (SpaceX's call,
10-20, entry #32) is why the index now carries the most-posted cashtags. Then:

- **One entry per story, where the pipeline can tell.** Retweets and quotes of
  one root post are folded under the story's best original post as `also:`
  lines (the heading says `story of N posts`), and the entry ranks by the
  story's best value, so a famous account's zero-like retweets no longer take
  slots of their own. Cite and `pick` the member whose words you use: the
  original for the fact, a quote for its own commentary; any member's id works.
  The fold sees only a shared root post, so a quote of the lab's announcement
  and a quote of the author's thread are two entries, and independent posts on
  one headline stay separate: count them as one candidate and cite the
  best-sourced one.
- **An event ranks by its post count as well as its best post.** An earnings
  call quoted line by line, a filing, a strike: each post carries one line and
  scores low on its own, so the best sits mid-list, most are discarded, and
  together they are the day's investing item. The `Most-posted subjects:` line
  counts cashtags named in ten or more of the run's items, kept or discarded,
  with how many were shortlisted and the best entry; a subject without a cashtag
  (SpaceX, Anthropic) you count yourself when the subject grep below returns a
  crowd. Read every post on such an event, discarded ones included, before
  judging it by any one entry's rank, and cite the one closest to the words.
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
- **A Reddit link post is scored on a stub.** Its body is the title and a
  `(link/media post) URL` line, so Jev rates it `uncertain` and it sits near the
  bottom (a lab's own research page has sat at #67 of 72). When the title or the
  linked domain names a lab, a holding or a paper, open the URL before dismissing
  it.
- **Quote tweets and retweets now arrive whole.** A retweet carries the full
  retweeted text, and a quote tweet ends with `[Quoting @author: …]`, one level
  deep. When that block is missing on a `quote` item, or a retweet still ends in
  "…", the lookup failed: open the URL before dismissing it when the author or a
  holding's ticker matters ("That's why I'm invested in $COHR" says nothing on
  its own). A quote post whose own words are a few words, or whose words Jev
  flagged as promo, is scored on the quoted post (its signals line says `scored
  on the quoted post`): the heading's author wrote the reaction, the quoted
  author the content. Judge, cite and attribute the quoted post; when the root
  was not collected, link the quote post's URL and say the claim reaches you
  through it. In a `--same-day new` run the root is often in an earlier run
  today, discarded or shortlisted and left out as seen: grep that run's logs
  for the quoted author's handle, open the root, and cite and attribute it in
  place of the wrapper (`pick` still takes the wrapper's id: only this run's
  items are accepted).
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

**A candidate that yields a ledger proposal is a pick when its goal has fewer
than two picks.** A watch item, premise evidence or claim evidence says the
user will log this fact, which is the regret test passed, and the facts the
proposal needs belong in a pick body, not in one Near-misses line. The slot
is the goal's: Investing with one pick takes it even when the day stands at
the cap, and the other goal's weaker pick (the one that yields no proposal,
else the lower-ranked) folds into its neighbour as one linked sentence or
moves to Near misses. Run the proposal step's routing while you pick, not
after the report is written: a Near-misses line that ends up with proposals
is the sign the pick was wrong. A Near-misses line carries a proposal only
when its goal already holds two picks.

**Read a figure against the holding it names before any premise.** A yield, a
lead time, a unit cap or a price on a holding's own product is a specific new
fact whatever its source: "a channel check, not a disclosure" sets the hedge and
the proposal's `source_type`, not whether it is a pick. Say which card it bears
on and which way first (substrate yields at Intel's packaging partners are
against INTC's foundry assumption), and only then whether it also confirms a
shared premise. Filed as "supports P2" it reads as confirmation and loses the
slot to a weaker item that looks like evidence against.

**An analyst's revision is measured against the firm's standing coverage, not
against its own prior.** A "43% cut" of a model you never saw is news only if
the new number sits below what the firm's main coverage and your own valuation
already assume. Spend the verification search on the standing estimates: a
regional model reconciled toward the house view is "not new news" and belongs
in Near misses. When the note is unseen, the heading says the figure reaches
you through coverage and states it against the standing numbers you found, not
against the old figure alone.

**Derive the period before you read a figure.** A cumulative disclosure (nine
months, year to date, a half) says nothing about the latest quarter until you
subtract the periods already reported; the implied quarter and its
quarter-on-quarter trend is the fact that bears on a holding, and the heading
carries that, not the headline total. Show the arithmetic in one clause. And a
second vendor restating a known condition (Dell on memory tightness, three days
after the quote) is a new voice, not a new fact: it earns a clause, not a pick.

**A holding's own officer restating a dated window is measured against the
standing window, not matched to it.** A sold-out, booked or lead-time window
("sold out through end-2027", "booked into FY2028") is the same fact as the
register's bullet only when its end date is unchanged and nothing beside it
has moved. The fact to test is whether the window moved: extended is for;
unchanged while the capacity it covers grows, or while a peer's window runs
longer (LITE "almost sold out for 2029" against COHR's end-2027), is mixed and
bears on the card's growth-fade or pricing assumption; shortened is against.
State the standing window, the new one and the peer's in one clause, and route
it as a watch item on the holding. A match by subject alone is the redundancy
check's false positive, and on a day with a free Investing slot it cost a pick.

**Collect the story's evidence before writing a pick.** Grep today's runs for
the company, ticker and Chinese name of the pick's subject, in `shortlist.md`
and `discarded.md` alike
(`grep -il 'CXMT\|长鑫\|\$MU' ~/projects/news/data/signal_digest/runs/<today>_*/{shortlist,discarded}.md`),
and fold in whatever adds a figure or contradicts the claim as one linked
sentence; a morning's discarded post has corrected an afternoon's pick before.
The pick's own source counts: a brief that lists several analyst notes carries
the counter-note beside the one you quote, and it goes into the pick as one
linked clause, never into silence.

Compare against the user's latest valuation when one exists:
`~/projects/stock_picker/data/valuations/<TICKER>/<date>.md` is the base model
and the authoritative figure; the `.whatif.md` beside it is a scenario file,
cite it only as such. Quote every figure with its file name and date.

**AI.** Three kinds of item qualify: an advance that changes what is possible or
what it costs (say what it does, how it works at a level a strong engineer can
follow, and what it enables or threatens; a benchmark bump doesn't qualify); a
durable shift in how the industry works; an unmet need a product could fill.
How long the point stays useful matters more than how new it is. A roundup is
not a shift: an aggregator's list of moves each more than two days old (blocks
the feeds carried weeks ago) restates known facts, and a durable shift earns its
pick only with a fact or a primary source of its own, which is what the pick
cites. When a pick is
best understood as a general concept (a bottleneck and where the overflow goes,
a feedback loop, payoff asymmetry), write it up that way: name the concept in one
sentence and link the forms it takes in this haul. That is a way of writing a
pick, not a separate quota.

**Primary sources.** Posts by people who run major AI, chip, cloud or internet
companies, and faithful reports of their words, are primary sources on strategy
and often the earliest public signal. The prefilter boosts them (list and
weights in `src/signal_digest/leaders.py`; the signals line shows `leader xN`).
Still judge by content: a prolific poster's jokes, politics and reposts count for
nothing.

Most of these people never post, so their talks (a podcast, a keynote, an
earnings call, a conference interview) used to reach the feeds only when a
followed account summarized one. The `leader_talks` source removes that
dependence: it searches X for the names in `leaders.py` (chip, supply-chain and
hyperscaler CEOs, English and Chinese) and brings the top posts of the last
three days, so a talk is collected whether or not the feeds carried it. Treat
its entries as the first thing to read in full. A CEO disclosing a demand mix,
a capacity figure, a lead time or next year's bottleneck is the earliest primary
source on where the build-out's constraints are, which serves both goals at once
and usually is the day's most valuable item. Such a talk still competes for the
three slots rather than getting a slot of its own: an uncapped slot would fill
with talks that have nothing new (a founding anecdote, a tour, a politics
remark) and the reader would stop trusting it. The figure earns the slot, not
the name, and a talk with a new figure beats any commentator's take for one.
When it still loses, a Near-misses line carries the figure in one sentence, so
a bottleneck disclosure never vanishes. The same talk arrives as several posts
(an outlet, a thread, a Chinese summary, quote-tweets): count them as one
candidate and cite the one closest to the words. A talk the search brings in
from two or three days back that no earlier run carried is new to the user,
whatever its date.

A leader's remark on a story already picked is a development in two
cases: it discloses a figure, a decision or guidance of the leader's own
company, or the speaker's own stake changes what the known facts mean (the
lender behind a deal doubting its financing). The same words from a commentator
are a new voice; from a participant they move the story. When the stake is the
point, the heading says so ("the lender behind Anthropic's chips doubts the
financing"), not "two CEOs named the weak links".

**Engagement** measures what the crowd already knows. Use it as context, never as
the reason to pick.

**Verify before you trust.** For every investing pick, and every VERIFY item that
would matter if true, spend one web search to confirm the claim and read what
was actually said. Headline accounts (Polymarket, zerohedge) routinely reframe;
a verified-but-reframed claim may move from investing to AI or drop out. State
the result in one sentence with the primary source linked. The heading and the
TL;DR then carry what the primary source says, not the feed post's paraphrase.

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
- Whenever AI has fewer than two picks, a Near-misses line likewise names the
  best AI candidate not picked and why it lost: the first `learn` entry from the
  top of the shortlist you did not pick, with its rank. A full day's cap is a
  reason it lost, not a reason to leave it out; when Near misses is full, it
  displaces the weakest line (a ticker the user does not hold, a known price
  curve), not the other way round.
- **An event at a holding itself is named whether or not it is picked.** An
  index entry marked `holding` that reports something happening to the company
  (a lawsuit, a contract, guidance, a price change, a management change, a
  product launch or a design win) gets the one search every VERIFY item gets,
  then a pick, a clause inside a pick, or a Near-misses line with the verdict.
  An entry marked with several holdings is an event at each of them: a
  holding's new product that pulls on a component another holding sells out of
  (Marvell's 32-laser memory appliance against Coherent's and Lumentum's InP)
  is named for both sides. A ticker list, a selloff roll call or a sector read
  is not an event and needs nothing; the lint warns only about VERIFY items, so
  walk the `holding` entries yourself.
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
  first use. A time window ("since early 2025") stays with the figure the source
  attaches it to: when two figures sit together, check which one is dated before
  carrying the window. The reader is a strong engineer, not a finance specialist.
- A vendor's superlative or ranking ("the most capable US open-weight model") is
  the vendor's claim until an independent benchmark confirms it: attribute it
  ("Meta calls it …"), in the TL;DR too, or drop it.
- A quotation links the document that contains the words (the slides, not the
  blog post beside them). A quote that reaches you through coverage (a Chinese
  write-up of an English talk) is attributed to the person only after you find it
  in the primary; otherwise attribute it to the coverage.
- **Write in English** whatever the sources' language. Quote Chinese verbatim only
  where the wording carries something a translation loses (a coined phrase, a
  quote being weighed), followed by an English gloss.
- In chat, reply with the TL;DR bullets, the report path and the number of log
  proposals. Don't paste the report.

## Propose log entries for the portfolio

Picks are also evidence for the user's research logs in `stock_picker`: a
**watch item** per holding (news a thesis card's next print must settle), the
**portfolio premise register**, and the **AI industry claims ledger** (revisable claims
about the AI build-out and its adoption, `~/notes/wiki/Investment/Micro fundamentals/AI
Industry Claims/`). This skill only *proposes* entries and never writes
any of them, because nobody reviews an unattended run before it lands and a framing can
turn out wrong the same day. The user applies the ones they approve with
`/portfolio-brief log the digest proposals`.

`PB` below is `/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/projects/stock_picker/skills/portfolio-brief/portfolio_brief.py`.

1. **Candidates**: each investing pick, each Near-misses line on a holding or a
   premise, and each pick or Near-misses line on either goal that states an industry-level
   fact about the AI build-out or its adoption. A watch item goes to any ticker with a
   baseline card in the vault, not only to `reader.holdings`: for every company outside
   the holdings whose own fact a pick reports (Amazon on AWS being sold out; both vendors
   of a two-vendor launch, so AWS's TorchNeuron beside Google's TorchTPU), check for its card
   (`ls ~/notes/wiki/Investment/Micro\ fundamentals/*/<TICKER>/<TICKER>\ fundamentals.md`)
   and, when one exists, route the fact to it exactly as to a holding, reading its card with
   `PB status --tickers <TICKER> --compact`; when none exists, the `skipped` entry says
   "no baseline card". The routing rule (one holding's card → watch
   item, or a `watch_update` when the fact is a new number or confirmation on one of the
   ticker's open items; a shared premise → premise evidence; a ledger claim → claim evidence; every one
   that applies), the significance bar and the fact-level redundancy check are
   owned by `portfolio-brief` Step 5 (`~/projects/stock_picker/skills/portfolio-brief/SKILL.md`);
   apply them as written there. The formats are in `~/projects/stock_picker/docs/attention-layer.md`
   (*Watch items*, *Premise register*, *Industry claims ledger*, *Proposal files*). Zero
   proposals is a normal run.
2. **Read the current state first.** `PB status --compact` gives each holding's
   `open_watch` and `baseline.path`; read that baseline's `## Thesis card` so `bears_on`
   names a specific assumption, trigger, scenario or premise and `test_at` names the next
   print (its `Next re-test`). A fact that develops an open item (the stalled deal has
   closed; the rumoured number is now confirmed) is a `watch_update` on it, not a second
   item and not a `skipped` entry asking the user to amend the item by hand. Read each touched premise's **Claim** and evidence in the
   register, its newest bullets most carefully: the user's own same-day entries land there
   too (an earnings-call summary arrives the same afternoon), and a fact a bullet already
   records, whoever wrote it, is not proposed again; the dry run's `already_present` catches
   only an identical entry, not a repeated fact. A dated window restated by the holding's own
   officer is a repeated fact only when its end date is unchanged and nothing beside it moved
   (the rule under *Pick the vital few*); otherwise it is proposed with the comparison in `item`. For claim evidence, read the claims index's *Registry* and the candidate claim's
   `Claim`, `Refuted if` and newest bullets: the fact must bear on that `Claim` line, and one
   the claim already records from another outlet is not proposed. Propose `status` and
   `status_reason` only when the evidence moves the claim's status, and never a new claim (a
   fact no claim covers goes in `skipped` as "no ledger claim; candidate new claim"). Read
   any `proposed_log.json` from today's earlier runs: what they proposed is
   not proposed again, approved or not.
3. **Write `proposed_log.json`** into the run directory: `run_id`, `proposals` (each with
   `kind`, `pick` as `invest:<item id>`, `ai:<item id>` or `near-miss`, and `args`), and `skipped` (one
   `{what, why}` per candidate declined). A `watch_update`'s `args` are `ticker`, `match` (a
   substring of the open item's title that picks only it), `direction` (`for`, `against` or
   `mixed` relative to the thesis; `mixed` when the news both deepens and eases the item's
   concern) and `update` (the new fact in one line of at most 50 words with its link; the
   command writes the `<date> · <direction>:` prefix itself). Watch-item, register and
   ledger fields follow *Writing for the reader* in `attention-layer.md`; the lint refuses an
   over-limit field. The pick's verification sentence sets
   `source_type` (for claim evidence, the ledger's set: `news`, `sell-side`, `trade blog`,
   `investor post`, `forum`, …, with the caveat in `qualifier`) and the caveats that go into
   `item`, `claim` or `evidence`. A caveat that the evidence falls short of the claim's own
   test ("operating income, not cash flow" against a claim worded on cash flow) is itself a
   claim about the source: look for the test's measure in the document first (the S-1's
   cash-flow statement), and when it is there, the evidence states it and the caveat goes.
   `date` is the evidence's
   date. `item`, `claim` and `evidence` carry only facts the report states or a page you opened for
   this run says; a fact you remember (what the CEO said at the last call) stays out until
   you open and link where it was said. Link every source: a watch item's `source` and an evidence entry's `links` each need
   the URL of every post or article named (and the primary document's when one exists);
   the dry run in step 4 rejects an outlet name or run id alone. Where `item`, `claim` or `evidence`
   attributes a fact, write the attribution as the link ("per [Carrio](url) only").
4. **Validate**: `PB apply-proposals <run dir>/proposed_log.json --dry-run`. Fix every
   failed proposal; one that comes back `already_present` is logged already, so drop it.
5. **Append `## Proposed log`** at the end of `report.md`: one line per proposal in file
   order, `N. watch TICKER · <direction> — <title>`, `N. premise Pn · <direction> — <claim
   in a dozen words>`, `N. update TICKER · <the open item's title> — <the new fact in a dozen
   words>` or `N. claim <ID> · <direction> — <evidence in a dozen words>` (add
   `· status → <new>` when it proposes one), or `None.` The numbers are what the user approves by.

## Check the report, then log the picks

Run the lint before logging and fix every error it reports:

```bash
… lint --run-dir <run id>
```

It checks the word budget, the pick cap, the TL;DR bullet and pick-body lengths,
the TL;DR and `Sources:` structure, the first Near-misses line, the `Collection:`
line against the manifest (every source's fetched count, and every failed,
retried or repaired source, must be named), every link label against its URL (a label saying "via Coinpaper" on a kucoin.com URL is the
kind of slip it exists for), and `proposed_log.json`: its count against the
`## Proposed log` lines, and every proposal against portfolio-brief's log-entry
rules (stock_picker's `log_entry_rules`, the rules step 4's dry run applies), so a
proposal the user cannot apply as written is an error here too. It warns about every VERIFY item that names a
holding and appears nowhere in the report, by author and id: decide whether it
is an event at the holding, and if so name it. `lookup_links` lists every link that is
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
the accounts that do. Picks whose `keep_reason` is `uncertain`, `verify`, `holding` or
`dropped: …` are what Jev's ranking alone would have missed; if they pile up, the
weights in `src/signal_digest/jev_filter.py` need retuning.

## Where things live

- Code: `~/projects/news/src/signal_digest/` (`run.py` CLI, `sources.py`
  adapters, `jev_filter.py` questions, weights and the per-track keep line,
  `render.py` the shortlist, its story folding, the investing index and the
  most-posted subjects line, `lint.py` the report
  checks, `profile.py` reader context, `leaders.py` the leader handles and
  the names, words and window behind the `leader_talks` search, `run_daily.py`
  the 9:00 and 15:45 LaunchAgent entry point).
- Data: `~/projects/news/data/signal_digest/runs/<run id>/` (deleted after
  10 days; keep it that long so a week-later review can compare report.md against the
  items, scores and raw snapshots it came from; `collect.log` there holds the
  collectors' stderr, tracebacks included), `picks.jsonl` (the memory that
  drives `PICKED <date>` markers),
  `seen_counts.json`; each run's `proposed_log.json` holds its proposals for the
  stock_picker logs.
- The reader profile is rebuilt every run from `stock_picker/data/portfolio.csv`,
  `data/ticker.csv` and the premise register; `--profile FILE` swaps it.

---
name: signal-digest-review
description: Daily quality review of the previous day's signal-digest runs during a hill-climbing period. Reads each run's report, shortlist, discarded log and pick log, scores the picks and the log proposals against the user's two goals (investment return with controlled risk; AI technology and industry trends for learning and startup ideas), hunts for misses, spot-checks one claim, checks pipeline health, and writes a short scorecard plus at most one improvement suggestion to a running list. Use when the user asks to "review yesterday's digest", "score the signal digest", "how did the digest do", or when the signal-digest-review LaunchAgent runs it unattended. Does not edit the signal-digest skill; changes are batched by the user.
---

# signal-digest-review

A reviewer of the `signal-digest` skill's daily output. The digest's goal is
in `~/skills/signal-digest/SKILL.md` under "Goal"; read that section first and
judge against it, not against your own taste. The point of the review period
(about 10 days) is to learn whether the skill finds the vital few items and
where it fails, so the user can change it in batches with evidence.

## Inputs

The runner (`news.src.signal_digest.review_daily`) names the date and the run
directories to review, each with `report.md`, `shortlist.md`, `discarded.md`,
`manifest.json`, `scored.jsonl` and, since 2026-10-19, `proposed_log.json`. Read, in this order and nothing else in bulk:

1. `report.md` of each run.
2. The first 30 items of each `shortlist.md` and the first 10 lines of each
   `discarded.md`, looking for anything that beats a pick.
3. `manifest.json` for source errors, counts, and the picks.
4. `~/projects/news/data/signal_digest/reviews/feedback.md` if it exists: the
   user's own marks on earlier picks (`[x]` useful, `[-]` not). Their judgment
   outranks yours; when a mark disagrees with your score, say so and defer.
5. Each run's `proposed_log.json`, and which of its proposals the user applied: a watch
   item's title in `~/notes/wiki/Investment/Investment system/Watch Items.md`, or an
   evidence bullet's date and source in `Portfolio Premise Register.md` beside it. An
   applied proposal is the user's approval and outranks your score, like a `[x]` mark.
6. Earlier scorecards in `reviews/` only to check whether a finding repeats.

Open an item's full content through its `ref` or URL only when a decision
turns on it. One web search per report for the spot-check, no more.

## Checklist

Answer every point in one or two sentences, with the item linked.

1. **Picks vs goal.** For each pick: would the user regret not knowing this?
   Did it bear on a holding or premise, or change what is possible or what it
   costs? A sentiment reading or a benchmark bump scores low.
2. **Misses.** The best unpicked item in the shortlist top 30 and discarded top
   10, and whether it should have beaten a pick. Items on a holding count double.
3. **Repeats and developments.** For any pick marked as a development of an
   earlier story, was the "what changed" real, or a new voice on known facts?
   A speaker whose own stake changes what the facts mean (the lender behind a
   deal doubting its financing) is a development, not a new voice; score the
   write-up on whether it led with that stake.
4. **Spot-check.** One factual claim per report, against a primary source. Say
   confirmed, reframed or wrong.
5. **Format.** Run the lint on each report and quote its errors and the
   warnings you agree with:
   `cd ~/projects && /opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python -m news.src.signal_digest.run lint --run-dir <run id>`.
   An error costs the Format point. Then by eye: the TL;DR standing alone,
   and Near misses naming the best unpicked investing item when Investing had
   fewer than two picks.
6. **Pipeline health.** Source errors and repairs (`attempts`, `repair`,
   `repair_failed` and `refetch` in the manifest's `collect` block, with the
   traceback in the run's `collect.log`; the report's `Collection:` line must
   match them, and a repair that worked is not a pipeline fault), a source whose
   fetched count on that line is far below its usual, stale brief
   or X Today, AI-news items with no body, retweets still ending in "…", and the Jev rank and
   `keep_reason` of each pick (from `scored.jsonl`; a pick below the keep line
   is a filter miss worth noting; the line is per track since 2026-10-12, so
   compare an investing pick's `invest` rank, not its overall rank).
7. **Log proposals.** The rules are the routing rule, significance bar and redundancy
   check in `~/projects/stock_picker/skills/portfolio-brief/SKILL.md` Step 5; judge against
   those, not your own taste. Per run: is each proposal routed right (one holding's card →
   watch item, a shared premise → premise evidence, the right premise, `for`/`against`
   relative to its **Claim** line), above the bar, not a re-proposal of an earlier run's,
   and framed as the verified primary source says rather than the feed post? A pick on a
   holding or premise with neither a proposal nor a `skipped` entry is a miss. Run
   `/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/projects/stock_picker/skills/portfolio-brief/portfolio_brief.py apply-proposals <run dir>/proposed_log.json --dry-run`;
   a failed proposal costs the point. Never apply a proposal yourself.
8. **One suggestion at most.** The single change with the best evidence from
   this day, appended to `reviews/suggestions.md` as one line with the date and
   the evidence link. If the day shows nothing new, append nothing.

## Output

Write `~/projects/news/data/signal_digest/reviews/<YYYY-MM-DD>.md`:

```markdown
# Digest review — <date> (runs: <ids>)

Score: Investing <0-2> · AI <0-2> · Misses <0-2> · Format <0-2> · Pipeline <0-2> → <total>/10 · Proposals <0-2, or n/a>

## Picks
- <run id> · <pick title> — <score and one-sentence why> ([source](<link>))

## Misses
- <item> — <why it should have beaten a pick, or "none found">

## Spot-check
- <claim> — confirmed / reframed / wrong ([primary](<link>))

## Pipeline
- <errors, stale sources, stubs, Jev ranks of picks>

## Proposals
- <run id> · <N. proposal> — <routed right / over the bar / duplicate / misframed; applied by the user or not>

## Suggestion
<one line, or "none today">
```

Scores: 2 = met the goal, 1 = partly, 0 = failed; `Misses` 2 means none found.
`Proposals` sits outside the /10 total so scorecards before and after 2026-10-19 stay
comparable; it is `n/a` for a run with no `proposed_log.json`, and 2 for a correct
"None." (nothing on a holding or premise cleared the bar).
Every score below 2 names its reason in the matching section, in one clause
("Format 1: TL;DR bullet of three sentences"); an unexplained point lost cannot
be acted on.
Under 300 words. Also append the day's picks to `reviews/feedback.md` as
`- [ ] <date> <run id> · <title> (<link>)` when they are not there yet, so the
user can mark them. Do not edit `~/skills/signal-digest/SKILL.md` or the
pipeline; the user applies changes in batches on about day 5 and day 10.

In chat, reply with the score line and the suggestion, plus the file path.

# signal-digest: the dated incidents behind the rules

Each rule in SKILL.md that was added or sharpened after a daily review keeps its evidence
here, so the skill stays short and the reasoning stays checkable. Read this only when a rule
seems wrong for the case in front of you. Newest last.

- **2026-10-12 · verify, then let the primary source write the heading.** A post's "memory
  is the weak link" became the heading; the source said financing.
- **2026-10-12 · a leader's stake is a development.** The funding story had two days of
  issuance data and bank forecasts behind it; then Broadcom's CEO, the lender behind
  Anthropic's chip leases, said capital could be the constraint. From a commentator that is
  a new voice; from the lender it is the story moving from observers to a participant, and
  the heading should say so ("the lender behind Anthropic's chips doubts the financing"),
  not "two CEOs named the weak links".
- **2026-10-12 · value rank is not a cross-source comparison.** Long Zhihu articles took
  ranks 1–5 because AI-news items carry full bodies; a two-line X post on a holding sat at
  rank 40. Left as is, because the articles that get picked are long too.
- **2026-10-14 15:45 · one entry per story.** Six of the top 14 entries were zero-like
  retweets of one Meta paper, and six of the top 30 were independent posts on Anthropic's
  $16.8B quarter. The shortlist now folds the first kind; the second is still yours to count
  as one candidate.
- **2026-10-15 · a leader's figure is usually the day's most valuable item.** Huang on Bg2:
  frontier labs are a quarter to a third of demand, gear per gigawatt went from $18B to over
  $40B, land and power limit next year.
- **2026-10-15 · attribute vendor superlatives.** The TL;DR stated Meta's claim about Muse
  Spark Open as fact.
- **2026-10-15 15:45 · an event at a holding is named whether or not it is picked.** Tower's
  fraud suit against Intel sat in the index as a VERIFY item and the report never mentioned
  it, while two unsourced MU rumours got lines. The lint now warns about every unnamed
  VERIFY item on a holding.
- **2026-10-16 09:00 · holdings pass the keep line whatever their rank.** On a 200-item
  morning the invest line sat at 0.44 and a $MU post on CXMT's flat Q3 fell under it at
  0.42, the fact the afternoon's MU pick needed. Entries naming a holding's ticker now pass
  regardless (`HOLDING`).
- **2026-10-16 15:45 · derive the quarter from a cumulative figure.** CXMT's nine-month
  profit was read as a cash pile when Q1 and Q2 implied Q3 up 1–4% QoQ on revenue up
  15–20%, the fact that bore on MU. The morning's discarded "Q3 almost flat QoQ" post
  belonged inside that pick and would have corrected it, which is why the skill says to
  grep today's runs for the subject before writing.
- **2026-10-16 15:45 · judge a thin quote wrapper on the quoted post.** "Sell everything"
  quoting a report of Anthropic's 80–90% automation projection was the day's AI pick; the
  wrapper had been dropped as promo at 0.116 and the root was never collected.
- **2026-10-17 15:45 · "seen" is not "reported".** "This morning's run carried the release"
  opened the DeepSeek pick, though the 09:00 report never named DeepSeek (shortlist #41 and
  #46). The same afternoon the pick went to "Notice the cost column" while @PawelHuryn's
  post with the 105-bug data sat in the 09:00 `discarded.md` at 0.263: in a `--same-day new`
  run, find the root in the earlier run and cite it in place of the wrapper.
- **2026-10-18 · propose log entries, never write them.** The 09:00 AMD pick read a Morgan
  Stanley model reconciliation as a 43% cut; the explanation surfaced that afternoon. An
  unattended run's framing can be wrong the same day, so the user applies proposals.
- **2026-10-18 09:00 · an analyst's revision is measured against the standing coverage.**
  The AMD pick read Morgan Stanley's "43% cut" (14.1M → 8.0M GPUs over 2026–30, note unseen)
  as evidence against the bull case. The firm's main US coverage already modelled 672k / 1.1M /
  1.4M for 2026–28; the cut was MS Asia reconciling an inflated model toward that view, so
  "not new news". The same Neo Reports brief carried KeyBanc raising AMD's AI GPU revenue to
  about $16.5B, and the pick left it out.
- **2026-10-18 09:00 · read a figure against the holding first.** KeyBanc's EMIB-T substrate
  yields (50–60% at Ibiden, 20–30% at Unimicron; invest #4) got a Near-misses line as "channel
  checks, not an Intel disclosure, support P2", while the AMD reconciliation (invest #12) took
  the slot. The user logged the yields as an INTC watch item against the foundry assumption,
  plus a P2 bullet.
- **2026-10-18 09:00 · a Reddit link post is scored on a stub.** The day's AI pick, Anthropic's
  employment paper, sat at #67 of 72 as `uncertain` (0.239) because the Reddit post's body was
  the link line alone.
- **2026-10-18 09:00 · a time window stays with its figure.** "Since early 2025" was attached
  to the junior share of technical hires (27% → 9%) when the source dates the junior share of
  employees (21% → 14%).
- **2026-10-18 15:45 · a roundup is not a shift.** The AI pick on incumbents blocking agents
  collected blocks known since September through a secondary aggregator (learn #30, 0.325).
- **2026-10-19 09:00 · the lint checks the proposals.** Two of three proposals named outlets
  and the run id in `source` with no URL, so `apply-proposals` refused them and the user applied
  them by hand; the link rule and the dry-run step entered the skill at 10:16 that day, and the
  lint now checks them against the same rules (it imports stock_picker's `log_entry_rules`)
  so the gate does not depend on the agent remembering step 4.
  The INTC proposal also carried "a change from July" that neither the report nor the
  @BacklogAlpha post said; `item` and `claim` now carry only what the report or an opened page
  says.
- **2026-10-20 09:00 · a watch item is a pick when there is room.** Micron's Taoyuan union
  strike (index #13) stayed a Near-misses line under one investing pick, yet it earned a
  300-word MU watch-item proposal against the card's margin line, and the user applied it
  while skipping the pick's P2 bullet. The facts the proposal needed belonged in a pick body.
- **2026-10-20 15:45 · an event ranks by its post count as well as its best post.** SpaceX's
  Q3 call arrived as 21 posts naming $SPCX out of 126 items, each quoting one line: the best
  ranked #21 by value, the pick (the capex guide doubled to $35–40B, 10 GW more in 2027)
  sat at #32 outside the index, and a dozen one-line quotes were discarded at low value.
  The shortlist now counts cashtags in ten or more items on a `Most-posted subjects:` line
  and lists each one's best entry in the index.
- **2026-10-20 15:45 · a fact the register already records is not proposed.** The P2
  proposal (SpaceX rents above $50/W, payback under a year) repeated the user's own
  same-day SPCX bullet from the earnings-call summary, which sat directly above it in P2's
  evidence; the dry run passed it because the entry was not identical.
- **2026-10-21 15:45 · a candidate that yields a ledger proposal is a pick.** Lam's call
  (2027 equipment spending above $200B, DRAM growing fastest, clean rooms still limiting; entry
  #26) stayed a Near-misses line under one investing pick and two AI picks, yet it yielded the
  run's only two proposals (CHIP-4 against, MEM-1 for), the user applied both and opened claim
  EQP-1 on it. The 10-20 rule covered watch items on a day under the cap; claim evidence on a
  day at the cap slipped past it. The rule now covers every proposal kind and lets the goal with
  one pick take the slot from the other goal's weaker pick.
- **2026-10-22 09:00 · a restated window is measured by its end date.** Coherent's CTO said InP
  laser capacity is "essentially sold out through the end of 2027" (index #12, holding COHR).
  The proposal step matched it to the register's 2026-08-12 "FY2027 fully booked" bullet and
  skipped it as redundant, in both runs, while Investing had a free slot each time. The user
  logged it the same day as a mixed COHR watch item: the window had not extended into 2028
  while LITE's CEO says LITE is almost sold out for 2029, which bears on the card's assumption
  that growth fades as the 2027-28 capacity lands. The fact was the unmoved end date, not the
  sold-out condition.
- **2026-10-23 09:00 · a holding's product launch is an event at the holding.** Marvell's
  Celestial AI memory appliance, 32 external lasers per box (index #10, marked `holding $LITE
  $COHR $MRVL`), was named nowhere in the report: a new product pulling on InP capacity that
  COHR and LITE say is sold out. The event list named lawsuits, contracts, guidance, prices and
  management changes, and the lint warns only about VERIFY items.
- **2026-10-23 15:45 · a watch item goes to any ticker with a card.** Jassy's "AWS 2027
  largely sold out" pick yielded P2, MEM-1 and GEN-1 evidence and no AMZN entry or skip, because
  the proposal step read only `reader.holdings`; the vault holds an AMZN baseline and the user
  wrote the watch item the same day.
- **2026-10-24 · vendor release feeds, tried and withdrawn.** Google's TorchTPU and AWS's
  TorchNeuron (10-20) reached no run until a Zhihu write-up on 10-24. A `vendor_releases` RSS
  source (eleven feeds from eight hand-picked vendors) ran once, 20261025_1545, and was removed the
  same day: a short vendor list chosen by which blogs had a working feed is arbitrary, and the
  source needs a systematic list before it comes back. The same pick's proposals had no AMZN entry
  for TorchNeuron: the any-ticker-with-a-card rule now names every company whose own fact a pick
  reports.
- **2026-10-25 15:45 · an added source must not split the day.** The first run with a new
  default source matched no same-day run (the signature compared source lists for equality), so
  `--same-day new` judged the morning's 58 items as new and the agent set them aside by hand. The
  signature now accepts an earlier run whose sources are a subset of this run's.
- **2026-10-25 15:45 · a development of an open item is an update, not a skip.** Musk said the
  stalled $40B GPU debt had closed; NVDA already had the 10-23 "SPV stalls on pricing" item, so
  the run could only skip it and ask for a hand amendment, which never came while its three other
  proposals were applied. A `watch_update` proposal (`update-ticker-watch-item`) now appends the
  dated sentence portfolio-brief's redundancy check already called for.
- **2026-10-26 15:45 · the best AI candidate needs a Near-misses line too.** Anthropic's "How
  the Claude Code team does code review" (shortlist #3, learn; PRs doubled, reverts down 40%)
  lost to the Cohere pick under a full three-pick day and appeared nowhere, while Near misses
  spent lines on Microsoft's buyout (not held) and a model's price step. Only Investing had a
  named-runner-up rule.
- **2026-10-26 09:00 · a caveat about the source must be checked against the source.** GEN-8's
  claim evidence from Anthropic's S-1 carried the qualifier "operating income, not cash flow"
  against the claim's "cash-flow negative", while the S-1 reports H1 operating cash flow of
  +$3.93B, the claim's own test.
- **2026-10-26 · a primary-document weight in Jev, replayed and rejected.** The review proposed
  boosting company documents (Meta's FWP at invest #24, Celestica's 2027 outlook #50 of 64). A
  Noul question ("figures from a company's own filing, results release, guidance or announced
  deal") asked of all 3,455 items in the 21 stored runs (10-17 to 10-27) answered about 0.95 for
  Carrio's quote posts and every S-1 commentary thread alike (Meta's FWP post 0.78, Celestica
  0.63). Multiplying invest by 1 + b·P moved the 26 investing picks down, not up: mean rank 13.5
  at b = 0 against 13.7, 14.4 and 15.1 at b = 0.3, 0.5 and 1.0, and 16 → 14 inside the top-12
  index at 0.5. A company document is read off the shortlist (the index's holding and
  most-posted entries, the subject grep), not ranked up by Jev.

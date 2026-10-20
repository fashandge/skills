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

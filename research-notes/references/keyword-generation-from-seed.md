# Generating Keywords from a Seed Note or Wiki

If the user provides a seed note, wiki article, or report on the topic (or if one exists in the vault), read it first to extract candidate keywords before searching. Score every candidate against a single test: **"if a note contains this term, is it almost certainly about the topic?"** If no, drop it — high recall on the wrong topic is worse than low recall on the right one.

Pick keywords in this priority order. Local search is cheap, so **err on the side of more queries — ~15–20 strong terms is fine, even more if the topic is broad**. The real cost isn't query count, it's letting *weak* terms in: a single noisy keyword can flood the union with off-topic notes. Quantity is free; precision is not.

1. **Topic name + direct synonyms (both languages)** — the canonical labels for the topic itself (光通信 / 光互连 / 光互联 / optical communications / optical networking). Always include both Chinese and English.
2. **Core technical concepts unique to the topic** — terms-of-art whose meaning is the topic (CPO, LPO/NPO, silicon photonics, 硅光, 光模块, InP, EML, CW laser, FAU, Photonics-SOI). A note using these is almost certainly on-topic.
3. **Sub-segments / adjacent technologies that drive the topic** — narrower than the topic but still topic-defining (1.6T, ZR+, DCI for optical; HBM, NAND for storage). Include only if they're rarely used outside the topic.
4. **For investment topics: tickers and primary public companies in the topic** — the small set of stocks the topic *is about* (LITE, COHR, CIEN, GLW, AAOI, TSEM, AXTI, FN for optical). A note about LITE is a note about optical comms.
5. **Chinese-market peers and component vendors**, if the vault has Chinese-language coverage (中际旭创, 新易盛, Soitec/SLOIY).

## What to Exclude

These inflate the union with off-topic notes:

- **Research-shop / analyst / publisher names** (Bernstein, SemiAnalysis, Goldman Sachs, LightCounting, fpeking, lionhill). They surface notes that *cite* the source on any topic, not notes about your topic. The seed note often lists them in a "References" section — that's not a green light to query them.
- **Generic macro / financial terms** (hyperscaler capex, AI infrastructure, capex, valuation, P/E). These match thousands of unrelated notes.
- **Cross-cutting tech terms that span many topics** (AI, GPU, datacenter, NVIDIA, NVLink moat — unless the topic *is* NVIDIA). NVDA and AVGO are platform companies that show up in every AI-infra note; querying them pulls in everything.
- **Trading-tactic terms** (均线, EMA, breakout, support, resistance, PEG screen) — these match chart-commentary notes that happen to mention a topic ticker but aren't about the topic.
- **Generic verbs and structure words** from the seed (报告, 投资, 分析, 风险, report, analysis, investment).

When in doubt, run a candidate query with `--limit 5` and skim the top results: if 2+ of them clearly aren't about the topic, drop the keyword from the plan.

## Building the Query Plan

Build a query list from the kept terms, then run them as separate AND queries. Start with the broadest single-term queries first (priorities 1–2), then narrow with 2-term combinations only if a single-term query returns too much.

**Example query plan for "光通信" (optical communications):**

```bash
# Broad single-term sweeps (run separately, dedupe results)
notes-search search "光通信"
notes-search search "光互连"
notes-search search "optical communications"
notes-search search "silicon photonics"
notes-search search "硅光"
notes-search search "CPO"

# Narrowing with 2-term AND (only if single-term returns too much)
notes-search search "光通信 CPO"      # mixed lang, fine
notes-search search "硅光 InP"         # mixed lang, fine
notes-search search "CPO CW laser"    # English-only
notes-search search "光模块 1.6T"      # Chinese-only

# Ticker-scoped
notes-search search "LITE"
notes-search search "TSEM PH18"
```

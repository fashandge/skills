---
name: x-market-news-summary
description: Fetch recent tweets from Twitter sources and analyze market implications for SPY/QQQ
triggers:
  - x market news
  - x market news summary
  - x news summary
  - twitter news summary
---

# X Market News Summary

Fetch and analyze recent tweets from Twitter/X sources to summarize market-moving news and implications for SPY/QQQ.

## Execution Discipline

- During normal execution, do not inspect `src/x_market_news/*.py`.
- Treat the local scripts and existing summary/cache files as the operational interface.
- Only read source code if a required command fails, returns unexpected output, or the file/state layout does not match these instructions.
- During normal runs with new tweets, do not read the prior summary markdown file.
- Only read the prior summary file for the zero-new-tweets fallback or if command/file output is inconsistent and you need to debug.

## Usage

```
/x-market-news-summary [page_size] [--sources handle1,handle2,...] [--mode full|incremental]
```

- `page_size`: Page size for xreach pagination (default: 50). The fetcher scans by date/cutoff boundary with an internal 10-page safety cap.
- `--sources`: Twitter handles separated by comma (default: unusual_whales,wallstengine)
- `--mode`: Optional override. If omitted, infer `full` vs `incremental` by checking whether a same-day `x_market_news_YYYYMMDD_HHMM.md` file already exists.

## Instructions

At skill start:
- Determine the current local time in `America/Los_Angeles`.
- Use that local time for the output filename and `Generated HH:MM`.
- Infer mode if `--mode` is omitted:
  - no same-day summary file -> `full`
  - existing same-day summary file -> `incremental`

### Full Mode

1. **Fetch tweets** from each source using the preprocessor script:
   ```bash
   /opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/projects/news/src/x_market_news/fetch.py [page_size] --account [handle] --update-cache
   ```

   Run this for each handle in `--sources`. The `--update-cache` flag saves tweets for later incremental runs.
   The fetcher keeps paging until it reaches older-than-today tweets or the internal page cap.
   For `wallstengine`, source-specific filtering is applied before cache writes.

2. **Load cache and write summary**:
   - Read today's cache files from `~/projects/news/data/x_market_news/cache/tweets/`.
   - Build the markdown summary directly from those cache files.
   - Do not inspect `src/x_market_news/*.py` unless the fetch command fails or the cache files are missing/unexpected.

### Incremental Mode

1. **Fetch only new tweets** since the last summary:
   ```bash
   /opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python ~/projects/news/src/x_market_news/fetch.py [page_size] --account [handle] --mode incremental --update-cache
   ```

   `fetch.py` will infer the incremental cutoff from today's latest summary filename when `--after-time` is omitted. Keep `--after-time` available only for manual override/debugging.
   The fetcher keeps paging until it reaches that cutoff or the internal page cap.
   For `wallstengine`, source-specific filtering is applied before cache writes.

2. **Load all cached tweets** for the combined summary:
   ```bash
   cat ~/projects/news/data/x_market_news/cache/tweets/[handle]_[YYYYMMDD].jsonl
   ```

3. **Use different source sets for the two sections**:
   - `## New Developments` must use only the newly fetched tweets from the current incremental window.
   - `## Combined Summary for Today` must use all cached tweets for today across all configured sources.
   - Do not build the combined section by lightly editing the prior markdown summary.
   - In normal incremental runs with new tweets, do not read the prior summary markdown at all.
   - Only use the prior summary in the zero-new-tweets fallback, where the combined section is intentionally copied forward.
   - Do not inspect `src/x_market_news/*.py` during this flow unless the fetch command, cache read, or summary file lookup fails.

### Analysis (both modes)

1. **Build a tweet-citation map** before writing. Each cache line has `{id, text, t, v}`. The tweet URL is `https://x.com/{handle}/status/{id}`. Every material claim in the summary must cite at least one tweet via a markdown link `([@x](url))` where `x` is a 1-letter abbreviation of the handle (e.g. `@u` for `@unusual_whales`, `@f` for `@FirstSquawk`). If two configured sources share a first letter, use the shortest unambiguous prefix (`@un`, `@us`). The Sources section at the bottom expands these to the full handle. Combine multiple tweets only when the claim genuinely aggregates them.

2. **Categorize** tweets into themes (geopolitics, Fed/rates, Big Tech/AI, economic data, political news, earnings, options flow). Pick 3–5 themes total — the most market-moving ones, not one per category.

## Key Principles

1. **Cite sources inline.** Every material claim, statistic, level, or named event ends with `([@x](url))` linking to the tweet, where `@x` is the 1-letter handle abbreviation defined in the Analysis step.
2. **Single-fact rule.** Each concrete fact (price, %, event, quote) appears in exactly **one** place in the document. If a fact would naturally fit two sections, place it where it is most actionable and reference the theme by name elsewhere (e.g. "(see *Hormuz crisis*)"). The TL;DR may name themes but must not restate their data points.
3. **No bullish/bearish dual-column table.** It forces the same fact into both columns. Direction lives inside each theme (Bullish / Bearish / Watch).
4. **Future-only catalysts.** The Catalysts Ahead table contains scheduled future events (earnings, FOMC, data releases, expirations) with concrete dates. Drop today-already-happened items, vague "ongoing" rows, and speculative date stamps — those belong inside the relevant theme.
5. **Actionable for SPY/QQQ.** Sector or single-name detail belongs inside the relevant theme, not in a separate sector section.

## Output File

Save the summary to:
- **Directory**: `~/projects/news/data/x_market_news/`
- **Filename**: `x_market_news_YYYYMMDD_HHMM.md`

Use the skill start time in local time for the HHMM portion (e.g. `x_market_news_20260421_0900.md`).

## Full Mode Structure

```markdown
## X Market Summary ({Month} {Day}, {Year})
Sources: @handle1, @handle2 | Generated HH:MM

### TL;DR
3–5 sentences synthesizing the day for SPY/QQQ. Each sentence cites at least one
tweet. This is the only narrative synthesis section — do not restate it later.

### Themes
3–5 themes total. For each:

- **Theme name** — one-line framing ([@x](url))
  - Key data point or development inline ([@x](url))
  - Direction: Bullish / Bearish / Watch
  - SPY/QQQ implication: one sentence (mention sector tickers like XLE/XLY/XLF inline if relevant)
  (≤ 3 bullets per theme, including the framing line)

### Catalysts Ahead

| When | Catalyst | Why it matters |
|------|----------|----------------|
| ...  | ...      | ...            |

Future-dated only (earnings, FOMC, data releases, scheduled diplomacy, options
expiry). ≤ 6 rows. No today-already-happened items, no vague "ongoing" rows.
Reference themes by name in "Why it matters" instead of restating data points.

### Sources
- `@u` = @unusual_whales, `@f` = @FirstSquawk (expand the abbreviation key for whichever sources are configured)
- [@unusual_whales — short tweet label](url)
- ...

List every tweet actually cited above using the full handle. Omit tweets you did not cite.
```

### Length caps

- **TL;DR:** ≤ 5 sentences.
- **Each theme:** ≤ 3 bullets (framing line counts).
- **Catalysts table:** ≤ 6 rows.
- No additional sections (no separate Economic Signals table, Sector Impacts list, Positioning Thoughts, or Bottom Line — fold their content into Themes).

## Incremental Mode Structure

```markdown
## X Market Summary Update ({Month} {Day}, {Year})
Sources: @handle1, @handle2 | Generated HH:MM

### New Developments (since HH:MM)
Bullets covering only material new since the previous summary, using only tweets
from the new incremental window. Cite sources for every item.

**Key shift**: one-line summary of what changed since last summary.

### Combined Summary for Today
Re-emit the full structure (TL;DR / Themes / Catalysts Ahead / Sources) covering
all of today's cached tweets, applying the single-fact rule across old and new
material. Do not duplicate content between New Developments and the Combined
Summary's Themes — in the Combined Summary, integrate new items into the
appropriate theme.
```

For incremental mode:
- "New Developments" analyzes ONLY the new tweets from the inferred incremental fetch window.
- "Combined Summary" analyzes ALL cached tweets for the day (from the .jsonl files) and reads like a fresh full-day summary, not an addendum.
- Derive `since HH:MM` from the latest same-day summary filename, not a passed argument.

---
name: fetch-x-posts
description: Fetch X/Twitter posts via the news project's xreach-based modules — search top or first N posts for a query (including from a specific account via from:handle), snapshot the logged-in home feed (For You / Following), or bulk-fetch a user's timeline. Use when user asks to "search X", "get top/first N tweets for a query", "search tweets from @handle", "snapshot my X home feed", "get following feed", "fetch user @handle tweets", "pull N posts from X", or wants real-world usage opinions from X posts.
---

# fetch-x-posts

Unified interface over the `news` project's X fetchers (no scraping, no API tokens — uses `xreach` CLI which reads your browser cookies).

## Modules covered

| Task | Module | Auth | Data location |
|------|--------|------|---------------|
| Search query | `x_search` | browser cookies via `xreach search` | `data/x_search/<sanitized_query>/search_*.jsonl` |
| Home feed For You / Following | `x_home_feed` | browser cookies via `xreach home` | `data/x_home_feed/{for_you,following}/home_*.jsonl` |
| User timeline bulk | `user_tweets` | browser cookies via `xreach tweets` | `data/user_tweets/<handle>/tweets.jsonl` + `.resume.json` |

## Commands (use ml env python)

Interpreter: `/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python`

### 1. Search — first or top N posts for a query, including from a specific account

Supports both `latest` (first N as they appear, recency) and `top` (relevance). Use `from:handle` to restrict to a particular account.

```bash
# First 50 as shown (latest, default) — fastest for recency / timelines
python -m news.src.x_search.fetch --query "NVDA news" --count 50

# Top 50 most relevant (best for "top N posts about X")
python -m news.src.x_search.fetch --query "claude spark 1.1 vs grok 4.5" --type top --count 50 --no-fetch-articles

# From a particular account — first N or top N
python -m news.src.x_search.fetch --query "from:elonmusk" --count 50 --type latest
python -m news.src.x_search.fetch --query "from:elonmusk" --type top --count 50
python -m news.src.x_search.fetch --query "from:unusual_whales TSLA" --count 20 --type top
python -m news.src.x_search.fetch --query "from:OpenAI GPT-5" --count 30 --type latest

# Without article enrichment (faster, no browser render)
python -m news.src.x_search.fetch --query "NVDA" --count 10 --no-fetch-articles

# Dry run
python -m news.src.x_search.fetch --query "NVDA" --count 20 --no-write

# Programmatic
from news.src.x_search import fetch as x_search_fetch
posts = x_search_fetch.fetch_search_feed("Grok 4.5 reviews", search_type="top", count=50, write=False)
```

Search types: `top` (relevance), `latest` (recency, default), `people`, `photos`, `videos`. Snapshots dedup by id, 7-day retention.

### 2. Home feed — For You (algorithmic) vs Following (chronological)

```bash
# For You, top 50 (default)
python -m news.src.x_home_feed.fetch

# Following feed, top 100
python -m news.src.x_home_feed.fetch --following --count 100

# For You is the DEFAULT feed; --following is the ONLY feed switch. There is
# NO --feed flag (the module rejects it — two handoff workers hit this in
# 2026-08). Write `--feed for_you` as nothing, `--feed following` as --following.
python -m news.src.x_home_feed.fetch --count 50 --no-fetch-articles

# Dry run
python -m news.src.x_home_feed.fetch --count 20 --no-write
```

Each run is a fresh timestamped snapshot — no resume, no merge (feed is personalized & ephemeral).

### 3. User timeline — resumable bulk fetch

```bash
# DEFAULT (latest N): ensure the newest 500 are cached — front-fill new tweets, then
# backfill older only if short. Re-run anytime to catch up; no flag needed.
python -m news.src.user_tweets.fetch elonmusk --target 500

# Patient settings for background run (rides throttles)
python -m news.src.user_tweets.fetch elonmusk --target 500 --delay 5 --max-retries 20 --backoff-max 900

# --backfill: deepen the back-catalog with OLDER history (backward only)
python -m news.src.user_tweets.fetch elonmusk --backfill --target 3000

# With linked X Articles enrichment (off by default for bulk)
python -m news.src.user_tweets.fetch elonmusk --target 500 --fetch-articles
```

**For "latest N tweets from @handle": just run the default, then read the first N lines of `tweets.jsonl`** — that file is deduped by id and sorted newest-first at the end of every run, so `head -n N` *is* the latest N. The default front-fills from the top of the timeline to catch tweets posted since the last run, then backfills older only if the cache is short of `--target`. (There is no `--refresh` flag — the default already catches up. Use `--backfill` only when you want deeper *older* history without re-scanning the top.)

Hard ceiling: Twitter only serves ~800-3200 most recent tweets per handle regardless of paging.

## Post-fetch workflow

All snapshots are raw xreach item dicts, one JSONL per line, with fields: `id`, `text`, `createdAt`, `user`, `likeCount`, `retweetCount`, `viewCount`, `replyCount`, etc., plus optional `linked_articles`.

**Never sort or `max()` on the raw `createdAt` string.** Twitter's format leads with the weekday (`Tue Apr 21 16:00:00 +0000 2026`), so lexicographic comparison ranks by weekday name and silently returns a wrong — but plausible — "latest" tweet. Either rely on file order (below) or parse first:

```python
from news.src.common import xreach
newest = max(posts, key=lambda p: xreach.parse_twitter_date(p["createdAt"]))
```

File order by module:
- `user_tweets/<handle>/tweets.jsonl` — **sorted newest-first**; the latest N are the first N lines, no parsing needed.
- `x_search` / `x_home_feed` snapshots — **not time-sorted**; they keep the API's own order (relevance rank for `top`, feed rank for home). Parse `createdAt` if you need chronology.

**Token discipline (important):**
- Don't `cat` every file. After fetching, parse JSONL with Python to get summary stats.
- Example parser:
```bash
python << 'PY'
import json, pathlib, glob
path = sorted(pathlib.Path("data/x_search/<sanitized_query>").glob("*.jsonl"))[-1]
posts = [json.loads(l) for l in path.read_text().splitlines()]
posts_sorted = sorted(posts, key=lambda x: x.get("likeCount",0), reverse=True)
print(f"Total: {len(posts)} unique")
for p in posts_sorted[:10]:
    print(f"{p['likeCount']} likes | {p['createdAt']} | {p['text'][:200]}")
PY
```
- Only read full text of top relevant posts when user wants summary/analysis.

## Gotchas

- Auth: `xreach` reads your Chrome cookies automatically — no `logged_in_chrome` or storage-state file needed for search/home/user. If you get auth errors, open X in Chrome and re-login.
- Article enrichment: when enabled (default ON for search/home, OFF for user_tweets), uses `browser` project's LoggedInChrome with `~/projects/browser/data/storage_states/x.com.json`. If expired, auto-refreshes from live Chrome. Pass `--no-fetch-articles` to skip for speed.
- Rate limits: transient failures (`TransientFetchError`) are auto-retried with exponential backoff. Don't spam with `--delay 0`.
- Sanitization: search query dir sanitized: lowercased, non-alnum → `_`, truncated 80 chars. `NVDA news` → `nvda_news`.

## When user asks for summary

1. Fetch with `--type top --count N --no-fetch-articles` for fastest relevant results.
2. Parse JSONL, dedup by id if multiple queries, sort by `likeCount`/`viewCount`.
3. Summarize findings with themes, not just list — include representative high-like quotes.
4. Cite data location.

## References

- Module docs: `docs/modules/x_search.md`, `docs/modules/x_home_feed.md`, `docs/modules/user_tweets.md`, `docs/modules/common.md`
- Fetchers: `src/x_search/fetch.py`, `src/x_home_feed/fetch.py`, `src/user_tweets/fetch.py`

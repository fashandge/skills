---
name: fetch-reddit-posts
description: Fetch N Reddit posts and ALL their comments from a subreddit (or your logged-in home feed) into a temp folder, with no LLM calls — a pure Python script does the work. Use when the user asks to grab/scrape/download/pull/save posts (or posts + comments) from a subreddit or their Reddit home feed, e.g. "fetch the top 10 posts in r/X", "get the latest 20 posts and comments from r/Y", "pull every post from the last week in r/Z", "fetch the first N posts as shown when I open r/X", or "fetch the top N from my Reddit home feed". Selection can be top-N (all/year/month/week/day), most-recent-N, a time range (last N days/weeks/months), or the first-N-as-rendered timeline.
allowed-tools: Bash, Read
---

# fetch-reddit-posts

Fetch N Reddit posts plus **all of their comments** into a temp folder. One Python
script does everything and **no LLM is involved in fetching**: it drives a
logged-in Chrome, pulls Reddit's JSON from inside the page, and writes one
Markdown file per post (body + fully-expanded nested comments) plus
`index.md` / `index.json`.

## Run it

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python \
  ~/skills/fetch-reddit-posts/fetch_reddit_posts.py <target> [-n N] [mode] [flags]
```

`<target>` = subreddit (bare name, `r/name`, or URL) or the literal `home`.
Canonical examples:

```bash
… AiAutomations -n 10 --top all      # top N (all|year|month|week|day|hour)
… AiAutomations --since 7d           # every post in the last N days/weeks/months (Nd|Nw|Nm)
… home -n 10 --timeline              # first N as rendered (home feed needs --timeline)
```

**Run `-h` for the full, authoritative flag list** (`--new`, `--out`,
`--comment-sort`, `--max-more-calls`, …). Default mode is `--timeline` (first N
posts in the personalized order you actually see when you open the page).

## Gotchas (why this script exists)

- **Don't use curl** — Reddit returns 403 to plain `curl`/`urllib` from most IPs,
  and the home feed needs login. The script reuses the `browser` project's
  `logged_in_chrome` (auto-discovers the `reddit.com.json` storage-state) and
  fetches same-origin, which works. If the login state is missing/expired:
  `python ~/projects/browser/src/refresh_state.py reddit.com`.
- **Comments are complete** — "load more" stubs are expanded via the
  `morechildren` API. The per-post header shows `comments: <num>` vs how many were
  rendered; the small gap is just skipped `[deleted]`/`[removed]` bodies.
- **`--timeline` / `home` are personalized** — order varies by session and time
  (that's the point: "as shown to me"). `--top` / `--new` / `--since` are
  deterministic. `--since` returns *every* post in the window, not capped by `-n`.

## Token discipline (important)

The point is to keep content **on disk, out of the context window**. After running,
report from the printed stdout summary or read only `index.md` — do **not** `cat`
every post file in. Read individual post files only when the user wants
analysis, and prefer the few that matter over dumping the whole folder.

Default output is a fresh OS temp dir (path printed). Pass `--out <dir>` to write
into the session scratchpad instead.

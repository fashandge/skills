---
name: fetch-reddit-posts
description: Search Reddit for a topic, and fetch Reddit posts plus ALL their comments into a folder, with no LLM calls — a pure Python script does the work. Use when the user asks to search Reddit or find/summarize what Redditors say about something, e.g. "search reddit for X", "find reddit threads about X", "what does reddit say about X", "search r/Y for X", "summarize reddit reviews/opinions on X" — multiple query variants are deduped into a candidate list you triage before fetching. Also use to grab/scrape/download/pull/save posts (or posts + comments) from a subreddit or the logged-in home feed, e.g. "fetch the top 10 posts in r/X", "get the latest 20 posts and comments from r/Y", "pull every post from the last week in r/Z", or "fetch the top N from my Reddit home feed". Selection can be a search, top-N (all/year/month/week/day), most-recent-N, a time range (last N days/weeks/months), or the first-N-as-rendered timeline.
allowed-tools: Bash, Read
---

# fetch-reddit-posts

Search Reddit, and fetch posts plus **all of their comments** into a folder. One
Python script does everything and **no LLM is involved in fetching**: it drives a
logged-in Chrome, pulls Reddit's JSON from inside the page, and writes one
Markdown file per post (body + fully-expanded nested comments) plus
`index.md` / `index.json`.

## Run it

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python \
  ~/skills/fetch-reddit-posts/fetch_reddit_posts.py <target> [-n N] [mode] [flags]
```

`<target>` = subreddit (bare name, `r/name`, or URL), `home`, or `all`
(site-wide, search only). Canonical examples:

```bash
… AiAutomations -n 10 --top all      # top N (all|year|month|week|day|hour)
… AiAutomations --since 7d           # every post in the last N days/weeks/months (Nd|Nw|Nm)
… home -n 10 --timeline              # first N as rendered (home feed needs --timeline)
… all -q "pi vs hermes" -q "hermes agent review" --time year   # search: candidates only
… PiCodingAgent -q "hermes" -q "openclaw"                      # search inside one subreddit
… all -q "X vs Y" --expand-subs                                # best recall (see gotchas)
… --from <dir> --select 1-30 --out <dir> --resume              # then fetch the ones you picked
… --from <dir> --grep '\bpi\b' --rescan                        # which of those discuss X? (offline)
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
- **Search is two-phase on purpose** — search returns a lot of junk and comment
  forests are expensive, so phase 1 writes only `candidates.md` (title, score,
  comments, snippet) and prints the exact phase-2 command to run next. Triage
  that file, then fetch the rows worth having. Repeat `-q` for query variants;
  hits are deduped and tagged with which query found them.
- **Never use `--sort top` on a site-wide search.** It ranks by upvotes among
  loose matches, so a short query returns whatever is popular on Reddit — a real
  run of `-q "pi vs hermes" --sort top` returned r/skyrim merch and a truck
  mileage chart, while the identical query under `--sort relevance` returned the
  actual comparison thread as result #1. Relevance is the default; keep it.
- **Search queries both Reddit and a web index by default** (`--discover both`).
  Reddit's own search only matches post titles/bodies — its API silently ignores
  comment search — so a thread where the discussion happens in the *comments* is
  invisible to it. The web pass (Tavily, `TAVILY_API_KEY` in
  `~/.config/secrets.env`) ranks the whole page and finds those; without the key
  it degrades to Reddit-only with a note. Pass `--discover reddit` to skip the
  metered API. Candidates are round-robined across sources so no pass gets
  starved by `-n`.
- **Add `--expand-subs` only when your query is a minority topic inside the subs
  you land in.** "X vs Y" lands in r/X, and you want the rare r/X threads about Y
  — buried at 15 upvotes site-wide, top hit once scoped. But when the query *is*
  the sub's subject ("hermes agent memory" in r/hermesagent) it just re-returns
  the sub: measured at +45 posts and zero extra on-topic hits. Off by default.
- **`--grep REGEX`** counts a term's hits inside each fetched comment tree — the
  only way to surface threads whose *comments*, not titles, discuss your term.
  For the follow-up you didn't plan for, `--from <run dir> --grep X --rescan`
  recounts over posts already on disk: no network, no browser, instant. Reach
  for that instead of hand-rolling `grep` over the folder.
- **Long runs are safe to start** — 429s are backed off automatically, posts are
  fetched in batches with a fresh browser session each, and every post is
  appended to `index.jsonl` as it lands. After any interruption, re-run the same
  command with `--out <same dir> --resume`.
- **Comments are complete** — "load more" stubs are expanded via the
  `morechildren` API. The per-post header shows `comments: <num>` vs how many were
  rendered; the small gap is just skipped `[deleted]`/`[removed]` bodies.
- **`--timeline` / `home` are personalized** — order varies by session and time
  (that's the point: "as shown to me"). `--top` / `--new` / `--since` are
  deterministic. `--since` returns *every* post in the window, not capped by `-n`.

## Token discipline (important)

The point is to keep content **on disk, out of the context window**. After running,
report from the printed stdout summary or read only `candidates.md` / `index.md`
— do **not** `cat` every post file in. Read individual post files only when the
user wants analysis, and prefer the few that matter over dumping the whole folder.

Default output is a fresh OS temp dir (path printed). Pass `--out <dir>` to write
into the session scratchpad instead.

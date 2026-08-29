---
name: fetch-zhihu-posts
description: Search Zhihu (知乎), fetch whole questions — EVERY answer, not just the top few — into a folder as Markdown (a pure Python script does the fetching, no LLM calls), then by default summarize the haul in Chinese; say "fetch only" / "just fetch" to stop after the fetch. Use when the user asks what Zhihu says about something, wants Chinese community opinion, real-world user reviews, or hands-on experience reports (实际体验 / 实测 / 使用体验) on a product, model, company or event, e.g. "summarize zhihu reviews of X", "search zhihu for X", "知乎上怎么评价 X", "what do Chinese users say about X". Also use to pull one specific question's full answer set from a URL or id, or to grab 知乎专栏 articles found alongside it. Search is two-phase — query variants are deduped into a candidate list you triage before fetching.
allowed-tools: Bash, Read
---

# fetch-zhihu-posts

Search Zhihu, and fetch questions with **all of their answers** into a folder. One
Python script does everything and **no LLM is involved in fetching**: it drives a
logged-in Chrome, pulls Zhihu's JSON from inside the page, and writes one Markdown
file per question (YAML frontmatter + every answer with author, votes and date)
plus `index.md` / `index.json`.

Fetching is the means, not the deliverable: by default a run ends with a written
**summary** of the haul (see below), not "here are the files".

## Run it

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python \
  ~/skills/fetch-zhihu-posts/fetch_zhihu_posts.py <target|-q QUERY|--from DIR> [flags]
```

Canonical examples:

```bash
# phase 1: search with query variants → candidates only, no answer bodies
… -q "hy4 preview 实际体验" -q "混元 hy4 实测"

# phase 2: fetch the questions you picked out of candidates.md
… --from <dir> --select 1-5 --out <dir> --resume

# skip search — one question, every answer, by URL or bare id
… https://www.zhihu.com/question/2076674418479257365
```

**Run `-h` for the full, authoritative flag list** (`--max-answers`, `--min-votes`,
`--order`, `--sort`, `--per-query`, `--no-articles`, `--headed`, …).

## Where output goes

Without `--out` a run writes to a fresh `$TMPDIR` directory that macOS clears on
its own (files untouched for 3+ days) — the right default for a scratch fetch,
and the script prints the path plus that caveat. **A run directory is not
storage**: pass `--out DIR` when the results should survive, and if anything is
worth keeping long-term, absorb it into `~/notes` rather than pointing at a temp
path later. `--out` on an existing run directory also appends to it, which is
what `--resume` and phase 2 rely on.

## Token discipline

A popular question is 50+ answers and **~100KB of Markdown** — do not `cat` the
output. Report from the printed summary and `index.md`, then read individual
question files (or `grep` them) only as the task actually needs. Phase 1 exists
precisely so you triage from cheap snippets before paying for bodies.

Reading for the summary is budgeted, not exhaustive: `wc -c *.md | sort -n`
first, read the small files whole, and for the big ones read only the head —
answers are sorted by votes by default, so the top of the file *is* the
high-signal part; ~15–20KB per file is plenty. Batch `head -c N` over several
files into one scratch file and read that; a single unbudgeted read of a big
file blows past the Read tool's cap and gets spilled to disk anyway.

## Summarize (the default deliverable)

After phase 2, write the summary — the user should not have to ask. **Opt-out**:
if the user says "fetch only", "just fetch", "don't summarize" (只抓取 / 不用总结),
stop after the fetch and report the output directory plus the printed run
summary.

- **In Chinese, verdict first.** The source is Chinese, so per the global
  answer-shape rules the summary is too, and it opens with a direct verdict on
  the question actually asked, then the evidence. Quotes stay verbatim.
- **Attribute high-signal claims** to the answer's author handle, vote count and
  date — that is what separates a Zhihu summary from a vibe check.
- **Weight by genre**: `[question]` files are many users answering — the real
  reviews; `[article]` files are single-author 专栏 posts, often promotional,
  with possibly-partial bodies (see Gotchas). Lean on questions; cite an
  article as one author's take.

## Gotchas (why this script exists)

- **Don't use curl, and don't scrape the rendered page.** Zhihu answers `403` to
  plain `curl`/`urllib`, and a *rendered* question page carries only the first ~3
  answers (the rest arrive by XHR). The script reuses the `browser` project's
  `logged_in_chrome` (auto-discovers `zhihu.com.json`) and fetches same-origin.
- **A stale session fails silently — it does not raise.** `page.goto` returns a
  perfectly good HTTP 200 serving the *logged-out* page, so a naive run looks like
  "this question only has 3 answers" rather than an error. The fetcher converts the
  API's 403 into a typed `ZhihuAPIError`, which `run_with_auto_refresh` then heals
  by re-capturing cookies from the live Chrome login and retrying once. If the real
  Chrome is signed out too, sign in there, or run:
  `python ~/projects/browser/src/refresh_state.py zhihu.com`
- **Two Zhihu URL shapes, two genres.** `/question/{id}` is many users answering —
  that's the reviews. `zhuanlan.zhihu.com/p/{id}` is a single-author column, often
  promotional. Both land in candidates, labelled `[question]` / `[article]` —
  the summary weights them differently (see above).
- **Some endpoints need Zhihu's signed headers** (`x-zse-96`) and are unreachable:
  question *detail* (so the real answer count is unknown until fetched — phase 1
  reports search *hits* instead) and article *bodies* (so article text comes from
  the search index and may be partial; the file says so).
- **Answers Zhihu served collapsed or clipped are flagged**, not silently kept —
  `⚠️ 正文可能被截断` in the file and a `truncated` count in `index.md`.

## Where the logic lives

The script is a thin two-phase CLI. The Zhihu API layer — `search_zhihu`,
`fetch_zhihu_question`, `zhihu_api_session`, the auth-expiry typing and the
paging — lives in `clipping/fetchers/zhihu.py` beside that module's existing URL
classification, shell-marker detection and `SITE_VALUES`, so other callers (e.g.
`news/src/zhihu_ai_news`) can reuse it. Edit the fetcher there, not here.

## Related

- `fetch-reddit-posts` / `fetch-x-posts` — same two-phase shape for other sources.
- The official `zhihu` skill (知乎开放平台 CLI) is a *complementary* discovery tool:
  first-party and authorized, but capped at 10 results per search and 10 searches
  per day, and it cannot enumerate a question's answers. Use it to find things;
  use this to pull a discussion in full.

#!/usr/bin/env python
"""Search Reddit, and fetch posts + ALL their comments into a folder — no LLM calls.

Drives a logged-in Chrome (the `browser` project's logged_in_chrome) and issues
same-origin `fetch()` calls from inside the page, so Reddit's JSON endpoints work
(plain curl/urllib gets 403 from most IPs, and the home feed needs your login).

Two things this does:

  LISTING   fetch posts from one subreddit, or your logged-in home feed
            --top [tf] | --new | --timeline | --since Nd|Nw|Nm

  SEARCH    find posts across all of Reddit (target `all`) or inside one
            subreddit, with one or more -q/--query variants.  Search is
            TWO-PHASE by design: phase 1 writes a cheap candidate list
            (candidates.md / .json — title, score, comments, snippet; no
            comment trees), you pick the rows worth having, then phase 2
            (--from ... --select ...) fetches those posts in full.
            Search returns a lot of junk and comment forests are expensive,
            so triaging before fetching is the whole point.  Phase 1 prints
            the exact phase-2 command to run next.

Each fetched post is written as one Markdown file (post body + full nested
comments, including expanded "load more" stubs), alongside an append-only
`index.jsonl` ledger and derived `index.md` / `index.json`.  Nothing is sent
to an LLM.

Examples:
  # a subreddit listing, as today
  %(prog)s AiAutomations -n 10 --top month

  # phase 1: search all of Reddit with two query variants, candidates only
  %(prog)s all -q "claude code vs cursor" -q "cursor migration" --sort top --time year

  # phase 2: fetch full posts + comments for the rows you picked
  %(prog)s --from <dir>/candidates.json --select 1-30 --out <dir> --resume
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import random
import re
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode

from browser.src import logged_in_chrome

REDDIT = "https://www.reddit.com"

# --------------------------------------------------------------------------- #
# schema constants — the single source of truth for argparse `choices=` AND for
# every error message. Never spell these values out again anywhere else.
# --------------------------------------------------------------------------- #
TIMEFRAMES = ("all", "year", "month", "week", "day", "hour")
SEARCH_SORTS = ("relevance", "hot", "top", "new", "comments")
COMMENT_SORTS = ("confidence", "top", "new", "controversial", "old", "qa")
DISCOVERY = ("reddit", "web", "both")
LISTING_MODE_FLAGS = ("--top", "--new", "--timeline", "--since")
# (flag, dest) — "was it set?" is decided by comparing against the parser's own
# default, so adding a flag or changing a default cannot desync the validator.
SEARCH_ONLY = (("--sort", "sort"), ("--time", "time"), ("--per-query", "per_query"),
               ("--nsfw", "nsfw"), ("--discover", "discover"),
               ("--expand-subs", "expand_subs"), ("--web-results", "web_results"))
SEARCH_ONLY_FLAGS = tuple(f for f, _ in SEARCH_ONLY)

# Below this, site-wide search loses the low-score long tail — which is exactly
# where cross-tool comparison threads live.
MIN_USEFUL_PER_QUERY = 15

# Reddit stops paging search around here, and relevance degrades well before it.
SEARCH_HARD_CAP = 250

# Row schema shared by candidates.json (phase 1) and index.json (phase 2), so
# --from needs no special-casing between them.
ROW_KEYS = ("n", "title", "author", "subreddit", "score", "num_comments",
            "comments_fetched", "posted", "url", "file", "found_by", "snippet",
            "grep_hits")

_TARGETS = ("a subreddit (AiAutomations | r/AiAutomations | "
            "https://www.reddit.com/r/AiAutomations), 'home' (your logged-in "
            "feed, --timeline only), or 'all' (site-wide, requires --query)")
_FROM_SOURCES = ("a run directory, a candidates.json / index.json from a "
                 "previous run, a newline-delimited list of permalinks, or '-' "
                 "for stdin")


def _opts(values) -> str:
    """'{a,b,c}' — for interpolating an enum into help and error text."""
    return "{" + ",".join(values) + "}"


# In-page fetch: runs in the reddit.com origin with cookies. Returns a plain
# object — page.evaluate already JSON-serializes the result, and an in-page
# JSON.stringify can itself throw on lone surrogates in Reddit bodies. The
# try/catch keeps an in-page network failure attributable to its URL.
_FETCH_JS = """
async (u) => {
  try {
    const r = await fetch(u, {credentials: 'include'});
    return {status: r.status, retryAfter: r.headers.get('retry-after'),
            body: await r.text()};
  } catch (e) {
    return {status: 0, retryAfter: null, body: '', error: String(e)};
  }
}
"""


# --------------------------------------------------------------------------- #
# secrets
# --------------------------------------------------------------------------- #
def secret(name: str) -> str | None:
    """Look up an API key: environment, then ~/.config/secrets.env."""
    if os.environ.get(name):
        return os.environ[name]
    p = pathlib.Path.home() / ".config/secrets.env"
    if p.exists():
        m = re.search(rf"^\s*(?:export\s+)?{re.escape(name)}=(.+)$",
                      p.read_text(), re.M)
        if m:
            return m.group(1).strip().strip("'\"")
    return None


# --------------------------------------------------------------------------- #
# web discovery (Tavily)
# --------------------------------------------------------------------------- #
# Why this exists: Reddit's own search is a weak lexical match on title+body and
# its API silently ignores type=comment, so a thread whose *comments* hold the
# discussion is unreachable natively. A web index ranks the whole crawled page,
# so it finds those — and subreddits you would never have guessed. Tavily is the
# only backend that works here: Anthropic's WebSearch hard-blocks reddit.com and
# Exa's index excludes it (both verified: 0 results).
def web_discover(queries: list[str], max_results: int,
                 sub: str | None = None) -> dict[str, list[str]]:
    """Return {permalink: [query labels]} for Reddit posts matching the queries.

    `sub` restricts results to one subreddit. The web backend can only filter by
    *domain*, so scoping has to happen here — otherwise a subreddit-scoped run
    silently imports off-target hits (searching r/PiCodingAgent for "hermes"
    otherwise returns r/handbags and r/GreekMythology).
    """
    key = secret("TAVILY_API_KEY")
    if not key:
        raise RuntimeError(
            "web discovery needs TAVILY_API_KEY. Add it to ~/.config/secrets.env "
            "(chmod 600) as: export TAVILY_API_KEY=tvly-...  Get one at "
            "https://tavily.com. Use --discover reddit to stay on Reddit's own "
            "search, which needs no key.")
    want = f"/r/{sub.lower()}/" if sub else None
    found: dict[str, list[str]] = {}
    off_target = 0
    for qi, q in enumerate(queries, 1):
        label = f"w{qi}"
        payload = json.dumps({
            "api_key": key, "query": q, "max_results": max_results,
            "include_domains": ["reddit.com"], "search_depth": "advanced"}).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search", data=payload,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
        except Exception as exc:
            sys.stderr.write(f"  [warn] web search failed for {q!r}: {exc}\n")
            continue
        hits = 0
        for row in data.get("results", []):
            url = row.get("url", "")
            # Tavily also returns subreddit landing pages; keep only real threads.
            if "/comments/" not in url:
                continue
            pl = permalink_of(url).split("?")[0]
            if want and want not in pl.lower():
                off_target += 1
                continue
            found.setdefault(pl, [])
            if label not in found[pl]:
                found[pl].append(label)
            hits += 1
        where = f" in r/{sub}" if sub else ""
        print(f"  {label} {q!r}{where}: {hits} reddit threads (web)", flush=True)
    if off_target:
        print(f"      (dropped {off_target} web hits outside r/{sub})", flush=True)
    return found


def hydrate(fetch, links: dict[str, list[str]]) -> list[dict]:
    """Turn discovered permalinks into post dicts, one cheap Reddit call each.

    Web results carry no score/comment-count/date (Tavily's content field is a
    ~140-char SEO blurb), so metadata has to come from Reddit itself for the
    candidate list to be comparable with the native path.
    """
    posts = []
    for i, (pl, labels) in enumerate(links.items(), 1):
        try:
            res = fetch_post(fetch, pl, "confidence", 0, with_comments=False)
        except Exception as exc:
            sys.stderr.write(f"  [warn] could not hydrate {pl}: {exc}\n")
            continue
        post = res["post"]
        post["_found_by"] = labels
        post["_rank_best"] = i
        posts.append(post)
        time.sleep(0.3)
    print(f"  hydrated {len(posts)}/{len(links)} web results with Reddit metadata",
          flush=True)
    return posts


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
class RedditHTTPError(RuntimeError):
    def __init__(self, status: int, url: str, hint: str = "", snippet: str = ""):
        self.status, self.url, self.snippet = status, url, snippet
        msg = f"HTTP {status} from reddit for {url}"
        if hint:
            msg += f"\n  {hint}"
        if snippet:
            msg += f"\n  body starts: {snippet[:200]!r}"
        super().__init__(msg)


def fetch_json(page, url: str, retries: int = 5):
    """GET `url` from inside the reddit.com origin and parse JSON.

    Handles the failure modes that otherwise surface as a bare JSONDecodeError:
    429 (empty body) is retried with backoff, and every other non-200 raises a
    RedditHTTPError that names the status and what to do about it.
    """
    for attempt in range(retries + 1):
        r = page.evaluate(_FETCH_JS, url)
        status, body = r.get("status", 0), r.get("body") or ""

        if status == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                # Usually an HTML login wall or a Reddit error page served as 200.
                raise RedditHTTPError(
                    200, url,
                    "expected JSON, got something else — the logged-in session may "
                    "have expired. Refresh: "
                    "python ~/projects/browser/src/refresh_state.py reddit.com",
                    body) from None

        if status in (429, 500, 502, 503, 504) and attempt < retries:
            delay = None
            ra = r.get("retryAfter")
            if ra:
                try:
                    delay = float(ra)
                except ValueError:
                    delay = None
                if delay is not None and delay > 120:
                    delay = None  # implausible; fall back to our own backoff
            if delay is None:
                delay = min(60.0, 2.0 * (2 ** attempt)) * random.uniform(0.8, 1.2)
            sys.stderr.write(f"  [http {status}] retry {attempt + 1}/{retries} "
                             f"in {delay:.0f}s\n")
            sys.stderr.flush()
            time.sleep(delay)
            continue

        if status == 429:
            raise RedditHTTPError(429, url,
                                  "rate limited and out of retries — rerun with a "
                                  "smaller --batch-size or -n, or wait a few minutes")
        if status in (401, 403):
            raise RedditHTTPError(status, url,
                                  "the logged-in session is likely expired. Refresh: "
                                  "python ~/projects/browser/src/refresh_state.py reddit.com")
        if status == 404:
            raise RedditHTTPError(404, url,
                                  "no such subreddit or post (check spelling / that "
                                  "it is not private)")
        if status == 0:
            hint = r.get("error") or "in-page network error"
            if attempt < retries:
                time.sleep(2)
                continue
            raise RedditHTTPError(0, url, hint)
        raise RedditHTTPError(status, url, snippet=body)

    raise RedditHTTPError(0, url, "exhausted retries")


def is_auth_error(exc: BaseException) -> bool:
    return isinstance(exc, RedditHTTPError) and exc.status in (401, 403)


# --------------------------------------------------------------------------- #
# URL building + pagination
# --------------------------------------------------------------------------- #
def listing_url(path: str, params: dict | None = None) -> str:
    """Build a Reddit .json URL from a PATH and a params dict.

    `path` is a path only ("/r/x/top", "/search", "/r/x/search", a permalink) —
    it must never carry a query string. Taking params as a dict is what makes
    the old `base + ".json"` bug (which produced "...&t=all.json?limit=100" once
    the base had a query) impossible to express.
    """
    if "?" in path:
        raise ValueError(f"listing_url() takes a path, not a query string: {path!r}")
    q = {"raw_json": 1}
    for k, v in (params or {}).items():
        if v is None or v is False:
            continue
        q[k] = v
    return f"{REDDIT}{path.rstrip('/')}.json?{urlencode(q)}"


def paginate(fetch, path: str, params: dict, n: int, *, cutoff: float | None = None,
             hard_cap: int = 1000, page_size: int = 100) -> list[dict]:
    """Page a Reddit listing/search endpoint, returning up to n t3 posts.

    If cutoff is set, keep every post with created_utc >= cutoff and stop once
    older posts appear (n acts as a safety cap).
    """
    posts: list[dict] = []
    seen: set[str] = set()
    after = None
    while len(posts) < min(n, hard_cap):
        url = listing_url(path, {**params, "limit": page_size, "after": after})
        data = fetch(url)
        children = data.get("data", {}).get("children", [])
        if not children:
            break
        stop = False
        for c in children:
            if c.get("kind") != "t3":
                continue
            d = c["data"]
            if cutoff is not None and d.get("created_utc", 0) < cutoff:
                stop = True
                break
            if d.get("id") in seen:
                continue
            seen.add(d.get("id"))
            posts.append(d)
        after = data.get("data", {}).get("after")
        if stop or not after:
            break
        time.sleep(0.4)
    return posts[:n]


# --------------------------------------------------------------------------- #
# target / arg parsing helpers
# --------------------------------------------------------------------------- #
def normalize_target(target: str) -> tuple[str, str | None]:
    """Return ('home', None), ('all', None) or ('subreddit', 'AiAutomations')."""
    t = target.strip()
    if t.lower() in ("home", "frontpage", "/"):
        return "home", None
    if t.lower() == "all":
        return "all", None
    m = re.search(r"reddit\.com/r/([^/?#]+)", t)
    if m:
        return "subreddit", m.group(1)
    return "subreddit", t.lstrip("/").removeprefix("r/")


def parse_since(s: str) -> float:
    """'7d' / '2w' / '1m' -> cutoff epoch seconds (UTC)."""
    m = re.fullmatch(r"\s*(\d+)\s*([dwm])\s*", s.lower())
    if not m:
        raise ValueError(f"--since must look like 7d / 2w / 1m, got {s!r}")
    n, unit = int(m.group(1)), m.group(2)
    days = n * {"d": 1, "w": 7, "m": 30}[unit]
    return time.time() - days * 86400


def parse_select(spec: str, total: int) -> list[int]:
    """'1-30' / '1-10,15,40-' / 'all' -> sorted 1-based row numbers within total."""
    spec = (spec or "all").strip()
    if spec.lower() == "all":
        return list(range(1, total + 1))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d*)", part)
        if m:
            lo = int(m.group(1))
            hi = int(m.group(2)) if m.group(2) else total
            out.update(range(max(1, lo), min(total, hi) + 1))
            continue
        if part.isdigit():
            v = int(part)
            if 1 <= v <= total:
                out.add(v)
            continue
        raise ValueError(part)
    return sorted(out)


def slugify(text: str, maxlen: int = 50) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return (s[:maxlen] or "post").strip("_")


def iso(ts: float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def snippet_of(post: dict, limit: int = 220) -> str:
    body = re.sub(r"\s+", " ", (post.get("selftext") or "").strip())
    if not body and post.get("url") and not post.get("is_self"):
        body = f"(link) {post['url']}"
    return body[:limit] + ("…" if len(body) > limit else "")


# --------------------------------------------------------------------------- #
# search
# --------------------------------------------------------------------------- #
def merge_posts(into: list[dict], new: list[dict]) -> list[dict]:
    """Union post lists, deduping by id and merging their `_found_by` labels."""
    by_id = {p.get("id"): p for p in into}
    for p in new:
        pid = p.get("id")
        cur = by_id.get(pid)
        if cur is None:
            by_id[pid] = p
            into.append(p)
            continue
        for lbl in p.get("_found_by", []):
            if lbl not in cur["_found_by"]:
                cur["_found_by"].append(lbl)
        cur["_rank_best"] = min(cur.get("_rank_best", 10 ** 6),
                                p.get("_rank_best", 10 ** 6))
    return into


def search_posts(fetch, queries: list[str], sub: str | None, sort: str, tf: str,
                 per_query: int, nsfw: bool, tag: str = "q") -> list[dict]:
    """Fan out across query variants, dedupe by post id, keep first-seen order.

    Each surviving post gains `_found_by` (which queries surfaced it) and
    `_rank_best` (best rank across queries).
    """
    path = f"/r/{sub}/search" if sub else "/search"
    params_base = {"sort": sort, "t": tf, "type": "link",
                   "restrict_sr": "on" if sub else None,
                   "include_over_18": "on" if nsfw else None}
    posts: list[dict] = []
    raw = 0
    for qi, q in enumerate(queries, 1):
        label = f"{tag}{qi}"
        hits = paginate(fetch, path, {**params_base, "q": q}, per_query,
                        hard_cap=SEARCH_HARD_CAP)
        raw += len(hits)
        where = f" in r/{sub}" if sub else ""
        print(f"  {label} {q!r}{where}: {len(hits)} results", flush=True)
        if len(hits) >= SEARCH_HARD_CAP:
            print(f"      (hit Reddit's ~{SEARCH_HARD_CAP}-result search ceiling — "
                  f"add more -q variants rather than raising --per-query)", flush=True)
        for rank, d in enumerate(hits, 1):
            d["_found_by"] = [label]
            d["_rank_best"] = rank
        merge_posts(posts, hits)
    if not sub:
        print(f"  {len(queries)} quer{'y' if len(queries) == 1 else 'ies'} → "
              f"{raw} raw → {len(posts)} unique", flush=True)
    return posts


def _pass_kind(label: str) -> str:
    """Which discovery pass a `_found_by` label came from."""
    return "web" if label.startswith("w") else ("expand" if label.startswith("s")
                                                else "reddit")


def rank_candidates(posts: list[dict]) -> list[dict]:
    """Order candidates so no discovery pass gets starved by the -n cut.

    Two things go wrong with naive ordering. First-seen order lets whichever pass
    ran first fill the entire quota. But ranking purely by "found by most passes"
    is also wrong: a subreddit-scoped expansion returns that sub's generally
    popular threads, which match every query loosely and therefore appear in
    every pass — so megathreads and setup guides crowd out the narrowly-relevant
    thread that only the web index could find.

    So: sort within each pass kind (multi-pass hits first, then by rank), then
    round-robin across kinds. Every source gets proportional representation, and
    the web finds — unreachable through Reddit's own search — always survive.
    """
    def key(p):
        labels = p.get("_found_by", []) or []
        return (-len({_pass_kind(l) for l in labels}), -len(labels),
                p.get("_rank_best", 10 ** 6))

    buckets: dict[str, list[dict]] = {}
    for p in posts:
        labels = p.get("_found_by", []) or []
        # Attribute each post to its rarest source: web < expand < reddit.
        kinds = {_pass_kind(l) for l in labels}
        home = ("web" if "web" in kinds
                else "expand" if "expand" in kinds else "reddit")
        buckets.setdefault(home, []).append(p)
    for b in buckets.values():
        b.sort(key=key)

    out: list[dict] = []
    order = [k for k in ("web", "reddit", "expand") if k in buckets]
    i = 0
    while len(out) < len(posts):
        progressed = False
        for k in order:
            if i < len(buckets[k]):
                out.append(buckets[k][i])
                progressed = True
        if not progressed:
            break
        i += 1
    return out


def top_subreddits(posts: list[dict], n: int) -> list[str]:
    """The subreddits a first pass landed in — the signal for where to look next."""
    counts = collections.Counter(p.get("subreddit", "") for p in posts
                                 if p.get("subreddit"))
    return [s for s, _ in counts.most_common(n)]


def expand_by_subreddit(fetch, posts: list[dict], queries: list[str], sort: str,
                        tf: str, per_query: int, nsfw: bool, n_subs: int) -> list[dict]:
    """Re-run every query scoped to the busiest subreddits from the first pass.

    Site-wide relevance buries low-score posts, but a cross-tool comparison
    thread in a brand subreddit is often exactly that: 15 upvotes and invisible
    site-wide, yet the top hit once the search is scoped there.
    """
    subs = top_subreddits(posts, n_subs)
    if not subs:
        return posts
    print(f"  expanding into top {len(subs)} subreddit(s): "
          f"{', '.join('r/' + s for s in subs)}", flush=True)
    before = len(posts)
    for si, sub in enumerate(subs, 1):
        found = search_posts(fetch, queries, sub, sort, tf, per_query, nsfw,
                             tag=f"s{si}.")
        merge_posts(posts, found)
    print(f"  expansion added {len(posts) - before} new posts", flush=True)
    return posts


def filter_candidates(posts: list[dict], match: list[str], exclude: list[str],
                      min_score: int, min_comments: int) -> tuple[list[dict], dict]:
    """Drop obvious junk deterministically. Repeated --match/--exclude are ORed."""
    m_res = [re.compile(p, re.I) for p in (match or [])]
    x_res = [re.compile(p, re.I) for p in (exclude or [])]
    dropped = {"match": 0, "exclude": 0, "min_score": 0, "min_comments": 0}
    kept = []
    for d in posts:
        hay = f"{d.get('title', '')}\n{d.get('selftext', '')}"
        if m_res and not any(r.search(hay) for r in m_res):
            dropped["match"] += 1
            continue
        if x_res and any(r.search(hay) for r in x_res):
            dropped["exclude"] += 1
            continue
        if (d.get("score") or 0) < min_score:
            dropped["min_score"] += 1
            continue
        if (d.get("num_comments") or 0) < min_comments:
            dropped["min_comments"] += 1
            continue
        kept.append(d)
    return kept, dropped


def candidate_row(post: dict, n: int) -> dict:
    row = {k: None for k in ROW_KEYS}
    row.update({
        "n": n,
        "title": post.get("title", ""),
        "author": post.get("author", ""),
        "subreddit": post.get("subreddit", ""),
        "score": post.get("score"),
        "num_comments": post.get("num_comments"),
        "posted": iso(post.get("created_utc")),
        "url": f"{REDDIT}{post.get('permalink', '')}",
        "found_by": ",".join(post.get("_found_by", [])) or None,
        "snippet": snippet_of(post),
    })
    return row


def write_candidates(out_dir: pathlib.Path, rows: list[dict], meta: dict) -> dict:
    (out_dir / "candidates.json").write_text(json.dumps(rows, indent=2))
    (out_dir / "query.json").write_text(json.dumps(meta, indent=2))
    md = [f"# Reddit search — {meta['header']}", f"# {meta['counts']}", ""]
    for r in rows:
        md.append(f"{r['n']:>3}. [{r['title']}]({r['url']})")
        bits = [f"r/{r['subreddit']}", f"u/{r['author']}", f"{r['score']}↑",
                f"{r['num_comments']}c", (r["posted"] or "")[:10]]
        if r.get("found_by"):
            bits.append(f"found_by: {r['found_by']}")
        md.append(f"     {' · '.join(b for b in bits if b)}")
        if r.get("snippet"):
            md.append(f"     > {r['snippet']}")
        md.append("")
    (out_dir / "candidates.md").write_text("\n".join(md) + "\n")
    return {"candidates_json": str(out_dir / "candidates.json"),
            "candidates_md": str(out_dir / "candidates.md")}


def load_from(src: str) -> list[dict]:
    """Load rows from a run dir, candidates.json/index.json, a permalink list, or '-'."""
    if src == "-":
        text, name = sys.stdin.read(), "<stdin>"
    else:
        p = pathlib.Path(src).expanduser()
        if p.is_dir():
            for cand in ("candidates.json", "index.json"):
                if (p / cand).exists():
                    p = p / cand
                    break
            else:
                raise FileNotFoundError(
                    f"{src} has no candidates.json or index.json — pass one of "
                    f"{_FROM_SOURCES}")
        if not p.exists():
            raise FileNotFoundError(f"{src} does not exist — pass {_FROM_SOURCES}")
        text, name = p.read_text(), str(p)

    if text.lstrip().startswith("["):
        out = []
        for i, r in enumerate(json.loads(text), 1):
            url = r.get("url") or r.get("permalink")
            if url:
                out.append({**r, "n": r.get("n") or i, "url": url})
        if not out:
            raise ValueError(f"{name} has no rows with a url/permalink")
        return out
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append({"n": len(out) + 1, "url": line, "title": "", "author": "",
                    "subreddit": "", "score": None, "num_comments": None})
    if not out:
        raise ValueError(f"{name} contained no permalinks")
    return out


def permalink_of(url: str) -> str:
    return re.sub(r"^https?://[^/]+", "", url) or url


# --------------------------------------------------------------------------- #
# listing: rendered DOM order (timeline / home — "as shown to me")
# --------------------------------------------------------------------------- #
def fetch_dom_order(page, url: str, n: int) -> list[dict]:
    """Scroll the rendered feed and collect the first n non-promoted posts in
    display order (the personalized sort the user actually sees)."""
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_selector("shreddit-post", timeout=30000)
    order: list[str] = []
    seen: dict[str, dict] = {}
    stagnant = 0
    while len(order) < n and stagnant < 8:
        items = page.eval_on_selector_all(
            "shreddit-post",
            """els => els.map(e => ({
                title: e.getAttribute('post-title'),
                author: e.getAttribute('author'),
                score: e.getAttribute('score'),
                comments: e.getAttribute('comment-count'),
                permalink: e.getAttribute('permalink'),
                promoted: e.getAttribute('promoted'),
                id: e.getAttribute('id')
            }))""",
        )
        prev = len(order)
        for it in items:
            pl = it.get("permalink")
            if pl and pl not in seen and not it.get("promoted"):
                seen[pl] = it
                order.append(pl)
        if len(order) >= n:
            break
        page.mouse.wheel(0, 5000)
        time.sleep(1.3)
        stagnant = stagnant + 1 if len(order) == prev else 0
    return [seen[pl] for pl in order[:n]]


# --------------------------------------------------------------------------- #
# comments: build full forest (expanding "load more" via morechildren)
# --------------------------------------------------------------------------- #
def build_comment_forest(fetch, link_fullname: str, top_children: list[dict],
                         max_more_calls: int = 80) -> list[dict]:
    """Return a list of root comment nodes {'data':..., 'replies':[...]} with all
    'more' stubs expanded via the morechildren API."""
    nodes: dict[str, dict] = {}
    roots: list[dict] = []
    more_batches: list[list[str]] = []

    def node_for(fn: str) -> dict:
        nd = nodes.get(fn)
        if nd is None:
            nd = {"data": None, "replies": []}
            nodes[fn] = nd
        return nd

    def add_thing(thing: dict):
        if thing.get("kind") == "more":
            kids = thing.get("data", {}).get("children") or []
            if kids:
                more_batches.append(kids)
            return
        if thing.get("kind") != "t1":
            return
        d = thing["data"]
        fn = d.get("name")
        if not fn:
            return
        nd = node_for(fn)
        nd["data"] = d
        replies = d.get("replies")
        if replies and isinstance(replies, dict):
            for c in replies["data"]["children"]:
                add_thing(c)
        parent = d.get("parent_id")
        if parent == link_fullname:
            if nd not in roots:
                roots.append(nd)
        else:
            pnode = node_for(parent)
            if nd not in pnode["replies"]:
                pnode["replies"].append(nd)

    for c in top_children:
        add_thing(c)

    calls = 0
    while more_batches and calls < max_more_calls:
        batch: list[str] = []
        while more_batches and len(batch) < 100:
            batch.extend(more_batches.pop(0))
        if not batch:
            break
        calls += 1
        url = listing_url("/api/morechildren", {
            "api_type": "json", "link_id": link_fullname,
            "children": ",".join(batch), "limit_children": "false"})
        try:
            data = fetch(url)
            for t in data["json"]["data"]["things"]:
                add_thing(t)
        except Exception as exc:  # keep going; partial is better than nothing
            sys.stderr.write(f"  [warn] morechildren batch failed: {exc}\n")
        time.sleep(0.4)
    return roots


def render_forest(roots: list[dict]) -> tuple[str, int]:
    """Render comment nodes to quoted Markdown; return (md, comment_count)."""
    out: list[str] = []
    count = 0

    def walk(node: dict, depth: int):
        nonlocal count
        d = node["data"]
        child_depth = depth
        if d:
            body = (d.get("body") or "").strip()
            if body and body not in ("[deleted]", "[removed]"):
                count += 1
                prefix = "> " * (depth + 1)
                author = d.get("author", "[deleted]")
                score = d.get("score", 0)
                quoted = "\n".join(f"{prefix}{ln}" for ln in body.splitlines())
                out.append(f"{prefix}**{author}** · {score} points\n{prefix.rstrip()}\n{quoted}")
                child_depth = depth + 1
        for r in node["replies"]:
            walk(r, child_depth)

    for r in roots:
        walk(r, 0)
    return "\n\n".join(out), count


# --------------------------------------------------------------------------- #
# per-post fetch + write
# --------------------------------------------------------------------------- #
def fetch_post(fetch, permalink: str, comment_sort: str, max_more_calls: int,
               with_comments: bool = True) -> dict:
    url = listing_url(permalink, {"limit": 500, "sort": comment_sort})
    data = fetch(url)
    post = data[0]["data"]["children"][0]["data"]
    if not with_comments:
        return {"post": post, "comments_md": "", "comment_count": 0}
    roots = build_comment_forest(fetch, post["name"], data[1]["data"]["children"],
                                 max_more_calls=max_more_calls)
    comments_md, ccount = render_forest(roots)
    return {"post": post, "comments_md": comments_md, "comment_count": ccount}


def write_post(out_dir: pathlib.Path, idx: int, permalink: str, res: dict,
               grep: str | None = None) -> dict:
    post = res["post"]
    body = (post.get("selftext") or "").strip()
    if post.get("url") and not body and not post.get("is_self"):
        body = f"(link/media post) {post.get('url')}"
    parts = [
        f"# {post.get('title', '')}\n",
        f"- author: u/{post.get('author', '')}",
        f"- subreddit: {post.get('subreddit_name_prefixed', '')}",
        f"- score: {post.get('score')} | upvote_ratio: {post.get('upvote_ratio')}",
        f"- comments: {post.get('num_comments')}",
        f"- posted: {iso(post.get('created_utc'))}",
        f"- url: {REDDIT}{permalink}",
        "",
        body if body else "(no body text)",
    ]
    if res["comments_md"]:
        parts += ["", f"## Comments ({res['comment_count']} rendered)", "", res["comments_md"]]
    fname = f"{idx:02d}_{slugify(post.get('title', ''))}.md"
    (out_dir / fname).write_text("\n".join(parts) + "\n")
    row = {k: None for k in ROW_KEYS}
    row.update({
        "n": idx, "title": post.get("title", ""), "author": post.get("author", ""),
        "subreddit": post.get("subreddit", ""),
        "score": post.get("score"), "num_comments": post.get("num_comments"),
        "comments_fetched": res["comment_count"], "posted": iso(post.get("created_utc")),
        "url": f"{REDDIT}{permalink}", "file": fname,
        "snippet": snippet_of(post),
        "grep_hits": (len(re.findall(grep, res["comments_md"], re.I))
                      if grep else None),
    })
    return row


# --------------------------------------------------------------------------- #
# index: append-only ledger + derived views
# --------------------------------------------------------------------------- #
def append_ledger(out_dir: pathlib.Path, row: dict) -> None:
    with (out_dir / "index.jsonl").open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def read_ledger(out_dir: pathlib.Path) -> list[dict]:
    p = out_dir / "index.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # a torn final line from a hard kill; skip it
    return rows


def rescan_grep(out_dir: pathlib.Path, pattern: str) -> list[dict]:
    """Recount `pattern` in the comment trees already on disk. No network.

    `--grep` at fetch time only helps if you knew the term before fetching. The
    natural follow-up ("which of these actually discuss X?") arrives afterwards,
    so this reruns the count over an existing run directory and rewrites the
    ledger and index in place.
    """
    rows = read_ledger(out_dir)
    if not rows:
        raise FileNotFoundError(
            f"{out_dir} has no index.jsonl — --rescan works on a directory a "
            f"previous fetch wrote. Pass the --out directory of that run.")
    pat = re.compile(pattern, re.I)
    scanned = 0
    for r in rows:
        f = out_dir / r["file"] if r.get("file") else None
        if not f or not f.exists():
            r["grep_hits"] = None
            continue
        text = f.read_text()
        # Count only inside the comments section, matching fetch-time semantics
        # (write_post greps res["comments_md"], never the post body).
        i = text.find("\n## Comments")
        r["grep_hits"] = len(pat.findall(text[i:])) if i != -1 else 0
        scanned += 1
    rows.sort(key=lambda r: r.get("n") or 0)
    with (out_dir / "index.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"rescanned {scanned} post file(s) for {pattern!r}", flush=True)
    return rows


def write_index(out_dir: pathlib.Path, rows: list[dict], header: str) -> None:
    (out_dir / "index.json").write_text(json.dumps(rows, indent=2))
    md = [f"# Reddit fetch — {header}, {len(rows)} posts", ""]
    for r in rows:
        hits = (f" · **{r['grep_hits']} grep hits**"
                if r.get("grep_hits") else "")
        md.append(f"{r['n']:>2}. [{r['title']}]({r['url']}) — u/{r['author']} · "
                  f"{r['score']}↑ · {r['num_comments']} comments "
                  f"({r['comments_fetched']} fetched){hits} · {r['posted']} · "
                  f"`{r['file']}`")
    (out_dir / "index.md").write_text("\n".join(md) + "\n")


# --------------------------------------------------------------------------- #
# Chrome sessions
# --------------------------------------------------------------------------- #
def in_session(op):
    """Run op(page, fetch) inside a FRESH Chrome; retry once on session expiry.

    Each unit of work owns its own browser (the `browser` project's documented
    idiom for run_with_auto_refresh) so a long run is a sequence of short
    sessions rather than one session degrading over hundreds of pages. The
    `fetch` closure is rebuilt per session — it must never outlive its page.
    """
    def _run():
        with logged_in_chrome.LoggedInChrome() as chrome:
            page = chrome.open(f"{REDDIT}/")
            time.sleep(2)
            return op(page, lambda u: fetch_json(page, u))
    return logged_in_chrome.run_with_auto_refresh(
        _run, slug="reddit.com", is_auth_error=is_auth_error)


def run_batch(permalinks: list[str], start_idx: int, out_dir: pathlib.Path,
              comment_sort: str, max_more_calls: int, with_comments: bool,
              grep: str | None = None) -> list[dict]:
    """Fetch one batch of posts in a single Chrome session. Returns written rows.

    This is the swap point: if per-batch in-process sessions ever prove
    unreliable, this body becomes a subprocess call without touching callers.
    """
    def op(page, fetch):
        rows = []
        for offset, pl in enumerate(permalinks):
            idx = start_idx + offset
            try:
                res = fetch_post(fetch, pl, comment_sort, max_more_calls, with_comments)
                row = write_post(out_dir, idx, pl, res, grep)
                append_ledger(out_dir, row)
                rows.append(row)
                hits = (f" grep:{row['grep_hits']}"
                        if row.get("grep_hits") else "")
                print(f"  {idx:>3}. [{row['score']}↑ {row['num_comments']}c "
                      f"({row['comments_fetched']} fetched){hits}] "
                      f"{row['title'][:70]}", flush=True)
            except Exception as exc:
                print(f"  {idx:>3}. FAILED {pl}: {exc}", flush=True)
            time.sleep(0.8)
        return rows
    return in_session(op)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help=f"{_TARGETS}. Omit when using --from.")
    ap.add_argument("-n", type=int, default=None,
                    help="how many posts you end up with (default 10; 100 for search)")

    g = ap.add_argument_group("listing modes (subreddit/home; mutually exclusive)")
    mode = g.add_mutually_exclusive_group()
    mode.add_argument("--top", nargs="?", const="all", choices=list(TIMEFRAMES),
                      help=f"top N posts in a timeframe {_opts(TIMEFRAMES)} (default all)")
    mode.add_argument("--new", action="store_true", help="most recent N posts")
    mode.add_argument("--timeline", action="store_true",
                      help="first N posts as rendered (personalized; the default)")
    mode.add_argument("--since", metavar="Nd|Nw|Nm",
                      help="every post in the last N days/weeks/months")

    s = ap.add_argument_group("search (requires --query)")
    s.add_argument("-q", "--query", action="append", metavar="TEXT",
                   help="search text; REPEAT for multi-query fan-out (deduped, "
                        "each candidate tagged with the queries that found it)")
    s.add_argument("--sort", default="relevance", choices=list(SEARCH_SORTS),
                   help=f"search sort {_opts(SEARCH_SORTS)} (default relevance)")
    s.add_argument("--time", default="all", choices=list(TIMEFRAMES),
                   help=f"search timeframe {_opts(TIMEFRAMES)} (default all); "
                        "'--top week' is the same as '--sort top --time week'")
    s.add_argument("--per-query", type=int, default=25,
                   help=f"results pulled per query before dedupe (default 25; "
                        f"Reddit caps search paging near {SEARCH_HARD_CAP}). Going "
                        f"below {MIN_USEFUL_PER_QUERY} drops the low-score long "
                        f"tail, which is where cross-tool comparison threads live")
    s.add_argument("--nsfw", action="store_true", help="include over-18 results")
    s.add_argument("--discover", default="both", choices=list(DISCOVERY),
                   help=f"where candidates come from {_opts(DISCOVERY)} (default "
                        "both). 'web' uses Tavily restricted to reddit.com, which "
                        "finds threads whose TITLES do not contain your terms "
                        "(Reddit's own search cannot search comments); results are "
                        "then hydrated with real Reddit metadata. 'both' unions "
                        "them for best recall, and degrades to reddit-only if "
                        "TAVILY_API_KEY is unset. Use 'reddit' to avoid the "
                        "metered API entirely")
    s.add_argument("--web-results", type=int, default=15,
                   help="results per query from the web backend (default 15)")
    s.add_argument("--expand-subs", nargs="?", type=int, const=3, default=0,
                   metavar="N",
                   help="after the first pass, re-run every query scoped to the N "
                        "busiest subreddits it landed in (default 3 when given). "
                        "USE IT when your query is a minority topic INSIDE those "
                        "subs — 'X vs Y' lands in r/X and you want the rare r/X "
                        "threads about Y, which site-wide relevance buries at 15 "
                        "upvotes but scoped search ranks #1. SKIP IT when your "
                        "query IS what the sub is about ('hermes agent memory' in "
                        "r/hermesagent): measured, that added 45 posts and zero "
                        "on-topic hits, because scoped search just re-returns the "
                        "sub. Off by default for that reason")

    f = ap.add_argument_group("candidate filters")
    f.add_argument("--match", action="append", metavar="REGEX",
                   help="keep posts whose title+body matches; repeat = OR. For AND "
                        "use one lookahead regex: '(?=.*a)(?=.*b)'")
    f.add_argument("--exclude", action="append", metavar="REGEX",
                   help="drop posts whose title+body matches; repeat = OR")
    f.add_argument("--min-score", type=int, default=0, help="minimum upvotes (default 0)")
    f.add_argument("--min-comments", type=int, default=0,
                   help="minimum comment count (default 0)")
    f.add_argument("--grep", metavar="REGEX",
                   help="after fetching, count matches of REGEX in each post's "
                        "comment tree and report them in index.md. Reddit cannot "
                        "search comments, so this is the only way to find threads "
                        "where the discussion — not the title — mentions your term")

    p2 = ap.add_argument_group("phase 2 — fetch already-chosen posts")
    p2.add_argument("--from", dest="from_", metavar="PATH",
                    help=f"permalinks source: {_FROM_SOURCES}")
    p2.add_argument("--select", metavar="SPEC", default=None,
                    help="1-based rows from --from: '1-30', '1-10,15,40-', 'all' "
                         "(default all)")
    p2.add_argument("--rescan", action="store_true",
                    help="recount --grep over posts a previous run already "
                         "fetched, then rewrite index.md/index.json in place. "
                         "Needs --from <run dir> and --grep. No network, no "
                         "browser — use it for the follow-up question 'which of "
                         "these threads actually discuss X?'")

    o = ap.add_argument_group("output / robustness")
    o.add_argument("--out", help="output dir (default: a fresh temp dir)")
    o.add_argument("--resume", action="store_true",
                   help="skip posts already in <out>/index.jsonl; needs --out. "
                        "Phase-2 only — re-running a search is cheap and its "
                        "ranking drifts, so row numbers would not be stable.")
    o.add_argument("--batch-size", type=int, default=25,
                   help="posts per Chrome session (default 25); a fresh browser "
                        "session is started per batch")
    o.add_argument("--comments", action=argparse.BooleanOptionalAction, default=None,
                   help="fetch full comment trees (default: on for listings and "
                        "--from, off for --query search)")
    o.add_argument("--comment-sort", default="confidence", choices=list(COMMENT_SORTS),
                   help=f"comment sort {_opts(COMMENT_SORTS)} "
                        "(default confidence = Reddit 'Best')")
    o.add_argument("--max-more-calls", type=int, default=80,
                   help="cap on morechildren expansion requests per post (default 80)")
    o.add_argument("--json", action="store_true",
                   help="print a machine-readable run manifest on stdout (paths and "
                        "counts, not the index itself — that is on disk)")
    return ap


def validate(ap: argparse.ArgumentParser, args) -> None:
    """Reject before any side effect, naming the valid set so one retry converges."""
    listing_used = [f for f, v in zip(LISTING_MODE_FLAGS,
                                      (args.top, args.new, args.timeline, args.since)) if v]
    search_only_used = [flag for flag, dest in SEARCH_ONLY
                        if getattr(args, dest) != ap.get_default(dest)]

    if args.rescan:
        missing = ([] if args.from_ else ["--from <run dir>"]) \
            + ([] if args.grep else ["--grep REGEX"])
        if missing:
            ap.error(f"--rescan needs {' and '.join(missing)}. It recounts a "
                     f"pattern over posts an earlier run already fetched, e.g. "
                     f"--from /tmp/myrun --grep '\\bpi\\b' --rescan")
        return

    if args.from_:
        bad = ([f"target {args.target!r}"] if args.target else []) \
            + (["--query"] if args.query else []) + listing_used
        if bad:
            ap.error(f"--from is phase 2 (fetch already-chosen posts) and takes no "
                     f"target, --query, or listing mode; got {', '.join(bad)}. "
                     f"Drop those, or drop --from.")
        if args.resume and not args.out:
            ap.error("--resume needs --out DIR — the directory of the run you are "
                     "resuming. Without --out every run gets a fresh temp dir with "
                     "nothing to resume; the previous run printed its directory on "
                     "its last line.")
        return

    if args.select is not None:
        ap.error("--select picks rows from a --from file. To cap a fresh search or "
                 "listing, use -n.")
    if not args.target:
        ap.error(f"need a target or --from. Valid targets: {_TARGETS}. For phase 2, "
                 f"pass --from <{_FROM_SOURCES}>.")

    kind, _ = normalize_target(args.target)

    if args.query:
        if listing_used:
            ap.error(f"--query (search) cannot be combined with listing modes "
                     f"({', '.join(LISTING_MODE_FLAGS)}); got {', '.join(listing_used)}. "
                     f"Search uses --sort {_opts(SEARCH_SORTS)} and "
                     f"--time {_opts(TIMEFRAMES)} instead — e.g. '--top week' "
                     f"becomes '--sort top --time week'.")
        if kind == "home":
            ap.error("'home' cannot be searched. Search targets are 'all' "
                     "(site-wide) or a subreddit name (which restricts the search "
                     "to that subreddit).")
    else:
        if search_only_used:
            one = len(search_only_used) == 1
            ap.error(f"{', '.join(search_only_used)} "
                     f"{'only applies' if one else 'only apply'} to search and "
                     f"{'needs' if one else 'need'} --query. For a subreddit "
                     f"listing use --top {_opts(TIMEFRAMES)}, --new, --timeline, "
                     f"or --since Nd|Nw|Nm.")
        if kind == "all":
            ap.error("target 'all' is search-only; add --query TEXT. Reddit has no "
                     "site-wide listing endpoint — pick a subreddit, or use 'home' "
                     "with --timeline.")
        if kind == "home" and listing_used and not args.timeline:
            ap.error(f"'home' supports only --timeline. For a subreddit the valid "
                     f"modes are --top {_opts(TIMEFRAMES)}, --new, --timeline, or "
                     f"--since Nd|Nw|Nm.")

    if args.resume:
        ap.error("--resume is a phase-2 feature: it needs --from (a fixed row order) "
                 "so numbering stays stable. Re-running a search or listing is cheap "
                 "and idempotent — just run it again.")

    for flag, pats in (("--match", args.match), ("--exclude", args.exclude),
                       ("--grep", [args.grep] if args.grep else [])):
        for p in pats or []:
            try:
                re.compile(p)
            except re.error as e:
                ap.error(f"{flag} {p!r} is not a valid regex: {e}")

    if args.since:
        try:
            parse_since(args.since)
        except ValueError as e:
            ap.error(str(e))


def main():
    ap = build_parser()
    args = ap.parse_args()
    validate(ap, args)

    py, script = sys.executable, str(pathlib.Path(__file__).resolve())

    # Post-hoc grep over an existing run: no network, no browser, returns early.
    if args.rescan:
        d = pathlib.Path(args.from_).expanduser()
        if d.is_file():
            d = d.parent
        if not d.is_dir():
            ap.error(f"--rescan needs a run directory; {args.from_} is not one.")
        try:
            rows = rescan_grep(d, args.grep)
        except FileNotFoundError as e:
            ap.error(str(e))
        write_index(d, rows, f"rescan grep={args.grep!r}")
        hit = [r for r in rows if r.get("grep_hits")]
        print(f"\n{len(hit)}/{len(rows)} posts mention {args.grep!r} in comments:",
              flush=True)
        for r in sorted(hit, key=lambda r: -(r["grep_hits"] or 0)):
            print(f"  {r['grep_hits']:>4} × {r['title'][:66]}", flush=True)
        print(f"\nindex: {d / 'index.md'}", flush=True)
        if args.json:
            print(json.dumps({"out_dir": str(d), "mode": "rescan",
                              "grep": args.grep,
                              "counts": {"posts": len(rows), "with_hits": len(hit)},
                              "index_md": str(d / "index.md")}, indent=2))
        return

    searching = bool(args.query)
    kind, sub = normalize_target(args.target) if args.target else ("from", None)

    if args.n is None:
        args.n = 100 if searching else 10
    if args.comments is None:
        args.comments = not searching
    if not searching and not args.from_ and not any(
            [args.top, args.new, args.timeline, args.since]):
        args.timeline = True

    # ---- resolve output dir + label ----
    rows_from: list[dict] | None = None
    if args.from_:
        try:
            rows_from = load_from(args.from_)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
            ap.error(str(e))
        try:
            picked = set(parse_select(args.select or "all", len(rows_from)))
        except ValueError as e:
            ap.error(f"--select must be comma-separated 1-based ranges over the "
                     f"{len(rows_from)} rows in {args.from_}, e.g. '1-30', "
                     f"'1-10,15,40-', 'all'. Got {str(e)!r}.")
        # An explicit --select IS the cap; -n only applies when taking everything,
        # otherwise a 13-row selection silently becomes 10.
        rows_from = [r for r in rows_from if r["n"] in picked]
        if (args.select or "all").strip().lower() == "all":
            rows_from = rows_from[:args.n]
        label = f"from/{pathlib.Path(args.from_).name}"
        prefix = f"reddit_fetch_{slugify(pathlib.Path(args.from_).stem, 30)}_"
    elif searching:
        label = f"search/{args.discover}/{args.sort}/{args.time}"
        prefix = (f"reddit_search_{slugify(args.query[0], 30)}_"
                  f"{('in_' + sub) if sub else 'all'}_")
        # The two settings that quietly wreck a site-wide search. sort=top ranks
        # by score among loose matches, so a weak query returns whatever is
        # popular on Reddit rather than what is relevant.
        if args.sort == "top" and not sub and args.discover != "web":
            print("  WARNING: --sort top on a site-wide search ranks by upvotes "
                  "among loose matches, so short or ambiguous queries return "
                  "unrelated popular posts. Use --sort relevance unless you "
                  "specifically want Reddit's biggest threads.", flush=True)
        if args.per_query < MIN_USEFUL_PER_QUERY and args.discover != "web":
            print(f"  WARNING: --per-query {args.per_query} is below "
                  f"{MIN_USEFUL_PER_QUERY}; the low-score long tail (where "
                  f"cross-tool comparison threads live) will be cut off. Prefer "
                  f"more -q variants over a smaller --per-query.", flush=True)
    else:
        label = (f"top/{args.top}" if args.top else "new" if args.new
                 else f"since/{args.since}" if args.since else "timeline")
        prefix = f"reddit_{sub or 'home'}_"

    out_dir = pathlib.Path(args.out).expanduser() if args.out else pathlib.Path(
        tempfile.mkdtemp(prefix=prefix))
    out_dir.mkdir(parents=True, exist_ok=True)

    header = (f"target={args.target or args.from_} mode={label} "
              f"{'queries=' + str(len(args.query)) + ' ' if searching else ''}"
              f"n={args.n} comments={'on' if args.comments else 'off'}")
    print(f"{header} -> {out_dir}", flush=True)

    manifest = {"out_dir": str(out_dir), "mode": label, "queries": args.query or [],
                "counts": {}, "next_command": None}

    # ---- phase A: selection (one short session) ----
    if rows_from is not None:
        permalinks = [permalink_of(r["url"]) for r in rows_from]
    else:
        # Web discovery is plain HTTP, so it runs before Chrome is launched;
        # only the metadata hydration needs a session.
        web_links: dict[str, list[str]] = {}
        if searching and args.discover in ("web", "both"):
            try:
                web_links = web_discover(args.query, args.web_results, sub)
            except RuntimeError as e:
                # 'both' is a superset request, so falling back to Reddit-only
                # still satisfies most of it — never make a missing optional key
                # a hard failure on the default path. 'web' asked for web only,
                # so there is nothing to degrade to.
                if args.discover == "web":
                    ap.error(str(e))
                print(f"  NOTE: web discovery unavailable, continuing with Reddit "
                      f"search only.\n        {e}", flush=True)
                args.discover = "reddit"

        def select_op(page, fetch):
            if searching:
                posts: list[dict] = []
                if args.discover in ("reddit", "both"):
                    posts = search_posts(fetch, args.query, sub, args.sort,
                                         args.time, args.per_query, args.nsfw)
                if web_links:
                    merge_posts(posts, hydrate(fetch, web_links))
                if args.expand_subs:
                    posts = expand_by_subreddit(
                        fetch, posts, args.query, args.sort, args.time,
                        args.per_query, args.nsfw, args.expand_subs)
                if args.discover == "both" or args.expand_subs:
                    posts = rank_candidates(posts)
                    print(f"  total unique after all passes: {len(posts)} "
                          f"(ranked; multi-pass hits first)", flush=True)
                return posts
            if args.timeline:
                url = f"{REDDIT}/" if kind == "home" else f"{REDDIT}/r/{sub}/"
                return fetch_dom_order(page, url, args.n)
            if args.top:
                return paginate(fetch, f"/r/{sub}/top", {"t": args.top}, args.n)
            if args.new:
                return paginate(fetch, f"/r/{sub}/new", {}, args.n)
            return paginate(fetch, f"/r/{sub}/new", {},
                            n=max(args.n, 500), cutoff=parse_since(args.since))

        found = in_session(select_op)
        manifest["counts"]["unique"] = len(found)

        if args.match or args.exclude or args.min_score or args.min_comments:
            found, dropped = filter_candidates(found, args.match, args.exclude,
                                               args.min_score, args.min_comments)
            if any(dropped.values()):
                print("  dropped: " + ", ".join(f"{k}={v}" for k, v in dropped.items() if v),
                      flush=True)
        found = found[:args.n]
        manifest["counts"]["kept"] = len(found)

        if searching:
            rows = [candidate_row(p, i) for i, p in enumerate(found, 1)]
            manifest.update(write_candidates(out_dir, rows, {
                "header": " | ".join(f'"{q}"' for q in args.query),
                "counts": f"sort={args.sort} t={args.time} "
                          f"scope={'r/' + sub if sub else 'site-wide'} — "
                          f"{len(rows)} candidates",
                "queries": args.query, "sort": args.sort, "time": args.time,
                "scope": sub or "all", "per_query": args.per_query,
            }))
            print(f"\nDONE: {len(rows)} candidates -> {manifest['candidates_md']}",
                  flush=True)
            if not args.comments:
                nxt = (f"{py} {script} --from {out_dir}/candidates.json "
                       f"--select 1-{min(30, len(rows)) or 1} --out {out_dir} --resume")
                manifest["next_command"] = nxt
                print(f"\nnext: {nxt}", flush=True)
                if args.json:
                    print(json.dumps(manifest, indent=2))
                return
            permalinks = [permalink_of(r["url"]) for r in rows]
        else:
            permalinks = [p["permalink"] for p in found]

    # ---- phase B: post fetch, one Chrome session per batch ----
    existing = read_ledger(out_dir) if args.resume else []
    done_urls = {r["url"] for r in existing}
    if done_urls:
        print(f"resume: skipping {len(done_urls)} already fetched", flush=True)
    todo = [pl for pl in permalinks if f"{REDDIT}{pl}" not in done_urls]
    next_idx = max((r["n"] for r in existing), default=0) + 1

    print(f"selected {len(todo)} posts; fetching"
          f"{'' if args.comments else ' (no comments)'}...", flush=True)

    batches = [todo[i:i + args.batch_size] for i in range(0, len(todo), args.batch_size)]
    for bi, batch in enumerate(batches, 1):
        print(f"batch {bi}/{len(batches)} "
              f"(posts {next_idx}-{next_idx + len(batch) - 1})", flush=True)
        try:
            run_batch(batch, next_idx, out_dir, args.comment_sort,
                      args.max_more_calls, args.comments, args.grep)
        except Exception as exc:
            print(f"  batch {bi} died ({exc}); retrying once with a fresh session",
                  flush=True)
            fetched = {r["url"] for r in read_ledger(out_dir)}
            rest = [pl for pl in batch if f"{REDDIT}{pl}" not in fetched]
            try:
                run_batch(rest, next_idx + (len(batch) - len(rest)), out_dir,
                          args.comment_sort, args.max_more_calls, args.comments,
                          args.grep)
            except Exception as exc2:
                print(f"  batch {bi} failed again ({exc2}); moving on", flush=True)
        next_idx += len(batch)
        if bi < len(batches):
            time.sleep(2)

    rows = read_ledger(out_dir)
    write_index(out_dir, rows, header)
    manifest["counts"]["fetched"] = len(rows)
    manifest["counts"]["failed"] = max(0, len(todo) + len(existing) - len(rows))
    manifest["index_json"] = str(out_dir / "index.json")
    manifest["index_md"] = str(out_dir / "index.md")

    print(f"\nDONE: {len(rows)} posts -> {out_dir}", flush=True)
    print(f"index: {out_dir / 'index.md'}", flush=True)
    if args.json:
        print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

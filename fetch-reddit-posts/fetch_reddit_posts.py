#!/usr/bin/env python
"""Fetch N Reddit posts + ALL their comments into a temp folder — no LLM calls.

Drives a logged-in Chrome (the `browser` project's logged_in_chrome) and issues
same-origin `fetch()` calls from inside the page, so Reddit's JSON endpoints work
(plain curl/urllib gets 403 from most IPs, and the home feed needs your login).

Selection modes (pick one):
  --top [all|year|month|week|day|hour]  Top N posts in a timeframe (default all)
  --new                                 Most recent N posts
  --timeline                            First N posts as they render when you open
                                        the page (the personalized default sort)
  --since <Nd|Nw|Nm>                    Every post from the last N days/weeks/months
                                        (uses 'new', filtered by timestamp)

Target is a subreddit (name, r/name, or full URL) or the literal `home`
(your logged-in Reddit home feed; only valid with --timeline).

Each post is written as one Markdown file (post body + full nested comments,
including expanded "load more" stubs). A compact index is printed to stdout and
written as index.md / index.json. Nothing is sent to an LLM.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
import time
from datetime import datetime, timezone

from browser.src.logged_in_chrome import LoggedInChrome

REDDIT = "https://www.reddit.com"
# In-page fetch: runs in the reddit.com origin with cookies, returns raw text.
_FETCH_JS = "async (u) => { const r = await fetch(u, {credentials:'include'}); return await r.text(); }"


# --------------------------------------------------------------------------- #
# target / arg parsing
# --------------------------------------------------------------------------- #
def normalize_target(target: str) -> tuple[str, str | None]:
    """Return ('home', None) or ('subreddit', 'AiAutomations')."""
    t = target.strip()
    if t.lower() in ("home", "frontpage", "/"):
        return "home", None
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


def slugify(text: str, maxlen: int = 50) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return (s[:maxlen] or "post").strip("_")


def iso(ts: float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# --------------------------------------------------------------------------- #
# listing: JSON endpoints (top / new / since)
# --------------------------------------------------------------------------- #
def fetch_listing(fetchjson, base_url: str, n: int, t: str | None = None,
                  cutoff: float | None = None, hard_cap: int = 1000) -> list[dict]:
    """Paginate a Reddit listing JSON endpoint, returning up to n t3 posts.

    If cutoff is set, keep every post with created_utc >= cutoff and stop once
    older posts appear (n acts as a safety cap)."""
    posts: list[dict] = []
    after = None
    while len(posts) < min(n, hard_cap):
        url = f"{base_url}.json?limit=100&raw_json=1"
        if t:
            url += f"&t={t}"
        if after:
            url += f"&after={after}"
        data = json.loads(fetchjson(url))
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
            posts.append(d)
        after = data.get("data", {}).get("after")
        if stop or not after:
            break
        time.sleep(0.4)
    return posts[:n]


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
def build_comment_forest(fetchjson, link_fullname: str, top_children: list[dict],
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
        url = (f"{REDDIT}/api/morechildren.json?api_type=json&raw_json=1"
               f"&link_id={link_fullname}&children={','.join(batch)}&limit_children=false")
        try:
            data = json.loads(fetchjson(url))
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
def fetch_post(fetchjson, permalink: str, comment_sort: str, max_more_calls: int) -> dict:
    url = f"{REDDIT}{permalink.rstrip('/')}.json?limit=500&sort={comment_sort}&raw_json=1"
    data = json.loads(fetchjson(url))
    post = data[0]["data"]["children"][0]["data"]
    roots = build_comment_forest(fetchjson, post["name"], data[1]["data"]["children"],
                                 max_more_calls=max_more_calls)
    comments_md, ccount = render_forest(roots)
    return {"post": post, "comments_md": comments_md, "comment_count": ccount}


def write_post(out_dir: pathlib.Path, idx: int, permalink: str, res: dict) -> dict:
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
    return {
        "n": idx, "title": post.get("title", ""), "author": post.get("author", ""),
        "score": post.get("score"), "num_comments": post.get("num_comments"),
        "comments_fetched": res["comment_count"], "posted": iso(post.get("created_utc")),
        "url": f"{REDDIT}{permalink}", "file": fname,
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="subreddit (name, r/name, or URL) or 'home'")
    ap.add_argument("-n", type=int, default=10, help="number of posts (default 10)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--top", nargs="?", const="all",
                      choices=["all", "year", "month", "week", "day", "hour"],
                      help="top N posts in a timeframe (default 'all')")
    mode.add_argument("--new", action="store_true", help="most recent N posts")
    mode.add_argument("--timeline", action="store_true",
                      help="first N posts as rendered (personalized default sort)")
    mode.add_argument("--since", metavar="Nd|Nw|Nm",
                      help="every post in the last N days/weeks/months")
    ap.add_argument("--out", help="output dir (default: a fresh temp dir)")
    ap.add_argument("--comment-sort", default="confidence",
                    choices=["confidence", "top", "new", "controversial", "old", "qa"],
                    help="comment sort (default confidence = Reddit 'Best')")
    ap.add_argument("--max-more-calls", type=int, default=80,
                    help="cap on morechildren expansion requests per post (default 80)")
    args = ap.parse_args()

    kind, sub = normalize_target(args.target)

    # default mode = timeline
    if not any([args.top, args.new, args.timeline, args.since]):
        args.timeline = True
    if kind == "home" and not args.timeline:
        ap.error("'home' target only supports --timeline")

    out_dir = pathlib.Path(args.out) if args.out else pathlib.Path(
        tempfile.mkdtemp(prefix=f"reddit_{sub or 'home'}_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    label = ("home/timeline" if kind == "home" else
             f"top/{args.top}" if args.top else
             "new" if args.new else
             f"since/{args.since}" if args.since else
             "timeline")
    print(f"target={args.target} mode={label} n={args.n} -> {out_dir}", flush=True)

    with LoggedInChrome() as chrome:
        page = chrome.open(f"{REDDIT}/")
        time.sleep(2)
        fetchjson = lambda u: page.evaluate(_FETCH_JS, u)  # noqa: E731

        # ---- select posts ----
        if args.timeline:
            url = f"{REDDIT}/" if kind == "home" else f"{REDDIT}/r/{sub}/"
            selected = fetch_dom_order(page, url, args.n)
            permalinks = [it["permalink"] for it in selected]
        elif args.top:
            posts = fetch_listing(fetchjson, f"{REDDIT}/r/{sub}/top", args.n, t=args.top)
            permalinks = [p["permalink"] for p in posts]
        elif args.new:
            posts = fetch_listing(fetchjson, f"{REDDIT}/r/{sub}/new", args.n)
            permalinks = [p["permalink"] for p in posts]
        else:  # since
            cutoff = parse_since(args.since)
            posts = fetch_listing(fetchjson, f"{REDDIT}/r/{sub}/new",
                                  n=max(args.n, 500), cutoff=cutoff)
            permalinks = [p["permalink"] for p in posts]

        print(f"selected {len(permalinks)} posts; fetching comments...", flush=True)

        # ---- fetch each post + comments ----
        index = []
        for i, pl in enumerate(permalinks, 1):
            try:
                res = fetch_post(fetchjson, pl, args.comment_sort, args.max_more_calls)
                row = write_post(out_dir, i, pl, res)
                index.append(row)
                print(f"  {i:>3}. [{row['score']}↑ {row['num_comments']}c "
                      f"({row['comments_fetched']} fetched)] {row['title'][:70]}", flush=True)
            except Exception as exc:
                print(f"  {i:>3}. FAILED {pl}: {exc}", flush=True)
            time.sleep(0.8)

    # ---- write index ----
    (out_dir / "index.json").write_text(json.dumps(index, indent=2))
    md = [f"# Reddit fetch — {args.target} ({label}), {len(index)} posts", ""]
    for r in index:
        md.append(f"{r['n']:>2}. [{r['title']}]({r['url']}) — u/{r['author']} · "
                  f"{r['score']}↑ · {r['num_comments']} comments "
                  f"({r['comments_fetched']} fetched) · {r['posted']} · `{r['file']}`")
    (out_dir / "index.md").write_text("\n".join(md) + "\n")

    print(f"\nDONE: {len(index)} posts -> {out_dir}", flush=True)
    print(f"index: {out_dir / 'index.md'}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Search Zhihu, and fetch whole questions (ALL answers) into a folder — no LLM calls.

Drives a logged-in Chrome (the `browser` project's logged_in_chrome) and issues
same-origin `fetch()` calls from inside the page, so Zhihu's JSON endpoints work
(plain curl/urllib gets 403, and a logged-out page silently serves only the first
few answers instead of erroring).

Two things this does:

  SEARCH    find discussions with one or more -q/--query variants.  Search is
            TWO-PHASE by design: phase 1 writes a cheap candidate list
            (candidates.md / .json — question title, hits, votes, snippet; no
            answer bodies), you pick the rows worth having, then phase 2
            (--from ... --select ...) fetches those questions in full.
            Answers scatter across questions and a popular question is 50+
            answers, so triaging before fetching is the whole point.  Phase 1
            prints the exact phase-2 command to run next.

  FETCH     pull every answer of a question, by URL or bare id, straight past
            phase 1 when you already know what you want.

Each fetched question is written as one Markdown file (YAML frontmatter + every
answer, author, vote count and date), alongside an append-only `index.jsonl`
ledger and derived `index.md` / `index.json`.  Nothing is sent to an LLM.

Examples:
  # phase 1: search with two query variants, candidates only
  %(prog)s -q "hy4 preview 实际体验" -q "混元 hy4 实测"

  # phase 2: fetch the questions you picked
  %(prog)s --from <dir> --select 1-5 --out <dir> --resume

  # skip search entirely — one question, every answer
  %(prog)s https://www.zhihu.com/question/2076674418479257365
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
import time
from datetime import datetime

from clipping import normalize
from clipping.fetchers import zhihu

# Row schema shared by candidates.json (phase 1) and index.json (phase 2), so
# --from needs no special-casing between them.
ROW_KEYS = ("n", "kind", "title", "question_id", "content_id", "author", "hits",
            "votes", "answers", "answers_fetched", "created", "url", "file",
            "found_by", "snippet", "truncated")

ORDERS = ("default", "updated")
ANSWER_SORTS = ("votes", "original")
KINDS = ("question", "article")


def _opts(values) -> str:
    return " | ".join(values)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def parse_select(spec: str, total: int) -> list[int]:
    """Parse "1-5,8,11-" into 1-based indices, clamped to `total`."""
    picked: list[int] = []
    for part in (p.strip() for p in spec.split(",") if p.strip()):
        if "-" in part:
            lo, _, hi = part.partition("-")
            start = int(lo) if lo.strip() else 1
            end = int(hi) if hi.strip() else total
        else:
            start = end = int(part)
        if start < 1 or end < start:
            raise ValueError(f"bad --select range {part!r}")
        picked.extend(range(start, min(end, total) + 1))
    out, seen = [], set()
    for i in picked:
        if i not in seen:
            seen.add(i)
            out.append(i)
    if not out:
        raise ValueError(f"--select {spec!r} selected nothing (1..{total} available)")
    return out


def question_id_of(target: str) -> str | None:
    """Extract a question id from a URL, an answer URL, or a bare numeric id."""
    target = target.strip()
    if target.isdigit():
        return target
    m = re.search(r"/question/(\d+)", target)
    return m.group(1) if m else None


def slugify(text: str, maxlen: int = 60) -> str:
    """Filesystem-safe stem. Zhihu titles are CJK, so keep the characters."""
    text = re.sub(r"[\s/\\:*?\"<>|]+", "_", (text or "").strip())
    text = re.sub(r"_+", "_", text).strip("_")
    # Budget in BYTES: normalize.FILENAME_MAX_BYTES is a byte budget and CJK is
    # 3 bytes a character, so a character count would blow past it.
    while len(text.encode("utf-8")) > maxlen and text:
        text = text[:-1]
    return text or "untitled"


def snippet_of(text: str, limit: int = 200) -> str:
    flat = re.sub(r"\s+", " ", (text or "").strip())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def demote_headings(md: str, by: int = 2) -> str:
    """Push every heading in an answer body `by` levels down.

    Answers are written under a `##` heading per author, and Zhihu bodies often
    contain their own `##` sections — which would render as siblings of the
    author headings and silently break the document's structure. Fenced code is
    skipped so a `# comment` inside ``` stays a comment.
    """
    out, in_fence = [], False
    for line in (md or "").split("\n"):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
        elif not in_fence:
            m = re.match(r"^(#{1,6})(\s)", line)
            if m:
                line = "#" * min(6, len(m.group(1)) + by) + line[len(m.group(1)):]
        out.append(line)
    return "\n".join(out)


def new_out_dir(explicit: str | None) -> pathlib.Path:
    """Resolve the output dir; default to a self-reaping temp dir.

    Without --out the run lands in $TMPDIR, which macOS clears on its own
    (`com.apple.bsd.dirhelper`, daily, files untouched for 3+ days). That is the
    right default for a scratch fetch, but it means a run is NOT a place to keep
    anything — hence the notice, so a caller coming back later is not surprised
    by a directory that quietly evaporated. Deleting at exit would be wrong: the
    files are the deliverable and are read after this process is gone.
    """
    if explicit:
        p = pathlib.Path(explicit).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    p = pathlib.Path(tempfile.mkdtemp(prefix="zhihu-"))
    print(f"note: writing to a temp dir the OS reaps after ~3 days ({p}).\n"
          f"      pass --out DIR to keep the results.", flush=True)
    return p


# --------------------------------------------------------------------------- #
# phase 1 — search → candidates
# --------------------------------------------------------------------------- #
def collect_candidates(queries: list[str], per_query: int,
                       with_articles: bool) -> list[dict]:
    """Run every query in ONE browser session; group answers by question."""
    def op(page, fetch):
        found: list[dict] = []
        for q in queries:
            print(f"  searching: {q}", flush=True)
            hits = zhihu.search_zhihu(fetch, q, limit=per_query)
            print(f"    {len(hits)} result(s)", flush=True)
            found.extend(hits)
            time.sleep(0.6)
        return found

    records = zhihu.zhihu_api_session(op)

    questions: dict[str, dict] = {}
    articles: dict[str, dict] = {}
    for r in records:
        if r["type"] == "answer":
            row = questions.setdefault(r["question_id"], {
                "kind": "question", "question_id": r["question_id"],
                "content_id": "", "title": r["question_title"], "author": "",
                "hits": 0, "votes": 0, "created": r["created"],
                "url": zhihu.question_web_url(r["question_id"]),
                "found_by": [], "snippet": "",
            })
            row["hits"] += 1
            # Votes on the best-ranked answer we saw — a proxy for how much
            # substance the question holds, since the real answer count is only
            # knowable by paging it (question detail is signed-only).
            row["votes"] = max(row["votes"], r["voteup_count"])
            if r["found_by"] not in row["found_by"]:
                row["found_by"].append(r["found_by"])
            if not row["snippet"]:
                row["snippet"] = snippet_of(r["excerpt"])
        elif r["type"] == "article" and with_articles:
            row = articles.setdefault(r["id"], {
                "kind": "article", "question_id": "", "content_id": r["id"],
                "title": r["title"], "author": r["author"], "hits": 0,
                "votes": r["voteup_count"], "created": r["created"],
                "url": r["url"], "found_by": [],
                "snippet": snippet_of(r["excerpt"] or r.get("contentMarkdown", "")),
                "contentMarkdown": r.get("contentMarkdown", ""),
            })
            row["hits"] += 1
            if r["found_by"] not in row["found_by"]:
                row["found_by"].append(r["found_by"])

    rows = sorted(questions.values(), key=lambda r: (-r["hits"], -r["votes"]))
    rows += sorted(articles.values(), key=lambda r: -r["votes"])
    for n, row in enumerate(rows, 1):
        row["n"] = n
        row["found_by"] = ",".join(row["found_by"])
    return rows


def write_candidates(out_dir: pathlib.Path, rows: list[dict], meta: dict) -> None:
    (out_dir / "candidates.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "query.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# Zhihu search — {meta['header']}", f"# {meta['counts']}", ""]
    for r in rows:
        md.append(f"{r['n']:>3}. [{r['title']}]({r['url']})")
        bits = [f"[{r['kind']}]"]
        if r["kind"] == "question":
            bits.append(f"{r['hits']} hit(s)")
            bits.append(f"top answer {r['votes']}↑")
        else:
            bits += [r["author"], f"{r['votes']}↑"]
        bits.append(r["created"])
        if r.get("found_by"):
            bits.append(f"found_by: {r['found_by']}")
        md.append(f"     {' · '.join(b for b in bits if b)}")
        if r.get("snippet"):
            md.append(f"     > {r['snippet']}")
        md.append("")
    (out_dir / "candidates.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def load_from(src: str) -> list[dict]:
    """Load rows from a run dir, or a candidates.json / index.json from one."""
    p = pathlib.Path(src).expanduser()
    if p.is_dir():
        for name in ("candidates.json", "index.json"):
            if (p / name).exists():
                p = p / name
                break
        else:
            raise FileNotFoundError(
                f"{src} has no candidates.json or index.json — pass the --out "
                f"directory of a previous run, or a question URL/id directly.")
    rows = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{p} holds no rows")
    return rows


# --------------------------------------------------------------------------- #
# phase 2 — fetch → markdown
# --------------------------------------------------------------------------- #
def render_question(result: dict, answers: list[dict], row: dict) -> str:
    frontmatter = normalize.build_clean_frontmatter({
        "title": result["title"] or f"知乎问题 {result['question_id']}",
        "site": "知乎",
        "source": result["url"],
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "answers": len(answers),
        "found_by": row.get("found_by") or None,
    })
    parts = [f"# {result['title']}", "",
             f"- 来源: {result['url']}",
             f"- 回答数: {len(answers)}", ""]
    for a in answers:
        heading = f"## {a['author'] or '匿名'}"
        if a["author_headline"]:
            heading += f" — {a['author_headline']}"
        parts.append(heading)
        meta = f"{a['voteup_count']} 赞同 · {a['comment_count']} 评论 · {a['created']}"
        if a["truncated"]:
            meta += " · ⚠️ 正文可能被截断"
        parts += [f"*{meta}* · [原文]({a['url']})", "",
                  demote_headings(a["contentMarkdown"]) or "(空)", "", "---", ""]
    return normalize.render_markdown_with_frontmatter(frontmatter, "\n".join(parts))


def render_article(row: dict) -> str:
    frontmatter = normalize.build_clean_frontmatter({
        "title": row["title"], "site": "知乎专栏", "source": row["url"],
        "author": row.get("author") or None,
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "found_by": row.get("found_by") or None,
    })
    body = row.get("contentMarkdown") or row.get("snippet") or "(空)"
    parts = [f"# {row['title']}", "",
             f"- 作者: {row.get('author') or '未知'}",
             f"- 来源: {row['url']}",
             f"- 赞同: {row.get('votes', 0)}",
             "",
             "> 正文取自知乎搜索索引，可能不是全文。",
             "", body]
    return normalize.render_markdown_with_frontmatter(frontmatter, "\n".join(parts))


def fetch_rows(rows: list[dict], out_dir: pathlib.Path, *, max_answers: int | None,
               order: str, answer_sort: str, min_votes: int,
               headless: bool) -> list[dict]:
    """Fetch every selected row in one browser session. Returns written rows."""
    questions = [r for r in rows if r.get("kind", "question") == "question"]
    articles = [r for r in rows if r.get("kind") == "article"]
    written: list[dict] = []

    # Articles need no network: the search index already carried their body.
    for row in articles:
        out = dict.fromkeys(ROW_KEYS)
        fname = f"{row['n']:02d}_{slugify(row['title'])}.md"
        (out_dir / fname).write_text(render_article(row), encoding="utf-8")
        out.update({**{k: row.get(k) for k in ROW_KEYS if k in row},
                    "n": row["n"], "kind": "article", "file": fname,
                    "answers": 0, "answers_fetched": 0})
        append_ledger(out_dir, out)
        written.append(out)
        print(f"  {row['n']:>3}. [article] {row['title'][:60]}", flush=True)

    if not questions:
        return written

    def op(page, fetch):
        done = []
        for row in questions:
            qid = row["question_id"]
            try:
                result = zhihu.fetch_zhihu_question(
                    fetch, qid, max_answers=max_answers, order=order)
                answers = [a for a in result["answers"]
                           if a["voteup_count"] >= min_votes]
                if answer_sort == "votes":
                    answers.sort(key=lambda a: -a["voteup_count"])
                title = result["title"] or row.get("title") or f"question {qid}"
                result["title"] = title
                fname = f"{row['n']:02d}_{slugify(title)}.md"
                (out_dir / fname).write_text(
                    render_question(result, answers, row), encoding="utf-8")
                out = dict.fromkeys(ROW_KEYS)
                out.update({
                    "n": row["n"], "kind": "question", "title": title,
                    "question_id": qid, "content_id": "",
                    "author": "", "hits": row.get("hits"),
                    "votes": max((a["voteup_count"] for a in answers), default=0),
                    "answers": len(result["answers"]),
                    "answers_fetched": len(answers),
                    "created": row.get("created", ""), "url": result["url"],
                    "file": fname, "found_by": row.get("found_by"),
                    "snippet": snippet_of(
                        answers[0]["contentMarkdown"] if answers else ""),
                    "truncated": sum(1 for a in answers if a["truncated"]),
                })
                append_ledger(out_dir, out)
                done.append(out)
                flag = f" ⚠️{out['truncated']} truncated" if out["truncated"] else ""
                print(f"  {row['n']:>3}. [{out['answers_fetched']}/{out['answers']} "
                      f"answers{flag}] {title[:60]}", flush=True)
            except Exception as exc:  # one bad question must not kill the run
                print(f"  {row['n']:>3}. FAILED {qid}: {exc}", flush=True)
            time.sleep(0.8)
        return done

    return written + zhihu.zhihu_api_session(op, headless=headless)


# --------------------------------------------------------------------------- #
# index: append-only ledger + derived views
# --------------------------------------------------------------------------- #
def append_ledger(out_dir: pathlib.Path, row: dict) -> None:
    with (out_dir / "index.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_ledger(out_dir: pathlib.Path) -> list[dict]:
    p = out_dir / "index.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # a torn final line from a hard kill; skip it
    return rows


def write_index(out_dir: pathlib.Path, rows: list[dict], header: str) -> None:
    rows = sorted(rows, key=lambda r: r.get("n") or 0)
    (out_dir / "index.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# Zhihu fetch — {header}, {len(rows)} item(s)", ""]
    for r in rows:
        if r.get("kind") == "article":
            md.append(f"{r['n']:>2}. [{r['title']}]({r['url']}) — [article] "
                      f"{r.get('author', '')} · {r.get('votes', 0)}↑ · `{r['file']}`")
        else:
            warn = (f" · ⚠️ {r['truncated']} truncated" if r.get("truncated") else "")
            md.append(f"{r['n']:>2}. [{r['title']}]({r['url']}) — "
                      f"{r.get('answers_fetched', 0)}/{r.get('answers', 0)} answers · "
                      f"top {r.get('votes', 0)}↑{warn} · `{r['file']}`")
    (out_dir / "index.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?",
                    help="a question URL (https://www.zhihu.com/question/<id>), an "
                         "answer URL, or a bare question id — fetches it directly, "
                         "skipping search. Omit when using -q or --from.")

    s = ap.add_argument_group("phase 1 — search")
    s.add_argument("-q", "--query", action="append", metavar="TEXT",
                   help="search query; repeat for variants (hits are deduped and "
                        "tagged with which query found them)")
    s.add_argument("--per-query", type=int, default=40, metavar="N",
                   help="max search results per query (default 40)")
    s.add_argument("--articles", action=argparse.BooleanOptionalAction, default=True,
                   help="include 专栏 articles in candidates (default: yes). Their "
                        "body comes from the search index, not a second fetch.")

    p2 = ap.add_argument_group("phase 2 — fetch chosen rows")
    p2.add_argument("--from", dest="from_", metavar="PATH",
                    help="a run directory, or a candidates.json / index.json from one")
    p2.add_argument("--select", metavar="SPEC",
                    help="1-based rows to fetch, e.g. '1-5,8,11-' (default: all)")

    f = ap.add_argument_group("answer selection")
    f.add_argument("--max-answers", type=int, default=None, metavar="N",
                   help="stop after N answers per question (default: all of them)")
    f.add_argument("--min-votes", type=int, default=0, metavar="N",
                   help="drop answers below N upvotes (default 0)")
    f.add_argument("--order", default="default", choices=list(ORDERS),
                   help=f"Zhihu's own feed order: {_opts(ORDERS)} (default: default)")
    f.add_argument("--sort", dest="answer_sort", default="votes",
                   choices=list(ANSWER_SORTS),
                   help=f"answer order in the written file: {_opts(ANSWER_SORTS)} "
                        f"(default: votes)")

    o = ap.add_argument_group("output")
    o.add_argument("--out", help="output dir. Default: a fresh $TMPDIR dir, which "
                                 "macOS reaps after ~3 days — pass this to keep the "
                                 "results, or to add to an existing run")
    o.add_argument("--resume", action="store_true",
                   help="skip rows already in the run's index.jsonl")
    o.add_argument("--headed", action="store_true",
                   help="show the browser window (debugging)")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if not any((args.target, args.query, args.from_)):
        ap.error("give a question URL/id, -q/--query to search, or --from to fetch "
                 "a previous run's candidates")
    if args.target and args.query:
        ap.error("a direct question target and -q/--query are mutually exclusive")

    # ---- phase 1: search -------------------------------------------------- #
    if args.query:
        out_dir = new_out_dir(args.out)
        print(f"searching zhihu ({len(args.query)} query variant(s))…", flush=True)
        rows = collect_candidates(args.query, args.per_query, args.articles)
        if not rows:
            print("no results — try different query wording", flush=True)
            return 1
        n_q = sum(1 for r in rows if r["kind"] == "question")
        meta = {"queries": args.query,
                "header": " | ".join(args.query),
                "counts": f"{n_q} question(s), {len(rows) - n_q} article(s)"}
        write_candidates(out_dir, rows, meta)
        print(f"\n{meta['counts']} → {out_dir}/candidates.md", flush=True)
        print("\nTriage that file, then fetch the rows worth having:\n"
              f"  {sys.argv[0]} --from {out_dir} --select 1-5 --out {out_dir} --resume",
              flush=True)
        return 0

    # ---- phase 2: fetch --------------------------------------------------- #
    if args.target:
        qid = question_id_of(args.target)
        if not qid:
            ap.error(f"could not read a question id from {args.target!r} — expected "
                     f"a /question/<id> URL or a bare numeric id")
        rows = [{"n": 1, "kind": "question", "question_id": qid, "title": "",
                 "url": zhihu.question_web_url(qid), "found_by": None}]
        header = f"question {qid}"
        out_dir = new_out_dir(args.out)
    else:
        rows = load_from(args.from_)
        out_dir = new_out_dir(args.out or args.from_)
        if args.select:
            picked = set(parse_select(args.select, len(rows)))
            rows = [r for r in rows if r["n"] in picked]
        header = f"{len(rows)} selected row(s)"

    existing = read_ledger(out_dir)
    if args.resume:
        done = {r.get("n") for r in existing}
        before = len(rows)
        rows = [r for r in rows if r["n"] not in done]
        if before != len(rows):
            print(f"resume: skipping {before - len(rows)} already-fetched row(s)",
                  flush=True)
    if not rows:
        print("nothing left to fetch", flush=True)
        write_index(out_dir, existing, header)
        return 0

    print(f"fetching {len(rows)} row(s) → {out_dir}", flush=True)
    written = fetch_rows(rows, out_dir, max_answers=args.max_answers,
                         order=args.order, answer_sort=args.answer_sort,
                         min_votes=args.min_votes, headless=not args.headed)
    write_index(out_dir, read_ledger(out_dir), header)
    total = sum(r.get("answers_fetched") or 0 for r in written)
    print(f"\nwrote {len(written)} file(s), {total} answer(s) → {out_dir}/index.md",
          flush=True)
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())

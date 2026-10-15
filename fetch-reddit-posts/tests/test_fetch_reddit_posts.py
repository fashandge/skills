"""Pure-unit tests — no Chrome, no network.

The first two classes are regressions for the two defects that motivated the
search rewrite: `.json`-appended-to-a-query-string URLs, and 429s surfacing as
an opaque JSONDecodeError.
"""
import json
from urllib.parse import parse_qs, urlparse

import pytest

import fetch_reddit_posts as frp


class TestListingUrl:
    """Defect 1: URLs were built by appending '.json' to a base string."""

    def test_json_precedes_the_query_string(self):
        url = frp.listing_url("/r/x/search", {"q": "a b", "t": "all", "restrict_sr": "on"})
        assert ".json?" in url
        assert url.count("?") == 1
        assert "&t=all.json" not in url

    def test_params_are_encoded_not_concatenated(self):
        url = frp.listing_url("/search", {"q": 'pi vs hermes & "quotes"', "t": "year"})
        q = parse_qs(urlparse(url).query)
        assert q["q"] == ['pi vs hermes & "quotes"']
        assert q["t"] == ["year"]
        assert q["raw_json"] == ["1"]

    def test_none_and_false_params_are_dropped(self):
        url = frp.listing_url("/search", {"q": "x", "after": None, "restrict_sr": False})
        assert "after" not in url and "restrict_sr" not in url

    def test_listing_and_permalink_paths(self):
        assert frp.listing_url("/r/x/top", {"t": "month"}).startswith(
            f"{frp.REDDIT}/r/x/top.json?")
        assert frp.listing_url("/r/x/comments/abc/slug/", {"limit": 500}).startswith(
            f"{frp.REDDIT}/r/x/comments/abc/slug.json?")

    def test_a_path_carrying_a_query_string_is_rejected(self):
        with pytest.raises(ValueError, match="path, not a query string"):
            frp.listing_url("/search?q=already", {"t": "all"})


class FakePage:
    """Stands in for a Playwright page: replays a scripted list of responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def evaluate(self, js, url):
        self.calls += 1
        return self.responses.pop(0)


class TestFetchJson:
    """Defect 2: no status handling, so a 429's empty body looked like a parse bug."""

    def test_200_parses(self):
        page = FakePage([{"status": 200, "body": '{"ok": 1}'}])
        assert frp.fetch_json(page, "u") == {"ok": 1}

    def test_429_waits_for_the_reported_reset_then_succeeds(self):
        waits = []
        frp.RATE = frp.RateLimit(max_cooldown=600, sleep=waits.append)
        page = FakePage([
            {"status": 429, "reset": "42", "remaining": "0", "body": ""},
            {"status": 200, "body": '{"ok": 1}'},
        ])
        assert frp.fetch_json(page, "u") == {"ok": 1}
        assert waits == [43]  # the reported reset plus a 1 s margin, nothing blind

    def test_429_past_the_budget_raises_at_once_without_backoff(self):
        waits = []
        frp.RATE = frp.RateLimit(max_cooldown=100, sleep=waits.append)
        page = FakePage([{"status": 429, "reset": "540", "body": ""}])
        with pytest.raises(frp.RedditHTTPError) as e:
            frp.fetch_json(page, "u")
        assert e.value.status == 429 and page.calls == 1 and waits == []
        assert "--resume" in str(e.value)

    def test_429_without_headers_uses_retry_after_then_the_fallback(self):
        waits = []
        frp.RATE = frp.RateLimit(max_cooldown=600, sleep=waits.append)
        page = FakePage([
            {"status": 429, "retryAfter": "5", "body": ""},
            {"status": 429, "body": ""},
            {"status": 200, "body": "{}"},
        ])
        frp.fetch_json(page, "u")
        assert waits == [6, frp.FALLBACK_COOLDOWN + 1]

    def test_5xx_still_backs_off(self, monkeypatch):
        monkeypatch.setattr(frp.time, "sleep", lambda s: None)
        page = FakePage([{"status": 503, "body": ""}, {"status": 200, "body": "{}"}])
        assert frp.fetch_json(page, "u") == {}
        assert page.calls == 2

    def test_every_response_updates_the_budget(self):
        frp.RATE = frp.RateLimit(clock=lambda: 1000.0)
        frp.fetch_json(FakePage([{"status": 200, "remaining": "57.0", "reset": "300",
                                  "body": "{}"}]), "u")
        assert frp.RATE.remaining == 57 and frp.RATE.reset_at == 1300

    def test_403_does_not_retry_and_names_the_refresh_command(self):
        page = FakePage([{"status": 403, "body": ""}])
        with pytest.raises(frp.RedditHTTPError) as e:
            frp.fetch_json(page, "u")
        assert page.calls == 1
        assert frp.is_auth_error(e.value)
        assert "refresh_state.py reddit.com" in str(e.value)

    def test_404_names_the_likely_cause(self):
        page = FakePage([{"status": 404, "body": ""}])
        with pytest.raises(frp.RedditHTTPError) as e:
            frp.fetch_json(page, "u")
        assert e.value.status == 404
        assert "no such subreddit or post" in str(e.value)

    def test_html_body_served_as_200_is_not_a_bare_decode_error(self):
        page = FakePage([{"status": 200, "body": "<!doctype html><html>login</html>"}])
        with pytest.raises(frp.RedditHTTPError) as e:
            frp.fetch_json(page, "u")
        assert "expected JSON" in str(e.value)


class TestParseSelect:
    def test_all_and_default(self):
        assert frp.parse_select("all", 3) == [1, 2, 3]
        assert frp.parse_select("", 3) == [1, 2, 3]

    def test_ranges_singletons_and_open_ended(self):
        assert frp.parse_select("1-3", 10) == [1, 2, 3]
        assert frp.parse_select("1-2,5,9-", 10) == [1, 2, 5, 9, 10]

    def test_clamped_to_total_and_deduped(self):
        assert frp.parse_select("1-99,2", 3) == [1, 2, 3]

    def test_garbage_raises_with_the_offending_token(self):
        with pytest.raises(ValueError, match=r"1\.\.3"):
            frp.parse_select("1..3", 10)


class TestLoadFrom:
    def _write(self, tmp_path, name, text):
        p = tmp_path / name
        p.write_text(text)
        return p

    def test_candidates_json(self, tmp_path):
        p = self._write(tmp_path, "candidates.json",
                        '[{"n": 1, "url": "https://www.reddit.com/r/x/comments/a/t/"}]')
        assert load_urls(frp.load_from(str(p))) == ["https://www.reddit.com/r/x/comments/a/t/"]

    def test_a_directory_resolves_candidates_then_index(self, tmp_path):
        self._write(tmp_path, "index.json", '[{"n": 1, "url": "https://r/i"}]')
        assert frp.load_from(str(tmp_path))[0]["url"] == "https://r/i"
        self._write(tmp_path, "candidates.json", '[{"n": 1, "url": "https://r/c"}]')
        assert frp.load_from(str(tmp_path))[0]["url"] == "https://r/c"

    def test_newline_list_with_comments_and_blanks(self, tmp_path):
        p = self._write(tmp_path, "list.txt",
                        "# a comment\n\n/r/x/comments/a/t/\n/r/y/comments/b/u/\n")
        rows = frp.load_from(str(p))
        assert [r["n"] for r in rows] == [1, 2]
        assert rows[0]["url"] == "/r/x/comments/a/t/"

    def test_missing_path_names_the_valid_sources(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="run directory"):
            frp.load_from(str(tmp_path / "nope.json"))

    def test_permalink_of_strips_only_the_origin(self):
        assert frp.permalink_of("https://www.reddit.com/r/x/comments/a/t/") == \
            "/r/x/comments/a/t/"
        assert frp.permalink_of("/r/x/comments/a/t/") == "/r/x/comments/a/t/"


def load_urls(rows):
    return [r["url"] for r in rows]


class TestFilterCandidates:
    POSTS = [
        {"title": "Cursor vs Claude", "selftext": "long writeup", "score": 100,
         "num_comments": 50},
        {"title": "meme about cursor", "selftext": "", "score": 5, "num_comments": 1},
        {"title": "unrelated", "selftext": "nothing here", "score": 900,
         "num_comments": 400},
    ]

    def test_no_filters_keeps_everything(self):
        kept, dropped = frp.filter_candidates(self.POSTS, [], [], 0, 0)
        assert len(kept) == 3 and not any(dropped.values())

    def test_match_is_ored_across_patterns(self):
        kept, _ = frp.filter_candidates(self.POSTS, ["cursor", "unrelated"], [], 0, 0)
        assert len(kept) == 3
        kept, dropped = frp.filter_candidates(self.POSTS, ["cursor"], [], 0, 0)
        assert len(kept) == 2 and dropped["match"] == 1

    def test_exclude_and_thresholds_report_their_own_counts(self):
        kept, dropped = frp.filter_candidates(self.POSTS, [], ["meme"], 50, 10)
        assert [p["title"] for p in kept] == ["Cursor vs Claude", "unrelated"]
        assert dropped["exclude"] == 1

    def test_match_is_case_insensitive_and_covers_body(self):
        kept, _ = frp.filter_candidates(self.POSTS, ["LONG WRITEUP"], [], 0, 0)
        assert len(kept) == 1


class TestParseSince:
    def test_units(self):
        now = frp.time.time()
        assert now - frp.parse_since("7d") == pytest.approx(7 * 86400, abs=5)
        assert now - frp.parse_since("2w") == pytest.approx(14 * 86400, abs=5)
        assert now - frp.parse_since("1m") == pytest.approx(30 * 86400, abs=5)

    def test_garbage_raises(self):
        with pytest.raises(ValueError, match="7d / 2w / 1m"):
            frp.parse_since("7 years")


class TestMergePosts:
    """Union of discovery passes: reddit search + web + per-subreddit expansion."""

    def test_dedupes_by_id_and_unions_found_by(self):
        a = [{"id": "x", "_found_by": ["q1"], "_rank_best": 5}]
        b = [{"id": "x", "_found_by": ["w1"], "_rank_best": 2},
             {"id": "y", "_found_by": ["w1"], "_rank_best": 3}]
        out = frp.merge_posts(a, b)
        assert [p["id"] for p in out] == ["x", "y"]
        assert out[0]["_found_by"] == ["q1", "w1"]
        assert out[0]["_rank_best"] == 2

    def test_does_not_duplicate_a_label(self):
        a = [{"id": "x", "_found_by": ["q1"], "_rank_best": 1}]
        frp.merge_posts(a, [{"id": "x", "_found_by": ["q1"], "_rank_best": 9}])
        assert a[0]["_found_by"] == ["q1"]

    def test_preserves_first_seen_order(self):
        a = [{"id": "1", "_found_by": [], "_rank_best": 1},
             {"id": "2", "_found_by": [], "_rank_best": 2}]
        frp.merge_posts(a, [{"id": "3", "_found_by": [], "_rank_best": 1}])
        assert [p["id"] for p in a] == ["1", "2", "3"]


class TestRankCandidates:
    """Multi-pass hits must survive the -n cut, or web/expansion finds get lost."""

    def test_web_finds_are_never_starved_by_a_larger_pass(self):
        posts = ([{"id": f"r{i}", "_found_by": ["q1"], "_rank_best": i} for i in range(20)]
                 + [{"id": "w", "_found_by": ["w1"], "_rank_best": 99}])
        top = [p["id"] for p in frp.rank_candidates(posts)][:3]
        assert "w" in top, "a lone web result must not be crowded out by 20 reddit hits"

    def test_round_robin_alternates_across_sources(self):
        posts = [{"id": "r1", "_found_by": ["q1"], "_rank_best": 1},
                 {"id": "r2", "_found_by": ["q1"], "_rank_best": 2},
                 {"id": "w1", "_found_by": ["w1"], "_rank_best": 1},
                 {"id": "e1", "_found_by": ["s1.1"], "_rank_best": 1}]
        assert [p["id"] for p in frp.rank_candidates(posts)] == ["w1", "r1", "e1", "r2"]

    def test_within_a_bucket_multi_pass_then_rank_wins(self):
        posts = [{"id": "a", "_found_by": ["q1"], "_rank_best": 9},
                 {"id": "b", "_found_by": ["q1", "q2"], "_rank_best": 9},
                 {"id": "c", "_found_by": ["q1"], "_rank_best": 2}]
        assert [p["id"] for p in frp.rank_candidates(posts)] == ["b", "c", "a"]

    def test_every_post_survives_ranking(self):
        posts = [{"id": str(i), "_found_by": ["w1" if i % 3 else "q1"], "_rank_best": i}
                 for i in range(25)]
        assert len(frp.rank_candidates(posts)) == 25

    def test_expansion_and_web_labels_are_distinct_kinds(self):
        assert frp._pass_kind("w1") == "web"
        assert frp._pass_kind("s2.1") == "expand"
        assert frp._pass_kind("q1") == "reddit"


class TestTopSubreddits:
    def test_ranks_by_frequency(self):
        posts = ([{"subreddit": "hermesagent"}] * 3 + [{"subreddit": "PiCodingAgent"}] * 2
                 + [{"subreddit": "LocalLLaMA"}])
        assert frp.top_subreddits(posts, 2) == ["hermesagent", "PiCodingAgent"]

    def test_ignores_blank_subreddits(self):
        assert frp.top_subreddits([{"subreddit": ""}, {"other": 1}], 3) == []


class TestWebDiscover:
    """The web backend filters by DOMAIN only, so subreddit scoping happens here."""

    def _fake_tavily(self, monkeypatch, urls):
        import io

        payload = json.dumps({"results": [{"url": u} for u in urls]}).encode()
        monkeypatch.setattr(frp.urllib.request, "urlopen",
                            lambda req, timeout=0: io.BytesIO(payload))
        monkeypatch.setattr(frp, "secret", lambda name: "fake-key")

    def test_keeps_only_threads_and_strips_query_strings(self, monkeypatch):
        self._fake_tavily(monkeypatch, [
            "https://www.reddit.com/r/PiCodingAgent/comments/a/t/?utm_source=x",
            "https://www.reddit.com/r/hermesagent",          # landing page
            "https://www.reddit.com/r/hermesagent/hot",      # listing page
        ])
        got = frp.web_discover(["q"], 5)
        assert list(got) == ["/r/PiCodingAgent/comments/a/t/"]

    def test_subreddit_scoping_drops_off_target_hits(self, monkeypatch):
        self._fake_tavily(monkeypatch, [
            "https://www.reddit.com/r/PiCodingAgent/comments/a/t/",
            "https://www.reddit.com/r/handbags/comments/b/hermes_bag/",
            "https://www.reddit.com/r/GreekMythology/comments/c/hermes/",
        ])
        got = frp.web_discover(["hermes"], 5, sub="PiCodingAgent")
        assert list(got) == ["/r/PiCodingAgent/comments/a/t/"]

    def test_subreddit_match_is_case_insensitive(self, monkeypatch):
        self._fake_tavily(monkeypatch,
                          ["https://www.reddit.com/r/picodingagent/comments/a/t/"])
        assert len(frp.web_discover(["q"], 5, sub="PiCodingAgent")) == 1

    def test_missing_key_raises_with_the_fix(self, monkeypatch):
        monkeypatch.setattr(frp, "secret", lambda name: None)
        with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
            frp.web_discover(["q"], 5)


class TestSecret:
    def test_environment_wins(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "from-env")
        assert frp.secret("TAVILY_API_KEY") == "from-env"

    def test_reads_export_lines_from_secrets_env(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ZZ_TEST_KEY", raising=False)
        home = tmp_path
        (home / ".config").mkdir()
        (home / ".config/secrets.env").write_text(
            '# comment\nexport ZZ_TEST_KEY="abc123"\nexport OTHER=1\n')
        monkeypatch.setattr(frp.pathlib.Path, "home", staticmethod(lambda: home))
        assert frp.secret("ZZ_TEST_KEY") == "abc123"
        assert frp.secret("MISSING_KEY") is None


class TestGrepHits:
    def _res(self, comments_md):
        return {"post": {"title": "t", "author": "a", "subreddit": "s", "score": 1,
                         "num_comments": 2, "created_utc": 1, "selftext": "body"},
                "comments_md": comments_md, "comment_count": 2}

    def test_counts_matches_case_insensitively(self, tmp_path):
        row = frp.write_post(tmp_path, 1, "/r/x/comments/a/t/",
                             self._res("I use Pi daily\nand PI again"), grep=r"\bpi\b")
        assert row["grep_hits"] == 2

    def test_none_when_no_grep_requested(self, tmp_path):
        row = frp.write_post(tmp_path, 1, "/r/x/comments/a/t/", self._res("x"))
        assert row["grep_hits"] is None


class TestRescanGrep:
    """Post-hoc grep: the follow-up question arrives after the fetch."""

    def _run_dir(self, tmp_path):
        (tmp_path / "01_a.md").write_text(
            "# A\n\n- score: 1\n\nbody mentions pi twice: pi pi\n"
            "\n## Comments (2 rendered)\n\n> **u1** · 5 points\n> I use Pi daily\n"
            "\n> **u2** · 2 points\n> PI again here\n")
        (tmp_path / "02_b.md").write_text("# B\n\nnothing\n\n## Comments (0 rendered)\n\n")
        rows = [{"n": 1, "title": "A", "author": "x", "subreddit": "s", "score": 1,
                 "num_comments": 2, "comments_fetched": 2, "posted": "", "file": "01_a.md",
                 "url": "u1", "grep_hits": None, "snippet": "", "found_by": None},
                {"n": 2, "title": "B", "author": "x", "subreddit": "s", "score": 1,
                 "num_comments": 0, "comments_fetched": 0, "posted": "", "file": "02_b.md",
                 "url": "u2", "grep_hits": None, "snippet": "", "found_by": None}]
        with (tmp_path / "index.jsonl").open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        return tmp_path

    def test_counts_only_inside_the_comments_section(self, tmp_path):
        d = self._run_dir(tmp_path)
        rows = frp.rescan_grep(d, r"\bpi\b")
        # 2 in comments; the 3 in the post body must NOT count (matches
        # fetch-time semantics, which grep only comments_md).
        assert rows[0]["grep_hits"] == 2
        assert rows[1]["grep_hits"] == 0

    def test_rewrites_the_ledger_so_a_second_scan_sees_fresh_values(self, tmp_path):
        d = self._run_dir(tmp_path)
        frp.rescan_grep(d, r"\bpi\b")
        assert frp.read_ledger(d)[0]["grep_hits"] == 2
        frp.rescan_grep(d, r"nomatchhere")
        assert frp.read_ledger(d)[0]["grep_hits"] == 0

    def test_missing_post_file_yields_none_not_a_crash(self, tmp_path):
        d = self._run_dir(tmp_path)
        (d / "01_a.md").unlink()
        assert frp.rescan_grep(d, "pi")[0]["grep_hits"] is None

    def test_directory_without_a_ledger_is_rejected(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="index.jsonl"):
            frp.rescan_grep(tmp_path, "pi")


class TestPaginate:
    def test_follows_after_cursor_dedupes_and_caps(self):
        def child(i):
            return {"kind": "t3", "data": {"id": f"p{i}", "created_utc": 1000}}

        pages = [
            {"data": {"children": [child(1), child(2)], "after": "t3_2"}},
            {"data": {"children": [child(2), child(3)], "after": None}},
        ]
        seen_urls = []

        def fetch(url):
            seen_urls.append(url)
            return pages[len(seen_urls) - 1]

        got = frp.paginate(fetch, "/r/x/new", {}, n=10)
        assert [p["id"] for p in got] == ["p1", "p2", "p3"]
        assert "after=t3_2" in seen_urls[1]

    def test_cutoff_stops_at_the_first_older_post(self):
        pages = [{"data": {"children": [
            {"kind": "t3", "data": {"id": "a", "created_utc": 5000}},
            {"kind": "t3", "data": {"id": "b", "created_utc": 100}},
        ], "after": "x"}}]
        got = frp.paginate(lambda u: pages[0], "/r/x/new", {}, n=10, cutoff=1000)
        assert [p["id"] for p in got] == ["a"]


# --------------------------------------------------------------------------- #
# Rate limits: on 2026-10-14 a burst spent Reddit's 100-request window and 6 of
# 13 posts were silently dropped (each burned ~60 s of blind backoff, then the
# run printed only "DONE: 2 posts"). Waits must follow Reddit's own reset
# time, stay within a run-wide budget, and every loss must be named.
# --------------------------------------------------------------------------- #
def r429(pl="x"):
    return frp.RedditHTTPError(429, pl, "rate limited")


def items(*pls, start=1):
    return list(enumerate(pls, start))


def url(pl):
    return f"{frp.REDDIT}{pl}"


class ScriptedBatches:
    """fetch_batch stand-in: each call consumes one scripted outcome.

    An outcome is {permalink: exc-or-None}; posts mapped to None (or absent)
    land in the ledger. A 429 defers the rest of the call, as run_batch does.
    An outcome that is an Exception instance is raised (a dead session).
    """

    def __init__(self, out_dir, outcomes):
        self.out_dir, self.outcomes, self.calls = out_dir, list(outcomes), []

    def __call__(self, batch):
        self.calls.append([pl for _, pl in batch])
        outcome = self.outcomes.pop(0) if self.outcomes else {}
        if isinstance(outcome, Exception):
            raise outcome
        errors = {}
        for pos, (idx, pl) in enumerate(batch):
            exc = outcome.get(pl)
            if exc is None:
                frp.append_ledger(self.out_dir, {"n": idx, "url": url(pl)})
                continue
            errors[pl] = exc
            if frp.is_rate_limited(exc):
                return errors, batch[pos + 1:]
        return errors, []


@pytest.fixture(autouse=True)
def fresh_rate_limit(monkeypatch):
    """Each test gets its own budget; the real one would sleep."""
    monkeypatch.setattr(frp, "RATE", frp.RateLimit(sleep=lambda s: None))


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


class TestRateLimit:
    def make(self, remaining, reset, **kw):
        clock, waits = Clock(), []
        rl = frp.RateLimit(clock=clock, sleep=waits.append, **kw)
        rl.update(remaining, reset)
        return rl, clock, waits

    def test_no_pacing_while_plenty_remain(self):
        rl, _, waits = self.make("99.0", "540")
        rl.pace()
        assert waits == []

    def test_low_budget_spreads_the_rest_over_the_window(self):
        rl, _, waits = self.make("4", "200")
        rl.pace()
        assert waits == [50]  # 200 s left / 4 requests

    def test_exhausted_budget_waits_out_the_window(self):
        rl, _, waits = self.make("0", "120")
        rl.pace()
        assert waits == [120]

    def test_count_goes_stale_once_the_window_resets(self):
        rl, clock, waits = self.make("2", "30")
        clock.t = 31
        rl.pace()
        assert waits == [] and rl.remaining is None

    def test_unknown_budget_never_pauses(self):
        rl, _, waits = self.make(None, None)
        rl.pace()
        assert waits == []

    def test_cooldown_waits_exactly_until_reset_within_budget(self):
        rl, _, waits = self.make("0", "540", max_cooldown=600)
        assert rl.cooldown(540) is True
        assert waits == [541] and rl.spent == 541

    def test_cooldown_refuses_rather_than_overrun_the_budget(self):
        rl, _, waits = self.make("0", "540", max_cooldown=600)
        rl.cooldown(540)
        assert rl.cooldown(540) is False  # a second full window does not fit
        assert waits == [541]

    def test_zero_budget_never_waits(self):
        rl, _, waits = self.make("0", "5", max_cooldown=0)
        assert rl.cooldown(5) is False and waits == []


class TestFetchPosts:
    def run(self, tmp_path, outcomes, its, batch_size=25):
        waits = []
        fb = ScriptedBatches(tmp_path, outcomes)
        failed, skipped = frp.fetch_posts(its, tmp_path, batch_size, fb,
                                          sleep=waits.append)
        return failed, skipped, fb

    def test_clean_run_reports_nothing(self, tmp_path):
        failed, skipped, fb = self.run(tmp_path, [{}], items("/a", "/b"))
        assert (failed, skipped) == ({}, [])

    def test_posts_keep_the_numbers_they_were_given(self, tmp_path):
        self.run(tmp_path, [{}], items("/a", "/b", "/c", start=7))
        assert sorted(r["n"] for r in frp.read_ledger(tmp_path)) == [7, 8, 9]

    def test_an_escaped_429_fails_that_post_and_skips_the_rest(self, tmp_path):
        failed, skipped, fb = self.run(
            tmp_path, [{"/b": r429()}], items("/a", "/b", "/c", "/d", "/e"),
            batch_size=3)
        assert failed == {url("/b"): "HTTP 429"}
        assert skipped == [url("/c"), url("/d"), url("/e")]
        assert len(fb.calls) == 1  # later batches cost no requests

    def test_other_errors_fail_only_their_post(self, tmp_path):
        err = frp.RedditHTTPError(404, "/a", "no such post")
        failed, skipped, fb = self.run(tmp_path, [{"/a": err}, {}],
                                       items("/a", "/b", "/c"), batch_size=2)
        assert failed == {url("/a"): "HTTP 404"} and skipped == []
        assert len(fb.calls) == 2

    def test_dead_session_retries_once_then_names_what_is_lost(self, tmp_path):
        frp.append_ledger(tmp_path, {"n": 1, "url": url("/a")})  # landed before the crash
        boom = RuntimeError("browser closed")
        failed, _, fb = self.run(tmp_path, [boom, boom], items("/a", "/b"))
        assert fb.calls == [["/a", "/b"], ["/b"]]
        assert failed == {url("/b"): "session died: browser closed"}

    def test_dead_session_recovers_on_the_retry(self, tmp_path):
        failed, _, fb = self.run(tmp_path, [RuntimeError("x"), {}], items("/a"))
        assert failed == {} and len(fb.calls) == 2


class TestRunBatch:
    def test_a_429_stops_the_batch_and_defers_the_rest(self, monkeypatch, tmp_path):
        tried = []

        def fake_fetch_post(fetch, pl, *a):
            tried.append(pl)
            if pl == "/b":
                raise r429(pl)
            return {"post": {"title": pl}, "comments_md": "", "comment_count": 0}

        monkeypatch.setattr(frp, "in_session", lambda op: op(None, None))
        monkeypatch.setattr(frp, "fetch_post", fake_fetch_post)
        monkeypatch.setattr(frp.time, "sleep", lambda s: None)
        errors, deferred = frp.run_batch(items("/a", "/b", "/c", "/d"), tmp_path,
                                         "confidence", 0, False)
        assert tried == ["/a", "/b"]
        assert list(errors) == ["/b"] and frp.is_rate_limited(errors["/b"])
        assert deferred == [(3, "/c"), (4, "/d")]

    def test_posts_are_paced_at_least_1_5_s_apart(self, monkeypatch, tmp_path):
        sleeps = []
        monkeypatch.setattr(frp, "in_session", lambda op: op(None, None))
        monkeypatch.setattr(frp, "fetch_post", lambda *a: {
            "post": {"title": "t"}, "comments_md": "", "comment_count": 0})
        monkeypatch.setattr(frp.time, "sleep", sleeps.append)
        frp.run_batch(items("/a", "/b", "/c"), tmp_path, "confidence", 0, False)
        assert len(sleeps) == 3 and min(sleeps) >= 1.5


class TestMoreChildrenRateLimit:
    def test_a_429_while_expanding_comments_fails_the_post_not_truncates_it(self):
        top = [{"kind": "more", "data": {"children": ["c1", "c2"]}}]

        def fetch(u):
            raise r429(u)

        with pytest.raises(frp.RedditHTTPError) as e:
            frp.build_comment_forest(fetch, "t3_x", top)
        assert e.value.status == 429


class TestDoneLine:
    def test_clean_run_is_unchanged(self, tmp_path):
        assert frp.done_line(5, tmp_path, {}, []) == f"DONE: 5 posts -> {tmp_path}"

    def test_names_every_failed_and_skipped_url_on_the_one_line(self, tmp_path):
        line = frp.done_line(2, tmp_path, {url("/a"): "HTTP 429", url("/b"): "HTTP 404"},
                             [url("/c")])
        assert "\n" not in line
        assert line.startswith("DONE: 2 posts, 2 failed (")
        for u in (url("/a"), url("/b"), url("/c")):
            assert u in line
        assert "[HTTP 429]" in line and "1 skipped" in line and "--resume" in line

    def test_index_md_lists_failed_and_skipped(self, tmp_path):
        frp.write_index(tmp_path, [], "h", {url("/a"): "HTTP 429"}, [url("/b")])
        md = (tmp_path / "index.md").read_text()
        assert f"**FAILED** {url('/a')}" in md and f"**SKIPPED**" in md

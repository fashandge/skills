import json

import pytest

import fetch_zhihu_posts as fzp


# ---- target parsing -------------------------------------------------------
@pytest.mark.parametrize("target,expected", [
    ("2076674418479257365", "2076674418479257365"),
    ("https://www.zhihu.com/question/2076674418479257365", "2076674418479257365"),
    ("https://www.zhihu.com/question/123/answer/456", "123"),   # answer URL → parent
    ("https://www.zhihu.com/question/123?sort=created", "123"),
    ("https://zhuanlan.zhihu.com/p/999", None),                  # article, not a question
    ("not a url", None),
])
def test_question_id_of(target, expected):
    assert fzp.question_id_of(target) == expected


# ---- --select -------------------------------------------------------------
def test_parse_select_ranges_singles_and_open_end():
    assert fzp.parse_select("1-3", 10) == [1, 2, 3]
    assert fzp.parse_select("2,5", 10) == [2, 5]
    assert fzp.parse_select("8-", 10) == [8, 9, 10]
    assert fzp.parse_select("-3", 10) == [1, 2, 3]


def test_parse_select_dedupes_preserving_order():
    assert fzp.parse_select("3,1-3,1", 10) == [3, 1, 2]


def test_parse_select_clamps_to_total():
    assert fzp.parse_select("1-99", 3) == [1, 2, 3]


@pytest.mark.parametrize("spec", ["0", "5-2", "99", ""])
def test_parse_select_rejects_bad_specs(spec):
    with pytest.raises(ValueError):
        fzp.parse_select(spec, 3)


# ---- filenames ------------------------------------------------------------
def test_slugify_keeps_cjk_and_budgets_in_bytes():
    """CJK is 3 bytes/char, so the cap must be measured in bytes, not characters."""
    title = "如何评价腾讯混元发布并开源新一代大语言模型" * 5
    out = fzp.slugify(title, maxlen=60)
    assert len(out.encode("utf-8")) <= 60
    assert "如何评价" in out


def test_slugify_replaces_path_separators_and_never_returns_empty():
    assert "/" not in fzp.slugify("a/b:c*d?e")
    assert fzp.slugify("") == "untitled"
    assert fzp.slugify("///") == "untitled"


# ---- heading demotion -----------------------------------------------------
def test_demote_headings_pushes_body_headings_below_the_answer_heading():
    body = "## 参数\n正文\n### 细节"
    assert fzp.demote_headings(body) == "#### 参数\n正文\n##### 细节"


def test_demote_headings_leaves_code_fences_alone():
    body = "## 真标题\n```python\n# 这是注释\n```\n# 又一个标题"
    out = fzp.demote_headings(body).split("\n")
    assert out[0] == "#### 真标题"
    assert out[2] == "# 这是注释"     # untouched inside the fence
    assert out[4] == "### 又一个标题"


def test_demote_headings_caps_at_h6_and_ignores_hashes_without_space():
    assert fzp.demote_headings("###### deep") == "###### deep"
    assert fzp.demote_headings("#hashtag") == "#hashtag"
    assert fzp.demote_headings("") == ""


# ---- ledger / index -------------------------------------------------------
def test_read_ledger_skips_a_torn_final_line(tmp_path):
    (tmp_path / "index.jsonl").write_text(
        json.dumps({"n": 1}) + "\n" + '{"n": 2, "tit',  # killed mid-write
        encoding="utf-8")
    assert fzp.read_ledger(tmp_path) == [{"n": 1}]


def test_read_ledger_missing_file_is_empty(tmp_path):
    assert fzp.read_ledger(tmp_path) == []


def test_write_index_sorts_by_n_and_marks_articles(tmp_path):
    rows = [
        {"n": 2, "kind": "article", "title": "文章", "url": "u2", "author": "甲",
         "votes": 3, "file": "02.md"},
        {"n": 1, "kind": "question", "title": "问题", "url": "u1", "answers": 5,
         "answers_fetched": 4, "votes": 9, "truncated": 1, "file": "01.md"},
    ]
    fzp.write_index(tmp_path, rows, "hdr")
    md = (tmp_path / "index.md").read_text(encoding="utf-8")
    lines = [ln for ln in md.splitlines() if ln.strip().startswith(("1.", "2."))]
    assert lines[0].startswith(" 1.") and "4/5 answers" in lines[0]
    assert "⚠️ 1 truncated" in lines[0]
    assert "[article]" in lines[1]
    assert json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))[0]["n"] == 1


# ---- load_from ------------------------------------------------------------
def test_load_from_prefers_candidates_json_in_a_run_dir(tmp_path):
    (tmp_path / "candidates.json").write_text(
        json.dumps([{"n": 1, "kind": "question"}]), encoding="utf-8")
    assert fzp.load_from(str(tmp_path))[0]["n"] == 1


def test_load_from_rejects_a_directory_with_no_rows(tmp_path):
    with pytest.raises(FileNotFoundError):
        fzp.load_from(str(tmp_path))


# ---- CLI validation -------------------------------------------------------
def test_cli_requires_a_target_query_or_from():
    with pytest.raises(SystemExit):
        fzp.main([])


def test_cli_rejects_target_plus_query():
    with pytest.raises(SystemExit):
        fzp.main(["123", "-q", "x"])


def test_cli_rejects_a_target_with_no_question_id():
    with pytest.raises(SystemExit):
        fzp.main(["https://zhuanlan.zhihu.com/p/999"])

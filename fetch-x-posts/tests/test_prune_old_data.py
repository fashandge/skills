import os
import time

import prune_old_data


def _touch(path, age_days):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
    t = time.time() - age_days * 86400
    os.utime(path, (t, t))


def test_prunes_stale_search_and_home_but_keeps_user_tweets(tmp_path):
    _touch(tmp_path / "x_search/old_q/search_1.jsonl", 10)
    _touch(tmp_path / "x_search/mixed_q/search_1.jsonl", 10)
    _touch(tmp_path / "x_search/mixed_q/search_2.jsonl", 1)
    _touch(tmp_path / "x_home_feed/for_you/home_old.jsonl", 10)
    _touch(tmp_path / "x_home_feed/for_you/home_new.jsonl", 1)
    _touch(tmp_path / "user_tweets/elonmusk/tweets.jsonl", 100)

    report = prune_old_data.prune(tmp_path, 7)

    assert not (tmp_path / "x_search/old_q").exists()
    assert (tmp_path / "x_search/mixed_q/search_1.jsonl").exists()
    assert not (tmp_path / "x_home_feed/for_you/home_old.jsonl").exists()
    assert (tmp_path / "x_home_feed/for_you/home_new.jsonl").exists()
    assert (tmp_path / "user_tweets/elonmusk/tweets.jsonl").exists()
    assert len(report["removed_dirs"]) == 1 and len(report["removed_files"]) == 1


def test_dry_run_deletes_nothing(tmp_path):
    _touch(tmp_path / "x_search/old_q/search_1.jsonl", 10)
    report = prune_old_data.prune(tmp_path, 7, dry_run=True)
    assert report["removed_dirs"] and (tmp_path / "x_search/old_q").exists()

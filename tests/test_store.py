"""Store tests: URL-keyed dedupe, reruns add nothing, digest view."""

from watcher.store import Store
from .conftest import make_settings


def row(url: str, score: float = 5.0, **kw) -> dict:
    base = dict(url=url, source="remoteok", title="T", company="C", location="Remote",
                remote=1, description="d", tags="", posted_at=None, score=score, why="w")
    base.update(kw)
    return base


def test_insert_and_dedupe_by_url(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    try:
        assert store.insert_listings([row("https://x/1"), row("https://x/2")]) == 2
        assert store.insert_listings([row("https://x/1"), row("https://x/2")]) == 0
        assert store.stats()["total_listings"] == 2
    finally:
        store.close()


def test_seen_urls(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    try:
        store.insert_listings([row("https://x/1")])
        assert store.seen_urls(["https://x/1", "https://x/2"]) == {"https://x/1"}
        assert store.seen_urls([]) == set()
    finally:
        store.close()


def test_top_unreported_respects_threshold_and_marks_reported(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    try:
        store.insert_listings([
            row("https://x/hi", score=9.0, title="Hi"),
            row("https://x/lo", score=1.0, title="Lo"),
        ])
        top = store.top_unreported(10, min_score=3.0)
        assert [t.url for t in top] == ["https://x/hi"]
        store.mark_reported(["https://x/hi"])
        assert [t.url for t in store.top_unreported(10, min_score=0)] == ["https://x/lo"]
        assert store.count_unreported() == 1
    finally:
        store.close()


def test_feed_hash_roundtrip(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    try:
        assert store.feed_hash("remoteok") is None
        store.set_feed_hash("remoteok", "abc123")
        assert store.feed_hash("remoteok") == "abc123"
        store.set_feed_hash("remoteok", "def456")
        assert store.feed_hash("remoteok") == "def456"
    finally:
        store.close()

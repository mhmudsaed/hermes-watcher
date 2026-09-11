"""Runner tests: hash-skip, rerun dedupe, dead-feed tolerance, digest render."""

import httpx

from watcher.digest import render_digest
from watcher.notify import FakeSender
from watcher.runner import run_once
from watcher.store import ScoredListing, Store
from .conftest import fixture_bytes, fixture_client, make_settings


def mapping() -> dict[str, bytes]:
    return {
        "remoteok.com/api": fixture_bytes("remoteok.json"),
        "programming-jobs.rss": fixture_bytes("weworkremotely.xml"),
        "hn.algolia.com/api/v1/search": b'{"hits": []}',
        "remotive.com/api": fixture_bytes("remotive.json"),
        "arbeitnow.com/api": fixture_bytes("arbeitnow.json"),
        "akhtaboot.com": b"<html>not a feed</html>",
    }


def hn_thread_client() -> httpx.Client:
    m = dict(mapping())
    m["hn.algolia.com/api/v1/search"] = (
        b'{"hits": [{"title": "Ask HN: Who is hiring? (September 2026)", '
        b'"objectID": "49522897", "created_at": "2026-09-01"}]}'
    )
    m["hn.algolia.com/api/v1/items/"] = fixture_bytes("hn_whoishiring.json")

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for key, payload in m.items():
            if key in url:
                return httpx.Response(200, content=payload)
        return httpx.Response(404, content=b"nope")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_full_cycle_then_rerun_adds_nothing(tmp_path):
    settings = make_settings(tmp_path)
    settings.sources = ["remoteok", "remotive", "arbeitnow"]
    store = Store(settings.db_path)
    try:
        first = run_once(settings, sender=FakeSender(),
                         client=fixture_client(mapping()), store=store)
        assert first.new_listings > 0
        assert first.digest_text  # non-silent default
        second = run_once(settings, sender=FakeSender(),
                          client=fixture_client(mapping()), store=store)
        assert second.new_listings == 0
        assert set(second.skipped_unchanged) == {"remoteok", "remotive", "arbeitnow"}
        assert second.fetched == {}
    finally:
        store.close()


def test_hash_skip_does_zero_scoring(tmp_path, monkeypatch):
    import watcher.runner as runner_mod

    settings = make_settings(tmp_path)
    settings.sources = ["remoteok"]
    store = Store(settings.db_path)
    try:
        run_once(settings, sender=FakeSender(), client=fixture_client(mapping()), store=store)
        calls = []
        real_score = runner_mod.score_listing

        def counting(listing, profile):
            calls.append(listing.url)
            return real_score(listing, profile)

        monkeypatch.setattr(runner_mod, "score_listing", counting)
        run_once(settings, sender=FakeSender(), client=fixture_client(mapping()), store=store)
        assert calls == []  # unchanged feed: fetch only, no scoring
    finally:
        store.close()


def test_dead_feed_skipped_digest_still_builds(tmp_path):
    settings = make_settings(tmp_path)
    settings.sources = ["remoteok", "akhtaboot"]

    def handler(request: httpx.Request) -> httpx.Response:
        if "remoteok.com" in str(request.url):
            return httpx.Response(200, content=fixture_bytes("remoteok.json"))
        return httpx.Response(200, content=b"<html>not a feed</html>")

    store = Store(settings.db_path)
    try:
        result = run_once(settings, sender=FakeSender(),
                          client=httpx.Client(transport=httpx.MockTransport(handler)),
                          store=store)
        assert "akhtaboot" in result.skipped_dead
        assert "remoteok" in result.fetched
        assert result.digest_text
    finally:
        store.close()


def test_parse_error_skipped_digest_still_builds(tmp_path):
    settings = make_settings(tmp_path)
    settings.sources = ["remoteok", "remotive"]
    m = dict(mapping())
    m["remotive.com/api"] = b"{broken json"

    store = Store(settings.db_path)
    try:
        result = run_once(settings, sender=FakeSender(),
                          client=fixture_client(m), store=store)
        assert "remotive" in result.skipped_dead
        assert "remoteok" in result.fetched
        assert result.digest_text
    finally:
        store.close()


def test_hn_thread_flow(tmp_path):
    settings = make_settings(tmp_path)
    settings.sources = ["hn"]
    store = Store(settings.db_path)
    try:
        result = run_once(settings, sender=FakeSender(),
                          client=hn_thread_client(), store=store)
        assert result.fetched.get("hn") == 4
        assert result.new_listings == 4
    finally:
        store.close()


def test_digest_rendering_groups_by_source_and_caps_items():
    items = [
        ScoredListing(url=f"https://x/{i}", title=f"Role {i}", company="C",
                      location="Remote", remote=True, source="remoteok" if i % 2 == 0 else "hn",
                      score=9.0 - i, why="w")
        for i in range(5)
    ]
    text = render_digest(items, max_items=3, run_date="2026-09-11")
    assert "2026-09-11" in text
    assert "RemoteOK" in text and "HN Who" in text
    assert "+2 more" in text
    assert "Role 4" not in text


def test_digest_empty_modes():
    assert "Nothing new" in render_digest([], run_date="2026-09-11", empty_mode="status")
    assert render_digest([], run_date="2026-09-11", empty_mode="silent") == ""


def test_reported_items_not_redelivered(tmp_path):
    settings = make_settings(tmp_path)
    settings.sources = ["remoteok"]
    store = Store(settings.db_path)
    try:
        first = run_once(settings, sender=FakeSender(),
                         client=fixture_client(mapping()), store=store)
        assert first.digest_items >= 0
        second = run_once(settings, sender=FakeSender(),
                          client=fixture_client(mapping()), store=store)
        assert second.digest_items == 0  # all reported; unchanged feed anyway
    finally:
        store.close()

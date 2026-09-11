"""Normalization tests: every source adapter parses its fixture payload."""

from watcher.sources import get_source
from .conftest import fixture_bytes


def test_remoteok_parse():
    listings = get_source("remoteok").parse(fixture_bytes("remoteok.json"))
    assert len(listings) == 5  # 6 payload entries minus the legal notice
    urls = [l.url for l in listings]
    assert all(u.startswith("https://") for u in urls)
    first = listings[0]
    assert first.source == "remoteok"
    assert first.title and first.company and first.url
    assert first.remote  # fixture jobs are remote


def test_remoteok_skips_legal_notice():
    listings = get_source("remoteok").parse(fixture_bytes("remoteok.json"))
    assert not any("legal" in l.title.lower() or "terms" in l.title.lower() for l in listings)


def test_remoteok_rejects_bad_payload():
    import pytest

    from watcher.sources.base import SourceError

    with pytest.raises(SourceError):
        get_source("remoteok").parse(b"not json{{{")


def test_weworkremotely_parse():
    listings = get_source("weworkremotely").parse(fixture_bytes("weworkremotely.xml"))
    assert len(listings) == 3
    assert all(l.remote for l in listings)
    assert listings[0].company == "Confluent"
    assert listings[0].url.startswith("https://weworkremotely.com")
    assert "<" not in listings[0].description  # html stripped


def test_weworkremotely_rejects_bad_xml():
    import pytest

    from watcher.sources.base import SourceError

    with pytest.raises(SourceError):
        get_source("weworkremotely").parse(b"<rss><unclosed")


def test_hn_parse():
    listings = get_source("hn").parse(fixture_bytes("hn_whoishiring.json"))
    assert len(listings) == 4
    assert all(l.url.startswith("https://news.ycombinator.com/item?id=") for l in listings)
    assert "hn-whoishiring" in listings[0].tags
    companies = [l.company for l in listings]
    assert any("Modash" in c for c in companies)


def test_remotive_parse():
    listings = get_source("remotive").parse(fixture_bytes("remotive.json"))
    assert len(listings) == 3
    assert all(l.remote for l in listings)
    assert listings[0].company == "Credit Wellness, LLC"
    assert listings[0].url.startswith("https://remotive.com/remote-jobs/")


def test_arbeitnow_parse():
    listings = get_source("arbeitnow").parse(fixture_bytes("arbeitnow.json"))
    assert len(listings) == 3
    by_title = {l.title: l for l in listings}
    onsite = by_title["Bauingenieur (m/w/d) - Projektmanagement"]
    assert onsite.remote is False
    assert onsite.location == "Minden"
    remote = by_title["(Senior) Go-to-Market Scaling Manager - Germany (m/f/d)"]
    assert remote.remote is True


def test_akhtaboot_skipped_with_reason():
    """No stable public feed: fetch must raise SourceUnavailable, never hang/fail."""
    import httpx
    import pytest

    from watcher.sources.base import SourceUnavailable

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not a feed</html>")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(SourceUnavailable, match="no stable public feed"):
        get_source("akhtaboot").fetch(client)

"""Akhtaboot (Jordan) adapter — best-effort.

There is no stable public Akhtaboot jobs feed: the candidate /jobs/feed URLs
redirect to HTML pages or 500s (verified Sep 2026). Per the spec this source is
handled gracefully: fetch() probes the known candidate feed URLs and returns
the first payload that actually looks like a feed; otherwise it raises
SourceUnavailable with the reason, and the runner records a skip — the digest
still builds from the other sources.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from watcher.models import Listing
from watcher.sources.base import USER_AGENT, SourceAdapter, SourceError, SourceUnavailable
from watcher.sources.weworkremotely import strip_html

CANDIDATE_FEEDS = [
    "https://www.akhtaboot.com/en/the-middle-east/jobs/feed",
    "https://www.akhtaboot.com/en/jordan/jobs/feed",
]

SKIP_REASON = (
    "no stable public feed (candidate feed URLs return HTML/errors); "
    "skipped-with-reason per spec"
)


def _looks_like_feed(payload: bytes) -> bool:
    head = payload[:2000].lower()
    return b"<rss" in head or b"<feed" in head or b"<item" in head or b"<entry" in head


class AkhtabootSource(SourceAdapter):
    name = "akhtaboot"
    feed_url = CANDIDATE_FEEDS[0]

    def fetch(self, client: httpx.Client) -> bytes:
        errors: list[str] = []
        for url in CANDIDATE_FEEDS:
            try:
                resp = client.get(url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                errors.append(f"{url}: {exc}")
                continue
            if _looks_like_feed(resp.content):
                return resp.content
            errors.append(f"{url}: not a feed (HTML/error page)")
        raise SourceUnavailable(f"{self.name}: {SKIP_REASON} [{'; '.join(errors)}]")

    def parse(self, raw: bytes) -> list[Listing]:
        """Best-effort generic RSS/Atom parse."""
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise SourceError(f"{self.name}: invalid XML: {exc}") from exc
        listings: list[Listing] = []
        for item in list(root.iter("item")) + list(
            root.iter("{http://www.w3.org/2005/Atom}entry")
        ):
            title = (item.findtext("title") or "").strip()
            link_el = item.find("link")
            link = ""
            if link_el is not None:
                link = (link_el.get("href") or (link_el.text or "")).strip()
            if not title or not link:
                continue
            listings.append(
                Listing(
                    source=self.name,
                    title=title,
                    company="",
                    location="Jordan",
                    remote=False,
                    url=link,
                    description=strip_html(
                        item.findtext("description") or item.findtext("summary") or ""
                    )[:4000],
                    posted_at=item.findtext("pubDate"),
                )
            )
        return listings

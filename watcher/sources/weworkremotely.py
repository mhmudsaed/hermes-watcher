"""We Work Remotely RSS adapter. Stdlib-only XML parsing, no feedparser needed."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

from watcher.models import Listing
from watcher.sources.base import SourceAdapter, SourceError

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", html.unescape(text))
    return re.sub(r"\s+", " ", text).strip()


class WeWorkRemotelySource(SourceAdapter):
    name = "weworkremotely"
    feed_url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    def parse(self, raw: bytes) -> list[Listing]:
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise SourceError(f"{self.name}: invalid RSS XML: {exc}") from exc
        listings: list[Listing] = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not title or not link:
                continue
            company, _, role = title.partition(":")
            if not role:
                company, role = "", title
            region = (item.findtext("region") or "").strip()
            category = (item.findtext("category") or "").strip()
            listings.append(
                Listing(
                    source=self.name,
                    title=role.strip(),
                    company=company.strip(),
                    location=region,
                    remote=True,  # WWR lists remote jobs only
                    url=link,
                    description=strip_html(item.findtext("description") or "")[:4000],
                    tags=[category] if category else [],
                    posted_at=item.findtext("pubDate"),
                )
            )
        return listings

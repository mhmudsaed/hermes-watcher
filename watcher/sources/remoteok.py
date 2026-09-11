"""RemoteOK public JSON API adapter. GET https://remoteok.com/api -> [legal, jobs...]."""

from __future__ import annotations

import json

from watcher.models import Listing
from watcher.sources.base import SourceAdapter, SourceError


class RemoteOKSource(SourceAdapter):
    name = "remoteok"
    feed_url = "https://remoteok.com/api"

    def parse(self, raw: bytes) -> list[Listing]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise SourceError(f"{self.name}: invalid JSON payload: {exc}") from exc
        if not isinstance(payload, list):
            raise SourceError(f"{self.name}: expected a JSON list, got {type(payload).__name__}")
        listings: list[Listing] = []
        for item in payload:
            if not isinstance(item, dict) or "position" not in item:
                continue  # index 0 is the legal notice, not a job
            url = str(item.get("url") or item.get("apply_url") or "").strip()
            if not url:
                continue
            location = str(item.get("location") or "").strip()
            listings.append(
                Listing(
                    source=self.name,
                    title=str(item.get("position") or "").strip(),
                    company=str(item.get("company") or "").strip(),
                    location=location,
                    remote="remote" in location.lower()
                    or "anywhere" in location.lower()
                    or not location,
                    url=url,
                    description=str(item.get("description") or "")[:4000],
                    tags=[str(t) for t in (item.get("tags") or []) if t],
                    posted_at=item.get("date"),
                )
            )
        return listings

"""Arbeitnow public JSON API adapter. GET https://www.arbeitnow.com/api/job-board-api."""

from __future__ import annotations

import json

from watcher.models import Listing
from watcher.sources.base import SourceAdapter, SourceError
from watcher.sources.weworkremotely import strip_html


class ArbeitnowSource(SourceAdapter):
    name = "arbeitnow"
    feed_url = "https://www.arbeitnow.com/api/job-board-api"

    def parse(self, raw: bytes) -> list[Listing]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise SourceError(f"{self.name}: invalid JSON payload: {exc}") from exc
        jobs = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise SourceError(f"{self.name}: expected object with a 'data' list")
        listings: list[Listing] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            url = str(job.get("url") or "").strip()
            if not url:
                continue
            remote = bool(job.get("remote"))
            location = str(job.get("location") or "").strip()
            listings.append(
                Listing(
                    source=self.name,
                    title=str(job.get("title") or "").strip(),
                    company=str(job.get("company_name") or "").strip(),
                    location=location or ("Remote" if remote else ""),
                    remote=remote,
                    url=url,
                    description=strip_html(str(job.get("description") or ""))[:4000],
                    tags=[str(t) for t in (job.get("tags") or []) if t]
                    + [str(t) for t in (job.get("job_types") or []) if t],
                    posted_at=None,
                )
            )
        return listings

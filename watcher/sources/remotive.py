"""Remotive public JSON API adapter. GET https://remotive.com/api/remote-jobs."""

from __future__ import annotations

import json
import re

from watcher.models import Listing
from watcher.sources.base import SourceAdapter, SourceError
from watcher.sources.weworkremotely import strip_html


class RemotiveSource(SourceAdapter):
    name = "remotive"
    feed_url = "https://remotive.com/api/remote-jobs?limit=100"

    def parse(self, raw: bytes) -> list[Listing]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise SourceError(f"{self.name}: invalid JSON payload: {exc}") from exc
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise SourceError(f"{self.name}: expected object with a 'jobs' list")
        listings: list[Listing] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            url = str(job.get("url") or "").strip()
            if not url:
                continue
            loc = str(job.get("candidate_required_location") or "").strip()
            job_type = str(job.get("job_type") or "").replace("_", " ")
            category = str(job.get("category") or "").strip()
            listings.append(
                Listing(
                    source=self.name,
                    title=str(job.get("title") or "").strip(),
                    company=str(job.get("company_name") or "").strip(),
                    location=loc,
                    remote=True,  # Remotive lists remote jobs only
                    url=url,
                    description=strip_html(str(job.get("description") or ""))[:4000],
                    tags=[t for t in [category, job_type] if t]
                    + [str(t) for t in (job.get("tags") or []) if t],
                    posted_at=job.get("publication_date"),
                )
            )
        return listings

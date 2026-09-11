"""HN "Who is hiring" adapter over the public Algolia API (no login, no scraping).

Two-step fetch:
  1. search for the latest "Ask HN: Who is hiring? (<Month> <Year>)" story,
  2. fetch that thread's top-level comments; each comment is one hiring post.

parse() handles the thread-items payload ({"id","title","children":[...]})."""

from __future__ import annotations

import json
import re

import httpx

from watcher.models import Listing
from watcher.sources.base import SourceAdapter, SourceError, SourceUnavailable
from watcher.sources.weworkremotely import strip_html

_TAG_RE = re.compile(r"<[^>]+>")
_SEARCH_URL = "https://hn.algolia.com/api/v1/search?tags=story&query=Who%20is%20hiring%3F"
_ITEM_URL = "https://hn.algolia.com/api/v1/items/{story_id}"


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return text.strip()[:160]


def comment_to_listing(source: str, story_id: int, comment: dict) -> Listing | None:
    text = strip_html(str(comment.get("text") or ""))
    if not text:
        return None
    head = _first_line(text)
    # Conventional format: "Company | Role | Location | ..." — split on pipes.
    parts = [p.strip() for p in re.split(r"\s*\|\s*", head) if p.strip()]
    company = parts[0][:120] if parts else f"HN comment {comment.get('id')}"
    title = parts[1][:160] if len(parts) > 1 else head[:160]
    rest = " ".join(parts[2:]).lower() if len(parts) > 2 else text[:300].lower()
    remote = any(k in rest for k in ("remote", "anywhere", "worldwide", "async", "distributed"))
    location = " ".join(parts[2:])[:160] if len(parts) > 2 else ""
    url = f"https://news.ycombinator.com/item?id={comment.get('id')}"
    return Listing(
        source=source,
        title=title,
        company=company,
        location=location,
        remote=remote,
        url=url,
        description=text[:4000],
        tags=["hn-whoishiring"],
        posted_at=comment.get("created_at"),
    )


class HNWhoIsHiringSource(SourceAdapter):
    name = "hn"
    # feed_url is the latest-thread lookup; thread id resolution happens in fetch().
    feed_url = _SEARCH_URL

    def _latest_story_id(self, client: httpx.Client) -> tuple[int, str]:
        try:
            resp = client.get(
                self.feed_url,
                headers={"User-Agent": "hermes-watcher/0.1.0"},
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceUnavailable(f"{self.name}: thread search failed: {exc}") from exc
        monthly = [h for h in hits if "Who is hiring?" in str(h.get("title", ""))]
        if not monthly:
            raise SourceUnavailable(f"{self.name}: no 'Who is hiring' thread found")
        monthly.sort(key=lambda h: str(h.get("created_at", "")), reverse=True)
        top = monthly[0]
        return int(top["objectID"]), str(top.get("title", ""))

    def fetch_thread(self, client: httpx.Client) -> bytes:
        story_id, _ = self._latest_story_id(client)
        try:
            resp = client.get(
                _ITEM_URL.format(story_id=story_id),
                headers={"User-Agent": "hermes-watcher/0.1.0"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceUnavailable(f"{self.name}: thread fetch failed: {exc}") from exc
        return resp.content

    def fetch(self, client: httpx.Client) -> bytes:  # type: ignore[override]
        return self.fetch_thread(client)

    def parse(self, raw: bytes) -> list[Listing]:
        try:
            thread = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise SourceError(f"{self.name}: invalid JSON thread payload: {exc}") from exc
        story_id = thread.get("id", 0)
        children = thread.get("children")
        if not isinstance(children, list):
            raise SourceError(f"{self.name}: expected thread with children comments")
        listings: list[Listing] = []
        for comment in children:
            if not isinstance(comment, dict):
                continue
            listing = comment_to_listing(self.name, story_id, comment)
            if listing is not None:
                listings.append(listing)
        return listings

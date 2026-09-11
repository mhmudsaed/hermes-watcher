"""One-shot run cycle: poll -> hash-skip -> score -> store -> digest -> send.

Quiet feeds (unchanged sha256) cost one HTTP fetch and zero scoring. A dead
feed is recorded as skipped and never blocks the digest.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from watcher.config import Settings, load_profile, repo_root
from watcher.digest import render_digest
from watcher.hashing import sha256_hex
from watcher.notify import BaseSender, FakeSender, TelegramSender
from watcher.scoring import Profile, score_listing
from watcher.sources import get_source
from watcher.sources.base import SourceError
from watcher.store import Store


@dataclass
class RunResult:
    fetched: dict[str, int] = field(default_factory=dict)  # source -> listings parsed
    skipped_unchanged: list[str] = field(default_factory=list)
    skipped_dead: dict[str, str] = field(default_factory=dict)  # source -> reason
    new_listings: int = 0
    digest_items: int = 0
    digest_text: str = ""
    delivery: str = ""

    def summary(self) -> str:
        parts = [
            f"fetched={self.fetched}",
            f"unchanged={self.skipped_unchanged}",
            f"dead={list(self.skipped_dead)}",
            f"new={self.new_listings}",
            f"digest_items={self.digest_items}",
            f"delivery={self.delivery}",
        ]
        return " | ".join(parts)


def make_sender(settings: Settings) -> BaseSender:
    if settings.bot_token and settings.chat_id:
        return TelegramSender(settings.bot_token, settings.chat_id)
    return FakeSender()


def run_once(
    settings: Settings,
    sender: BaseSender | None = None,
    client: httpx.Client | None = None,
    store: Store | None = None,
) -> RunResult:
    profile_data = load_profile(repo_root() / settings.profile_path if not _is_abs(settings.profile_path) else settings.profile_path)
    profile = Profile.from_dict(profile_data)
    threshold = settings.threshold or profile.threshold

    own_store = store is None
    store = store or Store(settings.db_path)
    own_client = client is None
    client = client or httpx.Client(
        timeout=settings.request_timeout, follow_redirects=True
    )
    sender = sender or make_sender(settings)
    result = RunResult()
    try:
        for i, name in enumerate(settings.sources):
            if i:
                time.sleep(settings.min_interval_seconds)
            adapter = get_source(name)
            try:
                raw = adapter.fetch(client)
            except SourceError as exc:
                result.skipped_dead[name] = str(exc)
                continue
            digest_hash = sha256_hex(raw)
            if store.feed_hash(name) == digest_hash:
                result.skipped_unchanged.append(name)
                continue
            try:
                listings = adapter.parse(raw)
            except SourceError as exc:
                result.skipped_dead[name] = f"parse failed: {exc}"
                continue
            result.fetched[name] = len(listings)
            store.set_feed_hash(name, digest_hash)

            known = store.seen_urls([l.url for l in listings if l.url])
            fresh = [l for l in listings if l.url and l.url not in known]
            rows = []
            for listing in fresh:
                score, why = score_listing(listing, profile)
                rows.append(
                    {
                        "url": listing.url, "source": listing.source,
                        "title": listing.title, "company": listing.company,
                        "location": listing.location, "remote": int(listing.remote),
                        "description": listing.description,
                        "tags": ",".join(listing.tags),
                        "posted_at": listing.posted_at,
                        "score": score, "why": why,
                    }
                )
            result.new_listings += store.insert_listings(rows)

        digest_items = store.top_unreported(settings.max_items, threshold)
        result.digest_items = len(digest_items)
        result.digest_text = render_digest(
            digest_items,
            max_items=settings.max_items,
            empty_mode=settings.empty_mode,
        )
        result.delivery = sender.send(result.digest_text)
        store.mark_reported([d.url for d in digest_items])
        return result
    finally:
        if own_client:
            client.close()
        if own_store:
            store.close()


def _is_abs(path: str) -> bool:
    return path.startswith("/") or path.startswith("~")

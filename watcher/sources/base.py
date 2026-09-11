"""Source adapter interface: fetch raw feed bytes, parse to Listings."""

from __future__ import annotations

import abc

import httpx

from watcher.models import Listing

USER_AGENT = "hermes-watcher/0.1.0 (+https://mahmoudsaeed.com/work/watcher-telegram-digest)"


class SourceError(Exception):
    """Base class for source failures."""


class SourceUnavailable(SourceError):
    """A feed is dead or not configured: skip it, never block the digest."""


class SourceAdapter(abc.ABC):
    """One public job board. Fetch returns raw bytes; parse normalizes them."""

    name: str = ""
    feed_url: str = ""

    def fetch(self, client: httpx.Client) -> bytes:
        if not self.feed_url:
            raise SourceUnavailable(f"{self.name}: no public feed URL configured")
        try:
            resp = client.get(
                self.feed_url,
                headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceUnavailable(f"{self.name}: request failed: {exc}") from exc
        return resp.content

    @abc.abstractmethod
    def parse(self, raw: bytes) -> list[Listing]:
        """Normalize raw payload bytes to listings. Raises SourceError on bad payload."""

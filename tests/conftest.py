"""Shared test helpers: fixture loading, fake HTTP client, temp settings."""

from __future__ import annotations

from pathlib import Path

import httpx

from watcher.config import Settings
from watcher.store import Store
from watcher.notify import FakeSender

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_client(mapping: dict[str, bytes]) -> httpx.Client:
    """httpx client whose transport serves fixed payloads per URL substring."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for key, payload in mapping.items():
            if key in url:
                return httpx.Response(200, content=payload)
        return httpx.Response(404, content=b"no fixture for " + url.encode())

    return httpx.Client(transport=httpx.MockTransport(handler))


def make_settings(tmp_path: Path, **overrides) -> Settings:
    s = Settings(
        db_path=str(tmp_path / "test.db"),
        profile_path="profiles/default.yaml",
        max_items=15,
        threshold=3.0,
        empty_mode="status",
    )
    for k, v in overrides.items():
        setattr(s, k, v)
    s.min_interval_seconds = 0
    return s


def open_store(settings: Settings) -> Store:
    return Store(settings.db_path)


def fresh_sender() -> FakeSender:
    return FakeSender()

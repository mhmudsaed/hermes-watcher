"""Runtime configuration: env vars + YAML profile + polite HTTP defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_DB = "data/watcher.db"
DEFAULT_PROFILE = "profiles/default.yaml"


@dataclass
class Settings:
    db_path: str = DEFAULT_DB
    profile_path: str = DEFAULT_PROFILE
    bot_token: str = ""
    chat_id: str = ""
    max_items: int = 15
    threshold: float = 3.0
    empty_mode: str = "status"  # or "silent"
    sources: list[str] = field(
        default_factory=lambda: [
            "remoteok", "weworkremotely", "hn", "remotive", "arbeitnow", "akhtaboot",
        ]
    )
    request_timeout: float = 20.0
    min_interval_seconds: float = 2.0  # politeness gap between feed requests

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Settings":
        e = env if env is not None else os.environ
        s = cls()
        s.db_path = e.get("WATCHER_DB", DEFAULT_DB)
        s.profile_path = e.get("WATCHER_PROFILE", DEFAULT_PROFILE)
        s.bot_token = e.get("TELEGRAM_BOT_TOKEN", "")
        s.chat_id = e.get("TELEGRAM_CHAT_ID", "")
        s.max_items = int(e.get("WATCHER_MAX_ITEMS", "15"))
        s.threshold = float(e.get("WATCHER_THRESHOLD", "3.0"))
        s.empty_mode = e.get("WATCHER_EMPTY_MODE", "status")
        if e.get("WATCHER_SOURCES"):
            s.sources = [x.strip() for x in e["WATCHER_SOURCES"].split(",") if x.strip()]
        s.request_timeout = float(e.get("WATCHER_HTTP_TIMEOUT", "20"))
        s.min_interval_seconds = float(e.get("WATCHER_MIN_INTERVAL", "2"))
        return s


def load_profile(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"profile {path}: expected a mapping")
    return data


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent

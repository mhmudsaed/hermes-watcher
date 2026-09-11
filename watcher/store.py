"""SQLite store: listings keyed by URL, feed hashes, digest views."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass


@dataclass
class ScoredListing:
    url: str
    title: str
    company: str
    location: str
    remote: bool
    source: str
    score: float
    why: str

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    url TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    remote INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    posted_at TEXT,
    score REAL NOT NULL DEFAULT 0,
    why TEXT NOT NULL DEFAULT '',
    first_seen INTEGER NOT NULL,
    reported INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS feed_hashes (
    source TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    checked_at INTEGER NOT NULL
);
"""


class Store:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # -- listings ---------------------------------------------------------
    def seen_urls(self, urls: list[str]) -> set[str]:
        """Which of these URLs are already stored (URL-keyed dedupe)."""
        if not urls:
            return set()
        found: set[str] = set()
        for i in range(0, len(urls), 500):
            chunk = urls[i : i + 500]
            rows = self.conn.execute(
                f"SELECT url FROM listings WHERE url IN ({','.join('?' * len(chunk))})",
                chunk,
            ).fetchall()
            found.update(r["url"] for r in rows)
        return found

    def insert_listings(self, rows: list[dict], now: int | None = None) -> int:
        """Insert new listings; existing URLs are ignored. Returns # inserted."""
        now = now if now is not None else int(time.time())
        cur = self.conn.executemany(
            """INSERT OR IGNORE INTO listings
               (url, source, title, company, location, remote, description,
                tags, posted_at, score, why, first_seen, reported)
               VALUES (:url, :source, :title, :company, :location, :remote,
                       :description, :tags, :posted_at, :score, :why, :first_seen, 0)""",
            [{**r, "first_seen": now} for r in rows],
        )
        self.conn.commit()
        return cur.rowcount if cur.rowcount is not None else 0

    def mark_reported(self, urls: list[str]) -> None:
        if not urls:
            return
        for i in range(0, len(urls), 500):
            chunk = urls[i : i + 500]
            self.conn.execute(
                f"UPDATE listings SET reported = 1 WHERE url IN ({','.join('?' * len(chunk))})",
                chunk,
            )
        self.conn.commit()

    def top_unreported(self, limit: int, min_score: float = 0.0) -> list[ScoredListing]:
        rows = self.conn.execute(
            """SELECT url, title, company, location, remote, source, score, why
               FROM listings WHERE reported = 0 AND score >= ?
               ORDER BY score DESC, first_seen DESC LIMIT ?""",
            (min_score, limit),
        ).fetchall()
        return [
            ScoredListing(
                url=r["url"], title=r["title"], company=r["company"],
                location=r["location"], remote=bool(r["remote"]),
                source=r["source"], score=r["score"], why=r["why"],
            )
            for r in rows
        ]

    def count_unreported(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM listings WHERE reported = 0"
        ).fetchone()[0]

    # -- feed hashes ------------------------------------------------------
    def feed_hash(self, source: str) -> str | None:
        row = self.conn.execute(
            "SELECT sha256 FROM feed_hashes WHERE source = ?", (source,)
        ).fetchone()
        return row["sha256"] if row else None

    def set_feed_hash(self, source: str, sha256: str, now: int | None = None) -> None:
        now = now if now is not None else int(time.time())
        self.conn.execute(
            """INSERT INTO feed_hashes (source, sha256, checked_at)
               VALUES (?, ?, ?)
               ON CONFLICT(source) DO UPDATE SET sha256 = excluded.sha256,
               checked_at = excluded.checked_at""",
            (source, sha256, now),
        )
        self.conn.commit()

    # -- stats ------------------------------------------------------------
    def stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        unreported = self.count_unreported()
        by_source = {
            r["source"]: r["n"]
            for r in self.conn.execute(
                "SELECT source, COUNT(*) AS n FROM listings GROUP BY source"
            ).fetchall()
        }
        hashes = {
            r["source"]: {"sha256": r["sha256"][:12] + "…", "checked_at": r["checked_at"]}
            for r in self.conn.execute("SELECT source, sha256, checked_at FROM feed_hashes").fetchall()
        }
        return {
            "db_path": self.path,
            "total_listings": total,
            "unreported": unreported,
            "by_source": by_source,
            "feeds": hashes,
        }

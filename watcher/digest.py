"""Digest rendering: top-N matches grouped by source as one Telegram message."""

from __future__ import annotations

from datetime import date

from watcher.store import ScoredListing

SOURCE_LABELS = {
    "remoteok": "RemoteOK",
    "weworkremotely": "We Work Remotely",
    "hn": "HN Who's Hiring",
    "remotive": "Remotive",
    "arbeitnow": "Arbeitnow",
    "akhtaboot": "Akhtaboot",
}


def _escape(text: str) -> str:
    """Escape Telegram MarkdownV2 special chars in free-form feed text."""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, "\\" + ch)
    return text


def render_digest(
    items: list[ScoredListing],
    max_items: int = 15,
    run_date: str | None = None,
    empty_mode: str = "status",
) -> str:
    """Render the morning digest. empty_mode: 'status' -> short line, 'silent' -> ''."""
    day = run_date or date.today().isoformat()
    shown = items[:max_items]
    if not shown:
        if empty_mode == "silent":
            return ""
        return (
            f"\U0001f50e Job watcher — {day}\n"
            "Nothing new above your threshold today. Quiet days cost a few HTTP requests."
        )
    lines = [f"\U0001f50e Job watcher — {day} ({len(shown)} new)"]
    by_source: dict[str, list[ScoredListing]] = {}
    for item in shown:
        by_source.setdefault(item.source, []).append(item)
    for source, group in by_source.items():
        lines.append(f"\n*{_escape(SOURCE_LABELS.get(source, source))}*")
        for item in group:
            flag = "\U0001f30d remote" if item.remote else _escape(item.location or "onsite")
            lines.append(
                f"• *{_escape(item.title)}* — {_escape(item.company)} ({flag}) "
                f"— score {item.score:g}\n  {_escape(item.url)}"
            )
    if len(items) > max_items:
        lines.append(f"\n_+{len(items) - max_items} more in the database (max_items={max_items})_")
    return "\n".join(lines)

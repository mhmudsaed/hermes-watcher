"""Telegram delivery behind a thin adapter. Offline fake prints to console/file.

All network use sits behind TelegramSender; tests and demo use FakeSender.
"""

from __future__ import annotations

import abc
from pathlib import Path

import httpx


class SendError(Exception):
    pass


class BaseSender(abc.ABC):
    @abc.abstractmethod
    def send(self, text: str) -> str:
        """Deliver the digest; returns a human-readable receipt."""


class TelegramSender(BaseSender):
    """Real Telegram Bot API sender (live mode only, needs bot token + chat id)."""

    def __init__(self, bot_token: str, chat_id: str, timeout: float = 20.0):
        if not bot_token or not chat_id:
            raise SendError("bot token and chat id are both required")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, text: str) -> str:
        if not text:
            return "skipped: empty digest (silent mode)"
        try:
            resp = httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise SendError(f"telegram send failed: {exc}") from exc
        data = resp.json()
        if not data.get("ok"):
            raise SendError(f"telegram API error: {data}")
        return f"sent: message_id={data['result'].get('message_id')}"


class FakeSender(BaseSender):
    """Offline fake: prints to stdout and optionally appends to a file."""

    def __init__(self, out_file: str | Path | None = None):
        self.out_file = Path(out_file) if out_file else None
        self.sent: list[str] = []

    def send(self, text: str) -> str:
        self.sent.append(text)
        print(text)
        if self.out_file:
            self.out_file.parent.mkdir(parents=True, exist_ok=True)
            with self.out_file.open("a", encoding="utf-8") as fh:
                fh.write(text + "\n---\n")
        return f"fake-sent: {len(text)} chars" + (
            f" -> {self.out_file}" if self.out_file else " (stdout)"
        )

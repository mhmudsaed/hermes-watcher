"""Common listing shape every source adapter normalizes to."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Listing:
    source: str
    title: str
    company: str
    location: str = ""
    remote: bool = False
    url: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    posted_at: str | None = None

    def text_blob(self) -> str:
        """Lowercased searchable text used by the scorer. Data, never instructions."""
        return " ".join(
            [self.title, self.company, self.location, self.description, " ".join(self.tags)]
        ).lower()

    def title_blob(self) -> str:
        return f"{self.title} {self.company}".lower()

"""Keyword scoring against a configurable profile. Returns (score, why).

Feed content is untrusted data: scoring only matches literal keywords, never
treats listing text as instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from watcher.models import Listing


@dataclass
class Profile:
    include: dict[str, float] = field(default_factory=dict)  # keyword -> weight
    exclude: list[str] = field(default_factory=list)  # hard veto on title match
    exclude_description: list[str] = field(default_factory=list)  # veto anywhere
    title_boost: float = 2.0  # multiplier for hits in title/company vs body
    remote_bonus: float = 1.0
    jordan_bonus: float = 1.5
    threshold: float = 3.0  # digest cutoff

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        include = data.get("include", {}) or {}
        return cls(
            include={str(k).lower(): float(v) for k, v in include.items()},
            exclude=[str(k).lower() for k in (data.get("exclude", []) or [])],
            exclude_description=[
                str(k).lower() for k in (data.get("exclude_description", []) or [])
            ],
            title_boost=float(data.get("title_boost", 2.0)),
            remote_bonus=float(data.get("remote_bonus", 1.0)),
            jordan_bonus=float(data.get("jordan_bonus", 1.5)),
            threshold=float(data.get("threshold", 3.0)),
        )


def _contains(blob: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", blob) is not None


def score_listing(listing: Listing, profile: Profile) -> tuple[float, str]:
    blob = listing.text_blob()
    title = listing.title_blob()
    reasons: list[str] = []

    for veto in profile.exclude:
        if _contains(title, veto):
            return 0.0, f"excluded: title matches {veto!r}"
    for veto in profile.exclude_description:
        if _contains(blob, veto):
            return 0.0, f"excluded: matches {veto!r}"

    score = 0.0
    for keyword, weight in profile.include.items():
        if _contains(title, keyword):
            score += weight * profile.title_boost
            reasons.append(f"+{weight * profile.title_boost:g} title:{keyword}")
        elif _contains(blob, keyword):
            score += weight
            reasons.append(f"+{weight:g} {keyword}")

    if listing.remote and score > 0:
        score += profile.remote_bonus
        reasons.append(f"+{profile.remote_bonus:g} remote")
    loc = listing.location.lower()
    if ("jordan" in loc or "amman" in loc) and score > 0:
        score += profile.jordan_bonus
        reasons.append(f"+{profile.jordan_bonus:g} jordan")

    score = round(score, 2)
    why = "; ".join(reasons) if reasons else "no keyword hits"
    return score, why

"""Scoring tests against the default profile."""

from watcher.config import load_profile, repo_root
from watcher.models import Listing
from watcher.scoring import Profile, score_listing


def profile() -> Profile:
    return Profile.from_dict(load_profile(repo_root() / "profiles/default.yaml"))


def listing(**kw) -> Listing:
    base = dict(source="test", title="Python Automation Engineer",
                company="Acme", location="Remote", remote=True,
                url="https://example.com/j/1", description="")
    base.update(kw)
    return Listing(**base)


def test_python_remote_scores_above_threshold():
    p = profile()
    score, why = score_listing(
        listing(description="We need python, llm and rag experience for our chatbot."),
        p,
    )
    assert score >= p.threshold, why
    assert "python" in why


def test_title_hits_boost_more_than_body():
    p = profile()
    in_title, _ = score_listing(listing(title="Python Developer"), p)
    in_body, _ = score_listing(
        listing(title="Marketing Specialist", description="python a plus"), p
    )
    assert in_title > in_body > 0


def test_senior_title_vetoed():
    p = profile()
    score, why = score_listing(
        listing(title="Senior Python Engineer", description="python llm rag"), p
    )
    assert score == 0.0
    assert "excluded" in why


def test_security_clearance_vetoed():
    p = profile()
    score, why = score_listing(
        listing(title="Python Engineer",
                description="python role. Requires security clearance."),
        p,
    )
    assert score == 0.0
    assert "excluded" in why


def test_unrelated_posting_scores_zero():
    p = profile()
    score, why = score_listing(
        listing(title="Warehouse Shift Supervisor", company="Logistics Co",
                location="Amman", remote=False,
                description="Forklifts, inventory counts, night shifts.", url="https://example.com/j/9"),
        p,
    )
    assert score == 0.0
    assert why == "no keyword hits"


def test_jordan_bonus_applies():
    p = profile()
    amman, _ = score_listing(
        listing(title="Python Developer", location="Amman, Jordan", remote=False,
                description="python"), p,
    )
    elsewhere, _ = score_listing(
        listing(title="Python Developer", location="Berlin", remote=False,
                description="python"), p,
    )
    assert amman > elsewhere

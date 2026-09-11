# SPEC — Watcher (hermes-watcher)

Owner: Mahmoud Saeed · Built by: autonomous build agent · Backs: mahmoudsaeed.com/work/watcher-telegram-digest

## Mission

A daily job-feed watcher: polls a fixed set of public job boards, hashes feeds to skip
unchanged ones, scores new listings against a configurable profile, dedupes against a
local SQLite database keyed by URL, and delivers ONE curated morning digest to
Telegram. It only reads; it never applies to anything.

## Problem

Checking a handful of job boards by hand every morning takes real time and everything
blurs together. The useful version is not more listings but fewer: one message a day
with only what's worth reading, everything already seen filtered out.

## Scope (what to build)

1. **Sources (public APIs/RSS only, no scraping-with-login)**:
   RemoteOK API, We Work Remotely RSS, HN Who's Hiring (Algolia API),
   Remotive API, Arbeitnow API, Akhtaboot (Jordan; handle gracefully if no stable
   public feed — fetch best-effort or mark skipped-with-reason).
   Each source is an adapter: fetch + normalize to a common listing shape.
2. **Change detection**: each feed's content is hashed; scoring only runs when the
   hash differs from the last cycle. Quiet days cost a couple of HTTP requests.
3. **Store**: SQLite; every listing ever seen stored with URL as unique key — reruns
   can never re-report an old job. Digest is a view over this table.
4. **Scoring**: configurable profile (JSON/YAML): include/exclude keywords, weights,
   location/remote hints; returns score + why. Sensible defaults for a remote-first
   AI/automation junior profile.
5. **Digest**: single Telegram message (adapter; offline fake prints to console/file):
   top N new matches grouped by source, with title, company, location/remote flag,
   and direct URL. Configurable max items; "nothing new" day → short status line or
   silence (configurable).
6. **Scheduling**: `--once` one-shot mode; documented cron/systemd-timer setup for
   daily morning runs; a shipped example systemd timer file.
7. **CLI**: `run --once`, `digest --preview`, `sources`, `stats`.

## Hard design decisions (carry these through)

- Public feeds instead of scraping — no login, no fragile HTML where a feed exists.
- It only does work when something changed (feed hashing).
- A database, not a chat history — URL-keyed dedupe.

## Security & guardrails

- It only reads. Nothing is ever applied to, clicked, or submitted.
- Feeds are polled on a slow human-paced schedule, not hammered; respect intervals.
- A dead feed is skipped and noted; it never blocks the digest.
- Treat feed content as untrusted data.

## Stack

Python 3.11+, httpx + feedparser (or stdlib XML if practical), sqlite3 (stdlib),
Telegram adapter with offline fake. Fixture files for every source's payload in tests/.

## Testing requirements

- Offline: fixture payloads per source → normalization tests; hash-skip logic test
  (unchanged feed does zero scoring); URL dedupe test (rerun adds nothing); scoring
  tests; digest rendering test; "dead feed skipped, digest still builds" test.
- One-command demo: `scripts/demo.sh` runs a full cycle against fixture payloads and
  prints the rendered digest preview.

## Definition of Done (checklist)

- [ ] `pytest -q` fully green offline.
- [ ] `scripts/demo.sh` works: fixtures → digest preview printed.
- [ ] Example systemd timer + cron line documented in README.
- [ ] README.md + docs/TESTING.md + docs/STATUS.md + .env.example complete.
- [ ] All work committed; git status clean.

## Credentials for live mode (expand into docs/TESTING.md)

- Telegram: bot token + chat id (BotFather step-by-step; how to get chat id).
- No other credentials — all sources are public. Document rate/politeness settings.

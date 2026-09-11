# STATUS — hermes-watcher (living status, updated at acceptance)

## Done

- Six source adapters (fetch + normalize to `Listing`): RemoteOK API,
  We Work Remotely RSS (stdlib XML, no feedparser dependency), HN Who's Hiring
  via Algolia API (latest monthly thread search + thread-items parse),
  Remotive API, Arbeitnow API, Akhtaboot best-effort (probes candidate feed
  URLs, skips with recorded reason — verified Sep 2026 that no stable public
  Akhtaboot feed exists: candidate URLs return redirects/HTML/500s).
- Change detection: sha256 over raw feed bytes; unchanged feeds skip scoring
  entirely (proven by a scorer call-count test).
- SQLite store: URL-primary-key dedupe, feed-hash table, reported flags, digest
  view (`top_unreported`), stats.
- Scoring: YAML profile with include weights, title/company boost, remote +
  Jordan bonuses, title/full-text vetoes, threshold cutoff. Defaults target a
  remote-first AI/automation junior.
- Digest: single Telegram MarkdownV2 message, grouped by source, max-items cap
  with "+N more", `status`/`silent` empty modes.
- Delivery: `TelegramSender` (live) behind `BaseSender`; `FakeSender` (stdout +
  optional file) used by all tests and the demo.
- CLI: `run --once`, `digest --preview/--send`, `sources`, `stats`.
- Offline proof: `pytest -q` 27 passed; `scripts/demo.sh` green (cycle 1:
  `new=14, digest_items=3`; cycle 2 rerun: `new=0`, all feeds `unchanged`).
- Docs: README, docs/TESTING.md, docs/STATUS.md, .env.example, example systemd
  service + timer, cron line.

## Mocked / fixture-based (by design, per working agreement)

- All tests run against `tests/fixtures/` payloads captured from the real public
  feeds (Sep 2026) — no network in tests.
- `scripts/demo.sh` uses a MockTransport HTTP client + FakeSender; HN and
  Akhtaboot exercise the dead-feed path in the demo, live-capable paths covered
  by unit tests.

## Known limitations

- HN adapter reads top-level comments of the latest monthly thread only; jobs
  buried in reply chains are missed. Comment-to-listing parsing is heuristic
  ("Company | Role | Location" pipe convention).
- WWR adapter polls the programming category feed only; other categories
  (design, marketing, ...) are out of scope for the default profile.
- Digest is plain MarkdownV2 text; no inline buttons or per-job deep links
  beyond the source URL.
- Single-user SQLite; concurrent writers not supported (fine for one daily run).

## Decisions made

- Dropped the `feedparser` dependency: stdlib `xml.etree` handles the two RSS
  shapes (WWR + generic Akhtaboot fallback). Fewer deps, same coverage.
- Akhtaboot ships as skip-with-reason, NOT scraped: spec allows it, and the
  working agreement prefers public feeds over fragile HTML.
- Demo pins four single-request sources; HN's two-step lookup tested separately
  with mocked search+thread payloads.

## Next steps (post-acceptance, need a human)

1. Mahmoud supplies `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (BotFather steps in
   docs/TESTING.md) and runs the live verification checklist.
2. Install the systemd timer (or cron line) for daily 08:00 Asia/Amman runs.
3. Optional product work: per-category WWR feeds, reply-chain HN parsing,
   score-threshold auto-tuning from click-throughs (requires live run data).

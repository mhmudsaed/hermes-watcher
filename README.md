# hermes-watcher

A daily job-feed watcher. It polls a fixed set of public job boards, hashes feeds to
skip unchanged ones, scores new listings against a configurable profile, dedupes
against a local SQLite database keyed by URL, and delivers ONE curated morning
digest to Telegram. It only reads — it never applies to anything.

Checking a handful of job boards by hand every morning takes real time and everything
blurs together. The useful version is not more listings but fewer: one message a day
with only what's worth reading, everything already seen filtered out.

Backs the case study: mahmoudsaeed.com/work/watcher-telegram-digest

## Demo

▶️ The fetch → score → digest cycle — full-quality recording (plays inline):

https://github.com/user-attachments/assets/46df4d16-886b-45e8-8641-49e4da4ad550

One command runs a full fetch → score → digest cycle offline with zero credentials: `./scripts/demo.sh`. The suite is also one command — `pytest -q` → **27 passed**. The video above is a real recording (mildly sped up; it opens and closes on a title card). The [full-quality MP4](docs/assets/demo.mp4) is also in this repo.

## Architecture

```
public feeds ──► adapters (fetch + normalize) ──► sha256 change check ──► score ──► SQLite ──► one Telegram digest
   │                       │                           │                    │          │                │
   │              watcher/sources/*.py          watcher/hashing.py   watcher/scoring  watcher/store   watcher/notify
   │                                                                                (URL primary key) (FakeSender offline)
   └─ RemoteOK API, We Work Remotely RSS, HN Who's Hiring (Algolia), Remotive API,
      Arbeitnow API, Akhtaboot (Jordan; skipped-with-reason, no stable public feed)
```

Key design decisions (per spec):

- Public feeds instead of scraping — no login, no fragile HTML where a feed exists.
- Work only happens when something changed: each feed's raw bytes are hashed
  (sha256) and scoring runs only on a hash mismatch. Quiet days cost a few HTTP
  requests.
- A database, not chat history: every listing ever seen is stored with its URL as
  the unique key, so reruns can never re-report an old job.
- A dead feed is skipped and noted; it never blocks the digest.

## Install

Requires Python 3.11+.

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e '.[test]'
cp .env.example .env   # optional; empty Telegram creds = offline print mode
```

## Quickstart (offline demo, no credentials)

```bash
scripts/demo.sh
```

This runs the pytest suite, executes a full fixture-backed cycle twice (second run
proves hash-skip + dedupe: zero new), prints the rendered digest preview, and shows
`stats`. Everything offline — no network, no Telegram.

Manual CLI use:

```bash
.venv/bin/python -m watcher.cli run --once        # one poll cycle (FakeSender unless Telegram creds set)
.venv/bin/python -m watcher.cli digest --preview  # render current digest without sending
.venv/bin/python -m watcher.cli digest --send     # render + send via configured sender
.venv/bin/python -m watcher.cli sources           # configured sources + last feed hashes
.venv/bin/python -m watcher.cli stats             # database stats
```

## Configuration

| Variable | Default | What it does |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | Bot token from BotFather. Empty = offline print mode. |
| `TELEGRAM_CHAT_ID` | _(empty)_ | Chat to deliver the digest to. Empty = offline print mode. |
| `WATCHER_DB` | `data/watcher.db` | SQLite path (relative to repo root, or absolute). |
| `WATCHER_PROFILE` | `profiles/default.yaml` | Scoring profile (keywords, weights, vetoes, threshold). |
| `WATCHER_MAX_ITEMS` | `15` | Max listings per digest message. |
| `WATCHER_THRESHOLD` | `3.0` | Minimum score to include in the digest. |
| `WATCHER_EMPTY_MODE` | `status` | `status` = short "nothing new" line on quiet days; `silent` = send nothing. |
| `WATCHER_SOURCES` | all six | Comma-separated subset to poll. |
| `WATCHER_MIN_INTERVAL` | `2` | Seconds between feed requests (politeness). |
| `WATCHER_HTTP_TIMEOUT` | `20` | Per-request HTTP timeout in seconds. |

Tune scoring by editing `profiles/default.yaml`: `include` keyword weights,
`exclude` title vetoes, `exclude_description` full-text vetoes, bonuses, threshold.

## Scheduling (live mode)

systemd timer (ships in `systemd/`; edit paths, then install):

```bash
mkdir -p ~/.config/systemd/user
cp systemd/hermes-watcher.{service,timer} ~/.config/systemd/user/
# edit WorkingDirectory/EnvironmentFile paths inside the .service file
systemctl --user daemon-reload
systemctl --user enable --now hermes-watcher.timer
systemctl --user list-timers | grep hermes-watcher
```

Cron alternative (08:00 daily):

```cron
0 8 * * * cd ~/Codes/hermes-watcher && ./.venv/bin/python -m watcher.cli run --once >> data/watcher.log 2>&1
```

## Live-mode setup

See [docs/TESTING.md](docs/TESTING.md) (credentials, BotFather steps, politeness
notes) and [docs/STATUS.md](docs/STATUS.md) (what's done, mocked, and next).

## Security notes

- Read-only by design: fetches public feeds, never applies/clicks/submits.
- Feed content is untrusted data: matched as literal keywords only, never executed
  or treated as instructions; RSS parsed with stdlib XML (no entity expansion
  attacks surface beyond ElementTree defaults); HTML stripped before scoring.
- No secrets in code/logs/commits: Telegram creds live in `.env` (gitignored).
- Polite by default: 2s gap between feed requests, 20s timeouts, unchanged feeds
  are not re-fetched for scoring.

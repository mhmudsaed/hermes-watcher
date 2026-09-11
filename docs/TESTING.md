# TESTING — hermes-watcher

## Works WITHOUT credentials (do this first)

Everything below runs fully offline — no network, no Telegram, no setup beyond
the venv. This is the acceptance path.

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e '.[test]'

# full suite: 27 tests
.venv/bin/python -m pytest -q

# one-command demo: suite + fixture cycle x2 + digest preview + stats
scripts/demo.sh
```

What the suite covers (all against `tests/fixtures/`, never the network):

| Area | Tests |
|---|---|
| Source normalization | fixture payload per adapter: RemoteOK (legal-notice skip, 5 jobs), We Work Remotely RSS (3 items, HTML stripped), HN thread (4 comments -> listings), Remotive (3 jobs), Arbeitnow (remote/onsite flags); bad-payload rejection; Akhtaboot skipped-with-reason |
| Hash-skip | unchanged feed does zero scoring (scorer call-counted via monkeypatch); rerun reports `new=0`, all sources `unchanged` |
| URL dedupe | rerun inserts nothing; `seen_urls`; reported items never re-delivered |
| Scoring | above-threshold AI/automation match; title boost > body; senior-title veto; security-clearance veto; unrelated posting scores 0; Jordan bonus |
| Digest | grouped by source, `max_items` cap with "+N more", empty `status` vs `silent` modes |
| Dead feed | dead/parse-broken feed skipped, digest still builds from healthy sources |

Expected demo output (second cycle proves the core loop):

```
cycle 1: fetched={...4 sources...} | unchanged=[] | dead=['hn', 'akhtaboot'] | new=14 | digest_items=3 | ...
cycle 2 (rerun, expect zero new): fetched={} | unchanged=[...4 sources...] | dead=[...] | new=0 | digest_items=0 | ...
```

Note: the demo pins `WATCHER_SOURCES` to the four single-request JSON/RSS feeds.
`hn` (two-step thread lookup with an empty search in the demo harness) and
`akhtaboot` (no stable public feed) exercise the dead-feed path there; both are
covered live-capable by unit tests (`test_hn_thread_flow`, akhtaboot skip test).

## Needs credentials (live mode)

The ONLY credentials in the whole project are Telegram. All six job sources are
public — no API keys, no logins.

### 1. Create the bot, get the token

1. Open Telegram, message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, pick a display name (e.g. `Mahmoud Job Watcher`) and a username
   ending in `bot` (e.g. `mahmoud_job_watcher_bot`).
3. BotFather replies with the token, e.g. `123456789:AAH...`. Copy it.
4. Optional: `/setdescription`, `/setabouttext` — cosmetic only.

### 2. Get your chat id

1. Message your new bot anything (e.g. `hi`) from the account/chat that should
   receive the digest. For a channel: add the bot as admin and post once.
2. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser
   (replace `<TOKEN>` with the token from step 1).
3. Read `message.chat.id` (a person: e.g. `123456789`; a channel: e.g.
   `-1001234567890`). That is your chat id.

### 3. Wire it up

```bash
cp .env.example .env
# edit .env:
#   TELEGRAM_BOT_TOKEN=123456789:AAH...
#   TELEGRAM_CHAT_ID=123456789
.venv/bin/python -m watcher.cli digest --preview   # check the digest first
.venv/bin/python -m watcher.cli digest --send      # sends ONE real Telegram message
.venv/bin/python -m watcher.cli run --once         # full live poll cycle
```

With both `TELEGRAM_*` vars set, `run --once` delivers via the real Telegram Bot
API; with either empty it prints to stdout (FakeSender) and never touches the
network for delivery. `.env` is gitignored — tokens never enter commits or logs
(the sender logs only `message_id`, never the token).

### Live verification checklist (requires live run)

- [ ] `digest --send` arrives in the target chat, Markdown-formatted, links open.
- [ ] `run --once` against real feeds: all five stable sources fetch; akhtaboot
      records skipped-with-reason; digest arrives once.
- [ ] Second `run --once` within minutes: feeds mostly `unchanged`, `new=0`.
- [ ] systemd timer installed; `journalctl --user -u hermes-watcher.service`
      shows the morning run and its one-line summary.

## Rate / politeness settings

Defaults: 2s gap between feed requests (`WATCHER_MIN_INTERVAL`), 20s per-request
timeout (`WATCHER_HTTP_TIMEOUT`), one cycle per day. Feeds are polled on a slow
human-paced schedule and never hammered; unchanged feeds cost one conditional
fetch each. HN goes through the official Algolia API (search + one thread fetch),
not page scraping. Akhtaboot has no stable public feed and is skipped with a
recorded reason rather than scraped.

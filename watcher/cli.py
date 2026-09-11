"""CLI: run --once | digest --preview | sources | stats."""

from __future__ import annotations

import argparse
import json
import sys

from watcher import __version__
from watcher.config import Settings
from watcher.notify import FakeSender
from watcher.runner import make_sender, run_once
from watcher.sources import SOURCES
from watcher.store import Store


def cmd_run(args: argparse.Namespace, settings: Settings) -> int:
    if args.once:
        sender = make_sender(settings)
        result = run_once(settings, sender=sender)
        print(result.summary(), file=sys.stderr)
        return 0
    print("only --once is supported (scheduling is via cron/systemd timer)", file=sys.stderr)
    return 2


def cmd_digest(args: argparse.Namespace, settings: Settings) -> int:
    from watcher.digest import render_digest

    store = Store(settings.db_path)
    try:
        items = store.top_unreported(settings.max_items, settings.threshold)
        text = render_digest(items, max_items=settings.max_items, empty_mode=settings.empty_mode)
    finally:
        store.close()
    if args.send:
        print(make_sender(settings).send(text), file=sys.stderr)
    else:
        FakeSender().send(text)
    return 0


def cmd_sources(_args: argparse.Namespace, settings: Settings) -> int:
    from watcher.sources import get_source

    store = Store(settings.db_path)
    try:
        rows = []
        for name in settings.sources:
            try:
                url = get_source(name).feed_url
            except Exception as exc:  # unknown source configured
                url = f"ERROR: {exc}"
            h = store.feed_hash(name)
            rows.append({"source": name, "feed": url, "last_hash": (h[:12] + "…") if h else None})
        print(json.dumps(rows, indent=2))
    finally:
        store.close()
    return 0


def cmd_stats(_args: argparse.Namespace, settings: Settings) -> int:
    store = Store(settings.db_path)
    try:
        print(json.dumps(store.stats(), indent=2))
    finally:
        store.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="watcher", description="Daily job-feed watcher.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a poll cycle")
    r.add_argument("--once", action="store_true", required=True, help="one-shot poll cycle")
    r.set_defaults(func=cmd_run)

    d = sub.add_parser("digest", help="render the current digest")
    d.add_argument("--preview", action="store_true", help="print digest without sending")
    d.add_argument("--send", action="store_true", help="send via configured sender")
    d.set_defaults(func=cmd_digest)

    s = sub.add_parser("sources", help="list configured sources and hash state")
    s.set_defaults(func=cmd_sources)

    st = sub.add_parser("stats", help="database stats")
    st.set_defaults(func=cmd_stats)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    if getattr(args, "cmd", None) == "digest" and not (args.preview or args.send):
        args.preview = True
    return args.func(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())

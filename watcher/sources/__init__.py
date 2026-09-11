"""Source adapters for the six public feeds."""

from watcher.sources.base import SourceAdapter, SourceError, SourceUnavailable  # noqa: F401
from watcher.sources.remoteok import RemoteOKSource  # noqa: F401
from watcher.sources.weworkremotely import WeWorkRemotelySource  # noqa: F401
from watcher.sources.hn import HNWhoIsHiringSource  # noqa: F401
from watcher.sources.remotive import RemotiveSource  # noqa: F401
from watcher.sources.arbeitnow import ArbeitnowSource  # noqa: F401
from watcher.sources.akhtaboot import AkhtabootSource  # noqa: F401

SOURCES: dict[str, type[SourceAdapter]] = {
    "remoteok": RemoteOKSource,
    "weworkremotely": WeWorkRemotelySource,
    "hn": HNWhoIsHiringSource,
    "remotive": RemotiveSource,
    "arbeitnow": ArbeitnowSource,
    "akhtaboot": AkhtabootSource,
}


def get_source(name: str) -> SourceAdapter:
    try:
        return SOURCES[name]()
    except KeyError:
        raise SourceError(f"unknown source: {name!r} (known: {sorted(SOURCES)})") from None

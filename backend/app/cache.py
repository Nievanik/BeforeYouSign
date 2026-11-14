"""JSON file cache for every external call. OFFLINE=1 means cache only, never the network."""
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from app import config

CACHE_DIR = config.DEMO_DIR / "cache" if config.DEMO else Path(__file__).resolve().parents[1] / "cache"


class CacheMiss(Exception):
    """OFFLINE=1 and this request was never cached."""


def cached(source: str, request: dict, fetch: Callable[[], Any]) -> Any:
    """Return the cached JSON for (source, request), or call fetch() and store its result."""
    key = hashlib.sha1(json.dumps(request, sort_keys=True).encode()).hexdigest()
    path = CACHE_DIR / source / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    if config.OFFLINE:
        raise CacheMiss(f"{source}: no cached response for {request}")
    result = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(result))
    tmp.replace(path)  # atomic, so a crash never leaves a half-written cache file
    return result

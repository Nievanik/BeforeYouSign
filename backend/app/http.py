"""One HTTP client for every tool: generic User-Agent, retries on 429/5xx with backoff."""
import random
import time

import httpx

from app import config

_client = httpx.Client(headers={"User-Agent": config.USER_AGENT}, timeout=120, follow_redirects=True)


def request(method: str, url: str, retries: int = 4, **kw) -> httpx.Response:
    for attempt in range(retries + 1):
        try:
            r = _client.request(method, url, **kw)
        except httpx.TransportError:
            if attempt == retries:
                raise
        else:
            if r.status_code != 429 and r.status_code < 500 or attempt == retries:
                return r
            if r.headers.get("Retry-After", "").isdigit():
                time.sleep(min(int(r.headers["Retry-After"]), 60))
                continue
        time.sleep(min(2**attempt, 30) + random.random())
    raise AssertionError("unreachable")

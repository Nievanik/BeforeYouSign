import pytest

from app import cache, config


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)


def test_fetches_once_then_reads_cache():
    calls = []
    fetch = lambda: calls.append(1) or {"v": 1}
    assert cache.cached("src", {"q": 1}, fetch) == {"v": 1}
    assert cache.cached("src", {"q": 1}, fetch) == {"v": 1}
    assert len(calls) == 1


def test_offline_miss_raises_without_fetching(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE", True)
    with pytest.raises(cache.CacheMiss):
        cache.cached("src", {"q": 2}, lambda: pytest.fail("fetched while offline"))

"""Persistent cache behavior through public APIs and isolated local storage."""

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from jira_as import JiraCache, get_cache


@pytest.fixture
def clock(monkeypatch):
    now = SimpleNamespace(seconds=1000.0)
    # Replace only the cache's clock dependency, without changing global time.
    monkeypatch.setattr("jira_as.cache.time", SimpleNamespace(time=lambda: now.seconds))
    return now


@pytest.fixture
def cache(tmp_path):
    with JiraCache(cache_dir=str(tmp_path / "cache")) as instance:
        yield instance


def test_json_round_trip_replacement_categories_and_persistence(tmp_path):
    directory = str(tmp_path / "cache")
    value = {"summary": "Résumé", "labels": ["release"], "active": True}
    with get_cache(directory) as cache:
        assert cache.get("SBX-1", "issue") is None
        cache.set("SBX-1", value, "issue")
        cache.set("SBX-1", ["project data"], "project")
        assert cache.get("SBX-1", "issue") == value
        value["labels"].append("not persisted")
        assert cache.get("SBX-1", "issue")["labels"] == ["release"]
        cache.set("SBX-1", {"summary": "Replacement"}, "issue")
        assert cache.get_stats().entry_count == 2

    with JiraCache(directory) as reopened:
        assert reopened.get("SBX-1", "issue") == {"summary": "Replacement"}
        assert reopened.get("SBX-1", "project") == ["project data"]


@pytest.mark.parametrize(
    "category, seconds",
    [
        ("issue", 300),
        ("project", 3600),
        ("user", 3600),
        ("field", 86400),
        ("search", 60),
        ("unlisted", 300),
    ],
)
def test_category_ttl_expires_and_removes_entry(cache, clock, category, seconds):
    cache.set("entry", {"value": 7}, category)
    clock.seconds += seconds - 1
    assert cache.get("entry", category) == {"value": 7}
    clock.seconds += 2
    assert cache.get("entry", category) is None
    stats = cache.get_stats()
    assert (stats.entry_count, stats.hits, stats.misses) == (0, 1, 1)
    assert stats.total_size_bytes == 0
    assert stats.by_category == {}


def test_custom_ttl_overrides_category(cache, clock):
    cache.set("short", "value", "field", ttl=timedelta(seconds=10))
    clock.seconds += 9
    assert cache.get("short", "field") == "value"
    clock.seconds += 2
    assert cache.get("short", "field") is None


def test_capacity_evicts_least_recently_used_value(tmp_path, clock):
    # Each JSON string occupies 10 bytes, so the cache fits three entries.
    with JiraCache(str(tmp_path / "cache"), max_size_mb=30 / (1024 * 1024)) as cache:
        cache.set("first", "aaaaaaaa")
        clock.seconds += 1
        cache.set("second", "bbbbbbbb")
        clock.seconds += 1
        cache.set("third", "cccccccc")
        clock.seconds += 1
        assert cache.get("first") == "aaaaaaaa"
        clock.seconds += 1
        cache.set("fourth", "dddddddd")
        assert cache.get("second") is None
        assert cache.get("first") == "aaaaaaaa"
        assert cache.get("third") == "cccccccc"
        assert cache.get("fourth") == "dddddddd"
        assert cache.get_stats().total_size_bytes == 30


def test_capacity_reclaims_expired_data_before_live_data(tmp_path, clock):
    with JiraCache(str(tmp_path / "cache"), max_size_mb=20 / (1024 * 1024)) as cache:
        cache.set("live", "aaaaaaaa")
        clock.seconds += 1
        cache.set("expired", "bbbbbbbb", ttl=timedelta(seconds=1))
        clock.seconds += 2
        cache.set("new", "cccccccc")
        assert cache.get("live") == "aaaaaaaa"
        assert cache.get("expired") is None
        assert cache.get("new") == "cccccccc"
        assert cache.get_stats().entry_count == 2


def test_rejected_values_preserve_existing_cache(tmp_path):
    with get_cache(str(tmp_path / "cache"), max_size_mb=20 / (1024 * 1024)) as cache:
        cache.set("kept", "value")
        with pytest.raises(ValueError, match="exceeds maximum cache size"):
            cache.set("oversized", "x" * 21)
        with pytest.raises(TypeError, match="JSON serializable"):
            cache.set("invalid", object())
        assert cache.get("kept") == "value"
        assert cache.get("oversized") is None
        assert cache.get("invalid") is None
        assert cache.get_stats().entry_count == 1


@pytest.mark.parametrize(
    "selection, removed",
    [
        ({"key": "SBX-1", "category": "issue"}, {("SBX-1", "issue")}),
        (
            {"pattern": "SBX-*", "category": "issue"},
            {("SBX-1", "issue"), ("SBX-2", "issue")},
        ),
        (
            {"pattern": "SBX-?"},
            {("SBX-1", "issue"), ("SBX-2", "issue"), ("SBX-1", "project")},
        ),
        (
            {"category": "issue"},
            {("SBX-1", "issue"), ("SBX-2", "issue"), ("OTHER-1", "issue")},
        ),
        ({"pattern": "MISSING-*"}, set()),
    ],
)
def test_invalidation_counts_and_unrelated_values(cache, selection, removed):
    entries = {
        ("SBX-1", "issue"),
        ("SBX-2", "issue"),
        ("SBX-1", "project"),
        ("OTHER-1", "issue"),
    }
    for key, category in entries:
        cache.set(key, f"{category}:{key}", category)
    assert cache.invalidate(**selection) == len(removed)
    assert cache.invalidate(**selection) == 0
    for key, category in entries:
        expected = None if (key, category) in removed else f"{category}:{key}"
        assert cache.get(key, category) == expected


def test_clear_reports_count_and_persists_removal(cache):
    cache.set("one", 1)
    cache.set("two", 2, "issue")
    assert cache.clear() == 2
    assert cache.clear() == 0
    assert cache.get("one") is None
    assert cache.get("two", "issue") is None
    assert cache.get_stats().entry_count == 0


def test_statistics_report_categories_sizes_and_hit_rate(cache):
    empty = cache.get_stats()
    assert (empty.entry_count, empty.total_size_bytes, empty.hit_rate) == (0, 0, 0.0)
    cache.set("one", "abc", "issue")  # JSON string: five bytes.
    cache.set("two", [1, 2], "project")  # JSON array: six bytes.
    assert cache.get("one", "issue") == "abc"
    assert cache.get("missing") is None
    stats = cache.get_stats()
    assert (stats.hits, stats.misses, stats.hit_rate) == (1, 1, 0.5)
    assert stats.entry_count == 2
    assert stats.total_size_bytes == 11
    assert stats.by_category == {
        "issue": {"count": 1, "size_bytes": 5},
        "project": {"count": 1, "size_bytes": 6},
    }


@pytest.mark.parametrize("query", ["project = SBX", "summary ~ " + "x" * 250])
def test_generated_keys_are_stable_and_usable(cache, query):
    key = cache.generate_key("search", query, limit=10, start=0)
    assert key == cache.generate_key("search", query, start=0, limit=10)
    assert key != cache.generate_key("search", query, start=1, limit=10)
    assert key != cache.generate_key("issue", query, start=0, limit=10)
    assert len(key) <= 200
    cache.set(key, ["SBX-1"], "search")
    assert cache.get(key, "search") == ["SBX-1"]


def test_default_directory_is_under_redirected_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    with get_cache() as cache:
        cache.set("saved", True)
    directory = tmp_path / ".jira-skills" / "cache"
    assert directory.stat().st_mode & 0o777 == 0o700
    with JiraCache(str(directory)) as reopened:
        assert reopened.get("saved") is True


def test_context_manager_propagates_caller_exception(tmp_path):
    directory = str(tmp_path / "cache")
    with pytest.raises(RuntimeError, match="caller failed"):
        with JiraCache(directory) as cache:
            cache.set("committed", True)
            raise RuntimeError("caller failed")
    with JiraCache(directory) as reopened:
        assert reopened.get("committed") is True

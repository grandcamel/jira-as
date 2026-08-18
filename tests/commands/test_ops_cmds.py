"""
Unit tests for ops CLI commands.

Tests cover:
- cache-status: Display cache statistics
- cache-clear: Clear cache entries
- cache-warm: Pre-warm cache with metadata
- discover-project: Discover project context
"""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from jira_as.cli.commands.ops_cmds import (
    _analyze_field_fill_rates,
    _analyze_parent_hierarchy,
    _analyze_value_distributions,
    _cache_clear_impl,
    _cache_status_impl,
    _cache_warm_impl,
    _discover_project_impl,
    _format_bytes,
    _format_cache_clear,
    _format_cache_status,
    _format_cache_warm,
    _format_discover_project,
    _is_critical_error,
    ops,
)

# =============================================================================
# Helper Function Tests
# =============================================================================


@pytest.mark.unit
class TestFormatBytes:
    """Tests for the _format_bytes helper function."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        assert _format_bytes(512) == "512 B"
        assert _format_bytes(1024) == "1.0 KB"
        assert _format_bytes(1536) == "1.5 KB"
        assert _format_bytes(1024 * 1024) == "1.0 MB"
        assert _format_bytes(1024 * 1024 * 1024) == "1.0 GB"


@pytest.mark.unit
class TestIsCriticalError:
    """Tests for the _is_critical_error helper function."""

    def test_regular_exception_not_critical(self):
        """Test that regular exceptions are not critical."""
        assert _is_critical_error(ValueError("test")) is False

    def test_generic_exception_not_critical(self):
        """Test that generic exceptions are not critical."""
        assert _is_critical_error(Exception("test")) is False


# =============================================================================
# Mock Classes
# =============================================================================


class MockCacheStats:
    """Mock for JiraCache.get_stats() return value."""

    def __init__(
        self,
        total_size_bytes=1024 * 1024,
        entry_count=100,
        hits=80,
        misses=20,
        hit_rate=0.8,
        by_category=None,
    ):
        self.total_size_bytes = total_size_bytes
        self.entry_count = entry_count
        self.hits = hits
        self.misses = misses
        self.hit_rate = hit_rate
        self.by_category = by_category or {
            "issue": {"count": 50, "size_bytes": 512 * 1024},
            "project": {"count": 50, "size_bytes": 512 * 1024},
        }


# =============================================================================
# Cache Status Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestCacheStatusImpl:
    """Tests for the _cache_status_impl implementation function."""

    def test_cache_status_basic(self):
        """Test getting cache status."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()
        mock_cache.max_size = 100 * 1024 * 1024

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = _cache_status_impl()

        assert result["total_size_bytes"] == 1024 * 1024
        assert result["entry_count"] == 100
        assert result["hits"] == 80
        assert result["misses"] == 20
        assert result["hit_rate"] == 0.8


@pytest.mark.unit
class TestFormatCacheStatus:
    """Tests for the _format_cache_status formatting function."""

    def test_format_cache_status_basic(self):
        """Test formatting cache status."""
        stats = {
            "total_size_bytes": 1024 * 1024,
            "max_size_bytes": 100 * 1024 * 1024,
            "entry_count": 100,
            "hits": 80,
            "misses": 20,
            "hit_rate": 0.8,
            "by_category": {
                "issue": {"count": 50, "size_bytes": 512 * 1024},
            },
        }

        result = _format_cache_status(stats)

        assert "Cache Statistics:" in result
        assert "1.0 MB" in result
        assert "100" in result
        assert "80.0%" in result

    def test_format_cache_status_no_requests(self):
        """Test formatting cache status with no requests."""
        stats = {
            "total_size_bytes": 0,
            "max_size_bytes": 100 * 1024 * 1024,
            "entry_count": 0,
            "hits": 0,
            "misses": 0,
            "hit_rate": 0,
            "by_category": {},
        }

        result = _format_cache_status(stats)

        assert "N/A (no requests)" in result
        assert "No cached entries" in result


# =============================================================================
# Cache Clear Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestCacheClearImpl:
    """Tests for the _cache_clear_impl implementation function."""

    def test_cache_clear_dry_run(self):
        """Test cache clear in dry-run mode."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats(entry_count=100)

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = _cache_clear_impl(dry_run=True)

        assert result["dry_run"] is True
        assert result["entries_before"] == 100
        mock_cache.clear.assert_not_called()
        mock_cache.invalidate.assert_not_called()

    def test_cache_clear_all(self):
        """Test clearing all cache entries."""
        mock_cache = MagicMock()
        mock_cache.get_stats.side_effect = [
            MockCacheStats(entry_count=100, total_size_bytes=1024 * 1024),
            MockCacheStats(entry_count=0, total_size_bytes=0),
        ]
        mock_cache.clear.return_value = 100

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = _cache_clear_impl(force=True)

        assert result["cleared_count"] == 100
        assert result["dry_run"] is False
        mock_cache.clear.assert_called_once()

    def test_cache_clear_by_category(self):
        """Test clearing cache by category."""
        mock_cache = MagicMock()
        mock_cache.get_stats.side_effect = [
            MockCacheStats(entry_count=100),
            MockCacheStats(entry_count=50),
        ]
        mock_cache.invalidate.return_value = 50

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = _cache_clear_impl(category="issue", force=True)

        assert result["cleared_count"] == 50
        mock_cache.invalidate.assert_called_once_with(category="issue")

    def test_cache_clear_key_requires_category(self):
        """Test that --key requires --category."""
        with pytest.raises(ValueError, match="--key requires --category"):
            _cache_clear_impl(key="test-key", force=True)


@pytest.mark.unit
class TestFormatCacheClear:
    """Tests for the _format_cache_clear formatting function."""

    def test_format_cache_clear_dry_run(self):
        """Test formatting dry-run cache clear."""
        result = {
            "dry_run": True,
            "description": "all cache entries",
            "entries_before": 100,
            "size_before_bytes": 1024 * 1024,
        }

        output = _format_cache_clear(result)

        assert "DRY RUN:" in output
        assert "all cache entries" in output
        assert "100" in output

    def test_format_cache_clear_applied(self):
        """Test formatting applied cache clear."""
        result = {
            "dry_run": False,
            "cleared_count": 50,
            "freed_bytes": 512 * 1024,
        }

        output = _format_cache_clear(result)

        assert "Cleared 50" in output
        assert "Freed" in output


# =============================================================================
# Cache Warm Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestCacheWarmImpl:
    """Tests for the _cache_warm_impl implementation function."""

    def test_cache_warm_projects(self, mock_jira_client):
        """Test warming project cache."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()

        mock_jira_client.get.return_value = [
            {"key": "PROJ1", "name": "Project 1"},
            {"key": "PROJ2", "name": "Project 2"},
        ]

        # Configure mock to work as a context manager
        mock_jira_client.__enter__ = MagicMock(return_value=mock_jira_client)
        mock_jira_client.__exit__ = MagicMock(return_value=False)

        with (
            patch(
                "jira_as.cli.commands.ops_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.ops_cmds.JiraCache",
                return_value=mock_cache,
            ),
        ):
            result = _cache_warm_impl(projects=True)

        assert result["total_cached"] == 2
        assert "projects" in result["warmed"]
        mock_jira_client.__exit__.assert_called_once()

    def test_cache_warm_fields(self, mock_jira_client):
        """Test warming field cache."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()

        mock_jira_client.get.return_value = [
            {"id": "field1", "name": "Field 1"},
            {"id": "field2", "name": "Field 2"},
        ]

        with (
            patch(
                "jira_as.cli.commands.ops_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.ops_cmds.JiraCache",
                return_value=mock_cache,
            ),
        ):
            result = _cache_warm_impl(fields=True)

        # Should warm fields, issue types, priorities, statuses
        assert result["total_cached"] > 0
        assert "fields" in result["warmed"]

    def test_cache_warm_all(self, mock_jira_client):
        """Test warming all caches."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()

        mock_jira_client.get.return_value = []

        with (
            patch(
                "jira_as.cli.commands.ops_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.ops_cmds.JiraCache",
                return_value=mock_cache,
            ),
        ):
            result = _cache_warm_impl(warm_all=True)

        assert "total_cached" in result
        assert "cache_size_bytes" in result

    def test_cache_warm_no_options_error(self):
        """Test that at least one option is required."""
        with pytest.raises(ValueError, match="At least one warming option"):
            _cache_warm_impl()


@pytest.mark.unit
class TestFormatCacheWarm:
    """Tests for the _format_cache_warm formatting function."""

    def test_format_cache_warm_success(self):
        """Test formatting successful cache warming."""
        result = {
            "total_cached": 150,
            "cache_size_bytes": 2 * 1024 * 1024,
        }

        output = _format_cache_warm(result)

        assert "Cache warming complete" in output
        assert "150" in output

    def test_format_cache_warm_with_errors(self):
        """Test formatting cache warm with errors."""
        result = {
            "total_cached": 50,
            "cache_size_bytes": 1024 * 1024,
            "errors": ["Connection timeout", "Rate limit"],
        }

        output = _format_cache_warm(result)

        assert "Warnings:" in output
        assert "Connection timeout" in output


# =============================================================================
# Discover Project Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestDiscoverProjectImpl:
    """Tests for the _discover_project_impl implementation function."""

    def test_discover_project_basic(self, mock_jira_client, sample_project):
        """Test discovering a project."""
        mock_jira_client.get_project.return_value = deepcopy(sample_project)
        mock_jira_client.get_project_statuses.return_value = [
            {
                "id": "1",
                "name": "Task",
                "statuses": [{"name": "Open"}, {"name": "Done"}],
            }
        ]
        mock_jira_client.get_project_components.return_value = []
        mock_jira_client.get_project_versions.return_value = []
        mock_jira_client.get.return_value = []  # priorities
        mock_jira_client.find_assignable_users.return_value = []
        mock_jira_client.search_issues.return_value = {"issues": []}

        # Configure mock to work as a context manager
        mock_jira_client.__enter__ = MagicMock(return_value=mock_jira_client)
        mock_jira_client.__exit__ = MagicMock(return_value=False)

        with patch(
            "jira_as.cli.commands.ops_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _discover_project_impl(project_key="PROJ")

        assert "metadata" in result
        assert "patterns" in result
        assert result["metadata"]["project_key"] == "PROJ"
        mock_jira_client.__exit__.assert_called_once()


@pytest.mark.unit
class TestFormatDiscoverProject:
    """Tests for the _format_discover_project formatting function."""

    def test_format_discover_project(self):
        """Test formatting project discovery."""
        context = {
            "metadata": {
                "project_key": "PROJ",
                "project_name": "Test Project",
                "project_type": "software",
                "is_team_managed": False,
                "issue_types": [{"name": "Task"}],
                "components": [],
                "versions": [],
                "assignable_users": [],
            },
            "patterns": {
                "sample_size": 50,
                "sample_period_days": 30,
                "top_assignees": [{"display_name": "John Doe"}],
                "common_labels": ["bug", "feature"],
            },
        }

        output = _format_discover_project(context)

        assert "Project: PROJ" in output
        assert "Test Project" in output
        assert "software" in output
        assert "John Doe" in output


# =============================================================================
# CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestCacheStatusCommand:
    """Tests for the cache-status CLI command."""

    def test_cache_status_cli(self, cli_runner):
        """Test CLI cache-status command."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()
        mock_cache.max_size = 100 * 1024 * 1024

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = cli_runner.invoke(ops, ["cache-status"])

        assert result.exit_code == 0
        assert "Cache Statistics:" in result.output

    def test_cache_status_cli_json(self, cli_runner):
        """Test CLI cache-status with JSON output."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()
        mock_cache.max_size = 100 * 1024 * 1024

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = cli_runner.invoke(ops, ["cache-status", "--json"])

        assert result.exit_code == 0
        assert "{" in result.output


@pytest.mark.unit
class TestCacheClearCommand:
    """Tests for the cache-clear CLI command."""

    def test_cache_clear_cli_dry_run(self, cli_runner):
        """Test CLI cache-clear with dry-run."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = cli_runner.invoke(ops, ["cache-clear", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN:" in result.output

    def test_cache_clear_cli_force(self, cli_runner):
        """Test CLI cache-clear with --force."""
        mock_cache = MagicMock()
        mock_cache.get_stats.side_effect = [
            MockCacheStats(),
            MockCacheStats(entry_count=0, total_size_bytes=0),
        ]
        mock_cache.clear.return_value = 100

        with patch(
            "jira_as.cli.commands.ops_cmds.JiraCache",
            return_value=mock_cache,
        ):
            result = cli_runner.invoke(ops, ["cache-clear", "--force"])

        assert result.exit_code == 0
        assert "Cleared" in result.output


@pytest.mark.unit
class TestCacheWarmCommand:
    """Tests for the cache-warm CLI command."""

    def test_cache_warm_cli_no_options_error(self, cli_runner):
        """Test CLI cache-warm fails without options."""
        result = cli_runner.invoke(ops, ["cache-warm"])

        assert result.exit_code != 0
        assert "At least one warming option" in result.output

    def test_cache_warm_cli_projects(self, cli_runner, mock_jira_client):
        """Test CLI cache-warm with --projects."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = MockCacheStats()
        mock_jira_client.get.return_value = [{"key": "PROJ"}]

        with (
            patch(
                "jira_as.cli.cli_utils.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.ops_cmds.JiraCache",
                return_value=mock_cache,
            ),
        ):
            result = cli_runner.invoke(ops, ["cache-warm", "--projects"])

        assert result.exit_code == 0


@pytest.mark.unit
class TestDiscoverProjectCommand:
    """Tests for the discover-project CLI command."""

    def test_discover_project_cli(self, cli_runner, mock_jira_client, sample_project):
        """Test CLI discover-project command."""
        mock_jira_client.get_project.return_value = deepcopy(sample_project)
        mock_jira_client.get_project_statuses.return_value = []
        mock_jira_client.get_project_components.return_value = []
        mock_jira_client.get_project_versions.return_value = []
        mock_jira_client.get.return_value = []
        mock_jira_client.find_assignable_users.return_value = []
        mock_jira_client.search_issues.return_value = {"issues": []}

        with patch(
            "jira_as.cli.commands.ops_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(ops, ["discover-project", "PROJ"])

        assert result.exit_code == 0
        assert "Project: PROJ" in result.output

    def test_discover_project_cli_json(
        self, cli_runner, mock_jira_client, sample_project
    ):
        """Test CLI discover-project with JSON output."""
        mock_jira_client.get_project.return_value = deepcopy(sample_project)
        mock_jira_client.get_project_statuses.return_value = []
        mock_jira_client.get_project_components.return_value = []
        mock_jira_client.get_project_versions.return_value = []
        mock_jira_client.get.return_value = []
        mock_jira_client.find_assignable_users.return_value = []
        mock_jira_client.search_issues.return_value = {"issues": []}

        with patch(
            "jira_as.cli.commands.ops_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(ops, ["discover-project", "PROJ", "-o", "json"])

        assert result.exit_code == 0
        assert "{" in result.output


# =============================================================================
# discover-project analyses
# =============================================================================


class TestFieldFillRates:
    """Fill rates say how often a field actually carries a value."""

    def test_counts_populated_fields(self):
        """Only non-empty values count as filled."""
        issues = [
            {"fields": {"assignee": {"accountId": "a"}, "labels": ["x"]}},
            {"fields": {"assignee": None, "labels": []}},
        ]

        result = _analyze_field_fill_rates(issues, ["assignee", "labels"])

        assert result["assignee"] == {"filled": 1, "total": 2, "percentage": 50.0}
        assert result["labels"] == {"filled": 1, "total": 2, "percentage": 50.0}

    def test_field_never_present_is_zero_not_missing(self):
        """A field absent everywhere still gets a 0% entry."""
        result = _analyze_field_fill_rates([{"fields": {}}], ["duedate"])

        assert result["duedate"]["percentage"] == 0.0

    def test_empty_sample(self):
        """No issues means no rates."""
        assert _analyze_field_fill_rates([], ["assignee"]) == {}


class TestValueDistributions:
    """Distributions show the values a project actually uses."""

    def test_counts_scalar_and_list_fields(self):
        """Objects and arrays of objects are both counted by name."""
        issues = [
            {
                "fields": {
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                    "components": [{"name": "api"}, {"name": "web"}],
                }
            },
            {
                "fields": {
                    "status": {"name": "Open"},
                    "priority": {"name": "Low"},
                    "components": [{"name": "api"}],
                }
            },
        ]

        result = _analyze_value_distributions(issues)

        assert result["status"]["Open"] == {"count": 2, "percentage": 100.0}
        assert result["priority"]["High"]["count"] == 1
        assert result["components"]["api"]["count"] == 2

    def test_ranks_and_truncates(self):
        """Only the top N values are reported, most common first."""
        issues = [{"fields": {"status": {"name": f"S{n % 12}"}}} for n in range(120)]

        result = _analyze_value_distributions(issues, top_n=3)

        assert len(result["status"]) == 3

    def test_absent_fields_are_omitted(self):
        """A field with no values does not appear at all."""
        result = _analyze_value_distributions([{"fields": {}}])

        assert result == {}


class TestParentHierarchy:
    """Parent analysis says whether new issues need a parent."""

    def test_maps_child_types_to_parent_types(self):
        """The child-to-parent mapping is built from the sample."""
        issues = [
            {
                "fields": {
                    "issuetype": {"name": "Story"},
                    "parent": {"fields": {"issuetype": {"name": "Epic"}}},
                }
            },
            {
                "fields": {
                    "issuetype": {"name": "Sub-task"},
                    "parent": {"fields": {"issuetype": {"name": "Story"}}},
                }
            },
        ]

        result = _analyze_parent_hierarchy(issues)

        assert result["issues_with_parent"] == 2
        assert result["percentage"] == 100.0
        assert result["child_to_parent_types"]["Story"] == {"Epic": 1}
        assert result["parent_issue_types"] == {"Epic": 1, "Story": 1}

    def test_hint_when_parents_are_the_norm(self):
        """A mostly-parented project tells you to pass --parent."""
        issues = [
            {
                "fields": {
                    "issuetype": {"name": "Story"},
                    "parent": {"fields": {"issuetype": {"name": "Epic"}}},
                }
            }
        ] * 9 + [{"fields": {"issuetype": {"name": "Task"}}}]

        assert "set --parent" in _analyze_parent_hierarchy(issues)["hint"]

    def test_hint_when_project_is_flat(self):
        """No parents at all is reported as a flat project."""
        result = _analyze_parent_hierarchy(
            [{"fields": {"issuetype": {"name": "Task"}}}]
        )

        assert result["issues_with_parent"] == 0
        assert "flat" in result["hint"]

    def test_hint_when_parents_are_optional(self):
        """A mixed project says --parent is optional."""
        issues = [
            {
                "fields": {
                    "issuetype": {"name": "Story"},
                    "parent": {"fields": {"issuetype": {"name": "Epic"}}},
                }
            }
        ] + [{"fields": {"issuetype": {"name": "Task"}}}] * 4

        assert "optional" in _analyze_parent_hierarchy(issues)["hint"]

    def test_empty_sample(self):
        """No issues means no hierarchy data."""
        assert _analyze_parent_hierarchy([]) == {}

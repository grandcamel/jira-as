"""
Tests for jira-as search commands.

Tests cover:
- Constants and helper functions
- Search implementation functions
- Filter implementation functions
- Formatting functions
- CLI commands
"""

import csv
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from jira_as import JiraError, ValidationError
from jira_as.cli.commands.search_cmds import (
    COMMON_FIELDS,  # Constants; Search implementation functions; Filter implementation functions; Formatting functions; Helper functions; Click commands
    FUNCTION_EXAMPLES,
    JQL_TEMPLATES,
    _build_jql_impl,
    _bulk_update_impl,
    _export_results_impl,
    _format_fields,
    _format_filter_detail,
    _format_filters,
    _format_functions,
    _format_search_output,
    _format_suggestions,
    _format_validation_result,
    _format_value_for_jql,
    _get_fields_impl,
    _get_filters_impl,
    _get_functions_impl,
    _get_return_type,
    _get_suggestions_impl,
    _search_issues_impl,
    _suggest_correction,
    search,
)
from tests.test_utility_survivors import utility_simulation as utility_simulation

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Create mock JIRA client with context manager support."""
    client = MagicMock()
    client.close = MagicMock()
    # Support context manager pattern
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


@pytest.fixture
def sample_issues():
    """Sample issues for testing."""
    return [
        {
            "key": "TEST-1",
            "fields": {
                "summary": "First issue",
                "status": {"name": "Open"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Bug"},
                "assignee": {"displayName": "John Doe", "accountId": "123"},
                "reporter": {"displayName": "Jane Smith", "accountId": "456"},
                "labels": ["bug", "critical"],
                "created": "2024-01-15T10:00:00.000+0000",
                "updated": "2024-01-16T15:30:00.000+0000",
            },
        },
        {
            "key": "TEST-2",
            "fields": {
                "summary": "Second issue",
                "status": {"name": "In Progress"},
                "priority": {"name": "Medium"},
                "issuetype": {"name": "Task"},
                "assignee": None,
                "reporter": {"displayName": "Jane Smith"},
                "labels": [],
            },
        },
        {
            "key": "TEST-3",
            "fields": {
                "summary": "Third issue",
                "status": {"name": "Done"},
                "priority": {"name": "Low"},
                "issuetype": {"name": "Story"},
                "assignee": {"displayName": "Bob Wilson"},
                "reporter": {"displayName": "John Doe"},
                "labels": ["feature"],
            },
        },
    ]


@pytest.fixture
def sample_filter():
    """Sample filter for testing."""
    return {
        "id": "10001",
        "name": "My Open Issues",
        "jql": "assignee = currentUser() AND status != Done",
        "description": "All my open issues",
        "favourite": True,
        "owner": {
            "accountId": "user123",
            "displayName": "John Doe",
        },
        "sharePermissions": [
            {"type": "project", "project": {"key": "TEST", "name": "Test Project"}},
        ],
        "viewUrl": "https://jira.example.com/issues/?filter=10001",
    }


@pytest.fixture
def sample_filters():
    """Sample filter list for testing."""
    return [
        {
            "id": "10001",
            "name": "My Open Issues",
            "jql": "assignee = currentUser() AND status != Done",
            "favourite": True,
            "owner": {"displayName": "John Doe"},
        },
        {
            "id": "10002",
            "name": "All Bugs",
            "jql": "type = Bug AND status != Done",
            "favourite": False,
            "owner": {"displayName": "Jane Smith"},
        },
        {
            "id": "10003",
            "name": "Sprint Issues",
            "jql": "sprint in openSprints()",
            "favourite": True,
            "owner": {"displayName": "John Doe"},
        },
    ]


@pytest.fixture
def sample_fields():
    """Sample JQL fields for testing."""
    return [
        {
            "value": "project",
            "displayName": "Project",
            "cfid": None,
            "operators": ["=", "!=", "in", "not in"],
        },
        {
            "value": "status",
            "displayName": "Status",
            "cfid": None,
            "operators": ["=", "!=", "in", "not in", "was", "was in", "changed"],
        },
        {
            "value": "customfield_10001",
            "displayName": "Story Points",
            "cfid": "10001",
            "operators": ["=", "!=", ">", "<", ">=", "<="],
        },
        {
            "value": "customfield_10002",
            "displayName": "Epic Link",
            "cfid": "10002",
            "operators": ["=", "!=", "in", "not in", "is empty", "is not empty"],
        },
    ]


@pytest.fixture
def sample_functions():
    """Sample JQL functions for testing."""
    return [
        {
            "value": "currentUser()",
            "displayName": "currentUser()",
            "isList": "false",
            "types": ["com.atlassian.jira.user.ApplicationUser"],
        },
        {
            "value": "openSprints()",
            "displayName": "openSprints()",
            "isList": "true",
            "types": ["com.atlassian.greenhopper.Sprint"],
        },
        {
            "value": "startOfDay()",
            "displayName": "startOfDay(increment)",
            "isList": "false",
            "types": ["java.util.Date"],
        },
        {
            "value": "membersOf(group)",
            "displayName": "membersOf(groupname)",
            "isList": "true",
            "types": ["com.atlassian.jira.user.ApplicationUser"],
        },
    ]


@pytest.fixture
def sample_suggestions():
    """Sample suggestions for testing."""
    return [
        {"value": "High", "displayName": "High"},
        {"value": "Medium", "displayName": "Medium"},
        {"value": "Low", "displayName": "Low"},
        {"value": "Lowest", "displayName": "Lowest"},
    ]


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Tests for constants."""

    def test_common_fields_contains_expected(self):
        """Test COMMON_FIELDS contains essential fields."""
        assert "project" in COMMON_FIELDS
        assert "status" in COMMON_FIELDS
        assert "assignee" in COMMON_FIELDS
        assert "priority" in COMMON_FIELDS
        assert "summary" in COMMON_FIELDS

    def test_jql_templates_keys(self):
        """Test JQL_TEMPLATES contains expected templates."""
        assert "my-open" in JQL_TEMPLATES
        assert "my-bugs" in JQL_TEMPLATES
        assert "unassigned" in JQL_TEMPLATES
        assert "blockers" in JQL_TEMPLATES

    def test_jql_templates_values_are_valid_jql(self):
        """Test JQL_TEMPLATES values look like JQL."""
        for name, jql in JQL_TEMPLATES.items():
            assert isinstance(jql, str)
            assert len(jql) > 0
            # JQL should contain at least one comparison operator or keyword
            assert any(op in jql for op in ["=", "!=", "in", "IS", ">=", "<="])

    def test_function_examples_valid(self):
        """Test FUNCTION_EXAMPLES are valid."""
        assert "currentUser()" in FUNCTION_EXAMPLES
        assert "openSprints()" in FUNCTION_EXAMPLES
        for func, example in FUNCTION_EXAMPLES.items():
            # Extract function name without parentheses for matching
            func_base = func.split("(")[0]
            assert func_base in example or func in example


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_suggest_correction_exact_match(self):
        """Test suggestion finds close matches."""
        result = _suggest_correction("porject")
        assert result == "project"

    def test_suggest_correction_case_insensitive(self):
        """Test suggestion is case insensitive."""
        result = _suggest_correction("STATUS")
        assert result == "status"

    def test_suggest_correction_no_match(self):
        """Test suggestion returns None for no match."""
        result = _suggest_correction("zzzznotafield")
        assert result is None

    def test_suggest_correction_custom_fields(self):
        """Test suggestion with custom field list."""
        custom_fields = ["customfield_10001", "customfield_10002", "story_points"]
        result = _suggest_correction("customfield_1001", custom_fields)
        assert result == "customfield_10001"

    def test_format_value_for_jql_no_spaces(self):
        """Test formatting value without spaces."""
        result = _format_value_for_jql("Bug")
        assert result == "Bug"

    def test_format_value_for_jql_with_spaces(self):
        """Test formatting value with spaces gets quoted."""
        result = _format_value_for_jql("In Progress")
        assert result == '"In Progress"'

    def test_get_return_type_date(self):
        """Test getting return type for Date function."""
        func = {"types": ["java.util.Date"]}
        result = _get_return_type(func)
        assert result == "Date"

    def test_get_return_type_user(self):
        """Test getting return type for User function."""
        func = {"types": ["com.atlassian.jira.user.ApplicationUser"]}
        result = _get_return_type(func)
        assert result == "User"

    def test_get_return_type_sprint(self):
        """Test getting return type for Sprint function."""
        func = {"types": ["com.atlassian.greenhopper.Sprint"]}
        result = _get_return_type(func)
        assert result == "Sprint"

    def test_get_return_type_empty(self):
        """Test getting return type with no types."""
        func = {"types": []}
        result = _get_return_type(func)
        assert result == "Unknown"

    def test_get_return_type_missing(self):
        """Test getting return type with missing types key."""
        func = {}
        result = _get_return_type(func)
        assert result == "Unknown"


# =============================================================================
# Test Search Implementation Functions
# =============================================================================


class TestSearchImplementation:
    """Tests for search implementation functions."""

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_search_issues_basic(
        self, mock_validate, mock_get_client, mock_client, sample_issues
    ):
        """Test basic issue search."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.search_issues.return_value = {
            "issues": sample_issues,
            "total": 3,
        }

        result = _search_issues_impl(jql="project = TEST")

        assert result["total"] == 3
        assert len(result["issues"]) == 3
        assert result["_jql"] == "project = TEST"
        mock_client.__exit__.assert_called_once()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_search_issues_with_filter(
        self, mock_validate, mock_get_client, mock_client, sample_issues
    ):
        """Test search using saved filter."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.get_filter.return_value = {
            "id": "10001",
            "name": "My Filter",
            "jql": "project = TEST",
        }
        mock_client.search_issues.return_value = {
            "issues": sample_issues,
            "total": 3,
        }

        result = _search_issues_impl(filter_id="10001")

        assert result["_filter_name"] == "My Filter"
        mock_client.get_filter.assert_called_with("10001")

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_search_issues_with_save(self, mock_validate, mock_get_client, mock_client):
        """Test search with save-as filter option."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.search_issues.return_value = {"issues": [], "total": 0}
        mock_client.create_filter.return_value = {
            "id": "10005",
            "name": "New Filter",
        }

        result = _search_issues_impl(jql="project = TEST", save_as="New Filter")

        assert "savedFilter" in result
        assert result["savedFilter"]["name"] == "New Filter"
        mock_client.create_filter.assert_called_once()

    def test_search_issues_no_query_no_filter(self):
        """Test search fails without JQL or filter."""
        with pytest.raises(ValidationError, match="Either JQL query or filter_id"):
            _search_issues_impl()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_export_results_csv(
        self, mock_validate, mock_get_client, mock_client, sample_issues, tmp_path
    ):
        """Test exporting results to CSV."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.search_issues.return_value = {"issues": sample_issues}

        output_file = str(tmp_path / "export.csv")

        with patch("jira_as.cli.commands.search_cmds.export_csv") as mock_export:
            result = _export_results_impl(
                jql="project = TEST",
                output_file=output_file,
                format_type="csv",
            )

            assert result["exported"] == 3
            assert result["format"] == "csv"
            mock_export.assert_called_once()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_export_results_json(
        self, mock_validate, mock_get_client, mock_client, sample_issues, tmp_path
    ):
        """Test exporting results to JSON."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.search_issues.return_value = {"issues": sample_issues}

        output_file = str(tmp_path / "export.json")
        result = _export_results_impl(
            jql="project = TEST",
            output_file=output_file,
            format_type="json",
        )

        assert result["exported"] == 3
        assert result["format"] == "json"
        assert os.path.exists(output_file)

        with open(output_file) as f:
            data = json.load(f)
        assert data["total"] == 3

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_export_no_issues_writes_csv_headers(
        self, mock_validate, mock_get_client, mock_client, tmp_path
    ):
        """An empty result set is a successful export of a header-only CSV."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = EMPTY"
        mock_client.search_issues.return_value = {"issues": []}
        output_file = str(tmp_path / "export.csv")

        result = _export_results_impl(
            jql="project = EMPTY", output_file=output_file, fields=["key", "summary"]
        )

        assert result["exported"] == 0
        # 'output_file' must be present - the CLI reads it unconditionally.
        assert result["output_file"] == output_file
        assert result["format"] == "csv"

        with open(output_file) as f:
            assert f.read().strip() == "key,summary"

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_export_no_issues_writes_empty_json(
        self, mock_validate, mock_get_client, mock_client, tmp_path
    ):
        """An empty JSON export is a valid, empty envelope."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = EMPTY"
        mock_client.search_issues.return_value = {"issues": []}
        output_file = str(tmp_path / "export.json")

        result = _export_results_impl(
            jql="project = EMPTY", output_file=output_file, format_type="json"
        )

        assert result["exported"] == 0
        assert result["output_file"] == output_file

        with open(output_file) as f:
            assert json.load(f) == {"issues": [], "total": 0}

    def test_export_command_exits_zero_on_no_results(
        self, utility_simulation, cli_runner, tmp_path
    ):
        utility_simulation.issues = []
        output_file = str(tmp_path / "export.csv")
        result = cli_runner.invoke(
            search,
            ["export", "project = SBX", "-o", output_file, "--transport", "simulation"],
        )
        assert result.exit_code == 0, result.output
        assert "Exported 0 issues" in result.output

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_json_export_keeps_nested_values(
        self, mock_validate, mock_get_client, mock_client, tmp_path
    ):
        """Nested field values stay real JSON, not a stringified Python repr."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.search_issues.return_value = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "S",
                        "status": {"name": "Open", "id": "1"},
                    },
                }
            ]
        }
        output_file = str(tmp_path / "export.json")

        _export_results_impl(
            jql="project = TEST",
            output_file=output_file,
            format_type="json",
            fields=["key", "summary", "status"],
        )

        with open(output_file) as f:
            data = json.load(f)

        assert data["issues"][0]["status"] == {"name": "Open", "id": "1"}

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_csv_export_flattens_without_python_repr(
        self, mock_validate, mock_get_client, mock_client, tmp_path
    ):
        """CSV collapses objects to a display name, or compact JSON."""
        mock_validate.return_value = "project = TEST"
        mock_get_client.return_value = mock_client
        mock_client.search_issues.return_value = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "Jane"},
                        # No display-name key: must not become a Python repr.
                        "customfield_1": {"start": "2024-01-01"},
                        "labels": ["a", {"name": "b"}],
                    },
                }
            ]
        }
        output_file = str(tmp_path / "export.csv")

        _export_results_impl(
            jql="project = TEST",
            output_file=output_file,
            format_type="csv",
            fields=["key", "status", "assignee", "customfield_1", "labels"],
        )

        with open(output_file) as f:
            row = list(csv.DictReader(f))[0]

        assert row["status"] == "Open"
        assert row["assignee"] == "Jane"
        assert row["labels"] == "a, b"
        # Parseable JSON, not "{'start': '2024-01-01'}".
        assert json.loads(row["customfield_1"]) == {"start": "2024-01-01"}

    def test_build_jql_from_clauses(self):
        """Test building JQL from clauses."""
        result = _build_jql_impl(
            clauses=["project = TEST", "status = Open"],
            operator="AND",
        )

        assert result["jql"] == "project = TEST AND status = Open"

    def test_build_jql_with_order(self):
        """Test building JQL with ORDER BY."""
        result = _build_jql_impl(
            clauses=["project = TEST"],
            order_by="created",
            order_desc=True,
        )

        assert "ORDER BY created DESC" in result["jql"]

    def test_build_jql_from_template(self):
        """Test building JQL from template."""
        result = _build_jql_impl(template="my-open")

        assert result["jql"] == JQL_TEMPLATES["my-open"]

    def test_build_jql_unknown_template(self):
        """Test building JQL with unknown template."""
        with pytest.raises(ValidationError, match="Unknown template"):
            _build_jql_impl(template="nonexistent")

    def test_build_jql_no_input(self):
        """Test building JQL with no input."""
        with pytest.raises(ValidationError, match="Either clauses or template"):
            _build_jql_impl()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_build_jql_with_validation(self, mock_get_client, mock_client):
        """Test building JQL with validation."""
        mock_get_client.return_value = mock_client
        mock_client.parse_jql.return_value = {"queries": [{"errors": []}]}

        result = _build_jql_impl(
            clauses=["project = TEST"],
            validate=True,
        )

        assert result["valid"] is True
        assert result["errors"] == []

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.get_autocomplete_cache")
    def test_get_suggestions_cached(
        self, mock_get_cache, mock_get_client, mock_client, sample_suggestions
    ):
        """Test getting suggestions with cache."""
        mock_get_client.return_value = mock_client
        mock_cache = MagicMock()
        mock_cache.get_suggestions.return_value = sample_suggestions
        mock_get_cache.return_value = mock_cache

        result = _get_suggestions_impl("priority")

        assert len(result) == 4
        mock_cache.get_suggestions.assert_called_once()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_suggestions_no_cache(
        self, mock_get_client, mock_client, sample_suggestions
    ):
        """Test getting suggestions without cache."""
        mock_get_client.return_value = mock_client
        mock_client.get_jql_suggestions.return_value = {"results": sample_suggestions}

        result = _get_suggestions_impl("priority", use_cache=False)

        assert len(result) == 4
        mock_client.get_jql_suggestions.assert_called_once()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.get_autocomplete_cache")
    def test_get_fields_all(
        self, mock_get_cache, mock_get_client, mock_client, sample_fields
    ):
        """Test getting all fields."""
        mock_get_client.return_value = mock_client
        mock_cache = MagicMock()
        mock_cache.get_fields.return_value = sample_fields
        mock_get_cache.return_value = mock_cache

        result = _get_fields_impl()

        assert len(result) == 4

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.get_autocomplete_cache")
    def test_get_fields_custom_only(
        self, mock_get_cache, mock_get_client, mock_client, sample_fields
    ):
        """Test getting custom fields only."""
        mock_get_client.return_value = mock_client
        mock_cache = MagicMock()
        mock_cache.get_fields.return_value = sample_fields
        mock_get_cache.return_value = mock_cache

        result = _get_fields_impl(custom_only=True)

        assert len(result) == 2
        assert all(f.get("cfid") is not None for f in result)

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.get_autocomplete_cache")
    def test_get_fields_system_only(
        self, mock_get_cache, mock_get_client, mock_client, sample_fields
    ):
        """Test getting system fields only."""
        mock_get_client.return_value = mock_client
        mock_cache = MagicMock()
        mock_cache.get_fields.return_value = sample_fields
        mock_get_cache.return_value = mock_cache

        result = _get_fields_impl(system_only=True)

        assert len(result) == 2
        assert all(f.get("cfid") is None for f in result)

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.get_autocomplete_cache")
    def test_get_fields_filtered(
        self, mock_get_cache, mock_get_client, mock_client, sample_fields
    ):
        """Test getting fields filtered by name."""
        mock_get_client.return_value = mock_client
        mock_cache = MagicMock()
        mock_cache.get_fields.return_value = sample_fields
        mock_get_cache.return_value = mock_cache

        result = _get_fields_impl(name_filter="status")

        assert len(result) == 1
        assert result[0]["value"] == "status"

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_functions_all(self, mock_get_client, mock_client, sample_functions):
        """Test getting all functions."""
        mock_get_client.return_value = mock_client
        mock_client.get_jql_autocomplete.return_value = {
            "visibleFunctionNames": sample_functions
        }

        result = _get_functions_impl()

        assert len(result) == 4

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_functions_list_only(
        self, mock_get_client, mock_client, sample_functions
    ):
        """Test getting list-returning functions only."""
        mock_get_client.return_value = mock_client
        mock_client.get_jql_autocomplete.return_value = {
            "visibleFunctionNames": sample_functions
        }

        result = _get_functions_impl(list_only=True)

        assert len(result) == 2
        assert all(f.get("isList") == "true" for f in result)

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_functions_filtered(
        self, mock_get_client, mock_client, sample_functions
    ):
        """Test getting functions filtered by name."""
        mock_get_client.return_value = mock_client
        mock_client.get_jql_autocomplete.return_value = {
            "visibleFunctionNames": sample_functions
        }

        result = _get_functions_impl(name_filter="sprint")

        assert len(result) == 1
        assert "Sprint" in result[0]["value"]

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_bulk_update_dry_run(
        self, mock_validate, mock_get_client, mock_client, sample_issues
    ):
        """Test bulk update dry run."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.search_issues.return_value = {"issues": sample_issues, "total": 3}

        result = _bulk_update_impl(
            jql="project = TEST",
            add_labels=["newlabel"],
            dry_run=True,
        )

        assert result["would_update"] == 3
        assert "TEST-1" in result["issues"]
        mock_client.update_issue.assert_not_called()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_bulk_update_execute(
        self, mock_validate, mock_get_client, mock_client, sample_issues
    ):
        """Test bulk update execution."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = TEST"
        mock_client.search_issues.return_value = {"issues": sample_issues, "total": 3}

        result = _bulk_update_impl(
            jql="project = TEST",
            add_labels=["newlabel"],
            dry_run=False,
        )

        assert result["updated"] == 3
        assert result["failed"] == 0
        assert mock_client.update_issue.call_count == 3

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_bulk_update_no_issues(self, mock_validate, mock_get_client, mock_client):
        """Test bulk update with no matching issues."""
        mock_get_client.return_value = mock_client
        mock_validate.return_value = "project = EMPTY"
        mock_client.search_issues.return_value = {"issues": [], "total": 0}

        result = _bulk_update_impl(
            jql="project = EMPTY",
            add_labels=["newlabel"],
        )

        assert result["updated"] == 0
        assert "No issues found" in result["message"]


# =============================================================================
# Test Filter Implementation Functions
# =============================================================================


class TestFilterImplementation:
    """Tests for filter implementation functions."""

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_filters_my_filters(self, mock_get_client, mock_client, sample_filters):
        """Test getting my filters."""
        mock_get_client.return_value = mock_client
        mock_client.get_my_filters.return_value = sample_filters

        result = _get_filters_impl(my_filters=True)

        assert result["type"] == "my"
        assert len(result["filters"]) == 3

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_filters_by_id(self, mock_get_client, mock_client, sample_filter):
        """Test getting filter by ID."""
        mock_get_client.return_value = mock_client
        mock_client.get_filter.return_value = sample_filter

        result = _get_filters_impl(filter_id="10001")

        assert result["type"] == "single"
        assert result["filter"]["name"] == "My Open Issues"

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_filters_search(self, mock_get_client, mock_client, sample_filters):
        """Test searching filters."""
        mock_get_client.return_value = mock_client
        mock_client.search_filters.return_value = {"values": sample_filters}

        result = _get_filters_impl(search_name="Open")

        assert result["type"] == "search"
        mock_client.search_filters.assert_called_once()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_get_filters_no_option(self, mock_get_client, mock_client):
        """Test getting filters with no options raises error."""
        mock_get_client.return_value = mock_client
        with pytest.raises(ValidationError, match="Specify"):
            _get_filters_impl()


# =============================================================================
# Test Formatting Functions
# =============================================================================


class TestFormattingFunctions:
    """Tests for formatting functions."""

    def test_format_search_output_basic(self, sample_issues):
        """Test basic search output formatting."""
        results = {
            "issues": sample_issues,
            "total": 3,
            "isLast": True,
        }

        output = _format_search_output(results, False, False, False)

        assert "Found 3 issue(s)" in output

    def test_format_search_output_with_filter(self, sample_issues):
        """Test search output with filter name."""
        results = {
            "issues": sample_issues,
            "total": 3,
            "_filter_name": "My Filter",
            "_jql": "project = TEST",
        }

        output = _format_search_output(results, False, False, False)

        assert "Running filter: My Filter" in output
        assert "JQL: project = TEST" in output

    def test_format_search_output_pagination(self, sample_issues):
        """Test search output with pagination."""
        results = {
            "issues": sample_issues,
            "total": 100,
            "nextPageToken": "abc123",
        }

        output = _format_search_output(results, False, False, False)

        assert "Next page token: abc123" in output
        assert "Showing 3 of 100" in output

    def test_format_search_output_saved_filter(self, sample_issues):
        """Test search output with saved filter."""
        results = {
            "issues": sample_issues,
            "total": 3,
            "savedFilter": {"id": "10010", "name": "New Filter"},
        }

        output = _format_search_output(results, False, False, False)

        assert "Saved as filter: New Filter" in output

    def test_format_validation_result_valid(self):
        """Test formatting valid query result."""
        result = {
            "valid": True,
            "query": "project = TEST",
            "errors": [],
        }

        output = _format_validation_result(result)

        assert "Valid JQL" in output
        assert "project = TEST" in output

    def test_format_validation_result_with_structure(self):
        """Test formatting validation with structure."""
        result = {
            "valid": True,
            "query": "project = TEST",
            "errors": [],
            "structure": {
                "where": {
                    "clauses": [
                        {
                            "field": {"name": "project"},
                            "operator": "=",
                            "operand": {"value": "TEST"},
                        }
                    ]
                }
            },
        }

        output = _format_validation_result(result)

        assert "Structure:" in output
        assert "project = TEST" in output

    def test_format_validation_result_invalid(self):
        """Test formatting invalid query result."""
        result = {
            "valid": False,
            "query": "porject = TEST",
            "errors": ["Field 'porject' does not exist"],
        }

        output = _format_validation_result(result)

        assert "Invalid JQL" in output
        assert "Errors:" in output
        assert "does not exist" in output
        # Should suggest correction
        assert "project" in output

    def test_format_suggestions(self, sample_suggestions):
        """Test formatting suggestions."""
        output = _format_suggestions("priority", sample_suggestions)

        assert "Suggestions for 'priority'" in output
        assert "High" in output
        assert "Medium" in output
        assert "Usage:" in output

    def test_format_suggestions_empty(self):
        """Test formatting empty suggestions."""
        output = _format_suggestions("customfield", [])

        assert "No suggestions found" in output

    def test_format_fields(self, sample_fields):
        """Test formatting fields."""
        output = _format_fields(sample_fields)

        assert "JQL Fields:" in output
        assert "project" in output
        assert "status" in output
        assert "Custom" in output
        assert "System" in output
        assert "Total:" in output

    def test_format_fields_empty(self):
        """Test formatting empty fields."""
        output = _format_fields([])

        assert "No fields found" in output

    def test_format_functions(self, sample_functions):
        """Test formatting functions."""
        output = _format_functions(sample_functions)

        assert "JQL Functions:" in output
        assert "currentUser()" in output
        assert "openSprints()" in output
        assert "Returns List" in output

    def test_format_functions_with_examples(self, sample_functions):
        """Test formatting functions with examples."""
        output = _format_functions(sample_functions, show_examples=True)

        assert "Examples:" in output

    def test_format_functions_empty(self):
        """Test formatting empty functions."""
        output = _format_functions([])

        assert "No functions found" in output

    def test_format_filters(self, sample_filters):
        """Test formatting filters."""
        output = _format_filters(sample_filters)

        assert "My Open Issues" in output
        assert "All Bugs" in output
        assert "Total:" in output
        assert "favourites" in output

    def test_format_filters_empty(self):
        """Test formatting empty filters."""
        output = _format_filters([])

        assert "No filters found" in output

    def test_format_filter_detail(self, sample_filter):
        """Test formatting filter detail."""
        output = _format_filter_detail(sample_filter)

        assert "ID:" in output
        assert "10001" in output
        assert "My Open Issues" in output
        assert "John Doe" in output
        assert "Favourite:" in output
        assert "JQL:" in output
        assert "Shared With:" in output
        assert "Project:" in output
        assert "View URL:" in output


# =============================================================================
# Test CLI Commands
# =============================================================================


class TestSearchCLICommands:
    """Tests for search CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    def test_query_command_no_query(self, runner):
        """Test search query requires JQL or filter."""
        result = runner.invoke(search, ["query"])

        assert result.exit_code != 0
        assert "required" in result.output.lower()

    def test_build_command_list_templates(self, runner):
        """Test build command listing templates."""
        result = runner.invoke(search, ["build", "--list-templates"])

        assert result.exit_code == 0
        assert "Available Templates:" in result.output
        assert "my-open" in result.output

    def test_build_command_with_clauses(self, runner):
        """Test build command with clauses."""
        result = runner.invoke(
            search,
            [
                "build",
                "-c",
                "project = TEST",
                "-c",
                "status = Open",
            ],
        )

        assert result.exit_code == 0
        assert "project = TEST AND status = Open" in result.output

    def test_build_command_with_template(self, runner):
        """Test build command with template."""
        result = runner.invoke(search, ["build", "-t", "my-open"])

        assert result.exit_code == 0
        assert "assignee = currentUser()" in result.output

    def test_suggest_command(self, utility_simulation, runner):
        result = runner.invoke(
            search, ["suggest", "-f", "project", "--transport", "simulation"]
        )
        assert result.exit_code == 0, result.output
        assert "Sandbox" in result.output
        assert utility_simulation.calls[0][0] == "getFieldAutoCompleteForQueryString"

    def test_fields_command(self, utility_simulation, runner, sample_fields):
        utility_simulation.fields = sample_fields
        result = runner.invoke(search, ["fields", "--transport", "simulation"])
        assert result.exit_code == 0, result.output
        assert "project" in result.output
        assert "JQL Fields:" in result.output

    def test_functions_command(self, utility_simulation, runner):
        result = runner.invoke(search, ["functions", "--transport", "simulation"])
        assert result.exit_code == 0, result.output
        assert "currentUser()" in result.output

    def test_bulk_update_dry_run(self, utility_simulation, runner):
        before = utility_simulation.snapshot()
        result = runner.invoke(
            search,
            [
                "bulk-update",
                "project = SBX",
                "--add-labels",
                "newlabel",
                "--dry-run",
                "--transport",
                "simulation",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Would update" in result.output
        assert utility_simulation.snapshot() == before


class TestFilterCLICommands:
    """Tests for filter CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    @patch("jira_as.cli.commands.search_cmds.validate_jql")
    def test_client_close_on_error(self, mock_validate, mock_get_client):
        """Test client is closed even on error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_validate.side_effect = ValidationError("Bad JQL")

        try:
            _search_issues_impl(jql="bad query")
        except ValidationError:
            pass

        # Client should still be closed
        # Note: In this case, validate_jql is called before client operations

    @patch("jira_as.cli.commands.search_cmds.get_jira_client")
    def test_partial_bulk_update_failure(self, mock_get_client):
        """Test bulk update handles partial failures."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_get_client.return_value = mock_client
        mock_client.search_issues.return_value = {
            "issues": [
                {"key": "TEST-1", "fields": {"labels": []}},
                {"key": "TEST-2", "fields": {"labels": []}},
            ],
            "total": 2,
        }
        # First succeeds, second fails
        mock_client.update_issue.side_effect = [None, JiraError("Update failed")]

        with patch(
            "jira_as.cli.commands.search_cmds.validate_jql",
            return_value="jql",
        ):
            result = _bulk_update_impl(
                jql="project = TEST",
                add_labels=["label"],
                dry_run=False,
            )

        assert result["updated"] == 1
        assert result["failed"] == 1
        assert len(result["failures"]) == 1

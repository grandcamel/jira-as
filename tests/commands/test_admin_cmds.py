"""
Tests for jira-as admin commands.

Tests cover:
- Helper functions
- Implementation functions for all admin operations
- Formatting functions
- CLI commands
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from jira_as import JiraError, ValidationError
from jira_as.cli.commands.admin_cmds import (
    SYSTEM_GROUPS,  # Formatting functions; Automation implementation functions; Group implementation functions; Notification scheme implementation functions; Permission scheme implementation functions; Screen implementation functions; Helper functions; Click commands
    _format_categories,
    _format_groups,
    _format_issue_types,
    _format_permission_schemes,
    _format_screens,
    _format_statuses,
    _format_users,
    _format_workflows,
    _is_system_group,
    _parse_comma_list,
    admin,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Create mock JIRA client with context manager support."""
    client = MagicMock()
    client.close = MagicMock()
    # Support context manager pattern: with get_jira_client() as client:
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=None)
    return client


@pytest.fixture
def sample_projects():
    """Sample projects for testing."""
    return {
        "values": [
            {
                "id": "10001",
                "key": "PROJ1",
                "name": "Project One",
                "projectTypeKey": "software",
                "lead": {"displayName": "John Doe"},
            },
            {
                "id": "10002",
                "key": "PROJ2",
                "name": "Project Two",
                "projectTypeKey": "business",
                "lead": {"displayName": "Jane Smith"},
            },
        ],
        "isLast": True,
        "total": 2,
    }


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    return {
        "id": "10001",
        "key": "TEST",
        "name": "Test Project",
        "projectTypeKey": "software",
        "lead": {"displayName": "John Doe", "accountId": "user123"},
        "description": "A test project",
        "url": "https://jira.example.com/projects/TEST",
    }


@pytest.fixture
def sample_users():
    """Sample users for testing."""
    return [
        {
            "accountId": "user123",
            "displayName": "John Doe",
            "emailAddress": "john@example.com",
            "active": True,
        },
        {
            "accountId": "user456",
            "displayName": "Jane Smith",
            "emailAddress": "jane@example.com",
            "active": True,
        },
        {
            "accountId": "user789",
            "displayName": "Inactive User",
            "emailAddress": "inactive@example.com",
            "active": False,
        },
    ]


@pytest.fixture
def sample_groups():
    """Sample groups for testing."""
    return [
        {"name": "jira-administrators", "groupId": "group1"},
        {"name": "developers", "groupId": "group2"},
        {"name": "jira-users", "groupId": "group3"},
        {"name": "qa-team", "groupId": "group4"},
    ]


@pytest.fixture
def sample_permission_schemes():
    """Sample permission schemes for testing."""
    return [
        {
            "id": "10000",
            "name": "Default Permission Scheme",
            "description": "Default permissions",
        },
        {
            "id": "10001",
            "name": "Restricted Scheme",
            "description": "Restricted access",
        },
    ]


@pytest.fixture
def sample_screens():
    """Sample screens for testing."""
    return [
        {
            "id": "1",
            "name": "Default Screen",
            "description": "Default issue screen",
        },
        {
            "id": "2",
            "name": "Bug Screen",
            "description": "Screen for bugs",
        },
    ]


@pytest.fixture
def sample_issue_types():
    """Sample issue types for testing."""
    return [
        {
            "id": "10001",
            "name": "Bug",
            "description": "A bug",
            "subtask": False,
            "scope": {"type": "PROJECT"},
        },
        {
            "id": "10002",
            "name": "Task",
            "description": "A task",
            "subtask": False,
            "scope": {"type": "PROJECT"},
        },
        {
            "id": "10003",
            "name": "Sub-task",
            "description": "A sub-task",
            "subtask": True,
            "scope": {"type": "PROJECT"},
        },
    ]


@pytest.fixture
def sample_workflows():
    """Sample workflows for testing."""
    return [
        {
            "name": "Default Workflow",
            "description": "The default workflow",
            "scope": {"type": "GLOBAL"},
            "statuses": [
                {"id": "1", "name": "Open"},
                {"id": "2", "name": "In Progress"},
                {"id": "3", "name": "Done"},
            ],
        },
        {
            "name": "Bug Workflow",
            "description": "Workflow for bugs",
            "scope": {"type": "PROJECT"},
            "statuses": [
                {"id": "1", "name": "Open"},
                {"id": "4", "name": "Investigating"},
                {"id": "3", "name": "Done"},
            ],
        },
    ]


@pytest.fixture
def sample_statuses():
    """Sample statuses for testing."""
    return [
        {"id": "1", "name": "Open", "statusCategory": {"name": "To Do"}},
        {"id": "2", "name": "In Progress", "statusCategory": {"name": "In Progress"}},
        {"id": "3", "name": "Done", "statusCategory": {"name": "Done"}},
    ]


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_parse_comma_list_basic(self):
        """Test parsing comma-separated values."""
        result = _parse_comma_list("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_comma_list_with_spaces(self):
        """Test parsing with spaces around values."""
        result = _parse_comma_list(" a , b , c ")
        assert result == ["a", "b", "c"]

    def test_parse_comma_list_empty(self):
        """Test parsing empty string returns None."""
        result = _parse_comma_list("")
        assert result is None

    def test_parse_comma_list_none(self):
        """Test parsing None returns None."""
        result = _parse_comma_list(None)
        assert result is None

    def test_parse_comma_list_single(self):
        """Test parsing single value."""
        result = _parse_comma_list("single")
        assert result == ["single"]

    def test_is_system_group_true(self):
        """Test system group detection - true cases."""
        assert _is_system_group("jira-administrators") is True
        assert _is_system_group("jira-users") is True
        assert _is_system_group("site-admins") is True

    def test_is_system_group_false(self):
        """Test system group detection - false cases."""
        assert _is_system_group("developers") is False
        assert _is_system_group("qa-team") is False
        assert _is_system_group("my-custom-group") is False

    def test_system_groups_constant(self):
        """Test SYSTEM_GROUPS contains expected groups."""
        assert "jira-administrators" in SYSTEM_GROUPS
        assert "jira-users" in SYSTEM_GROUPS


# =============================================================================
# Test Project Implementation Functions
# =============================================================================


# =============================================================================
# Test Category Implementation Functions
# =============================================================================


# =============================================================================
# Test User Implementation Functions
# =============================================================================


# =============================================================================
# Test Group Implementation Functions
# =============================================================================


# =============================================================================
# Test Automation Implementation Functions
# =============================================================================


# =============================================================================
# Test Permission Scheme Implementation Functions
# =============================================================================


# =============================================================================
# Test Notification Scheme Implementation Functions
# =============================================================================


# =============================================================================
# Test Screen Implementation Functions
# =============================================================================


# =============================================================================
# Test Issue Type Implementation Functions
# =============================================================================


# =============================================================================
# Test Workflow Implementation Functions
# =============================================================================


# =============================================================================
# Test Formatting Functions
# =============================================================================


class TestFormattingFunctions:
    """Tests for formatting functions."""

    def test_format_categories(self):
        """Test formatting categories."""
        categories = [
            {"id": "1", "name": "Development", "description": "Dev projects"},
            {"id": "2", "name": "Support", "description": "Support projects"},
        ]
        result = _format_categories(categories)

        assert "Development" in result
        assert "Support" in result

    def test_format_users(self, sample_users):
        """Test formatting users."""
        result = _format_users(sample_users)

        assert "John Doe" in result
        assert "Jane Smith" in result

    def test_format_users_with_groups(self, sample_users):
        """Test formatting users with groups."""
        sample_users[0]["groups"] = ["developers", "qa-team"]
        result = _format_users(sample_users, show_groups=True)

        assert "developers" in result

    def test_format_groups(self, sample_groups):
        """Test formatting groups."""
        result = _format_groups(sample_groups)

        assert "developers" in result
        assert "jira-administrators" in result

    def test_format_groups_show_system(self, sample_groups):
        """Test formatting groups with system flag."""
        result = _format_groups(sample_groups, show_system=True)

        # System groups should be shown
        assert "jira-administrators" in result
        assert "jira-users" in result

    def test_format_permission_schemes(self, sample_permission_schemes):
        """Test formatting permission schemes."""
        result = _format_permission_schemes(sample_permission_schemes)

        assert "Default Permission Scheme" in result
        assert "Restricted Scheme" in result

    def test_format_screens(self, sample_screens):
        """Test formatting screens."""
        result = _format_screens(sample_screens)

        assert "Default Screen" in result
        assert "Bug Screen" in result

    def test_format_issue_types(self, sample_issue_types):
        """Test formatting issue types."""
        result = _format_issue_types(sample_issue_types)

        assert "Bug" in result
        assert "Task" in result
        assert "Sub-task" in result

    def test_format_workflows(self, sample_workflows):
        """Test formatting workflows."""
        result = _format_workflows(sample_workflows)

        assert "Default Workflow" in result
        assert "Bug Workflow" in result

    def test_format_statuses(self, sample_statuses):
        """Test formatting statuses."""
        result = _format_statuses(sample_statuses)

        assert "Open" in result
        assert "In Progress" in result
        assert "Done" in result


# =============================================================================
# Test CLI Commands - Project
# =============================================================================


# =============================================================================
# Test CLI Commands - User
# =============================================================================


# =============================================================================
# Test CLI Commands - Group
# =============================================================================


# =============================================================================
# Test CLI Commands - Automation
# =============================================================================


# =============================================================================
# Test CLI Commands - Issue Type
# =============================================================================


# =============================================================================
# Test CLI Commands - Workflow
# =============================================================================


# =============================================================================
# Test CLI Commands - Status
# =============================================================================


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in CLI commands."""

    @patch("jira_as.cli.commands.admin_cmds.get_client_from_context")
    def test_jira_error_handling(self, mock_get_client, mock_client, cli_runner):
        """Test JiraError handling in CLI."""
        mock_get_client.return_value = mock_client
        mock_client.search_projects.side_effect = JiraError("API error")

        result = cli_runner.invoke(admin, ["project", "list"])

        assert result.exit_code != 0

    @patch("jira_as.cli.commands.admin_cmds.get_client_from_context")
    def test_validation_error_handling(self, mock_get_client, mock_client, cli_runner):
        """Test ValidationError handling in CLI."""
        mock_get_client.return_value = mock_client
        mock_client.get_project.side_effect = ValidationError("Invalid project key")

        result = cli_runner.invoke(admin, ["project", "get", "INVALID"])

        assert result.exit_code != 0


# =============================================================================
# Test Repaired Admin Client Calls
# =============================================================================

"""
Tests for the testing utilities module.
"""

from unittest.mock import MagicMock

import pytest

from jira_as.testing import (
    IssueBuilder,
    assert_issue_has_field,
    assert_search_returns_empty,
    assert_search_returns_results,
    generate_unique_name,
    get_jira_version,
    is_cloud_instance,
    wait_for_assignment,
    wait_for_transition,
)


class TestIssueBuilder:
    """Tests for IssueBuilder fluent API."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock JIRA client."""
        client = MagicMock()
        client.post.return_value = {"id": "12345", "key": "TEST-1"}
        return client

    def test_basic_build(self, mock_client):
        """Test basic issue creation with defaults."""
        builder = IssueBuilder(mock_client, "TEST")
        issue = builder.with_summary("Test summary").build()

        assert issue["key"] == "TEST-1"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/rest/api/3/issue"
        fields = call_args[1]["json"]["fields"]
        assert fields["summary"] == "Test summary"
        assert fields["project"]["key"] == "TEST"
        assert fields["issuetype"]["name"] == "Task"

    def test_with_type(self, mock_client):
        """Test setting issue type."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("Bug test").with_type("Bug").build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        assert fields["issuetype"]["name"] == "Bug"

    def test_with_priority(self, mock_client):
        """Test setting priority."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("High priority").with_priority("High").build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        assert fields["priority"]["name"] == "High"

    def test_with_description(self, mock_client):
        """Test setting description with ADF format."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("With description").with_description(
            "Test description"
        ).build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        assert fields["description"]["type"] == "doc"
        assert fields["description"]["version"] == 1

    def test_with_labels(self, mock_client):
        """Test setting labels (replaces defaults)."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("Custom labels").with_labels(["custom", "labels"]).build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        assert fields["labels"] == ["custom", "labels"]

    def test_add_labels(self, mock_client):
        """Test adding labels to existing."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("Add labels").add_labels(["extra"]).build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        # Default labels are ["test", "automated"], plus "extra"
        assert "extra" in fields["labels"]
        assert "test" in fields["labels"]

    def test_with_assignee(self, mock_client):
        """Test setting assignee."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("Assigned").with_assignee("account123").build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        assert fields["assignee"]["accountId"] == "account123"

    def test_with_field(self, mock_client):
        """Test setting arbitrary field."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("Custom field").with_field(
            "customfield_10001", "value"
        ).build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        assert fields["customfield_10001"] == "value"

    def test_link_to(self, mock_client):
        """Test linking to another issue."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.with_summary("Linked").link_to("TEST-100", "Relates").build()

        # Should make 2 calls: create issue, create link
        assert mock_client.post.call_count == 2
        link_call = mock_client.post.call_args_list[1]
        assert link_call[0][0] == "/rest/api/3/issueLink"

    def test_auto_summary(self, mock_client):
        """Test auto-generated summary when not set."""
        builder = IssueBuilder(mock_client, "TEST")
        builder.build()

        call_args = mock_client.post.call_args
        fields = call_args[1]["json"]["fields"]
        assert "[Test]" in fields["summary"]
        assert "Task" in fields["summary"]


class TestAssertionHelpers:
    """Tests for assertion helper functions."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock JIRA client."""
        return MagicMock()

    def test_assert_search_returns_results_success(self, mock_client):
        """Test successful search assertion."""
        mock_client.post.return_value = {
            "issues": [{"key": "TEST-1"}, {"key": "TEST-2"}]
        }

        results = assert_search_returns_results(
            mock_client, "project = TEST", min_count=1, timeout=1
        )

        assert len(results) == 2
        assert results[0]["key"] == "TEST-1"

    def test_assert_search_returns_results_timeout(self, mock_client):
        """Test search assertion timeout."""
        mock_client.post.return_value = {"issues": []}

        with pytest.raises(AssertionError) as exc_info:
            assert_search_returns_results(
                mock_client, "project = TEST", min_count=1, timeout=1
            )

        assert "Expected at least 1 results" in str(exc_info.value)

    def test_assert_search_returns_empty_success(self, mock_client):
        """Test empty search assertion success."""
        mock_client.post.return_value = {"total": 0}

        # Should not raise
        assert_search_returns_empty(mock_client, "project = EMPTY", timeout=1)

    def test_assert_search_returns_empty_failure(self, mock_client):
        """Test empty search assertion failure."""
        mock_client.post.return_value = {"total": 5}

        with pytest.raises(AssertionError) as exc_info:
            assert_search_returns_empty(mock_client, "project = TEST", timeout=1)

        assert "Expected no results" in str(exc_info.value)
        assert "got 5" in str(exc_info.value)

    def test_assert_issue_has_field_present(self):
        """Test field presence assertion."""
        issue = {"key": "TEST-1", "fields": {"summary": "Test"}}

        # Should not raise
        assert_issue_has_field(issue, "summary")

    def test_assert_issue_has_field_missing(self):
        """Test missing field assertion."""
        issue = {"key": "TEST-1", "fields": {"summary": "Test"}}

        with pytest.raises(AssertionError) as exc_info:
            assert_issue_has_field(issue, "description")

        assert "missing field 'description'" in str(exc_info.value)

    def test_assert_issue_has_field_value_match(self):
        """Test field value assertion."""
        issue = {"key": "TEST-1", "fields": {"summary": "Test"}}

        # Should not raise
        assert_issue_has_field(issue, "summary", "Test")

    def test_assert_issue_has_field_value_mismatch(self):
        """Test field value mismatch."""
        issue = {"key": "TEST-1", "fields": {"summary": "Test"}}

        with pytest.raises(AssertionError) as exc_info:
            assert_issue_has_field(issue, "summary", "Different")

        assert "expected 'Different'" in str(exc_info.value)
        assert "got 'Test'" in str(exc_info.value)

    def test_assert_issue_has_field_nested_value(self):
        """Test nested field value (e.g., status.name)."""
        issue = {"key": "TEST-1", "fields": {"status": {"name": "Open", "id": "1"}}}

        # Should not raise - extracts name from dict
        assert_issue_has_field(issue, "status", "Open")


class TestVersionDetection:
    """Tests for version detection utilities."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock JIRA client."""
        return MagicMock()

    def test_get_jira_version(self, mock_client):
        """Test version parsing."""
        mock_client.get.return_value = {"version": "9.4.5"}

        version = get_jira_version(mock_client)

        assert version == (9, 4, 5)

    def test_get_jira_version_with_suffix(self, mock_client):
        """Test version parsing with build suffix."""
        mock_client.get.return_value = {"version": "9.4.5-SNAPSHOT"}

        version = get_jira_version(mock_client)

        assert version == (9, 4, 5)

    def test_get_jira_version_fallback(self, mock_client):
        """Test fallback to v2 API."""
        mock_client.get.side_effect = [
            Exception("v3 not available"),
            {"version": "8.20.0"},
        ]

        version = get_jira_version(mock_client)

        assert version == (8, 20, 0)

    def test_is_cloud_instance_true(self, mock_client):
        """Test cloud instance detection."""
        mock_client.get.return_value = {"deploymentType": "Cloud"}

        assert is_cloud_instance(mock_client) is True

    def test_is_cloud_instance_false(self, mock_client):
        """Test server/DC instance detection."""
        mock_client.get.return_value = {"deploymentType": "Server"}

        assert is_cloud_instance(mock_client) is False

    def test_is_cloud_instance_error(self, mock_client):
        """Test cloud detection on error."""
        mock_client.get.side_effect = Exception("Network error")

        assert is_cloud_instance(mock_client) is False


class TestWaitUtilities:
    """Tests for wait/polling utilities."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock JIRA client."""
        return MagicMock()

    def test_wait_for_transition_success(self, mock_client):
        """Test successful transition wait."""
        mock_client.get.return_value = {"fields": {"status": {"name": "Done"}}}

        result = wait_for_transition(mock_client, "TEST-1", "Done", timeout=1)

        assert result is True

    def test_wait_for_transition_timeout(self, mock_client):
        """Test transition wait timeout."""
        mock_client.get.return_value = {"fields": {"status": {"name": "Open"}}}

        result = wait_for_transition(mock_client, "TEST-1", "Done", timeout=1)

        assert result is False

    def test_wait_for_assignment_success(self, mock_client):
        """Test successful assignment wait."""
        mock_client.get.return_value = {
            "fields": {"assignee": {"accountId": "user123"}}
        }

        result = wait_for_assignment(mock_client, "TEST-1", "user123", timeout=1)

        assert result is True

    def test_wait_for_assignment_unassigned(self, mock_client):
        """Test waiting for unassignment."""
        mock_client.get.return_value = {"fields": {"assignee": None}}

        result = wait_for_assignment(mock_client, "TEST-1", None, timeout=1)

        assert result is True


class TestGenerateUniqueName:
    """Tests for unique name generation."""

    def test_generate_unique_name_format(self):
        """Test unique name format."""
        name = generate_unique_name("test")

        assert name.startswith("test_")
        # Should have timestamp and suffix
        parts = name.split("_")
        assert len(parts) == 3  # prefix_timestamp_suffix

    def test_generate_unique_name_unique(self):
        """Test names are actually unique."""
        names = [generate_unique_name() for _ in range(10)]
        assert len(names) == len(set(names))

    def test_generate_unique_name_custom_prefix(self):
        """Test custom prefix."""
        name = generate_unique_name("custom")

        assert name.startswith("custom_")

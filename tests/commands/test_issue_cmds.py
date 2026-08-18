"""
Unit tests for issue CLI commands.

Tests cover:
- get_issue: Retrieving issue details, fields, links, time tracking
- create_issue: Creating issues with various options
- update_issue: Updating issue fields
- delete_issue: Deleting issues with/without confirmation
"""

import json
from copy import deepcopy
from unittest.mock import patch

import pytest

from jira_as.cli.commands.issue_cmds import (
    _create_issue_impl,
    _delete_issue_impl,
    _get_issue_impl,
    _update_issue_impl,
    issue,
)

# =============================================================================
# Tests for _get_issue_impl
# =============================================================================


@pytest.mark.unit
class TestGetIssueImpl:
    """Tests for the _get_issue_impl implementation function."""

    def test_get_issue_success(self, mock_jira_client, sample_issue):
        """Test retrieving an issue successfully."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_issue_impl(issue_key="PROJ-123")

        mock_jira_client.get_issue.assert_called_once_with("PROJ-123", fields=None)
        assert result["key"] == "PROJ-123"
        assert result["fields"]["summary"] == "Test Issue Summary"

    def test_get_issue_normalizes_key(self, mock_jira_client, sample_issue):
        """Test that issue key is normalized to uppercase."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_issue_impl(issue_key="proj-123")

        mock_jira_client.get_issue.assert_called_once_with("PROJ-123", fields=None)
        assert result["key"] == "PROJ-123"

    def test_get_issue_with_specific_fields(
        self, mock_jira_client, sample_issue_minimal
    ):
        """Test retrieving an issue with specific fields."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue_minimal)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_issue_impl(issue_key="PROJ-124", fields=["summary", "status"])

        mock_jira_client.get_issue.assert_called_once_with(
            "PROJ-124", fields=["summary", "status"]
        )
        assert result["key"] == "PROJ-124"

    def test_get_issue_with_links(self, mock_jira_client, sample_issue_with_links):
        """Test retrieving an issue with issue links."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue_with_links)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_issue_impl(issue_key="PROJ-126")

        assert "issuelinks" in result["fields"]
        assert len(result["fields"]["issuelinks"]) == 2

    def test_get_issue_with_time_tracking(
        self, mock_jira_client, sample_issue_with_time_tracking
    ):
        """Test retrieving an issue with time tracking information."""
        mock_jira_client.get_issue.return_value = deepcopy(
            sample_issue_with_time_tracking
        )

        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_issue_impl(issue_key="PROJ-125")

        tt = result["fields"]["timetracking"]
        assert tt["originalEstimate"] == "2d"
        assert tt["remainingEstimate"] == "1d 4h"
        assert tt["timeSpent"] == "4h"

    def test_get_issue_not_found(self, mock_jira_client):
        """Test handling issue not found error."""
        from jira_as import NotFoundError

        mock_jira_client.get_issue.side_effect = NotFoundError("Issue", "PROJ-999")

        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            pytest.raises(NotFoundError) as exc_info,
        ):
            _get_issue_impl(issue_key="PROJ-999")

        assert "not found" in str(exc_info.value).lower()

    def test_get_issue_uses_context_manager(self, mock_jira_client, sample_issue):
        """Test that client is used as context manager."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _get_issue_impl(issue_key="PROJ-123")

        mock_jira_client.__enter__.assert_called_once()
        mock_jira_client.__exit__.assert_called_once()


# =============================================================================
# Tests for _create_issue_impl
# =============================================================================


@pytest.mark.unit
class TestCreateIssueImpl:
    """Tests for the _create_issue_impl implementation function."""

    def test_create_issue_basic(self, mock_jira_client, sample_created_issue):
        """Test creating a basic issue."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.issue_cmds.has_project_context",
                return_value=False,
            ),
        ):
            result = _create_issue_impl(
                project="PROJ",
                issue_type="Bug",
                summary="Test bug",
            )

        assert result["key"] == "PROJ-130"
        mock_jira_client.create_issue.assert_called_once()

    def test_create_issue_with_description(
        self, mock_jira_client, sample_created_issue
    ):
        """Test creating an issue with description."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.issue_cmds.has_project_context",
                return_value=False,
            ),
        ):
            result = _create_issue_impl(
                project="PROJ",
                issue_type="Bug",
                summary="Test bug",
                description="This is a test description",
            )

        assert result["key"] == "PROJ-130"
        call_args = mock_jira_client.create_issue.call_args[0][0]
        assert "description" in call_args

    def test_create_issue_with_labels(self, mock_jira_client, sample_created_issue):
        """Test creating an issue with labels."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.issue_cmds.has_project_context",
                return_value=False,
            ),
        ):
            result = _create_issue_impl(
                project="PROJ",
                issue_type="Bug",
                summary="Test bug",
                labels=["urgent", "backend"],
            )

        assert result["key"] == "PROJ-130"
        call_args = mock_jira_client.create_issue.call_args[0][0]
        assert call_args["labels"] == ["urgent", "backend"]

    def test_create_issue_uses_context_manager(
        self, mock_jira_client, sample_created_issue
    ):
        """Test that client is used as context manager."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.issue_cmds.has_project_context",
                return_value=False,
            ),
        ):
            _create_issue_impl(
                project="PROJ",
                issue_type="Bug",
                summary="Test bug",
            )

        mock_jira_client.__enter__.assert_called()
        mock_jira_client.__exit__.assert_called()


# =============================================================================
# Tests for _update_issue_impl
# =============================================================================


@pytest.mark.unit
class TestUpdateIssueImpl:
    """Tests for the _update_issue_impl implementation function."""

    def test_update_issue_summary(self, mock_jira_client):
        """Test updating issue summary."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _update_issue_impl(issue_key="PROJ-123", summary="New summary")

        mock_jira_client.update_issue.assert_called_once()
        call_args = mock_jira_client.update_issue.call_args
        assert call_args[0][0] == "PROJ-123"
        assert call_args[0][1]["summary"] == "New summary"

    def test_update_issue_priority(self, mock_jira_client):
        """Test updating issue priority."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _update_issue_impl(issue_key="PROJ-123", priority="High")

        call_args = mock_jira_client.update_issue.call_args
        assert call_args[0][1]["priority"] == {"name": "High"}

    def test_update_issue_labels(self, mock_jira_client):
        """Test updating issue labels."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _update_issue_impl(issue_key="PROJ-123", labels=["bug", "urgent"])

        call_args = mock_jira_client.update_issue.call_args
        assert call_args[0][1]["labels"] == ["bug", "urgent"]

    def test_update_issue_no_fields_raises_error(self, mock_jira_client):
        """Test that updating with no fields raises ValueError."""
        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            pytest.raises(ValueError, match="No fields specified"),
        ):
            _update_issue_impl(issue_key="PROJ-123")

    def test_update_issue_uses_context_manager(self, mock_jira_client):
        """Test that client is used as context manager."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _update_issue_impl(issue_key="PROJ-123", summary="New summary")

        mock_jira_client.__enter__.assert_called_once()
        mock_jira_client.__exit__.assert_called_once()


# =============================================================================
# Tests for _delete_issue_impl
# =============================================================================


@pytest.mark.unit
class TestDeleteIssueImpl:
    """Tests for the _delete_issue_impl implementation function."""

    def test_delete_issue_force(self, mock_jira_client):
        """Test force deleting an issue."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _delete_issue_impl(issue_key="PROJ-123", force=True)

        mock_jira_client.delete_issue.assert_called_once_with("PROJ-123")
        assert result is None

    def test_delete_issue_no_force_returns_info(self, mock_jira_client, sample_issue):
        """Test deleting without force returns issue info for confirmation."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _delete_issue_impl(issue_key="PROJ-123", force=False)

        mock_jira_client.delete_issue.assert_not_called()
        assert result is not None
        assert result["key"] == "PROJ-123"
        assert result["summary"] == "Test Issue Summary"

    def test_delete_issue_uses_context_manager(self, mock_jira_client):
        """Test that client is used as context manager."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _delete_issue_impl(issue_key="PROJ-123", force=True)

        mock_jira_client.__enter__.assert_called_once()
        mock_jira_client.__exit__.assert_called_once()


# =============================================================================
# Tests for CLI Commands
# =============================================================================


@pytest.mark.unit
class TestGetIssueCommand:
    """Tests for the get_issue Click command."""

    def test_get_issue_cli_success(self, cli_runner, mock_jira_client, sample_issue):
        """Test CLI get issue command success."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(issue, ["get", "PROJ-123"])

        assert result.exit_code == 0
        assert "PROJ-123" in result.output

    def test_get_issue_cli_json_output(
        self, cli_runner, mock_jira_client, sample_issue
    ):
        """Test CLI get issue command with JSON output."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)

        with patch(
            "jira_as.cli.commands.issue_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(issue, ["get", "PROJ-123", "--output", "json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["key"] == "PROJ-123"


@pytest.mark.unit
class TestCreateIssueCommand:
    """Tests for the create_issue Click command."""

    def test_create_issue_cli_success(
        self, cli_runner, mock_jira_client, sample_created_issue
    ):
        """Test CLI create issue command success."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_client_from_context",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.issue_cmds.has_project_context",
                return_value=False,
            ),
        ):
            result = cli_runner.invoke(
                issue,
                [
                    "create",
                    "--project",
                    "PROJ",
                    "--type",
                    "Bug",
                    "--summary",
                    "Test bug",
                ],
            )

        assert result.exit_code == 0
        assert "PROJ-130" in result.output


@pytest.mark.unit
class TestUpdateIssueCommand:
    """Tests for the update_issue Click command."""

    def test_update_issue_cli_success(self, cli_runner, mock_jira_client):
        """Test CLI update issue command success."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                issue,
                ["update", "PROJ-123", "--summary", "Updated summary"],
            )

        assert result.exit_code == 0
        assert "Updated" in result.output


@pytest.mark.unit
class TestDeleteIssueCommand:
    """Tests for the delete_issue Click command."""

    def test_delete_issue_cli_force(self, cli_runner, mock_jira_client):
        """Test CLI delete issue command with force flag."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                issue,
                ["delete", "PROJ-123", "--force"],
            )

        assert result.exit_code == 0
        assert "Deleted" in result.output
        mock_jira_client.delete_issue.assert_called_once()


# =============================================================================
# Tests for parent handling, ADF auto-wrap, and dry run
# =============================================================================


@pytest.mark.unit
class TestCreateIssueParentAndAdf:
    """Tests for --parent, --parent-via-update, --dry-run and ADF wrapping."""

    @staticmethod
    def _no_context():
        return patch(
            "jira_as.cli.commands.issue_cmds.has_project_context", return_value=False
        )

    def test_parent_uses_modern_parent_field(
        self, mock_jira_client, sample_created_issue
    ):
        """A parent is set through the 'parent' field, not an epic custom field."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with self._no_context():
            _create_issue_impl(
                project="PROJ",
                issue_type="Task",
                summary="Child",
                parent="PROJ-100",
                client=mock_jira_client,
            )

        fields = mock_jira_client.create_issue.call_args[0][0]
        assert fields["parent"] == {"key": "PROJ-100"}
        # No epic-link custom field smuggling.
        assert not any(k.startswith("customfield_") for k in fields)

    def test_parent_via_update_defers_the_parent(
        self, mock_jira_client, sample_created_issue
    ):
        """--parent-via-update creates first, then sets the parent."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with self._no_context():
            result = _create_issue_impl(
                project="PROJ",
                issue_type="Task",
                summary="Child",
                parent="PROJ-100",
                parent_via_update=True,
                client=mock_jira_client,
            )

        create_fields = mock_jira_client.create_issue.call_args[0][0]
        assert "parent" not in create_fields
        mock_jira_client.update_issue.assert_called_once_with(
            "PROJ-130", {"parent": {"key": "PROJ-100"}}
        )
        assert result["parent_set_via_update"] == "PROJ-100"

    def test_dry_run_does_not_call_the_api(self, mock_jira_client):
        """--dry-run returns the payload and creates nothing."""
        with self._no_context():
            result = _create_issue_impl(
                project="PROJ",
                issue_type="Task",
                summary="Preview",
                parent="PROJ-100",
                dry_run=True,
                client=mock_jira_client,
            )

        mock_jira_client.create_issue.assert_not_called()
        assert result["dry_run"] is True
        assert result["fields"]["summary"] == "Preview"
        assert result["fields"]["parent"] == {"key": "PROJ-100"}

    def test_dry_run_reports_deferred_parent(self, mock_jira_client):
        """A dry run shows a parent that would be set in a second step."""
        with self._no_context():
            result = _create_issue_impl(
                project="PROJ",
                issue_type="Task",
                summary="Preview",
                parent="PROJ-100",
                parent_via_update=True,
                dry_run=True,
                client=mock_jira_client,
            )

        assert "parent" not in result["fields"]
        assert result["deferred_parent"] == {"key": "PROJ-100"}

    def test_custom_field_string_is_wrapped_in_adf(
        self, monkeypatch, mock_jira_client, sample_created_issue
    ):
        """A configured rich-text custom field gets an ADF document."""
        monkeypatch.setenv("JIRA_ADF_CUSTOM_FIELDS", "customfield_10050")
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with self._no_context():
            _create_issue_impl(
                project="PROJ",
                issue_type="Task",
                summary="Test",
                custom_fields={
                    "customfield_10050": "plain notes",
                    "customfield_10099": "left alone",
                },
                client=mock_jira_client,
            )

        fields = mock_jira_client.create_issue.call_args[0][0]
        assert fields["customfield_10050"]["type"] == "doc"
        # Fields that are not configured as rich text stay untouched.
        assert fields["customfield_10099"] == "left alone"

    def test_existing_adf_value_passes_through(
        self, monkeypatch, mock_jira_client, sample_created_issue
    ):
        """A value that is already ADF is not re-wrapped."""
        monkeypatch.setenv("JIRA_ADF_CUSTOM_FIELDS", "customfield_10050")
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)
        adf = {"version": 1, "type": "doc", "content": []}

        with self._no_context():
            _create_issue_impl(
                project="PROJ",
                issue_type="Task",
                summary="Test",
                custom_fields={"customfield_10050": adf},
                client=mock_jira_client,
            )

        fields = mock_jira_client.create_issue.call_args[0][0]
        assert fields["customfield_10050"] == adf

    def test_story_points_field_resolved_per_project(
        self, mock_jira_client, sample_created_issue
    ):
        """Story points resolve the field ID against the target project."""
        mock_jira_client.create_issue.return_value = deepcopy(sample_created_issue)

        with (
            self._no_context(),
            patch(
                "jira_as.cli.commands.issue_cmds.get_agile_fields",
                return_value={
                    "epic_link": "customfield_10014",
                    "story_points": "customfield_12345",
                },
            ) as mock_agile,
        ):
            _create_issue_impl(
                project="PROJ",
                issue_type="Story",
                summary="Test",
                story_points=5,
                client=mock_jira_client,
            )

        mock_agile.assert_called_once_with(project_key="PROJ")
        fields = mock_jira_client.create_issue.call_args[0][0]
        assert fields["customfield_12345"] == 5


@pytest.mark.unit
class TestUpdateIssueParentAndAdf:
    """Tests for parent and ADF handling on update."""

    def test_update_sets_parent(self, mock_jira_client):
        """--parent sets the modern parent field."""
        _update_issue_impl(
            issue_key="PROJ-123", parent="PROJ-100", client=mock_jira_client
        )

        fields = mock_jira_client.update_issue.call_args[0][1]
        assert fields["parent"] == {"key": "PROJ-100"}

    def test_update_clears_parent(self, mock_jira_client):
        """--parent none removes the parent."""
        _update_issue_impl(issue_key="PROJ-123", parent="none", client=mock_jira_client)

        fields = mock_jira_client.update_issue.call_args[0][1]
        assert fields["parent"] is None

    def test_update_wraps_custom_field_in_adf(self, monkeypatch, mock_jira_client):
        """Rich-text custom fields are wrapped on update too."""
        monkeypatch.setenv("JIRA_ADF_CUSTOM_FIELDS", "customfield_10050")

        _update_issue_impl(
            issue_key="PROJ-123",
            custom_fields={"customfield_10050": "notes"},
            client=mock_jira_client,
        )

        fields = mock_jira_client.update_issue.call_args[0][1]
        assert fields["customfield_10050"]["type"] == "doc"


# =============================================================================
# Tests for issue group aliases
# =============================================================================


@pytest.mark.unit
class TestIssueGroupAliases:
    """The issue group exposes transition, transitions and comment aliases."""

    def test_transitions_alias_is_read_only(self, cli_runner, mock_jira_client):
        """'issue transitions' lists transitions without performing one."""
        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_client_from_context",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.lifecycle_cmds._get_transitions_impl",
                return_value=[{"id": "31", "name": "Done", "to": {"name": "Done"}}],
            ) as mock_impl,
        ):
            result = cli_runner.invoke(issue, ["transitions", "PROJ-123"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        mock_jira_client.transition_issue.assert_not_called()

    def test_transition_alias_delegates_to_lifecycle(
        self, cli_runner, mock_jira_client
    ):
        """'issue transition' reuses the lifecycle implementation."""
        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_client_from_context",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.lifecycle_cmds._transition_issue_impl"
            ) as mock_impl,
        ):
            result = cli_runner.invoke(
                issue,
                [
                    "transition",
                    "PROJ-123",
                    "--to",
                    "Done",
                    "--resolution",
                    "Fixed",
                    "--comment",
                    "done",
                ],
            )

        assert result.exit_code == 0
        kwargs = mock_impl.call_args.kwargs
        assert kwargs["transition_name"] == "Done"
        assert kwargs["resolution"] == "Fixed"
        assert kwargs["comment"] == "done"

    def test_transition_alias_requires_a_target(self, cli_runner, mock_jira_client):
        """Neither --to nor --id is a usage error, as in the lifecycle group."""
        with patch(
            "jira_as.cli.commands.issue_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(issue, ["transition", "PROJ-123"])

        assert result.exit_code != 0

    def test_comment_alias_delegates_to_collaborate(self, cli_runner, mock_jira_client):
        """'issue comment' reuses the collaborate implementation."""
        with (
            patch(
                "jira_as.cli.commands.issue_cmds.get_client_from_context",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.collaborate_cmds._add_comment_impl",
                return_value={"id": "10500"},
            ) as mock_impl,
        ):
            result = cli_runner.invoke(
                issue,
                ["comment", "PROJ-123", "--body", "**hi**", "--format", "markdown"],
            )

        assert result.exit_code == 0
        kwargs = mock_impl.call_args.kwargs
        assert kwargs["body"] == "**hi**"
        assert kwargs["body_format"] == "markdown"
        assert "10500" in result.output

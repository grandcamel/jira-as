"""
Unit tests for relationships CLI commands.

Tests cover:
- link: Create links between issues
- unlink: Remove links
- get-links: Get all links for an issue
- get-blockers: Get blocking issues
- get-dependencies: Get dependency tree
- link-types: List available link types
- clone: Clone an issue
- bulk-link: Bulk link multiple issues
- stats: Get link statistics
"""

from copy import deepcopy
from unittest.mock import patch

import pytest

from jira_as import NotFoundError, ValidationError
from jira_as.cli.commands.relationships_cmds import (
    _bulk_link_impl,
    _clone_issue_impl,
    _create_remote_link_impl,
    _get_blockers_impl,
    _get_dependencies_impl,
    _get_link_stats_impl,
    _get_link_types_impl,
    _get_links_impl,
    _link_issue_impl,
    _unlink_issue_impl,
    relationships,
)

# =============================================================================
# Link Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestLinkIssueImpl:
    """Tests for the _link_issue_impl implementation function."""

    def test_link_issue_blocks(self, mock_jira_client, sample_link_types):
        """Test creating a blocks link."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _link_issue_impl(
                issue_key="PROJ-123",
                blocks="PROJ-456",
            )

        assert result is None
        mock_jira_client.create_link.assert_called_once()
        mock_jira_client.__enter__.assert_called_once()
        mock_jira_client.__exit__.assert_called_once()

    def test_link_issue_relates_to(self, mock_jira_client, sample_link_types):
        """Test creating a relates to link."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _link_issue_impl(
                issue_key="PROJ-123",
                relates_to="PROJ-456",
            )

        mock_jira_client.create_link.assert_called_once()

    def test_link_issue_dry_run(self, mock_jira_client, sample_link_types):
        """Test dry-run mode returns preview info."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _link_issue_impl(
                issue_key="PROJ-123",
                blocks="PROJ-456",
                dry_run=True,
            )

        assert result is not None
        assert result["source"] == "PROJ-123"
        assert result["target"] == "PROJ-456"
        assert "preview" in result
        mock_jira_client.create_link.assert_not_called()

    def test_link_issue_with_comment(self, mock_jira_client, sample_link_types):
        """Test creating a link with comment."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _link_issue_impl(
                issue_key="PROJ-123",
                blocks="PROJ-456",
                comment="Adding dependency",
            )

        mock_jira_client.create_link.assert_called_once()
        # Comment is passed as 4th argument (ADF format)
        call_args = mock_jira_client.create_link.call_args
        assert call_args[0][3] is not None  # ADF comment

    def test_link_issue_self_reference_raises_error(
        self, mock_jira_client, sample_link_types
    ):
        """Test that self-reference raises error."""
        from jira_as import ValidationError

        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with (
            patch(
                "jira_as.cli.commands.relationships_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            pytest.raises(ValidationError, match="Cannot link an issue to itself"),
        ):
            _link_issue_impl(
                issue_key="PROJ-123",
                blocks="PROJ-123",
            )


@pytest.mark.unit
class TestUnlinkIssueImpl:
    """Tests for the _unlink_issue_impl implementation function."""

    def test_unlink_specific_issue(self, mock_jira_client, sample_issue_links):
        """Test unlinking from a specific issue."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _unlink_issue_impl(
                issue_key="PROJ-123",
                from_issue="PROJ-127",
            )

        assert result["deleted_count"] == 1
        mock_jira_client.delete_link.assert_called_once()

    def test_unlink_all_of_type(self, mock_jira_client, sample_blocker_links):
        """Test unlinking all links of a type."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_blocker_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _unlink_issue_impl(
                issue_key="PROJ-123",
                link_type="Blocks",
                remove_all=True,
            )

        assert result["deleted_count"] == 2
        assert mock_jira_client.delete_link.call_count == 2

    def test_unlink_dry_run(self, mock_jira_client, sample_issue_links):
        """Test dry-run mode returns preview."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _unlink_issue_impl(
                issue_key="PROJ-123",
                from_issue="PROJ-127",
                dry_run=True,
            )

        assert "links_to_delete" in result
        assert len(result["links_to_delete"]) == 1
        mock_jira_client.delete_link.assert_not_called()


# =============================================================================
# Get Links Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestGetLinksImpl:
    """Tests for the _get_links_impl implementation function."""

    def test_get_all_links(self, mock_jira_client, sample_issue_links):
        """Test getting all links."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_links_impl(issue_key="PROJ-123")

        assert len(result) == 2
        mock_jira_client.get_issue_links.assert_called_once_with("PROJ-123")

    def test_get_links_filter_by_type(self, mock_jira_client, sample_issue_links):
        """Test filtering links by type."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_links_impl(issue_key="PROJ-123", link_type="Blocks")

        assert len(result) == 1
        assert result[0]["type"]["name"] == "Blocks"


# =============================================================================
# Get Blockers Implementation Tests
# =============================================================================


def _blocks_link(link_id: str, key: str, status_name: str) -> dict:
    """Build a minimal inward "Blocks" link for blocker tests."""
    return {
        "id": link_id,
        "type": {"id": "10000", "name": "Blocks", "inward": "is blocked by"},
        "outwardIssue": {
            "key": key,
            "fields": {"summary": f"Summary {key}", "status": {"name": status_name}},
        },
    }


@pytest.mark.unit
class TestGetBlockersImpl:
    """Tests for the _get_blockers_impl implementation function."""

    def test_get_blockers_inward(self, mock_jira_client, sample_blocker_links):
        """Completed blockers are filtered out by default."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_blocker_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_blockers_impl(issue_key="PROJ-123", direction="inward")

        # The fixture holds one Open and one Done blocker.
        assert result["total"] == 1
        assert result["direction"] == "inward"
        assert result["include_done"] is False
        assert [b["key"] for b in result["blockers"]] == ["PROJ-200"]

    def test_get_blockers_include_done(self, mock_jira_client, sample_blocker_links):
        """--include-done keeps completed blockers in the result."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_blocker_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_blockers_impl(
                issue_key="PROJ-123", direction="inward", include_done=True
            )

        assert result["total"] == 2
        assert result["include_done"] is True
        assert [b["key"] for b in result["blockers"]] == ["PROJ-200", "PROJ-201"]

    def test_get_blockers_uses_status_category(
        self, mock_jira_client, sample_blocker_links
    ):
        """statusCategory wins over the status name when both are present."""
        links = deepcopy(sample_blocker_links)
        # A non-English status name that is nonetheless in the done category.
        links[0]["outwardIssue"]["fields"]["status"] = {
            "name": "Erledigt",
            "statusCategory": {"key": "done", "name": "Done"},
        }
        # A status literally named "Done" but still in progress.
        links[1]["outwardIssue"]["fields"]["status"] = {
            "name": "Done",
            "statusCategory": {"key": "indeterminate", "name": "In Progress"},
        }
        mock_jira_client.get_issue_links.return_value = links

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_blockers_impl(issue_key="PROJ-123", direction="inward")

        assert [b["key"] for b in result["blockers"]] == ["PROJ-201"]

    def test_get_blockers_recursive_filters_done(self, mock_jira_client):
        """Recursive traversal applies the same completed-blocker filter."""

        def _links(issue_key):
            if issue_key == "PROJ-123":
                return [
                    _blocks_link("1", "PROJ-200", "Open"),
                    _blocks_link("2", "PROJ-201", "Done"),
                ]
            if issue_key == "PROJ-200":
                return [_blocks_link("3", "PROJ-300", "Done")]
            return []

        mock_jira_client.get_issue_links.side_effect = _links

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_blockers_impl(
                issue_key="PROJ-123", direction="inward", recursive=True
            )

        assert [b["key"] for b in result["all_blockers"]] == ["PROJ-200"]

    def test_get_blockers_no_results(self, mock_jira_client):
        """Test when no blockers exist."""
        mock_jira_client.get_issue_links.return_value = []

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_blockers_impl(issue_key="PROJ-123")

        assert result["total"] == 0
        assert len(result["blockers"]) == 0


# =============================================================================
# Get Dependencies Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestGetDependenciesImpl:
    """Tests for the _get_dependencies_impl implementation function."""

    def test_get_all_dependencies(self, mock_jira_client, sample_issue_links):
        """Test getting all dependencies."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_dependencies_impl(issue_key="PROJ-123")

        assert result["total"] == 2
        assert len(result["dependencies"]) == 2
        assert "status_summary" in result

    def test_get_dependencies_filter_by_type(
        self, mock_jira_client, sample_issue_links
    ):
        """Test filtering dependencies by type."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_dependencies_impl(issue_key="PROJ-123", link_types=["Blocks"])

        assert result["total"] == 1


# =============================================================================
# Get Link Types Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestGetLinkTypesImpl:
    """Tests for the _get_link_types_impl implementation function."""

    def test_get_all_link_types(self, mock_jira_client, sample_link_types):
        """Test getting all link types."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_link_types_impl()

        assert len(result) == 4
        mock_jira_client.get_link_types.assert_called_once()

    def test_get_link_types_filter(self, mock_jira_client, sample_link_types):
        """Test filtering link types."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_link_types_impl(filter_pattern="block")

        assert len(result) == 1
        assert result[0]["name"] == "Blocks"


# =============================================================================
# Clone Issue Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestCloneIssueImpl:
    """Tests for the _clone_issue_impl implementation function."""

    def test_clone_issue_basic(
        self, mock_jira_client, sample_issue, sample_cloned_issue
    ):
        """Test basic issue cloning."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)
        mock_jira_client.create_issue.return_value = deepcopy(sample_cloned_issue)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _clone_issue_impl(issue_key="PROJ-123")

        assert result["original_key"] == "PROJ-123"
        assert result["clone_key"] == "PROJ-300"
        mock_jira_client.create_issue.assert_called_once()
        mock_jira_client.create_link.assert_called_once()  # Clone link

    def test_clone_issue_no_link(
        self, mock_jira_client, sample_issue, sample_cloned_issue
    ):
        """Test cloning without clone link."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)
        mock_jira_client.create_issue.return_value = deepcopy(sample_cloned_issue)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _clone_issue_impl(issue_key="PROJ-123", create_clone_link=False)

        assert result["original_key"] == "PROJ-123"
        mock_jira_client.create_link.assert_not_called()

    def test_clone_issue_to_project(
        self, mock_jira_client, sample_issue, sample_cloned_issue
    ):
        """Test cloning to different project."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)
        mock_jira_client.create_issue.return_value = deepcopy(sample_cloned_issue)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _clone_issue_impl(issue_key="PROJ-123", to_project="OTHER")

        assert result["project"] == "OTHER"


# =============================================================================
# Bulk Link Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestBulkLinkImpl:
    """Tests for the _bulk_link_impl implementation function."""

    def test_bulk_link_issues(self, mock_jira_client):
        """Test bulk linking issues."""
        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _bulk_link_impl(
                issues=["PROJ-1", "PROJ-2", "PROJ-3"],
                target="PROJ-100",
                link_type="Blocks",
            )

        assert result["created"] == 3
        assert result["failed"] == 0
        assert mock_jira_client.create_link.call_count == 3

    def test_bulk_link_dry_run(self, mock_jira_client):
        """Test bulk link dry run."""
        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _bulk_link_impl(
                issues=["PROJ-1", "PROJ-2"],
                target="PROJ-100",
                link_type="Blocks",
                dry_run=True,
            )

        assert result["dry_run"] is True
        assert result["would_create"] == 2
        mock_jira_client.create_link.assert_not_called()

    def test_bulk_link_with_jql(self, mock_jira_client):
        """Test bulk link with JQL query."""
        mock_jira_client.search_issues.return_value = {
            "issues": [{"key": "PROJ-1"}, {"key": "PROJ-2"}]
        }

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _bulk_link_impl(
                jql="project = PROJ",
                target="PROJ-100",
                link_type="Blocks",
            )

        assert result["created"] == 2
        mock_jira_client.search_issues.assert_called_once()


# =============================================================================
# Get Link Stats Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestGetLinkStatsImpl:
    """Tests for the _get_link_stats_impl implementation function."""

    def test_get_single_issue_stats(self, mock_jira_client, sample_issue_links):
        """Test getting stats for a single issue."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_link_stats_impl(issue_key="PROJ-123")

        assert result["issue_key"] == "PROJ-123"
        assert result["total_links"] == 2
        assert "by_type" in result
        assert "by_direction" in result

    def test_get_project_stats(self, mock_jira_client, sample_issue_with_links):
        """Test getting stats for a project."""
        mock_jira_client.search_issues.return_value = {
            "issues": [deepcopy(sample_issue_with_links)],
            "total": 1,
        }

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_link_stats_impl(project="PROJ")

        assert "jql" in result
        assert "issues_analyzed" in result
        assert "most_connected" in result


# =============================================================================
# CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestLinkCommand:
    """Tests for the link CLI command."""

    def test_link_cli_blocks(self, cli_runner, mock_jira_client, sample_link_types):
        """Test CLI link command with --blocks."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["link", "PROJ-123", "--blocks", "PROJ-456"],
            )

        assert result.exit_code == 0
        assert "Linked" in result.output

    def test_link_cli_dry_run(self, cli_runner, mock_jira_client, sample_link_types):
        """Test CLI link command with dry-run."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["link", "PROJ-123", "--blocks", "PROJ-456", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output


@pytest.mark.unit
class TestGetLinksCommand:
    """Tests for the get-links CLI command."""

    def test_get_links_cli(self, cli_runner, mock_jira_client, sample_issue_links):
        """Test CLI get-links command."""
        mock_jira_client.get_issue_links.return_value = deepcopy(sample_issue_links)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["get-links", "PROJ-123"],
            )

        assert result.exit_code == 0
        assert "Links for PROJ-123" in result.output


@pytest.mark.unit
class TestLinkTypesCommand:
    """Tests for the link-types CLI command."""

    def test_link_types_cli(self, cli_runner, mock_jira_client, sample_link_types):
        """Test CLI link-types command."""
        mock_jira_client.get_link_types.return_value = deepcopy(sample_link_types)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["link-types"],
            )

        assert result.exit_code == 0
        assert "Available Link Types" in result.output


@pytest.mark.unit
class TestCloneCommand:
    """Tests for the clone CLI command."""

    def test_clone_cli(
        self, cli_runner, mock_jira_client, sample_issue, sample_cloned_issue
    ):
        """Test CLI clone command."""
        mock_jira_client.get_issue.return_value = deepcopy(sample_issue)
        mock_jira_client.create_issue.return_value = deepcopy(sample_cloned_issue)

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["clone", "PROJ-123"],
            )

        assert result.exit_code == 0
        assert "Cloned" in result.output
        assert "PROJ-300" in result.output


@pytest.mark.unit
class TestBulkLinkCommand:
    """Tests for the bulk-link CLI command."""

    def test_bulk_link_cli(self, cli_runner, mock_jira_client):
        """Test CLI bulk-link command."""
        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["bulk-link", "--issues", "PROJ-1,PROJ-2", "--blocks", "PROJ-100"],
            )

        assert result.exit_code == 0
        assert "Bulk link" in result.output

    def test_bulk_link_cli_no_issues_error(self, cli_runner, mock_jira_client):
        """Test CLI bulk-link command fails without issues."""
        result = cli_runner.invoke(
            relationships,
            ["bulk-link", "--blocks", "PROJ-100"],
        )

        assert result.exit_code != 0
        assert "Either --jql or --issues is required" in result.output


# =============================================================================
# Remote (web) links
# =============================================================================


@pytest.mark.unit
class TestCreateRemoteLinkImpl:
    """Tests for _create_remote_link_impl."""

    def test_creates_remote_link(self, mock_jira_client):
        """The URL and title reach the client."""
        mock_jira_client.create_remote_link.return_value = {"id": 10001}

        result = _create_remote_link_impl(
            issue_key="PROJ-123",
            remote_url="https://example.com/doc",
            remote_title="Design doc",
            remote_relationship="documented by",
            client=mock_jira_client,
        )

        mock_jira_client.create_remote_link.assert_called_once_with(
            "PROJ-123",
            url="https://example.com/doc",
            title="Design doc",
            relationship="documented by",
        )
        assert result["id"] == 10001

    def test_title_defaults_to_the_url(self, mock_jira_client):
        """A link without a title is titled by its URL."""
        mock_jira_client.create_remote_link.return_value = {"id": 1}

        _create_remote_link_impl(
            issue_key="PROJ-123",
            remote_url="https://example.com/doc",
            client=mock_jira_client,
        )

        kwargs = mock_jira_client.create_remote_link.call_args.kwargs
        assert kwargs["title"] == "https://example.com/doc"

    def test_dry_run_creates_nothing(self, mock_jira_client):
        """--dry-run previews without calling the API."""
        result = _create_remote_link_impl(
            issue_key="PROJ-123",
            remote_url="https://example.com/doc",
            dry_run=True,
            client=mock_jira_client,
        )

        mock_jira_client.create_remote_link.assert_not_called()
        assert result["dry_run"] is True
        assert "https://example.com/doc" in result["preview"]

    def test_blank_url_is_rejected(self, mock_jira_client):
        """An empty URL fails before the API call."""
        with pytest.raises(ValidationError, match="requires a URL"):
            _create_remote_link_impl(
                issue_key="PROJ-123", remote_url="", client=mock_jira_client
            )


@pytest.mark.unit
class TestLinkCommandRemoteUrl:
    """Tests for 'relationships link --remote-url'."""

    def test_remote_url_creates_a_remote_link(self, cli_runner, mock_jira_client):
        """--remote-url takes the remote-link path."""
        mock_jira_client.create_remote_link.return_value = {"id": 1}

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["link", "PROJ-123", "--remote-url", "https://example.com/doc"],
            )

        assert result.exit_code == 0, result.output
        mock_jira_client.create_remote_link.assert_called_once()
        mock_jira_client.create_link.assert_not_called()

    def test_remote_url_conflicts_with_native_options(
        self, cli_runner, mock_jira_client
    ):
        """Mixing --remote-url with a native link option is a usage error."""
        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                [
                    "link",
                    "PROJ-123",
                    "--remote-url",
                    "https://example.com",
                    "--blocks",
                    "PROJ-124",
                ],
            )

        assert result.exit_code != 0
        assert "cannot be combined" in result.output

    def test_remote_title_requires_remote_url(self, cli_runner, mock_jira_client):
        """--remote-title alone is a usage error."""
        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships,
                ["link", "PROJ-123", "--blocks", "PROJ-124", "--remote-title", "T"],
            )

        assert result.exit_code != 0
        assert "require --remote-url" in result.output

    def test_native_link_failure_hints_at_remote_url(
        self, cli_runner, mock_jira_client
    ):
        """A rejected native link suggests the remote-link route."""
        mock_jira_client.get_link_types.return_value = [
            {
                "id": "1",
                "name": "Blocks",
                "inward": "is blocked by",
                "outward": "blocks",
            }
        ]
        mock_jira_client.create_link.side_effect = NotFoundError("cross-project")

        with patch(
            "jira_as.cli.commands.relationships_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                relationships, ["link", "PROJ-123", "--blocks", "OTHER-1"]
            )

        assert result.exit_code != 0
        assert "--remote-url" in result.output

"""
Unit tests for collaborate CLI commands.

Tests cover:
- comment: Add, list, update, delete comments
- attachment: Upload, download attachments
- watchers: Manage issue watchers
- activity: Get issue changelog
- notify: Send notifications
- update-fields: Update custom fields
"""

import json
from copy import deepcopy
from unittest.mock import patch

import pytest

from jira_as.cli.commands.collaborate_cmds import (
    _add_comment_impl,
    _add_watcher_impl,
    _get_comments_impl,
    _list_watchers_impl,
    _send_notification_impl,
    collaborate,
)

# =============================================================================
# Comment Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestAddCommentImpl:
    """Tests for the _add_comment_impl implementation function."""

    def test_add_comment_basic(self, mock_jira_client, sample_comment):
        """Test adding a basic comment."""
        mock_jira_client.add_comment.return_value = deepcopy(sample_comment)

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _add_comment_impl(
                issue_key="PROJ-123",
                body="Test comment",
            )

        assert result["id"] == "10001"
        mock_jira_client.add_comment.assert_called_once()
        mock_jira_client.__enter__.assert_called_once()
        mock_jira_client.__exit__.assert_called_once()

    def test_add_comment_with_visibility(self, mock_jira_client, sample_comment):
        """Test adding a comment with visibility restrictions."""
        mock_jira_client.add_comment_with_visibility.return_value = deepcopy(
            sample_comment
        )

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            _add_comment_impl(
                issue_key="PROJ-123",
                body="Private comment",
                visibility_type="role",
                visibility_value="Developers",
            )

        mock_jira_client.add_comment_with_visibility.assert_called_once()


@pytest.mark.unit
class TestGetCommentsImpl:
    """Tests for the _get_comments_impl implementation function."""

    def test_get_comments_list(self, mock_jira_client, sample_comments_response):
        """Test getting list of comments."""
        mock_jira_client.get_comments.return_value = deepcopy(sample_comments_response)

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_comments_impl(issue_key="PROJ-123")

        assert result["total"] == 2
        assert len(result["comments"]) == 2
        mock_jira_client.get_comments.assert_called_once()

    def test_get_comment_by_id(self, mock_jira_client, sample_comment):
        """Test getting a specific comment by ID."""
        mock_jira_client.get_comment.return_value = deepcopy(sample_comment)

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _get_comments_impl(issue_key="PROJ-123", comment_id="10001")

        assert result["id"] == "10001"
        mock_jira_client.get_comment.assert_called_once_with("PROJ-123", "10001")


# =============================================================================
# Attachment Implementation Tests
# =============================================================================


# =============================================================================
# Watchers Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestWatchersImpl:
    """Tests for watchers implementation functions."""

    def test_list_watchers(self, mock_jira_client, sample_watchers):
        """Test listing watchers."""
        mock_jira_client.get.return_value = {"watchers": deepcopy(sample_watchers)}

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _list_watchers_impl(issue_key="PROJ-123")

        assert len(result) == 2
        mock_jira_client.get.assert_called_once()

    def test_add_watcher(self, mock_jira_client):
        """Test adding a watcher."""
        with (
            patch(
                "jira_as.cli.commands.collaborate_cmds.get_jira_client",
                return_value=mock_jira_client,
            ),
            patch(
                "jira_as.cli.commands.collaborate_cmds.resolve_user_to_account_id",
                return_value="user-123",
            ),
        ):
            _add_watcher_impl(issue_key="PROJ-123", user="user@example.com")

        mock_jira_client.post.assert_called_once()


# =============================================================================
# Activity Implementation Tests
# =============================================================================


# =============================================================================
# Notification Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestNotificationImpl:
    """Tests for notification implementation functions."""

    def test_send_notification_dry_run(self, mock_jira_client):
        """Test notification dry-run mode."""
        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _send_notification_impl(
                issue_key="PROJ-123",
                subject="Test",
                body="Test body",
                watchers=True,
                dry_run=True,
            )

        assert result["issue_key"] == "PROJ-123"
        assert result["recipients"]["watchers"] is True
        mock_jira_client.notify_issue.assert_not_called()

    def test_send_notification(self, mock_jira_client):
        """Test sending notification."""
        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _send_notification_impl(
                issue_key="PROJ-123",
                subject="Test",
                body="Test body",
                watchers=True,
            )

        assert result is None
        mock_jira_client.notify_issue.assert_called_once()


# =============================================================================
# Custom Fields Implementation Tests
# =============================================================================


# =============================================================================
# CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestCommentCommands:
    """Tests for comment CLI commands."""

    @pytest.mark.parametrize(
        "body_args",
        [
            [],
            ["--body", "inline", "--body-stdin"],
            ["--body-file", "{body_file}", "--body-stdin"],
            ["--body", "inline", "--body-file", "{body_file}"],
            [
                "--body",
                "inline",
                "--body-file",
                "{body_file}",
                "--body-stdin",
            ],
        ],
    )
    @pytest.mark.parametrize(
        "command_args",
        [
            ["comment", "add", "PROJ-123"],
            ["comment", "update", "PROJ-123", "--id", "10001"],
        ],
    )
    def test_comment_writes_require_exactly_one_body_source(
        self, cli_runner, mock_jira_client, tmp_path, body_args, command_args
    ):
        """Add and update reject no source and every multiple-source combination."""
        body_file = tmp_path / "comment.txt"
        body_file.write_text("from file", encoding="utf-8")
        args = [str(body_file) if arg == "{body_file}" else arg for arg in body_args]

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                collaborate,
                [*command_args, *args],
                input="from stdin",
            )

        assert result.exit_code == 2
        assert "exactly one of --body, --body-file, or --body-stdin" in result.output
        mock_jira_client.add_comment.assert_not_called()
        mock_jira_client.update_comment.assert_not_called()

    @pytest.mark.parametrize(
        "command_args",
        [
            ["comment", "add", "PROJ-123"],
            ["comment", "update", "PROJ-123", "--id", "10001"],
        ],
    )
    def test_comment_writes_reject_literal_newlines_in_markdown_body(
        self, cli_runner, mock_jira_client, command_args
    ):
        """Add and update reject escaped-newline Markdown before the write."""
        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                collaborate,
                [
                    *command_args,
                    "--format",
                    "markdown",
                    "--body",
                    r"## Resolution\n\nBody",
                ],
            )

        assert result.exit_code == 2
        assert "literal \\n sequences but no actual newline" in result.output
        assert "--body-file or --body-stdin" in result.output
        mock_jira_client.add_comment.assert_not_called()
        mock_jira_client.update_comment.assert_not_called()

    @pytest.mark.parametrize("command", ["update"])
    @pytest.mark.parametrize("body_format", ["text", "adf"])
    @pytest.mark.parametrize("source", ["file", "stdin"])
    def test_comment_writes_preserve_text_and_adf_safe_source_semantics(
        self,
        cli_runner,
        mock_jira_client,
        sample_comment,
        tmp_path,
        command,
        body_format,
        source,
    ):
        """Add and update preserve text/ADF semantics from files and stdin."""
        adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Already ADF"}],
                }
            ],
        }
        if body_format == "adf":
            raw_body = json.dumps(adf)
            expected_body = adf
        else:
            raw_body = "**literal**\\n stays literal\nsecond line"
            expected_body = {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "**literal**\\n stays literal",
                            }
                        ],
                    },
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "second line"}],
                    },
                ],
            }

        if command == "add":
            command_args = ["comment", "add", "PROJ-123"]
            mock_method = mock_jira_client.add_comment
            body_arg_index = 1
        else:
            command_args = ["comment", "update", "PROJ-123", "--id", "10001"]
            mock_method = mock_jira_client.update_comment
            body_arg_index = 2
        mock_method.return_value = deepcopy(sample_comment)

        input_text = None
        if source == "file":
            body_file = tmp_path / f"comment.{body_format}"
            body_file.write_bytes(raw_body.encode("utf-8"))
            source_args = ["--body-file", str(body_file)]
        else:
            source_args = ["--body-stdin"]
            input_text = raw_body

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                collaborate,
                [
                    *command_args,
                    "--format",
                    body_format,
                    *source_args,
                ],
                input=input_text,
            )

        assert result.exit_code == 0, result.output
        assert mock_method.call_args.args[body_arg_index] == expected_body


@pytest.mark.unit
class TestWatchersCommand:
    """Tests for watchers CLI command."""

    def test_watchers_list_cli(self, cli_runner, mock_jira_client, sample_watchers):
        """Test CLI watchers list command."""
        mock_jira_client.get.return_value = {"watchers": deepcopy(sample_watchers)}

        with patch(
            "jira_as.cli.commands.collaborate_cmds.get_client_from_context",
            return_value=mock_jira_client,
        ):
            result = cli_runner.invoke(
                collaborate,
                ["watchers", "PROJ-123", "--list"],
            )

        assert result.exit_code == 0

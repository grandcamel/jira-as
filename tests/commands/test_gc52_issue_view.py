"""Regression tests for GC-52's one-command issue view."""

import json
from copy import deepcopy
from unittest.mock import patch

import pytest

from jira_as.cli.commands.issue_cmds import _get_all_comments_impl, issue
from jira_as.cli.main import cli
from jira_as.mock import MockJiraClient


@pytest.mark.unit
def test_issue_get_comments_renders_description_and_adf_comments(
    cli_runner, mock_jira_client, sample_issue
):
    mock_jira_client.get_issue.return_value = deepcopy(sample_issue)
    mock_jira_client.get_comments.return_value = {
        "startAt": 0,
        "maxResults": 100,
        "total": 1,
        "comments": [
            {
                "id": "10001",
                "author": {"displayName": "Ada Lovelace"},
                "created": "2026-08-31T12:00:00.000+0000",
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "Rendered comment body"}
                            ],
                        }
                    ],
                },
            }
        ],
    }

    with patch(
        "jira_as.cli.commands.issue_cmds.get_client_from_context",
        return_value=mock_jira_client,
    ):
        result = cli_runner.invoke(issue, ["get", "PROJ-123", "--comments"])

    assert result.exit_code == 0, result.output
    assert "This is a test description." in result.output
    assert "Comments (1):" in result.output
    assert "Ada Lovelace" in result.output
    assert "Rendered comment body" in result.output
    mock_jira_client.get_comments.assert_called_once_with(
        "PROJ-123", max_results=100, start_at=0, order_by="created"
    )


@pytest.mark.unit
def test_issue_get_comments_fetches_every_comment_page(
    cli_runner, mock_jira_client, sample_issue
):
    mock_jira_client.get_issue.return_value = deepcopy(sample_issue)
    mock_jira_client.get_comments.side_effect = [
        {
            "startAt": 0,
            "maxResults": 100,
            "total": 101,
            "comments": [{"body": "first page"}] * 100,
        },
        {
            "startAt": 100,
            "maxResults": 100,
            "total": 101,
            "comments": [{"body": "last page"}],
        },
    ]

    with patch(
        "jira_as.cli.commands.issue_cmds.get_client_from_context",
        return_value=mock_jira_client,
    ):
        result = cli_runner.invoke(
            issue, ["get", "PROJ-123", "--comments", "--output", "json"]
        )

    assert result.exit_code == 0, result.output
    assert len(json.loads(result.output)["fields"]["comment"]["comments"]) == 101
    assert mock_jira_client.get_comments.call_count == 2


@pytest.mark.unit
def test_issue_comment_paging_works_with_supported_mock_client():
    client = MockJiraClient()
    client.add_comment("DEMO-84", "Mock comment")

    result = _get_all_comments_impl(client, "DEMO-84")

    assert result["comments"][-1]["body"] == "Mock comment"


@pytest.mark.unit
def test_collaborate_comments_is_a_discoverable_comment_alias(cli_runner):
    result = cli_runner.invoke(cli, ["collaborate", "comments", "--help"])

    assert result.exit_code == 0, result.output
    assert "Manage issue comments" in result.output


@pytest.mark.unit
def test_search_jql_is_a_discoverable_query_alias(cli_runner):
    result = cli_runner.invoke(cli, ["search", "jql", "--help"])

    assert result.exit_code == 0, result.output
    assert "Search for issues using JQL query" in result.output

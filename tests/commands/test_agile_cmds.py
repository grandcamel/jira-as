"""Tests for agile_cmds.py - Agile/Scrum commands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from jira_as import ValidationError
from jira_as.cli.commands.agile_cmds import (
    FIBONACCI_SEQUENCE,
    VALID_EPIC_COLORS,
    _add_to_epic_impl,
    _close_sprint_impl,
    _convert_description_to_adf,
    _create_subtask_impl,
    _estimate_issue_impl,
    _format_epic_details,
    _format_sprint_details,
    _format_velocity,
    _get_backlog_impl,
    _get_board_for_project,
    _get_board_id_for_project,
    _get_velocity_impl,
    _move_to_sprint_impl,
    _parse_date_safe,
    _rank_issue_impl,
    _start_sprint_impl,
    _update_sprint_impl,
    agile,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Create a mock JIRA client with context manager support."""
    client = MagicMock()
    client.close = MagicMock()
    # Support context manager pattern: with get_jira_client() as client:
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=None)
    return client


@pytest.fixture
def sample_epic():
    """Sample epic data."""
    return {
        "id": "10001",
        "key": "PROJ-100",
        "self": "https://test.atlassian.net/rest/api/3/issue/10001",
        "fields": {
            "summary": "Epic Summary",
            "status": {"name": "To Do"},
            "issuetype": {"name": "Epic"},
            "project": {"key": "PROJ"},
            "customfield_10011": "Epic Name Value",
        },
    }


@pytest.fixture
def sample_sprint():
    """Sample sprint data."""
    return {
        "id": 456,
        "name": "Sprint 1",
        "state": "active",
        "startDate": "2024-01-01T00:00:00.000Z",
        "endDate": "2024-01-14T00:00:00.000Z",
        "goal": "Complete feature X",
    }


@pytest.fixture
def sample_board():
    """Sample board data."""
    return {
        "id": 123,
        "name": "PROJ board",
        "type": "scrum",
        "location": {"projectKey": "PROJ"},
    }


@pytest.fixture
def sample_issues():
    """Sample issues for sprint/backlog."""
    return [
        {
            "key": "PROJ-1",
            "fields": {
                "summary": "Issue 1",
                "status": {"name": "To Do"},
                "customfield_10016": 5,
            },
        },
        {
            "key": "PROJ-2",
            "fields": {
                "summary": "Issue 2",
                "status": {"name": "Done"},
                "customfield_10016": 3,
            },
        },
        {
            "key": "PROJ-3",
            "fields": {
                "summary": "Issue 3",
                "status": {"name": "In Progress"},
                "customfield_10016": 8,
            },
        },
    ]


@pytest.fixture
def sample_velocity_sprints():
    """Sample closed sprints for velocity calculation."""
    return [
        {
            "id": 101,
            "name": "Sprint 1",
            "state": "closed",
            "startDate": "2024-01-01T00:00:00.000Z",
            "endDate": "2024-01-14T00:00:00.000Z",
        },
        {
            "id": 102,
            "name": "Sprint 2",
            "state": "closed",
            "startDate": "2024-01-15T00:00:00.000Z",
            "endDate": "2024-01-28T00:00:00.000Z",
        },
        {
            "id": 103,
            "name": "Sprint 3",
            "state": "closed",
            "startDate": "2024-01-29T00:00:00.000Z",
            "endDate": "2024-02-11T00:00:00.000Z",
        },
    ]


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for constants."""

    def test_valid_epic_colors(self):
        """Test valid epic colors."""
        assert "blue" in VALID_EPIC_COLORS
        assert "red" in VALID_EPIC_COLORS
        assert "green" in VALID_EPIC_COLORS
        assert len(VALID_EPIC_COLORS) == 11

    def test_fibonacci_sequence(self):
        """Test Fibonacci sequence."""
        assert FIBONACCI_SEQUENCE == [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_board_for_project_scrum_board(self, mock_client):
        """Test finding scrum board for project."""
        mock_client.get_all_boards.return_value = {
            "values": [
                {"id": 1, "name": "Board 1", "type": "scrum"},
                {"id": 2, "name": "Board 2", "type": "kanban"},
            ]
        }

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _get_board_for_project("PROJ")

        assert result["id"] == 1
        assert result["type"] == "scrum"
        mock_client.__exit__.assert_called_once()

    def test_get_board_for_project_kanban_fallback(self, mock_client):
        """Test falling back to any board when no scrum board."""
        mock_client.get_all_boards.return_value = {
            "values": [{"id": 2, "name": "Board 2", "type": "kanban"}]
        }

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _get_board_for_project("PROJ")

        assert result["id"] == 2
        assert result["type"] == "kanban"

    def test_get_board_for_project_no_board(self, mock_client):
        """Test no board found."""
        mock_client.get_all_boards.return_value = {"values": []}

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _get_board_for_project("PROJ")

        assert result is None

    def test_get_board_for_project_with_client(self, mock_client):
        """Test with provided client."""
        mock_client.get_all_boards.return_value = {
            "values": [{"id": 1, "name": "Board", "type": "scrum"}]
        }

        result = _get_board_for_project("PROJ", client=mock_client)

        assert result["id"] == 1
        mock_client.close.assert_not_called()

    def test_get_board_id_for_project_success(self, mock_client):
        """Test getting board ID for project."""
        mock_client.get_all_boards.return_value = {
            "values": [{"id": 123, "name": "Board", "type": "scrum"}]
        }

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _get_board_id_for_project("PROJ")

        assert result == 123

    def test_get_board_id_for_project_no_board(self, mock_client):
        """Test error when no board found."""
        mock_client.get_all_boards.return_value = {"values": []}

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            with pytest.raises(ValidationError, match="No board found"):
                _get_board_id_for_project("PROJ")

    def test_parse_date_safe_valid(self):
        """Test parsing valid date."""
        with patch(
            "jira_as.cli.commands.agile_cmds.parse_date_to_iso",
            return_value="2024-01-15T00:00:00.000Z",
        ):
            result = _parse_date_safe("2024-01-15")
            assert result == "2024-01-15T00:00:00.000Z"

    def test_parse_date_safe_none(self):
        """Test parsing None date."""
        result = _parse_date_safe(None)
        assert result is None

    def test_parse_date_safe_empty(self):
        """Test parsing empty date."""
        result = _parse_date_safe("")
        assert result is None

    def test_parse_date_safe_invalid(self):
        """Test parsing invalid date."""
        with patch(
            "jira_as.cli.commands.agile_cmds.parse_date_to_iso",
            side_effect=ValueError("Invalid date"),
        ):
            with pytest.raises(ValidationError, match="Invalid date"):
                _parse_date_safe("invalid")

    def test_convert_description_to_adf_json(self):
        """Test converting JSON description to ADF."""
        adf_json = '{"type": "doc", "version": 1, "content": []}'
        result = _convert_description_to_adf(adf_json)
        assert result == {"type": "doc", "version": 1, "content": []}

    def test_convert_description_to_adf_markdown(self):
        """Test converting markdown description to ADF."""
        with patch(
            "jira_as.cli.commands.agile_cmds.markdown_to_adf",
            return_value={"type": "doc", "content": []},
        ):
            result = _convert_description_to_adf("# Heading\n\nText")
            assert result == {"type": "doc", "content": []}

    def test_convert_description_to_adf_plain_text(self):
        """Test converting plain text description to ADF."""
        with patch(
            "jira_as.cli.commands.agile_cmds.text_to_adf",
            return_value={"type": "doc", "content": []},
        ):
            result = _convert_description_to_adf("Plain text")
            assert result == {"type": "doc", "content": []}


# =============================================================================
# Epic Implementation Tests
# =============================================================================


class TestEpicImplementation:
    """Tests for epic implementation functions."""

    def test_add_to_epic_impl_success(self, mock_client, sample_epic):
        """Test adding issues to epic."""
        mock_client.get_issue.return_value = sample_epic

        with (
            patch(
                "jira_as.cli.commands.agile_cmds.get_jira_client",
                return_value=mock_client,
            ),
            patch(
                "jira_as.cli.commands.agile_cmds.get_agile_field",
                return_value="customfield_10014",
            ),
        ):
            result = _add_to_epic_impl("PROJ-100", ["PROJ-1", "PROJ-2"])

        assert result["added"] == 2
        assert result["failed"] == 0
        assert mock_client.update_issue.call_count == 2
        mock_client.__enter__.assert_called_once()
        mock_client.__exit__.assert_called_once()

    def test_add_to_epic_impl_dry_run(self, mock_client, sample_epic):
        """Test dry run for adding issues to epic."""
        mock_client.get_issue.return_value = sample_epic

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _add_to_epic_impl("PROJ-100", ["PROJ-1", "PROJ-2"], dry_run=True)

        assert result["would_add"] == 2
        mock_client.update_issue.assert_not_called()

    def test_add_to_epic_impl_not_epic(self, mock_client):
        """Test error when target is not an epic."""
        mock_client.get_issue.return_value = {
            "key": "PROJ-100",
            "fields": {"issuetype": {"name": "Story"}},
        }

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            with pytest.raises(ValidationError, match="not an Epic"):
                _add_to_epic_impl("PROJ-100", ["PROJ-1"])

    def test_add_to_epic_impl_missing_issues(self, mock_client):
        """Test error when no issues provided."""
        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            with pytest.raises(ValidationError, match="At least one issue key"):
                _add_to_epic_impl("PROJ-100", [])


# =============================================================================
# Sprint Implementation Tests
# =============================================================================


class TestSprintImplementation:
    """Tests for sprint implementation functions."""

    def test_start_sprint_impl(self, mock_client, sample_sprint):
        """Test starting sprint."""
        mock_client.update_sprint.return_value = {**sample_sprint, "state": "active"}

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _start_sprint_impl(456)

        assert result["state"] == "active"
        mock_client.update_sprint.assert_called_once()
        call_kwargs = mock_client.update_sprint.call_args[1]
        assert call_kwargs["state"] == "active"

    def test_close_sprint_impl(self, mock_client, sample_sprint):
        """Test closing sprint."""
        mock_client.update_sprint.return_value = {**sample_sprint, "state": "closed"}

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _close_sprint_impl(456)

        assert result["state"] == "closed"
        mock_client.update_sprint.assert_called_once()

    def test_close_sprint_impl_with_move(self, mock_client, sample_sprint):
        """Incomplete issues are found first, then moved to the target sprint."""
        mock_client.update_sprint.return_value = {**sample_sprint, "state": "closed"}
        # move_issues_to_sprint returns None and takes a list of issue keys.
        mock_client.move_issues_to_sprint.return_value = None
        mock_client.search_issues.return_value = {
            "issues": [{"key": f"PROJ-{n}"} for n in range(1, 6)]
        }

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _close_sprint_impl(456, move_incomplete_to=457)

        assert result["moved_issues"] == 5
        mock_client.move_issues_to_sprint.assert_called_once_with(
            457, ["PROJ-1", "PROJ-2", "PROJ-3", "PROJ-4", "PROJ-5"]
        )
        assert result["state"] == "closed"

    def test_close_sprint_impl_with_nothing_to_move(self, mock_client, sample_sprint):
        """A sprint with no open issues closes without a move call."""
        mock_client.update_sprint.return_value = {**sample_sprint, "state": "closed"}
        mock_client.search_issues.return_value = {"issues": []}

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _close_sprint_impl(456, move_incomplete_to=457)

        assert result["moved_issues"] == 0
        mock_client.move_issues_to_sprint.assert_not_called()

    def test_update_sprint_impl(self, mock_client, sample_sprint):
        """Test updating sprint."""
        mock_client.update_sprint.return_value = {**sample_sprint, "name": "New Name"}

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _update_sprint_impl(456, name="New Name", goal="New goal")

        assert result["name"] == "New Name"
        call_kwargs = mock_client.update_sprint.call_args[1]
        assert call_kwargs["name"] == "New Name"
        assert call_kwargs["goal"] == "New goal"

    def test_update_sprint_impl_no_fields(self, mock_client):
        """Test error when no fields to update."""
        with pytest.raises(ValidationError, match="At least one field"):
            _update_sprint_impl(456)

    def test_move_to_sprint_impl_success(self, mock_client):
        """Test moving issues to sprint."""
        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _move_to_sprint_impl(456, issue_keys=["PROJ-1", "PROJ-2"])

        assert result["moved"] == 2
        mock_client.move_issues_to_sprint.assert_called_once()

    def test_move_to_sprint_impl_with_jql(self, mock_client, sample_issues):
        """Test moving issues to sprint with JQL."""
        mock_client.search_issues.return_value = {"issues": sample_issues}

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _move_to_sprint_impl(456, jql="project = PROJ")

        assert result["moved"] == 3

    def test_move_to_sprint_impl_dry_run(self, mock_client):
        """Test dry run for moving issues."""
        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _move_to_sprint_impl(456, issue_keys=["PROJ-1"], dry_run=True)

        assert result["would_move"] == 1
        mock_client.move_issues_to_sprint.assert_not_called()


# =============================================================================
# Backlog/Rank Implementation Tests
# =============================================================================


class TestBacklogRankImplementation:
    """Tests for backlog and rank implementation functions."""

    def test_get_backlog_impl_by_board(self, mock_client, sample_issues):
        """Test getting backlog by board."""
        mock_client.get_board_backlog.return_value = {
            "issues": sample_issues,
            "total": 3,
        }

        with (
            patch(
                "jira_as.cli.commands.agile_cmds.get_jira_client",
                return_value=mock_client,
            ),
            patch(
                "jira_as.cli.commands.agile_cmds.get_agile_fields",
                return_value={
                    "epic_link": "customfield_10014",
                    "story_points": "customfield_10016",
                },
            ),
        ):
            result = _get_backlog_impl(board_id=123)

        assert len(result["issues"]) == 3
        mock_client.__enter__.assert_called_once()
        mock_client.__exit__.assert_called_once()

    def test_rank_issue_impl_before(self, mock_client):
        """Test ranking issue before another."""
        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _rank_issue_impl(["PROJ-1"], before_key="PROJ-2")

        assert result["ranked"] == 1
        mock_client.rank_issues.assert_called_once_with(
            ["PROJ-1"], rank_before="PROJ-2"
        )

    def test_rank_issue_impl_after(self, mock_client):
        """Test ranking issue after another."""
        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _rank_issue_impl(["PROJ-1"], after_key="PROJ-2")

        assert result["ranked"] == 1
        mock_client.rank_issues.assert_called_once_with(["PROJ-1"], rank_after="PROJ-2")

    def test_rank_issue_impl_no_position(self, mock_client):
        """Test error when no position specified."""
        with pytest.raises(ValidationError, match="Must specify"):
            _rank_issue_impl(["PROJ-1"])

    def test_rank_issue_impl_top_bottom_not_implemented(self, mock_client):
        """Test error for top/bottom (not implemented)."""
        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            with pytest.raises(ValidationError, match="requires implementation"):
                _rank_issue_impl(["PROJ-1"], position="top")


# =============================================================================
# Estimation Implementation Tests
# =============================================================================


class TestEstimationImplementation:
    """Tests for estimation implementation functions."""

    def test_estimate_issue_impl_success(self, mock_client):
        """Test setting story points."""
        with (
            patch(
                "jira_as.cli.commands.agile_cmds.get_jira_client",
                return_value=mock_client,
            ),
            patch(
                "jira_as.cli.commands.agile_cmds.get_agile_field",
                return_value="customfield_10016",
            ),
        ):
            result = _estimate_issue_impl(issue_keys=["PROJ-1"], points=5)

        assert result["updated"] == 1
        assert result["points"] == 5
        mock_client.update_issue.assert_called_once()

    def test_estimate_issue_impl_fibonacci_valid(self, mock_client):
        """Test valid Fibonacci value."""
        with (
            patch(
                "jira_as.cli.commands.agile_cmds.get_jira_client",
                return_value=mock_client,
            ),
            patch(
                "jira_as.cli.commands.agile_cmds.get_agile_field",
                return_value="customfield_10016",
            ),
        ):
            result = _estimate_issue_impl(
                issue_keys=["PROJ-1"], points=8, validate_fibonacci=True
            )

        assert result["updated"] == 1

    def test_estimate_issue_impl_fibonacci_invalid(self):
        """Test invalid Fibonacci value."""
        with pytest.raises(ValidationError, match="not a valid Fibonacci"):
            _estimate_issue_impl(
                issue_keys=["PROJ-1"], points=7, validate_fibonacci=True
            )

    def test_estimate_issue_impl_clear(self, mock_client):
        """Test clearing story points."""
        with (
            patch(
                "jira_as.cli.commands.agile_cmds.get_jira_client",
                return_value=mock_client,
            ),
            patch(
                "jira_as.cli.commands.agile_cmds.get_agile_field",
                return_value="customfield_10016",
            ),
        ):
            _estimate_issue_impl(issue_keys=["PROJ-1"], points=0)

        # Points 0 should set to None
        call_args = mock_client.update_issue.call_args[0]
        assert call_args[1]["customfield_10016"] is None

    def test_get_velocity_impl_success(
        self, mock_client, sample_board, sample_velocity_sprints
    ):
        """Test calculating velocity."""
        mock_client.get_all_boards.return_value = {"values": [sample_board]}
        mock_client.get_board_sprints.return_value = {"values": sample_velocity_sprints}

        # Different points for each sprint
        def mock_search(jql, **kwargs):
            if "sprint = 101" in jql:
                return {"issues": [{"fields": {"customfield_10016": 10}}]}
            elif "sprint = 102" in jql:
                return {"issues": [{"fields": {"customfield_10016": 15}}]}
            else:
                return {"issues": [{"fields": {"customfield_10016": 12}}]}

        mock_client.search_issues.side_effect = mock_search

        with (
            patch(
                "jira_as.cli.commands.agile_cmds.get_jira_client",
                return_value=mock_client,
            ),
            patch(
                "jira_as.cli.commands.agile_cmds.get_agile_fields",
                return_value={"story_points": "customfield_10016"},
            ),
        ):
            result = _get_velocity_impl(project_key="PROJ", num_sprints=3)

        assert result["sprints_analyzed"] == 3
        assert result["total_points"] == 37  # 10 + 15 + 12
        assert result["average_velocity"] == round((10 + 15 + 12) / 3, 1)

    def test_create_subtask_impl_success(self, mock_client):
        """Test creating subtask."""
        mock_client.get_issue.return_value = {
            "key": "PROJ-1",
            "fields": {
                "project": {"key": "PROJ"},
                "issuetype": {"subtask": False},
            },
        }
        mock_client.get.return_value = [
            {"name": "Sub-task", "subtask": True},
            {"name": "Story", "subtask": False},
        ]
        mock_client.create_issue.return_value = {
            "key": "PROJ-10",
            "self": "https://test.atlassian.net/rest/api/3/issue/10",
        }

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            result = _create_subtask_impl(parent_key="PROJ-1", summary="Subtask")

        assert result["key"] == "PROJ-10"
        mock_client.create_issue.assert_called_once()

    def test_create_subtask_impl_parent_is_subtask(self, mock_client):
        """Test error when parent is subtask."""
        mock_client.get_issue.return_value = {
            "key": "PROJ-1",
            "fields": {
                "project": {"key": "PROJ"},
                "issuetype": {"subtask": True},
            },
        }

        with patch(
            "jira_as.cli.commands.agile_cmds.get_jira_client",
            return_value=mock_client,
        ):
            with pytest.raises(ValidationError, match="cannot have subtasks"):
                _create_subtask_impl(parent_key="PROJ-1", summary="Subtask")


# =============================================================================
# Formatting Function Tests
# =============================================================================


class TestFormattingFunctions:
    """Tests for formatting functions."""

    def test_format_epic_details(self, sample_epic):
        """Test formatting epic details."""
        epic_data = {
            "key": sample_epic["key"],
            "fields": sample_epic["fields"],
            "_agile_fields": {"epic_name": "customfield_10011"},
        }
        output = _format_epic_details(epic_data)

        assert "PROJ-100" in output
        assert "Epic Summary" in output
        assert "Epic Name Value" in output
        assert "To Do" in output

    def test_format_epic_details_with_progress(self, sample_epic):
        """Test formatting epic with progress."""
        epic_data = {
            "key": sample_epic["key"],
            "fields": sample_epic["fields"],
            "_agile_fields": {"epic_name": "customfield_10011"},
            "progress": {"total": 10, "done": 5, "percentage": 50},
            "story_points": {"total": 40, "done": 20, "percentage": 50},
            "children": [
                {
                    "key": "PROJ-1",
                    "fields": {"summary": "Child 1", "status": {"name": "Done"}},
                },
            ],
        }
        output = _format_epic_details(epic_data)

        assert "5/10 issues (50%)" in output
        assert "20/40 (50%)" in output
        assert "Children:" in output
        assert "PROJ-1" in output

    def test_format_sprint_details(self, sample_sprint):
        """Test formatting sprint details."""
        sprint_data = {
            **sample_sprint,
            "_story_points_field": "customfield_10016",
        }
        output = _format_sprint_details(sprint_data)

        assert "Sprint 1" in output
        assert "active" in output
        assert "Complete feature X" in output

    def test_format_sprint_details_with_issues(self, sample_sprint, sample_issues):
        """Test formatting sprint with issues."""
        sprint_data = {
            **sample_sprint,
            "_story_points_field": "customfield_10016",
            "issues": sample_issues,
            "progress": {"total": 3, "done": 1, "percentage": 33},
            "story_points": {"total": 16, "done": 3, "percentage": 19},
        }
        output = _format_sprint_details(sprint_data)

        assert "Issues:" in output
        assert "PROJ-1" in output
        assert "1/3 issues (33%)" in output

    def test_format_velocity(self):
        """Test formatting velocity report."""
        data = {
            "project_key": "PROJ",
            "board_id": 123,
            "sprints_analyzed": 3,
            "average_velocity": 12.3,
            "velocity_stdev": 2.5,
            "min_velocity": 10,
            "max_velocity": 15,
            "total_points": 37,
            "sprints": [
                {
                    "sprint_name": "Sprint 1",
                    "completed_points": 10,
                    "completed_issues": 5,
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-14",
                },
            ],
        }
        output = _format_velocity(data)

        assert "Velocity Report: PROJ" in output
        assert "12.3 points/sprint" in output
        assert "10 - 15 points" in output
        assert "Sprint 1" in output


# =============================================================================
# CLI Command Tests
# =============================================================================


class TestSprintCommands:
    """Tests for sprint CLI commands."""

    def test_sprint_manage_start(self, generic_workflow):
        result = CliRunner().invoke(
            agile,
            ["sprint", "manage", "-s", "456", "--start", "--transport", "simulation"],
        )
        assert result.exit_code == 0, result.output
        assert generic_workflow.snapshot()["sprints"][0]["state"] == "active"

    def test_sprint_manage_close(self, generic_workflow):
        before = generic_workflow.snapshot()
        runner = CliRunner()
        args = ["sprint", "manage", "-s", "456", "--close", "--transport", "simulation"]
        result = runner.invoke(agile, args)
        assert result.exit_code == 0, result.output
        assert generic_workflow.snapshot() == before
        result = runner.invoke(agile, [*args, "--confirm"])
        assert result.exit_code == 0, result.output
        assert generic_workflow.snapshot()["sprints"][0]["state"] == "closed"

    def test_sprint_move_issues_to_sprint(self, generic_workflow):
        result = CliRunner().invoke(
            agile,
            [
                "sprint",
                "move-issues",
                "--issues",
                "SBX-1",
                "--sprint",
                "456",
                "--transport",
                "simulation",
            ],
        )
        assert result.exit_code == 0, result.output
        assert generic_workflow.snapshot()["issues"][0]["fields"]["sprint"] == 456

    def test_sprint_move_issues_to_backlog(self, generic_workflow):
        result = CliRunner().invoke(
            agile,
            [
                "sprint",
                "move-issues",
                "--issues",
                "SBX-1",
                "--backlog",
                "--transport",
                "simulation",
            ],
        )
        assert result.exit_code == 0, result.output
        assert generic_workflow.snapshot()["issues"][0]["fields"]["sprint"] is None


class TestOtherAgileCommands:
    """Tests for other agile CLI commands."""

    def test_velocity_text(self, generic_workflow):
        result = CliRunner().invoke(
            agile, ["velocity", "--project", "SBX", "--transport", "simulation"]
        )
        assert result.exit_code == 0, result.output
        assert '"average_velocity": 8.0' in result.output


class TestErrorHandling:
    """Tests for error handling in CLI commands."""

    def test_validation_error_handled(self):
        """Test validation error is handled gracefully."""
        runner = CliRunner()
        result = runner.invoke(
            agile,
            ["epic", "create", "-p", "PROJ", "-s", "Summary", "-c", "invalid_color"],
        )

        assert result.exit_code != 0


# =============================================================================
# Board listing, multi-board resolution and backlog fallback
# =============================================================================


class TestBoardResolutionWarning:
    """A project with several boards reports which one was used."""

    def test_multiple_boards_warn(self, mock_client, capsys):
        """The chosen board is named on stderr."""
        mock_client.get_all_boards.return_value = {
            "values": [
                {"id": 1, "name": "Kanban", "type": "kanban"},
                {"id": 2, "name": "Scrum", "type": "scrum"},
            ]
        }

        board = _get_board_for_project("PROJ", client=mock_client)

        # Scrum boards are preferred over the first result.
        assert board["id"] == 2
        err = capsys.readouterr().err
        assert "has 2 boards" in err
        assert "Using board 2" in err

    def test_single_board_does_not_warn(self, mock_client, capsys):
        """One board needs no disambiguation."""
        mock_client.get_all_boards.return_value = {
            "values": [{"id": 1, "name": "Only", "type": "scrum"}]
        }

        board = _get_board_for_project("PROJ", client=mock_client)

        assert board["id"] == 1
        assert capsys.readouterr().err == ""

    def test_no_boards_returns_none(self, mock_client):
        """A project with no boards resolves to None."""
        mock_client.get_all_boards.return_value = {"values": []}

        assert _get_board_for_project("PROJ", client=mock_client) is None


@pytest.fixture
def generic_workflow(tmp_path, monkeypatch):
    from as_engine.simulation import JiraSimulationStore

    from jira_as import engine
    from jira_as.autocomplete_cache import InstanceFieldsCache

    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path))
    seed = JiraSimulationStore().snapshot()
    seed["sprints"] = [
        {"id": 456, "originBoardId": 1, "name": "Sprint 456", "state": "future"},
        {"id": 457, "originBoardId": 1, "name": "Closed", "state": "closed"},
    ]
    seed["issues"][0]["fields"].update(
        {
            "sprint": 457,
            "status": {"name": "Done", "statusCategory": {"key": "done"}},
            "customfield_10016": 8,
        }
    )
    store = JiraSimulationStore(seed)
    surface = engine.create_surface(transport="simulation", store=store)
    monkeypatch.setattr(engine, "create_surface", lambda **_: surface)
    InstanceFieldsCache(tmp_path).write(store.fields)
    return store

"""
Unit tests for fields CLI commands.

Tests cover:
- list: List fields with filters
- create: Create custom fields
- check-project: Check field availability for a project
- configure-agile: Configure Agile field mappings
"""

from copy import deepcopy
from unittest.mock import patch

import pytest

from jira_as import ValidationError
from jira_as.cli.commands.fields_cmds import (
    AGILE_FIELDS,
    AGILE_PATTERNS,
    FIELD_TYPES,
    _add_field_to_screen,
    _find_agile_fields,
    _find_project_screens,
    _format_agile_config,
    _format_fields_list,
    _format_project_fields,
    _list_fields_impl,
    _resolve_issue_type_id,
    fields,
)

# =============================================================================
# Constants Tests
# =============================================================================


@pytest.mark.unit
class TestConstants:
    """Tests for module constants."""

    def test_agile_patterns_defined(self):
        """Test that AGILE_PATTERNS is defined."""
        assert len(AGILE_PATTERNS) > 0
        assert "epic" in AGILE_PATTERNS
        assert "sprint" in AGILE_PATTERNS
        assert "story" in AGILE_PATTERNS

    def test_agile_fields_defined(self):
        """Test that AGILE_FIELDS is defined."""
        assert "sprint" in AGILE_FIELDS
        assert "story_points" in AGILE_FIELDS
        assert "epic_link" in AGILE_FIELDS

    def test_field_types_defined(self):
        """Test that FIELD_TYPES is defined with valid types."""
        assert "text" in FIELD_TYPES
        assert "number" in FIELD_TYPES
        assert "select" in FIELD_TYPES
        assert "date" in FIELD_TYPES

        # Each type should have 'type' and 'searcher' keys
        for field_type, config in FIELD_TYPES.items():
            assert "type" in config, f"Missing 'type' for {field_type}"
            assert "searcher" in config, f"Missing 'searcher' for {field_type}"


# =============================================================================
# Helper Function Tests
# =============================================================================


@pytest.mark.unit
class TestFindAgileFields:
    """Tests for the _find_agile_fields helper function."""

    def test_find_agile_fields_all_found(self, mock_jira_client, sample_fields):
        """Test finding all Agile fields."""
        mock_jira_client.get.return_value = deepcopy(sample_fields)

        result = _find_agile_fields(mock_jira_client)

        assert result["story_points"] == "customfield_10001"
        assert result["sprint"] == "customfield_10003"
        mock_jira_client.get.assert_called_once_with("/rest/api/3/field")

    def test_find_agile_fields_none_found(self, mock_jira_client):
        """Test when no Agile fields are found."""
        mock_jira_client.get.return_value = [
            {"id": "customfield_99999", "name": "Some Other Field"}
        ]

        result = _find_agile_fields(mock_jira_client)

        assert result["story_points"] is None
        assert result["epic_link"] is None
        assert result["sprint"] is None


@pytest.mark.unit
class TestFindProjectScreens:
    """Tests for the _find_project_screens helper function."""

    def test_find_project_screens_default(
        self, mock_jira_client, sample_project_classic, sample_screens
    ):
        """Test finding screens when no scheme mappings exist."""
        mock_jira_client.get.side_effect = [
            deepcopy(sample_project_classic),  # Project info
            {"values": []},  # No scheme mappings
            deepcopy(sample_screens),  # All screens
        ]

        result = _find_project_screens(mock_jira_client, "PROJ")

        assert len(result) == 1
        assert result[0]["name"] == "Default Screen"


@pytest.mark.unit
class TestAddFieldToScreen:
    """Tests for the _add_field_to_screen helper function."""

    def test_add_field_to_screen_dry_run(self, mock_jira_client):
        """Test dry-run mode returns True without making changes."""
        result = _add_field_to_screen(
            mock_jira_client, screen_id=1, field_id="customfield_10001", dry_run=True
        )

        assert result is True
        mock_jira_client.get.assert_not_called()
        mock_jira_client.post.assert_not_called()

    def test_add_field_to_screen_already_present(
        self, mock_jira_client, sample_screen_tabs, sample_screen_fields
    ):
        """Test when field is already on screen."""
        mock_jira_client.get.side_effect = [
            deepcopy(sample_screen_tabs),
            [{"id": "customfield_10001", "name": "Story Points"}],  # Field exists
        ]

        result = _add_field_to_screen(
            mock_jira_client, screen_id=1, field_id="customfield_10001"
        )

        assert result is True
        mock_jira_client.post.assert_not_called()

    def test_add_field_to_screen_success(
        self, mock_jira_client, sample_screen_tabs, sample_screen_fields
    ):
        """Test successfully adding a field to screen."""
        mock_jira_client.get.side_effect = [
            deepcopy(sample_screen_tabs),
            deepcopy(sample_screen_fields),  # Field not present
        ]

        result = _add_field_to_screen(
            mock_jira_client, screen_id=1, field_id="customfield_10001"
        )

        assert result is True
        mock_jira_client.post.assert_called_once()

    def test_add_field_to_screen_no_tabs(self, mock_jira_client):
        """Test when screen has no tabs."""
        mock_jira_client.get.return_value = []

        result = _add_field_to_screen(
            mock_jira_client, screen_id=1, field_id="customfield_10001"
        )

        assert result is False


# =============================================================================
# List Fields Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestListFieldsImpl:
    """Tests for the _list_fields_impl implementation function."""

    def test_list_fields_custom_only(self, mock_jira_client, sample_fields):
        """Test listing only custom fields (default)."""
        mock_jira_client.get.return_value = deepcopy(sample_fields)

        with patch(
            "jira_as.cli.commands.fields_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _list_fields_impl()

        # Should exclude 'summary' which has custom=False
        assert len(result) == 4
        assert all(f["custom"] for f in result)
        mock_jira_client.__enter__.assert_called_once()
        mock_jira_client.__exit__.assert_called_once()

    def test_list_fields_all(self, mock_jira_client, sample_fields):
        """Test listing all fields including system fields."""
        mock_jira_client.get.return_value = deepcopy(sample_fields)

        with patch(
            "jira_as.cli.commands.fields_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _list_fields_impl(custom_only=False)

        assert len(result) == 5

    def test_list_fields_with_filter(self, mock_jira_client, sample_fields):
        """Test listing fields with name filter."""
        mock_jira_client.get.return_value = deepcopy(sample_fields)

        with patch(
            "jira_as.cli.commands.fields_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _list_fields_impl(filter_pattern="sprint")

        assert len(result) == 1
        assert result[0]["name"] == "Sprint"

    def test_list_fields_agile_only(self, mock_jira_client, sample_fields):
        """Test listing only Agile-related fields."""
        mock_jira_client.get.return_value = deepcopy(sample_fields)

        with patch(
            "jira_as.cli.commands.fields_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _list_fields_impl(agile_only=True)

        # Story Points, Epic Link, Sprint match agile patterns
        assert len(result) == 3
        names = [f["name"] for f in result]
        assert "Story Points" in names
        assert "Epic Link" in names
        assert "Sprint" in names

    def test_list_fields_empty(self, mock_jira_client):
        """Test listing fields when none match criteria."""
        mock_jira_client.get.return_value = []

        with patch(
            "jira_as.cli.commands.fields_cmds.get_jira_client",
            return_value=mock_jira_client,
        ):
            result = _list_fields_impl()

        assert result == []


# =============================================================================
# Create Field Implementation Tests
# =============================================================================


# =============================================================================
# Check Project Fields Implementation Tests
# =============================================================================


@pytest.mark.unit
class TestCheckProjectFieldsImpl:
    """Tests for the _check_project_fields_impl implementation function."""

    @pytest.fixture
    def sample_issuetypes_meta(self):
        """Sample response from get_create_issue_meta_issuetypes."""
        return {
            "values": [
                {"id": "10001", "name": "Task", "description": "A task"},
                {"id": "10002", "name": "Bug", "description": "A bug"},
            ]
        }

    @pytest.fixture
    def sample_fields_meta_task(self):
        """Sample response from get_create_issue_meta_fields for Task."""
        return {
            "values": [
                {"fieldId": "summary", "name": "Summary", "required": True},
                {"fieldId": "description", "name": "Description", "required": False},
                {
                    "fieldId": "customfield_10001",
                    "name": "Story Points",
                    "required": False,
                },
                {
                    "fieldId": "customfield_10002",
                    "name": "Epic Link",
                    "required": False,
                },
            ]
        }

    @pytest.fixture
    def sample_fields_meta_bug(self):
        """Sample response from get_create_issue_meta_fields for Bug."""
        return {
            "values": [
                {"fieldId": "summary", "name": "Summary", "required": True},
                {"fieldId": "description", "name": "Description", "required": False},
                {"fieldId": "priority", "name": "Priority", "required": True},
            ]
        }


# =============================================================================
# Configure Agile Fields Implementation Tests
# =============================================================================


# =============================================================================
# Formatting Function Tests
# =============================================================================


@pytest.mark.unit
class TestFormatFieldsList:
    """Tests for the _format_fields_list formatting function."""

    def test_format_fields_list_empty(self):
        """Test formatting empty field list."""
        result = _format_fields_list([])
        assert "No fields found" in result

    def test_format_fields_list_with_fields(self):
        """Test formatting field list with data."""
        fields = [
            {"id": "customfield_10001", "name": "Story Points", "type": "number"},
            {"id": "customfield_10002", "name": "Epic Link", "type": "string"},
        ]

        result = _format_fields_list(fields)

        assert "Found 2 field(s)" in result
        assert "Story Points" in result
        assert "Epic Link" in result
        assert "customfield_10001" in result


@pytest.mark.unit
class TestFormatProjectFields:
    """Tests for the _format_project_fields formatting function."""

    def test_format_project_fields_basic(self):
        """Test formatting project fields without Agile check."""
        data = {
            "project": {
                "key": "PROJ",
                "name": "Test Project",
                "project_type": "software",
            },
            "is_team_managed": False,
            "issue_types": [
                {"name": "Task", "fields": [{"id": "summary"}]},
                {"name": "Bug", "fields": [{"id": "summary"}, {"id": "priority"}]},
            ],
        }

        result = _format_project_fields(data, check_agile=False)

        assert "Project: PROJ" in result
        assert "Test Project" in result
        assert "Issue Types: 2" in result

    def test_format_project_fields_with_agile(self):
        """Test formatting project fields with Agile check."""
        data = {
            "project": {
                "key": "PROJ",
                "name": "Test Project",
                "project_type": "software",
            },
            "is_team_managed": False,
            "issue_types": [],
            "agile_fields": {
                "story_points": {"id": "customfield_10001", "name": "Story Points"},
                "epic_link": None,
            },
        }

        result = _format_project_fields(data, check_agile=True)

        assert "Agile Field Availability" in result
        assert "story_points" in result


@pytest.mark.unit
class TestFormatAgileConfig:
    """Tests for the _format_agile_config formatting function."""

    def test_format_agile_config_dry_run(self):
        """Test formatting Agile config in dry-run mode."""
        data = {
            "project": "PROJ",
            "dry_run": True,
            "fields_found": {"story_points": "customfield_10001"},
            "screens_found": ["Default Screen"],
            "fields_added": [
                {
                    "field": "story_points",
                    "field_id": "customfield_10001",
                    "screen": "Default Screen",
                }
            ],
        }

        result = _format_agile_config(data)

        assert "[DRY RUN]" in result
        assert "Project: PROJ" in result
        assert "Would add" in result

    def test_format_agile_config_applied(self):
        """Test formatting Agile config when changes are applied."""
        data = {
            "project": "PROJ",
            "dry_run": False,
            "fields_found": {"story_points": "customfield_10001"},
            "screens_found": ["Default Screen"],
            "fields_added": [
                {
                    "field": "story_points",
                    "field_id": "customfield_10001",
                    "screen": "Default Screen",
                }
            ],
        }

        result = _format_agile_config(data)

        assert "[DRY RUN]" not in result
        assert "Added fields:" in result
        assert "configured successfully" in result


# =============================================================================
# CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestFieldsListCommand:
    """Tests for the fields list CLI command."""

    def test_fields_list_cli(self, generic_workflow, cli_runner):
        result = cli_runner.invoke(fields, ["list"])
        assert result.exit_code == 0, result.output
        assert "Found 2 field(s)" in result.output
        assert "Notes" in result.output
        assert generic_workflow.calls == []

    def test_fields_list_cli_json(self, generic_workflow, cli_runner):
        import json

        result = cli_runner.invoke(fields, ["list", "--output", "json"])
        assert result.exit_code == 0, result.output
        assert {row["id"] for row in json.loads(result.output)} == {
            "customfield_10010",
            "customfield_10016",
        }
        assert generic_workflow.calls == []

    def test_fields_list_cli_agile(self, generic_workflow, cli_runner):
        result = cli_runner.invoke(fields, ["list", "--agile"])
        assert result.exit_code == 0, result.output
        assert "Story Points" in result.output and "Notes" not in result.output
        assert generic_workflow.calls == []


# =============================================================================
# Project- and issue-type-scoped field listing
# =============================================================================


@pytest.mark.unit
class TestListFieldsScoping:
    """'fields list --project/--issue-type' reads the create screen."""

    @staticmethod
    def _meta_client(mock_jira_client):
        mock_jira_client.get_create_issue_meta_issuetypes.return_value = {
            "issueTypes": [
                {"id": "10001", "name": "Bug"},
                {"id": "10002", "name": "Task"},
            ]
        }
        mock_jira_client.get_create_issue_meta_fields.side_effect = [
            {
                "fields": [
                    {
                        "fieldId": "customfield_10050",
                        "name": "Root Cause",
                        "custom": True,
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ]
            },
            {
                "fields": [
                    {
                        "fieldId": "customfield_10051",
                        "name": "Team",
                        "custom": True,
                        "required": False,
                        "schema": {"type": "option"},
                    }
                ]
            },
        ]
        return mock_jira_client

    def test_without_project_lists_the_whole_catalogue(self, mock_jira_client):
        """No --project keeps the previous instance-wide behaviour."""
        mock_jira_client.get.return_value = [
            {"id": "customfield_1", "name": "A", "custom": True, "schema": {}}
        ]

        result = _list_fields_impl(client=mock_jira_client)

        mock_jira_client.get.assert_called_once_with("/rest/api/3/field")
        assert [f["id"] for f in result] == ["customfield_1"]

    def test_project_scope_uses_create_meta(self, mock_jira_client):
        """--project reads the create screen, not the field catalogue."""
        client = self._meta_client(mock_jira_client)

        result = _list_fields_impl(project="PROJ", client=client)

        client.get.assert_not_called()
        assert {f["id"] for f in result} == {
            "customfield_10050",
            "customfield_10051",
        }

    def test_issue_type_scope_queries_one_type(self, mock_jira_client):
        """--issue-type narrows to a single type's fields."""
        client = self._meta_client(mock_jira_client)

        result = _list_fields_impl(project="PROJ", issue_type="Bug", client=client)

        assert client.get_create_issue_meta_fields.call_count == 1
        assert client.get_create_issue_meta_fields.call_args[0][1] == "10001"
        assert [f["id"] for f in result] == ["customfield_10050"]
        assert result[0]["required"] is True

    def test_issue_type_requires_project(self, mock_jira_client):
        """--issue-type on its own is rejected."""
        with pytest.raises(ValidationError, match="requires --project"):
            _list_fields_impl(issue_type="Bug", client=mock_jira_client)

    def test_unknown_issue_type_lists_the_alternatives(self, mock_jira_client):
        """A bad issue type names what is available."""
        client = self._meta_client(mock_jira_client)

        with pytest.raises(ValidationError, match="Available: Bug, Task"):
            _list_fields_impl(project="PROJ", issue_type="Nope", client=client)

    def test_issue_type_resolves_by_id(self, mock_jira_client):
        """An ID works as well as a name."""
        client = self._meta_client(mock_jira_client)

        assert _resolve_issue_type_id(client, "PROJ", "10002") == ("10002", "Task")

    def test_field_on_several_types_is_listed_once(self, mock_jira_client):
        """A shared field is deduplicated and records its issue types."""
        mock_jira_client.get_create_issue_meta_issuetypes.return_value = {
            "issueTypes": [
                {"id": "10001", "name": "Bug"},
                {"id": "10002", "name": "Task"},
            ]
        }
        shared = {
            "fieldId": "customfield_10050",
            "name": "Team",
            "custom": True,
            "schema": {"type": "option"},
        }
        mock_jira_client.get_create_issue_meta_fields.side_effect = [
            {"fields": [shared]},
            {"fields": [shared]},
        ]

        result = _list_fields_impl(project="PROJ", client=mock_jira_client)

        assert len(result) == 1
        assert result[0]["issue_types"] == ["Bug", "Task"]


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
        {"sprint": 457, "status": {"name": "Done"}, "customfield_10016": 8}
    )
    store = JiraSimulationStore(seed)
    surface = engine.create_surface(transport="simulation", store=store)
    monkeypatch.setattr(engine, "create_surface", lambda **_: surface)
    InstanceFieldsCache(tmp_path).write(store.fields)
    return store

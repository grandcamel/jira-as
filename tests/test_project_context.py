"""Tests for project_context module."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from jira_as.project_context import (
    ProjectContext,
    _deep_merge,
    clear_context_cache,
    format_context_summary,
    get_common_labels,
    get_defaults_for_issue_type,
    get_project_context,
    get_statuses_for_issue_type,
    get_valid_transitions,
    has_project_context,
    load_json_file,
    merge_contexts,
    suggest_assignee,
    validate_transition,
)


class TestProjectContext:
    """Tests for ProjectContext dataclass."""

    def test_default_values(self):
        """Test default values for ProjectContext."""
        ctx = ProjectContext(project_key="PROJ")
        assert ctx.project_key == "PROJ"
        assert ctx.metadata == {}
        assert ctx.workflows == {}
        assert ctx.patterns == {}
        assert ctx.defaults == {}
        assert ctx.source == "none"
        assert ctx.discovered_at is None

    def test_has_context_empty(self):
        """Test has_context returns False when empty."""
        ctx = ProjectContext(project_key="PROJ")
        assert ctx.has_context() is False

    def test_has_context_with_metadata(self):
        """Test has_context returns True with metadata."""
        ctx = ProjectContext(project_key="PROJ", metadata={"issue_types": []})
        assert ctx.has_context() is True

    def test_has_context_with_workflows(self):
        """Test has_context returns True with workflows."""
        ctx = ProjectContext(project_key="PROJ", workflows={"by_issue_type": {}})
        assert ctx.has_context() is True

    def test_get_issue_types(self):
        """Test get_issue_types returns issue types."""
        ctx = ProjectContext(
            project_key="PROJ",
            metadata={"issue_types": [{"id": "1", "name": "Bug"}]},
        )
        types = ctx.get_issue_types()
        assert len(types) == 1
        assert types[0]["name"] == "Bug"

    def test_get_issue_types_empty(self):
        """Test get_issue_types returns empty list when not set."""
        ctx = ProjectContext(project_key="PROJ")
        assert ctx.get_issue_types() == []

    def test_get_components(self):
        """Test get_components returns components."""
        ctx = ProjectContext(
            project_key="PROJ",
            metadata={"components": [{"id": "1", "name": "Backend"}]},
        )
        comps = ctx.get_components()
        assert len(comps) == 1
        assert comps[0]["name"] == "Backend"

    def test_get_versions(self):
        """Test get_versions returns versions."""
        ctx = ProjectContext(
            project_key="PROJ",
            metadata={"versions": [{"id": "1", "name": "1.0.0"}]},
        )
        versions = ctx.get_versions()
        assert len(versions) == 1
        assert versions[0]["name"] == "1.0.0"

    def test_get_priorities(self):
        """Test get_priorities returns priorities."""
        ctx = ProjectContext(
            project_key="PROJ",
            metadata={"priorities": [{"id": "1", "name": "High"}]},
        )
        priorities = ctx.get_priorities()
        assert len(priorities) == 1
        assert priorities[0]["name"] == "High"

    def test_get_assignable_users(self):
        """Test get_assignable_users returns users."""
        ctx = ProjectContext(
            project_key="PROJ",
            metadata={"assignable_users": [{"accountId": "abc", "displayName": "John"}]},
        )
        users = ctx.get_assignable_users()
        assert len(users) == 1
        assert users[0]["displayName"] == "John"


class TestLoadJsonFile:
    """Tests for load_json_file function."""

    def test_load_existing_file(self, tmp_path):
        """Test loading an existing JSON file."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        result = load_json_file(json_file)
        assert result == {"key": "value"}

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading a non-existent file returns None."""
        result = load_json_file(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns None."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")

        result = load_json_file(json_file)
        assert result is None


class TestMergeContexts:
    """Tests for merge_contexts function."""

    def test_both_none(self):
        """Test merge with both contexts None."""
        merged, source = merge_contexts(None, None)
        assert merged == {}
        assert source == "none"

    def test_only_skill(self):
        """Test merge with only skill context."""
        skill = {"metadata": {"key": "value"}}
        merged, source = merge_contexts(skill, None)
        assert merged == skill
        assert source == "skill"

    def test_only_settings(self):
        """Test merge with only settings context."""
        settings = {"defaults": {"priority": "High"}}
        merged, source = merge_contexts(None, settings)
        assert merged == settings
        assert source == "settings"

    def test_both_contexts_merge(self):
        """Test merging both contexts."""
        skill = {"metadata": {"a": 1}, "defaults": {"b": 2}}
        settings = {"defaults": {"b": 3, "c": 4}}
        merged, source = merge_contexts(skill, settings)
        assert merged["metadata"] == {"a": 1}
        assert merged["defaults"]["b"] == 3  # Settings override
        assert merged["defaults"]["c"] == 4
        assert source == "merged"


class TestDeepMerge:
    """Tests for _deep_merge function."""

    def test_simple_merge(self):
        """Test simple dict merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test nested dict merge."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}
        result = _deep_merge(base, override)
        assert result["outer"] == {"a": 1, "b": 3, "c": 4}

    def test_base_not_modified(self):
        """Test that base dict is not modified."""
        base = {"a": 1}
        override = {"a": 2}
        _deep_merge(base, override)
        assert base == {"a": 1}


class TestGetDefaultsForIssueType:
    """Tests for get_defaults_for_issue_type function."""

    def test_empty_defaults(self):
        """Test with no defaults configured."""
        ctx = ProjectContext(project_key="PROJ")
        result = get_defaults_for_issue_type(ctx, "Bug")
        assert result == {}

    def test_global_defaults_only(self):
        """Test with only global defaults."""
        ctx = ProjectContext(
            project_key="PROJ",
            defaults={"global": {"priority": "Medium", "labels": ["test"]}},
        )
        result = get_defaults_for_issue_type(ctx, "Bug")
        assert result["priority"] == "Medium"
        assert result["labels"] == ["test"]

    def test_issue_type_defaults_override(self):
        """Test issue type defaults override global."""
        ctx = ProjectContext(
            project_key="PROJ",
            defaults={
                "global": {"priority": "Medium"},
                "by_issue_type": {"Bug": {"priority": "High"}},
            },
        )
        result = get_defaults_for_issue_type(ctx, "Bug")
        assert result["priority"] == "High"

    def test_labels_merge(self):
        """Test labels are merged between global and type-specific."""
        ctx = ProjectContext(
            project_key="PROJ",
            defaults={
                "global": {"labels": ["global-label"]},
                "by_issue_type": {"Bug": {"labels": ["bug-label"]}},
            },
        )
        result = get_defaults_for_issue_type(ctx, "Bug")
        assert set(result["labels"]) == {"global-label", "bug-label"}

    def test_components_merge(self):
        """Test components are merged between global and type-specific."""
        ctx = ProjectContext(
            project_key="PROJ",
            defaults={
                "global": {"components": ["Backend"]},
                "by_issue_type": {"Bug": {"components": ["Frontend"]}},
            },
        )
        result = get_defaults_for_issue_type(ctx, "Bug")
        assert set(result["components"]) == {"Backend", "Frontend"}


class TestGetValidTransitions:
    """Tests for get_valid_transitions function."""

    def test_no_workflows(self):
        """Test with no workflows configured."""
        ctx = ProjectContext(project_key="PROJ")
        result = get_valid_transitions(ctx, "Bug", "Open")
        assert result == []

    def test_with_transitions(self):
        """Test with transitions configured."""
        ctx = ProjectContext(
            project_key="PROJ",
            workflows={
                "by_issue_type": {
                    "Bug": {
                        "transitions": {
                            "Open": [
                                {"id": "1", "name": "Start", "to_status": "In Progress"}
                            ]
                        }
                    }
                }
            },
        )
        result = get_valid_transitions(ctx, "Bug", "Open")
        assert len(result) == 1
        assert result[0]["name"] == "Start"


class TestGetStatusesForIssueType:
    """Tests for get_statuses_for_issue_type function."""

    def test_no_workflows(self):
        """Test with no workflows configured."""
        ctx = ProjectContext(project_key="PROJ")
        result = get_statuses_for_issue_type(ctx, "Bug")
        assert result == []

    def test_with_statuses(self):
        """Test with statuses configured."""
        ctx = ProjectContext(
            project_key="PROJ",
            workflows={
                "by_issue_type": {
                    "Bug": {
                        "statuses": [
                            {"id": "1", "name": "Open", "category": "To Do"}
                        ]
                    }
                }
            },
        )
        result = get_statuses_for_issue_type(ctx, "Bug")
        assert len(result) == 1
        assert result[0]["name"] == "Open"


class TestSuggestAssignee:
    """Tests for suggest_assignee function."""

    def test_no_patterns(self):
        """Test with no patterns configured."""
        ctx = ProjectContext(project_key="PROJ")
        result = suggest_assignee(ctx)
        assert result is None

    def test_with_top_assignees(self):
        """Test with top assignees in patterns."""
        ctx = ProjectContext(
            project_key="PROJ",
            patterns={
                "top_assignees": [
                    {"account_id": "abc123", "display_name": "John"}
                ]
            },
        )
        result = suggest_assignee(ctx)
        assert result == "abc123"

    def test_with_issue_type_assignees(self):
        """Test with issue type specific assignees."""
        ctx = ProjectContext(
            project_key="PROJ",
            patterns={
                "by_issue_type": {
                    "Bug": {
                        "assignees": {
                            "abc123": {"count": 10},
                            "def456": {"count": 5},
                        }
                    }
                }
            },
        )
        result = suggest_assignee(ctx, issue_type="Bug")
        assert result == "abc123"


class TestGetCommonLabels:
    """Tests for get_common_labels function."""

    def test_no_patterns(self):
        """Test with no patterns configured."""
        ctx = ProjectContext(project_key="PROJ")
        result = get_common_labels(ctx)
        assert result == []

    def test_with_issue_type_labels(self):
        """Test with issue type specific labels."""
        ctx = ProjectContext(
            project_key="PROJ",
            patterns={
                "by_issue_type": {
                    "Bug": {"labels": {"bug": 10, "urgent": 5}}
                }
            },
        )
        result = get_common_labels(ctx, issue_type="Bug")
        assert result == ["bug", "urgent"]

    def test_limit(self):
        """Test label limit."""
        ctx = ProjectContext(
            project_key="PROJ",
            patterns={
                "by_issue_type": {
                    "Bug": {"labels": {"a": 10, "b": 8, "c": 6, "d": 4}}
                }
            },
        )
        result = get_common_labels(ctx, issue_type="Bug", limit=2)
        assert len(result) == 2


class TestValidateTransition:
    """Tests for validate_transition function."""

    def test_valid_transition(self):
        """Test validating a valid transition."""
        ctx = ProjectContext(
            project_key="PROJ",
            workflows={
                "by_issue_type": {
                    "Bug": {
                        "transitions": {
                            "Open": [{"to_status": "In Progress"}]
                        }
                    }
                }
            },
        )
        assert validate_transition(ctx, "Bug", "Open", "In Progress") is True

    def test_invalid_transition(self):
        """Test validating an invalid transition."""
        ctx = ProjectContext(project_key="PROJ")
        assert validate_transition(ctx, "Bug", "Open", "Done") is False


class TestFormatContextSummary:
    """Tests for format_context_summary function."""

    def test_minimal_context(self):
        """Test formatting minimal context."""
        ctx = ProjectContext(project_key="PROJ", source="none")
        summary = format_context_summary(ctx)
        assert "Project: PROJ" in summary
        assert "Source: none" in summary

    def test_with_discovered_at(self):
        """Test formatting with discovered_at."""
        ctx = ProjectContext(
            project_key="PROJ",
            source="skill",
            discovered_at="2025-01-15T10:00:00Z",
        )
        summary = format_context_summary(ctx)
        assert "Discovered: 2025-01-15" in summary

    def test_with_issue_types(self):
        """Test formatting with issue types."""
        ctx = ProjectContext(
            project_key="PROJ",
            metadata={"issue_types": [{"name": "Bug"}, {"name": "Story"}]},
        )
        summary = format_context_summary(ctx)
        assert "Issue Types: Bug, Story" in summary

    def test_with_components(self):
        """Test formatting with components."""
        ctx = ProjectContext(
            project_key="PROJ",
            metadata={"components": [{"name": "Backend"}, {"name": "Frontend"}]},
        )
        summary = format_context_summary(ctx)
        assert "Components: Backend, Frontend" in summary


class TestClearContextCache:
    """Tests for clear_context_cache function."""

    def test_clear_all(self):
        """Test clearing all cached contexts."""
        # Ensure cache is populated
        import jira_as.project_context as pc

        pc._context_cache["PROJ1"] = ProjectContext(project_key="PROJ1")
        pc._context_cache["PROJ2"] = ProjectContext(project_key="PROJ2")

        clear_context_cache()

        assert len(pc._context_cache) == 0

    def test_clear_specific(self):
        """Test clearing specific project cache."""
        import jira_as.project_context as pc

        pc._context_cache["PROJ1"] = ProjectContext(project_key="PROJ1")
        pc._context_cache["PROJ2"] = ProjectContext(project_key="PROJ2")

        clear_context_cache("PROJ1")

        assert "PROJ1" not in pc._context_cache
        assert "PROJ2" in pc._context_cache

        # Clean up
        clear_context_cache()


class TestHasProjectContext:
    """Tests for has_project_context function."""

    @patch("jira_as.project_context.get_project_skill_path")
    @patch("jira_as.project_context.load_settings_context")
    def test_no_context(self, mock_settings, mock_skill_path):
        """Test when no context exists."""
        mock_path = Path("/nonexistent")
        mock_skill_path.return_value = mock_path
        mock_settings.return_value = None

        result = has_project_context("PROJ")
        assert result is False

    @patch("jira_as.project_context.get_project_skill_path")
    def test_skill_path_exists(self, mock_skill_path, tmp_path):
        """Test when skill path exists."""
        skill_dir = tmp_path / "jira-project-PROJ"
        skill_dir.mkdir()
        mock_skill_path.return_value = skill_dir

        result = has_project_context("PROJ")
        assert result is True

    @patch("jira_as.project_context.get_project_skill_path")
    @patch("jira_as.project_context.load_settings_context")
    def test_settings_exists(self, mock_settings, mock_skill_path):
        """Test when settings context exists."""
        mock_skill_path.return_value = Path("/nonexistent")
        mock_settings.return_value = {"defaults": {}}

        result = has_project_context("PROJ")
        assert result is True

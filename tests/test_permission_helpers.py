"""
Tests for permission_helpers module.
"""

import pytest
from assistant_skills_lib.error_handler import ValidationError

from jira_as.permission_helpers import (
    HOLDER_TYPES_WITH_PARAMETER,
    HOLDER_TYPES_WITHOUT_PARAMETER,
    VALID_HOLDER_TYPES,
    build_grant_payload,
    find_grant_by_spec,
    find_scheme_by_name,
    format_grant,
    format_grant_for_export,
    format_scheme_summary,
    get_holder_display,
    group_grants_by_permission,
    parse_grant_string,
    validate_holder_type,
    validate_permission,
)


class TestConstants:
    """Tests for module constants."""

    def test_valid_holder_types_not_empty(self):
        """Test VALID_HOLDER_TYPES is not empty."""
        assert len(VALID_HOLDER_TYPES) > 0

    def test_holder_types_with_parameter(self):
        """Test holder types that require parameters."""
        assert "group" in HOLDER_TYPES_WITH_PARAMETER
        assert "projectRole" in HOLDER_TYPES_WITH_PARAMETER
        assert "user" in HOLDER_TYPES_WITH_PARAMETER
        assert "applicationRole" in HOLDER_TYPES_WITH_PARAMETER

    def test_holder_types_without_parameter(self):
        """Test holder types that don't require parameters."""
        assert "anyone" in HOLDER_TYPES_WITHOUT_PARAMETER
        assert "projectLead" in HOLDER_TYPES_WITHOUT_PARAMETER
        assert "reporter" in HOLDER_TYPES_WITHOUT_PARAMETER
        assert "currentAssignee" in HOLDER_TYPES_WITHOUT_PARAMETER

    def test_holder_types_are_disjoint(self):
        """Test that with/without parameter lists don't overlap."""
        overlap = set(HOLDER_TYPES_WITH_PARAMETER) & set(HOLDER_TYPES_WITHOUT_PARAMETER)
        assert len(overlap) == 0


class TestParseGrantString:
    """Tests for parse_grant_string function."""

    def test_parse_without_parameter(self):
        """Test parsing grant without holder parameter."""
        permission, holder_type, param = parse_grant_string("BROWSE_PROJECTS:anyone")
        assert permission == "BROWSE_PROJECTS"
        assert holder_type == "anyone"
        assert param is None

    def test_parse_with_parameter(self):
        """Test parsing grant with holder parameter."""
        permission, holder_type, param = parse_grant_string(
            "CREATE_ISSUES:group:jira-developers"
        )
        assert permission == "CREATE_ISSUES"
        assert holder_type == "group"
        assert param == "jira-developers"

    def test_parse_lowercase_permission_uppercased(self):
        """Test that permission is uppercased."""
        permission, _, _ = parse_grant_string("browse_projects:anyone")
        assert permission == "BROWSE_PROJECTS"

    def test_parse_with_colons_in_parameter(self):
        """Test parsing when parameter contains colons."""
        permission, holder_type, param = parse_grant_string(
            "EDIT_ISSUES:user:user:with:colons"
        )
        assert permission == "EDIT_ISSUES"
        assert holder_type == "user"
        assert param == "user:with:colons"

    def test_empty_string_raises(self):
        """Test empty string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            parse_grant_string("")
        assert "cannot be empty" in str(exc_info.value)

    def test_missing_holder_type_raises(self):
        """Test missing holder type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            parse_grant_string("BROWSE_PROJECTS")
        assert "Invalid grant format" in str(exc_info.value)

    def test_invalid_holder_type_raises(self):
        """Test invalid holder type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            parse_grant_string("BROWSE_PROJECTS:invalid_type")
        assert "Invalid holder type" in str(exc_info.value)

    def test_missing_required_parameter_raises(self):
        """Test missing required parameter raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            parse_grant_string("CREATE_ISSUES:group")
        assert "requires a parameter" in str(exc_info.value)

    def test_unexpected_parameter_raises(self):
        """Test unexpected parameter raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            parse_grant_string("BROWSE_PROJECTS:anyone:unexpected")
        assert "does not accept a parameter" in str(exc_info.value)


class TestFormatGrant:
    """Tests for format_grant function."""

    def test_format_anyone(self):
        """Test formatting 'anyone' holder type."""
        grant = {"holder": {"type": "anyone"}}
        assert format_grant(grant) == "anyone"

    def test_format_group_with_parameter(self):
        """Test formatting group holder with parameter."""
        grant = {"holder": {"type": "group", "parameter": "jira-developers"}}
        assert format_grant(grant) == "group: jira-developers"

    def test_format_project_role(self):
        """Test formatting projectRole holder."""
        grant = {"holder": {"type": "projectRole", "parameter": "Developers"}}
        assert format_grant(grant) == "projectRole: Developers"

    def test_format_unknown_type(self):
        """Test formatting unknown holder type."""
        grant = {"holder": {"type": "customType"}}
        assert format_grant(grant) == "customType"

    def test_format_empty_holder(self):
        """Test formatting grant with empty holder."""
        grant = {"holder": {}}
        assert format_grant(grant) == "unknown"


class TestFormatGrantForExport:
    """Tests for format_grant_for_export function."""

    def test_export_without_parameter(self):
        """Test export format without parameter."""
        grant = {"permission": "BROWSE_PROJECTS", "holder": {"type": "anyone"}}
        assert format_grant_for_export(grant) == "BROWSE_PROJECTS:anyone"

    def test_export_with_parameter(self):
        """Test export format with parameter."""
        grant = {
            "permission": "CREATE_ISSUES",
            "holder": {"type": "group", "parameter": "jira-devs"},
        }
        assert format_grant_for_export(grant) == "CREATE_ISSUES:group:jira-devs"

    def test_export_missing_permission(self):
        """Test export with missing permission uses UNKNOWN."""
        grant = {"holder": {"type": "anyone"}}
        assert format_grant_for_export(grant) == "UNKNOWN:anyone"


class TestBuildGrantPayload:
    """Tests for build_grant_payload function."""

    def test_build_without_parameter(self):
        """Test building payload without parameter."""
        payload = build_grant_payload("BROWSE_PROJECTS", "anyone")
        assert payload == {
            "permission": "BROWSE_PROJECTS",
            "holder": {"type": "anyone"},
        }

    def test_build_with_parameter(self):
        """Test building payload with parameter."""
        payload = build_grant_payload("CREATE_ISSUES", "group", "jira-developers")
        assert payload == {
            "permission": "CREATE_ISSUES",
            "holder": {"type": "group", "parameter": "jira-developers"},
        }


class TestValidatePermission:
    """Tests for validate_permission function."""

    def test_valid_permission(self):
        """Test valid permission returns True."""
        permissions = {"BROWSE_PROJECTS": {}, "CREATE_ISSUES": {}}
        assert validate_permission("BROWSE_PROJECTS", permissions) is True

    def test_valid_permission_case_insensitive(self):
        """Test validation is case-insensitive."""
        permissions = {"BROWSE_PROJECTS": {}}
        assert validate_permission("browse_projects", permissions) is True

    def test_invalid_permission_raises(self):
        """Test invalid permission raises ValidationError."""
        permissions = {"BROWSE_PROJECTS": {}, "CREATE_ISSUES": {}}
        with pytest.raises(ValidationError) as exc_info:
            validate_permission("INVALID_PERM", permissions)
        assert "Invalid permission key" in str(exc_info.value)

    def test_invalid_permission_suggests_similar(self):
        """Test invalid permission suggests similar ones."""
        permissions = {"BROWSE_PROJECTS": {}, "BROWSE_ISSUES": {}}
        with pytest.raises(ValidationError) as exc_info:
            validate_permission("BROWSE", permissions)
        # Should suggest matches containing "BROWSE"
        assert "BROWSE" in str(exc_info.value)


class TestValidateHolderType:
    """Tests for validate_holder_type function."""

    def test_valid_holder_type(self):
        """Test valid holder type returns True."""
        assert validate_holder_type("anyone") is True
        assert validate_holder_type("group") is True

    def test_invalid_holder_type_raises(self):
        """Test invalid holder type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_holder_type("invalid")
        assert "Invalid holder type" in str(exc_info.value)
        assert "Valid types" in str(exc_info.value)


class TestFindSchemeByName:
    """Tests for find_scheme_by_name function."""

    def test_find_exact_match(self):
        """Test finding scheme by exact name."""
        schemes = [
            {"name": "Default Scheme"},
            {"name": "Custom Scheme"},
        ]
        result = find_scheme_by_name(schemes, "Default Scheme")
        assert result["name"] == "Default Scheme"

    def test_find_case_insensitive(self):
        """Test case-insensitive matching."""
        schemes = [{"name": "Default Scheme"}]
        result = find_scheme_by_name(schemes, "default scheme")
        assert result["name"] == "Default Scheme"

    def test_fuzzy_match_disabled(self):
        """Test fuzzy matching disabled returns None for partial."""
        schemes = [{"name": "Default Scheme"}]
        result = find_scheme_by_name(schemes, "Default", fuzzy=False)
        assert result is None

    def test_not_found_returns_none(self):
        """Test not found returns None."""
        schemes = [{"name": "Default Scheme"}]
        result = find_scheme_by_name(schemes, "Nonexistent")
        assert result is None


class TestGroupGrantsByPermission:
    """Tests for group_grants_by_permission function."""

    def test_group_grants(self):
        """Test grouping grants by permission."""
        grants = [
            {"permission": "BROWSE_PROJECTS", "holder": {"type": "anyone"}},
            {
                "permission": "CREATE_ISSUES",
                "holder": {"type": "group", "parameter": "dev"},
            },
            {
                "permission": "BROWSE_PROJECTS",
                "holder": {"type": "group", "parameter": "users"},
            },
        ]
        grouped = group_grants_by_permission(grants)

        assert len(grouped["BROWSE_PROJECTS"]) == 2
        assert len(grouped["CREATE_ISSUES"]) == 1

    def test_empty_grants(self):
        """Test grouping empty grants list."""
        grouped = group_grants_by_permission([])
        assert grouped == {}


class TestFindGrantBySpec:
    """Tests for find_grant_by_spec function."""

    def test_find_without_parameter(self):
        """Test finding grant without holder parameter."""
        grants = [
            {"permission": "BROWSE_PROJECTS", "holder": {"type": "anyone"}},
            {
                "permission": "CREATE_ISSUES",
                "holder": {"type": "group", "parameter": "dev"},
            },
        ]
        result = find_grant_by_spec(grants, "BROWSE_PROJECTS", "anyone")
        assert result["permission"] == "BROWSE_PROJECTS"

    def test_find_with_parameter(self):
        """Test finding grant with holder parameter."""
        grants = [
            {
                "permission": "CREATE_ISSUES",
                "holder": {"type": "group", "parameter": "dev"},
            },
            {
                "permission": "CREATE_ISSUES",
                "holder": {"type": "group", "parameter": "users"},
            },
        ]
        result = find_grant_by_spec(grants, "CREATE_ISSUES", "group", "dev")
        assert result["holder"]["parameter"] == "dev"

    def test_find_case_insensitive_permission(self):
        """Test permission matching is case-insensitive."""
        grants = [{"permission": "BROWSE_PROJECTS", "holder": {"type": "anyone"}}]
        result = find_grant_by_spec(grants, "browse_projects", "anyone")
        assert result is not None

    def test_find_case_insensitive_parameter(self):
        """Test parameter matching is case-insensitive."""
        grants = [
            {
                "permission": "CREATE_ISSUES",
                "holder": {"type": "group", "parameter": "Developers"},
            }
        ]
        result = find_grant_by_spec(grants, "CREATE_ISSUES", "group", "developers")
        assert result is not None

    def test_not_found_returns_none(self):
        """Test not found returns None."""
        grants = [{"permission": "BROWSE_PROJECTS", "holder": {"type": "anyone"}}]
        result = find_grant_by_spec(grants, "CREATE_ISSUES", "anyone")
        assert result is None


class TestGetHolderDisplay:
    """Tests for get_holder_display function."""

    def test_anyone(self):
        """Test anyone holder display."""
        assert get_holder_display({"type": "anyone"}) == "anyone"

    def test_project_lead(self):
        """Test projectLead holder display."""
        assert get_holder_display({"type": "projectLead"}) == "project lead"

    def test_reporter(self):
        """Test reporter holder display."""
        assert get_holder_display({"type": "reporter"}) == "reporter"

    def test_current_assignee(self):
        """Test currentAssignee holder display."""
        assert get_holder_display({"type": "currentAssignee"}) == "current assignee"

    def test_group(self):
        """Test group holder display."""
        assert (
            get_holder_display({"type": "group", "parameter": "jira-developers"})
            == "group: jira-developers"
        )

    def test_project_role(self):
        """Test projectRole holder display."""
        assert (
            get_holder_display({"type": "projectRole", "parameter": "Developers"})
            == "role: Developers"
        )

    def test_user(self):
        """Test user holder display."""
        assert (
            get_holder_display({"type": "user", "parameter": "abc123"})
            == "user: abc123"
        )

    def test_application_role(self):
        """Test applicationRole holder display."""
        assert (
            get_holder_display(
                {"type": "applicationRole", "parameter": "jira-software-users"}
            )
            == "app role: jira-software-users"
        )

    def test_unknown_type(self):
        """Test unknown holder type display."""
        assert get_holder_display({"type": "customType"}) == "customType"


class TestFormatSchemeSummary:
    """Tests for format_scheme_summary function."""

    def test_basic_summary(self):
        """Test basic scheme summary."""
        scheme = {
            "id": "10000",
            "name": "Default Permission Scheme",
            "permissions": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        }
        summary = format_scheme_summary(scheme)
        assert "Default Permission Scheme" in summary
        assert "ID: 10000" in summary
        assert "Grants: 3" in summary

    def test_summary_with_description(self):
        """Test summary includes description."""
        scheme = {
            "id": "10000",
            "name": "Custom Scheme",
            "description": "This is a custom permission scheme",
            "permissions": [],
        }
        summary = format_scheme_summary(scheme)
        assert "This is a custom permission scheme" in summary

    def test_summary_truncates_long_description(self):
        """Test summary truncates long descriptions."""
        long_desc = "A" * 100
        scheme = {
            "id": "10000",
            "name": "Scheme",
            "description": long_desc,
            "permissions": [],
        }
        summary = format_scheme_summary(scheme)
        assert "..." in summary
        # Should only show first 80 chars
        assert "A" * 80 in summary

"""
Test that all package imports work correctly.
"""

import pytest


class TestPackageImports:
    """Test that all public exports are importable."""

    def test_version(self):
        """Test version is accessible."""
        from jira_assistant_skills_lib import __version__

        assert __version__ == "0.2.1"

    def test_client_imports(self):
        """Test client classes are importable."""
        from jira_assistant_skills_lib import JiraClient, AutomationClient

        assert JiraClient is not None
        assert AutomationClient is not None

    def test_config_imports(self):
        """Test configuration imports."""
        from jira_assistant_skills_lib import ConfigManager, get_jira_client

        assert ConfigManager is not None
        assert get_jira_client is not None

    def test_error_imports(self):
        """Test error classes are importable."""
        from jira_assistant_skills_lib import (
            JiraError,
            AuthenticationError,
            PermissionError,
            ValidationError,
            NotFoundError,
            RateLimitError,
            ConflictError,
            ServerError,
            handle_jira_error,
            print_error,
            handle_errors,
        )

        assert JiraError is not None
        assert AuthenticationError is not None
        assert ValidationError is not None

    def test_validator_imports(self):
        """Test validator functions are importable."""
        from jira_assistant_skills_lib import (
            validate_issue_key,
            validate_jql,
            validate_project_key,
            validate_file_path,
            validate_url,
            validate_email,
        )

        assert validate_issue_key is not None
        assert validate_jql is not None

    def test_formatter_imports(self):
        """Test formatter functions are importable."""
        from jira_assistant_skills_lib import (
            format_issue,
            format_table,
            format_json,
            export_csv,
            print_success,
            print_warning,
            print_info,
        )

        assert format_issue is not None
        assert format_table is not None

    def test_adf_imports(self):
        """Test ADF helper functions are importable."""
        from jira_assistant_skills_lib import (
            text_to_adf,
            markdown_to_adf,
            adf_to_text,
            wiki_markup_to_adf,
        )

        assert text_to_adf is not None
        assert markdown_to_adf is not None

    def test_time_utils_imports(self):
        """Test time utilities are importable."""
        from jira_assistant_skills_lib import (
            parse_time_string,
            format_seconds,
            parse_relative_date,
            SECONDS_PER_HOUR,
            SECONDS_PER_DAY,
        )

        assert parse_time_string is not None
        assert format_seconds is not None
        assert SECONDS_PER_HOUR == 3600

    def test_cache_imports(self):
        """Test cache classes are importable."""
        from jira_assistant_skills_lib import JiraCache, get_cache

        assert JiraCache is not None
        assert get_cache is not None


class TestValidators:
    """Test validator functions."""

    def test_validate_issue_key_valid(self):
        """Test valid issue key."""
        from jira_assistant_skills_lib import validate_issue_key

        assert validate_issue_key("PROJ-123") == "PROJ-123"
        assert validate_issue_key("proj-123") == "PROJ-123"  # Uppercase normalization
        assert validate_issue_key("ABC123-456") == "ABC123-456"

    def test_validate_issue_key_invalid(self):
        """Test invalid issue key."""
        from jira_assistant_skills_lib import validate_issue_key
        from assistant_skills_lib.error_handler import ValidationError

        with pytest.raises(ValidationError):
            validate_issue_key("")
        with pytest.raises(ValidationError):
            validate_issue_key("invalid")
        with pytest.raises(ValidationError):
            validate_issue_key("123-ABC")

    def test_validate_project_key_valid(self):
        """Test valid project key."""
        from jira_assistant_skills_lib import validate_project_key

        assert validate_project_key("PROJ") == "PROJ"
        assert validate_project_key("proj") == "PROJ"  # Uppercase normalization

    def test_validate_project_key_invalid(self):
        """Test invalid project key."""
        from jira_assistant_skills_lib import validate_project_key
        from assistant_skills_lib.error_handler import ValidationError

        with pytest.raises(ValidationError):
            validate_project_key("")
        with pytest.raises(ValidationError):
            validate_project_key("A")  # Too short

    def test_validate_jql_valid(self):
        """Test valid JQL."""
        from jira_assistant_skills_lib import validate_jql

        assert validate_jql("project = PROJ") == "project = PROJ"
        assert validate_jql("  project = PROJ  ") == "project = PROJ"  # Trim

    def test_validate_jql_invalid(self):
        """Test invalid JQL."""
        from jira_assistant_skills_lib import validate_jql
        from assistant_skills_lib.error_handler import ValidationError

        with pytest.raises(ValidationError):
            validate_jql("")


class TestTimeUtils:
    """Test time utility functions."""

    def test_parse_time_string(self):
        """Test parsing JIRA time strings."""
        from jira_assistant_skills_lib import parse_time_string

        assert parse_time_string("2h") == 7200
        assert parse_time_string("30m") == 1800
        assert parse_time_string("1h 30m") == 5400

    def test_format_seconds(self):
        """Test formatting seconds to JIRA time."""
        from jira_assistant_skills_lib import format_seconds

        assert format_seconds(7200) == "2h"
        assert format_seconds(1800) == "30m"
        assert format_seconds(0) == "0m"


class TestAdfHelper:
    """Test ADF helper functions."""

    def test_text_to_adf(self):
        """Test converting text to ADF."""
        from jira_assistant_skills_lib import text_to_adf

        result = text_to_adf("Hello world")
        assert result["version"] == 1
        assert result["type"] == "doc"
        assert len(result["content"]) == 1

    def test_adf_to_text(self):
        """Test extracting text from ADF."""
        from jira_assistant_skills_lib import adf_to_text, text_to_adf

        adf = text_to_adf("Hello world")
        text = adf_to_text(adf)
        assert "Hello world" in text

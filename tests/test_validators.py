"""
Comprehensive tests for validators module.
"""

import os
import tempfile

import pytest
from assistant_skills_lib.error_handler import ValidationError

from jira_as.validators import (
    PROJECT_TEMPLATES,
    VALID_ASSIGNEE_TYPES,
    VALID_PROJECT_TYPES,
    safe_get_nested,
    validate_assignee_type,
    validate_avatar_file,
    validate_category_name,
    validate_email,
    validate_file_path,
    validate_issue_key,
    validate_jql,
    validate_project_key,
    validate_project_name,
    validate_project_template,
    validate_project_type,
    validate_transition_id,
    validate_url,
)


class TestSafeGetNested:
    """Tests for safe_get_nested function."""

    def test_simple_path(self):
        """Test accessing a simple nested path."""
        obj = {"fields": {"status": {"name": "Open"}}}
        assert safe_get_nested(obj, "fields.status.name") == "Open"

    def test_missing_path_returns_default(self):
        """Test that missing path returns default value."""
        obj = {"fields": {"status": {"name": "Open"}}}
        assert (
            safe_get_nested(obj, "fields.assignee.displayName", "Unassigned")
            == "Unassigned"
        )

    def test_empty_dict_returns_default(self):
        """Test that empty dict returns default."""
        assert safe_get_nested({}, "a.b.c", "default") == "default"

    def test_none_obj_returns_default(self):
        """Test that None object returns default."""
        assert safe_get_nested(None, "a.b", "default") == "default"

    def test_non_dict_obj_returns_default(self):
        """Test that non-dict object returns default."""
        assert safe_get_nested("not a dict", "a.b", "default") == "default"
        assert safe_get_nested(123, "a.b", "default") == "default"
        assert safe_get_nested([], "a.b", "default") == "default"

    def test_partial_path_non_dict(self):
        """Test path that hits non-dict value mid-way."""
        obj = {"fields": "not a dict"}
        assert safe_get_nested(obj, "fields.status.name", "default") == "default"

    def test_none_value_in_path(self):
        """Test path with None value mid-way."""
        obj = {"fields": {"status": None}}
        assert safe_get_nested(obj, "fields.status.name", "default") == "default"

    def test_single_key_path(self):
        """Test single key path (no dots)."""
        obj = {"key": "value"}
        assert safe_get_nested(obj, "key") == "value"

    def test_default_none(self):
        """Test default value is None when not specified."""
        obj = {"a": 1}
        assert safe_get_nested(obj, "missing") is None


class TestValidateIssueKey:
    """Tests for validate_issue_key function."""

    def test_valid_simple(self):
        """Test valid simple issue key."""
        assert validate_issue_key("PROJ-123") == "PROJ-123"

    def test_valid_lowercase_normalized(self):
        """Test lowercase is normalized to uppercase."""
        assert validate_issue_key("proj-123") == "PROJ-123"

    def test_valid_mixed_case(self):
        """Test mixed case is normalized."""
        assert validate_issue_key("PrOj-123") == "PROJ-123"

    def test_valid_alphanumeric_project(self):
        """Test project key with numbers."""
        assert validate_issue_key("ABC123-456") == "ABC123-456"

    def test_valid_single_letter_project(self):
        """Test single letter project key."""
        assert validate_issue_key("A-1") == "A-1"

    def test_valid_long_number(self):
        """Test issue with long number."""
        assert validate_issue_key("PROJ-999999") == "PROJ-999999"

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_issue_key("")

    def test_invalid_none(self):
        """Test None raises error."""
        with pytest.raises(ValidationError):
            validate_issue_key(None)

    def test_invalid_whitespace_only(self):
        """Test whitespace only raises error."""
        with pytest.raises(ValidationError):
            validate_issue_key("   ")

    def test_invalid_no_dash(self):
        """Test missing dash raises error."""
        with pytest.raises(ValidationError):
            validate_issue_key("PROJ123")

    def test_invalid_no_number(self):
        """Test missing number raises error."""
        with pytest.raises(ValidationError):
            validate_issue_key("PROJ-")

    def test_invalid_no_project(self):
        """Test missing project key raises error."""
        with pytest.raises(ValidationError):
            validate_issue_key("-123")

    def test_invalid_starts_with_number(self):
        """Test project starting with number raises error."""
        with pytest.raises(ValidationError):
            validate_issue_key("123-456")

    def test_invalid_special_chars(self):
        """Test special characters raise error."""
        with pytest.raises(ValidationError):
            validate_issue_key("PROJ_123")
        with pytest.raises(ValidationError):
            validate_issue_key("PR@J-123")


class TestValidateProjectKey:
    """Tests for validate_project_key function."""

    def test_valid_simple(self):
        """Test valid simple project key."""
        assert validate_project_key("PROJ") == "PROJ"

    def test_valid_lowercase_normalized(self):
        """Test lowercase is normalized."""
        assert validate_project_key("proj") == "PROJ"

    def test_valid_with_numbers(self):
        """Test project key with numbers."""
        assert validate_project_key("PROJ2") == "PROJ2"

    def test_valid_min_length(self):
        """Test minimum length (2 chars)."""
        assert validate_project_key("AB") == "AB"

    def test_valid_max_length(self):
        """Test maximum length (10 chars)."""
        assert validate_project_key("ABCDEFGHIJ") == "ABCDEFGHIJ"

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_project_key("")

    def test_invalid_too_short(self):
        """Test single character raises error."""
        with pytest.raises(ValidationError):
            validate_project_key("A")

    def test_invalid_too_long(self):
        """Test 11+ characters raises error."""
        with pytest.raises(ValidationError):
            validate_project_key("ABCDEFGHIJK")

    def test_invalid_starts_with_number(self):
        """Test starting with number raises error."""
        with pytest.raises(ValidationError):
            validate_project_key("1PROJ")

    def test_invalid_special_chars(self):
        """Test special characters raise error."""
        with pytest.raises(ValidationError):
            validate_project_key("PROJ-1")
        with pytest.raises(ValidationError):
            validate_project_key("PROJ_X")


class TestValidateJql:
    """Tests for validate_jql function."""

    def test_valid_simple(self):
        """Test valid simple JQL."""
        assert validate_jql("project = PROJ") == "project = PROJ"

    def test_valid_stripped(self):
        """Test whitespace is stripped."""
        assert validate_jql("  project = PROJ  ") == "project = PROJ"

    def test_valid_complex(self):
        """Test complex JQL query."""
        jql = "project = PROJ AND status = Open ORDER BY created DESC"
        assert validate_jql(jql) == jql

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_jql("")

    def test_invalid_dangerous_drop(self):
        """Test SQL injection pattern DROP raises error."""
        with pytest.raises(ValidationError):
            validate_jql("project = PROJ; DROP TABLE issues")

    def test_invalid_dangerous_delete(self):
        """Test SQL injection pattern DELETE raises error."""
        with pytest.raises(ValidationError):
            validate_jql("project = PROJ; DELETE FROM issues")

    def test_invalid_dangerous_insert(self):
        """Test SQL injection pattern INSERT raises error."""
        with pytest.raises(ValidationError):
            validate_jql("project = PROJ; INSERT INTO issues")

    def test_invalid_dangerous_update(self):
        """Test SQL injection pattern UPDATE raises error."""
        with pytest.raises(ValidationError):
            validate_jql("project = PROJ; UPDATE issues SET")

    def test_invalid_dangerous_script(self):
        """Test XSS pattern script raises error."""
        with pytest.raises(ValidationError):
            validate_jql("project = PROJ <script>alert('xss')</script>")

    def test_invalid_dangerous_javascript(self):
        """Test XSS pattern javascript: raises error."""
        with pytest.raises(ValidationError):
            validate_jql("project = PROJ javascript:alert(1)")

    def test_invalid_too_long(self):
        """Test JQL over 10000 chars raises error."""
        long_jql = "project = " + "A" * 10000
        with pytest.raises(ValidationError):
            validate_jql(long_jql)


class TestValidateTransitionId:
    """Tests for validate_transition_id function."""

    def test_valid_numeric_string(self):
        """Test valid numeric string."""
        assert validate_transition_id("123") == "123"

    def test_valid_zero(self):
        """Test zero is valid."""
        assert validate_transition_id("0") == "0"

    def test_valid_integer(self):
        """Test integer input converted to string."""
        assert validate_transition_id(456) == "456"

    def test_invalid_negative(self):
        """Test negative number raises error."""
        with pytest.raises(ValidationError):
            validate_transition_id("-1")

    def test_invalid_non_numeric(self):
        """Test non-numeric string raises error."""
        with pytest.raises(ValidationError):
            validate_transition_id("abc")

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_transition_id("")


class TestValidateProjectType:
    """Tests for validate_project_type function."""

    def test_valid_software(self):
        """Test software project type."""
        assert validate_project_type("software") == "software"

    def test_valid_business(self):
        """Test business project type."""
        assert validate_project_type("business") == "business"

    def test_valid_service_desk(self):
        """Test service_desk project type."""
        assert validate_project_type("service_desk") == "service_desk"

    def test_valid_uppercase_normalized(self):
        """Test uppercase is normalized to lowercase."""
        assert validate_project_type("SOFTWARE") == "software"
        assert validate_project_type("Business") == "business"

    def test_invalid_unknown_type(self):
        """Test unknown type raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_project_type("unknown")
        assert "software" in str(exc_info.value)
        assert "business" in str(exc_info.value)

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_project_type("")

    def test_all_valid_types_work(self):
        """Test all valid types from constant."""
        for project_type in VALID_PROJECT_TYPES:
            assert validate_project_type(project_type) == project_type


class TestValidateAssigneeType:
    """Tests for validate_assignee_type function."""

    def test_valid_project_lead(self):
        """Test PROJECT_LEAD assignee type."""
        assert validate_assignee_type("PROJECT_LEAD") == "PROJECT_LEAD"

    def test_valid_unassigned(self):
        """Test UNASSIGNED assignee type."""
        assert validate_assignee_type("UNASSIGNED") == "UNASSIGNED"

    def test_valid_component_lead(self):
        """Test COMPONENT_LEAD assignee type."""
        assert validate_assignee_type("COMPONENT_LEAD") == "COMPONENT_LEAD"

    def test_valid_lowercase_normalized(self):
        """Test lowercase is normalized to uppercase."""
        assert validate_assignee_type("project_lead") == "PROJECT_LEAD"
        assert validate_assignee_type("unassigned") == "UNASSIGNED"

    def test_invalid_unknown_type(self):
        """Test unknown type raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_assignee_type("unknown")
        assert "PROJECT_LEAD" in str(exc_info.value)

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_assignee_type("")

    def test_all_valid_types_work(self):
        """Test all valid types from constant."""
        for assignee_type in VALID_ASSIGNEE_TYPES:
            assert validate_assignee_type(assignee_type) == assignee_type


class TestValidateProjectTemplate:
    """Tests for validate_project_template function."""

    def test_valid_scrum_shortcut(self):
        """Test scrum shortcut expands."""
        result = validate_project_template("scrum")
        assert result == PROJECT_TEMPLATES["scrum"]
        assert "scrum" in result

    def test_valid_kanban_shortcut(self):
        """Test kanban shortcut expands."""
        result = validate_project_template("kanban")
        assert result == PROJECT_TEMPLATES["kanban"]

    def test_valid_uppercase_shortcut(self):
        """Test uppercase shortcut is normalized."""
        result = validate_project_template("SCRUM")
        assert result == PROJECT_TEMPLATES["scrum"]

    def test_valid_full_template_key_with_colon(self):
        """Test full template key with colon passes through."""
        full_key = "com.example:custom-template"
        assert validate_project_template(full_key) == full_key

    def test_valid_full_template_key_with_dot(self):
        """Test full template key with dot passes through."""
        full_key = "com.example.template"
        assert validate_project_template(full_key) == full_key

    def test_invalid_unknown_shortcut(self):
        """Test unknown shortcut raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_project_template("unknowntemplate")
        assert "scrum" in str(exc_info.value)
        assert "kanban" in str(exc_info.value)

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_project_template("")

    def test_all_shortcuts_work(self):
        """Test all template shortcuts expand correctly."""
        for shortcut, full_key in PROJECT_TEMPLATES.items():
            assert validate_project_template(shortcut) == full_key


class TestValidateProjectName:
    """Tests for validate_project_name function."""

    def test_valid_simple(self):
        """Test valid simple name."""
        assert validate_project_name("My Project") == "My Project"

    def test_valid_min_length(self):
        """Test minimum length (2 chars)."""
        assert validate_project_name("AB") == "AB"

    def test_valid_max_length(self):
        """Test maximum length (80 chars)."""
        name = "A" * 80
        assert validate_project_name(name) == name

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_project_name("")

    def test_invalid_too_short(self):
        """Test single character raises error."""
        with pytest.raises(ValidationError):
            validate_project_name("A")

    def test_invalid_too_long(self):
        """Test 81+ characters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_project_name("A" * 81)
        assert "80" in str(exc_info.value)


class TestValidateCategoryName:
    """Tests for validate_category_name function."""

    def test_valid_simple(self):
        """Test valid simple name."""
        assert validate_category_name("Development") == "Development"

    def test_valid_min_length(self):
        """Test minimum length (1 char)."""
        assert validate_category_name("A") == "A"

    def test_valid_max_length(self):
        """Test maximum length (255 chars)."""
        name = "A" * 255
        assert validate_category_name(name) == name

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_category_name("")

    def test_invalid_too_long(self):
        """Test 256+ characters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_category_name("A" * 256)
        assert "255" in str(exc_info.value)


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_https(self):
        """Test valid HTTPS URL."""
        url = validate_url("https://example.atlassian.net")
        assert url.startswith("https://")

    def test_valid_trailing_slash_removed(self):
        """Test trailing slash is removed."""
        url = validate_url("https://example.atlassian.net/")
        assert not url.endswith("/")

    def test_invalid_http(self):
        """Test HTTP URL raises error (HTTPS required)."""
        with pytest.raises(ValidationError):
            validate_url("http://example.atlassian.net")

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_url("")

    def test_scheme_auto_added(self):
        """Test that https:// is auto-added to URLs without scheme."""
        url = validate_url("example.atlassian.net")
        assert url.startswith("https://")


class TestValidateEmail:
    """Tests for validate_email function."""

    def test_valid_simple(self):
        """Test valid simple email."""
        email = validate_email("user@example.com")
        assert email == "user@example.com"

    def test_valid_normalized_lowercase(self):
        """Test email is normalized to lowercase."""
        email = validate_email("User@Example.COM")
        assert email == "user@example.com"

    def test_invalid_empty(self):
        """Test empty string raises error."""
        with pytest.raises(ValidationError):
            validate_email("")

    def test_invalid_no_at(self):
        """Test missing @ raises error."""
        with pytest.raises(ValidationError):
            validate_email("userexample.com")

    def test_invalid_no_domain(self):
        """Test missing domain raises error."""
        with pytest.raises(ValidationError):
            validate_email("user@")


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_valid_existing_file(self):
        """Test valid existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            result = validate_file_path(temp_path, must_exist=True)
            assert os.path.isabs(result)
            assert os.path.exists(result)
        finally:
            os.unlink(temp_path)

    def test_valid_no_exist_check(self):
        """Test path without existence check."""
        result = validate_file_path("/nonexistent/path/file.txt", must_exist=False)
        assert os.path.isabs(result)

    def test_invalid_file_not_found(self):
        """Test nonexistent file raises error."""
        with pytest.raises(ValidationError):
            validate_file_path("/definitely/does/not/exist.txt", must_exist=True)

    def test_invalid_file_too_large(self):
        """Test file over 10MB raises error."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write just over 10MB
            f.write(b"x" * (10 * 1024 * 1024 + 1))
            temp_path = f.name

        try:
            with pytest.raises(ValidationError) as exc_info:
                validate_file_path(temp_path, must_exist=True)
            assert "too large" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)


class TestValidateAvatarFile:
    """Tests for validate_avatar_file function."""

    def test_valid_png(self):
        """Test valid PNG file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake png content")
            temp_path = f.name

        try:
            result = validate_avatar_file(temp_path)
            assert result.endswith(".png")
        finally:
            os.unlink(temp_path)

    def test_valid_jpg(self):
        """Test valid JPG file."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake jpg content")
            temp_path = f.name

        try:
            result = validate_avatar_file(temp_path)
            assert result.endswith(".jpg")
        finally:
            os.unlink(temp_path)

    def test_valid_jpeg(self):
        """Test valid JPEG file."""
        with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as f:
            f.write(b"fake jpeg content")
            temp_path = f.name

        try:
            result = validate_avatar_file(temp_path)
            assert result.endswith(".jpeg")
        finally:
            os.unlink(temp_path)

    def test_valid_gif(self):
        """Test valid GIF file."""
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            f.write(b"fake gif content")
            temp_path = f.name

        try:
            result = validate_avatar_file(temp_path)
            assert result.endswith(".gif")
        finally:
            os.unlink(temp_path)

    def test_invalid_extension(self):
        """Test invalid file extension raises error."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"text content")
            temp_path = f.name

        try:
            with pytest.raises(ValidationError) as exc_info:
                validate_avatar_file(temp_path)
            assert ".png" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_invalid_too_large(self):
        """Test avatar over 1MB raises error."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write just over 1MB
            f.write(b"x" * (1 * 1024 * 1024 + 1))
            temp_path = f.name

        try:
            with pytest.raises(ValidationError) as exc_info:
                validate_avatar_file(temp_path)
            assert "too large" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

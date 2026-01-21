"""
Input validation utilities for JIRA operations.

Provides functions to validate issue keys, JQL queries, project keys,
and other inputs before making API calls.
"""

import os
import re
from typing import Any

from assistant_skills_lib.error_handler import ValidationError
from assistant_skills_lib.validators import validate_email as base_validate_email
from assistant_skills_lib.validators import (
    validate_int,
)
from assistant_skills_lib.validators import validate_path as base_validate_path
from assistant_skills_lib.validators import (
    validate_required,
)
from assistant_skills_lib.validators import validate_url as base_validate_url


def safe_get_nested(obj: dict, path: str, default: Any = None) -> Any:
    """
    Safely access nested dict values using dot notation.

    Replaces verbose chains like:
        fields.get("status", {}).get("name", "N/A")
    with:
        safe_get_nested(fields, "status.name", "N/A")

    Args:
        obj: Dictionary to access
        path: Dot-separated path (e.g., "fields.status.name")
        default: Default value if path not found

    Returns:
        Value at path or default

    Examples:
        >>> issue = {"fields": {"status": {"name": "Open"}}}
        >>> safe_get_nested(issue, "fields.status.name", "N/A")
        'Open'
        >>> safe_get_nested(issue, "fields.assignee.displayName", "Unassigned")
        'Unassigned'
        >>> safe_get_nested({}, "a.b.c", "default")
        'default'
    """
    if not obj or not isinstance(obj, dict):
        return default

    keys = path.split(".")
    current: Any = obj

    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default

    return current


def validate_issue_key(issue_key: str) -> str:
    """
    Validate JIRA issue key format (e.g., PROJ-123).

    Args:
        issue_key: Issue key to validate

    Returns:
        Normalized issue key (uppercase)

    Raises:
        ValidationError: If format is invalid
    """
    issue_key = validate_required(issue_key, "issue_key")
    issue_key = issue_key.upper()

    pattern = r"^[A-Z][A-Z0-9]*-[0-9]+$"
    if not re.match(pattern, issue_key):
        raise ValidationError(
            f"Invalid issue key format: '{issue_key}'. "
            "Expected format: PROJECT-123 (e.g., PROJ-42, DEV-1234)",
            operation="validation",
            details={"field": "issue_key", "value": issue_key},
        )

    return issue_key


def validate_project_key(project_key: str) -> str:
    """
    Validate JIRA project key format.

    Args:
        project_key: Project key to validate

    Returns:
        Normalized project key (uppercase)

    Raises:
        ValidationError: If format is invalid
    """
    project_key = validate_required(project_key, "project_key")
    project_key = project_key.upper()

    pattern = r"^[A-Z][A-Z0-9]*$"
    if not re.match(pattern, project_key):
        raise ValidationError(
            f"Invalid project key format: '{project_key}'. "
            "Expected format: 2-10 uppercase letters/numbers, starting with a letter "
            "(e.g., PROJ, DEV, SUPPORT)",
            operation="validation",
            details={"field": "project_key", "value": project_key},
        )

    if len(project_key) < 2 or len(project_key) > 10:
        raise ValidationError(
            f"Project key must be 2-10 characters long (got {len(project_key)})",
            operation="validation",
            details={"field": "project_key", "value": project_key},
        )

    return project_key


def validate_jql(jql: str) -> str:
    """
    Basic JQL syntax validation.

    Args:
        jql: JQL query string to validate

    Returns:
        Normalized JQL query (stripped)

    Raises:
        ValidationError: If JQL appears invalid
    """
    jql = validate_required(jql, "jql")

    dangerous_patterns = [
        r";\s*DROP",
        r";\s*DELETE",
        r";\s*INSERT",
        r";\s*UPDATE",
        r"<script",
        r"javascript:",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, jql, re.IGNORECASE):
            raise ValidationError(
                f"JQL query contains potentially dangerous pattern: {pattern}",
                operation="validation",
                details={"field": "jql", "value": jql},
            )

    if len(jql) > 10000:
        raise ValidationError(
            f"JQL query is too long ({len(jql)} characters). Maximum is 10000.",
            operation="validation",
            details={"field": "jql", "value": jql},
        )

    return jql


def validate_file_path(file_path: str, must_exist: bool = True) -> str:
    """
    Validate file path for attachments.
    Leverages base_validate_path and adds JIRA-specific size limits.

    Args:
        file_path: Path to file
        must_exist: If True, verify file exists

    Returns:
        Absolute file path

    Raises:
        ValidationError: If file doesn't exist or path is invalid
    """
    path_obj = base_validate_path(
        file_path,
        field_name="file_path",
        must_exist=must_exist,
        must_be_file=True,  # Always a file for attachments
    )
    abs_path = str(path_obj.absolute())

    if must_exist:
        file_size = os.path.getsize(abs_path)
        max_size = 10 * 1024 * 1024
        if file_size > max_size:
            raise ValidationError(
                f"File is too large ({file_size / 1024 / 1024:.1f}MB). "
                f"Maximum size is {max_size / 1024 / 1024}MB.",
                operation="validation",
                details={"field": "file_path", "value": abs_path},
            )

    return abs_path


def validate_url(url: str, require_https: bool = True) -> str:
    """
    Validate JIRA instance URL using base_validate_url.

    Args:
        url: URL to validate
        require_https: If True, ensure HTTPS protocol (default for Jira)

    Returns:
        Normalized URL (no trailing slash)

    Raises:
        ValidationError: If URL format is invalid
    """
    return base_validate_url(
        url,
        field_name="URL",
        require_https=require_https,
        allowed_schemes=["https"],  # JIRA typically requires HTTPS
    )


def validate_email(email: str) -> str:
    """
    Validate email address format using base_validate_email.

    Args:
        email: Email address to validate

    Returns:
        Normalized email (lowercase)

    Raises:
        ValidationError: If email format is invalid
    """
    return base_validate_email(email, field_name="email")


def validate_transition_id(transition_id: str) -> str:
    """
    Validate transition ID (numeric string).

    Args:
        transition_id: Transition ID to validate

    Returns:
        Validated transition ID

    Raises:
        ValidationError: If not a valid numeric ID
    """
    transition_id_int = validate_int(transition_id, "transition_id", min_value=0)
    return str(transition_id_int)


# ========== Project Administration Validators ==========

VALID_PROJECT_TYPES = ["software", "business", "service_desk"]
VALID_ASSIGNEE_TYPES = ["PROJECT_LEAD", "UNASSIGNED", "COMPONENT_LEAD"]

# Common project template shortcuts
PROJECT_TEMPLATES = {
    "scrum": "com.pyxis.greenhopper.jira:gh-simplified-agility-scrum",
    "kanban": "com.pyxis.greenhopper.jira:gh-simplified-agility-kanban",
    "basic": "com.pyxis.greenhopper.jira:gh-simplified-basic",
    "simplified-scrum": "com.pyxis.greenhopper.jira:gh-simplified-agility-scrum",
    "simplified-kanban": "com.pyxis.greenhopper.jira:gh-simplified-agility-kanban",
    "classic-scrum": "com.pyxis.greenhopper.jira:gh-scrum-template",
    "classic-kanban": "com.pyxis.greenhopper.jira:gh-kanban-template",
    "project-management": "com.atlassian.jira-core-project-templates:jira-core-project-management",
    "task-management": "com.atlassian.jira-core-project-templates:jira-core-task-management",
    "it-service-desk": "com.atlassian.servicedesk:simplified-it-service-desk",
    "general-service-desk": "com.atlassian.servicedesk:simplified-general-service-desk",
}


def _validate_enum(
    value: str, field_name: str, valid_values: list[str], normalize: str = "lower"
) -> str:
    """
    Validate value is in a list of valid options.

    Args:
        value: Value to validate
        field_name: Field name for error messages
        valid_values: List of valid options
        normalize: "lower" or "upper" for case normalization

    Returns:
        Normalized, validated value

    Raises:
        ValidationError: If value is not in valid_values
    """
    value = validate_required(value, field_name)
    value = value.lower() if normalize == "lower" else value.upper()

    if value not in valid_values:
        raise ValidationError(
            f"Invalid {field_name.replace('_', ' ')}: '{value}'. "
            f"Valid types: {', '.join(valid_values)}",
            operation="validation",
            details={"field": field_name, "value": value},
        )

    return value


def validate_project_type(project_type: str) -> str:
    """
    Validate project type.

    Args:
        project_type: Project type (software, business, service_desk)

    Returns:
        Validated project type (lowercase)

    Raises:
        ValidationError: If project type is invalid
    """
    return _validate_enum(project_type, "project_type", VALID_PROJECT_TYPES, "lower")


def validate_assignee_type(assignee_type: str) -> str:
    """
    Validate default assignee type.

    Args:
        assignee_type: Assignee type (PROJECT_LEAD, UNASSIGNED, COMPONENT_LEAD)

    Returns:
        Validated assignee type (uppercase)

    Raises:
        ValidationError: If assignee type is invalid
    """
    return _validate_enum(assignee_type, "assignee_type", VALID_ASSIGNEE_TYPES, "upper")


def validate_project_template(template: str) -> str:
    """
    Validate and expand project template.

    Args:
        template: Template shortcut or full template key

    Returns:
        Full template key

    Raises:
        ValidationError: If template is unknown shortcut
    """
    template = validate_required(template, "project_template")
    template = template.lower()

    # If it's a shortcut, expand it
    if template in PROJECT_TEMPLATES:
        return PROJECT_TEMPLATES[template]

    # If it looks like a full template key, return it
    if "." in template or ":" in template:
        return template

    # Unknown shortcut
    shortcuts = ", ".join(PROJECT_TEMPLATES.keys())
    raise ValidationError(
        f"Unknown template shortcut: '{template}'. "
        f"Valid shortcuts: {shortcuts}\n"
        "Or provide a full template key (e.g., com.pyxis.greenhopper.jira:gh-scrum-template)",
        operation="validation",
        details={"field": "project_template", "value": template},
    )


def _validate_string_length(
    value: str, field_name: str, min_length: int, max_length: int
) -> str:
    """
    Validate string length within bounds.

    Args:
        value: String to validate (already stripped by validate_required)
        field_name: Field name for error messages
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Validated string

    Raises:
        ValidationError: If length is out of bounds
    """
    value = validate_required(value, field_name)

    if len(value) < min_length:
        raise ValidationError(
            f"{field_name.replace('_', ' ').capitalize()} must be at least "
            f"{min_length} character{'s' if min_length > 1 else ''} long",
            operation="validation",
            details={"field": field_name, "value": value},
        )

    if len(value) > max_length:
        raise ValidationError(
            f"{field_name.replace('_', ' ').capitalize()} is too long "
            f"({len(value)} characters). Maximum is {max_length}.",
            operation="validation",
            details={"field": field_name, "value": value},
        )

    return value


def validate_project_name(name: str) -> str:
    """
    Validate project name.

    Args:
        name: Project name

    Returns:
        Validated project name (stripped)

    Raises:
        ValidationError: If name is invalid
    """
    return _validate_string_length(name, "project_name", min_length=2, max_length=80)


def validate_category_name(name: str) -> str:
    """
    Validate project category name.

    Args:
        name: Category name

    Returns:
        Validated category name (stripped)

    Raises:
        ValidationError: If name is invalid
    """
    return _validate_string_length(name, "category_name", min_length=1, max_length=255)


def validate_avatar_file(file_path: str) -> str:
    """
    Validate avatar file for project avatar upload.

    Args:
        file_path: Path to avatar image file

    Returns:
        Absolute path to validated file

    Raises:
        ValidationError: If file is invalid for avatar use
    """
    # Use base file validation
    abs_path = validate_file_path(file_path, must_exist=True)

    # Check file extension
    valid_extensions = [".png", ".jpg", ".jpeg", ".gif"]
    ext = os.path.splitext(abs_path)[1].lower()

    if ext not in valid_extensions:
        raise ValidationError(
            f"Invalid avatar file format: '{ext}'. "
            f"Valid formats: {', '.join(valid_extensions)}",
            operation="validation",
            details={"field": "file_path", "value": abs_path},
        )

    # Check file size (1MB max for avatars)
    file_size = os.path.getsize(abs_path)
    max_size = 1 * 1024 * 1024  # 1MB
    if file_size > max_size:
        raise ValidationError(
            f"Avatar file is too large ({file_size / 1024:.1f}KB). "
            f"Maximum size is {max_size / 1024}KB.",
            operation="validation",
            details={"field": "file_path", "value": abs_path},
        )

    return abs_path

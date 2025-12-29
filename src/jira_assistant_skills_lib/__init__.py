"""
JIRA Assistant Skills Library

A shared library for interacting with the JIRA REST API, providing:
    - jira_client: HTTP client with retry logic and error handling
    - config_manager: Multi-source configuration management
    - error_handler: Exception hierarchy and error handling
    - validators: Input validation for JIRA-specific formats
    - formatters: Output formatting utilities (tables, JSON, CSV)
    - adf_helper: Atlassian Document Format conversion
    - time_utils: JIRA time format parsing and formatting
    - cache: SQLite-based caching with TTL support
    - credential_manager: Secure credential storage

Example usage:
    from jira_assistant_skills_lib import get_jira_client, handle_errors

    @handle_errors
    def main():
        client = get_jira_client()
        issue = client.get_issue('PROJ-123')
        print(issue['fields']['summary'])
"""

__version__ = "0.1.1"

# Error handling
from .error_handler import (
    JiraError,
    AuthenticationError,
    PermissionError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    ConflictError,
    ServerError,
    AutomationError,
    AutomationNotFoundError,
    AutomationPermissionError,
    AutomationValidationError,
    handle_jira_error,
    sanitize_error_message,
    print_error,
    handle_errors,
)

# JIRA Client
from .jira_client import JiraClient

# Configuration
from .config_manager import (
    ConfigManager,
    get_jira_client,
)

# Validators
from .validators import (
    validate_issue_key,
    validate_jql,
    validate_project_key,
    validate_file_path,
    validate_url,
    validate_email,
    validate_transition_id,
    validate_project_type,
    validate_assignee_type,
    validate_project_template,
    validate_project_name,
    validate_category_name,
    validate_avatar_file,
    VALID_PROJECT_TYPES,
    VALID_ASSIGNEE_TYPES,
    PROJECT_TEMPLATES,
)

# Formatters
from .formatters import (
    format_issue,
    format_table,
    format_json,
    export_csv,
    get_csv_string,
    format_transitions,
    format_comments,
    format_search_results,
    print_success,
    print_warning,
    print_info,
    EPIC_LINK_FIELD,
    STORY_POINTS_FIELD,
)

# ADF Helper
from .adf_helper import (
    text_to_adf,
    markdown_to_adf,
    adf_to_text,
    create_adf_paragraph,
    create_adf_heading,
    create_adf_code_block,
    wiki_markup_to_adf,
)

# Time utilities
from .time_utils import (
    parse_time_string,
    format_seconds,
    format_seconds_long,
    parse_relative_date,
    format_datetime_for_jira,
    validate_time_format,
    calculate_progress,
    format_progress_bar,
    parse_date_to_iso,
    convert_to_jira_datetime_string,
    SECONDS_PER_MINUTE,
    SECONDS_PER_HOUR,
    SECONDS_PER_DAY,
    SECONDS_PER_WEEK,
    HOURS_PER_DAY,
    DAYS_PER_WEEK,
)

# Cache
from .cache import (
    JiraCache,
    get_cache,
)

# Automation client
from .automation_client import AutomationClient

# Batch processing
from .batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchProgress,
    CheckpointManager,
    get_recommended_batch_size,
    generate_operation_id,
    list_pending_checkpoints,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "JiraClient",
    "AutomationClient",
    # Config
    "ConfigManager",
    "get_jira_client",
    # Errors
    "JiraError",
    "AuthenticationError",
    "PermissionError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "ConflictError",
    "ServerError",
    "AutomationError",
    "AutomationNotFoundError",
    "AutomationPermissionError",
    "AutomationValidationError",
    "handle_jira_error",
    "sanitize_error_message",
    "print_error",
    "handle_errors",
    # Validators
    "validate_issue_key",
    "validate_jql",
    "validate_project_key",
    "validate_file_path",
    "validate_url",
    "validate_email",
    "validate_transition_id",
    "validate_project_type",
    "validate_assignee_type",
    "validate_project_template",
    "validate_project_name",
    "validate_category_name",
    "validate_avatar_file",
    "VALID_PROJECT_TYPES",
    "VALID_ASSIGNEE_TYPES",
    "PROJECT_TEMPLATES",
    # Formatters
    "format_issue",
    "format_table",
    "format_json",
    "export_csv",
    "get_csv_string",
    "format_transitions",
    "format_comments",
    "format_search_results",
    "print_success",
    "print_warning",
    "print_info",
    "EPIC_LINK_FIELD",
    "STORY_POINTS_FIELD",
    # ADF Helper
    "text_to_adf",
    "markdown_to_adf",
    "adf_to_text",
    "create_adf_paragraph",
    "create_adf_heading",
    "create_adf_code_block",
    "wiki_markup_to_adf",
    # Time Utils
    "parse_time_string",
    "format_seconds",
    "format_seconds_long",
    "parse_relative_date",
    "format_datetime_for_jira",
    "validate_time_format",
    "calculate_progress",
    "format_progress_bar",
    "parse_date_to_iso",
    "convert_to_jira_datetime_string",
    "SECONDS_PER_MINUTE",
    "SECONDS_PER_HOUR",
    "SECONDS_PER_DAY",
    "SECONDS_PER_WEEK",
    "HOURS_PER_DAY",
    "DAYS_PER_WEEK",
    # Cache
    "JiraCache",
    "get_cache",
    # Batch Processing
    "BatchProcessor",
    "BatchConfig",
    "BatchProgress",
    "CheckpointManager",
    "get_recommended_batch_size",
    "generate_operation_id",
    "list_pending_checkpoints",
]

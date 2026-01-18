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

__version__ = "1.1.0"

# Error handling
# ADF Helper
from .adf_helper import _parse_wiki_inline  # Exposed for testing
from .adf_helper import (
    adf_to_text,
    create_adf_code_block,
    create_adf_heading,
    create_adf_paragraph,
    markdown_to_adf,
    text_to_adf,
    wiki_markup_to_adf,
)

# Autocomplete cache
from .autocomplete_cache import (
    AutocompleteCache,
    get_autocomplete_cache,
)

# Automation client
from .automation_client import AutomationClient

# Batch processing
from .batch_processor import (
    BatchConfig,
    BatchProcessor,
    BatchProgress,
    CheckpointManager,
    generate_operation_id,
    get_recommended_batch_size,
    list_pending_checkpoints,
)

# Cache
from .cache import (
    CacheStats,
    JiraCache,
    get_cache,
)

# Configuration
from .config_manager import (
    ConfigManager,
    get_agile_field,
    get_agile_fields,
    get_automation_client,
    get_jira_client,
    get_project_defaults,
)

# Credential management
from .credential_manager import (
    CredentialBackend,
    CredentialManager,
    CredentialNotFoundError,
    get_credentials,
    is_keychain_available,
    store_credentials,
    validate_credentials,
)
from .error_handler import (
    AuthenticationError,
    AutomationError,
    AutomationNotFoundError,
    AutomationPermissionError,
    AutomationValidationError,
    ConflictError,
    JiraError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServerError,
    ValidationError,
    handle_errors,
    handle_jira_error,
    print_error,
    sanitize_error_message,
)

# JSM / SLA utilities (now in formatters)
# Formatters
from .formatters import format_duration  # backwards-compatible alias
from .formatters import (
    EPIC_LINK_FIELD,
    STORY_POINTS_FIELD,
    IssueFields,
    calculate_sla_percentage,
    export_csv,
    extract_issue_fields,
    format_comments,
    format_issue,
    format_json,
    format_search_results,
    format_sla_duration,
    format_sla_time,
    format_table,
    format_transitions,
    get_csv_string,
    get_sla_status_emoji,
    get_sla_status_text,
    is_sla_at_risk,
    print_info,
    print_success,
    print_warning,
)

# JIRA Client
from .jira_client import JiraClient

# Permission helpers
from .permission_helpers import (
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

# Project context
from .project_context import (
    ProjectContext,
    clear_context_cache,
    format_context_summary,
    get_common_labels,
    get_defaults_for_issue_type,
    get_project_context,
    get_statuses_for_issue_type,
    get_valid_transitions,
    has_project_context,
    suggest_assignee,
    validate_transition,
)

# Request batching
from .request_batcher import (
    BatchError,
    BatchResult,
    RequestBatcher,
    batch_fetch_issues,
)

# Time utilities
from .time_utils import (
    DAYS_PER_WEEK,
    HOURS_PER_DAY,
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    SECONDS_PER_WEEK,
    calculate_progress,
    convert_to_jira_datetime_string,
    format_datetime_for_jira,
    format_progress_bar,
    format_seconds,
    format_seconds_long,
    parse_date_to_iso,
    parse_relative_date,
    parse_time_string,
    validate_time_format,
)

# Transition helpers
from .transition_helpers import (
    find_transition_by_keywords,
    find_transition_by_name,
)

# User helpers
from .user_helpers import (
    UserNotFoundError,
    get_user_display_info,
    resolve_user_to_account_id,
    resolve_users_batch,
)

# Validators
from .validators import (
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

__all__ = [
    "DAYS_PER_WEEK",
    "EPIC_LINK_FIELD",
    "HOLDER_TYPES_WITHOUT_PARAMETER",
    "HOLDER_TYPES_WITH_PARAMETER",
    "HOURS_PER_DAY",
    "IssueFields",
    "PROJECT_TEMPLATES",
    "SECONDS_PER_DAY",
    "SECONDS_PER_HOUR",
    "SECONDS_PER_MINUTE",
    "SECONDS_PER_WEEK",
    "STORY_POINTS_FIELD",
    "VALID_ASSIGNEE_TYPES",
    "VALID_HOLDER_TYPES",
    "VALID_PROJECT_TYPES",
    "AuthenticationError",
    # Autocomplete Cache
    "AutocompleteCache",
    "AutomationClient",
    "AutomationError",
    "AutomationNotFoundError",
    "AutomationPermissionError",
    "AutomationValidationError",
    "BatchConfig",
    "BatchError",
    # Batch Processing
    "BatchProcessor",
    "BatchProgress",
    "BatchResult",
    "CacheStats",
    "CheckpointManager",
    # Config
    "ConfigManager",
    "ConflictError",
    "CredentialBackend",
    # Credential Management
    "CredentialManager",
    "CredentialNotFoundError",
    # Cache
    "JiraCache",
    # Client
    "JiraClient",
    # Errors
    "JiraError",
    "NotFoundError",
    "PermissionError",
    # Project Context
    "ProjectContext",
    "RateLimitError",
    # Request Batching
    "RequestBatcher",
    "ServerError",
    # User Helpers
    "UserNotFoundError",
    "ValidationError",
    # Version
    "__version__",
    "_parse_wiki_inline",  # Exposed for testing
    "adf_to_text",
    "batch_fetch_issues",
    "build_grant_payload",
    "calculate_progress",
    "calculate_sla_percentage",
    "clear_context_cache",
    "convert_to_jira_datetime_string",
    "create_adf_code_block",
    "create_adf_heading",
    "create_adf_paragraph",
    "export_csv",
    "extract_issue_fields",
    "find_grant_by_spec",
    "find_scheme_by_name",
    "find_transition_by_keywords",
    # Transition Helpers
    "find_transition_by_name",
    "format_comments",
    "format_context_summary",
    "format_datetime_for_jira",
    "format_duration",  # backwards-compatible alias for format_sla_duration
    "format_grant",
    "format_grant_for_export",
    # Formatters
    "format_issue",
    "format_json",
    "format_progress_bar",
    "format_scheme_summary",
    "format_search_results",
    "format_seconds",
    "format_seconds_long",
    # JSM / SLA Utilities
    "format_sla_duration",
    "format_sla_time",
    "format_table",
    "format_transitions",
    "generate_operation_id",
    "get_agile_field",
    "get_agile_fields",
    "get_autocomplete_cache",
    "get_automation_client",
    "get_cache",
    "get_common_labels",
    "get_credentials",
    "get_csv_string",
    "get_defaults_for_issue_type",
    "get_holder_display",
    "get_jira_client",
    "get_project_context",
    "get_project_defaults",
    "get_recommended_batch_size",
    "get_sla_status_emoji",
    "get_sla_status_text",
    "get_statuses_for_issue_type",
    "get_user_display_info",
    "get_valid_transitions",
    "group_grants_by_permission",
    "handle_errors",
    "handle_jira_error",
    "has_project_context",
    "is_keychain_available",
    "is_sla_at_risk",
    "list_pending_checkpoints",
    "markdown_to_adf",
    "parse_date_to_iso",
    # Permission Helpers
    "parse_grant_string",
    "parse_relative_date",
    # Time Utils
    "parse_time_string",
    "print_error",
    "print_info",
    "print_success",
    "print_warning",
    "resolve_user_to_account_id",
    "resolve_users_batch",
    "safe_get_nested",
    "sanitize_error_message",
    "store_credentials",
    "suggest_assignee",
    # ADF Helper
    "text_to_adf",
    "validate_assignee_type",
    "validate_avatar_file",
    "validate_category_name",
    "validate_credentials",
    "validate_email",
    "validate_file_path",
    "validate_holder_type",
    # Validators
    "validate_issue_key",
    "validate_jql",
    "validate_permission",
    "validate_project_key",
    "validate_project_name",
    "validate_project_template",
    "validate_project_type",
    "validate_time_format",
    "validate_transition",
    "validate_transition_id",
    "validate_url",
    "wiki_markup_to_adf",
]

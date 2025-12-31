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

__version__ = "0.1.5"

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
    get_automation_client,
    get_agile_fields,
    get_agile_field,
    get_project_defaults,
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
    _parse_wiki_inline,  # Exposed for testing
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
    CacheStats,
    get_cache,
)

# Request batching
from .request_batcher import (
    RequestBatcher,
    BatchResult,
    BatchError,
    batch_fetch_issues,
)

# Automation client
from .automation_client import AutomationClient

# Permission helpers
from .permission_helpers import (
    parse_grant_string,
    format_grant,
    format_grant_for_export,
    build_grant_payload,
    validate_permission,
    validate_holder_type,
    find_scheme_by_name,
    group_grants_by_permission,
    find_grant_by_spec,
    get_holder_display,
    format_scheme_summary,
    VALID_HOLDER_TYPES,
    HOLDER_TYPES_WITH_PARAMETER,
    HOLDER_TYPES_WITHOUT_PARAMETER,
)

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

# Credential management
from .credential_manager import (
    CredentialManager,
    CredentialBackend,
    CredentialNotFoundError,
    is_keychain_available,
    get_credentials,
    store_credentials,
    validate_credentials,
)

# Project context
from .project_context import (
    ProjectContext,
    get_project_context,
    clear_context_cache,
    has_project_context,
    get_defaults_for_issue_type,
    get_valid_transitions,
    get_statuses_for_issue_type,
    suggest_assignee,
    get_common_labels,
    validate_transition,
    format_context_summary,
)

# Transition helpers
from .transition_helpers import (
    find_transition_by_name,
    find_transition_by_keywords,
    format_transition_list,
)

# User helpers
from .user_helpers import (
    UserNotFoundError,
    resolve_user_to_account_id,
    get_user_display_info,
    resolve_users_batch,
)

# JSM utilities
from .jsm_utils import (
    format_sla_time,
    format_duration,
    calculate_sla_percentage,
    is_sla_at_risk,
    get_sla_status_emoji,
    get_sla_status_text,
)

# Autocomplete cache
from .autocomplete_cache import (
    AutocompleteCache,
    get_autocomplete_cache,
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
    "get_automation_client",
    "get_agile_fields",
    "get_agile_field",
    "get_project_defaults",
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
    "CacheStats",
    "get_cache",
    # Request Batching
    "RequestBatcher",
    "BatchResult",
    "BatchError",
    "batch_fetch_issues",
    # Batch Processing
    "BatchProcessor",
    "BatchConfig",
    "BatchProgress",
    "CheckpointManager",
    "get_recommended_batch_size",
    "generate_operation_id",
    "list_pending_checkpoints",
    # Permission Helpers
    "parse_grant_string",
    "format_grant",
    "format_grant_for_export",
    "build_grant_payload",
    "validate_permission",
    "validate_holder_type",
    "find_scheme_by_name",
    "group_grants_by_permission",
    "find_grant_by_spec",
    "get_holder_display",
    "format_scheme_summary",
    "VALID_HOLDER_TYPES",
    "HOLDER_TYPES_WITH_PARAMETER",
    "HOLDER_TYPES_WITHOUT_PARAMETER",
    # Credential Management
    "CredentialManager",
    "CredentialBackend",
    "CredentialNotFoundError",
    "is_keychain_available",
    "get_credentials",
    "store_credentials",
    "validate_credentials",
    # Project Context
    "ProjectContext",
    "get_project_context",
    "clear_context_cache",
    "has_project_context",
    "get_defaults_for_issue_type",
    "get_valid_transitions",
    "get_statuses_for_issue_type",
    "suggest_assignee",
    "get_common_labels",
    "validate_transition",
    "format_context_summary",
    # Transition Helpers
    "find_transition_by_name",
    "find_transition_by_keywords",
    "format_transition_list",
    # User Helpers
    "UserNotFoundError",
    "resolve_user_to_account_id",
    "get_user_display_info",
    "resolve_users_batch",
    # JSM Utilities
    "format_sla_time",
    "format_duration",
    "calculate_sla_percentage",
    "is_sla_at_risk",
    "get_sla_status_emoji",
    "get_sla_status_text",
    # Autocomplete Cache
    "AutocompleteCache",
    "get_autocomplete_cache",
]

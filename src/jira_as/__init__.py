"""
JIRA AS

A Python library for interacting with the JIRA REST API, providing:
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
    from jira_as import get_jira_client, handle_errors

    @handle_errors
    def main():
        client = get_jira_client()
        issue = client.get_issue('PROJ-123')
        print(issue['fields']['summary'])
"""

__version__ = "1.0.0"

# Error handling
# ADF Helper
from .adf_helper import _parse_wiki_inline  # Exposed for testing
from .adf_helper import adf_to_text
from .adf_helper import create_adf_code_block
from .adf_helper import create_adf_heading
from .adf_helper import create_adf_paragraph
from .adf_helper import markdown_to_adf
from .adf_helper import text_to_adf
from .adf_helper import wiki_markup_to_adf

# Autocomplete cache
from .autocomplete_cache import AutocompleteCache
from .autocomplete_cache import get_autocomplete_cache

# Automation client
from .automation_client import AutomationClient

# Batch processing
from .batch_processor import BatchConfig
from .batch_processor import BatchProcessor
from .batch_processor import BatchProgress
from .batch_processor import CheckpointManager
from .batch_processor import generate_operation_id
from .batch_processor import get_recommended_batch_size
from .batch_processor import list_pending_checkpoints

# Cache
from .cache import CacheStats
from .cache import JiraCache
from .cache import get_cache

# Configuration
from .config_manager import ConfigManager
from .config_manager import get_agile_field
from .config_manager import get_agile_fields
from .config_manager import get_automation_client
from .config_manager import get_jira_client
from .config_manager import get_project_defaults

# Credential management
from .credential_manager import CredentialBackend
from .credential_manager import CredentialManager
from .credential_manager import CredentialNotFoundError
from .credential_manager import get_credentials
from .credential_manager import is_keychain_available
from .credential_manager import store_credentials
from .credential_manager import validate_credentials
from .error_handler import AuthenticationError
from .error_handler import AutomationError
from .error_handler import AutomationNotFoundError
from .error_handler import AutomationPermissionError
from .error_handler import AutomationValidationError
from .error_handler import ConflictError
from .error_handler import JiraError
from .error_handler import NotFoundError
from .error_handler import PermissionError
from .error_handler import RateLimitError
from .error_handler import ServerError
from .error_handler import ValidationError
from .error_handler import handle_errors
from .error_handler import handle_jira_error
from .error_handler import print_error
from .error_handler import sanitize_error_message

# JSM / SLA utilities (now in formatters)
# Formatters
from .formatters import EPIC_LINK_FIELD
from .formatters import STORY_POINTS_FIELD
from .formatters import IssueFields
from .formatters import calculate_sla_percentage
from .formatters import export_csv
from .formatters import extract_issue_fields
from .formatters import format_comments
from .formatters import format_duration  # backwards-compatible alias
from .formatters import format_issue
from .formatters import format_json
from .formatters import format_search_results
from .formatters import format_sla_duration
from .formatters import format_sla_time
from .formatters import format_table
from .formatters import format_transitions
from .formatters import get_csv_string
from .formatters import get_sla_status_emoji
from .formatters import get_sla_status_text
from .formatters import is_sla_at_risk
from .formatters import print_info
from .formatters import print_success
from .formatters import print_warning

# JIRA Client
from .jira_client import JiraClient

# Permission helpers
from .permission_helpers import HOLDER_TYPES_WITH_PARAMETER
from .permission_helpers import HOLDER_TYPES_WITHOUT_PARAMETER
from .permission_helpers import VALID_HOLDER_TYPES
from .permission_helpers import build_grant_payload
from .permission_helpers import find_grant_by_spec
from .permission_helpers import find_scheme_by_name
from .permission_helpers import format_grant
from .permission_helpers import format_grant_for_export
from .permission_helpers import format_scheme_summary
from .permission_helpers import get_holder_display
from .permission_helpers import group_grants_by_permission
from .permission_helpers import parse_grant_string
from .permission_helpers import validate_holder_type
from .permission_helpers import validate_permission

# Project context
from .project_context import ProjectContext
from .project_context import clear_context_cache
from .project_context import format_context_summary
from .project_context import get_common_labels
from .project_context import get_defaults_for_issue_type
from .project_context import get_project_context
from .project_context import get_statuses_for_issue_type
from .project_context import get_valid_transitions
from .project_context import has_project_context
from .project_context import suggest_assignee
from .project_context import validate_transition

# Request batching
from .request_batcher import BatchError
from .request_batcher import BatchResult
from .request_batcher import RequestBatcher
from .request_batcher import batch_fetch_issues

# Time utilities
from .time_utils import DAYS_PER_WEEK
from .time_utils import HOURS_PER_DAY
from .time_utils import SECONDS_PER_DAY
from .time_utils import SECONDS_PER_HOUR
from .time_utils import SECONDS_PER_MINUTE
from .time_utils import SECONDS_PER_WEEK
from .time_utils import calculate_progress
from .time_utils import convert_to_jira_datetime_string
from .time_utils import format_datetime_for_jira
from .time_utils import format_progress_bar
from .time_utils import format_seconds
from .time_utils import format_seconds_long
from .time_utils import parse_date_to_iso
from .time_utils import parse_relative_date
from .time_utils import parse_time_string
from .time_utils import validate_time_format

# Transition helpers
from .transition_helpers import find_transition_by_keywords
from .transition_helpers import find_transition_by_name

# User helpers
from .user_helpers import UserNotFoundError
from .user_helpers import get_user_display_info
from .user_helpers import resolve_user_to_account_id
from .user_helpers import resolve_users_batch

# Validators
from .validators import PROJECT_TEMPLATES
from .validators import VALID_ASSIGNEE_TYPES
from .validators import VALID_PROJECT_TYPES
from .validators import safe_get_nested
from .validators import validate_assignee_type
from .validators import validate_avatar_file
from .validators import validate_category_name
from .validators import validate_email
from .validators import validate_file_path
from .validators import validate_issue_key
from .validators import validate_jql
from .validators import validate_project_key
from .validators import validate_project_name
from .validators import validate_project_template
from .validators import validate_project_type
from .validators import validate_transition_id
from .validators import validate_url

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

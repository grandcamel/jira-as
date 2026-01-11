"""
Error handling for JIRA API operations.

Provides custom exception hierarchy and utilities for handling
JIRA API errors with user-friendly messages.

Security Note: Error messages may contain sensitive data from JIRA responses.
Use sanitize_error_message() before logging errors in production environments.
"""

from __future__ import annotations

import functools
import re
import sys
from collections.abc import Callable
from typing import Any

# Import base error classes and functions from the consolidated library
from assistant_skills_lib.error_handler import (
    AuthenticationError as BaseAuthenticationError,
)
from assistant_skills_lib.error_handler import (
    BaseAPIError,
)
from assistant_skills_lib.error_handler import ConflictError as BaseConflictError
from assistant_skills_lib.error_handler import NotFoundError as BaseNotFoundError
from assistant_skills_lib.error_handler import PermissionError as BasePermissionError
from assistant_skills_lib.error_handler import RateLimitError as BaseRateLimitError
from assistant_skills_lib.error_handler import ServerError as BaseServerError
from assistant_skills_lib.error_handler import ValidationError as BaseValidationError
from assistant_skills_lib.error_handler import handle_errors as base_handle_errors
from assistant_skills_lib.error_handler import print_error as base_print_error
from assistant_skills_lib.error_handler import (
    sanitize_error_message as base_sanitize_error_message,
)


class JiraError(BaseAPIError):
    """Base exception for all JIRA-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            response_data=response_data,
            **kwargs,
        )


class AuthenticationError(BaseAuthenticationError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        hint = "\n\nTroubleshooting:\n"
        hint += "  1. Verify JIRA_API_TOKEN is set correctly\n"
        hint += "  2. Check that your email matches your JIRA account\n"
        hint += "  3. Ensure the API token hasn't expired\n"
        hint += "  4. Get a new token at: https://id.atlassian.com/manage-profile/security/api-tokens"
        super().__init__(message + hint, **kwargs)


class PermissionError(BasePermissionError):
    """Raised when the user lacks permissions for an operation."""

    def __init__(self, message: str = "Permission denied", **kwargs: Any):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        hint = "\n\nTroubleshooting:\n"
        hint += "  1. Check your JIRA permissions for this project\n"
        hint += "  2. Verify you have the required role (e.g., Developer, Admin)\n"
        hint += "  3. Contact your JIRA administrator if access is needed"
        super().__init__(message + hint, **kwargs)


class ValidationError(BaseValidationError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        **kwargs: Any,
    ):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        self.field = field
        if field:
            message = f"{message} (field: {field})"
        super().__init__(message, **kwargs)


class NotFoundError(BaseNotFoundError):
    """Raised when a resource is not found."""

    def __init__(
        self, resource_type: str = "Resource", resource_id: str = "", **kwargs: Any
    ):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, **kwargs)


class RateLimitError(BaseRateLimitError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None, **kwargs: Any):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        message = "API rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        else:
            message += ". Please wait before retrying"
        # Pass retry_after to base class so it sets the attribute
        super().__init__(message, retry_after=retry_after, **kwargs)


class ConflictError(BaseConflictError):
    """Raised when there's a conflict (e.g., duplicate, concurrent modification)."""

    pass


class ServerError(BaseServerError):
    """Raised when the JIRA server encounters an error."""

    def __init__(self, message: str = "JIRA server error", **kwargs: Any):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        hint = "\n\nThe JIRA server encountered an error. Please try again later."
        super().__init__(message + hint, **kwargs)


# -----------------------------------------------------------------------------
# Automation API Errors
# -----------------------------------------------------------------------------


class AutomationError(JiraError):  # Inherit from JiraError as it's Jira-specific
    """Base exception for Automation API errors."""

    def __init__(self, message: str = "Automation API error", **kwargs: Any):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        hint = "\n\nTroubleshooting:\n"
        hint += "  1. Verify you have Jira Administrator permissions\n"
        hint += "  2. Ensure the Cloud ID is correct\n"
        hint += "  3. Check API token scopes include 'manage:jira-automation'"
        super().__init__(message + hint, **kwargs)


class AutomationNotFoundError(AutomationError):
    """Raised when an automation rule or template is not found."""

    def __init__(
        self,
        resource_type: str = "Automation resource",
        resource_id: str = "",
        **kwargs: Any,
    ):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, **kwargs)


class AutomationPermissionError(AutomationError):
    """Raised when the user lacks permissions for automation management."""

    def __init__(self, message: str = "Automation permission denied", **kwargs: Any):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        hint = "\n\nTroubleshooting:\n"
        hint += "  1. You need Jira Administrator permission for full rule management\n"
        hint += "  2. Project Administrator is needed for project-scoped rules\n"
        hint += "  3. Ensure API token has 'manage:jira-automation' scope"
        super().__init__(message + hint, **kwargs)


class AutomationValidationError(AutomationError):
    """Raised when automation rule configuration is invalid."""

    def __init__(
        self,
        message: str = "Automation validation failed",
        field: str | None = None,
        **kwargs: Any,
    ):
        # Remove 'message' from kwargs if present to avoid duplicate argument
        kwargs.pop("message", None)
        self.field = field
        if field:
            message = f"{message} (field: {field})"
        super().__init__(message, **kwargs)


def handle_jira_error(response: Any, operation: str = "operation") -> None:
    """
    Handle HTTP response errors and raise appropriate exceptions.

    Args:
        response: requests.Response object
        operation: Description of the operation being performed

    Raises:
        Appropriate JiraError subclass based on status code
    """
    if response.ok:
        return

    status_code = response.status_code

    try:
        error_data = response.json()
        error_messages = error_data.get("errorMessages", [])
        errors = error_data.get("errors", {})

        if error_messages:
            message = "; ".join(error_messages)
        elif errors:
            message = "; ".join([f"{k}: {v}" for k, v in errors.items()])
        else:
            message = error_data.get("message", response.text or "Unknown error")
    except ValueError:
        message = response.text or f"HTTP {status_code} error"
        error_data = {}

    message = f"Failed to {operation}: {message}"

    error_kwargs = {
        "message": message,
        "status_code": status_code,
        "response_data": error_data,
        "operation": operation,
    }

    if status_code == 400:
        raise ValidationError(**error_kwargs)
    elif status_code == 401:
        raise AuthenticationError(**error_kwargs)
    elif status_code == 403:
        raise PermissionError(**error_kwargs)
    elif status_code == 404:
        raise NotFoundError(
            resource_type="Resource", resource_id="", **error_kwargs
        )  # Resource specific info added
    elif status_code == 409:
        raise ConflictError(**error_kwargs)
    elif status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            retry_after=int(retry_after) if retry_after else None, **error_kwargs
        )
    elif status_code >= 500:
        raise ServerError(**error_kwargs)
    else:
        raise JiraError(**error_kwargs)


def sanitize_error_message(message: str) -> str:
    """
    Sanitize error messages to remove potentially sensitive information.

    Calls the base sanitizer and then applies JIRA-specific redactions.

    Args:
        message: Raw error message

    Returns:
        Sanitized error message safe for production logging
    """
    if not message:
        return message

    sanitized = base_sanitize_error_message(message)

    # Redact Atlassian account IDs (24-character hex strings)
    sanitized = re.sub(
        r"[0-9a-f]{24}", "[ACCOUNT_ID REDACTED]", sanitized, flags=re.IGNORECASE
    )

    # Redact longer UUIDs/tokens (32+ chars of hex)
    sanitized = re.sub(
        r"[0-9a-f]{32,}", "[TOKEN REDACTED]", sanitized, flags=re.IGNORECASE
    )

    # Redact API tokens (typical formats: ATATT, etc.)
    sanitized = re.sub(r"(ATATT[A-Za-z0-9+/=]+)", "[API_TOKEN REDACTED]", sanitized)

    return sanitized


def print_error(error: Exception, debug: bool = False) -> None:
    """
    Print error message to stderr with optional debug information.

    Uses the base print_error function and provides Jira-specific hints.

    Args:
        error: Exception to print
        debug: If True, include full stack trace
    """
    extra_hints = {
        AuthenticationError: "Check your JIRA_EMAIL and JIRA_API_TOKEN. Get a token at: https://id.atlassian.com/manage-profile/security/api-tokens",
        PermissionError: "Verify your JIRA permissions for this operation or project.",
        AutomationError: "Verify JIRA Administrator permissions and API token scopes for 'manage:jira-automation'.",
    }

    # Adapt debug for show_traceback in base_print_error
    show_traceback = debug and hasattr(error, "__traceback__")

    # Pass the sanitized error message and specific hints to the base print_error
    base_print_error(
        message=f"Jira Error: {error.message if isinstance(error, BaseAPIError) else str(error)}",
        error=error,
        show_traceback=show_traceback,
        extra_hints=extra_hints,
    )
    if isinstance(error, JiraError) and error.response_data:
        response_str = sanitize_error_message(str(error.response_data))
        print(f"\nResponse data: {response_str}", file=sys.stderr)


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in CLI scripts.

    Catches JIRA-specific exceptions and prints user-friendly error messages,
    and exits with appropriate status codes.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function with error handling
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except JiraError as e:
            print_error(e)
            sys.exit(1)
        except Exception:
            # Re-raise unexpected exceptions to be caught by base_handle_errors
            raise

    # Wrap Jira's custom handler with the base handler to catch generic exceptions
    return base_handle_errors(wrapper)

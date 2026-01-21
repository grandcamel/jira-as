"""
CLI utilities for jira-as commands.

Provides common patterns for Click commands:
- Client context management
- Parsing utilities (comma-separated lists, JSON)
- Error handling decorator
- Output formatting helpers
- Validators for Click callbacks
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast

import click

from jira_as import (
    AuthenticationError,
    ConflictError,
    JiraError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServerError,
    ValidationError,
    get_jira_client,
    print_error,
)

if TYPE_CHECKING:
    from jira_as import JiraClient

F = TypeVar("F", bound=Callable[..., Any])


def get_client_from_context(ctx: click.Context) -> "JiraClient":
    """Get or create a shared JiraClient from the Click context.

    This provides a single client instance shared across all commands in a CLI
    invocation, improving performance and testability.

    Args:
        ctx: Click context object

    Returns:
        Shared JiraClient instance
    """
    ctx.ensure_object(dict)
    if ctx.obj.get("_client") is None:
        ctx.obj["_client"] = get_jira_client()
    return cast("JiraClient", ctx.obj["_client"])


def parse_comma_list(value: str | None) -> list[str] | None:
    """
    Parse a comma-separated string into a list.

    Args:
        value: Comma-separated string or None

    Returns:
        List of stripped strings, or None if input is None/empty/whitespace

    Example:
        parse_comma_list("a, b, c") -> ["a", "b", "c"]
        parse_comma_list(None) -> None
    """
    if not value or not value.strip():
        return None
    result = [item.strip() for item in value.split(",") if item.strip()]
    return result if result else None


# Maximum JSON input size (1 MB) to prevent DoS via large payloads
MAX_JSON_SIZE = 1024 * 1024


def parse_json_arg(
    value: str | None, max_size: int = MAX_JSON_SIZE
) -> dict[str, Any] | None:
    """
    Parse a JSON string argument into a dict with size limit.

    Args:
        value: JSON string or None
        max_size: Maximum allowed JSON size in bytes (default 1 MB)

    Returns:
        Parsed dict, or None if input is None/empty

    Raises:
        click.BadParameter: If JSON is invalid or size exceeds limit
    """
    if not value:
        return None
    if len(value) > max_size:
        raise click.BadParameter(
            f"JSON too large ({len(value):,} bytes, max {max_size:,} bytes)"
        )
    try:
        return cast(dict[str, Any], json.loads(value))
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {e}") from e


def handle_jira_errors(func: F) -> F:
    """Decorator to handle exceptions in CLI commands.

    Catches JiraError exceptions and prints user-friendly error messages,
    then exits with appropriate exit codes.

    Exit codes:
        1 - Validation error or generic error
        2 - Authentication error
        3 - Permission denied
        4 - Resource not found
        5 - Rate limit exceeded
        6 - Conflict error
        7 - Server error
        130 - User interrupt (Ctrl+C)

    Example:
        @issue.command(name="get")
        @click.argument("issue_key")
        @click.pass_context
        @handle_jira_errors
        def get_issue(ctx, issue_key):
            result = _get_issue_impl(issue_key)
            click.echo(format_issue(result))
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except click.exceptions.Exit:
            # Normal exit, re-raise
            raise
        except click.BadParameter:
            # Let Click handle bad parameter errors
            raise
        except ValidationError as e:
            print_error(e)
            raise click.exceptions.Exit(1)
        except AuthenticationError as e:
            print_error(e)
            raise click.exceptions.Exit(2)
        except PermissionError as e:
            print_error(e)
            raise click.exceptions.Exit(3)
        except NotFoundError as e:
            print_error(e)
            raise click.exceptions.Exit(4)
        except RateLimitError as e:
            print_error(e)
            raise click.exceptions.Exit(5)
        except ConflictError as e:
            print_error(e)
            raise click.exceptions.Exit(6)
        except ServerError as e:
            print_error(e)
            raise click.exceptions.Exit(7)
        except JiraError as e:
            print_error(e)
            raise click.exceptions.Exit(1)
        except KeyboardInterrupt:
            click.echo("\nOperation cancelled", err=True)
            raise click.exceptions.Exit(130)
        except Exception as e:
            print_error(e, debug=True)
            raise click.exceptions.Exit(1)

    return wrapper  # type: ignore[return-value]


def format_json_output(data: Any) -> str:
    """
    Format data as pretty-printed JSON.

    Args:
        data: Data to format

    Returns:
        JSON string with 2-space indentation
    """
    return json.dumps(data, indent=2, default=str)


# Alias for convenience
format_json = format_json_output


def get_output_format(ctx: click.Context, explicit_output: str | None = None) -> str:
    """
    Get output format from explicit option or context.

    Args:
        ctx: Click context
        explicit_output: Explicitly specified output format

    Returns:
        Output format string ("text", "json", or "table")
    """
    if explicit_output:
        return explicit_output
    return ctx.obj.get("OUTPUT", "text") if ctx.obj else "text"


def validate_positive_int(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    """Click callback to validate positive integers.

    Args:
        ctx: Click context
        param: Click parameter
        value: Integer value to validate

    Returns:
        Validated integer or None

    Raises:
        click.BadParameter: If value is not positive
    """
    if value is not None and value <= 0:
        raise click.BadParameter("must be a positive integer")
    return value


def validate_non_negative_int(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    """Click callback to validate non-negative integers.

    Args:
        ctx: Click context
        param: Click parameter
        value: Integer value to validate

    Returns:
        Validated integer or None

    Raises:
        click.BadParameter: If value is negative
    """
    if value is not None and value < 0:
        raise click.BadParameter("must be a non-negative integer")
    return value


def output_results(
    data: Any,
    output_format: str = "text",
    columns: list[str] | None = None,
    success_msg: str | None = None,
) -> None:
    """Output results in the specified format.

    Args:
        data: Results to output (list of dicts, dict, or string)
        output_format: One of "json", "text", "table"
        columns: Column names for table output
        success_msg: Optional success message for text output
    """
    from jira_as import (
        format_json,
        format_table,
        print_success,
    )

    if output_format == "json":
        click.echo(format_json(data))
    elif output_format == "table":
        if isinstance(data, list) and data:
            click.echo(format_table(data, columns=columns))
        else:
            click.echo(format_json(data))
    else:
        if isinstance(data, list) and data:
            click.echo(format_table(data, columns=columns))
        elif isinstance(data, dict):
            click.echo(format_json(data))
        elif data:
            click.echo(data)
        if success_msg:
            print_success(success_msg)


__all__ = [
    "MAX_JSON_SIZE",
    "format_json",
    "format_json_output",
    "get_client_from_context",
    "get_output_format",
    "handle_jira_errors",
    "output_results",
    "parse_comma_list",
    "parse_json_arg",
    "validate_non_negative_int",
    "validate_positive_int",
]

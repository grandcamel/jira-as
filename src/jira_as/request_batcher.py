"""
Request batching layer for JIRA API operations.

Provides efficient batching of multiple API requests for parallel
execution with configurable concurrency limits.

Features:
- Collect multiple requests for batch execution
- Parallel execution with max concurrency limit
- Progress reporting via callback
- Partial failure handling (one error doesn't stop others)
- Result mapping back to original request IDs
- Support for GET, POST, PUT, DELETE methods

This module re-exports the base request batching classes from assistant-skills-lib
with JIRA-specific error classes and convenience functions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Re-export base classes
from assistant_skills_lib import BatchError as BaseBatchError
from assistant_skills_lib import (
    BatchResult,
    RequestBatcher,
)

from .error_handler import JiraError

# For backward compatibility, re-export all symbols
__all__ = [
    "BatchResult",
    "BatchError",
    "RequestBatcher",
    "batch_fetch_issues",
]


class BatchError(JiraError):
    """
    Error during batch execution.

    Extends JiraError to maintain JIRA-specific error hierarchy.
    """

    def __init__(self, message: str = "Batch execution failed", **kwargs: Any):
        kwargs.pop("message", None)
        super().__init__(message, **kwargs)


def batch_fetch_issues(
    client: Any,
    issue_keys: list[str],
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """
    Convenience function to fetch multiple JIRA issues in batch.

    Args:
        client: JiraClient instance
        issue_keys: List of issue keys to fetch
        progress_callback: Optional progress callback

    Returns:
        Dict mapping issue keys to issue data (or error)
    """
    batcher = RequestBatcher(client)
    key_to_id: dict[str, str] = {}

    for key in issue_keys:
        request_id = batcher.add("GET", f"/rest/api/3/issue/{key}")
        key_to_id[key] = request_id

    results = batcher.execute_sync(progress_callback)

    # Map back to issue keys
    issues: dict[str, Any] = {}
    for key, request_id in key_to_id.items():
        result = results.get(request_id)
        if result and result.success:
            issues[key] = result.data
        else:
            issues[key] = {"error": result.error if result else "Unknown error"}

    return issues

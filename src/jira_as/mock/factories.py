"""
Shared factories for building mock JIRA API responses.

Consolidates common patterns used across mock mixins to reduce duplication
and ensure consistent response structures.
"""

from __future__ import annotations

from typing import Any


class ResponseFactory:
    """Build standard API response structures."""

    @staticmethod
    def paginated(
        items: list[Any],
        start_at: int = 0,
        max_results: int = 50,
        format: str = "standard",
    ) -> dict[str, Any]:
        """
        Create a paginated response.

        Args:
            items: Full list of items to paginate
            start_at: Starting index
            max_results: Maximum results per page
            format: 'standard' for JIRA REST API, 'jsm' for Service Management API

        Returns:
            Paginated response dict
        """
        total = len(items)
        end_at = min(start_at + max_results, total)
        paginated = items[start_at:end_at]
        is_last = end_at >= total

        if format == "jsm":
            return {
                "size": len(paginated),
                "start": start_at,
                "limit": max_results,
                "isLastPage": is_last,
                "values": paginated,
            }

        # Standard JIRA REST API format
        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": total,
            "isLast": is_last,
            "values": paginated,
        }

    @staticmethod
    def paginated_issues(
        issues: list[dict[str, Any]],
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """
        Create a paginated response for issue search results.

        Uses 'issues' key instead of 'values'.
        """
        total = len(issues)
        end_at = min(start_at + max_results, total)
        paginated = issues[start_at:end_at]

        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": total,
            "issues": paginated,
        }


class URLFactory:
    """Build self URLs for JIRA resources."""

    @staticmethod
    def issue(base_url: str, issue_id: str) -> str:
        return f"{base_url}/rest/api/3/issue/{issue_id}"

    @staticmethod
    def project(base_url: str, project_key: str) -> str:
        return f"{base_url}/rest/api/3/project/{project_key}"

    @staticmethod
    def user(base_url: str, account_id: str) -> str:
        return f"{base_url}/rest/api/3/user?accountId={account_id}"

    @staticmethod
    def board(base_url: str, board_id: int | str) -> str:
        return f"{base_url}/rest/agile/1.0/board/{board_id}"

    @staticmethod
    def sprint(base_url: str, sprint_id: int | str) -> str:
        return f"{base_url}/rest/agile/1.0/sprint/{sprint_id}"

    @staticmethod
    def comment(base_url: str, issue_id: str, comment_id: str) -> str:
        return f"{base_url}/rest/api/3/issue/{issue_id}/comment/{comment_id}"

    @staticmethod
    def attachment(base_url: str, attachment_id: str) -> str:
        return f"{base_url}/rest/api/3/attachment/{attachment_id}"

    @staticmethod
    def worklog(base_url: str, issue_id: str, worklog_id: str) -> str:
        return f"{base_url}/rest/api/3/issue/{issue_id}/worklog/{worklog_id}"

    @staticmethod
    def filter(base_url: str, filter_id: str) -> str:
        return f"{base_url}/rest/api/3/filter/{filter_id}"

    @staticmethod
    def role(base_url: str, role_id: int | str) -> str:
        return f"{base_url}/rest/api/3/role/{role_id}"


class UserFactory:
    """Build user objects."""

    @staticmethod
    def full(
        account_id: str,
        display_name: str,
        email: str | None = None,
        active: bool = True,
    ) -> dict[str, Any]:
        """Create a full user object with all fields."""
        user = {
            "accountId": account_id,
            "displayName": display_name,
            "active": active,
        }
        if email:
            user["emailAddress"] = email
        return user

    @staticmethod
    def minimal(account_id: str, display_name: str) -> dict[str, Any]:
        """Create a minimal user object (for embedded references)."""
        return {
            "accountId": account_id,
            "displayName": display_name,
        }

    @staticmethod
    def unknown(account_id: str) -> dict[str, Any]:
        """Create a placeholder for unknown user."""
        return {
            "accountId": account_id,
            "displayName": "Unknown User",
        }


class TimestampFactory:
    """Build timestamp objects."""

    # Standard timestamp format used throughout mock
    DEFAULT_TIMESTAMP = "2025-01-01T10:00:00.000+0000"

    @staticmethod
    def standard(timestamp: str | None = None) -> str:
        """Return standard JIRA timestamp string."""
        return timestamp or TimestampFactory.DEFAULT_TIMESTAMP

    @staticmethod
    def jsm(timestamp: str | None = None) -> dict[str, str]:
        """Return JSM-style timestamp dict with iso8601 key."""
        ts = timestamp or "2025-01-01T10:00:00+0000"
        return {"iso8601": ts}


class CommentFactory:
    """Build comment objects."""

    @staticmethod
    def standard(
        comment_id: str,
        body: str | dict[str, Any],
        author: dict[str, Any],
        created: str | None = None,
        updated: str | None = None,
    ) -> dict[str, Any]:
        """Create a standard JIRA comment."""
        ts = TimestampFactory.standard(created)
        return {
            "id": comment_id,
            "body": body,
            "author": author,
            "created": ts,
            "updated": updated or ts,
        }

    @staticmethod
    def jsm(
        comment_id: str,
        body: str | dict[str, Any],
        author: dict[str, Any],
        public: bool = True,
        created: str | None = None,
    ) -> dict[str, Any]:
        """Create a JSM request comment."""
        return {
            "id": comment_id,
            "body": body,
            "public": public,
            "author": author,
            "created": TimestampFactory.jsm(created),
        }


class StatusFactory:
    """Build status objects."""

    @staticmethod
    def build(name: str, status_id: str) -> dict[str, Any]:
        """Create a status object."""
        return {"name": name, "id": status_id}

    @staticmethod
    def with_category(
        name: str, status_id: str, category: str = "TODO"
    ) -> dict[str, Any]:
        """Create a status with category info."""
        return {
            "name": name,
            "id": status_id,
            "statusCategory": {"name": category, "key": category.lower()},
        }

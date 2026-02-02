"""Collaborate mixin for MockJiraClient.

Provides mock implementations for watchers, changelog, attachments, and notifications.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class CollaborateMixin(_Base):
    """Mixin providing collaboration functionality.

    Assumes base class provides:
        - self._issues: Dict[str, Dict]
        - self.base_url: str
        - self.USERS: Dict[str, Dict]
    """

    # =========================================================================
    # Instance State
    # =========================================================================

    def _ensure_watchers_state(self):
        """Ensure _watchers dict exists."""
        if not hasattr(self, "_watchers"):
            self._watchers: dict[str, list[dict]] = {}

    def _ensure_attachments_state(self):
        """Ensure _attachments dict exists."""
        if not hasattr(self, "_attachments"):
            self._attachments: dict[str, list[dict]] = {}

    # =========================================================================
    # Watcher Operations
    # =========================================================================

    def get_watchers(self, issue_key: str) -> dict[str, Any]:
        """Get watchers for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            Dictionary containing watcher count and list.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_watchers_state()

        self._verify_issue_exists(issue_key)

        watchers = self._watchers.get(issue_key, [])

        # Include reporter by default as a watcher
        if not watchers:
            reporter = self._issues[issue_key]["fields"].get("reporter")
            if reporter:
                watchers = [reporter]

        return {
            "self": f"{self.base_url}/rest/api/3/issue/{issue_key}/watchers",
            "isWatching": True,
            "watchCount": len(watchers),
            "watchers": watchers,
        }

    def add_watcher(self, issue_key: str, account_id: str) -> None:
        """Add a watcher to an issue.

        Args:
            issue_key: The issue key.
            account_id: The account ID to add as watcher.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_watchers_state()

        self._verify_issue_exists(issue_key)

        if issue_key not in self._watchers:
            self._watchers[issue_key] = []

        # Get user info
        user = self.USERS.get(
            account_id,
            {
                "accountId": account_id,
                "displayName": "Unknown User",
            },
        )

        # Avoid duplicates
        if not any(w.get("accountId") == account_id for w in self._watchers[issue_key]):
            self._watchers[issue_key].append(user)

    def remove_watcher(self, issue_key: str, account_id: str) -> None:
        """Remove a watcher from an issue.

        Args:
            issue_key: The issue key.
            account_id: The account ID to remove.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_watchers_state()

        self._verify_issue_exists(issue_key)

        if issue_key in self._watchers:
            self._watchers[issue_key] = [
                w for w in self._watchers[issue_key] if w.get("accountId") != account_id
            ]

    # =========================================================================
    # Changelog Operations
    # =========================================================================

    def get_changelog(
        self,
        issue_key: str,
        start_at: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Get changelog for an issue.

        Args:
            issue_key: The issue key.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of changelog entries.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        # Return mock changelog
        changelog = [
            {
                "id": "10001",
                "author": self.USERS["abc123"],
                "created": "2025-01-01T10:00:00.000+0000",
                "items": [
                    {
                        "field": "status",
                        "fieldtype": "jira",
                        "from": None,
                        "fromString": None,
                        "to": "10000",
                        "toString": "To Do",
                    }
                ],
            },
            {
                "id": "10002",
                "author": self.USERS["abc123"],
                "created": "2025-01-02T10:00:00.000+0000",
                "items": [
                    {
                        "field": "assignee",
                        "fieldtype": "jira",
                        "from": None,
                        "fromString": None,
                        "to": "abc123",
                        "toString": "Jason Krueger",
                    }
                ],
            },
        ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(changelog, start_at, max_results)

    def get_issue_with_changelog(
        self,
        issue_key: str,
        fields: str | None = None,
    ) -> dict[str, Any]:
        """Get issue with full changelog.

        Args:
            issue_key: The issue key.
            fields: Fields to include.

        Returns:
            Issue with changelog expanded.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        issue = dict(self._issues[issue_key])
        issue["changelog"] = self.get_changelog(issue_key)

        return issue

    # =========================================================================
    # Attachment Operations
    # =========================================================================

    def get_attachments(self, issue_key: str) -> list[dict[str, Any]]:
        """Get attachments for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of attachments.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_attachments_state()

        self._verify_issue_exists(issue_key)

        return self._attachments.get(issue_key, [])

    def add_attachment(
        self,
        issue_key: str,
        filename: str,
        content: bytes | None = None,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """Add an attachment to an issue.

        Args:
            issue_key: The issue key.
            filename: The filename.
            content: File content (not used in mock).
            content_type: MIME type of the file.

        Returns:
            The created attachment.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_attachments_state()

        self._verify_issue_exists(issue_key)

        if issue_key not in self._attachments:
            self._attachments[issue_key] = []

        attachment_id = str(len(self._attachments[issue_key]) + 1)
        attachment = {
            "id": attachment_id,
            "filename": filename,
            "author": self.USERS["abc123"],
            "created": "2025-01-08T10:00:00.000+0000",
            "size": len(content) if content else 0,
            "mimeType": content_type,
            "content": f"{self.base_url}/secure/attachment/{attachment_id}/{filename}",
        }

        self._attachments[issue_key].append(attachment)
        return attachment

    def delete_attachment(self, attachment_id: str) -> None:
        """Delete an attachment.

        Args:
            attachment_id: The attachment ID.
        """
        self._ensure_attachments_state()

        for issue_key in list(self._attachments.keys()):
            self._attachments[issue_key] = [
                a for a in self._attachments[issue_key] if a["id"] != attachment_id
            ]

    def get_attachment(self, attachment_id: str) -> dict[str, Any]:
        """Get attachment metadata.

        Args:
            attachment_id: The attachment ID.

        Returns:
            Attachment metadata.

        Raises:
            NotFoundError: If the attachment is not found.
        """
        self._ensure_attachments_state()

        for attachments in self._attachments.values():
            for attachment in attachments:
                if attachment["id"] == attachment_id:
                    return attachment

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Attachment {attachment_id} not found")

    # =========================================================================
    # Notification Operations
    # =========================================================================

    def notify_users(
        self,
        issue_key: str,
        subject: str,
        text_body: str | None = None,
        html_body: str | None = None,
        to: list[str] | None = None,
        restrict_groups: list[str] | None = None,
        restrict_permissions: list[str] | None = None,
    ) -> None:
        """Send notification about an issue.

        Args:
            issue_key: The issue key.
            subject: Email subject.
            text_body: Plain text body.
            html_body: HTML body.
            to: List of account IDs to notify.
            restrict_groups: Groups to restrict notification to.
            restrict_permissions: Permissions to restrict notification to.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        # In mock, this is a no-op
        pass

    def get_notification_scheme(self, project_key: str) -> dict[str, Any]:
        """Get notification scheme for a project.

        Args:
            project_key: The project key.

        Returns:
            The notification scheme details.
        """
        return {
            "id": "10000",
            "name": "Default Notification Scheme",
            "description": "Default notification scheme for projects",
            "notificationSchemeEvents": [
                {
                    "event": {"id": "1", "name": "Issue Created"},
                    "notifications": [
                        {"type": "reporter"},
                        {"type": "currentAssignee"},
                        {"type": "watchers"},
                    ],
                },
                {
                    "event": {"id": "2", "name": "Issue Updated"},
                    "notifications": [
                        {"type": "reporter"},
                        {"type": "currentAssignee"},
                        {"type": "watchers"},
                    ],
                },
            ],
        }

    # =========================================================================
    # Activity Stream Operations
    # =========================================================================

    def get_issue_activity(
        self,
        issue_key: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get activity stream for an issue.

        Args:
            issue_key: The issue key.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated activity stream.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        # Combine changelog and comments into activity
        activities = []

        # Add changelog entries
        changelog = self.get_changelog(issue_key)
        for entry in changelog.get("values", []):
            activities.append(
                {
                    "type": "history",
                    "timestamp": entry["created"],
                    "author": entry["author"],
                    "changes": entry["items"],
                }
            )

        # Add comments
        comments = (
            self._comments.get(issue_key, []) if hasattr(self, "_comments") else []
        )
        for comment in comments:
            activities.append(
                {
                    "type": "comment",
                    "timestamp": comment.get("created"),
                    "author": comment.get("author"),
                    "body": comment.get("body"),
                }
            )

        # Sort by timestamp descending
        activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        paginated = activities[start_at : start_at + max_results]

        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(activities),
            "isLast": start_at + max_results >= len(activities),
            "activities": paginated,
        }

    # =========================================================================
    # Mention Operations
    # =========================================================================

    def get_user_mentions(
        self,
        issue_key: str | None = None,
        project_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get users that can be mentioned.

        Args:
            issue_key: Optional issue to filter by.
            project_key: Optional project to filter by.

        Returns:
            List of users available for mentions.
        """
        return list(self.USERS.values())

    # =========================================================================
    # Vote Operations
    # =========================================================================

    def get_votes(self, issue_key: str) -> dict[str, Any]:
        """Get votes for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            Vote information.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return {
            "self": f"{self.base_url}/rest/api/3/issue/{issue_key}/votes",
            "votes": 0,
            "hasVoted": False,
            "voters": [],
        }

    def add_vote(self, issue_key: str) -> None:
        """Add vote to an issue.

        Args:
            issue_key: The issue key.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)
        # In mock, this is a no-op

    def remove_vote(self, issue_key: str) -> None:
        """Remove vote from an issue.

        Args:
            issue_key: The issue key.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)
        # In mock, this is a no-op

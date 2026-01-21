"""Relationships mixin for MockJiraClient.

Provides mock implementations for issue links, dependencies, and cloning.
"""

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class RelationshipsMixin(_Base):
    """Mixin providing issue relationship functionality.

    Assumes base class provides:
        - self._issues: Dict[str, Dict]
        - self._next_issue_id: int
        - self.base_url: str
        - self.USERS: Dict[str, Dict]
    """

    # =========================================================================
    # Class Constants - Link Types
    # =========================================================================

    LINK_TYPES: ClassVar[list[dict[str, str]]] = [
        {
            "id": "10000",
            "name": "Blocks",
            "inward": "is blocked by",
            "outward": "blocks",
            "self": "https://mock.atlassian.net/rest/api/3/issueLinkType/10000",
        },
        {
            "id": "10001",
            "name": "Cloners",
            "inward": "is cloned by",
            "outward": "clones",
            "self": "https://mock.atlassian.net/rest/api/3/issueLinkType/10001",
        },
        {
            "id": "10002",
            "name": "Duplicate",
            "inward": "is duplicated by",
            "outward": "duplicates",
            "self": "https://mock.atlassian.net/rest/api/3/issueLinkType/10002",
        },
        {
            "id": "10003",
            "name": "Relates",
            "inward": "relates to",
            "outward": "relates to",
            "self": "https://mock.atlassian.net/rest/api/3/issueLinkType/10003",
        },
        {
            "id": "10004",
            "name": "Cause",
            "inward": "is caused by",
            "outward": "causes",
            "self": "https://mock.atlassian.net/rest/api/3/issueLinkType/10004",
        },
    ]

    # =========================================================================
    # Instance State - Issue Links
    # =========================================================================

    def _ensure_links_state(self):
        """Ensure _issue_links dict exists."""
        if not hasattr(self, "_issue_links"):
            self._issue_links: dict[str, list[dict]] = {}

    # =========================================================================
    # Link Type Operations
    # =========================================================================

    def get_issue_link_types(self) -> dict[str, Any]:
        """Get all issue link types.

        Returns:
            Dictionary containing list of issue link types.
        """
        return {
            "issueLinkTypes": self.LINK_TYPES,
        }

    def get_issue_link_type(self, link_type_id: str) -> dict[str, Any]:
        """Get an issue link type by ID.

        Args:
            link_type_id: The link type ID.

        Returns:
            The link type details.

        Raises:
            NotFoundError: If the link type is not found.
        """
        for lt in self.LINK_TYPES:
            if lt["id"] == link_type_id:
                return lt

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Link type {link_type_id} not found")

    # =========================================================================
    # Issue Link Operations
    # =========================================================================

    def create_issue_link(
        self,
        link_type: str,
        inward_issue: str,
        outward_issue: str,
        comment: dict[str, Any] | None = None,
    ) -> None:
        """Create a link between two issues.

        Args:
            link_type: Name of the link type.
            inward_issue: The inward issue key (is blocked by, etc.).
            outward_issue: The outward issue key (blocks, etc.).
            comment: Optional comment to add with the link.

        Raises:
            NotFoundError: If either issue is not found.
        """
        self._ensure_links_state()

        self._verify_issue_exists(inward_issue)
        self._verify_issue_exists(outward_issue)

        # Find link type
        link_type_obj = None
        for lt in self.LINK_TYPES:
            if lt["name"].lower() == link_type.lower():
                link_type_obj = lt
                break

        if not link_type_obj:
            # Use "Relates" as default
            link_type_obj = self.LINK_TYPES[3]

        # Create the link
        link_id = str(len(self._issue_links) + 1)
        link = {
            "id": link_id,
            "type": link_type_obj,
            "inwardIssue": {"key": inward_issue},
            "outwardIssue": {"key": outward_issue},
        }

        # Store link for both issues
        if inward_issue not in self._issue_links:
            self._issue_links[inward_issue] = []
        if outward_issue not in self._issue_links:
            self._issue_links[outward_issue] = []

        self._issue_links[inward_issue].append(link)
        self._issue_links[outward_issue].append(link)

    def get_issue_link(self, link_id: str) -> dict[str, Any]:
        """Get an issue link by ID.

        Args:
            link_id: The link ID.

        Returns:
            The link details.

        Raises:
            NotFoundError: If the link is not found.
        """
        self._ensure_links_state()

        for issue_links in self._issue_links.values():
            for link in issue_links:
                if link["id"] == link_id:
                    return link

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Link {link_id} not found")

    def delete_issue_link(self, link_id: str) -> None:
        """Delete an issue link.

        Args:
            link_id: The link ID to delete.

        Raises:
            NotFoundError: If the link is not found.
        """
        self._ensure_links_state()

        found = False
        for issue_key in list(self._issue_links.keys()):
            self._issue_links[issue_key] = [
                link
                for link in self._issue_links[issue_key]
                if link["id"] != link_id or not (found := True)
            ]

        if not found:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Link {link_id} not found")

    def get_issue_links(self, issue_key: str) -> list[dict[str, Any]]:
        """Get all links for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of issue links.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_links_state()

        self._verify_issue_exists(issue_key)

        return self._issue_links.get(issue_key, [])

    # =========================================================================
    # Remote Link Operations
    # =========================================================================

    def get_remote_links(self, issue_key: str) -> list[dict[str, Any]]:
        """Get remote links for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of remote links.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        # Return mock remote links
        return [
            {
                "id": 10000,
                "self": f"{self.base_url}/rest/api/3/issue/{issue_key}/remotelink/10000",
                "globalId": f"system={self.base_url}&id=10000",
                "application": {
                    "type": "com.atlassian.confluence",
                    "name": "Confluence",
                },
                "relationship": "mentioned in",
                "object": {
                    "url": "https://confluence.example.com/pages/viewpage.action?pageId=12345",
                    "title": "Related Confluence Page",
                },
            }
        ]

    def create_remote_link(
        self,
        issue_key: str,
        url: str,
        title: str,
        relationship: str | None = None,
        icon_url: str | None = None,
        icon_title: str | None = None,
    ) -> dict[str, Any]:
        """Create a remote link for an issue.

        Args:
            issue_key: The issue key.
            url: The URL of the remote link.
            title: The title of the link.
            relationship: Relationship type (e.g., "mentioned in").
            icon_url: URL for the link icon.
            icon_title: Title for the icon.

        Returns:
            The created remote link.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return {
            "id": 10001,
            "self": f"{self.base_url}/rest/api/3/issue/{issue_key}/remotelink/10001",
        }

    def delete_remote_link(self, issue_key: str, link_id: str) -> None:
        """Delete a remote link.

        Args:
            issue_key: The issue key.
            link_id: The remote link ID.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)
        # In mock, this is a no-op

    # =========================================================================
    # Clone Operations
    # =========================================================================

    def clone_issue(
        self,
        issue_key: str,
        summary: str | None = None,
        project_key: str | None = None,
        include_links: bool = False,
        include_attachments: bool = False,
        include_subtasks: bool = False,
    ) -> dict[str, Any]:
        """Clone an issue.

        Args:
            issue_key: The issue key to clone.
            summary: New summary (defaults to "Clone of <original>").
            project_key: Target project (defaults to same project).
            include_links: Whether to clone issue links.
            include_attachments: Whether to clone attachments.
            include_subtasks: Whether to clone subtasks.

        Returns:
            The cloned issue.

        Raises:
            NotFoundError: If the source issue is not found.
        """
        self._verify_issue_exists(issue_key)

        source = self._issues[issue_key]
        source_fields = source["fields"]

        # Determine target project
        target_project = project_key or source_fields["project"]["key"]

        # Create cloned issue fields
        clone_fields = {
            "project": {"key": target_project},
            "summary": summary or f"Clone of {source_fields['summary']}",
            "description": source_fields.get("description"),
            "issuetype": source_fields.get("issuetype"),
            "priority": source_fields.get("priority"),
            "labels": source_fields.get("labels", []),
        }

        # Create the cloned issue
        result = self.create_issue(clone_fields)

        # Create "clones" link if requested
        if include_links:
            self._ensure_links_state()
            self.create_issue_link("Cloners", result["key"], issue_key)

        return result

    # =========================================================================
    # Dependency Analysis Operations
    # =========================================================================

    def get_blockers(
        self, issue_key: str, recursive: bool = False
    ) -> list[dict[str, Any]]:
        """Get issues that block this issue.

        Args:
            issue_key: The issue key.
            recursive: Whether to get blockers recursively.

        Returns:
            List of blocking issues.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_links_state()

        self._verify_issue_exists(issue_key)

        blockers = []
        links = self._issue_links.get(issue_key, [])

        for link in links:
            if link["type"]["name"] == "Blocks":
                # If this issue is the inward issue, the outward issue blocks it
                if link["inwardIssue"]["key"] == issue_key:
                    blocker_key = link["outwardIssue"]["key"]
                    if blocker_key in self._issues:
                        blockers.append(self._issues[blocker_key])

                        if recursive:
                            # Get blockers of blockers
                            blockers.extend(
                                self.get_blockers(blocker_key, recursive=True)
                            )

        return blockers

    def get_blocked_by(
        self, issue_key: str, recursive: bool = False
    ) -> list[dict[str, Any]]:
        """Get issues that are blocked by this issue.

        Args:
            issue_key: The issue key.
            recursive: Whether to get blocked issues recursively.

        Returns:
            List of blocked issues.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_links_state()

        self._verify_issue_exists(issue_key)

        blocked = []
        links = self._issue_links.get(issue_key, [])

        for link in links:
            if link["type"]["name"] == "Blocks":
                # If this issue is the outward issue, it blocks the inward issue
                if link["outwardIssue"]["key"] == issue_key:
                    blocked_key = link["inwardIssue"]["key"]
                    if blocked_key in self._issues:
                        blocked.append(self._issues[blocked_key])

                        if recursive:
                            blocked.extend(
                                self.get_blocked_by(blocked_key, recursive=True)
                            )

        return blocked

    def get_related_issues(
        self, issue_key: str, link_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all related issues.

        Args:
            issue_key: The issue key.
            link_type: Optional filter by link type name.

        Returns:
            List of related issues.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._ensure_links_state()

        self._verify_issue_exists(issue_key)

        related = []
        links = self._issue_links.get(issue_key, [])

        for link in links:
            if link_type and link["type"]["name"].lower() != link_type.lower():
                continue

            # Get the other issue in the link
            if link["inwardIssue"]["key"] == issue_key:
                other_key = link["outwardIssue"]["key"]
            else:
                other_key = link["inwardIssue"]["key"]

            if other_key in self._issues:
                related.append(
                    {
                        "issue": self._issues[other_key],
                        "linkType": link["type"],
                        "direction": (
                            "outward"
                            if link["inwardIssue"]["key"] == issue_key
                            else "inward"
                        ),
                    }
                )

        return related

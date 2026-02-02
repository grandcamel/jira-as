"""Base mock JIRA client with core functionality.

Contains MockJiraClientBase with essential issue, user, project, and transition
operations that other mixins build upon.
"""

import os
from typing import Any, ClassVar


def is_mock_mode() -> bool:
    """Check if JIRA mock mode is enabled.

    Returns:
        True if JIRA_MOCK_MODE environment variable is set to 'true'.
    """
    return os.environ.get("JIRA_MOCK_MODE", "").lower() == "true"


class MockJiraClientBase:
    """Base mock client with core JIRA operations.

    Provides seed data for DEMO and DEMOSD projects, along with essential
    methods for issue CRUD, transitions, comments, worklogs, users, and projects.

    Mixins extend this class to add specialized functionality.
    """

    # =========================================================================
    # Class Constants - Users
    # =========================================================================

    USERS: ClassVar[dict[str, dict[str, Any]]] = {
        "abc123": {
            "accountId": "abc123",
            "displayName": "Jason Krueger",
            "emailAddress": "jasonkrue@gmail.com",
            "active": True,
        },
        "def456": {
            "accountId": "def456",
            "displayName": "Jane Manager",
            "emailAddress": "jane@example.com",
            "active": True,
        },
    }

    # =========================================================================
    # Class Constants - Projects
    # =========================================================================

    PROJECTS: ClassVar[list[dict[str, str]]] = [
        {
            "key": "DEMO",
            "name": "Demo Project",
            "id": "10000",
            "projectTypeKey": "software",
            "style": "classic",
        },
        {
            "key": "DEMOSD",
            "name": "Demo Service Desk",
            "id": "10001",
            "projectTypeKey": "service_desk",
            "style": "classic",
        },
    ]

    # =========================================================================
    # Class Constants - Transitions
    # =========================================================================

    TRANSITIONS: ClassVar[list[dict[str, Any]]] = [
        {"id": "11", "name": "To Do", "to": {"name": "To Do", "id": "10000"}},
        {
            "id": "21",
            "name": "In Progress",
            "to": {"name": "In Progress", "id": "10001"},
        },
        {"id": "31", "name": "Done", "to": {"name": "Done", "id": "10002"}},
    ]

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(
        self,
        base_url: str = "https://mock.atlassian.net",
        email: str = "test@example.com",
        api_token: str = "mock-token",
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ):
        """Initialize mock client with optional parameters for interface compatibility.

        Args:
            base_url: Base URL for JIRA instance (used in response URLs).
            email: User email (for interface compatibility).
            api_token: API token (for interface compatibility).
            timeout: Request timeout in seconds (for interface compatibility).
            max_retries: Number of retries (for interface compatibility).
            retry_backoff: Backoff multiplier (for interface compatibility).
        """
        self.base_url = base_url
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Initialize mutable state
        self._next_issue_id = 100
        self._issues = self._init_issues()
        self._comments: dict[str, list[dict]] = {}
        self._worklogs: dict[str, list[dict]] = {}

    # =========================================================================
    # Verification Helpers
    # =========================================================================

    def _verify_issue_exists(self, issue_key: str) -> dict[str, Any]:
        """Verify issue exists and return it, or raise NotFoundError.

        Args:
            issue_key: The issue key to verify.

        Returns:
            The issue dict if found.

        Raises:
            NotFoundError: If the issue is not found.
        """
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError

            raise NotFoundError(f"Issue {issue_key} not found")
        return self._issues[issue_key]

    def _verify_project_exists(self, project_key: str) -> dict[str, Any]:
        """Verify project exists and return it, or raise NotFoundError.

        Args:
            project_key: The project key to verify.

        Returns:
            The project dict if found.

        Raises:
            NotFoundError: If the project is not found.
        """
        for project in self.PROJECTS:
            if project["key"] == project_key:
                return project
        from ..error_handler import NotFoundError

        raise NotFoundError(f"Project {project_key} not found")

    # =========================================================================
    # Issue Factory Methods
    # =========================================================================

    def _make_issue(
        self,
        key: str,
        issue_id: str,
        summary: str,
        issuetype: dict[str, str],
        status: dict[str, str],
        priority: dict[str, str],
        assignee: dict[str, Any] | None,
        reporter: dict[str, Any],
        project: dict[str, str],
        description: dict[str, Any] | None = None,
        labels: list[str] | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Factory method to create an issue structure.

        Args:
            key: Issue key (e.g., 'DEMO-84')
            issue_id: Issue ID (e.g., '10084')
            summary: Issue summary
            issuetype: Issue type dict with name and id
            status: Status dict with name and id
            priority: Priority dict with name and id
            assignee: Assignee user dict or None
            reporter: Reporter user dict
            project: Project dict with key, name, id
            description: Optional ADF description
            labels: Labels list (default: ['demo'])
            **extra_fields: Additional top-level fields (e.g., requestTypeId)

        Returns:
            Complete issue dictionary
        """
        issue = {
            "key": key,
            "id": issue_id,
            "self": f"{self.base_url}/rest/api/3/issue/{issue_id}",
            "fields": {
                "summary": summary,
                "description": description,
                "issuetype": issuetype,
                "status": status,
                "priority": priority,
                "assignee": assignee,
                "reporter": reporter,
                "project": project,
                "created": "2025-01-01T10:00:00.000+0000",
                "updated": "2025-01-01T10:00:00.000+0000",
                "labels": labels or ["demo"],
            },
        }
        # Add any extra top-level fields (for service desk issues)
        issue.update(extra_fields)
        return issue

    def _make_demo_issue(
        self,
        key: str,
        issue_id: str,
        summary: str,
        issuetype_name: str,
        issuetype_id: str,
        priority_name: str,
        priority_id: str,
        assignee_id: str | None,
        description: dict[str, Any] | None = None,
        reporter_id: str = "abc123",
    ) -> dict[str, Any]:
        """Factory for DEMO project issues."""
        return self._make_issue(
            key=key,
            issue_id=issue_id,
            summary=summary,
            issuetype={"name": issuetype_name, "id": issuetype_id},
            status={"name": "To Do", "id": "10000"},
            priority={"name": priority_name, "id": priority_id},
            assignee=self.USERS.get(assignee_id) if assignee_id else None,
            reporter={
                "accountId": reporter_id,
                "displayName": self.USERS[reporter_id]["displayName"],
            },
            project={"key": "DEMO", "name": "Demo Project", "id": "10000"},
            description=description,
        )

    def _make_sd_issue(
        self,
        key: str,
        issue_id: str,
        summary: str,
        description_text: str,
        issuetype_name: str,
        issuetype_id: str,
        priority_name: str,
        priority_id: str,
        reporter_id: str,
        request_type_id: str,
    ) -> dict[str, Any]:
        """Factory for DEMOSD service desk issues."""
        description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description_text}],
                }
            ],
        }
        return self._make_issue(
            key=key,
            issue_id=issue_id,
            summary=summary,
            issuetype={"name": issuetype_name, "id": issuetype_id},
            status={"name": "Waiting for support", "id": "10100"},
            priority={"name": priority_name, "id": priority_id},
            assignee=None,
            reporter=self.USERS[reporter_id],
            project={"key": "DEMOSD", "name": "Demo Service Desk", "id": "10001"},
            description=description,
            requestTypeId=request_type_id,
            serviceDeskId="1",
            currentStatus={"status": "Waiting for support", "statusCategory": "new"},
        )

    def _make_adf_description(self, text: str) -> dict[str, Any]:
        """Create an ADF description from plain text."""
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }

    def _init_issues(self) -> dict[str, dict]:
        """Initialize issue store with seed data matching DEMO project.

        Returns:
            Dictionary of issue key to issue data for DEMO-84 through DEMO-91
            and DEMOSD-1 through DEMOSD-5.
        """
        # DEMO project issues
        demo_issues = {
            "DEMO-84": self._make_demo_issue(
                "DEMO-84",
                "10084",
                "Product Launch",
                "Epic",
                "10000",
                "High",
                "2",
                "abc123",
                description=self._make_adf_description(
                    "Epic for product launch activities"
                ),
            ),
            "DEMO-85": self._make_demo_issue(
                "DEMO-85",
                "10085",
                "User Authentication",
                "Story",
                "10001",
                "High",
                "2",
                "abc123",
            ),
            "DEMO-86": self._make_demo_issue(
                "DEMO-86",
                "10086",
                "Login fails on mobile Safari",
                "Bug",
                "10002",
                "High",
                "2",
                "def456",
            ),
            "DEMO-87": self._make_demo_issue(
                "DEMO-87",
                "10087",
                "Update API documentation",
                "Task",
                "10003",
                "Medium",
                "3",
                "def456",
            ),
            "DEMO-91": self._make_demo_issue(
                "DEMO-91",
                "10091",
                "Search pagination bug",
                "Bug",
                "10002",
                "Medium",
                "3",
                "abc123",
                reporter_id="def456",
            ),
        }

        # DEMOSD service desk issues
        sd_issues = {
            "DEMOSD-1": self._make_sd_issue(
                "DEMOSD-1",
                "20001",
                "Can't connect to VPN",
                "I'm working from home and can't connect to the corporate VPN. Getting 'connection timeout' error.",
                "IT help",
                "10100",
                "Medium",
                "3",
                "abc123",
                "1",
            ),
            "DEMOSD-2": self._make_sd_issue(
                "DEMOSD-2",
                "20002",
                "New laptop for development",
                "Need a new development laptop with 32GB RAM and SSD.",
                "Computer support",
                "10101",
                "Medium",
                "3",
                "abc123",
                "2",
            ),
            "DEMOSD-3": self._make_sd_issue(
                "DEMOSD-3",
                "20003",
                "New hire starting Monday - Alex Chen",
                "Please set up accounts and equipment for new hire Alex Chen starting Monday.",
                "New employee",
                "10102",
                "High",
                "2",
                "def456",
                "3",
            ),
            "DEMOSD-4": self._make_sd_issue(
                "DEMOSD-4",
                "20004",
                "Conference travel to AWS re:Invent",
                "Requesting approval for travel to AWS re:Invent in Las Vegas.",
                "Travel request",
                "10103",
                "Medium",
                "3",
                "abc123",
                "4",
            ),
            "DEMOSD-5": self._make_sd_issue(
                "DEMOSD-5",
                "20005",
                "Purchase ergonomic keyboard",
                "Need to purchase an ergonomic keyboard for RSI prevention. Estimated cost: $150.",
                "Purchase over $100",
                "10104",
                "Low",
                "4",
                "abc123",
                "5",
            ),
        }

        return {**demo_issues, **sd_issues}

    # =========================================================================
    # Issue Operations
    # =========================================================================

    def get_issue(
        self, issue_key: str, fields: str | None = None, expand: str | None = None
    ) -> dict[str, Any]:
        """Get issue by key.

        Args:
            issue_key: The issue key (e.g., 'DEMO-84').
            fields: Comma-separated list of fields to return (for interface compatibility).
            expand: Fields to expand (for interface compatibility).

        Returns:
            The issue data.

        Raises:
            NotFoundError: If the issue is not found.
        """
        return self._verify_issue_exists(issue_key)

    def search_issues(
        self,
        jql: str,
        fields: list | None = None,
        max_results: int = 50,
        next_page_token: str | None = None,
        start_at: int | None = 0,
        expand: str | None = None,
    ) -> dict[str, Any]:
        """Search issues with JQL. Supports basic project and assignee filtering.

        Args:
            jql: JQL query string.
            fields: List of fields to return (for API parity).
            max_results: Maximum number of results to return.
            next_page_token: Pagination token (ignored in mock, for API compatibility).
            start_at: Starting index for pagination (deprecated, use next_page_token).
            expand: Fields to expand.

        Returns:
            Search results with pagination info and matching issues.
        """
        issues = list(self._issues.values())
        jql_upper = jql.upper()

        # Filter by project - check DEMOSD first to avoid matching DEMO prefix
        if "PROJECT = DEMOSD" in jql_upper or "PROJECT=DEMOSD" in jql_upper:
            issues = [i for i in issues if i["key"].startswith("DEMOSD-")]
        elif "PROJECT = DEMO" in jql_upper or "PROJECT=DEMO" in jql_upper:
            # Filter DEMO but exclude DEMOSD
            issues = [
                i
                for i in issues
                if i["key"].startswith("DEMO-") and not i["key"].startswith("DEMOSD-")
            ]

        # Filter by assignee
        if "ASSIGNEE" in jql_upper:
            jql_lower = jql.lower()
            if "jane" in jql_lower:
                issues = [
                    i
                    for i in issues
                    if i["fields"].get("assignee")
                    and i["fields"]["assignee"].get("displayName", "").lower()
                    == "jane manager"
                ]
            elif "jason" in jql_lower:
                issues = [
                    i
                    for i in issues
                    if i["fields"].get("assignee")
                    and i["fields"]["assignee"].get("displayName", "").lower()
                    == "jason krueger"
                ]

        # Filter by issue type
        if "ISSUETYPE = BUG" in jql_upper or "ISSUETYPE=BUG" in jql_upper:
            issues = [i for i in issues if i["fields"]["issuetype"]["name"] == "Bug"]
        elif "ISSUETYPE = STORY" in jql_upper or "ISSUETYPE=STORY" in jql_upper:
            issues = [i for i in issues if i["fields"]["issuetype"]["name"] == "Story"]
        elif "ISSUETYPE = EPIC" in jql_upper or "ISSUETYPE=EPIC" in jql_upper:
            issues = [i for i in issues if i["fields"]["issuetype"]["name"] == "Epic"]
        elif "ISSUETYPE = TASK" in jql_upper or "ISSUETYPE=TASK" in jql_upper:
            issues = [i for i in issues if i["fields"]["issuetype"]["name"] == "Task"]

        # Filter by status
        if 'STATUS = "IN PROGRESS"' in jql_upper or 'STATUS="IN PROGRESS"' in jql_upper:
            issues = [
                i for i in issues if i["fields"]["status"]["name"] == "In Progress"
            ]
        elif 'STATUS = "TO DO"' in jql_upper or 'STATUS="TO DO"' in jql_upper:
            issues = [i for i in issues if i["fields"]["status"]["name"] == "To Do"]

        # Filter by reporter
        if "REPORTER" in jql_upper:
            jql_lower = jql.lower()
            if "jane" in jql_lower:
                issues = [
                    i
                    for i in issues
                    if i["fields"].get("reporter", {}).get("displayName", "").lower()
                    == "jane manager"
                ]
            elif "jason" in jql_lower:
                issues = [
                    i
                    for i in issues
                    if i["fields"].get("reporter", {}).get("displayName", "").lower()
                    == "jason krueger"
                ]

        # Text search (text ~ "keyword")
        import re

        text_match = re.search(r'TEXT\s*~\s*["\']([^"\']+)["\']', jql, re.IGNORECASE)
        if text_match:
            search_term = text_match.group(1).lower()
            issues = [
                i
                for i in issues
                if search_term in i["fields"].get("summary", "").lower()
            ]

        # Pagination
        from .factories import ResponseFactory

        return ResponseFactory.paginated_issues(issues, start_at or 0, max_results)

    def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a new issue.

        Args:
            fields: Dictionary of field values for the new issue.

        Returns:
            The created issue key, id, and self URL.
        """
        self._next_issue_id += 1
        project_key = fields.get("project", {}).get("key", "DEMO")
        issue_key = f"{project_key}-{self._next_issue_id}"
        issue_id = str(10000 + self._next_issue_id)

        # Get issue type name
        issue_type = fields.get("issuetype", {})
        if isinstance(issue_type, dict):
            type_name = issue_type.get("name", "Task")
        else:
            type_name = "Task"

        # Get priority name
        priority = fields.get("priority", {})
        if isinstance(priority, dict):
            priority_name = priority.get("name", "Medium")
        else:
            priority_name = "Medium"

        new_issue = {
            "key": issue_key,
            "id": issue_id,
            "self": f"{self.base_url}/rest/api/3/issue/{issue_id}",
            "fields": {
                "summary": fields.get("summary", "New Issue"),
                "description": fields.get("description"),
                "issuetype": {"name": type_name, "id": "10000"},
                "status": {"name": "To Do", "id": "10000"},
                "priority": {"name": priority_name, "id": "3"},
                "assignee": fields.get("assignee"),
                "reporter": self.USERS["abc123"],
                "project": {"key": project_key, "name": "Demo Project", "id": "10000"},
                "created": "2025-01-08T10:00:00.000+0000",
                "updated": "2025-01-08T10:00:00.000+0000",
                "labels": fields.get("labels", []),
            },
        }

        self._issues[issue_key] = new_issue
        return {"key": issue_key, "id": issue_id, "self": new_issue["self"]}

    def create_issues_bulk(self, issue_updates: list[dict[str, Any]]) -> dict[str, Any]:
        """Create multiple issues in bulk.

        Args:
            issue_updates: List of issue field dictionaries, each containing
                          fields for one issue.

        Returns:
            Bulk creation response with created issues and any errors.
        """
        created_issues = []
        errors = []

        for i, update in enumerate(issue_updates):
            try:
                fields = update.get("fields", update)
                result = self.create_issue(fields)
                created_issues.append(result)
            except Exception as e:
                errors.append(
                    {
                        "status": 400,
                        "elementErrors": {"errorMessages": [str(e)]},
                        "failedElementNumber": i,
                    }
                )

        return {
            "issues": created_issues,
            "errors": errors,
        }

    def get_create_issue_meta_issuetypes(
        self,
        project_id_or_key: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get issue types for project create metadata.

        This replaces the deprecated /rest/api/3/issue/createmeta endpoint.

        Args:
            project_id_or_key: Project ID or key.
            start_at: Starting index for pagination.
            max_results: Maximum results per page.

        Returns:
            Issue types available for creating issues in the project.
        """
        # Verify project exists
        self._verify_project_exists(project_id_or_key)

        issue_types = [
            {
                "id": "10000",
                "name": "Epic",
                "description": "A big user story",
                "subtask": False,
            },
            {
                "id": "10001",
                "name": "Story",
                "description": "A user story",
                "subtask": False,
            },
            {
                "id": "10002",
                "name": "Bug",
                "description": "A bug",
                "subtask": False,
            },
            {
                "id": "10003",
                "name": "Task",
                "description": "A task",
                "subtask": False,
            },
            {
                "id": "10004",
                "name": "Sub-task",
                "description": "A sub-task",
                "subtask": True,
            },
        ]

        from .factories import ResponseFactory

        return ResponseFactory.paginated(issue_types, start_at, max_results)

    def get_create_issue_meta_fields(
        self,
        project_id_or_key: str,
        issue_type_id: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get fields for a specific issue type in create metadata.

        This replaces the deprecated /rest/api/3/issue/createmeta endpoint.

        Args:
            project_id_or_key: Project ID or key.
            issue_type_id: Issue type ID.
            start_at: Starting index for pagination.
            max_results: Maximum results per page.

        Returns:
            Fields available for creating issues of this type.
        """
        # Verify project exists
        self._verify_project_exists(project_id_or_key)

        # Return common fields for all issue types
        fields = [
            {
                "fieldId": "summary",
                "name": "Summary",
                "required": True,
                "schema": {"type": "string"},
            },
            {
                "fieldId": "description",
                "name": "Description",
                "required": False,
                "schema": {"type": "string"},
            },
            {
                "fieldId": "priority",
                "name": "Priority",
                "required": False,
                "schema": {"type": "priority"},
            },
            {
                "fieldId": "assignee",
                "name": "Assignee",
                "required": False,
                "schema": {"type": "user"},
            },
            {
                "fieldId": "labels",
                "name": "Labels",
                "required": False,
                "schema": {"type": "array", "items": "string"},
            },
        ]

        from .factories import ResponseFactory

        return ResponseFactory.paginated(fields, start_at, max_results)

    def update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any] | None = None,
        update: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update an issue.

        Args:
            issue_key: The issue key to update.
            fields: Dictionary of field values to update.
            update: Update operations (for interface compatibility).

        Returns:
            Empty dictionary on success.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)
        if fields:
            self._issues[issue_key]["fields"].update(fields)
        return {}

    def delete_issue(self, issue_key: str, delete_subtasks: bool = True) -> None:
        """Delete an issue.

        Args:
            issue_key: The issue key to delete.
            delete_subtasks: Whether to delete subtasks (for interface compatibility).

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)
        del self._issues[issue_key]

    def assign_issue(self, issue_key: str, account_id: str | None = None) -> None:
        """Assign an issue to a user.

        Args:
            issue_key: The issue key to assign.
            account_id: The account ID to assign to, or None to unassign.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        if account_id is None:
            self._issues[issue_key]["fields"]["assignee"] = None
        elif account_id in self.USERS:
            self._issues[issue_key]["fields"]["assignee"] = self.USERS[account_id]
        else:
            # Accept any account_id for mock purposes
            self._issues[issue_key]["fields"]["assignee"] = {
                "accountId": account_id,
                "displayName": "Unknown User",
            }

    # =========================================================================
    # Transition Operations
    # =========================================================================

    def get_transitions(self, issue_key: str) -> list:
        """Get available transitions for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of available transitions.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)
        return self.TRANSITIONS

    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        fields: dict[str, Any] | None = None,
        update: dict[str, Any] | None = None,
        comment: str | None = None,
    ) -> None:
        """Transition an issue to a new status.

        Args:
            issue_key: The issue key to transition.
            transition_id: The ID of the transition to perform.
            fields: Additional fields to update.
            update: Update operations.
            comment: Optional comment to add.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        # Find the transition
        for t in self.TRANSITIONS:
            if t["id"] == transition_id:
                self._issues[issue_key]["fields"]["status"] = t["to"]
                break

    # =========================================================================
    # Comment Operations
    # =========================================================================

    def add_comment(self, issue_key: str, body: dict[str, Any]) -> dict[str, Any]:
        """Add a comment to an issue.

        Args:
            issue_key: The issue key.
            body: The comment body in ADF format.

        Returns:
            The created comment.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        if issue_key not in self._comments:
            self._comments[issue_key] = []

        comment_id = str(len(self._comments[issue_key]) + 1)
        comment = {
            "id": comment_id,
            "body": body,
            "author": self.USERS["abc123"],
            "created": "2025-01-08T10:00:00.000+0000",
            "updated": "2025-01-08T10:00:00.000+0000",
        }
        self._comments[issue_key].append(comment)
        return comment

    def get_comments(
        self,
        issue_key: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get comments for an issue.

        Args:
            issue_key: The issue key.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of comments.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)
        comments = self._comments.get(issue_key, [])

        from .factories import ResponseFactory

        result = ResponseFactory.paginated(comments, start_at, max_results)
        # Rename 'values' to 'comments' for this endpoint
        result["comments"] = result.pop("values")
        return result

    def get_comment(self, issue_key: str, comment_id: str) -> dict[str, Any]:
        """Get a specific comment.

        Args:
            issue_key: The issue key.
            comment_id: The comment ID.

        Returns:
            The comment data.

        Raises:
            NotFoundError: If the issue or comment is not found.
        """
        self._verify_issue_exists(issue_key)

        for comment in self._comments.get(issue_key, []):
            if comment["id"] == comment_id:
                return comment

        from ..error_handler import NotFoundError

        raise NotFoundError(f"Comment {comment_id} not found")

    def update_comment(
        self,
        issue_key: str,
        comment_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a comment.

        Args:
            issue_key: The issue key.
            comment_id: The comment ID to update.
            body: The new comment body.

        Returns:
            The updated comment.

        Raises:
            NotFoundError: If the issue or comment is not found.
        """
        self._verify_issue_exists(issue_key)

        for comment in self._comments.get(issue_key, []):
            if comment["id"] == comment_id:
                comment["body"] = body
                return comment

        from ..error_handler import NotFoundError

        raise NotFoundError(f"Comment {comment_id} not found")

    def delete_comment(self, issue_key: str, comment_id: str) -> None:
        """Delete a comment.

        Args:
            issue_key: The issue key.
            comment_id: The comment ID to delete.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        comments = self._comments.get(issue_key, [])
        self._comments[issue_key] = [c for c in comments if c["id"] != comment_id]

    # =========================================================================
    # Worklog Operations
    # =========================================================================

    def add_worklog(
        self,
        issue_key: str,
        time_spent: str | None = None,
        time_spent_seconds: int | None = None,
        started: str | None = None,
        comment: dict[str, Any] | None = None,
        adjust_estimate: str | None = None,
        new_estimate: str | None = None,
        reduce_by: str | None = None,
        visibility_type: str | None = None,
        visibility_value: str | None = None,
    ) -> dict[str, Any]:
        """Add a worklog to an issue.

        Args:
            issue_key: The issue key.
            time_spent: Time spent in JIRA format (e.g., '2h 30m').
            time_spent_seconds: Time spent in seconds.
            started: Start time for the worklog.
            comment: Optional comment for the worklog.
            adjust_estimate: How to adjust the estimate.
            new_estimate: New estimate value.
            reduce_by: Amount to reduce estimate by.
            visibility_type: 'role' or 'group' to restrict visibility (ignored in mock).
            visibility_value: Role or group name for visibility restriction (ignored in mock).

        Returns:
            The created worklog.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        if issue_key not in self._worklogs:
            self._worklogs[issue_key] = []

        worklog_id = str(len(self._worklogs[issue_key]) + 1)
        worklog = {
            "id": worklog_id,
            "timeSpent": time_spent or f"{(time_spent_seconds or 0) // 60}m",
            "timeSpentSeconds": time_spent_seconds or 0,
            "started": started or "2025-01-08T10:00:00.000+0000",
            "comment": comment,
            "author": self.USERS["abc123"],
            "created": "2025-01-08T10:00:00.000+0000",
            "updated": "2025-01-08T10:00:00.000+0000",
        }

        # Add visibility if specified
        if visibility_type and visibility_value:
            worklog["visibility"] = {
                "type": visibility_type,
                "value": visibility_value,
                "identifier": visibility_value,
            }

        self._worklogs[issue_key].append(worklog)
        return worklog

    def get_worklogs(
        self,
        issue_key: str,
        start_at: int = 0,
        max_results: int = 1000,
    ) -> dict[str, Any]:
        """Get worklogs for an issue.

        Args:
            issue_key: The issue key.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of worklogs.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        worklogs = self._worklogs.get(issue_key, [])
        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(worklogs),
            "worklogs": worklogs[start_at : start_at + max_results],
        }

    # =========================================================================
    # User Operations
    # =========================================================================

    def search_users(
        self,
        query: str | None = None,
        account_id: str | None = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> list:
        """Search for users.

        Args:
            query: Search query string.
            account_id: Specific account ID to find.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            List of matching users.
        """
        if account_id and account_id in self.USERS:
            return [self.USERS[account_id]]

        if query:
            query_lower = query.lower()
            return [
                u
                for u in self.USERS.values()
                if query_lower in u["displayName"].lower()
                or query_lower in u.get("emailAddress", "").lower()
            ]

        return list(self.USERS.values())

    def get_user(
        self,
        account_id: str | None = None,
        username: str | None = None,
        key: str | None = None,
        expand: list | None = None,
    ) -> dict[str, Any]:
        """Get user by account ID.

        Args:
            account_id: The user's account ID.
            username: Username (for backwards compatibility).
            key: User key (for backwards compatibility).
            expand: Fields to expand.

        Returns:
            The user data.

        Raises:
            NotFoundError: If the user is not found.
        """
        if account_id and account_id in self.USERS:
            return self.USERS[account_id]

        # Search by name for backwards compatibility
        if username:
            for user in self.USERS.values():
                if username.lower() in user["displayName"].lower():
                    return user

        from ..error_handler import NotFoundError

        raise NotFoundError("User not found")

    def get_current_user(self, expand: list | None = None) -> dict[str, Any]:
        """Get the current authenticated user.

        Args:
            expand: Fields to expand.

        Returns:
            The current user data.
        """
        return self.USERS["abc123"]

    def get_current_user_id(self) -> str:
        """Get the current user's account ID.

        Returns:
            The current user's account ID.
        """
        return "abc123"

    def find_assignable_users(
        self,
        query: str,
        project_key: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> list:
        """Find users assignable to issues in a project.

        Args:
            query: Search query (name or email).
            project_key: Project key to search within.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            List of assignable users matching the query.
        """
        users = list(self.USERS.values())

        # Filter by query if provided
        if query:
            query_lower = query.lower()
            users = [
                u
                for u in users
                if query_lower in u["displayName"].lower()
                or query_lower in u.get("emailAddress", "").lower()
            ]

        return users[start_at : start_at + max_results]

    def get_all_users(self, start_at: int = 0, max_results: int = 50) -> list:
        """Get all users (paginated).

        Note: Requires 'Browse users and groups' global permission.

        Args:
            start_at: Starting index for pagination.
            max_results: Maximum results to return.

        Returns:
            List of user objects.
        """
        users = list(self.USERS.values())
        return users[start_at : start_at + max_results]

    def get_users_bulk(
        self, account_ids: list, max_results: int = 200
    ) -> dict[str, Any]:
        """Get multiple users by account IDs.

        Args:
            account_ids: List of user account IDs (max 200).
            max_results: Maximum results to return.

        Returns:
            Response with 'values' array of user objects.
        """
        users = [self.USERS[aid] for aid in account_ids if aid in self.USERS][
            :max_results
        ]
        return {"values": users}

    def get_user_groups(self, account_id: str) -> list:
        """Get groups that a user belongs to.

        Args:
            account_id: User's account ID.

        Returns:
            List of group objects with name, groupId.
        """
        # Return mock groups for known users
        if account_id in self.USERS:
            return [
                {"name": "jira-software-users", "groupId": "group-2"},
                {"name": "developers", "groupId": "group-4"},
            ]
        return []

    # =========================================================================
    # Project Operations
    # =========================================================================

    def get_project(
        self,
        project_key: str,
        expand: str | None = None,
        properties: list | None = None,
    ) -> dict[str, Any]:
        """Get project by key.

        Args:
            project_key: The project key (e.g., 'DEMO').
            expand: Fields to expand.
            properties: Properties to include.

        Returns:
            The project data.

        Raises:
            NotFoundError: If the project is not found.
        """
        for project in self.PROJECTS:
            if project["key"] == project_key:
                return project

        from ..error_handler import NotFoundError

        raise NotFoundError(f"Project {project_key} not found")

    def get_project_statuses(self, project_key: str) -> list:
        """Get all statuses for a project.

        Args:
            project_key: The project key.

        Returns:
            List of status categories with their statuses.
        """
        return [
            {
                "id": "10000",
                "name": "To Do",
                "statuses": [{"id": "10000", "name": "To Do"}],
            },
            {
                "id": "10001",
                "name": "In Progress",
                "statuses": [{"id": "10001", "name": "In Progress"}],
            },
            {
                "id": "10002",
                "name": "Done",
                "statuses": [{"id": "10002", "name": "Done"}],
            },
        ]

    def get_project_components(self, project_key: str) -> list:
        """Get all components for a project.

        Args:
            project_key: The project key (e.g., 'DEMO').

        Returns:
            List of component objects.

        Raises:
            NotFoundError: If the project is not found.
        """
        self._verify_project_exists(project_key)

        # Return mock components for known projects
        if project_key == "DEMO":
            return [
                {
                    "id": "10000",
                    "name": "Backend",
                    "description": "Backend services and APIs",
                    "self": f"{self.base_url}/rest/api/3/component/10000",
                    "project": "DEMO",
                    "projectId": 10000,
                },
                {
                    "id": "10001",
                    "name": "Frontend",
                    "description": "Frontend UI components",
                    "self": f"{self.base_url}/rest/api/3/component/10001",
                    "project": "DEMO",
                    "projectId": 10000,
                },
                {
                    "id": "10002",
                    "name": "Documentation",
                    "description": "Project documentation",
                    "self": f"{self.base_url}/rest/api/3/component/10002",
                    "project": "DEMO",
                    "projectId": 10000,
                },
            ]
        elif project_key == "DEMOSD":
            return [
                {
                    "id": "10100",
                    "name": "IT Support",
                    "description": "IT support requests",
                    "self": f"{self.base_url}/rest/api/3/component/10100",
                    "project": "DEMOSD",
                    "projectId": 10001,
                },
                {
                    "id": "10101",
                    "name": "Hardware",
                    "description": "Hardware related issues",
                    "self": f"{self.base_url}/rest/api/3/component/10101",
                    "project": "DEMOSD",
                    "projectId": 10001,
                },
            ]

        # Return empty list for other projects
        return []

    def get_project_versions(self, project_key: str, expand: str | None = None) -> list:
        """Get all versions for a project.

        Args:
            project_key: The project key (e.g., 'DEMO').
            expand: Optional expansions.

        Returns:
            List of version objects.

        Raises:
            NotFoundError: If the project is not found.
        """
        self._verify_project_exists(project_key)

        # Return mock versions for known projects
        if project_key == "DEMO":
            return [
                {
                    "id": "10000",
                    "name": "1.0.0",
                    "description": "Initial release",
                    "archived": False,
                    "released": True,
                    "releaseDate": "2025-01-01",
                    "self": f"{self.base_url}/rest/api/3/version/10000",
                    "projectId": 10000,
                },
                {
                    "id": "10001",
                    "name": "1.1.0",
                    "description": "Feature update",
                    "archived": False,
                    "released": False,
                    "self": f"{self.base_url}/rest/api/3/version/10001",
                    "projectId": 10000,
                },
                {
                    "id": "10002",
                    "name": "2.0.0",
                    "description": "Major release",
                    "archived": False,
                    "released": False,
                    "self": f"{self.base_url}/rest/api/3/version/10002",
                    "projectId": 10000,
                },
            ]

        # Return empty list for other projects
        return []

    # =========================================================================
    # HTTP Methods (scaffolding for low-level access)
    # =========================================================================

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        operation: str = "fetch data",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generic GET - returns empty dict for unmocked endpoints.

        Args:
            endpoint: The API endpoint.
            params: Query parameters.
            operation: Description of the operation.
            headers: Additional headers.

        Returns:
            Empty dictionary.
        """
        return {}

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        operation: str = "create resource",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generic POST - returns empty dict for unmocked endpoints.

        Args:
            endpoint: The API endpoint.
            data: Request body data.
            operation: Description of the operation.
            headers: Additional headers.

        Returns:
            Empty dictionary.
        """
        return {}

    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        operation: str = "update resource",
    ) -> dict[str, Any]:
        """Generic PUT - returns empty dict for unmocked endpoints.

        Args:
            endpoint: The API endpoint.
            data: Request body data.
            operation: Description of the operation.

        Returns:
            Empty dictionary.
        """
        return {}

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        operation: str = "delete resource",
    ) -> None:
        """Generic DELETE - no-op for unmocked endpoints.

        Args:
            endpoint: The API endpoint.
            params: Query parameters.
            operation: Description of the operation.
        """
        pass

    # =========================================================================
    # Context Manager
    # =========================================================================

    def close(self):
        """Close the client (no-op for mock)."""
        pass

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close()

"""Mock JIRA responses for testing without API calls.

When JIRA_MOCK_MODE=true, the MockJiraClient is used instead of the real
JiraClient, providing fast, deterministic responses for skill testing.

The mock data matches the DEMO project structure used in skill tests.
"""

import os
from typing import Any, Dict, List, Optional


class MockJiraClient:
    """Returns consistent mock data matching DEMO project structure.

    Implements the same interface as JiraClient but returns canned responses.
    Supports basic stateful operations (create, update, transition) within
    a single test session.
    """

    def __init__(
        self,
        base_url: str = "https://mock.atlassian.net",
        email: str = "test@example.com",
        api_token: str = "mock-token",
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ):
        """Initialize mock client with optional parameters for interface compatibility."""
        self.base_url = base_url
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Initialize mutable state
        self._next_issue_id = 100
        self._issues = self._init_issues()
        self._comments: Dict[str, List[Dict]] = {}
        self._worklogs: Dict[str, List[Dict]] = {}

    def _init_issues(self) -> Dict[str, Dict]:
        """Initialize issue store with seed data matching DEMO project."""
        return {
            "DEMO-84": {
                "key": "DEMO-84",
                "id": "10084",
                "self": f"{self.base_url}/rest/api/3/issue/10084",
                "fields": {
                    "summary": "Product Launch",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Epic for product launch activities"}
                                ],
                            }
                        ],
                    },
                    "issuetype": {"name": "Epic", "id": "10000"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "High", "id": "2"},
                    "assignee": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                    },
                    "project": {"key": "DEMO", "name": "Demo Project", "id": "10000"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
            },
            "DEMO-85": {
                "key": "DEMO-85",
                "id": "10085",
                "self": f"{self.base_url}/rest/api/3/issue/10085",
                "fields": {
                    "summary": "User Authentication",
                    "description": None,
                    "issuetype": {"name": "Story", "id": "10001"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "High", "id": "2"},
                    "assignee": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                    },
                    "project": {"key": "DEMO", "name": "Demo Project", "id": "10000"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
            },
            "DEMO-86": {
                "key": "DEMO-86",
                "id": "10086",
                "self": f"{self.base_url}/rest/api/3/issue/10086",
                "fields": {
                    "summary": "Login fails on mobile Safari",
                    "description": None,
                    "issuetype": {"name": "Bug", "id": "10002"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "High", "id": "2"},
                    "assignee": {
                        "accountId": "def456",
                        "displayName": "Jane Manager",
                        "emailAddress": "jane@example.com",
                    },
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                    },
                    "project": {"key": "DEMO", "name": "Demo Project", "id": "10000"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
            },
            "DEMO-87": {
                "key": "DEMO-87",
                "id": "10087",
                "self": f"{self.base_url}/rest/api/3/issue/10087",
                "fields": {
                    "summary": "Update API documentation",
                    "description": None,
                    "issuetype": {"name": "Task", "id": "10003"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "Medium", "id": "3"},
                    "assignee": {
                        "accountId": "def456",
                        "displayName": "Jane Manager",
                        "emailAddress": "jane@example.com",
                    },
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                    },
                    "project": {"key": "DEMO", "name": "Demo Project", "id": "10000"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
            },
            "DEMO-91": {
                "key": "DEMO-91",
                "id": "10091",
                "self": f"{self.base_url}/rest/api/3/issue/10091",
                "fields": {
                    "summary": "Search pagination bug",
                    "description": None,
                    "issuetype": {"name": "Bug", "id": "10002"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "Medium", "id": "3"},
                    "assignee": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                    "reporter": {
                        "accountId": "def456",
                        "displayName": "Jane Manager",
                        "emailAddress": "jane@example.com",
                    },
                    "project": {"key": "DEMO", "name": "Demo Project", "id": "10000"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
            },
        }

    # =========================================================================
    # Users
    # =========================================================================

    USERS = {
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
    # Projects
    # =========================================================================

    PROJECTS = [
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
    # Issue Operations
    # =========================================================================

    def get_issue(self, issue_key: str, fields: str = None, expand: str = None) -> Dict[str, Any]:
        """Get issue by key."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")
        return self._issues[issue_key]

    def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: str = None,
        expand: str = None,
    ) -> Dict[str, Any]:
        """Search issues with JQL. Supports basic project and assignee filtering."""
        issues = list(self._issues.values())
        jql_upper = jql.upper()

        # Filter by project
        if "PROJECT = DEMO" in jql_upper or "PROJECT=DEMO" in jql_upper:
            issues = [i for i in issues if i["key"].startswith("DEMO-")]

        # Filter by assignee
        if "ASSIGNEE" in jql_upper:
            jql_lower = jql.lower()
            if "jane" in jql_lower:
                issues = [
                    i for i in issues
                    if i["fields"].get("assignee", {}).get("displayName", "").lower() == "jane manager"
                ]
            elif "jason" in jql_lower:
                issues = [
                    i for i in issues
                    if i["fields"].get("assignee", {}).get("displayName", "").lower() == "jason krueger"
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
        if "STATUS = \"IN PROGRESS\"" in jql_upper or "STATUS=\"IN PROGRESS\"" in jql_upper:
            issues = [i for i in issues if i["fields"]["status"]["name"] == "In Progress"]
        elif "STATUS = \"TO DO\"" in jql_upper or "STATUS=\"TO DO\"" in jql_upper:
            issues = [i for i in issues if i["fields"]["status"]["name"] == "To Do"]

        # Filter by reporter
        if "REPORTER" in jql_upper:
            jql_lower = jql.lower()
            if "jane" in jql_lower:
                issues = [
                    i for i in issues
                    if i["fields"].get("reporter", {}).get("displayName", "").lower() == "jane manager"
                ]
            elif "jason" in jql_lower:
                issues = [
                    i for i in issues
                    if i["fields"].get("reporter", {}).get("displayName", "").lower() == "jason krueger"
                ]

        # Text search (text ~ "keyword")
        import re
        text_match = re.search(r'TEXT\s*~\s*["\']([^"\']+)["\']', jql, re.IGNORECASE)
        if text_match:
            search_term = text_match.group(1).lower()
            issues = [
                i for i in issues
                if search_term in i["fields"].get("summary", "").lower()
            ]

        # Pagination
        paginated = issues[start_at : start_at + max_results]

        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(issues),
            "issues": paginated,
        }

    def create_issue(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue."""
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

    def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any] = None,
        update: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Update an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        if fields:
            self._issues[issue_key]["fields"].update(fields)
        return {}

    def delete_issue(self, issue_key: str, delete_subtasks: bool = True) -> None:
        """Delete an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")
        del self._issues[issue_key]

    def assign_issue(self, issue_key: str, account_id: Optional[str] = None) -> None:
        """Assign an issue to a user."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

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
    # Transitions
    # =========================================================================

    TRANSITIONS = [
        {"id": "11", "name": "To Do", "to": {"name": "To Do", "id": "10000"}},
        {"id": "21", "name": "In Progress", "to": {"name": "In Progress", "id": "10001"}},
        {"id": "31", "name": "Done", "to": {"name": "Done", "id": "10002"}},
    ]

    def get_transitions(self, issue_key: str) -> list:
        """Get available transitions for an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")
        return self.TRANSITIONS

    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        fields: Dict[str, Any] = None,
        update: Dict[str, Any] = None,
        comment: str = None,
    ) -> None:
        """Transition an issue to a new status."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        # Find the transition
        for t in self.TRANSITIONS:
            if t["id"] == transition_id:
                self._issues[issue_key]["fields"]["status"] = t["to"]
                break

    # =========================================================================
    # Comments
    # =========================================================================

    def add_comment(self, issue_key: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Add a comment to an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

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
    ) -> Dict[str, Any]:
        """Get comments for an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        comments = self._comments.get(issue_key, [])
        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(comments),
            "comments": comments[start_at : start_at + max_results],
        }

    def get_comment(self, issue_key: str, comment_id: str) -> Dict[str, Any]:
        """Get a specific comment."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        for comment in self._comments.get(issue_key, []):
            if comment["id"] == comment_id:
                return comment

        from .error_handler import NotFoundError
        raise NotFoundError(f"Comment {comment_id} not found")

    def update_comment(
        self,
        issue_key: str,
        comment_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a comment."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        for comment in self._comments.get(issue_key, []):
            if comment["id"] == comment_id:
                comment["body"] = body
                return comment

        from .error_handler import NotFoundError
        raise NotFoundError(f"Comment {comment_id} not found")

    def delete_comment(self, issue_key: str, comment_id: str) -> None:
        """Delete a comment."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        comments = self._comments.get(issue_key, [])
        self._comments[issue_key] = [c for c in comments if c["id"] != comment_id]

    # =========================================================================
    # Worklogs
    # =========================================================================

    def add_worklog(
        self,
        issue_key: str,
        time_spent: str = None,
        time_spent_seconds: int = None,
        started: str = None,
        comment: Dict[str, Any] = None,
        adjust_estimate: str = None,
        new_estimate: str = None,
        reduce_by: str = None,
    ) -> Dict[str, Any]:
        """Add a worklog to an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

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
        self._worklogs[issue_key].append(worklog)
        return worklog

    def get_worklogs(
        self,
        issue_key: str,
        start_at: int = 0,
        max_results: int = 1000,
    ) -> Dict[str, Any]:
        """Get worklogs for an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        worklogs = self._worklogs.get(issue_key, [])
        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(worklogs),
            "worklogs": worklogs[start_at : start_at + max_results],
        }

    # =========================================================================
    # Users
    # =========================================================================

    def search_users(
        self,
        query: str = None,
        account_id: str = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> list:
        """Search for users."""
        if account_id and account_id in self.USERS:
            return [self.USERS[account_id]]

        if query:
            query_lower = query.lower()
            return [
                u for u in self.USERS.values()
                if query_lower in u["displayName"].lower()
                or query_lower in u.get("emailAddress", "").lower()
            ]

        return list(self.USERS.values())

    def get_user(
        self,
        account_id: str = None,
        username: str = None,
        key: str = None,
        expand: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Get user by account ID."""
        if account_id and account_id in self.USERS:
            return self.USERS[account_id]

        # Search by name for backwards compatibility
        if username:
            for user in self.USERS.values():
                if username.lower() in user["displayName"].lower():
                    return user

        from .error_handler import NotFoundError
        raise NotFoundError(f"User not found")

    def get_current_user(self, expand: Optional[list] = None) -> Dict[str, Any]:
        """Get the current authenticated user."""
        return self.USERS["abc123"]

    def get_current_user_id(self) -> str:
        """Get the current user's account ID."""
        return "abc123"

    def find_assignable_users(
        self,
        project: str = None,
        issue_key: str = None,
        query: str = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> list:
        """Find users assignable to a project or issue."""
        return list(self.USERS.values())

    # =========================================================================
    # Projects
    # =========================================================================

    def get_project(
        self,
        project_key: str,
        expand: str = None,
        properties: list = None,
    ) -> Dict[str, Any]:
        """Get project by key."""
        for project in self.PROJECTS:
            if project["key"] == project_key:
                return project

        from .error_handler import NotFoundError
        raise NotFoundError(f"Project {project_key} not found")

    def get_project_statuses(self, project_key: str) -> list:
        """Get all statuses for a project."""
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

    # =========================================================================
    # HTTP Methods (for low-level access)
    # =========================================================================

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "fetch data",
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generic GET - returns empty dict for unmocked endpoints."""
        return {}

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        operation: str = "create resource",
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generic POST - returns empty dict for unmocked endpoints."""
        return {}

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        operation: str = "update resource",
    ) -> Dict[str, Any]:
        """Generic PUT - returns empty dict for unmocked endpoints."""
        return {}

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "delete resource",
    ) -> None:
        """Generic DELETE - no-op for unmocked endpoints."""
        pass

    # =========================================================================
    # Context Manager
    # =========================================================================

    def close(self):
        """Close the client (no-op for mock)."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def is_mock_mode() -> bool:
    """Check if JIRA mock mode is enabled."""
    return os.environ.get("JIRA_MOCK_MODE", "").lower() == "true"

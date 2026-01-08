"""Base mock JIRA client with core functionality.

Contains MockJiraClientBase with essential issue, user, project, and transition
operations that other mixins build upon.
"""

import os
from typing import Any, Dict, List, Optional


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
    # Class Constants - Projects
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
    # Class Constants - Transitions
    # =========================================================================

    TRANSITIONS = [
        {"id": "11", "name": "To Do", "to": {"name": "To Do", "id": "10000"}},
        {"id": "21", "name": "In Progress", "to": {"name": "In Progress", "id": "10001"}},
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
        self._comments: Dict[str, List[Dict]] = {}
        self._worklogs: Dict[str, List[Dict]] = {}

    def _init_issues(self) -> Dict[str, Dict]:
        """Initialize issue store with seed data matching DEMO project.

        Returns:
            Dictionary of issue key to issue data for DEMO-84 through DEMO-91
            and DEMOSD-1 through DEMOSD-5.
        """
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
            # =====================================================================
            # DEMOSD Service Desk Issues
            # =====================================================================
            "DEMOSD-1": {
                "key": "DEMOSD-1",
                "id": "20001",
                "self": f"{self.base_url}/rest/api/3/issue/20001",
                "fields": {
                    "summary": "Can't connect to VPN",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "I'm working from home and can't connect to the corporate VPN. Getting 'connection timeout' error.",
                                    }
                                ],
                            }
                        ],
                    },
                    "issuetype": {"name": "IT help", "id": "10100"},
                    "status": {"name": "Waiting for support", "id": "10100"},
                    "priority": {"name": "Medium", "id": "3"},
                    "assignee": None,
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                    "project": {"key": "DEMOSD", "name": "Demo Service Desk", "id": "10001"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
                "requestTypeId": "1",
                "serviceDeskId": "1",
                "currentStatus": {"status": "Waiting for support", "statusCategory": "new"},
            },
            "DEMOSD-2": {
                "key": "DEMOSD-2",
                "id": "20002",
                "self": f"{self.base_url}/rest/api/3/issue/20002",
                "fields": {
                    "summary": "New laptop for development",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Need a new development laptop with 32GB RAM and SSD.",
                                    }
                                ],
                            }
                        ],
                    },
                    "issuetype": {"name": "Computer support", "id": "10101"},
                    "status": {"name": "Waiting for support", "id": "10100"},
                    "priority": {"name": "Medium", "id": "3"},
                    "assignee": None,
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                    "project": {"key": "DEMOSD", "name": "Demo Service Desk", "id": "10001"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
                "requestTypeId": "2",
                "serviceDeskId": "1",
                "currentStatus": {"status": "Waiting for support", "statusCategory": "new"},
            },
            "DEMOSD-3": {
                "key": "DEMOSD-3",
                "id": "20003",
                "self": f"{self.base_url}/rest/api/3/issue/20003",
                "fields": {
                    "summary": "New hire starting Monday - Alex Chen",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Please set up accounts and equipment for new hire Alex Chen starting Monday.",
                                    }
                                ],
                            }
                        ],
                    },
                    "issuetype": {"name": "New employee", "id": "10102"},
                    "status": {"name": "Waiting for support", "id": "10100"},
                    "priority": {"name": "High", "id": "2"},
                    "assignee": None,
                    "reporter": {
                        "accountId": "def456",
                        "displayName": "Jane Manager",
                        "emailAddress": "jane@example.com",
                    },
                    "project": {"key": "DEMOSD", "name": "Demo Service Desk", "id": "10001"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
                "requestTypeId": "3",
                "serviceDeskId": "1",
                "currentStatus": {"status": "Waiting for support", "statusCategory": "new"},
            },
            "DEMOSD-4": {
                "key": "DEMOSD-4",
                "id": "20004",
                "self": f"{self.base_url}/rest/api/3/issue/20004",
                "fields": {
                    "summary": "Conference travel to AWS re:Invent",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Requesting approval for travel to AWS re:Invent in Las Vegas.",
                                    }
                                ],
                            }
                        ],
                    },
                    "issuetype": {"name": "Travel request", "id": "10103"},
                    "status": {"name": "Waiting for support", "id": "10100"},
                    "priority": {"name": "Medium", "id": "3"},
                    "assignee": None,
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                    "project": {"key": "DEMOSD", "name": "Demo Service Desk", "id": "10001"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
                "requestTypeId": "4",
                "serviceDeskId": "1",
                "currentStatus": {"status": "Waiting for support", "statusCategory": "new"},
            },
            "DEMOSD-5": {
                "key": "DEMOSD-5",
                "id": "20005",
                "self": f"{self.base_url}/rest/api/3/issue/20005",
                "fields": {
                    "summary": "Purchase ergonomic keyboard",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Need to purchase an ergonomic keyboard for RSI prevention. Estimated cost: $150.",
                                    }
                                ],
                            }
                        ],
                    },
                    "issuetype": {"name": "Purchase over $100", "id": "10104"},
                    "status": {"name": "Waiting for support", "id": "10100"},
                    "priority": {"name": "Low", "id": "4"},
                    "assignee": None,
                    "reporter": {
                        "accountId": "abc123",
                        "displayName": "Jason Krueger",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                    "project": {"key": "DEMOSD", "name": "Demo Service Desk", "id": "10001"},
                    "created": "2025-01-01T10:00:00.000+0000",
                    "updated": "2025-01-01T10:00:00.000+0000",
                    "labels": ["demo"],
                },
                "requestTypeId": "5",
                "serviceDeskId": "1",
                "currentStatus": {"status": "Waiting for support", "statusCategory": "new"},
            },
        }

    # =========================================================================
    # Issue Operations
    # =========================================================================

    def get_issue(self, issue_key: str, fields: str = None, expand: str = None) -> Dict[str, Any]:
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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
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
        """Search issues with JQL. Supports basic project and assignee filtering.

        Args:
            jql: JQL query string.
            start_at: Starting index for pagination.
            max_results: Maximum number of results to return.
            fields: Comma-separated list of fields to return.
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
            issues = [i for i in issues if i["key"].startswith("DEMO-") and not i["key"].startswith("DEMOSD-")]

        # Filter by assignee
        if "ASSIGNEE" in jql_upper:
            jql_lower = jql.lower()
            if "jane" in jql_lower:
                issues = [
                    i for i in issues
                    if i["fields"].get("assignee") and i["fields"]["assignee"].get("displayName", "").lower() == "jane manager"
                ]
            elif "jason" in jql_lower:
                issues = [
                    i for i in issues
                    if i["fields"].get("assignee") and i["fields"]["assignee"].get("displayName", "").lower() == "jason krueger"
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

    def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any] = None,
        update: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")
        del self._issues[issue_key]

    def assign_issue(self, issue_key: str, account_id: Optional[str] = None) -> None:
        """Assign an issue to a user.

        Args:
            issue_key: The issue key to assign.
            account_id: The account ID to assign to, or None to unassign.

        Raises:
            NotFoundError: If the issue is not found.
        """
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        # Find the transition
        for t in self.TRANSITIONS:
            if t["id"] == transition_id:
                self._issues[issue_key]["fields"]["status"] = t["to"]
                break

    # =========================================================================
    # Comment Operations
    # =========================================================================

    def add_comment(self, issue_key: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Add a comment to an issue.

        Args:
            issue_key: The issue key.
            body: The comment body in ADF format.

        Returns:
            The created comment.

        Raises:
            NotFoundError: If the issue is not found.
        """
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        comments = self._comments.get(issue_key, [])
        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(comments),
            "comments": comments[start_at : start_at + max_results],
        }

    def get_comment(self, issue_key: str, comment_id: str) -> Dict[str, Any]:
        """Get a specific comment.

        Args:
            issue_key: The issue key.
            comment_id: The comment ID.

        Returns:
            The comment data.

        Raises:
            NotFoundError: If the issue or comment is not found.
        """
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        for comment in self._comments.get(issue_key, []):
            if comment["id"] == comment_id:
                return comment

        from ..error_handler import NotFoundError
        raise NotFoundError(f"Comment {comment_id} not found")

    def update_comment(
        self,
        issue_key: str,
        comment_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        comments = self._comments.get(issue_key, [])
        self._comments[issue_key] = [c for c in comments if c["id"] != comment_id]

    # =========================================================================
    # Worklog Operations
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

        Returns:
            The created worklog.

        Raises:
            NotFoundError: If the issue is not found.
        """
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
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
        if issue_key not in self._issues:
            from ..error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

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
        query: str = None,
        account_id: str = None,
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

    def get_current_user(self, expand: Optional[list] = None) -> Dict[str, Any]:
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
        project: str = None,
        issue_key: str = None,
        query: str = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> list:
        """Find users assignable to a project or issue.

        Args:
            project: Project key to filter by.
            issue_key: Issue key to filter by.
            query: Search query.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            List of assignable users.
        """
        return list(self.USERS.values())

    # =========================================================================
    # Project Operations
    # =========================================================================

    def get_project(
        self,
        project_key: str,
        expand: str = None,
        properties: list = None,
    ) -> Dict[str, Any]:
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

    # =========================================================================
    # HTTP Methods (scaffolding for low-level access)
    # =========================================================================

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "fetch data",
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
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
        data: Optional[Dict[str, Any]] = None,
        operation: str = "create resource",
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
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
        data: Optional[Dict[str, Any]] = None,
        operation: str = "update resource",
    ) -> Dict[str, Any]:
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
        params: Optional[Dict[str, Any]] = None,
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

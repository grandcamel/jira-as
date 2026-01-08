"""Mock JIRA responses for testing without API calls.

When JIRA_MOCK_MODE=true, the MockJiraClient is used instead of the real
JiraClient, providing fast, deterministic responses for skill testing.

The mock data matches the DEMO project structure used in skill tests.
"""

import os
import re
from typing import Any, Dict, List, Optional


class MockJiraClient:
    """Returns consistent mock data matching DEMO project structure.

    Implements the same interface as JiraClient but returns canned responses.
    Supports basic stateful operations (create, update, transition) within
    a single test session.
    """

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
        "ghi789": {
            "accountId": "ghi789",
            "displayName": "Admin User",
            "emailAddress": "admin@example.com",
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
    # Admin: Project Roles
    # =========================================================================

    PROJECT_ROLES = [
        {"id": 10002, "name": "Administrators", "description": "Project administrators"},
        {"id": 10001, "name": "Developers", "description": "A project role for developers"},
        {"id": 10000, "name": "Users", "description": "A project role for users"},
    ]

    # =========================================================================
    # Admin: Groups
    # =========================================================================

    GROUPS = [
        {"name": "jira-administrators", "groupId": "group-admin-001"},
        {"name": "jira-software-users", "groupId": "group-sw-001"},
        {"name": "jira-users", "groupId": "group-users-001"},
        {"name": "site-admins", "groupId": "group-site-001"},
        {"name": "developers", "groupId": "group-dev-001"},
    ]

    # =========================================================================
    # Admin: Permissions
    # =========================================================================

    MOCK_USER_PERMISSIONS = {
        "BROWSE_PROJECTS": True,
        "CREATE_ISSUES": True,
        "EDIT_ISSUES": True,
        "DELETE_ISSUES": False,
        "ASSIGN_ISSUES": True,
        "ASSIGNABLE_USER": True,
        "RESOLVE_ISSUES": True,
        "CLOSE_ISSUES": True,
        "TRANSITION_ISSUES": True,
        "SCHEDULE_ISSUES": False,
        "MOVE_ISSUES": True,
        "SET_ISSUE_SECURITY": False,
        "MANAGE_WATCHERS": True,
        "ADD_COMMENTS": True,
        "EDIT_ALL_COMMENTS": False,
        "DELETE_ALL_COMMENTS": False,
        "CREATE_ATTACHMENTS": True,
        "DELETE_ALL_ATTACHMENTS": False,
        "WORK_ON_ISSUES": True,
        "LINK_ISSUES": True,
        "VIEW_VOTERS_AND_WATCHERS": True,
        "ADMINISTER_PROJECTS": False,
    }

    # =========================================================================
    # Agile: Boards
    # =========================================================================

    BOARDS = [
        {
            "id": 1,
            "name": "DEMO Board",
            "type": "scrum",
            "location": {"projectKey": "DEMO", "projectName": "Demo Project", "projectId": "10000"},
        }
    ]

    # =========================================================================
    # Relationships: Link Types
    # =========================================================================

    LINK_TYPES = [
        {"id": "10000", "name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
        {"id": "10001", "name": "Cloners", "inward": "is cloned by", "outward": "clones"},
        {"id": "10002", "name": "Duplicate", "inward": "is duplicated by", "outward": "duplicates"},
        {"id": "10003", "name": "Relates", "inward": "relates to", "outward": "relates to"},
    ]

    # =========================================================================
    # Fields: Field Definitions
    # =========================================================================

    FIELDS = [
        # System Fields
        {"id": "summary", "name": "Summary", "custom": False, "schema": {"type": "string"}, "searchable": True, "navigable": True},
        {"id": "description", "name": "Description", "custom": False, "schema": {"type": "doc"}, "searchable": True, "navigable": True},
        {"id": "issuetype", "name": "Issue Type", "custom": False, "schema": {"type": "issuetype"}, "searchable": True, "navigable": True},
        {"id": "project", "name": "Project", "custom": False, "schema": {"type": "project"}, "searchable": True, "navigable": True},
        {"id": "status", "name": "Status", "custom": False, "schema": {"type": "status"}, "searchable": True, "navigable": True},
        {"id": "priority", "name": "Priority", "custom": False, "schema": {"type": "priority"}, "searchable": True, "navigable": True},
        {"id": "assignee", "name": "Assignee", "custom": False, "schema": {"type": "user"}, "searchable": True, "navigable": True},
        {"id": "reporter", "name": "Reporter", "custom": False, "schema": {"type": "user"}, "searchable": True, "navigable": True},
        {"id": "labels", "name": "Labels", "custom": False, "schema": {"type": "array", "items": "string"}, "searchable": True, "navigable": True},
        {"id": "created", "name": "Created", "custom": False, "schema": {"type": "datetime"}, "searchable": True, "navigable": True},
        {"id": "updated", "name": "Updated", "custom": False, "schema": {"type": "datetime"}, "searchable": True, "navigable": True},
        {"id": "resolution", "name": "Resolution", "custom": False, "schema": {"type": "resolution"}, "searchable": True, "navigable": True},
        {"id": "fixVersions", "name": "Fix Version/s", "custom": False, "schema": {"type": "array", "items": "version"}, "searchable": True, "navigable": True},
        {"id": "components", "name": "Component/s", "custom": False, "schema": {"type": "array", "items": "component"}, "searchable": True, "navigable": True},
        {"id": "duedate", "name": "Due Date", "custom": False, "schema": {"type": "date"}, "searchable": True, "navigable": True},
        {"id": "timetracking", "name": "Time Tracking", "custom": False, "schema": {"type": "timetracking"}, "searchable": False, "navigable": True},
        # Agile Custom Fields
        {"id": "customfield_10016", "name": "Story Points", "custom": True, "schema": {"type": "number"}, "searchable": True, "navigable": True},
        {"id": "customfield_10014", "name": "Epic Link", "custom": True, "schema": {"type": "any"}, "searchable": True, "navigable": True},
        {"id": "customfield_10020", "name": "Sprint", "custom": True, "schema": {"type": "array", "items": "sprint"}, "searchable": True, "navigable": True},
        {"id": "customfield_10011", "name": "Epic Name", "custom": True, "schema": {"type": "string"}, "searchable": True, "navigable": True},
        {"id": "customfield_10012", "name": "Epic Color", "custom": True, "schema": {"type": "string"}, "searchable": False, "navigable": True},
        {"id": "customfield_10019", "name": "Rank", "custom": True, "schema": {"type": "any"}, "searchable": False, "navigable": True},
        {"id": "customfield_10017", "name": "Story point estimate", "custom": True, "schema": {"type": "number"}, "searchable": True, "navigable": True},
    ]

    # =========================================================================
    # JSM Service Desk Configuration
    # =========================================================================

    SERVICE_DESKS = [
        {
            "id": "1",
            "projectId": "10001",
            "projectName": "Demo Service Desk",
            "projectKey": "DEMOSD",
        }
    ]

    # Request Types for DEMOSD
    REQUEST_TYPES = {
        "1": [
            {"id": "1", "name": "IT help", "description": "Get help from IT"},
            {"id": "2", "name": "Computer support", "description": "Computer hardware/software issues"},
            {"id": "3", "name": "New employee", "description": "Onboard a new team member"},
            {"id": "4", "name": "Travel request", "description": "Request travel approval"},
            {"id": "5", "name": "Purchase over $100", "description": "Purchase request over $100"},
        ]
    }

    # Queues for DEMOSD
    QUEUES = {
        "1": [
            {"id": "1", "name": "All open", "issueCount": 5},
            {"id": "2", "name": "Assigned to me", "issueCount": 0},
            {"id": "3", "name": "Unassigned", "issueCount": 5},
        ]
    }

    # SLA Definitions
    SLAS = {
        "1": {"name": "Time to first response", "completedCycles": []},
        "2": {"name": "Time to resolution", "completedCycles": []},
    }

    # JSM Transitions
    JSM_TRANSITIONS = [
        {"id": "11", "name": "Waiting for support"},
        {"id": "21", "name": "In Progress"},
        {"id": "31", "name": "Pending"},
        {"id": "41", "name": "Resolved"},
    ]

    # =========================================================================
    # Transitions
    # =========================================================================

    TRANSITIONS = [
        {"id": "11", "name": "To Do", "to": {"name": "To Do", "id": "10000"}},
        {"id": "21", "name": "In Progress", "to": {"name": "In Progress", "id": "10001"}},
        {"id": "31", "name": "Done", "to": {"name": "Done", "id": "10002"}},
    ]

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
        # Admin: Project role actors
        self._project_role_actors: Dict[tuple, List[Dict]] = {}
        # Agile: Sprints
        self._sprints = self._init_sprints()
        self._sprint_issues: Dict[int, List[str]] = {1: ["DEMO-85", "DEMO-86"]}
        # Collaborate: Watchers
        self._watchers: Dict[str, List[str]] = {}
        # Relationships: Issue links
        self._issue_links: Dict[str, List[Dict]] = {}
        self._next_link_id = 1000

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
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
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
                    "customfield_10014": "DEMO-84",  # Epic Link
                    "customfield_10016": 8,  # Story Points
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
                },
            },
            "DEMO-86": {
                "key": "DEMO-86",
                "id": "10086",
                "self": f"{self.base_url}/rest/api/3/issue/10086",
                "fields": {
                    "summary": "Login fails on mobile Safari",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Users report login button not responsive on iOS Safari.\n\nSteps to reproduce:\n1. Open app in Safari on iPhone\n2. Enter credentials\n3. Tap Login button\n\nExpected: User logs in\nActual: Nothing happens"
                                    }
                                ],
                            }
                        ],
                    },
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
                    "labels": ["demo", "mobile", "safari"],
                    "components": [
                        {"id": "10000", "name": "Mobile"},
                        {"id": "10001", "name": "Authentication"},
                    ],
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
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
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
                },
            },
            "DEMO-88": {
                "key": "DEMO-88",
                "id": "10088",
                "self": f"{self.base_url}/rest/api/3/issue/10088",
                "fields": {
                    "summary": "Dashboard redesign",
                    "description": None,
                    "issuetype": {"name": "Story", "id": "10001"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "Medium", "id": "3"},
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
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
                },
            },
            "DEMO-89": {
                "key": "DEMO-89",
                "id": "10089",
                "self": f"{self.base_url}/rest/api/3/issue/10089",
                "fields": {
                    "summary": "Performance optimization",
                    "description": None,
                    "issuetype": {"name": "Task", "id": "10003"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "Medium", "id": "3"},
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
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
                },
            },
            "DEMO-90": {
                "key": "DEMO-90",
                "id": "10090",
                "self": f"{self.base_url}/rest/api/3/issue/10090",
                "fields": {
                    "summary": "Add dark mode support",
                    "description": None,
                    "issuetype": {"name": "Story", "id": "10001"},
                    "status": {"name": "To Do", "id": "10000"},
                    "priority": {"name": "Low", "id": "4"},
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
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
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
                    "timetracking": {
                        "originalEstimate": "0m",
                        "remainingEstimate": "0m",
                        "originalEstimateSeconds": 0,
                        "remainingEstimateSeconds": 0,
                    },
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

    def _init_sprints(self) -> List[Dict]:
        """Initialize sprint data for agile scenarios."""
        return [
            {
                "id": 1,
                "self": f"{self.base_url}/rest/agile/1.0/sprint/1",
                "name": "Sprint 1",
                "state": "active",
                "startDate": "2025-01-01T00:00:00.000Z",
                "endDate": "2025-01-14T00:00:00.000Z",
                "originBoardId": 1,
                "goal": "Complete MVP features",
            }
        ]

    # =========================================================================
    # Time Parsing Helpers
    # =========================================================================

    def _parse_time_to_seconds(self, time_str: str) -> int:
        """Parse JIRA time format to seconds (e.g., '2d', '1d 4h', '30m')."""
        if not time_str:
            return 0
        total = 0
        # Weeks
        match = re.search(r'(\d+)w', time_str)
        if match:
            total += int(match.group(1)) * 5 * 8 * 3600  # 5 days per week
        # Days
        match = re.search(r'(\d+)d', time_str)
        if match:
            total += int(match.group(1)) * 8 * 3600  # 8 hours per day
        # Hours
        match = re.search(r'(\d+)h', time_str)
        if match:
            total += int(match.group(1)) * 3600
        # Minutes
        match = re.search(r'(\d+)m', time_str)
        if match:
            total += int(match.group(1)) * 60
        return total

    def _seconds_to_time_str(self, seconds: int) -> str:
        """Convert seconds to JIRA time format string."""
        if seconds == 0:
            return "0m"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        else:
            return f"{minutes}m"

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
        fields: Optional[List[str]] = None,
        max_results: int = 50,
        next_page_token: Optional[str] = None,
        start_at: Optional[int] = None,
        expand: str = None,
    ) -> Dict[str, Any]:
        """Search issues with JQL. Supports project, assignee, type, status, priority filtering."""
        issues = list(self._issues.values())
        jql_upper = jql.upper()

        # Normalize TYPE to ISSUETYPE
        jql_upper = jql_upper.replace("TYPE =", "ISSUETYPE =").replace("TYPE=", "ISSUETYPE=")

        # Filter by project - check DEMOSD first to avoid matching DEMO prefix
        if "PROJECT = DEMOSD" in jql_upper or "PROJECT=DEMOSD" in jql_upper:
            issues = [i for i in issues if i["key"].startswith("DEMOSD-")]
        elif "PROJECT = DEMO" in jql_upper or "PROJECT=DEMO" in jql_upper:
            # Filter DEMO but exclude DEMOSD
            issues = [i for i in issues if i["key"].startswith("DEMO-") and not i["key"].startswith("DEMOSD-")]

        # Filter by assignee
        if "ASSIGNEE" in jql_upper:
            jql_lower = jql.lower()
            if "currentuser()" in jql_lower:
                # currentUser() resolves to abc123 (Jason Krueger)
                issues = [
                    i for i in issues
                    if i["fields"].get("assignee") and i["fields"]["assignee"].get("accountId") == "abc123"
                ]
            elif "jane" in jql_lower:
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
        if "STATUS != DONE" in jql_upper or "STATUS!=DONE" in jql_upper or "STATUS <> DONE" in jql_upper:
            issues = [i for i in issues if i["fields"]["status"]["name"] != "Done"]
        elif "STATUS = \"IN PROGRESS\"" in jql_upper or "STATUS=\"IN PROGRESS\"" in jql_upper:
            issues = [i for i in issues if i["fields"]["status"]["name"] == "In Progress"]
        elif "STATUS = \"TO DO\"" in jql_upper or "STATUS=\"TO DO\"" in jql_upper:
            issues = [i for i in issues if i["fields"]["status"]["name"] == "To Do"]
        elif "STATUS = OPEN" in jql_upper or "STATUS=OPEN" in jql_upper:
            issues = [i for i in issues if i["fields"]["status"]["name"] != "Done"]

        # Filter by priority
        if "PRIORITY = HIGH" in jql_upper or "PRIORITY=HIGH" in jql_upper:
            issues = [i for i in issues if i["fields"]["priority"]["name"] == "High"]
        elif "PRIORITY = MEDIUM" in jql_upper or "PRIORITY=MEDIUM" in jql_upper:
            issues = [i for i in issues if i["fields"]["priority"]["name"] == "Medium"]
        elif "PRIORITY = LOW" in jql_upper or "PRIORITY=LOW" in jql_upper:
            issues = [i for i in issues if i["fields"]["priority"]["name"] == "Low"]

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
        text_match = re.search(r'TEXT\s*~\s*["\']([^"\']+)["\']', jql, re.IGNORECASE)
        if text_match:
            search_term = text_match.group(1).lower()
            issues = [
                i for i in issues
                if search_term in i["fields"].get("summary", "").lower()
            ]

        # Summary search (summary ~ "keyword")
        summary_match = re.search(r'SUMMARY\s*~\s*["\']([^"\']+)["\']', jql, re.IGNORECASE)
        if summary_match:
            search_term = summary_match.group(1).lower()
            issues = [
                i for i in issues
                if search_term in i["fields"].get("summary", "").lower()
            ]

        # Epic Link filter ("Epic Link" = DEMO-84)
        epic_link_match = re.search(r'"Epic Link"\s*=\s*(\w+-\d+)', jql, re.IGNORECASE)
        if epic_link_match:
            epic_key = epic_link_match.group(1)
            issues = [
                i for i in issues
                if i["fields"].get("customfield_10014") == epic_key
            ]

        # Parent filter (for subtasks)
        parent_match = re.search(r'parent\s*=\s*(\w+-\d+)', jql, re.IGNORECASE)
        if parent_match:
            parent_key = parent_match.group(1)
            issues = [
                i for i in issues
                if i["fields"].get("parent", {}).get("key") == parent_key
            ]

        # Sprint filter (sprint in openSprints() or sprint in (active))
        if "SPRINT" in jql_upper:
            if "SPRINT IN OPENSPRINTS()" in jql_upper or "SPRINT IN (ACTIVE)" in jql_upper:
                # Find issues in active sprints
                active_issue_keys = set()
                for sprint in self._sprints:
                    if sprint.get("state") == "active":
                        active_issue_keys.update(self._sprint_issues.get(sprint["id"], []))
                issues = [i for i in issues if i["key"] in active_issue_keys]

        # Pagination
        offset = start_at or 0
        paginated = issues[offset:offset + max_results]
        is_last = offset + len(paginated) >= len(issues)

        return {
            "startAt": offset,
            "maxResults": max_results,
            "total": len(issues),
            "issues": paginated,
            "isLast": is_last,
            "nextPageToken": None if is_last else f"token_{offset + max_results}",
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

        # Get priority name with proper ID mapping
        priority = fields.get("priority", {})
        if isinstance(priority, dict):
            priority_name = priority.get("name", "Medium")
            priority_id = priority.get("id", "3")
        else:
            priority_name = "Medium"
            priority_id = "3"

        # Map priority names to IDs
        priority_id_map = {"Highest": "1", "High": "2", "Medium": "3", "Low": "4", "Lowest": "5"}
        if priority_name in priority_id_map:
            priority_id = priority_id_map[priority_name]

        new_issue = {
            "key": issue_key,
            "id": issue_id,
            "self": f"{self.base_url}/rest/api/3/issue/{issue_id}",
            "fields": {
                "summary": fields.get("summary", "New Issue"),
                "description": fields.get("description"),
                "issuetype": {"name": type_name, "id": "10000"},
                "status": {"name": "To Do", "id": "10000"},
                "priority": {"name": priority_name, "id": priority_id},
                "assignee": fields.get("assignee"),
                "reporter": self.USERS["abc123"],
                "project": {"key": project_key, "name": "Demo Project", "id": "10000"},
                "created": "2025-01-08T10:00:00.000+0000",
                "updated": "2025-01-08T10:00:00.000+0000",
                "labels": fields.get("labels", []),
                "timetracking": {
                    "originalEstimate": "0m",
                    "remainingEstimate": "0m",
                    "originalEstimateSeconds": 0,
                    "remainingEstimateSeconds": 0,
                },
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
            for key, value in fields.items():
                self._issues[issue_key]["fields"][key] = value
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
            self._issues[issue_key]["fields"]["assignee"] = {
                "accountId": account_id,
                "displayName": "Unknown User",
            }

    # =========================================================================
    # Transitions
    # =========================================================================

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

        for t in self.TRANSITIONS:
            if t["id"] == transition_id:
                self._issues[issue_key]["fields"]["status"] = t["to"]
                break

    # =========================================================================
    # Comments
    # =========================================================================

    def add_comment(
        self,
        issue_key: str,
        body: Dict[str, Any],
        visibility: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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

        if visibility:
            comment["visibility"] = visibility

        self._comments[issue_key].append(comment)
        return comment

    def add_comment_with_visibility(
        self,
        issue_key: str,
        body: Dict[str, Any],
        visibility_type: str = None,
        visibility_value: str = None,
    ) -> Dict[str, Any]:
        """Add a comment with visibility restrictions."""
        visibility = None
        if visibility_type and visibility_value:
            visibility = {
                "type": visibility_type,
                "value": visibility_value,
                "identifier": visibility_value,
            }
        return self.add_comment(issue_key, body, visibility)

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
    # Watchers (Collaborate)
    # =========================================================================

    def get_watchers(self, issue_key: str) -> Dict[str, Any]:
        """Get watchers for an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        watcher_ids = self._watchers.get(issue_key, [])
        watchers = [self.USERS[uid] for uid in watcher_ids if uid in self.USERS]

        return {
            "self": f"{self.base_url}/rest/api/3/issue/{issue_key}/watchers",
            "isWatching": self.get_current_user_id() in watcher_ids,
            "watchCount": len(watchers),
            "watchers": watchers,
        }

    def add_watcher(self, issue_key: str, account_id: str) -> None:
        """Add a watcher to an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        if issue_key not in self._watchers:
            self._watchers[issue_key] = []

        if account_id not in self._watchers[issue_key]:
            self._watchers[issue_key].append(account_id)

    def remove_watcher(self, issue_key: str, account_id: str) -> None:
        """Remove a watcher from an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        if issue_key in self._watchers and account_id in self._watchers[issue_key]:
            self._watchers[issue_key].remove(account_id)

    # =========================================================================
    # Changelog (Collaborate)
    # =========================================================================

    def get_changelog(
        self, issue_key: str, start_at: int = 0, max_results: int = 100
    ) -> Dict[str, Any]:
        """Get issue changelog (activity history)."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        # Return mock changelog entries
        values = [
            {
                "id": "1001",
                "author": self.USERS["abc123"],
                "created": "2025-01-02T10:00:00.000+0000",
                "items": [
                    {
                        "field": "status",
                        "fieldtype": "jira",
                        "fieldId": "status",
                        "from": "10000",
                        "fromString": "To Do",
                        "to": "10001",
                        "toString": "In Progress",
                    }
                ],
            },
            {
                "id": "1002",
                "author": self.USERS["abc123"],
                "created": "2025-01-03T14:30:00.000+0000",
                "items": [
                    {
                        "field": "assignee",
                        "fieldtype": "jira",
                        "fieldId": "assignee",
                        "from": "abc123",
                        "fromString": "Jason Krueger",
                        "to": "def456",
                        "toString": "Jane Manager",
                    }
                ],
            },
        ]

        paginated = values[start_at : start_at + max_results]

        return {
            "self": f"{self.base_url}/rest/api/3/issue/{issue_key}/changelog",
            "maxResults": max_results,
            "startAt": start_at,
            "total": len(values),
            "isLast": (start_at + len(paginated)) >= len(values),
            "values": paginated,
        }

    # =========================================================================
    # Notifications (Collaborate)
    # =========================================================================

    def notify_issue(
        self,
        issue_key: str,
        subject: str = None,
        text_body: str = None,
        html_body: str = None,
        to: Dict[str, Any] = None,
        restrict: Dict[str, Any] = None,
    ) -> None:
        """Send notification about an issue (no-op for mock, just validates issue exists)."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

    # =========================================================================
    # Worklogs
    # =========================================================================

    def add_worklog(
        self,
        issue_key: str,
        time_spent: str,
        started: Optional[str] = None,
        comment: Optional[Dict[str, Any]] = None,
        adjust_estimate: str = "auto",
        new_estimate: Optional[str] = None,
        reduce_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a worklog to an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        if issue_key not in self._worklogs:
            self._worklogs[issue_key] = []

        worklog_id = str(len(self._worklogs[issue_key]) + 1)
        time_spent_seconds = self._parse_time_to_seconds(time_spent)

        worklog = {
            "id": worklog_id,
            "timeSpent": time_spent,
            "timeSpentSeconds": time_spent_seconds,
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

    def get_worklog(self, issue_key: str, worklog_id: str) -> Dict[str, Any]:
        """Get a specific worklog."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        for worklog in self._worklogs.get(issue_key, []):
            if worklog["id"] == worklog_id:
                return worklog

        from .error_handler import NotFoundError
        raise NotFoundError(f"Worklog {worklog_id} not found")

    def update_worklog(
        self,
        issue_key: str,
        worklog_id: str,
        time_spent: Optional[str] = None,
        started: Optional[str] = None,
        comment: Optional[Dict[str, Any]] = None,
        adjust_estimate: str = "auto",
        new_estimate: Optional[str] = None,
        visibility_type: Optional[str] = None,
        visibility_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing worklog."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        for worklog in self._worklogs.get(issue_key, []):
            if worklog["id"] == worklog_id:
                if time_spent is not None:
                    worklog["timeSpent"] = time_spent
                    worklog["timeSpentSeconds"] = self._parse_time_to_seconds(time_spent)
                if started is not None:
                    worklog["started"] = started
                if comment is not None:
                    worklog["comment"] = comment
                worklog["updated"] = "2025-01-08T10:00:00.000+0000"
                return worklog

        from .error_handler import NotFoundError
        raise NotFoundError(f"Worklog {worklog_id} not found")

    def delete_worklog(
        self,
        issue_key: str,
        worklog_id: str,
        adjust_estimate: str = "auto",
        new_estimate: Optional[str] = None,
        increase_by: Optional[str] = None,
    ) -> None:
        """Delete a worklog."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        worklogs = self._worklogs.get(issue_key, [])
        original_len = len(worklogs)
        self._worklogs[issue_key] = [w for w in worklogs if w["id"] != worklog_id]

        if len(self._worklogs[issue_key]) == original_len:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Worklog {worklog_id} not found")

    # =========================================================================
    # Time Tracking
    # =========================================================================

    def get_time_tracking(self, issue_key: str) -> Dict[str, Any]:
        """Get time tracking info for an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        # Calculate from worklogs
        worklogs = self._worklogs.get(issue_key, [])
        time_spent_seconds = sum(w.get("timeSpentSeconds", 0) for w in worklogs)

        # Get stored estimates from issue fields
        issue_fields = self._issues[issue_key].get("fields", {})
        timetracking = issue_fields.get("timetracking", {})

        return {
            "originalEstimate": timetracking.get("originalEstimate", "0m"),
            "remainingEstimate": timetracking.get("remainingEstimate", "0m"),
            "timeSpent": self._seconds_to_time_str(time_spent_seconds),
            "originalEstimateSeconds": timetracking.get("originalEstimateSeconds", 0),
            "remainingEstimateSeconds": timetracking.get("remainingEstimateSeconds", 0),
            "timeSpentSeconds": time_spent_seconds,
        }

    def set_time_tracking(
        self,
        issue_key: str,
        original_estimate: Optional[str] = None,
        remaining_estimate: Optional[str] = None,
    ) -> None:
        """Set time tracking estimates on an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        if "timetracking" not in self._issues[issue_key]["fields"]:
            self._issues[issue_key]["fields"]["timetracking"] = {}

        tt = self._issues[issue_key]["fields"]["timetracking"]

        if original_estimate is not None:
            tt["originalEstimate"] = original_estimate
            tt["originalEstimateSeconds"] = self._parse_time_to_seconds(original_estimate)

        if remaining_estimate is not None:
            tt["remainingEstimate"] = remaining_estimate
            tt["remainingEstimateSeconds"] = self._parse_time_to_seconds(remaining_estimate)

    # =========================================================================
    # Users
    # =========================================================================

    def search_users(
        self,
        query: str = "",
        max_results: int = 50,
        start_at: int = 0,
        account_id: str = None,
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

        if username:
            for user in self.USERS.values():
                if username.lower() in user["displayName"].lower():
                    return user

        from .error_handler import NotFoundError
        raise NotFoundError("User not found")

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
    # Admin: Permissions
    # =========================================================================

    def get_my_permissions(
        self,
        project_key: Optional[str] = None,
        permissions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get current user's permissions."""
        if permissions:
            perm_list = [p.strip() for p in permissions.split(",")]
        else:
            perm_list = list(self.MOCK_USER_PERMISSIONS.keys())

        result = {"permissions": {}}
        for perm in perm_list:
            have_perm = self.MOCK_USER_PERMISSIONS.get(perm, False)
            result["permissions"][perm] = {
                "id": perm,
                "key": perm,
                "name": perm.replace("_", " ").title(),
                "description": f"Permission to {perm.lower().replace('_', ' ')}",
                "havePermission": have_perm,
            }

        return result

    # =========================================================================
    # Admin: Project Roles
    # =========================================================================

    def get_project_roles_for_project(self, project_key: str) -> Dict[str, str]:
        """Get all roles for a project with their URLs."""
        if project_key not in [p["key"] for p in self.PROJECTS]:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Project {project_key} not found")

        result = {}
        for role in self.PROJECT_ROLES:
            result[role["name"]] = f"{self.base_url}/rest/api/3/project/{project_key}/role/{role['id']}"
        return result

    def get_project_role_actors(
        self, project_key: str, role_id: int
    ) -> Dict[str, Any]:
        """Get actors (users/groups) for a project role."""
        role = None
        for r in self.PROJECT_ROLES:
            if r["id"] == role_id:
                role = r
                break

        if not role:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Role {role_id} not found")

        key = (project_key, role_id)
        actors = self._project_role_actors.get(key, [])

        # For Administrators role, add current user by default
        if role["name"] == "Administrators" and not actors:
            actors = [
                {
                    "id": 10100,
                    "type": "atlassian-user-role-actor",
                    "displayName": "Jason Krueger",
                    "actorUser": {
                        "accountId": "abc123",
                        "emailAddress": "jasonkrue@gmail.com",
                    },
                }
            ]

        return {
            "id": role_id,
            "name": role["name"],
            "description": role.get("description", ""),
            "actors": actors,
            "self": f"{self.base_url}/rest/api/3/project/{project_key}/role/{role_id}",
        }

    def add_user_to_project_role(
        self, project_key: str, role_id: int, account_id: str
    ) -> Dict[str, Any]:
        """Add a user to a project role."""
        key = (project_key, role_id)
        if key not in self._project_role_actors:
            self._project_role_actors[key] = []

        user = self.USERS.get(account_id, {"displayName": "Unknown", "emailAddress": ""})

        # Check if already in role
        for actor in self._project_role_actors[key]:
            if actor.get("actorUser", {}).get("accountId") == account_id:
                return self.get_project_role_actors(project_key, role_id)

        self._project_role_actors[key].append({
            "id": 10000 + len(self._project_role_actors[key]),
            "type": "atlassian-user-role-actor",
            "displayName": user.get("displayName", "Unknown"),
            "actorUser": {
                "accountId": account_id,
                "emailAddress": user.get("emailAddress", ""),
            },
        })

        return self.get_project_role_actors(project_key, role_id)

    def remove_user_from_project_role(
        self, project_key: str, role_id: int, account_id: str
    ) -> None:
        """Remove a user from a project role."""
        key = (project_key, role_id)
        if key in self._project_role_actors:
            self._project_role_actors[key] = [
                a for a in self._project_role_actors[key]
                if a.get("actorUser", {}).get("accountId") != account_id
            ]

    # =========================================================================
    # Admin: Groups
    # =========================================================================

    def find_groups(
        self,
        query: str = "",
        start_at: int = 0,
        max_results: int = 50,
        exclude_id: Optional[list] = None,
        caseInsensitive: bool = True,
    ) -> Dict[str, Any]:
        """Find groups by name."""
        groups = self.GROUPS

        if query:
            query_check = query.lower() if caseInsensitive else query
            groups = [
                g for g in groups
                if (query_check in g["name"].lower() if caseInsensitive else query in g["name"])
            ]

        if exclude_id:
            groups = [g for g in groups if g["groupId"] not in exclude_id]

        return {
            "groups": groups[start_at:start_at + max_results],
            "total": len(groups),
        }

    # =========================================================================
    # Projects
    # =========================================================================

    def get_project(
        self,
        project_key: str,
        expand: str = None,
        properties: list = None,
    ) -> Dict[str, Any]:
        """Get project by key with optional expansion."""
        for project in self.PROJECTS:
            if project["key"] == project_key:
                result = project.copy()

                # Add expanded fields for configuration
                if expand:
                    expand_list = expand if isinstance(expand, list) else [expand]

                    if any("description" in e for e in expand_list):
                        result["description"] = "Demo project for testing"

                    if any("lead" in e for e in expand_list):
                        result["lead"] = self.USERS["abc123"]

                    if any("issueTypes" in e for e in expand_list):
                        result["issueTypes"] = [
                            {"id": "10000", "name": "Epic", "subtask": False},
                            {"id": "10001", "name": "Story", "subtask": False},
                            {"id": "10002", "name": "Bug", "subtask": False},
                            {"id": "10003", "name": "Task", "subtask": False},
                            {"id": "10004", "name": "Sub-task", "subtask": True},
                        ]

                    if any("components" in e for e in expand_list):
                        result["components"] = [
                            {"id": "10000", "name": "Backend"},
                            {"id": "10001", "name": "Frontend"},
                        ]

                    if any("versions" in e for e in expand_list):
                        result["versions"] = [
                            {"id": "10000", "name": "1.0", "released": True},
                            {"id": "10001", "name": "2.0", "released": False},
                        ]

                # Add scheme info
                result["permissionScheme"] = {"id": "10000", "name": "Default Software Scheme"}
                result["notificationScheme"] = {"id": "10000", "name": "Default Notification Scheme"}
                result["issueTypeScreenScheme"] = {"id": "1", "name": "Default Issue Type Screen Scheme"}
                result["assigneeType"] = "PROJECT_LEAD"
                result["simplified"] = False
                result["isPrivate"] = False

                return result

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
    # Agile: Boards
    # =========================================================================

    def get_all_boards(
        self,
        project_key: Optional[str] = None,
        board_type: Optional[str] = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> Dict[str, Any]:
        """Get all boards, optionally filtered by project."""
        boards = self.BOARDS
        if project_key:
            boards = [b for b in boards if b.get("location", {}).get("projectKey") == project_key]
        if board_type:
            boards = [b for b in boards if b.get("type") == board_type]
        return {
            "maxResults": max_results,
            "startAt": start_at,
            "total": len(boards),
            "isLast": True,
            "values": boards[start_at:start_at + max_results],
        }

    def get_board(self, board_id: int) -> Dict[str, Any]:
        """Get board by ID."""
        for board in self.BOARDS:
            if board["id"] == board_id:
                return board
        from .error_handler import NotFoundError
        raise NotFoundError(f"Board {board_id} not found")

    # =========================================================================
    # Agile: Sprints
    # =========================================================================

    def get_board_sprints(
        self,
        board_id: int,
        state: Optional[str] = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> Dict[str, Any]:
        """Get sprints for a board."""
        sprints = [s for s in self._sprints if s.get("originBoardId") == board_id]
        if state:
            sprints = [s for s in sprints if s.get("state") == state]
        return {
            "maxResults": max_results,
            "startAt": start_at,
            "total": len(sprints),
            "isLast": True,
            "values": sprints[start_at:start_at + max_results],
        }

    def get_sprint(self, sprint_id: int) -> Dict[str, Any]:
        """Get sprint by ID."""
        for sprint in self._sprints:
            if sprint["id"] == sprint_id:
                return sprint
        from .error_handler import NotFoundError
        raise NotFoundError(f"Sprint {sprint_id} not found")

    def get_sprint_issues(
        self,
        sprint_id: int,
        fields: Optional[list] = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> Dict[str, Any]:
        """Get issues in a sprint."""
        issue_keys = self._sprint_issues.get(sprint_id, [])
        issues = [self._issues[k] for k in issue_keys if k in self._issues]
        return {
            "maxResults": max_results,
            "startAt": start_at,
            "total": len(issues),
            "issues": issues[start_at:start_at + max_results],
        }

    def move_issues_to_sprint(
        self,
        sprint_id: int,
        issue_keys: list,
        rank: Optional[str] = None,
    ) -> None:
        """Move issues to a sprint."""
        if sprint_id not in [s["id"] for s in self._sprints]:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Sprint {sprint_id} not found")

        if sprint_id not in self._sprint_issues:
            self._sprint_issues[sprint_id] = []

        for key in issue_keys:
            if key not in self._issues:
                from .error_handler import NotFoundError
                raise NotFoundError(f"Issue {key} not found")
            # Remove from other sprints
            for sid in self._sprint_issues:
                if key in self._sprint_issues[sid]:
                    self._sprint_issues[sid].remove(key)
            # Add to target sprint
            if key not in self._sprint_issues[sprint_id]:
                self._sprint_issues[sprint_id].append(key)

    def get_board_backlog(
        self,
        board_id: int,
        jql: Optional[str] = None,
        fields: Optional[list] = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> Dict[str, Any]:
        """Get backlog issues for a board."""
        # Get all issues not in any active sprint
        active_sprint_issues = set()
        for sprint in self._sprints:
            if sprint.get("state") == "active":
                active_sprint_issues.update(self._sprint_issues.get(sprint["id"], []))

        # Backlog = project issues not in active sprint
        board = self.get_board(board_id)
        project_key = board.get("location", {}).get("projectKey", "DEMO")

        backlog_issues = [
            issue for key, issue in self._issues.items()
            if key.startswith(f"{project_key}-") and key not in active_sprint_issues
        ]

        return {
            "maxResults": max_results,
            "startAt": start_at,
            "total": len(backlog_issues),
            "issues": backlog_issues[start_at:start_at + max_results],
        }

    # =========================================================================
    # Relationships: Issue Links
    # =========================================================================

    def get_link_types(self) -> list:
        """Get all available issue link types."""
        return self.LINK_TYPES

    def get_issue_links(self, issue_key: str) -> list:
        """Get all links for an issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        return self._issue_links.get(issue_key, [])

    def create_link(
        self,
        link_type: str,
        inward_key: str,
        outward_key: str,
        comment: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a link between two issues."""
        if inward_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {inward_key} not found")
        if outward_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {outward_key} not found")

        # Find link type info
        link_type_info = None
        for lt in self.LINK_TYPES:
            if lt["name"].lower() == link_type.lower():
                link_type_info = lt
                break

        if not link_type_info:
            from .error_handler import ValidationError
            raise ValidationError(f"Unknown link type: {link_type}")

        self._next_link_id += 1
        link_id = str(self._next_link_id)

        # Create outward link for inward_key
        outward_link = {
            "id": link_id,
            "type": link_type_info,
            "outwardIssue": self._issues[outward_key],
        }
        if inward_key not in self._issue_links:
            self._issue_links[inward_key] = []
        self._issue_links[inward_key].append(outward_link)

        # Create inward link for outward_key
        inward_link = {
            "id": link_id,
            "type": link_type_info,
            "inwardIssue": self._issues[inward_key],
        }
        if outward_key not in self._issue_links:
            self._issue_links[outward_key] = []
        self._issue_links[outward_key].append(inward_link)

    def get_link(self, link_id: str) -> Dict[str, Any]:
        """Get a specific issue link by ID."""
        for links in self._issue_links.values():
            for link in links:
                if link["id"] == link_id:
                    return link
        from .error_handler import NotFoundError
        raise NotFoundError(f"Issue link {link_id} not found")

    def delete_link(self, link_id: str) -> None:
        """Delete an issue link."""
        found = False
        for issue_key in self._issue_links:
            original_len = len(self._issue_links[issue_key])
            self._issue_links[issue_key] = [
                l for l in self._issue_links[issue_key] if l["id"] != link_id
            ]
            if len(self._issue_links[issue_key]) < original_len:
                found = True
        if not found:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue link {link_id} not found")

    def clone_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        clone_subtasks: bool = False,
        clone_links: bool = False,
    ) -> Dict[str, Any]:
        """Clone an issue by copying its fields to a new issue."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Issue {issue_key} not found")

        original = self._issues[issue_key]
        original_fields = original["fields"]

        clone_fields = {
            "project": {"key": original_fields["project"]["key"]},
            "issuetype": original_fields["issuetype"],
            "summary": summary or original_fields.get("summary", "Clone"),
            "description": original_fields.get("description"),
            "priority": original_fields.get("priority"),
            "labels": original_fields.get("labels", []),
        }

        clone = self.create_issue(clone_fields)

        # Create Cloners link
        try:
            self.create_link("Cloners", issue_key, clone["key"])
        except Exception:
            pass

        # Clone links if requested
        if clone_links:
            for link in self._issue_links.get(issue_key, []):
                link_type = link["type"]["name"]
                if link_type == "Cloners":
                    continue
                if "outwardIssue" in link:
                    try:
                        self.create_link(link_type, clone["key"], link["outwardIssue"]["key"])
                    except Exception:
                        pass
                elif "inwardIssue" in link:
                    try:
                        self.create_link(link_type, link["inwardIssue"]["key"], clone["key"])
                    except Exception:
                        pass

        return clone

    # =========================================================================
    # Fields: Field Management
    # =========================================================================

    def _get_createmeta(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get issue create metadata for a project."""
        params = params or {}
        project_key = params.get("projectKeys", "DEMO")
        issue_type_name = params.get("issuetypeNames")

        issue_types = [
            {"id": "10000", "name": "Epic", "fields": self._get_issue_type_fields("Epic")},
            {"id": "10001", "name": "Story", "fields": self._get_issue_type_fields("Story")},
            {"id": "10002", "name": "Bug", "fields": self._get_issue_type_fields("Bug")},
            {"id": "10003", "name": "Task", "fields": self._get_issue_type_fields("Task")},
        ]

        if issue_type_name:
            issue_types = [it for it in issue_types if it["name"].lower() == issue_type_name.lower()]

        return {
            "projects": [{
                "key": project_key,
                "name": "Demo Project",
                "issuetypes": issue_types,
            }]
        }

    def _get_issue_type_fields(self, issue_type: str) -> Dict[str, Any]:
        """Get fields available for an issue type."""
        base_fields = {
            "summary": {"name": "Summary", "required": True},
            "description": {"name": "Description", "required": False},
            "priority": {"name": "Priority", "required": False},
            "labels": {"name": "Labels", "required": False},
            "assignee": {"name": "Assignee", "required": False},
        }

        if issue_type in ["Story", "Bug", "Task"]:
            base_fields["customfield_10016"] = {"name": "Story Points", "required": False}
            base_fields["customfield_10014"] = {"name": "Epic Link", "required": False}
            base_fields["customfield_10020"] = {"name": "Sprint", "required": False}

        if issue_type == "Epic":
            base_fields["customfield_10011"] = {"name": "Epic Name", "required": True}
            base_fields["customfield_10012"] = {"name": "Epic Color", "required": False}

        return base_fields

    def _get_screens(self) -> Dict[str, Any]:
        """Get all screens."""
        return {
            "values": [
                {"id": 1, "name": "Default Screen"},
                {"id": 2, "name": "DEMO: Scrum Default Issue Screen"},
                {"id": 3, "name": "DEMO: Scrum Bug Screen"},
            ]
        }

    def _get_screen(self, screen_id: int) -> Dict[str, Any]:
        """Get a specific screen."""
        screens = {
            1: {"id": 1, "name": "Default Screen"},
            2: {"id": 2, "name": "DEMO: Scrum Default Issue Screen"},
            3: {"id": 3, "name": "DEMO: Scrum Bug Screen"},
        }
        return screens.get(screen_id, {"id": screen_id, "name": f"Screen {screen_id}"})

    def _get_screen_tabs(self, screen_id: int) -> list:
        """Get tabs for a screen."""
        return [{"id": 1, "name": "Field Tab"}]

    def _get_screen_tab_fields(self, screen_id: int, tab_id: int) -> list:
        """Get fields for a screen tab."""
        return [
            {"id": "summary", "name": "Summary"},
            {"id": "description", "name": "Description"},
            {"id": "priority", "name": "Priority"},
            {"id": "customfield_10016", "name": "Story Points"},
        ]

    def _get_issuetype_screen_scheme(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get issue type screen scheme for a project."""
        return {
            "values": [{
                "issueTypeScreenScheme": {
                    "id": "1",
                    "name": "DEMO Issue Type Screen Scheme",
                }
            }]
        }

    def _get_issuetype_screen_scheme_mapping(self, scheme_id: str) -> Dict[str, Any]:
        """Get mapping for an issue type screen scheme."""
        return {
            "values": [{
                "issueTypeId": "default",
                "screenSchemeId": "1",
            }]
        }

    def _get_screen_scheme(self, scheme_id: str) -> Dict[str, Any]:
        """Get a screen scheme."""
        return {
            "id": scheme_id,
            "name": "Default Screen Scheme",
            "screens": {
                "default": 1,
                "create": 2,
                "edit": 2,
            },
        }

    # =========================================================================
    # Dev: Development Information
    # =========================================================================

    def _get_dev_info(self, issue_id: str) -> Dict[str, Any]:
        """Return mock development information for an issue."""
        dev_info = {
            "10086": {  # DEMO-86
                "detail": [
                    {
                        "repositories": [
                            {
                                "name": "demo-app",
                                "url": "https://github.com/example/demo-app",
                                "commits": [
                                    {
                                        "id": "abc123def456789",
                                        "displayId": "abc123d",
                                        "message": "fix(DEMO-86): fix login button on mobile Safari",
                                        "url": "https://github.com/example/demo-app/commit/abc123def456789",
                                        "author": {
                                            "name": "Jane Manager",
                                            "email": "jane@example.com",
                                        },
                                        "authorTimestamp": "2025-01-01T12:00:00.000+0000",
                                    },
                                ],
                            }
                        ]
                    }
                ]
            },
        }
        return dev_info.get(issue_id, {"detail": []})

    # =========================================================================
    # JSM Service Desk Operations
    # =========================================================================

    def get_service_desks(self, start: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Get all service desks."""
        return {
            "size": len(self.SERVICE_DESKS),
            "start": start,
            "limit": limit,
            "isLastPage": True,
            "values": self.SERVICE_DESKS,
        }

    def get_service_desk(self, service_desk_id: str) -> Dict[str, Any]:
        """Get service desk by ID."""
        for sd in self.SERVICE_DESKS:
            if sd["id"] == service_desk_id:
                return sd
        from .error_handler import NotFoundError
        raise NotFoundError(f"Service desk {service_desk_id} not found")

    def lookup_service_desk_by_project_key(self, project_key: str) -> Dict[str, Any]:
        """Lookup service desk by project key."""
        for sd in self.SERVICE_DESKS:
            if sd.get("projectKey") == project_key:
                return sd
        from .error_handler import JiraError
        raise JiraError(f"No service desk found for project key: {project_key}")

    def get_service_desk_queues(
        self,
        service_desk_id: int,
        include_count: bool = False,
        start: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get queues for a service desk."""
        queues = self.QUEUES.get(str(service_desk_id), [])
        return {
            "size": len(queues),
            "start": start,
            "limit": limit,
            "isLastPage": True,
            "values": queues,
        }

    def get_queues(
        self,
        service_desk_id: int,
        include_count: bool = False,
        start: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Alias for get_service_desk_queues."""
        return self.get_service_desk_queues(service_desk_id, include_count, start, limit)

    def get_queue(self, service_desk_id: int, queue_id: int) -> Dict[str, Any]:
        """Get a specific queue by ID."""
        queues = self.QUEUES.get(str(service_desk_id), [])
        for queue in queues:
            if queue["id"] == str(queue_id):
                return queue
        from .error_handler import NotFoundError
        raise NotFoundError(f"Queue {queue_id} not found in service desk {service_desk_id}")

    def get_queue_issues(
        self,
        service_desk_id: int,
        queue_id: int,
        start: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get issues in a service desk queue."""
        demosd_issues = [i for i in self._issues.values() if i["key"].startswith("DEMOSD-")]

        queue = self.get_queue(service_desk_id, queue_id)
        queue_name = queue.get("name", "").lower()

        if "unassigned" in queue_name:
            demosd_issues = [i for i in demosd_issues if i["fields"].get("assignee") is None]
        elif "assigned to me" in queue_name:
            demosd_issues = [i for i in demosd_issues if i["fields"].get("assignee", {}).get("accountId") == "abc123"]

        paginated = demosd_issues[start : start + limit]
        return {
            "size": len(paginated),
            "start": start,
            "limit": limit,
            "isLastPage": start + limit >= len(demosd_issues),
            "values": paginated,
        }

    def get_request_types(
        self,
        service_desk_id: str,
        start: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get request types for a service desk."""
        types = self.REQUEST_TYPES.get(service_desk_id, [])
        return {
            "size": len(types),
            "start": start,
            "limit": limit,
            "isLastPage": True,
            "values": types,
        }

    # =========================================================================
    # JSM Request Operations
    # =========================================================================

    def get_request(self, issue_key: str, expand: Optional[list] = None) -> Dict[str, Any]:
        """Get JSM request details."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Request {issue_key} not found")

        issue = self._issues[issue_key]
        return {
            "issueId": issue["id"],
            "issueKey": issue_key,
            "requestTypeId": issue.get("requestTypeId", "1"),
            "serviceDeskId": issue.get("serviceDeskId", "1"),
            "currentStatus": issue.get("currentStatus", {"status": "Open"}),
            "reporter": issue["fields"].get("reporter"),
            "requestFieldValues": [
                {"fieldId": "summary", "label": "Summary", "value": issue["fields"].get("summary")},
                {"fieldId": "description", "label": "Description", "value": issue["fields"].get("description")},
            ],
        }

    def get_request_status(self, issue_key: str) -> Dict[str, Any]:
        """Get the status of a JSM request."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Request {issue_key} not found")

        issue = self._issues[issue_key]
        return issue.get("currentStatus", {"status": issue["fields"]["status"]["name"]})

    def get_request_slas(
        self,
        issue_key: str,
        start: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get SLAs for a request."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Request {issue_key} not found")

        return {
            "size": 2,
            "start": start,
            "limit": limit,
            "isLastPage": True,
            "values": [
                {
                    "id": "1",
                    "name": "Time to first response",
                    "completedCycles": [],
                    "ongoingCycle": {
                        "startTime": {"iso8601": "2025-01-01T10:00:00+0000"},
                        "breachTime": {"iso8601": "2025-01-02T10:00:00+0000"},
                        "remainingTime": {"millis": 86400000, "friendly": "24h"},
                        "breached": False,
                    },
                },
                {
                    "id": "2",
                    "name": "Time to resolution",
                    "completedCycles": [],
                    "ongoingCycle": {
                        "startTime": {"iso8601": "2025-01-01T10:00:00+0000"},
                        "breachTime": {"iso8601": "2025-01-08T10:00:00+0000"},
                        "remainingTime": {"millis": 604800000, "friendly": "7d"},
                        "breached": False,
                    },
                },
            ],
        }

    def get_request_sla(
        self,
        issue_key: str,
        sla_metric_id: str = None,
    ) -> Dict[str, Any]:
        """Get a specific SLA for a request."""
        if sla_metric_id:
            slas = self.get_request_slas(issue_key)
            for sla in slas.get("values", []):
                if sla["id"] == sla_metric_id:
                    return sla
            from .error_handler import NotFoundError
            raise NotFoundError(f"SLA {sla_metric_id} not found")
        return self.get_request_slas(issue_key)

    # =========================================================================
    # JSM Request Comments
    # =========================================================================

    def add_request_comment(
        self,
        issue_key: str,
        body: str,
        public: bool = True,
    ) -> Dict[str, Any]:
        """Add a JSM comment with visibility."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Request {issue_key} not found")

        if issue_key not in self._comments:
            self._comments[issue_key] = []

        comment_id = str(len(self._comments[issue_key]) + 1)
        comment = {
            "id": comment_id,
            "body": body,
            "public": public,
            "author": self.USERS["abc123"],
            "created": {"iso8601": "2025-01-08T10:00:00+0000"},
        }
        self._comments[issue_key].append(comment)
        return comment

    def get_request_comments(
        self,
        issue_key: str,
        public: bool = None,
        internal: bool = None,
        start: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get JSM comments with visibility filter."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Request {issue_key} not found")

        comments = self._comments.get(issue_key, [])

        if internal is not None and public is None:
            public = not internal
        if public is not None:
            comments = [c for c in comments if c.get("public") == public]

        return {
            "size": len(comments),
            "start": start,
            "limit": limit,
            "isLastPage": True,
            "values": comments[start : start + limit],
        }

    # =========================================================================
    # JSM Request Transitions
    # =========================================================================

    def get_request_transitions(self, issue_key: str) -> list:
        """Get available JSM transitions for a request."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Request {issue_key} not found")
        return self.JSM_TRANSITIONS

    def transition_request(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None,
        public: bool = True,
    ) -> None:
        """Transition a JSM request to a new status."""
        if issue_key not in self._issues:
            from .error_handler import NotFoundError
            raise NotFoundError(f"Request {issue_key} not found")

        for t in self.JSM_TRANSITIONS:
            if t["id"] == transition_id:
                self._issues[issue_key]["fields"]["status"] = {"name": t["name"], "id": t["id"]}
                if issue_key.startswith("DEMOSD"):
                    self._issues[issue_key]["currentStatus"] = {"status": t["name"]}
                break

        if comment:
            self.add_request_comment(issue_key, comment, public)

    # =========================================================================
    # JSM Request Creation
    # =========================================================================

    def create_request(
        self,
        service_desk_id: str,
        request_type_id: str,
        request_field_values: Dict[str, Any],
        raise_on_behalf_of: str = None,
    ) -> Dict[str, Any]:
        """Create a new JSM request."""
        self._next_issue_id += 1
        issue_key = f"DEMOSD-{self._next_issue_id}"
        issue_id = str(20000 + self._next_issue_id)

        request_types = self.REQUEST_TYPES.get(service_desk_id, [])
        type_name = "IT help"
        for rt in request_types:
            if rt["id"] == request_type_id:
                type_name = rt["name"]
                break

        new_issue = {
            "key": issue_key,
            "id": issue_id,
            "self": f"{self.base_url}/rest/api/3/issue/{issue_id}",
            "fields": {
                "summary": request_field_values.get("summary", "New Request"),
                "description": request_field_values.get("description"),
                "issuetype": {"name": type_name, "id": "10100"},
                "status": {"name": "Waiting for support", "id": "10100"},
                "priority": {"name": "Medium", "id": "3"},
                "assignee": None,
                "reporter": self.USERS.get(raise_on_behalf_of, self.USERS["abc123"]),
                "project": {"key": "DEMOSD", "name": "Demo Service Desk", "id": "10001"},
                "created": "2025-01-08T10:00:00.000+0000",
                "updated": "2025-01-08T10:00:00.000+0000",
                "labels": [],
            },
            "requestTypeId": request_type_id,
            "serviceDeskId": service_desk_id,
            "currentStatus": {"status": "Waiting for support", "statusCategory": "new"},
        }

        self._issues[issue_key] = new_issue

        return {
            "issueId": issue_id,
            "issueKey": issue_key,
            "requestTypeId": request_type_id,
            "serviceDeskId": service_desk_id,
            "currentStatus": {"status": "Waiting for support"},
        }

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
        """Generic GET with routing for various endpoints."""
        # Route /mypermissions
        if endpoint == "/rest/api/3/mypermissions":
            return self.get_my_permissions(
                project_key=params.get("projectKey") if params else None,
                permissions=params.get("permissions") if params else None,
            )

        # Route /project/{key}/role
        match = re.match(r"/rest/api/3/project/([^/]+)/role/?$", endpoint)
        if match:
            return self.get_project_roles_for_project(match.group(1))

        # Route /project/{key}/role/{id}
        match = re.match(r"/rest/api/3/project/([^/]+)/role/(\d+)$", endpoint)
        if match:
            return self.get_project_role_actors(match.group(1), int(match.group(2)))

        # Route /groups/picker
        if endpoint == "/rest/api/3/groups/picker":
            return self.find_groups(
                query=params.get("query", "") if params else "",
                max_results=params.get("maxResults", 50) if params else 50,
            )

        # Route /field
        if endpoint == "/rest/api/3/field":
            return self.FIELDS

        # Route /issue/createmeta
        if endpoint == "/rest/api/3/issue/createmeta":
            return self._get_createmeta(params)

        # Route /screens
        if endpoint == "/rest/api/3/screens":
            return self._get_screens()

        if "/rest/api/3/screens/" in endpoint and "/tabs" in endpoint:
            parts = endpoint.split("/")
            screen_id = int(parts[5])
            if endpoint.endswith("/tabs"):
                return self._get_screen_tabs(screen_id)
            if "/fields" in endpoint:
                tab_id = int(parts[7])
                return self._get_screen_tab_fields(screen_id, tab_id)

        if endpoint.startswith("/rest/api/3/screens/") and "/tabs" not in endpoint:
            screen_id = int(endpoint.split("/")[-1])
            return self._get_screen(screen_id)

        # Route issuetypescreenscheme requests
        if endpoint == "/rest/api/3/issuetypescreenscheme/project":
            return self._get_issuetype_screen_scheme(params)

        if "/rest/api/3/issuetypescreenscheme/" in endpoint and "/mapping" in endpoint:
            scheme_id = endpoint.split("/")[-2]
            return self._get_issuetype_screen_scheme_mapping(scheme_id)

        # Route screenscheme requests
        if endpoint.startswith("/rest/api/3/screenscheme/"):
            scheme_id = endpoint.split("/")[-1]
            return self._get_screen_scheme(scheme_id)

        # Route watchers endpoint
        watcher_match = re.match(r"/rest/api/3/issue/([A-Z]+-\d+)/watchers", endpoint)
        if watcher_match:
            issue_key = watcher_match.group(1)
            return self.get_watchers(issue_key)

        # Route changelog endpoint
        changelog_match = re.match(r"/rest/api/3/issue/([A-Z]+-\d+)/changelog", endpoint)
        if changelog_match:
            issue_key = changelog_match.group(1)
            return self.get_changelog(
                issue_key,
                start_at=params.get("startAt", 0) if params else 0,
                max_results=params.get("maxResults", 100) if params else 100,
            )

        # Route dev-status endpoint
        if "/rest/dev-status/latest/issue/detail" in endpoint:
            issue_id = params.get("issueId") if params else None
            return self._get_dev_info(issue_id)

        # Route /issueLinkType
        if endpoint == "/rest/api/3/issueLinkType":
            return {"issueLinkTypes": self.LINK_TYPES}

        return {}

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        operation: str = "create resource",
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generic POST with routing for various endpoints."""
        # Route POST /project/{key}/role/{id} - add user to role
        match = re.match(r"/rest/api/3/project/([^/]+)/role/(\d+)$", endpoint)
        if match and data and "user" in data:
            project_key = match.group(1)
            role_id = int(match.group(2))
            for account_id in data["user"]:
                self.add_user_to_project_role(project_key, role_id, account_id)
            return self.get_project_role_actors(project_key, role_id)

        # Route add watcher endpoint
        watcher_match = re.match(r"/rest/api/3/issue/([A-Z]+-\d+)/watchers", endpoint)
        if watcher_match:
            issue_key = watcher_match.group(1)
            account_id = data.strip('"') if isinstance(data, str) else data
            self.add_watcher(issue_key, account_id)
            return {}

        # Route screen tab field additions
        if "/rest/api/3/screens/" in endpoint and "/tabs/" in endpoint and "/fields" in endpoint:
            return {"id": data.get("fieldId", "unknown"), "name": "Added Field"}

        # Route issue link creation
        if endpoint == "/rest/api/3/issueLink":
            if data:
                link_type = data.get("type", {}).get("name", "")
                inward_key = data.get("inwardIssue", {}).get("key", "")
                outward_key = data.get("outwardIssue", {}).get("key", "")
                if link_type and inward_key and outward_key:
                    self.create_link(link_type, inward_key, outward_key)
            return {}

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
        """Generic DELETE with routing for various endpoints."""
        # Route DELETE /project/{key}/role/{id}?user=xxx
        match = re.match(r"/rest/api/3/project/([^/]+)/role/(\d+)$", endpoint)
        if match and params and "user" in params:
            self.remove_user_from_project_role(
                match.group(1),
                int(match.group(2)),
                params["user"],
            )
            return

        # Route remove watcher endpoint
        watcher_match = re.match(r"/rest/api/3/issue/([A-Z]+-\d+)/watchers", endpoint)
        if watcher_match and params and "accountId" in params:
            issue_key = watcher_match.group(1)
            self.remove_watcher(issue_key, params["accountId"])
            return

        # Route issue link deletion
        link_match = re.match(r"/rest/api/3/issueLink/(\d+)$", endpoint)
        if link_match:
            self.delete_link(link_match.group(1))
            return

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

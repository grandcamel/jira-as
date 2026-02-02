"""Mock JIRA client package.

This package provides mock implementations of the JIRA client for testing
without making actual API calls. The mock client returns consistent,
deterministic data matching the DEMO project structure.

Usage:
    from jira_as.mock import MockJiraClient, is_mock_mode

    # Check if mock mode is enabled
    if is_mock_mode():
        client = MockJiraClient()
    else:
        client = JiraClient(...)

    # Use the client normally
    issue = client.get_issue("DEMO-84")

Environment Variables:
    JIRA_MOCK_MODE: Set to 'true' to enable mock mode globally.

Architecture:
    The mock client is built using a mixin-based architecture:

    - base.py: MockJiraClientBase with core functionality
    - mixins/: Specialized functionality modules
        - agile.py: Boards, sprints, backlog
        - jsm.py: Service desk, requests, SLAs
        - admin.py: Permissions, roles, groups
        - relationships.py: Issue links, dependencies
        - collaborate.py: Watchers, changelog
        - time.py: Worklogs, estimates
        - fields.py: Field metadata, screens
        - dev.py: Development integration
        - search.py: Advanced JQL parsing
    - clients.py: Composed client classes

Available Clients:
    - MockJiraClient: Full-featured client with all capabilities
    - MockAgileClient: Minimal client for agile testing
    - MockJSMClient: Minimal client for JSM testing
    - MockSearchClient: Minimal client for search testing
    - (and more...)
"""

from .base import is_mock_mode

# Also export specialized clients for convenience
from .clients import (
    MockAdminClient,
    MockAgileClient,
    MockAgileSearchClient,
    MockCollaborateClient,
    MockDevClient,
    MockFieldsClient,
    MockFullDevClient,
    MockJiraClient,
    MockJSMClient,
    MockJSMCollaborateClient,
    MockRelationshipsClient,
    MockSearchClient,
    MockTimeClient,
)

__all__ = [
    "MockAdminClient",
    # Specialized clients
    "MockAgileClient",
    # Combination clients
    "MockAgileSearchClient",
    "MockCollaborateClient",
    "MockDevClient",
    "MockFieldsClient",
    "MockFullDevClient",
    "MockJSMClient",
    "MockJSMCollaborateClient",
    # Primary exports
    "MockJiraClient",
    "MockRelationshipsClient",
    "MockSearchClient",
    "MockTimeClient",
    "is_mock_mode",
]

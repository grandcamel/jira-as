"""Composed mock client classes.

This module defines mock client classes composed from the base class and mixins.
Each class provides a different set of functionality for specific testing needs.
"""

from .base import MockJiraClientBase
from .mixins import (
    AdminMixin,
    AgileMixin,
    CollaborateMixin,
    DevMixin,
    FieldsMixin,
    JSMMixin,
    RelationshipsMixin,
    SearchMixin,
    TimeTrackingMixin,
)


class MockJiraClient(
    MockJiraClientBase,
    AgileMixin,
    JSMMixin,
    AdminMixin,
    RelationshipsMixin,
    CollaborateMixin,
    TimeTrackingMixin,
    FieldsMixin,
    DevMixin,
    SearchMixin,
):
    """Full-featured mock client with all capabilities.

    This is the default mock client that provides mock implementations
    for all JIRA functionality including:

    - Core issue operations (create, read, update, delete)
    - Transitions and status changes
    - Comments and worklogs
    - User and project management
    - Agile boards, sprints, and backlog
    - JSM service desk, requests, and SLAs
    - Administration (roles, groups, permissions)
    - Issue relationships and links
    - Collaboration (watchers, changelog, attachments)
    - Time tracking and estimates
    - Field metadata and screens
    - Development integration (branches, commits, PRs)
    - Advanced JQL search and filters
    """

    pass


# =============================================================================
# Skill-Specific Minimal Clients
# =============================================================================


class MockAgileClient(MockJiraClientBase, AgileMixin):
    """Minimal mock for agile skill testing.

    Provides only core issue operations plus agile-specific functionality:
    - Boards
    - Sprints
    - Backlog management
    - Epic operations
    """

    pass


class MockJSMClient(MockJiraClientBase, JSMMixin):
    """Minimal mock for JSM skill testing.

    Provides only core issue operations plus JSM-specific functionality:
    - Service desks
    - Request types
    - Queues
    - SLAs
    - Customer management
    """

    pass


class MockAdminClient(MockJiraClientBase, AdminMixin):
    """Minimal mock for admin skill testing.

    Provides only core issue operations plus administration functionality:
    - Roles
    - Groups
    - Permissions
    - Projects
    - Issue types
    - Workflows
    """

    pass


class MockSearchClient(MockJiraClientBase, SearchMixin):
    """Minimal mock for search skill testing.

    Provides only core issue operations plus advanced search functionality:
    - Advanced JQL parsing
    - Saved filters
    - Bulk search operations
    - Export capabilities
    """

    pass


class MockCollaborateClient(MockJiraClientBase, CollaborateMixin):
    """Minimal mock for collaboration skill testing.

    Provides only core issue operations plus collaboration functionality:
    - Watchers
    - Changelog
    - Attachments
    - Notifications
    - Votes
    """

    pass


class MockTimeClient(MockJiraClientBase, TimeTrackingMixin):
    """Minimal mock for time tracking skill testing.

    Provides only core issue operations plus time tracking functionality:
    - Worklogs
    - Time estimates
    - Time reports
    """

    pass


class MockRelationshipsClient(MockJiraClientBase, RelationshipsMixin):
    """Minimal mock for relationships skill testing.

    Provides only core issue operations plus relationship functionality:
    - Issue links
    - Remote links
    - Clone operations
    - Dependency analysis
    """

    pass


class MockDevClient(MockJiraClientBase, DevMixin):
    """Minimal mock for development skill testing.

    Provides only core issue operations plus development functionality:
    - Development info
    - Branch names
    - Commit messages
    - PR descriptions
    """

    pass


class MockFieldsClient(MockJiraClientBase, FieldsMixin):
    """Minimal mock for fields skill testing.

    Provides only core issue operations plus field metadata functionality:
    - System fields
    - Custom fields
    - Screens
    - Field configurations
    """

    pass


# =============================================================================
# Combination Clients
# =============================================================================


class MockAgileSearchClient(MockJiraClientBase, AgileMixin, SearchMixin):
    """Mock client for agile + search testing.

    Combines agile board/sprint operations with advanced search capabilities.
    """

    pass


class MockJSMCollaborateClient(MockJiraClientBase, JSMMixin, CollaborateMixin):
    """Mock client for JSM + collaboration testing.

    Combines service desk operations with collaboration features like
    watchers and notifications.
    """

    pass


class MockFullDevClient(MockJiraClientBase, DevMixin, RelationshipsMixin, SearchMixin):
    """Mock client for full development workflow testing.

    Combines development integration with relationships (for linking)
    and search (for finding issues).
    """

    pass

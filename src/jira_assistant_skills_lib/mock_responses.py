"""Backwards compatibility - import from mock package.

This module is maintained for backwards compatibility. All functionality
has been refactored into the mock/ package with a mixin-based architecture.

For new code, prefer importing directly from the mock package:
    from jira_assistant_skills_lib.mock import MockJiraClient, is_mock_mode

Architecture:
    The mock client is now built using composable mixins:

    mock/
    ├── __init__.py      # Package exports
    ├── base.py          # MockJiraClientBase - core functionality
    ├── clients.py       # Composed client classes
    └── mixins/
        ├── agile.py     # AgileMixin - boards, sprints, backlog
        ├── jsm.py       # JSMMixin - service desk, requests, SLAs
        ├── admin.py     # AdminMixin - permissions, roles, groups
        ├── relationships.py  # RelationshipsMixin - issue links
        ├── collaborate.py    # CollaborateMixin - watchers, changelog
        ├── time.py      # TimeTrackingMixin - worklogs, estimates
        ├── fields.py    # FieldsMixin - field metadata, screens
        ├── dev.py       # DevMixin - development integration
        └── search.py    # SearchMixin - advanced JQL parsing
"""

from .mock import MockJiraClient, is_mock_mode

__all__ = ["MockJiraClient", "is_mock_mode"]

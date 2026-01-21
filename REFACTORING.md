# JiraClient Refactoring Plan

This document outlines the plan to refactor the monolithic `jira_client.py` (6,228 lines, 200+ methods) into feature-focused modules while maintaining backwards compatibility.

## Current State

The `JiraClient` class contains all JIRA API operations in a single file:
- Core HTTP operations
- Issue CRUD
- Agile (sprints, boards, backlogs)
- Issue links and relationships
- Comments and attachments
- Time tracking and worklogs
- JQL, filters, and search
- Versions and components
- JSM (Service Management)
- User and group management
- Project administration
- Workflows, screens, and issue types
- Permission schemes

## Proposed Architecture

### Mixin-Based Approach

Use Python mixins to split functionality while maintaining a single `JiraClient` class:

```
src/jira_as/
├── __init__.py              # Public exports
├── jira_client.py           # Slim JiraClient combining all mixins
├── _base.py                 # BaseJiraClient with HTTP methods
├── _mixins/
│   ├── __init__.py
│   ├── issues.py            # Issue CRUD operations
│   ├── agile.py             # Sprint, board, backlog operations
│   ├── links.py             # Issue linking and relationships
│   ├── comments.py          # Comments and visibility
│   ├── attachments.py       # File uploads/downloads
│   ├── worklogs.py          # Time tracking and worklogs
│   ├── jql.py               # JQL parsing, autocomplete, filters
│   ├── versions.py          # Version management
│   ├── components.py        # Component management
│   ├── jsm.py               # Service Management (large module)
│   ├── users.py             # User operations
│   ├── groups.py            # Group management
│   ├── projects.py          # Project administration
│   ├── workflows.py         # Workflow schemes
│   ├── screens.py           # Screen configuration
│   ├── issue_types.py       # Issue type schemes
│   └── permissions.py       # Permission schemes
```

### Mixin Example

```python
# _mixins/issues.py
from typing import Any, Dict, List, Optional

class IssuesMixin:
    """Mixin providing issue CRUD operations."""

    def search_issues(
        self, jql: str, fields: Optional[List[str]] = None, max_results: int = 50
    ) -> Dict[str, Any]:
        """Search for issues using JQL."""
        # Implementation using self.get(), self.post() from BaseJiraClient
        ...

    def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        ...

    def create_issue(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> None:
        ...

    def delete_issue(self, issue_key: str, delete_subtasks: bool = True) -> None:
        ...

    def clone_issue(self, issue_key: str, **kwargs) -> Dict[str, Any]:
        ...
```

### New JiraClient

```python
# jira_client.py
from ._base import BaseJiraClient
from ._mixins import (
    IssuesMixin,
    AgileMixin,
    LinksMixin,
    CommentsMixin,
    AttachmentsMixin,
    WorklogsMixin,
    JqlMixin,
    VersionsMixin,
    ComponentsMixin,
    JsmMixin,
    UsersMixin,
    GroupsMixin,
    ProjectsMixin,
    WorkflowsMixin,
    ScreensMixin,
    IssueTypesMixin,
    PermissionsMixin,
)

class JiraClient(
    IssuesMixin,
    AgileMixin,
    LinksMixin,
    CommentsMixin,
    AttachmentsMixin,
    WorklogsMixin,
    JqlMixin,
    VersionsMixin,
    ComponentsMixin,
    JsmMixin,
    UsersMixin,
    GroupsMixin,
    ProjectsMixin,
    WorkflowsMixin,
    ScreensMixin,
    IssueTypesMixin,
    PermissionsMixin,
    BaseJiraClient,
):
    """
    Complete JIRA REST API client.

    Combines all feature-specific mixins to provide a unified interface.
    All existing code using JiraClient will continue to work unchanged.
    """
    pass
```

## Module Size Estimates

| Module | Methods | Lines (est) |
|--------|---------|-------------|
| _base.py | 8 | 250 |
| issues.py | 15 | 400 |
| agile.py | 25 | 700 |
| links.py | 8 | 200 |
| comments.py | 8 | 200 |
| attachments.py | 5 | 150 |
| worklogs.py | 8 | 300 |
| jql.py | 20 | 500 |
| versions.py | 10 | 300 |
| components.py | 8 | 200 |
| jsm.py | 55 | 1500 |
| users.py | 12 | 350 |
| groups.py | 10 | 300 |
| projects.py | 20 | 500 |
| workflows.py | 12 | 350 |
| screens.py | 15 | 400 |
| issue_types.py | 18 | 450 |
| permissions.py | 15 | 400 |

## Migration Steps

### Phase 1: Create Base and First Mixin (Low Risk)
1. Create `_base.py` with HTTP methods (`get`, `post`, `put`, `delete`, `upload_file`, `download_file`)
2. Create `_mixins/issues.py` with issue CRUD
3. Verify all existing tests pass
4. No changes to public API

### Phase 2: Extract High-Value Mixins
1. Extract `agile.py` (sprint/board operations)
2. Extract `jsm.py` (largest module)
3. Extract `jql.py` (filter operations)
4. Each extraction must pass all tests

### Phase 3: Complete Extraction
1. Extract remaining mixins
2. Reduce `jira_client.py` to just the class composition
3. Final test verification

### Phase 4: Optional - Standalone Clients
For users who only need specific functionality:

```python
# Lightweight client for issue operations only
from jira_as import BaseJiraClient
from jira_as._mixins import IssuesMixin

class IssueClient(IssuesMixin, BaseJiraClient):
    """Lightweight client for issue operations only."""
    pass
```

## Backwards Compatibility

- All public exports from `__init__.py` remain unchanged
- `JiraClient` class keeps all existing methods
- No import path changes for consumers
- Type hints preserved
- Docstrings preserved

## Testing Strategy

1. Run full test suite after each mixin extraction
2. Verify no regression in existing functionality
3. Add type checking with mypy
4. Verify IDE autocomplete still works

## Timeline Recommendation

This refactoring should be done incrementally over multiple PRs:
1. PR 1: Base class + issues mixin (foundation)
2. PR 2: Agile mixin (frequently used)
3. PR 3: JSM mixin (largest, isolated)
4. PR 4-8: Remaining mixins in logical groups

## Benefits

1. **Maintainability**: Each module is focused and ~200-500 lines
2. **Testability**: Mixins can be unit tested in isolation
3. **Documentation**: Each mixin documents one API area
4. **Code Navigation**: IDEs can jump to relevant code faster
5. **Selective Imports**: Future option for lightweight clients
6. **Onboarding**: New contributors understand structure faster

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Method name conflicts | Unique naming convention per mixin |
| Type checking complexity | Protocols or TYPE_CHECKING imports |
| IDE autocomplete issues | Explicit re-exports in __init__.py |
| Import circular deps | Base class has no dependencies on mixins |

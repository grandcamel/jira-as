# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the `jira-assistant-skills-lib` PyPI package - a shared Python library providing HTTP client, configuration management, error handling, and utilities for JIRA REST API automation. It is a dependency of the [JIRA Assistant Skills](https://github.com/grandcamel/Jira-Assistant-Skills) project.

**Usage context**: This library powers the `jira` CLI and skill scripts. When Claude Code invokes a JIRA skill, it loads the SKILL.md context, then uses Bash to execute `jira` CLI commands which call this library.

## Common Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_imports.py

# Run a specific test class or method
pytest tests/test_imports.py::TestValidators
pytest tests/test_imports.py::TestValidators::test_validate_issue_key_valid

# Format code
black src tests
isort src tests

# Type checking
mypy src
```

## Architecture

### Module Structure

The package is organized as a flat module under `src/jira_assistant_skills_lib/`:

- **jira_client.py**: HTTP client with retry logic (3 attempts, exponential backoff on 429/5xx), session management, and unified error handling for JIRA REST API v3
- **config_manager.py**: Configuration from environment variables. Priority: env vars > keychain > settings.local.json > settings.json > defaults
- **error_handler.py**: Exception hierarchy mapping HTTP status codes to domain exceptions (400→ValidationError, 401→AuthenticationError, 403→PermissionError, 404→NotFoundError, 429→RateLimitError, 5xx→ServerError)
- **validators.py**: Input validation for JIRA-specific formats (issue keys: `^[A-Z][A-Z0-9]*-[0-9]+$`, project keys, JQL, URLs, emails)
- **formatters.py**: Output formatting for tables (via tabulate), JSON, and CSV export
- **adf_helper.py**: Atlassian Document Format conversion (markdown/text ↔ ADF)
- **time_utils.py**: JIRA time format parsing ('2h 30m' → seconds) and formatting
- **cache.py**: SQLite-based caching with TTL support
- **credential_manager.py**: Secure credential storage via system keychain (optional) or JSON fallback
- **automation_client.py**: Client for JIRA Automation API
- **request_batcher.py**: Concurrent API request batching
- **batch_processor.py**: Large-scale operations with checkpoint support
- **project_context.py**: Project metadata and workflow defaults
- **transition_helpers.py**: Fuzzy workflow transition matching
- **user_helpers.py**: User resolution to account IDs
- **jsm_utils.py**: Jira Service Management SLA utilities

### Dependencies

This library inherits from `assistant-skills-lib` (base library) and extends it with JIRA-specific functionality. Key dependencies:
- `requests>=2.28.0`: HTTP client
- `tabulate>=0.9.0`: Table formatting
- `assistant-skills-lib>=1.0.0`: Base validation, error handling, config management

### Configuration

Environment variables (highest priority):
- `JIRA_API_TOKEN`: API token from https://id.atlassian.com/manage-profile/security/api-tokens
- `JIRA_EMAIL`: Email associated with JIRA account
- `JIRA_SITE_URL`: JIRA instance URL (e.g., https://company.atlassian.net)
- `JIRA_MOCK_MODE`: Set to `true` to use mock client instead of real API

Agile field overrides (optional):
- `JIRA_EPIC_LINK_FIELD`, `JIRA_STORY_POINTS_FIELD`, `JIRA_SPRINT_FIELD`

### Error Handling Pattern

All modules use a consistent 4-layer approach:
1. Pre-validation via validators.py before API calls
2. API errors via handle_jira_error() which maps status codes to exceptions
3. Retry logic in JiraClient for [429, 500, 502, 503, 504]
4. User messages with troubleshooting hints in exception messages

### Export Pattern

All public APIs are exported from `__init__.py`. Consumer scripts should use:
```python
from jira_assistant_skills_lib import get_jira_client, ValidationError, validate_issue_key
```

### JiraClient Usage Pattern

**Always use context manager** for JiraClient to ensure proper resource cleanup:

```python
# Correct - context manager handles cleanup automatically
with get_jira_client() as client:
    issue = client.get_issue("PROJ-123")
    return issue

# Wrong - manual try/finally is deprecated
client = get_jira_client()
try:
    issue = client.get_issue("PROJ-123")
finally:
    client.close()  # Don't do this
```

Both `JiraClient` and `MockJiraClient` implement `__enter__` and `__exit__` methods.

## Adding New Functionality

When adding new modules:
1. Create the module in `src/jira_assistant_skills_lib/`
2. Export public APIs from `__init__.py` in both the imports section and `__all__`
3. Add corresponding tests in `tests/`
4. Use existing error classes from error_handler.py
5. Follow the validation pattern: validate inputs before API calls

## Mock Client

The library includes a mock JIRA client for testing without real API calls.

### Architecture

```
src/jira_assistant_skills_lib/mock/
├── __init__.py      # Exports MockJiraClient, is_mock_mode
├── base.py          # MockJiraClientBase with core operations + is_mock_mode()
├── clients.py       # Composed clients (MockJiraClient = Base + all mixins)
└── mixins/          # Specialized functionality
    ├── agile.py     # Boards, sprints, backlog
    ├── search.py    # Advanced JQL parsing
    ├── jsm.py       # Service desk, SLAs
    └── ...          # admin, collaborate, dev, fields, relationships, time
```

### Enabling Mock Mode

Set `JIRA_MOCK_MODE=true` environment variable. The `get_jira_client()` function checks this:

```python
def get_jira_client():
    from .mock import is_mock_mode, MockJiraClient
    if is_mock_mode():
        return MockJiraClient()  # Returns mock instead of real client
    # ... normal client creation from JIRA_* env vars
```

### Seed Data

Mock client provides deterministic test data:
- **DEMO project**: DEMO-84 (Epic), DEMO-85 (Story), DEMO-86 (Bug), DEMO-87 (Task), DEMO-91 (Bug)
- **DEMOSD project**: DEMOSD-1 through DEMOSD-5 (Service desk requests)
- **Users**: Jason Krueger (abc123), Jane Manager (def456)

## Testing Patterns

### Mock Client Fixtures

When mocking `get_jira_client()` in tests, always add context manager support:

```python
@pytest.fixture
def mock_client():
    """Create mock JIRA client with context manager support."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=None)
    return client
```

To verify cleanup, assert on `__exit__` instead of `close`:
```python
# Correct
mock_client.__exit__.assert_called_once()

# Wrong - close() is no longer called directly
mock_client.close.assert_called_once()
```

## Gotchas

- **Context manager required**: Always use `with get_jira_client() as client:` pattern. Manual `try/finally` with `close()` is deprecated.
- **Test mock context manager**: Mock fixtures must include `__enter__` and `__exit__` methods or tests will fail with context manager usage.
- **Exception hierarchy**: Custom exceptions must inherit from base classes in `error_handler.py` (e.g., `JiraError`, `NotFoundError`, `ValidationError`). Never inherit directly from `Exception`.
- **Constants in constants.py**: Field IDs like `EPIC_LINK_FIELD`, `STORY_POINTS_FIELD` are defined in `constants.py`. Import them, don't duplicate.
- **Mock API parity**: Mock methods must match `JiraClient` signatures exactly. If real client adds parameters (e.g., `next_page_token`), mock must accept them too or skills will fail with `TypeError: got unexpected keyword argument`.
- **Version sync**: `pyproject.toml` version and `__init__.py` `__version__` must match. Use `./scripts/sync-version.sh` if available.
- **Import from package**: Always `from jira_assistant_skills_lib import ...`, never import internal modules directly.
- **Mixin method conflicts**: When adding mock methods, check if base class or other mixins define the same method. Use `super()` calls if extending.
- **Test with real signatures**: When updating mock, test against actual skill scripts to catch signature mismatches early.

## Version Management

Version is defined in two places that must stay in sync:
- `pyproject.toml`: `version = "0.2.3"` (source of truth for publishing)
- `src/jira_assistant_skills_lib/__init__.py`: `__version__ = "0.2.3"` (runtime access)

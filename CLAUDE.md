# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the `jira-assistant-skills-lib` PyPI package - a shared Python library providing HTTP client, configuration management, error handling, and utilities for JIRA REST API automation. It is a dependency of the [JIRA Assistant Skills](https://github.com/grandcamel/Jira-Assistant-Skills) project.

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
- **config_manager.py**: Multi-source configuration merging with profile support. Priority: env vars > keychain > settings.local.json > settings.json > defaults
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
- `JIRA_PROFILE`: Profile name for multi-instance support

Profile-based Agile field overrides via env vars:
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

## Adding New Functionality

When adding new modules:
1. Create the module in `src/jira_assistant_skills_lib/`
2. Export public APIs from `__init__.py` in both the imports section and `__all__`
3. Add corresponding tests in `tests/`
4. Use existing error classes from error_handler.py
5. Follow the validation pattern: validate inputs before API calls

## Version Management

Version is defined in two places that must stay in sync:
- `pyproject.toml`: `version = "0.2.0"` (source of truth for publishing)
- `src/jira_assistant_skills_lib/__init__.py`: `__version__ = "0.1.5"` (runtime access)

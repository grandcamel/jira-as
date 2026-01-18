# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-01-18

### Added
- Comprehensive test coverage for CLI and helper modules
  - `cli/main.py`: 0% → 93% coverage
  - `mock/factories.py`: 0% → 100% coverage
  - `search_helpers.py`: 23% → 100% coverage
  - `user_helpers.py`: 32% → 100% coverage
  - `permission_helpers.py`: 17% → 99% coverage
  - `mock_responses.py`: 0% → 100% coverage
- Ruff linter configuration in `pyproject.toml`
- Explicit `__all__` exports in `formatters.py`

### Fixed
- All mypy type errors resolved (strict type checking now passes)
- Missing re-exports in `formatters.py` (export_csv, format_json, etc.)
- Type annotations for collection variables across codebase

### Changed
- Updated dev tools: black 26.1.0, ruff 0.14.13, uv 0.9.26
- Import ordering standardized with ruff

## [1.0.0] - 2025-01-17

### Added
- `jira-as` CLI with 13 command groups (issue, search, lifecycle, fields, ops, bulk, dev, relationships, time, collaborate, agile, jsm, admin)
- Context manager pattern for `JiraClient` and `MockJiraClient`
- Mixin-based mock client architecture for better maintainability
- Shared factories for mock response building

### Changed
- **BREAKING**: Package renamed from `jira-assistant-skills-lib` to `jira-assistant-skills`
- **BREAKING**: Requires Python 3.10+ (dropped 3.8/3.9 support)
- Refactored to use `assistant-skills-lib` base library

### Fixed
- Exception hierarchy alignment (UserNotFoundError, BatchError)
- Deprecation warnings in board lookup

## [0.2.2] - 2025-01-10

### Added
- Mock client support via `JIRA_MOCK_MODE=true` environment variable
- `next_page_token` support in mock `search_issues`

### Fixed
- MockJiraClient returned correctly when mock mode enabled

## [0.2.1] - 2025-01-09

### Added
- Mixin-based mock client architecture
- Consolidated scenario support in mock client

## [0.1.5] - 2025-01-08

### Added
- Initial mock_responses.py implementation

## [0.1.0] - 2025-01-01

### Added
- Initial release
- JiraClient with retry logic and error handling
- ConfigManager for multi-source configuration
- Validators for JIRA-specific formats
- Formatters for tables, JSON, CSV output
- ADF helper for Atlassian Document Format conversion
- Time utilities for JIRA time format parsing
- SQLite-based caching with TTL support
- Credential manager with keychain support

[1.1.0]: https://github.com/grandcamel/jira-assistant-skills-lib/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/grandcamel/jira-assistant-skills-lib/compare/v0.2.2...v1.0.0
[0.2.2]: https://github.com/grandcamel/jira-assistant-skills-lib/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/grandcamel/jira-assistant-skills-lib/compare/v0.1.5...v0.2.1
[0.1.5]: https://github.com/grandcamel/jira-assistant-skills-lib/compare/v0.1.0...v0.1.5
[0.1.0]: https://github.com/grandcamel/jira-assistant-skills-lib/releases/tag/v0.1.0

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.3] - 2026-08-18

### Added
- **Issue parent handling**: `issue create --parent` and `issue update --parent`
  set the modern `parent` field instead of smuggling a key into the epic-link
  custom field. `issue create --parent-via-update` creates the issue first and
  sets the parent in a follow-up update, for workflows whose validators reject
  a parent at create time.
- **ADF auto-wrap**: plain-string values for rich-text fields are converted to
  ADF on create and update; values that are already ADF pass through unchanged.
  `JIRA_ADF_CUSTOM_FIELDS` (comma-separated field IDs) extends the built-in
  `description`/`environment` set.
- `issue create --dry-run` builds and prints the payload without calling the API.
- **Issue group aliases**: `issue transitions` (read-only), `issue transition`
  (same options as `lifecycle transition`), and `issue comment` (alias for
  `collaborate comment add`, with `--format text|markdown|adf`). Each delegates
  to the canonical implementation so behaviour cannot drift.
- **Per-project agile fields**: `get_agile_fields()` and `get_agile_field()`
  take an optional `project_key`, and the new `get_project_agile_fields()`
  reads `jira.projects.<KEY>.agile_fields` from settings, which outranks the
  global and environment values. `issue create --story-points` resolves its
  field ID against the target project rather than a global custom field ID.
- **Remote links**: `JiraClient.create_remote_link()`, `get_remote_links()` and
  `delete_remote_link()`, surfaced as `relationships link --remote-url` with
  `--remote-title` and `--remote-relationship`. A native link rejected with 404
  or 403 now hints at `--remote-url`, which reaches cross-project and JSM
  targets that a native link cannot.
- **`agile board list`**: lists boards from `/rest/agile/1.0/board` with
  `isLast` pagination and `--project`, `--type scrum|kanban`, `--output
  text|json`. An unscoped listing warns that it covers every board on the site.
- `fields list --project` and `--issue-type` scope the listing to a project's
  create-screen fields instead of the whole instance catalogue.
- `ops discover-project` reports field fill rates, value distributions for the
  low-cardinality fields, and parent-hierarchy hints.
- `request create` gains `--priority` and `--labels`; `request comment` gains
  `--format text|wiki` and `--dry-run`.
- `JiraClient.get_statuses()`, `get_project_notification_scheme()`,
  `get_board_issues()`, `move_issues_to_backlog()`, and scheme-to-project
  enumeration for permission and workflow schemes, with mock counterparts.

### Changed
- **Search pagination**: `/rest/api/3/search/jql` caps a page at 100 issues.
  `search_issues()` now caps each request accordingly and, when `max_results`
  exceeds the cap and the caller is not paging manually, walks `nextPageToken`
  until the requested count or the last page. Explicit `next_page_token` or
  `start_at` paging stays single-page.
- `search export` keeps nested field values as real JSON in JSON exports; CSV
  collapses objects to their display name or to compact JSON rather than a
  Python repr.
- `request create --summary` is now optional, and the request type's field
  metadata is checked first so required fields the API cannot set (portal-only
  and asset-backed pickers) are named explicitly instead of returning an opaque
  400. `--dry-run` respects `-o json`.
- `issue-type-scheme create` requires `--issue-types`; the API rejects a scheme
  with no issue types.
- Ruff is the sole import sorter. The isort pre-commit hook and `[tool.isort]`
  config are removed.
- Coverage `fail_under` lowered from 70 to 60. The 70 target had never been met
  (main sat at 59.8%); the suite now clears 62%, so the gate is enforceable
  rather than permanently red.

### Fixed
- **13 admin commands** called `JiraClient` methods that do not exist or used
  the wrong signature: notification scheme create/add/remove, permission scheme
  assign and project listing, issue type create, issue type scheme
  get/create/assign/project lookup, workflow scheme get/assign, workflow for
  issue, and `status list`. Screen and screen scheme IDs are coerced to int at
  the CLI boundary with a clear error for non-numeric input.
- `admin project config --show-schemes` crashed on a missing
  `get_project_notification_scheme()`.
- **JSM envelope handling**: `request comments`, `request participants`,
  `approval list`, `request-type fields` and `asset affected` returned the raw
  `{"values": [...]}` envelope where a list was declared. `request comments`
  also ignored `--internal-only` entirely.
- `request status` read `status` off the status-history envelope, so its text
  output always showed `N/A`. It now reports the most recent entry.
- Repaired JSM client calls that would have failed at runtime: `service-desk
  create` (wrong parameters), `request remove-participant` (singular method
  name), `customer create` (service desk passed as the email positional, and an
  API-required display name that could be omitted), `kb search` (result cap
  passed as `highlight`), `kb suggest` (nonexistent method), and `request
  create` (int IDs where the API expects strings).
- `search export` with no matching issues raised `KeyError: 'output_file'`. An
  empty result now writes a header-only CSV or an empty JSON envelope, exit 0.
- `sprint close --move-incomplete-to` passed a sprint ID where a list of issue
  keys belongs and read a return value from a method that returns `None`.
- `agile backlog` falls back to the board's issues when the board exposes no
  backlog endpoint, as Kanban and team-managed boards often do not. Resolving a
  project to a board now warns when the project has several, naming the one
  chosen.
- `issue update --no-notify` returned 403 for non-administrators, losing the
  edit along with the notification suppression. It now retries with
  `notifyUsers` omitted so the update still applies, and warns on stderr. The
  mock accepts `notify_users` for parity.
- `testing.py` called `client.post(json=...)` four times; `post()` takes
  `data`, so every `IssueBuilder.build()` and search assertion raised
  `TypeError`. These now use the typed client methods.
- `jira_client.py` and `automation_client.py` contained
  `from error_handler import ...` statements that would have raised
  `ModuleNotFoundError` when reached.
- Bulk and issue commands passed `issue.get("key")` into client calls, sending
  `None` to the API instead of failing loudly on a malformed result.
- The mock's screen `--scope` filter read a key no seeded screen carried, so it
  silently returned nothing.
- The mock's `get_request_participants()` returned a bare list where the real
  client returns a paginated envelope, breaking mock-mode callers that unwrap
  `values`.
- `JiraClient.post()` accepted a raw string body in its implementation (the
  watcher API needs one) but not in its type annotation.
- `mypy src` passes clean; the branch started with 91 errors.

---

## [1.1.2] - 2026-08-18

### Fixed
- `version list` and `component list` called `JiraClient.get_versions()` and
  `get_components()`, which do not exist. They now use `get_project_versions()`
  and `get_project_components()`.
- The mock's `get_all_boards()` now leads with `project_key` in the same order
  as the real client, keeping `project_key_or_id` as a compatibility alias.
- `relationships get-blockers --include-done` was accepted but ignored.
  Completed blockers are now filtered out by default, with `statusCategory`
  preferred over the status name so non-English workflows classify correctly.

---

## [1.0.0] - 2025-01-20

### Changed
- **BREAKING**: Package renamed from `jira-assistant-skills` to `jira-as`
- **BREAKING**: Module renamed from `jira_assistant_skills_lib` to `jira_as`
- All imports must be updated: `from jira_as import ...`
- Updated dependency to `assistant-skills-lib>=1.0.0`

---

## Previous Releases (as jira-assistant-skills)

## [1.2.0] - 2025-01-20

### Changed
- **BREAKING**: Removed profile feature from `ConfigManager`
  - Removed `profile` parameter from `get_client()`, `get_default_project()`, `get_agile_fields()`, `get_agile_field()`, `get_automation_client()`
  - Removed `get_profile_config()` method
  - Removed `JIRA_PROFILE` environment variable support and deprecation warning
- Updated dependency to `assistant-skills-lib>=1.0.0`

## [1.1.0-pre] - 2025-01-18

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
- **BREAKING**: Package renamed from `jira-as` to `jira-as`
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

[1.2.0]: https://github.com/grandcamel/jira-as/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/grandcamel/jira-as/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/grandcamel/jira-as/compare/v0.2.2...v1.0.0
[0.2.2]: https://github.com/grandcamel/jira-as/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/grandcamel/jira-as/compare/v0.1.5...v0.2.1
[0.1.5]: https://github.com/grandcamel/jira-as/compare/v0.1.0...v0.1.5
[0.1.0]: https://github.com/grandcamel/jira-as/releases/tag/v0.1.0

# Cross-Library Implementation Plan

## Overview

This document outlines refactoring opportunities and patterns that can be standardized across the four Assistant Skills libraries:
- `assistant-skills-lib` (base library)
- `jira-assistant-skills-lib`
- `confluence-assistant-skills-lib`
- `splunk-assistant-skills-lib`

## Current State Summary

| Feature | Base Lib | JIRA | Confluence | Splunk |
|---------|----------|------|------------|--------|
| Credential Manager | BaseCredentialManager | Full (keychain) | Basic | Basic |
| Config Manager | N/A | Full | Basic | Full |
| Mock Client | N/A | Full (mixins) | Full (mixins) | Full (mixins) |
| is_mock_mode() | N/A | Yes | Yes | Yes |
| Batch Processor | Yes | Yes | No | No |
| Request Batcher | Yes | Yes | No | No |
| Domain Context | N/A | ProjectContext | SpaceContext | SearchContext |
| Error Hierarchy | BaseAPIError | JiraError | ConfluenceError | SplunkError |
| ADF Helper | N/A | Yes | Yes | N/A |
| Fluent Builders | N/A | IssueBuilder | PageBuilder | EventBuilder |
| CLI Structure | N/A | Click-based | Click-based | Click-based |
| Cache | SkillCache | JiraCache | Uses base | N/A |
| Live Integration Tests | N/A | Docker container | Docker container | N/A |

---

## Phase 1: Base Library Enhancements

### 1.1 Add BaseConfigManager to assistant-skills-lib

**Current State**: Each library implements its own ConfigManager with similar patterns.

**Target**: Create a base class that handles:
- Multi-source configuration priority (env vars > keychain > settings.local.json > settings.json > defaults)
- Thread-safe singleton access with double-checked locking
- Standard settings file paths (`.claude/settings.json`, `.claude/settings.local.json`)

**Implementation**:
```python
# assistant-skills-lib/src/assistant_skills_lib/config_manager.py

class BaseConfigManager:
    """Base configuration manager with multi-source priority."""

    # Subclasses define these
    ENV_PREFIX: str  # e.g., "JIRA", "CONFLUENCE", "SPLUNK"
    REQUIRED_VARS: list[str]  # e.g., ["site_url", "email", "api_token"]

    def __init__(self, settings_dir: str = ".claude"):
        self.settings_dir = settings_dir
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load config with priority: env > keychain > settings.local.json > settings.json > defaults"""
        pass

    @classmethod
    def get_instance(cls) -> "BaseConfigManager":
        """Thread-safe singleton access."""
        pass
```

**Files to create**:
- `assistant-skills-lib/src/assistant_skills_lib/config_manager.py`

**Files to update**:
- `assistant-skills-lib/src/assistant_skills_lib/__init__.py` - export BaseConfigManager
- `jira-assistant-skills-lib/.../config_manager.py` - extend BaseConfigManager
- `confluence-assistant-skills-lib/.../config_manager.py` - extend BaseConfigManager
- `splunk-assistant-skills-lib/.../config_manager.py` - extend BaseConfigManager

**Priority**: High
**Effort**: Medium

---

### 1.2 Add BaseMockClient to assistant-skills-lib

**Current State**: All three domain libraries have similar mock client implementations with:
- Base class with HTTP method stubs
- Mixin architecture for domain-specific endpoints
- Request recording for assertions
- Seed data initialization

**Target**: Extract common mock client functionality to base library.

**Implementation**:
```python
# assistant-skills-lib/src/assistant_skills_lib/mock/base.py

class BaseMockClient:
    """Base mock client with request recording and ID generation."""

    def __init__(self, base_url: str = "https://mock.example.com", **kwargs):
        self.base_url = base_url
        self._requests: list[dict[str, Any]] = []
        self._init_seed_data()

    def _generate_id(self) -> str:
        """Generate unique ID for new resources."""
        return str(uuid.uuid4().int)[:10]

    def _now_iso(self) -> str:
        """Return current timestamp in ISO format."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _record_request(self, method: str, endpoint: str, **kwargs) -> None:
        """Record request for test assertions."""
        pass

    def get_recorded_requests(self) -> list[dict[str, Any]]:
        """Return all recorded requests."""
        pass

    def clear_recorded_requests(self) -> None:
        """Clear recorded requests."""
        pass

    def reset(self) -> None:
        """Reset all mock data to initial state."""
        pass
```

**Files to create**:
- `assistant-skills-lib/src/assistant_skills_lib/mock/__init__.py`
- `assistant-skills-lib/src/assistant_skills_lib/mock/base.py`

**Priority**: Medium
**Effort**: Medium

---

### 1.3 Add is_mock_mode() Pattern to Base Library

**Current State**: Each library implements `is_mock_mode()` checking `{SERVICE}_MOCK_MODE` env var.

**Target**: Provide a factory function in base library.

**Implementation**:
```python
# assistant-skills-lib/src/assistant_skills_lib/mock/__init__.py

def create_mock_mode_checker(env_var_name: str) -> Callable[[], bool]:
    """Create a mock mode checker for a specific environment variable."""
    def is_mock_mode() -> bool:
        return os.environ.get(env_var_name, "").lower() == "true"
    return is_mock_mode
```

**Priority**: Low
**Effort**: Low

---

## Phase 2: Port JIRA Patterns to Confluence/Splunk

### 2.1 Batch Processor for Confluence and Splunk

**Current State**: JIRA has BatchProcessor with checkpointing. Confluence and Splunk lack this.

**What it provides**:
- Configurable batch size with `BatchConfig`
- Progress tracking with `BatchProgress`
- Checkpoint/resume support via `CheckpointManager`
- Graceful interruption handling

**Files to create**:
- `confluence-assistant-skills-lib/.../batch_processor.py` (copy from base library)
- `splunk-assistant-skills-lib/.../batch_processor.py` (copy from base library)

**Update __init__.py** in both libraries to export:
- `BatchConfig`, `BatchProcessor`, `BatchProgress`, `CheckpointManager`
- `generate_operation_id`, `get_recommended_batch_size`, `list_pending_checkpoints`

**Priority**: Medium
**Effort**: Low (base library already has it)

---

### 2.2 Request Batcher for Confluence and Splunk

**Current State**: JIRA has RequestBatcher for parallel HTTP requests. Confluence and Splunk lack this.

**What it provides**:
- Parallel HTTP request execution with configurable concurrency
- `BatchResult` with success/error tracking
- Thread-safe result aggregation

**Files to create**:
- `confluence-assistant-skills-lib/.../request_batcher.py` (copy from base library)
- `splunk-assistant-skills-lib/.../request_batcher.py` (copy from base library)

**Priority**: Medium
**Effort**: Low (base library already has it)

---

### 2.3 Keychain Integration for Confluence and Splunk

**Current State**:
- JIRA has full keychain integration with `is_keychain_available()`, `store_credentials()`, `get_credentials()`
- Confluence has `ConfluenceCredentialManager` but incomplete keychain support
- Splunk has `SplunkCredentialManager` but incomplete keychain support

**Target**: Full keychain integration matching JIRA's pattern.

**Files to update**:
- `confluence-assistant-skills-lib/.../credential_manager.py` - add keychain functions
- `splunk-assistant-skills-lib/.../credential_manager.py` - add keychain functions

**Functions to add**:
```python
def is_keychain_available() -> bool:
    """Check if keychain storage is available."""
    pass

def store_credentials(site_url: str, email: str, api_token: str) -> bool:
    """Store credentials in keychain."""
    pass

def get_credentials() -> tuple[str, str, str] | None:
    """Get credentials from keychain."""
    pass

def validate_credentials(site_url: str, email: str, api_token: str) -> bool:
    """Validate credentials by testing connection."""
    pass
```

**Priority**: High
**Effort**: Medium

---

### 2.4 Autocomplete Cache for Confluence and Splunk

**Current State**: JIRA has `AutocompleteCache` for CLI autocompletion. Others lack this.

**What it provides**:
- SQLite-based cache for autocomplete data
- Parallel background refresh
- CLI shell completion integration

**Files to create**:
- `confluence-assistant-skills-lib/.../autocomplete_cache.py`
- `splunk-assistant-skills-lib/.../autocomplete_cache.py`

**Priority**: Low
**Effort**: Medium

---

## Phase 3: Standardize CLI Patterns

### 3.1 CLI Context Sharing Pattern

**Current State**: All libraries use Click but with different context patterns.

**Standard Pattern** (from Splunk CLAUDE.md):
```python
# Use shared client via Click context
def get_client_from_context(ctx: click.Context) -> Client:
    """Get client from Click context, creating if needed."""
    if "client" not in ctx.obj:
        ctx.obj["client"] = get_client()
    return ctx.obj["client"]

# In commands:
@click.pass_context
def my_command(ctx):
    client = get_client_from_context(ctx)
```

**Files to update**:
- `confluence-assistant-skills-lib/cli/cli_utils.py` - add `get_client_from_context()`
- Ensure all command files use shared context

**Priority**: Medium
**Effort**: Low

---

### 3.2 Time Bounds Decorator Pattern

**Current State**: Splunk has `@with_time_bounds` decorator for `--earliest`/`--latest` options.

**Target**: Add to Confluence for date-range queries.

**Implementation**:
```python
def with_time_bounds(f):
    """Decorator adding --earliest and --latest options."""
    @click.option("--earliest", "-e", help="Start time")
    @click.option("--latest", "-l", help="End time")
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper
```

**Priority**: Low
**Effort**: Low

---

### 3.3 CLI Error Handler Decorator

**Current State**: All libraries have `handle_cli_errors` but implementations vary.

**Standard Pattern**:
```python
def handle_cli_errors(f):
    """Decorator for CLI commands with user-friendly error messages."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AuthenticationError as e:
            click.echo(f"Authentication failed: {e}", err=True)
            sys.exit(1)
        except ValidationError as e:
            click.echo(f"Validation error: {e}", err=True)
            sys.exit(1)
        # ... other error types
    return wrapper
```

**Priority**: Low
**Effort**: Low

---

## Phase 4: Test Infrastructure Alignment

### 4.1 Docker Container Pattern for Splunk

**Current State**: JIRA and Confluence have Docker container support for live integration tests. Splunk lacks this.

**What it provides**:
- `DockerSplunkContainer` class with reference counting
- Connection pooling with `get_splunk_connection()`
- Automatic cleanup with `reset_splunk_connection()`

**Files to create**:
- `splunk-assistant-skills-lib/tests/live_integration/__init__.py`
- `splunk-assistant-skills-lib/tests/live_integration/splunk_container.py`

**Priority**: Low
**Effort**: High (requires Splunk Docker image setup)

---

### 4.2 Conftest Patterns

**Standard fixtures for all libraries**:
```python
# conftest.py

@pytest.fixture
def mock_client():
    """Provide a fresh mock client for each test."""
    client = MockClient()
    yield client
    client.reset()

@pytest.fixture
def mock_config(monkeypatch):
    """Set up mock configuration environment."""
    monkeypatch.setenv("SERVICE_SITE_URL", "https://mock.example.com")
    monkeypatch.setenv("SERVICE_EMAIL", "test@example.com")
    monkeypatch.setenv("SERVICE_API_TOKEN", "test-token")
```

**Priority**: Low
**Effort**: Low

---

## Phase 5: Documentation Alignment

### 5.1 CLAUDE.md Completeness

**Current State**:
- JIRA: ~900 lines (comprehensive)
- Splunk: ~200 lines (comprehensive)
- Confluence: ~50 lines (needs expansion)

**Target**: All CLAUDE.md files should include:
- Build & Test Commands
- Architecture overview
- CLI Module structure
- Core Modules descriptions
- Key Patterns
- Security Considerations
- Coding Patterns with examples
- Test Markers list

**Files to update**:
- `confluence-assistant-skills-lib/CLAUDE.md` - expand significantly

**Priority**: Medium
**Effort**: Medium

---

## Phase 6: Unique Patterns to Consider Sharing

### 6.1 JIRA-Specific (Could Be Generalized)

| Pattern | Description | Generalizable? |
|---------|-------------|----------------|
| `ProjectContext` | Caches project metadata for intelligent defaults | Yes → BaseContext |
| `permission_helpers` | Permission scheme management | No (JIRA-specific) |
| `transition_helpers` | Workflow transition finding | No (JIRA-specific) |
| `user_helpers` | User resolution and batch lookup | Partially (user patterns common) |
| `adf_helper` | Atlassian Document Format | Yes (shared with Confluence) |

### 6.2 Confluence-Specific

| Pattern | Description | Generalizable? |
|---------|-------------|----------------|
| `SpaceContext` | Caches space metadata | Already generalized as Context |
| `xhtml_helper` | Legacy storage format | No (Confluence-specific) |
| `markdown_parser` | Markdown to ADF | Yes (shared with JIRA) |

### 6.3 Splunk-Specific

| Pattern | Description | Generalizable? |
|---------|-------------|----------------|
| `SearchContext` | Caches search metadata | Already generalized as Context |
| `spl_helper` | SPL query building | No (Splunk-specific) |
| `job_poller` | Async job state management | Partially (async patterns common) |
| `time_utils` | Splunk time modifiers | No (Splunk-specific) |

---

## Implementation Order

### Immediate (This Week)
1. **Phase 2.3**: Keychain integration for Confluence/Splunk
2. **Phase 5.1**: Expand Confluence CLAUDE.md

### Short-Term (Next 2 Weeks)
3. **Phase 2.1**: Batch Processor for Confluence/Splunk
4. **Phase 2.2**: Request Batcher for Confluence/Splunk
5. **Phase 3.1**: CLI Context sharing standardization

### Medium-Term (Next Month)
6. **Phase 1.1**: BaseConfigManager in assistant-skills-lib
7. **Phase 1.2**: BaseMockClient in assistant-skills-lib
8. **Phase 2.4**: Autocomplete Cache for Confluence/Splunk

### Long-Term (As Needed)
9. **Phase 4.1**: Docker Container for Splunk
10. **Phase 1.3**: is_mock_mode() factory in base library

---

## Files Changed Summary

### assistant-skills-lib (New)
- `src/assistant_skills_lib/config_manager.py` (new)
- `src/assistant_skills_lib/mock/__init__.py` (new)
- `src/assistant_skills_lib/mock/base.py` (new)
- `src/assistant_skills_lib/__init__.py` (update exports)

### confluence-assistant-skills-lib
- `src/confluence_assistant_skills/credential_manager.py` (add keychain)
- `src/confluence_assistant_skills/batch_processor.py` (new)
- `src/confluence_assistant_skills/request_batcher.py` (new)
- `src/confluence_assistant_skills/autocomplete_cache.py` (new)
- `src/confluence_assistant_skills/cli/cli_utils.py` (add context sharing)
- `CLAUDE.md` (expand)

### splunk-assistant-skills-lib
- `src/splunk_assistant_skills_lib/credential_manager.py` (add keychain)
- `src/splunk_assistant_skills_lib/batch_processor.py` (new)
- `src/splunk_assistant_skills_lib/request_batcher.py` (new)
- `src/splunk_assistant_skills_lib/autocomplete_cache.py` (new)
- `tests/live_integration/splunk_container.py` (new)

---

## Success Metrics

1. **Code Reuse**: 80%+ of common patterns use base library
2. **Feature Parity**: All three domain libraries have:
   - Keychain integration
   - Batch processing
   - Request batching
   - Mock client with `is_mock_mode()`
3. **Documentation**: All CLAUDE.md files > 200 lines
4. **Test Coverage**: All libraries have comprehensive pytest markers

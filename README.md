# JIRA AS

[![PyPI version](https://badge.fury.io/py/jira-as.svg)](https://badge.fury.io/py/jira-as)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library and CLI for JIRA REST API automation, providing HTTP client, configuration management, error handling, and utilities for the [JIRA Assistant Skills](https://github.com/grandcamel/Jira-Assistant-Skills) Claude Code plugin.

## Installation

```bash
pip install jira-as
```

With optional keyring support for secure credential storage:

```bash
pip install jira-as[keyring]
```

## Features

- **CLI (`jira-as`)**: Command-line interface for JIRA operations
- **JiraClient**: HTTP client with automatic retry logic and exponential backoff
- **ConfigManager**: Multi-source configuration (env vars > keychain > settings.local.json > settings.json > defaults)
- **Error Handling**: Exception hierarchy mapping HTTP status codes to domain exceptions
- **Validators**: Input validation for issue keys, project keys, JQL queries, URLs, and more
- **Formatters**: Output formatting for tables, JSON, CSV export
- **ADF Helper**: Atlassian Document Format conversion (markdown/text to ADF and back)
- **Time Utils**: JIRA time format parsing and formatting (e.g., '2h', '1d 4h 30m')
- **Cache**: SQLite-based caching with TTL support for API responses
- **Credential Manager**: Secure credential storage via system keychain or JSON fallback
- **Mock Client**: Full mock implementation for testing without JIRA access

## Quick Start

### Configuration

Set environment variables:

```bash
export JIRA_API_TOKEN="your-api-token"  # Get from https://id.atlassian.com/manage-profile/security/api-tokens
export JIRA_EMAIL="your-email@company.com"
export JIRA_SITE_URL="https://your-company.atlassian.net"
```

### CLI Usage

```bash
# Get an issue
jira-as issue get PROJ-123

# Search issues
jira-as search query "project = PROJ AND status = Open"

# Create an issue
jira-as issue create PROJ --summary "New task" --type Task

# Transition an issue
jira-as lifecycle transition PROJ-123 "In Progress"

# See all commands
jira-as --help
```

### Library Usage

```python
from jira_as import get_jira_client, handle_errors

@handle_errors
def main():
    # Get a configured JIRA client (use as context manager)
    with get_jira_client() as client:
        # Fetch an issue
        issue = client.get_issue('PROJ-123')
        print(f"Summary: {issue['fields']['summary']}")

        # Search issues with JQL
        results = client.search_issues('project = PROJ AND status = Open')
        for issue in results['issues']:
            print(f"{issue['key']}: {issue['fields']['summary']}")

if __name__ == '__main__':
    main()
```

## Core Components

### JiraClient

```python
from jira_as import JiraClient

# Direct instantiation (prefer get_jira_client() for config management)
client = JiraClient(
    base_url="https://your-company.atlassian.net",
    email="your-email@company.com",
    api_token="your-api-token"
)

# Use as context manager
with client:
    issue = client.get_issue('PROJ-123')
    client.create_issue(project_key='PROJ', summary='New issue', issue_type='Task')
    client.transition_issue('PROJ-123', 'Done')
```

### Error Handling

```python
from jira_as import (
    JiraError,
    AuthenticationError,
    PermissionError,
    NotFoundError,
    handle_errors
)

@handle_errors
def main():
    # Exceptions are caught and formatted nicely
    pass

# Or handle manually
try:
    with get_jira_client() as client:
        client.get_issue('INVALID-999')
except NotFoundError as e:
    print(f"Issue not found: {e}")
except AuthenticationError as e:
    print(f"Auth failed: {e}")
except JiraError as e:
    print(f"JIRA error: {e}")
```

### Validators

```python
from jira_as import (
    validate_issue_key,
    validate_project_key,
    validate_jql,
    validate_url,
    ValidationError
)

try:
    key = validate_issue_key('PROJ-123')  # Returns 'PROJ-123'
    key = validate_issue_key('invalid')   # Raises ValidationError
except ValidationError as e:
    print(f"Invalid input: {e}")
```

### ADF Helper

```python
from jira_as import (
    markdown_to_adf,
    text_to_adf,
    adf_to_text
)

# Convert markdown to ADF for JIRA
adf = markdown_to_adf("**Bold** and *italic* text")

# Convert plain text to ADF
adf = text_to_adf("Simple text content")

# Extract text from ADF
text = adf_to_text(adf_document)
```

### Time Utils

```python
from jira_as import (
    parse_time_string,
    format_seconds,
    parse_relative_date
)

# Parse JIRA time format to seconds
seconds = parse_time_string('2h 30m')  # 9000

# Format seconds to JIRA time format
time_str = format_seconds(9000)  # '2h 30m'

# Parse relative dates
dt = parse_relative_date('yesterday')
dt = parse_relative_date('2025-01-15')
```

## Mock Mode

For testing without JIRA access:

```bash
export JIRA_MOCK_MODE=true
jira-as issue get DEMO-85  # Returns mock data
```

```python
import os
os.environ['JIRA_MOCK_MODE'] = 'true'

from jira_as import get_jira_client

with get_jira_client() as client:  # Returns MockJiraClient
    issue = client.get_issue('DEMO-85')  # Mock data
```

## Development

```bash
# Clone the repository
git clone https://github.com/grandcamel/jira-as.git
cd jira-as

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code (black formats; ruff sorts imports)
black src tests
ruff check --fix src tests

# Type checking
mypy src
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Generic Surface

The `api` group exposes the pinned Jira Cloud platform v3, Jira Software and
Jira Service Management documents through as-engine. All three indexes are
primary. Start with `jira-as help`, `jira-as api search sprint`, or
`jira-as api describe getIssue`. Use `help paging`, `help search`, and
`help agile` for tagged operations; `--tier platform|software|servicedesk`
selects one document's help. `--full` expands descriptions, `--examples` shows
enrichment examples, and long help lists continue with `--offset`.

```sh
jira-as api --transport responder call getIssue --issueIdOrKey SBX-1
jira-as api call getIssue --issue-id-or-key PROJ-1
jira-as api call searchAndReconsileIssuesUsingJql --jql 'project = PROJ' --all --limit 100
jira-as api call searchAndReconsileIssuesUsingJqlPost --body @search.json --all
```

Parameters accept their exact published names and kebab aliases. Bodies come
from `--body @file`, `--body -` (stdin), or repeated `--field path=value`.
One page is returned by default. `--all` merges the tagged collection; its
`--limit` caps the total, while `--maxResults` or the body `maxResults` field
sets the request page size. For APIs with a `limit` parameter use
`--parameter-limit` alongside `--all`. JSON is the default call output;
`--format table|markdown` renders it. Errors are JSON on stderr with status,
messages, operation and note; exits distinguish usage (2), authentication (3),
permission (4), not found (5), server/transport (6), and conflict (7).

Automatic paging is unsupported for findBulkAssignableUsers, findAssignableUsers, findUsersWithAllPermissions, and findUsersWithBrowsePermission: they filter after slicing, so an empty page does not prove exhaustion. Use getAllUsers plus caller-side filtering.
For getAllUsers/getAllUsersDefault, maxResults above 1000 refuses before sending.
The supported bare-array endpoints advance by the sent page size and probe until
an empty page; a short nonempty page continues.

Discovery and responder mode need no credentials. HTTP calls use the existing
`JIRA_SITE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` and configuration chain only
when a call is sent. `JIRA_AS_TRANSPORT` selects `http`, `responder`, `cassette`
(with `JIRA_AS_CASSETTE`), or `simulation` (optional `JIRA_AS_SIMULATION_SEED`).
`JIRA_AS_RECORD` records HTTP responses through the shared scrubber. Simulation
is stateful for the supported wrapper workflows. Risk-tagged operations preview
without sending until `--confirm` is supplied.

Published operation IDs that collide are corrected in each document's
`identity.overlay.json`; descriptions/notes preserve their original names and
routes for search. Platform IDs are unchanged. Other examples include
`getSoftwareIssue`, `getBoardConfiguration`, `getServiceDeskArticles`, and
`getRequestAttachmentContent`. These explicit corrections preserve every route.

### Project scope

The Generic Surface checks generated scope tags against `JIRA_ALLOWED_PROJECTS`
before sending. An absent allowlist is unrestricted; an empty value denies scoped
calls. Body-only identity requires matching `--project KEY`, including bodies
read from files. Keyed updates also check any project change hidden in the body.
JQL requires a complete project restriction and supports literal AND predicates.
Site-level calls (including numeric board, sprint and service-desk routes) require
`JIRA_ALLOW_SITE_OPERATIONS=true`; the default is false. Discovery and help stay
settings-free. See [project scope details](docs/allowed-projects.md#generic-surface-project-scope-20).

### Wrapper migration

JAS-49 retains 35 wrappers that need a workflow, local transform, cache, or
autocomplete affordance; 14 compatibility verbs retain their 1.x names. The
remaining 143 wrappers are migration hints: invoking one performs no transport,
prints the indexed replacement, and exits 2; `--help` exits 0. Use `help
migration` or [the wrapper table](docs/wrapper-verbs.md) for the complete map.

The survivor groups are bulk, lifecycle, fields, ops, relationships, search,
time, dev, agile, and JSM. `fields list`, `fields get`, and `fields cache warm`
use the v2 cached instance metadata. `api call --adf-field customfield_ID`
explicitly converts Markdown to ADF; a warm textarea-field cache enables the
same conversion automatically. Stateful simulation exercises supported survivor
workflows without HTTP.

Sixteen commands remain on the legacy client pending JAS-64: admin automation
and automation-template, `dev get-commits`, and JSM asset commands. Jira
attachment multipart/binary transport and generic risk enrichment remain pending
JAS-65; their migration hints do not claim those capabilities are available.

### Instance fields cache

`fields cache warm` fetches instance metadata into
`~/.cache/jira-as/v2/instance-fields.json`, with a 24-hour TTL. Set
`JIRA_FIELDS_CACHE_DIR` (or `jira.fields_cache_dir` in configuration) to select
the directory; use separate directories for different Jira instances. Reads
never fetch metadata or migrate a 1.x cache. Missing, expired, or malformed
metadata is cold: `fields list` reports it, and `api describe createIssue`
explains that automatic textarea conversion is inactive. Explicit
`api call createIssue --adf-field customfield_ID …` still works with a cold
cache. For an offline warm-up, use `fields cache warm --transport responder`.

### Rich text and notes

Platform v3 description/environment, comment body and worklog comment paths
accept Markdown. Use real newlines in UTF-8 files:

```bash
jira-as api --transport responder call createIssue \
  --field fields.project.key=SBX --field fields.summary=x \
  --field fields.issuetype.name=Task --field fields.description=@notes.md
jira-as api --transport responder call addComment \
  --issueIdOrKey SBX-1 --field body=@notes.md
```

Tagged reads render Markdown with lossless placeholders for unsupported ADF
nodes; `--raw` preserves the stored ADF. Use a JSON `--body @request.json` or
stdin for already encoded ADF or an explicit null. Bulk create converts the
static paths in each `issueUpdates` item supplied as JSON. Use `--adf-field
customfield_ID` to convert a selected custom field; a warm instance-field cache
also converts textarea custom fields automatically. A cold cache leaves
unselected custom fields literal, and pre-encoded ADF passes through unchanged.
JSM request fields also pass through unchanged; its explicit
`isAdfRequest=true` mode requires caller-supplied ADF. JSM request comments
remain strings.

`help adf`, `help fields`, `help project-types`, `help rate-limits` and the other
topics render source-backed entries. `api describe` and errors carry relevant
notes. Removed issue-search operations name their `/search/jql` replacements;
use `api describe searchForIssuesUsingJql` or `help search`. The operationId
`search` continues to mean status discovery. Search hides deprecated operations
unless `--include-deprecated` is supplied; calling one warns on stderr.

## Build

The product vendors pristine Base Documents and manifest pins in
`src/jira_as/specs`. The wheel hook keeps the source stamp and compiles all
three documents through as-engine into `_generated/catalog.json` and three
indexes. Editable builds persist the same indexes; sdists contain source
inputs and the hook, excluding compiled indexes. Nothing is fetched during
compilation or runtime. The dependency range is `as-engine>=0.1.0a0,<0.2`.

To rebuild local indexes after changing an overlay:

```sh
python -c "from as_engine.build import compile_product; compile_product('src/jira_as/specs', 'src/jira_as/_generated')"
python scripts/generate_paging_tags.py
```

Run the generator before compilation when paging changes. Generated paging
precedes hand paging overrides in the manifest. Refresh deliberately with
`python scripts/refresh_base_documents.py --from-file platform=/path/to/document.json`
(and similarly `software` or `servicedesk`). The script records an oasdiff
changelog beside each refreshed source and updates manifest pins last. Set
`OASDIFF` to choose the executable. Without `--from-file` it explicitly fetches
the manifest URLs; offline workflows must supply local files.

### Compatibility Contract

The fourteen `jira-host` operations keep their recorded 1.x invocation and output
shapes on the generic engine path. The machine-readable contract, capture
provenance, scope rules and responder suite are described in
[Compatibility Contract](docs/compatibility-contract.md). Duration input accepts
both `2h30m` and `2h 30m`; `issue update --format markdown|text|adf` supplements
existing description auto-detection.

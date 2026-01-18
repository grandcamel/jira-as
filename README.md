# JIRA Assistant Skills

[![PyPI version](https://badge.fury.io/py/jira-assistant-skills.svg)](https://badge.fury.io/py/jira-assistant-skills)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library and CLI for JIRA REST API automation, providing HTTP client, configuration management, error handling, and utilities for the [JIRA Assistant Skills](https://github.com/grandcamel/Jira-Assistant-Skills) Claude Code plugin.

## Installation

```bash
pip install jira-assistant-skills
```

With optional keyring support for secure credential storage:

```bash
pip install jira-assistant-skills[keyring]
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
from jira_assistant_skills_lib import get_jira_client, handle_errors

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
from jira_assistant_skills_lib import JiraClient

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
from jira_assistant_skills_lib import (
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
from jira_assistant_skills_lib import (
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
from jira_assistant_skills_lib import (
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
from jira_assistant_skills_lib import (
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

from jira_assistant_skills_lib import get_jira_client

with get_jira_client() as client:  # Returns MockJiraClient
    issue = client.get_issue('DEMO-85')  # Mock data
```

## Development

```bash
# Clone the repository
git clone https://github.com/grandcamel/jira-assistant-skills-lib.git
cd jira-assistant-skills-lib

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
isort src tests

# Type checking
mypy src
```

## License

MIT License - see [LICENSE](LICENSE) for details.

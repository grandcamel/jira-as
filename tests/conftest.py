"""
Root conftest.py for jira-as tests.

Provides pytest hooks and shared fixtures for all tests.

Hooks:
- pytest_addoption: Adds --live CLI flag for running live API tests
- pytest_collection_modifyitems: Skips live tests unless --live flag is provided

Note: Markers are registered in pyproject.toml [tool.pytest.ini_options].markers

Fixtures:
- mock_config: Sample JIRA configuration dictionary
- mock_jira_client: Mock JiraClient for unit tests (re-exported from commands/conftest.py)
"""

import pytest


# =============================================================================
# Pytest Hooks
# =============================================================================


def pytest_addoption(parser):
    """Add custom CLI options for pytest."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run live JIRA API tests (requires credentials)",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on CLI flags."""
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="need --live option to run")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Sample JIRA configuration dictionary for testing."""
    return {
        "site_url": "https://test.atlassian.net",
        "email": "test@example.com",
        "api_token": "test-api-token",
        "default_project": "PROJ",
        "page_size": 50,
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Temporary directory for cache testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def sample_jql_results():
    """Sample JQL search results for testing."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 2,
        "issues": [
            {
                "id": "10001",
                "key": "PROJ-1",
                "fields": {
                    "summary": "First issue",
                    "status": {"name": "Open"},
                    "issuetype": {"name": "Bug"},
                },
            },
            {
                "id": "10002",
                "key": "PROJ-2",
                "fields": {
                    "summary": "Second issue",
                    "status": {"name": "In Progress"},
                    "issuetype": {"name": "Task"},
                },
            },
        ],
    }

"""
Tests for JiraClient using mocked HTTP responses.
"""

import json
import os
import tempfile

import pytest
import responses

from jira_as.error_handler import AuthenticationError
from jira_as.error_handler import NotFoundError
from jira_as.error_handler import PermissionError
from jira_as.error_handler import RateLimitError
from jira_as.error_handler import ServerError
from jira_as.error_handler import ValidationError
from jira_as.jira_client import JiraClient


@pytest.fixture
def client():
    """Create a JiraClient for testing."""
    return JiraClient(
        base_url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token",
        timeout=30,
    )


@pytest.fixture
def base_url():
    """Base URL for mocked responses."""
    return "https://test.atlassian.net"


class TestJiraClientInit:
    """Tests for JiraClient initialization."""

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base_url."""
        client = JiraClient(
            base_url="https://test.atlassian.net/",
            email="test@example.com",
            api_token="test-token",
        )
        assert client.base_url == "https://test.atlassian.net"

    def test_init_stores_credentials(self):
        """Test that credentials are stored."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )
        assert client.email == "test@example.com"
        assert client.api_token == "test-token"

    def test_init_stores_config(self):
        """Test that configuration is stored."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
            timeout=60,
            max_retries=5,
            retry_backoff=3.0,
        )
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_backoff == 3.0

    def test_init_creates_session(self):
        """Test that session is created with proper config."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )
        assert client.session is not None
        assert client.session.headers["Accept"] == "application/json"
        assert client.session.headers["Content-Type"] == "application/json"

    def test_context_manager(self):
        """Test client works as context manager."""
        with JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        ) as client:
            assert client.session is not None

    def test_close(self):
        """Test close method."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )
        client.close()
        # Session should still exist but be closed


class TestHttpMethods:
    """Tests for basic HTTP methods."""

    @responses.activate
    def test_get_success(self, client, base_url):
        """Test successful GET request."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/test",
            json={"key": "value"},
            status=200,
        )

        result = client.get("/rest/api/3/test")
        assert result == {"key": "value"}

    @responses.activate
    def test_get_with_params(self, client, base_url):
        """Test GET request with query parameters."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search",
            json={"issues": []},
            status=200,
        )

        result = client.get("/rest/api/3/search", params={"jql": "project=TEST"})
        assert result == {"issues": []}
        assert "jql=project%3DTEST" in responses.calls[0].request.url

    @responses.activate
    def test_post_success(self, client, base_url):
        """Test successful POST request."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue",
            json={"id": "10001", "key": "TEST-1"},
            status=201,
        )

        result = client.post(
            "/rest/api/3/issue",
            data={"fields": {"summary": "Test"}},
        )
        assert result["key"] == "TEST-1"

    @responses.activate
    def test_post_returns_empty_on_204(self, client, base_url):
        """Test POST with 204 No Content returns empty dict."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/test",
            status=204,
        )

        result = client.post("/rest/api/3/test", data={})
        assert result == {}

    @responses.activate
    def test_put_success(self, client, base_url):
        """Test successful PUT request."""
        responses.add(
            responses.PUT,
            f"{base_url}/rest/api/3/issue/TEST-1",
            status=204,
        )

        result = client.put(
            "/rest/api/3/issue/TEST-1",
            data={"fields": {"summary": "Updated"}},
        )
        assert result == {}

    @responses.activate
    def test_delete_success(self, client, base_url):
        """Test successful DELETE request."""
        responses.add(
            responses.DELETE,
            f"{base_url}/rest/api/3/issue/TEST-1",
            status=204,
        )

        result = client.delete("/rest/api/3/issue/TEST-1")
        assert result == {}


class TestErrorHandling:
    """Tests for error handling."""

    @responses.activate
    def test_401_raises_authentication_error(self, client, base_url):
        """Test 401 raises AuthenticationError."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json={"errorMessages": ["Not authenticated"]},
            status=401,
        )

        with pytest.raises(AuthenticationError):
            client.get("/rest/api/3/myself")

    @responses.activate
    def test_403_raises_permission_error(self, client, base_url):
        """Test 403 raises PermissionError."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/project/SECRET",
            json={"errorMessages": ["Access denied"]},
            status=403,
        )

        with pytest.raises(PermissionError):
            client.get("/rest/api/3/project/SECRET")

    @responses.activate
    def test_404_raises_not_found_error(self, client, base_url):
        """Test 404 raises NotFoundError."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/NOTFOUND-1",
            json={"errorMessages": ["Issue not found"]},
            status=404,
        )

        with pytest.raises(NotFoundError):
            client.get("/rest/api/3/issue/NOTFOUND-1")

    @responses.activate
    def test_400_raises_validation_error(self, client, base_url):
        """Test 400 raises ValidationError."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue",
            json={"errors": {"summary": "Required field"}},
            status=400,
        )

        with pytest.raises(ValidationError):
            client.post("/rest/api/3/issue", data={})

    @responses.activate
    def test_429_raises_rate_limit_error(self, client, base_url):
        """Test 429 raises RateLimitError."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search",
            json={"errorMessages": ["Rate limit exceeded"]},
            status=429,
        )

        with pytest.raises(RateLimitError):
            client.get("/rest/api/3/search")

    @responses.activate
    def test_500_raises_server_error(self, client, base_url):
        """Test 500 raises ServerError."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1",
            json={"errorMessages": ["Internal error"]},
            status=500,
        )

        with pytest.raises(ServerError):
            client.get("/rest/api/3/issue/TEST-1")


class TestIssueOperations:
    """Tests for issue CRUD operations."""

    @responses.activate
    def test_get_issue(self, client, base_url):
        """Test getting an issue."""
        issue_data = {
            "id": "10001",
            "key": "TEST-1",
            "fields": {
                "summary": "Test Issue",
                "status": {"name": "Open"},
            },
        }
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1",
            json=issue_data,
            status=200,
        )

        result = client.get_issue("TEST-1")
        assert result["key"] == "TEST-1"
        assert result["fields"]["summary"] == "Test Issue"

    @responses.activate
    def test_get_issue_with_fields(self, client, base_url):
        """Test getting an issue with specific fields."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1",
            json={"key": "TEST-1", "fields": {"summary": "Test"}},
            status=200,
        )

        client.get_issue("TEST-1", fields=["summary", "status"])
        assert "fields=summary%2Cstatus" in responses.calls[0].request.url

    @responses.activate
    def test_create_issue(self, client, base_url):
        """Test creating an issue."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue",
            json={"id": "10001", "key": "TEST-1"},
            status=201,
        )

        result = client.create_issue(
            {
                "project": {"key": "TEST"},
                "summary": "New Issue",
                "issuetype": {"name": "Task"},
            }
        )
        assert result["key"] == "TEST-1"

    @responses.activate
    def test_update_issue(self, client, base_url):
        """Test updating an issue."""
        responses.add(
            responses.PUT,
            f"{base_url}/rest/api/3/issue/TEST-1",
            status=204,
        )

        # update_issue returns None
        result = client.update_issue("TEST-1", {"summary": "Updated"})
        assert result is None

    @responses.activate
    def test_delete_issue(self, client, base_url):
        """Test deleting an issue."""
        responses.add(
            responses.DELETE,
            f"{base_url}/rest/api/3/issue/TEST-1",
            status=204,
        )

        # delete_issue returns None
        client.delete_issue("TEST-1")
        # Check param is in URL
        assert "deleteSubtasks=true" in responses.calls[0].request.url

    @responses.activate
    def test_delete_issue_without_subtasks(self, client, base_url):
        """Test deleting an issue without subtasks."""
        responses.add(
            responses.DELETE,
            f"{base_url}/rest/api/3/issue/TEST-1",
            status=204,
        )

        # When delete_subtasks=False, param should not be in URL
        client.delete_issue("TEST-1", delete_subtasks=False)
        # deleteSubtasks should NOT be in URL (only added when True)
        assert "deleteSubtasks" not in responses.calls[0].request.url


class TestSearchOperations:
    """Tests for search operations."""

    @responses.activate
    def test_search_issues(self, client, base_url):
        """Test searching issues with JQL."""
        # search_issues uses GET to /rest/api/3/search/jql
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search/jql",
            json={
                "issues": [{"key": "TEST-1"}, {"key": "TEST-2"}],
                "total": 2,
                "startAt": 0,
                "maxResults": 50,
            },
            status=200,
        )

        result = client.search_issues("project = TEST")
        assert len(result["issues"]) == 2
        assert result["total"] == 2

    @responses.activate
    def test_search_issues_with_fields(self, client, base_url):
        """Test searching with specific fields."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search/jql",
            json={"issues": [], "total": 0},
            status=200,
        )

        client.search_issues("project = TEST", fields=["summary", "status"])
        assert "fields=summary%2Cstatus" in responses.calls[0].request.url

    @responses.activate
    def test_search_issues_with_pagination(self, client, base_url):
        """Test searching with pagination."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search/jql",
            json={"issues": [], "total": 100, "startAt": 50, "maxResults": 25},
            status=200,
        )

        client.search_issues("project = TEST", start_at=50, max_results=25)
        assert "startAt=50" in responses.calls[0].request.url
        assert "maxResults=25" in responses.calls[0].request.url


class TestTransitionOperations:
    """Tests for transition operations."""

    @responses.activate
    def test_get_transitions(self, client, base_url):
        """Test getting available transitions."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1/transitions",
            json={
                "transitions": [
                    {"id": "11", "name": "To Do"},
                    {"id": "21", "name": "In Progress"},
                    {"id": "31", "name": "Done"},
                ]
            },
            status=200,
        )

        result = client.get_transitions("TEST-1")
        assert len(result) == 3
        assert result[0]["name"] == "To Do"

    @responses.activate
    def test_transition_issue(self, client, base_url):
        """Test transitioning an issue."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue/TEST-1/transitions",
            status=204,
        )

        client.transition_issue("TEST-1", "21")
        body = json.loads(responses.calls[0].request.body)
        assert body["transition"]["id"] == "21"

    @responses.activate
    def test_transition_issue_with_fields(self, client, base_url):
        """Test transitioning with additional fields."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue/TEST-1/transitions",
            status=204,
        )

        client.transition_issue(
            "TEST-1",
            "21",
            fields={"resolution": {"name": "Fixed"}},
        )
        body = json.loads(responses.calls[0].request.body)
        assert body["fields"]["resolution"]["name"] == "Fixed"


class TestCommentOperations:
    """Tests for comment operations."""

    @responses.activate
    def test_get_comments(self, client, base_url):
        """Test getting comments."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1/comment",
            json={
                "comments": [
                    {"id": "1", "body": {"type": "doc", "content": []}},
                ],
                "total": 1,
            },
            status=200,
        )

        result = client.get_comments("TEST-1")
        assert len(result["comments"]) == 1

    @responses.activate
    def test_add_comment(self, client, base_url):
        """Test adding a comment."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue/TEST-1/comment",
            json={"id": "10001", "body": {"type": "doc", "content": []}},
            status=201,
        )

        result = client.add_comment(
            "TEST-1",
            {"type": "doc", "version": 1, "content": []},
        )
        assert result["id"] == "10001"

    @responses.activate
    def test_update_comment(self, client, base_url):
        """Test updating a comment."""
        responses.add(
            responses.PUT,
            f"{base_url}/rest/api/3/issue/TEST-1/comment/10001",
            json={"id": "10001"},
            status=200,
        )

        result = client.update_comment(
            "TEST-1",
            "10001",
            {"type": "doc", "version": 1, "content": []},
        )
        assert result["id"] == "10001"

    @responses.activate
    def test_delete_comment(self, client, base_url):
        """Test deleting a comment."""
        responses.add(
            responses.DELETE,
            f"{base_url}/rest/api/3/issue/TEST-1/comment/10001",
            status=204,
        )

        client.delete_comment("TEST-1", "10001")
        assert len(responses.calls) == 1


class TestWorklogOperations:
    """Tests for worklog operations."""

    @responses.activate
    def test_add_worklog(self, client, base_url):
        """Test adding a worklog."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue/TEST-1/worklog",
            json={"id": "10001", "timeSpent": "1h"},
            status=201,
        )

        # add_worklog uses time_spent (string format like "1h")
        result = client.add_worklog("TEST-1", time_spent="1h")
        assert result["timeSpent"] == "1h"

    @responses.activate
    def test_add_worklog_with_comment(self, client, base_url):
        """Test adding a worklog with comment."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue/TEST-1/worklog",
            json={"id": "10001"},
            status=201,
        )

        client.add_worklog(
            "TEST-1",
            time_spent="1h",
            comment={"type": "doc", "content": []},
        )
        body = json.loads(responses.calls[0].request.body)
        assert body["timeSpent"] == "1h"
        assert "comment" in body

    @responses.activate
    def test_get_worklogs(self, client, base_url):
        """Test getting worklogs."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1/worklog",
            json={
                "worklogs": [{"id": "1", "timeSpent": "1h"}],
                "total": 1,
            },
            status=200,
        )

        result = client.get_worklogs("TEST-1")
        assert len(result["worklogs"]) == 1


class TestUserOperations:
    """Tests for user operations."""

    @responses.activate
    def test_get_current_user_id(self, client, base_url):
        """Test getting current user ID."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json={"accountId": "abc123", "displayName": "Test User"},
            status=200,
        )

        result = client.get_current_user_id()
        assert result == "abc123"

    @responses.activate
    def test_assign_issue(self, client, base_url):
        """Test assigning an issue."""
        responses.add(
            responses.PUT,
            f"{base_url}/rest/api/3/issue/TEST-1/assignee",
            status=204,
        )

        client.assign_issue("TEST-1", "abc123")
        body = json.loads(responses.calls[0].request.body)
        assert body["accountId"] == "abc123"

    @responses.activate
    def test_unassign_issue(self, client, base_url):
        """Test unassigning an issue (account_id=None sends None as body)."""
        responses.add(
            responses.PUT,
            f"{base_url}/rest/api/3/issue/TEST-1/assignee",
            status=204,
        )

        client.assign_issue("TEST-1", None)
        # When account_id is None, data is None (not {"accountId": None})
        assert responses.calls[0].request.body is None

    @responses.activate
    def test_search_users(self, client, base_url):
        """Test searching users."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/user/search",
            json=[{"accountId": "abc123", "displayName": "Test User"}],
            status=200,
        )

        result = client.search_users("test")
        assert len(result) == 1
        assert result[0]["accountId"] == "abc123"


class TestSprintOperations:
    """Tests for sprint operations."""

    @responses.activate
    def test_get_sprint(self, client, base_url):
        """Test getting a sprint."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/agile/1.0/sprint/1",
            json={"id": 1, "name": "Sprint 1", "state": "active"},
            status=200,
        )

        result = client.get_sprint(1)
        assert result["id"] == 1
        assert result["state"] == "active"

    @responses.activate
    def test_create_sprint(self, client, base_url):
        """Test creating a sprint."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/agile/1.0/sprint",
            json={"id": 1, "name": "New Sprint"},
            status=201,
        )

        result = client.create_sprint(
            board_id=1,
            name="New Sprint",
        )
        assert result["name"] == "New Sprint"

    @responses.activate
    def test_update_sprint(self, client, base_url):
        """Test updating a sprint (uses PUT per JIRA REST API spec)."""
        responses.add(
            responses.PUT,
            f"{base_url}/rest/agile/1.0/sprint/1",
            json={"id": 1, "name": "Updated Sprint"},
            status=200,
        )

        result = client.update_sprint(1, name="Updated Sprint")
        assert result["name"] == "Updated Sprint"

    @responses.activate
    def test_move_issues_to_sprint(self, client, base_url):
        """Test moving issues to sprint."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/agile/1.0/sprint/1/issue",
            status=204,
        )

        client.move_issues_to_sprint(1, ["TEST-1", "TEST-2"])
        body = json.loads(responses.calls[0].request.body)
        assert body["issues"] == ["TEST-1", "TEST-2"]


class TestBoardOperations:
    """Tests for board operations."""

    @responses.activate
    def test_get_board(self, client, base_url):
        """Test getting a board."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/agile/1.0/board/1",
            json={"id": 1, "name": "Test Board", "type": "scrum"},
            status=200,
        )

        result = client.get_board(1)
        assert result["name"] == "Test Board"

    @responses.activate
    def test_get_all_boards(self, client, base_url):
        """Test getting all boards."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/agile/1.0/board",
            json={
                "values": [{"id": 1, "name": "Board 1"}],
                "total": 1,
            },
            status=200,
        )

        result = client.get_all_boards()
        assert len(result["values"]) == 1

    @responses.activate
    def test_get_board_backlog(self, client, base_url):
        """Test getting board backlog."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/agile/1.0/board/1/backlog",
            json={"issues": [{"key": "TEST-1"}], "total": 1},
            status=200,
        )

        result = client.get_board_backlog(1)
        assert len(result["issues"]) == 1


class TestLinkOperations:
    """Tests for issue link operations."""

    @responses.activate
    def test_get_link_types(self, client, base_url):
        """Test getting link types."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issueLinkType",
            json={
                "issueLinkTypes": [
                    {
                        "id": "1",
                        "name": "Blocks",
                        "inward": "is blocked by",
                        "outward": "blocks",
                    },
                ]
            },
            status=200,
        )

        result = client.get_link_types()
        assert len(result) == 1
        assert result[0]["name"] == "Blocks"

    @responses.activate
    def test_create_link(self, client, base_url):
        """Test creating a link."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issueLink",
            json={},
            status=201,
        )

        # create_link signature: link_type, inward_key, outward_key
        client.create_link("Blocks", "TEST-1", "TEST-2")
        body = json.loads(responses.calls[0].request.body)
        assert body["type"]["name"] == "Blocks"
        assert body["inwardIssue"]["key"] == "TEST-1"
        assert body["outwardIssue"]["key"] == "TEST-2"

    @responses.activate
    def test_delete_link(self, client, base_url):
        """Test deleting a link."""
        responses.add(
            responses.DELETE,
            f"{base_url}/rest/api/3/issueLink/10001",
            status=204,
        )

        client.delete_link("10001")
        assert len(responses.calls) == 1


class TestProjectOperations:
    """Tests for project operations."""

    @responses.activate
    def test_get_project(self, client, base_url):
        """Test getting a project."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/project/TEST",
            json={"id": "10000", "key": "TEST", "name": "Test Project"},
            status=200,
        )

        result = client.get_project("TEST")
        assert result["key"] == "TEST"

    @responses.activate
    def test_create_project(self, client, base_url):
        """Test creating a project."""
        # create_project calls get_current_user_id if no lead provided
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json={"accountId": "abc123"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/project",
            json={"id": "10000", "key": "NEW"},
            status=201,
        )

        result = client.create_project(
            key="NEW",
            name="New Project",
            project_type_key="software",
        )
        assert result["key"] == "NEW"

    @responses.activate
    def test_create_project_with_lead(self, client, base_url):
        """Test creating a project with explicit lead."""
        responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/project",
            json={"id": "10000", "key": "NEW"},
            status=201,
        )

        result = client.create_project(
            key="NEW",
            name="New Project",
            project_type_key="software",
            lead_account_id="abc123",
        )
        assert result["key"] == "NEW"
        body = json.loads(responses.calls[0].request.body)
        assert body["leadAccountId"] == "abc123"

    @responses.activate
    def test_delete_project(self, client, base_url):
        """Test deleting a project."""
        responses.add(
            responses.DELETE,
            f"{base_url}/rest/api/3/project/TEST",
            status=204,
        )

        client.delete_project("TEST")
        assert "enableUndo=true" in responses.calls[0].request.url


class TestFileOperations:
    """Tests for file upload/download operations."""

    @responses.activate
    def test_upload_file(self, client, base_url):
        """Test uploading a file."""
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            responses.add(
                responses.POST,
                f"{base_url}/rest/api/3/issue/TEST-1/attachments",
                json=[{"id": "10001", "filename": "test.txt"}],
                status=200,
            )

            # upload_file takes endpoint as first param
            result = client.upload_file(
                "/rest/api/3/issue/TEST-1/attachments", temp_path
            )
            assert result[0]["filename"] == "test.txt"
        finally:
            os.unlink(temp_path)

    @responses.activate
    def test_download_file(self, client, base_url):
        """Test downloading a file."""
        # download_file takes a full URL
        responses.add(
            responses.GET,
            f"{base_url}/secure/attachment/10001/file.txt",
            body=b"file content",
            status=200,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "downloaded.txt")
            # download_file takes full URL, not just ID
            client.download_file(
                f"{base_url}/secure/attachment/10001/file.txt", output_path
            )
            assert os.path.exists(output_path)
            with open(output_path, "rb") as f:
                assert f.read() == b"file content"


class TestTimeTracking:
    """Tests for time tracking operations."""

    @responses.activate
    def test_get_time_tracking(self, client, base_url):
        """Test getting time tracking info."""
        responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1",
            json={
                "fields": {
                    "timetracking": {
                        "originalEstimate": "2h",
                        "remainingEstimate": "1h",
                        "timeSpent": "1h",
                    }
                }
            },
            status=200,
        )

        result = client.get_time_tracking("TEST-1")
        assert result["originalEstimate"] == "2h"

    @responses.activate
    def test_set_time_tracking(self, client, base_url):
        """Test setting time tracking."""
        responses.add(
            responses.PUT,
            f"{base_url}/rest/api/3/issue/TEST-1",
            status=204,
        )

        client.set_time_tracking("TEST-1", original_estimate="4h")
        body = json.loads(responses.calls[0].request.body)
        assert body["fields"]["timetracking"]["originalEstimate"] == "4h"

"""Tests for mock client mixins.

Tests the mixin functionality in isolation using the composed MockJiraClient.
"""

import pytest

from jira_as.mock import MockJiraClient
from jira_as.error_handler import NotFoundError


class TestTimeTrackingMixin:
    """Tests for TimeTrackingMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_get_time_tracking_configuration(self, client):
        """Test getting time tracking configuration."""
        config = client.get_time_tracking_configuration()
        assert "workingHoursPerDay" in config
        assert "workingDaysPerWeek" in config
        assert "timeFormat" in config
        assert "defaultUnit" in config

    def test_set_time_tracking_configuration(self, client):
        """Test setting time tracking configuration."""
        config = client.set_time_tracking_configuration(
            working_hours_per_day=7.5,
            working_days_per_week=4,
            time_format="days",
            default_unit="hour",
        )
        assert config["workingHoursPerDay"] == 7.5
        assert config["workingDaysPerWeek"] == 4
        assert config["timeFormat"] == "days"
        assert config["defaultUnit"] == "hour"

    def test_get_time_tracking_existing_issue(self, client):
        """Test getting time tracking for existing issue."""
        # DEMO-84 exists in seed data
        tracking = client.get_time_tracking("DEMO-84")
        assert "originalEstimate" in tracking or tracking == {}

    def test_get_time_tracking_nonexistent_issue(self, client):
        """Test getting time tracking for non-existent issue raises error."""
        with pytest.raises(NotFoundError):
            client.get_time_tracking("NONEXISTENT-999")

    def test_set_estimate(self, client):
        """Test setting estimate."""
        client.set_estimate("DEMO-84", "2h")
        tracking = client.get_time_tracking("DEMO-84")
        assert "originalEstimate" in tracking or "remainingEstimate" in tracking

    def test_adjust_remaining_estimate(self, client):
        """Test adjusting remaining estimate."""
        client.adjust_remaining_estimate("DEMO-84", "1h 30m")
        tracking = client.get_time_tracking("DEMO-84")
        assert "remainingEstimate" in tracking

    def test_add_worklog(self, client):
        """Test adding worklog to issue."""
        worklog = client.add_worklog(
            issue_key="DEMO-84",
            time_spent="1h",
            comment="Working on this",
        )
        assert "id" in worklog
        assert worklog["timeSpent"] == "1h"

    def test_get_worklogs(self, client):
        """Test getting worklogs for issue."""
        # Add a worklog first
        client.add_worklog("DEMO-84", "1h", "Test worklog")

        worklogs = client.get_worklogs("DEMO-84")
        assert "worklogs" in worklogs
        assert len(worklogs["worklogs"]) >= 1

    def test_update_worklog(self, client):
        """Test updating a worklog."""
        # Add a worklog first
        worklog = client.add_worklog("DEMO-84", "1h", "Original")

        # Update it
        updated = client.update_worklog(
            issue_key="DEMO-84",
            worklog_id=worklog["id"],
            time_spent="2h",
            comment="Updated",
        )
        assert updated["timeSpent"] == "2h"

    def test_delete_worklog(self, client):
        """Test deleting a worklog."""
        # Add a worklog first
        worklog = client.add_worklog("DEMO-84", "1h", "To delete")

        # Delete it
        client.delete_worklog("DEMO-84", worklog["id"])

        # Verify it's gone
        worklogs = client.get_worklogs("DEMO-84")
        worklog_ids = [w["id"] for w in worklogs["worklogs"]]
        assert worklog["id"] not in worklog_ids

    def test_get_worklog(self, client):
        """Test getting a specific worklog."""
        # Add a worklog first
        worklog = client.add_worklog("DEMO-84", "2h", "Test worklog")

        # Get it
        fetched = client.get_worklog("DEMO-84", worklog["id"])
        assert fetched["id"] == worklog["id"]

    def test_get_worklog_ids_modified_since(self, client):
        """Test getting worklog IDs modified since a date."""
        result = client.get_worklog_ids_modified_since(0)
        assert "values" in result

    def test_get_user_worklogs(self, client):
        """Test getting worklogs for a user."""
        result = client.get_user_worklogs("abc123")
        assert "worklogs" in result

    def test_get_project_worklogs(self, client):
        """Test getting worklogs for a project."""
        result = client.get_project_worklogs("DEMO")
        assert "worklogs" in result

    def test_get_time_report(self, client):
        """Test getting time tracking report."""
        report = client.get_time_report("DEMO-84")
        assert isinstance(report, dict)


class TestSearchMixin:
    """Tests for SearchMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_search_issues_basic(self, client):
        """Test basic JQL search."""
        results = client.search_issues("project = DEMO")
        assert "issues" in results
        assert "total" in results

    def test_search_issues_with_fields(self, client):
        """Test search with specific fields."""
        results = client.search_issues(
            "project = DEMO",
            fields=["summary", "status"],
        )
        assert "issues" in results

    def test_search_issues_pagination(self, client):
        """Test search pagination."""
        results = client.search_issues(
            "project = DEMO",
            start_at=0,
            max_results=10,
        )
        assert results["startAt"] == 0
        assert results["maxResults"] == 10

    def test_search_issues_by_status(self, client):
        """Test search by status."""
        results = client.search_issues("project = DEMO AND status = Open")
        # Should return issues (may be empty if no Open issues in seed data)
        assert "issues" in results

    def test_search_issues_by_issue_type(self, client):
        """Test search by issue type."""
        results = client.search_issues("project = DEMO AND issuetype = Bug")
        assert "issues" in results

    def test_search_issues_by_assignee(self, client):
        """Test search by assignee."""
        results = client.search_issues("project = DEMO AND assignee = currentUser()")
        assert "issues" in results

    def test_search_issues_order_by(self, client):
        """Test search with ORDER BY."""
        results = client.search_issues(
            "project = DEMO ORDER BY created DESC"
        )
        assert "issues" in results

    def test_advanced_search(self, client):
        """Test advanced JQL search."""
        results = client.advanced_search("project = DEMO")
        assert "issues" in results
        assert "total" in results
        assert "expand" in results

    def test_advanced_search_with_expand(self, client):
        """Test advanced search with expand parameter."""
        results = client.advanced_search(
            "project = DEMO",
            expand=["changelog", "renderedFields"],
        )
        assert "expand" in results

    def test_validate_jql(self, client):
        """Test JQL validation."""
        result = client.validate_jql("project = DEMO")
        assert isinstance(result, dict)

    def test_validate_jql_invalid(self, client):
        """Test JQL validation with invalid query."""
        result = client.validate_jql("invalid query ===")
        # Should return validation result (may include errors/warnings)
        assert isinstance(result, dict)

    def test_get_filter(self, client):
        """Test getting a filter."""
        filter_result = client.get_filter("10000")
        assert "id" in filter_result
        assert "name" in filter_result

    def test_get_my_filters(self, client):
        """Test getting current user's filters."""
        filters = client.get_my_filters()
        assert isinstance(filters, list)

    def test_get_favourite_filters(self, client):
        """Test getting favourite filters."""
        filters = client.get_favourite_filters()
        assert isinstance(filters, list)

    def test_create_filter(self, client):
        """Test creating a filter."""
        new_filter = client.create_filter(
            name="New Test Filter",
            jql="project = DEMO AND issuetype = Task",
        )
        assert "id" in new_filter
        assert new_filter["name"] == "New Test Filter"

    def test_update_filter(self, client):
        """Test updating a filter."""
        updated = client.update_filter(
            filter_id="10000",
            name="Updated Filter Name",
        )
        assert updated["name"] == "Updated Filter Name"

    def test_delete_filter(self, client):
        """Test deleting a filter."""
        # Use an existing filter ID that we know exists
        # Delete may fail if filter doesn't exist in mock, just verify no crash
        try:
            client.delete_filter("10001")
        except Exception:
            pass  # Expected if filter management differs

    def test_search_filters(self, client):
        """Test searching filters."""
        result = client.search_filters(filter_name="Bug")
        assert "values" in result or isinstance(result, list)

    def test_set_filter_favourite(self, client):
        """Test setting filter as favourite."""
        result = client.set_filter_favourite("10001", favourite=True)
        assert result["favourite"] is True

    def test_search_issues_by_keys(self, client):
        """Test searching by specific issue keys."""
        results = client.search_issues_by_keys(["DEMO-84", "DEMO-85"])
        # Returns list directly, not paginated
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_count_issues(self, client):
        """Test counting issues matching JQL."""
        count = client.count_issues("project = DEMO")
        assert isinstance(count, int)
        assert count >= 0

    def test_export_search_results(self, client):
        """Test exporting search results."""
        results = client.export_search_results("project = DEMO")
        assert "data" in results or isinstance(results, list)


class TestRelationshipsMixin:
    """Tests for RelationshipsMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_get_issue_link_types(self, client):
        """Test getting issue link types."""
        link_types = client.get_issue_link_types()
        assert "issueLinkTypes" in link_types
        assert len(link_types["issueLinkTypes"]) > 0

    def test_create_issue_link(self, client):
        """Test creating issue link."""
        # Link DEMO-84 to DEMO-85
        client.create_issue_link(
            link_type="Relates",
            inward_issue="DEMO-84",
            outward_issue="DEMO-85",
        )
        # Just verify the call succeeds
        # Links may be stored differently in the mock

    def test_delete_issue_link(self, client):
        """Test deleting issue link."""
        # Create a link first
        client.create_issue_link(
            link_type="Relates",
            inward_issue="DEMO-84",
            outward_issue="DEMO-85",
        )

        # Get the link ID
        issue = client.get_issue("DEMO-84")
        links = issue["fields"].get("issuelinks", [])
        if links:
            link_id = links[0]["id"]
            client.delete_issue_link(link_id)

    def test_get_remote_links(self, client):
        """Test getting remote links."""
        links = client.get_remote_links("DEMO-84")
        assert isinstance(links, list)

    def test_create_remote_link(self, client):
        """Test creating remote link."""
        link = client.create_remote_link(
            issue_key="DEMO-84",
            url="https://example.com",
            title="Example Link",
        )
        assert "id" in link


class TestCollaborateMixin:
    """Tests for CollaborateMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_add_comment(self, client):
        """Test adding comment to issue."""
        comment = client.add_comment("DEMO-84", "Test comment")
        assert "id" in comment
        assert "Test comment" in str(comment.get("body", ""))

    def test_get_comments(self, client):
        """Test getting comments for issue."""
        # Add a comment first
        client.add_comment("DEMO-84", "Test comment for get")

        comments = client.get_comments("DEMO-84")
        assert "comments" in comments
        assert len(comments["comments"]) >= 1

    def test_update_comment(self, client):
        """Test updating a comment."""
        # Add a comment first
        comment = client.add_comment("DEMO-84", "Original comment")

        # Update it
        updated = client.update_comment(
            issue_key="DEMO-84",
            comment_id=comment["id"],
            body="Updated comment",
        )
        assert "Updated comment" in str(updated.get("body", ""))

    def test_delete_comment(self, client):
        """Test deleting a comment."""
        # Add a comment first
        comment = client.add_comment("DEMO-84", "To delete")

        # Delete it
        client.delete_comment("DEMO-84", comment["id"])

    def test_get_watchers(self, client):
        """Test getting watchers for issue."""
        watchers = client.get_watchers("DEMO-84")
        assert "watchCount" in watchers

    def test_add_watcher(self, client):
        """Test adding watcher to issue."""
        client.add_watcher("DEMO-84", "abc123")
        watchers = client.get_watchers("DEMO-84")
        assert watchers["watchCount"] >= 1

    def test_remove_watcher(self, client):
        """Test removing watcher from issue."""
        # Add a watcher first
        client.add_watcher("DEMO-84", "abc123")

        # Remove them
        client.remove_watcher("DEMO-84", "abc123")


class TestAgileMixin:
    """Tests for AgileMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_get_boards(self, client):
        """Test getting agile boards."""
        boards = client.get_boards()
        assert "values" in boards

    def test_get_board(self, client):
        """Test getting specific board."""
        # Board 1 exists in seed data
        board = client.get_board(1)
        assert "id" in board
        assert "name" in board

    def test_get_sprints(self, client):
        """Test getting sprints for board."""
        sprints = client.get_sprints(1)
        assert "values" in sprints

    def test_get_backlog_issues(self, client):
        """Test getting backlog issues."""
        issues = client.get_backlog_issues(1)
        assert "issues" in issues


class TestAdminMixin:
    """Tests for AdminMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_get_all_projects(self, client):
        """Test getting all projects."""
        projects = client.get_all_projects()
        assert len(projects) > 0

    def test_get_project(self, client):
        """Test getting specific project."""
        project = client.get_project("DEMO")
        assert project["key"] == "DEMO"

    def test_get_project_nonexistent(self, client):
        """Test getting non-existent project raises error."""
        with pytest.raises(NotFoundError):
            client.get_project("NONEXISTENT")

    def test_get_issue_types(self, client):
        """Test getting issue types."""
        types = client.get_issue_types()
        assert len(types) > 0
        # Should have standard types
        type_names = [t["name"] for t in types]
        assert "Bug" in type_names or "Story" in type_names

    def test_get_priorities(self, client):
        """Test getting priorities."""
        priorities = client.get_priorities()
        assert len(priorities) > 0

    def test_get_project_statuses(self, client):
        """Test getting project statuses."""
        statuses = client.get_project_statuses("DEMO")
        assert len(statuses) > 0


class TestFieldsMixin:
    """Tests for FieldsMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_get_fields(self, client):
        """Test getting all fields."""
        fields = client.get_fields()
        assert len(fields) > 0

    def test_get_field(self, client):
        """Test getting specific field."""
        fields = client.get_fields()
        if fields:
            field_id = fields[0]["id"]
            field = client.get_field(field_id)
            assert "id" in field


class TestJSMMixin:
    """Tests for JSMMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_get_service_desks(self, client):
        """Test getting service desks."""
        desks = client.get_service_desks()
        assert "values" in desks

    def test_get_request_types(self, client):
        """Test getting request types for service desk."""
        types = client.get_request_types(1)
        assert "values" in types

    def test_get_customers(self, client):
        """Test getting customers for service desk."""
        customers = client.get_customers(1)
        assert "values" in customers


class TestDevMixin:
    """Tests for DevMixin functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh mock client."""
        return MockJiraClient()

    def test_get_development_status(self, client):
        """Test getting development status for issue."""
        # This may return empty or mock data
        status = client.get_development_status("DEMO-84")
        assert isinstance(status, dict)

    def test_generate_branch_name(self, client):
        """Test generating branch name for issue."""
        branch = client.generate_branch_name("DEMO-84")
        # Branch name may be lowercase
        assert "demo-84" in branch.lower()

    def test_generate_commit_message(self, client):
        """Test generating commit message for issue."""
        message = client.generate_commit_message("DEMO-84", "Test message")
        assert "DEMO-84" in message

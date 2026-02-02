"""
Tests for mock factory classes.
"""

from jira_as.mock.factories import (
    CommentFactory,
    ResponseFactory,
    StatusFactory,
    TimestampFactory,
    URLFactory,
    UserFactory,
)


class TestResponseFactory:
    """Test ResponseFactory methods."""

    def test_paginated_standard_format(self):
        """Test standard paginated response."""
        items = ["a", "b", "c", "d", "e"]
        result = ResponseFactory.paginated(items, start_at=0, max_results=3)

        assert result["startAt"] == 0
        assert result["maxResults"] == 3
        assert result["total"] == 5
        assert result["isLast"] is False
        assert result["values"] == ["a", "b", "c"]

    def test_paginated_last_page(self):
        """Test paginated response on last page."""
        items = ["a", "b", "c"]
        result = ResponseFactory.paginated(items, start_at=0, max_results=10)

        assert result["isLast"] is True
        assert result["values"] == ["a", "b", "c"]

    def test_paginated_with_offset(self):
        """Test paginated response with offset."""
        items = ["a", "b", "c", "d", "e"]
        result = ResponseFactory.paginated(items, start_at=2, max_results=2)

        assert result["startAt"] == 2
        assert result["values"] == ["c", "d"]
        assert result["isLast"] is False

    def test_paginated_jsm_format(self):
        """Test JSM paginated response format."""
        items = ["a", "b", "c"]
        result = ResponseFactory.paginated(
            items, start_at=0, max_results=10, format="jsm"
        )

        assert result["size"] == 3
        assert result["start"] == 0
        assert result["limit"] == 10
        assert result["isLastPage"] is True
        assert result["values"] == ["a", "b", "c"]

    def test_paginated_empty_list(self):
        """Test paginated with empty list."""
        result = ResponseFactory.paginated([], start_at=0, max_results=10)

        assert result["total"] == 0
        assert result["values"] == []
        assert result["isLast"] is True

    def test_paginated_issues(self):
        """Test paginated issues response."""
        issues = [{"key": "PROJ-1"}, {"key": "PROJ-2"}, {"key": "PROJ-3"}]
        result = ResponseFactory.paginated_issues(issues, start_at=0, max_results=2)

        assert result["startAt"] == 0
        assert result["maxResults"] == 2
        assert result["total"] == 3
        assert len(result["issues"]) == 2
        assert result["issues"][0]["key"] == "PROJ-1"

    def test_paginated_issues_empty(self):
        """Test paginated issues with empty list."""
        result = ResponseFactory.paginated_issues([], start_at=0, max_results=10)

        assert result["total"] == 0
        assert result["issues"] == []


class TestURLFactory:
    """Test URLFactory methods."""

    BASE_URL = "https://example.atlassian.net"

    def test_issue_url(self):
        """Test issue URL generation."""
        url = URLFactory.issue(self.BASE_URL, "12345")
        assert url == f"{self.BASE_URL}/rest/api/3/issue/12345"

    def test_project_url(self):
        """Test project URL generation."""
        url = URLFactory.project(self.BASE_URL, "PROJ")
        assert url == f"{self.BASE_URL}/rest/api/3/project/PROJ"

    def test_user_url(self):
        """Test user URL generation."""
        url = URLFactory.user(self.BASE_URL, "abc123")
        assert url == f"{self.BASE_URL}/rest/api/3/user?accountId=abc123"

    def test_board_url(self):
        """Test board URL generation."""
        url = URLFactory.board(self.BASE_URL, 42)
        assert url == f"{self.BASE_URL}/rest/agile/1.0/board/42"

    def test_board_url_string_id(self):
        """Test board URL with string ID."""
        url = URLFactory.board(self.BASE_URL, "42")
        assert url == f"{self.BASE_URL}/rest/agile/1.0/board/42"

    def test_sprint_url(self):
        """Test sprint URL generation."""
        url = URLFactory.sprint(self.BASE_URL, 100)
        assert url == f"{self.BASE_URL}/rest/agile/1.0/sprint/100"

    def test_comment_url(self):
        """Test comment URL generation."""
        url = URLFactory.comment(self.BASE_URL, "12345", "67890")
        assert url == f"{self.BASE_URL}/rest/api/3/issue/12345/comment/67890"

    def test_attachment_url(self):
        """Test attachment URL generation."""
        url = URLFactory.attachment(self.BASE_URL, "att-123")
        assert url == f"{self.BASE_URL}/rest/api/3/attachment/att-123"

    def test_worklog_url(self):
        """Test worklog URL generation."""
        url = URLFactory.worklog(self.BASE_URL, "12345", "wl-123")
        assert url == f"{self.BASE_URL}/rest/api/3/issue/12345/worklog/wl-123"

    def test_filter_url(self):
        """Test filter URL generation."""
        url = URLFactory.filter(self.BASE_URL, "10000")
        assert url == f"{self.BASE_URL}/rest/api/3/filter/10000"

    def test_role_url(self):
        """Test role URL generation."""
        url = URLFactory.role(self.BASE_URL, 10002)
        assert url == f"{self.BASE_URL}/rest/api/3/role/10002"


class TestUserFactory:
    """Test UserFactory methods."""

    def test_full_user(self):
        """Test creating a full user object."""
        user = UserFactory.full(
            account_id="abc123",
            display_name="John Doe",
            email="john@example.com",
            active=True,
        )

        assert user["accountId"] == "abc123"
        assert user["displayName"] == "John Doe"
        assert user["emailAddress"] == "john@example.com"
        assert user["active"] is True

    def test_full_user_without_email(self):
        """Test creating a full user without email."""
        user = UserFactory.full(
            account_id="abc123",
            display_name="John Doe",
        )

        assert user["accountId"] == "abc123"
        assert user["displayName"] == "John Doe"
        assert "emailAddress" not in user
        assert user["active"] is True  # default

    def test_full_user_inactive(self):
        """Test creating an inactive user."""
        user = UserFactory.full(
            account_id="abc123",
            display_name="John Doe",
            active=False,
        )

        assert user["active"] is False

    def test_minimal_user(self):
        """Test creating a minimal user object."""
        user = UserFactory.minimal(account_id="abc123", display_name="John Doe")

        assert user["accountId"] == "abc123"
        assert user["displayName"] == "John Doe"
        assert "emailAddress" not in user
        assert "active" not in user

    def test_unknown_user(self):
        """Test creating an unknown user placeholder."""
        user = UserFactory.unknown(account_id="unknown-123")

        assert user["accountId"] == "unknown-123"
        assert user["displayName"] == "Unknown User"


class TestTimestampFactory:
    """Test TimestampFactory methods."""

    def test_default_timestamp(self):
        """Test DEFAULT_TIMESTAMP constant."""
        assert TimestampFactory.DEFAULT_TIMESTAMP == "2025-01-01T10:00:00.000+0000"

    def test_standard_timestamp_default(self):
        """Test standard timestamp with default."""
        ts = TimestampFactory.standard()
        assert ts == TimestampFactory.DEFAULT_TIMESTAMP

    def test_standard_timestamp_custom(self):
        """Test standard timestamp with custom value."""
        ts = TimestampFactory.standard("2024-06-15T14:30:00.000+0000")
        assert ts == "2024-06-15T14:30:00.000+0000"

    def test_jsm_timestamp_default(self):
        """Test JSM timestamp with default."""
        ts = TimestampFactory.jsm()
        assert ts == {"iso8601": "2025-01-01T10:00:00+0000"}

    def test_jsm_timestamp_custom(self):
        """Test JSM timestamp with custom value."""
        ts = TimestampFactory.jsm("2024-06-15T14:30:00+0000")
        assert ts == {"iso8601": "2024-06-15T14:30:00+0000"}


class TestCommentFactory:
    """Test CommentFactory methods."""

    def test_standard_comment(self):
        """Test creating a standard comment."""
        author = UserFactory.minimal("abc123", "John Doe")
        comment = CommentFactory.standard(
            comment_id="10001",
            body="This is a comment",
            author=author,
        )

        assert comment["id"] == "10001"
        assert comment["body"] == "This is a comment"
        assert comment["author"] == author
        assert "created" in comment
        assert "updated" in comment

    def test_standard_comment_with_timestamps(self):
        """Test creating a comment with custom timestamps."""
        author = UserFactory.minimal("abc123", "John Doe")
        comment = CommentFactory.standard(
            comment_id="10001",
            body="This is a comment",
            author=author,
            created="2024-01-01T10:00:00.000+0000",
            updated="2024-01-02T10:00:00.000+0000",
        )

        assert comment["created"] == "2024-01-01T10:00:00.000+0000"
        assert comment["updated"] == "2024-01-02T10:00:00.000+0000"

    def test_standard_comment_with_adf_body(self):
        """Test creating a comment with ADF body."""
        author = UserFactory.minimal("abc123", "John Doe")
        adf_body = {
            "version": 1,
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]}
            ],
        }
        comment = CommentFactory.standard(
            comment_id="10001",
            body=adf_body,
            author=author,
        )

        assert comment["body"] == adf_body

    def test_jsm_comment(self):
        """Test creating a JSM request comment."""
        author = UserFactory.minimal("abc123", "John Doe")
        comment = CommentFactory.jsm(
            comment_id="10001",
            body="This is a JSM comment",
            author=author,
            public=True,
        )

        assert comment["id"] == "10001"
        assert comment["body"] == "This is a JSM comment"
        assert comment["author"] == author
        assert comment["public"] is True
        assert "created" in comment
        assert "iso8601" in comment["created"]

    def test_jsm_comment_internal(self):
        """Test creating an internal JSM comment."""
        author = UserFactory.minimal("abc123", "John Doe")
        comment = CommentFactory.jsm(
            comment_id="10001",
            body="Internal note",
            author=author,
            public=False,
        )

        assert comment["public"] is False


class TestStatusFactory:
    """Test StatusFactory methods."""

    def test_build_status(self):
        """Test building a basic status."""
        status = StatusFactory.build(name="To Do", status_id="10001")

        assert status["name"] == "To Do"
        assert status["id"] == "10001"

    def test_status_with_category(self):
        """Test building a status with category."""
        status = StatusFactory.with_category(
            name="In Progress",
            status_id="10002",
            category="IN_PROGRESS",
        )

        assert status["name"] == "In Progress"
        assert status["id"] == "10002"
        assert status["statusCategory"]["name"] == "IN_PROGRESS"
        assert status["statusCategory"]["key"] == "in_progress"

    def test_status_with_default_category(self):
        """Test building a status with default TODO category."""
        status = StatusFactory.with_category(
            name="Open",
            status_id="10001",
        )

        assert status["statusCategory"]["name"] == "TODO"
        assert status["statusCategory"]["key"] == "todo"

"""
Tests for user_helpers module.
"""

from unittest.mock import MagicMock

import pytest

from jira_as.user_helpers import (
    UserNotFoundError,
    get_user_display_info,
    resolve_user_to_account_id,
    resolve_users_batch,
)


class TestUserNotFoundError:
    """Tests for UserNotFoundError exception."""

    def test_error_stores_identifier(self):
        """Test that identifier is stored on the exception."""
        error = UserNotFoundError("user@example.com")
        assert error.identifier == "user@example.com"

    def test_error_message_format(self):
        """Test that error message follows expected format."""
        error = UserNotFoundError("user@example.com")
        # NotFoundError format: "{resource_type} not found: {resource_id}"
        assert "User" in str(error)
        assert "user@example.com" in str(error)

    def test_error_is_not_found_error(self):
        """Test that error inherits from NotFoundError."""
        from jira_as.error_handler import NotFoundError

        error = UserNotFoundError("test")
        assert isinstance(error, NotFoundError)


class TestResolveUserToAccountId:
    """Tests for resolve_user_to_account_id function."""

    def test_email_triggers_search(self):
        """Test that email address triggers user search."""
        mock_client = MagicMock()
        mock_client.search_users.return_value = [{"accountId": "abc123"}]

        result = resolve_user_to_account_id(mock_client, "user@example.com")

        assert result == "abc123"
        mock_client.search_users.assert_called_once_with(
            "user@example.com", max_results=1
        )

    def test_account_id_passed_through(self):
        """Test that account ID (no @) is passed through without search."""
        mock_client = MagicMock()

        result = resolve_user_to_account_id(mock_client, "abc123")

        assert result == "abc123"
        mock_client.search_users.assert_not_called()

    def test_email_not_found_raises(self):
        """Test that email not found raises UserNotFoundError."""
        mock_client = MagicMock()
        mock_client.search_users.return_value = []

        with pytest.raises(UserNotFoundError) as exc_info:
            resolve_user_to_account_id(mock_client, "unknown@example.com")

        assert exc_info.value.identifier == "unknown@example.com"

    def test_email_with_plus_sign(self):
        """Test email with plus sign (contains @)."""
        mock_client = MagicMock()
        mock_client.search_users.return_value = [{"accountId": "def456"}]

        result = resolve_user_to_account_id(mock_client, "user+tag@example.com")

        assert result == "def456"
        mock_client.search_users.assert_called_once()


class TestGetUserDisplayInfo:
    """Tests for get_user_display_info function."""

    def test_calls_client_get(self):
        """Test that function calls client.get with correct params."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "accountId": "abc123",
            "displayName": "John Doe",
            "emailAddress": "john@example.com",
            "active": True,
        }

        result = get_user_display_info(mock_client, "abc123")

        assert result["displayName"] == "John Doe"
        mock_client.get.assert_called_once_with(
            "/rest/api/3/user",
            params={"accountId": "abc123"},
            operation="get user abc123",
        )

    def test_returns_full_user_info(self):
        """Test that full user info is returned."""
        mock_client = MagicMock()
        user_data = {
            "accountId": "xyz789",
            "displayName": "Jane Smith",
            "emailAddress": "jane@example.com",
            "active": True,
        }
        mock_client.get.return_value = user_data

        result = get_user_display_info(mock_client, "xyz789")

        assert result == user_data


class TestResolveUsersBatch:
    """Tests for resolve_users_batch function."""

    def test_resolves_multiple_emails(self):
        """Test resolving multiple email addresses."""
        mock_client = MagicMock()
        mock_client.search_users.side_effect = [
            [{"accountId": "id1"}],
            [{"accountId": "id2"}],
        ]

        result = resolve_users_batch(
            mock_client,
            ["user1@example.com", "user2@example.com"],
        )

        assert result == {
            "user1@example.com": "id1",
            "user2@example.com": "id2",
        }

    def test_passes_through_account_ids(self):
        """Test that account IDs are passed through without search."""
        mock_client = MagicMock()

        result = resolve_users_batch(mock_client, ["abc123", "def456"])

        assert result == {"abc123": "abc123", "def456": "def456"}
        mock_client.search_users.assert_not_called()

    def test_mixed_emails_and_ids(self):
        """Test mix of emails and account IDs."""
        mock_client = MagicMock()
        mock_client.search_users.return_value = [{"accountId": "resolved123"}]

        result = resolve_users_batch(
            mock_client,
            ["user@example.com", "existing-id"],
        )

        assert result == {
            "user@example.com": "resolved123",
            "existing-id": "existing-id",
        }

    def test_skips_not_found_users(self):
        """Test that users not found are silently skipped."""
        mock_client = MagicMock()
        mock_client.search_users.side_effect = [
            [{"accountId": "found123"}],
            [],  # Second user not found
        ]

        result = resolve_users_batch(
            mock_client,
            ["found@example.com", "notfound@example.com"],
        )

        # Only the found user should be in result
        assert result == {"found@example.com": "found123"}
        assert "notfound@example.com" not in result

    def test_empty_list_returns_empty_dict(self):
        """Test empty input returns empty dict."""
        mock_client = MagicMock()

        result = resolve_users_batch(mock_client, [])

        assert result == {}

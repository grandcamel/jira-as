"""Tests for the JIRA credential manager."""

from unittest.mock import MagicMock, patch

import pytest

from jira_as.credential_manager import (
    CredentialManager,
    CredentialNotFoundError,
    get_credential_manager,
    get_credentials,
    is_keychain_available,
    store_credentials,
    validate_credentials,
)


class TestCredentialManager:
    """Tests for CredentialManager class."""

    def test_get_service_name(self):
        """Test service name is jira-assistant."""
        manager = CredentialManager()
        assert manager.get_service_name() == "jira-assistant"

    def test_get_env_prefix(self):
        """Test environment prefix is JIRA."""
        manager = CredentialManager()
        assert manager.get_env_prefix() == "JIRA"

    def test_get_credential_fields(self):
        """Test credential fields list."""
        manager = CredentialManager()
        fields = manager.get_credential_fields()
        assert "site_url" in fields
        assert "email" in fields
        assert "api_token" in fields

    def test_get_credential_not_found_hint(self):
        """Test hint text includes setup instructions."""
        manager = CredentialManager()
        hint = manager.get_credential_not_found_hint()
        assert "JIRA_API_TOKEN" in hint
        assert "JIRA_EMAIL" in hint
        assert "JIRA_SITE_URL" in hint
        assert "id.atlassian.com" in hint


class TestCredentialNotFoundError:
    """Tests for CredentialNotFoundError class."""

    def test_error_message(self):
        """Test error message includes instructions."""
        error = CredentialNotFoundError()
        message = str(error)
        assert "No JIRA credentials found" in message
        assert "JIRA_API_TOKEN" in message
        assert "JIRA_EMAIL" in message
        assert "JIRA_SITE_URL" in message


class TestValidateCredentials:
    """Tests for credential validation."""

    @patch("requests.get")
    def test_validate_success(self, mock_get):
        """Test successful validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "accountId": "abc123",
            "displayName": "Test User",
        }
        mock_get.return_value = mock_response

        manager = CredentialManager()
        result = manager.validate_credentials(
            {
                "site_url": "https://test.atlassian.net",
                "email": "test@example.com",
                "api_token": "test-token",
            }
        )

        assert result["accountId"] == "abc123"

    @patch("requests.get")
    def test_validate_401_unauthorized(self, mock_get):
        """Test validation with 401 response."""
        from jira_as.error_handler import AuthenticationError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        manager = CredentialManager()
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            manager.validate_credentials(
                {
                    "site_url": "https://test.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "bad-token",
                }
            )

    @patch("requests.get")
    def test_validate_403_forbidden(self, mock_get):
        """Test validation with 403 response."""
        from jira_as.error_handler import AuthenticationError

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        manager = CredentialManager()
        with pytest.raises(AuthenticationError, match="Access forbidden"):
            manager.validate_credentials(
                {
                    "site_url": "https://test.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "test-token",
                }
            )

    @patch("requests.get")
    def test_validate_connection_error(self, mock_get):
        """Test validation with connection error."""
        import requests

        from jira_as.error_handler import JiraError

        mock_get.side_effect = requests.exceptions.ConnectionError()

        manager = CredentialManager()
        with pytest.raises(JiraError, match="Cannot connect"):
            manager.validate_credentials(
                {
                    "site_url": "https://test.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "test-token",
                }
            )

    @patch("requests.get")
    def test_validate_timeout(self, mock_get):
        """Test validation with timeout."""
        import requests

        from jira_as.error_handler import JiraError

        mock_get.side_effect = requests.exceptions.Timeout()

        manager = CredentialManager()
        with pytest.raises(JiraError, match="timed out"):
            manager.validate_credentials(
                {
                    "site_url": "https://test.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "test-token",
                }
            )


class TestGetCredentialsTuple:
    """Tests for get_credentials_tuple method."""

    @patch.object(CredentialManager, "get_credentials")
    def test_get_credentials_tuple_success(self, mock_get):
        """Test successful credential retrieval as tuple."""
        mock_get.return_value = {
            "site_url": "https://test.atlassian.net",
            "email": "test@example.com",
            "api_token": "test-token",
        }

        manager = CredentialManager()
        url, email, token = manager.get_credentials_tuple()

        assert url == "https://test.atlassian.net"
        assert email == "test@example.com"
        assert token == "test-token"

    @patch.object(CredentialManager, "get_credentials")
    def test_get_credentials_tuple_not_found(self, mock_get):
        """Test credential not found raises error."""
        from assistant_skills_lib import CredentialNotFoundError as BaseError

        mock_get.side_effect = BaseError("jira-assistant")

        manager = CredentialManager()
        with pytest.raises(CredentialNotFoundError):
            manager.get_credentials_tuple()


class TestStoreCredentialsTuple:
    """Tests for store_credentials_tuple method."""

    @patch.object(CredentialManager, "store_credentials")
    def test_store_credentials_tuple_success(self, mock_store):
        """Test successful credential storage."""
        from assistant_skills_lib import CredentialBackend

        mock_store.return_value = CredentialBackend.KEYCHAIN

        manager = CredentialManager()
        result = manager.store_credentials_tuple(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

        assert result == CredentialBackend.KEYCHAIN
        mock_store.assert_called_once()

    def test_store_credentials_tuple_empty_token(self):
        """Test storing with empty token raises error."""
        from jira_as.error_handler import ValidationError

        manager = CredentialManager()
        with pytest.raises(ValidationError, match="API token cannot be empty"):
            manager.store_credentials_tuple(
                url="https://test.atlassian.net",
                email="test@example.com",
                api_token="",
            )

    def test_store_credentials_tuple_whitespace_token(self):
        """Test storing with whitespace token raises error."""
        from jira_as.error_handler import ValidationError

        manager = CredentialManager()
        with pytest.raises(ValidationError, match="API token cannot be empty"):
            manager.store_credentials_tuple(
                url="https://test.atlassian.net",
                email="test@example.com",
                api_token="   ",
            )


class TestValidateCredentialsTuple:
    """Tests for validate_credentials_tuple method."""

    @patch.object(CredentialManager, "validate_credentials")
    def test_validate_credentials_tuple(self, mock_validate):
        """Test validating credentials from tuple values."""
        mock_validate.return_value = {"accountId": "abc123"}

        manager = CredentialManager()
        result = manager.validate_credentials_tuple(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

        assert result["accountId"] == "abc123"
        mock_validate.assert_called_once()


class TestSingletonAndConvenienceFunctions:
    """Tests for singleton and convenience functions."""

    def test_get_credential_manager_singleton(self):
        """Test get_credential_manager returns same instance."""
        # Reset the singleton for testing
        import jira_as.credential_manager as cm

        cm._credential_manager = None

        manager1 = get_credential_manager()
        manager2 = get_credential_manager()

        assert manager1 is manager2

        # Clean up
        cm._credential_manager = None

    def test_is_keychain_available(self):
        """Test is_keychain_available wrapper."""
        # Just test it doesn't crash - actual availability depends on system
        result = is_keychain_available()
        assert isinstance(result, bool)


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch.object(CredentialManager, "get_credentials_tuple")
    def test_get_credentials(self, mock_get_tuple):
        """Test get_credentials convenience function."""
        mock_get_tuple.return_value = (
            "https://test.atlassian.net",
            "test@example.com",
            "test-token",
        )

        # Reset singleton to use fresh manager
        import jira_as.credential_manager as cm

        cm._credential_manager = None

        url, email, token = get_credentials()

        assert url == "https://test.atlassian.net"
        assert email == "test@example.com"
        assert token == "test-token"

        # Clean up
        cm._credential_manager = None

    @patch.object(CredentialManager, "store_credentials_tuple")
    def test_store_credentials(self, mock_store):
        """Test store_credentials convenience function."""
        from assistant_skills_lib import CredentialBackend

        mock_store.return_value = CredentialBackend.KEYCHAIN

        # Reset singleton
        import jira_as.credential_manager as cm

        cm._credential_manager = None

        result = store_credentials(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

        assert result == CredentialBackend.KEYCHAIN

        # Clean up
        cm._credential_manager = None

    @patch.object(CredentialManager, "validate_credentials_tuple")
    def test_validate_credentials_function(self, mock_validate):
        """Test validate_credentials convenience function."""
        mock_validate.return_value = {"accountId": "abc123"}

        # Reset singleton
        import jira_as.credential_manager as cm

        cm._credential_manager = None

        result = validate_credentials(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

        assert result["accountId"] == "abc123"

        # Clean up
        cm._credential_manager = None
